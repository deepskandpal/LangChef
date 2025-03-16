from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional
import json
import csv
import io
from ..schemas import (
    DatasetCreate, DatasetUpdate, DatasetResponse,
    DatasetItemCreate, DatasetItemResponse,
    DatasetVersionCreate, DatasetVersionResponse,
    DatasetUpload
)
from ...models import Dataset, DatasetItem, DatasetVersion, DatasetType
from ...utils import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from fastapi import Form

router = APIRouter()

@router.post("/", response_model=DatasetResponse, status_code=status.HTTP_201_CREATED)
async def create_dataset(dataset: DatasetCreate, db: AsyncSession = Depends(get_db)):
    """Create a new dataset."""
    try:
        # Convert dataset_type to lowercase string to avoid enum issues
        dataset_type = dataset.dataset_type
        if isinstance(dataset_type, str):
            dataset_type = dataset_type.lower()
        else:
            # Convert enum to string
            dataset_type = dataset_type.value
        
        # Create the dataset using the ORM
        db_dataset = Dataset(
            name=dataset.name,
            description=dataset.description,
            dataset_type=dataset_type,  # Changed from type to dataset_type
            version=1,
            is_active=True,
            meta_data=dataset.metadata or {},
            examples=dataset.examples or []
        )
        db.add(db_dataset)
        
        try:
            await db.commit()
            await db.refresh(db_dataset)
        except Exception as db_error:
            await db.rollback()
            raise HTTPException(
                status_code=500,
                detail=f"Error creating dataset: {str(db_error)}"
            )
        
        # Create initial version
        db_version = DatasetVersion(
            dataset_id=db_dataset.id,
            version=1,
            meta_data=dataset.metadata or {}
        )
        db.add(db_version)
        
        try:
            await db.commit()
        except Exception as version_error:
            # Try to clean up if version creation fails
            await db.delete(db_dataset)
            await db.commit()
            raise HTTPException(
                status_code=500,
                detail=f"Error creating dataset version: {str(version_error)}"
            )
        
        # Add items if provided
        if dataset.items:
            try:
                # Process in batches for better performance
                batch_size = 100
                items_added = 0
                
                for i in range(0, len(dataset.items), batch_size):
                    batch = dataset.items[i:i + batch_size]
                    for item_content in batch:
                        # Validate item content is a dictionary
                        if not isinstance(item_content, dict):
                            print(f"Skipping invalid item: {item_content}")
                            continue
                        
                        db_item = DatasetItem(
                            dataset_id=db_dataset.id,
                            content=item_content,
                            metadata={}
                        )
                        db.add(db_item)
                        items_added += 1
                    
                    await db.commit()
                
                # If no valid items were added, log a warning
                if items_added == 0 and dataset.items:
                    print(f"Warning: No valid items were added to dataset {db_dataset.id} from {len(dataset.items)} provided items")
            
            except Exception as item_error:
                # If adding items fails, log the error but don't delete the dataset
                print(f"Error adding items to dataset {db_dataset.id}: {str(item_error)}")
                await db.rollback()
                # Continue to return the dataset even if adding items failed
        
        return db_dataset
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Log the error
        print(f"Unexpected error creating dataset: {str(e)}")
        # Re-raise as HTTP exception
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while creating the dataset"
        )

