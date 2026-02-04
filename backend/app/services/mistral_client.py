"""
Mistral AI Client

Client for Mistral AI chat completions used in pipeline step processing.
Uses the mistralai SDK (already installed for OCR).
"""

import logging
import os

from mistralai import Mistral

logger = logging.getLogger(__name__)

MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY", "")


class MistralClient:
    """Client for Mistral AI chat completions."""

    def __init__(self):
        """Initialize Mistral client with API key from environment."""
        if not MISTRAL_API_KEY:
            raise ValueError("MISTRAL_API_KEY environment variable not set")
        self.client = Mistral(api_key=MISTRAL_API_KEY)
        logger.info("Mistral AI client initialized")

    async def process_text(
        self,
        prompt: str,
        model: str = "mistral-large-latest",
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> dict:
        """
        Process text with Mistral model.

        Args:
            prompt: The full prompt to send to the model
            model: Mistral model name (default: mistral-large-latest)
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens in response

        Returns:
            dict with keys:
                - content: The model's response text
                - input_tokens: Number of input tokens used
                - output_tokens: Number of output tokens generated
        """
        logger.info(
            f"Calling Mistral API (model: {model}, temp: {temperature}, max_tokens: {max_tokens})"
        )

        try:
            response = self.client.chat.complete(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens,
            )

            content = response.choices[0].message.content
            input_tokens = response.usage.prompt_tokens
            output_tokens = response.usage.completion_tokens

            logger.info(
                f"Mistral response: {len(content)} chars, {input_tokens} in / {output_tokens} out tokens"
            )

            return {
                "content": content,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
            }

        except Exception as e:
            logger.error(f"Mistral API error: {e}")
            raise
