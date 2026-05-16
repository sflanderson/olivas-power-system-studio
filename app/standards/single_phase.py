"""
app/standards/single_phase.py — Single-phase Mid-Tap transformers + per-phase loads.

Implementa transformadores monofásicos split-phase (mid-tap) e cargas
per-phase conforme PTW Tutorial §Part 9 p. 247-252.

Aplicação típica brasileira: redes de distribuição rurais/comerciais
com transformador 1φ no poste — 13.8 kV → 240 V L-L → 120 V L-N
(cada metade), comum em USA e regiões rurais BR.

Reference
---------
PTW Tutorial §Part 9 p. 247-252 (Single-phase Mid-Tap Pole Mount TX).
ABNT NBR 5440 (Transformadores para redes aéreas de distribuição).
"""

from __future__ import annotations

from dataclasses import dataclass, field


def split_phase_secondary_voltages(v_primary_v: float) -> tuple[float, float, float]:
    """Compute split-phase secondary voltages from L-L primary.

    Per PTW Tutorial §Part 9 p. 247-250 (TX 1φ Mid-Tap 100 kVA 240V):
    o secundário tem dois enrolamentos em série com tap central:

    .. code::

        Phase A ----.       (V_AN = V_LL/2)
                    |---- Neutral
        Phase B ----'       (V_BN = V_LL/2)

    Tipicamente Phase A e Phase B estão em **oposição de fase** —
    a soma vetorial é V_LL = V_AN + V_BN (ambas referidas a Neutral).

    Parameters
    ----------
    v_primary_v
        Voltagem L-L do secundário, em Volts (e.g., 240, 480, 220, 220 etc.).

    Returns
    -------
    (v_an, v_bn, v_ll)
        Tupla com (V_Phase A−Neutral, V_Phase B−Neutral, V_L−L), em Volts.

    References
    ----------
    PTW Tutorial §Part 9 p. 247-250.
    ABNT NBR 5440.
    """
    if v_primary_v < 0:
        raise ValueError(
            f"v_primary_v must be ≥ 0; got {v_primary_v!r}"
        )
    v_half = v_primary_v / 2.0
    return (v_half, v_half, v_primary_v)


@dataclass
class PerPhaseLoad:
    """Per-phase current load (Phases A/B/C separately).

    Per PTW Tutorial §Part 9 p. 250 (LOAD-0002 100A only on Phase A):
    permite modelar cargas desbalanceadas onde a corrente em uma fase
    difere significativamente das outras.

    Útil para:
    * Análise de desbalanceio (cargas residenciais 1φ em sistemas 3φ)
    * Estudos SLG (Single-Line-to-Ground)
    * Sistemas split-phase 240/120V

    Attributes
    ----------
    phase_a_amps, phase_b_amps, phase_c_amps
        Corrente em cada fase, em Amperes (≥ 0).

    References
    ----------
    PTW Tutorial §Part 9 p. 250.
    """

    phase_a_amps: float
    phase_b_amps: float
    phase_c_amps: float

    def __post_init__(self) -> None:
        for name, val in (
            ("phase_a_amps", self.phase_a_amps),
            ("phase_b_amps", self.phase_b_amps),
            ("phase_c_amps", self.phase_c_amps),
        ):
            if val < 0:
                raise ValueError(f"{name} must be ≥ 0; got {val!r}")

    @property
    def total_amps(self) -> float:
        """Total current = soma das 3 fases."""
        return self.phase_a_amps + self.phase_b_amps + self.phase_c_amps

    @property
    def is_balanced(self) -> bool:
        """True iff Phase A ≈ Phase B ≈ Phase C (within 5% tolerance)."""
        avg = self.total_amps / 3.0
        if avg == 0.0:
            return True  # Vacuously balanced (no load)
        max_dev = max(
            abs(self.phase_a_amps - avg),
            abs(self.phase_b_amps - avg),
            abs(self.phase_c_amps - avg),
        )
        return max_dev / avg <= 0.05

    @property
    def unbalance_factor(self) -> float:
        """
        Unbalance factor ∈ [0, 1]:
        - 0 = perfeitamente balanceado (A=B=C)
        - 1 = totalmente desbalanceado (1 fase = total, outras = 0)

        Definição: max_phase_deviation_from_avg / max_phase.
        """
        max_phase = max(self.phase_a_amps, self.phase_b_amps, self.phase_c_amps)
        if max_phase == 0.0:
            return 0.0
        avg = self.total_amps / 3.0
        max_dev = max(
            abs(self.phase_a_amps - avg),
            abs(self.phase_b_amps - avg),
            abs(self.phase_c_amps - avg),
        )
        return max_dev / max_phase

    @classmethod
    def phase_only(cls, phase: str, amps: float) -> "PerPhaseLoad":
        """Construct a load that exists on a single phase only.

        Útil para modelar cargas 1φ em sistema 3φ.

        Parameters
        ----------
        phase
            ``"A"``, ``"B"``, or ``"C"`` (case-insensitive).
        amps
            Corrente nessa fase.

        Returns
        -------
        PerPhaseLoad
            Carga com apenas a fase especificada não-nula.
        """
        phase_upper = phase.upper()
        if phase_upper not in ("A", "B", "C"):
            raise ValueError(f"phase must be 'A', 'B', or 'C'; got {phase!r}")
        return cls(
            phase_a_amps=amps if phase_upper == "A" else 0.0,
            phase_b_amps=amps if phase_upper == "B" else 0.0,
            phase_c_amps=amps if phase_upper == "C" else 0.0,
        )


__all__ = [
    "split_phase_secondary_voltages",
    "PerPhaseLoad",
]
