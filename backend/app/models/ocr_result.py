"""
OCR Result Model

Dataclass for complete OCR extraction results including structured output.
Used by OCREngineManager to return rich OCR data through the pipeline.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class OCRResult:
    """Complete OCR extraction result with structured data for semantic processing.

    This dataclass captures all output from PP-StructureV3 including:
    - Plain text extraction
    - Markdown-formatted text with tables
    - Structured JSON output with page/table/layout data
    - Confidence scores and processing metadata

    The structured_output is critical for semantic table translation,
    allowing the AI pipeline to understand what lab values mean
    (e.g., "Hämoglobin is a blood value") rather than treating them as plain text.

    Attributes:
        text: Extracted plain text content
        confidence: OCR confidence score (0.0-1.0)
        markdown: Markdown-formatted text with tables (if available)
        structured_output: PP-StructureV3 JSON with pages, tables, layout info
        processing_time: Time taken for OCR extraction in seconds
        engine: OCR engine used (e.g., "PPStructureV3", "PaddleOCR-3.x")
        mode: Extraction mode ("structured", "text", "auto")
        has_tables: Whether tables were detected in the document

    Example:
        >>> result = OCRResult(
        ...     text="Hämoglobin: 14.5 g/dL",
        ...     confidence=0.95,
        ...     markdown="| Parameter | Value | Unit |\\n|---|---|---|\\n| Hämoglobin | 14.5 | g/dL |",
        ...     structured_output={
        ...         "pages": [{
        ...             "page": 1,
        ...             "content": {
        ...                 "tables": [{
        ...                     "rows": [["Hämoglobin", "14.5", "g/dL", "13.5-17.5"]]
        ...                 }]
        ...             }
        ...         }],
        ...         "total_pages": 1
        ...     },
        ...     engine="PPStructureV3"
        ... )
    """

    # Required fields
    text: str
    confidence: float

    # Optional structured data (from PP-StructureV3)
    markdown: str | None = None
    structured_output: dict[str, Any] | None = None

    # Metadata
    processing_time: float = 0.0
    engine: str = "UNKNOWN"
    mode: str = "text"

    # Computed properties
    @property
    def has_tables(self) -> bool:
        """Check if structured output contains tables."""
        if not self.structured_output:
            return False

        pages = self.structured_output.get("pages", [])
        for page in pages:
            content = page.get("content", {})
            # Check various possible table locations in PP-StructureV3 output
            if content.get("tables"):
                return True
            if isinstance(content, dict):
                for key, value in content.items():
                    if "table" in key.lower() and value:
                        return True
        return False

    @property
    def table_count(self) -> int:
        """Count total tables across all pages."""
        if not self.structured_output:
            return 0

        count = 0
        pages = self.structured_output.get("pages", [])
        for page in pages:
            content = page.get("content", {})
            if isinstance(content, dict):
                tables = content.get("tables", [])
                if isinstance(tables, list):
                    count += len(tables)
        return count

    @property
    def page_count(self) -> int:
        """Get total page count from structured output."""
        if not self.structured_output:
            return 1
        return self.structured_output.get("total_pages", 1)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "text": self.text,
            "confidence": self.confidence,
            "markdown": self.markdown,
            "structured_output": self.structured_output,
            "processing_time": self.processing_time,
            "engine": self.engine,
            "mode": self.mode,
            "has_tables": self.has_tables,
            "table_count": self.table_count,
            "page_count": self.page_count,
        }

    @classmethod
    def from_legacy(cls, text: str, confidence: float) -> "OCRResult":
        """Create OCRResult from legacy tuple format for backward compatibility.

        Args:
            text: Extracted text
            confidence: Confidence score

        Returns:
            OCRResult with minimal data (no structured output)
        """
        return cls(text=text, confidence=confidence)
