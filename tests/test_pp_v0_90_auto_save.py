"""
tests/test_pp_v0_90_auto_save.py — v0.90: auto-save +
crash recovery.

Cobertura
---------

* PpEditor tracking: ``current_sch_path`` + ``is_dirty()``.
* ``autosave_path_for(p)`` retorna ``p + .autosave``.
* ``remove_autosave_for`` remove arquivo (silencioso se ausente).
* ``is_autosave_newer_than_original`` compara mtimes.
* ``find_untitled_recoveries`` lista ``~/.olivas/recovery/``.
* ``cleanup_old_recoveries`` apaga > N dias.
* ``AutoSaveManager``:
  - skip se editor.is_dirty() == False
  - save em ``<path>.autosave`` quando path conhecido
  - save em recovery dir quando untitled (cria + reusa path)
  - ``set_interval_seconds`` clampa a 5s mín
  - ``trigger_now`` força save imediato
* Save manual (``save_to_sch``) limpa autosave correspondente.
* New project limpa ``current_sch_path``.
"""

from __future__ import annotations

import os
import time
from pathlib import Path

import pytest

PySide6 = pytest.importorskip("PySide6")
from PySide6.QtCore import QPointF
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture
def isolated_recovery(monkeypatch, tmp_path):
    """Isola ~/.olivas/recovery/ para um tmpdir."""
    rec = tmp_path / ".olivas" / "recovery"
    monkeypatch.setattr(
        "app.gui.auto_save._RECOVERY_DIR", rec,
    )
    return rec


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------


class TestAutosavePathHelpers:

    def test_autosave_path_appends_suffix(self):
        from app.gui.auto_save import autosave_path_for
        p = autosave_path_for("/tmp/x.sch")
        assert str(p).endswith(".sch.autosave")

    def test_remove_autosave_silent_if_missing(self, tmp_path):
        from app.gui.auto_save import remove_autosave_for
        # Não levanta
        remove_autosave_for(str(tmp_path / "nonexistent.sch"))

    def test_remove_autosave_deletes_file(self, tmp_path):
        from app.gui.auto_save import (
            autosave_path_for, remove_autosave_for,
        )
        sch = tmp_path / "x.sch"
        autosave = autosave_path_for(str(sch))
        autosave.write_text("dummy", encoding="utf-8")
        assert autosave.is_file()
        remove_autosave_for(str(sch))
        assert not autosave.is_file()


# ---------------------------------------------------------------------------
# is_autosave_newer_than_original
# ---------------------------------------------------------------------------


class TestAutosaveAge:

    def test_newer_when_no_original(self, tmp_path):
        from app.gui.auto_save import (
            autosave_path_for, is_autosave_newer_than_original,
        )
        sch = tmp_path / "missing.sch"
        autosave = autosave_path_for(str(sch))
        autosave.write_text("dummy", encoding="utf-8")
        assert is_autosave_newer_than_original(
            str(autosave), str(sch),
        )

    def test_not_newer_when_no_autosave(self, tmp_path):
        from app.gui.auto_save import (
            autosave_path_for, is_autosave_newer_than_original,
        )
        sch = tmp_path / "x.sch"
        sch.write_text("dummy", encoding="utf-8")
        autosave = autosave_path_for(str(sch))
        assert not is_autosave_newer_than_original(
            str(autosave), str(sch),
        )

    def test_newer_when_autosave_more_recent(self, tmp_path):
        from app.gui.auto_save import (
            autosave_path_for, is_autosave_newer_than_original,
        )
        sch = tmp_path / "x.sch"
        sch.write_text("v1", encoding="utf-8")
        # Touch para garantir mtime mais antigo
        old_t = time.time() - 100
        os.utime(sch, (old_t, old_t))
        autosave = autosave_path_for(str(sch))
        autosave.write_text("v2", encoding="utf-8")
        assert is_autosave_newer_than_original(
            str(autosave), str(sch),
        )