@router.get("/", response_model=None)
async def get_datasets_sync(
    skip: int = 0, 
    limit: int = 100, 
    name: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get all datasets with optional filtering."""
    try:
        # Use raw SQL to bypass SQLAlchemy's enum conversion issues
        sql_query = """
        SELECT id, name, description, type, version, is_active, meta_data, examples, created_at, updated_at 
        FROM datasets
        """
        
        # Add WHERE clause if name filter is provided
        params = {}
        if name:
            sql_query += " WHERE name ILIKE :name"
            params["name"] = f"%{name}%"
        
        # Add ORDER BY, OFFSET and LIMIT
        sql_query += " ORDER BY id DESC OFFSET :skip LIMIT :limit"
        params["skip"] = skip
        params["limit"] = limit
        
        # Execute query
        result = await db.execute(text(sql_query), params)
        rows = result.fetchall()
        
        # Convert rows to dictionaries
        datasets = []
        for row in rows:
            datasets.append({
                "id": row[0],
                "name": row[1],
                "description": row[2],
                "type": row[3],  # Keep type as string
                "version": row[4],
                "is_active": row[5],
                "metadata": row[6],
                "examples": row[7],
                "created_at": row[8],
                "updated_at": row[9]
            })
        
        return datasets
    except Exception as e:
        print(f"Error retrieving datasets: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving datasets: {str(e)}"
        )

@router.get("/{dataset_id}", response_model=None)
async def get_dataset_sync(dataset_id: int, db: AsyncSession = Depends(get_db)):
    """Get a specific dataset by ID."""
    try:
        # Use raw SQL to bypass SQLAlchemy's enum conversion issues
        sql_query = """
        SELECT id, name, description, type, version, is_active, meta_data, examples, created_at, updated_at 
        FROM datasets
        WHERE id = :dataset_id
        """
        
        # Execute query
        result = await db.execute(text(sql_query), {"dataset_id": dataset_id})
        row = result.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="Dataset not found")
        
        # Convert row to dictionary
        dataset = {
            "id": row[0],
            "name": row[1],
            "description": row[2],
            "type": row[3],  # Keep type as string
            "version": row[4],
            "is_active": row[5],
            "metadata": row[6],
            "examples": row[7],
            "created_at": row[8],
            "updated_at": row[9]
        }
        
        # Get dataset items count
        items_count_query = """
        SELECT COUNT(*) FROM dataset_items WHERE dataset_id = :dataset_id
        """
        items_count_result = await db.execute(text(items_count_query), {"dataset_id": dataset_id})
        items_count = items_count_result.scalar_one() or 0
        
        dataset["items_count"] = items_count
        
        return dataset
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error retrieving dataset: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving dataset: {str(e)}"
        )

@router.put("/{dataset_id}", response_model=None)
async def update_dataset(dataset_id: int, dataset: DatasetUpdate, db: AsyncSession = Depends(get_db)):
    """Update a dataset."""
    try:
        # First check if the dataset exists using raw SQL
        check_query = text("""
        SELECT id, version, type FROM datasets WHERE id = :dataset_id
        """)
        
        result = await db.execute(check_query, {"dataset_id": dataset_id})
        row = result.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="Dataset not found")
        
        current_version = row[1]
        current_type = row[2]
        
        # Update dataset fields if provided
        update_data = dataset.dict(exclude_unset=True)
        
        # Construct the SQL update parts
        set_parts = []
        update_params = {"dataset_id": dataset_id}
        
        if "name" in update_data:
            set_parts.append("name = :name")
            update_params["name"] = update_data["name"]
        
        if "description" in update_data:
            set_parts.append("description = :description")
            update_params["description"] = update_data["description"]
        
        if "is_active" in update_data:
            set_parts.append("is_active = :is_active")
            update_params["is_active"] = update_data["is_active"]
        
        if "examples" in update_data:
            set_parts.append("examples = :examples")
            update_params["examples"] = json.dumps(update_data["examples"])
        
        # Handle metadata update and version
        if "metadata" in update_data:
            # Increment version
            new_version = current_version + 1
            set_parts.append("version = :version, meta_data = :meta_data")
            update_params["version"] = new_version
            update_params["meta_data"] = json.dumps(update_data["metadata"])
            
            # Create new version
            version_query = text("""
            INSERT INTO dataset_versions (dataset_id, version, meta_data, created_at, updated_at)
            VALUES (:dataset_id, :version, :meta_data, now(), now())
            """)
            await db.execute(
                version_query, 
                {
                    "dataset_id": dataset_id,
                    "version": new_version,
                    "meta_data": json.dumps(update_data["metadata"])
                }
            )
        
        if set_parts:
            # Update the dataset if there are fields to update
            set_parts.append("updated_at = now()")
            update_query = text(f"""
            UPDATE datasets 
            SET {", ".join(set_parts)}
            WHERE id = :dataset_id
            RETURNING id, name, description, type, version, is_active, meta_data, examples, created_at, updated_at
            """)
            
            update_result = await db.execute(update_query, update_params)
            updated_row = update_result.fetchone()
            
            if not updated_row:
                raise HTTPException(status_code=500, detail="Failed to update dataset")
            
            await db.commit()
            
            # Return the updated dataset
            return {
                "id": updated_row[0],
                "name": updated_row[1],
                "description": updated_row[2],
                "type": updated_row[3],
                "version": updated_row[4],
                "is_active": updated_row[5],
                "metadata": updated_row[6],
                "examples": updated_row[7],
                "created_at": updated_row[8],
                "updated_at": updated_row[9]
            }
        else:
            # If no fields to update, just get the current dataset
            get_query = text("""
            SELECT id, name, description, type, version, is_active, meta_data, examples, created_at, updated_at
            FROM datasets
            WHERE id = :dataset_id
            """)
            
            get_result = await db.execute(get_query, {"dataset_id": dataset_id})
            current_row = get_result.fetchone()
            
            return {
                "id": current_row[0],
                "name": current_row[1],
                "description": current_row[2],
                "type": current_row[3],
                "version": current_row[4],
                "is_active": current_row[5],
                "metadata": current_row[6],
                "examples": current_row[7],
                "created_at": current_row[8],
                "updated_at": current_row[9]
            }
    
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        print(f"Error updating dataset: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error updating dataset: {str(e)}"
        )

@router.delete("/{dataset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dataset(dataset_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a dataset."""
    try:
        # First check if the dataset exists using raw SQL
        check_query = text("""
        SELECT id FROM datasets WHERE id = :dataset_id
        """)
        
        result = await db.execute(check_query, {"dataset_id": dataset_id})
        row = result.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="Dataset not found")
        
        # Delete dataset items first using raw SQL
        delete_items_query = text("""
        DELETE FROM dataset_items WHERE dataset_id = :dataset_id
        """)
        await db.execute(delete_items_query, {"dataset_id": dataset_id})
        
        # Delete dataset versions 
        delete_versions_query = text("""
        DELETE FROM dataset_versions WHERE dataset_id = :dataset_id
        """)
        await db.execute(delete_versions_query, {"dataset_id": dataset_id})
        
        # Delete the dataset 
        delete_dataset_query = text("""
        DELETE FROM datasets WHERE id = :dataset_id
        """)
        await db.execute(delete_dataset_query, {"dataset_id": dataset_id})
        
        await db.commit()
        return None
    
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        print(f"Error deleting dataset: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error deleting dataset: {str(e)}"
        )

