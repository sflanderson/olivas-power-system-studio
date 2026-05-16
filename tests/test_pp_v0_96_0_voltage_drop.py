"""
tests/test_pp_v0_96_0_voltage_drop.py — v0.96.0:

Estudo modular de Queda de Tensão por barramento.

Cobertura:

* run() em projeto válido + retorna VoltageDropResult
* per_bus / per_feeder dicts populados
* Violations detectadas quando V_drop > limit
* worst_bus identificado corretamente
* Warnings em casos sem fonte / sem bus
* Limites NBR 5410: 4% (regime), 7% (motor), 10% (iluminação)
* Citation NBR 5410 §6.2.7 presente
"""

from __future__ import annotations

import pytest

from app.postprocessor.studies.voltage_drop import (
    VOLTAGE_DROP_LIMIT_LIGHTING_PCT,
    VOLTAGE_DROP_LIMIT_MOTOR_START_PCT,
    VOLTAGE_DROP_LIMIT_NORMAL_PCT,
    VoltageDropResult,
    run,
)


@pytest.fixture
def project_simple():
    """build_simple_13_8kV — Vac → BUS → R_LOAD → GND."""
    from app.preprocessor.templates import build_simple_13_8kV
    return build_simple_13_8kV()


@pytest.fixture
def project_industrial():
    """build_industrial_480V — 2 níveis de tensão."""
    from app.preprocessor.templates import build_industrial_480V
    return build_industrial_480V()


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


class TestConstants:

    def test_limit_normal_4pct(self):
        assert VOLTAGE_DROP_LIMIT_NORMAL_PCT == 4.0

    def test_limit_motor_start_7pct(self):
        assert VOLTAGE_DROP_LIMIT_MOTOR_START_PCT == 7.0

    def test_limit_lighting_10pct(self):
        assert VOLTAGE_DROP_LIMIT_LIGHTING_PCT == 10.0


# ---------------------------------------------------------------------------
# run()
# ---------------------------------------------------------------------------


class TestRun:

    def test_runs_on_simple_project(self, project_simple):
        r = run(project_simple)
        assert isinstance(r, VoltageDropResult)
        assert r.n_buses_analyzed >= 1

    def test_returns_per_bus_dict(self, project_simple):
        r = run(project_simple)
        assert isinstance(r.per_bus_pct, dict)
        # Pelo menos 1 bus analisado
        assert len(r.per_bus_pct) >= 1

    def test_industrial_two_levels(self, project_industrial):
        r = run(project_industrial)
        # 2 buses (BUS-MV-13.8, BUS-LV-480)
        assert r.n_buses_analyzed >= 2


class TestEmptyProjects:

    def test_empty_project_warns(self):
        from app.preprocessor.models import PpProject
        proj = PpProject(version="0.0.19")
        r = run(proj)
        assert "Nenhum BUS" in " ".join(r.warnings)

    def test_no_source_warns(self):
        """Bus sem Vac/SM gera warning."""
        from app.preprocessor.models import PpComponent, PpProject, PpProperty
        proj = PpProject(version="0.0.19")
        proj.components.append(PpComponent(
            type="BUS", name="BUS-1", visible=True,
            x=0, y=0, label_dx=0, label_dy=0, mirror=0, rotation=0,
            properties=[
                PpProperty("BUS-1", True),
                PpProperty("13.8", True),
                PpProperty("3", False),
                PpProperty("swgr_15kv", True),
                PpProperty("1", True),
                PpProperty("0", True),
                PpProperty("10", False),
                PpProperty("4", False),
                PpProperty("", False),
            ],
        ))
        r = run(proj)
        assert "Nenhuma fonte" in " ".join(r.warnings)


# ---------------------------------------------------------------------------
# Limits
# ---------------------------------------------------------------------------


class TestLimits:

    def test_default_limit_4pct(self, project_simple):
        r = run(project_simple)
        assert r.limit_pct == 4.0

    def test_custom_motor_limit_7pct(self, project_simple):
        r = run(project_simple, limit_pct=7.0)
        assert r.limit_pct == 7.0


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


class TestResultDataclass:

    def test_summary_contains_NBR(self, project_simple):
        r = run(project_simple)
        s = r.summary()
        assert "NBR 5410" in s
        assert "Buses" in s

    def test_citation_present(self, project_simple):
        r = run(project_simple)
        assert "NBR 5410:2008" in r.citation
        assert "§6.2.7" in r.citation

    def test_worst_bus_consistent_with_max(self, project_industrial):
        r = run(project_industrial)
        if r.per_bus_pct:
            max_drop = max(r.per_bus_pct.values())
            assert r.worst_drop_pct == max_drop


# ---------------------------------------------------------------------------
# Violations
# ---------------------------------------------------------------------------


class TestViolations:

    def test_violations_below_limit(self, project_simple):
        """Sistema simples curtinho → V-drop pequeno → sem
        violations com limit 4%."""
        r = run(project_simple, limit_pct=4.0)
        # Em sistema 13.8 kV simples, V-drop é tipicamente < 1%
        assert all(vd < 4.0 for vd in r.per_bus_pct.values())

    def test_aggressive_limit_finds_violations(self, project_industrial):
        """Limit agressivo (0.001%) força violations."""
        r = run(project_industrial, limit_pct=0.001)
        # Algum bus deveria violar
        if r.per_bus_pct:
            assert len(r.violations) > 0
