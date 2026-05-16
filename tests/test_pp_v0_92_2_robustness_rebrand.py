"""
tests/test_pp_v0_92_2_robustness_rebrand.py — v0.92.2:

Cobertura das melhorias de robustez + rebrand:

1. **logging_config**: get_logger funcional, idempotente,
   log_engineering_event estruturado.
2. **ArcFlashCase.__post_init__**: rejeita inputs físicos
   inválidos (tensão ≤ 0, corrente > 200 kA, tempo ≤ 0,
   gap fora de [0, 200], working_distance fora de [50, 5000]).
3. **Logging dos fallbacks**: divisão por zero em IEC 60909
   (z_thevenin=0, Ik3=0) emite WARNING.
4. **Rebrand**: PRODUCT_NAME = "Olivas Power System Studio",
   audit_trail.make_audit_header() default usa novo nome,
   welcome dialog título atualizado, reports HTML com novo
   header.
"""

from __future__ import annotations

import logging

import pytest


# ---------------------------------------------------------------------------
# logging_config
# ---------------------------------------------------------------------------


class TestLoggingConfig:

    def test_get_logger_returns_logger(self):
        from app.core.logging_config import get_logger
        log = get_logger("test_module")
        assert isinstance(log, logging.Logger)

    def test_configure_idempotent(self):
        """v0.92.2: configure_logging pode ser chamado múltiplas
        vezes sem duplicar handlers."""
        from app.core.logging_config import configure_logging
        configure_logging()
        configure_logging()  # Segunda chamada deve ser no-op
        # Verifica que não duplicou handlers
        root = logging.getLogger("app")
        # 2 ou menos handlers (1 stream + opcionalmente 1 file)
        assert len(root.handlers) <= 2

    def test_log_engineering_event_emits_structured(self):
        """v0.92.2: log_engineering_event gera linha estruturada
        com EVT, NORM, BUS, FALLBACK."""
        from app.core.logging_config import (
            get_logger, log_engineering_event,
        )
        log = get_logger("app.test_evt")
        records = []

        class _ListHandler(logging.Handler):
            def emit(self, record):
                records.append(record)

        h = _ListHandler(level=logging.DEBUG)
        logging.getLogger("app").addHandler(h)
        try:
            log_engineering_event(
                log,
                event="z_thevenin_zero",
                norm="IEC 60909-0 §4.3.1",
                bus="BUS-MAIN",
                fallback="Ik''=inf",
                voltage_kV=13.8,
            )
        finally:
            logging.getLogger("app").removeHandler(h)
        msg = " ".join(r.getMessage() for r in records)
        assert "EVT=z_thevenin_zero" in msg
        assert "NORM=IEC 60909-0 §4.3.1" in msg
        assert "BUS=BUS-MAIN" in msg
        assert "FALLBACK=" in msg
        assert "VOLTAGE_KV=13.8" in msg


# ---------------------------------------------------------------------------
# ArcFlashCase validation
# ---------------------------------------------------------------------------


class TestArcFlashCaseValidation:

    def _valid_case(self, **overrides):
        """Helper: retorna kwargs válidos com possíveis overrides."""
        from app.standards.nbr17227 import EquipmentClass
        kwargs = dict(
            bus_name="BUS-1",
            rated_voltage_kV=13.8,
            bolted_fault_current_kA=12.5,
            arc_clearing_time_ms=500.0,
            equipment_class=EquipmentClass.SWITCHGEAR_15KV,
        )
        kwargs.update(overrides)
        return kwargs

    def test_valid_case_accepts(self):
        from app.postprocessor.arc_flash import ArcFlashCase
        c = ArcFlashCase(**self._valid_case())
        assert c.bus_name == "BUS-1"

    def test_empty_bus_name_rejected(self):
        from app.postprocessor.arc_flash import ArcFlashCase
        with pytest.raises(ValueError, match="bus_name"):
            ArcFlashCase(**self._valid_case(bus_name=""))

    def test_zero_voltage_rejected(self):
        from app.postprocessor.arc_flash import ArcFlashCase
        with pytest.raises(ValueError, match="rated_voltage_kV"):
            ArcFlashCase(**self._valid_case(rated_voltage_kV=0))

    def test_negative_voltage_rejected(self):
        from app.postprocessor.arc_flash import ArcFlashCase
        with pytest.raises(ValueError, match="rated_voltage_kV"):
            ArcFlashCase(**self._valid_case(rated_voltage_kV=-5))

    def test_zero_fault_current_rejected(self):
        from app.postprocessor.arc_flash import ArcFlashCase
        with pytest.raises(ValueError, match="bolted_fault_current_kA"):
            ArcFlashCase(**self._valid_case(bolted_fault_current_kA=0))

    def test_excessive_fault_current_rejected(self):
        from app.postprocessor.arc_flash import ArcFlashCase
        with pytest.raises(ValueError, match="200 kA"):
            ArcFlashCase(**self._valid_case(bolted_fault_current_kA=300))

    def test_zero_clearing_time_rejected(self):
        from app.postprocessor.arc_flash import ArcFlashCase
        with pytest.raises(ValueError, match="arc_clearing_time_ms"):
            ArcFlashCase(**self._valid_case(arc_clearing_time_ms=0))

    def test_invalid_enclosure_factor_rejected(self):
        from app.postprocessor.arc_flash import ArcFlashCase
        with pytest.raises(ValueError, match="enclosure_correction"):
            ArcFlashCase(**self._valid_case(
                enclosure_correction_factor=10,
            ))

    def test_gap_out_of_range_rejected(self):
        from app.postprocessor.arc_flash import ArcFlashCase
        with pytest.raises(ValueError, match="gap_mm"):
            ArcFlashCase(**self._valid_case(gap_mm=300.0))

    def test_working_distance_out_of_range_rejected(self):
        from app.postprocessor.arc_flash import ArcFlashCase
        with pytest.raises(ValueError, match="working_distance_mm"):
            ArcFlashCase(**self._valid_case(working_distance_mm=10.0))

    def _attach_list_handler(self):
        """v0.92.2 helper: anexa handler de lista ao logger 'app'
        para capturar records. caplog do pytest não funciona com
        propagate=False (default do Olivas)."""
        from app.core.logging_config import get_logger
        records = []

        class _ListHandler(logging.Handler):
            def emit(self, record):
                records.append(record)

        app_logger = logging.getLogger("app")
        h = _ListHandler(level=logging.DEBUG)
        app_logger.addHandler(h)
        return records, h

    def test_voltage_below_typical_warns_but_accepts(self):
        """v0.92.2: tensão < 0.208 kV acima de 0 é aceita com warning."""
        from app.postprocessor.arc_flash import ArcFlashCase
        records, h = self._attach_list_handler()
        try:
            c = ArcFlashCase(
                **self._valid_case(rated_voltage_kV=0.10),
            )
        finally:
            logging.getLogger("app").removeHandler(h)
        assert c.rated_voltage_kV == 0.10
        msgs = [r.getMessage() for r in records]
        assert any("abaixo da faixa" in m for m in msgs), (
            f"Expected 'abaixo da faixa' warning. Got: {msgs}"
        )

    def test_voltage_above_15kv_warns_but_accepts(self):
        """v0.92.2: tensão > 15 kV aceita com warning (limite NBR)."""
        from app.postprocessor.arc_flash import ArcFlashCase
        records, h = self._attach_list_handler()
        try:
            c = ArcFlashCase(
                **self._valid_case(rated_voltage_kV=34.5),
            )
        finally:
            logging.getLogger("app").removeHandler(h)
        assert c.rated_voltage_kV == 34.5
        msgs = [r.getMessage() for r in records]
        assert any("acima da faixa" in m for m in msgs), (
            f"Expected 'acima da faixa' warning. Got: {msgs}"
        )


