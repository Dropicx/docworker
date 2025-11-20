-- Migration: Remove LLM-based PII Preprocessing Step
-- Purpose: Replace LLM-based PII removal with local spaCy AdvancedPrivacyFilter
-- Date: 2025-11-20
-- Related Issue: #35 - Improve spaCy PII Removal System

-- IMPORTANT: This migration is for existing databases only.
-- New installations will use the updated modular_pipeline_seed.py file.

BEGIN;

-- Step 1: Delete the LLM-based "PII Preprocessing" step (order 3)
DELETE FROM dynamic_pipeline_steps
WHERE name = 'PII Preprocessing'
AND "order" = 3
AND document_class_id IS NULL;

-- Step 2: Renumber subsequent steps (shift orders 4-9 down to 3-8)
UPDATE dynamic_pipeline_steps
SET "order" = "order" - 1,
    last_modified = CURRENT_TIMESTAMP,
    modified_by = 'migration_remove_llm_pii'
WHERE document_class_id IS NULL  -- Only universal steps
AND "order" >= 4                 -- Steps after PII Preprocessing
AND "order" <= 9;                -- Up to Text Formatting

-- Step 3: Verify the new pipeline order
-- Expected result: Steps 1-8 (Medical Validation, Classification, Patient-Friendly Translation,
-- Fact Check, Grammar Check, Language Translation, Quality Check, Formatting)

COMMIT;

-- Verification queries (run after migration):
-- SELECT id, name, "order", enabled FROM dynamic_pipeline_steps WHERE document_class_id IS NULL ORDER BY "order";
-- Expected output:
-- Order 1: Medical Content Validation
-- Order 2: Document Classification
-- Order 3: Patient-Friendly Translation (was 4)
-- Order 4: Medical Fact Check (was 5)
-- Order 5: Grammar and Spelling Check (was 6)
-- Order 6: Language Translation (was 7)
-- Order 7: Final Quality Check (was 8)
-- Order 8: Text Formatting (was 9)
