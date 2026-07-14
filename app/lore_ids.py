def resolve_short_id(short_id: str, candidates: list[dict]):
    matches = [c for c in candidates if c["id"].startswith(short_id)]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        return "ambiguous"
    return None


def lore_text(entry: dict) -> str:
    return entry.get("memory", entry.get("text", ""))
