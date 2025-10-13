# ADR 002: Extract Business Logic to Service Layer

## Status

**Accepted** - Implementation in progress

## Date

2025-10-13

## Context

Following ADR-001 (Repository Pattern), we need to extract business logic from API routers into a dedicated service layer. Currently, routers contain significant business logic, making them difficult to test and maintain.

### Current Issues

```python
# Example from app/routers/process.py (before refactoring)
@router.get("/process/pipeline-stats")
async def get_pipeline_stats(...):
    # 200+ lines of complex business logic in router
    # Database queries
    # Data transformations
    # Statistics calculations
    # All mixed with HTTP handling
```

**Problems**:
- Violates Single Responsibility Principle
- Routers do more than handle HTTP
- Business logic can't be tested independently
- Logic can't be reused in other contexts
- Hard to maintain and understand

## Decision

We will implement a **Service Layer** that sits between routers and repositories, containing all business logic.

### Architecture

```
┌───────────────────────────────────────┐
│         API Layer (Routers)           │
│  - HTTP request/response handling     │
│  - Input validation (Pydantic)        │
│  - HTTP status codes                  │
│  - Rate limiting                      │
└──────────────┬────────────────────────┘
               │ Depends on
┌──────────────▼────────────────────────┐
│       Service Layer (NEW FOCUS)       │
│  - Business logic                     │
│  - Workflow orchestration             │
│  - Business rules validation          │
│  - Coordination between repositories  │
└──────────────┬────────────────────────┘
               │ Uses
┌──────────────▼────────────────────────┐
│        Repository Layer               │
│  - Database access                    │
│  - CRUD operations                    │
└───────────────────────────────────────┘
```

### Principles

1. **Single Responsibility**
   - Each service handles one business domain
   - Services don't handle HTTP concerns
   - Services don't directly access database

2. **Dependency Injection**
   - Services injected into routers via FastAPI `Depends()`
   - Repositories injected into services
   - Makes testing easy with mocks

3. **Clear Interfaces**
   - Services have well-defined public methods
   - Return plain Python types (dict, list, etc.)
   - Raise domain exceptions (ValueError, RuntimeError)

4. **Stateless**
   - Services don't maintain state between calls
   - All dependencies passed in constructor
   - Thread-safe by design

### Implementation Example

**Service**:
```python
class ProcessingService:
    """Handles document processing business logic."""

    def __init__(self, session: Session):
        self.job_repository = PipelineJobRepository(session)

    def start_processing(self, processing_id: str, options: dict) -> dict:
        """
        Start document processing workflow.

        Business logic:
        1. Validate job exists
        2. Update job options
        3. Queue to worker
        4. Return status
        """
        # Get job via repository
        job = self.job_repository.get_by_processing_id(processing_id)
        if not job:
            raise ValueError("Job not found")

        # Business logic: update options
        job.processing_options = options
        self.session.commit()

        # Business logic: queue to worker
        task_id = self._queue_to_worker(processing_id, options)

        # Return result (plain dict)
        return {
            "processing_id": processing_id,
            "task_id": task_id,
            "status": "QUEUED"
        }

    def _queue_to_worker(self, processing_id: str, options: dict) -> str:
        """Private helper method."""
        from app.services.celery_client import enqueue_document_processing
        return enqueue_document_processing(processing_id, options=options)
```

**Router Using Service**:
```python
def get_processing_service(
    session: Session = Depends(get_session)
) -> ProcessingService:
    """Dependency injection factory for service."""
    return ProcessingService(session)

@router.post("/process/{processing_id}")
async def start_processing(
    processing_id: str,
    options: ProcessingOptions,
    service: ProcessingService = Depends(get_processing_service)
):
    """
    HTTP endpoint - only handles HTTP concerns.

    No business logic here - all delegated to service.
    """
    try:
        # Delegate to service
        result = service.start_processing(processing_id, options.dict())
        return result  # FastAPI handles JSON serialization

    except ValueError as e:
        # Map domain exception to HTTP status
        raise HTTPException(status_code=404, detail=str(e))

    except Exception as e:
        # Generic error handling
        raise HTTPException(status_code=500, detail=str(e))
```

