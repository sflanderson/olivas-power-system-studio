"""
tests/test_pp_v4_1_0_commercial_sprint1.py — Sprint commercial-1.

Cobre os 3 novos módulos:

* ``app/commercial/machine_id.py``
* ``app/commercial/license_server_client.py``
* ``app/commercial/feature_gates.py``

Anti-alucinação
================

* Não testa rede real — endpoints externos são stubbed via
  monkeypatch.
* QSettings é evitado nos testes que dependem de paths puros
  (usa ``set_tier_override`` quando possível).
"""

from __future__ import annotations

import time

import pytest


# ---------------------------------------------------------------------------
# machine_id
# ---------------------------------------------------------------------------


class TestMachineId:

    def test_module_loadable(self):
        from app.commercial import machine_id  # noqa: F401

    def test_get_machine_id_returns_sha256_hex(self):
        from app.commercial.machine_id import get_machine_id

        mid = get_machine_id(force_refresh=True)
        assert isinstance(mid, str)
        assert len(mid) == 64
        # SHA256 hex usa apenas 0-9a-f
        assert all(c in "0123456789abcdef" for c in mid)

    def test_get_machine_id_is_deterministic_within_session(self):
        from app.commercial.machine_id import (
            get_machine_id, reset_machine_id_cache,
        )

        reset_machine_id_cache()
        mid1 = get_machine_id(force_refresh=True)
        mid2 = get_machine_id()  # usa cache
        assert mid1 == mid2

    def test_masked_machine_id_format(self):
        from app.commercial.machine_id import (
            get_machine_id, masked_machine_id,
        )

        get_machine_id(force_refresh=True)
        masked = masked_machine_id()
        assert "..." in masked
        # 8 chars + "..." + 8 chars
        assert len(masked) == 19

    def test_gather_hardware_signature_returns_4_components(self):
        from app.commercial.machine_id import _gather_hardware_signature

        sig = _gather_hardware_signature()
        parts = sig.split("|")
        assert len(parts) == 4


# ---------------------------------------------------------------------------
# license_server_client
# ---------------------------------------------------------------------------


class TestLicenseServerClient:

    def test_module_loadable(self):
        from app.commercial import license_server_client  # noqa: F401

    def test_check_active_license_returns_none_when_unset(
        self, monkeypatch
    ):
        from app.commercial import license_server_client as lsc

        monkeypatch.setattr(lsc, "_qsettings_read", lambda: None)
        result = lsc.check_active_license()
        assert result is None

    def test_check_active_license_returns_license_when_valid(
        self, monkeypatch
    ):
        from app.commercial import license_server_client as lsc

        future_expiry = int(time.time()) + 3600
        monkeypatch.setattr(
            lsc,
            "_qsettings_read",
            lambda: {
                "token": "fake.jwt.token",
                "tier": "commercial",
                "expiry_unix": future_expiry,
                "customer_id": "CUST123",
            },
        )
        result = lsc.check_active_license()
        assert result is not None
        assert result.tier == "commercial"
        assert result.is_active()

    def test_check_active_license_returns_none_when_expired(
        self, monkeypatch
    ):
        from app.commercial import license_server_client as lsc

        past_expiry = int(time.time()) - 3600
        monkeypatch.setattr(
            lsc,
            "_qsettings_read",
            lambda: {
                "token": "expired.jwt.token",
                "tier": "commercial",
                "expiry_unix": past_expiry,
                "customer_id": "CUST123",
            },
        )
        result = lsc.check_active_license()
        assert result is None

    def test_activate_fails_when_server_not_configured(
        self, monkeypatch
    ):
        from app.commercial import license_server_client as lsc

        monkeypatch.setattr(lsc, "get_server_url", lambda: None)
        result = lsc.activate("OLV-COMM-AA001234-20270101-ABCD1234", "MACH")
        assert result.ok is False
        assert result.error_code == "server_not_configured"

    def test_activate_fails_when_key_empty(self, monkeypatch):
        from app.commercial import license_server_client as lsc

        monkeypatch.setattr(
            lsc, "get_server_url", lambda: "https://example.test"
        )
        result = lsc.activate("", "MACH")
        assert result.ok is False
        assert result.error_code == "empty_key"

    def test_activate_success_persists_token(self, monkeypatch):
        from app.commercial import license_server_client as lsc

        future_expiry = int(time.time()) + 86400 * 30
        monkeypatch.setattr(
            lsc, "get_server_url", lambda: "https://example.test"
        )
        monkeypatch.setattr(
            lsc,
            "_post_json",
            lambda url, payload, timeout=10: {
                "token": "header.payload.sig",
                "tier": "commercial",
                "customer_id": "CUST999",
                "expiry_unix": future_expiry,
            },
        )

        written = []
        monkeypatch.setattr(
            lsc,
            "_qsettings_write",
            lambda lic: written.append(lic),
        )

        result = lsc.activate(
            "OLV-COMM-AA001234-20270101-ABCD1234", "FINGERPRINT"
        )
        assert result.ok is True
        assert result.license is not None
        assert result.license.tier == "commercial"
        assert result.license.expiry_unix == future_expiry
        assert len(written) == 1

    def test_decode_jwt_payload_handles_invalid(self):
        from app.commercial.license_server_client import _decode_jwt_payload

        assert _decode_jwt_payload("not.a.jwt") == {} or isinstance(
            _decode_jwt_payload("not.a.jwt"), dict
        )
        assert _decode_jwt_payload("invalid") == {}

    def test_verified_license_is_active(self):
        from app.commercial.license_server_client import VerifiedLicense

        future = int(time.time()) + 3600
        lic = VerifiedLicense(
            tier="commercial",
            customer_id="X",
            expiry_unix=future,
            token="t",
        )
        assert lic.is_active() is True

    def test_verified_license_not_active_when_expired(self):
        from app.commercial.license_server_client import VerifiedLicense

        past = int(time.time()) - 100
        lic = VerifiedLicense(
            tier="commercial",
            customer_id="X",
            expiry_unix=past,
            token="t",
        )
        assert lic.is_active() is False


