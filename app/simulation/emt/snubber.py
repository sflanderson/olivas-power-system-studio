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
from typing import Callable, Sequence

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
    gate:
        **Modo literal.** Chamável sem argumentos que devolve o estado da
        porta da válvula. Enquanto devolver ``False`` o disparo é
        inibido, ainda que a tensão de disparo seja excedida. Padrão
        ``None`` = sem porta, o comportamento de sempre. É por aqui que
        :class:`SnubberMasterTrigger` replica o travamento de ``FM`` do
        MODEL ``SNUB_CTRL`` do arquivo. A porta NÃO interrompe uma
        condução em curso: um tiristor já disparado só bloqueia no zero
        de corrente, e é assim que o arquivo se comporta.
    deionization_time_s:
        **Modo literal.** Tempo morto após o bloqueio, durante o qual a
        válvula não redispara [s]. Padrão 0,0 — que é o valor impresso
        pela listagem do caso ("Valve. 2.404E+03 1.000E+00 0.000E+00")
        [FATO: listagem].
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
        gate: Callable[[], bool] | None = None,
        deionization_time_s: float = 0.0,
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
        if gate is not None and not callable(gate):
            raise ValueError(f"gate deve ser chamável ou None, obtido {gate!r}")
        t_deion = float(deionization_time_s)
        if not math.isfinite(t_deion) or t_deion < 0.0:
            raise ValueError(
                f"deionization_time_s deve ser finito e >= 0, obtido {deionization_time_s!r}"
            )
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
        self.gate = gate
        self.deionization_time_s = t_deion
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
        self._t_off: float = -1.0
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
        self._t_off = -1.0
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
        """Disparo por nível de tensão, condicionado à porta quando houver.

        No MODO LITERAL a porta é a saída ``GA_P``/``GA_N`` do MODEL
        ``SNUB_CTRL``: enquanto ela vale 0, a válvula não dispara ainda
        que a tensão de disparo seja excedida; depois de travada em 1,
        o disparo passa a ser decidido só pelo nível local — que é o
        comportamento de um tiristor com sinal de porta permanente.
        """
        if self._locked:
            return
        if self.gate is not None and not self.gate():
            return
        if self.deionization_time_s > 0.0 and self._t_off >= 0.0:
            if (t - self._t_off) < self.deionization_time_s:
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
        self._t_off = float(t)
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
# Modo de compatibilidade LITERAL com o ramo amortecedor do arquivo ATP
# ---------------------------------------------------------------------------
#
# Reproduz o MODEL ``SNUB_CTRL`` e os cartões de válvula e de resistor da
# variante com amortecedor
# [REPO: tests/fixtures/atp/trt_all_motors_com_snubber_2026-04.atp:532-581
# (MODEL), :752-754 (resistores de 30 Ω) e :769-774 (válvulas tipo 11)].
# Modo OPCIONAL, selecionado por parâmetro: o comportamento padrão de
# :class:`ThyristorSnubber` e de :func:`build_snubber_branch` não muda.

#: Tensão de disparo das válvulas [V] [FATO: listagem, "Valve. 2.404E+03
#: 1.000E+00 0.000E+00"]. Vale 1,0009 vez a tensão nominal fase-terra
#: eficaz do barramento de 4,16 kV, contra um pico de regime de 3386 V —
#: ver ``emt_snubber_atp_trigger_below_steady_peak``.
ATP_SNUBBER_BREAKOVER_V: float = 2404.0

#: Corrente de manutenção das válvulas [A] [FATO: listagem].
ATP_SNUBBER_HOLDING_CURRENT_A: float = 1.0

#: Tempo de desionização das válvulas [s] [FATO: listagem, terceiro campo
#: nulo]. O cartão do arquivo traz ``.005`` na mesma posição — ver
#: ``emt_snubber_atp_valve_card_vs_listing``.
ATP_SNUBBER_DEIONIZATION_TIME_S: float = 0.0

