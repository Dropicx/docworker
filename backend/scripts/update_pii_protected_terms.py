#!/usr/bin/env python3
"""
Update PII protected medical terms in the database.

Adds new medical terms to privacy_filter.custom_medical_terms in system_settings.
These terms were identified from production analysis as being incorrectly removed
by the PII service.

Usage:
    # Dry run (show what would be added)
    python scripts/update_pii_protected_terms.py --dry-run

    # Update dev database
    python scripts/update_pii_protected_terms.py --env dev

    # Update production database
    python scripts/update_pii_protected_terms.py --env prod
"""

import argparse
import json
import os
import sys
from sqlalchemy import create_engine, text

# Database URLs
DEV_DB_URL = os.getenv(
    "DEV_DATABASE_URL",
    "postgresql://postgres:KfcqZpqRnRCTyvVxHKkDHjssedAjXZSp@turntable.proxy.rlwy.net:58299/railway",
)
PROD_DB_URL = os.getenv(
    "PROD_DATABASE_URL",
    "postgresql://postgres:VknAapdgHdGkHjkmsyHWsJyKCspFmqzO@gondola.proxy.rlwy.net:15456/railway",
)

# New medical terms to add (identified from production analysis 2025-01)
# These terms were incorrectly removed/anonymized by the PII service
NEW_TERMS = [
    # Substance abuse terms (commonly misclassified as NAME)
    "Cannabisabusus",
    "Cannabis",
    "Drogenabusus",
    "Medikamentenabusus",
    "Polytoxikomanie",
    "Nikotinabusus",
    "Alkoholabusus",
    "Abusus",
    # Liver conditions (commonly misclassified as NAME)
    "Stauungsleber",
    # Cardiac valve conditions (commonly misclassified as NAME/removed)
    "Trikuspidalinsuffizienz",
    "Trikuspidalklappeninsuffizienz",
    "Trikuspidalsuffizienz",  # Variant spelling (missing 'in')
    "Mitralklappeninsuffizienz",
    "Aortenklappeninsuffizienz",
    "Pulmonalklappeninsuffizienz",
    "Klappeninsuffizienz",
    "Herzinsuffizienz",
    "Rechtsherzinsuffizienz",
    "Linksherzinsuffizienz",
    # Clinical findings (commonly misclassified as NAME)
    "Blutungsstigmata",
    "Stigmata",
    # Lung anatomy - carina terms (commonly removed)
    "Mittellappenkarina",
    "Mittellappencarina",
    "Karina",
    "Carina",
    "Hauptkarina",
    "Hauptcarina",
    # Severity descriptors (commonly misclassified)
    "Höchstgradig",
    "Höchstgradige",
    "Höchstgradiger",
    "Höchstgradiges",
    "Hochgradig",
    "Hochgradige",
    "Hochgradiger",
    "Hochgradiges",
    "Mittelgradig",
    "Mittelgradige",
    "Mittelgradiger",
    "Geringgradig",
    "Geringgradige",
    "Geringgradiger",
    "Höhergradig",
    "Höhergradige",
    "Höhergradiger",
    # Other medical terms (commonly removed/misclassified)
    "Lungenbeteiligung",
    "Leberbeteiligung",
    "Nierenbeteiligung",
    "Voraufnahme",
    "Voraufnahmen",
    "Voruntersuchung",
    "Voruntersuchungen",
    # Procedure variants (including common typos)
    "Appendektimie",
    "Appendektomie",
    # ==================== SARKOIDOSE DOCUMENT TERMS (2025-01) ====================
    # Joint/body parts (commonly misclassified as ORGANIZATION)
    "Sprunggelenk",
    "Sprunggelenke",
    "Sprunggelenken",
    "Vorfuß",
    "Vorfüße",
    "Fußgelenk",
    "Fußgelenke",
    # Imaging modalities (commonly misclassified as ORGANIZATION)
    "CT-Thorax",
    "CT Thorax",
    "MRT-Thorax",
    "MRT Thorax",
    "PET-CT",
    "PET/CT",
    "SPECT-CT",
    # Bronchoscopy procedures and equipment (commonly misclassified as ORGANIZATION)
    "EBUS",
    "Endobronchialerultraschall",
    "Endobronchialer Ultraschall",
    "Ultraschallbronchoskop",
    "Ultraschallbronchoskops",
    # Bronchoscopy procedures (commonly misclassified as LOCATION)
    "Spülungen",
    "Spülung",
    "Lavagen",
    "Lavage",
    "Bronchoalveoläre Lavage",
    "Bronchoalveolärelavage",
    # Bronchial anatomy - karina/carina terms (commonly misclassified as LOCATION)
    "Oberlappenkarina",
    "Unterlappenkarina",
    "Hauptbronchus",
    "Oberlappenbronchus",
    "Mittellappenbronchus",
    "Unterlappenbronchus",
    "Segmentbronchus",
    "Segmentbronchien",
    "Bifurkation",
    "Trachealbifurkation",
    # Cell surface markers (commonly misclassified as LOCATION)
    "CD19",
    "CD19+",
    "CD3",
    "CD3+",
    "CD4",
    "CD4+",
    "CD8",
    "CD8+",
    "CD16",
    "CD16+",
    "CD56",
    "CD56+",
    "CD45",
    "CD45+",
    "HLA-DR",
    "HLA-DR+",
    # ==================== ALTINDAG DOCUMENT ANALYSIS (2025-01) ====================
    # Joint abbreviations (commonly misclassified as ORGANIZATION)
    "OSG",
    "USG",  # Oberes/Unteres Sprunggelenk
    "OSG-Arthritis",
    "OSG-Arthrose",
    # Lung segment/carina abbreviations (commonly misclassified as ORGANIZATION)
    "OL Karina",
    "OL-Karina",  # Oberlappen Karina
    "UL Karina",
    "UL-Karina",  # Unterlappen Karina
    "ML Karina",
    "ML-Karina",  # Mittellappen Karina
    # Carina variant spellings with 'c' (commonly misclassified as LOCATION)
    "Oberlappencarina",
    "Unterlappencarina",
    "Mittellappencarina",
    # Clinical density terms (commonly misclassified when combined with anatomy)
    "Verdichte",
    "Verdichtete",
    "Verdichteter",
    "Verdichtung",
    "Verdichtungen",
    # ==================== FISCHELL DOCUMENT ANALYSIS (2025-01) ====================
    # Cardiac abbreviations (commonly misclassified as ORGANIZATION)
    "TI",
    "MI",
    "AI",
    "PI",  # Valve insufficiency abbreviations
    "HFrEF",
    "HFpEF",
    "HFmrEF",  # Heart failure types
    "LVEF",
    "RVEF",  # Ejection fraction
    "CRT",
    "CRT-D",
    "CRT-P",  # Cardiac resynchronization therapy
    "ICD",
    "S-ICD",  # Implantable cardioverter-defibrillator
    # Pacemaker modes
    "VVI",
    "VVIR",
    "DDD",
    "DDDR",
    "AAI",
    "AAIR",
    "VOO",
    "DOO",
    "LV Stimulation",
    "RV Stimulation",
    # Pacemaker manufacturers and models
    "Biotronik",
    "Medtronic",
    "Boston Scientific",
    "Abbott",
    "St. Jude",
    "Etrinsa",
    "Evia",
    "Edora",
    "Entovis",
    "Eluna",
    "DR-T",
    "SR-T",
    "HF-T",
    # Cardiac electrophysiology terms
    "AV-junktional",
    "AV-junktionalen",
    "AV-junktionaler",
    "AV-Block",
    "AV-Knoten",
    "AV-Überleitung",
    "Ersatzrhythmus",
    "Junktionalrhythmus",
    # Cardiac procedures
    "Cryo",
    "Cryo-Ballon",
    "Cryoballon",
    "Kryoballon",
    "Pulmonalvenenablation",
    "Pulmonalvenenisolation",
    "PVI",
    "Elektrokardioversion",
    "Elektrokardioversionen",
    # Lab value abbreviations
    "RPI",
    "IRF",
    "HB",
    "Hb",
    "Hgb",
    "Herz-Thorax-Quotient",
    "HTQ",
    "CTR",
    # Medications
    "Torasemid",
    "Furosemid",
    "Spironolacton",
    "Eplerenon",
    "Prednisolon",
    "Colchicin",
    "Rivaroxaban",
    "Apixaban",
    "Edoxaban",
    # Latin medical terms
    "domo",
    "in domo",
    "loco",
    "in loco",
    # ==================== PAAR DOCUMENT ANALYSIS (2025-01) ====================
    # Microbiology terms (commonly misclassified as BIC/ORGANIZATION)
    "KEIMZAHL",
    "Keimzahl",
    "keimzahl",  # Colony count
    "KBE",
    "KBE/ml",
    "KbE",  # Koloniebildende Einheiten (CFU)
    "CFU",
    "CFU/ml",  # Colony forming units
    "KULTURBEFUND",
    "Kulturbefund",  # Culture findings
    "ANTIBIOGRAMM",
    "Antibiogramm",  # Antibiogram
    # Urine collection methods
    "Mittelstrahlurin",
    "Mittelstrahl-Urin",
    "Mittelstrahl",
    "Katheterurin",
    "Spontanurin",
    "Morgenurin",
    "Sammelurin",
    # Microbiology organisms (commonly appearing in culture results)
    "Morganella",
    "Morganella morganii",
    "Enterococcus",
    "Enterococcus spp",
    "Escherichia",
    "Escherichia coli",
    "E. coli",
    "Klebsiella",
    "Pseudomonas",
    "Staphylococcus",
    "Streptococcus",
    # Antibiotic resistance markers
    "MRSA",
    "ESBL",
    "VRE",
    "MRGN",
    # Lab test abbreviations
    "Nit",
    "Leu",
    "Bakt",
    "Ket",
    "Bil",
    "Glu",
    "Eiw",
    # ==================== KRÜGER DOCUMENT ANALYSIS (2025-01) ====================
    # Laboratory test methods (commonly misclassified as BIC/ORGANIZATION)
    "IMMUNOASSAY",
    "Immunoassay",
    "immunoassay",  # Lab test method - wrongly replaced with [BIC]
    "ANTIGENNACHWEIS",
    "Antigennachweis",  # Antigen detection
    "MOLEKULARBIOLOGISCHER",
    "Molekularbiologischer",
    "molekularbiologischer",
    "DIREKTNACHWEIS",
    "Direktnachweis",
    "ELISA",
    "EIA",
    "RIA",
    "CLIA",
    "ECLIA",  # Immunoassay types
    "PCR",
    "RT-PCR",
    "qPCR",  # Molecular tests
    # Pathogen names (appearing in lab results)
    "C. difficile",
    "Clostridioides difficile",
    "Clostridium difficile",
    "GDH-AG",
    "GDH",  # Glutamate dehydrogenase antigen
    "Staph",
    "Staph.",
    "Staphylococcus epidermidis",
    "Staphylococcus capitis",
    "Staphylococcus aureus",
    "S. aureus",
    "S. epidermidis",
    # Liver disease terms
    "MELD",
    "MELD-Score",
    "MELD-Na",
    "Child-Pugh",
    "Child A",
    "Child B",
    "Child C",
    "TIPPS",
    "TIPS",  # Transjugular intrahepatic portosystemic shunt
    "Parazentese",
    "Aszitespunktion",
    "Aszitesdrainage",
    # Anatomical terms (lung hilum)
    "perihilär",
    "infrahilär",
    "hilär",
    "Hilus",
    # Medical eponyms (conditions named after people)
    "Mallory-Weiss",
    "Mallory-Weiss-Syndrom",
    "Mallory-Weiss-Riss",
    # Medication
    "Terlipressin",
    "Albumin",
    "Albuminsubstitution",
    # Clinical abbreviations
    "DNR",
    "DNI",
    "DNR/DNI",  # Do not resuscitate/intubate
    # ==================== KAMES DOCUMENT ANALYSIS (2025-01) ====================
    # Patient/Patientin - German words for patient, NOT names!
    # These are commonly misdetected as PERSON entities
    "Patient",
    "Patientin",
    "Patienten",
    "Patientinnen",
    "Pat",
    "Pat.",  # Abbreviations
    # General condition terms
    "AZ-reduziert",
    "AZ-reduzierte",
    "AZ-reduzierter",
    "AZ-reduzierten",
    "allgemeinzustandsreduziert",
    "allgemeinzustandsreduzierte",
    # Cytology/pathology terms
    "Zytologie",
    "Zytologisch",
    "Zytologische",
    "Histologie",
    "Histologisch",
    "Histologische",
    "Pathologie",
    "Pathologisch",
    "Pathologische",
    # ==================== OCR TYPO FIXES (2025-02) ====================
    # Common OCR errors that get misclassified as entities
    # "Nächliche" is OCR typo of "Nächtliche" (nocturnal) - misclassified as LOCATION
    "Nächliche",
    "nächliche",  # lowercase variant
]


