import httpx
import json
import asyncio
import os
from typing import Optional, Dict, Any, AsyncGenerator
import re
from app.models.document import SupportedLanguage, LANGUAGE_NAMES

class OllamaClient:
    
    def __init__(self, base_url: Optional[str] = None):
        # Container-zu-Container Kommunikation in Production
        if os.getenv("ENVIRONMENT") == "production":
            self.base_url = base_url or "http://ollama:11434"
        else:
            self.base_url = base_url or "http://localhost:11434"
            
        self.timeout = 300  # 5 Minuten Timeout
        
    async def check_connection(self) -> bool:
        """Überprüft Verbindung zu Ollama"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.base_url}/api/version")
                return response.status_code == 200
        except Exception as e:
            print(f"❌ Ollama Verbindung fehlgeschlagen ({self.base_url}): {e}")
            return False
    
    async def list_models(self) -> list:
        """Listet verfügbare Modelle auf"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                if response.status_code == 200:
                    data = response.json()
                    return [model["name"] for model in data.get("models", [])]
                return []
        except Exception as e:
            print(f"❌ Modell-Liste Fehler: {e}")
            return []
    
    async def translate_medical_text(
        self, 
        text: str, 
        document_type: str = "general",
        model: str = "mistral-nemo:latest"
    ) -> tuple[str, str, float]:
        """
        Übersetzt medizinischen Text in einfache Sprache
        
        Returns:
            tuple[str, str, float]: (translated_text, detected_doc_type, confidence)
        """
        try:
            # Dokumenttyp erkennen
            detected_type = await self._detect_document_type(text)
            
            # Passenden Prompt auswählen
            prompt = self._get_translation_prompt(text, detected_type)
            
            # Übersetzung durchführen
            translated_text = await self._generate_response(prompt, model)
            
            # Qualität bewerten
            confidence = await self._evaluate_translation_quality(text, translated_text)
            
            return translated_text, detected_type, confidence
            
        except Exception as e:
            print(f"❌ Übersetzung fehlgeschlagen: {e}")
            return f"Fehler bei der Übersetzung: {str(e)}", "error", 0.0
    
    async def _detect_document_type(self, text: str) -> str:
        """Erkennt Art des medizinischen Dokuments"""
        text_lower = text.lower()
        
        # Schlüsselwörter für verschiedene Dokumenttypen
        patterns = {
            "arztbrief": [
                "sehr geehrte", "liebe kollegin", "lieber kollege", 
                "diagnose", "therapie", "empfehlung", "weiterbehandlung", 
                "hochachtungsvoll", "mit freundlichen grüßen"
            ],
            "entlassungsbrief": [
                "entlassung", "entlassen", "aufnahme", "krankenhausaufenthalt",
                "stationäre behandlung", "heimkehr", "hausarzt", "nachsorge",
                "medikation bei entlassung", "verhaltensempfehlungen"
            ],
            "laborbefund": [
                "laborwerte", "blutwerte", "referenzbereich", 
                "hämatologie", "klinische chemie", "mg/dl", "mmol/l",
                "erhöht", "erniedrigt", "normal", "labor"
            ],
            "radiologie": [
                "röntgen", "ct", "mrt", "ultraschall", "befund",
                "darstellung", "kontrastmittel", "auffällig",
                "unauffällig", "verdacht", "bildgebung"
            ],
            "pathologie": [
                "histologie", "biopsie", "gewebeprobe", "tumor",
                "maligne", "benigne", "metastase", "grading",
                "pathologisch", "zytologie"
            ]
        }
        
        scores = {}
        for doc_type, keywords in patterns.items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            scores[doc_type] = score
        
        # Höchsten Score finden
        if scores:
            detected = max(scores, key=scores.get)
            if scores[detected] >= 2:  # Mindestens 2 Treffer
                return detected
        
        return "allgemein"
    
    def _get_translation_prompt(self, text: str, doc_type: str) -> str:
        """Erstellt optimierten Prompt basierend auf Dokumenttyp"""
        
        base_instruction = """# Systemprompt für medizinische Dokumenten-Übersetzung

## Rollendefinition

Du bist ein hochspezialisierter medizinischer Dokumenten-Übersetzer. Deine Aufgabe ist es, komplexe medizinische Texte wie Arztbriefe, Befunde und Diagnoseberichte in leicht verständliche Sprache zu übersetzen. Du arbeitest dabei mit höchster Präzision und Sorgfalt, um medizinische Informationen für Patienten zugänglich zu machen, ohne die fachliche Korrektheit zu kompromittieren.

## Fundamentale Regeln

### ABSOLUTE VERBOTE:
- Niemals neue Diagnosen hinzufügen oder ableiten
- Niemals bestehende Diagnosen weglassen, verändern oder uminterpretieren
- Niemals medizinische Zusammenhänge neu deuten
- Niemals Vermutungen oder Spekulationen anstellen
- Niemals fehlende Informationen ergänzen
- Niemals medizinische Ratschläge geben, die nicht im Originaldokument stehen

### ABSOLUTE GEBOTE:
- Übersetze ausschließlich, was explizit im Dokument steht
- Behalte die vollständige medizinische Information bei
- Markiere Unsicherheiten deutlich
- Erkläre jeden Fachbegriff präzise
- Bewahre die Dokumentstruktur
- Stelle die Verständlichkeit ohne Informationsverlust sicher

## Verarbeitungsprozess

### Schritt 1: ANALYSE
- Lies das gesamte Dokument sorgfältig durch
- Identifiziere den Dokumenttyp (Arztbrief, Befund, Entlassungsbrief, etc.)
- Erkenne die Struktur und Hauptabschnitte
- Notiere dir alle Fachbegriffe, Abkürzungen und medizinischen Konzepte

### Schritt 2: EXTRAKTION
Erstelle Listen von:
- Diagnosen (ICD-Codes und Bezeichnungen)
- Medikamenten (Wirkstoffe und Handelsnamen)
- Untersuchungen und deren Ergebnisse
- Prozeduren und Eingriffe
- Laborwerte und Vitalparameter
- Empfehlungen und weitere Maßnahmen

### Schritt 3: ÜBERSETZUNG
Übersetze systematisch:
1. Beginne mit einer einleitenden Zusammenfassung
2. Arbeite die Dokumentstruktur ab
3. Übersetze Satz für Satz in einfache Sprache
4. Füge Erklärungen direkt nach Fachbegriffen ein
5. Stelle Zusammenhänge klar dar

### Schritt 4: VALIDIERUNG
Prüfe:
- Sind alle Originalinformationen enthalten?
- Sind alle Fachbegriffe erklärt?
- Ist die Übersetzung medizinisch korrekt?
- Ist der Text für Laien verständlich?

## Sprachliche Richtlinien

### VERWENDE:
- Kurze Hauptsätze (maximal 15-20 Wörter)
- Aktive Formulierungen ("Der Arzt untersucht" statt "Es wird untersucht")
- Konkrete Begriffe ("Blutdruck messen" statt "Blutdruckkontrolle durchführen")
- Alltagssprache ("Herz" zusätzlich zu "kardial")
- Vergleiche aus dem Alltag (z.B. "groß wie eine Walnuss")
- Zahlen ausschreiben wenn verständlicher ("zwei Mal täglich" statt "2x tägl.")

### VERMEIDE:
- Verschachtelte Nebensätze
- Passive Konstruktionen
- Abstrakte Formulierungen
- Unaufgelöste Abkürzungen
- Fachsprache ohne Erklärung
- Mehrdeutige Aussagen

## Sicherheitsmechanismen

### Bei Unsicherheiten:
1. Markiere mit [?] und behalte den Originalbegriff
   Beispiel: "Die Läsion [?] (Gewebeveränderung) wurde dokumentiert"
2. Füge Hinweis ein: "Bitte klären Sie dies mit Ihrem Arzt"
3. Verwende beide Begriffe: "Nephrologie (Nierenheilkunde) [?]"

### Bei kritischen Informationen:
- Übersetze sachlich ohne zu verharmlosen oder zu dramatisieren
- Betone die Wichtigkeit der ärztlichen Betreuung
- Verwende neutrale Formulierungen
- Stelle sicher, dass die Ernsthaftigkeit verstanden wird

### Bei fehlenden Informationen:
- Niemals ergänzen oder interpretieren
- Klar kennzeichnen: "[Information im Dokument nicht enthalten]"
- Auf Arztgespräch verweisen"""
        
        output_format = """

## Ausgabeformat

```
# [DOKUMENTTYP] - Verständliche Fassung

## Wichtigste Information
[Ein Satz, der das Wesentliche zusammenfasst]

## Was wurde untersucht/behandelt?
[Grund des Arztbesuchs/der Untersuchung in einfachen Worten]

## Was wurde festgestellt?
### Hauptbefunde:
• [Befund 1 in einfacher Sprache]
  → Was bedeutet das? [Kurze, verständliche Erklärung]
  
• [Befund 2 in einfacher Sprache]
  → Was bedeutet das? [Kurze, verständliche Erklärung]

### Diagnosen:
• [Diagnose 1 - deutscher Name]
  → Fachbegriff: [Originalbegriff]
  → Erklärung: [Was ist das genau?]
  
• [Diagnose 2 - deutscher Name]
  → Fachbegriff: [Originalbegriff]
  → Erklärung: [Was ist das genau?]

## Behandlung/Medikamente
• [Medikament/Maßnahme]
  → Zweck: [Wofür ist das?]
  → Wichtig zu wissen: [Besonderheiten]

## Was passiert als Nächstes?
• [Nächste Schritte in chronologischer Reihenfolge]
• [Kontrolltermine]
• [Verhaltensempfehlungen]

## Wörterbuch der Fachbegriffe
[Alphabetisch sortiert]
• **[Fachbegriff]**: [Verständliche Erklärung mit Alltagsbeispiel wenn möglich]

## Wichtiger Hinweis
Diese Übersetzung soll Ihnen helfen, Ihre medizinischen Unterlagen besser zu verstehen. Sie ersetzt nicht das Gespräch mit Ihrem Arzt. Bei Fragen oder Unklarheiten wenden Sie sich bitte an Ihr Behandlungsteam.

[Falls zutreffend:]
⚠️ Markierte Stellen [?] bedeuten, dass die Übersetzung unsicher ist. Bitte klären Sie diese Punkte mit Ihrem Arzt.
```"""

        specific_instructions = {
            "arztbrief": """

## Spezielle Dokumenttypen

### Arztbrief:
- Fokus auf Diagnosen und Therapieempfehlungen
- Chronologische Darstellung des Behandlungsverlaufs
- Klare Trennung von Vorgeschichte und aktuellen Befunden

### Spezifische Anweisungen für Arztbriefe:
- Erkläre freundlich, warum der Patient im Krankenhaus/beim Arzt war
- Alle Diagnosen ausführlich in Alltagssprache erklären
- Untersuchungsergebnisse, Laborwerte, Bildgebung detailliert übersetzen
- Alle Medikamente, Therapien und deren Zweck erklären
- Termine, Nachkontrollen, Warnzeichen hervorheben
- Konkrete Handlungsempfehlungen für den Alltag""",
            
            "laborbefund": """

## Spezielle Dokumenttypen

### Laborberichte:
- Werte mit Normalbereich vergleichen
- Bedeutung von Abweichungen erklären
- Zusammenhang zum Gesundheitszustand herstellen

### Spezifische Anweisungen für Laborbefunde:
- Erklärung, welche Blutwerte untersucht wurden und warum
- Status jedes Wertes (normal, erhöht, erniedrigt) klar benennen
- Jeden einzelnen Laborwert mit Normalbereich und Bedeutung erklären
- Was auffällige Werte für die Gesundheit bedeuten
- Welche Werte besondere Aufmerksamkeit brauchen
- Was bei auffälligen Werten zu tun ist""",
            
            "radiologie": """

## Spezielle Dokumenttypen

### Befundbericht (Radiologie):
- Detaillierte Erklärung der Untersuchungsmethode
- Verständliche Darstellung der Ergebnisse
- Bedeutung der Befunde für den Patienten

### Spezifische Anweisungen für Radiologie-Befunde:
- Welche Bildgebung wurde gemacht und warum
- Alle Beobachtungen in einfacher Sprache beschreiben
- Anatomische Strukturen und deren Zustand genau erklären
- Was die Befunde für die Gesundheit bedeuten
- Auffälligkeiten oder Normalwerte hervorheben
- Weitere Untersuchungen oder Behandlungen""",
            
            "pathologie": """

## Spezielle Dokumenttypen

### Befundbericht (Pathologie):
- Detaillierte Erklärung der Untersuchungsmethode
- Verständliche Darstellung der Ergebnisse
- Bedeutung der Befunde für den Patienten

### Spezifische Anweisungen für Pathologie-Befunde:
- Einfühlsam erklären, welches Gewebe untersucht wurde
- Alle Ergebnisse verständlich und beruhigend formulieren
- Zellveränderungen und Eigenschaften in Alltagssprache
- Was die Befunde für Behandlung und Prognose bedeuten
- Besonders relevante Informationen sensibel vermitteln
- Behandlungsoptionen und weitere Maßnahmen""",
            
            "entlassungsbrief": """

## Spezielle Dokumenttypen

### Entlassungsbrief:
- Zusammenfassung des Krankenhausaufenthalts
- Klare Darstellung der weiteren Maßnahmen
- Medikamentenplan verständlich erklären

### Spezifische Anweisungen für Entlassungsbriefe:
- Grund und Verlauf des Krankenhausaufenthalts
- Was während der Behandlung gemacht wurde
- Aktuelle Gesundheitssituation zum Entlassungszeitpunkt
- Alle Medikamente mit Dosierung und Zweck erklären
- Verhalten zuhause und wichtige Termine
- Warnzeichen, bei denen sofort ein Arzt kontaktiert werden sollte"""
        }
        
        # Füge Übersetzungsbeispiele hinzu
        translation_examples = """

## Übersetzungsbeispiele

### Standardformulierungen:
- "Pat. zeigt keine Auffälligkeiten" → "Bei Ihnen wurde nichts Ungewöhnliches festgestellt"
- "Auskultatorisch unauffällig" → "Beim Abhören von Herz und Lunge war alles normal"
- "Therapie mit ASS 100mg 1-0-0" → "Behandlung mit Aspirin 100mg - eine Tablette morgens"
- "V.a. Pneumonie" → "Verdacht auf Lungenentzündung"
- "Z.n. Appendektomie 2019" → "Blinddarm wurde 2019 entfernt"

### Fachbegriffe:
- "Hypertonie" → "Bluthochdruck (dauerhaft erhöhter Blutdruck)"
- "Diabetes mellitus Typ 2" → "Zuckerkrankheit Typ 2 (Blutzucker ist zu hoch)"
- "Koronare Herzkrankheit" → "Verengung der Herzkranzgefäße (Blutgefäße, die das Herz versorgen)"
- "Gastroenteritis" → "Magen-Darm-Entzündung (Durchfall und Erbrechen)"

### Laborwerte:
- "Hb 12,5 g/dl" → "Hämoglobin (roter Blutfarbstoff): 12,5 - leicht erniedrigt"
- "Leukos 11.000/µl" → "Weiße Blutkörperchen: 11.000 - leicht erhöht (normale Abwehrreaktion)"
- "CRP erhöht" → "Entzündungswert im Blut ist erhöht\""""

        instruction = base_instruction + output_format
        if doc_type in specific_instructions:
            instruction += specific_instructions[doc_type]
        instruction += translation_examples
        
        return f"""{instruction}

## Qualitätskontrolle

Vor der Ausgabe prüfe:
- [ ] Alle medizinischen Informationen sind erhalten
- [ ] Keine neuen Informationen wurden hinzugefügt
- [ ] Alle Fachbegriffe sind erklärt
- [ ] Der Text ist für Laien verständlich
- [ ] Die Struktur ist logisch und übersichtlich
- [ ] Unsicherheiten sind markiert
- [ ] Der Hinweis auf ärztliche Rücksprache ist vorhanden

## Abschlusshinweis

Füge IMMER am Ende hinzu:

"**Rechtlicher Hinweis:** Diese Übersetzung dient ausschließlich Ihrem besseren Verständnis der medizinischen Unterlagen. Sie stellt keine medizinische Beratung dar und ersetzt nicht das Gespräch mit Ihrem behandelnden Arzt. Alle medizinischen Entscheidungen sollten nur in Absprache mit qualifiziertem medizinischem Fachpersonal getroffen werden. Bei Notfällen wählen Sie bitte den Notruf 112."

ORIGINAL MEDIZINISCHER TEXT:
{text}

EINFACHE ÜBERSETZUNG:"""
    
    async def _generate_response(self, prompt: str, model: str) -> str:
        """Generiert Antwort von Ollama"""
        try:
            # Erst versuchen, verfügbare Modelle zu laden, falls das angegebene Modell nicht existiert
            if model not in await self.list_models():
                print(f"⚠️ Modell {model} nicht verfügbar, verwende Fallback...")
                available_models = await self.list_models()
                
                # Fallback-Logik: Bevorzuge Mistral-Nemo, dann andere
                fallback_models = [
                    "mistral-nemo:latest", "llama3.2:latest", "llama3.1", 
                    "mistral:7b", "deepseek-r1:7b", "gemma3:27b"
                ]
                
                for fallback in fallback_models:
                    if fallback in available_models:
                        model = fallback
                        print(f"✅ Verwende Fallback-Modell: {model}")
                        break
                else:
                    # Wenn kein Fallback gefunden, nimm das erste verfügbare Modell
                    if available_models:
                        model = available_models[0]
                        print(f"✅ Verwende erstes verfügbares Modell: {model}")
                    else:
                        return "Fehler: Keine Modelle verfügbar"
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                payload = {
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.3,  # Niedrig für konsistente medizinische Übersetzungen
                        "top_p": 0.9,
                        "top_k": 40,
                        "num_predict": 3000  # Längere Antworten für ausführliche Erklärungen
                    }
                }
                
                print(f"🤖 Generiere mit Modell: {model}")
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json=payload
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return result.get("response", "Keine Antwort erhalten").strip()
                else:
                    print(f"❌ Ollama API Error: {response.status_code} - {response.text}")
                    return f"Fehler bei der Ollama-Anfrage: {response.status_code}"
                    
        except Exception as e:
            print(f"❌ Ollama-Generation Fehler: {e}")
            return f"Fehler bei der KI-Übersetzung: {str(e)}"
    
    async def _evaluate_translation_quality(self, original: str, translated: str) -> float:
        """Bewertet Qualität der Übersetzung"""
        if not translated or translated.startswith("Fehler"):
            return 0.0
        
        confidence = 0.5  # Basis-Vertrauen
        
        # Länge der Übersetzung
        if len(translated) > 100:
            confidence += 0.1
        if len(translated) > 500:
            confidence += 0.1
        
        # Verhältnis Original zu Übersetzung (sollte nicht zu stark abweichen)
        length_ratio = len(translated) / max(len(original), 1)
        if 0.5 <= length_ratio <= 2.0:
            confidence += 0.1
        
        # Einfache Sprache Indikatoren
        simple_indicators = [
            "das bedeutet", "einfach gesagt", "vereinfacht", 
            "das heißt", "mit anderen worten"
        ]
        translated_lower = translated.lower()
        found_indicators = sum(1 for indicator in simple_indicators if indicator in translated_lower)
        confidence += min(found_indicators * 0.05, 0.2)
        
        # Medizinische Fachbegriffe sollten reduziert sein
        medical_terms = [
            "pathologie", "histologie", "maligne", "benigne",
            "ätiologie", "therapeutisch", "diagnostisch"
        ]
        original_terms = sum(1 for term in medical_terms if term in original.lower())
        translated_terms = sum(1 for term in medical_terms if term in translated_lower)
        
        if original_terms > 0:
            reduction_rate = 1 - (translated_terms / original_terms)
            confidence += reduction_rate * 0.1
        
        return min(confidence, 1.0)
    
    async def _evaluate_language_translation_quality(self, original: str, translated: str) -> float:
        """Bewertet Qualität der Sprachübersetzung"""
        if not translated or translated.startswith("Fehler"):
            return 0.0
        
        confidence = 0.6  # Basis-Vertrauen höher als bei medizinischer Vereinfachung
        
        # Länge der Übersetzung sollte ähnlich dem Original sein
        if len(translated) > 50:
            confidence += 0.1
        
        # Verhältnis Original zu Übersetzung
        length_ratio = len(translated) / max(len(original), 1)
        if 0.7 <= length_ratio <= 1.5:
            confidence += 0.1
        
        # Struktur-Elemente sollten erhalten bleiben (Emojis)
        emoji_pattern = r'[😀-🿿]|[\U0001F300-\U0001F5FF]|[\U0001F600-\U0001F64F]|[\U0001F680-\U0001F6FF]|[\U0001F700-\U0001F77F]|[\U0001F780-\U0001F7FF]|[\U0001F800-\U0001F8FF]|[\U00002600-\U000027BF]'
        original_emojis = len(re.findall(emoji_pattern, original))
        translated_emojis = len(re.findall(emoji_pattern, translated))
        
        if original_emojis > 0:
            emoji_retention = min(translated_emojis / original_emojis, 1.0)
            confidence += emoji_retention * 0.1
        
        # Text sollte nicht zu viele englische Wörter enthalten (außer bei englischer Zielsprache)
        english_words = ["the", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by"]
        english_count = sum(1 for word in english_words if word in translated.lower())
        if english_count < 3:  # Weniger englische Wörter ist besser
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    async def generate_streaming(
        self, 
        prompt: str, 
        model: str = "mistral-nemo:latest"
    ) -> AsyncGenerator[str, None]:
        """Streaming-Generation für Live-Updates"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                payload = {
                    "model": model,
                    "prompt": prompt,
                    "stream": True,
                    "options": {
                        "temperature": 0.3,
                        "top_p": 0.9,
                        "top_k": 40
                    }
                }
                
                async with client.stream(
                    "POST", 
                    f"{self.base_url}/api/generate",
                    json=payload
                ) as response:
                    async for chunk in response.aiter_lines():
                        if chunk:
                            try:
                                data = json.loads(chunk)
                                if "response" in data:
                                    yield data["response"]
                                if data.get("done", False):
                                    break
                            except json.JSONDecodeError:
                                continue
                                
        except Exception as e:
            yield f"Streaming-Fehler: {str(e)}"
    
    async def translate_to_language(
        self,
        simplified_text: str,
        target_language: SupportedLanguage,
        model: str = "mannix/llamax3-8b-alpaca:latest"
    ) -> tuple[str, float]:
        """
        Übersetzt vereinfachten Text in eine andere Sprache
        
        Args:
            simplified_text: Der bereits vereinfachte Text
            target_language: Die Zielsprache
            model: Das zu verwendende Modell
            
        Returns:
            tuple[str, float]: (translated_text, confidence)
        """
        try:
            language_name = LANGUAGE_NAMES.get(target_language, target_language.value)
            
            prompt = self._get_language_translation_prompt(simplified_text, target_language, language_name)
            
            # Übersetzung durchführen
            translated_text = await self._generate_response(prompt, model)
            
            # Qualität bewerten
            confidence = await self._evaluate_language_translation_quality(simplified_text, translated_text)
            
            return translated_text, confidence
            
        except Exception as e:
            print(f"❌ Sprachübersetzung fehlgeschlagen: {e}")
            return f"Fehler bei der Sprachübersetzung: {str(e)}", 0.0

    def _get_language_translation_prompt(self, text: str, target_language: SupportedLanguage, language_name: str) -> str:
        """Erstellt Prompt für Sprachübersetzung"""
        
        return f"""Du bist ein professioneller medizinischer Übersetzer, der bereits vereinfachte medizinische Texte in andere Sprachen übersetzt.

AUFGABE:
- Übersetze den folgenden bereits vereinfachten medizinischen Text in {language_name} ({target_language.value})
- Behalte die einfache, verständliche Sprache bei
- Übersetze alle medizinischen Begriffe korrekt und angemessen
- Behalte die Struktur mit Emojis und Überschriften bei
- Stelle sicher, dass der Text für Patienten verständlich bleibt

WICHTIGE REGELN:
- Verwende einfache, klare Sprache in der Zielsprache
- Behalte medizinische Genauigkeit bei
- Übersetze Emojis und Struktur-Elemente nicht - behalte sie bei
- Falls ein medizinischer Begriff keine direkte Übersetzung hat, erkläre ihn in Klammern
- Stelle sicher, dass der übersetzte Text genauso verständlich ist wie das Original

ORIGINAL TEXT (bereits vereinfacht):
{text}

ÜBERSETZUNG IN {language_name.upper()}:""" 