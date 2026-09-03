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
from dataclasses import dataclass, field
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
        sem_perfil = [o.index for o in self.aging if o.profile is None]
        if sem_perfil:
            raise ValueError(
                "manobras de envelhecimento sem perfil de estresse nos "
                f"índices {sem_perfil[:5]}{'…' if len(sem_perfil) > 5 else ''}: "
                "o dano não pode ser integrado sem a forma de onda"
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

        Returns
        -------
        float
            ``inf`` quando o dano acumulado é nulo.

        Raises
        ------
        ValueError
            Nenhuma manobra de envelhecimento contabilizada.
        """
        n = accumulator.n_operations
        if n <= 0:
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
    "KNOWN_LIMITATIONS",
    "RULE_OF_THREE",
    "ManeuverOutcome",
    "SwitchingCampaign",
    "TerminalRate",
    "campaign_from_summary",
]
