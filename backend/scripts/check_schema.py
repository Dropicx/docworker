#!/usr/bin/env python3
"""Check database schema for dynamic_pipeline_steps table."""
import os
os.environ['DATABASE_URL'] = 'postgresql://postgres:KfcqZpqRnRCTyvVxHKkDHjssedAjXZSp@turntable.proxy.rlwy.net:58299/railway'
os.environ['OVH_AI_ENDPOINTS_ACCESS_TOKEN'] = 'dummy'

import sys
sys.path.insert(0, '/media/catchmelit/5a972e8f-2616-4a45-b03c-2d2fd85f5030/Projects/doctranslator/backend')

from sqlalchemy import create_engine, text, inspect

DATABASE_URL = 'postgresql://postgres:KfcqZpqRnRCTyvVxHKkDHjssedAjXZSp@turntable.proxy.rlwy.net:58299/railway'
engine = create_engine(DATABASE_URL)

print('\n' + '='*120)
print('DATABASE SCHEMA - dynamic_pipeline_steps TABLE')
print('='*120)

inspector = inspect(engine)
columns = inspector.get_columns('dynamic_pipeline_steps')

print('\n📋 Column Names and Types:\n')
for col in columns:
    nullable = 'NULL' if col['nullable'] else 'NOT NULL'
    print(f'   {col["name"]:<30} {str(col["type"]):<30} {nullable}')

print('\n' + '='*120)
print('TEST THE EXACT QUERY FROM get_universal_steps()')
print('='*120)

with engine.connect() as conn:
    # This is the EXACT query from the repository
    result = conn.execute(text('''
        SELECT *
        FROM dynamic_pipeline_steps
        WHERE document_class_id IS NULL
        AND enabled = TRUE
        ORDER BY "order"
    '''))

    steps = result.fetchall()
    print(f'\n✅ Query result: {len(steps)} steps\n')

    if steps:
        for step in steps[:5]:  # Show first 5
            print(f'   ID: {step[0]}, Name: {step[1]}')
    else:
        print('   ❌ Query returned 0 results!')

print('\n' + '='*120)
print('TEST WITH ENABLED = true (lowercase boolean)')
print('='*120)

with engine.connect() as conn:
    result = conn.execute(text('''
        SELECT *
        FROM dynamic_pipeline_steps
        WHERE document_class_id IS NULL
        AND enabled = true
        ORDER BY "order"
    '''))

    steps = result.fetchall()
    print(f'\n✅ Query result: {len(steps)} steps')

print('\n' + '='*120)
print('TEST WITH enabled::boolean (explicit cast)')
print('='*120)

with engine.connect() as conn:
    result = conn.execute(text('''
        SELECT *
        FROM dynamic_pipeline_steps
        WHERE document_class_id IS NULL
        AND enabled::boolean IS TRUE
        ORDER BY "order"
    '''))

    steps = result.fetchall()
    print(f'\n✅ Query result: {len(steps)} steps')

print('\n' + '='*120)
