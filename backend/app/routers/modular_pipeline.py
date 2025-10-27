"""
Modular Pipeline Router

API endpoints for managing user-configurable pipeline:
- OCR engine configuration
- Dynamic pipeline steps (CRUD)
- Available AI models
- Step reordering
"""

from datetime import datetime
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.core.dependencies import get_pipeline_step_repository
from app.core.permissions import get_current_user_required, require_role
from app.database.auth_models import UserDB
from app.database.connection import get_session
from app.database.modular_pipeline_models import OCREngineEnum
from app.repositories.pipeline_step_repository import PipelineStepRepository
from app.services.document_class_manager import DocumentClassManager
from app.services.modular_pipeline_executor import ModularPipelineManager
from app.services.ocr_engine_manager import OCREngineManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])

# ==================== AUTHENTICATION ====================


def require_user_auth(current_user: UserDB = Depends(get_current_user_required)):
    """Require user authentication (USER or ADMIN role)"""
    return require_role("user")(current_user)


# ==================== PYDANTIC MODELS ====================


class OCRConfigRequest(BaseModel):
    """Request model for OCR configuration update"""

    selected_engine: OCREngineEnum
    paddleocr_config: dict[str, Any] | None = None
    vision_llm_config: dict[str, Any] | None = None
    hybrid_config: dict[str, Any] | None = None
    pii_removal_enabled: bool | None = True


class OCRConfigResponse(BaseModel):
    """Response model for OCR configuration"""

    id: int
    selected_engine: str
    paddleocr_config: dict[str, Any] | None
    vision_llm_config: dict[str, Any] | None
    hybrid_config: dict[str, Any] | None
    pii_removal_enabled: bool
    last_modified: datetime

    class Config:
        from_attributes = True


class PipelineStepRequest(BaseModel):
    """Request model for creating/updating pipeline step"""

    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    order: int = Field(..., ge=1)
    enabled: bool = True
    prompt_template: str = Field(..., min_length=1)
    selected_model_id: int
    temperature: float | None = Field(0.7, ge=0.0, le=2.0)
    max_tokens: int | None = Field(None, ge=100, le=16000)
    retry_on_failure: bool = True
    max_retries: int = Field(3, ge=0, le=10)
    input_from_previous_step: bool = True
    output_format: str | None = Field("text", pattern="^(text|json|markdown)$")

    # Pipeline branching fields
    document_class_id: int | None = None
    is_branching_step: bool = False
    branching_field: str | None = "document_type"
    post_branching: bool = False  # NEW: Runs after document-specific processing

    # Conditional execution
    required_context_variables: list[str] | None = None

    # Stop conditions (early termination)
    stop_conditions: dict[str, Any] | None = None

    @field_validator("prompt_template")
    @classmethod
    def validate_prompt(cls, v):
        """Validate prompt template contains {input_text} placeholder"""
        if "{input_text}" not in v:
            raise ValueError("Prompt template must contain {input_text} placeholder")
        return v

    @field_validator("stop_conditions")
    @classmethod
    def validate_stop_conditions(cls, v):
        """Validate stop_conditions structure"""
        if v is None:
            return v

        # Ensure it's a dictionary
        if not isinstance(v, dict):
            raise ValueError("stop_conditions must be a dictionary")

        # Validate stop_on_values exists and is a non-empty list
        if "stop_on_values" not in v:
            raise ValueError("stop_conditions must contain stop_on_values")

        if not isinstance(v["stop_on_values"], list):
            raise ValueError("stop_on_values must be a list")

        if len(v["stop_on_values"]) == 0:
            raise ValueError("stop_on_values cannot be empty")

        # Ensure all values are strings
        if not all(isinstance(val, str) for val in v["stop_on_values"]):
            raise ValueError("All stop_on_values must be strings")

        # Ensure termination_message exists
        if not v.get("termination_message"):
            raise ValueError("termination_message is required when stop_conditions is set")

        # Provide default for termination_reason if not set
        if not v.get("termination_reason"):
            v["termination_reason"] = "Pipeline stopped"

        return v


