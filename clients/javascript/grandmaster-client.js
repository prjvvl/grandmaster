/**
 * Grandmaster WebSocket Client
 * A simple client for connecting to the Grandmaster service.
 */

const WebSocket = require('ws');

class GrandmasterClient {
  /**
   * Create a new Grandmaster client
   * @param {Object} options - Configuration options
   * @param {string} options.url - WebSocket server URL (e.g., 'ws://grandmaster:8765')
   * @param {string} options.appName - Application name
   * @param {function} options.onConnect - Callback function when connected
   * @param {function} options.onMessage - Callback function when message received
   * @param {function} options.onError - Callback function when error occurs
   * @param {function} options.onClose - Callback function when connection closes
   * @param {number} options.reconnectInterval - Reconnect interval in ms (default: 5000)
   * @param {number} options.maxReconnectAttempts - Max reconnect attempts (default: 10)
   */
  constructor(options) {
    this.url = options.url || process.env.GRANDMASTER_URL || 'ws://grandmaster:8765';
    this.appName = options.appName || process.env.APP_NAME || 'unknown-app';
    this.onConnect = options.onConnect || (() => {});
    this.onMessage = options.onMessage || (() => {});
    this.onError = options.onError || ((err) => { console.error('Error:', err); });
    this.onClose = options.onClose || (() => {});
    this.reconnectInterval = options.reconnectInterval || 5000;
    this.maxReconnectAttempts = options.maxReconnectAttempts || 10;
    
    this.ws = null;
    this.reconnectCount = 0;
    this.connected = false;
    this.reconnectTimer = null;
  }

  /**
   * Connect to the Grandmaster server
   */
  connect() {
    if (this.ws) {
      this.ws.terminate();
    }

    console.log(`Connecting to Grandmaster at ${this.url}...`);
    
    this.ws = new WebSocket(this.url);

    this.ws.on('open', () => {
      console.log('Connected to Grandmaster');
      this.connected = true;
      this.reconnectCount = 0;
      
      // Send initial connection message
      this.send(`✅ App connected: ${this.appName}`);
      
      // Call onConnect callback
      this.onConnect();
    });

    this.ws.on('message', (data) => {
      let message;
      try {
        message = JSON.parse(data);
      } catch (e) {
        message = { content: data.toString() };
      }
      
      this.onMessage(message);
    });

    this.ws.on('error', (err) => {
      this.onError(err);
    });

    this.ws.on('close', () => {
      this.connected = false;
      console.log('Disconnected from Grandmaster');
      
      // Clear any existing reconnect timer
      if (this.reconnectTimer) {
        clearTimeout(this.reconnectTimer);
      }
      
      // Attempt to reconnect
      if (this.reconnectCount < this.maxReconnectAttempts) {
        this.reconnectCount++;
        const delay = Math.min(30000, this.reconnectInterval * Math.pow(1.5, this.reconnectCount - 1));
        console.log(`Reconnecting (${this.reconnectCount}/${this.maxReconnectAttempts}) in ${delay}ms...`);
        
        this.reconnectTimer = setTimeout(() => this.connect(), delay);
      } else {
        console.log('Max reconnect attempts reached');
      }
      
      this.onClose();
    });
  }

  /**
   * Send a message to Grandmaster
   * @param {string} content - Message content
   * @param {Object} additionalData - Additional data to include
   * @returns {boolean} - Whether the message was sent
   */
  send(content, additionalData = {}) {
    if (!this.connected || !this.ws) {
      return false;
    }

    try {
      const message = {
        app: this.appName,
        content: content,
        timestamp: new Date().toISOString(),
        ...additionalData
      };

      this.ws.send(JSON.stringify(message));
      return true;
    } catch (err) {
      this.onError(err);
      return false;
    }
  }

  /**
   * Disconnect from the Grandmaster server
   */
  disconnect() {
    // Clear any reconnect timer
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    
    if (this.ws) {
      // Send goodbye message if connected
      if (this.connected) {
        this.send(`🔌 App disconnecting: ${this.appName}`);
      }
      
      // Close connection
      this.ws.close();
      this.ws = null;
      this.connected = false;
    }
  }
}

module.exports = GrandmasterClient;