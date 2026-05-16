"""
tests/test_pp_vcb_model.py — v0.22.1: emissão MODEL de reignição
para VCB/VCB3.

Cobre:

* Carregamento do template ``vcb_reignition.mod``.
* Detecção heurística ``vcb_needs_model()`` (default → False,
  customizado → True).
* Construção de USE block com DATA values corretas vindas das
  properties.
* Integração end-to-end em ``bridge_to_atp.to_atp()`` — a seção
  ``/MODELS`` aparece ANTES de ``/BRANCH`` no raw_lines, e os
  índices das sections BRANCH/SWITCH/SOURCE continuam válidos
  após o shift.

NÃO cobre (fora de escopo v0.22.1):
- Execução do ATP solver (MVP ainda não executa .atp).
- Wiring TACS automático (v0.22.2).
- Validação semântica do código MODELS (requer parser ATP-EMTP).
"""

from __future__ import annotations

import pytest

from app.core.serializer import serialize_project
from app.preprocessor.bridge_to_atp import to_atp
from app.preprocessor.models import PpComponent, PpProject, PpProperty
from app.preprocessor.vcb_model_emitter import (
    VCB3_REIGNITION_PROPS,
    VCB_REIGNITION_DEFAULTS,
    VCB_REIGNITION_PROPS,
    build_models_section,
    build_use_block,
    load_reignition_template,
    vcb_needs_model,
)


# ---------------------------------------------------------------------------
# Helpers de construção
# ---------------------------------------------------------------------------


def _make_vcb(name: str, props: list[str]) -> PpComponent:
    """Cria um VCB 1φ com properties fornecidas (10 slots)."""
    assert len(props) == 10
    return PpComponent(
        type="VCB", name=name, visible=True, x=0, y=0,
        label_dx=0, label_dy=0, mirror=0, rotation=0,
        properties=[PpProperty(p) for p in props],
    )


def _make_vcb3(name: str, props: list[str]) -> PpComponent:
    """Cria um VCB 3φ com 14 properties."""
    assert len(props) == 14
    return PpComponent(
        type="VCB3", name=name, visible=True, x=0, y=0,
        label_dx=0, label_dy=0, mirror=0, rotation=0,
        properties=[PpProperty(p) for p in props],
    )


def _default_vcb_props() -> list[str]:
    """Properties default do VCB 1φ — correspondem aos defaults CIGRE."""
    return [
        "0", "1e9",            # T_open, T_close
        "5.0", "1.0",          # I_chop, sigma
        "16.0", "0.034",       # di/dt, didt_sigma
        "17.0", "690.0",       # k_dielec, U0
        "5e-4", "1",           # T_bounce, Seed
    ]


def _default_vcb3_props() -> list[str]:
    """Properties default do VCB 3φ."""
    return [
        "0.05", "1e9",         # T_open_A, T_close_A
        "0.05", "1e9",         # T_open_B, T_close_B
        "0.05", "1e9",         # T_open_C, T_close_C
        "5.0", "1.0",          # I_chop, sigma
        "16.0", "0.034",       # di/dt, didt_sigma
        "17.0", "690.0",       # k_dielec, U0
        "5e-4", "1",           # T_bounce, Seed
    ]


# ---------------------------------------------------------------------------
# Template: carregamento e conteúdo mínimo
# ---------------------------------------------------------------------------


class TestTemplateLoading:
    def test_template_is_loadable(self):
        text = load_reignition_template()
        assert isinstance(text, str)
        assert len(text) > 100  # não-trivial

    def test_template_contains_MODEL_keyword(self):
        text = load_reignition_template()
        assert "MODEL vcb_reignition" in text
        assert "ENDMODEL" in text

    def test_template_contains_all_DATA_params(self):
        """Os 8 params CIGRE + T_open devem estar declarados em DATA."""
        text = load_reignition_template()
        expected = {
            "I_chop_mean", "I_chop_sigma",
            "didt_crit_0", "didt_sigma",
            "k_dielec", "U0_dielec",
            "T_bounce", "T_open", "Seed",
        }
        for param in expected:
            assert param in text, f"Template sem DATA {param!r}"

    def test_template_references_CIGRE(self):
        """Traceability: o template deve citar CIGRE WG A3.26."""
        text = load_reignition_template()
        assert "CIGRE" in text
        assert "A3.26" in text

    def test_template_has_INPUT_OUTPUT(self):
        text = load_reignition_template()
        assert "INPUT" in text
        assert "OUTPUT" in text
        assert "switch_cmd" in text  # output esperado


