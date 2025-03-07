from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from api.schemas import (
    PromptCreate, PromptUpdate, PromptResponse,
    PromptVersionCreate, PromptVersionResponse
)
from models import Prompt, PromptVersion
from ...utils import get_db
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()

@router.post("/", response_model=PromptResponse, status_code=status.HTTP_201_CREATED)
def create_prompt(prompt: PromptCreate, db: Session = Depends(get_db)):
    """Create a new prompt."""
    db_prompt = Prompt(
        name=prompt.name,
        description=prompt.description,
        content=prompt.content,
        metadata=prompt.metadata
    )
    db.add(db_prompt)
    db.commit()
    db.refresh(db_prompt)
    
    # Create initial version
    db_version = PromptVersion(
        prompt_id=db_prompt.id,
        version=1,
        content=prompt.content,
        metadata=prompt.metadata
    )
    db.add(db_version)
    db.commit()
    db.refresh(db_version)
    
    return db_prompt

@router.get("/")
async def get_prompts(db: AsyncSession = Depends(get_db)):
    """Get all prompts."""
    return {"prompts": []}

@router.get("/{prompt_id}")
async def get_prompt(prompt_id: int, db: AsyncSession = Depends(get_db)):
    """Get a prompt by ID."""
    return {"prompt": {"id": prompt_id, "name": "Sample Prompt", "content": "This is a sample prompt."}}

@router.put("/{prompt_id}", response_model=PromptResponse)
def update_prompt(prompt_id: int, prompt: PromptUpdate, db: Session = Depends(get_db)):
    """Update a prompt."""
    db_prompt = db.query(Prompt).filter(Prompt.id == prompt_id).first()
    if db_prompt is None:
        raise HTTPException(status_code=404, detail="Prompt not found")
    
    # Update prompt fields if provided
    update_data = prompt.dict(exclude_unset=True)
    
    # If content is updated, create a new version
    if "content" in update_data:
        # Increment version
        db_prompt.version += 1
        
        # Create new version
        db_version = PromptVersion(
            prompt_id=db_prompt.id,
            version=db_prompt.version,
            content=update_data["content"],
            metadata=db_prompt.metadata if "metadata" not in update_data else update_data["metadata"]
        )
        db.add(db_version)
    
    # Update prompt
    for key, value in update_data.items():
        setattr(db_prompt, key, value)
    
    db.commit()
    db.refresh(db_prompt)
    return db_prompt

@router.delete("/{prompt_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_prompt(prompt_id: int, db: Session = Depends(get_db)):
    """Delete a prompt."""
    db_prompt = db.query(Prompt).filter(Prompt.id == prompt_id).first()
    if db_prompt is None:
        raise HTTPException(status_code=404, detail="Prompt not found")
    
    db.delete(db_prompt)
    db.commit()
    return None

@router.post("/{prompt_id}/versions", response_model=PromptVersionResponse)
def create_prompt_version(
    prompt_id: int, 
    version: PromptVersionCreate, 
    db: Session = Depends(get_db)
):
    """Create a new version of a prompt."""
    db_prompt = db.query(Prompt).filter(Prompt.id == prompt_id).first()
    if db_prompt is None:
        raise HTTPException(status_code=404, detail="Prompt not found")
    
    # Increment version
    db_prompt.version += 1
    db_prompt.content = version.content
    
    if version.metadata:
        db_prompt.metadata = version.metadata
    
    # Create new version
    db_version = PromptVersion(
        prompt_id=db_prompt.id,
        version=db_prompt.version,
        content=version.content,
        metadata=version.metadata
    )
    
    db.add(db_version)
    db.commit()
    db.refresh(db_version)
    
    return db_version

@router.get("/{prompt_id}/versions", response_model=List[PromptVersionResponse])
def get_prompt_versions(prompt_id: int, db: Session = Depends(get_db)):
    """Get all versions of a prompt."""
    db_prompt = db.query(Prompt).filter(Prompt.id == prompt_id).first()
    if db_prompt is None:
        raise HTTPException(status_code=404, detail="Prompt not found")
    
    versions = db.query(PromptVersion).filter(PromptVersion.prompt_id == prompt_id).all()
    return versions

@router.get("/{prompt_id}/versions/{version}", response_model=PromptVersionResponse)
def get_prompt_version(prompt_id: int, version: int, db: Session = Depends(get_db)):
    """Get a specific version of a prompt."""
    db_version = db.query(PromptVersion).filter(
        PromptVersion.prompt_id == prompt_id,
        PromptVersion.version == version
    ).first()
    
    if db_version is None:
        raise HTTPException(status_code=404, detail="Prompt version not found")
    
    return db_version 