"""冻结感知（PyInstaller）路径解析；导入本模块不产生任何目录副作用。"""
import os
import sys
import tempfile
from pathlib import Path


def is_frozen() -> bool:
    """是否运行在 PyInstaller 冻结环境中。"""
    return getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS")


def app_dir() -> Path:
    """应用所在目录：冻结时为 exe 同级目录，开发时为 backend/。"""
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def bundle_dir() -> Path:
    """只读资源根目录：冻结时为 _MEIPASS 临时目录，开发时为 backend/。"""
    if is_frozen():
        return Path(sys._MEIPASS)
    return app_dir()


def resource_path(rel: str) -> Path:
    """拼接随包分发的只读资源路径。"""
    return bundle_dir() / rel


def is_dir_writable(d: Path) -> bool:
    """尝试创建目录并写入临时文件，判断目录是否可写。"""
    path = Path(d)
    try:
        path.mkdir(parents=True, exist_ok=True)
    except (OSError, ValueError):
        return False
    if not path.is_dir():
        return False

    tmp_path = None
    try:
        fd, name = tempfile.mkstemp(dir=str(path))
        tmp_path = Path(name)
        os.close(fd)
        return True
    except OSError:
        return False
    finally:
        if tmp_path is not None:
            try:
                tmp_path.unlink()
            except OSError:
                pass


def _fallback_root() -> Path:
    """不可写时的用户数据根目录。"""
    if os.name == "nt":
        local_appdata = os.environ.get("LOCALAPPDATA")
        base = Path(local_appdata) if local_appdata else Path.home() / "AppData" / "Local"
        return base / "Inventory"
    xdg_data_home = os.environ.get("XDG_DATA_HOME")
    base = Path(xdg_data_home) if xdg_data_home else Path.home() / ".local" / "share"
    return base / "Inventory"


def default_data_dir() -> Path:
    """默认可写数据目录：优先 app_dir()/data，不可写时回退到用户数据目录。"""
    preferred = app_dir() / "data"
    if is_dir_writable(preferred):
        return preferred
    if os.name == "nt":
        return _fallback_root() / "data"
    return _fallback_root()


def default_static_dir() -> Path:
    """默认静态文件目录：优先 app_dir()/static，不可写时回退到用户数据目录。"""
    preferred = app_dir() / "static"
    if is_dir_writable(preferred):
        return preferred
    return _fallback_root() / "static"


def default_spa_dist() -> Path:
    """前端构建产物目录：冻结时在 bundle 内，开发时为仓库根 frontend/dist。"""
    if is_frozen():
        return bundle_dir() / "frontend" / "dist"
    return app_dir().parent / "frontend" / "dist"
