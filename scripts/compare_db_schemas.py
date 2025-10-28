#!/usr/bin/env python3
"""
Comprehensive Database Schema Comparison Tool
Compares DEV and PROD PostgreSQL databases and generates migration reports.
"""

import json
import sys
from datetime import datetime
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass, asdict
import psycopg2
from psycopg2.extras import RealDictCursor


@dataclass
class ColumnInfo:
    """Column definition information"""
    name: str
    data_type: str
    is_nullable: str
    column_default: str = None
    character_maximum_length: int = None
    numeric_precision: int = None
    numeric_scale: int = None


@dataclass
class IndexInfo:
    """Index definition information"""
    name: str
    columns: List[str]
    is_unique: bool
    is_primary: bool
    index_type: str = None


@dataclass
class ForeignKeyInfo:
    """Foreign key constraint information"""
    name: str
    source_table: str
    source_columns: List[str]
    target_table: str
    target_columns: List[str]
    on_delete: str = None
    on_update: str = None


@dataclass
class TableSchema:
    """Complete table schema"""
    name: str
    columns: List[ColumnInfo]
    indexes: List[IndexInfo]
    foreign_keys: List[ForeignKeyInfo]
    constraints: List[Dict[str, Any]]


class DatabaseSchemaComparator:
    """Compare schemas between two PostgreSQL databases"""

    def __init__(self, dev_url: str, prod_url: str):
        self.dev_url = dev_url
        self.prod_url = prod_url
        self.dev_conn = None
        self.prod_conn = None

    def connect(self):
        """Establish database connections"""
        print("🔌 Connecting to databases...")
        try:
            self.dev_conn = psycopg2.connect(self.dev_url)
            print("  ✅ Connected to DEV database")
        except Exception as e:
            print(f"  ❌ Failed to connect to DEV: {e}")
            sys.exit(1)

        try:
            self.prod_conn = psycopg2.connect(self.prod_url)
            print("  ✅ Connected to PROD database")
        except Exception as e:
            print(f"  ❌ Failed to connect to PROD: {e}")
            sys.exit(1)

    def disconnect(self):
        """Close database connections"""
        if self.dev_conn:
            self.dev_conn.close()
        if self.prod_conn:
            self.prod_conn.close()
        print("🔌 Disconnected from databases")

    def get_tables(self, conn) -> List[str]:
        """Get list of all tables in the database"""
        query = """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_type = 'BASE TABLE'
            ORDER BY table_name;
        """
        with conn.cursor() as cur:
            cur.execute(query)
            return [row[0] for row in cur.fetchall()]

    def get_columns(self, conn, table_name: str) -> List[ColumnInfo]:
        """Get column information for a table"""
        query = """
            SELECT
                column_name as name,
                data_type,
                is_nullable,
                column_default,
                character_maximum_length,
                numeric_precision,
                numeric_scale
            FROM information_schema.columns
            WHERE table_schema = 'public'
            AND table_name = %s
            ORDER BY ordinal_position;
        """
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, (table_name,))
            return [ColumnInfo(**row) for row in cur.fetchall()]

    def get_indexes(self, conn, table_name: str) -> List[IndexInfo]:
        """Get index information for a table"""
        query = """
            SELECT
                i.relname as index_name,
                array_agg(a.attname ORDER BY a.attnum) as column_names,
                ix.indisunique as is_unique,
                ix.indisprimary as is_primary,
                am.amname as index_type
            FROM pg_class t
            JOIN pg_index ix ON t.oid = ix.indrelid
            JOIN pg_class i ON i.oid = ix.indexrelid
            JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = ANY(ix.indkey)
            JOIN pg_am am ON i.relam = am.oid
            WHERE t.relkind = 'r'
            AND t.relname = %s
            AND t.relnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public')
            GROUP BY i.relname, ix.indisunique, ix.indisprimary, am.amname
            ORDER BY i.relname;
        """
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, (table_name,))
            return [IndexInfo(
                name=row['index_name'],
                columns=row['column_names'],
                is_unique=row['is_unique'],
                is_primary=row['is_primary'],
                index_type=row['index_type']
            ) for row in cur.fetchall()]

    def get_foreign_keys(self, conn, table_name: str) -> List[ForeignKeyInfo]:
        """Get foreign key information for a table"""
        query = """
            SELECT
                con.conname as constraint_name,
                att.attname as source_column,
                cl.relname as target_table,
                att2.attname as target_column,
                con.confdeltype as on_delete,
                con.confupdtype as on_update
            FROM pg_constraint con
            JOIN pg_class rel ON rel.oid = con.conrelid
            JOIN pg_attribute att ON att.attrelid = con.conrelid AND att.attnum = ANY(con.conkey)
            JOIN pg_class cl ON cl.oid = con.confrelid
            JOIN pg_attribute att2 ON att2.attrelid = con.confrelid AND att2.attnum = ANY(con.confkey)
            WHERE con.contype = 'f'
            AND rel.relname = %s
            AND rel.relnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public')
            ORDER BY con.conname;
        """
        fk_dict = {}
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, (table_name,))
            for row in cur.fetchall():
                fk_name = row['constraint_name']
                if fk_name not in fk_dict:
                    fk_dict[fk_name] = {
                        'name': fk_name,
                        'source_table': table_name,
                        'source_columns': [],
                        'target_table': row['target_table'],
                        'target_columns': [],
                        'on_delete': self._translate_action(row['on_delete']),
                        'on_update': self._translate_action(row['on_update'])
                    }
                fk_dict[fk_name]['source_columns'].append(row['source_column'])
                fk_dict[fk_name]['target_columns'].append(row['target_column'])

        return [ForeignKeyInfo(**fk) for fk in fk_dict.values()]

    def _translate_action(self, action_code: str) -> str:
        """Translate PostgreSQL action code to readable string"""
        actions = {
            'a': 'NO ACTION',
            'r': 'RESTRICT',
            'c': 'CASCADE',
            'n': 'SET NULL',
            'd': 'SET DEFAULT'
        }
        return actions.get(action_code, 'NO ACTION')

    def get_table_schema(self, conn, table_name: str) -> TableSchema:
        """Get complete schema for a table"""
        return TableSchema(
            name=table_name,
            columns=self.get_columns(conn, table_name),
            indexes=self.get_indexes(conn, table_name),
            foreign_keys=self.get_foreign_keys(conn, table_name),
            constraints=[]  # Can be extended if needed
        )

    def compare_schemas(self) -> Dict[str, Any]:
        """Compare DEV and PROD schemas"""
        print("\n📊 Analyzing schemas...")

        # Get table lists
        dev_tables = set(self.get_tables(self.dev_conn))
        prod_tables = set(self.get_tables(self.prod_conn))

        print(f"  DEV tables: {len(dev_tables)}")
        print(f"  PROD tables: {len(prod_tables)}")

        # Find differences
        new_tables = dev_tables - prod_tables
        removed_tables = prod_tables - dev_tables
        common_tables = dev_tables & prod_tables

        comparison = {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'dev_table_count': len(dev_tables),
                'prod_table_count': len(prod_tables),
                'new_tables': len(new_tables),
                'removed_tables': len(removed_tables),
                'common_tables': len(common_tables)
            },
            'new_tables': sorted(list(new_tables)),
            'removed_tables': sorted(list(removed_tables)),
            'table_differences': {}
        }

        # Compare common tables
        print(f"\n🔍 Comparing {len(common_tables)} common tables...")
        for table in sorted(common_tables):
            print(f"  Analyzing: {table}")
            dev_schema = self.get_table_schema(self.dev_conn, table)
            prod_schema = self.get_table_schema(self.prod_conn, table)

            table_diff = self.compare_table_schemas(dev_schema, prod_schema)
            if table_diff['has_differences']:
                comparison['table_differences'][table] = table_diff

        return comparison

    def compare_table_schemas(self, dev: TableSchema, prod: TableSchema) -> Dict[str, Any]:
        """Compare schemas of two tables"""
        diff = {
            'has_differences': False,
            'column_differences': {},
            'index_differences': {},
            'foreign_key_differences': {}
        }

        # Compare columns
        dev_cols = {col.name: col for col in dev.columns}
        prod_cols = {col.name: col for col in prod.columns}

        new_cols = set(dev_cols.keys()) - set(prod_cols.keys())
        removed_cols = set(prod_cols.keys()) - set(dev_cols.keys())
        common_cols = set(dev_cols.keys()) & set(prod_cols.keys())

        if new_cols:
            diff['has_differences'] = True
            diff['column_differences']['new'] = [
                asdict(dev_cols[col]) for col in sorted(new_cols)
            ]

        if removed_cols:
            diff['has_differences'] = True
            diff['column_differences']['removed'] = [
                asdict(prod_cols[col]) for col in sorted(removed_cols)
            ]

        # Check for modified columns
        modified = []
        for col_name in common_cols:
            dev_col = dev_cols[col_name]
            prod_col = prod_cols[col_name]
            if (dev_col.data_type != prod_col.data_type or
                dev_col.is_nullable != prod_col.is_nullable or
                dev_col.column_default != prod_col.column_default):
                modified.append({
                    'name': col_name,
                    'dev': asdict(dev_col),
                    'prod': asdict(prod_col)
                })

        if modified:
            diff['has_differences'] = True
            diff['column_differences']['modified'] = modified

        # Compare indexes (simplified)
        dev_idx = {idx.name: idx for idx in dev.indexes}
        prod_idx = {idx.name: idx for idx in prod.indexes}

        new_idx = set(dev_idx.keys()) - set(prod_idx.keys())
        removed_idx = set(prod_idx.keys()) - set(dev_idx.keys())

        if new_idx:
            diff['has_differences'] = True
            diff['index_differences']['new'] = [
                asdict(dev_idx[idx]) for idx in sorted(new_idx)
            ]

        if removed_idx:
            diff['has_differences'] = True
            diff['index_differences']['removed'] = [
                asdict(prod_idx[idx]) for idx in sorted(removed_idx)
            ]

        # Compare foreign keys
        dev_fk = {fk.name: fk for fk in dev.foreign_keys}
        prod_fk = {fk.name: fk for fk in prod.foreign_keys}

        new_fk = set(dev_fk.keys()) - set(prod_fk.keys())
        removed_fk = set(prod_fk.keys()) - set(dev_fk.keys())

        if new_fk:
            diff['has_differences'] = True
            diff['foreign_key_differences']['new'] = [
                asdict(dev_fk[fk]) for fk in sorted(new_fk)
            ]

        if removed_fk:
            diff['has_differences'] = True
            diff['foreign_key_differences']['removed'] = [
                asdict(prod_fk[fk]) for fk in sorted(removed_fk)
            ]

        return diff

    def generate_migration_sql(self, comparison: Dict[str, Any]) -> str:
        """Generate SQL migration script"""
        sql_lines = [
            "-- Migration Script: DEV to PROD",
            f"-- Generated: {datetime.now().isoformat()}",
            "-- WARNING: Review carefully before executing!",
            "",
            "BEGIN;",
            ""
        ]

        # Create new tables
        if comparison['new_tables']:
            sql_lines.append("-- ============================================")
            sql_lines.append("-- NEW TABLES")
            sql_lines.append("-- ============================================")
            sql_lines.append("")

            for table in comparison['new_tables']:
                schema = self.get_table_schema(self.dev_conn, table)
                sql_lines.append(f"-- Creating table: {table}")
                sql_lines.append(self._generate_create_table_sql(schema))
                sql_lines.append("")

        # Modify existing tables
        if comparison['table_differences']:
            sql_lines.append("-- ============================================")
            sql_lines.append("-- TABLE MODIFICATIONS")
            sql_lines.append("-- ============================================")
            sql_lines.append("")

            for table, diff in comparison['table_differences'].items():
                sql_lines.append(f"-- Modifying table: {table}")

                # Add new columns
                if 'new' in diff.get('column_differences', {}):
                    for col in diff['column_differences']['new']:
                        sql_lines.append(self._generate_add_column_sql(table, col))

                # Modify columns
                if 'modified' in diff.get('column_differences', {}):
                    for col in diff['column_differences']['modified']:
                        sql_lines.append(f"-- Modified column: {col['name']}")
                        sql_lines.append(f"-- DEV: {col['dev']}")
                        sql_lines.append(f"-- PROD: {col['prod']}")
                        sql_lines.append(f"-- TODO: Review and add ALTER COLUMN statement if needed")

                # Add new indexes
                if 'new' in diff.get('index_differences', {}):
                    for idx in diff['index_differences']['new']:
                        if not idx['is_primary']:  # Skip primary keys
                            sql_lines.append(self._generate_create_index_sql(table, idx))

                # Add new foreign keys
                if 'new' in diff.get('foreign_key_differences', {}):
                    for fk in diff['foreign_key_differences']['new']:
                        sql_lines.append(self._generate_add_foreign_key_sql(fk))

                sql_lines.append("")

        sql_lines.append("COMMIT;")
        sql_lines.append("")
        sql_lines.append("-- Migration complete!")

        return "\n".join(sql_lines)

    def _generate_create_table_sql(self, schema: TableSchema) -> str:
        """Generate CREATE TABLE statement"""
        lines = [f"CREATE TABLE {schema.name} ("]

        col_defs = []
        for col in schema.columns:
            col_def = f"    {col.name} {col.data_type}"

            if col.character_maximum_length:
                col_def += f"({col.character_maximum_length})"

            if col.is_nullable == 'NO':
                col_def += " NOT NULL"

            if col.column_default:
                col_def += f" DEFAULT {col.column_default}"

            col_defs.append(col_def)

        lines.append(",\n".join(col_defs))
        lines.append(");")

        # Add indexes
        for idx in schema.indexes:
            if not idx.is_primary:
                lines.append(self._generate_create_index_sql(schema.name, idx))

        return "\n".join(lines)

    def _generate_add_column_sql(self, table: str, col: Dict[str, Any]) -> str:
        """Generate ALTER TABLE ADD COLUMN statement"""
        sql = f"ALTER TABLE {table} ADD COLUMN {col['name']} {col['data_type']}"

        if col.get('character_maximum_length'):
            sql += f"({col['character_maximum_length']})"

        if col['is_nullable'] == 'NO':
            sql += " NOT NULL"

        if col.get('column_default'):
            sql += f" DEFAULT {col['column_default']}"

        return sql + ";"

    def _generate_create_index_sql(self, table: str, idx) -> str:
        """Generate CREATE INDEX statement"""
        # Handle both dict and IndexInfo object
        if isinstance(idx, dict):
            unique = "UNIQUE " if idx['is_unique'] else ""
            cols = ", ".join(idx['columns'])
            name = idx['name']
        else:
            unique = "UNIQUE " if idx.is_unique else ""
            cols = ", ".join(idx.columns)
            name = idx.name
        return f"CREATE {unique}INDEX {name} ON {table} ({cols});"

    def _generate_add_foreign_key_sql(self, fk: Dict[str, Any]) -> str:
        """Generate ALTER TABLE ADD FOREIGN KEY statement"""
        source_cols = ", ".join(fk['source_columns'])
        target_cols = ", ".join(fk['target_columns'])
        sql = f"ALTER TABLE {fk['source_table']} ADD CONSTRAINT {fk['name']} "
        sql += f"FOREIGN KEY ({source_cols}) REFERENCES {fk['target_table']} ({target_cols})"

        if fk.get('on_delete'):
            sql += f" ON DELETE {fk['on_delete']}"
        if fk.get('on_update'):
            sql += f" ON UPDATE {fk['on_update']}"

        return sql + ";"

    def assess_risk(self, comparison: Dict[str, Any]) -> Dict[str, Any]:
        """Assess migration risk level"""
        risk = {
            'level': 'LOW',
            'score': 0,
            'factors': []
        }

        # New tables (medium risk)
        if comparison['new_tables']:
            risk['score'] += len(comparison['new_tables']) * 2
            risk['factors'].append(f"{len(comparison['new_tables'])} new tables")

        # Removed tables (critical risk)
        if comparison['removed_tables']:
            risk['score'] += len(comparison['removed_tables']) * 10
            risk['factors'].append(f"⚠️  {len(comparison['removed_tables'])} tables to be removed")

        # Modified tables
        for table, diff in comparison.get('table_differences', {}).items():
            if 'removed' in diff.get('column_differences', {}):
                risk['score'] += 5
                risk['factors'].append(f"⚠️  Columns removed in {table}")

            if 'modified' in diff.get('column_differences', {}):
                risk['score'] += len(diff['column_differences']['modified']) * 3
                risk['factors'].append(f"Column modifications in {table}")

        # Determine risk level
        if risk['score'] >= 20:
            risk['level'] = 'CRITICAL'
        elif risk['score'] >= 10:
            risk['level'] = 'HIGH'
        elif risk['score'] >= 5:
            risk['level'] = 'MEDIUM'

        return risk


