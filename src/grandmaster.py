

import asyncio
import logging
import os
import signal
import sys
from typing import Dict, List, Any, Optional, Callable

from dotenv import load_dotenv

from .telegram_client import TelegramClient
from .websocket_server import WebSocketServer
from .utils import setup_logging
from .config import load_configs

class Grandmaster:
    """
    Grandmaster class that orchestrates all components and serves as the central hub.
    """

    def __init__(self, config_path: str = ".env"):
        """Initialize the Grandmaster instance."""
        # Load environment variables
        load_dotenv(config_path)
        
        # Setup logging
        self.logger = setup_logging(os.getenv("LOG_LEVEL", "INFO"))
        self.logger.info("Initializing Grandmaster...")
        
        # Initialize components
        self.telegram = TelegramClient(self)
        self.websocket_server = WebSocketServer(self)
        
        # Load apps configuration
        self.app_configs = load_configs()

        # Setup signal handlers for graceful shutdown
        for sig in (signal.SIGINT, signal.SIGTERM):
            signal.signal(sig, self._signal_handler)


    async def start(self):
        """Start all components."""
        self.logger.info("Starting Grandmaster...")
        
        await self.telegram.start()
        await self.websocket_server.start()

        await self.send_message("🔥 Grandmaster has awakened 🔥", "bunker")

        self.logger.info("Grandmaster started successfully.")

        await self._autostart_apps()


    async def stop(self):
        """Stop all components and perform cleanup."""
        self.logger.info("Stopping Grandmaster...")

        for app_name, config in self.app_configs.items():
            if config.get("auto_start", False):
                await self.stop_app(app_name)

        await self.websocket_server.stop()

        await asyncio.sleep(2)
        await self.send_message("❄️ Grandmaster has gone cold ❄️", "bunker")
        await asyncio.sleep(2)
        await self.telegram.stop()
        
        self.logger.info("Grandmaster stopped successfully.")    


    async def _autostart_apps(self):
        """Start apps that are configured to auto-start."""
        for app_name, config in self.app_configs.items():
            if config.get("auto_start", False):
                self.logger.info(f"Auto-starting app: {app_name}")
                await self.start_app(app_name)
    
    async def start_app(self, app_name: str):
        if app_name not in self.app_configs:
            self.logger.error(f"App '{app_name}' not found in configuration")
            return
        
        app = self.app_configs[app_name]
        try:
            self.logger.info(f"Starting app: {app_name}")
            await self.send_message(f"🚀 Starting app: {app['name']} 🚀", "bunker")

            process = await asyncio.create_subprocess_shell(
                app["start_cmd"],
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=app["working_dir"],
                env={**os.environ, **app["env"]}
            )

            stdout, stderr = await process.communicate()

            if process.returncode == 1:
                error_msg = stderr.decode() if stderr else "Unknown error"
                self.logger.error(f"Failed to execute app {app_name}: {error_msg}")
                await self.send_message(f"❌ Failed to execute app: {app['name']}", "bunker")
                return False
        
        except Exception as e:
            self.logger.error(f"Failed to start app {app_name}: {e}")
            error_msg = str(e)
            await self.send_message(f"❌ Encountered issue while processing app: {app['name']}\n\n{error_msg}", "bunker")
            return False

    async def stop_app(self, app_name: str):
        if app_name not in self.app_configs:
            self.logger.error(f"App '{app_name}' not found in configuration")
            return
        
        app = self.app_configs[app_name]
        try:
            self.logger.info(f"Stopping app: {app_name}")
            await self.send_message(f"🛑 Stopping app: {app['name']} 🛑", "bunker")

            process = await asyncio.create_subprocess_shell(
                app["stop_cmd"],
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=app["working_dir"],
                env={**os.environ, **app["env"]}
            )

            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                self.app_configs[app_name]["status"] = "stopped"
                self.logger.info(f"App stopped successfully: {app_name}")
                await self.send_message(f"✅ App stopped: {app['name']}", "bunker")
                return True
            else:
                error_msg = stderr.decode() if stderr else "Unknown error"
                self.logger.error(f"Failed to stop app {app_name}: {error_msg}")
                await self.send_message(f"❌ Failed to stop app: {app['name']}", "bunker")
                return False
        
        except Exception as e:
            self.logger.error(f"Failed to stop app {app_name}: {e}")
            await self.send_message(f"❌ Failed to stop app: {app['name']}", "bunker")
            return False
        
    async def restart_app(self, app_name: str):
        """Restart a registered application."""
        await self.stop_app(app_name)
        await asyncio.sleep(2)  # Give it a moment to fully stop
        return await self.start_app(app_name)
    
    async def send_message(self, content: str, channel: str, media_type: Optional[str] = None, media_path: Optional[str] = None, parse_mode: str = None):
        """Send a message to the specified Telegram channel."""
        return await self.telegram.send_message(content, channel, media_type, media_path, parse_mode)

    def _signal_handler(self, sig, frame):
        """Handle termination signals."""
        self.logger.info(f"Received signal {sig}, initiating shutdown...")
        loop = asyncio.get_event_loop()
        loop.create_task(self.stop())
        loop.call_later(10, lambda: sys.exit(0))  # Force exit after 10 seconds if cleanup is stuck
