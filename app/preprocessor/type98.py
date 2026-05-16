"""
app.preprocessor.type98 — emissão de cards ATP Type-98 (reator
pseudo-não-linear PWL).

Type-98 é o elemento ATP padrão para modelar saturação em reatores
e ramos magnetizantes de transformadores. Consiste numa
característica flux-current definida por pontos (i, ψ) que o solver
percorre segmento a segmento, avançando de um para o seguinte quando
a operação sai do intervalo do segmento atual.

Referências
-----------
* ATP Rule Book Vol 1 §8.4 (Type-98 Pseudononlinear Reactor).
* H. W. Dommel, EMTP Theory Book, BPA, 1986, §6.2 (saturação
  de trafos + Type-98).

Convenções
----------
* A curva ``(i, ψ)`` é fornecida no **primeiro quadrante** (i ≥ 0,
  ψ ≥ 0). ATP extrapola para o terceiro quadrante por simetria
  ímpar — comportamento físico do núcleo ferromagnético.
* Pontos devem ser **estritamente monotônicos** em ambos os eixos
  (i e ψ crescentes), senão o solver troca de segmento
  indefinidamente.
* O primeiro ponto é tipicamente ``(0, 0)`` — início da zona
  linear.
* Unidades: ``i`` em **Amperes**, ``ψ`` em **V·s = Wb-turn**
  (fluxo concatenado, não densidade de fluxo B).

Formato do card Type-98
-----------------------

Linha 1 (cabeçalho):
::

    98  N1     N2         I_ss          psi_ss

onde ``I_ss`` e ``psi_ss`` são o ponto de operação em regime
permanente (phasor solution) — usados como chute inicial.

Linhas 2..N (pares i, ψ):
::

           I_k                     psi_k

Terminador:
::

    9999

A função :func:`emit_type98_cards` constrói essas linhas com a
formatação correta de colunas ATP.

Escopo (v0.24.2 MVP)
--------------------

* Parsing de curva em 2 formatos: CSV string (``"0,0;5,0.8;10,1.0"``)
  e lista Python ``[(i1, ψ1), (i2, ψ2), ...]``.
* Validação: monotonicidade, não-vazio, primeiro ponto ≥ (0, 0).
* Emissão dos cards com formato ATP padrão.
* Helper ``default_saturation_curve()`` — uma curva canônica de
  trafo de potência típico para uso em testes e como starter kit.

Integração com BCTRAN e LNL vem em sub-sprints seguintes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Optional, Sequence


# ---------------------------------------------------------------------------
# Schema: ponto e curva
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SaturationPoint:
    """
    Um ponto ``(i, ψ)`` da característica de saturação.

    Attributes
    ----------
    current:
        Corrente de magnetização em **Amperes** (RMS ou pico —
        convenção depende do estudo; típico em ATP é **pico**).
    flux:
        Fluxo concatenado em **V·s** (weber-turn).
    """

    current: float
    flux: float

    def __post_init__(self) -> None:
        if self.current < 0:
            raise ValueError(
                f"current negativo ({self.current}) — use só primeiro "
                "quadrante; ATP extrapola por simetria ímpar."
            )
        if self.flux < 0:
            raise ValueError(
                f"flux negativo ({self.flux}) — use só primeiro quadrante."
            )


@dataclass
class SaturationCurve:
    """
    Curva de saturação PWL completa (lista de pontos).

    Attributes
    ----------
    points:
        Lista de ``SaturationPoint`` em ordem crescente de corrente.
    i_ss:
        Corrente em regime permanente (phasor solution). Default
        0 — ATP calcula a partir do steady-state.
    flux_ss:
        Fluxo em regime permanente. Default 0.

    Validations
    -----------
    * Mínimo 2 pontos (1 segmento PWL).
    * Monotonicidade: ``i`` e ``ψ`` estritamente crescentes.
    * Primeiro ponto idealmente em (0, 0) — zona linear começa
      na origem; aceitamos outros como aviso.
    """

    points: list[SaturationPoint] = field(default_factory=list)
    i_ss: float = 0.0
    flux_ss: float = 0.0

    def __post_init__(self) -> None:
        self._validate()

    def _validate(self) -> None:
        if len(self.points) < 2:
            raise ValueError(
                f"Curva precisa de pelo menos 2 pontos (tem "
                f"{len(self.points)}). Um único ponto é caso linear, "
                "use um indutor simples."
            )
        # Monotonicidade estrita em current e flux
        for i in range(1, len(self.points)):
            p_prev = self.points[i - 1]
            p_curr = self.points[i]
            if p_curr.current <= p_prev.current:
                raise ValueError(
                    f"current não-monotônico no ponto {i}: "
                    f"{p_prev.current} → {p_curr.current} (deve ser "
                    "estritamente crescente)."
                )
            if p_curr.flux <= p_prev.flux:
                raise ValueError(
                    f"flux não-monotônico no ponto {i}: "
                    f"{p_prev.flux} → {p_curr.flux} (deve ser "
                    "estritamente crescente)."
                )

    def is_canonical(self, tol: float = 1e-9) -> bool:
        """True se o primeiro ponto é ``(0, 0)`` (origem)."""
        p0 = self.points[0]
        return abs(p0.current) < tol and abs(p0.flux) < tol

    def knee_point(self) -> SaturationPoint:
        """
        Retorna o "joelho" da curva — heurística: ponto onde o
        gradiente dψ/di cai mais abruptamente (transição linear
        → saturada).

        Útil para validação visual e sanity-check. Se só houver 2
        pontos, retorna o último (segmento linear → saturado).
        """
        if len(self.points) == 2:
            return self.points[-1]
        # Calcula derivada local em cada segmento
        best_idx = 1
        best_drop = 0.0
        for i in range(1, len(self.points) - 1):
            p_prev = self.points[i - 1]
            p_curr = self.points[i]
            p_next = self.points[i + 1]
            slope1 = (p_curr.flux - p_prev.flux) / (
                p_curr.current - p_prev.current
            )
            slope2 = (p_next.flux - p_curr.flux) / (
                p_next.current - p_curr.current
            )
            drop = slope1 - slope2   # positive = saturation
            if drop > best_drop:
                best_drop = drop
                best_idx = i
        return self.points[best_idx]


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


def parse_csv_curve(text: str) -> SaturationCurve:
    """
    Parseia uma string CSV de pontos ``"i1,ψ1;i2,ψ2;..."``.

    Formato aceito:
    * Separador entre pontos: ``;`` (semicolon).
    * Separador i/ψ: ``,`` (comma).
    * Espaços em branco ao redor são ignorados.
    * Pontos vazios são ignorados (permite trailing ``;``).

    Exemplo:
    ::

        "0,0; 5,0.8; 10,1.0; 20,1.05; 50,1.10"

    Returns
    -------
    SaturationCurve
    """
    text = (text or "").strip()
    if not text:
        raise ValueError("CSV vazio — forneça ao menos 2 pontos (i, ψ).")

    points: list[SaturationPoint] = []
    for raw in text.split(";"):
        token = raw.strip()
        if not token:
            continue
        parts = [p.strip() for p in token.split(",")]
        if len(parts) != 2:
            raise ValueError(
                f"Ponto malformado {token!r} — esperado 'i,ψ'."
            )
        try:
            i_val = float(parts[0])
            f_val = float(parts[1])
        except ValueError as e:
            raise ValueError(
                f"Ponto {token!r} não-numérico: {e}"
            ) from e
        points.append(SaturationPoint(current=i_val, flux=f_val))

    return SaturationCurve(points=points)


# ---------------------------------------------------------------------------
# Default curve — usada em tests e como "starter kit" para o usuário
# ---------------------------------------------------------------------------


def default_saturation_curve() -> SaturationCurve:
    """
    Curva canônica de um trafo de potência típico (60 Hz, núcleo
    grão-orientado):

    * Zona linear até ~1.0 p.u. de fluxo com i ≪ 1 A.
    * Joelho em ~1.05 p.u.
    * Saturação profunda acima de 1.15 p.u.

    Valores aproximados, adequados como ponto de partida para
    estudos de inrush. Usuário ajusta conforme data sheet.
    """
    return SaturationCurve(
        points=[
            SaturationPoint(0.0,    0.0),
            SaturationPoint(1.0,    0.95),   # linear quase até joelho
            SaturationPoint(5.0,    1.05),   # joelho
            SaturationPoint(20.0,   1.10),   # início saturação
            SaturationPoint(200.0,  1.15),   # saturação profunda
        ],
    )


# ---------------------------------------------------------------------------
# Emissão de cards ATP
# ---------------------------------------------------------------------------


def emit_type98_cards(
    node_hot: str,
    node_gnd: str,
    curve: SaturationCurve,
    *,
    comment: str = "",
) -> list[str]:
    """
    Constrói as linhas ATP para um elemento Type-98.

    Parameters
    ----------
    node_hot:
        Nó onde o reator se conecta (entrada da corrente magnetizante).
    node_gnd:
        Nó de retorno (normalmente terra ou neutro).
    curve:
        Curva de saturação já validada.
    comment:
        Comentário ATP (linha começando com "C ") opcional,
        colocado antes dos cards.

    Returns
    -------
    list[str]
        Linhas prontas para inserir na seção /BRANCH.

    Formato
    -------
    Linha 1 (cabeçalho):
        col 0-1: "98"
        col 2-7: node_hot (6 chars)
        col 8-13: node_gnd (6 chars)
        col 14-25: (reservado, em branco)
        col 26-37: i_ss (12 chars, notação científica)
        col 38-49: flux_ss (12 chars)

    Linhas 2..N (pontos PWL):
        col 0-13: (em branco — posição reservada para kind)
        col 14-25: i_k
        col 26-37: psi_k

    Terminador:
        col 0-3: "9999"
    """
    lines: list[str] = []
    if comment:
        lines.append(f"C {comment}")

    # Linha 1 — cabeçalho
    header = (
        f"98{node_hot:<6s}{node_gnd:<6s}"
        f"{'':<12s}"
        f"{curve.i_ss:>12.4E}{curve.flux_ss:>12.4E}"
    )
    lines.append(header)

    # Pontos PWL
    for pt in curve.points:
        # Formato: 14 chars em branco + i (12) + ψ (12)
        lines.append(f"{'':<14s}{pt.current:>12.4E}{pt.flux:>12.4E}")

    # Terminador
    lines.append("9999")

    return lines


# ---------------------------------------------------------------------------
# Convenience: emit from CSV string directly
# ---------------------------------------------------------------------------


def emit_type98_from_csv(
    node_hot: str,
    node_gnd: str,
    csv_text: str,
    *,
    comment: str = "",
) -> list[str]:
    """
    Atalho: parseia ``csv_text`` e emite cards num único passo.

    Raises
    ------
    ValueError
        Se o CSV é malformado, não-monotônico, ou tem < 2 pontos.
    """
    curve = parse_csv_curve(csv_text)
    return emit_type98_cards(node_hot, node_gnd, curve, comment=comment)
