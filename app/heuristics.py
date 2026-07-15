import re
from typing import Optional

URL_RE = re.compile(r"https?://\S+")

# Explicit search intent — kept separate from generic questions so callers can
# force a real search_web call rather than leaving it to the model's discretion
# (Ollama's tool-calling has no way to *require* a tool call, and the model has
# shown it'll sometimes narrate a fake search instead of actually invoking one).
#
# Two ways a message signals "this needs a real search": naming the action
# ("search up", "look into") or naming something time-sensitive ("latest",
# "today's"). The second is deliberately broader and more durable than trying
# to enumerate every possible search verb in natural English (we already
# missed "find out", "check on", etc. once) — "the latest X" needs a real
# lookup no matter what verb is used to ask for it, or none at all.
_SEARCH_ACTION_PATTERNS = [
    r"\bsearch\s+(up|for)\b", r"\blook\s+up\b", r"\blook\s+into\b", r"\bgoogle\b",
    r"\bfind\s+out\b", r"\bfigure\s+out\b", r"\bcheck\s+on\b",
    r"\bcan\s+you\s+(find|search|look\s*up)\b",
]
_RECENCY_PATTERNS = [
    r"\blatest\b", r"\bnewest\b", r"\bcurrent(ly)?\b", r"\btoday'?s\b",
    r"\bthis\s+week\b", r"\brecent(ly)?\b", r"\bright\s+now\b", r"\bup\s+to\s+date\b",
]
SEARCH_RE = re.compile("|".join(_SEARCH_ACTION_PATTERNS + _RECENCY_PATTERNS), re.IGNORECASE)

_QUESTION_PATTERNS = [
    r"\bwhat\s*'?s\b", r"\bwhat\s+is\b", r"\bwhat\s+are\b", r"\bwhat\s+was\b",
    r"\bwho\s+is\b", r"\bwho\s+are\b", r"\bwho\s*'?s\b",
    r"\bwhen\s+is\b", r"\bwhen\s+was\b", r"\bwhen\s+did\b",
    r"\bwhere\s+is\b", r"\bwhere\s+was\b",
    r"\bhow\s+(do|does|did)\b",
    r"\bwhat\s+happened\b",
    r"\bping\b",  # correctly looking up a name -> exact snowflake ID is an indirection
                  # task the fast model is unreliable at; escalate for a better shot at it
]
QUESTION_RE = re.compile("|".join(_QUESTION_PATTERNS), re.IGNORECASE)


def detect_escalation(content: str, image_urls: list[str]) -> Optional[str]:
    """Returns a short reason ('image'/'url'/'search'/'question') if the smart-model
    path should be used for this message, else None. Pure regex, no model call."""
    if image_urls:
        return "image"
    if URL_RE.search(content):
        return "url"
    if SEARCH_RE.search(content):
        return "search"
    if QUESTION_RE.search(content):
        return "question"
    return None
