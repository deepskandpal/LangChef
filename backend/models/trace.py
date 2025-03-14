from sqlalchemy import Column, String, Text, Integer, ForeignKey, JSON, Boolean, Float, Enum, DateTime
from sqlalchemy.orm import relationship
import enum
from .base import Base, BaseModel

class TraceStatus(enum.Enum):
    STARTED = "started"
    COMPLETED = "completed"
    FAILED = "failed"

class Trace(Base, BaseModel):
    __tablename__ = "traces"
    
    name = Column(String(255), nullable=False)
    status = Column(Enum(TraceStatus), default=TraceStatus.STARTED, nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=True)
    duration_ms = Column(Float, nullable=True)
    meta_data = Column(JSON, nullable=True)
    
    # Relationships
    spans = relationship("Span", back_populates="trace")
    
    def __repr__(self):
        return f"<Trace(id={self.id}, name='{self.name}', status={self.status})>"

class SpanType(enum.Enum):
    LLM = "llm"
    FUNCTION = "function"
    TOOL = "tool"
    CUSTOM = "custom"

class Span(Base, BaseModel):
    __tablename__ = "spans"
    
    trace_id = Column(Integer, ForeignKey("traces.id"), nullable=False)
    parent_span_id = Column(Integer, ForeignKey("spans.id"), nullable=True)
    name = Column(String(255), nullable=False)
    type = Column(Enum(SpanType), nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=True)
    duration_ms = Column(Float, nullable=True)
    input = Column(JSON, nullable=True)
    output = Column(JSON, nullable=True)
    meta_data = Column(JSON, nullable=True)
    
    # Relationships
    trace = relationship("Trace", back_populates="spans")
    
    def __repr__(self):
        return f"<Span(id={self.id}, trace_id={self.trace_id}, name='{self.name}', type={self.type})>"

# Define the parent relationship after the class is fully defined
Span.parent = relationship(
    "Span",
    backref="children",
    remote_side=[Span.id],
    foreign_keys=[Span.parent_span_id]
) 