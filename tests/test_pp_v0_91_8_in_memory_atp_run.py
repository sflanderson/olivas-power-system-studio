"""
tests/test_pp_v0_91_8_in_memory_atp_run.py — v0.91.8:

Hotfix: rodar ATP em projeto in-memory falhava com "ATP file
not found" porque ``self.project.file_path`` era sintético
(tipo ``<pp-export-N>``) e não correspondia a um arquivo
real no disco.

Fix: ``MainWindow._resolve_atp_run_path()``:

* Path real → usa diretamente.
* Sintético (in-memory) → serializa para
  ``%TEMP%/olivas_run/<safe_name>.atp`` e usa esse path.
* Falha de I/O → QMessageBox.warning + retorna None
  (caller aborta sem crash).

Também: ``_load_results`` agora usa
``self._last_atp_run_path`` para encontrar .pl4/.lis (que
estão ao lado do temp file, não do path sintético).

Cobertura
---------

* ``_resolve_atp_run_path`` retorna path real para
  ``file_path`` que é arquivo no disco.
* ``_resolve_atp_run_path`` serializa in-memory project
  para temp file e retorna path do temp.
* In-memory project sem ``file_path`` (None/empty) também
  é serializado.
* Falha de serialização → None + warning.
* ``_last_atp_run_path`` usado em ``_load_results``.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

PySide6 = pytest.importorskip("PySide6")
from PySide6.QtWidgets import QApplication, QMessageBox


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def _make_project(file_path: str = "<pp-export-1>"):
    """Cria um AtpProject mínimo com file_path sintético."""
    from app.core.project_model import AtpProject
    proj = AtpProject(
        file_path=file_path,
        raw_lines=[
            "BEGIN NEW DATA CASE\n",
            "/BRANCH\n",
            "BLANK BRANCH\n",
            "BLANK\n",
        ],
    )
    return proj


# ---------------------------------------------------------------------------
# _resolve_atp_run_path
# ---------------------------------------------------------------------------


class TestResolveAtpRunPath:

    def test_no_project_returns_none(self, qapp):
        from app.gui.main_window import MainWindow
        mw = MainWindow()
        try:
            result = mw._resolve_atp_run_path()
            assert result is None
        finally:
            mw.close()

    def test_real_disk_path_used_directly(self, qapp, tmp_path):
        """Quando file_path é arquivo real no disco, retorna o path."""
        from app.gui.main_window import MainWindow
        atp_file = tmp_path / "real.atp"
        atp_file.write_text("BEGIN NEW DATA CASE\n", encoding="utf-8")
        mw = MainWindow()
        try:
            mw.project = _make_project(file_path=str(atp_file))
            result = mw._resolve_atp_run_path()
            assert result is not None
            assert Path(result) == atp_file.resolve()
        finally:
            mw.close()

    def test_synthetic_path_serialized_to_temp(
        self, qapp, monkeypatch, tmp_path,
    ):
        """In-memory (synthetic) path → temp file criado."""
        from app.gui.main_window import MainWindow
        # Isola TEMP dir
        monkeypatch.setattr(
            tempfile, "gettempdir", lambda: str(tmp_path),
        )
        mw = MainWindow()
        try:
            mw.project = _make_project(file_path="<pp-export-2>")
            result = mw._resolve_atp_run_path()
            assert result is not None
            target = Path(result)
            assert target.is_file()
            # Em ~/temp/olivas_run/
            assert "olivas_run" in str(target)
            assert "pp-export-2" in target.name or "pp_export_2" in target.name
            # Conteúdo serializado
            content = target.read_text(encoding="utf-8")
            assert "BEGIN NEW DATA CASE" in content
        finally:
            mw.close()

    def test_synthetic_path_with_special_chars(
        self, qapp, monkeypatch, tmp_path,
    ):
        """Path com chars especiais é sanitizado."""
        from app.gui.main_window import MainWindow
        monkeypatch.setattr(
            tempfile, "gettempdir", lambda: str(tmp_path),
        )
        mw = MainWindow()
        try:
            mw.project = _make_project(
                file_path="<pp-export with / spaces>",
            )
            result = mw._resolve_atp_run_path()
            assert result is not None
            # Sem chars especiais no nome do arquivo
            name = Path(result).name
            for forbidden in ("<", ">", "/", " "):
                assert forbidden not in name
        finally:
            mw.close()

    def test_serialization_failure_returns_none(
        self, qapp, monkeypatch,
    ):
        """Quando serialize_project levanta, retorna None."""
        from app.gui.main_window import MainWindow

        def raising_serialize(_proj):
            raise RuntimeError("serialize broken")

        monkeypatch.setattr(
            "app.core.serializer.serialize_project",
            raising_serialize,
        )
        warned = []
        monkeypatch.setattr(
            QMessageBox, "warning",
            lambda *a, **kw: warned.append(a),
        )
        mw = MainWindow()
        try:
            mw.project = _make_project(file_path="<scratch>")
            result = mw._resolve_atp_run_path()
            assert result is None
            # Warning mostrado
            assert len(warned) == 1
        finally:
            mw.close()

    def test_disk_write_failure_returns_none(
        self, qapp, monkeypatch, tmp_path,
    ):
        """Quando write_text levanta OSError, retorna None."""
        from app.gui.main_window import MainWindow
        monkeypatch.setattr(
            tempfile, "gettempdir", lambda: str(tmp_path),
        )
        # Patch Path.write_text para levantar
        original_write = Path.write_text

        def raising_write(self, *a, **kw):
            if str(self).endswith(".atp"):
                raise OSError("disk full")
            return original_write(self, *a, **kw)

        monkeypatch.setattr(Path, "write_text", raising_write)
        warned = []
        monkeypatch.setattr(
            QMessageBox, "warning",
            lambda *a, **kw: warned.append(a),
        )
        mw = MainWindow()
        try:
            mw.project = _make_project(file_path="<scratch-2>")
            result = mw._resolve_atp_run_path()
            assert result is None
            assert len(warned) == 1
        finally:
            mw.close()


# ---------------------------------------------------------------------------
# _load_results respect _last_atp_run_path
# ---------------------------------------------------------------------------


class TestLoadResultsLastRunPath:

    def test_load_uses_last_run_path_if_set(self, qapp, tmp_path):
        """Após run real, _load_results procura .pl4/.lis ao
        lado do _last_atp_run_path (temp file)."""
        from app.gui.main_window import MainWindow
        # Cria .lis fake ao lado do temp .atp
        atp_temp = tmp_path / "scratch.atp"
        atp_temp.write_text("BEGIN", encoding="utf-8")
        lis_temp = tmp_path / "scratch.lis"
        lis_temp.write_text("listing", encoding="utf-8")

        mw = MainWindow()
        try:
            mw.project = _make_project(file_path="<pp-export-1>")
            mw._last_atp_run_path = str(atp_temp)
            # Chama _load_results — deve achar o lis
            mw._load_results()
            # results_text não está vazio
            assert mw.results_text.toPlainText() != ""
        finally:
            mw.close()

    def test_load_fallback_to_file_path_when_no_last_run(
        self, qapp, tmp_path,
    ):
        """Sem _last_atp_run_path, fallback para file_path."""
        from app.gui.main_window import MainWindow
        atp_file = tmp_path / "real.atp"
        atp_file.write_text("BEGIN", encoding="utf-8")
        mw = MainWindow()
        try:
            mw.project = _make_project(file_path=str(atp_file))
            # Não seta _last_atp_run_path
            # _load_results não crasha + acha (vazio se não há .lis)
            mw._load_results()
        finally:
            mw.close()
