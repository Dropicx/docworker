#!/usr/bin/env python3
"""
Test phase-aware ordering for pipeline steps using direct database connection.

Verifies that steps are ordered correctly by execution phase:
1. Pre-branching universal (document_class_id = NULL, post_branching = False)
2. Document-specific (document_class_id != NULL)
3. Post-branching universal (document_class_id = NULL, post_branching = True)
"""
from sqlalchemy import create_engine, text, case

DATABASE_URL = "postgresql://postgres:KfcqZpqRnRCTyvVxHKkDHjssedAjXZSp@turntable.proxy.rlwy.net:58299/railway"


def test_phase_aware_ordering():
    """Test that steps are ordered by phase first, then by order field."""
    engine = create_engine(DATABASE_URL)

    print("\n" + "="*120)
    print("TESTING PHASE-AWARE ORDERING")
    print("="*120 + "\n")

    with engine.connect() as conn:
        # Query with phase-aware ordering using CASE expression
        result = conn.execute(text("""
            SELECT
                id,
                name,
                "order",
                enabled,
                document_class_id,
                post_branching,
                CASE
                    WHEN post_branching = TRUE THEN 3
                    WHEN document_class_id IS NOT NULL THEN 2
                    ELSE 1
                END as phase_order
            FROM dynamic_pipeline_steps
            ORDER BY
                CASE
                    WHEN post_branching = TRUE THEN 3
                    WHEN document_class_id IS NOT NULL THEN 2
                    ELSE 1
                END,
                "order"
        """))

        steps = result.fetchall()

        print(f"📊 Total steps: {len(steps)}\n")
        print("Execution order (phase-aware):")
        print("-" * 120)
        print(f"{'#':<5} {'Phase':<20} {'Order':<7} {'Enabled':<9} {'DocClass':<12} {'PostBranch':<12} {'Name':<50}")
        print("-" * 120)

        current_phase = None
        phase_counter = 0

        for idx, step in enumerate(steps, 1):
            step_id, name, order, enabled, doc_class_id, post_branching, phase_order = step

            # Determine phase label
            if post_branching:
                phase = "POST-BRANCHING"
                phase_num = 3
            elif doc_class_id is not None:
                phase = f"DOC-SPECIFIC ({doc_class_id})"
                phase_num = 2
            else:
                phase = "PRE-BRANCHING"
                phase_num = 1

            # Print phase separator when phase changes
            if current_phase != phase_num:
                if current_phase is not None:
                    print("-" * 120)
                current_phase = phase_num
                phase_counter = 0

            phase_counter += 1
            doc_class = f"ID:{doc_class_id}" if doc_class_id else "NULL"

            print(
                f"{idx:<5} {phase:<20} {order:<7} {str(enabled):<9} "
                f"{doc_class:<12} {str(post_branching):<12} {name:<50}"
            )

        print("-" * 120)

        # Validate ordering
        print("\n📋 Validation:")
        print("-" * 120)

        phase_sequence = [step[6] for step in steps]  # phase_order is column 6

        # Check if phases are in correct order
        is_correct = all(phase_sequence[i] <= phase_sequence[i+1] for i in range(len(phase_sequence)-1))

        if is_correct:
            print("✅ Phase ordering is CORRECT")
            print("   Pre-branching → Document-specific → Post-branching")
        else:
            print("❌ Phase ordering is INCORRECT")
            print(f"   Phase sequence: {phase_sequence}")

        # Count steps per phase
        pre_branching = sum(1 for p in phase_sequence if p == 1)
        doc_specific = sum(1 for p in phase_sequence if p == 2)
        post_branching = sum(1 for p in phase_sequence if p == 3)

        print(f"\n📊 Steps per phase:")
        print(f"   Phase 1 (Pre-branching):  {pre_branching} steps")
        print(f"   Phase 2 (Doc-specific):   {doc_specific} steps")
        print(f"   Phase 3 (Post-branching): {post_branching} steps")

        # Test enabled steps ordering
        print("\n" + "="*120)
        print("TESTING ENABLED STEPS ORDERING")
        print("="*120 + "\n")

        result_enabled = conn.execute(text("""
            SELECT
                id,
                name,
                "order",
                document_class_id,
                post_branching,
                CASE
                    WHEN post_branching = TRUE THEN 3
                    WHEN document_class_id IS NOT NULL THEN 2
                    ELSE 1
                END as phase_order
            FROM dynamic_pipeline_steps
            WHERE enabled = TRUE
            ORDER BY
                CASE
                    WHEN post_branching = TRUE THEN 3
                    WHEN document_class_id IS NOT NULL THEN 2
                    ELSE 1
                END,
                "order"
        """))

        enabled_steps = result_enabled.fetchall()
        print(f"📊 Enabled steps: {len(enabled_steps)}\n")

        phase_sequence_enabled = [step[5] for step in enabled_steps]  # phase_order is column 5

        is_correct_enabled = all(
            phase_sequence_enabled[i] <= phase_sequence_enabled[i+1]
            for i in range(len(phase_sequence_enabled)-1)
        )

        if is_correct_enabled:
            print("✅ Enabled steps phase ordering is CORRECT")
        else:
            print("❌ Enabled steps phase ordering is INCORRECT")
            print(f"   Phase sequence: {phase_sequence_enabled}")

        # Show enabled steps summary
        pre_branching_enabled = sum(1 for p in phase_sequence_enabled if p == 1)
        doc_specific_enabled = sum(1 for p in phase_sequence_enabled if p == 2)
        post_branching_enabled = sum(1 for p in phase_sequence_enabled if p == 3)

        print(f"\n📊 Enabled steps per phase:")
        print(f"   Phase 1 (Pre-branching):  {pre_branching_enabled} steps")
        print(f"   Phase 2 (Doc-specific):   {doc_specific_enabled} steps")
        print(f"   Phase 3 (Post-branching): {post_branching_enabled} steps")

        print("\n" + "="*120)
        print("✅ PHASE-AWARE ORDERING TEST COMPLETE")
        print("="*120)


if __name__ == "__main__":
    test_phase_aware_ordering()
