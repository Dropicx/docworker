"""
Celery Worker Entry Point

Enhanced Celery worker with priority queues, retry strategies, and monitoring.
"""
import os
import sys
import logging
from celery import Celery

# Add paths for imports
sys.path.insert(0, '/app/backend')
sys.path.insert(0, '/app/shared')

# Import enhanced worker configuration
from worker import config

# Configure logging with enhanced format
logging.basicConfig(
    level=os.getenv('LOG_LEVEL', 'INFO'),
    format=config.CELERY_WORKER_LOG_FORMAT
)
logger = logging.getLogger(__name__)

# Redis configuration from Railway
logger.info(f"🔗 Connecting to Redis: {config.REDIS_URL.split('@')[0]}...")

# Create Celery app
celery_app = Celery(
    'doctranslator_worker',
    broker=config.REDIS_URL,
    backend=config.REDIS_URL,
    include=['worker.tasks.document_processing', 'worker.tasks.scheduled_tasks']
)

# Apply enhanced configuration from config.py
celery_app.conf.update(
    # ==================== SERIALIZATION ====================
    task_serializer=config.CELERY_TASK_SERIALIZER,
    accept_content=config.CELERY_ACCEPT_CONTENT,
    result_serializer=config.CELERY_RESULT_SERIALIZER,

    # ==================== TIMEZONE ====================
    timezone=config.CELERY_TIMEZONE,
    enable_utc=config.CELERY_ENABLE_UTC,

    # ==================== TASK TIMEOUTS ====================
    task_time_limit=config.TASK_TIME_LIMIT,
    task_soft_time_limit=config.TASK_SOFT_TIME_LIMIT,

    # ==================== WORKER SETTINGS ====================
    worker_concurrency=config.WORKER_CONCURRENCY,
    worker_max_tasks_per_child=config.WORKER_MAX_TASKS_PER_CHILD,
    worker_prefetch_multiplier=config.WORKER_PREFETCH_MULTIPLIER,
    worker_send_task_events=config.CELERY_WORKER_SEND_TASK_EVENTS,
    worker_pool=config.CELERY_WORKER_POOL,
    worker_disable_rate_limits=config.CELERY_WORKER_DISABLE_RATE_LIMITS,

    # ==================== PRIORITY QUEUES ====================
    task_queues=config.CELERY_TASK_QUEUES,
    task_default_queue=config.CELERY_TASK_DEFAULT_QUEUE,
    task_default_routing_key=config.CELERY_TASK_DEFAULT_ROUTING_KEY,
    task_routes=config.CELERY_TASK_ROUTES,

    # ==================== RETRY CONFIGURATION ====================
    task_default_retry_delay=config.CELERY_TASK_DEFAULT_RETRY_DELAY,
    task_max_retries=config.CELERY_TASK_MAX_RETRIES,
    task_retry_backoff=config.CELERY_TASK_RETRY_BACKOFF,
    task_retry_backoff_max=config.CELERY_TASK_RETRY_BACKOFF_MAX,
    task_retry_jitter=config.CELERY_TASK_RETRY_JITTER,
    task_autoretry_for=config.CELERY_TASK_AUTORETRY_FOR,

    # ==================== COMPRESSION ====================
    task_compression=config.CELERY_TASK_COMPRESSION,
    result_compression=config.CELERY_RESULT_COMPRESSION,

    # ==================== RESULT BACKEND ====================
    result_expires=config.CELERY_RESULT_EXPIRES,
    result_persistent=config.CELERY_RESULT_PERSISTENT,
    result_backend_always_retry=config.CELERY_RESULT_BACKEND_ALWAYS_RETRY,
    result_backend_transport_options=config.CELERY_RESULT_BACKEND_TRANSPORT_OPTIONS,

    # ==================== WORKER BEHAVIOR ====================
    task_acks_late=config.CELERY_TASK_ACKS_LATE,
    task_reject_on_worker_lost=config.CELERY_TASK_REJECT_ON_WORKER_LOST,
    task_track_started=config.CELERY_TASK_TRACK_STARTED,
    task_send_sent_event=config.CELERY_TASK_SEND_SENT_EVENT,

    # ==================== BROKER SETTINGS ====================
    broker_connection_retry_on_startup=config.BROKER_CONNECTION_RETRY_ON_STARTUP,
    broker_connection_retry=config.BROKER_CONNECTION_RETRY,
    broker_connection_max_retries=config.BROKER_CONNECTION_MAX_RETRIES,

    # ==================== GRACEFUL SHUTDOWN ====================
    worker_shutdown_timeout=config.CELERY_WORKER_SHUTDOWN_TIMEOUT,

    # ==================== BEAT SCHEDULE ====================
    beat_schedule=config.CELERYBEAT_SCHEDULE,
)

logger.info("✅ Celery worker initialized with enhanced configuration")
logger.info(f"⚙️  Worker settings:")
logger.info(f"   - Concurrency: {config.WORKER_CONCURRENCY}")
logger.info(f"   - Pool: {config.CELERY_WORKER_POOL}")
logger.info(f"   - Prefetch multiplier: {config.WORKER_PREFETCH_MULTIPLIER}")
logger.info(f"   - Max tasks per child: {config.WORKER_MAX_TASKS_PER_CHILD}")
logger.info(f"🔄 Priority queues configured:")
logger.info(f"   - high_priority: Interactive user uploads")
logger.info(f"   - default: Standard tasks")
logger.info(f"   - low_priority: Background tasks")
logger.info(f"   - maintenance: Scheduled cleanup")
logger.info(f"📦 Compression enabled: {config.CELERY_TASK_COMPRESSION}")
logger.info(f"🔁 Retry strategy: Exponential backoff with jitter")
logger.info(f"   - Max retries: {config.CELERY_TASK_MAX_RETRIES}")
logger.info(f"   - Max backoff: {config.CELERY_TASK_RETRY_BACKOFF_MAX}s")
logger.info(f"⏱️  Task timeouts:")
logger.info(f"   - Soft limit: {config.TASK_SOFT_TIME_LIMIT}s ({config.TASK_SOFT_TIME_LIMIT//60} min)")
logger.info(f"   - Hard limit: {config.TASK_TIME_LIMIT}s ({config.TASK_TIME_LIMIT//60} min)")
logger.info("📅 Celery Beat schedule configured:")
logger.info("   - cleanup_orphaned_jobs: every 10 minutes (maintenance queue)")
logger.info("   - cleanup_celery_results: every hour (maintenance queue)")
logger.info("   - cleanup_old_files: every 24 hours (maintenance queue)")
logger.info("   - database_maintenance: every 24 hours (maintenance queue)")

if __name__ == '__main__':
    celery_app.start()
