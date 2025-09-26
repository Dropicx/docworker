"""
AI logging service for comprehensive interaction tracking
"""

import logging
import time
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from contextlib import contextmanager
from datetime import datetime

from app.database.unified_models import AILogInteractionDB

logger = logging.getLogger(__name__)

class AILoggingService:
    """Service for logging AI interactions"""
    
    def __init__(self, session: Session):
        self.session = session

    def _log_ai_interaction(
        self,
        processing_id: str,
        step_name: str,
        input_text: Optional[str] = None,
        output_text: Optional[str] = None,
        processing_time_ms: Optional[int] = None,
        status: str = "success",
        error_message: Optional[str] = None,
        document_type: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        request_id: Optional[str] = None,
        confidence_score: Optional[float] = None,
        model_used: Optional[str] = None,
        input_metadata: Optional[Dict[str, Any]] = None,
        output_metadata: Optional[Dict[str, Any]] = None
    ):
        """Log AI interaction to database"""
        try:
            log_entry = AILogInteractionDB(
                processing_id=processing_id,
                step_name=step_name,
                input_text=input_text,
                output_text=output_text,
                processing_time_ms=processing_time_ms or 0,
                status=status,
                error_message=error_message,
                document_type=document_type,
                user_id=user_id,
                session_id=session_id,
                request_id=request_id,
                confidence_score=confidence_score,
                model_used=model_used,
                input_metadata=input_metadata,
                output_metadata=output_metadata,
                created_at=datetime.now()
            )
            
            self.session.add(log_entry)
            self.session.commit()
            
        except Exception as e:
            logger.error(f"Failed to log AI interaction: {e}")
            self.session.rollback()

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
            self._log_ai_interaction(
                processing_id=processing_id,
                step_name=step_name,
                input_text=input_text,
                output_text=output_text,
                processing_time_ms=processing_time_ms,
                status=status,
                error_message=error_message,
                document_type=document_type,
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
        self._log_ai_interaction(
            processing_id=processing_id,
            step_name="MEDICAL_VALIDATION",
            input_text=input_text,
            output_text=f"Medical: {is_medical}, Confidence: {confidence:.2%}, Method: {method}",
            confidence_score=confidence,
            status="success" if is_medical else "non_medical",
            document_type=document_type,
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
        self._log_ai_interaction(
            processing_id=processing_id,
            step_name="CLASSIFICATION",
            input_text=input_text,
            output_text=f"Classified as: {document_type}",
            confidence_score=confidence,
            status="success",
            document_type=document_type,
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
        self._log_ai_interaction(
            processing_id=processing_id,
            step_name="TRANSLATION",
            input_text=input_text,
            output_text=output_text,
            confidence_score=confidence,
            model_used=model_used,
            status="success",
            document_type=document_type,
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
        self._log_ai_interaction(
            processing_id=processing_id,
            step_name=step_name,
            input_text=input_text,
            output_text=output_text,
            status="success",
            document_type=document_type,
            output_metadata={"changes_made": changes_made}
        )

    def log_fact_check(
        self,
        processing_id: str,
        input_text: str,
        output_text: str,
        document_type: str,
        status: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """Log fact check step"""
        self._log_ai_interaction(
            processing_id=processing_id,
            step_name="FACT_CHECK",
            input_text=input_text,
            output_text=output_text,
            status=status,
            document_type=document_type,
            output_metadata={"details": details}
        )

    def log_grammar_check(
        self,
        processing_id: str,
        input_text: str,
        output_text: str,
        document_type: str,
        status: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """Log grammar check step"""
        self._log_ai_interaction(
            processing_id=processing_id,
            step_name="GRAMMAR_CHECK",
            input_text=input_text,
            output_text=output_text,
            status=status,
            document_type=document_type,
            output_metadata={"details": details}
        )

    def log_language_translation(
        self,
        processing_id: str,
        input_text: str,
        output_text: str,
        target_language: str,
        confidence: float
    ):
        """Log language translation step"""
        self._log_ai_interaction(
            processing_id=processing_id,
            step_name="LANGUAGE_TRANSLATION",
            input_text=input_text,
            output_text=output_text,
            confidence_score=confidence,
            status="success",
            output_metadata={"target_language": target_language, "confidence": confidence}
        )

    def get_processing_logs(self, processing_id: str) -> list:
        """Get all logs for a processing ID"""
        try:
            logs = self.session.query(AILogInteractionDB).filter(
                AILogInteractionDB.processing_id == processing_id
            ).order_by(AILogInteractionDB.created_at).all()
            return [log.__dict__ for log in logs]
        except Exception as e:
            logger.error(f"Failed to get processing logs: {e}")
            return []

    def get_analytics(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        document_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get processing analytics"""
        try:
            query = self.session.query(AILogInteractionDB)
            
            if start_date:
                start_dt = datetime.fromisoformat(start_date)
                query = query.filter(AILogInteractionDB.created_at >= start_dt)
            
            if end_date:
                end_dt = datetime.fromisoformat(end_date)
                query = query.filter(AILogInteractionDB.created_at <= end_dt)
            
            if document_type:
                query = query.filter(AILogInteractionDB.document_type == document_type)
            
            logs = query.all()
            
            # Basic analytics
            total_interactions = len(logs)
            success_count = len([log for log in logs if log.status == "success"])
            error_count = len([log for log in logs if log.status == "error"])
            
            # Group by step
            step_counts = {}
            for log in logs:
                step = log.step_name
                step_counts[step] = step_counts.get(step, 0) + 1
            
            return {
                "total_interactions": total_interactions,
                "success_count": success_count,
                "error_count": error_count,
                "success_rate": success_count / total_interactions if total_interactions > 0 else 0,
                "step_counts": step_counts,
                "date_range": {
                    "start": start_date,
                    "end": end_date
                }
            }
        except Exception as e:
            logger.error(f"Failed to get analytics: {e}")
            return {
                "total_interactions": 0,
                "success_count": 0,
                "error_count": 0,
                "success_rate": 0,
                "step_counts": {},
                "error": str(e)
            }
