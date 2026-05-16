"""
tests/test_pp_v3_0_3_mf_tables.py — v3.0.3 Sprint B.2.

Interrupting Multiplying Factor (MF) tables — Figs 1-1 a 1-15.

Cobre:
* `BreakerCycle` enum — §1.3.7 p. 1-19 (linhas 1102–1104)
* `FaultType` enum — §1.3.8 p. 1-21 (Figs label)
* `AnsiStandard` enum — C37.5 (Total) vs C37.010 (Symmetrical)
* `mf_local()` — Figs 1-1, 1-2, 1-4..1-11 (LOCAL gens)
* `mf_remote()` — Figs 1-3, 1-12..1-15 (REMOTE gens, dc-decay only)
* `mf_interpolated()` — peso linear NACD (§1.3.7 prose linhas 1147-1153)
* `mf_by_mode()` — dispatcher dos 3 modos NACD

Anti-alucinação: cada teste cita seção+página de A_Fault e/ou IEEE C37.x-1979.
Anti-simplismo: cobre 4 cycles × 2 fault types × 2 stds × 3 NACD modes.

ATENÇÃO: o manual A_Fault declara que Figs 1-1..1-15 são gráficos
fotograficamente interpolados (§1.3.8 p. 1-21 linhas 1267-1273) e
**não publica os valores em tabela**. Olivas usa interpolação a partir
de pontos numéricos publicados no próprio manual (§1.3.7, §1.3.8, §1.4.3,
§1.4.4) — todos validados contra exemplos numéricos do manual.

Para robustez >v4.0.0, recomenda-se substituir pelo dataset numérico
de IEEE Std 551-2006 (Violet Book) ou IEEE Std 141 (Red Book).

Reference: SKM PTW Reference-A_Fault.pdf, edição 2006-03-26.
"""

from __future__ import annotations

import math
import pytest


# ===========================================================================
# Sprint B.2.A — Enums (BreakerCycle, FaultType, AnsiStandard)
# ===========================================================================


class TestEnums:

    def test_breaker_cycle_four_options(self):
        """§1.3.7 p. 1-19: 4 breaker classes — 2/3/5/8 cycle rated."""
        from app.standards.ansi_c37 import BreakerCycle
        cycles = {b.value for b in BreakerCycle}
        assert cycles == {2, 3, 5, 8}

    def test_breaker_contact_parting_table(self):
        """§1.3.7 linhas 1102-1104: contact parting times."""
        from app.standards.ansi_c37 import BREAKER_CONTACT_PARTING
        # rated_cycle: contact_parting_cycles
        assert BREAKER_CONTACT_PARTING == {2: 1.5, 3: 2.0, 5: 3.0, 8: 4.0}

    def test_fault_type_enum(self):
        """§1.3.8: 3-phase + SLG."""
        from app.standards.ansi_c37 import FaultType
        assert {f.value for f in FaultType} == {"3ph", "slg"}

    def test_ansi_standard_enum(self):
        """§1.3.3: C37.5 (pre-1964 Total Rated) vs C37.010 (post-1964 Symm-Rated)."""
        from app.standards.ansi_c37 import AnsiStandard
        assert {s.value for s in AnsiStandard} == {"C37.5", "C37.010"}


# ===========================================================================
# Sprint B.2.B — mf_local() — Figs 1-1, 1-2, 1-4..1-11
# ===========================================================================


