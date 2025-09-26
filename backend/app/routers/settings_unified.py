"""
Unified Settings Router

This module contains the new, unified settings API that uses only
the universal prompt system and database storage.
"""

import os
import logging
import time
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import secrets

from fastapi import APIRouter, HTTPException, Depends, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field, ValidationError

from app.models.document_types import DocumentClass, PromptTestRequest, PromptTestResponse
from app.services.unified_prompt_manager import UnifiedPromptManager
from app.services.ovh_client import OVHClient
from app.database.connection import get_session
from app.database.unified_models import SystemSettingsDB, UniversalPipelineStepConfigDB
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/settings", tags=["settings"])
security = HTTPBearer()

# Session management
active_sessions: Dict[str, datetime] = {}

# ==================== AUTHENTICATION ====================

class AuthRequest(BaseModel):
    password: str = Field(..., description="Access password")

class AuthResponse(BaseModel):
    success: bool
    message: str
    session_token: Optional[str] = None

@router.post("/auth", response_model=AuthResponse)
async def authenticate(auth_request: AuthRequest):
    """
    Authenticate with access password.
    Returns a session token for accessing protected endpoints.
    """
    try:
        # Get correct password from database
        db = next(get_session())
        try:
            password_setting = db.query(SystemSettingsDB).filter_by(key="settings_access_code").first()
            correct_password = password_setting.value if password_setting else "milan"
        finally:
            db.close()
        
        if auth_request.password == correct_password:
            # Generate session token
            session_token = secrets.token_urlsafe(32)
            expires_at = datetime.now() + timedelta(hours=24)
            
            # Store session
            active_sessions[session_token] = expires_at
            
            logger.info("Settings authentication successful")
            return AuthResponse(
                success=True,
                message="Authentication successful",
                session_token=session_token
            )
        else:
            logger.warning("Settings authentication failed - incorrect password")
            return AuthResponse(
                success=False,
                message="Invalid password"
            )
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        return AuthResponse(
            success=False,
            message="Authentication failed"
        )

def verify_session_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> bool:
    """Verify session token."""
    token = credentials.credentials
    if token in active_sessions:
        if active_sessions[token] > datetime.now():
            return True
        else:
            # Token expired
            del active_sessions[token]
    return False

@router.get("/check-auth")
async def check_authentication(authenticated: bool = Depends(verify_session_token)):
    """Check if current session is authenticated."""
    return {"authenticated": authenticated}

# ==================== UNIVERSAL PROMPTS ====================

@router.get("/universal-prompts")
async def get_universal_prompts(
    authenticated: bool = Depends(verify_session_token),
    db: Session = Depends(get_session)
):
    """Get universal prompts."""
    if not authenticated:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    try:
        unified_manager = UnifiedPromptManager(db)
        universal_prompts = unified_manager.get_universal_prompts()
        
        if not universal_prompts:
            # Create default universal prompts
            universal_prompts = unified_manager.create_default_universal_prompts()
            unified_manager.save_universal_prompts(universal_prompts)
        
        return {
            "success": True,
            "global_prompts": {
                "medical_validation_prompt": universal_prompts.medical_validation_prompt,
                "classification_prompt": universal_prompts.classification_prompt,
                "preprocessing_prompt": universal_prompts.preprocessing_prompt,
                "grammar_check_prompt": universal_prompts.grammar_check_prompt,
                "language_translation_prompt": universal_prompts.language_translation_prompt
            },
            "version": universal_prompts.version,
            "last_modified": universal_prompts.last_modified.isoformat(),
            "modified_by": universal_prompts.modified_by
        }
    except Exception as e:
        logger.error(f"Failed to get universal prompts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get universal prompts: {str(e)}"
        )

class UniversalPromptUpdateRequest(BaseModel):
    prompts: Dict[str, str] = Field(..., description="Universal prompts to update")
    user: Optional[str] = Field(None, description="Username making the change")

@router.put("/universal-prompts")
async def update_universal_prompts(
    update_request: UniversalPromptUpdateRequest,
    authenticated: bool = Depends(verify_session_token),
    db: Session = Depends(get_session)
):
    """Update universal prompts."""
    if not authenticated:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    try:
        unified_manager = UnifiedPromptManager(db)
        universal_prompts = unified_manager.get_universal_prompts()
        
        if not universal_prompts:
            universal_prompts = unified_manager.create_default_universal_prompts()
        
        # Update prompts
        for key, value in update_request.prompts.items():
            if hasattr(universal_prompts, key):
                setattr(universal_prompts, key, value)
        
        universal_prompts.last_modified = datetime.now()
        universal_prompts.modified_by = update_request.user or "settings_ui"
        
        success = unified_manager.save_universal_prompts(universal_prompts)
        
        if success:
            logger.info(f"Updated universal prompts by {update_request.user or 'unknown'}")
            return {
                "success": True,
                "message": "Universal prompts updated successfully",
                "version": universal_prompts.version
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save universal prompts"
            )
    except Exception as e:
        logger.error(f"Failed to update universal prompts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update universal prompts: {str(e)}"
        )

