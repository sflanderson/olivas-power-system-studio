"""
tests/test_pp_bctran.py — v0.24.0: rotina BCTRAN para cálculo de
parâmetros de transformador a partir de dados de teste padrão.

Cobre:

* Validação de inputs (``TransformerBCTRANData.__post_init__``).
* Cálculo das matrizes ``[R]``, ``[L]`` para casos conhecidos.
* Sanidade física: ``Z_sc`` reconstruído a partir de ``[R]``,
  ``[L]`` deve bater com o teste de curto-circuito original.
* Conservação de energia: R_sc total = ``p_sc / I_nom²``.
* ``turns_ratio`` correto.
* Simetria das matrizes.
* Edge case ``i_0_pct == 0`` (magnetização desprezível) → L finito
  mas grande (representado como ~1 TΩ).
* Formatação básica das linhas ATP.

Não cobre (próximas sub-sprints):
* Trafos 3φ (v0.24.2+).
* Trafos 3-enrolamento (v0.24.2+).
* Saturação via Type-98 (v0.24.2).
* Formato estrito de colunas ATP (v0.24.1 — integração no bridge).
"""

from __future__ import annotations

import math

import pytest

from app.preprocessor.bctran import (
    TransformerBCTRANData,
    TransformerOCTest,
    TransformerParameters,
    TransformerSCTest,
    compute_bctran_parameters,
)


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _std_100mva_230_69() -> TransformerBCTRANData:
    """Trafo típico 100 MVA, 230/69 kV, 60 Hz — SC 10%, OC 0.5%."""
    return TransformerBCTRANData(
        v_h=230_000,
        v_l=69_000,
        s_nom=100e6,
        frequency=60.0,
        sc_test=TransformerSCTest(v_sc_pct=10.0, p_sc_kw=400.0),
        oc_test=TransformerOCTest(i_0_pct=0.5, p_0_kw=50.0),
        name="100MVA-230-69",
    )


def _distribution_500kva() -> TransformerBCTRANData:
    """Trafo de distribuição 500 kVA, 13.8/0.38 kV, 60 Hz — SC 5%, OC 2%."""
    return TransformerBCTRANData(
        v_h=13_800,
        v_l=380,
        s_nom=500e3,
        frequency=60.0,
        sc_test=TransformerSCTest(v_sc_pct=5.0, p_sc_kw=7.0),
        oc_test=TransformerOCTest(i_0_pct=2.0, p_0_kw=1.2),
    )


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------


class TestInputValidation:
    def test_negative_v_h_rejected(self):
        with pytest.raises(ValueError, match="v_h"):
            TransformerBCTRANData(
                v_h=-1, v_l=69000, s_nom=100e6,
                sc_test=TransformerSCTest(10.0, 400.0),
                oc_test=TransformerOCTest(0.5, 50.0),
            )

    def test_negative_v_l_rejected(self):
        with pytest.raises(ValueError, match="v_l"):
            TransformerBCTRANData(
                v_h=230000, v_l=-69000, s_nom=100e6,
                sc_test=TransformerSCTest(10.0, 400.0),
                oc_test=TransformerOCTest(0.5, 50.0),
            )

    def test_negative_s_nom_rejected(self):
        with pytest.raises(ValueError, match="s_nom"):
            TransformerBCTRANData(
                v_h=230000, v_l=69000, s_nom=-1,
                sc_test=TransformerSCTest(10.0, 400.0),
                oc_test=TransformerOCTest(0.5, 50.0),
            )

    def test_negative_frequency_rejected(self):
        with pytest.raises(ValueError, match="frequency"):
            TransformerBCTRANData(
                v_h=230000, v_l=69000, s_nom=100e6, frequency=-60.0,
                sc_test=TransformerSCTest(10.0, 400.0),
                oc_test=TransformerOCTest(0.5, 50.0),
            )

    def test_v_sc_pct_out_of_range_rejected(self):
        with pytest.raises(ValueError, match="v_sc_pct"):
            TransformerBCTRANData(
                v_h=230000, v_l=69000, s_nom=100e6,
                sc_test=TransformerSCTest(v_sc_pct=150.0, p_sc_kw=400.0),
                oc_test=TransformerOCTest(0.5, 50.0),
            )

    def test_v_sc_pct_zero_rejected(self):
        with pytest.raises(ValueError, match="v_sc_pct"):
            TransformerBCTRANData(
                v_h=230000, v_l=69000, s_nom=100e6,
                sc_test=TransformerSCTest(v_sc_pct=0.0, p_sc_kw=400.0),
                oc_test=TransformerOCTest(0.5, 50.0),
            )

    def test_negative_p_sc_rejected(self):
        with pytest.raises(ValueError, match="p_sc_kw"):
            TransformerBCTRANData(
                v_h=230000, v_l=69000, s_nom=100e6,
                sc_test=TransformerSCTest(v_sc_pct=10.0, p_sc_kw=-1.0),
                oc_test=TransformerOCTest(0.5, 50.0),
            )

    def test_i_0_pct_100_rejected(self):
        with pytest.raises(ValueError, match="i_0_pct"):
            TransformerBCTRANData(
                v_h=230000, v_l=69000, s_nom=100e6,
                sc_test=TransformerSCTest(10.0, 400.0),
                oc_test=TransformerOCTest(i_0_pct=100.0, p_0_kw=50.0),
            )

    def test_zero_i_0_accepted_magnetization_negligible(self):
        """i_0_pct = 0 representa magnetização desprezível — permitido."""
        data = TransformerBCTRANData(
            v_h=230000, v_l=69000, s_nom=100e6,
            sc_test=TransformerSCTest(10.0, 400.0),
            oc_test=TransformerOCTest(i_0_pct=0.0, p_0_kw=0.0),
        )
        params = compute_bctran_parameters(data)
        # Magnetização ausente → L grande (representado como ~1 TΩ/ω)
        assert params.L[0][1] > 1e9  # mútua ≈ X_m/ω, X_m = 1e12 Ω


