# One Piece TCG Shopping Assistant

This is a coordinator agent that helps One Piece Trading Card Game players find competitive decks and purchase cards. It leverages multiple specialized agents:

1. **Deck Recommender Agent**: Finds competitive tournament decks from GumGum.gg
2. **Card Researcher Agent**: Provides detailed information about specific cards
3. **Shopify Client**: Connects to a Shopify store to check availability and pricing of cards

## Features

- **Deck Recommendations**: Get competitive deck recommendations based on leader, color, and format
- **Card Research**: Get detailed information about specific cards
- **Shopping Integration**: Check availability and pricing of cards in a Shopify store
- **Streaming Responses**: All responses can be streamed in real-time, including reasoning events

## API Endpoints

- `/coordinator`: Get a response from the coordinator agent
- `/coordinator-streaming`: Stream coordinator agent responses with reasoning events using async iterators
- `/coordinator-streaming-callback`: Stream coordinator agent responses using callback handlers

## Usage

### Running Locally

1. Set up environment variables:
   ```
   PERPLEXITY_API_KEY=your-api-key
   COMPETITIVE_DECK_ENDPOINT=your-gumgum-api-endpoint
   COMPETITIVE_DECK_SECRET=your-gumgum-api-key
   SHOPIFY_STORE_DOMAIN=your-shopify-store-domain
   ```

2. Run the server:
   ```
   cd docker/app
   python -m uvicorn app:app --reload --host 0.0.0.0 --port 8000
   ```

3. Or use the provided scripts:
   ```
   # Windows
   ./local_tests/run_coordinator_local.ps1
   
   # Unix
   ./local_tests/run_coordinator_local.sh
   ```

### Testing

1. Run the tests:
   ```
   cd local_tests
   python test_coordinator_agent.py
   ```

2. Test directly without running the server:
   ```
   cd local_tests
   python test_coordinator_direct.py "I want a recent Red Zoro competitive deck"
   ```

## Example Requests

### Get a Deck Recommendation

```
POST /coordinator
{
  "prompt": "I want a recent Red Zoro competitive deck"
}
```

### Stream a Deck Recommendation with Reasoning

```
POST /coordinator-streaming
{
  "prompt": "I want a recent Red Zoro competitive deck"
}
```

### Get Card Information

```
POST /coordinator
{
  "prompt": "Tell me about the OP03-001 Roronoa Zoro card"
}
```

### Check Card Availability and Pricing

```
POST /coordinator
{
  "prompt": "Is OP03-001 Roronoa Zoro available for purchase?"
}
```

## Environment Variables

- `PERPLEXITY_API_KEY`: API key for Perplexity (used by the card researcher agent)
- `COMPETITIVE_DECK_ENDPOINT`: API endpoint for GumGum.gg (used by the deck recommender agent)
- `COMPETITIVE_DECK_SECRET`: API key for GumGum.gg (used by the deck recommender agent)
- `SHOPIFY_STORE_DOMAIN`: Domain for the Shopify store (used by the Shopify client)
- `ENVIRONMENT`: Set to "production" to enable CloudWatch logging

## Logging

- Console logging is enabled by default
- CloudWatch logging is enabled in production mode
