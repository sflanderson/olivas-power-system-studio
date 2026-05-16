"""
app.preprocessor.synchronous_machine — modelagem de máquinas
síncronas ATP MACHINE-59 (2 amortecedores) e MACHINE-58
(1 amortecedor).

Fundamento (Park 1929 + IEEE Std 115)
======================================

Manufacturers data caracterizam a máquina em quatro grupos:

* **Reatâncias d-axis** (pu): ``Xd`` (synchronous), ``Xd'``
  (transient), ``Xd''`` (subtransient), ``xL`` (stator leakage).
* **Reatâncias q-axis** (pu): ``Xq``, ``Xq'`` (apenas tipo 59),
  ``Xq''``.
* **Constantes de tempo curto-circuito** (s): ``Td'``, ``Td''``,
  ``Tq'`` (tipo 59), ``Tq''``.
* **Comuns**: ``Ra`` (armadura, pu), ``X0`` (zero-seq, pu),
  ``H`` (inércia, s — energia cinética em ωₛ / S_base),
  ``D`` (damping, pu·s/rad).

Conversão para parâmetros operacionais (Lambda values do ATP):

::

    Tdo' = Td' · (Xd / Xd')      (open-circuit transient)
    Tdo'' = Td'' · (Xd' / Xd'')  (open-circuit subtransient)
    L_d  = Xd / ωs               (henries; ωs = 2πf)
    Z_base = V_LL² / S_3φ        (ohms)
    I_pp = V / Xd''              (subtransient SC current, pu)

Estas relações são as do método clássico Concordia (1951) /
Anderson-Fouad (1977) e estão padronizadas no IEEE Std 115-2009.

Aplicações (memória do projeto)
================================

A SM59/58 é fundamental para:

* **TRT (Transient Recovery Voltage)**: o gerador é a fonte
  atrás do disjuntor; sem SM realista não há TRT.
* **Curto-circuito alimentado por gerador**: I_subtransient (Xd'')
  define o pico inicial de SC; decaimento via Td''/Td'.
* **Estabilidade transitória**: H define a constante de tempo
  mecânica do oscilatório eletromecânico.
* **Inrush sympathetic**: trafo conectado próximo ao gerador
  vê impedância subtransitória; importante em energização.

MVP v0.27.0 — escopo
====================

* SM59 (2 amortecedores) e SM58 (1 amortecedor — q-axis sem
  transitório).
* Inicialização automática (auto-init via ATP steady-state) ou
  manual via P0/Q0/V0/ang0.
* Sem multi-mass (rotor único). SSR/torsional fica para v0.27.5.
* Sem exciter/governor — components separados em v0.27.6.
* Sem saturação curve. Adicionada via LNL externa em v0.27.0.5.

Limitações conhecidas:

* Strict ATP card format (column-precise) ainda em draft —
  mesmo padrão de JMARTI .pch e BCTRAN cards.
* Apenas conexão Y-grounded ou Y com neutro acessível.

Referências
============

* P. M. Anderson, A. A. Fouad, *Power System Control and
  Stability*, 2ed §4.
* IEEE Std 115-2009 (test procedures for synchronous machines).
* P. Kundur, *Power System Stability and Control*, §3 (machine
  representation).
* ATP Rule Book vol 2, Section VIII (synchronous machines).
"""

from __future__ import annotations

