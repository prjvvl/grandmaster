import asyncio
import json
import logging
import os
from typing import Dict, Set, Any

import websockets
from websockets.server import WebSocketServerProtocol

class WebSocketServer:
    """WebSocket server to communicate with apps"""

    def __init__(self, grandmaster):
        """Initialize the WebSocket server."""
        self.grandmaster = grandmaster
        self.logger = logging.getLogger('grandmaster.websocket')
        self.host = os.getenv("WEBSOCKET_HOST", "0.0.0.0")
        self.port = int(os.getenv("WEBSOCKET_PORT", "8765"))
        self.apps: Set[WebSocketServerProtocol] = set()
        self.server = None


    async def start(self):
        """Start the WebSocket server."""
        self.logger.info(f"Starting WebSocket server on {self.host}:{self.port}")
        self.server = await websockets.serve(
            self._handle_app,
            self.host,
            self.port
        )
        self.logger.info("WebSocket server started successfully")


    async def stop(self):
        """Stop the WebSocket server."""
        if self.server:
            self.logger.info("Stopping WebSocket server")
            self.server.close()
            await self.server.wait_closed()
            self.logger.info("WebSocket server stopped successfully")


    async def _handle_app(self, websocket: WebSocketServerProtocol, path: str):
        """Handle a WebSocket client app connection."""

        app_id = id(websocket)
        app_info = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"

        try:
            # Add app to connected apps
            self.apps.add(websocket)
            self.logger.info(f"App connected: {app_id} ({app_info})")
            
            # Listen for messages
            async for message in websocket:
                try:
                    # Parse the JSON message
                    data = json.loads(message)
                    self.logger.info(f"Received message from {app_info}: {data}")
                    
                    # Extract and print content
                    if 'content' in data:
                        content = data['content']
                        await self.grandmaster.send_message(content, "bunker")
                    else:
                        self.logger.warning(f"Message from {app_info} has no 'content' field")
                
                except json.JSONDecodeError:
                    self.logger.error(f"Invalid JSON received from {app_info}")
        
        except websockets.exceptions.ConnectionClosed:
            self.logger.info(f"App disconnected: {app_info}")
        
        except Exception as e:
            self.logger.error(f"Error handling app {app_info}: {str(e)}")
        
        finally:
            # Remove app from connected apps
            if websocket in self.apps:
                self.apps.remove(websocket)
                self.logger.info(f"App removed: {app_info}")