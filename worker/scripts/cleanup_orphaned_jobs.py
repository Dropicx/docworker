#!/usr/bin/env python3
"""
Startup Cleanup Script for Orphaned Jobs

Runs when worker starts to clean up any jobs that were orphaned
during the previous deployment/restart.

This is a standalone script that doesn't require Celery to be running.
"""
import sys
import os
import logging

# Add paths for imports
sys.path.insert(0, '/app/backend')
sys.path.insert(0, '/app/shared')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def cleanup_orphaned_jobs():
    """Clean up jobs stuck in RUNNING status from previous worker restart"""
    logger.info("🔍 Startup: Checking for orphaned pipeline jobs...")

    try:
        import redis
        from app.database.connection import get_session
        from sqlalchemy import text

        # Connect to Redis
        redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
        r = redis.from_url(redis_url, decode_responses=True)

        # Get session from generator
        session_gen = get_session()
        session = next(session_gen)

        try:
            # At startup, mark ALL RUNNING jobs as orphaned
            # (since worker is just starting, no jobs should be running)
            result = session.execute(
                text("""
                UPDATE pipeline_jobs
                SET status = 'FAILED',
                    error_message = 'Job interrupted by worker restart. Please retry your document.',
                    failed_at = NOW(),
                    updated_at = NOW()
                WHERE status = 'RUNNING'
                RETURNING job_id, filename
                """)
            )

            orphaned_jobs = result.fetchall()
            session.commit()

            orphaned_count = len(orphaned_jobs)
            celery_tasks_removed = 0

            if orphaned_count > 0:
                logger.warning(f"🧹 Startup cleanup: Found {orphaned_count} orphaned jobs from previous restart")
                for job in orphaned_jobs:
                    logger.warning(f"  ✗ {job.job_id} - {job.filename} (marked as FAILED)")

                    # Clean up Celery task result from Redis
                    celery_key = f"celery-task-meta-{job.job_id}"
                    if r.exists(celery_key):
                        r.delete(celery_key)
                        celery_tasks_removed += 1
                        logger.info(f"    🗑️  Removed Celery task: {celery_key}")

                logger.info(f"✅ Orphaned jobs cleaned up - users can retry")
                logger.info(f"✅ Removed {celery_tasks_removed} Celery task results from Redis")
            else:
                logger.info("✅ Startup cleanup: No orphaned jobs found")

            return orphaned_count
        finally:
            # Close the session generator
            try:
                next(session_gen)
            except StopIteration:
                pass

    except Exception as e:
        logger.error(f"❌ Startup cleanup error: {str(e)}")
        # Don't fail the worker startup if cleanup fails
        return 0


if __name__ == '__main__':
    logger.info("================================================")
    logger.info("🧹 Running Startup Orphaned Jobs Cleanup")
    logger.info("================================================")

    try:
        count = cleanup_orphaned_jobs()
        logger.info(f"✅ Cleanup complete: {count} jobs cleaned")
        logger.info("🟢 Ready to start worker")
        logger.info("================================================")
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ Fatal error during cleanup: {e}")
        logger.warning("⚠️  Continuing worker startup despite cleanup failure...")
        sys.exit(0)  # Exit 0 so worker can still start
