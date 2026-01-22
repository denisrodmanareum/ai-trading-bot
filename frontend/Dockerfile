# Multi-arch support
FROM --platform=$TARGETPLATFORM node:18-alpine

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy app files
COPY . .

# Fix for Node 18+ OpenSSL issue
ENV NODE_OPTIONS=--openssl-legacy-provider

# Expose port
EXPOSE 3000

# Start development server
CMD ["npm", "start"]
