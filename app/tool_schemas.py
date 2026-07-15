TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": (
                "Search the live web for current information, news, facts, prices, or "
                "anything that might not be in your training data. Use this when the user "
                "asks something time-sensitive or you're not confident in your own knowledge."
            ),
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string", "description": "The search query."}},
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_url",
            "description": (
                "Fetch and read the text content of a specific webpage URL, e.g. when a user "
                "shares a link and asks about it."
            ),
            "parameters": {
                "type": "object",
                "properties": {"url": {"type": "string", "description": "The full URL to fetch."}},
                "required": ["url"],
            },
        },
    },
]
