from sqlalchemy import Column, String, Text, Integer, ForeignKey, JSON, Boolean
from sqlalchemy.orm import relationship
from backend.models.base import Base, BaseModel

class Prompt(Base, BaseModel):
    __tablename__ = "prompts"
    
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    content = Column(Text, nullable=False)
    version = Column(Integer, default=1, nullable=False)
    is_active = Column(Boolean, default=True)
    meta_data = Column(JSON, nullable=True)
    
    # Relationships
    experiments = relationship("Experiment", back_populates="prompt")
    
    def __repr__(self):
        return f"<Prompt(id={self.id}, name='{self.name}', version={self.version})>"

class PromptVersion(Base, BaseModel):
    __tablename__ = "prompt_versions"
    
    prompt_id = Column(Integer, ForeignKey("prompts.id"), nullable=False)
    version = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    meta_data = Column(JSON, nullable=True)
    
    # Relationships
    prompt = relationship("Prompt")
    
    def __repr__(self):
        return f"<PromptVersion(id={self.id}, prompt_id={self.prompt_id}, version={self.version})>" 