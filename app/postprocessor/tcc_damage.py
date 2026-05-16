"""
app.postprocessor.tcc_damage — Damage curves para coordenação
de proteção (v1.2.0 Fase γ).

Filosofia
==========

Em coordenação real (IEEE 242 §15), as curvas de **proteção**
(51, 50, 49, 87) precisam estar **abaixo** das curvas de
**damage** dos equipamentos protegidos. Damage curves são:

* **Cable damage** — limite térmico do isolamento. Acima
  desta curva, o cabo derrete (NBR 5410 §6.5.4).
* **Transformer through-fault** — stress térmico/mecânico
  acumulado em faltas que passam pelo XFMR
  (IEEE C57.109-1993).
* **Motor thermal limit** — locked rotor heating curve
  (IEC 60079-7 / NEMA MG-1).

Este módulo expõe 3 dataclasses de damage curve. Cada uma
implementa ``damage_time_at_current(I)`` retornando o tempo
até o equipamento sofrer dano permanente. Plot conjunto com
curvas de proteção mostra **violations** (cruzamentos).

Compatibilidade
================

Módulo paralelo a:

* ``tcc_segments.py`` (Fase α — protection segments)
* ``tcc_devices.py`` (Fase β — protection devices)
* ``tcc_curves.py`` (legacy v1.1.0)

Damage curves NÃO são TCCSegments — são limites a evitar,
não funções ativas. Se necessário compor com TCCSegments
no plot, é responsabilidade do consumer (Fase δ).

Cobertura normativa
====================

* NBR 5410:2004 §6.5.4 (cable thermal stress, K factors)
* IEEE Std C57.109-1993 (transformer through-fault duration)
* IEC 60079-7:2017 (motor locked rotor time tE)
* NEMA MG-1 §12.45 (motor thermal limit)
* IEEE 242:2001 §15 (coordination com damage curves)
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum


# ---------------------------------------------------------------------------
# γ.1 — Cable damage curve (NBR 5410 §6.5.4 / IEC 60364-4-43)
# ---------------------------------------------------------------------------


class CableMaterial(str, Enum):
    """
    Material conductor + isolação.

    K factors (NBR 5410 Tabela 43, IEC 60364-4-43 Tabela A.54.2):

    * **Cu/PVC ≤300 mm²**: K = 115
    * **Cu/PVC >300 mm²**: K = 103 (já não é mais usado em new
      installations mas legacy)
    * **Cu/EPR ou XLPE**: K = 143
    * **Al/PVC**: K = 76
    * **Al/EPR ou XLPE**: K = 94

    Cu/PVC tem 2 valores conforme bitola — separamos via
    enum para clareza, mas a classe ``CableDamageCurve``
    selecciona automaticamente baseado em ``section_mm2``.
    """

    Cu_PVC = "Cu/PVC"
    Cu_XLPE = "Cu/XLPE"
    Cu_EPR = "Cu/EPR"
    Al_PVC = "Al/PVC"
    Al_XLPE = "Al/XLPE"
    Al_EPR = "Al/EPR"


# K factors da NBR 5410 Tabela 43.
# Fonte: ABNT NBR 5410:2004 (cobre + alumínio com PVC ou XLPE/EPR).
# Equivalência IEC 60364-4-43 Tabela A.54.2.
# Cu/PVC tem 2 valores: 115 para ≤300mm², 103 para >300mm².
# A função ``_K_factor`` faz o lookup correto.
_K_BASE: dict[CableMaterial, float] = {
    CableMaterial.Cu_PVC: 115.0,    # ≤300 mm² (>300mm² = 103)
    CableMaterial.Cu_XLPE: 143.0,
    CableMaterial.Cu_EPR: 143.0,    # mesmo K que XLPE
    CableMaterial.Al_PVC: 76.0,
    CableMaterial.Al_XLPE: 94.0,
    CableMaterial.Al_EPR: 94.0,
}


def _K_factor(material: CableMaterial, section_mm2: float) -> float:
    """
    Lookup do K factor da NBR 5410 §6.5.4 conforme material e
    bitola. Cu/PVC reduz de 115 para 103 acima de 300 mm².

    Returns
    -------
    float
        K em (A·s^0.5 / mm²).
    """
    if material == CableMaterial.Cu_PVC and section_mm2 > 300.0:
        return 103.0
    return _K_BASE[material]


@dataclass(frozen=True)
class CableDamageCurve:
    """
    Curva de damage (limite térmico) de um cabo, conforme
    NBR 5410 §6.5.4 / IEC 60364-4-43.

    Fórmula
    --------

    ::

        t_damage(I) = (K · S)² / I²

    onde:

    * ``K`` (A·s^0.5/mm²) — constante da Tabela 43 NBR 5410
      (depende de material conductor + isolação)
    * ``S`` (mm²) — seção do condutor
    * ``I`` (A) — corrente de falta

    Para coordenação correta (IEEE 242 §15.6.3), a curva de
    proteção 51/50 do upstream DEVE estar abaixo desta
    damage curve em todo o range de I até o ``Iccs`` do bus.

    Convenção
    ----------

    Damage curve é definida para qualquer I > 0; não há
    pickup explícito — a curva começa em ``i_min_A``
    (default 0.1 × Inom_cable, ajustável via param).

    Para I ≤ ``i_min_A``: ``time = inf`` (não-relevante para
    coordenação prática).

    Attributes
    ----------

    cable_id:
        Identificador (ex: "C-MAIN-50mm2", "Feeder F1").
    section_mm2:
        Seção (mm²). Bitolas comuns NBR 5410: 1.5, 2.5, 4, 6,
        10, 16, 25, 35, 50, 70, 95, 120, 150, 185, 240, 300.
    material:
        Material + isolação (vide ``CableMaterial``).
    i_min_A:
        Limite inferior do range válido (default 1.0 A).
        Abaixo retorna ``inf``. Não confundir com pickup.
    enabled:
        Se False, ``damage_time_at_current`` retorna ``inf``.

    Cobertura
    ----------

    * NBR 5410:2004 §6.5.4 (cable thermal stress)
    * IEC 60364-4-43 Tabela A.54.2 (equivalente internacional)
    * IEEE 242:2001 §15.6.3 (coordination com cable damage)
    """

    cable_id: str
    section_mm2: float
    material: CableMaterial
    i_min_A: float = 1.0
    enabled: bool = True

    def __post_init__(self) -> None:
        if self.section_mm2 <= 0:
            raise ValueError(
                f"section_mm2 deve ser > 0, recebido {self.section_mm2}"
            )
        if self.i_min_A <= 0:
            raise ValueError(
                f"i_min_A deve ser > 0, recebido {self.i_min_A}"
            )

    def K_factor(self) -> float:
        """K factor desta combinação material + bitola (NBR Tabela 43)."""
        return _K_factor(self.material, self.section_mm2)

    def damage_time_at_current(self, current_A: float) -> float:
        """
        Tempo até damage térmico para corrente I.

        Fórmula NBR 5410 §6.5.4: ``t = (K·S)² / I²``.

        Returns
        -------
        float
            Tempo em segundos. ``inf`` se I ≤ i_min_A ou disabled.
        """
        if not self.enabled:
            return float("inf")
        if current_A <= self.i_min_A:
            return float("inf")
        if current_A <= 0:
            return float("inf")
        K = self.K_factor()
        K_S = K * self.section_mm2
        return (K_S ** 2) / (current_A ** 2)

    def damage_points(
        self,
        i_min_A: float = 10.0,
        i_max_A: float = 1e5,
        n_points: int = 100,
    ) -> list[tuple[float, float]]:
        """
        Pontos (I, t) para plot log-log da damage curve.

        Restringe ao range ``[max(i_min_A, self.i_min_A), i_max_A]``.
        """
        eff_min = max(i_min_A, self.i_min_A * 1.001)
        if eff_min <= 0 or i_max_A <= eff_min or n_points < 2:
            return []
        log_min = math.log10(eff_min)
        log_max = math.log10(i_max_A)
        step = (log_max - log_min) / (n_points - 1)
        pts: list[tuple[float, float]] = []
        for i in range(n_points):
            I = 10 ** (log_min + i * step)
            t = self.damage_time_at_current(I)
            if math.isfinite(t):
                pts.append((I, t))
        return pts


# ---------------------------------------------------------------------------
# γ.2 — Transformer through-fault curve (IEEE C57.109 / IEEE 242 §11.5.6)
# ---------------------------------------------------------------------------


class XfmrFaultCategory(str, Enum):
    """
    Categoria de transformador para through-fault analysis.

    Conforme IEEE C57.109-1993 §4 (Fault Frequency Categories):

    * **FREQUENT** — small/medium dry-type & liquid-immersed
      transformers em sistemas com faltas frequentes (urban
      distribution, ramais com proteção limitada). Curva
      mais conservadora.
    * **INFREQUENT** — large transformers protegidos por
      relés rápidos + breakers em sistemas onde faltas são
      raras (subestações grandes, geração). Curva mais
      tolerante (mais energia até damage).

    A escolha entre FREQUENT e INFREQUENT depende de:

    * Tamanho do transformador (Cat I/II = frequent default)
    * Tipo de proteção upstream (relé numérico + breaker
      rápido permite uso da curva infrequent)
    * Filosofia da concessionária

    Para análise conservadora, sempre usar FREQUENT.
    """

    FREQUENT = "Frequent fault duty"
    INFREQUENT = "Infrequent fault duty"


# Constantes K para t = K / (I/In)², conforme
# IEEE Std 242-2001 (Buff Book) §11.5.6:
# "For the frequent-fault region, the I²t curve corresponds
# to a value of K = 1250 (where I is in per unit of nameplate
# full-load current and t is in seconds). For the
# infrequent-fault region, K = 5000."
_K_THROUGH_FAULT: dict[XfmrFaultCategory, float] = {
    XfmrFaultCategory.FREQUENT: 1250.0,
    XfmrFaultCategory.INFREQUENT: 5000.0,
}

# Mechanical floor do t (IEEE C57.109 §5):
# Para I_pu acima do threshold (sqrt(K/2)), o XFMR aguenta NO
# MÍNIMO 2 s antes de damage mecânico (forças de pico). A curva
# se "achata" em t=2s para high I (não desce abaixo disso por
# mais que I cresça). Em low I (I_pu ≤ sqrt(K/2)) a curva
# térmica I²t domina (t > 2s).
#
# Logo: damage_time = MAX(t_thermal, MECH_FLOOR), não MIN.
# Pictoricamente no log-log: a curva tem 2 segments —
# ramo térmico inverso para I baixos, ramo horizontal em 2s
# para I altos.
_T_MECHANICAL_FLOOR_S = 2.0


@dataclass(frozen=True)
class TransformerThroughFaultCurve:
    """
    Curva through-fault de um transformador, IEEE C57.109-1993
    + IEEE Std 242-2001 §11.5.6.

    Modelagem
    ----------

    Curva IEEE C57.109 em 2 segments:

    ::

        t(I) = MAX(K / (I/In)², T_mech_floor_s)    para I > In

    onde:

    * ``K`` (s) — constante categoria (1250 frequent / 5000 infrequent)
    * ``In`` — corrente nominal do transformador (A)
    * ``T_mech_floor`` = 2.0 s (piso mecânico em high I)

    Threshold I_pu onde a curva muda de regime:

    ::

        I_pu_thresh = sqrt(K / T_mech_floor)
                    = sqrt(1250/2) ≈ 25  (frequent)
                    = sqrt(5000/2) ≈ 50  (infrequent)

    Em I_pu ≤ thresh: regime térmico I²t domina (t > 2s).
    Em I_pu > thresh: piso mecânico aplica (t = 2s constante).

    Para coordenação correta (IEEE 242 §15.6.4), a curva de
    proteção upstream do XFMR DEVE estar abaixo desta damage
    curve em todo o range de I até o ``Iccs`` do bus primário.

    Convenção
    ----------

    * Para ``I ≤ In``: ``time = inf`` (não-damage).
    * Para ``I > In``: ``time = MAX(K / (I/In)², 2s)``.

    Attributes
    ----------

    xfmr_id:
        Identificador (ex: "XFMR-MAIN", "T1-13.8/0.48 kV").
    rated_current_A:
        Corrente nominal full-load (In) em A. Para transformador
        2000 kVA / 13.8 kV: In = 2000/(√3·13.8) = 83.7 A.
    category:
        ``FREQUENT`` (K=1250) ou ``INFREQUENT`` (K=5000).
    enabled:
        Se False, ``through_fault_time_at_current`` retorna inf.

    Cobertura normativa
    --------------------

    * IEEE Std C57.109-1993 — Through-Fault Duration Guide
    * IEEE Std 242-2001 (Buff Book) §11.5.6 — K factors 1250/5000
    * IEEE Std 242-2001 §15.6.4 — coordination com XFMR damage
    * NBR 5356 — transformadores de potência (BR equivalente)

    Limitações documentadas
    ------------------------

    * Não modela inrush de magnetização (~8-12× In, t<0.1s).
      Usar ``TCCSegmentTimeCurrentPoints`` para inrush
      personalizado.
    * Não modela delta-Y phase shift em through-faults
      assimétricos (LL/SLG dão currents diferentes do 3φ).
      Esta classe assume worst-case 3φ.
    * Para precisão de datasheet específico, usar
      ``TCCSegmentTimeCurrentPoints`` com Tabela 1 do manual
      do fabricante.
    """

    xfmr_id: str
    rated_current_A: float
    category: XfmrFaultCategory
    enabled: bool = True

    def __post_init__(self) -> None:
        if self.rated_current_A <= 0:
            raise ValueError(
                f"rated_current_A deve ser > 0, recebido "
                f"{self.rated_current_A}"
            )

    def K_factor(self) -> float:
        """K (s) para t = K / (I/In)² — IEEE 242 §11.5.6."""
        return _K_THROUGH_FAULT[self.category]

    def through_fault_time_at_current(self, current_A: float) -> float:
        """
        Tempo até damage por through-fault na corrente I.

        Implementa IEEE C57.109 §5: ``t = MAX(K/I_pu², 2s)``.

        Returns
        -------
        float
            Tempo em segundos. ``inf`` se ``I ≤ rated_current_A``
            ou disabled.
        """
        if not self.enabled:
            return float("inf")
        if current_A <= self.rated_current_A:
            return float("inf")
        K = self.K_factor()
        i_pu = current_A / self.rated_current_A
        # Ramo térmico: t_thermal = K / I_pu²
        t_thermal = K / (i_pu ** 2)
        # Piso mecânico (IEEE C57.109 §5): em high I (I_pu > sqrt(K/2)),
        # XFMR aguenta no MÍNIMO 2s antes de damage mecânico.
        # MAX entre os 2 ramos = damage envelope.
        return max(t_thermal, _T_MECHANICAL_FLOOR_S)

    def through_fault_points(
        self,
        i_min_A: float = 0.0,
        i_max_A: float = 1e5,
        n_points: int = 100,
    ) -> list[tuple[float, float]]:
        """
        Pontos (I, t) para plot log-log.

        Range default começa logo acima de In e vai até i_max_A.
        """
        eff_min = max(i_min_A, self.rated_current_A * 1.001)
        if eff_min <= 0 or i_max_A <= eff_min or n_points < 2:
            return []
        log_min = math.log10(eff_min)
        log_max = math.log10(i_max_A)
        step = (log_max - log_min) / (n_points - 1)
        pts: list[tuple[float, float]] = []
        for i in range(n_points):
            I = 10 ** (log_min + i * step)
            t = self.through_fault_time_at_current(I)
            if math.isfinite(t):
                pts.append((I, t))
        return pts


# ---------------------------------------------------------------------------
# γ.3 — Motor thermal limit (IEC 60079-7 / NEMA MG-1)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MotorThermalCurve:
    """
    Curva de damage térmico de motor (locked rotor heating
    + overload protection).

    Modelagem
    ----------

    Aproximação analítica baseada em IEC 60079-7 §6.4.2 e
    NEMA MG-1 §12.45 (single-time-constant motor):

    ::

        t(I) = K_motor / (I/FLA)²    para FLA·1.05 < I

    O K_motor é calibrado para que, em ``locked rotor current``
    (default 6× FLA), a curva passe pelo ``locked_rotor_time_s``
    (tE):

    ::

        K_motor = locked_rotor_time_s × locked_rotor_factor²
                = tE × (I_LR / FLA)²

    Convenção
    ----------

    * Para ``I ≤ 1.05 × FLA``: ``time = inf`` (operação contínua,
      motor acomoda termicamente).
    * Para ``1.05 FLA < I``: ``time = K_motor / (I/FLA)²``.

    Em ``I = locked_rotor_factor × FLA`` (típico 6×): retorna
    exatamente ``locked_rotor_time_s`` (ponto-âncora).

    Attributes
    ----------

    motor_id:
        Identificador (ex: "M-PUMP-1", "MOT-VFD-3").
    fla_A:
        Full Load Amperes em A.
    locked_rotor_factor:
        Razão I_locked_rotor / FLA. Default 6.0 (motor padrão
        NEMA Design B, IEC 60079-7).
    locked_rotor_time_s:
        Tempo permitido em locked rotor (tE). Default 10.0 s
        (motor padrão Class B insulation).

        Valores típicos:

        * Motor IEC pequeno (≤22kW): 10-20 s
        * Motor NEMA Design B médio: 8-15 s
        * Motor com ventilação forçada: 15-30 s
        * Motor crítico (com PT100 + relé 49): use datasheet
    enabled:
        Se False, ``thermal_time_at_current`` retorna inf.

    Cobertura normativa
    --------------------

    * IEC 60079-7:2017 §6.4.2 (motors for explosive atmospheres
      — definição de tE)
    * NEMA MG-1 §12.45 (motor thermal limit single-time-const)
    * IEC 60034-12 (motor starting characteristics, NEMA Design)
    * IEEE Std 242:2001 §11.6 (motor protection coordination)

    Limitações documentadas
    ------------------------

    * Modelo single-time-constant é aproximação. Motores com
      thermal ROTOR != STATOR (e.g., grandes alta tensão)
      requerem 2-time-constant model — usar
      ``TCCSegmentTimeCurrentPoints`` com tabela do datasheet.
    * Não distingue HOT vs COLD start (datasheet do fabricante
      tem 2 curvas separadas; aqui uma única).
    * Para coordenação 49 IEEE 242 §11.6, esta curva é o
      LIMITE — proteção 49 deve estar abaixo (mais rápida).
    """

    motor_id: str
    fla_A: float
    locked_rotor_factor: float = 6.0
    locked_rotor_time_s: float = 10.0
    enabled: bool = True

    def __post_init__(self) -> None:
        if self.fla_A <= 0:
            raise ValueError(
                f"fla_A deve ser > 0, recebido {self.fla_A}"
            )
        if self.locked_rotor_factor <= 1.0:
            raise ValueError(
                f"locked_rotor_factor deve ser > 1.0, recebido "
                f"{self.locked_rotor_factor}"
            )
        if self.locked_rotor_time_s <= 0:
            raise ValueError(
                f"locked_rotor_time_s deve ser > 0, recebido "
                f"{self.locked_rotor_time_s}"
            )

    def K_motor(self) -> float:
        """
        Constante térmica K = tE × (I_LR/FLA)².

        Calibração: para I=I_LR, t = K/(I_LR/FLA)² = tE.
        """
        return self.locked_rotor_time_s * (self.locked_rotor_factor ** 2)

    def thermal_time_at_current(self, current_A: float) -> float:
        """
        Tempo até damage térmico no motor para corrente I.

        Returns
        -------
        float
            Tempo em segundos. ``inf`` se ``I ≤ 1.05·FLA`` (operação
            contínua) ou disabled.
        """
        if not self.enabled:
            return float("inf")
        # 1.05 × FLA é o threshold típico de overload (NEMA MG-1)
        # — abaixo disso o motor acomoda termicamente.
        i_threshold = 1.05 * self.fla_A
        if current_A <= i_threshold:
            return float("inf")
        K = self.K_motor()
        i_pu = current_A / self.fla_A
        return K / (i_pu ** 2)

    def thermal_points(
        self,
        i_min_A: float = 0.0,
        i_max_A: float = 1e5,
        n_points: int = 100,
    ) -> list[tuple[float, float]]:
        """
        Pontos (I, t) para plot log-log.
        """
        eff_min = max(i_min_A, 1.05 * self.fla_A * 1.001)
        if eff_min <= 0 or i_max_A <= eff_min or n_points < 2:
            return []
        log_min = math.log10(eff_min)
        log_max = math.log10(i_max_A)
        step = (log_max - log_min) / (n_points - 1)
        pts: list[tuple[float, float]] = []
        for i in range(n_points):
            I = 10 ** (log_min + i * step)
            t = self.thermal_time_at_current(I)
            if math.isfinite(t):
                pts.append((I, t))
        return pts
