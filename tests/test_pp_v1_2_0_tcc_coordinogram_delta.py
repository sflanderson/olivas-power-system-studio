"""
tests.test_pp_v1_2_0_tcc_coordinogram_delta — sub-sprint δ.

Cobre integração GUI do widget ``TCCCoordinogramWidget`` com:

* δ.1 — TCCDevice (β) renderizando composite envelope
* δ.2 — DamageCurves (γ) overlay vermelho tracejado
* δ.3 — Mix de tipos sem crash, sem regression v1.1.0

**Aceite δ**:
- Smoke test mixed (5 tipos no mesmo widget) passing
- TCCCurve legacy continua funcionando (regression)
- Damage curves NÃO entram em line_artists drag-able
- TCCDevice entra em line_artists (composite arrastável)
- Pickup verticals visíveis para cada segment do device
- Coord pair-wise envolvendo damage é skipped (não crashes)
"""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6")
pytest.importorskip("matplotlib")

from PySide6.QtWidgets import QApplication

from app.gui.tcc_coordinogram import TCCCoordinogramWidget
from app.postprocessor.tcc_curves import (
    CurveType, FuseClass, FuseTCCCurve, TCCCurve,
)
from app.postprocessor.tcc_damage import (
    CableDamageCurve, CableMaterial,
    MotorThermalCurve,
    TransformerThroughFaultCurve, XfmrFaultCategory,
)
from app.postprocessor.tcc_devices import MultiFunctionRelay


# ---------------------------------------------------------------------------
# QApplication fixture
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


# ---------------------------------------------------------------------------
# δ.1 — TCCDevice no widget
# ---------------------------------------------------------------------------


class TestTCCDeviceInWidget:

    def _make_relay(self):
        return MultiFunctionRelay.relay_51_50_49(
            device_id="R-MOT",
            curve_type=CurveType.IEC_STANDARD_INVERSE,
            pickup_51_A=120, tms_51=0.20,
            pickup_50_A=1500,
            pickup_49_A=130, delay_49_s=8.0,
            manufacturer="SEL", model="751",
        )

    def test_widget_accepts_TCCDevice(self, qapp):
        relay = self._make_relay()
        w = TCCCoordinogramWidget([relay], fault_current_A=2000)
        assert len(w._curves) == 1

    def test_TCCDevice_is_drag_able(self, qapp):
        """TCCDevice (composite) entra em line_artists."""
        relay = self._make_relay()
        w = TCCCoordinogramWidget([relay], fault_current_A=2000)
        assert len(w._line_artists) == 1

    def test_legacy_TCCCurve_still_works(self, qapp):
        """Backward compat: TCCCurve v1.1.0 continua funcional."""
        legacy = TCCCurve(
            relay_id="R-LEGACY",
            curve_type=CurveType.IEC_VERY_INVERSE,
            pickup_A=100, tms=0.30,
        )
        w = TCCCoordinogramWidget([legacy], fault_current_A=1000)
        assert len(w._line_artists) == 1


# ---------------------------------------------------------------------------
# δ.2 — Damage curves no widget
# ---------------------------------------------------------------------------


class TestDamageCurvesInWidget:

    def test_widget_accepts_cable_damage(self, qapp):
        c = CableDamageCurve(
            cable_id="C1", section_mm2=50,
            material=CableMaterial.Cu_XLPE,
        )
        w = TCCCoordinogramWidget([c], fault_current_A=5000)
        assert len(w._curves) == 1

    def test_damage_NOT_in_line_artists(self, qapp):
        """Damage não é arrastável — fora de _line_artists."""
        c = CableDamageCurve(
            cable_id="C1", section_mm2=50,
            material=CableMaterial.Cu_XLPE,
        )
        w = TCCCoordinogramWidget([c], fault_current_A=5000)
        assert len(w._line_artists) == 0

    def test_widget_accepts_xfmr_through_fault(self, qapp):
        x = TransformerThroughFaultCurve(
            xfmr_id="T1", rated_current_A=100,
            category=XfmrFaultCategory.FREQUENT,
        )
        w = TCCCoordinogramWidget([x], fault_current_A=2000)
        assert len(w._curves) == 1
        assert len(w._line_artists) == 0

    def test_widget_accepts_motor_thermal(self, qapp):
        m = MotorThermalCurve(motor_id="M1", fla_A=100)
        w = TCCCoordinogramWidget([m], fault_current_A=600)
        assert len(w._curves) == 1
        assert len(w._line_artists) == 0


