"""
Modular Pipeline Executor Service

Worker-ready service for executing user-configured pipeline steps.
Designed to be stateless and compatible with Redis queue workers.
"""

from datetime import datetime
import logging
import time
from typing import Any

from sqlalchemy.orm import Session

from app.database.modular_pipeline_models import (
    AvailableModelDB,
    DynamicPipelineStepDB,
    ModelProvider,
    OCRConfigurationDB,
    StepExecutionStatus,
)
from app.repositories.available_model_repository import AvailableModelRepository
from app.repositories.ocr_configuration_repository import OCRConfigurationRepository
from app.repositories.pipeline_job_repository import PipelineJobRepository
from app.repositories.pipeline_step_execution_repository import PipelineStepExecutionRepository
from app.repositories.pipeline_step_repository import PipelineStepRepository
from app.services.ai_cost_tracker import AICostTracker
from app.services.ai_logging_service import AILoggingService
from app.services.document_class_manager import DocumentClassManager
from app.services.mistral_client import MistralClient
from app.services.ovh_client import OVHClient
from app.services.pipeline_progress_tracker import PipelineProgressTracker
from app.services.prompt_guard import (
    detect_injection,
    log_injection_detection,
    sanitize_for_prompt,
    validate_step_output,
)

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

    def __init__(
        self,
        session: Session,
        job_repository: PipelineJobRepository | None = None,
        step_repository: PipelineStepRepository | None = None,
        step_execution_repository: PipelineStepExecutionRepository | None = None,
        ocr_config_repository: OCRConfigurationRepository | None = None,
        model_repository: AvailableModelRepository | None = None,
    ):
        """
        Initialize executor with database session and repositories.

        Args:
            session: SQLAlchemy session (kept for backward compatibility)
            job_repository: Pipeline job repository (injected for clean architecture)
            step_repository: Pipeline step repository (injected for clean architecture)
            step_execution_repository: Pipeline step execution repository (injected for encryption)
            ocr_config_repository: OCR configuration repository (injected for clean architecture)
            model_repository: Available model repository (injected for clean architecture)
        """
        self.session = session
        self.job_repository = job_repository or PipelineJobRepository(session)
        self.step_repository = step_repository or PipelineStepRepository(session)
        self.step_execution_repository = (
            step_execution_repository or PipelineStepExecutionRepository(session)
        )
        self.ocr_config_repository = ocr_config_repository or OCRConfigurationRepository(session)
        self.model_repository = model_repository or AvailableModelRepository(session)
        self.ovh_client = OVHClient()
        self.doc_class_manager = DocumentClassManager(session)
        self.cost_tracker = AICostTracker(session)
        self.ai_logger = AILoggingService(session)
        self.progress_tracker = PipelineProgressTracker()
        logger.info("💰 Cost tracker initialized for pipeline executor")
        logger.info("📊 AI interaction logger initialized")

    # ==================== CONFIGURATION LOADING ====================

    def load_pipeline_steps(self) -> list[DynamicPipelineStepDB]:
        """
        Load all enabled pipeline steps from database using repository pattern.

        Returns:
            List of pipeline steps ordered by 'order' field
        """
        try:
            steps = self.step_repository.get_enabled_steps()

            logger.info(f"📋 Loaded {len(steps)} enabled pipeline steps")
            return steps
        except Exception as e:
            logger.error(f"❌ Failed to load pipeline steps: {e}")
            return []

    def load_universal_steps(self) -> list[DynamicPipelineStepDB]:
        """
        Load pre-branching universal pipeline steps (document_class_id = NULL, post_branching = FALSE).
        These steps run for all documents BEFORE document-specific processing.
        Only ENABLED steps are returned (filtered by repository).

        Returns:
            List of pre-branching universal pipeline steps ordered by execution order
        """
        try:
            # Get universal steps (already filtered for enabled by repository)
            universal_steps = self.step_repository.get_universal_steps()

            # DEBUG: Log what we got from repository
            logger.info(
                f"🔍 DEBUG: Repository returned {len(universal_steps)} universal steps (document_class_id = NULL)"
            )
            for step in universal_steps:
                logger.info(
                    f"   - {step.name} (order={step.order}, post_branching={step.post_branching}, enabled={step.enabled})"
                )

            # Filter for pre-branching only (post_branching = False)
            steps = [s for s in universal_steps if not s.post_branching]

            logger.info(
                f"📋 Loaded {len(steps)} pre-branching universal pipeline steps (after filtering post_branching=False)"
            )
            if len(steps) == 0 and len(universal_steps) > 0:
                logger.warning(
                    f"⚠️ ISSUE DETECTED: Repository returned {len(universal_steps)} universal steps but ALL have post_branching=True!"
                )
                logger.warning(
                    "   Expected at least some steps with post_branching=False for pre-branching phase"
                )

            return steps
        except Exception as e:
            logger.error(f"❌ Failed to load universal pipeline steps: {e}")
            return []

    def load_post_branching_steps(self) -> list[DynamicPipelineStepDB]:
        """
        Load post-branching universal pipeline steps (document_class_id = NULL, post_branching = TRUE).
        These steps run for all documents AFTER document-specific processing.
        Only ENABLED steps are returned (filtered by repository).

        Returns:
            List of post-branching universal pipeline steps ordered by execution order
        """
        try:
            # Get post-branching steps (already filtered for enabled by repository)
            steps = self.step_repository.get_post_branching_steps()

            logger.info(f"📋 Loaded {len(steps)} post-branching universal pipeline steps")
            return steps
        except Exception as e:
            logger.error(f"❌ Failed to load post-branching pipeline steps: {e}")
            return []

    def load_steps_by_document_class(self, document_class_id: int) -> list[DynamicPipelineStepDB]:
        """
        Load pipeline steps specific to a document class using repository pattern.
        Only ENABLED steps are returned (filtered by repository).

        Args:
            document_class_id: ID of the document class

        Returns:
            List of document-specific pipeline steps ordered by execution order
        """
        try:
            # Get document class steps (already filtered for enabled by repository)
            steps = self.step_repository.get_steps_by_document_class(document_class_id)

            logger.info(
                f"📋 Loaded {len(steps)} enabled steps for document class ID {document_class_id}"
            )
            return steps
        except Exception as e:
            logger.error(f"❌ Failed to load steps for document class {document_class_id}: {e}")
            return []

    def find_branching_step(
        self, steps: list[DynamicPipelineStepDB]
    ) -> DynamicPipelineStepDB | None:
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

    def check_stop_condition(
        self, step: DynamicPipelineStepDB, output_text: str
    ) -> dict[str, Any] | None:
        """
        Check if step output matches termination condition.

        **Matching Strategy:**
        - Extracts the FIRST WORD from step output (case-insensitive)
        - Example: "NICHT_MEDIZINISCH - Details here" → matches "NICHT_MEDIZINISCH"
        - Example: "Der Text ist NICHT_MEDIZINISCH" → does NOT match (first word is "DER")

        **Best Practice:**
        - Configure your prompt to return the decision value as the FIRST word
        - Example prompt: "Antworte NUR mit: MEDIZINISCH oder NICHT_MEDIZINISCH"

        Args:
            step: Pipeline step configuration
            output_text: Output from the step

        Returns:
            Dictionary with termination info if condition matches, None otherwise:
            {
                "should_stop": True,
                "termination_reason": "Non-medical content detected",
                "termination_message": "Das hochgeladene Dokument enthält keinen medizinischen Inhalt.",
                "matched_value": "NICHT_MEDIZINISCH",
                "step_name": "Medical Content Validation",
                "step_order": 1
            }
        """
        if not step.stop_conditions:
            return None

        # Clean and uppercase the output for matching
        clean_output = output_text.strip().upper()

        # Extract first word (decision value)
        # IMPORTANT: Only matches if stop value is the FIRST word in output
        decision_value = clean_output.split()[0] if clean_output.split() else clean_output

        # Get stop values from configuration
        stop_values = step.stop_conditions.get("stop_on_values", [])
        if not stop_values:
            return None

        # Check if output matches any stop value
        for stop_value in stop_values:
            if decision_value == stop_value.upper():
                logger.warning(
                    f"🛑 Stop condition matched for step '{step.name}': {decision_value}"
                )
                return {
                    "should_stop": True,
                    "termination_reason": step.stop_conditions.get(
                        "termination_reason", "Processing stopped"
                    ),
                    "termination_message": step.stop_conditions.get(
                        "termination_message", "Processing was terminated."
                    ),
                    "matched_value": decision_value,
                    "step_name": step.name,
                    "step_order": step.order,
                }

        return None

    def _log_step_execution(
        self,
        job_id: str,
        step: DynamicPipelineStepDB,
        status: StepExecutionStatus,
        input_text: str,
        output_text: str | None,
        step_start_time: float,
        error: str | None = None,
        metadata: dict | None = None,
    ) -> None:
        """
        Centralized step execution logging.

        Uses encrypted repository to ensure input_text and output_text are encrypted.

        Args:
            job_id: Pipeline job ID (UUID string)
            step: Pipeline step configuration
            status: Execution status (COMPLETED, FAILED, SKIPPED, TERMINATED)
            input_text: Input text for the step (will be encrypted)
            output_text: Output text from the step (will be encrypted, None if failed)
            step_start_time: Step start timestamp
            error: Error message if step failed
            metadata: Additional metadata to store
        """
        # Use repository to create step execution (ensures encryption of input_text/output_text)
        # IMPORTANT: Store FULL text (no truncation) - this is the primary source for user-facing results
        self.step_execution_repository.create(
            job_id=job_id,
            step_id=step.id,
            step_name=step.name,
            step_order=step.order,
            status=status,
            input_text=input_text,  # FULL text (was truncated to 1000 chars before)
            output_text=output_text,  # FULL text (was truncated to 1000 chars before)
            model_used=self.get_model_info(step.selected_model_id).name if output_text else None,
            prompt_used=step.prompt_template[:500]
            if step.prompt_template
            else None,  # Metadata can be truncated
            started_at=datetime.fromtimestamp(step_start_time),
            completed_at=datetime.now(),
            execution_time_seconds=time.time() - step_start_time,
            error_message=error,
            step_metadata=metadata,
        )

    def _handle_stop_condition(
        self,
        step: DynamicPipelineStepDB,
        output: str,
        current_output: str,
        job_id: int,
        step_start_time: float,
        step_execution_time: float,
        pipeline_start_time: float,
        execution_metadata: dict,
        success: bool = True,
    ) -> tuple[bool, str, dict]:
        """
        Check and handle stop conditions for a step.

        Args:
            step: Pipeline step configuration
            output: Output from the step
            current_output: Current pipeline output
            job_id: Pipeline job ID
            step_start_time: Step start timestamp
            step_execution_time: Step execution time
            pipeline_start_time: Pipeline start timestamp
            execution_metadata: Execution metadata dictionary
            success: Whether step executed successfully

        Returns:
            (should_terminate, current_output, execution_metadata)
            should_terminate=True means pipeline should stop immediately
        """
        if not success:
            return False, current_output, execution_metadata

        stop_info = self.check_stop_condition(step, output)
        if not stop_info or not stop_info.get("should_stop"):
            return False, current_output, execution_metadata

        logger.warning(f"🛑 Pipeline termination triggered: {stop_info['termination_reason']}")

        # Log this step as TERMINATED
        self._log_step_execution(
            job_id=job_id,
            step=step,
            status=StepExecutionStatus.TERMINATED,
            input_text=current_output,
            output_text=output,
            step_start_time=step_start_time,
            error=None,
            metadata={"termination_info": stop_info, "is_termination_step": True},
        )

        # Add to execution metadata
        execution_metadata["steps_executed"].append(
            {
                "step_name": step.name,
                "step_order": step.order,
                "success": True,
                "execution_time": step_execution_time,
                "error": None,
                "terminated": True,
            }
        )

        # Return early with termination info
        execution_metadata["terminated"] = True
        execution_metadata["termination_step"] = step.name
        execution_metadata["termination_reason"] = stop_info["termination_reason"]
        execution_metadata["termination_message"] = stop_info["termination_message"]
        execution_metadata["matched_value"] = stop_info["matched_value"]
        execution_metadata["total_time"] = time.time() - pipeline_start_time

        logger.info(
            f"🛑 Pipeline terminated at step '{step.name}': {stop_info['termination_reason']}"
        )
        return True, current_output, execution_metadata

    def extract_branch_value(
        self, output_text: str, branching_field: str = "document_type"
    ) -> dict[str, Any] | None:
        """
        Extract the branch value from step output with DYNAMIC BRANCHING SUPPORT.

        Supports multiple branching types:
        - document_type: Routes to document class-specific pipeline steps
        - Any other field: Generic branching with metadata storage (boolean, enum, etc.)

        Args:
            output_text: Output text from the branching step
            branching_field: Field name to extract (e.g., "document_type", "medical_validation", "quality_level")

        Returns:
            Dictionary with branching metadata:
            {
                "field": "medical_validation",
                "value": "MEDIZINISCH",
                "type": "boolean" | "document_class" | "enum" | "generic",
                "target_id": 3,  # For document_class type only
                "target_key": "ARZTBRIEF",  # For document_class type only
                "target_display_name": "Arztbrief"  # For document_class type only
            }
            Returns None if extraction fails
        """
        if not output_text:
            logger.error("❌ Cannot extract branch value from empty output")
            return None

        # Clean and uppercase the output
        cleaned_output = output_text.strip().upper()

        # Remove common prefixes/suffixes
        for prefix in [
            "DOCUMENT_TYPE:",
            "CLASS:",
            "CLASSIFICATION:",
            f"{branching_field.upper()}:",
        ]:
            if cleaned_output.startswith(prefix):
                cleaned_output = cleaned_output[len(prefix) :].strip()

        # For document_type branching, look for valid class keys ANYWHERE in the output
        # This handles cases where LLM responds with "DIESER BERICHT IST EIN BEFUNDBERICHT"
        if branching_field == "document_type":
            # Get all valid document class keys from database
            try:
                all_classes = self.doc_class_manager.get_all_classes()
                valid_classes = [c.class_key.upper() for c in all_classes if c.is_enabled]
            except Exception:
                # Fallback to hardcoded values if database lookup fails
                valid_classes = ["ARZTBRIEF", "BEFUNDBERICHT", "LABORWERTE"]

            found_class = None
            for class_key in valid_classes:
                if class_key in cleaned_output:
                    found_class = class_key
                    logger.info(f"🔍 Found document class '{class_key}' in output")
                    break

            if found_class:
                branch_value = found_class
            else:
                # Fallback to first word if no valid class found
                branch_value = (
                    cleaned_output.split()[0] if cleaned_output.split() else cleaned_output
                )
                logger.warning(
                    f"⚠️ No valid document class found in output, using first word: {branch_value}"
                )
        else:
            # For other branching fields, extract first word
            branch_value = cleaned_output.split()[0] if cleaned_output.split() else cleaned_output

        # Determine branch type based on field name
        if branching_field == "document_type":
            # Document class branching - lookup class and load class-specific steps
            doc_class = self.doc_class_manager.get_class_by_key(branch_value)
            if doc_class:
                logger.info(
                    f"✅ Document class branching: {branch_value} → {doc_class.display_name}"
                )
                return {
                    "field": branching_field,
                    "value": branch_value,
                    "type": "document_class",
                    "target_id": doc_class.id,
                    "target_key": doc_class.class_key,
                    "target_display_name": doc_class.display_name,
                }
            logger.warning(f"⚠️ Unknown document class: {branch_value}")
            return {
                "field": branching_field,
                "value": branch_value,
                "type": "document_class",
                "target_id": None,
                "target_key": branch_value,
                "target_display_name": "Unknown",
            }
        # Generic branching (boolean, enum, quality level, etc.)
        # Determine subtype based on common patterns
        branch_type = "generic"
        if branch_value in ["TRUE", "FALSE", "YES", "NO", "JA", "NEIN"]:
            branch_type = "boolean"
        elif branch_value in ["MEDIZINISCH", "NICHT_MEDIZINISCH"]:
            branch_type = "boolean"  # Medical validation boolean
        elif branch_value in ["HIGH", "MEDIUM", "LOW", "HOCH", "MITTEL", "NIEDRIG"]:
            branch_type = "enum"  # Quality level enum

        logger.info(f"✅ Generic branching ({branch_type}): {branching_field} = {branch_value}")
        return {
            "field": branching_field,
            "value": branch_value,
            "type": branch_type,
            "target_id": None,
            "target_key": None,
            "target_display_name": None,
        }

    def load_ocr_configuration(self) -> OCRConfigurationDB | None:
        """
        Load OCR configuration from database using repository pattern.

        Returns:
            OCR configuration or None if not found
        """
        try:
            config = self.ocr_config_repository.get_config()
            if config:
                logger.info(f"🔍 Loaded OCR configuration: {config.selected_engine}")
            return config
        except Exception as e:
            logger.error(f"❌ Failed to load OCR configuration: {e}")
            return None

    def get_model_info(self, model_id: int) -> AvailableModelDB | None:
        """
        Get model information from database using repository pattern.

        Args:
            model_id: Database ID of the model

        Returns:
            Model information or None if not found
        """
        try:
            return self.model_repository.get_enabled_model_by_id(model_id)
        except Exception as e:
            logger.error(f"❌ Failed to load model info for ID {model_id}: {e}")
            return None

    # ==================== STEP EXECUTION ====================

    async def execute_step(
        self,
        step: DynamicPipelineStepDB,
        input_text: str,
        context: dict[str, Any] = None,
        processing_id: str = None,
        document_type: str = None,
    ) -> tuple[bool, str, str | None]:
        """
        Execute a single pipeline step.

        Args:
            step: Pipeline step configuration
            input_text: Input text for this step
            context: Additional context variables (e.g., target_language)
            processing_id: Processing ID for cost tracking (optional)
            document_type: Document type for cost tracking (optional)

        Returns:
            Tuple of (success: bool, output_text: str, error_message: str | None)
        """
        context = context or {}

        # Get model information
        model = self.get_model_info(step.selected_model_id)
        if not model:
            error = f"Model ID {step.selected_model_id} not found or disabled"
            logger.error(f"❌ {error}")
            return False, "", error

        # Sanitize input text before prompt construction
        sanitized_input, was_modified = sanitize_for_prompt(input_text)
        if was_modified:
            logger.info(f"Input text sanitized for step '{step.name}'")

        # Detect injection patterns (log only, don't block)
        injection_report = detect_injection(input_text)
        if injection_report.has_detections:
            log_injection_detection(
                report=injection_report,
                processing_id=processing_id,
                step_name=step.name,
            )

        # Prepare prompt with variable substitution (sanitized input)
        try:
            prompt = step.prompt_template.format(
                input_text=sanitized_input,
                **context,  # e.g., target_language
            )
        except KeyError as e:
            error = f"Missing required variable in prompt template: {e}"
            logger.error(f"❌ {error}")
            return False, "", error

        # Get system_prompt for role separation (may be None for backward compat)
        system_prompt = getattr(step, "system_prompt", None)

        # Execute with retries
        max_retries = step.max_retries if step.retry_on_failure else 1
        last_error = None

        for attempt in range(max_retries):
            try:
                logger.info(
                    f"🔄 Executing step '{step.name}' (attempt {attempt + 1}/{max_retries})"
                )
                logger.info(
                    f"   Model: {model.name} | Temp: {step.temperature} | Max Tokens: {step.max_tokens or model.max_tokens}"
                )
                logger.info(f"   Input length: {len(input_text)} characters")

                # Call AI model based on provider
                start_time = time.time()

                if model.provider == ModelProvider.MISTRAL:
                    # Use Mistral AI API
                    mistral_client = MistralClient()
                    mistral_result = await mistral_client.process_text(
                        prompt=prompt,
                        model=model.name,
                        temperature=step.temperature or 0.7,
                        max_tokens=step.max_tokens or model.max_tokens or 4096,
                        system_prompt=system_prompt,
                    )
                    result_dict = {
                        "text": mistral_result["content"],
                        "input_tokens": mistral_result["input_tokens"],
                        "output_tokens": mistral_result["output_tokens"],
                    }

                elif model.provider == ModelProvider.DIFY_RAG:
                    # External RAG service (Dify on Hetzner)
                    from app.services.dify_rag_client import DifyRAGClient

                    rag_client = DifyRAGClient()
                    if not rag_client.is_enabled:
                        logger.info(f"Dify RAG not configured, skipping '{step.name}'")
                        result_dict = {"text": "", "input_tokens": 0, "output_tokens": 0}
                    else:
                        target_language = context.get("target_language", "en")
                        answer, rag_metadata = await rag_client.query_guidelines(
                            medical_text=input_text,
                            document_type=context.get("document_type", "UNKNOWN"),
                            target_language=target_language,
                            user_id=processing_id or "pipeline",
                        )
                        if rag_metadata.get("skipped"):
                            logger.info(
                                f"Dify RAG skipped for '{step.name}': {rag_metadata.get('reason', rag_metadata.get('error', 'unknown'))}"
                            )
                            result_dict = {"text": "", "input_tokens": 0, "output_tokens": 0}
                        else:
                            result_dict = {"text": answer, "input_tokens": 0, "output_tokens": 0}

                else:
                    # Use OVH AI Endpoints (default)
                    result_dict = await self.ovh_client.process_medical_text_with_prompt(
                        full_prompt=prompt,
                        temperature=step.temperature or 0.7,
                        max_tokens=step.max_tokens or model.max_tokens or 4096,
                        use_fast_model=(model.name == "Mistral-Nemo-Instruct-2407"),
                        system_prompt=system_prompt,
                    )

                execution_time = time.time() - start_time

                # Extract text from dict response
                result = result_dict["text"]

                # Check for API errors
                if result.startswith("Error"):
                    last_error = result

                    # Detect 503 service unavailable errors (infrastructure issues)
                    is_503_error = (
                        "503" in result
                        or "Service Unavailable" in result
                        or "ring-balancer" in result
                    )

                    if is_503_error and attempt < max_retries - 1:
                        # Use longer backoff for 503 errors (infrastructure recovery time)
                        retry_delay = 5 * (attempt + 1)  # 5s, 10s instead of 1s, 2s
                        logger.warning(
                            f"⚠️ OVH infrastructure error (503) on attempt {attempt + 1}: {result[:200]}"
                        )
                        logger.info(f"   Waiting {retry_delay}s for OVH infrastructure recovery...")
                        time.sleep(retry_delay)
                    else:
                        logger.warning(f"⚠️ API error on attempt {attempt + 1}: {result}")

                    continue

                # ✨ NEW: Log AI call with token usage (don't break pipeline if this fails!)
                try:
                    self.cost_tracker.log_ai_call(
                        processing_id=processing_id,
                        step_name=step.name,
                        input_tokens=result_dict.get("input_tokens", 0),
                        output_tokens=result_dict.get("output_tokens", 0),
                        model_provider="OVH",
                        model_name=result_dict.get("model") or model.name,
                        processing_time_seconds=execution_time,
                        document_type=document_type,
                        metadata={
                            "step_id": step.id,
                            "temperature": step.temperature or 0.7,
                            "max_tokens": step.max_tokens or model.max_tokens or 4096,
                            "model_db_id": model.id,
                            "attempt": attempt + 1,
                        },
                    )
                    logger.info(
                        f"💰 Logged {result_dict.get('total_tokens', 0)} tokens for step '{step.name}'"
                    )
                except Exception as log_error:
                    # Don't fail the pipeline if logging fails!
                    logger.error(f"⚠️ Failed to log AI costs (non-critical): {log_error}")

                # Validate output
                expected_values = None
                stop_conds = getattr(step, "stop_conditions", None)
                if isinstance(stop_conds, dict) and stop_conds.get("stop_on_values"):
                    # For classification/validation steps, check output format
                    expected_values = list(stop_conds["stop_on_values"])

                is_valid, validation_msg = validate_step_output(
                    step_name=step.name,
                    output=result,
                    input_text=input_text,
                    expected_values=expected_values,
                    system_prompt=system_prompt if isinstance(system_prompt, str) else None,
                )
                if not is_valid:
                    logger.warning(
                        f"Output validation failed for '{step.name}': {validation_msg}"
                    )
                    # On structured steps (classification), retry
                    if getattr(step, "is_branching_step", False) and attempt < max_retries - 1:
                        last_error = f"Output validation: {validation_msg}"
                        continue

                # Success!
                logger.info(f"✅ Step '{step.name}' completed in {execution_time:.2f}s")
                return True, result, None

            except Exception as e:
                last_error = str(e)
                logger.error(f"❌ Step '{step.name}' failed on attempt {attempt + 1}: {e}")

                if attempt < max_retries - 1:
                    # Detect 503 errors in exceptions (OVH infrastructure issues)
                    error_str = str(e).lower()
                    is_503_error = (
                        "503" in error_str
                        or "service unavailable" in error_str
                        or "ring-balancer" in error_str
                    )

                    if is_503_error:
                        # Use longer backoff for 503 errors (infrastructure recovery time)
                        retry_delay = 5 * (attempt + 1)  # 5s, 10s
                        logger.warning("⚠️ OVH infrastructure error (503) detected in exception")
                        logger.info(f"   Waiting {retry_delay}s for OVH infrastructure recovery...")
                        time.sleep(retry_delay)
                    else:
                        # Standard exponential backoff for other errors
                        retry_delay = 1 * (attempt + 1)  # 1s, 2s
                        logger.info(f"🔄 Retrying step '{step.name}' in {retry_delay}s...")
                        time.sleep(retry_delay)

        # All retries failed
        return False, "", last_error or "Unknown error"

    # ==================== PIPELINE EXECUTION ====================

    async def execute_pipeline(
        self, processing_id: str, input_text: str, context: dict[str, Any] = None
    ) -> tuple[bool, str, dict[str, Any]]:
        """
        Execute complete AI pipeline on input text.

        IMPORTANT - EXECUTOR IS A PURE SERVICE:
        - Does NOT modify job status (worker's responsibility)
        - Does NOT set job.started_at (preserves queue time)
        - Does NOT mark jobs as failed (returns errors to worker)
        - Only writes PipelineStepExecutionDB records for audit trail
        - Only updates progress_percent and current_step_id for real-time tracking

        The worker (orchestrator) owns the job lifecycle and handles all status changes.

        Args:
            processing_id: Unique ID for this processing request
            input_text: Initial input text (after OCR)
            context: Additional context (e.g., target_language, document_type)

        Returns:
            Tuple of (success: bool, final_output: str, execution_metadata: Dict)
            - success: True if pipeline completed, False if error occurred
            - final_output: Processed text from pipeline
            - execution_metadata: Complete metadata including errors if any
        """
        context = context or {}

        logger.info(
            f"🚀 Starting modular pipeline execution with branching support: {processing_id[:8]}"
        )

        # NOTE: PII removal is now handled by external service in worker BEFORE pipeline execution
        # See worker/tasks/document_processing.py - PIIServiceClient (Hetzner primary, Railway fallback)

        # Load job using repository (must exist - created by upload endpoint)
        job = self.job_repository.get_by_processing_id(processing_id)

        if not job:
            error_msg = f"Job not found for processing_id: {processing_id}"
            logger.error(f"❌ {error_msg}")
            return False, "", {"error": error_msg, "error_type": "job_not_found"}

        logger.info(f"📋 Loaded job: {job.job_id}")
        job_id = job.job_id

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
            "pre_branching_steps": len(universal_steps),
            "steps_executed": [],
            "total_time": 0,
            "branching_occurred": False,
            "document_class": None,
            "branching_path": [],  # Track all branching decisions
            "post_branching_steps": 0,  # Will be set later
        }

        pipeline_start_time = time.time()
        all_steps = []  # Track all steps for progress calculation

        # ==================== PHASE 1: UNIVERSAL STEPS ====================
        logger.info(f"📋 Phase 1: Executing {len(universal_steps)} universal steps")

        branch_metadata = None  # Stores branching metadata (replaces branch_value)
        document_class_specific_steps = []

        for idx, step in enumerate(universal_steps):
            step_start_time = time.time()
            all_steps.append(step)

            # Update job progress
            len(all_steps)
            progress_percent = int(
                (idx / max(len(universal_steps), 1)) * 50
            )  # First 50% is universal steps
            job.progress_percent = progress_percent
            job.current_step_id = step.id
            self.session.commit()

            await self.progress_tracker.step_started(
                processing_id=processing_id,
                step_name=step.name,
                ui_stage=step.ui_stage or "translation",
                completed_count=idx,
                total_steps=len(universal_steps),
                phase="universal",
            )

            logger.info(f"▶️  Step {idx + 1}/{len(universal_steps)}: {step.name}")

            # Check if step has required context variables
            if step.required_context_variables:
                missing_vars = [
                    var
                    for var in step.required_context_variables
                    if var not in context or context[var] is None
                ]

                if missing_vars:
                    logger.info(
                        f"⏭️  Skipping step '{step.name}' - missing required context variables: {missing_vars}"
                    )

                    # Log skipped step using encrypted repository
                    self._log_step_execution(
                        job_id=job_id,
                        step=step,
                        status=StepExecutionStatus.SKIPPED,
                        input_text=current_output,
                        output_text=None,
                        step_start_time=step_start_time,
                        error=None,
                        metadata={
                            "skip_reason": "missing_required_context_variables",
                            "missing_variables": missing_vars,
                            "required_variables": step.required_context_variables,
                        },
                    )

                    execution_metadata["steps_executed"].append(
                        {
                            "step_name": step.name,
                            "step_order": step.order,
                            "success": True,  # Skipping is success
                            "execution_time": time.time() - step_start_time,
                            "error": None,
                            "skipped": True,
                            "skip_reason": f"Missing required variables: {', '.join(missing_vars)}",
                        }
                    )

                    # Continue to next step without updating current_output
                    continue

            # Execute step
            success, output, error = await self.execute_step(
                step=step,
                input_text=current_output,
                context=context,
                processing_id=processing_id,
                document_type=context.get("document_type"),
            )

            step_execution_time = time.time() - step_start_time

            # Prepare step metadata (will be populated for branching steps)
            step_metadata_dict = None

            # Check if this is the branching step - extract branch BEFORE logging to DB
            if step.is_branching_step and branching_step and success:
                logger.info(f"🔀 Branching step detected: {step.name}")

                # Extract branch metadata (new dynamic system)
                branch_metadata = self.extract_branch_value(
                    output, step.branching_field or "document_type"
                )

                if branch_metadata:
                    # Store branching metadata for this step
                    step_metadata_dict = {
                        "is_branching_step": True,
                        "branching_field": step.branching_field or "document_type",
                        "branch_metadata": branch_metadata,
                        "decision_timestamp": datetime.now().isoformat(),
                    }

                    # Add to branching path for job-level tracking
                    execution_metadata["branching_path"].append(
                        {
                            "step_name": step.name,
                            "step_order": step.order,
                            "field": branch_metadata["field"],
                            "decision": branch_metadata["value"],
                            "type": branch_metadata["type"],
                        }
                    )

                    # Handle document class branching (loads class-specific steps)
                    if branch_metadata["type"] == "document_class" and branch_metadata["target_id"]:
                        logger.info(
                            f"🎯 Document class branch: {branch_metadata['target_display_name']} (ID: {branch_metadata['target_id']})"
                        )

                        # Load document class-specific steps
                        document_class_specific_steps = self.load_steps_by_document_class(
                            branch_metadata["target_id"]
                        )

                        execution_metadata["branching_occurred"] = True
                        execution_metadata["document_class"] = {
                            "class_key": branch_metadata["target_key"],
                            "display_name": branch_metadata["target_display_name"],
                            "class_id": branch_metadata["target_id"],
                        }
                        execution_metadata["class_specific_steps"] = len(
                            document_class_specific_steps
                        )

                        # Store document_type in context for subsequent steps
                        context["document_type"] = branch_metadata["target_key"]
                    else:
                        # Generic branching (boolean, enum, etc.) - just log the decision
                        logger.info(
                            f"🔀 Generic branch decision: {branch_metadata['field']} = {branch_metadata['value']}"
                        )
                else:
                    logger.warning("⚠️ Failed to extract branch value from output")

            # Check for stop conditions (early termination)
            should_terminate, current_output, execution_metadata = self._handle_stop_condition(
                step=step,
                output=output,
                current_output=current_output,
                job_id=job_id,
                step_start_time=step_start_time,
                step_execution_time=step_execution_time,
                pipeline_start_time=pipeline_start_time,
                execution_metadata=execution_metadata,
                success=success,
            )
            if should_terminate:
                return False, current_output, execution_metadata

            # Log step execution with metadata
            self._log_step_execution(
                job_id=job_id,
                step=step,
                status=StepExecutionStatus.COMPLETED if success else StepExecutionStatus.FAILED,
                input_text=current_output,
                output_text=output if success else None,
                step_start_time=step_start_time,
                error=error,
                metadata=step_metadata_dict,  # Store branching metadata
            )

            # Store metadata for in-memory tracking
            execution_metadata["steps_executed"].append(
                {
                    "step_name": step.name,
                    "step_order": step.order,
                    "success": success,
                    "execution_time": step_execution_time,
                    "error": error,
                    "is_branching_step": step.is_branching_step,
                }
            )

            if not success:
                logger.error(f"❌ Pipeline failed at step '{step.name}': {error}")
                # Return error to worker - don't mark job as failed here
                execution_metadata["failed_at_step"] = step.name
                execution_metadata["failed_step_id"] = step.id
                execution_metadata["error"] = error
                execution_metadata["error_type"] = "step_execution_failed"
                execution_metadata["total_time"] = time.time() - pipeline_start_time
                return False, current_output, execution_metadata

            await self.progress_tracker.step_completed(processing_id, step.name)

            # Update current output for next step
            # For branching steps, keep the input flowing (don't replace with branch decision)
            if step.input_from_previous_step and not step.is_branching_step:
                if step.output_format == "append" and output:
                    current_output = current_output + output
                else:
                    current_output = output

            # If document class branching occurred, break to load class-specific steps
            if step.is_branching_step and document_class_specific_steps:
                break  # Exit universal steps loop, continue with class-specific steps

        # ==================== PHASE 2: CLASS-SPECIFIC STEPS ====================
        if document_class_specific_steps:
            phase1_completed = len(all_steps)
            phase2_total = phase1_completed + len(document_class_specific_steps)
            await self.progress_tracker.update_total_steps(processing_id, phase2_total)

            logger.info(
                f"📋 Phase 2: Executing {len(document_class_specific_steps)} class-specific steps"
            )

            for idx, step in enumerate(document_class_specific_steps):
                step_start_time = time.time()
                all_steps.append(step)

                # Update job progress
                progress_percent = 50 + int((idx / max(len(document_class_specific_steps), 1)) * 50)
                job.progress_percent = progress_percent
                job.current_step_id = step.id
                self.session.commit()

                await self.progress_tracker.step_started(
                    processing_id=processing_id,
                    step_name=step.name,
                    ui_stage=step.ui_stage or "translation",
                    completed_count=phase1_completed + idx,
                    total_steps=phase2_total,
                    phase="class_specific",
                )

                logger.info(
                    f"▶️  Step {idx + 1}/{len(document_class_specific_steps)}: {step.name} [{execution_metadata['document_class']['class_key']}]"
                )

                # Execute step
                success, output, error = await self.execute_step(
                    step=step,
                    input_text=current_output,
                    context=context,
                    processing_id=processing_id,
                    document_type=context.get("document_type"),
                )

                step_execution_time = time.time() - step_start_time

                # Prepare step metadata (class-specific steps could also be branching)
                step_metadata_dict = None

                # Check if this is a branching step (rare in class-specific, but supported)
                if step.is_branching_step and success:
                    logger.info(f"🔀 Branching step in class-specific pipeline: {step.name}")

                    # Extract branch metadata
                    branch_info = self.extract_branch_value(
                        output, step.branching_field or "document_type"
                    )

                    if branch_info:
                        # Store branching metadata for this step
                        step_metadata_dict = {
                            "is_branching_step": True,
                            "branching_field": step.branching_field or "document_type",
                            "branch_metadata": branch_info,
                            "decision_timestamp": datetime.now().isoformat(),
                        }

                        # Add to branching path
                        execution_metadata["branching_path"].append(
                            {
                                "step_name": step.name,
                                "step_order": step.order,
                                "field": branch_info["field"],
                                "decision": branch_info["value"],
                                "type": branch_info["type"],
                            }
                        )

                        logger.info(
                            f"🔀 Class-specific branch decision: {branch_info['field']} = {branch_info['value']}"
                        )

                # Check for stop conditions (early termination) - PHASE 2
                should_terminate, current_output, execution_metadata = self._handle_stop_condition(
                    step=step,
                    output=output,
                    current_output=current_output,
                    job_id=job_id,
                    step_start_time=step_start_time,
                    step_execution_time=step_execution_time,
                    pipeline_start_time=pipeline_start_time,
                    execution_metadata=execution_metadata,
                    success=success,
                )
                if should_terminate:
                    return False, current_output, execution_metadata

                # Log step execution with metadata
                self._log_step_execution(
                    job_id=job_id,
                    step=step,
                    status=StepExecutionStatus.COMPLETED if success else StepExecutionStatus.FAILED,
                    input_text=current_output,
                    output_text=output if success else None,
                    step_start_time=step_start_time,
                    error=error,
                    metadata=step_metadata_dict,  # Store branching metadata
                )

                # Store metadata for in-memory tracking
                execution_metadata["steps_executed"].append(
                    {
                        "step_name": step.name,
                        "step_order": step.order,
                        "success": success,
                        "execution_time": step_execution_time,
                        "error": error,
                        "document_class_id": step.document_class_id,
                    }
                )

                if not success:
                    logger.error(f"❌ Pipeline failed at step '{step.name}': {error}")
                    # Return error to worker - don't mark job as failed here
                    execution_metadata["failed_at_step"] = step.name
                    execution_metadata["failed_step_id"] = step.id
                    execution_metadata["error"] = error
                    execution_metadata["error_type"] = "step_execution_failed"
                    execution_metadata["total_time"] = time.time() - pipeline_start_time
                    return False, current_output, execution_metadata

                await self.progress_tracker.step_completed(processing_id, step.name)

                # Update current output for next step
                if step.input_from_previous_step:
                    if step.output_format == "append" and output:
                        current_output = current_output + output
                    else:
                        current_output = output

        # ==================== PHASE 3: POST-BRANCHING UNIVERSAL STEPS ====================
        post_branching_steps = self.load_post_branching_steps()

        if post_branching_steps:
            pre_phase3_completed = len(all_steps)
            full_total = pre_phase3_completed + len(post_branching_steps)
            await self.progress_tracker.update_total_steps(processing_id, full_total)

            logger.info(
                f"📋 Phase 3: Executing {len(post_branching_steps)} post-branching universal steps"
            )

            for idx, step in enumerate(post_branching_steps):
                step_start_time = time.time()
                all_steps.append(step)

                # Update job progress
                # Phase 3 is the last 20% of progress (50% universal + 30% doc-specific + 20% post-branching)
                base_progress = 80  # After Phase 1 (50%) and Phase 2 (30%)
                progress_percent = base_progress + int(
                    (idx / max(len(post_branching_steps), 1)) * 20
                )
                job.progress_percent = progress_percent
                job.current_step_id = step.id
                self.session.commit()

                await self.progress_tracker.step_started(
                    processing_id=processing_id,
                    step_name=step.name,
                    ui_stage=step.ui_stage or "translation",
                    completed_count=pre_phase3_completed + idx,
                    total_steps=full_total,
                    phase="post_branching",
                )

                logger.info(
                    f"▶️  Step {idx + 1}/{len(post_branching_steps)}: {step.name} [POST-BRANCHING]"
                )

                # Check if step has required context variables
                if step.required_context_variables:
                    missing_vars = [
                        var
                        for var in step.required_context_variables
                        if var not in context or context[var] is None
                    ]

                    if missing_vars:
                        logger.info(
                            f"⏭️  Skipping post-branching step '{step.name}' - missing required context variables: {missing_vars}"
                        )

                        # Log skipped step using encrypted repository
                        self._log_step_execution(
                            job_id=job_id,
                            step=step,
                            status=StepExecutionStatus.SKIPPED,
                            input_text=current_output,
                            output_text=None,
                            step_start_time=step_start_time,
                            error=None,
                            metadata={
                                "post_branching": True,
                                "skip_reason": "missing_required_context_variables",
                                "missing_variables": missing_vars,
                                "required_variables": step.required_context_variables,
                            },
                        )

                        execution_metadata["steps_executed"].append(
                            {
                                "step_name": step.name,
                                "step_order": step.order,
                                "success": True,  # Skipping is success
                                "execution_time": time.time() - step_start_time,
                                "error": None,
                                "post_branching": True,
                                "skipped": True,
                                "skip_reason": f"Missing required variables: {', '.join(missing_vars)}",
                            }
                        )

                        # Continue to next step without updating current_output
                        continue

                # Execute step
                success, output, error = await self.execute_step(
                    step=step,
                    input_text=current_output,
                    context=context,
                    processing_id=processing_id,
                    document_type=context.get("document_type"),
                )

                step_execution_time = time.time() - step_start_time

                # Check for stop conditions (early termination) - PHASE 3
                should_terminate, current_output, execution_metadata = self._handle_stop_condition(
                    step=step,
                    output=output,
                    current_output=current_output,
                    job_id=job_id,
                    step_start_time=step_start_time,
                    step_execution_time=step_execution_time,
                    pipeline_start_time=pipeline_start_time,
                    execution_metadata=execution_metadata,
                    success=success,
                )
                if should_terminate:
                    return False, current_output, execution_metadata

                # Log step execution
                self._log_step_execution(
                    job_id=job_id,
                    step=step,
                    status=StepExecutionStatus.COMPLETED if success else StepExecutionStatus.FAILED,
                    input_text=current_output,
                    output_text=output if success else None,
                    step_start_time=step_start_time,
                    error=error,
                    metadata={"post_branching": True},
                )

                # Store metadata for in-memory tracking
                execution_metadata["steps_executed"].append(
                    {
                        "step_name": step.name,
                        "step_order": step.order,
                        "success": success,
                        "execution_time": step_execution_time,
                        "error": error,
                        "post_branching": True,
                    }
                )

                if not success:
                    logger.error(
                        f"❌ Pipeline failed at post-branching step '{step.name}': {error}"
                    )
                    execution_metadata["failed_at_step"] = step.name
                    execution_metadata["failed_step_id"] = step.id
                    execution_metadata["error"] = error
                    execution_metadata["error_type"] = "step_execution_failed"
                    execution_metadata["total_time"] = time.time() - pipeline_start_time
                    return False, current_output, execution_metadata

                await self.progress_tracker.step_completed(processing_id, step.name)

                # Update current output for next step
                if step.input_from_previous_step:
                    if step.output_format == "append" and output:
                        current_output = current_output + output
                    else:
                        current_output = output

        # Pipeline completed successfully
        total_time = time.time() - pipeline_start_time
        execution_metadata["total_time"] = total_time
        execution_metadata["total_steps"] = len(all_steps)
        execution_metadata["post_branching_steps"] = (
            len(post_branching_steps) if post_branching_steps else 0
        )
        execution_metadata["pipeline_execution_time"] = total_time  # For worker to use

        # NOTE: Executor is a pure service - it does NOT finalize the job
        # The worker (orchestrator) is responsible for job finalization
        # We only return execution results for the worker to use

        logger.info(f"✅ Pipeline execution completed successfully in {total_time:.2f}s")
        logger.info(
            f"📊 Branching decisions: {len(execution_metadata['branching_path'])} decision(s) made"
        )
        if execution_metadata.get("document_class"):
            logger.info(
                f"📄 Document class: {execution_metadata['document_class']['display_name']}"
            )

        await self.progress_tracker.cleanup(processing_id)

        return True, current_output, execution_metadata

    # ==================== HELPER METHODS ====================

    def _serialize_pipeline_config(self) -> dict[str, Any]:
        """Serialize current pipeline configuration for job record."""
        steps = self.load_pipeline_steps()
        return {
            "steps": [
                {
                    "id": step.id,
                    "name": step.name,
                    "order": step.order,
                    "model_id": step.selected_model_id,
                }
                for step in steps
            ]
        }

    def _serialize_ocr_config(self) -> dict[str, Any]:
        """Serialize current OCR configuration for job record."""
        config = self.load_ocr_configuration()
        if not config:
            return {}

        return {
            "selected_engine": config.selected_engine,
            "mistral_ocr_config": config.mistral_ocr_config,
            "paddleocr_config": config.paddleocr_config,
            "pii_removal_enabled": config.pii_removal_enabled,
        }


