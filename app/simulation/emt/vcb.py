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
from app.simulation.emt.components import Capacitor, Inductor, Resistor, Switch

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

#: Instante a partir do qual a suportabilidade do *gap* cresce.
#:
#: ``RECOVERY_FROM_SEPARATION`` — a partir da SEPARAÇÃO DOS CONTATOS. É a
#: referência da literatura primária: ``U = A(t − t_open) + B``, com
#: ``t_open`` o instante de separação [LITERATURA: Wong, Snider e Lo,
#: IPST 2003, modelo estocástico sobre 48 disjuntores]. A razão é
#: física: quem sustenta a tensão é a DISTÂNCIA entre os contatos, que
#: cresce monotonicamente enquanto eles se afastam, e não é reposta a
#: zero a cada extinção de arco.
#:
#: ``RECOVERY_FROM_EXTINCTION`` — a partir de cada extinção de arco.
#: Reinicia o relógio a cada interrupção, de modo que o *gap* nunca
#: acumula rigidez: uma vez iniciada a sequência, o polo reignite a cada
#: meio ciclo indefinidamente e a manobra nunca se completa
#: [CÁLCULO PRÓPRIO: medição — reignições espaçadas de 8,33 ms a 60 Hz,
#: chave fechada ao fim da janela em 100 % das realizações]. Preservado
#: para reprodutibilidade de casos legados, não para uso físico.
RECOVERY_FROM_SEPARATION: str = "separation"
RECOVERY_FROM_EXTINCTION: str = "extinction"
RECOVERY_REFERENCES: tuple[str, ...] = (
    RECOVERY_FROM_SEPARATION,
    RECOVERY_FROM_EXTINCTION,
)


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
        recovery_reference: str = RECOVERY_FROM_SEPARATION,
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
        if str(recovery_reference) not in RECOVERY_REFERENCES:
            raise ValueError(
                f"recovery_reference deve ser um de {RECOVERY_REFERENCES}, "
                f"obtido {recovery_reference!r}"
            )
        self.recovery_reference = str(recovery_reference)
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
        return float(self.recovery.withstand_V(t - self._recovery_origin()))

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
        v_wth = float(self.recovery.withstand_V(t - self._recovery_origin()))
        if abs(v_gap) > v_wth:
            self.switch.close()
            self._state = STATE_ARCING_HF
            self._arc_established = False
            self._result.reignition_count += 1
            self._result.reignition_times_s.append(t)
            self._result.reignition_voltages_V.append(v_gap)
            self._result.reignition_withstand_V.append(v_wth)

    def _recovery_origin(self) -> float:
        """Instante de origem do relógio da recuperação dielétrica [s].

        Na referência física (padrão) é a SEPARAÇÃO DOS CONTATOS: a
        rigidez do *gap* acompanha a distância entre contatos, que cresce
        enquanto eles se afastam e não volta a zero quando o arco se
        extingue [LITERATURA: Wong, Snider e Lo, IPST 2003,
        ``U = A(t − t_open) + B``].
        """
        if self.recovery_reference == RECOVERY_FROM_SEPARATION:
            return self.separation_time_s
        assert self._t_extinction is not None
        return self._t_extinction

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
# Modo de compatibilidade LITERAL com o MODEL VCB_R*/S*/T* do arquivo ATP
# ---------------------------------------------------------------------------
#
# Tudo o que segue reproduz, LINHA A LINHA, o bloco ``EXEC`` do MODEL
# ``VCB_Rr`` de [REPO: tests/fixtures/atp/trt_all_motors_dt_ea.atp:110-199],
# com os dados do bloco ``USE`` correspondente (linhas 526-604 do mesmo
# arquivo). É um modo OPCIONAL, selecionado por parâmetro
# (``atp_model_compatibility=True`` em :func:`build_vcb_pole`, ou o uso
# direto de :class:`AtpModelCompatibility`): o comportamento padrão de
# :class:`VacuumCircuitBreakerModel` NÃO é alterado por nada desta seção.
#
# A razão de existir do modo é metodológica: o caso de referência é o
# ARQUIVO, não a idealização física dele. Onde a lógica escrita difere da
# lógica que se esperaria de um disjuntor a vácuo, o modo literal segue o
# arquivo e a divergência é declarada — em docstring e em
# :data:`KNOWN_LIMITATIONS` — em vez de ser silenciosamente corrigida.


#: Instantes de separação de contatos por polo [s]
#: [FATO: arquivo, ``T_OPENr/s/t`` no bloco USE].
ATP_T_OPEN_S: tuple[float, float, float] = (0.01455, 0.02475, 0.02481)

#: Corrente de corte por polo [A] — valores FIXOS e distintos por polo,
#: não faixa de amostragem [FATO: arquivo, ``I_CHOPr/s/t``].
ATP_I_CHOP_A: tuple[float, float, float] = (1.0, 2.0, 2.0)

#: Capacidade de extinção de alta frequência por polo [A/µs]
#: [FATO: arquivo, ``DIDT_CRITr/s/t``].
ATP_DIDT_CRIT_A_PER_US: tuple[float, float, float] = (5.0, 15.0, 15.0)

#: Constantes da lei de recuperação dielétrica, iguais nos três polos
#: [FATO: arquivo, ``RRDS_Ar/s/t`` e ``RRDS_Br/s/t``].
ATP_RRDS_A_KV_PER_MS: float = 0.801
ATP_RRDS_B_KV_PER_MS2: float = 1.226

#: Margem do critério de reignição: o MODEL escreve
#: ``IF ABS(V_CBr) > V_WITHr * 1.1`` [FATO: arquivo, MODEL VCB_Rr].
ATP_REIGNITION_MARGIN: float = 1.1

#: Limiar que VALIDA a passagem por zero da corrente: só reinicia o
#: temporizador da recuperação se ``ABS(I_PREV) > 0.01``
#: [FATO: arquivo, MODEL VCB_Rr].
ATP_ZERO_CROSSING_THRESHOLD_A: float = 0.01

#: Segunda condição de extinção: ``ABS(I_CB) < 0.1 AND T_ZERO >= 0``
#: [FATO: arquivo, MODEL VCB_Rr, estados 1 e 3].
ATP_EXTINCTION_CURRENT_A: float = 0.1

#: Resistências do ramo série comutado [Ω] [FATO: arquivo, ``RCLOSED``,
#: ``RARC`` e ``ROPEN`` do bloco USE].
ATP_R_CLOSED_OHM: float = 0.001
ATP_R_ARC_OHM: float = 20.0
ATP_R_OPEN_OHM: float = 1.0e6

#: Indutâncias do ramo série comutado [H] [FATO: arquivo, ``LCLOSED``,
#: ``LARC`` e ``LOPEN``; ver ``emt_vcb_atp_lc_unit_convention``].
ATP_L_CLOSED_H: float = 2.0e-3
ATP_L_ARC_H: float = 50.0e-6
ATP_L_OPEN_H: float = 0.6e-6