# ---------------------------------------------------------------------------
# δ.3 — Mix completo (smoke test integrado)
# ---------------------------------------------------------------------------


class TestMixedTypes:

    def _make_full_mix(self):
        """5 tipos diferentes simulando coord real."""
        return [
            # Legacy v1.1.0
            TCCCurve(
                relay_id="R-LEGACY",
                curve_type=CurveType.IEC_VERY_INVERSE,
                pickup_A=80, tms=0.10,
            ),
            # Multi-function relay (β)
            MultiFunctionRelay.relay_51_50_49(
                device_id="R-MOT",
                curve_type=CurveType.IEC_STANDARD_INVERSE,
                pickup_51_A=120, tms_51=0.20,
                pickup_50_A=1500,
                pickup_49_A=130, delay_49_s=8.0,
            ),
            # Fuse v1.1.0
            FuseTCCCurve("F-MAIN", FuseClass.gG, rated_current_A=200),
            # Damage curves (γ)
            CableDamageCurve("C-FEEDER", section_mm2=50,
                              material=CableMaterial.Cu_XLPE),
            TransformerThroughFaultCurve("T1", rated_current_A=100,
                                          category=XfmrFaultCategory.FREQUENT),
            MotorThermalCurve("M1", fla_A=100),
        ]

    def test_widget_renders_6_mixed_types_no_crash(self, qapp):
        curves = self._make_full_mix()
        w = TCCCoordinogramWidget(curves, fault_current_A=3000)
        assert len(w._curves) == 6

    def test_only_3_drag_able_in_full_mix(self, qapp):
        """TCCCurve + Device + Fuse = 3 drag-able. 3 damage = 0."""
        curves = self._make_full_mix()
        w = TCCCoordinogramWidget(curves, fault_current_A=3000)
        assert len(w._line_artists) == 3

    def test_no_crash_when_drawing_violations(self, qapp):
        """Coord par-a-par envolvendo damage NÃO deve crashar."""
        curves = self._make_full_mix()
        # Construtor já chama _draw_all() que chama _draw_violations
        w = TCCCoordinogramWidget(curves, fault_current_A=3000)
        # Se chegou aqui, não crashou
        assert w is not None


# ---------------------------------------------------------------------------
# Set/get curves (API de modificação)
# ---------------------------------------------------------------------------


class TestSetCurves:

    def test_set_curves_resets_with_new_mix(self, qapp):
        c_old = TCCCurve(
            relay_id="old", curve_type=CurveType.IEC_VERY_INVERSE,
            pickup_A=100, tms=0.3,
        )
        w = TCCCoordinogramWidget([c_old])
        assert len(w._curves) == 1

        c_new1 = MultiFunctionRelay.relay_51_only(
            device_id="new", curve_type=CurveType.IEC_STANDARD_INVERSE,
            pickup_A=80, tms=0.2,
        )
        c_new2 = CableDamageCurve(
            cable_id="C", section_mm2=50,
            material=CableMaterial.Cu_PVC,
        )
        w.set_curves([c_new1, c_new2])
        assert len(w._curves) == 2
        # Damage não conta como drag-able
        assert len(w._line_artists) == 1


# ---------------------------------------------------------------------------
# δ.3 — Violation marker (proteção × damage cruzamento)
# ---------------------------------------------------------------------------


