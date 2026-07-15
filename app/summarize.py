from typing import Optional

from . import config, mem0_client, ollama_client

_SUMMARY_SYSTEM_PROMPT = (
    "You are summarizing a Discord conversation so it can be recalled later as "
    "long-term memory. Write a concise summary (3-6 sentences) of what actually "
    "happened: notable topics discussed, decisions made, facts revealed about "
    "people, and any events or plans mentioned. Skip small talk and filler. "
    "Write it as plain factual narration, not as a chat log."
)


async def summarize_conversation(history: list[dict]) -> Optional[str]:
    if not history:
        return None
    transcript = "\n".join(f"{turn['name']}: {turn['content']}" for turn in history)
    messages = [
        {"role": "system", "content": _SUMMARY_SYSTEM_PROMPT},
        {"role": "user", "content": f"Conversation:\n{transcript}"},
    ]
    # chat_raw (not chat()) — a real summary needs more room than the fast-path's
    # num_predict cap allows, and a bigger context window for long histories.
    response = await ollama_client.chat_raw(
        messages, model=config.OLLAMA_SMART_MODEL, num_ctx=config.OLLAMA_SMART_NUM_CTX
    )
    return response["message"]["content"].strip()


async def store_summary(guild_id: int, summary: str) -> None:
    await mem0_client.add(
        [{"role": "assistant", "content": summary}],
        agent_id=mem0_client.guild_scope(guild_id),
        infer=False,
        metadata={"type": "summary"},
    )
