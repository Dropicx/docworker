"""
Audit Log Router

Provides admin-only endpoints for viewing, filtering, and exporting audit logs.
Supports comprehensive audit trail analysis for security monitoring and compliance.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.permissions import require_admin
from app.database.auth_models import UserDB, AuditAction
from app.database.connection import get_session
from app.repositories.audit_log_repository import AuditLogRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/audit", tags=["audit"])


# ==================== PYDANTIC MODELS ====================

class AuditLogResponse(BaseModel):
    """Audit log response model"""
    id: UUID = Field(..., description="Log entry ID")
    user_id: Optional[UUID] = Field(None, description="User who performed the action")
    action: AuditAction = Field(..., description="Action performed")
    resource_type: Optional[str] = Field(None, description="Type of resource affected")
    resource_id: Optional[str] = Field(None, description="ID of resource affected")
    ip_address: Optional[str] = Field(None, description="Client IP address")
    user_agent: Optional[str] = Field(None, description="Client user agent")
    details: Optional[str] = Field(None, description="Additional details (JSON)")
    timestamp: str = Field(..., description="Event timestamp")

    class Config:
        from_attributes = True


class AuditLogListResponse(BaseModel):
    """Audit log list response model"""
    logs: list[AuditLogResponse] = Field(..., description="List of audit log entries")
    total: int = Field(..., description="Total number of logs")
    page: int = Field(..., description="Current page number")
    limit: int = Field(..., description="Number of logs per page")


class AuditSummaryResponse(BaseModel):
    """Audit summary response model"""
    time_period_hours: int = Field(..., description="Time period in hours")
    action_counts: dict = Field(..., description="Count of each action type")
    unique_users: int = Field(..., description="Number of unique users")
    unique_ips: int = Field(..., description="Number of unique IP addresses")
    total_events: int = Field(..., description="Total number of events")


class AuditFilterRequest(BaseModel):
    """Audit log filter request model"""
    user_id: Optional[UUID] = Field(None, description="Filter by user ID")
    action: Optional[AuditAction] = Field(None, description="Filter by action type")
    resource_type: Optional[str] = Field(None, description="Filter by resource type")
    resource_id: Optional[str] = Field(None, description="Filter by resource ID")
    ip_address: Optional[str] = Field(None, description="Filter by IP address")
    start_date: Optional[datetime] = Field(None, description="Start date filter")
    end_date: Optional[datetime] = Field(None, description="End date filter")
    search_term: Optional[str] = Field(None, description="Search term")


class AuditExportResponse(BaseModel):
    """Audit export response model"""
    message: str = Field(..., description="Export confirmation message")
    total_records: int = Field(..., description="Number of records exported")
    filename: str = Field(..., description="Export filename")


# ==================== AUDIT LOG ENDPOINTS ====================

@router.get("/logs", response_model=AuditLogListResponse)
async def list_audit_logs(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(100, ge=1, le=1000, description="Number of logs per page"),
    user_id: Optional[UUID] = Query(None, description="Filter by user ID"),
    action: Optional[AuditAction] = Query(None, description="Filter by action type"),
    resource_type: Optional[str] = Query(None, description="Filter by resource type"),
    hours: int = Query(24, ge=1, le=168, description="Hours to look back"),
    current_user: UserDB = Depends(require_admin()),
    db: Session = Depends(get_session)
):
    """
    List audit logs with optional filtering (admin only).

    Args:
        page: Page number for pagination
        limit: Number of logs per page
        user_id: Filter by user ID
        action: Filter by action type
        resource_type: Filter by resource type
        hours: Hours to look back
        current_user: Current authenticated admin user
        db: Database session

    Returns:
        Paginated list of audit logs
    """
    try:
        audit_repo = AuditLogRepository(db)

        # Calculate skip for pagination
        skip = (page - 1) * limit

        # Get logs based on filters
        if user_id:
            logs = audit_repo.get_by_user(user_id, skip=skip, limit=limit)
        elif action:
            logs = audit_repo.get_by_action(action, skip=skip, limit=limit)
        elif resource_type:
            logs = audit_repo.get_by_resource(resource_type, "", skip=skip, limit=limit)
        else:
            logs = audit_repo.get_recent_logs(hours=hours, skip=skip, limit=limit)

        # Convert to response format
        log_responses = [
            AuditLogResponse(
                id=log.id,
                user_id=log.user_id,
                action=log.action,
                resource_type=log.resource_type,
                resource_id=log.resource_id,
                ip_address=log.ip_address,
                user_agent=log.user_agent,
                details=log.details,
                timestamp=log.timestamp.isoformat()
            )
            for log in logs
        ]

        return AuditLogListResponse(
            logs=log_responses,
            total=len(log_responses),
            page=page,
            limit=limit
        )

    except Exception as e:
        logger.error(f"Error listing audit logs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list audit logs"
        )


@router.get("/logs/user/{user_id}", response_model=AuditLogListResponse)
async def get_user_audit_logs(
    user_id: UUID,
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(100, ge=1, le=1000, description="Number of logs per page"),
    current_user: UserDB = Depends(require_admin()),
    db: Session = Depends(get_session)
):
    """
    Get audit logs for a specific user (admin only).

    Args:
        user_id: User ID to get logs for
        page: Page number for pagination
        limit: Number of logs per page
        current_user: Current authenticated admin user
        db: Database session

    Returns:
        Paginated list of user's audit logs
    """
    try:
        audit_repo = AuditLogRepository(db)

        # Calculate skip for pagination
        skip = (page - 1) * limit

        # Get user logs
        logs = audit_repo.get_by_user(user_id, skip=skip, limit=limit)

        # Convert to response format
        log_responses = [
            AuditLogResponse(
                id=log.id,
                user_id=log.user_id,
                action=log.action,
                resource_type=log.resource_type,
                resource_id=log.resource_id,
                ip_address=log.ip_address,
                user_agent=log.user_agent,
                details=log.details,
                timestamp=log.timestamp.isoformat()
            )
            for log in logs
        ]

        return AuditLogListResponse(
            logs=log_responses,
            total=len(log_responses),
            page=page,
            limit=limit
        )

    except Exception as e:
        logger.error(f"Error getting audit logs for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user audit logs"
        )


@router.get("/logs/action/{action_type}", response_model=AuditLogListResponse)
async def get_action_audit_logs(
    action_type: AuditAction,
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(100, ge=1, le=1000, description="Number of logs per page"),
    hours: int = Query(24, ge=1, le=168, description="Hours to look back"),
    current_user: UserDB = Depends(require_admin()),
    db: Session = Depends(get_session)
):
    """
    Get audit logs for a specific action type (admin only).

    Args:
        action_type: Action type to filter by
        page: Page number for pagination
        limit: Number of logs per page
        hours: Hours to look back
        current_user: Current authenticated admin user
        db: Database session

    Returns:
        Paginated list of action-specific audit logs
    """
    try:
        audit_repo = AuditLogRepository(db)

        # Calculate skip for pagination
        skip = (page - 1) * limit

        # Get action logs
        logs = audit_repo.get_by_action(action_type, skip=skip, limit=limit)

        # Convert to response format
        log_responses = [
            AuditLogResponse(
                id=log.id,
                user_id=log.user_id,
                action=log.action,
                resource_type=log.resource_type,
                resource_id=log.resource_id,
                ip_address=log.ip_address,
                user_agent=log.user_agent,
                details=log.details,
                timestamp=log.timestamp.isoformat()
            )
            for log in logs
        ]

        return AuditLogListResponse(
            logs=log_responses,
            total=len(log_responses),
            page=page,
            limit=limit
        )

    except Exception as e:
        logger.error(f"Error getting audit logs for action {action_type}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get action audit logs"
        )


@router.get("/logs/failed-logins", response_model=AuditLogListResponse)
async def get_failed_login_logs(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(100, ge=1, le=1000, description="Number of logs per page"),
    hours: int = Query(24, ge=1, le=168, description="Hours to look back"),
    current_user: UserDB = Depends(require_admin()),
    db: Session = Depends(get_session)
):
    """
    Get failed login attempts (admin only).

    Args:
        page: Page number for pagination
        limit: Number of logs per page
        hours: Hours to look back
        current_user: Current authenticated admin user
        db: Database session

    Returns:
        Paginated list of failed login logs
    """
    try:
        audit_repo = AuditLogRepository(db)

        # Calculate skip for pagination
        skip = (page - 1) * limit

        # Get failed login logs
        logs = audit_repo.get_failed_logins(hours=hours, skip=skip, limit=limit)

        # Convert to response format
        log_responses = [
            AuditLogResponse(
                id=log.id,
                user_id=log.user_id,
                action=log.action,
                resource_type=log.resource_type,
                resource_id=log.resource_id,
                ip_address=log.ip_address,
                user_agent=log.user_agent,
                details=log.details,
                timestamp=log.timestamp.isoformat()
            )
            for log in logs
        ]

        return AuditLogListResponse(
            logs=log_responses,
            total=len(log_responses),
            page=page,
            limit=limit
        )

    except Exception as e:
        logger.error(f"Error getting failed login logs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get failed login logs"
        )


@router.get("/logs/permission-denied", response_model=AuditLogListResponse)
async def get_permission_denied_logs(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(100, ge=1, le=1000, description="Number of logs per page"),
    hours: int = Query(24, ge=1, le=168, description="Hours to look back"),
    current_user: UserDB = Depends(require_admin()),
    db: Session = Depends(get_session)
):
    """
    Get permission denied events (admin only).

    Args:
        page: Page number for pagination
        limit: Number of logs per page
        hours: Hours to look back
        current_user: Current authenticated admin user
        db: Database session

    Returns:
        Paginated list of permission denied logs
    """
    try:
        audit_repo = AuditLogRepository(db)

        # Calculate skip for pagination
        skip = (page - 1) * limit

        # Get permission denied logs
        logs = audit_repo.get_permission_denied(hours=hours, skip=skip, limit=limit)

        # Convert to response format
        log_responses = [
            AuditLogResponse(
                id=log.id,
                user_id=log.user_id,
                action=log.action,
                resource_type=log.resource_type,
                resource_id=log.resource_id,
                ip_address=log.ip_address,
                user_agent=log.user_agent,
                details=log.details,
                timestamp=log.timestamp.isoformat()
            )
            for log in logs
        ]

        return AuditLogListResponse(
            logs=log_responses,
            total=len(log_responses),
            page=page,
            limit=limit
        )

    except Exception as e:
        logger.error(f"Error getting permission denied logs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get permission denied logs"
        )


@router.get("/logs/ip/{ip_address}", response_model=AuditLogListResponse)
async def get_ip_audit_logs(
    ip_address: str,
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(100, ge=1, le=1000, description="Number of logs per page"),
    hours: int = Query(24, ge=1, le=168, description="Hours to look back"),
    current_user: UserDB = Depends(require_admin()),
    db: Session = Depends(get_session)
):
    """
    Get audit logs for a specific IP address (admin only).

    Args:
        ip_address: IP address to filter by
        page: Page number for pagination
        limit: Number of logs per page
        hours: Hours to look back
        current_user: Current authenticated admin user
        db: Database session

    Returns:
        Paginated list of IP-specific audit logs
    """
    try:
        audit_repo = AuditLogRepository(db)

        # Calculate skip for pagination
        skip = (page - 1) * limit

        # Get IP logs
        logs = audit_repo.get_logs_by_ip(ip_address, hours=hours, skip=skip, limit=limit)

        # Convert to response format
        log_responses = [
            AuditLogResponse(
                id=log.id,
                user_id=log.user_id,
                action=log.action,
                resource_type=log.resource_type,
                resource_id=log.resource_id,
                ip_address=log.ip_address,
                user_agent=log.user_agent,
                details=log.details,
                timestamp=log.timestamp.isoformat()
            )
            for log in logs
        ]

        return AuditLogListResponse(
            logs=log_responses,
            total=len(log_responses),
            page=page,
            limit=limit
        )

    except Exception as e:
        logger.error(f"Error getting audit logs for IP {ip_address}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get IP audit logs"
        )


@router.get("/summary", response_model=AuditSummaryResponse)
async def get_audit_summary(
    hours: int = Query(24, ge=1, le=168, description="Hours to look back"),
    current_user: UserDB = Depends(require_admin()),
    db: Session = Depends(get_session)
):
    """
    Get audit log summary for a time period (admin only).

    Args:
        hours: Hours to look back
        current_user: Current authenticated admin user
        db: Database session

    Returns:
        Audit log summary statistics
    """
    try:
        audit_repo = AuditLogRepository(db)

        summary = audit_repo.get_activity_summary(hours=hours)

        return AuditSummaryResponse(
            time_period_hours=summary["time_period_hours"],
            action_counts=summary["action_counts"],
            unique_users=summary["unique_users"],
            unique_ips=summary["unique_ips"],
            total_events=summary["total_events"]
        )

    except Exception as e:
        logger.error(f"Error getting audit summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get audit summary"
        )


@router.get("/export/csv")
async def export_audit_logs_csv(
    start_date: Optional[datetime] = Query(None, description="Start date for export"),
    end_date: Optional[datetime] = Query(None, description="End date for export"),
    limit: int = Query(10000, ge=1, le=50000, description="Maximum records to export"),
    current_user: UserDB = Depends(require_admin()),
    db: Session = Depends(get_session)
):
    """
    Export audit logs as CSV (admin only).

    Args:
        start_date: Start date for export
        end_date: End date for export
        limit: Maximum records to export
        current_user: Current authenticated admin user
        db: Database session

    Returns:
        CSV file download
    """
    try:
        audit_repo = AuditLogRepository(db)

        # Get CSV data
        csv_data = audit_repo.export_logs_csv(
            start_date=start_date,
            end_date=end_date,
            limit=limit
        )

        if not csv_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No audit logs found for the specified criteria"
            )

        # Generate CSV content
        import csv
        import io

        output = io.StringIO()
        fieldnames = ["timestamp", "user_id", "action", "resource_type", "resource_id", "ip_address", "user_agent", "details"]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(csv_data)

        csv_content = output.getvalue()
        output.close()

        # Generate filename
        timestamp = datetime.now(datetime.UTC).strftime("%Y%m%d_%H%M%S")
        filename = f"audit_logs_{timestamp}.csv"

        # Log export action
        audit_repo.create_log(
            user_id=current_user.id,
            action=AuditAction.AUDIT_EXPORT,
            resource_type="audit_logs",
            resource_id="csv_export",
            details={
                "start_date": start_date.isoformat() if start_date else None,
                "end_date": end_date.isoformat() if end_date else None,
                "record_count": len(csv_data)
            }
        )

        logger.info(f"Admin {current_user.email} exported {len(csv_data)} audit logs to CSV")

        # Return CSV file
        return StreamingResponse(
            io.BytesIO(csv_content.encode('utf-8')),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting audit logs to CSV: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to export audit logs"
        )


@router.post("/cleanup")
async def cleanup_old_audit_logs(
    days: int = Query(90, ge=30, le=365, description="Days to keep logs"),
    current_user: UserDB = Depends(require_admin()),
    db: Session = Depends(get_session)
):
    """
    Clean up old audit logs (admin only).

    Args:
        days: Number of days to keep logs
        current_user: Current authenticated admin user
        db: Database session

    Returns:
        Cleanup results
    """
    try:
        audit_repo = AuditLogRepository(db)

        count = audit_repo.cleanup_old_logs(days=days)

        # Log cleanup action
        audit_repo.create_log(
            user_id=current_user.id,
            action=AuditAction.SYSTEM_CLEANUP,
            resource_type="audit_logs",
            resource_id="cleanup",
            details={"days_kept": days, "logs_removed": count}
        )

        logger.info(f"Admin {current_user.email} cleaned up {count} old audit logs (kept {days} days)")

        return {
            "message": f"Cleaned up {count} old audit logs",
            "days_kept": days,
            "logs_removed": count
        }

    except Exception as e:
        logger.error(f"Error cleaning up audit logs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cleanup audit logs"
        )


# ==================== HEALTH CHECK ====================

@router.get("/health")
async def audit_health_check():
    """
    Audit service health check.

    Returns:
        Service status
    """
    return {
        "status": "healthy",
        "service": "audit",
        "version": "1.0.0"
    }