#: Capacitâncias do ramo série comutado [F] [FATO: arquivo, ``CCLOSED``,
#: ``CARC`` e ``COPEN``; ver ``emt_vcb_atp_lc_unit_convention``].
ATP_C_CLOSED_F: float = 0.0
ATP_C_ARC_F: float = 20.0e-9
ATP_C_OPEN_F: float = 6.0e-6

#: Estados do MODEL, com os MESMOS códigos inteiros do arquivo. Note que
#: a numeração NÃO é a de :data:`VCB_STATES`: aqui 2 é o gap aberto e 3 é
#: o arco de alta frequência.
ATP_CB_CLOSED: int = 0
ATP_CB_ARCING: int = 1
ATP_CB_OPEN: int = 2
ATP_CB_ARCING_HF: int = 3

#: Estados do MODEL, na ordem dos códigos.
ATP_CB_STATES: tuple[int, int, int, int] = (
    ATP_CB_CLOSED,
    ATP_CB_ARCING,
    ATP_CB_OPEN,
    ATP_CB_ARCING_HF,
)

#: Nomes dos estados do MODEL, para leitura humana.
ATP_CB_STATE_NAMES: dict[int, str] = {
    ATP_CB_CLOSED: "fechado",
    ATP_CB_ARCING: "arco",
    ATP_CB_OPEN: "aberto",
    ATP_CB_ARCING_HF: "arco_alta_frequencia",
}

#: Ordem de atualização de ``I_PREV`` EXATAMENTE como escrita no arquivo:
#: ``I_PREV := I_CBr`` ocorre DENTRO do bloco ``IF TNOW > TIME_PREVr``,
#: isto é, ANTES do teste de passagem por zero ``IF I_PREV * I_CBr <= 0``.
#: Como ``TNOW > TIME_PREVr`` é verdadeiro em todo passo, o teste compara
#: a corrente com ELA MESMA e ``T_ZEROr`` nunca é atribuído — o
#: temporizador da recuperação dielétrica nunca parte, ``V_WITHr``
#: permanece nulo e nenhuma reignição é declarada. Ver
#: ``emt_vcb_atp_iprev_overwritten_before_zero_test``.
ATP_ZERO_ORDER_LITERAL: str = "literal"

#: Ordem em que ``I_PREV`` é atualizado DEPOIS do teste de passagem por
#: zero, de modo que o teste compare amostras CONSECUTIVAS. É a leitura
#: que dá sentido ao limiar de 0,01 A e ao reinício do temporizador; é
#: [INFERÊNCIA FÍSICA] sobre a intenção do autor do MODEL, não o que o
#: arquivo executa.
ATP_ZERO_ORDER_DEFERRED: str = "deferred"

#: Ordens aceitas.
ATP_ZERO_ORDERS: tuple[str, str] = (ATP_ZERO_ORDER_LITERAL, ATP_ZERO_ORDER_DEFERRED)

#: ``I_CBr`` lido da CHAVE IDEAL, como no arquivo: a entrada do MODEL vem
#: do par de chaves ``MEASURING`` que está em série com a chave tipo 13, e
#: NÃO com o ramo R-L-C paralelo [FATO: arquivo, cartões
#: ``X0001AXX0027 MEASURING`` / ``XX0027XX0022 MEASURING`` e
#: ``13XX0022X0002A``].
ATP_CURRENT_FROM_SWITCH: str = "switch"

#: ``I_CBr`` lido do POLO INTEIRO (chave ideal + ramo R-L-C em paralelo).
#: Não é o que o arquivo faz; existe para quantificar o efeito da escolha.
ATP_CURRENT_FROM_POLE: str = "pole"

#: Fontes de corrente aceitas.
ATP_CURRENT_SOURCES: tuple[str, str] = (ATP_CURRENT_FROM_SWITCH, ATP_CURRENT_FROM_POLE)


# -- elementos R, L e C de valor comutável ---------------------------------


class SwitchedResistor(Resistor):
    """Resistor cujo valor é comutado por um controlador durante a marcha.

    É o equivalente do cartão tipo 91 com ``TACS CONTROL`` do arquivo
    [FATO: arquivo, ``91XX0020X0001ATACS  XX0025``]: a resistência é uma
    saída do MODEL, reavaliada a cada passo.

    A mudança de valor é publicada em :meth:`topology_signature`, de modo
    que o solver a trate como MUDANÇA DE TOPOLOGIA: refatora a matriz e
    dispara o CDA de Lin e Martí, exatamente como faz na comutação de uma
    chave. Sem isso a fatoração em cache ficaria obsoleta e o passo
    seguinte seria resolvido com a matriz antiga.
    """

    def set_resistance(self, resistance_ohm: float) -> bool:
        """Impõe ``R`` [Ω]; devolve ``True`` se o valor mudou."""
        r = float(resistance_ohm)
        if not math.isfinite(r) or r <= 0.0:
            raise ValueError(f"resistance_ohm deve ser finito e > 0, obtido {resistance_ohm!r}")
        if r == self.resistance_ohm:
            return False
        self.resistance_ohm = r
        self._g = 1.0 / r
        return True

    def topology_signature(self) -> object:
        return ("R", self.resistance_ohm)


class SwitchedInductor(Inductor):
    """Indutor cujo valor é comutado por um controlador durante a marcha.

    Equivalente do cartão com ``TACS CONTROL`` no campo de indutância
    [FATO: arquivo, ``TACS CONTROL                  XX0024``].

    A corrente de histórico NÃO é reescalada na comutação: o fluxo
    concatenado ``L·i`` salta quando ``L`` salta. É o que o ATP também
    faz com um ramo controlado por TACS, e é a razão de o CDA ser
    obrigatório aqui — ver ``emt_vcb_atp_lc_history_not_rescaled``.
    """

    def set_inductance(self, inductance_H: float) -> bool:
        """Impõe ``L`` [H]; devolve ``True`` se o valor mudou."""
        value = float(inductance_H)
        if not math.isfinite(value) or value <= 0.0:
            raise ValueError(f"inductance_H deve ser finito e > 0, obtido {inductance_H!r}")
        if value == self.inductance_H:
            return False
        self.inductance_H = value
        if self._dt > 0.0:
            self._g = self._dt / (2.0 * value)
        return True

    def topology_signature(self) -> object:
        return ("L", self.inductance_H)


