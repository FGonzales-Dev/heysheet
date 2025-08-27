#!/bin/bash
set -e  # Exit on any error

echo "Starting deployment process..."

# Debug environment
echo "DEBUG: $DJANGO_DEBUG"
echo "PORT: $PORT"
echo "DB_HOST: $DB_HOST"

# Check if manage.py exists
if [ ! -f "manage.py" ]; then
    echo "Error: manage.py not found in $(pwd)"
    ls -la
    exit 1
fi

# Install any missing dependencies
echo "Installing dependencies..."
pip install --no-cache-dir -r requirements.txt

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Run migrations
echo "Running migrations..."
python manage.py migrate --noinput

# Test Django configuration
echo "Testing Django setup..."
python manage.py check --deploy

# Start the application
echo "Starting gunicorn server on port $PORT..."
gunicorn core.wsgi:application --bind 0.0.0.0:$PORT --workers 1 --timeout 120 --worker-class sync --max-requests 100 --max-requests-jitter 10 --log-level info
