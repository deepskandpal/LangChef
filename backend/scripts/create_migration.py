#!/usr/bin/env python3
"""
Migration generation script.
This script creates a new migration using Alembic.
"""

import os
import sys
import argparse
from pathlib import Path

# Add the parent directory to sys.path
sys.path.append(str(Path(__file__).parent.parent.parent))

def create_migration():
    """Create a new migration using Alembic."""
    parser = argparse.ArgumentParser(description="Create a new database migration")
    parser.add_argument("message", help="Migration message")
    parser.add_argument("--autogenerate", action="store_true", help="Autogenerate migration based on model changes")
    
    args = parser.parse_args()
    
    # Change to the backend directory where alembic.ini is located
    os.chdir(Path(__file__).parent.parent)
    
    # Build the alembic command
    cmd = f"alembic revision"
    if args.autogenerate:
        cmd += " --autogenerate"
    cmd += f" -m \"{args.message}\""
    
    # Run the command
    print(f"Running: {cmd}")
    os.system(cmd)
    
    print("Migration created successfully!")

if __name__ == "__main__":
    create_migration() 