"""
Card Researcher module for One Piece TCG cards.
This module provides functionality to research One Piece TCG cards using Perplexity API.
"""

import os
import json
import requests
import pathlib
from datetime import datetime
from strands import tool
from utils.logging import get_logger
from utils.aws_config import aws_config
from dotenv import load_dotenv

# Configure logger
logger = get_logger("card_researcher")

# Counter for API calls
PERPLEXITY_API_CALL_COUNT = 0
# Maximum number of API calls allowed (configurable)
PERPLEXITY_API_CALL_LIMIT = int(os.environ.get('PERPLEXITY_API_CALL_LIMIT', '1'))
# Flag to enable/disable the limit
PERPLEXITY_API_LIMIT_ENABLED = os.environ.get('PERPLEXITY_API_LIMIT_ENABLED', 'true').lower() == 'true'

# Load environment variables from .env files in multiple possible locations
# This ensures we find the .env file regardless of where the script is run from
possible_env_paths = [
    '.env',  # Current directory
    '../.env',  # Parent directory
    '../../.env',  # Two levels up
    '../../../.env',  # Three levels up
    '../../local_tests/.env',  # local_tests directory from app directory
]

for env_path in possible_env_paths:
    if os.path.exists(env_path):
        logger.info(f"Loading environment variables from {env_path}")
        load_dotenv(env_path)
        break

# Define a card research system prompt
CARD_RESEARCH_SYSTEM_PROMPT = """You are a One Piece Trading Card Game expert assistant.
When users mention card nicknames or descriptions, translate them to official card IDs.
For example, "Blue Doffy Leader" should be translated to "OP01-060".
Always include the card ID in your response when you find a match.

Use web search to find accurate information about One Piece TCG cards.
Here is the official card list frmo Bandai: https://en.onepiece-cardgame.com/cardlist/ 
You can filter it on all sets and all leaders.
Always verify information from multiple sources when possible.
Format your responses clearly with only the Card ID (e.g., OP01-060)

If you cannot find a specific card ID, just mention you cannot find the Card ID, don't do extra things.
"""

# Helper function to get Perplexity API key using centralized AWS config
def get_perplexity_api_key():
    """Get Perplexity API key using centralized AWS config."""
    logger.info("Getting Perplexity API key")
    
    # First check for direct environment variable
    direct_api_key = os.environ.get('PERPLEXITY_API_KEY')
    if direct_api_key:
        logger.info(f"Using API key from PERPLEXITY_API_KEY environment variable: {direct_api_key[:5]}...")
        return direct_api_key
    
    # Next check for PERPLEXITY_API_KEY environment variable
    env_value = os.environ.get('PERPLEXITY_API_KEY')
    if env_value:
        logger.info(f"Using API key from environment variable: {env_value[:5]}...")
        return env_value
    
    # Finally, try AWS Parameter Store using centralized config
    try:
        parameter_path = "/tcg-agent/production/perplexity/api-key"
        logger.info(f"Trying AWS Parameter Store: {parameter_path}")
        value = aws_config.get_parameter(parameter_path)
        if value:
            logger.info(f"Found parameter in AWS Parameter Store")
            return value
    except Exception as e:
        logger.error(f"Error retrieving parameter from AWS: {str(e)}")
    
    logger.error("Perplexity API key not found")
    return None

def reset_perplexity_api_counter():
    """Reset the Perplexity API call counter to zero."""
    global PERPLEXITY_API_CALL_COUNT
    logger.info("Resetting Perplexity API call counter")
    PERPLEXITY_API_CALL_COUNT = 0
    return PERPLEXITY_API_CALL_COUNT

def get_perplexity_api_counter():
    """Get the current Perplexity API call count and limit."""
    return {
        "count": PERPLEXITY_API_CALL_COUNT,
        "limit": PERPLEXITY_API_CALL_LIMIT,
        "enabled": PERPLEXITY_API_LIMIT_ENABLED
    }

@tool
def card_research_agent(query: str) -> str:
    """
    Process and respond to card identification queries using Perplexity.
    
    Args:
        query: A question about One Piece TCG cards
        
    Returns:
        Detailed card information including card ID
    """
    global PERPLEXITY_API_CALL_COUNT
    
    formatted_query = f"Please identify this One Piece Trading Card Game card: {query}. Include the card ID, name, type, color, cost, power, counter, effect text, set information, and rarity."
    
    try:
        logger.info(f"Card research agent called with query: {query}")
        
        # Check if we've reached the API call limit
        if PERPLEXITY_API_LIMIT_ENABLED and PERPLEXITY_API_CALL_COUNT >= PERPLEXITY_API_CALL_LIMIT:
            logger.warning(f"Perplexity API call limit reached ({PERPLEXITY_API_CALL_LIMIT}). Skipping API call.")
            return f"API call limit reached ({PERPLEXITY_API_CALL_COUNT}/{PERPLEXITY_API_CALL_LIMIT}). For testing purposes, further calls to Perplexity API have been disabled. Adjust PERPLEXITY_API_CALL_LIMIT environment variable to change this limit."
        
        # Debug current directory and environment
        current_dir = os.getcwd()
        logger.info(f"Current working directory: {current_dir}")
        logger.info(f"Environment variables: PERPLEXITY_API_KEY exists: {'Yes' if 'PERPLEXITY_API_KEY' in os.environ else 'No'}")
        
        # Try to load .env file from the current directory again (in case it wasn't loaded earlier)
        if os.path.exists('.env'):
            logger.info("Loading .env file from current directory")
            load_dotenv('.env')
        elif os.path.exists('../local_tests/.env'):
            logger.info("Loading .env file from ../local_tests/.env")
            load_dotenv('../local_tests/.env')
        
        # Get Perplexity API key using centralized approach
        perplexity_api_key = get_perplexity_api_key()
            
        if not perplexity_api_key:
            logger.error("Perplexity API key not found")
            return "Error: Perplexity API key not found. Please ensure the API key is set in environment variables or Parameter Store."
        
        logger.info(f"Using PERPLEXITY_API_KEY: {perplexity_api_key[:5]}...")
        
        # Use direct API call to Perplexity
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
        
        logger.info(f"Sending request to {url}...")
        
        # Send the request
        response = requests.post(url, headers=headers, json=body)
        
        # Check if the request was successful
        if response.status_code == 200:
            # Increment the API call counter
            PERPLEXITY_API_CALL_COUNT += 1
            logger.info(f"Request successful! Perplexity API call count: {PERPLEXITY_API_CALL_COUNT}/{PERPLEXITY_API_CALL_LIMIT}")
            response_data = response.json()
            
            # Extract the message content
            message_content = response_data["choices"][0]["message"]["content"]
            
            # Add citations if available
            if "citations" in response_data and response_data["citations"]:
                message_content += "\n\nCitations:\n"
                for i, citation in enumerate(response_data["citations"]):
                    message_content += f"[{i+1}] {citation}\n"
            
            logger.info(f"Response length: {len(message_content)}")
            logger.debug(f"Response preview: {message_content[:100]}...")
            
            return message_content
        else:
            error_message = f"Request failed with status code {response.status_code}: {response.text}"
            logger.error(error_message)
            return f"Error: Failed to get response from Perplexity API. {error_message}"
    except Exception as e:
        logger.error(f"Error processing card query: {str(e)}", exc_info=True)
        return f"Error processing your card query: {str(e)}"
