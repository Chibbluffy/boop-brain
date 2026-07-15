from . import brave_search, web_fetch

_DISPATCH = {
    "search_web": lambda args: brave_search.search_web(args.get("query", "")),
    "fetch_url": lambda args: web_fetch.fetch_url(args.get("url", "")),
}


async def execute_tool_call(name: str, arguments: dict) -> str:
    fn = _DISPATCH.get(name)
    if fn is None:
        return f"Unknown tool: {name}"
    try:
        return await fn(arguments)
    except Exception as e:
        return f"Tool '{name}' failed: {type(e).__name__}: {e}"
