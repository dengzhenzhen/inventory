import os
import sys
import tempfile
from pathlib import Path
import pytest

folder = Path(tempfile.mkdtemp(prefix="inventory-tests-"))
os.environ.update(
    DATA_DIR=str(folder / "data"),
    STATIC_DIR=str(folder / "static"),
    INVENTORY_CONFIG_PATH=str(folder / "config.ini"),
    SEED_DEMO="0",
    SPA_DIST=str(folder / "spa"),
)
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.main import app
from app.database import Base, engine
from app.seed import init_db
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    with TestClient(app) as c:
        with engine.begin() as conn:
            for table in reversed(Base.metadata.sorted_tables):
                conn.execute(table.delete())
        init_db()
        yield c


def login(c, password="admin123"):
    r = c.post("/api/auth/login", json={"username": "admin", "password": password})
    assert r.status_code == 200, r.text
    c.headers["Authorization"] = "Bearer " + r.json()["data"]["access_token"]
    return r.json()["data"]


@pytest.fixture
def auth(client):
    login(client)
    assert (
        client.put(
            "/api/auth/password",
            json={"old_password": "admin123", "new_password": "newpass123"},
        ).status_code
        == 200
    )
    login(client, "newpass123")
    return client
