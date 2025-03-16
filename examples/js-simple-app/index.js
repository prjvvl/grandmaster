/**
 * Simple JS application that connects to Grandmaster
 */

const GrandmasterClient = require('grandmaster-client');

// Create info function to log with timestamp
function info(message) {
    console.log(`[${new Date().toISOString()}] ${message}`);
}

// Create a counter to demonstrate app functionality
let counter = 0;

// Create the Grandmaster client
const client = new GrandmasterClient({
    url: process.env.GRANDMASTER_URL || 'ws://grandmaster:8765',
    appName: process.env.APP_NAME || 'js-simple-app',
    
    onConnect: () => {
        info('Connected to Grandmaster!');
        
        // Send heartbeat/status every minute
        setInterval(() => {
            counter++;
            client.send('Heartbeat', {
                counter: counter,
                memory: process.memoryUsage().heapUsed / 1024 / 1024,
                uptime: process.uptime()
            });
        }, 60000);
        
        // Send initial status
        client.send('Application started', {
            version: '1.0.0',
            environment: process.env.NODE_ENV || 'development',
            nodejs: process.version
        });
    },
    
    onMessage: (message) => {
        info(`Received message: ${JSON.stringify(message)}`);
        
        // Handle echo command
        if (message.command === 'echo') {
            info('Echoing message back');
            client.send(`Echo: ${message.text}`, {
                original: message
            });
        }
    },
    
    onError: (err) => {
        console.error(`Connection error: ${err.message}`);
    },
    
    onClose: () => {
        info('Disconnected from Grandmaster');
    }
});

// Log startup
info('Starting application...');

// Connect to Grandmaster
client.connect();

// Handle graceful shutdown
process.on('SIGINT', () => {
    info('Shutting down...');
    client.disconnect();
    setTimeout(() => process.exit(0), 1000);
});

process.on('SIGTERM', () => {
    info('Terminating...');
    client.disconnect();
    setTimeout(() => process.exit(0), 1000);
});