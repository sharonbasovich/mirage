"""Regression test: the deployment entrypoint exposes the real Mirage API app."""
from fastapi import FastAPI

from app.main import app
from mirage import api


def test_deploy_app_is_real_application() -> None:
    assert app is api.app
    assert isinstance(app, FastAPI)


def test_deploy_app_exposes_expected_endpoints() -> None:
    paths = {route.path for route in app.routes}
    for expected in (
        "/api/health",
        "/api/strategies",
        "/api/demos",
        "/api/run",
        "/api/demo/{key}",
        "/api/audit",
        "/api/ledger/verify",
    ):
        assert expected in paths, f"missing endpoint {expected}"
