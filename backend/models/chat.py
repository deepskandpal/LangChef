from sqlalchemy import Column, String, Text, Integer, ForeignKey, JSON, Boolean, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base, BaseModel
from uuid import uuid4

class Chat(Base, BaseModel):
    """Chat model for storing conversation history."""
    
    __tablename__ = "chats"
    
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=True)  # Auto-generated from first few characters of initial message
    system_prompt = Column(Text, nullable=True)
    model_id = Column(String, nullable=False)
    model_name = Column(String, nullable=True)
    model_provider = Column(String, nullable=True)
    configuration = Column(JSON, nullable=True)  # Store temperature, max_tokens, etc.
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", backref="chats")
    messages = relationship("ChatMessage", back_populates="chat", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Chat(id={self.id}, user_id='{self.user_id}', model='{self.model_id}')>"


class ChatMessage(Base, BaseModel):
    """Model for storing individual messages within a chat."""
    
    __tablename__ = "chat_messages"
    
    chat_id = Column(Integer, ForeignKey("chats.id"), nullable=False)
    role = Column(String, nullable=False)  # 'user', 'assistant', or 'system'
    content = Column(Text, nullable=False)
    order = Column(Integer, nullable=False)  # To maintain message order
    message_metadata = Column(JSON, nullable=True)  # For storing additional info like tokens, cost, etc.
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    chat = relationship("Chat", back_populates="messages")
    
    def __repr__(self):
        return f"<ChatMessage(id={self.id}, chat_id={self.chat_id}, role='{self.role}', order={self.order})>" 