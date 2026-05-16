"""
tests/test_pp_v3_3_1_audit_deferreds.py — v3.3.1 (4 sub-sprints).

Fecha 4 deferreds audit-driven de v3.3.0 (`docs/v3.3.0_TIER1_AUDIT.md`):

* Sub-sprint A — PowerFlowDialog N-bus (build_pf_system_from_project)
* Sub-sprint B — EquipmentEvalDialog auto-load (set_equipments do projeto)
* Sub-sprint C — KT/KG/KSO em calculate_short_circuit (correction_factor param)
* Sub-sprint D — decay μ·q em calculate_short_circuit (NEAR_TO_GENERATOR)
"""

from __future__ import annotations

import os
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication
    import sys
    return QApplication.instance() or QApplication(sys.argv)


# ===========================================================================
# Sub-sprint A — build_pf_system_from_project
# ===========================================================================


class TestSubSprintA_BuildPfFromProject:

    def test_empty_project_returns_none(self, qapp):
        from app.gui.analysis_dialogs import build_pf_system_from_project
        from app.preprocessor.models import PpProject
        proj = PpProject()
        sys_pf = build_pf_system_from_project(proj)
        assert sys_pf is None

    def test_none_project_returns_none(self, qapp):
        from app.gui.analysis_dialogs import build_pf_system_from_project
        sys_pf = build_pf_system_from_project(None)
        assert sys_pf is None

    def test_3_buses_become_slack_pq_pq(self, qapp):
        from app.gui.analysis_dialogs import build_pf_system_from_project
        from app.preprocessor.models import PpComponent, PpProject, PpProperty

        proj = PpProject()
        for i, name in enumerate(["B1", "B2", "B3"]):
            proj.components.append(PpComponent(
                type="BUS", name=name, visible=True,
                x=i*100, y=0, label_dx=10, label_dy=-20,
                mirror=0, rotation=0,
                properties=[PpProperty(name, True)],
            ))
        sys_pf = build_pf_system_from_project(proj)
        assert sys_pf is not None
        assert len(sys_pf.buses) == 3
        # First bus is slack
        from app.postprocessor.power_flow import BusType
        assert sys_pf.buses[0].type == BusType.SLACK
        # Others are PQ
        assert sys_pf.buses[1].type == BusType.PQ
        assert sys_pf.buses[2].type == BusType.PQ

    def test_branches_connect_adjacent_buses(self, qapp):
        from app.gui.analysis_dialogs import build_pf_system_from_project
        from app.preprocessor.models import PpComponent, PpProject, PpProperty

        proj = PpProject()
        for i, name in enumerate(["B1", "B2", "B3"]):
            proj.components.append(PpComponent(
                type="BUS", name=name, visible=True,
                x=i*100, y=0, label_dx=10, label_dy=-20,
                mirror=0, rotation=0,
                properties=[PpProperty(name, True)],
            ))
        sys_pf = build_pf_system_from_project(proj)
        # 3 buses → 2 branches (linear)
        assert len(sys_pf.branches) == 2

    def test_can_solve_extracted_system(self, qapp):
        """Sistema extraído deve convergir (default impedance OK)."""
        from app.gui.analysis_dialogs import build_pf_system_from_project
        from app.preprocessor.models import PpComponent, PpProject, PpProperty

        proj = PpProject()
        for i, name in enumerate(["B1", "B2"]):
            proj.components.append(PpComponent(
                type="BUS", name=name, visible=True,
                x=i*100, y=0, label_dx=10, label_dy=-20,
                mirror=0, rotation=0,
                properties=[PpProperty(name, True)],
            ))
        sys_pf = build_pf_system_from_project(proj)
        sol = sys_pf.solve()
        assert sol.converged


# ===========================================================================
# Sub-sprint B — auto-load EquipmentEvalDialog (handler in main_window)
# ===========================================================================


class TestSubSprintB_AutoLoad:

    def test_main_window_handler_calls_build_equipment(self):
        """main_window._on_show_equipment_eval imports build_equipment_from_project."""
        with open(
            "D:/000 - UFMG - DOUTORADO/MVP/app/gui/main_window.py",
            encoding="utf-8",
        ) as f:
            content = f.read()
        # Find the def _on_show_equipment_eval (handler definition, not menu wiring)
        idx = content.find("def _on_show_equipment_eval")
        assert idx >= 0
        # Within the handler body, must reference build_equipment_from_project
        snippet = content[idx:idx+2000]
        assert "build_equipment_from_project" in snippet
        assert "set_equipments" in snippet


# ===========================================================================
# Sub-sprint C — correction_factor in calculate_short_circuit
# ===========================================================================


