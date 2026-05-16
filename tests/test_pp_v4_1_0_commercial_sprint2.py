"""
tests/test_pp_v4_1_0_commercial_sprint2.py — Sprint commercial-2.

Cobre:
* app/gui/license_dialog.py — smoke + helpers
* main_window menu Ajuda → Ativar Licença
* license_server_client.try_refresh
"""

from __future__ import annotations

import os
import sys
import time

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication(sys.argv)


# ---------------------------------------------------------------------------
# license_dialog smoke
# ---------------------------------------------------------------------------


class TestLicenseDialog:

    def test_module_loadable(self):
        from app.gui import license_dialog  # noqa: F401

    def test_human_error_known_codes(self):
        from app.gui.license_dialog import _human_error

        msg = _human_error("invalid_key", None)
        assert "Chave inválida" in msg

        msg = _human_error("max_activations_exceeded", None)
        assert "máximo permitido" in msg

        msg = _human_error("network_error", None)
        assert "conexão" in msg.lower()

    def test_human_error_http_code_passthrough(self):
        from app.gui.license_dialog import _human_error

        msg = _human_error("http_500", "Internal Server Error")
        assert "500" in msg
        assert "Internal Server Error" in msg

    def test_human_error_unknown_returns_message(self):
        from app.gui.license_dialog import _human_error

        msg = _human_error(None, "alguma falha")
        assert msg == "alguma falha"

        msg = _human_error("totally_made_up_code", None)
        # Fallback: "Falha desconhecida"
        assert "desconhecida" in msg.lower()

    def test_dialog_constructs(self, qapp):
        from app.gui.license_dialog import LicenseDialog

        dlg = LicenseDialog()
        assert dlg.windowTitle().startswith("Ativar Licença")
        assert dlg.minimumWidth() >= 500
        dlg.close()

    def test_dialog_shows_educational_when_no_license(
        self, qapp, monkeypatch
    ):
        from app.commercial.feature_gates import set_tier_override
        set_tier_override("educational")
        try:
            monkeypatch.setattr(
                "app.commercial.license_server_client.check_active_license",
                lambda: None,
            )
            from app.gui.license_dialog import LicenseDialog
            dlg = LicenseDialog()
            text = dlg._status_label.text()
            assert "educational" in text
            assert "bloqueadas" in text.lower()
            dlg.close()
        finally:
            set_tier_override(None)

    def test_dialog_shows_active_license(self, qapp, monkeypatch):
        from app.commercial.feature_gates import set_tier_override
        from app.commercial.license_server_client import VerifiedLicense

        set_tier_override("commercial")
        try:
            future = int(time.time()) + 86400 * 15
            monkeypatch.setattr(
                "app.commercial.license_server_client.check_active_license",
                lambda: VerifiedLicense(
                    tier="commercial",
                    customer_id="CUST42",
                    expiry_unix=future,
                    token="t.t.t",
                ),
            )
            monkeypatch.setattr(
                "app.commercial.license_server_client.days_until_expiry",
                lambda: 15,
            )
            from app.gui.license_dialog import LicenseDialog
            dlg = LicenseDialog()
            text = dlg._status_label.text()
            assert "ativa" in text.lower()
            assert "commercial" in text
            assert "CUST42" in text
            assert "15 dias" in text
            dlg.close()
        finally:
            set_tier_override(None)


# ---------------------------------------------------------------------------
# license_server_client.try_refresh edge cases
# ---------------------------------------------------------------------------


class TestTryRefresh:

    def test_try_refresh_without_server_url(self, monkeypatch):
        from app.commercial import license_server_client as lsc

        monkeypatch.setattr(lsc, "get_server_url", lambda: None)
        result = lsc.try_refresh()
        assert result.ok is False
        assert result.error_code == "server_not_configured"

    def test_try_refresh_without_local_token(self, monkeypatch):
        from app.commercial import license_server_client as lsc

        monkeypatch.setattr(
            lsc, "get_server_url", lambda: "https://example.test"
        )
        monkeypatch.setattr(lsc, "_qsettings_read", lambda: None)
        result = lsc.try_refresh()
        assert result.ok is False
        assert result.error_code == "no_local_token"

    def test_try_refresh_success_updates_token(self, monkeypatch):
        from app.commercial import license_server_client as lsc

        future = int(time.time()) + 86400 * 30
        monkeypatch.setattr(
            lsc, "get_server_url", lambda: "https://example.test"
        )
        monkeypatch.setattr(
            lsc,
            "_qsettings_read",
            lambda: {
                "token": "old.jwt.token",
                "tier": "commercial",
                "expiry_unix": int(time.time()) + 3600,
                "customer_id": "CUST7",
            },
        )
        monkeypatch.setattr(
            lsc,
            "_post_json",
            lambda url, payload, timeout=10: {
                "token": "new.jwt.token",
                "tier": "commercial",
                "customer_id": "CUST7",
                "expiry_unix": future,
            },
        )

        written = []
        monkeypatch.setattr(
            lsc,
            "_qsettings_write",
            lambda lic: written.append(lic),
        )

        result = lsc.try_refresh()
        assert result.ok is True
        assert result.license is not None
        assert result.license.token == "new.jwt.token"
        assert result.license.expiry_unix == future
        assert len(written) == 1


# ---------------------------------------------------------------------------
# Worker route descriptions — sanity (sem rede)
# ---------------------------------------------------------------------------


class TestWorkerArtifacts:
    """Confirma que os arquivos do Worker estão presentes e
    contêm os endpoints esperados (smoke estático)."""

    def test_index_ts_has_routes(self):
        from pathlib import Path
        idx = Path(__file__).parent.parent / "infra" / "license-server" / "src" / "index.ts"
        assert idx.is_file()
        content = idx.read_text(encoding="utf-8")
        assert "app.get('/health'" in content
        assert "app.post('/activate'" in content
        assert "app.post('/refresh'" in content
        assert "app.post('/revoke'" in content
        assert "app.post('/webhook/hotmart'" in content
        # /refresh e /revoke saíram do stub 501:
        assert "not_implemented" not in content.split("/webhook/hotmart")[0]

    def test_schema_has_three_tables(self):
        from pathlib import Path
        sql = Path(__file__).parent.parent / "infra" / "license-server" / "db" / "schema.sql"
        assert sql.is_file()
        content = sql.read_text(encoding="utf-8")
        assert "create table if not exists licenses" in content
        assert "create table if not exists activations" in content
        assert "create table if not exists webhooks_log" in content