#: Resistor de cada fase para a terra [Ω] [FATO: arquivo, cartões
#: ``XX0034 30.``, ``XX0035 30.`` e ``XX0042 30.``].
ATP_SNUBBER_RESISTANCE_OHM: float = 30.0

#: Limiar do controlador mestre: ``IF (STA > 1.9 OR ...)`` [FATO: arquivo,
#: MODEL SNUB_CTRL]. Nos códigos de estado do MODEL do disjuntor, 1,9
#: separa o estado de arco de frequência industrial (1) dos estados
#: aberto (2) e de arco de alta frequência (3): a trava é acionada pelo
#: PRIMEIRO desses dois, isto é, na primeira interrupção declarada.
ATP_SNUBBER_LATCH_THRESHOLD: float = 1.9

#: Nomes das seis saídas de porta do MODEL ``SNUB_CTRL``.
ATP_SNUBBER_GATE_NAMES: tuple[str, ...] = (
    "GA_P",
    "GA_N",
    "GB_P",
    "GB_N",
    "GC_P",
    "GC_N",
)

#: Correspondência entre o nome do estado da máquina de
#: :class:`~app.simulation.emt.vcb.VacuumCircuitBreakerModel` e o CÓDIGO
#: inteiro do MODEL do arquivo, para que o controlador mestre possa
#: observar polos dos dois modos com o mesmo limiar numérico.
ATP_STATE_CODE_BY_NAME: dict[str, int] = {
    "closed": 0,
    "arcing": 1,
    "arcing_hf": 3,
    "open": 2,
    "cleared": 2,
}


def atp_state_code(pole) -> float:
    """Código de estado do polo ``pole`` na numeração do arquivo.

    Aceita um :class:`~app.simulation.emt.vcb.AtpModelCompatibility`
    (que já expõe ``cb_state`` inteiro) ou um
    :class:`~app.simulation.emt.vcb.VacuumCircuitBreakerModel` (cujo
    ``state`` é um rótulo textual, traduzido por
    :data:`ATP_STATE_CODE_BY_NAME`).

    Raises
    ------
    ValueError
        O objeto não expõe estado legível.
    """
    code = getattr(pole, "cb_state", None)
    if code is not None:
        return float(code)
    name = getattr(pole, "state", None)
    if isinstance(name, str) and name in ATP_STATE_CODE_BY_NAME:
        return float(ATP_STATE_CODE_BY_NAME[name])
    raise ValueError(
        f"polo {pole!r} não expõe 'cb_state' nem um 'state' conhecido; "
        f"estados aceitos: {sorted(ATP_STATE_CODE_BY_NAME)}"
    )


