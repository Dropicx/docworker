import os
import logging
import time
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import secrets

from fastapi import APIRouter, HTTPException, Depends, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field, ValidationError, validator

from app.models.document_types import (
    DocumentClass,
    DocumentPrompts,
    PromptTestRequest,
    PromptTestResponse
)

def convert_frontend_to_db_document_type(frontend_type: str) -> DocumentClass:
    """Convert frontend document type (lowercase) to database enum (uppercase)"""
    conversion_map = {
        "arztbrief": DocumentClass.ARZTBRIEF,
        "befundbericht": DocumentClass.BEFUNDBERICHT,
        "laborwerte": DocumentClass.LABORWERTE
    }
    if frontend_type.lower() not in conversion_map:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid document type: {frontend_type}. Must be one of: arztbrief, befundbericht, laborwerte"
        )
    return conversion_map[frontend_type.lower()]
from app.services.prompt_manager import PromptManager
from app.services.database_prompt_manager import DatabasePromptManager
from app.services.global_prompts_manager import GlobalPromptsManager
from app.services.ovh_client import OVHClient
from app.database.connection import get_session
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/settings", tags=["settings"])

# Security
security = HTTPBearer(auto_error=False)

# Session storage (in production, use Redis or database)
authenticated_sessions: Dict[str, datetime] = {}
SESSION_DURATION = timedelta(hours=24)

# Database dependency
def get_db_session() -> Session:
    """Get database session"""
    return next(get_session())

# Initialize services
prompt_manager = PromptManager()
global_prompts_manager = GlobalPromptsManager()

class AuthRequest(BaseModel):
    code: str = Field(..., description="Access code for settings")

class AuthResponse(BaseModel):
    success: bool
    token: Optional[str] = None
    message: str

class PromptUpdateRequest(BaseModel):
    prompts: DocumentPrompts
    user: Optional[str] = Field(None, description="Username making the change")
    
    @validator('prompts', pre=True)
    def convert_document_type(cls, v):
        if isinstance(v, dict) and 'document_type' in v:
            # Convert frontend lowercase to database uppercase
            frontend_type = v['document_type']
            if isinstance(frontend_type, str):
                conversion_map = {
                    "arztbrief": "ARZTBRIEF",
                    "befundbericht": "BEFUNDBERICHT", 
                    "laborwerte": "LABORWERTE"
                }
                if frontend_type.lower() in conversion_map:
                    v['document_type'] = conversion_map[frontend_type.lower()]
        return v

class ImportRequest(BaseModel):
    data: Dict[str, Any] = Field(..., description="Prompt data to import")

def verify_access_code(code: str) -> bool:
    """Verify the settings access code."""
    correct_code = os.getenv("SETTINGS_ACCESS_CODE", "milan")
    return code == correct_code

def generate_session_token() -> str:
    """Generate a secure session token."""
    return secrets.token_urlsafe(32)