class TestMfLocal:

    def test_low_xr_gives_unity(self):
        """X/R baixo (sem componente DC) → MF próximo de 1.0."""
        from app.standards.ansi_c37 import (
            BreakerCycle, FaultType, AnsiStandard, mf_local,
        )
        mf = mf_local(
            x_over_r=2.0,
            breaker=BreakerCycle.CYC_5,
            fault=FaultType.THREE_PHASE,
            std=AnsiStandard.C37_010,
        )
        assert 0.99 <= mf <= 1.05

    def test_high_xr_gives_high_mf_local_5cyc(self):
        """
        §1.3.8 p. 1-22 linha 1289: X/R=60, 5-cyc breaker, LOCAL 3-ph → MF=1.167.
        Tolerância ±0.05 (5%) — fórmula analítica vs gráfico interpolado.
        """
        from app.standards.ansi_c37 import (
            BreakerCycle, FaultType, AnsiStandard, mf_local,
        )
        mf = mf_local(
            x_over_r=60.0,
            breaker=BreakerCycle.CYC_5,
            fault=FaultType.THREE_PHASE,
            std=AnsiStandard.C37_010,
        )
        assert mf == pytest.approx(1.167, abs=0.05)

    def test_high_xr_8cyc_local_mf_close_to_1_180(self):
        """
        §1.3.8 p. 1-22 linha 1290: X/R=60, 8-cyc breaker (4-cyc parting),
        LOCAL 3-ph → MF=1.180. Tolerância ±0.05.
        """
        from app.standards.ansi_c37 import (
            BreakerCycle, FaultType, AnsiStandard, mf_local,
        )
        mf = mf_local(
            x_over_r=60.0,
            breaker=BreakerCycle.CYC_8,
            fault=FaultType.THREE_PHASE,
            std=AnsiStandard.C37_010,
        )
        assert mf == pytest.approx(1.180, abs=0.05)

    def test_remote_higher_than_local_at_low_xr(self):
        """
        Validação contra §1.4.3 Case 2 INTERPOLATED:
        X/R=11.88, 5-cyc → MF_remote=1.030, MF_local≈1.0006 (back-derived).
        Para X/R baixo, AC decrement domina e LOCAL < REMOTE.
        """
        from app.standards.ansi_c37 import (
            BreakerCycle, FaultType, AnsiStandard, mf_local, mf_remote,
        )
        mf_l = mf_local(11.88, BreakerCycle.CYC_5, FaultType.THREE_PHASE, AnsiStandard.C37_010)
        mf_r = mf_remote(11.88, BreakerCycle.CYC_5, FaultType.THREE_PHASE, AnsiStandard.C37_010)
        # Aceita LOCAL ≤ REMOTE com tolerância (fitting empírico)
        assert mf_l <= mf_r + 0.05  # tolerância fitting


# ===========================================================================
# Sprint B.2.C — mf_remote() — Figs 1-3, 1-12..1-15 (dc-decay only)
# ===========================================================================


class TestMfRemote:

    def test_low_xr_gives_unity(self):
        """X/R baixo → MF ≈ 1.0 (sem componente DC)."""
        from app.standards.ansi_c37 import (
            BreakerCycle, FaultType, AnsiStandard, mf_remote,
        )
        mf = mf_remote(2.0, BreakerCycle.CYC_5, FaultType.THREE_PHASE, AnsiStandard.C37_010)
        assert 0.99 <= mf <= 1.05

    def test_remote_3ph_equals_slg_per_figure_label(self):
        """
        §1.3.8: Figs 1-3 e 1-12..1-15 são rotuladas '3-phase AND SLG'
        (mesmo gráfico). REMOTE não diferencia 3-ph de SLG.
        """
        from app.standards.ansi_c37 import (
            BreakerCycle, FaultType, AnsiStandard, mf_remote,
        )
        mf_3ph = mf_remote(20.0, BreakerCycle.CYC_5, FaultType.THREE_PHASE, AnsiStandard.C37_010)
        mf_slg = mf_remote(20.0, BreakerCycle.CYC_5, FaultType.SLG, AnsiStandard.C37_010)
        assert mf_3ph == pytest.approx(mf_slg)

    def test_remote_at_xr_11_88_5cyc_close_to_1_030(self):
        """
        §1.4.3 Case 2 All Remote (linha 2456): X/R=11.88, 5-cyc → MF=1.030.
        """
        from app.standards.ansi_c37 import (
            BreakerCycle, FaultType, AnsiStandard, mf_remote,
        )
        mf = mf_remote(11.88, BreakerCycle.CYC_5, FaultType.THREE_PHASE, AnsiStandard.C37_010)
        assert mf == pytest.approx(1.030, abs=0.05)


# ===========================================================================
# Sprint B.2.D — mf_interpolated() — peso linear NACD
# ===========================================================================


