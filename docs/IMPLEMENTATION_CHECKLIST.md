# Pipeline Termination - Implementation Checklist

Use this checklist to implement the pipeline termination feature step-by-step.

## ✅ Phase 1: Type System (30 min)

### Task 1.1: Update API Types

**File**: `frontend/src/types/api.ts`

**Changes**:

```typescript
// 1. Add 'terminated' to ProcessingStatus enum (line 72)
export type ProcessingStatus =
  | 'pending'
  | 'processing'
  | 'extracting_text'
  | 'translating'
  | 'language_translating'
  | 'completed'
  | 'error'
  | 'non_medical_content'
  | 'terminated';  // ADD THIS LINE

// 2. Add termination fields to TranslationResult (after line 32)
export interface TranslationResult {
  processing_id: string;
  original_text: string;
  translated_text: string;
  language_translated_text?: string;
  target_language?: string;
  document_type_detected?: string;
  confidence_score: number;
  language_confidence_score?: number;
  processing_time_seconds: number;
  timestamp: string;
  // ADD THESE FIELDS:
  terminated?: boolean;
  termination_step?: string;
  termination_reason?: string;
  termination_message?: string;
  matched_value?: string;
}

// 3. Add termination fields to ProcessingProgress (after line 19)
export interface ProcessingProgress {
  processing_id: string;
  status: ProcessingStatus;
  progress_percent: number;
  current_step: string;
  message?: string;
  error?: string;
  timestamp: string;
  // ADD THESE FIELDS:
  terminated?: boolean;
  termination_message?: string;
}
```

**Test**: Run `npm run build` - should compile without errors

---

## ✅ Phase 2: Detection Logic (45 min)

### Task 2.1: Update ProcessingStatus Component

**File**: `frontend/src/components/ProcessingStatus.tsx`

**Changes**:

```typescript
// Replace lines 38-42 with this enhanced version:

// Detect termination from multiple sources (backward compatible)
const isTerminated =
  statusResponse.status === 'terminated' ||
  statusResponse.status === 'non_medical_content' ||
  statusResponse.terminated === true;

if (isTerminated) {
  setIsPolling(false);

  // Get user-friendly message
  const terminationMessage =
    statusResponse.termination_message ||
    statusResponse.error ||
    statusResponse.message ||
    'Verarbeitung wurde gestoppt';

  // Pass structured metadata to parent
  const metadata = {
    isTermination: true,
    reason: statusResponse.termination_reason,
    step: statusResponse.termination_step || statusResponse.current_step
  };

  setError(terminationMessage);
  onError(terminationMessage, metadata);
}
```

**Test**: Console log should show termination detection

### Task 2.2: Update App.tsx State Management

**File**: `frontend/src/App.tsx`

**Option A: Simple (Recommended for MVP)**

```typescript
// 1. Add new state after line 22:
const [errorMetadata, setErrorMetadata] = useState<any>(null);

// 2. Update handleProcessingError (replace lines 119-122):
const handleProcessingError = (errorMessage: string, metadata?: any) => {
  setError(errorMessage);
  setErrorMetadata(metadata || null);
  setAppState('error');
};

// 3. Update handleProcessingComplete to check termination:
// Replace lines 106-117 with:
const handleProcessingComplete = async () => {
  if (!uploadResponse) return;

  try {
    const result = await ApiService.getProcessingResult(uploadResponse.processing_id);

    // Check if processing was terminated
    if (result.terminated) {
      const metadata = {
        isTermination: true,
        reason: result.termination_reason,
        step: result.termination_step
      };
      handleProcessingError(
        result.termination_message || 'Verarbeitung wurde gestoppt',
        metadata
      );
      return;
    }

    // Normal completion
    setTranslationResult(result);
    setAppState('result');
  } catch (error: any) {
    setError(error.message);
    setAppState('error');
  }
};
```

**Test**: State should update correctly on termination

---

## ✅ Phase 3: UI Integration (90 min)

### Task 3.1: Add TerminationCard Component

**File**: Already created at `frontend/src/components/TerminationCard.tsx`

✅ Component is ready to use

### Task 3.2: Import and Use TerminationCard in App.tsx

**File**: `frontend/src/App.tsx`

