"""
Modular Pipeline Executor Service

Worker-ready service for executing user-configured pipeline steps.
Designed to be stateless and compatible with Redis queue workers.
"""

import logging
import time
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.database.modular_pipeline_models import (
    DynamicPipelineStepDB,
    AvailableModelDB,
    OCRConfigurationDB,
    PipelineJobDB,
    PipelineStepExecutionDB,
    StepExecutionStatus
)
from app.services.ovh_client import OVHClient

logger = logging.getLogger(__name__)


class ModularPipelineExecutor:
    """
    Executes user-configured pipeline steps dynamically.

    Design Principles:
    - Stateless: All state passed as parameters or loaded from DB
    - Worker-Ready: Can be called from Redis queue worker
    - Database-Driven: All configuration from database
    - Retry-Aware: Handles retries per step configuration
    """

    def __init__(self, session: Session):
        """
        Initialize executor with database session.

        Args:
            session: SQLAlchemy session for database access
        """
        self.session = session
        self.ovh_client = OVHClient()

    # ==================== CONFIGURATION LOADING ====================

    def load_pipeline_steps(self) -> List[DynamicPipelineStepDB]:
        """
        Load all enabled pipeline steps from database, ordered by execution order.

        Returns:
            List of pipeline steps ordered by 'order' field
        """
        try:
            steps = self.session.query(DynamicPipelineStepDB).filter_by(
                enabled=True
            ).order_by(DynamicPipelineStepDB.order).all()

            logger.info(f"📋 Loaded {len(steps)} enabled pipeline steps")
            return steps
        except Exception as e:
            logger.error(f"❌ Failed to load pipeline steps: {e}")
            return []

    def load_ocr_configuration(self) -> Optional[OCRConfigurationDB]:
        """
        Load OCR configuration from database.

        Returns:
            OCR configuration or None if not found
        """
        try:
            config = self.session.query(OCRConfigurationDB).first()
            if config:
                logger.info(f"🔍 Loaded OCR configuration: {config.selected_engine}")
            return config
        except Exception as e:
            logger.error(f"❌ Failed to load OCR configuration: {e}")
            return None

    def get_model_info(self, model_id: int) -> Optional[AvailableModelDB]:
        """
        Get model information from database.

        Args:
            model_id: Database ID of the model

        Returns:
            Model information or None if not found
        """
        try:
            model = self.session.query(AvailableModelDB).filter_by(
                id=model_id,
                is_enabled=True
            ).first()
            return model
        except Exception as e:
            logger.error(f"❌ Failed to load model info for ID {model_id}: {e}")
            return None

    # ==================== STEP EXECUTION ====================

    async def execute_step(
        self,
        step: DynamicPipelineStepDB,
        input_text: str,
        context: Dict[str, Any] = None
    ) -> Tuple[bool, str, Optional[str]]:
        """
        Execute a single pipeline step.

        Args:
            step: Pipeline step configuration
            input_text: Input text for this step
            context: Additional context variables (e.g., target_language)

        Returns:
            Tuple of (success: bool, output_text: str, error_message: Optional[str])
        """
        context = context or {}

        # Get model information
        model = self.get_model_info(step.selected_model_id)
        if not model:
            error = f"Model ID {step.selected_model_id} not found or disabled"
            logger.error(f"❌ {error}")
            return False, "", error

        # Prepare prompt with variable substitution
        try:
            prompt = step.prompt_template.format(
                input_text=input_text,
                **context  # e.g., target_language
            )
        except KeyError as e:
            error = f"Missing required variable in prompt template: {e}"
            logger.error(f"❌ {error}")
            return False, "", error

        # Execute with retries
        max_retries = step.max_retries if step.retry_on_failure else 1
        last_error = None

        for attempt in range(max_retries):
            try:
                logger.info(f"🔄 Executing step '{step.name}' (attempt {attempt + 1}/{max_retries})")
                logger.debug(f"   Model: {model.name}")
                logger.debug(f"   Temperature: {step.temperature}")
                logger.debug(f"   Max Tokens: {step.max_tokens or model.max_tokens}")

                # Call AI model
                start_time = time.time()

                result = await self.ovh_client.process_medical_text_with_prompt(
                    full_prompt=prompt,
                    temperature=step.temperature or 0.7,
                    max_tokens=step.max_tokens or model.max_tokens or 4096,
                    use_fast_model=(model.name == "Mistral-Nemo-Instruct-2407")
                )

                execution_time = time.time() - start_time

                # Check for API errors
                if result.startswith("Error"):
                    last_error = result
                    logger.warning(f"⚠️ API error on attempt {attempt + 1}: {result}")
                    continue

                # Success!
                logger.info(f"✅ Step '{step.name}' completed in {execution_time:.2f}s")
                return True, result, None

            except Exception as e:
                last_error = str(e)
                logger.error(f"❌ Step '{step.name}' failed on attempt {attempt + 1}: {e}")

                if attempt < max_retries - 1:
                    logger.info(f"🔄 Retrying step '{step.name}'...")
                    time.sleep(1 * (attempt + 1))  # Exponential backoff

        # All retries failed
        return False, "", last_error or "Unknown error"

    # ==================== PIPELINE EXECUTION ====================

    async def execute_pipeline(
        self,
        processing_id: str,
        input_text: str,
        context: Dict[str, Any] = None
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Execute complete pipeline on input text.

        Args:
            processing_id: Unique ID for this processing request
            input_text: Initial input text (after OCR)
            context: Additional context (e.g., target_language, document_type)

        Returns:
            Tuple of (success: bool, final_output: str, execution_metadata: Dict)
        """
        context = context or {}

        logger.info(f"🚀 Starting modular pipeline execution: {processing_id[:8]}")

        # Create pipeline job record
        job_id = str(uuid.uuid4())
        pipeline_config = self._serialize_pipeline_config()
        ocr_config = self._serialize_ocr_config()

        job = PipelineJobDB(
            job_id=job_id,
            processing_id=processing_id,
            status=StepExecutionStatus.RUNNING,
            pipeline_config=pipeline_config,
            ocr_config=ocr_config,
            started_at=datetime.now()
        )
        self.session.add(job)
        self.session.commit()

        # Load pipeline steps
        steps = self.load_pipeline_steps()
        if not steps:
            error = "No enabled pipeline steps found"
            logger.error(f"❌ {error}")
            self._mark_job_failed(job, error)
            return False, "", {"error": error}

        # Execute steps sequentially
        current_output = input_text
        execution_metadata = {
            "job_id": job_id,
            "total_steps": len(steps),
            "steps_executed": [],
            "total_time": 0
        }

        pipeline_start_time = time.time()

        for idx, step in enumerate(steps):
            step_start_time = time.time()

            # Update job progress
            progress_percent = int((idx / len(steps)) * 100)
            job.progress_percent = progress_percent
            job.current_step_id = step.id
            self.session.commit()

            # Execute step
            success, output, error = await self.execute_step(
                step=step,
                input_text=current_output,
                context=context
            )

            step_execution_time = time.time() - step_start_time

            # Log step execution
            step_execution = PipelineStepExecutionDB(
                job_id=job_id,
                step_id=step.id,
                step_name=step.name,
                step_order=step.order,
                status=StepExecutionStatus.COMPLETED if success else StepExecutionStatus.FAILED,
                input_text=current_output[:1000],  # Truncate for storage
                output_text=output[:1000] if success else None,
                model_used=self.get_model_info(step.selected_model_id).name if success else None,
                prompt_used=step.prompt_template[:500],
                started_at=datetime.fromtimestamp(step_start_time),
                completed_at=datetime.now(),
                execution_time_seconds=step_execution_time,
                error_message=error
            )
            self.session.add(step_execution)
            self.session.commit()

            # Store metadata
            execution_metadata["steps_executed"].append({
                "step_name": step.name,
                "step_order": step.order,
                "success": success,
                "execution_time": step_execution_time,
                "error": error
            })

            if not success:
                logger.error(f"❌ Pipeline failed at step '{step.name}': {error}")
                self._mark_job_failed(job, error, step.id)
                execution_metadata["failed_at_step"] = step.name
                execution_metadata["total_time"] = time.time() - pipeline_start_time
                return False, current_output, execution_metadata

            # Update current output for next step
            if step.input_from_previous_step:
                current_output = output

        # Pipeline completed successfully
        total_time = time.time() - pipeline_start_time
        execution_metadata["total_time"] = total_time

        job.status = StepExecutionStatus.COMPLETED
        job.completed_at = datetime.now()
        job.progress_percent = 100
        job.result_data = {"output": current_output[:1000]}
        job.total_execution_time_seconds = total_time
        self.session.commit()

        logger.info(f"✅ Pipeline completed successfully in {total_time:.2f}s")
        return True, current_output, execution_metadata

    # ==================== HELPER METHODS ====================

    def _serialize_pipeline_config(self) -> Dict[str, Any]:
        """Serialize current pipeline configuration for job record."""
        steps = self.load_pipeline_steps()
        return {
            "steps": [
                {
                    "id": step.id,
                    "name": step.name,
                    "order": step.order,
                    "model_id": step.selected_model_id
                }
                for step in steps
            ]
        }

    def _serialize_ocr_config(self) -> Dict[str, Any]:
        """Serialize current OCR configuration for job record."""
        config = self.load_ocr_configuration()
        if not config:
            return {}

        return {
            "selected_engine": config.selected_engine,
            "tesseract_config": config.tesseract_config,
            "paddleocr_config": config.paddleocr_config,
            "vision_llm_config": config.vision_llm_config,
            "hybrid_config": config.hybrid_config
        }

    def _mark_job_failed(
        self,
        job: PipelineJobDB,
        error_message: str,
        failed_step_id: Optional[int] = None
    ):
        """Mark job as failed with error details."""
        job.status = StepExecutionStatus.FAILED
        job.failed_at = datetime.now()
        job.error_message = error_message
        job.error_step_id = failed_step_id
        self.session.commit()


class ModularPipelineManager:
    """
    High-level manager for modular pipeline CRUD operations.
    Used by API endpoints for pipeline configuration.
    """

    def __init__(self, session: Session):
        self.session = session

    # ==================== PIPELINE STEP CRUD ====================

    def get_all_steps(self) -> List[DynamicPipelineStepDB]:
        """Get all pipeline steps (enabled and disabled)."""
        return self.session.query(DynamicPipelineStepDB).order_by(
            DynamicPipelineStepDB.order
        ).all()

    def get_step(self, step_id: int) -> Optional[DynamicPipelineStepDB]:
        """Get a single pipeline step by ID."""
        return self.session.query(DynamicPipelineStepDB).filter_by(id=step_id).first()

    def create_step(self, step_data: Dict[str, Any]) -> DynamicPipelineStepDB:
        """Create a new pipeline step."""
        step = DynamicPipelineStepDB(**step_data)
        self.session.add(step)
        self.session.commit()
        self.session.refresh(step)
        return step

    def update_step(self, step_id: int, step_data: Dict[str, Any]) -> Optional[DynamicPipelineStepDB]:
        """Update an existing pipeline step."""
        step = self.get_step(step_id)
        if not step:
            return None

        for key, value in step_data.items():
            if hasattr(step, key):
                setattr(step, key, value)

        step.last_modified = datetime.now()
        self.session.commit()
        self.session.refresh(step)
        return step

    def delete_step(self, step_id: int) -> bool:
        """Delete a pipeline step."""
        step = self.get_step(step_id)
        if not step:
            return False

        self.session.delete(step)
        self.session.commit()
        return True

    def reorder_steps(self, step_order: List[int]) -> bool:
        """
        Reorder pipeline steps.

        Args:
            step_order: List of step IDs in desired order

        Returns:
            True if successful, False otherwise
        """
        try:
            for new_order, step_id in enumerate(step_order, start=1):
                step = self.get_step(step_id)
                if step:
                    step.order = new_order
                    step.last_modified = datetime.now()

            self.session.commit()
            return True
        except Exception as e:
            logger.error(f"❌ Failed to reorder steps: {e}")
            self.session.rollback()
            return False

    # ==================== OCR CONFIGURATION ====================

    def get_ocr_config(self) -> Optional[OCRConfigurationDB]:
        """Get current OCR configuration."""
        return self.session.query(OCRConfigurationDB).first()

    def update_ocr_config(self, config_data: Dict[str, Any]) -> Optional[OCRConfigurationDB]:
        """Update OCR configuration."""
        config = self.get_ocr_config()
        if not config:
            config = OCRConfigurationDB(**config_data)
            self.session.add(config)
        else:
            for key, value in config_data.items():
                if hasattr(config, key):
                    setattr(config, key, value)
            config.last_modified = datetime.now()

        self.session.commit()
        self.session.refresh(config)
        return config

    # ==================== AVAILABLE MODELS ====================

    def get_all_models(self, enabled_only: bool = False) -> List[AvailableModelDB]:
        """Get all available AI models."""
        query = self.session.query(AvailableModelDB)
        if enabled_only:
            query = query.filter_by(is_enabled=True)
        return query.all()

    def get_model(self, model_id: int) -> Optional[AvailableModelDB]:
        """Get a single model by ID."""
        return self.session.query(AvailableModelDB).filter_by(id=model_id).first()
