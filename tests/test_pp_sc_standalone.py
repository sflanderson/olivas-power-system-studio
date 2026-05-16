"""
tests/test_pp_sc_standalone.py — v0.27.11.1: modo standalone
de cálculo de SC (estilo SKM PTW / ETAP) sem fluxo de potência.

Cobre:

* BusPipelineConfig.resolve_voltage_factor_c() —
  auto-classificação por nível de tensão (IEC 60909-0 Table 1)
  e override explícito.
* calculation_kind="max" vs "min" para c_max/c_min.
* Behavior LV-residential (230/400V), LV-industrial,
  MV (1-35 kV), HV (>35 kV).
* Backward compatibility: voltage_factor_c=None (default)
  ainda gera c válido.

Referências
============

IEC 60909-0:2016 Table 1:

  +----------------+--------+--------+
  | Sistema        | c_max  | c_min  |
  +================+========+========+
  | LV residencial |  1.05  |  0.95  |
  | LV industrial  |  1.10  |  0.95  |
  | MV (1-35 kV)   |  1.10  |  1.00  |
  | HV (>35 kV)    |  1.10  |  1.00  |
  +----------------+--------+--------+

* c_max para máxima Ik'' — dimensionamento.
* c_min para mínima Ik'' — sensibilidade da proteção.
"""

from __future__ import annotations

import pytest

from app.postprocessor.bus_pipeline import BusPipelineConfig
from app.postprocessor.short_circuit import ShortCircuitNetwork
from app.standards.iec60909 import (
    VoltageLevel, classify_voltage, voltage_factor_c,
)


# ---------------------------------------------------------------------------
# resolve_voltage_factor_c
# ---------------------------------------------------------------------------


class TestResolveVoltageFactor:

    def test_none_explicit_c_auto_classifies_LV(self):
        """
        Para 0.4 kV (LV industrial) com kind=max: c=1.10.
        """
        config = BusPipelineConfig()
        c = config.resolve_voltage_factor_c(rated_voltage_kV=0.4)
        assert c == 1.10

    def test_none_explicit_c_auto_classifies_MV(self):
        """13.8 kV (MV) com kind=max: c=1.10."""
        config = BusPipelineConfig()
        c = config.resolve_voltage_factor_c(rated_voltage_kV=13.8)
        assert c == 1.10

    def test_none_explicit_c_auto_classifies_HV(self):
        """138 kV (HV) com kind=max: c=1.10."""
        config = BusPipelineConfig()
        c = config.resolve_voltage_factor_c(rated_voltage_kV=138.0)
        assert c == 1.10

    def test_kind_min_MV(self):
        """13.8 kV (MV) com kind=min: c=1.00."""
        config = BusPipelineConfig(calculation_kind="min")
        c = config.resolve_voltage_factor_c(rated_voltage_kV=13.8)
        assert c == 1.00

    def test_kind_min_HV(self):
        """138 kV (HV) com kind=min: c=1.00."""
        config = BusPipelineConfig(calculation_kind="min")
        c = config.resolve_voltage_factor_c(rated_voltage_kV=138.0)
        assert c == 1.00

    def test_kind_min_LV(self):
        """0.4 kV (LV industrial) com kind=min: c=0.95."""
        config = BusPipelineConfig(calculation_kind="min")
        c = config.resolve_voltage_factor_c(rated_voltage_kV=0.4)
        assert c == 0.95

    def test_explicit_voltage_factor_overrides(self):
        """
        Quando voltage_factor_c é explícito, override total —
        ignora kind e auto-classificação.
        """
        config = BusPipelineConfig(
            voltage_factor_c=1.07,
            calculation_kind="min",      # ignorado
        )
        c = config.resolve_voltage_factor_c(rated_voltage_kV=13.8)
        assert c == 1.07

    def test_consistent_with_iec_module(self):
        """
        BusPipelineConfig.resolve() deve ser consistente com
        app.standards.iec60909.voltage_factor_c().
        """
        for V_kV in [0.230, 0.4, 6.6, 13.8, 69.0, 138.0, 230.0]:
            for kind in ("max", "min"):
                config = BusPipelineConfig(calculation_kind=kind)
                c_pipe = config.resolve_voltage_factor_c(V_kV)
                c_lib = voltage_factor_c(
                    classify_voltage(V_kV), kind=kind,
                )
                assert c_pipe == c_lib, (
                    f"Inconsistência em V={V_kV}, kind={kind}: "
                    f"pipe={c_pipe} vs lib={c_lib}"
                )


