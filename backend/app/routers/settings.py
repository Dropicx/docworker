import os
import logging
import time
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import secrets

from fastapi import APIRouter, HTTPException, Depends, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field, ValidationError

from app.models.document_types import (
    DocumentClass,
    DocumentPrompts,
    PromptTestRequest,
    PromptTestResponse
)
from app.services.prompt_manager import PromptManager
from app.services.ovh_client import OVHClient

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/settings", tags=["settings"])

# Security
security = HTTPBearer(auto_error=False)

# Session storage (in production, use Redis or database)
authenticated_sessions: Dict[str, datetime] = {}
SESSION_DURATION = timedelta(hours=24)

# Initialize services
prompt_manager = PromptManager()

class AuthRequest(BaseModel):
    code: str = Field(..., description="Access code for settings")

class AuthResponse(BaseModel):
    success: bool
    token: Optional[str] = None
    message: str

class PromptUpdateRequest(BaseModel):
    prompts: DocumentPrompts
    user: Optional[str] = Field(None, description="Username making the change")

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
    document_type: DocumentClass,
    authenticated: bool = Depends(verify_session_token)
):
    """
    Get prompts for a specific document type.

    Requires authentication.
    """
    try:
        prompts = prompt_manager.get_prompts(document_type)

        return {
            "document_type": document_type.value,
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
    document_type: DocumentClass,
    update_request: PromptUpdateRequest,
    authenticated: bool = Depends(verify_session_token)
):
    """
    Update prompts for a specific document type.

    Requires authentication.
    """
    try:
        # Ensure document type matches
        update_request.prompts.document_type = document_type

        # Save prompts
        success = prompt_manager.save_prompts(
            document_type=document_type,
            prompts=update_request.prompts,
            user=update_request.user or "settings_ui",
            create_backup=True
        )

        if success:
            logger.info(f"Updated prompts for {document_type.value} by {update_request.user or 'unknown'}")
            return {
                "success": True,
                "message": f"Prompts updated successfully for {document_type.value}",
                "version": update_request.prompts.version
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save prompts"
            )

    except ValidationError as e:
        logger.error(f"Validation error updating prompts for {document_type.value}: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Validation error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Failed to update prompts for {document_type.value}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update prompts: {str(e)}"
        )

@router.post("/prompts/{document_type}/reset")
async def reset_prompts(
    document_type: DocumentClass,
    authenticated: bool = Depends(verify_session_token)
):
    """
    Reset prompts to defaults for a specific document type.

    Requires authentication.
    """
    try:
        success = prompt_manager.reset_to_defaults(document_type)

        if success:
            logger.info(f"Reset prompts to defaults for {document_type.value}")
            return {
                "success": True,
                "message": f"Prompts reset to defaults for {document_type.value}"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to reset prompts"
            )

    except Exception as e:
        logger.error(f"Failed to reset prompts for {document_type.value}: {e}")
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
    authenticated: bool = Depends(verify_session_token)
):
    """
    Export prompts for backup or sharing.

    If document_type is specified, exports only that type.
    Otherwise exports all document types.

    Requires authentication.
    """
    try:
        export_data = prompt_manager.export_prompts(document_type)

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
    authenticated: bool = Depends(verify_session_token)
):
    """
    Import prompts from exported data.

    Requires authentication.
    """
    try:
        results = prompt_manager.import_prompts(
            import_data=import_request.data,
            user="import"
        )

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