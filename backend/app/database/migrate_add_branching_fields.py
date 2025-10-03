"""
Migration Script: Add Pipeline Branching Fields

Adds the following columns to dynamic_pipeline_steps table:
- document_class_id (Integer, nullable, Foreign Key to document_classes)
- is_branching_step (Boolean, default False)
- branching_field (String, nullable)

Run this script ONCE to upgrade existing databases.
"""

import logging
from sqlalchemy import text, inspect, Column, Integer, Boolean, String, ForeignKey
from app.database.connection import engine, get_session

logger = logging.getLogger(__name__)


def check_column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table"""
    inspector = inspect(engine)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns


def add_branching_columns():
    """Add branching columns to dynamic_pipeline_steps table"""
    logger.info("🔧 Starting migration: Add pipeline branching fields")
    logger.info("=" * 60)

    table_name = 'dynamic_pipeline_steps'

    # Check if table exists
    inspector = inspect(engine)
    if table_name not in inspector.get_table_names():
        logger.error(f"❌ Table '{table_name}' does not exist!")
        logger.error("   Please run init_dynamic_pipeline.py first to create tables.")
        return False

    with engine.connect() as conn:
        # Start transaction
        trans = conn.begin()

        try:
            # 1. Add document_class_id column (nullable, foreign key)
            if not check_column_exists(table_name, 'document_class_id'):
                logger.info(f"   Adding column 'document_class_id'...")
                conn.execute(text(f'''
                    ALTER TABLE {table_name}
                    ADD COLUMN document_class_id INTEGER;
                '''))

                # Add foreign key constraint
                logger.info(f"   Adding foreign key constraint...")
                conn.execute(text(f'''
                    ALTER TABLE {table_name}
                    ADD CONSTRAINT fk_document_class_id
                    FOREIGN KEY (document_class_id)
                    REFERENCES document_classes(id)
                    ON DELETE CASCADE;
                '''))

                # Create index
                logger.info(f"   Creating index on 'document_class_id'...")
                conn.execute(text(f'''
                    CREATE INDEX ix_{table_name}_document_class_id
                    ON {table_name}(document_class_id);
                '''))

                logger.info(f"   ✅ Added 'document_class_id' column")
            else:
                logger.info(f"   ✓ Column 'document_class_id' already exists")

            # 2. Add is_branching_step column (boolean, default False, not null)
            if not check_column_exists(table_name, 'is_branching_step'):
                logger.info(f"   Adding column 'is_branching_step'...")
                conn.execute(text(f'''
                    ALTER TABLE {table_name}
                    ADD COLUMN is_branching_step BOOLEAN NOT NULL DEFAULT FALSE;
                '''))
                logger.info(f"   ✅ Added 'is_branching_step' column")
            else:
                logger.info(f"   ✓ Column 'is_branching_step' already exists")

            # 3. Add branching_field column (varchar, nullable)
            if not check_column_exists(table_name, 'branching_field'):
                logger.info(f"   Adding column 'branching_field'...")
                conn.execute(text(f'''
                    ALTER TABLE {table_name}
                    ADD COLUMN branching_field VARCHAR(100);
                '''))
                logger.info(f"   ✅ Added 'branching_field' column")
            else:
                logger.info(f"   ✓ Column 'branching_field' already exists")

            # Commit transaction
            trans.commit()
            logger.info("=" * 60)
            logger.info("✅ Migration completed successfully!")
            logger.info("")
            logger.info("New columns added to 'dynamic_pipeline_steps':")
            logger.info("  - document_class_id (nullable, FK to document_classes)")
            logger.info("  - is_branching_step (boolean, default: False)")
            logger.info("  - branching_field (varchar, nullable)")
            logger.info("")
            logger.info("You can now:")
            logger.info("  1. Create document classes via the UI")
            logger.info("  2. Assign steps to specific document classes")
            logger.info("  3. Mark classification steps as branching points")

            return True

        except Exception as e:
            trans.rollback()
            logger.error(f"❌ Migration failed: {e}")
            logger.error("   Rolling back changes...")
            raise


def verify_migration():
    """Verify that all columns were added successfully"""
    logger.info("")
    logger.info("🔍 Verifying migration...")

    table_name = 'dynamic_pipeline_steps'
    required_columns = ['document_class_id', 'is_branching_step', 'branching_field']

    all_present = True
    for column in required_columns:
        exists = check_column_exists(table_name, column)
        status = "✅" if exists else "❌"
        logger.info(f"   {status} {column}: {'Present' if exists else 'Missing'}")
        if not exists:
            all_present = False

    if all_present:
        logger.info("✅ All columns verified successfully!")
    else:
        logger.error("❌ Some columns are missing!")

    return all_present


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    try:
        # Run migration
        success = add_branching_columns()

        if success:
            # Verify migration
            verify_migration()

    except Exception as e:
        logger.error(f"❌ Migration script failed: {e}")
        exit(1)