# ---------------------------------------------------------------------------
# IEC 60909 fallback logging
# ---------------------------------------------------------------------------


class TestIec60909FallbackLogging:

    def test_z_thevenin_zero_logs_warning(self):
        """v0.92.2: divisão por zero em initial_symmetric_sc_current_kA
        agora loga warning (era silent fallback)."""
        from app.standards.iec60909 import initial_symmetric_sc_current_kA

        records = []

        class _ListHandler(logging.Handler):
            def emit(self, record):
                records.append(record)

        h = _ListHandler(level=logging.DEBUG)
        logging.getLogger("app").addHandler(h)
        try:
            ik = initial_symmetric_sc_current_kA(
                rated_voltage_kV=13.8,
                z_thevenin_ohm=complex(0, 0),
                voltage_factor=1.0,
            )
        finally:
            logging.getLogger("app").removeHandler(h)
        assert ik == float("inf")
        msgs = " ".join(r.getMessage() for r in records)
        assert "z_thevenin" in msgs, (
            f"Expected 'z_thevenin' in log msg. Got: {msgs!r}"
        )


# ---------------------------------------------------------------------------
# Rebrand
# ---------------------------------------------------------------------------


class TestRebrand:

    def test_product_name_is_power_system_studio(self):
        from app.core.version import PRODUCT_NAME
        assert PRODUCT_NAME == "Olivas Power System Studio"

    def test_product_tagline_mentions_alternatives(self):
        from app.core.version import PRODUCT_TAGLINE
        assert "PTW" in PRODUCT_TAGLINE
        assert "ETAP" in PRODUCT_TAGLINE
        assert "EasyPower" in PRODUCT_TAGLINE

    def test_version_is_at_least_0_92_2(self):
        """v0.92.2: features deste sprint estão disponíveis em
        qualquer versão >= 0.92.2. Aceita 0.93+ porque o
        rebrand persiste."""
        from app.core.version import VERSION_TUPLE, VERSION
        assert VERSION_TUPLE >= (0, 92, 2)
        # Aceita "0.92.x" ou "0.93+" (futuras versões)
        assert VERSION.startswith(("0.92", "0.93", "0.94", "1."))

    def test_audit_trail_default_software_name(self):
        from app.postprocessor.audit_trail import make_audit_header
        h = make_audit_header(
            report_kind="Test",
            inputs={"a": 1},
            standards_applied=["IEC 60909-0"],
        )
        assert h.software_name == "Olivas Power System Studio"

    def test_welcome_dialog_title_rebrand(self, qapp_setup):
        from app.gui.welcome_dialog import WelcomeDialog
        dlg = WelcomeDialog()
        assert "Power System Studio" in dlg.windowTitle()

    def test_welcome_header_mentions_alternatives(self, qapp_setup):
        from PySide6.QtWidgets import QLabel
        from app.gui.welcome_dialog import WelcomeDialog
        dlg = WelcomeDialog()
        all_text = " ".join(
            l.text() for l in dlg.findChildren(QLabel)
        )
        assert "PTW" in all_text or "ETAP" in all_text or \
               "EasyPower" in all_text


@pytest.fixture(scope="module")
def qapp_setup():
    """v0.92.2: fixture compartilhada — QApplication para testes
    de rebrand que tocam GUI."""
    import os
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app