class TestViolationMarker:

    def test_violation_with_slow_relay_and_small_cable(self, qapp):
        """Relé MUITO lento (TMS=1.5) + cabo pequeno (4mm² PVC)
        em I=1000A:
        - t_relay ≈ 83s (IEC SI tms=1.5)
        - t_cable_damage = (115·4)²/1000² = 0.21s
        → violation (cabo derrete bem antes do relé)
        """
        slow_relay = TCCCurve(
            relay_id="R-SLOW",
            curve_type=CurveType.IEC_STANDARD_INVERSE,
            pickup_A=80, tms=1.5,
        )
        small_cable = CableDamageCurve(
            cable_id="C-SMALL", section_mm2=4,
            material=CableMaterial.Cu_PVC,
        )
        w = TCCCoordinogramWidget(
            [slow_relay, small_cable], fault_current_A=1000,
        )
        markers = [a for a in w._ax.lines if a.get_marker() == "x"]
        assert len(markers) == 1, (
            f"Esperado 1 violation marker, obtido {len(markers)}"
        )

    def test_no_violation_with_fast_relay_and_big_cable(self, qapp):
        """Relé rápido (TMS=0.05) + cabo grande (240mm² XLPE)
        → sem violation."""
        fast_relay = TCCCurve(
            relay_id="R-FAST",
            curve_type=CurveType.IEC_STANDARD_INVERSE,
            pickup_A=80, tms=0.05,
        )
        big_cable = CableDamageCurve(
            cable_id="C-BIG", section_mm2=240,
            material=CableMaterial.Cu_XLPE,
        )
        w = TCCCoordinogramWidget(
            [fast_relay, big_cable], fault_current_A=1000,
        )
        markers = [a for a in w._ax.lines if a.get_marker() == "x"]
        assert len(markers) == 0

    def test_no_violation_check_when_only_protections(self, qapp):
        """Sem damage curves → função early-returns, sem markers."""
        r1 = TCCCurve(
            relay_id="R1",
            curve_type=CurveType.IEC_VERY_INVERSE,
            pickup_A=200, tms=0.5,
        )
        r2 = TCCCurve(
            relay_id="R2",
            curve_type=CurveType.IEC_VERY_INVERSE,
            pickup_A=80, tms=0.1,
        )
        w = TCCCoordinogramWidget([r1, r2], fault_current_A=2000)
        markers = [a for a in w._ax.lines if a.get_marker() == "x"]
        assert len(markers) == 0

    def test_no_violation_check_when_only_damages(self, qapp):
        """Sem proteções → não há contra o que checar."""
        c = CableDamageCurve(
            cable_id="C", section_mm2=50,
            material=CableMaterial.Cu_XLPE,
        )
        w = TCCCoordinogramWidget([c], fault_current_A=1000)
        markers = [a for a in w._ax.lines if a.get_marker() == "x"]
        assert len(markers) == 0

    def test_violation_with_device_vs_damage(self, qapp):
        """TCCDevice (composite muito lento) vs cable damage."""
        slow_device = MultiFunctionRelay.relay_51_only(
            device_id="R-DEV",
            curve_type=CurveType.IEC_STANDARD_INVERSE,
            pickup_A=80, tms=1.5,
        )
        small_cable = CableDamageCurve(
            cable_id="C", section_mm2=4,
            material=CableMaterial.Cu_PVC,
        )
        w = TCCCoordinogramWidget(
            [slow_device, small_cable], fault_current_A=1000,
        )
        markers = [a for a in w._ax.lines if a.get_marker() == "x"]
        assert len(markers) >= 1

    def test_violation_with_xfmr_through_fault(self, qapp):
        """Relé rápido vs XFMR through-fault: depende do K.
        Para In=100A, K_FREQUENT=1250, em I=1500A (15pu):
        - t_xfmr = 1250/225 = 5.55s
        - Se relé tem TMS muito alto, viola.
        """
        # Relé propositalmente muito lento
        slow_relay = TCCCurve(
            relay_id="R-VERY-SLOW",
            curve_type=CurveType.IEC_STANDARD_INVERSE,
            pickup_A=120, tms=2.0,  # absurdo
        )
        xfmr = TransformerThroughFaultCurve(
            xfmr_id="T1", rated_current_A=100,
            category=XfmrFaultCategory.FREQUENT,
        )
        w = TCCCoordinogramWidget(
            [slow_relay, xfmr], fault_current_A=1500,
        )
        markers = [a for a in w._ax.lines if a.get_marker() == "x"]
        assert len(markers) >= 1
