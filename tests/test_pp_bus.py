"""
tests/test_pp_bus.py — v0.27.7: barramentos elétricos com
metadata de painel estilo SKM PTW.

Cobre:

* BusComponent (frozen dataclass + defaults).
* validate_bus — bus_id vazio, voltage > 0, n_phases ∈ {1,3},
  n_taps ∈ [2,8], coerência tensão × panel_type.
* effective_clearing_time_ms — AFD overrides quando habilitado.
* bus_to_arc_flash_case — integração com NBR 17227.
* emit_bus_metadata_lines — comentários ATP estruturados.
* Helpers make_default_mv_switchgear, make_default_lv_panel,
  make_default_motor_control_center.
* Bridge integration: BUS.ocomp → metadata em /BRANCH +
  warnings.
* Cenário realista: AFD reduz ~50× a energia incidente
  (justificativa econômica do AFD).
"""

from __future__ import annotations

import pytest

from app.preprocessor.bridge_to_atp import _convert_bus, to_atp
from app.preprocessor.bus import (
    BusComponent,
    bus_to_arc_flash_case,
    effective_clearing_time_ms,
    emit_bus_metadata_lines,
    make_default_lv_panel,
    make_default_motor_control_center,
    make_default_mv_switchgear,
    validate_bus,
)
from app.preprocessor.models import PpComponent, PpProject, PpProperty
from app.standards.nbr17227 import EquipmentClass


# ---------------------------------------------------------------------------
# BusComponent dataclass + defaults
# ---------------------------------------------------------------------------


class TestBusComponentDataclass:
    def test_minimal_construction(self):
        b = BusComponent(
            bus_id="B1", rated_voltage_kV=13.8,
        )
        assert b.bus_id == "B1"
        assert b.n_phases == 3
        assert b.n_taps == 4
        assert b.is_lineside is True
        assert b.has_AFD is False

    def test_n_pins_3phase_4taps(self):
        b = BusComponent(bus_id="B", rated_voltage_kV=13.8,
                         n_phases=3, n_taps=4)
        assert b.n_pins == 12

    def test_n_pins_1phase(self):
        b = BusComponent(bus_id="B", rated_voltage_kV=0.480,
                         n_phases=1, n_taps=4,
                         panel_type=EquipmentClass.LV_PANEL_TYPICAL)
        assert b.n_pins == 4

    def test_frozen(self):
        b = BusComponent(bus_id="B", rated_voltage_kV=13.8)
        with pytest.raises(Exception):
            b.bus_id = "X"


# ---------------------------------------------------------------------------
# validate_bus
# ---------------------------------------------------------------------------


class TestValidateBus:
    def test_default_valid(self):
        b = make_default_mv_switchgear("SWGR1", 13.8)
        assert validate_bus(b) == []

    def test_empty_bus_id(self):
        b = BusComponent(bus_id="", rated_voltage_kV=13.8)
        errs = validate_bus(b)
        assert any("bus_id" in e for e in errs)

    def test_zero_voltage(self):
        b = BusComponent(bus_id="X", rated_voltage_kV=0)
        errs = validate_bus(b)
        assert any("rated_voltage_kV" in e for e in errs)

    def test_invalid_n_phases(self):
        b = BusComponent(bus_id="X", rated_voltage_kV=13.8, n_phases=2)
        errs = validate_bus(b)
        assert any("n_phases" in e for e in errs)

    def test_n_taps_out_of_range(self):
        b = BusComponent(bus_id="X", rated_voltage_kV=13.8, n_taps=10)
        errs = validate_bus(b)
        assert any("n_taps" in e for e in errs)

    def test_AFD_with_zero_time_rejected(self):
        b = BusComponent(
            bus_id="X", rated_voltage_kV=13.8,
            has_AFD=True, AFD_clearing_time_ms=0.0,
        )
        errs = validate_bus(b)
        assert any("AFD" in e for e in errs)

    def test_lv_panel_with_mv_voltage_warned(self):
        """LV_PANEL com tensão > 1 kV é inconsistente."""
        b = BusComponent(
            bus_id="X", rated_voltage_kV=4.16,
            panel_type=EquipmentClass.LV_PANEL_TYPICAL,
        )
        errs = validate_bus(b)
        assert any("LV" in e and "kV" in e for e in errs)

    def test_15kv_class_with_low_voltage_warned(self):
        """SWITCHGEAR_15KV requer 5 < V ≤ 15 kV."""
        b = BusComponent(
            bus_id="X", rated_voltage_kV=4.16,
            panel_type=EquipmentClass.SWITCHGEAR_15KV,
        )
        errs = validate_bus(b)
        assert any("15kV" in e for e in errs)