def main():
    """Main execution function"""
    # Database connection strings
    DEV_URL = "postgresql://postgres:KfcqZpqRnRCTyvVxHKkDHjssedAjXZSp@turntable.proxy.rlwy.net:58299/railway"
    PROD_URL = "postgresql://postgres:VknAapdgHdGkHjkmsyHWsJyKCspFmqzO@gondola.proxy.rlwy.net:15456/railway"

    print("=" * 60)
    print("DATABASE SCHEMA COMPARISON TOOL")
    print("=" * 60)

    comparator = DatabaseSchemaComparator(DEV_URL, PROD_URL)

    try:
        # Connect to databases
        comparator.connect()

        # Compare schemas
        comparison = comparator.compare_schemas()

        # Assess risk
        risk = comparator.assess_risk(comparison)
        comparison['risk_assessment'] = risk

        # Generate migration SQL
        migration_sql = comparator.generate_migration_sql(comparison)

        # Save reports
        print("\n💾 Saving reports...")

        # JSON report
        json_file = "scripts/schema_comparison_report.json"
        with open(json_file, 'w') as f:
            json.dump(comparison, f, indent=2, default=str)
        print(f"  ✅ JSON report: {json_file}")

        # SQL migration script
        sql_file = "scripts/migration_dev_to_prod.sql"
        with open(sql_file, 'w') as f:
            f.write(migration_sql)
        print(f"  ✅ SQL migration: {sql_file}")

        # Print summary
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print(f"Risk Level: {risk['level']} (Score: {risk['score']})")
        print(f"\nNew Tables: {len(comparison['new_tables'])}")
        if comparison['new_tables']:
            for table in comparison['new_tables']:
                print(f"  + {table}")

        print(f"\nRemoved Tables: {len(comparison['removed_tables'])}")
        if comparison['removed_tables']:
            for table in comparison['removed_tables']:
                print(f"  - {table}")

        print(f"\nModified Tables: {len(comparison['table_differences'])}")
        for table in comparison['table_differences']:
            print(f"  ~ {table}")

        print("\n" + "=" * 60)
        print("✅ Schema comparison complete!")
        print("=" * 60)
        print(f"\nReview the migration script before executing:")
        print(f"  {sql_file}")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    finally:
        comparator.disconnect()


if __name__ == "__main__":
    main()
