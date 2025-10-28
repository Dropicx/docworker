#!/usr/bin/env python3
"""
Check remote Railway database configuration
"""
import sys
from sqlalchemy import create_engine, text

# Railway dev database
DATABASE_URL = "postgresql://postgres:KfcqZpqRnRCTyvVxHKkDHjssedAjXZSp@turntable.proxy.rlwy.net:58299/railway"

def check_remote_database():
    """Check remote database pipeline steps"""
    try:
        engine = create_engine(DATABASE_URL)

        print("\n" + "="*120)
        print("RAILWAY DEV DATABASE - PIPELINE STEPS CONFIGURATION")
        print("="*120 + "\n")

        with engine.connect() as conn:
            # Query all pipeline steps
            result = conn.execute(text("""
                SELECT
                    id,
                    "order",
                    enabled,
                    document_class_id,
                    post_branching,
                    is_branching_step,
                    branching_field,
                    name
                FROM dynamic_pipeline_steps
                ORDER BY "order"
            """))

            steps = result.fetchall()

            if not steps:
                print("❌ No pipeline steps found in database!")
                return

            print(f"📊 Total steps in database: {len(steps)}\n")

            print("Step Details:")
            print("-" * 120)
            print(f"{'ID':<5} {'Order':<7} {'Enabled':<9} {'DocClass':<12} {'PostBranch':<12} {'Branching':<11} {'Field':<20} {'Name':<40}")
            print("-" * 120)

            for step in steps:
                step_id, order, enabled, doc_class_id, post_branching, is_branching, branching_field, name = step

                doc_class = f"ID:{doc_class_id}" if doc_class_id else "NULL"
                branching = "YES" if is_branching else "NO"
                field = branching_field or "-"

                print(f"{step_id:<5} {order:<7} {str(enabled):<9} {doc_class:<12} {str(post_branching):<12} {branching:<11} {field:<20} {name:<40}")

            print("-" * 120)

            # Count by category
            enabled_count = sum(1 for s in steps if s[2])  # enabled column
            universal_count = sum(1 for s in steps if s[3] is None)  # document_class_id column
            pre_branching_universal = sum(1 for s in steps if s[3] is None and not s[4] and s[2])  # NULL, not post_branching, enabled
            post_branching_count = sum(1 for s in steps if s[4])  # post_branching column

            print(f"\n📋 Summary:")
            print(f"   Total steps: {len(steps)}")
            print(f"   Enabled steps: {enabled_count}")
            print(f"   Universal steps (doc_class_id IS NULL): {universal_count}")
            print(f"   Pre-branching universal (enabled, NULL doc_class, post_branching=FALSE): {pre_branching_universal}")
            print(f"   Post-branching steps: {post_branching_count}")

            if pre_branching_universal == 0:
                print(f"\n⚠️  ISSUE FOUND:")
                print(f"   No pre-branching universal steps found!")
                print(f"   This is why you see: '⚠️ No universal pipeline steps found, loading all steps as fallback'")
                print(f"   The fallback loads all {enabled_count} enabled steps instead.")
                print(f"\n💡 Expected behavior:")
                print(f"   Steps should have: document_class_id = NULL AND post_branching = FALSE")
            else:
                print(f"\n✅ Configuration looks correct!")
                print(f"   {pre_branching_universal} pre-branching universal steps configured properly")

            # Show which steps match the expected criteria
            print(f"\n🔍 Steps matching 'pre-branching universal' criteria:")
            print(f"   (document_class_id IS NULL AND post_branching = FALSE AND enabled = TRUE)")
            print("-" * 120)

            matching = [s for s in steps if s[3] is None and not s[4] and s[2]]
            if matching:
                for step in matching:
                    print(f"   ✓ Order {step[1]}: {step[7]}")
            else:
                print(f"   ❌ NONE - This is the problem!")
                print(f"\n   Steps with document_class_id IS NULL:")
                null_class = [s for s in steps if s[3] is None]
                if null_class:
                    for step in null_class:
                        post_br = "post_branching=TRUE" if step[4] else "post_branching=FALSE"
                        enab = "enabled=TRUE" if step[2] else "enabled=FALSE"
                        print(f"      Order {step[1]}: {step[7]} ({post_br}, {enab})")
                else:
                    print(f"      NONE - All steps have document_class_id set!")

    except Exception as e:
        print(f"❌ Error connecting to database: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_remote_database()