class PipelineStepResponse(BaseModel):
    """Response model for pipeline step"""

    id: int
    name: str
    description: str | None
    order: int
    enabled: bool
    prompt_template: str
    selected_model_id: int
    temperature: float | None
    max_tokens: int | None
    retry_on_failure: bool
    max_retries: int
    input_from_previous_step: bool
    output_format: str | None
    created_at: datetime
    last_modified: datetime
    modified_by: str | None

    # Pipeline branching fields
    document_class_id: int | None
    is_branching_step: bool
    branching_field: str | None
    post_branching: bool  # NEW: Runs after document-specific processing

    # Conditional execution
    required_context_variables: list[str] | None

    # Stop conditions (early termination)
    stop_conditions: dict[str, Any] | None

    class Config:
        from_attributes = True


class ModelResponse(BaseModel):
    """Response model for available model"""

    id: int
    name: str
    display_name: str
    provider: str
    description: str | None
    max_tokens: int | None
    supports_vision: bool
    is_enabled: bool

    class Config:
        from_attributes = True


class StepReorderRequest(BaseModel):
    """Request model for reordering steps"""

    step_ids: list[int] = Field(..., min_items=1)


class EngineStatusResponse(BaseModel):
    """Response model for OCR engine status"""

    engine: str
    available: bool
    description: str
    speed: str
    accuracy: str
    cost: str
    configuration: dict[str, Any]


class DocumentClassRequest(BaseModel):
    """Request model for creating/updating document class"""

    class_key: str = Field(..., min_length=1, max_length=100)
    display_name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    icon: str | None = Field(None, max_length=10)
    examples: list[str] | None = None
    strong_indicators: list[str] | None = None
    weak_indicators: list[str] | None = None
    is_enabled: bool = True


class DocumentClassResponse(BaseModel):
    """Response model for document class"""

    id: int
    class_key: str
    display_name: str
    description: str | None
    icon: str | None
    examples: list[str] | None
    strong_indicators: list[str] | None
    weak_indicators: list[str] | None
    is_enabled: bool
    is_system_class: bool
    created_at: datetime
    last_modified: datetime
    created_by: str | None

    class Config:
        from_attributes = True


# ==================== OCR CONFIGURATION ENDPOINTS ====================


@router.get("/ocr-config", response_model=OCRConfigResponse)
async def get_ocr_config(
    db: Session = Depends(get_session), current_user: UserDB = Depends(require_user_auth)
):
    """
    Get current OCR engine configuration.
    Requires authentication.
    """

    manager = ModularPipelineManager(db)
    config = manager.get_ocr_config()

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="OCR configuration not found"
        )

    return config


