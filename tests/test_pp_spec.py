"""
Tests for ``app.preprocessor.spec`` — schema declarativo ``.ocomp``.

Cobre:

1. **Modelos pydantic**: validação de campos, unicidade de nomes,
   consistência de referências cruzadas (pins ↔ branches, props ↔
   property_mapping), regras por type (ENUM/choices, min/max),
   consistência svg ↔ icon_svg.
2. **Validação de alto nível**: ``ComponentSpec`` completo aceita
   um spec válido e rejeita combinações inconsistentes com mensagens
   descritivas.
3. **Helpers LLM**: ``llm_tool_schema()`` produz JSON Schema válido,
   ``to_llm_dict`` / ``from_llm_dict`` fazem round-trip lossless.
4. **Loader YAML**: ``load_ocomp_string``, ``dump_ocomp_string`` e
   I/O em disco fazem round-trip preservando ordem e valores.
5. **Registry**: registro, colisão, consulta, filtragem por categoria,
   carregamento de diretório.

Convenções
----------

* Um **spec mínimo válido** é construído via :func:`_minimal_spec` —
  usado como base para testes de mutação.
* Testes de validação negativa usam ``pytest.raises(ValidationError)``
  para confirmar que o pydantic levanta, e ``match=`` para verificar
  que a mensagem menciona o campo relevante.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from app.preprocessor.spec import (
    AtpEmissionKind,
    AtpEmissionSpec,
    BranchMapping,
    ComponentSpec,
    ComponentSpecRegistry,
    LLMHintsSpec,
    PinPhase,
    PinRole,
    PinSpec,
    PropertyGroup,
    PropertySpec,
    PropertyType,
    SymbolSpec,
    dump_ocomp_file,
    dump_ocomp_string,
    load_ocomp_file,
    load_ocomp_string,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _minimal_spec(**overrides) -> ComponentSpec:
    """Cria um ComponentSpec mínimo válido, com overrides opcionais."""
    defaults: dict = dict(
        code="R",
        label_pt="Resistor",
        category="passive",
        symbol=SymbolSpec(
            size=(40, 60),
            bounding_box=(-20, -30, 40, 60),
            renderer="ResistorSymbol",
        ),
        pins=[
            PinSpec(name="p1", label="Terminal 1", position=(0, -30)),
            PinSpec(name="p2", label="Terminal 2", position=(0, 30)),
        ],
        properties=[
            PropertySpec(
                name="R",
                label="Resistencia",
                unit="ohm",
                default=1000.0,
            ),
        ],
        atp_emission=AtpEmissionSpec(kind=AtpEmissionKind.RESISTOR),
    )
    defaults.update(overrides)
    return ComponentSpec(**defaults)


# ===========================================================================
# 1. PinSpec
# ===========================================================================


class TestPinSpec:
    def test_minimal(self) -> None:
        p = PinSpec(name="a", label="Ânodo", position=(0, -30))
        assert p.name == "a"
        assert p.phase == PinPhase.NONE
        assert p.role == PinRole.TERMINAL

    def test_name_stripped(self) -> None:
        p = PinSpec(name="  foo  ", label="x", position=(0, 0))
        assert p.name == "foo"

    def test_name_empty_rejected(self) -> None:
        with pytest.raises(ValidationError):
            PinSpec(name="   ", label="x", position=(0, 0))

    def test_phase_enum(self) -> None:
        p = PinSpec(
            name="a", label="Ânodo A",
            position=(-40, -30), phase=PinPhase.A,
        )
        assert p.phase == PinPhase.A

    def test_role_enum(self) -> None:
        p = PinSpec(
            name="ctrl", label="Controle",
            position=(0, 0), role=PinRole.CONTROL,
        )
        assert p.role == PinRole.CONTROL

    def test_extra_field_rejected(self) -> None:
        with pytest.raises(ValidationError):
            PinSpec(
                name="a", label="x", position=(0, 0),
                unknown_field="oops",
            )


# ===========================================================================
# 2. PropertySpec
# ===========================================================================


class TestPropertySpec:
    def test_minimal_float(self) -> None:
        p = PropertySpec(name="R", label="Resistencia")
        assert p.type == PropertyType.FLOAT
        assert p.visible is True
        assert p.group == PropertyGroup.MAIN

    def test_enum_requires_choices(self) -> None:
        with pytest.raises(ValidationError, match="choices"):
            PropertySpec(name="mode", label="Mode", type=PropertyType.ENUM)

    def test_choices_without_enum_rejected(self) -> None:
        with pytest.raises(ValidationError, match="choices"):
            PropertySpec(
                name="R", label="R",
                type=PropertyType.FLOAT, choices=[1, 2, 3],
            )

    def test_enum_with_choices_ok(self) -> None:
        p = PropertySpec(
            name="mode", label="Mode",
            type=PropertyType.ENUM, choices=["auto", "manual"],
        )
        assert p.choices == ["auto", "manual"]

    def test_min_max_order(self) -> None:
        with pytest.raises(ValidationError, match="min .* > max"):
            PropertySpec(name="R", label="R", min=10.0, max=5.0)

    def test_min_max_equal_ok(self) -> None:
        p = PropertySpec(name="R", label="R", min=5.0, max=5.0)
        assert p.min == 5.0 and p.max == 5.0

    def test_phase_property(self) -> None:
        p = PropertySpec(
            name="T_open_A", label="T_open A",
            phase=PinPhase.A, unit="s", default=50e-3,
        )
        assert p.phase == PinPhase.A


# ===========================================================================
# 3. SymbolSpec
# ===========================================================================


class TestSymbolSpec:
    def test_minimal_python_renderer(self) -> None:
        s = SymbolSpec(
            size=(40, 60), bounding_box=(-20, -30, 40, 60),
            renderer="ResistorSymbol",
        )
        assert s.icon_svg is None

    def test_svg_requires_icon_svg(self) -> None:
        with pytest.raises(ValidationError, match="icon_svg"):
            SymbolSpec(
                size=(40, 60), bounding_box=(-20, -30, 40, 60),
                renderer="svg",
            )

    def test_non_svg_rejects_icon_svg(self) -> None:
        with pytest.raises(ValidationError, match="icon_svg"):
            SymbolSpec(
                size=(40, 60), bounding_box=(-20, -30, 40, 60),
                renderer="ResistorSymbol",
                icon_svg="<svg></svg>",
            )

    def test_svg_with_icon_ok(self) -> None:
        s = SymbolSpec(
            size=(40, 40), bounding_box=(-20, -20, 40, 40),
            renderer="svg", icon_svg="<svg><rect/></svg>",
        )
        assert s.renderer == "svg"
        assert s.icon_svg is not None


# ===========================================================================
# 4. AtpEmissionSpec e BranchMapping
# ===========================================================================


class TestAtpEmissionSpec:
    def test_resistor_default_count(self) -> None:
        e = AtpEmissionSpec(kind=AtpEmissionKind.RESISTOR)
        assert e.count == 1
        assert e.branches == []

    def test_model_use_requires_ref(self) -> None:
        with pytest.raises(ValidationError, match="model_ref"):
            AtpEmissionSpec(kind=AtpEmissionKind.MODEL_USE)

    def test_custom_requires_emitter(self) -> None:
        with pytest.raises(ValidationError, match="custom_emitter"):
            AtpEmissionSpec(kind=AtpEmissionKind.CUSTOM)

    def test_branches_count_mismatch(self) -> None:
        with pytest.raises(ValidationError, match="count"):
            AtpEmissionSpec(
                kind=AtpEmissionKind.MULTI_SWITCH,
                count=3,
                branches=[
                    BranchMapping(phase=PinPhase.A, pins=["a1", "a2"]),
                    BranchMapping(phase=PinPhase.B, pins=["b1", "b2"]),
                ],
            )

    def test_branches_count_match(self) -> None:
        e = AtpEmissionSpec(
            kind=AtpEmissionKind.MULTI_SWITCH,
            count=2,
            branches=[
                BranchMapping(phase=PinPhase.A, pins=["a1", "a2"]),
                BranchMapping(phase=PinPhase.B, pins=["b1", "b2"]),
            ],
        )
        assert e.count == 2 and len(e.branches) == 2

    def test_count_at_least_0(self) -> None:
        """v0.22.0: count=0 válido (componentes metadata-only — diretivas
        Qucs .TR/.DC/.AC/.SW/.SP, bloco Eqn). Negativo continua rejeitado."""
        # count=0 aceito
        e = AtpEmissionSpec(kind=AtpEmissionKind.CUSTOM, count=0)
        assert e.count == 0
        # count=-1 rejeitado
        with pytest.raises(ValidationError):
            AtpEmissionSpec(kind=AtpEmissionKind.RESISTOR, count=-1)


# ===========================================================================
# 5. ComponentSpec — validação cruzada
# ===========================================================================


class TestComponentSpecValidation:
    def test_minimal_ok(self) -> None:
        spec = _minimal_spec()
        assert spec.code == "R"
        assert len(spec.pins) == 2

    def test_code_invalid_chars(self) -> None:
        with pytest.raises(ValidationError, match="code inv"):
            _minimal_spec(code="R!BANG")

    def test_code_empty(self) -> None:
        with pytest.raises(ValidationError):
            _minimal_spec(code="")

    def test_code_too_long(self) -> None:
        with pytest.raises(ValidationError):
            _minimal_spec(code="A" * 33)

    def test_pin_names_unique(self) -> None:
        with pytest.raises(ValidationError, match="pinos duplicados"):
            _minimal_spec(
                pins=[
                    PinSpec(name="p", label="T1", position=(0, -30)),
                    PinSpec(name="p", label="T2", position=(0, 30)),
                ]
            )

    def test_property_names_unique(self) -> None:
        with pytest.raises(ValidationError, match="propriedades duplicad"):
            _minimal_spec(
                properties=[
                    PropertySpec(name="R", label="R1"),
                    PropertySpec(name="R", label="R2"),
                ]
            )

    def test_no_pins_accepted(self) -> None:
        """v0.22.0: pins=[] válido para componentes sem pinos elétricos
        (TACS/MODEL, diretivas de simulação .TR/.DC/.AC/.SW/.SP, Eqn).
        O schema anteriormente exigia min_length=1; foi relaxado para
        suportar esses tipos de componente."""
        spec = _minimal_spec(
            pins=[],
            atp_emission=AtpEmissionSpec(kind=AtpEmissionKind.CUSTOM, count=0),
        )
        assert spec.pins == []

    def test_emission_pins_must_exist(self) -> None:
        with pytest.raises(ValidationError, match="pino inexistente"):
            _minimal_spec(
                atp_emission=AtpEmissionSpec(
                    kind=AtpEmissionKind.RESISTOR,
                    count=1,
                    branches=[
                        BranchMapping(pins=["p1", "nonexistent"]),
                    ],
                )
            )

    def test_emission_props_must_exist(self) -> None:
        with pytest.raises(ValidationError, match="propriedade inexistente"):
            _minimal_spec(
                atp_emission=AtpEmissionSpec(
                    kind=AtpEmissionKind.RESISTOR,
                    count=1,
                    branches=[
                        BranchMapping(
                            pins=["p1", "p2"],
                            property_mapping={"r": "DoesNotExist"},
                        ),
                    ],
                )
            )

    def test_full_vcb3_shape(self) -> None:
        """Sanity check com a forma canônica do VCB3 (14 props, 6 pinos, 3 branches)."""
        spec = _minimal_spec(
            code="VCB3",
            label_pt="Disjuntor a vácuo 3φ",
            category="switch",
            symbol=SymbolSpec(
                size=(80, 80),
                bounding_box=(-40, -40, 80, 80),
                renderer="VCB3PhaseSymbol",
            ),
            pins=[
                PinSpec(name=f"{ph}_{side}", label=f"{ph} {side}",
                        position=(-40 if side == "in" else 40,
                                  {"A": -30, "B": 0, "C": 30}[ph]),
                        phase=PinPhase[ph])
                for ph in ("A", "B", "C")
                for side in ("in", "out")
            ],
            properties=[
                PropertySpec(
                    name=f"T_open_{ph}", label=f"T_open {ph}", unit="s",
                    phase=PinPhase[ph], group=PropertyGroup.TIMING, default=50e-3,
                )
                for ph in ("A", "B", "C")
            ] + [
                PropertySpec(
                    name=f"T_close_{ph}", label=f"T_close {ph}", unit="s",
                    phase=PinPhase[ph], group=PropertyGroup.TIMING, default=100.0,
                )
                for ph in ("A", "B", "C")
            ] + [
                PropertySpec(name="I_chop", label="I_chop", unit="A",
                             group=PropertyGroup.REIGNITION, default=5.0),
                PropertySpec(name="Seed", label="Seed", type=PropertyType.INT,
                             group=PropertyGroup.REIGNITION, default=42),
            ],
            atp_emission=AtpEmissionSpec(
                kind=AtpEmissionKind.MULTI_SWITCH,
                count=3,
                branches=[
                    BranchMapping(
                        phase=PinPhase[ph],
                        pins=[f"{ph}_in", f"{ph}_out"],
                        property_mapping={
                            "t_open": f"T_open_{ph}",
                            "t_close": f"T_close_{ph}",
                        },
                    )
                    for ph in ("A", "B", "C")
                ],
            ),
        )
        assert spec.code == "VCB3"
        assert len(spec.pins) == 6
        assert len(spec.properties) == 8
        assert spec.atp_emission.count == 3
        assert len(spec.atp_emission.branches) == 3


# ===========================================================================
# 6. ComponentSpec — helpers de consulta
# ===========================================================================


class TestComponentSpecHelpers:
    def test_pin_by_name(self) -> None:
        spec = _minimal_spec()
        assert spec.pin_by_name("p1") is not None
        assert spec.pin_by_name("p1").label == "Terminal 1"
        assert spec.pin_by_name("nonexistent") is None

    def test_property_by_name(self) -> None:
        spec = _minimal_spec()
        assert spec.property_by_name("R") is not None
        assert spec.property_by_name("nonexistent") is None

    def test_pins_by_phase(self) -> None:
        spec = _minimal_spec(
            pins=[
                PinSpec(name="a", label="A", position=(-40, 0), phase=PinPhase.A),
                PinSpec(name="b", label="B", position=(0, 0), phase=PinPhase.B),
                PinSpec(name="c", label="C", position=(40, 0), phase=PinPhase.C),
            ]
        )
        assert len(spec.pins_by_phase(PinPhase.A)) == 1
        assert spec.pins_by_phase(PinPhase.A)[0].name == "a"
        assert spec.pins_by_phase(PinPhase.N) == []

    def test_properties_by_group(self) -> None:
        spec = _minimal_spec(
            properties=[
                PropertySpec(name="R", label="R", group=PropertyGroup.MAIN),
                PropertySpec(name="T_amb", label="T_amb",
                             group=PropertyGroup.THERMAL),
            ]
        )
        assert len(spec.properties_by_group(PropertyGroup.MAIN)) == 1
        assert len(spec.properties_by_group(PropertyGroup.THERMAL)) == 1
        assert len(spec.properties_by_group(PropertyGroup.REIGNITION)) == 0


# ===========================================================================
# 7. LLM integration helpers
# ===========================================================================


class TestLLMIntegration:
    def test_llm_tool_schema_is_valid_json_schema(self) -> None:
        schema = ComponentSpec.llm_tool_schema()
        # JSON Schema deve ter essas chaves top-level
        assert "type" in schema
        assert "properties" in schema
        assert "required" in schema
        # Required top-level obrigatórios.
        # v0.22.0: 'pins' deixou de ser required (default_factory=list) para
        # permitir componentes sem pinos elétricos (TACS/MODEL, sim
        # directives). Continua aparecendo em 'properties'.
        required = set(schema["required"])
        assert {
            "code", "label_pt", "category", "symbol", "atp_emission",
        }.issubset(required)
        assert "pins" in schema["properties"]

    def test_llm_tool_schema_has_defs_for_nested(self) -> None:
        schema = ComponentSpec.llm_tool_schema()
        defs = schema.get("$defs", {})
        # Deve ter defs para os sub-modelos
        assert "PinSpec" in defs
        assert "PropertySpec" in defs
        assert "SymbolSpec" in defs
        assert "AtpEmissionSpec" in defs
        assert "BranchMapping" in defs
        assert "LLMHintsSpec" in defs

    def test_llm_tool_schema_enums_are_string_enums(self) -> None:
        schema = ComponentSpec.llm_tool_schema()
        defs = schema.get("$defs", {})
        # Enums são serializados como strings (por str Enum)
        pin_phase = defs.get("PinPhase", {})
        assert pin_phase.get("type") == "string"
        assert "A" in pin_phase.get("enum", [])

    def test_to_from_llm_dict_roundtrip(self) -> None:
        spec = _minimal_spec()
        d = spec.to_llm_dict()
        assert isinstance(d, dict)
        spec2 = ComponentSpec.from_llm_dict(d)
        assert spec == spec2

    def test_to_llm_dict_excludes_none(self) -> None:
        spec = _minimal_spec()
        d = spec.to_llm_dict()
        # description é None no spec mínimo → não deve aparecer
        assert "description" not in d or d.get("description") is not None

    def test_from_llm_dict_validates(self) -> None:
        with pytest.raises(ValidationError):
            ComponentSpec.from_llm_dict({"code": "R"})  # faltam campos


# ===========================================================================
# 8. Loader — YAML I/O
# ===========================================================================


class TestLoader:
    def test_dump_load_string_roundtrip(self) -> None:
        spec = _minimal_spec()
        yaml_str = dump_ocomp_string(spec)
        assert "code: R" in yaml_str or "code: 'R'" in yaml_str
        spec2 = load_ocomp_string(yaml_str)
        assert spec == spec2

    def test_load_string_not_dict_raises(self) -> None:
        with pytest.raises(ValueError, match="dict raiz"):
            load_ocomp_string("- foo\n- bar\n")

    def test_load_string_invalid_yaml(self) -> None:
        import yaml as _yaml
        with pytest.raises(_yaml.YAMLError):
            load_ocomp_string("key: value\n  bad indent:\n wrong")

    def test_load_string_missing_required_field(self) -> None:
        with pytest.raises(ValidationError):
            load_ocomp_string("code: R\n")

    def test_dump_preserves_order(self) -> None:
        """code/label_pt/category devem vir antes de pins/properties."""
        spec = _minimal_spec()
        yaml_str = dump_ocomp_string(spec)
        # code aparece antes de pins no output
        assert yaml_str.index("code:") < yaml_str.index("pins:")
        assert yaml_str.index("label_pt:") < yaml_str.index("properties:")

    def test_dump_allows_unicode(self) -> None:
        spec = _minimal_spec(label_pt="Disjuntor a vácuo 3φ")
        yaml_str = dump_ocomp_string(spec)
        # Não escapado — Unicode preservado
        assert "vácuo" in yaml_str
        assert "3φ" in yaml_str

    def test_load_file_not_found(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            load_ocomp_file(tmp_path / "nonexistent.ocomp")

    def test_dump_load_file_roundtrip(self, tmp_path: Path) -> None:
        spec = _minimal_spec()
        path = tmp_path / "R.ocomp"
        dump_ocomp_file(spec, path)
        assert path.is_file()
        spec2 = load_ocomp_file(path)
        assert spec == spec2

    def test_dump_file_creates_parent(self, tmp_path: Path) -> None:
        spec = _minimal_spec()
        path = tmp_path / "nested" / "sub" / "R.ocomp"
        dump_ocomp_file(spec, path)
        assert path.is_file()

    def test_load_file_error_context(self, tmp_path: Path) -> None:
        """Exceção do pydantic deve incluir o path do arquivo via __notes__ (PEP 678)."""
        path = tmp_path / "bad.ocomp"
        path.write_text("code: X\n", encoding="utf-8")
        with pytest.raises(ValidationError) as excinfo:
            load_ocomp_file(path)
        notes = getattr(excinfo.value, "__notes__", [])
        assert any("bad.ocomp" in note for note in notes), (
            f"esperava path do arquivo nas __notes__, mas recebi: {notes}"
        )


# ===========================================================================
# 9. Registry
# ===========================================================================


class TestRegistry:
    def test_empty(self) -> None:
        reg = ComponentSpecRegistry()
        assert len(reg) == 0
        assert reg.all_codes() == ()
        assert reg.get("R") is None

    def test_register_and_get(self) -> None:
        reg = ComponentSpecRegistry()
        spec = _minimal_spec()
        reg.register(spec)
        assert reg.get("R") is spec
        assert "R" in reg
        assert len(reg) == 1

    def test_register_duplicate_raises(self) -> None:
        reg = ComponentSpecRegistry()
        reg.register(_minimal_spec(code="R"))
        with pytest.raises(ValueError, match="colis"):
            reg.register(_minimal_spec(code="R", label_pt="Outro"))

    def test_register_same_instance_idempotent(self) -> None:
        reg = ComponentSpecRegistry()
        spec = _minimal_spec()
        reg.register(spec)
        reg.register(spec)  # mesma instância → ok
        assert len(reg) == 1

    def test_require_raises_on_missing(self) -> None:
        reg = ComponentSpecRegistry()
        with pytest.raises(KeyError, match="X"):
            reg.require("X")

    def test_require_returns_spec(self) -> None:
        reg = ComponentSpecRegistry()
        spec = _minimal_spec()
        reg.register(spec)
        assert reg.require("R") is spec

    def test_clear(self) -> None:
        reg = ComponentSpecRegistry()
        reg.register(_minimal_spec())
        reg.clear()
        assert len(reg) == 0

    def test_all_codes_sorted(self) -> None:
        reg = ComponentSpecRegistry()
        reg.register(_minimal_spec(code="Z"))
        reg.register(_minimal_spec(code="A"))
        reg.register(_minimal_spec(code="M"))
        assert reg.all_codes() == ("A", "M", "Z")

    def test_by_category(self) -> None:
        reg = ComponentSpecRegistry()
        reg.register(_minimal_spec(code="R", category="passive"))
        reg.register(_minimal_spec(code="L", category="passive"))
        reg.register(_minimal_spec(code="Vac", category="source"))
        passives = reg.by_category("passive")
        assert len(passives) == 2
        assert {s.code for s in passives} == {"R", "L"}

    def test_iter_yields_specs(self) -> None:
        reg = ComponentSpecRegistry()
        reg.register(_minimal_spec())
        specs = list(reg)
        assert len(specs) == 1
        assert specs[0].code == "R"

    def test_contains_rejects_non_string(self) -> None:
        reg = ComponentSpecRegistry()
        reg.register(_minimal_spec())
        assert ("R" in reg) is True
        assert (123 in reg) is False  # type: ignore[operator]

    def test_load_directory_not_exists(self, tmp_path: Path) -> None:
        reg = ComponentSpecRegistry()
        with pytest.raises(FileNotFoundError):
            reg.load_directory(tmp_path / "nonexistent")

    def test_load_directory_empty(self, tmp_path: Path) -> None:
        reg = ComponentSpecRegistry()
        assert reg.load_directory(tmp_path) == 0

    def test_load_directory_with_specs(self, tmp_path: Path) -> None:
        dump_ocomp_file(_minimal_spec(code="R"), tmp_path / "R.ocomp")
        dump_ocomp_file(_minimal_spec(code="L"), tmp_path / "L.ocomp")
        reg = ComponentSpecRegistry()
        n = reg.load_directory(tmp_path)
        assert n == 2
        assert reg.get("R") is not None
        assert reg.get("L") is not None

    def test_load_directory_raise_on_error(self, tmp_path: Path) -> None:
        (tmp_path / "bad.ocomp").write_text("code: X\n", encoding="utf-8")
        reg = ComponentSpecRegistry()
        with pytest.raises(ValidationError):
            reg.load_directory(tmp_path)

    def test_load_directory_skip_on_error(self, tmp_path: Path) -> None:
        (tmp_path / "bad.ocomp").write_text("code: X\n", encoding="utf-8")
        dump_ocomp_file(_minimal_spec(code="R"), tmp_path / "R.ocomp")
        reg = ComponentSpecRegistry()
        n = reg.load_directory(tmp_path, raise_on_error=False)
        # Apenas o R.ocomp carregou
        assert n == 1
        assert reg.get("R") is not None


# ===========================================================================
# 10. Equivalência semântica de enums (para JSON Schema / Claude)
# ===========================================================================


class TestEnumSerialization:
    def test_pin_phase_values_are_strings(self) -> None:
        assert PinPhase.A.value == "A"
        assert PinPhase.NONE.value == "none"

    def test_property_type_values_are_strings(self) -> None:
        assert PropertyType.FLOAT.value == "float"
        assert PropertyType.ENUM.value == "enum"

    def test_atp_emission_kind_values_are_strings(self) -> None:
        assert AtpEmissionKind.RESISTOR.value == "resistor"
        assert AtpEmissionKind.MULTI_SWITCH.value == "multi_switch"

    def test_enum_roundtrip_via_yaml(self) -> None:
        spec = _minimal_spec(
            pins=[
                PinSpec(name="a", label="A", position=(0, 0), phase=PinPhase.A),
                PinSpec(name="b", label="B", position=(0, 10)),
            ]
        )
        yaml_str = dump_ocomp_string(spec)
        assert "phase: A" in yaml_str
        spec2 = load_ocomp_string(yaml_str)
        assert spec2.pins[0].phase == PinPhase.A