# ---------------------------------------------------------------------------
# vcb_needs_model() heurística
# ---------------------------------------------------------------------------


class TestVcbNeedsModel:
    def test_vcb_with_all_defaults_does_not_need_model(self):
        vcb = _make_vcb("DJ1", _default_vcb_props())
        assert vcb_needs_model(vcb) is False

    def test_vcb_with_customized_I_chop_needs_model(self):
        props = _default_vcb_props()
        props[2] = "8.0"  # I_chop customizado
        vcb = _make_vcb("DJ1", props)
        assert vcb_needs_model(vcb) is True

    def test_vcb_with_customized_kdielec_needs_model(self):
        props = _default_vcb_props()
        props[6] = "25.0"  # k_dielec customizado
        vcb = _make_vcb("DJ1", props)
        assert vcb_needs_model(vcb) is True

    def test_vcb_with_empty_properties_does_not_need_model(self):
        """Properties vazias são tratadas como não-customizadas."""
        props = _default_vcb_props()
        props[2] = ""
        props[3] = ""
        vcb = _make_vcb("DJ1", props)
        assert vcb_needs_model(vcb) is False

    def test_vcb3_with_all_defaults_does_not_need_model(self):
        vcb3 = _make_vcb3("DJ3", _default_vcb3_props())
        assert vcb_needs_model(vcb3) is False

    def test_vcb3_with_customized_didt_needs_model(self):
        props = _default_vcb3_props()
        props[8] = "25.0"  # di/dt customizado
        vcb3 = _make_vcb3("DJ3", props)
        assert vcb_needs_model(vcb3) is True

    def test_non_vcb_component_never_needs_model(self):
        r = PpComponent(
            type="R", name="R1", visible=True, x=0, y=0,
            label_dx=0, label_dy=0, mirror=0, rotation=0,
            properties=[PpProperty("100")],
        )
        assert vcb_needs_model(r) is False


# ---------------------------------------------------------------------------
# build_use_block()
# ---------------------------------------------------------------------------


class TestBuildUseBlock:
    def test_use_block_has_correct_structure(self):
        props = _default_vcb_props()
        props[2] = "8.0"
        vcb = _make_vcb("DJ1", props)
        lines = build_use_block(vcb, "DJ1", "0.05")
        # Verifica estrutura básica.
        text = "\n".join(lines)
        assert "USE vcb_reignition AS DJ1" in text
        assert "INPUT" in text
        assert "DATA" in text
        assert "OUTPUT" in text
        assert "ENDUSE" in text

    def test_use_block_propagates_customized_I_chop(self):
        props = _default_vcb_props()
        props[2] = "8.5"
        vcb = _make_vcb("DJ1", props)
        lines = build_use_block(vcb, "DJ1", "0.05")
        text = "\n".join(lines)
        # O DATA de I_chop_mean deve pegar o valor customizado.
        assert "I_chop_mean := 8.5" in text

    def test_use_block_uses_defaults_when_empty(self):
        """Properties vazias → caem nos defaults CIGRE declarados no emitter."""
        props = _default_vcb_props()
        props[2] = ""  # vazio
        vcb = _make_vcb("DJ1", props)
        lines = build_use_block(vcb, "DJ1", "0.05")
        text = "\n".join(lines)
        # Default é "5.0" conforme VCB_REIGNITION_DEFAULTS["I_chop_mean"]
        assert f"I_chop_mean := {VCB_REIGNITION_DEFAULTS['I_chop_mean']}" in text

    def test_use_block_t_open_uses_passed_value(self):
        """T_open vem do argumento (não da property) — importante para
        VCB3 onde cada fase tem T_open próprio."""
        vcb = _make_vcb("DJ1", _default_vcb_props())
        lines = build_use_block(vcb, "DJ1", "0.123")
        text = "\n".join(lines)
        assert "T_open := 0.123" in text

    def test_use_block_for_vcb3_includes_phase_comment(self):
        vcb3 = _make_vcb3("DJ3", _default_vcb3_props())
        lines = build_use_block(vcb3, "DJ3_A", "0.05", phase="A")
        text = "\n".join(lines)
        assert "fase A" in text

    def test_use_block_rejects_non_vcb(self):
        r = PpComponent(
            type="R", name="R1", visible=True, x=0, y=0,
            label_dx=0, label_dy=0, mirror=0, rotation=0,
            properties=[PpProperty("100")],
        )
        with pytest.raises(ValueError, match="VCB"):
            build_use_block(r, "R1", "0.05")


