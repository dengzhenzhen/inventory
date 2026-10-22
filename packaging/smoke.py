"""Smoke-test the frozen app and stop its complete process tree before cleanup."""

import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request


def stop_process_tree(proc):
    if sys.platform == "win32":
        # A onefile EXE's PID belongs to the bootloader. terminate()/kill() only
        # stop that process, leaving the Python child holding inventory.db open.
        result = subprocess.run(
            ["taskkill", "/PID", str(proc.pid), "/T", "/F"],
            capture_output=True,
            text=True,
            errors="replace",
            timeout=20,
        )
        if result.returncode and proc.poll() is None:
            raise RuntimeError(
                f"Unable to stop smoke-test process tree {proc.pid}: "
                f"{result.stdout} {result.stderr}"
            )
        proc.wait(timeout=10)
    else:
        if proc.poll() is not None:
            return
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=10)


def cleanup_workspace(workspace):
    # TerminateProcess completion can precede the last descendant releasing its
    # handles. Retry only sharing violations; persistent failures still fail CI.
    for attempt in range(20):
        try:
            workspace.cleanup()
            return
        except OSError as exc:
            # Python 3.10 TemporaryDirectory can wrap WinError 32 in WinError
            # 267 while its onerror callback mistakes a locked file for a dir.
            error = exc
            while error is not None:
                if getattr(error, "winerror", None) in (5, 32, 33):
                    break
                error = error.__cause__ or error.__context__
            if error is None or attempt == 19:
                raise
            time.sleep(0.25)


def main():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    workspace = tempfile.TemporaryDirectory(prefix="inventory-smoke-")
    root = Path(workspace.name)
    try:
        # Keep bootloader extraction files in the same disposable workspace.
        (root / "tmp").mkdir()
        env = {
            **os.environ,
            "DATA_DIR": str(root / "data"),
            "STATIC_DIR": str(root / "static"),
            "INVENTORY_CONFIG_PATH": str(root / "config.ini"),
            "INVENTORY_NO_BROWSER": "1",
            "HOST": "127.0.0.1",
            "PORT": str(port),
            "SEED_DEMO": "0",
            "TMP": str(root / "tmp"),
            "TEMP": str(root / "tmp"),
        }
        with (root / "process.log").open(
            "w+", encoding="utf-8", errors="replace"
        ) as log:
            proc = subprocess.Popen(
                [str(Path("dist/Inventory.exe").resolve())],
                env=env,
                stdout=log,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
            )
            try:
                for _ in range(90):
                    if proc.poll() is not None:
                        raise RuntimeError("EXE exited early")
                    try:
                        with urllib.request.urlopen(
                            f"http://127.0.0.1:{port}/api/health", timeout=1
                        ) as response:
                            if json.load(response)["data"]["status"] == "healthy":
                                break
                    except (OSError, ValueError):
                        time.sleep(1)
                else:
                    raise RuntimeError("EXE did not become ready")
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/", timeout=5
                ) as response:
                    assert b"<html" in response.read().lower()
                request = urllib.request.Request(
                    f"http://127.0.0.1:{port}/api/auth/login",
                    data=json.dumps(
                        {"username": "admin", "password": "admin123"}
                    ).encode(),
                    headers={"Content-Type": "application/json"},
                )
                with urllib.request.urlopen(request, timeout=5) as response:
                    assert json.load(response)["data"]["must_change_password"]
                assert (root / "data" / "inventory.db").is_file()
            except Exception:
                log.flush()
                log.seek(0)
                print(log.read())
                raise
            finally:
                stop_process_tree(proc)
    finally:
        cleanup_workspace(workspace)
    # This message must include successful shutdown and directory removal.
    print("Frozen EXE migration, login, SPA and process-tree cleanup smoke passed")


if __name__ == "__main__":
    main()
