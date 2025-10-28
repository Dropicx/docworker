#!/usr/bin/env python3
"""
Execute migration script on PROD database with safety checks
"""

import sys
import psycopg2


def execute_migration(db_url: str, sql_file: str):
    """Execute migration SQL file"""
    print("=" * 60)
    print("DATABASE MIGRATION EXECUTOR")
    print("=" * 60)

    # Read SQL file
    print(f"\n📖 Reading migration file: {sql_file}")
    try:
        with open(sql_file, 'r') as f:
            sql = f.read()
        print(f"  ✅ Read {len(sql)} characters")
    except Exception as e:
        print(f"  ❌ Failed to read file: {e}")
        sys.exit(1)

    # Connect to database
    print("\n🔌 Connecting to PROD database...")
    try:
        conn = psycopg2.connect(db_url)
        conn.autocommit = False  # Explicit transaction control
        print("  ✅ Connected successfully")
    except Exception as e:
        print(f"  ❌ Connection failed: {e}")
        sys.exit(1)

    # Execute migration
    print("\n🚀 Executing migration...")
    try:
        cursor = conn.cursor()
        cursor.execute(sql)
        conn.commit()
        print("  ✅ Migration executed successfully")
        print("  ✅ Transaction committed")
    except Exception as e:
        print(f"  ❌ Migration failed: {e}")
        print("  🔄 Rolling back transaction...")
        conn.rollback()
        print("  ✅ Rollback complete - no changes applied")
        cursor.close()
        conn.close()
        sys.exit(1)

    # Verify tables
    print("\n🔍 Verifying migration...")
    try:
        cursor.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)
        tables = [row[0] for row in cursor.fetchall()]
        print(f"  ✅ Total tables: {len(tables)}")

        # Check for new tables
        new_tables = ['users', 'api_keys', 'refresh_tokens', 'audit_logs']
        for table in new_tables:
            if table in tables:
                print(f"  ✅ {table} created successfully")
            else:
                print(f"  ⚠️  {table} not found")

        # Check pipeline_jobs columns
        cursor.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'pipeline_jobs'
            AND column_name IN ('user_id', 'created_by_admin_id');
        """)
        new_cols = [row[0] for row in cursor.fetchall()]
        print(f"  ✅ pipeline_jobs new columns: {len(new_cols)}/2")
        for col in new_cols:
            print(f"     ✅ {col}")

    except Exception as e:
        print(f"  ⚠️  Verification warning: {e}")

    cursor.close()
    conn.close()

    print("\n" + "=" * 60)
    print("✅ MIGRATION COMPLETE!")
    print("=" * 60)


def main():
    PROD_URL = "postgresql://postgres:VknAapdgHdGkHjkmsyHWsJyKCspFmqzO@gondola.proxy.rlwy.net:15456/railway"
    SQL_FILE = "scripts/migration_dev_to_prod.sql"

    print("\n⚠️  WARNING: You are about to modify the PRODUCTION database!")
    print("Database: gondola.proxy.rlwy.net:15456")
    print(f"SQL File: {SQL_FILE}\n")

    response = input("Type 'YES' to proceed with migration: ")

    if response != 'YES':
        print("❌ Migration cancelled")
        sys.exit(0)

    execute_migration(PROD_URL, SQL_FILE)


if __name__ == "__main__":
    main()
