"""Cleanup service for temporary files, memory store, and database jobs.

Provides automated and manual cleanup utilities for medical document processing.
Manages three cleanup domains: system temp files, in-memory processing store,
and database pipeline jobs. Supports regular cleanup + emergency procedures.

**Cleanup Domains**:
    - System Temp Files: Files in OS temp dir (medical_*, uploaded_*, processed_*)
    - Memory Store: In-memory processing data (global processing_store dict)
    - Database Jobs: Pipeline execution records (PipelineJobDB entries)

**Retention Policies**:
    - Temp Files: 1 hour (immediate processing completion)
    - Memory Store: 30 minutes (active processing window)
    - Database Jobs: 24 hours (configurable via DB_RETENTION_HOURS env var)

**Security Features**:
    - Secure temp file creation with 0o600 permissions (owner-only)
    - Secure deletion with file overwrite before removal
    - GDPR compliance through automated data retention

**Usage**:
    Regular cleanup (scheduled):
        >>> await cleanup_temp_files()  # Returns count of files removed

    Emergency cleanup (high memory):
        >>> await emergency_cleanup()  # Aggressive cleanup of all domains

Module-level Constants:
    processing_store (dict): Global in-memory store for active processing jobs
    MAX_DATA_AGE (timedelta): Memory store retention (30 minutes)
    DB_RETENTION_HOURS (int): Database job retention from env (default 24h)
"""

from datetime import datetime, timedelta
import gc
import logging
import os
from pathlib import Path
import tempfile
from typing import Any

logger = logging.getLogger(__name__)

# Globaler In-Memory Store für Verarbeitungsdaten
processing_store: dict[str, dict[str, Any]] = {}

# Maximale Lebenszeit für temporäre Daten (30 Minuten)
MAX_DATA_AGE = timedelta(minutes=30)

# Database retention period (24 hours for development, configurable via env)
DB_RETENTION_HOURS = int(os.getenv("DB_RETENTION_HOURS", "24"))


async def cleanup_temp_files():
    """Orchestrate comprehensive cleanup across all domains.

    Main cleanup entry point that sequentially cleans temp files, memory store,
    and database jobs. Runs garbage collection after cleanup. Safe to call
    repeatedly from scheduled tasks.

    Returns:
        int: Number of temp files removed (for logging/monitoring)

    Example:
        >>> # Scheduled cleanup (e.g., FastAPI lifespan or cron)
        >>> files_removed = await cleanup_temp_files()
        >>> print(f"Cleaned {files_removed} files")
        Cleaned 15 files

    Note:
        **Cleanup Sequence**:
        1. System temp files (1 hour retention)
        2. In-memory processing store (30 minute retention)
        3. Database pipeline jobs (24 hour retention, configurable)
        4. Python garbage collection

        **Error Handling**:
        Exceptions logged but don't propagate - cleanup continues.
        Returns 0 on error to allow monitoring without disruption.

        **Performance**:
        - Temp files: O(n) scan of temp directory
        - Memory store: O(n) iteration of processing_store dict
        - Database jobs: Single query with age filter
        - Typical: 100-500ms for small installations

        **Logging**:
        Logs summary if any items removed, individual items at DEBUG level.
    """
    try:
        # Cleanup temporäre Dateien im System temp
        files_removed = await cleanup_system_temp_files()

        # Cleanup In-Memory Store
        items_removed = await cleanup_memory_store()

        # Cleanup old database jobs
        jobs_removed = await cleanup_old_database_jobs()

        # Garbage Collection
        gc.collect()

        if files_removed > 0 or items_removed > 0 or jobs_removed > 0:
            logger.info(
                f"🧹 Cleanup: {files_removed} files, {items_removed} memory items, {jobs_removed} database jobs removed"
            )

        return files_removed

    except Exception as e:
        logger.error(f"❌ Cleanup-Fehler: {e}")
        return 0


async def cleanup_system_temp_files():
    """Bereinigt temporäre Dateien im Systemverzeichnis"""
    files_removed = 0
    try:
        temp_dir = tempfile.gettempdir()
        current_time = datetime.now()

        # Suche nach medizinischen Dokumenten-Dateien
        for root, _dirs, files in os.walk(temp_dir):
            for file in files:
                if file.startswith(("medical_", "uploaded_", "processed_")):
                    file_path = Path(root) / file
                    try:
                        # Datei älter als 1 Stunde?
                        file_time = datetime.fromtimestamp(file_path.stat().st_ctime)
                        if current_time - file_time > timedelta(hours=1):
                            file_path.unlink()
                            files_removed += 1
                            logger.debug(f"🗑️ Temporäre Datei gelöscht: {file}")
                    except (OSError, FileNotFoundError):
                        # Datei bereits gelöscht oder nicht zugreifbar
                        continue

        return files_removed

    except Exception as e:
        logger.error(f"❌ System-Temp-Cleanup Fehler: {e}")
        return files_removed