# ==================== DOCUMENT-SPECIFIC PROMPTS ====================

@router.get("/document-prompts/{document_type}")
async def get_document_prompts(
    document_type: str,
    authenticated: bool = Depends(verify_session_token),
    db: Session = Depends(get_session)
):
    """Get document-specific prompts for a document type."""
    if not authenticated:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    try:
        # Convert document type
        doc_class = DocumentClass(document_type.upper())
        
        unified_manager = UnifiedPromptManager(db)
        specific_prompts = unified_manager.get_document_specific_prompts(doc_class)
        
        if not specific_prompts:
            # Create default document-specific prompts
            specific_prompts = unified_manager.create_default_document_specific_prompts(doc_class)
            unified_manager.save_document_specific_prompts(doc_class, specific_prompts)
        
        return {
            "success": True,
            "document_type": document_type,
            "prompts": {
                "translation_prompt": specific_prompts.translation_prompt,
                "fact_check_prompt": specific_prompts.fact_check_prompt,
                "final_check_prompt": specific_prompts.final_check_prompt,
                "formatting_prompt": specific_prompts.formatting_prompt
            },
            "version": specific_prompts.version,
            "last_modified": specific_prompts.last_modified.isoformat(),
            "modified_by": specific_prompts.modified_by
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid document type: {document_type}"
        )
    except Exception as e:
        logger.error(f"Failed to get document prompts for {document_type}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get document prompts: {str(e)}"
        )

class DocumentPromptUpdateRequest(BaseModel):
    prompts: Dict[str, str] = Field(..., description="Document-specific prompts to update")
    user: Optional[str] = Field(None, description="Username making the change")

@router.put("/document-prompts/{document_type}")
async def update_document_prompts(
    document_type: str,
    update_request: DocumentPromptUpdateRequest,
    authenticated: bool = Depends(verify_session_token),
    db: Session = Depends(get_session)
):
    """Update document-specific prompts."""
    if not authenticated:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    try:
        # Convert document type
        doc_class = DocumentClass(document_type.upper())
        
        unified_manager = UnifiedPromptManager(db)
        specific_prompts = unified_manager.get_document_specific_prompts(doc_class)
        
        if not specific_prompts:
            specific_prompts = unified_manager.create_default_document_specific_prompts(doc_class)
        
        # Update prompts
        for key, value in update_request.prompts.items():
            if hasattr(specific_prompts, key):
                setattr(specific_prompts, key, value)
        
        specific_prompts.last_modified = datetime.now()
        specific_prompts.modified_by = update_request.user or "settings_ui"
        
        success = unified_manager.save_document_specific_prompts(doc_class, specific_prompts)
        
        if success:
            logger.info(f"Updated document prompts for {document_type} by {update_request.user or 'unknown'}")
            return {
                "success": True,
                "message": f"Document prompts updated successfully for {document_type}",
                "version": specific_prompts.version
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save document prompts"
            )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid document type: {document_type}"
        )
    except Exception as e:
        logger.error(f"Failed to update document prompts for {document_type}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update document prompts: {str(e)}"
        )

# ==================== PIPELINE STEPS ====================

@router.get("/pipeline-steps")
async def get_pipeline_steps(
    authenticated: bool = Depends(verify_session_token),
    db: Session = Depends(get_session)
):
    """Get all pipeline step configurations."""
    if not authenticated:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    try:
        unified_manager = UnifiedPromptManager(db)
        steps = unified_manager.get_pipeline_steps()
        
        # Create default steps if none exist
        if not steps:
            unified_manager.create_default_pipeline_steps()
            steps = unified_manager.get_pipeline_steps()
        
        pipeline_steps = {}
        for step in steps:
            pipeline_steps[step.step_name.lower()] = {
                "enabled": step.enabled,
                "order": step.order,
                "name": step.name,
                "description": step.description
            }
        
        return {
            "success": True,
            "pipeline_steps": pipeline_steps
        }
    except Exception as e:
        logger.error(f"Failed to get pipeline steps: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get pipeline steps: {str(e)}"
        )

