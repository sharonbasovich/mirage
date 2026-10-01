"""ASGI entrypoint for deployment: `uvicorn app.main:app`."""
from fastapi import FastAPI

from mirage.api import app as app

assert isinstance(app, FastAPI)

__all__ = ["app"]
