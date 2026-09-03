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
* linha/cabo com **dependência de frequência** pelo método de Martí
  (``JMartiLine``), com ajuste racional por *vector fitting* a partir de
  tabelas amostradas de ``Z_c(ω)`` e ``A(ω)``, convolução recursiva por
  polo e decomposição modal com matriz real e constante — mesma
  interface de componente do Bergeron;
* **amortecimento crítico (CDA)** por dois meios-passos de Euler
  regressivo após cada manobra — indispensável para que a interrupção
  de corrente indutiva não gere oscilação numérica de período ``2Δt``;
* **partida em regime permanente senoidal** por solução fasorial
  (``Solver(init="steady_state")``), com semeadura coerente dos termos
  históricos e do histórico de trânsito das linhas — equivalente do
  ``TSTART`` negativo do cartão de fonte do ATP;
* critério de comutação por **margem de corrente** ``Imar``, com o nome
  e o significado do campo do cartão de chave do ATP;
* cache de fatoração LU indexado por assinatura de topologia;
* sondas que alimentam
  :func:`app.postprocessor.prognosis.stress_profile.extract_stress_events`.

Referências principais
=======================

Fontes primárias contra as quais o kernel foi conferido equação a
equação (ver as docstrings de ``components.py``, ``circuit.py`` e
``line.py`` para a correspondência item a item):

* [FONTE: H. W. Dommel, "Digital computer solution of electromagnetic
  transients in single- and multiphase networks", *IEEE Transactions on
  Power Apparatus and Systems*, vol. PAS-88, n. 4, pp. 388-399, abr.
  1969, doi:10.1109/TPAS.1969.292459] — eqs. (7a)/(7b), (9a)/(9b),
  (10a)/(10b), (11), (12)-(13), (17a)/(17b) e Apêndice I.
* [FONTE: C.-W. Ho, A. E. Ruehli, P. A. Brennan, "The modified nodal
  approach to network analysis", *IEEE Transactions on Circuits and
  Systems*, vol. CAS-22, n. 6, pp. 504-509, jun. 1975] — eq. (2) e
  Tabela I.
* [FONTE: J. Lin, J. R. Martí, "Implementation of the CDA procedure in
  the EMTP", *IEEE Transactions on Power Systems*, vol. 5, n. 2,
  pp. 394-402, maio 1990] — §2 e eqs. (2)-(4).
* [FONTE: H. W. Dommel, "Nonlinear and time-varying elements in digital
  simulation of electromagnetic transients", *IEEE Transactions on
  Power Apparatus and Systems*, vol. PAS-90, pp. 2561-2567, 1971] —
  §III e §V.
* [FONTE: J. Mahseredjian, S. Dennetière, L. Dubé, B. Khodabakhchian,
  L. Gérin-Lajoie, "On a new approach for the simulation of transients
  in power systems", *Electric Power Systems Research* 77 (2007)
  1514-1520] — §2, eq. (2).
* [LITERATURA: J. R. Marti e J. Lin, "Suppression of numerical
  oscillations in the EMTP", *IEEE Transactions on Power Systems*,
  vol. 4, n. 2, pp. 739-747, maio 1989, doi:10.1109/59.193849] —
  conceito original do CDA.
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

Partida em regime permanente
=============================