class SwitchedCapacitor(Capacitor):
    """Capacitor cujo valor é comutado por um controlador durante a marcha.

    Admite ``C = 0`` — o valor de ``CCLOSED`` no arquivo [FATO: arquivo,
    ``CCLOSEDr:= 0.0``] —, caso em que a condutância companheira e o
    termo de histórico são nulos e o ramo série fica ABERTO, que é a
    leitura física de uma capacitância nula. A validação de positividade
    do :class:`~app.simulation.emt.components.Capacitor` é contornada na
    construção justamente para admitir esse caso, e reposta em
    :meth:`set_capacitance` na forma ``C >= 0``.
    """

    def __init__(
        self,
        name: str,
        node_p: str,
        node_n: str,
        capacitance_F: float,
        *,
        initial_voltage_V: float = 0.0,
    ) -> None:
        c0 = float(capacitance_F)
        super().__init__(
            name,
            node_p,
            node_n,
            c0 if c0 > 0.0 else 1.0,
            initial_voltage_V=initial_voltage_V,
        )
        self.set_capacitance(c0)

    def set_capacitance(self, capacitance_F: float) -> bool:
        """Impõe ``C`` [F], admitindo zero; devolve ``True`` se mudou."""
        value = float(capacitance_F)
        if not math.isfinite(value) or value < 0.0:
            raise ValueError(f"capacitance_F deve ser finito e >= 0, obtido {capacitance_F!r}")
        if value == self.capacitance_F:
            return False
        self.capacitance_F = value
        if value == 0.0:
            self._i = 0.0
            self._v = 0.0
        if self._dt > 0.0:
            self._g = 2.0 * value / self._dt
        return True

    def topology_signature(self) -> object:
        return ("C", self.capacitance_F)


# -- bloco DATA do MODEL ----------------------------------------------------


@dataclass(frozen=True)
class AtpVcbParameters:
    """Bloco ``DATA`` do MODEL ``VCB_R*``, com os valores do bloco ``USE``.

    Os padrões são os do POLO R (fase A do arquivo). Use
    :meth:`for_pole` para os polos S e T, cujos ``T_OPEN``, ``I_CHOP`` e
    ``DIDT_CRIT`` diferem [FATO: arquivo, blocos USE].

    Attributes
    ----------
    t_open_s:
        ``T_OPENr`` [s] — instante de separação dos contatos.
    rrds_a_kV_per_ms, rrds_b_kV_per_ms2:
        ``RRDS_Ar`` e ``RRDS_Br`` da lei ``V_wth = A·t + B·t²`` (kV, ms).
    i_chop_A:
        ``I_CHOPr`` [A] — limiar de corte de corrente.
    didt_crit_A_per_us:
        ``DIDT_CRITr`` [A/µs] — di/dt crítico de alta frequência.
    r_closed_ohm, r_arc_ohm, r_open_ohm:
        ``RCLOSEDr``, ``RARCr`` e ``ROPENr`` [Ω].
    l_closed_H, l_arc_H, l_open_H:
        ``LCLOSEDr``, ``LARCr`` e ``LOPENr`` [H].
    c_closed_F, c_arc_F, c_open_F:
        ``CCLOSEDr``, ``CARCr`` e ``COPENr`` [F].
    reignition_margin:
        Fator do critério de reignição; 1,1 no arquivo.
    zero_crossing_threshold_A:
        Limiar que valida a passagem por zero; 0,01 A no arquivo.
    extinction_current_A:
        Limiar da segunda condição de extinção; 0,1 A no arquivo.
    """

    t_open_s: float = ATP_T_OPEN_S[0]
    rrds_a_kV_per_ms: float = ATP_RRDS_A_KV_PER_MS
    rrds_b_kV_per_ms2: float = ATP_RRDS_B_KV_PER_MS2
    i_chop_A: float = ATP_I_CHOP_A[0]
    didt_crit_A_per_us: float = ATP_DIDT_CRIT_A_PER_US[0]
    r_closed_ohm: float = ATP_R_CLOSED_OHM
    r_arc_ohm: float = ATP_R_ARC_OHM
    r_open_ohm: float = ATP_R_OPEN_OHM
    l_closed_H: float = ATP_L_CLOSED_H
    l_arc_H: float = ATP_L_ARC_H
    l_open_H: float = ATP_L_OPEN_H
    c_closed_F: float = ATP_C_CLOSED_F
    c_arc_F: float = ATP_C_ARC_F
    c_open_F: float = ATP_C_OPEN_F
    reignition_margin: float = ATP_REIGNITION_MARGIN
    zero_crossing_threshold_A: float = ATP_ZERO_CROSSING_THRESHOLD_A
    extinction_current_A: float = ATP_EXTINCTION_CURRENT_A
    #: Campo ``Imar`` (colunas 35-44) do cartão de chave tipo 13 que o
    #: MODEL comanda [LISTA: 02, §1.3 e §3.6]. No arquivo o campo está EM
    #: BRANCO: a chave abre na primeira passagem natural por zero da
    #: corrente após ``SW_STATE = 0`` — ``None`` reproduz isso (detecção
    #: por mudança de sinal entre passos). Um valor numérico [A] passa a
    #: abrir em ``|i| <= Imar``.
    switch_current_margin_A: float | None = None

    def __post_init__(self) -> None:
        if self.switch_current_margin_A is not None:
            margem = float(self.switch_current_margin_A)
            if not math.isfinite(margem) or margem < 0.0:
                raise ValueError(
                    f"switch_current_margin_A deve ser None (Imar em branco) ou finito e >= 0, obtido {margem!r}"
                )
        for campo in ("t_open_s", "zero_crossing_threshold_A"):
            valor = float(getattr(self, campo))
            if not math.isfinite(valor) or valor < 0.0:
                raise ValueError(f"{campo} deve ser finito e >= 0, obtido {valor!r}")
        for campo in (
            "i_chop_A",
            "didt_crit_A_per_us",
            "r_closed_ohm",
            "r_arc_ohm",
            "r_open_ohm",
            "l_closed_H",
            "l_arc_H",
            "l_open_H",
            "reignition_margin",
            "extinction_current_A",
        ):
            valor = float(getattr(self, campo))
            if not math.isfinite(valor) or valor <= 0.0:
                raise ValueError(f"{campo} deve ser finito e > 0, obtido {valor!r}")
        for campo in ("c_closed_F", "c_arc_F", "c_open_F", "rrds_a_kV_per_ms", "rrds_b_kV_per_ms2"):
            valor = float(getattr(self, campo))
            if not math.isfinite(valor) or valor < 0.0:
                raise ValueError(f"{campo} deve ser finito e >= 0, obtido {valor!r}")

    @classmethod
    def for_pole(cls, index: int, **overrides) -> AtpVcbParameters:
        """Parâmetros do polo ``index`` (0 = R/A, 1 = S/B, 2 = T/C).

        Reproduz os três blocos ``USE`` do arquivo: os polos diferem em
        ``T_OPEN``, ``I_CHOP`` e ``DIDT_CRIT``; todo o resto é comum
        [FATO: arquivo, linhas 526-604].
        """
        k = int(index)
        if not 0 <= k < len(ATP_T_OPEN_S):
            raise ValueError(f"index deve estar em 0..{len(ATP_T_OPEN_S) - 1}, obtido {index!r}")
        base = {
            "t_open_s": ATP_T_OPEN_S[k],
            "i_chop_A": ATP_I_CHOP_A[k],
            "didt_crit_A_per_us": ATP_DIDT_CRIT_A_PER_US[k],
        }
        base.update(overrides)
        return cls(**base)


