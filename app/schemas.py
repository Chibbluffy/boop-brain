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
    image_urls: list[str] = []


class GenerateResponse(BaseModel):
    reply: Optional[str] = None


class ClearHistoryRequest(BaseModel):
    channel_id: int


class ClearHistoryResponse(BaseModel):
    cleared: bool


class LoreAddRequest(BaseModel):
    guild_id: int
    text: str
    added_by_user_id: int
    added_by_name: str


class LoreAddMeRequest(BaseModel):
    user_id: int
    text: str


class LoreAddResponse(BaseModel):
    id: Optional[str] = None


class LoreEntry(BaseModel):
    id: str
    text: str


class LoreListRequest(BaseModel):
    guild_id: int
    user_id: int


class LoreListResponse(BaseModel):
    guild_lore: list[LoreEntry]
    user_lore: list[LoreEntry]


class LoreForgetRequest(BaseModel):
    guild_id: int
    user_id: int
    short_id: str
    is_admin: bool = False


class LoreForgetResponse(BaseModel):
    deleted: bool
    ambiguous: bool = False
    forbidden: bool = False
    text: Optional[str] = None
