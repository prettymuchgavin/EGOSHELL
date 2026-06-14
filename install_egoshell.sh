#!/bin/bash

# Exit on any error
set -e

# Define the repository URL and directory name
REPO_URL="https://github.com/prettymuchgavin/EGOSHELL.git"
DIR_NAME="EGOSHELL"

echo "Cloning EGOSHELL repository..."
if [ -d "$HOME/$DIR_NAME" ]; then
    echo "Directory $DIR_NAME already exists. Pulling latest changes..."
    cd "$HOME/$DIR_NAME"
    git pull
else
    git clone "$REPO_URL" "$HOME/$DIR_NAME"
    cd "$HOME/$DIR_NAME"
fi

# Create and activate Python virtual environment
echo "Setting up Python virtual environment..."

# Detect python command
PYTHON_CMD="python3"
if ! command -v python3 &>/dev/null; then
    if command -v python &>/dev/null; then
        PYTHON_CMD="python"
    else
        echo "Error: Python is not installed or not in PATH."
        exit 1
    fi
fi

if [ ! -d ".venv" ]; then
    $PYTHON_CMD -m venv .venv
    echo "Virtual environment created."
else
    echo "Virtual environment already exists."
fi

# Activate the environment
if [ -f ".venv/Scripts/activate" ]; then
    source .venv/Scripts/activate
elif [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
else
    echo "Error: Virtual environment activation script not found."
    exit 1
fi

# Check if setup.py exists before running
if [ -f "setup.py" ]; then
    echo "Running setup.py within venv..."
    $PYTHON_CMD setup.py < /dev/tty
else
    echo "Error: setup.py not found in $(pwd)"
    exit 1
fi

echo "Setup complete!"
