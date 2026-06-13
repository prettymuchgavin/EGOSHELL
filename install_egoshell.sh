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
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    echo "Virtual environment created."
else
    echo "Virtual environment already exists."
fi

# Activate the environment
source .venv/bin/activate

# Check if setup.py exists before running
if [ -f "setup.py" ]; then
    echo "Running setup.py within venv..."
    python3 setup.py
else
    echo "Error: setup.py not found in $HOME/$DIR_NAME"
    exit 1
fi

echo "Setup complete!"
