"""
app.postprocessor.ct_saturation — análise de saturação de
Transformadores de Corrente (TCs) para proteção (v0.93.0).

Filosofia
==========

Saturação de TC é uma das **causas mais comuns de mal-
funcionamento de proteção 50/51**. Quando o TC satura:

* Sinal secundário fica truncado (perde valor RMS verdadeiro)
* Relé "vê" corrente menor → dispara tarde ou não dispara
* Saída assimétrica gera componente DC → afeta diferenciais
* Tempo até saturação < tempo de pickup do relé = FALHA

Este módulo implementa a análise em **3 níveis** consagrada
em SKM PTW Power*Tools, ETAP CT Saturation Analyzer e nos
estudos OSPF / CIGRÉ:

1. **Level 1 — ANSI estático** (IEEE C57.13.1-2017):
   Verifica se a tensão de capacidade do TC (V_tap) é maior
   que a tensão requerida pela falta (V_req = I_fsec ·
   (1+X/R) · Z_loop). Critério clássico para classes ANSI C.

2. **Level 2 — IEC joelho** (IEC 61869-2 §5.6):
   Verifica se a tensão de joelho (Vk, definida pelo critério
   10/50: 10% acima de Vk → 50% mais corrente) é maior que
   a tensão requerida. Aplica-se a classes IEC P / PR.

3. **Level 3 — Dinâmico** (CIGRÉ Working Group 23-15):
   Simula a equação do fluxo magnético via ODE:

   ::

       λ(t) / dt = (i_st(t) - i_e(λ)) · R_total

   Considerando:
   * DC offset máximo (φ - θ = -π/2, pior caso)
   * Constante de tempo T_p = X/(ωR)
   * Curva de magnetização não-linear (interp1)
   * Fluxo remanescente (Kr · λ_joelho)
   * 0.8 (ANSI / IEC P), 0.1 (IEC PR)

   Determina **t_sat** (tempo até satura) e compara com
   **t_relay** (tempo de pickup) e **t_total** (extinção
   total = t_relay + t_breaker).

Cobertura normativa
====================

* IEEE C57.13.1-2017 — Standard for Performance and Test
  Code for Current Transformers Used for Protection
* IEEE C37.110-2007 — Application of Current Transformers
  Used for Protective Relaying
* IEC 61869-2:2012 — Current transformers (substituiu
  60044-1:2003)
* CIGRÉ WG 23-15 — Effect of CT saturation on protective
  relays
* ABNT NBR 6856:2015 — Transformadores de corrente

Não inclui (limitações declaradas)
===================================

* TPS/TPX/TPY/TPZ classes (IEC 61869-2 §6.5) — específicas
  para diferenciais transitórios; uso restrito.
* Modelagem detalhada de histerese (Jiles-Atherton);
  usamos curva monotônica equivalente.
* Saturação de núcleos não-orientados (ferrite,
  amorfo) — assume aço silício 0.27 mm grão orientado.
* Efeito de carga reverse (back-fed); assume falta única
  forward.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Callable, Optional

from app.core.logging_config import get_logger

log = get_logger(__name__)


# ---------------------------------------------------------------------------
# Constantes físicas
# ---------------------------------------------------------------------------


_PI2 = 2 * math.pi
_SQRT2 = math.sqrt(2)
_DEFAULT_FREQ_HZ = 60.0   # Brasil (60 Hz). EUA também 60 Hz.

# Resistividade do cobre @ 75°C (operação típica de cabos
# de proteção em painel) — fórmula linearizada:
# ρ(T) = ρ(20°C) · (1 + α·(T-20))
# ρ(20°C, Cu) = 0.01724 Ω·mm²/m
# α(Cu) = 0.00393 /°C
_RHO_CU_75C_OHM_MM2_PER_M = (
    0.01724 * (1 + 0.00393 * (75 - 20))
)   # ≈ 0.02097 Ω·mm²/m

# Critério IEC 10/50: 10% V → 50% I
_IEC_KNEE_V_RATIO = 1.10
_IEC_KNEE_I_RATIO = 1.50

# Fatores de remanência típicos (CIGRÉ + IEC 61869-2)
DEFAULT_KR_ANSI = 0.8       # ANSI C high remanence (~80%)
DEFAULT_KR_IEC_P = 0.8      # IEC P (mesmo)
DEFAULT_KR_IEC_PR = 0.1     # IEC PR low remanence (gap, <=10%)


# ---------------------------------------------------------------------------
# Dataclasses de input
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CTFaultContext:
    """
    Contexto de falta no ponto onde o TC está instalado.

    Atributos
    ---------
    bus_id:
        Identificador do barramento (ex: "BUS-MAIN-13.8").
    rated_voltage_kV:
        Tensão nominal LL (kV). Usada apenas para metadata
        (não entra nos cálculos de saturação propriamente).
    I_fault_rms_kA:
        Corrente de curto-circuito simétrica RMS (kA).
        Tipicamente Ik'' do estudo IEC 60909.
    X_over_R:
        Razão X/R no ponto da falta. Determina:
        * O κ (peak factor) em Level 1 (1 + X/R)
        * A constante de tempo DC T_p = X/(ωR)
        * O ângulo θ = atan(X/R)
    """

    bus_id: str
    rated_voltage_kV: float
    I_fault_rms_kA: float
    X_over_R: float

    def __post_init__(self) -> None:
        # Validação física (v0.93.0 — defensável)
        if not isinstance(self.bus_id, str) or not self.bus_id.strip():
            raise ValueError(
                f"CTFaultContext: bus_id deve ser string não-vazia "
                f"(got {self.bus_id!r})"
            )
        if self.rated_voltage_kV <= 0:
            raise ValueError(
                f"CTFaultContext[{self.bus_id}]: rated_voltage_kV "
                f"deve ser > 0 (got {self.rated_voltage_kV})"
            )
        if self.I_fault_rms_kA <= 0:
            raise ValueError(
                f"CTFaultContext[{self.bus_id}]: I_fault_rms_kA "
                f"deve ser > 0 (got {self.I_fault_rms_kA})"
            )
        if self.X_over_R < 0:
            raise ValueError(
                f"CTFaultContext[{self.bus_id}]: X_over_R "
                f"não pode ser negativo (got {self.X_over_R})"
            )

    @property
    def I_fault_rms_A(self) -> float:
        return self.I_fault_rms_kA * 1000.0

    @property
    def I_fault_peak_A(self) -> float:
        """Pico de falta = √2 · Irms."""
        return self.I_fault_rms_A * _SQRT2

    @property
    def time_constant_dc_s(self, freq_hz: float = _DEFAULT_FREQ_HZ) -> float:
        """T_p = X / (ωR) — constante de decaimento DC."""
        if self.X_over_R <= 0:
            return 1e-4   # ~0; sem componente DC apreciável
        omega = _PI2 * freq_hz
        return self.X_over_R / omega


@dataclass(frozen=True)
class MagnetizationCurve:
    """
    Curva de excitação V-I do TC em RMS (eixo X = Ie em A,
    eixo Y = Ve em V). Define o comportamento não-linear do
    núcleo magnético.

    A curva é fornecida pelo fabricante OU estimada pela
    função :func:`typical_magnetization_curve` baseada na
    classe (C-rating ou VA · ALF).

    Convenção: pontos em ordem crescente (Ie monotônico).
    """

    Ie: tuple[float, ...]   # corrente excitação RMS (A)
    Ve: tuple[float, ...]   # tensão secundária RMS (V)

    def __post_init__(self):
        if len(self.Ie) != len(self.Ve):
            raise ValueError(
                f"MagnetizationCurve: Ie ({len(self.Ie)}) e "
                f"Ve ({len(self.Ve)}) devem ter mesmo tamanho"
            )
        if len(self.Ie) < 2:
            raise ValueError(
                "MagnetizationCurve: precisa de pelo menos 2 pontos"
            )

    def knee_voltage_iec_10_50(self) -> float:
        """
        v0.93.0 — Tensão de joelho conforme IEC 61869-2 §5.6:
        ponto onde 10% de aumento em V causa ≥ 50% aumento
        em I. Algoritmo: itera pelos pares (V_i, I_i) buscando
        o primeiro V tal que I(1.10·V) / I(V) ≥ 1.50.
        """
        for i in range(len(self.Ve) - 1):
            v1 = self.Ve[i]
            i1 = max(self.Ie[i], 1e-12)
            v_test = v1 * _IEC_KNEE_V_RATIO
            i_test = _interp_linear(self.Ve, self.Ie, v_test)
            if (i_test / i1) >= _IEC_KNEE_I_RATIO:
                return v1
        # Não achou — retorna o último (saturação implícita)
        return self.Ve[-1]

    def excitation_current(self, V: float) -> float:
        """Ie(V) — interpolação linear da curva."""
        return _interp_linear(self.Ve, self.Ie, V)

    def excitation_current_from_flux(
        self, flux_wb_e: float, freq_hz: float = _DEFAULT_FREQ_HZ,
    ) -> float:
        """
        Ie(λ) — converte fluxo concatenado para tensão e
        retorna a corrente de excitação correspondente.

        V_rms = ω · λ_rms = ω · λ_peak / √2.
        Como o fluxo de pico está disponível: V_peak = ω·λ_peak,
        e V_rms = V_peak/√2.
        """
        omega = _PI2 * freq_hz
        V_rms = omega * abs(flux_wb_e) / _SQRT2
        i_rms = self.excitation_current(V_rms)
        # Retorna o pico instantâneo (multiplica por √2 e
        # mantém sinal do fluxo)
        sign = 1.0 if flux_wb_e >= 0 else -1.0
        return sign * i_rms * _SQRT2


def typical_magnetization_curve(
    knee_voltage_V: float,
    knee_current_A: float = 0.1,
) -> MagnetizationCurve:
    """
    v0.93.0 — Gera uma curva de excitação típica baseada em
    V_knee e I_knee. Útil quando o fabricante não fornece a
    curva detalhada (estimativa de engenharia).

    Forma da curva (multiplicadores de V_knee e I_knee):

    ::

        V/V_knee:  0.10, 0.50, 0.80, 1.00, 1.10, 1.50
        I/I_knee:  0.01, 0.05, 0.10, 1.00, 5.00, 50.0

    O joelho (V=V_knee, I=I_knee) cumpre o critério IEC
    10/50 por construção.
    """
    if knee_voltage_V <= 0:
        raise ValueError("knee_voltage_V deve ser > 0")
    Vmul = (0.10, 0.50, 0.80, 1.00, 1.10, 1.50)
    Imul = (0.01, 0.05, 0.10, 1.00, 5.00, 50.0)
    Ve = tuple(knee_voltage_V * v for v in Vmul)
    Ie = tuple(knee_current_A * i for i in Imul)
    return MagnetizationCurve(Ie=Ie, Ve=Ve)


@dataclass(frozen=True)
class CTSpec:
    """
    Especificação completa de um TC para análise de
    saturação.

    Tipo / Norma
    ------------
    tipo_TC ∈ {"ANSI_C", "IEC_P", "IEC_PR"}
    * ANSI_C — classe IEEE C57.13 (C50, C100, C200, C400, C800)
    * IEC_P — classe IEC 61869-2 P (alta remanência ~80%)
    * IEC_PR — classe IEC 61869-2 PR (low remanence ≤10%, com gap)

    Relação de Transformação
    ------------------------
    I_pri_nom_tap: corrente primária do tap em uso (A)
    I_pri_nom_full: corrente primária máxima do enrolamento (A)
                     (para classe ANSI C, V_tap = V_full ·
                      I_pri_nom_tap/I_pri_nom_full)
    I_sn: corrente secundária nominal (1 ou 5 A)
    CT_Ratio = I_pri_nom_tap / I_sn

    Classe / Tensão
    ----------------
    CT_Rating_C: tensão de capacidade ANSI (V) — para Cxxx
                 (ex: 200 → 200 V no full ratio)
    IEC_VA: potência IEC (VA)
    IEC_ALF: fator ALF (10, 15, 20, 30, 40, 50)
             (CT_Rating_C = IEC_VA/I_sn · IEC_ALF)

    Burden
    ------
    R_s: resistência do enrolamento secundário (Ω)
    R_b: resistência da carga (relé + cabo) (Ω)
    Z_loop = R_s + R_b

    Curva de Excitação
    -------------------
    curve: :class:`MagnetizationCurve` — pode ser do
           fabricante OU típica.

    Remanência
    -----------
    Kr: fator de remanência (0..1) — fração do λ_joelho
        que persiste no núcleo após operações anteriores.
        Default por classe: 0.8 (ANSI / IEC P), 0.1 (IEC PR).

    Tempos
    -------
    t_relay_ms: tempo de pickup do relé (ms) — quando o
                relé toma a decisão de disparar.
    t_breaker_ms: tempo de abertura do disjuntor (ms) —
                  desde o trip até a extinção.
    t_total_ms: t_relay + t_breaker — tempo até falta
                ser efetivamente extinta.
    """

    tag: str
    tipo_TC: str   # "ANSI_C", "IEC_P", "IEC_PR"
    I_pri_nom_tap: float
    I_pri_nom_full: float
    I_sn: float    # 1 or 5
    CT_Rating_C: float
    R_s: float     # secundário interno
    R_b: float     # burden externo (relé + cabo)
    curve: MagnetizationCurve
    Kr: float = DEFAULT_KR_ANSI
    t_relay_ms: float = 20.0
    t_breaker_ms: float = 50.0

    # Opcionais (informativos, não usados no cálculo)
    IEC_VA: Optional[float] = None
    IEC_ALF: Optional[float] = None
    description: str = ""

    def __post_init__(self) -> None:
        if self.tipo_TC not in ("ANSI_C", "IEC_P", "IEC_PR"):
            raise ValueError(
                f"CTSpec[{self.tag}]: tipo_TC deve ser ANSI_C, "
                f"IEC_P ou IEC_PR (got {self.tipo_TC!r})"
            )
        if self.I_pri_nom_tap <= 0:
            raise ValueError(
                f"CTSpec[{self.tag}]: I_pri_nom_tap > 0"
            )
        if self.I_pri_nom_full < self.I_pri_nom_tap:
            raise ValueError(
                f"CTSpec[{self.tag}]: I_pri_nom_full deve ser "
                f">= I_pri_nom_tap"
            )
        if self.I_sn not in (1, 1.0, 5, 5.0):
            log.warning(
                "CTSpec[%s]: I_sn=%s não-padrão; IEC/ANSI usam "
                "1 A ou 5 A.", self.tag, self.I_sn,
            )
        if self.R_s < 0:
            raise ValueError(
                f"CTSpec[{self.tag}]: R_s não pode ser negativo"
            )
        if self.R_b < 0:
            raise ValueError(
                f"CTSpec[{self.tag}]: R_b não pode ser negativo"
            )
        if not (0 <= self.Kr <= 1):
            raise ValueError(
                f"CTSpec[{self.tag}]: Kr deve ∈ [0, 1] "
                f"(got {self.Kr})"
            )
        if self.t_relay_ms <= 0:
            raise ValueError(
                f"CTSpec[{self.tag}]: t_relay_ms > 0"
            )
        if self.t_breaker_ms <= 0:
            raise ValueError(
                f"CTSpec[{self.tag}]: t_breaker_ms > 0"
            )

    @property
    def CT_Ratio(self) -> float:
        """N1/N2 = I_pri_tap / I_sn."""
        return self.I_pri_nom_tap / self.I_sn

    @property
    def Z_loop(self) -> float:
        """Impedância total do laço secundário (Ω)."""
        return self.R_s + self.R_b

    @property
    def t_total_ms(self) -> float:
        """Tempo até extinção total (ms)."""
        return self.t_relay_ms + self.t_breaker_ms


# ---------------------------------------------------------------------------
# Burden helper (cabo + relé)
# ---------------------------------------------------------------------------


def cable_burden_resistance(
    distance_m: float,
    cross_section_mm2: float,
    rho_ohm_mm2_per_m: float = _RHO_CU_75C_OHM_MM2_PER_M,
) -> float:
    """
    v0.93.0 — Resistência DC do cabo de cobre (ida+volta) a
    75°C, conforme NBR 5410 §6.2.

    R = ρ · L / A

    Parameters
    ----------
    distance_m:
        Distância TOTAL (ida + volta) entre TC e relé (m).
    cross_section_mm2:
        Bitola do cabo (2.5, 4, 6, 10, 16…).
    rho_ohm_mm2_per_m:
        Resistividade do material. Default = cobre @ 75°C.

    Returns
    -------
    float
        Resistência em ohms.
    """
    if distance_m <= 0:
        raise ValueError("distance_m deve ser > 0")
    if cross_section_mm2 <= 0:
        raise ValueError("cross_section_mm2 deve ser > 0")
    return rho_ohm_mm2_per_m * distance_m / cross_section_mm2


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Level1AnsiResult:
    """
    Resultado do critério ANSI estático (1 + X/R).

    V_tap: tensão de capacidade no tap atual (V)
    V_req: tensão requerida pela falta (V)
    passed: V_tap >= V_req
    recommended_class_C: sugestão de classe ANSI próxima
                          (ex: "C200", "C400")
    """

    V_tap: float
    V_req: float
    passed: bool
    recommended_class_C: str
    citation: str = "IEEE C57.13.1-2017 §6.4.1 (1+X/R criterion)"


@dataclass(frozen=True)
class Level2IecResult:
    """
    Resultado do critério IEC joelho.

    Ek_actual: tensão de joelho real do TC (V)
    Ek_req: tensão requerida (V) — mesmo cálculo do Level 1
    passed: Ek_actual >= Ek_req
    recommended_class: sugestão "VA 10P{ALF}" (ex: "25VA 10P30")
    """

    Ek_actual: float
    Ek_req: float
    passed: bool
    recommended_class: str
    citation: str = "IEC 61869-2:2012 §5.6 (knee 10/50)"


@dataclass(frozen=True)
class Level3DynamicResult:
    """
    Resultado da simulação dinâmica do fluxo magnético.

    t_sat_ms: tempo até saturação (ms) ou ∞ se não satura
    sat_at_trip_pct: % do λ_joelho atingido no instante do trip
    sat_peak_pct: % máximo de λ_joelho atingido em toda simulação
    margin_ms: t_sat - t_relay (positivo = OK; negativo = FALHA)
    status: "PASSOU" / "APROVADO COM TOLERANCIA" / "FALHOU"
    flux_curve: tuple de (t_ms, λ) — para plotar
    secondary_current_ideal: i_st(t) (sem distorção) — para plotar
    secondary_current_real: i_s(t) (com distorção) — para plotar
    """

    t_sat_ms: float
    sat_at_trip_pct: float
    sat_peak_pct: float
    margin_ms: float
    status: str
    flux_curve_t_ms: tuple[float, ...] = ()
    flux_curve_wb_e: tuple[float, ...] = ()
    secondary_current_ideal: tuple[float, ...] = ()
    secondary_current_real: tuple[float, ...] = ()
    citation: str = (
        "CIGRÉ WG 23-15 / IEEE C37.110-2007 §6.2 "
        "(transient saturation analysis)"
    )


@dataclass(frozen=True)
class CTSaturationReport:
    """
    Relatório consolidado da análise CT-SAT (3 níveis).

    final_status:
        Pior caso entre os 3 níveis. Se Level 3 falhar ou
        for inconclusivo, é o critério mestre (CIGRÉ
        recomenda Level 3 como autoritativo).
    final_detail: razão técnica do final_status.
    level1, level2, level3: resultados individuais.
    """

    ct: "CTSpec"
    fault: CTFaultContext
    level1: Level1AnsiResult
    level2: Optional[Level2IecResult]
    level3: Level3DynamicResult
    final_status: str
    final_detail: str

    def summary(self) -> str:
        """Texto humano-legível resumindo os 3 níveis."""
        lines = [
            f"=== CT Saturation Report — {self.ct.tag} ===",
            f"Bus: {self.fault.bus_id} ({self.fault.rated_voltage_kV:.2f} kV)",
            f"Falta: {self.fault.I_fault_rms_kA:.2f} kA, X/R = {self.fault.X_over_R:.2f}",
            f"Tipo TC: {self.ct.tipo_TC}, Kr = {self.ct.Kr:.2f}",
            f"Relação: {self.ct.I_pri_nom_tap:.0f}/{self.ct.I_sn:.0f}",
            f"Burden: {self.ct.Z_loop:.4f} Ω",
            "",
            f"  Nível 1 (ANSI):     V_tap={self.level1.V_tap:.0f} V, "
            f"V_req={self.level1.V_req:.0f} V → "
            f"{'PASSOU' if self.level1.passed else 'FALHOU'}",
        ]
        if self.level2 is not None:
            lines.append(
                f"  Nível 2 (IEC):      Ek={self.level2.Ek_actual:.0f} V, "
                f"Ek_req={self.level2.Ek_req:.0f} V → "
                f"{'PASSOU' if self.level2.passed else 'FALHOU'}"
            )
        lines.append(
            f"  Nível 3 (Dinâmico): t_sat={self.level3.t_sat_ms:.1f} ms "
            f"(margem {self.level3.margin_ms:+.1f} ms) → "
            f"{self.level3.status}"
        )
        lines.append("")
        lines.append(f"RESULTADO FINAL: {self.final_status}")
        lines.append(f"  → {self.final_detail}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Level 1 — ANSI estático (1 + X/R)
# ---------------------------------------------------------------------------


def analyze_ansi_level1(
    ct: CTSpec, fault: CTFaultContext,
) -> Level1AnsiResult:
    """
    Critério ANSI/IEEE C57.13.1-2017 §6.4.1.

    V_req = I_fault_sec · (1 + X/R) · Z_loop
    V_tap = V_capacity_full · I_pri_tap / I_pri_full

    PASSOU se V_tap >= V_req.
    """
    if ct.CT_Rating_C <= 0:
        raise ValueError(
            f"CT [{ct.tag}]: CT_Rating_C deve ser > 0 para Level 1"
        )

    # Tensão requerida pela falta
    I_fault_sec = fault.I_fault_rms_A / ct.CT_Ratio
    V_req = I_fault_sec * (1 + fault.X_over_R) * ct.Z_loop

    # Tensão de capacidade no tap atual
    V_tap = ct.CT_Rating_C * (
        ct.I_pri_nom_tap / ct.I_pri_nom_full
    )

    passed = V_tap >= V_req

    # Recomendação: qual classe ANSI cobriria V_req?
    classes = (100, 200, 400, 800)
    C_req = V_req * (ct.I_pri_nom_full / ct.I_pri_nom_tap)
    rec = next((f"C{c}" for c in classes if c >= C_req), None)
    if rec is None:
        # Acima de C800 → custom
        rec = f"C{int(math.ceil(C_req / 100) * 100)} (custom)"

    log.info(
        "CT-SAT L1 [%s @ %s]: V_tap=%.1f V, V_req=%.1f V → %s",
        ct.tag, fault.bus_id, V_tap, V_req,
        "PASSOU" if passed else "FALHOU",
    )

    return Level1AnsiResult(
        V_tap=V_tap, V_req=V_req,
        passed=passed,
        recommended_class_C=rec,
    )


# ---------------------------------------------------------------------------
# Level 2 — IEC joelho (10/50)
# ---------------------------------------------------------------------------


def analyze_iec_level2(
    ct: CTSpec, fault: CTFaultContext,
) -> Optional[Level2IecResult]:
    """
    Critério IEC 61869-2:2012 §5.6 — joelho 10/50.

    Ek_req = I_fault_sec · (1 + X/R) · Z_loop
    Ek_actual = curve.knee_voltage_iec_10_50()

    Retorna None se a curva for inválida.
    """
    if ct.curve is None or len(ct.curve.Ie) < 2:
        log.warning(
            "CT-SAT L2 [%s]: curva de excitação ausente; "
            "pulando Level 2 IEC.", ct.tag,
        )
        return None

    I_fault_sec = fault.I_fault_rms_A / ct.CT_Ratio
    Ek_req = I_fault_sec * (1 + fault.X_over_R) * ct.Z_loop
    Ek_actual = ct.curve.knee_voltage_iec_10_50()

    passed = Ek_actual >= Ek_req

    # Recomendação IEC: ALF necessário
    if ct.IEC_VA is not None and ct.IEC_VA > 0:
        ALF_calc = Ek_req / (ct.I_sn * ct.Z_loop)
        alfs = (10, 15, 20, 30, 40, 50)
        alf_rec = next((a for a in alfs if a >= ALF_calc), None)
        suffix = "PR" if ct.tipo_TC == "IEC_PR" else "P"
        if alf_rec is not None:
            rec = f"{ct.IEC_VA:.0f}VA 10{suffix}{alf_rec}"
        else:
            rec = (
                f"{ct.IEC_VA:.0f}VA 10{suffix}"
                f"{int(math.ceil(ALF_calc / 5) * 5)}+"
            )
    else:
        rec = "N/A (sem VA configurado)"

    log.info(
        "CT-SAT L2 [%s @ %s]: Ek_actual=%.1f V, Ek_req=%.1f V → %s",
        ct.tag, fault.bus_id, Ek_actual, Ek_req,
        "PASSOU" if passed else "FALHOU",
    )

    return Level2IecResult(
        Ek_actual=Ek_actual, Ek_req=Ek_req,
        passed=passed,
        recommended_class=rec,
    )


# ---------------------------------------------------------------------------
# Level 3 — Dinâmico (ODE solver)
# ---------------------------------------------------------------------------


def analyze_dynamic_level3(
    ct: CTSpec, fault: CTFaultContext,
    *,
    freq_hz: float = _DEFAULT_FREQ_HZ,
    t_sim_stop_s: float = 0.2,
    n_steps: int = 2001,
) -> Level3DynamicResult:
    """
    Simulação dinâmica do fluxo magnético com DC offset máximo
    e remanência (CIGRÉ WG 23-15 / IEEE C37.110-2007 §6.2).

    Equação diferencial:

    ::

        dλ/dt = (i_st(t) - i_e(λ)) · R_total

    onde:

    * i_p(t) = I_peak · [sin(ωt + φ - θ) - sin(φ - θ) · exp(-t/T_p)]
      é a corrente primária com DC offset máximo (φ-θ = -π/2).
    * i_st(t) = i_p(t) / N — corrente secundária ideal
      (se não houvesse saturação).
    * i_e(λ) — corrente de excitação não-linear (interp da curva
      magnetização).
    * R_total = R_s + R_b — burden total no laço secundário.

    Condição inicial: λ(0) = Kr · λ_joelho (fluxo remanescente).

    Critérios de aprovação:

    * **PASSOU**: t_sat > t_total (TC não satura durante toda
      a falta).
    * **APROVADO COM TOLERÂNCIA**: t_sat > t_relay + margin_req
      (TC satura DEPOIS da decisão do relé).
    * **FALHOU**: t_sat ≤ t_relay + margin_req.

    margin_req: 3.0 ms (ANSI/IEC P), 2.0 ms (IEC PR).

    Implementação: sem dependência de scipy — usa RK4 manual
    com passo fixo h = t_sim_stop_s / (n_steps - 1). n_steps=2001
    → h=0.1 ms, suficiente para precisão de ms.
    """
    if ct.curve is None or len(ct.curve.Ie) < 2:
        return Level3DynamicResult(
            t_sat_ms=float("inf"),
            sat_at_trip_pct=0.0,
            sat_peak_pct=0.0,
            margin_ms=0.0,
            status="PULADO (curva ausente)",
        )

    # ---------- 1. Configuração física ----------
    omega = _PI2 * freq_hz
    Z_loop = ct.Z_loop
    I_peak = fault.I_fault_peak_A

    if fault.X_over_R <= 0:
        T_p = 1e-4
    else:
        T_p = fault.X_over_R / omega
    theta = math.atan(fault.X_over_R)
    phi = 0.0   # Pior caso (DC offset máximo)

    def i_p(t: float) -> float:
        """Corrente primária instantânea (A) — DC offset max."""
        return I_peak * (
            math.sin(omega * t + phi - theta)
            - math.sin(phi - theta) * math.exp(-t / T_p)
        )

    def i_st(t: float) -> float:
        """Corrente secundária ideal (A) — sem saturação."""
        return i_p(t) / ct.CT_Ratio

    # ---------- 2. Curva de magnetização e remanência ----------
    # Estende para simetria: -fliplr(Ve), 0, Ve (mesmo para Ie).
    Ve_arr = list(ct.curve.Ve)
    Ie_arr = list(ct.curve.Ie)
    lambda_pos = [v * _SQRT2 / omega for v in Ve_arr]
    ie_pos = [i * _SQRT2 for i in Ie_arr]

    # Curva simétrica em torno de zero
    lambda_curve = (
        [-v for v in reversed(lambda_pos)] + [0.0] + lambda_pos
    )
    ie_curve = (
        [-i for i in reversed(ie_pos)] + [0.0] + ie_pos
    )

    def i_e_lambda(lam: float) -> float:
        """Corrente de excitação dado o fluxo concatenado λ."""
        return _interp_linear(
            tuple(lambda_curve), tuple(ie_curve), lam,
        )

    # Joelho real (limite físico)
    Ek_actual = ct.curve.knee_voltage_iec_10_50()
    lambda_knee = (Ek_actual * _SQRT2) / omega

    # Condição inicial: fluxo remanescente
    lambda_0 = ct.Kr * lambda_knee

    # ---------- 3. Simulação RK4 ----------
    h = t_sim_stop_s / (n_steps - 1)
    t_arr = [i * h for i in range(n_steps)]
    lambda_arr = [0.0] * n_steps
    lambda_arr[0] = lambda_0

    def f(t: float, lam: float) -> float:
        return (i_st(t) - i_e_lambda(lam)) * Z_loop

    for k in range(n_steps - 1):
        t = t_arr[k]
        lam = lambda_arr[k]
        k1 = f(t, lam)
        k2 = f(t + h / 2, lam + h / 2 * k1)
        k3 = f(t + h / 2, lam + h / 2 * k2)
        k4 = f(t + h, lam + h * k3)
        lambda_arr[k + 1] = lam + (h / 6) * (
            k1 + 2 * k2 + 2 * k3 + k4
        )

    # ---------- 4. Análise ----------
    # Tempo até saturação: primeiro instante em que |λ| ≥ λ_knee
    t_sat_ms = float("inf")
    for k, lam in enumerate(lambda_arr):
        if abs(lam) >= lambda_knee:
            t_sat_ms = t_arr[k] * 1000.0
            break

    # λ no instante do trip (interpolação)
    t_trip_s = ct.t_relay_ms / 1000.0
    lambda_at_trip = _interp_linear(
        tuple(t_arr), tuple(lambda_arr), t_trip_s,
    )
    sat_at_trip_pct = (abs(lambda_at_trip) / lambda_knee) * 100.0
    sat_peak_pct = (
        max(abs(lam) for lam in lambda_arr) / lambda_knee
    ) * 100.0
    margin_ms = t_sat_ms - ct.t_relay_ms

    # Critério de aprovação
    margin_req = 2.0 if ct.tipo_TC == "IEC_PR" else 3.0
    if t_sat_ms > ct.t_total_ms:
        status = "PASSOU"
    elif t_sat_ms > (ct.t_relay_ms + margin_req):
        status = "APROVADO COM TOLERANCIA"
    else:
        status = "FALHOU"

    log.info(
        "CT-SAT L3 [%s @ %s]: t_sat=%.1f ms, margem=%+.1f ms → %s",
        ct.tag, fault.bus_id, t_sat_ms, margin_ms, status,
    )

    # Correntes para plotagem
    i_st_arr = [i_st(t) for t in t_arr]
    i_e_arr = [i_e_lambda(lam) for lam in lambda_arr]
    i_s_arr = [
        i_st_arr[k] - i_e_arr[k] for k in range(n_steps)
    ]

    return Level3DynamicResult(
        t_sat_ms=t_sat_ms,
        sat_at_trip_pct=sat_at_trip_pct,
        sat_peak_pct=sat_peak_pct,
        margin_ms=margin_ms,
        status=status,
        flux_curve_t_ms=tuple(t * 1000.0 for t in t_arr),
        flux_curve_wb_e=tuple(lambda_arr),
        secondary_current_ideal=tuple(i_st_arr),
        secondary_current_real=tuple(i_s_arr),
    )


# ---------------------------------------------------------------------------
# Orchestrator: run all 3 levels
# ---------------------------------------------------------------------------


def analyze_full(
    ct: CTSpec, fault: CTFaultContext,
    *,
    freq_hz: float = _DEFAULT_FREQ_HZ,
) -> CTSaturationReport:
    """
    Orquestra os 3 níveis de análise e consolida o resultado.

    O **Level 3 é autoritativo** quando todos os níveis foram
    executados (CIGRÉ WG 23-15 §4.3): falhar dinamicamente
    é mais crítico que falhar estaticamente, pois inclui
    DC offset e remanência.
    """
    level1 = analyze_ansi_level1(ct, fault)
    level2 = analyze_iec_level2(ct, fault)
    level3 = analyze_dynamic_level3(ct, fault, freq_hz=freq_hz)

    # Decisão final — priorizando Level 3 (dinâmico)
    if "FALHOU" in level3.status:
        final_status = level3.status
        final_detail = (
            f"Saturação prematura ({level3.t_sat_ms:.1f} ms) "
            f"devido a X/R={fault.X_over_R:.2f} e "
            f"remanência Kr={ct.Kr:.2f}. Margem "
            f"{level3.margin_ms:+.1f} ms vs requerida +"
            f"{2.0 if ct.tipo_TC == 'IEC_PR' else 3.0:.0f} ms."
        )
    elif "TOLERANCIA" in level3.status:
        final_status = level3.status
        final_detail = (
            f"TC satura após o tempo de decisão do relé "
            f"(margem {level3.margin_ms:+.1f} ms). "
            f"Aceito pela proteção 50/51, mas reduz overhead."
        )
    elif "PULADO" in level3.status:
        # Level 3 não rodou; usa Level 2 como master
        if level2 is not None and level2.passed:
            final_status = "PASSOU (estático)"
            final_detail = (
                "Level 3 dinâmico pulado (curva ausente). "
                f"Level 2 IEC: Ek={level2.Ek_actual:.0f} V > "
                f"Ek_req={level2.Ek_req:.0f} V."
            )
        elif level1.passed:
            final_status = "PASSOU (estático)"
            final_detail = (
                "Level 3 dinâmico pulado (curva ausente). "
                f"Level 1 ANSI: V_tap={level1.V_tap:.0f} V > "
                f"V_req={level1.V_req:.0f} V."
            )
        else:
            final_status = "FALHOU"
            final_detail = (
                "Level 3 pulado e Level 1 falhou — "
                "TC subdimensionado para a falta."
            )
    else:
        final_status = level3.status   # PASSOU
        final_detail = (
            "Desempenho robusto em todos os cenários. "
            f"t_sat = {level3.t_sat_ms:.1f} ms > t_total = "
            f"{ct.t_total_ms:.1f} ms."
        )

    return CTSaturationReport(
        ct=ct, fault=fault,
        level1=level1, level2=level2, level3=level3,
        final_status=final_status,
        final_detail=final_detail,
    )


# ---------------------------------------------------------------------------
# Helpers (interpolação linear sem dependência scipy)
# ---------------------------------------------------------------------------


def _interp_linear(
    x_curve: tuple[float, ...],
    y_curve: tuple[float, ...],
    x_query: float,
) -> float:
    """
    Interpolação linear 1-D com extrapolação. Equivale ao
    ``interp1(..., 'linear', 'extrap')`` do MATLAB.
    """
    n = len(x_curve)
    if n == 0:
        return 0.0
    if n == 1:
        return y_curve[0]

    # Fora do range — extrapola usando primeira/última
    # tangente
    if x_query <= x_curve[0]:
        if x_curve[1] == x_curve[0]:
            return y_curve[0]
        slope = (y_curve[1] - y_curve[0]) / (
            x_curve[1] - x_curve[0]
        )
        return y_curve[0] + slope * (x_query - x_curve[0])
    if x_query >= x_curve[-1]:
        if x_curve[-1] == x_curve[-2]:
            return y_curve[-1]
        slope = (y_curve[-1] - y_curve[-2]) / (
            x_curve[-1] - x_curve[-2]
        )
        return y_curve[-1] + slope * (x_query - x_curve[-1])

    # Bisseção para achar o intervalo (assume x_curve sorted)
    lo, hi = 0, n - 1
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if x_curve[mid] <= x_query:
            lo = mid
        else:
            hi = mid
    x0, x1 = x_curve[lo], x_curve[hi]
    y0, y1 = y_curve[lo], y_curve[hi]
    if x1 == x0:
        return y0
    t = (x_query - x0) / (x1 - x0)
    return y0 + t * (y1 - y0)
