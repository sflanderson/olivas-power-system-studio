"""
tests/test_pp_v2_0_0_commercial.py — v2.0.0 Sprint D.

Cobre commercial features:

* License key validation (HMAC-SHA256)
* Telemetry opt-in (anonymous usage stats)
"""

from __future__ import annotations

import pytest


class TestLicenseKey:

    def test_module_loadable(self):
        from app.commercial import license_key  # noqa: F401

    def test_validate_empty_key_returns_education_tier(self):
        """Sem chave = tier educational (default, não block)."""
        from app.commercial.license_key import validate_license_key
        result = validate_license_key("")
        assert result.tier == "educational"
        assert result.valid is True   # educational é válido (sem
                                       # chave também é OK)

    def test_validate_invalid_key_returns_invalid(self):
        from app.commercial.license_key import validate_license_key
        result = validate_license_key("RANDOM-INVALID-XYZ")
        assert result.valid is False

    def test_validate_demo_key_returns_demo_tier(self):
        """Chave demo embutida (anti-alucinação: sem inventar
        chaves comerciais reais)."""
        from app.commercial.license_key import (
            DEMO_KEY, validate_license_key,
        )
        result = validate_license_key(DEMO_KEY)
        assert result.valid is True
        assert result.tier in ("demo", "educational")


class TestTelemetry:

    def test_telemetry_loadable(self):
        from app.commercial import telemetry  # noqa: F401

    def test_telemetry_default_opt_out(self):
        """Default = OFF (privacy first). User precisa opt-in."""
        from app.commercial.telemetry import (
            is_telemetry_enabled, reset_telemetry,
        )
        reset_telemetry()
        assert is_telemetry_enabled() is False

    def test_telemetry_opt_in(self):
        from app.commercial.telemetry import (
            enable_telemetry, is_telemetry_enabled, reset_telemetry,
        )
        reset_telemetry()
        enable_telemetry()
        assert is_telemetry_enabled() is True
        reset_telemetry()

    def test_telemetry_record_event_when_disabled(self):
        """Quando OFF, record_event é no-op (não cria nada)."""
        from app.commercial.telemetry import (
            record_event, reset_telemetry,
        )
        reset_telemetry()
        # Não deve raise mesmo com telemetry off
        record_event("test_event")

    def test_telemetry_anonymous_format(self):
        """Eventos não contêm PII (anti-tracking)."""
        from app.commercial.telemetry import (
            enable_telemetry, record_event, get_recent_events,
            reset_telemetry,
        )
        reset_telemetry()
        enable_telemetry()
        record_event("study_run")
        events = get_recent_events()
        # Cada evento é anônimo
        for ev in events:
            assert "name" in ev
            # NÃO deve ter user_id, ip, hostname, etc
            assert "user_id" not in ev
            assert "ip_address" not in ev
            assert "hostname" not in ev
        reset_telemetry()
