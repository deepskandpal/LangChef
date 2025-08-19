from sqlalchemy import Column, String, Text, Integer, ForeignKey, JSON, Boolean, Enum
from sqlalchemy.orm import relationship
import enum
from backend.models.base import Base, BaseModel

class DatasetType(enum.Enum):
    TEXT = "text"
    JSON = "json"
    CSV = "csv"
    JSONL = "jsonl"
    CUSTOM = "custom"

class Dataset(Base, BaseModel):
    __tablename__ = "datasets"
    
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    dataset_type = Column(Enum(DatasetType), nullable=False, name="type")
    version = Column(Integer, default=1, nullable=False)
    is_active = Column(Boolean, default=True)
    meta_data = Column(JSON, nullable=True)
    
    # Relationships
    items = relationship("DatasetItem", back_populates="dataset")
    experiments = relationship("Experiment", back_populates="dataset")
    
    def __repr__(self):
        return f"<Dataset(id={self.id}, name='{self.name}', type={self.dataset_type}, version={self.version})>"

class DatasetItem(Base, BaseModel):
    __tablename__ = "dataset_items"
    
    dataset_id = Column(Integer, ForeignKey("datasets.id"), nullable=False)
    content = Column(JSON, nullable=False)
    meta_data = Column(JSON, nullable=True)
    
    # Relationships
    dataset = relationship("Dataset", back_populates="items")
    experiment_results = relationship("ExperimentResult", back_populates="dataset_item")
    
    def __repr__(self):
        return f"<DatasetItem(id={self.id}, dataset_id={self.dataset_id})>"

class DatasetVersion(Base, BaseModel):
    __tablename__ = "dataset_versions"
    
    dataset_id = Column(Integer, ForeignKey("datasets.id"), nullable=False)
    version = Column(Integer, nullable=False)
    meta_data = Column(JSON, nullable=True)
    
    # Relationships
    dataset = relationship("Dataset")
    
    def __repr__(self):
        return f"<DatasetVersion(id={self.id}, dataset_id={self.dataset_id}, version={self.version})>" 