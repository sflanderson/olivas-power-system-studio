"""
app.preprocessor.units — conversão de strings Qucs (com prefixo SI)
para float em unidade base SI, e formatação inversa para o ATP.

Exemplos
--------

>>> parse_value("10 kOhm")
10000.0
>>> parse_value("1 mH")
0.001
>>> parse_value("100 uF")
0.0001
>>> parse_value("47uH")
4.7e-05
>>> format_atp(1000.0, width=6)
'  1000'
>>> format_atp(0.001, width=6)
' 0.001'

O ATP usa colunas estreitas (6 ou 10 caracteres) para campos
numéricos. As funções `format_atp_*` produzem strings já com
o número de caracteres alvo, escolhendo notação fixa ou
científica conforme couber.

Notas
-----

* Prefixos SI suportados: T, G, M, k, m, u, n, p, f.
* Caso especial Qucs: ``M`` minúsculo é "mili" (m), MAIÚSCULO
  é "Mega". Atenção: no Qucs ``M`` significa mili também em
  alguns campos! A política aqui é a SI clássica
  (M=Mega, m=mili) — se um teste em fixture real falhar,
  refinaremos.
* Variáveis (ex: ``"Vamp"``, ``"Bduty"``) — quando não há
  número parseável, retornamos ``None`` e o caller decide se
  rejeita o componente ou propaga o nome literal para o ATP.
"""

from __future__ import annotations

import math
import re
from typing import Optional


# ---------------------------------------------------------------------------
# Tabela de prefixos SI
# ---------------------------------------------------------------------------

# Ordenado do maior expoente para o menor — importante na regex
# greedy (do contrário "M" pegaria antes de "m" sem ambiguidade,
# mas também tem que pegar "Meg" antes de "M" em algumas variantes).
_SI_PREFIXES: dict[str, float] = {
    "T":  1e12,
    "G":  1e9,
    "MEG": 1e6,   # forma escrita comum em SPICE/ATP
    "M":  1e6,
    "k":  1e3,
    "K":  1e3,    # Qucs aceita ambos
    "m":  1e-3,
    "u":  1e-6,
    "µ":  1e-6,   # caractere micro
    "n":  1e-9,
    "p":  1e-12,
    "f":  1e-15,
}


# Sufixos de unidade que ignoramos (para extrair só o número).
# A unidade real é determinada pelo TIPO do componente, não pela
# string. Ex: "10 kOhm" e "10 k" ambos viram 10000.0; é o catálogo
# que sabe que isso é resistência.
_UNIT_SUFFIXES = (
    "Ohm", "ohm", "Ω",   # resistência
    "H", "h",            # indutância
    "F", "f",            # capacitância
    "V", "v",            # tensão
    "A", "a",            # corrente
    "Hz", "hz", "HZ",    # frequência
    "s", "S",            # tempo
    "W", "w",            # potência
    "var", "VAR",        # potência reativa
)


# Regex: opcional sinal, mantissa (com decimal e expoente científico),
# opcional whitespace, opcional prefixo SI, opcional unidade
_NUMBER_RE = re.compile(
    r"""
    ^\s*
    (?P<sign>[+-]?)
    (?P<mantissa>\d+(?:\.\d*)?|\.\d+)
    (?:[eE](?P<exp>[+-]?\d+))?
    \s*
    (?P<suffix>[A-Za-zµΩ]*)
    \s*$
    """,
    re.VERBOSE,
)


def parse_value(text: str) -> Optional[float]:
    """
    Converte uma string Qucs em float SI.

    Retorna ``None`` se a string não contém um número (típico de
    parâmetros simbólicos como ``"Vamp"`` que referenciam uma
    equação no `Eqn`). Cabe ao caller decidir o fallback.

    Comportamento
    -------------
    * ``""``                → ``None``
    * ``"10"``              → 10.0
    * ``"10.5"``            → 10.5
    * ``"1e-3"``            → 0.001
    * ``"10 k"``            → 10000.0
    * ``"10 kOhm"``         → 10000.0
    * ``"47uH"``            → 4.7e-5
    * ``"100 uF"``          → 1e-4
    * ``"1 MEG"``           → 1e6
    * ``"-5.5"``            → -5.5
    * ``"Vamp"``            → ``None``
    * ``"  +3.14e2 V "``    → 314.0
    """
    if text is None:
        return None
    s = text.strip()
    if not s:
        return None

    m = _NUMBER_RE.match(s)
    if not m:
        return None

    mantissa = float(m.group("mantissa"))
    if m.group("sign") == "-":
        mantissa = -mantissa

    exp = m.group("exp")
    if exp:
        mantissa *= 10 ** int(exp)

    suffix = m.group("suffix") or ""
    multiplier = _resolve_suffix(suffix)
    if multiplier is None:
        # sufixo presente mas não reconhecido — string toda inválida
        return None

    return mantissa * multiplier


