"""
app.simulation.emt.snubber — *snubber* ativo a tiristor (par de SCR
antiparalelos em série com resistor de amortecimento) sobre o kernel EMT
dedicado do Olivas Power System Studio.

O que o Documento A descreve
=============================

O ramo é ligado em paralelo com os terminais da máquina e é composto de
[FATO: doc A, p. 2, III-A]:

* **dois SCR em antiparalelo**, formando uma chave CA bidirecional; e
* um **resistor de amortecimento ``R_s`` em série**, dimensionado
  próximo da impedância de surto do circuito associado
  (``R_s = 30 Ω`` por fase no modelo de A) [FATO: doc A, p. 2, III-A e
  Tabela II, p. 3].

O ciclo de operação declarado é [FATO: doc A, p. 2, III-A, itens 1 a 4]:

1. **Regime permanente** — SCR bloqueados, ramo aberto, corrente nula;
   não altera a impedância equivalente nem introduz perdas
   ("transparente à rede").
2. **Disparo** — a tensão sobre o DIAC cresce com a sobretensão; ao
   atingir o nível de *breakover*, o DIAC conduz abruptamente e injeta o
   pulso de porta no SCR da polaridade adequada. O disparo depende
   **apenas** das condições elétricas locais, sem comando digital.
3. **Amortecimento** — a corrente circula por ``R_s``, dissipando a
   energia do surto e reduzindo pico e ``dv/dt``.
4. **Bloqueio natural** — ao decair a corrente do ramo pelo zero, os SCR
   bloqueiam sozinhos e o ramo reabre, pronto para o próximo evento.

A lacuna do nível de *breakover*
=================================

**[FATO por omissão]** O Documento A não informa o nível de *breakover*
do DIAC em nenhuma das cinco páginas: nem no texto da Seção III-A, nem
na Tabela II (que lista apenas ``R_s = 30 Ω``), nem na legenda da Fig. 1.
Sem ele, o instante de disparo — e portanto todo o resultado da Tabela
III — não é reprodutível a partir do artigo.

Consequência de projeto: :class:`ThyristorSnubber` torna
``breakover_voltage_V`` um parâmetro **obrigatório**, sem valor padrão.
Um padrão silencioso disfarçaria uma escolha do implementador como dado
do artigo, o que este projeto proíbe. Faixa de referência para
dimensionamento, a declarar como hipótese no laudo: acima da tensão de
fase de pico em regime (3,40 kV para a barra de 4,16 kV) e abaixo do
nível de proteção pretendido [INFERÊNCIA FÍSICA].

O que o modelo registra
========================

A camada digital de A "adquire o registro oscilográfico de alta
resolução do transitório **apenas durante a condução do SCR**" e dele
extrai as métricas de estresse dielétrico [FATO: doc A, p. 2, III-B].
Por isso :class:`ThyristorSnubber` expõe exatamente essas duas
grandezas: a **janela de condução** (lista de pares ``(t_on, t_off)``) e
a **energia dissipada** ``E_s = ∫ R_s·i² dt``.

Uso
===

::

    from app.simulation.emt.snubber import build_snubber_branch

    branch = build_snubber_branch(
        "snub_a", "barra_a", "gnd", breakover_voltage_V=6.0e3
    )
    ckt.extend(branch.components)
    solver.run(t_end=45.0e-3, controllers=[branch.controller])
    E_s = branch.controller.energy_J

Sem I/O, sem GUI. Determinístico.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Sequence

from app.core.logging_config import get_logger
from app.simulation.emt.components import Resistor, Switch

log = get_logger(__name__)


# ---------------------------------------------------------------------------
# Constantes do Documento A
# ---------------------------------------------------------------------------

#: Resistor de amortecimento por fase [Ω] [FATO: doc A, p. 2, III-A e
#: Tabela II, p. 3: "Snubber damping resistor Rs (per phase) 30 Ω"].
DOC_A_SNUBBER_RESISTANCE_OHM: float = 30.0

#: Estados do ramo.
SNUBBER_BLOCKED: str = "blocked"
SNUBBER_CONDUCTING: str = "conducting"
SNUBBER_STATES: tuple[str, ...] = (SNUBBER_BLOCKED, SNUBBER_CONDUCTING)


# ---------------------------------------------------------------------------
# Janela de condução
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ConductionWindow:
    """Uma janela de condução do par de SCR.

    Attributes
    ----------
    start_s:
        Instante do disparo (fechamento do ramo) [s].
    end_s:
        Instante do bloqueio natural [s]; ``None`` se a janela ainda
        estava aberta ao fim da simulação.
    peak_current_A:
        Maior |i| observado na janela [A].
    energy_J:
        Energia dissipada em ``R_s`` dentro da janela [J].
    """

    start_s: float
    end_s: float | None = None
    peak_current_A: float = 0.0
    energy_J: float = 0.0

    @property
    def duration_s(self) -> float:
        """Duração da janela [s]; 0,0 enquanto não bloqueada."""
        if self.end_s is None:
            return 0.0
        return float(self.end_s) - float(self.start_s)


@dataclass
class SnubberResult:
    """Resultado auditável do ramo após a manobra.

    Attributes
    ----------
    name:
        Rótulo do ramo.
    breakover_voltage_V:
        Nível de disparo efetivamente usado [V] — dado do usuário, NÃO
        do Documento A.
    n_firings:
        Número de disparos (janelas de condução iniciadas).
    windows:
        Janelas de condução, em ordem cronológica.
    energy_J:
        Energia total dissipada em ``R_s`` [J].
    peak_current_A:
        Maior |i| do ramo em toda a simulação [A].
    peak_branch_voltage_V:
        Maior |v| observado sobre o ramo (com ou sem condução) [V].
    """

    name: str = ""
    breakover_voltage_V: float = 0.0
    n_firings: int = 0
    windows: list[ConductionWindow] = field(default_factory=list)
    energy_J: float = 0.0
    peak_current_A: float = 0.0
    peak_branch_voltage_V: float = 0.0

    @property
    def conduction_time_s(self) -> float:
        """Tempo total de condução [s] (soma das janelas fechadas)."""
        return sum(w.duration_s for w in self.windows)

    @property
    def fired(self) -> bool:
        """``True`` se houve pelo menos um disparo."""
        return self.n_firings > 0


# ---------------------------------------------------------------------------
# Controlador do ramo
# ---------------------------------------------------------------------------


class ThyristorSnubber:
    """Par de SCR antiparalelos com ``R_s`` série, disparado por *breakover*.

    É um **controlador** do kernel: um chamável ``f(t, solver)`` passado
    em ``Solver.run(controllers=[...])``, invocado ANTES de cada passo,
    com ``t`` já resolvido e o estado do ramo já submetido.

    Representação do par antiparalelo
    ----------------------------------
    Os dois SCR são representados por UMA :class:`Switch` ideal
    bidirecional. A justificativa é que, do ponto de vista dos terminais,
    um par antiparalelo ideal disparado conduz nas duas polaridades sem
    queda; qual dos dois tiristores conduz é interno ao par e não altera
    a equação de ramo. O que se perde com isso está declarado em
    ``emt_snubber_ideal_valve_pair``: queda direta de condução (1 a 2 V
    por válvula), corrente de manutenção, ``di/dt`` e ``dv/dt`` críticos
    de comutação e tempo de recuperação reversa.

    Lógica de disparo e bloqueio
    -----------------------------

    ``blocked`` → (``|v_ramo| >= breakover_voltage_V``) → ``conducting``
        Emula o DIAC: disparo por nível, apenas com a grandeza local
        [FATO: doc A, p. 2, III-A, item 2]. Uma vez disparado, o SCR
        **trava** — não desliga por queda de tensão.

    ``conducting`` → (zero de corrente do ramo) → ``blocked``
        Bloqueio natural [FATO: doc A, p. 2, III-A, item 4]. O zero é
        detectado por troca de sinal entre passos consecutivos ou por
        ``|i| <= holding_current_A``.

    Parameters
    ----------
    switch:
        Chave do kernel que representa o par antiparalelo. Deve começar
        ABERTA (regime permanente transparente).
    resistor:
        Resistor de amortecimento em série no mesmo ramo. Usado para o
        valor de ``R_s`` na integral de energia e para a validação de
        consistência de nó.
    breakover_voltage_V:
        Nível de *breakover* do DIAC [V], > 0. **Obrigatório**: o
        Documento A não o informa [FATO por omissão].
    holding_current_A:
        Corrente de manutenção [A], >= 0. O ramo bloqueia quando
        ``|i| <= holding_current_A`` além do critério de troca de sinal.
        Padrão 0,0 (válvula ideal).
    min_conduction_time_s:
        Tempo mínimo de condução [s] antes de o bloqueio ser avaliado.
        Padrão 0,0. Serve para impedir o bloqueio espúrio no primeiro
        passo, em que a corrente ainda parte de zero.
    max_firings:
        Teto de disparos; acima dele o ramo permanece bloqueado e um
        aviso é registrado. Padrão 0 (sem teto).
    single_shot:
        Se ``True``, o ramo dispara UMA vez e nunca mais. Padrão
        ``False`` (o ciclo de A é rearmável, item 4).
    name:
        Rótulo do ramo; padrão o nome da chave.

    Raises
    ------
    ValueError
        Componentes de tipo errado, ramo mal formado (a chave e o
        resistor não compartilham um nó) ou parâmetros inválidos.
    """

    def __init__(
        self,
        switch: Switch,
        resistor: Resistor,
        *,
        breakover_voltage_V: float,
        holding_current_A: float = 0.0,
        min_conduction_time_s: float = 0.0,
        max_firings: int = 0,
        single_shot: bool = False,
        name: str = "",
    ) -> None:
        if not isinstance(switch, Switch):
            raise ValueError(
                f"ThyristorSnubber comanda um Switch do kernel, obtido "
                f"{type(switch).__name__}"
            )
        if not isinstance(resistor, Resistor):
            raise ValueError(
                f"ThyristorSnubber exige um Resistor de amortecimento, obtido "
                f"{type(resistor).__name__}"
            )
        if not set(switch.nodes) & set(resistor.nodes):
            raise ValueError(
                f"chave {switch.name!r} e resistor {resistor.name!r} não "
                f"compartilham nó: {switch.nodes} × {resistor.nodes} — não "
                f"formam um ramo série"
            )
        v_bo = float(breakover_voltage_V)
        if not math.isfinite(v_bo) or v_bo <= 0.0:
            raise ValueError(
                f"breakover_voltage_V deve ser finito e > 0, obtido "
                f"{breakover_voltage_V!r}. O Documento A NÃO informa este "
                f"nível [FATO por omissão]: ele é entrada obrigatória do "
                f"estudo e deve ser declarado como hipótese no laudo"
            )
        i_h = float(holding_current_A)
        if not math.isfinite(i_h) or i_h < 0.0:
            raise ValueError(f"holding_current_A deve ser finito e >= 0, obtido {holding_current_A!r}")
        t_min = float(min_conduction_time_s)
        if not math.isfinite(t_min) or t_min < 0.0:
            raise ValueError(
                f"min_conduction_time_s deve ser finito e >= 0, obtido {min_conduction_time_s!r}"
            )
        if int(max_firings) < 0:
            raise ValueError(f"max_firings deve ser >= 0, obtido {max_firings!r}")
        if switch.closed:
            log.warning(
                "snubber %r criado com a válvula FECHADA: o ramo NÃO é "
                "transparente em regime, contrariando o item 1 do ciclo de "
                "operação do Documento A",
                name or switch.name,
            )

        self.switch = switch
        self.resistor = resistor
        self.name = str(name) if name else str(switch.name)
        self.breakover_voltage_V = v_bo
        self.holding_current_A = i_h
        self.min_conduction_time_s = t_min
        self.max_firings = int(max_firings)
        self.single_shot = bool(single_shot)
        self.resistance_ohm = float(resistor.resistance_ohm)

        self._state: str = SNUBBER_BLOCKED
        self._i_prev: float = 0.0
        self._t_prev: float = -1.0
        self._conducting_prev: bool = False
        self._t_on: float = 0.0
        self._window_energy_J: float = 0.0
        self._window_peak_A: float = 0.0
        self._locked: bool = False
        self._locked_warned: bool = False
        self._result = SnubberResult(name=self.name, breakover_voltage_V=v_bo)

    # -- ciclo de vida ------------------------------------------------------

    def reset(self) -> None:
        """Reinicia a lógica e zera a integral de energia.

        ``Solver.run(reset=True)`` não alcança controladores; este método
        é chamado automaticamente quando o tempo retrocede (nova
        execução) e pode ser chamado explicitamente entre realizações.
        """
        self.switch.open()
        self._state = SNUBBER_BLOCKED
        self._i_prev = 0.0
        self._t_prev = -1.0
        self._conducting_prev = False
        self._t_on = 0.0
        self._window_energy_J = 0.0
        self._window_peak_A = 0.0
        self._locked = False
        self._locked_warned = False
        self._result = SnubberResult(
            name=self.name, breakover_voltage_V=self.breakover_voltage_V
        )

    # -- leitura ------------------------------------------------------------

    @property
    def state(self) -> str:
        """Estado corrente (:data:`SNUBBER_BLOCKED` ou :data:`SNUBBER_CONDUCTING`)."""
        return self._state

    @property
    def conducting(self) -> bool:
        """``True`` se o par de SCR está conduzindo."""
        return self._state == SNUBBER_CONDUCTING

    @property
    def result(self) -> SnubberResult:
        """Resultado acumulado do ramo."""
        return self._result

    @property
    def energy_J(self) -> float:
        """Energia dissipada em ``R_s`` [J]: ``E_s = ∫ R_s·i² dt``."""
        return self._result.energy_J + self._window_energy_J

    @property
    def n_firings(self) -> int:
        """Número de disparos ocorridos."""
        return self._result.n_firings

    @property
    def conduction_windows(self) -> tuple[ConductionWindow, ...]:
        """Janelas de condução fechadas, em ordem cronológica."""
        return tuple(self._result.windows)

    @property
    def conduction_time_s(self) -> float:
        """Tempo total de condução [s]."""
        return self._result.conduction_time_s

    # -- controlador --------------------------------------------------------

    def __call__(self, t: float, solver) -> None:
        """Avalia disparo, integral de energia e bloqueio no instante ``t``."""
        t_f = float(t)
        if self._t_prev >= 0.0 and t_f < self._t_prev:
            self.reset()

        i_now = float(self.switch.branch_current(0))
        # A tensão sensível ao DIAC é a do RAMO INTEIRO (válvula em série
        # com R_s): com a válvula bloqueada a corrente é nula, R_s não cai
        # tensão nenhuma e a tensão da válvula É a do ramo.
        v_branch = float(self.switch.branch_voltage(0))
        if self._state == SNUBBER_CONDUCTING:
            v_branch += float(self.resistor.branch_voltage(0))

        self._result.peak_branch_voltage_V = max(
            self._result.peak_branch_voltage_V, abs(v_branch)
        )

        # Integral de energia sobre o intervalo já percorrido, pela regra
        # do trapézio: E += ½·R_s·(i_ant² + i²)·Δt. Só acumula quando os
        # dois extremos do intervalo estavam em condução.
        if self._conducting_prev and self._t_prev >= 0.0:
            dt = t_f - self._t_prev
            if dt > 0.0:
                self._window_energy_J += (
                    0.5 * self.resistance_ohm * (self._i_prev**2 + i_now**2) * dt
                )
            self._window_peak_A = max(self._window_peak_A, abs(i_now))
            self._result.peak_current_A = max(self._result.peak_current_A, abs(i_now))

        if self._state == SNUBBER_BLOCKED:
            self._evaluate_breakover(t_f, v_branch)
        else:
            self._evaluate_natural_blocking(t_f, i_now)

        self._i_prev = i_now
        self._t_prev = t_f
        self._conducting_prev = self._state == SNUBBER_CONDUCTING

    # -- transições ---------------------------------------------------------

    def _evaluate_breakover(self, t: float, v_branch: float) -> None:
        """Disparo do DIAC por nível de tensão."""
        if self._locked:
            return
        if abs(v_branch) < self.breakover_voltage_V:
            return
        if self.max_firings and self._result.n_firings >= self.max_firings:
            if not self._locked_warned:
                self._locked_warned = True
                log.warning(
                    "snubber %r atingiu o teto de %d disparos em t = %.6g s e "
                    "permanecerá bloqueado; o ramo NÃO protege a partir daqui",
                    self.name,
                    self.max_firings,
                    t,
                )
            self._locked = True
            return
        self.switch.close()
        self._state = SNUBBER_CONDUCTING
        self._t_on = t
        self._window_energy_J = 0.0
        self._window_peak_A = 0.0
        self._result.n_firings += 1

    def _evaluate_natural_blocking(self, t: float, i_now: float) -> None:
        """Bloqueio natural no zero de corrente do ramo."""
        if (t - self._t_on) < self.min_conduction_time_s:
            return
        if not self._conducting_prev:
            # Primeiro passo após o disparo: a corrente ainda é a do
            # instante anterior (nula) e um teste de zero seria espúrio.
            return
        crossed = self._i_prev * i_now < 0.0
        at_zero = abs(i_now) <= self.holding_current_A
        if not (crossed or at_zero):
            return
        self.switch.open()
        self._state = SNUBBER_BLOCKED
        self._result.windows.append(
            ConductionWindow(
                start_s=self._t_on,
                end_s=t,
                peak_current_A=self._window_peak_A,
                energy_J=self._window_energy_J,
            )
        )
        self._result.energy_J += self._window_energy_J
        self._window_energy_J = 0.0
        self._window_peak_A = 0.0
        if self.single_shot:
            self._locked = True


# ---------------------------------------------------------------------------
# Montagem do ramo
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SnubberBranch:
    """Ramo de *snubber* montado: componentes + controlador.

    Attributes
    ----------
    switch:
        Par de SCR antiparalelos (chave ideal bidirecional).
    resistor:
        Resistor de amortecimento ``R_s``.
    controller:
        :class:`ThyristorSnubber` que comanda o ramo.
    """

    switch: Switch
    resistor: Resistor
    controller: ThyristorSnubber

    @property
    def components(self) -> tuple:
        """Componentes a inserir no circuito, na ordem de montagem."""
        return (self.switch, self.resistor)

    @property
    def name(self) -> str:
        """Rótulo do ramo."""
        return self.controller.name


def build_snubber_branch(
    name: str,
    node_bus: str,
    node_ref: str,
    *,
    breakover_voltage_V: float,
    resistance_ohm: float = DOC_A_SNUBBER_RESISTANCE_OHM,
    node_mid: str | None = None,
    **kwargs,
) -> SnubberBranch:
    """Monta o ramo ``barra → SCR‖SCR → R_s → referência``.

    Parameters
    ----------
    name:
        Prefixo dos componentes: gera ``<name>_scr`` e ``<name>_rs``.
    node_bus:
        Nó de conexão à barra (lado de carga do VCB, conforme a Fig. 2 de
        A, que mostra o ramo no barramento do painel e não nos bornes do
        motor [FATO: doc A, Fig. 2, p. 4 — leitura de figura]).
    node_ref:
        Nó de referência (neutro/terra), conforme a legenda da Fig. 1
        ("connected between the bus and the neutral")
        [FATO: doc A, Fig. 1, p. 2].
    breakover_voltage_V:
        Nível de disparo [V] — obrigatório, ver o cabeçalho do módulo.
    resistance_ohm:
        ``R_s`` [Ω]; padrão 30,0 de A.
    node_mid:
        Nó interno entre válvula e resistor; padrão ``<name>_mid``.
    **kwargs:
        Repassados a :class:`ThyristorSnubber`.

    Returns
    -------
    SnubberBranch
        Componentes e controlador prontos para ``Circuit.extend`` e
        ``Solver.run(controllers=...)``.
    """
    label = str(name)
    if not label:
        raise ValueError("build_snubber_branch exige um nome não vazio")
    mid = str(node_mid) if node_mid else f"{label}_mid"
    switch = Switch(f"{label}_scr", str(node_bus), mid, closed=False)
    resistor = Resistor(f"{label}_rs", mid, str(node_ref), float(resistance_ohm))
    controller = ThyristorSnubber(
        switch,
        resistor,
        breakover_voltage_V=float(breakover_voltage_V),
        name=label,
        **kwargs,
    )
    return SnubberBranch(switch=switch, resistor=resistor, controller=controller)


def three_phase_snubber(
    prefix: str,
    nodes_abc: Sequence[str],
    node_ref: str,
    *,
    breakover_voltage_V: float,
    resistance_ohm: float = DOC_A_SNUBBER_RESISTANCE_OHM,
    **kwargs,
) -> tuple[SnubberBranch, ...]:
    """Monta um ramo de *snubber* por fase (Fig. 1 de A).

    Parameters
    ----------
    prefix:
        Prefixo comum; gera ``<prefix>_a``, ``<prefix>_b``, ``<prefix>_c``
        (ou ``<prefix>_0..n`` se houver outro número de fases).
    nodes_abc:
        Nós de barra por fase.
    node_ref:
        Nó de referência comum (neutro/terra).
    breakover_voltage_V, resistance_ohm, **kwargs:
        Como em :func:`build_snubber_branch`.

    Returns
    -------
    tuple[SnubberBranch, ...]
        Um ramo por fase, na ordem informada.
    """
    nodes = tuple(str(n) for n in nodes_abc)
    if not nodes:
        raise ValueError("three_phase_snubber exige pelo menos um nó de fase")
    labels = ("a", "b", "c") if len(nodes) == 3 else tuple(str(k) for k in range(len(nodes)))
    return tuple(
        build_snubber_branch(
            f"{prefix}_{lbl}",
            node,
            str(node_ref),
            breakover_voltage_V=float(breakover_voltage_V),
            resistance_ohm=float(resistance_ohm),
            **kwargs,
        )
        for lbl, node in zip(labels, nodes)
    )


# ---------------------------------------------------------------------------
# Limitações declaradas do módulo
# ---------------------------------------------------------------------------

KNOWN_LIMITATIONS: dict[str, str] = {
    "emt_snubber_breakover_not_published": (
        "O nível de breakover do DIAC NÃO é informado pelo Documento A — nem "
        "no texto da Seção III-A, nem na Tabela II, nem na legenda da Fig. 1 "
        "[FATO por omissão]. Sem ele o instante de disparo não é reprodutível "
        "e, com ele, tampouco os valores da Tabela III. O parâmetro é "
        "obrigatório neste módulo justamente para que a escolha apareça como "
        "hipótese do usuário e não como dado do artigo."
    ),
    "emt_snubber_ideal_valve_pair": (
        "O par de SCR antiparalelos é UMA chave ideal bidirecional. Não há "
        "queda direta de condução (1 a 2 V por válvula), corrente de "
        "manutenção real, di/dt e dv/dt críticos de comutação, tempo de "
        "recuperação reversa nem atraso de porta. O disparo e o bloqueio são "
        "instantâneos no passo, de modo que o tempo de resposta reportado é "
        "COTA INFERIOR do real — A declara disparo 'within a microsecond of "
        "the anomaly', que é exatamente o passo de integração."
    ),
    "emt_snubber_no_diac_dynamics": (
        "O DIAC é reduzido a um comparador de nível com travamento. A "
        "característica real de resistência negativa, a tensão de manutenção "
        "e a dispersão de fabricação do breakover (tipicamente ±10 %) não são "
        "representadas; a sensibilidade do resultado a essa dispersão deve ser "
        "obtida por varredura do parâmetro."
    ),
    "emt_snubber_firing_quantized_to_step": (
        "Disparo e bloqueio ocorrem apenas em instante múltiplo de Δt, sem "
        "interpolação para o cruzamento exato do nível de breakover ou do zero "
        "de corrente. Com Δt de 1 µs e frentes de 15 kV/µs, a tensão pode "
        "ultrapassar o nível de disparo em até 15 kV dentro de um único passo "
        "[CÁLCULO PRÓPRIO], de modo que o pico registrado depende do passo. "
        "Verifique a convergência do pico reduzindo Δt."
    ),
    "emt_snubber_energy_from_resistor_only": (
        "A energia reportada é E_s = ∫R_s·i² dt, isto é, apenas a dissipada no "
        "resistor de amortecimento. A energia dissipada nas válvulas (ideais "
        "aqui) e a trocada com as capacitâncias parasitas do ramo não entram "
        "na conta. E_s é, portanto, COTA INFERIOR da energia absorvida pelo "
        "ramo, e é a grandeza correta para dimensionar o resistor — não para "
        "dimensionar as válvulas."
    ),
    "emt_snubber_single_branch_per_phase": (
        "Um ramo por fase, entre barra e referência (ligação estrela, "
        "conforme a Fig. 1 de A). Ligação em delta, ramo entre fases e "
        "acoplamento entre as três células não são representados; o "
        "desequilíbrio entre fases decorre apenas do escalonamento dos polos "
        "do disjuntor."
    ),
}


__all__ = [
    "DOC_A_SNUBBER_RESISTANCE_OHM",
    "SNUBBER_BLOCKED",
    "SNUBBER_CONDUCTING",
    "SNUBBER_STATES",
    "ConductionWindow",
    "SnubberResult",
    "ThyristorSnubber",
    "SnubberBranch",
    "build_snubber_branch",
    "three_phase_snubber",
    "KNOWN_LIMITATIONS",
]
