import httpx
import json
import asyncio
import os
from typing import Optional, Dict, Any, AsyncGenerator, Tuple
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
        model: str = "gpt-oss:20b"  # MANDATORY: Always use gpt-oss:20b for document analysis
    ) -> tuple[str, str, float, str]:
        """
        Übersetzt medizinischen Text in einfache Sprache
        
        Returns:
            tuple[str, str, float, str]: (translated_text, doc_type, confidence, cleaned_original)
        """
        try:
            # SCHRITT 1: Intelligente KI-basierte Vorverarbeitung
            print("🧠 Schritt 1: KI extrahiert medizinisch relevante Informationen...")
            cleaned_text = await self._ai_preprocess_text(text, model)
            
            # SCHRITT 2: Hauptübersetzung - EINE universelle Methode für ALLE Dokumente
            print("🤖 Schritt 2: Übersetze in einfache Sprache...")
            prompt = self._get_universal_translation_prompt(cleaned_text)
            translated_text = await self._generate_response(prompt, model)
            
            # SCHRITT 3: Qualitätskontrolle - prüfe ob Übersetzung sinnvoll ist
            if not translated_text or len(translated_text) < 100:
                print("⚠️ Übersetzung zu kurz - versuche erneut...")
                # Vereinfachter Prompt für zweiten Versuch
                simple_prompt = f"""Übersetze diesen medizinischen Text in einfache, verständliche Sprache:

{cleaned_text}

Einfache Übersetzung:"""
                translated_text = await self._generate_response(simple_prompt, model)
            
            # SCHRITT 4: Qualität bewerten
            confidence = await self._evaluate_translation_quality(cleaned_text, translated_text)
            
            # Gebe zurück - "universal" als einheitlicher Dokumenttyp
            return translated_text, "universal", confidence, cleaned_text
            
        except Exception as e:
            print(f"❌ Übersetzung fehlgeschlagen: {e}")
            return f"Fehler bei der Übersetzung: {str(e)}", "error", 0.0, text
    
    async def _detect_document_type_DEPRECATED(self, text: str) -> str:
        """DEPRECATED - Nicht mehr verwendet, da alle Dokumente gleich behandelt werden"""
        return "universal"
    
    async def _detect_document_type(self, text: str) -> str:
        """Gibt immer 'universal' zurück - alle Dokumente werden gleich behandelt"""
        return "universal"
        
        # ALTE IMPLEMENTIERUNG ENTFERNT
        patterns = {
            # KATEGORIE 1: Arztbriefe (alle Arten von Briefen zwischen Ärzten)
            "arztbrief": [
                # Allgemeine Arztbriefe
                "sehr geehrte", "liebe kollegin", "lieber kollege",
                "mit freundlichen grüßen", "hochachtungsvoll", "gez.",
                # Entlassungsbriefe
                "entlassung", "entlassen", "krankenhausaufenthalt", "stationär",
                # Überweisungen
                "überweisung", "überweisen", "vorstellung", "konsil",
                # Therapieberichte
                "therapie", "behandlung", "medikation", "empfehlung",
                # Befundberichte
                "befund", "diagnose", "anamnese", "untersuchung",
                # Operationsberichte
                "operation", "op-bericht", "eingriff", "narkose"
            ],
            
            # KATEGORIE 2: Laborbefunde (alle Labor- und Messwerte)
            "laborbefund": [
                # Blutwerte
                "laborwerte", "blutwerte", "blutbild", "hämatologie",
                # Einheiten
                "mg/dl", "mmol/l", "µg/l", "u/l", "g/dl", "pg/ml",
                # Referenzbereiche
                "referenzbereich", "normalbereich", "norm", "referenz",
                # Bewertungen
                "erhöht", "erniedrigt", "normal", "pathologisch",
                # Spezielle Tests
                "hba1c", "cholesterin", "ldl", "hdl", "triglyceride",
                "kreatinin", "gfr", "tsh", "psa", "ck", "troponin",
                # Urinwerte
                "urin", "urinstatus", "urinkultur",
                # Mikrobiologie
                "bakterien", "keime", "resistenz", "antibiogramm"
            ],
            
            # KATEGORIE 3: Bildgebung (alle bildgebenden Verfahren)
            "bildgebung": [
                # Verfahren
                "röntgen", "ct", "mrt", "mri", "ultraschall", "sonographie",
                "szintigraphie", "pet", "angiographie", "mammographie",
                # Befundbeschreibung
                "darstellung", "kontrastmittel", "schnittbild", "aufnahme",
                "auffällig", "unauffällig", "verdacht", "hinweis",
                # Anatomie
                "thorax", "abdomen", "schädel", "wirbelsäule", "gelenk",
                # Pathologie in Bildern
                "tumor", "metastase", "zyste", "knoten", "herd",
                "fraktur", "läsion", "infiltrat", "erguss"
            ]
        }
        
        scores = {}
        for doc_type, keywords in patterns.items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            scores[doc_type] = score
        
        # Höchsten Score finden - mit niedrigerer Schwelle für bessere Erkennung
        if scores:
            detected = max(scores, key=scores.get)
            if scores[detected] >= 1:  # Nur 1 Treffer nötig
                return detected
        
        # Fallback auf "arztbrief" statt "allgemein" für konsistenteres Format
        return "arztbrief"  # Standard-Kategorie
    
    def _get_universal_translation_prompt(self, text: str) -> str:
        """Erstellt EINEN universellen Prompt für ALLE medizinischen Dokumente"""
        
        base_instruction = """Du bist ein hochspezialisierter medizinischer Übersetzer. Deine Aufgabe ist es, medizinische Dokumente vollständig und präzise in patientenfreundliche Sprache zu übersetzen.

KRITISCHE ANTI-HALLUZINATIONS-REGELN:
- ⛔ FÜGE NICHTS HINZU was nicht explizit im Dokument steht
- ⛔ KEINE Vermutungen, Annahmen oder "könnte sein" Aussagen
- ⛔ KEINE allgemeinen medizinischen Ratschläge die nicht im Text stehen
- ⛔ KEINE zusätzlichen Erklärungen außer direkte Übersetzung von Fachbegriffen
- ✅ Übersetze NUR was wörtlich im Dokument steht
- ✅ Lasse KEINE medizinische Information weg
- ✅ Erkläre Fachbegriffe kurz in Klammern (nur Definition, keine Zusatzinfos)
- ✅ Spreche den Patienten DIREKT an (nutze "Sie", "Ihr", "Ihnen")
- ✅ Bei Unklarheiten: markiere mit [unklar] statt zu interpretieren
- ✅ KEINE Behandlungsempfehlungen die nicht im Original stehen

SPRACHLICHE RICHTLINIEN:

VERWENDE:
- Kurze Hauptsätze (maximal 15-20 Wörter)
- Aktive Formulierungen ("Der Arzt untersucht" statt "Es wird untersucht")
- Konkrete Begriffe ("Blutdruck messen" statt "Blutdruckkontrolle durchführen")
- Alltagssprache ("Herz" zusätzlich zu "kardial")
- Vergleiche aus dem Alltag (z.B. "groß wie eine Walnuss")
- Zahlen ausschreiben wenn verständlicher ("zwei Mal täglich" statt "2x tägl.")
- Direkte Ansprache ("Sie waren", "Ihr Blutdruck", "Sie sollen")

VERMEIDE:
- Verschachtelte Nebensätze
- Passive Konstruktionen
- Abstrakte Formulierungen
- Unaufgelöste Abkürzungen
- Fachsprache ohne Erklärung
- Mehrdeutige Aussagen
- Unpersönliche Formulierungen wie "Der Patient"

EINHEITLICHES ÜBERSETZUNGSFORMAT FÜR ALLE DOKUMENTTYPEN:

# 📋 Ihre medizinische Dokumentation - Einfach erklärt

## 🎯 Das Wichtigste zuerst
[Die zentrale Information in einem klaren Satz]

## 📊 Zusammenfassung
### Was wurde gemacht?
• [Untersuchung/Behandlung in einfachen Worten]
• [Zeitraum/Datum wenn vorhanden]

### Was wurde gefunden?
• [Hauptbefund 1 in einfacher Sprache]
  → Bedeutung: [Was heißt das für Sie?]
• [Hauptbefund 2 in einfacher Sprache]
  → Bedeutung: [Was heißt das für Sie?]

## 🏥 Ihre Diagnosen
• [Diagnose in Alltagssprache]
  → Medizinisch: [Fachbegriff]
  → Erklärung: [Was ist das genau?]

## 💊 Behandlung & Medikamente
• [Medikament/Behandlung]
  → Wofür: [Zweck]
  → Einnahme: [Wie und wann]
  → Wichtig: [Besonderheiten/Nebenwirkungen]

## ✅ Ihre nächsten Schritte
• [Was Sie tun sollen]
• [Termine die anstehen]
• [Worauf Sie achten müssen]

## 📖 Fachbegriffe verstehen
• **[Begriff 1]**: [Einfache Erklärung]
• **[Begriff 2]**: [Einfache Erklärung]

## ⚠️ Wichtige Hinweise
• Diese Übersetzung hilft Ihnen, Ihre Unterlagen zu verstehen
• Besprechen Sie alle Fragen mit Ihrem Arzt
• Bei Notfällen: 112 anrufen

---
*Übersetzung erstellt am: [Datum]*"""
        
        # UNIVERSELLE Anleitung für ALLE medizinischen Dokumente
        universal_instruction = """
DIESES DOKUMENT KANN ENTHALTEN:
- Arztbriefe, Entlassungsbriefe, Befundberichte
- Laborwerte und Blutwerte
- Bildgebungsbefunde (Röntgen, MRT, CT, Ultraschall)
- Pathologiebefunde
- Medikationspläne
- Kombinationen aus allem oben genannten

BEHANDLE JEDEN INHALT ANGEMESSEN:
- Bei Laborwerten: Erkläre Wert → Normalbereich → Bedeutung
- Bei Diagnosen: Übersetze Fachbegriffe in Alltagssprache
- Bei Medikamenten: Erkläre Zweck und Einnahme
- Bei Bildgebung: Beschreibe was untersucht wurde und was gefunden wurde
- Bei Empfehlungen: Mache klar was der Patient tun soll

Nutze IMMER das einheitliche Format oben, egal welche Inhalte das Dokument hat."""
        
        instruction = base_instruction + universal_instruction
        
        return f"""{instruction}

ORIGINAL MEDIZINISCHER TEXT:
{text}

ÜBERSETZUNG IN EINFACHER SPRACHE:"""
    
    async def _generate_response(self, prompt: str, model: str) -> str:
        """Generiert Antwort von Ollama"""
        try:
            # MANDATORY: Ensure gpt-oss:20b is used for document analysis and translation
            primary_model = "gpt-oss:20b"
            
            # Check if primary model is available
            available_models = await self.list_models()
            
            # For medical document translation, ALWAYS use gpt-oss:20b if available
            if primary_model in available_models:
                model = primary_model
                print(f"✅ Using mandatory model for document analysis: {model}")
            elif model not in available_models:
                print(f"⚠️ CRITICAL: Primary model {primary_model} not available!")
                print(f"⚠️ Model {model} also not available, trying fallbacks...")
                
                # Fallback-Logik: Only use if gpt-oss:20b is truly unavailable
                fallback_models = [
                    "mistral-nemo:latest", "llama3.2:latest", "llama3.1", 
                    "mistral:7b", "deepseek-r1:7b", "gemma3:27b"
                ]
                
                for fallback in fallback_models:
                    if fallback in available_models:
                        model = fallback
                        print(f"⚠️ Using fallback model (gpt-oss:20b not available): {model}")
                        break
                else:
                    # Wenn kein Fallback gefunden, nimm das erste verfügbare Modell
                    if available_models:
                        model = available_models[0]
                        print(f"⚠️ Using first available model: {model}")
                    else:
                        return "ERROR: No models available. Please ensure gpt-oss:20b is loaded."
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                payload = {
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.3,  # Etwas höher für natürlichere Sprache
                        "top_p": 0.7,  # Ausgewogener
                        "top_k": 20,  # Mehr Varianz erlaubt
                        "num_predict": 4000,  # Längere Antworten für vollständige Übersetzung
                        "repeat_penalty": 1.1,  # Leicht gegen Wiederholungen
                        "seed": 42  # Für reproduzierbare Ergebnisse
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
        model: str = "gpt-oss:20b"  # MANDATORY: Default to gpt-oss:20b
    ) -> AsyncGenerator[str, None]:
        """Streaming-Generation für Live-Updates"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                payload = {
                    "model": model,
                    "prompt": prompt,
                    "stream": True,
                    "options": {
                        "temperature": 0.1,  # SEHR konservativ
                        "top_p": 0.5,
                        "top_k": 10,
                        "repeat_penalty": 1.2,
                        "seed": 42
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
        model: str = "gpt-oss:20b"  # MANDATORY: Use gpt-oss:20b for all translations
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

    async def _ai_preprocess_text(self, text: str, model: str) -> str:
        """Nutzt KI um medizinisch relevante Informationen zu extrahieren"""
        
        preprocess_prompt = f"""Du bist ein medizinischer Dokumentenverarbeiter. Deine Aufgabe ist es, aus dem folgenden Text NUR die medizinisch relevanten Informationen zu extrahieren.

