"""
Prompt Injection Protection Module

Defense-in-depth utilities for detecting and neutralizing prompt injection
patterns in text before it enters LLM prompts. Designed for medical document
processing where aggressive text stripping would corrupt clinical content.

Strategy:
- ESCAPE characters that cause technical issues (curly braces, zero-width chars)
- DETECT & LOG suspicious patterns for admin monitoring
- Structural defenses (role separation, boundary markers, output validation)
  are handled by the callers (pipeline executor, LLM clients)
"""

import logging
import re
import unicodedata
from dataclasses import dataclass, field
from enum import IntEnum

logger = logging.getLogger(__name__)


class InjectionSeverity(IntEnum):
    """Severity levels for detected injection patterns."""
    NONE = 0
    LOW = 1      # Single pattern, likely benign
    MEDIUM = 2   # Multiple patterns or moderate-risk pattern
    HIGH = 3     # Strong injection indicators


@dataclass
class InjectionDetection:
    """A single detected injection pattern."""
    pattern_name: str
    matched_text: str
    category: str  # e.g. "role_manipulation", "boundary_attack"


@dataclass
class InjectionReport:
    """Result of scanning text for injection patterns."""
    severity: InjectionSeverity = InjectionSeverity.NONE
    detections: list[InjectionDetection] = field(default_factory=list)

    @property
    def has_detections(self) -> bool:
        return len(self.detections) > 0


# ---------------------------------------------------------------------------
# Injection pattern definitions
# ---------------------------------------------------------------------------

# Each entry: (pattern_name, regex, category)
# Patterns are matched case-insensitively. Word boundaries (\b) are used where
# appropriate to reduce false positives on legitimate medical text.

_INJECTION_PATTERNS: list[tuple[str, str, str]] = [
    # Role manipulation
    ("ignore_previous", r"\bignore\s+(all\s+)?(above|previous|prior)\s+(instructions?|prompts?|text)\b", "role_manipulation"),
    ("new_instructions", r"\b(new|updated|revised)\s+instructions?\b", "role_manipulation"),
    ("system_role", r"^(system|assistant|user)\s*:", "role_manipulation"),
    ("act_as", r"\b(you\s+are\s+now|act\s+as|pretend\s+to\s+be|roleplay\s+as)\b", "role_manipulation"),
    ("forget_everything", r"\b(forget|disregard|override)\s+(everything|all|previous|above)\b", "role_manipulation"),
    ("instead_do", r"\binstead[,\s]+(do|output|respond|write|say)\b", "instruction_override"),

    # Boundary attacks
    ("boundary_end", r"---\s*END", "boundary_attack"),
    ("boundary_delimiters", r"={5,}", "boundary_attack"),

    # Data exfiltration
    ("repeat_prompt", r"\b(repeat|output|show|display|print)\s+(the\s+|your\s+)?(system\s+prompt|instructions?|prompt)\b", "data_exfiltration"),
    ("what_told", r"\bwhat\s+(were\s+you|are\s+your)\s+(told|instructions?)\b", "data_exfiltration"),

    # Encoding evasion
    ("base64_instruction", r"\b(base64|decode|eval)\s*[:(]", "encoding_evasion"),
    ("unicode_escape", r"\\u[0-9a-fA-F]{4}", "encoding_evasion"),

    # Python format string attacks (also a crash risk)
    ("format_string_dunder", r"\{__\w+__", "format_string_attack"),
    ("format_string_globals", r"__globals__", "format_string_attack"),
]

_COMPILED_PATTERNS: list[tuple[str, re.Pattern, str]] = [
    (name, re.compile(pattern, re.IGNORECASE | re.MULTILINE), category)
    for name, pattern, category in _INJECTION_PATTERNS
]

# Zero-width and invisible Unicode characters to strip
_INVISIBLE_CHARS = frozenset([
    "\u200b",  # Zero Width Space
    "\u200c",  # Zero Width Non-Joiner
    "\u200d",  # Zero Width Joiner
    "\u200e",  # Left-to-Right Mark
    "\u200f",  # Right-to-Left Mark
    "\u2060",  # Word Joiner
    "\u2061",  # Function Application
    "\u2062",  # Invisible Times
    "\u2063",  # Invisible Separator
    "\u2064",  # Invisible Plus
    "\ufeff",  # Zero Width No-Break Space (BOM)
    "\u00ad",  # Soft Hyphen
    "\u034f",  # Combining Grapheme Joiner
    "\u061c",  # Arabic Letter Mark
    "\u115f",  # Hangul Choseong Filler
    "\u1160",  # Hangul Jungseong Filler
    "\u17b4",  # Khmer Vowel Inherent Aq
    "\u17b5",  # Khmer Vowel Inherent Aa
    "\u180e",  # Mongolian Vowel Separator
    "\uffa0",  # Halfwidth Hangul Filler
])

