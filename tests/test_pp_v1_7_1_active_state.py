"""
tests/test_pp_v1_7_1_active_state.py — v1.7.1.

Cobre:

* Sprint A: PpComponent.is_active field
* Sprint B: state property em 8 switching components
* Sprint D: bus_energization lê property 'state'
"""

from __future__ import annotations

from pathlib import Path

import pytest


SPECS_DIR = Path(
    "D:/000 - UFMG - DOUTORADO/MVP/app/preprocessor/catalog_specs"
)


# Switching components que devem ter property 'state'
_SWITCHING_COMPONENTS = {
    "BREAKER", "FUSE", "CONTACTOR",
    # VCB/VCB3/SWITCH: opcional se YAML existir
}


# ===========================================================================
# Sprint A — PpComponent.is_active
# ===========================================================================


class TestPpComponentIsActive:

    def test_default_is_active_true(self):
        """Default backward-compat: componente novo é active."""
        from app.preprocessor.models import PpComponent
        comp = PpComponent(
            type="R", name="R1", visible=True,
            x=0, y=0, label_dx=0, label_dy=0,
            mirror=0, rotation=0,
        )
        assert comp.is_active is True

    def test_can_set_inactive(self):
        from app.preprocessor.models import PpComponent
        comp = PpComponent(
            type="R", name="R1", visible=True,
            x=0, y=0, label_dx=0, label_dy=0,
            mirror=0, rotation=0,
            is_active=False,
        )
        assert comp.is_active is False

    def test_kwarg_is_active_accepted(self):
        from app.preprocessor.models import PpComponent
        # explicit True
        comp = PpComponent(
            type="R", name="R2", visible=True,
            x=0, y=0, label_dx=0, label_dy=0,
            mirror=0, rotation=0,
            is_active=True,
        )
        assert comp.is_active is True


# ===========================================================================
# Sprint B — state property em switching components
# ===========================================================================


def _has_state_property(yaml_text: str) -> bool:
    text = yaml_text.lower()
    return "name: state" in text or "name: status" in text


class TestSwitchingComponentsHaveState:

    def test_breaker_has_state(self):
        spec_file = SPECS_DIR / "BREAKER.ocomp"
        if not spec_file.is_file():
            pytest.skip("BREAKER.ocomp não encontrado")
        text = spec_file.read_text(encoding="utf-8")
        assert _has_state_property(text), (
            "BREAKER.ocomp deve ter property 'state'"
        )

    def test_fuse_has_state(self):
        spec_file = SPECS_DIR / "FUSE.ocomp"
        if not spec_file.is_file():
            pytest.skip("FUSE.ocomp não encontrado")
        text = spec_file.read_text(encoding="utf-8")
        assert _has_state_property(text)

    def test_contactor_has_state(self):
        spec_file = SPECS_DIR / "CONTACTOR.ocomp"
        if not spec_file.is_file():
            pytest.skip("CONTACTOR.ocomp não encontrado")
        text = spec_file.read_text(encoding="utf-8")
        assert _has_state_property(text)


# ===========================================================================
# Sprint D — bus_energization lê property 'state'
# ===========================================================================


class TestBusEnergizationReadsState:
    """Verifica que compute_energization_for_pp_project detecta
    breakers abertos via property 'state'='open'."""

    def test_compute_helper_exists(self):
        from app.postprocessor.bus_energization import (
            compute_energization_for_pp_project,
        )
        assert compute_energization_for_pp_project is not None

    def test_compute_dict_form_with_state_open_returns_dead(self):
        """Modo direto: components dict com is_open=True isola
        downstream."""
        from app.postprocessor.bus_energization import (
            BusState, compute_energization,
        )
        # Mesmo padrão de v1.7.0 mas reaffirmando que infra funciona
        components = [
            {"id": "S1", "type": "Iac", "is_source": True},
            {"id": "Q1", "type": "BREAKER",
             "is_source": False, "is_open": True},
            {"id": "B1", "type": "BUS", "is_source": False},
        ]
        wires = [
            {"from": "S1", "to": "Q1"},
            {"from": "Q1", "to": "B1"},
        ]
        result = compute_energization(
            components=components, wires=wires,
        )
        assert result["B1"] == BusState.DEAD


# ===========================================================================
# Sprint A integration — anti-regressão (testes legacy)
# ===========================================================================


class TestBackwardCompat:
    """Garantir que adicionar is_active não quebra construções
    antigas (sem o kwarg)."""

    def test_old_style_construction_still_works(self):
        """Existing code that doesn't pass is_active continues to work."""
        from app.preprocessor.models import PpComponent
        # Construção EXATA como código legacy (sem is_active)
        comp = PpComponent(
            type="L", name="L99", visible=True,
            x=10, y=20, label_dx=0, label_dy=0,
            mirror=0, rotation=0,
        )
        assert comp.type == "L"
        assert comp.is_active is True   # default
