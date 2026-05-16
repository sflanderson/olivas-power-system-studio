"""
tests/test_pp_registry_guard.py — Guard contra drift legacy ↔ registry.

A partir de v0.21.8.b, ``catalog.py`` e ``node_coalescer.py`` consultam
o registry de ``.ocomp`` antes dos dicts legados. Como os dicts legados
ainda são usados para os 30 códigos sem ``.ocomp``, eles continuam
presentes no código.

Este teste garante que, para os 10 códigos *migrados*, os dados legados
continuam consistentes com os ``.ocomp``. Se alguém editar um dict
legado e esquecer de espelhar no ``.ocomp`` (ou vice-versa), o CI falha
imediatamente — evitando regressão sutil nos 30 códigos que ainda caem
no fallback.

Checks
------
1. Para cada ``code`` com ``.ocomp``:

   * ``catalog._ENTRIES`` (legado) tem a mesma ``label_pt``, ``category``,
     ``atp_supported`` que o spec.
   * ``node_coalescer._PIN_GEOMETRY`` (legado) tem as mesmas posições de
     pinos que ``spec.pins[*].position``.

2. Os accessors públicos (``catalog.get``, ``node_coalescer.pin_positions``)
   retornam o mesmo resultado para código com ``.ocomp`` quer entrando pelo
   caminho registry, quer pelo caminho legado (comparação direta).

Por que este teste existe
-------------------------
Durante a migração incremental, dois caminhos (registry-first e legacy-
fallback) convivem. Sem este guard, é trivial que:

* Alguém adicione um label novo ao ``catalog._PROPERTY_LABELS`` esquecendo
  de adicionar ao ``.ocomp`` — ``all_entries()`` retorna o spec (sem o
  label), mas ``property_labels()`` ainda usa o legacy dict. Inconsistente.
* Alguém mova uma pin position no ``.ocomp`` sem atualizar
  ``_PIN_GEOMETRY`` — ``pin_positions()`` passa a usar a nova posição,
  quebrando testes antigos de coalescência que checavam a posição legada.

Escopo
------
Só valida os 10 códigos com ``.ocomp`` (v0.21.8.b). Códigos legacy-only
(Tr, TLIN, etc.) serão cobertos conforme migrarem em v0.22.x.
"""

from __future__ import annotations

import pytest

from app.preprocessor import catalog
from app.preprocessor.node_coalescer import (
    _PIN_GEOMETRY,
    _pin_geometry_for,
)
from app.preprocessor.spec import get_default_registry


@pytest.fixture(scope="module")
def registry():
    """Registry default (cacheado pelo módulo)."""
    return get_default_registry()


@pytest.fixture(scope="module")
def ocomp_codes(registry):
    """Lista de códigos que têm .ocomp (45 após v0.26.5 — incluem
    5 specs TACS prebuilt: PID, Integrator, LowPass, Limiter, TSum)."""
    codes = registry.all_codes()
    assert len(codes) == 49, (
        f"Esperado 49 .ocomp em catalog_specs/, encontrados {len(codes)}"
    )
    return codes


# ---------------------------------------------------------------------------
# Paridade de metadata: _ENTRIES (legacy) ↔ ComponentSpec (registry)
# ---------------------------------------------------------------------------


