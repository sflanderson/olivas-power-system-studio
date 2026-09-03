"""
app.simulation.emt.vcb — modelo dinâmico de disjuntor a vácuo (VCB) por
polo, sobre o kernel EMT dedicado do Olivas Power System Studio.

Escopo
======

Este módulo NÃO é um ramo de circuito: é a camada de **controle** que
comanda uma :class:`app.simulation.emt.components.Switch` ideal do
kernel, reproduzindo os três fenômenos que a chave ideal, por
declaração, não contém (limitação ``emt_ideal_switch_no_arc``):

1. **Corte de corrente (*current chopping*)** — o arco a vácuo é
   instável e colapsa antes do zero natural quando a corrente
   instantânea cai abaixo de um nível ``I_ch`` de poucos ampères
   [FATO: doc A, p. 2, II-A e Tabela II, p. 3: ``I_ch`` de 1 A a 2 A].
2. **Recuperação dielétrica (*cold recovery*)** — a suportabilidade do
   *gap* aberto cresce com o tempo decorrido desde a extinção segundo a
   lei PARABÓLICA de taxa de crescimento da rigidez dielétrica (RRDS)

   .. math:: V_{wth}(t) = A\\,t + B\\,t^2

   com ``A = 0,801 kV/ms`` e ``B = 1,226 kV/ms²``
   [FATO: doc A, p. 3, IV-B e Tabela II].
3. **Reignição de alta frequência** — declarada quando a TRV através do
   *gap* excede a suportabilidade instantânea; a corrente de alta
   frequência subsequente é interrompida conforme o critério de
   ``di/dt`` no zero (faixa 5 A/µs a 15 A/µs)
   [FATO: doc A, p. 3, IV-B e Tabela II].

O escalonamento (*stagger*) dos instantes de separação de contatos entre
polos, de 14 ms a 25 ms [FATO: doc A, p. 3, IV-B e Tabela II], é
parametrizado em :func:`three_phase_vcb`.

A ambiguidade do critério de di/dt
===================================

O Documento A é **internamente ambíguo** quanto ao sentido do critério, e
a Etapa 2 §9.2 do estudo de RUL registra a divergência item a item
[REPO: docs/research/rul_isolamento/02_ETAPA2_cruzamento_A_x_B.md:738]:

* o **texto** da Seção IV-B afirma que a corrente de alta frequência "is
  interrupted when its di/dt at the zero crossing **exceeds** a critical
  value" [FATO: doc A, p. 3, IV-B];
* a **Tabela II** do mesmo artigo nomeia o parâmetro "Critical
  **reignition** di/dt" [FATO: doc A, Tabela II, p. 3], ou seja, o valor
  acima do qual há reignição — convenção oposta, e é a adotada pelo
  MODEL do repositório [REPO:
  app/preprocessor/atp_templates/vcb_reignition.mod:98-101].

A literatura consolidada de interruptores a vácuo adota a convenção
FÍSICA: o interruptor extingue a corrente de alta frequência quando o
``di/dt`` no zero está **dentro** da sua capacidade de extinção, isto é,
quando ``|di/dt| <= di/dt_crítico``; acima disso o plasma não se
desioniza a tempo e o arco persiste
[LITERATURA: S. M. Wong, L. A. Snider e E. W. C. Lo, "Overvoltages and
reignition behavior of vacuum circuit breaker", *6th APSCOM*, 2003,
pp. 653-658, doi:10.1049/cp:20030663;
LITERATURA: T. Abdulahovic, T. Thiringer, M. Reza e H. Breder, "Vacuum
circuit-breaker parameter calculation and modelling for power system
transient studies", *IEEE Transactions on Power Delivery*, vol. 32,
n. 3, pp. 1165-1172, 2017, doi:10.1109/TPWRD.2014.2357993].

Por isso o padrão deste módulo é :data:`DIDT_INTERRUPT_WITHIN`
(interrompe quando ``|di/dt| <= capacidade``). A convenção invertida
permanece disponível em :data:`DIDT_INTERRUPT_ABOVE`, exclusivamente
para reproduzir a leitura literal do texto de A e o comportamento do
``.mod`` legado — **não** use a convenção invertida em estudo de
isolamento sem declarar a escolha no laudo, porque o sinal do efeito do
parâmetro sobre ``n_r`` (entrada do vetor de estresse) se inverte com
ela [REPO:
docs/research/rul_isolamento/02_ETAPA2_cruzamento_A_x_B.md:738, item 4].

Uso
===

::

    from app.simulation.emt import Circuit, Solver, Switch
    from app.simulation.emt.vcb import VacuumCircuitBreakerModel

    sw = ckt.add(Switch("cb_a", "fonte", "carga", closed=True))
    vcb = VacuumCircuitBreakerModel(sw, separation_time_s=14.0e-3)
    solver.run(t_end=45.0e-3, controllers=[vcb])
    n_r = vcb.reignition_count

Sem I/O, sem GUI. Determinístico para uma dada semente.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Protocol, Sequence

import numpy as np

from app.core.logging_config import get_logger
from app.simulation.emt.components import Switch

log = get_logger(__name__)


# ---------------------------------------------------------------------------
# Constantes do Documento A (Tabela II, p. 3)
# ---------------------------------------------------------------------------

#: Constante A da lei parabólica de RRDS [kV/ms] [FATO: doc A, Tabela II, p. 3].
DOC_A_RRDS_A_KV_PER_MS: float = 0.801

#: Constante B da lei parabólica de RRDS [kV/ms²] [FATO: doc A, Tabela II, p. 3].
DOC_A_RRDS_B_KV_PER_MS2: float = 1.226

#: Faixa de corrente de *chopping* [A] [FATO: doc A, Tabela II, p. 3].
DOC_A_CHOPPING_RANGE_A: tuple[float, float] = (1.0, 2.0)

#: Faixa de di/dt crítico de alta frequência [A/µs] [FATO: doc A, Tabela II, p. 3].
DOC_A_DIDT_RANGE_A_PER_US: tuple[float, float] = (5.0, 15.0)

#: Faixa dos instantes de separação de contatos entre polos [s]
#: [FATO: doc A, p. 3, IV-B e Tabela II: "14 ms to 25 ms"].
#:
#: [FATO por omissão] A não declara se 14-25 ms é a FAIXA dos instantes
#: absolutos de separação ou a DIFERENÇA entre polos. A interpretação
#: adotada aqui — instantes absolutos dentro da faixa — é a única
#: compatível com a janela simulada de 45 ms e com a dispersão física de
#: um disjuntor tripolar de comando único (o intervalo entre zeros de
#: corrente consecutivos de fases distintas é 1/(6f) = 2,78 ms a 60 Hz,
#: de modo que 11 ms de diferença entre polos seria mecanicamente
#: implausível se lida como diferença) [INFERÊNCIA FÍSICA].
DOC_A_STAGGER_RANGE_S: tuple[float, float] = (14.0e-3, 25.0e-3)

#: Passo de integração do Documento A [s] [FATO: doc A, Tabela II, p. 3].
DOC_A_TIME_STEP_S: float = 1.0e-6

#: Janela simulada do Documento A [s] [FATO: doc A, Tabela II, p. 3].
DOC_A_WINDOW_S: float = 45.0e-3


# ---------------------------------------------------------------------------
# Convenções de di/dt — ver §"A ambiguidade do critério de di/dt"
# ---------------------------------------------------------------------------

#: Convenção FÍSICA (padrão): a corrente de alta frequência é
#: interrompida no zero quando ``|di/dt| <= capacidade``.
DIDT_INTERRUPT_WITHIN: str = "interrupt_within"

#: Convenção INVERTIDA (leitura literal do texto de A, p. 3, IV-B): a
#: corrente é interrompida quando ``|di/dt| > capacidade``. Disponível
#: apenas para reprodução do texto de A e do ``.mod`` legado.
DIDT_INTERRUPT_ABOVE: str = "interrupt_above"

#: Convenções aceitas.
DIDT_CONVENTIONS: tuple[str, ...] = (DIDT_INTERRUPT_WITHIN, DIDT_INTERRUPT_ABOVE)


# ---------------------------------------------------------------------------
# Estados da máquina do polo
# ---------------------------------------------------------------------------

#: Contatos ainda fechados; nenhuma separação comandada.
STATE_CLOSED: str = "closed"

#: Contatos separados, arco de frequência industrial conduzindo.
STATE_ARCING: str = "arcing"

#: Contatos separados, arco de alta frequência conduzindo (pós-reignição).
STATE_ARCING_HF: str = "arcing_hf"

#: Corrente cortada/interrompida; *gap* em recuperação dielétrica.
STATE_OPEN: str = "open"

#: Interrupção definitiva (limite de reignições atingido ou trava manual).
STATE_CLEARED: str = "cleared"

#: Estados possíveis, na ordem canônica do ciclo de manobra.
VCB_STATES: tuple[str, ...] = (
    STATE_CLOSED,
    STATE_ARCING,
    STATE_ARCING_HF,
    STATE_OPEN,
    STATE_CLEARED,
)

#: Distribuições aceitas para a amostragem de ``I_ch``.
CHOPPING_DISTRIBUTIONS: tuple[str, ...] = ("uniform", "normal", "deterministic")

#: Teto de reignições por polo antes de travar em :data:`STATE_CLEARED`.
#: Salvaguarda numérica, NÃO física: uma sequência real de reignições de
#: VCB tem dezenas de eventos [LITERATURA: A. Greenwood, *Electrical
#: Transients in Power Systems*, 2. ed., Wiley, 1991, cap. 5].
DEFAULT_MAX_REIGNITIONS: int = 200


# ---------------------------------------------------------------------------
# Leis de recuperação dielétrica
# ---------------------------------------------------------------------------


class DielectricRecovery(Protocol):
    """Contrato mínimo de uma lei de recuperação dielétrica."""

    def withstand_V(self, elapsed_s: float) -> float:
        """Suportabilidade do *gap* [V] após ``elapsed_s`` da extinção."""
        ...


@dataclass(frozen=True)
class ParabolicRecovery:
    """Lei PARABÓLICA do Documento A: ``V_wth(t) = A·t + B·t²``.

    ``A`` em kV/ms e ``B`` em kV/ms², como publicados
    [FATO: doc A, Tabela II, p. 3]. A conversão para SI é interna, de
    modo que os valores da tabela entram sem transformação pelo usuário.

    Notas de auditoria
    ------------------
    Em ``t = 1 ms`` esta lei entrega ``0,801 + 1,226 = 2,027 kV``, contra
    ``17,7 kV`` da lei LINEAR do ``.mod`` do repositório — razão de
    ``8,7×`` [CÁLCULO PRÓPRIO; cf. Etapa 2 §9.2]. A inclinação
    instantânea ``A + 2Bt`` só alcança os 17 kV/ms do ``.mod`` em
    ``t = 6,6 ms``. As duas leis são pontos legítimos de um espaço de
    parâmetros incertos (faixa publicada de RRDS: 2 a 50 kV/ms) e a
    escolha deve ser declarada no laudo.
    """

    a_kV_per_ms: float = DOC_A_RRDS_A_KV_PER_MS
    b_kV_per_ms2: float = DOC_A_RRDS_B_KV_PER_MS2

    def __post_init__(self) -> None:
        for label, value in (("a_kV_per_ms", self.a_kV_per_ms), ("b_kV_per_ms2", self.b_kV_per_ms2)):
            v = float(value)
            if not math.isfinite(v):
                raise ValueError(f"{label} deve ser finito, obtido {value!r}")
            if v < 0.0:
                raise ValueError(
                    f"{label} deve ser >= 0 (a rigidez do gap não decresce), obtido {value!r}"
                )
        if float(self.a_kV_per_ms) == 0.0 and float(self.b_kV_per_ms2) == 0.0:
            raise ValueError(
                "recuperação dielétrica nula (A = B = 0): o gap nunca suporta "
                "tensão e a simulação reignitaria indefinidamente"
            )

    def withstand_V(self, elapsed_s: float) -> float:
        """``V_wth`` [V] após ``elapsed_s`` [s] da extinção do arco."""
        t_ms = max(0.0, float(elapsed_s)) * 1.0e3
        return 1.0e3 * (self.a_kV_per_ms * t_ms + self.b_kV_per_ms2 * t_ms * t_ms)

    def slope_kV_per_ms(self, elapsed_s: float) -> float:
        """Inclinação instantânea ``A + 2B·t`` [kV/ms] — grandeza de auditoria."""
        t_ms = max(0.0, float(elapsed_s)) * 1.0e3
        return self.a_kV_per_ms + 2.0 * self.b_kV_per_ms2 * t_ms


@dataclass(frozen=True)
class LinearRecovery:
    """Lei LINEAR do ``vcb_reignition.mod`` legado: ``U0 + k·t``.

    Adaptador de compatibilidade. Os padrões reproduzem
    ``U0_dielec = 690 V`` e ``k_dielec = 17 V/µs``
    [REPO: app/preprocessor/atp_templates/vcb_reignition.mod:52-53,115].

    Divergem dos de A por construção — ver a nota de auditoria de
    :class:`ParabolicRecovery` e a Etapa 2 §9.2. Existe para que os casos
    legados do repositório continuem reprodutíveis por este kernel, não
    para reproduzir o Documento A.
    """

    u0_V: float = 690.0
    k_V_per_us: float = 17.0

    def __post_init__(self) -> None:
        for label, value in (("u0_V", self.u0_V), ("k_V_per_us", self.k_V_per_us)):
            v = float(value)
            if not math.isfinite(v):
                raise ValueError(f"{label} deve ser finito, obtido {value!r}")
            if v < 0.0:
                raise ValueError(f"{label} deve ser >= 0, obtido {value!r}")

    def withstand_V(self, elapsed_s: float) -> float:
        """``V_wth`` [V] após ``elapsed_s`` [s] da extinção do arco."""
        t_us = max(0.0, float(elapsed_s)) * 1.0e6
        return self.u0_V + self.k_V_per_us * t_us


# ---------------------------------------------------------------------------
# Resultado por polo
# ---------------------------------------------------------------------------


@dataclass
class VCBPoleResult:
    """Resultado auditável de um polo após a manobra.

    Attributes
    ----------
    name:
        Nome do polo (o da chave comandada).
    separation_time_s:
        Instante comandado de separação de contatos [s].
    chopping_current_A:
        Valor de ``I_ch`` efetivamente usado nesta realização [A]
        (determinístico ou amostrado).
    chopping_time_s:
        Instante do PRIMEIRO corte de corrente [s]; ``None`` se não
        houve corte na janela simulada.
    chopping_current_at_chop_A:
        Corrente instantânea no passo do primeiro corte [A].
    reignition_count:
        Número de reignições do polo — o ``n_r`` do vetor de estresse
        ``s_{m,j}`` (Etapa 1 §5.4, D7).
    reignition_times_s:
        Instantes das reignições [s], em ordem cronológica.
    reignition_voltages_V:
        Tensão através do *gap* no instante de cada reignição [V].
    reignition_withstand_V:
        Suportabilidade ``V_wth`` vencida em cada reignição [V].
    interruption_times_s:
        Instantes de todas as interrupções (o corte inicial e cada
        extinção de arco de alta frequência) [s].
    final_state:
        Estado do polo ao fim da simulação.
    """

    name: str = ""
    separation_time_s: float = 0.0
    chopping_current_A: float = 0.0
    chopping_time_s: float | None = None
    chopping_current_at_chop_A: float = 0.0
    reignition_count: int = 0
    reignition_times_s: list[float] = field(default_factory=list)
    reignition_voltages_V: list[float] = field(default_factory=list)
    reignition_withstand_V: list[float] = field(default_factory=list)
    interruption_times_s: list[float] = field(default_factory=list)
    final_state: str = STATE_CLOSED

    @property
    def cleared(self) -> bool:
        """``True`` se o polo terminou a janela com o *gap* aberto."""
        return self.final_state in (STATE_OPEN, STATE_CLEARED)

    @property
    def peak_reignition_voltage_V(self) -> float:
        """Maior |v_gap| entre as reignições [V]; 0,0 se não houve."""
        if not self.reignition_voltages_V:
            return 0.0
        return max(abs(v) for v in self.reignition_voltages_V)


# ---------------------------------------------------------------------------
# Modelo de polo
# ---------------------------------------------------------------------------


class VacuumCircuitBreakerModel:
    """Polo de disjuntor a vácuo comandando uma :class:`Switch` ideal.

    É um **controlador** no sentido do kernel: um chamável
    ``f(t, solver)`` passado em ``Solver.run(controllers=[...])``, e é
    invocado ANTES de cada passo, com ``t`` já resolvido e o estado do
    ramo já submetido (``commit``) no instante ``t``.

    Máquina de estados
    ------------------

    ``closed`` → (``t >= separation_time_s``) → ``arcing``
        Os contatos se separam mas o arco conduz; a chave permanece
        fechada e nada muda eletricamente. É o comportamento físico: a
        separação mecânica não interrompe a corrente.

    ``arcing`` → (``|i| <= I_ch``) → ``open``
        **Corte de corrente.** O arco a vácuo colapsa antes do zero
        natural. Como ``I_ch`` é de 1 A a 2 A contra um pico de centenas
        de ampères, a condição só é atendida na vizinhança do zero de
        corrente [FATO: doc A, p. 2, II-A]. Quando
        ``require_zero_crossing=True`` exige-se, além disso, que a
        corrente esteja de fato caminhando para o zero.

    ``open`` → (``|v_gap| > V_wth(t − t_corte)``) → ``arcing_hf``
        **Reignição.** A TRV vence a suportabilidade ainda em
        recuperação; a chave fecha e o contador incrementa.

    ``arcing_hf`` → (zero de corrente com ``di/dt`` conforme a convenção) → ``open``
        **Extinção do arco de alta frequência**, reiniciando a
        recuperação dielétrica a partir do novo instante de extinção.

    ``open``/``arcing_hf`` → ``cleared``
        Trava definitiva ao atingir ``max_reignitions``.

    Parameters
    ----------
    switch:
        Chave ideal do kernel que representa o polo. Deve começar
        FECHADA para que a manobra faça sentido; um aviso é registrado
        caso contrário.
    separation_time_s:
        Instante de separação dos contatos [s], >= 0.
    chopping_current_A:
        ``I_ch`` determinístico [A]. ``None`` (padrão) usa a faixa e a
        distribuição informadas.
    chopping_range_A:
        Faixa de ``I_ch`` [A]; padrão ``(1,0; 2,0)`` de A.
    chopping_distribution:
        ``"deterministic"`` (ponto médio da faixa, padrão quando
        ``seed is None``), ``"uniform"`` (padrão quando há semente) ou
        ``"normal"`` (média ``chopping_current_A``, desvio
        ``chopping_sigma_A``, truncada em > 0).
    chopping_sigma_A:
        Desvio-padrão de ``I_ch`` [A] na distribuição normal.
    seed:
        Semente EXPLÍCITA do Monte Carlo. ``None`` ⇒ realização
        determinística. Nunca há semente implícita: o kernel não usa
        entropia do sistema.
    recovery:
        Lei de recuperação dielétrica; padrão
        :class:`ParabolicRecovery` com os valores de A.
    didt_capability_A_per_us:
        Capacidade de extinção de corrente de alta frequência [A/µs];
        padrão 15,0 (extremo superior da faixa de A).
    didt_convention:
        :data:`DIDT_INTERRUPT_WITHIN` (padrão, físico) ou
        :data:`DIDT_INTERRUPT_ABOVE` (leitura literal do texto de A).
    require_zero_crossing:
        Exige que a corrente esteja decrescendo em módulo (ou que tenha
        trocado de sinal) para autorizar o corte. Padrão ``True``.
    max_reignitions:
        Teto de reignições antes de travar em ``cleared``.
    name:
        Rótulo do polo; padrão o nome da chave.

    Raises
    ------
    ValueError
        ``switch`` não é uma :class:`Switch`; tempo, corrente,
        capacidade ou distribuição inválidos.
    """

    def __init__(
        self,
        switch: Switch,
        *,
        separation_time_s: float,
        chopping_current_A: float | None = None,
        chopping_range_A: tuple[float, float] = DOC_A_CHOPPING_RANGE_A,
        chopping_distribution: str | None = None,
        chopping_sigma_A: float = 0.0,
        seed: int | None = None,
        recovery: DielectricRecovery | None = None,
        didt_capability_A_per_us: float = DOC_A_DIDT_RANGE_A_PER_US[1],
        didt_convention: str = DIDT_INTERRUPT_WITHIN,
        require_zero_crossing: bool = True,
        max_reignitions: int = DEFAULT_MAX_REIGNITIONS,
        name: str = "",
    ) -> None:
        if not isinstance(switch, Switch):
            raise ValueError(
                "VacuumCircuitBreakerModel comanda um componente Switch do "
                f"kernel, obtido {type(switch).__name__}"
            )
        t_sep = float(separation_time_s)
        if not math.isfinite(t_sep) or t_sep < 0.0:
            raise ValueError(
                f"separation_time_s deve ser finito e >= 0, obtido {separation_time_s!r}"
            )
        lo, hi = (float(chopping_range_A[0]), float(chopping_range_A[1]))
        if not (math.isfinite(lo) and math.isfinite(hi)):
            raise ValueError(f"chopping_range_A deve ser finita, obtida {chopping_range_A!r}")
        if lo <= 0.0 or hi < lo:
            raise ValueError(
                f"chopping_range_A deve satisfazer 0 < lo <= hi, obtida {chopping_range_A!r}"
            )
        didt = float(didt_capability_A_per_us)
        if not math.isfinite(didt) or didt <= 0.0:
            raise ValueError(
                f"didt_capability_A_per_us deve ser finito e > 0, obtido "
                f"{didt_capability_A_per_us!r}"
            )
        if str(didt_convention) not in DIDT_CONVENTIONS:
            raise ValueError(
                f"didt_convention deve ser um de {DIDT_CONVENTIONS}, "
                f"obtido {didt_convention!r}"
            )
        if int(max_reignitions) < 0:
            raise ValueError(f"max_reignitions deve ser >= 0, obtido {max_reignitions!r}")
        sigma = float(chopping_sigma_A)
        if not math.isfinite(sigma) or sigma < 0.0:
            raise ValueError(f"chopping_sigma_A deve ser finito e >= 0, obtido {chopping_sigma_A!r}")

        if chopping_distribution is None:
            distribution = "uniform" if seed is not None else "deterministic"
        else:
            distribution = str(chopping_distribution)
        if distribution not in CHOPPING_DISTRIBUTIONS:
            raise ValueError(
                f"chopping_distribution deve ser um de {CHOPPING_DISTRIBUTIONS}, "
                f"obtido {chopping_distribution!r}"
            )
        if distribution == "normal":
            if chopping_current_A is None:
                raise ValueError(
                    "a distribuição 'normal' exige chopping_current_A como média"
                )
            if sigma <= 0.0:
                raise ValueError("a distribuição 'normal' exige chopping_sigma_A > 0")
            if seed is None:
                raise ValueError(
                    "a distribuição 'normal' exige semente explícita (seed); "
                    "o kernel nunca usa entropia implícita do sistema"
                )
        if distribution == "uniform" and seed is None:
            raise ValueError(
                "a distribuição 'uniform' exige semente explícita (seed); "
                "use chopping_distribution='deterministic' para o ponto médio"
            )
        if chopping_current_A is not None:
            i_ch = float(chopping_current_A)
            if not math.isfinite(i_ch) or i_ch <= 0.0:
                raise ValueError(
                    f"chopping_current_A deve ser finito e > 0, obtido {chopping_current_A!r}"
                )

        if not switch.closed:
            log.warning(
                "polo %r criado com a chave ABERTA: não há corrente para cortar "
                "e o modelo permanecerá em %r",
                name or switch.name,
                STATE_OPEN,
            )

        self.switch = switch
        self.name = str(name) if name else str(switch.name)
        self.separation_time_s = t_sep
        self.chopping_range_A = (lo, hi)
        self.chopping_distribution = distribution
        self.chopping_sigma_A = sigma
        self.seed = None if seed is None else int(seed)
        self._chopping_setpoint_A = None if chopping_current_A is None else float(chopping_current_A)
        self.recovery: DielectricRecovery = recovery if recovery is not None else ParabolicRecovery()
        self.didt_capability_A_per_us = didt
        self.didt_convention = str(didt_convention)
        self.require_zero_crossing = bool(require_zero_crossing)
        self.max_reignitions = int(max_reignitions)
        self._initially_closed = bool(switch.closed)

        # Estado dinâmico.
        self._state: str = STATE_CLOSED
        self._i_prev: float = 0.0
        self._t_prev: float = -1.0
        self._t_extinction: float | None = None
        self._arc_established: bool = False
        self._last_didt_A_per_us: float = 0.0
        self._i_ch_A: float = 0.0
        self._result = VCBPoleResult(name=self.name, separation_time_s=t_sep)
        self._locked_warned = False
        self.reset()

    # -- amostragem ---------------------------------------------------------

    def _sample_chopping_current(self) -> float:
        """Amostra ``I_ch`` [A] conforme a distribuição declarada.

        [HIPÓTESE] O Documento A informa apenas a FAIXA 1 A a 2 A
        [FATO: doc A, Tabela II, p. 3]; nenhuma distribuição é declarada
        [FATO por omissão]. Adota-se a uniforme por ser a de máxima
        entropia dado o suporte — escolha do módulo, não do artigo.
        """
        lo, hi = self.chopping_range_A
        if self.chopping_distribution == "deterministic":
            if self._chopping_setpoint_A is not None:
                return self._chopping_setpoint_A
            return 0.5 * (lo + hi)
        rng = np.random.default_rng(self.seed)
        if self.chopping_distribution == "uniform":
            return float(rng.uniform(lo, hi))
        # normal truncada em > 0 — convenção do .mod legado.
        mean = float(self._chopping_setpoint_A or 0.0)
        for _ in range(64):
            value = float(rng.normal(mean, self.chopping_sigma_A))
            if value > 0.0:
                return value
        log.warning(
            "amostragem normal de I_ch em %r não produziu valor positivo em 64 "
            "tentativas (média %.3g A, sigma %.3g A); usando a média",
            self.name,
            mean,
            self.chopping_sigma_A,
        )
        return abs(mean) or lo

    # -- ciclo de vida ------------------------------------------------------

    def reset(self) -> None:
        """Reinicia a máquina de estados e reamostra ``I_ch``.

        ``Solver.run(reset=True)`` NÃO alcança controladores — eles não
        pertencem ao circuito. Este método é chamado automaticamente
        quando o controlador detecta que o tempo retrocedeu (nova
        execução), e pode ser chamado explicitamente entre realizações
        do Monte Carlo.
        """
        self.switch.set_state(self._initially_closed)
        self._state = STATE_CLOSED
        self._i_prev = 0.0
        self._t_prev = -1.0
        self._t_extinction = None
        self._arc_established = False
        self._last_didt_A_per_us = 0.0
        self._i_ch_A = self._sample_chopping_current()
        # O I_ch amostrado É o campo Imar do cartão de chave do ATP nesta
        # realização: publica-se na própria chave para que o cartão fique
        # autodescritivo e o critério possa ser lido por quem inspecionar
        # o circuito [LISTA: 02, §1.3 e §3.6].
        self.switch.current_margin_A = self._i_ch_A
        self._locked_warned = False
        self._result = VCBPoleResult(
            name=self.name,
            separation_time_s=self.separation_time_s,
            chopping_current_A=self._i_ch_A,
        )

    # -- leitura ------------------------------------------------------------

    @property
    def state(self) -> str:
        """Estado corrente da máquina (um de :data:`VCB_STATES`)."""
        return self._state

    @property
    def result(self) -> VCBPoleResult:
        """Resultado acumulado do polo."""
        self._result.final_state = self._state
        return self._result

    @property
    def reignition_count(self) -> int:
        """Contador de reignições do polo — o ``n_r`` de ``s_{m,j}``."""
        return self._result.reignition_count

    @property
    def sampled_chopping_current_A(self) -> float:
        """``I_ch`` desta realização [A]."""
        return self._i_ch_A

    @property
    def current_margin_A(self) -> float:
        """``I_mar`` em vigor [A] — o campo *current margin* do ATP.

        É o MESMO número de :attr:`sampled_chopping_current_A`, exposto
        com o nome do campo do cartão de chave do ATP (colunas 35-44)
        porque é essa a função que ele exerce: a abertura comandada em
        ``separation_time_s`` só se efetiva no primeiro instante em que
        ``|i| <= I_mar`` [LISTA: 02, §1.3 e §3.6]. A diferença em relação
        a um cartão de ATP é que aqui o limiar é AMOSTRADO da faixa de
        *chopping* do Documento A a cada realização, em vez de fixo.
        """
        return self._i_ch_A

    @property
    def last_didt_A_per_us(self) -> float:
        """``|di/dt|`` medido no último cruzamento por zero de alta frequência [A/µs]."""
        return self._last_didt_A_per_us

    @property
    def arc_established(self) -> bool:
        """``True`` quando o arco corrente já completou um passo de condução."""
        return self._arc_established

    @property
    def chopping_time_s(self) -> float | None:
        """Instante do primeiro corte de corrente [s], ou ``None``."""
        return self._result.chopping_time_s

    def withstand_V(self, t: float) -> float:
        """Suportabilidade do *gap* [V] no instante ``t``.

        Vale 0,0 enquanto houver arco (estado de condução): um *gap* em
        arco não suporta tensão.
        """
        if self._t_extinction is None or self._state in (
            STATE_CLOSED,
            STATE_ARCING,
            STATE_ARCING_HF,
        ):
            return 0.0
        return float(self.recovery.withstand_V(t - self._t_extinction))

    # -- controlador --------------------------------------------------------

    def __call__(self, t: float, solver) -> None:
        """Avalia a máquina de estados no instante ``t`` [s]."""
        t_f = float(t)
        # Nova execução do solver (t retrocedeu): reinicia a realização.
        if self._t_prev >= 0.0 and t_f < self._t_prev:
            self.reset()

        i_now = float(self.switch.branch_current(0))
        v_gap = float(self.switch.branch_voltage(0))
        dt = t_f - self._t_prev if self._t_prev >= 0.0 else float(getattr(solver, "dt", 0.0))

        if self._state == STATE_CLOSED:
            if t_f >= self.separation_time_s:
                self._state = STATE_ARCING
                self._arc_established = True
        if self._state == STATE_ARCING:
            self._evaluate_power_frequency_arc(t_f, i_now)
        elif self._state == STATE_ARCING_HF:
            self._evaluate_high_frequency_arc(t_f, i_now, dt)
        elif self._state == STATE_OPEN:
            self._evaluate_dielectric_recovery(t_f, v_gap)

        self._i_prev = i_now
        self._t_prev = t_f

    # -- transições ---------------------------------------------------------

    def _evaluate_power_frequency_arc(self, t: float, i_now: float) -> None:
        """Corte de corrente do arco de frequência industrial.

        O critério ``|i| <= I_ch`` é o mesmo do campo *current margin*
        (``Imar``, colunas 35-44) do cartão de chave do ATP e o da
        Seção 5 das notas de aula: "a abertura comandada em ``t0`` só se
        efetiva a partir do primeiro instante ``t >= t0`` em que a
        corrente na chave se anula ou cai abaixo de um limiar
        ``|Imar|``" [LISTA: 02, §1.3]. Aqui ``I_mar`` é a corrente de
        *chopping* amostrada da faixa do Documento A, em vez de um valor
        fixo de cartão. Validação do critério contra o ATP no circuito de
        referência: os dois programas cortam a corrente no MESMO passo,
        ``t_c = 32,361 ms`` [LISTA: 02, §3.7 e Tabela 3].

        O corte só é avaliado a partir do segundo passo de condução do
        arco corrente (guarda ``_arc_established``): no passo da ignição,
        ``i(t−Δt)`` ainda é a amostra do estado ANTERIOR e qualquer teste
        de decaimento ou de cruzamento por zero seria espúrio. O
        *chopping* é o colapso de um arco EXISTENTE cuja corrente decai
        abaixo do nível de instabilidade, não do arco que acaba de nascer.
        """
        if not self._arc_established:
            self._arc_established = True
            return
        if abs(i_now) > self._i_ch_A:
            return
        if self.require_zero_crossing and not self._heading_to_zero(i_now):
            return
        self._interrupt(t, i_now, first_chop=True)

    def _evaluate_high_frequency_arc(self, t: float, i_now: float, dt: float) -> None:
        """Extinção do arco de alta frequência no zero de corrente.

        O critério é o do Documento A: a corrente de alta frequência é
        interrompida no cruzamento por zero conforme o ``di/dt`` naquele
        instante [FATO: doc A, p. 3, IV-B]. A mesma guarda de arco
        estabelecido se aplica — no passo da reignição ``i(t−Δt)`` é a
        amostra do gap ABERTO (nula) e o teste de cruzamento seria
        espúrio.

        Este é o mecanismo que produz a ESCALADA: enquanto o ``di/dt`` no
        zero exceder a capacidade de extinção, o arco persiste, a
        capacitância do lado da carga é recarregada, e a interrupção
        seguinte parte de uma tensão presa maior.
        """
        if not self._arc_established:
            self._arc_established = True
            return
        crossed = (self._i_prev * i_now < 0.0) or (i_now == 0.0 and self._i_prev != 0.0)
        if not crossed:
            return
        didt_A_per_us = 0.0
        if dt > 0.0:
            didt_A_per_us = abs(i_now - self._i_prev) / dt * 1.0e-6
        self._last_didt_A_per_us = didt_A_per_us
        capable = didt_A_per_us <= self.didt_capability_A_per_us
        if self.didt_convention == DIDT_INTERRUPT_ABOVE:
            capable = not capable
        if capable:
            self._interrupt(t, i_now, first_chop=False)

    def _evaluate_dielectric_recovery(self, t: float, v_gap: float) -> None:
        """Reignição quando a TRV vence a suportabilidade instantânea."""
        if self._result.reignition_count >= self.max_reignitions:
            if not self._locked_warned:
                self._locked_warned = True
                log.warning(
                    "polo %r atingiu o teto de %d reignições em t = %.6g s; "
                    "travado em %r — o resultado NÃO é a interrupção física, "
                    "é a salvaguarda numérica do modelo",
                    self.name,
                    self.max_reignitions,
                    t,
                    STATE_CLEARED,
                )
            self._state = STATE_CLEARED
            return
        assert self._t_extinction is not None
        v_wth = float(self.recovery.withstand_V(t - self._t_extinction))
        if abs(v_gap) > v_wth:
            self.switch.close()
            self._state = STATE_ARCING_HF
            self._arc_established = False
            self._result.reignition_count += 1
            self._result.reignition_times_s.append(t)
            self._result.reignition_voltages_V.append(v_gap)
            self._result.reignition_withstand_V.append(v_wth)

    def _interrupt(self, t: float, i_now: float, *, first_chop: bool) -> None:
        """Abre a chave e inicia (ou reinicia) a recuperação dielétrica."""
        self.switch.open()
        self._state = STATE_OPEN
        self._arc_established = False
        self._t_extinction = t
        self._result.interruption_times_s.append(t)
        if first_chop and self._result.chopping_time_s is None:
            self._result.chopping_time_s = t
            self._result.chopping_current_at_chop_A = i_now

    def _heading_to_zero(self, i_now: float) -> bool:
        """``True`` se a corrente decresce em módulo ou trocou de sinal."""
        if self._t_prev < 0.0:
            return False
        if self._i_prev * i_now < 0.0:
            return True
        return abs(i_now) <= abs(self._i_prev)


# ---------------------------------------------------------------------------
# Adaptador de compatibilidade com o MODEL legado do repositório
# ---------------------------------------------------------------------------


def vcb_from_mod_parameters(
    switch: Switch,
    *,
    t_open: float = 0.05,
    i_chop_mean: float = 5.0,
    i_chop_sigma: float = 1.0,
    didt_crit_0: float = 16.0,
    k_dielec: float = 17.0,
    u0_dielec: float = 690.0,
    seed: int | None = 1,
    name: str = "",
    **kwargs,
) -> VacuumCircuitBreakerModel:
    """Constrói um polo com os parâmetros de ``vcb_reignition.mod``.

    Adaptador de **compatibilidade**: reproduz, sobre este kernel, a
    parametrização dos casos legados do repositório
    [REPO: app/preprocessor/atp_templates/vcb_reignition.mod:47-56], a
    saber ``I_chop_mean = 5,0 A``, ``I_chop_sigma = 1,0 A``,
    ``didt_crit_0 = 16 A/µs``, ``k_dielec = 17 V/µs``,
    ``U0_dielec = 690 V`` e ``T_open = 0,05 s``.

    Diferenças assumidas e declaradas
    ---------------------------------
    1. A recuperação é LINEAR (:class:`LinearRecovery`), não parabólica —
       é a lei do ``.mod`` [REPO: ``.mod``:115].
    2. A convenção de ``di/dt`` **permanece** a física
       (:data:`DIDT_INTERRUPT_WITHIN`) por padrão, e NÃO a do ``.mod``
       (que reignita acima do crítico, ``.mod``:98-101). Passe
       ``didt_convention=DIDT_INTERRUPT_ABOVE`` para reproduzir também
       essa convenção. A escolha é explícita porque a Etapa 2 §9.2
       registra que o sinal do efeito sobre ``n_r`` se inverte com ela.
    3. ``T_bounce`` (rebote mecânico) do ``.mod`` **não** é reproduzido:
       o bloco correspondente do MODEL é inerte (``.mod``:124-128, corpo
       vazio), de modo que não há comportamento a reproduzir
       [REPO: verificado no arquivo].
    4. ``didt_sigma`` (endurecimento ``di/dt_crit(t)``) do ``.mod`` não é
       reproduzido: a capacidade aqui é constante. Efeito declarado como
       limitação ``emt_vcb_constant_didt_capability``.

    Parameters
    ----------
    switch:
        Chave do kernel que representa o polo.
    t_open, i_chop_mean, i_chop_sigma, didt_crit_0, k_dielec, u0_dielec, seed:
        Homônimos do bloco ``DATA`` do ``.mod``, nas mesmas unidades.
    name:
        Rótulo do polo.
    **kwargs:
        Repassados a :class:`VacuumCircuitBreakerModel` (por exemplo
        ``didt_convention``), permitindo sobrepor qualquer padrão.

    Returns
    -------
    VacuumCircuitBreakerModel
        Polo parametrizado como o MODEL legado.
    """
    params: dict = {
        "separation_time_s": float(t_open),
        "chopping_current_A": float(i_chop_mean),
        "chopping_sigma_A": float(i_chop_sigma),
        "chopping_distribution": "normal" if seed is not None else "deterministic",
        "seed": seed,
        "recovery": LinearRecovery(u0_V=float(u0_dielec), k_V_per_us=float(k_dielec)),
        "didt_capability_A_per_us": float(didt_crit_0),
        "name": name,
    }
    # A faixa só é usada nas distribuições que a consultam; mantém-se
    # coerente com a média do .mod para não invalidar a validação de 0 < lo <= hi.
    params.setdefault("chopping_range_A", (max(1.0e-3, float(i_chop_mean) - 3.0 * float(i_chop_sigma)),
                                           float(i_chop_mean) + 3.0 * float(i_chop_sigma)))
    params.update(kwargs)
    return VacuumCircuitBreakerModel(switch, **params)


# ---------------------------------------------------------------------------
# Montagem trifásica com escalonamento (stagger) de polos
# ---------------------------------------------------------------------------


def stagger_times(
    n_poles: int = 3,
    *,
    span_s: tuple[float, float] = DOC_A_STAGGER_RANGE_S,
) -> tuple[float, ...]:
    """Instantes de separação igualmente espaçados dentro de ``span_s``.

    Com ``n_poles = 3`` e o padrão de A devolve ``(14,0; 19,5; 25,0) ms``
    [FATO: doc A, Tabela II, p. 3, "Contact separation stagger 14 ms to
    25 ms"; a distribuição UNIFORME dentro da faixa é
    [HIPÓTESE] deste módulo — A não a declara].

    Raises
    ------
    ValueError
        ``n_poles < 1`` ou faixa inválida.
    """
    n = int(n_poles)
    if n < 1:
        raise ValueError(f"n_poles deve ser >= 1, obtido {n_poles!r}")
    lo, hi = float(span_s[0]), float(span_s[1])
    if not (math.isfinite(lo) and math.isfinite(hi)):
        raise ValueError(f"span_s deve ser finita, obtida {span_s!r}")
    if lo < 0.0 or hi < lo:
        raise ValueError(f"span_s deve satisfazer 0 <= lo <= hi, obtida {span_s!r}")
    if n == 1:
        return (lo,)
    step = (hi - lo) / float(n - 1)
    return tuple(lo + step * k for k in range(n))


def three_phase_vcb(
    switches: Sequence[Switch],
    *,
    stagger_s: Sequence[float] | None = None,
    seeds: Sequence[int | None] | None = None,
    **kwargs,
) -> tuple[VacuumCircuitBreakerModel, ...]:
    """Cria um polo por fase, com escalonamento dos instantes de separação.

    Parameters
    ----------
    switches:
        Chaves das fases, na ordem A, B, C.
    stagger_s:
        Instantes de separação por polo [s]. ``None`` (padrão) usa
        :func:`stagger_times` com a faixa de A.
    seeds:
        Sementes por polo (Monte Carlo independente por fase).
        ``None`` (padrão) replica a semente de ``kwargs`` em todos.
    **kwargs:
        Repassados a :class:`VacuumCircuitBreakerModel`.

    Returns
    -------
    tuple[VacuumCircuitBreakerModel, ...]
        Um modelo por chave, na mesma ordem.

    Raises
    ------
    ValueError
        Comprimentos incompatíveis entre ``switches``, ``stagger_s`` e
        ``seeds``.
    """
    sws = tuple(switches)
    if not sws:
        raise ValueError("three_phase_vcb exige pelo menos uma chave")
    times = tuple(stagger_s) if stagger_s is not None else stagger_times(len(sws))
    if len(times) != len(sws):
        raise ValueError(
            f"stagger_s tem {len(times)} instantes para {len(sws)} chaves"
        )
    if seeds is not None and len(tuple(seeds)) != len(sws):
        raise ValueError(f"seeds tem {len(tuple(seeds))} entradas para {len(sws)} chaves")
    seed_list = tuple(seeds) if seeds is not None else (kwargs.pop("seed", None),) * len(sws)
    kwargs.pop("seed", None)
    poles: list[VacuumCircuitBreakerModel] = []
    for sw, t_sep, seed in zip(sws, times, seed_list):
        poles.append(
            VacuumCircuitBreakerModel(
                sw, separation_time_s=float(t_sep), seed=seed, **kwargs
            )
        )
    return tuple(poles)


# ---------------------------------------------------------------------------
# Limitações declaradas do módulo — padrão do projeto
# (cf. app/postprocessor/audit_trail.py:338 e
# app/postprocessor/prognosis/__init__.py:168). Prefixo ``emt_`` para não
# colidir no catálogo global do laudo.
# ---------------------------------------------------------------------------

KNOWN_LIMITATIONS: dict[str, str] = {
    "emt_vcb_no_arc_voltage": (
        "O arco a vácuo é representado por uma chave IDEAL comandada: "
        "durante a condução a queda de tensão no arco é ZERO e não há "
        "resistência de arco dependente da corrente (Cassie/Mayr). A energia "
        "efetivamente dissipada no arco não é calculada, e a corrente "
        "conduzida durante o arco é a da rede sem a limitação que a tensão de "
        "arco (tipicamente 20 a 200 V em vácuo) imporia. O efeito sobre a TRV "
        "é de segunda ordem contra os quilovolts do transitório, mas o "
        "balanço energético do polo NÃO fecha."
    ),
    "emt_vcb_didt_convention_ambiguous": (
        "A convenção do critério de di/dt na extinção do arco de alta "
        "frequência é AMBÍGUA na fonte primária: o texto do Documento A "
        "(p. 3, IV-B) descreve interrupção ACIMA do valor crítico, enquanto a "
        "Tabela II do mesmo artigo nomeia o parâmetro 'Critical reignition "
        "di/dt' — convenção oposta, adotada pelo MODEL legado do repositório. "
        "Este módulo adota por padrão a convenção FÍSICA (interrompe quando "
        "|di/dt| <= capacidade), consistente com Wong (2003) e Abdulahovic "
        "(2017); a convenção invertida está disponível por flag. O sinal do "
        "efeito deste parâmetro sobre n_r é, portanto, INDETERMINADO enquanto "
        "a fonte não for esclarecida — e n_r entra no vetor de estresse."
    ),
    "emt_vcb_constant_didt_capability": (
        "A capacidade de extinção de alta frequência é CONSTANTE ao longo da "
        "manobra. Não há endurecimento da câmara com a distância entre "
        "contatos — o termo didt_sigma·(t − t_open) do MODEL legado — nem "
        "dependência da corrente de arco anterior. Sequências longas de "
        "reignição têm, por isso, a extinção final governada só pela "
        "recuperação dielétrica."
    ),
    "emt_vcb_chopping_distribution_assumed": (
        "O Documento A informa apenas a FAIXA de I_ch (1 A a 2 A) e nenhuma "
        "distribuição. A distribuição UNIFORME sobre a faixa é hipótese deste "
        "módulo (máxima entropia dado o suporte), não do artigo. A "
        "sensibilidade é quadrática: a energia magnética capturada no corte é "
        "½·L·I_ch², de modo que a razão entre os extremos da faixa vale 4×."
    ),
    "emt_vcb_chop_quantized_to_step": (
        "O corte ocorre no primeiro passo em que |i| <= I_ch, sem "
        "interpolação para o instante exato do cruzamento por zero. Com o "
        "passo de 1 µs do Documento A e uma corrente de partida de 1349 A de "
        "pico a 60 Hz, a corrente varia cerca de 0,51 A por passo na "
        "vizinhança do zero [CÁLCULO PRÓPRIO: 2πf·Î·Δt], de modo que o I_ch "
        "efetivo pode exceder o nominal em até esse valor — significativo "
        "contra um I_ch de 1 A a 2 A. Reduza Δt ao estudar a sensibilidade a "
        "I_ch."
    ),
    "emt_vcb_stagger_interpretation": (
        "O Documento A declara 'contact separation stagger 14 ms to 25 ms' sem "
        "dizer se a faixa descreve os instantes ABSOLUTOS de separação ou a "
        "DIFERENÇA entre polos. Este módulo adota instantes absolutos "
        "igualmente espaçados na faixa, única leitura compatível com a janela "
        "de 45 ms. A leitura alternativa mudaria por completo qual fase corta "
        "primeiro e, com ela, a atribuição por fase da Tabela III."
    ),
    "emt_vcb_zero_initial_withstand": (
        "A lei V_wth(t) = A·t + B·t² vale ZERO em t = 0. Com as constantes "
        "publicadas no Documento A (A = 0,801 kV/ms), o gap suporta apenas "
        "0,801 V um passo de 1 µs após o corte, enquanto a TRV de um corte "
        "indutivo sobe a centenas de kV/ms: a reignição ocorre SEMPRE no "
        "primeiro passo, e a tensão de reignição fica determinada pelo passo "
        "de integração, não pela física. Além disso o termo parabólico é "
        "desprezível na escala de µs — em t = 1 µs, B·t² = 1,23 mV contra "
        "A·t = 0,801 V — e só iguala o termo linear em t = A/B = 0,653 ms "
        "[CÁLCULO PRÓPRIO]. Consequência de método: nessa faixa de "
        "parâmetros a contagem n_r e a escalada de tensão DEPENDEM de Δt; "
        "declare o passo usado e verifique a convergência antes de usar n_r "
        "no vetor de estresse."
    ),
    "emt_vcb_single_gap_per_pole": (
        "Cada polo é UM gap. Câmaras em série, capacitâncias de equalização e "
        "a distribuição de tensão entre gaps não são representadas, o que "
        "restringe o modelo à classe de tensão de gap único — o caso de 4,16 kV "
        "do Documento A."
    ),
}


__all__ = [
    # constantes do Documento A
    "DOC_A_RRDS_A_KV_PER_MS",
    "DOC_A_RRDS_B_KV_PER_MS2",
    "DOC_A_CHOPPING_RANGE_A",
    "DOC_A_DIDT_RANGE_A_PER_US",
    "DOC_A_STAGGER_RANGE_S",
    "DOC_A_TIME_STEP_S",
    "DOC_A_WINDOW_S",
    # convenções e estados
    "DIDT_INTERRUPT_WITHIN",
    "DIDT_INTERRUPT_ABOVE",
    "DIDT_CONVENTIONS",
    "STATE_CLOSED",
    "STATE_ARCING",
    "STATE_ARCING_HF",
    "STATE_OPEN",
    "STATE_CLEARED",
    "VCB_STATES",
    "CHOPPING_DISTRIBUTIONS",
    "DEFAULT_MAX_REIGNITIONS",
    # leis de recuperação
    "DielectricRecovery",
    "ParabolicRecovery",
    "LinearRecovery",
    # modelo
    "VCBPoleResult",
    "VacuumCircuitBreakerModel",
    "vcb_from_mod_parameters",
    "stagger_times",
    "three_phase_vcb",
    # auditoria
    "KNOWN_LIMITATIONS",
]
