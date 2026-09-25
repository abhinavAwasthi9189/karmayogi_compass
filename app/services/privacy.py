"""Lightweight PII scrub for text sent to a third-party LLM (Gemini). Masks
obvious personal identifiers -- email addresses and long digit sequences
(phone numbers, IDs) -- before a learner's question or chat history is put
into a prompt.

This is a best-effort regex-based redaction, not a certified PII filter. It
exists to keep obviously identifying data (an official's own email or phone
number, if they happen to type one into the Compass AI chat) out of
third-party model calls by default -- it does not replace proper data
governance for a real deployment.
"""
import re

_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_PHONE_RE = re.compile(r"(?<!\d)(?:\+?\d[\s-]?){10,13}(?!\d)")
_LONG_DIGITS_RE = re.compile(r"(?<!\d)\d{6,}(?!\d)")


def scrub(text: str) -> str:
    """Masks emails, phone-shaped digit runs, and other long digit runs
    (e.g. employee IDs) in the given text. Safe to call on empty/None."""
    if not text:
        return text
    text = _EMAIL_RE.sub("[email removed]", text)
    text = _PHONE_RE.sub("[phone number removed]", text)
    text = _LONG_DIGITS_RE.sub("[number removed]", text)
    return text