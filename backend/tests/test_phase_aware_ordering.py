#!/usr/bin/env python3
"""
Test phase-aware ordering for pipeline steps.

Verifies that steps are ordered correctly by execution phase:
1. Pre-branching universal (document_class_id = NULL, post_branching = False)
2. Document-specific (document_class_id != NULL)
3. Post-branching universal (document_class_id = NULL, post_branching = True)
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.modular_pipeline_models import Base, DynamicPipelineStepDB, AvailableModelDB
from app.repositories.pipeline_step_repository import PipelineStepRepository


@pytest.fixture(scope="function")
def test_db_session():
    """Create an in-memory SQLite database session for testing"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    # Seed with test data
    model = AvailableModelDB(
        name="test-model",
        display_name="Test Model",
        provider="OVH",
        max_tokens=4096,
        is_enabled=True
    )
    session.add(model)
    session.commit()

    # Add test steps
    steps = [
        DynamicPipelineStepDB(
            name="Pre-branching 1", order=1, prompt_template="test",
            selected_model_id=model.id, enabled=True, post_branching=False
        ),
        DynamicPipelineStepDB(
            name="Pre-branching 2", order=2, prompt_template="test",
            selected_model_id=model.id, enabled=True, post_branching=False
        ),
        DynamicPipelineStepDB(
            name="Doc-specific 1", order=10, prompt_template="test",
            selected_model_id=model.id, enabled=True, document_class_id=1, post_branching=False
        ),
        DynamicPipelineStepDB(
            name="Post-branching 1", order=20, prompt_template="test",
            selected_model_id=model.id, enabled=True, post_branching=True
        ),
    ]
    session.add_all(steps)
    session.commit()

    yield session

    session.close()
    Base.metadata.drop_all(engine)


def test_phase_aware_ordering(test_db_session):
    """Test that steps are ordered by phase first, then by order field."""
    repo = PipelineStepRepository(test_db_session)

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

    # Verify phase ordering is correct
    assert is_correct, f"Phase ordering is incorrect: {phase_order}"
    assert is_correct_enabled, f"Enabled steps phase ordering is incorrect: {phase_order_enabled}"
