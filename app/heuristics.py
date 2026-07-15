import re
from typing import Optional

URL_RE = re.compile(r"https?://\S+")

_QUESTION_PATTERNS = [
    r"\bwhat\s*'?s\b", r"\bwhat\s+is\b", r"\bwhat\s+are\b", r"\bwhat\s+was\b",
    r"\bwho\s+is\b", r"\bwho\s+are\b", r"\bwho\s*'?s\b",
    r"\bwhen\s+is\b", r"\bwhen\s+was\b", r"\bwhen\s+did\b",
    r"\bwhere\s+is\b", r"\bwhere\s+was\b",
    r"\bhow\s+(do|does|did)\b",
    r"\bsearch\s+for\b", r"\blook\s+up\b", r"\bgoogle\b",
    r"\bcan\s+you\s+(find|search|look\s*up)\b",
    r"\bwhat\s+happened\b",
    r"\bping\b",  # correctly looking up a name -> exact snowflake ID is an indirection
                  # task the fast model is unreliable at; escalate for a better shot at it
]
QUESTION_RE = re.compile("|".join(_QUESTION_PATTERNS), re.IGNORECASE)


def detect_escalation(content: str, image_urls: list[str]) -> Optional[str]:
    """Returns a short reason ('image'/'url'/'question') if the smart-model path
    should be used for this message, else None. Pure regex, no model call."""
    if image_urls:
        return "image"
    if URL_RE.search(content):
        return "url"
    if QUESTION_RE.search(content):
        return "question"
    return None