class ModularPipelineManager:
    """
    High-level manager for modular pipeline CRUD operations.
    Used by API endpoints for pipeline configuration.
    """

    def __init__(
        self,
        session: Session,
        step_repository: PipelineStepRepository | None = None,
        ocr_config_repository: OCRConfigurationRepository | None = None,
        model_repository: AvailableModelRepository | None = None,
    ):
        """
        Initialize manager with database session and repositories.

        Args:
            session: SQLAlchemy session (kept for backward compatibility)
            step_repository: Pipeline step repository (injected for clean architecture)
            ocr_config_repository: OCR configuration repository (injected for clean architecture)
            model_repository: Available model repository (injected for clean architecture)
        """
        self.session = session
        self.step_repository = step_repository or PipelineStepRepository(session)
        self.ocr_config_repository = ocr_config_repository or OCRConfigurationRepository(session)
        self.model_repository = model_repository or AvailableModelRepository(session)

    # ==================== PIPELINE STEP CRUD ====================

    def get_all_steps(self) -> list[DynamicPipelineStepDB]:
        """Get all pipeline steps (enabled and disabled) using repository pattern."""
        return self.step_repository.get_all_ordered()

    def get_step(self, step_id: int) -> DynamicPipelineStepDB | None:
        """Get a single pipeline step by ID using repository pattern."""
        return self.step_repository.get(step_id)

    def create_step(self, step_data: dict[str, Any]) -> DynamicPipelineStepDB:
        """Create a new pipeline step."""
        step = DynamicPipelineStepDB(**step_data)
        self.session.add(step)
        self.session.commit()
        self.session.refresh(step)
        return step

    def update_step(self, step_id: int, step_data: dict[str, Any]) -> DynamicPipelineStepDB | None:
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

    def reorder_steps(self, step_order: list[int]) -> bool:
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

    def get_ocr_config(self) -> OCRConfigurationDB | None:
        """Get current OCR configuration using repository pattern."""
        return self.ocr_config_repository.get_config()

    def update_ocr_config(self, config_data: dict[str, Any]) -> OCRConfigurationDB | None:
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

    def get_all_models(self, enabled_only: bool = False) -> list[AvailableModelDB]:
        """Get all available AI models using repository pattern."""
        if enabled_only:
            return self.model_repository.get_enabled_models()
        return self.model_repository.get_all()

    def get_model(self, model_id: int) -> AvailableModelDB | None:
        """Get a single model by ID using repository pattern."""
        return self.model_repository.get(model_id)

    def update_model(self, model_id: int, model_data: dict[str, Any]) -> AvailableModelDB | None:
        """
        Update an existing AI model.

        Args:
            model_id: ID of the model to update
            model_data: Dictionary of fields to update

        Returns:
            Updated model instance or None if not found
        """
        model = self.get_model(model_id)
        if not model:
            return None

        # Update fields
        for key, value in model_data.items():
            if hasattr(model, key):
                setattr(model, key, value)

        # Update timestamp
        model.last_modified = datetime.now()

        self.session.commit()
        self.session.refresh(model)
        return model