_INVISIBLE_CHARS_PATTERN = re.compile(
    "[" + "".join(re.escape(c) for c in _INVISIBLE_CHARS) + "]"
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def detect_injection(text: str) -> InjectionReport:
    """
    Scan input text for known prompt injection patterns.

    Returns an InjectionReport with severity and list of detections.
    Does NOT modify the text.
    """
    if not text:
        return InjectionReport()

    report = InjectionReport()

    for pattern_name, compiled, category in _COMPILED_PATTERNS:
        matches = compiled.findall(text)
        if matches:
            # Take the first match as representative
            matched_text = matches[0] if isinstance(matches[0], str) else matches[0][0] if matches[0] else pattern_name
            report.detections.append(InjectionDetection(
                pattern_name=pattern_name,
                matched_text=str(matched_text)[:100],
                category=category,
            ))

    # Calculate severity based on detections
    if not report.detections:
        report.severity = InjectionSeverity.NONE
    elif len(report.detections) == 1:
        # Single detection — could be a false positive in medical text
        report.severity = InjectionSeverity.LOW
    elif len(report.detections) <= 3:
        report.severity = InjectionSeverity.MEDIUM
    else:
        report.severity = InjectionSeverity.HIGH

    # Boost severity for high-risk categories
    high_risk_categories = {"data_exfiltration", "format_string_attack"}
    if any(d.category in high_risk_categories for d in report.detections):
        report.severity = max(report.severity, InjectionSeverity.MEDIUM)

    return report


def sanitize_for_prompt(text: str) -> tuple[str, bool]:
    """
    Sanitize text before inserting into an LLM prompt.

    Actions performed:
    1. Escape curly braces to prevent .format() crashes and variable injection
    2. Strip zero-width / invisible Unicode characters
    3. NFKC Unicode normalization to collapse homoglyphs

    Does NOT strip injection patterns (high false-positive risk with medical text).
    Detection and logging are handled separately.

    Returns:
        (sanitized_text, was_modified) — was_modified is True if any changes were made.
    """
    if not text:
        return text, False

    original = text
    result = text

    # 1. Escape curly braces: { -> {{ and } -> }}
    # This prevents .format() crashes and variable injection.
    result = result.replace("{", "{{").replace("}", "}}")

    # 2. Strip zero-width / invisible Unicode characters
    result = _INVISIBLE_CHARS_PATTERN.sub("", result)

    # 3. NFKC normalization (collapses fullwidth Latin, etc.)
    result = unicodedata.normalize("NFKC", result)

    was_modified = result != original
    return result, was_modified


def detect_prompt_leakage(output: str, system_prompt: str) -> bool:
    """
    Check if LLM output contains fragments of the system prompt,
    indicating a successful prompt extraction attack.

    Uses a sliding window of 3+ consecutive words from the system prompt.
    Short or empty prompts are skipped.

    Returns True if leakage is detected.
    """
    if not output or not system_prompt:
        return False

    # Tokenize system prompt into words (simple whitespace split)
    prompt_words = system_prompt.split()
    if len(prompt_words) < 5:
        # Too short to meaningfully detect leakage
        return False

    output_lower = output.lower()

    # Check for 4-gram matches (4 consecutive words from system prompt in output)
    window_size = 4
    for i in range(len(prompt_words) - window_size + 1):
        fragment = " ".join(prompt_words[i:i + window_size]).lower()
        if fragment in output_lower:
            return True

    return False


def log_injection_detection(
    report: InjectionReport,
    processing_id: str | None = None,
    step_name: str | None = None,
) -> None:
    """
    Log injection detection events as structured warnings.

    Called by pipeline executor after sanitize_for_prompt + detect_injection.
    """
    if not report.has_detections:
        return

    patterns_found = [
        {"name": d.pattern_name, "category": d.category, "matched": d.matched_text}
        for d in report.detections
    ]

    logger.warning(
        "SECURITY:PROMPT_INJECTION_DETECTED | "
        f"processing_id={processing_id or 'unknown'} | "
        f"step={step_name or 'unknown'} | "
        f"severity={report.severity.name} | "
        f"patterns={len(report.detections)} | "
        f"details={patterns_found}"
    )


def validate_step_output(
    step_name: str,
    output: str,
    input_text: str,
    expected_values: list[str] | None = None,
    system_prompt: str | None = None,
) -> tuple[bool, str]:
    """
    Validate LLM output for anomalies that may indicate injection manipulation.

    Checks:
    1. For classification/validation steps: first word must be in expected_values
    2. Output length ratio vs input (flag if >10x longer)
    3. System prompt leakage detection

    Returns:
        (is_valid, validation_message)
    """
    if not output:
        return False, "Empty output"

    output_stripped = output.strip()

    # Check 1: Expected values (for classification/validation steps)
    if expected_values:
        first_word = output_stripped.split()[0].upper() if output_stripped.split() else ""
        expected_upper = [v.upper() for v in expected_values]
        if first_word not in expected_upper:
            return False, (
                f"Output '{first_word}' not in expected values {expected_values}"
            )

    # Check 2: Output length ratio
    if input_text and len(input_text) > 100:
        ratio = len(output_stripped) / len(input_text)
        if ratio > 10:
            logger.warning(
                f"Suspicious output length ratio ({ratio:.1f}x) for step '{step_name}'"
            )
            # Don't fail — just warn. Some steps legitimately produce long output.

    # Check 3: System prompt leakage
    if system_prompt and detect_prompt_leakage(output_stripped, system_prompt):
        return False, "Possible system prompt leakage detected in output"

    return True, "OK"