@dataclass
class AtpPoleResult:
    """Registro de auditoria do polo em modo literal.

    Nada aqui realimenta a máquina de estados: são OBSERVÁVEIS, incluídos
    porque o MODEL do arquivo não publica contadores e o laudo precisa
    deles.
    """

    name: str = ""
    #: ``True`` — a extinção de alta frequência do arquivo usa
    #: ``ABS(DI_DT) > crítico``, convenção INVERTIDA em relação à física
    #: usual (extinguir quando o di/dt no zero é PEQUENO). É saída
    #: declarada do modo literal, exigida para que a leitura do resultado
    #: não confunda as duas convenções.
    didt_convention_inverted: bool = True
    didt_convention: str = DIDT_INTERRUPT_ABOVE
    chopping_time_s: float | None = None
    chopping_current_at_chop_A: float = 0.0
    reignition_count: int = 0
    reignition_times_s: list[float] = field(default_factory=list)
    reignition_voltages_V: list[float] = field(default_factory=list)
    reignition_withstand_V: list[float] = field(default_factory=list)
    extinction_times_s: list[float] = field(default_factory=list)
    hf_extinction_count: int = 0
    zero_crossing_times_s: list[float] = field(default_factory=list)
    state_changes: list[tuple[float, int]] = field(default_factory=list)
    final_state: int = ATP_CB_CLOSED
    peak_gap_voltage_V: float = 0.0
    #: Instante em que a chave IDEAL efetivamente abriu (primeiro passo,
    #: após ``SW_STATE = 0``, em que ``|i| <= Imar``) e a corrente nesse
    #: passo [A]. ``None`` se a chave não chegou a abrir. Distingue o
    #: COMANDO (``T_OPEN``) da ABERTURA (passagem por zero), como no
    #: cartão de chave tipo 13 do ATP [LISTA: 02, §1.3].
    switch_opening_time_s: float | None = None
    switch_opening_current_A: float = 0.0


