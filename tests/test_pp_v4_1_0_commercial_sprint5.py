"""
tests/test_pp_v4_1_0_commercial_sprint5.py — Sprint commercial-5.

Cobre a integração Hotmart (smoke estático em TypeScript):

* Arquivos esperados existem
* Handlers do hotmart.ts cobrem 4 tipos de evento
* Idempotência implementada (findLicenseByHotmartEvent)
* E-mail templates contêm campos críticos
* Config inclui TIER_LABEL_PT e DOWNLOAD_URL_PRO
* index.ts roteia /webhook/hotmart para handleHotmartEvent
"""

from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
WORKER_SRC = PROJECT_ROOT / "infra" / "license-server" / "src"


# ---------------------------------------------------------------------------
# Existência de arquivos
# ---------------------------------------------------------------------------


class TestSprint5FilesExist:

    def test_hotmart_handler_exists(self):
        assert (WORKER_SRC / "hotmart.ts").is_file()

    def test_resend_client_exists(self):
        assert (WORKER_SRC / "resend.ts").is_file()

    def test_email_templates_exist(self):
        assert (WORKER_SRC / "email_templates.ts").is_file()


# ---------------------------------------------------------------------------
# Hotmart event coverage
# ---------------------------------------------------------------------------


REQUIRED_EVENTS = [
    "PURCHASE_APPROVED",
    "PURCHASE_REFUNDED",
    "PURCHASE_CHARGEBACK",
    "SUBSCRIPTION_CANCELLATION",
]


class TestHotmartHandler:

    def _read(self):
        return (WORKER_SRC / "hotmart.ts").read_text(encoding="utf-8")

    def test_covers_all_required_events(self):
        content = self._read()
        for ev in REQUIRED_EVENTS:
            assert f"'{ev}'" in content or f'"{ev}"' in content, (
                f"hotmart.ts não trata evento {ev}"
            )

    def test_router_has_default_case(self):
        content = self._read()
        # Default case loga e retorna ignored
        assert "default:" in content
        assert "'ignored'" in content or '"ignored"' in content

    def test_idempotency_via_event_id_lookup(self):
        content = self._read()
        # PURCHASE_APPROVED deve verificar findLicenseByHotmartEvent
        assert "findLicenseByHotmartEvent" in content
        assert "duplicate" in content

    def test_unknown_product_id_logged_and_ignored(self):
        content = self._read()
        assert "HOTMART_PRODUCT_TIER_MAP" in content
        assert "unknown_product" in content

    def test_handle_purchase_approved_signature(self):
        content = self._read()
        assert "handlePurchaseApproved" in content
        assert "handleRevocationEvent" in content
        assert "handleHotmartEvent" in content

    def test_revocation_event_calls_revoke(self):
        content = self._read()
        assert "revokeLicenseByHash" in content

    def test_sends_welcome_email_on_purchase(self):
        content = self._read()
        assert "welcomeKeyEmail" in content
        assert "sendEmail" in content

    def test_revocation_sends_notification_email(self):
        content = self._read()
        assert "revocationEmail" in content


# ---------------------------------------------------------------------------
# Email templates content
# ---------------------------------------------------------------------------


class TestEmailTemplates:

    def _read(self):
        return (WORKER_SRC / "email_templates.ts").read_text(encoding="utf-8")

    def test_welcome_email_has_required_fields(self):
        content = self._read()
        assert "welcomeKeyEmail" in content
        # Campos críticos
        for field in (
            "licenseKey",
            "tierLabel",
            "expiryDate",
            "downloadUrl",
            "maxActivations",
        ):
            assert field in content, f"Template welcome sem '{field}'"

    def test_welcome_email_pt_br(self):
        content = self._read()
        # Texto em português brasileiro
        assert "Bem-vindo" in content
        assert "Chave de licença" in content or "chave de licença" in content
        assert "Ativar" in content

    def test_welcome_email_includes_legal_links(self):
        content = self._read()
        assert "EULA" in content
        assert "PRIVACY" in content
        assert "TERMS" in content

    def test_welcome_email_includes_lgpd_dpo(self):
        content = self._read()
        assert "dpo@olivas.com.br" in content

    def test_revocation_email_present(self):
        content = self._read()
        assert "revocationEmail" in content
        assert "encerrada" in content.lower()

    def test_no_pii_leak_in_text_template(self):
        """Templates não devem incluir dados além de nome e e-mail
        do próprio destinatário."""
        content = self._read()
        # Não deve haver placeholders de CPF, endereço, telefone
        for forbidden in ("CPF", "endereço", "telefone", "RG"):
            # Permitido em comentários explicando o que NÃO é incluído.
            # Pegamos só ocorrências fora de comentários: regex grosso
            assert forbidden not in content, (
                f"Template menciona '{forbidden}' — verificar se há PII leak"
            )


# ---------------------------------------------------------------------------
# Resend client
# ---------------------------------------------------------------------------


class TestResendClient:

    def _read(self):
        return (WORKER_SRC / "resend.ts").read_text(encoding="utf-8")

    def test_uses_resend_api_endpoint(self):
        content = self._read()
        assert "api.resend.com/emails" in content

    def test_supports_html_and_text(self):
        content = self._read()
        assert "html" in content
        assert "text" in content

    def test_uses_bearer_auth(self):
        content = self._read()
        assert "Bearer" in content


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


class TestSprint5Config:

    def _read(self):
        return (WORKER_SRC / "config.ts").read_text(encoding="utf-8")

    def test_has_tier_label_pt(self):
        content = self._read()
        assert "TIER_LABEL_PT" in content
        # Labels em PT-BR
        assert "Estudante" in content
        assert "Pro Individual" in content
        assert "Pro Engenharia" in content
        assert "Empresarial" in content

    def test_has_download_url(self):
        content = self._read()
        assert "DOWNLOAD_URL_PRO" in content

    def test_has_email_from(self):
        content = self._read()
        assert "EMAIL_FROM" in content


# ---------------------------------------------------------------------------
# index.ts routing
# ---------------------------------------------------------------------------


class TestSprint5Routing:

    def _read(self):
        return (WORKER_SRC / "index.ts").read_text(encoding="utf-8")

    def test_webhook_route_delegates_to_handler(self):
        content = self._read()
        assert "handleHotmartEvent" in content
        # Não deve ter mais TODO de implementação
        assert "TODO commercial-4 W5-6" not in content

    def test_webhook_validates_hottok(self):
        content = self._read()
        assert "X-Hotmart-Hottok" in content
        assert "HOTMART_HOTTOK" in content
        assert "unauthorized" in content

    def test_webhook_validates_required_fields(self):
        content = self._read()
        assert "missing_event_fields" in content

    def test_webhook_catches_handler_errors(self):
        content = self._read()
        # try / catch + log + 500
        assert "internal_error" in content
        assert "status: 'failed'" in content or 'status: "failed"' in content
