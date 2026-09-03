"""
tests/test_pp_v0_95_0_cable_sizing.py — v0.95.0:

Dimensionamento de cabos NBR 5410 / NEC 310 / IEC 60364.

Cobertura:

* dimension_cable() — algoritmo de iteração + critérios
* Validação física dos inputs
* Fatores de correção (temperatura, agrupamento)
* 3 critérios: ampacidade + V-drop + estresse térmico
* Lookup por (material, insulation, installation)
* CableDesign dataclass: summary(), is_acceptable
* voltage_drop_percent() — API pública independente
"""

from __future__ import annotations

import pytest

from app.postprocessor.cable_sizing import (
    CableDesign,
    ConductorMaterial,
    Insulation,
    InstallationMethod,
    STANDARD_SECTIONS_MM2,
    dimension_cable,
    voltage_drop_percent,
)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


class TestInputValidation:

    def test_rejects_zero_current(self):
        with pytest.raises(ValueError, match="load_current_A"):
            dimension_cable(
                load_current_A=0, rated_voltage_V=380, length_m=50,
            )

    def test_rejects_negative_current(self):
        with pytest.raises(ValueError, match="load_current_A"):
            dimension_cable(
                load_current_A=-50, rated_voltage_V=380, length_m=50,
            )

    def test_rejects_zero_voltage(self):
        with pytest.raises(ValueError, match="rated_voltage_V"):
            dimension_cable(
                load_current_A=100, rated_voltage_V=0, length_m=50,
            )

    def test_rejects_zero_length(self):
        with pytest.raises(ValueError, match="length_m"):
            dimension_cable(
                load_current_A=100, rated_voltage_V=380, length_m=0,
            )

    def test_rejects_invalid_pf(self):
        with pytest.raises(ValueError, match="power_factor"):
            dimension_cable(
                load_current_A=100, rated_voltage_V=380, length_m=50,
                power_factor=1.5,
            )

    def test_rejects_unsupported_combo(self):
        """v0.95.0: Al ainda não tabelado."""
        with pytest.raises(ValueError, match="não tabelada"):
            dimension_cable(
                load_current_A=100, rated_voltage_V=380, length_m=50,
                material=ConductorMaterial.ALUMINUM,
            )


# ---------------------------------------------------------------------------
# Standard sizing scenarios
# ---------------------------------------------------------------------------


class TestStandardSizing:

    def test_lv_feeder_200A_typical(self):
        """Feeder LV 380V — 200A — Cu PVC B1 → 95 mm²."""
        r = dimension_cable(
            load_current_A=200,
            rated_voltage_V=380,
            length_m=50,
        )
        assert r.section_mm2 == 95
        assert r.is_acceptable
        assert r.passes_ampacity
        assert r.passes_voltage_drop

    def test_small_load_uses_smallest_section(self):
        """Carga 10A → bitola mínima padrão."""
        r = dimension_cable(
            load_current_A=10,
            rated_voltage_V=220,
            length_m=20,
        )
        assert r.section_mm2 == 1.5  # mínima

    def test_xlpe_higher_ampacity_than_pvc(self):
        """XLPE 90°C tem maior ampacidade que PVC 70°C."""
        for I in (100, 150):
            r_pvc = dimension_cable(
                load_current_A=I, rated_voltage_V=380, length_m=20,
                insulation=Insulation.PVC,
            )
            r_xlpe = dimension_cable(
                load_current_A=I, rated_voltage_V=380, length_m=20,
                insulation=Insulation.XLPE,
            )
            # XLPE pode usar bitola menor ou igual
            assert r_xlpe.section_mm2 <= r_pvc.section_mm2

    def test_a1_lower_ampacity_than_b1(self):
        """A1 (embutido) dissipa menos calor que B1 (aparente)
        → exige bitola maior para mesma carga."""
        for I in (100, 200):
            r_a1 = dimension_cable(
                load_current_A=I, rated_voltage_V=380, length_m=20,
                installation=InstallationMethod.A1,
            )
            r_b1 = dimension_cable(
                load_current_A=I, rated_voltage_V=380, length_m=20,
                installation=InstallationMethod.B1,
            )
            assert r_a1.section_mm2 >= r_b1.section_mm2


