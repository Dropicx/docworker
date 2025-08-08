import httpx
import json
import asyncio
import os
import logging
from typing import Optional, Dict, Any, AsyncGenerator, Tuple
import re
from app.models.document import SupportedLanguage, LANGUAGE_NAMES
from app.services.ovh_client import OVHClient

# Setup logger
logger = logging.getLogger(__name__)

class OllamaClient:
    
    def __init__(self, base_url: Optional[str] = None, use_ovh_for_main: bool = True):
        # Container-zu-Container Kommunikation in Production
        if os.getenv("ENVIRONMENT") == "production":
            self.base_url = base_url or "http://ollama-gpu:11434"  # GPU instance only
        else:
            self.base_url = base_url or "http://localhost:7869"   # GPU instance only
            
        self.timeout = 300  # 5 Minuten Timeout
        
        # Model configuration from environment
        self.preprocessing_model = os.getenv("OLLAMA_PREPROCESSING_MODEL", "gpt-oss:20b")
        self.translation_model = os.getenv("OLLAMA_TRANSLATION_MODEL", "zongwei/gemma3-translator:4b")
        
        # OVH client for main processing
        self.use_ovh_for_main = use_ovh_for_main
        if self.use_ovh_for_main:
            self.ovh_client = OVHClient()
            logger.info("✅ OVH API client initialized for main processing")
        
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
        model: str = None  # Will use configured models
    ) -> tuple[str, str, float, str]:
        """
        Übersetzt medizinischen Text in einfache Sprache
        
        Returns:
            tuple[str, str, float, str]: (translated_text, doc_type, confidence, cleaned_original)
        """
        try:
            # SCHRITT 1: Intelligente KI-basierte Vorverarbeitung mit lokalem gpt-oss:20b
            print(f"🧠 Schritt 1: KI extrahiert medizinisch relevante Informationen mit {self.preprocessing_model}...")
            cleaned_text = await self._ai_preprocess_text(text, self.preprocessing_model)
            
            # SCHRITT 2: Hauptübersetzung - Verwende OVH API wenn aktiviert
            if self.use_ovh_for_main and self.ovh_client:
                print(f"🤖 Schritt 2: Übersetze mit OVH Meta-Llama-3.3-70B-Instruct")
                translated_text, doc_type, confidence, _ = await self.ovh_client.translate_medical_document(cleaned_text)
                print(f"✅ Hauptübersetzung erfolgreich mit OVH API")
            else:
                # Fallback auf lokales Modell wenn OVH nicht verfügbar
                print(f"🤖 Schritt 2: Übersetze in einfache Sprache mit lokalem Model: {self.preprocessing_model}")
                prompt = self._get_universal_translation_prompt(cleaned_text)
                translated_text = await self._generate_response(prompt, self.preprocessing_model)
                print(f"✅ Hauptübersetzung erfolgreich mit {self.preprocessing_model}")
                confidence = await self._evaluate_translation_quality(cleaned_text, translated_text)
            
            # SCHRITT 3: Qualitätskontrolle - prüfe ob Übersetzung sinnvoll ist
            if not translated_text or len(translated_text) < 100:
                print("⚠️ Übersetzung zu kurz - versuche erneut...")
                # Vereinfachter Prompt für zweiten Versuch
                simple_prompt = f"""Übersetze diesen medizinischen Text in einfache, verständliche Sprache:

{cleaned_text}

Einfache Übersetzung:"""
                if self.use_ovh_for_main and self.ovh_client:
                    translated_text = await self.ovh_client.process_medical_text(cleaned_text, simple_prompt)
                else:
                    translated_text = await self._generate_response(simple_prompt, self.preprocessing_model)
            
            # SCHRITT 4: Qualität bewerten wenn nicht bereits von OVH bewertet
            if not self.use_ovh_for_main or not self.ovh_client:
                confidence = await self._evaluate_translation_quality(cleaned_text, translated_text)
            
            # Gebe zurück - "universal" als einheitlicher Dokumenttyp
            return translated_text, "universal", confidence, cleaned_text
            
        except Exception as e:
            print(f"❌ Übersetzung fehlgeschlagen: {e}")
            return f"Fehler bei der Übersetzung: {str(e)}", "error", 0.0, text
    
    def _get_universal_translation_prompt(self, text: str) -> str:
        """Erstellt EINEN universellen Prompt für ALLE medizinischen Dokumente"""
        
        base_instruction = """Du bist ein hochspezialisierter medizinischer Übersetzer. Deine Aufgabe ist es, medizinische Dokumente vollständig und präzise in patientenfreundliche Sprache zu übersetzen.

KRITISCHE ANTI-HALLUZINATIONS-REGELN:
⛔ FÜGE NICHTS HINZU was nicht explizit im Dokument steht
⛔ KEINE Vermutungen, Annahmen oder "könnte sein" Aussagen
⛔ KEINE allgemeinen medizinischen Ratschläge die nicht im Text stehen
⛔ KEINE zusätzlichen Erklärungen außer direkte Übersetzung von Fachbegriffen
⛔ KEINE Verweise auf Anhänge ("siehe Anhang", "weitere Werte im Anhang") wenn diese nicht explizit im Text erwähnt werden
⛔ ERFINDE KEINE zusätzlichen Informationen die nicht da sind
⛔ KEINE Meta-Kommentare wie "Alle Angaben entsprechen dem Originaltext" oder "Diese Information stammt aus dem Dokument"
⛔ KEINE Hinweise darauf, dass du übersetzt oder dass dies eine Übersetzung ist
✅ Übersetze NUR was wörtlich im Dokument steht
✅ Lasse KEINE medizinische Information weg
✅ Erkläre Fachbegriffe kurz in Klammern (nur Definition, keine Zusatzinfos)
✅ Spreche den Patienten DIREKT an (nutze "Sie", "Ihr", "Ihnen")
✅ Bei Unklarheiten: markiere mit [unklar] statt zu interpretieren
✅ KEINE Behandlungsempfehlungen die nicht im Original stehen
✅ ERKLÄRE IMMER medizinische Codes (ICD, OPS, DRG, etc.) - nie nur auflisten!


SPRACHLICHE RICHTLINIEN:

VERWENDE:
Kurze Hauptsätze (maximal 15-20 Wörter)
Aktive Formulierungen ("Der Arzt untersucht" statt "Es wird untersucht")
Konkrete Begriffe ("Blutdruck messen" statt "Blutdruckkontrolle durchführen")
Alltagssprache ("Herz" zusätzlich zu "kardial")
Vergleiche aus dem Alltag (z.B. "groß wie eine Walnuss")
Zahlen ausschreiben wenn verständlicher ("zwei Mal täglich" statt "2x tägl.")
Direkte Ansprache ("Sie waren", "Ihr Blutdruck", "Sie sollen")

VERMEIDE:
Verschachtelte Nebensätze
Passive Konstruktionen
Abstrakte Formulierungen
Unaufgelöste Abkürzungen
Fachsprache ohne Erklärung
Mehrdeutige Aussagen
Unpersönliche Formulierungen wie "Der Patient"
Meta-Kommentare über die Übersetzung selbst
Sätze wie "Alle Angaben entsprechen dem Originaltext"
Hinweise wie "Laut Dokument" oder "Gemäß den Unterlagen"

EINHEITLICHES ÜBERSETZUNGSFORMAT FÜR ALLE DOKUMENTTYPEN:

# 📋 Ihre medizinische Dokumentation - Einfach erklärt

## 🎯 Das Wichtigste zuerst
[Die zentrale Information in einem klaren Satz]

## 📊 Zusammenfassung
### Was wurde gemacht?
• [Untersuchung/Behandlung in einfacher Sprache]
• [Zeitraum/Datum wenn vorhanden]

### Was wurde gefunden?
• [Hauptbefund 1 in einfacher Sprache]
  → Bedeutung: [Was heißt das für Sie?]
• [Hauptbefund 2 in einfacher Sprache]
  → Bedeutung: [Was heißt das für Sie?]

## 🏥 Ihre Diagnosen
• [Diagnose in Alltagssprache]
  → Medizinisch: [Fachbegriff]
  → ICD-Code falls vorhanden: [Code mit Erklärung, z.B. "I10.90 - Bluthochdruck ohne bekannte Ursache"]
  → Erklärung: [Was ist das genau?]

## 💊 Behandlung & Medikamente
• [Medikament/Behandlung]
  → Wofür: [Zweck]
  → Einnahme: [Wie und wann]
  → Wichtig: [Besonderheiten/Nebenwirkungen]

## ✅ Ihre nächsten Schritte
• [Was Sie tun sollen in einfacher Sprache]
• [Termine die anstehen]
• [Worauf Sie achten müssen in einfacher Sprache]

## 📖 Fachbegriffe verstehen
• **[Begriff 1]**: [Einfache Erklärung]
• **[Begriff 2]**: [Einfache Erklärung]

## 🔢 Medizinische Codes erklärt (falls vorhanden)
### ICD-Codes (Diagnose-Schlüssel):
**[ICD-Code]**: [Vollständige Erklärung was diese Diagnose bedeutet]
  Beispiel: **I10.90**: Bluthochdruck ohne bekannte Ursache - Ihr Blutdruck ist dauerhaft erhöht
  
### OPS-Codes (Behandlungs-Schlüssel):
**[OPS-Code]**: [Vollständige Erklärung welche Behandlung durchgeführt wurde]
  Beispiel: **5-511.11**: Entfernung der Gallenblase durch Bauchspiegelung (minimal-invasive Operation)

## ⚠️ Wichtige Hinweise
Diese Übersetzung hilft Ihnen, Ihre Unterlagen zu verstehen
Besprechen Sie alle Fragen mit Ihrem Arzt
Bei Notfällen: 112 anrufen

---
"""
        
        # UNIVERSELLE Anleitung für ALLE medizinischen Dokumente
        universal_instruction = """
DIESES DOKUMENT KANN ENTHALTEN:
- Arztbriefe, Entlassungsbriefe, Befundberichte
- Laborwerte und Blutwerte
- Bildgebungsbefunde (Röntgen, MRT, CT, Ultraschall)
- Pathologiebefunde
- Medikationspläne
- Medizinische Codes (ICD-10, OPS, DRG, GOÄ, EBM)
- Kombinationen aus allem oben genannten

BEHANDLE JEDEN INHALT ANGEMESSEN:
- Bei Laborwerten: Erkläre Wert → Normalbereich → Bedeutung
- Bei Diagnosen: Übersetze Fachbegriffe in Alltagssprache
- Bei Medikamenten: Erkläre Zweck und Einnahme
- Bei Bildgebung: Beschreibe was untersucht wurde und was gefunden wurde
- Bei Empfehlungen: Mache klar was der Patient tun soll
- Bei medizinischen Codes (ICD, OPS): ERKLÄRE immer was der Code bedeutet! Nicht nur auflisten!
  
  ICD-Beispiele (Diagnose-Codes):
  • "ICD I10.90" → "I10.90 - Bluthochdruck ohne bekannte Ursache (Ihr Blutdruck ist dauerhaft zu hoch)"
  • "ICD E11.9" → "E11.9 - Diabetes Typ 2 (Zuckerkrankheit, die meist im Erwachsenenalter auftritt)"
  • "ICD J44.0" → "J44.0 - COPD mit akuter Verschlechterung (chronische Lungenerkrankung mit plötzlicher Verschlimmerung)"
  • "ICD M54.5" → "M54.5 - Kreuzschmerzen (Schmerzen im unteren Rückenbereich)"
  
  OPS-Beispiele (Behandlungs-Codes):
  • "OPS 5-511.11" → "5-511.11 - Entfernung der Gallenblase durch Bauchspiegelung (minimal-invasive Operation)"
  • "OPS 3-035" → "3-035 - MRT des Kopfes (Kernspintomographie zur Untersuchung des Gehirns)"
  • "OPS 1-632.0" → "1-632.0 - Magenspiegelung mit Gewebeentnahme (Untersuchung des Magens mit einer Kamera)"
  • "OPS 8-931.0" → "8-931.0 - Überwachung auf der Intensivstation (engmaschige medizinische Betreuung)"
  
  WICHTIG: Codes IMMER mit verständlicher Erklärung versehen! Der Patient muss verstehen, was gemeint ist!

Nutze IMMER das einheitliche Format oben, egal welche Inhalte das Dokument hat."""
        
        instruction = base_instruction + universal_instruction
        
        return f"""{instruction}

ORIGINAL MEDIZINISCHER TEXT:
{text}

ÜBERSETZUNG IN EINFACHER SPRACHE:"""
    
    
    async def _generate_response(self, prompt: str, model: str) -> str:
        """Generiert Antwort von Ollama GPU-Instanz"""
        try:
            # Check if requested model is available
            available_models = await self.list_models()
            
            # Use the requested model if available
            if model in available_models:
                print(f"✅ Generiere mit Modell: {model}")
            elif model not in available_models:
                print(f"⚠️ CRITICAL: Requested model {model} not available!")
                print(f"⚠️ Model {model} not found, trying fallbacks...")
                
                # Fallback-Logik: Only use if gpt-oss:20b is truly unavailable
                fallback_models = [
                    "mistral-nemo:latest", "llama3.1", 
                    "mistral:7b", "deepseek-r1:7b"
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
                
                print(f"🚀 GPU: Generiere mit Modell: {model}")
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
        model: str = None  # Will use configured model
    ) -> AsyncGenerator[str, None]:
        """Streaming-Generation für Live-Updates"""
        # Use configured model if not specified
        if model is None:
            model = self.preprocessing_model
        
        # If OVH is enabled for main processing, use OVH streaming
        if self.use_ovh_for_main and self.ovh_client:
            async for chunk in self.ovh_client.generate_streaming(prompt):
                yield chunk
            return
        
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
        model: str = None  # Will use configured translation model
    ) -> tuple[str, float]:
        """
        Übersetzt vereinfachten Text in eine andere Sprache
        Verwendet gemma3-translator:4b für präzise Übersetzungen
        
        Args:
            simplified_text: Der bereits vereinfachte Text
            target_language: Die Zielsprache
            model: Das zu verwendende Modell (Standard: gemma3-translator:4b)
            
        Returns:
            tuple[str, float]: (translated_text, confidence)
        """
        try:
            # Use configured translation model
            if model is None:
                model = self.translation_model
            
            language_name = LANGUAGE_NAMES.get(target_language, target_language.value)
            
            print(f"🌐 TRANSLATION: Verwende Model: {model} für Sprache: {language_name}")
            prompt = self._get_language_translation_prompt(simplified_text, target_language, language_name)
            translated_text = await self._generate_response(prompt, model)
            print(f"✅ TRANSLATION: Erfolgreich mit {model}")
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

    async def _ai_preprocess_text(self, text: str, model: str = None) -> str:
        """
        Nutzt KI um nur wirklich irrelevante Formatierungen zu entfernen
        Verwendet konfiguriertes Preprocessing-Model auf GPU-Instanz
        """
        
        # Use configured preprocessing model
        if model is None:
            model = self.preprocessing_model
        
        logger.info(f"Starting preprocessing with {model} on GPU instance")
        
        preprocess_prompt = f"""Du bist ein medizinischer Dokumentenbereiniger für Datenschutz und Übersichtlichkeit.

🚨 KRITISCHE REGEL: BEHALTE ABSOLUT ALLE MEDIZINISCHEN INFORMATIONEN!

ENTFERNE NUR (komplett löschen):
- Patientennamen und Patientenadressen
- Geburtsdaten von Patienten (ABER: Untersuchungsdaten müssen bleiben!)
- Arztnamen und Unterschriften (ABER: Fachabteilungen bleiben!)
- Versicherungsnummern, Patientennummern
- Private Telefonnummern und E-Mails
- Briefköpfe, Logos, reine Formatierungszeichen
- Seitenzahlen, Kopf-/Fußzeilen
- Grußformeln (z.B. "Mit freundlichen Grüßen", "Sehr geehrte")
- Anreden und Verabschiedungen

⚠️ MUSS UNBEDINGT BLEIBEN - NIEMALS LÖSCHEN:
✅ ALLE Laborwerte (auch in Tabellen, Listen oder ANHÄNGEN!)
✅ ALLE Blutwerte, Urinwerte, etc.
✅ ALLE Messwerte und Zahlen mit medizinischer Bedeutung
✅ ALLE Referenzbereiche und Normwerte
✅ ALLE Anhänge und deren KOMPLETTE Inhalte
✅ ALLE Verweise auf Anhänge (z.B. "siehe Anhang", "Laborwerte im Anhang")
✅ KOMPLETTE Anhänge mit Laborwerten, auch wenn sie am Ende stehen
✅ ALLE Diagnosen und Befunde
✅ ALLE Medikamente und Dosierungen  
✅ ALLE medizinischen Daten und Termine
✅ ALLE Untersuchungsergebnisse
✅ Krankenhaus-/Abteilungsnamen
✅ Der KOMPLETTE medizinische Inhalt
✅ Medizinische Codes (ICD, OPS, etc.)

🔴 SPEZIALREGEL FÜR ANHÄNGE:
Wenn "siehe Anhang" oder "Laborwerte im Anhang" erwähnt wird:
→ BEHALTE den Verweis UND den kompletten Anhang-Inhalt!
→ Auch wenn der Anhang am Ende steht, BEHALTE IHN KOMPLETT!
→ Entferne NUR Patientendaten aus dem Anhang, NICHT die Werte!

WICHTIG: Wenn du dir unsicher bist, BEHALTE die Information!

BEISPIELE:
❌ LÖSCHEN: "Sehr geehrte Frau Maria Müller, geb. 15.03.1965"
✅ BEHALTEN: "Hämoglobin: 12.5 g/dl (Norm: 12-16)"
✅ BEHALTEN: "siehe Anhang: Laborwerte vom 15.10.2024"
✅ BEHALTEN: "Die Laborwerte finden Sie im beigefügten Anhang"
✅ BEHALTEN: Kompletter Anhang mit allen Laborwerten
✅ BEHALTEN: Alle Tabellen mit Messwerten

ORIGINALTEXT:
{text}

BEREINIGTER TEXT (nur medizinische Inhalte):"""
        
        # Verwende GPU-Instanz für Preprocessing (schneller!)
        print(f"🔧 PREPROCESSING: Verwende Model: {model} (GPU-Instanz)")
        cleaned_text = await self._generate_response(preprocess_prompt, model)
        print(f"✅ PREPROCESSING: Erfolgreich mit {model}")
        
        # Nachbearbeitung: Entferne nur DOPPELTE Bullet Points und unnötige Nummerierungen
        import re
        # Entfernt Nummerierung VOR Bullet Points (z.B. "1. •" wird zu "•")
        cleaned_text = re.sub(r'^\s*\d+[.)]\s*([•\-\*])', r'\1', cleaned_text, flags=re.MULTILINE)
        # Entfernt doppelte Bullet-Points (z.B. "• •" wird zu "•")
        cleaned_text = re.sub(r'^([•\-\*])\s*[•\-\*]+\s*', r'\1 ', cleaned_text, flags=re.MULTILINE)
        # Entfernt mehrfache Bullet-Points in einer Zeile
        cleaned_text = re.sub(r'([•\-\*])\s*\1+', r'\1', cleaned_text)
        
        # Fallback wenn KI-Preprocessing fehlschlägt
        if not cleaned_text or cleaned_text.startswith("Fehler") or len(cleaned_text) < 50:
            print("⚠️ KI-Preprocessing fehlgeschlagen, verwende Originaltext")
            return text
        
        print(f"✅ Text intelligent bereinigt: {len(text)} → {len(cleaned_text)} Zeichen")
        return cleaned_text 