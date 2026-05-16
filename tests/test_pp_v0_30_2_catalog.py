"""
tests/test_pp_v0_30_2_catalog.py — v0.30.2: catálogo de
equipamentos industriais brasileiros.

Cobre:

* Estrutura dos dataclasses (CatalogMotor, CatalogTransformer,
  CatalogGenerator)
* Catálogo populado (9+ motores, 5+ TRs, 4+ geradores)
* list_motors / list_transformers / list_generators com
  filtros (power, voltage, manufacturer, n_poles)
* find_motor / find_transformer / find_generator (closest
  match)
* Conversores motor_catalog_to_parameters /
  generator_catalog_to_parameters
"""

from __future__ import annotations

import pytest

from app.preprocessor.equipment_catalog import (
    CatalogGenerator, CatalogMotor, CatalogTransformer,
    EfficiencyClass, GENERATOR_CATALOG, MOTOR_CATALOG,
    Manufacturer, TRANSFORMER_CATALOG,
    find_generator, find_motor, find_transformer,
    generator_catalog_to_parameters, list_generators,
    list_motors, list_transformers,
    motor_catalog_to_parameters,
)


# ---------------------------------------------------------------------------
# Catálogo populado
# ---------------------------------------------------------------------------


class TestCatalogPopulated:

    def test_motors_min_count(self):
        assert len(MOTOR_CATALOG) >= 9

    def test_transformers_min_count(self):
        assert len(TRANSFORMER_CATALOG) >= 5

    def test_generators_min_count(self):
        assert len(GENERATOR_CATALOG) >= 4

    def test_manufacturers_diversity_motors(self):
        manufacturers = {m.manufacturer for m in MOTOR_CATALOG}
        assert Manufacturer.WEG in manufacturers
        assert Manufacturer.ABB in manufacturers
        assert Manufacturer.SIEMENS in manufacturers

    def test_motor_voltage_range(self):
        """Catalogo cobre BT (380-480V) e MT (4.16, 6.6, 13.8 kV)."""
        voltages = {m.rated_voltage_kV for m in MOTOR_CATALOG}
        assert any(0.3 < v < 0.6 for v in voltages)   # BT
        assert any(3 < v < 8 for v in voltages)        # MT baixa
        assert any(v > 10 for v in voltages)            # MT alta


# ---------------------------------------------------------------------------
# Dataclass validation
# ---------------------------------------------------------------------------


class TestDataclassValidation:

    def test_motor_dataclass_fields(self):
        m = MOTOR_CATALOG[0]
        assert isinstance(m, CatalogMotor)
        assert m.rated_power_kW > 0
        assert m.rated_voltage_kV > 0
        assert 0.5 < m.rated_pf < 1.0
        assert 0.5 < m.efficiency < 1.0
        assert m.locked_rotor_current_pu >= 4.0
        assert m.locked_rotor_current_pu <= 12.0
        assert m.n_poles >= 2

    def test_transformer_dataclass_fields(self):
        t = TRANSFORMER_CATALOG[0]
        assert isinstance(t, CatalogTransformer)
        assert t.rated_power_MVA > 0
        assert t.voltage_HV_kV > t.voltage_LV_kV
        assert 1 <= t.impedance_percent <= 20
        assert t.copper_loss_kW > 0
        assert t.iron_loss_kW > 0

    def test_generator_dataclass_fields(self):
        g = GENERATOR_CATALOG[0]
        assert isinstance(g, CatalogGenerator)
        assert g.rated_power_MVA > 0
        # Hierarquia Xd > Xd' > Xd''
        assert g.Xd_pu > g.Xd_prime_pu > g.Xd_pp_pu


# ---------------------------------------------------------------------------
# list_motors
# ---------------------------------------------------------------------------


class TestListMotors:

    def test_no_filters_returns_all(self):
        assert len(list_motors()) == len(MOTOR_CATALOG)

    def test_filter_by_power_range(self):
        small = list_motors(power_min_kW=0, power_max_kW=100)
        for m in small:
            assert m.rated_power_kW <= 100

    def test_filter_by_voltage(self):
        results = list_motors(voltage_kV=4.16)
        for m in results:
            # Tolerância 5%
            assert abs(m.rated_voltage_kV - 4.16) <= 4.16 * 0.05

    def test_filter_by_manufacturer(self):
        weg_only = list_motors(manufacturer=Manufacturer.WEG)
        for m in weg_only:
            assert m.manufacturer == Manufacturer.WEG
        assert len(weg_only) >= 1

    def test_filter_by_n_poles(self):
        four_pole = list_motors(n_poles=4)
        for m in four_pole:
            assert m.n_poles == 4


# ---------------------------------------------------------------------------
# find_* (closest match)
# ---------------------------------------------------------------------------


