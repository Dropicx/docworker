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
from typing import Union

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
async def authenticate(
    auth_request: AuthRequest,
    db: Session = Depends(get_session)
):
    """
    Authenticate with access password.
    Returns a session token for accessing protected endpoints.
    """
    try:
        # Get correct password from database
        password_setting = db.query(SystemSettingsDB).filter_by(key="settings_access_code").first()
        correct_password = password_setting.value if password_setting else "milan"
        
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
            universal_prompts.is_active = True
            db.add(universal_prompts)
            db.commit()
        
        return {
            "success": True,
            "global_prompts": {
                "medical_validation_prompt": universal_prompts.medical_validation_prompt,
                "classification_prompt": universal_prompts.classification_prompt,
                "preprocessing_prompt": universal_prompts.preprocessing_prompt,
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
    medical_validation_prompt: Optional[str] = Field(None, description="Medical validation prompt")
    classification_prompt: Optional[str] = Field(None, description="Classification prompt")
    preprocessing_prompt: Optional[str] = Field(None, description="Preprocessing prompt")
    language_translation_prompt: Optional[str] = Field(None, description="Language translation prompt")
    user: Optional[str] = Field(None, description="Username making the change")

    class Config:
        # Allow extra fields to be ignored
        extra = "ignore"

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

    # Add validation logging
    logger.info(f"Universal prompts update request received")

    try:
        unified_manager = UnifiedPromptManager(db)
        universal_prompts = unified_manager.get_universal_prompts()

        if not universal_prompts:
            universal_prompts = unified_manager.create_default_universal_prompts()
            universal_prompts.is_active = True
            db.add(universal_prompts)
            db.flush()  # Ensure it gets an ID

        # Update prompts directly - only valid fields with actual values
        updated_fields = []

        # Check each field individually
        if update_request.medical_validation_prompt is not None:
            universal_prompts.medical_validation_prompt = update_request.medical_validation_prompt
            updated_fields.append("medical_validation_prompt")

        if update_request.classification_prompt is not None:
            universal_prompts.classification_prompt = update_request.classification_prompt
            updated_fields.append("classification_prompt")

        if update_request.preprocessing_prompt is not None:
            universal_prompts.preprocessing_prompt = update_request.preprocessing_prompt
            updated_fields.append("preprocessing_prompt")

        if update_request.language_translation_prompt is not None:
            universal_prompts.language_translation_prompt = update_request.language_translation_prompt
            updated_fields.append("language_translation_prompt")

        if not updated_fields:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No universal prompt fields provided to update. Valid fields: medical_validation_prompt, classification_prompt, preprocessing_prompt, language_translation_prompt"
            )

        logger.info(f"Updated universal prompt fields: {updated_fields}")

        universal_prompts.last_modified = datetime.now()
        universal_prompts.modified_by = update_request.user or "settings_ui"

        # Commit - SQLAlchemy will automatically generate UPDATE
        db.commit()

        logger.info(f"Updated universal prompts by {update_request.user or 'unknown'}")
        return {
            "success": True,
            "message": "Universal prompts updated successfully",
            "version": universal_prompts.version
        }
    except Exception as e:
        logger.error(f"Failed to update universal prompts: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update universal prompts: {str(e)}"
        )

@router.put("/universal-prompts-debug")
async def update_universal_prompts_debug(
    request: Request,
    authenticated: bool = Depends(verify_session_token),
    db: Session = Depends(get_session)
):
    """Debug endpoint for universal prompts update - accepts raw JSON."""
    if not authenticated:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )

    try:
        # Get raw request body
        raw_body = await request.json()
        logger.info(f"Raw universal prompts update request: {raw_body}")

        # Extract prompts and user
        prompts = raw_body.get("prompts", {})
        user = raw_body.get("user", "debug_user")

        if not prompts or not isinstance(prompts, dict):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or missing 'prompts' field"
            )

        logger.info(f"Prompts keys received: {list(prompts.keys())}")

        unified_manager = UnifiedPromptManager(db)
        universal_prompts = unified_manager.get_universal_prompts()

        if not universal_prompts:
            universal_prompts = unified_manager.create_default_universal_prompts()
            universal_prompts.is_active = True
            db.add(universal_prompts)
            db.flush()

        # Valid universal prompt fields
        valid_universal_fields = {
            "medical_validation_prompt",
            "classification_prompt",
            "preprocessing_prompt",
            "language_translation_prompt"
        }

        # Update prompts directly - only valid fields
        updated_fields = []
        for key, value in prompts.items():
            if key in valid_universal_fields and hasattr(universal_prompts, key):
                setattr(universal_prompts, key, value)
                updated_fields.append(key)
                logger.info(f"Updated {key}")
            elif key not in valid_universal_fields:
                logger.warning(f"Skipping invalid universal prompt field: {key}")

        if not updated_fields:
            available_fields = [f for f in valid_universal_fields if hasattr(universal_prompts, f)]
            return {
                "error": "No valid universal prompt fields found",
                "received_fields": list(prompts.keys()),
                "valid_fields": list(valid_universal_fields),
                "available_fields": available_fields
            }

        universal_prompts.last_modified = datetime.now()
        universal_prompts.modified_by = user

        db.commit()

        logger.info(f"Successfully updated universal prompt fields: {updated_fields}")
        return {
            "success": True,
            "message": "Universal prompts updated successfully",
            "updated_fields": updated_fields,
            "version": universal_prompts.version
        }

    except Exception as e:
        logger.error(f"Failed to update universal prompts (debug): {e}")
        db.rollback()
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
            specific_prompts.document_type = doc_class.value.upper()
            db.add(specific_prompts)
            db.commit()
        
        # Get combined prompts (universal + document-specific)
        combined_prompts = unified_manager.get_combined_prompts(doc_class)
        
        return {
            "success": True,
            "document_type": document_type,
            "prompts": {
                # Universal prompts
                "medical_validation_prompt": combined_prompts.get("medical_validation_prompt", ""),
                "classification_prompt": combined_prompts.get("classification_prompt", ""),
                "preprocessing_prompt": combined_prompts.get("preprocessing_prompt", ""),
                "language_translation_prompt": combined_prompts.get("language_translation_prompt", ""),
                
                # Document-specific prompts
                "translation_prompt": combined_prompts.get("translation_prompt", ""),
                "fact_check_prompt": combined_prompts.get("fact_check_prompt", ""),
                "grammar_check_prompt": combined_prompts.get("grammar_check_prompt", ""),
                "final_check_prompt": combined_prompts.get("final_check_prompt", ""),
                "formatting_prompt": combined_prompts.get("formatting_prompt", "")
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

        # Get or create document-specific prompts
        specific_prompts = unified_manager.get_document_specific_prompts(doc_class)
        if not specific_prompts:
            specific_prompts = unified_manager.create_default_document_specific_prompts(doc_class)
            specific_prompts.document_type = doc_class.value.upper()
            db.add(specific_prompts)
            db.flush()  # Ensure it gets an ID

        # Separate universal and document-specific prompts
        universal_prompt_fields = [
            "medical_validation_prompt", "classification_prompt", "preprocessing_prompt",
            "language_translation_prompt"
        ]
        document_specific_prompt_fields = [
            "translation_prompt", "fact_check_prompt", "grammar_check_prompt",
            "final_check_prompt", "formatting_prompt"
        ]

        # Track if we need to update anything
        doc_updated = False
        universal_updated = False

        # Update document-specific prompts directly
        for key, value in update_request.prompts.items():
            if key in document_specific_prompt_fields and hasattr(specific_prompts, key):
                setattr(specific_prompts, key, value)
                doc_updated = True

        if doc_updated:
            specific_prompts.last_modified = datetime.now()
            specific_prompts.modified_by = update_request.user or "settings_ui"

        # Update universal prompts if any were provided
        universal_prompts = unified_manager.get_universal_prompts()
        if universal_prompts:
            for key, value in update_request.prompts.items():
                if key in universal_prompt_fields and hasattr(universal_prompts, key):
                    setattr(universal_prompts, key, value)
                    universal_updated = True

            if universal_updated:
                universal_prompts.last_modified = datetime.now()
                universal_prompts.modified_by = update_request.user or "settings_ui"

        # Commit all changes at once - SQLAlchemy will automatically generate UPDATEs
        db.commit()

        logger.info(f"Updated document prompts for {document_type} by {update_request.user or 'unknown'}")
        return {
            "success": True,
            "message": f"Document prompts updated successfully for {document_type}",
            "version": specific_prompts.version
        }

    except ValueError as e:
        logger.error(f"Invalid document type {document_type}: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid document type: {document_type}"
        )
    except Exception as e:
        logger.error(f"Failed to update document prompts for {document_type}: {e}")
        db.rollback()
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
            success = unified_manager.create_default_pipeline_steps()
            if success:
                db.commit()
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
            db.commit()
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
        db.rollback()
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

async def get_pipeline_settings_internal(db: Session) -> dict:
    """Internal function to get pipeline settings (used by both GET and PUT endpoints)."""
    try:
        # Get pipeline step configurations
        pipeline_steps = db.query(UniversalPipelineStepConfigDB).all()
        
        # Get system settings for pipeline configuration
        from app.database.models import SystemSettingsDB
        
        # Get system settings
        system_settings = db.query(SystemSettingsDB).filter(
            SystemSettingsDB.key.in_(["use_optimized_pipeline", "pipeline_cache_timeout"])
        ).all()
        
        system_config = {}
        for setting in system_settings:
            if setting.key == "pipeline_cache_timeout":
                system_config["pipeline_cache_timeout"] = int(setting.value) if setting.value.isdigit() else 1800
            elif setting.key == "use_optimized_pipeline":
                system_config["use_optimized_pipeline"] = setting.value.lower() == "true"
        
        # Convert to frontend format - organized by type and order
        settings = {
            "use_optimized_pipeline": system_config.get("use_optimized_pipeline", True),  # Default to true
            "pipeline_cache_timeout": system_config.get("pipeline_cache_timeout", 1800),  # Default to 30 minutes
            "enable_medical_validation": False,
            "enable_preprocessing": False,
            "enable_classification": False,
            "enable_translation": False,
            "enable_fact_check": False,
            "enable_grammar_check": False,
            "enable_language_translation": False,
            "enable_final_check": False,
            "enable_formatting": False
        }
        
        # Map step names to frontend flags (in processing order)
        step_mapping = {
            "MEDICAL_VALIDATION": "enable_medical_validation",
            "PREPROCESSING": "enable_preprocessing",
            "CLASSIFICATION": "enable_classification", 
            "TRANSLATION": "enable_translation",
            "FACT_CHECK": "enable_fact_check",
            "GRAMMAR_CHECK": "enable_grammar_check",
            "LANGUAGE_TRANSLATION": "enable_language_translation",
            "FINAL_CHECK": "enable_final_check",
            "FORMATTING": "enable_formatting"
        }
        
        for step in pipeline_steps:
            if step.step_name in step_mapping:
                settings[step_mapping[step.step_name]] = step.enabled
        
        # Note: Old document-specific pipeline steps removed - now using universal_pipeline_steps
        # All step configuration is now handled through the unified system
        
        return {"settings": settings}
        
    except Exception as e:
        logger.error(f"Failed to get pipeline settings: {e}")
        raise e

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
        return await get_pipeline_settings_internal(db)
    except Exception as e:
        logger.error(f"Failed to get pipeline settings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get pipeline settings: {str(e)}"
        )

class PipelineSettingsUpdateRequest(BaseModel):
    settings: Dict[str, Any] = Field(..., description="Pipeline settings to update")

@router.put("/pipeline-settings")
async def update_pipeline_settings(
    update_request: PipelineSettingsUpdateRequest,
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
        settings = update_request.settings
        
        # Map frontend flags back to step names (in processing order)
        step_mapping = {
            "enable_medical_validation": "MEDICAL_VALIDATION",
            "enable_preprocessing": "PREPROCESSING",
            "enable_classification": "CLASSIFICATION", 
            "enable_translation": "TRANSLATION",
            "enable_fact_check": "FACT_CHECK",
            "enable_grammar_check": "GRAMMAR_CHECK",
            "enable_language_translation": "LANGUAGE_TRANSLATION",
            "enable_final_check": "FINAL_CHECK",
            "enable_formatting": "FORMATTING"
        }
        
        # Handle system settings (pipeline_cache_timeout, use_optimized_pipeline)
        from app.database.models import SystemSettingsDB
        
        if "pipeline_cache_timeout" in settings:
            cache_timeout_setting = db.query(SystemSettingsDB).filter_by(key="pipeline_cache_timeout").first()
            if cache_timeout_setting:
                cache_timeout_setting.value = str(settings["pipeline_cache_timeout"])
                cache_timeout_setting.updated_at = datetime.now()
                cache_timeout_setting.updated_by = "frontend_update"
            else:
                new_setting = SystemSettingsDB(
                    key="pipeline_cache_timeout",
                    value=str(settings["pipeline_cache_timeout"]),
                    value_type="int",
                    description="Pipeline cache timeout in seconds",
                    is_encrypted=False,
                    updated_by="frontend_update"
                )
                db.add(new_setting)
        
        if "use_optimized_pipeline" in settings:
            optimized_setting = db.query(SystemSettingsDB).filter_by(key="use_optimized_pipeline").first()
            if optimized_setting:
                optimized_setting.value = str(settings["use_optimized_pipeline"]).lower()
                optimized_setting.updated_at = datetime.now()
                optimized_setting.updated_by = "frontend_update"
            else:
                new_setting = SystemSettingsDB(
                    key="use_optimized_pipeline",
                    value=str(settings["use_optimized_pipeline"]).lower(),
                    value_type="bool",
                    description="Whether to use optimized pipeline",
                    is_encrypted=False,
                    updated_by="frontend_update"
                )
                db.add(new_setting)
        
        # Update each step configuration based on frontend flags
        for frontend_key, step_name in step_mapping.items():
            if frontend_key in settings:
                # All steps are now handled as universal steps (unified system)
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
        
        # Get updated settings to return to frontend
        updated_settings = await get_pipeline_settings_internal(db)
        
        return {
            "success": True,
            "message": "Pipeline settings updated successfully",
            "settings": updated_settings["settings"]
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


@router.get("/model-configuration")
async def get_model_configuration(authenticated: bool = Depends(verify_session_token)):
    """Get current OVH model configuration for each pipeline step."""
    if not authenticated:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )

    try:
        # Get OVH client to access model configuration
        ovh_client = OVHClient()

        # Model mapping for each prompt/step type
        model_mapping = {
            # Universal/Global Prompts (preprocessing phase)
            "medical_validation_prompt": ovh_client.main_model,
            "classification_prompt": ovh_client.main_model,
            "preprocessing_prompt": ovh_client.preprocessing_model,
            "language_translation_prompt": ovh_client.translation_model,

            # Document-specific prompts (main processing phase)
            "translation_prompt": ovh_client.main_model,
            "fact_check_prompt": ovh_client.main_model,
            "grammar_check_prompt": ovh_client.main_model,
            "final_check_prompt": ovh_client.main_model,
            "formatting_prompt": ovh_client.main_model
        }

        # Environment variable info for reference
        environment_config = {
            "OVH_MAIN_MODEL": ovh_client.main_model,
            "OVH_PREPROCESSING_MODEL": ovh_client.preprocessing_model,
            "OVH_TRANSLATION_MODEL": ovh_client.translation_model
        }

        return {
            "success": True,
            "model_mapping": model_mapping,
            "environment_config": environment_config,
            "model_descriptions": {
                ovh_client.main_model: "Primary model for most AI tasks",
                ovh_client.preprocessing_model: "Specialized for text preprocessing and PII removal",
                ovh_client.translation_model: "Optimized for language translation tasks"
            }
        }

    except Exception as e:
        logger.error(f"Failed to get model configuration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get model configuration: {str(e)}"
        )