## Consequences

### Positive

1. **Testability**
   - Can test business logic without HTTP layer
   - Can mock repositories for unit tests
   - Fast test execution
   ```python
   def test_start_processing():
       mock_repo = Mock(spec=PipelineJobRepository)
       service = ProcessingService(session, mock_repo)
       result = service.start_processing("id", {})
       assert result["status"] == "QUEUED"
   ```

2. **Reusability**
   - Business logic can be called from anywhere
   - CLI tools can use same services
   - Background tasks can use services
   - No HTTP dependency

3. **Maintainability**
   - Clear separation of concerns
   - Easy to find business logic
   - Consistent patterns across codebase

4. **Thin Routers**
   - Routers become simple HTTP adapters
   - Easy to understand
   - Less code in routers
   ```python
   # Before: 612 lines in process.py with business logic
   # After: ~100 lines just handling HTTP
   ```

### Negative

1. **More Files**
   - Additional service files to maintain
   - More imports needed

2. **Learning Curve**
   - Team needs to understand service pattern
   - Need to know where to put logic

3. **Initial Effort**
   - Requires extracting existing logic
   - Need to refactor existing code

## Implementation Plan

### Phase 1: Create Core Services ✅ **IN PROGRESS**
- ✅ Create `ProcessingService` - Document processing workflows
- [ ] Create `StatisticsService` - Pipeline statistics
- [ ] Create `AuthenticationService` - Auth logic

### Phase 2: Refactor Routers
- [ ] Refactor `process.py` to use `ProcessingService`
- [ ] Extract statistics logic to `StatisticsService`
- [ ] Update other routers

### Phase 3: Update Existing Services
- [ ] Refactor `ModularPipelineExecutor` to use repositories
- [ ] Update other services to follow pattern

### Phase 4: Testing
- [ ] Add unit tests for services
- [ ] Update router tests
- [ ] Achieve 80%+ coverage

## Service Design Guidelines

### Service Naming
- Name services after business domain: `ProcessingService`, `DocumentService`
- End with "Service" suffix
- One service per domain/feature

### Service Methods
- Public methods are the service interface
- Private methods (underscore prefix) for internal logic
- Return plain Python types (dict, list, primitives)
- Raise domain exceptions (ValueError, RuntimeError)
- Don't return HTTP responses

### Service Dependencies
- Inject repositories via constructor
- Accept Session for repository creation
- Don't create services inside services (inject them)

### Example Structure
```python
class DocumentService:
    """Service for document management operations."""

    def __init__(self, session: Session):
        self.doc_repository = DocumentRepository(session)
        self.job_repository = PipelineJobRepository(session)

    def create_document(self, file_data: bytes) -> dict:
        """Public API method."""
        # Business logic here
        pass

    def _validate_document(self, file_data: bytes) -> bool:
        """Private helper method."""
        pass
```

## Error Handling

### Service Layer
- Raise domain exceptions: `ValueError`, `RuntimeError`
- Include descriptive error messages
- Don't handle HTTP-specific errors

### Router Layer
- Catch domain exceptions
- Map to appropriate HTTP status codes
- Return proper HTTP responses
```python
try:
    result = service.do_something()
    return result
except ValueError as e:
    raise HTTPException(status_code=400, detail=str(e))
except RuntimeError as e:
    raise HTTPException(status_code=500, detail=str(e))
```

## References

- **Related Issue**: #14 (Code Organization & Architecture)
- **Related ADR**: ADR-001 (Repository Pattern)
- **Documentation**: `docs/ARCHITECTURE_ASSESSMENT.md`

## Notes

- FastAPI's dependency injection makes this pattern natural
- Services should be stateless and thread-safe
- This enables clean architecture and domain-driven design
- Follows SOLID principles, especially Single Responsibility and Dependency Inversion

---

**Authors**: Claude AI Assistant
**Reviewers**: To be determined
**Last Updated**: 2025-10-13
