"""
app.preprocessor.tacs_blocks — blocos discretos / não-linear para
``/TACS HYBRID``: limitadores, dead-band, zero-order hold,
weighted sum.

Visão geral
-----------

Diferente das transfer functions s-domain (módulo
``tacs_tf.py``), estes blocos implementam operações **estáticas
ou amostradas** que não cabem em N(s)/D(s):

* ``TacsLimiter``   → hard clip ``y = max(lo, min(u, hi))`` —
  ATP TACS device-54.
* ``TacsDeadBand``  → dead-band ``y = 0 se |u| < ε senão u``
  (com offset opcional para deslocar a zona morta) — device-53.
* ``TacsZOH``       → zero-order hold ``y latch u no rising edge
  do trigger`` — device-65.
* ``TacsSum``       → weighted sum ``y = bias + Σᵢ kᵢ·xᵢ``
  (até 6 entradas) — device-98.

Cada bloco tem uma função ``emit_*_lines(b)`` que retorna a
representação draft em linhas + comentários ``C ``. O dispatcher
``emit_tacs_section`` (em ``tacs.py``) chama essas funções
quando reconhece o tipo na lista de items.

Limitação MVP v0.26.3
---------------------

Mesmo formato draft legível dos demais blocos TACS — strict
fixed-column ATP fica para sub-sprint.

Referências
-----------

* ATP Rule Book V.4-V.5 (TACS device types).
"""

from __future__ import annotations

from dataclasses import dataclass


# ---------------------------------------------------------------------------
# TacsLimiter (device-54)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TacsLimiter:
    """
    Limitador hard: ``y = max(output_min, min(u, output_max))``.

    Diferença chave para ``output_min``/``output_max`` em
    ``TacsTransferFunction``: aqui é um bloco *standalone* — sua
    entrada é um sinal qualquer, não a saída de uma TF.

    Útil para limitar duty-cycle de PWM, índice de modulação, ou
    qualquer sinal de comando antes do conversor.

    Attributes
    ----------
    name, output, input_signal:
        Conforme convenção TACS (≤ 6 chars).
    output_min, output_max:
        Limites finitos (ambos exigidos). Se quiser apenas um lado,
        passe ``-1e30`` / ``1e30`` para o outro.
    """

    name: str
    output: str
    input_signal: str
    output_min: float
    output_max: float


def validate_limiter(b: TacsLimiter) -> list[str]:
    """Retorna lista de erros (vazia ⇒ ok)."""
    errors: list[str] = []
    for attr in ("name", "output", "input_signal"):
        v = getattr(b, attr)
        if not v:
            errors.append(f"{attr} vazio")
        elif len(v) > 6:
            errors.append(f"{attr} {v!r} > 6 chars (limite ATP)")
    if b.output_min >= b.output_max:
        errors.append(
            f"output_min ({b.output_min}) >= output_max ({b.output_max})"
        )
    return errors


def emit_limiter_lines(b: TacsLimiter) -> list[str]:
    """Linhas draft (sem ``\\n``) — cartão device-54."""
    out_p = b.output.ljust(6)[:6]
    in_p = b.input_signal.ljust(6)[:6]
    return [
        f"C  TACS Limiter: {b.output} = clip({b.input_signal}, "
        f"{_fmt(b.output_min)}, {_fmt(b.output_max)})",
        f"54{out_p}    {in_p}        "
        f"min = {_fmt(b.output_min)}  max = {_fmt(b.output_max)}",
    ]


# ---------------------------------------------------------------------------
# TacsDeadBand (device-53)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TacsDeadBand:
    """
    Dead-band simétrica: saída zerada dentro de ``[center -
    half_width, center + half_width]``; passa-direto fora.

    Modela folga mecânica (gear backlash, threshold de comparador,
    histerese de relé térmico).

    Attributes
    ----------
    name, output, input_signal:
        Conforme convenção TACS.
    half_width:
        Metade da largura da zona morta (deve ser > 0).
    center:
        Centro da zona morta (default 0).
    """

    name: str
    output: str
    input_signal: str
    half_width: float
    center: float = 0.0


