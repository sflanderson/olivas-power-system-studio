"""
tests/test_pp_bctran_3w.py — v0.24.4: BCTRAN estendido para
trafos 3-enrolamento (H/M/B) e grupos trifásicos (YY/YD/DY/DD).

Cobre:

* ``TransformerConnection`` enum — valores esperados.
* ``ThreePhaseGroup`` — validação de clock (0..11), phase_shift
  em graus, formato ``describe()`` (ex: "Yd11").
* ``TransformerBCTRAN3Data`` validation — rejeita tensões ≤ 0,
  SCs fora de (0, 100)%, OC fora de [0, 100)%.
* ``compute_bctran_parameters_3w`` — matriz 3×3 simétrica em [L],
  diagonal em [R], ratios corretos, frequência escala.
* Validação dimensional: Z_{HM} reconstruído do [L], [R] =
  v_sc_pct × Z_base_HM.
"""

from __future__ import annotations

import math

import pytest

from app.preprocessor.bctran import (
    ThreePhaseGroup,
    Transformer3WindingParameters,
    TransformerBCTRAN3Data,
    TransformerConnection,
    TransformerOCTest,
    TransformerSCTest,
    compute_bctran_parameters_3w,
)


# ---------------------------------------------------------------------------
# TransformerConnection enum
# ---------------------------------------------------------------------------


class TestTransformerConnection:
    def test_expected_values(self):
        assert TransformerConnection.Y.value == "Y"
        assert TransformerConnection.D.value == "D"
        assert TransformerConnection.YAUTO.value == "Yauto"
        assert TransformerConnection.ZIGZAG.value == "Z"


# ---------------------------------------------------------------------------
# ThreePhaseGroup
# ---------------------------------------------------------------------------


class TestThreePhaseGroup:
    def test_default_is_yy0(self):
        g = ThreePhaseGroup()
        assert g.h_connection == TransformerConnection.Y
        assert g.l_connection == TransformerConnection.Y
        assert g.clock == 0

    def test_clock_out_of_range_rejected(self):
        with pytest.raises(ValueError, match="clock group"):
            ThreePhaseGroup(clock=12)

    def test_negative_clock_rejected(self):
        with pytest.raises(ValueError, match="clock group"):
            ThreePhaseGroup(clock=-1)

    def test_phase_shift_deg(self):
        g = ThreePhaseGroup(clock=6)
        assert g.phase_shift_deg == 180.0
        g = ThreePhaseGroup(clock=11)
        assert g.phase_shift_deg == 330.0

    def test_describe_yd11(self):
        g = ThreePhaseGroup(
            h_connection=TransformerConnection.Y,
            l_connection=TransformerConnection.D,
            clock=11,
        )
        assert g.describe() == "Yd11"

    def test_describe_dy5(self):
        g = ThreePhaseGroup(
            h_connection=TransformerConnection.D,
            l_connection=TransformerConnection.Y,
            clock=5,
        )
        assert g.describe() == "Dy5"

    def test_clock_accepts_all_valid(self):
        for c in range(0, 12):
            ThreePhaseGroup(clock=c)   # não-lanca


# ---------------------------------------------------------------------------
# TransformerBCTRAN3Data validation
# ---------------------------------------------------------------------------


def _std_3w_data(**overrides) -> TransformerBCTRAN3Data:
    """
    Dados típicos 300/300/50 MVA 500/138/13.8 kV.

    v0.28.2-PRO: ajustados v_sc_h_b e v_sc_m_b para produzir
    Wye-equivalente FISICAMENTE CONSISTENTE (todos x_i ≥ 0).
    Valores anteriores (10/15/8 %) produziam x_m = -133 Ω
    (não-físico).
    """
    base = dict(
        v_h=500e3, v_m=138e3, v_b=13.8e3,
        s_h=300e6, s_m=300e6, s_b=50e6,
        sc_h_m=TransformerSCTest(v_sc_pct=10.0, p_sc_kw=800.0),
        # v0.28.2-PRO: 15% → 8% (Wye-consistent)
        sc_h_b=TransformerSCTest(v_sc_pct=8.0, p_sc_kw=200.0),
        sc_m_b=TransformerSCTest(v_sc_pct=8.0, p_sc_kw=150.0),
        oc_test=TransformerOCTest(i_0_pct=0.3, p_0_kw=100.0),
        frequency=60.0,
        name="500-138-13.8",
    )
    base.update(overrides)
    return TransformerBCTRAN3Data(**base)


class TestBCTRAN3DataValidation:
    def test_happy_path(self):
        data = _std_3w_data()
        assert data.v_h == 500e3

    def test_v_h_negative_rejected(self):
        with pytest.raises(ValueError, match="v_h"):
            _std_3w_data(v_h=-1)

    def test_v_m_negative_rejected(self):
        with pytest.raises(ValueError, match="v_m"):
            _std_3w_data(v_m=0)

    def test_v_b_zero_rejected(self):
        with pytest.raises(ValueError, match="v_b"):
            _std_3w_data(v_b=0)

    def test_s_h_zero_rejected(self):
        with pytest.raises(ValueError, match="s_h"):
            _std_3w_data(s_h=0)

    def test_sc_h_m_out_of_range(self):
        with pytest.raises(ValueError, match="sc_h_m"):
            _std_3w_data(
                sc_h_m=TransformerSCTest(v_sc_pct=150.0, p_sc_kw=800.0),
            )

    def test_sc_h_b_negative_p(self):
        with pytest.raises(ValueError, match="sc_h_b"):
            _std_3w_data(
                sc_h_b=TransformerSCTest(v_sc_pct=15.0, p_sc_kw=-1.0),
            )

    def test_i_0_out_of_range(self):
        with pytest.raises(ValueError, match="i_0_pct"):
            _std_3w_data(
                oc_test=TransformerOCTest(i_0_pct=150.0, p_0_kw=100.0),
            )


