def assemble_messages(persona: str, history: list[dict], lore_lines: list[str], display_name: str, content: str) -> list[dict]:
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
    # Same "Name: text" shape as history — a format switch right at the most recent,
    # most-attended-to position in the prompt was confusing the small model (it would
    # comment on "the JSON formatting" instead of just responding to the message).
    messages.append({"role": "user", "content": f"{display_name}: {content}"})
    return messages
