#!/usr/bin/env python3
"""
Verify migration success by comparing DEV and PROD schemas post-migration
"""

import psycopg2
import sys


def get_table_count(conn):
    """Get count of tables"""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT COUNT(*)
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_type = 'BASE TABLE';
        """)
        return cur.fetchone()[0]


def get_table_list(conn):
    """Get list of tables"""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_type = 'BASE TABLE'
            ORDER BY table_name;
        """)
        return {row[0] for row in cur.fetchall()}


def get_column_count(conn, table):
    """Get column count for a table"""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT COUNT(*)
            FROM information_schema.columns
            WHERE table_schema = 'public'
            AND table_name = %s;
        """, (table,))
        return cur.fetchone()[0]


def verify():
    """Verify migration success"""
    DEV_URL = "postgresql://postgres:KfcqZpqRnRCTyvVxHKkDHjssedAjXZSp@turntable.proxy.rlwy.net:58299/railway"
    PROD_URL = "postgresql://postgres:VknAapdgHdGkHjkmsyHWsJyKCspFmqzO@gondola.proxy.rlwy.net:15456/railway"

    print("=" * 60)
    print("POST-MIGRATION VERIFICATION")
    print("=" * 60)

    # Connect to both databases
    print("\n🔌 Connecting to databases...")
    try:
        dev_conn = psycopg2.connect(DEV_URL)
        prod_conn = psycopg2.connect(PROD_URL)
        print("  ✅ Connected to both databases")
    except Exception as e:
        print(f"  ❌ Connection failed: {e}")
        sys.exit(1)

    # Compare table counts
    print("\n📊 Comparing table counts...")
    dev_count = get_table_count(dev_conn)
    prod_count = get_table_count(prod_conn)
    print(f"  DEV:  {dev_count} tables")
    print(f"  PROD: {prod_count} tables")

    if dev_count == prod_count:
        print("  ✅ Table counts match!")
    else:
        print(f"  ⚠️  Table count mismatch: {abs(dev_count - prod_count)} difference")

    # Compare table lists
    print("\n📋 Comparing table lists...")
    dev_tables = get_table_list(dev_conn)
    prod_tables = get_table_list(prod_conn)

    missing_in_prod = dev_tables - prod_tables
    extra_in_prod = prod_tables - dev_tables

    if not missing_in_prod and not extra_in_prod:
        print("  ✅ All tables present in both databases!")
    else:
        if missing_in_prod:
            print(f"  ⚠️  Missing in PROD: {missing_in_prod}")
        if extra_in_prod:
            print(f"  ⚠️  Extra in PROD: {extra_in_prod}")

    # Check specific migration items
    print("\n🔍 Verifying specific migration items...")

    # Check new tables
    new_tables = ['users', 'api_keys', 'refresh_tokens', 'audit_logs']
    for table in new_tables:
        if table in prod_tables:
            print(f"  ✅ {table} exists in PROD")
        else:
            print(f"  ❌ {table} missing in PROD")

    # Check pipeline_jobs columns
    print("\n📊 Checking pipeline_jobs columns...")
    with prod_conn.cursor() as cur:
        cur.execute("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'pipeline_jobs'
            AND column_name IN ('user_id', 'created_by_admin_id')
            ORDER BY column_name;
        """)
        cols = cur.fetchall()
        if len(cols) == 2:
            print("  ✅ Both new columns exist:")
            for col_name, col_type in cols:
                print(f"     - {col_name} ({col_type})")
        else:
            print(f"  ⚠️  Expected 2 columns, found {len(cols)}")

    # Check foreign keys
    print("\n🔗 Checking foreign keys...")
    with prod_conn.cursor() as cur:
        cur.execute("""
            SELECT
                con.conname as constraint_name,
                rel.relname as table_name,
                cl.relname as referenced_table
            FROM pg_constraint con
            JOIN pg_class rel ON rel.oid = con.conrelid
            JOIN pg_class cl ON cl.oid = con.confrelid
            WHERE con.contype = 'f'
            AND rel.relname = 'pipeline_jobs'
            AND con.conname LIKE '%user_id%' OR con.conname LIKE '%created_by%';
        """)
        fks = cur.fetchall()
        if len(fks) >= 2:
            print(f"  ✅ Foreign keys created: {len(fks)}")
            for fk_name, table, ref_table in fks:
                print(f"     - {fk_name}: {table} → {ref_table}")
        else:
            print(f"  ⚠️  Expected at least 2 FKs, found {len(fks)}")

    dev_conn.close()
    prod_conn.close()

    print("\n" + "=" * 60)
    print("✅ VERIFICATION COMPLETE!")
    print("=" * 60)


if __name__ == "__main__":
    verify()