async def cleanup_memory_store():
    """Bereinigt den In-Memory Store von alten Daten"""
    items_removed = 0
    try:
        current_time = datetime.now()
        expired_keys = []

        for processing_id, data in processing_store.items():
            created_time = data.get("created_at", current_time)

            # Daten älter als MAX_DATA_AGE?
            if current_time - created_time > MAX_DATA_AGE:
                expired_keys.append(processing_id)

        # Abgelaufene Daten löschen
        for key in expired_keys:
            del processing_store[key]
            items_removed += 1
            logger.debug(f"🗑️ Abgelaufene Verarbeitungsdaten gelöscht: {key}")

        if len(processing_store) > 0:
            logger.debug(f"📊 Aktive Verarbeitungen: {len(processing_store)}")

        return items_removed

    except Exception as e:
        logger.error(f"❌ Memory-Store-Cleanup Fehler: {e}")
        return items_removed


async def cleanup_old_database_jobs():
    """Delete pipeline jobs and related PII-containing records older than retention period.

    Removes completed and failed jobs older than DB_RETENTION_HOURS along with
    their related records in pipeline_step_executions (contains PII text) and
    user_feedback (where consent not given). Complies with GDPR data retention.

    IMPORTANT: ai_interaction_logs are PRESERVED for cost/usage statistics.
    They only contain token counts and costs, no PII.

    Returns:
        int: Number of database jobs deleted

    Note:
        **Cascading Deletion**:
        When a job is deleted, these related records are also deleted:
        - pipeline_step_executions (by job_id) - contains input/output text with potential PII
        - user_feedback (by processing_id, only if feedback consent also not given)

        **PRESERVED for statistics**:
        - ai_interaction_logs - token counts, costs, model usage (no PII)

        **GDPR Compliance**:
        - Jobs with data_consent_given = True are preserved
        - Step executions (with PII text) follow the job's consent status
        - Orphaned step executions are also cleaned up
    """
    jobs_removed = 0
    step_executions_removed = 0
    feedback_removed = 0

    try:
        # Import here to avoid circular imports
        from sqlalchemy import or_

        from app.database.connection import get_db_session
        from app.database.modular_pipeline_models import (
            PipelineJobDB,
            PipelineStepExecutionDB,
            UserFeedbackDB,
        )

        db = next(get_db_session())

        try:
            cutoff_time = datetime.now() - timedelta(hours=DB_RETENTION_HOURS)

            # Find jobs older than retention period without consent
            old_jobs = (
                db.query(PipelineJobDB)
                .filter(
                    PipelineJobDB.uploaded_at < cutoff_time,
                    or_(
                        PipelineJobDB.data_consent_given.is_(False),
                        PipelineJobDB.data_consent_given.is_(None),
                    ),
                )
                .all()
            )

            if old_jobs:
                logger.info(
                    f"🗑️ Found {len(old_jobs)} jobs older than {DB_RETENTION_HOURS} hours (without consent)"
                )

                for job in old_jobs:
                    job_age_hours = (datetime.now() - job.uploaded_at).total_seconds() / 3600
                    logger.debug(
                        f"   Deleting job {job.processing_id} (age: {job_age_hours:.1f}h, status: {job.status})"
                    )

                    # Delete related step executions (contains PII text)
                    step_count = (
                        db.query(PipelineStepExecutionDB)
                        .filter(PipelineStepExecutionDB.job_id == job.job_id)
                        .delete(synchronize_session=False)
                    )
                    step_executions_removed += step_count

                    # NOTE: ai_interaction_logs are PRESERVED for cost statistics
                    # They only contain token counts and costs, no PII

                    # Delete feedback only if feedback's consent is also not given
                    feedback_count = (
                        db.query(UserFeedbackDB)
                        .filter(
                            UserFeedbackDB.processing_id == job.processing_id,
                            or_(
                                UserFeedbackDB.data_consent_given.is_(False),
                                UserFeedbackDB.data_consent_given.is_(None),
                            ),
                        )
                        .delete(synchronize_session=False)
                    )
                    feedback_removed += feedback_count

                    # Delete the job itself
                    db.delete(job)
                    jobs_removed += 1

                db.commit()
                logger.info(
                    f"✅ Deleted {jobs_removed} jobs, {step_executions_removed} step executions, "
                    f"{feedback_removed} feedback records (ai_interaction_logs preserved for statistics)"
                )
            else:
                logger.debug(
                    f"📊 No jobs older than {DB_RETENTION_HOURS} hours found (excluding consented jobs)"
                )

            # Also cleanup orphaned step executions (records without parent job)
            orphaned_cleaned = await cleanup_orphaned_step_executions(db)
            if orphaned_cleaned > 0:
                logger.info(f"🧹 Cleaned {orphaned_cleaned} orphaned step executions")

            # Log count of preserved jobs with consent (for monitoring)
            consented_jobs_count = (
                db.query(PipelineJobDB)
                .filter(
                    PipelineJobDB.uploaded_at < cutoff_time,
                    PipelineJobDB.data_consent_given.is_(True),
                )
                .count()
            )
            if consented_jobs_count > 0:
                logger.info(f"📋 Preserved {consented_jobs_count} old jobs with user consent")

            return jobs_removed

        finally:
            db.close()

    except Exception as e:
        logger.error(f"❌ Database cleanup error: {e}")
        return jobs_removed