import math
from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Dados primários
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SynchronousMachineParameters:
    """
    Parâmetros de máquina síncrona em manufacturers data.

    Convenção
    ---------

    * Reatâncias em **pu** na base ``S_3φ`` / ``V_LL``.
    * Constantes de tempo em **segundos**.
    * Inércia ``H`` em **segundos** (energia cinética em
      velocidade síncrona dividida por S_base).
    * Tipo 58 selecionado automaticamente quando ``Xq_prime = 0``.

    Attributes
    ----------
    name:
        Identificador interno (≤ 6 chars).
    node_a, node_b, node_c:
        Terminais de armadura (≤ 6 chars).
    node_neutral:
        Neutro acessível (vazio ⇒ Y-grounded internamente).
    rated_voltage_kV:
        Tensão nominal linha-linha (kV).
    rated_power_MVA:
        Potência nominal aparente (MVA).
    frequency_Hz:
        Frequência nominal (Hz). Default 60.
    n_poles:
        Número de polos (par, ≥ 2). Default 2.
    Xd, Xd_prime, Xd_pp:
        Reatâncias d-axis: síncrona, transitória, subtransitória (pu).
    Td_prime, Td_pp:
        Constantes de tempo de curto-circuito d-axis (s).
    Xq, Xq_prime, Xq_pp:
        Reatâncias q-axis (pu). Xq_prime=0 seleciona tipo 58.
    Tq_prime, Tq_pp:
        Constantes de tempo de curto-circuito q-axis (s).
    Ra, xL, X0:
        Resistência de armadura, dispersão de estator, zero-seq (pu).
    H, D:
        Inércia (s) e coef. damping mecânico (pu·s/rad).
    P0_MW, Q0_MVAr, V0_pu, angle0_deg:
        Estado inicial (preferência usuário). ATP pode auto-init.
    """

    # Identificação + topologia
    name: str
    node_a: str
    node_b: str
    node_c: str
    node_neutral: str = ""

    # Ratings
    rated_voltage_kV: float = 13.8
    rated_power_MVA: float = 100.0
    frequency_Hz: float = 60.0
    n_poles: int = 2

    # d-axis (pu)
    Xd: float = 1.80
    Xd_prime: float = 0.30
    Xd_pp: float = 0.20
    Td_prime: float = 0.80
    Td_pp: float = 0.030

    # q-axis (pu)
    Xq: float = 1.70
    Xq_prime: float = 0.55     # 0 ⇒ tipo 58
    Xq_pp: float = 0.20
    Tq_prime: float = 0.40
    Tq_pp: float = 0.050

    # Comuns (pu)
    Ra: float = 0.003
    xL: float = 0.15
    X0: float = 0.05

    # Mecânica
    H: float = 3.0
    D: float = 0.0

    # Inicialização
    P0_MW: float = 0.0
    Q0_MVAr: float = 0.0
    V0_pu: float = 1.0
    angle0_deg: float = 0.0


# ---------------------------------------------------------------------------
# Conversões e métricas derivadas
# ---------------------------------------------------------------------------


def base_impedance_ohm(
    rated_voltage_kV: float, rated_power_MVA: float,
) -> float:
    """
    Impedância base (3φ): ``Z_base = V_LL² / S_3φ`` em ohms.

    Para conversão pu → SI: ``Z_SI = Z_pu · Z_base``.
    """
    if rated_voltage_kV <= 0 or rated_power_MVA <= 0:
        raise ValueError(
            f"V_LL ({rated_voltage_kV}) e S_3φ ({rated_power_MVA}) "
            "devem ser > 0"
        )
    return (rated_voltage_kV * 1.0e3) ** 2 / (rated_power_MVA * 1.0e6)


def synchronous_speed_rpm(frequency_Hz: float, n_poles: int) -> float:
    """``n_s = 120·f / poles`` (rpm)."""
    return 120.0 * frequency_Hz / n_poles


def operational_parameters(p: SynchronousMachineParameters) -> dict:
    """
    Converte manufacturers data para operational/Lambda parameters
    usados internamente pelo ATP.

    Identidades clássicas (Anderson-Fouad §4.6):

    * ``Tdo' = Td' · Xd / Xd'`` (open-circuit transient)
    * ``Tdo'' = Td'' · Xd' / Xd''`` (open-circuit subtransient)
    * Idem para q-axis.

    Returns
    -------
    dict
        Chaves: omega_s, Z_base, Tdo_prime, Tdo_pp, Tqo_prime,
        Tqo_pp, n_s_rpm, is_type_59.
    """
    omega_s = 2.0 * math.pi * p.frequency_Hz
    z_base = base_impedance_ohm(p.rated_voltage_kV, p.rated_power_MVA)
    n_s_rpm = synchronous_speed_rpm(p.frequency_Hz, p.n_poles)
    is_type_59 = p.Xq_prime > 0.0

    Tdo_prime = (
        p.Td_prime * (p.Xd / p.Xd_prime) if p.Xd_prime > 0 else 0.0
    )
    Tdo_pp = (
        p.Td_pp * (p.Xd_prime / p.Xd_pp) if p.Xd_pp > 0 else 0.0
    )
    if is_type_59:
        Tqo_prime = p.Tq_prime * (p.Xq / p.Xq_prime)
        Tqo_pp = p.Tq_pp * (p.Xq_prime / p.Xq_pp) if p.Xq_pp > 0 else 0.0
    else:
        Tqo_prime = 0.0
        Tqo_pp = p.Tq_pp * (p.Xq / p.Xq_pp) if p.Xq_pp > 0 else 0.0

    return {
        "omega_s": omega_s,
        "Z_base": z_base,
        "n_s_rpm": n_s_rpm,
        "Tdo_prime": Tdo_prime,
        "Tdo_pp": Tdo_pp,
        "Tqo_prime": Tqo_prime,
        "Tqo_pp": Tqo_pp,
        "is_type_59": is_type_59,
    }


