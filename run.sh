#!/bin/bash
# Starts the pipeline. Your data persists between runs; use `python3 db.py --reset` to start over.
cd "$(dirname "$0")"
python3 db.py
echo "=========================================================="
echo "  Job Hunt Pipeline Studio V2: http://localhost:8000"
echo "=========================================================="
python3 server.py