class PipelineStepUpdateRequest(BaseModel):
    step_name: str = Field(..., description="Name of the pipeline step")
    enabled: bool = Field(..., description="Whether the step is enabled")

@router.put("/pipeline-steps")
async def update_pipeline_step(
    update_request: PipelineStepUpdateRequest,
    authenticated: bool = Depends(verify_session_token),
    db: Session = Depends(get_session)
):
    """Update a pipeline step configuration."""
    if not authenticated:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    try:
        unified_manager = UnifiedPromptManager(db)
        success = unified_manager.update_pipeline_step(
            update_request.step_name, 
            update_request.enabled
        )
        
        if success:
            logger.info(f"Updated pipeline step {update_request.step_name}: enabled={update_request.enabled}")
            return {
                "success": True,
                "message": f"Pipeline step '{update_request.step_name}' {'enabled' if update_request.enabled else 'disabled'}"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update pipeline step"
            )
    except Exception as e:
        logger.error(f"Failed to update pipeline step {update_request.step_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update pipeline step: {str(e)}"
        )

# ==================== PROMPT TESTING ====================

@router.post("/test-prompt", response_model=PromptTestResponse)
async def test_prompt(
    test_request: PromptTestRequest,
    authenticated: bool = Depends(verify_session_token)
):
    """Test a prompt with sample text."""
    if not authenticated:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    try:
        ovh_client = OVHClient()
        
        # Test the prompt
        result = await ovh_client.test_prompt(
            prompt=test_request.prompt,
            sample_text=test_request.sample_text,
            temperature=test_request.temperature,
            max_tokens=test_request.max_tokens
        )
        
        return PromptTestResponse(
            success=True,
            result=result,
            processing_time=0.0  # Could be calculated if needed
        )
    except Exception as e:
        logger.error(f"Prompt test failed: {e}")
        return PromptTestResponse(
            success=False,
            error=str(e),
            processing_time=0.0
        )

# ==================== SYSTEM SETTINGS ====================

@router.get("/system-settings")
async def get_system_settings(
    authenticated: bool = Depends(verify_session_token),
    db: Session = Depends(get_session)
):
    """Get system settings."""
    if not authenticated:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    try:
        settings = db.query(SystemSettingsDB).all()
        
        settings_dict = {}
        for setting in settings:
            if setting.value_type == 'bool':
                settings_dict[setting.key] = setting.value.lower() == 'true'
            elif setting.value_type == 'int':
                settings_dict[setting.key] = int(setting.value)
            elif setting.value_type == 'float':
                settings_dict[setting.key] = float(setting.value)
            else:
                settings_dict[setting.key] = setting.value
        
        return {
            "success": True,
            "settings": settings_dict
        }
    except Exception as e:
        logger.error(f"Failed to get system settings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get system settings: {str(e)}"
        )

class SystemSettingsUpdateRequest(BaseModel):
    settings: Dict[str, Any] = Field(..., description="Settings to update")

@router.put("/system-settings")
async def update_system_settings(
    update_request: SystemSettingsUpdateRequest,
    authenticated: bool = Depends(verify_session_token),
    db: Session = Depends(get_session)
):
    """Update system settings."""
    if not authenticated:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    try:
        for key, value in update_request.settings.items():
            setting = db.query(SystemSettingsDB).filter_by(key=key).first()
            
            if setting:
                setting.value = str(value)
                setting.updated_at = datetime.now()
                setting.updated_by = "settings_ui"
            else:
                # Create new setting
                value_type = "bool" if isinstance(value, bool) else "int" if isinstance(value, int) else "float" if isinstance(value, float) else "string"
                new_setting = SystemSettingsDB(
                    key=key,
                    value=str(value),
                    value_type=value_type,
                    description=f"System setting: {key}",
                    is_encrypted=False,
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                    updated_by="settings_ui"
                )
                db.add(new_setting)
        
        db.commit()
        logger.info(f"Updated system settings: {list(update_request.settings.keys())}")
        
        return {
            "success": True,
            "message": "System settings updated successfully"
        }
    except Exception as e:
        logger.error(f"Failed to update system settings: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update system settings: {str(e)}"
        )

# ==================== DOCUMENT TYPES ====================

