import httpx
import json
import asyncio
import os
from typing import Optional, Dict, Any, AsyncGenerator
import re

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
                "entlassung", "aufnahme", "diagnose", "therapie",
                "empfehlung", "weiterbehandlung", "hochachtungsvoll"
            ],
            "laborbefund": [
                "laborwerte", "blutwerte", "referenzbereich", 
                "hämatologie", "klinische chemie", "mg/dl", "mmol/l",
                "erhöht", "erniedrigt", "normal"
            ],
            "radiologie": [
                "röntgen", "ct", "mrt", "ultraschall", "befund",
                "darstellung", "kontrastmittel", "auffällig",
                "unauffällig", "verdacht"
            ],
            "pathologie": [
                "histologie", "biopsie", "gewebeprobe", "tumor",
                "maligne", "benigne", "metastase", "grading"
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
        
        base_instruction = """Du bist ein erfahrener medizinischer Übersetzer, der komplexe medizinische Texte vollständig und präzise in patientenfreundliche Sprache übersetzt.

ZENTRALE AUFGABE:
- Erstelle eine VOLLSTÄNDIGE und DETAILLIERTE Zusammenfassung ohne Details auszulassen
- Übersetze JEDEN medizinischen Fachbegriff in einfache deutsche Sprache
- Strukturiere die Übersetzung klar und übersichtlich mit Zwischenüberschriften

STRUKTUR DER ÜBERSETZUNG:
📋 **ZUSAMMENFASSUNG**
[Kurze, beruhigende Einleitung über das Dokument]

🏥 **HAUPTBEFUNDE**
[Alle wichtigen Diagnosen und Befunde in einfacher Sprache]

📊 **DETAILS**
[Alle spezifischen Werte, Messungen und Beobachtungen erklärt]

💊 **BEHANDLUNG & EMPFEHLUNGEN**
[Alle vorgeschlagenen Therapien und nächste Schritte]

⚠️ **WICHTIGE PUNKTE**
[Besonders bedeutsame Informationen hervorgehoben]

ÜBERSETZUNGSREGELN:
- Verwende eine beruhigende, positive aber ehrliche Sprache
- Erkläre JEDEN medizinischen Begriff sofort in Klammern
- Verwende Emojis für bessere Struktur und Lesbarkeit
- Lasse KEINE Information aus dem Original weg
- Erkläre komplexe Zusammenhänge Schritt für Schritt
- Verwende Metaphern und Vergleiche für besseres Verständnis"""
        
        specific_instructions = {
            "arztbrief": """
SPEZIELLE ANWEISUNGEN FÜR ARZTBRIEFE:
📋 **ZUSAMMENFASSUNG**: Erkläre freundlich, warum der Patient im Krankenhaus/beim Arzt war
🏥 **HAUPTBEFUNDE**: Alle Diagnosen ausführlich in Alltagssprache erklären
📊 **DETAILS**: Untersuchungsergebnisse, Laborwerte, Bildgebung detailliert übersetzen
💊 **BEHANDLUNG**: Alle Medikamente, Therapien und deren Zweck erklären
⚠️ **WICHTIGE PUNKTE**: Termine, Nachkontrollen, Warnzeichen hervorheben
🏠 **ZUHAUSE**: Konkrete Handlungsempfehlungen für den Alltag""",
            
            "laborbefund": """
SPEZIELLE ANWEISUNGEN FÜR LABORBEFUNDE:
📋 **ZUSAMMENFASSUNG**: Erklärung, welche Blutwerte untersucht wurden und warum
🏥 **HAUPTBEFUNDE**: Status jedes Wertes (normal, erhöht, erniedrigt) klar benennen
📊 **DETAILS**: Jeden einzelnen Laborwert mit Normalbereich und Bedeutung erklären
💊 **BEDEUTUNG**: Was auffällige Werte für die Gesundheit bedeuten
⚠️ **WICHTIGE PUNKTE**: Welche Werte besondere Aufmerksamkeit brauchen
🏠 **NÄCHSTE SCHRITTE**: Was bei auffälligen Werten zu tun ist""",
            
            "radiologie": """
SPEZIELLE ANWEISUNGEN FÜR RADIOLOGIE-BEFUNDE:
📋 **ZUSAMMENFASSUNG**: Welche Bildgebung wurde gemacht und warum
🏥 **HAUPTBEFUNDE**: Alle Beobachtungen in einfacher Sprache beschreiben
📊 **DETAILS**: Anatomische Strukturen und deren Zustand genau erklären
💊 **BEDEUTUNG**: Was die Befunde für die Gesundheit bedeuten
⚠️ **WICHTIGE PUNKTE**: Auffälligkeiten oder Normalwerte hervorheben
🏠 **NÄCHSTE SCHRITTE**: Weitere Untersuchungen oder Behandlungen""",
            
            "pathologie": """
SPEZIELLE ANWEISUNGEN FÜR PATHOLOGIE-BEFUNDE:
📋 **ZUSAMMENFASSUNG**: Einfühlsam erklären, welches Gewebe untersucht wurde
🏥 **HAUPTBEFUNDE**: Alle Ergebnisse verständlich und beruhigend formulieren  
📊 **DETAILS**: Zellveränderungen und Eigenschaften in Alltagssprache
💊 **BEDEUTUNG**: Was die Befunde für Behandlung und Prognose bedeuten
⚠️ **WICHTIGE PUNKTE**: Besonders relevante Informationen sensibel vermitteln
🏠 **NÄCHSTE SCHRITTE**: Behandlungsoptionen und weitere Maßnahmen"""
        }
        
        instruction = base_instruction
        if doc_type in specific_instructions:
            instruction += specific_instructions[doc_type]
        
        return f"""{instruction}

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