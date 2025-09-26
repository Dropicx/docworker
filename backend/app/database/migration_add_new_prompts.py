"""
Database migration script to add new prompt fields
"""

import logging
from sqlalchemy import text, Column, Text
from sqlalchemy.exc import OperationalError
from app.database.connection import get_engine

logger = logging.getLogger(__name__)

def migrate_add_new_prompt_fields():
    """
    Add medical_validation_prompt and formatting_prompt fields to existing database
    """
    try:
        engine = get_engine()

        with engine.connect() as conn:
            # Check if the new fields already exist
            try:
                result = conn.execute(text("""
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name = 'document_prompts'
                    AND column_name IN ('medical_validation_prompt', 'formatting_prompt')
                """))
                existing_columns = [row[0] for row in result]

                if 'medical_validation_prompt' in existing_columns and 'formatting_prompt' in existing_columns:
                    logger.info("✅ New prompt fields already exist, no migration needed")
                    return True

            except Exception as e:
                logger.warning(f"Could not check existing columns (might be normal): {e}")

            logger.info("🔄 Starting database migration to add new prompt fields...")

            # Add medical_validation_prompt column if it doesn't exist
            if 'medical_validation_prompt' not in existing_columns:
                try:
                    conn.execute(text("""
                        ALTER TABLE document_prompts
                        ADD COLUMN medical_validation_prompt TEXT
                    """))
                    logger.info("✅ Added medical_validation_prompt column")
                except OperationalError as e:
                    if "already exists" in str(e).lower():
                        logger.info("✅ medical_validation_prompt column already exists")
                    else:
                        raise e

            # Add formatting_prompt column if it doesn't exist
            if 'formatting_prompt' not in existing_columns:
                try:
                    conn.execute(text("""
                        ALTER TABLE document_prompts
                        ADD COLUMN formatting_prompt TEXT
                    """))
                    logger.info("✅ Added formatting_prompt column")
                except OperationalError as e:
                    if "already exists" in str(e).lower():
                        logger.info("✅ formatting_prompt column already exists")
                    else:
                        raise e

            # Update existing records with default values
            default_medical_validation_prompt = """Analysiere diesen Text und bestimme, ob er medizinischen Inhalt enthält.

KRITERIEN FÜR MEDIZINISCHEN INHALT:
- Diagnosen oder Symptome
- Medizinische Fachbegriffe
- Behandlungen oder Therapien
- Medikamente oder Dosierungen
- Laborwerte oder Messwerte
- Medizinische Abkürzungen
- Anatomische Begriffe

Antworte NUR mit: MEDIZINISCH oder NICHT_MEDIZINISCH"""

            default_formatting_prompt = """Formatiere diesen medizinischen Text für optimale Lesbarkeit.

FORMATIERUNG:
- Verwende klare Überschriften mit Emojis
- Erstelle Bullet Points für Listen (→)
- Hebe wichtige Informationen hervor
- Strukturiere den Text logisch
- Füge Leerzeilen zwischen Abschnitten ein
- Verwende einheitliche Formatierung

BEHALTE:
- Alle medizinischen Informationen
- Die Verständlichkeit
- Alle wichtigen Details

Antworte mit dem formatierten Text."""

            # Update existing records where the new fields are NULL
            conn.execute(text("""
                UPDATE document_prompts
                SET medical_validation_prompt = :medical_validation_prompt
                WHERE medical_validation_prompt IS NULL
            """), {'medical_validation_prompt': default_medical_validation_prompt})

            conn.execute(text("""
                UPDATE document_prompts
                SET formatting_prompt = :formatting_prompt
                WHERE formatting_prompt IS NULL
            """), {'formatting_prompt': default_formatting_prompt})

            logger.info("✅ Updated existing records with default prompt values")

            # Make the new columns NOT NULL after setting default values
            try:
                conn.execute(text("""
                    ALTER TABLE document_prompts
                    ALTER COLUMN medical_validation_prompt SET NOT NULL
                """))
                logger.info("✅ Set medical_validation_prompt as NOT NULL")
            except OperationalError as e:
                logger.warning(f"Could not set medical_validation_prompt as NOT NULL: {e}")

            try:
                conn.execute(text("""
                    ALTER TABLE document_prompts
                    ALTER COLUMN formatting_prompt SET NOT NULL
                """))
                logger.info("✅ Set formatting_prompt as NOT NULL")
            except OperationalError as e:
                logger.warning(f"Could not set formatting_prompt as NOT NULL: {e}")

            # Commit all changes
            conn.commit()

            # Verify the migration
            result = conn.execute(text("SELECT COUNT(*) FROM document_prompts WHERE medical_validation_prompt IS NOT NULL AND formatting_prompt IS NOT NULL"))
            updated_count = result.scalar()

            logger.info(f"✅ Migration completed successfully! Updated {updated_count} records")
            return True

    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        return False

