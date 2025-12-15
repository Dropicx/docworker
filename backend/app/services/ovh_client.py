import base64
from collections.abc import AsyncGenerator
from io import BytesIO
import logging
from typing import Any

import httpx
from openai import AsyncOpenAI
from PIL import Image

from app.core.config import settings

# ⚡ NOTE: PII removal now happens in worker (OptimizedPrivacyFilter)
# This service receives already-cleaned text from the worker
# No need to import privacy filters here anymore

# Setup logger
logger = logging.getLogger(__name__)


class OVHClient:
    """OVH AI Endpoints client for medical text processing and vision OCR.

    This client provides a comprehensive interface to OVH's AI infrastructure,
    supporting both text-based LLM operations and vision-based OCR. It handles
    medical document translation, multi-image processing, and streaming responses.

    The client uses different models optimized for specific tasks:
    - Main Model (Llama 3.3 70B): High-quality translation and processing
    - Preprocessing Model (Mistral Nemo): Fast routine tasks
    - Vision Model (Qwen 2.5 VL): Advanced OCR and image understanding

    Attributes:
        access_token (str): OVH API access token from settings
        base_url (str): Base URL for OVH AI Endpoints
        main_model (str): Primary LLM model for high-quality tasks
        preprocessing_model (str): Fast model for routine operations
        translation_model (str): Model for language translation
        vision_model (str): Vision model for OCR tasks
        vision_base_url (str): Base URL for vision API
        client (AsyncOpenAI): OpenAI-compatible client for text models
        vision_client (AsyncOpenAI): OpenAI-compatible client for vision
        timeout (int): Request timeout in seconds

    Example:
        >>> client = OVHClient()
        >>> text, confidence = await client.extract_text_with_vision(
        ...     image_data=pdf_bytes,
        ...     file_type="pdf"
        ... )
        >>> print(f"Extracted {len(text)} characters with {confidence:.0%} confidence")

    Note:
        All methods that call AI models return token usage information for
        cost tracking. The client automatically selects the optimal model
        based on task complexity.
    """

    def __init__(self) -> None:
        # Load configuration from settings
        self.access_token = settings.ovh_api_token
        self.base_url = settings.ovh_ai_base_url

        # Different models for different tasks
        self.main_model = settings.ovh_main_model
        self.preprocessing_model = settings.ovh_preprocessing_model
        self.translation_model = settings.ovh_translation_model

        # Vision model for OCR tasks
        self.vision_model = settings.ovh_vision_model
        self.vision_base_url = settings.ovh_vision_base_url

        # Define which prompt types should use fast model for speed optimization
        self.fast_model_prompt_types = {
            "preprocessing_prompt",
            "language_translation_prompt",
            "grammar_check_prompt",
            "final_check_prompt",
            "formatting_prompt",
        }

        # ⚡ NOTE: PII filtering now happens in worker before pipeline execution
        # No privacy filter needed here - text arrives pre-cleaned

        # Debug logging for configuration (only if debug enabled)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("🔍 OVH Client Initialization:")
            logger.debug(f"   - Access Token: {'✅ Set' if self.access_token else '❌ NOT SET'}")
            logger.debug(
                f"   - Token Length: {len(self.access_token) if self.access_token else 0} chars"
            )
            logger.debug(f"   - Base URL: {self.base_url}")
            logger.debug(f"   - Main Model: {self.main_model}")
            logger.debug(f"   - Vision Model: {self.vision_model}")
            logger.debug(f"   - Vision URL: {self.vision_base_url}")
            logger.debug(f"   - USE_OVH_ONLY: {settings.use_ovh_only}")

        if not self.access_token:
            logger.warning("⚠️ OVH_AI_ENDPOINTS_ACCESS_TOKEN not set - API calls will fail!")
            logger.warning("   Please set the following environment variables in Railway:")
            logger.warning("   - OVH_AI_ENDPOINTS_ACCESS_TOKEN=your-token-here")
            logger.warning("   - OVH_AI_BASE_URL=https://oai.endpoints.kepler.ai.cloud.ovh.net/v1")

        # Initialize OpenAI client for OVH (use dummy key to prevent initialization errors)
        try:
            self.client = AsyncOpenAI(
                base_url=self.base_url,
                api_key=self.access_token or "dummy-key-not-set",  # Use dummy key if not set
            )

            # Initialize separate client for vision model
            self.vision_client = AsyncOpenAI(
                base_url=self.vision_base_url, api_key=self.access_token or "dummy-key-not-set"
            )
        except Exception as e:
            logger.error(f"Failed to initialize OVH clients: {e}")
            self.client = None
            self.vision_client = None

        # Alternative HTTP client for direct API calls
        self.timeout = settings.ai_timeout_seconds

    async def check_connection(self) -> tuple[bool, str]:
        """Verify connectivity and authentication with OVH AI Endpoints.

        Performs a simple test API call to validate that the client is properly
        configured and can communicate with OVH's AI infrastructure.

        Returns:
            tuple[bool, str]: A tuple containing:
                - bool: True if connection successful, False otherwise
                - str: Success message or detailed error description

        Example:
            >>> client = OVHClient()
            >>> success, message = await client.check_connection()
            >>> if success:
            ...     print(f"Connected: {message}")
            ... else:
            ...     print(f"Connection failed: {message}")

        Note:
            Provides specific error guidance for common issues:
            - 401: Invalid or expired API token
            - 404: Model not found or unavailable
            - Timeout: Network connectivity issues
        """
        if not self.access_token:
            error = (
                "OVH API token not configured - OVH_AI_ENDPOINTS_ACCESS_TOKEN is empty or not set"
            )
            logger.error(f"❌ {error}")
            logger.error("   Please ensure the environment variable is set in Railway")
            return False, error

        if not self.client:
            error = "OVH client not initialized"
            logger.error(f"❌ {error}")
            return False, error

        try:
            logger.debug(f"🔄 Testing OVH connection to {self.base_url}")
            logger.debug(f"   Using model: {self.main_model}")
            logger.debug(
                f"   Token (last 8 chars): ...{self.access_token[-8:] if self.access_token else 'NOT SET'}"
            )

            # Try a simple completion to test connection
            response = await self.client.chat.completions.create(
                model=self.main_model,
                messages=[{"role": "user", "content": "Say 'OK' if you can read this"}],
                max_tokens=10,
                temperature=0,
            )

            if response and response.choices:
                logger.info("✅ OVH AI Endpoints connection successful")
                logger.info(f"   Response: {response.choices[0].message.content[:50]}")
                return True, "Connection successful"
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
                "grammar",
                "formatting",
                "format",
                "structure",
                "layout",
                "final check",
                "validation",
                "template",
                "language_translation",
            ]
            return any(keyword in task_lower for keyword in speed_optimized_keywords)

        return False

    async def process_medical_text_with_prompt(
        self,
        full_prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 4000,
        use_fast_model: bool = False,
    ) -> dict[str, Any]:
        """Process medical text using AI with intelligent model selection.

        Sends a complete prompt to OVH AI and returns the processed result along
        with detailed token usage for cost tracking. Automatically selects between
        high-quality (Llama 3.3 70B) and fast (Mistral Nemo) models based on task.

        Args:
            full_prompt: Complete prompt including instructions and input text
            temperature: Sampling temperature (0.0-1.0). Lower = more deterministic.
                Default 0.3 for medical accuracy.
            max_tokens: Maximum tokens to generate in response. Default 4000.
            use_fast_model: If True, uses Mistral Nemo for speed. If False, uses
                Llama 3.3 70B for quality. Default False.

        Returns:
            dict[str, Any]: Processing result containing:
                - text (str): The AI-generated response
                - input_tokens (int): Number of tokens in the prompt
                - output_tokens (int): Number of tokens in the response
                - total_tokens (int): Sum of input and output tokens
                - model (str): Name of the model that was used

        Example:
            >>> client = OVHClient()
            >>> prompt = "Translate this medical text: {text}"
            >>> result = await client.process_medical_text_with_prompt(
            ...     full_prompt=prompt,
            ...     temperature=0.3,
            ...     use_fast_model=False
            ... )
            >>> print(f"Used {result['total_tokens']} tokens")
            >>> print(f"Response: {result['text']}")

        Note:
            - Fast model (Mistral Nemo): 50-100ms faster, suitable for formatting/grammar
            - High-quality model (Llama 3.3 70B): Best for translation and medical content
            - Token usage is returned for cost tracking via AICostTracker
        """
        if not self.access_token:
            logger.error("❌ OVH API token not configured")
            return {
                "text": "Error: OVH API token not configured. Please set OVH_AI_ENDPOINTS_ACCESS_TOKEN in .env",
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
                "model": None,
            }

        # Choose model based on task type
        model_to_use = self.preprocessing_model if use_fast_model else self.main_model
        model_type = "fast" if use_fast_model else "high-quality"

        try:
            logger.debug(f"🚀 Processing with OVH {model_to_use} ({model_type})")

            # Use simple user message with the full prompt
            messages = [{"role": "user", "content": full_prompt}]

            # Make the API call using OpenAI client
            response = await self.client.chat.completions.create(
                model=model_to_use,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=0.9,
            )

            result = response.choices[0].message.content

            # ✨ NEW: Extract token usage from response
            usage = getattr(response, "usage", None)
            input_tokens = getattr(usage, "prompt_tokens", 0) if usage else 0
            output_tokens = getattr(usage, "completion_tokens", 0) if usage else 0
            total_tokens = getattr(usage, "total_tokens", 0) if usage else 0

            if not usage:
                logger.warning("⚠️ API response has no usage data")

            logger.debug(
                f"✅ OVH processing successful with {model_to_use} ({model_type}) - {total_tokens} tokens"
            )

            return {
                "text": result.strip(),
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": total_tokens,
                "model": model_to_use,
            }

        except Exception as e:
            logger.error(f"❌ OVH API error: {e}")
            return {
                "text": f"Error processing with OVH API: {str(e)}",
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
                "model": model_to_use,
            }

    async def process_prompt_with_optimization(
        self,
        full_prompt: str,
        prompt_type: str = None,
        temperature: float = 0.3,
        max_tokens: int = 4000,
    ) -> str:
        """
        Process a prompt with automatic model optimization based on prompt type.
        This is the recommended method for processing prompts in the pipeline.
        """
        use_fast = self.should_use_fast_model(prompt_type=prompt_type)

        logger.info(
            f"🔄 Processing prompt type '{prompt_type}' with {'fast' if use_fast else 'high-quality'} model"
        )

        return await self.process_medical_text_with_prompt(
            full_prompt=full_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            use_fast_model=use_fast,
        )

    async def process_medical_text(
        self,
        text: str,
        instruction: str = "Process this medical text",
        temperature: float = 0.3,
        max_tokens: int = 4000,
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
            logger.debug(f"🚀 Processing with OVH {self.main_model}")

            # Prepare the message
            messages = [
                {
                    "role": "system",
                    "content": "Du bist ein hochspezialisierter medizinischer Textverarbeiter. Befolge die Anweisungen präzise. Antworte IMMER in der gleichen Sprache wie der Eingabetext.",
                },
                {"role": "user", "content": f"{instruction}\n\nText to process:\n{text}"},
            ]

            # Make the API call using OpenAI client
            response = await self.client.chat.completions.create(
                model=self.main_model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=0.9,
            )

            result = response.choices[0].message.content
            logger.debug("✅ OVH processing successful")
            return result.strip()

        except Exception as e:
            logger.error(f"❌ OVH API error: {e}")
            return f"Error processing with OVH API: {str(e)}"

    async def preprocess_medical_text(
        self, text: str, temperature: float = 0.3, max_tokens: int = 4000
    ) -> str:
        """
        Preprocess medical text - first removes PII locally, then optionally uses OVH
        """
        logger.info(f"📄 PREPROCESSING PIPELINE STARTED ({len(text)} characters)")

        # ⚡ PII REMOVAL NOW HAPPENS IN WORKER (before pipeline)
        # This preprocessing step no longer needs to remove PII
        # Text arrives here already cleaned by OptimizedPrivacyFilter in worker
        logger.info("ℹ️  [2/3] Text already PII-filtered by worker (OptimizedPrivacyFilter)")
        cleaned_text = text

        # SCHRITT 2: Optional zusätzliche Bereinigung mit OVH (wenn API verfügbar)
        # Dies ist jetzt optional - wenn OVH nicht verfügbar, verwenden wir nur lokale Bereinigung
        if not self.access_token:
            logger.debug("ℹ️ OVH API not configured, using local PII removal only")
            return cleaned_text  # Return locally cleaned text

        try:
            logger.debug(f"🔧 Additional preprocessing with OVH {self.preprocessing_model}")

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
            messages = [{"role": "user", "content": full_prompt}]

            response = await self.client.chat.completions.create(
                model=self.preprocessing_model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=0.9,
            )

            result = response.choices[0].message.content

            logger.info(f"✅ OVH preprocessing completed: {len(result)} characters (reduced by {len(text) - len(result)})")

            # Clean up formatting
            import re

            result = re.sub(r"^\s*\d+[.)]\s*([•\-\*])", r"\1", result, flags=re.MULTILINE)
            result = re.sub(r"^([•\-\*])\s*[•\-\*]+\s*", r"\1 ", result, flags=re.MULTILINE)
            result = re.sub(r"([•\-\*])\s*\1+", r"\1", result)

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
        custom_prompt: str | None = None,
    ) -> tuple[str, float]:
        """Translate simplified medical text to target language with quality scoring.

        Translates patient-friendly medical text to another language while preserving
        formatting, medical terms, and numerical values. Automatically evaluates
        translation quality based on multiple indicators.

        Args:
            simplified_text: German medical text already simplified for patients
            target_language: Target language code (e.g., "English", "French", "Spanish")
            temperature: AI temperature (0.0-1.0). Default 0.3 for accuracy.
            max_tokens: Maximum response tokens. Default 4000.
            custom_prompt: Optional custom translation prompt. If None, uses
                default prompt with strict formatting rules.

        Returns:
            tuple[str, float]: A tuple containing:
                - str: Translated text with preserved formatting
                - float: Translation quality confidence (0.0-1.0)

        Example:
            >>> client = OVHClient()
            >>> de_text = "Ihr Blutdruck ist erhöht (145/90 mmHg)."
            >>> en_text, confidence = await client.translate_to_language(
            ...     simplified_text=de_text,
            ...     target_language="English"
            ... )
            >>> print(f"Translation ({confidence:.0%} confidence): {en_text}")
            >>> # Output: "Your blood pressure is elevated (145/90 mmHg)."

        Note:
            **Quality Indicators**:
            - Text length comparison (0.7-1.5 ratio expected)
            - Symbol preservation (bullets, arrows, emojis)
            - Structure preservation (formatting, line breaks)

            **Translation Rules**:
            - Numbers and units preserved exactly
            - Medical symbols (•, →, ##) unchanged
            - Formatting (line breaks, indentation) maintained
        """
        if not self.access_token:
            logger.error("❌ OVH API token not configured")
            return simplified_text, 0.0

        try:
            logger.debug(f"🌐 Translating to {target_language} with OVH {self.translation_model}")

            if custom_prompt:
                # Use custom prompt and replace placeholders
                translation_prompt = custom_prompt.replace("{language}", target_language).replace(
                    "{text}", simplified_text
                )
                logger.info("📝 Using custom language translation prompt")
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
                logger.info("📝 Using default language translation prompt")

            messages = [{"role": "user", "content": translation_prompt}]

            response = await self.client.chat.completions.create(
                model=self.translation_model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=0.9,
            )

            result = response.choices[0].message.content
            logger.debug("✅ OVH language translation successful")

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

        emoji_pattern = (
            r"[😀-🿿]|[\U0001F300-\U0001F5FF]|[\U0001F600-\U0001F64F]|[\U0001F680-\U0001F6FF]"
        )
        original_emojis = len(re.findall(emoji_pattern, original))
        translated_emojis = len(re.findall(emoji_pattern, translated))

        if original_emojis > 0:
            emoji_retention = min(translated_emojis / original_emojis, 1.0)
            confidence += emoji_retention * 0.1

        return min(confidence, 1.0)

    async def generate_streaming(
        self, prompt: str, temperature: float = 0.3, max_tokens: int = 4000
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
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            )

            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            logger.error(f"❌ OVH streaming error: {e}")
            yield f"Streaming error: {str(e)}"

    async def translate_medical_document(
        self, text: str, document_type: str = "universal", custom_prompts: Any | None = None
    ) -> tuple[str, str, float, str]:
        """
        Main processing using OVH Meta-Llama-3.3-70B for medical document translation

        Returns:
            tuple[str, str, float, str]: (translated_text, doc_type, confidence, cleaned_original)
        """
        try:
            logger.info(f"🌍 TRANSLATION PIPELINE STARTED ({len(text)} characters)")

            # Create the comprehensive instruction for medical translation (in German)
            if custom_prompts and hasattr(custom_prompts, "translation_prompt"):
                instruction = custom_prompts.translation_prompt
                logger.info(f"📝 Using custom translation prompt for {document_type}")
            else:
                instruction = self._get_medical_translation_instruction()
                logger.info(f"📝 Using default translation prompt for {document_type}")

            # Format the complete prompt
            full_prompt = f"""{instruction}

ORIGINAL MEDIZINISCHER TEXT:
{text}

ÜBERSETZUNG IN EINFACHER SPRACHE:"""

            # Process with OVH API using the formatted prompt (main translation - use high-quality model)
            translated_text = await self.process_medical_text_with_prompt(
                full_prompt=full_prompt,
                temperature=0.3,
                max_tokens=4000,
                use_fast_model=False,  # Main translation needs quality
            )

            # Improve formatting for bullet points and arrows
            translated_text = self._improve_formatting(translated_text)

            # Evaluate quality
            confidence = self._evaluate_translation_quality(text, translated_text)

            logger.info(f"✅ TRANSLATION COMPLETED: {len(translated_text)} characters, confidence: {confidence:.2%}")

            return translated_text, document_type, confidence, text

        except Exception as e:
            logger.error(f"❌ OVH translation failed: {e}")
            return f"Translation error: {str(e)}", "error", 0.0, text

    def _get_medical_translation_instruction(self) -> str:
        """Get the comprehensive medical translation instruction"""

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

        return base_instruction + universal_instruction

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
            "this means",
            "simply put",
            "in other words",
            "das bedeutet",
            "einfach gesagt",
            "mit anderen worten",
        ]
        translated_lower = translated.lower()
        found_indicators = sum(
            1 for indicator in simple_indicators if indicator in translated_lower
        )
        confidence += min(found_indicators * 0.05, 0.1)

        return min(confidence, 1.0)

    def _improve_formatting(self, text: str) -> str:
        """
        Minimale Formatierung - konvertiert Bullet Points zu Standard Markdown
        """
        import re

        # Ersetze alle Bullet-Symbole (•) durch Standard Markdown (-)
        text = re.sub(r"^•", "-", text, flags=re.MULTILINE)
        text = re.sub(r"\n•", "\n-", text)

        # Stelle sicher dass Unterpunkte korrekt formatiert sind
        text = re.sub(r"^  →", "  - →", text, flags=re.MULTILINE)

        # Entferne mehrfache Leerzeilen
        text = re.sub(r"\n{3,}", "\n\n", text)

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
                use_fast_model=True,  # Formatting is routine task - use fast model
            )

            # Apply additional formatting improvements
            return self._improve_formatting(formatted_text)

        except Exception as e:
            logger.error(f"Error formatting text: {e}")
            # Return original text with basic formatting if AI formatting fails
            return self._improve_formatting(text)

    async def extract_text_with_vision(
        self,
        image_data: bytes | Image.Image,
        file_type: str = "image",
        confidence_threshold: float = 0.7,
    ) -> tuple[str, float]:
        """Extract text from images using Qwen 2.5 VL vision model with OCR.

        Performs advanced OCR on images using OVH's vision AI model. Handles
        complex medical documents including tables, multi-column layouts, and
        handwritten text. Provides confidence scoring based on text quality.

        Args:
            image_data: Image content as raw bytes or PIL Image object
            file_type: Type of source file ("image", "pdf", "jpg", "png").
                Used for format detection and logging.
            confidence_threshold: Minimum confidence score (0.0-1.0) to consider
                extraction successful. Default 0.7.

        Returns:
            tuple[str, float]: A tuple containing:
                - str: Extracted text with preserved formatting (tables use pipe syntax)
                - float: Confidence score (0.0-1.0) based on text quality indicators

        Raises:
            Exception: On API failures, returns error message as text with 0.0 confidence

        Example:
            >>> client = OVHClient()
            >>> with open("medical_report.pdf", "rb") as f:
            ...     pdf_bytes = f.read()
            >>> text, confidence = await client.extract_text_with_vision(
            ...     image_data=pdf_bytes,
            ...     file_type="pdf"
            ... )
            >>> if confidence > 0.7:
            ...     print(f"High quality extraction: {len(text)} characters")

        Note:
            - Table formatting: Uses pipe separators (| Col1 | Col2 |)
            - Medical terms: Preserved exactly as written
            - Unclear text: Marked with [unclear] placeholder
            - Timeout: 180 seconds for complex multi-page documents
            - Confidence factors: Text length, medical terms, table structure
        """
        if not self.access_token or not self.vision_client:
            logger.error("❌ OVH vision client not configured")
            return "Error: OVH vision client not configured", 0.0

        try:
            logger.info(f"🔍 Starting vision OCR with Qwen 2.5 VL for {file_type}")

            # Convert image to base64 with proper MIME type detection (like OVH example)

            if isinstance(image_data, Image.Image):
                # Convert PIL Image to bytes
                buffered = BytesIO()
                # Save as PNG for best quality
                image_data.save(buffered, format="PNG")
                image_bytes = buffered.getvalue()
                mime_type = "image/png"
            else:
                image_bytes = image_data
                # Try to detect MIME type, default to PNG for PDFs converted to images
                mime_type = "image/png"  # Default for PDF->image conversion

            # Encode to base64 exactly like OVH example
            encoded_image = (
                f"data:{mime_type};base64,{base64.b64encode(image_bytes).decode('utf-8')}"
            )

            # Create medical OCR prompt
            ocr_prompt = self._get_medical_ocr_prompt()

            # Prepare messages for vision model (exactly like OVH example)
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": ocr_prompt},
                        {"type": "image_url", "image_url": {"url": encoded_image}},
                    ],
                }
            ]

            # Make API call to Qwen 2.5 VL using direct HTTP request
            # OVH endpoints may have different structure than OpenAI
            logger.info(f"🚀 Calling Qwen 2.5 VL vision API at {self.vision_base_url}")

            # Try direct HTTP call with reasonable timeout for vision processing
            vision_timeout = 180.0  # 3 minutes timeout for complex multi-page vision processing
            async with httpx.AsyncClient(timeout=vision_timeout) as client:
                headers = {
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json",
                }

                # Payload structure exactly matching OVH example
                payload = {
                    "max_tokens": 4000,
                    "messages": messages,
                    "model": self.vision_model,
                    "temperature": 0.1,
                }

                # Use the correct OVH vision endpoint only
                endpoint_url = f"{self.vision_base_url}/api/openai_compat/v1/chat/completions"

                logger.info(f"🔄 Calling endpoint: {endpoint_url}")
                response = await client.post(endpoint_url, headers=headers, json=payload)

                if response.status_code == 200:
                    response_data = response.json()
                    logger.info(f"✅ Success with endpoint: {endpoint_url}")
                else:
                    error_text = response.text
                    logger.error(f"❌ Vision API failed {response.status_code}: {error_text[:200]}")
                    raise Exception(f"Vision API error {response.status_code}: {error_text}")

            # Parse response from the successful endpoint call
            if "choices" in response_data and len(response_data["choices"]) > 0:
                extracted_text = response_data["choices"][0]["message"]["content"]
            else:
                logger.error(f"❌ Unexpected response format: {response_data}")
                extracted_text = "Unerwartetes Antwortformat vom Vision-API."

            if not extracted_text or len(extracted_text.strip()) < 10:
                logger.warning("⚠️ Vision OCR returned very short text")
                return "Kein Text im Bild erkannt.", 0.1

            # Calculate confidence based on text quality
            confidence = self._calculate_vision_ocr_confidence(extracted_text)

            logger.info(
                f"✅ Vision OCR successful: {len(extracted_text)} characters, confidence: {confidence:.2%}"
            )

            return extracted_text.strip(), confidence

        except Exception as e:
            error_msg = str(e) if str(e) else "Unknown error occurred"
            logger.error(f"❌ Vision OCR failed: {error_msg}")
            logger.error(f"❌ Exception type: {type(e).__name__}")

            # Provide specific error messages based on common failure patterns
            if "timeout" in error_msg.lower() or "TimeoutError" in str(type(e)):
                error_text = "Vision OCR timeout - document may be too complex or server overloaded"
            elif "404" in error_msg or "Not Found" in error_msg:
                error_text = (
                    "Vision API endpoint not found - service may be temporarily unavailable"
                )
            elif "401" in error_msg or "unauthorized" in error_msg.lower():
                error_text = "Vision API authentication failed - token may be invalid"
            elif "429" in error_msg or "rate" in error_msg.lower():
                error_text = "Vision API rate limit exceeded - too many concurrent requests"
            elif "500" in error_msg or "Internal Server Error" in error_msg:
                error_text = "Vision API internal server error - temporary service issue"
            elif not error_msg or error_msg.strip() == "":
                error_text = "Vision API call failed with empty response - network or server issue"
            else:
                error_text = f"Vision OCR error: {error_msg}"

            return error_text, 0.0

    def _get_medical_ocr_prompt(self) -> str:
        """
        Get simplified and more direct OCR prompt for medical documents
        """
        return """Extract ALL visible text from this medical document image with perfect structure preservation.

**CRITICAL TABLE FORMATTING RULES:**
- If you see a table, format it using pipe separators: | Column1 | Column2 | Column3 |
- Each table row must be on its own line
- Align columns consistently
- Preserve headers and data relationships
- Example table format:
  | Parameter | Wert | Referenzbereich | Einheit |
  | Glukose | 95 | 70-110 | mg/dl |
  | Hämoglobin | 14.2 | 12.0-16.0 | g/dl |

**TEXT FORMATTING RULES:**
- Keep paragraph structure with proper line breaks
- Preserve headers, subheaders, and section divisions
- Maintain list formatting (bullet points, numbers)
- Keep date/time formatting intact
- Preserve medical terminology exactly as written

**QUALITY REQUIREMENTS:**
- Extract every visible character, number, and symbol
- Include all medical values, units, and reference ranges
- Mark unclear text as [unclear] but try to read everything
- Do NOT add extra line breaks between table rows
- Do NOT split table cells across multiple lines
- Do NOT interpret or change medical terms

Begin text extraction with perfect structure preservation:"""

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
            "laborwerte",
            "befund",
            "diagnose",
            "patient",
            "arzt",
            "blutbild",
            "urin",
            "röntgen",
            "mrt",
            "ct",
            "ultraschall",
            "mg/dl",
            "mmol/l",
            "µg/ml",
            "ng/ml",
            "u/l",
            "iu/l",
            "normal",
            "pathologisch",
            "auffällig",
            "unauffällig",
        ]

        text_lower = text.lower()
        found_terms = sum(1 for term in medical_terms if term in text_lower)
        confidence += min(found_terms * 0.01, 0.1)

        # Structure indicators (tables, lists)
        import re

        # Reward proper table formatting with pipes
        table_rows = len(re.findall(r"\|.*\|.*\|", text))
        if table_rows >= 2:  # At least header + one data row
            confidence += min(table_rows * 0.01, 0.1)  # Up to 0.1 bonus for well-formatted tables
            logger.debug(
                f"📊 Found {table_rows} properly formatted table rows, confidence boost: +{min(table_rows * 0.01, 0.1):.3f}"
            )

        # Basic structure indicators
        if "|" in text or "- " in text or "## " in text:
            confidence += 0.02

        # Number indicators (likely measurements) - more weight for medical values
        numbers_with_units = len(
            re.findall(
                r"\d+[.,]?\d*\s*(mg/dl|mmol/l|µg/l|ng/ml|u/l|iu/l|g/l|%|/µl)", text, re.IGNORECASE
            )
        )
        confidence += min(numbers_with_units * 0.008, 0.08)  # Higher reward for medical units

        # Penalize weird line breaks (common OCR issue)
        excessive_breaks = len(re.findall(r"\n\s*\n\s*\n", text))  # 3+ consecutive line breaks
        confidence -= min(excessive_breaks * 0.02, 0.05)  # Penalty for formatting issues

        return min(confidence, 0.95)  # Cap at 95%

    async def process_multiple_images_ocr(
        self, images: list[bytes | Image.Image], merge_strategy: str = "sequential"
    ) -> tuple[str, float]:
        """Process multiple images with parallel OCR and intelligent merging.

        Extracts text from multiple images concurrently using vision AI, then
        merges the results using the specified strategy. Includes retry logic,
        concurrency control, and comprehensive error handling for production use.

        Args:
            images: List of images to process. Each can be raw bytes or PIL Image.
            merge_strategy: Strategy for combining results. Options:
                - "sequential": Adds page separators between each page
                - "smart": Intelligently detects continuation vs new sections

        Returns:
            tuple[str, float]: A tuple containing:
                - str: Merged text from all pages with proper formatting
                - float: Average confidence score across all pages

        Example:
            >>> client = OVHClient()
            >>> images = [page1_bytes, page2_bytes, page3_bytes]
            >>> text, confidence = await client.process_multiple_images_ocr(
            ...     images=images,
            ...     merge_strategy="smart"
            ... )
            >>> print(f"Extracted {len(text)} chars from {len(images)} pages")
            >>> print(f"Average confidence: {confidence:.0%}")

        Note:
            **Performance Optimizations**:
            - Parallel processing with semaphore (max 2 concurrent API calls)
            - Retry logic: Up to 3 attempts per image with exponential backoff
            - Failed pages: Included with [ERROR] markers to maintain page order

            **Merge Strategies**:
            - Sequential: "--- Seite 1 ---\\nText\\n\\n--- Seite 2 ---"
            - Smart: Detects sentence continuation (commas, conjunctions)

            **Error Handling**:
            - Individual page failures don't stop processing
            - Failed pages tracked and reported in logs
            - Returns partial results if some pages succeed
        """
        if not images:
            return "No images provided", 0.0

        logger.info(f"🔄 Processing {len(images)} images with vision OCR")

        ocr_results = []
        total_confidence = 0.0

        # Process all images in parallel for much faster performance
        import asyncio

        logger.info("🚀 Starting parallel OCR processing for all images")

        # Limit concurrent API calls to prevent overwhelming OVH servers
        semaphore = asyncio.Semaphore(2)  # Max 2 concurrent vision API calls for stability

        async def process_single_image(i: int, image: bytes | Image.Image) -> dict:
            """Process a single image with retry logic and concurrency control"""
            async with semaphore:  # Limit concurrent API calls
                logger.info(f"📄 Processing image {i}/{len(images)} in parallel")

                # Retry logic for failed OCR calls
                max_retries = 2
                retry_delay = 2  # seconds

                for attempt in range(max_retries + 1):
                    try:
                        text, confidence = await self.extract_text_with_vision(image, f"image_{i}")

                        # Check for successful extraction
                        if (
                            text
                            and len(text.strip()) > 20
                            and not text.startswith("Vision OCR error")
                        ):
                            logger.info(
                                f"✅ Image {i} processed: {len(text)} chars, confidence: {confidence:.2%}"
                            )
                            return {
                                "page": i,
                                "text": text,
                                "confidence": confidence,
                                "success": True,
                            }
                        if attempt < max_retries:
                            # Failed but can retry
                            logger.warning(
                                f"⚠️ Image {i} attempt {attempt + 1} failed: {text[:100]}... - retrying in {retry_delay}s"
                            )
                            await asyncio.sleep(retry_delay)
                            retry_delay *= 1.5  # Exponential backoff
                        else:
                            # Final attempt failed
                            logger.error(
                                f"❌ Image {i} failed after {max_retries + 1} attempts: {text}"
                            )
                            return {
                                "page": i,
                                "text": text
                                or f"Vision OCR failed after {max_retries + 1} attempts",
                                "confidence": 0.0,
                                "success": False,
                            }

                    except Exception as e:
                        if attempt < max_retries:
                            logger.warning(
                                f"⚠️ Image {i} attempt {attempt + 1} exception: {e} - retrying in {retry_delay}s"
                            )
                            await asyncio.sleep(retry_delay)
                            retry_delay *= 1.5
                        else:
                            logger.error(
                                f"❌ Image {i} failed after {max_retries + 1} attempts with exception: {e}"
                            )
                            return {
                                "page": i,
                                "text": f"Vision OCR exception after {max_retries + 1} attempts: {e}",
                                "confidence": 0.0,
                                "success": False,
                            }
                return None

        # Create tasks for all images
        tasks = [process_single_image(i, image) for i, image in enumerate(images, 1)]

        # Process all images concurrently
        parallel_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results - include both successful and failed pages for complete coverage
        failed_pages = []
        for result in parallel_results:
            if isinstance(result, Exception):
                logger.error(f"❌ Parallel OCR task failed: {result}")
                continue

            if result["success"]:
                ocr_results.append(
                    {
                        "page": result["page"],
                        "text": result["text"],
                        "confidence": result["confidence"],
                    }
                )
                total_confidence += result["confidence"]
            else:
                # Keep track of failed pages for reporting
                failed_pages.append(result["page"])
                # Add placeholder text for failed pages to maintain page order
                ocr_results.append(
                    {
                        "page": result["page"],
                        "text": f"[ERROR: Page {result['page']} extraction failed - {result['text']}]",
                        "confidence": 0.0,
                    }
                )

        if not ocr_results:
            return "Failed to extract text from any image", 0.0

        # Log partial failures
        if failed_pages:
            logger.warning(f"⚠️ Failed to extract from {len(failed_pages)} pages: {failed_pages}")
            logger.warning(
                f"✅ Successfully extracted from {len(ocr_results) - len(failed_pages)} pages"
            )

        # Merge results based on strategy
        if merge_strategy == "sequential":
            merged_text = self._merge_sequential(ocr_results)
        elif merge_strategy == "smart":
            merged_text = self._merge_smart(ocr_results)
        else:
            merged_text = self._merge_sequential(ocr_results)

        avg_confidence = total_confidence / len(ocr_results)

        logger.info(
            f"🎯 Multi-image OCR complete: {len(merged_text)} total chars, avg confidence: {avg_confidence:.2%}"
        )

        return merged_text, avg_confidence

    def _merge_sequential(self, ocr_results: list[dict]) -> str:
        """
        Merge OCR results in sequential order with page separators
        """
        merged_parts = []

        for result in sorted(ocr_results, key=lambda x: x["page"]):
            page_text = result["text"]
            page_num = result["page"]

            # Add page header
            merged_parts.append(f"--- Seite {page_num} ---")
            merged_parts.append(page_text)
            merged_parts.append("")  # Empty line between pages

        return "\n".join(merged_parts)

    def _merge_smart(self, ocr_results: list[dict]) -> str:
        """
        Intelligently merge OCR results with context awareness
        """
        if len(ocr_results) == 1:
            return ocr_results[0]["text"]

        merged_parts = []

        for i, result in enumerate(sorted(ocr_results, key=lambda x: x["page"])):
            page_text = result["text"].strip()

            if i == 0:
                # First page - add as is
                merged_parts.append(page_text)
            else:
                # Subsequent pages - check for continuation
                prev_text = merged_parts[-1] if merged_parts else ""

                # Simple heuristic: if previous page ends mid-sentence, continue
                if prev_text.rstrip().endswith((",", "-", "und", "oder", "sowie")):
                    # Likely continuation - merge without page break
                    merged_parts.append(page_text)
                else:
                    # New section - add page separator
                    merged_parts.append(f"\n--- Seite {result['page']} ---\n")
                    merged_parts.append(page_text)

        return "\n".join(merged_parts)