def verify_session_token(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> bool:
    """Verify session token from Authorization header."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    # Check if token exists and is not expired
    if token in authenticated_sessions:
        session_time = authenticated_sessions[token]
        if datetime.now() - session_time < SESSION_DURATION:
            # Update last activity time
            authenticated_sessions[token] = datetime.now()
            return True
        else:
            # Session expired
            del authenticated_sessions[token]

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )

# Cleanup old sessions periodically
def cleanup_expired_sessions():
    """Remove expired sessions from memory."""
    current_time = datetime.now()
    expired = [
        token for token, last_activity in authenticated_sessions.items()
        if current_time - last_activity >= SESSION_DURATION
    ]
    for token in expired:
        del authenticated_sessions[token]

@router.post("/auth", response_model=AuthResponse)
async def authenticate(auth_request: AuthRequest):
    """
    Authenticate with access code to get session token.

    The access code is set via environment variable SETTINGS_ACCESS_CODE.
    Default code is 'milan' if not set.
    """
    cleanup_expired_sessions()

    if verify_access_code(auth_request.code):
        token = generate_session_token()
        authenticated_sessions[token] = datetime.now()

        logger.info(f"Successful authentication from settings page")

        return AuthResponse(
            success=True,
            token=token,
            message="Authentication successful"
        )
    else:
        logger.warning(f"Failed authentication attempt with code: {auth_request.code[:2]}...")

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access code"
        )

@router.get("/check-auth")
async def check_authentication(authenticated: bool = Depends(verify_session_token)):
    """Check if current session is authenticated."""
    return {"authenticated": authenticated}

@router.get("/prompts/{document_type}")
async def get_prompts(
    document_type: str,
    authenticated: bool = Depends(verify_session_token),
    db: Session = Depends(get_db_session)
):
    """
    Get prompts for a specific document type.

    Requires authentication.
    """
    try:
        # Convert frontend document type to database enum
        db_document_type = convert_frontend_to_db_document_type(document_type)
        
        # Try database first, fallback to file-based
        db_prompt_manager = DatabasePromptManager(db)
        prompts = db_prompt_manager.load_prompts(db_document_type)

        return {
            "document_type": document_type,
            "prompts": {
                "classification_prompt": prompts.classification_prompt,
                "preprocessing_prompt": prompts.preprocessing_prompt,
                "translation_prompt": prompts.translation_prompt,
                "fact_check_prompt": prompts.fact_check_prompt,
                "grammar_check_prompt": prompts.grammar_check_prompt,
                "language_translation_prompt": prompts.language_translation_prompt,
                "final_check_prompt": prompts.final_check_prompt
            },
            "metadata": {
                "version": prompts.version,
                "last_modified": prompts.last_modified.isoformat() if prompts.last_modified else None,
                "modified_by": prompts.modified_by
            }
        }
    except Exception as e:
        logger.error(f"Failed to get prompts for {document_type.value}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load prompts: {str(e)}"
        )

@router.put("/prompts/{document_type}")
async def update_prompts(
    document_type: str,
    update_request: PromptUpdateRequest,
    authenticated: bool = Depends(verify_session_token),
    db: Session = Depends(get_db_session)
):
    """
    Update prompts for a specific document type.

    Requires authentication.
    """
    try:
        # Convert frontend document type to database enum
        db_document_type = convert_frontend_to_db_document_type(document_type)
        
        # Ensure document type matches
        update_request.prompts.document_type = db_document_type

        # Try database first, fallback to file-based
        db_prompt_manager = DatabasePromptManager(db)
        success = db_prompt_manager.save_prompts(db_document_type, update_request.prompts)

        if not success:
            # Fallback to file-based system
            success = prompt_manager.save_prompts(
                document_type=db_document_type,
                prompts=update_request.prompts,
                user=update_request.user or "settings_ui",
                create_backup=True
            )

        if success:
            logger.info(f"Updated prompts for {document_type} by {update_request.user or 'unknown'}")
            return {
                "success": True,
                "message": f"Prompts updated successfully for {document_type}",
                "version": update_request.prompts.version
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save prompts"
            )

    except ValidationError as e:
        logger.error(f"Validation error updating prompts for {document_type}: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Validation error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Failed to update prompts for {document_type}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update prompts: {str(e)}"
        )

@router.post("/prompts/{document_type}/reset")
async def reset_prompts(
    document_type: str,
    authenticated: bool = Depends(verify_session_token),
    db: Session = Depends(get_db_session)
):
    """
    Reset prompts to defaults for a specific document type.

    Requires authentication.
    """
    try:
        # Convert frontend document type to database enum
        db_document_type = convert_frontend_to_db_document_type(document_type)
        
        # Try database first, fallback to file-based
        db_prompt_manager = DatabasePromptManager(db)
        success = db_prompt_manager.reset_prompts(db_document_type)
        
        if not success:
            # Fallback to file-based system
            success = prompt_manager.reset_to_defaults(db_document_type)

        if success:
            logger.info(f"Reset prompts to defaults for {document_type}")
            return {
                "success": True,
                "message": f"Prompts reset to defaults for {document_type}"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to reset prompts"
            )

    except Exception as e:
        logger.error(f"Failed to reset prompts for {document_type}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset prompts: {str(e)}"
        )

@router.post("/test-prompt", response_model=PromptTestResponse)
async def test_prompt(
    test_request: PromptTestRequest,
    authenticated: bool = Depends(verify_session_token)
):
    """
    Test a prompt with sample text using OVH API.

    Requires authentication.
    """
    try:
        start_time = time.time()

        # Initialize OVH client
        ovh_client = OVHClient()

        # Check OVH connection
        connected, error = await ovh_client.check_connection()
        if not connected:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"OVH API not available: {error}"
            )

        # Replace placeholders in prompt
        prompt = test_request.prompt.replace("{text}", test_request.sample_text)
        prompt = prompt.replace("{language}", "Deutsch")  # Default for testing

        # Process with OVH
        result = await ovh_client.process_medical_text(
            text=test_request.sample_text,
            instruction=prompt,
            temperature=test_request.temperature,
            max_tokens=test_request.max_tokens
        )

        processing_time = time.time() - start_time

        return PromptTestResponse(
            result=result,
            processing_time=processing_time,
            model_used=test_request.model or ovh_client.main_model,
            tokens_used=None  # OVH doesn't provide token count easily
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Prompt test failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Prompt test failed: {str(e)}"
        )

@router.get("/export")
async def export_prompts(
    document_type: Optional[DocumentClass] = None,
    authenticated: bool = Depends(verify_session_token),
    db: Session = Depends(get_db_session)
):
    """
    Export prompts for backup or sharing.

    If document_type is specified, exports only that type.
    Otherwise exports all document types.

    Requires authentication.
    """
    try:
        # Try database first, fallback to file-based
        db_prompt_manager = DatabasePromptManager(db)
        
        if document_type:
            # Export specific document type
            prompts = db_prompt_manager.load_prompts(document_type)
            export_data = {
                "export_date": datetime.now().isoformat(),
                "version": prompts.version,
                "prompts": {
                    document_type.value: prompts.dict()
                }
            }
        else:
            # Export all document types
            export_data = {
                "export_date": datetime.now().isoformat(),
                "version": 1,
                "prompts": {}
            }
            
            for doc_type in DocumentClass:
                try:
                    prompts = db_prompt_manager.load_prompts(doc_type)
                    export_data["prompts"][doc_type.value] = prompts.dict()
                except Exception as e:
                    logger.warning(f"Failed to export {doc_type.value}: {e}")

        return export_data

    except Exception as e:
        logger.error(f"Failed to export prompts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export prompts: {str(e)}"
        )

@router.post("/import")
async def import_prompts(
    import_request: ImportRequest,
    authenticated: bool = Depends(verify_session_token),
    db: Session = Depends(get_db_session)
):
    """
    Import prompts from exported data.

    Requires authentication.
    """
    try:
        # Try database first, fallback to file-based
        db_prompt_manager = DatabasePromptManager(db)
        results = {}
        
        # Import each document type
        for doc_type_str, prompts_data in import_request.data.prompts.items():
            try:
                doc_type = DocumentClass(doc_type_str)
                # Convert dict to DocumentPrompts object
                prompts = DocumentPrompts(**prompts_data)
                prompts.modified_by = "import"
                
                success = db_prompt_manager.save_prompts(doc_type, prompts)
                if not success:
                    # Fallback to file-based system
                    success = prompt_manager.save_prompts(doc_type, prompts, user="import")
                
                results[doc_type_str] = success
            except Exception as e:
                logger.error(f"Failed to import {doc_type_str}: {e}")
                results[doc_type_str] = False

        # Count successes and failures
        success_count = sum(1 for success in results.values() if success)
        failure_count = len(results) - success_count

        logger.info(f"Import completed: {success_count} success, {failure_count} failures")

        return {
            "success": failure_count == 0,
            "message": f"Imported {success_count} document types successfully",
            "results": results
        }

    except Exception as e:
        logger.error(f"Failed to import prompts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to import prompts: {str(e)}"
        )

@router.get("/document-types")
async def get_document_types(
    authenticated: bool = Depends(verify_session_token)
):
    """
    Get list of available document types with descriptions.

    Requires authentication.
    """
    from app.models.document_types import DOCUMENT_TYPE_DESCRIPTIONS

    return {
        "document_types": [
            {
                "id": doc_class.value,
                "name": DOCUMENT_TYPE_DESCRIPTIONS[doc_class]["name"],
                "description": DOCUMENT_TYPE_DESCRIPTIONS[doc_class]["description"],
                "icon": DOCUMENT_TYPE_DESCRIPTIONS[doc_class]["icon"],
                "examples": DOCUMENT_TYPE_DESCRIPTIONS[doc_class]["examples"]
            }
            for doc_class in DocumentClass
        ]
    }

# Pipeline Step Management Endpoints

class PipelineStepUpdateRequest(BaseModel):
    """Request to update pipeline step configuration"""
    step_name: str = Field(..., description="Name of the pipeline step")
    enabled: bool = Field(..., description="Whether to enable or disable the step")

@router.put("/pipeline-steps/{document_type}")
async def update_pipeline_step(
    document_type: str,
    update_request: PipelineStepUpdateRequest,
    authenticated: bool = Depends(verify_session_token),
    db: Session = Depends(get_db_session)
):
    """
    Enable or disable a specific pipeline step for a document type.
    
    Args:
        document_type: The document type to update
        update_request: Step name and enabled status
        
    Returns:
        Updated pipeline configuration
    """
    if not authenticated:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    try:
        # Convert frontend document type to database enum
        db_document_type = convert_frontend_to_db_document_type(document_type)
        
        # Try database first, fallback to file-based
        db_prompt_manager = DatabasePromptManager(db)
        prompts = db_prompt_manager.load_prompts(db_document_type)
        
        # Update the specific step
        if update_request.step_name in prompts.pipeline_steps:
            prompts.pipeline_steps[update_request.step_name].enabled = update_request.enabled
            prompts.last_modified = datetime.now()
            prompts.modified_by = "admin"
            
            # Save the updated prompts
            success = db_prompt_manager.save_prompts(db_document_type, prompts)
            if not success:
                # Fallback to file-based system
                prompt_manager = PromptManager()
                prompt_manager.save_prompts(db_document_type, prompts)
            
            logger.info(f"Updated pipeline step {update_request.step_name} for {document_type}: enabled={update_request.enabled}")
            
            return {
                "success": True,
                "message": f"Pipeline step '{update_request.step_name}' {'enabled' if update_request.enabled else 'disabled'} for {document_type}",
                "pipeline_steps": {
                    name: {
                        "enabled": config.enabled,
                        "order": config.order,
                        "name": config.name,
                        "description": config.description
                    }
                    for name, config in prompts.pipeline_steps.items()
                }
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Pipeline step '{update_request.step_name}' not found"
            )
            
    except Exception as e:
        logger.error(f"Failed to update pipeline step: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update pipeline step: {str(e)}"
        )

@router.get("/pipeline-steps/{document_type}")
async def get_pipeline_steps(
    document_type: str,
    authenticated: bool = Depends(verify_session_token),
    db: Session = Depends(get_db_session)
):
    """
    Get pipeline step configuration for a document type.
    
    Args:
        document_type: The document type to get configuration for
        
    Returns:
        Pipeline step configuration
    """
    if not authenticated:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    try:
        # Convert frontend document type to database enum
        db_document_type = convert_frontend_to_db_document_type(document_type)
        
        # Try database first, fallback to file-based
        db_prompt_manager = DatabasePromptManager(db)
        prompts = db_prompt_manager.load_prompts(db_document_type)
        
        return {
            "document_type": document_type,
            "pipeline_steps": {
                name: {
                    "enabled": config.enabled,
                    "order": config.order,
                    "name": config.name,
                    "description": config.description
                }
                for name, config in prompts.pipeline_steps.items()
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get pipeline steps: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get pipeline steps: {str(e)}"
        )

@router.post("/pipeline-steps/{document_type}/reset")
async def reset_pipeline_steps(
    document_type: str,
    authenticated: bool = Depends(verify_session_token),
    db: Session = Depends(get_db_session)
):
    """
    Reset all pipeline steps to default (enabled) state for a document type.
    
    Args:
        document_type: The document type to reset
        
    Returns:
        Reset pipeline configuration
    """
    if not authenticated:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    try:
        # Convert frontend document type to database enum
        db_document_type = convert_frontend_to_db_document_type(document_type)
        
        # Try database first, fallback to file-based
        db_prompt_manager = DatabasePromptManager(db)
        prompts = db_prompt_manager.load_prompts(db_document_type)
        
        # Reset all steps to enabled
        for step_config in prompts.pipeline_steps.values():
            step_config.enabled = True
        
        prompts.last_modified = datetime.now()
        prompts.modified_by = "admin"
        
        # Save the updated prompts
        success = db_prompt_manager.save_prompts(db_document_type, prompts)
        if not success:
            # Fallback to file-based system
            prompt_manager = PromptManager()
            prompt_manager.save_prompts(db_document_type, prompts)
        
        logger.info(f"Reset all pipeline steps for {document_type}")
        
        return {
            "success": True,
            "message": f"All pipeline steps reset to enabled for {document_type}",
            "pipeline_steps": {
                name: {
                    "enabled": config.enabled,
                    "order": config.order,
                    "name": config.name,
                    "description": config.description
                }
                for name, config in prompts.pipeline_steps.items()
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to reset pipeline steps: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset pipeline steps: {str(e)}"
        )

# Pipeline Settings Management

class PipelineSettingsRequest(BaseModel):
    """Request to update pipeline settings"""
    settings: Dict[str, Any] = Field(..., description="Pipeline settings to update")

@router.get("/pipeline-settings")
async def get_pipeline_settings(
    authenticated: bool = Depends(verify_session_token)
):
    """
    Get current pipeline optimization settings.

    Returns current environment variable settings and configuration.
    """
    if not authenticated:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )

    try:
        # Get current settings from environment variables
        settings = {
            "use_optimized_pipeline": os.getenv("USE_OPTIMIZED_PIPELINE", "true").lower() == "true",
            "pipeline_cache_timeout": int(os.getenv("PIPELINE_CACHE_TIMEOUT", "300")),
            "enable_medical_validation": os.getenv("ENABLE_MEDICAL_VALIDATION", "true").lower() == "true",
            "enable_classification": os.getenv("ENABLE_CLASSIFICATION", "true").lower() == "true",
            "enable_preprocessing": os.getenv("ENABLE_PREPROCESSING", "true").lower() == "true",
            "enable_translation": os.getenv("ENABLE_TRANSLATION", "true").lower() == "true",
            "enable_fact_check": os.getenv("ENABLE_FACT_CHECK", "true").lower() == "true",
            "enable_grammar_check": os.getenv("ENABLE_GRAMMAR_CHECK", "true").lower() == "true",
            "enable_language_translation": os.getenv("ENABLE_LANGUAGE_TRANSLATION", "true").lower() == "true",
            "enable_final_check": os.getenv("ENABLE_FINAL_CHECK", "true").lower() == "true",
            "enable_formatting": os.getenv("ENABLE_FORMATTING", "true").lower() == "true"
        }

        return {
            "settings": settings,
            "message": "Pipeline settings retrieved successfully"
        }

    except Exception as e:
        logger.error(f"Failed to get pipeline settings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get pipeline settings: {str(e)}"
        )

@router.put("/pipeline-settings")
async def update_pipeline_settings(
    update_request: PipelineSettingsRequest,
    authenticated: bool = Depends(verify_session_token)
):
    """
    Update pipeline optimization settings.

    Note: In a production environment, this would update a configuration file
    or database. For demo purposes, we'll return the updated settings.
    """
    if not authenticated:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )

    try:
        # Validate settings
        valid_settings = {
            "use_optimized_pipeline": bool,
            "pipeline_cache_timeout": int,
            "enable_medical_validation": bool,
            "enable_classification": bool,
            "enable_preprocessing": bool,
            "enable_translation": bool,
            "enable_fact_check": bool,
            "enable_grammar_check": bool,
            "enable_language_translation": bool,
            "enable_final_check": bool,
            "enable_formatting": bool
        }

        updated_settings = {}
        for key, value in update_request.settings.items():
            if key in valid_settings:
                # Type validation
                expected_type = valid_settings[key]
                if key == "pipeline_cache_timeout":
                    # Validate cache timeout range
                    timeout_value = int(value)
                    if timeout_value < 60 or timeout_value > 3600:
                        raise ValueError(f"Cache timeout must be between 60 and 3600 seconds")
                    updated_settings[key] = timeout_value
                else:
                    updated_settings[key] = expected_type(value)

        # In a real implementation, you would update environment variables or config file
        # For now, we'll log the changes and return success
        logger.info(f"Pipeline settings update requested: {updated_settings}")
        logger.warning("Pipeline settings updates require application restart to take effect")

        # Get current settings (simulated update)
        current_settings = {
            "use_optimized_pipeline": updated_settings.get("use_optimized_pipeline", os.getenv("USE_OPTIMIZED_PIPELINE", "true").lower() == "true"),
            "pipeline_cache_timeout": updated_settings.get("pipeline_cache_timeout", int(os.getenv("PIPELINE_CACHE_TIMEOUT", "300"))),
            "enable_medical_validation": updated_settings.get("enable_medical_validation", os.getenv("ENABLE_MEDICAL_VALIDATION", "true").lower() == "true"),
            "enable_classification": updated_settings.get("enable_classification", os.getenv("ENABLE_CLASSIFICATION", "true").lower() == "true"),
            "enable_preprocessing": updated_settings.get("enable_preprocessing", os.getenv("ENABLE_PREPROCESSING", "true").lower() == "true"),
            "enable_translation": updated_settings.get("enable_translation", os.getenv("ENABLE_TRANSLATION", "true").lower() == "true"),
            "enable_fact_check": updated_settings.get("enable_fact_check", os.getenv("ENABLE_FACT_CHECK", "true").lower() == "true"),
            "enable_grammar_check": updated_settings.get("enable_grammar_check", os.getenv("ENABLE_GRAMMAR_CHECK", "true").lower() == "true"),
            "enable_language_translation": updated_settings.get("enable_language_translation", os.getenv("ENABLE_LANGUAGE_TRANSLATION", "true").lower() == "true"),
            "enable_final_check": updated_settings.get("enable_final_check", os.getenv("ENABLE_FINAL_CHECK", "true").lower() == "true"),
            "enable_formatting": updated_settings.get("enable_formatting", os.getenv("ENABLE_FORMATTING", "true").lower() == "true")
        }

        return {
            "success": True,
            "message": "Pipeline settings updated successfully. Restart required for changes to take effect.",
            "settings": current_settings,
            "warning": "Application restart required for environment variable changes to take effect"
        }

    except ValueError as e:
        logger.error(f"Validation error updating pipeline settings: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Validation error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Failed to update pipeline settings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update pipeline settings: {str(e)}"
        )

# Global Prompts Management

class GlobalPromptUpdateRequest(BaseModel):
    """Request to update global prompts"""
    medical_validation_prompt: str = Field(..., description="Universal medical validation prompt")
    classification_prompt: str = Field(..., description="Universal document classification prompt")
    preprocessing_prompt: str = Field(..., description="Universal preprocessing prompt")
    grammar_check_prompt: str = Field(..., description="Universal grammar check prompt")
    language_translation_prompt: str = Field(..., description="Universal language translation prompt")
    user: Optional[str] = Field(None, description="Username making the change")

@router.get("/global-prompts")
async def get_global_prompts(
    authenticated: bool = Depends(verify_session_token)
):
    """
    Get current global/universal prompts used across all document types.

    These prompts handle preprocessing steps that should be consistent
    regardless of document type:
    - Medical validation
    - Document classification
    - Personal data removal
    - Grammar checking
    - Language translation
    """
    if not authenticated:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )

    try:
        prompts = global_prompts_manager.get_global_prompts()

        return {
            "global_prompts": {
                "medical_validation_prompt": prompts.medical_validation_prompt,
                "classification_prompt": prompts.classification_prompt,
                "preprocessing_prompt": prompts.preprocessing_prompt,
                "grammar_check_prompt": prompts.grammar_check_prompt,
                "language_translation_prompt": prompts.language_translation_prompt
            },
            "metadata": {
                "version": prompts.version,
                "last_modified": prompts.last_modified,
                "modified_by": prompts.modified_by
            },
            "statistics": global_prompts_manager.get_statistics()
        }

    except Exception as e:
        logger.error(f"Failed to get global prompts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get global prompts: {str(e)}"
        )

@router.put("/global-prompts")
async def update_global_prompts(
    update_request: GlobalPromptUpdateRequest,
    authenticated: bool = Depends(verify_session_token)
):
    """
    Update global/universal prompts.

    These prompts affect all document types and should be carefully tested
    before updating in production.
    """
    if not authenticated:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )

    try:
        # Get current prompts
        current_prompts = global_prompts_manager.get_global_prompts()

        # Create updated prompts object
        from app.services.global_prompts_manager import GlobalPrompts
        updated_prompts = GlobalPrompts(
            medical_validation_prompt=update_request.medical_validation_prompt,
            classification_prompt=update_request.classification_prompt,
            preprocessing_prompt=update_request.preprocessing_prompt,
            grammar_check_prompt=update_request.grammar_check_prompt,
            language_translation_prompt=update_request.language_translation_prompt,
            version=current_prompts.version,  # Will be incremented by manager
            last_modified=current_prompts.last_modified,  # Will be updated by manager
            modified_by=current_prompts.modified_by  # Will be updated by manager
        )

        # Update prompts
        success = global_prompts_manager.update_global_prompts(
            updated_prompts,
            update_request.user or "admin"
        )

        if success:
            logger.info(f"Global prompts updated by {update_request.user or 'unknown'}")
            return {
                "success": True,
                "message": "Global prompts updated successfully",
                "version": updated_prompts.version
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save global prompts"
            )

    except ValidationError as e:
        logger.error(f"Validation error updating global prompts: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Validation error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Failed to update global prompts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update global prompts: {str(e)}"
        )

@router.post("/global-prompts/reset")
async def reset_global_prompts(
    authenticated: bool = Depends(verify_session_token)
):
    """
    Reset global prompts to default values.

    This will create a backup of current prompts before resetting.
    """
    if not authenticated:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )

    try:
        success = global_prompts_manager.reset_to_defaults()

        if success:
            logger.info("Global prompts reset to defaults")
            return {
                "success": True,
                "message": "Global prompts reset to default values"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to reset global prompts"
            )

    except Exception as e:
        logger.error(f"Failed to reset global prompts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset global prompts: {str(e)}"
        )

@router.get("/global-prompts/export")
async def export_global_prompts(
    authenticated: bool = Depends(verify_session_token)
):
    """
    Export global prompts for backup or sharing.
    """
    if not authenticated:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )

    try:
        export_data = global_prompts_manager.export_global_prompts()
        return export_data

    except Exception as e:
        logger.error(f"Failed to export global prompts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export global prompts: {str(e)}"
        )

@router.post("/global-prompts/import")
async def import_global_prompts(
    import_request: ImportRequest,
    authenticated: bool = Depends(verify_session_token)
):
    """
    Import global prompts from exported data.
    """
    if not authenticated:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )

    try:
        success = global_prompts_manager.import_global_prompts(
            import_request.data,
            user="import_admin"
        )

        if success:
            logger.info("Global prompts imported successfully")
            return {
                "success": True,
                "message": "Global prompts imported successfully"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to import global prompts"
            )

    except Exception as e:
        logger.error(f"Failed to import global prompts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to import global prompts: {str(e)}"
        )

@router.post("/global-prompts/test")
async def test_global_prompt(
    test_request: PromptTestRequest,
    authenticated: bool = Depends(verify_session_token)
):
    """
    Test a global prompt with sample text using OVH API.
    """
    if not authenticated:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )

    try:
        start_time = time.time()

        # Initialize OVH client
        ovh_client = OVHClient()

        # Check OVH connection
        connected, error = await ovh_client.check_connection()
        if not connected:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"OVH API not available: {error}"
            )

        # Replace placeholders in prompt
        prompt = test_request.prompt.replace("{text}", test_request.sample_text)
        prompt = prompt.replace("{language}", "Deutsch")  # Default for testing

        # Process with OVH
        result = await ovh_client.process_medical_text(
            text=test_request.sample_text,
            instruction=prompt,
            temperature=test_request.temperature,
            max_tokens=test_request.max_tokens
        )

        processing_time = time.time() - start_time

        return PromptTestResponse(
            result=result,
            processing_time=processing_time,
            model_used=test_request.model or ovh_client.main_model,
            tokens_used=None  # OVH doesn't provide token count easily
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Global prompt test failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Global prompt test failed: {str(e)}"
        )