# ---------------------------------------------------------------------------
# Sanity física: Z_sc reconstruído
# ---------------------------------------------------------------------------


class TestPhysicalSanity:
    def test_z_sc_recovered_from_100mva_230_69(self):
        """Z_sc(100MVA) = 52.9 Ω @ 10% — deve ser recuperável."""
        data = _std_100mva_230_69()
        params = compute_bctran_parameters(data)
        # Z_sc visto dos terminais H = R1+R2 + j(X1+X2) onde X1+X2 = L11+L22-2*L12
        r_sc_eff = params.R[0][0] + params.R[1][1]
        x_sc_eff = (
            params.L[0][0] + params.L[1][1] - 2 * params.L[0][1]
        ) * 2 * math.pi * 60.0
        z_sc_eff = math.sqrt(r_sc_eff ** 2 + x_sc_eff ** 2)
        z_base = 230_000 ** 2 / 100e6
        z_sc_expected = 0.10 * z_base
        assert z_sc_eff == pytest.approx(z_sc_expected, rel=0.01)

    def test_r_sc_recovered_matches_p_sc(self):
        """R_sc total = p_sc / I_nom² — conservação de energia."""
        data = _std_100mva_230_69()
        params = compute_bctran_parameters(data)
        r_sc_eff = params.R[0][0] + params.R[1][1]
        i_nom = 100e6 / 230_000
        r_sc_expected = 400e3 / (i_nom ** 2)
        assert r_sc_eff == pytest.approx(r_sc_expected, rel=0.001)

    def test_distribution_trafo_z_sc(self):
        """Mesmo teste com distribuição 500 kVA."""
        data = _distribution_500kva()
        params = compute_bctran_parameters(data)
        r_sc_eff = params.R[0][0] + params.R[1][1]
        x_sc_eff = (
            params.L[0][0] + params.L[1][1] - 2 * params.L[0][1]
        ) * 2 * math.pi * 60.0
        z_sc_eff = math.sqrt(r_sc_eff ** 2 + x_sc_eff ** 2)
        z_base = 13_800 ** 2 / 500e3
        z_sc_expected = 0.05 * z_base
        assert z_sc_eff == pytest.approx(z_sc_expected, rel=0.01)


# ---------------------------------------------------------------------------
# Matrix structure
# ---------------------------------------------------------------------------