def _resolve_suffix(suffix: str) -> Optional[float]:
    """
    Resolve o sufixo (prefixo SI + unidade) em um multiplicador.
    Retorna ``None`` se o sufixo é inválido (não é vazio, mas
    também não casa com nenhum prefixo+unidade conhecidos).
    """
    if not suffix:
        return 1.0

    # Tentar primeiro casos especiais multiletra (MEG, Ohm, Hz...)
    s = suffix
    # Tira unidade do fim
    for unit in _UNIT_SUFFIXES:
        if s.endswith(unit):
            s = s[: -len(unit)]
            break
    # Agora s deve ser ou vazio ou um prefixo SI
    if not s:
        return 1.0
    # Casos multiletra primeiro
    if s.upper() == "MEG":
        return 1e6
    if s in _SI_PREFIXES:
        return _SI_PREFIXES[s]
    # Heurística: se o primeiro char é prefixo e o resto é unidade
    # já tirada — não chega aqui. Senão, inválido.
    return None


# ---------------------------------------------------------------------------
# Formatação para ATP
# ---------------------------------------------------------------------------


def format_atp_value(value: float, width: int = 6) -> str:
    """
    Formata um float para um campo de largura fixa do ATP.

    Estratégia
    ----------
    1. Se ``value`` for inteiro e cabe em ``width`` chars como
       inteiro → usa inteiro (ex: ``1000`` em width=6 → ``"  1000"``).
    2. Senão, tenta a representação MAIS CURTA que preserva o valor
       (ascendente em casas decimais, escolhendo a primeira que dá
       round-trip exato dentro da tolerância numérica).
    3. Se nem fixed-point com width-1 decimais couber/preserva, cai
       para notação científica curta.

    O ATP é tolerante a ambos os formatos nos campos numéricos.
    Esta política gera saída mais legível (sem zeros decorativos).
    """
    if value is None:
        return " " * width
    if not math.isfinite(value):
        return " " * width

    # 1. Inteiro
    if value == int(value):
        s = str(int(value))
        if len(s) <= width:
            return s.rjust(width)

    # 2. Fixed point com mínimo de decimais que ainda preserva valor
    #    (ascendente: 0, 1, 2, ... até width-1)
    for decimals in range(0, width):
        s = f"{value:.{decimals}f}"
        if len(s) > width:
            break
        # Preserva valor? (compara via parse-back)
        try:
            if abs(float(s) - value) <= max(abs(value), 1.0) * 1e-9:
                return s.rjust(width)
        except ValueError:
            continue
    # Fallback: forma fixa mais larga que ainda cabe (não-preservante)
    for decimals in range(width - 2, -1, -1):
        s = f"{value:.{decimals}f}"
        if len(s) <= width:
            return s.rjust(width)

    # 3. Científica
    for decimals in range(max(1, width - 6), -1, -1):
        s = f"{value:.{decimals}e}"
        if len(s) <= width:
            return s.rjust(width)

    # Última tentativa: trunca brutalmente
    s = f"{value:.0e}"
    return s[:width].rjust(width)


def format_atp_str(value: float, width: int = 6) -> str:
    """
    Como `format_atp_value`, mas devolve string sem padding.
    Útil quando o serializer ATP do projeto faz seu próprio
    `_rfit`/`_fit` (caso de `app/core/serializer.py`).
    """
    return format_atp_value(value, width).strip()


# ---------------------------------------------------------------------------
# Helpers de conveniência
# ---------------------------------------------------------------------------


def parse_value_or_keep(text: str) -> str:
    """
    Tenta parsear como número; se não der, devolve a string original
    intacta (útil para propagar variáveis simbólicas direto para o
    ATP, que pode não suportar mas pelo menos preserva intenção).
    """
    v = parse_value(text)
    if v is None:
        return text
    return format_atp_str(v, width=10)


def is_numeric(text: str) -> bool:
    """True sse `text` parseia como número."""
    return parse_value(text) is not None
