# Privacy Filter Documentation

GDPR-compliant PII removal system for German medical documents.

## Overview

The `AdvancedPrivacyFilter` removes personally identifiable information (PII) from German medical documents while preserving all medical content. It uses a hybrid approach combining:

- **Regex patterns** for structured PII (dates, addresses, phone numbers)
- **spaCy NER** for intelligent name detection
- **Medical term protection** to prevent false positives

## Architecture

```
Input Document
       │
       ▼
┌──────────────────────┐
│  Medical Term        │  Protect 300+ medical terms, 120+ drugs
│  Protection          │  ICD-10, OPS, LOINC codes
└──────────────────────┘
       │
       ▼
┌──────────────────────┐
│  Pattern-Based       │  Regex removal of 17+ PII types
│  PII Removal         │  (dates, addresses, phones, etc.)
└──────────────────────┘
       │
       ▼
┌──────────────────────┐
│  NER-Based           │  spaCy de_core_news_sm model
│  Name Detection      │  Context-aware name removal
└──────────────────────┘
       │
       ▼
┌──────────────────────┐
│  Medical Term        │  Restore protected terms
│  Restoration         │  Preserve medical content
└──────────────────────┘
       │
       ▼
Output (PII-Free)
```

## PII Types Detected

The filter detects and removes **17+ PII types**:

| Type | Pattern | Replacement |
|------|---------|-------------|
| `birthdate` | Geb.: DD.MM.YYYY | `[GEBURTSDATUM ENTFERNT]` |
| `patient_name` | Patient: Name | `[NAME ENTFERNT]` |
| `street_address` | Straße + Number | `[ADRESSE ENTFERNT]` |
| `postal_code_city` | PLZ + City | `[PLZ/ORT ENTFERNT]` |
| `phone_number` | +49 XXX XXXX | `[TELEFON ENTFERNT]` |
| `mobile_phone` | 0151/0152/0160... | `[MOBILTELEFON ENTFERNT]` |
| `fax_number` | Fax: XXX | `[FAX ENTFERNT]` |
| `email_address` | user@domain.de | `[EMAIL ENTFERNT]` |
| `insurance_number` | A123456789 | `[NUMMER ENTFERNT]` |
| `insurance_policy` | Versichertennr. | `[VERSICHERTENNUMMER ENTFERNT]` |
| `patient_id` | Patienten-ID | `[PATIENTEN-ID ENTFERNT]` |
| `hospital_id` | Krankenhaus-Nr. | `[KRANKENHAUS-NR ENTFERNT]` |
| `tax_id` | Steuer-ID (11 digits) | `[STEUER-ID ENTFERNT]` |
| `social_security` | Sozialversicherung | `[SOZIALVERSICHERUNGSNUMMER ENTFERNT]` |
| `passport` | Reisepass C... | `[REISEPASSNUMMER ENTFERNT]` |
| `id_card` | Personalausweis | `[PERSONALAUSWEIS ENTFERNT]` |
| `gender` | Geschlecht: m/w/d | `[GESCHLECHT ENTFERNT]` |
| `url` | https://... | `[URL ENTFERNT]` |

## Medical Term Protection

### Protected Categories

| Category | Count | Examples |
|----------|-------|----------|
| Medical Terms | 300+ | Diabetes, Hypertonie, Hämoglobin |
| Abbreviations | 210+ | HbA1c, TSH, CRP, eGFR, MRT |
| Drug Names (INN) | 120+ | Metformin, Ramipril, Omeprazol |
| Brand Names (DE) | 50+ | Beloc, Pantozol, Marcumar |
| Medical Eponyms | 50+ | Parkinson, Alzheimer, Cushing |
| LOINC Codes | 60+ | 2339-0 (Glucose), 718-7 (Hgb) |

### Medical Coding Support

- **ICD-10 codes**: A00.0 - Z99.9 (e.g., E11.9, I10, G20)
- **OPS codes**: 1-000.0 - 9-999.9 (e.g., 5-470.11)
- **EBM codes**: 5-digit billing codes
- **LOINC codes**: Lab test identifiers (e.g., 2339-0, 718-7)

## Confidence Scoring (Phase 5)

Each PII removal is classified by confidence level:

| Level | Criteria | Example |
|-------|----------|---------|
| **High** | Multi-word names OR title context (Dr., Herr) | "Dr. Schmidt" |
| **Medium** | Single word with some context | "Schmidt" after "Patient:" |
| **Low** | Single word, no context | "Schmidt" alone |
| **Pattern-based** | Regex match (100% confident) | "Geb.: 01.01.1980" |

### Quality Score

Quality score (0-100) is calculated as:
```
score = weighted_avg(
    pattern_based * 100,
    high_confidence * 100,
    medium_confidence * 80,
    low_confidence * 50
)
```

### Review Recommendation

`review_recommended = True` when:
- More than 2 low-confidence removals
- Any potential false positives detected
- Medical content validation fails

## Usage

### Basic Usage

```python
from app.services.privacy_filter_advanced import AdvancedPrivacyFilter

filter = AdvancedPrivacyFilter()
cleaned_text, metadata = filter.remove_pii(document_text)

# Check results
print(f"PII types found: {metadata['pii_types_detected']}")
print(f"Quality score: {metadata['quality_summary']['quality_score']}")
print(f"Review needed: {metadata['review_recommended']}")
```

