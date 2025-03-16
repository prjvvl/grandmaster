FROM python:3.10-slim

WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Copy client library
COPY ../../clients/python/grandmaster_client.py .

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV GRANDMASTER_URL=ws://grandmaster:8765
ENV APP_NAME=py-monitor-app

# Start the application
CMD ["python", "app.py"]