class TestCatalogEntryParity:
    """Garante que ``_ENTRIES`` legado concorda com specs para os 10 migrados."""

    def test_legacy_entry_exists_for_each_ocomp(self, ocomp_codes):
        """Todo código com .ocomp também deve existir no _ENTRIES legado."""
        legacy_codes = {e.code for e in catalog._ENTRIES}
        for code in ocomp_codes:
            assert code in legacy_codes, (
                f".ocomp {code!r} sem correspondente em catalog._ENTRIES — "
                f"adicionar ao _ENTRIES ou remover o .ocomp"
            )

    @pytest.mark.parametrize("code", [
                'R', 'L', 'C', 'GND', 'Tr', 'sTr',
        'Tr3', 'MUT', 'TLIN', 'BERG', 'JMARTI', 'Vdc',
        'Vac', 'Idc', 'Iac', 'Vrect', 'Vsurge', 'SwIdeal',
        'Relais', 'SwTACS', 'VCB', 'VCB3', 'Diode', 'Thyr',
        'GTO', 'IGBT', 'MOSFET', 'ZnO', 'RNL', 'LNL',
        'VProbe', 'IProbe', 'TACS', 'MODEL', 'Eqn', '.TR',
        '.DC', '.AC', '.SW', '.SP',
    ])
    def test_label_pt_matches(self, code, registry):
        """label_pt do spec == label_pt do _ENTRIES legado."""
        legacy = catalog._BY_CODE[code]
        spec = registry.require(code)
        assert legacy.label_pt == spec.label_pt, (
            f"[{code}] label_pt divergente: legacy={legacy.label_pt!r} "
            f"vs spec={spec.label_pt!r}"
        )

    @pytest.mark.parametrize("code", [
                'R', 'L', 'C', 'GND', 'Tr', 'sTr',
        'Tr3', 'MUT', 'TLIN', 'BERG', 'JMARTI', 'Vdc',
        'Vac', 'Idc', 'Iac', 'Vrect', 'Vsurge', 'SwIdeal',
        'Relais', 'SwTACS', 'VCB', 'VCB3', 'Diode', 'Thyr',
        'GTO', 'IGBT', 'MOSFET', 'ZnO', 'RNL', 'LNL',
        'VProbe', 'IProbe', 'TACS', 'MODEL', 'Eqn', '.TR',
        '.DC', '.AC', '.SW', '.SP',
    ])
    def test_category_matches(self, code, registry):
        """category do spec == category do _ENTRIES legado."""
        legacy = catalog._BY_CODE[code]
        spec = registry.require(code)
        assert legacy.category == spec.category, (
            f"[{code}] category divergente: legacy={legacy.category!r} "
            f"vs spec={spec.category!r}"
        )

    @pytest.mark.parametrize("code", [
                'R', 'L', 'C', 'GND', 'Tr', 'sTr',
        'Tr3', 'MUT', 'TLIN', 'BERG', 'JMARTI', 'Vdc',
        'Vac', 'Idc', 'Iac', 'Vrect', 'Vsurge', 'SwIdeal',
        'Relais', 'SwTACS', 'VCB', 'VCB3', 'Diode', 'Thyr',
        'GTO', 'IGBT', 'MOSFET', 'ZnO', 'RNL', 'LNL',
        'VProbe', 'IProbe', 'TACS', 'MODEL', 'Eqn', '.TR',
        '.DC', '.AC', '.SW', '.SP',
    ])
    def test_atp_supported_matches(self, code, registry):
        """atp_supported do spec == atp_supported do _ENTRIES legado."""
        legacy = catalog._BY_CODE[code]
        spec = registry.require(code)
        assert legacy.atp_supported == spec.atp_supported, (
            f"[{code}] atp_supported divergente: legacy={legacy.atp_supported} "
            f"vs spec={spec.atp_supported}"
        )


# ---------------------------------------------------------------------------
# Paridade de pin geometry: _PIN_GEOMETRY (legacy) ↔ spec.pins (registry)
# ---------------------------------------------------------------------------


class TestPinGeometryParity:
    """Garante que ``_PIN_GEOMETRY`` legado concorda com ``spec.pins``."""

    @pytest.mark.parametrize("code", [
                'R', 'L', 'C', 'GND', 'Tr', 'sTr',
        'Tr3', 'MUT', 'TLIN', 'BERG', 'JMARTI', 'Vdc',
        'Vac', 'Idc', 'Iac', 'Vrect', 'Vsurge', 'SwIdeal',
        'Relais', 'SwTACS', 'VCB', 'VCB3', 'Diode', 'Thyr',
        'GTO', 'IGBT', 'MOSFET', 'ZnO', 'RNL', 'LNL',
        'VProbe', 'IProbe', 'TACS', 'MODEL', 'Eqn', '.TR',
        '.DC', '.AC', '.SW', '.SP',
    ])
    def test_pin_positions_match(self, code, registry):
        """spec.pins[*].position == _PIN_GEOMETRY[code]."""
        legacy = _PIN_GEOMETRY.get(code)
        spec = registry.require(code)
        spec_positions = [p.position for p in spec.pins]
        assert legacy == spec_positions, (
            f"[{code}] geometria divergente:\n"
            f"  legacy    = {legacy}\n"
            f"  spec.pins = {spec_positions}"
        )

    @pytest.mark.parametrize("code", [
                'R', 'L', 'C', 'GND', 'Tr', 'sTr',
        'Tr3', 'MUT', 'TLIN', 'BERG', 'JMARTI', 'Vdc',
        'Vac', 'Idc', 'Iac', 'Vrect', 'Vsurge', 'SwIdeal',
        'Relais', 'SwTACS', 'VCB', 'VCB3', 'Diode', 'Thyr',
        'GTO', 'IGBT', 'MOSFET', 'ZnO', 'RNL', 'LNL',
        'VProbe', 'IProbe', 'TACS', 'MODEL', 'Eqn', '.TR',
        '.DC', '.AC', '.SW', '.SP',
    ])
    def test_pin_geometry_for_resolves_via_registry(self, code):
        """_pin_geometry_for() resolve via registry para códigos com .ocomp."""
        from app.preprocessor.spec import get_default_registry
        spec = get_default_registry().require(code)
        expected = [p.position for p in spec.pins]
        actual = _pin_geometry_for(code)
        assert actual == expected, (
            f"[{code}] _pin_geometry_for retornou {actual!r}, "
            f"esperado do spec: {expected!r}"
        )