### Batch Processing

```python
# Process multiple documents efficiently
documents = [doc1, doc2, doc3, ...]
results = filter.remove_pii_batch(documents, batch_size=32)

for cleaned, metadata in results:
    print(f"Processed: {metadata['total_time_ms']:.1f}ms")
```

### Custom Terms (Database-driven)

Add custom terms via `system_settings` table:

```sql
-- Add custom medical terms
INSERT INTO system_settings (key, value, value_type)
VALUES ('privacy_filter.custom_medical_terms',
        '["spezialterm", "klinikspezifisch"]',
        'json');

-- Add custom drug names
INSERT INTO system_settings (key, value, value_type)
VALUES ('privacy_filter.custom_drugs',
        '["neuesmedikament"]',
        'json');

-- Exclude terms from protection
INSERT INTO system_settings (key, value, value_type)
VALUES ('privacy_filter.excluded_terms',
        '["termzuentfernen"]',
        'json');
```

## API Endpoints

### GET /api/privacy/metrics

Returns filter capabilities and statistics.

**Response:**
```json
{
  "filter_capabilities": {
    "has_ner": true,
    "spacy_model": "de_core_news_sm",
    "removal_method": "AdvancedPrivacyFilter_Phase5"
  },
  "detection_stats": {
    "pii_types_count": 17,
    "medical_terms_count": 312,
    "drug_database_count": 127,
    "loinc_codes_count": 60
  }
}
```

### POST /api/privacy/test

Live test the filter with custom text.

**Request:**
```json
{
  "text": "Patient: Müller, Hans\nGeb.: 15.05.1965"
}
```

**Response:**
```json
{
  "processing_time_ms": 45.2,
  "pii_types_detected": ["patient_name", "birthdate"],
  "quality_score": 100.0,
  "review_recommended": false
}
```

### GET /api/privacy/health

Check filter health and readiness.

### GET /api/privacy/pii-types

List all supported PII types with descriptions.

## Performance

### Targets

| Metric | Target | Typical |
|--------|--------|---------|
| Average processing time | <100ms | 50-70ms |
| Short documents (<500 chars) | <30ms | 15-25ms |
| Long documents (>3000 chars) | <150ms | 80-120ms |
| Memory per document | <50MB | ~20MB |

### Benchmarking

Run the benchmark script:
```bash
cd backend
python scripts/benchmark_privacy_filter.py --iterations 20
python scripts/benchmark_privacy_filter.py --output results.json
```

## Metadata Structure

The `remove_pii()` method returns `(cleaned_text, metadata)`:

```python
{
    # Basic detection
    "entities_detected": 5,
    "has_ner": True,

    # Confidence scoring (Phase 5.1)
    "high_confidence_removals": 3,
    "medium_confidence_removals": 0,
    "low_confidence_removals": 1,
    "pattern_based_removals": 4,

    # False positive tracking (Phase 5.2)
    "potential_false_positives": [],
    "preserved_medical_terms": [...],
    "review_recommended": False,

    # GDPR audit trail (Phase 5.3)
    "pii_types_detected": ["birthdate", "patient_name", ...],
    "processing_timestamp": "2024-01-20T10:30:00",
    "gdpr_compliant": True,

    # Quality summary (Phase 5.4)
    "quality_summary": {
        "quality_score": 95.0,
        "total_pii_removed": 8,
        "confidence_breakdown": {...},
        "review_flags": []
    },

    # Performance metrics
    "total_time_ms": 52.3,
    "regex_removal_time_ms": 5.2,
    "ner_removal_time_ms": 35.1,
}
```

## GDPR Compliance

### Data Processing

- All PII processing happens locally (no external API calls)
- No PII is logged or stored during processing
- Audit trail records types removed (not content)

### Compliance Features

- **Audit Trail**: Every removal is tracked by type
- **Timestamp**: Processing time recorded
- **Version Tracking**: Filter version in metadata
- **Review System**: Automatic flagging of uncertain removals

### Best Practices

1. Always check `review_recommended` before publishing
2. Log `pii_types_detected` for audit purposes
3. Store `processing_timestamp` for compliance records
4. Review `potential_false_positives` for quality assurance

## Troubleshooting

### spaCy Model Not Loading

```python
# Check if NER is available
filter = AdvancedPrivacyFilter()
print(f"NER available: {filter.has_ner}")
```

If `has_ner = False`, install the German model:
```bash
python -m spacy download de_core_news_sm
```

### Medical Terms Being Removed

Add terms to custom dictionary:
```sql
INSERT INTO system_settings (key, value, value_type)
VALUES ('privacy_filter.custom_medical_terms',
        '["yourterm"]', 'json');
```

### Performance Issues

1. Check document length (>5000 chars may be slow)
2. Use batch processing for multiple documents
3. Run benchmark script to identify bottlenecks

## Related Files

- `backend/app/services/privacy_filter_advanced.py` - Main implementation
- `backend/app/routers/privacy_metrics.py` - API endpoints
- `backend/tests/test_privacy_filter_advanced.py` - Test suite
- `backend/scripts/benchmark_privacy_filter.py` - Benchmark script
