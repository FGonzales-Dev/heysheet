#!/bin/bash

# Collect static files
python manage.py collectstatic --noinput

# Run migrations
python manage.py migrate --noinput

# Start the application
gunicorn core.wsgi:application --bind 0.0.0.0:$PORT
