import json

import redis.asyncio as redis

from . import config

_pool = redis.ConnectionPool(host=config.REDIS_HOST, port=config.REDIS_PORT, decode_responses=True)


def _key(channel_id: int) -> str:
    return f"history:{channel_id}"


async def get_recent(channel_id: int) -> list[dict]:
    client = redis.Redis(connection_pool=_pool)
    raw = await client.lrange(_key(channel_id), 0, -1)
    return [json.loads(entry) for entry in raw]


async def append(channel_id: int, role: str, name: str, content: str) -> None:
    client = redis.Redis(connection_pool=_pool)
    entry = json.dumps({"role": role, "name": name, "content": content})
    key = _key(channel_id)
    async with client.pipeline() as pipe:
        pipe.rpush(key, entry)
        pipe.ltrim(key, -config.HISTORY_MAX_TURNS * 2, -1)
        pipe.expire(key, config.HISTORY_TTL_SECONDS)
        await pipe.execute()


async def clear(channel_id: int) -> None:
    client = redis.Redis(connection_pool=_pool)
    await client.delete(_key(channel_id))


async def get_ttl(channel_id: int) -> int:
    """Remaining seconds until this channel's history expires. -2 if the key
    doesn't exist (channel has no history right now), -1 if it exists with no TTL."""
    client = redis.Redis(connection_pool=_pool)
    return await client.ttl(_key(channel_id))


async def list_channel_ids() -> list[int]:
    """All channel IDs that currently have rolling history, via SCAN (safe for
    production Redis — doesn't block like KEYS would)."""
    client = redis.Redis(connection_pool=_pool)
    ids = []
    async for key in client.scan_iter(match="history:*"):
        try:
            ids.append(int(key.split(":", 1)[1]))
        except (IndexError, ValueError):
            continue
    return ids


def _guild_key(channel_id: int) -> str:
    return f"channel_guild:{channel_id}"


async def set_channel_guild(channel_id: int, guild_id: int) -> None:
    client = redis.Redis(connection_pool=_pool)
    await client.set(_guild_key(channel_id), str(guild_id), ex=config.HISTORY_TTL_SECONDS)


async def get_channel_guild(channel_id: int) -> int | None:
    client = redis.Redis(connection_pool=_pool)
    value = await client.get(_guild_key(channel_id))
    return int(value) if value is not None else None


def _summarized_key(channel_id: int) -> str:
    return f"summarized:{channel_id}"


async def mark_summarized(channel_id: int, ttl_seconds: int) -> None:
    client = redis.Redis(connection_pool=_pool)
    await client.set(_summarized_key(channel_id), "1", ex=max(ttl_seconds, 1))


async def is_summarized(channel_id: int) -> bool:
    client = redis.Redis(connection_pool=_pool)
    return bool(await client.exists(_summarized_key(channel_id)))
