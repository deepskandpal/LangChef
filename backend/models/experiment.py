from sqlalchemy import Column, String, Text, Integer, ForeignKey, JSON, Boolean, Float, Enum
from sqlalchemy.orm import relationship
import enum
from .base import Base, BaseModel

class ModelProvider(enum.Enum):
    OPENAI = "openai"
    AWS_BEDROCK = "aws_bedrock"
    ANTHROPIC = "anthropic"
    HUGGINGFACE = "huggingface"
    CUSTOM = "custom"

class ExperimentStatus(enum.Enum):
    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class Experiment(Base, BaseModel):
    __tablename__ = "experiments"
    
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    prompt_id = Column(Integer, ForeignKey("prompts.id"), nullable=False)
    dataset_id = Column(Integer, ForeignKey("datasets.id"), nullable=False)
    model_provider = Column(Enum(ModelProvider), nullable=False)
    model_name = Column(String(255), nullable=False)
    model_config = Column(JSON, nullable=True)
    status = Column(Enum(ExperimentStatus), default=ExperimentStatus.CREATED, nullable=False)
    metadata = Column(JSON, nullable=True)
    
    # Relationships
    prompt = relationship("Prompt", back_populates="experiments")
    dataset = relationship("Dataset", back_populates="experiments")
    results = relationship("ExperimentResult", back_populates="experiment")
    metrics = relationship("ExperimentMetric", back_populates="experiment")
    
    def __repr__(self):
        return f"<Experiment(id={self.id}, name='{self.name}', status={self.status})>"

class ExperimentResult(Base, BaseModel):
    __tablename__ = "experiment_results"
    
    experiment_id = Column(Integer, ForeignKey("experiments.id"), nullable=False)
    dataset_item_id = Column(Integer, ForeignKey("dataset_items.id"), nullable=False)
    input = Column(JSON, nullable=False)
    output = Column(JSON, nullable=False)
    latency_ms = Column(Float, nullable=True)
    token_count_input = Column(Integer, nullable=True)
    token_count_output = Column(Integer, nullable=True)
    cost = Column(Float, nullable=True)
    metadata = Column(JSON, nullable=True)
    
    # Relationships
    experiment = relationship("Experiment", back_populates="results")
    dataset_item = relationship("DatasetItem", back_populates="experiment_results")
    
    def __repr__(self):
        return f"<ExperimentResult(id={self.id}, experiment_id={self.experiment_id}, dataset_item_id={self.dataset_item_id})>"

class ExperimentMetric(Base, BaseModel):
    __tablename__ = "experiment_metrics"
    
    experiment_id = Column(Integer, ForeignKey("experiments.id"), nullable=False)
    name = Column(String(255), nullable=False)
    value = Column(Float, nullable=False)
    metadata = Column(JSON, nullable=True)
    
    # Relationships
    experiment = relationship("Experiment", back_populates="metrics")
    
    def __repr__(self):
        return f"<ExperimentMetric(id={self.id}, experiment_id={self.experiment_id}, name='{self.name}', value={self.value})>" 