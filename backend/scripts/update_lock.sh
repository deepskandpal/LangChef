#!/bin/bash
# Script to update the uv.lock file when dependencies change

set -e

echo "Updating uv.lock file from pyproject.toml..."
uv pip compile ../pyproject.toml -o ../uv.lock

echo "Done! Updated uv.lock file."
echo "To install the updated dependencies, run: uv pip install -e .." 