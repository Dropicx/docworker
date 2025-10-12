# Code Refactoring Notes

## Duplicate Services Analysis

### Text Extractors (5 implementations → Should consolidate to 1)

**Current implementations:**
1. `backend/app/services/text_extractor.py` (252 lines) - Original basic extractor
2. `backend/app/services/text_extractor_simple.py` (130 lines) - Simplified version
3. `backend/app/services/text_extractor_ocr.py` (609 lines) - With OCR support
4. `backend/app/services/text_extractor_ovh.py` (236 lines) - Using OVH Vision API
5. `backend/app/services/hybrid_text_extractor.py` (772 lines) - Combines multiple strategies

**Recommendation:**
- **Keep**: `hybrid_text_extractor.py` - Most feature-complete
- **Archive**: Others - Move to `backend/app/services/_deprecated/`
- **Future**: Create unified `TextExtractorService` with strategy pattern

**Usage analysis:**
- `process.py` router uses `text_extractor_ocr` and `text_extractor_simple`
- `hybrid_text_extractor` imports `text_extractor_ocr`
- Worker may use different extractors

**Risk**: HIGH - Core functionality, breaking changes would affect document processing

---

### Privacy Filters (4 implementations → Should consolidate to 1)

**Current implementations:**
1. `backend/app/services/privacy_filter.py` (355 lines) - Basic spaCy-based filter
2. `backend/app/services/privacy_filter_advanced.py` (562 lines) - Enhanced with context
3. `backend/app/services/optimized_privacy_filter.py` (250 lines) - Performance optimized
4. `backend/app/services/smart_privacy_filter.py` (439 lines) - AI-enhanced filtering

**Recommendation:**
- **Keep**: `smart_privacy_filter.py` or `privacy_filter_advanced.py`
- **Archive**: Others
- **Future**: Create unified `PrivacyFilterService` with configurable strategies

**Usage analysis:**
- Tests use `privacy_filter_advanced` and `privacy_filter`
- `optimized_privacy_filter` uses `privacy_filter_advanced` as fallback

**Risk**: HIGH - PII protection is critical for GDPR compliance

---

### Table Processors (2 implementations → Should consolidate to 1)

**Current implementations:**
1. `backend/app/services/table_processor.py` (317 lines) - Basic table extraction
2. `backend/app/services/improved_table_processor.py` (600 lines) - Enhanced extraction

**Recommendation:**
- **Keep**: `improved_table_processor.py`
- **Archive**: `table_processor.py`

**Risk**: MEDIUM - Table extraction is important but has fallbacks

---

## Repository Layer (✅ COMPLETED)

**Created:**
- `backend/app/repositories/base_repository.py` - Generic CRUD operations
- `backend/app/repositories/settings_repository.py` - System settings with type conversion
- `backend/app/repositories/feature_flags_repository.py` - Feature flag management
- `backend/app/repositories/__init__.py` - Clean exports

**Benefits:**
- Centralized database access logic
- Type-safe repository pattern
- Easy to test with mocks
- Consistent error handling

**Usage example:**
```python
from app.repositories import SettingsRepository
from app.database.connection import get_session

with next(get_session()) as db:
    settings_repo = SettingsRepository(db)
    max_file_size = settings_repo.get_value("max_file_size_mb", default=50)
```

---

## Next Steps (Future Refactoring)

### Phase 2 - Service Consolidation (RISKY - Separate PR)
1. Consolidate text extractors into unified service with strategy pattern
2. Consolidate privacy filters into single configurable service
3. Remove deprecated implementations
4. Update all imports throughout codebase
5. Comprehensive testing before deployment

### Phase 3 - Router Refactoring (MEDIUM RISK)
1. Extract business logic from `process.py` (1059 lines)
2. Extract logic from `process_multi_file.py` (433 lines)
3. Create dedicated service classes for each domain
4. Use repository pattern consistently
5. Implement dependency injection via FastAPI Depends

### Phase 4 - Database Model Consolidation (LOW PRIORITY)
1. Review `models.py`, `unified_models.py`, `modular_pipeline_models.py`
2. Identify overlapping/duplicate models
3. Create migration strategy
4. Consolidate carefully with database migrations

---

## Configuration Management (✅ COMPLETED)

**Implemented:**
- ✅ Centralized configuration in `backend/app/core/config.py`
- ✅ Pydantic Settings with type-safe validation
- ✅ Feature flags infrastructure
- ✅ Environment variable migration
- ✅ Backward compatibility for Railway deployment

---

## Dependency Injection (PARTIAL)

**Current state:**
- FastAPI Depends pattern used in some routers
- Not consistently applied throughout codebase
- Services create dependencies directly

**TODO:**
- Apply Depends pattern consistently
- Use repository injection in services
- Make services injectable
- Improve testability

---

## Testing Recommendations

Before consolidating services:
1. Create integration tests for each text extractor strategy
2. Create tests for each privacy filter configuration
3. Benchmark performance of different implementations
4. Test with real production documents
5. Have rollback plan ready

---

*Last updated: 2025-10-12*
*Related Issue: #14*
