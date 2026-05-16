"""
tests/test_pp_v2_0_0_iec61850.py — v2.0.0 Sprint B.

Cobre o módulo ``app.integration.iec61850_client``:

* Stub mode (gera dados sintéticos)
* Configuração via dataclass
* Recepção de MMSReport com timestamp + measurements
"""

from __future__ import annotations

from datetime import datetime

import pytest


class TestIEC61850Module:

    def test_module_loadable(self):
        from app.integration import iec61850_client  # noqa: F401


class TestIEC61850Config:

    def test_config_dataclass(self):
        from app.integration.iec61850_client import (
            IEC61850MMSConfig,
        )
        cfg = IEC61850MMSConfig(
            host="192.168.1.100",
            port=102,
            ied_name="IED_BAY_01",
            mode="stub",
        )
        assert cfg.host == "192.168.1.100"
        assert cfg.port == 102
        assert cfg.mode == "stub"


class TestIEC61850StubClient:

    def test_stub_client_generates_synthetic_data(self):
        from app.integration.iec61850_client import (
            IEC61850MMSClient, IEC61850MMSConfig,
        )
        cfg = IEC61850MMSConfig(
            host="dummy", port=102, ied_name="IED-TEST",
            mode="stub",
        )
        client = IEC61850MMSClient(cfg)
        report = client.get_report()
        # Stub gera dados realistas
        assert report is not None
        assert report.ied_name == "IED-TEST"
        assert isinstance(report.timestamp, datetime)
        # Pelo menos algumas medições padrão
        assert len(report.measurements) >= 1

    def test_stub_voltage_in_typical_range(self):
        from app.integration.iec61850_client import (
            IEC61850MMSClient, IEC61850MMSConfig,
        )
        cfg = IEC61850MMSConfig(
            host="dummy", port=102, ied_name="IED-V",
            mode="stub",
        )
        client = IEC61850MMSClient(cfg)
        report = client.get_report()
        # Voltage measurement deve existir e estar em range típico
        v_meas = [
            m for m in report.measurements
            if m.name.lower().startswith("v") or "voltage" in m.name.lower()
        ]
        assert len(v_meas) >= 1
        # Todas em range razoável (kV)
        for m in v_meas:
            assert 0.0 < m.value < 800.0


class TestIEC61850RealMode:

    def test_real_mode_raises_without_lib(self):
        """Real mode exige libiec61850 — sem ela, raise informativo."""
        from app.integration.iec61850_client import (
            IEC61850MMSClient, IEC61850MMSConfig,
        )
        cfg = IEC61850MMSConfig(
            host="192.168.1.100", port=102,
            ied_name="IED-REAL", mode="real",
        )
        client = IEC61850MMSClient(cfg)
        # Sem lib, get_report no real mode raise NotImplementedError
        # com mensagem instrutiva
        with pytest.raises((NotImplementedError, ImportError, Exception)):
            client.get_report()


class TestMMSReport:

    def test_report_is_immutable(self):
        from app.integration.iec61850_client import (
            MMSReport, MMSMeasurement,
        )
        report = MMSReport(
            ied_name="X",
            timestamp=datetime.now(),
            measurements=(
                MMSMeasurement(
                    name="V_RMS_A", value=13.8, unit="kV",
                ),
            ),
        )
        # Frozen dataclass
        with pytest.raises(Exception):
            report.ied_name = "Y"
