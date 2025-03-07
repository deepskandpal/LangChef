#!/usr/bin/env python3
"""
Development server script with hot reloading.
This script runs the FastAPI application with uvicorn and enables hot reloading.
"""

import os
import sys
from pathlib import Path

# Add the parent directory to sys.path
sys.path.append(str(Path(__file__).parent.parent.parent))

import uvicorn
from backend.config import settings

if __name__ == "__main__":
    uvicorn.run(
        "backend.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True,
        reload_dirs=["backend"],
        log_level="info"
    ) 