class AtpModelCompatibility:
    """Máquina de quatro estados do MODEL ``VCB_R*``, reproduzida ao pé da letra.

    Modo de compatibilidade **opcional**, selecionado por parâmetro. Não
    substitui :class:`VacuumCircuitBreakerModel` — reproduz o ARQUIVO,
    com os seis pontos em que a lógica escrita se afasta da idealização
    física, cada um deles verificável em
    ``tests/test_emt_vcb_snubber.py``:

    1. **Quatro estados** com os códigos do arquivo (0 fechado, 1 arco,
       2 aberto, 3 arco de alta frequência) e as MESMAS atribuições de
       ``R``, ``L`` e ``C`` em cada transição. Os quatro blocos ``IF`` do
       ``EXEC`` são sequenciais e não excludentes: uma transição pode
       CASCATEAR dentro do mesmo passo (0→1→2→3), e isso é reproduzido.
    2. **Margem de 10 %** no critério de reignição:
       ``ABS(V_CB) > V_WITH*1.1 AND V_WITH > 0``. O fator NÃO é uma
       tolerância numérica — ele desloca a reignição para 10 % acima da
       suportabilidade publicada.
    3. **Convenção invertida** de extinção de alta frequência:
       ``ABS(DI_DT) > DIDT_CRIT*1E6``, isto é, o arco se extingue quando
       a taxa é GRANDE. A física usual é a oposta. O modo publica
       :attr:`didt_convention_inverted` = ``True`` como saída explícita.
    4. **Reinício do temporizador a cada passagem por zero da corrente**,
       e não na extinção do arco: ``T_ZERO := TNOW`` sempre que
       ``I_PREV*I_CB <= 0`` com ``ABS(I_PREV) > 0,01``. A suportabilidade
       ``V_WITH`` é, portanto, medida desde o último zero de corrente.
    5. **Segunda condição de extinção**, ``ABS(I_CB) < 0,1 AND
       T_ZERO >= 0``, presente tanto no estado 1 quanto no estado 3, que
       zera ``CHOPPED`` e rearma o corte.
    6. **Ramo série R-L-C comutado em paralelo com a chave ideal** — não
       uma chave ideal isolada. É a topologia do arquivo: a chave tipo 13
       controlada por ``SW_STATE`` e, em paralelo, ``C``, ``L`` e ``R``
       controlados por ``C_VAL``, ``L_VAL`` e ``R_VAL``.

    O defeito de ordem em ``I_PREV``
    ---------------------------------
    No arquivo, ``I_PREV := I_CBr`` está DENTRO do bloco
    ``IF TNOW > TIME_PREVr``, que precede o teste de passagem por zero.
    Como esse ``IF`` é verdadeiro em todo passo, quando o teste
    ``IF I_PREV * I_CBr <= 0.0`` é avaliado ``I_PREV`` JÁ VALE ``I_CBr``:
    o produto é ``I_CB²``, não negativo por construção, e o único caso em
    que ele é nulo (``I_CB = 0`` exato) reprova a guarda seguinte
    ``ABS(I_PREV) > 0.01``. Consequência: ``T_ZERO`` permanece em −1,0
    durante toda a simulação, ``V_WITH`` permanece nulo, a reignição
    nunca é declarada e a segunda condição de extinção nunca é atendida.

    Isso NÃO é interpretação: é o que o arquivo executa, e está coberto
    por teste. O parâmetro ``zero_crossing_order`` permite escolher entre
    :data:`ATP_ZERO_ORDER_LITERAL` (padrão — o arquivo, com o defeito) e
    :data:`ATP_ZERO_ORDER_DEFERRED` (``I_PREV`` atualizado ao FIM do
    passo, que é a leitura em que os itens 4 e 5 têm efeito).

    Parameters
    ----------
    switch:
        Chave ideal do polo, comandada por ``SW_STATE``. Deve começar
        FECHADA.
    resistor, inductor, capacitor:
        Elementos do ramo série comutado, em paralelo com a chave.
    parameters:
        Bloco ``DATA``; padrão :class:`AtpVcbParameters` do polo R.
    zero_crossing_order:
        :data:`ATP_ZERO_ORDER_LITERAL` (padrão) ou
        :data:`ATP_ZERO_ORDER_DEFERRED`.
    current_source:
        :data:`ATP_CURRENT_FROM_SWITCH` (padrão, o que o arquivo lê) ou
        :data:`ATP_CURRENT_FROM_POLE`.
    timestep_s:
        Passo usado quando o controlador é acionado por :meth:`step`
        fora de um solver. Padrão :data:`DOC_A_TIME_STEP_S`.
    name:
        Rótulo do polo.

    Raises
    ------
    ValueError
        Tipos errados de componente, seletores inválidos ou ramo série
        mal formado.
    """

    def __init__(
        self,
        switch: Switch,
        resistor: SwitchedResistor,
        inductor: SwitchedInductor,
        capacitor: SwitchedCapacitor,
        *,
        parameters: AtpVcbParameters | None = None,
        zero_crossing_order: str = ATP_ZERO_ORDER_LITERAL,
        current_source: str = ATP_CURRENT_FROM_SWITCH,
        timestep_s: float = DOC_A_TIME_STEP_S,
        name: str = "",
    ) -> None:
        if not isinstance(switch, Switch):
            raise ValueError(
                f"AtpModelCompatibility comanda um Switch do kernel, obtido "
                f"{type(switch).__name__}"
            )
        if not isinstance(resistor, SwitchedResistor):
            raise ValueError(
                f"o ramo de arco exige um SwitchedResistor, obtido {type(resistor).__name__}"
            )
        if not isinstance(inductor, SwitchedInductor):
            raise ValueError(
                f"o ramo de arco exige um SwitchedInductor, obtido {type(inductor).__name__}"
            )
        if not isinstance(capacitor, SwitchedCapacitor):
            raise ValueError(
                f"o ramo de arco exige um SwitchedCapacitor, obtido {type(capacitor).__name__}"
            )
        if str(zero_crossing_order) not in ATP_ZERO_ORDERS:
            raise ValueError(
                f"zero_crossing_order deve ser um de {ATP_ZERO_ORDERS}, "
                f"obtido {zero_crossing_order!r}"
            )
        if str(current_source) not in ATP_CURRENT_SOURCES:
            raise ValueError(
                f"current_source deve ser um de {ATP_CURRENT_SOURCES}, "
                f"obtido {current_source!r}"
            )
        dt = float(timestep_s)
        if not math.isfinite(dt) or dt <= 0.0:
            raise ValueError(f"timestep_s deve ser finito e > 0, obtido {timestep_s!r}")
        if not (set(capacitor.nodes) & set(inductor.nodes)) or not (
            set(inductor.nodes) & set(resistor.nodes)
        ):
            raise ValueError(
                f"C {capacitor.nodes}, L {inductor.nodes} e R {resistor.nodes} não "
                f"formam um ramo série contíguo"
            )
        if not switch.closed:
            log.warning(
                "polo literal %r criado com a chave ABERTA: o MODEL do arquivo "
                "parte de SW_STATE = 1.0 (fechada)",
                name or switch.name,
            )

        self.switch = switch
        self.resistor = resistor
        self.inductor = inductor
        self.capacitor = capacitor
        self.parameters = parameters if parameters is not None else AtpVcbParameters()
        self.zero_crossing_order = str(zero_crossing_order)
        self.current_source = str(current_source)
        self.timestep_s = dt
        self.name = str(name) if name else str(switch.name)

        # Bloco VAR do MODEL, com os mesmos nomes em minúsculas.
        self.tnow: float = 0.0
        self.sw_state: float = 1.0
        # Semântica tipo 13: o comando de abertura só se efetiva na
        # passagem por zero seguinte; guarda-se a corrente da chave no
        # passo anterior e se o comando já foi visto com a chave fechada.
        self._i_sw_prev: float = 0.0
        self._sw_open_commanded: bool = False
        self.r_val: float = self.parameters.r_closed_ohm
        self.l_val: float = self.parameters.l_closed_H
        self.c_val: float = self.parameters.c_closed_F
        self.v_cb: float = 0.0
        self.v_with: float = 0.0
        self.t_azero: float = 0.0
        self.t_zero: float = -1.0
        self.i_prev: float = 0.0
        self.cb_state: int = ATP_CB_CLOSED
        self.di_dt: float = 0.0
        self.chopped: int = 0
        self.time_prev: float = 0.0
        self.t_ms: float = 0.0
        self.t_squared: float = 0.0
        self.vwithstandkv: float = 0.0

        self._t_solver_prev: float = -1.0
        self._result = AtpPoleResult(name=self.name)
        self.reset()

    # -- ciclo de vida ------------------------------------------------------

    def reset(self) -> None:
        """Reproduz o bloco ``INIT`` do MODEL e repõe os componentes."""
        p = self.parameters
        self.tnow = 0.0
        self.sw_state = 1.0
        self._i_sw_prev = 0.0
        self._sw_open_commanded = False
        self.r_val = p.r_closed_ohm
        self.l_val = p.l_closed_H
        self.c_val = p.c_closed_F
        self.v_cb = 0.0
        self.v_with = 0.0
        self.t_azero = 0.0
        self.t_zero = -1.0
        self.i_prev = 0.0
        self.cb_state = ATP_CB_CLOSED
        self.di_dt = 0.0
        self.chopped = 0
        self.time_prev = 0.0
        self.t_ms = 0.0
        self.t_squared = 0.0
        self.vwithstandkv = 0.0
        self._t_solver_prev = -1.0
        self._result = AtpPoleResult(name=self.name)
        self.switch.set_state(True)
        self.apply()

    # -- leitura ------------------------------------------------------------

    @property
    def state(self) -> int:
        """``CB_STATE`` corrente, com o código inteiro do arquivo."""
        return self.cb_state

    @property
    def state_name(self) -> str:
        """Nome legível do estado corrente."""
        return ATP_CB_STATE_NAMES[self.cb_state]

    @property
    def didt_convention(self) -> str:
        """Sempre :data:`DIDT_INTERRUPT_ABOVE` — o critério do arquivo."""
        return DIDT_INTERRUPT_ABOVE

    @property
    def didt_convention_inverted(self) -> bool:
        """``True``: o arquivo extingue com ``|di/dt| > crítico``.

        Saída ADICIONAL do modo literal, exigida para que quem lê o
        resultado saiba que a convenção é a inversa da física usual —
        a mesma ambiguidade registrada em
        ``emt_vcb_didt_convention_ambiguous``.
        """
        return True

    @property
    def result(self) -> AtpPoleResult:
        """Registro de auditoria do polo."""
        self._result.final_state = self.cb_state
        return self._result

    @property
    def outputs(self) -> dict[str, float | bool]:
        """Bloco ``OUTPUT`` do MODEL, mais a saída de convenção invertida.

        As cinco primeiras chaves são exatamente as saídas declaradas no
        arquivo (``SW_STATEr``, ``R_VALr``, ``L_VALr``, ``C_VALr`` e
        ``CB_STATEr``); ``DIDT_INVERTED`` é o acréscimo do item 3.
        """
        return {
            "SW_STATE": self.sw_state,
            "R_VAL": self.r_val,
            "L_VAL": self.l_val,
            "C_VAL": self.c_val,
            "CB_STATE": float(self.cb_state),
            "DIDT_INVERTED": True,
        }

    def withstand_V(self) -> float:
        """``V_WITHr`` do último passo [V]."""
        return self.v_with

    # -- atribuições de R, L e C por estado ---------------------------------

    def _assign_closed(self) -> None:
        p = self.parameters
        self.r_val, self.l_val, self.c_val = p.r_closed_ohm, p.l_closed_H, p.c_closed_F

    def _assign_arc(self) -> None:
        p = self.parameters
        self.r_val, self.l_val, self.c_val = p.r_arc_ohm, p.l_arc_H, p.c_arc_F

    def _assign_open(self) -> None:
        p = self.parameters
        self.r_val, self.l_val, self.c_val = p.r_open_ohm, p.l_open_H, p.c_open_F

    # -- EXEC ---------------------------------------------------------------

    def step(self, *, v_cb: float, i_cb: float, tnow: float) -> None:
        """Um ``EXEC`` do MODEL, na ordem em que está escrito no arquivo.

        Parameters
        ----------
        v_cb:
            ``V_POSr − V_NEGr`` [V] no passo.
        i_cb:
            ``I_CBr`` [A] no passo.
        tnow:
            ``TNOW`` [s] — o relógio interno do MODEL, que vale
            ``k·timestep`` no k-ésimo ``EXEC``.
        """
        p = self.parameters
        i = float(i_cb)
        self.tnow = float(tnow)
        self.v_cb = float(v_cb)
        self._result.peak_gap_voltage_V = max(
            self._result.peak_gap_voltage_V, abs(self.v_cb)
        )

        # IF TNOW > TIME_PREVr THEN ... ENDIF
        if self.tnow > self.time_prev:
            self.di_dt = (i - self.i_prev) / (self.tnow - self.time_prev)
            self.time_prev = self.tnow
            if self.zero_crossing_order == ATP_ZERO_ORDER_LITERAL:
                # Ordem do ARQUIVO: I_PREV é sobrescrito ANTES do teste
                # de passagem por zero que vem a seguir.
                self.i_prev = i

        # IF I_PREV * I_CBr <= 0.0 THEN IF ABS(I_PREV) > 0.01 THEN ...
        if self.i_prev * i <= 0.0:
            if abs(self.i_prev) > p.zero_crossing_threshold_A:
                self.t_zero = self.tnow
                self.t_azero = 0.0
                self._result.zero_crossing_times_s.append(self.tnow)

        if self.zero_crossing_order == ATP_ZERO_ORDER_DEFERRED:
            self.i_prev = i

        # IF T_ZEROr >= 0.0 THEN T_AZEROr := TNOW - T_ZEROr ENDIF
        if self.t_zero >= 0.0:
            self.t_azero = self.tnow - self.t_zero

        self.t_ms = self.t_azero * 1000.0
        self.t_squared = self.t_ms * self.t_ms
        self.vwithstandkv = p.rrds_a_kV_per_ms * self.t_ms + p.rrds_b_kV_per_ms2 * self.t_squared

        if self.tnow > p.t_open_s and self.cb_state > 0:
            self.v_with = self.vwithstandkv * 1000.0
        else:
            self.v_with = 0.0

        # Os quatro blocos são SEQUENCIAIS no arquivo (IF, não ELSIF): uma
        # transição pode cascatear dentro do mesmo EXEC.
        if self.cb_state == ATP_CB_CLOSED:
            if self.tnow >= p.t_open_s:
                self._enter(ATP_CB_ARCING)
                self.sw_state = 0.0
                self._assign_arc()
            else:
                self._assign_closed()

        if self.cb_state == ATP_CB_ARCING:
            if abs(i) <= p.i_chop_A and self.chopped == 0:
                self.chopped = 1
                self._enter(ATP_CB_OPEN)
                self._assign_open()
                if self._result.chopping_time_s is None:
                    self._result.chopping_time_s = self.tnow
                    self._result.chopping_current_at_chop_A = i
                self._result.extinction_times_s.append(self.tnow)
            if abs(i) < p.extinction_current_A and self.t_zero >= 0.0:
                self._enter(ATP_CB_OPEN)
                self._assign_open()
                self.chopped = 0
                self._result.extinction_times_s.append(self.tnow)

        if self.cb_state == ATP_CB_OPEN:
            if abs(self.v_cb) > self.v_with * p.reignition_margin and self.v_with > 0.0:
                self._enter(ATP_CB_ARCING_HF)
                self._assign_arc()
                self._result.reignition_count += 1
                self._result.reignition_times_s.append(self.tnow)
                self._result.reignition_voltages_V.append(self.v_cb)
                self._result.reignition_withstand_V.append(self.v_with)

        if self.cb_state == ATP_CB_ARCING_HF:
            if (
                abs(self.di_dt) > p.didt_crit_A_per_us * 1.0e6
                and abs(i) < p.extinction_current_A
            ):
                self._enter(ATP_CB_OPEN)
                self._assign_open()
                self.chopped = 0
                self._result.hf_extinction_count += 1
                self._result.extinction_times_s.append(self.tnow)
            if abs(i) < p.extinction_current_A and self.t_zero >= 0.0:
                self._enter(ATP_CB_OPEN)
                self._assign_open()
                self.chopped = 0
                self._result.extinction_times_s.append(self.tnow)

    def _enter(self, state: int) -> None:
        """Registra a mudança de ``CB_STATE`` e a efetiva."""
        if state != self.cb_state:
            self._result.state_changes.append((self.tnow, int(state)))
        self.cb_state = int(state)

    # -- acoplamento com o kernel -------------------------------------------

    def apply(self) -> None:
        """Escreve ``SW_STATE``, ``R_VAL``, ``L_VAL`` e ``C_VAL`` nos ramos.

        Semântica da chave tipo 13 do ATP. ``SW_STATE = 0`` é um COMANDO
        de abertura, não a abertura em si: a chave controlada por TACS só
        abre no primeiro instante em que ``|i| <= Imar`` (campo *current
        margin*; em branco, a passagem natural por zero) [LISTA: 02, §1.3
        e §3.6]. Forçar a abertura no instante do comando — como este
        método fazia — descarrega a corrente de carga (74 A no polo R,
        centenas de ampères nos polos S e T) no ramo série de arco de
        20 Ω / 50 nH / 20 pF e produz um degrau de centenas de quilovolts
        em um passo, artefato que cresce com a redução do passo
        [CÁLCULO PRÓPRIO: ``Δv ≈ i·Δt/C_arc`` = 74 A × 1 µs / 20 pF =
        3,7 MV antes do amortecimento da rede]. A própria lógica do
        MODEL pressupõe a chave ainda conduzindo no estado de arco: o
        corte (``|I_CB| <= I_CHOP``) é testado sobre a corrente TOTAL do
        polo enquanto a chave a carrega.
        """
        i_now = float(self.switch.branch_current(0))
        if self.sw_state > 0.5:
            self.switch.set_state(True)
        elif self.switch.closed:
            margem = self.parameters.switch_current_margin_A
            if margem is None:
                # Imar em branco: abre na primeira mudança de sinal da
                # corrente da chave após o comando (zero natural).
                pode_abrir = self._i_sw_prev * i_now <= 0.0 and self._sw_open_commanded
            else:
                pode_abrir = abs(i_now) <= float(margem)
            if pode_abrir:
                self.switch.set_state(False)
                self._result.switch_opening_time_s = self.tnow
                self._result.switch_opening_current_A = i_now
            self._sw_open_commanded = True
        self._i_sw_prev = i_now
        self.resistor.set_resistance(self.r_val)
        self.inductor.set_inductance(self.l_val)
        self.capacitor.set_capacitance(self.c_val)

    def measured_current_A(self) -> float:
        """``I_CBr`` conforme :attr:`current_source` [A]."""
        i_switch = float(self.switch.branch_current(0))
        if self.current_source == ATP_CURRENT_FROM_SWITCH:
            return i_switch
        return i_switch + float(self.resistor.branch_current(0))

    def __call__(self, t: float, solver) -> None:
        """Controlador do kernel: um ``EXEC`` por passo, no relógio do MODEL."""
        t_f = float(t)
        if self._t_solver_prev >= 0.0 and t_f < self._t_solver_prev:
            self.reset()
        dt = float(getattr(solver, "dt", 0.0)) or self.timestep_s
        # O k-ésimo EXEC do MODEL ocorre em TNOW = k·timestep, enquanto o
        # controlador do kernel é chamado com o instante JÁ resolvido,
        # (k−1)·Δt. O deslocamento de um passo é o que faz o instante de
        # separação cair no MESMO passo dos dois programas.
        self.step(
            v_cb=float(self.switch.branch_voltage(0)),
            i_cb=self.measured_current_A(),
            tnow=t_f + dt,
        )
        self.apply()
        self._t_solver_prev = t_f