class SnubberMasterTrigger:
    """MODEL ``SNUB_CTRL``: uma única trava de disparo para as três fases.

    O MODEL do arquivo tem quatro linhas de lógica::

        IF (STA > 1.9 OR STB > 1.9 OR STC > 1.9 OR FM > 0.5) THEN
          FM := 1.0
        ENDIF
        GA_P := FM   ...   GC_N := FM

    Três consequências, todas reproduzidas aqui:

    1. **Comum às três fases.** Basta UM polo cruzar o limiar para armar
       as seis portas — as duas válvulas de cada uma das três fases.
    2. **Trava.** ``FM`` só é escrito com 1,0; o próprio ``FM > 0.5`` está
       na condição, de modo que a partir da primeira ocorrência a
       expressão é permanentemente verdadeira. Não há liberação em
       nenhum ponto do arquivo fora do bloco ``INIT``.
    3. **O limiar é 1,9, não 0,9.** Nos códigos do MODEL do disjuntor
       (0 fechado, 1 arco, 2 aberto, 3 arco de alta frequência) o gatilho
       NÃO é o estado de arco de frequência industrial: é o estado
       ABERTO — a primeira interrupção declarada — ou o de arco de alta
       frequência. Ver ``emt_snubber_atp_latch_threshold_is_state_two``.

    Como o polo em modo literal alcança o estado 2 no passo seguinte à
    separação de contatos, a trava fecha praticamente junto com a
    manobra, e as válvulas ficam permanentemente habilitadas pelo resto
    da simulação — inclusive depois de a rede voltar ao regime.

    Parameters
    ----------
    poles:
        Polos observados (``STA``, ``STB``, ``STC``).
    controllers:
        Controladores de válvula a acionar depois de atualizar ``FM``.
        Podem ser vazios: neste caso o objeto é só a porta, consultada
        por :meth:`gate`.
    latch_threshold:
        Limiar da condição; padrão :data:`ATP_SNUBBER_LATCH_THRESHOLD`.
    drive_controllers:
        Se ``True`` (padrão), este objeto CHAMA os controladores de
        válvula a cada passo, e portanto substitui-os na lista de
        controladores do solver. Se ``False``, apenas atualiza ``FM`` e
        os controladores devem ser passados ao solver separadamente.
    name:
        Rótulo.
    """

    def __init__(
        self,
        poles: Sequence,
        controllers: Sequence = (),
        *,
        latch_threshold: float = ATP_SNUBBER_LATCH_THRESHOLD,
        drive_controllers: bool = True,
        name: str = "snub_ctrl",
    ) -> None:
        limiar = float(latch_threshold)
        if not math.isfinite(limiar):
            raise ValueError(f"latch_threshold deve ser finito, obtido {latch_threshold!r}")
        self.poles = tuple(poles)
        self.controllers = tuple(controllers)
        self.latch_threshold = limiar
        self.drive_controllers = bool(drive_controllers)
        self.name = str(name)
        self._fm: float = 0.0
        self._armed_time_s: float | None = None
        self._t_prev: float = -1.0

    # -- leitura ------------------------------------------------------------

    @property
    def fm(self) -> float:
        """``FM`` do MODEL: 0,0 ou 1,0."""
        return self._fm

    @property
    def armed(self) -> bool:
        """``True`` depois da primeira ocorrência do limiar."""
        return self._fm > 0.5

    @property
    def armed_time_s(self) -> float | None:
        """Instante em que a trava fechou [s]; ``None`` se nunca fechou."""
        return self._armed_time_s

    @property
    def gates(self) -> dict[str, float]:
        """As seis saídas de porta do MODEL, todas iguais a ``FM``."""
        return {nome: self._fm for nome in ATP_SNUBBER_GATE_NAMES}

    def gate(self) -> bool:
        """Porta a ligar em ``ThyristorSnubber(gate=...)``."""
        return self._fm > 0.5

    # -- ciclo de vida ------------------------------------------------------

    def reset(self) -> None:
        """Bloco ``INIT`` do MODEL: ``FM := 0`` e portas em zero."""
        self._fm = 0.0
        self._armed_time_s = None
        self._t_prev = -1.0
        for ctrl in self.controllers:
            reset = getattr(ctrl, "reset", None)
            if callable(reset):
                reset()

    # -- controlador --------------------------------------------------------

    def __call__(self, t: float, solver) -> None:
        """Um ``EXEC`` do MODEL ``SNUB_CTRL``."""
        t_f = float(t)
        if self._t_prev >= 0.0 and t_f < self._t_prev:
            self.reset()
        self._t_prev = t_f
        if self._fm <= 0.5:
            disparo = any(
                atp_state_code(polo) > self.latch_threshold for polo in self.poles
            )
            if disparo:
                self._fm = 1.0
                self._armed_time_s = t_f
        if self.drive_controllers:
            for ctrl in self.controllers:
                ctrl(t_f, solver)


