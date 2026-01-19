"""
Medical Term Verification Service - Lightweight Addon

Verifies if a term flagged as PII is actually a medical term.
Uses MEDIALpy for English abbreviations + German pattern matching.

This module prevents false positives where medical terminology like:
- "Nächtliche" -> [LOCATION] (should be preserved - means "nocturnal")
- "Kardiopulmonal" -> [NAME] (should be preserved - means "cardiopulmonary")
- "ST-Strecken-Veränderungen" -> [ORGANIZATION] (should be preserved - ECG term)
"""
import logging
import re
from functools import lru_cache

logger = logging.getLogger(__name__)

# Try to import MEDIALpy (optional dependency)
try:
    import medialpy
    MEDIALPY_AVAILABLE = True
    MEDIALPY_VERSION = getattr(medialpy, '__version__', 'unknown')
except ImportError:
    MEDIALPY_AVAILABLE = False
    MEDIALPY_VERSION = None
    logger.warning("MEDIALpy not installed - abbreviation lookup disabled")


class MedicalTermVerifier:
    """
    Lightweight medical term verification as addon to existing PII filter.

    Provides an additional layer of medical term detection beyond the
    existing medical_terms set in PIIFilter. When spaCy/Presidio detects
    a term as PER/LOC/ORG, this verifier checks if it's actually a
    medical term that should be preserved.
    """

    def __init__(self):
        self._init_german_patterns()
        logger.info(
            f"MedicalTermVerifier initialized - MEDIALpy: {MEDIALPY_AVAILABLE}"
            f"{f' (v{MEDIALPY_VERSION})' if MEDIALPY_VERSION else ''}"
        )

    def _init_german_patterns(self):
        """Initialize German medical term patterns."""

        # German medical suffixes (Latin/Greek origin, used in German)
        self.german_suffixes = {
            # Disease/condition suffixes
            'itis', 'ose', 'osis', 'pathie', 'penie', 'zytose', 'amie', 'emie',
            'urie', 'algie', 'asthenie', 'plegie', 'parese', 'spasmus',
            # Procedure suffixes
            'ektomie', 'tomie', 'plastik', 'skopie', 'graphie', 'gramm',
            'zentese', 'stase', 'lyse',
            # Organ/anatomy suffixes
            'pulmonal', 'pulmonale', 'pulmonaler', 'pulmonalen',
            'kardial', 'kardiale', 'kardialer', 'kardialen',
            'renal', 'renale', 'renaler', 'renalen',
            'hepatisch', 'hepatische', 'hepatischer', 'hepatischen',
            'zerebral', 'zerebrale', 'zerebraler', 'zerebralen',
            'intestinal', 'intestinale', 'intestinaler',
            'vaskular', 'vaskulare', 'vaskularer', 'vaskularen',
            'neural', 'neurale', 'neuraler', 'neuralen',
            'muskular', 'muskulare', 'muskularer', 'muskularen',
            # Compound organ adjectives
            'kardiopulmonal', 'kardiopulmonale', 'kardiopulmonaler',
            'kardiorenal', 'kardiorenale', 'kardiorenaler',
            'hepatorenal', 'hepatorenale', 'hepatorenaler',
            # Clinical descriptors
            'pathologisch', 'physiologisch', 'chronisch', 'akut',
            'systemisch', 'lokal', 'diffus', 'fokal',
        }

        # German medical prefixes
        self.german_prefixes = {
            'hyper', 'hypo', 'tachy', 'brady', 'poly', 'oligo', 'an', 'dys',
            'para', 'peri', 'endo', 'exo', 'intra', 'extra', 'trans', 'sub',
            'supra', 'infra', 'retro', 'ante', 'post', 'neo', 'pseudo',
            'hemi', 'mono', 'bi', 'tri', 'multi', 'pan',
        }

        # German temporal/frequency medical adjectives (commonly misclassified as LOC)
        self.german_temporal_terms = {
            'nächtlich', 'nächtliche', 'nächtlicher', 'nächtlichen', 'nächtliches',
            'paroxysmal', 'paroxysmale', 'paroxysmaler', 'paroxysmalen',
            'intermittierend', 'intermittierende', 'intermittierender',
            'persistierend', 'persistierende', 'persistierender',
            'rezidivierend', 'rezidivierende', 'rezidivierender',
            'progredient', 'progrediente', 'progredienter',
        }

        # ECG/medical compound patterns (commonly misclassified as ORG)
        self.compound_patterns = [
            r'^st[-\s]?strecke',       # ST-Strecke, ST Strecke
            r'^st[-\s]?hebung',        # ST-Hebung
            r'^st[-\s]?senkung',       # ST-Senkung
            r'^t[-\s]?welle',          # T-Welle
            r'^p[-\s]?welle',          # P-Welle
            r'^qrs[-\s]?komplex',      # QRS-Komplex
            r'^qt[-\s]?zeit',          # QT-Zeit
            r'^pq[-\s]?intervall',     # PQ-Intervall
            r'veränderung(en)?$',      # ...veränderungen
            r'störung(en)?$',          # ...störungen
            r'insuffizienz$',          # ...insuffizienz
            r'stenose$',               # ...stenose
        ]
        self.compound_regex = re.compile(
            '|'.join(self.compound_patterns),
            re.IGNORECASE
        )

    @lru_cache(maxsize=10000)
    def is_medical_term(self, term: str) -> tuple[bool, str]:
        """
        Check if a term is medical using multiple lightweight methods.

        Args:
            term: The term to check

        Returns:
            (is_medical: bool, reason: str)
        """
        if not term or len(term) < 2:
            return False, "too_short"

        term_lower = term.lower()

        # 1. Check MEDIALpy abbreviation database (English)
        if MEDIALPY_AVAILABLE:
            try:
                if medialpy.exists(term.upper()):
                    meaning = medialpy.find(term.upper())
                    return True, f"abbreviation:{meaning[:50] if meaning else 'known'}"
            except Exception:
                pass  # Silently continue if lookup fails

        # 2. Check German temporal/frequency terms (often misclassified as LOC)
        if term_lower in self.german_temporal_terms:
            return True, "german_temporal_medical"

        # 3. Check German medical suffixes
        for suffix in self.german_suffixes:
            if term_lower.endswith(suffix) and len(term_lower) > len(suffix) + 2:
                return True, f"german_suffix:{suffix}"

        # 4. Check German medical prefixes + minimum length
        for prefix in self.german_prefixes:
            if term_lower.startswith(prefix) and len(term_lower) > len(prefix) + 3:
                # Additional check: must end with common medical pattern
                if any(term_lower.endswith(s) for s in ['ie', 'isch', 'al', 'ar', 'ose', 'itis']):
                    return True, f"german_prefix:{prefix}"

        # 5. Check compound patterns (ECG terms, etc.)
        if self.compound_regex.search(term_lower):
            return True, "compound_medical_term"

        # 6. Check for German compound medical words (contains medical root)
        medical_roots = ['kardio', 'pulmono', 'hepato', 'nephro', 'neuro',
                        'gastro', 'dermato', 'onko', 'hamat', 'endo']
        for root in medical_roots:
            if root in term_lower:
                return True, f"german_root:{root}"

        return False, "not_medical"

    def verify_before_removal(self, term: str, detected_as: str) -> bool:
        """
        Convenience method: Should this term be preserved (not removed)?

        Args:
            term: The term flagged for removal
            detected_as: What it was detected as (PER, LOC, ORG)

        Returns:
            True if term should be PRESERVED (is medical)
        """
        is_medical, reason = self.is_medical_term(term)
        if is_medical:
            logger.info(
                f"PRESERVED medical term '{term}' ({reason}) - "
                f"was incorrectly flagged as {detected_as}"
            )
        return is_medical

    def clear_cache(self):
        """Clear the LRU cache if needed (e.g., for testing)."""
        self.is_medical_term.cache_clear()

    def get_cache_stats(self) -> dict:
        """Get cache statistics."""
        info = self.is_medical_term.cache_info()
        return {
            "hits": info.hits,
            "misses": info.misses,
            "size": info.currsize,
            "maxsize": info.maxsize,
        }
