"""
Migration: Add feature flags and dynamic configuration tables

This migration adds support for:
- Feature flags (runtime toggles)
- Dynamic configuration (database-backed settings)
"""

import logging
from sqlalchemy import text
from app.database.connection import get_engine

logger = logging.getLogger(__name__)


def upgrade():
    """Add feature flags and configuration tables"""
    engine = get_engine()

    with engine.connect() as conn:
        logger.info("Creating feature_flags table...")

        # Create feature_flags table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS feature_flags (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) UNIQUE NOT NULL,
                enabled BOOLEAN DEFAULT FALSE,
                description TEXT,
                rollout_percentage INTEGER DEFAULT 0 CHECK (rollout_percentage >= 0 AND rollout_percentage <= 100),
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            );
        """))

        # Create index on name for fast lookups
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_feature_flags_name ON feature_flags(name);
        """))

        logger.info("Creating configuration table...")

        # Create configuration table for dynamic settings
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS configuration (
                id SERIAL PRIMARY KEY,
                key VARCHAR(255) UNIQUE NOT NULL,
                value JSONB NOT NULL,
                description TEXT,
                is_secret BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW(),
                updated_by VARCHAR(100)
            );
        """))

        # Create index on key for fast lookups
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_configuration_key ON configuration(key);
        """))

        logger.info("Seeding default feature flags...")

        # Seed default feature flags (matching Feature enum in app.services.feature_flags)
        conn.execute(text("""
            INSERT INTO feature_flags (name, enabled, description, rollout_percentage)
            VALUES
                -- OCR and Text Extraction
                ('vision_llm_fallback_enabled', TRUE, 'Allow fallback to Vision LLM when local OCR fails', 100),
                ('multi_file_processing_enabled', TRUE, 'Enable multi-file document processing', 100),

                -- Privacy and Security
                ('advanced_privacy_filter_enabled', TRUE, 'Use advanced privacy filtering', 100),
                ('pii_removal_enabled', TRUE, 'Enable PII removal in preprocessing', 100),

                -- Performance and Monitoring
                ('cost_tracking_enabled', TRUE, 'Enable AI cost tracking and logging', 100),
                ('ai_logging_enabled', TRUE, 'Enable detailed AI interaction logging', 100),
                ('parallel_step_execution_enabled', FALSE, 'Execute independent pipeline steps in parallel', 0),

                -- Pipeline Features
                ('dynamic_branching_enabled', TRUE, 'Enable dynamic pipeline branching based on document type', 100),
                ('stop_conditions_enabled', TRUE, 'Enable pipeline stop conditions', 100),
                ('retry_on_failure_enabled', TRUE, 'Retry failed pipeline steps automatically', 100),

                -- Experimental Features
                ('hybrid_ocr_strategy_enabled', FALSE, 'Use hybrid OCR strategy (experimental)', 0),
                ('auto_quality_detection_enabled', FALSE, 'Automatic document quality detection (experimental)', 0),

                -- Legacy flags (backward compatibility)
                ('enable_ocr', TRUE, 'Enable OCR text extraction from images', 100),
                ('enable_privacy_filter', TRUE, 'Enable PII privacy filtering', 100),
                ('enable_multi_file', TRUE, 'Enable multi-file batch processing', 100)
            ON CONFLICT (name) DO NOTHING;
        """))

        conn.commit()
        logger.info("✅ Feature flags migration completed successfully")


def downgrade():
    """Remove feature flags and configuration tables"""
    engine = get_engine()

    with engine.connect() as conn:
        logger.info("Dropping feature_flags table...")
        conn.execute(text("DROP TABLE IF EXISTS feature_flags CASCADE;"))

        logger.info("Dropping configuration table...")
        conn.execute(text("DROP TABLE IF EXISTS configuration CASCADE;"))

        conn.commit()
        logger.info("✅ Feature flags migration rollback completed")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger.info("Running feature flags migration...")
    upgrade()
