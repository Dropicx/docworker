# Privacy Filter (PII Removal System)

## Overview

DocTranslator implements a **multi-layered PII (Personally Identifiable Information) removal system** to ensure GDPR compliance. All personal data is removed from medical documents **before** any AI processing occurs.

The system uses three complementary approaches:

1. **spaCy NER** - Named Entity Recognition for names, locations, organizations
2. **Microsoft Presidio** - Enhanced detection for IBAN, credit cards, phones, emails
3. **Custom regex patterns** - German-specific identifiers (Tax ID, SSN, insurance numbers)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    PII REMOVAL PIPELINE                              │
│                                                                      │
│  Input Text                                                          │
│       │                                                              │
│       ▼                                                              │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ STEP 1: Custom Regex Patterns                                │    │
│  │ - German Tax ID, Social Security                            │    │
│  │ - Insurance numbers, Patient IDs                            │    │
│  │ - Phone/Fax/Email with German formats                       │    │
│  │ - Addresses (German street patterns)                        │    │
│  │ - Doctor titles with names                                   │    │
│  └─────────────────────────────────────────────────────────────┘    │
│       │                                                              │
│       ▼                                                              │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ STEP 2: spaCy NER (Named Entity Recognition)                 │    │
│  │ - de_core_news_lg: German model (PER, LOC, ORG)             │    │
│  │ - en_core_web_lg: English model (PERSON, GPE, ORG, FAC)     │    │
│  │ - Medical term protection (skip known terms)                 │    │
│  │ - Medical eponym preservation (Parkinson, etc.)              │    │
│  └─────────────────────────────────────────────────────────────┘    │
│       │                                                              │
│       ▼                                                              │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ STEP 3: Microsoft Presidio                                   │    │
│  │ - IBAN codes                                                  │    │
│  │ - Credit card numbers                                         │    │
│  │ - Additional phone/email formats                              │    │
│  │ - IP addresses, URLs                                          │    │
│  │ - Date/time patterns                                          │    │
│  └─────────────────────────────────────────────────────────────┘    │
│       │                                                              │
│       ▼                                                              │
│  Output: Cleaned Text with Placeholders                              │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Infrastructure

### Primary: Hetzner PII Service

**Location**: `pii_service/` directory
**Deployment**: 2x CPX32 servers (4 vCPU, 8GB RAM) with load balancer
**Network**: Private (10.1.0.0/16) with managed SSL

The primary PII service runs on dedicated Hetzner infrastructure:

```
Railway Worker
      │
      │ HTTPS (POST /remove-pii)
      ▼
Hetzner Load Balancer
      │
      ├──▶ PII Server 1 (spaCy + Presidio)
      │
      └──▶ PII Server 2 (spaCy + Presidio)
```

### Fallback: Local Privacy Filter

**Location**: `backend/app/services/privacy_filter_advanced.py`

If the Hetzner service is unavailable, the worker falls back to a local implementation with reduced functionality (regex-only, no large spaCy models).

---

## PII Types Detected

### German Patterns

| PII Type | Example | Placeholder |
|----------|---------|-------------|
| **Doctor title + name** | "Dr. med. Schmidt" | `[DOCTOR_NAME]` |
| **Honorific + name** | "Herr Müller", "Frau Schmidt" | `[NAME]` |
| **Patient name (labeled)** | "Patient: Max Mustermann" | `[PATIENT_NAME]` |
| **Name comma format** | "Mustermann, Anna" | `[PATIENT_NAME]` |
| **Birthdate** | "geb. 15.03.1980" | `[BIRTHDATE]` |
| **Standalone date** | "15.03.2024" | `[DATE]` |
| **German month date** | "15. März 2024" | `[DATE]` |
| **Tax ID** | "Steuer-ID: 12345678901" | `[TAX_ID]` |
| **Social Security** | "SV-Nr: 12 123456 A 123" | `[SOCIAL_SECURITY]` |
| **Phone** | "Tel: 030 1234567" | `[PHONE]` |
| **Fax** | "Fax: 030 1234568" | `[FAX]` |
| **Email** | "kontakt@praxis.de" | `[EMAIL]` |
| **Street address** | "Hauptstraße 15" | `[ADDRESS]` |
| **PLZ + City** | "10115 Berlin" | `[PLZ_CITY]` |
| **Insurance number** | "Versicherten-Nr: A123456789" | `[INSURANCE_ID]` |
| **Patient ID** | "Patient-Nr: P-2024-001" | `[PATIENT_ID]` |
| **Case reference** | "Fall-Nr. 12345" | `[REFERENCE_ID]` |

### English Patterns

