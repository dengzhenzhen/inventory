import json
import io
import sqlite3
import zipfile
from pathlib import Path
import pytest
from test_business import post, pieces
from app import backups as b
from app.database import engine, SessionLocal


def test_backup_wal_restore(auth):
    from app.config import IMAGE_DIR

    (IMAGE_DIR / "test.jpg").write_bytes(b"image-original")
    post(auth)
    response = auth.get("/api/backups")
    assert response.status_code == 200
    with zipfile.ZipFile(io.BytesIO(response.content)) as z:
        assert z.read("images/test.jpg") == b"image-original"
        assert "config.ini" not in z.namelist()
    validated = auth.post(
        "/api/backups/validate",
        files={"file": ("backup.zip", response.content, "application/zip")},
    )
    assert validated.status_code == 200, validated.text
    token = validated.json()["data"]["token"]
    post(auth, code="B")
    assert pieces(auth) == 20
    restore = auth.post("/api/backups/restore", json={"token": token})
    assert restore.status_code == 200
    assert auth.get("/api/stock").status_code == 503
    (IMAGE_DIR / "test.jpg").write_bytes(b"image-changed")
    engine.dispose()
    b.apply_pending()
    assert (IMAGE_DIR / "test.jpg").read_bytes() == b"image-original"
    from app.ledger_models import AuthSession, Movement
    from sqlalchemy import func

    with SessionLocal() as db:
        assert db.query(AuthSession).count() == 0
        assert db.query(func.sum(Movement.quantity)).scalar() == 10
    assert not b.maintenance()


def test_corrupt_and_traversal_backup(auth):
    assert (
        auth.post(
            "/api/backups/validate", files={"file": ("bad.zip", b"bad")}
        ).status_code
        == 422
    )
    response = auth.get("/api/backups")
    buf = io.BytesIO(response.content)
    with zipfile.ZipFile(buf, "a") as z:
        z.writestr("../evil", "x")
    assert (
        auth.post(
            "/api/backups/validate", files={"file": ("bad.zip", buf.getvalue())}
        ).status_code
        == 422
    )
    buf = io.BytesIO(response.content)
    with zipfile.ZipFile(buf, "a") as z:
        z.writestr("inventory.db", b"corrupt")
    assert (
        auth.post(
            "/api/backups/validate", files={"file": ("bad.zip", buf.getvalue())}
        ).status_code
        == 422
    )


def test_restore_failure_rolls_back(auth, monkeypatch):
    post(auth)
    archive = b.create_backup()
    b.atomic_json(b.PENDING, {"archive": str(archive), "rollback": str(archive)})
    original = b._apply
    calls = []

    def fail_once(path):
        calls.append(path)
        if len(calls) == 1:
            raise OSError("simulated interrupted replace")
        original(path)

    monkeypatch.setattr(b, "_apply", fail_once)
    engine.dispose()
    b.apply_pending()
    assert len(calls) == 2
    assert b.FAILURE.exists()
    assert not b.PENDING.exists()
    b.FAILURE.unlink()


def test_interrupted_restore_journal_rolls_back(auth):
    post(auth)
    archive = b.create_backup()
    post(auth, code="B")
    b.atomic_json(b.JOURNAL, {"archive": str(archive), "rollback": str(archive)})
    engine.dispose()
    b.apply_pending()
    assert b.FAILURE.exists()
    assert not b.JOURNAL.exists()
    assert pieces(auth) == 10 if not b.maintenance() else True
    b.FAILURE.unlink()
    assert pieces(auth) == 10