# ---------------------------------------------------------------------------
# feature_gates
# ---------------------------------------------------------------------------


class TestFeatureGates:

    def setup_method(self):
        from app.commercial.feature_gates import set_tier_override
        set_tier_override(None)

    def teardown_method(self):
        from app.commercial.feature_gates import set_tier_override
        set_tier_override(None)

    def test_module_loadable(self):
        from app.commercial import feature_gates  # noqa: F401

    def test_default_tier_is_educational(self, monkeypatch):
        from app.commercial import feature_gates as fg

        # Garante que nenhum fallback retorna tier maior
        monkeypatch.setattr(
            "app.commercial.license_server_client.check_active_license",
            lambda: None,
        )
        # E que QSettings legacy também não acha chave
        try:
            from PySide6.QtCore import QSettings
            settings = QSettings("OlivasATPStudio", "OlivasATPStudio")
            settings.remove("commercial/legacy_license_key")
            settings.sync()
        except ImportError:
            pass

        assert fg.current_tier() == "educational"

    def test_set_tier_override_works(self):
        from app.commercial.feature_gates import (
            current_tier, set_tier_override,
        )

        set_tier_override("commercial")
        assert current_tier() == "commercial"

        set_tier_override("enterprise")
        assert current_tier() == "enterprise"

    def test_is_feature_available_for_audit_trail(self):
        from app.commercial.feature_gates import (
            Feature, is_feature_available, set_tier_override,
        )

        set_tier_override("educational")
        assert is_feature_available(Feature.AUDIT_TRAIL_SHA256) is False

        set_tier_override("commercial")
        assert is_feature_available(Feature.AUDIT_TRAIL_SHA256) is True

    def test_is_feature_available_for_unknown_returns_true(self):
        from app.commercial.feature_gates import (
            is_feature_available, set_tier_override,
        )

        set_tier_override("educational")
        # Feature não catalogada → não bloqueia
        assert is_feature_available("uncatalogued_x") is True

    def test_require_feature_raises_when_insufficient(self):
        from app.commercial.feature_gates import (
            Feature, LicenseRequiredError, require_feature, set_tier_override,
        )

        set_tier_override("educational")
        with pytest.raises(LicenseRequiredError) as exc:
            require_feature(Feature.AI_LAUDO)
        assert exc.value.feature == Feature.AI_LAUDO
        assert exc.value.required_tier == "commercial"
        assert exc.value.current_tier == "educational"

    def test_require_feature_passes_when_tier_sufficient(self):
        from app.commercial.feature_gates import (
            Feature, require_feature, set_tier_override,
        )

        set_tier_override("commercial")
        require_feature(Feature.AI_LAUDO)  # não deve raise

        set_tier_override("enterprise")
        require_feature(Feature.AI_LAUDO)  # tier acima também passa

    def test_requires_tier_decorator(self):
        from app.commercial.feature_gates import (
            LicenseRequiredError, requires_tier, set_tier_override,
        )

        @requires_tier("commercial")
        def generate_pdf():
            return "ok"

        set_tier_override("educational")
        with pytest.raises(LicenseRequiredError):
            generate_pdf()

        set_tier_override("commercial")
        assert generate_pdf() == "ok"

    def test_requires_tier_rejects_invalid_tier_name(self):
        from app.commercial.feature_gates import requires_tier

        with pytest.raises(ValueError):
            @requires_tier("ultra_premium_xyz")
            def f():
                pass

    def test_requires_feature_decorator(self):
        from app.commercial.feature_gates import (
            Feature, LicenseRequiredError, requires_feature, set_tier_override,
        )

        @requires_feature(Feature.PREMIUM_RELAY_LIBRARY)
        def get_relay(brand):
            return f"relay-{brand}"

        # Commercial não basta para pro_engineering
        set_tier_override("commercial")
        with pytest.raises(LicenseRequiredError):
            get_relay("SEL")

        set_tier_override("pro_engineering")
        assert get_relay("SEL") == "relay-SEL"

    def test_tier_hierarchy_enterprise_includes_lower(self):
        from app.commercial.feature_gates import (
            Feature, is_feature_available, set_tier_override,
        )

        set_tier_override("enterprise")
        assert is_feature_available(Feature.AUDIT_TRAIL_SHA256) is True
        assert is_feature_available(Feature.AI_LAUDO) is True
        assert is_feature_available(Feature.PREMIUM_RELAY_LIBRARY) is True
        assert is_feature_available(Feature.MULTI_SEAT) is True

    def test_tier_hierarchy_educational_blocks_all_paid(self):
        from app.commercial.feature_gates import (
            FEATURE_TIER_MAP, is_feature_available, set_tier_override,
        )

        set_tier_override("educational")
        for feature in FEATURE_TIER_MAP.keys():
            assert is_feature_available(feature) is False, (
                f"Feature {feature} should be blocked at educational"
            )


