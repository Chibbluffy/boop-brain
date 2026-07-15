import asyncio

from . import config, ollama_client, tools as tool_exec
from .tool_schemas import TOOLS


async def run_smart_chat(messages: list[dict]) -> str:
    for _ in range(config.TOOL_MAX_ROUNDS):
        response = await ollama_client.chat_raw(
            messages, model=config.OLLAMA_SMART_MODEL, tools=TOOLS,
            num_ctx=config.OLLAMA_SMART_NUM_CTX,
        )
        message = response["message"]
        tool_calls = message.get("tool_calls") or []
        if not tool_calls:
            return message.get("content", "")

        messages.append({"role": "assistant", "content": message.get("content", ""), "tool_calls": tool_calls})
        results = await asyncio.gather(*[
            tool_exec.execute_tool_call(call["function"]["name"], call["function"].get("arguments", {}))
            for call in tool_calls
        ])
        for call, result in zip(tool_calls, results):
            messages.append({"role": "tool", "content": result, "name": call["function"]["name"]})

    # Iteration cap hit — force a final plain-text answer with no tools available.
    response = await ollama_client.chat_raw(
        messages, model=config.OLLAMA_SMART_MODEL, tools=None, num_ctx=config.OLLAMA_SMART_NUM_CTX
    )
    return response["message"].get("content", "")
