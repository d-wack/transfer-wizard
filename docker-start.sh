#!/bin/bash
# Docker start script for TransferWizard
# This script starts all services using Docker Compose

# Build and start containers
echo "Starting all services with Docker Compose..."
docker compose up --build

# Note: Use Ctrl+C to stop all services

# To run in detached mode, uncomment the following line:
# docker-compose up -d --build
