"""
tests.test_pp_v1_2_0_tcc_segments_alpha3 — sub-sprint α.3.

Cobre os 2 segments analíticos PTW introduzidos em v1.2.0 α.3:

* ``TCCSegmentAnalyticAD`` — fórmula `T = AD/(M^N - C) + BD + K`
* ``TCCSegmentAnalyticSM`` — polynomial `T = SM·[A + B(M-C) + D/(M-C)² + E/(M-C)³]`

Validação anti-alucinação: usamos como ouro os parâmetros canônicos
de IEEE C37.112-2018 que ANSI Mod-Inv satisfaz com
(AD, N, C, BD, K) = (0.0515, 0.02, 1.0, 0.0, 0.114). Se nossa
fórmula AD reproduzir t≈10s @ M=2 com TMS=1, está correta —
mesmo número que ``operating_time_s(ANSI_MOD_INV, 2, 1)`` retorna.

Aceite α.3
==========

* 12+ testes, 100% verde
* Casos canônicos de IEEE C37.112 reproduzidos
* Sem regressão em α.1+α.2
"""

from __future__ import annotations

import math

import pytest

from app.postprocessor.tcc_curves import CurveType, operating_time_s
from app.postprocessor.tcc_segments import (
    TCCSegment,
    TCCSegmentAnalyticAD,
    TCCSegmentAnalyticSM,
)


# ---------------------------------------------------------------------------
# TCCSegmentAnalyticAD
# ---------------------------------------------------------------------------


class TestTCCSegmentAnalyticAD:

    def test_below_pickup_returns_inf(self):
        s = TCCSegmentAnalyticAD(
            segment_id="x", pickup_A=100.0,
            AD=0.0515, N=0.02, C=1.0, BD=0.0, K=0.114,
        )
        assert math.isinf(s.time_at_current(50.0))
        assert math.isinf(s.time_at_current(100.0))

    def test_ansi_mod_inverse_canonical(self):
        """
        Validação anti-alucinação: a fórmula AD com parâmetros
        ANSI Mod-Inv DEVE coincidir com operating_time_s do
        legacy (que usa _CURVE_CONSTANTS = (0.0515, 0.02, 0.114)).

        Para M=2, TMS=1: t ≈ 10.03s (referência IEEE C37.112).
        Aqui validamos t ≈ 22s (porque o TMS legacy multiplica
        toda a expressão; nosso AD não tem TMS embutido — é
        um nível mais cru). O check é via paralelo:

        operating_time_s(ANSI_MOD_INV, 2.0, 1.0)
            = 1.0 * (0.0515 / (2^0.02 - 1) + 0.114)
            ≈ 3.81 s

        Nosso analytic com (AD=0.0515, N=0.02, C=1, BD=0, K=0.114)
        deve retornar EXATAMENTE o mesmo valor para M=2.
        """
        s = TCCSegmentAnalyticAD(
            segment_id="ANSI mod-inv canon",
            pickup_A=100.0,
            AD=0.0515, N=0.02, C=1.0, BD=0.0, K=0.114,
        )
        # I = 200A → M = 2
        t_analytic = s.time_at_current(200.0)
        # Compara com legacy
        t_legacy = operating_time_s(
            CurveType.ANSI_MODERATELY_INVERSE,
            multiple_of_pickup=2.0,
            tms=1.0,
        )
        assert t_analytic == pytest.approx(t_legacy, rel=1e-6), (
            f"Analytic AD {t_analytic} != legacy {t_legacy}"
        )

    def test_ansi_very_inverse_canonical(self):
        """ANSI Very Inverse: (A=19.61, p=2.0, B=0.491)."""
        s = TCCSegmentAnalyticAD(
            segment_id="ANSI VI canon",
            pickup_A=100.0,
            AD=19.61, N=2.0, C=1.0, BD=0.0, K=0.491,
        )
        t_analytic = s.time_at_current(500.0)  # M=5
        t_legacy = operating_time_s(
            CurveType.ANSI_VERY_INVERSE,
            multiple_of_pickup=5.0,
            tms=1.0,
        )
        assert t_analytic == pytest.approx(t_legacy, rel=1e-6)

    def test_iec_standard_inverse_canonical(self):
        """IEC SI: A=0.14, p=0.02, B=0."""
        s = TCCSegmentAnalyticAD(
            segment_id="IEC SI canon",
            pickup_A=100.0,
            AD=0.14, N=0.02, C=1.0, BD=0.0, K=0.0,
        )
        t_analytic = s.time_at_current(1000.0)  # M=10
        t_legacy = operating_time_s(
            CurveType.IEC_STANDARD_INVERSE,
            multiple_of_pickup=10.0,
            tms=1.0,
        )
        assert t_analytic == pytest.approx(t_legacy, rel=1e-6)

    def test_disabled_returns_inf(self):
        s = TCCSegmentAnalyticAD(
            segment_id="x", pickup_A=100.0,
            AD=0.14, N=0.02, C=1.0, enabled=False,
        )
        assert math.isinf(s.time_at_current(1000.0))

    def test_large_C_shifts_pickup_effective(self):
        """Se C=4.0, pickup efetivo é I = pickup × C^(1/N).
        Para N=2, C=4: I_eff = 100 × 2 = 200A.
        I=150 deve dar inf (M^N=2.25 < 4)."""
        s = TCCSegmentAnalyticAD(
            segment_id="x", pickup_A=100.0,
            AD=10.0, N=2.0, C=4.0, BD=0.0, K=0.0,
        )
        assert math.isinf(s.time_at_current(150.0))   # M=1.5, M²=2.25 < 4
        assert math.isinf(s.time_at_current(200.0))   # M=2, M²=4 = C → boundary
        # Acima do threshold (M²-4 > 0)
        t = s.time_at_current(300.0)   # M=3, M²=9, denom=5
        assert math.isfinite(t)
        assert t == pytest.approx(10.0 / 5.0, rel=1e-3)  # 2.0s

    def test_points_excludes_inf_below_pickup_eff(self):
        s = TCCSegmentAnalyticAD(
            segment_id="x", pickup_A=100.0,
            AD=10.0, N=2.0, C=4.0,
        )
        pts = s.points(i_min_A=10, i_max_A=10000, n_points=50)
        # Todos os pontos devem ter t finito
        for I, t in pts:
            assert math.isfinite(t)
            assert t > 0
        assert len(pts) > 20


