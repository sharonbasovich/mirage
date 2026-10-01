"""ASGI entrypoint for deployment: `uvicorn main:app`."""
from mirage.api import app

__all__ = ["app"]
