#!/bin/bash

PROJECT_NAME="hello-world"
PID_FILE="${PROJECT_NAME}.pid"
LOG_DIR="./logs"
LOG_FILE="${LOG_DIR}/${PROJECT_NAME}.log"

# Create logs directory if it doesn't exist
mkdir -p "$LOG_DIR"

# Check if the process is already running
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p $PID > /dev/null 2>&1; then
        echo "$PROJECT_NAME is already running with PID: $PID"
        exit 1
    else
        echo "Found stale PID file. Removing..."
        rm -f "$PID_FILE"
    fi
fi

# Rotate logs if they exist and are too large (over 10MB)
if [ -f "$LOG_FILE" ]; then
    FILE_SIZE=$(du -k "$LOG_FILE" | cut -f1)
    if [ $FILE_SIZE -gt 10240 ]; then
        TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
        mv "$LOG_FILE" "${LOG_FILE}.${TIMESTAMP}"
        echo "Rotated old log file to ${LOG_FILE}.${TIMESTAMP}"
    fi
fi

# Start the project
echo "Starting $PROJECT_NAME..."
npm start >> "$LOG_FILE" 2>&1 &

# Save the new PID
echo $! > "$PID_FILE"

echo "$PROJECT_NAME started with PID: $(cat $PID_FILE)"
echo "Logs are being written to: $LOG_FILE"