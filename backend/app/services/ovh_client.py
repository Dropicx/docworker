import os
import httpx
import logging
import base64
from typing import Optional, Dict, Any, AsyncGenerator, Union, List
from openai import AsyncOpenAI
import json
from PIL import Image
from io import BytesIO
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

        # Vision model for OCR tasks
        self.vision_model = os.getenv("OVH_VISION_MODEL", "Qwen2.5-VL-72B-Instruct")
        self.vision_base_url = os.getenv("OVH_VISION_BASE_URL", "https://qwen-2-5-vl-72b-instruct.endpoints.kepler.ai.cloud.ovh.net/v1")

        # Define which prompt types should use fast model for speed optimization
        self.fast_model_prompt_types = {
            'preprocessing_prompt',
            'language_translation_prompt',
            'grammar_check_prompt',
            'final_check_prompt',
            'formatting_prompt'
        }
        
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
        logger.info(f"   - Vision Model: {self.vision_model}")
        logger.info(f"   - Vision URL: {self.vision_base_url}")
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

            # Initialize separate client for vision model
            self.vision_client = AsyncOpenAI(
                base_url=self.vision_base_url,
                api_key=self.access_token or "dummy-key-not-set"
            )
        except Exception as e:
            logger.error(f"Failed to initialize OVH clients: {e}")
            self.client = None
            self.vision_client = None
        
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

    def should_use_fast_model(self, prompt_type: str = None, task_description: str = None) -> bool:
        """
        Determine whether to use fast model based on prompt type or task description.
        Fast model is used for routine tasks to improve speed.
        """
        if prompt_type and prompt_type in self.fast_model_prompt_types:
            return True

        # Additional heuristics based on task description
        if task_description:
            task_lower = task_description.lower()
            speed_optimized_keywords = [
                'grammar', 'formatting', 'format', 'structure', 'layout',
                'final check', 'validation', 'template', 'language_translation'
            ]
            return any(keyword in task_lower for keyword in speed_optimized_keywords)

        return False

    async def process_medical_text_with_prompt(
        self,
        full_prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 4000,
        use_fast_model: bool = False
    ) -> str:
        """
        Process medical text with complete prompt (identical to ollama_client.py format)
        Now supports fast model for routine tasks to improve speed
        """
        if not self.access_token:
            logger.error("❌ OVH API token not configured")
            return "Error: OVH API token not configured. Please set OVH_AI_ENDPOINTS_ACCESS_TOKEN in .env"

        # Choose model based on task type
        model_to_use = self.preprocessing_model if use_fast_model else self.main_model
        model_type = "fast" if use_fast_model else "high-quality"

        try:
            logger.info(f"🚀 Processing with OVH {model_to_use} ({model_type})")

            # Use simple user message with the full prompt (like ollama)
            messages = [
                {
                    "role": "user",
                    "content": full_prompt
                }
            ]

            # Make the API call using OpenAI client
            response = await self.client.chat.completions.create(
                model=model_to_use,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=0.9
            )

            result = response.choices[0].message.content
            logger.info(f"✅ OVH processing successful with {model_to_use} ({model_type})")
            return result.strip()

        except Exception as e:
            logger.error(f"❌ OVH API error: {e}")
            return f"Error processing with OVH API: {str(e)}"

    async def process_prompt_with_optimization(
        self,
        full_prompt: str,
        prompt_type: str = None,
        temperature: float = 0.3,
        max_tokens: int = 4000
    ) -> str:
        """
        Process a prompt with automatic model optimization based on prompt type.
        This is the recommended method for processing prompts in the pipeline.
        """
        use_fast = self.should_use_fast_model(prompt_type=prompt_type)

        logger.info(f"🔄 Processing prompt type '{prompt_type}' with {'fast' if use_fast else 'high-quality'} model")

        return await self.process_medical_text_with_prompt(
            full_prompt=full_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            use_fast_model=use_fast
        )

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
        max_tokens: int = 4000,
        custom_prompt: Optional[str] = None
    ) -> tuple[str, float]:
        """
        Translate simplified text to another language using Meta-Llama-3.3-70B
        """
        if not self.access_token:
            logger.error("❌ OVH API token not configured")
            return simplified_text, 0.0
        
        try:
            logger.info(f"🌐 Translating to {target_language} with OVH {self.translation_model}")
            
            if custom_prompt:
                # Use custom prompt and replace placeholders
                translation_prompt = custom_prompt.replace("{language}", target_language).replace("{text}", simplified_text)
                logger.info(f"📝 Using custom language translation prompt")
            else:
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
                logger.info(f"📝 Using default language translation prompt")
            
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
        document_type: str = "universal",
        custom_prompts: Optional[Any] = None
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
            if custom_prompts and hasattr(custom_prompts, 'translation_prompt'):
                instruction = custom_prompts.translation_prompt
                logger.info(f"📝 Using custom translation prompt for {document_type}")
            else:
                instruction = self._get_medical_translation_instruction()
                logger.info(f"📝 Using default translation prompt for {document_type}")
            
            # Format the complete prompt exactly like ollama_client.py
            full_prompt = f"""{instruction}

ORIGINAL MEDIZINISCHER TEXT:
{text}

ÜBERSETZUNG IN EINFACHER SPRACHE:"""
            
            # Process with OVH API using the formatted prompt (main translation - use high-quality model)
            translated_text = await self.process_medical_text_with_prompt(
                full_prompt=full_prompt,
                temperature=0.3,
                max_tokens=4000,
                use_fast_model=False  # Main translation needs quality
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
    
    async def format_text(self, text: str, formatting_prompt: str) -> str:
        """
        Format text using AI with a specific formatting prompt.
        This method applies document-specific formatting rules.
        """
        try:
            if not text or not formatting_prompt:
                return text
            
            # Create full prompt for formatting
            full_prompt = f"{formatting_prompt}\n\nTEXT TO FORMAT:\n{text}"

            # Use the medical text processing with the formatting prompt (use fast model for formatting)
            formatted_text = await self.process_medical_text_with_prompt(
                full_prompt=full_prompt,
                temperature=0.3,
                max_tokens=4000,
                use_fast_model=True  # Formatting is routine task - use fast model
            )
            
            # Apply additional formatting improvements
            formatted_text = self._improve_formatting(formatted_text)
            
            return formatted_text
            
        except Exception as e:
            logger.error(f"Error formatting text: {e}")
            # Return original text with basic formatting if AI formatting fails
            return self._improve_formatting(text)

    async def extract_text_with_vision(
        self,
        image_data: Union[bytes, Image.Image],
        file_type: str = "image",
        confidence_threshold: float = 0.7
    ) -> tuple[str, float]:
        """
        Extract text from image using Qwen 2.5 VL vision model

        Args:
            image_data: Image as bytes or PIL Image
            file_type: Type of file being processed
            confidence_threshold: Minimum confidence for success

        Returns:
            tuple[str, float]: (extracted_text, confidence_score)
        """
        if not self.access_token or not self.vision_client:
            logger.error("❌ OVH vision client not configured")
            return "Error: OVH vision client not configured", 0.0

        try:
            logger.info(f"🔍 Starting vision OCR with Qwen 2.5 VL for {file_type}")

            # Convert image to base64
            if isinstance(image_data, Image.Image):
                # Convert PIL Image to bytes
                buffered = BytesIO()
                # Save as PNG for best quality
                image_data.save(buffered, format="PNG")
                image_bytes = buffered.getvalue()
            else:
                image_bytes = image_data

            # Encode to base64
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
            image_url = f"data:image/png;base64,{image_base64}"

            # Create medical OCR prompt
            ocr_prompt = self._get_medical_ocr_prompt()

            # Prepare messages for vision model
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": ocr_prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": image_url
                            }
                        }
                    ]
                }
            ]

            # Make API call to Qwen 2.5 VL
            logger.info(f"🚀 Calling Qwen 2.5 VL vision API at {self.vision_base_url}")
            response = await self.vision_client.chat.completions.create(
                model=self.vision_model,
                messages=messages,
                max_tokens=4000,
                temperature=0.1  # Very low for precise OCR
            )

            extracted_text = response.choices[0].message.content

            if not extracted_text or len(extracted_text.strip()) < 10:
                logger.warning("⚠️ Vision OCR returned very short text")
                return "Kein Text im Bild erkannt.", 0.1

            # Calculate confidence based on text quality
            confidence = self._calculate_vision_ocr_confidence(extracted_text)

            logger.info(f"✅ Vision OCR successful: {len(extracted_text)} characters, confidence: {confidence:.2%}")
            logger.info(f"📄 Extracted text preview: {extracted_text[:500]}...")

            return extracted_text.strip(), confidence

        except Exception as e:
            logger.error(f"❌ Vision OCR failed: {e}")
            return f"Vision OCR error: {str(e)}", 0.0

    def _get_medical_ocr_prompt(self) -> str:
        """
        Get specialized OCR prompt for medical documents
        """
        return """Du bist ein hochpräziser OCR-Scanner, spezialisiert auf medizinische Dokumente.

🎯 AUFGABE:
Extrahiere ALLEN sichtbaren Text aus diesem medizinischen Dokument mit höchster Präzision.

⚡ KRITISCHE REGELN:
1. EXTRAHIERE JEDEN sichtbaren Text - auch kleine Details
2. BEHALTE die originale Struktur und Formatierung bei
3. ERKENNE Tabellen, Listen, Formulare und ihre Struktur
4. ACHTE besonders auf:
   - Laborwerte und Messergebnisse
   - Medizinische Begriffe und Abkürzungen
   - Datum- und Zeitangaben
   - Dosierungen und Einheiten
   - Unterschriften und Stempel (transkribiere sie)
5. Bei unleserlichen Stellen: markiere mit [unleserlich]
6. KEINE Interpretation oder Korrektur - nur exakte Extraktion
7. BEWAHRE alle Zahlen, Symbole und Sonderzeichen

📋 FORMATIERUNG:
- Nutze Markdown für Struktur
- Tabellen als Markdown-Tabellen
- Listen mit Bindestrichen (-)
- Überschriften mit ##
- Behalte Zeilenumbrüche bei

🏥 MEDIZINISCHE PRÄZISION:
- Alle Laborwerte mit exakten Zahlen
- Alle Einheiten (mg/dl, mmol/l, etc.)
- Alle Referenzbereiche
- Alle Medikamentennamen und Dosierungen
- Alle Diagnosecodes (ICD, OPS)

Beginne sofort mit der Textextraktion:"""

    def _calculate_vision_ocr_confidence(self, text: str) -> float:
        """
        Calculate confidence score for vision OCR results
        """
        if not text or len(text.strip()) < 10:
            return 0.0

        confidence = 0.7  # Base confidence for Qwen 2.5 VL

        # Length indicators
        if len(text) > 100:
            confidence += 0.05
        if len(text) > 500:
            confidence += 0.05
        if len(text) > 1000:
            confidence += 0.05

        # Medical content indicators
        medical_terms = [
            'laborwerte', 'befund', 'diagnose', 'patient', 'arzt',
            'blutbild', 'urin', 'röntgen', 'mrt', 'ct', 'ultraschall',
            'mg/dl', 'mmol/l', 'µg/ml', 'ng/ml', 'u/l', 'iu/l',
            'normal', 'pathologisch', 'auffällig', 'unauffällig'
        ]

        text_lower = text.lower()
        found_terms = sum(1 for term in medical_terms if term in text_lower)
        confidence += min(found_terms * 0.01, 0.1)

        # Structure indicators (tables, lists)
        if '|' in text or '- ' in text or '## ' in text:
            confidence += 0.05

        # Number indicators (likely measurements)
        import re
        numbers_with_units = len(re.findall(r'\d+[.,]?\d*\s*(mg|ml|mmol|µg|ng|u/l|iu/l|%)', text, re.IGNORECASE))
        confidence += min(numbers_with_units * 0.005, 0.05)

        return min(confidence, 0.95)  # Cap at 95%

    async def process_multiple_images_ocr(
        self,
        images: List[Union[bytes, Image.Image]],
        merge_strategy: str = "sequential"
    ) -> tuple[str, float]:
        """
        Process multiple images with OCR and merge results intelligently

        Args:
            images: List of images to process
            merge_strategy: How to merge results ("sequential", "smart")

        Returns:
            tuple[str, float]: (merged_text, average_confidence)
        """
        if not images:
            return "No images provided", 0.0

        logger.info(f"🔄 Processing {len(images)} images with vision OCR")

        ocr_results = []
        total_confidence = 0.0

        for i, image in enumerate(images, 1):
            logger.info(f"📄 Processing image {i}/{len(images)}")

            text, confidence = await self.extract_text_with_vision(image, f"image_{i}")

            if text and not text.startswith("Error"):
                ocr_results.append({
                    'page': i,
                    'text': text,
                    'confidence': confidence
                })
                total_confidence += confidence
                logger.info(f"✅ Image {i} processed: {len(text)} chars, confidence: {confidence:.2%}")
            else:
                logger.warning(f"⚠️ Image {i} failed: {text}")

        if not ocr_results:
            return "Failed to extract text from any image", 0.0

        # Merge results based on strategy
        if merge_strategy == "sequential":
            merged_text = self._merge_sequential(ocr_results)
        elif merge_strategy == "smart":
            merged_text = self._merge_smart(ocr_results)
        else:
            merged_text = self._merge_sequential(ocr_results)

        avg_confidence = total_confidence / len(ocr_results)

        logger.info(f"🎯 Multi-image OCR complete: {len(merged_text)} total chars, avg confidence: {avg_confidence:.2%}")

        return merged_text, avg_confidence

    def _merge_sequential(self, ocr_results: List[Dict]) -> str:
        """
        Merge OCR results in sequential order with page separators
        """
        merged_parts = []

        for result in sorted(ocr_results, key=lambda x: x['page']):
            page_text = result['text']
            page_num = result['page']

            # Add page header
            merged_parts.append(f"--- Seite {page_num} ---")
            merged_parts.append(page_text)
            merged_parts.append("")  # Empty line between pages

        return "\n".join(merged_parts)

    def _merge_smart(self, ocr_results: List[Dict]) -> str:
        """
        Intelligently merge OCR results with context awareness
        """
        if len(ocr_results) == 1:
            return ocr_results[0]['text']

        merged_parts = []

        for i, result in enumerate(sorted(ocr_results, key=lambda x: x['page'])):
            page_text = result['text'].strip()

            if i == 0:
                # First page - add as is
                merged_parts.append(page_text)
            else:
                # Subsequent pages - check for continuation
                prev_text = merged_parts[-1] if merged_parts else ""

                # Simple heuristic: if previous page ends mid-sentence, continue
                if prev_text.rstrip().endswith((',', '-', 'und', 'oder', 'sowie')):
                    # Likely continuation - merge without page break
                    merged_parts.append(page_text)
                else:
                    # New section - add page separator
                    merged_parts.append(f"\n--- Seite {result['page']} ---\n")
                    merged_parts.append(page_text)

        return "\n".join(merged_parts)