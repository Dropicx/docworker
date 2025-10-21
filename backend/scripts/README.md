# Backend Utility Scripts

Reusable database inspection, diagnostic, and migration utilities for DocTranslator.

## Database Inspection Scripts

### `list_tables.py`
Lists all tables in dev and prod databases with row counts and comparison.

**Usage:**
```bash
python3 scripts/list_tables.py
```

**Output:**
- Table count per database
- Row count per table
- Tables missing in either database
- Common tables count

---

### `show_table_schema.py`
Shows detailed schema for a specific table including column types, defaults, and sample data.

**Usage:**
```bash
python3 scripts/show_table_schema.py <table_name>
```

**Example:**
```bash
python3 scripts/show_table_schema.py dynamic_pipeline_steps
```

**Output:**
- Column names, types, nullability, defaults
- First 3 rows of sample data

---

### `inspect_db_differences.py`
Performs detailed schema and data comparison between dev and prod databases.

**Usage:**
```bash
python3 scripts/inspect_db_differences.py
```

**Output:**
- Schema differences for specified tables
- Missing/extra columns
- Different column definitions
- Data comparison for configuration tables

---

## Diagnostic & Debugging Scripts

### `check_production_steps.py`
Diagnoses pipeline steps configuration and identifies issues with universal/branching steps.

**Usage:**
```bash
python3 scripts/check_production_steps.py
```

**Output:**
- All enabled pipeline steps
- Universal steps (document_class_id = NULL)
- Pre-branching universal steps
- Post-branching universal steps
- Root cause analysis for missing steps

---

### `check_schema.py`
Tests database schema queries for `dynamic_pipeline_steps` table.

**Usage:**
```bash
python3 scripts/check_schema.py
```

**Output:**
- Column names and types
- Query result counts with different boolean syntaxes
- Helps debug query issues

---

### `check_step_timestamps.py`
Checks creation and modification timestamps for pipeline steps.

**Usage:**
```bash
python3 scripts/check_step_timestamps.py
```

**Output:**
- Step creation timestamps
- Last modification times
- Useful for debugging timing issues

---

### `diagnose_steps_simple.py`
Simple diagnostic script to check production pipeline steps.

**Usage:**
```bash
python3 scripts/diagnose_steps_simple.py
```

**Output:**
- All enabled steps with details
- Quick overview of step configuration

---

## Migration & Verification Scripts

### `run_migrations.py`
Executes all pending database migrations on a target database.

**Usage:**
```bash
python3 scripts/run_migrations.py <database_url>
```

**Example:**
```bash
python3 scripts/run_migrations.py postgresql://user:pass@host:port/database
```

**Output:**
- Migration execution status
- Summary of successful/failed migrations

**Migrations run:**
- add_pii_toggle
- add_step_metadata
- add_stop_conditions
- add_post_branching
- add_required_context_variables

---

### `verify_enhanced_ocr.py`
Verifies that Enhanced OCR System components can be imported and instantiated.

**Usage:**
```bash
python3 scripts/verify_enhanced_ocr.py
```

**Output:**
- Component import verification
- Instantiation checks
- System readiness status

---

## Configuration

### Database URLs
Most scripts use hardcoded database URLs. Update these variables at the top of each file:

```python
DEV_DB_URL = "postgresql://..."
PROD_DB_URL = "postgresql://..."
DATABASE_URL = "postgresql://..."  # For single-db scripts
```

### Environment Variables
Some scripts set environment variables:
```python
os.environ['DATABASE_URL'] = 'postgresql://...'
os.environ['OVH_AI_ENDPOINTS_ACCESS_TOKEN'] = 'dummy'  # For imports
```

## Requirements

All scripts require SQLAlchemy which is already installed in the backend virtual environment:

```bash
cd /media/catchmelit/5a972e8f-2616-4a45-b03c-2d2fd85f5030/Projects/doctranslator/backend
venv/bin/python3 scripts/<script_name>.py
```

## When to Use

**Before migrations:**
- `list_tables.py` - Understand current database state
- `inspect_db_differences.py` - Identify schema/data differences

**Schema investigation:**
- `show_table_schema.py` - Inspect specific table structures
- `check_schema.py` - Debug query issues

**Pipeline debugging:**
- `check_production_steps.py` - Diagnose step configuration issues
- `diagnose_steps_simple.py` - Quick step overview
- `check_step_timestamps.py` - Debug timing problems

**Migrations:**
- `run_migrations.py` - Apply migrations to any database

**After changes:**
- All inspection scripts to verify synchronization
- `verify_enhanced_ocr.py` - Verify OCR system

## Notes

- Inspection scripts are **read-only** and safe to run anytime
- Diagnostic scripts connect to production databases (be careful)
- Migration scripts **modify data** - use with caution
- Credentials are intentionally hardcoded for dev/prod comparison
- Update database URLs before running on different environments
