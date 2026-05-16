"""
tests/test_pp_v1_5_1_demand_calculator.py — v1.5.1 Sprint B+C.

Cobre o módulo ``app.postprocessor.studies.demand_load``:

* Algorithm Connected → Demand → Design
* Multi-level demand factor application
* Diversity factors entre categorias (NEC 220.61)
* DemandReport / CategoryResult dataclasses
"""

from __future__ import annotations

import pytest


class TestApplyDemandLevels:

    def test_single_level_100_pct(self):
        """ALL @ 100% retorna o connected inteiro."""
        from app.postprocessor.dapper_catalog import DemandLevel
        from app.postprocessor.studies.demand_load import (
            apply_demand_levels,
        )
        levels = (DemandLevel(kVA_limit=None, demand_pct=100.0),)
        assert apply_demand_levels(50000.0, levels) == pytest.approx(50000.0)

    def test_single_level_50_pct(self):
        from app.postprocessor.dapper_catalog import DemandLevel
        from app.postprocessor.studies.demand_load import (
            apply_demand_levels,
        )
        levels = (DemandLevel(kVA_limit=None, demand_pct=50.0),)
        assert apply_demand_levels(40000.0, levels) == pytest.approx(20000.0)

    def test_three_levels_lighting_220_42(self):
        """
        NEC 220.42: 100/35/25%
        Connected = 200_000 VA
          L1: min(200000, 3000) × 100% = 3000
          L2: min(197000, 117000) × 35% = 40_950
          L3: 80_000 × 25% = 20_000
          total = 63_950 VA
        """
        from app.postprocessor.dapper_catalog import DemandLevel
        from app.postprocessor.studies.demand_load import (
            apply_demand_levels,
        )
        levels = (
            DemandLevel(kVA_limit=3000.0, demand_pct=100.0),
            DemandLevel(kVA_limit=120000.0, demand_pct=35.0),
            DemandLevel(kVA_limit=None, demand_pct=25.0),
        )
        # Note: 3000 (level 1) + (120000-3000)=117000 max em L2 + ALL em L3
        # Connected 200_000:
        #   chunk_1 = min(200000, 3000) = 3000  → 3000
        #   remaining = 197_000
        #   chunk_2 = min(197000, 120000) = 120_000  →  120000 * 0.35 = 42_000
        # ATENÇÃO: NEC 220.42 usa kVA_limit como ABSOLUTOS no acumulado
        # (3000 e 120000 são THRESHOLDS, não chunks)
        # Mas implementação do design doc usa CHUNKS:
        #   3000 @ 100% = 3000
        #   (120000-3000=117000 OR ALL until that absolute) @ 35%
        # Aqui consideramos a interpretação simples: o limite é o
        # tamanho do chunk daquele nível, não threshold.
        # Para v1.5.1 ficamos com chunks (consistente com design doc).
        result = apply_demand_levels(200000.0, levels)
        # L1: 3000 @ 100% = 3000
        # L2: 120000 @ 35% = 42_000
        # L3: (200000 - 3000 - 120000)=77000 @ 25% = 19_250
        # total = 64_250
        assert result == pytest.approx(64250.0, rel=1e-3)

    def test_connected_below_first_level(self):
        """Connected 1000 VA, primeiro level é 3000 — só usa 1000."""
        from app.postprocessor.dapper_catalog import DemandLevel
        from app.postprocessor.studies.demand_load import (
            apply_demand_levels,
        )
        levels = (
            DemandLevel(kVA_limit=3000.0, demand_pct=100.0),
            DemandLevel(kVA_limit=None, demand_pct=50.0),
        )
        result = apply_demand_levels(1000.0, levels)
        assert result == pytest.approx(1000.0)


class TestComputeDemand:

    def test_loadable(self):
        from app.postprocessor.studies.demand_load import (
            compute_demand, LoadEntry, DemandReport,
        )
        assert compute_demand is not None

    def test_single_entry_lighting(self):
        from app.postprocessor.studies.demand_load import (
            compute_demand, LoadEntry,
        )
        entries = [
            LoadEntry(
                name="Bay 1 lighting",
                category_code="NEC_220_42_LIGHTING",
                connected_kVA=2000.0,
            ),
        ]
        report = compute_demand(entries)
        assert report.total_connected_kVA == pytest.approx(2000.0)
        # 2000 < 3000 (primeiro nível), então 100% → demand = 2000
        assert report.total_demand_kVA == pytest.approx(2000.0)
        # Design = demand × LCL (1.25 para lighting)
        assert report.total_design_kVA == pytest.approx(2500.0)

    def test_multiple_categories_grouped(self):
        from app.postprocessor.studies.demand_load import (
            compute_demand, LoadEntry,
        )
        entries = [
            LoadEntry(
                name="Lighting 1",
                category_code="NEC_220_42_LIGHTING",
                connected_kVA=1000.0,
            ),
            LoadEntry(
                name="Lighting 2",
                category_code="NEC_220_42_LIGHTING",
                connected_kVA=1500.0,
            ),
            LoadEntry(
                name="Motor",
                category_code="NEC_220_50_MOTORS",
                connected_kVA=50000.0,
            ),
        ]
        report = compute_demand(entries)
        # 2 categorias agrupadas
        assert len(report.by_category) == 2
        cat_codes = {r.category_code for r in report.by_category}
        assert "NEC_220_42_LIGHTING" in cat_codes
        assert "NEC_220_50_MOTORS" in cat_codes

    def test_design_uses_lcl_factor(self):
        from app.postprocessor.studies.demand_load import (
            compute_demand, LoadEntry,
        )
        entries = [
            LoadEntry(
                name="Capacitor",
                category_code="CAPACITOR_BANK",
                connected_kVA=100.0,
            ),
        ]
        report = compute_demand(entries)
        # CAPACITOR_BANK: ALL @ 100%, LCL=1.35
        assert report.total_demand_kVA == pytest.approx(100.0)
        assert report.total_design_kVA == pytest.approx(135.0)

    def test_unknown_category_raises(self):
        from app.postprocessor.studies.demand_load import (
            compute_demand, LoadEntry,
        )
        entries = [
            LoadEntry(
                name="Bad",
                category_code="UNKNOWN_XYZ",
                connected_kVA=10.0,
            ),
        ]
        with pytest.raises(KeyError):
            compute_demand(entries)


class TestDemandReportSummary:

    def test_summary_returns_str(self):
        from app.postprocessor.studies.demand_load import (
            compute_demand, LoadEntry,
        )
        entries = [
            LoadEntry(
                name="Office PCs",
                category_code="OFFICE_EQUIPMENT",
                connected_kVA=20.0,
            ),
        ]
        report = compute_demand(entries)
        summary = report.summary()
        assert "Connected" in summary or "kVA" in summary

    def test_weighted_pf_computed(self):
        from app.postprocessor.studies.demand_load import (
            compute_demand, LoadEntry,
        )
        entries = [
            LoadEntry(
                name="L1", category_code="NEC_220_42_LIGHTING",
                connected_kVA=10.0,
            ),
            LoadEntry(
                name="M1", category_code="NEC_220_50_MOTORS",
                connected_kVA=10.0,
            ),
        ]
        report = compute_demand(entries)
        # weighted_pf entre 0 e 1
        assert 0.0 < report.weighted_pf <= 1.0
