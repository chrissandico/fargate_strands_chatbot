from strands import tool, Agent
from typing import Dict, Any, List, AsyncGenerator
import json
import logging
import asyncio
import os
import requests
from datetime import datetime
from utils.logging import get_logger
from dotenv import load_dotenv

# Import the card_research_agent and related functions from the card_researcher module
from card_researcher import (
    card_research_agent, 
    reset_perplexity_api_counter,
    get_perplexity_api_counter
)

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
        logger = get_logger("coordinator_agent_init")
        logger.info(f"Loading environment variables from {env_path}")
        load_dotenv(env_path)
        break

# Configure logger
logger = get_logger("coordinator_agent")

# System prompt for the coordinator agent
COORDINATOR_SYSTEM_PROMPT = """You are a One Piece Trading Card Game shopping assistant that helps players find competitive decks and purchase cards.

Your task is to coordinate between these specialized tools:
1. get_competitive_decks: Finds competitive tournament decks from GumGum.gg
2. card_research_agent: Provides detailed information about specific cards
3. shopify_search: Searches the Shopify store catalog for cards
4. shopify_cart: Manages the shopping cart
5. manage_perplexity_api_counter: For testing purposes, manages the Perplexity API call counter

When a user asks about competitive decks:
1. Use get_competitive_decks to find appropriate decks
2. Use card_research_agent to get detailed information about key cards
3. Use shopify_search to check availability and pricing
4. Use shopify_cart to help them add cards to their cart

When a user asks about specific cards:
1. Use card_research_agent to get detailed information
2. Use shopify_search to check availability and pricing

When a user wants to purchase cards:
1. Use shopify_cart to manage their shopping cart
2. Guide them through the checkout process

IMPORTANT: Explain your reasoning process clearly as you work through each step.
For example, when analyzing a deck request, explain how you're interpreting the user's preferences.
When researching cards, explain why you're focusing on certain cards first.
When checking shopping options, explain your strategy for finding the best deals.

Always provide helpful, accurate information about One Piece TCG cards and decks.

For testing purposes, you can use the manage_perplexity_api_counter tool to:
- Check the current API call count with action="get"
- Reset the counter with action="reset"
- The default limit is 10 calls, but can be configured with the PERPLEXITY_API_CALL_LIMIT environment variable
"""

@tool
def get_competitive_decks(user_input: str) -> Dict[str, Any]:
    """
    Get competitive One Piece TCG deck recommendations from GumGum.gg database.
    
    Processes natural language input to extract deck search criteria and returns
    tournament-winning deck information with complete deck lists.
    
    Args:
        user_input: Natural language description of deck requirements
                   (e.g., "Show me the latest Red Luffy deck from OP10" or 
                    "I want a competitive deck for Purple Doffy in the west region")
    
    Returns:
        Dictionary containing deck recommendations with complete deck lists,
        tournament information, and metadata. Always mentions data is powered by gumgum.gg.
    """
    # This is a mock implementation for testing
    logger.info(f"Mock get_competitive_decks called with: {user_input}")
    
    # For testing purposes, return a mock deck
    return {
        'success': True,
        'source': 'gumgum.gg',
        'message': 'Tournament-winning deck data powered by www.gumgum.gg',
        'deck': {
            'name': "Red Zoro Tournament Deck",
            'set': "OP10",
            'region': "west",
            'leader': "OP03-001 Roronoa Zoro",
            'author': "Tournament Player",
            'tournament': "Regional Championship",
            'event': "Summer 2025",
            'decklist': [
                {'card_id': 'OP03-001', 'name': 'Roronoa Zoro', 'quantity': 4, 'type': 'Leader'},
                {'card_id': 'OP10-015', 'name': 'Monkey D. Luffy', 'quantity': 4, 'type': 'Character'},
                {'card_id': 'OP09-022', 'name': 'Shanks', 'quantity': 3, 'type': 'Character'},
                {'card_id': 'OP08-017', 'name': 'Eustass "Captain" Kid', 'quantity': 3, 'type': 'Character'}
            ],
            'total_cards': 14
        },
        'metadata': {
            'data_source': 'gumgum.gg tournament database',
            'search_criteria': {'leader': 'Zoro', 'color': 'Red', 'format': 'OP10'},
            'competitive_level': 'Tournament-winning',
            'disclaimer': 'Deck data powered by www.gumgum.gg'
        }
    }