# ---------------------------------------------------------------------------
# Integration: gates aplicados nos pontos quentes
# ---------------------------------------------------------------------------


class TestGatesIntegration:
    """
    Prova que ``@requires_feature`` está realmente protegendo as
    funções dos módulos comerciáveis. Cada teste força tier
    ``educational`` e verifica que a função levanta
    ``LicenseRequiredError``.
    """

    def setup_method(self):
        from app.commercial.feature_gates import set_tier_override
        set_tier_override("educational")

    def teardown_method(self):
        from app.commercial.feature_gates import set_tier_override
        set_tier_override(None)

    def test_audit_trail_blocked_at_educational(self):
        from app.commercial.feature_gates import LicenseRequiredError
        from app.postprocessor.audit_trail import make_audit_header

        with pytest.raises(LicenseRequiredError) as exc:
            make_audit_header(
                report_kind="curto-circuito",
                inputs={"S_kQ_MVA": 250.0},
                standards_applied=["IEC 60909-0:2016"],
            )
        assert exc.value.feature == "audit_trail_sha256"

    def test_report_html_blocked_at_educational(self):
        from app.commercial.feature_gates import LicenseRequiredError
        from app.postprocessor.report_html import generate_html_report

        # Stub mínimo de BusPipelineReport (não vai ser usado pois
        # decorator dispara antes do corpo da função)
        class _StubReport:
            pass

        with pytest.raises(LicenseRequiredError):
            generate_html_report(_StubReport())  # type: ignore[arg-type]

    def test_reliability_mc_blocked_at_educational(self):
        from app.commercial.feature_gates import LicenseRequiredError
        from app.postprocessor.reliability_monte_carlo import run_monte_carlo

        with pytest.raises(LicenseRequiredError):
            run_monte_carlo([])

    def test_arc_flash_mc_blocked_at_educational(self):
        from app.commercial.feature_gates import LicenseRequiredError
        from app.postprocessor.arc_flash_monte_carlo import (
            ArcFlashUncertainty, run_monte_carlo,
        )

        with pytest.raises(LicenseRequiredError):
            run_monte_carlo(
                base_case=None,
                uncertainty=ArcFlashUncertainty(),
            )

    def test_pf_mc_blocked_at_educational(self):
        from app.commercial.feature_gates import LicenseRequiredError
        from app.postprocessor.power_flow_monte_carlo import (
            PfUncertainty, run_pf_monte_carlo,
        )

        with pytest.raises(LicenseRequiredError):
            run_pf_monte_carlo(
                pf_system=None,
                uncertainty=PfUncertainty(),
            )

    def test_gates_passthrough_at_enterprise(self):
        """Tier enterprise deve permitir todos os gates."""
        from app.commercial.feature_gates import (
            Feature, is_feature_available, set_tier_override,
        )

        set_tier_override("enterprise")
        assert is_feature_available(Feature.AUDIT_TRAIL_SHA256)
        assert is_feature_available(Feature.PDF_PROFESSIONAL)
        assert is_feature_available(Feature.RELIABILITY_MC)
        assert is_feature_available(Feature.ARC_FLASH_MC)
        assert is_feature_available(Feature.POWER_FLOW_MC)
