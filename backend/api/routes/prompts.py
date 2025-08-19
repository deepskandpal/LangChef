from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional

from backend.api.schemas import (
    PromptCreate, PromptUpdate, PromptResponse,
    PromptVersionCreate, PromptVersionResponse
)
from backend.models import Prompt, PromptVersion, User
from backend.database import get_db
from backend.services.auth_service import get_current_user
from backend.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()

@router.post("/", response_model=PromptResponse, status_code=status.HTTP_201_CREATED)
async def create_prompt(
    prompt: PromptCreate, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new prompt."""
    logger.info(f"Creating new prompt: {prompt.name}")
    
    try:
        db_prompt = Prompt(
            name=prompt.name,
            description=prompt.description,
            content=prompt.content,
            metadata=prompt.metadata
        )
        db.add(db_prompt)
        await db.flush()  # Flush to get the ID
        
        # Create initial version
        db_version = PromptVersion(
            prompt_id=db_prompt.id,
            version=1,
            content=prompt.content,
            metadata=prompt.metadata
        )
        db.add(db_version)
        await db.flush()
        
        logger.info(f"Created prompt with ID: {db_prompt.id}")
        return db_prompt
        
    except Exception as e:
        logger.error(f"Error creating prompt: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create prompt"
        )

@router.get("/")
async def get_prompts(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all prompts."""
    logger.info("Fetching all prompts")
    
    try:
        result = await db.execute(select(Prompt))
        prompts = result.scalars().all()
        logger.info(f"Found {len(prompts)} prompts")
        return {"prompts": prompts}
    except Exception as e:
        logger.error(f"Error fetching prompts: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch prompts"
        )

@router.get("/{prompt_id}")
async def get_prompt(
    prompt_id: int, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a prompt by ID."""
    logger.info(f"Fetching prompt with ID: {prompt_id}")
    
    try:
        result = await db.execute(select(Prompt).where(Prompt.id == prompt_id))
        prompt = result.scalar_one_or_none()
        
        if not prompt:
            logger.warning(f"Prompt not found: {prompt_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Prompt not found"
            )
        
        logger.info(f"Found prompt: {prompt.name}")
        return {"prompt": prompt}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching prompt {prompt_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch prompt"
        )

@router.put("/{prompt_id}", response_model=PromptResponse)
async def update_prompt(
    prompt_id: int, 
    prompt: PromptUpdate, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a prompt."""
    logger.info(f"Updating prompt with ID: {prompt_id}")
    
    try:
        result = await db.execute(select(Prompt).where(Prompt.id == prompt_id))
        db_prompt = result.scalar_one_or_none()
        
        if db_prompt is None:
            logger.warning(f"Prompt not found for update: {prompt_id}")
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
        
        await db.flush()
        logger.info(f"Updated prompt: {db_prompt.name}")
        return db_prompt
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating prompt {prompt_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update prompt"
        )

@router.delete("/{prompt_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_prompt(
    prompt_id: int, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a prompt."""
    logger.info(f"Deleting prompt with ID: {prompt_id}")
    
    try:
        result = await db.execute(select(Prompt).where(Prompt.id == prompt_id))
        db_prompt = result.scalar_one_or_none()
        
        if db_prompt is None:
            logger.warning(f"Prompt not found for deletion: {prompt_id}")
            raise HTTPException(status_code=404, detail="Prompt not found")
        
        await db.delete(db_prompt)
        logger.info(f"Deleted prompt: {db_prompt.name}")
        return None
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting prompt {prompt_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete prompt"
        )

@router.post("/{prompt_id}/versions", response_model=PromptVersionResponse)
async def create_prompt_version(
    prompt_id: int, 
    version: PromptVersionCreate, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new version of a prompt."""
    logger.info(f"Creating new version for prompt ID: {prompt_id}")
    
    try:
        result = await db.execute(select(Prompt).where(Prompt.id == prompt_id))
        db_prompt = result.scalar_one_or_none()
        
        if db_prompt is None:
            logger.warning(f"Prompt not found for version creation: {prompt_id}")
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
        await db.flush()
        
        logger.info(f"Created version {db_version.version} for prompt {prompt_id}")
        return db_version
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating version for prompt {prompt_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create prompt version"
        )

@router.get("/{prompt_id}/versions", response_model=List[PromptVersionResponse])
async def get_prompt_versions(
    prompt_id: int, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all versions of a prompt."""
    logger.info(f"Fetching versions for prompt ID: {prompt_id}")
    
    try:
        result = await db.execute(select(Prompt).where(Prompt.id == prompt_id))
        db_prompt = result.scalar_one_or_none()
        
        if db_prompt is None:
            logger.warning(f"Prompt not found for versions: {prompt_id}")
            raise HTTPException(status_code=404, detail="Prompt not found")
        
        versions_result = await db.execute(
            select(PromptVersion).where(PromptVersion.prompt_id == prompt_id)
        )
        versions = versions_result.scalars().all()
        
        logger.info(f"Found {len(versions)} versions for prompt {prompt_id}")
        return versions
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching versions for prompt {prompt_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch prompt versions"
        )

@router.get("/{prompt_id}/versions/{version}", response_model=PromptVersionResponse)
async def get_prompt_version(
    prompt_id: int, 
    version: int, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific version of a prompt."""
    logger.info(f"Fetching version {version} for prompt ID: {prompt_id}")
    
    try:
        result = await db.execute(
            select(PromptVersion).where(
                PromptVersion.prompt_id == prompt_id,
                PromptVersion.version == version
            )
        )
        db_version = result.scalar_one_or_none()
        
        if db_version is None:
            logger.warning(f"Prompt version not found: {prompt_id}/v{version}")
            raise HTTPException(status_code=404, detail="Prompt version not found")
        
        logger.info(f"Found version {version} for prompt {prompt_id}")
        return db_version
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching version {version} for prompt {prompt_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch prompt version"
        ) 