WICHTIGE REGELN:
- BEHALTE: Alle Diagnosen, Symptome, Behandlungen, Medikamente, Untersuchungsergebnisse, Laborwerte
- BEHALTE: Medizinisch relevante Daten (OP-Termine, Untersuchungsdaten, Behandlungszeiträume)
- BEHALTE: Dosierungen, Mengenangaben, medizinische Messwerte
- BEHALTE: Empfehlungen, Anweisungen, nächste Schritte

- ENTFERNE NUR wenn NICHT medizinisch relevant:
  • Vollständige Adressen (außer Krankenhaus/Praxis-Name)
  • Telefonnummern und E-Mails
  • Patientennummern und Versicherungsnummern
  • Grußformeln und Unterschriften
  • Briefkopf-Formatierungen

- WICHTIG: Behalte Namen von Ärzten und medizinischen Einrichtungen
- WICHTIG: Behalte alle Zahlen die medizinische Bedeutung haben könnten

ORIGINALTEXT:
{text}

EXTRAHIERTER MEDIZINISCHER INHALT (vollständig, nur ohne irrelevante Formatierung):"""
        
        cleaned_text = await self._generate_response(preprocess_prompt, model)
        
        # Fallback wenn KI-Preprocessing fehlschlägt
        if not cleaned_text or cleaned_text.startswith("Fehler") or len(cleaned_text) < 50:
            print("⚠️ KI-Preprocessing fehlgeschlagen, verwende Originaltext")
            return text
        
        print(f"✅ Text intelligent bereinigt: {len(text)} → {len(cleaned_text)} Zeichen")
        return cleaned_text

    async def _preprocess_and_anonymize(self, text: str) -> Tuple[str, dict]:
        """Entfernt irrelevante persönliche Informationen für schnellere Verarbeitung"""
        removed_info = {
            "names": [],
            "addresses": [],
            "dates": [],
            "ids": []
        }
        
        cleaned_text = text
        
        # Entferne Adressen (Straßen, PLZ, Orte)
        address_patterns = [
            r'\b\d{5}\s+[A-Za-zäöüÄÖÜß\s]+\b',  # PLZ + Ort
            r'\b[A-Za-zäöüÄÖÜß]+straße\s+\d+[a-z]?\b',  # Straße + Hausnummer
            r'\b[A-Za-zäöüÄÖÜß]+weg\s+\d+[a-z]?\b',
            r'\b[A-Za-zäöüÄÖÜß]+platz\s+\d+[a-z]?\b',
            r'\b[A-Za-zäöüÄÖÜß]+allee\s+\d+[a-z]?\b'
        ]
        
        for pattern in address_patterns:
            matches = re.findall(pattern, cleaned_text, re.IGNORECASE)
            removed_info["addresses"].extend(matches)
            cleaned_text = re.sub(pattern, "[ADRESSE]", cleaned_text, flags=re.IGNORECASE)
        
        # Entferne Geburtsdaten und andere Datumsangaben (außer medizinisch relevante)
        date_pattern = r'\b\d{1,2}[.]\d{1,2}[.]\d{2,4}\b'
        dates = re.findall(date_pattern, cleaned_text)
        for date in dates:
            # Behalte medizinisch relevante Daten (z.B. OP-Termine, Untersuchungsdaten)
            if not any(keyword in cleaned_text[max(0, cleaned_text.find(date)-50):cleaned_text.find(date)+50].lower() 
                      for keyword in ['untersuchung', 'operation', 'op', 'eingriff', 'behandlung', 'termin', 'kontroll']):
                removed_info["dates"].append(date)
                cleaned_text = cleaned_text.replace(date, "[DATUM]")
        
        # Entferne Patientennummern, Versicherungsnummern, etc.
        id_patterns = [
            r'\b[A-Z]\d{9,12}\b',  # Versicherungsnummer
            r'\bPat[.]?-?Nr[.]?:?\s*\d+\b',  # Patientennummer
            r'\bFallnr[.]?:?\s*\d+\b',  # Fallnummer
            r'\bAktenzeichen:?\s*[A-Z0-9/-]+\b'
        ]
        
        for pattern in id_patterns:
            matches = re.findall(pattern, cleaned_text, re.IGNORECASE)
            removed_info["ids"].extend(matches)
            cleaned_text = re.sub(pattern, "[ID]", cleaned_text, flags=re.IGNORECASE)
        
        # Entferne Telefonnummern
        phone_pattern = r'\b(?:\+49|0)[1-9]\d{1,14}\b'
        phones = re.findall(phone_pattern, cleaned_text)
        if phones:
            removed_info["phones"] = phones
            cleaned_text = re.sub(phone_pattern, "[TELEFON]", cleaned_text)
        
        # Entferne E-Mail-Adressen
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, cleaned_text)
        if emails:
            removed_info["emails"] = emails
            cleaned_text = re.sub(email_pattern, "[EMAIL]", cleaned_text)
        
        # Entferne Grußformeln und Unterschriften (nicht medizinisch relevant)
        greeting_patterns = [
            r'Mit freundlichen Grüßen[\s\S]{0,100}$',
            r'Hochachtungsvoll[\s\S]{0,100}$',
            r'gez\.[\s\S]{0,50}$',
            r'i\.A\.[\s\S]{0,50}$'
        ]
        
        for pattern in greeting_patterns:
            cleaned_text = re.sub(pattern, "", cleaned_text, flags=re.IGNORECASE)
        
        # Log was entfernt wurde
        total_removed = sum(len(v) if isinstance(v, list) else 0 for v in removed_info.values())
        if total_removed > 0:
            print(f"🧹 Entfernt: {total_removed} irrelevante Informationen für schnellere Verarbeitung")
            print(f"   Original: {len(text)} Zeichen → Bereinigt: {len(cleaned_text)} Zeichen")
            print(f"   Einsparung: {100 * (1 - len(cleaned_text)/len(text)):.1f}%")
        
        return cleaned_text, removed_info
    
    async def _validate_translation(self, original_text: str, translation: str, model: str) -> str:
        """Validiert die Übersetzung auf Halluzinationen und Fehler"""
        
        # Prüfe ob Übersetzung leer oder fehlerhaft ist
        if not translation or len(translation.strip()) < 50:
            print("⚠️ Übersetzung zu kurz oder leer, erstelle neue...")
            # Direkt neue Übersetzung versuchen
            simple_prompt = f"""Übersetze diesen medizinischen Text in einfache Sprache für Patienten:

