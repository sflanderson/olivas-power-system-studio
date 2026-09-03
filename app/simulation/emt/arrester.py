"""
app.simulation.emt.arrester — para-raios de óxido metálico (ZnO).

Por que este módulo existe
===========================

A varredura estatística do disjuntor a vácuo mostrou que o motor produz
escalada até 77 pu porque **nada no modelo representa o limite dielétrico
da carga** [REPO:
``docs/research/rul_isolamento/08_VARREDURA_ESTATISTICA_VCB.md``, §3.2.1].
Numa instalação real a escalada é grampeada pelo para-raios — quando há —
ou pela disrupção da própria isolação. Sem esse elemento, qualquer
resultado de escalada acima do envelope da IEC 60034-15 descreve tensão
que a máquina não suportaria.

O para-raios é, além disso, a mitigação que as duas fontes primárias de
transitório de VCB modelam: Vollet e de Metz-Noblat colocam um MOA no
cubículo e outro no motor e medem 32 kV fase-terra num motor de 11 kV
[LITERATURA: IPST 2007, p. 4-6]; Xemard et al. reportam redução de 4,3
para 2,64 pu [LITERATURA: IPST 2019, p. 5]. Ambos advertem que o
para-raios **limita a amplitude mas não elimina as reignições**
[LITERATURA: Vollet 2007, p. 5].

Método numérico
================

Compensação, com a característica ``v-i`` representada ponto a ponto —
:mod:`app.simulation.emt.nonlinear`. O exemplo trabalhado do artigo que
funda o método é exatamente este: *"a lightning arrester at the
substation end of the cable"* [FONTE: Dommel 1971, Fig. 3, p. 2562].

Dados
======

As curvas publicadas trazem DOIS pontos cada, e é o que este módulo
transcreve; os pontos intermediários vêm de interpolação log-log entre
eles, que é a única inferência feita e está declarada em
:func:`exponent_from_points` [CÁLCULO PRÓPRIO].

Limitações
===========

Ver :data:`app.simulation.emt.nonlinear.KNOWN_LIMITATIONS` — em especial
``emt_nonlinear_no_dynamic_arrester_model`` — e
:data:`KNOWN_LIMITATIONS` deste módulo.

Fontes
=======

* VOLLET, C.; DE METZ-NOBLAT, B. Vacuum circuit breaker model:
  application case to motors switching. In: IPST 2007, Lyon,
  paper 07IPST106.
* DOMMEL, H. W. Nonlinear and time-varying elements in digital simulation
  of electromagnetic transients. **IEEE Transactions on Power Apparatus
  and Systems**, v. PAS-90, n. 6, p. 2561-2567, 1971.
* Levantamento consolidado, com a verificação de cada valor:
  ``docs/research/rul_isolamento/anexos/pesquisa/fisica_surtos_vcb_isolamento.md``,
  §3.6.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence

import numpy as np

from app.core.logging_config import get_logger

from .nonlinear import CompensatedBranch, PiecewiseLinearVI

log = get_logger(__name__)


# ---------------------------------------------------------------------------
# Dados publicados
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ArresterPoints:
    """Dois pontos publicados da característica de um para-raios.

    Attributes
    ----------
    low_voltage_V, low_current_A:
        Ponto de baixa corrente — a região de fuga, próxima ao joelho.
    high_voltage_V, high_current_A:
        Ponto de alta corrente — o nível de proteção.
    system_voltage_V:
        Tensão nominal do sistema em que o para-raios foi aplicado [V],
        necessária para o escalonamento.
    source:
        Procedência do dado.
    """

    low_voltage_V: float
    low_current_A: float
    high_voltage_V: float
    high_current_A: float
    system_voltage_V: float
    source: str

    def __post_init__(self) -> None:
        for rotulo, valor in (
            ("low_voltage_V", self.low_voltage_V),
            ("low_current_A", self.low_current_A),
            ("high_voltage_V", self.high_voltage_V),
            ("high_current_A", self.high_current_A),
            ("system_voltage_V", self.system_voltage_V),
        ):
            v = float(valor)
            if not math.isfinite(v) or v <= 0.0:
                raise ValueError(f"{rotulo} deve ser finito e > 0, obtido {valor!r}")
        if float(self.high_voltage_V) <= float(self.low_voltage_V):
            raise ValueError("high_voltage_V deve exceder low_voltage_V")
        if float(self.high_current_A) <= float(self.low_current_A):
            raise ValueError("high_current_A deve exceder low_current_A")


#: Para-raios do TERMINAL DO MOTOR do caso de 11 kV de Vollet: 18,4 kV a
#: 0,1 mA e 36,8 kV a 10 kA [LITERATURA: Vollet e de Metz-Noblat, IPST
#: 2007, p. 4-6; transcrito do levantamento, §3.6].
VOLLET_MOTOR_ARRESTER: ArresterPoints = ArresterPoints(
    low_voltage_V=18.4e3,
    low_current_A=0.1e-3,
    high_voltage_V=36.8e3,
    high_current_A=10.0e3,
    system_voltage_V=11.0e3,
    source="Vollet e de Metz-Noblat, IPST 2007 — para-raios do motor",
)

#: Para-raios do CUBÍCULO (barra) do mesmo caso: 21,6 kV a 3 mA e
#: 76,9 kV a 40 kA [LITERATURA: idem].
VOLLET_BUS_ARRESTER: ArresterPoints = ArresterPoints(
    low_voltage_V=21.6e3,
    low_current_A=3.0e-3,
    high_voltage_V=76.9e3,
    high_current_A=40.0e3,
    system_voltage_V=11.0e3,
    source="Vollet e de Metz-Noblat, IPST 2007 — para-raios do cubículo",
)

#: Pontos por década da característica gerada. A grandeza que importa num
#: dispositivo de proteção é o erro em TENSÃO — o erro em corrente é
#: enorme por construção, porque ``i`` é uma potência de expoente 13 a 27
#: de ``v``. Com 4 pontos por década o erro de interpolação em tensão fica
#: em 0,15 % na curva do motor e 0,31 % na do cubículo; com 2 pontos, em
#: 0,59 % e 1,21 % [CÁLCULO PRÓPRIO: ver ``tests/test_emt_arrester.py``].
#: Adotado 4, que põe o erro de representação uma ordem de grandeza abaixo
#: da dispersão da própria curva publicada.
POINTS_PER_DECADE: int = 4


def exponent_from_points(points: ArresterPoints) -> float:
    """Expoente ``α`` da lei ``i = i₁·(v/v₁)^α`` que passa pelos dois pontos.

    A interpolação entre os pontos publicados é feita em log-log, isto é,
    admite-se que a característica seja uma reta nesse plano. É a ÚNICA
    inferência sobre a forma da curva feita neste módulo, e é a
    representação corrente de um varistor de ZnO [CÁLCULO PRÓPRIO].

    Para o para-raios do motor de Vollet o ajuste dá ``α = 26,58``; para o
    do cubículo, ``α = 12,92`` — ambos dentro da ordem de grandeza
    esperada para ZnO.
    """
    return float(
        math.log(points.high_current_A / points.low_current_A)
        / math.log(points.high_voltage_V / points.low_voltage_V)
    )


def characteristic_from_points(
    points: ArresterPoints,
    *,
    scale: float = 1.0,
    points_per_decade: int = POINTS_PER_DECADE,
    name: str | None = None,
) -> PiecewiseLinearVI:
    """Característica por trechos gerada a partir dos dois pontos publicados.

    Parameters
    ----------
    points:
        Pontos publicados.
    scale:
        Fator aplicado às TENSÕES, e apenas a elas. Serve para transpor um
        para-raios publicado para outra tensão de sistema; ver
        :func:`scale_for_system_voltage`.
    points_per_decade:
        Densidade da amostragem em corrente.
    name:
        Rótulo; padrão derivado da procedência.

    Raises
    ------
    ValueError
        ``scale`` ou ``points_per_decade`` inválidos.
    """
    k = float(scale)
    if not math.isfinite(k) or k <= 0.0:
        raise ValueError(f"scale deve ser finito e > 0, obtido {scale!r}")
    n = int(points_per_decade)
    if n < 1:
        raise ValueError(f"points_per_decade deve ser >= 1, obtido {points_per_decade!r}")

    alpha = exponent_from_points(points)
    decadas = math.log10(points.high_current_A / points.low_current_A)
    n_pontos = max(2, int(round(decadas * n)) + 1)
    i = np.logspace(
        math.log10(points.low_current_A),
        math.log10(points.high_current_A),
        n_pontos,
    )
    v = k * points.low_voltage_V * (i / points.low_current_A) ** (1.0 / alpha)
    return PiecewiseLinearVI(
        voltage_V=tuple(float(x) for x in v),
        current_A=tuple(float(x) for x in i),
        name=name or f"MOA({points.source})",
    )


def scale_for_system_voltage(
    points: ArresterPoints, system_voltage_V: float
) -> float:
    """Fator de escala de tensão para transpor o para-raios a outro sistema.

    O escalonamento é PROPORCIONAL à tensão nominal do sistema. A razão é
    a regra de seleção corrente: a tensão de operação contínua do
    para-raios acompanha a tensão fase-terra do sistema, e a tensão
    residual acompanha a de operação contínua para uma mesma classe de
    varistor [INFERÊNCIA a partir da prática de seleção — NÃO é dado das
    fontes primárias, que publicam a curva de um caso de 11 kV].

    A consequência precisa ser dita quando o resultado for citado: um
    para-raios real de 4,16 kV tem curva de catálogo, e o escalonamento
    aqui só garante que a MARGEM DE PROTEÇÃO relativa seja a do caso
    publicado.

    Raises
    ------
    ValueError
        Tensão de sistema não finita ou não positiva.
    """
    u = float(system_voltage_V)
    if not math.isfinite(u) or u <= 0.0:
        raise ValueError(f"system_voltage_V deve ser finito e > 0, obtido {u!r}")
    return u / float(points.system_voltage_V)


# ---------------------------------------------------------------------------
# O ramo
# ---------------------------------------------------------------------------


class MetalOxideArrester(CompensatedBranch):
    """Para-raios de óxido metálico como ramo compensado.

    Parameters
    ----------
    name:
        Rótulo do ramo.
    node_p, node_n:
        Terminais; ``node_n`` é tipicamente a terra.
    characteristic:
        Característica ``v-i``. Use :func:`characteristic_from_points` ou
        :meth:`from_published`.

    Notes
    -----
    O para-raios NÃO limita o número de reignições, apenas a amplitude —
    *"arresters do not limit the multiple reignitions"*
    [LITERATURA: Vollet 2007, p. 5]. Uma simulação em que a contagem de
    reignições caia ao inserir o para-raios deve ser examinada: o efeito
    esperado é sobre a tensão, não sobre a contagem.
    """

    @classmethod
    def from_published(
        cls,
        name: str,
        node_p: str,
        node_n: str,
        *,
        points: ArresterPoints = VOLLET_MOTOR_ARRESTER,
        system_voltage_V: float | None = None,
        points_per_decade: int = POINTS_PER_DECADE,
    ) -> "MetalOxideArrester":
        """Constrói a partir de uma curva publicada, opcionalmente escalada.

        Parameters
        ----------
        points:
            Curva publicada; padrão, o para-raios de motor de Vollet.
        system_voltage_V:
            Tensão do sistema de aplicação [V]. ``None`` (padrão) usa a
            curva como publicada, sem escalonamento.
        points_per_decade:
            Densidade da característica gerada.
        """
        escala = (
            1.0
            if system_voltage_V is None
            else scale_for_system_voltage(points, float(system_voltage_V))
        )
        return cls(
            name,
            node_p,
            node_n,
            characteristic_from_points(
                points, scale=escala, points_per_decade=points_per_decade, name=name
            ),
        )

    @property
    def protective_level_V(self) -> float:
        """Tensão residual no ponto de maior corrente caracterizado [V]."""
        v, _i = self.characteristic.max_point
        return float(v)

    @property
    def reference_voltage_V(self) -> float:
        """Tensão do joelho — o primeiro ponto caracterizado [V]."""
        return float(self.characteristic.knee_voltage_V)


def three_phase_arrester(
    prefix: str,
    nodes_abc: Sequence[str],
    node_ref: str,
    *,
    points: ArresterPoints = VOLLET_MOTOR_ARRESTER,
    system_voltage_V: float | None = None,
    points_per_decade: int = POINTS_PER_DECADE,
) -> tuple[MetalOxideArrester, ...]:
    """Um para-raios por fase, contra a referência comum.

    Parameters
    ----------
    prefix:
        Prefixo; gera ``<prefix>_a``, ``<prefix>_b``, ``<prefix>_c``.
    nodes_abc:
        Nós de fase.
    node_ref:
        Nó de referência (terra).
    points, system_voltage_V, points_per_decade:
        Como em :meth:`MetalOxideArrester.from_published`.

    Raises
    ------
    ValueError
        Lista de nós vazia.
    """
    nodes = tuple(str(n) for n in nodes_abc)
    if not nodes:
        raise ValueError("three_phase_arrester exige pelo menos um nó de fase")
    labels = (
        ("a", "b", "c") if len(nodes) == 3 else tuple(str(k) for k in range(len(nodes)))
    )
    return tuple(
        MetalOxideArrester.from_published(
            f"{prefix}_{lbl}",
            node,
            str(node_ref),
            points=points,
            system_voltage_V=system_voltage_V,
            points_per_decade=points_per_decade,
        )
        for lbl, node in zip(labels, nodes)
    )


# ---------------------------------------------------------------------------
# Limitações
# ---------------------------------------------------------------------------

KNOWN_LIMITATIONS: dict[str, str] = {
    "emt_arrester_two_point_curve": (
        "As fontes primárias acessadas publicam DOIS pontos da curva v-i "
        "de cada para-raios (Vollet 2007: 18,4 kV a 0,1 mA e 36,8 kV a "
        "10 kA no motor; 21,6 kV a 3 mA e 76,9 kV a 40 kA na barra). Os "
        "pontos intermediários deste módulo vêm de interpolação log-log "
        "entre eles [CÁLCULO PRÓPRIO], não de catálogo. O expoente "
        "ajustado (26,58 e 12,92) é plausível para ZnO, mas a curva "
        "resultante é uma RECONSTRUÇÃO."
    ),
    "emt_arrester_scaling_by_system_voltage": (
        "A transposição de um para-raios publicado para outra tensão de "
        "sistema é feita escalando as tensões pela razão das tensões "
        "nominais. É a prática de seleção (a tensão de operação contínua "
        "acompanha a fase-terra do sistema), mas NÃO é dado das fontes: um "
        "para-raios real de 4,16 kV tem curva de catálogo. O que o "
        "escalonamento preserva é a MARGEM DE PROTEÇÃO relativa do caso "
        "publicado, e é isso — e só isso — que um resultado escalado pode "
        "afirmar."
    ),
    "emt_arrester_no_energy_rating": (
        "Não há capacidade de absorção de energia nem critério de falha "
        "térmica: o ramo conduz indefinidamente qualquer corrente. A "
        "energia acumulada é medida (``energy_J``) e deve ser confrontada "
        "MANUALMENTE com a classe de descarga do para-raios escolhido; um "
        "resultado em que a energia exceda a classe descreve um para-raios "
        "que teria falhado."
    ),
}


__all__ = [
    "KNOWN_LIMITATIONS",
    "POINTS_PER_DECADE",
    "VOLLET_BUS_ARRESTER",
    "VOLLET_MOTOR_ARRESTER",
    "ArresterPoints",
    "MetalOxideArrester",
    "characteristic_from_points",
    "exponent_from_points",
    "scale_for_system_voltage",
    "three_phase_arrester",
]
