# Deploy to Fargate

This project deploys a FastAPI application to AWS Fargate using AWS CDK.

## Project Structure

The project is organized with the following directory structure:

```
deploy_to_fargate/
├── README.md                 # Project documentation
├── .gitignore                # Git ignore file
├── infrastructure/           # All CDK/infrastructure code
│   ├── cdk.json              # CDK configuration
│   ├── package.json          # NPM package definition
│   ├── package-lock.json     # NPM lock file
│   ├── tsconfig.json         # TypeScript configuration
│   ├── bin/                  # CDK app entry point
│   └── lib/                  # CDK stack definition
├── src/                      # Application source code
│   ├── app/                  # Main application code
│   │   ├── app.py            # FastAPI application
│   │   ├── card_researcher.py # Card researcher module
│   │   ├── coordinator_agent.py # Coordinator agent module
│   │   └── utils/            # Utility modules
│   ├── Dockerfile            # Docker container definition
│   └── requirements.txt      # Python dependencies
├── scripts/                  # Deployment and utility scripts
└── tests/                    # All test files
    ├── local_tests/          # Local testing scripts
    ├── unit_tests/           # Unit tests
    └── integration_tests/    # Integration tests
```

## Application Overview

This application provides several API endpoints:

- `/health`: Health check endpoint
- `/weather` and `/weather-streaming`: Weather information endpoints
- `/card-search` and `/card-search-streaming`: Card search endpoints using Perplexity API
- `/coordinator` and `/coordinator-streaming`: Coordinator agent endpoints

## Development

### Local Development

To run the application locally:

1. Set up environment variables in a `.env` file
2. Run the application using Docker:

```bash
cd src
docker build -t tcg-agent .
docker run -p 8000:8000 --env-file ../.env tcg-agent
```

### Testing

Tests are located in the `tests` directory:

- `tests/local_tests`: Scripts for local testing
- `tests/unit_tests`: Unit tests
- `tests/integration_tests`: Integration tests

## Deployment

To deploy the application to AWS:

1. Install dependencies:

```bash
cd infrastructure
npm install
```

2. Deploy the CDK stack:

```bash
cd infrastructure
npx cdk deploy
```

## Configuration

The application can be configured using:

- Environment variables
- AWS Parameter Store parameters
