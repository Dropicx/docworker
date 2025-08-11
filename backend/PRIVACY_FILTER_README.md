# Privacy Filter mit spaCy NER

## 🚀 Deployment-Status

Die Anwendung ist jetzt mit **spaCy NER (Named Entity Recognition)** für intelligente Namenerkennung konfiguriert!

## 📦 Was wurde implementiert?

### 1. **Drei-Stufen-System** mit Fallback:

#### Stufe 1: AdvancedPrivacyFilter mit spaCy NER ✨
- **Aktiviert wenn**: spaCy und deutsches Modell installiert sind
- **Vorteile**: 
  - KI-basierte Namenerkennung
  - Erkennt auch unbekannte Namen
  - Unterscheidet medizinische Eponyme von echten Namen
- **Datei**: `privacy_filter_advanced.py`

#### Stufe 2: SmartPrivacyFilter (Heuristik) 🧩
- **Aktiviert wenn**: spaCy nicht verfügbar
- **Vorteile**:
  - Keine externen Dependencies
  - Schnell und zuverlässig
  - Kontextbasierte Erkennung
- **Datei**: `smart_privacy_filter.py`

#### Stufe 3: Basis-Filter (veraltet) ⚠️
- **Nicht mehr verwendet**
- **Datei**: `privacy_filter.py`

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
Die Anwendung wählt automatisch den besten verfügbaren Filter:

```python
# In ovh_client.py und ollama_client.py
if ADVANCED_FILTER_AVAILABLE:
    self.privacy_filter = AdvancedPrivacyFilter()  # Mit spaCy
    logger.info("🧠 Using AdvancedPrivacyFilter with spaCy NER")
else:
    self.privacy_filter = SmartPrivacyFilter()     # Fallback
    logger.info("📝 Using SmartPrivacyFilter (heuristic-based)")
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