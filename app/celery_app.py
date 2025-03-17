from celery import Celery
from config import Config
import os

def make_celery(app_name=__name__):
    """
    Create a Celery instance that can be used to define tasks.
    """
    # Get Redis URL from environment or use default
    broker_url = os.environ.get('CELERY_BROKER_URL', 'redis://redis:6379/0')
    result_backend = os.environ.get('CELERY_RESULT_BACKEND', 'redis://redis:6379/0')
    
    # Create Celery app
    celery = Celery(
        app_name,
        broker=broker_url,
        backend=result_backend,
        include=['app.tasks.job_tasks']  # Include the tasks module
    )
    
    # Set configuration from object
    celery.conf.update(
        task_serializer='json',
        accept_content=['json'],
        result_serializer='json',
        enable_utc=True,
        task_track_started=True,
        task_time_limit=3600,  # 1 hour
        worker_max_tasks_per_child=1000,  # Restart worker after 1000 tasks to prevent memory leaks
        worker_prefetch_multiplier=1  # Process one task at a time (good for long-running tasks)
    )
    
    return celery

# Create the Celery app
celery_app = make_celery()