def build_atp_literal_snubber_branch(
    name: str,
    node_bus: str,
    node_ref: str,
    *,
    breakover_voltage_V: float = ATP_SNUBBER_BREAKOVER_V,
    holding_current_A: float = ATP_SNUBBER_HOLDING_CURRENT_A,
    resistance_ohm: float = ATP_SNUBBER_RESISTANCE_OHM,
    deionization_time_s: float = ATP_SNUBBER_DEIONIZATION_TIME_S,
    gate: Callable[[], bool] | None = None,
    **kwargs,
) -> SnubberBranch:
    """Monta o ramo do arquivo: par de válvulas + 30 Ω da fase para a terra.

    Topologia do arquivo, fase A [FATO: arquivo]::

        X0002A ──[11 X0002A→XX0042]──┬── XX0042 ──[30 Ω]── terra
               ──[11 XX0042→X0002A]──┘

    isto é, DUAS válvulas antiparalelas entre a barra e o nó do resistor,
    e o resistor de 30 Ω desse nó para a terra. As duas válvulas são
    representadas por uma única chave bidirecional, como no modo padrão.

    Parameters
    ----------
    name, node_bus, node_ref:
        Como em :func:`build_snubber_branch`.
    breakover_voltage_V:
        Tensão de disparo [V]; padrão 2404 V [FATO: listagem].
    holding_current_A:
        Corrente de manutenção [A]; padrão 1 A [FATO: listagem].
    resistance_ohm:
        Resistor da fase para a terra [Ω]; padrão 30 Ω [FATO: arquivo].
    deionization_time_s:
        Tempo morto após o bloqueio [s]; padrão 0 [FATO: listagem].
    gate:
        Porta comum das válvulas — tipicamente
        ``SnubberMasterTrigger.gate``.
    **kwargs:
        Repassados a :class:`ThyristorSnubber`.
    """
    return build_snubber_branch(
        name,
        node_bus,
        node_ref,
        breakover_voltage_V=float(breakover_voltage_V),
        resistance_ohm=float(resistance_ohm),
        holding_current_A=float(holding_current_A),
        deionization_time_s=float(deionization_time_s),
        gate=gate,
        **kwargs,
    )


