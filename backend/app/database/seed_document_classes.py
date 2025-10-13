"""
Seed Default Document Classes

Creates the three default medical document classes:
- ARZTBRIEF (Doctor's letters)
- BEFUNDBERICHT (Medical reports)
- LABORWERTE (Lab results)

These are marked as system classes and cannot be deleted.
"""

import logging

from sqlalchemy.orm import Session

from app.database.connection import get_session
from app.database.modular_pipeline_models import DocumentClassDB

logger = logging.getLogger(__name__)

DEFAULT_DOCUMENT_CLASSES = [
    {
        "class_key": "ARZTBRIEF",
        "display_name": "Arztbrief",
        "description": "Briefe zwischen Ärzten, Entlassungsbriefe, Überweisungen",
        "icon": "📨",
        "examples": [
            "Entlassungsbrief",
            "Überweisungsschreiben",
            "Konsiliarbericht",
            "Therapiebericht"
        ],
        "strong_indicators": [
            "sehr geehrte",
            "liebe kollegin",
            "lieber kollege",
            "mit freundlichen grüßen",
            "hochachtungsvoll",
            "gez.",
            "entlassung",
            "entlassen",
            "überweisung",
            "überweisen",
            "vorstellung",
            "konsil",
            "therapiebericht"
        ],
        "weak_indicators": [
            "patient wurde",
            "anamnese",
            "diagnose",
            "therapie",
            "empfehlung",
            "weiteres vorgehen",
            "rückfragen"
        ],
        "is_enabled": True,
        "is_system_class": True,
        "created_by": "system_seed"
    },
    {
        "class_key": "BEFUNDBERICHT",
        "display_name": "Befundbericht",
        "description": "Medizinische Befunde, Untersuchungsergebnisse, Bildgebung",
        "icon": "🔬",
        "examples": [
            "MRT-Befund",
            "CT-Bericht",
            "Ultraschallbefund",
            "Pathologiebefund"
        ],
        "strong_indicators": [
            "befund",
            "befundbericht",
            "untersuchung vom",
            "röntgen",
            "ct",
            "mrt",
            "mri",
            "ultraschall",
            "sonographie",
            "szintigraphie",
            "pet",
            "angiographie",
            "mammographie",
            "darstellung",
            "kontrastmittel",
            "schnittbild",
            "aufnahme"
        ],
        "weak_indicators": [
            "auffällig",
            "unauffällig",
            "verdacht",
            "hinweis",
            "tumor",
            "metastase",
            "zyste",
            "knoten",
            "herd",
            "fraktur",
            "läsion",
            "infiltrat",
            "erguss"
        ],
        "is_enabled": True,
        "is_system_class": True,
        "created_by": "system_seed"
    },
    {
        "class_key": "LABORWERTE",
        "display_name": "Laborwerte",
        "description": "Laborergebnisse, Blutwerte, Messwerte mit Referenzbereichen",
        "icon": "🧪",
        "examples": [
            "Blutbild",
            "Urinanalyse",
            "Hormonwerte",
            "Tumormarker"
        ],
        "strong_indicators": [
            "laborwerte",
            "blutwerte",
            "blutbild",
            "hämatologie",
            "mg/dl",
            "mmol/l",
            "µg/l",
            "u/l",
            "g/dl",
            "pg/ml",
            "referenzbereich",
            "normalbereich",
            "norm",
            "referenz",
            "hba1c",
            "cholesterin",
            "ldl",
            "hdl",
            "triglyceride",
            "kreatinin",
            "gfr",
            "tsh",
            "psa",
            "ck",
            "troponin"
        ],
        "weak_indicators": [
            "erhöht",
            "erniedrigt",
            "normal",
            "pathologisch",
            "urin",
            "urinstatus",
            "urinkultur",
            "bakterien",
            "keime",
            "resistenz",
            "antibiogramm"
        ],
        "is_enabled": True,
        "is_system_class": True,
        "created_by": "system_seed"
    }
]


def seed_document_classes(session: Session = None):
    """
    Seed default document classes into the database.

    Args:
        session: Optional database session. If not provided, creates a new one.
    """
    close_session = False
    if session is None:
        session = next(get_session())
        close_session = True

    try:
        logger.info("🌱 Seeding default document classes...")

        for class_data in DEFAULT_DOCUMENT_CLASSES:
            # Check if class already exists
            existing = session.query(DocumentClassDB).filter_by(
                class_key=class_data["class_key"]
            ).first()

            if existing:
                logger.info(f"   ✓ Document class '{class_data['class_key']}' already exists, skipping")
                continue

            # Create new document class
            doc_class = DocumentClassDB(**class_data)
            session.add(doc_class)
            logger.info(f"   ✅ Created document class: {class_data['class_key']} - {class_data['display_name']}")

        session.commit()
        logger.info("✅ Document class seeding completed successfully!")

    except Exception as e:
        logger.error(f"❌ Error seeding document classes: {e}")
        session.rollback()
        raise

    finally:
        if close_session:
            session.close()


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Run seeding
    seed_document_classes()
