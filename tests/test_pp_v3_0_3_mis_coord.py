"""
tests/test_pp_v3_0_3_mis_coord.py — v3.0.3 Sprint B.6.

Mis-coordination ratio + Levels to Search + Cleared Fault Threshold.

Conforme PTW Tutorial §Part 5 p. 144-145:

* Cleared Fault Threshold (default 80%)
* Mis-Coordination Ratio (configurável)
* Levels to Search upstream
* Conditions 1 e 2 do mis-coord check

Anti-alucinação: cita Tutorial §Part 5 p. 144-145.
Anti-simplismo: cobre threshold + ratio + N levels search.

Reference: PTW Tutorial §Part 5 p. 144-145.
"""

from __future__ import annotations

import pytest


# ===========================================================================
# Sprint B.6.A — cleared_fault_threshold()
# ===========================================================================


class TestClearedFaultThreshold:

    def test_threshold_default_80_percent(self):
        """§Tutorial Part 5 p. 144: default Cleared Fault Threshold = 80%."""
        from app.postprocessor.mis_coordination import (
            DEFAULT_CLEARED_FAULT_THRESHOLD,
        )
        assert DEFAULT_CLEARED_FAULT_THRESHOLD == 0.80

    def test_main_clears_when_through_current_above_threshold(self):
        """
        I_through_main / I_total ≥ 80% → main is_cleared = True
        (i.e., main breaker pode interromper a corrente passando por ele).
        """
        from app.postprocessor.mis_coordination import is_main_cleared
        # 90% da corrente passa pelo main → cleared
        assert is_main_cleared(i_main_kA=9.0, i_total_kA=10.0, threshold=0.80) is True

    def test_main_not_cleared_when_through_current_below_threshold(self):
        """
        I_through_main / I_total < 80% → main NOT cleared
        (significant fault current bypassing — backup needed).
        """
        from app.postprocessor.mis_coordination import is_main_cleared
        # 70% bypass → not cleared
        assert is_main_cleared(i_main_kA=7.0, i_total_kA=10.0, threshold=0.80) is False


# ===========================================================================
# Sprint B.6.B — mis_coordination_ratio()
# ===========================================================================


class TestMisCoordinationRatio:

    def test_zero_when_main_first(self):
        """
        Mis-coord ratio: t_main_trip / t_backup_trip.
        Main trip antes de backup → ratio < 1 → coordinated.
        """
        from app.postprocessor.mis_coordination import mis_coordination_ratio
        ratio = mis_coordination_ratio(
            t_main_trip_s=0.05,    # main = 50ms
            t_backup_trip_s=0.20,  # backup = 200ms
        )
        # 0.25 — main mais rápido = coordinated (< 1)
        assert ratio == pytest.approx(0.25)

    def test_one_when_simultaneous(self):
        """Trip times iguais → ratio = 1 (limite)."""
        from app.postprocessor.mis_coordination import mis_coordination_ratio
        ratio = mis_coordination_ratio(t_main_trip_s=0.10, t_backup_trip_s=0.10)
        assert ratio == 1.0

    def test_above_one_when_backup_first(self):
        """
        Backup trip antes de main → ratio > 1 → mis-coordination!
        Cenário ruim: arc-flash pode ter bus inteiro desligado por backup.
        """
        from app.postprocessor.mis_coordination import mis_coordination_ratio
        ratio = mis_coordination_ratio(
            t_main_trip_s=0.30,
            t_backup_trip_s=0.10,
        )
        assert ratio > 1.0

    def test_invalid_zero_backup_raises(self):
        """t_backup = 0 não é físico."""
        from app.postprocessor.mis_coordination import mis_coordination_ratio
        with pytest.raises(ValueError):
            mis_coordination_ratio(t_main_trip_s=0.10, t_backup_trip_s=0.0)


# ===========================================================================
# Sprint B.6.C — upstream_search_levels enum / count
# ===========================================================================


class TestUpstreamSearch:

    def test_default_levels_to_search_is_3(self):
        """§Tutorial Part 5 p. 145: default Levels to Search = 3."""
        from app.postprocessor.mis_coordination import (
            DEFAULT_LEVELS_TO_SEARCH,
        )
        assert DEFAULT_LEVELS_TO_SEARCH == 3

    def test_search_finds_devices_within_levels(self):
        """
        Topologia fictícia: device → level1 → level2 → level3.
        upstream_search com max_levels=3 retorna 3 devices.
        """
        from app.postprocessor.mis_coordination import upstream_search
        # Mock topology: dict device → upstream_device
        topology = {
            "DEV": "L1",
            "L1": "L2",
            "L2": "L3",
            "L3": "MAIN",
            "MAIN": None,
        }
        result = upstream_search(
            start_device="DEV", topology=topology, max_levels=3,
        )
        assert result == ["L1", "L2", "L3"]

    def test_search_stops_at_no_upstream(self):
        """Sem upstream → para a busca."""
        from app.postprocessor.mis_coordination import upstream_search
        topology = {
            "DEV": "L1",
            "L1": None,  # no upstream
        }
        result = upstream_search(
            start_device="DEV", topology=topology, max_levels=10,
        )
        assert result == ["L1"]

    def test_search_limited_by_max_levels(self):
        """max_levels < topology depth → para no limite."""
        from app.postprocessor.mis_coordination import upstream_search
        topology = {
            "A": "B", "B": "C", "C": "D", "D": "E", "E": None,
        }
        result = upstream_search(
            start_device="A", topology=topology, max_levels=2,
        )
        assert result == ["B", "C"]
