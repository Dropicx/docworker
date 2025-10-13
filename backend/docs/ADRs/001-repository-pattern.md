# ADR 001: Implement Repository Pattern for Database Access

## Status

**Accepted** - Implementation in progress (Phase 1 complete)

## Date

2025-10-13

## Context

The DocTranslator codebase has grown organically with database access logic scattered throughout routers and services. This creates several issues:

1. **Tight Coupling**: Routers directly use SQLAlchemy queries, coupling HTTP layer to database implementation
2. **Code Duplication**: Similar database queries repeated across multiple files
3. **Testing Difficulty**: Hard to test business logic without setting up full database
4. **Maintenance Burden**: Database schema changes require updates in many places
5. **No Abstraction**: Direct database access makes it difficult to change ORM or database

### Current Issues

```python
# Example from app/routers/process.py (before refactoring)
@router.post("/process/{processing_id}")
async def start_processing(processing_id: str, db: Session = Depends(get_session)):
    # Direct database access in router
    job = db.query(PipelineJobDB).filter_by(processing_id=processing_id).first()
    job.processing_options = options_dict
    db.commit()
```

**Problems**:
- Business logic mixed with HTTP handling
- Direct SQLAlchemy usage in router
- Hard to test without database
- Violates separation of concerns

## Decision

We will implement the **Repository Pattern** to abstract database access operations.

### Architecture

```
API Layer (Routers)
    ↓ uses
Service Layer (Business Logic)
    ↓ uses
Repository Layer (Data Access) ← NEW
    ↓ uses
Database Layer (SQLAlchemy Models)
```

### Key Components

1. **Base Repository** (`app/repositories/base.py`)
   - Generic base class with common CRUD operations
   - Type-safe using Python generics
   - Reusable across all models

2. **Specific Repositories** (e.g., `PipelineJobRepository`)
   - Extend base repository
   - Add model-specific query methods
   - Encapsulate complex database logic

3. **Service Layer** (e.g., `ProcessingService`)
   - Use repositories for data access
   - Contain business logic
   - Coordinate between repositories and external services

### Implementation Example

**Base Repository**:
```python
class BaseRepository(Generic[ModelType]):
    def __init__(self, model: type[ModelType], session: Session):
        self.model = model
        self.session = session

    def get(self, id: int) -> ModelType | None:
        return self.session.query(self.model).filter_by(id=id).first()

    def create(self, **kwargs) -> ModelType:
        instance = self.model(**kwargs)
        self.session.add(instance)
        self.session.commit()
        return instance
    # ... more CRUD methods
```

**Specific Repository**:
```python
class PipelineJobRepository(BaseRepository[PipelineJobDB]):
    def __init__(self, session: Session):
        super().__init__(PipelineJobDB, session)

    def get_by_processing_id(self, processing_id: str) -> PipelineJobDB | None:
        return self.session.query(self.model).filter_by(
            processing_id=processing_id
        ).first()

    def get_active_jobs(self) -> list[PipelineJobDB]:
        return self.session.query(self.model).filter_by(
            status=StepExecutionStatus.RUNNING
        ).all()
```

**Service Using Repository**:
```python
class ProcessingService:
    def __init__(self, session: Session):
        self.job_repository = PipelineJobRepository(session)

    def start_processing(self, processing_id: str, options: dict) -> dict:
        # Use repository instead of direct database access
        job = self.job_repository.get_by_processing_id(processing_id)
        if not job:
            raise ValueError("Job not found")
        # ... business logic
```

**Router Using Service**:
```python
@router.post("/process/{processing_id}")
async def start_processing(
    processing_id: str,
    service: ProcessingService = Depends(get_processing_service)
):
    try:
        result = service.start_processing(processing_id, options)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
```

## Consequences

### Positive

1. **Separation of Concerns**
   - Clear boundaries between layers
   - Routers only handle HTTP
   - Services contain business logic
   - Repositories handle data access

2. **Improved Testability**
   - Can test business logic with mock repositories
   - Don't need database for unit tests
   - Faster test execution

3. **Code Reusability**
   - Common queries defined once in repository
   - Can be reused across services
   - Reduces code duplication

4. **Maintainability**
   - Database changes localized to repositories
   - Easier to understand code structure
   - Clear patterns for new developers

5. **Flexibility**
   - Easy to switch database implementations
   - Can add caching at repository level
   - Can implement read replicas

### Negative

1. **More Abstraction**
   - Additional layer adds complexity
   - More files to maintain
   - Steeper learning curve

2. **Initial Effort**
   - Requires refactoring existing code
   - Migration period with mixed patterns
   - Team needs to learn new pattern

3. **Potential Over-Engineering**
   - Simple CRUD operations now have more layers
   - Could be overkill for very simple queries

## Implementation Plan

### Phase 1: Foundation ✅ **COMPLETE**
- ✅ Create `app/repositories/` directory
- ✅ Implement `BaseRepository` with generic CRUD operations
- ✅ Create first repository: `PipelineJobRepository`
- ✅ Create first service: `ProcessingService`

### Phase 2: Expand Repositories (Next)
- [ ] Create `PipelineStepRepository`
- [ ] Create `DocumentClassRepository`
- [ ] Create `SystemSettingsRepository`
- [ ] Update `FeatureFlagsRepository` to extend BaseRepository

### Phase 3: Refactor Services
- [ ] Update existing services to use repositories
- [ ] Remove direct database queries from services
- [ ] Add dependency injection for repositories

### Phase 4: Refactor Routers
- [ ] Update `process.py` to use `ProcessingService`
- [ ] Update `modular_pipeline.py` to use services
- [ ] Update other routers
- [ ] Remove all direct database access from routers

### Phase 5: Testing
- [ ] Add unit tests for repositories
- [ ] Add unit tests for services with mock repositories
- [ ] Update integration tests
- [ ] Verify test coverage

## References

- **Related Issue**: #14 (Code Organization & Architecture)
- **Related ADR**: None (first ADR)
- **Documentation**: `docs/ARCHITECTURE_ASSESSMENT.md`

## Notes

- This is the first step in a larger architectural refactoring
- Pattern chosen is consistent with industry best practices (DDD, Clean Architecture)
- FastAPI's dependency injection makes this pattern natural to implement
- Gradual migration allows us to refactor incrementally without breaking changes

---

**Authors**: Claude AI Assistant
**Reviewers**: To be determined
**Last Updated**: 2025-10-13
