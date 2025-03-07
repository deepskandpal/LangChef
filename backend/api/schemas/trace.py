from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from models.trace import TraceStatus, SpanType

class TraceBase(BaseModel):
    name: str
    metadata: Optional[Dict[str, Any]] = None

class TraceCreate(TraceBase):
    start_time: datetime

class TraceUpdate(BaseModel):
    status: Optional[TraceStatus] = None
    end_time: Optional[datetime] = None
    duration_ms: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None

class SpanBase(BaseModel):
    name: str
    type: SpanType
    start_time: datetime
    input: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None

class SpanCreate(SpanBase):
    trace_id: int
    parent_span_id: Optional[int] = None

class SpanUpdate(BaseModel):
    end_time: Optional[datetime] = None
    duration_ms: Optional[float] = None
    output: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None

class SpanResponse(SpanBase):
    id: int
    trace_id: int
    parent_span_id: Optional[int] = None
    end_time: Optional[datetime] = None
    duration_ms: Optional[float] = None
    output: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

class TraceResponse(TraceBase):
    id: int
    status: TraceStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_ms: Optional[float] = None
    created_at: datetime
    updated_at: datetime
    spans: Optional[List[SpanResponse]] = None

    class Config:
        orm_mode = True 