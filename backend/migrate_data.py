#!/usr/bin/env python3
"""
Database Data Migration Script: Dev to Prod
Migrates configuration data from dev to prod database
"""

import psycopg2
import json
from datetime import datetime
import sys

# Database connection strings
DEV_DB = "postgresql://postgres:KfcqZpqRnRCTyvVxHKkDHjssedAjXZSp@turntable.proxy.rlwy.net:58299/railway"
PROD_DB = "postgresql://postgres:VknAapdgHdGkHjkmsyHWsJyKCspFmqzO@gondola.proxy.rlwy.net:15456/railway"

def backup_table_data(conn, table_name):
    """Backup table data to dict"""
    print(f"📦 Backing up {table_name}...")
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM {table_name}")
    columns = [desc[0] for desc in cursor.description]
    rows = cursor.fetchall()
    cursor.close()

    data = []
    for row in rows:
        row_dict = {}
        for i, col in enumerate(columns):
            value = row[i]
            # Convert to JSON-serializable format
            if isinstance(value, datetime):
                value = value.isoformat()
            row_dict[col] = value
        data.append(row_dict)

    print(f"   ✓ Backed up {len(data)} rows from {table_name}")
    return {'columns': columns, 'data': data}

def clear_table(conn, table_name):
    """Clear all data from a table"""
    print(f"🗑️  Clearing {table_name}...")
    cursor = conn.cursor()
    cursor.execute(f"DELETE FROM {table_name}")
    conn.commit()
    cursor.close()
    print(f"   ✓ Cleared {table_name}")

def migrate_table(dev_conn, prod_conn, table_name, backup_first=True):
    """Migrate table data from dev to prod"""
    print(f"\n{'='*60}")
    print(f"📊 Migrating {table_name}")
    print(f"{'='*60}")

    # Backup prod data if requested
    prod_backup = None
    if backup_first:
        prod_backup = backup_table_data(prod_conn, table_name)

    # Get dev data
    dev_data = backup_table_data(dev_conn, table_name)

    if len(dev_data['data']) == 0:
        print(f"   ⚠️  No data in dev {table_name}, skipping...")
        return prod_backup

    # Clear prod table
    clear_table(prod_conn, table_name)

    # Insert dev data into prod
    print(f"📥 Inserting {len(dev_data['data'])} rows into prod {table_name}...")
    cursor = prod_conn.cursor()

    for row in dev_data['data']:
        columns = list(row.keys())
        # Convert dict/list values to JSON strings
        values = []
        for col in columns:
            val = row[col]
            if isinstance(val, (dict, list)):
                val = json.dumps(val)
            values.append(val)

        placeholders = ','.join(['%s'] * len(columns))
        columns_str = ','.join([f'"{col}"' for col in columns])

        query = f"INSERT INTO {table_name} ({columns_str}) VALUES ({placeholders})"
        cursor.execute(query, values)

    prod_conn.commit()
    cursor.close()
    print(f"   ✓ Migration of {table_name} completed!")

    return prod_backup

def main():
    """Main migration process"""
    print("\n" + "="*60)
    print("🚀 DATABASE MIGRATION: Dev → Prod")
    print("="*60 + "\n")

    # Connect to databases
    print("🔌 Connecting to databases...")
    try:
        dev_conn = psycopg2.connect(DEV_DB)
        prod_conn = psycopg2.connect(PROD_DB)
        print("   ✓ Connected to both databases\n")
    except Exception as e:
        print(f"   ❌ Connection failed: {e}")
        sys.exit(1)

    # Create backup file
    backup_file = f"prod_config_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    backups = {}

    try:
        # Migration order (respects foreign keys)
        tables_to_migrate = [
            'available_models',      # No dependencies
            'document_classes',      # No dependencies
            'dynamic_pipeline_steps', # Depends on available_models, document_classes
            'ocr_configuration',     # No dependencies
            'system_settings'        # No dependencies
        ]

        for table in tables_to_migrate:
            backup = migrate_table(dev_conn, prod_conn, table, backup_first=True)
            backups[table] = backup

        # Save backup file
        print(f"\n💾 Saving backup to {backup_file}...")
        with open(backup_file, 'w') as f:
            json.dump(backups, f, indent=2, default=str)
        print(f"   ✓ Backup saved!")

        print("\n" + "="*60)
        print("✅ MIGRATION COMPLETED SUCCESSFULLY!")
        print("="*60)
        print(f"\n📁 Backup file: {backup_file}")
        print("\n📊 Migration Summary:")
        for table in tables_to_migrate:
            if table in backups and backups[table]:
                count = len(backups[table]['data'])
                print(f"   • {table}: {count} rows migrated")

    except Exception as e:
        print(f"\n❌ MIGRATION FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    finally:
        dev_conn.close()
        prod_conn.close()
        print("\n🔌 Database connections closed")

if __name__ == "__main__":
    main()
