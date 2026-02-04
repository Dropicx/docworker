#!/usr/bin/env python3
"""Simple diagnostic script to check production pipeline steps."""

import os

os.environ["DATABASE_URL"] = (
    "postgresql://postgres:KfcqZpqRnRCTyvVxHKkDHjssedAjXZSp@turntable.proxy.rlwy.net:58299/railway"
)
os.environ["OVH_AI_ENDPOINTS_ACCESS_TOKEN"] = "dummy"  # Just for import to work

import sys

sys.path.insert(
    0, "/media/catchmelit/5a972e8f-2616-4a45-b03c-2d2fd85f5030/Projects/doctranslator/backend"
)

from sqlalchemy import create_engine, text

DATABASE_URL = (
    "postgresql://postgres:KfcqZpqRnRCTyvVxHKkDHjssedAjXZSp@turntable.proxy.rlwy.net:58299/railway"
)
engine = create_engine(DATABASE_URL)

print("\n" + "=" * 120)
print("PRODUCTION DATABASE - ALL ENABLED PIPELINE STEPS")
print("=" * 120)

with engine.connect() as conn:
    result = conn.execute(
        text("""
        SELECT
            id,
            name,
            "order",
            enabled,
            document_class_id,
            post_branching,
            is_branching_step
        FROM dynamic_pipeline_steps
        WHERE enabled = TRUE
        ORDER BY
            CASE
                WHEN post_branching = TRUE THEN 3
                WHEN document_class_id IS NOT NULL THEN 2
                ELSE 1
            END,
            "order"
    """)
    )

    steps = result.fetchall()
    print(f"\n📊 Total enabled steps: {len(steps)}\n")
    print(
        f'{"Phase":<8} {"ID":<5} {"Name":<45} {"Order":<7} {"DocClassID":<12} {"PostBranch":<12} {"Branching":<10}'
    )
    print("-" * 120)

    for step in steps:
        step_id, name, order, enabled, doc_class_id, post_branching, is_branching = step

        # Determine phase
        if post_branching:
            phase = "PHASE 3"
        elif doc_class_id is not None:
            phase = "PHASE 2"
        else:
            phase = "PHASE 1"

        doc_class = str(doc_class_id) if doc_class_id is not None else "NULL"

        print(
            f"{phase:<8} {step_id:<5} {name:<45} {order:<7} {doc_class:<12} {str(post_branching):<12} {str(is_branching):<10}"
        )

print("\n" + "=" * 120)
print("PHASE BREAKDOWN")
print("=" * 120)

with engine.connect() as conn:
    # Phase 1: Pre-branching universal
    result = conn.execute(
        text("""
        SELECT COUNT(*), ARRAY_AGG(name ORDER BY "order")
        FROM dynamic_pipeline_steps
        WHERE document_class_id IS NULL
        AND post_branching = FALSE
        AND enabled = TRUE
    """)
    )
    phase1_count, phase1_names = result.fetchone()

    print(f"\n🔵 PHASE 1 (Pre-branching Universal): {phase1_count} steps")
    print(f"   Filter: document_class_id IS NULL AND post_branching = FALSE AND enabled = TRUE")
    if phase1_count > 0:
        for name in phase1_names or []:
            print(f"   ✅ {name}")
    else:
        print(f"   ❌ NO STEPS CONFIGURED!")

    # Phase 2: Document-specific
    result = conn.execute(
        text("""
        SELECT COUNT(*), ARRAY_AGG(DISTINCT document_class_id)
        FROM dynamic_pipeline_steps
        WHERE document_class_id IS NOT NULL
        AND enabled = TRUE
    """)
    )
    phase2_count, doc_class_ids = result.fetchone()

    print(f"\n🟢 PHASE 2 (Document-Specific): {phase2_count} steps")
    print(f"   Filter: document_class_id IS NOT NULL AND enabled = TRUE")
    if phase2_count > 0:
        print(f"   Document Class IDs: {doc_class_ids}")
    else:
        print(f"   ❌ NO STEPS CONFIGURED!")

    # Phase 3: Post-branching universal
    result = conn.execute(
        text("""
        SELECT COUNT(*), ARRAY_AGG(name ORDER BY "order")
        FROM dynamic_pipeline_steps
        WHERE document_class_id IS NULL
        AND post_branching = TRUE
        AND enabled = TRUE
    """)
    )
    phase3_count, phase3_names = result.fetchone()

    print(f"\n🟣 PHASE 3 (Post-branching Universal): {phase3_count} steps")
    print(f"   Filter: document_class_id IS NULL AND post_branching = TRUE AND enabled = TRUE")
    if phase3_count > 0:
        for name in phase3_names or []:
            print(f"   ✅ {name}")
    else:
        print(f"   ❌ NO STEPS CONFIGURED!")

print("\n" + "=" * 120)
print("ROOT CAUSE ANALYSIS")
print("=" * 120)

with engine.connect() as conn:
    # Count steps with NULL document_class_id
    result = conn.execute(
        text("""
        SELECT COUNT(*)
        FROM dynamic_pipeline_steps
        WHERE document_class_id IS NULL
        AND enabled = TRUE
    """)
    )
    null_doc_class_count = result.fetchone()[0]

    print(f"\n🔍 Steps with document_class_id = NULL: {null_doc_class_count}")

    if null_doc_class_count == 0:
        print("\n❌ PROBLEM IDENTIFIED:")
        print("   ALL enabled steps have document_class_id assigned to a specific document class!")
        print("   This is why get_universal_steps() returns 0 results.")
        print("")
        print("💡 EXPECTED CONFIGURATION:")
        print("   - Phase 1 steps (pre-branching) should have document_class_id = NULL")
        print("   - Phase 2 steps (doc-specific) should have document_class_id = 1, 2, 3...")
        print("   - Phase 3 steps (post-branching) should have document_class_id = NULL")
        print("")
        print("🔧 FIX REQUIRED:")
        print("   Update universal steps to set document_class_id = NULL")
        print("   Set post_branching = TRUE for Phase 3 steps")
        print("   Set post_branching = FALSE for Phase 1 steps")

print("\n" + "=" * 120)
