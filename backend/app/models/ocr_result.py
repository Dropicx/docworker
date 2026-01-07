"""
OCR Result Model

Dataclass for OCR extraction results.
Used by OCREngineManager to return OCR data through the pipeline.
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class OCRResult:
    """OCR extraction result with markdown output.

    Attributes:
        text: Extracted text content (plain text or markdown)
        confidence: OCR confidence score (0.0-1.0)
        markdown: Markdown-formatted text (if available)
        processing_time: Time taken for OCR extraction in seconds
        engine: OCR engine used (e.g., "MISTRAL_OCR", "PADDLEOCR")
        mode: Extraction mode ("mistral", "hybrid", "text")

    Example:
        >>> result = OCRResult(
        ...     text="# Report\\n\\nHämoglobin: 14.5 g/dL",
        ...     confidence=0.95,
        ...     markdown="# Report\\n\\n| Parameter | Value |\\n|---|---|\\n| Hämoglobin | 14.5 |",
        ...     engine="MISTRAL_OCR"
        ... )
    """

    # Required fields
    text: str
    confidence: float

    # Optional markdown output
    markdown: str | None = None

    # Metadata
    processing_time: float = 0.0
    engine: str = "UNKNOWN"
    mode: str = "text"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "text": self.text,
            "confidence": self.confidence,
            "markdown": self.markdown,
            "processing_time": self.processing_time,
            "engine": self.engine,
            "mode": self.mode,
        }

    @classmethod
    def from_legacy(cls, text: str, confidence: float) -> "OCRResult":
        """Create OCRResult from legacy tuple format for backward compatibility.

        Args:
            text: Extracted text
            confidence: Confidence score

        Returns:
            OCRResult with minimal data
        """
        return cls(text=text, confidence=confidence)
