"""
AI logging service for comprehensive interaction tracking
"""

import logging
import time
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from contextlib import contextmanager

from app.services.database_service import DatabaseService
from app.database.models import ProcessingStepEnum, DocumentClassEnum

logger = logging.getLogger(__name__)

class AILoggingService:
    """Service for logging AI interactions"""
    
    def __init__(self, session: Session):
        self.session = session
        self.db_service = DatabaseService(session)

    @contextmanager
    def log_interaction(
        self,
        processing_id: str,
        step_name: str,
        document_type: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        request_id: Optional[str] = None
    ):
        """Context manager for logging AI interactions"""
        start_time = time.time()
        input_text = None
        output_text = None
        error_message = None
        status = "success"
        
        try:
            yield {
                "set_input": lambda text: setattr(self, '_input_text', text),
                "set_output": lambda text: setattr(self, '_output_text', text),
                "set_error": lambda error: setattr(self, '_error_message', error)
            }
            
            # Get values from context
            input_text = getattr(self, '_input_text', None)
            output_text = getattr(self, '_output_text', None)
            error_message = getattr(self, '_error_message', None)
            
            if error_message:
                status = "error"
                
        except Exception as e:
            status = "error"
            error_message = str(e)
            logger.error(f"Error in AI interaction logging: {e}")
            
        finally:
            # Calculate processing time
            processing_time_ms = int((time.time() - start_time) * 1000)
            
            # Log to database
            self.db_service.log_ai_interaction(
                processing_id=processing_id,
                step_name=ProcessingStepEnum(step_name),
                input_text=input_text,
                output_text=output_text,
                processing_time_ms=processing_time_ms,
                status=status,
                error_message=error_message,
                document_type=DocumentClassEnum(document_type) if document_type else None,
                user_id=user_id,
                session_id=session_id,
                request_id=request_id
            )

    def log_medical_validation(
        self,
        processing_id: str,
        input_text: str,
        is_medical: bool,
        confidence: float,
        method: str,
        document_type: Optional[str] = None
    ):
        """Log medical validation step"""
        self.db_service.log_ai_interaction(
            processing_id=processing_id,
            step_name=ProcessingStepEnum.MEDICAL_VALIDATION,
            input_text=input_text,
            output_text=f"Medical: {is_medical}, Confidence: {confidence:.2%}, Method: {method}",
            confidence_score=confidence,
            status="success" if is_medical else "non_medical",
            document_type=DocumentClassEnum(document_type) if document_type else None,
            input_metadata={"method": method},
            output_metadata={"is_medical": is_medical, "confidence": confidence}
        )

    def log_classification(
        self,
        processing_id: str,
        input_text: str,
        document_type: str,
        confidence: float,
        method: str
    ):
        """Log document classification step"""
        self.db_service.log_ai_interaction(
            processing_id=processing_id,
            step_name=ProcessingStepEnum.CLASSIFICATION,
            input_text=input_text,
            output_text=f"Classified as: {document_type}",
            confidence_score=confidence,
            status="success",
            document_type=DocumentClassEnum(document_type),
            input_metadata={"method": method},
            output_metadata={"document_type": document_type, "confidence": confidence}
        )

    def log_translation(
        self,
        processing_id: str,
        input_text: str,
        output_text: str,
        confidence: float,
        model_used: str,
        document_type: Optional[str] = None
    ):
        """Log translation step"""
        self.db_service.log_ai_interaction(
            processing_id=processing_id,
            step_name=ProcessingStepEnum.TRANSLATION,
            input_text=input_text,
            output_text=output_text,
            confidence_score=confidence,
            model_used=model_used,
            status="success",
            document_type=DocumentClassEnum(document_type) if document_type else None,
            output_metadata={"confidence": confidence, "model": model_used}
        )

    def log_quality_check(
        self,
        processing_id: str,
        step_name: str,
        input_text: str,
        output_text: str,
        changes_made: int,
        document_type: Optional[str] = None
    ):
        """Log quality check step (fact check, grammar check, etc.)"""
        self.db_service.log_ai_interaction(
            processing_id=processing_id,
            step_name=ProcessingStepEnum(step_name),
            input_text=input_text,
            output_text=output_text,
            status="success",
            document_type=DocumentClassEnum(document_type) if document_type else None,
            output_metadata={"changes_made": changes_made}
        )

    def get_processing_logs(self, processing_id: str) -> list:
        """Get all logs for a processing ID"""
        return self.db_service.get_ai_interaction_logs(processing_id=processing_id)

    def get_analytics(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        document_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get processing analytics"""
        from datetime import datetime
        
        start_dt = datetime.fromisoformat(start_date) if start_date else None
        end_dt = datetime.fromisoformat(end_date) if end_date else None
        doc_type = DocumentClassEnum(document_type) if document_type else None
        
        return self.db_service.get_processing_analytics(
            start_date=start_dt,
            end_date=end_dt,
            document_type=doc_type
        )