| PII Type | Example | Placeholder |
|----------|---------|-------------|
| **Doctor title + name** | "Dr. Smith", "Prof. Johnson" | `[DOCTOR_NAME]` |
| **Honorific + name** | "Mr. Smith", "Mrs. Johnson" | `[NAME]` |
| **Patient name** | "Patient: John Doe" | `[PATIENT_NAME]` |
| **Birthdate** | "DOB: 03/15/1980" | `[BIRTHDATE]` |
| **SSN** | "SSN: 123-45-6789" | `[SSN]` |
| **Phone** | "Phone: (555) 123-4567" | `[PHONE]` |
| **Email** | "john@example.com" | `[EMAIL]` |
| **Address** | "123 Main Street" | `[ADDRESS]` |
| **ZIP code** | "12345" or "12345-6789" | `[ZIPCODE]` |

### Presidio-Detected Types

| PII Type | Description | Placeholder |
|----------|-------------|-------------|
| **IBAN** | International bank account number | `[IBAN]` |
| **Credit card** | Card numbers (Visa, MC, etc.) | `[CREDIT_CARD]` |
| **IP address** | IPv4 and IPv6 addresses | `[IP_ADDRESS]` |
| **URL** | Web addresses | `[URL]` |
| **Date/Time** | Various date formats | `[DATE]` |

### NER-Detected Entities

| Entity Type | German (de) | English (en) | Placeholder |
|-------------|-------------|--------------|-------------|
| **Person** | PER | PERSON | `[NAME]` |
| **Location** | LOC | LOC, GPE | `[LOCATION]` |
| **Organization** | ORG | ORG, FAC | `[ORGANIZATION]` |
| **Date** | - | DATE | `[DATE]` |
| **Time** | - | TIME | `[TIME]` |

---

## Medical Term Protection

The PII filter preserves medical terminology to ensure document meaning is retained.

### Protected Categories

#### Anatomy (100+ terms)
```
herz, lunge, leber, niere, magen, darm, kopf, hals, brust, bauch,
rücken, schulter, knie, hüfte, hand, fuß, hirn, gehirn, muskel,
knochen, gelenk, nerv, gefäß, thorax, abdomen, extremitäten,
wirbelsäule, becken, schädel, milz, pankreas, gallenblase,
schilddrüse, nebenniere, prostata, uterus, ovarien, hoden,
lymphknoten, rückenmark, knochenmark, arterie, vene, aorta...
```

#### Clinical Terms (100+ terms)
```
patient, diagnose, befund, therapie, behandlung, untersuchung,
operation, medikament, dosierung, anamnese, prognose, epikrise,
symptom, syndrom, erkrankung, krankheit, störung, insuffizienz,
entzündung, infektion, nekrose, ischämie, ruptur, läsion...
```

#### Conditions (100+ terms)
```
stenose, thrombose, embolie, infarkt, tumor, karzinom, metastase,
aneurysma, fraktur, hypertonie, tachykardie, bradykardie,
arrhythmie, diabetes, pneumonie, bronchitis, asthma, copd,
gastritis, hepatitis, arthritis, arthrose, osteoporose,
depression, schizophrenie, demenz...
```

#### Cardiac Valve Terms
```
mitralinsuffizienz, mitralstenose, aorteninsuffizienz,
aortenstenose, trikuspidalklappe, pulmonalklappe,
herzinsuffizienz, klappeninsuffizienz, klappenstenose...
```

#### Procedures (50+ terms)
```
appendektomie, cholezystektomie, gastrektomie, nephrektomie,
thyreoidektomie, mastektomie, laparotomie, thorakotomie,
kraniotomie, angioplastik, arthroplastik...
```

#### Lab Values (50+ terms)
```
hämoglobin, hämatokrit, erythrozyten, leukozyten, thrombozyten,
kreatinin, harnstoff, harnsäure, bilirubin, transaminasen,
got, gpt, ggt, ap, ldh, ck, troponin, bnp, crp, tsh, hba1c...
```

### Medication Database (200+ drugs)

The filter includes a comprehensive medication database to prevent drug names from being removed:

```python
drug_database = {
    # Diabetes
    "metformin", "glibenclamid", "sitagliptin", "empagliflozin", "insulin",

    # Beta blockers
    "metoprolol", "bisoprolol", "carvedilol", "nebivolol", "atenolol",

    # ACE inhibitors
    "ramipril", "enalapril", "lisinopril", "perindopril", "captopril",

    # Statins
    "simvastatin", "atorvastatin", "rosuvastatin", "pravastatin",

    # Anticoagulants
    "aspirin", "clopidogrel", "rivaroxaban", "apixaban", "warfarin",

    # Antibiotics
    "amoxicillin", "ciprofloxacin", "azithromycin", "metronidazol",

    # PPIs
    "omeprazol", "pantoprazol", "esomeprazol",

    # And 150+ more...
}
```

