"""
tests/test_pp_v4_1_0_commercial_sprint4.py — Sprint commercial-4.

Cobre os documentos jurídicos em ``legal/``:

* Existem
* Têm cabeçalhos e seções obrigatórias
* Contêm disclaimer de "modelo pré-revisão jurídica"
* Mencionam LGPD, foro BH/MG, idioma PT
* CLA preserva dual licensing
"""

from __future__ import annotations

from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parent.parent
LEGAL_DIR = PROJECT_ROOT / "legal"


# ---------------------------------------------------------------------------
# Existência
# ---------------------------------------------------------------------------


REQUIRED_DOCS = ["README.md", "EULA.md", "TERMS.md", "PRIVACY_LGPD.md",
                 "SLA.md", "CLA.md"]


class TestDocsExist:

    @pytest.mark.parametrize("doc", REQUIRED_DOCS)
    def test_doc_file_exists(self, doc):
        assert (LEGAL_DIR / doc).is_file(), (
            f"Documento {doc} ausente em legal/"
        )

    @pytest.mark.parametrize("doc", REQUIRED_DOCS)
    def test_doc_non_trivial_size(self, doc):
        size = (LEGAL_DIR / doc).stat().st_size
        assert size > 500, (
            f"Documento {doc} suspeitamente pequeno ({size} bytes)"
        )


# ---------------------------------------------------------------------------
# Disclaimer "modelo pré-revisão"
# ---------------------------------------------------------------------------


REVIEWABLE_DOCS = ["EULA.md", "TERMS.md", "PRIVACY_LGPD.md", "SLA.md", "CLA.md"]


class TestDisclaimers:

    @pytest.mark.parametrize("doc", REVIEWABLE_DOCS)
    def test_doc_carries_pre_review_warning(self, doc):
        content = (LEGAL_DIR / doc).read_text(encoding="utf-8")
        assert "AVISO" in content
        assert "modelo" in content.lower()
        assert "advogado" in content.lower()

    @pytest.mark.parametrize("doc", REVIEWABLE_DOCS)
    def test_doc_states_status_as_pre_review(self, doc):
        content = (LEGAL_DIR / doc).read_text(encoding="utf-8")
        assert "pré-revisão" in content.lower() or "pre-revisao" in content.lower()


# ---------------------------------------------------------------------------
# Foro + lei
# ---------------------------------------------------------------------------


FORO_DOCS = ["EULA.md", "TERMS.md", "PRIVACY_LGPD.md", "SLA.md", "CLA.md"]


class TestForo:

    @pytest.mark.parametrize("doc", FORO_DOCS)
    def test_belo_horizonte_jurisdiction(self, doc):
        content = (LEGAL_DIR / doc).read_text(encoding="utf-8")
        assert "Belo Horizonte" in content or "MG" in content


# ---------------------------------------------------------------------------
# Conteúdo específico LGPD
# ---------------------------------------------------------------------------


class TestPrivacyLGPD:

    def test_mentions_lgpd_law_number(self):
        content = (LEGAL_DIR / "PRIVACY_LGPD.md").read_text(encoding="utf-8")
        assert "13.709" in content

    def test_lists_titular_rights(self):
        content = (LEGAL_DIR / "PRIVACY_LGPD.md").read_text(encoding="utf-8")
        # Art. 18 LGPD direitos
        assert "Art. 18" in content
        # Confirmação, acesso, correção, portabilidade
        for keyword in ("Confirmar", "Acessar", "Corrigir", "Portabilidade"):
            assert keyword in content, f"Falta direito '{keyword}'"

    def test_declares_dpo(self):
        content = (LEGAL_DIR / "PRIVACY_LGPD.md").read_text(encoding="utf-8")
        assert "DPO" in content or "Encarregado" in content

    def test_declares_legal_bases(self):
        content = (LEGAL_DIR / "PRIVACY_LGPD.md").read_text(encoding="utf-8")
        assert "Art. 7" in content
        # Bases legais comuns
        for base in ("consentimento", "execução de contrato", "legítimo interesse"):
            assert base in content.lower()

    def test_declares_retention_periods(self):
        content = (LEGAL_DIR / "PRIVACY_LGPD.md").read_text(encoding="utf-8")
        assert "retenção" in content.lower()
        assert "5 anos" in content or "12 meses" in content

    def test_lists_processors(self):
        content = (LEGAL_DIR / "PRIVACY_LGPD.md").read_text(encoding="utf-8")
        for op in ("Hotmart", "Cloudflare", "Supabase"):
            assert op in content

    def test_declares_machine_id_is_hash(self):
        content = (LEGAL_DIR / "PRIVACY_LGPD.md").read_text(encoding="utf-8")
        assert "SHA256" in content
        assert "Machine ID" in content or "machine_id" in content


# ---------------------------------------------------------------------------
# EULA
# ---------------------------------------------------------------------------