# -- montagem do polo -------------------------------------------------------


@dataclass(frozen=True)
class AtpLiteralPole:
    """Polo em modo literal: chave ideal + ramo série R-L-C + controlador."""

    switch: Switch
    resistor: SwitchedResistor
    inductor: SwitchedInductor
    capacitor: SwitchedCapacitor
    controller: AtpModelCompatibility

    @property
    def components(self) -> tuple:
        """Componentes a inserir no circuito, na ordem de montagem."""
        return (self.switch, self.capacitor, self.inductor, self.resistor)

    @property
    def name(self) -> str:
        """Rótulo do polo."""
        return self.controller.name


@dataclass(frozen=True)
class VcbPole:
    """Polo no modo PADRÃO: chave ideal comandada por :class:`VacuumCircuitBreakerModel`."""

    switch: Switch
    controller: VacuumCircuitBreakerModel

    @property
    def components(self) -> tuple:
        """Componentes a inserir no circuito."""
        return (self.switch,)

    @property
    def name(self) -> str:
        """Rótulo do polo."""
        return self.controller.name


def build_atp_literal_pole(
    name: str,
    node_p: str,
    node_n: str,
    *,
    parameters: AtpVcbParameters | None = None,
    node_mid_c: str | None = None,
    node_mid_l: str | None = None,
    switch: Switch | None = None,
    **kwargs,
) -> AtpLiteralPole:
    """Monta o polo do arquivo: chave ideal ‖ (C série L série R).

    A ordem dos elementos é a dos cartões de ramo do arquivo — do nó de
    fonte para o nó de carga, ``C``, depois ``L``, depois ``R``
    [FATO: arquivo, ``X0002AXX0021`` (C), ``XX0021XX0020`` (L),
    ``91XX0020X0001A`` (R)]. A ordem não altera a resposta do ramo série,
    mas mantém os nós internos rastreáveis contra o arquivo.

    Parameters
    ----------
    name:
        Prefixo dos componentes: gera ``<name>``, ``<name>_c``,
        ``<name>_l`` e ``<name>_r``.
    node_p, node_n:
        Nós do polo (lado da fonte e lado da carga).
    parameters:
        Bloco ``DATA``; padrão o do polo R.
    node_mid_c, node_mid_l:
        Nós internos do ramo série; padrão ``<name>_mc`` e ``<name>_ml``.
    switch:
        Chave já existente a reaproveitar; padrão cria uma fechada.
    **kwargs:
        Repassados a :class:`AtpModelCompatibility`.

    Returns
    -------
    AtpLiteralPole
        Componentes e controlador prontos para ``Circuit.extend`` e
        ``Solver.run(controllers=...)``.
    """
    label = str(name)
    if not label:
        raise ValueError("build_atp_literal_pole exige um nome não vazio")
    par = parameters if parameters is not None else AtpVcbParameters()
    mid_c = str(node_mid_c) if node_mid_c else f"{label}_mc"
    mid_l = str(node_mid_l) if node_mid_l else f"{label}_ml"
    sw = switch if switch is not None else Switch(label, str(node_p), str(node_n), closed=True)
    cap = SwitchedCapacitor(f"{label}_c", str(node_p), mid_c, par.c_closed_F)
    ind = SwitchedInductor(f"{label}_l", mid_c, mid_l, par.l_closed_H)
    res = SwitchedResistor(f"{label}_r", mid_l, str(node_n), par.r_closed_ohm)
    ctrl = AtpModelCompatibility(sw, res, ind, cap, parameters=par, name=label, **kwargs)
    return AtpLiteralPole(switch=sw, resistor=res, inductor=ind, capacitor=cap, controller=ctrl)


