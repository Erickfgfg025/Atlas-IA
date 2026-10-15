from __future__ import annotations

"""PyInstaller entry point for the ATLAS AI local API."""
import uvicorn

from atlas.backend.main import app


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info", access_log=False)
