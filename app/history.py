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
