# DocTranslator Architecture

**Version:** 2.0 (Clean Architecture Refactoring)
**Last Updated:** January 2025
**Status:** Active Development

## Table of Contents

1. [Overview](#overview)
2. [Architectural Layers](#architectural-layers)
3. [Design Patterns](#design-patterns)
4. [Data Flow](#data-flow)
5. [Code Organization](#code-organization)
6. [Best Practices](#best-practices)
7. [Testing Strategy](#testing-strategy)

---

## Overview

DocTranslator follows **Clean Architecture** principles with a clear separation between HTTP handling, business logic, and data access. The architecture is designed for:

- **Maintainability**: Clear separation of concerns
- **Testability**: Easy mocking and unit testing
- **Scalability**: Independent scaling of components
- **Flexibility**: Easy to swap implementations

### Architectural Principles

1. **Dependency Inversion**: High-level modules don't depend on low-level modules
2. **Single Responsibility**: Each class has one reason to change
3. **Dependency Injection**: Dependencies provided externally
4. **Interface Segregation**: Small, focused interfaces

---

## Architectural Layers

The application is structured in three distinct layers:

```
┌──────────────────────────────────────┐
│         Router Layer (HTTP)          │  ← FastAPI Endpoints
│    app/routers/*.py                  │  ← HTTP Request/Response
└──────────────┬───────────────────────┘
               │ Depends()
               ↓
┌──────────────────────────────────────┐
│       Service Layer (Business)       │  ← Business Logic
│    app/services/*_service.py         │  ← Orchestration
└──────────────┬───────────────────────┘
               │ Constructor Injection
               ↓
┌──────────────────────────────────────┐
│      Repository Layer (Data)         │  ← Data Access
│    app/repositories/*_repository.py  │  ← Database Queries
└──────────────────────────────────────┘
```

### 1. Router Layer

**Location:** `app/routers/`

**Responsibility:** HTTP concerns only
- Route registration
- Request validation (Pydantic)
- Response formatting
- HTTP status codes
- Error handling (HTTPException)
- Authentication/Authorization

**Rules:**
- ❌ NO direct database access
- ❌ NO business logic
- ✅ Inject services via `Depends()`
- ✅ Return Pydantic models
- ✅ Handle HTTP-specific concerns only

**Example:**
```python
from fastapi import APIRouter, Depends, HTTPException
from app.core.dependencies import get_processing_service
from app.services.processing_service import ProcessingService

router = APIRouter()

@router.post("/process/{processing_id}")
async def start_processing(
    processing_id: str,
    service: ProcessingService = Depends(get_processing_service)
):
    """Router: HTTP handling only"""
    try:
        result = service.start_processing(processing_id, options)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
```

### 2. Service Layer

**Location:** `app/services/`

**Responsibility:** Business logic and orchestration
- Coordinate between repositories
- Implement business rules
- Handle transactions
- Call external services (Celery, AI APIs)
- Format return data

**Rules:**
- ✅ Use repositories for data access
- ✅ Contain all business logic
- ✅ Return plain dicts or domain objects
- ❌ NO HTTP concerns (no HTTPException)
- ❌ NO direct database queries (use repositories)

**Example:**
```python
class ProcessingService:
    def __init__(self, db: Session, job_repository: PipelineJobRepository | None = None):
        self.db = db
        self.job_repository = job_repository or PipelineJobRepository(db)

    def start_processing(self, processing_id: str, options: dict) -> dict:
        """Service: Business logic"""
        # Get job from repository
        job = self.job_repository.get_by_processing_id(processing_id)
        if not job:
            raise ValueError(f"Processing job {processing_id} not found")

        # Business logic
        job.processing_options = options
        self.db.commit()

        # Call external service
        task_id = enqueue_document_processing(processing_id, options)

        return {
            "processing_id": processing_id,
            "task_id": task_id,
            "status": "QUEUED"
        }
```

### 3. Repository Layer

**Location:** `app/repositories/`

**Responsibility:** Data access abstraction
- CRUD operations
- Specialized queries
- Database transactions
- Query optimization

**Rules:**
- ✅ Extend `BaseRepository[ModelType]`
- ✅ Use SQLAlchemy ORM
- ✅ Type-safe with generics
- ❌ NO business logic
- ❌ NO HTTP concerns

**Example:**
```python
from app.repositories.base_repository import BaseRepository
from app.database.modular_pipeline_models import PipelineJobDB

class PipelineJobRepository(BaseRepository[PipelineJobDB]):
    def __init__(self, db: Session):
        super().__init__(db, PipelineJobDB)

    def get_by_processing_id(self, processing_id: str) -> PipelineJobDB | None:
        """Repository: Data access only"""
        return self.db.query(self.model).filter_by(
            processing_id=processing_id
        ).first()

    def get_active_jobs(self) -> list[PipelineJobDB]:
        """Specialized query"""
        return self.db.query(self.model).filter_by(
            status=StepExecutionStatus.RUNNING
        ).all()
```

---

## Design Patterns

### Repository Pattern

**Purpose:** Abstract data access from business logic

**Benefits:**
- Centralized data access logic
- Easy to mock for testing
- Reusable queries across services
- Database-agnostic interface

**Implementation:**

```python
# 1. Base Repository (Generic)
class BaseRepository(Generic[ModelType]):
    def __init__(self, db: Session, model: type[ModelType]):
        self.db = db
        self.model = model

    def get(self, id: Any) -> ModelType | None:
        return self.db.query(self.model).filter(self.model.id == id).first()

    def create(self, **kwargs) -> ModelType:
        entity = self.model(**kwargs)
        self.db.add(entity)
        self.db.commit()
        self.db.refresh(entity)
        return entity

# 2. Specialized Repository
class PipelineJobRepository(BaseRepository[PipelineJobDB]):
    def get_by_processing_id(self, processing_id: str) -> PipelineJobDB | None:
        return self.db.query(self.model).filter_by(
            processing_id=processing_id
        ).first()
```

**Available Repositories:**
- `BaseRepository` - Generic CRUD operations
- `PipelineJobRepository` - Pipeline job management
- `PipelineStepRepository` - Dynamic pipeline steps
- `DocumentClassRepository` - Document classifications
- `SystemSettingsRepository` - System configuration

### Service Layer Pattern

**Purpose:** Encapsulate business logic

**Benefits:**
- Testable business logic
- Reusable across endpoints
- Transaction management
- Clear orchestration

**Implementation:**

```python
class ProcessingService:
    def __init__(
        self,
        db: Session,
        job_repository: PipelineJobRepository | None = None
    ):
        self.db = db
        self.job_repository = job_repository or PipelineJobRepository(db)

    def start_processing(self, processing_id: str, options: dict) -> dict:
        # Business logic using repository
        job = self.job_repository.get_by_processing_id(processing_id)
        # ... more logic
        return result
```

**Available Services:**
- `ProcessingService` - Document processing workflows
- `StatisticsService` - Pipeline statistics and metrics
- `AILoggingService` - AI interaction logging

### Dependency Injection Pattern

**Purpose:** Provide dependencies externally

**Benefits:**
- Easy to test (mock dependencies)
- Loose coupling
- Configuration flexibility
- Clear dependencies

**Implementation:**

```python
# 1. Define factory in app/core/dependencies.py
from fastapi import Depends

def get_processing_service(
    db: Session = Depends(get_session)
) -> ProcessingService:
    return ProcessingService(db)

# 2. Use in router
@router.post("/endpoint")
async def endpoint(
    service: ProcessingService = Depends(get_processing_service)
):
    return service.do_something()
```

---

## Data Flow

### Request Flow (Typical POST/PUT)

```
1. HTTP Request
   ↓
2. Router validates request (Pydantic)
   ↓
3. FastAPI injects dependencies
   ├─ Database session
   └─ Service instance
   ↓
4. Router calls service method
   ↓
5. Service uses repository for data access
   ↓
6. Service implements business logic
   ↓
7. Service returns plain dict
   ↓
8. Router formats HTTP response
   ↓
9. HTTP Response
```

### Example: Start Processing

```python
# 1. Request arrives
POST /process/abc123 {"target_language": "en"}

# 2. Router (HTTP layer)
@router.post("/process/{processing_id}")
async def start_processing(
    processing_id: str,
    options: ProcessingOptions,
    service: ProcessingService = Depends(get_processing_service)
):
    # 3. Delegate to service
    result = service.start_processing(processing_id, options.dict())
    return result

# 4. Service (Business layer)
class ProcessingService:
    def start_processing(self, processing_id: str, options: dict) -> dict:
        # 5. Use repository
        job = self.job_repository.get_by_processing_id(processing_id)

        # 6. Business logic
        job.processing_options = options
        self.db.commit()

        # 7. Call external service
        task_id = enqueue_document_processing(processing_id, options)

        # 8. Return data
        return {"processing_id": processing_id, "task_id": task_id}

# 9. Repository (Data layer)
class PipelineJobRepository:
    def get_by_processing_id(self, processing_id: str) -> PipelineJobDB:
        return self.db.query(self.model).filter_by(
            processing_id=processing_id
        ).first()
```

---

## Code Organization

```
backend/
├── app/
│   ├── core/
│   │   └── dependencies.py         # DI factories
│   ├── database/
│   │   ├── connection.py           # DB session management
│   │   ├── modular_pipeline_models.py
│   │   └── unified_models.py
│   ├── models/
│   │   └── document.py             # Pydantic models
│   ├── repositories/
│   │   ├── __init__.py
│   │   ├── base_repository.py      # Generic base
│   │   ├── pipeline_job_repository.py
│   │   ├── pipeline_step_repository.py
│   │   ├── document_class_repository.py
│   │   └── system_settings_repository.py
│   ├── services/
│   │   ├── processing_service.py
│   │   ├── statistics_service.py
│   │   └── ai_logging_service.py
│   └── routers/
│       ├── process.py
│       ├── modular_pipeline.py
│       └── upload.py
├── tests/
│   ├── repositories/
│   │   └── test_pipeline_job_repository.py
│   └── services/
│       └── test_processing_service.py
└── docs/
    ├── ARCHITECTURE.md             # This file
    └── ADRs/
        ├── 001-repository-pattern.md
        └── 002-service-layer-pattern.md
```

---

## Best Practices

### For Routers

```python
# ✅ DO: Keep routers thin
@router.post("/endpoint")
async def endpoint(service: Service = Depends(get_service)):
    try:
        result = service.do_work()
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

# ❌ DON'T: Put business logic in routers
@router.post("/endpoint")
async def endpoint(db: Session = Depends(get_session)):
    job = db.query(JobDB).filter_by(id=1).first()  # ❌ Direct query
    if not job:  # ❌ Business logic
        raise HTTPException(status_code=404)
    job.status = "COMPLETED"  # ❌ Business logic
    db.commit()
    return job
```

### For Services

```python
# ✅ DO: Use repositories
class ProcessingService:
    def __init__(self, db: Session):
        self.job_repository = PipelineJobRepository(db)

    def process(self, id: str):
        job = self.job_repository.get_by_processing_id(id)
        # Business logic here
        return result

# ❌ DON'T: Use direct database queries
class ProcessingService:
    def process(self, id: str):
        job = self.db.query(JobDB).filter_by(processing_id=id).first()  # ❌
```

### For Repositories

```python
# ✅ DO: Keep methods focused on data access
class JobRepository(BaseRepository[JobDB]):
    def get_active_jobs(self) -> list[JobDB]:
        return self.db.query(self.model).filter_by(
            status=Status.RUNNING
        ).all()

# ❌ DON'T: Add business logic
class JobRepository:
    def process_job(self, id: int):  # ❌ Business logic
        job = self.get(id)
        job.status = "COMPLETED"
        self.db.commit()
        return job
```

### Dependency Injection

```python
# ✅ DO: Use factories
def get_processing_service(db: Session = Depends(get_session)):
    return ProcessingService(db)

@router.post("/endpoint")
async def endpoint(service: ProcessingService = Depends(get_processing_service)):
    return service.process()

# ❌ DON'T: Create services manually
@router.post("/endpoint")
async def endpoint(db: Session = Depends(get_session)):
    service = ProcessingService(db)  # ❌ Manual creation
    return service.process()
```

---

## Testing Strategy

### Unit Tests

Test each layer independently using mocks:

```python
# Repository Tests (uses in-memory SQLite)
def test_get_by_processing_id(repository, sample_job):
    job = repository.get_by_processing_id(sample_job.processing_id)
    assert job is not None
    assert job.processing_id == sample_job.processing_id

# Service Tests (mock repositories)
def test_start_processing(mock_repository):
    service = ProcessingService(db, job_repository=mock_repository)
    mock_repository.get_by_processing_id.return_value = mock_job

    result = service.start_processing("test-123", {})

    assert result["processing_id"] == "test-123"
    mock_repository.get_by_processing_id.assert_called_once()

# Router Tests (mock services)
def test_start_processing_endpoint(client, mock_service):
    mock_service.start_processing.return_value = {"status": "QUEUED"}

    response = client.post("/process/test-123")

    assert response.status_code == 200
    assert response.json()["status"] == "QUEUED"
```

### Integration Tests

Test interactions between layers:

```python
def test_full_processing_flow(client, db):
    # Create job
    job = PipelineJobDB(processing_id="test-123", ...)
    db.add(job)
    db.commit()

    # Start processing
    response = client.post("/process/test-123")
    assert response.status_code == 200

    # Verify database state
    updated_job = db.query(PipelineJobDB).filter_by(
        processing_id="test-123"
    ).first()
    assert updated_job.status == "QUEUED"
```

### Test Pyramid

```
           ┌──────────────┐
          ╱  E2E Tests    ╲      ← Few (slow, expensive)
         ╱   (10%)        ╲
        ├──────────────────┤
       ╱ Integration Tests ╲     ← Some (medium speed)
      ╱     (30%)          ╲
     ├────────────────────────┤
    ╱    Unit Tests          ╲   ← Many (fast, cheap)
   ╱       (60%)             ╲
  └─────────────────────────────┘
```

---

## Migration Guide

### From Direct Queries to Repositories

**Before:**
```python
@router.get("/jobs/{id}")
async def get_job(id: int, db: Session = Depends(get_session)):
    job = db.query(JobDB).filter_by(id=id).first()
    if not job:
        raise HTTPException(status_code=404)
    return job
```

**After:**
```python
@router.get("/jobs/{id}")
async def get_job(
    id: int,
    service: ProcessingService = Depends(get_processing_service)
):
    try:
        job = service.get_job(id)
        return job
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
```

### Benefits Achieved

✅ **52% code reduction** in router layer
✅ **Improved testability** - easy mocking
✅ **Better maintainability** - clear separation
✅ **Reusable logic** - repositories used across services
✅ **Type safety** - generic repositories with type hints

---

## Further Reading

- [Architecture Decision Records](./ADRs/README.md)
- [ADR-001: Repository Pattern](./ADRs/001-repository-pattern.md)
- [ADR-002: Service Layer Pattern](./ADRs/002-service-layer-pattern.md)
- [Testing Guide](./TESTING.md)
- [Contributing Guide](../CONTRIBUTING.md)

---

**Document Version:** 2.0
**Last Review:** January 2025
**Next Review:** March 2025
