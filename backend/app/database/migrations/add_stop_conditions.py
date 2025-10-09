"""
Add stop_conditions column to dynamic_pipeline_steps table.

This enables early pipeline termination based on step output.
Example: Stop processing if MEDICAL_VALIDATION returns "NICHT_MEDIZINISCH"
"""

from sqlalchemy import text
from app.database.connection import get_engine

def upgrade():
    """Add stop_conditions column"""
    engine = get_engine()

    with engine.connect() as conn:
        # Add stop_conditions column (JSON)
        conn.execute(text("""
            ALTER TABLE dynamic_pipeline_steps
            ADD COLUMN IF NOT EXISTS stop_conditions JSON DEFAULT NULL
        """))

        conn.commit()

        print("✅ Migration completed: Added stop_conditions column")
        return True

def downgrade():
    """Remove stop_conditions column"""
    engine = get_engine()

    with engine.connect() as conn:
        conn.execute(text("""
            ALTER TABLE dynamic_pipeline_steps
            DROP COLUMN IF EXISTS stop_conditions
        """))

        conn.commit()

        print("✅ Migration reverted: Removed stop_conditions column")

if __name__ == "__main__":
    print("🔄 Running migration: add_stop_conditions")
    upgrade()
