"""
Grandmaster orchestration core module.
Serves as the central hub for managing applications and communication.
"""

import asyncio
import logging
import os
import signal
import sys
import time
import json
import subprocess
from typing import Dict, List, Any, Optional, Callable, Tuple

from dotenv import load_dotenv

from .telegram_client import TelegramClient
from .websocket_server import WebSocketServer
from .utils import setup_logging, format_timedelta, safe_execute_shell_cmd
from .config import load_configs, save_configs, get_env


class Grandmaster:
    """
    Grandmaster class that orchestrates all components and serves as the central hub.
    """

    def __init__(self, config_path: str = ".env"):
        """
        Initialize the Grandmaster instance.
        
        Args:
            config_path: Path to the configuration file
        """
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
        
        # Track running apps and their status
        self.running_apps = {}
        self.start_time = time.time()
        
        # Load runtime configuration
        self.container_mode = os.path.exists('/.dockerenv')
        self.logger.info(f"Running in container mode: {self.container_mode}")
        
    async def start(self):
        """Start all components and autostart configured applications."""
        self.logger.info("Starting Grandmaster...")
        
        # Start the WebSocket server first
        try:
            await self.websocket_server.start()
        except Exception as e:
            self.logger.error(f"Failed to start WebSocket server: {e}")
            raise RuntimeError(f"Failed to start WebSocket server: {e}")
        
        # Start the Telegram client
        try:
            await self.telegram.start()
        except Exception as e:
            self.logger.error(f"Failed to start Telegram client: {e}")
            # Continue even if Telegram fails - it's not critical for core functionality
        
        # Send startup notification
        await self.send_message("🔥 Grandmaster has awakened 🔥", "bunker")
        
        self.logger.info("Grandmaster started successfully.")
        
        # Autostart applications
        await self._autostart_apps()

    async def stop(self):
        """Stop all components and perform cleanup."""
        self.logger.info("Stopping Grandmaster...")
        
        # First stop all running applications
        stop_tasks = []
        for app_name in list(self.running_apps.keys()):
            stop_tasks.append(self.stop_app(app_name))
        
        if stop_tasks:
            self.logger.info(f"Stopping {len(stop_tasks)} running applications")
            await asyncio.gather(*stop_tasks, return_exceptions=True)
        
        # Stop WebSocket server
        try:
            await self.websocket_server.stop()
        except Exception as e:
            self.logger.error(f"Error stopping WebSocket server: {e}")
        
        # Send shutdown notification
        await self.send_message("❄️ Grandmaster has gone cold ❄️", "bunker")
        
        # Finally stop Telegram
        try:
            await self.telegram.stop()
        except Exception as e:
            self.logger.error(f"Error stopping Telegram client: {e}")
        
        self.logger.info("Grandmaster stopped successfully.")

    async def _autostart_apps(self):
        """Start apps that are configured to auto-start."""
        autostart_tasks = []
        
        for app_name, config in self.app_configs.items():
            if config.get("auto_start", False):
                self.logger.info(f"Auto-starting app: {app_name}")
                autostart_tasks.append(self.start_app(app_name))
        
        if autostart_tasks:
            results = await asyncio.gather(*autostart_tasks, return_exceptions=True)
            success_count = sum(1 for r in results if r is True)
            self.logger.info(f"Auto-started {success_count}/{len(autostart_tasks)} applications")
    
    async def start_app(self, app_name: str) -> bool:
        """
        Start an application by name.
        
        Args:
            app_name: The name of the application to start
            
        Returns:
            True if the application was started successfully, False otherwise
        """
        if app_name not in self.app_configs:
            self.logger.error(f"App '{app_name}' not found in configuration")
            return False
        
        # Check if app is already running
        if app_name in self.running_apps:
            self.logger.warning(f"App '{app_name}' is already running")
            return True
        
        app = self.app_configs[app_name]
        try:
            self.logger.info(f"Starting app: {app_name}")
            await self.send_message(f"🚀 Starting app: {app['name']}", "bunker")
            
            # Handle Docker and non-Docker apps differently
            app_type = app.get("type", "process")
            
            if app_type == "docker" and self.container_mode:
                # In Docker mode, we use Docker Compose commands
                self.logger.info(f"Starting Docker app: {app_name}")
                result = await self._start_docker_app(app_name, app)
            else:
                # Traditional process-based app
                self.logger.info(f"Starting process app: {app_name}")
                result = await self._start_process_app(app_name, app)
            
            if not result:
                return False
            
            # Update app status
            self.app_configs[app_name]["status"] = "running"
            self.running_apps[app_name] = {
                "started_at": time.time(),
                "status": "running",
                "type": app_type
            }
            
            # Save updated configuration
            save_configs(self.app_configs)
            
            self.logger.info(f"App started successfully: {app_name}")
            await self.send_message(f"✅ App started: {app['name']}", "bunker")
            return True
            
        except Exception as e:
            self.logger.error(f"Exception while starting app {app_name}: {e}")
            error_msg = str(e)
            await self.send_message(f"❌ Error starting app: {app['name']}\n\n{error_msg}", "bunker")
            return False
    
    async def _start_docker_app(self, app_name: str, app_config: Dict[str, Any]) -> bool:
        """Start a Docker-managed application."""
        try:
            command = app_config["start_cmd"]
            working_dir = app_config["working_dir"]
            
            # Execute the command
            result = await asyncio.to_thread(
                safe_execute_shell_cmd,
                command,
                working_dir,
                timeout=60
            )
            
            if not result['success']:
                error_msg = result['stderr'] or "Unknown error"
                self.logger.error(f"Failed to start Docker app {app_name}: {error_msg}")
                await self.send_message(
                    f"❌ Failed to start Docker app: {app_config['name']}\n\n{error_msg}", 
                    "bunker"
                )
                return False
                
            return True
        except Exception as e:
            self.logger.error(f"Error starting Docker app {app_name}: {e}")
            return False
    
    async def _start_process_app(self, app_name: str, app_config: Dict[str, Any]) -> bool:
        """Start a process-based application."""
        try:
            # Execute the start command
            result = await asyncio.to_thread(
                safe_execute_shell_cmd,
                app_config["start_cmd"],
                app_config["working_dir"],
                timeout=60,
                env={**os.environ, **app_config.get("env", {})}
            )
            
            if not result['success']:
                error_msg = result['stderr'] or "Unknown error"
                self.logger.error(f"Failed to start app {app_name}: {error_msg}")
                await self.send_message(f"❌ Failed to start app: {app_config['name']}\n\n{error_msg}", "bunker")
                return False
                
            return True
        except Exception as e:
            self.logger.error(f"Error starting process app {app_name}: {e}")
            return False

    async def stop_app(self, app_name: str) -> bool:
        """
        Stop an application by name.
        
        Args:
            app_name: The name of the application to stop
            
        Returns:
            True if the application was stopped successfully, False otherwise
        """
        if app_name not in self.app_configs:
            self.logger.error(f"App '{app_name}' not found in configuration")
            return False
        
        # Check if app is not running
        if app_name not in self.running_apps:
            self.logger.warning(f"App '{app_name}' is not running")
            return True
        
        app = self.app_configs[app_name]
        app_type = app.get("type", "process")
        
        try:
            self.logger.info(f"Stopping app: {app_name}")
            await self.send_message(f"🛑 Stopping app: {app['name']}", "bunker")
            
            # Handle Docker and non-Docker apps differently
            if app_type == "docker" and self.container_mode:
                # Docker-managed app
                result = await self._stop_docker_app(app_name, app)
            else:
                # Process-based app
                result = await self._stop_process_app(app_name, app)
            
            if not result:
                return False
            
            # Update app status
            self.app_configs[app_name]["status"] = "stopped"
            if app_name in self.running_apps:
                del self.running_apps[app_name]
            
            # Save updated configuration
            save_configs(self.app_configs)
            
            self.logger.info(f"App stopped successfully: {app_name}")
            await self.send_message(f"✅ App stopped: {app['name']}", "bunker")
            return True
            
        except Exception as e:
            self.logger.error(f"Exception while stopping app {app_name}: {e}")
            error_msg = str(e)
            await self.send_message(f"❌ Error stopping app: {app['name']}\n\n{error_msg}", "bunker")
            return False
    
    async def _stop_docker_app(self, app_name: str, app_config: Dict[str, Any]) -> bool:
        """Stop a Docker-managed application."""
        try:
            command = app_config["stop_cmd"]
            working_dir = app_config["working_dir"]
            
            # Execute the command
            result = await asyncio.to_thread(
                safe_execute_shell_cmd,
                command,
                working_dir,
                timeout=60
            )
            
            if not result['success']:
                error_msg = result['stderr'] or "Unknown error"
                self.logger.error(f"Failed to stop Docker app {app_name}: {error_msg}")
                await self.send_message(
                    f"❌ Failed to stop Docker app: {app_config['name']}\n\n{error_msg}", 
                    "bunker"
                )
                return False
                
            return True
        except Exception as e:
            self.logger.error(f"Error stopping Docker app {app_name}: {e}")
            return False
    
    async def _stop_process_app(self, app_name: str, app_config: Dict[str, Any]) -> bool:
        """Stop a process-based application."""
        try:
            # Execute the stop command
            result = await asyncio.to_thread(
                safe_execute_shell_cmd,
                app_config["stop_cmd"],
                app_config["working_dir"],
                timeout=60
            )
            
            if not result['success']:
                error_msg = result['stderr'] or "Unknown error"
                self.logger.error(f"Failed to stop app {app_name}: {error_msg}")
                await self.send_message(f"❌ Failed to stop app: {app_config['name']}\n\n{error_msg}", "bunker")
                return False
                
            return True
        except Exception as e:
            self.logger.error(f"Error stopping process app {app_name}: {e}")
            return False
            
    async def restart_app(self, app_name: str) -> bool:
        """
        Restart an application by name.
        
        Args:
            app_name: The name of the application to restart
            
        Returns:
            True if the application was restarted successfully, False otherwise
        """
        self.logger.info(f"Restarting app: {app_name}")
        
        # Stop the app if it's running
        if app_name in self.running_apps:
            stop_success = await self.stop_app(app_name)
            if not stop_success:
                self.logger.warning(f"Failed to stop app {app_name} during restart")
                # Continue anyway to try starting it
        
        # Give it a moment to fully stop
        await asyncio.sleep(2)
        
        # Start the app
        return await self.start_app(app_name)
    
    def get_app_status(self, app_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get the status of a specific app or all apps.
        
        Args:
            app_name: Optional app name to get status for
            
        Returns:
            Dictionary with app status information
        """
        if app_name:
            if app_name not in self.app_configs:
                return {"error": f"App '{app_name}' not found"}
            
            app_info = self.app_configs[app_name].copy()
            
            # Add runtime information if the app is running
            if app_name in self.running_apps:
                app_info["running"] = True
                app_info["uptime"] = format_timedelta(time.time() - self.running_apps[app_name]["started_at"])
            else:
                app_info["running"] = False
                app_info["uptime"] = None
                
            return app_info
        else:
            # Return status for all apps
            result = {}
            for name, config in self.app_configs.items():
                app_info = config.copy()
                
                # Add runtime information if the app is running
                if name in self.running_apps:
                    app_info["running"] = True
                    app_info["uptime"] = format_timedelta(time.time() - self.running_apps[name]["started_at"])
                else:
                    app_info["running"] = False
                    app_info["uptime"] = None
                    
                result[name] = app_info
                
            return result
    
    async def register_app(self, app_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Register a new application with Grandmaster.
        
        Args:
            app_info: Application information
            
        Returns:
            Response with success status and details
        """
        app_name = app_info.get("app_name")
        if not app_name:
            return {"success": False, "error": "Missing app_name"}
            
        # Check if app already exists
        if app_name in self.app_configs:
            return {"success": False, "error": f"App '{app_name}' already exists"}
            
        # Create app configuration
        app_config = {
            "name": app_info.get("name", app_name),
            "description": app_info.get("description", ""),
            "start_cmd": app_info.get("start_cmd", ""),
            "stop_cmd": app_info.get("stop_cmd", ""),
            "working_dir": app_info.get("working_dir", "/"),
            "auto_start": app_info.get("auto_start", False),
            "status": "stopped",
            "env": app_info.get("env", {}),
            "type": app_info.get("type", "process")
        }
        
        # Add to configurations
        self.app_configs[app_name] = app_config
        
        # Save configurations
        if save_configs(self.app_configs):
            self.logger.info(f"Registered new app: {app_name}")
            await self.send_message(f"➕ Registered new app: {app_config['name']}", "bunker")
            return {"success": True, "app": app_config}
        else:
            self.logger.error(f"Failed to save config after registering app: {app_name}")
            return {"success": False, "error": "Failed to save configuration"}
    
    async def unregister_app(self, app_name: str) -> Dict[str, Any]:
        """
        Unregister an application from Grandmaster.
        
        Args:
            app_name: Name of the application to unregister
            
        Returns:
            Response with success status and details
        """
        # Check if app exists
        if app_name not in self.app_configs:
            return {"success": False, "error": f"App '{app_name}' not found"}
            
        # Stop the app if it's running
        if app_name in self.running_apps:
            await self.stop_app(app_name)
            
        # Remove from configurations
        app_config = self.app_configs.pop(app_name)
        
        # Save configurations
        if save_configs(self.app_configs):
            self.logger.info(f"Unregistered app: {app_name}")
            await self.send_message(f"➖ Unregistered app: {app_config['name']}", "bunker")
            return {"success": True}
        else:
            # Restore app config
            self.app_configs[app_name] = app_config
            self.logger.error(f"Failed to save config after unregistering app: {app_name}")
            return {"success": False, "error": "Failed to save configuration"}
    
    async def send_message(self, content: str, channel: str, media_type: Optional[str] = None, media_path: Optional[str] = None, parse_mode: Optional[str] = None):
        """
        Send a message to the specified Telegram channel.
        
        Args:
            content: The message content
            channel: The channel to send to
            media_type: Optional media type
            media_path: Optional path to media file
            parse_mode: Optional parsing mode
            
        Returns:
            Response from the Telegram API or None
        """
        try:
            return await self.telegram.send_message(content, channel, media_type, media_path, parse_mode)
        except Exception as e:
            self.logger.error(f"Failed to send message to channel {channel}: {e}")
            return None
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get the current status of the Grandmaster service.
        
        Returns:
            Dictionary with status information
        """
        ws_status = self.websocket_server.get_status()
        
        return {
            "uptime": format_timedelta(time.time() - self.start_time),
            "container_mode": self.container_mode,
            "apps": {
                "total": len(self.app_configs),
                "running": len(self.running_apps)
            },
            "websocket": ws_status
        }