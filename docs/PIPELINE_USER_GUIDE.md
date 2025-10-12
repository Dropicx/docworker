# Pipeline Creation & Management Guide

**DocTranslator Settings UI - Complete User Guide**

This guide walks you through creating and managing processing pipelines in the DocTranslator settings interface.

---

## Table of Contents

1. [Overview](#overview)
2. [Accessing Pipeline Settings](#accessing-pipeline-settings)
3. [Understanding Pipeline Steps](#understanding-pipeline-steps)
4. [Creating a New Pipeline Step](#creating-a-new-pipeline-step)
5. [Editing Existing Steps](#editing-existing-steps)
6. [Pipeline Variables](#pipeline-variables)
7. [Advanced Features](#advanced-features)
8. [Common Use Cases](#common-use-cases)
9. [Best Practices](#best-practices)
10. [Troubleshooting](#troubleshooting)

---

## Overview

### What is a Pipeline?

A **pipeline** is a sequence of AI-powered processing steps that transform your medical documents from German OCR text into patient-friendly translations. Each step performs a specific task like validation, classification, translation, or quality checking.

### Default Pipeline Structure

```
┌─────────────────────────────────────────────────────────┐
│ PHASE 1: Universal Pre-Processing                      │
├─────────────────────────────────────────────────────────┤
│ 1. Medical Content Validation                          │
│ 2. Document Classification (ARZTBRIEF/BEFUNDBERICHT)  │
│ 3. PII Preprocessing (Remove personal data)           │
└─────────────────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────────────────┐
│ PHASE 2: Document-Specific Processing                  │
├─────────────────────────────────────────────────────────┤
│ 4. Patient-Friendly Translation                        │
│ 5. Medical Fact Check                                  │
│ 6. Grammar and Spelling Check                          │
└─────────────────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────────────────┐
│ PHASE 3: Universal Post-Processing                     │
├─────────────────────────────────────────────────────────┤
│ 7. Language Translation (if target language selected) │
│ 8. Final Quality Check                                │
│ 9. Text Formatting (Markdown)                         │
└─────────────────────────────────────────────────────────┘
```

---

## Accessing Pipeline Settings

### Step 1: Navigate to Settings

1. Open the DocTranslator web interface
2. Click the **⚙️ Settings** button in the header
3. Select **"Pipeline-Schritte"** (Pipeline Steps) from the left sidebar

### Step 2: View Pipeline Steps

You'll see a visual pipeline builder with:
- **Pre-Branching Steps**: Universal steps that run for all documents
- **Branching Step**: Document classification (routes to different processing paths)
- **Document-Specific Branches**: Steps specific to each document type
- **Post-Branching Steps**: Final steps that run for all documents

---

## Understanding Pipeline Steps

### Step Properties

Each pipeline step has the following properties:

| Property | Description | Example |
|----------|-------------|---------|
| **Name** | Step identifier | "Medical Content Validation" |
| **Description** | What this step does | "Validates if document contains medical content" |
| **Order** | Execution sequence | 1, 2, 3... |
| **Enabled** | Active/inactive toggle | ✅ Enabled / ❌ Disabled |
| **Prompt Template** | AI instructions with variables | "Analyze the following text: {input_text}" |
| **Selected Model** | AI model to use | Llama 3.3 70B, Mistral Nemo |
| **Temperature** | AI creativity (0.0-1.0) | 0.3 (precise), 0.7 (creative) |
| **Max Tokens** | Maximum output length | 4096 tokens |

### Step Types

#### 1. **Universal Steps** (No document_class_id)
- Run for **all documents** regardless of type
- Examples: Medical Validation, PII Preprocessing, Final Quality Check

#### 2. **Branching Steps** (is_branching_step = true)
- Determines the **document type**
- Routes processing to specific branches
- Example: Document Classification

#### 3. **Document-Specific Steps** (document_class_id set)
- Run only for **specific document types**
- Examples: Arztbrief-specific translation, Lab results formatting

#### 4. **Post-Branching Steps** (post_branching = true)
- Run **after document-specific processing**
- Apply final transformations
- Examples: Language Translation, Text Formatting

---

## Creating a New Pipeline Step

### Step-by-Step Guide

#### 1. **Click "Neuen Schritt erstellen"** (Create New Step)

#### 2. **Fill in Basic Information**

**Name** (Required)
```
Medical Fact Verification
```

**Description** (Optional but recommended)
```
Cross-checks medical facts against the original OCR text to ensure accuracy
```

**Order** (Required)
```
5
```
*This determines when the step runs. Existing steps will be reordered automatically.*

#### 3. **Configure AI Settings**

**Select Model**
- **Meta-Llama-3.3-70B-Instruct**: For complex tasks (translation, fact-checking)
- **Mistral-Nemo-Instruct-2407**: For simple tasks (classification, validation)
- **Qwen 2.5 VL 72B**: For vision/OCR tasks (slow but accurate)

**Temperature**
- **0.1-0.3**: Precise, consistent (fact-checking, grammar)
- **0.5-0.7**: Balanced (translation, simplification)
- **0.8-1.0**: Creative (not recommended for medical content)

**Max Tokens**
- **100-500**: Short outputs (classification, validation)
- **1000-2000**: Medium outputs (simplified text)
- **4000-8000**: Long outputs (full translations)

#### 4. **Write the Prompt Template**

Use variables to access data:

```
You are a medical fact-checker.

**Original OCR Text:**
{original_text}

**Simplified Version:**
{input_text}

**Task:**
1. Compare the simplified text against the original
2. Verify all medical facts (diagnoses, medications, dosages)
3. Ensure no critical information was lost
4. Return the verified text or corrections if needed

Return only the corrected text.
```

**Available Variables:**
- `{input_text}` - Output from the previous step
- `{original_text}` - Original OCR text (with PII removed)
- `{document_type}` - Document classification (ARZTBRIEF, BEFUNDBERICHT, LABORWERTE)
- `{target_language}` - User's selected target language (en, fr, es, etc.)

#### 5. **Configure Advanced Settings**

**Retry on Failure**
- ✅ **Enabled**: Automatically retry if step fails (recommended)
- Max Retries: 2-3 attempts

**Input from Previous Step**
- ✅ **Enabled**: Use output from previous step as `{input_text}` (default)
- ❌ **Disabled**: Use original OCR text as input

**Output Format**
- **text**: Plain text (default)
- **markdown**: Formatted markdown
- **json**: Structured data

#### 6. **Save the Step**

Click **"Speichern"** (Save) and your step will be added to the pipeline.

---

## Editing Existing Steps

### How to Edit

1. Click the **📝 Edit** icon next to any pipeline step
2. Modify the fields you want to change
3. Click **"Speichern"** (Save)

### Reordering Steps

1. Click the **↕️ Drag handle** icon
2. Drag the step to its new position
3. The pipeline will automatically update execution order

### Disabling Steps

1. Click the **⚙️ Settings** icon
2. Toggle **"Enabled"** to ❌ Disabled
3. Step will be skipped during processing

### Deleting Steps

1. Click the **🗑️ Delete** icon
2. Confirm deletion
3. Step is permanently removed

⚠️ **Warning:** Deleting steps cannot be undone. Consider disabling instead.

---

## Pipeline Variables

### Core Variables

#### `{input_text}` - Previous Step Output
**Type:** Dynamic (changes with each step)
**Usage:** Main processing input

```
Translate the following text to simple German:

{input_text}
```

**How it works:**
- Step 1 receives: Original OCR text
- Step 2 receives: Output from Step 1
- Step 3 receives: Output from Step 2
- And so on...

---

#### `{original_text}` - Original OCR Text
**Type:** Static (never changes)
**Usage:** Fact-checking, verification, comparisons

```
Compare the simplified version with the original:

Original:
{original_text}

Simplified:
{input_text}

Ensure no medical facts were changed.
```

**⚠️ Privacy Note:** This text has already been through PII removal, so it's safe to use with AI services.

---

#### `{target_language}` - User's Target Language
**Type:** Optional (may be null)
**Usage:** Conditional translation logic

```
{% if target_language %}
Translate the following text to {target_language}:
{% else %}
Simplify the following text in German:
{% endif %}

{input_text}
```

**Possible Values:** `en`, `fr`, `es`, `it`, `pt`, `nl`, `pl`, `de`

---

#### `{document_type}` - Document Classification
**Type:** Set after branching step
**Usage:** Document-specific instructions

```
You are processing a {document_type} document.

{% if document_type == 'LABORWERTE' %}
Focus on explaining laboratory values and reference ranges.
{% elif document_type == 'ARZTBRIEF' %}
Focus on diagnoses and treatment recommendations.
{% elif document_type == 'BEFUNDBERICHT' %}
Focus on diagnostic findings and their implications.
{% endif %}

Text to process:
{input_text}
```

**Possible Values:** `ARZTBRIEF`, `BEFUNDBERICHT`, `LABORWERTE`, custom classes

---

### Variable Examples

#### Example 1: Fact-Checking Against Original

```
**Task:** Verify medical accuracy

**Simplified Text:**
{input_text}

**Original OCR Text:**
{original_text}

**Instructions:**
1. Compare simplified against original
2. Ensure no medical facts changed
3. Check all dosages, dates, diagnoses
4. Return "VERIFIED" or list discrepancies
```

#### Example 2: Conditional Translation

```
{% if target_language %}
Translate this German medical text to {target_language}:

{input_text}

Use precise medical terminology where appropriate, but keep the patient-friendly tone.
{% else %}
The user has not selected a target language. Skip this step.
{% endif %}
```

#### Example 3: Document-Type-Specific Processing

```
Document Type: {document_type}

Original Medical Text:
{original_text}

Current Version:
{input_text}

Task: Extract key information specific to this document type.

{% if document_type == 'ARZTBRIEF' %}
Extract: Patient condition, diagnoses, treatment plan, medications, next steps
{% elif document_type == 'LABORWERTE' %}
Extract: Test names, values, reference ranges, abnormal results
{% elif document_type == 'BEFUNDBERICHT' %}
Extract: Examination type, findings, impressions, recommendations
{% endif %}
```

---

## Advanced Features

### 1. Conditional Execution (Skip Steps)

**When to use:** Skip steps when required data is missing (e.g., no target language selected)

#### How to Configure

1. Edit a pipeline step
2. Scroll to **"Bedingte Ausführung"** (Conditional Execution) section
3. Add required context variables (e.g., `target_language`)
4. Save the step

#### Example: Skip Translation if No Target Language

**Step Name:** Language Translation
**Required Context Variables:** `target_language`

**What happens:**
- ✅ If user selects target language → Step runs normally
- ⏭️ If no target language selected → Step is **skipped** (not failed)
- 📊 Execution log shows: "Step skipped - missing required variables"

#### Available Context Variables

Add these to **required context variables**:
- `target_language` - User's selected language
- `document_type` - Document classification (available after branching)
- `original_text` - Original OCR text
- Custom variables you add in code

#### UI Example

```
┌───────────────────────────────────────────────────┐
│ Bedingte Ausführung                               │
├───────────────────────────────────────────────────┤
│ Definieren Sie Kontextvariablen, die vorhanden   │
│ sein müssen, damit dieser Schritt ausgeführt     │
│ wird.                                             │
│                                                   │
│ Required Variables:                               │
│ ┌───────────────────┐ ┌─────────────────────┐   │
│ │ target_language ✕ │ │                     │   │
│ └───────────────────┘ └─────────────────────┘   │
│                                                   │
│ [target_language     ] [Hinzufügen]              │
│                                                   │
│ ⚠️ Wenn target_language erforderlich ist, wird   │
│ dieser Schritt übersprungen, wenn keine Sprache  │
│ ausgewählt wurde.                                │
└───────────────────────────────────────────────────┘
```

---

### 2. Pipeline Termination (Early Exit)

**When to use:** Stop processing when business rules are violated (e.g., non-medical content)

#### How to Configure

1. Edit a pipeline step
2. Scroll to **"Stop Conditions"** section
3. Add stop conditions configuration
4. Save the step

#### Example: Reject Non-Medical Documents

**Step Name:** Medical Content Validation
**Stop Conditions:**
```json
{
  "stop_on_values": ["NICHT_MEDIZINISCH"],
  "termination_reason": "Non-medical content detected",
  "termination_message": "Das hochgeladene Dokument enthält keinen medizinischen Inhalt. Bitte laden Sie ein medizinisches Dokument (z.B. Arztbrief, Befundbericht, Laborwerte) hoch."
}
```

**What happens:**
- ✅ If output is "MEDIZINISCH" → Continue to next step
- 🛑 If output is "NICHT_MEDIZINISCH" → **Stop pipeline immediately**
- 📨 User sees: Friendly termination message (not an error)
- 💰 Benefit: Save 80% of API costs by stopping early

#### Stop Condition Properties

| Property | Description | Example |
|----------|-------------|---------|
| **stop_on_values** | Array of output values that trigger termination | `["NICHT_MEDIZINISCH", "LOW_QUALITY"]` |
| **termination_reason** | Technical reason (for logs) | "Non-medical content detected" |
| **termination_message** | User-friendly message (shown in UI) | "Bitte laden Sie ein medizinisches Dokument hoch" |

#### Common Use Cases

**1. Reject Non-Medical Content**
```json
{
  "stop_on_values": ["NICHT_MEDIZINISCH"],
  "termination_reason": "Non-medical content",
  "termination_message": "Das Dokument enthält keinen medizinischen Inhalt."
}
```

**2. Reject Unsupported Document Types**
```json
{
  "stop_on_values": ["RECHNUNG", "UNKNOWN"],
  "termination_reason": "Unsupported document type",
  "termination_message": "Dieser Dokumenttyp wird derzeit nicht unterstützt."
}
```

**3. Reject Low-Quality Scans**
```json
{
  "stop_on_values": ["LOW_QUALITY", "UNREADABLE"],
  "termination_reason": "Document quality too low",
  "termination_message": "Die Qualität des Dokuments ist zu niedrig für eine zuverlässige Verarbeitung."
}
```

---

### 3. Document Classification & Branching

**When to use:** Route documents to different processing paths based on type

#### How It Works

1. **Pre-Branching Steps** run for all documents
2. **Branching Step** classifies the document
3. **Document-Specific Steps** run based on classification
4. **Post-Branching Steps** run for all documents

#### Setting Up Branching

**Step 1: Mark the Branching Step**

Edit the classification step and set:
- ✅ **Is Branching Step**: Enabled (Check the "Klassifizierungs-Schritt (verzweigt Pipeline)" checkbox)
- **Branching Field**: `document_type` (appears after enabling branching step)

**What is the Branching Field?**
The branching field is the name of the variable that will hold the document classification result. For example:
- If your prompt outputs "ARZTBRIEF", the system will set `document_type = "ARZTBRIEF"`
- The system uses this value to route the document to the correct processing branch
- Default: `document_type` (recommended for most cases)

**Step 2: Create Document Classes**

Go to **"Dokumentklassen"** (Document Classes) and create:
- **ARZTBRIEF** - Doctor's letters
- **BEFUNDBERICHT** - Medical reports
- **LABORWERTE** - Lab results

**Step 3: Create Document-Specific Steps**

When creating a step, select:
- **Document Class**: ARZTBRIEF (only runs for doctor's letters)
- Write prompts specific to that document type

**Step 4: Create Post-Branching Steps**

For universal final steps:
- ✅ **Post-Branching**: Enabled
- **Document Class**: None (runs for all documents)

#### Visual Example

```
┌────────────────────────────────────┐
│ Medical Validation (Universal)     │
└────────────────┬───────────────────┘
                 │
┌────────────────▼───────────────────┐
│ Classification (Branching)         │
│ Output: ARZTBRIEF, BEFUNDBERICHT   │
└────────────────┬───────────────────┘
                 │
      ┌──────────┴──────────┐
      │                     │
┌─────▼──────┐      ┌──────▼────────┐
│ ARZTBRIEF  │      │ BEFUNDBERICHT │
│ Branch     │      │ Branch        │
│            │      │               │
│ • Trans-   │      │ • Trans-      │
│   lation   │      │   lation      │
│ • Format   │      │ • Format      │
└─────┬──────┘      └──────┬────────┘
      │                     │
      └──────────┬──────────┘
                 │
┌────────────────▼───────────────────┐
│ Language Translation (Post-Branch) │
└────────────────┬───────────────────┘
                 │
┌────────────────▼───────────────────┐
│ Final Quality Check (Post-Branch)  │
└────────────────────────────────────┘
```

---

### 4. Post-Branching Steps

**When to use:** Apply final transformations that should run for ALL document types

#### How to Configure

1. Create or edit a step
2. Enable **"Post-Branching"** checkbox
3. Leave **"Document Class"** as None
4. Save the step

#### Common Post-Branching Steps

1. **Language Translation** - Translate to user's target language
2. **Final Quality Check** - Ensure completeness and accuracy
3. **Text Formatting** - Apply markdown formatting
4. **Metadata Extraction** - Extract structured data

#### Example: Language Translation (Post-Branching)

**Configuration:**
- Name: Language Translation
- Post-Branching: ✅ Enabled
- Document Class: None
- Required Context Variables: `target_language`

**Prompt:**
```
{% if target_language %}
Translate the following text EXACTLY to {target_language}:

{input_text}

Maintain medical accuracy and patient-friendly tone.
{% endif %}
```

**What happens:**
- Runs **after** all document-specific processing
- Applies to **all document types** (ARZTBRIEF, BEFUNDBERICHT, LABORWERTE)
- Skips if no target language selected (conditional execution)

---

## Common Use Cases

### Use Case 1: Add a Quality Check Step

**Goal:** Verify medical accuracy before final output

**Steps:**
1. Create new step named "Medical Accuracy Check"
2. Set order: 8 (after translation, before formatting)
3. Select model: Llama 3.3 70B
4. Set temperature: 0.3 (precise)
5. Write prompt:

```
Compare the translated text with the original medical document:

Original (German):
{original_text}

Translated Version:
{input_text}

Target Language: {target_language}

Task:
1. Verify all medical facts are accurate
2. Check that no information was lost or changed
3. Ensure all dosages, dates, and diagnoses match
4. Return the verified text or corrections

Return only the verified/corrected text.
```

6. Enable retry on failure (3 attempts)
7. Save

---

### Use Case 2: Skip Steps When No Translation Needed

**Goal:** Skip language translation step if user didn't select a target language

**Steps:**
1. Edit the "Language Translation" step
2. Scroll to **"Bedingte Ausführung"**
3. Add required variable: `target_language`
4. Save

**Result:**
- With target language → Step runs, text is translated
- Without target language → Step is skipped, processing continues

---

### Use Case 3: Reject Non-Medical Documents Early

**Goal:** Stop processing and notify user if document is not medical

**Steps:**
1. Edit "Medical Content Validation" step
2. Ensure prompt outputs either "MEDIZINISCH" or "NICHT_MEDIZINISCH"
3. Add stop conditions:

```json
{
  "stop_on_values": ["NICHT_MEDIZINISCH"],
  "termination_reason": "Non-medical content detected",
  "termination_message": "Das hochgeladene Dokument enthält keinen medizinischen Inhalt. Bitte laden Sie ein medizinisches Dokument (z.B. Arztbrief, Befundbericht, Laborwerte) hoch."
}
```

4. Save

**Result:**
- Medical document → Continue processing
- Non-medical document → Stop immediately, show friendly message
- Save 80% API costs on invalid uploads

---

### Use Case 4: Create Document-Type-Specific Formatting

**Goal:** Format lab results differently than doctor's letters

**Steps:**

**For ARZTBRIEF (Doctor's Letters):**
1. Create step: "Arztbrief Formatting"
2. Document Class: ARZTBRIEF
3. Prompt:

```
Format this doctor's letter with the following structure:

# Arztbrief Zusammenfassung

## Patienteninformation
[Extract patient info]

## Diagnosen
[Extract diagnoses]

## Behandlungsplan
[Extract treatment plan]

## Medikamente
[Extract medications]

## Nächste Schritte
[Extract follow-up]

Text:
{input_text}
```

**For LABORWERTE (Lab Results):**
1. Create step: "Lab Results Formatting"
2. Document Class: LABORWERTE
3. Prompt:

```
Format these lab results in a clear table:

# Laborwerte

| Test | Wert | Referenzbereich | Status |
|------|------|-----------------|--------|
[Extract and format all test results]

## Auffällige Werte
[List any abnormal values with explanations]

Text:
{input_text}
```

**Result:** Each document type gets formatted appropriately for its content.

---

## Best Practices

### 1. Prompt Writing

✅ **DO:**
- Be specific and clear in instructions
- Use examples when possible
- Include expected output format
- Use variables for dynamic content
- Test prompts with sample data

❌ **DON'T:**
- Write vague prompts ("improve this text")
- Assume the AI knows your context
- Use overly complex instructions
- Skip variable substitution
- Forget to handle edge cases

### 2. Model Selection

| Task Type | Recommended Model | Temperature | Max Tokens |
|-----------|------------------|-------------|------------|
| **Classification** | Mistral Nemo | 0.3 | 100 |
| **Validation** | Mistral Nemo | 0.3 | 200 |
| **Translation** | Llama 3.3 70B | 0.7 | 4096 |
| **Fact-Checking** | Llama 3.3 70B | 0.3 | 4096 |
| **Simplification** | Llama 3.3 70B | 0.7 | 4096 |
| **OCR (Vision)** | Qwen 2.5 VL 72B | 0.1 | 4096 |

### 3. Variable Usage

✅ **Always available:**
- `{input_text}` - Use for main processing
- `{original_text}` - Use for verification

⚠️ **Conditionally available:**
- `{target_language}` - Check before using
- `{document_type}` - Only after branching step

💡 **Pro Tip:** Use conditional logic with `{% if variable %}...{% endif %}`

### 4. Error Handling

✅ **Enable retry for:**
- Translation steps (may timeout)
- Complex analysis steps
- External API calls

❌ **Don't enable retry for:**
- Simple classification (fast, deterministic)
- Validation steps (should be quick)
- Steps with strict time requirements

### 5. Step Ordering

**Recommended Order:**
1. **Validation** (reject invalid documents early)
2. **Classification** (route to correct branch)
3. **PII Removal** (protect privacy)
4. **Translation/Simplification** (main processing)
5. **Fact-Checking** (verify accuracy)
6. **Quality Checks** (ensure completeness)
7. **Formatting** (final presentation)

### 6. Testing Pipeline Changes

Before deploying changes to production:

1. **Test with sample documents**
   - Medical documents (expected path)
   - Non-medical documents (termination path)
   - Edge cases (poor scans, unusual formats)

2. **Check execution logs**
   - Verify steps execute in correct order
   - Check for unexpected errors
   - Validate output quality

3. **Monitor costs**
   - Compare token usage before/after changes
   - Ensure termination works (saves costs)
   - Check for unnecessary retries

4. **Review processing times**
   - Measure end-to-end processing time
   - Identify slow steps
   - Optimize prompts if needed

---

## Troubleshooting

### Problem: Step is not executing

**Possible Causes:**
1. Step is disabled (❌)
2. Previous step failed
3. Required context variables missing
4. Stop condition triggered

**Solutions:**
- Check if step is enabled in settings
- Review execution logs for errors
- Verify required variables are available
- Check if stop condition was met

---

### Problem: Output quality is poor

**Possible Causes:**
1. Wrong model selected
2. Temperature too high/low
3. Prompt is too vague
4. Max tokens too low

**Solutions:**
- Use Llama 3.3 70B for complex tasks
- Adjust temperature (0.3 for precise, 0.7 for creative)
- Rewrite prompt with clearer instructions
- Increase max tokens if output is truncated

---

### Problem: Processing is too slow

**Possible Causes:**
1. Too many steps
2. Using slow models
3. Max tokens too high
4. Unnecessary retries

**Solutions:**
- Combine similar steps
- Use Mistral Nemo for simple tasks
- Reduce max tokens to reasonable values
- Disable retry for fast, deterministic steps

---

### Problem: Pipeline terminates unexpectedly

**Possible Causes:**
1. Stop condition triggered
2. Required variable missing
3. Branching step failed

**Solutions:**
- Check execution logs for termination reason
- Review stop conditions configuration
- Verify all required variables are set
- Check branching step output

---

### Problem: Translation is inaccurate

**Possible Causes:**
1. Not using `{original_text}` for verification
2. Temperature too high
3. Model not suitable for medical content
4. Prompt doesn't emphasize accuracy

**Solutions:**
- Add fact-checking step with `{original_text}`
- Lower temperature to 0.3-0.5
- Use Llama 3.3 70B for medical translation
- Update prompt to emphasize medical accuracy

---

### Problem: Variables not substituting

**Possible Causes:**
1. Variable name typo
2. Variable not available yet
3. Wrong syntax (use `{variable}` not `${variable}`)
4. Variable is null/empty

**Solutions:**
- Check variable spelling: `{input_text}` not `{inputText}`
- Verify step order (document_type only after branching)
- Use correct Python format string syntax: `{variable}`
- Add conditional logic: `{% if variable %}{variable}{% endif %}`

---

## Getting Help

### Documentation Resources

- **[PIPELINE_VARIABLES.md](PIPELINE_VARIABLES.md)** - Complete variable reference
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - System architecture
- **[API.md](API.md)** - API endpoints reference
- **[DATABASE.md](DATABASE.md)** - Database schema

### Support Channels

- **GitHub Issues**: Report bugs or feature requests
- **Development Team**: Contact for technical support
- **User Forum**: Community discussion and help

---

## Appendix: Quick Reference

### Available Variables

```python
{input_text}        # Output from previous step
{original_text}     # Original OCR text (PII-cleaned)
{ocr_text}          # Alias for original_text
{target_language}   # User's selected language (optional)
{document_type}     # Document classification (after branching)
```

### Model Reference

```python
# Fast, efficient (simple tasks)
"Mistral-Nemo-Instruct-2407"

# High-quality (complex tasks)
"Meta-Llama-3_3-70B-Instruct"

# Vision/OCR (slow but accurate)
"Qwen2.5-VL-72B-Instruct"
```

### Temperature Guide

```python
0.1 - 0.3  # Precise, consistent (classification, validation)
0.5 - 0.7  # Balanced (translation, simplification)
0.8 - 1.0  # Creative (NOT recommended for medical)
```

### Common Patterns

**Conditional Logic:**
```python
{% if target_language %}
  Translate to {target_language}
{% else %}
  Keep in German
{% endif %}
```

**Fact-Checking:**
```python
Original: {original_text}
Current: {input_text}
Verify accuracy...
```

**Document-Specific:**
```python
{% if document_type == 'ARZTBRIEF' %}
  Instructions for doctor's letters...
{% elif document_type == 'LABORWERTE' %}
  Instructions for lab results...
{% endif %}
```

---

**Last Updated:** January 2025
**Version:** 2.0
**Maintained by:** DocTranslator Team
