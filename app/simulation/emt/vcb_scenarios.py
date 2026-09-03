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

import cmath
import math
from dataclasses import dataclass, field, replace
from typing import Iterator, Sequence

import numpy as np

from app.core.logging_config import get_logger

from .vcb import (
    DIDT_INTERRUPT_WITHIN,
    WONG_EXTINCTION_LAWS,
    DielectricRecovery,
    LinearExtinction,
    LinearRecovery,
    ParabolicRecovery,
)

logger = get_logger(__name__)

__all__ = [
    "DOC_A_SCENARIO",
    "LITERATURE_WORST_ARC_TIME_S",
    "LITERATURE_RRDS_WORST_KV_PER_MS",
    "PoleCurrentZeros",
    "FIELD_PEAK_CEILING_PU",
    "LITERATURE_CHOPPING_RANGE_A",
    "LITERATURE_DIDT_RANGE_A_PER_US",
    "LITERATURE_RRDS_RANGE_KV_PER_MS",
    "LITERATURE_SCENARIO",
    "MEASURED_SCENARIO",
    "WONG_SCENARIO",
    "SCENARIOS",
    "VcbParameterRanges",
    "VcbSample",
    "sample_vcb_parameters",
    "sample_vcb_parameters_by_arc_time",
    "scenario",
    "sweep_samples",
    "sweep_three_pole_samples",
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
    extinction_laws:
        Pares ``(C, D)`` da lei ``di/dt = C·(t − t_sep) + D``, em
        ``(A/µs², A/µs)``. ``None`` (padrão) amostra ``D`` de
        ``didt_A_per_us`` com ``C = 0``, isto é, capacidade CONSTANTE.
        Uma tupla de pares faz o amostrador escolher UM deles: são
        alternativas discretas publicadas, não uma faixa contínua
        [LITERATURA: Wong, Snider e Lo, IPST 2003, p. 1-2].
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
    extinction_laws: tuple[tuple[float, float], ...] | None = None
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
        if self.extinction_laws is not None:
            leis = tuple(self.extinction_laws)
            if not leis:
                raise ValueError("extinction_laws não pode ser uma tupla vazia")
            for c, d in leis:
                if not (math.isfinite(float(c)) and math.isfinite(float(d))):
                    raise ValueError(
                        f"extinction_laws: par não finito {(c, d)!r}"
                    )
                if float(d) <= 0.0:
                    raise ValueError(
                        f"extinction_laws: D deve ser > 0, obtido {d!r}"
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

#: Cenário com a lei de extinção DEPENDENTE DO TEMPO de Wong, em vez da
#: capacidade constante. É o cenário do critério de aceitação: Wong
#: identifica a escalada máxima em RRDS intermediária (20 a 30 kV/ms)
#: justamente na combinação com capacidade de inclinação NEGATIVA
#: [LITERATURA: Wong, Snider e Lo, IPST 2003, p. 5-6]. Com capacidade
#: constante essa dependência não pode aparecer, porque nada distingue
#: o início do fim da abertura.
WONG_SCENARIO = VcbParameterRanges(
    name="wong",
    extinction_laws=WONG_EXTINCTION_LAWS,
    source="Wong, Snider e Lo (IPST 2003), lei di/dt = C·(t − t_sep) + D",
)

SCENARIOS: dict[str, VcbParameterRanges] = {
    s.name: s
    for s in (LITERATURE_SCENARIO, MEASURED_SCENARIO, WONG_SCENARIO, DOC_A_SCENARIO)
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
    didt_slope_A_per_us2:
        Inclinação ``C`` da lei ``di/dt = C·(t − t_sep) + D`` [A/µs²].
        ``0`` (padrão) dá capacidade CONSTANTE, que é o caso do
        Documento A; valor não nulo ativa a lei de Wong, com ``D`` em
        ``didt_capability_A_per_us``.
    """

    scenario_name: str
    chopping_current_A: float
    didt_capability_A_per_us: float
    rrds_a_kV_per_ms: float
    rrds_b_kV_per_ms2: float
    separation_time_s: float
    arc_time_s: float | None = None
    didt_slope_A_per_us2: float = 0.0

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
            "didt_capability_A_per_us": self.extinction(),
            "didt_convention": DIDT_INTERRUPT_WITHIN,
        }

    def extinction(self):
        """Capacidade de extinção desta realização.

        Devolve o número — a capacidade CONSTANTE — quando a inclinação
        é nula, e a lei linear de Wong quando não é. O polo aceita as
        duas formas.
        """
        if self.didt_slope_A_per_us2 == 0.0:
            return self.didt_capability_A_per_us
        return LinearExtinction(
            c_A_per_us2=float(self.didt_slope_A_per_us2),
            d_A_per_us=float(self.didt_capability_A_per_us),
        )


def _uniform(rng: np.random.Generator, faixa: tuple[float, float]) -> float:
    lo, hi = float(faixa[0]), float(faixa[1])
    return lo if hi <= lo else float(rng.uniform(lo, hi))


def _extincao(
    rng: np.random.Generator, ranges: VcbParameterRanges
) -> tuple[float, float]:
    """Sorteia ``(D, C)`` da capacidade de extinção.

    Sem ``extinction_laws`` o ``D`` sai da faixa contínua e ``C`` é nulo —
    capacidade constante. Com ``extinction_laws``, escolhe UM dos pares
    publicados, porque são alternativas discretas e não uma faixa.
    """
    if ranges.extinction_laws is None:
        return _uniform(rng, ranges.didt_A_per_us), 0.0
    leis = tuple(ranges.extinction_laws)
    c, d = leis[int(rng.integers(len(leis)))]
    return float(d), float(c)


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
    # A ORDEM dos sorteios é parte do contrato: mudá-la muda a realização
    # produzida por uma mesma semente e invalida os conjuntos de dados já
    # publicados. É corte, extinção, RRDS, separação.
    corte = _uniform(rng, ranges.chopping_A)
    d, c = _extincao(rng, ranges)
    rrds = _uniform(rng, ranges.rrds_kV_per_ms)
    return VcbSample(
        scenario_name=ranges.name,
        chopping_current_A=corte,
        didt_capability_A_per_us=d,
        rrds_a_kV_per_ms=rrds,
        rrds_b_kV_per_ms2=float(ranges.rrds_parabolic_kV_per_ms2 or 0.0),
        separation_time_s=t0 if t1 <= t0 else float(rng.uniform(t0, t1)),
        didt_slope_A_per_us2=c,
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


# ---------------------------------------------------------------------------
# Amostragem por TEMPO DE ARCO
# ---------------------------------------------------------------------------
#
# Sortear o instante de separação uniformemente no ciclo é correto quanto à
# física, mas ineficiente quanto à amostragem: a janela em que a escalada é
# provável — tempo de arco de 0 a 100 µs [LITERATURA: Wong, Snider e Lo,
# IPST 2003, p. 5-6] — ocupa 1,2 % de um ciclo de 60 Hz (100 µs sobre os
# 8,333 ms entre zeros consecutivos) [CÁLCULO PRÓPRIO]. Uma varredura de
# 100 realizações cai nessa janela cerca de uma vez.
#
# A variável de controle é, portanto, o tempo de arco, e não o instante
# absoluto. É também a variável que a IEC 62271-110:2023 manda determinar
# em ensaio, sob o nome de "re-ignition-free arcing time window", para fins
# de chaveamento controlado [NORMA: IEC 62271-110:2023, 3.7 e 4.1].


@dataclass(frozen=True)
class PoleCurrentZeros:
    """Zeros da corrente de um polo, em regime permanente senoidal.

    Enquanto a chave está fechada, a corrente do polo é a de regime. Com a
    referência cosseno de amplitude adotada no projeto,
    ``i(t) = |I|·cos(ωt + φ)``, e os zeros são os instantes em que
    ``ωt + φ = π/2 + kπ`` [CÁLCULO PRÓPRIO]. A expressão é exata até o
    primeiro zero após a separação — que é justamente o intervalo sobre o
    qual o tempo de arco se define.

    Attributes
    ----------
    phase_angle_rad:
        Ângulo ``φ`` do fasor de corrente do polo [rad].
    frequency_Hz:
        Frequência fundamental [Hz].
    """

    phase_angle_rad: float
    frequency_Hz: float = 60.0

    def __post_init__(self) -> None:
        if not math.isfinite(self.phase_angle_rad):
            raise ValueError(
                f"phase_angle_rad deve ser finito, obtido {self.phase_angle_rad!r}"
            )
        if not (math.isfinite(self.frequency_Hz) and self.frequency_Hz > 0.0):
            raise ValueError(
                f"frequency_Hz deve ser finita e > 0, obtido {self.frequency_Hz!r}"
            )

    @classmethod
    def from_phasor(cls, phasor: complex, frequency_Hz: float = 60.0) -> "PoleCurrentZeros":
        """Constrói a partir do fasor de corrente do polo.

        Raises
        ------
        ValueError
            Fasor nulo — sem zeros definidos.
        """
        if abs(complex(phasor)) <= 0.0:
            raise ValueError("fasor de corrente nulo: os zeros não estão definidos")
        return cls(
            phase_angle_rad=float(cmath.phase(complex(phasor))),
            frequency_Hz=float(frequency_Hz),
        )

    @property
    def omega_rad_s(self) -> float:
        """``ω = 2πf`` [rad/s]."""
        return 2.0 * math.pi * float(self.frequency_Hz)

    @property
    def half_period_s(self) -> float:
        """Intervalo entre zeros consecutivos, ``T/2`` [s]."""
        return 0.5 / float(self.frequency_Hz)

    def _zero_at_index(self, k: int) -> float:
        return (0.5 * math.pi + k * math.pi - self.phase_angle_rad) / self.omega_rad_s

    def first_zero_after(self, t: float) -> float:
        """Primeiro zero de corrente estritamente após ``t`` [s]."""
        t = float(t)
        k = (
            math.floor(
                (self.omega_rad_s * t + self.phase_angle_rad - 0.5 * math.pi) / math.pi
            )
            + 1
        )
        tz = self._zero_at_index(k)
        while tz <= t:  # guarda contra arredondamento na fronteira
            k += 1
            tz = self._zero_at_index(k)
        return tz

    def first_zero_at_or_after(self, t: float, *, rel_tol: float = 1.0e-9) -> float:
        """Primeiro zero de corrente em ``t`` ou depois [s].

        Difere de :meth:`first_zero_after` no ponto de fronteira: separar
        os contatos exatamente sobre um zero interrompe ali mesmo, e não
        meio ciclo adiante. ``rel_tol`` é a tolerância de fronteira em
        frações de meio período — o padrão, ``1e-9``, vale 8,3 ps em
        60 Hz [CÁLCULO PRÓPRIO].
        """
        t = float(t)
        x = (
            self.omega_rad_s * t + self.phase_angle_rad - 0.5 * math.pi
        ) / math.pi
        k = math.ceil(x - float(rel_tol))
        return self._zero_at_index(k)

    def arc_time_after(self, separation_time_s: float) -> float:
        """Tempo de arco resultante de separar os contatos em ``t`` [s].

        É a distância até o zero de corrente em que a interrupção é
        tentada. Separação sobre o próprio zero dá tempo de arco nulo.
        """
        t = float(separation_time_s)
        return max(0.0, self.first_zero_at_or_after(t) - t)

    def separation_for_arc_time(
        self, arc_time_s: float, *, earliest_separation_s: float = 0.0
    ) -> float:
        """Instante de separação que produz o tempo de arco pedido [s].

        Escolhe o primeiro zero de corrente compatível com o piso
        ``earliest_separation_s`` e recua ``arc_time_s`` a partir dele.

        Raises
        ------
        ValueError
            Tempo de arco negativo, não finito ou maior ou igual a ``T/2``
            — acima de meio período o recuo cruzaria um zero anterior e o
            tempo de arco realizado não seria o pedido.
        """
        tau = float(arc_time_s)
        if not math.isfinite(tau) or tau < 0.0:
            raise ValueError(f"arc_time_s deve ser finito e >= 0, obtido {arc_time_s!r}")
        if tau >= self.half_period_s:
            raise ValueError(
                "arc_time_s deve ser < T/2 = "
                f"{self.half_period_s:.6g} s, obtido {tau!r}: acima de meio período "
                "o recuo atravessa um zero anterior e o tempo de arco realizado "
                "difere do pedido"
            )
        piso = float(earliest_separation_s)
        if not math.isfinite(piso) or piso < 0.0:
            raise ValueError(
                f"earliest_separation_s deve ser finito e >= 0, obtido {earliest_separation_s!r}"
            )
        return self.first_zero_at_or_after(piso + tau) - tau


def sample_vcb_parameters_by_arc_time(
    ranges: VcbParameterRanges,
    *,
    rng: np.random.Generator,
    zeros: PoleCurrentZeros,
    arc_time_window_s: tuple[float, float] = LITERATURE_WORST_ARC_TIME_S,
    earliest_separation_s: float = 0.0,
) -> VcbSample:
    """Sorteia uma realização com o TEMPO DE ARCO como variável de controle.

    Os três parâmetros do disjuntor são sorteados como em
    :func:`sample_vcb_parameters`; o que muda é o instante de separação,
    aqui derivado do tempo de arco sorteado e dos zeros da corrente do
    polo.

    Parameters
    ----------
    ranges:
        Faixas do cenário.
    rng:
        Gerador semeado.
    zeros:
        Zeros da corrente do polo.
    arc_time_window_s:
        Janela ``(mín, máx)`` do tempo de arco [s]. O padrão é a janela em
        que a escalada é mais severa [LITERATURA: Wong 2003].
    earliest_separation_s:
        Piso do instante de separação [s] — tipicamente o fim da janela de
        acomodação do regime permanente.

    Raises
    ------
    ValueError
        Janela de tempo de arco inválida.
    """
    t0, t1 = float(arc_time_window_s[0]), float(arc_time_window_s[1])
    if not (math.isfinite(t0) and math.isfinite(t1)) or t0 < 0.0 or t1 < t0:
        raise ValueError(
            "arc_time_window_s deve ser (início >= 0, fim >= início) finito, "
            f"obtido {arc_time_window_s!r}"
        )
    tau = _uniform(rng, (t0, t1))
    t_sep = zeros.separation_for_arc_time(
        tau, earliest_separation_s=earliest_separation_s
    )
    # Mesma ordem do amostrador por janela — ver a nota lá.
    corte = _uniform(rng, ranges.chopping_A)
    d, c = _extincao(rng, ranges)
    rrds = _uniform(rng, ranges.rrds_kV_per_ms)
    return VcbSample(
        scenario_name=ranges.name,
        chopping_current_A=corte,
        didt_capability_A_per_us=d,
        rrds_a_kV_per_ms=rrds,
        rrds_b_kV_per_ms2=float(ranges.rrds_parabolic_kV_per_ms2 or 0.0),
        separation_time_s=t_sep,
        arc_time_s=tau,
        didt_slope_A_per_us2=c,
    )


def sweep_three_pole_samples(
    ranges: VcbParameterRanges,
    *,
    n: int,
    zeros_abc: Sequence[PoleCurrentZeros],
    arc_time_window_s: tuple[float, float] = LITERATURE_WORST_ARC_TIME_S,
    earliest_separation_s: float = 0.0,
    leading_pole: int = 0,
    seed: int = 0,
) -> list[tuple[VcbSample, VcbSample, VcbSample]]:
    """``n`` realizações de um disjuntor TRIPOLAR, uma tupla por realização.

    Os três polos de um disjuntor compartilham o mesmo acionamento, de modo
    que a separação mecânica é comum às três fases; o que difere entre elas
    é o tempo de arco, porque cada polo tem seus próprios zeros de corrente
    [CONVENÇÃO DE MODELAGEM — a dispersão mecânica entre polos, de ordem
    sub-milissegundo, é desprezada aqui]. Amostrar as três fases de forma
    independente, como faz :func:`sweep_samples`, produz um disjuntor que
    não existe.

    O sorteio é feito sobre o tempo de arco do polo ``leading_pole``; o
    instante de separação comum decorre dele, e os tempos de arco das
    outras duas fases são consequência da geometria dos zeros.

    Os parâmetros do disjuntor (corte, di/dt, RRDS) são sorteados por polo:
    são propriedades do arco e da superfície de contato, e não do
    acionamento.

    Parameters
    ----------
    ranges:
        Faixas do cenário.
    n:
        Número de realizações.
    zeros_abc:
        Zeros da corrente das três fases, na ordem ``a, b, c``.
    arc_time_window_s:
        Janela do tempo de arco do polo condutor [s].
    earliest_separation_s:
        Piso do instante de separação [s].
    leading_pole:
        Índice ``0, 1, 2`` do polo cujo tempo de arco é sorteado.
    seed:
        Semente do gerador.

    Raises
    ------
    ValueError
        ``n`` não positivo, ``zeros_abc`` sem três elementos ou
        ``leading_pole`` fora de ``0..2``.
    """
    if int(n) <= 0:
        raise ValueError(f"n deve ser > 0, obtido {n!r}")
    zeros = tuple(zeros_abc)
    if len(zeros) != 3:
        raise ValueError(f"zeros_abc deve trazer 3 polos, obtido {len(zeros)}")
    if int(leading_pole) not in (0, 1, 2):
        raise ValueError(f"leading_pole deve estar em 0..2, obtido {leading_pole!r}")

    rng = np.random.default_rng(int(seed))
    realizacoes: list[tuple[VcbSample, VcbSample, VcbSample]] = []
    for _ in range(int(n)):
        condutor = sample_vcb_parameters_by_arc_time(
            ranges,
            rng=rng,
            zeros=zeros[int(leading_pole)],
            arc_time_window_s=arc_time_window_s,
            earliest_separation_s=earliest_separation_s,
        )
        t_sep = condutor.separation_time_s
        polos: list[VcbSample] = []
        for k, z in enumerate(zeros):
            if k == int(leading_pole):
                polos.append(condutor)
                continue
            polos.append(
                replace(
                    sample_vcb_parameters(
                        ranges, rng=rng, separation_window_s=(t_sep, t_sep)
                    ),
                    arc_time_s=z.arc_time_after(t_sep),
                )
            )
        realizacoes.append((polos[0], polos[1], polos[2]))
    return realizacoes