def validate_dead_band(b: TacsDeadBand) -> list[str]:
    """Retorna lista de erros."""
    errors: list[str] = []
    for attr in ("name", "output", "input_signal"):
        v = getattr(b, attr)
        if not v:
            errors.append(f"{attr} vazio")
        elif len(v) > 6:
            errors.append(f"{attr} {v!r} > 6 chars (limite ATP)")
    if b.half_width <= 0:
        errors.append(
            f"half_width deve ser > 0 (achado {b.half_width})"
        )
    return errors


def emit_dead_band_lines(b: TacsDeadBand) -> list[str]:
    out_p = b.output.ljust(6)[:6]
    in_p = b.input_signal.ljust(6)[:6]
    lo = b.center - b.half_width
    hi = b.center + b.half_width
    return [
        f"C  TACS DeadBand: {b.output} = deadband({b.input_signal}, "
        f"center={_fmt(b.center)}, half_width={_fmt(b.half_width)})  "
        f"=> 0 dentro de [{_fmt(lo)}, {_fmt(hi)}]",
        f"53{out_p}    {in_p}        "
        f"center = {_fmt(b.center)}  half_width = {_fmt(b.half_width)}",
    ]


# ---------------------------------------------------------------------------
# TacsZOH (device-65)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TacsZOH:
    """
    Zero-Order Hold: latches ``input_signal`` no **rising edge**
    de ``trigger_signal`` (transição 0 → ≠0). Mantém o último
    valor latched até o próximo rising edge.

    Usos típicos: amostragem de set-point em controlador digital,
    refresh periódico de saída de MPPT, dispatch DSP.

    Attributes
    ----------
    name, output, input_signal, trigger_signal:
        Conforme convenção TACS.
    initial_output:
        Valor de saída em t = 0 (antes do primeiro trigger).
    """

    name: str
    output: str
    input_signal: str
    trigger_signal: str
    initial_output: float = 0.0


def validate_zoh(b: TacsZOH) -> list[str]:
    """Retorna lista de erros."""
    errors: list[str] = []
    for attr in ("name", "output", "input_signal", "trigger_signal"):
        v = getattr(b, attr)
        if not v:
            errors.append(f"{attr} vazio")
        elif len(v) > 6:
            errors.append(f"{attr} {v!r} > 6 chars (limite ATP)")
    if b.input_signal == b.trigger_signal:
        errors.append(
            f"input_signal == trigger_signal ({b.input_signal!r}) "
            "— ZOH degenerado"
        )
    return errors


def emit_zoh_lines(b: TacsZOH) -> list[str]:
    out_p = b.output.ljust(6)[:6]
    in_p = b.input_signal.ljust(6)[:6]
    trig_p = b.trigger_signal.ljust(6)[:6]
    lines = [
        f"C  TACS ZOH: {b.output} = sample({b.input_signal}) on rising "
        f"edge of {b.trigger_signal}",
    ]
    if b.initial_output != 0.0:
        lines.append(f"C  initial_output = {_fmt(b.initial_output)}")
    lines.append(
        f"65{out_p}    {in_p}    trig = {trig_p}  "
        f"init = {_fmt(b.initial_output)}"
    )
    return lines


# ---------------------------------------------------------------------------
# TacsSum (device-98)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TacsSum:
    """
    Weighted sum: ``y = bias + Σᵢ kᵢ·xᵢ``.

    ATP TACS device-98 aceita até 6 inputs ponderados; cada entrada
    é par ``(signal_name, weight)``. Útil para somador/subtrator
    de sinais em controle (ex: ``err = ref - meas`` ⇔ ``inputs =
    ((ref, 1.0), (meas, -1.0))``).

    Attributes
    ----------
    name, output:
        Conforme convenção TACS.
    inputs:
        Tupla de pares ``(signal_name, weight)``. Mín 1, máx 6.
    bias:
        Constante somada. Default 0.
    """

    name: str
    output: str
    inputs: tuple
    bias: float = 0.0


