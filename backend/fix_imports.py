#!/usr/bin/env python3
"""
Batch fix missing imports in Python files based on Ruff F821 errors.
This script adds missing imports for common types like Any, timedelta, Request, Header, etc.
"""

import re
from pathlib import Path
from typing import Set

def fix_file_imports(file_path: Path) -> bool:
    """Fix missing imports in a single file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content
        lines = content.split('\n')

        # Detect what imports are needed
        needs_any = re.search(r'\b(dict|list)\[.*Any.*\]|: Any\b|\bAny\b', content)
        needs_timedelta = 'timedelta' in content and 'from datetime import' in content
        needs_request = re.search(r'\brequest: Request\b|\(Request\)', content)
        needs_header = 'Header' in content and 'from fastapi import' in content

        # Find the last import line to insert new imports
        last_import_idx = -1
        typing_import_idx = -1
        datetime_import_idx = -1
        fastapi_import_idx = -1

        for i, line in enumerate(lines):
            if line.startswith('from typing import'):
                typing_import_idx = i
            if line.startswith('from datetime import'):
                datetime_import_idx = i
            if line.startswith('from fastapi import'):
                fastapi_import_idx = i
            if line.startswith(('import ', 'from ')):
                last_import_idx = i

        # Fix typing imports
        if needs_any and typing_import_idx == -1:
            # Add new typing import
            insert_idx = last_import_idx + 1
            lines.insert(insert_idx, 'from typing import Any')
            typing_import_idx = insert_idx
            last_import_idx += 1
        elif needs_any and typing_import_idx >= 0:
            # Add Any to existing typing import if not present
            if 'Any' not in lines[typing_import_idx]:
                lines[typing_import_idx] = lines[typing_import_idx].replace(
                    'from typing import ', 'from typing import Any, '
                )

        # Fix datetime imports
        if needs_timedelta and datetime_import_idx >= 0:
            if 'timedelta' not in lines[datetime_import_idx]:
                lines[datetime_import_idx] = lines[datetime_import_idx].replace(
                    'from datetime import ', 'from datetime import timedelta, '
                ).replace('datetime, timedelta', 'timedelta, datetime')  # Keep datetime first

        # Fix fastapi imports
        if (needs_request or needs_header) and fastapi_import_idx >= 0:
            imports_to_add = []
            if needs_request and 'Request' not in lines[fastapi_import_idx]:
                imports_to_add.append('Request')
            if needs_header and 'Header' not in lines[fastapi_import_idx]:
                imports_to_add.append('Header')

            if imports_to_add:
                # Add to existing fastapi import
                if '(' in lines[fastapi_import_idx]:
                    # Multi-line import
                    lines[fastapi_import_idx] = lines[fastapi_import_idx].replace(
                        'from fastapi import (',
                        f"from fastapi import ({', '.join(imports_to_add)}, "
                    )
                else:
                    # Single line import
                    lines[fastapi_import_idx] = lines[fastapi_import_idx].replace(
                        'from fastapi import ',
                        f"from fastapi import {', '.join(imports_to_add)}, "
                    )

        # Fix invalid "from e" in non-except blocks (remove them)
        content = '\n'.join(lines)
        # Remove "from e" that appears at end of raise statements not in except blocks
        content = re.sub(r'(\s+)(detail=.*)\) from e$', r'\1\2)', content, flags=re.MULTILINE)

        # Only write if changed
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✓ Fixed: {file_path}")
            return True
        else:
            return False

    except Exception as e:
        print(f"✗ Error fixing {file_path}: {e}")
        return False

def main():
    """Fix imports in all Python files under app/."""
    backend_dir = Path(__file__).parent
    app_dir = backend_dir / 'app'

    # Target directories
    directories = ['routers', 'services', 'repositories', 'models']

    fixed_count = 0
    for dir_name in directories:
        dir_path = app_dir / dir_name
        if not dir_path.exists():
            continue

        py_files = list(dir_path.rglob('*.py'))
        print(f"\n📁 Fixing {dir_name}/ ({len(py_files)} files)...")

        for py_file in py_files:
            if fix_file_imports(py_file):
                fixed_count += 1

    print(f"\n✅ Fixed {fixed_count} files")

if __name__ == '__main__':
    main()
