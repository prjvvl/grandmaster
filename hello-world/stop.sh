#!/bin/bash

PROJECT_NAME="hello-world"
PID_FILE="${PROJECT_NAME}.pid"
LOG_DIR="./logs"
LOG_FILE="${LOG_DIR}/${PROJECT_NAME}.log"

# Check if PID file exists
if [ ! -f "$PID_FILE" ]; then
    echo "$PROJECT_NAME is not running or PID file is missing."
    exit 1
fi

# Read the PID and stop the process
PID=$(cat "$PID_FILE")
echo "Stopping $PROJECT_NAME with PID: $PID"

# Log the stopping action if log file exists
if [ -d "$LOG_DIR" ] && [ -w "$LOG_DIR" ]; then
    echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Application stop requested" >> "$LOG_FILE"
fi

# Stop the process
kill "$PID"

# Check if process was successfully stopped
if ! ps -p "$PID" > /dev/null 2>&1; then
    echo "$PROJECT_NAME stopped successfully."
    
    # Log successful termination
    if [ -d "$LOG_DIR" ] && [ -w "$LOG_DIR" ]; then
        echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Application stopped successfully" >> "$LOG_FILE"
    fi
else
    echo "Warning: Process did not terminate immediately. Forcefully killing..."
    kill -9 "$PID"
    
    # Log forced termination
    if [ -d "$LOG_DIR" ] && [ -w "$LOG_DIR" ]; then
        echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Application forcefully terminated" >> "$LOG_FILE"
    fi
fi

# Remove PID file
rm -f "$PID_FILE"
echo "$PROJECT_NAME stopped and PID file removed."