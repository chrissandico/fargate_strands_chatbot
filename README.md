# One Piece TCG Shopping Assistant

This project implements a One Piece Trading Card Game (TCG) Shopping Assistant API using FastAPI and Strands Agents. The API provides endpoints for weather information, card research, and a coordinator agent that helps players find competitive decks and purchase cards.

## Features

### Weather Assistant
- `/weather` - Get weather information for a location
- `/weather-streaming` - Stream weather information for a location

### Card Research Assistant
- `/card-search` - Get information about a One Piece TCG card, including its ID
- `/card-search-streaming` - Stream information about a One Piece TCG card

### Coordinator Agent
- `/coordinator` - Get a response from the coordinator agent
- `/coordinator-streaming` - Stream coordinator agent responses with reasoning events
- `/coordinator-streaming-callback` - Stream coordinator agent responses using callback handlers

## Architecture

The application uses a multi-agent architecture:

1. **Weather Agent**: Makes HTTP requests to the National Weather Service API to provide weather information
2. **Card Research Agent**: Uses the Perplexity API to search for One Piece TCG card information
3. **Coordinator Agent**: Orchestrates between specialized agents:
   - **Deck Recommender**: Finds competitive tournament decks from GumGum.gg
   - **Card Researcher**: Provides detailed information about specific cards
   - **Shopify Client**: Connects to a Shopify store to check availability and pricing of cards

## Prerequisites

- Python 3.12+
- Docker
- AWS CLI configured with appropriate permissions
- Perplexity API key
- GumGum.gg API credentials (optional)
- Shopify store domain (optional)

## Local Development

### Setup

1. Clone the repository
2. Create a `.env` file with your API keys:
   ```
   PERPLEXITY_API_KEY=your-api-key
   COMPETITIVE_DECK_ENDPOINT=your-gumgum-api-endpoint
   COMPETITIVE_DECK_SECRET=your-gumgum-api-key
   SHOPIFY_STORE_DOMAIN=your-shopify-store-domain
   ```
3. Install dependencies:
   ```
   pip install -r docker/requirements.txt
   ```

### Running Locally

Run the FastAPI application:

```bash
cd docker/app
python -m uvicorn app:app --reload
```

Or use the provided scripts:

```bash
# Windows
./local_tests/run_coordinator_local.ps1

# Unix
./local_tests/run_coordinator_local.sh
```

### Testing

Test the coordinator agent:

```bash
# Test all endpoints
python local_tests/test_coordinator_api.py "I want a recent Red Zoro competitive deck"

# Test specific endpoint
python local_tests/test_coordinator_api.py "I want a recent Red Zoro competitive deck" --endpoint streaming

# Test with direct script
python local_tests/test_coordinator_direct.py "I want a recent Red Zoro competitive deck"
```

Test the card search endpoint:

```bash
python local_tests/test_card_search_local.py "OP03-001 Roronoa Zoro"
```

Test the weather endpoint:

```bash
python test_weather_streaming.py "Seattle"
```

### Docker Testing

Run the application in a Docker container:

```bash
# Windows
./local_tests/run_coordinator_docker.ps1

# Unix
./local_tests/run_coordinator_docker.sh
```

## Deployment

The application is deployed to AWS Fargate using CDK.

### Prerequisites

- AWS CDK installed
- AWS CLI configured with appropriate permissions
- Node.js and npm installed

### Setting Up Parameters in AWS Parameter Store

Before deploying, you need to set up the required parameters in AWS Parameter Store. Use the provided scripts:

```bash
# Windows
./setup_parameter_store.ps1

# Unix
chmod +x setup_parameter_store.sh
./setup_parameter_store.sh
```

These scripts will prompt you for your Perplexity API key and store it securely in AWS Parameter Store.

### Deploying to AWS

Use the provided deployment scripts to deploy the application to AWS:

```bash
# Windows
./deploy.ps1

# Unix
chmod +x deploy.sh
./deploy.sh
```

These scripts will:
1. Check if the required parameters are set up in AWS Parameter Store
2. Install dependencies
3. Bootstrap CDK (if needed)
4. Deploy the application to AWS Fargate
5. Test the deployed endpoints

After deployment, the script will output the endpoint URL of your deployed application.

### Testing the Deployed Application

The deployment scripts automatically test the deployed endpoints. You can also manually test them:

```bash
# Test the health endpoint
curl http://your-endpoint-url/health

# Test the coordinator endpoint
curl -X POST http://your-endpoint-url/coordinator \
    -H "Content-Type: application/json" \
    -d '{"prompt": "Tell me about the OP03-001 Roronoa Zoro card"}'

# Test the coordinator streaming endpoint
curl -X POST http://your-endpoint-url/coordinator-streaming \
    -H "Content-Type: application/json" \
    -d '{"prompt": "Tell me about the OP03-001 Roronoa Zoro card"}'
```

## Security Best Practices

### AWS Authentication

This project uses a centralized approach to AWS authentication to ensure consistent access across all parts of the application. See [AWS_AUTHENTICATION.md](AWS_AUTHENTICATION.md) for detailed documentation on:

- Centralized AWS configuration module
- Comprehensive task role for Fargate deployment
- AWS profiles for local development
- Troubleshooting AWS access issues

### Handling Secrets

⚠️ **IMPORTANT**: Never hardcode secrets in your source code, even for development or testing purposes.

Follow these best practices for handling secrets:

1. **Use environment variables** for local development:
   ```
   # Store in .env file (which is in .gitignore)
   PERPLEXITY_API_KEY=your-api-key
   ```
2. **Use AWS Parameter Store** for production:
   ```bash
   aws ssm put-parameter \
       --name "/tcg-agent/production/perplexity/api-key" \
       --value "your-api-key" \
       --type "SecureString" \
       --overwrite
   ```
3. **Use the centralized AWS configuration** to access parameters:
   ```python
   from utils.aws_config import aws_config
   api_key = aws_config.get_parameter("/tcg-agent/production/perplexity/api-key")
   ```
4. **Use placeholder values** in example code and documentation
5. **Regularly rotate** API keys and other secrets
6. **Set up Git pre-commit hooks** to prevent committing secrets (consider using tools like `git-secrets` or `detect-secrets`)
7. **Monitor for exposed secrets** using GitHub's secret scanning or similar tools

### Error Handling

The application includes robust error handling with CloudWatch logging. If the card research agent fails, detailed error information is logged to CloudWatch, including:

- Error type
- Error message
- Query parameters
- Stack trace

## License

This project is licensed under the MIT License - see the LICENSE file for details.
