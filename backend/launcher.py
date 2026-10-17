"""冻结（PyInstaller）与开发环境共用的启动入口。

职责：
1. 引导 ``config.ini``（冻结环境首次运行生成随机密钥）。
2. 检测已有实例（HTTP 健康探测 + Windows 命名互斥量）。
3. 绑定配置的端口，端口被外部程序占用时明确报错，绝不自动换端口。
4. 用 uvicorn 单进程单 worker 运行 ``app.main:app``。
5. 服务就绪后再打开浏览器（``INVENTORY_NO_BROWSER=1`` 可禁用）。

注意：本模块导入时不加载 ``app.main``，配置引导完成后才导入应用。
"""
import errno
import json
import multiprocessing
import os
import socket
import sys
import threading
import time
import traceback
import urllib.request
import webbrowser

# 直接执行 ``python backend/launcher.py`` 时保证 ``app`` 包可导入。
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

from app.runtime_config import ensure_config, load_runtime_config  # noqa: E402

_HEALTH_PATH = "/api/health"
_DEFAULT_HOST = "0.0.0.0"
_DEFAULT_PORT = 8000
_MUTEX_NAME = "Local\\InventoryApp"
_ERROR_ALREADY_EXISTS = 183
_WINDOWS_PORT_IN_USE = 10048

# 互斥量需在进程生命周期内保持引用，不能关闭。
_MUTEX_HANDLE = None


def _reconfigure_standard_streams() -> None:
    """尽力把控制台输出切到 errors="replace"，避免重定向到非 UTF-8 控制台时报错。"""
    for stream in (sys.stdout, sys.stderr):
        try:
            if stream is not None and hasattr(stream, "reconfigure"):
                stream.reconfigure(errors="replace")
        except Exception:  # noqa: BLE001 - 编码重配置失败不应影响启动
            pass


def _browser_suppressed() -> bool:
    return os.getenv("INVENTORY_NO_BROWSER", "") == "1"


def _open_browser(port: int) -> None:
    """在服务就绪后打开默认浏览器；失败不影响服务。"""
    if _browser_suppressed():
        return
    try:
        webbrowser.open(f"http://localhost:{port}/", new=2)
    except Exception as exc:  # noqa: BLE001 - 浏览器打开失败不应终止服务
        print(f"[WARN] 无法自动打开浏览器：{exc}", file=sys.stderr)


def _is_healthy(port: int, timeout: float = 1.0) -> bool:
    """探测本机健康接口，必须同时满足 code==0 与 data.status=="healthy"。"""
    url = f"http://127.0.0.1:{port}{_HEALTH_PATH}"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            if getattr(response, "status", 200) != 200:
                return False
            payload = json.loads(response.read().decode("utf-8"))
    except Exception:  # noqa: BLE001 - 连接失败/超时/JSON 损坏都视为未就绪
        return False

    data = payload.get("data")
    return (
        payload.get("code") == 0
        and isinstance(data, dict)
        and data.get("status") == "healthy"
    )


def _wait_until_healthy(port: int, timeout: float) -> bool:
    """在超时时间内轮询健康接口。"""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if _is_healthy(port):
            return True
        time.sleep(0.25)
    return False


def _acquire_single_instance_mutex() -> bool:
    """Windows 命名互斥量；返回 True 表示已有实例存在。

    非 Windows 平台直接返回 False。新建的互斥量句柄保存在模块级变量中，
    直到进程退出才由系统释放。
    """
    global _MUTEX_HANDLE
    if sys.platform != "win32":
        return False

    try:
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32")
        kernel32.CreateMutexW.argtypes = [
            wintypes.LPVOID,
            wintypes.BOOL,
            wintypes.LPCWSTR,
        ]
        kernel32.CreateMutexW.restype = wintypes.HANDLE

        kernel32.SetLastError(0)
        handle = kernel32.CreateMutexW(None, False, _MUTEX_NAME)
        last_error = kernel32.GetLastError()

        if not handle:
            print(
                f"[WARN] 创建单实例互斥量失败（GetLastError={last_error}），继续启动。",
                file=sys.stderr,
            )
            return False

        _MUTEX_HANDLE = handle
        return last_error == _ERROR_ALREADY_EXISTS
    except Exception as exc:  # noqa: BLE001 - 互斥量不可用时退化为健康探测
        print(f"[WARN] Windows 单实例检测失败：{exc}", file=sys.stderr)
        return False


