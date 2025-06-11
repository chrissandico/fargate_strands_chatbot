from collections.abc import Callable
from queue import Queue
from threading import Thread
from typing import Iterator, Dict, Optional
from uuid import uuid4
import asyncio

from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import StreamingResponse, PlainTextResponse
from pydantic import BaseModel
import uvicorn
from strands import Agent, tool
from strands_tools import http_request
import os
import boto3
from mcp import StdioServerParameters, stdio_client
from mcp.client.streamable_http import streamablehttp_client
from strands.tools.mcp import MCPClient
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()

app = FastAPI(title="TCG Assistant API")

# Function to retrieve parameters from AWS Parameter Store
def get_parameter(service_name, parameter_name):
    """Retrieve a parameter from AWS Parameter Store."""
    print(f"get_parameter called for {service_name}/{parameter_name}")
    
    # For local development, use environment variables
    env_var_name = f"{service_name.upper()}_{parameter_name.upper().replace('-', '_')}"
    print(f"Looking for environment variable: {env_var_name}")
    env_value = os.environ.get(env_var_name)
    print(f"Environment variable value: {env_value}")
    
    # Also check for direct PERPLEXITY_API_KEY
    if service_name == 'perplexity' and parameter_name == 'api-key':
        direct_api_key = os.environ.get('PERPLEXITY_API_KEY')
        print(f"Direct PERPLEXITY_API_KEY: {direct_api_key}")
        if direct_api_key:
            print(f"Using direct PERPLEXITY_API_KEY")
            return direct_api_key
    
    if env_value:
        print(f"Using environment variable value")
        return env_value
    
    # Check if we're running in a Docker container (local development)
    in_docker = os.path.exists('/.dockerenv')
    print(f"Running in Docker container: {in_docker}")
    
    if in_docker:
        print(f"Running in Docker container, using default value for {service_name}/{parameter_name}")
        # For Perplexity API key, use a default value for testing
    if service_name == 'perplexity' and parameter_name == 'api-key':
        default_key = os.environ.get('PERPLEXITY_API_KEY')
        if default_key:
            print(f"Using API key from Docker environment: {default_key[:5] if default_key else 'None'}...")
            return default_key
        print("No API key found in Docker environment")
        return None
    
    # Skip AWS Parameter Store for local development
    print("Skipping AWS Parameter Store for local development")
    if service_name == 'perplexity' and parameter_name == 'api-key':
        # Check for API key in environment variables
        env_key = os.environ.get('PERPLEXITY_API_KEY')
        if env_key:
            print(f"Using API key from environment variables: {env_key[:5]}...")
            return env_key
        print("No API key found in environment variables")
        return None
    
    # If environment variable is not set and not in Docker, try AWS Parameter Store
    # This code is kept for reference but not used in local development
    """
    parameter_path = f"/tcg-agent/production/{service_name}/{parameter_name}"
    try:
        ssm = boto3.client('ssm', region_name='us-east-1')
        response = ssm.get_parameter(
            Name=parameter_path,
            WithDecryption=True
        )
        return response['Parameter']['Value']
    except Exception as e:
        print(f"Error retrieving parameter {parameter_path}: {str(e)}")
        return None
    """
    
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

# Define a card research system prompt
CARD_RESEARCH_SYSTEM_PROMPT = """You are a One Piece Trading Card Game expert assistant.
When users mention card nicknames or descriptions, translate them to official card IDs.
For example, "Blue Doffy Leader" should be translated to "OP01-060".
Always include the card ID in your response when you find a match.
Provide detailed information about the card including its effects, rarity, and set.

Use web search to find accurate information about One Piece TCG cards.
When searching, include terms like "One Piece TCG", "card ID", and specific card details.
Always verify information from multiple sources when possible.

Format your responses clearly with:
1. Card ID (e.g., OP01-060)
2. Card Name
3. Card Type (Leader, Character, Event, etc.)
4. Color
5. Cost (if applicable)
6. Power (if applicable)
7. Counter (if applicable)
8. Card Effect/Text
9. Set Information
10. Rarity

If you cannot find a specific card ID, explain what information you found and suggest possible matches.
"""

