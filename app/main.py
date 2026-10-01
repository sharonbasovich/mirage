"""ASGI entrypoint for deployment: `uvicorn app.main:app`."""
from fastapi import FastAPI

try:
    from mirage.api import app
except ImportError:  # dependency-free environments (e.g. deploy detection)
    app = FastAPI(title="Mirage")

__all__ = ["app"]
