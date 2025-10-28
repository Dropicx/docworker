# Type Checking Guide

This document describes the type checking setup for DocTranslator and provides guidelines for maintaining type safety.

## Overview

DocTranslator uses **MyPy** for static type checking with a gradual typing approach. The project is configured with moderate strictness that will increase over time as type coverage improves.

## Configuration

Type checking is configured in `backend/pyproject.toml`:

```toml
[tool.mypy]
python_version = "3.11"
exclude = ["migrations/", "_deprecated/", "tests/"]

# Type checking strictness
strict_optional = true
no_implicit_optional = true
warn_redundant_casts = true
warn_unused_ignores = true
warn_unused_configs = true
warn_unreachable = true
check_untyped_defs = true
implicit_reexport = true
strict_equality = true

# Error reporting
show_error_context = true
show_column_numbers = true
show_error_codes = true
pretty = true
```

### Strictness Levels by Module

Different parts of the codebase have different strictness levels:

**Strict modules** (new code):
- `app.routers.admin.*` - Admin endpoints
- `app.core.*` - Core functionality

**Moderate strictness** (existing code):
- All other modules follow base configuration

**Excluded from checking**:
- `migrations/` - Database migrations
- `_deprecated/` - Deprecated code
- `tests/` - Test files (initially)

## Running MyPy

### Locally

```bash
cd backend
python -m mypy app/ --config-file=pyproject.toml
```

### Via Pre-commit Hook

MyPy runs automatically on every commit:

```bash
# Install hooks
pre-commit install

# Run manually
pre-commit run mypy --all-files
```

### In CI/CD

MyPy runs in the GitHub Actions workflow (`.github/workflows/quality.yml`):

```yaml
- name: Run MyPy type checker
  run: |
    python -m mypy app/ --config-file=pyproject.toml
  continue-on-error: true  # Don't fail build on type errors
```

**Note**: Type checking is informational only and does not block PRs. This allows for gradual type improvement.

## Type Annotation Guidelines

### Function Signatures

Always annotate function signatures with types:

```python
# ✅ Good
def process_document(
    document_id: str,
    db: Session,
    settings: Settings
) -> dict[str, str]:
    """Process a document and return results."""
    return {"status": "completed"}

# ❌ Bad
def process_document(document_id, db, settings):
    return {"status": "completed"}
```

### Modern Type Syntax (Python 3.11+)

Use modern union syntax and built-in generics:

```python
# ✅ Good (Python 3.11+)
from typing import Any

def get_config(key: str) -> str | None:
    """Get configuration value."""
    pass

def get_items() -> list[dict[str, Any]]:
    """Get list of items."""
    pass

# ❌ Old style (deprecated)
from typing import Optional, Union, List, Dict

def get_config(key: str) -> Optional[str]:
    pass

def get_items() -> List[Dict[str, Any]]:
    pass
```

### Pydantic Models

Use Pydantic v2 field validators:

```python
from pydantic import BaseModel, field_validator

class ConfigRequest(BaseModel):
    name: str
    value: str | None = None

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v.strip():
            raise ValueError('Name cannot be empty')
        return v.strip()
```

### FastAPI Dependencies

Type annotate dependency functions:

```python
from typing import Annotated
from fastapi import Depends
from sqlalchemy.orm import Session

def get_session() -> Generator[Session, None, None]:
    """Get database session."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

# In routes
@router.get("/items")
async def get_items(
    db: Annotated[Session, Depends(get_session)]
) -> list[ItemResponse]:
    """Get all items."""
    return db.query(Item).all()
```

### Handling Third-Party Libraries

Some third-party libraries don't have type stubs. Handle these gracefully:

```python
# Option 1: Add type stubs (preferred)
# In requirements.txt:
# types-aiofiles==24.1.0.20240626

# Option 2: Configure mypy to ignore missing imports
# In pyproject.toml:
[[tool.mypy.overrides]]
module = ["celery.*", "slowapi.*"]
ignore_missing_imports = true

# Option 3: Use type: ignore with explanation
import some_untyped_library  # type: ignore[import-untyped]
```