def legacy_database(path, bad_date=False):
    with sqlite3.connect(path) as db:
        db.executescript("""
CREATE TABLE category(id INTEGER PRIMARY KEY,name VARCHAR(50) NOT NULL UNIQUE,sort_order INTEGER);
CREATE TABLE supplier(id INTEGER PRIMARY KEY,name VARCHAR(100) NOT NULL UNIQUE,contact TEXT,phone TEXT,remark TEXT);
CREATE TABLE size(id INTEGER PRIMARY KEY,name VARCHAR(20) NOT NULL UNIQUE,sort_order INTEGER);
CREATE TABLE product(id INTEGER PRIMARY KEY,style_code VARCHAR(64) NOT NULL UNIQUE,name TEXT,category_id INTEGER,supplier_id INTEGER,retail_price FLOAT,main_image TEXT,remark TEXT,created_at DATETIME,updated_at DATETIME);
CREATE TABLE user(id INTEGER PRIMARY KEY,username VARCHAR(50) NOT NULL UNIQUE,password_hash TEXT NOT NULL,created_at DATETIME);
CREATE TABLE purchase(id INTEGER PRIMARY KEY,product_id INTEGER NOT NULL,style_code TEXT,size_id INTEGER,size_text TEXT,quantity INTEGER,cost_price FLOAT,purchase_date TEXT,supplier_id INTEGER,remark TEXT,created_at DATETIME);
CREATE TABLE sale(id INTEGER PRIMARY KEY,product_id INTEGER NOT NULL,style_code TEXT,size_id INTEGER,size_text TEXT,quantity INTEGER,unit_price FLOAT,sale_date TEXT,remark TEXT,created_at DATETIME);
INSERT INTO product VALUES(1,'NEW','商品',NULL,NULL,19.99,NULL,NULL,'2026-01-01 00:00:00','2026-01-01 00:00:00');
INSERT INTO purchase VALUES(1,1,'OLD',NULL,NULL,10,0.10,'2026-01-01',NULL,'旧单','2026-01-01 00:00:00');
INSERT INTO sale VALUES(1,1,'OLD',NULL,NULL,3,0.30,'2026-01-02',NULL,'2026-01-02 00:00:00');
""")
        if bad_date:
            db.execute("UPDATE purchase SET purchase_date='bad'")


def migration_for(path):
    from sqlalchemy import create_engine
    from alembic.config import Config
    from alembic import command

    e = create_engine("sqlite:///" + str(path))
    cfg = Config()
    cfg.set_main_option(
        "script_location", str(Path(__file__).resolve().parents[1] / "migrations")
    )
    try:
        with e.begin() as conn:
            conn.exec_driver_sql("BEGIN IMMEDIATE")
            cfg.attributes["connection"] = conn
            command.upgrade(cfg, "head")
    finally:
        e.dispose()


def test_legacy_migration_is_repeatable(tmp_path):
    path = tmp_path / "legacy.db"
    legacy_database(path)
    migration_for(path)
    migration_for(path)
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT SUM(quantity) FROM movement").fetchone()[0] == 7
        assert db.execute("SELECT COUNT(*) FROM document").fetchone()[0] == 2
        assert db.execute("SELECT retail_cents FROM product").fetchone()[0] == 1999
        assert (
            db.execute(
                "SELECT cost_micro FROM document_line WHERE quantity<0"
            ).fetchone()[0]
            == 100000
        )
        assert db.execute("SELECT name FROM size").fetchone()[0] == "未指定"


def test_failed_migration_rolls_back(tmp_path):
    path = tmp_path / "invalid.db"
    legacy_database(path, bad_date=True)
    with pytest.raises(RuntimeError, match="日期无效"):
        migration_for(path)
    with sqlite3.connect(path) as db:
        assert "retail_cents" not in {
            r[1] for r in db.execute("PRAGMA table_info(product)")
        }
        assert not db.execute(
            "SELECT name FROM sqlite_master WHERE name='document'"
        ).fetchone()
        db.execute("UPDATE purchase SET purchase_date='2026-01-01'")
    migration_for(path)


def test_automatic_preupgrade_backup(tmp_path, monkeypatch):
    from sqlalchemy import create_engine
    from app import upgrades

    path = tmp_path / "old.db"
    legacy_database(path)
    e = create_engine("sqlite:///" + str(path))
    monkeypatch.setattr(upgrades, "engine", e)
    monkeypatch.setattr(upgrades, "DB_PATH", path)
    monkeypatch.setattr(upgrades, "DATA_DIR", tmp_path)
    try:
        upgrades.migrate()
    finally:
        e.dispose()
    backups = list((tmp_path / "backups").glob("pre-v2-*.db"))
    assert len(backups) == 1
    with sqlite3.connect(backups[0]) as db:
        assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert "retail_cents" not in {
            r[1] for r in db.execute("PRAGMA table_info(product)")
        }


@pytest.mark.parametrize("version, expected", [("2.0.0", 200), ("2.1.0", 422)])
def test_backup_version_compatibility(auth, version, expected):
    response = auth.get("/api/backups")
    output = io.BytesIO()
    with (
        zipfile.ZipFile(io.BytesIO(response.content)) as original,
        zipfile.ZipFile(output, "w") as patched,
    ):
        for name in original.namelist():
            data = original.read(name)
            if name == "manifest.json":
                manifest = json.loads(data)
                manifest["app_version"] = version
                data = json.dumps(manifest).encode()
            patched.writestr(name, data)
    result = auth.post(
        "/api/backups/validate", files={"file": ("backup.zip", output.getvalue())}
    )
    assert result.status_code == expected
