# Dokumentation: Spezialisierter Medizinischer Systemprompt

## Übersicht

Der DocTranslator verwendet einen hochspezialisierten Systemprompt für die Übersetzung medizinischer Dokumente. Dieser Prompt wurde entwickelt, um höchste medizinische Genauigkeit bei optimaler Patientenverständlichkeit zu gewährleisten.

## Implementierung

**Datei**: `backend/app/services/ollama_client.py`  
**Methode**: `_get_translation_prompt()`  
**Datum der Implementierung**: 2024

## Kernprinzipien

### 1. Medizinische Präzision
- **Absolute Verbote**: Niemals neue Diagnosen hinzufügen, bestehende weglassen oder uminterpretieren
- **Vollständigkeitsprinzip**: Alle medizinischen Informationen müssen erhalten bleiben
- **Quelltreue**: Nur explizit im Dokument stehende Informationen übersetzen

### 2. Patientenverständlichkeit
- **Einfache Sprache**: Kurze Hauptsätze (max. 15-20 Wörter)
- **Aktive Formulierungen**: "Der Arzt untersucht" statt "Es wird untersucht"
- **Alltagsvergleiche**: "groß wie eine Walnuss"
- **Fachbegriff-Erklärung**: Jeder medizinische Begriff wird sofort erklärt

### 3. Sicherheitsmechanismen
- **Unsicherheitsmarkierung**: [?] bei unklaren Begriffen
- **Arzt-Rücksprache**: Hinweise auf notwendige Klärungen
- **Rechtlicher Hinweis**: Klare Abgrenzung zur medizinischen Beratung

## Verarbeitungsprozess

### Schritt 1: Analyse
1. **Dokumenttyp-Erkennung**: Automatische Klassifizierung (Arztbrief, Laborbefund, etc.)
2. **Strukturanalyse**: Erkennung der Hauptabschnitte
3. **Fachbegriff-Identifikation**: Erfassung aller medizinischen Konzepte

### Schritt 2: Extraktion
Systematische Erfassung von:
- Diagnosen (ICD-Codes und Bezeichnungen)
- Medikamenten (Wirkstoffe und Handelsnamen)
- Untersuchungsergebnissen
- Prozeduren und Eingriffen
- Laborwerten und Vitalparametern
- Empfehlungen und Maßnahmen

### Schritt 3: Übersetzung
1. **Einleitende Zusammenfassung**
2. **Strukturierte Abarbeitung**
3. **Satz-für-Satz-Übersetzung**
4. **Direkte Fachbegriff-Erklärung**
5. **Zusammenhang-Darstellung**

### Schritt 4: Validierung
Qualitätskontrolle für:
- Vollständigkeit der Originalinformationen
- Erklärung aller Fachbegriffe
- Medizinische Korrektheit
- Laienverständlichkeit

## Ausgabeformat

### Struktur
```
# [DOKUMENTTYP] - Verständliche Fassung

## Wichtigste Information
[Essenz in einem Satz]

## Was wurde untersucht/behandelt?
[Grund des Arztbesuchs]

## Was wurde festgestellt?
### Hauptbefunde:
• [Befund in einfacher Sprache]
  → Was bedeutet das? [Erklärung]

### Diagnosen:
• [Deutsche Bezeichnung]
  → Fachbegriff: [Original]
  → Erklärung: [Detailbeschreibung]

## Behandlung/Medikamente
• [Maßnahme]
  → Zweck: [Verwendungszweck]
  → Wichtig zu wissen: [Besonderheiten]

## Was passiert als Nächstes?
• [Chronologische Schritte]
• [Kontrolltermine]
• [Verhaltensempfehlungen]

## Wörterbuch der Fachbegriffe
• **[Begriff]**: [Verständliche Erklärung]

## Wichtiger Hinweis
[Standardhinweis auf ärztliche Betreuung]

⚠️ Markierte Stellen [?] bei Unsicherheiten
```

## Dokumenttyp-Spezialisierung

### Arztbriefe
- **Fokus**: Diagnosen und Therapieempfehlungen
- **Besonderheiten**: Chronologische Darstellung, Trennung Vorgeschichte/aktuelle Befunde
- **Spezielle Abschnitte**: Therapieplan, Nachkontrollen, Hausarzt-Empfehlungen

### Laborbefunde
- **Fokus**: Werteerklärungen mit Normalbereich-Vergleichen
- **Besonderheiten**: Status-Bewertung (normal/erhöht/erniedrigt)
- **Spezielle Abschnitte**: Einzelwert-Erklärung, Gesundheitsbedeutung

### Radiologie-Befunde
- **Fokus**: Bildgebungserklärungen
- **Besonderheiten**: Anatomische Strukturbeschreibung
- **Spezielle Abschnitte**: Untersuchungsmethode, Befundbedeutung

### Pathologie-Befunde
- **Fokus**: Sensitive Kommunikation
- **Besonderheiten**: Einfühlsame Gewebeerklärung
- **Spezielle Abschnitte**: Zellveränderungen, Prognose-Information

### Entlassungsbriefe
- **Fokus**: Nachsorge und Verhaltensempfehlungen
- **Besonderheiten**: Krankenhausaufenthalt-Zusammenfassung
- **Spezielle Abschnitte**: Medikamentenplan, Zuhause-Verhalten, Warnzeichen

