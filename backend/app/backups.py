"""Verified local backups and staged restart-only restoration."""

from contextlib import closing
import hashlib
import json
import os
import shutil
import sqlite3
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path, PurePosixPath
from .config import DATA_DIR, DB_PATH, IMAGE_DIR

MAX_ARCHIVE = 256 * 1024 * 1024
MAX_EXPANDED = 512 * 1024 * 1024
PENDING = DATA_DIR / "restore-pending.json"
JOURNAL = DATA_DIR / "restore-journal.json"
FAILURE = DATA_DIR / "restore-failure.txt"


def atomic_json(path, value):
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(value, f, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def db_check(path):
    with closing(sqlite3.connect(f"{path.as_uri()}?mode=ro", uri=True)) as db:
        if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ValueError("数据库损坏")
        if db.execute("PRAGMA foreign_key_check").fetchone():
            raise ValueError("数据库外键损坏")
        row = db.execute("SELECT version_num FROM alembic_version").fetchone()
        if not row or row[0] != "v2_0001":
            raise ValueError("不支持的数据库版本")
        # Do not allow a forged schema to be adopted merely by naming a revision.
        from .database import Base

        for table in Base.metadata.sorted_tables:
            cols = {r[1] for r in db.execute(f'PRAGMA table_info("{table.name}")')}
            if not {c.name for c in table.columns} <= cols:
                raise ValueError(f"备份缺少表或字段：{table.name}")


def create_backup():
    folder = DATA_DIR / "backups"
    folder.mkdir(parents=True, exist_ok=True)
    result = folder / f"inventory-{datetime.now():%Y%m%d-%H%M%S-%f}.zip"
    with tempfile.TemporaryDirectory(dir=DATA_DIR) as tmp:
        copy = Path(tmp) / "inventory.db"
        with (
            closing(sqlite3.connect(DB_PATH)) as src,
            closing(sqlite3.connect(copy)) as dst,
        ):
            src.backup(dst)
        db_check(copy.resolve())
        files = {"inventory.db": copy}
        for p in IMAGE_DIR.iterdir():
            if p.is_file() and not p.is_symlink() and not p.name.startswith("."):
                files["images/" + p.name] = p
        manifest = {
            "app_version": "2.0.0",
            "schema": "v2_0001",
            "created_at": datetime.now().isoformat(),
            "files": {},
        }
        with zipfile.ZipFile(result, "w", zipfile.ZIP_DEFLATED) as z:
            for name, p in files.items():
                data = p.read_bytes()
                z.writestr(name, data)
                manifest["files"][name] = {
                    "size": len(data),
                    "sha256": hashlib.sha256(data).hexdigest(),
                }
            z.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False))
    return result


def validate_archive(path):
    if path.stat().st_size > MAX_ARCHIVE:
        raise ValueError("备份压缩包不能超过 256MB")
    with zipfile.ZipFile(path) as z:
        infos = z.infolist()
        names = [i.filename for i in infos]
        if len(names) != len(set(names)) or len(names) > 10002:
            raise ValueError("备份文件重复或过多")
        if sum(i.file_size for i in infos) > MAX_EXPANDED:
            raise ValueError("备份展开不能超过 512MB")
        for i in infos:
            name = i.filename
            p = PurePosixPath(name)
            allowed = name in ("manifest.json", "inventory.db") or (
                len(p.parts) == 2
                and p.parts[0] == "images"
                and p.parts[1] not in ("", ".", "..")
            )
            if (
                not allowed
                or "\\" in name
                or p.is_absolute()
                or ".." in p.parts
                or i.is_dir()
                or (i.external_attr >> 16) & 0o170000 == 0o120000
            ):
                raise ValueError("备份含非法文件路径")
        manifest = json.loads(z.read("manifest.json"))
        if (
            manifest.get("schema") != "v2_0001"
            or manifest.get("app_version") != "2.0.0"
        ):
            raise ValueError("不支持的备份版本")
        if set(manifest["files"]) != set(names) - {"manifest.json"}:
            raise ValueError("文件清单不匹配")
        for name, meta in manifest["files"].items():
            data = z.read(name)
            if (
                len(data) != meta["size"]
                or hashlib.sha256(data).hexdigest() != meta["sha256"]
            ):
                raise ValueError("备份校验和不匹配")
        with tempfile.TemporaryDirectory(dir=DATA_DIR) as tmp:
            dbfile = Path(tmp) / "inventory.db"
            dbfile.write_bytes(z.read("inventory.db"))
            db_check(dbfile.resolve())
    return manifest


def maintenance():
    return PENDING.exists() or JOURNAL.exists() or FAILURE.exists()


def _apply(path):
    validate_archive(path)
    with tempfile.TemporaryDirectory(dir=DATA_DIR) as tmp:
        stage = Path(tmp)
        images = stage / "images"
        images.mkdir()
        with zipfile.ZipFile(path) as z:
            (stage / "inventory.db").write_bytes(z.read("inventory.db"))
            for n in z.namelist():
                if n.startswith("images/"):
                    (images / PurePosixPath(n).name).write_bytes(z.read(n))
        # This runs before migrations/startup requests and before the engine is opened.
        for suffix in ("-wal", "-shm"):
            Path(str(DB_PATH) + suffix).unlink(missing_ok=True)
        os.replace(stage / "inventory.db", DB_PATH)
        previous = IMAGE_DIR.with_name("images.restore-old")
        if previous.exists():
            shutil.rmtree(previous)
        if IMAGE_DIR.exists():
            os.replace(IMAGE_DIR, previous)
        shutil.copytree(images, IMAGE_DIR)
        if previous.exists():
            shutil.rmtree(previous)


def apply_pending():
    """A journal surviving a crash always rolls back before accepting another restore."""
    if JOURNAL.exists():
        journal = json.loads(JOURNAL.read_text())
        _apply(Path(journal["rollback"]))
        JOURNAL.unlink()
        PENDING.unlink(missing_ok=True)
        FAILURE.write_text(
            "恢复曾中断，已回滚。核对数据后可在网页解除维护模式。", encoding="utf-8"
        )
        return
    if not PENDING.exists():
        return
    task = json.loads(PENDING.read_text())
    atomic_json(JOURNAL, task)
    try:
        _apply(Path(task["archive"]))
        with closing(sqlite3.connect(DB_PATH)) as db:
            db.execute("DELETE FROM auth_session")
            db.commit()
        PENDING.unlink()
        FAILURE.unlink(missing_ok=True)
    except Exception as exc:
        # PENDING includes a full verified rollback archive created before maintenance.
        _apply(Path(task["rollback"]))
        PENDING.unlink()
        FAILURE.write_text(f"恢复失败，已回滚：{exc}", encoding="utf-8")
    finally:
        JOURNAL.unlink(missing_ok=True)