@router.post("/{dataset_id}/items", response_model=DatasetItemResponse)
async def create_dataset_item(
    dataset_id: int, 
    item: DatasetItemCreate, 
    db: AsyncSession = Depends(get_db)
):
    """Add an item to a dataset."""
    query = select(Dataset).filter(Dataset.id == dataset_id)
    result = await db.execute(query)
    db_dataset = result.scalar_one_or_none()
    
    if db_dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    db_item = DatasetItem(
        dataset_id=dataset_id,
        content=item.content,
        metadata=item.metadata
    )
    
    db.add(db_item)
    await db.commit()
    await db.refresh(db_item)
    
    return db_item

@router.get("/{dataset_id}/items", response_model=None)
async def get_dataset_items(
    dataset_id: int, 
    skip: int = 0, 
    limit: int = 100, 
    db: AsyncSession = Depends(get_db)
):
    """Get all items in a dataset."""
    try:
        # First check if dataset exists using raw SQL
        dataset_query = text("""
        SELECT id, name, type FROM datasets WHERE id = :dataset_id
        """)
        
        dataset_result = await db.execute(dataset_query, {"dataset_id": dataset_id})
        dataset_row = dataset_result.fetchone()
        
        if not dataset_row:
            raise HTTPException(status_code=404, detail="Dataset not found")
        
        # Get items using raw SQL
        items_query = text("""
        SELECT id, dataset_id, content, meta_data, created_at, updated_at
        FROM dataset_items
        WHERE dataset_id = :dataset_id
        ORDER BY id
        LIMIT :limit OFFSET :skip
        """)
        
        items_result = await db.execute(
            items_query, 
            {
                "dataset_id": dataset_id,
                "skip": skip,
                "limit": limit
            }
        )
        
        rows = items_result.fetchall()
        
        # Convert rows to dictionaries
        items = []
        for row in rows:
            items.append({
                "id": row[0],
                "dataset_id": row[1],
                "content": row[2],
                "metadata": row[3],  # Still name this "metadata" in the response
                "created_at": row[4],
                "updated_at": row[5]
            })
        
        return items
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error retrieving dataset items: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving dataset items: {str(e)}"
        )