class TestEULA:

    def test_dual_licensing_explained(self):
        content = (LEGAL_DIR / "EULA.md").read_text(encoding="utf-8")
        # Deve diferenciar Apache 2.0 (Community) de EULA (Pro)
        assert "Apache" in content
        assert "Community" in content
        assert "Pro" in content

    def test_lists_tier_max_activations(self):
        content = (LEGAL_DIR / "EULA.md").read_text(encoding="utf-8")
        # Esperado: Estudante / Pro Individual / Pro Engenharia / Empresarial
        assert "Estudante" in content
        assert "Pro Individual" in content
        assert "Pro Engenharia" in content
        assert "Empresarial" in content

    def test_professional_disclaimer(self):
        """5.2 — laudos exigem engenheiro habilitado."""
        content = (LEGAL_DIR / "EULA.md").read_text(encoding="utf-8")
        assert "engenheiro" in content.lower()
        assert "CREA" in content
        assert "NR-10" in content

    def test_cdc_7_days_refund(self):
        """Art. 49 CDC — direito de arrependimento."""
        content = (LEGAL_DIR / "EULA.md").read_text(encoding="utf-8")
        assert "7" in content
        assert "Art. 49" in content
        assert "Código de Defesa do Consumidor" in content or "CDC" in content

    def test_forbids_reverse_engineering(self):
        content = (LEGAL_DIR / "EULA.md").read_text(encoding="utf-8")
        # Permite quando lei imperativa autoriza
        assert "engenharia reversa" in content.lower()
        assert "9.609" in content  # Lei do Software

    def test_limits_liability(self):
        content = (LEGAL_DIR / "EULA.md").read_text(encoding="utf-8")
        assert "responsabilidade" in content.lower()
        # Limitada a 2x valor pago
        assert "2 (duas) vezes" in content or "2x" in content


# ---------------------------------------------------------------------------
# CLA
# ---------------------------------------------------------------------------


class TestCLA:

    def test_preserves_dual_licensing(self):
        """CLA permite que o Licenciante distribua sob Apache OU
        proprietária — chave para o modelo de negócio."""
        content = (LEGAL_DIR / "CLA.md").read_text(encoding="utf-8")
        assert "Apache" in content
        assert "proprietária" in content.lower() or "proprietary" in content.lower()
        assert "qualquer outra licença" in content.lower()

    def test_grants_perpetual_irrevocable(self):
        content = (LEGAL_DIR / "CLA.md").read_text(encoding="utf-8")
        assert "perpétua" in content.lower()
        assert "irrevogável" in content.lower()

    def test_grants_patent_license(self):
        content = (LEGAL_DIR / "CLA.md").read_text(encoding="utf-8")
        assert "patente" in content.lower()

    def test_signoff_instructions(self):
        content = (LEGAL_DIR / "CLA.md").read_text(encoding="utf-8")
        assert "Signed-off-by" in content
        assert "CLA-Accepted" in content


# ---------------------------------------------------------------------------
# README / índice
# ---------------------------------------------------------------------------


class TestLegalReadme:

    def test_lists_all_docs(self):
        content = (LEGAL_DIR / "README.md").read_text(encoding="utf-8")
        for doc in REVIEWABLE_DOCS:
            assert doc in content

    def test_explains_community_vs_pro(self):
        content = (LEGAL_DIR / "README.md").read_text(encoding="utf-8")
        assert "Community" in content
        assert "Pro" in content
        assert "Apache" in content
        assert "EULA" in content

    def test_eula_acceptance_flow_documented(self):
        content = (LEGAL_DIR / "README.md").read_text(encoding="utf-8")
        assert "aceite" in content.lower()
        assert "QSettings" in content or "primeira execução" in content.lower()


# ---------------------------------------------------------------------------
# TERMS
# ---------------------------------------------------------------------------


class TestTerms:

    def test_describes_service(self):
        content = (LEGAL_DIR / "TERMS.md").read_text(encoding="utf-8")
        # license server + updates
        assert "license server" in content.lower() or "servidor de licença" in content.lower()
        assert "atualizações" in content.lower() or "atualizacoes" in content.lower()

    def test_describes_no_remote_processing(self):
        """Não processamos dados elétricos no servidor."""
        content = (LEGAL_DIR / "TERMS.md").read_text(encoding="utf-8")
        assert "localmente" in content.lower() or "máquina" in content.lower()

    def test_offline_grace_period_30_days(self):
        content = (LEGAL_DIR / "TERMS.md").read_text(encoding="utf-8")
        # Token JWT vale 30 dias offline
        assert "30 dias" in content or "trinta dias" in content.lower()


# ---------------------------------------------------------------------------
# SLA
# ---------------------------------------------------------------------------


class TestSLA:

    def test_states_uptime_targets(self):
        content = (LEGAL_DIR / "SLA.md").read_text(encoding="utf-8")
        assert "99" in content
        # Métricas separadas
        assert "/activate" in content

    def test_severity_levels(self):
        content = (LEGAL_DIR / "SLA.md").read_text(encoding="utf-8")
        for sev in ("S1", "S2", "S3", "S4"):
            assert sev in content

    def test_credit_table(self):
        content = (LEGAL_DIR / "SLA.md").read_text(encoding="utf-8")
        assert "Crédito" in content or "Compensação" in content