# We're now using the card_research_agent directly from the card_researcher module
# No need to redefine it here

@tool
def manage_perplexity_api_counter(action: str = "get") -> Dict[str, Any]:
    """
    Manage the Perplexity API call counter.
    
    Args:
        action: The action to perform (get, reset)
        
    Returns:
        Dictionary containing counter information
    """
    logger.info(f"Managing Perplexity API counter with action: {action}")
    
    if action == "reset":
        reset_perplexity_api_counter()
        logger.info("Perplexity API counter reset")
        return {
            "success": True,
            "message": "Perplexity API counter reset successfully",
            "counter": get_perplexity_api_counter()
        }
    else:  # Default to "get"
        counter_info = get_perplexity_api_counter()
        logger.info(f"Retrieved Perplexity API counter: {counter_info}")
        return {
            "success": True,
            "counter": counter_info
        }

@tool
def shopify_search(query: str, context: str = "") -> Dict[str, Any]:
    """
    Search the Shopify store catalog for One Piece TCG cards.
    
    Args:
        query: The search query (card name or ID)
        context: Additional context to help tailor results
        
    Returns:
        Dictionary containing search results with product information
    """
    # This is a mock implementation for testing
    logger.info(f"Mock shopify_search called with: {query}, context: {context}")
    
    # For testing purposes, return mock product information
    if "OP03-001" in query or "Zoro" in query:
        return {
            "success": True,
            "products": [
                {
                    "title": "OP03-001 Roronoa Zoro (Leader)",
                    "price": "24.99",
                    "currency": "USD",
                    "available": True,
                    "url": "https://shop.example.com/products/op03-001-zoro",
                    "image_url": "https://shop.example.com/images/op03-001-zoro.jpg",
                    "variant_id": "gid://shopify/ProductVariant/12345"
                }
            ],
            "total_results": 1,
            "source": "shopify"
        }
    elif "OP10-015" in query or "Luffy" in query:
        return {
            "success": True,
            "products": [
                {
                    "title": "OP10-015 Monkey D. Luffy (Super Rare)",
                    "price": "12.99",
                    "currency": "USD",
                    "available": True,
                    "url": "https://shop.example.com/products/op10-015-luffy",
                    "image_url": "https://shop.example.com/images/op10-015-luffy.jpg",
                    "variant_id": "gid://shopify/ProductVariant/67890"
                }
            ],
            "total_results": 1,
            "source": "shopify"
        }
    else:
        return {
            "success": True,
            "products": [],
            "total_results": 0,
            "source": "shopify"
        }

