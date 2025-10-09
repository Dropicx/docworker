# Pipeline Variables & Context System

## Overview

The DocTranslator pipeline provides a **context system** that allows any pipeline step to access various data throughout the processing flow. This enables advanced use cases like fact-checking against the original text, conditional logic based on document type, and preserving data across multiple transformation steps.

## Variable Types

### 1. **Step Input/Output Variables**

| Variable | Type | Description | Availability |
|----------|------|-------------|--------------|
| `{input_text}` | string | Output from the previous pipeline step | **Every step** |

**Behavior**:
- **Overwrites** with each step's output
- Use this when you want to process the current transformed text
- Example: Step 5 receives the output from Step 4 as `{input_text}`

### 2. **Preserved Context Variables**

| Variable | Type | Description | Availability |
|----------|------|-------------|--------------|
| `{original_text}` | string | **🔒 PII-cleaned OCR text (privacy-safe)** | **Every step (never changes)** |
| `{ocr_text}` | string | Alias for `{original_text}` | **Every step (never changes)** |

**Behavior**:
- **Immutable** - remains constant throughout the entire pipeline
- Contains OCR output **after PII removal** (if enabled) - safe for AI processing
- **No sensitive data** (names, addresses, dates of birth removed by spaCy NER)
- Before any AI transformations, perfect for fact-checking and comparisons
- Perfect for fact-checking, comparisons, or re-extracting specific information

**Security Note**: ⚠️ This text has already passed through the PII removal filter, so it's safe to send to AI services and does not contain sensitive personal information.

**Added in**: `worker/tasks/document_processing.py` lines 143-147
```python
# Note: extracted_text has already been through PII removal (if enabled)
pipeline_context = options or {}
pipeline_context['original_text'] = extracted_text  # PII-cleaned OCR text (safe for AI processing)
pipeline_context['ocr_text'] = extracted_text  # Alias for clarity
```

### 3. **User-Provided Variables**

| Variable | Type | Description | Availability |
|----------|------|-------------|--------------|
| `{target_language}` | string | User's selected target language | **Every step (if provided)** |

**Possible Values**: `en`, `fr`, `es`, `it`, `pt`, `nl`, `pl`, `de`

**Example Usage**:
```
{% if target_language == 'en' %}
Translate the following text to English...
{% endif %}

{input_text}
```

### 4. **Pipeline-Generated Variables**

| Variable | Type | Description | Availability |
|----------|------|-------------|--------------|
| `{document_type}` | string | Detected document class | **After branching step** |

**Possible Values**: `ARZTBRIEF`, `BEFUNDBERICHT`, `LABORWERTE`, custom classes

**Set By**: The branching/classification step (typically Step 3)

**Example Usage**:
```
You are processing a {document_type} document.

Original medical text:
{original_text}

Simplified version:
{input_text}

Verify that the simplified version accurately represents the original medical information.
```

## Variable Access in Prompts

### Basic Variable Substitution

Variables are accessed using Python's `str.format()` syntax:

```python
prompt_template = """
Analyze the following text:

{input_text}

Compare it with the original:
{original_text}

Target language: {target_language}
"""
```

### Runtime Substitution

The pipeline executor replaces variables at runtime in `modular_pipeline_executor.py`:

```python
# Line 308-311
prompt = step.prompt_template.format(
    input_text=input_text,
    **context  # Includes original_text, ocr_text, target_language, document_type
)
```

## Common Use Cases

### 1. **Fact-Checking Against Original**

Use `{original_text}` to verify that transformed text hasn't lost critical information:

```
Task: Verify medical accuracy

Simplified text:
{input_text}

Original OCR text:
{original_text}

Instructions:
1. Compare the simplified text against the original
2. Ensure no medical facts were changed or omitted
3. Check that all dosages, dates, and diagnoses are accurate
4. Return "VERIFIED" if accurate, or list discrepancies
```

### 2. **Conditional Processing Based on Document Type**

Use `{document_type}` for type-specific instructions:

```
Document Type: {document_type}

{% if document_type == 'LABORWERTE' %}
Focus on explaining laboratory values and reference ranges.
{% elif document_type == 'ARZTBRIEF' %}
Focus on explaining diagnoses and treatment recommendations.
{% elif document_type == 'BEFUNDBERICHT' %}
Focus on explaining diagnostic findings and their implications.
{% endif %}

Text to process:
{input_text}
```

### 3. **Re-Extracting Specific Information**

