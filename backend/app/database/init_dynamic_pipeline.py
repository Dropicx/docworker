"""
Initialize Dynamic Pipeline System

Creates database tables and seeds initial data for the dynamic pipeline system:
1. Creates all modular pipeline tables
2. Seeds default document classes (ARZTBRIEF, BEFUNDBERICHT, LABORWERTE)

Run this script to set up the dynamic pipeline database structure.
"""

import logging

from sqlalchemy import inspect

from app.database.connection import engine, get_session
from app.database.modular_pipeline_models import Base
from app.database.seed_document_classes import seed_document_classes

logger = logging.getLogger(__name__)


def create_tables():
    """Create all tables for the dynamic pipeline system"""
    logger.info("📋 Creating dynamic pipeline tables...")

    # Get existing tables
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()

    # Create tables
    Base.metadata.create_all(bind=engine, checkfirst=True)

    # Check which tables were created
    new_tables = set(inspector.get_table_names()) - set(existing_tables)

    if new_tables:
        logger.info(f"   ✅ Created {len(new_tables)} new tables: {', '.join(sorted(new_tables))}")
    else:
        logger.info("   ✓ All tables already exist")

    logger.info("✅ Table creation completed!")


def initialize_dynamic_pipeline():
    """
    Initialize the dynamic pipeline system:
    1. Create tables
    2. Seed document classes
    """
    logger.info("🚀 Initializing Dynamic Pipeline System")
    logger.info("=" * 60)

    try:
        # Step 1: Create tables
        create_tables()

        # Step 2: Seed document classes
        session = next(get_session())
        try:
            seed_document_classes(session)
        finally:
            session.close()

        logger.info("=" * 60)
        logger.info("✅ Dynamic Pipeline System initialized successfully!")
        logger.info("")
        logger.info("Next steps:")
        logger.info("  1. Configure OCR engines via API or UI")
        logger.info("  2. Create pipeline steps via API or UI")
        logger.info("  3. (Optional) Add custom document classes via UI")

    except Exception as e:
        logger.error(f"❌ Initialization failed: {e}")
        raise


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    # Run initialization
    initialize_dynamic_pipeline()
