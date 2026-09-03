"""
app.simulation.emt.flashover — disrupção da isolação como evento terminal.

Por que este módulo existe
===========================

A instalação **sem para-raios** — que é a do arquivo de referência —
continua sem limite dielétrico: nada no modelo disrupta, e a cauda de
escalada calcula tensões que a máquina não suportaria
[REPO: ``docs/research/rul_isolamento/09_PARA_RAIOS_E_CRITERIO_DE_
ACEITACAO.md``, §6]. Este módulo fecha essa lacuna com a alternativa
mínima: um limiar no envelope normativo, com **registro do evento**.

O que o modelo afirma, e o que NÃO afirma
==========================================

A IEC 60034-15 fixa níveis de **suportabilidade de ensaio** — a tensão
que a máquina deve sobreviver —, não a tensão de ruptura. A tensão de
ruptura real fica ACIMA do nível de ensaio, por margem não publicada.
Portanto:

* Este ramo **não** prevê o instante físico da disrupção.
* O que ele marca é a fronteira além da qual o resultado **deixa o
  domínio que a norma garante**, e conta as travessias.
* A forma de onda depois do disparo **não é objeto do modelo**: o arco é
  um resistor pequeno para a terra, escolha de modelagem declarada.

Consequência para o modelo de dano, que precisa ser dita com precisão:
uma realização que atinge o nível **não é estresse a integrar, é um
evento terminal a contar**. Grampear a tensão reduz o estresse calculado
— é conservador quanto à AMPLITUDE e anticonservador quanto ao DANO. Por
isso a contagem de disrupções é a saída que importa, e não a forma de
onda grampeada.

Níveis
=======

Edição 2009, texto lido na amostra oficial [NORMA: IEC 60034-15:2009,
Tabela 1]::

    U_P  = 4·U_N + 5 kV          (pico, isolação principal, 1,2/50 µs)
    U'_P = 0,65·U_P              (pico, entre espiras, frente 0,2 µs)

Edição 2025 — a Tabela 1 da edição publicada NÃO foi acessada; os valores
vêm do CDV 2/2199/CDV (2024), marcado *subject to change*
[NORMA: IEC CDV 60034-15, 4.2-4.3 e Tabela 1]::

    U_P  = 5,0·√(2/3)·U_N        mínimo 8,0 kV
    U'_P = 3,5·√(2/3)·U_N        mínimo 5,6 kV

O CDV prevê ainda nível **reforçado** — padrão + 15 kV (SLI) e + 11 kV
(SFI), limitado a duas vezes o padrão — justamente para *"very frequent
switching or aborted starts"*, que é a condição deste estudo.

Fontes
=======

* IEC 60034-15:2009, Tabela 1 e cláusulas 4.2-4.3.
* IEC CDV 60034-15 (2/2199/CDV, 2024), Tabela 1 — provisório.
* Fichamento normativo:
  ``docs/research/rul_isolamento/01_ETAPA1_monitoramento_degradacao_isolamento.md``,
  §4.1.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Sequence

from app.core.logging_config import get_logger

from .components import Resistor, Switch

log = get_logger(__name__)


#: Edições reconhecidas de :func:`iec_60034_15_levels`.
EDITION_2009: str = "2009"
EDITION_2025_CDV: str = "2025-cdv"
EDITIONS: tuple[str, ...] = (EDITION_2009, EDITION_2025_CDV)

#: Fração do nível de impulso atmosférico que dá o nível de frente
#: íngreme na edição 2009 [NORMA: IEC 60034-15:2009, Tabela 1].
TURN_FRACTION_2009: float = 0.65

#: Coeficientes da edição 2025, em pu do pico fase-terra
#: [NORMA: IEC CDV 60034-15, Tabela 1 — PROVISÓRIO].
SLI_PU_2025: float = 5.0
SFI_PU_2025: float = 3.5
SLI_FLOOR_2025_V: float = 8.0e3
SFI_FLOOR_2025_V: float = 5.6e3

#: Acréscimos do nível REFORÇADO do CDV [V], limitados a 2× o padrão.
ENHANCED_SLI_ADDER_V: float = 15.0e3
ENHANCED_SFI_ADDER_V: float = 11.0e3

#: Resistência do canal de arco após a disrupção [Ω]. CONVENÇÃO DE
#: MODELAGEM: um valor pequeno mas não nulo, para que a disrupção não
#: seja um curto ideal e o sistema permaneça bem condicionado. A forma de
#: onda depois do disparo não é objeto do modelo — ver o cabeçalho.
DEFAULT_ARC_RESISTANCE_OHM: float = 1.0

#: Corrente abaixo da qual o canal de arco se extingue [A]. Um arco no ar
#: se apaga na passagem por zero da corrente; o limiar evita que a
#: extinção dependa de o passo cair exatamente sobre o zero.
DEFAULT_HOLDING_CURRENT_A: float = 1.0

FLASHOVER_IDLE: str = "idle"
FLASHOVER_CONDUCTING: str = "conducting"
FLASHOVER_STATES: tuple[str, ...] = (FLASHOVER_IDLE, FLASHOVER_CONDUCTING)


def iec_60034_15_levels(
    rated_voltage_V: float,
    *,
    edition: str = EDITION_2009,
    enhanced: bool = False,
) -> tuple[float, float]:
    """Níveis ``(U_P, U'_P)`` da IEC 60034-15 [V de pico].

    Parameters
    ----------
    rated_voltage_V:
        Tensão nominal de LINHA da máquina [V].
    edition:
        ``"2009"`` (padrão) ou ``"2025-cdv"``. A segunda usa valores do
        CDV, marcados *subject to change* pela própria norma — a Tabela 1
        da edição publicada não foi acessada.
    enhanced:
        Nível reforçado do CDV, previsto para chaveamento muito frequente
        ou partidas abortadas. Só se aplica à edição 2025.

    Returns
    -------
    tuple[float, float]
        ``(nível de impulso atmosférico, nível de frente íngreme)`` [V].

    Raises
    ------
    ValueError
        Tensão inválida, edição desconhecida, ou ``enhanced`` pedido para
        a edição 2009, que não define nível reforçado.
    """
    u_n = float(rated_voltage_V)
    if not math.isfinite(u_n) or u_n <= 0.0:
        raise ValueError(
            f"rated_voltage_V deve ser finita e > 0, obtida {rated_voltage_V!r}"
        )
    ed = str(edition)
    if ed not in EDITIONS:
        raise ValueError(f"edition deve ser um de {EDITIONS}, obtida {edition!r}")
    if ed == EDITION_2009:
        if enhanced:
            raise ValueError(
                "a edição 2009 não define nível reforçado; use edition="
                f"{EDITION_2025_CDV!r}"
            )
        sli = 4.0 * u_n + 5.0e3
        return sli, TURN_FRACTION_2009 * sli

    pico_fase_terra = u_n * math.sqrt(2.0 / 3.0)
    sli = max(SLI_FLOOR_2025_V, SLI_PU_2025 * pico_fase_terra)
    sfi = max(SFI_FLOOR_2025_V, SFI_PU_2025 * pico_fase_terra)
    if enhanced:
        sli = min(2.0 * sli, sli + ENHANCED_SLI_ADDER_V)
        sfi = min(2.0 * sfi, sfi + ENHANCED_SFI_ADDER_V)
    return sli, sfi


@dataclass
class FlashoverResult:
    """Registro auditável das disrupções de um caminho.

    Attributes
    ----------
    count:
        Número de disrupções.
    times_s:
        Instante de cada disrupção [s].
    voltages_V:
        Tensão no instante de cada disrupção [V], com sinal.
    energy_J:
        Energia dissipada no canal de arco [J].
    """

    count: int = 0
    times_s: list[float] = field(default_factory=list)
    voltages_V: list[float] = field(default_factory=list)
    energy_J: float = 0.0

    @property
    def peak_voltage_V(self) -> float:
        """Maior tensão de disrupção em módulo [V]; ``0`` se não houve."""
        if not self.voltages_V:
            return 0.0
        return max(abs(v) for v in self.voltages_V)


class InsulationFlashover:
    """Disrupção da isolação para a terra, com registro do evento.

    Máquina de dois estados. Em repouso o caminho está aberto e a
    isolação apenas suporta a tensão; quando ``|v|`` cruza o limiar, o
    canal fecha sobre o resistor de arco e permanece fechado até a
    corrente cair abaixo da corrente de manutenção — o comportamento de
    um arco no ar, que se apaga na passagem por zero.

    Parameters
    ----------
    switch:
        Chave ideal do caminho de disrupção.
    resistor:
        Resistor do canal de arco.
    threshold_V:
        Nível de disrupção [V de pico]. Tipicamente
        :func:`iec_60034_15_levels`.
    node:
        Nó monitorado; ``None`` usa o terminal positivo da chave.
    holding_current_A:
        Corrente de extinção [A].
    max_events:
        Teto de disrupções registradas antes de travar o caminho aberto,
        salvaguarda numérica análoga à do polo do disjuntor.
    name:
        Rótulo.

    Raises
    ------
    ValueError
        Parâmetros inválidos.
    """

    def __init__(
        self,
        switch: Switch,
        resistor: Resistor,
        *,
        threshold_V: float,
        node: str | None = None,
        holding_current_A: float = DEFAULT_HOLDING_CURRENT_A,
        max_events: int = 200,
        name: str = "",
    ) -> None:
        if not isinstance(switch, Switch):
            raise ValueError(
                "InsulationFlashover comanda um Switch do kernel, obtido "
                f"{type(switch).__name__}"
            )
        if not isinstance(resistor, Resistor):
            raise ValueError(
                "InsulationFlashover exige um Resistor de canal de arco, obtido "
                f"{type(resistor).__name__}"
            )
        v = float(threshold_V)
        if not math.isfinite(v) or v <= 0.0:
            raise ValueError(f"threshold_V deve ser finito e > 0, obtido {threshold_V!r}")
        i_hold = float(holding_current_A)
        if not math.isfinite(i_hold) or i_hold <= 0.0:
            raise ValueError(
                f"holding_current_A deve ser finito e > 0, obtido {holding_current_A!r}"
            )
        if int(max_events) < 0:
            raise ValueError(f"max_events deve ser >= 0, obtido {max_events!r}")

        self.switch = switch
        self.resistor = resistor
        self.threshold_V = v
        self.node = str(node) if node else str(switch.nodes[0])
        self.holding_current_A = i_hold
        self.max_events = int(max_events)
        self.name = str(name) if name else str(switch.name)
        self._state = FLASHOVER_IDLE
        self._result = FlashoverResult()
        self._t_prev = -1.0
        self._p_prev = 0.0
        self._locked_warned = False

    # -- leitura ------------------------------------------------------------

    @property
    def state(self) -> str:
        """Estado corrente."""
        return self._state

    @property
    def result(self) -> FlashoverResult:
        """Registro das disrupções."""
        return self._result

    @property
    def count(self) -> int:
        """Número de disrupções."""
        return self._result.count

    def reset(self) -> None:
        """Zera o estado e o registro."""
        self._state = FLASHOVER_IDLE
        self._result = FlashoverResult()
        self._t_prev = -1.0
        self._p_prev = 0.0
        self._locked_warned = False
        self.switch.open()

    # -- máquina de estados -------------------------------------------------

    def __call__(self, t: float, solver) -> None:
        """Avalia o caminho no instante ``t`` [s]."""
        t_f = float(t)
        if self._t_prev >= 0.0 and t_f < self._t_prev:
            self.reset()

        v_node = self._node_voltage(solver)
        i_arc = float(self.resistor.branch_current(0)) if self._state == FLASHOVER_CONDUCTING else 0.0
        potencia = abs(v_node * i_arc) if self._state == FLASHOVER_CONDUCTING else 0.0
        if self._t_prev >= 0.0 and t_f > self._t_prev:
            self._result.energy_J += 0.5 * (self._p_prev + potencia) * (t_f - self._t_prev)
        self._p_prev = potencia

        if self._state == FLASHOVER_IDLE:
            if abs(v_node) >= self.threshold_V:
                self._fire(t_f, v_node)
        elif abs(i_arc) <= self.holding_current_A:
            # Extinção na passagem por zero — o arco no ar não se
            # sustenta abaixo da corrente de manutenção.
            self.switch.open()
            self._state = FLASHOVER_IDLE

        self._t_prev = t_f

    def _fire(self, t: float, v_node: float) -> None:
        if self._result.count >= self.max_events:
            if not self._locked_warned:
                self._locked_warned = True
                log.warning(
                    "caminho de disrupção %r atingiu o teto de %d eventos em "
                    "t = %.6g s e foi travado ABERTO: o resultado a partir "
                    "daqui é a salvaguarda numérica, não a física",
                    self.name,
                    self.max_events,
                    t,
                )
            return
        self.switch.close()
        self._state = FLASHOVER_CONDUCTING
        self._result.count += 1
        self._result.times_s.append(float(t))
        self._result.voltages_V.append(float(v_node))
        if self._result.count == 1:
            log.warning(
                "DISRUPÇÃO em %r: |v| = %.4g V atingiu o nível de %.4g V em "
                "t = %.6g s. A realização deixou o domínio que a norma "
                "garante e deve ser contada como evento TERMINAL, não "
                "integrada como estresse",
                self.name,
                abs(float(v_node)),
                self.threshold_V,
                t,
            )

    def _node_voltage(self, solver) -> float:
        """Tensão do nó monitorado [V], lida do estado do solver."""
        if self._state == FLASHOVER_CONDUCTING:
            # Com o caminho fechado, a tensão do nó é a do próprio ramo.
            return float(self.switch.branch_voltage(0)) + float(
                self.resistor.branch_voltage(0)
            )
        return float(self.switch.branch_voltage(0))


@dataclass(frozen=True)
class FlashoverPath:
    """Caminho de disrupção montado: componentes e controlador."""

    switch: Switch
    resistor: Resistor
    controller: InsulationFlashover

    @property
    def components(self) -> tuple:
        """Componentes a inserir no circuito, na ordem de montagem."""
        return (self.switch, self.resistor)

    @property
    def name(self) -> str:
        """Rótulo do caminho."""
        return self.controller.name


def build_flashover_path(
    name: str,
    node: str,
    node_ref: str,
    *,
    threshold_V: float,
    arc_resistance_ohm: float = DEFAULT_ARC_RESISTANCE_OHM,
    node_mid: str | None = None,
    **kwargs,
) -> FlashoverPath:
    """Monta ``nó → chave → R_arco → referência``.

    Parameters
    ----------
    name:
        Prefixo; gera ``<name>_sw`` e ``<name>_arc``.
    node, node_ref:
        Terminal monitorado e referência (terra).
    threshold_V:
        Nível de disrupção [V de pico].
    arc_resistance_ohm:
        Resistência do canal [Ω].
    node_mid:
        Nó interno; padrão ``<name>_mid``.
    **kwargs:
        Repassados a :class:`InsulationFlashover`.

    Raises
    ------
    ValueError
        Nome vazio ou resistência inválida.
    """
    label = str(name)
    if not label:
        raise ValueError("build_flashover_path exige um nome não vazio")
    r = float(arc_resistance_ohm)
    if not math.isfinite(r) or r <= 0.0:
        raise ValueError(
            f"arc_resistance_ohm deve ser finita e > 0, obtida {arc_resistance_ohm!r}"
        )
    mid = str(node_mid) if node_mid else f"{label}_mid"
    switch = Switch(f"{label}_sw", str(node), mid, closed=False)
    resistor = Resistor(f"{label}_arc", mid, str(node_ref), r)
    controller = InsulationFlashover(
        switch,
        resistor,
        threshold_V=float(threshold_V),
        node=str(node),
        name=label,
        **kwargs,
    )
    return FlashoverPath(switch=switch, resistor=resistor, controller=controller)


def three_phase_flashover(
    prefix: str,
    nodes_abc: Sequence[str],
    node_ref: str,
    *,
    threshold_V: float,
    arc_resistance_ohm: float = DEFAULT_ARC_RESISTANCE_OHM,
    **kwargs,
) -> tuple[FlashoverPath, ...]:
    """Um caminho de disrupção por fase.

    Raises
    ------
    ValueError
        Lista de nós vazia.
    """
    nodes = tuple(str(n) for n in nodes_abc)
    if not nodes:
        raise ValueError("three_phase_flashover exige pelo menos um nó de fase")
    labels = (
        ("a", "b", "c") if len(nodes) == 3 else tuple(str(k) for k in range(len(nodes)))
    )
    return tuple(
        build_flashover_path(
            f"{prefix}_{lbl}",
            node,
            str(node_ref),
            threshold_V=float(threshold_V),
            arc_resistance_ohm=float(arc_resistance_ohm),
            **kwargs,
        )
        for lbl, node in zip(labels, nodes)
    )


KNOWN_LIMITATIONS: dict[str, str] = {
    "emt_flashover_withstand_is_not_breakdown": (
        "O limiar é um nível de SUPORTABILIDADE DE ENSAIO da IEC 60034-15, "
        "não a tensão de ruptura da máquina. A ruptura real ocorre ACIMA "
        "do nível de ensaio, por margem não publicada. O ramo, portanto, "
        "NÃO prevê o instante físico da disrupção: marca a fronteira além "
        "da qual o resultado deixa o domínio que a norma garante, e conta "
        "as travessias. A leitura correta de uma travessia é EVENTO "
        "TERMINAL a contar, não estresse a integrar — grampear a tensão é "
        "conservador quanto à amplitude e ANTICONSERVADOR quanto ao dano."
    ),
    "emt_flashover_arc_channel_is_a_convention": (
        "Depois do disparo o canal é um resistor de 1 Ω para a terra, com "
        "extinção abaixo de 1 A. São CONVENÇÕES DE MODELAGEM, não dados: "
        "não há tensão de arco, nem dependência da corrente, nem "
        "alongamento do canal. A forma de onda posterior ao disparo não é "
        "objeto do modelo e não deve ser reportada como resultado."
    ),
    "emt_flashover_2025_levels_are_provisional": (
        "Os níveis da edição 2025 vêm do CDV 2/2199/CDV (2024), marcado "
        "'subject to change'; a Tabela 1 da edição publicada NÃO foi "
        "acessada. A verificação de forma feita no fichamento reproduz a "
        "tabela do CDV com três dígitos, mas a citação acadêmica exige a "
        "edição publicada [INSERIR CITAÇÃO]."
    ),
    "emt_flashover_clamped_waveform_is_not_a_result": (
        "O caminho fecha no passo SEGUINTE ao cruzamento do limiar, e os "
        "meios-passos do CDA não chamam controladores; com frentes de "
        "quilovolt por microssegundo, o pico registrado ultrapassa o "
        "limiar. Medido sobre as oito realizações em escalada do caso de "
        "referência, a ultrapassagem vai de 1,04 a 1,87 vezes o limiar "
        "[CÁLCULO PRÓPRIO]. O pico grampeado NÃO é, portanto, resultado "
        "quantitativo: o que o ramo entrega é a CONTAGEM de travessias e "
        "o instante de cada uma."
    ),
    "emt_flashover_marginal_realizations_are_not_step_converged": (
        "A sequência de escalada que leva à travessia é uma cadeia de "
        "decisões de limiar sobre o di/dt nos zeros de alta frequência, e "
        "essa cadeia NÃO é convergida em passo para realizações "
        "marginais. Medido: das oito realizações que escalam a "
        "Δt = 1 µs, DUAS colapsam para uma única reignição e 2,3 pu a "
        "Δt = 0,2 µs, enquanto outras duas escalam nos dois passos "
        "[CÁLCULO PRÓPRIO]. MEDIDO em varredura completa: a FRAÇÃO é "
        "estável — 8 de 150 nos dois passos —, mas o CONJUNTO muda: seis "
        "realizações em comum, duas exclusivas de cada passo. A "
        "estatística de população é utilizável; o desfecho de uma "
        "realização específica, não. Passo adequado para este caso: "
        "0,2 µs, que fica a 2,7 % de 0,05 µs, contra 21 % do passo de "
        "1 µs."
    ),
    "emt_flashover_phase_to_ground_only": (
        "Só se representa a disrupção FASE-TERRA no terminal. Não há "
        "disrupção entre espiras (que é interna à bobina e não aparece "
        "como ramo do circuito) nem entre fases, embora Vollet reporte "
        "sobretensões fase-fase de até o dobro das fase-terra. Um "
        "resultado sem disrupção fase-terra não é, portanto, um resultado "
        "sem disrupção."
    ),
}


__all__ = [
    "DEFAULT_ARC_RESISTANCE_OHM",
    "DEFAULT_HOLDING_CURRENT_A",
    "EDITIONS",
    "EDITION_2009",
    "EDITION_2025_CDV",
    "ENHANCED_SFI_ADDER_V",
    "ENHANCED_SLI_ADDER_V",
    "FLASHOVER_CONDUCTING",
    "FLASHOVER_IDLE",
    "FLASHOVER_STATES",
    "KNOWN_LIMITATIONS",
    "SFI_FLOOR_2025_V",
    "SFI_PU_2025",
    "SLI_FLOOR_2025_V",
    "SLI_PU_2025",
    "TURN_FRACTION_2009",
    "FlashoverPath",
    "FlashoverResult",
    "InsulationFlashover",
    "build_flashover_path",
    "iec_60034_15_levels",
    "three_phase_flashover",
]
