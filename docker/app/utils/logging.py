import logging
import os
import json
from datetime import datetime

def get_logger(name):
    """Configure and return a logger with the given name."""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # Clear existing handlers
    if logger.handlers:
        logger.handlers.clear()
    
    # Add console handler for local development
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Add CloudWatch handler in production
    if os.environ.get("ENVIRONMENT") == "production":
        try:
            import watchtower
            cloudwatch_handler = watchtower.CloudWatchLogHandler(
                log_group="TCGAssistant",
                stream_name=f"{name}-{datetime.now().strftime('%Y-%m-%d')}",
                boto3_client=boto3.client('logs', region_name='us-east-1')
            )
            cloudwatch_handler.setFormatter(formatter)
            logger.addHandler(cloudwatch_handler)
        except Exception as e:
            logger.error(f"Failed to set up CloudWatch logging: {str(e)}")
    
    return logger

def log_structured_event(logger, event_type, data):
    """Log a structured event with consistent formatting."""
    event = {
        "event_type": event_type,
        "timestamp": datetime.utcnow().isoformat(),
        "data": data
    }
    logger.info(json.dumps(event))