async def cleanup_orphaned_step_executions(db=None):
    """Clean up orphaned step executions that have no parent job.

    Step executions contain input/output text which may have PII, so they
    must be deleted when their parent job is gone.

    NOTE: ai_interaction_logs are NOT deleted - they contain only token counts
    and costs for statistics, no PII.

    Returns:
        int: Number of orphaned step executions deleted
    """
    total_removed = 0
    close_db = False

    try:
        from sqlalchemy import or_

        from app.database.modular_pipeline_models import (
            PipelineJobDB,
            PipelineStepExecutionDB,
            UserFeedbackDB,
        )

        if db is None:
            from app.database.connection import get_db_session

            db = next(get_db_session())
            close_db = True

        try:
            # Get all valid job_ids
            valid_job_ids = {j.job_id for j in db.query(PipelineJobDB.job_id).all()}
            valid_processing_ids = {
                j.processing_id for j in db.query(PipelineJobDB.processing_id).all()
            }

            # Find and delete orphaned step executions (job_id not in valid jobs)
            # These contain PII text and must be cleaned
            if valid_job_ids:
                orphaned_steps = (
                    db.query(PipelineStepExecutionDB)
                    .filter(~PipelineStepExecutionDB.job_id.in_(valid_job_ids))
                    .delete(synchronize_session=False)
                )
            else:
                # No jobs exist, all step executions are orphaned
                orphaned_steps = db.query(PipelineStepExecutionDB).delete(synchronize_session=False)

            if orphaned_steps > 0:
                logger.info(
                    f"   🗑️ Deleted {orphaned_steps} orphaned step executions (contained PII text)"
                )
                total_removed += orphaned_steps

            # NOTE: ai_interaction_logs are PRESERVED for cost/usage statistics
            # They only contain token counts and costs, no PII

            # Find and delete orphaned feedback where consent NOT given
            # (feedback with consent may be kept for analysis even without job)
            if valid_processing_ids:
                orphaned_feedback = (
                    db.query(UserFeedbackDB)
                    .filter(
                        ~UserFeedbackDB.processing_id.in_(valid_processing_ids),
                        or_(
                            UserFeedbackDB.data_consent_given.is_(False),
                            UserFeedbackDB.data_consent_given.is_(None),
                        ),
                    )
                    .delete(synchronize_session=False)
                )
            else:
                # No jobs exist, delete feedback without consent
                orphaned_feedback = (
                    db.query(UserFeedbackDB)
                    .filter(
                        or_(
                            UserFeedbackDB.data_consent_given.is_(False),
                            UserFeedbackDB.data_consent_given.is_(None),
                        )
                    )
                    .delete(synchronize_session=False)
                )

            if orphaned_feedback > 0:
                logger.info(
                    f"   🗑️ Deleted {orphaned_feedback} orphaned feedback records (without consent)"
                )
                total_removed += orphaned_feedback

            if total_removed > 0:
                db.commit()

            return total_removed

        finally:
            if close_db:
                db.close()

    except Exception as e:
        logger.error(f"❌ Orphaned records cleanup error: {e}")
        return total_removed


def add_to_processing_store(processing_id: str, data: dict[str, Any]):
    """Fügt Daten zum Processing Store hinzu"""
    data["created_at"] = datetime.now()
    processing_store[processing_id] = data


def get_from_processing_store(processing_id: str) -> dict[str, Any]:
    """Holt Daten aus dem Processing Store"""
    return processing_store.get(processing_id, {})


