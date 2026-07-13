import json

from fastapi import Depends, FastAPI

from . import config, ollama_client
from .auth import require_secret
from .schemas import GenerateRequest, GenerateResponse

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
    payload = json.dumps({
        "user_id": req.user_id,
        "user_name": req.user_name,
        "display_name": req.display_name,
        "guild_id": req.guild_id,
        "channel_id": req.channel_id,
        "content": req.content,
    })
    messages = [
        {"role": "system", "content": _persona},
        {"role": "user", "content": payload},
    ]
    reply = await ollama_client.chat(messages)
    return GenerateResponse(reply=reply)


@app.post("/history/clear", dependencies=[Depends(require_secret)])
async def clear_history(req: dict):
    # Phase 2 will back this with real Redis-stored history; nothing persists yet.
    return {"cleared": True}