# ---------------------------------------------------------------------------
# build_models_section() — seção /MODELS completa
# ---------------------------------------------------------------------------


class TestBuildModelsSection:
    def test_no_vcbs_returns_empty_list(self):
        assert build_models_section([]) == []

    def test_all_defaults_returns_empty_list(self):
        """Se nenhum VCB tem params customizados, seção /MODELS não é emitida."""
        vcb = _make_vcb("DJ1", _default_vcb_props())
        assert build_models_section([vcb]) == []

    def test_one_customized_vcb_returns_section(self):
        props = _default_vcb_props()
        props[2] = "8.0"
        vcb = _make_vcb("DJ1", props)
        lines = build_models_section([vcb])
        assert lines
        assert lines[0] == "/MODELS"
        text = "\n".join(lines)
        assert "MODEL vcb_reignition" in text
        assert "USE vcb_reignition AS DJ1" in text
        # Apenas 1 USE para 1 VCB 1φ
        assert text.count("USE vcb_reignition AS") == 1

    def test_vcb3_emits_3_use_blocks_one_per_phase(self):
        props = _default_vcb3_props()
        props[6] = "8.0"  # I_chop customizado
        vcb3 = _make_vcb3("DJ3", props)
        lines = build_models_section([vcb3])
        text = "\n".join(lines)
        # 1 MODEL + 3 USE (A/B/C)
        assert text.count("MODEL vcb_reignition") == 1
        assert text.count("ENDMODEL") == 1
        assert text.count("USE vcb_reignition AS") == 3
        assert "USE vcb_reignition AS DJ3_A" in text
        assert "USE vcb_reignition AS DJ3_B" in text
        assert "USE vcb_reignition AS DJ3_C" in text

    def test_multiple_vcbs_share_one_model_definition(self):
        """2 VCBs = 1 MODEL + 2 USE (não duplica definição)."""
        props = _default_vcb_props()
        props[2] = "8.0"
        vcb1 = _make_vcb("DJ1", props)
        vcb2 = _make_vcb("DJ2", props)
        lines = build_models_section([vcb1, vcb2])
        text = "\n".join(lines)
        assert text.count("MODEL vcb_reignition") == 1
        assert text.count("ENDMODEL") == 1
        assert text.count("USE vcb_reignition AS") == 2


# ---------------------------------------------------------------------------
# Integração end-to-end: to_atp() injeta a seção
# ---------------------------------------------------------------------------