def build_vcb_pole(
    name: str,
    node_p: str,
    node_n: str,
    *,
    atp_model_compatibility: bool = False,
    parameters: AtpVcbParameters | None = None,
    **kwargs,
):
    """Monta um polo de disjuntor no modo PADRÃO ou no modo LITERAL.

    É o ponto de entrada em que o modo de compatibilidade é
    **selecionado por parâmetro**:

    * ``atp_model_compatibility=False`` (padrão) devolve um
      :class:`VcbPole` — uma chave ideal comandada por
      :class:`VacuumCircuitBreakerModel`, com o comportamento de sempre;
    * ``atp_model_compatibility=True`` devolve um :class:`AtpLiteralPole`
      — a máquina de quatro estados do arquivo e o ramo série R-L-C
      comutado em paralelo com a chave.

    Os dois expõem ``switch``, ``controller``, ``components`` e ``name``,
    de modo que o chamador monta o circuito da mesma forma nos dois modos.

    Parameters
    ----------
    name, node_p, node_n:
        Rótulo e nós do polo.
    atp_model_compatibility:
        Seletor do modo. Padrão ``False``.
    parameters:
        Bloco ``DATA`` do modo literal; ignorado no modo padrão.
    **kwargs:
        Repassados ao controlador do modo escolhido.
    """
    if atp_model_compatibility:
        return build_atp_literal_pole(
            name, node_p, node_n, parameters=parameters, **kwargs
        )
    if parameters is not None:
        raise ValueError(
            "parameters só se aplica ao modo literal; use "
            "atp_model_compatibility=True ou remova o argumento"
        )
    sw = Switch(str(name), str(node_p), str(node_n), closed=True)
    kwargs.setdefault("name", str(name))
    return VcbPole(switch=sw, controller=VacuumCircuitBreakerModel(sw, **kwargs))


