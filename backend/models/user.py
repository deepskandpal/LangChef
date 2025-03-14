from sqlalchemy import Column, String, Boolean, DateTime, Text
from sqlalchemy.sql import func
from uuid import uuid4

from .base import Base


class User(Base):
    """User model for AWS SSO authentication."""
    
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=True)
    aws_identity_id = Column(String, unique=True, index=True, nullable=True)
    aws_access_key_id = Column(String, nullable=True)
    aws_secret_access_key = Column(String, nullable=True)
    aws_session_token = Column(Text, nullable=True)
    aws_token_expiry = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self):
        return f"<User {self.username}>" 