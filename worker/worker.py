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
    broker_connection_retry_on_startup=True,  # Retry Redis connection on startup (Celery 6.0+ compatibility)
    result_expires=3600,  # Task results expire after 1 hour
    result_backend_transport_options={
        'master_name': 'mymaster'
    } if 'sentinel' in REDIS_URL.lower() else {},
    # Celery Beat schedule for periodic tasks
    beat_schedule={
        'cleanup-orphaned-jobs-every-10-min': {
            'task': 'cleanup_orphaned_jobs',
            'schedule': 600.0,  # Run every 10 minutes
        },
        'cleanup-celery-results-hourly': {
            'task': 'cleanup_celery_results',
            'schedule': 3600.0,  # Run every hour
        },
        'cleanup-old-files-daily': {
            'task': 'cleanup_old_files',
            'schedule': 86400.0,  # Run every 24 hours
        },
        'database-maintenance-daily': {
            'task': 'database_maintenance',
            'schedule': 86400.0,  # Run every 24 hours
        },
    },
)

logger.info("✅ Celery worker initialized")
logger.info("📅 Celery Beat schedule configured:")
logger.info("   - cleanup_orphaned_jobs: every 10 minutes")
logger.info("   - cleanup_celery_results: every hour")
logger.info("   - cleanup_old_files: every 24 hours")
logger.info("   - database_maintenance: every 24 hours")

if __name__ == '__main__':
    celery_app.start()
