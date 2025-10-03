"""
Simple migration to add branching columns
Runs each ALTER TABLE separately with commits
"""
import sys
from sqlalchemy import text
from app.database.connection import engine

def migrate():
    print("🔧 Adding branching columns to dynamic_pipeline_steps...")

    with engine.connect() as conn:
        # Add columns one at a time, each in its own transaction

        # 1. document_class_id
        try:
            conn.execute(text("ALTER TABLE dynamic_pipeline_steps ADD COLUMN document_class_id INTEGER;"))
            conn.commit()
            print("✅ Added document_class_id")
        except Exception as e:
            if "already exists" in str(e):
                print("✓ document_class_id already exists")
            else:
                print(f"❌ Error adding document_class_id: {e}")
                return False

        # 2. Foreign key constraint
        try:
            conn.execute(text("ALTER TABLE dynamic_pipeline_steps ADD CONSTRAINT fk_document_class_id FOREIGN KEY (document_class_id) REFERENCES document_classes(id) ON DELETE CASCADE;"))
            conn.commit()
            print("✅ Added foreign key constraint")
        except Exception as e:
            if "already exists" in str(e):
                print("✓ Foreign key already exists")
            else:
                print(f"⚠️  Foreign key warning: {e}")

        # 3. Index
        try:
            conn.execute(text("CREATE INDEX ix_dynamic_pipeline_steps_document_class_id ON dynamic_pipeline_steps(document_class_id);"))
            conn.commit()
            print("✅ Added index")
        except Exception as e:
            if "already exists" in str(e):
                print("✓ Index already exists")
            else:
                print(f"⚠️  Index warning: {e}")

        # 4. is_branching_step
        try:
            conn.execute(text("ALTER TABLE dynamic_pipeline_steps ADD COLUMN is_branching_step BOOLEAN NOT NULL DEFAULT FALSE;"))
            conn.commit()
            print("✅ Added is_branching_step")
        except Exception as e:
            if "already exists" in str(e):
                print("✓ is_branching_step already exists")
            else:
                print(f"❌ Error adding is_branching_step: {e}")
                return False

        # 5. branching_field
        try:
            conn.execute(text("ALTER TABLE dynamic_pipeline_steps ADD COLUMN branching_field VARCHAR(100);"))
            conn.commit()
            print("✅ Added branching_field")
        except Exception as e:
            if "already exists" in str(e):
                print("✓ branching_field already exists")
            else:
                print(f"❌ Error adding branching_field: {e}")
                return False

    print("\n✅ Migration completed!")
    return True

if __name__ == "__main__":
    if migrate():
        sys.exit(0)
    else:
        sys.exit(1)
