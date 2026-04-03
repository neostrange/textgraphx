#!/bin/bash
# TextGraphX Pipeline Execution Script
# Convenience wrapper that handles environment setup and runs the pipeline
#
# Usage:
#   ./run.sh                          # Full pipeline with default dataset
#   ./run.sh --dataset /custom/path   # Full pipeline with custom dataset
#   ./run.sh --phases ingestion       # Run only ingestion phase
#   ./run.sh --check                  # Run health checks without executing
#   ./run.sh --help                   # Show all options

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv310"

# Check if venv exists
if [ ! -d "$VENV_DIR" ]; then
    echo "Error: Virtual environment not found at $VENV_DIR"
    echo "Creating virtual environment..."
    python3.10 -m venv "$VENV_DIR"
    
    echo "Activating venv and installing dependencies..."
    source "$VENV_DIR/bin/activate"
    pip install --upgrade pip setuptools wheel
    pip install -r "$SCRIPT_DIR/requirements.txt"
    pip install spacy
    python -m spacy download en_core_web_sm
    deactivate
fi

# Activate virtual environment
source "$VENV_DIR/bin/activate"

# Set PYTHONPATH
export PYTHONPATH="$SCRIPT_DIR:${PYTHONPATH}"

# Run the pipeline orchestrator
python "$SCRIPT_DIR/run_pipeline.py" "$@"

# Deactivate when done
deactivate
