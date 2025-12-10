from pydantic import BaseModel
from typing import Dict, Any

class ToolCall(BaseModel):
    action: str
    params: Dict[str, Any]