@router.put("/ocr-config", response_model=OCRConfigResponse)
async def update_ocr_config(
    config_request: OCRConfigRequest,
    db: Session = Depends(get_session),
    current_user: UserDB = Depends(require_user_auth),
):
    """
    Update OCR engine configuration.
    Requires authentication.
    """

    manager = ModularPipelineManager(db)

    try:
        config_data = config_request.dict()
        config_data["modified_by"] = "settings_ui"

        config = manager.update_ocr_config(config_data)

        if not config:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update OCR configuration",
            )

        logger.info(f"✅ OCR configuration updated: {config.selected_engine}")
        return config

    except Exception as e:
        logger.error(f"❌ Failed to update OCR config: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)) from e


@router.get("/ocr-engines", response_model=dict[str, EngineStatusResponse])
async def get_available_engines(
    db: Session = Depends(get_session), current_user: UserDB = Depends(require_user_auth)
):
    """
    Get information about available OCR engines.
    Requires authentication.
    """

    ocr_manager = OCREngineManager(db)

    try:
        return ocr_manager.get_available_engines()

    except Exception as e:
        logger.error(f"❌ Failed to get OCR engines: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)) from e


@router.get("/ocr-engines/{engine}", response_model=EngineStatusResponse)
async def get_engine_status(
    engine: OCREngineEnum,
    db: Session = Depends(get_session),
    current_user: UserDB = Depends(require_user_auth),
):
    """
    Get detailed status of a specific OCR engine.
    Requires authentication.
    """

    ocr_manager = OCREngineManager(db)

    try:
        return ocr_manager.get_engine_status(engine)

    except Exception as e:
        logger.error(f"❌ Failed to get engine status: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)) from e


# ==================== PIPELINE STEPS ENDPOINTS ====================


@router.get("/steps", response_model=list[PipelineStepResponse])
async def get_all_steps(
    db: Session = Depends(get_session), current_user: UserDB = Depends(require_user_auth)
):
    """
    Get all pipeline steps (enabled and disabled).
    Requires authentication.
    """

    manager = ModularPipelineManager(db)

    try:
        return manager.get_all_steps()

    except Exception as e:
        logger.error(f"❌ Failed to get pipeline steps: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)) from e


@router.get("/steps/{step_id}", response_model=PipelineStepResponse)
async def get_step(
    step_id: int,
    db: Session = Depends(get_session),
    current_user: UserDB = Depends(require_user_auth),
):
    """
    Get a single pipeline step by ID.
    Requires authentication.
    """

    manager = ModularPipelineManager(db)

    step = manager.get_step(step_id)
    if not step:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Step {step_id} not found"
        )

    return step


@router.post("/steps", response_model=PipelineStepResponse, status_code=status.HTTP_201_CREATED)
async def create_step(
    step_request: PipelineStepRequest,
    db: Session = Depends(get_session),
    current_user: UserDB = Depends(require_user_auth),
):
    """
    Create a new pipeline step.
    Requires authentication.
    """

    manager = ModularPipelineManager(db)

    try:
        step_data = step_request.dict()
        step_data["modified_by"] = "settings_ui"

        step = manager.create_step(step_data)

        logger.info(f"✅ Created pipeline step: {step.name} (order: {step.order})")
        return step

    except Exception as e:
        logger.error(f"❌ Failed to create pipeline step: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)) from e


@router.put("/steps/{step_id}", response_model=PipelineStepResponse)
async def update_step(
    step_id: int,
    step_request: PipelineStepRequest,
    db: Session = Depends(get_session),
    current_user: UserDB = Depends(require_user_auth),
):
    """
    Update an existing pipeline step.
    Requires authentication.
    """

    manager = ModularPipelineManager(db)

    try:
        step_data = step_request.dict()
        step_data["modified_by"] = "settings_ui"

        step = manager.update_step(step_id, step_data)

        if not step:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Step {step_id} not found"
            )

        logger.info(f"✅ Updated pipeline step: {step.name} (ID: {step_id})")
        return step

    except Exception as e:
        logger.error(f"❌ Failed to update pipeline step: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)) from e


@router.delete("/steps/{step_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_step(
    step_id: int,
    db: Session = Depends(get_session),
    current_user: UserDB = Depends(require_user_auth),
):
    """
    Delete a pipeline step.
    Requires authentication.
    """

    manager = ModularPipelineManager(db)

    success = manager.delete_step(step_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Step {step_id} not found"
        )

    logger.info(f"✅ Deleted pipeline step ID: {step_id}")
    return


@router.post("/steps/reorder")
async def reorder_steps(
    reorder_request: StepReorderRequest,
    db: Session = Depends(get_session),
    current_user: UserDB = Depends(require_user_auth),
):
    """
    Reorder pipeline steps.
    Requires authentication.
    """

    manager = ModularPipelineManager(db)

    try:
        success = manager.reorder_steps(reorder_request.step_ids)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to reorder steps"
            )

        logger.info(f"✅ Reordered pipeline steps: {reorder_request.step_ids}")
        return {"success": True, "message": "Steps reordered successfully"}

    except Exception as e:
        logger.error(f"❌ Failed to reorder steps: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)) from e


@router.get("/steps/universal", response_model=list[PipelineStepResponse])
async def get_universal_steps(
    current_user: UserDB = Depends(require_user_auth),
    step_repository: PipelineStepRepository = Depends(get_pipeline_step_repository),
):
    """
    Get universal pipeline steps (document_class_id = NULL).
    These steps run for all document types.
    Requires authentication.
    """

    try:
        steps = step_repository.get_universal_steps()
        logger.info(f"📋 Retrieved {len(steps)} universal pipeline steps")
        return steps

    except Exception as e:
        logger.error(f"❌ Failed to get universal steps: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)) from e


@router.get("/steps/by-class/{class_id}", response_model=list[PipelineStepResponse])
async def get_steps_by_document_class(
    class_id: int,
    current_user: UserDB = Depends(require_user_auth),
    db: Session = Depends(get_session),
    step_repository: PipelineStepRepository = Depends(get_pipeline_step_repository),
):
    """
    Get pipeline steps for a specific document class.
    Requires authentication.
    """

    # Verify document class exists
    doc_class_manager = DocumentClassManager(db)
    doc_class = doc_class_manager.get_class(class_id)
    if not doc_class:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Document class {class_id} not found"
        )

    try:
        steps = step_repository.get_steps_by_document_class(class_id)
        logger.info(f"📋 Retrieved {len(steps)} steps for document class '{doc_class.class_key}'")
        return steps

    except Exception as e:
        logger.error(f"❌ Failed to get steps for class {class_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)) from e


@router.get("/visualization")
async def get_pipeline_visualization(
    current_user: UserDB = Depends(require_user_auth),
    db: Session = Depends(get_session),
    step_repository: PipelineStepRepository = Depends(get_pipeline_step_repository),
):
    """
    Get complete pipeline structure showing universal steps and class-specific branches.
    Requires authentication.

    Returns:
        {
            "universal_steps": [...],
            "branching_step": {...},
            "branches": {
                "ARZTBRIEF": {
                    "class_info": {...},
                    "steps": [...]
                },
                "BEFUNDBERICHT": {...},
                ...
            }
        }
    """

    try:
        # Get universal steps
        universal_steps = step_repository.get_universal_steps()

        # Find branching step
        branching_step = step_repository.get_branching_step()

        # Get all document classes
        doc_class_manager = DocumentClassManager(db)
        all_classes = doc_class_manager.get_all_classes(enabled_only=True)

        # Build branches
        branches = {}
        for doc_class in all_classes:
            class_steps = step_repository.get_steps_by_document_class(doc_class.id)

            branches[doc_class.class_key] = {
                "class_info": {
                    "id": doc_class.id,
                    "class_key": doc_class.class_key,
                    "display_name": doc_class.display_name,
                    "description": doc_class.description,
                    "icon": doc_class.icon,
                    "is_enabled": doc_class.is_enabled,
                    "is_system_class": doc_class.is_system_class,
                },
                "steps": [PipelineStepResponse.from_orm(step) for step in class_steps],
            }

        result = {
            "universal_steps": [PipelineStepResponse.from_orm(step) for step in universal_steps],
            "branching_step": PipelineStepResponse.from_orm(branching_step)
            if branching_step
            else None,
            "branches": branches,
        }

        logger.info(
            f"📊 Pipeline visualization: {len(universal_steps)} universal steps, {len(branches)} branches"
        )
        return result

    except Exception as e:
        logger.error(f"❌ Failed to get pipeline visualization: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)) from e


# ==================== AVAILABLE MODELS ENDPOINTS ====================


@router.get("/models", response_model=list[ModelResponse])
async def get_available_models(
    enabled_only: bool = False,
    db: Session = Depends(get_session),
    current_user: UserDB = Depends(require_user_auth),
):
    """
    Get all available AI models.
    Requires authentication.

    Args:
        enabled_only: If True, only return enabled models
    """

    manager = ModularPipelineManager(db)

    try:
        return manager.get_all_models(enabled_only=enabled_only)

    except Exception as e:
        logger.error(f"❌ Failed to get available models: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)) from e


@router.get("/models/{model_id}", response_model=ModelResponse)
async def get_model(
    model_id: int,
    db: Session = Depends(get_session),
    current_user: UserDB = Depends(require_user_auth),
):
    """
    Get a single model by ID.
    Requires authentication.
    """

    manager = ModularPipelineManager(db)

    model = manager.get_model(model_id)
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Model {model_id} not found"
        )

    return model


# ==================== DOCUMENT CLASS ENDPOINTS ====================


@router.get("/document-classes", response_model=list[DocumentClassResponse])
async def get_all_document_classes(
    enabled_only: bool = False,
    db: Session = Depends(get_session),
    current_user: UserDB = Depends(require_user_auth),
):
    """
    Get all document classes.
    Requires authentication.

    Args:
        enabled_only: If True, only return enabled classes
    """

    doc_class_manager = DocumentClassManager(db)

    try:
        return doc_class_manager.get_all_classes(enabled_only=enabled_only)

    except Exception as e:
        logger.error(f"❌ Failed to get document classes: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)) from e


@router.get("/document-classes/{class_id}", response_model=DocumentClassResponse)
async def get_document_class(
    class_id: int,
    db: Session = Depends(get_session),
    current_user: UserDB = Depends(require_user_auth),
):
    """
    Get a single document class by ID.
    Requires authentication.
    """

    doc_class_manager = DocumentClassManager(db)

    doc_class = doc_class_manager.get_class(class_id)
    if not doc_class:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Document class {class_id} not found"
        )

    return doc_class


@router.post(
    "/document-classes", response_model=DocumentClassResponse, status_code=status.HTTP_201_CREATED
)
async def create_document_class(
    class_request: DocumentClassRequest,
    db: Session = Depends(get_session),
    current_user: UserDB = Depends(require_user_auth),
):
    """
    Create a new document class.
    Requires authentication.
    """

    doc_class_manager = DocumentClassManager(db)

    try:
        class_data = class_request.dict()
        class_data["created_by"] = "settings_ui"
        class_data["is_system_class"] = False  # User-created classes are never system classes

        doc_class = doc_class_manager.create_class(class_data)

        if not doc_class:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create document class",
            )

        logger.info(f"✅ Created document class: {doc_class.class_key}")
        return doc_class

    except ValueError as e:
        # Validation errors (duplicate key, etc.)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    except Exception as e:
        logger.error(f"❌ Failed to create document class: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)) from e


@router.put("/document-classes/{class_id}", response_model=DocumentClassResponse)
async def update_document_class(
    class_id: int,
    class_request: DocumentClassRequest,
    db: Session = Depends(get_session),
    current_user: UserDB = Depends(require_user_auth),
):
    """
    Update an existing document class.
    Requires authentication.
    """

    doc_class_manager = DocumentClassManager(db)

    try:
        class_data = class_request.dict()

        doc_class = doc_class_manager.update_class(class_id, class_data)

        if not doc_class:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Document class {class_id} not found"
            )

        logger.info(f"✅ Updated document class: {doc_class.class_key}")
        return doc_class

    except ValueError as e:
        # Validation errors
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    except Exception as e:
        logger.error(f"❌ Failed to update document class: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)) from e


@router.delete("/document-classes/{class_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document_class(
    class_id: int,
    db: Session = Depends(get_session),
    current_user: UserDB = Depends(require_user_auth),
):
    """
    Delete a document class.
    Cannot delete system classes or classes with associated pipeline steps.
    Requires authentication.
    """

    doc_class_manager = DocumentClassManager(db)

    try:
        success = doc_class_manager.delete_class(class_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Document class {class_id} not found"
            )

        logger.info(f"✅ Deleted document class ID: {class_id}")
        return

    except ValueError as e:
        # Cannot delete (system class or has steps)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    except Exception as e:
        logger.error(f"❌ Failed to delete document class: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)) from e


@router.get("/document-classes/statistics/summary")
async def get_document_class_statistics(
    db: Session = Depends(get_session), current_user: UserDB = Depends(require_user_auth)
):
    """
    Get statistics about document classes.
    Requires authentication.
    """

    doc_class_manager = DocumentClassManager(db)

    try:
        return doc_class_manager.get_class_statistics()

    except Exception as e:
        logger.error(f"❌ Failed to get document class statistics: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)) from e