class TestMatrixStructure:
    def test_r_matrix_is_diagonal(self):
        """Com o algoritmo simétrico, [R] é diagonal (R1=R2=R_sc/2)."""
        data = _std_100mva_230_69()
        params = compute_bctran_parameters(data)
        assert params.R[0][1] == 0.0
        assert params.R[1][0] == 0.0
        # Diagonal deve ser simétrica (R1 = R2)
        assert params.R[0][0] == params.R[1][1]

    def test_l_matrix_is_symmetric(self):
        """[L] deve ser simétrica — mútua física."""
        data = _std_100mva_230_69()
        params = compute_bctran_parameters(data)
        assert params.L[0][1] == params.L[1][0]

    def test_is_symmetric_returns_true(self):
        """TransformerParameters.is_symmetric() helper."""
        data = _std_100mva_230_69()
        params = compute_bctran_parameters(data)
        assert params.is_symmetric() is True

    def test_L_self_greater_than_mutual(self):
        """L_self = L_mutua + L_dispersao > L_mutua — fisicamente exige."""
        data = _std_100mva_230_69()
        params = compute_bctran_parameters(data)
        assert params.L[0][0] > params.L[0][1]
        assert params.L[1][1] > params.L[1][0]


# ---------------------------------------------------------------------------
# Turns ratio
# ---------------------------------------------------------------------------


class TestTurnsRatio:
    def test_230_69_ratio(self):
        params = compute_bctran_parameters(_std_100mva_230_69())
        assert params.turns_ratio == pytest.approx(230 / 69, rel=1e-6)

    def test_step_up_ratio(self):
        """Trafo elevador 13.8/230 kV → turns_ratio < 1."""
        data = TransformerBCTRANData(
            v_h=13_800, v_l=230_000, s_nom=100e6,
            sc_test=TransformerSCTest(10.0, 400.0),
            oc_test=TransformerOCTest(0.5, 50.0),
        )
        params = compute_bctran_parameters(data)
        assert params.turns_ratio == pytest.approx(13.8 / 230, rel=1e-6)
        assert params.turns_ratio < 1.0


# ---------------------------------------------------------------------------
# ATP card emission
# ---------------------------------------------------------------------------


class TestAtpCardEmission:
    def test_emits_four_lines(self):
        """1 comment + 1 tipo-51 + 2 tipo-52 = 4 linhas."""
        params = compute_bctran_parameters(_std_100mva_230_69())
        cards = params.to_atp_cards("H1", "H2", "L1", "L2")
        assert len(cards) == 4
        # Linha 0 é um comentário ATP (começa com "C ")
        assert cards[0].startswith("C ")

    def test_first_branch_is_type_51(self):
        params = compute_bctran_parameters(_std_100mva_230_69())
        cards = params.to_atp_cards("H1", "H2", "L1", "L2")
        assert cards[1].startswith("51")

    def test_subsequent_branches_are_type_52(self):
        params = compute_bctran_parameters(_std_100mva_230_69())
        cards = params.to_atp_cards("H1", "H2", "L1", "L2")
        assert cards[2].startswith("52")
        assert cards[3].startswith("52")

    def test_nodes_in_output(self):
        params = compute_bctran_parameters(_std_100mva_230_69())
        cards = params.to_atp_cards("BUS_H", "GND", "BUS_L", "GND")
        joined = "\n".join(cards)
        assert "BUS_H" in joined
        assert "BUS_L" in joined


# ---------------------------------------------------------------------------
# Frequency scaling
# ---------------------------------------------------------------------------


class TestFrequencyScaling:
    def test_50hz_vs_60hz_inductance_scales(self):
        """Com mesmos dados de teste @ tensão nominal, a indutância
        em H é calculada a partir de X = ωL, onde ω = 2πf."""
        data_60 = _std_100mva_230_69()
        data_50 = TransformerBCTRANData(
            v_h=230_000, v_l=69_000, s_nom=100e6, frequency=50.0,
            sc_test=TransformerSCTest(10.0, 400.0),
            oc_test=TransformerOCTest(0.5, 50.0),
        )
        params_60 = compute_bctran_parameters(data_60)
        params_50 = compute_bctran_parameters(data_50)
        # L_50 / L_60 = 60/50 = 1.2 (mesma reatância X, ω menor → L maior)
        ratio = params_50.L[0][0] / params_60.L[0][0]
        assert ratio == pytest.approx(60.0 / 50.0, rel=1e-6)

    def test_r_independent_of_frequency(self):
        """Resistência é DC-like, não depende de f."""
        data_60 = _std_100mva_230_69()
        data_50 = TransformerBCTRANData(
            v_h=230_000, v_l=69_000, s_nom=100e6, frequency=50.0,
            sc_test=TransformerSCTest(10.0, 400.0),
            oc_test=TransformerOCTest(0.5, 50.0),
        )
        r_60 = compute_bctran_parameters(data_60).R[0][0]
        r_50 = compute_bctran_parameters(data_50).R[0][0]
        assert r_60 == pytest.approx(r_50, rel=1e-9)
