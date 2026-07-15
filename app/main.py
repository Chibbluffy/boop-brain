import asyncio

from fastapi import Depends, FastAPI

from . import config, dedup, heuristics, history, images, mem0_client, ollama_client, tool_loop
from .auth import require_secret
from .lore_ids import lore_text, resolve_short_id
from .prompt import assemble_messages
from .schemas import (
    ClearHistoryRequest,
    ClearHistoryResponse,
    GenerateRequest,
    GenerateResponse,
    LoreAddMeRequest,
    LoreAddRequest,
    LoreAddResponse,
    LoreDeleteRequest,
    LoreDeleteResponse,
    LoreEntry,
    LoreForgetRequest,
    LoreForgetResponse,
    LoreGuildListRequest,
    LoreListRequest,
    LoreListResponse,
    LoreScanDuplicatesRequest,
    LoreScanDuplicatesResponse,
    LoreUpdateRequest,
    LoreUpdateResponse,
    LoreUserListRequest,
)

app = FastAPI()

_persona: str = ""


@app.on_event("startup")
async def load_persona():
    global _persona
    with open(config.CHATBOT_CONTEXT_FILE, "r") as f:
        _persona = f.read()


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


async def _extract_and_store(guild_scope: str, user_content: str, reply: str) -> None:
    try:
        result = await mem0_client.add(
            [{"role": "user", "content": user_content}, {"role": "assistant", "content": reply}],
            agent_id=guild_scope,
        )
        added = result.get("results", []) if isinstance(result, dict) else (result or [])
        if added:
            print(f"[lore auto-extract] {guild_scope}: {len(added)} memor{'y' if len(added) == 1 else 'ies'} "
                  f"{[a.get('event', '?') for a in added]}: {[a.get('memory', '') for a in added]}")
        else:
            print(f"[lore auto-extract] {guild_scope}: nothing extracted from this exchange")
    except Exception as e:
        print(f"[lore extraction failed] {e}")


@app.post("/generate", response_model=GenerateResponse, dependencies=[Depends(require_secret)])
async def generate(req: GenerateRequest):
    history_snapshot = await history.get_recent(req.channel_id)
    await history.append(req.channel_id, role="user", name=req.display_name, content=req.content)

    if not req.is_mention:
        should_reply = await ollama_client.gate2_check(history_snapshot, req.content)
        if not should_reply:
            return GenerateResponse(reply=None)

    reason = heuristics.detect_escalation(req.content, req.image_urls)
    print(f"[route] channel={req.channel_id} escalate={reason}")

    guild_scope = mem0_client.guild_scope(req.guild_id)
    user_scope = mem0_client.user_scope(req.user_id)
    guild_hits, user_hits = await asyncio.gather(
        mem0_client.search(req.content, agent_id=guild_scope, limit=config.LORE_TOP_K),
        mem0_client.search(req.content, user_id=user_scope, limit=config.LORE_TOP_K),
    )
    lore_lines = [lore_text(hit) for hit in guild_hits + user_hits]

    payload = {
        "user_id": req.user_id,
        "user_name": req.user_name,
        "display_name": req.display_name,
        "guild_id": req.guild_id,
        "channel_id": req.channel_id,
        "content": req.content,
    }
    messages = assemble_messages(_persona, history_snapshot, lore_lines=lore_lines, payload=payload)
    if reason:
        image_b64_list = await images.fetch_images_b64(req.image_urls)
        if image_b64_list:
            messages[-1]["images"] = image_b64_list
        reply = await tool_loop.run_smart_chat(messages)
    else:
        reply = await ollama_client.chat(messages)

    await history.append(req.channel_id, role="assistant", name="BoopBot", content=reply)
    asyncio.create_task(_extract_and_store(guild_scope, req.content, reply))
    return GenerateResponse(reply=reply)


@app.post("/history/clear", response_model=ClearHistoryResponse, dependencies=[Depends(require_secret)])
async def clear_history(req: ClearHistoryRequest):
    await history.clear(req.channel_id)
    return ClearHistoryResponse(cleared=True)


