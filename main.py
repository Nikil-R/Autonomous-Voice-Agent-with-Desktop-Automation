"""Main FastAPI application entry point.

Run using:
uvicorn main:app --reload
"""

import sys
from pathlib import Path

# Add project root directory to sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Import the FastAPI instance
from api.app import app

__all__ = ["app"]
