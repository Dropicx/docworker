# Architecture Assessment - Issue #14

**Date**: 2025-10-13
**Status**: Analysis Complete
**Priority**: High - Foundation for maintainability

## Executive Summary

The DocTranslator codebase requires architectural refactoring to improve maintainability, testability, and separation of concerns. The current architecture mixes business logic with API handlers and lacks proper layering.

## Current Architecture Issues

### 1. Mixed Business Logic and API Handlers

**Problem**: Routers contain substantial business logic instead of just handling HTTP concerns.

**Example** (`app/routers/process.py` lines 256-462):
```python
@router.get("/process/pipeline-stats")
async def get_pipeline_stats(authenticated: bool = Depends(verify_session_token)):
    # 200+ lines of business logic in router
    # Complex database queries
    # Data transformation
    # Statistics calculation
```

**Impact**:
- Hard to test business logic independently
- Difficult to reuse logic across endpoints
- Violates Single Responsibility Principle

### 2. Direct Database Access from Routers

**Problem**: Routers directly access database using SQLAlchemy queries.

**Example** (`app/routers/process.py` lines 72-84):
```python
@router.post("/process/{processing_id}")
async def start_processing(..., db: Session = Depends(get_session)):
    # Direct database query in router
    job = db.query(PipelineJobDB).filter_by(processing_id=processing_id).first()
    job.processing_options = options_dict
    db.commit()
```

**Impact**:
- Tight coupling to database implementation
- Difficult to mock for testing
- No abstraction layer for data access

### 3. No Dependency Injection Pattern

**Problem**: Dependencies are created directly in code rather than injected.

**Example** (`app/routers/process.py` lines 90-91):
```python
from app.services.celery_client import enqueue_document_processing
task_id = enqueue_document_processing(processing_id, options=options_dict)
```

**Impact**:
- Hard to substitute implementations
- Difficult to test with mocks
- Tight coupling between components

### 4. Configuration Spread Across Multiple Files

**Problem**: Configuration accessed inconsistently across the codebase.