### Medical Eponyms (50+ names)

Disease names derived from people are preserved:

```python
medical_eponyms = {
    # Neurological
    "parkinson", "alzheimer", "huntington", "guillain", "barré",
    "tourette", "ménière", "wernicke", "korsakoff",

    # Cardiovascular
    "raynaud", "marfan", "kawasaki", "fallot", "brugada",

    # Gastrointestinal
    "crohn", "barrett", "whipple", "hirschsprung",

    # Endocrine
    "cushing", "addison", "hashimoto", "graves", "basedow",

    # Genetic
    "down", "turner", "klinefelter", "prader", "willi",

    # And 30+ more...
}
```

### German Declension Support

The filter handles German grammatical variations:

```python
# Input: "nächtliche paroxysmale Dyspnoe"
# Without declension support: "nächtliche" might be removed as unknown
# With declension support: stem "nächtlich" matches medical terms → preserved

german_suffixes = [
    'ischen', 'ische', 'ischer',  # adjective endings
    'ungen', 'liche', 'lichen',   # noun/adjective endings
    'aler', 'ales', 'enen',       # more adjective endings
    'en', 'er', 'es', 'e', 'n'    # common endings
]
```

---

## False Positive Prevention

### Medical Value Protection

Numbers followed by medical units are not treated as phone numbers:

```python
# Protected patterns (NOT phone numbers):
"4000 Hz"      # Audiometry frequency
"120/80 mmHg"  # Blood pressure
"1500 ml"      # Fluid volume
"75 kg"        # Weight
"150 mg"       # Medication dosage

# Medical units recognized:
Hz, kHz, MHz, mmHg, cmH2O, kPa, mg, µg, ng, g, kg,
ml, µl, dl, l, mm, cm, m, mmol, µmol, U, IU, IE,
mV, µV, V, Bq, MBq, Gy, bpm, /min, pg/ml, ng/ml...
```

### Preserved Organizations

Generic organizations that don't identify patients:

```python
preserved_orgs = {
    # German insurance companies
    "aok", "tk", "techniker", "barmer", "dak", "bkk", "ikk",

    # Medical organizations
    "who", "rki", "ema", "fda", "cdc", "pei",

    # Medical associations
    "ärzteblatt", "ärztekammer", "kassenärztliche",
}
```

### Preserved Locations

Country names that don't identify patients:

```python
preserved_locations = {
    "deutschland", "germany", "österreich", "austria",
    "schweiz", "switzerland", "europa", "europe",
    "usa", "amerika", "america",
}
```

---

## API Reference

### Remove PII (Single Text)

```http
POST /remove-pii
Authorization: Bearer <API_KEY>
Content-Type: application/json

{
  "text": "Patient Max Mustermann, geb. 15.03.1980, wohnhaft Hauptstraße 15, 10115 Berlin. Diagnose: Morbus Parkinson.",
  "language": "de",
  "include_metadata": true,
  "custom_protection_terms": ["Aspirin", "Ibuprofen"]
}
```

**Response:**

```json
{
  "cleaned_text": "Patient [NAME], geb. [BIRTHDATE], wohnhaft [ADDRESS], [PLZ_CITY]. Diagnose: Morbus Parkinson.",
  "processing_time_ms": 45.2,
  "language_used": "de",
  "metadata": {
    "language": "de",
    "original_length": 145,
    "cleaned_length": 98,
    "processing_timestamp": "2026-01-16T10:30:00.000Z",
    "gdpr_compliant": true,
    "entities_detected": 4,
    "pattern_removals": 3,
    "pii_types": ["honorific_name", "birthdate", "address", "plz_city"],
    "ner_removals": 1,
    "ner_locations_removed": 0,
    "ner_orgs_removed": 0,
    "eponyms_preserved": 1,
    "presidio_removals": 0,
    "custom_terms_count": 2
  }
}
```

### Remove PII (Batch)

```http
POST /remove-pii/batch
Authorization: Bearer <API_KEY>
Content-Type: application/json

{
  "texts": [
    "Patient Anna Schmidt, Tel: 030 12345",
    "Dr. med. Weber, Klinik Berlin"
  ],
  "language": "de",
  "batch_size": 32,
  "custom_protection_terms": []
}
```

**Response:**

