"""
WebSocket server module for Grandmaster.
Handles connections and communication with client applications.
"""

import asyncio
import json
import logging
import os
from typing import Dict, Set, Any, Optional

import websockets
from websockets.server import WebSocketServerProtocol
from websockets.exceptions import ConnectionClosed

from .config import get_websocket_config

class AppConnection:
    """Represents a connected application."""
    
    def __init__(self, websocket: WebSocketServerProtocol, app_name: Optional[str] = None):
        """
        Initialize an app connection.
        
        Args:
            websocket: The WebSocket connection
            app_name: Optional name of the application
        """
        self.websocket = websocket
        self.app_name = app_name or "unknown"
        self.connected_at = asyncio.get_event_loop().time()
        self.last_message_at = self.connected_at
        self.remote_address = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
    
    @property
    def id(self) -> int:
        """Get the unique ID of this connection."""
        return id(self.websocket)
    
    @property
    def info(self) -> str:
        """Get a string representation of this connection."""
        return f"{self.app_name}@{self.remote_address}"
    
    @property
    def uptime(self) -> float:
        """Get the uptime of this connection in seconds."""
        return asyncio.get_event_loop().time() - self.connected_at
    
    async def send(self, message: Dict[str, Any]) -> bool:
        """
        Send a message to the application.
        
        Args:
            message: The message to send
            
        Returns:
            True if the message was sent successfully, False otherwise
        """
        try:
            await self.websocket.send(json.dumps(message))
            return True
        except Exception:
            return False


class WebSocketServer:
    """WebSocket server to communicate with apps."""

    def __init__(self, grandmaster):
        """Initialize the WebSocket server."""
        self.grandmaster = grandmaster
        self.logger = logging.getLogger('grandmaster.websocket')
        
        # Get configuration
        ws_config = get_websocket_config()
        self.host = ws_config["host"]
        self.port = ws_config["port"]
        
        self.connections: Dict[int, AppConnection] = {}
        self.server = None
        self._stopping = False

    async def start(self):
        """Start the WebSocket server."""
        self.logger.info(f"Starting WebSocket server on {self.host}:{self.port}")
        try:
            self.server = await websockets.serve(
                self._handle_connection,
                self.host,
                self.port
            )
            self.logger.info("WebSocket server started successfully")
        except OSError as e:
            self.logger.error(f"Failed to start WebSocket server: {e}")
            raise

    async def stop(self):
        """Stop the WebSocket server."""
        if self.server:
            self.logger.info("Stopping WebSocket server")
            self._stopping = True
            
            # Close all connections
            close_tasks = []
            for conn in self.connections.values():
                try:
                    close_tasks.append(conn.websocket.close(1001, "Server shutting down"))
                except Exception:
                    pass
            
            if close_tasks:
                await asyncio.gather(*close_tasks, return_exceptions=True)
            
            # Close the server
            self.server.close()
            await self.server.wait_closed()
            self.logger.info("WebSocket server stopped successfully")

    async def broadcast(self, message: Dict[str, Any]):
        """
        Broadcast a message to all connected applications.
        
        Args:
            message: The message to broadcast
        """
        if not self.connections:
            return
        
        self.logger.debug(f"Broadcasting message to {len(self.connections)} clients")
        
        tasks = []
        for conn in self.connections.values():
            tasks.append(conn.send(message))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        failed = sum(1 for r in results if r is not True)
        
        if failed:
            self.logger.warning(f"Failed to send broadcast message to {failed} clients")

    async def _handle_connection(self, websocket: WebSocketServerProtocol, path: str):
        """
        Handle a WebSocket client app connection.
        
        Args:
            websocket: The WebSocket connection
            path: The connection path
        """
        conn = AppConnection(websocket)
        
        try:
            # Register the connection
            self.connections[conn.id] = conn
            self.logger.info(f"New connection: {conn.info}")
            
            # Listen for messages
            async for message in websocket:
                if self._stopping:
                    break
                
                try:
                    # Parse the JSON message
                    data = json.loads(message)
                    
                    # Update app name if provided
                    if 'app' in data and isinstance(data['app'], str):
                        conn.app_name = data['app']
                        self.logger.info(f"Connection {conn.id} identified as '{conn.app_name}'")
                    
                    # Update last message timestamp
                    conn.last_message_at = asyncio.get_event_loop().time()
                    
                    # Extract and relay content
                    if 'content' in data:
                        content = data['content']
                        self.logger.info(f"Received from {conn.info}: {content}")
                        
                        # Format message for Telegram
                        formatted_message = f"📨 Message from {conn.app_name}:\n{content}"
                        await self.grandmaster.send_message(formatted_message, "bunker")
                    else:
                        self.logger.warning(f"Message from {conn.info} has no 'content' field")
                
                except json.JSONDecodeError:
                    self.logger.error(f"Invalid JSON received from {conn.info}")
        
        except ConnectionClosed:
            self.logger.info(f"Connection closed: {conn.info}")
        
        except Exception as e:
            self.logger.error(f"Error handling connection {conn.info}: {str(e)}")
        
        finally:
            # Remove connection from registry
            if conn.id in self.connections:
                del self.connections[conn.id]
                self.logger.info(f"Connection removed: {conn.info}")
                
    def get_status(self) -> Dict[str, Any]:
        """
        Get the current status of the WebSocket server.
        
        Returns:
            Dictionary with status information
        """
        connections_info = []
        for conn in self.connections.values():
            connections_info.append({
                "app": conn.app_name,
                "remote": conn.remote_address,
                "uptime": int(conn.uptime),
                "last_message": int(conn.last_message_at)
            })
            
        return {
            "active": self.server is not None,
            "host": self.host,
            "port": self.port,
            "connections": len(self.connections),
            "connections_info": connections_info
        }