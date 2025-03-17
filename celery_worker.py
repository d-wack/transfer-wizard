#!/usr/bin/env python
"""
Celery worker startup script for TransferWizard.
This script starts a Celery worker that processes job execution tasks.
"""
import os
from app import create_app
from app.celery_app import celery_app

# Create the Flask app
app = create_app()

# Initialize the Celery app with the Flask app context
with app.app_context():
    if __name__ == '__main__':
        print("Starting Celery worker...")
        # This allows the worker to access Flask-specific configurations and context
        celery_app.start()
