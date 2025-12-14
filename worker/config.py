"""
Worker Configuration

Enhanced configuration settings for the Celery worker with priority queues,
retry strategies, compression, and monitoring.
"""
import os
from kombu import Queue

# ==================== REDIS CONNECTION ====================
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

# ==================== WORKER SETTINGS ====================
WORKER_CONCURRENCY = int(os.getenv('WORKER_CONCURRENCY', '2'))
WORKER_MAX_TASKS_PER_CHILD = int(os.getenv('WORKER_MAX_TASKS_PER_CHILD', '50'))
WORKER_PREFETCH_MULTIPLIER = int(os.getenv('WORKER_PREFETCH_MULTIPLIER', '1'))

# ==================== TASK TIMEOUTS ====================
# Increased for complex medical documents like lab reports
TASK_TIME_LIMIT = int(os.getenv('TASK_TIME_LIMIT', '1200'))  # 20 minutes hard limit
TASK_SOFT_TIME_LIMIT = int(os.getenv('TASK_SOFT_TIME_LIMIT', '1080'))  # 18 minutes soft limit

# ==================== PRIORITY QUEUES ====================
# Define multiple queues with different priorities
CELERY_TASK_QUEUES = (
    Queue('high_priority', routing_key='high_priority'),
    Queue('default', routing_key='default'),
    Queue('low_priority', routing_key='low_priority'),
    Queue('maintenance', routing_key='maintenance'),
)

# Default queue for tasks without explicit routing
CELERY_TASK_DEFAULT_QUEUE = 'default'
CELERY_TASK_DEFAULT_ROUTING_KEY = 'default'

# Route tasks to appropriate queues
CELERY_TASK_ROUTES = {
    # High priority - interactive user uploads
    'process_medical_document': {'queue': 'high_priority'},

    # Low priority - scheduled maintenance tasks
    'cleanup_orphaned_jobs': {'queue': 'maintenance'},
    'cleanup_celery_results': {'queue': 'maintenance'},
    'cleanup_old_files': {'queue': 'maintenance'},
    'database_maintenance': {'queue': 'maintenance'},
    'cleanup_orphaned_content': {'queue': 'maintenance'},  # GDPR cleanup (Issue #47)
}

# ==================== RETRY CONFIGURATION ====================
# Default retry policy for all tasks
CELERY_TASK_DEFAULT_RETRY_DELAY = 60  # 1 minute base delay
CELERY_TASK_MAX_RETRIES = 3

# Exponential backoff settings
CELERY_TASK_RETRY_BACKOFF = True
CELERY_TASK_RETRY_BACKOFF_MAX = 600  # 10 minutes max backoff
CELERY_TASK_RETRY_JITTER = True  # Add randomness to prevent thundering herd

# Auto-retry for specific exceptions
CELERY_TASK_AUTORETRY_FOR = (
    ConnectionError,  # Network issues
    TimeoutError,  # Timeout errors
)

# ==================== COMPRESSION ====================
# Compress task messages and results to reduce Redis bandwidth
CELERY_TASK_COMPRESSION = os.getenv('CELERY_TASK_COMPRESSION', 'gzip')
CELERY_RESULT_COMPRESSION = os.getenv('CELERY_RESULT_COMPRESSION', 'gzip')

# ==================== RESULT BACKEND ====================
CELERY_RESULT_EXPIRES = int(os.getenv('CELERY_RESULT_EXPIRES', '3600'))  # 1 hour
CELERY_RESULT_PERSISTENT = False  # Don't persist results after expiration
CELERY_RESULT_BACKEND_ALWAYS_RETRY = True  # Retry Redis operations

# Result backend transport options
CELERY_RESULT_BACKEND_TRANSPORT_OPTIONS = {
    'master_name': 'mymaster',  # Redis Sentinel support
    'socket_keepalive': True,
    'socket_keepalive_options': {
        1: 10,  # TCP_KEEPIDLE
        2: 10,  # TCP_KEEPINTVL
        3: 3,   # TCP_KEEPCNT
    },
    'retry_on_timeout': True,
    'health_check_interval': 30,
}

