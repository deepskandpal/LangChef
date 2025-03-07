#!/usr/bin/env python3
"""
Migration application script.
This script applies migrations using Alembic.
"""

import os
import sys
import argparse
from pathlib import Path

# Add the parent directory to sys.path
sys.path.append(str(Path(__file__).parent.parent.parent))

def apply_migrations():
    """Apply migrations using Alembic."""
    parser = argparse.ArgumentParser(description="Apply database migrations")
    parser.add_argument("--revision", default="head", help="Revision to upgrade to (default: head)")
    parser.add_argument("--sql", action="store_true", help="Don't emit SQL to database - dump to standard output instead")
    
    args = parser.parse_args()
    
    # Change to the backend directory where alembic.ini is located
    os.chdir(Path(__file__).parent.parent)
    
    # Build the alembic command
    cmd = f"alembic upgrade"
    if args.sql:
        cmd += " --sql"
    cmd += f" {args.revision}"
    
    # Run the command
    print(f"Running: {cmd}")
    os.system(cmd)
    
    if not args.sql:
        print("Migrations applied successfully!")

if __name__ == "__main__":
    apply_migrations() 