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
