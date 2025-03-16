# Grandmaster

A centralized orchestration system for managing multiple applications with WebSocket communication and Telegram control.

## Features

- Start, stop, and restart applications through a unified interface
- Control applications and receive notifications via Telegram
- WebSocket server for real-time communication with applications
- Docker integration for easy deployment
- Extensible architecture to add new managed applications

## Quick Setup

### Prerequisites

- Docker and Docker Compose
- Telegram Bot Token

### Docker Setup

1. Create `.env` file with Telegram bot tokens and channels:
   ```
   # Telegram Configuration
   TELEGRAM_BOT_TOKEN=your_telegram_bot_token
   TELEGRAM_BUNKER_CHANNEL_ID=your_logs_channel_id
   TELEGRAM_WHISPERS_CHANNEL_ID=your_general_channel_id
   
   # WebSocket Configuration
   WEBSOCKET_HOST=0.0.0.0
   WEBSOCKET_PORT=8765
   ```

2. Run Docker Compose:
   ```bash
   docker-compose up -d
   ```

## Connect Your Application

Grandmaster provides client libraries in multiple languages to make it easy to connect:

### JavaScript/Node.js

```javascript
// Install: npm install ws
const GrandmasterClient = require('./clients/javascript/grandmaster-client');

const client = new GrandmasterClient({
  url: 'ws://grandmaster:8765',
  appName: 'your-app-name'
});

client.connect();
client.send('Hello from your app!');
```

### Python

```python
# Install: pip install websockets
from clients.python.grandmaster_client import GrandmasterClient

client = GrandmasterClient(
    url='ws://grandmaster:8765', 
    app_name='your-app-name'
)
client.start()
```

## Docker Network

To connect from another container, add it to the `grandmaster-network`:

```yaml
# Your docker-compose.yaml
services:
  your-service:
    # ... other configuration
    networks:
      - grandmaster-network
    environment:
      - GRANDMASTER_URL=ws://grandmaster:8765

networks:
  grandmaster-network:
    external: true
```

## WebSocket Protocol

Applications send JSON messages with:
```json
{
  "app": "app-name",
  "content": "Message content",
  "timestamp": "2025-03-16T12:34:56Z" 
}
```

## Folder Structure

```
grandmaster/
├── Dockerfile                   # Main container
├── docker-compose.yaml          # Services configuration
├── requirements.txt             # Python dependencies
├── .env                         # Environment variables
│
├── src/                         # Core code
│   ├── grandmaster.py           # Main orchestrator
│   ├── websocket_server.py      # WebSocket server
│   └── ... other modules
│
├── clients/                     # Client libraries
│   ├── javascript/              # JS client
│   └── python/                  # Python client
│
├── examples/                    # Example apps
│   ├── js-simple-app/           # Simple JS app
│   └── py-monitor-app/          # Python monitor
│
└── logs/                        # Log files
```

## Examples

The repository includes two example applications:

1. **js-simple-app**: A simple JavaScript application that sends periodic heartbeats
2. **py-monitor-app**: A Python monitoring application that reports system metrics

Run the examples with:
```bash
docker-compose up -d
```

## Client Libraries

Find client libraries in the `clients/` directory:
- JavaScript/Node.js: `clients/javascript/grandmaster-client.js`
- Python: `clients/python/grandmaster_client.py`

These clients handle reconnection, error handling, and message formatting.