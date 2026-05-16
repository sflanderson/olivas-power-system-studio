"""
app/standards/transformer_tap.py — Transformer Tap modeling.

Implements PTW Reference-A_Fault.pdf §1.4.2 p. 1-31/32/33 (Modeling
Transformers with Taps) — primary tap adjustment of secondary voltage.

Aplicação: ANSI Comprehensive Short Circuit com transformadores cujos
taps primários estão fora do nominal (ajuste fino de relação).

Cenário típico:
* TAPS YES — usar tap ratio efetivo (V_secondary aumentada/diminuída)
* TAPS NO  — ignorar taps (assumir nominal)

Manual A_Fault demonstra (§1.4.2):
* Tap = -2.5% no primário → V_no-load_secondary = 1/(1-0.025) = 1.0256 pu
* B4 fault: TAPS YES = 19.772 kA vs TAPS NO = 19.360 kA
* SLG vs 3-φ em delta-wye-grounded: 36.864 vs 34.795 kA (SLG > 3-φ)

Reference
---------
PTW Reference-A_Fault.pdf §1.4.2 p. 1-31/32/33.
ANSI/IEEE C57.12 (transformer standard).
NEMA TR-1 (5-step taps standard).
"""

from __future__ import annotations

from dataclasses import dataclass, field


# NEMA standard 5-step tap percentages (TR-1).
STANDARD_NEMA_TAPS: tuple[float, ...] = (-5.0, -2.5, 0.0, +2.5, +5.0)


@dataclass
class TransformerTap:
    """Transformer primary-side tap configuration.

    Per ANSI C57.12 + NEMA TR-1: o tap primário ajusta a relação efetiva
    do transformador. Tap negativo (e.g., -2.5%) significa que o
    enrolamento primário está com 2.5% **menos espiras** efetivas → a
    relação N1/N2 diminui → V_secondary **aumenta** para mesma V_primary.

    .. math::
        V_{sec,no\\_load} = \\frac{V_{pri}}{1 + \\frac{tap\\%}{100}}

    Para tap = -2.5%: V_sec = V_pri / 0.975 = V_pri × 1.0256

    Attributes
    ----------
    tap_percent
        Tap setting em porcentagem do nominal. Range típico ±5%.
        Negativo = mais V_secondary; positivo = menos V_secondary.

    References
    ----------
    PTW Reference-A_Fault.pdf §1.4.2 p. 1-31.
    ANSI C57.12.
    """

    tap_percent: float = 0.0

    def __post_init__(self) -> None:
        # Tap = ±100% causa V_secondary = ±∞ (divisão por zero ou negativo)
        if self.tap_percent <= -100.0 or self.tap_percent >= 100.0:
            raise ValueError(
                f"tap_percent must be in (-100, +100); got {self.tap_percent!r}"
            )

    def no_load_secondary_voltage_pu(self, v_primary_pu: float = 1.0) -> float:
        """Compute V_secondary at no-load, in pu.

        Per §1.4.2 p. 1-31: ``V_sec = V_pri / (1 + tap%/100)``.

        Parameters
        ----------
        v_primary_pu
            Voltagem aplicada no primário (default 1.0 pu = nominal).

        Returns
        -------
        float
            Voltagem efetiva no secundário sem carga, em pu.

        References
        ----------
        PTW A_Fault §1.4.2 p. 1-31.
        """
        if v_primary_pu < 0:
            raise ValueError(
                f"v_primary_pu must be ≥ 0; got {v_primary_pu!r}"
            )
        return v_primary_pu / (1.0 + self.tap_percent / 100.0)

    @classmethod
    def from_nema_step(cls, step: int) -> "TransformerTap":
        """Construct from NEMA 5-step index.

        Step convention: -2 → -5%, -1 → -2.5%, 0 → 0%, +1 → +2.5%, +2 → +5%.

        References
        ----------
        NEMA TR-1.
        """
        if not -2 <= step <= 2:
            raise ValueError(
                f"NEMA step must be in [-2, 2]; got {step!r}"
            )
        return cls(tap_percent=STANDARD_NEMA_TAPS[step + 2])


def voltage_with_tap(
    v_nominal_pu: float,
    tap_percent: float,
) -> float:
    """Compute effective pre-fault voltage given a transformer tap setting.

    Convenience wrapper for :class:`TransformerTap.no_load_secondary_voltage_pu`.

    Per §1.4.2 p. 1-31: para TAPS YES scenario com tap = -2.5%,
    V_eff = V_nominal / 0.975 = 1.0256 × V_nominal.

    Parameters
    ----------
    v_nominal_pu
        Voltagem nominal pre-fault, pu.
    tap_percent
        Tap em %. Default 0% = TAPS NO (ignorar tap).

    Returns
    -------
    float
        Voltagem efetiva pré-falta, pu.

    References
    ----------
    PTW A_Fault §1.4.2 p. 1-31.
    """
    return TransformerTap(tap_percent=tap_percent).no_load_secondary_voltage_pu(
        v_primary_pu=v_nominal_pu
    )


def slg_vs_3ph_ratio(z0_over_z1: float) -> float:
    """Compute the ratio I_SLG / I_3ph at a fault bus.

    Per Symmetrical Components Theory (Stevenson, Ch. 12) e PTW A_Fault
    §1.4.2 p. 1-33:

    .. math::
        \\frac{I_{SLG}}{I_{3\\phi}} = \\frac{3}{1 + (Z_2/Z_1) + (Z_0/Z_1)}
        \\approx \\frac{3}{2 + Z_0/Z_1} \\quad \\text{(para } Z_2 \\approx Z_1 \\text{)}

    Em delta-wye-grounded próximo do TX, Z0 pode ser BAIXO (caminho de
    retorno direto via neutro), e o fator 3 no numerador domina,
    resultando em I_SLG > I_3ph (paradox aparente, mas físicamente correto).

    Manual A_Fault §1.4.2 p. 1-33 demonstra: I_3ph=34.795 kA vs I_SLG=36.864 kA
    em B3 (delta-wye-grounded TX próximo) — ratio ≈ 1.0594 → Z0/Z1 ≈ 0.83.

    Parameters
    ----------
    z0_over_z1
        Ratio Z0 (zero seq) / Z1 (positive seq), assumindo Z2 ≈ Z1.
        Típico: 0.5-1.0 (delta-wye-grounded), 1.0 (sólidamente aterrado
        simétrico), 5-100 (alta-impedância grounded ou isolado).

    Returns
    -------
    float
        I_SLG / I_3ph ratio.

    References
    ----------
    PTW A_Fault §1.4.2 p. 1-33.
    Stevenson, "Elements of Power System Analysis", Ch. 12.
    IEEE Std 142 (Green Book) §1.5 (system grounding).
    """
    if z0_over_z1 < 0:
        raise ValueError(
            f"z0_over_z1 must be ≥ 0; got {z0_over_z1!r}"
        )
    # Assuming Z2 ≈ Z1 (typical for transformers / cables):
    return 3.0 / (1.0 + 1.0 + z0_over_z1)


__all__ = [
    "TransformerTap",
    "STANDARD_NEMA_TAPS",
    "voltage_with_tap",
    "slg_vs_3ph_ratio",
]