def short_circuit_currents(
    p: SynchronousMachineParameters,
    v_prefault_pu: float = 1.0,
    time_s: float = 0.0,
) -> dict:
    """
    Correntes de curto-circuito trifásico simétrico (pu) em
    diferentes regimes — útil para validação manual e
    pré-cálculo de TRT/seletividade.

    Decomposição clássica:

    ::

        I(t) = (I'' - I') · exp(-t/Td'')
             + (I' - Iss) · exp(-t/Td')
             + Iss

    Componentes DC (offset assimétrico) **não** são incluídos —
    aqui apenas a envoltória simétrica AC.

    Parameters
    ----------
    v_prefault_pu:
        Tensão pré-falta na armadura (pu). Default 1.0.
    time_s:
        Instante após o curto (s). Default 0 = subtransitório puro.

    Returns
    -------
    dict
        I_subtransient_pu, I_transient_pu, I_steady_state_pu,
        I_at_t_pu, I_subtransient_kA (em SI), time_s.
    """
    if v_prefault_pu < 0:
        raise ValueError(f"v_prefault_pu deve ser >= 0 (achado {v_prefault_pu})")
    if time_s < 0:
        raise ValueError(f"time_s deve ser >= 0 (achado {time_s})")

    I_pp = v_prefault_pu / p.Xd_pp
    I_p = v_prefault_pu / p.Xd_prime
    I_ss = v_prefault_pu / p.Xd

    if time_s == 0.0:
        I_t = I_pp
    else:
        I_t = (
            (I_pp - I_p) * math.exp(-time_s / p.Td_pp)
            + (I_p - I_ss) * math.exp(-time_s / p.Td_prime)
            + I_ss
        )

    # Conversão para SI:
    # I_base = S / (sqrt(3) · V_LL) em A
    I_base_A = (p.rated_power_MVA * 1.0e6) / (
        math.sqrt(3.0) * p.rated_voltage_kV * 1.0e3
    )
    return {
        "I_subtransient_pu": I_pp,
        "I_transient_pu": I_p,
        "I_steady_state_pu": I_ss,
        "I_at_t_pu": I_t,
        "I_subtransient_kA": I_pp * I_base_A / 1.0e3,
        "I_transient_kA": I_p * I_base_A / 1.0e3,
        "I_steady_state_kA": I_ss * I_base_A / 1.0e3,
        "I_at_t_kA": I_t * I_base_A / 1.0e3,
        "I_base_A": I_base_A,
        "time_s": time_s,
    }


# ---------------------------------------------------------------------------
# Validador
# ---------------------------------------------------------------------------


