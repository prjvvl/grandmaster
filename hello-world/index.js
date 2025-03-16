const WebSocket = require('ws');
const fs = require('fs');
const path = require('path');

const serverUrl = 'ws://localhost:8765';
const appName = 'hello-world';
const logFile = path.join(__dirname, 'logs', `${appName}.log`);

// Create logs directory if it doesn't exist
if (!fs.existsSync(path.join(__dirname, 'logs'))) {
    fs.mkdirSync(path.join(__dirname, 'logs'));
}

// Function to log to console and file
function log(message) {
    const timestamp = new Date().toISOString();
    const logMessage = `[${timestamp}] ${message}`;
    
    console.log(logMessage);
    
    // Append to log file
    fs.appendFileSync(logFile, logMessage + '\n');
}

async function hello() {
    return new Promise((resolve, reject) => {
        const ws = new WebSocket(serverUrl);
        let resolved = false; // Flag to prevent multiple resolutions

        ws.on('open', () => {
            log(`Connected to server`);
            ws.send(JSON.stringify({ 
                app: appName,
                content: '✅ App started: Hello World App' 
            }));
            setInterval(() => {
                const message = 'Greetings from Hello World App';
                log(`Sending: ${message}`);
                ws.send(JSON.stringify({ 
                    app: appName,
                    content: message
                }));
            }, 60 * 1000); // 1 min interval
        });

        ws.on('message', (data) => {
            if (!resolved) {
                log(`Received from server: ${data}`);
                ws.close();
                resolved = true;
                resolve();
            }
        });

        ws.on('error', (err) => {
            if (!resolved) {
                log(`Error: ${err}`);
                resolved = true;
                reject(err);
            }
        });

        ws.on('close', () => {
            log(`Disconnected from server`);
            if (!resolved) {
                resolved = true;
                resolve();
            }
        });
    });
}

log(`Starting ${appName} application`);
hello().then(() => process.exit(0)).catch(() => process.exit(1));