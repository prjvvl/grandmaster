import os

# Get base directory (container's working directory)
BASE_DIR = os.environ.get("GRANDMASTER_BASE_DIR", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PATHS = {
    "hello-world": os.path.join(BASE_DIR, "hello-world")
}

DEFAULT_CONFIG = {
    "hello-world": {
        "name": "Hello World App",
        "description": "A simple app that prints 'Hello, World!'",
        "start_cmd": f'bash {os.path.join(PATHS["hello-world"], "start.sh")}',
        "stop_cmd": f'bash {os.path.join(PATHS["hello-world"], "stop.sh")}',
        "working_dir": PATHS["hello-world"],
        "auto_start": True,
        "env": {}
    }
}

def load_configs():
    return DEFAULT_CONFIG