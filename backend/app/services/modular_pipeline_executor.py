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
    StepExecutionStatus,
    DocumentClassDB
)
from app.services.ovh_client import OVHClient
from app.services.document_class_manager import DocumentClassManager

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
        self.doc_class_manager = DocumentClassManager(session)

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

    def load_universal_steps(self) -> List[DynamicPipelineStepDB]:
        """
        Load universal pipeline steps (document_class_id = NULL).
        These steps run for all documents regardless of classification.

        Returns:
            List of universal pipeline steps ordered by execution order
        """
        try:
            steps = self.session.query(DynamicPipelineStepDB).filter_by(
                enabled=True,
                document_class_id=None
            ).order_by(DynamicPipelineStepDB.order).all()

            logger.info(f"📋 Loaded {len(steps)} universal pipeline steps")
            return steps
        except Exception as e:
            logger.error(f"❌ Failed to load universal pipeline steps: {e}")
            return []

    def load_steps_by_document_class(self, document_class_id: int) -> List[DynamicPipelineStepDB]:
        """
        Load pipeline steps specific to a document class.

        Args:
            document_class_id: ID of the document class

        Returns:
            List of document-specific pipeline steps ordered by execution order
        """
        try:
            steps = self.session.query(DynamicPipelineStepDB).filter_by(
                enabled=True,
                document_class_id=document_class_id
            ).order_by(DynamicPipelineStepDB.order).all()

            logger.info(f"📋 Loaded {len(steps)} steps for document class ID {document_class_id}")
            return steps
        except Exception as e:
            logger.error(f"❌ Failed to load steps for document class {document_class_id}: {e}")
            return []

    def find_branching_step(self, steps: List[DynamicPipelineStepDB]) -> Optional[DynamicPipelineStepDB]:
        """
        Find the branching/classification step in the pipeline.

        Args:
            steps: List of pipeline steps to search

        Returns:
            The branching step or None if not found
        """
        for step in steps:
            if step.is_branching_step:
                logger.info(f"🔀 Found branching step: {step.name} (order: {step.order})")
                return step

        logger.warning("⚠️ No branching step found in pipeline")
        return None

    def extract_branch_value(self, output_text: str, branching_field: str = "document_type") -> Optional[str]:
        """
        Extract the branch value from step output.

        For classification steps, this extracts the document class key (e.g., "ARZTBRIEF")
        from the AI model's output.

        Args:
            output_text: Output text from the branching step
            branching_field: Field name to extract (currently only supports "document_type")

        Returns:
            Extracted branch value (document class key) or None if extraction failed
        """
        if not output_text:
            logger.error("❌ Cannot extract branch value from empty output")
            return None

        # Clean and uppercase the output
        branch_value = output_text.strip().upper()

        # Remove common prefixes/suffixes
        for prefix in ["DOCUMENT_TYPE:", "CLASS:", "CLASSIFICATION:"]:
            if branch_value.startswith(prefix):
                branch_value = branch_value[len(prefix):].strip()

        # Extract first word (should be the class key)
        branch_value = branch_value.split()[0] if branch_value.split() else branch_value

        # Validate it's a known document class
        doc_class = self.doc_class_manager.get_class_by_key(branch_value)
        if doc_class:
            logger.info(f"✅ Extracted branch value: {branch_value} → {doc_class.display_name}")
            return branch_value
        else:
            logger.warning(f"⚠️ Unknown document class: {branch_value}")
            # Return it anyway - might be a new class or fallback behavior needed
            return branch_value

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

        logger.info(f"🚀 Starting modular pipeline execution with branching support: {processing_id[:8]}")

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

        # Load universal pipeline steps (document_class_id = NULL)
        universal_steps = self.load_universal_steps()
        if not universal_steps:
            logger.warning("⚠️ No universal pipeline steps found, loading all steps as fallback")
            universal_steps = self.load_pipeline_steps()

        # Find branching step
        branching_step = self.find_branching_step(universal_steps)

        # Initialize execution state
        current_output = input_text
        execution_metadata = {
            "job_id": job_id,
            "total_steps": 0,
            "universal_steps": len(universal_steps),
            "steps_executed": [],
            "total_time": 0,
            "branching_occurred": False,
            "document_class": None
        }

        pipeline_start_time = time.time()
        all_steps = []  # Track all steps for progress calculation

        # ==================== PHASE 1: UNIVERSAL STEPS ====================
        logger.info(f"📋 Phase 1: Executing {len(universal_steps)} universal steps")

        branch_value = None
        document_class_specific_steps = []

        for idx, step in enumerate(universal_steps):
            step_start_time = time.time()
            all_steps.append(step)

            # Update job progress
            total_steps_so_far = len(all_steps)
            progress_percent = int((idx / max(len(universal_steps), 1)) * 50)  # First 50% is universal steps
            job.progress_percent = progress_percent
            job.current_step_id = step.id
            self.session.commit()

            logger.info(f"▶️  Step {idx + 1}/{len(universal_steps)}: {step.name}")

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
                input_text=current_output[:1000],
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
                "error": error,
                "is_branching_step": step.is_branching_step
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

            # Check if this is the branching step
            if step.is_branching_step and branching_step:
                logger.info(f"🔀 Branching step detected: {step.name}")

                # Extract branch value (document class)
                branch_value = self.extract_branch_value(
                    output,
                    step.branching_field or "document_type"
                )

                if branch_value:
                    # Get document class
                    doc_class = self.doc_class_manager.get_class_by_key(branch_value)

                    if doc_class:
                        logger.info(f"🎯 Branch selected: {doc_class.display_name} (ID: {doc_class.id})")

                        # Load document class-specific steps
                        document_class_specific_steps = self.load_steps_by_document_class(doc_class.id)

                        execution_metadata["branching_occurred"] = True
                        execution_metadata["document_class"] = {
                            "class_key": doc_class.class_key,
                            "display_name": doc_class.display_name,
                            "class_id": doc_class.id
                        }
                        execution_metadata["class_specific_steps"] = len(document_class_specific_steps)

                        # Store document_type in context for subsequent steps
                        context["document_type"] = doc_class.class_key

                        break  # Exit universal steps loop, continue with class-specific steps
                    else:
                        logger.warning(f"⚠️ Document class '{branch_value}' not found, continuing without branching")
                else:
                    logger.warning(f"⚠️ Failed to extract branch value, continuing without branching")

        # ==================== PHASE 2: CLASS-SPECIFIC STEPS ====================
        if document_class_specific_steps:
            logger.info(f"📋 Phase 2: Executing {len(document_class_specific_steps)} class-specific steps")

            for idx, step in enumerate(document_class_specific_steps):
                step_start_time = time.time()
                all_steps.append(step)

                # Update job progress
                progress_percent = 50 + int((idx / max(len(document_class_specific_steps), 1)) * 50)
                job.progress_percent = progress_percent
                job.current_step_id = step.id
                self.session.commit()

                logger.info(f"▶️  Step {idx + 1}/{len(document_class_specific_steps)}: {step.name} [{execution_metadata['document_class']['class_key']}]")

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
                    input_text=current_output[:1000],
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
                    "error": error,
                    "document_class_id": step.document_class_id
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
        execution_metadata["total_steps"] = len(all_steps)

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
