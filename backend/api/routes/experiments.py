from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
import time
import json
from datetime import datetime
from ..schemas import (
    ExperimentCreate, ExperimentUpdate, ExperimentResponse,
    ExperimentResultCreate, ExperimentResultResponse,
    ExperimentMetricCreate, ExperimentMetricResponse,
    RunExperiment
)
from ...models import (
    Experiment, ExperimentResult, ExperimentMetric, 
    ExperimentStatus, Prompt, Dataset, DatasetItem
)
from ...services.llm_service import get_llm_service
from ...utils import get_db
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()

@router.post("/", response_model=ExperimentResponse, status_code=status.HTTP_201_CREATED)
def create_experiment(experiment: ExperimentCreate, db: Session = Depends(get_db)):
    """Create a new experiment."""
    # Check if prompt exists
    db_prompt = db.query(Prompt).filter(Prompt.id == experiment.prompt_id).first()
    if db_prompt is None:
        raise HTTPException(status_code=404, detail="Prompt not found")
    
    # Check if dataset exists
    db_dataset = db.query(Dataset).filter(Dataset.id == experiment.dataset_id).first()
    if db_dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    db_experiment = Experiment(
        name=experiment.name,
        description=experiment.description,
        prompt_id=experiment.prompt_id,
        dataset_id=experiment.dataset_id,
        model_provider=experiment.model_provider,
        model_name=experiment.model_name,
        model_config=experiment.model_config,
        metadata=experiment.metadata
    )
    db.add(db_experiment)
    db.commit()
    db.refresh(db_experiment)
    
    return db_experiment

@router.get("/", response_model=List[ExperimentResponse])
def get_experiments(
    skip: int = 0, 
    limit: int = 100, 
    name: Optional[str] = None,
    status: Optional[ExperimentStatus] = None,
    db: Session = Depends(get_db)
):
    """Get all experiments with optional filtering."""
    query = db.query(Experiment)
    
    if name:
        query = query.filter(Experiment.name.ilike(f"%{name}%"))
    
    if status:
        query = query.filter(Experiment.status == status)
    
    return query.offset(skip).limit(limit).all()

@router.get("/{experiment_id}", response_model=ExperimentResponse)
def get_experiment(experiment_id: int, db: Session = Depends(get_db)):
    """Get a specific experiment by ID."""
    db_experiment = db.query(Experiment).filter(Experiment.id == experiment_id).first()
    if db_experiment is None:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return db_experiment

@router.put("/{experiment_id}", response_model=ExperimentResponse)
def update_experiment(experiment_id: int, experiment: ExperimentUpdate, db: Session = Depends(get_db)):
    """Update an experiment."""
    db_experiment = db.query(Experiment).filter(Experiment.id == experiment_id).first()
    if db_experiment is None:
        raise HTTPException(status_code=404, detail="Experiment not found")
    
    # Update experiment fields if provided
    update_data = experiment.dict(exclude_unset=True)
    
    for key, value in update_data.items():
        setattr(db_experiment, key, value)
    
    db.commit()
    db.refresh(db_experiment)
    return db_experiment

@router.delete("/{experiment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_experiment(experiment_id: int, db: Session = Depends(get_db)):
    """Delete an experiment."""
    db_experiment = db.query(Experiment).filter(Experiment.id == experiment_id).first()
    if db_experiment is None:
        raise HTTPException(status_code=404, detail="Experiment not found")
    
    db.delete(db_experiment)
    db.commit()
    return None

@router.post("/{experiment_id}/results", response_model=ExperimentResultResponse)
def create_experiment_result(
    experiment_id: int, 
    result: ExperimentResultCreate, 
    db: Session = Depends(get_db)
):
    """Add a result to an experiment."""
    db_experiment = db.query(Experiment).filter(Experiment.id == experiment_id).first()
    if db_experiment is None:
        raise HTTPException(status_code=404, detail="Experiment not found")
    
    db_result = ExperimentResult(
        experiment_id=experiment_id,
        dataset_item_id=result.dataset_item_id,
        input=result.input,
        output=result.output,
        latency_ms=result.latency_ms,
        token_count_input=result.token_count_input,
        token_count_output=result.token_count_output,
        cost=result.cost,
        metadata=result.metadata
    )
    
    db.add(db_result)
    db.commit()
    db.refresh(db_result)
    
    return db_result

@router.get("/{experiment_id}/results", response_model=List[ExperimentResultResponse])
def get_experiment_results(
    experiment_id: int, 
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db)
):
    """Get all results for an experiment."""
    db_experiment = db.query(Experiment).filter(Experiment.id == experiment_id).first()
    if db_experiment is None:
        raise HTTPException(status_code=404, detail="Experiment not found")
    
    results = db.query(ExperimentResult).filter(
        ExperimentResult.experiment_id == experiment_id
    ).offset(skip).limit(limit).all()
    
    return results

