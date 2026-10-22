"""Regression for Windows onefile children keeping the smoke database open."""

import importlib.util
from pathlib import Path
import subprocess
import sys
import time
from unittest.mock import Mock

import pytest

spec = importlib.util.spec_from_file_location(
    "inventory_smoke", Path(__file__).resolve().parents[2] / "packaging" / "smoke.py"
)
smoke = importlib.util.module_from_spec(spec)
spec.loader.exec_module(smoke)


def test_windows_stops_descendants_before_waiting(monkeypatch):
    monkeypatch.setattr(smoke.sys, "platform", "win32")
    proc = Mock(pid=12345)
    run = Mock(return_value=subprocess.CompletedProcess([], 0, "", ""))
    monkeypatch.setattr(smoke.subprocess, "run", run)
    smoke.stop_process_tree(proc)
    assert run.call_args.args[0] == ["taskkill", "/PID", "12345", "/T", "/F"]
    proc.terminate.assert_not_called()
    proc.kill.assert_not_called()
    proc.wait.assert_called_once_with(timeout=10)


def test_tree_shutdown_error_is_not_ignored(monkeypatch):
    monkeypatch.setattr(smoke.sys, "platform", "win32")
    proc = Mock(pid=12345)
    proc.poll.return_value = None
    monkeypatch.setattr(
        smoke.subprocess,
        "run",
        Mock(return_value=subprocess.CompletedProcess([], 1, "", "Access denied")),
    )
    with pytest.raises(RuntimeError, match="Access denied"):
        smoke.stop_process_tree(proc)


def test_cleanup_retries_sharing_violation_but_fails_persistent_lock(monkeypatch):
    violation = PermissionError("database still open")
    violation.winerror = 32
    workspace = Mock()
    workspace.cleanup.side_effect = [violation, None]
    monkeypatch.setattr(smoke.time, "sleep", lambda _: None)
    smoke.cleanup_workspace(workspace)
    assert workspace.cleanup.call_count == 2
    wrapped = NotADirectoryError("TemporaryDirectory recursive error")
    wrapped.winerror = 267
    wrapped.__context__ = violation
    workspace.cleanup.reset_mock()
    workspace.cleanup.side_effect = [wrapped, None]
    smoke.cleanup_workspace(workspace)
    assert workspace.cleanup.call_count == 2
    workspace.cleanup.reset_mock()
    workspace.cleanup.side_effect = violation
    with pytest.raises(PermissionError):
        smoke.cleanup_workspace(workspace)
    assert workspace.cleanup.call_count == 20


@pytest.mark.skipif(sys.platform != "win32", reason="Windows holds open SQLite files")
def test_actual_windows_parent_child_database_handles_are_released(tmp_path):
    database = tmp_path / "inventory.db"
    ready = tmp_path / "ready"
    child = (
        "import sqlite3,time;from pathlib import Path;"
        f"db=sqlite3.connect({str(database)!r});"
        "db.execute('CREATE TABLE marker(id INTEGER)');db.commit();"
        f"Path({str(ready)!r}).write_text('ready');time.sleep(120)"
    )
    parent = (
        "import subprocess,sys;"
        f"child=subprocess.Popen([sys.executable,'-c',{child!r}]);"
        "child.wait()"
    )
    proc = subprocess.Popen([sys.executable, "-c", parent])
    try:
        for _ in range(100):
            if ready.exists():
                break
            if proc.poll() is not None:
                pytest.fail("Test subprocess exited before opening the database")
            time.sleep(0.1)
        else:
            pytest.fail("Child did not open the database")
        with pytest.raises(PermissionError):
            database.unlink()
    finally:
        smoke.stop_process_tree(proc)
    for attempt in range(20):
        try:
            database.unlink()
            break
        except PermissionError:
            if attempt == 19:
                raise
            time.sleep(0.25)
    assert not database.exists()
