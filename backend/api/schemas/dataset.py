from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List, Union
from datetime import datetime
from models.dataset import DatasetType

class DatasetBase(BaseModel):
    name: str
    description: Optional[str] = None
    type: DatasetType
    metadata: Optional[Dict[str, Any]] = None

class DatasetCreate(DatasetBase):
    pass

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
        orm_mode = True

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
        orm_mode = True

class DatasetResponse(DatasetBase):
    id: int
    version: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    items: Optional[List[DatasetItemResponse]] = None
    versions: Optional[List[DatasetVersionResponse]] = None

    class Config:
        orm_mode = True

class DatasetUpload(BaseModel):
    file_content: Union[str, Dict[str, Any], List[Dict[str, Any]]]
    file_type: DatasetType
    name: str
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None 