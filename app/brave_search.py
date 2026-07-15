import aiohttp

from . import config

BRAVE_ENDPOINT = "https://api.search.brave.com/res/v1/web/search"


async def search_web(query: str, count: int = 5) -> str:
    headers = {"Accept": "application/json", "X-Subscription-Token": config.BRAVE_API_KEY}
    params = {"q": query, "count": count}
    async with aiohttp.ClientSession() as session:
        async with session.get(
            BRAVE_ENDPOINT, headers=headers, params=params,
            timeout=aiohttp.ClientTimeout(total=10),
        ) as resp:
            resp.raise_for_status()
            data = await resp.json()

    results = data.get("web", {}).get("results", [])[:count]
    if not results:
        return "No results found."
    return "\n".join(
        f"- {r.get('title', '')}\n  {r.get('url', '')}\n  {r.get('description', '')}"
        for r in results
    )
