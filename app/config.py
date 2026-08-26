import os
from dotenv import load_dotenv

load_dotenv()

OLLAMA_BASE_URL       = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
OLLAMA_MODEL          = os.getenv("OLLAMA_MODEL", "llama3.1")
OLLAMA_RELEVANCE_MODEL = os.getenv("OLLAMA_RELEVANCE_MODEL", OLLAMA_MODEL)
OLLAMA_EMBED_MODEL    = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
OLLAMA_NUM_CTX        = int(os.getenv("OLLAMA_NUM_CTX", "8192"))
OLLAMA_SMART_MODEL    = os.getenv("OLLAMA_SMART_MODEL", OLLAMA_MODEL)
OLLAMA_SMART_NUM_CTX  = int(os.getenv("OLLAMA_SMART_NUM_CTX", "16384"))
OLLAMA_MAX_REPLY_TOKENS = int(os.getenv("OLLAMA_MAX_REPLY_TOKENS", "220"))

BRAVE_API_KEY       = os.getenv("BRAVE_API_KEY", "")
TOOL_MAX_ROUNDS     = int(os.getenv("TOOL_MAX_ROUNDS", "3"))
FETCH_URL_MAX_CHARS = int(os.getenv("FETCH_URL_MAX_CHARS", "4000"))

QDRANT_HOST        = os.getenv("QDRANT_HOST", "qdrant")
QDRANT_PORT         = int(os.getenv("QDRANT_PORT", "6333"))
QDRANT_COLLECTION   = os.getenv("QDRANT_COLLECTION", "boopbot_lore")
QDRANT_EMBED_DIMS   = int(os.getenv("QDRANT_EMBED_DIMS", "768"))
QDRANT_API_KEY      = os.getenv("QDRANT_API_KEY", "")
# Built from host/port with an explicit scheme (overridable via QDRANT_URL for e.g.
# Qdrant Cloud). Passing this as "url" rather than bare host/port matters once an
# api_key is set: qdrant-client defaults https=True whenever an api_key is present
# and no scheme says otherwise, which breaks a plain-http self-hosted Qdrant.
QDRANT_URL = os.getenv("QDRANT_URL", f"http://{QDRANT_HOST}:{QDRANT_PORT}")

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

HISTORY_MAX_TURNS   = int(os.getenv("HISTORY_MAX_TURNS", "12"))
HISTORY_TTL_SECONDS = int(os.getenv("HISTORY_TTL_SECONDS", "21600"))
LORE_TOP_K          = int(os.getenv("LORE_TOP_K", "5"))

# How often the background sweep checks for idle channels, and how much remaining
# history TTL counts as "about to expire" (i.e. summarize now, before it's gone).
# The threshold should stay comfortably larger than the interval, or a channel could
# slip from "not yet idle" to "already expired" between two sweeps.
IDLE_SWEEP_INTERVAL_SECONDS    = int(os.getenv("IDLE_SWEEP_INTERVAL_SECONDS", "300"))
IDLE_SUMMARY_THRESHOLD_SECONDS = int(os.getenv("IDLE_SUMMARY_THRESHOLD_SECONDS", "600"))

CHATBOT_CONTEXT_FILE = os.getenv("CHATBOT_CONTEXT_FILE", "/app/persona/chatbot_context.txt")
BRAIN_SHARED_SECRET  = os.getenv("BRAIN_SHARED_SECRET", "")