# ---------------------------------------------------------------------------
# compute_bctran_parameters_3w — output structure
# ---------------------------------------------------------------------------


class TestCompute3W:
    def test_returns_3x3_matrices(self):
        p = compute_bctran_parameters_3w(_std_3w_data())
        assert len(p.R) == 3
        assert len(p.L) == 3
        for row in p.R:
            assert len(row) == 3
        for row in p.L:
            assert len(row) == 3

    def test_L_is_symmetric(self):
        p = compute_bctran_parameters_3w(_std_3w_data())
        assert p.is_symmetric()

    def test_R_is_diagonal(self):
        """[R] no algoritmo Wye-equivalent fica diagonal."""
        p = compute_bctran_parameters_3w(_std_3w_data())
        for i in range(3):
            for j in range(3):
                if i != j:
                    assert p.R[i][j] == 0.0

    def test_ratios_correct(self):
        p = compute_bctran_parameters_3w(_std_3w_data())
        assert p.ratios[0] == pytest.approx(500 / 138)
        assert p.ratios[1] == pytest.approx(500 / 13.8)

    def test_L_self_greater_than_mutual_with_balanced_data(self):
        """
        Com dados de teste triangle-inequality-consistent (SC entre
        pares formam triângulo válido), L[i][i] > L[i][j].

        Nota: datasheets reais às vezes violam essa propriedade
        porque perdas são medidas independentemente — caso em que
        o Wye-equivalent pode ter componentes negativas. Isso não
        é erro de cálculo; é artefato do teste. ATP aceita.
        """
        # SC%: HM=12, HB=10, MB=6 — satisfazem triangle inequality
        # em ohms referidos ao H (verificado algebricamente: X_m > 0).
        data = _std_3w_data(
            v_h=230e3, v_m=69e3, v_b=13.8e3,
            s_h=100e6, s_m=100e6, s_b=100e6,
            sc_h_m=TransformerSCTest(v_sc_pct=12.0, p_sc_kw=300.0),
            sc_h_b=TransformerSCTest(v_sc_pct=10.0, p_sc_kw=400.0),
            sc_m_b=TransformerSCTest(v_sc_pct=6.0,  p_sc_kw=200.0),
        )
        p = compute_bctran_parameters_3w(data)
        for i in range(3):
            for j in range(3):
                if i != j:
                    assert p.L[i][i] >= p.L[i][j] - 1e-6


class TestPhysicalSanity:
    def test_z_hm_reconstructed_from_matrices(self):
        """
        Z_{HM} visto de H (com M em curto, B aberto) deve
        corresponder ao v_sc_pct * Z_base_HM do teste original.
        """
        data = _std_3w_data()
        params = compute_bctran_parameters_3w(data)

        # Z_HM do teste: (v_sc_HM/100) * V_H²/min(S_H, S_M)
        s_hm = min(data.s_h, data.s_m)
        z_base_hm = data.v_h ** 2 / s_hm
        z_hm_expected = (data.sc_h_m.v_sc_pct / 100.0) * z_base_hm

        # Z_HM da matriz: L_HH + L_MM - 2*L_HM (dispersão equivalente)
        omega = 2 * math.pi * 60
        l_hh = params.L[0][0]
        l_mm = params.L[1][1]
        l_hm = params.L[0][1]
        x_hm_eff = (l_hh + l_mm - 2 * l_hm) * omega
        r_hm_eff = params.R[0][0] + params.R[1][1]
        z_hm_eff = math.sqrt(r_hm_eff ** 2 + x_hm_eff ** 2)

        assert z_hm_eff == pytest.approx(z_hm_expected, rel=0.01)

    def test_clock_preserved_in_parameters(self):
        data = _std_3w_data(
            group_3phase=ThreePhaseGroup(
                h_connection=TransformerConnection.Y,
                l_connection=TransformerConnection.D,
                clock=11,
            ),
        )
        p = compute_bctran_parameters_3w(data)
        assert p.group.describe() == "Yd11"
        assert p.group.phase_shift_deg == 330.0


# ---------------------------------------------------------------------------
# Frequency scaling
# ---------------------------------------------------------------------------


class TestFrequencyScaling:
    def test_L_scales_inversely_with_frequency(self):
        data_60 = _std_3w_data(frequency=60.0)
        data_50 = _std_3w_data(frequency=50.0)
        p60 = compute_bctran_parameters_3w(data_60)
        p50 = compute_bctran_parameters_3w(data_50)
        ratio = p50.L[0][0] / p60.L[0][0]
        assert ratio == pytest.approx(60.0 / 50.0, rel=1e-4)

    def test_R_independent_of_frequency(self):
        data_60 = _std_3w_data(frequency=60.0)
        data_50 = _std_3w_data(frequency=50.0)
        r_60 = compute_bctran_parameters_3w(data_60).R[0][0]
        r_50 = compute_bctran_parameters_3w(data_50).R[0][0]
        assert r_60 == pytest.approx(r_50, rel=1e-9)
