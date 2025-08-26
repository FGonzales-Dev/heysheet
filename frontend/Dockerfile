# --- Build stage ---
    FROM node:20-slim AS builder
    WORKDIR /app
    
    # deps (paths are relative to /frontend build context)
    COPY package*.json ./
    RUN npm ci
    
    # source + build
    COPY . .
    ARG VITE_API_URL
    ENV VITE_API_URL=$VITE_API_URL
    RUN npm run build
    
    # --- Runtime stage ---
    FROM nginx:alpine
    RUN apk add --no-cache gettext
    
    # static files
    COPY --from=builder /app/dist /usr/share/nginx/html
    
    # nginx template + entrypoint (these files live in /frontend)
    COPY nginx.conf.template /etc/nginx/conf.d/default.conf.template
    COPY docker-entrypoint.sh /docker-entrypoint.sh
    RUN chmod +x /docker-entrypoint.sh
    
    EXPOSE 8080
    CMD ["/docker-entrypoint.sh"]
    