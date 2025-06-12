import boto3
import os
import logging
from utils.logging import get_logger

logger = get_logger("aws_config")

class AWSConfig:
    """Centralized AWS configuration and client management."""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AWSConfig, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self._initialize()
            self._initialized = True
    
    def _initialize(self):
        """Initialize AWS configuration and clients."""
        # Explicitly set region to us-east-1 to match the Inference Profile
        self.region = 'us-east-1'
        logger.info(f"Initializing AWS configuration with region: {self.region}")
        
        # Set the AWS_REGION environment variable to ensure consistency
        os.environ['AWS_REGION'] = self.region
        logger.info(f"Set AWS_REGION environment variable to: {self.region}")
        
        # Initialize clients
        self._bedrock_client = None
        self._ssm_client = None
        
        # Log AWS identity for debugging
        try:
            sts = boto3.client('sts')
            identity = sts.get_caller_identity()
            logger.info(f"AWS Identity: Account={identity['Account']}, ARN={identity['Arn']}")
        except Exception as e:
            logger.warning(f"Could not determine AWS identity: {str(e)}")
    
    def get_bedrock_client(self):
        """Get or create a Bedrock client."""
        if self._bedrock_client is None:
            logger.info("Creating Bedrock client")
            self._bedrock_client = boto3.client('bedrock-runtime', region_name=self.region)
        return self._bedrock_client
    
    def get_ssm_client(self):
        """Get or create an SSM client."""
        if self._ssm_client is None:
            logger.info("Creating SSM client")
            self._ssm_client = boto3.client('ssm', region_name=self.region)
        return self._ssm_client
    
    def get_parameter(self, parameter_name, with_decryption=True):
        """Get a parameter from SSM Parameter Store."""
        try:
            client = self.get_ssm_client()
            response = client.get_parameter(
                Name=parameter_name,
                WithDecryption=with_decryption
            )
            return response['Parameter']['Value']
        except Exception as e:
            logger.error(f"Error getting parameter {parameter_name}: {str(e)}")
            return None

# Global instance for easy import
aws_config = AWSConfig()
