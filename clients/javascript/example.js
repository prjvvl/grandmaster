/**
 * Example of using the Grandmaster client
 */

const GrandmasterClient = require('./grandmaster-client');

// Create a new client
const client = new GrandmasterClient({
  url: process.env.GRANDMASTER_URL || 'ws://grandmaster:8765',
  appName: 'example-js-app',
  
  // Callbacks
  onConnect: () => {
    console.log('Connected to Grandmaster! Sending some data...');
    
    // Example: Send a message every 30 seconds
    setInterval(() => {
      // Get some system information
      const memoryUsage = process.memoryUsage();
      const metrics = {
        memory: {
          rss: Math.round(memoryUsage.rss / 1024 / 1024),
          heapTotal: Math.round(memoryUsage.heapTotal / 1024 / 1024),
          heapUsed: Math.round(memoryUsage.heapUsed / 1024 / 1024)
        },
        uptime: process.uptime()
      };
      
      client.send('Periodic status update', {
        status: 'healthy',
        metrics: metrics
      });
      
      console.log(`Status update sent. Memory usage: ${metrics.memory.heapUsed}MB`);
    }, 30000);
  },
  
  onMessage: (message) => {
    console.log('Received message from Grandmaster:', message);
    
    // Handle commands or other messages from Grandmaster
    if (message.command === 'restart') {
      console.log('Restarting application...');
      // Implementation of restart logic
    }
    
    // Respond to ping requests
    if (message.command === 'ping') {
      client.send('pong', { 
        responseId: message.id,
        timestamp: Date.now()
      });
    }
  },
  
  onError: (err) => {
    console.error('Connection error:', err);
  },
  
  onClose: () => {
    console.log('Connection closed');
  }
});

// Connect to Grandmaster
client.connect();

// Make sure we disconnect properly on exit
process.on('SIGINT', () => {
  console.log('Shutting down...');
  client.disconnect();
  setTimeout(() => process.exit(0), 1000);
});

process.on('SIGTERM', () => {
  console.log('Terminating...');
  client.disconnect();
  setTimeout(() => process.exit(0), 1000);
});