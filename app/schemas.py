from typing import Optional

from pydantic import BaseModel


class GenerateRequest(BaseModel):
    guild_id: int
    channel_id: int
    user_id: int
    user_name: str
    display_name: str
    content: str
    is_mention: bool


class GenerateResponse(BaseModel):
    reply: Optional[str] = None
