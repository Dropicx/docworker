"""
Feedback Analysis Service

AI-powered quality analysis for user feedback.
Compares OCR text → PII-anonymized text → final translation to identify:
- PII leaks (personal data not properly anonymized)
- Translation quality issues
- Optimization recommendations

Uses Mistral Large for analysis.
"""

import json
import logging
import re
import time
from datetime import datetime

from sqlalchemy.orm import Session

from app.database.modular_pipeline_models import FeedbackAnalysisStatus
from app.repositories.feedback_repository import FeedbackRepository
from app.repositories.pipeline_step_execution_repository import PipelineStepExecutionRepository
from app.repositories.pipeline_job_repository import PipelineJobRepository
from app.services.ai_cost_tracker import AICostTracker
from app.services.mistral_client import MistralClient

logger = logging.getLogger(__name__)


# AI Prompt for quality analysis
ANALYSIS_SYSTEM_PROMPT = """You are a medical translation quality analyst. Your task is to analyze the quality and privacy compliance of German medical document translations.

You will receive:
1. Original OCR text (German)
2. Text after PII anonymization (placeholders like [NAME], [ADDRESS], etc.)
3. Final patient-friendly translation

Analyze for:
1. **PII Leak Check**: Compare original with anonymized text. List any personal names, addresses, phone numbers, emails, birthdates, insurance numbers, or other identifiers that were NOT properly anonymized.
2. **Translation Quality**: Evaluate the patient-friendly translation for medical accuracy, completeness, clarity, and formatting.
3. **Recommendations**: Suggest improvements for the translation pipeline.

IMPORTANT: Respond ONLY with valid JSON in the exact format below. No additional text before or after the JSON.
"""

ANALYSIS_USER_PROMPT = """Analyze this medical document translation:

## Original OCR Text (German):
{original_text}

## After PII Anonymization:
{pii_text}

## Final Patient-Friendly Translation:
{translated_text}

Respond with this exact JSON structure:
{{
  "pii_issues": ["List each PII that leaked through anonymization. Leave empty [] if none found."],
  "translation_issues": ["List translation quality issues. Leave empty [] if translation is good."],
  "recommendations": ["List improvement suggestions for the pipeline."],
  "overall_quality_score": 8,
  "detailed_analysis": "Full paragraph analysis explaining your findings..."
}}"""