class TestFindMotor:

    def test_finds_closest_power(self):
        m = find_motor(power_kW=1500, voltage_kV=6.6)
        assert m is not None
        assert m.rated_voltage_kV == pytest.approx(6.6, rel=0.05)

    def test_returns_none_when_no_match(self):
        # Tensão impossível 50 kV → não há motor
        m = find_motor(power_kW=100, voltage_kV=50.0)
        assert m is None

    def test_filters_by_n_poles(self):
        # Pede 6 polos
        m = find_motor(
            power_kW=1000, voltage_kV=4.16, n_poles=6,
        )
        if m is not None:
            assert m.n_poles == 6


class TestFindTransformer:

    def test_finds_closest_power(self):
        t = find_transformer(
            power_MVA=2.0, voltage_HV_kV=13.8, voltage_LV_kV=0.480,
        )
        assert t is not None
        assert t.rated_power_MVA == pytest.approx(2.0, rel=0.5)

    def test_returns_none_when_no_match(self):
        t = find_transformer(
            power_MVA=1.0, voltage_HV_kV=999.0, voltage_LV_kV=1.0,
        )
        assert t is None


class TestFindGenerator:

    def test_finds_closest(self):
        g = find_generator(power_MVA=5.0, voltage_kV=4.16)
        assert g is not None

    def test_filter_manufacturer(self):
        g = find_generator(
            power_MVA=200, voltage_kV=18.0,
            manufacturer=Manufacturer.SIEMENS,
        )
        if g is not None:
            assert g.manufacturer == Manufacturer.SIEMENS


# ---------------------------------------------------------------------------
# Converters
# ---------------------------------------------------------------------------


class TestConverters:

    def test_motor_to_parameters(self):
        m = find_motor(power_kW=200, voltage_kV=0.440)
        assert m is not None
        params = motor_catalog_to_parameters(m, "M-MAIN")
        assert params.name == "M-MAIN"
        assert params.rated_power_kW == m.rated_power_kW
        assert params.locked_rotor_current_pu == m.locked_rotor_current_pu

    def test_generator_to_parameters(self):
        g = find_generator(power_MVA=5, voltage_kV=4.16)
        assert g is not None
        params = generator_catalog_to_parameters(
            g, "GEN-1",
        )
        assert params.name == "GEN-1"
        assert params.Xd == g.Xd_pu
        assert params.Xd_prime == g.Xd_prime_pu
        assert params.Xd_pp == g.Xd_pp_pu

    def test_motor_params_usable_in_motor_starting(self):
        """Catalog motor → MotorParameters → analyze_motor_starting."""
        from app.postprocessor.motor_starting import (
            MotorStartingCase, analyze_motor_starting,
        )
        m = find_motor(power_kW=1500, voltage_kV=6.6)
        assert m is not None
        params = motor_catalog_to_parameters(m, "M-CAT")
        # Constrói cenário de partida
        case = MotorStartingCase(
            motor_name=m.model,
            motor_rated_power_kW=params.rated_power_kW,
            motor_rated_voltage_kV=params.rated_voltage_kV,
            motor_rated_pf=params.rated_pf,
            motor_efficiency=params.efficiency,
            locked_rotor_current_pu=params.locked_rotor_current_pu,
            starting_pf=params.starting_pf,
            starting_torque_pu=m.starting_torque_pu,
            load_torque_pu=1.0,
            inertia_motor_kg_m2=m.inertia_kg_m2,
            bus_pre_fault_voltage_pu=1.0,
            bus_thevenin_impedance_ohm=0.5,
            bus_rated_voltage_kV=params.rated_voltage_kV,
            n_poles=params.n_poles,
        )
        rpt = analyze_motor_starting(case)
        # Resultado físicamente plausível
        assert 0.5 < rpt.voltage_dip_pu < 1.0
        assert rpt.starting_current_kA > 0


# ---------------------------------------------------------------------------
# Sanity checks por equipamento
# ---------------------------------------------------------------------------


class TestEquipmentSanity:

    def test_all_motors_have_valid_efficiency_class(self):
        for m in MOTOR_CATALOG:
            assert m.efficiency_class in EfficiencyClass

    def test_all_motors_locked_rotor_in_range(self):
        for m in MOTOR_CATALOG:
            # NEMA Design A/B/C/D: 4-12× I_n
            assert 4.0 <= m.locked_rotor_current_pu <= 12.0

    def test_all_motors_pf_starting_lower_than_running(self):
        for m in MOTOR_CATALOG:
            assert m.starting_pf < m.rated_pf

    def test_all_transformers_HV_above_LV(self):
        for t in TRANSFORMER_CATALOG:
            assert t.voltage_HV_kV > t.voltage_LV_kV

    def test_all_generators_xd_hierarchy(self):
        """IEC: Xd > Xd' > Xd'' for all SMs."""
        for g in GENERATOR_CATALOG:
            assert g.Xd_pu > g.Xd_prime_pu
            assert g.Xd_prime_pu > g.Xd_pp_pu
