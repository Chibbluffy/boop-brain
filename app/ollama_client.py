import ollama

from . import config

_client = ollama.AsyncClient(host=config.OLLAMA_BASE_URL)


async def chat(messages: list[dict], model: str = config.OLLAMA_MODEL) -> str:
    response = await _client.chat(model=model, messages=messages, options={"num_ctx": config.OLLAMA_NUM_CTX})
    return response["message"]["content"]


async def chat_raw(messages: list[dict], model: str, tools: list[dict] = None, num_ctx: int = None) -> dict:
    kwargs = {
        "model": model,
        "messages": messages,
        "options": {"num_ctx": num_ctx or config.OLLAMA_NUM_CTX},
    }
    if tools:
        kwargs["tools"] = tools
    return await _client.chat(**kwargs)


async def gate2_check(history: list[dict], candidate_content: str) -> bool:
    transcript = "\n".join(f"{turn['name']}: {turn['content']}" for turn in history[-8:])
    messages = [
        {
            "role": "system",
            "content": (
                "You are deciding whether an AI character should naturally jump into an "
                "ongoing conversation it was not addressed in. Answer with exactly one word: "
                "YES or NO."
            ),
        },
        {
            "role": "user",
            "content": f"Recent conversation:\n{transcript}\n\nNew message: {candidate_content}\n\n"
                       "Would it be natural for the character to jump in here?",
        },
    ]
    answer = await chat(messages, model=config.OLLAMA_RELEVANCE_MODEL)
    return answer.strip().upper().startswith("Y")
