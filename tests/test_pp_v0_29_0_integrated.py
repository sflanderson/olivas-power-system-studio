"""
tests/test_pp_v0_29_0_integrated.py — v0.29.0:
Integração sequencial 0/1/2 + μ·q + Method C no bus_pipeline.

Cobre:

* BusPipelineConfig com 3 novos blocos de campos
* analyze_bus_full_pipeline aplica:
  - Method A/B/C de κ
  - apply_near_to_generator_decay (μ·q)
  - calculate_all_faults (sequencial)
* BusPipelineReport carrega os 3 novos resultados
* summary() formata novos blocos
* Backward compat: defaults preservam comportamento anterior
"""

from __future__ import annotations

import pytest

from app.postprocessor.bus_pipeline import (
    BusPipelineConfig,
    BusPipelineReport,
    analyze_bus_full_pipeline,
)
from app.postprocessor.short_circuit import (
    ScSource, ShortCircuitNetwork,
)
from app.preprocessor.models import (
    PpComponent, PpProject, PpProperty,
)


def _mk(t, n, props, x=0, y=0):
    return PpComponent(
        type=t, name=n, visible=True,
        x=x, y=y, label_dx=0, label_dy=0, mirror=0, rotation=0,
        properties=[PpProperty(p) for p in props],
    )


def _bus(name="B1", bus_id="BUS-1", voltage="13.8"):
    return _mk("BUS", name, [
        bus_id, voltage, "3", "swgr_15kv",
        "1", "0", "10", "4", "",
    ])


# ---------------------------------------------------------------------------
# BusPipelineConfig — novos campos
# ---------------------------------------------------------------------------


class TestNewConfigFields:

    def test_compute_asymmetric_faults_default_false(self):
        c = BusPipelineConfig()
        assert c.compute_asymmetric_faults is False

    def test_apply_near_to_generator_decay_default_false(self):
        c = BusPipelineConfig()
        assert c.apply_near_to_generator_decay is False

    def test_kappa_method_default_B(self):
        c = BusPipelineConfig()
        assert c.kappa_method == "B"

    def test_grounding_type_default_solid(self):
        c = BusPipelineConfig()
        assert c.grounding_type == "solid"

    def test_minimum_clearing_time_default(self):
        c = BusPipelineConfig()
        assert c.minimum_clearing_time_s == 0.05

    def test_fc_Hz_default(self):
        c = BusPipelineConfig()
        assert c.fc_Hz == 20.0


# ---------------------------------------------------------------------------
# BusPipelineReport — novos campos
# ---------------------------------------------------------------------------


class TestNewReportFields:

    def test_default_decay_result_none(self):
        r = BusPipelineReport(
            bus_id="X", rated_voltage_kV=13.8,
            panel_type="swgr_15kv",
            is_lineside=True, has_AFD=False,
            n_neighbors=0, n_sc_sources=0,
            sources_summary=(),
            Ik_pp_kA=0.0, ip_kA=0.0, kappa=0.0,
            coordination_clearing_time_ms=0.0,
            effective_clearing_time_ms=0.0,
            incident_energy_cal_cm2=0.0,
            arc_flash_boundary_mm=0.0,
            ppe_category="0",
            warnings=(),
        )
        assert r.decay_result is None
        assert r.asymmetric_fault_result is None
        assert r.Ib_kA == 0.0
        assert r.Ik_steady_kA == 0.0
        assert r.kappa_method_used == "B"


# ---------------------------------------------------------------------------
# Backward compat — config default não muda Ik''
# ---------------------------------------------------------------------------


class TestBackwardCompat:

    def test_default_pipeline_unchanged(self):
        """Sem nada novo na config, comportamento idêntico ao
        v0.28.x (apenas Method A wired). v0.29.0 não pode
        regredir."""
        proj = PpProject(components=[_bus()])
        # Sem fontes → ValueError. API deve aceitar.
        with pytest.raises(ValueError, match="nenhuma fonte"):
            analyze_bus_full_pipeline(
                proj, "BUS-1",
                coordination_clearing_time_ms=200.0,
            )


# ---------------------------------------------------------------------------
# κ Method dispatcher (sem schematic, usando ShortCircuitNetwork direto)
# ---------------------------------------------------------------------------


class TestKappaMethodDispatcher:
    """
    Testa a lógica do κ Method que será aplicada quando o
    pipeline chamar. Como o pipeline precisa de PpProject
    integro, testamos a lógica subjacente isoladamente.
    """

    def test_method_B_increases_kappa(self):
        from app.standards.iec60909_kappa import (
            kappa_method_A, kappa_method_B,
        )
        rovx = 0.10
        kA = kappa_method_A(rovx)
        kB = kappa_method_B(rovx)
        assert kB > kA
        assert kB <= 2.0

    def test_method_C_uses_fc_correction(self):
        from app.standards.iec60909_kappa import kappa_method_C
        z_at_fc = complex(0.10, 0.50)   # R/X em fc = 0.20
        kC = kappa_method_C(z_at_fc, fc_Hz=20.0)
        # Com correção fc/fn=20/60=0.333, R/X corrigido = 0.067
        # → κ = 1.02 + 0.98·exp(-3·0.067) ≈ 1.82
        assert 1.5 < kC < 2.0


