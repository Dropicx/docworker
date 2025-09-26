"""
Optimized Pipeline Processor V2 - Universal vs Document-Specific Prompts
"""

import asyncio
import logging
import time
from typing import Dict, Optional, Tuple, Any, List
from datetime import datetime, timedelta
from dataclasses import dataclass

from app.models.document_types import DocumentClass, ProcessingStepEnum
from app.services.ovh_client import OVHClient
from app.services.ai_interaction_logger import AIInteractionLogger

logger = logging.getLogger(__name__)

@dataclass
class UniversalPrompts:
    """Container for universal prompts used across all document types"""
    medical_validation_prompt: str
    classification_prompt: str
    preprocessing_prompt: str
    grammar_check_prompt: str
    language_translation_prompt: str
    version: int = 1
    last_modified: Optional[datetime] = None

@dataclass
class DocumentSpecificPrompts:
    """Container for document-type-specific prompts"""
    document_type: DocumentClass
    translation_prompt: str
    fact_check_prompt: str
    final_check_prompt: str
    formatting_prompt: str
    version: int = 1
    last_modified: Optional[datetime] = None

@dataclass
class PipelineStep:
    """Represents a single pipeline step with its configuration"""
    name: ProcessingStepEnum
    is_universal: bool
    enabled: bool
    order: int
    description: str

