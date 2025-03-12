#!/usr/bin/env python3
"""
Script to run database migrations.
"""

import asyncio
import os
import sys
import subprocess
from pathlib import Path

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings


def run_migrations():
    """Run database migrations."""
    try:
        # Get the backend directory
        backend_dir = Path(__file__).parent.parent.absolute()
        
        # Run alembic migrations
        print(f"Running migrations for database: {settings.DATABASE_URL}")
        result = subprocess.run(
            ["alembic", "upgrade", "head"],
            cwd=backend_dir,
            check=True,
            capture_output=True,
            text=True
        )
        
        print(result.stdout)
        
        if result.stderr:
            print(f"Warnings: {result.stderr}", file=sys.stderr)
        
        print("Migrations completed successfully.")
        
    except subprocess.CalledProcessError as e:
        print(f"Error running migrations: {e}", file=sys.stderr)
        print(f"Output: {e.stdout}", file=sys.stderr)
        print(f"Error: {e.stderr}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    run_migrations() 