def validate_sm(p: SynchronousMachineParameters) -> list[str]:
    """
    Valida parâmetros da SM. Retorna lista de erros (vazia ⇒ ok).

    Verifica:

    * Nomes (não-vazios, ≤ 6 chars).
    * Ratings positivos, n_poles par e ≥ 2.
    * **Hierarquia d-axis**: ``Xd > Xd' > Xd'' > xL > 0``
      (consistência física — viola = dados inconsistentes).
    * **Hierarquia q-axis**: tipo 59 ⇒ ``Xq > Xq' > Xq''``;
      tipo 58 ⇒ ``Xq > Xq''``.
    * Constantes de tempo positivas e ``Td' > Td''``.
    * Ra ≥ 0, X0 > 0, H > 0.
    """
    errors: list[str] = []

    # Nome / nós
    if not p.name:
        errors.append("name vazio")
    elif len(p.name) > 6:
        errors.append(f"name {p.name!r} > 6 chars (limite ATP)")
    for attr in ("node_a", "node_b", "node_c"):
        v = getattr(p, attr)
        if not v:
            errors.append(f"{attr} vazio")
        elif len(v) > 6:
            errors.append(f"{attr} {v!r} > 6 chars (limite ATP)")
    if p.node_neutral and len(p.node_neutral) > 6:
        errors.append(f"node_neutral {p.node_neutral!r} > 6 chars")

    # Ratings
    if p.rated_voltage_kV <= 0:
        errors.append(
            f"rated_voltage_kV deve ser > 0 (achado {p.rated_voltage_kV})"
        )
    if p.rated_power_MVA <= 0:
        errors.append(
            f"rated_power_MVA deve ser > 0 (achado {p.rated_power_MVA})"
        )
    if p.frequency_Hz <= 0:
        errors.append(
            f"frequency_Hz deve ser > 0 (achado {p.frequency_Hz})"
        )
    if p.n_poles < 2 or p.n_poles % 2 != 0:
        errors.append(
            f"n_poles deve ser par e ≥ 2 (achado {p.n_poles})"
        )

    # Hierarquia d-axis
    if not (p.Xd > p.Xd_prime > p.Xd_pp > p.xL > 0):
        errors.append(
            f"Hierarquia d-axis violada: Xd={p.Xd}, Xd'={p.Xd_prime}, "
            f"Xd''={p.Xd_pp}, xL={p.xL}. "
            "Esperado Xd > Xd' > Xd'' > xL > 0."
        )

    # Hierarquia q-axis
    if p.Xq <= 0:
        errors.append(f"Xq deve ser > 0 (achado {p.Xq})")
    if p.Xq_pp <= 0:
        errors.append(f"Xq'' deve ser > 0 (achado {p.Xq_pp})")
    if p.Xq_prime > 0:
        if not (p.Xq > p.Xq_prime > p.Xq_pp):
            errors.append(
                f"Hierarquia q-axis (tipo 59) violada: Xq={p.Xq}, "
                f"Xq'={p.Xq_prime}, Xq''={p.Xq_pp}. "
                "Esperado Xq > Xq' > Xq''."
            )
    else:
        if not (p.Xq > p.Xq_pp):
            errors.append(
                f"q-axis (tipo 58) violada: Xq={p.Xq}, Xq''={p.Xq_pp}. "
                "Esperado Xq > Xq''."
            )

    # Constantes de tempo
    if p.Td_prime <= 0:
        errors.append(f"Td' deve ser > 0 (achado {p.Td_prime})")
    if p.Td_pp <= 0:
        errors.append(f"Td'' deve ser > 0 (achado {p.Td_pp})")
    if p.Td_prime <= p.Td_pp:
        errors.append(
            f"Td' ({p.Td_prime}) deve ser > Td'' ({p.Td_pp})"
        )
    if p.Tq_pp <= 0:
        errors.append(f"Tq'' deve ser > 0 (achado {p.Tq_pp})")
    if p.Xq_prime > 0 and p.Tq_prime <= 0:
        errors.append(
            f"Tq' deve ser > 0 quando Xq' > 0 (tipo 59). "
            f"Achado Tq' = {p.Tq_prime}"
        )

    # Outros
    if p.Ra < 0:
        errors.append(f"Ra deve ser >= 0 (achado {p.Ra})")
    if p.X0 <= 0:
        errors.append(f"X0 deve ser > 0 (achado {p.X0})")
    if p.H <= 0:
        errors.append(f"H deve ser > 0 (achado {p.H})")
    if p.D < 0:
        errors.append(f"D deve ser >= 0 (achado {p.D})")

    # Sanity: V0 positivo
    if p.V0_pu < 0:
        errors.append(f"V0_pu deve ser >= 0 (achado {p.V0_pu})")

    return errors


# ---------------------------------------------------------------------------
# Emissão de cartões MACHINE-59 / MACHINE-58
# ---------------------------------------------------------------------------


