"""
Configuration module for Grandmaster.
Handles application configurations and environment settings.
"""

import os
import json
import logging
from typing import Dict, Any, Optional

# Get base directory (container's working directory)
BASE_DIR = os.environ.get("GRANDMASTER_BASE_DIR", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Directory paths
CONFIG_DIR = os.path.join(BASE_DIR, "config")
EXAMPLES_DIR = os.path.join(BASE_DIR, "examples")

# Ensure config directory exists
os.makedirs(CONFIG_DIR, exist_ok=True)

# Example applications paths
APP_PATHS = {
    "js-simple-app": os.path.join(EXAMPLES_DIR, "js-simple-app"),
    "py-monitor-app": os.path.join(EXAMPLES_DIR, "py-monitor-app")
}

# Default application configurations
DEFAULT_CONFIG: Dict[str, Dict[str, Any]] = {
    "js-simple-app": {
        "name": "JavaScript Simple App",
        "description": "A simple JS application that connects to Grandmaster",
        "start_cmd": "docker-compose up -d js-simple-app",
        "stop_cmd": "docker-compose stop js-simple-app",
        "working_dir": BASE_DIR,
        "auto_start": True,
        "status": "stopped",  # Initial status
        "env": {},
        "type": "docker"  # This is a Docker-managed app
    },
    "py-monitor-app": {
        "name": "Python Monitoring App",
        "description": "A Python monitoring application that reports system metrics",
        "start_cmd": "docker-compose up -d py-monitor-app",
        "stop_cmd": "docker-compose stop py-monitor-app",
        "working_dir": BASE_DIR,
        "auto_start": True,
        "status": "stopped",  # Initial status
        "env": {},
        "type": "docker"  # This is a Docker-managed app
    }
}

def get_env(key: str, default: Optional[Any] = None) -> Any:
    """
    Get environment variable with a fallback default.
    
    Args:
        key: The environment variable name
        default: Default value if the environment variable is not set
        
    Returns:
        The environment variable value or the default
    """
    return os.environ.get(key, default)

def get_config_path() -> Optional[str]:
    """
    Get the path to the custom config file.
    
    Returns:
        The path to the config file or None if it doesn't exist
    """
    config_file = os.path.join(CONFIG_DIR, "apps.json")
    if os.path.exists(config_file):
        return config_file
    return None

def load_configs() -> Dict[str, Dict[str, Any]]:
    """
    Load application configurations from config file or use defaults.
    
    Returns:
        Dictionary of application configurations
    """
    logger = logging.getLogger('grandmaster.config')
    config_path = get_config_path()
    
    # Start with default config
    merged_config = DEFAULT_CONFIG.copy()
    
    # If custom config exists, merge it with defaults
    if config_path:
        try:
            with open(config_path, 'r') as file:
                logger.info(f"Loading app configurations from {config_path}")
                custom_config = json.load(file)
                
                # Merge with defaults (custom config takes precedence)
                for app_name, app_config in custom_config.items():
                    if app_name in merged_config:
                        merged_config[app_name].update(app_config)
                    else:
                        merged_config[app_name] = app_config
                
                logger.info(f"Loaded {len(custom_config)} custom app configurations")
        except Exception as e:
            logger.error(f"Failed to load custom config: {e}")
    else:
        logger.info(f"Using default app configurations ({len(DEFAULT_CONFIG)} apps)")
    
    return merged_config

def save_configs(configs: Dict[str, Dict[str, Any]]) -> bool:
    """
    Save application configurations to file.
    
    Args:
        configs: Dictionary of application configurations
        
    Returns:
        True if saved successfully, False otherwise
    """
    logger = logging.getLogger('grandmaster.config')
    config_file = os.path.join(CONFIG_DIR, "apps.json")
    
    try:
        # Ensure config directory exists
        os.makedirs(os.path.dirname(config_file), exist_ok=True)
        
        # Write config to file
        with open(config_file, 'w') as file:
            json.dump(configs, file, indent=2)
            
        logger.info(f"Saved app configurations to {config_file}")
        return True
    except Exception as e:
        logger.error(f"Failed to save app configurations: {e}")
        return False

def get_websocket_config() -> Dict[str, Any]:
    """
    Get WebSocket server configuration.
    
    Returns:
        Dictionary with WebSocket configuration
    """
    return {
        "host": get_env("WEBSOCKET_HOST", "0.0.0.0"),
        "port": int(get_env("WEBSOCKET_PORT", "8765"))
    }