class TestSubSprintC_CorrectionFactor:

    def test_default_correction_is_1(self):
        """Default correction_factor=1.0 produces same result as before."""
        from app.standards.iec60909 import calculate_short_circuit
        a = calculate_short_circuit(
            rated_voltage_kV=13.8,
            z_thevenin_ohm=complex(0.05, 0.50),
        )
        b = calculate_short_circuit(
            rated_voltage_kV=13.8,
            z_thevenin_ohm=complex(0.05, 0.50),
            correction_factor=1.0,
        )
        assert a.Ik_pp_kA == pytest.approx(b.Ik_pp_kA)

    def test_kt_above_1_reduces_current(self):
        """KT=1.05 amplifies Z → reduces Ik''."""
        from app.standards.iec60909 import calculate_short_circuit
        no_kt = calculate_short_circuit(
            rated_voltage_kV=13.8,
            z_thevenin_ohm=complex(0.05, 0.50),
        )
        with_kt = calculate_short_circuit(
            rated_voltage_kV=13.8,
            z_thevenin_ohm=complex(0.05, 0.50),
            correction_factor=1.05,
        )
        assert with_kt.Ik_pp_kA < no_kt.Ik_pp_kA
        # Ik is proportional to 1/|Z| → ratio = 1/1.05
        assert with_kt.Ik_pp_kA == pytest.approx(
            no_kt.Ik_pp_kA / 1.05, rel=1e-3,
        )

    def test_invalid_correction_raises(self):
        from app.standards.iec60909 import calculate_short_circuit
        with pytest.raises(ValueError):
            calculate_short_circuit(
                rated_voltage_kV=13.8,
                z_thevenin_ohm=complex(0.05, 0.50),
                correction_factor=0.0,
            )

    def test_combined_kt_kg_kso(self):
        """User pode passar KT × KG × KSO produto."""
        from app.standards.iec60909 import (
            calculate_short_circuit,
            transformer_correction_factor_KT,
            generator_correction_factor_KG,
        )
        kt = transformer_correction_factor_KT(
            voltage_factor_c_max=1.10, x_T_pu=0.05,
        )
        kg = generator_correction_factor_KG(
            voltage_factor_c_max=1.10, x_d_subtransient_pu=0.20,
        )
        combined = kt * kg
        result = calculate_short_circuit(
            rated_voltage_kV=13.8,
            z_thevenin_ohm=complex(0.05, 0.50),
            correction_factor=combined,
        )
        assert result.Ik_pp_kA > 0


# ===========================================================================
# Sub-sprint D — decay μ·q for NEAR_TO_GENERATOR
# ===========================================================================


class TestSubSprintD_DecayIntegration:

    def test_far_default_no_decay(self):
        """FAR_FROM_GENERATOR (default) → Ib = Ik = Ik''."""
        from app.standards.iec60909 import calculate_short_circuit
        result = calculate_short_circuit(
            rated_voltage_kV=13.8,
            z_thevenin_ohm=complex(0.05, 0.50),
        )
        assert result.Ib_kA == result.Ik_pp_kA
        assert result.Ik_steady_kA == result.Ik_pp_kA

    def test_near_with_decay_reduces_ib(self):
        """NEAR_TO_GENERATOR + Xd''=0.20 + t=0.05 → μ ~ 0.82 → Ib < Ik''."""
        from app.standards.iec60909 import calculate_short_circuit, FaultDistance
        result = calculate_short_circuit(
            rated_voltage_kV=13.8,
            z_thevenin_ohm=complex(0.05, 0.50),
            fault_distance=FaultDistance.NEAR_TO_GENERATOR,
            breaker_min_delay_s=0.05,
            generator_x_d_subtransient_pu=0.20,
        )
        # Ib should be reduced via μ
        assert result.Ib_kA < result.Ik_pp_kA
        # μ ≈ 0.824 for r=5, t=0.05 → Ib/Ik'' ~ 0.82
        ratio = result.Ib_kA / result.Ik_pp_kA
        assert 0.80 < ratio < 0.85

    def test_near_without_xd_falls_back(self):
        """NEAR mas sem Xd'' fornecido → fallback Ib=Ik."""
        from app.standards.iec60909 import calculate_short_circuit, FaultDistance
        result = calculate_short_circuit(
            rated_voltage_kV=13.8,
            z_thevenin_ohm=complex(0.05, 0.50),
            fault_distance=FaultDistance.NEAR_TO_GENERATOR,
            # generator_x_d_subtransient_pu=None (omitted)
        )
        # Sem dados de gerador → fallback
        assert result.Ib_kA == result.Ik_pp_kA

    def test_near_synchronous_vs_async(self):
        """Síncrono mantém ~Ib em steady; async motor decai 50%."""
        from app.standards.iec60909 import calculate_short_circuit, FaultDistance
        sync = calculate_short_circuit(
            rated_voltage_kV=13.8,
            z_thevenin_ohm=complex(0.05, 0.50),
            fault_distance=FaultDistance.NEAR_TO_GENERATOR,
            breaker_min_delay_s=0.05,
            generator_x_d_subtransient_pu=0.20,
            is_synchronous_motor=True,
        )
        async_motor = calculate_short_circuit(
            rated_voltage_kV=13.8,
            z_thevenin_ohm=complex(0.05, 0.50),
            fault_distance=FaultDistance.NEAR_TO_GENERATOR,
            breaker_min_delay_s=0.05,
            generator_x_d_subtransient_pu=0.20,
            is_synchronous_motor=False,
        )
        # Sync: Ik = Ib; Async: Ik < Ib
        assert sync.Ik_steady_kA == sync.Ib_kA
        assert async_motor.Ik_steady_kA < async_motor.Ib_kA


# ===========================================================================
# 7ª garantia — verify wiring acessível ao usuário
# ===========================================================================


class TestSeventhGuaranteeWired:

    def test_run_power_flow_uses_project(self):
        """run_power_flow_analysis tries build_pf_system_from_project first."""
        with open(
            "D:/000 - UFMG - DOUTORADO/MVP/app/gui/analysis_dialogs.py",
            encoding="utf-8",
        ) as f:
            content = f.read()
        assert "build_pf_system_from_project" in content
        assert "N-bus" in content or "N-bus path" in content

    def test_calculate_short_circuit_doc_cites_v3_3_1(self):
        """calculate_short_circuit doc cita v3.3.1 sub-sprints."""
        with open(
            "D:/000 - UFMG - DOUTORADO/MVP/app/standards/iec60909.py",
            encoding="utf-8",
        ) as f:
            content = f.read()
        assert "Sub-sprint C" in content
        assert "Sub-sprint D" in content
        assert "correction_factor" in content
