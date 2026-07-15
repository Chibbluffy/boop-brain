import asyncio
import base64
from typing import Optional

import aiohttp


async def _fetch_one(session: aiohttp.ClientSession, url: str) -> Optional[str]:
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            resp.raise_for_status()
            data = await resp.read()
            return base64.b64encode(data).decode("ascii")
    except Exception as e:
        print(f"[image fetch failed] {url}: {e}")
        return None


async def fetch_images_b64(urls: list[str]) -> list[str]:
    if not urls:
        return []
    async with aiohttp.ClientSession() as session:
        results = await asyncio.gather(*[_fetch_one(session, u) for u in urls])
    return [r for r in results if r is not None]
