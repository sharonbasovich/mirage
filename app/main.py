"""ASGI entrypoint for deployment: `uvicorn app.main:app`."""
from fastapi import FastAPI

from mirage.api import app as _app

app = _app if isinstance(_app, FastAPI) else FastAPI(title="Mirage")

__all__ = ["app"]
