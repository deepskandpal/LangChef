from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from typing import List, Optional, Dict, Any
import time
import json
from datetime import datetime

from backend.api.schemas import (
    ExperimentCreate, ExperimentUpdate, ExperimentResponse,
    ExperimentResultCreate, ExperimentResultResponse,
    ExperimentMetricCreate, ExperimentMetricResponse,
    RunExperiment
)
from backend.models import (
    Experiment, ExperimentResult, ExperimentMetric, 
    ExperimentStatus, Prompt, Dataset, DatasetItem
)
from backend.services.llm_service import get_llm_service
from backend.database import get_db
from backend.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()

@router.post("/", response_model=ExperimentResponse, status_code=status.HTTP_201_CREATED)
async def create_experiment(experiment: ExperimentCreate, db: AsyncSession = Depends(get_db)):
    """Create a new experiment."""
    logger.info(f"Creating experiment: {experiment.name}")
    
    try:
        # Check if prompt exists
        prompt_result = await db.execute(select(Prompt).where(Prompt.id == experiment.prompt_id))
        db_prompt = prompt_result.scalar_one_or_none()
        if db_prompt is None:
            logger.warning(f"Prompt not found: {experiment.prompt_id}")
            raise HTTPException(status_code=404, detail="Prompt not found")
        
        # Check if dataset exists
        dataset_result = await db.execute(select(Dataset).where(Dataset.id == experiment.dataset_id))
        db_dataset = dataset_result.scalar_one_or_none()
        if db_dataset is None:
            logger.warning(f"Dataset not found: {experiment.dataset_id}")
            raise HTTPException(status_code=404, detail="Dataset not found")
        
        db_experiment = Experiment(
            name=experiment.name,
            description=experiment.description,
            prompt_id=experiment.prompt_id,
            dataset_id=experiment.dataset_id,
            model_provider=experiment.model_provider,
            model_name=experiment.model_name,
            model_config=experiment.llm_config,
            metadata=experiment.metadata
        )
        db.add(db_experiment)
        await db.flush()
        
        logger.info(f"Created experiment with ID: {db_experiment.id}")
        return db_experiment
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating experiment: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create experiment"
        )

