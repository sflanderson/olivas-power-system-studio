"""
tests/test_pp_xfmr.py — v0.27.5: Hybrid Transformer (XFMR)
Mork model para estudos de inrush.

Cobre:

* Enums: CoreType, WindingConnection, DataSource.
* FrolichCoefficients + H(B) avaliação.
* SaturationCurvePoint dataclass.
* HybridTransformerParameters (frozen, defaults).
* validate_xfmr — hierarquia V_HV > V_LV, uk em range,
  saturação monotônica, fluxo residual, La > 0.
* estimate_peak_inrush_current_kA — pior caso vs melhor
  caso (closing angle 0° vs 90°).
* emit_xfmr_cards — formato draft.
* Bridge: XFMR.ocomp → cards injetados em /BRANCH.
"""

from __future__ import annotations

import math

import pytest

from app.preprocessor.bridge_to_atp import _convert_xfmr, to_atp
from app.preprocessor.models import PpComponent, PpProject, PpProperty
from app.preprocessor.xfmr import (
    CoreType, DataSource, FrolichCoefficients,
    HybridTransformerParameters, SaturationCurvePoint,
    TYPICAL_FROLICH_BY_CLASS, WindingConnection,
    emit_xfmr_cards, estimate_peak_inrush_current_kA,
    validate_xfmr,
)


# ---------------------------------------------------------------------------
# Frolich
# ---------------------------------------------------------------------------


class TestFrolich:
    def test_basic_evaluation(self):
        c = FrolichCoefficients(a=120, b=1.0, c=20)
        # Em B=1.0: H = 120·1/(1+1) + 20·1 = 60 + 20 = 80
        assert c.H_of_B(1.0) == pytest.approx(80.0, abs=0.1)

    def test_zero_flux(self):
        c = FrolichCoefficients(a=120, b=1.0, c=20)
        assert c.H_of_B(0.0) == 0.0

    def test_negative_flux(self):
        """Anti-simetria: H(-B) = -H(B)."""
        c = FrolichCoefficients(a=120, b=1.0, c=20)
        assert c.H_of_B(-1.0) == pytest.approx(-c.H_of_B(1.0), abs=0.001)

    def test_extreme_saturation(self):
        """Em B → ∞: H ≈ a + c·B (linear)."""
        c = FrolichCoefficients(a=120, b=1.0, c=20)
        H_high = c.H_of_B(10.0)
        # H ≈ 120·10/(1+10) + 20·10 = 109 + 200 ≈ 309
        assert H_high == pytest.approx(309.0, abs=2.0)

    def test_typical_classes_present(self):
        assert "go_si_modern" in TYPICAL_FROLICH_BY_CLASS
        assert "go_si_old" in TYPICAL_FROLICH_BY_CLASS
        assert "amorphous" in TYPICAL_FROLICH_BY_CLASS


# ---------------------------------------------------------------------------
# Validador
# ---------------------------------------------------------------------------


def _basic_xfmr(**overrides) -> HybridTransformerParameters:
    base = dict(
        name="TR1",
        nodes_hv=("H1", "H2", "H3"),
        nodes_lv=("L1", "L2", "L3"),
        rated_voltage_HV_kV=138.0,
        rated_voltage_LV_kV=13.8,
        rated_power_MVA=25.0,
    )
    base.update(overrides)
    return HybridTransformerParameters(**base)