@tool
def card_research_agent(query: str) -> str:
    """
    Process and respond to card identification queries using Perplexity.
    
    Args:
        query: A question about One Piece TCG cards
        
    Returns:
        Detailed card information including card ID
    """
    formatted_query = f"Please identify this One Piece Trading Card Game card: {query}. Include the card ID, name, type, color, cost, power, counter, effect text, set information, and rarity."
    
    try:
        print("Routed to Card Research Agent")
        
        # Get Perplexity API key directly from environment variables
        perplexity_api_key = os.environ.get("PERPLEXITY_API_KEY")
        print(f"PERPLEXITY_API_KEY from env: {perplexity_api_key}")
        
        if not perplexity_api_key:
            # Fall back to Parameter Store only if environment variable is not set
            perplexity_api_key = get_parameter('perplexity', 'api-key')
            print(f"PERPLEXITY_API_KEY from parameter store: {perplexity_api_key}")
            
        if not perplexity_api_key:
            return "Error: Perplexity API key not found. Please ensure the API key is set in environment variables or Parameter Store."
        
        print(f"Using PERPLEXITY_API_KEY: {perplexity_api_key[:5]}...")
        
        # Use direct API call to Perplexity
        import requests
        import json
        
        # Define the API endpoint
        url = "https://api.perplexity.ai/chat/completions"
        
        # Define the request headers
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {perplexity_api_key}"
        }
        
        # Define the request body
        body = {
            "model": "sonar-pro",
            "messages": [
                {
                    "role": "user",
                    "content": formatted_query
                }
            ]
        }
        
        print(f"Sending request to {url}...")
        
        # Send the request
        response = requests.post(url, headers=headers, json=body)
        
        # Check if the request was successful
        if response.status_code == 200:
            print("Request successful!")
            response_data = response.json()
            
            # Extract the message content
            message_content = response_data["choices"][0]["message"]["content"]
            
            # Add citations if available
            if "citations" in response_data and response_data["citations"]:
                message_content += "\n\nCitations:\n"
                for i, citation in enumerate(response_data["citations"]):
                    message_content += f"[{i+1}] {citation}\n"
            
            print(f"Response length: {len(message_content)}")
            print(f"Response preview: {message_content[:100]}...")
            
            return message_content
        else:
            error_message = f"Request failed with status code {response.status_code}: {response.text}"
            print(error_message)
            return f"Error: Failed to get response from Perplexity API. {error_message}"
    except Exception as e:
        print(f"Error processing card query: {str(e)}")
        return f"Error processing your card query: {str(e)}"
        
        # The following code is kept for reference but not used and is unreachable
        """
        perplexity_mcp_server = MCPClient(
            lambda: stdio_client(
                StdioServerParameters(
                    command="docker",
                    args=[
                        "run",
                        "-i",
                        "--rm",
                        "-e",
                        f"PERPLEXITY_API_KEY={perplexity_api_key}",
                        "mcp/perplexity-ask",
                    ],
                    env={},
                )
            )
        )

        with perplexity_mcp_server:
            # Get tools from the MCP server
            tools = perplexity_mcp_server.list_tools_sync()
            
            # Create the card research agent
            agent = Agent(
                system_prompt=CARD_RESEARCH_SYSTEM_PROMPT,
                tools=tools,
            )
            
            # Get response from the agent
            response = agent(formatted_query)
            return str(response)
        """

