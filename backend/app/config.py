"""应用配置（环境变量优先，提供开发默认值）。"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent          # backend/
DATA_DIR = Path(os.getenv("DATA_DIR", str(BASE_DIR / "data")))
STATIC_DIR = Path(os.getenv("STATIC_DIR", str(BASE_DIR / "static")))
IMAGE_DIR = STATIC_DIR / "images"
DB_PATH = Path(os.getenv("DB_PATH", str(DATA_DIR / "inventory.db")))
DATABASE_URL = f"sqlite:///{DB_PATH}"

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me-please-use-32-bytes-min")
ALGORITHM = "HS256"
TOKEN_EXPIRE_MINUTES = int(os.getenv("TOKEN_EXPIRE_MINUTES", "720"))
DEFAULT_USERNAME = os.getenv("DEFAULT_USERNAME", "admin")
DEFAULT_PASSWORD = os.getenv("DEFAULT_PASSWORD", "admin123")
CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()]
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "5"))
ALLOWED_IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


def ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
