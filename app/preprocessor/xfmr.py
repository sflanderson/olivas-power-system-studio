"""
app.preprocessor.xfmr — Hybrid Transformer Model (XFMR) com
núcleo topologicamente correto, baseado no trabalho de Mork
et al. (Michigan Tech, BPA-funded).

Aplicação primária
==================

**Estudos de inrush** (energização de transformador). O modelo
BCTRAN linear (entregue em v0.24.x) **não** captura o pico de
corrente de magnetização que ocorre na energização — só o XFMR
hybrid model faz isso corretamente, porque modela:

* Saturação **por perna do núcleo** (não apenas no terminal).
* **Topologia correta** do núcleo (3-leg, 5-leg, shell-form),
  que afeta a corrente zero-sequência e o caminho do fluxo
  durante saturação.
* **Equação de Frolich** para magnetização — extrapolação
  física para regiões fora dos pontos do test report (BCTRAN
  faz extrapolação linear, que falha em saturação extrema).
* **Fluxo residual** (residual flux), key parameter para o
  pico de inrush.

Outras aplicações
------------------

* **Sympathetic inrush** (transformadores próximos a um sendo
  energizado).
* **Geomagnetic disturbance (GIC/GMD)** — DC bias do núcleo.
* **Ferrorressonância** — saturação dinâmica do núcleo
  acoplada com capacitâncias.
* **Faltas internas** — diferencial 87T deve dessensibilizar
  a 2ª harmônica do inrush.

Fundamento (Mork MTU4-MTU7 + ATPDraw §5.7)
============================================

Estrutura do modelo (Fig. 5.68 ATPDraw manual):

::

    HV winding ─[R(f)]─[Leakage Lk]─┬─ artificial winding (core)
                                    │
                                    ├─[Mag Lleg]─ leg
                                    └─[Mag Lyoke]─ yoke

Quatro partes:

1. **Resistance R(f)**: resistência DC + skin/proximity effect.
2. **Leakage inductance** (A-matrix): impedância de dispersão
   conforme test report (BCTRAN-style).
3. **Capacitance** (C-matrix): capacitâncias entre enrolamentos
   e à terra.
4. **Core**: magnetização individual de pernas e yokes via
   equação de Frolich.

**Equação de Frolich** (3 parâmetros):

::

    H = a · B / (b + B) · sign(B) + c · B

Onde:

* B é a densidade de fluxo (Tesla)
* H é o campo magnético (A/m)
* a, b, c são parâmetros ajustados ao test report

A vantagem: extrapolação física para B → ∞ (a corrente cresce
de forma realística, não linear).

Topologias de núcleo suportadas
================================

* **TRIPLEX** (single-phase bank): 3 transformadores monofásicos
  com núcleos independentes. Não há acoplamento magnético entre
  fases. Zero-seq sem caminho preferencial (alta impedância).

* **THREE_LEG_STACKED**: 3 fases no mesmo núcleo com 3 pernas
  verticais + yokes superiores e inferiores. Zero-seq encontra
  alto-impedância (caminho de retorno via ar/tank).

* **FIVE_LEG_STACKED**: 3 pernas centrais + 2 pernas laterais
  para zero-sequência. Caminho de retorno baixa-impedância para
  zero-seq → mais sujeito a saturação assimétrica em GIC.

* **SHELL_FORM**: núcleo envoltório com pernas internas.
  Comportamento similar ao 5-leg para zero-seq.

MVP v0.27.5
============

* Test Report mode (entrada principal).
* Core types: TRIPLEX, THREE_LEG_STACKED, FIVE_LEG_STACKED.
* Saturação PWL (Frolich opcional via fitting offline).
* Pico de inrush estimado via modelo simplificado de Specht.
* Geração draft de cartões ATP via /BRANCH (formato similar
  a BCTRAN cascade).

Limitações conhecidas
======================

* **Design mode** e **Typical values mode** não cobertos no
  MVP — Test Report mode é prioritário.
* **Frolich fitting** automático é pesado (gradient method);
  MVP usa parâmetros fornecidos pelo usuário ou defaults
  típicos por classe de transformador.
* **Capacitâncias entre enrolamentos** simplificadas (apenas
  HV-LV; sem cross-couplings completos).
* **Frequency-dependent R(f)**: apenas DC (R_dc); skin effect
  fica para v0.27.5.5.

Referências
============

* B. A. Mork et al., "Parameter Estimation and Advanced
  Transformer Models for EMTP Simulations", Michigan
  Technological University Reports MTU4, MTU6, MTU7, BPA-
  funded (2002-2008).
* H. K. Høidalen et al., "Implementation and verification of
  the Hybrid Transformer Model in ATPDraw", EPRI 2007.
* IEEE Std C57.123-2002 (Guide for Transformer Loss
  Measurement).
* IEEE C37.91-2008 (Transformer Protection — relevante para
  estudos de coordenação 87T).
* H. W. Dommel, *EMTP Theory Book* §6.3 (BCTRAN matrix model).
* ATPDraw 7.7 Manual §5.7 (XFMR component dialog box).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class CoreType(str, Enum):
    """
    Topologias de núcleo suportadas pelo XFMR.

    Ref: ATPDraw §5.7 Type of core.
    """
    TRIPLEX = "TRIPLEX"                    # 3× monofásico (banco)
    THREE_LEG_STACKED = "THREE_LEG"        # 3 pernas, com yokes
    FIVE_LEG_STACKED = "FIVE_LEG"          # 3 pernas + 2 outer legs
    SHELL_FORM = "SHELL"                   # núcleo envoltório


class WindingConnection(str, Enum):
    """Conexões de enrolamento (mesmo subset usado em BCTRAN)."""
    WYE = "Y"           # estrela com neutro acessível
    WYE_GROUNDED = "Yg"  # estrela aterrada
    DELTA = "D"
    AUTO = "A"          # auto-transformador
    ZIGZAG = "Z"


class DataSource(str, Enum):
    """Fonte primária dos parâmetros."""
    TEST_REPORT = "test_report"
    DESIGN = "design"
    TYPICAL = "typical"


# ---------------------------------------------------------------------------
# Saturation curve (Frolich)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FrolichCoefficients:
    """
    Coeficientes da equação de Frolich (3-parâmetro):

    ::

        H = a · B / (b + B) · sign(B) + c · B

    Para B em Tesla e H em A/m. Coeficientes típicos para aço
    silício GO (grain-oriented):

    * a ≈ 50–200 A/m
    * b ≈ 0.5–1.5 T
    * c ≈ 5–50 A/m/T (slope linear de saturação extrema)

    Para test report fitting, ajusta-se a/b/c minimizando o
    erro RMS entre I_excitação medida e calculada.
    """
    a: float
    b: float
    c: float

    def H_of_B(self, B_T: float) -> float:
        """
        Avalia H(B) em A/m. Função ímpar (anti-simétrica):
        ``H(-B) = -H(B)``.
        """
        if B_T == 0.0:
            return 0.0
        sign = 1.0 if B_T > 0 else -1.0
        # |B| no termo principal + sign para preservar antisimetria
        return self.a * abs(B_T) / (self.b + abs(B_T)) * sign + self.c * B_T


# Defaults típicos para classes de núcleo (Mork et al.).
TYPICAL_FROLICH_BY_CLASS: dict[str, FrolichCoefficients] = {
    # Aço silício GO moderno (B_max ≈ 1.7 T nominal)
    "go_si_modern": FrolichCoefficients(a=120.0, b=1.0, c=20.0),
    # Aço silício GO antigo (1980s)
    "go_si_old": FrolichCoefficients(a=200.0, b=1.2, c=30.0),
    # Aço amorfo (para distribuição moderna)
    "amorphous": FrolichCoefficients(a=80.0, b=0.8, c=10.0),
}


@dataclass(frozen=True)
class SaturationCurvePoint:
    """
    Ponto da curva de saturação (excitação) — par (V_pu, I_pu).

    ATPDraw aceita até 9 pontos. Test report típico:

    * V/V_n = 1.00, I/I_n ≈ 0.5%
    * V/V_n = 1.05, I/I_n ≈ 0.7%
    * V/V_n = 1.10, I/I_n ≈ 1.5%
    * V/V_n = 1.15, I/I_n ≈ 5.0%
    * V/V_n = 1.20, I/I_n ≈ 20.0% (joelho)
    """
    voltage_pu: float
    current_pu: float
    losses_kW: Optional[float] = None  # opcional


# ---------------------------------------------------------------------------
# HybridTransformerParameters
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class HybridTransformerParameters:
    """
    Parâmetros do XFMR — modelo Hybrid Transformer Mork.

    MVP v0.27.5: Test Report mode com 2 enrolamentos (HV+LV).
    Tertiary winding e Design/Typical modes em sub-sprints.

    Attributes
    ----------
    name:
        Identificador interno (≤ 6 chars).
    nodes_hv, nodes_lv:
        Tuplas de 3 nós para os terminais HV e LV (3φ).
    rated_voltage_HV_kV, rated_voltage_LV_kV:
        Tensões nominais L-L (kV).
    rated_power_MVA:
        Potência nominal (MVA).
    frequency_Hz:
        Frequência nominal.
    connection_HV, connection_LV:
        Conexões dos enrolamentos.

    Test Report data (positive seq):

    uk_pos_pct:
        Tensão de curto-circuito % (uk%).
    p_load_kW:
        Perdas de carga em SC (kW).

    Test Report data (no-load, magnetization):

    saturation_curve:
        Pontos da curva de excitação (V_pu, I_pu, losses).
    p_no_load_kW:
        Perdas a vazio em V_n (kW).
    i_no_load_pct:
        Corrente de excitação em V_n (% de I_n).

    Core:

    core_type:
        Topologia (TRIPLEX, THREE_LEG, FIVE_LEG, SHELL).
    frolich:
        Coeficientes da equação de Frolich (None ⇒ usa default
        por classe).
    residual_flux_pu:
        Fluxo residual (key para inrush). Default 0 (zero); range
        típico ±0.8 pu.
    final_slope_inductance_pu:
        La (mH no formato ATP) — inductância final de saturação
        extrema. Crítica para inrush (Mork 2008).

    Capacitance (simplificado MVP):

    C_HV_to_ground_pF:
        Capacitância HV-terra (default 0).
    C_LV_to_ground_pF:
        Capacitância LV-terra (default 0).
    C_HV_LV_pF:
        Capacitância entre enrolamentos.
    """

    # Identificação + topologia
    name: str
    nodes_hv: tuple[str, str, str]
    nodes_lv: tuple[str, str, str]

    # Ratings
    rated_voltage_HV_kV: float
    rated_voltage_LV_kV: float
    rated_power_MVA: float
    frequency_Hz: float = 60.0

    # Conexões
    connection_HV: WindingConnection = WindingConnection.WYE_GROUNDED
    connection_LV: WindingConnection = WindingConnection.DELTA

    # Test report — short-circuit (load loss)
    uk_pos_pct: float = 10.0
    p_load_kW: float = 100.0

    # Test report — no-load (magnetization)
    saturation_curve: tuple[SaturationCurvePoint, ...] = field(
        default_factory=lambda: (
            SaturationCurvePoint(voltage_pu=0.95, current_pu=0.003, losses_kW=10.0),
            SaturationCurvePoint(voltage_pu=1.00, current_pu=0.005, losses_kW=15.0),
            SaturationCurvePoint(voltage_pu=1.05, current_pu=0.008, losses_kW=20.0),
            SaturationCurvePoint(voltage_pu=1.10, current_pu=0.020, losses_kW=30.0),
            SaturationCurvePoint(voltage_pu=1.15, current_pu=0.080, losses_kW=50.0),
            SaturationCurvePoint(voltage_pu=1.20, current_pu=0.250, losses_kW=80.0),
        )
    )
    p_no_load_kW: float = 15.0
    i_no_load_pct: float = 0.5

    # Core
    core_type: CoreType = CoreType.THREE_LEG_STACKED
    frolich: Optional[FrolichCoefficients] = None  # None ⇒ go_si_modern default
    residual_flux_pu: float = 0.0
    final_slope_inductance_pu: float = 0.04   # típico 3-leg

    # Capacitância (simplificado MVP)
    C_HV_to_ground_pF: float = 0.0
    C_LV_to_ground_pF: float = 0.0
    C_HV_LV_pF: float = 0.0

    # Metadata
    data_source: DataSource = DataSource.TEST_REPORT


# ---------------------------------------------------------------------------
# Estimativa de pico de inrush (Specht 1969 / Mork et al.)
# ---------------------------------------------------------------------------


def estimate_peak_inrush_current_kA(
    p: HybridTransformerParameters,
    flux_residual_pu: Optional[float] = None,
    closing_angle_deg: float = 0.0,
) -> dict:
    """
    Estima o pico de corrente de inrush (kA) usando o método
    simplificado de Specht (1969), adaptado por Mork.

    Cenário: energização do enrolamento ``HV`` com o LV em aberto
    no ângulo ``closing_angle_deg`` da onda de tensão. O pior caso
    é tipicamente em t=0 (zero crossing de V) com fluxo residual
    máximo do mesmo sinal.

    Princípio:

    1. Fluxo de regime permanente: φ_ss = √2·V / (ω·N).
    2. Fluxo no instante de fechamento: φ_0 = -φ_ss·cos(θ) +
       φ_residual (onde θ é o ângulo da tensão).
    3. Pico transitório: φ_max = 2·φ_ss·|cos(θ)| + |φ_res|.
    4. Para B_max correspondente, lê I da curva de saturação
       extrapolada por Frolich.

    Parameters
    ----------
    flux_residual_pu:
        Override do fluxo residual (default = p.residual_flux_pu).
    closing_angle_deg:
        Ângulo da tensão no instante de fechamento (graus).
        Pior caso = 0° (zero-crossing).

    Returns
    -------
    dict
        peak_inrush_kA: pico estimado.
        peak_inrush_pu: pico em pu (vs I nominal HV).
        flux_max_pu: fluxo máximo atingido.
        worst_case: True se closing_angle indica pior caso.
    """
    if flux_residual_pu is None:
        flux_residual_pu = p.residual_flux_pu

    theta_rad = math.radians(closing_angle_deg)
    cos_theta = math.cos(theta_rad)

    # Fluxo máximo transitório (em pu de φ_n)
    flux_max_pu = 2.0 * abs(cos_theta) + abs(flux_residual_pu)

    # Aproximação: usa o último ponto da curva de saturação +
    # extrapolação linear via final_slope_inductance.
    # Se flux_max ≤ último ponto da curva, interpola linearmente.
    # Se acima, usa La (final slope).

    sat_pts = sorted(p.saturation_curve, key=lambda pt: pt.voltage_pu)
    last_v = sat_pts[-1].voltage_pu
    last_i = sat_pts[-1].current_pu

    if flux_max_pu <= last_v:
        # Interpola na curva PWL
        i_pu = _interpolate_pwl(
            tuple((pt.voltage_pu, pt.current_pu) for pt in sat_pts),
            flux_max_pu,
        )
    else:
        # Extrapolação via La: ΔI = (flux_max - last_v) / La
        # (final_slope_inductance_pu é a inductância da reta após o joelho)
        delta_v = flux_max_pu - last_v
        i_pu = last_i + delta_v / p.final_slope_inductance_pu

    # I_base no lado HV (kA)
    i_base_HV_kA = (
        p.rated_power_MVA * 1.0e3
        / (math.sqrt(3.0) * p.rated_voltage_HV_kV)
    ) / 1.0e3  # kA

    peak_kA = i_pu * i_base_HV_kA

    return {
        "peak_inrush_kA": peak_kA,
        "peak_inrush_pu": i_pu,
        "flux_max_pu": flux_max_pu,
        "closing_angle_deg": closing_angle_deg,
        "worst_case": closing_angle_deg == 0.0 and flux_residual_pu >= 0,
        "i_base_HV_kA": i_base_HV_kA,
    }


def _interpolate_pwl(
    points: tuple[tuple[float, float], ...], x: float,
) -> float:
    """
    Interpolação linear PWL entre pontos (x, y) ordenados por x.

    Se x < x[0] ⇒ retorna y[0].
    Se x > x[-1] ⇒ retorna y[-1] (caller deve detectar e usar La).
    """
    if x <= points[0][0]:
        return points[0][1]
    if x >= points[-1][0]:
        return points[-1][1]
    for i in range(len(points) - 1):
        x0, y0 = points[i]
        x1, y1 = points[i + 1]
        if x0 <= x <= x1:
            t = (x - x0) / (x1 - x0)
            return y0 + t * (y1 - y0)
    return points[-1][1]


# ---------------------------------------------------------------------------
# Validador
# ---------------------------------------------------------------------------


def validate_xfmr(p: HybridTransformerParameters) -> list[str]:
    """
    Valida parâmetros do XFMR.

    Verifica:

    * Nome ≤ 6 chars.
    * Nós únicos (HV ≠ LV nas mesmas fases).
    * Voltagens > 0, S > 0, freq > 0.
    * uk% no range (1–25%).
    * Curva de saturação monotônica (V e I crescendo) e não-vazia.
    * Fluxo residual no range realístico (-0.95 a +0.95).
    * La > 0.
    """
    errors: list[str] = []

    if not p.name:
        errors.append("name vazio")
    elif len(p.name) > 6:
        errors.append(f"name {p.name!r} > 6 chars (limite ATP)")

    for attr in ("nodes_hv", "nodes_lv"):
        nodes = getattr(p, attr)
        if len(nodes) != 3:
            errors.append(f"{attr} deve ter 3 nós (achado {len(nodes)})")
        for n in nodes:
            if not n:
                errors.append(f"{attr} contém nó vazio")
            elif len(n) > 6:
                errors.append(f"{attr} contém nó >6 chars: {n!r}")

    # Detectar overlap HV/LV
    if set(p.nodes_hv) & set(p.nodes_lv):
        errors.append(
            "nodes_hv e nodes_lv compartilham nós — short circuit?"
        )

    if p.rated_voltage_HV_kV <= 0:
        errors.append(f"rated_voltage_HV_kV deve ser > 0")
    if p.rated_voltage_LV_kV <= 0:
        errors.append(f"rated_voltage_LV_kV deve ser > 0")
    if p.rated_voltage_HV_kV <= p.rated_voltage_LV_kV:
        errors.append(
            f"V_HV ({p.rated_voltage_HV_kV}) deve ser > "
            f"V_LV ({p.rated_voltage_LV_kV}) — convenção HV/LV"
        )
    if p.rated_power_MVA <= 0:
        errors.append("rated_power_MVA deve ser > 0")
    if p.frequency_Hz <= 0:
        errors.append("frequency_Hz deve ser > 0")

    if not (1.0 <= p.uk_pos_pct <= 25.0):
        errors.append(
            f"uk_pos_pct={p.uk_pos_pct} fora do range típico [1, 25]%"
        )

    if not p.saturation_curve:
        errors.append("saturation_curve vazia")
    else:
        # Monotonia
        prev_v, prev_i = -1.0, -1.0
        for pt in p.saturation_curve:
            if pt.voltage_pu <= prev_v:
                errors.append(
                    f"saturation_curve não-monotônica em V: "
                    f"{pt.voltage_pu} <= {prev_v}"
                )
                break
            if pt.current_pu < prev_i:
                errors.append(
                    f"saturation_curve não-monotônica em I: "
                    f"{pt.current_pu} < {prev_i}"
                )
                break
            prev_v, prev_i = pt.voltage_pu, pt.current_pu

    if not (-0.95 <= p.residual_flux_pu <= 0.95):
        errors.append(
            f"residual_flux_pu={p.residual_flux_pu} fora "
            "do range físico (-0.95, 0.95)"
        )

    if p.final_slope_inductance_pu <= 0:
        errors.append("final_slope_inductance_pu deve ser > 0")

    return errors


# ---------------------------------------------------------------------------
# Emissão de cartões ATP (formato draft)
# ---------------------------------------------------------------------------


def emit_xfmr_cards(p: HybridTransformerParameters) -> list[str]:
    """
    Emite cartões ATP draft para o XFMR.

    Formato MVP v0.27.5: documentação textual estruturada
    (mesma estratégia de BCTRAN/JMARTI). O strict ATP format
    depende do tipo de núcleo (cards Type-93 + Type-98 inductors
    + matrix BCTRAN-like) e fica para v0.27.5.5.

    Estrutura:

    ::

        C XFMR — Hybrid Transformer <name>
        C   Rated: V_HV/V_LV = X/Y kV, S = Z MVA, f = F Hz
        C   Connections: HV=<conn>, LV=<conn>
        C   Core type: <type>
        C   uk = <pct>%, p_load = <kW>
        C   No-load: i_0 = <pct>%, p_0 = <kW>
        C   Saturation curve (V_pu, I_pu, P_kW):
        C     ...
        C   Residual flux: <pu>
        C   Final slope La: <pu>
        C   Frolich coefs: a=<>, b=<>, c=<>
        C   Capacitances: C_HV_g=<pF>, C_LV_g=<pF>, C_HV_LV=<pF>
        C
        C [Cards Type-93/98 + matrix in v0.27.5.5]
    """
    errs = validate_xfmr(p)
    if errs:
        raise ValueError(
            f"HybridTransformerParameters {p.name!r} inválido: "
            + "; ".join(errs)
        )

    lines: list[str] = []
    lines.append(f"C XFMR — Hybrid Transformer {p.name}")
    lines.append(
        f"C   Rated: V_HV={p.rated_voltage_HV_kV:.2f} kV, "
        f"V_LV={p.rated_voltage_LV_kV:.2f} kV, "
        f"S={p.rated_power_MVA:.2f} MVA, f={p.frequency_Hz:.1f} Hz"
    )
    lines.append(
        f"C   Connections: HV={p.connection_HV.value}, "
        f"LV={p.connection_LV.value}"
    )
    lines.append(f"C   Core type: {p.core_type.value}")
    lines.append(
        f"C   Test report (SC): uk={p.uk_pos_pct:.2f}%, "
        f"P_load={p.p_load_kW:.2f} kW"
    )
    lines.append(
        f"C   Test report (NL): I_0={p.i_no_load_pct:.3f}%, "
        f"P_0={p.p_no_load_kW:.2f} kW"
    )
    lines.append("C   Saturation curve:")
    for pt in p.saturation_curve:
        loss = (
            f", P={pt.losses_kW:.2f} kW" if pt.losses_kW is not None else ""
        )
        lines.append(
            f"C     V/Vn={pt.voltage_pu:.3f}, "
            f"I/In={pt.current_pu:.4f}{loss}"
        )
    lines.append(f"C   Residual flux: {p.residual_flux_pu:+.3f} pu")
    lines.append(
        f"C   Final slope La: {p.final_slope_inductance_pu:.4f} pu"
    )
    if p.frolich:
        lines.append(
            f"C   Frolich: a={p.frolich.a:.2f} A/m, "
            f"b={p.frolich.b:.3f} T, c={p.frolich.c:.2f} A/m/T"
        )
    if any([p.C_HV_to_ground_pF, p.C_LV_to_ground_pF, p.C_HV_LV_pF]):
        lines.append(
            f"C   Caps: C_HVg={p.C_HV_to_ground_pF:.0f} pF, "
            f"C_LVg={p.C_LV_to_ground_pF:.0f} pF, "
            f"C_HV-LV={p.C_HV_LV_pF:.0f} pF"
        )

    # Cartões ATP simplificados (BCTRAN-style placeholder + Type-98 LNL).
    # Formato draft: para cada fase um BRANCH placeholder.
    lines.append("C")
    lines.append("C  ATP cards (draft format — strict in v0.27.5.5):")
    for i, phase in enumerate(("A", "B", "C")):
        n_h = p.nodes_hv[i].ljust(6)[:6]
        n_l = p.nodes_lv[i].ljust(6)[:6]
        lines.append(
            f"C  TR{p.name[:2]}{phase}: HV={n_h.strip()} LV={n_l.strip()}"
        )
        # Placeholder type 51 (mutual coupling) — refinar em v0.27.5.5
        lines.append(
            f"  {n_h}{n_l}                "
            f"{p.uk_pos_pct/100*p.rated_voltage_HV_kV**2/p.rated_power_MVA:>10.6f}"
            "       ; placeholder R-L type-51"
        )

    lines.append("C END XFMR " + p.name)
    return lines
