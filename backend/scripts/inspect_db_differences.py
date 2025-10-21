#!/usr/bin/env python3
"""
Database Inspection Script: Show detailed differences between Dev and Prod
"""

from sqlalchemy import create_engine, text
import sys
import json

# Database credentials
DEV_DB_URL = "postgresql://postgres:KfcqZpqRnRCTyvVxHKkDHjssedAjXZSp@turntable.proxy.rlwy.net:58299/railway"
PROD_DB_URL = "postgresql://postgres:VknAapdgHdGkHjkmsyHWsJyKCspFmqzO@gondola.proxy.rlwy.net:15456/railway"

def connect_db(db_url: str, name: str):
    """Connect to database"""
    try:
        engine = create_engine(db_url, pool_pre_ping=True)
        conn = engine.connect()
        print(f"✅ Connected to {name} database")
        return engine, conn
    except Exception as e:
        print(f"❌ Failed to connect to {name} database: {e}")
        sys.exit(1)

def get_table_schema(conn, table_name: str):
    """Get detailed schema for a table"""
    result = conn.execute(text("""
        SELECT
            column_name,
            data_type,
            character_maximum_length,
            is_nullable,
            column_default
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = :table_name
        ORDER BY ordinal_position
    """), {"table_name": table_name})

    return [dict(row._mapping) for row in result]

def get_table_data(conn, table_name: str):
    """Get all data from a table"""
    try:
        result = conn.execute(text(f"SELECT * FROM {table_name} ORDER BY id"))
        return [dict(row._mapping) for row in result]
    except Exception as e:
        print(f"⚠️  Error reading {table_name}: {e}")
        return []

def compare_schemas(dev_conn, prod_conn, table_name: str):
    """Compare schema for a specific table"""
    print(f"\n{'='*80}")
    print(f"Schema Comparison: {table_name}")
    print('='*80)

    dev_schema = get_table_schema(dev_conn, table_name)
    prod_schema = get_table_schema(prod_conn, table_name)

    # Create dictionaries for easy comparison
    dev_cols = {col['column_name']: col for col in dev_schema}
    prod_cols = {col['column_name']: col for col in prod_schema}

    # Columns in dev but not in prod
    missing_in_prod = set(dev_cols.keys()) - set(prod_cols.keys())
    if missing_in_prod:
        print(f"\n⚠️  Columns in DEV but MISSING in PROD:")
        for col in missing_in_prod:
            col_info = dev_cols[col]
            print(f"  - {col}: {col_info['data_type']}")

    # Columns in prod but not in dev
    extra_in_prod = set(prod_cols.keys()) - set(dev_cols.keys())
    if extra_in_prod:
        print(f"\n⚠️  Columns in PROD but NOT in DEV:")
        for col in extra_in_prod:
            col_info = prod_cols[col]
            print(f"  - {col}: {col_info['data_type']}")

    # Columns with different definitions
    common_cols = set(dev_cols.keys()) & set(prod_cols.keys())
    different_cols = []
    for col in common_cols:
        if dev_cols[col] != prod_cols[col]:
            different_cols.append(col)

    if different_cols:
        print(f"\n⚠️  Columns with DIFFERENT definitions:")
        for col in different_cols:
            print(f"\n  Column: {col}")
            print(f"    DEV:  {dev_cols[col]}")
            print(f"    PROD: {prod_cols[col]}")

    if not missing_in_prod and not extra_in_prod and not different_cols:
        print(f"\n✅ Schemas match perfectly!")

def compare_data(dev_conn, prod_conn, table_name: str):
    """Compare data in a specific table"""
    print(f"\n{'='*80}")
    print(f"Data Comparison: {table_name}")
    print('='*80)

    dev_data = get_table_data(dev_conn, table_name)
    prod_data = get_table_data(prod_conn, table_name)

    print(f"\nDEV rows: {len(dev_data)}")
    print(f"PROD rows: {len(prod_data)}")

    if dev_data == prod_data:
        print(f"✅ Data matches perfectly!")
    else:
        print(f"\n⚠️  Data differences found!")

        # Show data from both
        if dev_data:
            print(f"\nDEV data (first 5 rows):")
            for i, row in enumerate(dev_data[:5]):
                print(f"  Row {i+1}: {row}")

        if prod_data:
            print(f"\nPROD data (first 5 rows):")
            for i, row in enumerate(prod_data[:5]):
                print(f"  Row {i+1}: {row}")

def main():
    """Main inspection workflow"""
    print("=" * 80)
    print("DATABASE INSPECTION: Dev vs Prod")
    print("=" * 80)

    # Connect to databases
    dev_engine, dev_conn = connect_db(DEV_DB_URL, "DEV")
    prod_engine, prod_conn = connect_db(PROD_DB_URL, "PROD")

    try:
        # Tables with schema differences
        schema_diff_tables = [
            'pipeline_jobs',
            'ai_interaction_logs',
            'dynamic_pipeline_steps',
            'ocr_configuration',
            'pipeline_step_executions',
            'available_models'
        ]

        # Configuration tables to check data
        config_tables = [
            'universal_prompts',
            'document_specific_prompts',
            'universal_pipeline_steps',
            'system_settings'
        ]

        # Check schema differences
        print("\n\n" + "=" * 80)
        print("SCHEMA DIFFERENCES")
        print("=" * 80)

        for table in schema_diff_tables:
            compare_schemas(dev_conn, prod_conn, table)

        # Check data differences
        print("\n\n" + "=" * 80)
        print("DATA COMPARISON")
        print("=" * 80)

        for table in config_tables:
            compare_data(dev_conn, prod_conn, table)

    except Exception as e:
        print(f"\n❌ Inspection failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        dev_conn.close()
        prod_conn.close()
        print("\n🔌 Database connections closed")

if __name__ == "__main__":
    main()
