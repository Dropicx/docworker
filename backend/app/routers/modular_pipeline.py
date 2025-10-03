"""
Modular Pipeline Router

API endpoints for managing user-configurable pipeline:
- OCR engine configuration
- Dynamic pipeline steps (CRUD)
- Available AI models
- Step reordering
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, Field, validator
from sqlalchemy.orm import Session

from app.database.connection import get_session
from app.database.modular_pipeline_models import (
    OCRConfigurationDB,
    DynamicPipelineStepDB,
    AvailableModelDB,
    OCREngineEnum,
    ModelProvider
)
from app.services.modular_pipeline_executor import ModularPipelineManager
from app.services.ocr_engine_manager import OCREngineManager
from app.routers.settings_unified import verify_session_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])

# ==================== PYDANTIC MODELS ====================

class OCRConfigRequest(BaseModel):
    """Request model for OCR configuration update"""
    selected_engine: OCREngineEnum
    tesseract_config: Optional[Dict[str, Any]] = None
    paddleocr_config: Optional[Dict[str, Any]] = None
    vision_llm_config: Optional[Dict[str, Any]] = None
    hybrid_config: Optional[Dict[str, Any]] = None

class OCRConfigResponse(BaseModel):
    """Response model for OCR configuration"""
    id: int
    selected_engine: str
    tesseract_config: Optional[Dict[str, Any]]
    paddleocr_config: Optional[Dict[str, Any]]
    vision_llm_config: Optional[Dict[str, Any]]
    hybrid_config: Optional[Dict[str, Any]]
    last_modified: datetime

    class Config:
        from_attributes = True


class PipelineStepRequest(BaseModel):
    """Request model for creating/updating pipeline step"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    order: int = Field(..., ge=1)
    enabled: bool = True
    prompt_template: str = Field(..., min_length=1)
    selected_model_id: int
    temperature: Optional[float] = Field(0.7, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(None, ge=100, le=16000)
    retry_on_failure: bool = True
    max_retries: int = Field(3, ge=0, le=10)
    input_from_previous_step: bool = True
    output_format: Optional[str] = Field("text", pattern="^(text|json|markdown)$")

    @validator('prompt_template')
    def validate_prompt(cls, v):
        """Validate prompt template contains {input_text} placeholder"""
        if '{input_text}' not in v:
            raise ValueError('Prompt template must contain {input_text} placeholder')
        return v


class PipelineStepResponse(BaseModel):
    """Response model for pipeline step"""
    id: int
    name: str
    description: Optional[str]
    order: int
    enabled: bool
    prompt_template: str
    selected_model_id: int
    temperature: Optional[float]
    max_tokens: Optional[int]
    retry_on_failure: bool
    max_retries: int
    input_from_previous_step: bool
    output_format: Optional[str]
    created_at: datetime
    last_modified: datetime
    modified_by: Optional[str]

    class Config:
        from_attributes = True


class ModelResponse(BaseModel):
    """Response model for available model"""
    id: int
    name: str
    display_name: str
    provider: str
    description: Optional[str]
    max_tokens: Optional[int]
    supports_vision: bool
    is_enabled: bool

    class Config:
        from_attributes = True


class StepReorderRequest(BaseModel):
    """Request model for reordering steps"""
    step_ids: List[int] = Field(..., min_items=1)


class EngineStatusResponse(BaseModel):
    """Response model for OCR engine status"""
    engine: str
    available: bool
    description: str
    speed: str
    accuracy: str
    cost: str
    configuration: Dict[str, Any]


# ==================== OCR CONFIGURATION ENDPOINTS ====================

@router.get("/ocr-config", response_model=OCRConfigResponse)
async def get_ocr_config(
    db: Session = Depends(get_session),
    authenticated: bool = Depends(verify_session_token)
):
    """
    Get current OCR engine configuration.
    Requires authentication.
    """
    if not authenticated:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    manager = ModularPipelineManager(db)
    config = manager.get_ocr_config()

    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="OCR configuration not found")

    return config


@router.put("/ocr-config", response_model=OCRConfigResponse)
async def update_ocr_config(
    config_request: OCRConfigRequest,
    db: Session = Depends(get_session),
    authenticated: bool = Depends(verify_session_token)
):
    """
    Update OCR engine configuration.
    Requires authentication.
    """
    if not authenticated:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    manager = ModularPipelineManager(db)

    try:
        config_data = config_request.dict()
        config_data["modified_by"] = "settings_ui"

        config = manager.update_ocr_config(config_data)

        if not config:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update OCR configuration")

        logger.info(f"✅ OCR configuration updated: {config.selected_engine}")
        return config

    except Exception as e:
        logger.error(f"❌ Failed to update OCR config: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/ocr-engines", response_model=Dict[str, EngineStatusResponse])
async def get_available_engines(
    db: Session = Depends(get_session),
    authenticated: bool = Depends(verify_session_token)
):
    """
    Get information about available OCR engines.
    Requires authentication.
    """
    if not authenticated:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    ocr_manager = OCREngineManager(db)

    try:
        engines = ocr_manager.get_available_engines()
        return engines

    except Exception as e:
        logger.error(f"❌ Failed to get OCR engines: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/ocr-engines/{engine}", response_model=EngineStatusResponse)
