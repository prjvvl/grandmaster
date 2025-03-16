FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install Node.js and npm
RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    && curl -sL https://deb.nodesource.com/setup_16.x | bash - \
    && apt-get install -y nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    GRANDMASTER_BASE_DIR=/app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Create necessary directories
RUN mkdir -p logs config

# Make script files executable
RUN find . -name "*.sh" -exec chmod +x {} \;

# Set the entrypoint
ENTRYPOINT ["python", "-m", "src.main"]

# Default command (can be overridden)
CMD [".env"]