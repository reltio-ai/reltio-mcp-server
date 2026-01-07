#!/bin/bash

set -e

echo "Using uv to manage Python and virtualenv (uv is required)..."
if command -v uv >/dev/null 2>&1; then
    echo "Found uv. Ensuring Python 3.13 and virtualenv via uv..."
    uv python install 3.13 || true
    if [ ! -d ".venv" ]; then
        uv venv -p 3.13 .venv
    else
        echo "Virtual environment .venv already exists."
    fi
    PYTHON=".venv/bin/python"
else
    echo "uv not found. Please install uv before running this script: https://pypa.github.io/uv/"
    exit 1
fi

# Verify the selected Python is >= 3.13
if ! $PYTHON -c 'import sys; exit(not (sys.version_info >= (3,13)))' 2>/dev/null; then
  echo "Python 3.13+ is required. Please check the installation."
  exit 1
fi

# Activate existing virtual environment
source ./.venv/bin/activate

# 3. Install MCP & requirements
echo "Installing dependencies using uv..."
uv add "mcp[cli]" httpx requests

# 5. Run the MCP server
echo "Starting MCP server..."
mcp install --with requests --with pyyaml main.py -f .env 

echo "MCP server started. Restart the Claude app now."
