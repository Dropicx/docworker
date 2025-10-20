#!/usr/bin/env python3
"""
Test phase-aware ordering for pipeline steps.

Verifies that steps are ordered correctly by execution phase:
1. Pre-branching universal (document_class_id = NULL, post_branching = False)
2. Document-specific (document_class_id != NULL)
3. Post-branching universal (document_class_id = NULL, post_branching = True)
"""
import sys
sys.path.insert(0, '/media/catchmelit/5a972e8f-2616-4a45-b03c-2d2fd85f5030/Projects/doctranslator/backend')

from app.database.connection import get_db_session
from app.repositories.pipeline_step_repository import PipelineStepRepository


def test_phase_aware_ordering():
    """Test that steps are ordered by phase first, then by order field."""
    db = next(get_db_session())
    repo = PipelineStepRepository(db)

    print("\n" + "="*120)
    print("TESTING PHASE-AWARE ORDERING")
    print("="*120 + "\n")

    # Get all steps with new phase-aware ordering
    all_steps = repo.get_all_ordered()

    print(f"📊 Total steps: {len(all_steps)}\n")
    print("Execution order (phase-aware):")
    print("-" * 120)
    print(f"{'#':<5} {'Phase':<20} {'Order':<7} {'Enabled':<9} {'DocClass':<12} {'PostBranch':<12} {'Name':<50}")
    print("-" * 120)

    current_phase = None
    phase_counter = 0

    for idx, step in enumerate(all_steps, 1):
        # Determine phase
        if step.post_branching:
            phase = "POST-BRANCHING"
            phase_num = 3
        elif step.document_class_id is not None:
            phase = f"DOC-SPECIFIC ({step.document_class_id})"
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
        doc_class = f"ID:{step.document_class_id}" if step.document_class_id else "NULL"

        print(
            f"{idx:<5} {phase:<20} {step.order:<7} {str(step.enabled):<9} "
            f"{doc_class:<12} {str(step.post_branching):<12} {step.name:<50}"
        )

    print("-" * 120)

    # Validate ordering
    print("\n📋 Validation:")
    print("-" * 120)

    phase_order = []
    for step in all_steps:
        if step.post_branching:
            phase_order.append(3)
        elif step.document_class_id is not None:
            phase_order.append(2)
        else:
            phase_order.append(1)

    # Check if phases are in correct order
    is_correct = all(phase_order[i] <= phase_order[i+1] for i in range(len(phase_order)-1))

    if is_correct:
        print("✅ Phase ordering is CORRECT")
        print("   Pre-branching → Document-specific → Post-branching")
    else:
        print("❌ Phase ordering is INCORRECT")
        print(f"   Phase sequence: {phase_order}")

    # Count steps per phase
    pre_branching = sum(1 for p in phase_order if p == 1)
    doc_specific = sum(1 for p in phase_order if p == 2)
    post_branching = sum(1 for p in phase_order if p == 3)

    print(f"\n📊 Steps per phase:")
    print(f"   Phase 1 (Pre-branching):  {pre_branching} steps")
    print(f"   Phase 2 (Doc-specific):   {doc_specific} steps")
    print(f"   Phase 3 (Post-branching): {post_branching} steps")

    # Test enabled steps ordering
    print("\n" + "="*120)
    print("TESTING ENABLED STEPS ORDERING")
    print("="*120 + "\n")

    enabled_steps = repo.get_enabled_steps()
    print(f"📊 Enabled steps: {len(enabled_steps)}\n")

    phase_order_enabled = []
    for step in enabled_steps:
        if step.post_branching:
            phase_order_enabled.append(3)
        elif step.document_class_id is not None:
            phase_order_enabled.append(2)
        else:
            phase_order_enabled.append(1)

    is_correct_enabled = all(
        phase_order_enabled[i] <= phase_order_enabled[i+1]
        for i in range(len(phase_order_enabled)-1)
    )

    if is_correct_enabled:
        print("✅ Enabled steps phase ordering is CORRECT")
    else:
        print("❌ Enabled steps phase ordering is INCORRECT")
        print(f"   Phase sequence: {phase_order_enabled}")

    db.close()


if __name__ == "__main__":
    test_phase_aware_ordering()
