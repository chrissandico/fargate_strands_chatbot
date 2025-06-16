from collections.abc import Callable
from queue import Queue
from threading import Thread
from typing import Iterator, Dict, Optional
from uuid import uuid4
import asyncio
import json

from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import StreamingResponse, PlainTextResponse
from pydantic import BaseModel
import uvicorn
from strands import Agent, tool
from strands_tools import http_request
import os
from mcp import StdioServerParameters, stdio_client
from utils.aws_config import aws_config
from mcp.client.streamable_http import streamablehttp_client
from strands.tools.mcp import MCPClient
from dotenv import load_dotenv

from coordinator_agent import CoordinatorAgent
from card_researcher import card_research_agent, CARD_RESEARCH_SYSTEM_PROMPT
from utils.logging import get_logger
from utils.streaming import queue_to_generator

# Load environment variables from .env files in multiple possible locations
# This ensures we find the .env file regardless of where the script is run from
possible_env_paths = [
    '.env',  # Current directory
    '../.env',  # Parent directory
    '../../.env',  # Two levels up
    '../../../.env',  # Three levels up
    '../../local_tests/.env',  # local_tests directory from app directory
    '../local_tests/.env',  # local_tests directory from parent directory
]

for env_path in possible_env_paths:
    if os.path.exists(env_path):
        logger = get_logger("app_init")
        logger.info(f"Loading environment variables from {env_path}")
        load_dotenv(env_path)
        break

# Configure logger
logger = get_logger("app")

# Function to retrieve parameters from AWS Parameter Store
def get_parameter(service_name, parameter_name):
    """Retrieve a parameter from AWS Parameter Store."""
    logger.info(f"get_parameter called for {service_name}/{parameter_name}")
    
    # For local development, use environment variables
    env_var_name = f"{service_name.upper()}_{parameter_name.upper().replace('-', '_')}"
    logger.info(f"Looking for environment variable: {env_var_name}")
    env_value = os.environ.get(env_var_name)
    logger.info(f"Environment variable value: {env_value[:5] if env_value else 'None'}")
    
    # Also check for direct PERPLEXITY_API_KEY
    if service_name == 'perplexity' and parameter_name == 'api-key':
        direct_api_key = os.environ.get('PERPLEXITY_API_KEY')
        logger.info(f"Direct PERPLEXITY_API_KEY: {direct_api_key[:5] if direct_api_key else 'None'}")
        if direct_api_key:
            logger.info(f"Using direct PERPLEXITY_API_KEY")
            return direct_api_key
    
    if env_value:
        logger.info(f"Using environment variable value")
        return env_value
    
    # Check if we're running in a Docker container (local development)
    in_docker = os.path.exists('/.dockerenv')
    logger.info(f"Running in Docker container: {in_docker}")
    
    if in_docker:
        logger.info(f"Running in Docker container, using default value for {service_name}/{parameter_name}")
        # For Perplexity API key, use a default value for testing
        if service_name == 'perplexity' and parameter_name == 'api-key':
            default_key = os.environ.get('PERPLEXITY_API_KEY')
            if default_key:
                logger.info(f"Using API key from Docker environment: {default_key[:5] if default_key else 'None'}...")
                return default_key
            logger.info("No API key found in Docker environment")
            return None
    
    # Try AWS Parameter Store using centralized AWS config
    try:
        parameter_path = f"/tcg-agent/production/{service_name}/{parameter_name}"
        logger.info(f"Trying AWS Parameter Store: {parameter_path}")
        value = aws_config.get_parameter(parameter_path)
        if value:
            logger.info(f"Found parameter in AWS Parameter Store")
            return value
    except Exception as e:
        logger.error(f"Error retrieving parameter from AWS: {str(e)}")
    
    return None