# ---------------------------------------------------------------------------
# Standalone SC integration (sem PF) — comparação max vs min
# ---------------------------------------------------------------------------


class TestStandaloneScMaxVsMin:
    """
    Cenário SKM PTW-style: rede com utility 500 MVA em 13.8 kV.

    Em SKM PTW / ETAP, quando se faz o cálculo "MAX" (máximo
    Ik'' para dimensionar equipamentos), usa-se c_max nas
    impedâncias E na fórmula final. Quando "MIN", c_min em
    AMBAS — para sensibilidade da proteção, valores mais
    conservadores.

    A razão final esperada Ik''_max / Ik''_min = c_max/c_min
    porque a relação Z(c) = c·V²/S e Ik'' = c·V/Z = S/V (cancela)
    NÃO se aplica quando se mede no bus DEPOIS de uma malha
    com R/X — a parte do feeder cancela, mas a parte do
    circuito interno (R/X) não. Por isso pequenos desvios
    do ratio c_max/c_min são esperados.
    """

    def test_max_consistent_kind_and_factor(self):
        """
        Modo SKM-PTW ortodoxo: c_max em todos os lugares
        para o cálculo "MAX".
        """
        # Usando c_max=1.10 para MV
        net = ShortCircuitNetwork(rated_voltage_kV=13.8)
        net.add_network_feeder(
            "UTIL", S_kQ_MVA=500.0,
            voltage_factor=1.10, r_over_x=0.10,
        )
        sc = net.calculate_at_bus("BUS", kind="max")
        # Sanity: c reportado = 1.10
        assert sc.voltage_factor_c == 1.10
        # Ik'' positivo
        assert sc.Ik_pp_kA > 0

    def test_min_consistent_kind_and_factor(self):
        """Modo SKM-PTW: c_min em todos os lugares para 'MIN'."""
        # Usando c_min=1.00 para MV
        net = ShortCircuitNetwork(rated_voltage_kV=13.8)
        net.add_network_feeder(
            "UTIL", S_kQ_MVA=500.0,
            voltage_factor=1.00, r_over_x=0.10,
        )
        sc = net.calculate_at_bus("BUS", kind="min")
        assert sc.voltage_factor_c == 1.00
        assert sc.Ik_pp_kA > 0

    def test_simple_feeder_max_min_ratio(self):
        """
        Para feeder único (sem outras impedâncias internas), a
        razão Ik''_max / Ik''_min = (c_max/c_min)² / (c_max/c_min)
        = c_max/c_min, considerando consistência max-max e
        min-min na mesma rede:

        - Z_max = c_max × V²/S; Ik''_max = c_max × V / Z_max =
          c_max × V / (c_max × V²/S) = S/V (independente!).

        Mas com o "kind" do calculate_at_bus controlando o c
        FINAL e o voltage_factor da fonte controlando Z, o
        cancelamento só ocorre se ambos forem iguais.
        """
        # max-max
        net1 = ShortCircuitNetwork(rated_voltage_kV=13.8)
        net1.add_network_feeder(
            "UTIL", S_kQ_MVA=500.0,
            voltage_factor=1.10, r_over_x=0.10,
        )
        Ik_max = net1.calculate_at_bus("BUS", kind="max").Ik_pp_kA

        # min-min
        net2 = ShortCircuitNetwork(rated_voltage_kV=13.8)
        net2.add_network_feeder(
            "UTIL", S_kQ_MVA=500.0,
            voltage_factor=1.00, r_over_x=0.10,
        )
        Ik_min = net2.calculate_at_bus("BUS", kind="min").Ik_pp_kA

        # Para feeder único, ambos cancelam (S/V equivalente):
        # Ik = c × V/√3 / (c × V²/S) = S / (V × √3)
        # Logo Ik_max ≈ Ik_min (independente de c).
        # Mas a razão pode variar se houver outras Z internas
        # — aqui é só feeder, então razão ≈ 1.0.
        ratio = Ik_max / Ik_min
        assert ratio == pytest.approx(1.0, rel=1e-3)


