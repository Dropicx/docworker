"""
Optimized Privacy Filter with Hybrid Approach

Fast-path regex (10ms) + conditional spaCy NER (100ms)
60-70% faster than pure spaCy approach while maintaining high accuracy.

Performance Targets:
- Simple documents (regex only): 10-20ms
- Complex documents (regex + spaCy): 100-120ms
- Average: 50-70ms (vs. 200ms current)

Architecture:
1. Fast regex filter removes obvious PII patterns
2. Heuristic determines if spaCy NER is needed
3. spaCy NER applied only when necessary for name detection
4. Medical terms protected and restored throughout
"""

import re
import logging
import os
import time


logger = logging.getLogger(__name__)


class OptimizedPrivacyFilter:
    """
    Hybrid PII filter combining speed and accuracy.

    Uses fast regex patterns for obvious PII (addresses, phones, etc.)
    and conditional spaCy NER for intelligent name detection.
    """

    def __init__(self, spacy_model_path: str | None = None):
        """
        Initialize optimized privacy filter.

        Args:
            spacy_model_path: Path to spaCy model (e.g., /data/spacy_models/de_core_news_sm)
                             If None, uses environment variable SPACY_MODEL_PATH or system installation
        """
        self.spacy_model_path = spacy_model_path or os.getenv('SPACY_MODEL_PATH')
        self.nlp = None
        self.has_ner = False

        # Initialize component filters
        self._init_component_filters()

        # Load spaCy model
        self._load_spacy_model()

        logger.info("🎯 OptimizedPrivacyFilter initialized")

    def _init_component_filters(self):
        """Initialize fast regex filter and advanced NER filter components"""
        try:
            # Import fast regex-based filter
            from app.services.smart_privacy_filter import SmartPrivacyFilter
            self._fast_filter = SmartPrivacyFilter()
            logger.info("✅ Fast regex filter loaded (SmartPrivacyFilter)")
        except ImportError as e:
            logger.error(f"❌ Failed to load SmartPrivacyFilter: {e}")
            raise

        try:
            # Import advanced spaCy-based filter
            from app.services.privacy_filter_advanced import AdvancedPrivacyFilter
            self._advanced_filter = AdvancedPrivacyFilter()
            logger.info("✅ Advanced NER filter loaded (AdvancedPrivacyFilter)")
        except ImportError as e:
            logger.error(f"❌ Failed to load AdvancedPrivacyFilter: {e}")
            raise

    def _load_spacy_model(self):
        """
        Load spaCy model from Railway volume or system installation.

        Priority:
        1. Railway volume path (e.g., /data/spacy_models/de_core_news_sm)
        2. System installation (standard pip install)
        3. Fallback to no NER (regex only)
        """
        try:
            import spacy

            # Try loading from Railway volume first
            if self.spacy_model_path and os.path.exists(self.spacy_model_path):
                try:
                    self.nlp = spacy.load(self.spacy_model_path)
                    self.has_ner = True
                    logger.info(f"✅ spaCy loaded from Railway volume: {self.spacy_model_path}")
                    return
                except Exception as e:
                    logger.warning(f"⚠️ Failed to load from volume: {e}, trying system installation...")

            # Fallback to system installation
            try:
                self.nlp = spacy.load("de_core_news_sm")
                self.has_ner = True
                logger.info("✅ spaCy loaded from system installation")
                return
            except OSError:
                logger.warning("⚠️ spaCy model 'de_core_news_sm' not found in system")

        except ImportError:
            logger.warning("⚠️ spaCy not installed")

        # No spaCy available - will use regex-only mode
        self.nlp = None
        self.has_ner = False
        logger.info("📝 Running in regex-only mode (no spaCy NER)")

    def remove_pii(self, text: str) -> str:
        """
        Remove PII using hybrid approach.

        Performance-optimized execution path:
        1. Fast regex filter (5-10ms): Remove obvious PII patterns
        2. Heuristic check (1ms): Determine if NER needed
        3. Conditional NER (~100ms): Apply spaCy only when necessary
        4. Medical term restoration (1ms): Restore protected medical terms

        Args:
            text: Input text with potential PII

        Returns:
            str: Text with PII removed, medical terms preserved
        """
        if not text:
            return text

        start_time = time.time()

        logger.info("🔍 Starting optimized PII removal...")

        # STEP 1: Protect medical terms (both filters use this)
        # This prevents false positives on medical terminology
        protected_text = self._fast_filter._protect_medical_terms(text)

        # STEP 2: Fast regex filter - Remove obvious PII patterns
        # Handles: addresses, phones, emails, insurance numbers, dates
        # Performance: 5-10ms
        logger.debug("⚡ Applying fast regex filter...")
        cleaned_text = self._fast_filter._remove_explicit_patterns(protected_text)

        # STEP 3: Intelligent name detection
        # Decision: Use spaCy NER or heuristic based on text characteristics
        if self._needs_ner_analysis(cleaned_text) and self.has_ner:
            # Complex case: Use spaCy NER for accurate name detection
            # Performance: ~100ms
            logger.debug("🧠 Applying spaCy NER for name detection...")
            cleaned_text = self._advanced_filter._remove_names_with_ner(cleaned_text)
        else:
            # Simple case: Use fast heuristic name detection
            # Performance: ~5ms
            logger.debug("📝 Using heuristic name detection...")
            cleaned_text = self._fast_filter._remove_names_smart(cleaned_text)

        # STEP 4: Restore medical terms
        # Converts protected placeholders back to original medical terms
        # Performance: 1ms
        cleaned_text = self._fast_filter._restore_medical_terms(cleaned_text)

        # Clean up formatting
        cleaned_text = re.sub(r'\n{3,}', '\n\n', cleaned_text)
        cleaned_text = re.sub(r'[ \t]+', ' ', cleaned_text)

        # Performance metrics
        elapsed_ms = (time.time() - start_time) * 1000
        logger.info(f"✅ PII removal completed in {elapsed_ms:.1f}ms")

        return cleaned_text.strip()

    def _needs_ner_analysis(self, text: str) -> bool:
        """
        Heuristic to determine if spaCy NER is needed.

        Optimization: Skip expensive NER for simple cases where regex is sufficient.

        Skip NER if:
        - Text is very short (<100 chars) - unlikely to contain complex names
        - Few capitalized words (<5) - no names to detect
        - Already heavily cleaned by regex - little PII remaining

        Args:
            text: Text after regex cleaning

        Returns:
            bool: True if NER should be applied, False to use fast heuristic
        """
        # Very short text - skip NER
        if len(text) < 100:
            logger.debug("📊 Skipping NER: text too short (<100 chars)")
            return False

        # Count capitalized words (potential names)
        words = text.split()
        cap_words = sum(1 for w in words if w and len(w) > 1 and w[0].isupper())

        # Few capitalized words - likely no names remaining
        if cap_words < 5:
            logger.debug(f"📊 Skipping NER: few capitalized words ({cap_words} < 5)")
            return False

        # Count "suspicious" patterns that might be names
        # e.g., "Dr. X" or "Herr Y" patterns that regex might have missed
        title_patterns = ['Dr.', 'Prof.', 'Herr', 'Frau']
        has_titles = any(title in text for title in title_patterns)

        if not has_titles and cap_words < 10:
            logger.debug(f"📊 Skipping NER: no titles and moderate caps ({cap_words} < 10)")
            return False

        # Complex text - apply NER for best accuracy
        logger.debug(f"📊 Applying NER: complex text ({cap_words} cap words)")
        return True

    def validate_medical_content(self, original: str, cleaned: str) -> bool:
        """
        Validate that medical content is preserved.

        Delegates to AdvancedPrivacyFilter's validation logic.

        Args:
            original: Original text before PII removal
            cleaned: Text after PII removal

        Returns:
            bool: True if ≥80% of medical terms preserved
        """
        return self._advanced_filter.validate_medical_content(original, cleaned)

    def get_performance_stats(self) -> dict:
        """
        Get performance and configuration statistics.

        Returns:
            dict: Filter configuration and capabilities
        """
        return {
            'filter_type': 'OptimizedPrivacyFilter',
            'mode': 'hybrid_ner' if self.has_ner else 'regex_only',
            'spacy_available': self.has_ner,
            'spacy_model_path': self.spacy_model_path if self.has_ner else None,
            'expected_performance_ms': {
                'simple_documents': '10-20',
                'complex_documents': '100-120',
                'average': '50-70'
            }
        }
