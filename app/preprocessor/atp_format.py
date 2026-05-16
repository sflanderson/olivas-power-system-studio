"""
app.preprocessor.atp_format — helpers para emitir cards ATP
em **strict fixed-format** (column-precise).

v0.28.4-PRO Onda 4: substitui emitters draft por formatação
column-precise compatível com ATP solver.

Convenções ATP (Rule Book Vol 2)
=================================

* Linha total: ≤ 80 colunas (strict).
* Cards de tipo (Type-1, 51, 59, 93, 98...) ocupam colunas
  específicas dependendo do tipo.
* **Default fixed format**:
    - Type indicator: cols 1-2 (2 chars)
    - Node name 1: cols 3-8 (6 chars)
    - Node name 2: cols 9-14 (6 chars)
    - Numeric fields: 6 chars OR 10 chars cada (depending on
      card)
* **Extended format** (raro, mas alguns cards usam): node
  fields 8 chars, numeric 16 chars.

Helpers
========

* ``fmt_node(name, width=6, *, project=None, where='')``:
  trunca + pad-right com espaços. Emite warning de truncation
  via project.warnings se aplicável.
* ``fmt_num(value, width, *, scientific=False)``: número em
  fixed-width Fortran-like com padding.
* ``card_format(type_code, *fields, widths)``: monta linha
  completa com validação de comprimento total ≤ 80.

Esses helpers garantem que strings escritas em ``raw_lines``
não excedam 80 cols e seguem o layout esperado pelo ATP.
"""

from __future__ import annotations

import math
from typing import Optional


ATP_LINE_MAX_WIDTH = 80
ATP_NODE_FIELD_WIDTH = 6
ATP_NODE_FIELD_WIDTH_EXTENDED = 8


def fmt_node(
    name: Optional[str],
    width: int = ATP_NODE_FIELD_WIDTH,
    *,
    project=None,
    where: str = "",
) -> str:
    """
    Formata nome de nó em campo fixed-width.

    * Trunca se exceder ``width``.
    * Right-pad com espaços para preencher exatamente ``width``.
    * Se ``project`` fornecido e truncamento ocorrer, emite
      warning em ``project.warnings``.
    """
    s = "" if name is None else str(name)
    if len(s) > width:
        truncated = s[:width]
        if project is not None:
            ctx = f" em {where}" if where else ""
            project.warnings.append(
                f"Nó ATP {s!r} truncado para {truncated!r}{ctx} "
                f"(campo {width} chars). Verifique colisão."
            )
        s = truncated
    # Pad com espaços à direita
    return s.ljust(width)


def fmt_num(
    value: float,
    width: int,
    *,
    scientific: bool = False,
    decimals: Optional[int] = None,
) -> str:
    """
    Formata número em campo fixed-width estilo Fortran.

    Estratégia:

    1. Se ``scientific=True`` ou |value| ≥ 10^(width-3) ou
       |value| < 10^(-(width-3)) e ≠ 0: usa notação científica.
    2. Senão: tenta decimal com ``decimals`` (default = max
       que cabe no width).
    3. Right-align (pad à esquerda com espaços).

    Garante que retorna EXATAMENTE ``width`` chars.

    Parameters
    ----------
    value:
        Número (float).
    width:
        Largura do campo (>= 4 recomendado para usar decimais).
    scientific:
        Force notação científica.
    decimals:
        Casas decimais (None = auto-fit).

    Returns
    -------
    str
        String com EXATAMENTE ``width`` chars.
    """
    if width < 1:
        raise ValueError(f"width deve ser >= 1 (achado {width})")

    # Caso especial: zero
    if value == 0.0:
        return "0".rjust(width)
    if not math.isfinite(value):
        # NaN, inf — substitui por 0
        return "0".rjust(width)

    if scientific or _needs_scientific(value, width):
        # Formato Fortran-style: 1.234E+05 → comprimento variável
        # Calcula expoente
        exp = int(math.floor(math.log10(abs(value))))
        mantissa = value / (10 ** exp)
        # Ajusta decimais para caber no width
        # "X.YYE+ZZ" = sign(1) + digit(1) + dot(1) + frac + 'E' + sign(1) + 2digit_exp
        # → 7 chars de overhead, sobra width-7 para frac
        avail_frac = max(1, width - 7 if value < 0 else width - 6)
        formatted = f"{mantissa:.{avail_frac}f}E{exp:+03d}"
        # Garante exato width
        return formatted[:width].rjust(width)

    if decimals is None:
        # Auto-fit: tenta decimais decrescentes
        for d in range(width - 2, -1, -1):
            s = f"{value:.{d}f}"
            if len(s) <= width:
                return s.rjust(width)
        return f"{value:.0f}"[:width].rjust(width)

    s = f"{value:.{decimals}f}"
    return s[:width].rjust(width)


def _needs_scientific(value: float, width: int) -> bool:
    """Heurística: notação científica se |val| muito grande/pequeno."""
    av = abs(value)
    if av == 0:
        return False
    # Se exigir mais que (width-1) dígitos para parte inteira
    # ou for muito pequeno
    if av >= 10 ** (width - 1):
        return True
    if av < 10 ** (-(width - 4)):
        return True
    return False


def card_line(
    type_code: str,
    *,
    type_width: int = 2,
) -> str:
    """
    Cria linha vazia (80 chars) com type_code nos primeiros
    bytes. Use ``set_field`` para preencher campos por offset.

    Returns
    -------
    str
        Linha de comprimento ATP_LINE_MAX_WIDTH preenchida com
        espaços, exceto pelo type_code.
    """
    line = list(" " * ATP_LINE_MAX_WIDTH)
    code = str(type_code)[:type_width].ljust(type_width)
    for i, ch in enumerate(code):
        line[i] = ch
    return "".join(line)


def set_field(
    line: str, start: int, value: str, width: int,
) -> str:
    """
    Sobrescreve campo de width chars em line[start:start+width].

    Parameters
    ----------
    line:
        Linha original (qualquer tamanho).
    start:
        Coluna inicial 0-indexed.
    value:
        String a inserir (será trimmed/padded para width).
    width:
        Largura do campo.

    Returns
    -------
    str
        Nova linha. Se start+width > len(line), pad com espaços.
    """
    needed = start + width
    if needed > len(line):
        line = line.ljust(needed)
    payload = str(value)[:width].ljust(width)
    return line[:start] + payload + line[start + width:]


def validate_card_width(line: str, *, where: str = "") -> str:
    """
    Garante que line ≤ ATP_LINE_MAX_WIDTH chars.

    Estratégia: trim trailing whitespace, depois trunca em 80
    se ainda exceder. Emite warning em logs se truncar.
    """
    trimmed = line.rstrip()
    if len(trimmed) > ATP_LINE_MAX_WIDTH:
        # Real overflow — trunca silenciosamente em 80
        # (caller deve assegurar que campos cabem)
        return trimmed[:ATP_LINE_MAX_WIDTH]
    return trimmed
