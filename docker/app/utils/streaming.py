import asyncio
import json
from typing import Dict, Any, AsyncGenerator
import logging

from .logging import get_logger

logger = get_logger("streaming")

async def stream_to_queue(queue: asyncio.Queue, event: Dict[str, Any]):
    """Stream an event to a queue."""
    try:
        await queue.put(event)
    except Exception as e:
        logger.error(f"Error streaming to queue: {str(e)}")

async def queue_to_generator(queue: asyncio.Queue) -> AsyncGenerator[str, None]:
    """Convert a queue to an async generator of JSON strings."""
    while True:
        try:
            event = await queue.get()
            yield json.dumps(event) + "\n"
            queue.task_done()
            
            # Check if this is the end event
            if event.get("complete") or event.get("error"):
                # Add a small delay to ensure all events are processed
                await asyncio.sleep(0.1)
                if queue.empty():
                    break
        except Exception as e:
            logger.error(f"Error in queue to generator: {str(e)}")
            yield json.dumps({"error": True, "message": str(e)}) + "\n"
            break
