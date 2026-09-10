import pytest
from fastapi.testclient import TestClient

import auth
import db
from app import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    """A client backed by a fresh, seeded SQLite file per test."""
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "test.db"))
    with TestClient(app) as c:  # the context manager runs the startup seed
        yield c


@pytest.fixture
def api_key_headers():
    return {"X-API-Key": auth.API_KEY}