# ---------------------------------------------------------------------------
# effective_clearing_time_ms
# ---------------------------------------------------------------------------


class TestEffectiveClearingTime:
    def test_no_AFD_returns_coordination_time(self):
        b = BusComponent(
            bus_id="X", rated_voltage_kV=13.8, has_AFD=False,
        )
        assert effective_clearing_time_ms(b, 500) == 500.0

    def test_with_AFD_returns_min(self):
        b = BusComponent(
            bus_id="X", rated_voltage_kV=13.8,
            has_AFD=True, AFD_clearing_time_ms=10.0,
        )
        # AFD = 10 ms < 500 ms → 10
        assert effective_clearing_time_ms(b, 500) == 10.0

    def test_AFD_slower_than_coordination_returns_coord(self):
        """Se AFD está mais lento que coord (caso raro), usa coord."""
        b = BusComponent(
            bus_id="X", rated_voltage_kV=13.8,
            has_AFD=True, AFD_clearing_time_ms=300.0,
        )
        assert effective_clearing_time_ms(b, 100) == 100.0


# ---------------------------------------------------------------------------
# bus_to_arc_flash_case
# ---------------------------------------------------------------------------


class TestBusToArcFlashCase:
    def test_basic_case(self):
        b = make_default_mv_switchgear("BUS1", 13.8)
        case = bus_to_arc_flash_case(
            b, bolted_fault_current_kA=20.0,
            coordination_clearing_time_ms=200.0,
        )
        assert case.bus_name == "BUS1"
        assert case.rated_voltage_kV == 13.8
        assert case.bolted_fault_current_kA == 20.0

    def test_AFD_overrides_clearing_time(self):
        b = BusComponent(
            bus_id="B", rated_voltage_kV=13.8,
            panel_type=EquipmentClass.SWITCHGEAR_15KV,
            has_AFD=True, AFD_clearing_time_ms=10.0,
        )
        case = bus_to_arc_flash_case(
            b, bolted_fault_current_kA=20.0,
            coordination_clearing_time_ms=500.0,
        )
        # T deve ser 10 ms (AFD), não 500 ms
        assert case.arc_clearing_time_ms == 10.0

    def test_panel_type_propagates(self):
        b = make_default_motor_control_center("CCM1", 4.16)
        case = bus_to_arc_flash_case(
            b, bolted_fault_current_kA=15.0,
            coordination_clearing_time_ms=200.0,
        )
        assert case.equipment_class == EquipmentClass.CCM_5KV


# ---------------------------------------------------------------------------
# Emit metadata
# ---------------------------------------------------------------------------