```json
{
  "results": [
    {
      "cleaned_text": "Patient [NAME], Tel: [PHONE]",
      "metadata": { "entities_detected": 2 }
    },
    {
      "cleaned_text": "[DOCTOR_NAME], [ORGANIZATION]",
      "metadata": { "entities_detected": 2 }
    }
  ],
  "total_documents": 2,
  "processing_time_ms": 78.5,
  "language_used": "de"
}
```

### Health Check

```http
GET /health
```

**Response:**

```json
{
  "status": "healthy",
  "service": "SpaCy PII Service",
  "version": "1.0.0",
  "spacy_available": true,
  "german_model_loaded": true,
  "english_model_loaded": true,
  "presidio_available": true,
  "memory_usage_mb": 2048.5
}
```

---

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `EXTERNAL_PII_URL` | Hetzner PII service URL | - |
| `EXTERNAL_PII_API_KEY` | API key for Hetzner service | - |
| `USE_EXTERNAL_PII` | Enable external service | `true` |
| `PII_TIMEOUT_SECONDS` | Request timeout | `30` |
| `SPACY_DATA_DIR` | Model storage path | `/data/models` |

### Custom Protection Terms

Additional terms can be protected via the database:

```sql
INSERT INTO system_settings (key, value, category)
VALUES ('pii_custom_protection_terms',
        '["CustomDrug", "SpecialCondition"]',
        'privacy');
```

These terms are passed to the PII service with each request.

---

## Performance

### Processing Times

| Scenario | Time | Method |
|----------|------|--------|
| Simple document (few names) | 10-20ms | Fast-path regex |
| Complex document (many entities) | 100-120ms | Full NER pipeline |
| Batch (32 documents) | 500-800ms | Parallel processing |

### Memory Usage

| Component | Memory |
|-----------|--------|
| spaCy de_core_news_lg | ~800MB |
| spaCy en_core_web_lg | ~800MB |
| Presidio analyzers | ~200MB |
| Application overhead | ~200MB |
| **Total** | ~2GB |

### Throughput

- Single requests: ~50 requests/second
- Batch mode: ~500 texts/second
- Concurrent users: 100+ (with load balancer)

---

## Quality Assurance

### Confidence Levels

Each detection includes a confidence score:

- **HIGH** (>0.9): Strong pattern match or high NER confidence
- **MEDIUM** (0.6-0.9): Moderate confidence, may need review
- **LOW** (<0.6): Weak match, logged for analysis

### False Positive Tracking

The system logs potential false positives for continuous improvement:

```python
# Logged when medical value incorrectly flagged as PII
logger.warning(
    f"Detected likely false positive: '{match}' - "
    f"a medical value was incorrectly replaced as PII."
)
```

### Audit Trail

Every PII removal operation is logged:

```
2026-01-16 10:30:00 | method=POST path=/remove-pii status=200 duration=0.045s client=10.1.1.10
```

Audit logs are retained for 90 days (GDPR compliance).

---

## Testing

### Unit Tests

```bash
cd pii_service
pytest tests/test_pii_patterns.py -v
```

### Test Cases

```python
def test_german_name_removal():
    text = "Patient Max Mustermann"
    result, _ = filter.remove_pii(text, "de")
    assert "[NAME]" in result
    assert "Mustermann" not in result

def test_medical_term_preservation():
    text = "Diagnose: Morbus Parkinson"
    result, _ = filter.remove_pii(text, "de")
    assert "Parkinson" in result  # Eponym preserved

def test_medication_preservation():
    text = "Medikation: Metoprolol 100mg"
    result, _ = filter.remove_pii(text, "de")
    assert "Metoprolol" in result  # Drug preserved
    assert "100mg" in result       # Dosage preserved
```

---

## Troubleshooting

### Common Issues

**Models not loading:**
```bash
# Check model installation
python -c "import spacy; spacy.load('de_core_news_lg')"

# Verify SPACY_DATA_DIR
ls $SPACY_DATA_DIR/de_core_news_lg/
```

**High memory usage:**
- Ensure only one PIIFilter instance is created (singleton pattern)
- Check for memory leaks with `psutil.Process().memory_info()`

**False positives:**
- Add custom protection terms via API
- Check if term is in medical term database
- Review NER entity labels

**Slow processing:**
- Check if spaCy models are loaded (startup time: 60-90s)
- Use batch endpoint for multiple texts
- Monitor CPU usage on Hetzner servers

---

## GDPR Compliance Checklist

- [x] PII removal before AI processing
- [x] EU-only infrastructure (Hetzner Germany)
- [x] No text content in logs (metadata only)
- [x] Audit trail for compliance
- [x] 90-day audit log retention
- [x] Custom term protection support
- [x] Batch processing for efficiency
- [x] Fallback to local processing if service unavailable

---

*Last Updated: January 2026*
