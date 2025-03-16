FROM node:16-slim

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy application code
COPY . .

# Create link to client library
RUN mkdir -p /app/node_modules/grandmaster-client && \
    ln -s /app/../../clients/javascript/grandmaster-client.js /app/node_modules/grandmaster-client/index.js

# Set environment variables
ENV NODE_ENV=production
ENV GRANDMASTER_URL=ws://grandmaster:8765
ENV APP_NAME=js-simple-app

# Start the application
CMD ["node", "index.js"]