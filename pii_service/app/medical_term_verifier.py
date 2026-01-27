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
        self._init_german_scoring_systems()
        self._init_german_medical_abbreviations()
        self._init_bacterial_species_pattern()
        self._init_autoantibody_pattern()
        self._init_anatomical_terms()
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
            'zentese', 'stase', 'lyse', 'ostomie',
            # Additional compound word suffixes
            'furkation', 'bifurkation', 'trifurkation',  # Vessel branching
            'umsatz',  # Metabolism: Grundumsatz
            'stomose', 'anastomose',  # Surgical connections
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

    def _init_german_scoring_systems(self):
        """Initialize German/international medical scoring systems.

        These are commonly misclassified as names (e.g., "Child" in "Child-Pugh score").
        """
        self.german_scoring_systems = {
            # Liver scoring
            'child', 'child-pugh', 'meld', 'meld-na',
            # General ICU scores
            'sofa', 'apache', 'saps', 'tiss',
            # Cardiac
            'nyha', 'killip', 'timi', 'grace', 'chads2', 'cha2ds2-vasc', 'has-bled',
            # Anesthesia
            'asa', 'mallampati',
            # GI bleeding
            'forrest', 'rockall', 'blatchford', 'glasgow-blatchford',
            # Pancreatitis
            'ranson', 'bisap', 'ctsi', 'marshall',
            # Pneumonia
            'curb-65', 'curb', 'psi', 'fine',
            # Portal hypertension
            'baveno', 'paquet',
            # GERD
            'los angeles', 'savary-miller', 'savary', 'miller',
            # Esophageal cancer
            'siewert',
            # Varices
            'dagradi',
            # Neurological
            'glasgow', 'gcs', 'nihss', 'hunt-hess', 'fisher',
            # Cancer staging
            'tnm', 'figo', 'dukes', 'clark', 'breslow', 'gleason',
            # Other
            'apgar', 'bishop', 'karnofsky', 'ecog', 'rankin', 'barthel',
        }

    def _init_german_medical_abbreviations(self):
        """Initialize German medical procedure/test abbreviations.

        These are commonly misclassified as organizations.
        """
        self.german_medical_abbreviations = {
            # Endoscopy procedures
            'ögd', 'oegd', 'ösophagogastroduodenoskopie', 'ercp', 'mrcp', 'ptcd',
            'erc', 'koloskopie', 'gastroskopie', 'bronchoskopie', 'zystoskopie',
            'laparoskopie', 'thorakoskopie', 'arthroskopie', 'rektoskopie',
            # Imaging
            'ct', 'mrt', 'pet', 'pet-ct', 'spect', 'szintigraphie', 'fibroscan',
            'elastographie', 'sono', 'sonographie', 'doppler',
            # Lab tests
            'pcr', 'elisa', 'western-blot', 'western blot', 'immunblot',
            'ena', 'ana', 'anca', 'p-anca', 'c-anca', 'asma', 'ama', 'lkm', 'sma',
            # Procedures
            'tipss', 'tips', 'tace', 'rfa', 'mwa', 'prt', 'sirt',
            'erythrozytenkonzentrat', 'ek', 'ffp', 'tk', 'sbp',
            # Classifications (may look like locations)
            'los angeles', 'la klassifikation',
            # Genetic terms
            'hfe', 'h63d', 'c282y', 's65c',
            # Liver-specific
            'hep', 'hcv', 'hbv', 'hav', 'hev', 'hdv', 'hiv',
            # Function tests
            'ogtt', 'ltt', 'tsh',
            # Blood products
            'erythrozytenkonzentrat', 'thrombozytenkonzentrat',

            # Blood indices (2-4 letter abbreviations commonly misidentified as ORG)
            'mcv', 'mch', 'mchc', 'rdw', 'mpv', 'pdw', 'pct',
            'plt', 'wbc', 'rbc', 'hct', 'hgb',

            # Lung function abbreviations (commonly misidentified as ORG)
            'pef', 'mef', 'pif', 'tlc', 'frc', 'vc', 'ivc', 'evc',
            'fev1', 'fvc', 'dlco', 'kco', 'raw', 'sraw', 'gaw', 'sgaw',

            # Cardiac abbreviations (commonly misidentified as ORG)
            'lvef', 'rvef', 'lvedv', 'lvesv', 'lvedp',
            'tapse', 'mapse', 'gls', 'tdi',
            'abi', 'tbi', 'pwv', 'aix', 'cfpwv',

            # Body composition abbreviations
            'bia', 'bsa', 'ffm', 'tbw', 'ecw', 'icw',

            # Electrolyte abbreviations (short forms)
            'na', 'k', 'cl', 'mg', 'fe', 'zn', 'cu', 'po4',
        }

    def _init_bacterial_species_pattern(self):
        """Initialize bacterial species patterns.

        Bacterial species names are commonly misclassified as locations
        (e.g., "Staph. epidermidis" -> "Staph. [LOCATION]").
        """
        # Bacterial genera (genus names)
        self.bacterial_genera = {
            'staphylococcus', 'staph', 'streptococcus', 'strep',
            'pseudomonas', 'klebsiella', 'enterococcus', 'enterobacter',
            'escherichia', 'e. coli', 'e.coli', 'salmonella', 'shigella',
            'campylobacter', 'helicobacter', 'h. pylori', 'h.pylori',
            'clostridium', 'clostridioides', 'c. diff', 'c.diff',
            'haemophilus', 'neisseria', 'listeria', 'legionella',
            'bordetella', 'corynebacterium', 'mycobacterium', 'mycoplasma',
            'chlamydia', 'treponema', 'borrelia', 'rickettsia',
            'candida', 'aspergillus', 'cryptococcus',  # Fungi but often grouped
        }

        # Bacterial species epithets (species names)
        self.bacterial_species = {
            'aureus', 'epidermidis', 'haemolyticus', 'saprophyticus', 'hominis',
            'pneumoniae', 'pyogenes', 'agalactiae', 'viridans', 'mutans',
            'aeruginosa', 'coli', 'difficile', 'perfringens', 'botulinum',
            'tetani', 'faecalis', 'faecium', 'pylori', 'jejuni',
            'influenzae', 'meningitidis', 'gonorrhoeae', 'monocytogenes',
            'pneumophila', 'pertussis', 'tuberculosis', 'leprae',
            'albicans', 'glabrata', 'tropicalis', 'krusei', 'auris',
            'fumigatus', 'niger', 'flavus', 'neoformans',
        }

        # Pattern to match "Genus species" or "Genus. species" combinations
        genera_pattern = '|'.join(re.escape(g) for g in self.bacterial_genera)
        species_pattern = '|'.join(re.escape(s) for s in self.bacterial_species)
        self.bacterial_species_pattern = re.compile(
            rf'\b(?:{genera_pattern})\.?\s*(?:{species_pattern})?\b',
            re.IGNORECASE
        )

    def _init_autoantibody_pattern(self):
        """Initialize autoantibody patterns.

        Autoantibodies (anti-XXX format) are commonly misclassified as organizations.
        """
        self.autoantibody_pattern = re.compile(
            r'\banti[-\s]?(?:'
            r'jo[-\s]?1|nxp[-\s]?2|sma|lkm|slc|mi[-\s]?2|'
            r'dsdna|ds[-\s]?dna|centromere|scl[-\s]?70|'
            r'ssa|ssb|rnp|smith|sm|'
            r'cardiolipin|phospholipid|'
            r'gad|tpo|tg|tsh[-\s]?rezeptor|'
            r'ccp|mda[-\s]?5|sae|tif1[-\s]?gamma|pm[-\s]?scl|ku|'
            r'synthetase|srp|hmgcr|signal[-\s]?recognition|'
            r'hcv|hiv|hbv|hbs|hbc|hbe'
            r')\b',
            re.IGNORECASE
        )

    def _init_anatomical_terms(self):
        """Initialize anatomical terms that are commonly misclassified.

        These include lung lobes, imaging techniques, and medical descriptors.
        """
        self.anatomical_terms = {
            # Lung lobes (commonly misclassified as locations)
            'unterlappen', 'oberlappen', 'mittellappen', 'lingula',
            'unterlappenatelektase', 'oberlappenatelektase',
            # Imaging techniques (commonly misclassified as locations)
            'liegetechnik', 'stehendtechnik', 'stehend', 'liegend',
            'seitaufnahme', 'p.a.', 'ap', 'a.p.',
            # Medical descriptors
            'exokrin', 'exokriner', 'exokrine', 'exokrinen',
            'endokrin', 'endokriner', 'endokrine', 'endokrinen',
            # Genetic terms
            'heterozygoter', 'heterozygote', 'heterozygoten',
            'homozygoter', 'homozygote', 'homozygoten',
            # Clinical conditions
            'stauungsdermatitis', 'anasarka', 'aszites',
            'kardiorenal', 'hepatorenal', 'kardiopulmonal',
            # Medical devices/procedures
            'fibroscan', 'elastographie', 'sono', 'doppler',

            # Latin anatomical terms commonly used in German medical reports
            # Pancreas parts
            'caput', 'corpus', 'cauda',
            # Vessels
            'truncus', 'coeliacus', 'mesenterica', 'renalis',
            'vena', 'arteria', 'ductus', 'nervus',
            # General anatomy
            'lobus', 'segmentum', 'regio',
            'apex', 'basis', 'fundus', 'antrum',
            'cortex', 'medulla', 'parenchym', 'hilus', 'hilum',
            'collum', 'isthmus',
            # GI tract
            'pylorus', 'cardia', 'bulbus',
            'duodenum', 'jejunum', 'ileum', 'colon', 'rectum', 'sigmoid',
            # Urogenital
            'vesica', 'ureter', 'urethra', 'pelvis',
            'cervix', 'ovarium', 'tuba',

            # Disease names (could be confused with locations)
            'corona', 'covid', 'covid-19', 'sars', 'sars-cov-2', 'mers',
            'steatosis', 'hepatis', 'nash', 'nafld', 'afld',

            # Cell type abbreviations (commonly misclassified as NAME)
            'ery', 'erys', 'leuko', 'leukos', 'thrombo', 'thrombos',
            'lympho', 'lymphos', 'mono', 'monos', 'granu', 'granus',
            'neutro', 'neutros', 'eosino', 'basophil',

            # German abbreviations (must not be mangled)
            'z.b.', 'd.h.', 'u.a.', 'bzw.', 'ggf.', 'evtl.', 'etc.',
            'li.', 're.', 'bds.', 'neg.', 'pos.',

            # Body composition terms
            'körperwasseranteil', 'körperfettanteil', 'muskelmasse',
            'viszeralfett', 'subkutanfett',

            # UV/Skin terms
            'solarien', 'solarium', 'uv-faktor', 'uv-index', 'lsf', 'spf',

            # Vitamins (prevent single-letter detection as names)
            'vitamin', 'vitamin a', 'vitamin b', 'vitamin b1', 'vitamin b2',
            'vitamin b6', 'vitamin b12', 'vitamin c', 'vitamin d', 'vitamin d3',
            'vitamin e', 'vitamin k',

            # German compound medical terms (commonly misclassified)
            'bifurkation', 'trifurkation', 'anastomose',
            'grundumsatz', 'stoffwechselumsatz', 'ruheumsatz',
            'knöchel-arm-index', 'ankle-brachial-index',
            'leukozyten', 'erythrozyten', 'thrombozyten',
            'hämatokrit', 'hämoglobin',

            # Patient/Patientin - German words for patient, NOT names!
            # These are critically important - commonly misdetected as PERSON
            'patient', 'patientin', 'patienten', 'patientinnen',
            'pat', 'pat.',  # Abbreviations

            # General condition terms (commonly misclassified as NAME)
            'az-reduziert', 'az-reduzierte', 'az-reduzierter', 'az-reduzierten',
            'allgemeinzustand', 'allgemeinzustandes', 'allgemeinzustandsreduziert',

            # Cytology/pathology terms
            'zytologie', 'zytologisch', 'zytologische', 'zytologischer',
            'histologie', 'histologisch', 'histologische', 'histologischer',
            'pathologie', 'pathologisch', 'pathologische', 'pathologischer',
        }

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

        # 3. Check German scoring systems (e.g., Child-Pugh, MELD, Paquet)
        if term_lower in self.german_scoring_systems:
            return True, f"scoring_system:{term_lower}"

        # 4. Check German medical abbreviations (e.g., ÖGD, TIPSS, PCR)
        if term_lower in self.german_medical_abbreviations:
            return True, f"medical_abbrev:{term_lower}"

        # 5. Check anatomical/technical terms (e.g., Unterlappen, Liegetechnik)
        if term_lower in self.anatomical_terms:
            return True, f"anatomical:{term_lower}"

        # 6. Check bacterial genera and species
        if term_lower in self.bacterial_genera or term_lower in self.bacterial_species:
            return True, f"bacterial:{term_lower}"

        # 7. Check for bacterial species patterns (e.g., "Staph. epidermidis")
        if self.bacterial_species_pattern.search(term):
            return True, "bacterial_species"

        # 8. Check for autoantibody patterns (e.g., anti-Jo-1, anti-SMA)
        if self.autoantibody_pattern.search(term):
            return True, "autoantibody"

        # 9. Check German medical suffixes
        for suffix in self.german_suffixes:
            if term_lower.endswith(suffix) and len(term_lower) > len(suffix) + 2:
                return True, f"german_suffix:{suffix}"

        # 10. Check German medical prefixes + minimum length
        for prefix in self.german_prefixes:
            if term_lower.startswith(prefix) and len(term_lower) > len(prefix) + 3:
                # Additional check: must end with common medical pattern
                if any(term_lower.endswith(s) for s in ['ie', 'isch', 'al', 'ar', 'ose', 'itis']):
                    return True, f"german_prefix:{prefix}"

        # 11. Check compound patterns (ECG terms, etc.)
        if self.compound_regex.search(term_lower):
            return True, "compound_medical_term"

        # 12. Check for German compound medical words (contains medical root)
        medical_roots = ['kardio', 'pulmono', 'hepato', 'nephro', 'neuro',
                        'gastro', 'dermato', 'onko', 'hamat', 'endo',
                        'bifurk', 'anastom', 'stenos', 'thromb',  # Vascular
                        'metabol', 'umsatz', 'vitamin']  # Metabolism/nutrition
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
