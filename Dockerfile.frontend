# --- Build stage ---
    FROM node:20-slim AS builder
    WORKDIR /app
    
    # deps
    COPY frontend/package*.json ./
    RUN npm ci
    
    # source + build
    COPY frontend .
    # (Optional) pass Vite envs from DO at build time
    ARG VITE_API_URL
    ENV VITE_API_URL=$VITE_API_URL
    RUN npm run build
    
    # --- Runtime stage ---
    FROM nginx:alpine
    
    # needed for envsubst
    RUN apk add --no-cache gettext
    
    # static files
    COPY --from=builder /app/dist /usr/share/nginx/html
    
    # template + entrypoint
    COPY frontend/nginx.conf.template /etc/nginx/conf.d/default.conf.template
    COPY frontend/docker-entrypoint.sh /docker-entrypoint.sh
    RUN chmod +x /docker-entrypoint.sh
    
    # for local
    EXPOSE 8080
    
    CMD ["/docker-entrypoint.sh"]
    