# ==================== WORKER BEHAVIOR ====================
# Acknowledge tasks after they finish (not before)
CELERY_TASK_ACKS_LATE = True

# Reject tasks if worker crashes (requeue them)
CELERY_TASK_REJECT_ON_WORKER_LOST = True

# Track when tasks start (for monitoring)
CELERY_TASK_TRACK_STARTED = True

# Send task events for monitoring
CELERY_WORKER_SEND_TASK_EVENTS = True
CELERY_TASK_SEND_SENT_EVENT = True

# ==================== BROKER SETTINGS ====================
BROKER_CONNECTION_RETRY_ON_STARTUP = True
BROKER_CONNECTION_RETRY = True
BROKER_CONNECTION_MAX_RETRIES = 10

# ==================== SERIALIZATION ====================
CELERY_TASK_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_RESULT_SERIALIZER = 'json'

# ==================== TIMEZONE ====================
CELERY_TIMEZONE = 'Europe/Berlin'
CELERY_ENABLE_UTC = True

# ==================== BEAT SCHEDULE (PERIODIC TASKS) ====================
CELERYBEAT_SCHEDULE = {
    'cleanup-orphaned-jobs-every-10-min': {
        'task': 'cleanup_orphaned_jobs',
        'schedule': 600.0,  # Run every 10 minutes
        'options': {'queue': 'maintenance'}
    },
    'cleanup-celery-results-hourly': {
        'task': 'cleanup_celery_results',
        'schedule': 3600.0,  # Run every hour
        'options': {'queue': 'maintenance'}
    },
    'cleanup-old-files-daily': {
        'task': 'cleanup_old_files',
        'schedule': 86400.0,  # Run every 24 hours
        'options': {'queue': 'maintenance'}
    },
    'database-maintenance-daily': {
        'task': 'database_maintenance',
        'schedule': 86400.0,  # Run every 24 hours at midnight
        'options': {'queue': 'maintenance'}
    },
    'cleanup-orphaned-content-hourly': {
        'task': 'cleanup_orphaned_content',
        'schedule': 3600.0,  # Run every hour - GDPR content cleanup (Issue #47)
        'options': {'queue': 'maintenance'}
    },
}

# ==================== MONITORING & LOGGING ====================
CELERY_WORKER_LOG_FORMAT = '[%(asctime)s: %(levelname)s/%(processName)s] %(message)s'
CELERY_WORKER_TASK_LOG_FORMAT = '[%(asctime)s: %(levelname)s/%(processName)s][%(task_name)s(%(task_id)s)] %(message)s'

# Flower monitoring settings
FLOWER_PORT = int(os.getenv('FLOWER_PORT', '5555'))
FLOWER_BASIC_AUTH = os.getenv('FLOWER_BASIC_AUTH', '')  # Format: "user:password"

# ==================== TASK DEDUPLICATION ====================
# Prevent duplicate task submission (requires celery-once)
CELERY_ONCE = {
    'backend': 'celery_once.backends.Redis',
    'settings': {
        'url': REDIS_URL,
        'default_timeout': 60 * 60  # 1 hour lock
    }
}

# ==================== GRACEFUL SHUTDOWN ====================
CELERY_WORKER_SHUTDOWN_TIMEOUT = 60  # Wait 60 seconds for tasks to finish
CELERYD_MAX_TASKS_PER_CHILD = WORKER_MAX_TASKS_PER_CHILD  # Restart worker after N tasks

# ==================== PERFORMANCE TUNING ====================
# Pool type (prefork for CPU-bound, gevent for I/O-bound)
CELERY_WORKER_POOL = os.getenv('CELERY_WORKER_POOL', 'prefork')

# Disable rate limits (we handle this at application level)
CELERY_WORKER_DISABLE_RATE_LIMITS = True

# ==================== SECURITY ====================
# Accept only JSON content (prevent code injection)
CELERY_ACCEPT_CONTENT = ['json']

# Don't trust pickle from untrusted sources
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