### Type Aliases

Use type aliases for complex types:

```python
from typing import TypeAlias

# Complex types
DocumentDict: TypeAlias = dict[str, str | int | list[str]]
StepResult: TypeAlias = tuple[bool, str, dict[str, Any]]

def process_step(data: DocumentDict) -> StepResult:
    """Process a pipeline step."""
    return (True, "success", {})
```

## Common Type Issues and Solutions

### Issue: Missing Return Type

```python
# ❌ Problem
def get_user(user_id: int):
    return db.query(User).get(user_id)

# ✅ Solution
def get_user(user_id: int) -> User | None:
    return db.query(User).get(user_id)
```

### Issue: Any Type Overuse

```python
# ❌ Too generic
def process_data(data: Any) -> Any:
    return data["result"]

# ✅ More specific
def process_data(data: dict[str, str]) -> str:
    return data["result"]
```

### Issue: Untyped Function Arguments

```python
# ❌ No types
def calculate_total(items):
    return sum(item.price for item in items)

# ✅ With types
def calculate_total(items: list[Item]) -> float:
    return sum(item.price for item in items)
```

### Issue: Optional vs None Default

```python
# ❌ Implicit optional (old Pydantic v1)
def get_config(key: str, default=None):
    pass

# ✅ Explicit optional (Pydantic v2 + Python 3.11)
def get_config(key: str, default: str | None = None) -> str | None:
    pass
```

## Gradual Type Improvement Plan

### Phase 1: Core Modules (Current)
- ✅ Type all function signatures in `app.core.*`
- ✅ Type all function signatures in `app.routers.admin.*`
- ✅ Add type stubs for common libraries

### Phase 2: Service Layer (Next)
- [ ] Type all service classes in `app.services.*`
- [ ] Add return type annotations
- [ ] Remove `# type: ignore` where possible

### Phase 3: Routers (Future)
- [ ] Type all router endpoints
- [ ] Type all request/response models
- [ ] Enable stricter checking for routers

### Phase 4: Full Coverage (Long-term)
- [ ] Type all remaining modules
- [ ] Enable `disallow_untyped_defs = true` globally
- [ ] Achieve 90%+ type coverage
- [ ] Remove all `# type: ignore` comments

## Type Coverage Metrics

Track type coverage over time:

```bash
# Generate type coverage report
mypy app/ --html-report mypy-report/

# View coverage
open mypy-report/index.html
```

**Current Status** (as of Issue #24 completion):
- **Core modules**: ~80% typed
- **Admin routers**: ~90% typed
- **Service layer**: ~60% typed
- **Overall coverage**: ~65% typed

**Target**: 90% type coverage by end of 2025

## Best Practices

### DO ✅

- Always annotate public function signatures
- Use modern Python 3.11+ type syntax
- Use type aliases for complex types
- Add docstrings with type information
- Run mypy before committing
- Fix type errors before adding `# type: ignore`

### DON'T ❌

- Don't use `Any` unless absolutely necessary
- Don't ignore type errors without explanation
- Don't use old typing imports (Optional, Union, List, Dict)
- Don't leave functions untyped
- Don't skip mypy checks in CI/CD

## Resources

- [MyPy Documentation](https://mypy.readthedocs.io/)
- [Python Type Hints (PEP 484)](https://peps.python.org/pep-0484/)
- [Python 3.11 Type Hints](https://docs.python.org/3.11/library/typing.html)
- [Pydantic v2 Validators](https://docs.pydantic.dev/latest/concepts/validators/)
- [FastAPI Type Annotations](https://fastapi.tiangolo.com/python-types/)

## Getting Help

If you encounter type checking issues:

1. Check this guide for common solutions
2. Review MyPy error codes: https://mypy.readthedocs.io/en/stable/error_codes.html
3. Ask in team discussions or PR comments
4. When in doubt, add a `# type: ignore` with explanation and create a TODO

---

**Remember**: Type checking is a gradual process. Don't let perfect be the enemy of good. Add types incrementally and improve coverage over time.
