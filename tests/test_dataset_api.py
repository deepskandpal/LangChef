import pytest
import os
import json
import csv
import tempfile
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker

# Import your FastAPI app and database utilities
from backend.main import app
from backend.models import Base
from backend.utils import get_db

# Create a test database
TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5434/test_db")

engine = create_async_engine(TEST_DATABASE_URL, echo=True)
TestingSessionLocal = sessionmaker(class_=AsyncSession, autocommit=False, autoflush=False, bind=engine)

# Test client
client = TestClient(app)

# Override the get_db dependency
async def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        await db.close()

app.dependency_overrides[get_db] = override_get_db

# Fixtures
@pytest.fixture(scope="module")
async def setup_database():
    # Create the test database tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Clean up after tests
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture
def csv_file():
    # Create a temporary CSV file for testing
    with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.csv') as temp:
        writer = csv.writer(temp)
        writer.writerow(['name', 'age', 'city'])
        writer.writerow(['John Doe', '30', 'New York'])
        writer.writerow(['Jane Smith', '25', 'San Francisco'])
        writer.writerow(['Mike Johnson', '35', 'Chicago'])
    
    yield temp.name
    # Clean up the temporary file
    os.unlink(temp.name)

@pytest.fixture
def json_file():
    # Create a temporary JSON file for testing
    with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.json') as temp:
        json.dump([
            {'name': 'John Doe', 'age': 30, 'city': 'New York'},
            {'name': 'Jane Smith', 'age': 25, 'city': 'San Francisco'},
            {'name': 'Mike Johnson', 'age': 35, 'city': 'Chicago'}
        ], temp)
    
    yield temp.name
    # Clean up the temporary file
    os.unlink(temp.name)

