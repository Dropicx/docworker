#!/usr/bin/env python3
"""
Test how PostgreSQL handles duplicate ORDER values in queries
"""
from sqlalchemy import create_engine, text

DATABASE_URL = "postgresql://postgres:KfcqZpqRnRCTyvVxHKkDHjssedAjXZSp@turntable.proxy.rlwy.net:58299/railway"

def test_order_behavior():
    """Test ORDER BY behavior with duplicate values"""
    engine = create_engine(DATABASE_URL)

    print("\n" + "="*120)
    print("TESTING ORDER BY BEHAVIOR WITH DUPLICATE VALUES")
    print("="*120 + "\n")

    with engine.connect() as conn:
        # Test 1: Query universal steps multiple times to see if order changes
        print("Test 1: Running the same query 5 times to check consistency")
        print("-" * 120)

        for run in range(1, 6):
            result = conn.execute(text("""
                SELECT id, name, "order", post_branching
                FROM dynamic_pipeline_steps
                WHERE document_class_id IS NULL
                  AND enabled = TRUE
                ORDER BY "order"
            """))

            rows = result.fetchall()
            print(f"\nRun {run}: {len(rows)} rows returned")
            for row in rows:
                print(f"  ID {row[0]:<3} | Order {row[2]:<3} | post_branching={row[3]:<6} | {row[1]}")

        print("\n" + "="*120)
        print("Test 2: Check if row order changes between runs (deterministic vs non-deterministic)")
        print("-" * 120)

        # Run query 3 times and collect IDs in order
        runs = []
        for run in range(3):
            result = conn.execute(text("""
                SELECT id
                FROM dynamic_pipeline_steps
                WHERE document_class_id IS NULL
                  AND enabled = TRUE
                ORDER BY "order"
            """))
            run_ids = [row[0] for row in result.fetchall()]
            runs.append(run_ids)
            print(f"Run {run + 1} ID order: {run_ids}")

        if runs[0] == runs[1] == runs[2]:
            print("\n✅ ORDER is DETERMINISTIC: Same order every time")
        else:
            print("\n⚠️  ORDER is NON-DETERMINISTIC: Order changes between runs!")

        print("\n" + "="*120)
        print("Test 3: Add secondary ordering by ID to make it deterministic")
        print("-" * 120)

        result = conn.execute(text("""
            SELECT id, name, "order", post_branching
            FROM dynamic_pipeline_steps
            WHERE document_class_id IS NULL
              AND enabled = TRUE
            ORDER BY "order", id
        """))

        rows = result.fetchall()
        print(f"\nWith ORDER BY \"order\", id: {len(rows)} rows")
        for row in rows:
            print(f"  ID {row[0]:<3} | Order {row[2]:<3} | post_branching={row[3]:<6} | {row[1]}")

        print("\n" + "="*120)
        print("Test 4: Filter for post_branching = FALSE (the actual code logic)")
        print("-" * 120)

        # This is what the code does
        result = conn.execute(text("""
            SELECT id, name, "order", post_branching
            FROM dynamic_pipeline_steps
            WHERE document_class_id IS NULL
              AND enabled = TRUE
            ORDER BY "order"
        """))

        all_rows = result.fetchall()
        # Filter in Python like the code does
        filtered_rows = [r for r in all_rows if r[3] == False]  # post_branching == False

        print(f"\nAll rows returned: {len(all_rows)}")
        for row in all_rows:
            print(f"  ID {row[0]:<3} | Order {row[2]:<3} | post_branching={row[3]:<6} | {row[1]}")

        print(f"\nAfter Python filter (post_branching == False): {len(filtered_rows)}")
        for row in filtered_rows:
            print(f"  ID {row[0]:<3} | Order {row[2]:<3} | post_branching={row[3]:<6} | {row[1]}")

        print("\n" + "="*120)
        print("Test 5: What if Language Translation (post_branching=TRUE) is returned BEFORE Medical Validation?")
        print("-" * 120)

        # Both have order=1, so PostgreSQL might return them in any order
        # If Language Translation (TRUE) comes first, it would be at index 0
        # Then filtering would remove it, potentially confusing the logic

        print("\nScenario: If ORDER BY returns steps in this order:")
        print("  1. Language Translation (order=1, post_branching=TRUE)")
        print("  2. Medical Content Validation (order=1, post_branching=FALSE)")
        print("  3. Document Classification (order=2, post_branching=FALSE)")
        print("\nAfter Python filter (post_branching==False):")
        print("  1. Medical Content Validation")
        print("  2. Document Classification")
        print("\n✅ Result: Still returns 2 steps (correct)")

        print("\n💡 CONCLUSION:")
        print("   The duplicate order=1 values DON'T explain the '0 steps' issue.")
        print("   The filter happens AFTER the query, so we should still get 2 steps.")
        print("   The issue must be somewhere else in the code flow.")

if __name__ == "__main__":
    test_order_behavior()
