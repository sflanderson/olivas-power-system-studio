"""
app.postprocessor.prognosis.switching_campaign — dois caminhos de fim de vida.

Por que este módulo existe
===========================

A varredura estatística de manobras produz duas populações que **não
podem ser somadas**:

* as manobras que ficam abaixo do envelope de suportabilidade da máquina
  e a **envelhecem** — estresse a integrar por Miner;
* as que o atravessam e a **rompem** — evento terminal a contar.

Somar as segundas às primeiras, como estresse, é o erro que o módulo
impede: grampear a tensão de uma travessia reduz o estresse calculado e é
**anticonservador quanto ao dano**, além de descrever uma forma de onda
que não existe [REPO: :mod:`app.simulation.emt.flashover`, cabeçalho].

A vida da isolação é, portanto, o **mínimo** de dois caminhos:

.. math::

   N_{fim} = \\min\\big( N_{env},\\ N_{term} \\big)

com :math:`N_{env}` vindo do acumulador de dano (``D = 1``) e
:math:`N_{term}` da taxa de travessia do envelope. Reportar apenas um dos
dois é reportar metade do problema.

O caminho terminal
===================

A travessia é um processo de Bernoulli sobre manobras: cada manobra
atravessa o envelope com probabilidade :math:`p`, estimada pela fração da
varredura. O número esperado de manobras até a primeira travessia é
:math:`1/p` (média da geométrica).

Quando **nenhuma** realização atravessa — o caso da configuração com
para-raios —, a estimativa pontual é zero e não informa nada. O que se
reporta então é o limite superior: pela regra de três, com zero eventos em
:math:`n` ensaios o intervalo de confiança de 95 % vai de 0 a
:math:`3/n` [ESTATÍSTICA: aproximação padrão para proporções com zero
eventos]. Com :math:`n = 150` isso dá :math:`p \\le 2\\,\\%`, ou seja, **mais
de 50 manobras** esperadas até uma travessia — e não "nunca".

Fonte dos números do caso
==========================

``docs/research/rul_isolamento/09_PARA_RAIOS_E_CRITERIO_DE_ACEITACAO.md``,
§7.2, com os dados brutos em ``anexos/dados/varredura_vcb_n150*.json``.

Limitações
===========

Ver :data:`KNOWN_LIMITATIONS`.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, replace
from typing import Iterable, Sequence

from app.core.logging_config import get_logger

from .damage_models import CombinedDamageAccumulator, DamageModelParams
from .stress_profile import StressProfile

log = get_logger(__name__)


#: Multiplicador da regra de três para o limite superior de uma proporção
#: com ZERO eventos observados, ao nível de 95 %
#: [ESTATÍSTICA: ``p_max ≈ 3/n``, aproximação padrão].
RULE_OF_THREE: float = 3.0


@dataclass(frozen=True)
class ManeuverOutcome:
    """O desfecho de UMA manobra da campanha.

    Attributes
    ----------
    index:
        Índice da realização na varredura, para rastreabilidade.
    peak_pu:
        Maior tensão no terminal do motor [pu do pico fase-terra].
    reignitions:
        Reignições somadas nas três fases.
    crossed_withstand:
        ``True`` se a manobra atravessou o envelope de suportabilidade.
        Quando ``True`` a manobra é EVENTO TERMINAL e seu perfil de
        estresse não entra no acumulador.
    profile:
        Perfil de estresse da manobra. ``None`` é admissível quando o
        chamador só dispõe das estatísticas agregadas.
    label:
        Rótulo livre.
    """

    index: int
    peak_pu: float
    reignitions: int = 0
    crossed_withstand: bool = False
    profile: StressProfile | None = None
    label: str = ""

    def __post_init__(self) -> None:
        if int(self.index) != self.index or self.index < 0:
            raise ValueError(f"index deve ser inteiro >= 0, obtido {self.index!r}")
        if not math.isfinite(self.peak_pu) or self.peak_pu < 0.0:
            raise ValueError(f"peak_pu deve ser finito e >= 0, obtido {self.peak_pu!r}")
        if int(self.reignitions) != self.reignitions or self.reignitions < 0:
            raise ValueError(
                f"reignitions deve ser inteiro >= 0, obtido {self.reignitions!r}"
            )
        if self.profile is not None and not isinstance(self.profile, StressProfile):
            raise TypeError(
                "profile deve ser StressProfile ou None, obtido "
                f"{type(self.profile).__name__}"
            )


@dataclass(frozen=True)
class TerminalRate:
    """Taxa de travessia do envelope, com o intervalo que a sustenta.

    Attributes
    ----------
    n_crossed, n_total:
        Contagens observadas.
    """

    n_crossed: int
    n_total: int

    def __post_init__(self) -> None:
        if int(self.n_total) != self.n_total or self.n_total <= 0:
            raise ValueError(f"n_total deve ser inteiro > 0, obtido {self.n_total!r}")
        if int(self.n_crossed) != self.n_crossed or not (
            0 <= self.n_crossed <= self.n_total
        ):
            raise ValueError(
                f"n_crossed deve ser inteiro em 0..{self.n_total}, "
                f"obtido {self.n_crossed!r}"
            )

    @property
    def point_estimate(self) -> float:
        """``p = n_crossed / n_total``."""
        return self.n_crossed / self.n_total

    @property
    def upper_bound_95(self) -> float:
        """Limite superior de ``p`` a 95 %, saturado em 1.

        Com zero eventos usa a regra de três, ``3/n``; com eventos
        observados usa a aproximação normal sobre a estimativa pontual.
        A distinção importa: uma varredura sem travessia nenhuma **não**
        demonstra que a travessia é impossível, apenas que sua
        probabilidade está abaixo de ``3/n``.
        """
        if self.n_crossed == 0:
            return min(1.0, RULE_OF_THREE / self.n_total)
        p = self.point_estimate
        erro = 1.96 * math.sqrt(p * (1.0 - p) / self.n_total)
        return min(1.0, p + erro)

    @property
    def expected_maneuvers(self) -> float:
        """Manobras esperadas até a primeira travessia, ``1/p``.

        ``inf`` quando nenhuma travessia foi observada — caso em que a
        leitura correta é :attr:`minimum_expected_maneuvers`, e não
        "nunca".
        """
        p = self.point_estimate
        return math.inf if p == 0.0 else 1.0 / p

    @property
    def minimum_expected_maneuvers(self) -> float:
        """Cota INFERIOR das manobras esperadas, ``1/p_max``.

        É o número que se reporta quando a contagem observada é zero.
        """
        p = self.upper_bound_95
        return math.inf if p == 0.0 else 1.0 / p

    def describe(self) -> str:
        """Uma linha legível, com a distinção entre ponto e cota."""
        if self.n_crossed == 0:
            return (
                f"nenhuma travessia em {self.n_total} manobras: "
                f"p <= {self.upper_bound_95:.1%} (95 %), "
                f"ou seja mais de {self.minimum_expected_maneuvers:.0f} manobras"
            )
        return (
            f"{self.n_crossed} travessias em {self.n_total} manobras: "
            f"p = {self.point_estimate:.1%} "
            f"(<= {self.upper_bound_95:.1%} a 95 %), "
            f"{self.expected_maneuvers:.1f} manobras esperadas até a primeira"
        )


@dataclass
class SwitchingCampaign:
    """Uma campanha de manobras, com os dois caminhos separados.

    Parameters
    ----------
    withstand_level_kV:
        Envelope de suportabilidade adotado [kV de pico] — tipicamente
        :func:`app.simulation.emt.flashover.iec_60034_15_levels`. Serve de
        registro: a classificação de cada manobra vem de
        ``crossed_withstand``, não é recalculada aqui.
    outcomes:
        Desfechos das manobras.
    label:
        Rótulo da campanha (cenário, mitigação, passo).
    """

    withstand_level_kV: float
    outcomes: tuple[ManeuverOutcome, ...] = ()
    label: str = ""

    def __post_init__(self) -> None:
        v = float(self.withstand_level_kV)
        if not math.isfinite(v) or v <= 0.0:
            raise ValueError(
                f"withstand_level_kV deve ser finito e > 0, obtido {v!r}"
            )
        self.outcomes = tuple(self.outcomes)
        for o in self.outcomes:
            if not isinstance(o, ManeuverOutcome):
                raise TypeError(
                    f"outcomes deve conter ManeuverOutcome, obtido "
                    f"{type(o).__name__}"
                )

    def add(self, outcome: ManeuverOutcome) -> None:
        """Acrescenta o desfecho de uma manobra."""
        if not isinstance(outcome, ManeuverOutcome):
            raise TypeError(
                f"outcome deve ser ManeuverOutcome, obtido {type(outcome).__name__}"
            )
        self.outcomes = self.outcomes + (outcome,)

    def extend(self, outcomes: Iterable[ManeuverOutcome]) -> None:
        """Acrescenta vários desfechos."""
        for o in outcomes:
            self.add(o)

    # -- as duas populações -------------------------------------------------

    @property
    def n_maneuvers(self) -> int:
        """Total de manobras."""
        return len(self.outcomes)

    @property
    def aging(self) -> tuple[ManeuverOutcome, ...]:
        """Manobras que envelhecem a isolação — abaixo do envelope."""
        return tuple(o for o in self.outcomes if not o.crossed_withstand)

    @property
    def terminal(self) -> tuple[ManeuverOutcome, ...]:
        """Manobras que atravessam o envelope — eventos terminais."""
        return tuple(o for o in self.outcomes if o.crossed_withstand)

    def terminal_rate(self) -> TerminalRate:
        """Taxa de travessia com o intervalo que a sustenta.

        Raises
        ------
        ValueError
            Campanha vazia.
        """
        if not self.outcomes:
            raise ValueError("campanha sem manobras: a taxa não está definida")
        return TerminalRate(
            n_crossed=len(self.terminal), n_total=self.n_maneuvers
        )

    # -- o caminho do envelhecimento ---------------------------------------

    def accumulate(
        self,
        accumulator: CombinedDamageAccumulator | None = None,
        *,
        params: DamageModelParams | None = None,
    ) -> CombinedDamageAccumulator:
        """Integra o dano das manobras de ENVELHECIMENTO, e só delas.

        As manobras que atravessaram o envelope são deliberadamente
        excluídas: elas não envelhecem a isolação, encerram-na. Excluí-las
        é o que torna o dano acumulado legível — e é também o que obriga a
        reportar :meth:`terminal_rate` junto, sob pena de a exclusão virar
        omissão.

        Parameters
        ----------
        accumulator:
            Acumulador a alimentar. ``None`` cria um novo com ``params``.
        params:
            Parâmetros do modelo de dano, quando o acumulador é criado
            aqui. Todos NÃO CALIBRADOS — ver
            ``rul_params_not_calibrated``.

        Returns
        -------
        CombinedDamageAccumulator
            O acumulador, já alimentado.

        Raises
        ------
        ValueError
            Alguma manobra de envelhecimento não traz perfil de estresse.
        """
        acc = accumulator or CombinedDamageAccumulator(
            params=params or DamageModelParams()
        )
        # ``None`` e perfil VAZIO são coisas diferentes: o primeiro é
        # ausência de medição e impede integrar; o segundo é medição que
        # não encontrou excursão acima do limiar de detecção — dano nulo,
        # e uma manobra que ocorreu.
        sem_perfil = [o.index for o in self.aging if o.profile is None]
        if sem_perfil:
            raise ValueError(
                "manobras de envelhecimento sem perfil de estresse nos "
                f"índices {sem_perfil[:5]}{'…' if len(sem_perfil) > 5 else ''}: "
                "o dano não pode ser integrado sem a forma de onda. Um perfil "
                "VAZIO (medido, sem excursão acima do limiar) é aceito e "
                "contribui dano nulo"
            )
        for o in self.aging:
            acc.add_profile(o.profile)  # type: ignore[arg-type]
        return acc

    def maneuvers_to_damage_limit(
        self, accumulator: CombinedDamageAccumulator
    ) -> float:
        """Manobras até ``D = 1``, extrapolando o dano médio por manobra.

        A extrapolação supõe manobras futuras estatisticamente iguais às
        da campanha — que é a premissa de qualquer projeção por Miner —, e
        ignora a dependência do dano com o estado, que o próprio
        acumulador modela quando ``state_dependent_threshold`` está ativo.

        A contagem de manobras vem da CAMPANHA, e **não** de
        ``accumulator.n_operations``. As duas medem coisas diferentes e
        confundi-las erra o denominador nos dois sentidos:

        * ``n_operations`` conta GRUPOS de reignição identificados dentro
          do perfil. Um perfil que reúne as três fases de uma manobra
          declara até três grupos — logo SUPERESTIMA o número de manobras;
        * uma manobra tão branda que nenhuma excursão ultrapassa o limiar
          de DETECÇÃO produz perfil vazio e nenhum grupo — logo é
          SUBESTIMADA, embora tenha ocorrido e tenha de entrar no
          denominador.

        Returns
        -------
        float
            ``inf`` quando o dano acumulado é nulo.

        Raises
        ------
        ValueError
            Nenhuma manobra de envelhecimento na campanha, ou acumulador
            que não foi alimentado.
        """
        n = len(self.aging)
        if n <= 0:
            raise ValueError(
                "a campanha não tem manobra de envelhecimento: não há dano a "
                "extrapolar"
            )
        # Distinguir "acumulador não alimentado" de "alimentado e sem
        # dano": os dois dão n_operations = 0 e D = 0, e só a campanha
        # sabe qual é qual. Se ela tem excursões e o acumulador não viu
        # nenhuma, ele não foi alimentado — erro do chamador, e devolver
        # "vida infinita" para ele seria perigoso. Se ela não tem excursão
        # nenhuma, o dano nulo é o resultado correto.
        tem_excursao = any(
            o.profile is not None and o.profile.events for o in self.aging
        )
        if tem_excursao and accumulator.n_operations == 0 and accumulator.D_total <= 0.0:
            raise ValueError(
                "o acumulador não contabilizou manobra nenhuma; chame "
                "accumulate() antes"
            )
        d = accumulator.D_total
        if d <= 0.0:
            return math.inf
        return n / d

    # -- os dois caminhos juntos -------------------------------------------

    def life_summary(
        self, accumulator: CombinedDamageAccumulator
    ) -> dict[str, float | str | bool]:
        """Os dois caminhos lado a lado, e o que decide o fim de vida.

        Returns
        -------
        dict
            ``manobras_por_envelhecimento``, ``manobras_ate_travessia``,
            ``manobras_ate_o_fim`` (o mínimo), ``caminho_dominante`` e as
            grandezas de auditoria que sustentam cada um.
        """
        taxa = self.terminal_rate()
        n_env = self.maneuvers_to_damage_limit(accumulator)
        n_term = taxa.expected_maneuvers
        n_fim = min(n_env, n_term)
        if not math.isfinite(n_fim):
            dominante = "indeterminado"
        elif n_term < n_env:
            dominante = "travessia_do_envelope"
        elif n_env < n_term:
            dominante = "envelhecimento"
        else:
            dominante = "empate"
        return {
            "manobras_por_envelhecimento": n_env,
            "manobras_ate_travessia": n_term,
            "manobras_ate_travessia_cota_inferior": (
                taxa.minimum_expected_maneuvers
            ),
            "manobras_ate_o_fim": n_fim,
            "caminho_dominante": dominante,
            "dano_acumulado": accumulator.D_total,
            "dano_e_cota_inferior": accumulator.is_lower_bound,
            "manobras_de_envelhecimento": len(self.aging),
            "manobras_terminais": len(self.terminal),
            "taxa_de_travessia": taxa.point_estimate,
            "envelope_kV": float(self.withstand_level_kV),
            "descricao_da_taxa": taxa.describe(),
        }


def campaign_from_summary(
    *,
    withstand_level_kV: float,
    peaks_pu: Sequence[float],
    crossed: Sequence[bool],
    reignitions: Sequence[int] | None = None,
    label: str = "",
) -> SwitchingCampaign:
    """Campanha construída de estatísticas agregadas, sem formas de onda.

    Serve para reler um JSON de varredura já executada: a taxa terminal
    fica disponível, mas :meth:`SwitchingCampaign.accumulate` levanta,
    porque sem forma de onda não há dano a integrar.

    Raises
    ------
    ValueError
        Sequências de comprimentos diferentes ou vazias.
    """
    n = len(peaks_pu)
    if n == 0:
        raise ValueError("peaks_pu não pode ser vazia")
    if len(crossed) != n:
        raise ValueError(
            f"crossed deve ter o mesmo comprimento de peaks_pu ({n}), "
            f"obtido {len(crossed)}"
        )
    reig = list(reignitions) if reignitions is not None else [0] * n
    if len(reig) != n:
        raise ValueError(
            f"reignitions deve ter o mesmo comprimento de peaks_pu ({n}), "
            f"obtido {len(reig)}"
        )
    return SwitchingCampaign(
        withstand_level_kV=float(withstand_level_kV),
        outcomes=tuple(
            ManeuverOutcome(
                index=i,
                peak_pu=float(peaks_pu[i]),
                reignitions=int(reig[i]),
                crossed_withstand=bool(crossed[i]),
            )
            for i in range(n)
        ),
        label=str(label),
    )


# ---------------------------------------------------------------------------
# Acoplamento: a taxa terminal depende do dano acumulado
# ---------------------------------------------------------------------------
#
# A suportabilidade residual cai com o dano, ``U_w(D) = U_w0·ψ(D)``, de modo
# que a probabilidade de uma manobra atravessar o envelope CRESCE ao longo
# da vida. Tratar ``p`` como constante é, por isso, cota superior do número
# de manobras até o fim.
#
# O acoplamento é computável SEM SIMULAR NADA. A distribuição de picos da
# manobra não depende do dano da isolação — o pico é propriedade do circuito
# e do disjuntor —, logo
#
#     p(D) = P( V_pk > U_w0·ψ(D) )
#
# lê-se direto da distribuição empírica de picos NÃO GRAMPEADOS. É o que
# :class:`PeakDistribution` e :func:`survival` fazem.


@dataclass(frozen=True)
class PeakDistribution:
    """Distribuição empírica dos picos de manobra, NÃO grampeados.

    "Não grampeados" refere-se ao caminho de DISRUPÇÃO, e a distinção é
    fina mas decisiva:

    * o grampeamento pela disrupção é **consequência**, não projeto: uma
      série que passou por ele tem os picos altos truncados por um evento
      que encerra a máquina, e usá-la subestima a excedência. Não use.
    * o grampeamento por um **para-raios instalado** é a realidade física
      da instalação: os picos que ele produz são os que a isolação de
      fato vê. Use, e a distribuição descreve aquela instalação.

    Em resumo: a série correta é a da configuração de MITIGAÇÃO que se
    quer avaliar, sem o caminho de disrupção ativo.

    Attributes
    ----------
    peaks_kV:
        Picos observados [kV], um por manobra.
    label:
        Rótulo de procedência.
    """

    peaks_kV: tuple[float, ...]
    label: str = ""

    def __post_init__(self) -> None:
        picos = tuple(float(x) for x in self.peaks_kV)
        if not picos:
            raise ValueError("peaks_kV não pode ser vazia")
        if any(not math.isfinite(x) or x < 0.0 for x in picos):
            raise ValueError("peaks_kV deve conter valores finitos e >= 0")
        object.__setattr__(self, "peaks_kV", tuple(sorted(picos)))

    @property
    def n(self) -> int:
        """Número de manobras observadas."""
        return len(self.peaks_kV)

    @property
    def max_kV(self) -> float:
        """Maior pico observado [kV]."""
        return self.peaks_kV[-1]

    def exceedance(self, threshold_kV: float) -> float:
        """``P(V_pk >= limiar)`` pela contagem empírica.

        A igualdade CONTA como travessia, para coincidir com o critério do
        motor, que dispara em ``|v| >= limiar``
        [REPO: :class:`app.simulation.emt.flashover.InsulationFlashover`].
        Sem isso, uma distribuição com picos empatados exatamente sobre o
        limiar daria taxa nula.
        """
        limiar = float(threshold_kV)
        return sum(1 for v in self.peaks_kV if v >= limiar) / self.n

    def rate(self, threshold_kV: float) -> TerminalRate:
        """Taxa terminal no limiar, com o intervalo que a sustenta."""
        limiar = float(threshold_kV)
        return TerminalRate(
            n_crossed=sum(1 for v in self.peaks_kV if v >= limiar),
            n_total=self.n,
        )

    def breakpoints_kV(self, above_kV: float = 0.0) -> tuple[float, ...]:
        """Picos observados acima de ``above_kV``, em ordem DECRESCENTE.

        São os limiares em que a excedência muda de patamar. Entre dois
        deles ``p`` é constante — é o que torna a curva de sobrevivência
        resolúvel por segmentos, sem iterar manobra a manobra.
        """
        return tuple(v for v in reversed(self.peaks_kV) if v > float(above_kV))


@dataclass(frozen=True)
class SurvivalSegment:
    """Trecho da vida em que ``p`` é constante.

    Attributes
    ----------
    damage_start, damage_end:
        Dano acumulado no início e no fim do trecho.
    maneuver_start, maneuver_end:
        Manobras acumuladas nos mesmos pontos.
    withstand_kV:
        Suportabilidade residual no trecho [kV] — avaliada no INÍCIO, que
        é o valor conservador, já que ela só decresce.
    p:
        Taxa terminal por manobra no trecho.
    survival_start, survival_end:
        Probabilidade de sobreviver até o início e até o fim do trecho.
    """

    damage_start: float
    damage_end: float
    maneuver_start: float
    maneuver_end: float
    withstand_kV: float
    p: float
    survival_start: float
    survival_end: float


@dataclass(frozen=True)
class SurvivalCurve:
    """Vida com os dois caminhos ACOPLADOS.

    Attributes
    ----------
    segments:
        Trechos de ``p`` constante, do início ao fim da vida.
    maneuvers_to_damage_limit:
        Manobras até ``D = 1`` pelo caminho do envelhecimento isolado.
    withstand0_kV, psi_min:
        Parâmetros do decaimento da suportabilidade.
    """

    segments: tuple[SurvivalSegment, ...]
    maneuvers_to_damage_limit: float
    withstand0_kV: float
    psi_min: float

    @property
    def survival_at_damage_limit(self) -> float:
        """``S`` ao atingir ``D = 1``: chance de o envelhecimento vencer."""
        return self.segments[-1].survival_end if self.segments else 1.0

    @property
    def expected_maneuvers(self) -> float:
        """Manobras esperadas até o fim, sob os dois caminhos.

        ``E[N] = Σ_k S(k−1)`` sobre as manobras da vida útil, resolvido
        por trecho: num trecho de taxa ``p`` e comprimento ``m``, a soma
        vale ``S₀·(1 − (1−p)^m)/p`` para ``p > 0`` e ``S₀·m`` para
        ``p = 0``.
        """
        total = 0.0
        for seg in self.segments:
            m = seg.maneuver_end - seg.maneuver_start
            if seg.p <= 0.0:
                total += seg.survival_start * m
            else:
                total += seg.survival_start * (
                    1.0 - (1.0 - seg.p) ** m
                ) / seg.p
        return total

    @property
    def critical_damage(self) -> float | None:
        """Dano em que ``p`` deixa de ser o inicial. ``None`` se nunca muda.

        É o achado que o acoplamento entrega: **até este dano, tratar
        ``p`` como constante é exato**, e não conservador.
        """
        if not self.segments:
            return None
        p0 = self.segments[0].p
        for seg in self.segments:
            if seg.p != p0:
                return seg.damage_start
        return None

    @property
    def rate_is_constant(self) -> bool:
        """``True`` se ``p`` não muda em toda a vida útil."""
        return self.critical_damage is None

    def describe(self) -> str:
        """Uma linha com o que o acoplamento mudou, ou não mudou."""
        if self.rate_is_constant:
            return (
                f"p constante em {self.segments[0].p:.3%} durante toda a vida: "
                "o acoplamento com o dano NÃO altera o resultado, e a taxa "
                "fixa é exata"
            )
        return (
            f"p sobe de {self.segments[0].p:.3%} para "
            f"{self.segments[-1].p:.3%} a partir de D = "
            f"{self.critical_damage:.3g}"
        )


def survival(
    distribution: PeakDistribution,
    *,
    withstand0_kV: float,
    maneuvers_to_damage_limit: float,
    psi_min: float = 0.5,
) -> SurvivalCurve:
    """Curva de sobrevivência com ``p`` acoplado ao dano.

    A suportabilidade decai como ``ψ(D) = 1 − (1 − ψ_min)·D``, a mesma lei
    de :func:`psi_linear`, e o dano avança linearmente com as manobras —
    ``D(k) = k / N_D`` —, que é a premissa de qualquer projeção por Miner.

    A curva é resolvida POR TRECHOS: ``p`` só muda quando o limiar
    ``ψ(D)·U_w0`` cruza um pico observado, e entre dois cruzamentos a
    sobrevivência decai geometricamente. Isso evita iterar sobre as
    dezenas de milhões de manobras de uma vida típica.

    Parameters
    ----------
    distribution:
        Picos NÃO grampeados.
    withstand0_kV:
        Suportabilidade da isolação nova [kV].
    maneuvers_to_damage_limit:
        Manobras até ``D = 1`` pelo envelhecimento isolado, tipicamente de
        :meth:`SwitchingCampaign.maneuvers_to_damage_limit`.
    psi_min:
        Suportabilidade residual relativa em ``D = 1``.

    Raises
    ------
    ValueError
        Parâmetros fora de faixa, ou ``maneuvers_to_damage_limit`` não
        finito — sem um horizonte de envelhecimento não há vida útil sobre
        a qual integrar.
    """
    u0 = float(withstand0_kV)
    if not math.isfinite(u0) or u0 <= 0.0:
        raise ValueError(f"withstand0_kV deve ser finito e > 0, obtido {u0!r}")
    nd = float(maneuvers_to_damage_limit)
    if not math.isfinite(nd) or nd <= 0.0:
        raise ValueError(
            "maneuvers_to_damage_limit deve ser finito e > 0 — sem horizonte "
            f"de envelhecimento não há vida sobre a qual integrar, obtido {nd!r}"
        )
    pm = float(psi_min)
    if not math.isfinite(pm) or not (0.0 < pm <= 1.0):
        raise ValueError(f"psi_min deve estar em (0, 1], obtido {pm!r}")

    def psi(d: float) -> float:
        return 1.0 - (1.0 - pm) * min(1.0, max(0.0, d))

    # Danos em que o limiar cruza cada pico observado: ψ(D)·u0 = pico.
    # Só interessam os picos ENTRE ψ(1)·u0 e u0 — abaixo o limiar nunca
    # chega, acima já estão contados desde D = 0.
    limiar_final = psi(1.0) * u0
    cruzamentos = []
    for pico in distribution.breakpoints_kV(above_kV=limiar_final):
        if pico >= u0:
            continue  # já excedido com a isolação nova
        d = (1.0 - pico / u0) / (1.0 - pm)
        if 0.0 < d < 1.0:
            cruzamentos.append(d)
    bordas = [0.0] + sorted(set(cruzamentos)) + [1.0]

    segmentos: list[SurvivalSegment] = []
    s = 1.0
    for d0, d1 in zip(bordas[:-1], bordas[1:]):
        if d1 <= d0:
            continue
        limiar = psi(d0) * u0
        p = distribution.exceedance(limiar)
        m = (d1 - d0) * nd
        s_fim = s * (1.0 - p) ** m if p > 0.0 else s
        segmentos.append(
            SurvivalSegment(
                damage_start=d0,
                damage_end=d1,
                maneuver_start=d0 * nd,
                maneuver_end=d1 * nd,
                withstand_kV=limiar,
                p=p,
                survival_start=s,
                survival_end=s_fim,
            )
        )
        s = s_fim
    return SurvivalCurve(
        segments=tuple(segmentos),
        maneuvers_to_damage_limit=nd,
        withstand0_kV=u0,
        psi_min=pm,
    )


# ---------------------------------------------------------------------------
# Robustez da decisão ao expoente não calibrado
# ---------------------------------------------------------------------------
#
# O expoente de tensão da lei de potência inversa não está calibrado para
# mica-epóxi pré-formada de MT, e a vida absoluta é exponencialmente
# sensível a ele. Mas uma DECISÃO — instalar ou não uma mitigação — não
# precisa da vida absoluta: precisa da ordenação. Se uma configuração
# domina a outra para TODO expoente da faixa publicada, a decisão é livre
# de calibração ainda que o número não seja.
#
# É o que :func:`exponent_robustness` verifica.

#: Faixa do expoente de tensão na literatura acessada, para fio esmaltado
#: e epóxi puro [LITERATURA: CIGRE WG D1.43, TB 703]. NÃO é a faixa de
#: mica-epóxi pré-formada de MT, que nenhuma fonte acessada publica.
EXPONENT_LITERATURE_RANGE: tuple[float, float] = (3.8, 11.7)


@dataclass(frozen=True)
class ExponentRobustness:
    """Se a ordenação entre configurações resiste ao expoente incerto.

    Attributes
    ----------
    exponents:
        Expoentes varridos.
    lives:
        ``rótulo → manobras até o fim``, uma sequência por configuração,
        alinhada com :attr:`exponents`.
    winner:
        Rótulo que vence em TODOS os expoentes, ou ``None`` se a ordenação
        se inverte em algum ponto.
    """

    exponents: tuple[float, ...]
    lives: dict[str, tuple[float, ...]]
    winner: str | None

    @property
    def is_robust(self) -> bool:
        """``True`` se a decisão não depende da calibração do expoente."""
        return self.winner is not None

    @property
    def spread(self) -> dict[str, float]:
        """Razão entre a maior e a menor vida de cada configuração.

        É a medida de quanto a INCERTEZA do expoente move o número —
        distinta de quanto ela move a DECISÃO.
        """
        out: dict[str, float] = {}
        for rotulo, v in self.lives.items():
            finitos = [x for x in v if math.isfinite(x) and x > 0.0]
            out[rotulo] = (max(finitos) / min(finitos)) if finitos else math.inf
        return out

    def describe(self) -> str:
        """Uma linha com o veredito e o custo da incerteza."""
        faixa = f"n de {self.exponents[0]:.3g} a {self.exponents[-1]:.3g}"
        if not self.is_robust:
            return (
                f"a ordenação SE INVERTE em {faixa}: a decisão depende da "
                "calibração do expoente e não pode ser tomada sem ela"
            )
        dispersao = max(self.spread.values())
        return (
            f"{self.winner!r} vence em todo {faixa}: a decisão é LIVRE de "
            f"calibração, embora a vida absoluta varie por fator de "
            f"{dispersao:.3g}"
        )


def exponent_robustness(
    campaigns: dict[str, SwitchingCampaign],
    *,
    exponents: Sequence[float] | None = None,
    params: DamageModelParams | None = None,
) -> ExponentRobustness:
    """Varre o expoente de tensão e verifica se a ordenação se mantém.

    Para cada expoente, recalcula o dano de cada campanha sobre os perfis
    JÁ SIMULADOS — nenhuma simulação nova — e compara o fim de vida
    ``min(N_env, N_term)``.

    Parameters
    ----------
    campaigns:
        ``rótulo → campanha``, ao menos duas.
    exponents:
        Expoentes a varrer. ``None`` usa 9 pontos em
        :data:`EXPONENT_LITERATURE_RANGE`.
    params:
        Demais parâmetros do modelo, mantidos fixos na varredura.

    Raises
    ------
    ValueError
        Menos de duas campanhas, ou lista de expoentes vazia.
    """
    if len(campaigns) < 2:
        raise ValueError(
            "a robustez compara configurações: informe ao menos duas campanhas"
        )
    if exponents is None:
        lo, hi = EXPONENT_LITERATURE_RANGE
        exponents = tuple(lo + (hi - lo) * k / 8.0 for k in range(9))
    expoentes = tuple(float(x) for x in exponents)
    if not expoentes:
        raise ValueError("exponents não pode ser vazia")

    base = params or DamageModelParams()
    vidas: dict[str, list[float]] = {r: [] for r in campaigns}
    for n in expoentes:
        for rotulo, campanha in campaigns.items():
            p_local = replace(base, n_voltage=float(n))
            acumulador = campanha.accumulate(params=p_local)
            resumo = campanha.life_summary(acumulador)
            vidas[rotulo].append(float(resumo["manobras_ate_o_fim"]))

    rotulos = list(campaigns)
    vencedor: str | None = None
    for k in range(len(expoentes)):
        melhor = max(rotulos, key=lambda r: vidas[r][k])
        if vencedor is None:
            vencedor = melhor
        elif melhor != vencedor:
            vencedor = None
            break
    return ExponentRobustness(
        exponents=expoentes,
        lives={r: tuple(v) for r, v in vidas.items()},
        winner=vencedor,
    )


KNOWN_LIMITATIONS: dict[str, str] = {
    "rul_campaign_terminal_and_aging_are_not_additive": (
        "Os dois caminhos são reportados lado a lado e o fim de vida é o "
        "MÍNIMO deles, não a soma. Não há modelo de interação: uma "
        "isolação já envelhecida atravessa o envelope com probabilidade "
        "MAIOR que a nova, porque sua suportabilidade caiu, e essa "
        "dependência de p com D não é modelada. O resultado é, portanto, "
        "COTA SUPERIOR do número de manobras até o fim — a taxa real de "
        "travessia cresce com o dano acumulado."
    ),
    "rul_campaign_bernoulli_assumes_independence": (
        "A travessia é tratada como Bernoulli independente entre "
        "manobras, com p constante. Duas premissas embutidas: (i) as "
        "manobras futuras são estatisticamente iguais às da campanha — "
        "mesma janela de tempo de arco, mesmas faixas de parâmetro do "
        "disjuntor —, o que deixa de valer quando o disjuntor envelhece; "
        "(ii) não há correlação entre manobras consecutivas, o que uma "
        "sequência de partidas abortadas viola."
    ),
    "rul_campaign_rate_inherits_the_sweep_convergence": (
        "A taxa de travessia herda a convergência da varredura que a "
        "produziu. Medido no caso de referência: a FRAÇÃO é estável entre "
        "Δt = 1 µs e 0,2 µs (8 de 150 nos dois), mas o CONJUNTO de "
        "realizações que atravessam muda. Logo a taxa é utilizável e o "
        "desfecho de uma manobra específica não é "
        "[REPO: docs/research/rul_isolamento/"
        "09_PARA_RAIOS_E_CRITERIO_DE_ACEITACAO.md, §7.2]."
    ),
}


__all__ = [
    "EXPONENT_LITERATURE_RANGE",
    "KNOWN_LIMITATIONS",
    "RULE_OF_THREE",
    "ExponentRobustness",
    "PeakDistribution",
    "SurvivalCurve",
    "SurvivalSegment",
    "exponent_robustness",
    "survival",
    "ManeuverOutcome",
    "SwitchingCampaign",
    "TerminalRate",
    "campaign_from_summary",
]
