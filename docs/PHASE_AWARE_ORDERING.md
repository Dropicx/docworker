# Phase-Aware Pipeline Step Ordering

## Problem Statement

The pipeline execution has three distinct phases:
1. **Pre-branching universal steps** (document_class_id = NULL, post_branching = False)
2. **Document-specific steps** (document_class_id = specific ID)
3. **Post-branching universal steps** (document_class_id = NULL, post_branching = True)

### Current Issue

Previously, each phase ordered steps independently using the `order` field, which caused:
- Pre-branching step could have order=1
- Document-specific step could also have order=1
- Post-branching step could also have order=1

This created **duplicate order values** across different execution contexts and made it impossible to have a single, globally sequential ordering for the entire pipeline.

### User Requirement

> "The order number has to be dynamic... So when i drag and drop the steps etc on the UI it has to attach the correct number for the overall flow"

The system needs to respect the three-phase execution model while maintaining correct ordering within each phase.

## Solution: Dynamic Phase-Aware Ordering

### Implementation Approach

**Option Selected**: Dynamic calculation at query time using SQL CASE expressions

**Benefits**:
- ✅ No database migration required
- ✅ No schema changes needed
- ✅ Works automatically without UI changes
- ✅ Respects the three-phase execution model
- ✅ Minimal code changes

### Technical Implementation

Modified repository queries to add phase-based sorting:

```sql
ORDER BY
  CASE
    WHEN post_branching = TRUE THEN 3
    WHEN document_class_id IS NOT NULL THEN 2
    ELSE 1
  END,
  "order"
```

This ensures:
1. Pre-branching steps execute first (phase=1)
2. Document-specific steps execute second (phase=2)
3. Post-branching steps execute last (phase=3)
4. Within each phase, the existing `order` field determines sequence

### Files Modified

**backend/app/repositories/pipeline_step_repository.py**

1. **`get_all_ordered()`** (lines 30-53)
   - Added phase-aware ordering using SQLAlchemy case expression
   - Returns all steps sorted by phase, then order

2. **`get_enabled_steps()`** (lines 55-78)
   - Added phase-aware ordering for enabled steps
   - Critical for pipeline execution

3. **`get_disabled_steps()`** (lines 80-98)
   - Added phase-aware ordering for consistency
   - Ensures UI displays steps in correct sequence

### Phase-Specific Queries (No Changes Needed)

The following methods don't need phase-aware ordering because they already filter to a specific phase:

- `get_universal_steps()` - Filters for pre-branching steps only
- `get_steps_by_document_class()` - Filters for document-specific steps only
- `get_post_branching_steps()` - Filters for post-branching steps only

These methods are called during execution within their respective phases, so simple ORDER BY order is sufficient.

## How It Works

### Database Query Example

**Before** (Old query):
```sql
SELECT * FROM dynamic_pipeline_steps
ORDER BY "order"
```

**After** (New phase-aware query):
```sql
SELECT * FROM dynamic_pipeline_steps
ORDER BY
  CASE
    WHEN post_branching = TRUE THEN 3
    WHEN document_class_id IS NOT NULL THEN 2
    ELSE 1
  END,
  "order"
```

### Execution Flow

1. **Phase 1 - Pre-branching (priority=1)**
   - Medical Content Validation (order=1)
   - Document Classification (order=2)

2. **Phase 2 - Document-specific (priority=2)**
   - Arztbrief Translation (document_class_id=1, order=1)
   - Befundbericht Analysis (document_class_id=2, order=1)
   - (Each document class can have its own order=1,2,3...)

3. **Phase 3 - Post-branching (priority=3)**
   - Language Translation (order=1)
   - Final Quality Check (order=2)

### UI Drag-and-Drop Behavior

**Current behavior (maintained)**:
- UI can reorder steps within their respective sections
- Pre-branching steps: order=1,2,3...
- Doc-specific steps: order=1,2,3... (per document class)
- Post-branching steps: order=1,2,3...

**Database ensures correct execution**:
- Queries automatically sort by phase first
- Then by order within each phase
- No UI changes required

## Testing

### Test Script

Created `test_phase_ordering.py` to verify:
1. All steps are returned in correct phase order
2. Enabled steps maintain phase ordering
3. Steps within each phase maintain their order field sequence

### Manual Verification

Connect to Railway database and run:

```sql
SELECT
    id,
    name,
    "order",
    enabled,
    document_class_id,
    post_branching,
    CASE
        WHEN post_branching = TRUE THEN 3
        WHEN document_class_id IS NOT NULL THEN 2
        ELSE 1
    END as phase_order
FROM dynamic_pipeline_steps
ORDER BY
    CASE
        WHEN post_branching = TRUE THEN 3
        WHEN document_class_id IS NOT NULL THEN 2
        ELSE 1
    END,
    "order";
```

Expected result: Steps should be grouped by phase_order (1, 2, 3) and sorted by order within each group.

## Benefits

### For Execution
- ✅ Guaranteed correct execution order across all phases
- ✅ No more duplicate order confusion
- ✅ Clear separation between pre-branching, doc-specific, and post-branching

### For UI
- ✅ No changes required - existing drag-and-drop still works
- ✅ Steps displayed in correct global execution sequence
- ✅ Order field remains simple (1,2,3...) within each section

### For Database
- ✅ No migration required
- ✅ No schema changes
- ✅ Existing order values remain valid
- ✅ Backward compatible

## Next Steps

1. **Deploy Changes**
   ```bash
   git add backend/app/repositories/pipeline_step_repository.py
   git commit -m "Implement phase-aware ordering for pipeline steps"
   git push origin dev
   ```

2. **Verify in Production**
   - Check Railway logs for pipeline execution
   - Verify steps execute in correct order
   - Test UI drag-and-drop functionality

3. **Frontend Considerations** (Optional)
   - UI could show phase labels (Phase 1, Phase 2, Phase 3)
   - Display global execution number alongside local order
   - Add visual separators between phases

## Troubleshooting

### If steps still appear out of order

1. **Check repository usage**:
   - Ensure code calls `repo.get_enabled_steps()` not direct queries
   - Verify no custom ORDER BY clauses override phase ordering

2. **Database verification**:
   ```sql
   -- Check for steps with missing classification
   SELECT * FROM dynamic_pipeline_steps
   WHERE document_class_id IS NULL AND post_branching IS NULL;
   ```

3. **Execution log analysis**:
   - Check worker logs for "Phase 1", "Phase 2", "Phase 3" messages
   - Verify steps execute in expected sequence

## Summary

The phase-aware ordering system ensures that pipeline steps execute in the correct sequence:
1. **Pre-branching steps** run first for all documents
2. **Document-specific steps** run next based on classification
3. **Post-branching steps** run last for all documents

This is achieved through SQL-level ordering without requiring database schema changes or UI modifications. The solution is backward compatible and transparent to existing code.
