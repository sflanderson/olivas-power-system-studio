"""
Tests for ``app.gui.main_window`` ↔ ``app.gui.schematic_pp`` integration
(v0.21.4).

Cobertura
---------

* MainWindow expõe o tab "Esquemático Visual" e a instância
  ``self.schematic_pp`` é um :class:`PpEditor`.
* Callback ``_on_pp_open_sch`` carrega arquivo .sch na cena via
  monkeypatch do QFileDialog.
* Callback ``_on_pp_save_sch`` persiste cena em disco.
* Callback ``_on_pp_import_atp`` importa o caso ATP ativo para a
  cena PP (usa o AtpProject do caso ativo).
* Callback ``_on_pp_export_project`` publica um novo caso ATP via
  ``export_to_atp()`` e o registra em ``_cases``.
* ``export_requested`` signal do :class:`PpEditor` aciona o
  mesmo callback.
* Tests tolerantes a ``apply_theme`` em nova aba (não deve crashar).

Todos os testes usam QApplication headless — nenhum diálogo real é
aberto; QFileDialog é monkey-patched antes da chamada.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox

from app.core.project_model import (
    AtpProject,
    BranchComponent,
    HeaderInfo,
    Section,
    SourceComponent,
)
from app.gui.main_window import MainWindow
from app.gui.schematic_pp import PpEditor
from app.preprocessor.models import (
    PpComponent,
    PpProject,
    PpProperty,
    PpWire,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def mw(qapp):
    """MainWindow fresco, fechado ao final do teste."""
    w = MainWindow()
    yield w
    w.close()
    w.deleteLater()


def _sample_pp_project() -> PpProject:
    """
    Mini-projeto Qucs com 1 R + 1 Vdc + GND + fios em triângulo fechado.
    Serve como fixture simples para testes de round-trip.
    """
    r = PpComponent(
        type="R", name="R1", visible=True,
        x=100, y=100, label_dx=15, label_dy=-26, mirror=0, rotation=0,
        properties=[
            PpProperty(value="100", visible=True),
            PpProperty(value="26.85", visible=False),
            PpProperty(value="european", visible=False),
        ],
    )
    v = PpComponent(
        type="Vdc", name="V1", visible=True,
        x=50, y=100, label_dx=15, label_dy=-26, mirror=0, rotation=0,
        properties=[PpProperty(value="12 V", visible=True)],
    )
    gnd = PpComponent(
        type="GND", name="*", visible=True,
        x=75, y=150, label_dx=0, label_dy=0, mirror=0, rotation=0,
        properties=[],
    )
    wires = [
        PpWire(x1=50, y1=100, x2=100, y2=100, label=""),
        PpWire(x1=50, y1=100, x2=75, y2=150, label=""),
        PpWire(x1=100, y1=100, x2=75, y2=150, label=""),
    ]
    return PpProject(components=[r, v, gnd], wires=wires)


def _sample_atp_project() -> AtpProject:
    """Mini projeto ATP equivalente ao PP acima (RLC + fonte Vdc)."""
    branches = [
        BranchComponent(
            type_code="R", node1="N1", node2="N2",
            resistance="100", inductance=None, capacitance=None,
            raw_line="R N1    N2    100", line_number=0,
            semantic_type="resistor",
        ),
    ]
    sources = [
        SourceComponent(
            type_code="11", node="N1", amplitude="12", frequency=None,
            phase=None, t_start="-1", t_stop="1",
            raw_line="11 N1    12", line_number=1,
            semantic_type="dc",
        ),
    ]
    sections = {
        "BRANCH": Section(name="BRANCH", raw_lines=["R N1    N2    100"],
                          start_line=0, end_line=0),
        "SOURCE": Section(name="SOURCE", raw_lines=["11 N1    12"],
                          start_line=1, end_line=1),
    }
    proj = AtpProject(
        file_path="/fake/path.atp",
        raw_lines=[
            "BEGIN NEW DATA CASE", "/BRANCH", "R N1    N2    100",
            "/SOURCE", "11 N1    12", "BLANK", "BEGIN NEW DATA CASE",
            "C   END",
        ],
        header=HeaderInfo(
            raw_lines=["BEGIN NEW DATA CASE"],
            frequency=60.0, delta_t=1e-5, t_max=0.1,
        ),
        sections=sections,
        branches=branches,
        sources=sources,
    )
    return proj


# ---------------------------------------------------------------------------
# Tab + layout
# ---------------------------------------------------------------------------


class TestTabExists:
    """A aba deve estar no QTabWidget com texto estável."""

    def test_pp_editor_tab_present(self, mw):
        labels = [mw.tabs.tabText(i) for i in range(mw.tabs.count())]
        # v0.28.3-PRO Onda 3.4: tab agora marcada com ★ como
        # editor preferido (vs "Esquemático (legacy)")
        assert any("Esquemático Visual" in lbl for lbl in labels)

    def test_pp_editor_is_pp_editor_instance(self, mw):
        assert isinstance(mw.schematic_pp, PpEditor)

    def test_pp_editor_is_not_the_other_schematic(self, mw):
        """schematic (ATPDraw-like) e schematic_pp (Qucs-like) são widgets distintos."""
        assert mw.schematic is not mw.schematic_pp


# ---------------------------------------------------------------------------
# File menu submenu
# ---------------------------------------------------------------------------


class TestFileMenu:
    """Menu 'Arquivo' (v1.0.2 — submenu 'Esquemático visual'
    REMOVIDO; itens de IO promovidos para nível superior;
    Import/Export ATP desvinculados da UI principal)."""

    def _find_action(self, parent, text_substring: str):
        for action in parent.actions():
            if text_substring in action.text():
                return action
            if action.menu() is not None:
                found = self._find_action(action.menu(), text_substring)
                if found is not None:
                    return found
        return None

    def test_pp_open_action_exists(self, mw):
        """v1.0.2: 'Abrir esquemático (.sch)' no nível superior."""
        action = self._find_action(mw.menuBar(), ".sch")
        assert action is not None

    def test_pp_save_action_exists(self, mw):
        """v1.0.2: 'Salvar esquemático (.sch)' no nível superior."""
        action = self._find_action(mw.menuBar(), "Salvar esquemático")
        assert action is not None

    def test_atp_import_export_NOT_in_file_menu(self, mw):
        """v1.0.2: 'Importar caso ATP' e 'Exportar PP→ATP'
        REMOVIDOS do menu Arquivo (ATP IO desvinculado da UI;
        permanece apenas via API Python).
        Reflete reposicionamento estratégico v0.92.1+ do produto
        como alternativa profissional ao PTW (não interface ATP)."""
        assert self._find_action(
            mw.menuBar(), "Importar caso ATP atual",
        ) is None
        assert self._find_action(
            mw.menuBar(), "Exportar PP",
        ) is None

    def test_handlers_still_exist_for_api_compat(self, mw):
        """v1.0.2: handlers ``_on_pp_import_atp`` /
        ``_on_pp_export_project`` continuam EXISTINDO como
        atributos (chamáveis via API Python para integrações
        ou plugins) — só não estão wired ao menu."""
        assert hasattr(mw, "_on_pp_import_atp")
        assert hasattr(mw, "_on_pp_export_project")


# ---------------------------------------------------------------------------
# _on_pp_open_sch
# ---------------------------------------------------------------------------


class TestOpenSch:

    def test_open_sch_loads_scene(self, mw, tmp_path, monkeypatch):
        # Arrange: salva um .sch em disco.
        from app.preprocessor.qucs_sch_serializer import serialize_sch_file
        sch_path = tmp_path / "triangle.sch"
        serialize_sch_file(_sample_pp_project(), str(sch_path))

        # Stub QFileDialog.getOpenFileName to return the sch path.
        monkeypatch.setattr(
            QFileDialog, "getOpenFileName",
            staticmethod(lambda *a, **kw: (str(sch_path), "")),
        )

        # Act
        mw._on_pp_open_sch()

        # Assert: cena carregada com os 3 componentes.
        scene = mw.schematic_pp.scene
        assert len(scene.component_items()) == 3
        names = {c.component.name for c in scene.component_items()}
        assert "R1" in names
        assert "V1" in names

    def test_open_sch_dialog_cancelled(self, mw, monkeypatch):
        # Retornando ("", "") simula cancelamento.
        monkeypatch.setattr(
            QFileDialog, "getOpenFileName",
            staticmethod(lambda *a, **kw: ("", "")),
        )
        # Antes da chamada: cena vazia. Depois: ainda vazia (nada carregado).
        before = len(mw.schematic_pp.scene.component_items())
        mw._on_pp_open_sch()
        after = len(mw.schematic_pp.scene.component_items())
        assert after == before

    def test_open_sch_invalid_file_shows_error(self, mw, tmp_path, monkeypatch):
        # Arquivo sintaticamente quebrado.
        bad = tmp_path / "bad.sch"
        bad.write_text("not a qucs file at all", encoding="utf-8")

        monkeypatch.setattr(
            QFileDialog, "getOpenFileName",
            staticmethod(lambda *a, **kw: (str(bad), "")),
        )
        calls: list[tuple] = []
        monkeypatch.setattr(
            QMessageBox, "critical",
            staticmethod(lambda *a, **kw: calls.append(a) or QMessageBox.Ok),
        )

        mw._on_pp_open_sch()
        # Parser aceita vários formatos; se não lançar, teste verifica
        # simplesmente que não crashou. Se lançar, deve ter chamado critical.
        assert len(mw.schematic_pp.scene.component_items()) == 0 or calls


# ---------------------------------------------------------------------------
# _on_pp_save_sch
# ---------------------------------------------------------------------------


class TestSaveSch:

    def test_save_sch_writes_file(self, mw, tmp_path, monkeypatch):
        # Arrange: popula cena.
        mw.schematic_pp.scene.load_project(_sample_pp_project())
        out = tmp_path / "out.sch"
        monkeypatch.setattr(
            QFileDialog, "getSaveFileName",
            staticmethod(lambda *a, **kw: (str(out), "")),
        )

        # Act
        mw._on_pp_save_sch()

        # Assert: arquivo criado e contém tokens Qucs.
        assert out.exists()
        content = out.read_text(encoding="utf-8")
        assert "<Qucs Schematic" in content
        assert "<Components>" in content

    def test_save_sch_empty_scene_warns(self, mw, monkeypatch):
        """Cena vazia não deve disparar o save dialog."""
        dialog_called = []
        monkeypatch.setattr(
            QFileDialog, "getSaveFileName",
            staticmethod(lambda *a, **kw: dialog_called.append(True) or ("", "")),
        )
        info_called = []
        monkeypatch.setattr(
            QMessageBox, "information",
            staticmethod(
                lambda *a, **kw: info_called.append(a) or QMessageBox.Ok
            ),
        )
        mw._on_pp_save_sch()
        assert info_called  # mensagem "esquemático vazio"
        assert not dialog_called  # dialog não foi aberto

    def test_save_sch_cancel_does_nothing(self, mw, tmp_path, monkeypatch):
        mw.schematic_pp.scene.load_project(_sample_pp_project())
        monkeypatch.setattr(
            QFileDialog, "getSaveFileName",
            staticmethod(lambda *a, **kw: ("", "")),
        )
        # Não deve criar arquivo algum em tmp_path.
        mw._on_pp_save_sch()
        assert list(tmp_path.iterdir()) == []


# ---------------------------------------------------------------------------
# _on_pp_import_atp
# ---------------------------------------------------------------------------


class TestImportAtp:

    def test_import_atp_with_no_project_shows_info(self, mw, monkeypatch):
        called = []
        monkeypatch.setattr(
            QMessageBox, "information",
            staticmethod(lambda *a, **kw: called.append(a) or QMessageBox.Ok),
        )
        # mw._cases vazio → self.project == None
        mw._on_pp_import_atp()
        assert called

    def test_import_atp_loads_into_pp(self, mw):
        # Registra um caso ATP ativo.
        proj = _sample_atp_project()
        mw._cases[proj.file_path] = proj
        mw._active_case = proj.file_path

        mw._on_pp_import_atp()

        pp_scene = mw.schematic_pp.scene
        # Deve ter gerado ao menos 1 componente (resistor + source).
        assert len(pp_scene.component_items()) >= 2

    def test_import_atp_switches_to_pp_tab(self, mw):
        proj = _sample_atp_project()
        mw._cases[proj.file_path] = proj
        mw._active_case = proj.file_path

        mw._on_pp_import_atp()

        assert mw.tabs.currentWidget() is mw.schematic_pp


# ---------------------------------------------------------------------------
# _on_pp_export_project
# ---------------------------------------------------------------------------


class TestExportProject:

    def test_export_empty_scene_shows_info(self, mw, monkeypatch):
        called = []
        monkeypatch.setattr(
            QMessageBox, "information",
            staticmethod(lambda *a, **kw: called.append(a) or QMessageBox.Ok),
        )
        # cena PP vazia
        mw._on_pp_export_project()
        # Não há componentes → to_atp deve produzir projeto "vazio" que
        # disparar o info ou ser registrado como caso vazio. Aceita
        # qualquer um dos dois caminhos: info (mensagem) OU caso registrado
        # com 0 branches. O importante é que não crashe.
        assert called or "<pp-export-1>" in mw._cases

    def test_export_populated_scene_registers_case(self, mw):
        mw.schematic_pp.scene.load_project(_sample_pp_project())
        before_cases = set(mw._cases.keys())

        mw._on_pp_export_project()

        new_cases = set(mw._cases.keys()) - before_cases
        assert len(new_cases) == 1, (
            f"Expected exactly one new case, got {new_cases}"
        )
        key = next(iter(new_cases))
        assert key.startswith("<pp-export-")

        proj = mw._cases[key]
        assert isinstance(proj, AtpProject)
        # O branch R deve ter sido produzido.
        assert len(proj.branches) >= 1
        assert len(proj.sources) >= 1

    def test_export_makes_case_active(self, mw):
        mw.schematic_pp.scene.load_project(_sample_pp_project())

        mw._on_pp_export_project()

        assert mw._active_case and mw._active_case.startswith("<pp-export-")
        assert mw.project is not None

    def test_export_signal_triggers_callback(self, mw):
        """Emitindo o signal do PpEditor deve registrar como caso também."""
        mw.schematic_pp.scene.load_project(_sample_pp_project())
        before_n = len(mw._cases)

        # Dispara o signal diretamente (simula clique em "Exportar ATP").
        project = mw.schematic_pp.export_to_atp()
        mw.schematic_pp.export_requested.emit(project)

        after_n = len(mw._cases)
        assert after_n == before_n + 1

    def test_two_exports_get_unique_keys(self, mw):
        mw.schematic_pp.scene.load_project(_sample_pp_project())
        mw._on_pp_export_project()
        mw._on_pp_export_project()
        pp_keys = [k for k in mw._cases.keys() if k.startswith("<pp-export-")]
        assert len(set(pp_keys)) == len(pp_keys)  # todas únicas


# ---------------------------------------------------------------------------
# Round-trip: ATP → PP → ATP
# ---------------------------------------------------------------------------


class TestRoundTrip:
    """Smoke test de round-trip para garantir que o ciclo funciona."""

    def test_import_then_export(self, mw):
        proj = _sample_atp_project()
        mw._cases[proj.file_path] = proj
        mw._active_case = proj.file_path

        mw._on_pp_import_atp()
        assert len(mw.schematic_pp.scene.component_items()) >= 2

        # Re-exporta para novo caso.
        mw._on_pp_export_project()

        pp_keys = [k for k in mw._cases.keys() if k.startswith("<pp-export-")]
        assert len(pp_keys) == 1

    def test_sch_roundtrip_through_mainwindow(self, mw, tmp_path, monkeypatch):
        """Save → Open gera uma cena equivalente (mesmo número de componentes)."""
        mw.schematic_pp.scene.load_project(_sample_pp_project())
        n_before = len(mw.schematic_pp.scene.component_items())

        # Save.
        out = tmp_path / "rt.sch"
        monkeypatch.setattr(
            QFileDialog, "getSaveFileName",
            staticmethod(lambda *a, **kw: (str(out), "")),
        )
        mw._on_pp_save_sch()
        assert out.exists()

        # New project (wipe).
        mw.schematic_pp.new_project()
        assert len(mw.schematic_pp.scene.component_items()) == 0

        # Open.
        monkeypatch.setattr(
            QFileDialog, "getOpenFileName",
            staticmethod(lambda *a, **kw: (str(out), "")),
        )
        mw._on_pp_open_sch()
        n_after = len(mw.schematic_pp.scene.component_items())
        assert n_after == n_before
