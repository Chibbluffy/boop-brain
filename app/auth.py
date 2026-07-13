from fastapi import Header, HTTPException

from . import config


async def require_secret(x_boopbot_secret: str = Header(default="")):
    if not config.BRAIN_SHARED_SECRET or x_boopbot_secret != config.BRAIN_SHARED_SECRET:
        raise HTTPException(status_code=401, detail="invalid or missing secret")