# ---------------------------------------------------------------------------
# Voltage drop
# ---------------------------------------------------------------------------


class TestVoltageDrop:

    def test_long_cable_increases_section(self):
        """Cabo longo força bitola maior por V-drop."""
        r_short = dimension_cable(
            load_current_A=50, rated_voltage_V=380, length_m=10,
        )
        r_long = dimension_cable(
            load_current_A=50, rated_voltage_V=380, length_m=300,
        )
        assert r_long.section_mm2 >= r_short.section_mm2
        assert r_long.voltage_drop_pct > r_short.voltage_drop_pct

    def test_v_drop_within_4pct_default(self):
        """Default limit é 4% NBR 5410 §6.2.7."""
        r = dimension_cable(
            load_current_A=100, rated_voltage_V=380, length_m=100,
        )
        assert r.voltage_drop_pct <= 4.0
        assert r.voltage_drop_limit_pct == 4.0

    def test_motor_starting_uses_7pct(self):
        """Partida de motor permite 7% (cliente pode definir)."""
        r = dimension_cable(
            load_current_A=200, rated_voltage_V=380, length_m=80,
            voltage_drop_limit_pct=7.0,
        )
        assert r.voltage_drop_limit_pct == 7.0

    def test_voltage_drop_percent_api(self):
        """API pública voltage_drop_percent funciona."""
        v = voltage_drop_percent(
            load_current_A=100, length_m=100, section_mm2=35,
        )
        assert 0 < v < 10  # razoável

    def test_voltage_drop_proportional_to_length(self):
        """Dobrar L dobra V-drop (aproximadamente)."""
        v1 = voltage_drop_percent(100, 50, 35)
        v2 = voltage_drop_percent(100, 100, 35)
        assert abs(v2 - 2 * v1) < 0.05

    def test_voltage_drop_inversely_proportional_to_section(self):
        """Dobrar seção reduz V-drop (~metade)."""
        v_small = voltage_drop_percent(100, 50, 16)
        v_large = voltage_drop_percent(100, 50, 35)
        assert v_large < v_small / 1.5


# ---------------------------------------------------------------------------
# Correction factors
# ---------------------------------------------------------------------------


class TestCorrectionFactors:

    def test_high_ambient_temp_increases_section(self):
        """50°C ambiente reduz Iz → exige bitola maior."""
        r_30c = dimension_cable(
            load_current_A=100, rated_voltage_V=380, length_m=20,
            ambient_temp_C=30,
        )
        r_50c = dimension_cable(
            load_current_A=100, rated_voltage_V=380, length_m=20,
            ambient_temp_C=50,
        )
        assert r_50c.section_mm2 >= r_30c.section_mm2
        assert r_50c.fc_temperature < r_30c.fc_temperature

    def test_grouping_reduces_ampacity(self):
        """Agrupar 6 circuitos reduz Iz para 0.57 → bitola maior."""
        r_solo = dimension_cable(
            load_current_A=80, rated_voltage_V=380, length_m=20,
            n_circuits=1,
        )
        r_grouped = dimension_cable(
            load_current_A=80, rated_voltage_V=380, length_m=20,
            n_circuits=6,
        )
        assert r_grouped.fc_grouping < r_solo.fc_grouping
        assert r_grouped.section_mm2 >= r_solo.section_mm2

    def test_extreme_grouping_warns(self):
        """FC < 0.5 emite warning."""
        r = dimension_cable(
            load_current_A=80, rated_voltage_V=380, length_m=20,
            n_circuits=20, ambient_temp_C=55,
        )
        assert any("FC_total" in w for w in r.warnings)

    def test_grouping_factor_is_banded_not_interpolated(self):
        """Tabela 42 NBR 5410 é uma função em degraus (faixas 9-11,
        12-15, 16-19, ≥20 com fator ÚNICO cada) — confirmado contra a
        reprodução oficial da Prysmian (Guia BT, Tabela 13, conforme
        Tabela 42 da NBR 5410:2004). Regressão: uma versão anterior
        interpolava linearmente entre os extremos de cada faixa,
        produzindo fatores (ex. 0.48 para 10 circuitos) que não
        existem na norma."""
        from app.postprocessor.cable_sizing import _fc_grouping
        # Mesma faixa → mesmo fator (sem interpolação)
        assert _fc_grouping(9) == _fc_grouping(10) == _fc_grouping(11) == 0.50
        assert _fc_grouping(12) == _fc_grouping(15) == 0.45
        assert _fc_grouping(16) == _fc_grouping(19) == 0.41
        assert _fc_grouping(20) == _fc_grouping(30) == 0.38
        # Faixas adjacentes 1-8: valor próprio, conferido linha a linha
        assert [_fc_grouping(n) for n in range(1, 9)] == [
            1.00, 0.80, 0.70, 0.65, 0.60, 0.57, 0.54, 0.52,
        ]