class TestToAtpIntegration:
    def _make_project_with_vcb(self, customize: bool) -> PpProject:
        r = PpComponent(
            type="R", name="R1", visible=True, x=0, y=0,
            label_dx=0, label_dy=0, mirror=0, rotation=0,
            properties=[PpProperty("100"), PpProperty("26.85"), PpProperty("european")],
        )
        props = _default_vcb_props()
        if customize:
            props[2] = "8.0"
        vcb = _make_vcb("DJ1", props)
        return PpProject(components=[r, vcb], wires=[], diagrams=[])

    def test_default_vcb_no_models_section_in_output(self):
        atp = to_atp(self._make_project_with_vcb(customize=False))
        text = "\n".join(atp.raw_lines)
        assert "/MODELS" not in text
        assert "MODEL vcb_reignition" not in text

    def test_customized_vcb_has_models_section(self):
        atp = to_atp(self._make_project_with_vcb(customize=True))
        text = "\n".join(atp.raw_lines)
        assert "/MODELS" in text
        assert "MODEL vcb_reignition" in text
        assert "USE vcb_reignition AS DJ1" in text

    def test_models_section_appears_before_branch(self):
        atp = to_atp(self._make_project_with_vcb(customize=True))
        text = "\n".join(atp.raw_lines)
        assert text.index("/MODELS") < text.index("/BRANCH")

    def test_section_indices_shifted_correctly(self):
        """BRANCH/SWITCH/SOURCE start_line/end_line devem refletir o shift."""
        atp = to_atp(self._make_project_with_vcb(customize=True))
        # Sem /MODELS, BRANCH estaria em linha 1. Com /MODELS (~150 linhas),
        # BRANCH deve estar em linha >>1.
        assert atp.sections["BRANCH"].start_line > 50
        # Verifica que o apontador ainda aponta para a linha "/BRANCH" literal.
        branch_line = atp.raw_lines[atp.sections["BRANCH"].start_line]
        assert branch_line == "/BRANCH"

    def test_serialize_project_still_works_with_models(self):
        """Após inserir /MODELS, serialize_project deve produzir texto
        válido (com /BRANCH, /SWITCH etc. nas posições certas)."""
        atp = to_atp(self._make_project_with_vcb(customize=True))
        text = serialize_project(atp)
        # Sanity checks
        assert text.count("/MODELS") == 1
        assert text.count("/BRANCH") == 1
        assert text.count("/SWITCH") == 1
        assert text.count("/SOURCE") == 1
        # Ordem preservada
        idxs = [
            text.index("/MODELS"),
            text.index("/BRANCH"),
            text.index("/SWITCH"),
            text.index("/SOURCE"),
        ]
        assert idxs == sorted(idxs), f"Ordem de seções incorreta: {idxs}"

    def test_warning_emitted_mentions_TACS(self):
        """Warning educativo: usuário deve saber que TACS é manual."""
        atp = to_atp(self._make_project_with_vcb(customize=True))
        joined = " ".join(atp.warnings)
        assert "TACS" in joined
        assert "MANUAL" in joined or "manual" in joined

    def test_vcb3_integration(self):
        """VCB3 com reignição customizada emite 3 USE blocks."""
        props = _default_vcb3_props()
        props[6] = "8.0"  # I_chop customizado
        vcb3 = _make_vcb3("DJ3", props)
        p = PpProject(components=[vcb3], wires=[], diagrams=[])
        atp = to_atp(p)
        text = "\n".join(atp.raw_lines)
        assert "USE vcb_reignition AS DJ3_A" in text
        assert "USE vcb_reignition AS DJ3_B" in text
        assert "USE vcb_reignition AS DJ3_C" in text

    def test_no_regression_for_simple_project_without_vcb(self):
        """Projeto sem VCB continua produzindo output sem /MODELS."""
        r = PpComponent(
            type="R", name="R1", visible=True, x=0, y=0,
            label_dx=0, label_dy=0, mirror=0, rotation=0,
            properties=[PpProperty("100"), PpProperty("26.85"), PpProperty("european")],
        )
        p = PpProject(components=[r], wires=[], diagrams=[])
        atp = to_atp(p)
        text = serialize_project(atp)
        assert "/MODELS" not in text
        assert "MODEL vcb_reignition" not in text
        assert "/BRANCH" in text


# ---------------------------------------------------------------------------
# Integridade do layout: mapeamento props→DATA
# ---------------------------------------------------------------------------


class TestPropertyMappingIntegrity:
    """Guard para quando o .ocomp do VCB/VCB3 evoluir."""

    def test_vcb_mapping_has_8_reignition_params(self):
        names = [n for n, _ in VCB_REIGNITION_PROPS]
        assert len(names) == 8

    def test_vcb3_mapping_has_8_reignition_params(self):
        names = [n for n, _ in VCB3_REIGNITION_PROPS]
        assert len(names) == 8

    def test_vcb_vs_vcb3_same_param_names(self):
        """Os 8 nomes de params devem ser idênticos entre VCB e VCB3."""
        names_1ph = {n for n, _ in VCB_REIGNITION_PROPS}
        names_3ph = {n for n, _ in VCB3_REIGNITION_PROPS}
        assert names_1ph == names_3ph

    def test_vcb3_indices_start_after_timing(self):
        """VCB3 tem 6 props de timing antes dos 8 de reignição."""
        first_reignition_idx = VCB3_REIGNITION_PROPS[0][1]
        assert first_reignition_idx == 6