Extract specific data from the original OCR text that may have been lost:

```
From the original document below, extract:
- Patient date of birth
- Document issue date
- All medication names and dosages

Original document:
{original_text}

Return as JSON.
```

### 4. **Multi-Language Handling**

Use `{target_language}` for language-specific processing:

```
{% if target_language %}
Translate the following German medical text to {target_language}:
{% else %}
Simplify the following German medical text into plain German:
{% endif %}

{input_text}
```

### 5. **Quality Assurance**

Compare multiple versions throughout the pipeline:

```
Quality Check:

Original (OCR):
{original_text}

Processed (Current):
{input_text}

Verify:
1. No information loss
2. Medical terminology preserved where necessary
3. Readability improved
4. All facts accurate

Score: 1-10 and explain issues.
```

## Implementation Details

### Context Initialization

**Location**: `worker/tasks/document_processing.py`

```python
# Lines 143-154
pipeline_start = time.time()

# Prepare context with PII-cleaned OCR text preserved
# Note: extracted_text has already been through PII removal (if enabled)
pipeline_context = options or {}
pipeline_context['original_text'] = extracted_text  # PII-cleaned OCR text (safe for AI processing)
pipeline_context['ocr_text'] = extracted_text  # Alias for clarity

# Execute pipeline (async method, need to await)
success, final_output, metadata = await_sync(
    executor.execute_pipeline(
        processing_id=processing_id,
        input_text=extracted_text,
        context=pipeline_context
    )
)
```

**Processing Order**:
1. **OCR Extraction** (line 87-93): Raw text extracted from document
2. **PII Removal** (line 105-120): Sensitive data removed with spaCy NER (if enabled)
3. **Context Creation** (line 143-147): PII-cleaned text stored as `original_text`
4. **Pipeline Execution**: All steps receive privacy-safe text

### Context Flow Through Pipeline

**Location**: `backend/app/services/modular_pipeline_executor.py`

```python
# Line 140: Context parameter with default
context = context or {}

# Line 256: Document type added after branching
context["document_type"] = branch_metadata["target_key"]

# Line 308-311: Variable substitution
prompt = step.prompt_template.format(
    input_text=input_text,
    **context  # Expands all context variables
)
```

### Data Flow Diagram

```
┌─────────────────────────────────────────────────────────┐
│ OCR Extraction                                           │
│ extracted_text = "Patient Name: John Doe, DOB: 1980..." │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ 🔒 PII Removal (spaCy NER)                              │
│ extracted_text = "Patient Name: [REDACTED], DOB: ..."  │
│ ✅ Sensitive data removed locally before AI processing │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ Context Initialization (Worker)                         │
│ context = {                                             │
│   'original_text': extracted_text,  # 🔒 PII-cleaned   │
│   'ocr_text': extracted_text,       # Alias            │
│   'target_language': 'en',          # User option      │
│ }                                                       │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ Step 1: Medical Validation                              │
│ input_text = extracted_text                            │
│ context = {...} (unchanged)                            │
│ output = "MEDIZINISCH"                                 │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ Step 2: Classification (Branching)                      │
│ input_text = "MEDIZINISCH"                             │
│ context['document_type'] = "ARZTBRIEF"  # Added!       │
│ output = "ARZTBRIEF"                                   │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ Step 3: Translation                                     │
│ input_text = "Patient Name: John..."                   │
│ context = {                                            │
│   'original_text': "Patient Name: John...",  # 🔒      │
│   'document_type': "ARZTBRIEF",                        │
│   'target_language': 'en'                              │
│ }                                                      │
│ output = "Simplified text..."                         │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ Step 4: Fact Check                                      │
│ input_text = "Simplified text..."                      │
│ context = {                                            │
│   'original_text': "Patient Name: John...",  # 🔒      │
│   'document_type': "ARZTBRIEF",                        │
│   'target_language': 'en'                              │
│ }                                                      │
│ Prompt can access BOTH original_text AND input_text!   │
└─────────────────────────────────────────────────────────┘
```

## Variable Reference Table

| Variable | Mutable? | Added When | Example Value | Use Cases |
|----------|----------|------------|---------------|-----------|
| `{input_text}` | ✅ Yes | Every step | Current transformed text | Main processing input |
| `{original_text}` | 🔒 No | Worker init (after PII removal) | "Patient Name: [REDACTED]..." | Fact-checking, comparisons (privacy-safe) |
| `{ocr_text}` | 🔒 No | Worker init (after PII removal) | Same as original_text | Alias for clarity |
| `{target_language}` | ✅ Maybe | User request | "en", "fr", "es" | Conditional translation |
| `{document_type}` | ✅ Maybe | After branching | "ARZTBRIEF", "LABORWERTE" | Type-specific logic |

