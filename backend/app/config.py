"""应用配置：冻结感知路径 + 运行期配置（环境变量优先）。"""
import os
from pathlib import Path

from .paths import (
    app_dir,
    bundle_dir,
    default_data_dir,
    default_spa_dist,
    default_static_dir,
    resource_path,
)
from .runtime_config import SEED_DEMO, ensure_config, load_runtime_config

ensure_config()
_runtime = load_runtime_config()

BASE_DIR = app_dir()
DATA_DIR = Path(os.getenv("DATA_DIR", str(default_data_dir())))
STATIC_DIR = Path(os.getenv("STATIC_DIR", str(default_static_dir())))
IMAGE_DIR = STATIC_DIR / "images"
DB_PATH = Path(os.getenv("DB_PATH", str(DATA_DIR / "inventory.db")))
DATABASE_URL = "sqlite:///" + DB_PATH.as_posix()
SPA_DIST = Path(os.getenv("SPA_DIST", str(default_spa_dist())))

SECRET_KEY = _runtime["secret_key"]
ALGORITHM = "HS256"
TOKEN_EXPIRE_MINUTES = _runtime["token_expire_minutes"]
DEFAULT_USERNAME = _runtime["default_username"]
DEFAULT_PASSWORD = _runtime["default_password"]
_cors_origins = _runtime["cors_origins"]
if isinstance(_cors_origins, str):
    CORS_ORIGINS = [o.strip() for o in _cors_origins.split(",") if o.strip()]
else:
    CORS_ORIGINS = list(_cors_origins)
MAX_UPLOAD_MB = _runtime["max_upload_mb"]
ALLOWED_IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


def ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