@router.post("/{experiment_id}/metrics", response_model=ExperimentMetricResponse)
def create_experiment_metric(
    experiment_id: int, 
    metric: ExperimentMetricCreate, 
    db: Session = Depends(get_db)
):
    """Add a metric to an experiment."""
    db_experiment = db.query(Experiment).filter(Experiment.id == experiment_id).first()
    if db_experiment is None:
        raise HTTPException(status_code=404, detail="Experiment not found")
    
    db_metric = ExperimentMetric(
        experiment_id=experiment_id,
        name=metric.name,
        value=metric.value,
        metadata=metric.metadata
    )
    
    db.add(db_metric)
    db.commit()
    db.refresh(db_metric)
    
    return db_metric

@router.get("/{experiment_id}/metrics", response_model=List[ExperimentMetricResponse])
def get_experiment_metrics(
    experiment_id: int, 
    db: Session = Depends(get_db)
):
    """Get all metrics for an experiment."""
    db_experiment = db.query(Experiment).filter(Experiment.id == experiment_id).first()
    if db_experiment is None:
        raise HTTPException(status_code=404, detail="Experiment not found")
    
    metrics = db.query(ExperimentMetric).filter(
        ExperimentMetric.experiment_id == experiment_id
    ).all()
    
    return metrics

def run_experiment_task(experiment_id: int, db: Session):
    """Background task to run an experiment."""
    # Get experiment
    db_experiment = db.query(Experiment).filter(Experiment.id == experiment_id).first()
    if not db_experiment:
        return
    
    # Update status to running
    db_experiment.status = ExperimentStatus.RUNNING
    db.commit()
    
    try:
        # Get prompt
        db_prompt = db.query(Prompt).filter(Prompt.id == db_experiment.prompt_id).first()
        if not db_prompt:
            raise Exception("Prompt not found")
        
        # Get dataset items
        dataset_items = db.query(DatasetItem).filter(
            DatasetItem.dataset_id == db_experiment.dataset_id
        ).all()
        
        if not dataset_items:
            raise Exception("No dataset items found")
        
        # Get LLM service
        llm_service = get_llm_service(
            db_experiment.model_provider, 
            db_experiment.model_name,
            db_experiment.model_config
        )
        
        # Process each dataset item
        for item in dataset_items:
            # Prepare input
            input_data = {
                "prompt": db_prompt.content,
                "data": item.content
            }
            
            # Call LLM
            start_time = time.time()
            response = llm_service.generate(input_data)
            end_time = time.time()
            
            # Calculate metrics
            latency_ms = (end_time - start_time) * 1000
            token_count_input = llm_service.count_tokens(str(input_data))
            token_count_output = llm_service.count_tokens(str(response))
            cost = llm_service.calculate_cost(token_count_input, token_count_output)
            
            # Save result
            result = ExperimentResult(
                experiment_id=experiment_id,
                dataset_item_id=item.id,
                input=input_data,
                output=response,
                latency_ms=latency_ms,
                token_count_input=token_count_input,
                token_count_output=token_count_output,
                cost=cost,
                metadata={}
            )
            db.add(result)
        
        # Update experiment status
        db_experiment.status = ExperimentStatus.COMPLETED
        
    except Exception as e:
        # Update experiment status to failed
        db_experiment.status = ExperimentStatus.FAILED
        db_experiment.metadata = {
            **(db_experiment.metadata or {}),
            "error": str(e)
        }
    
    finally:
        db.commit()

@router.post("/{experiment_id}/run", response_model=ExperimentResponse)
def run_experiment(
    experiment_id: int, 
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Run an experiment."""
    db_experiment = db.query(Experiment).filter(Experiment.id == experiment_id).first()
    if db_experiment is None:
        raise HTTPException(status_code=404, detail="Experiment not found")
    
    if db_experiment.status == ExperimentStatus.RUNNING:
        raise HTTPException(status_code=400, detail="Experiment is already running")
    
    # Start the experiment in the background
    background_tasks.add_task(run_experiment_task, experiment_id, db)
    
    # Update status to running
    db_experiment.status = ExperimentStatus.RUNNING
    db.commit()
    db.refresh(db_experiment)
    
    return db_experiment

@router.get("/")
async def get_experiments(db: AsyncSession = Depends(get_db)):
    """Get all experiments."""
    return {"experiments": []}

@router.get("/{experiment_id}")
async def get_experiment(experiment_id: int, db: AsyncSession = Depends(get_db)):
    """Get an experiment by ID."""
    return {"experiment": {"id": experiment_id, "name": "Sample Experiment", "description": "This is a sample experiment."}} 