def emit_sm_cards(p: SynchronousMachineParameters) -> list[str]:
    """
    Emite cartões ATP MACHINE-59 (ou 58) no formato draft v0.27.0.

    Estrutura:

    ::

        C MACHINE 59 — Synchronous Machine <name>
        C   Rated: V_LL=<V> kV, S=<S> MVA, f=<f> Hz, poles=<p>
        C   d-axis: Xd, Xd', Xd'', Td', Td''
        C   q-axis: Xq, Xq', Xq'', Tq', Tq''   (ou simplificado em tipo 58)
        C   Common: Ra, xL, X0
        C   Mech:   H, D
        C   Init:   P0, Q0, V0, ang0
        C   Z_base = <Ω>
        59<NODEA><NODEB><NODEC><NODEN>     V_LL=…kV S=…MVA
           <Xd>     <Xd'>    <Xd''>   <Td'>    <Td''>     ; d-axis
           <Xq>     <Xq'>    <Xq''>   <Tq'>    <Tq''>     ; q-axis
           <Ra>     <xL>     <X0>     <H>      <D>        ; common+mech
           <P0>     <Q0>     <V0>     <ang0>              ; init
        BLANK card terminating MACHINE

    Item com configuração inválida levanta ``ValueError``.

    Returns
    -------
    list[str]
        Linhas (sem terminador ``\\n``).
    """
    errs = validate_sm(p)
    if errs:
        raise ValueError(
            f"SynchronousMachineParameters {p.name!r} inválida: "
            + "; ".join(errs)
        )

    op = operational_parameters(p)
    type_code = "59" if op["is_type_59"] else "58"

    # v0.28.4-PRO Onda 4.1: usa atp_format helpers para campos
    # column-precise (6 chars cada).
    from app.preprocessor.atp_format import fmt_node, fmt_num
    a = fmt_node(p.node_a)
    b = fmt_node(p.node_b)
    c = fmt_node(p.node_c)
    n = fmt_node(p.node_neutral) if p.node_neutral else "      "

    lines: list[str] = []
    lines.append(
        f"C MACHINE {type_code} — Synchronous Machine {p.name}"
    )
    lines.append(
        f"C   Rated: V_LL = {p.rated_voltage_kV:.3f} kV, "
        f"S = {p.rated_power_MVA:.3f} MVA, "
        f"f = {p.frequency_Hz:.2f} Hz, poles = {p.n_poles}"
    )
    lines.append(
        f"C   Speed: n_s = {op['n_s_rpm']:.2f} rpm, "
        f"ω_s = {op['omega_s']:.4f} rad/s"
    )
    lines.append(
        f"C   d-axis: Xd = {p.Xd:.4f}, Xd' = {p.Xd_prime:.4f}, "
        f"Xd'' = {p.Xd_pp:.4f}, Td' = {p.Td_prime:.4f}s, "
        f"Td'' = {p.Td_pp:.4f}s"
    )
    if op["is_type_59"]:
        lines.append(
            f"C   q-axis: Xq = {p.Xq:.4f}, Xq' = {p.Xq_prime:.4f}, "
            f"Xq'' = {p.Xq_pp:.4f}, Tq' = {p.Tq_prime:.4f}s, "
            f"Tq'' = {p.Tq_pp:.4f}s"
        )
    else:
        lines.append(
            f"C   q-axis (tipo 58): Xq = {p.Xq:.4f}, "
            f"Xq'' = {p.Xq_pp:.4f}, Tq'' = {p.Tq_pp:.4f}s"
        )
    lines.append(
        f"C   Open-circuit T: Tdo' = {op['Tdo_prime']:.4f}s, "
        f"Tdo'' = {op['Tdo_pp']:.4f}s"
    )
    lines.append(
        f"C   Common: Ra = {p.Ra:.4f}, xL = {p.xL:.4f}, "
        f"X0 = {p.X0:.4f} (pu)"
    )
    lines.append(
        f"C   Mech:   H = {p.H:.3f} s, D = {p.D:.4f} pu"
    )
    lines.append(
        f"C   Init:   P0 = {p.P0_MW:.3f} MW, "
        f"Q0 = {p.Q0_MVAr:.3f} MVAr, "
        f"V0 = {p.V0_pu:.4f} pu, ang0 = {p.angle0_deg:.2f}°"
    )
    lines.append(
        f"C   Z_base = {op['Z_base']:.4f} Ω"
    )

    # v0.28.4-PRO Onda 4.1: cartões em strict fixed-format
    # ATP Rule Book Vol 2 §VIII.1 (MACHINE-58/59):
    # Type code (cols 1-2) + 4 nodes (3-26) + ratings em cols 27-66.
    # Cada campo numérico 10 chars consistente.
    main_card = (
        f"{type_code:<2s}{a}{b}{c}{n}"
        f"{fmt_num(p.rated_voltage_kV * 1000.0, 10)}"  # V_LL em V
        f"{fmt_num(p.rated_power_MVA * 1.0e6, 10)}"     # S em VA
        f"{fmt_num(p.frequency_Hz, 10)}"
        f"{fmt_num(float(p.n_poles), 10)}"
    )
    lines.append(main_card.rstrip())

    # d-axis: 5 campos × 10 chars = 50 chars (cols 3-52)
    lines.append(
        "  "  # type continuation (2 spaces)
        f"{fmt_num(p.Xd, 10)}{fmt_num(p.Xd_prime, 10)}"
        f"{fmt_num(p.Xd_pp, 10)}{fmt_num(p.Td_prime, 10)}"
        f"{fmt_num(p.Td_pp, 10)}"
    )
    # q-axis
    if op["is_type_59"]:
        lines.append(
            "  "
            f"{fmt_num(p.Xq, 10)}{fmt_num(p.Xq_prime, 10)}"
            f"{fmt_num(p.Xq_pp, 10)}{fmt_num(p.Tq_prime, 10)}"
            f"{fmt_num(p.Tq_pp, 10)}"
        )
    else:
        lines.append(
            "  "
            f"{fmt_num(p.Xq, 10)}{fmt_num(0.0, 10)}"
            f"{fmt_num(p.Xq_pp, 10)}{fmt_num(0.0, 10)}"
            f"{fmt_num(p.Tq_pp, 10)}"
        )
    # common + mech
    lines.append(
        "  "
        f"{fmt_num(p.Ra, 10)}{fmt_num(p.xL, 10)}"
        f"{fmt_num(p.X0, 10)}{fmt_num(p.H, 10)}"
        f"{fmt_num(p.D, 10)}"
    )
    # init
    lines.append(
        "  "
        f"{fmt_num(p.P0_MW, 10)}{fmt_num(p.Q0_MVAr, 10)}"
        f"{fmt_num(p.V0_pu, 10)}{fmt_num(p.angle0_deg, 10)}"
    )
    # Comentário documentando a estrutura (após cards strict)
    lines.append(
        "C ^ MACHINE-{0}: 1=main, 2=d-axis, 3=q-axis, "
        "4=common, 5=init.".format(type_code)
    )
    lines.append("BLANK card terminating MACHINE")
    return lines


