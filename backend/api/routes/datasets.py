from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional
import json
import csv
import io
from api.schemas import (
    DatasetCreate, DatasetUpdate, DatasetResponse,
    DatasetItemCreate, DatasetItemResponse,
    DatasetVersionCreate, DatasetVersionResponse,
    DatasetUpload
)
from models import Dataset, DatasetItem, DatasetVersion, DatasetType
from ...utils import get_db
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()

@router.post("/", response_model=DatasetResponse, status_code=status.HTTP_201_CREATED)
def create_dataset(dataset: DatasetCreate, db: Session = Depends(get_db)):
    """Create a new dataset."""
    db_dataset = Dataset(
        name=dataset.name,
        description=dataset.description,
        type=dataset.type,
        metadata=dataset.metadata
    )
    db.add(db_dataset)
    db.commit()
    db.refresh(db_dataset)
    
    # Create initial version
    db_version = DatasetVersion(
        dataset_id=db_dataset.id,
        version=1,
        metadata=dataset.metadata
    )
    db.add(db_version)
    db.commit()
    
    return db_dataset

@router.get("/", response_model=List[DatasetResponse])
def get_datasets(
    skip: int = 0, 
    limit: int = 100, 
    name: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get all datasets with optional filtering."""
    query = db.query(Dataset)
    
    if name:
        query = query.filter(Dataset.name.ilike(f"%{name}%"))
    
    return query.offset(skip).limit(limit).all()

@router.get("/{dataset_id}", response_model=DatasetResponse)
def get_dataset(dataset_id: int, db: Session = Depends(get_db)):
    """Get a specific dataset by ID."""
    db_dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if db_dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return db_dataset

@router.put("/{dataset_id}", response_model=DatasetResponse)
def update_dataset(dataset_id: int, dataset: DatasetUpdate, db: Session = Depends(get_db)):
    """Update a dataset."""
    db_dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if db_dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    # Update dataset fields if provided
    update_data = dataset.dict(exclude_unset=True)
    
    # If metadata is updated, create a new version
    if "metadata" in update_data:
        # Increment version
        db_dataset.version += 1
        
        # Create new version
        db_version = DatasetVersion(
            dataset_id=db_dataset.id,
            version=db_dataset.version,
            metadata=update_data["metadata"]
        )
        db.add(db_version)
    
    # Update dataset
    for key, value in update_data.items():
        setattr(db_dataset, key, value)
    
    db.commit()
    db.refresh(db_dataset)
    return db_dataset

@router.delete("/{dataset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dataset(dataset_id: int, db: Session = Depends(get_db)):
    """Delete a dataset."""
    db_dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if db_dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    db.delete(db_dataset)
    db.commit()
    return None

@router.post("/{dataset_id}/items", response_model=DatasetItemResponse)
def create_dataset_item(
    dataset_id: int, 
    item: DatasetItemCreate, 
    db: Session = Depends(get_db)
):
    """Add an item to a dataset."""
    db_dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if db_dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    db_item = DatasetItem(
        dataset_id=dataset_id,
        content=item.content,
        metadata=item.metadata
    )
    
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    
    return db_item

@router.get("/{dataset_id}/items", response_model=List[DatasetItemResponse])
def get_dataset_items(
    dataset_id: int, 
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db)
):
    """Get all items in a dataset."""
    db_dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if db_dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    items = db.query(DatasetItem).filter(
        DatasetItem.dataset_id == dataset_id
    ).offset(skip).limit(limit).all()
    
    return items

@router.post("/{dataset_id}/versions", response_model=DatasetVersionResponse)
def create_dataset_version(
    dataset_id: int, 
    version: DatasetVersionCreate, 
    db: Session = Depends(get_db)
):
    """Create a new version of a dataset."""
    db_dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if db_dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    # Increment version
    db_dataset.version += 1
    
    if version.metadata:
        db_dataset.metadata = version.metadata
    
    # Create new version
    db_version = DatasetVersion(
        dataset_id=db_dataset.id,
        version=db_dataset.version,
        metadata=version.metadata
    )
    
    db.add(db_version)
    db.commit()
    db.refresh(db_version)
    
    return db_version

@router.get("/{dataset_id}/versions", response_model=List[DatasetVersionResponse])
def get_dataset_versions(dataset_id: int, db: Session = Depends(get_db)):
    """Get all versions of a dataset."""
    db_dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if db_dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    versions = db.query(DatasetVersion).filter(
        DatasetVersion.dataset_id == dataset_id
    ).all()
    
    return versions

@router.post("/upload", response_model=DatasetResponse)
def upload_dataset(
    dataset_upload: DatasetUpload,
    db: Session = Depends(get_db)
):
    """Upload a dataset from file content."""
    # Create the dataset
    db_dataset = Dataset(
        name=dataset_upload.name,
        description=dataset_upload.description,
        type=dataset_upload.file_type,
        metadata=dataset_upload.metadata
    )
    db.add(db_dataset)
    db.commit()
    db.refresh(db_dataset)
    
    # Create initial version
    db_version = DatasetVersion(
        dataset_id=db_dataset.id,
        version=1,
        metadata=dataset_upload.metadata
    )
    db.add(db_version)
    db.commit()
    
    # Process the file content based on type
    items = []
    
    if dataset_upload.file_type == DatasetType.JSON:
        if isinstance(dataset_upload.file_content, dict):
            items = [dataset_upload.file_content]
        elif isinstance(dataset_upload.file_content, list):
            items = dataset_upload.file_content
        else:
            try:
                content = json.loads(dataset_upload.file_content)
                if isinstance(content, dict):
                    items = [content]
                elif isinstance(content, list):
                    items = content
            except:
                raise HTTPException(
                    status_code=400, 
                    detail="Invalid JSON content"
                )
    
    elif dataset_upload.file_type == DatasetType.JSONL:
        if isinstance(dataset_upload.file_content, str):
            try:
                for line in dataset_upload.file_content.splitlines():
                    if line.strip():
                        items.append(json.loads(line))
            except:
                raise HTTPException(
                    status_code=400, 
                    detail="Invalid JSONL content"
                )
    
    elif dataset_upload.file_type == DatasetType.CSV:
        if isinstance(dataset_upload.file_content, str):
            try:
                csv_file = io.StringIO(dataset_upload.file_content)
                reader = csv.DictReader(csv_file)
                for row in reader:
                    items.append(dict(row))
            except:
                raise HTTPException(
                    status_code=400, 
                    detail="Invalid CSV content"
                )
    
    elif dataset_upload.file_type == DatasetType.TEXT:
        if isinstance(dataset_upload.file_content, str):
            lines = dataset_upload.file_content.splitlines()
            for line in lines:
                if line.strip():
                    items.append({"text": line})
    
    # Add items to the dataset
    for item_content in items:
        db_item = DatasetItem(
            dataset_id=db_dataset.id,
            content=item_content,
            metadata={}
        )
        db.add(db_item)
    
    db.commit()
    db.refresh(db_dataset)
    
    return db_dataset

@router.get("/")
async def get_datasets(db: AsyncSession = Depends(get_db)):
    """Get all datasets."""
    return {"datasets": []}

@router.get("/{dataset_id}")
async def get_dataset(dataset_id: int, db: AsyncSession = Depends(get_db)):
    """Get a dataset by ID."""
    return {"dataset": {"id": dataset_id, "name": "Sample Dataset", "description": "This is a sample dataset."}} 