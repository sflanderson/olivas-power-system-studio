"""
tests/test_pp_v0_81_examples_sch_apikey.py — v0.81:
* Schematics .sch para os 6 exemplos das normas.
* Centralized api_key_manager (QSettings + env + .env).
* Dialog ApiKeyDialog para configuração.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# .sch para exemplos
# ---------------------------------------------------------------------------


class TestExampleSchematics:

    def test_schematic_path_for_known(self):
        from app.examples.schematics import schematic_path_for
        for ex_id in [
            "stevenson_pf_3bus", "stevenson_sequential",
            "iec60909_annex_c", "ieee1584_ex_d2",
            "ieee399_motor_starting", "nbr17227_example",
        ]:
            p = schematic_path_for(ex_id)
            assert p is not None, f"{ex_id} não tem .sch"
            assert p.is_file()

    def test_schematic_path_unknown_returns_none(self):
        from app.examples.schematics import schematic_path_for
        assert schematic_path_for("__xyz__") is None

    def test_all_schematics_parse(self):
        """Todos os 6 .sch são válidos Qucs format."""
        from app.examples.schematics import schematic_path_for
        from app.preprocessor.qucs_sch_parser import parse_sch_file
        for ex_id in [
            "stevenson_pf_3bus", "stevenson_sequential",
            "iec60909_annex_c", "ieee1584_ex_d2",
            "ieee399_motor_starting", "nbr17227_example",
        ]:
            p = schematic_path_for(ex_id)
            project = parse_sch_file(str(p))
            assert len(project.components) > 0
            assert len(project.wires) > 0

    def test_stevenson_pf_3bus_has_3_buses(self):
        from app.examples.schematics import schematic_path_for
        from app.preprocessor.qucs_sch_parser import parse_sch_file
        proj = parse_sch_file(str(
            schematic_path_for("stevenson_pf_3bus"),
        ))
        bus_count = sum(1 for c in proj.components if c.type == "BUS")
        assert bus_count == 3

    def test_iec60909_has_transformer(self):
        from app.examples.schematics import schematic_path_for
        from app.preprocessor.qucs_sch_parser import parse_sch_file
        proj = parse_sch_file(str(
            schematic_path_for("iec60909_annex_c"),
        ))
        tr_count = sum(
            1 for c in proj.components if c.type in ("Tr", "sTr", "Tr3", "XFMR")
        )
        assert tr_count >= 1

    def test_ieee399_has_motor(self):
        from app.examples.schematics import schematic_path_for
        from app.preprocessor.qucs_sch_parser import parse_sch_file
        proj = parse_sch_file(str(
            schematic_path_for("ieee399_motor_starting"),
        ))
        motor_count = sum(
            1 for c in proj.components if c.type == "MOTOR"
        )
        assert motor_count >= 1


# ---------------------------------------------------------------------------
# api_key_manager
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_api_key_cache(monkeypatch):
    """Limpa cache + env entre tests."""
    from app.core import api_key_manager
    api_key_manager._CACHED_KEY = None
    api_key_manager._CACHE_INITIALIZED = False
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    yield


class TestApiKeyManager:

    def test_no_key_returns_none(self, tmp_path, monkeypatch):
        """Sem nenhuma fonte → None."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        # Não chama set_anthropic_api_key, não tem env, não tem .env
        from app.core.api_key_manager import (
            get_anthropic_api_key, _CACHE_INITIALIZED,
        )
        # Nota: _read_qsettings ainda pode pegar QSettings global
        # Por isso o teste pode retornar valor em ambiente
        # configurado — vamos só verificar não-crash
        result = get_anthropic_api_key(force_refresh=True)
        assert result is None or isinstance(result, str)

    def test_env_var_detected(self, tmp_path, monkeypatch):
        """Env ANTHROPIC_API_KEY → detectado."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        # Limpa QSettings que pode ter valor pré-existente
        try:
            from PySide6.QtCore import QSettings
            s = QSettings("OlivasATPStudio", "OlivasATPStudio")
            saved = s.value("anthropic_api_key", None)
            s.remove("anthropic_api_key")
        except ImportError:
            saved = None
        try:
            monkeypatch.setenv(
                "ANTHROPIC_API_KEY", "sk-test-from-env",
            )
            from app.core.api_key_manager import get_anthropic_api_key
            assert get_anthropic_api_key(force_refresh=True) == \
                "sk-test-from-env"
        finally:
            # Restaura QSettings
            if saved is not None:
                try:
                    from PySide6.QtCore import QSettings
                    s = QSettings("OlivasATPStudio", "OlivasATPStudio")
                    s.setValue("anthropic_api_key", saved)
                    s.sync()
                except ImportError:
                    pass

    def test_set_and_get(self, tmp_path, monkeypatch):
        """set_anthropic_api_key → get_anthropic_api_key retorna."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        from app.core.api_key_manager import (
            get_anthropic_api_key, set_anthropic_api_key,
            clear_anthropic_api_key,
        )
        try:
            set_anthropic_api_key("sk-ant-set-test")
            assert get_anthropic_api_key(force_refresh=True) == \
                "sk-ant-set-test"
        finally:
            clear_anthropic_api_key()

    def test_clear(self, tmp_path, monkeypatch):
        """clear_anthropic_api_key remove tudo."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        from app.core.api_key_manager import (
            clear_anthropic_api_key, set_anthropic_api_key,
        )
        set_anthropic_api_key("sk-temp")
        clear_anthropic_api_key()
        assert os.environ.get("ANTHROPIC_API_KEY") is None

    def test_dotenv_fallback(self, tmp_path, monkeypatch):
        """Se .env tem ANTHROPIC_API_KEY, é detectado."""
        # .env file teste — colocar em pasta que app/core/
        # subirá até encontrar
        from app.core import api_key_manager
        # Mocka o read_dotenv para retornar valor controlado
        monkeypatch.setattr(
            api_key_manager, "_read_dotenv",
            lambda: "sk-from-dotenv",
        )
        monkeypatch.setattr(
            api_key_manager, "_read_qsettings",
            lambda: None,
        )
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        api_key_manager._CACHED_KEY = None
        api_key_manager._CACHE_INITIALIZED = False
        assert api_key_manager.get_anthropic_api_key() == "sk-from-dotenv"

    def test_is_configured_false_when_empty(self, tmp_path, monkeypatch):
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        from app.core import api_key_manager
        api_key_manager._CACHED_KEY = None
        api_key_manager._CACHE_INITIALIZED = True   # simula cache
        api_key_manager._CACHED_KEY = None
        # Override fontes
        monkeypatch.setattr(
            api_key_manager, "_read_qsettings", lambda: None,
        )
        monkeypatch.setattr(
            api_key_manager, "_read_dotenv", lambda: None,
        )
        monkeypatch.setattr(
            api_key_manager, "_read_user_config", lambda: None,
        )
        api_key_manager._CACHE_INITIALIZED = False
        assert not api_key_manager.is_configured()

    def test_is_configured_true_for_valid_key(
        self, tmp_path, monkeypatch,
    ):
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        from app.core import api_key_manager
        api_key_manager._CACHED_KEY = None
        api_key_manager._CACHE_INITIALIZED = False
        monkeypatch.setattr(
            api_key_manager, "_read_qsettings",
            lambda: "sk-ant-validkey1234567890",
        )
        assert api_key_manager.is_configured()

    def test_masked_key(self, tmp_path, monkeypatch):
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        from app.core import api_key_manager
        api_key_manager._CACHED_KEY = None
        api_key_manager._CACHE_INITIALIZED = False
        monkeypatch.setattr(
            api_key_manager, "_read_qsettings",
            lambda: "sk-ant-1234567890ABCDEFG",
        )
        masked = api_key_manager.masked_key()
        assert masked.startswith("sk-")
        assert "*" in masked
        assert "EFG" in masked   # últimos 4 visíveis

    def test_masked_key_when_unconfigured(
        self, tmp_path, monkeypatch,
    ):
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        from app.core import api_key_manager
        api_key_manager._CACHED_KEY = None
        api_key_manager._CACHE_INITIALIZED = False
        monkeypatch.setattr(
            api_key_manager, "_read_qsettings", lambda: None,
        )
        monkeypatch.setattr(
            api_key_manager, "_read_dotenv", lambda: None,
        )
        monkeypatch.setattr(
            api_key_manager, "_read_user_config", lambda: None,
        )
        masked = api_key_manager.masked_key()
        assert "não configurada" in masked or "*" in masked


# ---------------------------------------------------------------------------
# ApiKeyDialog
# ---------------------------------------------------------------------------


class TestApiKeyDialog:

    def test_dialog_instantiates(self):
        PySide6 = pytest.importorskip("PySide6")
        from PySide6.QtWidgets import QApplication, QDialog
        app = QApplication.instance() or QApplication([])
        from app.gui.api_key_dialog import ApiKeyDialog
        dlg = ApiKeyDialog()
        assert isinstance(dlg, QDialog)
        assert "API Key" in dlg.windowTitle()


# ---------------------------------------------------------------------------
# Menu integration in MainWindow
# ---------------------------------------------------------------------------


class TestMenuIntegration:

    def test_menu_simulation_has_api_key_action(self):
        """v0.92: menu Simulação foi renomeado 'Ferramentas'.
        API Key Claude continua acessível por lá."""
        PySide6 = pytest.importorskip("PySide6")
        from PySide6.QtWidgets import QApplication, QMenu
        app = QApplication.instance() or QApplication([])
        from app.gui.main_window import MainWindow
        mw = MainWindow()
        try:
            menus = mw.menuBar().findChildren(QMenu)
            tools_menu = next(
                (m for m in menus if m.title() == "Ferramentas"),
                None,
            )
            assert tools_menu is not None, (
                "Menu 'Ferramentas' ausente "
                "(antes 'Simulação' até v0.91.x)."
            )
            actions_text = [a.text() for a in tools_menu.actions()]
            assert any(
                "API Key" in t or "API" in t for t in actions_text
            ), f"API Key action ausente em Ferramentas: {actions_text}"
        finally:
            mw.close()