def connect_db(db_url: str, name: str):
    """Connect to database."""
    try:
        engine = create_engine(db_url, pool_pre_ping=True)
        conn = engine.connect()
        print(f"Connected to {name} database")
        return engine, conn
    except Exception as e:
        print(f"Failed to connect to {name} database: {e}")
        sys.exit(1)


def get_current_terms(conn) -> list:
    """Get current custom medical terms from database."""
    result = conn.execute(
        text("""
        SELECT value FROM system_settings
        WHERE key = 'privacy_filter.custom_medical_terms'
    """)
    )
    row = result.fetchone()

    if row and row[0]:
        try:
            return json.loads(row[0])
        except json.JSONDecodeError:
            print("Warning: Invalid JSON in existing custom_medical_terms")
            return []
    return []


def update_terms(conn, terms: list, dry_run: bool = False) -> int:
    """Update or insert custom medical terms in database."""
    terms_json = json.dumps(terms, ensure_ascii=False, indent=2)

    # Check if setting exists
    result = conn.execute(
        text("""
        SELECT id FROM system_settings
        WHERE key = 'privacy_filter.custom_medical_terms'
    """)
    )
    existing = result.fetchone()

    if dry_run:
        if existing:
            print("\nDRY RUN: Would UPDATE existing setting")
        else:
            print("\nDRY RUN: Would INSERT new setting")
        print(f"Terms count: {len(terms)}")
        return len(terms)

    if existing:
        conn.execute(
            text("""
            UPDATE system_settings
            SET value = :value, updated_at = NOW()
            WHERE key = 'privacy_filter.custom_medical_terms'
        """),
            {"value": terms_json},
        )
    else:
        conn.execute(
            text("""
            INSERT INTO system_settings (key, value, value_type, created_at, updated_at)
            VALUES ('privacy_filter.custom_medical_terms', :value, 'json', NOW(), NOW())
        """),
            {"value": terms_json},
        )

    conn.commit()
    return len(terms)


