"""Start the actual frozen executable against temporary runtime data."""

import os
import json
import subprocess
import tempfile
import time
import urllib.request
from pathlib import Path
import socket

with socket.socket() as sock:
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
with tempfile.TemporaryDirectory(prefix="inventory-smoke-") as tmp:
    root = Path(tmp)
    env = {
        **os.environ,
        "DATA_DIR": str(root / "data"),
        "STATIC_DIR": str(root / "static"),
        "INVENTORY_CONFIG_PATH": str(root / "config.ini"),
        "INVENTORY_NO_BROWSER": "1",
        "HOST": "127.0.0.1",
        "PORT": str(port),
        "SEED_DEMO": "0",
    }
    with (root / "process.log").open("w+") as log:
        proc = subprocess.Popen(
            [str(Path("dist/Inventory.exe").resolve())],
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
        )
        try:
            for _ in range(90):
                if proc.poll() is not None:
                    raise RuntimeError("EXE exited early")
                try:
                    with urllib.request.urlopen(
                        f"http://127.0.0.1:{port}/api/health", timeout=1
                    ) as r:
                        if json.load(r)["data"]["status"] == "healthy":
                            break
                except (OSError, ValueError):
                    time.sleep(1)
            else:
                raise RuntimeError("EXE did not become ready")
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=5) as r:
                assert b"<html" in r.read().lower()
            req = urllib.request.Request(
                f"http://127.0.0.1:{port}/api/auth/login",
                data=json.dumps({"username": "admin", "password": "admin123"}).encode(),
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=5) as r:
                assert json.load(r)["data"]["must_change_password"]
            assert (root / "data" / "inventory.db").is_file()
            print("Frozen EXE migration, login and SPA smoke passed")
        except Exception:
            log.flush()
            log.seek(0)
            print(log.read())
            raise
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
