#!/usr/bin/env python3
"""Check when universal steps were created/modified."""

import os

os.environ["DATABASE_URL"] = (
    "postgresql://postgres:KfcqZpqRnRCTyvVxHKkDHjssedAjXZSp@turntable.proxy.rlwy.net:58299/railway"
)
os.environ["OVH_AI_ENDPOINTS_ACCESS_TOKEN"] = "dummy"

import sys

sys.path.insert(
    0, "/media/catchmelit/5a972e8f-2616-4a45-b03c-2d2fd85f5030/Projects/doctranslator/backend"
)

from sqlalchemy import create_engine, text
from datetime import datetime, timezone

DATABASE_URL = (
    "postgresql://postgres:KfcqZpqRnRCTyvVxHKkDHjssedAjXZSp@turntable.proxy.rlwy.net:58299/railway"
)
engine = create_engine(DATABASE_URL)

print("\n" + "=" * 120)
print("UNIVERSAL STEPS - CREATION AND MODIFICATION TIMESTAMPS")
print("=" * 120)
print("\nWorker logs timestamp: 2025-10-20 14:00:52 UTC (reported 0 universal steps)")
print(f'Current time: {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")} UTC')

with engine.connect() as conn:
    result = conn.execute(
        text("""
        SELECT
            id,
            name,
            document_class_id,
            post_branching,
            enabled,
            created_at,
            last_modified
        FROM dynamic_pipeline_steps
        WHERE document_class_id IS NULL
        AND enabled = TRUE
        ORDER BY id
    """)
    )

    steps = result.fetchall()
    print(f"\n📊 Universal steps with document_class_id = NULL: {len(steps)}\n")

    print(f'{"ID":<5} {"Name":<45} {"PostBranch":<12} {"Created At":<25} {"Last Modified":<25}')
    print("-" * 120)

    for step in steps:
        step_id, name, doc_class_id, post_branching, enabled, created_at, last_modified = step
        created_str = created_at.strftime("%Y-%m-%d %H:%M:%S") if created_at else "N/A"
        modified_str = last_modified.strftime("%Y-%m-%d %H:%M:%S") if last_modified else "N/A"

        print(
            f"{step_id:<5} {name:<45} {str(post_branching):<12} {created_str:<25} {modified_str:<25}"
        )

print("\n" + "=" * 120)
print("ANALYSIS")
print("=" * 120)

print(
    "\n🤔 If these steps were modified AFTER 14:00:52 UTC, that would explain why the worker saw 0 steps."
)
print(
    "🤔 If these steps existed BEFORE 14:00:52 UTC, there might be a database connection or session issue."
)

print("\n" + "=" * 120)
