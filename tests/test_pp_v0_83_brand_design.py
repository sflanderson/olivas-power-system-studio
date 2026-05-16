"""
tests/test_pp_v0_83_brand_design.py — v0.83: design system
brand "Oliveira":

* Paleta de cores no theme.py
* Splash screen com logo + progress bar
* Window icon (favicon)
* Logo nos reports HTML/PDF
"""

from __future__ import annotations

from pathlib import Path

import pytest


PySide6 = pytest.importorskip("PySide6")
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


# ---------------------------------------------------------------------------
# Brand palette
# ---------------------------------------------------------------------------


class TestBrandPalette:

    def test_logo_colors_exported(self):
        from app.gui.theme import (
            LIME_BRIGHT, CYAN_BRIGHT, PURPLE_DEEP, PURPLE_LIGHT,
        )
        assert LIME_BRIGHT == "#BFFF00"
        assert CYAN_BRIGHT == "#00A8E8"
        assert PURPLE_DEEP == "#7E2BA8"

    def test_olive_palette_exported(self):
        from app.gui.theme import (
            OLIVE_DEEP, OLIVE_MEDIUM, OLIVE_LIGHT,
            OLIVE_PALE, OLIVE_CREAM, OLIVE_BARK, OLIVE_GOLD,
        )
        assert OLIVE_DEEP == "#556B2F"
        assert OLIVE_MEDIUM == "#6B8E23"
        assert OLIVE_LIGHT == "#87A96B"
        assert OLIVE_PALE == "#B5D4A8"
        assert OLIVE_CREAM == "#FAFAF5"
        assert OLIVE_BARK == "#5C4D3C"
        assert OLIVE_GOLD == "#D4AF37"

    def test_dark_palette_uses_brand(self):
        from app.gui.theme import DARK, OLIVE_DEEP, CYAN_BRIGHT
        # Selection bg agora é OLIVE_DEEP (era #264f78)
        assert DARK["selection_bg"] == OLIVE_DEEP
        # val_info agora é CYAN_BRIGHT (logo)
        assert DARK["val_info"] == CYAN_BRIGHT

    def test_light_palette_uses_brand(self):
        from app.gui.theme import LIGHT, OLIVE_CREAM, OLIVE_DEEP
        # Bg base agora é OLIVE_CREAM (era #f0f0f0)
        assert LIGHT["bg"] == OLIVE_CREAM
        # Selection é OLIVE_DEEP
        assert LIGHT["selection_bg"] == OLIVE_DEEP

    def test_legacy_accent_aliases_brand(self):
        """ACCENT_BLUE/GREEN/PURPLE agora apontam à paleta brand."""
        from app.gui.theme import (
            ACCENT_BLUE, CYAN_BRIGHT,
            ACCENT_GREEN, OLIVE_LIGHT,
            ACCENT_PURPLE, PURPLE_LIGHT,
        )
        assert ACCENT_BLUE == CYAN_BRIGHT
        assert ACCENT_GREEN == OLIVE_LIGHT
        assert ACCENT_PURPLE == PURPLE_LIGHT


# ---------------------------------------------------------------------------
# Splash screen
# ---------------------------------------------------------------------------


class TestSplashScreen:

    def test_instantiates(self, qapp):
        from app.gui.splash_screen import (
            OlivasSplashScreen, SPLASH_WIDTH, SPLASH_HEIGHT,
        )
        splash = OlivasSplashScreen()
        try:
            assert splash.width() == SPLASH_WIDTH
            assert splash.height() == SPLASH_HEIGHT
        finally:
            splash.close()

    def test_has_logo_label(self, qapp):
        from app.gui.splash_screen import OlivasSplashScreen
        splash = OlivasSplashScreen()
        try:
            assert hasattr(splash, "_logo_label")
            # Logo carregado ou texto "OLIVAS" fallback
            pixmap = splash._logo_label.pixmap()
            text = splash._logo_label.text()
            assert (pixmap is not None and not pixmap.isNull()) or text
        finally:
            splash.close()

    def test_has_progress_bar(self, qapp):
        from PySide6.QtWidgets import QProgressBar
        from app.gui.splash_screen import OlivasSplashScreen
        splash = OlivasSplashScreen()
        try:
            assert hasattr(splash, "_progress")
            assert isinstance(splash._progress, QProgressBar)
            assert splash._progress.minimum() == 0
            assert splash._progress.maximum() == 100
        finally:
            splash.close()

    def test_set_progress_internal_state(self, qapp):
        """
        v0.83.4: usa ``set_progress(process_events=False)``
        para validar a API pública sem flakiness do event
        loop. Em produção (``app/main.py``) usa default
        ``process_events=True`` para repaint imediato.
        """
        from app.gui.splash_screen import OlivasSplashScreen
        splash = OlivasSplashScreen()
        try:
            splash.set_progress(50, "Carregando...", process_events=False)
            assert splash._progress.value() == 50
            assert splash._status_label.text() == "Carregando..."
        finally:
            splash.close()

    def test_progress_clamped(self, qapp):
        """
        v0.83.4: usa ``process_events=False`` para evitar
        flakiness em suite full. Mesma patologia do
        test_set_progress_internal_state.
        """
        from app.gui.splash_screen import OlivasSplashScreen
        splash = OlivasSplashScreen()
        try:
            splash.set_progress(150, process_events=False)
            assert splash._progress.value() == 100
            splash.set_progress(-10, process_events=False)
            assert splash._progress.value() == 0
        finally:
            splash.close()

    def test_finish_closes(self, qapp):
        """
        v0.83.5: spy em ``close()``/``raise_()``/
        ``activateWindow()`` em vez de ``isVisible()``.

        Sob stress de event loop em suite full (3000+
        testes), o flag ``isVisible()`` pode demorar a
        refletir ``close()`` por pressão no event queue
        do Qt. Validamos o contrato real do método: que
        ``finish(target)`` chama ``close()`` no splash e
        ``raise_()`` + ``activateWindow()`` no target.
        """
        from PySide6.QtWidgets import QWidget
        from app.gui.splash_screen import OlivasSplashScreen
        target = QWidget()
        splash = OlivasSplashScreen()

        closed = []
        raised = []
        activated = []
        original_close = splash.close
        original_raise = target.raise_
        original_activate = target.activateWindow

        def spy_close():
            closed.append(True)
            return original_close()

        def spy_raise():
            raised.append(True)
            return original_raise()

        def spy_activate():
            activated.append(True)
            return original_activate()

        splash.close = spy_close
        target.raise_ = spy_raise
        target.activateWindow = spy_activate

        splash.finish(target)

        assert closed == [True]
        assert raised == [True]
        assert activated == [True]
        target.close()

    def test_logo_path_exists(self):
        """Logo file deve existir em app/resources/logo.png."""
        logo = (
            Path(__file__).resolve().parent.parent
            / "app" / "resources" / "logo.png"
        )
        assert logo.is_file(), f"Logo missing: {logo}"


