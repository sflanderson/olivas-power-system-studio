"""
app.simulation.emt — motor de transitórios eletromagnéticos (EMT)
dedicado do **Olivas Power System Studio** (v4.0.0-beta).

Por que um motor próprio
=========================

O executável ATP-EMTP (TPBIG) é binário licenciado de terceiro, não
redistribuível e orientado a UM caso por execução. O estudo de vida
residual do isolamento exige da ordem de 10³ a 10⁴ execuções — o
cruzamento da frente de Pareto de planos de corte com o Monte Carlo do
instante de abertura e da corrente de *chopping*. Isso é incompatível
com aquele executável em três frentes: volume de execuções,
reprodutibilidade auditável e distribuição comercial.

O arquivo ``.atp`` permanece **fonte única da verdade** do caso
técnico; o que muda é quem o resolve. O runner do ATP
(:mod:`app.simulation.runner`) continua funcionando e não é tocado por
este pacote.

Escopo do kernel
=================

Solver nodal de Dommel com integração trapezoidal, passo fixo e
formulação nodal aumentada (MNA), com:

* modelos companheiros de ``R``, ``L``, ``C`` e ramo RL acoplado;
* fonte de tensão ideal e chave ideal por MNA (sem impedância
  fictícia), com dimensão do sistema invariante à topologia;
* linha/cabo a parâmetros distribuídos constantes (Bergeron) com
  interpolação linear de histórico e perdas concentradas ``R/4, R/2,
  R/4``;
* **amortecimento crítico (CDA)** por dois meios-passos de Euler
  regressivo após cada manobra — indispensável para que a interrupção
  de corrente indutiva não gere oscilação numérica de período ``2Δt``;
* cache de fatoração LU indexado por assinatura de topologia;
* sondas que alimentam
  :func:`app.postprocessor.prognosis.stress_profile.extract_stress_events`.

Referências principais
=======================

* [LITERATURA: H. W. Dommel, "Digital Computer Solution of
  Electromagnetic Transients in Single- and Multiphase Networks",
  *IEEE Transactions on Power Apparatus and Systems*, vol. PAS-88,
  n. 4, pp. 388-399, abr. 1969, doi:10.1109/TPAS.1969.292459]
* [LITERATURA: J. R. Marti e J. Lin, "Suppression of numerical
  oscillations in the EMTP", *IEEE Transactions on Power Systems*,
  vol. 4, n. 2, pp. 739-747, maio 1989, doi:10.1109/59.193849]
* [LITERATURA: J. A. Martinez-Velasco (ed.), *Transient Analysis of
  Power Systems: Solution Techniques, Tools and Applications*,
  Wiley/IEEE Press, 2015]
* [LITERATURA: A. Greenwood, *Electrical Transients in Power
  Systems*, 2. ed., Wiley, 1991]
* [LITERATURA: L. van der Sluis, *Transients in Power Systems*,
  Wiley, 2001]

Exemplo mínimo
===============

::

    from app.simulation.emt import (
        Circuit, Solver, Resistor, Capacitor, VoltageSource,
        NodeVoltageProbe,
    )

    ckt = Circuit("rc")
    ckt.add(VoltageSource("E", "1", "gnd", amplitude_V=0.0,
                          frequency_Hz=0.0, dc_offset_V=100.0))
    ckt.add(Resistor("R", "1", "2", 1000.0))
    ckt.add(Capacitor("C", "2", "gnd", 1.0e-6))

    solver = Solver(ckt, dt=1.0e-6)
    vc = solver.add_probe(NodeVoltageProbe("v_C", "2"))
    solver.run(t_end=5.0e-3)
    v_final = vc.values[-1]      # ≈ 100·(1 − e^(−5)) V

Sem I/O, sem GUI, determinístico.
"""

from __future__ import annotations

