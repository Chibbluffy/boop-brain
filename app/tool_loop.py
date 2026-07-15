import asyncio

from . import config, ollama_client, tools as tool_exec
from .tool_schemas import TOOLS


async def run_smart_chat(messages: list[dict]) -> str:
    for round_num in range(config.TOOL_MAX_ROUNDS):
        response = await ollama_client.chat_raw(
            messages, model=config.OLLAMA_SMART_MODEL, tools=TOOLS,
            num_ctx=config.OLLAMA_SMART_NUM_CTX,
        )
        message = response["message"]
        tool_calls = message.get("tool_calls") or []
        if not tool_calls:
            print(f"[tool_loop] round {round_num}: no tool_calls, returning direct answer")
            return message.get("content", "")

        print(f"[tool_loop] round {round_num}: {len(tool_calls)} tool_call(s) requested: "
              f"{[c['function']['name'] for c in tool_calls]}")

        messages.append({"role": "assistant", "content": message.get("content", ""), "tool_calls": tool_calls})
        results = await asyncio.gather(*[
            tool_exec.execute_tool_call(call["function"]["name"], call["function"].get("arguments", {}))
            for call in tool_calls
        ])
        for call, result in zip(tool_calls, results):
            name = call["function"]["name"]
            args = call["function"].get("arguments", {})
            preview = result[:200] + ("..." if len(result) > 200 else "")
            print(f"[tool_loop] {name}({args}) -> {preview}")
            messages.append({"role": "tool", "content": result, "name": name})

    print(f"[tool_loop] hit TOOL_MAX_ROUNDS={config.TOOL_MAX_ROUNDS}, forcing final answer with no tools")
    # Iteration cap hit — force a final plain-text answer with no tools available.
    response = await ollama_client.chat_raw(
        messages, model=config.OLLAMA_SMART_MODEL, tools=None, num_ctx=config.OLLAMA_SMART_NUM_CTX
    )
    return response["message"].get("content", "")