## Übersetzungsbeispiele

### Standardformulierungen
| Medizinisch | Patientenfreundlich |
|-------------|---------------------|
| "Pat. zeigt keine Auffälligkeiten" | "Bei Ihnen wurde nichts Ungewöhnliches festgestellt" |
| "Auskultatorisch unauffällig" | "Beim Abhören von Herz und Lunge war alles normal" |
| "Therapie mit ASS 100mg 1-0-0" | "Behandlung mit Aspirin 100mg - eine Tablette morgens" |
| "V.a. Pneumonie" | "Verdacht auf Lungenentzündung" |
| "Z.n. Appendektomie 2019" | "Blinddarm wurde 2019 entfernt" |

### Fachbegriffe
| Fachbegriff | Erklärung |
|-------------|-----------|
| "Hypertonie" | "Bluthochdruck (dauerhaft erhöhter Blutdruck)" |
| "Diabetes mellitus Typ 2" | "Zuckerkrankheit Typ 2 (Blutzucker ist zu hoch)" |
| "Koronare Herzkrankheit" | "Verengung der Herzkranzgefäße (Blutgefäße, die das Herz versorgen)" |
| "Gastroenteritis" | "Magen-Darm-Entzündung (Durchfall und Erbrechen)" |

### Laborwerte
| Medizinisch | Patientenfreundlich |
|-------------|---------------------|
| "Hb 12,5 g/dl" | "Hämoglobin (roter Blutfarbstoff): 12,5 - leicht erniedrigt" |
| "Leukos 11.000/µl" | "Weiße Blutkörperchen: 11.000 - leicht erhöht (normale Abwehrreaktion)" |
| "CRP erhöht" | "Entzündungswert im Blut ist erhöht" |

## Qualitätskontrolle

### Automatische Prüfungen
- [ ] Alle medizinischen Informationen erhalten
- [ ] Keine neuen Informationen hinzugefügt
- [ ] Alle Fachbegriffe erklärt
- [ ] Text für Laien verständlich
- [ ] Struktur logisch und übersichtlich
- [ ] Unsicherheiten markiert
- [ ] Rechtlicher Hinweis vorhanden

### Sicherheitsmechanismen
1. **Bei Unsicherheiten**: [?]-Markierung + Arzt-Rücksprache-Hinweis
2. **Bei kritischen Informationen**: Sachliche, neutrale Formulierung
3. **Bei fehlenden Informationen**: Klare Kennzeichnung + Verweis auf Arztgespräch

## Rechtlicher Hinweis

**Standard-Abschlusstext**:
> "Diese Übersetzung dient ausschließlich Ihrem besseren Verständnis der medizinischen Unterlagen. Sie stellt keine medizinische Beratung dar und ersetzt nicht das Gespräch mit Ihrem behandelnden Arzt. Alle medizinischen Entscheidungen sollten nur in Absprache mit qualifiziertem medizinischem Fachpersonal getroffen werden. Bei Notfällen wählen Sie bitte den Notruf 112."

## Technische Details

### Modell-Parameter
- **Temperatur**: 0.3 (niedrig für konsistente medizinische Übersetzungen)
- **Top-P**: 0.9
- **Top-K**: 40
- **Max Tokens**: 3000 (für ausführliche Erklärungen)

### Dokumenttyp-Erkennung
**Erkennungslogik**: Keyword-basierte Mustererkennung mit Mindest-Score von 2 Treffern

| Dokumenttyp | Schlüsselwörter |
|-------------|-----------------|
| Arztbrief | "sehr geehrte", "diagnose", "therapie", "weiterbehandlung" |
| Entlassungsbrief | "entlassung", "krankenhausaufenthalt", "nachsorge", "heimkehr" |
| Laborbefund | "laborwerte", "referenzbereich", "erhöht", "erniedrigt" |
| Radiologie | "röntgen", "ct", "mrt", "befund", "bildgebung" |
| Pathologie | "histologie", "biopsie", "maligne", "benigne" |

## Wartung und Updates

### Regelmäßige Überprüfung
- **Übersetzungsqualität**: Monatliche Stichproben
- **Neue Fachbegriffe**: Quartalsweise Aktualisierung
- **Sicherheitsmechanismen**: Halbjährliche Review

### Verbesserungsmaßnahmen
- **Feedback-Integration**: Nutzer-Rückmeldungen einarbeiten
- **Modell-Updates**: Neue Sprachmodelle testen
- **Prompt-Optimierung**: Kontinuierliche Verfeinerung

## Compliance und Datenschutz

### DSGVO-Konformität
- **Lokale Verarbeitung**: Keine Datenübertragung an externe Dienste
- **Keine Speicherung**: Dokumente werden nicht dauerhaft gespeichert
- **Anonymisierung**: Keine Personendaten in Logs

### Medizinische Standards
- **Patientensicherheit**: Höchste Priorität bei allen Übersetzungen
- **Evidenzbasiert**: Nur medizinisch fundierte Erklärungen
- **Transparenz**: Klare Kennzeichnung von Grenzen und Unsicherheiten 