@router.post("/{dataset_id}/versions", response_model=None)
async def create_dataset_version(
    dataset_id: int, 
    version: DatasetVersionCreate, 
    db: AsyncSession = Depends(get_db)
):
    """Create a new version of a dataset."""
    try:
        # First check if the dataset exists using raw SQL
        check_query = text("""
        SELECT id, version, meta_data FROM datasets WHERE id = :dataset_id
        """)
        
        dataset_result = await db.execute(check_query, {"dataset_id": dataset_id})
        dataset_row = dataset_result.fetchone()
        
        if not dataset_row:
            raise HTTPException(status_code=404, detail="Dataset not found")
        
        current_version = dataset_row[1]
        new_version = current_version + 1
        
        # Update dataset with new version and metadata if provided
        update_parts = ["version = :new_version"]
        update_params = {
            "dataset_id": dataset_id,
            "new_version": new_version
        }
        
        if version.metadata:
            update_parts.append("meta_data = :meta_data")
            update_params["meta_data"] = json.dumps(version.metadata)
        
        # Update the dataset
        update_query = text(f"""
        UPDATE datasets
        SET {', '.join(update_parts)}, updated_at = now()
        WHERE id = :dataset_id
        """)
        
        await db.execute(update_query, update_params)
        
        # Create new version record
        create_version_query = text("""
        INSERT INTO dataset_versions (dataset_id, version, meta_data, created_at, updated_at)
        VALUES (:dataset_id, :version, :meta_data, now(), now())
        RETURNING id, dataset_id, version, meta_data, created_at, updated_at
        """)
        
        version_result = await db.execute(
            create_version_query, 
            {
                "dataset_id": dataset_id,
                "version": new_version,
                "meta_data": json.dumps(version.metadata or {})
            }
        )
        
        version_row = version_result.fetchone()
        
        await db.commit()
        
        # Return version data
        return {
            "id": version_row[0],
            "dataset_id": version_row[1],
            "version": version_row[2],
            "metadata": version_row[3],
            "created_at": version_row[4],
            "updated_at": version_row[5]
        }
    
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        print(f"Error creating dataset version: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error creating dataset version: {str(e)}"
        )

@router.get("/{dataset_id}/versions", response_model=None)
async def get_dataset_versions(dataset_id: int, db: AsyncSession = Depends(get_db)):
    """Get all versions of a dataset."""
    try:
        # First check if the dataset exists using raw SQL
        check_query = text("""
        SELECT id FROM datasets WHERE id = :dataset_id
        """)
        
        dataset_result = await db.execute(check_query, {"dataset_id": dataset_id})
        dataset_row = dataset_result.fetchone()
        
        if not dataset_row:
            raise HTTPException(status_code=404, detail="Dataset not found")
        
        # Get versions using raw SQL
        versions_query = text("""
        SELECT id, dataset_id, version, meta_data, created_at, updated_at
        FROM dataset_versions
        WHERE dataset_id = :dataset_id
        ORDER BY version DESC
        """)
        
        versions_result = await db.execute(versions_query, {"dataset_id": dataset_id})
        rows = versions_result.fetchall()
        
        # Convert rows to dictionaries
        versions = []
        for row in rows:
            versions.append({
                "id": row[0],
                "dataset_id": row[1],
                "version": row[2],
                "metadata": row[3],
                "created_at": row[4],
                "updated_at": row[5]
            })
        
        return versions
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error retrieving dataset versions: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving dataset versions: {str(e)}"
        )

@router.post("/upload", response_model=DatasetResponse)
async def upload_dataset(
    dataset_upload: DatasetUpload,
    db: AsyncSession = Depends(get_db)
):
    """Upload a dataset from file content."""
    # Create the dataset
    db_dataset = Dataset(
        name=dataset_upload.name,
        description=dataset_upload.description,
        dataset_type=dataset_upload.file_type,
        meta_data=dataset_upload.metadata
    )
    db.add(db_dataset)
    await db.commit()
    await db.refresh(db_dataset)
    
    # Create initial version
    db_version = DatasetVersion(
        dataset_id=db_dataset.id,
        version=1,
        meta_data=dataset_upload.metadata
    )
    db.add(db_version)
    await db.commit()
    
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
    
    await db.commit()
    await db.refresh(db_dataset)
    
    return db_dataset