def rollback_migration():
    """
    Rollback the migration by removing the new columns
    WARNING: This will permanently delete data!
    """
    try:
        engine = get_engine()

        with engine.connect() as conn:
            logger.warning("⚠️  Starting rollback - this will permanently delete data!")

            # Drop the new columns
            try:
                conn.execute(text("ALTER TABLE document_prompts DROP COLUMN medical_validation_prompt"))
                logger.info("✅ Dropped medical_validation_prompt column")
            except OperationalError as e:
                if "does not exist" in str(e).lower():
                    logger.info("⏭️  medical_validation_prompt column already doesn't exist")
                else:
                    raise e

            try:
                conn.execute(text("ALTER TABLE document_prompts DROP COLUMN formatting_prompt"))
                logger.info("✅ Dropped formatting_prompt column")
            except OperationalError as e:
                if "does not exist" in str(e).lower():
                    logger.info("⏭️  formatting_prompt column already doesn't exist")
                else:
                    raise e

            conn.commit()
            logger.info("✅ Rollback completed successfully")
            return True

    except Exception as e:
        logger.error(f"❌ Rollback failed: {e}")
        return False

def check_migration_status():
    """
    Check the current status of the migration
    """
    try:
        engine = get_engine()

        with engine.connect() as conn:
            # Check if new columns exist
            result = conn.execute(text("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'document_prompts'
                AND column_name IN ('medical_validation_prompt', 'formatting_prompt')
                ORDER BY column_name
            """))

            columns = list(result)

            if not columns:
                return {
                    "status": "not_migrated",
                    "message": "New prompt fields do not exist",
                    "columns": []
                }

            # Check if there are any records with the new fields
            result = conn.execute(text("""
                SELECT
                    COUNT(*) as total_records,
                    COUNT(medical_validation_prompt) as records_with_medical_validation,
                    COUNT(formatting_prompt) as records_with_formatting
                FROM document_prompts
            """))

            stats = result.fetchone()

            return {
                "status": "migrated" if len(columns) == 2 else "partially_migrated",
                "message": "Migration completed" if len(columns) == 2 else "Migration partially completed",
                "columns": [{"name": col[0], "type": col[1], "nullable": col[2]} for col in columns],
                "record_stats": {
                    "total_records": stats[0],
                    "records_with_medical_validation": stats[1],
                    "records_with_formatting": stats[2]
                }
            }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Error checking migration status: {e}",
            "columns": []
        }

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        action = sys.argv[1].lower()

        if action == "migrate":
            print("🔄 Running migration to add new prompt fields...")
            success = migrate_add_new_prompt_fields()
            print("✅ Migration completed successfully!" if success else "❌ Migration failed!")
            sys.exit(0 if success else 1)

        elif action == "rollback":
            confirm = input("⚠️  This will permanently delete the new prompt fields. Are you sure? (yes/no): ")
            if confirm.lower() == "yes":
                print("🔄 Running rollback...")
                success = rollback_migration()
                print("✅ Rollback completed!" if success else "❌ Rollback failed!")
                sys.exit(0 if success else 1)
            else:
                print("❌ Rollback cancelled")
                sys.exit(1)

        elif action == "status":
            print("🔍 Checking migration status...")
            status = check_migration_status()
            print(f"Status: {status['status']}")
            print(f"Message: {status['message']}")
            if status['columns']:
                print("Columns:")
                for col in status['columns']:
                    print(f"  - {col['name']}: {col['type']} (nullable: {col['nullable']})")
            if 'record_stats' in status:
                stats = status['record_stats']
                print(f"Records: {stats['total_records']} total, {stats['records_with_medical_validation']} with medical validation, {stats['records_with_formatting']} with formatting")
            sys.exit(0)
        else:
            print("Usage: python migration_add_new_prompts.py [migrate|rollback|status]")
            sys.exit(1)
    else:
        print("🔄 Running migration by default...")
        success = migrate_add_new_prompt_fields()
        print("✅ Migration completed successfully!" if success else "❌ Migration failed!")
        sys.exit(0 if success else 1)