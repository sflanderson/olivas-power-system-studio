"""
app.preprocessor.tacs_interface — interface TACS↔EMTP.

Estabelece a ponte bidirecional entre o solver eletromagnético
principal e o bloco TACS:

* **Lado EMTP → TACS** (medição): ``TacsMeasuring`` representa
  uma medição de tensão (V) ou corrente (I) num nó/ramo do
  circuito que é exposta como sinal TACS de entrada.
* **Lado TACS → EMTP** (atuação):
    * ``TacsControlledSource`` — fonte de tensão/corrente cujo
      valor é atualizado a cada Δt pelo sinal TACS.
    * ``TacsControlledSwitch`` — chave que abre/fecha conforme
      um sinal lógico TACS (cross do threshold).

Cada classe tem ``validate_*`` (verifica nomes, ≤ 6 chars,
nós distintos quando aplicável) e ``emit_*_lines`` (texto
draft com comentário ``C `` + cartão device approx-ATP).

Limitação MVP v0.26.4
---------------------

* Formato draft legível (comentários ``C `` + cartões em
  colunas livres). Strict fixed-column ATP fica para refinamento.
* Atualmente, MEASURING e TACS source/switch são objetos
  programáticos — ainda não há .ocomp specs no catálogo (chega
  em v0.26.5).

Referências
-----------

* ATP Rule Book vol 2, §V.6 (TACS-EMTP interface).
* H. W. Dommel, *EMTP Theory Book*, §14.7 (TACS-circuit coupling).
"""

from __future__ import annotations

from dataclasses import dataclass


# ---------------------------------------------------------------------------
# TacsMeasuring (EMTP → TACS): voltage probe / current probe
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TacsMeasuring:
    """
    Probe que extrai uma grandeza elétrica do circuito e a fornece
    como sinal TACS.

    Tipos
    -----
    * ``"V"`` — tensão entre ``node1`` e ``node2``. Para tensão de
      fase, ``node2`` = GND (string vazia).
    * ``"I"`` — corrente que entra em ``node1`` e sai em ``node2``
      através de um branch implícito de impedância nula. Útil para
      proteção, MPPT current-mode, etc.

    Attributes
    ----------
    name:
        Identificador interno (≤ 6 chars).
    node1, node2:
        Nós do circuito (≤ 6 chars; ``""`` = GND).
    output_signal:
        Nome do sinal TACS resultante (≤ 6 chars).
    measurement_type:
        ``"V"`` ou ``"I"``.
    """

    name: str
    node1: str
    node2: str
    output_signal: str
    measurement_type: str  # "V" ou "I"


def validate_measuring(m: TacsMeasuring) -> list[str]:
    """Retorna lista de erros."""
    errors: list[str] = []
    for attr in ("name", "output_signal"):
        v = getattr(m, attr)
        if not v:
            errors.append(f"{attr} vazio")
        elif len(v) > 6:
            errors.append(f"{attr} {v!r} > 6 chars (limite ATP)")
    # node1/node2 podem ser vazios (GND), mas se setados devem ≤ 6.
    for attr in ("node1", "node2"):
        v = getattr(m, attr)
        if v and len(v) > 6:
            errors.append(f"{attr} {v!r} > 6 chars (limite ATP)")
    if m.measurement_type not in ("V", "I"):
        errors.append(
            f"measurement_type inválido: {m.measurement_type!r} "
            "(deve ser 'V' ou 'I')"
        )
    if m.measurement_type == "I" and m.node1 == m.node2:
        errors.append(
            "measurement_type 'I' exige node1 != node2"
        )
    return errors


def emit_measuring_lines(m: TacsMeasuring) -> list[str]:
    """
    Linhas draft para um probe MEASURING.

    Formato (V):

    ::

        C  TACS Measuring V: <output> = V(<node1>) - V(<node2>)
        90<output>    <node1>    <node2>    type=V

    Formato (I):

    ::

        C  TACS Measuring I: <output> = I[<node1> -> <node2>]
        91<output>    <node1>    <node2>    type=I
    """
    out_p = m.output_signal.ljust(6)[:6]
    n1 = m.node1.ljust(6)[:6] if m.node1 else "GND   "
    n2 = m.node2.ljust(6)[:6] if m.node2 else "GND   "
    if m.measurement_type == "V":
        return [
            f"C  TACS Measuring V: {m.output_signal} = "
            f"V({m.node1 or 'GND'}) - V({m.node2 or 'GND'})",
            f"90{out_p}    {n1}    {n2}    type=V",
        ]
    # current
    return [
        f"C  TACS Measuring I: {m.output_signal} = "
        f"I[{m.node1} -> {m.node2}]",
        f"91{out_p}    {n1}    {n2}    type=I",
    ]