@router.post("/upload/file", response_model=None)
async def upload_dataset_file(
    file: UploadFile = File(...),
    name: str = Form(...),
    description: str = Form(None),
    file_type: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    """Upload a dataset from a file."""
    try:
        # Convert file_type to lowercase and validate
        file_type_lower = file_type.lower()
        
        # Validate file type
        valid_types = ["text", "json", "csv", "jsonl", "custom"]
        if file_type_lower not in valid_types:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid file_type. Must be one of: {', '.join(valid_types)}"
            )
        
        # Create the dataset with SQL to bypass SQLAlchemy's enum handling
        metadata_json = json.dumps({})  # Ensure valid JSON for metadata
        examples_json = json.dumps([])  # Empty examples array
        
        # Create SQL query with enum value directly embedded
        query = text(f"""
        INSERT INTO datasets (name, description, type, version, is_active, meta_data, examples, created_at, updated_at)
        VALUES (:name, :description, '{file_type_lower}'::datasettype, :version, :is_active, :meta_data, :examples, now(), now())
        RETURNING id, created_at, updated_at
        """)
        
        try:
            result = await db.execute(
                query, 
                {
                    "name": name, 
                    "description": description, 
                    "version": 1, 
                    "is_active": True, 
                    "meta_data": metadata_json,
                    "examples": examples_json
                }
            )
            row = result.fetchone()
            dataset_id = row[0]
        except Exception as db_error:
            # Handle database-specific errors
            await db.rollback()
            raise HTTPException(
                status_code=500,
                detail=f"Database error creating dataset: {str(db_error)}"
            )
        
        # Create initial version
        try:
            db_version = DatasetVersion(
                dataset_id=dataset_id,
                version=1,
                meta_data={}
            )
            db.add(db_version)
            await db.commit()
        except Exception as version_error:
            await db.rollback()
            # Try to clean up the dataset if version creation fails
            await db.execute(text("DELETE FROM datasets WHERE id = :id"), {"id": dataset_id})
            await db.commit()
            raise HTTPException(
                status_code=500,
                detail=f"Error creating dataset version: {str(version_error)}"
            )
        
        # Read and decode file content
        try:
            content = await file.read()
            try:
                content_str = content.decode('utf-8')
            except UnicodeDecodeError:
                # If UTF-8 decoding fails, try with other common encodings
                for encoding in ['latin-1', 'iso-8859-1', 'windows-1252']:
                    try:
                        content_str = content.decode(encoding)
                        break
                    except UnicodeDecodeError:
                        continue
                else:
                    raise ValueError("Unable to decode file with common encodings")
        except Exception as read_error:
            # Clean up if file reading fails
            await db.execute(text("DELETE FROM datasets WHERE id = :id"), {"id": dataset_id})
            await db.commit()
            raise HTTPException(
                status_code=400,
                detail=f"Error reading file: {str(read_error)}"
            )
        
        # Process the file content based on type
        items = []
        
        try:
            if file_type_lower == "json":
                try:
                    json_data = json.loads(content_str)
                    if isinstance(json_data, dict):
                        items = [json_data]
                    elif isinstance(json_data, list):
                        items = json_data
                    else:
                        raise ValueError("Invalid JSON content type. Expected object or array.")
                except json.JSONDecodeError as e:
                    raise ValueError(f"Invalid JSON format: {str(e)}")
            
            elif file_type_lower == "jsonl":
                for line_num, line in enumerate(content_str.splitlines(), 1):
                    if not line.strip():
                        continue
                    try:
                        items.append(json.loads(line))
                    except json.JSONDecodeError as e:
                        raise ValueError(f"Invalid JSON at line {line_num}: {str(e)}")
            
            elif file_type_lower == "csv":
                # More robust CSV parsing
                csv_file = io.StringIO(content_str)
                # Try to detect dialect for better parsing
                try:
                    dialect = csv.Sniffer().sniff(csv_file.read(1024))
                    csv_file.seek(0)
                except:
                    dialect = csv.excel  # Default to standard CSV
                    csv_file.seek(0)
                
                # Try to read with the detected dialect
                reader = csv.DictReader(csv_file, dialect=dialect)
                # Handle missing or empty headers
                if not reader.fieldnames or all(not f for f in reader.fieldnames):
                    raise ValueError("CSV file must have headers in the first row")
                
                # Clean up field names by stripping whitespace
                reader.fieldnames = [f.strip() if f else f"column_{i}" for i, f in enumerate(reader.fieldnames)]
                
                # Process each row
                for row_num, row in enumerate(reader, 1):
                    # Convert empty strings to None and strip whitespace from values
                    cleaned_row = {}
                    for key, value in row.items():
                        if key is None:
                            continue  # Skip keys that are None
                        cleaned_key = key.strip() if key else f"column_{len(cleaned_row)}"
                        cleaned_value = value.strip() if value else None
                        cleaned_row[cleaned_key] = cleaned_value
                    
                    if cleaned_row:  # Only add non-empty rows
                        items.append(cleaned_row)
                
                if not items:
                    raise ValueError("No valid data rows found in CSV file")
            
            elif file_type_lower == "text":
                lines = content_str.splitlines()
                for line in lines:
                    if line.strip():
                        items.append({"text": line})
            
            if not items:
                raise ValueError("No items were extracted from the file")
            
        except Exception as parsing_error:
            # Clean up if parsing fails
            await db.execute(text("DELETE FROM datasets WHERE id = :id"), {"id": dataset_id})
            await db.commit()
            raise HTTPException(
                status_code=400,
                detail=f"Error parsing file content: {str(parsing_error)}"
            )
        
        # Add items to the dataset in batches to handle large files
        try:
            batch_size = 100
            for i in range(0, len(items), batch_size):
                batch = items[i:i + batch_size]
                for item_content in batch:
                    db_item = DatasetItem(
                        dataset_id=dataset_id,
                        content=item_content,
                        metadata={}
                    )
                    db.add(db_item)
                await db.commit()
        except Exception as item_error:
            # If adding items fails, log the error but don't delete the dataset
            # since partial data might be better than no data
            print(f"Error adding some items to dataset {dataset_id}: {str(item_error)}")
            await db.rollback()
            # Continue to return the dataset even if some items failed
        
        # Fetch the created dataset
        try:
            # Use a raw SQL query to fetch the dataset directly as a dictionary
            # This avoids SQLAlchemy's enum conversion issues
            get_query = text("""
            SELECT id, name, description, type, version, is_active, meta_data, examples, created_at, updated_at 
            FROM datasets 
            WHERE id = :id
            """)
            
            result = await db.execute(get_query, {"id": dataset_id})
            row = result.fetchone()
            
            if not row:
                raise ValueError(f"Dataset with id {dataset_id} not found after creation")
            
            # Manually construct the response object
            return {
                "id": row[0],
                "name": row[1],
                "description": row[2],
                "type": row[3],  # Return the string directly
                "version": row[4],
                "is_active": row[5],
                "metadata": row[6],
                "examples": row[7],
                "created_at": row[8],
                "updated_at": row[9],
                "items_count": len(items),
                "status": "success"
            }
        except Exception as fetch_error:
            print(f"Error fetching dataset after creation: {str(fetch_error)}")
            # Dataset was created but we couldn't fetch it properly
            # Return a simplified success response
            return {
                "id": dataset_id,
                "name": name,
                "description": description,
                "type": file_type_lower,
                "version": 1,
                "is_active": True,
                "metadata": {},
                "examples": [],
                "created_at": row[1] if 'row' in locals() and row else None,
                "updated_at": row[2] if 'row' in locals() and row else None,
                "items_count": len(items),
                "status": "success"
            }
    
    except HTTPException:
        # Re-raise HTTP exceptions as they already have proper status and detail
        raise
    except Exception as e:
        # Log any unexpected errors
        print(f"Unexpected error in upload_dataset_file: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while processing the file"
        )

