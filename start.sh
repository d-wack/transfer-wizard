#!/bin/bash
# Start script for TransferWizard
# This script starts the Redis container, Flask app, and Celery worker

echo "Starting Redis container with Docker Compose..."
docker-compose up -d redis

# Wait a moment for Redis to be ready
sleep 3

# Check if Redis is running
docker-compose exec redis redis-cli ping > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "Failed to start Redis container. Please check Docker logs."
    exit 1
fi

echo "Redis is running. Starting Celery worker..."
celery -A app.celery_app.celery_app worker --loglevel=info &
CELERY_PID=$!

# Start Flask app
echo "Starting Flask app..."
python run.py

# When Flask app is terminated, also terminate Celery worker
echo "Shutting down Celery worker..."
kill $CELERY_PID

# Keep Redis running - to stop it manually use: docker-compose down
echo "Redis container is still running. To stop it, run: docker-compose down"
