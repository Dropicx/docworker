"""AWMF Document data model."""
from dataclasses import dataclass
import re

@dataclass
class AWMFDocument:
    """Represents an AWMF guideline PDF."""
    url: str
    filename: str
    registry_number: str
    variant: str
    classification: str
    title: str
    version_date: str
    suffix: str | None

    @classmethod
    def from_url(cls, url: str) -> "AWMFDocument":
        filename = url.split("/")[-1]
        pattern = (
            r"^(\d{3}-\d{3})([a-z])?_"
            r"(S[123][ek]?)?_?"
            r"(.+?)_"
            r"(\d{4}-\d{2})"
            r"(?:-([a-z]+))?"
            r"\.pdf$"
        )
        match = re.match(pattern, filename, re.IGNORECASE)
        if match:
            return cls(
                url=url, filename=filename,
                registry_number=match.group(1), variant=match.group(2) or "",
                classification=match.group(3) or "", title=match.group(4),
                version_date=match.group(5), suffix=match.group(6),
            )
        else:
            registry_number, variant, version_date, suffix = "", "", "", None
            reg_match = re.match(r"^(\d{3}-\d{3})([a-z])?", filename)
            if reg_match:
                registry_number, variant = reg_match.group(1), reg_match.group(2) or ""
            date_match = re.search(r"_(\d{4}-\d{2})(?:-([a-z]+))?\.pdf$", filename, re.IGNORECASE)
            if date_match:
                version_date, suffix = date_match.group(1), date_match.group(2)
            return cls(url=url, filename=filename, registry_number=registry_number,
                      variant=variant, classification="", title=filename.replace(".pdf",""),
                      version_date=version_date, suffix=suffix)

    @property
    def registry_key(self) -> str:
        return f"{self.registry_number}{self.variant}"

    @property
    def base_key(self) -> str:
        pattern = r"_\d{4}-\d{2}(?:-[a-z]+)?\.pdf$"
        return re.sub(pattern, "", self.filename, flags=re.IGNORECASE)

    def __hash__(self): return hash(self.filename)
    def __eq__(self, other): return isinstance(other, AWMFDocument) and self.filename == other.filename

def extract_registry_key(filename: str) -> str:
    pattern = r"_\d{4}-\d{2}(?:-[a-z]+)?\.pdf$"
    match = re.search(pattern, filename, re.IGNORECASE)
    return filename[:match.start()] if match else filename.replace(".pdf", "")