def _bind_socket(host: str, port: int) -> socket.socket:
    """绑定监听端口；POSIX 上允许重启后复用 TIME_WAIT，Windows 上不设置。"""
    family = socket.AF_INET6 if ":" in host else socket.AF_INET
    sock = socket.socket(family, socket.SOCK_STREAM)
    if sys.platform != "win32":
        # Windows 的 SO_REUSEADDR 会允许抢占已被占用的端口，必须禁用。
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((host, port))
    return sock


def _is_port_in_use_error(exc: OSError) -> bool:
    if exc.errno == errno.EADDRINUSE:
        return True
    return getattr(exc, "winerror", None) == _WINDOWS_PORT_IN_USE


def _start_browser_opener(server, port: int) -> None:
    """后台守护线程轮询 server.started，就绪后再打开浏览器。"""
    if _browser_suppressed():
        return

    def _worker() -> None:
        while not getattr(server, "started", False):
            if getattr(server, "should_exit", False):
                return
            time.sleep(0.1)
        _open_browser(port)

    threading.Thread(target=_worker, name="browser-opener", daemon=True).start()


def _startup_failure(exc: BaseException) -> int:
    print("服务启动失败：", file=sys.stderr)
    traceback.print_exception(type(exc), exc, exc.__traceback__)
    if getattr(sys, "frozen", False):
        try:
            input("按回车退出...")
        except Exception:  # noqa: BLE001 - 无控制台时直接退出
            pass
    return 1


def main() -> int:
    _reconfigure_standard_streams()

    # 1. 先引导运行期配置，读取 host/port。
    ensure_config()
    runtime = load_runtime_config()
    host = str(runtime.get("host") or _DEFAULT_HOST)
    try:
        port = int(runtime.get("port", _DEFAULT_PORT))
    except (TypeError, ValueError):
        port = _DEFAULT_PORT

    try:
        # 2. 健康探测：已有本服务在运行则直接复用。
        if _is_healthy(port):
            print(f"服务已在运行：http://localhost:{port}/")
            _open_browser(port)
            return 0

        # 3. Windows 单实例：已有实例（可能尚在启动中）时等待就绪，绝不二次启动。
        if _acquire_single_instance_mutex():
            print(f"检测到已有实例，正在等待服务就绪：http://localhost:{port}/")
            if not _wait_until_healthy(port, timeout=20.0):
                print(
                    "检测到已有实例，但服务在 20 秒内未就绪，请检查该实例的控制台日志",
                    file=sys.stderr,
                )
                return 1
            print(f"服务已在运行：http://localhost:{port}/")
            _open_browser(port)
            return 0

        # 4. 绑定端口；被占用时区分本服务与外部程序。
        try:
            sock = _bind_socket(host, port)
        except OSError as exc:
            if _is_port_in_use_error(exc) and _wait_until_healthy(port, timeout=2.0):
                print(f"服务已在运行：http://localhost:{port}/")
                _open_browser(port)
                return 0
            if _is_port_in_use_error(exc):
                print(
                    f"端口 {port} 被其他程序占用，请修改 config.ini 或关闭占用程序",
                    file=sys.stderr,
                )
                return 1
            raise

        try:
            # 5. 配置引导完成后才导入应用。
            import uvicorn

            from app.main import app

            config = uvicorn.Config(
                app,
                host=host,
                port=port,
                log_level="info",
                loop="asyncio",
                http="h11",
                reload=False,
                workers=1,
                access_log=True,
            )
            server = uvicorn.Server(config)
            _start_browser_opener(server, port)
            server.run(sockets=[sock])
            return 0
        finally:
            try:
                sock.close()
            except OSError:
                pass
    except KeyboardInterrupt:
        return 0
    except BaseException as exc:  # noqa: BLE001 - 顶层错误需打印并保留窗口
        return _startup_failure(exc)


if __name__ == "__main__":
    multiprocessing.freeze_support()
    sys.exit(main())
