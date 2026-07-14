import asyncio
from typing import Optional

from mem0 import Memory

from . import config

_memory: Optional[Memory] = None


def _build_config() -> dict:
    return {
        "llm": {
            "provider": "ollama",
            "config": {
                "model": config.OLLAMA_MODEL,
                "temperature": 0.2,
                "max_tokens": 2000,
                "ollama_base_url": config.OLLAMA_BASE_URL,
            },
        },
        "embedder": {
            "provider": "ollama",
            "config": {
                "model": config.OLLAMA_EMBED_MODEL,
                "ollama_base_url": config.OLLAMA_BASE_URL,
            },
        },
        "vector_store": {
            "provider": "qdrant",
            "config": {
                "collection_name": config.QDRANT_COLLECTION,
                "host": config.QDRANT_HOST,
                "port": config.QDRANT_PORT,
                "embedding_model_dims": config.QDRANT_EMBED_DIMS,
            },
        },
        "version": "v1.1",
    }


def _get_memory() -> Memory:
    global _memory
    if _memory is None:
        _memory = Memory.from_config(_build_config())
    return _memory


def guild_scope(guild_id: int) -> str:
    return f"guild:{guild_id}"


def user_scope(user_id: int) -> str:
    return f"user:{user_id}"


def _unwrap(result):
    if isinstance(result, dict):
        return result.get("results", [])
    return result or []


def _filters(*, agent_id: str = None, user_id: str = None) -> dict:
    filters = {}
    if agent_id:
        filters["agent_id"] = agent_id
    if user_id:
        filters["user_id"] = user_id
    return filters


async def search(query: str, *, agent_id: str = None, user_id: str = None, limit: int) -> list[dict]:
    memory = _get_memory()
    result = await asyncio.to_thread(
        memory.search, query=query, filters=_filters(agent_id=agent_id, user_id=user_id), top_k=limit
    )
    return _unwrap(result)


async def add(messages: list[dict], *, agent_id: str = None, user_id: str = None) -> dict:
    memory = _get_memory()
    return await asyncio.to_thread(memory.add, messages=messages, agent_id=agent_id, user_id=user_id)


async def get_all(*, agent_id: str = None, user_id: str = None) -> list[dict]:
    memory = _get_memory()
    result = await asyncio.to_thread(
        memory.get_all, filters=_filters(agent_id=agent_id, user_id=user_id)
    )
    return _unwrap(result)


async def delete(memory_id: str) -> None:
    memory = _get_memory()
    await asyncio.to_thread(memory.delete, memory_id=memory_id)


def first_id(add_result) -> Optional[str]:
    results = _unwrap(add_result)
    return results[0]["id"] if results else None