@router.post("/upload/csv", status_code=status.HTTP_200_OK)
async def upload_csv_file(
    file: UploadFile = File(...),
    name: str = Form(...),
    description: str = Form(None),
    db: AsyncSession = Depends(get_db)
):
    """Upload a CSV file and create a dataset with the items parsed from it."""
    try:
        # Read and decode file content
        content = await file.read()
        try:
            content_str = content.decode('utf-8')
        except UnicodeDecodeError:
            # If UTF-8 decoding fails, try with other common encodings
            for encoding in ['latin-1', 'iso-8859-1', 'windows-1252']:
                try:
                    content_str = content.decode(encoding)
                    break
                except UnicodeDecodeError:
                    continue
            else:
                raise HTTPException(
                    status_code=400, 
                    detail="Unable to decode CSV file with common encodings"
                )
        
        # Parse CSV content
        items = []
        csv_file = io.StringIO(content_str)
        
        # Try to detect dialect for better parsing
        try:
            dialect = csv.Sniffer().sniff(csv_file.read(1024))
            csv_file.seek(0)
        except:
            dialect = csv.excel  # Default to standard CSV
            csv_file.seek(0)
        
        # Try to read with the detected dialect
        reader = csv.DictReader(csv_file, dialect=dialect)
        
        # Handle missing or empty headers
        if not reader.fieldnames or all(not f for f in reader.fieldnames):
            raise HTTPException(
                status_code=400, 
                detail="CSV file must have headers in the first row"
            )
        
        # Clean up field names by stripping whitespace
        reader.fieldnames = [f.strip() if f else f"column_{i}" for i, f in enumerate(reader.fieldnames)]
        
        # Process each row
        for row in reader:
            # Convert empty strings to None and strip whitespace from values
            cleaned_row = {}
            for key, value in row.items():
                if key is None:
                    continue  # Skip keys that are None
                cleaned_key = key.strip() if key else f"column_{len(cleaned_row)}"
                cleaned_value = value.strip() if value else None
                cleaned_row[cleaned_key] = cleaned_value
            
            if cleaned_row:  # Only add non-empty rows
                items.append(cleaned_row)
        
        if not items:
            raise HTTPException(
                status_code=400, 
                detail="No valid data rows found in CSV file"
            )
        
        # Create dataset using raw SQL to bypass ORM issues
        metadata_json = json.dumps({})  # Ensure valid JSON for metadata
        examples_json = json.dumps([])  # Empty examples array
        
        # Create SQL query with enum value directly embedded
        query = text(f"""
        INSERT INTO datasets (name, description, type, version, is_active, meta_data, examples, created_at, updated_at)
        VALUES (:name, :description, 'csv'::datasettype, :version, :is_active, :meta_data, :examples, now(), now())
        RETURNING id, created_at, updated_at
        """)
        
        try:
            result = await db.execute(
                query, 
                {
                    "name": name, 
                    "description": description or "", 
                    "version": 1, 
                    "is_active": True, 
                    "meta_data": metadata_json,
                    "examples": examples_json
                }
            )
            row = result.fetchone()
            dataset_id = row[0]
        except Exception as db_error:
            # Handle database-specific errors
            await db.rollback()
            raise HTTPException(
                status_code=500,
                detail=f"Database error creating dataset: {str(db_error)}"
            )
        
        # Create initial version
        try:
            db_version = DatasetVersion(
                dataset_id=dataset_id,
                version=1,
                meta_data={}
            )
            db.add(db_version)
            await db.commit()
        except Exception as version_error:
            await db.rollback()
            # Try to clean up the dataset if version creation fails
            await db.execute(text("DELETE FROM datasets WHERE id = :id"), {"id": dataset_id})
            await db.commit()
            raise HTTPException(
                status_code=500,
                detail=f"Error creating dataset version: {str(version_error)}"
            )
        
        # Add items to the dataset
        for item_content in items:
            db_item = DatasetItem(
                dataset_id=dataset_id,
                content=item_content,
                metadata={}
            )
            db.add(db_item)
        
        await db.commit()
        
        # Return simplified response
        return {
            "success": True,
            "id": dataset_id,
            "name": name,
            "description": description,
            "type": "csv",
            "items_count": len(items),
            "message": f"CSV dataset '{name}' created successfully with {len(items)} items"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in CSV upload: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing CSV file: {str(e)}"
        ) 