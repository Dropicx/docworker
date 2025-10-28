# Privacy Filter mit spaCy NER

> ## ⚠️ OUTDATED DOCUMENTATION (2025-10-13)
>
> **This document describes an old three-tier system that has been consolidated.**
>
> **Current Implementation**: Single consolidated filter
> - **Filter**: `AdvancedPrivacyFilter` (privacy_filter_advanced.py)
> - **Features**:
>   - Optional spaCy NER with graceful fallback to regex-only mode
>   - 146+ medical terms protected
>   - 210+ medical abbreviations protected
>   - GDPR-compliant PII removal
> - **Deprecated Filters**: Moved to `backend/app/services/_deprecated/`
>   - privacy_filter.py
>   - optimized_privacy_filter.py
>   - smart_privacy_filter.py
>
> See [REFACTORING_NOTES.md](../docs/REFACTORING_NOTES.md) for details.

## 🚀 Deployment-Status

Die Anwendung ist jetzt mit **spaCy NER (Named Entity Recognition)** für intelligente Namenerkennung konfiguriert!

## 📦 Was wurde implementiert?

### 1. **Konsolidiertes Filter-System**:

#### Current: AdvancedPrivacyFilter ✨
- **Location**: `backend/app/services/privacy_filter_advanced.py`
- **Features**:
  - Optional spaCy NER (falls verfügbar)
  - Graceful fallback to regex-only mode
  - 146+ medizinische Begriffe geschützt
  - 210+ medizinische Abkürzungen geschützt
  - GDPR-konform

#### Deprecated Filters (moved to _deprecated/) ⚠️
- `privacy_filter.py` - Basic filter
- `optimized_privacy_filter.py` - Performance optimized
- `smart_privacy_filter.py` - Heuristic-based

## 🐳 Docker-Deployment

### Requirements
```txt
spacy==3.7.2
```

### Dockerfile
```dockerfile
# spaCy und deutsches Modell werden automatisch installiert
RUN pip install --no-cache-dir -r requirements.txt
RUN python -m spacy download de_core_news_sm
```

## 🔧 Konfiguration

### Automatische Erkennung
Die Anwendung verwendet AdvancedPrivacyFilter mit automatischem Fallback:

```python
# Current implementation (worker/tasks/document_processing.py)
from app.services.privacy_filter_advanced import AdvancedPrivacyFilter

pii_filter = AdvancedPrivacyFilter()
# Automatically uses spaCy NER if available, otherwise falls back to regex-only mode
cleaned_text = pii_filter.remove_pii(extracted_text)
```

## 🧪 Testen

### Lokal testen
```bash
# Mit API
python test_api_privacy.py

# Direkt
python test_advanced_filter.py
```

### Railway testen
```bash
python test_api_privacy.py https://ihre-app.up.railway.app
```

## 📊 Erwartete Ergebnisse

### Mit spaCy (AdvancedPrivacyFilter):
- **Namenerkennung**: 95%+ Genauigkeit
- **Medizinische Begriffe erhalten**: 98%+
- **Geschwindigkeit**: ~200ms pro Dokument

### Ohne spaCy (SmartPrivacyFilter):
- **Namenerkennung**: 85%+ Genauigkeit
- **Medizinische Begriffe erhalten**: 95%+
- **Geschwindigkeit**: ~50ms pro Dokument

## 🔍 Was wird entfernt?

### Persönliche Daten (PII):
- ✅ Namen (auch unbekannte)
- ✅ Adressen
- ✅ Geburtsdaten
- ✅ Telefonnummern
- ✅ E-Mail-Adressen
- ✅ Versicherungsnummern
- ✅ Geschlechtsangaben

### Was bleibt erhalten:
- ✅ Medizinische Eponyme (Morbus Crohn, Parkinson, etc.)
- ✅ Anatomische Strukturen (Baker-Zyste, etc.)
- ✅ Medizinische Tests (Babinski-Reflex, etc.)
- ✅ Laborwerte und Befunde
- ✅ Diagnosen (ICD-Codes)
- ✅ Medikamente und Dosierungen
- ✅ Medizinische Abkürzungen (BMI, HbA1c, etc.)

## 🚨 Wichtige Hinweise

1. **Railway Deployment**: 
   - Der Docker-Build kann 2-3 Minuten dauern (spaCy-Installation)
   - Das deutsche Modell ist ~15MB groß

2. **Speicherverbrauch**:
   - Mit spaCy: ~200MB RAM
   - Ohne spaCy: ~50MB RAM

3. **Erste Anfrage**:
   - Kann etwas länger dauern (Model-Loading)
   - Nachfolgende Anfragen sind schneller

## 📈 Performance-Monitoring

In den Logs sehen Sie:
```
🧠 Using AdvancedPrivacyFilter with spaCy NER    # spaCy aktiv
✅ spaCy deutsches Modell (de_core_news_sm) geladen

oder

📝 Using SmartPrivacyFilter (heuristic-based)    # Fallback aktiv
⚠️ spaCy nicht verfügbar, verwende reine Heuristik
```

## 🆘 Troubleshooting

### spaCy funktioniert nicht?
1. Prüfen Sie die Logs beim Start
2. Stellen Sie sicher, dass genug RAM verfügbar ist
3. Der Fallback (SmartPrivacyFilter) funktioniert trotzdem gut!

### Zu viele Namen bleiben erhalten?
- Das System ist konservativ bei medizinischen Begriffen
- Lieber ein medizinischer Begriff zu viel als zu wenig

### Performance-Probleme?
- Erste Anfrage ist langsamer (Model-Loading)
- Bei Speicherproblemen: Fallback nutzt weniger RAM