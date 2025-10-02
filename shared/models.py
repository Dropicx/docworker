"""
Shared Pydantic Models

Data models shared between backend and worker services.
"""
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class TaskStatus(str, Enum):
    """Task status enumeration"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ProcessingStatus(str, Enum):
    """Document processing status"""
    UPLOADED = "uploaded"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskInfo(BaseModel):
    """Task information model"""
    task_id: str
    task_name: str
    status: TaskStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress: int = Field(default=0, ge=0, le=100)
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class DocumentProcessingTask(BaseModel):
    """Document processing task configuration"""
    processing_id: str
    file_path: str
    target_language: str = "en"
    options: Optional[Dict[str, Any]] = None
    priority: int = Field(default=5, ge=1, le=10)
    callback_url: Optional[str] = None


class DocumentProcessingResult(BaseModel):
    """Document processing result"""
    processing_id: str
    status: ProcessingStatus
    output_file: Optional[str] = None
    extracted_text: Optional[str] = None
    translation: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    processing_time: Optional[float] = None


class QueueStats(BaseModel):
    """Queue statistics"""
    queue_name: str
    pending_tasks: int
    active_tasks: int
    completed_tasks: int
    failed_tasks: int
    average_processing_time: Optional[float] = None


class WorkerStats(BaseModel):
    """Worker statistics"""
    worker_id: str
    status: str
    active_tasks: int
    completed_tasks: int
    failed_tasks: int
    uptime: float
    last_heartbeat: datetime


class HealthCheck(BaseModel):
    """Health check response"""
    status: str
    timestamp: datetime
    services: Dict[str, str]
    version: str
    uptime: float