def three_phase_atp_literal_snubber(
    prefix: str,
    nodes_abc: Sequence[str],
    node_ref: str,
    poles: Sequence,
    **kwargs,
) -> tuple[tuple[SnubberBranch, ...], SnubberMasterTrigger]:
    """Três ramos literais e o controlador mestre comum que os arma.

    Devolve ``(ramos, mestre)``. O ``mestre`` é o ÚNICO controlador a
    passar ao solver: ele aciona os três controladores de válvula depois
    de atualizar ``FM``, na mesma ordem em que o MODEL do arquivo escreve
    as seis portas.

    Parameters
    ----------
    prefix:
        Prefixo comum dos ramos.
    nodes_abc:
        Nós de barra por fase.
    node_ref:
        Nó de terra comum.
    poles:
        Polos do disjuntor observados pelo controlador mestre.
    **kwargs:
        Repassados a :func:`build_atp_literal_snubber_branch`.
    """
    nodes = tuple(str(n) for n in nodes_abc)
    if not nodes:
        raise ValueError("three_phase_atp_literal_snubber exige ao menos um nó de fase")
    rotulos = ("a", "b", "c") if len(nodes) == 3 else tuple(str(k) for k in range(len(nodes)))
    mestre = SnubberMasterTrigger(poles, (), name=f"{prefix}_ctrl")
    ramos = tuple(
        build_atp_literal_snubber_branch(
            f"{prefix}_{lbl}",
            node,
            str(node_ref),
            gate=mestre.gate,
            **kwargs,
        )
        for lbl, node in zip(rotulos, nodes)
    )
    mestre.controllers = tuple(r.controller for r in ramos)
    return ramos, mestre


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
    "emt_snubber_atp_trigger_below_steady_peak": (
        "MODO LITERAL. A tensão de disparo das válvulas do caso é 2404 V "
        "[FATO: listagem], ou 1,0009 vez a tensão nominal fase-terra eficaz, "
        "enquanto o pico de regime no barramento é 3386 V. O disparo está, "
        "portanto, ABAIXO do regime: uma vez travado o comando pelo "
        "controlador mestre, a válvula dispara em todo semiciclo e conduz de "
        "|v| = 2404 V até a corrente cair à corrente de manutenção de 1 A, "
        "isto é, praticamente até o zero de tensão. O ramo deixa de ser um "
        "amortecedor de transitório e passa a ser uma carga permanente de "
        "dezenas a centenas de quilowatts por fase sobre o resistor de 30 Ω "
        "[CÁLCULO PRÓPRIO, medido em tests/test_emt_vcb_snubber.py]. Nenhum "
        "resultado de energia ou de dv/dt extraído deste caso pode ser lido "
        "como desempenho do amortecedor projetado."
    ),
    "emt_snubber_atp_latch_threshold_is_state_two": (
        "MODO LITERAL. O MODEL SNUB_CTRL do arquivo arma com STA > 1.9, e não "
        "com STA > 0.9. Nos códigos do MODEL do disjuntor (0 fechado, 1 arco, "
        "2 aberto, 3 arco de alta frequência) isso significa que a trava NÃO "
        "fecha no estado de arco de frequência industrial: ela fecha no estado "
        "ABERTO, a primeira interrupção declarada, ou no de arco de alta "
        "frequência. A diferença é de um passo de integração no caso de "
        "referência, porque o polo literal alcança o estado 2 logo depois da "
        "separação, mas é uma diferença de SEMÂNTICA: o ramo não é armado pelo "
        "arco, é armado pela interrupção."
    ),
    "emt_snubber_atp_latch_never_released": (
        "MODO LITERAL. FM só recebe 1,0, e a própria condição do IF inclui "
        "FM > 0.5: depois da primeira ocorrência a habilitação é permanente "
        "até o fim da simulação, mesmo com o disjuntor já interrompido e a "
        "rede de volta ao regime. Não há desarme, temporização nem histerese "
        "no arquivo. Junto com a tensão de disparo abaixo do pico de regime, é "
        "esta a razão de o ramo conduzir indefinidamente."
    ),
    "emt_snubber_atp_valve_card_vs_listing": (
        "MODO LITERAL. O cartão de válvula do arquivo traz os campos 3.E3, 1. "
        "e .005 [REPO: tests/fixtures/atp/trt_all_motors_com_snubber_2026-04."
        "atp, cartões tipo 11], enquanto a listagem de saída imprime "
        "'Valve. 2.404E+03 1.000E+00 0.000E+00' [FATO: listagem]. Tensão de "
        "disparo e tempo de desionização DIVERGEM entre o cartão e a listagem. "
        "Os padrões deste módulo seguem a LISTAGEM, que é o que o programa "
        "efetivamente executou, e os três valores estão parametrizados. A "
        "atribuição campo a campo do cartão sob o cabeçalho impresso continua "
        "pendente de confirmação e está registrada como tal na especificação "
        "do caso."
    ),
    "emt_snubber_atp_valve_pair_is_one_switch": (
        "MODO LITERAL. O arquivo tem DUAS válvulas antiparalelas por fase, "
        "cada uma com sua porta (GA_P e GA_N), e este módulo as representa por "
        "uma única chave bidirecional com uma porta só. Como o controlador "
        "mestre escreve o MESMO FM nas seis portas, a redução é exata quanto "
        "ao comando; o que se perde é a assimetria entre os dois sentidos de "
        "condução — queda direta, corrente de manutenção e desionização "
        "independentes por válvula."
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
    # modo de compatibilidade literal com o arquivo ATP
    "ATP_SNUBBER_BREAKOVER_V",
    "ATP_SNUBBER_HOLDING_CURRENT_A",
    "ATP_SNUBBER_DEIONIZATION_TIME_S",
    "ATP_SNUBBER_RESISTANCE_OHM",
    "ATP_SNUBBER_LATCH_THRESHOLD",
    "ATP_SNUBBER_GATE_NAMES",
    "ATP_STATE_CODE_BY_NAME",
    "atp_state_code",
    "SnubberMasterTrigger",
    "build_atp_literal_snubber_branch",
    "three_phase_atp_literal_snubber",
    "KNOWN_LIMITATIONS",
]