class TestValidator:
    def test_valid_default(self):
        x = _basic_xfmr()
        assert validate_xfmr(x) == []

    def test_empty_name(self):
        x = _basic_xfmr(name="")
        errs = validate_xfmr(x)
        assert any("name vazio" in e for e in errs)

    def test_long_name(self):
        x = _basic_xfmr(name="ABCDEFGH")
        errs = validate_xfmr(x)
        assert any("> 6 chars" in e for e in errs)

    def test_v_hv_below_v_lv(self):
        x = _basic_xfmr(rated_voltage_HV_kV=10.0, rated_voltage_LV_kV=20.0)
        errs = validate_xfmr(x)
        assert any("V_HV" in e and "V_LV" in e for e in errs)

    def test_zero_rated_v(self):
        x = _basic_xfmr(rated_voltage_HV_kV=0)
        errs = validate_xfmr(x)
        assert any("rated_voltage_HV_kV" in e for e in errs)

    def test_uk_out_of_range(self):
        x = _basic_xfmr(uk_pos_pct=30.0)
        errs = validate_xfmr(x)
        assert any("uk_pos_pct" in e for e in errs)

    def test_residual_out_of_range(self):
        x = _basic_xfmr(residual_flux_pu=1.5)
        errs = validate_xfmr(x)
        assert any("residual_flux_pu" in e for e in errs)

    def test_la_must_be_positive(self):
        x = _basic_xfmr(final_slope_inductance_pu=0.0)
        errs = validate_xfmr(x)
        assert any("final_slope" in e.lower() for e in errs)

    def test_overlap_hv_lv_nodes(self):
        x = _basic_xfmr(
            nodes_hv=("X", "H2", "H3"),
            nodes_lv=("X", "L2", "L3"),
        )
        errs = validate_xfmr(x)
        assert any("compartilham" in e or "short" in e.lower() for e in errs)

    def test_non_monotonic_saturation(self):
        x = _basic_xfmr(saturation_curve=(
            SaturationCurvePoint(1.00, 0.005),
            SaturationCurvePoint(0.95, 0.003),  # V decresce — erro
        ))
        errs = validate_xfmr(x)
        assert any("monotôn" in e.lower() for e in errs)


# ---------------------------------------------------------------------------
# Inrush estimation
# ---------------------------------------------------------------------------


class TestInrushEstimation:
    def test_worst_case_closing_angle_0(self):
        """θ=0° dá pico maior que θ=90°."""
        x = _basic_xfmr(residual_flux_pu=0.7)
        r0 = estimate_peak_inrush_current_kA(x, closing_angle_deg=0.0)
        r90 = estimate_peak_inrush_current_kA(x, closing_angle_deg=90.0)
        assert r0["peak_inrush_kA"] > r90["peak_inrush_kA"]

    def test_no_residual_no_peak_at_90deg(self):
        """θ=90° com residual=0 → φ_max = 0 → I_peak ≈ 0."""
        x = _basic_xfmr(residual_flux_pu=0.0)
        r = estimate_peak_inrush_current_kA(x, closing_angle_deg=90.0)
        assert r["flux_max_pu"] == pytest.approx(0.0, abs=0.001)

    def test_residual_increases_peak(self):
        """Maior residual → maior pico."""
        x_low = _basic_xfmr(residual_flux_pu=0.0)
        x_high = _basic_xfmr(residual_flux_pu=0.8)
        r_low = estimate_peak_inrush_current_kA(x_low)
        r_high = estimate_peak_inrush_current_kA(x_high)
        assert r_high["peak_inrush_kA"] > r_low["peak_inrush_kA"]

    def test_flux_max_formula(self):
        """φ_max = 2·|cos(θ)| + |φ_res|."""
        x = _basic_xfmr(residual_flux_pu=0.5)
        r = estimate_peak_inrush_current_kA(x, closing_angle_deg=0.0)
        assert r["flux_max_pu"] == pytest.approx(2.5, abs=0.001)

    def test_peak_inrush_typical_pu(self):
        """Para 100 MVA / 138 kV thermal-class, com residual 0.7 e θ=0°,
        peak ≈ 5-10× I_n é esperado (Mork, Dommel)."""
        x = _basic_xfmr(
            rated_voltage_HV_kV=138.0, rated_power_MVA=100.0,
            residual_flux_pu=0.7,
        )
        r = estimate_peak_inrush_current_kA(x, closing_angle_deg=0.0)
        # peak deve ser claramente > 1 pu (= I_n)
        assert r["peak_inrush_pu"] > 1.0

    def test_i_base_formula(self):
        """I_base = S_3φ / (√3 · V_LL)."""
        x = _basic_xfmr(rated_voltage_HV_kV=138.0, rated_power_MVA=100.0)
        r = estimate_peak_inrush_current_kA(x)
        # 100e6 / (√3 · 138e3) = 418.4 A = 0.4184 kA
        assert r["i_base_HV_kA"] == pytest.approx(0.4184, abs=0.005)


