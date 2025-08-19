from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from sqlalchemy import func
from backend.models import Experiment, ExperimentResult, ExperimentMetric
from backend.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()

@router.get("/experiments/{experiment_id}/summary")
def get_experiment_metrics_summary(experiment_id: int, db: Session = Depends(get_db)):
    """Get a summary of metrics for an experiment."""
    # Check if experiment exists
    db_experiment = db.query(Experiment).filter(Experiment.id == experiment_id).first()
    if db_experiment is None:
        raise HTTPException(status_code=404, detail="Experiment not found")
    
    # Get results
    results = db.query(ExperimentResult).filter(
        ExperimentResult.experiment_id == experiment_id
    ).all()
    
    if not results:
        return {
            "experiment_id": experiment_id,
            "total_items": 0,
            "metrics": {}
        }
    
    # Calculate metrics
    total_items = len(results)
    total_latency = sum(r.latency_ms for r in results if r.latency_ms is not None)
    avg_latency = total_latency / total_items if total_items > 0 else 0
    
    total_tokens_input = sum(r.token_count_input for r in results if r.token_count_input is not None)
    total_tokens_output = sum(r.token_count_output for r in results if r.token_count_output is not None)
    total_tokens = total_tokens_input + total_tokens_output
    
    total_cost = sum(r.cost for r in results if r.cost is not None)
    
    # Get custom metrics
    custom_metrics = db.query(ExperimentMetric).filter(
        ExperimentMetric.experiment_id == experiment_id
    ).all()
    
    custom_metrics_dict = {m.name: m.value for m in custom_metrics}
    
    return {
        "experiment_id": experiment_id,
        "total_items": total_items,
        "metrics": {
            "latency": {
                "total_ms": total_latency,
                "avg_ms": avg_latency
            },
            "tokens": {
                "input": total_tokens_input,
                "output": total_tokens_output,
                "total": total_tokens
            },
            "cost": {
                "total": total_cost
            },
            "custom": custom_metrics_dict
        }
    }

@router.get("/experiments/compare")
def compare_experiments(experiment_ids: List[int], db: Session = Depends(get_db)):
    """Compare metrics across multiple experiments."""
    if not experiment_ids:
        raise HTTPException(status_code=400, detail="No experiment IDs provided")
    
    results = {}
    
    for exp_id in experiment_ids:
        # Check if experiment exists
        db_experiment = db.query(Experiment).filter(Experiment.id == exp_id).first()
        if db_experiment is None:
            results[exp_id] = {"error": "Experiment not found"}
            continue
        
        # Get summary metrics
        summary = get_experiment_metrics_summary(exp_id, db)
        results[exp_id] = summary
    
    return results

@router.get("/dashboard")
async def get_dashboard_metrics(db: AsyncSession = Depends(get_db)):
    """Get metrics for the dashboard."""
    return {
        "total_prompts": 10,
        "total_datasets": 5,
        "total_experiments": 15,
        "recent_experiments": []
    }

@router.get("/experiments/{experiment_id}")
async def get_experiment_metrics(experiment_id: int, db: AsyncSession = Depends(get_db)):
    """Get metrics for a specific experiment."""
    return {
        "experiment_id": experiment_id,
        "metrics": {
            "accuracy": 0.85,
            "latency": 250,
            "tokens_used": 1500
        }
    } 