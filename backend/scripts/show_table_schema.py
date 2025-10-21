#!/usr/bin/env python3
"""
Show schema for a specific table
"""

from sqlalchemy import create_engine, text
import sys

# Database credentials
DEV_DB_URL = "postgresql://postgres:KfcqZpqRnRCTyvVxHKkDHjssedAjXZSp@turntable.proxy.rlwy.net:58299/railway"

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

def show_schema(conn, table_name: str):
    """Show schema for a table"""
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

    print(f"\nSchema for {table_name}:")
    print("=" * 80)

    for row in result:
        col_name = row[0]
        col_type = row[1]
        max_len = row[2]
        nullable = row[3]
        default = row[4]

        type_str = col_type
        if max_len:
            type_str += f"({max_len})"

        print(f"  {col_name:30} {type_str:30} {'NULL' if nullable == 'YES' else 'NOT NULL':10} {default if default else ''}")

def show_sample_data(conn, table_name: str):
    """Show sample data from table"""
    result = conn.execute(text(f"SELECT * FROM {table_name} LIMIT 3"))

    print(f"\nSample data from {table_name}:")
    print("=" * 80)

    for i, row in enumerate(result):
        print(f"\nRow {i+1}:")
        for key, value in row._mapping.items():
            print(f"  {key}: {value}")

def main():
    """Main workflow"""
    table_name = sys.argv[1] if len(sys.argv) > 1 else "dynamic_pipeline_steps"

    print("=" * 80)
    print(f"TABLE SCHEMA: {table_name}")
    print("=" * 80)

    # Connect to database
    dev_engine, dev_conn = connect_db(DEV_DB_URL, "DEV")

    try:
        show_schema(dev_conn, table_name)
        show_sample_data(dev_conn, table_name)

    except Exception as e:
        print(f"\n❌ Failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        dev_conn.close()
        print("\n🔌 Database connection closed")

if __name__ == "__main__":
    main()
