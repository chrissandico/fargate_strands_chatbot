# AWS Configuration Module

This module provides centralized AWS configuration and client management for the TCG Agent application.

## Overview

The `aws_config.py` module implements a singleton pattern to ensure consistent AWS client configuration across the entire application. It provides:

- Centralized client initialization for all AWS services
- Consistent credential management
- Support for both local development and production environments
- Logging of AWS identity for debugging

## Usage

### Basic Usage

Import the pre-initialized instance:

```python
from utils.aws_config import aws_config

# Get a Bedrock client
bedrock_client = aws_config.get_bedrock_client()

# Use the client
response = bedrock_client.invoke_model(...)
```

### Getting Parameters from SSM

```python
from utils.aws_config import aws_config

# Get a parameter
api_key = aws_config.get_parameter("/tcg-agent/production/perplexity/api-key")

# Use the parameter
if api_key:
    # Do something with the API key
    pass
```

## AWS Credentials

The module uses the AWS SDK's default credential provider chain, which looks for credentials in the following order:

1. Environment variables (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`)
2. Shared credential file (`~/.aws/credentials`)
3. AWS profile specified by `AWS_PROFILE` environment variable
4. EC2 Instance Profile or ECS Task Role

For local development, use the provided setup scripts:
- `setup_aws_profile.sh` (Linux/macOS)
- `setup_aws_profile.ps1` (Windows)

These scripts create an AWS profile with the same permissions as the production environment.

## Adding New AWS Services

To add support for a new AWS service, extend the `AWSConfig` class:

```python
# In aws_config.py
def get_dynamodb_client(self):
    """Get or create a DynamoDB client."""
    if not hasattr(self, '_dynamodb_client'):
        logger.info("Creating DynamoDB client")
        self._dynamodb_client = boto3.client('dynamodb', region_name=self.region)
    return self._dynamodb_client
```

## Troubleshooting

If you encounter AWS permission issues:

1. Check the logs for the AWS identity being used
2. Verify that your AWS profile has the necessary permissions
3. For local development, ensure you've activated the correct profile:
   - Linux/macOS: `export AWS_PROFILE=tcg-agent-dev`
   - Windows: `$env:AWS_PROFILE="tcg-agent-dev"`
4. For production, verify that the ECS Task Role has the required permissions
