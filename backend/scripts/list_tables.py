#!/usr/bin/env python3
"""
List all tables in Dev and Prod databases
"""

from sqlalchemy import create_engine, text
import sys

# Database credentials
DEV_DB_URL = (
    "postgresql://postgres:KfcqZpqRnRCTyvVxHKkDHjssedAjXZSp@turntable.proxy.rlwy.net:58299/railway"
)
PROD_DB_URL = (
    "postgresql://postgres:VknAapdgHdGkHjkmsyHWsJyKCspFmqzO@gondola.proxy.rlwy.net:15456/railway"
)


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


def get_table_list(conn):
    """Get list of tables in database"""
    result = conn.execute(
        text("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        ORDER BY table_name
    """)
    )
    return [row[0] for row in result]


def get_row_count(conn, table_name: str):
    """Get row count for a table"""
    try:
        result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
        return result.fetchone()[0]
    except Exception as e:
        return f"Error: {e}"


def main():
    """Main listing workflow"""
    print("=" * 80)
    print("DATABASE TABLES LISTING")
    print("=" * 80)

    # Connect to databases
    dev_engine, dev_conn = connect_db(DEV_DB_URL, "DEV")
    prod_engine, prod_conn = connect_db(PROD_DB_URL, "PROD")

    try:
        dev_tables = get_table_list(dev_conn)
        prod_tables = get_table_list(prod_conn)

        print(f"\n{'='*80}")
        print(f"DEV Database Tables ({len(dev_tables)} total)")
        print("=" * 80)

        for table in dev_tables:
            count = get_row_count(dev_conn, table)
            print(f"  - {table}: {count} rows")

        print(f"\n{'='*80}")
        print(f"PROD Database Tables ({len(prod_tables)} total)")
        print("=" * 80)

        for table in prod_tables:
            count = get_row_count(prod_conn, table)
            print(f"  - {table}: {count} rows")

        # Compare
        print(f"\n{'='*80}")
        print("COMPARISON")
        print("=" * 80)

        missing_in_prod = set(dev_tables) - set(prod_tables)
        missing_in_dev = set(prod_tables) - set(dev_tables)
        common = set(dev_tables) & set(prod_tables)

        if missing_in_prod:
            print(f"\n⚠️  Tables in DEV but missing in PROD:")
            for table in missing_in_prod:
                print(f"  - {table}")

        if missing_in_dev:
            print(f"\n⚠️  Tables in PROD but missing in DEV:")
            for table in missing_in_dev:
                print(f"  - {table}")

        print(f"\n✅ Common tables: {len(common)}")
        print(
            f"✅ Both databases have the same tables: {missing_in_prod == missing_in_dev == set()}"
        )

    except Exception as e:
        print(f"\n❌ Listing failed: {e}")
        import traceback

        traceback.print_exc()
    finally:
        dev_conn.close()
        prod_conn.close()
        print("\n🔌 Database connections closed")


if __name__ == "__main__":
    main()
