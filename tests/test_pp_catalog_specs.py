"""
Tests de paridade entre ``app/preprocessor/catalog_specs/*.ocomp`` e
os módulos legados (``catalog.py``, ``node_coalescer.py``, ``editor.py``).

Objetivo
--------
Na sprint v0.21.8, introduzimos o formato declarativo ``.ocomp``. Esses
testes garantem que, enquanto os módulos legados ainda são fonte-da-
verdade em runtime (até v0.21.9 fazer a inversão), o conteúdo dos
``.ocomp`` está alinhado — i.e., nenhum drift silencioso.

Cobertura
---------
Para cada ``.ocomp`` em ``catalog_specs/``:

* O ``code`` aparece em :mod:`app.preprocessor.catalog` (legado).
* O ``label_pt`` do ``.ocomp`` bate com ``CatalogEntry.label_pt`` (ou
  com ``_PROPERTY_LABELS`` dependendo do caso — ver notas).
* A ``category`` bate.
* ``atp_supported`` bate.
* O número de pinos do ``.ocomp`` bate com ``_PIN_GEOMETRY`` legado.
* As posições (x, y) dos pinos batem.
* O número de properties do ``.ocomp`` bate com
  ``_DEFAULT_PROPS`` legado (editor.py).
* O atributo ``visible`` de cada property bate.

Quando o spec tem mais metadados do que o legado (descrições,
exemplos, ``llm_hints``), isso é feature adicional do .ocomp — não é
checado contra o legado (óbvio).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.preprocessor import catalog
from app.preprocessor.node_coalescer import _PIN_GEOMETRY
from app.preprocessor.spec import ComponentSpec, ComponentSpecRegistry

CATALOG_SPECS_DIR = Path(__file__).resolve().parents[1] / (
    "app/preprocessor/catalog_specs"
)


@pytest.fixture(scope="module")
def registry() -> ComponentSpecRegistry:
    """Carrega todos os .ocomp uma vez para o módulo."""
    reg = ComponentSpecRegistry()
    reg.load_directory(CATALOG_SPECS_DIR)
    return reg


# ---------------------------------------------------------------------------
# Lazy import do editor._DEFAULT_PROPS (módulo só é importável com Qt
# disponível; os testes individuais que dependem dele pulam se Qt falta)
# ---------------------------------------------------------------------------


def _load_default_props() -> dict[str, list[tuple[str, bool]]] | None:
    pytest.importorskip("PySide6")
    from app.gui.schematic_pp.editor import _DEFAULT_PROPS
    return _DEFAULT_PROPS


# ===========================================================================
# Geral: registry carrega sem erro
# ===========================================================================


class TestRegistryLoad:
    def test_directory_exists(self) -> None:
        assert CATALOG_SPECS_DIR.is_dir(), (
            f"diretório de specs não encontrado: {CATALOG_SPECS_DIR}"
        )

    def test_at_least_10_specs(self, registry: ComponentSpecRegistry) -> None:
        # v0.21.8 introduz 10 specs (R, L, C, GND, Vdc, Vac, SwIdeal,
        # Diode, VCB, VCB3). Sprints futuras aumentam.
        assert len(registry) >= 10

    def test_expected_codes_present(
        self, registry: ComponentSpecRegistry
    ) -> None:
        expected = {
            "R", "L", "C", "GND", "Vdc", "Vac",
            "SwIdeal", "Diode", "VCB", "VCB3",
        }
        assert expected.issubset(set(registry.all_codes())), (
            f"faltando: {expected - set(registry.all_codes())}"
        )

    def test_all_specs_have_unique_codes(
        self, registry: ComponentSpecRegistry
    ) -> None:
        codes = registry.all_codes()
        assert len(codes) == len(set(codes))


# ===========================================================================
# Paridade contra catalog.py (legado)
# ===========================================================================


@pytest.mark.parametrize(
    "code",
    ["R", "L", "C", "GND", "Vdc", "Vac", "SwIdeal", "Diode", "VCB", "VCB3"],
)
class TestCatalogParity:
    """Cada .ocomp deve bater com a ``CatalogEntry`` legada."""

    def test_code_in_catalog(
        self, code: str, registry: ComponentSpecRegistry
    ) -> None:
        spec = registry.require(code)
        entry = catalog.get(spec.code)
        assert entry is not None, (
            f"code {spec.code!r} presente em .ocomp mas não em catalog.py legado"
        )

    def test_label_pt_matches(
        self, code: str, registry: ComponentSpecRegistry
    ) -> None:
        spec = registry.require(code)
        entry = catalog.get(spec.code)
        assert entry is not None
        assert spec.label_pt == entry.label_pt, (
            f"{code}: label_pt difere — spec={spec.label_pt!r} "
            f"vs catalog={entry.label_pt!r}"
        )

    def test_category_matches(
        self, code: str, registry: ComponentSpecRegistry
    ) -> None:
        spec = registry.require(code)
        entry = catalog.get(spec.code)
        assert entry is not None
        assert spec.category == entry.category, (
            f"{code}: category difere — spec={spec.category!r} "
            f"vs catalog={entry.category!r}"
        )

    def test_atp_supported_matches(
        self, code: str, registry: ComponentSpecRegistry
    ) -> None:
        spec = registry.require(code)
        entry = catalog.get(spec.code)
        assert entry is not None
        assert spec.atp_supported == entry.atp_supported


# ===========================================================================
# Paridade de pinos contra node_coalescer._PIN_GEOMETRY
# ===========================================================================


@pytest.mark.parametrize(
    "code",
    ["R", "L", "C", "GND", "Vdc", "Vac", "SwIdeal", "Diode", "VCB", "VCB3"],
)
class TestPinParity:
    """As posições dos pinos devem bater exatamente entre .ocomp e legado."""

    def test_pin_count(
        self, code: str, registry: ComponentSpecRegistry
    ) -> None:
        spec = registry.require(code)
        legacy = _PIN_GEOMETRY.get(code)
        assert legacy is not None, f"{code}: sem geometria legada"
        assert len(spec.pins) == len(legacy), (
            f"{code}: contagem de pinos difere — spec={len(spec.pins)} "
            f"vs legacy={len(legacy)}"
        )

    def test_pin_positions_match_in_order(
        self, code: str, registry: ComponentSpecRegistry
    ) -> None:
        spec = registry.require(code)
        legacy = _PIN_GEOMETRY.get(code)
        assert legacy is not None
        spec_positions = [tuple(p.position) for p in spec.pins]
        assert spec_positions == legacy, (
            f"{code}: posições de pinos diferem\n"
            f"  spec   = {spec_positions}\n"
            f"  legacy = {legacy}"
        )

    def test_pin_names_unique(
        self, code: str, registry: ComponentSpecRegistry
    ) -> None:
        spec = registry.require(code)
        names = [p.name for p in spec.pins]
        assert len(names) == len(set(names))


# ===========================================================================
# Paridade de propriedades contra editor._DEFAULT_PROPS
# ===========================================================================


@pytest.mark.parametrize(
    "code",
    ["R", "L", "C", "GND", "Vdc", "Vac", "SwIdeal", "Diode", "VCB", "VCB3"],
)
class TestPropertyParity:
    """O número e a visibilidade das propriedades deve bater."""

    def test_property_count(
        self, code: str, registry: ComponentSpecRegistry
    ) -> None:
        default_props = _load_default_props()
        if default_props is None:
            pytest.skip("Qt não disponível")
        spec = registry.require(code)
        legacy = default_props.get(code, [])
        assert len(spec.properties) == len(legacy), (
            f"{code}: contagem de props difere — spec={len(spec.properties)} "
            f"vs legacy={len(legacy)}"
        )

    def test_property_visibility_flags(
        self, code: str, registry: ComponentSpecRegistry
    ) -> None:
        default_props = _load_default_props()
        if default_props is None:
            pytest.skip("Qt não disponível")
        spec = registry.require(code)
        legacy = default_props.get(code, [])
        spec_visible = [p.visible for p in spec.properties]
        legacy_visible = [vis for (_val, vis) in legacy]
        assert spec_visible == legacy_visible, (
            f"{code}: flags de visibilidade diferem\n"
            f"  spec   = {spec_visible}\n"
            f"  legacy = {legacy_visible}"
        )


# ===========================================================================
# Sanidade do ATP emission por tipo de componente
# ===========================================================================


class TestEmissionKinds:
    """Cada componente emite o kind ATP correto."""

    def test_r_resistor(self, registry: ComponentSpecRegistry) -> None:
        assert registry.require("R").atp_emission.kind.value == "resistor"

    def test_l_inductor(self, registry: ComponentSpecRegistry) -> None:
        assert registry.require("L").atp_emission.kind.value == "inductor"

    def test_c_capacitor(self, registry: ComponentSpecRegistry) -> None:
        assert registry.require("C").atp_emission.kind.value == "capacitor"

    def test_gnd_ground(self, registry: ComponentSpecRegistry) -> None:
        assert registry.require("GND").atp_emission.kind.value == "ground"

    def test_vdc_source_dc(self, registry: ComponentSpecRegistry) -> None:
        assert registry.require("Vdc").atp_emission.kind.value == "source_dc"

    def test_vac_source_ac(self, registry: ComponentSpecRegistry) -> None:
        assert registry.require("Vac").atp_emission.kind.value == "source_ac"

    def test_swideal_simple(self, registry: ComponentSpecRegistry) -> None:
        assert registry.require("SwIdeal").atp_emission.kind.value == (
            "switch_simple"
        )

    def test_diode(self, registry: ComponentSpecRegistry) -> None:
        assert registry.require("Diode").atp_emission.kind.value == "diode"

    def test_vcb_simple(self, registry: ComponentSpecRegistry) -> None:
        """VCB 1φ ainda emite switch_simple (reignição MODEL em v0.22.1)."""
        assert registry.require("VCB").atp_emission.kind.value == (
            "switch_simple"
        )

    def test_vcb3_multi(self, registry: ComponentSpecRegistry) -> None:
        """VCB3 emite multi_switch com count=3 e 3 branches."""
        spec = registry.require("VCB3")
        assert spec.atp_emission.kind.value == "multi_switch"
        assert spec.atp_emission.count == 3
        assert len(spec.atp_emission.branches) == 3


# ===========================================================================
# VCB3 — estrutura 3φ específica
# ===========================================================================


class TestVCB3Structure:
    """VCB3 é o primeiro componente 3φ do sistema — validar com cuidado."""

    def test_six_pins(self, registry: ComponentSpecRegistry) -> None:
        spec = registry.require("VCB3")
        assert len(spec.pins) == 6

    def test_pins_per_phase(self, registry: ComponentSpecRegistry) -> None:
        from app.preprocessor.spec import PinPhase
        spec = registry.require("VCB3")
        for ph in (PinPhase.A, PinPhase.B, PinPhase.C):
            pins = spec.pins_by_phase(ph)
            assert len(pins) == 2, (
                f"VCB3 fase {ph.value} tem {len(pins)} pinos, esperado 2"
            )

    def test_timing_props_are_per_phase(
        self, registry: ComponentSpecRegistry
    ) -> None:
        from app.preprocessor.spec import PinPhase, PropertyGroup
        spec = registry.require("VCB3")
        timing = spec.properties_by_group(PropertyGroup.TIMING)
        assert len(timing) == 6, (
            f"esperava 6 props de timing (T_open/T_close × 3φ), vi {len(timing)}"
        )
        # Cada fase tem 2 props (T_open e T_close)
        for ph in (PinPhase.A, PinPhase.B, PinPhase.C):
            phase_props = [p for p in timing if p.phase == ph]
            assert len(phase_props) == 2

    def test_reignition_props_shared(
        self, registry: ComponentSpecRegistry
    ) -> None:
        """Parâmetros de reignição são 1 por câmara (não por fase)."""
        from app.preprocessor.spec import PropertyGroup
        spec = registry.require("VCB3")
        reign = spec.properties_by_group(PropertyGroup.REIGNITION)
        # Esperado: I_chop, sigma_I_chop, didt_crit, didt_sigma,
        #           k_dielec, U0_dielec, T_bounce, Seed = 8 props
        assert len(reign) == 8

    def test_branches_reference_existing_pins(
        self, registry: ComponentSpecRegistry
    ) -> None:
        spec = registry.require("VCB3")
        pin_names = {p.name for p in spec.pins}
        for branch in spec.atp_emission.branches:
            for pname in branch.pins:
                assert pname in pin_names


# ===========================================================================
# LLM integration — todos specs devem ter tool schema exportável
# ===========================================================================


class TestLLMIntegration:
    """Todos os .ocomp carregados devem ter schema exportável para Claude."""

    def test_tool_schema_callable(
        self, registry: ComponentSpecRegistry
    ) -> None:
        schema = ComponentSpec.llm_tool_schema()
        assert "properties" in schema
        assert "required" in schema

    @pytest.mark.parametrize(
        "code",
        ["R", "VCB3"],  # um simples e um complexo
    )
    def test_spec_llm_dict_roundtrip(
        self,
        code: str,
        registry: ComponentSpecRegistry,
    ) -> None:
        spec = registry.require(code)
        d = spec.to_llm_dict()
        spec2 = ComponentSpec.from_llm_dict(d)
        assert spec == spec2

    def test_specs_with_hints(
        self, registry: ComponentSpecRegistry
    ) -> None:
        """Todos os specs desta sprint têm llm_hints preenchidos."""
        for spec in registry.all_specs():
            h = spec.llm_hints
            # Pelo menos 1 categoria de hint preenchida
            total = (
                len(h.typical_applications)
                + len(h.references)
                + len(h.common_mistakes)
                + len(h.alternatives)
            )
            assert total > 0, (
                f"{spec.code}: llm_hints completamente vazios; "
                "preencher pelo menos typical_applications"
            )
