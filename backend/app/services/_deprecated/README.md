# Deprecated Services

This directory contains service implementations that have been superseded by more comprehensive solutions.

**DO NOT** import from this directory in new code.

## Text Extractors (Deprecated 2025-10-13)

### Deprecated Files:
- `text_extractor.py` (252 lines) - Original basic extractor
- `text_extractor_simple.py` (130 lines) - Simplified version
- `text_extractor_ovh.py` (236 lines) - OVH Vision API only

### Current Solution:
Use `hybrid_text_extractor.HybridTextExtractor` instead - it provides:
- Intelligent strategy selection (LOCAL_TEXT, LOCAL_OCR, VISION_LLM, HYBRID)
- Smart multi-file merging with medical context awareness
- Built-in fallback handling
- Better error recovery

### Migration Guide:
```python
# Old (deprecated)
from app.services.text_extractor_simple import TextExtractor
extractor = TextExtractor()
text = extractor.extract_text(content, file_type)

# New (recommended)
from app.services.hybrid_text_extractor import HybridTextExtractor
extractor = HybridTextExtractor()
text, confidence = await extractor.extract_text(content, file_type, filename)
```

## Privacy Filters (Deprecated 2025-10-13)

### Deprecated Files:
- `privacy_filter.py` (355 lines) - Basic spaCy-based filter
- `optimized_privacy_filter.py` (250 lines) - Performance optimized version
- `smart_privacy_filter.py` (439 lines) - Heuristic-based filtering without ML dependencies

### Current Solution:
Use `privacy_filter_advanced.AdvancedPrivacyFilter` instead - it provides:
- 2x more medical terms (~146 vs ~70)
- 2x more protected abbreviations (~210 vs ~111)
- Optional spaCy NER with graceful fallback
- Validation method `validate_medical_content()`
- GDPR-compliant PII protection

### Migration Guide:
```python
# Old (deprecated)
from app.services.smart_privacy_filter import SmartPrivacyFilter
filter = SmartPrivacyFilter()
cleaned = filter.remove_pii(text)

# New (recommended)
from app.services.privacy_filter_advanced import AdvancedPrivacyFilter
filter = AdvancedPrivacyFilter()
cleaned = filter.remove_pii(text)
```

## Table Processors (Deprecated 2025-10-13)

### Deprecated Files:
- `table_processor.py` (317 lines) - Basic table extraction

### Current Solution:
Use `improved_table_processor.ImprovedTableProcessor` instead - it provides:
- Enhanced table extraction with better structure preservation
- Improved handling of complex medical tables
- Better fallback mechanisms

### Migration Guide:
```python
# Old (deprecated)
from app.services.table_processor import TableProcessor
processor = TableProcessor()
tables = processor.extract_tables(pdf_content)

# New (recommended)
from app.services.improved_table_processor import ImprovedTableProcessor
processor = ImprovedTableProcessor()
tables = processor.extract_tables(pdf_content)
```

## Removal Timeline

These files will be removed in a future sprint after confirming all code paths use the new implementations.
Estimated removal: Sprint ending 2025-11-15

## Related Issue

See GitHub issue #14 - Service Layer Consolidation