::

    ckt = Circuit("rl")
    ckt.add(VoltageSource("E", "1", "gnd", amplitude_V=100.0,
                          frequency_Hz=60.0, phase_reference="cos"))
    ckt.add(Resistor("R", "1", "2", 0.5))
    ckt.add(Inductor("L", "2", "gnd", 25.0e-3))

    solver = Solver(ckt, dt=1.0e-6, init="steady_state")
    solver.run(t_end=50.0e-3)
    fasor = solver.steady_state_solution   # PhasorSolution, para auditoria

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
from app.simulation.emt.jmarti import (
    DEFAULT_FIT_ITERATIONS,
    DEFAULT_FIT_TOLERANCE,
    DELAY_METHODS,
    EPSILON_0,
    FIT_WEIGHTS,
    JMARTI_LIMITATIONS,
    JMartiError,
    JMartiLine,
    LineDataError,
    LineFrequencyData,
    MU_0,
    ModalJMartiLine,
    ModalLineModel,
    ModalTransform,
    RationalFit,
    RationalFitError,
    clarke_transform,
    estimate_time_delay,
    frequency_grid,
    frequency_grid_for_delay,
    initial_poles,
    minimum_phase_angle,
    vector_fit,
)
from app.simulation.emt.line import BergeronLine, surge_impedance, travel_time
from app.simulation.emt.steady_state import (
    INIT_MODES,
    INIT_STEADY_STATE,
    INIT_ZERO,
    MultipleFrequenciesError,
    PhasorSolution,
    SteadyStateError,
    UnsupportedComponentError,
    assemble_phasor_system,
    initialize_steady_state,
    instantaneous,
    seed_from_phasor,
    solve_phasor,
    source_frequency,
    source_phasor,
)
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
    # regime permanente senoidal
    "INIT_ZERO",
    "INIT_STEADY_STATE",
    "INIT_MODES",
    "SteadyStateError",
    "MultipleFrequenciesError",
    "UnsupportedComponentError",
    "PhasorSolution",
    "solve_phasor",
    "seed_from_phasor",
    "initialize_steady_state",
    "assemble_phasor_system",
    "source_frequency",
    "source_phasor",
    "instantaneous",
    # linha a parâmetros constantes
    "BergeronLine",
    "surge_impedance",
    "travel_time",
    # linha dependente da frequência (JMarti)
    "JMartiLine",
    "ModalJMartiLine",
    "ModalTransform",
    "clarke_transform",
    "ModalLineModel",
    "LineFrequencyData",
    "RationalFit",
    "vector_fit",
    "initial_poles",
    "minimum_phase_angle",
    "estimate_time_delay",
    "frequency_grid",
    "frequency_grid_for_delay",
    "JMartiError",
    "LineDataError",
    "RationalFitError",
    "DEFAULT_FIT_TOLERANCE",
    "DEFAULT_FIT_ITERATIONS",
    "FIT_WEIGHTS",
    "DELAY_METHODS",
    "MU_0",
    "EPSILON_0",
    "JMARTI_LIMITATIONS",
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
    "emt_steady_state_single_frequency": (
        "A inicialização em regime permanente senoidal (Solver(init="
        "'steady_state')) resolve UMA ÚNICA frequência. O sistema MNA "
        "complexo é montado em um só ω, com Z_L = jωL e Z_C = 1/(jωC), e os "
        "históricos são semeados por I_L(0) = i_L(0) + G_L·v_L(0) e "
        "I_C(0) = −[G_C·v_C(0) + i_C(0)] [Dommel 1969, Apêndice I, p. 395; "
        "Lista 02, eq. (6)]. NÃO há superposição de harmônicos nem solução do "
        "ponto de operação em corrente contínua: fontes em frequências "
        "distintas, ou com dc_offset_V não nulo, levantam "
        "MultipleFrequenciesError em vez de produzir semeadura errada. "
        "Circuitos com componente contínua devem usar init='zero' com janela "
        "de acomodação. A semeadura também pressupõe REDE LINEAR na topologia "
        "corrente das chaves — coerente com emt_linear_components_only."
    ),
    "emt_steady_state_residual_deviation": (
        "A semeadura usa fasores CONTÍNUOS (jωL, 1/jωC), enquanto o ponto "
        "fixo exato da recursão trapezoidal tem impedância indutiva "
        "j·(2L/Δt)·tg(ωΔt/2) — a rede discreta responde como a contínua em "
        "ω_ef = (2/Δt)·tg(ωΔt/2). Resta, portanto, um desvio PERMANENTE de "
        "amplitude constante (não um transitório que decaia), de ordem "
        "relativa (ωΔt)²/12: no RL série de referência (0,5 Ω, 25 mH, 60 Hz) "
        "com Δt = 1 µs mede-se 1,36e−7 A sobre 4,43 A, caindo por 4 a cada "
        "divisão de Δt por 2 [CÁLCULO PRÓPRIO, tests/test_emt_steady_state.py]. "
        "Em saídas pouco sensíveis a ω o cancelamento o reduz muito mais — "
        "1,39e−10 V no circuito da Questão 2 da Lista 02 [Lista 02, Tabela 3]. "
        "Com passo grosseiro em relação ao período da fonte o resíduo deixa de "
        "ser desprezível. Além disso NÃO se registra amostra em t = 0 — a "
        "primeira amostra da série continua sendo a de t = Δt —, embora o "
        "vetor de estado em t = 0 já seja o do regime permanente e os "
        "controladores o enxerguem."
    ),
    "emt_steady_state_line_interpolation": (
        "Na linha de Bergeron a semeadura preenche o buffer de trânsito com a "
        "onda de regime amostrada em 0, −Δt, …, −(τ + 2Δt), como exige "
        "[Dommel 1969, Apêndice I, p. 395]. A admitância fasorial usada é a "
        "do PRÓPRIO modelo discreto (operador de atraso e^{−jωτ}, fator ζ e "
        "perdas concentradas R/4, R/2, R/4), não a da linha ideal; ainda "
        "assim resta o erro da INTERPOLAÇÃO LINEAR do histórico quando τ não "
        "é múltiplo inteiro de Δt, que aparece como transitório residual de "
        "ordem (ωΔt)² nos primeiros τ/Δt passos. Em ωτ múltiplo de π (linha "
        "em meia onda) sem perdas o sistema fasorial é singular e a "
        "inicialização levanta SteadyStateError."
    ),
    "emt_cda_residual_in_stiff_networks": (
        "Um único passo de CDA (o padrão do ATP, cda_full_steps=1) reduz o "
        "artefato trapezoidal por um fator da ordem de (1 + R·Δt/2L)², mas não "
        "o anula: em rede muito rígida após o evento — constante de tempo "
        "residual muito menor que Δt, caso da interrupção contra resistência "
        "de fuga elevada e SEM snubber — pode restar oscilação da ordem de "
        "dezenas de vezes o valor de regime. [CÁLCULO PRÓPRIO: L = 1 mH, "
        "R_p = 100 kΩ, Δt = 1 µs — resíduo de 36x o regime com 1 passo, 1,01x "
        "com 2 passos.] cda_full_steps=2 mitiga, MAS É EXTENSÃO NÃO "
        "PUBLICADA: Lin & Martí 1990, §2, p. 394, prescrevem exatamente um "
        "par de meios-passos de Δt/2 por descontinuidade, e o único caso em "
        "que a fonte admite meios-passos adicionais (§4, p. 395) é a mudança "
        "de segmento de indutância linear por partes, que não existe neste "
        "kernel. Declare o uso no laudo."
    ),
    "emt_cda_half_step_not_recorded": (
        "Por padrão as sondas registram apenas os instantes de passo COMPLETO; "
        "as amostras internas dos meios-passos do CDA são descartadas para "
        "manter a base de tempo uniforme. Como o maior valor instantâneo logo "
        "após uma interrupção pode cair DENTRO do par de meios-passos, o V_pk "
        "registrado pode subestimar o valor calculado pelo próprio solver. O "
        "caminho CORRETO para resolver o pico é REDUZIR Δt: Lin & Martí 1990, "
        "§2, p. 394, são explícitos em que os resultados em t+Δt/2 são "
        "'apenas quantidades matemáticas usadas pelo procedimento CDA, sem "
        "significado físico'. Solver(record_half_steps=True) existe para "
        "ensaio numérico e injeta esse ponto sem significado físico na série "
        "de saída e no vetor de estresse; emite WARNING quando ativado."
    ),
    "emt_constant_parameter_line": (
        "A linha/cabo de app/simulation/emt/line.py (BergeronLine) é de "
        "PARÂMETROS CONSTANTES: o efeito pelicular e o retorno pela terra, que "
        "atenuam e deformam a frente real, não são reproduzidos, a frente "
        "chega à outra extremidade praticamente sem atenuação e os valores de "
        "V_pk e dv/dt daí extraídos são COTA SUPERIOR do estresse real. O "
        "modelo DEPENDENTE DA FREQUÊNCIA existe desde "
        "app/simulation/emt/jmarti.py (JMartiLine, método de Martí 1982) e "
        "tem a mesma interface de componente, de modo que a escolha é de "
        "quem monta o caso — e deve ser declarada no laudo. As limitações "
        "próprias do modelo JMarti estão nas chaves com prefixo emt_jmarti_."
    ),
    "emt_single_mode_line": (
        "O componente PADRÃO de linha é um ramo MONOFÁSICO independente, nos "
        "DOIS modelos. O acoplamento mútuo entre condutores de um mesmo cabo "
        "tripolar só é representado por ModalJMartiLine, que exige do usuário "
        "a matriz de transformação modal real e um modelo por modo; sem "
        "esses dados, a dispersão entre modos aéreo e de terra — e o "
        "consequente espalhamento temporal entre fases — está ausente."
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
        "Os ramos ESTAMPADOS na matriz são lineares e invariantes no tempo. "
        "Não há saturação magnética, histerese, perdas no ferro nem "
        "resistência de arco dependente da corrente. O transformador é "
        "representado apenas pela impedância de dispersão (CoupledRL), sem "
        "capacitância entre enrolamentos — que é o caminho dominante de "
        "transferência de surto de frente rápida. RESSALVA: elementos não "
        "lineares existem FORA da matriz, por compensação "
        "(app.simulation.emt.nonlinear, Dommel 1971 §V), e o para-raios de "
        "óxido metálico está implementado sobre esse mecanismo "
        "(app.simulation.emt.arrester); a saturação de transformador, não."
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
        "origem — degrau imposto por uma fonte no meio da simulação — não o "
        "disparam automaticamente e podem produzir oscilação numérica "
        "trapezoidal residual, ao contrário do previsto em Lin & Martí 1990, "
        "§2, p. 394, que lista entre as descontinuidades os 'saltos no valor "
        "das fontes aplicadas'. A descontinuidade em t = 0 É tratada "
        "(Solver(cda_at_start=True), padrão), e deve ser desligada na partida "
        "em regime permanente, quando não existe descontinuidade nesse "
        "instante."
    ),
}

# As limitações próprias do modelo dependente da frequência vivem em
# app/simulation/emt/jmarti.py e são agregadas aqui para que o laudo tenha
# UM catálogo só. Colisão de chave é erro de programação e deve estourar.
for _key, _text in JMARTI_LIMITATIONS.items():
    if _key in KNOWN_LIMITATIONS:  # pragma: no cover - defensivo
        raise RuntimeError(
            f"colisão de chave no catálogo de limitações do kernel EMT: {_key!r}"
        )
    KNOWN_LIMITATIONS[_key] = _text
del _key, _text