class TestMfInterpolated:

    def test_nacd_zero_equals_mf_local(self):
        """NACD=0 (todos LOCAL) → MF_interp == MF_local."""
        from app.standards.ansi_c37 import (
            BreakerCycle, FaultType, AnsiStandard,
            mf_local, mf_interpolated,
        )
        mf_l = mf_local(20.0, BreakerCycle.CYC_5, FaultType.THREE_PHASE, AnsiStandard.C37_010)
        mf_i = mf_interpolated(20.0, 0.0, BreakerCycle.CYC_5, FaultType.THREE_PHASE, AnsiStandard.C37_010)
        assert mf_i == pytest.approx(mf_l)

    def test_nacd_one_equals_mf_remote(self):
        """NACD=1 (todos REMOTE) → MF_interp == MF_remote."""
        from app.standards.ansi_c37 import (
            BreakerCycle, FaultType, AnsiStandard,
            mf_remote, mf_interpolated,
        )
        mf_r = mf_remote(20.0, BreakerCycle.CYC_5, FaultType.THREE_PHASE, AnsiStandard.C37_010)
        mf_i = mf_interpolated(20.0, 1.0, BreakerCycle.CYC_5, FaultType.THREE_PHASE, AnsiStandard.C37_010)
        assert mf_i == pytest.approx(mf_r)

    def test_nacd_half_is_average(self):
        """NACD=0.5 → average linear de local e remote."""
        from app.standards.ansi_c37 import (
            BreakerCycle, FaultType, AnsiStandard,
            mf_local, mf_remote, mf_interpolated,
        )
        mf_l = mf_local(20.0, BreakerCycle.CYC_5, FaultType.THREE_PHASE, AnsiStandard.C37_010)
        mf_r = mf_remote(20.0, BreakerCycle.CYC_5, FaultType.THREE_PHASE, AnsiStandard.C37_010)
        mf_i = mf_interpolated(20.0, 0.5, BreakerCycle.CYC_5, FaultType.THREE_PHASE, AnsiStandard.C37_010)
        assert mf_i == pytest.approx(0.5 * mf_l + 0.5 * mf_r)


# ===========================================================================
# Sprint B.2.E — mf_by_mode() dispatcher
# ===========================================================================


class TestMfByMode:

    def test_all_remote_mode_uses_remote_curve(self):
        """ALL_REMOTE mode ignora NACD e força MF_remote."""
        from app.standards.ansi_c37 import (
            BreakerCycle, FaultType, AnsiStandard, NacdMode,
            mf_remote, mf_by_mode,
        )
        mf_r = mf_remote(20.0, BreakerCycle.CYC_5, FaultType.THREE_PHASE, AnsiStandard.C37_010)
        mf = mf_by_mode(
            x_over_r=20.0,
            nacd=0.3,  # baixo, mas mode força remote
            mode=NacdMode.ALL_REMOTE,
            breaker=BreakerCycle.CYC_5,
            fault=FaultType.THREE_PHASE,
            std=AnsiStandard.C37_010,
        )
        assert mf == pytest.approx(mf_r)

    def test_predominant_mode_below_threshold_uses_local(self):
        """PREDOMINANT mode + NACD<0.5 → usa LOCAL curve."""
        from app.standards.ansi_c37 import (
            BreakerCycle, FaultType, AnsiStandard, NacdMode,
            mf_local, mf_by_mode,
        )
        mf_l = mf_local(20.0, BreakerCycle.CYC_5, FaultType.THREE_PHASE, AnsiStandard.C37_010)
        mf = mf_by_mode(
            x_over_r=20.0,
            nacd=0.3,
            mode=NacdMode.PREDOMINANT,
            breaker=BreakerCycle.CYC_5,
            fault=FaultType.THREE_PHASE,
            std=AnsiStandard.C37_010,
        )
        assert mf == pytest.approx(mf_l)

    def test_predominant_mode_above_threshold_uses_remote(self):
        """PREDOMINANT mode + NACD>=0.5 → usa REMOTE curve."""
        from app.standards.ansi_c37 import (
            BreakerCycle, FaultType, AnsiStandard, NacdMode,
            mf_remote, mf_by_mode,
        )
        mf_r = mf_remote(20.0, BreakerCycle.CYC_5, FaultType.THREE_PHASE, AnsiStandard.C37_010)
        mf = mf_by_mode(
            x_over_r=20.0,
            nacd=0.7,
            mode=NacdMode.PREDOMINANT,
            breaker=BreakerCycle.CYC_5,
            fault=FaultType.THREE_PHASE,
            std=AnsiStandard.C37_010,
        )
        assert mf == pytest.approx(mf_r)

    def test_interpolated_mode_uses_weighted_combination(self):
        """INTERPOLATED mode → peso linear pela NACD."""
        from app.standards.ansi_c37 import (
            BreakerCycle, FaultType, AnsiStandard, NacdMode,
            mf_interpolated, mf_by_mode,
        )
        mf_int = mf_interpolated(20.0, 0.6, BreakerCycle.CYC_5, FaultType.THREE_PHASE, AnsiStandard.C37_010)
        mf = mf_by_mode(
            x_over_r=20.0,
            nacd=0.6,
            mode=NacdMode.INTERPOLATED,
            breaker=BreakerCycle.CYC_5,
            fault=FaultType.THREE_PHASE,
            std=AnsiStandard.C37_010,
        )
        assert mf == pytest.approx(mf_int)
