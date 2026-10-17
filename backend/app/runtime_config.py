"""运行期配置：``config.ini`` 的原子引导与读取。

配置文件仅用于打包后的可执行程序；开发模式默认只读取环境变量与内置默认值。
本模块导入时不生成任何文件，只有显式调用 :func:`ensure_config` 才会写入配置。
"""
import configparser
import os
import secrets
import sys
import tempfile
from pathlib import Path

from .paths import app_dir, default_data_dir, is_dir_writable, is_frozen

CONFIG_PATH = Path(os.getenv("INVENTORY_CONFIG_PATH", str((app_dir() if is_dir_writable(app_dir()) else default_data_dir().parent) / "config.ini")))

_DEV_SECRET_KEY = "dev-secret-change-me-please-use-32-bytes-min"

_DEFAULT_RAW = {
    "host": "0.0.0.0",
    "port": "8000",
    "secret_key": _DEV_SECRET_KEY,
    "default_username": "admin",
    "default_password": "admin123",
    "token_expire_minutes": "720",
    "cors_origins": "*",
    "max_upload_mb": "5",
}

_ENV_NAMES = {
    "host": "HOST",
    "port": "PORT",
    "secret_key": "SECRET_KEY",
    "default_username": "DEFAULT_USERNAME",
    "default_password": "DEFAULT_PASSWORD",
    "token_expire_minutes": "TOKEN_EXPIRE_MINUTES",
    "cors_origins": "CORS_ORIGINS",
    "max_upload_mb": "MAX_UPLOAD_MB",
}

_INT_KEYS = ("port", "token_expire_minutes", "max_upload_mb")


def _warn(message: str) -> None:
    print(f"[runtime_config] {message}", file=sys.stderr)


def _default_config_text() -> str:
    """生成带随机密钥的默认配置文本（仅用于首次创建）。"""
    values = dict(_DEFAULT_RAW)
    values["secret_key"] = secrets.token_urlsafe(48)
    lines = ["[app]"]
    for key in _DEFAULT_RAW:
        lines.append(f"{key} = {values[key]}")
    return "\n".join(lines) + "\n"


def _write_all(fd: int, data: bytes) -> None:
    view = memoryview(data)
    while view:
        written = os.write(fd, view)
        view = view[written:]


def _publish_config(tmp_path: Path) -> None:
    """把临时文件发布为 ``CONFIG_PATH``，且绝不覆盖已存在的配置。

    优先使用硬链接（原子 create-if-not-exists）；不支持硬链接的文件系统
    退化为 ``os.replace``，但替换前会重新确认目标仍然不存在。
    """
    try:
        os.link(str(tmp_path), str(CONFIG_PATH))
        return
    except FileExistsError:
        return
    except OSError:
        pass

    if CONFIG_PATH.exists():
        return
    try:
        os.replace(str(tmp_path), str(CONFIG_PATH))
    except FileExistsError:
        return


def ensure_config() -> None:
    """在冻结环境（或强制）下原子创建 ``config.ini``。

    文件已存在时立即返回，绝不会覆盖已有配置。首次创建先在目标目录写入
    独占临时文件，``fsync`` 后再通过硬链接（或带存在性复查的 ``replace``）
    原子发布；并发首启时只有一个进程能成功发布。
    """
    if not (is_frozen() or os.getenv("INVENTORY_FORCE_CONFIG", "0") == "1"):
        return
    if CONFIG_PATH.exists():
        return

    try:
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        _warn(f"无法创建配置目录 {CONFIG_PATH.parent}: {exc}")
        return

    tmp_path = None
    try:
        fd, tmp_name = tempfile.mkstemp(
            prefix=".config-", suffix=".tmp", dir=str(CONFIG_PATH.parent)
        )
        tmp_path = Path(tmp_name)
        try:
            _write_all(fd, _default_config_text().encode("utf-8"))
            os.fsync(fd)
        finally:
            os.close(fd)
        _publish_config(tmp_path)
    except OSError as exc:
        _warn(f"写入配置文件 {CONFIG_PATH} 失败: {exc}")
    finally:
        if tmp_path is not None:
            try:
                tmp_path.unlink()
            except FileNotFoundError:
                pass
            except OSError:
                pass


def _read_file_values() -> dict:
    """读取配置文件中的 ``[app]`` 值；损坏时告警并返回空字典。"""
    if not CONFIG_PATH.exists():
        return {}

    parser = configparser.ConfigParser(interpolation=None)
    try:
        with CONFIG_PATH.open("r", encoding="utf-8") as fh:
            parser.read_file(fh)
    except (configparser.Error, OSError, UnicodeError) as exc:
        _warn(f"配置文件 {CONFIG_PATH} 无法解析（将使用默认值且不会修改文件）: {exc}")
        return {}

    if not parser.has_section("app"):
        _warn(f"配置文件 {CONFIG_PATH} 缺少 [app] 段（将使用默认值且不会修改文件）")
        return {}
    return {key: parser.get("app", key) for key in _DEFAULT_RAW if parser.has_option("app", key)}


def _to_int(key: str, raw: str) -> int:
    try:
        return int(str(raw).strip())
    except (TypeError, ValueError):
        _warn(f"配置项 {key}={raw!r} 不是合法整数，回退默认值 {_DEFAULT_RAW[key]}")
        return int(_DEFAULT_RAW[key])


def load_runtime_config() -> dict:
    """返回完整运行配置；环境变量优先于文件，缺失/损坏时回退默认值。"""
    values = dict(_DEFAULT_RAW)
    values.update(_read_file_values())

    for key, env_name in _ENV_NAMES.items():
        raw = os.getenv(env_name)
        if raw is not None:
            values[key] = raw

    for key in _INT_KEYS:
        values[key] = _to_int(key, values[key])

    values["cors_origins"] = [o.strip() for o in str(values["cors_origins"]).split(",") if o.strip()]
    for key in ("host", "secret_key", "default_username", "default_password"):
        values[key] = str(values[key])

    return values


SEED_DEMO = os.getenv("SEED_DEMO", "0" if is_frozen() else "1").lower() in ("1", "true", "yes", "on")