# ---------------------------------------------------------------------------
# Backward compatibility — None default ainda válido
# ---------------------------------------------------------------------------


class TestBackwardCompatibility:

    def test_default_config_resolves(self):
        """
        BusPipelineConfig() (defaults) deve produzir c válido
        sem erros.
        """
        config = BusPipelineConfig()
        # Default volume_factor_c=None
        assert config.voltage_factor_c is None
        assert config.calculation_kind == "max"
        # resolve_voltage_factor_c() funciona em todas as
        # tensões usuais
        for V in [0.4, 13.8, 138.0]:
            c = config.resolve_voltage_factor_c(V)
            assert 0.95 <= c <= 1.10

    def test_old_explicit_c_still_works(self):
        """
        Código antigo que passava voltage_factor_c=1.10
        explicitamente continua funcionando (não é breaking).
        """
        config = BusPipelineConfig(voltage_factor_c=1.10)
        assert config.resolve_voltage_factor_c(13.8) == 1.10


# ---------------------------------------------------------------------------
# IEC Table 1 verification (sanity)
# ---------------------------------------------------------------------------


class TestIecTable1:
    """Verifica que os valores efetivos da Table 1 estão corretos."""

    def test_lv_residential_max(self):
        c = voltage_factor_c(VoltageLevel.LV_RESIDENTIAL, "max")
        assert c == 1.05

    def test_lv_residential_min(self):
        c = voltage_factor_c(VoltageLevel.LV_RESIDENTIAL, "min")
        assert c == 0.95

    def test_lv_industrial_max(self):
        c = voltage_factor_c(VoltageLevel.LV_INDUSTRIAL, "max")
        assert c == 1.10

    def test_lv_industrial_min(self):
        c = voltage_factor_c(VoltageLevel.LV_INDUSTRIAL, "min")
        assert c == 0.95

    def test_mv_max(self):
        assert voltage_factor_c(VoltageLevel.MV, "max") == 1.10

    def test_mv_min(self):
        assert voltage_factor_c(VoltageLevel.MV, "min") == 1.00

    def test_hv_max(self):
        assert voltage_factor_c(VoltageLevel.HV, "max") == 1.10

    def test_hv_min(self):
        assert voltage_factor_c(VoltageLevel.HV, "min") == 1.00

    def test_classify_thresholds(self):
        # 1 kV ≤ → LV_INDUSTRIAL
        assert classify_voltage(0.230) == VoltageLevel.LV_INDUSTRIAL
        assert classify_voltage(0.4) == VoltageLevel.LV_INDUSTRIAL
        assert classify_voltage(1.0) == VoltageLevel.LV_INDUSTRIAL
        # 1 < V ≤ 35 → MV
        assert classify_voltage(6.6) == VoltageLevel.MV
        assert classify_voltage(13.8) == VoltageLevel.MV
        assert classify_voltage(35.0) == VoltageLevel.MV
        # > 35 → HV
        assert classify_voltage(69.0) == VoltageLevel.HV
        assert classify_voltage(138.0) == VoltageLevel.HV
        assert classify_voltage(500.0) == VoltageLevel.HV
