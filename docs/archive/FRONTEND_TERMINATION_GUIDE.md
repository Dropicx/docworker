# Frontend Integration Guide: Pipeline Termination

## Overview

This guide shows how to integrate pipeline termination handling into the React frontend.

## Step 1: Update API Types

**File:** `frontend/src/types/api.ts`

Add termination fields to the `TranslationResult` interface:

```typescript
export interface TranslationResult {
  // Existing fields
  translated_text: string;
  original_text: string;
  processing_time_seconds: number;
  confidence_score: number;
  document_type_detected?: string;
  target_language?: string;
  language_translated_text?: string;
  language_confidence_score?: number;

  // NEW: Termination fields
  terminated?: boolean;
  termination_step?: string;
  termination_reason?: string;
  termination_message?: string;
  matched_value?: string;
}
```

## Step 2: Update App.tsx Error Handling

**File:** `frontend/src/App.tsx`

### Option A: Simple Approach (Recommended)

Treat termination as a special case of error with a better UX:

```typescript
const handleProcessingComplete = (result: TranslationResult) => {
  // Check for early termination
  if (result.terminated) {
    console.log('Pipeline terminated:', result.termination_reason);
    setError(result.termination_message || 'Verarbeitung wurde gestoppt.');
    setAppState('error');
    return;
  }

  // Normal completion
  setResult(result);
  setAppState('result');
};
```

**That's it!** The existing error display will show the user-friendly termination message.

### Option B: Advanced Approach (Custom UI)

Create a separate state for termination:

```typescript
type AppState = 'upload' | 'initializing' | 'processing' | 'result' | 'error' | 'terminated';

const [terminationInfo, setTerminationInfo] = useState<{
  message: string;
  reason: string;
  step: string;
} | null>(null);

const handleProcessingComplete = (result: TranslationResult) => {
  if (result.terminated) {
    setTerminationInfo({
      message: result.termination_message || 'Verarbeitung gestoppt',
      reason: result.termination_reason || 'Unknown',
      step: result.termination_step || 'Unknown'
    });
    setAppState('terminated');
    return;
  }

  setResult(result);
  setAppState('result');
};
```

Then add custom UI:

```tsx
{/* Termination State (Custom UI) */}
{appState === 'terminated' && terminationInfo && (
  <div className="min-h-screen flex items-center justify-center p-4">
    <div className="max-w-2xl w-full">
      <div className="card-elevated border-warning-200/50 bg-gradient-to-br from-warning-50/50 to-white">
        <div className="card-body text-center">
          {/* Icon */}
          <div className="flex-shrink-0 w-16 h-16 bg-gradient-to-br from-warning-500 to-warning-600 rounded-2xl flex items-center justify-center mx-auto mb-6">
            <AlertCircle className="w-8 h-8 text-white" />
          </div>

          {/* Title */}
          <h3 className="text-2xl font-bold text-warning-900 mb-3">
            Verarbeitung gestoppt
          </h3>

          {/* User-friendly message */}
          <p className="text-warning-800 mb-6 text-lg leading-relaxed">
            {terminationInfo.message}
          </p>

          {/* Technical details (optional, can be in a collapsible) */}
          <details className="mb-6 text-left">
            <summary className="cursor-pointer text-sm text-warning-700 font-medium">
              Technische Details
            </summary>
            <div className="mt-2 text-sm text-warning-600 bg-warning-50 p-3 rounded-lg">
              <p><strong>Schritt:</strong> {terminationInfo.step}</p>
              <p><strong>Grund:</strong> {terminationInfo.reason}</p>
            </div>
          </details>

          {/* Action buttons */}
          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            <button
              onClick={handleReset}
              className="btn-primary group"
            >
              <Upload className="w-5 h-5" />
              <span>Neues Dokument hochladen</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
)}
```

## Step 3: Update ProcessingStatus (Optional)

If you want to show termination info during processing polling:

**File:** `frontend/src/components/ProcessingStatus.tsx`

```typescript
useEffect(() => {
  const checkStatus = async () => {
    try {
      const status = await ApiService.getProcessingStatus(processingId);

      // Check for termination
      if (status.status === 'TERMINATED' || status.terminated) {
        onError(status.termination_message || 'Processing was stopped.');
        return;
      }

      // ... rest of existing logic
    } catch (error: any) {
      onError(error.message);
    }
  };

  // ... rest of existing code
}, [processingId]);
```

## Step 4: Testing

### Test Case 1: Non-Medical Content

1. Upload a non-medical document (e.g., invoice, letter)
2. Pipeline should stop at "Medical Content Validation" step
3. User sees: "Das hochgeladene Dokument enthält keinen medizinischen Inhalt..."
4. Can upload new document

### Test Case 2: Medical Content (Normal Flow)

1. Upload medical document (Arztbrief)
2. Pipeline completes normally
3. User sees translation result

## Step 5: API Response Examples

### Successful Termination Response

```json
{
  "processing_id": "abc123",
  "status": "TERMINATED",
  "terminated": true,
  "termination_step": "Medical Content Validation",
  "termination_reason": "Non-medical content detected",
  "termination_message": "Das hochgeladene Dokument enthält keinen medizinischen Inhalt. Bitte laden Sie ein medizinisches Dokument (z.B. Arztbrief, Befundbericht, Laborwerte) hoch.",
  "matched_value": "NICHT_MEDIZINISCH",
  "processing_time_seconds": 2.5,
  "steps_executed": [
    {
      "step_name": "Medical Content Validation",
      "success": true,
      "terminated": true
    }
  ]
}
```

### Normal Completion Response

```json
{
  "processing_id": "abc123",
  "status": "COMPLETED",
  "translated_text": "...",
  "original_text": "...",
  "processing_time_seconds": 45.2,
  "confidence_score": 0.92,
  "document_type_detected": "ARZTBRIEF"
}
```

## Recommendation

**Use Option A (Simple Approach)** - It requires minimal code changes and reuses existing error UI. The `termination_message` is already user-friendly and can be displayed directly.

The backend already provides clear, actionable messages that users can understand.

## Code Changes Summary

Minimal changes needed:

1. ✅ Add 5 optional fields to `TranslationResult` type
2. ✅ Add 4-line check in `handleProcessingComplete`
3. ✅ (Optional) Add termination check in `ProcessingStatus` component

**Total Lines Changed:** ~10 lines
**Breaking Changes:** None (all fields are optional)