# ---------------------------------------------------------------------------
# Accessors públicos continuam funcionando
# ---------------------------------------------------------------------------


class TestPublicAccessorsParity:
    """Sanity check: accessors públicos retornam os mesmos dados para os 10."""

    @pytest.mark.parametrize("code", [
                'R', 'L', 'C', 'GND', 'Tr', 'sTr',
        'Tr3', 'MUT', 'TLIN', 'BERG', 'JMARTI', 'Vdc',
        'Vac', 'Idc', 'Iac', 'Vrect', 'Vsurge', 'SwIdeal',
        'Relais', 'SwTACS', 'VCB', 'VCB3', 'Diode', 'Thyr',
        'GTO', 'IGBT', 'MOSFET', 'ZnO', 'RNL', 'LNL',
        'VProbe', 'IProbe', 'TACS', 'MODEL', 'Eqn', '.TR',
        '.DC', '.AC', '.SW', '.SP',
    ])
    def test_catalog_get_returns_consistent_entry(self, code, registry):
        """``catalog.get(code)`` deve refletir o spec, não o dict legado."""
        entry = catalog.get(code)
        spec = registry.require(code)
        assert entry is not None
        assert entry.code == spec.code
        assert entry.label_pt == spec.label_pt
        assert entry.category == spec.category
        assert entry.atp_supported == spec.atp_supported

    def test_catalog_all_entries_count(self, registry):
        """``all_entries()`` deve conter os 10 ocomp'd + 30 legacy = 40."""
        entries = catalog.all_entries()
        codes = {e.code for e in entries}
        # Todos os 10 com .ocomp presentes
        for code in registry.all_codes():
            assert code in codes, (
                f"Código com .ocomp {code!r} ausente de all_entries()"
            )

    def test_catalog_by_category_includes_ocomp(self, registry):
        """Componentes com .ocomp aparecem em by_category() da sua categoria."""
        for spec in registry.all_specs():
            entries = catalog.by_category(spec.category)
            codes = {e.code for e in entries}
            assert spec.code in codes, (
                f"[{spec.code}] ausente de by_category({spec.category!r})"
            )

    def test_is_atp_supported_consistent(self, registry):
        """``is_atp_supported(code)`` deve refletir o spec."""
        for spec in registry.all_specs():
            assert catalog.is_atp_supported(spec.code) == spec.atp_supported, (
                f"[{spec.code}] is_atp_supported divergente do spec"
            )


# ---------------------------------------------------------------------------
# Regression guard: legacy-only codes continuam intactos
# ---------------------------------------------------------------------------


class TestLegacyOnlyCodesPreserved:
    """Confirma que códigos sem .ocomp ainda vêm do dict legado."""

    # v0.22.0 migrou TODOS os 30 legacy-only para .ocomp.
    # Esta lista agora é VAZIA — a tabela legada _BY_CODE continua
    # como fallback, mas todo código suportado tem .ocomp como fonte
    # primária de verdade.
    LEGACY_ONLY_CODES: list[str] = []

    def test_all_legacy_codes_now_have_ocomp(self, registry):
        """v0.22.0: todos os 40 códigos do catálogo têm .ocomp."""
        legacy_codes = {e.code for e in catalog._ENTRIES}
        for code in legacy_codes:
            assert registry.contains(code), (
                f"[{code}] sumiu do registry — arquivo .ocomp removido?"
            )

    def test_total_catalog_count_preserved(self):
        """Total de entradas deve ser 49 (todos com .ocomp; v0.27.7.9
        adicionou MOTOR — IM/MS contribuição SC)."""
        assert len(catalog._ENTRIES) == 49, (
            f"catalog._ENTRIES tem {len(catalog._ENTRIES)} entradas, "
            f"esperado 49"
        )
        assert len(catalog.all_entries()) == 49, (
            f"catalog.all_entries() retorna {len(catalog.all_entries())}, "
            f"esperado 49"
        )
