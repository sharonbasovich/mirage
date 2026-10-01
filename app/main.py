"""ASGI entrypoint for deployment: `uvicorn app.main:app`."""
from mirage.api import app

__all__ = ["app"]
