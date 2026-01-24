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

            elif response.status_code in (401, 403):
                raise Exception(f"Dify RAG authentication failed: {response.status_code}")

            elif response.status_code == 429:
                raise Exception("Dify RAG rate limit exceeded")

            else:
                raise Exception(
                    f"Dify RAG error: {response.status_code} - {response.text[:200]}"
                )

    def _build_query(self, medical_text: str, document_type: str) -> str:
        """Build German query with medical context (max 2000 chars for query)."""
        # Truncate medical text to fit within Dify query limits
        max_text_length = 1500
        truncated_text = medical_text[:max_text_length]
        if len(medical_text) > max_text_length:
            truncated_text += "..."

        query = (
            f"Basierend auf dem folgenden medizinischen Dokument "
            f"(Typ: {document_type}), welche AWMF-Leitlinien sind relevant? "
            f"Bitte nenne die wichtigsten Empfehlungen mit Registernummer, "
            f"S-Klassifikation und Empfehlungsgrad.\n\n"
            f"Dokumentinhalt:\n{truncated_text}"
        )

        return query[:2000]

    def _format_german_only(self, german_answer: str) -> str:
        """Format German-only RAG output."""
        return (
            "\n\n---\n\n"
            "## AWMF-Leitlinien Empfehlungen\n\n"
            f"{german_answer}"
        )

    def _format_bilingual(self, german_answer: str, translated: str, target_language: str) -> str:
        """Format bilingual RAG output (German + target language)."""
        lang_labels = {
            "en": "English",
            "fr": "Francais",
            "es": "Espanol",
            "it": "Italiano",
            "pt": "Portugues",
            "nl": "Nederlands",
            "pl": "Polski",
        }
        target_label = lang_labels.get(target_language, target_language.upper())

        return (
            "\n\n---\n\n"
            "## AWMF-Leitlinien Empfehlungen / AWMF Guideline Recommendations\n\n"
            "### Deutsch (Original)\n\n"
            f"{german_answer}\n\n"
            f"### {target_label} (Translation)\n\n"
            f"{translated}"
        )

    async def check_health(self) -> dict:
        """Check health of Dify RAG service."""
        if not self.url:
            return {"status": "not_configured", "url": None}

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.url}/health")

                if response.status_code == 200:
                    return {
                        "status": "healthy",
                        "url": self.url,
                        "enabled": self.is_enabled,
                    }
                else:
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
