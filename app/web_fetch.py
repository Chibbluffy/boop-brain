import aiohttp
from bs4 import BeautifulSoup

from . import config


async def fetch_url(url: str) -> str:
    async with aiohttp.ClientSession() as session:
        async with session.get(
            url, timeout=aiohttp.ClientTimeout(total=10),
            headers={"User-Agent": "Mozilla/5.0 (compatible; BoopBot/1.0)"},
        ) as resp:
            resp.raise_for_status()
            content_type = resp.headers.get("Content-Type", "")
            if "html" not in content_type and "text" not in content_type:
                return f"Cannot read content of type {content_type or 'unknown'} at {url}"
            html = await resp.text(errors="ignore")

    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "header", "footer", "noscript"]):
        tag.decompose()
    text = " ".join(soup.get_text(separator=" ").split())
    if len(text) > config.FETCH_URL_MAX_CHARS:
        text = text[: config.FETCH_URL_MAX_CHARS] + "... [truncated]"
    return text or f"No readable text found at {url}"
