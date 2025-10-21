#!/usr/bin/env python3
"""
Debug the exact query the repository is running
"""
from sqlalchemy import create_engine, text

DATABASE_URL = "postgresql://postgres:KfcqZpqRnRCTyvVxHKkDHjssedAjXZSp@turntable.proxy.rlwy.net:58299/railway"

def debug_query():
    """Run the exact query from get_universal_steps()"""
    engine = create_engine(DATABASE_URL)

    print("\n" + "="*120)
    print("DEBUG: Exact query from get_universal_steps() repository method")
    print("="*120 + "\n")

    with engine.connect() as conn:
        # This is the EXACT query from pipeline_step_repository.py line 67-72
        query = text("""
            SELECT *
            FROM dynamic_pipeline_steps
            WHERE document_class_id IS NULL
              AND enabled = TRUE
            ORDER BY "order"
        """)

        result = conn.execute(query)
        steps = result.fetchall()

        print(f"Query returned: {len(steps)} rows\n")
        print("Results:")
        print("-" * 120)
        print(f"{'ID':<5} {'Order':<7} {'Enabled':<9} {'DocClass':<12} {'PostBranch':<12} {'Name':<40}")
        print("-" * 120)

        for step in steps:
            print(f"{step[0]:<5} {step[2]:<7} {str(step[3]):<9} {'NULL':<12} {str(step[16]):<12} {step[1]:<40}")

        print("-" * 120)

        # Now filter for pre-branching (like the code does)
        pre_branching = [s for s in steps if not s[16]]  # post_branching is column 16
        print(f"\nAfter filtering for post_branching = FALSE: {len(pre_branching)} rows")

        if pre_branching:
            print("\nPre-branching steps:")
            for step in pre_branching:
                print(f"   Order {step[2]}: {step[1]} (post_branching={step[16]})")
        else:
            print("\n❌ NO PRE-BRANCHING STEPS after filtering!")
            print("\nAll steps with their post_branching values:")
            for step in steps:
                print(f"   Order {step[2]}: {step[1]} (post_branching={step[16]})")

if __name__ == "__main__":
    debug_query()
