#!/usr/bin/env python3
"""
Check production database pipeline steps configuration.
Diagnose why get_universal_steps() returns 0 results.
"""
import sys
sys.path.insert(0, '/media/catchmelit/5a972e8f-2616-4a45-b03c-2d2fd85f5030/Projects/doctranslator/backend')

from app.database.connection import get_db_session
from app.repositories.pipeline_step_repository import PipelineStepRepository


def main():
    db = next(get_db_session())
    repo = PipelineStepRepository(db)

    print('\n' + '='*100)
    print('ALL ENABLED PIPELINE STEPS')
    print('='*100)

    all_enabled = repo.get_enabled_steps()
    print(f'\n📊 Total enabled steps: {len(all_enabled)}\n')
    print(f'{"ID":<5} {"Name":<40} {"Order":<7} {"DocClass":<15} {"PostBranch":<12} {"Branching":<10}')
    print('-' * 100)

    for step in all_enabled:
        doc_class = f'ID:{step.document_class_id}' if step.document_class_id else 'NULL'
        print(f'{step.id:<5} {step.name:<40} {step.order:<7} {doc_class:<15} {str(step.post_branching):<12} {str(step.is_branching_step):<10}')

    print('\n' + '='*100)
    print('UNIVERSAL STEPS (document_class_id = NULL)')
    print('='*100)

    universal_steps = repo.get_universal_steps()
    print(f'\n📊 Universal steps found: {len(universal_steps)}\n')

    if universal_steps:
        for step in universal_steps:
            print(f'ID: {step.id}, Name: {step.name}, Order: {step.order}, PostBranching: {step.post_branching}')
    else:
        print('❌ NO UNIVERSAL STEPS FOUND!')
        print('\n🔍 Root Cause Analysis:')
        print('   - get_universal_steps() returns 0 because ALL enabled steps have document_class_id set')
        print('   - The query filters for: document_class_id IS NULL AND enabled = True')
        print('   - None of the enabled steps match this criteria')
        print('\n💡 Solution:')
        print('   - Pre-branching universal steps must have document_class_id = NULL')
        print('   - Post-branching universal steps must have document_class_id = NULL AND post_branching = True')
        print('   - Update the database to set document_class_id = NULL for universal steps')

    print('\n' + '='*100)
    print('PRE-BRANCHING UNIVERSAL STEPS (document_class_id = NULL AND post_branching = False)')
    print('='*100)

    # Manual query to check pre-branching
    pre_branching = [s for s in universal_steps if not s.post_branching]
    print(f'\n📊 Pre-branching universal steps: {len(pre_branching)}\n')

    if pre_branching:
        for step in pre_branching:
            print(f'ID: {step.id}, Name: {step.name}, Order: {step.order}')
    else:
        print('❌ NO PRE-BRANCHING UNIVERSAL STEPS!')

    print('\n' + '='*100)
    print('POST-BRANCHING UNIVERSAL STEPS (document_class_id = NULL AND post_branching = True)')
    print('='*100)

    post_branching = repo.get_post_branching_steps()
    print(f'\n📊 Post-branching universal steps: {len(post_branching)}\n')

    if post_branching:
        for step in post_branching:
            print(f'ID: {step.id}, Name: {step.name}, Order: {step.order}')
    else:
        print('❌ NO POST-BRANCHING UNIVERSAL STEPS!')

    print('\n' + '='*100)
    db.close()


if __name__ == '__main__':
    main()