_MAX_SUM_INPUTS = 6


def validate_sum(b: TacsSum) -> list[str]:
    """Retorna lista de erros."""
    errors: list[str] = []
    for attr in ("name", "output"):
        v = getattr(b, attr)
        if not v:
            errors.append(f"{attr} vazio")
        elif len(v) > 6:
            errors.append(f"{attr} {v!r} > 6 chars (limite ATP)")
    if not b.inputs:
        errors.append("inputs vazio (mín 1)")
    elif len(b.inputs) > _MAX_SUM_INPUTS:
        errors.append(
            f"inputs com {len(b.inputs)} entradas > "
            f"{_MAX_SUM_INPUTS} (limite ATP device-98)"
        )
    for i, item in enumerate(b.inputs):
        if not isinstance(item, tuple) or len(item) != 2:
            errors.append(
                f"inputs[{i}] deve ser tupla (signal_name, weight); "
                f"achado {item!r}"
            )
            continue
        sig, w = item
        if not isinstance(sig, str) or not sig:
            errors.append(f"inputs[{i}] signal_name inválido: {sig!r}")
        elif len(sig) > 6:
            errors.append(
                f"inputs[{i}] signal_name {sig!r} > 6 chars"
            )
        if not isinstance(w, (int, float)):
            errors.append(
                f"inputs[{i}] weight deve ser número; achado {w!r}"
            )
    return errors


def emit_sum_lines(b: TacsSum) -> list[str]:
    """Linhas draft do device-98."""
    out_p = b.output.ljust(6)[:6]
    # Sumário humano: y = bias + k1*x1 + k2*x2 ...
    parts: list[str] = []
    if b.bias != 0.0:
        parts.append(_fmt(b.bias))
    for sig, w in b.inputs:
        if w == 1.0:
            term = sig
        elif w == -1.0:
            term = f"-{sig}"
        else:
            term = f"{_fmt(w)}·{sig}"
        parts.append(term)
    summary = " + ".join(parts).replace("+ -", "- ")

    lines = [f"C  TACS Sum: {b.output} = {summary}"]
    if b.bias != 0.0:
        lines.append(f"C  bias = {_fmt(b.bias)}")
    inputs_str = ", ".join(
        f"({sig}, k={_fmt(w)})" for sig, w in b.inputs
    )
    lines.append(f"C  inputs = [{inputs_str}]")
    lines.append(
        f"98{out_p}    " + " ".join(
            f"{sig.ljust(6)[:6]}*{_fmt(w)}" for sig, w in b.inputs
        )
        + (f"  + {_fmt(b.bias)}" if b.bias != 0.0 else "")
    )
    return lines


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fmt(v: float) -> str:
    """Formata número de forma compacta (int se inteiro)."""
    if isinstance(v, int) or (
        isinstance(v, float) and v == int(v) and abs(v) < 1e10
    ):
        return str(int(v))
    return f"{v:.6g}"


def make_subtractor(
    name: str, output: str, positive: str, negative: str,
) -> TacsSum:
    """
    Helper: ``y = positive - negative`` via TacsSum.

    Atalho frequente em controle: ``err = ref - meas``.
    """
    return TacsSum(
        name=name, output=output,
        inputs=((positive, 1.0), (negative, -1.0)),
    )


def make_adder(
    name: str, output: str, *signals: str,
) -> TacsSum:
    """
    Helper: ``y = x1 + x2 + …`` (todos com peso 1) via TacsSum.
    """
    return TacsSum(
        name=name, output=output,
        inputs=tuple((s, 1.0) for s in signals),
    )
