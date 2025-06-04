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
        
        base_instruction = """Du bist ein hochspezialisierter medizinischer Übersetzer. Deine Aufgabe ist es, medizinische Dokumente vollständig und präzise in patientenfreundliche Sprache zu übersetzen.

WICHTIGE REGELN:
- Übersetze NUR was im Dokument steht, füge NICHTS hinzu
- Lasse KEINE medizinische Information weg
- Erkläre JEDEN Fachbegriff sofort in Klammern
- Verwende einfache, kurze Sätze
- Markiere Unsicherheiten mit [?]
- Bei unklaren Begriffen: "Bitte klären Sie dies mit Ihrem Arzt"

ÜBERSETZUNGSFORMAT:
Erstelle eine strukturierte Übersetzung mit folgenden Abschnitten:

# [DOKUMENTTYP] - Verständliche Fassung

## Wichtigste Information
[Ein Satz über das Wesentliche]

## Was wurde untersucht/behandelt?
[Grund des Arztbesuchs in einfachen Worten]

## Was wurde festgestellt?
### Hauptbefunde:
• [Jeder Befund in einfacher Sprache]
  → Was bedeutet das? [Kurze Erklärung]

### Diagnosen:
• [Deutsche Bezeichnung]
  → Fachbegriff: [Original]
  → Erklärung: [Was ist das genau?]

## Behandlung/Medikamente
• [Medikament/Maßnahme]
  → Zweck: [Wofür?]
  → Wichtig zu wissen: [Besonderheiten]

## Was passiert als Nächstes?
• [Nächste Schritte]
• [Kontrolltermine]
• [Verhaltensempfehlungen]

## Wörterbuch der Fachbegriffe
• **[Fachbegriff]**: [Verständliche Erklärung]

## Wichtiger Hinweis
Diese Übersetzung ersetzt nicht das Gespräch mit Ihrem Arzt. Bei Fragen wenden Sie sich an Ihr Behandlungsteam.

**Rechtlicher Hinweis:** Diese Übersetzung dient nur Ihrem Verständnis und stellt keine medizinische Beratung dar. Bei Notfällen wählen Sie 112."""
        
        # Einfache dokumenttyp-spezifische Anweisungen
        specific_instructions = {
            "arztbrief": "Fokussiere dich besonders auf Diagnosen und Therapieempfehlungen. Erkläre alle Medikamente und nächste Schritte.",
            "laborbefund": "Erkläre jeden Laborwert mit seinem Normalbereich. Sage klar, ob Werte normal, erhöht oder erniedrigt sind.",
            "radiologie": "Erkläre die Untersuchungsmethode und was die Bilder zeigen. Übersetze anatomische Begriffe.",
            "pathologie": "Sei einfühlsam bei Gewebeveränderungen. Erkläre Befunde verständlich aber nicht beunruhigend.",
            "entlassungsbrief": "Fasse den Krankenhausaufenthalt zusammen. Erkläre alle Medikamente und Nachsorge-Termine."
        }
        
        instruction = base_instruction
        if doc_type in specific_instructions:
            instruction += f"\n\nSPEZIELL FÜR DIESEN DOKUMENTTYP: {specific_instructions[doc_type]}"
        
        return f"""{instruction}

ORIGINAL MEDIZINISCHER TEXT:
{text}

ÜBERSETZUNG IN EINFACHER SPRACHE:"""
    
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