## Best Practices

### ✅ DO

1. **Use `{original_text}` for verification steps**
   ```
   Compare {input_text} with {original_text} to ensure accuracy.
   ```

2. **Use `{input_text}` for transformation steps**
   ```
   Simplify the following medical text: {input_text}
   ```

3. **Provide fallbacks for optional variables**
   ```python
   target_lang = context.get('target_language', 'de')  # Default to German
   ```

4. **Document your variable usage in step descriptions**
   ```
   Description: "Fact-checks against {original_text} to prevent information loss"
   ```

### ❌ DON'T

1. **Don't assume optional variables always exist**
   ```
   # BAD: Will fail if target_language not provided
   Translate to {target_language}

   # GOOD: Provide default behavior
   {% if target_language %}
   Translate to {target_language}
   {% else %}
   Simplify in German
   {% endif %}
   ```

2. **Don't try to modify preserved context**
   ```
   # This won't work - original_text is immutable
   {original_text} = "Modified"  # ❌
   ```

3. **Don't rely on `{document_type}` before branching**
   ```
   # Step 1 (before branching): document_type doesn't exist yet
   # Step 5 (after branching): document_type available
   ```

## Adding Custom Context Variables

If you need to add new context variables, modify `worker/tasks/document_processing.py`:

```python
# Line ~145
pipeline_context = options or {}
pipeline_context['original_text'] = extracted_text
pipeline_context['ocr_text'] = extracted_text

# Add your custom variable here:
pipeline_context['custom_variable'] = your_value
pipeline_context['processing_timestamp'] = datetime.now().isoformat()
```

Then document it in the step editor UI (`frontend/src/components/settings/StepEditorModal.tsx`):

```tsx
<div>
  <code className="...">{'{custom_variable}'}</code>
  <span className="ml-2">Your description here</span>
</div>
```

## Error Handling

### Missing Variable Error

If a prompt references a variable that doesn't exist:

```python
# modular_pipeline_executor.py line 312-315
except KeyError as e:
    error = f"Missing required variable in prompt template: {e}"
    logger.error(f"❌ {error}")
    return False, "", error
```

**Solution**: Check variable availability or use conditional logic.

### Example of Safe Variable Access

```python
# In your prompt template:
Available language: {{ target_language if target_language else "German (default)" }}

Current text: {input_text}
Original text: {original_text}
```

## Testing Variables

Test your prompt templates with various contexts:

```python
# Test context
test_context = {
    'original_text': 'Sample medical text...',
    'ocr_text': 'Sample medical text...',
    'target_language': 'en',
    'document_type': 'ARZTBRIEF'
}

# Test prompt
prompt = """
Document: {document_type}
Original: {original_text}
Current: {input_text}
Target: {target_language}
"""

# Substitute
result = prompt.format(input_text='Processed text...', **test_context)
print(result)
```

## UI Documentation

The step editor modal displays available variables:

**Location**: `frontend/src/components/settings/StepEditorModal.tsx` (lines 310-330)

```tsx
<div className="mt-2 p-3 bg-brand-50 border border-brand-200 rounded-lg">
  <p className="text-xs font-semibold text-brand-900 mb-2">📝 Verfügbare Variablen:</p>
  <div className="grid grid-cols-1 gap-2 text-xs text-brand-700">
    <div>
      <code>{'{input_text}'}</code>
      <span>Ausgabe des vorherigen Schritts (wird überschrieben)</span>
    </div>
    <div>
      <code>{'{original_text}'}</code> / <code>{'{ocr_text}'}</code>
      <span>🔒 Ursprünglicher OCR-Text (bleibt immer verfügbar)</span>
    </div>
    {/* ... more variables ... */}
  </div>
</div>
```

## Related Documentation

- **[ARCHITECTURE.md](./ARCHITECTURE.md)** - Pipeline execution flow
- **[API.md](./API.md)** - Pipeline configuration endpoints
- **[DATABASE.md](./DATABASE.md)** - Pipeline step storage

---

**Version**: 1.0.0
**Last Updated**: January 2025
**Author**: DocTranslator Team