{original_text[:2000]}

Verständliche Übersetzung:"""
            return await self._generate_response(simple_prompt, model)
            
        # Prüfe auf typische Fehlermeldungen
        error_indicators = [
            "ich sehe leider keine",
            "bitte senden sie mir",
            "kann ich nicht",
            "fehler bei",
            "error:",
            "keine übersetzung",
            "nicht vorhanden",
            "korrigierte übersetzung:",  # Manchmal gibt KI nur diesen Header zurück
            "gib die übersetzung zurück"
        ]
        
        translation_lower = translation.lower()
        for indicator in error_indicators:
            if indicator in translation_lower and len(translation) < 200:
                print(f"⚠️ Fehlerhafte Antwort erkannt: '{indicator}'")
                # Neuer vereinfachter Versuch
                return await self._generate_response(
                    f"Übersetze in einfache Sprache:\n{original_text[:2000]}", 
                    model
                )
        
        # Wenn Übersetzung gut aussieht, direkt zurückgeben ohne weitere Validierung
        # (Validierung verursacht oft Probleme)
        return translation
        
        # ALTE VALIDIERUNG ENTFERNT - verursacht leere Outputs
        
        validated_text = await self._generate_response(validation_prompt, model)
        
        # Zusätzliche Sicherheitsprüfung: Entferne typische Halluzinations-Phrasen
        hallucination_phrases = [
            "könnte darauf hinweisen",
            "möglicherweise",
            "es ist anzunehmen",
            "vermutlich",
            "wahrscheinlich",
            "in der Regel",
            "üblicherweise",
            "oft",
            "häufig"
        ]
        
        # Prüfe ob diese Phrasen im Original vorkommen
        for phrase in hallucination_phrases:
            if phrase in validated_text.lower() and phrase not in original_text.lower():
                # Diese Phrase war nicht im Original - könnte Halluzination sein
                print(f"⚠️ Potenzielle Halluzination erkannt: '{phrase}'")
        
        return validated_text 