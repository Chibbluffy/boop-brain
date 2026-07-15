import asyncio

from . import config, mem0_client, ollama_client
from .lore_ids import lore_text


async def _confirm_duplicate(text_a: str, text_b: str) -> bool:
    messages = [
        {
            "role": "system",
            "content": (
                "You are checking whether two stored facts are duplicates or near-duplicates "
                "of each other (the same information, worded differently, or one is a strict "
                "subset of the other). Answer with exactly one word: YES or NO."
            ),
        },
        {"role": "user", "content": f"Fact A: {text_a}\nFact B: {text_b}\n\nAre these duplicates?"},
    ]
    answer = await ollama_client.chat(messages, model=config.OLLAMA_SMART_MODEL)
    return answer.strip().upper().startswith("Y")


async def find_duplicate_pairs(guild_id: int) -> list[dict]:
    scope = mem0_client.guild_scope(guild_id)
    entries = await mem0_client.get_all(agent_id=scope)
    if len(entries) < 2:
        return []

    by_id = {e["id"]: lore_text(e) for e in entries}

    # For each entry, find its nearest neighbors (itself included) via semantic search.
    candidate_lists = await asyncio.gather(*[
        mem0_client.search(text, agent_id=scope, limit=3) for text in by_id.values()
    ])

    seen_pairs = set()
    candidate_pairs = []
    for entry_id, hits in zip(by_id.keys(), candidate_lists):
        for hit in hits:
            other_id = hit["id"]
            if other_id == entry_id or other_id not in by_id:
                continue
            pair_key = tuple(sorted((entry_id, other_id)))
            if pair_key in seen_pairs:
                continue
            seen_pairs.add(pair_key)
            candidate_pairs.append(pair_key)

    if not candidate_pairs:
        return []

    confirmations = await asyncio.gather(*[
        _confirm_duplicate(by_id[a], by_id[b]) for a, b in candidate_pairs
    ])

    return [
        {"a": {"id": a, "text": by_id[a]}, "b": {"id": b, "text": by_id[b]}}
        for (a, b), is_dup in zip(candidate_pairs, confirmations) if is_dup
    ]
