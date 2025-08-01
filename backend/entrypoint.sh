#!/bin/sh

# Wait for the database to be ready
until nc -z db 5432; do
    echo "Waiting for database..."
    sleep 2
done

echo "Running migrations..."
python manage.py migrate

echo "Starting server..."
python manage.py runserver 0.0.0.0:8000