def update_processing_store(processing_id: str, updates: dict[str, Any]):
    """Aktualisiert Daten im Processing Store"""
    if processing_id in processing_store:
        processing_store[processing_id].update(updates)


def remove_from_processing_store(processing_id: str):
    """Entfernt Daten aus dem Processing Store"""
    if processing_id in processing_store:
        del processing_store[processing_id]
        logger.debug(f"🗑️ Verarbeitungsdaten manuell gelöscht: {processing_id}")


async def create_secure_temp_file(prefix: str = "medical_", suffix: str = "") -> str:
    """Create secure temporary file with restricted permissions for medical data.

    Creates temp file in system temp directory with owner-only permissions (0o600).
    Designed for secure storage of sensitive medical documents during processing.

    Args:
        prefix: Filename prefix for identification (default: "medical_")
        suffix: Filename suffix for file type (e.g., ".pdf", ".txt")

    Returns:
        str: Absolute path to created temp file

    Raises:
        Exception: If file creation fails (propagated for caller handling)

    Example:
        >>> # Store uploaded medical PDF temporarily
        >>> temp_path = await create_secure_temp_file(
        ...     prefix="medical_upload_",
        ...     suffix=".pdf"
        ... )
        >>> print(temp_path)
        '/tmp/medical_upload_a3f7b2e1.pdf'
        >>> # Use file, then cleanup
        >>> await secure_delete_file(temp_path)

    Note:
        **Security Features**:
        - Permissions: 0o600 (owner read/write only, no group/other access)
        - Location: OS temp directory (isolated per-user on multi-user systems)
        - File descriptor: Immediately closed after creation

        **GDPR Compliance**:
        Restrictive permissions prevent unauthorized access to medical data.
        Files should be deleted via secure_delete_file() after processing.

        **Cleanup**:
        Files with medical_* prefix automatically cleaned by
        cleanup_system_temp_files() after 1 hour if not manually deleted.

        **Use Cases**:
        - Temporary storage during document upload/processing
        - Intermediate file format conversions
        - Cache for expensive OCR results
    """
    try:
        fd, temp_path = tempfile.mkstemp(prefix=prefix, suffix=suffix)
        os.close(fd)  # Dateideskriptor schließen

        # Berechtigungen setzen (nur Besitzer kann lesen/schreiben)
        Path(temp_path).chmod(0o600)

        return temp_path

    except Exception as e:
        logger.error(f"❌ Temp-Datei-Erstellung Fehler: {e}")
        raise


async def secure_delete_file(file_path: str):
    """Securely delete file by overwriting before removal.

    Implements basic secure deletion by overwriting file contents with random
    data before unlinking. Prevents simple file recovery from disk. Designed
    for medical documents requiring GDPR-compliant disposal.

    Args:
        file_path: Absolute path to file to delete

    Returns:
        None

    Example:
        >>> # After processing medical document
        >>> temp_file = await create_secure_temp_file(suffix=".pdf")
        >>> # ... process file ...
        >>> await secure_delete_file(temp_file)  # Secure cleanup

    Note:
        **Deletion Process**:
        1. Check file exists (skip if already deleted)
        2. Overwrite file contents with random bytes (os.urandom)
        3. Remove file from filesystem (os.remove)

        **Security Level**:
        - Basic protection: Single-pass random overwrite
        - NOT military-grade: Modern SSDs may cache data
        - Sufficient for: GDPR compliance, basic security

        **Advanced Deletion**:
        For higher security needs, consider:
        - Multiple overwrite passes (DoD 5220.22-M standard)
        - SSD-specific secure erase commands
        - Full disk encryption as primary protection

        **Error Handling**:
        Exceptions logged but don't propagate - allows cleanup to continue.
        Missing files silently ignored (idempotent operation).

        **Performance**:
        Overwrite time proportional to file size (~1-5MB/s for large files).
        Consider async execution for large files to avoid blocking.
    """
    try:
        path = Path(file_path)
        if path.exists():
            # Datei überschreiben vor dem Löschen (einfache Sicherung)
            file_size = path.stat().st_size
            path.write_bytes(os.urandom(file_size))

            # Datei löschen
            path.unlink()
            logger.debug(f"🔒 Datei sicher gelöscht: {path.name}")

    except Exception as e:
        logger.error(f"❌ Sicheres Löschen fehlgeschlagen: {e}")