# ---------------------------------------------------------------------------
# Untitled recoveries
# ---------------------------------------------------------------------------


class TestUntitledRecoveries:

    def test_find_returns_empty_if_dir_absent(self, isolated_recovery):
        from app.gui.auto_save import find_untitled_recoveries
        assert find_untitled_recoveries() == []

    def test_find_lists_files(self, isolated_recovery):
        from app.gui.auto_save import find_untitled_recoveries
        isolated_recovery.mkdir(parents=True, exist_ok=True)
        f1 = isolated_recovery / "recovery_1.sch"
        f1.write_text("a", encoding="utf-8")
        f2 = isolated_recovery / "recovery_2.sch"
        f2.write_text("b", encoding="utf-8")
        # Garante mtime distinto
        os.utime(f1, (time.time() - 100, time.time() - 100))
        result = find_untitled_recoveries()
        assert len(result) == 2
        # Mais recente primeiro
        assert result[0] == f2

    def test_cleanup_old_recoveries_removes_old_files(
        self, isolated_recovery,
    ):
        from app.gui.auto_save import cleanup_old_recoveries
        isolated_recovery.mkdir(parents=True, exist_ok=True)
        new_f = isolated_recovery / "new.sch"
        new_f.write_text("a", encoding="utf-8")
        old_f = isolated_recovery / "old.sch"
        old_f.write_text("b", encoding="utf-8")
        # Old: mais de 31 dias atrás
        old_t = time.time() - 31 * 86400
        os.utime(old_f, (old_t, old_t))
        n = cleanup_old_recoveries(max_age_days=30)
        assert n == 1
        assert new_f.is_file()
        assert not old_f.is_file()


# ---------------------------------------------------------------------------
# PpEditor tracking
# ---------------------------------------------------------------------------


class TestPpEditorTracking:

    def test_initial_state(self, qapp):
        from app.gui.schematic_pp.editor import PpEditor
        ed = PpEditor()
        assert ed.current_sch_path is None
        assert ed.is_dirty() is False

    def test_load_sets_path_and_clean(self, qapp, tmp_path):
        from app.gui.schematic_pp.editor import PpEditor
        from app.preprocessor.templates import build_simple_13_8kV
        from app.preprocessor.qucs_sch_serializer import (
            serialize_sch_file,
        )

        sch = tmp_path / "x.sch"
        serialize_sch_file(build_simple_13_8kV(), str(sch))
        ed = PpEditor()
        ed.load_from_sch(str(sch))
        assert ed.current_sch_path == str(sch)
        assert ed.is_dirty() is False

    def test_save_sets_path_and_clean(self, qapp, tmp_path):
        from app.gui.schematic_pp.editor import PpEditor
        ed = PpEditor()
        ed.add_component_by_type("R")
        # Antes de salvar: dirty
        assert ed.is_dirty() is True
        sch = tmp_path / "y.sch"
        ed.save_to_sch(str(sch))
        assert ed.current_sch_path == str(sch)
        assert ed.is_dirty() is False

    def test_new_project_clears_path(self, qapp, tmp_path):
        from app.gui.schematic_pp.editor import PpEditor
        ed = PpEditor()
        ed.add_component_by_type("R")
        sch = tmp_path / "z.sch"
        ed.save_to_sch(str(sch))
        assert ed.current_sch_path == str(sch)
        ed.new_project()
        assert ed.current_sch_path is None

    def test_save_removes_autosave(self, qapp, tmp_path):
        """Save manual remove o autosave correspondente."""
        from app.gui.auto_save import autosave_path_for
        from app.gui.schematic_pp.editor import PpEditor
        ed = PpEditor()
        ed.add_component_by_type("R")
        sch = tmp_path / "x.sch"
        # Cria autosave fake
        autosave = autosave_path_for(str(sch))
        autosave.write_text("dummy", encoding="utf-8")
        assert autosave.is_file()
        ed.save_to_sch(str(sch))
        # Save manual deve ter removido o autosave
        assert not autosave.is_file()