@app.post('/card-search')
async def search_card(request: PromptRequest):
    """Endpoint to search for card information using Perplexity."""
    prompt = request.prompt
    
    if not prompt:
        raise HTTPException(status_code=400, detail="No prompt provided")

    try:
        result = card_research_agent(prompt)
        return PlainTextResponse(content=result)
    except Exception as e:
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
        # Get Perplexity API key directly from environment variables
        perplexity_api_key = os.environ.get("PERPLEXITY_API_KEY")
        print(f"PERPLEXITY_API_KEY from env (streaming): {perplexity_api_key}")
        
        if not perplexity_api_key:
            # Fall back to Parameter Store only if environment variable is not set
            perplexity_api_key = get_parameter('perplexity', 'api-key')
            print(f"PERPLEXITY_API_KEY from parameter store (streaming): {perplexity_api_key}")
            
        if not perplexity_api_key:
            yield "Error: Perplexity API key not found. Please ensure the API key is set in environment variables or Parameter Store."
            return
            
        print(f"Using PERPLEXITY_API_KEY (streaming): {perplexity_api_key[:5]}...")
        
        # Use direct API call to Perplexity
        import requests
        import json
        
        # Define the API endpoint
        url = "https://api.perplexity.ai/chat/completions"
        
        # Define the request headers
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {perplexity_api_key}"
        }
        
        # Define the formatted query
        formatted_query = f"Please identify this One Piece Trading Card Game card: {prompt}. Include the card ID, name, type, color, cost, power, counter, effect text, set information, and rarity."
        
        # Define the request body
        body = {
            "model": "sonar-pro",
            "messages": [
                {
                    "role": "user",
                    "content": formatted_query
                }
            ]
        }
        
        print(f"Sending request to {url} (streaming)...")
        
        # Send the request
        response = requests.post(url, headers=headers, json=body)
        
        # Check if the request was successful
        if response.status_code == 200:
            print("Request successful! (streaming)")
            response_data = response.json()
            
            # Extract the message content
            message_content = response_data["choices"][0]["message"]["content"]
            
            # Add citations if available
            if "citations" in response_data and response_data["citations"]:
                message_content += "\n\nCitations:\n"
                for i, citation in enumerate(response_data["citations"]):
                    message_content += f"[{i+1}] {citation}\n"
            
            print(f"Response length (streaming): {len(message_content)}")
            
            # Simulate streaming by yielding chunks of the response
            chunk_size = 50
            for i in range(0, len(message_content), chunk_size):
                yield message_content[i:i+chunk_size]
                await asyncio.sleep(0.1)  # Add a small delay to simulate streaming
        else:
            error_message = f"Request failed with status code {response.status_code}: {response.text}"
            print(error_message)
            yield f"Error: Failed to get response from Perplexity API. {error_message}"

        # The following code is kept for reference but not used
        """
        perplexity_mcp_server = MCPClient(
            lambda: stdio_client(
                StdioServerParameters(
                    command="docker",
                    args=[
                        "run",
                        "-i",
                        "--rm",
                        "-e",
                        f"PERPLEXITY_API_KEY={perplexity_api_key}",
                        "mcp/perplexity-ask",
                    ],
                    env={},
                )
            )
        )

        with perplexity_mcp_server:
            # Get tools from the MCP server
            tools = perplexity_mcp_server.list_tools_sync()
            
            # Create the card research agent
            formatted_query = f"Please identify this One Piece Trading Card Game card: {prompt}. Include the card ID, name, type, color, cost, power, counter, effect text, set information, and rarity."
            
            card_search_agent = Agent(
                system_prompt=CARD_RESEARCH_SYSTEM_PROMPT,
                tools=tools + [ready_to_summarize],
                callback_handler=None
            )
            
            async for item in card_search_agent.stream_async(formatted_query):
                if not is_summarizing:
                    continue
                if "data" in item:
                    yield item['data']
        """
    except Exception as e:
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

if __name__ == '__main__':
    # Get port from environment variable or default to 8000
    port = int(os.environ.get('PORT', 8000))
    uvicorn.run(app, host='0.0.0.0', port=port)
