# Build stage
FROM node:18-alpine AS build

WORKDIR /app

COPY match_prediction_app-front/package*.json ./

RUN npm install --frozen-lockfile

COPY match_prediction_app-front/ .

RUN npm run build

# Production stage
FROM nginx:alpine

COPY --from=build /app/dist /usr/share/nginx/html

COPY match_prediction_app-front/nginx.conf /etc/nginx/conf.d/default.conf

RUN mkdir -p /etc/nginx/ssl && \
    chown -R nginx:nginx /etc/nginx/ssl && \
    chown -R nginx:nginx /usr/share/nginx/html

EXPOSE 80 443

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost/index.html || exit 1

CMD ["nginx", "-g", "daemon off;"]
