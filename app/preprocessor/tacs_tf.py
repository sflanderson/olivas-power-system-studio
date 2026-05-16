"""
app.preprocessor.tacs_tf — transfer functions s-domain para o
``/TACS HYBRID`` do ATP.

Modela blocos do tipo

::

         N(s)        n0 + n1·s + n2·s² + … + n5·s⁵
    K · ────── = K · ────────────────────────────────
         D(s)        d0 + d1·s + d2·s² + … + d5·s⁵

como dataclasses imutáveis e os emite como cartões type-1
(general transfer function) na seção ``/TACS HYBRID``.

Helpers de construção
---------------------

* ``make_integrator(K, …)``      → K/s
* ``make_derivative(K, …)``      → K·s
* ``make_low_pass(K, τ, …)``     → K/(1 + τ·s)
* ``make_high_pass(K, τ, …)``    → K·τ·s/(1 + τ·s)
* ``make_lead_lag(K, T1, T2, …)``→ K·(1 + T1·s)/(1 + T2·s)
* ``make_pid(Kp, Ki, Kd, …)``    → Kp + Ki/s + Kd·s

Limites de saída
----------------

Cada TF aceita ``output_min`` / ``output_max`` opcionais — quando
ambos definidos, a TF satura na saída (clipping hard, comum em
controle de potência para limitar amplitude antes do
inversor/conversor).

Limitação MVP v0.26.2
---------------------

* Cartão emitido em **formato draft legível** (comentários ``C ``
  + cartão type-1 simplificado em colunas livres). O formato strict
  ATP fixed-column será refinado em sub-sprint.
* Apenas 1 input por TF — TACS suporta até 6 inputs somados; soma
  fica para v0.26.3.

Referências
-----------

* ATP Rule Book vol 2, Section V.4 (TACS pole/zero functions).
* Dommel, *EMTP Theory Book*, §14.5 (TACS transfer functions).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


# Limite máximo de polinômio (numerator/denominator) em type-1.
_MAX_POLY_ORDER = 5


@dataclass(frozen=True)
class TacsTransferFunction:
    """
    Transfer function s-domain para emissão em ``/TACS HYBRID``.

    Attributes
    ----------
    name:
        Identificador interno do bloco (≤ 6 chars).
    output:
        Nome do sinal de saída (≤ 6 chars).
    input_signal:
        Nome do sinal de entrada (≤ 6 chars).
    numerator:
        Coeficientes em ordem ascendente em s — ``(n0, n1, n2, …)``
        representa ``n0 + n1·s + n2·s² + …``. Ordem máx = 5.
    denominator:
        Idem para D(s). Ordem máx = 5. Não pode ser todo zero.
    gain:
        Ganho global K antes de N(s)/D(s). Default 1.0.
    initial_output:
        Valor de saída em t = 0 (antes do output_min/max).
    output_min, output_max:
        Limites de saturação opcionais. Se ambos None, não há
        clipping.
    """

    name: str
    output: str
    input_signal: str
    numerator: tuple[float, ...]
    denominator: tuple[float, ...]
    gain: float = 1.0
    initial_output: float = 0.0
    output_min: Optional[float] = None
    output_max: Optional[float] = None


# ---------------------------------------------------------------------------
# Validador
# ---------------------------------------------------------------------------


def validate_tf(tf: TacsTransferFunction) -> list[str]:
    """
    Retorna lista de erros (vazia ⇒ ok).

    Verifica:

    * ``name``/``output``/``input_signal`` não vazios e ≤ 6 chars.
    * ``numerator`` e ``denominator`` com 1 a 6 coeficientes.
    * ``denominator`` não-zero (não-trivial).
    * ``output_min < output_max`` quando ambos definidos.
    """
    errors: list[str] = []
    for attr_name in ("name", "output", "input_signal"):
        v = getattr(tf, attr_name)
        if not v:
            errors.append(f"{attr_name} vazio")
        elif len(v) > 6:
            errors.append(f"{attr_name} {v!r} > 6 chars (limite ATP)")
    if not tf.numerator:
        errors.append("numerator vazio")
    elif len(tf.numerator) > _MAX_POLY_ORDER + 1:
        errors.append(
            f"numerator de ordem {len(tf.numerator)-1} > "
            f"{_MAX_POLY_ORDER} (limite ATP type-1)"
        )
    if not tf.denominator:
        errors.append("denominator vazio")
    elif len(tf.denominator) > _MAX_POLY_ORDER + 1:
        errors.append(
            f"denominator de ordem {len(tf.denominator)-1} > "
            f"{_MAX_POLY_ORDER} (limite ATP type-1)"
        )
    elif all(c == 0.0 for c in tf.denominator):
        errors.append("denominator todo zero (TF mal definida)")
    if (
        tf.output_min is not None
        and tf.output_max is not None
        and tf.output_min >= tf.output_max
    ):
        errors.append(
            f"output_min ({tf.output_min}) >= output_max ({tf.output_max})"
        )
    return errors


# ---------------------------------------------------------------------------
# Pretty-printers
# ---------------------------------------------------------------------------


def _poly_str(coeffs: tuple[float, ...]) -> str:
    """Formata polinômio em s para human-readable.

    ``(1, 0, 2)`` → ``1 + 2·s²``."""
    parts: list[str] = []
    for k, c in enumerate(coeffs):
        if c == 0.0:
            continue
        if k == 0:
            parts.append(_fmt_coeff(c))
        elif k == 1:
            parts.append(f"{_fmt_coeff(c)}·s")
        else:
            parts.append(f"{_fmt_coeff(c)}·s^{k}")
    if not parts:
        return "0"
    return " + ".join(parts)


def _fmt_coeff(c: float) -> str:
    """Coeficiente: int se inteiro, senão notação científica concisa."""
    if c == int(c) and abs(c) < 1e10:
        return str(int(c))
    return f"{c:.6g}"


def render_tf_summary(tf: TacsTransferFunction) -> str:
    """Sumário textual de uma TF para comentário/log.

    Exemplo: ``ctrl1: y = K·(1 + 0.01·s) / (1 + 0.001·s) · u``
    (lead-lag).
    """
    num_s = _poly_str(tf.numerator)
    den_s = _poly_str(tf.denominator)
    if tf.gain == 1.0:
        gain_s = ""
    else:
        gain_s = f"{_fmt_coeff(tf.gain)} · "
    s = (
        f"{tf.output} = {gain_s}({num_s}) / ({den_s}) · "
        f"{tf.input_signal}"
    )
    if tf.output_min is not None or tf.output_max is not None:
        lo = (
            "-inf" if tf.output_min is None else _fmt_coeff(tf.output_min)
        )
        hi = (
            "+inf" if tf.output_max is None else _fmt_coeff(tf.output_max)
        )
        s += f"  [clip {lo} … {hi}]"
    return s


# ---------------------------------------------------------------------------
# Emissão draft (cartão type-1 simplificado)
# ---------------------------------------------------------------------------


def emit_tf_lines(tf: TacsTransferFunction) -> list[str]:
    """
    Emite a TF como bloco de linhas para a seção ``/TACS HYBRID``.

    Formato (draft v0.26.2):

    ::

        C  TACS TF: <summary>
        C  initial_output = <v>
        1<output>      <input>           gain = <g>
        C  numerator   = (n0, n1, n2, …)
        C  denominator = (d0, d1, d2, …)
        C  saturation  = (min, max)      (se aplicável)

    Type-1 do ATP é o "general transfer function" device. Esta
    versão usa formato livre legível com comentários — caller deve
    rodar ``validate_tf`` antes ou usar ``emit_tacs_section`` que
    valida automaticamente.

    Returns
    -------
    list[str]
        Linhas (sem terminador ``\\n``).
    """
    out_padded = tf.output.ljust(6)[:6]
    in_padded = tf.input_signal.ljust(6)[:6]

    lines: list[str] = []
    lines.append(f"C  TACS TF: {render_tf_summary(tf)}")
    if tf.initial_output != 0.0:
        lines.append(
            f"C  initial_output = {_fmt_coeff(tf.initial_output)}"
        )
    lines.append(
        f" 1{out_padded}    {in_padded}        "
        f"gain = {_fmt_coeff(tf.gain)}"
    )
    num_str = ", ".join(_fmt_coeff(c) for c in tf.numerator)
    den_str = ", ".join(_fmt_coeff(c) for c in tf.denominator)
    lines.append(f"C   numerator   = ({num_str})")
    lines.append(f"C   denominator = ({den_str})")
    if tf.output_min is not None or tf.output_max is not None:
        lo = (
            "-inf" if tf.output_min is None else _fmt_coeff(tf.output_min)
        )
        hi = (
            "+inf" if tf.output_max is None else _fmt_coeff(tf.output_max)
        )
        lines.append(f"C   saturation  = ({lo}, {hi})")
    return lines


# ---------------------------------------------------------------------------
# Helpers de construção
# ---------------------------------------------------------------------------


def make_integrator(
    name: str, input_signal: str, output: str,
    *, K: float = 1.0, initial_output: float = 0.0,
    output_min: Optional[float] = None,
    output_max: Optional[float] = None,
) -> TacsTransferFunction:
    """
    Integrador puro: ``y = K · ∫ u dt`` ⇔ ``Y(s)/U(s) = K/s``.

    N(s) = 1, D(s) = s ⇔ ``denominator = (0.0, 1.0)``.
    """
    return TacsTransferFunction(
        name=name, output=output, input_signal=input_signal,
        numerator=(1.0,), denominator=(0.0, 1.0),
        gain=K,
        initial_output=initial_output,
        output_min=output_min, output_max=output_max,
    )


def make_derivative(
    name: str, input_signal: str, output: str,
    *, K: float = 1.0,
) -> TacsTransferFunction:
    """
    Derivador puro: ``y = K · du/dt`` ⇔ ``Y(s)/U(s) = K·s``.

    N(s) = s, D(s) = 1. ATP usa diferença finita backward por
    padrão; use com cautela em sinais ruidosos.
    """
    return TacsTransferFunction(
        name=name, output=output, input_signal=input_signal,
        numerator=(0.0, 1.0), denominator=(1.0,),
        gain=K,
    )


def make_low_pass(
    name: str, input_signal: str, output: str,
    *, K: float = 1.0, tau: float = 1.0,
    initial_output: float = 0.0,
) -> TacsTransferFunction:
    """
    Low-pass de 1ª ordem: ``Y/U = K/(1 + τ·s)``.

    N(s) = 1, D(s) = 1 + τ·s ⇔ ``denominator = (1.0, τ)``.
    """
    if tau <= 0:
        raise ValueError(f"tau deve ser > 0 (achado {tau})")
    return TacsTransferFunction(
        name=name, output=output, input_signal=input_signal,
        numerator=(1.0,), denominator=(1.0, tau),
        gain=K,
        initial_output=initial_output,
    )


def make_high_pass(
    name: str, input_signal: str, output: str,
    *, K: float = 1.0, tau: float = 1.0,
) -> TacsTransferFunction:
    """
    High-pass de 1ª ordem: ``Y/U = K·τ·s/(1 + τ·s)``.

    N(s) = τ·s, D(s) = 1 + τ·s.
    """
    if tau <= 0:
        raise ValueError(f"tau deve ser > 0 (achado {tau})")
    return TacsTransferFunction(
        name=name, output=output, input_signal=input_signal,
        numerator=(0.0, tau), denominator=(1.0, tau),
        gain=K,
    )


def make_lead_lag(
    name: str, input_signal: str, output: str,
    *, K: float = 1.0, T1: float = 1.0, T2: float = 1.0,
) -> TacsTransferFunction:
    """
    Lead-lag de 1ª ordem: ``Y/U = K·(1 + T1·s)/(1 + T2·s)``.

    Lead se ``T1 > T2`` (avanço de fase); lag se ``T1 < T2``.
    """
    if T1 < 0 or T2 <= 0:
        raise ValueError(f"T1 >= 0 e T2 > 0 exigidos (T1={T1}, T2={T2})")
    return TacsTransferFunction(
        name=name, output=output, input_signal=input_signal,
        numerator=(1.0, T1), denominator=(1.0, T2),
        gain=K,
    )


def make_pid(
    name: str, input_signal: str, output: str,
    *, Kp: float = 1.0, Ki: float = 0.0, Kd: float = 0.0,
    output_min: Optional[float] = None,
    output_max: Optional[float] = None,
    initial_output: float = 0.0,
) -> TacsTransferFunction:
    """
    PID clássico: ``Y/U = Kp + Ki/s + Kd·s``.

    Combinando: ``Y/U = (Kd·s² + Kp·s + Ki)/s``.

    N(s) = Ki + Kp·s + Kd·s², D(s) = s ⇔ ``(0, 1)``.

    Saturação ``output_min``/``output_max`` é fortemente recomendada
    para evitar windup do integrador. Valor inicial = 0 por default.
    """
    return TacsTransferFunction(
        name=name, output=output, input_signal=input_signal,
        numerator=(Ki, Kp, Kd), denominator=(0.0, 1.0),
        gain=1.0,
        initial_output=initial_output,
        output_min=output_min, output_max=output_max,
    )