# ---------------------------------------------------------------------------
# TacsControlledSource (TACS → EMTP): SOURCE TYPE-13 (V) ou TYPE-14 (I)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TacsControlledSource:
    """
    Fonte de tensão (TYPE-13) ou corrente (TYPE-14) cujo valor
    é fornecido pelo sinal TACS ``control_signal`` a cada Δt.

    Substitui as fontes type-1/14 estáticas quando se quer um
    waveform arbitrário gerado por lógica TACS (PWM, modulação
    SPWM/SVM, set-point de droop control etc.).

    Attributes
    ----------
    name:
        Identificador interno (≤ 6 chars).
    node:
        Nó onde a fonte injeta. O outro terminal é GND implícito.
    control_signal:
        Nome do sinal TACS (≤ 6 chars) que define o valor.
    source_type:
        ``"V"`` (TYPE-13 — tensão) ou ``"I"`` (TYPE-14 —
        corrente).
    t_start, t_stop:
        Janela de ativação (s). Default ``[-1, 1e9]`` = sempre.
    """

    name: str
    node: str
    control_signal: str
    source_type: str  # "V" ou "I"
    t_start: float = -1.0
    t_stop: float = 1.0e9


def validate_controlled_source(s: TacsControlledSource) -> list[str]:
    """Retorna lista de erros."""
    errors: list[str] = []
    for attr in ("name", "control_signal"):
        v = getattr(s, attr)
        if not v:
            errors.append(f"{attr} vazio")
        elif len(v) > 6:
            errors.append(f"{attr} {v!r} > 6 chars (limite ATP)")
    if not s.node:
        errors.append("node vazio")
    elif len(s.node) > 6:
        errors.append(f"node {s.node!r} > 6 chars (limite ATP)")
    if s.source_type not in ("V", "I"):
        errors.append(
            f"source_type inválido: {s.source_type!r} "
            "(deve ser 'V' ou 'I')"
        )
    if s.t_start >= s.t_stop:
        errors.append(
            f"t_start ({s.t_start}) >= t_stop ({s.t_stop})"
        )
    return errors


def emit_controlled_source_lines(s: TacsControlledSource) -> list[str]:
    """
    Linhas draft para uma fonte TACS-controlled.

    TYPE-13 (V):

    ::

        C  TACS Source V: V(<node>) = <control_signal>(t)
        13<node>      <control_signal>    Tstart=<t0> Tstop=<t1>

    TYPE-14 (I):

    ::

        C  TACS Source I: I(<node>) = <control_signal>(t)
        14<node>      <control_signal>    Tstart=<t0> Tstop=<t1>
    """
    n = s.node.ljust(6)[:6]
    sig = s.control_signal.ljust(6)[:6]
    type_code = "13" if s.source_type == "V" else "14"
    desc = "V" if s.source_type == "V" else "I"
    summary = (
        f"C  TACS Source {desc}: {desc}({s.node}) = {s.control_signal}(t)"
    )
    card = (
        f"{type_code}{n}    {sig}    "
        f"Tstart={_fmt(s.t_start)} Tstop={_fmt(s.t_stop)}"
    )
    return [summary, card]