# ---------------------------------------------------------------------------
# Emit cards
# ---------------------------------------------------------------------------


class TestEmitCards:
    def test_basic_emit(self):
        x = _basic_xfmr()
        lines = emit_xfmr_cards(x)
        text = "\n".join(lines)
        assert "C XFMR" in text
        assert "Hybrid Transformer TR1" in text

    def test_metadata_in_comments(self):
        x = _basic_xfmr(
            rated_voltage_HV_kV=138.0,
            rated_voltage_LV_kV=13.8,
            rated_power_MVA=25.0,
        )
        text = "\n".join(emit_xfmr_cards(x))
        assert "138" in text
        assert "13.80" in text or "13.8" in text
        assert "25.00" in text or "25.0" in text

    def test_core_type_in_metadata(self):
        x = _basic_xfmr(core_type=CoreType.FIVE_LEG_STACKED)
        text = "\n".join(emit_xfmr_cards(x))
        assert "FIVE_LEG" in text

    def test_residual_flux_in_metadata(self):
        x = _basic_xfmr(residual_flux_pu=0.65)
        text = "\n".join(emit_xfmr_cards(x))
        assert "+0.650" in text

    def test_saturation_curve_in_metadata(self):
        x = _basic_xfmr()
        text = "\n".join(emit_xfmr_cards(x))
        assert "Saturation curve" in text

    def test_invalid_raises(self):
        x = _basic_xfmr(rated_voltage_HV_kV=0)
        with pytest.raises(ValueError, match="inválido"):
            emit_xfmr_cards(x)


# ---------------------------------------------------------------------------
# Bridge integration
# ---------------------------------------------------------------------------


def _mk_xfmr_comp(name: str, props: list[str]) -> PpComponent:
    return PpComponent(
        type="XFMR", name=name, visible=True,
        x=0, y=0, label_dx=0, label_dy=0, mirror=0, rotation=0,
        properties=[PpProperty(p) for p in props],
    )


_DEFAULT_PROPS = [
    "138", "13.8", "25", "60",   # ratings
    "THREE_LEG",                   # core
    "10", "100",                   # uk%, p_load
    "0.5", "15",                   # i_0%, p_0
    "0.0",                         # residual flux
    "0.04",                        # La
    "Yg", "D",                     # connections
    "0", "0", "0",                 # caps
]