class TestEmitBusMetadata:
    def test_basic_emit(self):
        b = make_default_mv_switchgear("SWGR-A", 13.8)
        lines = emit_bus_metadata_lines(b)
        text = "\n".join(lines)
        assert "BUS / PANEL: SWGR-A" in text
        assert "13.800 kV" in text

    def test_AFD_disabled_in_text(self):
        b = make_default_mv_switchgear("X", 13.8, has_AFD=False)
        text = "\n".join(emit_bus_metadata_lines(b))
        assert "AFD: disabled" in text

    def test_AFD_enabled_shows_time(self):
        b = make_default_mv_switchgear("X", 13.8, has_AFD=True)
        text = "\n".join(emit_bus_metadata_lines(b))
        assert "AFD: enabled" in text
        assert "ms" in text

    def test_lineside_in_text(self):
        b = BusComponent(
            bus_id="X", rated_voltage_kV=13.8, is_lineside=True,
        )
        text = "\n".join(emit_bus_metadata_lines(b))
        assert "Side: lineside" in text

    def test_loadside_in_text(self):
        b = BusComponent(
            bus_id="X", rated_voltage_kV=4.16,
            panel_type=EquipmentClass.CCM_5KV,
            is_lineside=False,
        )
        text = "\n".join(emit_bus_metadata_lines(b))
        assert "Side: loadside" in text


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class TestHelpers:
    def test_mv_switchgear_5kv(self):
        b = make_default_mv_switchgear("X", 4.16)
        assert b.panel_type == EquipmentClass.SWITCHGEAR_5KV
        assert validate_bus(b) == []

    def test_mv_switchgear_15kv(self):
        b = make_default_mv_switchgear("X", 13.8)
        assert b.panel_type == EquipmentClass.SWITCHGEAR_15KV
        assert validate_bus(b) == []

    def test_lv_panel(self):
        b = make_default_lv_panel("X", 0.480)
        assert b.panel_type == EquipmentClass.LV_PANEL_TYPICAL
        assert b.is_lineside is False
        assert validate_bus(b) == []

    def test_ccm_4kv(self):
        b = make_default_motor_control_center("CCM", 4.16)
        assert b.panel_type == EquipmentClass.CCM_5KV
        assert b.has_AFD is True   # CCMs modernos com AFD
        assert validate_bus(b) == []

    def test_ccm_15kv(self):
        b = make_default_motor_control_center("CCM", 13.8)
        assert b.panel_type == EquipmentClass.CCM_15KV


# ---------------------------------------------------------------------------
# Bridge integration
# ---------------------------------------------------------------------------


def _mk_bus(name: str, props: list[str]) -> PpComponent:
    return PpComponent(
        type="BUS", name=name, visible=True,
        x=0, y=0, label_dx=0, label_dy=0, mirror=0, rotation=0,
        properties=[PpProperty(p) for p in props],
    )


_DEFAULT_PROPS = [
    "BUS-1",        # bus_id
    "13.8",         # voltage
    "3",            # phases
    "swgr_15kv",    # panel_type
    "1",            # lineside
    "0",            # has_AFD
    "10",           # AFD time
    "4",            # n_taps
    "Test bus",     # description
]


class TestBridgeBus:
    def test_bus_emits_metadata(self):
        comp = _mk_bus("BUS-1", _DEFAULT_PROPS)
        atp = to_atp(PpProject(components=[comp]))
        text = "\n".join(atp.raw_lines)
        assert "BUS / PANEL: BUS-1" in text
        assert "swgr_15kv" in text

    def test_AFD_metadata_in_atp(self):
        props = list(_DEFAULT_PROPS)
        props[5] = "1"   # has_AFD = True
        props[6] = "8"   # AFD time = 8 ms
        comp = _mk_bus("BUS-AFD", props)
        atp = to_atp(PpProject(components=[comp]))
        text = "\n".join(atp.raw_lines)
        assert "AFD: enabled" in text
        assert "8.0 ms" in text

    def test_invalid_panel_type_falls_back(self):
        props = list(_DEFAULT_PROPS)
        props[3] = "INVALID_TYPE"
        comp = _mk_bus("X", props)
        atp = to_atp(PpProject(components=[comp]))
        # Warning emitted, but bus still created with default
        assert any("panel_type" in w.lower() for w in atp.warnings)
        text = "\n".join(atp.raw_lines)
        assert "swgr_15kv" in text

    def test_invalid_voltage_warned(self):
        props = list(_DEFAULT_PROPS)
        props[1] = "abc"
        comp = _mk_bus("X", props)
        atp = to_atp(PpProject(components=[comp]))
        assert any("rated_voltage_kV" in w for w in atp.warnings)

    def test_helper_direct_call(self):
        from app.preprocessor.node_coalescer import coalesce_nodes
        from app.core.project_model import AtpProject, HeaderInfo
        comp = _mk_bus("X", _DEFAULT_PROPS)
        proj = PpProject(components=[comp])
        node_map = coalesce_nodes(proj)
        atp = AtpProject(file_path="", raw_lines=[],
                         header=HeaderInfo(raw_lines=[]))
        b = _convert_bus(comp, "X", node_map, atp)
        assert b is not None
        assert b.bus_id == "BUS-1"
        assert b.panel_type == EquipmentClass.SWITCHGEAR_15KV

    def test_bus_with_other_components(self):
        bus = _mk_bus("BUS-1", _DEFAULT_PROPS)
        r = PpComponent(
            type="R", name="R1", visible=True,
            x=0, y=0, label_dx=0, label_dy=0, mirror=0, rotation=0,
            properties=[PpProperty("100 Ohm")],
        )
        atp = to_atp(PpProject(components=[bus, r]))
        text = "\n".join(atp.raw_lines)
        assert "BUS / PANEL" in text
        assert len(atp.branches) == 1   # R1


