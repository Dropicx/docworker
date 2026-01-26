"""
AWMF Document data model.

Represents an AWMF guideline PDF with structured metadata parsed from
the URL/filename.
"""

from dataclasses import dataclass
import re


@dataclass
class AWMFDocument:
    """Represents an AWMF guideline PDF."""

    url: str                    # Full download URL
    filename: str               # Extracted filename
    registry_number: str        # e.g., "001-005"
    variant: str                # e.g., "l", "i", "e", "m", "add", "flow", or ""
    classification: str         # S1, S2k, S2e, S3, or ""
    title: str                  # German title
    version_date: str           # YYYY-MM format
    suffix: str | None          # "verlaengert", "abgelaufen", etc.

    @classmethod
    def from_url(cls, url: str) -> "AWMFDocument":
        """
        Parse AWMF PDF URL into structured data.

        AWMF filename patterns:
        - 001-005l_S1_Rueckenmarksnahe-Regionalanaesthesien_2023-12.pdf
        - 001-005l_S1_Rueckenmarksnahe-Regionalanaesthesien_2023-12-verlaengert.pdf
        - 020-025e_S3_Guideline-Title_2024-06-abgelaufen.pdf
        - 030-010_S2k_Some-Title_2025-01.pdf (no variant letter)
        """
        filename = url.split("/")[-1]

        # Pattern breakdown:
        # (\d{3}-\d{3})       - registry number: 001-005
        # ([a-z])?            - optional variant: l, i, e, m, etc.
        # _                   - separator
        # (S[123][ek]?)?      - optional classification: S1, S2k, S2e, S3
        # _?                  - optional separator
        # (.+?)               - title (non-greedy)
        # _(\d{4}-\d{2})      - version date: 2023-12
        # (?:-([a-z]+))?      - optional suffix: verlaengert, abgelaufen
        # \.pdf$              - file extension

        pattern = (
            r"^(\d{3}-\d{3})([a-z])?_"           # registry + optional variant
            r"(S[123][ek]?)?_?"                   # optional classification
            r"(.+?)_"                             # title
            r"(\d{4}-\d{2})"                      # version date
            r"(?:-([a-z]+))?"                     # optional suffix
            r"\.pdf$"
        )

        match = re.match(pattern, filename, re.IGNORECASE)

        if match:
            registry_number = match.group(1)
            variant = match.group(2) or ""
            classification = match.group(3) or ""
            title = match.group(4)
            version_date = match.group(5)
            suffix = match.group(6)
        else:
            # Fallback: extract what we can
            registry_number = ""
            variant = ""
            classification = ""
            title = filename.replace(".pdf", "")
            version_date = ""
            suffix = None

            # Try to at least extract registry number
            reg_match = re.match(r"^(\d{3}-\d{3})([a-z])?", filename)
            if reg_match:
                registry_number = reg_match.group(1)
                variant = reg_match.group(2) or ""

            # Try to extract date
            date_match = re.search(r"_(\d{4}-\d{2})(?:-([a-z]+))?\.pdf$", filename, re.IGNORECASE)
            if date_match:
                version_date = date_match.group(1)
                suffix = date_match.group(2)

        return cls(
            url=url,
            filename=filename,
            registry_number=registry_number,
            variant=variant,
            classification=classification,
            title=title,
            version_date=version_date,
            suffix=suffix,
        )

    @property
    def registry_key(self) -> str:
        """
        Extract registry number + variant for matching.

        Used to detect version updates (same guideline, different date).
        Example: "001-005l" or "030-010"
        """
        return f"{self.registry_number}{self.variant}"

    @property
    def base_key(self) -> str:
        """
        Extract everything except the date for version matching.

        Example:
            "001-005l_S1_Rueckenmarksnahe-Regionalanaesthesien_2023-12.pdf"
            -> "001-005l_S1_Rueckenmarksnahe-Regionalanaesthesien"

        This allows matching different versions of the same guideline.
        """
        # Remove date suffix: _YYYY-MM.pdf or _YYYY-MM-suffix.pdf
        pattern = r"_\d{4}-\d{2}(?:-[a-z]+)?\.pdf$"
        return re.sub(pattern, "", self.filename, flags=re.IGNORECASE)

    def __hash__(self):
        return hash(self.filename)

    def __eq__(self, other):
        if isinstance(other, AWMFDocument):
            return self.filename == other.filename
        return False


def extract_registry_key(filename: str) -> str:
    """
    Extract registry key from filename for version matching.

    Standalone function for use when we only have the filename string.

    Example:
        "001-005l_S1_Rueckenmarksnahe-..._2023-12.pdf"
        -> "001-005l_S1_Rueckenmarksnahe-..."

    This allows matching different versions of the same guideline.
    """
    # Remove date suffix: _YYYY-MM.pdf or _YYYY-MM-suffix.pdf
    pattern = r"_\d{4}-\d{2}(?:-[a-z]+)?\.pdf$"
    match = re.search(pattern, filename, re.IGNORECASE)
    if match:
        return filename[:match.start()]
    return filename.replace(".pdf", "")