class FeedbackAnalysisService:
    """
    Service for AI-powered feedback quality analysis.

    Retrieves processing data, sends to Mistral Large for analysis,
    and stores results in the feedback record.
    """

    def __init__(self, db: Session):
        """
        Initialize the analysis service.

        Args:
            db: Database session
        """
        self.db = db
        self.feedback_repo = FeedbackRepository(db)
        self.step_execution_repo = PipelineStepExecutionRepository(db)
        self.job_repo = PipelineJobRepository(db)
        self.cost_tracker = AICostTracker(db)
        self._mistral_client = None

    @property
    def mistral_client(self) -> MistralClient:
        """Lazy initialization of Mistral client."""
        if self._mistral_client is None:
            self._mistral_client = MistralClient()
        return self._mistral_client

    def get_processing_texts(self, processing_id: str) -> dict | None:
        """
        Get the texts needed for analysis from a processing job.

        Retrieves:
        - Original OCR text (from TEXT_EXTRACTION step or job result)
        - PII-anonymized text (from PII_PREPROCESSING step)
        - Final translated text (from job result)

        Args:
            processing_id: Processing job ID

        Returns:
            Dict with {original_text, pii_text, translated_text} or None if not found
        """
        # Get the job
        job = self.job_repo.get_by_processing_id(processing_id)
        if not job:
            logger.warning(f"Job not found for processing_id: {processing_id}")
            return None

        # Check if content is available
        if not job.result_data:
            logger.warning(f"No result_data for processing_id: {processing_id}")
            return None

        result_data = job.result_data

        # Get original and translated text from result_data
        original_text = result_data.get("original_text", "")
        translated_text = result_data.get("translated_text", "")

        if not original_text or not translated_text:
            logger.warning(f"Missing text content for processing_id: {processing_id}")
            return None

        # Check if content was cleared (GDPR)
        if original_text == "[Content cleared - GDPR]":
            logger.info(f"Content cleared for processing_id: {processing_id}")
            return None

        # Get PII-anonymized text from step executions
        # Look for the PII preprocessing step output
        step_executions = self.step_execution_repo.get_by_job_id(job.job_id)

        pii_text = None
        for step in step_executions:
            # Look for PII-related step names
            if any(keyword in step.step_name.lower() for keyword in ["pii", "privacy", "datenschutz", "anonym"]):
                # The input to the next step after PII removal is the anonymized text
                pii_text = step.output_text
                break

        # If no dedicated PII step found, check for text extraction output
        # (which would be the text after PII removal if done as preprocessing)
        if not pii_text:
            for step in step_executions:
                if any(keyword in step.step_name.lower() for keyword in ["extraction", "ocr", "text"]):
                    pii_text = step.output_text
                    break

        # Fallback: use the original text from result (which should be post-PII)
        if not pii_text:
            pii_text = original_text

        return {
            "original_text": original_text,
            "pii_text": pii_text,
            "translated_text": translated_text,
        }

    def build_analysis_prompt(
        self, original_text: str, pii_text: str, translated_text: str
    ) -> str:
        """
        Build the AI prompt for quality analysis.

        Args:
            original_text: Original OCR-extracted text
            pii_text: Text after PII anonymization
            translated_text: Final patient-friendly translation

        Returns:
            Formatted prompt string
        """
        # Truncate texts if too long to avoid token limits
        max_chars = 8000  # ~2000 tokens per text section

        def truncate(text: str, max_len: int) -> str:
            if len(text) > max_len:
                return text[:max_len] + "\n\n[... truncated for analysis ...]"
            return text

        return ANALYSIS_USER_PROMPT.format(
            original_text=truncate(original_text, max_chars),
            pii_text=truncate(pii_text, max_chars),
            translated_text=truncate(translated_text, max_chars),
        )

    def parse_analysis_response(self, response_text: str) -> dict:
        """
        Parse the AI response into structured format.

        Args:
            response_text: Raw response from Mistral

        Returns:
            Parsed analysis dict with pii_issues, translation_issues, recommendations, quality_score
        """
        # Try to extract JSON from the response
        try:
            # First try direct JSON parse
            return json.loads(response_text)
        except json.JSONDecodeError:
            pass

        # Try to find JSON in the response (may have extra text)
        try:
            # Look for JSON object pattern
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                return json.loads(json_match.group())
        except (json.JSONDecodeError, AttributeError):
            pass

        # Fallback: return error structure
        logger.warning(f"Failed to parse AI response as JSON: {response_text[:500]}...")
        return {
            "pii_issues": [],
            "translation_issues": ["Failed to parse AI analysis response"],
            "recommendations": ["Check AI response format"],
            "overall_quality_score": 0,
            "detailed_analysis": f"Raw response: {response_text[:1000]}",
            "parse_error": True,
        }

    async def analyze_feedback(self, feedback_id: int) -> dict:
        """
        Perform AI analysis for a feedback entry.

        Args:
            feedback_id: Feedback entry ID

        Returns:
            Analysis result dict with status and analysis data
        """
        logger.info(f"Starting AI analysis for feedback ID: {feedback_id}")

        # Get the feedback entry
        feedback = self.feedback_repo.get_by_id(feedback_id)
        if not feedback:
            logger.error(f"Feedback not found: {feedback_id}")
            return {"status": "error", "message": "Feedback not found"}

        # Check if consent was given
        if not feedback.data_consent_given:
            logger.info(f"No consent for feedback {feedback_id}, skipping analysis")
            self.feedback_repo.update_analysis_result(
                feedback_id=feedback_id,
                status=FeedbackAnalysisStatus.SKIPPED,
                error_message="User did not consent to data usage",
            )
            return {"status": "skipped", "message": "No consent"}

        # Mark as processing
        self.feedback_repo.update_analysis_status(
            feedback_id=feedback_id,
            status=FeedbackAnalysisStatus.PROCESSING,
            started_at=datetime.now(),
        )

        try:
            # Get processing texts
            texts = self.get_processing_texts(feedback.processing_id)
            if not texts:
                logger.warning(f"No texts available for feedback {feedback_id}")
                self.feedback_repo.update_analysis_result(
                    feedback_id=feedback_id,
                    status=FeedbackAnalysisStatus.SKIPPED,
                    error_message="Processing content not available (may have been cleared)",
                )
                return {"status": "skipped", "message": "Content not available"}

            # Build prompt
            prompt = self.build_analysis_prompt(
                original_text=texts["original_text"],
                pii_text=texts["pii_text"],
                translated_text=texts["translated_text"],
            )

            # Add system context
            full_prompt = f"{ANALYSIS_SYSTEM_PROMPT}\n\n{prompt}"

            # Call Mistral Large
            logger.info(f"Calling Mistral Large for feedback {feedback_id}")
            start_time = time.time()
            response = await self.mistral_client.process_text(
                prompt=full_prompt,
                model="mistral-large-latest",
                temperature=0.3,  # Lower temperature for more consistent analysis
                max_tokens=2000,
            )
            processing_time = time.time() - start_time

            # Log cost for feedback analysis
            self.cost_tracker.log_ai_call(
                processing_id=f"feedback_{feedback_id}",
                step_name="FEEDBACK_ANALYSIS",
                input_tokens=response.get("input_tokens", 0),
                output_tokens=response.get("output_tokens", 0),
                model_provider="MISTRAL",
                model_name="mistral-large-latest",
                processing_time_seconds=processing_time,
                document_type="FEEDBACK",
                metadata={"feedback_id": feedback_id},
            )
            logger.info(
                f"Cost logged for feedback {feedback_id}: "
                f"input={response.get('input_tokens', 0)}, "
                f"output={response.get('output_tokens', 0)}, "
                f"time={processing_time:.2f}s"
            )

            # Parse response
            analysis = self.parse_analysis_response(response["content"])

            # Build summary (subset of analysis for quick display)
            summary = {
                "pii_issues": analysis.get("pii_issues", []),
                "translation_issues": analysis.get("translation_issues", []),
                "recommendations": analysis.get("recommendations", []),
                "overall_quality_score": analysis.get("overall_quality_score", 0),
            }

            # Store result
            self.feedback_repo.update_analysis_result(
                feedback_id=feedback_id,
                status=FeedbackAnalysisStatus.COMPLETED,
                analysis_text=analysis.get("detailed_analysis", response["content"]),
                analysis_summary=summary,
            )

            logger.info(
                f"Analysis completed for feedback {feedback_id}: "
                f"score={summary['overall_quality_score']}, "
                f"pii_issues={len(summary['pii_issues'])}, "
                f"translation_issues={len(summary['translation_issues'])}"
            )

            return {
                "status": "completed",
                "summary": summary,
                "tokens_used": response.get("input_tokens", 0) + response.get("output_tokens", 0),
            }

        except Exception as e:
            logger.error(f"Analysis failed for feedback {feedback_id}: {e}")
            self.feedback_repo.update_analysis_result(
                feedback_id=feedback_id,
                status=FeedbackAnalysisStatus.FAILED,
                error_message=str(e),
            )
            return {"status": "failed", "message": str(e)}
