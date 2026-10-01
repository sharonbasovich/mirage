"""ASGI entrypoint for deployment: `uvicorn app.main:app`."""
from fastapi import FastAPI

from mirage.api import app as _app

app: FastAPI = _app

__all__ = ["app"]