def get_memory_usage() -> dict[str, Any]:
    """Gibt Speichernutzung zurück"""
    try:
        import psutil

        process = psutil.Process()
        memory_info = process.memory_info()

        return {
            "rss": memory_info.rss,  # Resident Set Size
            "vms": memory_info.vms,  # Virtual Memory Size
            "percent": process.memory_percent(),
            "processing_store_size": len(processing_store),
        }
    except ImportError:
        return {
            "processing_store_size": len(processing_store),
            "note": "psutil nicht verfügbar für detaillierte Speicherinfo",
        }


async def emergency_cleanup():
    """Emergency cleanup for critical memory/disk situations.

    Aggressive cleanup that clears ALL in-memory data and completed database jobs,
    regardless of age. Used when system resources critically low. Should only be
    called when normal cleanup insufficient or memory threshold exceeded.

    Returns:
        None

    Example:
        >>> # Monitor memory usage
        >>> memory = get_memory_usage()
        >>> if memory['percent'] > 90:
        ...     logger.warning("High memory usage, triggering emergency cleanup")
        ...     await emergency_cleanup()

    Note:
        **Emergency Actions** (order of execution):
        1. Clear ALL processing_store data (lose in-progress tracking)
        2. Aggressive temp file cleanup (all medical_* files)
        3. Delete ALL completed database jobs (ignore retention policy)
        4. Force garbage collection (3 passes for thorough cleanup)

        **Impact**:
        - ⚠️ Loses in-progress processing state (users may see errors)
        - ⚠️ Deletes completed jobs regardless of age (audit trail lost)
        - ✅ Frees maximum possible memory immediately
        - ✅ System can continue operating vs. crash

        **When to Use**:
        - Memory usage > 90% and growing
        - Disk space critically low
        - Too many failed jobs accumulating
        - Production incident requiring immediate action

        **Recovery**:
        - In-progress jobs: Users need to re-upload documents
        - Completed jobs: Historical data lost but system functional
        - System recovers automatically after cleanup

        **Alternative**:
        For normal situations, use cleanup_temp_files() which respects
        retention policies and preserves in-progress processing.

        **Monitoring**:
        Log warning messages indicate emergency cleanup was triggered.
        Should investigate root cause (memory leaks, job accumulation).
    """
    try:
        logger.warning("🚨 Notfall-Bereinigung gestartet...")

        # Alle Verarbeitungsdaten löschen
        processing_store.clear()

        # Aggressive temp file cleanup
        await cleanup_system_temp_files()

        # Aggressive database cleanup (delete all completed jobs)
        await cleanup_all_completed_jobs()

        # Force garbage collection
        for _ in range(3):
            gc.collect()

        logger.info("✅ Notfall-Bereinigung abgeschlossen")

    except Exception as e:
        logger.error(f"❌ Notfall-Bereinigung Fehler: {e}")


async def cleanup_all_completed_jobs():
    """
    Emergency function: Deletes ALL completed jobs and related PII-containing records.
    Used only during emergency cleanup. Cascades to step_executions and feedback.

    NOTE: ai_interaction_logs are PRESERVED for cost/usage statistics.
    """
    jobs_removed = 0
    step_executions_removed = 0
    feedback_removed = 0

    try:
        from app.database.connection import get_db_session
        from app.database.modular_pipeline_models import (
            PipelineJobDB,
            PipelineStepExecutionDB,
            StepExecutionStatus,
            UserFeedbackDB,
        )

        db = next(get_db_session())

        try:
            # Delete all completed jobs with cascade
            completed_jobs = (
                db.query(PipelineJobDB)
                .filter(PipelineJobDB.status == StepExecutionStatus.COMPLETED)
                .all()
            )

            for job in completed_jobs:
                # Delete related step executions (contains PII text)
                step_count = (
                    db.query(PipelineStepExecutionDB)
                    .filter(PipelineStepExecutionDB.job_id == job.job_id)
                    .delete(synchronize_session=False)
                )
                step_executions_removed += step_count

                # NOTE: ai_interaction_logs are PRESERVED for cost statistics

                # Delete related feedback (emergency mode ignores consent)
                feedback_count = (
                    db.query(UserFeedbackDB)
                    .filter(UserFeedbackDB.processing_id == job.processing_id)
                    .delete(synchronize_session=False)
                )
                feedback_removed += feedback_count

                db.delete(job)
                jobs_removed += 1

            db.commit()
            logger.warning(
                f"🚨 Emergency: Deleted {jobs_removed} completed jobs, "
                f"{step_executions_removed} step executions, {feedback_removed} feedback records "
                f"(ai_interaction_logs preserved for statistics)"
            )

            return jobs_removed

        finally:
            db.close()

    except Exception as e:
        logger.error(f"❌ Emergency database cleanup error: {e}")
        return jobs_removed