# ---------------------------------------------------------------------------
# Thermal stress (SC current)
# ---------------------------------------------------------------------------


class TestThermalStress:

    def test_sc_check_increases_section_when_ampacity_insufficient(self):
        """SC alta + tempo longo exige bitola maior por estresse
        térmico, mesmo se ampacidade da carga seria menor."""
        r_no_sc = dimension_cable(
            load_current_A=50, rated_voltage_V=13800, length_m=100,
            insulation=Insulation.XLPE,
        )
        r_with_sc = dimension_cable(
            load_current_A=50, rated_voltage_V=13800, length_m=100,
            insulation=Insulation.XLPE,
            sc_current_kA=20.0, sc_clearing_time_s=0.5,
        )
        # Estresse térmico exige > 95 mm²
        assert r_with_sc.section_mm2 >= r_no_sc.section_mm2
        assert r_with_sc.thermal_min_section_mm2 is not None
        assert r_with_sc.thermal_min_section_mm2 > 50

    def test_thermal_constant_K_xlpe_higher_than_pvc(self):
        """K_XLPE = 143 vs K_PVC = 115 → XLPE permite bitola
        menor para mesma SC."""
        # Caso onde estresse térmico domina
        kwargs = dict(
            load_current_A=10, rated_voltage_V=13800, length_m=100,
            sc_current_kA=20.0, sc_clearing_time_s=0.5,
        )
        r_pvc = dimension_cable(**kwargs, insulation=Insulation.PVC)
        r_xlpe = dimension_cable(**kwargs, insulation=Insulation.XLPE)
        assert r_pvc.thermal_min_section_mm2 > r_xlpe.thermal_min_section_mm2


# ---------------------------------------------------------------------------
# CableDesign dataclass
# ---------------------------------------------------------------------------


class TestCableDesign:

    def test_summary_contains_key_fields(self):
        r = dimension_cable(
            load_current_A=100, rated_voltage_V=380, length_m=30,
        )
        s = r.summary()
        assert "Bitola" in s
        assert "Ampacidade" in s
        assert "Queda de tensão" in s
        assert "NBR 5410" in s
        assert ("APROVADO" in s or "INADEQUADO" in s)

    def test_is_acceptable_when_all_criteria_pass(self):
        r = dimension_cable(
            load_current_A=50, rated_voltage_V=380, length_m=30,
        )
        assert r.is_acceptable

    def test_citation_present(self):
        r = dimension_cable(
            load_current_A=50, rated_voltage_V=380, length_m=30,
        )
        assert "NBR 5410" in r.citation


# ---------------------------------------------------------------------------
# Standard sections list
# ---------------------------------------------------------------------------


class TestStandardSections:

    def test_standard_sections_monotonic(self):
        """Bitolas em ordem crescente."""
        for i in range(len(STANDARD_SECTIONS_MM2) - 1):
            assert (
                STANDARD_SECTIONS_MM2[i]
                < STANDARD_SECTIONS_MM2[i + 1]
            )

    def test_includes_common_sizes(self):
        for s in (1.5, 2.5, 4, 6, 10, 16, 25, 35, 50, 95, 240):
            assert s in STANDARD_SECTIONS_MM2
