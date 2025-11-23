from pydantic import BaseModel
from typing import Optional, Any

class WSMessage(BaseModel):
    type: str
    command: Optional[str] = None
    payload: Optional[dict[str, Any]] = None

class WSResponse(BaseModel):
    type: str
    data: Optional[dict[str, Any]] = None
    error: Optional[str] = None