#!/usr/bin/env python3
"""
Database initialization script.
This script creates the initial database schema and populates it with sample data.
"""

import os
import sys
from pathlib import Path

# Add the parent directory to sys.path
sys.path.append(str(Path(__file__).parent.parent.parent))

import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from backend.models import Base
from backend.config import settings

# Sample data for initial population
SAMPLE_PROMPTS = [
    {
        "name": "Simple Question Answering",
        "content": "Answer the following question accurately and concisely: {{question}}",
        "description": "A basic prompt for question answering tasks",
        "tags": ["qa", "general"]
    },
    {
        "name": "Code Review",
        "content": "Review the following code and suggest improvements:\n```{{language}}\n{{code}}\n```",
        "description": "Prompt for code review and suggestions",
        "tags": ["code", "review"]
    }
]

SAMPLE_DATASETS = [
    {
        "name": "General QA Pairs",
        "description": "A collection of general question-answer pairs for testing",
        "examples": [
            {"inputs": {"question": "What is the capital of France?"}, "expected_output": "Paris"},
            {"inputs": {"question": "Who wrote Romeo and Juliet?"}, "expected_output": "William Shakespeare"}
        ]
    },
    {
        "name": "Code Samples",
        "description": "Various code snippets for testing code-related prompts",
        "examples": [
            {
                "inputs": {
                    "language": "python",
                    "code": "def factorial(n):\n    if n == 0:\n        return 1\n    else:\n        return n * factorial(n-1)"
                },
                "expected_output": "The recursive factorial function looks correct, but consider adding error handling for negative inputs and using an iterative approach to avoid stack overflow for large inputs."
            }
        ]
    }
]


async def init_db():
    """Initialize the database with tables and sample data."""
    # Create async engine
    engine = create_async_engine(settings.DATABASE_URL)
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    
    # Create session
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    # Add sample data
    async with async_session() as session:
        from backend.models.prompts import Prompt
        from backend.models.datasets import Dataset
        import json
        
        # Add prompts
        for prompt_data in SAMPLE_PROMPTS:
            prompt = Prompt(
                name=prompt_data["name"],
                content=prompt_data["content"],
                description=prompt_data["description"],
                tags=prompt_data["tags"],
                version=1
            )
            session.add(prompt)
        
        # Add datasets
        for dataset_data in SAMPLE_DATASETS:
            dataset = Dataset(
                name=dataset_data["name"],
                description=dataset_data["description"],
                examples=json.dumps(dataset_data["examples"]),
                version=1
            )
            session.add(dataset)
        
        await session.commit()
    
    await engine.dispose()
    
    print("Database initialized successfully with sample data!")


if __name__ == "__main__":
    asyncio.run(init_db()) 