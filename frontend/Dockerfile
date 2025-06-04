# Multi-stage build for React app
FROM node:18-slim as build

# Set working directory
WORKDIR /app

# Install necessary system dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    make \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy package files
COPY package*.json ./

# Clear npm cache and install dependencies with fix for ajv issue
RUN npm cache clean --force && \
    rm -rf node_modules package-lock.json && \
    npm install --legacy-peer-deps && \
    npm install ajv@6.12.6 ajv-keywords@3.5.2 --save-dev --legacy-peer-deps && \
    npm ls ajv ajv-keywords || true

# Copy source code
COPY . .

# Build the application
RUN npm run build

# Production stage with nginx
FROM nginx:alpine

# Copy built app to nginx
COPY --from=build /app/build /usr/share/nginx/html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:9121 || exit 1

# Expose port
EXPOSE 9121

# Start nginx
CMD ["nginx", "-g", "daemon off;"] 