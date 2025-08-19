from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from backend.api.schemas import (
    TraceCreate, TraceUpdate, TraceResponse,
    SpanCreate, SpanUpdate, SpanResponse
)
from backend.models import Trace, Span, TraceStatus, SpanType
from backend.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()

@router.post("/", response_model=TraceResponse, status_code=status.HTTP_201_CREATED)
def create_trace(trace: TraceCreate, db: Session = Depends(get_db)):
    """Create a new trace."""
    db_trace = Trace(
        name=trace.name,
        status=TraceStatus.STARTED,
        start_time=trace.start_time,
        metadata=trace.metadata
    )
    db.add(db_trace)
    db.commit()
    db.refresh(db_trace)
    
    return db_trace

@router.get("/")
async def get_traces(db: AsyncSession = Depends(get_db)):
    """Get all traces."""
    return {"traces": []}

@router.get("/{trace_id}")
async def get_trace(trace_id: int, db: AsyncSession = Depends(get_db)):
    """Get a trace by ID."""
    return {"trace": {"id": trace_id, "name": "Sample Trace", "status": "completed"}}

@router.put("/{trace_id}", response_model=TraceResponse)
def update_trace(trace_id: int, trace: TraceUpdate, db: Session = Depends(get_db)):
    """Update a trace."""
    db_trace = db.query(Trace).filter(Trace.id == trace_id).first()
    if db_trace is None:
        raise HTTPException(status_code=404, detail="Trace not found")
    
    # Update trace fields if provided
    update_data = trace.dict(exclude_unset=True)
    
    for key, value in update_data.items():
        setattr(db_trace, key, value)
    
    db.commit()
    db.refresh(db_trace)
    return db_trace

@router.delete("/{trace_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_trace(trace_id: int, db: Session = Depends(get_db)):
    """Delete a trace."""
    db_trace = db.query(Trace).filter(Trace.id == trace_id).first()
    if db_trace is None:
        raise HTTPException(status_code=404, detail="Trace not found")
    
    db.delete(db_trace)
    db.commit()
    return None

@router.post("/{trace_id}/spans", response_model=SpanResponse)
def create_span(
    trace_id: int, 
    span: SpanCreate, 
    db: Session = Depends(get_db)
):
    """Add a span to a trace."""
    db_trace = db.query(Trace).filter(Trace.id == trace_id).first()
    if db_trace is None:
        raise HTTPException(status_code=404, detail="Trace not found")
    
    # If parent span is provided, check if it exists
    if span.parent_span_id:
        parent_span = db.query(Span).filter(Span.id == span.parent_span_id).first()
        if parent_span is None:
            raise HTTPException(status_code=404, detail="Parent span not found")
    
    db_span = Span(
        trace_id=trace_id,
        parent_span_id=span.parent_span_id,
        name=span.name,
        type=span.type,
        start_time=span.start_time,
        input=span.input,
        metadata=span.metadata
    )
    
    db.add(db_span)
    db.commit()
    db.refresh(db_span)
    
    return db_span

@router.get("/{trace_id}/spans", response_model=List[SpanResponse])
def get_spans(
    trace_id: int, 
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db)
):
    """Get all spans for a trace."""
    db_trace = db.query(Trace).filter(Trace.id == trace_id).first()
    if db_trace is None:
        raise HTTPException(status_code=404, detail="Trace not found")
    
    spans = db.query(Span).filter(
        Span.trace_id == trace_id
    ).offset(skip).limit(limit).all()
    
    return spans

@router.put("/{trace_id}/spans/{span_id}", response_model=SpanResponse)
def update_span(
    trace_id: int, 
    span_id: int, 
    span: SpanUpdate, 
    db: Session = Depends(get_db)
):
    """Update a span."""
    db_span = db.query(Span).filter(
        Span.id == span_id,
        Span.trace_id == trace_id
    ).first()
    
    if db_span is None:
        raise HTTPException(status_code=404, detail="Span not found")
    
    # Update span fields if provided
    update_data = span.dict(exclude_unset=True)
    
    for key, value in update_data.items():
        setattr(db_span, key, value)
    
    db.commit()
    db.refresh(db_span)
    return db_span

@router.post("/{trace_id}/complete", response_model=TraceResponse)
def complete_trace(trace_id: int, db: Session = Depends(get_db)):
    """Complete a trace."""
    db_trace = db.query(Trace).filter(Trace.id == trace_id).first()
    if db_trace is None:
        raise HTTPException(status_code=404, detail="Trace not found")
    
    # Set end time and calculate duration
    end_time = datetime.now()
    db_trace.end_time = end_time
    db_trace.status = TraceStatus.COMPLETED
    
    # Calculate duration in milliseconds
    if db_trace.start_time:
        duration_ms = (end_time - db_trace.start_time).total_seconds() * 1000
        db_trace.duration_ms = duration_ms
    
    db.commit()
    db.refresh(db_trace)
    return db_trace 