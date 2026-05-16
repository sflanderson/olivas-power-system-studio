"""
tests/test_pp_v1_7_3_pin_categories.py — v1.7.3.

Cobre categorização de pinos por função:

* `pin_category(name, label)` retorna "power" / "signal" / "trip" / "unknown"
* Pin dots com cores distintas por categoria
* Pin labels visíveis em select
* Topology validator (Bus→Breaker→CT→Motor)
"""

from __future__ import annotations

import pytest


# ===========================================================================
# Sprint A — Pin categorization
# ===========================================================================


class TestPinCategorize:

    def test_module_loadable(self):
        from app.gui.schematic_pp.pin_categories import (
            pin_category, PinCategory,
        )
        assert pin_category is not None

    def test_power_pins_detected(self):
        """P1/P2 (primário CT), T1/T2 (breaker linha) → power."""
        from app.gui.schematic_pp.pin_categories import (
            PinCategory, pin_category,
        )
        assert pin_category("P1", "Primário lado 1") == PinCategory.POWER
        assert pin_category("P2", "Primário lado 2") == PinCategory.POWER
        assert pin_category("T1", "Linha entrada") == PinCategory.POWER
        assert pin_category("T2", "Linha saída") == PinCategory.POWER

    def test_signal_pins_detected(self):
        """S1/S2 (secundário CT), TC_link (relé) → signal."""
        from app.gui.schematic_pp.pin_categories import (
            PinCategory, pin_category,
        )
        assert pin_category("S1", "Secundário 1") == PinCategory.SIGNAL
        assert pin_category("S2", "Secundário 2") == PinCategory.SIGNAL
        assert pin_category("TC_link", "Link ao TC") == PinCategory.SIGNAL

    def test_trip_pins_detected(self):
        """Trip_in (breaker), Trip_out (relé) → trip."""
        from app.gui.schematic_pp.pin_categories import (
            PinCategory, pin_category,
        )
        assert pin_category("Trip_in", "Trip do relé") == PinCategory.TRIP
        assert pin_category("Trip_out", "Trip → disjuntor") == PinCategory.TRIP
        assert pin_category("trip", "lower case") == PinCategory.TRIP

    def test_unknown_falls_back(self):
        """Pin name desconhecido → unknown (cor default)."""
        from app.gui.schematic_pp.pin_categories import (
            PinCategory, pin_category,
        )
        assert pin_category("XYZ", "?") == PinCategory.UNKNOWN

    def test_color_for_category_exists(self):
        from app.gui.schematic_pp.pin_categories import (
            PinCategory, color_for_category,
        )
        # Cada categoria tem cor definida
        for cat in PinCategory:
            color = color_for_category(cat)
            # QColor ou tuple RGB
            assert color is not None


# ===========================================================================
# Sprint B — Pin labels visible on select
# ===========================================================================


class TestPinLabelsVisible:

    def test_paint_pin_labels_method_exists(self):
        """ComponentItem deve ter helper para renderizar labels."""
        pytest.importorskip("PySide6")
        from app.gui.schematic_pp.items import ComponentItem
        # Helper deve existir para v1.7.3
        assert hasattr(ComponentItem, "_paint_pin_labels")


# ===========================================================================
# Sprint C — Topology validator
# ===========================================================================


class TestTopologyValidator:

    def test_validator_module_loadable(self):
        from app.preprocessor import topology_validator  # noqa: F401

    def test_validate_protection_chain_simple(self):
        """Bus → Breaker → CT → Motor com Trip do relay para Trip_in."""
        from app.preprocessor.topology_validator import (
            validate_protection_chain,
        )
        components = [
            {"id": "B1", "type": "BUS"},
            {"id": "Q1", "type": "BREAKER"},
            {"id": "TC1", "type": "CT"},
            {"id": "M1", "type": "MOTOR"},
            {"id": "R1", "type": "RELAY"},
        ]
        wires = [
            # Power chain
            {"from": "B1", "to": "Q1", "from_pin": "T_RIGHT", "to_pin": "T1"},
            {"from": "Q1", "to": "TC1", "from_pin": "T2", "to_pin": "P1"},
            {"from": "TC1", "to": "M1", "from_pin": "P2", "to_pin": "T1"},
            # Signal: TC secondary → relay
            {"from": "TC1", "to": "R1", "from_pin": "S1", "to_pin": "TC_link"},
            # Trip: relay → breaker
            {"from": "R1", "to": "Q1", "from_pin": "Trip_out", "to_pin": "Trip_in"},
        ]
        result = validate_protection_chain(
            components=components, wires=wires,
        )
        assert result.valid is True
        assert "OK" in result.message or result.errors == []

    def test_validate_missing_trip_wire(self):
        """Sem Trip wire = warn (não fatal mas registra)."""
        from app.preprocessor.topology_validator import (
            validate_protection_chain,
        )
        components = [
            {"id": "Q1", "type": "BREAKER"},
            {"id": "TC1", "type": "CT"},
            {"id": "R1", "type": "RELAY"},
        ]
        wires = [
            # Só conecta TC ao relay; sem trip wire
            {"from": "TC1", "to": "R1", "from_pin": "S1", "to_pin": "TC_link"},
        ]
        result = validate_protection_chain(
            components=components, wires=wires,
        )
        # Espera warning sobre falta de trip wire
        assert any(
            "trip" in err.lower() or "Trip_out" in err
            for err in result.errors + result.warnings
        )
