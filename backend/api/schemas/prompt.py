from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime

class PromptBase(BaseModel):
    name: str
    description: Optional[str] = None
    content: str
    metadata: Optional[Dict[str, Any]] = None

class PromptCreate(PromptBase):
    pass

class PromptUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    content: Optional[str] = None
    is_active: Optional[bool] = None
    metadata: Optional[Dict[str, Any]] = None

class PromptVersionCreate(BaseModel):
    content: str
    metadata: Optional[Dict[str, Any]] = None

class PromptVersionResponse(BaseModel):
    id: int
    prompt_id: int
    version: int
    content: str
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class PromptResponse(PromptBase):
    id: int
    version: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    versions: Optional[List[PromptVersionResponse]] = None

    class Config:
        from_attributes = True 