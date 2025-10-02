"""
Celery Worker Entry Point

This module initializes the Celery worker for processing background tasks.
"""
import os
import sys
import logging
from celery import Celery

# Add paths for imports
sys.path.insert(0, '/app/backend')
sys.path.insert(0, '/app/shared')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Redis configuration from Railway
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
logger.info(f"🔗 Connecting to Redis: {REDIS_URL.split('@')[0]}...")

# Create Celery app
celery_app = Celery(
    'doctranslator_worker',
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=['worker.tasks.document_processing', 'worker.tasks.scheduled_tasks']
)

# Celery configuration
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Europe/Berlin',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=600,  # 10 minutes max per task
    task_soft_time_limit=540,  # 9 minutes soft limit
    worker_prefetch_multiplier=1,  # Process one task at a time
    worker_max_tasks_per_child=50,  # Restart worker after 50 tasks
    task_acks_late=True,  # Acknowledge task after completion
    worker_prefetch_multiplier=1,  # Don't prefetch tasks
)

logger.info("✅ Celery worker initialized")

if __name__ == '__main__':
    celery_app.start()
