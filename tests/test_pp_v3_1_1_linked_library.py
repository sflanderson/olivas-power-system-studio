"""
tests/test_pp_v3_1_1_linked_library.py — v3.1.1 Sprint 3.

Library link/unlink — PpProperty.linked_library field (PTW Tutorial §Part 1 p.55).

Cobre:
* PpProperty.linked_library default None (backward-compat)
* Settable to a string (vendor library identifier)
* Backward-compat: existing PpComponent w/ properties without the field still parse
"""

from __future__ import annotations

import pytest


class TestPpPropertyLinkedLibrary:

    def test_default_none(self):
        from app.preprocessor.models import PpProperty
        p = PpProperty(value="10")
        assert p.linked_library is None

    def test_set_to_vendor_string(self):
        from app.preprocessor.models import PpProperty
        p = PpProperty(value="12.5", linked_library="ABB SACE T7")
        assert p.linked_library == "ABB SACE T7"

    def test_positional_args_backward_compat(self):
        """Old code passing only (value, visible) still works."""
        from app.preprocessor.models import PpProperty
        p = PpProperty("5", True)
        assert p.value == "5"
        assert p.visible is True
        assert p.linked_library is None

    def test_keyword_args_all_three(self):
        from app.preprocessor.models import PpProperty
        p = PpProperty(value="10", visible=True, linked_library="WEG")
        assert p.value == "10"
        assert p.visible is True
        assert p.linked_library == "WEG"

    def test_unlink_by_setting_none(self):
        """Unlink restaura comportamento normal."""
        from app.preprocessor.models import PpProperty
        p = PpProperty(value="10", linked_library="ABB")
        p.linked_library = None
        assert p.linked_library is None


class TestComponentWithLinkedProps:

    def test_component_with_mixed_linked_unlinked_props(self):
        """PpComponent pode ter props com/sem link, ambos coexistem."""
        from app.preprocessor.models import PpComponent, PpProperty
        comp = PpComponent(
            type="BREAKER",
            name="Q1",
            visible=True,
            x=100, y=100,
            label_dx=15, label_dy=-20, mirror=0, rotation=0,
            properties=[
                PpProperty("Q-01", True),  # tag (manual)
                PpProperty("15.0", True, linked_library="ABB HD4"),  # rated_voltage_kV (linked)
                PpProperty("1200.0", True, linked_library="ABB HD4"),  # rated_current_A (linked)
                PpProperty("25.0", False),  # breaking_capacity_kA (manual)
            ],
        )
        # Two are linked, two are manual
        linked = [p for p in comp.properties if p.linked_library is not None]
        manual = [p for p in comp.properties if p.linked_library is None]
        assert len(linked) == 2
        assert len(manual) == 2
        assert all(p.linked_library == "ABB HD4" for p in linked)


class TestSeventhGuaranteeAccessibility:

    def test_models_documents_link_feature(self):
        """Docstring de PpProperty.linked_library cita Tutorial §Part 1."""
        with open(
            "D:/000 - UFMG - DOUTORADO/MVP/app/preprocessor/models.py",
            encoding="utf-8",
        ) as f:
            content = f.read()
        assert "linked_library" in content
        assert "PTW Tutorial" in content
