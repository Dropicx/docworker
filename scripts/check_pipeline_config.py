#!/usr/bin/env python3
"""
Quick diagnostic script to check pipeline step configuration
"""
import sys
sys.path.insert(0, '/media/catchmelit/5a972e8f-2616-4a45-b03c-2d2fd85f5030/Projects/doctranslator/backend')

from app.database.connection import get_db_session
from app.database.modular_pipeline_models import DynamicPipelineStepDB

def check_pipeline_steps():
    """Check pipeline steps configuration"""
    db = next(get_db_session())

    print("\n" + "="*80)
    print("PIPELINE STEPS CONFIGURATION CHECK")
    print("="*80 + "\n")

    all_steps = db.query(DynamicPipelineStepDB).order_by(DynamicPipelineStepDB.order).all()

    print(f"📊 Total steps in database: {len(all_steps)}\n")

    print("Step Details:")
    print("-" * 120)
    print(f"{'ID':<5} {'Order':<7} {'Enabled':<9} {'DocClass':<12} {'PostBranch':<12} {'Branching':<11} {'Name':<50}")
    print("-" * 120)

    for step in all_steps:
        doc_class = f"ID:{step.document_class_id}" if step.document_class_id else "NULL"
        branching = "YES" if step.is_branching_step else "NO"

        print(f"{step.id:<5} {step.order:<7} {str(step.enabled):<9} {doc_class:<12} {str(step.post_branching):<12} {branching:<11} {step.name:<50}")

    print("-" * 120)

    # Count by category
    enabled = [s for s in all_steps if s.enabled]
    universal = [s for s in all_steps if s.document_class_id is None]
    pre_branching_universal = [s for s in universal if not s.post_branching and s.enabled]

    print(f"\n📋 Summary:")
    print(f"   Enabled steps: {len(enabled)}")
    print(f"   Universal steps (doc_class_id IS NULL): {len(universal)}")
    print(f"   Pre-branching universal (should be loaded): {len(pre_branching_universal)}")
    print(f"   Post-branching steps: {len([s for s in all_steps if s.post_branching])}")

    if len(pre_branching_universal) == 0:
        print(f"\n⚠️  WARNING: No pre-branching universal steps found!")
        print(f"   This is why you see the fallback warning in logs.")
        print(f"   Fallback loads all {len(enabled)} enabled steps instead.")

    db.close()

if __name__ == "__main__":
    check_pipeline_steps()