async def get_engine_status(
    engine: OCREngineEnum,
    db: Session = Depends(get_session),
    authenticated: bool = Depends(verify_session_token)
):
    """
    Get detailed status of a specific OCR engine.
    Requires authentication.
    """
    if not authenticated:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    ocr_manager = OCREngineManager(db)

    try:
        status_info = ocr_manager.get_engine_status(engine)
        return status_info

    except Exception as e:
        logger.error(f"❌ Failed to get engine status: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# ==================== PIPELINE STEPS ENDPOINTS ====================

@router.get("/steps", response_model=List[PipelineStepResponse])
async def get_all_steps(
    db: Session = Depends(get_session),
    authenticated: bool = Depends(verify_session_token)
):
    """
    Get all pipeline steps (enabled and disabled).
    Requires authentication.
    """
    if not authenticated:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    manager = ModularPipelineManager(db)

    try:
        steps = manager.get_all_steps()
        return steps

    except Exception as e:
        logger.error(f"❌ Failed to get pipeline steps: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/steps/{step_id}", response_model=PipelineStepResponse)
async def get_step(
    step_id: int,
    db: Session = Depends(get_session),
    authenticated: bool = Depends(verify_session_token)
):
    """
    Get a single pipeline step by ID.
    Requires authentication.
    """
    if not authenticated:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    manager = ModularPipelineManager(db)

    step = manager.get_step(step_id)
    if not step:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Step {step_id} not found")

    return step


@router.post("/steps", response_model=PipelineStepResponse, status_code=status.HTTP_201_CREATED)
async def create_step(
    step_request: PipelineStepRequest,
    db: Session = Depends(get_session),
    authenticated: bool = Depends(verify_session_token)
):
    """
    Create a new pipeline step.
    Requires authentication.
    """
    if not authenticated:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    manager = ModularPipelineManager(db)

    try:
        step_data = step_request.dict()
        step_data["modified_by"] = "settings_ui"

        step = manager.create_step(step_data)

        logger.info(f"✅ Created pipeline step: {step.name} (order: {step.order})")
        return step

    except Exception as e:
        logger.error(f"❌ Failed to create pipeline step: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.put("/steps/{step_id}", response_model=PipelineStepResponse)
async def update_step(
    step_id: int,
    step_request: PipelineStepRequest,
    db: Session = Depends(get_session),
    authenticated: bool = Depends(verify_session_token)
):
    """
    Update an existing pipeline step.
    Requires authentication.
    """
    if not authenticated:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    manager = ModularPipelineManager(db)

    try:
        step_data = step_request.dict()
        step_data["modified_by"] = "settings_ui"

        step = manager.update_step(step_id, step_data)

        if not step:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Step {step_id} not found")

        logger.info(f"✅ Updated pipeline step: {step.name} (ID: {step_id})")
        return step

    except Exception as e:
        logger.error(f"❌ Failed to update pipeline step: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.delete("/steps/{step_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_step(
    step_id: int,
    db: Session = Depends(get_session),
    authenticated: bool = Depends(verify_session_token)
):
    """
    Delete a pipeline step.
    Requires authentication.
    """
    if not authenticated:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    manager = ModularPipelineManager(db)

    success = manager.delete_step(step_id)

    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Step {step_id} not found")

    logger.info(f"✅ Deleted pipeline step ID: {step_id}")
    return None


@router.post("/steps/reorder")
async def reorder_steps(
    reorder_request: StepReorderRequest,
    db: Session = Depends(get_session),
    authenticated: bool = Depends(verify_session_token)
):
    """
    Reorder pipeline steps.
    Requires authentication.
    """
    if not authenticated:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    manager = ModularPipelineManager(db)

    try:
        success = manager.reorder_steps(reorder_request.step_ids)

        if not success:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to reorder steps")

        logger.info(f"✅ Reordered pipeline steps: {reorder_request.step_ids}")
        return {"success": True, "message": "Steps reordered successfully"}

    except Exception as e:
        logger.error(f"❌ Failed to reorder steps: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# ==================== AVAILABLE MODELS ENDPOINTS ====================

@router.get("/models", response_model=List[ModelResponse])
async def get_available_models(
    enabled_only: bool = False,
    db: Session = Depends(get_session),
    authenticated: bool = Depends(verify_session_token)
):
    """
    Get all available AI models.
    Requires authentication.

    Args:
        enabled_only: If True, only return enabled models
    """
    if not authenticated:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    manager = ModularPipelineManager(db)

    try:
        models = manager.get_all_models(enabled_only=enabled_only)
        return models

    except Exception as e:
        logger.error(f"❌ Failed to get available models: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/models/{model_id}", response_model=ModelResponse)
async def get_model(
    model_id: int,
    db: Session = Depends(get_session),
    authenticated: bool = Depends(verify_session_token)
):
    """
    Get a single model by ID.
    Requires authentication.
    """
    if not authenticated:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    manager = ModularPipelineManager(db)

    model = manager.get_model(model_id)
    if not model:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Model {model_id} not found")

    return model
