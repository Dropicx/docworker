# Pipeline Early Termination System

## Overview

The pipeline termination system allows steps to gracefully stop processing based on their output values. This is useful for:
- **Rejecting non-medical content** (MEDICAL_VALIDATION step)
- **Unsupported document types** (CLASSIFICATION step)
- **Quality thresholds** (any quality validation step)
- **Business rule enforcement** (custom conditions)

## How It Works

### 1. Database Schema

```sql
-- Added to dynamic_pipeline_steps table
stop_conditions JSON DEFAULT NULL

-- Example value:
{
  "stop_on_values": ["NICHT_MEDIZINISCH"],
  "termination_reason": "Non-medical content detected",
  "termination_message": "Das hochgeladene Dokument enthält keinen medizinischen Inhalt..."
}
```

### 2. Executor Logic

After each step execution succeeds, the executor:
1. **Checks stop conditions** defined in `stop_conditions` JSON
2. **Compares output** against `stop_on_values` array
3. **Terminates gracefully** if match found
4. **Returns metadata** with termination info

### 3. Response Structure

When termination occurs, the executor returns:

```python
return (False, current_output, {
    "terminated": True,
    "termination_step": "Medical Content Validation",
    "termination_reason": "Non-medical content detected",
    "termination_message": "Das hochgeladene Dokument enthält...",
    "matched_value": "NICHT_MEDIZINISCH",
    "total_time": 2.5,
    "steps_executed": [...]
})
```

## Configuration Examples

### Example 1: Medical Validation (Current Implementation)

```python
{
    'name': 'Medical Content Validation',
    'stop_conditions': {
        'stop_on_values': ['NICHT_MEDIZINISCH'],
        'termination_reason': 'Non-medical content detected',
        'termination_message': 'Das hochgeladene Dokument enthält keinen medizinischen Inhalt. Bitte laden Sie ein medizinisches Dokument (z.B. Arztbrief, Befundbericht, Laborwerte) hoch.'
    }
}
```

### Example 2: Unsupported Document Type

```python
{
    'name': 'Document Classification',
    'stop_conditions': {
        'stop_on_values': ['RECHNUNG', 'UNKNOWN'],
        'termination_reason': 'Unsupported document type',
        'termination_message': 'Dieser Dokumenttyp wird derzeit nicht unterstützt.'
    }
}
```

### Example 3: Quality Threshold

```python
{
    'name': 'Quality Check',
    'stop_conditions': {
        'stop_on_values': ['LOW_QUALITY', 'UNREADABLE'],
        'termination_reason': 'Document quality too low',
        'termination_message': 'Die Qualität des Dokuments ist zu niedrig für eine zuverlässige Übersetzung.'
    }
}
```

## Frontend Integration

### 1. Update API Types

```typescript
// frontend/src/types/api.ts
export interface TranslationResult {
  // ... existing fields
  terminated?: boolean;
  termination_reason?: string;
  termination_message?: string;
  termination_step?: string;
  matched_value?: string;
}
```

### 2. Handle Termination in App.tsx

```typescript
const handleProcessingComplete = (result: TranslationResult) => {
  // Check if processing was terminated
  if (result.terminated) {
    setError(result.termination_message || 'Processing was stopped.');
    setAppState('error');
    return;
  }

  // Normal processing completed
  setResult(result);
  setAppState('result');
};
```

### 3. Display User-Friendly Message

The `termination_message` is already user-friendly and can be displayed directly:

```tsx
{appState === 'error' && (
  <div className="card-elevated border-warning-200">
    <h3>Verarbeitung gestoppt</h3>
    <p>{error}</p>
    <button onClick={handleReset}>Neues Dokument hochladen</button>
  </div>
)}
```

## Database Migration

Run the migration to add the `stop_conditions` column:

```bash
cd backend
python -m app.database.migrations.add_stop_conditions
```

## Updating Existing Steps

You can update existing steps via the API:

```bash
# Update Medical Validation step with stop conditions
PUT /api/pipeline/steps/{step_id}
{
  "stop_conditions": {
    "stop_on_values": ["NICHT_MEDIZINISCH"],
    "termination_reason": "Non-medical content detected",
    "termination_message": "Das hochgeladene Dokument..."
  }
}
```

## Benefits

✅ **Efficiency** - Stop processing early, save API costs
✅ **User Experience** - Clear feedback on why processing stopped
✅ **Flexibility** - Per-step configuration
✅ **Non-Breaking** - Graceful termination, not an error
✅ **Auditable** - Logged with TERMINATED status in step_executions

## Limitations

- Only checks output values (string matching)
- Case-insensitive matching only
- Matches first word of output
- No regex or complex pattern matching (yet)

## Future Enhancements

- Regex pattern matching
- Complex conditions (AND/OR logic)
- Custom validation functions
- Conditional termination based on context
- Retry with different parameters