# ---------------------------------------------------------------------------
# AutoSaveManager
# ---------------------------------------------------------------------------


class TestAutoSaveManager:

    def test_initial_state(self, qapp):
        from app.gui.auto_save import AutoSaveManager
        from app.gui.schematic_pp.editor import PpEditor
        ed = PpEditor()
        mgr = AutoSaveManager(editor=ed, interval_seconds=60)
        assert not mgr.is_running()
        assert mgr.interval_seconds == 60

    def test_start_stop(self, qapp):
        from app.gui.auto_save import AutoSaveManager
        from app.gui.schematic_pp.editor import PpEditor
        ed = PpEditor()
        mgr = AutoSaveManager(editor=ed, interval_seconds=60)
        mgr.start()
        assert mgr.is_running()
        mgr.stop()
        assert not mgr.is_running()

    def test_set_interval_clamps_to_min_5s(self, qapp):
        from app.gui.auto_save import AutoSaveManager
        from app.gui.schematic_pp.editor import PpEditor
        ed = PpEditor()
        mgr = AutoSaveManager(editor=ed, interval_seconds=60)
        mgr.set_interval_seconds(1)
        assert mgr.interval_seconds == 5

    def test_trigger_skips_if_clean(self, qapp):
        """Editor sem mudanças → trigger_now retorna None."""
        from app.gui.auto_save import AutoSaveManager
        from app.gui.schematic_pp.editor import PpEditor
        ed = PpEditor()
        mgr = AutoSaveManager(editor=ed, interval_seconds=60)
        result = mgr.trigger_now()
        assert result is None

    def test_trigger_saves_to_autosave_path(self, qapp, tmp_path):
        from app.gui.auto_save import AutoSaveManager, autosave_path_for
        from app.gui.schematic_pp.editor import PpEditor
        ed = PpEditor()
        # Salva primeiro para ter um path conhecido (e clean)
        sch = tmp_path / "x.sch"
        ed.save_to_sch(str(sch))
        # Modifica para virar dirty
        ed.add_component_by_type("R")
        assert ed.is_dirty()
        mgr = AutoSaveManager(editor=ed, interval_seconds=60)
        target = mgr.trigger_now()
        assert target is not None
        assert target == str(autosave_path_for(str(sch)))
        assert Path(target).is_file()

    def test_trigger_untitled_uses_recovery_dir(
        self, qapp, isolated_recovery,
    ):
        """Editor sem path → autosave em ~/.olivas/recovery/."""
        from app.gui.auto_save import AutoSaveManager
        from app.gui.schematic_pp.editor import PpEditor
        ed = PpEditor()
        ed.add_component_by_type("R")
        mgr = AutoSaveManager(editor=ed, interval_seconds=60)
        target = mgr.trigger_now()
        assert target is not None
        assert isolated_recovery in Path(target).parents
        assert Path(target).is_file()

    def test_untitled_path_reused_across_ticks(
        self, qapp, isolated_recovery,
    ):
        """Mesmo untitled_path em 2 ticks consecutivos."""
        from app.gui.auto_save import AutoSaveManager
        from app.gui.schematic_pp.editor import PpEditor
        ed = PpEditor()
        ed.add_component_by_type("R")
        mgr = AutoSaveManager(editor=ed, interval_seconds=60)
        t1 = mgr.trigger_now()
        # Adiciona mais para virar dirty de novo (já está dirty —
        # add_component_by_type não setClean())
        ed.add_component_by_type("L")
        t2 = mgr.trigger_now()
        assert t1 == t2

    def test_saved_signal_emitted(self, qapp, tmp_path):
        from app.gui.auto_save import AutoSaveManager
        from app.gui.schematic_pp.editor import PpEditor
        ed = PpEditor()
        sch = tmp_path / "x.sch"
        ed.save_to_sch(str(sch))
        ed.add_component_by_type("R")
        mgr = AutoSaveManager(editor=ed, interval_seconds=60)
        captured: list[str] = []
        mgr.saved.connect(captured.append)
        mgr.trigger_now()
        assert len(captured) == 1


