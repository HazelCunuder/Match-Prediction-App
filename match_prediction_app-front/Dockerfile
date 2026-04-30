# Build stage
FROM node:18-alpine AS build

WORKDIR /app

# Copy package files
COPY match_prediction_app-front/package*.json ./

# Install dependencies
RUN npm install --frozen-lockfile

# Copy source code
COPY match_prediction_app-front/ .

# Build application
RUN npm run build

# Production stage
FROM nginx:alpine

# Copy built application
COPY --from=build /app/dist /usr/share/nginx/html

# Copy nginx configuration
COPY match_prediction_app-front/nginx.conf /etc/nginx/conf.d/default.conf

# Create SSL directory for certificates
RUN mkdir -p /etc/nginx/ssl && \
    chown -R nginx:nginx /etc/nginx/ssl && \
    chown -R nginx:nginx /usr/share/nginx/html

# Expose ports
EXPOSE 80 443

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost/index.html || exit 1

# Run nginx
CMD ["nginx", "-g", "daemon off;"]
