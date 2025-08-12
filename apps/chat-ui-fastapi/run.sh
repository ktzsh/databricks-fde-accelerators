#!/bin/bash
set -x

cd "$(dirname "$0")";

source .venv/bin/activate;

# Start the FastAPI server with port from environment variable
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port ${PORT:-8080}
