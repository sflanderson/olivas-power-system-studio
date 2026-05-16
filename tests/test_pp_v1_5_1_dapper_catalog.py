"""
tests/test_pp_v1_5_1_dapper_catalog.py — v1.5.1 Sprint A.

Cobre o módulo ``app.postprocessor.dapper_catalog`` (22 categorias
NEC 220.x + sectors industriais/comerciais BR).
"""

from __future__ import annotations

import pytest


class TestCatalogStructure:

    def test_module_loadable(self):
        from app.postprocessor import dapper_catalog  # noqa: F401

    def test_load_type_enum_loadable(self):
        from app.postprocessor.dapper_catalog import LoadType
        assert LoadType.CONSTANT_Z.value == "Z"
        assert LoadType.CONSTANT_KVA.value == "K"
        assert LoadType.CONSTANT_I.value == "I"

    def test_demand_level_dataclass(self):
        from app.postprocessor.dapper_catalog import DemandLevel
        lvl = DemandLevel(kVA_limit=3000.0, demand_pct=100.0)
        assert lvl.kVA_limit == 3000.0
        assert lvl.demand_pct == 100.0

    def test_demand_level_all_kva(self):
        from app.postprocessor.dapper_catalog import DemandLevel
        lvl = DemandLevel(kVA_limit=None, demand_pct=25.0)
        assert lvl.kVA_limit is None


class TestCatalogContents:

    def test_catalog_has_22_categories(self):
        from app.postprocessor.dapper_catalog import DAPPER_CATALOG
        assert len(DAPPER_CATALOG) >= 22

    def test_catalog_has_no_duplicate_codes(self):
        from app.postprocessor.dapper_catalog import DAPPER_CATALOG
        codes = [c.code for c in DAPPER_CATALOG]
        assert len(codes) == len(set(codes))

    def test_lookup_by_code(self):
        from app.postprocessor.dapper_catalog import (
            get_category, DAPPER_CATALOG,
        )
        cat = get_category("NEC_220_42_LIGHTING")
        assert cat is not None
        assert cat.nec_section == "220.42"

    def test_lookup_unknown_code_returns_none(self):
        from app.postprocessor.dapper_catalog import get_category
        assert get_category("UNKNOWN_X") is None

    def test_each_category_has_at_least_one_level(self):
        from app.postprocessor.dapper_catalog import DAPPER_CATALOG
        for c in DAPPER_CATALOG:
            assert len(c.levels) >= 1, (
                f"Categoria {c.code} sem levels"
            )

    def test_each_category_lcl_in_range(self):
        from app.postprocessor.dapper_catalog import DAPPER_CATALOG
        for c in DAPPER_CATALOG:
            assert 0.5 <= c.lcl_factor <= 2.5, (
                f"LCL fora do range razoável: {c.code}={c.lcl_factor}"
            )

    def test_each_category_pf_in_range(self):
        """Permite pf=0 (banco de capacitores = carga reativa pura)."""
        from app.postprocessor.dapper_catalog import DAPPER_CATALOG
        for c in DAPPER_CATALOG:
            assert 0.0 <= c.typical_pf <= 1.0, (
                f"PF fora do range: {c.code}={c.typical_pf}"
            )


class TestSpecificCategories:

    def test_nec_220_42_lighting_has_3_levels(self):
        """Lighting residencial: 100/35/25%."""
        from app.postprocessor.dapper_catalog import get_category
        cat = get_category("NEC_220_42_LIGHTING")
        assert cat is not None
        assert len(cat.levels) == 3
        # Level 1: 3000 VA @ 100%
        assert cat.levels[0].kVA_limit == pytest.approx(3000.0)
        assert cat.levels[0].demand_pct == pytest.approx(100.0)
        # Level 3: ALL @ 25%
        assert cat.levels[-1].kVA_limit is None
        assert cat.levels[-1].demand_pct == pytest.approx(25.0)

    def test_capacitor_bank_lcl_is_1_35(self):
        """Paridade PTW (Reference-DAPPER §1.4.10)."""
        from app.postprocessor.dapper_catalog import get_category
        cat = get_category("CAPACITOR_BANK")
        assert cat is not None
        assert cat.lcl_factor == pytest.approx(1.35)

    def test_data_center_lcl_is_1_40(self):
        """Vantagem competitiva — PUE típico 1.4."""
        from app.postprocessor.dapper_catalog import get_category
        cat = get_category("DATA_CENTER")
        assert cat is not None
        assert cat.lcl_factor == pytest.approx(1.40)

    def test_receptacles_general_matches_ptw(self):
        """10 kVA @ 100%, resto @ 50% (paridade PTW)."""
        from app.postprocessor.dapper_catalog import get_category
        cat = get_category("RECEPTACLES_GENERAL")
        assert cat is not None
        assert cat.levels[0].kVA_limit == pytest.approx(10000.0)
        assert cat.levels[0].demand_pct == pytest.approx(100.0)
        # Próximo level deve ser 50%
        assert cat.levels[1].demand_pct == pytest.approx(50.0)


class TestNECCoverage:

    def test_at_least_10_nec_categories(self):
        """Olivas vantagem: ≥10 categorias com NEC section explícita."""
        from app.postprocessor.dapper_catalog import DAPPER_CATALOG
        nec_cats = [
            c for c in DAPPER_CATALOG if c.nec_section
        ]
        assert len(nec_cats) >= 10

    def test_lookup_by_nec_section(self):
        from app.postprocessor.dapper_catalog import (
            get_categories_by_nec,
        )
        cats = get_categories_by_nec("220.42")
        assert len(cats) >= 1
        assert all(c.nec_section == "220.42" for c in cats)