def emit_sm_text(p: SynchronousMachineParameters) -> str:
    """Atalho: ``"\\n".join(emit_sm_cards(p)) + "\\n"``."""
    return "\n".join(emit_sm_cards(p)) + "\n"


# ---------------------------------------------------------------------------
# Helpers de construção / templates típicos
# ---------------------------------------------------------------------------


def make_default_hydro_generator(
    name: str, node_a: str, node_b: str, node_c: str,
    rated_voltage_kV: float, rated_power_MVA: float,
) -> SynchronousMachineParameters:
    """
    Helper: gerador hidrelétrico salient-pole típico (parâmetros
    representativos de Itaipu/Tucuruí scale).

    Reatâncias típicas (Anderson-Fouad Table 4.2 — hydro):
    ``Xd≈1.0, Xd'≈0.30, Xd''≈0.20, Xq≈0.65, Xq''≈0.20``.
    Inércia ``H≈3.0–4.0 s``.
    """
    return SynchronousMachineParameters(
        name=name,
        node_a=node_a, node_b=node_b, node_c=node_c,
        rated_voltage_kV=rated_voltage_kV,
        rated_power_MVA=rated_power_MVA,
        Xd=1.00, Xd_prime=0.30, Xd_pp=0.20,
        Td_prime=1.10, Td_pp=0.040,
        Xq=0.65, Xq_prime=0.0,        # salient pole ⇒ tipo 58
        Xq_pp=0.20, Tq_pp=0.080,
        Ra=0.003, xL=0.15, X0=0.06,
        H=3.5, D=0.0,
    )


def make_default_thermal_generator(
    name: str, node_a: str, node_b: str, node_c: str,
    rated_voltage_kV: float, rated_power_MVA: float,
) -> SynchronousMachineParameters:
    """
    Helper: gerador térmico round-rotor típico (turbo-gerador a
    vapor/gás scale 100-1000 MVA).

    Reatâncias típicas (Anderson-Fouad Table 4.2 — round-rotor):
    ``Xd≈1.8, Xd'≈0.30, Xd''≈0.20, Xq≈1.7, Xq'≈0.55, Xq''≈0.20``.
    Inércia ``H≈3.0–6.0 s``.
    """
    return SynchronousMachineParameters(
        name=name,
        node_a=node_a, node_b=node_b, node_c=node_c,
        rated_voltage_kV=rated_voltage_kV,
        rated_power_MVA=rated_power_MVA,
        Xd=1.80, Xd_prime=0.30, Xd_pp=0.20,
        Td_prime=0.80, Td_pp=0.030,
        Xq=1.70, Xq_prime=0.55, Xq_pp=0.20,
        Tq_prime=0.40, Tq_pp=0.050,
        Ra=0.003, xL=0.15, X0=0.05,
        H=4.0, D=0.0,
    )
