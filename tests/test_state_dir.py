"""Regression tests: writable-state location honours env override and falls
back to /tmp when the default home-based path is not creatable (serverless
read-only filesystems)."""
import tempfile
from pathlib import Path

from mirage.ledger import state_dir


def test_env_override_wins(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("MIRAGE_STATE_DIR", str(tmp_path))
    assert state_dir() == tmp_path


def test_default_home_location(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("MIRAGE_STATE_DIR", raising=False)
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    assert state_dir() == tmp_path / ".local" / "share" / "mirage"


def test_readonly_fallback_to_tmp(monkeypatch) -> None:
    monkeypatch.delenv("MIRAGE_STATE_DIR", raising=False)

    def _readonly(self, *args, **kwargs):
        raise OSError("read-only file system")

    monkeypatch.setattr(Path, "mkdir", _readonly)
    assert state_dir() == Path(tempfile.gettempdir()) / "mirage"
