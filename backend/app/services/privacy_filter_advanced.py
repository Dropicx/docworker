"""Advanced Privacy Filter Service with spaCy NER.

GDPR-compliant PII removal for German medical documents. Removes names,
addresses, birthdates, contact information, and insurance numbers while
preserving all medical information, lab values, diagnoses, and treatments.

Features:
    - Optional spaCy NER for intelligent name recognition
    - Fallback to heuristic-based detection if spaCy unavailable
    - Protects 146+ medical terms and 210+ medical abbreviations
    - Validates medical content preservation (GDPR compliance)
"""

import logging
import re
from re import Pattern

# Try to import spaCy, but make it optional
try:
    import spacy
    from spacy.language import Language

    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False
    spacy = None
    Language = None

logger = logging.getLogger(__name__)


class AdvancedPrivacyFilter:
    """GDPR-compliant privacy filter for German medical documents.

    Uses optional spaCy NER combined with regex patterns to remove personally
    identifiable information (PII) while preserving medical content. Designed
    specifically for German medical documents (Arztbrief, Befundbericht, Laborwerte).

    The filter removes:
        - Patient names (detected via spaCy NER and title patterns)
        - Birthdates (geb. XX.XX.XXXX format)
        - Addresses (street, PLZ, city)
        - Contact information (phone, email)
        - Insurance numbers
        - Salutations and signatures

    The filter preserves:
        - All medical terminology (146+ terms)
        - Medical abbreviations (210+ protected)
        - Lab values and measurements
        - Diagnoses (ICD codes, medical conditions)
        - Medications and dosages
        - Medical procedures and findings

    Attributes:
        nlp (Optional[Language]): spaCy language model if available
        has_ner (bool): Whether NER functionality is available
        medical_terms (Set[str]): Protected medical terminology
        protected_abbreviations (Set[str]): Protected medical abbreviations
        patterns (Dict[str, Pattern]): Compiled regex patterns for PII detection

    Example:
        >>> filter = AdvancedPrivacyFilter()
        >>> medical_text = "Patient: Max Mustermann, geb. 01.01.1980..."
        >>> cleaned = filter.remove_pii(medical_text)
        >>> is_valid = filter.validate_medical_content(medical_text, cleaned)
        >>> print(f"Medical content preserved: {is_valid}")
    """

    def __init__(self) -> None:
        """Initialisiert den Filter mit spaCy NER Model"""
        self.nlp = None
        self._initialize_spacy()

        logger.info(
            "🎯 Privacy Filter: Entfernt persönliche Daten, erhält medizinische Informationen"
        )

        # Medizinische Begriffe, die NICHT als Namen erkannt werden sollen
        self.medical_terms = {
            # Körperteile und Organe
            "herz",
            "lunge",
            "leber",
            "niere",
            "magen",
            "darm",
            "kopf",
            "hals",
            "brust",
            "bauch",
            "rücken",
            "schulter",
            "knie",
            "hüfte",
            "hand",
            "fuß",
            "hirn",
            "gehirn",
            "muskel",
            "knochen",
            "gelenk",
            "sehne",
            "nerv",
            "gefäß",
            "arterie",
            "vene",
            "lymphe",
            "milz",
            "pankreas",
            "schilddrüse",
            # Medizinische Fachbegriffe
            "patient",
            "patientin",
            "diagnose",
            "befund",
            "therapie",
            "behandlung",
            "untersuchung",
            "operation",
            "medikament",
            "dosierung",
            "anamnese",
            "kardial",
            "kardiale",
            "pulmonal",
            "hepatisch",
            "renal",
            "gastral",
            "neural",
            "muskulär",
            "vaskulär",
            "arterial",
            "arterielle",
            "arterieller",
            "arterielles",
            "venös",
            "symptom",
            "syndrom",
            "erkrankung",
            "krankheit",
            "störung",
            "insuffizienz",
            "stenose",
            "thrombose",
            "embolie",
            "infarkt",
            "ischämie",
            "nekrose",
            "inflammation",
            "infektion",
            "sepsis",
            "abszeß",
            "tumor",
            "karzinom",
            "hypertonie",
            "hypotonie",
            "diabetes",
            # Häufige medizinische Adjektive
            "akut",
            "akute",
            "akuter",
            "akutes",
            "chronisch",
            "chronische",
            "primär",
            "sekundär",
            "maligne",
            "benigne",
            "bilateral",
            "unilateral",
            "proximal",
            "distal",
            "lateral",
            "medial",
            "anterior",
            "posterior",
            "superior",
            "inferior",
            "links",
            "rechts",
            "beidseits",
            "normal",
            "pathologisch",
            "physiologisch",
            "regelrecht",
            "unauffällig",
            # Medikamente und Substanzen (häufige)
            "aspirin",
            "insulin",
            "cortison",
            "antibiotika",
            "penicillin",
            "morphin",
            "ibuprofen",
            "paracetamol",
            "metformin",
            "simvastatin",
            # Untersuchungen
            "mrt",
            "ct",
            "röntgen",
            "ultraschall",
            "ekg",
            "echo",
            "szintigraphie",
            "biopsie",
            "punktion",
            "endoskopie",
            "koloskopie",
            "gastroskopie",
            # Wichtige Wörter
            "aktuell",
            "aktuelle",
            "aktueller",
            "aktuelles",
            "vorhanden",
            # Abteilungen
            "innere",
            "medizin",
            "chirurgie",
            "neurologie",
            "kardiologie",
            "gastroenterologie",
            "pneumologie",
            "nephrologie",
            "onkologie",
            # Vitamine und Nährstoffe (auch Kleinschreibung)
            "vitamin",
            "vitamine",
            "d3",
            "b12",
            "b6",
            "b1",
            "b2",
            "b9",
            "k2",
            "k1",
            "folsäure",
            "folat",
            "cobalamin",
            "thiamin",
            "riboflavin",
            "niacin",
            "pantothensäure",
            "pyridoxin",
            "biotin",
            "ascorbinsäure",
            "tocopherol",
            "retinol",
            "calciferol",
            "cholecalciferol",
            "ergocalciferol",
            "calcium",
            "magnesium",
            "kalium",
            "natrium",
            "phosphor",
            "eisen",
            "zink",
            "kupfer",
            "mangan",
            "selen",
            "jod",
            "fluor",
            "chrom",
            # ERWEITERTE BLUTWERTE - Hämatologie
            "hämoglobin",
            "haemoglobin",
            "erythrozyten",
            "leukozyten",
            "thrombozyten",
            "hämatokrit",
            "haematokrit",
            "mcv",
            "mch",
            "mchc",
            "rdw",
            "retikulozyten",
            "neutrophile",
            "lymphozyten",
            "monozyten",
            "eosinophile",
            "basophile",
            "stabkernige",
            "segmentkernige",
            "blasten",
            "metamyelozyten",
            # Gerinnung
            "quick",
            "inr",
            "ptt",
            "aptt",
            "thrombinzeit",
            "fibrinogen",
            "antithrombin",
            "d-dimere",
            "d-dimer",
            "faktor",
            "protein",
            "plasminogen",
            "thromboplastin",
            # Leber
            "got",
            "gpt",
            "ast",
            "alt",
            "ggt",
            "gamma-gt",
            "ldh",
            "alkalische",
            "phosphatase",
            "bilirubin",
            "direktes",
            "indirektes",
            "albumin",
            "globulin",
            "cholinesterase",
            "ammoniak",
            "alpha-fetoprotein",
            "afp",
            # Niere
            "kreatinin",
            "harnstoff",
            "harnsäure",
            "cystatin",
            "egfr",
            "gfr",
            "mikroalbumin",
            "proteinurie",
            "clearance",
            "osmolalität",
            # Elektrolyte
            "chlorid",
            "phosphat",
            "bikarbonat",
            "anionenlücke",
            # Stoffwechsel
            "glucose",
            "glukose",
            "hba1c",
            "fruktosamin",
            "laktat",
            "lactat",
            "cholesterin",
            "hdl",
            "ldl",
            "vldl",
            "triglyzeride",
            "triglyceride",
            "lipoprotein",
            "apolipoprotein",
            # Hormone
            "tsh",
            "ft3",
            "ft4",
            "t3",
            "t4",
            "thyreoglobulin",
            "calcitonin",
            "cortisol",
            "acth",
            "aldosteron",
            "renin",
            "testosteron",
            "östrogen",
            "oestrogen",
            "progesteron",
            "prolaktin",
            "fsh",
            "lh",
            "hcg",
            "dhea",
            "somatotropin",
            "igf",
            "parathormon",
            "pth",
            # Entzündung/Infektion
            "crp",
            "c-reaktives",
            "procalcitonin",
            "pct",
            "bsg",
            "blutsenkung",
            "interleukin",
            "il-6",
            "tnf",
            "ferritin",
            "transferrin",
            "haptoglobin",
            # Tumormarker
            "cea",
            "ca19-9",
            "ca125",
            "ca15-3",
            "ca72-4",
            "psa",
            "fpsa",
            "nse",
            "cyfra",
            "scc",
            "chromogranin",
            "s100",
            # Immunologie
            "igg",
            "iga",
            "igm",
            "ige",
            "igd",
            "immunglobulin",
            "komplement",
            "c3",
            "c4",
            "ch50",
            "ana",
            "anca",
            "rheumafaktor",
            "rf",
            "ccp",
            "anti-ccp",
            "dsdna",
            "ena",
            "tpo",
            "trak",
            "gad",
            # Vitalstoffe (erweitert)
            "holotranscobalamin",
            "methylmalonsäure",
            "homocystein",  # Laborwerte und Einheiten
            "wert",
            "werte",
            "labor",
            "laborwert",
            "laborwerte",
            "blutbild",
            "parameter",
            "referenz",
            "referenzbereich",
            "normbereich",
            "normwert",
            "erhöht",
            "erniedrigt",
            "grenzwertig",
            "positiv",
            "negativ",
            "mg",
            "dl",
            "ml",
            "mmol",
            "µmol",
            "nmol",
            "pmol",
            "ng",
            "pg",
            "iu",
            "einheit",
            "einheiten",
            "prozent",
            "promille",
            "titer",
            "ratio",
            # Zusätzliche Begriffe aus Tabellen
            "messwert",
            "messung",
            "analyse",
            "bestimmung",
            "nachweis",
            "screening",
            "differentialblutbild",
            "gerinnungsstatus",
            "leberwerte",
            "nierenwerte",
            "schilddrüsenwerte",
            "elektrolytstatus",
            "blutgasanalyse",
            "urinstatus",
        }

        # Titel und Anreden, die auf Namen hinweisen
        self.name_indicators = {
            "herr",
            "frau",
            "dr",
            "prof",
            "professor",
            "med",
            "dipl",
            "ing",
            "herrn",
            "familie",
        }

        # Medizinische Abkürzungen, die geschützt werden müssen (ERWEITERT)
        self.protected_abbreviations = {
            # Diagnostik
            "BMI",
            "EKG",
            "MRT",
            "CT",
            "ICD",
            "OPS",
            "DRG",
            "GOÄ",
            "EBM",
            "PET",
            "SPECT",
            # Kardio
            "EF",
            "LAD",
            "RCA",
            "RCX",
            "RIVA",
            "CK",
            "CK-MB",
            "HDL",
            "LDL",
            "VLDL",
            "BNP",
            "NT-proBNP",
            "ANP",
            "AVK",
            "KHK",
            "NYHA",
            "TAVI",
            "PCI",
            "CABG",
            # Hormone & Schilddrüse
            "TSH",
            "fT3",
            "fT4",
            "T3",
            "T4",
            "TPO",
            "TRAK",
            "TG",
            "TAK",
            "MAK",
            "ACTH",
            "ADH",
            "FSH",
            "LH",
            "HCG",
            "PTH",
            "STH",
            "GH",
            "IGF-1",
            "DHEA-S",
            # Diabetes & Stoffwechsel
            "HbA1c",
            "HOMA",
            "OGTT",
            "BZ",
            "BE",
            "HBA1C",
            "C-Peptid",
            # Gerinnung
            "INR",
            "PTT",
            "aPTT",
            "AT3",
            "AT",
            "Quick",
            "TZ",
            "PTZ",
            "ACT",
            "TEG",
            "vWF",
            "ADAMTS13",
            "TAT",
            "F1+2",
            # Entzündung & Infektion
            "CRP",
            "PCT",
            "BSG",
            "ESR",
            "IL-1",
            "IL-2",
            "IL-6",
            "IL-8",
            "IL-10",
            "TNF",
            "TNF-α",
            "IFN",
            "SAA",
            "SR",
            # Tumormarker
            "AFP",
            "CEA",
            "CA",
            "CA19-9",
            "CA125",
            "CA15-3",
            "CA72-4",
            "PSA",
            "fPSA",
            "NSE",
            "SCC",
            "CYFRA",
            "ProGRP",
            "S100",
            "HE4",
            "M2-PK",
            # Vitamine und Nährstoffe
            "D3",
            "D2",
            "B12",
            "B6",
            "B1",
            "B2",
            "B9",
            "K2",
            "K1",
            "E",
            "C",
            "A",
            "25-OH",
            "25-OH-D",
            "25-OH-D3",
            "1,25-OH2",
            "OH-D3",
            "OH-D",
            # Hämatologie
            "GFR",
            "eGFR",
            "GPT",
            "GOT",
            "GGT",
            "AP",
            "ALP",
            "LDH",
            "LDHL",
            "MCH",
            "MCV",
            "MCHC",
            "RDW",
            "RDW-CV",
            "RDW-SD",
            "MPV",
            "PDW",
            "PLT",
            "WBC",
            "RBC",
            "HGB",
            "HCT",
            "HKT",
            "NEUT",
            "LYMPH",
            "LYM",
            "MONO",
            "EOS",
            "BASO",
            "IG",
            "RETI",
            "IRF",
            "LUC",
            "NRBC",
            # Immunologie
            "IgG",
            "IgM",
            "IgA",
            "IgE",
            "IgD",
            "C3",
            "C4",
            "CH50",
            "C1q",
            "ANA",
            "ANCA",
            "c-ANCA",
            "p-ANCA",
            "RF",
            "CCP",
            "ACPA",
            "ENA",
            "dsDNA",
            "Anti-dsDNA",
            "SSA",
            "SSB",
            "Scl-70",
            "Jo-1",
            "RNP",
            # Leber
            "AST",
            "ALT",
            "γ-GT",
            "GLDH",
            "CHE",
            "PCHE",
            "NH3",
            "NH4",
            # Niere
            "CKD-EPI",
            "MDRD",
            "ACR",
            "PCR",
            "BUN",
            # Elektrolyte & Blutgase
            "Na",
            "K",
            "Cl",
            "Ca",
            "P",
            "Mg",
            "Fe",
            "Zn",
            "Cu",
            "Se",
            "pO2",
            "pCO2",
            "pH",
            "HCO3",
            "AG",
            "SaO2",
            "SpO2",
            # Weitere wichtige Abkürzungen
            "diff",
            "BB",
            "KBB",
            "GBB",
            "DiffBB",
            "SSS",
            "AK",
            "HWI",
            "UTI",
            "COPD",
            "ARDS",
            "SIRS",
            "MOF",
            "MOV",
            "DIC",
            "HIT",
            "TTP",
            "HUS",
        }

        # Compile regex patterns
        self.patterns = self._compile_patterns()

    def _initialize_spacy(self):
        """Initialisiert spaCy mit deutschem Modell"""
        if not SPACY_AVAILABLE:
            logger.info("ℹ️ spaCy ist optional - verwende Heuristik-basierte Erkennung")
            self.nlp = None
            self.has_ner = False
            return

        try:
            import os
            from pathlib import Path

            # Try loading from Railway volume first (for worker processes)
            volume_path = os.getenv("SPACY_MODEL_PATH", "/data/spacy_models/de_core_news_sm")

            if Path(volume_path).exists():
                logger.info(f"🔍 Loading spaCy model from volume: {volume_path}")
                self.nlp = spacy.load(volume_path)
                logger.info("✅ spaCy model loaded from Railway volume")
                self.has_ner = True
                return

            # Fallback: Try loading by name
            self.nlp = spacy.load("de_core_news_sm")
            logger.info("✅ spaCy deutsches Modell (de_core_news_sm) geladen")
            self.has_ner = True
        except (OSError, ImportError) as e:
            logger.warning(
                f"⚠️ spaCy Modell nicht verfügbar - verwende eingeschränkten Heuristik-Modus: {e}"
            )
            logger.info("💡 Für bessere Namenerkennung: python -m spacy download de_core_news_sm")
            try:
                # Fallback: Versuche ein leeres deutsches Modell
                self.nlp = spacy.blank("de")
                logger.info("📦 Verwende spaCy blank model als Fallback (ohne NER)")
                self.has_ner = False
            except Exception as e2:
                logger.warning(
                    f"⚠️ spaCy Initialisierung fehlgeschlagen - verwende reine Heuristik: {e2}"
                )
                self.nlp = None
                self.has_ner = False

    def _compile_patterns(self) -> dict[str, Pattern[str]]:
        """Kompiliert Regex-Patterns für verschiedene PII-Typen"""
        return {
            # Geburtsdaten - matches "Geb.: 15.05.1965", "geb. 15.05.1965", etc.
            "birthdate": re.compile(
                r"\b(?:geb(?:oren)?\.?:?\s*(?:am\s*)?|geboren\s+am\s+|geburtsdatum:?\s*)"
                r"(?:\d{1,2}[\.\/-]\d{1,2}[\.\/-]\d{2,4}|\d{4}[\.\/-]\d{1,2}[\.\/-]\d{1,2})",
                re.IGNORECASE,
            ),
            # Explizite Patienteninfo - VERBESSERT für "Patient: Nachname, Vorname"
            "patient_info": re.compile(
                r"\b(?:patient(?:in)?|name|versicherte[rn]?|nachname|vorname)[:\s]*"
                r"([A-ZÄÖÜ][a-zäöüß]+(?:[\s,]+[A-ZÄÖÜ][a-zäöüß]+)*)",
                re.IGNORECASE,
            ),
            # Spezielles Pattern für "Nachname, Vorname" Format
            "name_format": re.compile(
                r"\b(?:patient|name)[:\s]+([A-ZÄÖÜ][a-zäöüß]+)\s*,\s*([A-ZÄÖÜ][a-zäöüß]+)",
                re.IGNORECASE,
            ),
            # Adressen
            "street_address": re.compile(
                r"\b[A-ZÄÖÜ][a-zäöüß]+(?:straße|str\.?|weg|allee|platz|ring|gasse|damm)\s+\d+[a-z]?\b",
                re.IGNORECASE,
            ),
            # PLZ + Stadt
            "plz_city": re.compile(r"\b\d{5}\s+[A-ZÄÖÜ][a-zäöüß]+(?:\s+[A-ZÄÖÜ][a-zäöüß]+)*\b"),
            # Telefon - German phone numbers
            # International: +49/0049 + any digits; National: 0 + at least 2 more digits
            "phone": re.compile(
                r"(?:^|\s)(?:(?:\+49|0049)\s*\d+(?:[\s\-\(\)\/]\d+)*|0\d{2,}(?:[\s\-\(\)\/]\d+)*)",
            ),
            # E-Mail
            "email": re.compile(r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b"),
            # Versicherungsnummern - handles compound words
            # Uses "patienten" not "patient" to avoid matching "Patient: Name"
            "insurance": re.compile(
                r"\b(?:versicherungs?|versichert\w*|kassen|patienten\w*|fall|akte)[\-\s]*(?:nr\.?|nummer)?[:\s]*[A-Z0-9][\w\-\/]*\b",
                re.IGNORECASE,
            ),
            # Anreden
            "salutation": re.compile(
                r"^(?:sehr\s+geehrte[rns]?\s+.*?[,!]|"
                r"(?:mit\s+)?(?:freundlichen|besten|herzlichen)\s+grüßen.*?$|"
                r"hochachtungsvoll.*?$)",
                re.IGNORECASE | re.MULTILINE,
            ),
        }

    def remove_pii(self, text: str) -> str:
        """Remove personally identifiable information while preserving medical content.

        GDPR-compliant PII removal using a multi-stage approach:
        1. Protect medical terms (temporary placeholders)
        2. Remove explicit PII patterns (regex)
        3. Remove names (spaCy NER or heuristic fallback)
        4. Restore protected medical terms
        5. Clean formatting

        Args:
            text: German medical document text to be anonymized

        Returns:
            Anonymized text with PII removed but medical information preserved.
            PII is replaced with markers like [NAME ENTFERNT], [ADRESSE ENTFERNT].

        Example:
            >>> filter = AdvancedPrivacyFilter()
            >>> doc = '''
            ... Patient: Müller, Hans
            ... Geb.: 01.01.1980
            ... Diagnose: Diabetes mellitus Typ 2
            ... HbA1c: 8.2%
            ... '''
            >>> cleaned = filter.remove_pii(doc)
            >>> assert "Müller" not in cleaned
            >>> assert "01.01.1980" not in cleaned
            >>> assert "Diabetes" in cleaned
            >>> assert "HbA1c" in cleaned
        """
        if not text:
            return text

        logger.info("🔍 Entferne persönliche Daten, behalte medizinische Informationen")

        # Schütze medizinische Begriffe vor Entfernung
        text = self._protect_medical_terms(text)

        # 1. Entferne alle persönlichen Daten (außer medizinische)
        text = self._remove_personal_data(text)

        # 2. Entferne Namen mit spaCy
        if self.nlp and self.has_ner:
            text = self._remove_names_with_ner(text)
        else:
            # Fallback: Heuristische Namenerkennung
            text = self._remove_names_heuristic(text)

        # 3. Stelle medizinische Begriffe wieder her
        text = self._restore_medical_terms(text)

        # 4. Formatierung bereinigen
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"[ \t]+", " ", text)

        logger.info("✅ Persönliche Daten entfernt - medizinische Informationen erhalten")
        return text.strip()

    def _protect_medical_terms(self, text: str) -> str:
        """Schützt medizinische Begriffe vor Entfernung"""
        import re

        # Schütze Vitamin-Kombinationen (z.B. "Vitamin D3", "Vitamin B12")
        vitamin_pattern = (
            r"\b(Vitamin|Vit\.?)\s*([A-Z][0-9]*|[0-9]+[-,]?[0-9]*[-]?OH[-]?[A-Z]?[0-9]*)\b"
        )
        text = re.sub(vitamin_pattern, r"§VITAMIN_\2§", text, flags=re.IGNORECASE)

        # Schütze Laborwert-Kombinationen mit Zahlen (z.B. "25-OH-D3", "1,25-OH2-D3")
        lab_pattern = r"\b([0-9]+[,.]?[0-9]*[-]?OH[0-9]*[-]?[A-Z]?[0-9]*)\b"
        text = re.sub(lab_pattern, r"§LAB_\1§", text, flags=re.IGNORECASE)

        # Schütze Laborwert-Zahlen-Kombinationen in Tabellen (z.B. "Hämoglobin 12.5")
        # Pattern: Laborwert gefolgt von Zahl und Einheit
        for term in self.medical_terms:
            if len(term) > 3:  # Nur längere Begriffe
                pattern = (
                    r"\b(" + re.escape(term) + r")\s*:?\s*([0-9]+[,.]?[0-9]*)\s*([a-zA-Z/%]*)\b"
                )
                text = re.sub(pattern, r"§LABVAL_\1_\2_\3§", text, flags=re.IGNORECASE)

        # Ersetze medizinische Abkürzungen temporär
        for abbr in self.protected_abbreviations:
            # Case-insensitive replacement mit Wortgrenzen
            pattern = r"\b" + re.escape(abbr) + r"\b"
            text = re.sub(pattern, f"§{abbr}§", text, flags=re.IGNORECASE)

        return text

    def _restore_medical_terms(self, text: str) -> str:
        """Stellt geschützte medizinische Begriffe wieder her"""
        import re

        # Stelle Vitamin-Kombinationen wieder her
        text = re.sub(r"§VITAMIN_([^§]+)§", r"Vitamin \1", text)

        # Stelle Laborwert-Kombinationen wieder her
        text = re.sub(r"§LAB_([^§]+)§", r"\1", text)

        # Stelle Laborwert-Zahlen-Kombinationen wieder her
        text = re.sub(r"§LABVAL_([^_§]+)_([^_§]+)_([^§]*)§", r"\1 \2 \3", text)

        # Stelle normale Abkürzungen wieder her
        for abbr in self.protected_abbreviations:
            text = text.replace(f"§{abbr}§", abbr)

        return text

    def _remove_personal_data(self, text: str) -> str:
        """Entfernt persönliche Daten aber ERHÄLT medizinische Informationen"""

        # CRITICAL ORDER: Remove birthdates FIRST before other patterns
        # This prevents phone/insurance patterns from matching parts of dates
        text = self.patterns["birthdate"].sub("[GEBURTSDATUM ENTFERNT]", text)

        # IMPORTANT: Remove insurance/patient numbers BEFORE patient_info pattern
        # to avoid partial matches on compound words like "Versichertennummer"
        text = self.patterns["insurance"].sub("[NUMMER ENTFERNT]", text)

        # Now remove explicit patient name patterns
        text = self.patterns["patient_info"].sub("[NAME ENTFERNT]", text)
        text = self.patterns["name_format"].sub("[NAME ENTFERNT]", text)

        # Adressen entfernen
        text = self.patterns["street_address"].sub("[ADRESSE ENTFERNT]", text)
        text = self.patterns["plz_city"].sub("[PLZ/ORT ENTFERNT]", text)

        # Kontaktdaten entfernen
        text = self.patterns["phone"].sub("[TELEFON ENTFERNT]", text)
        text = self.patterns["email"].sub("[EMAIL ENTFERNT]", text)

        # Anreden und Grußformeln entfernen
        text = self.patterns["salutation"].sub("", text)

        # Geschlecht entfernen (wenn explizit als "Geschlecht:" angegeben)
        return re.sub(
            r"\b(?:geschlecht)[:\s]*(?:männlich|weiblich|divers|m|w|d)\b",
            "[GESCHLECHT ENTFERNT]",
            text,
            flags=re.IGNORECASE,
        )

    def _remove_names_with_ner(self, text: str) -> str:
        """
        Verwendet spaCy NER zur intelligenten Namenerkennung
        Erkennt auch "Name: Nachname, Vorname" Format
        """
        # HINWEIS: Explizite Patterns wurden bereits in _remove_personal_data entfernt
        # Hier nur noch spaCy NER für nicht-explizite Namen

        # Verarbeite Text mit spaCy
        doc = self.nlp(text)

        # Sammle alle erkannten Personen-Entitäten
        persons_to_remove = set()

        for ent in doc.ents:
            # NUR PER = Person, ignoriere ORG, LOC etc.
            if ent.label_ == "PER":
                # Prüfe ob es ein medizinischer Begriff ist
                if ent.text.lower() not in self.medical_terms:
                    # Keine Zahlen im Namen (könnte Laborwert sein)
                    if not any(char.isdigit() for char in ent.text):
                        persons_to_remove.add(ent.text)
                        logger.debug(f"NER erkannt als Person: {ent.text}")

        # Zusätzlich: Erkenne Titel+Name Kombinationen
        for i, token in enumerate(doc):
            if token.text.lower() in ["dr.", "prof.", "herr", "frau", "dr", "prof"]:
                # Sammle die nächsten 1-2 Tokens als Namen
                name_parts = []
                for j in range(1, min(3, len(doc) - i)):
                    next_token = doc[i + j]
                    if (
                        next_token.text[0].isupper()
                        and len(next_token.text) > 2
                        and not any(char.isdigit() for char in next_token.text)
                        and next_token.text.lower() not in self.medical_terms
                    ):
                        name_parts.append(next_token.text)

                if name_parts:
                    full_name = " ".join(name_parts)
                    persons_to_remove.add(full_name)
                    logger.debug(f"Titel+Name erkannt: {token.text} {full_name}")

        # Entferne nur die sicher erkannten Namen
        result = text
        for person in persons_to_remove:
            # Ersetze den Namen überall im Text
            result = re.sub(
                r"\b" + re.escape(person) + r"\b", "[NAME ENTFERNT]", result, flags=re.IGNORECASE
            )

        # Entferne Titel die alleine stehen (aber nur am Zeilenanfang)
        return re.sub(
            r"^(?:Dr\.?|Prof\.?|Herr|Frau)\s*(?:\n|$)",
            "",
            result,
            flags=re.IGNORECASE | re.MULTILINE,
        )

    def _remove_names_heuristic(self, text: str) -> str:
        """
        Heuristische Namenerkennung als Fallback
        Erkennt Namen basierend auf Mustern und Kontext
        """
        # Remove doctor signatures like "Dr. med. Schmidt" or "Prof. Dr. Müller"
        text = re.sub(
            r"\b(?:Dr\.?|Prof\.?)\s+(?:med\.?\s+|Dr\.?\s+)?[A-ZÄÖÜ][a-zäöüß]+\b",
            "[NAME ENTFERNT]",
            text
        )

        lines = text.split("\n")
        cleaned_lines = []

        for line in lines:
            # Entferne Zeilen mit typischen Namensmustern
            # z.B. "Dr. Hans Müller" oder "Frau Maria Schmidt"
            if re.match(r"^\s*(?:Dr\.?|Prof\.?|Herr|Frau)\s+[A-ZÄÖÜ]", line):
                # Prüfe ob die Zeile medizinische Begriffe enthält
                line_lower = line.lower()
                contains_medical = any(term in line_lower for term in self.medical_terms)
                if not contains_medical:
                    continue  # Skip diese Zeile

            # HINWEIS: Patient-Info Patterns wurden bereits in _remove_personal_data entfernt

            # Erkenne potenzielle Namen (2-3 aufeinanderfolgende kapitalisierte Wörter)
            # aber nur wenn sie nicht medizinisch sind
            def replace_name(match):
                words = match.group(0).split()
                # Prüfe ob eines der Wörter ein medizinischer Begriff ist
                for word in words:
                    if word.lower() in self.medical_terms or "§" in word:
                        return match.group(0)  # Behalte es
                # Wenn keines medizinisch ist, könnte es ein Name sein
                if len(words) >= 2:
                    return ""
                return match.group(0)

            # Pattern für potenzielle Namen (2-3 kapitalisierte Wörter)
            line = re.sub(
                r"\b[A-ZÄÖÜ][a-zäöüß]+(?:\s+[A-ZÄÖÜ][a-zäöüß]+){1,2}\b", replace_name, line
            )

            cleaned_lines.append(line)

        return "\n".join(cleaned_lines)

    def _remove_dates_and_gender(self, text: str) -> str:
        """Entfernt Datumsangaben die Geburtsdaten sein könnten"""

        # Datumsformat prüfen (könnte Geburtsdatum sein)
        def check_date(match):
            date_str = match.group(0)
            # Extrahiere Jahr wenn möglich
            year_match = re.search(r"(19|20)\d{2}", date_str)
            if year_match:
                year = int(year_match.group(0))
                # Geburtsjahre typischerweise zwischen 1920 und 2010
                if 1920 <= year <= 2010:
                    # Aber behalte aktuelle Daten (Untersuchungsdaten)
                    import datetime

                    current_year = datetime.datetime.now().year
                    if year < current_year - 1:  # Älter als letztes Jahr
                        return "[DATUM ENTFERNT]"
            return date_str

        # Prüfe Datumsangaben
        date_pattern = re.compile(r"\b\d{1,2}[\.\/\-]\d{1,2}[\.\/\-](?:19|20)\d{2}\b")
        return date_pattern.sub(check_date, text)

    def validate_medical_content(self, original: str, cleaned: str) -> bool:
        """
        Validiert, dass medizinische Inhalte erhalten geblieben sind

        Returns:
            True wenn mindestens 80% der medizinischen Begriffe erhalten sind
        """
        medical_keywords = [
            "diagnose",
            "befund",
            "labor",
            "medikament",
            "therapie",
            "mg",
            "ml",
            "mmol",
            "icd",
            "ops",
            "untersuchung",
            "hämoglobin",
            "leukozyten",
            "erythrozyten",
            "thrombozyten",
            "glucose",
            "kreatinin",
            "cholesterin",
        ]

        original_lower = original.lower()
        cleaned_lower = cleaned.lower()

        original_count = sum(1 for kw in medical_keywords if kw in original_lower)
        cleaned_count = sum(1 for kw in medical_keywords if kw in cleaned_lower)

        if original_count > 0:
            preservation_rate = cleaned_count / original_count
            return preservation_rate >= 0.8

        return True
