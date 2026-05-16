"""
app.standards.iec60909_seq — componentes simétricas 0/1/2
para análise de faltas assimétricas conforme IEC 60909-0:2016
§4.3 e Stevenson §11.

Motivação
==========

A v0.28.0-PRO eleva o cálculo de SC do nível MVP (apenas
falta trifásica ``Ik3''``) para profissional, suportando:

* **Trifásica** (3φ) — IEC 60909-0 §4.3.1 (Ik''3).
* **Bifásica** (LL, fase-fase) — §4.3.2 (Ik''2).
* **Bifásica para terra** (LLG) — §4.3.3 (Ik''2EG).
* **Monofásica para terra** (LG, fase-terra) — §4.3.4
  (Ik''1).

Essa cobertura é CRÍTICA para:

* Coordenação de relés de **terra** (50N/51N/64) — pickup
  baseado em ``3·I0`` da falta LG.
* Dimensionamento de aterramento e malha de terra (TN/TT/IT).
* Estudo de NEUTRAL GROUNDING (Petersen coil, NGR).
* NBR 14039 §6.5 / NBR 5410 §6.4 — proteção contra contato
  indireto.

Equações de falta (positive-sequence reference V_th)
=====================================================

Para uma falta no bus de tensão Un (linha-linha) com
componentes simétricas Z_1, Z_2, Z_0 e tensão de pré-falta
V_th = c·Un/√3:

::

    Trifásica (3φ):
        I_k''3 = c·Un / (√3 · Z_1)

    Bifásica (LL):
        I_k''2 = c·Un / (Z_1 + Z_2)
                = (√3/2) · I_k''3   se Z_1 ≈ Z_2

    Monofásica (LG):
        I_k''1 = √3·c·Un / |Z_1 + Z_2 + Z_0|

    Bifásica-terra (LLG):
        I_k''2EG = √3·c·Un · |Z_2| / |Z_1·Z_2 + Z_2·Z_0 + Z_0·Z_1|
        (corrente em uma fase faltosa — corrente de terra é
         3·I_0 = √3·c·Un / |Z_2 + Z_0 + Z_1·Z_2/Z_0|)

Onde Z_1, Z_2, Z_0 são as impedâncias equivalentes vistas
do ponto de falta nas três sequências.

Tipo de aterramento
====================

* **TN-S/TN-C/TN-C-S**: neutro solidamente aterrado;
  Z_0 ≈ Z_1 (típico TR Yd ou Dy).
* **TT**: neutro aterrado via Re_N + terra remota; Z_0 grande.
* **IT (impedance-grounded)**: alta impedância de neutro;
  Z_0 muito grande, Ik''1 fica << Ik''3.
* **Resonant (Petersen)**: Z_0 imaginário ≈ X_C — quase nula
  corrente de terra em regime.

Limitações conhecidas
======================

* Esta entrega cobre **far-from-generator** (Ib = Ik = Ik'').
  Decay near-to-generator μ·q estará em v0.28.0-PRO P1.3.
* Modelagem de Petersen coil exige Z_0 puramente reativo;
  cubrimos genericamente (qualquer Z_0 complex).
* Para sistemas IT com derivação de neutro elevado, a
  fórmula LG fica limitada por capacitância de cabo (não
  modelada — refinamento futuro).

Referências
============

* IEC 60909-0:2016 §4.3.1 a §4.3.4 (cálculos das 4 faltas).
* IEC 60909-0:2016 §3.4-3.6 (definição Z_(0)/Z_(1)/Z_(2)).
* John J. Grainger, William D. Stevenson Jr., *Power System
  Analysis*, McGraw-Hill 1994 — §11 (Symmetrical Components).
* NBR 14039:2005 §6.5 (proteção contato indireto MT).
* NBR 5410:2008 §6.4 (proteção contato indireto BT).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class FaultType(str, Enum):
    """
    Tipos de falta cobertos pela IEC 60909-0 §4.3.

    * THREE_PHASE: trifásica (Ik''3) — máxima do sistema.
    * LINE_TO_LINE: bifásica (Ik''2).
    * LINE_TO_GROUND: monofásica fase-terra (Ik''1).
    * DOUBLE_LINE_TO_GROUND: bifásica-terra (Ik''2EG).
    """
    THREE_PHASE = "three_phase"          # 3φ
    LINE_TO_LINE = "line_to_line"        # LL
    LINE_TO_GROUND = "line_to_ground"    # LG
    DOUBLE_LINE_TO_GROUND = "double_line_to_ground"  # LLG


class GroundingType(str, Enum):
    """
    Tipo de aterramento do sistema (afeta Z_0 default).

    * SOLIDLY_GROUNDED: TN-S, TN-C, TN-C-S; Z_0 ≈ Z_1.
    * RESISTANCE_GROUNDED: TT com R_N; Z_0 = Z_1 + 3·R_N.
    * IMPEDANCE_GROUNDED: IT alta impedância; Z_0 grande.
    * UNGROUNDED: rede isolada; Z_0 → ∞ (capacitivo).
    * RESONANT_GROUNDED: Petersen coil; Z_0 = -j·1/(3ωC).
    """
    SOLIDLY_GROUNDED = "solid"
    RESISTANCE_GROUNDED = "resistance"
    IMPEDANCE_GROUNDED = "impedance"
    UNGROUNDED = "ungrounded"
    RESONANT_GROUNDED = "resonant"


# ---------------------------------------------------------------------------
# SequenceImpedances
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SequenceImpedances:
    """
    Impedâncias equivalentes 0/1/2 vistas do ponto de falta.

    Attributes
    ----------
    Z1:
        Sequência positiva (R_1 + jX_1) em ohms.
    Z2:
        Sequência negativa (R_2 + jX_2). Para máquinas
        rotativas, Z_2 ≈ Z_1; para componentes passivos
        (linhas, TR), Z_2 = Z_1 estritamente.
    Z0:
        Sequência zero (R_0 + jX_0). Depende muito do tipo
        de aterramento e de conexão dos transformadores
        (Y-Δ / Δ-Y bloqueia Z_0).
    """
    Z1: complex
    Z2: complex
    Z0: complex

    def __post_init__(self):
        if abs(self.Z1) <= 0:
            raise ValueError(f"Z1 deve ter módulo > 0 (achado {self.Z1})")
        if abs(self.Z2) <= 0:
            raise ValueError(f"Z2 deve ter módulo > 0 (achado {self.Z2})")
        # Z0 pode ser muito grande mas não zero
        if abs(self.Z0) <= 0:
            raise ValueError(f"Z0 deve ter módulo > 0 (achado {self.Z0})")


# ---------------------------------------------------------------------------
# Construtores
# ---------------------------------------------------------------------------


def sequence_impedances_from_grounding(
    Z1: complex,
    grounding: GroundingType,
    *,
    R_N_ohm: float = 0.0,
    Z0_override: complex | None = None,
) -> SequenceImpedances:
    """
    Helper: dado Z_1 e o tipo de aterramento, infere Z_0
    (Z_2 = Z_1 por default).

    Parameters
    ----------
    Z1:
        Impedância de sequência positiva (Thevenin no ponto
        de falta).
    grounding:
        Tipo de aterramento do sistema.
    R_N_ohm:
        Resistência de neutro (apenas RESISTANCE_GROUNDED).
    Z0_override:
        Se fornecido, usa esse valor para Z_0 (override total).

    Returns
    -------
    SequenceImpedances
    """
    Z2 = Z1   # padrão para componentes passivos
    if Z0_override is not None:
        return SequenceImpedances(Z1=Z1, Z2=Z2, Z0=Z0_override)

    if grounding == GroundingType.SOLIDLY_GROUNDED:
        # TN solidamente aterrado: Z_0 ≈ Z_1 (heurística para TR Yn)
        Z0 = Z1
    elif grounding == GroundingType.RESISTANCE_GROUNDED:
        # TT/TN com resistor de neutro: Z_0 = Z_1 + 3·R_N
        Z0 = Z1 + complex(3.0 * R_N_ohm, 0.0)
    elif grounding == GroundingType.IMPEDANCE_GROUNDED:
        # IT alta impedância — heurística: Z_0 = 100·Z_1
        Z0 = Z1 * 100.0
    elif grounding == GroundingType.UNGROUNDED:
        # Z_0 → ∞ (capacitivo); usa valor muito grande
        Z0 = complex(1e9, 1e9)
    elif grounding == GroundingType.RESONANT_GROUNDED:
        # Petersen: Z_0 puramente reativo grande (cancela cap)
        Z0 = complex(0.0, abs(Z1) * 50.0)
    else:
        raise ValueError(f"grounding desconhecido: {grounding}")

    return SequenceImpedances(Z1=Z1, Z2=Z2, Z0=Z0)


# ---------------------------------------------------------------------------
# Cálculos das 4 faltas
# ---------------------------------------------------------------------------


def three_phase_fault_kA(
    Un_kV: float, Z1: complex, voltage_factor_c: float = 1.10,
) -> float:
    """
    Falta trifásica simétrica — IEC 60909-0 §4.3.1:

    ::

        I_k''3 = c · Un / (√3 · |Z_1|)

    Returns
    -------
    float
        Ik''3 em kA (RMS, simétrica).
    """
    if Un_kV <= 0:
        raise ValueError(f"Un_kV deve ser > 0 (achado {Un_kV})")
    if abs(Z1) <= 0:
        raise ValueError(f"|Z1| deve ser > 0 (achado {Z1})")
    if voltage_factor_c <= 0:
        raise ValueError(
            f"voltage_factor_c deve ser > 0 (achado {voltage_factor_c})"
        )
    return voltage_factor_c * Un_kV / (math.sqrt(3.0) * abs(Z1))


def line_to_line_fault_kA(
    Un_kV: float, Z1: complex, Z2: complex,
    voltage_factor_c: float = 1.10,
) -> float:
    """
    Falta bifásica (fase-fase, sem terra) — IEC 60909-0 §4.3.2:

    ::

        I_k''2 = c · Un / |Z_1 + Z_2|

    Para Z_1 = Z_2 (típico componentes passivos):

    ::

        I_k''2 = (√3/2) · I_k''3 ≈ 0.866 · I_k''3

    Returns
    -------
    float
        Ik''2 em kA (RMS).
    """
    if Un_kV <= 0:
        raise ValueError(f"Un_kV deve ser > 0 (achado {Un_kV})")
    if abs(Z1 + Z2) <= 0:
        raise ValueError(f"|Z1 + Z2| deve ser > 0")
    return voltage_factor_c * Un_kV / abs(Z1 + Z2)


def line_to_ground_fault_kA(
    Un_kV: float, Z1: complex, Z2: complex, Z0: complex,
    voltage_factor_c: float = 1.10,
) -> float:
    """
    Falta monofásica fase-terra — IEC 60909-0 §4.3.4:

    ::

        I_k''1 = √3 · c · Un / |Z_1 + Z_2 + Z_0|

    Esta é a corrente NA FASE faltosa. A corrente de terra
    (que sensibiliza relés 50N/51N) é a mesma I_k''1.

    Para sistema isolado (UNGROUNDED): Z_0 → ∞ → I_k''1 → 0
    (apenas circulação capacitiva, não modelada aqui).

    Returns
    -------
    float
        Ik''1 em kA (RMS, na fase faltosa).
    """
    if Un_kV <= 0:
        raise ValueError(f"Un_kV deve ser > 0 (achado {Un_kV})")
    z_sum = Z1 + Z2 + Z0
    if abs(z_sum) <= 0:
        raise ValueError(f"|Z1+Z2+Z0| deve ser > 0")
    return math.sqrt(3.0) * voltage_factor_c * Un_kV / abs(z_sum)


def double_line_to_ground_fault_kA(
    Un_kV: float, Z1: complex, Z2: complex, Z0: complex,
    voltage_factor_c: float = 1.10,
) -> tuple[float, float]:
    """
    Falta bifásica-terra (LLG) — IEC 60909-0 §4.3.3.

    Returns
    -------
    tuple[float, float]
        (Ik''2EG_phase, I_ground), em kA.

        * ``Ik''2EG_phase`` — corrente em UMA das duas fases
          faltosas:

          ::

              I_k''2EG = √3 · c · Un · |Z_2|
                       / |Z_1 · Z_2 + Z_2 · Z_0 + Z_0 · Z_1|

        * ``I_ground`` = 3·I_0 — corrente de terra que retorna
          pelo neutro/aterramento:

          ::

              3·I_0 = √3 · c · Un / |Z_1 + Z_0 · (Z_1+Z_2)/Z_2|

    Notas
    -----
    Para Z_0 → ∞ (sistema isolado), Ik''2EG → Ik''2 (falta LL
    pura, sem componente de terra).
    """
    if Un_kV <= 0:
        raise ValueError(f"Un_kV deve ser > 0 (achado {Un_kV})")
    denom_phase = Z1 * Z2 + Z2 * Z0 + Z0 * Z1
    if abs(denom_phase) <= 0:
        raise ValueError("denominador phase = 0")
    I_phase = (
        math.sqrt(3.0) * voltage_factor_c * Un_kV * abs(Z2) / abs(denom_phase)
    )

    # Corrente de terra (3·I_0): considera divisor de tensão
    # do circuito sequencial em Y conectado.
    if abs(Z2) <= 0:
        raise ValueError("|Z2| = 0")
    z_eq = Z1 + Z0 * (Z1 + Z2) / Z2
    if abs(z_eq) <= 0:
        raise ValueError("|Z_eq| = 0")
    I_ground = math.sqrt(3.0) * voltage_factor_c * Un_kV / abs(z_eq)

    return I_phase, I_ground


# ---------------------------------------------------------------------------
# Wrapper consolidado
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AsymmetricFaultResult:
    """
    Resultado consolidado das 4 faltas no mesmo bus.

    Attributes
    ----------
    Un_kV:
        Tensão nominal (linha-linha).
    voltage_factor_c:
        c usado.
    seq_impedances:
        Z_0/Z_1/Z_2.
    Ik3_kA:
        Trifásica.
    Ik2_kA:
        Bifásica (LL).
    Ik1_kA:
        Monofásica fase-terra.
    Ik2EG_phase_kA / Ik2EG_ground_kA:
        Bifásica-terra (corrente da fase / da terra).
    grounding:
        Tipo de aterramento usado.
    """
    Un_kV: float
    voltage_factor_c: float
    seq_impedances: SequenceImpedances
    Ik3_kA: float
    Ik2_kA: float
    Ik1_kA: float
    Ik2EG_phase_kA: float
    Ik2EG_ground_kA: float
    grounding: GroundingType

    @property
    def maximum_fault_kA(self) -> float:
        """Maior das 4 — geralmente Ik3 mas em ungrounded pode variar."""
        return max(
            self.Ik3_kA, self.Ik2_kA, self.Ik1_kA, self.Ik2EG_phase_kA,
        )

    @property
    def Ik1_to_Ik3_ratio(self) -> float:
        """
        Razão Ik''1/Ik''3 — diagnóstico de tipo de
        aterramento:

        * ≈ 1.0 → solidamente aterrado (TN).
        * ≈ 0.5 → resistance ou impedance grounded.
        * → 0   → ungrounded ou Petersen.
        """
        if self.Ik3_kA <= 0:
            # v0.92.2: log o fallback (auditabilidade)
            from app.core.logging_config import get_logger
            log = get_logger(__name__)
            log.warning(
                "Ik3=%.3f kA <= 0 em sistema %.2f kV; razão Ik1/Ik3 "
                "indefinida. Fallback retorna 0.0. Verifique se há "
                "fonte trifásica conectada.",
                self.Ik3_kA, self.Un_kV,
            )
            return 0.0
        return self.Ik1_kA / self.Ik3_kA

    def summary(self) -> str:
        """Texto humano-readable das 4 correntes."""
        ratio = self.Ik1_to_Ik3_ratio
        return (
            f"=== IEC 60909-0 §4.3 — Faltas Assimétricas "
            f"(Un = {self.Un_kV:.2f} kV, c = {self.voltage_factor_c:.2f}) ===\n"
            f"Aterramento: {self.grounding.value}\n"
            f"Z_0 = {self.seq_impedances.Z0.real:+.4f} + "
            f"j{self.seq_impedances.Z0.imag:+.4f} Ω, "
            f"Z_1 = {self.seq_impedances.Z1.real:+.4f} + "
            f"j{self.seq_impedances.Z1.imag:+.4f} Ω, "
            f"Z_2 = {self.seq_impedances.Z2.real:+.4f} + "
            f"j{self.seq_impedances.Z2.imag:+.4f} Ω\n"
            f"\n"
            f"Trifásica (3φ):       I_k''3   = {self.Ik3_kA:8.3f} kA\n"
            f"Bifásica (LL):        I_k''2   = {self.Ik2_kA:8.3f} kA\n"
            f"Mono-terra (LG):      I_k''1   = {self.Ik1_kA:8.3f} kA\n"
            f"Bif-terra (LLG fase): I_k''2EG = {self.Ik2EG_phase_kA:8.3f} kA\n"
            f"Bif-terra (LLG terra): 3·I_0   = "
            f"{self.Ik2EG_ground_kA:8.3f} kA\n"
            f"\n"
            f"Razão I_k''1 / I_k''3 = {ratio:.3f}\n"
            f"Máxima falta:        {self.maximum_fault_kA:.3f} kA"
        )


def calculate_all_faults(
    Un_kV: float,
    seq_impedances: SequenceImpedances,
    grounding: GroundingType = GroundingType.SOLIDLY_GROUNDED,
    voltage_factor_c: float = 1.10,
) -> AsymmetricFaultResult:
    """
    Wrapper: dado Un + impedâncias 0/1/2 + tipo de aterramento,
    calcula todas as 4 faltas IEC 60909-0 §4.3.

    Parameters
    ----------
    Un_kV:
        Tensão nominal linha-linha.
    seq_impedances:
        Z_0/Z_1/Z_2 vistas do ponto de falta.
    grounding:
        Tipo de aterramento (informativo no relatório).
    voltage_factor_c:
        c IEC 60909-0 (1.10 default para HV/MV max).

    Returns
    -------
    AsymmetricFaultResult
    """
    Z1, Z2, Z0 = (
        seq_impedances.Z1, seq_impedances.Z2, seq_impedances.Z0,
    )
    Ik3 = three_phase_fault_kA(Un_kV, Z1, voltage_factor_c)
    Ik2 = line_to_line_fault_kA(Un_kV, Z1, Z2, voltage_factor_c)
    Ik1 = line_to_ground_fault_kA(Un_kV, Z1, Z2, Z0, voltage_factor_c)
    Ik2EG_phase, Ik2EG_ground = double_line_to_ground_fault_kA(
        Un_kV, Z1, Z2, Z0, voltage_factor_c,
    )
    return AsymmetricFaultResult(
        Un_kV=Un_kV,
        voltage_factor_c=voltage_factor_c,
        seq_impedances=seq_impedances,
        Ik3_kA=Ik3,
        Ik2_kA=Ik2,
        Ik1_kA=Ik1,
        Ik2EG_phase_kA=Ik2EG_phase,
        Ik2EG_ground_kA=Ik2EG_ground,
        grounding=grounding,
    )
