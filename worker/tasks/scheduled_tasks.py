"""
Scheduled Background Tasks

Tasks that run on a schedule (hourly, daily, etc.)
"""
import logging
from worker.worker import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name='database_maintenance')
def database_maintenance():
    """
    Daily database maintenance task
    - Clean up old processing records
    - Vacuum/optimize database
    """
    logger.info("🔧 Running database maintenance")

    try:
        import sys
        sys.path.insert(0, '/app/backend')
        from app.database.connection import get_session
        from sqlalchemy import text

        with get_session() as session:
            # Example: Delete processing records older than 7 days
            result = session.execute(
                text("""
                DELETE FROM ai_interaction_logs
                WHERE created_at < NOW() - INTERVAL '7 days'
                """)
            )
            session.commit()

            rows_deleted = result.rowcount
            logger.info(f"✅ Database maintenance complete: {rows_deleted} old records removed")

            return {
                'status': 'completed',
                'rows_deleted': rows_deleted
            }

    except Exception as e:
        logger.error(f"❌ Database maintenance error: {str(e)}")
        raise


@celery_app.task(name='health_check_worker')
def health_check_worker():
    """
    Worker health check task
    Used by monitoring systems to verify worker is responsive
    """
    logger.debug("❤️ Worker health check")
    return {'status': 'healthy', 'worker': 'doctranslator-worker'}


@celery_app.task(name='cleanup_celery_results')
def cleanup_celery_results():
    """
    Clean up expired Celery task results from Redis
    Runs hourly to prevent Redis memory bloat
    """
    logger.info("🧹 Cleaning up old Celery results from Redis")

    try:
        import os
        import redis

        redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
        r = redis.from_url(redis_url, decode_responses=True)

        # Get all celery result keys
        pattern = 'celery-task-meta-*'
        keys = r.keys(pattern)

        if not keys:
            logger.info("✅ No Celery results to clean up")
            return {'status': 'completed', 'keys_removed': 0}

        # Remove keys (respecting result_expires setting)
        # Redis will auto-expire based on TTL, but we can force cleanup
        expired_count = 0
        for key in keys:
            ttl = r.ttl(key)
            # If TTL is -1 (no expiration) or key is very old, delete it
            if ttl == -1 or ttl == -2:
                r.delete(key)
                expired_count += 1

        logger.info(f"✅ Celery results cleanup complete: {expired_count} keys removed")

        return {
            'status': 'completed',
            'total_keys_found': len(keys),
            'keys_removed': expired_count
        }

    except Exception as e:
        logger.error(f"❌ Celery results cleanup error: {str(e)}")
        raise
