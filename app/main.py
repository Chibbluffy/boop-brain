from fastapi import Depends, FastAPI

from . import config, history, ollama_client
from .auth import require_secret
from .prompt import assemble_messages
from .schemas import (
    ClearHistoryRequest,
    ClearHistoryResponse,
    GenerateRequest,
    GenerateResponse,
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


@app.post("/generate", response_model=GenerateResponse, dependencies=[Depends(require_secret)])
async def generate(req: GenerateRequest):
    history_snapshot = await history.get_recent(req.channel_id)
    await history.append(req.channel_id, role="user", name=req.display_name, content=req.content)

    payload = {
        "user_id": req.user_id,
        "user_name": req.user_name,
        "display_name": req.display_name,
        "guild_id": req.guild_id,
        "channel_id": req.channel_id,
        "content": req.content,
    }
    messages = assemble_messages(_persona, history_snapshot, lore_lines=[], payload=payload)
    reply = await ollama_client.chat(messages)

    await history.append(req.channel_id, role="assistant", name="BoopBot", content=reply)
    return GenerateResponse(reply=reply)


@app.post("/history/clear", response_model=ClearHistoryResponse, dependencies=[Depends(require_secret)])
async def clear_history(req: ClearHistoryRequest):
    await history.clear(req.channel_id)
    return ClearHistoryResponse(cleared=True)