@app.post("/lore/add", response_model=LoreAddResponse, dependencies=[Depends(require_secret)])
async def lore_add(req: LoreAddRequest):
    result = await mem0_client.add(
        [{"role": "user", "content": req.text}],
        agent_id=mem0_client.guild_scope(req.guild_id),
    )
    return LoreAddResponse(id=mem0_client.first_id(result))


@app.post("/lore/addme", response_model=LoreAddResponse, dependencies=[Depends(require_secret)])
async def lore_addme(req: LoreAddMeRequest):
    result = await mem0_client.add(
        [{"role": "user", "content": req.text}],
        user_id=mem0_client.user_scope(req.user_id),
    )
    return LoreAddResponse(id=mem0_client.first_id(result))


@app.post("/lore/list", response_model=LoreListResponse, dependencies=[Depends(require_secret)])
async def lore_list(req: LoreListRequest):
    guild_hits, user_hits = await asyncio.gather(
        mem0_client.get_all(agent_id=mem0_client.guild_scope(req.guild_id)),
        mem0_client.get_all(user_id=mem0_client.user_scope(req.user_id)),
    )
    return LoreListResponse(
        guild_lore=[LoreEntry(id=hit["id"], text=lore_text(hit)) for hit in guild_hits],
        user_lore=[LoreEntry(id=hit["id"], text=lore_text(hit)) for hit in user_hits],
    )


@app.post("/lore/forget", response_model=LoreForgetResponse, dependencies=[Depends(require_secret)])
async def lore_forget(req: LoreForgetRequest):
    guild_hits, user_hits = await asyncio.gather(
        mem0_client.get_all(agent_id=mem0_client.guild_scope(req.guild_id)),
        mem0_client.get_all(user_id=mem0_client.user_scope(req.user_id)),
    )
    match = resolve_short_id(req.short_id, guild_hits + user_hits)
    if match == "ambiguous":
        return LoreForgetResponse(deleted=False, ambiguous=True)
    if match is None:
        return LoreForgetResponse(deleted=False)
    is_guild_entry = any(match["id"] == hit["id"] for hit in guild_hits)
    if is_guild_entry and not req.is_admin:
        return LoreForgetResponse(deleted=False, forbidden=True)
    await mem0_client.delete(match["id"])
    return LoreForgetResponse(deleted=True, text=lore_text(match))


@app.post("/lore/guild/list", response_model=list[LoreEntry], dependencies=[Depends(require_secret)])
async def lore_guild_list(req: LoreGuildListRequest):
    hits = await mem0_client.get_all(agent_id=mem0_client.guild_scope(req.guild_id))
    return [LoreEntry(id=hit["id"], text=lore_text(hit)) for hit in hits]


@app.post("/lore/user/list", response_model=list[LoreEntry], dependencies=[Depends(require_secret)])
async def lore_user_list(req: LoreUserListRequest):
    hits = await mem0_client.get_all(user_id=mem0_client.user_scope(req.user_id))
    return [LoreEntry(id=hit["id"], text=lore_text(hit)) for hit in hits]


@app.post("/lore/update", response_model=LoreUpdateResponse, dependencies=[Depends(require_secret)])
async def lore_update(req: LoreUpdateRequest):
    await mem0_client.update(req.memory_id, req.text)
    return LoreUpdateResponse(updated=True)


@app.post("/lore/delete", response_model=LoreDeleteResponse, dependencies=[Depends(require_secret)])
async def lore_delete(req: LoreDeleteRequest):
    await mem0_client.delete(req.memory_id)
    return LoreDeleteResponse(deleted=True)


@app.post("/lore/guild/scan_duplicates", response_model=LoreScanDuplicatesResponse, dependencies=[Depends(require_secret)])
async def lore_scan_duplicates(req: LoreScanDuplicatesRequest):
    pairs = await dedup.find_duplicate_pairs(req.guild_id)
    return LoreScanDuplicatesResponse(pairs=pairs)