@router.get("/", response_model=List[ExperimentResponse])
async def get_experiments(
    skip: int = 0, 
    limit: int = 100, 
    name: Optional[str] = None,
    status: Optional[ExperimentStatus] = None,
    dataset_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get all experiments with optional filtering."""
    try:
        # Build the SQL query
        query = "SELECT * FROM experiments WHERE 1=1"
        params = {}
        
        if name:
            query += " AND name ILIKE :name"
            params["name"] = f"%{name}%"
        
        if status:
            query += " AND status = :status"
            params["status"] = status.value
            
        if dataset_id:
            query += " AND dataset_id = :dataset_id"
            params["dataset_id"] = dataset_id
        
        # Add pagination
        query += " OFFSET :skip LIMIT :limit"
        params["skip"] = skip
        params["limit"] = limit
        
        # Execute the query
        result = await db.execute(text(query), params)
        experiments = result.fetchall()
        
        # Convert to response model
        return [
            {
                "id": exp.id,
                "name": exp.name,
                "description": exp.description,
                "dataset_id": exp.dataset_id,
                "prompt_template_id": exp.prompt_template_id,
                "status": exp.status,
                "config": exp.config,
                "metadata": exp.metadata,
                "created_at": exp.created_at,
                "updated_at": exp.updated_at
            }
            for exp in experiments
        ]
    except Exception as e:
        print(f"Error in get_experiments: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve experiments: {str(e)}"
        )

@router.get("/{experiment_id}", response_model=ExperimentResponse)
async def get_experiment(experiment_id: int, db: AsyncSession = Depends(get_db)):
    """Get a specific experiment by ID."""
    try:
        # Execute raw SQL query to get the experiment
        query = "SELECT * FROM experiments WHERE id = :experiment_id"
        result = await db.execute(text(query), {"experiment_id": experiment_id})
        db_experiment = result.fetchone()
        
        if db_experiment is None:
            raise HTTPException(status_code=404, detail="Experiment not found")
        
        # Convert to response model
        return {
            "id": db_experiment.id,
            "name": db_experiment.name,
            "description": db_experiment.description,
            "dataset_id": db_experiment.dataset_id,
            "prompt_template_id": db_experiment.prompt_template_id,
            "status": db_experiment.status,
            "config": db_experiment.config,
            "metadata": db_experiment.metadata,
            "created_at": db_experiment.created_at,
            "updated_at": db_experiment.updated_at
        }
    except Exception as e:
        print(f"Error in get_experiment: {e}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve experiment: {str(e)}"
        )

@router.put("/{experiment_id}", response_model=ExperimentResponse)
async def update_experiment(experiment_id: int, experiment: ExperimentUpdate, db: AsyncSession = Depends(get_db)):
    """Update an experiment."""
    try:
        # First check if the experiment exists
        query = "SELECT * FROM experiments WHERE id = :experiment_id"
        result = await db.execute(text(query), {"experiment_id": experiment_id})
        db_experiment = result.fetchone()
        
        if db_experiment is None:
            raise HTTPException(status_code=404, detail="Experiment not found")
        
        # Update experiment fields if provided
        update_data = experiment.dict(exclude_unset=True)
        if not update_data:
            # If no fields to update, return the current experiment
            return {
                "id": db_experiment.id,
                "name": db_experiment.name,
                "description": db_experiment.description,
                "dataset_id": db_experiment.dataset_id,
                "prompt_template_id": db_experiment.prompt_template_id,
                "status": db_experiment.status,
                "config": db_experiment.config,
                "metadata": db_experiment.metadata,
                "created_at": db_experiment.created_at,
                "updated_at": db_experiment.updated_at
            }
        
        # Build UPDATE query
        update_query = "UPDATE experiments SET "
        update_params = {"experiment_id": experiment_id}
        
        update_parts = []
        for key, value in update_data.items():
            update_parts.append(f"{key} = :{key}")
            update_params[key] = value
        
        update_query += ", ".join(update_parts)
        update_query += ", updated_at = now() WHERE id = :experiment_id RETURNING *"
        
        # Execute the update
        result = await db.execute(text(update_query), update_params)
        updated_experiment = result.fetchone()
        await db.commit()
        
        # Return the updated experiment
        return {
            "id": updated_experiment.id,
            "name": updated_experiment.name,
            "description": updated_experiment.description,
            "dataset_id": updated_experiment.dataset_id,
            "prompt_template_id": updated_experiment.prompt_template_id,
            "status": updated_experiment.status,
            "config": updated_experiment.config,
            "metadata": updated_experiment.metadata,
            "created_at": updated_experiment.created_at,
            "updated_at": updated_experiment.updated_at
        }
    except Exception as e:
        await db.rollback()
        print(f"Error in update_experiment: {e}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update experiment: {str(e)}"
        )

@router.delete("/{experiment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_experiment(experiment_id: int, db: AsyncSession = Depends(get_db)):
    """Delete an experiment."""
    try:
        # First check if the experiment exists
        query = "SELECT id FROM experiments WHERE id = :experiment_id"
        result = await db.execute(text(query), {"experiment_id": experiment_id})
        db_experiment = result.fetchone()
        
        if db_experiment is None:
            raise HTTPException(status_code=404, detail="Experiment not found")
        
        # Delete the experiment
        delete_query = "DELETE FROM experiments WHERE id = :experiment_id"
        await db.execute(text(delete_query), {"experiment_id": experiment_id})
        await db.commit()
        
        return None
    except Exception as e:
        await db.rollback()
        print(f"Error in delete_experiment: {e}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete experiment: {str(e)}"
        )

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