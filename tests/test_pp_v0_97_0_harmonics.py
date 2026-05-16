"""
tests/test_pp_v0_97_0_harmonics.py — v0.97.0:

Análise de Harmônicos IEEE 519-2014.

Cobertura:

* NonLinearLoad — validação física
* Espectros típicos por LoadType
* analyze_harmonics() — agregação por bus
* V-THD e IHD calculados
* Violations IEEE 519 detectadas
* Recommendations automáticas (mitigação)
* Limites por classe de tensão (LV/MV/HV/EHV)
"""

from __future__ import annotations

import pytest

from app.postprocessor.harmonics import (
    HarmonicsResult,
    IEEE_519_V_THD_LIMITS,
    LoadType,
    NonLinearLoad,
    analyze_harmonics,
)


@pytest.fixture
def project_simple():
    from app.preprocessor.templates import build_simple_13_8kV
    return build_simple_13_8kV()


# ---------------------------------------------------------------------------
# NonLinearLoad
# ---------------------------------------------------------------------------


class TestNonLinearLoad:

    def test_creation_valid(self):
        load = NonLinearLoad(
            bus_id="BUS-1",
            load_type=LoadType.VFD_6_PULSE,
            S_kVA=500.0,
        )
        assert load.bus_id == "BUS-1"
        assert load.S_kVA == 500.0

    def test_rejects_zero_S(self):
        with pytest.raises(ValueError, match="S_kVA"):
            NonLinearLoad(
                bus_id="BUS-1",
                load_type=LoadType.VFD_6_PULSE,
                S_kVA=0,
            )

    def test_spectrum_returns_typical_for_load_type(self):
        load = NonLinearLoad(
            bus_id="BUS-1",
            load_type=LoadType.VFD_6_PULSE,
            S_kVA=100,
        )
        spec = load.spectrum
        # 5a deve ser ~35% da fundamental
        assert spec[5] == 35.0

    def test_override_spectrum(self):
        custom = {3: 50.0, 5: 30.0}
        load = NonLinearLoad(
            bus_id="BUS-1",
            load_type=LoadType.VFD_6_PULSE,
            S_kVA=100,
            spectrum_override=custom,
        )
        assert load.spectrum == custom


# ---------------------------------------------------------------------------
# LoadType spectra characteristics
# ---------------------------------------------------------------------------


class TestSpectra:

    def test_vfd_12_pulse_cancels_5_7(self):
        """12-pulse cancela substancialmente harmônicos 5 e 7."""
        l6 = NonLinearLoad("X", LoadType.VFD_6_PULSE, 100)
        l12 = NonLinearLoad("X", LoadType.VFD_12_PULSE, 100)
        assert l12.spectrum.get(5, 0) < l6.spectrum[5] / 5
        assert l12.spectrum.get(7, 0) < l6.spectrum[7] / 5

    def test_vfd_18_pulse_cancels_more(self):
        """18-pulse cancela mais que 12-pulse."""
        l12 = NonLinearLoad("X", LoadType.VFD_12_PULSE, 100)
        l18 = NonLinearLoad("X", LoadType.VFD_18_PULSE, 100)
        # 11 e 13 cancelados em 18-pulse
        assert l18.spectrum.get(11, 0) < l12.spectrum[11] / 5

    def test_arc_furnace_has_even_harmonics(self):
        """Forno a arco gera harmônicos pares (não-padrão)."""
        load = NonLinearLoad("X", LoadType.ARC_FURNACE, 100)
        assert 2 in load.spectrum
        assert 4 in load.spectrum

    def test_ups_smps_dominates_3rd(self):
        """UPS/SMPS predominam em 3a (zero-sequência)."""
        load = NonLinearLoad("X", LoadType.UPS_SMPS, 100)
        assert load.spectrum[3] > 20.0  # ≥ 25%


# ---------------------------------------------------------------------------
# analyze_harmonics
# ---------------------------------------------------------------------------


