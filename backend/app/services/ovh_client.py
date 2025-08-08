import os
import httpx
import logging
from typing import Optional, Dict, Any, AsyncGenerator
from openai import AsyncOpenAI
import json

# Setup logger
logger = logging.getLogger(__name__)

class OVHClient:
    """
    Client for OVH AI Endpoints using Meta-Llama-3.3-70B-Instruct
    """
    
    def __init__(self):
        self.access_token = os.getenv("OVH_AI_ENDPOINTS_ACCESS_TOKEN")
        self.base_url = os.getenv("OVH_AI_BASE_URL", "https://oai.endpoints.kepler.ai.cloud.ovh.net/v1")
        self.model = os.getenv("OVH_AI_MODEL", "Meta-Llama-3_3-70B-Instruct")
        
        if not self.access_token:
            logger.warning("⚠️ OVH_AI_ENDPOINTS_ACCESS_TOKEN not set in environment")
        
        # Initialize OpenAI client for OVH
        self.client = AsyncOpenAI(
            base_url=self.base_url,
            api_key=self.access_token or "dummy-key"  # Use dummy key if not set
        )
        
        # Alternative HTTP client for direct API calls
        self.timeout = 300  # 5 minutes timeout
        
    async def check_connection(self) -> bool:
        """Check connection to OVH AI Endpoints"""
        if not self.access_token:
            logger.error("❌ OVH API token not configured")
            return False
            
        try:
            # Try a simple completion to test connection
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "Hi"}],
                max_tokens=10,
                temperature=0
            )
            logger.info("✅ OVH AI Endpoints connection successful")
            return True
        except Exception as e:
            logger.error(f"❌ OVH AI Endpoints connection failed: {e}")
            return False
    
    async def process_medical_text_with_prompt(
        self,
        full_prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 4000
    ) -> str:
        """
        Process medical text with complete prompt (identical to ollama_client.py format)
        """
        if not self.access_token:
            logger.error("❌ OVH API token not configured")
            return "Error: OVH API token not configured. Please set OVH_AI_ENDPOINTS_ACCESS_TOKEN in .env"
        
        try:
            logger.info(f"🚀 Processing with OVH {self.model}")
            
            # Use simple user message with the full prompt (like ollama)
            messages = [
                {
                    "role": "user",
                    "content": full_prompt
                }
            ]
            
            # Make the API call using OpenAI client
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=0.9
            )
            
            result = response.choices[0].message.content
            logger.info(f"✅ OVH processing successful")
            return result.strip()
            
        except Exception as e:
            logger.error(f"❌ OVH API error: {e}")
            return f"Error processing with OVH API: {str(e)}"
    
    async def process_medical_text(
        self, 
        text: str,
        instruction: str = "Process this medical text",
        temperature: float = 0.3,
        max_tokens: int = 4000
    ) -> str:
        """
        Process medical text using Meta-Llama-3.3-70B-Instruct
        
        Args:
            text: The medical text to process
            instruction: Processing instruction
            temperature: Model temperature (0-1)
            max_tokens: Maximum tokens to generate
            
        Returns:
            Processed text from the model
        """
        if not self.access_token:
            logger.error("❌ OVH API token not configured")
            return "Error: OVH API token not configured. Please set OVH_AI_ENDPOINTS_ACCESS_TOKEN in .env"
        
        try:
            logger.info(f"🚀 Processing with OVH {self.model}")
            
            # Prepare the message
            messages = [
                {
                    "role": "system",
                    "content": "Du bist ein hochspezialisierter medizinischer Textverarbeiter. Befolge die Anweisungen präzise. Antworte IMMER in der gleichen Sprache wie der Eingabetext."
                },
                {
                    "role": "user",
                    "content": f"{instruction}\n\nText to process:\n{text}"
                }
            ]
            
            # Make the API call using OpenAI client
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=0.9
            )
            
            result = response.choices[0].message.content
            logger.info(f"✅ OVH processing successful")
            return result.strip()
            
        except Exception as e:
            logger.error(f"❌ OVH API error: {e}")
            return f"Error processing with OVH API: {str(e)}"
    
    async def process_medical_text_direct(
        self,
        text: str,
        instruction: str = "Process this medical text",
        temperature: float = 0.3,
        max_tokens: int = 4000
    ) -> str:
        """
        Process medical text using direct HTTP calls (alternative method)
        """
        if not self.access_token:
            return "Error: OVH API token not configured"
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                payload = {
                    "model": self.model,
                    "messages": [
                        {
                            "role": "system",
                            "content": "Du bist ein hochspezialisierter medizinischer Textverarbeiter. Antworte IMMER in der gleichen Sprache wie der Eingabetext."
                        },
                        {
                            "role": "user",
                            "content": f"{instruction}\n\nText:\n{text}"
                        }
                    ],
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "top_p": 0.9
                }
                
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.access_token}"
                }
                
                logger.info(f"🌐 Direct API call to OVH {self.model}")
                
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    headers=headers
                )
                
                if response.status_code == 200:
                    response_data = response.json()
                    result = response_data["choices"][0]["message"]["content"]
                    logger.info("✅ Direct OVH API call successful")
                    return result.strip()
                else:
                    logger.error(f"❌ OVH API error: {response.status_code} - {response.text}")
                    return f"Error: OVH API returned {response.status_code}"
                    
        except Exception as e:
            logger.error(f"❌ Direct OVH API call failed: {e}")
            return f"Error with direct API call: {str(e)}"
    
    async def generate_streaming(
        self,
        prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 4000
    ) -> AsyncGenerator[str, None]:
        """
        Generate streaming response from OVH API
        """
        if not self.access_token:
            yield "Error: OVH API token not configured"
            return
        
        try:
            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True
            )
            
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            logger.error(f"❌ OVH streaming error: {e}")
            yield f"Streaming error: {str(e)}"
    
    async def translate_medical_document(
        self,
        text: str,
        document_type: str = "universal"
    ) -> tuple[str, str, float, str]:
        """
        Main processing using OVH Meta-Llama-3.3-70B for medical document translation
        
        Returns:
            tuple[str, str, float, str]: (translated_text, doc_type, confidence, cleaned_original)
        """
        try:
            logger.info("🏥 Starting medical document processing with OVH AI")
            
            # Create the comprehensive instruction for medical translation (in German)
            instruction = self._get_medical_translation_instruction()
            
            # Format the complete prompt exactly like ollama_client.py
            full_prompt = f"""{instruction}

ORIGINAL MEDIZINISCHER TEXT:
{text}

ÜBERSETZUNG IN EINFACHER SPRACHE:"""
            
            # Process with OVH API using the formatted prompt
            translated_text = await self.process_medical_text_with_prompt(
                full_prompt=full_prompt,
                temperature=0.3,
                max_tokens=4000
            )
            
            # Evaluate quality
            confidence = self._evaluate_translation_quality(text, translated_text)
            
            return translated_text, document_type, confidence, text
            
        except Exception as e:
            logger.error(f"❌ OVH translation failed: {e}")
            return f"Translation error: {str(e)}", "error", 0.0, text
    
    def _get_medical_translation_instruction(self) -> str:
        """Get the comprehensive medical translation instruction - identical to ollama_client.py"""
        
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
        
        return instruction
    
    def _evaluate_translation_quality(self, original: str, translated: str) -> float:
        """Evaluate the quality of the translation"""
        if not translated or translated.startswith("Error"):
            return 0.0
        
        confidence = 0.6  # Base confidence for OVH model
        
        # Length check
        if len(translated) > 100:
            confidence += 0.1
        if len(translated) > 500:
            confidence += 0.1
        
        # Ratio check
        length_ratio = len(translated) / max(len(original), 1)
        if 0.5 <= length_ratio <= 2.0:
            confidence += 0.1
        
        # Simple language indicators
        simple_indicators = [
            "this means", "simply put", "in other words",
            "das bedeutet", "einfach gesagt", "mit anderen worten"
        ]
        translated_lower = translated.lower()
        found_indicators = sum(1 for indicator in simple_indicators if indicator in translated_lower)
        confidence += min(found_indicators * 0.05, 0.1)
        
        return min(confidence, 1.0)