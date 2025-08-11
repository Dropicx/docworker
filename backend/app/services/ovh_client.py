import os
import httpx
import logging
from typing import Optional, Dict, Any, AsyncGenerator
from openai import AsyncOpenAI
import json
# Try to use advanced filter with spaCy, fallback to smart filter
try:
    from app.services.privacy_filter_advanced import AdvancedPrivacyFilter
    ADVANCED_FILTER_AVAILABLE = True
except ImportError:
    from app.services.smart_privacy_filter import SmartPrivacyFilter
    ADVANCED_FILTER_AVAILABLE = False

# Setup logger
logger = logging.getLogger(__name__)

class OVHClient:
    """
    Client for OVH AI Endpoints using Meta-Llama-3.3-70B-Instruct
    """
    
    def __init__(self):
        self.access_token = os.getenv("OVH_AI_ENDPOINTS_ACCESS_TOKEN")
        self.base_url = os.getenv("OVH_AI_BASE_URL", "https://oai.endpoints.kepler.ai.cloud.ovh.net/v1")
        
        # Different models for different tasks
        self.main_model = os.getenv("OVH_MAIN_MODEL", "Meta-Llama-3_3-70B-Instruct")
        self.preprocessing_model = os.getenv("OVH_PREPROCESSING_MODEL", "Mistral-Nemo-Instruct-2407")
        self.translation_model = os.getenv("OVH_TRANSLATION_MODEL", "Meta-Llama-3_3-70B-Instruct")
        
        # Initialize privacy filter for local PII removal
        if ADVANCED_FILTER_AVAILABLE:
            self.privacy_filter = AdvancedPrivacyFilter()
            logger.info("🧠 Using AdvancedPrivacyFilter with spaCy NER")
        else:
            self.privacy_filter = SmartPrivacyFilter()
            logger.info("📝 Using SmartPrivacyFilter (heuristic-based)")
        
        # Debug logging for environment variables
        logger.info(f"🔍 OVH Client Initialization:")
        logger.info(f"   - Access Token: {'✅ Set' if self.access_token else '❌ NOT SET'}")
        logger.info(f"   - Token Length: {len(self.access_token) if self.access_token else 0} chars")
        logger.info(f"   - Base URL: {self.base_url}")
        logger.info(f"   - Main Model: {self.main_model}")
        logger.info(f"   - USE_OVH_ONLY: {os.getenv('USE_OVH_ONLY', 'not set')}")
        
        if not self.access_token:
            logger.warning("⚠️ OVH_AI_ENDPOINTS_ACCESS_TOKEN not set - API calls will fail!")
            logger.warning("   Please set the following environment variables in Railway:")
            logger.warning("   - OVH_AI_ENDPOINTS_ACCESS_TOKEN=your-token-here")
            logger.warning("   - OVH_AI_BASE_URL=https://oai.endpoints.kepler.ai.cloud.ovh.net/v1")
        
        # Initialize OpenAI client for OVH (use dummy key to prevent initialization errors)
        try:
            self.client = AsyncOpenAI(
                base_url=self.base_url,
                api_key=self.access_token or "dummy-key-not-set"  # Use dummy key if not set
            )
        except Exception as e:
            logger.error(f"Failed to initialize OVH client: {e}")
            self.client = None
        
        # Alternative HTTP client for direct API calls
        self.timeout = 300  # 5 minutes timeout
        
    async def check_connection(self) -> tuple[bool, str]:
        """Check connection to OVH AI Endpoints
        Returns: (success: bool, error_message: str)
        """
        if not self.access_token:
            error = "OVH API token not configured - OVH_AI_ENDPOINTS_ACCESS_TOKEN is empty or not set"
            logger.error(f"❌ {error}")
            logger.error("   Please ensure the environment variable is set in Railway")
            return False, error
        
        if not self.client:
            error = "OVH client not initialized"
            logger.error(f"❌ {error}")
            return False, error
            
        try:
            logger.info(f"🔄 Testing OVH connection to {self.base_url}")
            logger.info(f"   Using model: {self.main_model}")
            logger.info(f"   Token (last 8 chars): ...{self.access_token[-8:] if self.access_token else 'NOT SET'}")
            
            # Try a simple completion to test connection
            response = await self.client.chat.completions.create(
                model=self.main_model,
                messages=[{"role": "user", "content": "Say 'OK' if you can read this"}],
                max_tokens=10,
                temperature=0
            )
            
            if response and response.choices:
                logger.info("✅ OVH AI Endpoints connection successful")
                logger.info(f"   Response: {response.choices[0].message.content[:50]}")
                return True, "Connection successful"
            else:
                error = "Empty response from OVH API"
                logger.error(f"❌ {error}")
                return False, error
                
        except Exception as e:
            error_msg = str(e)
            logger.error(f"❌ OVH AI Endpoints connection failed: {error_msg}")
            
            # Provide specific guidance based on error
            if "401" in error_msg or "unauthorized" in error_msg.lower():
                error = f"Invalid API token (401 Unauthorized). Token last 8 chars: ...{self.access_token[-8:] if self.access_token else 'NOT SET'}"
                logger.error(f"   → {error}")
            elif "404" in error_msg:
                error = f"Model '{self.main_model}' not found (404). Available models may differ."
                logger.error(f"   → {error}")
            elif "connection" in error_msg.lower() or "timeout" in error_msg.lower():
                error = f"Cannot reach {self.base_url} (Connection/Timeout error)"
                logger.error(f"   → {error}")
            else:
                error = f"Unexpected error: {error_msg[:200]}"
                logger.error(f"   → {error}")
            
            return False, error
    
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
            logger.info(f"🚀 Processing with OVH {self.main_model}")
            
            # Use simple user message with the full prompt (like ollama)
            messages = [
                {
                    "role": "user",
                    "content": full_prompt
                }
            ]
            
            # Make the API call using OpenAI client
            response = await self.client.chat.completions.create(
                model=self.main_model,
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
            logger.info(f"🚀 Processing with OVH {self.main_model}")
            
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
                model=self.main_model,
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
    
    async def preprocess_medical_text(
        self,
        text: str,
        temperature: float = 0.3,
        max_tokens: int = 4000
    ) -> str:
        """
        Preprocess medical text - first removes PII locally, then optionally uses OVH
        """
        # Log the original text (truncated for readability)
        logger.info("=" * 80)
        logger.info("📄 PREPROCESSING PIPELINE STARTED")
        logger.info("=" * 80)
        logger.info(f"📥 [1/3] ORIGINAL EXTRACTED TEXT (first 1000 chars):")
        logger.info("-" * 40)
        logger.info(text[:1000] + "..." if len(text) > 1000 else text)
        logger.info(f"   Length: {len(text)} characters")
        logger.info("-" * 40)
        
        # SCHRITT 1: Lokale PII-Entfernung mit Python (schnell und datenschutzfreundlich)
        try:
            logger.info("🔒 [2/3] APPLYING PRIVACY FILTER...")
            cleaned_text = self.privacy_filter.remove_pii(text)
            
            # Log the privacy-filtered text
            logger.info(f"🔐 [2/3] PRIVACY-FILTERED TEXT (first 1000 chars):")
            logger.info("-" * 40)
            logger.info(cleaned_text[:1000] + "..." if len(cleaned_text) > 1000 else cleaned_text)
            logger.info(f"   Length: {len(cleaned_text)} characters")
            logger.info(f"   Reduction: {len(text) - len(cleaned_text)} characters removed")
            logger.info("-" * 40)
            
            # Grundlegende Validierung
            if len(cleaned_text) > 50:  # Mindestens etwas Text sollte übrig bleiben
                logger.info("✅ Local PII removal successful")
            else:
                logger.warning("⚠️ Text too short after PII removal, using original text")
                cleaned_text = text
        except Exception as e:
            logger.warning(f"⚠️ Local PII removal failed: {e}, using original text")
            cleaned_text = text
        
        # SCHRITT 2: Optional zusätzliche Bereinigung mit OVH (wenn API verfügbar)
        # Dies ist jetzt optional - wenn OVH nicht verfügbar, verwenden wir nur lokale Bereinigung
        if not self.access_token:
            logger.info("ℹ️ OVH API not configured, using local PII removal only")
            return cleaned_text  # Return locally cleaned text
        
        try:
            logger.info(f"🔧 Additional preprocessing with OVH {self.preprocessing_model}")
            
            preprocess_prompt = """Du bist ein medizinischer Dokumentenbereiniger für Datenschutz und Übersichtlichkeit.

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

ORIGINALTEXT:
{text}

BEREINIGTER TEXT (nur medizinische Inhalte):"""
            
            full_prompt = preprocess_prompt.format(text=cleaned_text)
            
            # Use preprocessing model
            messages = [
                {
                    "role": "user",
                    "content": full_prompt
                }
            ]
            
            response = await self.client.chat.completions.create(
                model=self.preprocessing_model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=0.9
            )
            
            result = response.choices[0].message.content
            
            # Log the OVH-preprocessed text
            logger.info(f"🤖 [3/3] OVH-PREPROCESSED TEXT (first 1000 chars):")
            logger.info("-" * 40)
            logger.info(result[:1000] + "..." if len(result) > 1000 else result)
            logger.info(f"   Length: {len(result)} characters")
            logger.info(f"   Total reduction from original: {len(text) - len(result)} characters")
            logger.info("-" * 40)
            
            logger.info(f"✅ OVH preprocessing successful with {self.preprocessing_model}")
            logger.info("=" * 80)
            logger.info("📄 PREPROCESSING PIPELINE COMPLETED")
            logger.info("=" * 80)
            
            # Clean up formatting
            import re
            result = re.sub(r'^\s*\d+[.)]\s*([•\-\*])', r'\1', result, flags=re.MULTILINE)
            result = re.sub(r'^([•\-\*])\s*[•\-\*]+\s*', r'\1 ', result, flags=re.MULTILINE)
            result = re.sub(r'([•\-\*])\s*\1+', r'\1', result)
            
            return result.strip() if result else text
            
        except Exception as e:
            logger.error(f"❌ OVH preprocessing error: {e}")
            return text  # Return original text on error
    
    async def translate_to_language(
        self,
        simplified_text: str,
        target_language: str,
        temperature: float = 0.3,
        max_tokens: int = 4000
    ) -> tuple[str, float]:
        """
        Translate simplified text to another language using Meta-Llama-3.3-70B
        """
        if not self.access_token:
            logger.error("❌ OVH API token not configured")
            return simplified_text, 0.0
        
        try:
            logger.info(f"🌐 Translating to {target_language} with OVH {self.translation_model}")
            
            translation_prompt = f"""Übersetze den folgenden Text EXAKT in {target_language}.

STRIKTE REGELN:
1. NUR übersetzen - KEINE Zusätze, Erklärungen oder Kommentare
2. EXAKTE Formatierung beibehalten - jede Zeile, jeder Absatz, jedes Symbol
3. Alle Symbole (•, →, ##, 📊, etc.) UNVERÄNDERT lassen
4. Zahlen und Einheiten (mg, ml, mmHg) NICHT ändern
5. Bei unübersetzbaren Begriffen das Original verwenden

TEXT ZUM ÜBERSETZEN:
{simplified_text}

ÜBERSETZUNG:"""
            
            messages = [
                {
                    "role": "user",
                    "content": translation_prompt
                }
            ]
            
            response = await self.client.chat.completions.create(
                model=self.translation_model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=0.9
            )
            
            result = response.choices[0].message.content
            logger.info(f"✅ OVH language translation successful")
            
            # Improve formatting for bullet points and arrows
            result = self._improve_formatting(result)
            
            # Evaluate quality
            confidence = self._evaluate_language_translation_quality(simplified_text, result)
            
            return result.strip(), confidence
            
        except Exception as e:
            logger.error(f"❌ OVH language translation error: {e}")
            return simplified_text, 0.0
    
    def _evaluate_language_translation_quality(self, original: str, translated: str) -> float:
        """
        Evaluate the quality of language translation
        """
        if not translated or translated.startswith("Error"):
            return 0.0
        
        confidence = 0.6  # Base confidence for OVH model
        
        # Length check
        if len(translated) > 50:
            confidence += 0.1
        
        # Ratio check
        length_ratio = len(translated) / max(len(original), 1)
        if 0.7 <= length_ratio <= 1.5:
            confidence += 0.1
        
        # Structure preservation (emojis)
        import re
        emoji_pattern = r'[😀-🿿]|[\U0001F300-\U0001F5FF]|[\U0001F600-\U0001F64F]|[\U0001F680-\U0001F6FF]'
        original_emojis = len(re.findall(emoji_pattern, original))
        translated_emojis = len(re.findall(emoji_pattern, translated))
        
        if original_emojis > 0:
            emoji_retention = min(translated_emojis / original_emojis, 1.0)
            confidence += emoji_retention * 0.1
        
        return min(confidence, 1.0)
    
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
                model=self.main_model,
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
            logger.info("=" * 80)
            logger.info("🌍 TRANSLATION PIPELINE STARTED")
            logger.info("=" * 80)
            logger.info(f"📥 INPUT TEXT FOR TRANSLATION (first 1000 chars):")
            logger.info("-" * 40)
            logger.info(text[:1000] + "..." if len(text) > 1000 else text)
            logger.info(f"   Length: {len(text)} characters")
            logger.info("-" * 40)
            
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
            
            # Log the translated text
            logger.info(f"📤 TRANSLATED TEXT (first 1000 chars):")
            logger.info("-" * 40)
            logger.info(translated_text[:1000] + "..." if len(translated_text) > 1000 else translated_text)
            logger.info(f"   Length: {len(translated_text)} characters")
            logger.info("-" * 40)
            
            # Improve formatting for bullet points and arrows
            translated_text = self._improve_formatting(translated_text)
            
            # Evaluate quality
            confidence = self._evaluate_translation_quality(text, translated_text)
            
            logger.info(f"📊 Translation confidence: {confidence:.2%}")
            logger.info("=" * 80)
            logger.info("🌍 TRANSLATION PIPELINE COMPLETED")
            logger.info("=" * 80)
            
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

MARKDOWN-FORMATIERUNG - SEHR WICHTIG:
• Verwende STANDARD Markdown-Listen
• Hauptpunkte: "- " (Bindestrich und Leerzeichen)
• Unterpunkte: "  - " (zwei Leerzeichen, Bindestrich, Leerzeichen)
• KEINE Bullet-Symbole (•) verwenden
• Pfeile NUR in Unterpunkten: "  - → Text"

RICHTIG:
- Medikament XY
  - → Wofür: Senkt den Blutdruck
  - → Einnahme: 1x täglich morgens

FALSCH:
• Medikament XY. → Wofür: Senkt den Blutdruck
- Medikament XY → Einnahme: täglich

EINHEITLICHES ÜBERSETZUNGSFORMAT FÜR ALLE DOKUMENTTYPEN:

# 📋 Ihre medizinische Dokumentation - Einfach erklärt

## 🎯 Das Wichtigste zuerst
[Die zentrale Information in einem klaren Satz]

## 📊 Zusammenfassung
### Was wurde gemacht?
- [Untersuchung/Behandlung in einfacher Sprache]
- [Zeitraum/Datum wenn vorhanden]

### Was wurde gefunden?
- [Hauptbefund 1 in einfacher Sprache]
  - → Bedeutung: [Was heißt das für Sie?]
- [Hauptbefund 2 in einfacher Sprache]
  - → Bedeutung: [Was heißt das für Sie?]

## 🏥 Ihre Diagnosen
- [Diagnose in Alltagssprache]
  - → Medizinisch: [Fachbegriff]
  - → ICD-Code: [Code mit Erklärung]
  - → Erklärung: [Was ist das genau?]

## 💊 Behandlung & Medikamente
- [Medikament/Behandlung]
  - → Wofür: [Zweck]
  - → Einnahme: [Wie und wann]
  - → Wichtig: [Besonderheiten/Nebenwirkungen]

## ✅ Ihre nächsten Schritte
- [Was Sie tun sollen in einfacher Sprache]
- [Termine die anstehen]
- [Worauf Sie achten müssen in einfacher Sprache]

## 📖 Fachbegriffe verstehen
- **[Begriff 1]**: [Einfache Erklärung]
- **[Begriff 2]**: [Einfache Erklärung]

## 🔢 Medizinische Codes erklärt (falls vorhanden)
### ICD-Codes (Diagnose-Schlüssel):
- **[ICD-Code]**: [Vollständige Erklärung was diese Diagnose bedeutet]
  
### OPS-Codes (Behandlungs-Schlüssel):
- **[OPS-Code]**: [Vollständige Erklärung welche Behandlung durchgeführt wurde]

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
    
    def _improve_formatting(self, text: str) -> str:
        """
        Minimale Formatierung - konvertiert Bullet Points zu Standard Markdown
        """
        import re
        
        # Ersetze alle Bullet-Symbole (•) durch Standard Markdown (-)
        text = re.sub(r'^•', '-', text, flags=re.MULTILINE)
        text = re.sub(r'\n•', '\n-', text)
        
        # Stelle sicher dass Unterpunkte korrekt formatiert sind
        text = re.sub(r'^  →', '  - →', text, flags=re.MULTILINE)
        
        # Entferne mehrfache Leerzeilen
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        return text.strip()