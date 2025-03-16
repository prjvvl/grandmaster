# src/main.py
import asyncio
import logging
import os
import sys
from typing import Optional

from dotenv import load_dotenv

# Ensure the src package is in the path
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

from src.grandmaster import Grandmaster


async def main(config_path: Optional[str] = None):
    """Main entry point for the Grandmaster application."""
    # Load environment variables if config path is provided
    if config_path:
        load_dotenv(config_path)
    
    # Create and start Grandmaster
    try:
        grandmaster = Grandmaster(config_path)
        await grandmaster.start()
        
        # Keep the application running
        while True:
            await asyncio.sleep(1)
    
    except KeyboardInterrupt:
        logging.info("Received keyboard interrupt, shutting down...")
    
    except Exception as e:
        logging.error(f"Error in main process: {str(e)}")
    
    finally:
        # Ensure proper cleanup
        try:
            await grandmaster.stop()
        except Exception as e:
            logging.error(f"Error during shutdown: {str(e)}")


if __name__ == "__main__":
    # Get configuration path from command line arguments
    config_path = sys.argv[1] if len(sys.argv) > 1 else ".env"
    
    # Run the main function
    asyncio.run(main(config_path))