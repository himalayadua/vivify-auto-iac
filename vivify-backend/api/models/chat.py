"""
Pydantic models for Chat API
"""

from pydantic import BaseModel
from typing import List, Optional, Dict, Any


class ChatMessage(BaseModel):
    """Chat message model"""
    message: str
    session_id: str
    history: Optional[List[Dict[str, Any]]] = []


class ChatResponse(BaseModel):
    """Chat response model"""
    type: str
    content: Optional[str] = None
    thought: Optional[str] = None
    toolName: Optional[str] = None
    toolInput: Optional[str] = None
    toolOutput: Optional[str] = None
    text: Optional[str] = None
    message: Optional[str] = None