class OptimizedPipelineV2:
    """
    Enhanced pipeline processor with universal vs document-specific prompt separation

    Flow:
    1. [UNIVERSAL] Medical Validation - Same for all docs
    2. [UNIVERSAL] Classification - Determines document type
    3. [UNIVERSAL] Preprocessing - Same anonymization for all
    4. [DOCUMENT-SPECIFIC] Translation - Complexity based on doc type
    5. [DOCUMENT-SPECIFIC] Fact Check - Domain-specific validation
    6. [UNIVERSAL] Grammar Check - Same language rules
    7. [DOCUMENT-SPECIFIC] Final Check - Type-specific quality
    8. [DOCUMENT-SPECIFIC] Formatting - Type-specific structure
    9. [UNIVERSAL] Language Translation - Same template for all (optional)
    """

    def __init__(self):
        self.ovh_client = OVHClient()
        self.ai_logger = AIInteractionLogger()

        # Caching
        self._universal_prompts_cache: Optional[UniversalPrompts] = None
        self._document_prompts_cache: Dict[DocumentClass, DocumentSpecificPrompts] = {}
        self._cache_timeout = timedelta(minutes=5)
        self._last_cache_update = datetime.now()

        # Performance tracking
        self._step_performance: Dict[str, Dict[str, Any]] = {}

        # Pipeline configuration
        self._pipeline_steps = self._get_default_pipeline_steps()

    def _get_default_pipeline_steps(self) -> List[PipelineStep]:
        """Define the optimized pipeline flow"""
        return [
            PipelineStep(ProcessingStepEnum.MEDICAL_VALIDATION, True, True, 1,
                        "Universal medical content detection"),
            PipelineStep(ProcessingStepEnum.CLASSIFICATION, True, True, 2,
                        "Universal document type classification"),
            PipelineStep(ProcessingStepEnum.PREPROCESSING, True, True, 3,
                        "Universal personal data removal"),
            PipelineStep(ProcessingStepEnum.TRANSLATION, False, True, 4,
                        "Document-specific medical translation"),
            PipelineStep(ProcessingStepEnum.FACT_CHECK, False, True, 5,
                        "Document-specific medical fact checking"),
            PipelineStep(ProcessingStepEnum.GRAMMAR_CHECK, True, True, 6,
                        "Universal grammar and spelling check"),
            PipelineStep(ProcessingStepEnum.FINAL_CHECK, False, True, 7,
                        "Document-specific quality assurance"),
            PipelineStep(ProcessingStepEnum.FORMATTING, False, True, 8,
                        "Document-specific text formatting"),
            PipelineStep(ProcessingStepEnum.LANGUAGE_TRANSLATION, True, False, 9,
                        "Universal language translation (optional)")
        ]

    async def process_document(
        self,
        text: str,
        target_language: str = "German",
        document_type_hint: Optional[DocumentClass] = None,
        processing_id: Optional[str] = None,
        enable_parallel_processing: bool = True
    ) -> Dict[str, Any]:
        """
        Process a document through the optimized pipeline

        Args:
            text: Input document text
            target_language: Target language for final translation
            document_type_hint: Optional hint for document type
            processing_id: Unique identifier for this processing session
            enable_parallel_processing: Enable parallel execution where possible

        Returns:
            Dictionary with processing results and metadata
        """
        if not processing_id:
            processing_id = f"proc_{int(time.time() * 1000)}"

        logger.info(f"🚀 Starting optimized pipeline V2 processing: {processing_id}")
        start_time = time.time()

        try:
            # Load prompts (with caching)
            universal_prompts = await self._get_universal_prompts()

            # Initialize result tracking
            results = {
                "processing_id": processing_id,
                "pipeline_version": "v2_optimized",
                "original_text": text,
                "steps_completed": [],
                "step_results": {},
                "performance_metrics": {},
                "document_type": None,
                "final_text": text
            }

            current_text = text
            detected_document_type = document_type_hint

            # Phase 1: Universal Pre-processing Steps (Sequential - each depends on previous)
            logger.info("🔍 Phase 1: Universal Pre-processing")

            # Step 1: Medical Validation (Universal)
            if self._is_step_enabled(ProcessingStepEnum.MEDICAL_VALIDATION):
                step_start = time.time()
                is_medical = await self._execute_universal_step(
                    ProcessingStepEnum.MEDICAL_VALIDATION,
                    current_text,
                    universal_prompts.medical_validation_prompt,
                    processing_id
                )

                if is_medical != "MEDIZINISCH":
                    logger.warning(f"Document {processing_id} failed medical validation: {is_medical}")
                    # Continue processing but mark as non-medical

                self._record_step_performance(ProcessingStepEnum.MEDICAL_VALIDATION, time.time() - step_start)
                results["steps_completed"].append("medical_validation")
                results["step_results"]["medical_validation"] = is_medical

            # Step 2: Classification (Universal)
            if self._is_step_enabled(ProcessingStepEnum.CLASSIFICATION):
                step_start = time.time()
                classification_result = await self._execute_universal_step(
                    ProcessingStepEnum.CLASSIFICATION,
                    current_text,
                    universal_prompts.classification_prompt,
                    processing_id
                )

                # Parse classification result to determine document type
                detected_document_type = self._parse_classification_result(classification_result)
                results["document_type"] = detected_document_type.value if detected_document_type else None

                self._record_step_performance(ProcessingStepEnum.CLASSIFICATION, time.time() - step_start)
                results["steps_completed"].append("classification")
                results["step_results"]["classification"] = classification_result

            # Step 3: Preprocessing (Universal)
            if self._is_step_enabled(ProcessingStepEnum.PREPROCESSING):
                step_start = time.time()
                preprocessed_text = await self._execute_universal_step(
                    ProcessingStepEnum.PREPROCESSING,
                    current_text,
                    universal_prompts.preprocessing_prompt,
                    processing_id
                )

                current_text = preprocessed_text
                self._record_step_performance(ProcessingStepEnum.PREPROCESSING, time.time() - step_start)
                results["steps_completed"].append("preprocessing")
                results["step_results"]["preprocessing"] = "Personal data removed"
                results["final_text"] = current_text

            # Phase 2: Document-Specific Processing Steps
            if detected_document_type:
                logger.info(f"📋 Phase 2: Document-specific processing for {detected_document_type.value}")

                # Load document-specific prompts
                doc_prompts = await self._get_document_specific_prompts(detected_document_type)

                # Steps that can run in parallel (fact_check + translation)
                if enable_parallel_processing:
                    parallel_tasks = []

                    # Step 4: Translation (Document-specific)
                    if self._is_step_enabled(ProcessingStepEnum.TRANSLATION):
                        parallel_tasks.append(
                            self._execute_document_specific_step(
                                ProcessingStepEnum.TRANSLATION,
                                current_text,
                                doc_prompts.translation_prompt,
                                detected_document_type,
                                processing_id
                            )
                        )

                    # Step 5: Fact Check (Document-specific) - can run in parallel with translation
                    if self._is_step_enabled(ProcessingStepEnum.FACT_CHECK):
                        parallel_tasks.append(
                            self._execute_document_specific_step(
                                ProcessingStepEnum.FACT_CHECK,
                                current_text,
                                doc_prompts.fact_check_prompt,
                                detected_document_type,
                                processing_id
                            )
                        )

                    if parallel_tasks:
                        parallel_results = await asyncio.gather(*parallel_tasks, return_exceptions=True)

                        # Process parallel results
                        if len(parallel_results) >= 1 and not isinstance(parallel_results[0], Exception):
                            current_text = parallel_results[0]  # Use translation result
                            results["steps_completed"].append("translation")
                            results["step_results"]["translation"] = "Completed"
                            results["final_text"] = current_text

                        if len(parallel_results) >= 2 and not isinstance(parallel_results[1], Exception):
                            results["steps_completed"].append("fact_check")
                            results["step_results"]["fact_check"] = "Completed"

                # Step 6: Grammar Check (Universal)
                if self._is_step_enabled(ProcessingStepEnum.GRAMMAR_CHECK):
                    step_start = time.time()
                    grammar_checked_text = await self._execute_universal_step(
                        ProcessingStepEnum.GRAMMAR_CHECK,
                        current_text,
                        universal_prompts.grammar_check_prompt,
                        processing_id
                    )

                    current_text = grammar_checked_text
                    self._record_step_performance(ProcessingStepEnum.GRAMMAR_CHECK, time.time() - step_start)
                    results["steps_completed"].append("grammar_check")
                    results["step_results"]["grammar_check"] = "Grammar corrected"
                    results["final_text"] = current_text

                # Step 7: Final Check (Document-specific)
                if self._is_step_enabled(ProcessingStepEnum.FINAL_CHECK):
                    step_start = time.time()
                    final_checked_text = await self._execute_document_specific_step(
                        ProcessingStepEnum.FINAL_CHECK,
                        current_text,
                        doc_prompts.final_check_prompt,
                        detected_document_type,
                        processing_id
                    )

                    current_text = final_checked_text
                    self._record_step_performance(ProcessingStepEnum.FINAL_CHECK, time.time() - step_start)
                    results["steps_completed"].append("final_check")
                    results["step_results"]["final_check"] = "Quality check completed"
                    results["final_text"] = current_text

                # Step 8: Formatting (Document-specific)
                if self._is_step_enabled(ProcessingStepEnum.FORMATTING):
                    step_start = time.time()
                    formatted_text = await self._execute_document_specific_step(
                        ProcessingStepEnum.FORMATTING,
                        current_text,
                        doc_prompts.formatting_prompt,
                        detected_document_type,
                        processing_id
                    )

                    current_text = formatted_text
                    self._record_step_performance(ProcessingStepEnum.FORMATTING, time.time() - step_start)
                    results["steps_completed"].append("formatting")
                    results["step_results"]["formatting"] = "Text formatted"
                    results["final_text"] = current_text

            # Phase 3: Optional Language Translation (Universal)
            if target_language.lower() != "german" and self._is_step_enabled(ProcessingStepEnum.LANGUAGE_TRANSLATION):
                step_start = time.time()
                language_prompt = universal_prompts.language_translation_prompt.replace("{language}", target_language)
                translated_text = await self._execute_universal_step(
                    ProcessingStepEnum.LANGUAGE_TRANSLATION,
                    current_text,
                    language_prompt,
                    processing_id
                )

                current_text = translated_text
                self._record_step_performance(ProcessingStepEnum.LANGUAGE_TRANSLATION, time.time() - step_start)
                results["steps_completed"].append("language_translation")
                results["step_results"]["language_translation"] = f"Translated to {target_language}"
                results["final_text"] = current_text

            # Final results
            total_time = time.time() - start_time
            results["performance_metrics"] = {
                "total_processing_time_seconds": total_time,
                "steps_performance": self._step_performance,
                "cache_utilization": self._get_cache_stats(),
                "pipeline_efficiency": len(results["steps_completed"]) / total_time if total_time > 0 else 0
            }

            logger.info(f"✅ Pipeline V2 processing completed: {processing_id} in {total_time:.2f}s")
            return results

        except Exception as e:
            logger.error(f"❌ Pipeline V2 processing failed: {processing_id} - {e}")
            return {
                "processing_id": processing_id,
                "error": str(e),
                "pipeline_version": "v2_optimized",
                "steps_completed": results.get("steps_completed", []) if 'results' in locals() else [],
                "final_text": current_text if 'current_text' in locals() else text
            }

    async def _execute_universal_step(
        self,
        step: ProcessingStepEnum,
        text: str,
        prompt: str,
        processing_id: str
    ) -> str:
        """Execute a universal pipeline step"""
        logger.info(f"🔄 Executing universal step: {step.value}")

        try:
            result = await self.ovh_client.process_medical_text(
                text=text,
                instruction=prompt,
                temperature=0.3,
                max_tokens=2000
            )

            # Log interaction
            await self.ai_logger.log_interaction(
                processing_id=processing_id,
                step_name=step,
                input_text=text,
                output_text=result,
                prompt_used=prompt,
                model_used=self.ovh_client.main_model,
                processing_time_ms=0  # Will be calculated by caller
            )

            return result.strip()

        except Exception as e:
            logger.error(f"Universal step {step.value} failed: {e}")
            return text  # Fallback to original text

    async def _execute_document_specific_step(
        self,
        step: ProcessingStepEnum,
        text: str,
        prompt: str,
        document_type: DocumentClass,
        processing_id: str
    ) -> str:
        """Execute a document-specific pipeline step"""
        logger.info(f"📋 Executing document-specific step: {step.value} for {document_type.value}")

        try:
            result = await self.ovh_client.process_medical_text(
                text=text,
                instruction=prompt,
                temperature=0.3,
                max_tokens=2000
            )

            # Log interaction
            await self.ai_logger.log_interaction(
                processing_id=processing_id,
                step_name=step,
                document_type=document_type,
                input_text=text,
                output_text=result,
                prompt_used=prompt,
                model_used=self.ovh_client.main_model,
                processing_time_ms=0  # Will be calculated by caller
            )

            return result.strip()

        except Exception as e:
            logger.error(f"Document-specific step {step.value} failed: {e}")
            return text  # Fallback to original text

    async def _get_universal_prompts(self) -> UniversalPrompts:
        """Get universal prompts with caching"""
        if (self._universal_prompts_cache is None or
            datetime.now() - self._last_cache_update > self._cache_timeout):

            # In a real implementation, this would load from database
            # For now, use the defaults from the JSON file
            self._universal_prompts_cache = UniversalPrompts(
                medical_validation_prompt="Analysiere diesen Text und bestimme, ob er medizinischen Inhalt enthält.\n\nKRITERIEN FÜR MEDIZINISCHEN INHALT:\n- Diagnosen oder Symptome\n- Medizinische Fachbegriffe\n- Behandlungen oder Therapien\n- Medikamente oder Dosierungen\n- Laborwerte oder Messwerte\n- Medizinische Abkürzungen\n- Anatomische Begriffe\n\nAntworte NUR mit: MEDIZINISCH oder NICHT_MEDIZINISCH",
                classification_prompt="Analysiere diesen medizinischen Text und klassifiziere ihn als: ARZTBRIEF (Kommunikation zwischen Ärzten), BEFUNDBERICHT (Untersuchungsergebnisse), oder LABORWERTE (Messwerte mit Referenzbereichen). Antworte mit der Kategorie.",
                preprocessing_prompt="Entferne alle persönlichen Daten aus diesem medizinischen Text, behalte aber ALLE medizinischen Informationen. Entferne: Namen, Adressen, Geburtsdaten, IDs. Behalte: Alle Diagnosen, Werte, Behandlungen, Medikamente.",
                grammar_check_prompt="Korrigiere Grammatik und Rechtschreibung in diesem deutschen Text. Ändere keine medizinischen Informationen.",
                language_translation_prompt="Übersetze diesen Text in {language}. Behalte alle Formatierungen und medizinischen Informationen exakt bei."
            )
            self._last_cache_update = datetime.now()

        return self._universal_prompts_cache

    async def _get_document_specific_prompts(self, document_type: DocumentClass) -> DocumentSpecificPrompts:
        """Get document-specific prompts with caching"""
        if document_type not in self._document_prompts_cache:

            # Document-specific prompt variations
            if document_type == DocumentClass.ARZTBRIEF:
                prompts = DocumentSpecificPrompts(
                    document_type=document_type,
                    translation_prompt="Übersetze diesen Arztbrief in einfache, patientenfreundliche Sprache. Erkläre komplexe medizinische Diagnosen und Behandlungen verständlich. Verwende 'Sie' und sprechen Sie den Patienten direkt an.",
                    fact_check_prompt="Prüfe diesen Arztbrief auf medizinische Korrektheit. Achte besonders auf Diagnose-Behandlung Konsistenz und korrekte medizinische Terminologie.",
                    final_check_prompt="Finale Kontrolle des Arztbriefs: Prüfe Vollständigkeit, medizinische Genauigkeit und Verständlichkeit für Patienten.",
                    formatting_prompt="Formatiere diesen Arztbrief mit klaren Abschnitten: 📋 Diagnose, 💊 Behandlung, 📅 Termine, ⚠️ Wichtige Hinweise."
                )
            elif document_type == DocumentClass.LABORWERTE:
                prompts = DocumentSpecificPrompts(
                    document_type=document_type,
                    translation_prompt="Erkläre diese Laborwerte in einfacher Sprache. Beschreibe was jeder Wert bedeutet, ob er normal ist, und was Abweichungen bedeuten könnten.",
                    fact_check_prompt="Prüfe Laborwerte auf Plausibilität. Kontrolliere Referenzbereiche und identifiziere ungewöhnliche Werte.",
                    final_check_prompt="Finale Kontrolle der Laborwerte: Sind alle Werte erklärt und Referenzbereiche korrekt dargestellt?",
                    formatting_prompt="Formatiere Laborwerte übersichtlich: 🧪 Wert | 📊 Referenzbereich | ✅/⚠️ Bewertung | 💡 Bedeutung."
                )
            else:  # BEFUNDBERICHT
                prompts = DocumentSpecificPrompts(
                    document_type=document_type,
                    translation_prompt="Übersetze diesen Befundbericht in verständliche Patientensprache. Erkläre medizinische Befunde, Untersuchungsmethoden und deren Bedeutung.",
                    fact_check_prompt="Prüfe den Befundbericht auf medizinische Genauigkeit. Kontrolliere Untersuchungsverfahren und Befundinterpretationen.",
                    final_check_prompt="Finale Kontrolle des Befundberichts: Sind alle Untersuchungsergebnisse verständlich erklärt?",
                    formatting_prompt="Formatiere den Befundbericht: 🔬 Untersuchung | 🎯 Befund | 📝 Bedeutung | 👨‍⚕️ Empfehlungen."
                )

            self._document_prompts_cache[document_type] = prompts

        return self._document_prompts_cache[document_type]

    def _parse_classification_result(self, classification_result: str) -> Optional[DocumentClass]:
        """Parse classification result to determine document type"""
        result_upper = classification_result.upper().strip()

        if "ARZTBRIEF" in result_upper:
            return DocumentClass.ARZTBRIEF
        elif "LABORWERTE" in result_upper or "LABOR" in result_upper:
            return DocumentClass.LABORWERTE
        elif "BEFUNDBERICHT" in result_upper or "BEFUND" in result_upper:
            return DocumentClass.BEFUNDBERICHT

        # Fallback to ARZTBRIEF if unclear
        logger.warning(f"Could not parse classification result: {classification_result}, defaulting to ARZTBRIEF")
        return DocumentClass.ARZTBRIEF

    def _is_step_enabled(self, step: ProcessingStepEnum) -> bool:
        """Check if a pipeline step is enabled"""
        # In a real implementation, this would check the database configuration
        # For now, all steps are enabled by default
        step_config = next((s for s in self._pipeline_steps if s.name == step), None)
        return step_config.enabled if step_config else True

    def _record_step_performance(self, step: ProcessingStepEnum, duration_seconds: float):
        """Record performance metrics for a step"""
        if step.value not in self._step_performance:
            self._step_performance[step.value] = {
                "total_executions": 0,
                "total_duration_seconds": 0,
                "average_duration_seconds": 0,
                "last_execution_seconds": 0
            }

        perf = self._step_performance[step.value]
        perf["total_executions"] += 1
        perf["total_duration_seconds"] += duration_seconds
        perf["average_duration_seconds"] = perf["total_duration_seconds"] / perf["total_executions"]
        perf["last_execution_seconds"] = duration_seconds

    def _get_cache_stats(self) -> Dict[str, Any]:
        """Get cache utilization statistics"""
        return {
            "universal_prompts_cached": self._universal_prompts_cache is not None,
            "document_prompts_cached": len(self._document_prompts_cache),
            "cache_age_minutes": (datetime.now() - self._last_cache_update).total_seconds() / 60,
            "cache_timeout_minutes": self._cache_timeout.total_seconds() / 60
        }

    async def get_pipeline_statistics(self) -> Dict[str, Any]:
        """Get comprehensive pipeline statistics"""
        return {
            "pipeline_version": "v2_optimized",
            "universal_steps": len([s for s in self._pipeline_steps if s.is_universal]),
            "document_specific_steps": len([s for s in self._pipeline_steps if not s.is_universal]),
            "enabled_steps": len([s for s in self._pipeline_steps if s.enabled]),
            "performance_metrics": self._step_performance,
            "cache_statistics": self._get_cache_stats(),
            "pipeline_flow": [
                {
                    "step": step.name.value,
                    "is_universal": step.is_universal,
                    "enabled": step.enabled,
                    "order": step.order,
                    "description": step.description
                }
                for step in self._pipeline_steps
            ]
        }