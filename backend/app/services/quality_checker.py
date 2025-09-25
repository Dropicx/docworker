import logging
import re
from typing import Tuple, Optional, Dict, Any
from app.models.document_types import DocumentClass

logger = logging.getLogger(__name__)

class QualityChecker:
    """
    Service for checking the quality of translated medical documents.
    Performs fact checking, grammar checking, and formatting validation.
    """

    def __init__(self, ovh_client=None):
        """
        Initialize the quality checker.

        Args:
            ovh_client: OVH client for AI-based checking
        """
        self.ovh_client = ovh_client

    async def fact_check(
        self,
        text: str,
        document_type: DocumentClass,
        fact_check_prompt: Optional[str] = None
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Check medical facts in the translated text.

        Args:
            text: The text to fact-check
            document_type: The document type
            fact_check_prompt: Custom prompt or None to use default

        Returns:
            Tuple of (checked_text, check_results)
        """
        logger.info(f"Starting fact check for {document_type.value}")

        if not self.ovh_client:
            logger.warning("OVH client not available for fact checking")
            return text, {"status": "skipped", "reason": "No AI client available"}

        try:
            # Use custom prompt or create default
            if not fact_check_prompt:
                fact_check_prompt = self._get_default_fact_check_prompt(document_type)

            # Replace placeholder in prompt
            prompt = fact_check_prompt.replace("{text}", text)

            # Perform fact check using OVH
            checked_text = await self.ovh_client.process_medical_text(
                text=text,
                instruction=prompt,
                temperature=0.1,  # Very low temperature for accuracy
                max_tokens=4000
            )

            # Analyze changes
            changes = self._analyze_changes(text, checked_text)

            logger.info(f"✅ Fact check completed: {changes['change_count']} changes made")

            return checked_text, {
                "status": "completed",
                "changes": changes,
                "document_type": document_type.value
            }

        except Exception as e:
            logger.error(f"Fact check failed: {e}")
            return text, {"status": "error", "error": str(e)}

    async def grammar_check(
        self,
        text: str,
        language: str = "de",
        grammar_check_prompt: Optional[str] = None
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Check and correct grammar in the text.

        Args:
            text: The text to check
            language: Language code (default: German)
            grammar_check_prompt: Custom prompt or None to use default

        Returns:
            Tuple of (corrected_text, check_results)
        """
        logger.info(f"Starting grammar check for language: {language}")

        if not self.ovh_client:
            logger.warning("OVH client not available for grammar checking")
            return text, {"status": "skipped", "reason": "No AI client available"}

        try:
            # Use custom prompt or create default
            if not grammar_check_prompt:
                grammar_check_prompt = self._get_default_grammar_prompt(language)

            # Replace placeholder in prompt
            prompt = grammar_check_prompt.replace("{text}", text)

            # Perform grammar check using OVH
            corrected_text = await self.ovh_client.process_medical_text(
                text=text,
                instruction=prompt,
                temperature=0.2,  # Low temperature for consistency
                max_tokens=4000
            )

            # Analyze changes
            changes = self._analyze_changes(text, corrected_text)

            logger.info(f"✅ Grammar check completed: {changes['change_count']} corrections")

            return corrected_text, {
                "status": "completed",
                "language": language,
                "changes": changes
            }

        except Exception as e:
            logger.error(f"Grammar check failed: {e}")
            return text, {"status": "error", "error": str(e)}

    async def final_quality_check(
        self,
        text: str,
        document_type: DocumentClass,
        final_check_prompt: Optional[str] = None
    ) -> Tuple[str, float]:
        """
        Perform final quality check and scoring.

        Args:
            text: The text to check
            document_type: The document type
            final_check_prompt: Custom prompt or None to use default

        Returns:
            Tuple of (final_text, quality_score)
        """
        logger.info(f"Starting final quality check for {document_type.value}")

        quality_score = 0.0

        # Basic quality metrics (can be done without AI)
        quality_metrics = self._calculate_quality_metrics(text)
        base_score = quality_metrics["base_score"]

        if not self.ovh_client:
            logger.warning("OVH client not available for final check")
            return text, base_score

        try:
            # Use custom prompt or create default
            if not final_check_prompt:
                final_check_prompt = self._get_default_final_prompt(document_type)

            # Replace placeholder in prompt
            prompt = final_check_prompt.replace("{text}", text)

            # Perform final check using OVH
            final_text = await self.ovh_client.process_medical_text(
                text=text,
                instruction=prompt,
                temperature=0.3,
                max_tokens=4000
            )

            # Calculate final quality score
            ai_improvements = self._analyze_changes(text, final_text)

            # Combine scores
            if ai_improvements["change_count"] > 0:
                # Small improvements boost score
                quality_score = min(base_score + 0.1, 1.0)
            else:
                # No changes needed = good quality
                quality_score = min(base_score + 0.15, 1.0)

            logger.info(f"✅ Final quality check completed: score={quality_score:.2%}")

            return final_text, quality_score

        except Exception as e:
            logger.error(f"Final quality check failed: {e}")
            return text, base_score

    def _analyze_changes(self, original: str, modified: str) -> Dict[str, Any]:
        """
        Analyze changes between original and modified text.

        Args:
            original: Original text
            modified: Modified text

        Returns:
            Dictionary with change analysis
        """
        changes = {
            "change_count": 0,
            "length_diff": len(modified) - len(original),
            "significant_change": False
        }

        # Simple change detection
        if original != modified:
            # Count line differences
            original_lines = original.split('\n')
            modified_lines = modified.split('\n')

            # Count changed lines
            max_lines = max(len(original_lines), len(modified_lines))
            changed_lines = 0

            for i in range(max_lines):
                orig_line = original_lines[i] if i < len(original_lines) else ""
                mod_line = modified_lines[i] if i < len(modified_lines) else ""

                if orig_line != mod_line:
                    changed_lines += 1

            changes["change_count"] = changed_lines
            changes["significant_change"] = changed_lines > 5 or abs(changes["length_diff"]) > 100

        return changes

    def _calculate_quality_metrics(self, text: str) -> Dict[str, Any]:
        """
        Calculate basic quality metrics without AI.

        Args:
            text: The text to analyze

        Returns:
            Dictionary with quality metrics
        """
        metrics = {
            "length": len(text),
            "has_structure": False,
            "has_sections": False,
            "has_formatting": False,
            "base_score": 0.5
        }

        # Check for structure elements
        if "##" in text or "#" in text:
            metrics["has_sections"] = True
            metrics["base_score"] += 0.1

        # Check for formatting elements
        if any(marker in text for marker in ["→", "•", "-", "**", "📋", "🎯", "✅"]):
            metrics["has_formatting"] = True
            metrics["base_score"] += 0.1

        # Check for proper length
        if 500 <= metrics["length"] <= 5000:
            metrics["base_score"] += 0.1

        # Check for structure
        if text.count('\n') > 10:
            metrics["has_structure"] = True
            metrics["base_score"] += 0.1

        # Check for patient-friendly indicators
        patient_friendly_terms = ["Sie", "Ihr", "Ihnen", "bedeutet", "heißt das", "einfach"]
        friendly_count = sum(1 for term in patient_friendly_terms if term in text)
        if friendly_count >= 3:
            metrics["base_score"] += 0.1

        # Cap at 1.0
        metrics["base_score"] = min(metrics["base_score"], 1.0)

        return metrics

    def _get_default_fact_check_prompt(self, document_type: DocumentClass) -> str:
        """Get default fact check prompt based on document type."""

        if document_type == DocumentClass.LABORWERTE:
            return """Prüfe diese Laborwerte auf Korrektheit:
1. Stimmen alle Zahlen und Einheiten?
2. Sind Referenzbereiche korrekt?
3. Ist die Bewertung (hoch/niedrig/normal) richtig?

Korrigiere NUR faktische Fehler. Behalte die Formatierung.

TEXT:
{text}

KORRIGIERTER TEXT:"""

        elif document_type == DocumentClass.BEFUNDBERICHT:
            return """Prüfe diesen Befundbericht auf medizinische Korrektheit:
1. Sind anatomische Begriffe richtig?
2. Stimmen Größenangaben und Lokalisationen?
3. Sind medizinische Begriffe korrekt erklärt?

Korrigiere NUR Fehler. Behalte die verständliche Sprache.

TEXT:
{text}

KORRIGIERTER TEXT:"""

        else:  # ARZTBRIEF
            return """Prüfe diesen Arztbrief auf Korrektheit:
1. Stimmen Medikamentendosierungen?
2. Sind Diagnosen korrekt wiedergegeben?
3. Stimmen Termine und Empfehlungen?

Korrigiere NUR faktische Fehler.

TEXT:
{text}

KORRIGIERTER TEXT:"""

    def _get_default_grammar_prompt(self, language: str) -> str:
        """Get default grammar check prompt."""

        if language == "de":
            return """Korrigiere NUR Grammatik- und Rechtschreibfehler in diesem deutschen Text.
Ändere NICHT:
- Medizinische Informationen
- Formatierung
- Zahlen und Einheiten

TEXT:
{text}

KORRIGIERTER TEXT:"""

        else:
            return f"""Correct ONLY grammar and spelling in this {language} text.
Do NOT change:
- Medical information
- Formatting
- Numbers and units

TEXT:
{{text}}

CORRECTED TEXT:"""

    def _get_default_final_prompt(self, document_type: DocumentClass) -> str:
        """Get default final quality check prompt."""

        return """Finale Qualitätskontrolle:
1. Ist der Text für Patienten verständlich?
2. Sind alle wichtigen Informationen vorhanden?
3. Gibt es noch unverständliche Fachbegriffe?
4. Ist die Formatierung klar?

Optimiere NUR die Verständlichkeit. Ändere keine medizinischen Fakten.

TEXT:
{text}

FINALER TEXT:"""