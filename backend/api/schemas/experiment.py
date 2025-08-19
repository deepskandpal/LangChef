from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from backend.models.experiment import ModelProvider, ExperimentStatus

class ExperimentBase(BaseModel):
    name: str
    description: Optional[str] = None
    prompt_id: int
    dataset_id: int
    model_provider: ModelProvider
    model_name: str
    llm_config: Optional[Dict[str, Any]] = Field(None, alias="model_config")
    metadata: Optional[Dict[str, Any]] = None

class ExperimentCreate(ExperimentBase):
    pass

class ExperimentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    llm_config: Optional[Dict[str, Any]] = Field(None, alias="model_config")
    status: Optional[ExperimentStatus] = None
    metadata: Optional[Dict[str, Any]] = None

class ExperimentResultBase(BaseModel):
    input: Dict[str, Any]
    output: Dict[str, Any]
    latency_ms: Optional[float] = None
    token_count_input: Optional[int] = None
    token_count_output: Optional[int] = None
    cost: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None

class ExperimentResultCreate(ExperimentResultBase):
    experiment_id: int
    dataset_item_id: int

class ExperimentResultResponse(ExperimentResultBase):
    id: int
    experiment_id: int
    dataset_item_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ExperimentMetricBase(BaseModel):
    name: str
    value: float
    metadata: Optional[Dict[str, Any]] = None

class ExperimentMetricCreate(ExperimentMetricBase):
    experiment_id: int

class ExperimentMetricResponse(ExperimentMetricBase):
    id: int
    experiment_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ExperimentResponse(ExperimentBase):
    id: int
    status: ExperimentStatus
    created_at: datetime
    updated_at: datetime
    results: Optional[List[ExperimentResultResponse]] = None
    metrics: Optional[List[ExperimentMetricResponse]] = None

    class Config:
        from_attributes = True

class RunExperiment(BaseModel):
    experiment_id: int 