def three_phase_atp_literal_poles(
    prefix: str,
    nodes_p: Sequence[str],
    nodes_n: Sequence[str],
    **kwargs,
) -> tuple[AtpLiteralPole, ...]:
    """Três polos literais com os dados ``USE`` de cada fase do arquivo.

    Parameters
    ----------
    prefix:
        Prefixo comum; gera ``<prefix>_a``, ``<prefix>_b``, ``<prefix>_c``.
    nodes_p, nodes_n:
        Nós de fonte e de carga por fase, na ordem A, B, C.
    **kwargs:
        Repassados a :func:`build_atp_literal_pole`.
    """
    ps = tuple(str(n) for n in nodes_p)
    ns = tuple(str(n) for n in nodes_n)
    if len(ps) != len(ns) or not ps:
        raise ValueError(
            f"nodes_p ({len(ps)}) e nodes_n ({len(ns)}) devem ter o mesmo "
            f"comprimento, não nulo"
        )
    rotulos = ("a", "b", "c") if len(ps) == 3 else tuple(str(k) for k in range(len(ps)))
    return tuple(
        build_atp_literal_pole(
            f"{prefix}_{lbl}",
            p,
            n,
            parameters=AtpVcbParameters.for_pole(k),
            **kwargs,
        )
        for k, (lbl, p, n) in enumerate(zip(rotulos, ps, ns))
    )



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
    "emt_vcb_atp_iprev_overwritten_before_zero_test": (
        "MODO LITERAL. No MODEL VCB_R* do arquivo, a atribuição I_PREV := I_CBr "
        "está DENTRO do bloco IF TNOW > TIME_PREVr, que precede o teste de "
        "passagem por zero IF I_PREV * I_CBr <= 0.0. Como esse IF é verdadeiro "
        "em todo passo, o teste compara a corrente com ela mesma: o produto é "
        "I_CB², nunca negativo, e o único caso em que se anula (I_CB = 0 exato) "
        "reprova a guarda ABS(I_PREV) > 0,01 que vem logo abaixo. Consequência "
        "executada pelo arquivo: T_ZERO permanece em −1,0, T_AZERO em zero, "
        "V_WITH em zero, e portanto NÃO HÁ REIGNIÇÃO nem segunda condição de "
        "extinção durante toda a simulação. O modo literal reproduz isso por "
        "padrão (ATP_ZERO_ORDER_LITERAL) e oferece a ordem adiada "
        "(ATP_ZERO_ORDER_DEFERRED) como leitura da INTENÇÃO do autor. Toda "
        "reignição relatada a partir deste caso depende de qual das duas "
        "ordens foi usada, e isso precisa constar do laudo."
    ),
    "emt_vcb_atp_current_read_from_ideal_switch_only": (
        "MODO LITERAL. A entrada I_CBr do MODEL vem do par de chaves MEASURING "
        "que está em série com a CHAVE IDEAL tipo 13, e não com o ramo R-L-C "
        "paralelo. Como SW_STATE é posto em 0,0 na transição fechado→arco e "
        "NUNCA volta a 1,0, a corrente medida cai a zero um passo depois da "
        "separação de contatos: o critério de corte ABS(I_CB) <= I_CHOP é "
        "atendido de imediato, e o corte que o modelo declara não é o colapso "
        "do arco a vácuo, é a abertura da própria chave ideal. A corrente "
        "física do polo continua pelo ramo R-L-C — em particular pelos 6 µF do "
        "estado aberto. O seletor current_source='pole' quantifica a diferença."
    ),
    "emt_vcb_atp_lc_unit_convention": (
        "MODO LITERAL. Os campos de indutância e capacitância do arquivo "
        "(LARC = 5.E-5, LOPEN = 6.E-7, CARC = 2.E-5, COPEN = 6.) NÃO admitem "
        "uma única convenção de unidade consistente: com o cartão de dados "
        "diversos sem XOPT/COPT, a leitura padrão do ATP é mH e µF, que dá "
        "COPEN = 6 µF (compatível com a especificação do caso) mas CARC = 20 pF "
        "(a especificação registra 20 nF). Os valores adotados como padrão "
        "deste módulo são os da especificação — 50 µH, 0,6 µH, 20 nF e 6 µF — e "
        "estão inteiramente parametrizados em AtpVcbParameters. No estado ABERTO "
        "a sensibilidade é baixa, porque o 1 MΩ em série domina os três "
        "elementos (a 6 µF vale 26,5 Ω em 1 kHz e a 0,6 µH vale 3,8 mΩ) "
        "[CÁLCULO PRÓPRIO]; no estado de ARCO, ao contrário, o 20 Ω é da "
        "mesma ordem das reatâncias e a leitura escolhida muda a frequência "
        "natural da malha de reignição por ordens de grandeza."
    ),
    "emt_vcb_atp_lc_history_not_rescaled": (
        "MODO LITERAL. Na comutação dos valores de R, L e C do ramo série, o "
        "histórico trapezoidal do indutor e do capacitor NÃO é reescalado: o "
        "fluxo concatenado L·i e a carga C·v saltam junto com o parâmetro. É o "
        "mesmo que um ramo controlado por TACS faz no ATP, e é a razão de a "
        "mudança de valor ser publicada como mudança de TOPOLOGIA neste kernel "
        "— para que o CDA de Lin e Martí seja disparado e a oscilação numérica "
        "de período 2·Δt seja removida. Ainda assim o salto é uma "
        "descontinuidade energética não física do modelo de origem."
    ),
    "emt_vcb_atp_state_codes_differ": (
        "MODO LITERAL. Os códigos de estado do arquivo (0 fechado, 1 arco, "
        "2 aberto, 3 arco de alta frequência) NÃO coincidem com a ordem de "
        "VCB_STATES deste módulo, em que o arco de alta frequência precede o "
        "aberto. Qualquer confronto entre as duas máquinas — inclusive o "
        "limiar STA > 1.9 do controlador do ramo amortecedor, que arma nos "
        "estados 2 e 3 — deve ser feito pelo código do arquivo, não pelo nome."
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
    # modo de compatibilidade literal com o MODEL do arquivo ATP
    "ATP_T_OPEN_S",
    "ATP_I_CHOP_A",
    "ATP_DIDT_CRIT_A_PER_US",
    "ATP_RRDS_A_KV_PER_MS",
    "ATP_RRDS_B_KV_PER_MS2",
    "ATP_REIGNITION_MARGIN",
    "ATP_ZERO_CROSSING_THRESHOLD_A",
    "ATP_EXTINCTION_CURRENT_A",
    "ATP_R_CLOSED_OHM",
    "ATP_R_ARC_OHM",
    "ATP_R_OPEN_OHM",
    "ATP_L_CLOSED_H",
    "ATP_L_ARC_H",
    "ATP_L_OPEN_H",
    "ATP_C_CLOSED_F",
    "ATP_C_ARC_F",
    "ATP_C_OPEN_F",
    "ATP_CB_CLOSED",
    "ATP_CB_ARCING",
    "ATP_CB_OPEN",
    "ATP_CB_ARCING_HF",
    "ATP_CB_STATES",
    "ATP_CB_STATE_NAMES",
    "ATP_ZERO_ORDER_LITERAL",
    "ATP_ZERO_ORDER_DEFERRED",
    "ATP_ZERO_ORDERS",
    "ATP_CURRENT_FROM_SWITCH",
    "ATP_CURRENT_FROM_POLE",
    "ATP_CURRENT_SOURCES",
    "SwitchedResistor",
    "SwitchedInductor",
    "SwitchedCapacitor",
    "AtpVcbParameters",
    "AtpPoleResult",
    "AtpModelCompatibility",
    "AtpLiteralPole",
    "VcbPole",
    "build_atp_literal_pole",
    "build_vcb_pole",
    "three_phase_atp_literal_poles",
    "stagger_times",
    "three_phase_vcb",
    # auditoria
    "KNOWN_LIMITATIONS",
]
