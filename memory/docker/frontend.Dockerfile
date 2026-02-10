# Stage 1: Build React dashboard
FROM node:20-slim AS builder

WORKDIR /app

COPY frontend/package*.json ./
RUN npm install --legacy-peer-deps || npm install --force

COPY frontend/ ./
RUN npm run build

# Stage 2: Nginx serves static files + reverse proxies to API
FROM nginx:alpine

# Remove default nginx config
RUN rm /etc/nginx/conf.d/default.conf

# Copy our nginx config
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf

# Copy built frontend
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
