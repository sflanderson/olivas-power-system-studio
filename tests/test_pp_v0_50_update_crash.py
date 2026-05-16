"""
tests/test_pp_v0_50_update_crash.py — v0.50: auto-update
checker + crash reporter.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Version
# ---------------------------------------------------------------------------


class TestVersion:

    def test_version_string(self):
        from app.core.version import VERSION, VERSION_TUPLE
        assert isinstance(VERSION, str)
        assert "." in VERSION
        assert isinstance(VERSION_TUPLE, tuple)
        assert all(isinstance(x, int) for x in VERSION_TUPLE)

    def test_parse_version_basic(self):
        from app.core.version import parse_version
        assert parse_version("1.2.3") == (1, 2, 3)
        assert parse_version("0.50.0") == (0, 50, 0)

    def test_parse_version_with_suffix(self):
        from app.core.version import parse_version
        assert parse_version("1.0.0-beta") == (1, 0, 0)
        assert parse_version("1.0.0+build.42") == (1, 0, 0)

    def test_is_newer_higher(self):
        from app.core.version import is_newer
        assert is_newer("1.0.0", "0.99.99") is True
        assert is_newer("0.51.0", "0.50.0") is True

    def test_is_newer_same(self):
        from app.core.version import is_newer
        assert is_newer("0.50.0", "0.50.0") is False

    def test_is_newer_lower(self):
        from app.core.version import is_newer
        assert is_newer("0.49.0", "0.50.0") is False


# ---------------------------------------------------------------------------
# Crash reporter
# ---------------------------------------------------------------------------


class TestCrashReporter:

    def test_crash_dir_creates(self, tmp_path, monkeypatch):
        from app.gui import crash_reporter
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        d = crash_reporter.crash_dir()
        assert d.is_dir()

    def test_system_info(self):
        from app.gui.crash_reporter import system_info
        info = system_info()
        assert "python_version" in info
        assert "platform" in info
        assert "atp_studio_version" in info

    def test_write_crash_dump(self, tmp_path, monkeypatch):
        from app.gui import crash_reporter
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        try:
            raise ValueError("simulated error")
        except ValueError:
            exc_type, exc_value, exc_tb = sys.exc_info()
            dump_path = crash_reporter.write_crash_dump(
                exc_type, exc_value, exc_tb,
            )
        assert dump_path.is_file()
        data = json.loads(dump_path.read_text(encoding="utf-8"))
        assert data["exception_type"] == "ValueError"
        assert "simulated error" in data["exception_message"]
        assert "traceback" in data
        assert "system" in data

    def test_install_uninstall_handler(self):
        from app.gui import crash_reporter
        original = sys.excepthook
        crash_reporter.install_crash_handler(silent=True)
        assert sys.excepthook is not original
        crash_reporter.uninstall_crash_handler()
        assert sys.excepthook is original

    def test_extra_context_recorded(self, tmp_path, monkeypatch):
        from app.gui import crash_reporter
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        try:
            raise RuntimeError("boom")
        except RuntimeError:
            exc_type, exc_value, exc_tb = sys.exc_info()
            dump_path = crash_reporter.write_crash_dump(
                exc_type, exc_value, exc_tb,
                extra_context={"project": "TEST", "bus": "B1"},
            )
        data = json.loads(dump_path.read_text(encoding="utf-8"))
        assert data["context"]["project"] == "TEST"

    def test_list_recent_crashes(self, tmp_path, monkeypatch):
        from app.gui import crash_reporter
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        # Cria 3 dumps com sleep de 1.1s para timestamps únicos
        # (filename usa YYYYMMDD_HHMMSS, precisão 1s).
        import time
        for i in range(3):
            try:
                raise ValueError(f"test {i}")
            except ValueError:
                exc_type, exc_value, exc_tb = sys.exc_info()
                crash_reporter.write_crash_dump(
                    exc_type, exc_value, exc_tb,
                )
            if i < 2:
                time.sleep(1.1)

        recent = crash_reporter.list_recent_crashes(limit=10)
        assert len(recent) >= 3


# ---------------------------------------------------------------------------
# Update checker
# ---------------------------------------------------------------------------


class TestUpdateChecker:

    def test_should_check_now_first_time(self):
        from app.gui.update_checker import should_check_now
        assert should_check_now(None) is True

    def test_should_check_now_recent(self):
        import time
        from app.gui.update_checker import should_check_now
        # 1 hora atrás → não check
        recent = time.time() - 3600
        assert should_check_now(recent) is False

    def test_should_check_now_old(self):
        import time
        from app.gui.update_checker import (
            should_check_now, UPDATE_CHECK_TTL_S,
        )
        # 25 horas atrás → check
        old = time.time() - (UPDATE_CHECK_TTL_S + 3600)
        assert should_check_now(old) is True

    def test_make_thread_returns_pair(self):
        PySide6 = pytest.importorskip("PySide6")
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance() or QApplication([])
        from app.gui.update_checker import (
            make_update_check_thread, UpdateCheckWorker,
        )
        thread, worker = make_update_check_thread(
            url="http://example.com/version.json",
        )
        assert thread is not None
        assert isinstance(worker, UpdateCheckWorker)

    def test_worker_emits_failed_on_bad_url(self):
        PySide6 = pytest.importorskip("PySide6")
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance() or QApplication([])
        from app.gui.update_checker import UpdateCheckWorker
        # URL inválida
        worker = UpdateCheckWorker(
            "http://invalid-host-zzz.local/foo.json",
            timeout_s=1.0,
        )
        emissions = []
        worker.check_failed.connect(
            lambda msg: emissions.append(msg),
        )
        worker.run()
        assert len(emissions) == 1