def main():
    parser = argparse.ArgumentParser(description="Update PII protected medical terms")
    parser.add_argument(
        "--env", choices=["dev", "prod"], default="dev", help="Database environment (default: dev)"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be updated without making changes"
    )
    args = parser.parse_args()

    print("=" * 60)
    print("PII PROTECTED TERMS UPDATE")
    print("=" * 60)

    # Select database
    if args.env == "prod":
        db_url = PROD_DB_URL
        db_name = "PRODUCTION"
    else:
        db_url = DEV_DB_URL
        db_name = "DEVELOPMENT"

    if args.dry_run:
        print(f"\nDRY RUN MODE - No changes will be made")

    print(f"\nTarget: {db_name}")

    # Connect
    engine, conn = connect_db(db_url, db_name)

    try:
        # Get current terms
        current_terms = get_current_terms(conn)
        print(f"\nCurrent custom terms: {len(current_terms)}")
        if current_terms:
            print(f"  First 10: {current_terms[:10]}")

        # Merge with new terms (avoid duplicates, case-insensitive)
        current_lower = {t.lower() for t in current_terms}
        new_to_add = [t for t in NEW_TERMS if t.lower() not in current_lower]

        print(f"\nNew terms to add: {len(new_to_add)}")
        if new_to_add:
            for term in new_to_add:
                print(f"  + {term}")

        # Merge lists
        merged_terms = current_terms + new_to_add
        print(f"\nTotal terms after merge: {len(merged_terms)}")

        # Update database
        if new_to_add:
            count = update_terms(conn, merged_terms, dry_run=args.dry_run)
            if args.dry_run:
                print(f"\nDRY RUN: Would update to {count} terms")
            else:
                print(f"\nUpdated database with {count} terms")
        else:
            print("\nNo new terms to add - database already up to date")

    finally:
        conn.close()
        engine.dispose()

    print("\nDone!")


if __name__ == "__main__":
    main()
