"""
Medical Content Validator - Validates if document contains medical content
"""

import re
import logging
from typing import Tuple, Dict, Any, Optional
from app.models.document_types import DocumentClass

logger = logging.getLogger(__name__)

class MedicalContentValidator:
    """
    Service for validating if a document contains medical content.
    Uses pattern matching and AI fallback to determine if content is medical.
    """

    def __init__(self, ovh_client=None):
        """
        Initialize the medical content validator.

        Args:
            ovh_client: Optional OVH client for AI-based validation
        """
        self.ovh_client = ovh_client

    async def validate_medical_content(
        self,
        text: str,
        use_ai_fallback: bool = True
    ) -> Tuple[bool, float, str]:
        """
        Validate if the text contains medical content.

        Args:
            text: The text to validate
            use_ai_fallback: Whether to use AI if pattern matching is uncertain

        Returns:
            Tuple of (is_medical, confidence, method_used)
        """
        logger.info("Starting medical content validation...")

        # First try pattern-based validation
        pattern_result = self._validate_by_patterns(text)

        # If confidence is high enough, return pattern result
        if pattern_result[1] >= 0.8:  # High confidence threshold
            logger.info(f"✅ Pattern validation successful: {pattern_result[0]} (confidence: {pattern_result[1]:.2%})")
            return pattern_result

        # If pattern matching is uncertain and AI is available, use AI
        if use_ai_fallback and self.ovh_client:
            logger.info("Pattern matching uncertain, using AI validation...")
            ai_result = await self._validate_by_ai(text)
            if ai_result[1] > pattern_result[1]:
                logger.info(f"✅ AI validation: {ai_result[0]} (confidence: {ai_result[1]:.2%})")
                return ai_result

        # Return best result (pattern or default)
        logger.info(f"Using pattern result: {pattern_result[0]} (confidence: {pattern_result[1]:.2%})")
        return pattern_result

    def _validate_by_patterns(self, text: str) -> Tuple[bool, float, str]:
        """
        Validate medical content using keyword patterns.

        Args:
            text: The text to validate

        Returns:
            Tuple of (is_medical, confidence, method)
        """
        text_lower = text.lower()
        
        # Medical keywords and patterns
        medical_keywords = [
            # General medical terms
            'diagnose', 'diagnose', 'behandlung', 'therapie', 'medikament', 'arzneimittel',
            'symptom', 'beschwerde', 'krankheit', 'erkrankung', 'patient', 'patientin',
            'arzt', 'ärztin', 'krankenhaus', 'klinik', 'praxis', 'untersuchung',
            'labor', 'laborwert', 'blutwert', 'urintest', 'röntgen', 'mrt', 'ct',
            'ultraschall', 'biopsie', 'operation', 'chirurgie', 'anästhesie',
            
            # Body parts and systems
            'herz', 'lunge', 'leber', 'niere', 'magen', 'darm', 'gehirn', 'nerv',
            'muskel', 'knochen', 'gelenk', 'haut', 'auge', 'ohr', 'nase', 'mund',
            'zahn', 'zähne', 'wirbelsäule', 'rücken', 'schulter', 'knie', 'fuß',
            
            # Medical conditions
            'diabetes', 'bluthochdruck', 'herzinfarkt', 'schlaganfall', 'krebs',
            'tumor', 'entzündung', 'infektion', 'allergie', 'asthma', 'bronchitis',
            'pneumonie', 'gastritis', 'hepatitis', 'nephritis', 'arthritis',
            'osteoporose', 'demenz', 'alzheimer', 'parkinson', 'epilepsie',
            
            # Medical procedures
            'impfung', 'vakzination', 'transfusion', 'transplantation', 'dialysis',
            'chemotherapie', 'strahlentherapie', 'physiotherapie', 'rehabilitation',
            
            # Medical measurements and units
            'mg/dl', 'mmol/l', 'iu/l', 'ng/ml', 'pg/ml', 'mmhg', 'bpm', 'fieber',
            'temperatur', 'blutdruck', 'puls', 'atemfrequenz', 'sauerstoffsättigung',
            
            # Medical abbreviations
            'icd', 'ops', 'gdr', 'drg', 'bmi', 'ecg', 'ekg', 'eeg', 'emg'
        ]

        # Count medical keyword matches
        medical_matches = sum(1 for keyword in medical_keywords if keyword in text_lower)
        
        # Calculate confidence based on matches and text length
        text_length = len(text.split())
        if text_length == 0:
            return False, 0.0, "pattern"
        
        # Base confidence on keyword density
        keyword_density = medical_matches / text_length
        confidence = min(keyword_density * 50, 1.0)  # Scale to 0-1
        
        # Additional patterns that strongly indicate medical content
        medical_patterns = [
            r'\b\d+\s*(mg|ml|g|kg|mg/dl|mmol/l|iu/l|ng/ml)\b',  # Medical units
            r'\b(blutdruck|puls|temperatur|fieber)\s*:?\s*\d+',  # Vital signs
            r'\b(icd|ops)\s*[-\s]?\d+',  # Medical codes
            r'\b(patient|patientin|herr|frau)\s+[a-zäöüß]+\s+[a-zäöüß]+',  # Patient names
            r'\b(arzt|ärztin|dr\.|prof\.)\s+[a-zäöüß]+',  # Doctor names
            r'\b(krankenhaus|klinik|praxis)\s+[a-zäöüß]+',  # Medical facilities
            r'\b(entlassung|aufnahme|verlegung|konsil)\b',  # Medical procedures
        ]
        
        pattern_matches = sum(1 for pattern in medical_patterns if re.search(pattern, text_lower))
        pattern_confidence = min(pattern_matches * 0.2, 0.5)  # Additional confidence from patterns
        
        total_confidence = min(confidence + pattern_confidence, 1.0)
        is_medical = total_confidence >= 0.3  # Threshold for medical content
        
        return is_medical, total_confidence, "pattern"

    async def _validate_by_ai(self, text: str) -> Tuple[bool, float, str]:
        """
        Validate medical content using AI (OVH API).

        Args:
            text: The text to validate

        Returns:
            Tuple of (is_medical, confidence, method)
        """
        if not self.ovh_client:
            logger.warning("OVH client not available for AI validation")
            return False, 0.0, "ai"

        try:
            # Prepare validation prompt
            validation_prompt = f"""Analysiere diesen Text und bestimme, ob es sich um medizinischen Inhalt handelt.

KRITERIEN FÜR MEDIZINISCHEN INHALT:
- Medizinische Begriffe, Diagnosen, Symptome
- Körperteile, Organe, Körpersysteme
- Medikamente, Behandlungen, Therapien
- Laborwerte, Messungen, Vitalzeichen
- Arztbriefe, Befunde, Krankenhausberichte
- Medizinische Abkürzungen (ICD, OPS, etc.)

Antworte NUR mit einem dieser Wörter:
- MEDICAL (wenn medizinisch)
- NON_MEDICAL (wenn nicht medizinisch)

Text zur Analyse:
{text[:2000]}  # Limit text for validation

BEWERTUNG:"""

            # Get AI validation
            result = await self.ovh_client.process_medical_text(
                text=text[:2000],  # Limit text length for validation
                instruction=validation_prompt,
                temperature=0.1,  # Low temperature for consistent validation
                max_tokens=10  # We only need one word
            )

            # Parse AI response
            result_clean = result.strip().upper()

            # Determine if medical based on response
            if "MEDICAL" in result_clean and "NON_MEDICAL" not in result_clean:
                is_medical = True
                confidence = 0.9  # High confidence for AI validation
            elif "NON_MEDICAL" in result_clean and "MEDICAL" not in result_clean:
                is_medical = False
                confidence = 0.9  # High confidence for AI validation
            else:
                # Ambiguous response, use pattern result
                pattern_result = self._validate_by_patterns(text)
                is_medical = pattern_result[0]
                confidence = pattern_result[1] * 0.7  # Reduce confidence for ambiguous AI response

            logger.info(f"AI validation result: {is_medical} (confidence: {confidence:.2%})")
            return is_medical, confidence, "ai"

        except Exception as e:
            logger.error(f"AI validation failed: {e}")
            # Fallback to pattern validation
            pattern_result = self._validate_by_patterns(text)
            return pattern_result[0], pattern_result[1] * 0.5, "ai_fallback"

    def get_validation_details(self, text: str) -> Dict[str, Any]:
        """
        Get detailed validation information for debugging.

        Args:
            text: The text to analyze

        Returns:
            Dictionary with validation details
        """
        text_lower = text.lower()
        
        # Count various medical indicators
        medical_keywords = [
            'diagnose', 'behandlung', 'therapie', 'medikament', 'symptom',
            'krankheit', 'patient', 'arzt', 'krankenhaus', 'untersuchung',
            'labor', 'blutwert', 'operation', 'herz', 'lunge', 'leber'
        ]
        
        keyword_matches = {keyword: text_lower.count(keyword) for keyword in medical_keywords}
        total_matches = sum(keyword_matches.values())
        
        # Check for medical patterns
        medical_patterns = [
            r'\b\d+\s*(mg|ml|g|kg|mg/dl|mmol/l)\b',
            r'\b(blutdruck|puls|temperatur)\s*:?\s*\d+',
            r'\b(icd|ops)\s*[-\s]?\d+',
            r'\b(patient|patientin)\s+[a-zäöüß]+',
            r'\b(arzt|ärztin|dr\.)\s+[a-zäöüß]+'
        ]
        
        pattern_matches = [len(re.findall(pattern, text_lower)) for pattern in medical_patterns]
        total_patterns = sum(pattern_matches)
        
        return {
            "text_length": len(text.split()),
            "keyword_matches": keyword_matches,
            "total_keyword_matches": total_matches,
            "pattern_matches": pattern_matches,
            "total_pattern_matches": total_patterns,
            "keyword_density": total_matches / len(text.split()) if text.split() else 0,
            "pattern_density": total_patterns / len(text.split()) if text.split() else 0
        }