# Define a weather-focused system prompt
WEATHER_SYSTEM_PROMPT = """You are a weather assistant with HTTP capabilities. You can:

1. Make HTTP requests to the National Weather Service API
2. Process and display weather forecast data
3. Provide weather information for locations in the United States

When retrieving weather information:
1. First get the coordinates or grid information using https://api.weather.gov/points/{latitude},{longitude} or https://api.weather.gov/points/{zipcode}
2. Then use the returned forecast URL to get the actual forecast

When displaying responses:
- Format weather data in a human-readable way
- Highlight important information like temperature, precipitation, and alerts
- Handle errors appropriately
- Don't ask follow-up questions

Always explain the weather conditions clearly and provide context for the forecast.

At the point where tools are done being invoked and a summary can be presented to the user, invoke the ready_to_summarize
tool and then continue with the summary.
"""

class PromptRequest(BaseModel):
    prompt: str

# Create FastAPI app
app = FastAPI(title="TCG Assistant API")

@app.get('/health')
def health_check():
    """Health check endpoint for the load balancer."""
    return {"status": "healthy"}

@app.post('/weather')
async def get_weather(request: PromptRequest):
    """Endpoint to get weather information."""
    prompt = request.prompt
    
    if not prompt:
        raise HTTPException(status_code=400, detail="No prompt provided")

    try:
        weather_agent = Agent(
            system_prompt=WEATHER_SYSTEM_PROMPT,
            tools=[http_request],
        )
        response = weather_agent(prompt)
        content = str(response)
        return PlainTextResponse(content=content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def run_weather_agent_and_stream_response(prompt: str):
    """
    A helper function to yield summary text chunks one by one as they come in, allowing the web server to emit
    them to caller live
    """
    is_summarizing = False

    @tool
    def ready_to_summarize():
        """
        A tool that is intended to be called by the agent right before summarize the response.
        """
        nonlocal is_summarizing
        is_summarizing = True
        return "Ok - continue providing the summary!"

    weather_agent = Agent(
        system_prompt=WEATHER_SYSTEM_PROMPT,
        tools=[http_request, ready_to_summarize],
        callback_handler=None
    )

    async for item in weather_agent.stream_async(prompt):
        if not is_summarizing:
            continue
        if "data" in item:
            yield item['data']

@app.post('/weather-streaming')
async def get_weather_streaming(request: PromptRequest):
    """Endpoint to stream the weather summary as it comes it, not all at once at the end."""
    try:
        prompt = request.prompt

        if not prompt:
            raise HTTPException(status_code=400, detail="No prompt provided")

        return StreamingResponse(
            run_weather_agent_and_stream_response(prompt),
            media_type="text/plain"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Card research system prompt and agent are now imported from card_researcher.py

@app.post('/card-search')
async def search_card(request: PromptRequest):
    """Endpoint to search for card information using Perplexity."""
    prompt = request.prompt
    
    if not prompt:
        raise HTTPException(status_code=400, detail="No prompt provided")

    try:
        # Debug environment variables before calling card_research_agent
        perplexity_api_key = os.environ.get("PERPLEXITY_API_KEY")
        logger.info(f"PERPLEXITY_API_KEY before card_research_agent call: {'Present' if perplexity_api_key else 'Missing'}")
        if perplexity_api_key:
            logger.info(f"API key starts with: {perplexity_api_key[:5]}...")
        else:
            # Try to load .env file again if API key is missing
            for env_path in possible_env_paths:
                if os.path.exists(env_path):
                    logger.info(f"Reloading environment variables from {env_path}")
                    load_dotenv(env_path)
                    perplexity_api_key = os.environ.get("PERPLEXITY_API_KEY")
                    if perplexity_api_key:
                        logger.info(f"API key found after reload: {perplexity_api_key[:5]}...")
                        break
        
        result = card_research_agent(prompt)
        return PlainTextResponse(content=result)
    except Exception as e:
        logger.error(f"Error in card search endpoint: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

async def run_card_search_agent_and_stream_response(prompt: str):
    """
    A helper function to yield card search results one by one as they come in
    """
    is_summarizing = False

    @tool
    def ready_to_summarize():
        """
        A tool that is intended to be called by the agent right before summarize the response.
        """
        nonlocal is_summarizing
        is_summarizing = True
        return "Ok - continue providing the summary!"

    try:
        # Get the result from the card_research_agent
        result = card_research_agent(prompt)
        
        # Simulate streaming by yielding chunks of the response
        chunk_size = 50
        for i in range(0, len(result), chunk_size):
            yield result[i:i+chunk_size]
            await asyncio.sleep(0.1)  # Add a small delay to simulate streaming
            
    except Exception as e:
        logger = get_logger("app")
        logger.error(f"Error processing card query: {str(e)}", exc_info=True)
        yield f"Error processing your card query: {str(e)}"

@app.post('/card-search-streaming')
async def get_card_search_streaming(request: PromptRequest):
    """Endpoint to stream card search results."""
    try:
        prompt = request.prompt

        if not prompt:
            raise HTTPException(status_code=400, detail="No prompt provided")

        return StreamingResponse(
            run_card_search_agent_and_stream_response(prompt),
            media_type="text/plain"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Initialize coordinator agent
try:
    coordinator_agent = CoordinatorAgent()
    logger.info("Coordinator agent initialized successfully")
except Exception as e:
    logger.error(f"Error initializing coordinator agent: {str(e)}", exc_info=True)
    coordinator_agent = None

# Define coordinator endpoints
@app.post('/coordinator')
async def get_coordinator_response(request: PromptRequest):
    """Endpoint to get a response from the coordinator agent."""
    try:
        if coordinator_agent is None:
            logger.error("Coordinator agent not initialized")
            raise HTTPException(status_code=500, detail="Coordinator agent not initialized")
            
        prompt = request.prompt
        logger.info(f"Received prompt: {prompt}")

        if not prompt:
            raise HTTPException(status_code=400, detail="No prompt provided")

        response = coordinator_agent.process_query(prompt)
        logger.info(f"Generated response of length: {len(response)}")
        return PlainTextResponse(content=response)
    except Exception as e:
        logger.error(f"Error in coordinator endpoint: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post('/coordinator-streaming')
async def get_coordinator_streaming(request: PromptRequest):
    """Endpoint to stream coordinator agent responses with reasoning events."""
    try:
        if coordinator_agent is None:
            logger.error("Coordinator agent not initialized")
            raise HTTPException(status_code=500, detail="Coordinator agent not initialized")
            
        prompt = request.prompt
        logger.info(f"Received streaming prompt: {prompt}")

        if not prompt:
            raise HTTPException(status_code=400, detail="No prompt provided")

        async def generate():
            async for event in coordinator_agent.stream_async(prompt):
                yield json.dumps(event) + "\n"

        return StreamingResponse(
            generate(),
            media_type="application/json"
        )
    except Exception as e:
        logger.error(f"Error in coordinator streaming endpoint: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post('/coordinator-streaming-callback')
async def get_coordinator_streaming_callback(request: PromptRequest):
    """Endpoint to stream coordinator agent responses using callback handler."""
    try:
        if coordinator_agent is None:
            logger.error("Coordinator agent not initialized")
            raise HTTPException(status_code=500, detail="Coordinator agent not initialized")
            
        prompt = request.prompt
        logger.info(f"Received streaming callback prompt: {prompt}")

        if not prompt:
            raise HTTPException(status_code=400, detail="No prompt provided")

        # Create a queue for streaming events
        queue = asyncio.Queue()
        
        # Start agent in background task
        task = asyncio.create_task(run_agent_with_callback(coordinator_agent, prompt, queue))
        
        return StreamingResponse(
            queue_to_generator(queue),
            media_type="application/json"
        )
    except Exception as e:
        logger.error(f"Error in coordinator streaming callback endpoint: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

async def run_agent_with_callback(agent, prompt, queue):
    """Run agent with callback handler and signal completion."""
    try:
        agent.stream_with_callback(prompt, queue)
    except Exception as e:
        logger = get_logger("app")
        logger.error(f"Error running agent with callback: {str(e)}", exc_info=True)
        await queue.put({"error": True, "message": str(e)})

if __name__ == '__main__':
    # Get port from environment variable or default to 8000
    port = int(os.environ.get('PORT', 8000))
    uvicorn.run(app, host='0.0.0.0', port=port)
