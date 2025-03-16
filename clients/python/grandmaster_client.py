"""
Grandmaster WebSocket Client for Python applications.
"""

import asyncio
import json
import logging
import os
import signal
import time
from typing import Any, Callable, Dict, Optional, Union

import websockets


class GrandmasterClient:
    """
    Client for connecting to the Grandmaster WebSocket server.
    """

    def __init__(
        self,
        url: str = None,
        app_name: str = None,
        on_connect: Callable = None,
        on_message: Callable = None,
        on_error: Callable = None,
        on_close: Callable = None,
        reconnect_interval: float = 5.0,
        max_reconnect_attempts: int = 10,
        log_level: str = "INFO",
    ):
        """
        Initialize the Grandmaster client.
        
        Args:
            url: WebSocket server URL (default: from env or ws://grandmaster:8765)
            app_name: Application name (default: from env or 'python-app')
            on_connect: Callback function when connected
            on_message: Callback function when message received
            on_error: Callback function when error occurs
            on_close: Callback function when connection closes
            reconnect_interval: Reconnect interval in seconds
            max_reconnect_attempts: Max reconnect attempts
            log_level: Logging level
        """
        self.url = url or os.environ.get("GRANDMASTER_URL", "ws://grandmaster:8765")
        self.app_name = app_name or os.environ.get("APP_NAME", "python-app")
        self.on_connect = on_connect
        self.on_message = on_message
        self.on_error = on_error
        self.on_close = on_close
        self.reconnect_interval = reconnect_interval
        self.max_reconnect_attempts = max_reconnect_attempts
        
        # Setup logging
        self.logger = logging.getLogger("grandmaster-client")
        self.logger.setLevel(getattr(logging, log_level))
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s'))
            self.logger.addHandler(handler)
        
        self.websocket = None
        self.reconnect_count = 0
        self.connected = False
        self.running = False
        self.loop = None

    async def connect(self):
        """Connect to the Grandmaster server."""
        self.running = True
        
        while self.running and self.reconnect_count < self.max_reconnect_attempts:
            try:
                self.logger.info(f"Connecting to Grandmaster at {self.url}...")
                
                async with websockets.connect(self.url) as websocket:
                    self.websocket = websocket
                    self.connected = True
                    self.reconnect_count = 0
                    self.logger.info(f"Connected to Grandmaster")
                    
                    # Send initial connection message
                    await self.send(f"✅ App connected: {self.app_name}")
                    
                    # Call on_connect callback
                    if self.on_connect:
                        if asyncio.iscoroutinefunction(self.on_connect):
                            await self.on_connect()
                        else:
                            self.on_connect()
                    
                    # Start the message listener
                    await self._listen_for_messages()
            
            except (websockets.exceptions.ConnectionClosed, 
                    websockets.exceptions.ConnectionError,
                    OSError) as e:
                self.connected = False
                self.websocket = None
                
                if self.on_error:
                    if asyncio.iscoroutinefunction(self.on_error):
                        await self.on_error(e)
                    else:
                        self.on_error(e)
                
                self.logger.warning(f"Connection error: {e}")
                
                if self.running:
                    self.reconnect_count += 1
                    if self.reconnect_count < self.max_reconnect_attempts:
                        retry_in = self.reconnect_interval * (2 ** min(self.reconnect_count - 1, 5))
                        self.logger.info(f"Reconnecting ({self.reconnect_count}/{self.max_reconnect_attempts}) in {retry_in:.1f}s...")
                        await asyncio.sleep(retry_in)
                    else:
                        self.logger.error("Max reconnect attempts reached")
                        break
            
            except Exception as e:
                self.logger.error(f"Unexpected error: {e}")
                if self.on_error:
                    if asyncio.iscoroutinefunction(self.on_error):
                        await self.on_error(e)
                    else:
                        self.on_error(e)
                break
        
        self.connected = False
        self.websocket = None
        
        if self.on_close:
            if asyncio.iscoroutinefunction(self.on_close):
                await self.on_close()
            else:
                self.on_close()

    async def _listen_for_messages(self):
        """Listen for messages from the server."""
        async for message in self.websocket:
            try:
                data = json.loads(message)
            except json.JSONDecodeError:
                data = {"content": message}
            
            self.logger.debug(f"Received message: {data}")
            
            if self.on_message:
                if asyncio.iscoroutinefunction(self.on_message):
                    await self.on_message(data)
                else:
                    self.on_message(data)

    async def send(self, content: str, additional_data: Dict[str, Any] = None) -> bool:
        """
        Send a message to Grandmaster.
        
        Args:
            content: Message content
            additional_data: Additional data to include
            
        Returns:
            True if the message was sent successfully, False otherwise
        """
        if not self.connected or not self.websocket:
            return False
        
        try:
            message = {
                "app": self.app_name,
                "content": content,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z")
            }
            
            if additional_data:
                message.update(additional_data)
            
            await self.websocket.send(json.dumps(message))
            self.logger.debug(f"Sent message: {content}")
            return True
        
        except Exception as e:
            self.logger.error(f"Error sending message: {e}")
            return False

    async def disconnect(self):
        """Disconnect from the Grandmaster server."""
        self.running = False
        
        if self.connected and self.websocket:
            try:
                # Send goodbye message
                await self.send(f"🔌 App disconnecting: {self.app_name}")
                
                # Close the connection
                await self.websocket.close()
            except Exception as e:
                self.logger.error(f"Error during disconnect: {e}")
        
        self.connected = False
        self.websocket = None
        self.logger.info("Disconnected from Grandmaster")

    def start(self):
        """Start the client in the current event loop."""
        self.loop = asyncio.get_event_loop()
        
        # Set up signal handlers
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                self.loop.add_signal_handler(sig, lambda s=sig: self._handle_signal(s))
            except NotImplementedError:
                # Windows doesn't support add_signal_handler
                signal.signal(sig, lambda s, f: self._handle_signal(s))
        
        try:
            self.loop.run_until_complete(self.connect())
        except Exception as e:
            self.logger.error(f"Error in event loop: {e}")
    
    def _handle_signal(self, sig):
        """Handle termination signals."""
        self.logger.info(f"Received signal {sig}, shutting down...")
        if self.loop and self.loop.is_running():
            asyncio.create_task(self.disconnect())
            self.loop.call_later(2, self.loop.stop)

    def __enter__(self):
        """Start the client when used as context manager."""
        self.running = True
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Disconnect when exiting context manager."""
        if self.loop and self.loop.is_running():
            self.loop.create_task(self.disconnect())
        else:
            asyncio.run(self.disconnect())