"""
Database service layer for managing prompts and settings
"""

import logging
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from datetime import datetime, timedelta

from app.database.models import (
    DocumentPromptsDB, 
    PipelineStepConfigDB, 
    AIInteractionLog,
    SystemSettingsDB,
    UserSessionsDB,
    DocumentClassEnum,
    ProcessingStepEnum
)
from app.models.document_types import DocumentClass, DocumentPrompts, PipelineStepConfig

logger = logging.getLogger(__name__)

class DatabaseService:
    """Service for database operations"""
    
    def __init__(self, session: Session):
        self.session = session

    # Document Prompts Management
    
    def get_document_prompts(self, document_type: DocumentClass) -> Optional[DocumentPrompts]:
        """Get document prompts from database"""
        try:
            db_prompts = self.session.query(DocumentPromptsDB).filter(
                DocumentPromptsDB.document_type == DocumentClassEnum(document_type.value)
            ).first()
            
            if not db_prompts:
                return None
            
            # Convert pipeline steps
            pipeline_steps = {}
            for step in db_prompts.pipeline_steps:
                pipeline_steps[step.step_name.value] = PipelineStepConfig(
                    enabled=step.enabled,
                    order=step.order,
                    name=step.name,
                    description=step.description or ""
                )
            
            return DocumentPrompts(
                document_type=document_type,
                medical_validation_prompt=getattr(db_prompts, 'medical_validation_prompt', 'Default medical validation prompt'),
                classification_prompt=db_prompts.classification_prompt,
                preprocessing_prompt=db_prompts.preprocessing_prompt,
                translation_prompt=db_prompts.translation_prompt,
                fact_check_prompt=db_prompts.fact_check_prompt,
                grammar_check_prompt=db_prompts.grammar_check_prompt,
                language_translation_prompt=db_prompts.language_translation_prompt,
                final_check_prompt=db_prompts.final_check_prompt,
                formatting_prompt=getattr(db_prompts, 'formatting_prompt', 'Default formatting prompt'),
                pipeline_steps=pipeline_steps,
                version=db_prompts.version,
                last_modified=db_prompts.last_modified,
                modified_by=db_prompts.modified_by
            )
        except Exception as e:
            logger.error(f"Failed to get document prompts: {e}")
            return None

    def save_document_prompts(self, prompts: DocumentPrompts) -> bool:
        """Save document prompts to database"""
        try:
            # Get or create document prompts record
            db_prompts = self.session.query(DocumentPromptsDB).filter(
                DocumentPromptsDB.document_type == DocumentClassEnum(prompts.document_type.value)
            ).first()
            
            if not db_prompts:
                db_prompts = DocumentPromptsDB(
                    document_type=DocumentClassEnum(prompts.document_type.value)
                )
                self.session.add(db_prompts)
            
            # Update prompt fields
            db_prompts.medical_validation_prompt = prompts.medical_validation_prompt
            db_prompts.classification_prompt = prompts.classification_prompt
            db_prompts.preprocessing_prompt = prompts.preprocessing_prompt
            db_prompts.translation_prompt = prompts.translation_prompt
            db_prompts.fact_check_prompt = prompts.fact_check_prompt
            db_prompts.grammar_check_prompt = prompts.grammar_check_prompt
            db_prompts.language_translation_prompt = prompts.language_translation_prompt
            db_prompts.final_check_prompt = prompts.final_check_prompt
            db_prompts.formatting_prompt = prompts.formatting_prompt
            db_prompts.version = prompts.version or 1
            db_prompts.last_modified = datetime.now()
            db_prompts.modified_by = prompts.modified_by or "admin"
            
            # Update pipeline steps
            self.session.query(PipelineStepConfigDB).filter(
                PipelineStepConfigDB.document_prompts_id == db_prompts.id
            ).delete()
            
            for step_name, step_config in prompts.pipeline_steps.items():
                db_step = PipelineStepConfigDB(
                    document_prompts_id=db_prompts.id,
                    step_name=ProcessingStepEnum(step_name),
                    enabled=step_config.enabled,
                    order=step_config.order,
                    name=step_config.name,
                    description=step_config.description
                )
                self.session.add(db_step)
            
            self.session.commit()
            return True
            
        except Exception as e:
            logger.error(f"Failed to save document prompts: {e}")
            self.session.rollback()
            return False

    def get_all_document_prompts(self) -> Dict[DocumentClass, DocumentPrompts]:
        """Get all document prompts"""
        result = {}
        for doc_class in DocumentClass:
            prompts = self.get_document_prompts(doc_class)
            if prompts:
                result[doc_class] = prompts
        return result

    def reset_document_prompts(self, document_type: DocumentClass) -> bool:
        """Reset document prompts to default values"""
        try:
            # Delete existing prompts
            self.session.query(DocumentPromptsDB).filter(
                DocumentPromptsDB.document_type == DocumentClassEnum(document_type.value)
            ).delete()
            
            # Create default prompts (this would need to be implemented)
            # For now, just return True
            self.session.commit()
            return True
            
        except Exception as e:
            logger.error(f"Failed to reset document prompts: {e}")
            self.session.rollback()
            return False

    # AI Interaction Logging
    
    def log_ai_interaction(
        self,
        processing_id: str,
        step_name: ProcessingStepEnum,
        input_text: Optional[str] = None,
        output_text: Optional[str] = None,
        model_used: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        prompt_used: Optional[str] = None,
        processing_time_ms: Optional[int] = None,
        confidence_score: Optional[float] = None,
        token_count: Optional[int] = None,
        status: str = "success",
        error_message: Optional[str] = None,
        document_type: Optional[DocumentClassEnum] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        request_id: Optional[str] = None,
        input_metadata: Optional[Dict[str, Any]] = None,
        output_metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Log AI interaction to database"""
        try:
            log_entry = AIInteractionLog(
                processing_id=processing_id,
                step_name=step_name,
                document_type=document_type,
                input_text=input_text,
                input_length=len(input_text) if input_text else None,
                input_metadata=input_metadata,
                model_used=model_used,
                temperature=temperature,
                max_tokens=max_tokens,
                prompt_used=prompt_used,
                output_text=output_text,
                output_length=len(output_text) if output_text else None,
                output_metadata=output_metadata,
                processing_time_ms=processing_time_ms,
                confidence_score=confidence_score,
                token_count=token_count,
                status=status,
                error_message=error_message,
                user_id=user_id,
                session_id=session_id,
                request_id=request_id,
                completed_at=datetime.now()
            )
            
            self.session.add(log_entry)
            self.session.commit()
            return True
            
        except Exception as e:
            logger.error(f"Failed to log AI interaction: {e}")
            self.session.rollback()
            return False

    def get_ai_interaction_logs(
        self,
        processing_id: Optional[str] = None,
        step_name: Optional[ProcessingStepEnum] = None,
        document_type: Optional[DocumentClassEnum] = None,
        user_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[AIInteractionLog]:
        """Get AI interaction logs with filters"""
        try:
            query = self.session.query(AIInteractionLog)
            
            if processing_id:
                query = query.filter(AIInteractionLog.processing_id == processing_id)
            if step_name:
                query = query.filter(AIInteractionLog.step_name == step_name)
            if document_type:
                query = query.filter(AIInteractionLog.document_type == document_type)
            if user_id:
                query = query.filter(AIInteractionLog.user_id == user_id)
            
            return query.order_by(desc(AIInteractionLog.created_at)).offset(offset).limit(limit).all()
            
        except Exception as e:
            logger.error(f"Failed to get AI interaction logs: {e}")
            return []

    def get_processing_analytics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        document_type: Optional[DocumentClassEnum] = None
    ) -> Dict[str, Any]:
        """Get processing analytics"""
        try:
            query = self.session.query(AIInteractionLog)
            
            if start_date:
                query = query.filter(AIInteractionLog.created_at >= start_date)
            if end_date:
                query = query.filter(AIInteractionLog.created_at <= end_date)
            if document_type:
                query = query.filter(AIInteractionLog.document_type == document_type)
            
            logs = query.all()
            
            # Calculate analytics
            total_interactions = len(logs)
            successful_interactions = len([log for log in logs if log.status == "success"])
            error_interactions = len([log for log in logs if log.status == "error"])
            
            avg_processing_time = sum(log.processing_time_ms or 0 for log in logs) / total_interactions if total_interactions > 0 else 0
            avg_confidence = sum(log.confidence_score or 0 for log in logs) / total_interactions if total_interactions > 0 else 0
            
            # Step-wise breakdown
            step_stats = {}
            for log in logs:
                step = log.step_name.value
                if step not in step_stats:
                    step_stats[step] = {"count": 0, "success": 0, "errors": 0, "avg_time": 0}
                step_stats[step]["count"] += 1
                if log.status == "success":
                    step_stats[step]["success"] += 1
                else:
                    step_stats[step]["errors"] += 1
                if log.processing_time_ms:
                    step_stats[step]["avg_time"] += log.processing_time_ms
            
            # Calculate averages
            for step in step_stats:
                if step_stats[step]["count"] > 0:
                    step_stats[step]["avg_time"] = step_stats[step]["avg_time"] / step_stats[step]["count"]
            
            return {
                "total_interactions": total_interactions,
                "successful_interactions": successful_interactions,
                "error_interactions": error_interactions,
                "success_rate": successful_interactions / total_interactions if total_interactions > 0 else 0,
                "avg_processing_time_ms": avg_processing_time,
                "avg_confidence_score": avg_confidence,
                "step_statistics": step_stats
            }
            
        except Exception as e:
            logger.error(f"Failed to get processing analytics: {e}")
            return {}

    # System Settings Management
    
    def get_system_setting(self, key: str) -> Optional[Any]:
        """Get system setting value"""
        try:
            setting = self.session.query(SystemSettingsDB).filter(
                SystemSettingsDB.key == key
            ).first()
            
            if not setting:
                return None
            
            # Parse value based on type
            if setting.value_type == "int":
                return int(setting.value) if setting.value else None
            elif setting.value_type == "float":
                return float(setting.value) if setting.value else None
            elif setting.value_type == "bool":
                return setting.value.lower() == "true" if setting.value else False
            elif setting.value_type == "json":
                import json
                return json.loads(setting.value) if setting.value else None
            else:
                return setting.value
                
        except Exception as e:
            logger.error(f"Failed to get system setting {key}: {e}")
            return None

    def set_system_setting(
        self, 
        key: str, 
        value: Any, 
        value_type: str = "string",
        description: Optional[str] = None,
        updated_by: Optional[str] = None
    ) -> bool:
        """Set system setting value"""
        try:
            setting = self.session.query(SystemSettingsDB).filter(
                SystemSettingsDB.key == key
            ).first()
            
            if not setting:
                setting = SystemSettingsDB(key=key)
                self.session.add(setting)
            
            # Convert value to string for storage
            if value_type == "json":
                import json
                setting.value = json.dumps(value)
            else:
                setting.value = str(value)
            
            setting.value_type = value_type
            setting.description = description
            setting.updated_at = datetime.now()
            setting.updated_by = updated_by
            
            self.session.commit()
            return True
            
        except Exception as e:
            logger.error(f"Failed to set system setting {key}: {e}")
            self.session.rollback()
            return False

    # User Session Management
    
    def create_user_session(
        self,
        session_token: str,
        user_id: Optional[str] = None,
        expires_at: Optional[datetime] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> bool:
        """Create user session"""
        try:
            session = UserSessionsDB(
                session_token=session_token,
                user_id=user_id,
                expires_at=expires_at,
                ip_address=ip_address,
                user_agent=user_agent
            )
            self.session.add(session)
            self.session.commit()
            return True
            
        except Exception as e:
            logger.error(f"Failed to create user session: {e}")
            self.session.rollback()
            return False

    def validate_user_session(self, session_token: str) -> bool:
        """Validate user session"""
        try:
            session = self.session.query(UserSessionsDB).filter(
                and_(
                    UserSessionsDB.session_token == session_token,
                    UserSessionsDB.is_active == True,
                    UserSessionsDB.expires_at > datetime.now()
                )
            ).first()
            
            if session:
                # Update last accessed
                session.last_accessed = datetime.now()
                self.session.commit()
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to validate user session: {e}")
            return False

    def invalidate_user_session(self, session_token: str) -> bool:
        """Invalidate user session"""
        try:
            session = self.session.query(UserSessionsDB).filter(
                UserSessionsDB.session_token == session_token
            ).first()
            
            if session:
                session.is_active = False
                self.session.commit()
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to invalidate user session: {e}")
            self.session.rollback()
            return False
