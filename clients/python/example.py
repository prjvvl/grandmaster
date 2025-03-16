"""
Example of using the Grandmaster client in a Python application.
"""

import asyncio
import logging
import time
import os
import platform
import psutil
from grandmaster_client import GrandmasterClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger("example-app")

# Track application start time
start_time = time.time()

# Callback functions
async def on_connect():
    """Called when connected to Grandmaster."""
    logger.info("Connected to Grandmaster! Starting status updates...")
    
    # Schedule periodic updates
    asyncio.create_task(send_periodic_updates())

async def send_periodic_updates():
    """Send periodic status updates to Grandmaster."""
    while client.connected:
        try:
            # Get system metrics
            memory = psutil.virtual_memory()
            cpu = psutil.cpu_percent(interval=1)
            disk = psutil.disk_usage('/')
            
            # Send status update
            await client.send(
                f"Status from {client.app_name}",
                {
                    "status": "healthy",
                    "metrics": {
                        "memory_percent": memory.percent,
                        "memory_used_mb": round(memory.used / 1024 / 1024, 2),
                        "cpu_percent": cpu,
                        "disk_percent": disk.percent,
                        "uptime_seconds": round(time.time() - start_time, 1)
                    },
                    "system_info": {
                        "platform": platform.platform(),
                        "python": platform.python_version(),
                        "hostname": platform.node()
                    }
                }
            )
            logger.info(f"Status update sent. CPU: {cpu}%, Memory: {memory.percent}%")
        except Exception as e:
            logger.error(f"Error sending status update: {e}")
        
        # Wait before sending next update
        await asyncio.sleep(30)

async def on_message(message):
    """Handle messages from Grandmaster."""
    logger.info(f"Received message: {message}")
    
    # Handle commands from Grandmaster
    if isinstance(message, dict) and message.get("command"):
        command = message.get("command")
        
        if command == "restart":
            logger.info("Received restart command")
            # Implement restart logic here
            
        elif command == "status":
            # Send immediate status update
            memory = psutil.virtual_memory()
            cpu = psutil.cpu_percent(interval=0.1)
            
            await client.send(
                "Status report (on demand)", 
                {
                    "status": "responding",
                    "timestamp": time.time(),
                    "cpu": cpu,
                    "memory": memory.percent
                }
            )
        
        elif command == "ping":
            # Respond to ping
            await client.send(
                "pong",
                {
                    "responseId": message.get("id"),
                    "latency_ms": round((time.time() - float(message.get("timestamp", 0))) * 1000, 2)
                }
            )

def on_error(error):
    """Handle connection errors."""
    logger.error(f"Connection error: {error}")

def on_close():
    """Handle connection closure."""
    logger.info("Connection closed")

# Create the client
client = GrandmasterClient(
    # Configuration
    url=os.environ.get("GRANDMASTER_URL"),  # Uses environment variable or default
    app_name=os.environ.get("APP_NAME", "example-python-app"),
    reconnect_interval=5.0,
    max_reconnect_attempts=10,
    log_level="INFO",
    
    # Callbacks
    on_connect=on_connect,
    on_message=on_message,
    on_error=on_error,
    on_close=on_close
)

# Start the client
if __name__ == "__main__":
    logger.info("Starting Grandmaster client...")
    try:
        client.start()
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
    except Exception as e:
        logger.error(f"Error running client: {e}")
    finally:
        logger.info("Application shutdown")