from app.simulation.emt.circuit import (
    DEFAULT_FACTORIZATION_CACHE_SIZE,
    INVERSE_CONDITION_LIMIT,
    PIVOT_TOLERANCE,
    SOLVE_STRATEGIES,
    Circuit,
    Controller,
    SingularSystemError,
    Solver,
    SolverResult,
    TimedSwitchController,
    lu_factor,
    lu_solve,
)
from app.simulation.emt.components import (
    GROUND_INDEX,
    GROUND_NAMES,
    INTEGRATION_MODES,
    MODE_BACKWARD_EULER_HALF,
    MODE_TRAPEZOIDAL,
    Capacitor,
    Component,
    CoupledRL,
    Inductor,
    Resistor,
    Switch,
    VoltageSource,
    is_ground,
    node_voltage,
    three_phase_voltage_sources,
)
from app.simulation.emt.line import BergeronLine, surge_impedance, travel_time
from app.simulation.emt.probes import (
    V_TO_KV,
    BranchCurrentProbe,
    BranchVoltageProbe,
    DifferentialVoltageProbe,
    NodeVoltageProbe,
    Probe,
    probe_series,
    to_kV,
    to_stress_profile,
)

__all__ = [
    # circuito e solver
    "Circuit",
    "Solver",
    "SolverResult",
    "Controller",
    "TimedSwitchController",
    "SingularSystemError",
    "lu_factor",
    "lu_solve",
    "PIVOT_TOLERANCE",
    "INVERSE_CONDITION_LIMIT",
    "SOLVE_STRATEGIES",
    "DEFAULT_FACTORIZATION_CACHE_SIZE",
    # componentes
    "Component",
    "Resistor",
    "Inductor",
    "Capacitor",
    "VoltageSource",
    "Switch",
    "CoupledRL",
    "three_phase_voltage_sources",
    "MODE_TRAPEZOIDAL",
    "MODE_BACKWARD_EULER_HALF",
    "INTEGRATION_MODES",
    "GROUND_NAMES",
    "GROUND_INDEX",
    "is_ground",
    "node_voltage",
    # linha
    "BergeronLine",
    "surge_impedance",
    "travel_time",
    # sondas
    "Probe",
    "NodeVoltageProbe",
    "BranchVoltageProbe",
    "BranchCurrentProbe",
    "DifferentialVoltageProbe",
    "to_kV",
    "to_stress_profile",
    "probe_series",
    "V_TO_KV",
    # auditoria
    "KNOWN_LIMITATIONS",
]


# ---------------------------------------------------------------------------
# Limitações conhecidas do módulo — padrão do projeto
# (cf. app/postprocessor/audit_trail.py:338-382 e
# app/postprocessor/prognosis/__init__.py:168). Chaves com prefixo
# ``emt_`` para evitar colisão no catálogo global do laudo.
# ---------------------------------------------------------------------------

