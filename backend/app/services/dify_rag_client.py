"""
Dify RAG Service Client

HTTP client for querying AWMF medical guidelines via self-hosted Dify RAG service.
Provides bilingual output (German + target language) by combining Dify RAG responses
with OVH translation.

Environment Variables:
    DIFY_RAG_URL: URL of Dify service (e.g., https://rag.fra-la.de)
    DIFY_RAG_API_KEY: Dify app API key (app-xxx)
    USE_DIFY_RAG: Set to 'true' to enable RAG queries

Usage:
    >>> client = DifyRAGClient()
    >>> answer, metadata = await client.query_guidelines("Diabetes Typ 2", "ARZTBRIEF", "en")
"""

import logging
import os

import httpx

logger = logging.getLogger(__name__)

# Configuration from environment
DIFY_RAG_URL = os.getenv("DIFY_RAG_URL", "")
DIFY_RAG_API_KEY = os.getenv("DIFY_RAG_API_KEY", "")
USE_DIFY_RAG = os.getenv("USE_DIFY_RAG", "false").lower() == "true"


class DifyRAGClient:
    """Client for Dify RAG service querying AWMF medical guidelines."""

    def __init__(self, url: str | None = None, api_key: str | None = None, timeout: float = 90.0):
        """
        Initialize Dify RAG client.

        Args:
            url: Override DIFY_RAG_URL from environment
            api_key: Override DIFY_RAG_API_KEY from environment
            timeout: Request timeout in seconds (default 90s, RAG is slow)
        """
        self.url = url or DIFY_RAG_URL
        self.api_key = api_key or DIFY_RAG_API_KEY
        self.timeout = timeout

        if self.url:
            logger.info(f"Dify RAG Client initialized: {self.url}")
        else:
            logger.debug("Dify RAG Client: not configured (no URL)")

    @property
    def is_enabled(self) -> bool:
        """Check if configured and enabled."""
        return bool(self.url) and bool(self.api_key) and USE_DIFY_RAG

    async def query_guidelines(
        self,
        medical_text: str,
        document_type: str = "UNKNOWN",
        target_language: str = "en",
        user_id: str = "pipeline-system",
    ) -> tuple[str, dict]:
        """
        Query AWMF guidelines knowledge base with bilingual output.

        1. Queries Dify with German prompt -> German guideline recommendations
        2. If target_language != "de", translates via OVH to target language
        3. Returns formatted bilingual output

        Args:
            medical_text: Medical document text to find guidelines for
            document_type: Document classification (ARZTBRIEF, BEFUNDBERICHT, LABORWERTE)
            target_language: Target language for translation (e.g., "en", "fr")
            user_id: User identifier for Dify session tracking

        Returns:
            Tuple of (formatted_answer, metadata)
            On failure: ("", {"skipped": True, "error": "..."})
        """
        if not self.is_enabled:
            return "", {"skipped": True, "reason": "not_enabled"}

        try:
            # Build query from medical text
            query = self._build_query(medical_text, document_type)

            # Query Dify for German guideline recommendations
            german_answer, rag_metadata = await self._query_dify(query, user_id)

            if not german_answer:
                return "", {"skipped": True, "reason": "empty_response", **rag_metadata}

            # If target language is German, return German-only format
            if target_language == "de":
                formatted = self._format_german_only(german_answer)
                return formatted, rag_metadata

            # Translate to target language via OVH
            try:
                from app.services.ovh_client import OVHClient

                ovh = OVHClient()
                translation_prompt = (
                    f"Translate the following German medical guideline recommendations to "
                    f"{target_language}. Keep medical terms accurate and preserve formatting:\n\n"
                    f"{german_answer}"
                )
                translated_result = await ovh.process_medical_text_with_prompt(
                    full_prompt=translation_prompt,
                    temperature=0.3,
                    max_tokens=4096,
                    use_fast_model=False,
                )
                translated = translated_result.get("text", "")

                if translated:
                    formatted = self._format_bilingual(german_answer, translated, target_language)
                    rag_metadata["translated"] = True
                    rag_metadata["target_language"] = target_language
                    return formatted, rag_metadata

            except Exception as translate_error:
                logger.warning(f"Translation of RAG output failed: {translate_error}")
                # Fall back to German-only
                rag_metadata["translation_error"] = str(translate_error)

            # Fallback: German-only if translation fails
            formatted = self._format_german_only(german_answer)
            return formatted, rag_metadata

        except Exception as e:
            logger.error(f"Dify RAG query failed: {e}")
            return "", {"skipped": True, "error": str(e)}

    async def _query_dify(self, query: str, user_id: str) -> tuple[str, dict]:
        """
        Send query to Dify chat-messages API.

        POST {url}/v1/chat-messages
        Headers: Authorization: Bearer {api_key}
        Body: { query, response_mode: "blocking", user }

        Returns:
            Tuple of (answer_text, metadata)
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "query": query,
            "response_mode": "blocking",
            "user": user_id,
            "inputs": {},
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.url}/v1/chat-messages",
                json=payload,
                headers=headers,
            )

            if response.status_code == 200:
                result = response.json()
                answer = result.get("answer", "")
                metadata = {
                    "conversation_id": result.get("conversation_id"),
                    "message_id": result.get("message_id"),
                    "retriever_resources": result.get("metadata", {}).get(
                        "retriever_resources", []
                    ),
                }
                return answer, metadata

            if response.status_code in (401, 403):
                raise Exception(f"Dify RAG authentication failed: {response.status_code}")

            if response.status_code == 429:
                raise Exception("Dify RAG rate limit exceeded")

            raise Exception(f"Dify RAG error: {response.status_code} - {response.text[:200]}")

    def _build_query(self, medical_text: str, document_type: str) -> str:
        """Build German query with medical context for patient-friendly output (max 2000 chars)."""
        # Truncate medical text to fit within Dify query limits
        max_text_length = 1200  # Reduced to make room for longer prompt
        truncated_text = medical_text[:max_text_length]
        if len(medical_text) > max_text_length:
            truncated_text += "..."

        query = (
            f"Du bist ein medizinischer Berater, der einem Patienten hilft, seine Gesundheit zu verstehen.\n\n"
            f"Basierend auf dem folgenden medizinischen Dokument (Typ: {document_type}), "
            f"gib dem Patienten 3-5 KURZE, VERSTÄNDLICHE Empfehlungen aus den AWMF-Leitlinien.\n\n"
            f"WICHTIGE REGELN:\n"
            f"1. Schreibe in EINFACHER SPRACHE - keine Fachbegriffe oder erkläre sie\n"
            f"2. Fokussiere auf PRAKTISCHE TIPPS - was kann der Patient TUN?\n"
            f"3. Halte jede Empfehlung KURZ (2-3 Sätze)\n"
            f"4. JEDE Empfehlung MUSS eine Quellenangabe haben im Format:\n"
            f'   📚 Quelle: AWMF Leitlinie "[Name]" (Reg.-Nr. [Nummer]), [S-Klassifikation]\n'
            f"5. Maximal 5 Empfehlungen - nur die WICHTIGSTEN\n\n"
            f"Dokumentinhalt:\n{truncated_text}"
        )

        return query[:2000]

    def _format_german_only(self, german_answer: str) -> str:
        """Format German-only RAG output with patient-friendly header."""
        return (
            "\n\n---\n\n"
            "## 📋 Empfehlungen aus medizinischen Leitlinien\n\n"
            "*Diese Empfehlungen basieren auf offiziellen deutschen Behandlungsrichtlinien (AWMF). "
            "Sie ersetzen nicht das Gespräch mit Ihrem Arzt.*\n\n"
            f"{german_answer}"
        )

    def _format_bilingual(self, german_answer: str, translated: str, target_language: str) -> str:
        """Format bilingual RAG output with patient-friendly header (German + target language)."""
        lang_labels = {
            "en": "English",
            "fr": "Français",
            "es": "Español",
            "it": "Italiano",
            "pt": "Português",
            "nl": "Nederlands",
            "pl": "Polski",
        }
        target_label = lang_labels.get(target_language, target_language.upper())

        return (
            "\n\n---\n\n"
            "## 📋 Empfehlungen aus medizinischen Leitlinien / Medical Guideline Recommendations\n\n"
            "*Diese Empfehlungen basieren auf offiziellen deutschen Behandlungsrichtlinien (AWMF). "
            "Sie ersetzen nicht das Gespräch mit Ihrem Arzt.*\n\n"
            "### Deutsch (Original)\n\n"
            f"{german_answer}\n\n"
            f"### {target_label} (Translation)\n\n"
            f"{translated}"
        )

    async def check_health(self) -> dict:
        """
        Check health of Dify RAG service.

        Dify doesn't have a standard /health endpoint, so we:
        1. Check if the server is reachable (any HTTP response)
        2. Optionally verify the API key works via /v1/parameters
        """
        if not self.url:
            return {"status": "not_configured", "url": None}

        try:
            async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
                # First check: Is the server reachable?
                # Dify root typically redirects to /apps, which is fine
                response = await client.get(self.url)

                # Any successful response (2xx, 3xx) means server is up
                if response.status_code < 400:
                    # If we have an API key, verify it works
                    if self.api_key:
                        try:
                            auth_response = await client.get(
                                f"{self.url}/v1/parameters",
                                headers={"Authorization": f"Bearer {self.api_key}"}
                            )
                            if auth_response.status_code == 200:
                                return {
                                    "status": "healthy",
                                    "url": self.url,
                                    "enabled": self.is_enabled,
                                    "api_key_valid": True,
                                }
                            elif auth_response.status_code in (401, 403):
                                return {
                                    "status": "auth_error",
                                    "url": self.url,
                                    "enabled": self.is_enabled,
                                    "error": "Invalid API key",
                                }
                        except Exception:
                            # Auth check failed but server is up
                            pass

                    return {
                        "status": "healthy",
                        "url": self.url,
                        "enabled": self.is_enabled,
                    }

                return {
                    "status": "error",
                    "url": self.url,
                    "error": f"HTTP {response.status_code}",
                }

        except httpx.TimeoutException:
            return {"status": "timeout", "url": self.url, "error": "Connection timeout"}

        except httpx.ConnectError as e:
            return {"status": "unreachable", "url": self.url, "error": str(e)}

        except Exception as e:
            return {"status": "error", "url": self.url, "error": str(e)}