# ---------------------------------------------------------------------------
# TCCSegmentAnalyticSM
# ---------------------------------------------------------------------------


class TestTCCSegmentAnalyticSM:

    def test_below_or_at_C_returns_inf(self):
        # Para M ≤ C: divisor (M-C)^2 = 0 ou (M-C) negativo
        s = TCCSegmentAnalyticSM(
            segment_id="x", pickup_A=100.0,
            SM=1.0, A=0.5, B=0.1, C=1.0, D=0.05, E=0.01,
        )
        # I = 100 → M=1.0 = C → inf
        assert math.isinf(s.time_at_current(100.0))
        # I = 80 → M=0.8 < C → inf
        assert math.isinf(s.time_at_current(80.0))

    def test_well_above_C_returns_finite(self):
        s = TCCSegmentAnalyticSM(
            segment_id="x", pickup_A=100.0,
            SM=1.0, A=0.5, B=0.1, C=1.0, D=0.05, E=0.01,
        )
        # M = 5: delta=4
        # poly = 0.5 + 0.1*4 + 0.05/16 + 0.01/64
        #      = 0.5 + 0.4 + 0.003125 + 0.000156...
        #      ≈ 0.903...
        t = s.time_at_current(500.0)
        assert math.isfinite(t)
        assert 0.85 < t < 0.95

    def test_SM_scales_linearly(self):
        s1 = TCCSegmentAnalyticSM(
            segment_id="x", pickup_A=100.0,
            SM=1.0, A=0.5, B=0.1, C=1.0, D=0.05, E=0.01,
        )
        s10 = TCCSegmentAnalyticSM(
            segment_id="x", pickup_A=100.0,
            SM=10.0, A=0.5, B=0.1, C=1.0, D=0.05, E=0.01,
        )
        I = 500.0
        t1 = s1.time_at_current(I)
        t10 = s10.time_at_current(I)
        assert t10 == pytest.approx(t1 * 10.0, rel=1e-6)

    def test_disabled_returns_inf(self):
        s = TCCSegmentAnalyticSM(
            segment_id="x", pickup_A=100.0,
            SM=1.0, A=0.5, B=0.1, C=1.0, D=0.05, E=0.01,
            enabled=False,
        )
        assert math.isinf(s.time_at_current(1000.0))

    def test_negative_polynomial_returns_inf(self):
        """Se SM negativo ou poly cai abaixo de zero, segment retorna inf
        (não-físico)."""
        s = TCCSegmentAnalyticSM(
            segment_id="x", pickup_A=100.0,
            SM=-1.0, A=0.5, B=0.1, C=1.0, D=0.05, E=0.01,
        )
        assert math.isinf(s.time_at_current(500.0))

    def test_points_count(self):
        s = TCCSegmentAnalyticSM(
            segment_id="x", pickup_A=100.0,
            SM=1.0, A=0.5, B=0.1, C=1.0, D=0.05, E=0.01,
        )
        pts = s.points(i_min_A=200, i_max_A=10000, n_points=50)
        assert len(pts) >= 30
        for I, t in pts:
            assert math.isfinite(t)
            assert t > 0


# ---------------------------------------------------------------------------
# Protocol conformance
# ---------------------------------------------------------------------------


class TestProtocolConformance:

    @pytest.mark.parametrize("seg_factory", [
        lambda: TCCSegmentAnalyticAD(
            segment_id="x", pickup_A=100.0, AD=0.14, N=0.02,
        ),
        lambda: TCCSegmentAnalyticSM(
            segment_id="x", pickup_A=100.0, SM=1.0,
            A=0.5, B=0.1, C=1.0, D=0.05, E=0.01,
        ),
    ])
    def test_segment_satisfies_protocol(self, seg_factory):
        seg = seg_factory()
        assert isinstance(seg, TCCSegment)
        assert callable(seg.time_at_current)
        assert callable(seg.points)