# ---------------------------------------------------------------------------
# Window icon (favicon)
# ---------------------------------------------------------------------------


class TestWindowIcon:

    def test_main_module_imports(self):
        """app/main.py importa sem erro (após refactor v0.83)."""
        import app.main
        assert hasattr(app.main, "main")
        assert hasattr(app.main, "_setup_application_icon")

    def test_setup_application_icon_callable(self):
        from app.main import _setup_application_icon
        assert callable(_setup_application_icon)


# ---------------------------------------------------------------------------
# Logo em reports
# ---------------------------------------------------------------------------


class TestReportHtmlLogo:

    def test_logo_data_uri_returns_valid(self):
        from app.postprocessor.report_html import _logo_data_uri
        uri = _logo_data_uri()
        assert uri.startswith("data:image/png;base64,")
        # Deve ter conteúdo significativo (> 1000 chars base64)
        assert len(uri) > 1000

    def test_html_contains_logo(self):
        from app.postprocessor.bus_pipeline import BusPipelineReport
        from app.postprocessor.report_html import generate_html_report
        r = BusPipelineReport(
            bus_id="TEST", rated_voltage_kV=13.8,
            panel_type="swgr_15kv",
            is_lineside=True, has_AFD=False,
            n_neighbors=1, n_sc_sources=1,
            sources_summary=("UTIL: 100%",),
            Ik_pp_kA=15, ip_kA=40, kappa=1.85,
            coordination_clearing_time_ms=200,
            effective_clearing_time_ms=200,
            incident_energy_cal_cm2=12,
            arc_flash_boundary_mm=2000,
            ppe_category="3", warnings=(),
        )
        html = generate_html_report(r)
        # Logo presente como data URI
        assert "data:image/png" in html
        # Brand colors aplicados
        assert "#556B2F" in html or "OLIVE_DEEP" in html.upper()

    def test_html_uses_brand_colors_in_css(self):
        from app.postprocessor.report_html import _HTML_CSS
        # Paleta Oliveira aplicada
        assert "#556B2F" in _HTML_CSS   # OLIVE_DEEP
        assert "#FAFAF5" in _HTML_CSS   # OLIVE_CREAM
        assert "#B5D4A8" in _HTML_CSS   # OLIVE_PALE


class TestReportPdfLogo:

    def test_pdf_generates_with_logo(self, tmp_path):
        """Smoke: PDF é gerado sem erro com paleta brand."""
        from app.postprocessor.bus_pipeline import BusPipelineReport
        from app.postprocessor.report_pdf import save_pdf_report
        r = BusPipelineReport(
            bus_id="TEST-BUS", rated_voltage_kV=13.8,
            panel_type="swgr_15kv",
            is_lineside=True, has_AFD=False,
            n_neighbors=1, n_sc_sources=1,
            sources_summary=("UTIL: 100%",),
            Ik_pp_kA=15, ip_kA=40, kappa=1.85,
            coordination_clearing_time_ms=200,
            effective_clearing_time_ms=200,
            incident_energy_cal_cm2=12,
            arc_flash_boundary_mm=2000,
            ppe_category="3", warnings=(),
        )
        out = tmp_path / "report.pdf"
        save_pdf_report(r, str(out))
        assert out.is_file()
        assert out.stat().st_size > 5000   # PDF não-vazio

    def test_pdf_starts_with_pdf_header(self, tmp_path):
        """Header válido %PDF-."""
        from app.postprocessor.bus_pipeline import BusPipelineReport
        from app.postprocessor.report_pdf import save_pdf_report
        r = BusPipelineReport(
            bus_id="X", rated_voltage_kV=13.8,
            panel_type="swgr_15kv", is_lineside=True,
            has_AFD=False, n_neighbors=0, n_sc_sources=0,
            sources_summary=(),
            Ik_pp_kA=10, ip_kA=20, kappa=1.5,
            coordination_clearing_time_ms=100,
            effective_clearing_time_ms=100,
            incident_energy_cal_cm2=5,
            arc_flash_boundary_mm=500,
            ppe_category="2", warnings=(),
        )
        out = tmp_path / "test.pdf"
        save_pdf_report(r, str(out))
        with open(out, "rb") as f:
            head = f.read(8)
        assert head.startswith(b"%PDF-")