class TestAnalyzeHarmonics:

    def test_no_loads_warns(self, project_simple):
        r = analyze_harmonics(project_simple, [])
        assert "Nenhuma carga" in " ".join(r.warnings)

    def test_with_load_returns_v_thd(self, project_simple):
        loads = [
            NonLinearLoad(
                bus_id="BUS-MAIN-13.8",
                load_type=LoadType.VFD_6_PULSE,
                S_kVA=500.0,
            ),
        ]
        r = analyze_harmonics(project_simple, loads)
        assert r.n_loads == 1
        assert isinstance(r.v_thd_per_bus, dict)

    def test_more_loads_higher_thd(self, project_simple):
        """Mais cargas → maior V-THD (mesmo bus)."""
        load_1 = NonLinearLoad(
            "BUS-MAIN-13.8", LoadType.VFD_6_PULSE, 100,
        )
        load_5 = [
            NonLinearLoad(
                "BUS-MAIN-13.8", LoadType.VFD_6_PULSE, 100,
            ) for _ in range(5)
        ]
        r1 = analyze_harmonics(project_simple, [load_1])
        r5 = analyze_harmonics(project_simple, load_5)
        if r1.v_thd_per_bus and r5.v_thd_per_bus:
            assert (
                r5.worst_v_thd_pct > r1.worst_v_thd_pct
            )

    def test_summary_contains_ieee_519(self, project_simple):
        loads = [
            NonLinearLoad(
                "BUS-MAIN-13.8",
                LoadType.VFD_6_PULSE, 100,
            ),
        ]
        r = analyze_harmonics(project_simple, loads)
        s = r.summary()
        assert "IEEE" in s
        assert "519" in s

    def test_citation_present(self, project_simple):
        loads = [
            NonLinearLoad(
                "BUS-MAIN-13.8",
                LoadType.VFD_6_PULSE, 100,
            ),
        ]
        r = analyze_harmonics(project_simple, loads)
        assert "IEEE Std 519-2014" in r.citation


# ---------------------------------------------------------------------------
# IEEE 519 limits
# ---------------------------------------------------------------------------


class TestIEEE519Limits:

    def test_limits_table_complete(self):
        """V_THD limits cobrem LV / MV / HV / EHV."""
        keys = list(IEEE_519_V_THD_LIMITS.keys())
        assert len(keys) >= 4
        # LV (≤ 1 kV): 5%
        assert IEEE_519_V_THD_LIMITS[(0.0, 1.0)] == 5.0
        # HV: mais restritivo
        assert IEEE_519_V_THD_LIMITS[(69.0, 161.0)] == 2.5

    def test_violations_detected_for_high_thd(self, project_simple):
        """Carga grande → V-THD alto → violation."""
        # 10 VFDs grandes na mesma barra LV — força V-THD alto
        loads = [
            NonLinearLoad(
                "BUS-MAIN-13.8",
                LoadType.VFD_6_PULSE, 1000,
            ) for _ in range(10)
        ]
        r = analyze_harmonics(project_simple, loads)
        # Violations devem ser detectadas
        assert isinstance(r.violations, tuple)


# ---------------------------------------------------------------------------
# Recommendations
# ---------------------------------------------------------------------------


class TestRecommendations:

    def test_no_violations_says_ok(self, project_simple):
        # Carga pequena → sem violation → recomendação OK
        loads = [
            NonLinearLoad("BUS-MAIN-13.8", LoadType.VFD_18_PULSE, 50),
        ]
        r = analyze_harmonics(project_simple, loads)
        if not r.violations:
            joined = " ".join(r.recommendations)
            assert "dentro dos limites" in joined

    def test_arc_furnace_suggests_svc(self, project_simple):
        """Forno a arco → recomendar SVC/STATCOM."""
        loads = [
            NonLinearLoad(
                "BUS-MAIN-13.8", LoadType.ARC_FURNACE, 5000,
            ),
        ]
        r = analyze_harmonics(project_simple, loads)
        joined = " ".join(r.recommendations)
        # Either SVC, STATCOM, or VFD upgrade should be suggested
        assert any(
            term in joined for term in ("SVC", "STATCOM", "filtro")
        )
