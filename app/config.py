import os
from dotenv import load_dotenv

load_dotenv()

OLLAMA_BASE_URL       = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
OLLAMA_MODEL          = os.getenv("OLLAMA_MODEL", "llama3.1")
OLLAMA_RELEVANCE_MODEL = os.getenv("OLLAMA_RELEVANCE_MODEL", OLLAMA_MODEL)
OLLAMA_EMBED_MODEL    = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
OLLAMA_NUM_CTX        = int(os.getenv("OLLAMA_NUM_CTX", "8192"))

QDRANT_HOST        = os.getenv("QDRANT_HOST", "qdrant")
QDRANT_PORT         = int(os.getenv("QDRANT_PORT", "6333"))
QDRANT_COLLECTION   = os.getenv("QDRANT_COLLECTION", "boopbot_lore")
QDRANT_EMBED_DIMS   = int(os.getenv("QDRANT_EMBED_DIMS", "768"))

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

HISTORY_MAX_TURNS   = int(os.getenv("HISTORY_MAX_TURNS", "12"))
HISTORY_TTL_SECONDS = int(os.getenv("HISTORY_TTL_SECONDS", "21600"))
LORE_TOP_K          = int(os.getenv("LORE_TOP_K", "5"))

CHATBOT_CONTEXT_FILE = os.getenv("CHATBOT_CONTEXT_FILE", "/app/persona/chatbot_context.txt")
BRAIN_SHARED_SECRET  = os.getenv("BRAIN_SHARED_SECRET", "")
