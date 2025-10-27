"""
Audit Log Repository

Provides data access methods for audit logging including creation,
querying, filtering, and export operations for security and compliance.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc

from app.database.auth_models import AuditLogDB, AuditAction
from app.repositories.base_repository import BaseRepository

logger = logging.getLogger(__name__)


class AuditLogRepository(BaseRepository[AuditLogDB]):
    """Repository for audit log data access operations."""

    def __init__(self, db: Session):
        super().__init__(db, AuditLogDB)

    def create_log(
        self,
        user_id: UUID | None,
        action: AuditAction,
        resource_type: str | None = None,
        resource_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        details: dict[str, Any | None] = None
    ) -> AuditLogDB:
        """
        Create a new audit log entry.

        Args:
            user_id: User who performed the action (None for system actions)
            action: Type of action performed
            resource_type: Type of resource affected
            resource_id: ID of resource affected
            ip_address: IP address of the request
            user_agent: User agent string
            details: Additional context as dictionary

        Returns:
            Created audit log instance
        """
        try:
            # Convert details dict to JSON string if provided
            details_json = None
            if details:
                import json
                details_json = json.dumps(details)

            audit_log = self.create(
                user_id=user_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                ip_address=ip_address,
                user_agent=user_agent,
                details=details_json,
                timestamp=datetime.now(datetime.UTC)
            )

            logger.debug(f"Created audit log for action {action} by user {user_id}")
            return audit_log
        except Exception as e:
            logger.error(f"Error creating audit log: {e}")
            raise

    def get_by_user(
        self,
        user_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> list[AuditLogDB]:
        """
        Get audit logs for a specific user.

        Args:
            user_id: User's UUID
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of audit log entries
        """
        try:
            return self.db.query(AuditLogDB).filter(
                AuditLogDB.user_id == user_id
            ).order_by(desc(AuditLogDB.timestamp)).offset(skip).limit(limit).all()
        except Exception as e:
            logger.error(f"Error getting audit logs for user {user_id}: {e}")
            raise

    def get_by_action(
        self,
        action: AuditAction,
        skip: int = 0,
        limit: int = 100
    ) -> list[AuditLogDB]:
        """
        Get audit logs by action type.

        Args:
            action: Action type to filter by
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of audit log entries
        """
        try:
            return self.db.query(AuditLogDB).filter(
                AuditLogDB.action == action
            ).order_by(desc(AuditLogDB.timestamp)).offset(skip).limit(limit).all()
        except Exception as e:
            logger.error(f"Error getting audit logs for action {action}: {e}")
            raise

    def get_by_resource(
        self,
        resource_type: str,
        resource_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> list[AuditLogDB]:
        """
        Get audit logs for a specific resource.

        Args:
            resource_type: Type of resource
            resource_id: ID of resource
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of audit log entries
        """
        try:
            return self.db.query(AuditLogDB).filter(
                and_(
                    AuditLogDB.resource_type == resource_type,
                    AuditLogDB.resource_id == resource_id
                )
            ).order_by(desc(AuditLogDB.timestamp)).offset(skip).limit(limit).all()
        except Exception as e:
            logger.error(f"Error getting audit logs for resource {resource_type}:{resource_id}: {e}")
            raise

    def get_recent_logs(
        self,
        hours: int = 24,
        skip: int = 0,
        limit: int = 100
    ) -> list[AuditLogDB]:
        """
        Get recent audit logs.

        Args:
            hours: Number of hours to look back
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of recent audit log entries
        """
        try:
            cutoff_time = datetime.now(datetime.UTC) - timedelta(hours=hours)
            return self.db.query(AuditLogDB).filter(
                AuditLogDB.timestamp >= cutoff_time
            ).order_by(desc(AuditLogDB.timestamp)).offset(skip).limit(limit).all()
        except Exception as e:
            logger.error(f"Error getting recent audit logs: {e}")
            raise

    def get_failed_logins(
        self,
        hours: int = 24,
        skip: int = 0,
        limit: int = 100
    ) -> list[AuditLogDB]:
        """
        Get failed login attempts.

        Args:
            hours: Number of hours to look back
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of failed login audit log entries
        """
        try:
            cutoff_time = datetime.now(datetime.UTC) - timedelta(hours=hours)
            return self.db.query(AuditLogDB).filter(
                and_(
                    AuditLogDB.action == AuditAction.AUTH_FAILURE,
                    AuditLogDB.timestamp >= cutoff_time
                )
            ).order_by(desc(AuditLogDB.timestamp)).offset(skip).limit(limit).all()
        except Exception as e:
            logger.error(f"Error getting failed login logs: {e}")
            raise

    def get_permission_denied(
        self,
        hours: int = 24,
        skip: int = 0,
        limit: int = 100
    ) -> list[AuditLogDB]:
        """
        Get permission denied events.

        Args:
            hours: Number of hours to look back
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of permission denied audit log entries
        """
        try:
            cutoff_time = datetime.now(datetime.UTC) - timedelta(hours=hours)
            return self.db.query(AuditLogDB).filter(
                and_(
                    AuditLogDB.action == AuditAction.PERMISSION_DENIED,
                    AuditLogDB.timestamp >= cutoff_time
                )
            ).order_by(desc(AuditLogDB.timestamp)).offset(skip).limit(limit).all()
        except Exception as e:
            logger.error(f"Error getting permission denied logs: {e}")
            raise

    def search_logs(
        self,
        search_term: str,
        skip: int = 0,
        limit: int = 100
    ) -> list[AuditLogDB]:
        """
        Search audit logs by various fields.

        Args:
            search_term: Search term
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of matching audit log entries
        """
        try:
            search_pattern = f"%{search_term}%"
            return self.db.query(AuditLogDB).filter(
                or_(
                    AuditLogDB.resource_type.ilike(search_pattern),
                    AuditLogDB.resource_id.ilike(search_pattern),
                    AuditLogDB.ip_address.ilike(search_pattern),
                    AuditLogDB.details.ilike(search_pattern)
                )
            ).order_by(desc(AuditLogDB.timestamp)).offset(skip).limit(limit).all()
        except Exception as e:
            logger.error(f"Error searching audit logs with term '{search_term}': {e}")
            raise

    def get_logs_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        skip: int = 0,
        limit: int = 100
    ) -> list[AuditLogDB]:
        """
        Get audit logs within a date range.

        Args:
            start_date: Start date
            end_date: End date
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of audit log entries in date range
        """
        try:
            return self.db.query(AuditLogDB).filter(
                and_(
                    AuditLogDB.timestamp >= start_date,
                    AuditLogDB.timestamp <= end_date
                )
            ).order_by(desc(AuditLogDB.timestamp)).offset(skip).limit(limit).all()
        except Exception as e:
            logger.error(f"Error getting audit logs by date range: {e}")
            raise

    def get_logs_by_ip(
        self,
        ip_address: str,
        hours: int = 24,
        skip: int = 0,
        limit: int = 100
    ) -> list[AuditLogDB]:
        """
        Get audit logs for a specific IP address.

        Args:
            ip_address: IP address to filter by
            hours: Number of hours to look back
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of audit log entries for the IP
        """
        try:
            cutoff_time = datetime.now(datetime.UTC) - timedelta(hours=hours)
            return self.db.query(AuditLogDB).filter(
                and_(
                    AuditLogDB.ip_address == ip_address,
                    AuditLogDB.timestamp >= cutoff_time
                )
            ).order_by(desc(AuditLogDB.timestamp)).offset(skip).limit(limit).all()
        except Exception as e:
            logger.error(f"Error getting audit logs for IP {ip_address}: {e}")
            raise

    def count_by_action(self, action: AuditAction) -> int:
        """
        Count audit logs by action type.

        Args:
            action: Action type to count

        Returns:
            Number of audit log entries
        """
        try:
            return self.db.query(AuditLogDB).filter(AuditLogDB.action == action).count()
        except Exception as e:
            logger.error(f"Error counting audit logs for action {action}: {e}")
            raise

    def count_by_user(self, user_id: UUID) -> int:
        """
        Count audit logs for a user.

        Args:
            user_id: User's UUID

        Returns:
            Number of audit log entries
        """
        try:
            return self.db.query(AuditLogDB).filter(AuditLogDB.user_id == user_id).count()
        except Exception as e:
            logger.error(f"Error counting audit logs for user {user_id}: {e}")
            raise

    def get_activity_summary(
        self,
        hours: int = 24
    ) -> dict[str, Any]:
        """
        Get activity summary for a time period.

        Args:
            hours: Number of hours to look back

        Returns:
            Dictionary with activity summary
        """
        try:
            cutoff_time = datetime.now(datetime.UTC) - timedelta(hours=hours)

            # Count by action
            action_counts = {}
            for action in AuditAction:
                count = self.db.query(AuditLogDB).filter(
                    and_(
                        AuditLogDB.action == action,
                        AuditLogDB.timestamp >= cutoff_time
                    )
                ).count()
                action_counts[action.value] = count

            # Count unique users
            unique_users = self.db.query(AuditLogDB.user_id).filter(
                and_(
                    AuditLogDB.user_id.isnot(None),
                    AuditLogDB.timestamp >= cutoff_time
                )
            ).distinct().count()

            # Count unique IPs
            unique_ips = self.db.query(AuditLogDB.ip_address).filter(
                and_(
                    AuditLogDB.ip_address.isnot(None),
                    AuditLogDB.timestamp >= cutoff_time
                )
            ).distinct().count()

            return {
                "time_period_hours": hours,
                "action_counts": action_counts,
                "unique_users": unique_users,
                "unique_ips": unique_ips,
                "total_events": sum(action_counts.values())
            }
        except Exception as e:
            logger.error(f"Error getting activity summary: {e}")
            raise

    def cleanup_old_logs(self, days: int = 90) -> int:
        """
        Delete old audit logs (for data retention).

        Args:
            days: Number of days to keep logs

        Returns:
            Number of logs deleted
        """
        try:
            cutoff_date = datetime.now(datetime.UTC) - timedelta(days=days)
            old_logs = self.db.query(AuditLogDB).filter(
                AuditLogDB.timestamp < cutoff_date
            ).all()

            count = len(old_logs)
            for log in old_logs:
                self.db.delete(log)

            if count > 0:
                self.db.commit()
                logger.info(f"Cleaned up {count} old audit logs")

            return count
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error cleaning up old audit logs: {e}")
            raise

    def export_logs_csv(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        limit: int = 10000
    ) -> list[dict[str, Any]]:
        """
        Export audit logs as CSV data.

        Args:
            start_date: Start date for export
            end_date: End date for export
            limit: Maximum number of records to export

        Returns:
            List of dictionaries with log data
        """
        try:
            query = self.db.query(AuditLogDB)

            if start_date:
                query = query.filter(AuditLogDB.timestamp >= start_date)
            if end_date:
                query = query.filter(AuditLogDB.timestamp <= end_date)

            logs = query.order_by(desc(AuditLogDB.timestamp)).limit(limit).all()

            # Convert to dictionary format for CSV export
            csv_data = []
            for log in logs:
                csv_data.append({
                    "timestamp": log.timestamp.isoformat(),
                    "user_id": str(log.user_id) if log.user_id else None,
                    "action": log.action.value,
                    "resource_type": log.resource_type,
                    "resource_id": log.resource_id,
                    "ip_address": log.ip_address,
                    "user_agent": log.user_agent,
                    "details": log.details
                })

            logger.info(f"Exported {len(csv_data)} audit logs to CSV format")
            return csv_data
        except Exception as e:
            logger.error(f"Error exporting audit logs to CSV: {e}")
            raise