```typescript
// 1. Add import at top (after line 6):
import TerminationCard from './components/TerminationCard';

// 2. Replace error state rendering (lines 378-406) with:
{appState === 'error' && (
  <div className="animate-fade-in">
    {errorMetadata?.isTermination ? (
      <TerminationCard
        message={error || 'Verarbeitung wurde gestoppt'}
        reason={errorMetadata.reason}
        step={errorMetadata.step}
        onReset={handleNewTranslation}
      />
    ) : (
      <div className="card-elevated border-error-200/50 bg-gradient-to-br from-error-50/50 to-white">
        <div className="card-body">
          <div className="flex items-start space-x-4">
            <div className="flex-shrink-0 w-12 h-12 bg-gradient-to-br from-error-500 to-error-600 rounded-xl flex items-center justify-center">
              <AlertTriangle className="w-6 h-6 text-white" />
            </div>
            <div className="flex-1">
              <h3 className="text-xl font-bold text-error-900 mb-2">
                Verarbeitung fehlgeschlagen
              </h3>
              <p className="text-error-700 mb-6 leading-relaxed">
                {error}
              </p>
              <button
                onClick={handleNewTranslation}
                className="btn-primary"
              >
                <Sparkles className="w-4 h-4 mr-2" />
                Neuen Versuch starten
              </button>
            </div>
          </div>
        </div>
      </div>
    )}
  </div>
)}
```

**Test**: Upload non-medical doc, should see TerminationCard

---

## ✅ Phase 4: Testing & Polish (60 min)

### Task 4.1: Manual Testing Checklist

- [ ] **Test Case 1**: Upload non-medical PDF (invoice, letter)
  - Expected: TerminationCard with message "keinen medizinischen Inhalt"
  - Expected: Orange/warning colors (not red error colors)
  - Expected: Clear call-to-action button

- [ ] **Test Case 2**: Upload medical PDF (Arztbrief)
  - Expected: Normal processing and translation result
  - Expected: No regression in existing flow

- [ ] **Test Case 3**: Test on mobile (320px width)
  - Expected: Readable text, clickable buttons
  - Expected: No horizontal scroll

- [ ] **Test Case 4**: Keyboard navigation
  - Expected: Can tab to button
  - Expected: Can activate with Enter/Space

- [ ] **Test Case 5**: Screen reader
  - Expected: Message is announced
  - Expected: Button has clear label

### Task 4.2: Build Test

```bash
cd frontend
npm run build
```

- [ ] Build succeeds without errors
- [ ] No TypeScript errors
- [ ] Bundle size increase < 5KB

### Task 4.3: Accessibility Check

Use Chrome DevTools Lighthouse:

```bash
npm run dev
# Open http://localhost:5173 in Chrome
# F12 → Lighthouse → Run Accessibility Audit
```

- [ ] Score remains 100%
- [ ] No contrast issues
- [ ] No keyboard navigation issues

---

## ✅ Phase 5: Deployment (30 min)

### Task 5.1: Pre-Deployment Checklist

- [ ] All tests pass
- [ ] Code reviewed
- [ ] Documentation updated
- [ ] Changelog entry added
- [ ] No console errors in production build

### Task 5.2: Deployment Steps

```bash
# 1. Build production bundle
npm run build

# 2. Test production build locally
npm run preview

# 3. Deploy (replace with your deployment command)
# e.g., railway up, vercel deploy, etc.
```

### Task 5.3: Post-Deployment Verification

- [ ] Health check passes
- [ ] Upload works
- [ ] Termination flow works
- [ ] No errors in browser console
- [ ] No errors in server logs

---

## 🎯 Summary

**Total Files Changed**: 3 files
- `frontend/src/types/api.ts` - Type definitions
- `frontend/src/components/ProcessingStatus.tsx` - Detection logic
- `frontend/src/App.tsx` - State management and UI

**Total New Files**: 1 file
- `frontend/src/components/TerminationCard.tsx` - UI component

**Total Lines Added**: ~180 lines
**Total Lines Modified**: ~40 lines

**Estimated Time**: 4-6 hours (including testing)

---

## 📊 Success Metrics

Track these metrics before and after deployment:

| Metric | Before | Target | Actual |
|--------|--------|--------|--------|
| Avg time for invalid doc | 45s | <5s | ___ |
| Tokens wasted per invalid | ~10K | ~2K | ___ |
| User confusion (support tickets) | ___ | -50% | ___ |
| Retry rate (same doc) | ___ | <10% | ___ |
| User satisfaction | ___ | +20% | ___ |

---

## 🐛 Troubleshooting

### Issue: TypeScript errors after type changes

**Solution**:
```bash
# Clear TypeScript cache
rm -rf node_modules/.cache
npm run build
```

### Issue: TerminationCard not showing

**Debug**:
```typescript
// Add console.log in handleProcessingError
console.log('Error metadata:', errorMetadata);
console.log('Is termination:', errorMetadata?.isTermination);
```

### Issue: Styling doesn't match designs

**Check**:
- Tailwind classes are correct
- `tailwind.config.js` has warning colors defined
- CSS is being applied (inspect element in DevTools)

---

## 📝 Notes

- Keep this checklist updated as you implement
- Mark each task complete with ✅
- Add actual metrics after deployment
- Document any deviations from plan
