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
    Clean up expired Celery task results from Redis.

    Removes:
    - Task results with no TTL (shouldn't happen, but safety check)
    - Task results that are expired (-2 TTL)
    - Task results older than 2 hours (even if still within TTL)

    Runs hourly to prevent Redis memory bloat.
    """
    logger.info("🧹 Cleaning up old Celery results from Redis")

    try:
        import os
        import redis
        import time
        import json

        redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
        r = redis.from_url(redis_url, decode_responses=False)  # Binary mode for decoding

        # Get all celery result keys
        pattern = b'celery-task-meta-*'
        keys = r.keys(pattern)

        if not keys:
            logger.info("✅ No Celery results to clean up")
            return {'status': 'completed', 'keys_removed': 0}

        # Remove keys based on TTL and age
        expired_count = 0
        old_count = 0
        current_time = time.time()

        for key in keys:
            ttl = r.ttl(key)

            # Remove if no expiration or already expired
            if ttl == -1 or ttl == -2:
                r.delete(key)
                expired_count += 1
                continue

            # Check if result is older than 2 hours
            try:
                result_data = r.get(key)
                if result_data:
                    # Celery stores JSON results
                    result_json = json.loads(result_data)
                    # Check if result has date_done field
                    if 'date_done' in result_json:
                        from datetime import datetime
                        date_done = datetime.fromisoformat(result_json['date_done'].replace('Z', '+00:00'))
                        age_seconds = (datetime.now(date_done.tzinfo) - date_done).total_seconds()

                        # Remove results older than 2 hours
                        if age_seconds > 7200:  # 2 hours
                            r.delete(key)
                            old_count += 1
            except Exception:
                # If we can't parse the result, skip it (don't delete)
                pass

        total_removed = expired_count + old_count

        logger.info(f"✅ Celery results cleanup complete:")
        logger.info(f"   - Expired/no TTL removed: {expired_count}")
        logger.info(f"   - Old (>2h) removed: {old_count}")
        logger.info(f"   - Total removed: {total_removed}")

        return {
            'status': 'completed',
            'total_keys_found': len(keys),
            'keys_removed': total_removed,
            'expired_removed': expired_count,
            'old_removed': old_count
        }

    except Exception as e:
        logger.error(f"❌ Celery results cleanup error: {str(e)}")
        raise


@celery_app.task(name='cleanup_orphaned_jobs')
def cleanup_orphaned_jobs():
    """
    Clean up jobs that have been stuck in RUNNING status.

    This happens when:
    - Worker service is restarted/rebuilt during job processing
    - Worker crashes mid-job
    - Network issues cause worker to lose connection

    Jobs stuck in RUNNING for >15 minutes are marked as FAILED.
    Also cleans up corresponding Celery task results from Redis.
    Runs every 10 minutes via Celery Beat.
    """
    logger.info("🧹 Checking for orphaned pipeline jobs...")

    try:
        import sys
        import os
        import redis
        sys.path.insert(0, '/app/backend')
        from app.database.connection import get_session
        from sqlalchemy import text

        # Connect to Redis
        redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
        r = redis.from_url(redis_url, decode_responses=True)

        # Get session from generator
        session_gen = get_session()
        session = next(session_gen)

        try:
            # Find jobs that have been RUNNING for more than 15 minutes without updates
            result = session.execute(
                text("""
                UPDATE pipeline_jobs
                SET status = 'FAILED',
                    error_message = 'Job orphaned due to worker restart. Please retry your document.',
                    failed_at = NOW(),
                    updated_at = NOW()
                WHERE status = 'RUNNING'
                  AND updated_at < NOW() - INTERVAL '15 minutes'
                RETURNING job_id, filename, updated_at
                """)
            )

            orphaned_jobs = result.fetchall()
            session.commit()

            orphaned_count = len(orphaned_jobs)
            celery_tasks_removed = 0

            if orphaned_count > 0:
                logger.warning(f"🧹 Cleaned up {orphaned_count} orphaned jobs:")
                for job in orphaned_jobs:
                    logger.warning(f"  - {job.job_id} ({job.filename}) - stuck since {job.updated_at}")

                    # Clean up Celery task result from Redis
                    # Celery stores results as: celery-task-meta-{task_id}
                    # Our job_id IS the Celery task_id
                    celery_key = f"celery-task-meta-{job.job_id}"
                    if r.exists(celery_key):
                        r.delete(celery_key)
                        celery_tasks_removed += 1
                        logger.info(f"    🗑️  Removed Celery task result: {celery_key}")

                logger.info(f"✅ Removed {celery_tasks_removed} Celery task results from Redis")
            else:
                logger.info("✅ No orphaned jobs found")

            return {
                'status': 'completed',
                'orphaned_jobs_cleaned': orphaned_count,
                'celery_tasks_removed': celery_tasks_removed,
                'jobs': [{'job_id': job.job_id, 'filename': job.filename} for job in orphaned_jobs]
            }
        finally:
            # Close the session generator
            try:
                next(session_gen)
            except StopIteration:
                pass

    except Exception as e:
        logger.error(f"❌ Orphaned jobs cleanup error: {str(e)}")
        raise


@celery_app.task(name='cleanup_old_files')
def cleanup_old_files():
    """
    Clean up old uploaded files from /tmp directory
    Runs daily to free up disk space
    """
    logger.info("🧹 Cleaning up old temporary files...")

    try:
        import os
        import time
        from pathlib import Path

        tmp_dir = Path('/tmp/medical-translator')
        if not tmp_dir.exists():
            logger.info("✅ No temporary directory found")
            return {'status': 'completed', 'files_removed': 0}

        # Remove files older than 24 hours
        cutoff_time = time.time() - (24 * 60 * 60)
        removed_count = 0

        for file_path in tmp_dir.glob('**/*'):
            if file_path.is_file():
                if file_path.stat().st_mtime < cutoff_time:
                    try:
                        file_path.unlink()
                        removed_count += 1
                    except Exception as e:
                        logger.warning(f"Could not delete {file_path}: {e}")

        logger.info(f"✅ Temporary files cleanup complete: {removed_count} files removed")

        return {
            'status': 'completed',
            'files_removed': removed_count
        }

    except Exception as e:
        logger.error(f"❌ File cleanup error: {str(e)}")
        raise