@tool
def shopify_cart(action: str, cart_id: str = None, items: List[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Manage the Shopify shopping cart.
    
    Args:
        action: The action to perform (create, get, update)
        cart_id: The ID of an existing cart (required for get and update)
        items: List of items to add/update in the cart (required for update)
            Each item should have:
            - merchandise_id: The product variant ID
            - quantity: The quantity to add
            - line_item_id: (Optional) The line item ID for existing items
            
    Returns:
        Dictionary containing cart information
    """
    # This is a mock implementation for testing
    logger.info(f"Mock shopify_cart called with: action={action}, cart_id={cart_id}, items={items}")
    
    # For testing purposes, return mock cart information
    if action == "create" or (action == "update" and not cart_id):
        return {
            "success": True,
            "cart": {
                "id": "gid://shopify/Cart/mock123456",
                "lines": items or [],
                "checkout_url": "https://shop.example.com/cart/mock123456",
                "total_price": "0.00",
                "currency": "USD"
            },
            "source": "shopify"
        }
    elif action == "get" and cart_id:
        return {
            "success": True,
            "cart": {
                "id": cart_id,
                "lines": [
                    {
                        "line_item_id": "gid://shopify/CartLine/line1",
                        "merchandise_id": "gid://shopify/ProductVariant/12345",
                        "quantity": 1,
                        "title": "OP03-001 Roronoa Zoro (Leader)",
                        "price": "24.99"
                    }
                ],
                "checkout_url": f"https://shop.example.com/cart/{cart_id}",
                "total_price": "24.99",
                "currency": "USD"
            },
            "source": "shopify"
        }
    elif action == "update" and cart_id and items:
        return {
            "success": True,
            "cart": {
                "id": cart_id,
                "lines": items,
                "checkout_url": f"https://shop.example.com/cart/{cart_id}",
                "total_price": "37.98",  # Mocked total price
                "currency": "USD"
            },
            "source": "shopify"
        }
    else:
        return {
            "success": False,
            "error": f"Invalid action '{action}' or missing required parameters",
            "source": "shopify"
        }

class CoordinatorAgent:
    """
    Coordinator agent that orchestrates between deck recommender, card researcher, and Shopify client.
    """
    
    def __init__(self):
        """Initialize the coordinator agent."""
        # Ensure environment variables are loaded
        for env_path in possible_env_paths:
            if os.path.exists(env_path):
                logger.info(f"Loading environment variables from {env_path}")
                load_dotenv(env_path)
                break
                
        # Debug environment variables
        perplexity_api_key = os.environ.get("PERPLEXITY_API_KEY")
        logger.info(f"PERPLEXITY_API_KEY in coordinator: {'Present' if perplexity_api_key else 'Missing'}")
        if perplexity_api_key:
            logger.info(f"API key starts with: {perplexity_api_key[:5]}...")
        
        self.tools = [
            get_competitive_decks,
            card_research_agent,
            shopify_search,
            shopify_cart,
            manage_perplexity_api_counter
        ]
        
        # Log the initial Perplexity API counter state
        counter_info = get_perplexity_api_counter()
        logger.info(f"Initial Perplexity API counter state: count={counter_info['count']}, limit={counter_info['limit']}, enabled={counter_info['enabled']}")
        
        # Create a native Strands Agent
        self.agent = Agent(
            system_prompt=COORDINATOR_SYSTEM_PROMPT,
            tools=self.tools
        )
        
        logger.info("Coordinator agent initialized with tools")
    
    def process_query(self, prompt: str) -> str:
        """Process a user query and return a response."""
        try:
            logger.info(f"Processing query: {prompt}")
            response = self.agent(prompt)
            logger.info(f"Generated response of length: {len(str(response))}")
            return str(response)
        except Exception as e:
            logger.error(f"Error processing query: {str(e)}", exc_info=True)
            return f"Error processing your request: {str(e)}"
    
    async def stream_async(self, prompt: str) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream the agent's response using async iterator."""
        try:
            logger.info(f"Streaming response for query: {prompt}")
            async for item in self.agent.stream_async(prompt):
                yield item
        except Exception as e:
            logger.error(f"Error streaming response: {str(e)}", exc_info=True)
            yield {"error": True, "message": str(e)}
    
    def stream_with_callback(self, prompt: str, queue: asyncio.Queue):
        """Stream the agent's response using a callback handler and queue."""
        try:
            logger.info(f"Streaming with callback for query: {prompt}")
            
            # Create a callback handler that puts events into the queue
            def callback_handler(event=None, **kwargs):
                if event:
                    asyncio.create_task(queue.put(event))
            
            # Create a temporary agent with the callback handler
            temp_agent = Agent(
                system_prompt=COORDINATOR_SYSTEM_PROMPT,
                tools=self.tools,
                callback_handler=callback_handler
            )
            
            # Start a task to run the agent
            asyncio.create_task(self._run_agent_with_callback(temp_agent, prompt, queue))
            
        except Exception as e:
            logger.error(f"Error in callback streaming: {str(e)}", exc_info=True)
            asyncio.create_task(queue.put({"error": True, "message": str(e)}))
    
    async def _run_agent_with_callback(self, agent, prompt: str, queue: asyncio.Queue):
        """Run the agent with the callback handler."""
        try:
            # Run the agent with the prompt
            agent(prompt)
            
            # Signal completion
            await queue.put({"complete": True})
            
        except Exception as e:
            logger.error(f"Error in direct streaming: {str(e)}", exc_info=True)
            await queue.put({"error": True, "message": str(e)})