@router.get("/document-types")
async def get_document_types(
    authenticated: bool = Depends(verify_session_token)
):
    """Get list of supported document types."""
    if not authenticated:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    try:
        document_types = [
            {
                "type": "arztbrief",
                "name": "Arztbrief",
                "description": "Medical letter from doctor to patient or other healthcare providers"
            },
            {
                "type": "befundbericht", 
                "name": "Befundbericht",
                "description": "Medical findings report with test results and diagnoses"
            },
            {
                "type": "laborwerte",
                "name": "Laborwerte", 
                "description": "Laboratory values and test results"
            }
        ]
        
        return {"document_types": document_types}
        
    except Exception as e:
        logger.error(f"Failed to get document types: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get document types: {str(e)}"
        )

# ==================== PIPELINE SETTINGS ====================

@router.get("/pipeline-settings")
async def get_pipeline_settings(
    authenticated: bool = Depends(verify_session_token),
    db: Session = Depends(get_session)
):
    """Get pipeline settings."""
    if not authenticated:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    try:
        # Get pipeline step configurations
        pipeline_steps = db.query(UniversalPipelineStepConfigDB).all()
        
        # Convert to frontend format - map to individual boolean flags
        settings = {
            "use_optimized_pipeline": True,  # Always true for unified system
            "pipeline_cache_timeout": 1800,  # 30 minutes default
            "enable_medical_validation": False,
            "enable_classification": False,
            "enable_preprocessing": False,
            "enable_translation": False,
            "enable_fact_check": False,
            "enable_grammar_check": False,
            "enable_language_translation": False,
            "enable_final_check": False
        }
        
        # Map step names to frontend flags
        step_mapping = {
            "MEDICAL_VALIDATION": "enable_medical_validation",
            "CLASSIFICATION": "enable_classification", 
            "PREPROCESSING": "enable_preprocessing",
            "TRANSLATION": "enable_translation",
            "FACT_CHECK": "enable_fact_check",
            "GRAMMAR_CHECK": "enable_grammar_check",
            "LANGUAGE_TRANSLATION": "enable_language_translation",
            "FINAL_CHECK": "enable_final_check"
        }
        
        for step in pipeline_steps:
            if step.step_name in step_mapping:
                settings[step_mapping[step.step_name]] = step.enabled
        
        return {"settings": settings}
        
    except Exception as e:
        logger.error(f"Failed to get pipeline settings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get pipeline settings: {str(e)}"
        )

@router.put("/pipeline-settings")
async def update_pipeline_settings(
    request: dict,
    authenticated: bool = Depends(verify_session_token),
    db: Session = Depends(get_session)
):
    """Update pipeline settings."""
    if not authenticated:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    try:
        settings = request.get("settings", {})
        
        # Map frontend flags back to step names
        step_mapping = {
            "enable_medical_validation": "MEDICAL_VALIDATION",
            "enable_classification": "CLASSIFICATION", 
            "enable_preprocessing": "PREPROCESSING",
            "enable_translation": "TRANSLATION",
            "enable_fact_check": "FACT_CHECK",
            "enable_grammar_check": "GRAMMAR_CHECK",
            "enable_language_translation": "LANGUAGE_TRANSLATION",
            "enable_final_check": "FINAL_CHECK"
        }
        
        # Update each step configuration based on frontend flags
        for frontend_key, step_name in step_mapping.items():
            if frontend_key in settings:
                step_db = db.query(UniversalPipelineStepConfigDB).filter_by(step_name=step_name).first()
                if step_db:
                    step_db.enabled = settings[frontend_key]
                    step_db.last_modified = datetime.now()
                    step_db.modified_by = "frontend_update"
                else:
                    # Create new step configuration if it doesn't exist
                    new_step = UniversalPipelineStepConfigDB(
                        step_name=step_name,
                        enabled=settings[frontend_key],
                        description=f"Step {step_name}",
                        order=0
                    )
                    db.add(new_step)
        
        db.commit()
        
        return {
            "success": True,
            "message": "Pipeline settings updated successfully"
        }
        
    except Exception as e:
        logger.error(f"Failed to update pipeline settings: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update pipeline settings: {str(e)}"
        )

# ==================== DATABASE MANAGEMENT ====================

@router.post("/seed-database")
async def seed_database(
    authenticated: bool = Depends(verify_session_token)
):
    """Trigger database seeding (for development/production setup)."""
    if not authenticated:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    try:
        from app.database.unified_seed import unified_seed_database
        
        result = unified_seed_database()
        
        if result:
            return {
                "success": True,
                "message": "Database seeded successfully"
            }
        else:
            return {
                "success": False,
                "message": "Database seeding failed"
            }
            
    except Exception as e:
        logger.error(f"Failed to seed database: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to seed database: {str(e)}"
        )