# Tests
@pytest.mark.asyncio
async def test_create_dataset(setup_database):
    """Test creating a dataset using the API"""
    # Create a new dataset
    response = client.post("/api/datasets/", json={
        "name": "Test Dataset",
        "description": "Test dataset description",
        "type": "csv",
        "items": [
            {"name": "John Doe", "age": "30", "city": "New York"},
            {"name": "Jane Smith", "age": "25", "city": "San Francisco"},
            {"name": "Mike Johnson", "age": "35", "city": "Chicago"}
        ]
    })
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Dataset"
    assert data["description"] == "Test dataset description"
    assert data["type"] == "csv"
    
    # Get the dataset to verify it was created
    dataset_id = data["id"]
    response = client.get(f"/api/datasets/{dataset_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Dataset"

@pytest.mark.asyncio
async def test_upload_csv_file(setup_database, csv_file):
    """Test uploading a CSV file using the API"""
    with open(csv_file, "rb") as f:
        response = client.post(
            "/api/datasets/upload/file",
            files={"file": ("test.csv", f, "text/csv")},
            data={
                "name": "Test CSV Upload",
                "description": "Testing CSV file upload",
                "file_type": "csv"
            }
        )
    
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test CSV Upload"
    assert data["description"] == "Testing CSV file upload"
    assert data["type"] == "csv"
    
    # Verify items were created from the CSV
    dataset_id = data["id"]
    response = client.get(f"/api/datasets/{dataset_id}/items")
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 3  # 3 rows in our test CSV
    
    # Check content of first item
    assert "name" in items[0]["content"]
    assert "age" in items[0]["content"]
    assert "city" in items[0]["content"]

@pytest.mark.asyncio
async def test_upload_csv_with_empty_rows(setup_database):
    """Test CSV upload with empty rows that should be handled gracefully"""
    # Create a CSV with empty rows
    with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.csv') as temp:
        writer = csv.writer(temp)
        writer.writerow(['name', 'age', 'city'])
        writer.writerow(['John Doe', '30', 'New York'])
        writer.writerow([])  # Empty row
        writer.writerow(['Jane Smith', '25', 'San Francisco'])
        writer.writerow(['', '', ''])  # Row with empty values
        writer.writerow(['Mike Johnson', '35', 'Chicago'])
    
    with open(temp.name, "rb") as f:
        response = client.post(
            "/api/datasets/upload/file",
            files={"file": ("test.csv", f, "text/csv")},
            data={
                "name": "CSV With Empty Rows",
                "description": "Testing CSV with empty rows",
                "file_type": "csv"
            }
        )
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify only valid rows were processed
    dataset_id = data["id"]
    response = client.get(f"/api/datasets/{dataset_id}/items")
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 3  # Only the 3 valid rows should be processed
    
    # Clean up
    os.unlink(temp.name)

@pytest.mark.asyncio
async def test_upload_csv_with_different_dialect(setup_database):
    """Test uploading a CSV with different dialect (semicolon separated)"""
    with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.csv') as temp:
        temp.write('name;age;city\n')
        temp.write('John Doe;30;New York\n')
        temp.write('Jane Smith;25;San Francisco\n')
        temp.write('Mike Johnson;35;Chicago\n')
    
    with open(temp.name, "rb") as f:
        response = client.post(
            "/api/datasets/upload/file",
            files={"file": ("test.csv", f, "text/csv")},
            data={
                "name": "Semicolon CSV",
                "description": "Testing semicolon-separated CSV",
                "file_type": "csv"
            }
        )
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify items were processed correctly
    dataset_id = data["id"]
    response = client.get(f"/api/datasets/{dataset_id}/items")
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 3
    
    # Clean up
    os.unlink(temp.name)

@pytest.mark.asyncio
async def test_upload_csv_with_whitespace(setup_database):
    """Test CSV upload with values containing whitespace"""
    with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.csv') as temp:
        writer = csv.writer(temp)
        writer.writerow(['  name  ', ' age ', '  city  '])
        writer.writerow(['  John Doe  ', '  30  ', '  New York  '])
        writer.writerow(['  Jane Smith  ', '  25  ', '  San Francisco  '])
    
    with open(temp.name, "rb") as f:
        response = client.post(
            "/api/datasets/upload/file",
            files={"file": ("test.csv", f, "text/csv")},
            data={
                "name": "Whitespace CSV",
                "description": "Testing CSV with whitespace",
                "file_type": "csv"
            }
        )
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify items were processed with whitespace trimmed
    dataset_id = data["id"]
    response = client.get(f"/api/datasets/{dataset_id}/items")
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 2
    
    # Check that whitespace was trimmed
    assert items[0]["content"]["name"] == "John Doe"
    assert items[0]["content"]["age"] == "30"
    assert items[0]["content"]["city"] == "New York"
    
    # Clean up
    os.unlink(temp.name)

@pytest.mark.asyncio
async def test_create_dataset_uppercase_type(setup_database):
    """Test creating a dataset with uppercase type that should be converted to lowercase"""
    response = client.post("/api/datasets/", json={
        "name": "Uppercase Type Test",
        "description": "Testing case insensitivity for type",
        "type": "CSV",  # Uppercase type
        "items": [
            {"name": "John Doe", "age": "30", "city": "New York"}
        ]
    })
    
    assert response.status_code == 201
    data = response.json()
    assert data["type"] == "csv"  # Should be converted to lowercase

@pytest.mark.asyncio
async def test_json_upload(setup_database, json_file):
    """Test uploading a JSON file"""
    with open(json_file, "rb") as f:
        response = client.post(
            "/api/datasets/upload/file",
            files={"file": ("test.json", f, "application/json")},
            data={
                "name": "Test JSON Upload",
                "description": "Testing JSON file upload",
                "file_type": "json"
            }
        )
    
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test JSON Upload"
    assert data["type"] == "json"
    
    # Verify items were created from the JSON
    dataset_id = data["id"]
    response = client.get(f"/api/datasets/{dataset_id}/items")
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 3

@pytest.mark.asyncio
async def test_batch_processing(setup_database):
    """Test that large datasets are processed in batches"""
    # Create a dataset with many items (more than batch size)
    items = [{"index": i, "value": f"test{i}"} for i in range(200)]  # More than batch size (100)
    
    response = client.post("/api/datasets/", json={
        "name": "Batch Test",
        "description": "Testing batch processing",
        "type": "custom",
        "items": items
    })
    
    assert response.status_code == 201
    data = response.json()
    
    # Verify all items were created
    dataset_id = data["id"]
    response = client.get(f"/api/datasets/{dataset_id}/items")
    assert response.status_code == 200
    result_items = response.json()
    assert len(result_items) == 200

if __name__ == "__main__":
    pytest.main(["-v", "test_dataset_api.py"]) 