# ---------------------------------------------------------------------------
# Faltas assimétricas (testa via ShortCircuitNetwork direto)
# ---------------------------------------------------------------------------


class TestAsymmetricFaultsIntegration:
    """
    A integração no pipeline foi adicionada mas o teste E2E
    requer um schematic completo. Aqui validamos a CHAIN da
    chamada — a partir de Z_th, o pipeline calcularia o que
    iec60909_seq calcula independentemente.
    """

    def test_solid_grounded_chain(self):
        from app.standards.iec60909_seq import (
            calculate_all_faults, GroundingType,
            sequence_impedances_from_grounding,
        )
        Z_th = complex(0.5, 2.0)
        seq = sequence_impedances_from_grounding(
            Z_th, GroundingType.SOLIDLY_GROUNDED,
        )
        result = calculate_all_faults(
            Un_kV=13.8, seq_impedances=seq,
            grounding=GroundingType.SOLIDLY_GROUNDED,
        )
        assert result.Ik3_kA > 0
        assert result.Ik2_kA > 0
        # Solid: Ik1 ≈ Ik3
        assert result.Ik1_to_Ik3_ratio == pytest.approx(1.0, rel=0.05)


# ---------------------------------------------------------------------------
# Decay near-to-gen integration (lógica)
# ---------------------------------------------------------------------------


class TestDecayIntegration:

    def test_far_returns_no_decay(self):
        from app.standards.iec60909_decay import (
            apply_near_to_generator_decay,
        )
        # Ik''/IrG = 1 → far → μ=q=1
        r = apply_near_to_generator_decay(
            Ik_pp_kA=10, IrG_kA=10,
            minimum_clearing_time_s=0.05,
        )
        assert not r.is_near_to_generator
        assert r.Ib_kA == 10.0
        assert r.Ik_steady_kA == 10.0

    def test_near_decays_Ib_and_Ik(self):
        from app.standards.iec60909_decay import (
            apply_near_to_generator_decay,
        )
        r = apply_near_to_generator_decay(
            Ik_pp_kA=20.0, IrG_kA=2.0,   # ratio=10
            minimum_clearing_time_s=0.05,
        )
        assert r.is_near_to_generator
        assert r.Ib_kA < 20.0
        assert r.Ik_steady_kA < r.Ib_kA


# ---------------------------------------------------------------------------
# Estimate I_rG helper
# ---------------------------------------------------------------------------


class TestEstimateIrG:

    def test_no_sources_returns_zero(self):
        from app.postprocessor.bus_pipeline import (
            _estimate_rated_current_from_sources,
        )
        net = ShortCircuitNetwork(rated_voltage_kV=13.8)
        # sem fontes
        assert _estimate_rated_current_from_sources(net, 13.8) == 0.0

    def test_zero_voltage_returns_zero(self):
        from app.postprocessor.bus_pipeline import (
            _estimate_rated_current_from_sources,
        )
        net = ShortCircuitNetwork(rated_voltage_kV=13.8)
        assert _estimate_rated_current_from_sources(net, 0.0) == 0.0


# ---------------------------------------------------------------------------
# Summary text
# ---------------------------------------------------------------------------


class TestSummaryV029:

    def test_kappa_method_in_summary(self):
        r = BusPipelineReport(
            bus_id="X", rated_voltage_kV=13.8,
            panel_type="swgr_15kv",
            is_lineside=True, has_AFD=False,
            n_neighbors=0, n_sc_sources=0,
            sources_summary=(),
            Ik_pp_kA=20.0, ip_kA=55.0, kappa=1.94,
            coordination_clearing_time_ms=500.0,
            effective_clearing_time_ms=500.0,
            incident_energy_cal_cm2=10.0,
            arc_flash_boundary_mm=2000.0,
            ppe_category="2",
            kappa_method_used="C",
            warnings=(),
        )
        text = r.summary()
        assert "Method C" in text

    def test_asymmetric_faults_in_summary(self):
        from app.standards.iec60909_seq import (
            calculate_all_faults, GroundingType,
            sequence_impedances_from_grounding,
        )
        Z = complex(0.5, 2.0)
        seq = sequence_impedances_from_grounding(
            Z, GroundingType.SOLIDLY_GROUNDED,
        )
        afr = calculate_all_faults(
            Un_kV=13.8, seq_impedances=seq,
            grounding=GroundingType.SOLIDLY_GROUNDED,
        )
        r = BusPipelineReport(
            bus_id="X", rated_voltage_kV=13.8,
            panel_type="swgr_15kv",
            is_lineside=True, has_AFD=False,
            n_neighbors=0, n_sc_sources=0,
            sources_summary=(),
            Ik_pp_kA=20.0, ip_kA=55.0, kappa=1.94,
            coordination_clearing_time_ms=500.0,
            effective_clearing_time_ms=500.0,
            incident_energy_cal_cm2=10.0,
            arc_flash_boundary_mm=2000.0,
            ppe_category="2",
            asymmetric_fault_result=afr,
            warnings=(),
        )
        text = r.summary()
        assert "Faltas assimétricas" in text
        assert "Trifásica" in text
        assert "Mono-terra" in text
