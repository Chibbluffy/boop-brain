import json


def assemble_messages(persona: str, history: list[dict], lore_lines: list[str], payload: dict) -> list[dict]:
    messages = [{"role": "system", "content": persona}]
    if lore_lines:
        messages.append({
            "role": "system",
            "content": "Known facts:\n" + "\n".join(f"- {line}" for line in lore_lines),
        })
    for turn in history:
        if turn["role"] == "assistant":
            messages.append({"role": "assistant", "content": turn["content"]})
        else:
            messages.append({"role": "user", "content": f"{turn['name']}: {turn['content']}"})
    messages.append({"role": "user", "content": json.dumps(payload)})
    return messages