# ---------------------------------------------------------------------------
# TacsControlledSwitch (TACS → EMTP): SWITCH TYPE-13
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TacsControlledSwitch:
    """
    Chave cuja transição open/close é determinada pelo cruzamento
    de ``control_signal`` com ``threshold``.

    Comportamento (default):

    * ``control_signal > threshold`` ⇒ chave **fechada**.
    * ``control_signal ≤ threshold`` ⇒ chave **aberta**.

    Use ``threshold`` para ajustar o nível lógico (ex: 0.5 para
    sinal binário 0/1, 0.0 para sinal +1/-1 simétrico).

    Attributes
    ----------
    name:
        Identificador interno (≤ 6 chars).
    node1, node2:
        Terminais da chave (≤ 6 chars; devem ser distintos).
    control_signal:
        Nome do sinal TACS (≤ 6 chars).
    threshold:
        Limiar de comparação (default 0.5 → binário 0/1).
    initial_state:
        Estado em t = 0 — ``False`` = aberta, ``True`` = fechada.
    """

    name: str
    node1: str
    node2: str
    control_signal: str
    threshold: float = 0.5
    initial_state: bool = False


def validate_controlled_switch(sw: TacsControlledSwitch) -> list[str]:
    """Retorna lista de erros."""
    errors: list[str] = []
    for attr in ("name", "control_signal"):
        v = getattr(sw, attr)
        if not v:
            errors.append(f"{attr} vazio")
        elif len(v) > 6:
            errors.append(f"{attr} {v!r} > 6 chars (limite ATP)")
    for attr in ("node1", "node2"):
        v = getattr(sw, attr)
        if not v:
            errors.append(f"{attr} vazio")
        elif len(v) > 6:
            errors.append(f"{attr} {v!r} > 6 chars (limite ATP)")
    if sw.node1 and sw.node2 and sw.node1 == sw.node2:
        errors.append(
            f"node1 == node2 ({sw.node1!r}) — chave degenerada"
        )
    return errors


def emit_controlled_switch_lines(sw: TacsControlledSwitch) -> list[str]:
    """
    Linhas draft para uma SWITCH controlada por TACS (TYPE-13).

    Formato:

    ::

        C  TACS Switch: <node1>--<node2> closed when <signal> > <threshold>
        C  initial_state = <open|closed>
        13<n1><n2>     <control_signal>    threshold = <th>
    """
    n1 = sw.node1.ljust(6)[:6]
    n2 = sw.node2.ljust(6)[:6]
    sig = sw.control_signal.ljust(6)[:6]
    state_word = "closed" if sw.initial_state else "open"
    return [
        f"C  TACS Switch: {sw.node1}--{sw.node2} closed when "
        f"{sw.control_signal} > {_fmt(sw.threshold)}",
        f"C  initial_state = {state_word}",
        f"13{n1}{n2}    {sig}    threshold = {_fmt(sw.threshold)}",
    ]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fmt(v: float) -> str:
    """Formata número de forma compacta."""
    if isinstance(v, int) or (
        isinstance(v, float) and v == int(v) and abs(v) < 1e10
    ):
        return str(int(v))
    return f"{v:.6g}"


def make_voltage_probe(
    name: str, node: str, output_signal: str,
) -> TacsMeasuring:
    """
    Helper: ``output_signal = V(node)`` (referência GND).
    """
    return TacsMeasuring(
        name=name, node1=node, node2="",
        output_signal=output_signal, measurement_type="V",
    )


def make_current_probe(
    name: str, node1: str, node2: str, output_signal: str,
) -> TacsMeasuring:
    """
    Helper: ``output_signal = I(node1 → node2)`` via branch
    de impedância nula.
    """
    return TacsMeasuring(
        name=name, node1=node1, node2=node2,
        output_signal=output_signal, measurement_type="I",
    )


def make_voltage_source_tacs(
    name: str, node: str, control_signal: str,
    *, t_start: float = -1.0, t_stop: float = 1.0e9,
) -> TacsControlledSource:
    """
    Helper: ``V(node) = control_signal(t)`` (TYPE-13).
    """
    return TacsControlledSource(
        name=name, node=node, control_signal=control_signal,
        source_type="V", t_start=t_start, t_stop=t_stop,
    )


def make_current_source_tacs(
    name: str, node: str, control_signal: str,
    *, t_start: float = -1.0, t_stop: float = 1.0e9,
) -> TacsControlledSource:
    """
    Helper: ``I(node) = control_signal(t)`` (TYPE-14).
    """
    return TacsControlledSource(
        name=name, node=node, control_signal=control_signal,
        source_type="I", t_start=t_start, t_stop=t_stop,
    )