KNOWN_LIMITATIONS: dict[str, str] = {
    "emt_no_steady_state_init": (
        "NÃO há inicialização fasorial em regime permanente nem rodada de "
        "condições iniciais consistentes. Toda simulação parte do repouso "
        "(correntes de indutor e tensões de capacitor nulas, salvo condição "
        "inicial explícita nos componentes) e a primeira amostra registrada é "
        "a de t = Δt, não a de t = 0. O caso deve incluir uma janela de "
        "acomodação de pelo menos 5 constantes de tempo ANTES do evento de "
        "manobra, sob pena de o transitório de energização contaminar o V_pk "
        "e o dv/dt medidos."
    ),
    "emt_cda_residual_in_stiff_networks": (
        "Um único passo de CDA (o padrão do ATP, cda_full_steps=1) reduz o "
        "artefato trapezoidal por um fator da ordem de (1 + R·Δt/2L)², mas não "
        "o anula: em rede muito rígida após o evento — constante de tempo "
        "residual muito menor que Δt, caso da interrupção contra resistência "
        "de fuga elevada e SEM snubber — pode restar oscilação da ordem de "
        "dezenas de vezes o valor de regime. [CÁLCULO PRÓPRIO: L = 1 mH, "
        "R_p = 100 kΩ, Δt = 1 µs — resíduo de 36x o regime com 1 passo, 1,01x "
        "com 2 passos.] Use cda_full_steps=2 nesses casos."
    ),
    "emt_cda_half_step_not_recorded": (
        "Por padrão as sondas registram apenas os instantes de passo COMPLETO; "
        "as amostras internas dos meios-passos do CDA são descartadas para "
        "manter a base de tempo uniforme. Como o maior valor instantâneo logo "
        "após uma interrupção pode cair DENTRO do par de meios-passos, o V_pk "
        "registrado pode subestimar o valor calculado pelo próprio solver. "
        "Ative Solver(record_half_steps=True) quando o pico importar."
    ),
    "emt_constant_parameter_line": (
        "A linha/cabo é de PARÂMETROS CONSTANTES (Bergeron). Não há modelo "
        "dependente da frequência (JMarti) nem transformação modal para "
        "múltiplos condutores. O efeito pelicular e o retorno pela terra, que "
        "atenuam e deformam a frente real, não são reproduzidos: a frente "
        "chega à outra extremidade praticamente sem atenuação. Os valores de "
        "V_pk e dv/dt daí extraídos são COTA SUPERIOR do estresse real, não "
        "estimativa central."
    ),
    "emt_single_mode_line": (
        "Cada linha é um ramo MONOFÁSICO independente. O acoplamento mútuo "
        "entre condutores de um mesmo cabo tripolar não é representado, de "
        "modo que a dispersão entre modos aéreo e de terra — e o consequente "
        "espalhamento temporal entre fases — está ausente."
    ),
    "emt_ideal_switch_no_arc": (
        "A chave é IDEAL: condução sem resistência e abertura instantânea, "
        "sem modelo de arco, de rigidez dielétrica de recuperação nem de "
        "corrente de chopping. Reacendimento, chopping e a curva V_wth(t) = "
        "A·t + B·t² pertencem ao CONTROLADOR que comanda a chave, camada "
        "acima deste kernel."
    ),
    "emt_switching_quantized_to_step": (
        "O passo é FIXO e a manobra só ocorre em instante múltiplo de Δt. Não "
        "há interpolação para o cruzamento exato por zero da corrente nem "
        "reamostragem no instante do evento, o que introduz erro de até Δt no "
        "instante de abertura e, com passo de 1 µs, até 1 µs de incerteza no "
        "instante de chopping. O Monte Carlo de instante de abertura deve "
        "usar Δt compatível com a resolução angular pretendida."
    ),
    "emt_linear_components_only": (
        "Todos os ramos são LINEARES e invariantes no tempo. Não há saturação "
        "magnética, histerese, perdas no ferro, para-raios de óxido metálico "
        "nem resistência de arco dependente da corrente. O transformador é "
        "representado apenas pela impedância de dispersão (CoupledRL), sem "
        "capacitância entre enrolamentos — que é o caminho dominante de "
        "transferência de surto de frente rápida."
    ),
    "emt_dense_lu_no_sparsity": (
        "A matriz MNA é DENSA e a fatoração LU é de Doolittle com pivotamento "
        "parcial em numpy puro, custo O(n³) por topologia e O(n²) por passo. "
        "Não há ordenação de esparsidade nem fatoração esparsa; o desempenho "
        "degrada como n³ e o kernel destina-se a redes de dezenas — não "
        "milhares — de nós, que é a escala do estudo de manobra de um "
        "alimentador de motor."
    ),
    "emt_cda_only_on_topology_change": (
        "O amortecimento crítico (dois meios-passos de Euler regressivo) é "
        "disparado por MUDANÇA DE ESTADO DE CHAVE. Descontinuidades de outra "
        "origem — degrau imposto por uma fonte, condição inicial "
        "inconsistente — não o disparam automaticamente e podem produzir "
        "oscilação numérica trapezoidal residual."
    ),
}
