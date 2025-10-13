import logging
from typing import Any

from app.models.document_types import (
    CLASSIFICATION_PATTERNS,
    DOCUMENT_TYPE_DESCRIPTIONS,
    DocumentClass,
    DocumentClassificationResult,
)

logger = logging.getLogger(__name__)

class DocumentClassifier:
    """
    Service for classifying medical documents into predefined categories.
    Uses pattern matching for fast classification, with AI fallback for uncertain cases.
    """

    def __init__(self, ovh_client=None):
        """
        Initialize the document classifier

        Args:
            ovh_client: Optional OVH client for AI-based classification
        """
        self.ovh_client = ovh_client
        self.patterns = CLASSIFICATION_PATTERNS

    async def classify_document(
        self,
        text: str,
        use_ai_fallback: bool = True
    ) -> DocumentClassificationResult:
        """
        Classify a medical document into one of the predefined categories.

        Args:
            text: The medical text to classify
            use_ai_fallback: Whether to use AI if pattern matching is uncertain

        Returns:
            DocumentClassificationResult with classification and confidence
        """
        logger.info("Starting document classification...")

        # First try pattern-based classification
        pattern_result = self._classify_by_patterns(text)

        # If confidence is high enough, return pattern result
        if pattern_result.confidence >= 0.7:
            logger.info(f"✅ Pattern classification successful: {pattern_result.document_class} (confidence: {pattern_result.confidence:.2%})")
            return pattern_result

        # If pattern matching is uncertain and AI is available, use AI
        if use_ai_fallback and self.ovh_client:
            logger.info("Pattern matching uncertain, using AI classification...")
            ai_result = await self._classify_by_ai(text)
            if ai_result.confidence > pattern_result.confidence:
                logger.info(f"✅ AI classification: {ai_result.document_class} (confidence: {ai_result.confidence:.2%})")
                return ai_result

        # Return best result (pattern or default)
        logger.info(f"Using pattern result: {pattern_result.document_class} (confidence: {pattern_result.confidence:.2%})")
        return pattern_result

    def _classify_by_patterns(self, text: str) -> DocumentClassificationResult:
        """
        Classify document using keyword patterns.

        Args:
            text: The text to classify

        Returns:
            Classification result based on pattern matching
        """
        text_lower = text.lower()
        scores = {}

        # Calculate scores for each document type
        for doc_class, patterns in self.patterns.items():
            score = 0
            strong_matches = 0
            weak_matches = 0

            # Check strong indicators (worth more points)
            for indicator in patterns.get("strong_indicators", []):
                if indicator in text_lower:
                    strong_matches += 1
                    score += 3  # Strong indicators worth 3 points

            # Check weak indicators
            for indicator in patterns.get("weak_indicators", []):
                if indicator in text_lower:
                    weak_matches += 1
                    score += 1  # Weak indicators worth 1 point

            scores[doc_class] = {
                "total_score": score,
                "strong_matches": strong_matches,
                "weak_matches": weak_matches
            }

            logger.debug(f"Pattern matching for {doc_class}: score={score}, strong={strong_matches}, weak={weak_matches}")

        # Find the best match
        if scores:
            best_class = max(scores, key=lambda x: scores[x]["total_score"])
            best_score_data = scores[best_class]

            # Calculate confidence based on matches
            max_possible_score = (
                len(self.patterns[best_class].get("strong_indicators", [])) * 3 +
                len(self.patterns[best_class].get("weak_indicators", []))
            )

            # Base confidence on score ratio and number of strong matches
            if max_possible_score > 0:
                score_ratio = best_score_data["total_score"] / max_possible_score
                # Boost confidence if we have strong matches
                if best_score_data["strong_matches"] > 0:
                    confidence = min(0.5 + (score_ratio * 0.5) + (best_score_data["strong_matches"] * 0.1), 1.0)
                else:
                    confidence = min(score_ratio * 0.6, 0.6)  # Max 60% confidence without strong matches
            else:
                confidence = 0.3

            # Check if there's a clear winner (significant difference from second best)
            sorted_scores = sorted(scores.items(), key=lambda x: x[1]["total_score"], reverse=True)
            if len(sorted_scores) > 1:
                score_diff = sorted_scores[0][1]["total_score"] - sorted_scores[1][1]["total_score"]
                if score_diff < 2:  # Too close to call
                    confidence *= 0.7  # Reduce confidence

            return DocumentClassificationResult(
                document_class=best_class,
                confidence=confidence,
                method="pattern",
                processing_hints=self._get_processing_hints(best_class)
            )

        # Default fallback
        return DocumentClassificationResult(
            document_class=DocumentClass.ARZTBRIEF,
            confidence=0.3,
            method="pattern",
            processing_hints=self._get_processing_hints(DocumentClass.ARZTBRIEF)
        )

    async def _classify_by_ai(self, text: str) -> DocumentClassificationResult:
        """
        Classify document using AI (OVH API).

        Args:
            text: The text to classify

        Returns:
            Classification result from AI
        """
        if not self.ovh_client:
            logger.warning("OVH client not available for AI classification")
            return DocumentClassificationResult(
                document_class=DocumentClass.ARZTBRIEF,
                confidence=0.0,
                method="ai",
                processing_hints={}
            )

        try:
            # Prepare classification prompt
            classification_prompt = f"""Analysiere diesen medizinischen Text und klassifiziere ihn in EINE der folgenden Kategorien:

1. ARZTBRIEF - Briefe zwischen Ärzten, Entlassungsbriefe, Überweisungen, Konsiliarbriefe
2. BEFUNDBERICHT - Untersuchungsbefunde, Bildgebung (MRT, CT, Röntgen), Pathologie
3. LABORWERTE - Laborergebnisse, Blutwerte, Urinwerte mit Messwerten und Referenzbereichen

Antworte NUR mit einem dieser Wörter: ARZTBRIEF, BEFUNDBERICHT, oder LABORWERTE

Text zur Klassifizierung:
{text[:2000]}  # Limit text for classification

KLASSIFIZIERUNG:"""

            # Get AI classification
            result = await self.ovh_client.process_medical_text(
                text=text[:2000],  # Limit text length for classification
                instruction=classification_prompt,
                temperature=0.1,  # Low temperature for consistent classification
                max_tokens=10  # We only need one word
            )

            # Parse AI response
            result_clean = result.strip().upper()

            # Map to DocumentClass
            if "ARZTBRIEF" in result_clean:
                doc_class = DocumentClass.ARZTBRIEF
                confidence = 0.9
            elif "BEFUNDBERICHT" in result_clean:
                doc_class = DocumentClass.BEFUNDBERICHT
                confidence = 0.9
            elif "LABORWERTE" in result_clean or "LABOR" in result_clean:
                doc_class = DocumentClass.LABORWERTE
                confidence = 0.9
            else:
                # AI gave unclear response, default with low confidence
                logger.warning(f"AI classification unclear: {result_clean}")
                doc_class = DocumentClass.ARZTBRIEF
                confidence = 0.5

            return DocumentClassificationResult(
                document_class=doc_class,
                confidence=confidence,
                method="ai",
                processing_hints=self._get_processing_hints(doc_class)
            )

        except Exception as e:
            logger.error(f"AI classification failed: {e}")
            return DocumentClassificationResult(
                document_class=DocumentClass.ARZTBRIEF,
                confidence=0.3,
                method="ai",
                processing_hints={}
            )

    def _get_processing_hints(self, doc_class: DocumentClass) -> dict[str, Any]:
        """
        Get processing hints based on document class.

        Args:
            doc_class: The document class

        Returns:
            Dictionary with processing hints
        """
        hints = {
            "document_info": DOCUMENT_TYPE_DESCRIPTIONS.get(doc_class, {}),
            "focus_areas": [],
            "special_handling": []
        }

        if doc_class == DocumentClass.ARZTBRIEF:
            hints["focus_areas"] = [
                "treatment_recommendations",
                "medication_changes",
                "follow_up_appointments",
                "diagnoses"
            ]
            hints["special_handling"] = [
                "preserve_doctor_recommendations",
                "highlight_patient_actions"
            ]

        elif doc_class == DocumentClass.BEFUNDBERICHT:
            hints["focus_areas"] = [
                "examination_findings",
                "abnormalities",
                "size_descriptions",
                "follow_up_examinations"
            ]
            hints["special_handling"] = [
                "use_visual_comparisons",
                "explain_medical_imaging_terms"
            ]

        elif doc_class == DocumentClass.LABORWERTE:
            hints["focus_areas"] = [
                "abnormal_values",
                "reference_ranges",
                "trends",
                "critical_values"
            ]
            hints["special_handling"] = [
                "preserve_all_numbers",
                "maintain_table_structure",
                "use_color_coding_analogies"
            ]

        return hints

    def get_document_type_info(self, doc_class: DocumentClass) -> dict[str, Any]:
        """
        Get information about a document type.

        Args:
            doc_class: The document class

        Returns:
            Information dictionary
        """
        return DOCUMENT_TYPE_DESCRIPTIONS.get(doc_class, {})
