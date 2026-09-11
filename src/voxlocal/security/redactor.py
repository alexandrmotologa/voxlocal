"""Zero-leakage PII and secret redaction filter for meeting transcripts."""

import re
from re import Pattern

# Regular expressions for secrets and PII
REDACTION_PATTERNS: dict[str, Pattern] = {
    "OPENAI_KEY": re.compile(r"\bsk-[a-zA-Z0-9]{20,}\b"),
    "GITHUB_TOKEN": re.compile(r"\bgh[pousr]_[a-zA-Z0-9]{36,}\b"),
    "AWS_KEY": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "BEARER_TOKEN": re.compile(r"(?i)\bBearer\s+[a-zA-Z0-9_\-\.]{24,}\b"),
    "CREDIT_CARD": re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b"),
    "IPV4_ADDRESS": re.compile(r"\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b"),
    "EMAIL": re.compile(r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b"),
    "PHONE_NUMBER": re.compile(r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),
    "PASSWORD_PHRASE": re.compile(r"(?i)\b(?:password|passwd|secret)(?:\s+is|\s*[:=])?\s+([^\s,;]+)"),
}


def redact_text(text: str) -> str:
    """Sanitize sensitive credentials, secrets, and PII from text.

    Args:
        text: Input string containing speech or notes.

    Returns:
        Sanitized string with sensitive tokens replaced by [REDACTED_*].
    """
    if not text:
        return text

    sanitized = text

    # Passwords with label
    def _replace_password(match: re.Match) -> str:
        full = match.group(0)
        val = match.group(1)
        return full.replace(val, "[REDACTED_PASSWORD]")

    sanitized = REDACTION_PATTERNS["PASSWORD_PHRASE"].sub(_replace_password, sanitized)

    # Specific patterns
    for name, pattern in REDACTION_PATTERNS.items():
        if name == "PASSWORD_PHRASE":
            continue
        placeholder = f"[REDACTED_{name}]"
        sanitized = pattern.sub(placeholder, sanitized)

    return sanitized
