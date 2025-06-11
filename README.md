# TCG Assistant API

This project implements a Trading Card Game (TCG) Assistant API using FastAPI and Strands Agents. The API provides endpoints for weather information and card research.

## Features

### Weather Assistant
- `/weather` - Get weather information for a location
- `/weather-streaming` - Stream weather information for a location

### Card Research Assistant
- `/card-search` - Get information about a One Piece TCG card, including its ID
- `/card-search-streaming` - Stream information about a One Piece TCG card

## Architecture

The application uses a multi-agent architecture:

1. **Weather Agent**: Makes HTTP requests to the National Weather Service API to provide weather information
2. **Card Research Agent**: Uses the Perplexity MCP server to search for One Piece TCG card information

## Prerequisites

- Python 3.12+
- Docker
- AWS CLI configured with appropriate permissions
- Perplexity API key

## Local Development

### Setup

1. Clone the repository
2. Create a `.env` file with your Perplexity API key:
   ```
   PERPLEXITY_API_KEY=your-api-key
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

### Testing

Test the weather endpoint:

```bash
python test_weather_streaming.py "Seattle"
```

Test the card search endpoint:

```bash
python test_card_search_local.py "Blue Doffy Leader"
```

Options:
- `--no-stream`: Use non-streaming endpoint
- `--start-server`: Start the server automatically before testing

## Deployment

The application is deployed to AWS Fargate using CDK.

### Prerequisites

- AWS CDK installed
- AWS CLI configured with appropriate permissions

### Deploying

1. Store the Perplexity API key in AWS Parameter Store:
   ```bash
   aws ssm put-parameter \
       --name "/tcg-agent/production/perplexity/api-key" \
       --value "your-api-key" \
       --type "SecureString" \
       --overwrite
   ```

2. Deploy the CDK stack:
   ```bash
   npm install
   cdk deploy
   ```

### Testing the Deployed API

Test the deployed weather endpoint:

```bash
python test_weather_streaming.py "Seattle"
```

Test the deployed card search endpoint:

```bash
python test_card_search.py "Blue Doffy Leader"
```

## Adding More Agents

This project is designed to be extended with additional agents. Future plans include:

1. **Deck Recommendation Agent**: Provide competitive deck recommendations using the GumGum.gg API
2. **Shopping Agent**: Help users purchase cards using the Shopify MCP server

## Security Best Practices

### Handling Secrets

⚠️ **IMPORTANT**: A Perplexity API key was previously hardcoded in the codebase and exposed in the Git repository. If you're using this key, please invalidate it immediately and generate a new one.

Follow these best practices for handling secrets:

1. **Never hardcode secrets** in your source code, even for development or testing purposes
2. **Use environment variables** for local development:
   ```
   # Store in .env file (which is in .gitignore)
   PERPLEXITY_API_KEY=your-api-key
   ```
3. **Use AWS Parameter Store** for production:
   ```bash
   aws ssm put-parameter \
       --name "/tcg-agent/production/perplexity/api-key" \
       --value "your-api-key" \
       --type "SecureString" \
       --overwrite
   ```
4. **Use placeholder values** in example code and documentation
5. **Regularly rotate** API keys and other secrets
6. **Set up Git pre-commit hooks** to prevent committing secrets (consider using tools like `git-secrets` or `detect-secrets`)
7. **Monitor for exposed secrets** using GitHub's secret scanning or similar tools

### What to Do If You Accidentally Commit a Secret

1. **Invalidate the secret immediately** - generate a new API key, password, etc.
2. **Remove the secret from Git history** - this is challenging and may require force-pushing, which can disrupt team workflows
3. **Notify relevant stakeholders** about the potential exposure
4. **Review access logs** for any suspicious activity

## License

This project is licensed under the MIT License - see the LICENSE file for details.
