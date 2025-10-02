# ==========================================
# Stage 1: Build Frontend
# ==========================================
FROM node:24-alpine AS build

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install ALL dependencies (including devDependencies for build)
RUN npm ci

# Copy source code
COPY . .

# Build application with Vite API URL
ARG VITE_API_URL=/api
ENV VITE_API_URL=${VITE_API_URL}
RUN npm run build

# ==========================================
# Stage 2: Production nginx Server
# ==========================================
FROM nginx:1.27-alpine

# Install curl for health checks
RUN apk add --no-cache curl

# Copy built frontend
COPY --from=build /app/dist /usr/share/nginx/html

# Create basic nginx config (Railway handles proxying)
RUN echo 'server { \
    listen 8080; \
    root /usr/share/nginx/html; \
    index index.html; \
    location / { \
        try_files $uri $uri/ /index.html; \
    } \
}' > /etc/nginx/conf.d/default.conf

# Environment variables
ENV PORT=8080

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/ || exit 1

# Start nginx
CMD ["nginx", "-g", "daemon off;"] 