"""Programmatic Alembic migration, with a verified pre-upgrade SQLite backup."""

from contextlib import closing
import sqlite3
from datetime import datetime
from sqlalchemy import inspect
from alembic.config import Config
from alembic import command
from .paths import bundle_dir
from .database import engine
from .config import DB_PATH, DATA_DIR


def migrate():
    names = inspect(engine).get_table_names()
    if "user" in names and "alembic_version" not in names:
        dest = DATA_DIR / "backups" / f"pre-v2-{datetime.now():%Y%m%d-%H%M%S-%f}.db"
        dest.parent.mkdir(parents=True, exist_ok=True)
        with (
            closing(sqlite3.connect(DB_PATH)) as source,
            closing(sqlite3.connect(dest)) as target,
        ):
            source.backup(target)
            if target.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise RuntimeError("升级前备份校验失败")
    cfg = Config()
    cfg.set_main_option("script_location", str(bundle_dir() / "migrations"))
    with engine.begin() as connection:
        connection.exec_driver_sql("BEGIN IMMEDIATE")
        cfg.attributes["connection"] = connection
        command.upgrade(cfg, "head")
