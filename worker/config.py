"""
Worker Configuration

Configuration settings for the Celery worker
"""
import os

# Redis connection
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

# Worker settings
WORKER_CONCURRENCY = int(os.getenv('WORKER_CONCURRENCY', '2'))
WORKER_MAX_TASKS_PER_CHILD = int(os.getenv('WORKER_MAX_TASKS_PER_CHILD', '50'))

# Task timeouts
TASK_TIME_LIMIT = int(os.getenv('TASK_TIME_LIMIT', '600'))  # 10 minutes
TASK_SOFT_TIME_LIMIT = int(os.getenv('TASK_SOFT_TIME_LIMIT', '540'))  # 9 minutes

# Celery beat schedule (for periodic tasks)
CELERYBEAT_SCHEDULE = {
    'cleanup-every-hour': {
        'task': 'cleanup_old_files',
        'schedule': 3600.0,  # Every hour
    },
    'cleanup-celery-results-hourly': {
        'task': 'cleanup_celery_results',
        'schedule': 3600.0,  # Every hour
    },
    'database-maintenance-daily': {
        'task': 'database_maintenance',
        'schedule': 86400.0,  # Every day
    },
}
