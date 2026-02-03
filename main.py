"""
Google Cloud Run Entry Point.

This module exposes the FastAPI app for Google Cloud Run.
It handles the PORT environment variable that Cloud Run provides.

Usage:
    - Local testing: python main.py
    - Cloud Run: Automatically started via Procfile
"""

import os
import sys
from pathlib import Path

# Add src directory to Python path for imports to work correctly
# This is necessary because the modules inside src/ use relative imports
# (e.g., 'from adapters.redis import ...')
src_path = str(Path(__file__).parent / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# Also add root to path so 'src.main' style imports work
root_path = str(Path(__file__).parent)
if root_path not in sys.path:
    sys.path.insert(0, root_path)

# Now import the FastAPI application
# Since src is in sys.path, we can import main directly (which is src/main.py)
# We need to use a different name to avoid conflict with this file
import src.main as src_main  # noqa: E402

app = src_main.app

# Re-export app for Cloud Run / Uvicorn
__all__ = ["app"]

if __name__ == "__main__":
    import uvicorn

    # Cloud Run provides the PORT environment variable
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
