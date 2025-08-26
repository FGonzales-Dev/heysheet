#!/bin/sh
set -e

# Default for local runs
: "${PORT:=8080}"

# Render the Nginx config from the template using envsubst
envsubst '${PORT}' \
  < /etc/nginx/conf.d/default.conf.template \
  > /etc/nginx/conf.d/default.conf

# Start Nginx in the foreground
exec nginx -g 'daemon off;'