**Current State**:
- ✅ `app/core/config.py` exists (from Issue #28)
- ❌ Not consistently used throughout codebase
- ❌ Some services still use `os.getenv()` directly
- ❌ No centralized feature flag management (partially addressed)

**Example** (`app/routers/process.py` line 36):
```python
expected_token = hashlib.sha256(os.getenv("SETTINGS_ACCESS_CODE", "admin123").encode()).hexdigest()
```

### 5. Inconsistent Service Layer

**Current State**:
- ✅ Many services exist in `app/services/`
- ❌ Services have inconsistent interfaces
- ❌ Some services do too much (God classes)
- ❌ No clear service contracts/protocols

**Analysis**:
```
app/services/
├── modular_pipeline_executor.py (1000+ lines - too large)
├── hybrid_text_extractor.py
├── document_classifier.py
├── ovh_client.py
└── ... 23 more service files
```

### 6. No Repository Pattern

**Problem**: No abstraction layer between business logic and data access.

**Current Practice**:
- Direct SQLAlchemy queries scattered throughout code
- No centralized data access logic
- Difficult to change database implementation

## Proposed Architecture

### Target Architecture (Layered)

```
┌─────────────────────────────────────────────────────────────┐
│                       API Layer                              │
│  (FastAPI Routers - HTTP concerns only)                     │
│  - Request/response handling                                │
│  - Input validation (Pydantic)                              │
│  - HTTP status codes                                        │
│  - Rate limiting                                            │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│                    Service Layer                             │
│  (Business logic and orchestration)                          │
│  - Document processing workflows                             │
│  - Pipeline execution                                        │
│  - Business rules                                            │
│  - Coordination between repositories                         │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│                  Repository Layer                            │
│  (Data access abstraction)                                  │
│  - CRUD operations                                          │
│  - Query building                                           │
│  - Transaction management                                   │
│  - Database-specific logic                                  │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│                     Data Layer                               │
│  (SQLAlchemy models and database)                           │
│  - Database schema                                          │
│  - ORM models                                               │
│  - Migrations                                               │
└─────────────────────────────────────────────────────────────┘
```

### Dependency Flow

```
API Layer (Routers)
    ↓ depends on
Service Layer
    ↓ depends on
Repository Layer
    ↓ depends on
Models/Database

Configuration ←── All layers can access (read-only)
```

## Refactoring Plan

### Phase 1: Create Repository Layer (2 days)

**Tasks**:
1. Create `app/repositories/` directory
2. Create base repository class with common CRUD operations
3. Implement specific repositories:
   - `PipelineJobRepository`
   - `PipelineStepRepository`
   - `DocumentClassRepository`
   - `FeatureFlagsRepository` (already partially done)
   - `SystemSettingsRepository`

**Example Repository**:
```python
# app/repositories/base.py
from typing import Generic, TypeVar, Type, List, Optional
from sqlalchemy.orm import Session

ModelType = TypeVar("ModelType")

class BaseRepository(Generic[ModelType]):
    def __init__(self, model: Type[ModelType], session: Session):
        self.model = model
        self.session = session

    def get(self, id: int) -> Optional[ModelType]:
        return self.session.query(self.model).filter_by(id=id).first()

    def get_all(self) -> List[ModelType]:
        return self.session.query(self.model).all()

    def create(self, **kwargs) -> ModelType:
        instance = self.model(**kwargs)
        self.session.add(instance)
        self.session.commit()
        self.session.refresh(instance)
        return instance

    def update(self, id: int, **kwargs) -> Optional[ModelType]:
        instance = self.get(id)
        if not instance:
            return None
        for key, value in kwargs.items():
            setattr(instance, key, value)
        self.session.commit()
        self.session.refresh(instance)
        return instance

    def delete(self, id: int) -> bool:
        instance = self.get(id)
        if not instance:
            return False
        self.session.delete(instance)
        self.session.commit()
        return True

# app/repositories/pipeline_job_repository.py
from app.database.modular_pipeline_models import PipelineJobDB
from app.repositories.base import BaseRepository

class PipelineJobRepository(BaseRepository[PipelineJobDB]):
    def __init__(self, session: Session):
        super().__init__(PipelineJobDB, session)

    def get_by_processing_id(self, processing_id: str) -> Optional[PipelineJobDB]:
        return self.session.query(self.model).filter_by(
            processing_id=processing_id
        ).first()

    def get_active_jobs(self) -> List[PipelineJobDB]:
        return self.session.query(self.model).filter_by(
            status="RUNNING"
        ).all()
```

### Phase 2: Extract Business Logic to Services (3 days)

**Tasks**:
1. Create service interfaces/protocols
2. Refactor existing services to use repositories
3. Extract business logic from routers to services
4. Create new services where needed:
   - `ProcessingService` - Document processing workflows
   - `StatisticsService` - Pipeline statistics
   - `AuthenticationService` - Token validation

**Example Service**:
```python
# app/services/processing_service.py
from typing import Dict, Optional
from sqlalchemy.orm import Session

from app.repositories.pipeline_job_repository import PipelineJobRepository
from app.services.celery_client import enqueue_document_processing
from app.core.config import Settings

class ProcessingService:
    def __init__(
        self,
        session: Session,
        settings: Settings,
        job_repository: Optional[PipelineJobRepository] = None
    ):
        self.session = session
        self.settings = settings
        self.job_repository = job_repository or PipelineJobRepository(session)

    def start_processing(
        self,
        processing_id: str,
        options: Dict[str, any]
    ) -> Dict[str, any]:
        """Start document processing with given options."""
        # Get job from repository
        job = self.job_repository.get_by_processing_id(processing_id)
        if not job:
            raise ValueError(f"Job {processing_id} not found")

        # Update job options
        job = self.job_repository.update(
            job.id,
            processing_options=options
        )

        # Enqueue to worker
        task_id = enqueue_document_processing(processing_id, options=options)

        return {
            "message": "Processing started",
            "processing_id": processing_id,
            "status": "QUEUED",
            "task_id": task_id,
            "target_language": options.get('target_language')
        }

    def get_processing_status(self, processing_id: str) -> Dict[str, any]:
        """Get current processing status."""
        job = self.job_repository.get_by_processing_id(processing_id)
        if not job:
            raise ValueError(f"Job {processing_id} not found")

        # Map status (business logic)
        status_mapping = {
            "PENDING": "PENDING",
            "RUNNING": "PROCESSING",
            "COMPLETED": "COMPLETED",
            "FAILED": "ERROR",
            "SKIPPED": "ERROR"
        }

        return {
            "processing_id": processing_id,
            "status": status_mapping.get(job.status, "PENDING"),
            "progress_percent": job.progress_percent,
            "current_step": self._get_step_description(job),
            "error": job.error_message
        }

    def _get_step_description(self, job: PipelineJobDB) -> str:
        """Get human-readable step description (private business logic)."""
        if job.status == "RUNNING":
            return f"Processing step {job.progress_percent}%"
        elif job.status == "COMPLETED":
            return "Processing completed"
        elif job.status == "FAILED":
            return "Error in processing"
        return "Waiting for processing..."
```

### Phase 3: Refactor Routers to Use Services (2 days)

**Tasks**:
1. Refactor routers to only handle HTTP concerns
2. Inject services into routers via FastAPI dependencies
3. Remove direct database access from routers
4. Remove business logic from routers

**Example Refactored Router**:
```python
# app/routers/process.py (refactored)
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.connection import get_session
from app.services.processing_service import ProcessingService
from app.core.config import Settings, get_settings

router = APIRouter()

def get_processing_service(
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings)
) -> ProcessingService:
    """Dependency injection for ProcessingService."""
    return ProcessingService(session, settings)

@router.post("/process/{processing_id}")
async def start_processing(
    processing_id: str,
    options: ProcessingOptions,
    service: ProcessingService = Depends(get_processing_service)
):
    """Start processing for uploaded document."""
    try:
        result = service.start_processing(
            processing_id,
            options.dict()
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/process/{processing_id}/status")
async def get_processing_status(
    processing_id: str,
    service: ProcessingService = Depends(get_processing_service)
):
    """Get current processing status."""
    try:
        result = service.get_processing_status(processing_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### Phase 4: Implement Dependency Injection (1 day)

**Current State**: Using FastAPI's built-in DI (good!)

**Improvements Needed**:
- Create service factory functions
- Use FastAPI `Depends()` consistently
- Make dependencies testable

**No additional DI container needed** - FastAPI's DI is sufficient for our needs.

### Phase 5: Centralize Configuration (1 day)

**Tasks**:
1. Ensure all services use `Settings` from `app.core.config`
2. Remove direct `os.getenv()` calls
3. Update configuration documentation

**Already Partially Complete** (from Issue #28):
- ✅ `app/core/config.py` with Pydantic Settings
- ✅ Feature flags system
- ❌ Some code still uses `os.getenv()` directly

### Phase 6: Testing & Documentation (1 day)

**Tasks**:
1. Update tests for new architecture
2. Create Architecture Decision Records (ADRs)
3. Update ARCHITECTURE.md with new patterns
4. Add code examples to documentation

## File Structure After Refactoring

```
backend/app/
├── core/
│   ├── __init__.py
│   ├── config.py                    # ✅ Exists (Issue #28)
│   └── exceptions.py                # NEW - Custom exceptions
│
├── repositories/                    # NEW
│   ├── __init__.py
│   ├── base.py                      # Base repository with CRUD
│   ├── pipeline_job_repository.py
│   ├── pipeline_step_repository.py
│   ├── document_class_repository.py
│   └── system_settings_repository.py
│
├── services/
│   ├── __init__.py
│   ├── processing_service.py        # NEW - Extracted from routers
│   ├── statistics_service.py        # NEW - Extracted from routers
│   ├── authentication_service.py    # NEW - Extracted from routers
│   ├── modular_pipeline_executor.py # EXISTS - Refactor to use repositories
│   ├── document_classifier.py       # EXISTS - Refactor
│   └── ... (other existing services)
│
├── routers/
│   ├── __init__.py
│   ├── process.py                   # REFACTOR - Remove business logic
│   ├── upload.py                    # REFACTOR
│   ├── modular_pipeline.py          # REFACTOR
│   └── admin/
│       └── config.py                # ✅ Exists (Issue #28)
│
├── database/
│   ├── __init__.py
│   ├── connection.py
│   ├── models.py
│   └── ...
│
└── models/
    ├── __init__.py
    └── document.py
```

## Benefits of Refactoring

### 1. Improved Testability
- Services can be tested independently with mock repositories
- Repositories can be tested with in-memory databases
- Routers become thin HTTP adapters (easy to test)

### 2. Better Maintainability
- Clear separation of concerns
- Each layer has a single responsibility
- Changes to database don't affect business logic
- Changes to business logic don't affect API

### 3. Enhanced Reusability
- Services can be used by multiple endpoints
- Repositories eliminate duplicate database queries
- Business logic can be reused across features

### 4. Easier Onboarding
- Clear architecture makes it easier for new developers
- Consistent patterns across codebase
- Well-defined boundaries between layers

### 5. Improved Testing Speed
- Can test business logic without spinning up the API
- Can test with mock databases
- Faster unit tests

## Risks and Mitigation

### Risk 1: Large Refactoring Scope
**Mitigation**:
- Refactor incrementally (one router at a time)
- Keep old code working during transition
- Use feature flags to control rollout

### Risk 2: Breaking Changes
**Mitigation**:
- Comprehensive test coverage before refactoring
- Keep API contracts unchanged
- Internal refactoring only

### Risk 3: Team Learning Curve
**Mitigation**:
- Comprehensive documentation
- Code examples and templates
- Pair programming sessions

## Success Metrics

- ✅ All routers < 200 lines (currently some >600 lines)
- ✅ 90%+ test coverage for services
- ✅ Zero direct database queries in routers
- ✅ All services use dependency injection
- ✅ All configuration via Settings class

## Timeline

| Phase | Duration | Status |
|-------|----------|--------|
| Phase 1: Repository Layer | 2 days | Not Started |
| Phase 2: Service Refactoring | 3 days | Not Started |
| Phase 3: Router Refactoring | 2 days | Not Started |
| Phase 4: Dependency Injection | 1 day | Not Started |
| Phase 5: Configuration Centralization | 1 day | Not Started |
| Phase 6: Testing & Documentation | 1 day | Not Started |
| **Total** | **10 days** | **In Progress** |

## Next Steps

1. ✅ Complete architecture assessment (this document)
2. ⏭️ Create repository layer base classes
3. ⏭️ Implement first repository (PipelineJobRepository)
4. ⏭️ Extract first service (ProcessingService)
5. ⏭️ Refactor first router (process.py)
6. ⏭️ Repeat for remaining routers
7. ⏭️ Create ADRs
8. ⏭️ Update documentation

## Conclusion

The current architecture has grown organically and now requires systematic refactoring to support long-term maintainability. The proposed layered architecture with repositories and services will provide clear separation of concerns, improved testability, and better code organization.

**Recommendation**: Proceed with refactoring in phases, starting with the repository layer. This is a high-priority foundation improvement that will pay dividends in code quality and maintainability.

---

**Document Status**: Complete
**Next Review**: After Phase 1 completion
**Related Issues**: #14 (Code Organization & Architecture)