# ---------------------------------------------------------------------------
# Cenário realista — valor do AFD
# ---------------------------------------------------------------------------


class TestRealisticAFDScenario:
    """
    Cenário realista demonstrando o **valor econômico do AFD**:
    * Switchgear 13.8 kV / 25 kA / coordenação 500 ms
    * Sem AFD: ~21 cal/cm² (Cat 3 — EPI 25 cal/cm²)
    * Com AFD 10 ms: ~0.4 cal/cm² (Cat 0 — sem EPI especial)
    * Razão > 40× → justifica investimento.
    """

    def test_afd_reduces_energy_dramatically(self):
        from app.postprocessor.arc_flash import calculate_arc_flash

        b_no_afd = make_default_mv_switchgear(
            "SWGR", 13.8, has_AFD=False,
        )
        b_with_afd = make_default_mv_switchgear(
            "SWGR-AFD", 13.8, has_AFD=True,
        )

        case_no = bus_to_arc_flash_case(
            b_no_afd, bolted_fault_current_kA=25.0,
            coordination_clearing_time_ms=500.0,
        )
        case_yes = bus_to_arc_flash_case(
            b_with_afd, bolted_fault_current_kA=25.0,
            coordination_clearing_time_ms=500.0,
        )

        r_no = calculate_arc_flash(case_no)
        r_yes = calculate_arc_flash(case_yes)

        # AFD deve reduzir E em pelo menos 10×
        assert r_no.incident_energy_cal_cm2 / r_yes.incident_energy_cal_cm2 > 10
        # v0.28.0-PRO: com calibração IEEE 1584, 13.8kV/Ibf=25 kA/T=500ms
        # gera DANGER (não Cat 3) sem AFD; com AFD reduz para Cat 0 ou 1.
        assert r_no.ppe_category.value in ("3", "4", "DANGER")
        assert r_yes.ppe_category.value in ("0", "1")

    def test_lineside_panels_used_with_max_ibf(self):
        """Lineside + AFD deve dar resultado usável."""
        from app.postprocessor.arc_flash import calculate_arc_flash

        b = BusComponent(
            bus_id="MAIN-LINESIDE",
            rated_voltage_kV=13.8,
            panel_type=EquipmentClass.SWITCHGEAR_15KV,
            is_lineside=True,
            has_AFD=True,
            AFD_clearing_time_ms=15.0,
        )
        case = bus_to_arc_flash_case(
            b, bolted_fault_current_kA=40.0,   # Ifault alto
            coordination_clearing_time_ms=2000.0,  # backup lento
        )
        r = calculate_arc_flash(case)
        # Mesmo com Ibf alto, AFD mantém categoria baixa
        assert r.incident_energy_cal_cm2 < 4.0   # Cat 0 ou 1