class TestBridgeXfmr:
    def test_xfmr_emits_cards(self):
        comp = _mk_xfmr_comp("TR1", _DEFAULT_PROPS)
        atp = to_atp(PpProject(components=[comp]))
        text = "\n".join(atp.raw_lines)
        assert "C XFMR" in text
        assert "Hybrid Transformer TR1" in text

    def test_invalid_v_warned(self):
        bad = list(_DEFAULT_PROPS)
        bad[0] = "abc"  # V_HV não-numérico
        comp = _mk_xfmr_comp("TR1", bad)
        atp = to_atp(PpProject(components=[comp]))
        assert any("rated_voltage_HV_kV" in w for w in atp.warnings)

    def test_invalid_core_type_falls_back(self):
        bad = list(_DEFAULT_PROPS)
        bad[4] = "INVALID_CORE"
        comp = _mk_xfmr_comp("TR1", bad)
        atp = to_atp(PpProject(components=[comp]))
        # Deve emitir warning + usar default THREE_LEG
        assert any("core_type" in w.lower() for w in atp.warnings)
        text = "\n".join(atp.raw_lines)
        assert "THREE_LEG" in text

    def test_v_hv_below_lv_rejected(self):
        bad = list(_DEFAULT_PROPS)
        bad[0] = "10"
        bad[1] = "20"
        comp = _mk_xfmr_comp("TR1", bad)
        atp = to_atp(PpProject(components=[comp]))
        text = "\n".join(atp.raw_lines)
        assert "C XFMR" not in text  # descartado
        assert any("V_HV" in w for w in atp.warnings)

    def test_xfmr_with_other_components(self):
        """XFMR coexiste com R/L/C."""
        x = _mk_xfmr_comp("TR1", _DEFAULT_PROPS)
        r = PpComponent(
            type="R", name="R1", visible=True,
            x=0, y=0, label_dx=0, label_dy=0, mirror=0, rotation=0,
            properties=[PpProperty("100 Ohm")],
        )
        atp = to_atp(PpProject(components=[x, r]))
        text = "\n".join(atp.raw_lines)
        assert "C XFMR" in text
        assert len(atp.branches) == 1   # R1

    def test_warning_summary_emitted(self):
        comp = _mk_xfmr_comp("TR1", _DEFAULT_PROPS)
        atp = to_atp(PpProject(components=[comp]))
        # warning final do XFMR menciona core type
        assert any("THREE_LEG" in w for w in atp.warnings)

    def test_helper_direct_call(self):
        from app.preprocessor.node_coalescer import coalesce_nodes
        from app.core.project_model import AtpProject, HeaderInfo
        comp = _mk_xfmr_comp("TR1", _DEFAULT_PROPS)
        proj = PpProject(components=[comp])
        node_map = coalesce_nodes(proj)
        atp = AtpProject(file_path="", raw_lines=[], header=HeaderInfo(raw_lines=[]))
        x = _convert_xfmr(comp, "TR1", node_map, atp)
        assert x is not None
        assert x.rated_voltage_HV_kV == 138.0
        assert x.core_type == CoreType.THREE_LEG_STACKED


# ---------------------------------------------------------------------------
# Cenário realista: inrush study
# ---------------------------------------------------------------------------


class TestInrushScenario:
    def test_inrush_typical_distribution_transformer(self):
        """
        Cenário: TR distribuição 30 MVA 138/13.8 kV, núcleo 3-leg,
        inrush em pior caso (residual=0.7 pu, θ=0°).

        Expectativa: pico ≥ 5× I nominal (típico Mork, Dommel).
        """
        x = _basic_xfmr(
            rated_voltage_HV_kV=138.0,
            rated_voltage_LV_kV=13.8,
            rated_power_MVA=30.0,
            core_type=CoreType.THREE_LEG_STACKED,
            residual_flux_pu=0.7,
        )
        r = estimate_peak_inrush_current_kA(x, closing_angle_deg=0.0)
        # I_n = 30e6 / (√3·138e3) ≈ 125.5 A
        # Pico esperado: ≥ 5× = 627 A ⇒ ≥ 0.627 kA
        assert r["peak_inrush_kA"] >= 0.5
        # E muito maior que I_n (em pu)
        assert r["peak_inrush_pu"] >= 5.0

    def test_inrush_mitigation_with_pow_switching(self):
        """
        Point-on-wave switching: θ=90° (peak voltage) → inrush
        praticamente eliminado.
        """
        x = _basic_xfmr(residual_flux_pu=0.0)
        r_worst = estimate_peak_inrush_current_kA(
            x, closing_angle_deg=0.0,
        )
        r_best = estimate_peak_inrush_current_kA(
            x, closing_angle_deg=90.0,
        )
        # Razão pior/melhor > 100×
        assert r_worst["peak_inrush_kA"] > 100 * max(
            r_best["peak_inrush_kA"], 1e-6
        )

    def test_5leg_vs_3leg_core(self):
        """Sanidade — ambos topologias geram sem erro."""
        x_3 = _basic_xfmr(core_type=CoreType.THREE_LEG_STACKED)
        x_5 = _basic_xfmr(core_type=CoreType.FIVE_LEG_STACKED)
        r_3 = estimate_peak_inrush_current_kA(x_3)
        r_5 = estimate_peak_inrush_current_kA(x_5)
        assert r_3["peak_inrush_kA"] > 0
        assert r_5["peak_inrush_kA"] > 0
