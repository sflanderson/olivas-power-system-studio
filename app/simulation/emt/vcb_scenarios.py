"""
app.simulation.emt.vcb_scenarios — parâmetros de disjuntor a vácuo como
faixas da LITERATURA, e não como constantes de um caso.

Por que este módulo existe
===========================

O caso de referência deste projeto fixa os três parâmetros que governam a
severidade da manobra — taxa de recuperação dielétrica (RRDS), capacidade
de extinção de corrente de alta frequência (di/dt crítico) e corrente de
corte — em valores que estão **fora da faixa publicada**, todos no sentido
de agravar o transitório:

============================  =====================  ========================
Parâmetro                     Caso de referência     Literatura primária
============================  =====================  ========================
RRDS                          0,801·t + 1,226·t²     20–50 kV/ms linear
                              (kV, t em ms) →        [Wong 2003; Vollet 2007];
                              2,0 kV em 1 ms         5,5 kV/ms medido
                                                     [Abdulahovic 2011]
di/dt de extinção             5–15 A/µs              100–600 A/µs (até 1000);
                                                     250–350 A/µs medido
Corrente de corte             1–2 A                  2–10 A (contatos Cu/Cr)
Pico resultante               8,9–12,2 pu            teto de 4,3–4,6 pu em
                                                     campo e em simulação
============================  =====================  ========================

Um disjuntor de recuperação 10 a 25 vezes mais lenta e extinção 7 a 120
vezes mais fácil é a combinação que **maximiza** o número de reignições.
Reproduzir esse ponto do espaço de parâmetros não valida nada: reproduz a
escolha. O que a literatura sustenta é uma FAIXA, e a severidade da manobra
é uma distribuição sobre ela — não um número.

Daí o desenho deste módulo: os parâmetros entram como
:class:`VcbParameterRanges`, o instante de separação entra como variável
aleatória (é ele que decide se o polo abre perto ou longe do zero de
corrente), e o resultado é uma amostra, não um valor.

Convenção de extinção de alta frequência
=========================================

A extinção ocorre quando o ``di/dt`` na passagem por zero está **dentro**
da capacidade do disjuntor. Wong, Snider e Lo escrevem, sobre o limite:
*"when the absolute value of the rate-of-change … above this di/dt limit,
arc extinction will not occur"* — isto é, acima do limite o arco
**persiste** [LITERATURA: Wong, Snider e Lo, IPST 2003]. O caso de
referência executa a condição invertida; ver
``docs/research/rul_isolamento/07_AUDITORIA_DO_CASO_ATP.md``.

Fontes
=======

* WONG, S. M.; SNIDER, L. A.; LO, E. W. C. Overvoltages and reignition
  behavior of vacuum circuit breaker. In: IPST 2003, New Orleans, paper
  03IPST14a-03. https://www.ipstconf.org/papers/Proc_IPST2003/03IPST14a-03.pdf
* VOLLET, C.; DE METZ-NOBLAT, B. Vacuum circuit breaker model: application
  case to motors switching. In: IPST 2007, Lyon, paper 07IPST106.
  https://www.ipstconf.org/papers/Proc_IPST2007/07IPST106.pdf
* ABDULAHOVIC, T. Analysis of High-Frequency Electrical Transients in
  Offshore Wind Parks. Tese (Doutorado), Chalmers, 2011.
  https://publications.lib.chalmers.se/records/fulltext/148759/148759.pdf

O levantamento consolidado, com a verificação de cada valor, está em
``docs/research/rul_isolamento/anexos/pesquisa/fisica_surtos_vcb_isolamento.md``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, replace
from typing import Iterator, Sequence

import numpy as np

from app.core.logging_config import get_logger

from .vcb import (
    DIDT_INTERRUPT_WITHIN,
    DielectricRecovery,
    LinearRecovery,
    ParabolicRecovery,
)

logger = get_logger(__name__)

__all__ = [
    "DOC_A_SCENARIO",
    "FIELD_PEAK_CEILING_PU",
    "LITERATURE_CHOPPING_RANGE_A",
    "LITERATURE_DIDT_RANGE_A_PER_US",
    "LITERATURE_RRDS_RANGE_KV_PER_MS",
    "LITERATURE_SCENARIO",
    "MEASURED_SCENARIO",
    "SCENARIOS",
    "VcbParameterRanges",
    "VcbSample",
    "sample_vcb_parameters",
    "scenario",
    "sweep_samples",
]


# ---------------------------------------------------------------------------
# Faixas da literatura
# ---------------------------------------------------------------------------

#: Corrente de corte de contatos Cu/Cr [A]. "Typically 2 to 10 A"
#: [LITERATURA: Vollet e de Metz-Noblat, IPST 2007].
LITERATURE_CHOPPING_RANGE_A: tuple[float, float] = (2.0, 10.0)

#: Capacidade de extinção de corrente de alta frequência [A/µs]. A faixa
#: publicada vai de 100 a 600 A/µs, com relatos até 1000; a medição em
#: disjuntor comercial deu 250–350 A/µs [LITERATURA: Abdulahovic 2011;
#: Wong, Snider e Lo, IPST 2003].
LITERATURE_DIDT_RANGE_A_PER_US: tuple[float, float] = (100.0, 600.0)

#: Taxa de recuperação dielétrica LINEAR [kV/ms]. Vollet adota 20 ou
#: 40 kV/ms; Wong varre 20–50; a medição em disjuntor comercial deu
#: 5,5 kV/ms na fase inicial [LITERATURA: Vollet 2007; Wong 2003;
#: Abdulahovic 2011]. A faixa larga cobre as três fontes.
LITERATURE_RRDS_RANGE_KV_PER_MS: tuple[float, float] = (5.0, 50.0)

#: Faixa de RRDS em que a escalada é MAIS severa [kV/ms]. Wong mostra que
#: a escalada é máxima em RRDS intermediária: recuperação rápida demais
#: impede a reignição, lenta demais permite a extinção no primeiro zero
#: de alta frequência [LITERATURA: Wong, Snider e Lo, IPST 2003].
LITERATURE_RRDS_WORST_KV_PER_MS: tuple[float, float] = (20.0, 30.0)

#: Teto de sobretensão observado em campo e em simulação [pu de pico
#: fase-terra]. Campanha EPRI com 33 motores e mais de 700 manobras:
#: ~3 pu em operação normal, até 4,6 pu; simulação com escalada: 4,3 pu
#: [LITERATURA: Gupta et al. via whitepaper Baker/SKF; Xemard et al.,
#: IPST 2019]. Serve de baliza de sanidade, não de limite físico.
FIELD_PEAK_CEILING_PU: float = 4.6

#: Tempo de arco em que a escalada é mais provável [s]: separação de
#: contatos a menos de 100 µs de um zero de corrente
#: [LITERATURA: Wong, Snider e Lo, IPST 2003].
LITERATURE_WORST_ARC_TIME_S: tuple[float, float] = (0.0, 100.0e-6)


# ---------------------------------------------------------------------------
# Faixas parametrizáveis
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class VcbParameterRanges:
    """Faixas dos parâmetros de um disjuntor a vácuo, com sua procedência.

    Cada campo é um par ``(mínimo, máximo)``. Amostrar de uma faixa é o
    ponto: os fabricantes não publicam esses valores (exceto a corrente
    máxima de corte de contatores), e a calibração por medição é possível
    mas laboriosa [LITERATURA: Abdulahovic 2011]. Enquanto não houver
    medição do disjuntor específico, a faixa É o dado.

    Attributes
    ----------
    name:
        Rótulo do cenário, propagado ao resultado para rastreabilidade.
    chopping_A:
        Corrente de corte [A].
    didt_A_per_us:
        Capacidade de extinção de corrente de alta frequência [A/µs].
    rrds_kV_per_ms:
        Taxa de recuperação dielétrica [kV/ms], modelo LINEAR.
    rrds_parabolic_kV_per_ms2:
        Termo quadrático [kV/ms²]. ``None`` (padrão) usa recuperação
        linear, que é a forma adotada pelas fontes primárias. Um valor
        numérico ativa a forma parabólica ``A·t + B·t²``.
    source:
        Procedência declarada, citada no relatório.
    within_literature:
        ``False`` marca o cenário como fora da faixa publicada. Não
        impede o uso — impede que o resultado seja lido como típico.
    """

    name: str
    chopping_A: tuple[float, float] = LITERATURE_CHOPPING_RANGE_A
    didt_A_per_us: tuple[float, float] = LITERATURE_DIDT_RANGE_A_PER_US
    rrds_kV_per_ms: tuple[float, float] = LITERATURE_RRDS_RANGE_KV_PER_MS
    rrds_parabolic_kV_per_ms2: float | None = None
    source: str = ""
    within_literature: bool = True

    def __post_init__(self) -> None:
        for campo in ("chopping_A", "didt_A_per_us", "rrds_kV_per_ms"):
            lo, hi = getattr(self, campo)
            lo, hi = float(lo), float(hi)
            if not (math.isfinite(lo) and math.isfinite(hi)):
                raise ValueError(f"{campo}: limites devem ser finitos, obtido {(lo, hi)!r}")
            if lo <= 0.0:
                raise ValueError(f"{campo}: o limite inferior deve ser > 0, obtido {lo!r}")
            if hi < lo:
                raise ValueError(f"{campo}: máximo {hi!r} menor que mínimo {lo!r}")
        if self.rrds_parabolic_kV_per_ms2 is not None:
            b = float(self.rrds_parabolic_kV_per_ms2)
            if not math.isfinite(b) or b < 0.0:
                raise ValueError(
                    f"rrds_parabolic_kV_per_ms2 deve ser None ou finito e >= 0, obtido {b!r}"
                )
        if not str(self.name).strip():
            raise ValueError("name não pode ser vazio")

    def narrowed_to_worst_case(self) -> "VcbParameterRanges":
        """Restringe a RRDS à faixa de escalada máxima de Wong 2003.

        Útil para o cenário de pior caso PLAUSÍVEL — que não é o mesmo
        que o pior caso possível: RRDS abaixo de 20 kV/ms permite que o
        arco se extinga no primeiro zero de alta frequência, e acima de
        30 kV/ms impede a reignição [LITERATURA: Wong 2003].
        """
        return replace(
            self,
            name=f"{self.name}_pior_caso",
            rrds_kV_per_ms=LITERATURE_RRDS_WORST_KV_PER_MS,
        )


#: Cenário padrão: faixas da literatura primária, recuperação linear.
LITERATURE_SCENARIO = VcbParameterRanges(
    name="literatura",
    source=(
        "Wong, Snider e Lo (IPST 2003); Vollet e de Metz-Noblat (IPST 2007); "
        "Abdulahovic (Chalmers, 2011)"
    ),
)

#: Cenário calibrado por medição em disjuntor comercial. Faixas estreitas
#: em torno dos valores medidos [LITERATURA: Abdulahovic 2011: RRDS
#: inicial 5,5 kV/ms; di/dt 250–350 A/µs; corte 2,5–5 A].
MEASURED_SCENARIO = VcbParameterRanges(
    name="medido",
    chopping_A=(2.5, 5.0),
    didt_A_per_us=(250.0, 350.0),
    rrds_kV_per_ms=(5.0, 6.0),
    source="Abdulahovic (Chalmers, 2011), medição em disjuntor comercial",
    within_literature=True,
)

#: Cenário do caso de referência. **Fora da faixa publicada nos três
#: parâmetros**, todos no sentido de agravar o transitório. Preservado
#: para reprodutibilidade e para o confronto, nunca como valor típico.
DOC_A_SCENARIO = VcbParameterRanges(
    name="caso_de_referencia",
    chopping_A=(1.0, 2.0),
    didt_A_per_us=(5.0, 15.0),
    rrds_kV_per_ms=(0.801, 0.801),
    rrds_parabolic_kV_per_ms2=1.226,
    source="arquivo de dados do caso de referência (tests/fixtures/atp)",
    within_literature=False,
)

SCENARIOS: dict[str, VcbParameterRanges] = {
    s.name: s
    for s in (LITERATURE_SCENARIO, MEASURED_SCENARIO, DOC_A_SCENARIO)
}


def scenario(name: str) -> VcbParameterRanges:
    """Cenário por nome. Emite aviso ao devolver um cenário fora da faixa."""
    try:
        s = SCENARIOS[str(name)]
    except KeyError:
        raise ValueError(
            f"cenário desconhecido {name!r}; disponíveis: {sorted(SCENARIOS)}"
        ) from None
    if not s.within_literature:
        logger.warning(
            "cenário %r está FORA da faixa publicada nos parâmetros de disjuntor; "
            "os resultados não devem ser lidos como típicos (ver vcb_scenarios)",
            s.name,
        )
    return s


# ---------------------------------------------------------------------------
# Amostragem
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class VcbSample:
    """Uma realização dos parâmetros de um polo.

    Attributes
    ----------
    scenario_name:
        Cenário de origem.
    chopping_current_A, didt_capability_A_per_us:
        Valores amostrados.
    rrds_a_kV_per_ms, rrds_b_kV_per_ms2:
        Coeficientes da recuperação dielétrica. ``rrds_b`` é ``0`` na
        forma linear.
    separation_time_s:
        Instante de separação dos contatos [s].
    arc_time_s:
        Tempo entre a separação e o zero de corrente seguinte [s],
        quando informado ao amostrador. É a variável que mais governa a
        escalada [LITERATURA: Wong 2003].
    """

    scenario_name: str
    chopping_current_A: float
    didt_capability_A_per_us: float
    rrds_a_kV_per_ms: float
    rrds_b_kV_per_ms2: float
    separation_time_s: float
    arc_time_s: float | None = None

    def recovery(self) -> DielectricRecovery:
        """Modelo de recuperação dielétrica desta realização.

        A forma linear das fontes primárias parte da origem
        (``V_wth = 0`` na extinção do arco) e sobe com a taxa amostrada.
        A identidade de unidades é exata: ``1 kV/ms = 1 V/µs``
        [CÁLCULO PRÓPRIO], de modo que a taxa em kV/ms entra sem
        conversão no campo ``k_V_per_us``.
        """
        if self.rrds_b_kV_per_ms2 > 0.0:
            return ParabolicRecovery(
                a_kV_per_ms=self.rrds_a_kV_per_ms,
                b_kV_per_ms2=self.rrds_b_kV_per_ms2,
            )
        return LinearRecovery(u0_V=0.0, k_V_per_us=self.rrds_a_kV_per_ms)

    def as_pole_kwargs(self) -> dict:
        """Argumentos para ``VacuumCircuitBreakerModel``.

        A convenção de extinção é a FÍSICA (``interrupt_within``): o arco
        se extingue quando o ``di/dt`` está dentro da capacidade
        [LITERATURA: Wong 2003].
        """
        return {
            "separation_time_s": self.separation_time_s,
            "chopping_current_A": self.chopping_current_A,
            "recovery": self.recovery(),
            "didt_capability_A_per_us": self.didt_capability_A_per_us,
            "didt_convention": DIDT_INTERRUPT_WITHIN,
        }


def _uniform(rng: np.random.Generator, faixa: tuple[float, float]) -> float:
    lo, hi = float(faixa[0]), float(faixa[1])
    return lo if hi <= lo else float(rng.uniform(lo, hi))


def sample_vcb_parameters(
    ranges: VcbParameterRanges,
    *,
    rng: np.random.Generator,
    separation_window_s: tuple[float, float],
) -> VcbSample:
    """Sorteia uma realização dos parâmetros de um polo.

    O instante de separação é sorteado uniformemente na janela: não há
    razão física para privilegiar um instante do ciclo, e é justamente a
    posição da separação em relação ao zero de corrente que decide entre
    corte simples e escalada [LITERATURA: Wong 2003].

    Parameters
    ----------
    ranges:
        Faixas do cenário.
    rng:
        Gerador. Passar um gerador semeado torna a varredura reprodutível.
    separation_window_s:
        Janela ``(início, fim)`` do instante de separação [s].

    Raises
    ------
    ValueError
        Janela de separação inválida.
    """
    t0, t1 = float(separation_window_s[0]), float(separation_window_s[1])
    if not (math.isfinite(t0) and math.isfinite(t1)) or t0 < 0.0 or t1 < t0:
        raise ValueError(
            f"separation_window_s deve ser (início >= 0, fim >= início) finito, obtido {(t0, t1)!r}"
        )
    return VcbSample(
        scenario_name=ranges.name,
        chopping_current_A=_uniform(rng, ranges.chopping_A),
        didt_capability_A_per_us=_uniform(rng, ranges.didt_A_per_us),
        rrds_a_kV_per_ms=_uniform(rng, ranges.rrds_kV_per_ms),
        rrds_b_kV_per_ms2=float(ranges.rrds_parabolic_kV_per_ms2 or 0.0),
        separation_time_s=t0 if t1 <= t0 else float(rng.uniform(t0, t1)),
    )


def sweep_samples(
    ranges: VcbParameterRanges,
    *,
    n: int,
    separation_window_s: tuple[float, float],
    seed: int = 0,
) -> list[VcbSample]:
    """``n`` realizações reprodutíveis do cenário.

    Raises
    ------
    ValueError
        ``n`` não positivo.
    """
    if int(n) <= 0:
        raise ValueError(f"n deve ser > 0, obtido {n!r}")
    rng = np.random.default_rng(int(seed))
    return [
        sample_vcb_parameters(
            ranges, rng=rng, separation_window_s=separation_window_s
        )
        for _ in range(int(n))
    ]
