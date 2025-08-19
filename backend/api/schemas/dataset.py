from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List, Union
from datetime import datetime
from backend.models.dataset import DatasetType
from pydantic import validator

class DatasetBase(BaseModel):
    name: str
    description: Optional[str] = None
    dataset_type: DatasetType = Field(alias="type")
    metadata: Optional[Dict[str, Any]] = None
    examples: Optional[List[Dict[str, Any]]] = Field(default_factory=list)

    class Config:
        populate_by_name = True

    def __init__(self, **data):
        # Convert dataset_type to lowercase if it's a string
        if "dataset_type" in data and isinstance(data["dataset_type"], str):
            data["dataset_type"] = data["dataset_type"].lower()
        elif "type" in data and isinstance(data["type"], str):
            data["type"] = data["type"].lower()
        super().__init__(**data)

class DatasetCreate(DatasetBase):
    items: Optional[List[Dict[str, Any]]] = None
    
    @validator('items')
    def validate_items(cls, v):
        if v is None:
            return v
        
        valid_items = []
        for i, item in enumerate(v):
            # Ensure each item is a dictionary
            if not isinstance(item, dict):
                print(f"Warning: Skipping non-dictionary item at index {i}")
                continue
                
            # Filter out any None values or empty strings as keys
            cleaned_item = {}
            for key, value in item.items():
                if key is None or key.strip() == '':
                    continue
                    
                # Use the cleaned key
                cleaned_key = key.strip()
                cleaned_item[cleaned_key] = value
                
            # Only add if there's at least one valid key-value pair
            if cleaned_item:
                valid_items.append(cleaned_item)
                
        return valid_items

class DatasetUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    metadata: Optional[Dict[str, Any]] = None

class DatasetItemBase(BaseModel):
    content: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None

class DatasetItemCreate(DatasetItemBase):
    pass

class DatasetItemUpdate(BaseModel):
    content: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None

class DatasetItemResponse(DatasetItemBase):
    id: int
    dataset_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class DatasetVersionCreate(BaseModel):
    metadata: Optional[Dict[str, Any]] = None

class DatasetVersionResponse(BaseModel):
    id: int
    dataset_id: int
    version: int
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class DatasetResponse(DatasetBase):
    id: int
    version: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    items: Optional[List[DatasetItemResponse]] = None
    versions: Optional[List[DatasetVersionResponse]] = None

    class Config:
        from_attributes = True

class DatasetUpload(BaseModel):
    file_content: Union[str, Dict[str, Any], List[Dict[str, Any]]]
    file_type: DatasetType
    name: str
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None 