# ---------------------------------------------------------------------------
# MainWindow recovery integration
# ---------------------------------------------------------------------------


class TestMainWindowRecovery:

    def test_offer_recovery_no_files_returns_false(
        self, qapp, isolated_recovery,
    ):
        from app.gui.main_window import MainWindow
        mw = MainWindow()
        try:
            result = mw.offer_recovery_if_available()
            assert result is False
        finally:
            mw.close()

    def test_offer_recovery_with_yes_loads_project(
        self, qapp, isolated_recovery, monkeypatch,
    ):
        from PySide6.QtWidgets import QMessageBox
        from app.gui.main_window import MainWindow
        from app.preprocessor.templates import build_simple_13_8kV
        from app.preprocessor.qucs_sch_serializer import (
            serialize_sch_file,
        )

        # Cria recovery file untitled
        isolated_recovery.mkdir(parents=True, exist_ok=True)
        rec_file = isolated_recovery / "recovery_999.sch"
        serialize_sch_file(build_simple_13_8kV(), str(rec_file))

        mw = MainWindow()
        try:
            # Mock Yes
            monkeypatch.setattr(
                QMessageBox, "question",
                lambda *a, **kw: QMessageBox.Yes,
            )
            result = mw.offer_recovery_if_available()
            assert result is True
            # Componentes carregados (v0.91.12: 4 components após
            # R_LOAD ser adicionado em build_simple_13_8kV).
            assert len(mw.schematic_pp.scene.component_items()) == 4
            # Arquivo de recovery removido
            assert not rec_file.is_file()
        finally:
            mw.close()

    def test_offer_recovery_with_no_discards(
        self, qapp, isolated_recovery, monkeypatch,
    ):
        from PySide6.QtWidgets import QMessageBox
        from app.gui.main_window import MainWindow

        isolated_recovery.mkdir(parents=True, exist_ok=True)
        rec_file = isolated_recovery / "recovery_888.sch"
        rec_file.write_text("dummy", encoding="utf-8")

        mw = MainWindow()
        try:
            monkeypatch.setattr(
                QMessageBox, "question",
                lambda *a, **kw: QMessageBox.No,
            )
            result = mw.offer_recovery_if_available()
            assert result is False
            # Arquivo removido (descartado)
            assert not rec_file.is_file()
        finally:
            mw.close()

    def test_offer_recovery_with_ignore_keeps(
        self, qapp, isolated_recovery, monkeypatch,
    ):
        from PySide6.QtWidgets import QMessageBox
        from app.gui.main_window import MainWindow

        isolated_recovery.mkdir(parents=True, exist_ok=True)
        rec_file = isolated_recovery / "recovery_777.sch"
        rec_file.write_text("dummy", encoding="utf-8")

        mw = MainWindow()
        try:
            monkeypatch.setattr(
                QMessageBox, "question",
                lambda *a, **kw: QMessageBox.Ignore,
            )
            result = mw.offer_recovery_if_available()
            assert result is False
            # Arquivo MANTIDO (Ignore = pra próxima vez)
            assert rec_file.is_file()
        finally:
            mw.close()


# ---------------------------------------------------------------------------
# AutoSave manager attached on MainWindow
# ---------------------------------------------------------------------------


class TestMainWindowAutoSave:

    def test_main_window_has_auto_save(self, qapp):
        from app.gui.main_window import MainWindow
        mw = MainWindow()
        try:
            assert hasattr(mw, "auto_save")
            from app.gui.auto_save import AutoSaveManager
            assert isinstance(mw.auto_save, AutoSaveManager)
            assert mw.auto_save.is_running()
        finally:
            mw.close()
