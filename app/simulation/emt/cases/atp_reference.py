"""
app.simulation.emt.cases.atp_reference — o caso do arquivo ATP ancorado no
motor de transitórios dedicado, SEM decodificar a matriz do transformador.

Motivação
=========

O caso de manobra que serve de referência a este projeto está descrito em
dois arquivos de dados do ATP — ``trt_all_motors_dt_ea.atp`` (sem ramo
amortecedor) e ``trt_all_motors_com_snubber_2026-04.atp`` (com ramo
amortecedor) — e a especificação já extraída deles está em
``docs/research/rul_isolamento/06_CASO_BASE_ATP_ESPECIFICACAO.md``. Um
único bloco daqueles arquivos permanece indecifrado: a matriz acoplada
6×6 do transformador sob a opção ``USE AR``, cuja semântica de colunas
não pôde ser lida com segurança [FATO: especificação, §4].

Este módulo NÃO adivinha aquela matriz. Ele obtém, da própria solução
fasorial impressa na listagem de saída do ATP
(``tests/fixtures/atp/referencia_regime_permanente.json``), o
**equivalente de Thévenin** da rede a montante, e monta o restante do
circuito exatamente como está nos cartões. O que estava indecifrado deixa
de ser necessário: a rede a montante entra pelo que ela FAZ nos terminais,
medido pelo próprio programa que gerou a referência.

Topologia do arquivo (variante com amortecedor, que é a da listagem)
====================================================================

Atenção à nomenclatura: na variante com amortecedor os rótulos ``X0001``
e ``X0002`` estão TROCADOS em relação à variante base — ``X0001`` é o
lado FONTE do disjuntor e ``X0002`` o lado CARGA [FATO: arquivo,
comparação cartão a cartão dos dois arquivos]. A listagem de referência é
a da variante com amortecedor, de modo que é essa a nomenclatura adotada
aqui::

    X0030 (fonte)  ─[ramo acoplado]─  X0028 (triângulo)
                        ║ matriz 6×6 INDECIFRADA
    XX0003 (estrela) ─[12,009 Ω]─ terra
    X0029x ─[1138,5235 Ω]─ XX0003                (ramo de magnetização)
    X0029x ─[linha JMarti]─ X0001x               (lado fonte do disjuntor)
    X0001x ─[disjuntor]─ X0002x                  (lado carga; barramento)
    X0002x ─[cabo Bergeron modal]─ 01ATx
    01ATx  ─[0,691 Ω + 8,9795 mH]─ terra         (motor, rotor bloqueado)
    X0002x ─[válvulas ‖]─ XX003x ─[30 Ω]─ terra  (ramo amortecedor)

Convenção dos fasores da listagem
=================================

Módulos de PICO, ângulos em graus, referência cosseno:
``x(t) = Re{X̂·e^{jωt}}`` com ``X̂ = |X|·e^{jθ}``. As duas convenções de
sinal das correntes publicadas foram determinadas por verificação
numérica, não por suposição:

* ``01ATx->TERRA``: o fasor publicado é o SIMÉTRICO da corrente que entra
  no ramo do motor pelo nó ``01ATx``. Verificação: ``|V̂|/|Ẑ_mot|``
  reproduz o módulo publicado com erro relativo < 1·10⁻⁹ e o ângulo
  difere de exatamente 180,0000° nas três fases [CÁLCULO PRÓPRIO].
* ``X0001x->XX00yy``: o fasor publicado é a corrente no sentido de
  JUSANTE (do lado fonte para o lado carga do disjuntor). Verificação: só
  com esse sinal a potência ativa que entra no cabo (929 592,9 W) é MAIOR
  que a que chega ao motor (867 077,8 W), com diferença de 62 515 W igual
  à perda série do cabo calculada de sua própria matriz (62 520,6 W)
  [CÁLCULO PRÓPRIO].

Dedução do equivalente — a álgebra por extenso
==============================================

**Passo 1 — forma do equivalente.** A fonte do arquivo é rigorosamente
equilibrada: 11 718,4337 V de pico em 0°, +120° e −120°
[FATO: arquivo, cartões tipo 14]. A matriz 6×6 do transformador, embora
indecifrada quanto ao significado das colunas, é estruturalmente
SIMÉTRICA: as linhas 1, 3 e 5 repetem o par diagonal
(89,372025111517 / 0,23393805061224), as linhas 2, 4 e 6 repetem
(2950,6630273902 / 0,00708611343774) e os termos fora da diagonal
repetem (−513,5089081617) e (−0,0857730263145)
[FATO: arquivo, bloco ``$VINTAGE, 1,`` / ``USE AR``]. Logo a rede a
montante do nó ``X0029`` é um trifásico EQUILIBRADO, e seu equivalente
tem a forma "três f.e.m. equilibradas atrás de uma impedância própria
``Z₁`` por fase, com ponto estrela aterrado por ``Z_n``".

Isso **não** impõe simetria à solução: o desequilíbrio observado nas
tensões (3386,4 / 3462,5 / 3397,0 V de pico) é produzido a JUSANTE, pelo
cabo não transposto, e o equivalente por fase resultante
(``Ê_k − Z₁·Î_k − Z_n·ΣÎ``) é diferente em cada fase porque as correntes
são diferentes. A verificação está em
:func:`AtpReferenceModel.phasor_validation`, que confronta fase a fase.

**Passo 2 — o que é conhecido.** Do arquivo tomam-se dois valores que NÃO
dependem da matriz indecifrada: o resistor de aterramento de neutro
``R_n = 12,009 Ω`` entre ``XX0003`` e a terra e o ramo de magnetização
``R_mag = 1138,5235091065 Ω`` de cada fase de ``X0029`` a ``XX0003``
[FATO: arquivo, cartões do bloco ``/BRANCH``].

**Passo 3 — correntes.** A corrente de linha publicada ``Î_k`` é a do
disjuntor. A corrente do ramo de magnetização sai da própria listagem::

    Î_mag,k = (V̂29_k − V̂_XX0003) / R_mag        ≈ 3,00 A de pico

e a corrente do enrolamento é ``Î_w,k = Î_k + Î_mag,k``. A corrente do
resistor de neutro é ``ΣÎ_k`` (a de magnetização circula entre ``X0029``
e ``XX0003`` e não passa pelo neutro), o que a própria listagem confirma:
``−R_n·ΣÎ_k`` vale 49,025 V contra os 49,026 V publicados em ``XX0003``,
erro relativo de 2·10⁻⁵ [CÁLCULO PRÓPRIO].

**Passo 4 — sistema.** Com ``α = (1, e^{+j120°}, e^{−j120°})``, a
sequência da própria fonte, e ``V̂_N = −R_n·ΣÎ``::

    V̂29_k − V̂_N = Ê·α_k − Z₁·Î_w,k        k = a, b, c

São TRÊS equações complexas em DUAS incógnitas complexas ``(Ê, Z₁)``. O
sistema é sobredeterminado de propósito: resolve-se por mínimos
quadrados e o RESÍDUO é o teste da hipótese de equilíbrio do passo 1.

**Passo 5 — resultado e conferências independentes.**

======================================  ==========================
Grandeza                                 Valor
======================================  ==========================
``Ê`` (fase a)                           3532,1077 V ∠ 30,0007°
``Z₁``                                   0,0142332 + j0,1276920 Ω
``L₁``                                   0,338714 mH
Resíduo dos mínimos quadrados            2,9·10⁻⁴ V (1·10⁻⁷ relativo)
======================================  ==========================

1. O ângulo de ``Ê`` é 30,0007°, isto é, a defasagem de 30° do
   transformador Δ–Y [INFERÊNCIA FÍSICA].
2. ``|Ê| / |V̂_fonte| = 0,3014147`` contra ``4160/13800 = 0,3014493`` da
   relação de espiras nominal — desvio de 1,1·10⁻⁴ [CÁLCULO PRÓPRIO].
3. Resolvendo em vez disso o sistema exatamente determinado de TRÊS
   incógnitas ``(Ê, Z₁, Z_m)``, em que ``Z_m`` é o termo mútuo comum às
   três fases, obtém-se ``Z_m = 12,009204 + j0,010599 Ω`` — o resistor de
   neutro de 12,009 Ω do cartão, recuperado com desvio de 1,7·10⁻⁵ sem
   ter sido informado. É a confirmação independente mais forte do
   método (:func:`derive_thevenin` com ``use_card_neutral=False``).
4. ``Z₀ = Z₁ + 3·Z_m = 36,0419 + j0,1595 Ω``; descontados os
   ``3·12,009 Ω`` do neutro sobra ``0,0149 + j0,1276 Ω ≈ Z₁``, isto é, o
   transformador tem impedância de sequência zero igual à direta — o que
   se espera de uma unidade Δ–Yaterrado [INFERÊNCIA FÍSICA].
5. Fechamento de potência: motor 867 077,8 + cabo 62 520,6 + ligação
   34 106,9 + ``Z₁`` 17 877,3 + neutro 100,1 + magnetização 15 365,9 =
   **997 048,6 W** contra os **997 130,9 W** da listagem — 0,0083%
   [CÁLCULO PRÓPRIO]. Os 82 W restantes são do ramo fonte–triângulo
   (0,00125 Ω por fase no nível de 13,8 kV) e das perdas transversais da
   linha a montante, nenhum dos dois representado aqui.

**Passo 6 — ligação X0029 → X0001.** A linha a montante (modelo JMarti,
cujos polos e resíduos estão no arquivo) é substituída por sua impedância
equivalente por fase em 60 Hz, extraída da própria solução fasorial::

    Z_link,k = (V̂29_k − V̂02_k) / Î_k

(usa-se ``V̂02`` porque a chave do disjuntor está FECHADA e ideal na
solução fasorial, de modo que ``V̂01 = V̂02``; o ramo de arco tipo 91 é
resistência variável no tempo e a listagem declara que essas são
ignoradas na solução fasorial [FATO: listagem, avisos]). Os três valores
são 0,004944+j0,058477, 0,028182+j0,042744 e 0,048632+j0,040239 Ω — R e L
positivos nas três fases, e FRANCAMENTE desiguais, como manda uma linha
não transposta. **Substituição declarada**: a dependência de frequência
da linha a montante NÃO é representada (limitação
``emt_atp_ref_upstream_lumped``).

Cabo a jusante — decodificação do cartão de comprimento negativo
================================================================

O cartão é, por modo::

    -1X0002A01ATA               0.04901436 46.99493446 93424.65873         -1. 1  30

**[HIPÓTESE]** de leitura dos campos sob comprimento negativo: ``R`` é a
resistência série TOTAL [Ω], ``A`` é a impedância de surto ``Z_c`` [Ω],
``B`` é a velocidade de propagação [unidade de comprimento por segundo] e
``|ℓ| = 1`` unidade. Daí ``τ_μ = 1/B_μ``, ``L'_μ = A_μ/B_μ`` e
``C'_μ = 1/(A_μ·B_μ)``.

**A hipótese foi CONFIRMADA pela própria solução fasorial**, e por isso a
substituição por impedância concentrada prevista como alternativa NÃO foi
necessária. Com a matriz de transformação modal punçada no arquivo, a
impedância série de fase em 60 Hz
``Z_ph = (T_i^T)^{-1}·diag(R + jωL)·T_i^{-1}`` reproduz a queda publicada
``V̂02 − V̂01AT`` com erro relativo de **1,0·10⁻⁶** nas três fases, usando
a média entre a corrente de entrada e a de saída — que é o que o
quadripolo π/Bergeron entrega quando ``ωτ ≪ 1`` [CÁLCULO PRÓPRIO]. A
corrente transversal publicada (``Î_ent − Î_mot``, de 0,16 a 0,28 A) é
reproduzida dentro de 5% por ``jωC_ph`` do mesmo cartão.

Em unidades de engenharia os modos valem 0,503 / 0,672 / 6,194 mH e
0,2278 / 0,0679 / 0,0064 µF por unidade de comprimento — valores de cabo
de média tensão POR QUILÔMETRO, do que se infere que a unidade do cartão
é o quilômetro e o cabo tem 1 km [INFERÊNCIA FÍSICA].

Matriz de transformação real × complexa
---------------------------------------

O arquivo punça uma matriz de transformação COMPLEXA (seis linhas
alternando parte real e imaginária). A solução fasorial do ATP usa a
matriz complexa — é o que o teste de 1,0·10⁻⁶ acima demonstra. Mas o
modelo de Bergeron no domínio do tempo só admite transformação REAL, e é
com ``T_r = Re(T_i)`` que este módulo trabalha, nas duas frentes (marcha
no tempo e estampagem fasorial), para que a semeadura de regime seja
consistente com o modelo integrado e não haja transitório espúrio de
partida.

A diferença entre as duas leituras é EXCLUSIVAMENTE de sequência zero:
``Z_ph(T_i) − Z_ph(T_r)`` tem os nove elementos praticamente iguais a
0,205 + j0,028 Ω, ou seja, ``ΔZ₀ = 0,636 + j0,095 Ω`` e um acoplamento
zero–direta ``ΔZ₀₁ = 0,0116 Ω``. Como a corrente direta é de 914 A, esse
acoplamento produz ≈ 10 V de queda de sequência zero A MAIS no cabo. A
corrente de carga é imposta pela impedância do motor, de modo que os
10 V não aparecem em ``01AT`` nem nas correntes: aparecem INTEGRALMENTE
nos nós a montante do cabo [CÁLCULO PRÓPRIO].

E há um fato que fecha a questão: ``Re[Z_ph(T_i)]`` tem autovalor
**−0,513 Ω** — a leitura complexa é NÃO PASSIVA em sequência zero.
Nenhum modelo fisicamente realizável reproduz exatamente a solução
fasorial do ATP; o resíduo declarado é, portanto, cota inferior do desvio
de qualquer modelo passivo, e não deficiência deste.

Resultado da validação e atribuição do resíduo
==============================================

Os números abaixo saem de :meth:`AtpReferenceModel.phasor_validation` e
são o critério declarado dos testes. ``cable_phasor_reading`` escolhe a
matriz da estampagem FASORIAL do cabo; a marcha no tempo usa sempre a
real.

===========================  ==================  ==================
Grandeza                     leitura ``"real"``  leitura ``"complexa"``
===========================  ==================  ==================
``01AT`` (3 tensões)         0,026 a 0,063%      ≤ 0,00014%
Correntes (6)                0,026 a 0,063%      ≤ 0,00014%
``X0029``/``X0002`` (6)      0,287 a 0,300%      ≤ 0,00021%
``XX0003`` (neutro, 49 V)    20,3% (9,97 V)      0,0136%
Perda total da rede          0,111%              0,0088%
Desvio da marcha em 5 ciclos 2,0 mV              3,24 V
===========================  ==================  ==================

A leitura da coluna direita é a demonstração de que **o equivalente, o
cabo, a ligação e o motor estão todos certos**: com a MESMA matriz que o
ATP usa, o desvio de TODAS as treze tensões e das seis correntes cai para
6,7·10⁻³ V e 1,2·10⁻³ A — que é o resíduo dos mínimos quadrados do passo
4 propagado pela rede, e nada mais. O resíduo da coluna esquerda é,
portanto, atribuído inteiramente à leitura da matriz de transformação, e
é uniforme: 9,94 a 10,01 V nos seis nós a montante do cabo e 9,97 V no
neutro, isto é, o MESMO fasor de sequência zero.

O padrão é a leitura real, porque ela mantém a semeadura coerente com o
modelo integrado: a marcha no tempo com o disjuntor fechado se afasta da
onda fasorial em **2,0 mV** ao longo de cinco ciclos (6,4·10⁻⁷ relativo),
contra **3,24 V** da leitura complexa, que é a incoerência do próprio ATP
tornada visível.

Convenções de rótulo de evidência
=================================

``[FATO: arquivo]`` — lido dos cartões; ``[FATO: listagem]`` — impresso
na saída do ATP; ``[CÁLCULO PRÓPRIO]`` — obtido aqui a partir daqueles;
``[INFERÊNCIA FÍSICA]``; ``[HIPÓTESE]``.

Sem I/O de rede, sem GUI.
"""

from __future__ import annotations

import cmath
import json
import math
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Sequence

import numpy as np

from app.simulation.emt.circuit import Circuit, Solver, SolverResult
from app.simulation.emt.components import (
    GROUND_INDEX,
    Capacitor,
    Component,
    Inductor,
    Resistor,
    Switch,
    node_voltage,
    three_phase_voltage_sources,
)
from app.simulation.emt.line import _TravelHistory
from app.simulation.emt.probes import (
    BranchCurrentProbe,
    DifferentialVoltageProbe,
    NodeVoltageProbe,
)
from app.simulation.emt.arrester import three_phase_arrester
from app.simulation.emt.flashover import three_phase_flashover
from app.simulation.emt.snubber import (
    SnubberBranch,
    SnubberMasterTrigger,
    three_phase_atp_literal_snubber,
    three_phase_snubber,
)
from app.simulation.emt.vcb import (
    ATP_ZERO_ORDER_DEFERRED,
    ATP_ZERO_ORDER_LITERAL,
    ATP_ZERO_ORDERS,
    DIDT_INTERRUPT_ABOVE,
    STATE_ARCING,
    STATE_ARCING_HF,
    AtpLiteralPole,
    AtpVcbParameters,
    ParabolicRecovery,
    VacuumCircuitBreakerModel,
    build_atp_literal_pole,
)
from app.core.logging_config import get_logger

log = get_logger(__name__)


# ---------------------------------------------------------------------------
# Constantes do caso — todas [FATO: arquivo] ou [FATO: listagem]
# ---------------------------------------------------------------------------

#: Caminho padrão da solução fasorial extraída da listagem do ATP.
REFERENCE_JSON_PATH: Path = (
    Path(__file__).resolve().parents[4]
    / "tests"
    / "fixtures"
    / "atp"
    / "referencia_regime_permanente.json"
)

#: Rótulos de fase usados nos dicionários deste módulo.
PHASES: tuple[str, str, str] = ("a", "b", "c")

#: Sufixos das fases nos nós do arquivo ATP.
PHASE_SUFFIX: tuple[str, str, str] = ("A", "B", "C")

#: Frequência de potência [Hz] [FATO: arquivo, cartão ``POWER FREQUENCY``].
FREQUENCY_HZ: float = 60.0

#: Passo de integração [s] [FATO: arquivo, cartão de dados diversos].
DT_S: float = 1.0e-6

#: Janela simulada [s] [FATO: arquivo, ``Tmax = .045``].
T_END_S: float = 0.045

#: Resistor de aterramento de neutro [Ω] [FATO: arquivo, ``XX0003 12.009``].
NEUTRAL_RESISTANCE_OHM: float = 12.009

#: Ramo de magnetização por fase, de ``X0029`` a ``XX0003`` [Ω]
#: [FATO: arquivo, matriz diagonal 1138.5235091065].
MAGNETIZING_RESISTANCE_OHM: float = 1138.5235091065

#: Motor de rotor bloqueado por fase [FATO: arquivo, ``01ATx .691 8.9795``].
MOTOR_RESISTANCE_OHM: float = 0.691
MOTOR_INDUCTANCE_H: float = 8.9795e-3

#: Amplitude da fonte do arquivo [V de pico] [FATO: arquivo, cartões tipo 14].
SOURCE_PEAK_V: float = 11718.4337

#: Impedância de surto modal do cabo a jusante [Ω] [FATO: arquivo, campo ``A``].
CABLE_MODAL_SURGE_OHM: tuple[float, float, float] = (
    46.99493446,
    99.49766584,
    986.1619784,
)

#: Velocidade de propagação modal [unidade de comprimento/s]
#: [FATO: arquivo, campo ``B``].
CABLE_MODAL_VELOCITY: tuple[float, float, float] = (
    93424.65873,
    148124.6884,
    159217.6316,
)

#: Resistência série TOTAL por modo [Ω] [FATO: arquivo, campo ``R``].
CABLE_MODAL_RESISTANCE_OHM: tuple[float, float, float] = (
    0.04901436,
    0.049182478,
    0.119786581,
)

#: Comprimento do cartão, em módulo [unidades] [FATO: arquivo, campo ``-1.``].
CABLE_LENGTH_UNITS: float = 1.0

#: Matriz de transformação modal punçada (corrente), linhas alternando parte
#: real e imaginária no arquivo [FATO: arquivo, seis linhas após os modos].
CABLE_TI_COMPLEX: np.ndarray = np.array(
    [
        [
            -0.4280586 - 0.0047707j,
            -0.70710678 - 1.28e-16j,
            0.54034857 - 0.11857294j,
        ],
        [
            0.795918429 + 2.84046e-17j,
            -4.4031e-17 - 1.6746e-17j,
            0.622838473 - 1.0263e-17j,
        ],
        [
            -0.4280586 - 0.0047707j,
            0.707106781 - 8.0896e-18j,
            0.54034857 - 0.11857294j,
        ],
    ],
    dtype=complex,
)

#: Instantes de separação dos contatos por polo [s]
#: [FATO: arquivo, ``T_OPENr/s/t``].
VCB_SEPARATION_TIME_S: tuple[float, float, float] = (0.01455, 0.02475, 0.02481)

#: Corrente de corte por polo [A] [FATO: arquivo, ``I_CHOPr/s/t``] — valores
#: FIXOS e distintos por polo, não faixa de amostragem.
VCB_CHOPPING_CURRENT_A: tuple[float, float, float] = (1.0, 2.0, 2.0)

#: Capacidade de extinção de alta frequência por polo [A/µs]
#: [FATO: arquivo, ``DIDT_CRITr/s/t``].
VCB_DIDT_CAPABILITY_A_PER_US: tuple[float, float, float] = (5.0, 15.0, 15.0)

#: Lei de recuperação dielétrica ``V_wth = A·t + B·t²`` (kV, t em ms)
#: [FATO: arquivo, ``RRDS_A`` e ``RRDS_B`` iguais nos três polos].
VCB_RRDS_A_KV_PER_MS: float = 0.801
VCB_RRDS_B_KV_PER_MS2: float = 1.226

#: Fator de reignição do MODEL: reignita com ``|V_gap| > V_wth·1,1``
#: [FATO: arquivo, código do MODEL ``VCB_R*``].
VCB_REIGNITION_FACTOR: float = 1.1

#: Resistência do ramo de arco [Ω] e de aberto [Ω], e capacitância de aberto
#: [F] [FATO: arquivo, ``RARC``, ``ROPEN``, ``COPEN`` com ``COPT = 0`` ⇒ µF].
VCB_ARC_RESISTANCE_OHM: float = 20.0
VCB_OPEN_RESISTANCE_OHM: float = 1.0e6
VCB_OPEN_CAPACITANCE_F: float = 6.0e-6

#: Ramo amortecedor: resistor por fase [Ω] [FATO: arquivo, cartões de 30.].
SNUBBER_RESISTANCE_OHM: float = 30.0

#: Tensão de disparo e corrente de manutenção das válvulas
#: [FATO: listagem, "Valve. 2.404E+03 1.000E+00 0.000E+00"].
SNUBBER_BREAKOVER_V: float = 2404.0
SNUBBER_HOLDING_CURRENT_A: float = 1.0

#: Perda total da rede impressa pela listagem [W] [FATO: listagem].
TOTAL_NETWORK_LOSS_W: float = 997130.9256266


# ---------------------------------------------------------------------------
# Leitura da referência
# ---------------------------------------------------------------------------


def _phasor(magnitude: float, angle_deg: float) -> complex:
    """Fasor de amplitude com referência cosseno: ``|X|·e^{jθ}``."""
    return float(magnitude) * cmath.exp(1j * math.radians(float(angle_deg)))


@dataclass(frozen=True)
class AtpReference:
    """Solução fasorial da listagem do ATP, já convertida em fasores.

    Attributes
    ----------
    frequency_Hz:
        Frequência da solução [Hz].
    sources:
        Fasores das fontes ideais por nó (``X0030A`` etc.) [V de pico].
    node_voltages:
        Fasores de tensão nodal por nó [V de pico].
    branch_currents:
        Fasores de corrente de ramo, COMO PUBLICADOS — as convenções de
        sinal estão no cabeçalho do módulo e são aplicadas pelos métodos
        :meth:`breaker_currents` e :meth:`motor_currents`.
    total_loss_W:
        Perda total da rede impressa pela listagem [W].
    valve:
        Dados das válvulas do ramo amortecedor.
    extrema:
        Extremos da janela inteira, por variável de saída.
    warnings:
        Avisos que a própria listagem emite.
    path:
        Arquivo de onde a referência foi lida.
    """

    frequency_Hz: float
    sources: dict[str, complex]
    node_voltages: dict[str, complex]
    branch_currents: dict[str, complex]
    total_loss_W: float
    valve: dict
    extrema: dict
    warnings: tuple[str, ...]
    path: Path

    # -- leitura ------------------------------------------------------------

    def node(self, name: str) -> complex:
        """Fasor da tensão nodal [V de pico].

        Raises
        ------
        KeyError
            Nó ausente da listagem — a mensagem lista os disponíveis.
        """
        key = str(name)
        if key not in self.node_voltages:
            raise KeyError(
                f"nó {key!r} não consta da listagem; disponíveis: "
                f"{sorted(self.node_voltages)}"
            )
        return self.node_voltages[key]

    def node_abc(self, prefix: str) -> np.ndarray:
        """Vetor ``[a, b, c]`` dos fasores de ``<prefix>A/B/C`` [V de pico]."""
        return np.array(
            [self.node(f"{prefix}{s}") for s in PHASE_SUFFIX], dtype=complex
        )

    def breaker_currents(self) -> np.ndarray:
        """Correntes do disjuntor no sentido de JUSANTE [A de pico].

        Sinal verificado por balanço de potência — ver o cabeçalho.
        """
        keys = ("X0001A->XX0027", "X0001B->XX0019", "X0001C->XX0011")
        return np.array([self.branch_currents[k] for k in keys], dtype=complex)

    def motor_currents(self) -> np.ndarray:
        """Correntes que ENTRAM no ramo do motor pelo nó ``01ATx`` [A de pico].

        É o SIMÉTRICO do fasor publicado — ver o cabeçalho.
        """
        keys = ("01ATA->TERRA", "01ATB->TERRA", "01ATC->TERRA")
        return -np.array([self.branch_currents[k] for k in keys], dtype=complex)

    def source_phasors(self) -> np.ndarray:
        """Vetor ``[a, b, c]`` das fontes ideais [V de pico]."""
        return np.array(
            [self.sources[f"X0030{s}"] for s in PHASE_SUFFIX], dtype=complex
        )

    @property
    def omega_rad_s(self) -> float:
        """``ω = 2πf`` [rad/s]."""
        return 2.0 * math.pi * self.frequency_Hz


def load_reference(path: str | Path | None = None) -> AtpReference:
    """Lê a solução fasorial de referência do JSON extraído da listagem.

    Parameters
    ----------
    path:
        Caminho do JSON; ``None`` (padrão) usa :data:`REFERENCE_JSON_PATH`.

    Returns
    -------
    AtpReference
        Fasores já convertidos (módulo de pico, ângulo em graus,
        referência cosseno).

    Raises
    ------
    FileNotFoundError
        Arquivo inexistente.
    ValueError
        Estrutura do JSON incompatível com a esperada.
    """
    p = Path(path) if path is not None else REFERENCE_JSON_PATH
    if not p.is_file():
        raise FileNotFoundError(
            f"referência de regime permanente não encontrada em {p}. É a "
            "fonte única da verdade do caso e não tem substituto sintético."
        )
    raw = json.loads(p.read_text(encoding="utf-8"))
    for key in ("frequencia_Hz", "fontes", "tensoes_nodais", "correntes_de_ramo"):
        if key not in raw:
            raise ValueError(f"JSON de referência sem a chave obrigatória {key!r}: {p}")

    def _block(name: str, field_name: str) -> dict[str, complex]:
        out: dict[str, complex] = {}
        for node, item in raw[name].items():
            if field_name not in item or "ang" not in item:
                raise ValueError(
                    f"entrada {node!r} de {name!r} sem os campos "
                    f"{field_name!r}/'ang' em {p}"
                )
            out[str(node)] = _phasor(item[field_name], item["ang"])
        return out

    return AtpReference(
        frequency_Hz=float(raw["frequencia_Hz"]),
        sources=_block("fontes", "V"),
        node_voltages=_block("tensoes_nodais", "V"),
        branch_currents=_block("correntes_de_ramo", "I"),
        total_loss_W=float(raw.get("perda_total_da_rede_W", TOTAL_NETWORK_LOSS_W)),
        valve=dict(raw.get("valvulas_do_amortecedor", {})),
        extrema=dict(raw.get("extremos_da_janela_completa", {})),
        warnings=tuple(str(x) for x in raw.get("_avisos_da_propria_listagem", ())),
        path=p,
    )


# ---------------------------------------------------------------------------
# Equivalente de Thévenin da rede a montante
# ---------------------------------------------------------------------------

#: Operador de sequência da fonte do arquivo: fase B ADIANTADA de 120°
#: [FATO: arquivo, cartões 14 com fase 0°, +120°, −120°].
_ALPHA: np.ndarray = np.array(
    [1.0, cmath.exp(2j * math.pi / 3.0), cmath.exp(-2j * math.pi / 3.0)],
    dtype=complex,
)


@dataclass(frozen=True)
class TheveninEquivalent:
    """Equivalente da rede a montante do nó ``X0029``, por fase.

    A montagem correspondente é: três f.e.m. equilibradas do ponto estrela
    ``XX0003`` aos nós internos, ``Z₁`` de cada nó interno a ``X0029_k``,
    ramo de magnetização de ``X0029_k`` de volta a ``XX0003`` e ``Z_n`` de
    ``XX0003`` à terra. A ligação ``X0029_k → X0001_k`` (linha a montante
    reduzida) vem em :attr:`z_link_ohm`.

    Attributes
    ----------
    emf_V:
        Fasor da f.e.m. interna da fase A [V de pico]; as outras duas são
        ``emf_V·α_k``.
    z_series_ohm:
        ``Z₁`` por fase [Ω] — dispersão do transformador mais o ramo
        fonte–triângulo, referidos a 4,16 kV.
    z_neutral_ohm:
        ``Z_n`` do ponto estrela à terra [Ω].
    z_magnetizing_ohm:
        Ramo de magnetização por fase [Ω], de ``X0029`` a ``XX0003``.
    z_link_ohm:
        Impedância equivalente por fase da linha a montante, de ``X0029``
        a ``X0001`` [Ω] — desigual entre as fases por construção.
    residual_V:
        Resíduo dos mínimos quadrados por fase [V], teste da hipótese de
        equilíbrio da rede a montante.
    z_mutual_ohm:
        Termo mútuo obtido quando ``use_card_neutral=False``; ``None`` na
        dedução padrão. Serve de conferência independente contra o
        resistor de neutro do cartão.
    """

    emf_V: complex
    z_series_ohm: complex
    z_neutral_ohm: complex
    z_magnetizing_ohm: float
    z_link_ohm: tuple[complex, complex, complex]
    residual_V: tuple[float, float, float]
    z_mutual_ohm: complex | None = None

    # -- leitura ------------------------------------------------------------

    @property
    def emf_abc_V(self) -> np.ndarray:
        """Vetor ``[a, b, c]`` das f.e.m. internas [V de pico]."""
        return self.emf_V * _ALPHA

    @property
    def emf_peak_V(self) -> float:
        """Módulo da f.e.m. interna [V de pico]."""
        return float(abs(self.emf_V))

    @property
    def emf_angle_deg(self) -> float:
        """Ângulo da f.e.m. da fase A [graus]."""
        return float(math.degrees(cmath.phase(self.emf_V)))

    @property
    def turns_ratio(self) -> float:
        """``|Ê| / |V̂_fonte|`` — relação de espiras implícita."""
        return self.emf_peak_V / SOURCE_PEAK_V

    def series_rl(self) -> tuple[float, float]:
        """``(R₁ [Ω], L₁ [H])`` de :attr:`z_series_ohm` em 60 Hz."""
        return _rl_from_impedance(self.z_series_ohm, "Z₁ do equivalente")

    def link_rl(self) -> tuple[tuple[float, float], ...]:
        """``(R, L)`` por fase da ligação ``X0029 → X0001``."""
        return tuple(
            _rl_from_impedance(z, f"Z_link da fase {ph}")
            for ph, z in zip(PHASES, self.z_link_ohm)
        )

    @property
    def zero_sequence_ohm(self) -> complex:
        """``Z₀ = Z₁ + 3·Z_n`` do equivalente [Ω]."""
        return self.z_series_ohm + 3.0 * self.z_neutral_ohm


def _rl_from_impedance(z: complex, label: str) -> tuple[float, float]:
    """Converte ``Z = R + jωL`` em ``(R, L)`` em 60 Hz, exigindo R, L > 0.

    Raises
    ------
    ValueError
        ``R < 0`` ou ``L <= 0`` — o ramo não seria fisicamente realizável
        e o kernel o rejeitaria; a mensagem diz qual grandeza falhou para
        que a substituição seja decidida com o número à vista.
    """
    omega = 2.0 * math.pi * FREQUENCY_HZ
    r = float(np.real(z))
    l = float(np.imag(z)) / omega
    if r < 0.0:
        raise ValueError(
            f"{label}: parte resistiva NEGATIVA ({r:.6g} Ω). Um ramo passivo "
            "não a representa; a extração por fase precisa ser substituída "
            "por uma representação acoplada."
        )
    if l <= 0.0:
        raise ValueError(f"{label}: indutância não positiva ({l:.6g} H)")
    return r, l


def derive_thevenin(
    reference: AtpReference, *, use_card_neutral: bool = True
) -> TheveninEquivalent:
    """Deduz o equivalente a montante da solução fasorial publicada.

    A álgebra está por extenso no cabeçalho do módulo (passos 1 a 6). Em
    resumo, com ``α = (1, e^{+j120°}, e^{−j120°})``::

        Î_mag,k = (V̂29_k − V̂_N) / R_mag
        Î_w,k   = Î_k + Î_mag,k
        V̂29_k − V̂_N = Ê·α_k − Z₁·Î_w,k          k = a, b, c

    Parameters
    ----------
    reference:
        Solução fasorial lida por :func:`load_reference`.
    use_card_neutral:
        ``True`` (padrão) fixa ``Z_n`` no resistor de 12,009 Ω do cartão
        [FATO: arquivo] e resolve ``(Ê, Z₁)`` por MÍNIMOS QUADRADOS sobre
        as três fases — o resíduo é então um teste da hipótese de rede a
        montante equilibrada. ``False`` resolve o sistema exatamente
        determinado de três incógnitas ``(Ê, Z₁, Z_m)``, cujo ``Z_m``
        RECUPERA o resistor de neutro sem tê-lo informado; é a
        conferência independente do método.

    Returns
    -------
    TheveninEquivalent
        Equivalente pronto para a montagem.

    Raises
    ------
    ValueError
        Sistema singular (correntes degeneradas na referência).
    """
    v29 = reference.node_abc("X0029")
    v02 = reference.node_abc("X0002")
    i_br = reference.breaker_currents()

    if use_card_neutral:
        v_n = reference.node("XX0003")
        i_mag = (v29 - v_n) / MAGNETIZING_RESISTANCE_OHM
        i_w = i_br + i_mag
        # Sistema sobredeterminado: 3 equações complexas, 2 incógnitas.
        M = np.zeros((3, 2), dtype=complex)
        M[:, 0] = _ALPHA
        M[:, 1] = -i_w
        rhs = v29 - v_n
        sol, _res, rank, _sv = np.linalg.lstsq(M, rhs, rcond=None)
        if rank < 2:
            raise ValueError(
                "sistema do equivalente é singular: as correntes publicadas "
                "não distinguem Ê de Z₁"
            )
        emf, z1 = complex(sol[0]), complex(sol[1])
        residual = tuple(float(abs(x)) for x in (M @ sol - rhs))
        z_mutual: complex | None = None
        z_n = complex(NEUTRAL_RESISTANCE_OHM, 0.0)
    else:
        # Sistema exatamente determinado em (Ê, Z₁, Z_m), sem informar o
        # resistor de neutro nem o ramo de magnetização.
        s_sum = complex(np.sum(i_br))
        M = np.zeros((3, 3), dtype=complex)
        rhs = np.zeros(3, dtype=complex)
        for k in range(3):
            M[k, 0] = _ALPHA[k]
            M[k, 1] = -i_br[k]
            M[k, 2] = -s_sum
            rhs[k] = v29[k]
        if abs(np.linalg.det(M)) <= 1.0e-9:
            raise ValueError(
                "sistema exatamente determinado do equivalente é singular; "
                "use use_card_neutral=True"
            )
        sol = np.linalg.solve(M, rhs)
        emf, z1, z_mutual = complex(sol[0]), complex(sol[1]), complex(sol[2])
        residual = (0.0, 0.0, 0.0)
        z_n = z_mutual

    z_link = tuple(complex(x) for x in (v29 - v02) / i_br)
    return TheveninEquivalent(
        emf_V=emf,
        z_series_ohm=z1,
        z_neutral_ohm=z_n,
        z_magnetizing_ohm=MAGNETIZING_RESISTANCE_OHM,
        z_link_ohm=z_link,  # type: ignore[arg-type]
        residual_V=residual,  # type: ignore[arg-type]
        z_mutual_ohm=z_mutual,
    )


# ---------------------------------------------------------------------------
# Cabo a jusante: Bergeron modal trifásico ACOPLADO
# ---------------------------------------------------------------------------


def downstream_cable_modal_data() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Devolve ``(Z_c [Ω], τ [s], R [Ω])`` por modo do cartão do arquivo.

    Leitura dos campos sob comprimento negativo — **[HIPÓTESE]** descrita
    e CONFIRMADA no cabeçalho do módulo::

        Z_c,μ = A_μ            τ_μ = |ℓ| / B_μ            R_μ = R_μ (total)
    """
    zc = np.asarray(CABLE_MODAL_SURGE_OHM, dtype=float)
    tau = CABLE_LENGTH_UNITS / np.asarray(CABLE_MODAL_VELOCITY, dtype=float)
    r = np.asarray(CABLE_MODAL_RESISTANCE_OHM, dtype=float)
    return zc, tau, r


def downstream_cable_modal_lc() -> tuple[np.ndarray, np.ndarray]:
    """``(L [H], C [F])`` TOTAIS por modo, derivados de ``Z_c`` e ``τ``.

    ``L_μ = Z_c,μ·τ_μ`` e ``C_μ = τ_μ/Z_c,μ`` — em unidades de engenharia
    dão 0,503/0,672/6,194 mH e 0,2278/0,0679/0,0064 µF, valores de cabo de
    média tensão por quilômetro [INFERÊNCIA FÍSICA].
    """
    zc, tau, _r = downstream_cable_modal_data()
    return zc * tau, tau / zc


def phase_series_impedance(
    omega_rad_s: float, *, transformation: np.ndarray | None = None
) -> np.ndarray:
    """Matriz ``Z_ph(ω) = (T^T)^{-1}·diag(R + jωL)·T^{-1}`` do cabo [Ω].

    Com ``transformation=None`` usa a matriz COMPLEXA punçada — que é a
    que o ATP emprega em sua solução fasorial e a que reproduz a queda
    publicada com erro de 1·10⁻⁶. Passe ``Re(T_i)`` para obter a leitura
    REAL, que é a única admissível na marcha no tempo.
    """
    t = CABLE_TI_COMPLEX if transformation is None else np.asarray(transformation)
    t = np.asarray(t, dtype=complex)
    l_mode, _c_mode = downstream_cable_modal_lc()
    z_mode = np.diag(
        np.asarray(CABLE_MODAL_RESISTANCE_OHM, dtype=float)
        + 1j * float(omega_rad_s) * l_mode
    )
    t_inv = np.linalg.inv(t)
    return np.linalg.inv(t.T) @ z_mode @ t_inv


def phase_shunt_admittance(
    omega_rad_s: float, *, transformation: np.ndarray | None = None
) -> np.ndarray:
    """Matriz transversal ``Y_ph(ω) = (T^T)^{-1}·diag(jωC)·T^{-1}`` [S]."""
    t = CABLE_TI_COMPLEX if transformation is None else np.asarray(transformation)
    t = np.asarray(t, dtype=complex)
    _l_mode, c_mode = downstream_cable_modal_lc()
    y_mode = np.diag(1j * float(omega_rad_s) * c_mode)
    return np.linalg.inv(t.T) @ y_mode @ np.linalg.inv(t)


class CoupledBergeronCable(Component):
    """Cabo trifásico ACOPLADO a parâmetros distribuídos constantes.

    É o modelo de Bergeron de :class:`~app.simulation.emt.line.BergeronLine`
    replicado nos três MODOS do cabo e reacoplado ao domínio de fase pela
    matriz de transformação punçada no arquivo. Cada modo tem sua própria
    impedância de surto, seu próprio tempo de trânsito e sua própria
    resistência concentrada em ``R/4, R/2, R/4`` — exatamente como no
    componente de uma fase, do qual esta classe reaproveita a álgebra e o
    buffer de histórico interpolado [REPO: app/simulation/emt/line.py:283].

    Formulação
    ----------

    Com ``T`` a matriz de transformação de CORRENTE
    (``i_fase = T·i_modo``, ``v_modo = Tᵀ·v_fase``), ``G = diag(1/z_μ)`` e
    ``z_μ = Z_c,μ + R_μ/4``::

        i_fase,k = (T·G·Tᵀ)·v_fase,k − T·i_hist,k

    de modo que a estampagem nodal em cada extremidade é o bloco cheio
    ``Y = T·G·Tᵀ`` (3×3, simétrico) e a fonte de corrente de histórico é
    ``T·i_hist``. Os dois blocos NÃO se conectam na matriz: as
    extremidades só se comunicam pelo histórico, cada modo com seu
    atraso ``τ_μ`` [FONTE: Dommel 1969, §I, p. 389].

    A matriz de transformação é REAL por exigência do modelo no domínio
    do tempo; o desvio em relação à leitura complexa do ATP é
    exclusivamente de sequência zero e está quantificado no cabeçalho do
    módulo.

    Parameters
    ----------
    name:
        Identificador do ramo.
    nodes_k, nodes_m:
        Três nós de cada extremidade, na ordem A, B, C.
    surge_impedance_ohm, travel_time_s, resistance_ohm:
        Vetores de três modos.
    transformation:
        Matriz 3×3 REAL de transformação de corrente — a única admissível
        na marcha no tempo.
    phasor_transformation:
        Matriz usada SOMENTE na estampagem fasorial. ``None`` (padrão)
        usa a mesma de :paramref:`transformation`, o que torna o modelo
        AUTOCONSISTENTE (a semeadura de regime é a do modelo integrado e
        não há transitório espúrio de partida). Passar a matriz COMPLEXA
        punçada reproduz a solução fasorial do ATP — que é o que o próprio
        ATP faz, usando a matriz complexa no fasor e a real na integração
        — ao preço dessa inconsistência.

    Raises
    ------
    ValueError
        Dimensões erradas, ``Z_c ≤ 0``, ``τ ≤ 0``, ``R < 0``,
        ``R/4 ≥ Z_c``, matriz singular ou nós repetidos.
    """

    def __init__(
        self,
        name: str,
        nodes_k: Sequence[str],
        nodes_m: Sequence[str],
        *,
        surge_impedance_ohm: Sequence[float],
        travel_time_s: Sequence[float],
        resistance_ohm: Sequence[float],
        transformation: np.ndarray,
        phasor_transformation: np.ndarray | None = None,
    ) -> None:
        nk = tuple(str(n) for n in nodes_k)
        nm = tuple(str(n) for n in nodes_m)
        if len(nk) != 3 or len(nm) != 3:
            raise ValueError(
                f"cabo {name!r} exige 3 nós por extremidade, obtidos "
                f"{len(nk)} e {len(nm)}"
            )
        if len(set(nk + nm)) != 6:
            raise ValueError(f"cabo {name!r} com nós repetidos: {nk + nm}")
        super().__init__(name, nk + nm)

        zc = np.asarray(surge_impedance_ohm, dtype=float)
        tau = np.asarray(travel_time_s, dtype=float)
        r = np.asarray(resistance_ohm, dtype=float)
        for label, arr in (("surge_impedance_ohm", zc), ("travel_time_s", tau), ("resistance_ohm", r)):
            if arr.shape != (3,) or not np.all(np.isfinite(arr)):
                raise ValueError(f"cabo {name!r}: {label} deve ter 3 valores finitos")
        if np.any(zc <= 0.0):
            raise ValueError(f"cabo {name!r}: Z_c modal deve ser > 0, obtido {zc}")
        if np.any(tau <= 0.0):
            raise ValueError(f"cabo {name!r}: τ modal deve ser > 0, obtido {tau}")
        if np.any(r < 0.0):
            raise ValueError(f"cabo {name!r}: R modal deve ser >= 0, obtido {r}")
        if np.any(r / 4.0 >= zc):
            raise ValueError(
                f"cabo {name!r}: R/4 >= Z_c em algum modo — a aproximação de "
                f"perdas concentradas não vale (R = {r}, Z_c = {zc})"
            )
        t = np.asarray(transformation, dtype=float)
        if t.shape != (3, 3) or not np.all(np.isfinite(t)):
            raise ValueError(f"cabo {name!r}: transformation deve ser 3×3 real finita")
        if abs(float(np.linalg.det(t))) < 1.0e-12:
            raise ValueError(
                f"cabo {name!r}: matriz de transformação singular "
                f"(det = {float(np.linalg.det(t)):.3e})"
            )

        self.surge_impedance_ohm = zc
        self.travel_time_s = tau
        self.resistance_ohm = r
        self.transformation = t
        if phasor_transformation is None:
            self.phasor_transformation = np.asarray(t, dtype=complex)
        else:
            tp = np.asarray(phasor_transformation, dtype=complex)
            if tp.shape != (3, 3) or not np.all(np.isfinite(tp)):
                raise ValueError(
                    f"cabo {name!r}: phasor_transformation deve ser 3×3 finita"
                )
            if abs(complex(np.linalg.det(tp))) < 1.0e-12:
                raise ValueError(f"cabo {name!r}: phasor_transformation singular")
            self.phasor_transformation = tp
        self._t_inv = np.linalg.inv(t)
        self._z = zc + r / 4.0
        self._zeta = (zc - r / 4.0) / self._z
        self._g = 1.0 / self._z
        #: ``Y = T·G·Tᵀ`` — bloco nodal 3×3 de cada extremidade [S].
        self._y_end = t @ np.diag(self._g) @ t.T

        self._history = [_TravelHistory() for _ in range(3)]
        self._v_ph_k = np.zeros(3)
        self._v_ph_m = np.zeros(3)
        self._i_ph_k = np.zeros(3)
        self._i_ph_m = np.zeros(3)
        self._i_hist_k = np.zeros(3)
        self._i_hist_m = np.zeros(3)
        self._warned_short = False
        self._seed: tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, float, float] | None = None

    # -- propriedades -------------------------------------------------------

    def n_branches(self) -> int:
        """Seis: três correntes de fase entrando por cada extremidade."""
        return 6

    @property
    def nodal_admittance_S(self) -> np.ndarray:
        """Bloco ``Y = T·G·Tᵀ`` de cada extremidade [S]."""
        return self._y_end.copy()

    @property
    def modal_conductance_S(self) -> np.ndarray:
        """``1/z_μ`` por modo [S]."""
        return self._g.copy()

    # -- ciclo de vida ------------------------------------------------------

    def prepare(self, dt: float) -> None:
        super().prepare(dt)
        if float(np.min(self.travel_time_s)) < self._dt and not self._warned_short:
            self._warned_short = True
            log.warning(
                "cabo %r: menor tempo de trânsito modal (%.6g s) é inferior ao "
                "passo Δt = %.6g s; o histórico será retido por ordem zero e o "
                "modo se comporta como ramo concentrado",
                self.name,
                float(np.min(self.travel_time_s)),
                self._dt,
            )

    def reset(self) -> None:
        for h in self._history:
            h.reset()
        self._v_ph_k = np.zeros(3)
        self._v_ph_m = np.zeros(3)
        self._i_ph_k = np.zeros(3)
        self._i_ph_m = np.zeros(3)
        self._i_hist_k = np.zeros(3)
        self._i_hist_m = np.zeros(3)
        if self._seed is not None:
            self._apply_seed()

    # -- estampagem no domínio do tempo -------------------------------------

    def _stamp_block(self, A: np.ndarray, rows: Sequence[int], cols: Sequence[int], block: np.ndarray) -> None:
        """Soma ``block`` em ``A[rows, cols]``, saltando a terra."""
        for i, ri in enumerate(rows):
            if ri == GROUND_INDEX:
                continue
            for j, cj in enumerate(cols):
                if cj == GROUND_INDEX:
                    continue
                A[ri, cj] += block[i, j]

    def stamp_matrix(self, A: np.ndarray) -> None:
        k = self._idx[0:3]
        m = self._idx[3:6]
        self._stamp_block(A, k, k, self._y_end)
        self._stamp_block(A, m, m, self._y_end)

    def _history_sources(self, t: float) -> tuple[np.ndarray, np.ndarray]:
        """``(i_hist,k, i_hist,m)`` MODAIS em ``t``, do estado em ``t − τ_μ``."""
        i_k = np.zeros(3)
        i_m = np.zeros(3)
        for mu in range(3):
            v_k_d, i_km_d, v_m_d, i_mk_d = self._history[mu].value_at(
                t - float(self.travel_time_s[mu])
            )
            z = float(self._zeta[mu])
            g = float(self._g[mu])
            a = 0.5 * (1.0 + z)
            b = 0.5 * (1.0 - z)
            i_k[mu] = -a * (v_m_d * g + z * i_mk_d) - b * (v_k_d * g + z * i_km_d)
            i_m[mu] = -a * (v_k_d * g + z * i_km_d) - b * (v_m_d * g + z * i_mk_d)
        return i_k, i_m

    def stamp_rhs(self, b: np.ndarray, t: float, mode: str) -> None:
        i_k, i_m = self._history_sources(t)
        self._i_hist_k = i_k
        self._i_hist_m = i_m
        inj_k = self.transformation @ i_k
        inj_m = self.transformation @ i_m
        for i, node in enumerate(self._idx[0:3]):
            if node != GROUND_INDEX:
                b[node] -= inj_k[i]
        for i, node in enumerate(self._idx[3:6]):
            if node != GROUND_INDEX:
                b[node] -= inj_m[i]

    def commit(self, x: np.ndarray, t: float, mode: str) -> None:
        v_k = np.array([node_voltage(x, i) for i in self._idx[0:3]])
        v_m = np.array([node_voltage(x, i) for i in self._idx[3:6]])
        self._v_ph_k = v_k
        self._v_ph_m = v_m
        vm_k = self.transformation.T @ v_k
        vm_m = self.transformation.T @ v_m
        im_k = self._g * vm_k + self._i_hist_k
        im_m = self._g * vm_m + self._i_hist_m
        self._i_ph_k = self.transformation @ im_k
        self._i_ph_m = self.transformation @ im_m
        for mu in range(3):
            self._history[mu].append(
                t, float(vm_k[mu]), float(im_k[mu]), float(vm_m[mu]), float(im_m[mu])
            )

    # -- leitura ------------------------------------------------------------

    def branch_voltage(self, index: int = 0) -> float:
        """0-2: tensão de fase da extremidade k; 3-5: da extremidade m [V]."""
        if 0 <= int(index) < 3:
            return float(self._v_ph_k[int(index)])
        if 3 <= int(index) < 6:
            return float(self._v_ph_m[int(index) - 3])
        raise ValueError(f"terminal inválido para o cabo acoplado: {index!r}")

    def branch_current(self, index: int = 0) -> float:
        """0-2: corrente de fase ENTRANDO por k; 3-5: entrando por m [A]."""
        if 0 <= int(index) < 3:
            return float(self._i_ph_k[int(index)])
        if 3 <= int(index) < 6:
            return float(self._i_ph_m[int(index) - 3])
        raise ValueError(f"terminal inválido para o cabo acoplado: {index!r}")

    # -- domínio fasorial ---------------------------------------------------

    def _modal_admittances(self, omega: float) -> tuple[np.ndarray, np.ndarray]:
        """``(y11, y12)`` por modo do quadripolo de Bergeron IMPLEMENTADO.

        Mesma álgebra de
        :func:`~app.simulation.emt.steady_state._line_admittance`, modo a
        modo — reproduzida aqui para que a estampagem fasorial seja a do
        MODELO INTEGRADO e não a de uma linha ideal equivalente.
        """
        y11 = np.zeros(3, dtype=complex)
        y12 = np.zeros(3, dtype=complex)
        for mu in range(3):
            g = float(self._g[mu])
            zeta = float(self._zeta[mu])
            d = complex(np.exp(-1j * omega * float(self.travel_time_s[mu])))
            a = 0.5 * (1.0 + zeta)
            b = 0.5 * (1.0 - zeta)
            P = 1.0 + b * d * zeta
            Q = a * d * zeta
            alpha = g * (1.0 - b * d)
            beta = -a * d * g
            det = P * P - Q * Q
            if abs(det) <= 1.0e-14 * max(1.0, abs(P) + abs(Q)):
                raise ValueError(
                    f"cabo {self.name!r}: quadripolo fasorial singular no modo "
                    f"{mu + 1} (ωτ múltiplo de π — meia onda)"
                )
            y11[mu] = (P * alpha - Q * beta) / det
            y12[mu] = (P * beta - Q * alpha) / det
        return y11, y12

    def _phase_blocks(self, omega: float) -> tuple[np.ndarray, np.ndarray]:
        """``(Y₁₁, Y₁₂)`` 3×3 no domínio de fase [S]."""
        y11, y12 = self._modal_admittances(omega)
        t = self.phasor_transformation
        return t @ np.diag(y11) @ t.T, t @ np.diag(y12) @ t.T

    def stamp_phasor(self, A: np.ndarray, b: np.ndarray, omega: float) -> None:
        """Estampa o quadripolo trifásico no sistema complexo."""
        y11, y12 = self._phase_blocks(omega)
        k = self._idx[0:3]
        m = self._idx[3:6]
        self._stamp_block(A, k, k, y11)
        self._stamp_block(A, m, m, y11)
        self._stamp_block(A, k, m, y12)
        self._stamp_block(A, m, k, y12)

    def phasor_branches(
        self, x: np.ndarray, omega: float
    ) -> tuple[tuple[complex, complex], ...]:
        """Pares ``(V̂, Î)`` das seis correntes de fase — gancho do kernel."""
        y11, y12 = self._phase_blocks(omega)
        v_k = np.array(
            [0.0 + 0.0j if i == GROUND_INDEX else complex(x[i]) for i in self._idx[0:3]]
        )
        v_m = np.array(
            [0.0 + 0.0j if i == GROUND_INDEX else complex(x[i]) for i in self._idx[3:6]]
        )
        i_k = y11 @ v_k + y12 @ v_m
        i_m = y12 @ v_k + y11 @ v_m
        return tuple(
            (complex(v), complex(i))
            for v, i in zip(np.concatenate([v_k, v_m]), np.concatenate([i_k, i_m]))
        )

    def seed_phasor(
        self,
        pairs: Sequence[tuple[complex, complex]],
        omega: float,
        dt: float,
    ) -> tuple[float, ...]:
        """Semeia o histórico modal com a onda de regime — gancho do kernel.

        Os fasores chegam no domínio de FASE (seis pares) e são levados ao
        modal por ``v_modo = Tᵀ·v_fase`` e ``i_modo = T⁻¹·i_fase`` antes de
        preencher os três buffers, cada um com o seu ``τ_μ``.
        """
        if len(pairs) != 6:
            raise ValueError(
                f"cabo {self.name!r}: seed_phasor espera 6 pares, obtidos {len(pairs)}"
            )
        v_ph_k = np.array([complex(pairs[i][0]) for i in range(3)])
        v_ph_m = np.array([complex(pairs[i][0]) for i in range(3, 6)])
        i_ph_k = np.array([complex(pairs[i][1]) for i in range(3)])
        i_ph_m = np.array([complex(pairs[i][1]) for i in range(3, 6)])
        t = self.transformation
        self._seed = (
            t.T @ v_ph_k,
            self._t_inv @ i_ph_k,
            t.T @ v_ph_m,
            self._t_inv @ i_ph_m,
            float(omega),
            float(dt),
        )
        self._apply_seed()
        out: list[float] = []
        for vec in (v_ph_k, v_ph_m, i_ph_k, i_ph_m):
            out.extend(float(np.real(z)) for z in vec)
        return tuple(out)

    def clear_steady_state_seed(self) -> None:
        """Descarta a semente e volta ao histórico nulo."""
        self._seed = None
        for h in self._history:
            h.reset()

    def _apply_seed(self) -> int:
        """Escreve a onda de regime até ``−(τ_μ + 2Δt)`` em cada modo."""
        assert self._seed is not None
        vm_k, im_k, vm_m, im_m, omega, dt_f = self._seed
        total = 0
        for mu in range(3):
            n = int(math.ceil(float(self.travel_time_s[mu]) / dt_f)) + 2
            times = [-(n - j) * dt_f for j in range(n + 1)]
            samples = []
            for tt in times:
                rot = np.exp(1j * omega * tt)
                samples.append(
                    (
                        float(np.real(vm_k[mu] * rot)),
                        float(np.real(im_k[mu] * rot)),
                        float(np.real(vm_m[mu] * rot)),
                        float(np.real(im_m[mu] * rot)),
                    )
                )
            self._history[mu].seed(times, samples)
            total += len(times)
        # Estado terminal em t = 0, coerente com a semente.
        vm0 = np.array([np.real(vm_k[mu]) for mu in range(3)])
        im0 = np.array([np.real(im_k[mu]) for mu in range(3)])
        vm0_m = np.array([np.real(vm_m[mu]) for mu in range(3)])
        im0_m = np.array([np.real(im_m[mu]) for mu in range(3)])
        self._v_ph_k = np.linalg.inv(self.transformation.T) @ vm0
        self._v_ph_m = np.linalg.inv(self.transformation.T) @ vm0_m
        self._i_ph_k = self.transformation @ im0
        self._i_ph_m = self.transformation @ im0_m
        return total


#: Leituras admitidas da matriz de transformação modal na estampagem
#: FASORIAL do cabo a jusante.
CABLE_PHASOR_REAL: str = "real"
CABLE_PHASOR_COMPLEX: str = "complexa"
CABLE_PHASOR_READINGS: tuple[str, str] = (CABLE_PHASOR_REAL, CABLE_PHASOR_COMPLEX)


def build_downstream_cable(
    name: str,
    nodes_k: Sequence[str],
    nodes_m: Sequence[str],
    *,
    transformation: np.ndarray | None = None,
    phasor_reading: str = CABLE_PHASOR_REAL,
) -> CoupledBergeronCable:
    """Instancia o cabo a jusante com os parâmetros do cartão do arquivo.

    ``transformation=None`` (padrão) usa ``Re(T_i)`` da matriz punçada —
    a parte real é a única admissível no domínio do tempo.

    ``phasor_reading`` escolhe a matriz da estampagem FASORIAL:
    ``"real"`` (padrão) mantém o modelo autoconsistente; ``"complexa"``
    reproduz a leitura que o ATP usa em sua própria solução fasorial, e
    serve para ATRIBUIR o resíduo da validação — ver o cabeçalho.
    """
    zc, tau, r = downstream_cable_modal_data()
    t = np.real(CABLE_TI_COMPLEX) if transformation is None else np.asarray(transformation, dtype=float)
    reading = str(phasor_reading)
    if reading not in CABLE_PHASOR_READINGS:
        raise ValueError(
            f"phasor_reading deve ser um de {CABLE_PHASOR_READINGS}, "
            f"obtido {phasor_reading!r}"
        )
    tp = CABLE_TI_COMPLEX if reading == CABLE_PHASOR_COMPLEX else None
    return CoupledBergeronCable(
        name,
        nodes_k,
        nodes_m,
        surge_impedance_ohm=zc,
        travel_time_s=tau,
        resistance_ohm=r,
        transformation=t,
        phasor_transformation=tp,
    )


# ---------------------------------------------------------------------------
# Controlador mestre de disparo do ramo amortecedor
# ---------------------------------------------------------------------------


class SnubberArmingGate:
    """Habilitação global do ramo amortecedor pelo estado de arco do disjuntor.

    Reproduz o MODEL ``SNUB_CTRL`` do arquivo, cujo comentário é "Controlador
    Master Trigger — replica o disparo (latch) para todas as fases" e cuja
    lógica é ``IF (STA > 1.9 OR STB > 1.9 OR STC > 1.9 OR FM > 0.5) THEN
    FM := 1.0`` [FATO: arquivo, MODEL SNUB_CTRL]. Isto é:

    1. a habilitação é GLOBAL — basta um polo em estado de arco para armar
       as três fases;
    2. a habilitação TRAVA: uma vez em 1, ``FM`` nunca volta a 0 durante a
       simulação.

    Enquanto não armado, os ramos permanecem bloqueados e os controladores
    de válvula sequer são chamados — o ramo é transparente em regime, como
    a listagem registra ("estado em regime: aberta"). Depois de armado, o
    disparo passa a ser decidido localmente por cada
    :class:`~app.simulation.emt.snubber.ThyristorSnubber` pelo nível de
    *breakover* de 2404 V [FATO: listagem].

    Parameters
    ----------
    poles:
        Polos do disjuntor observados.
    controllers:
        Controladores de válvula a habilitar.
    name:
        Rótulo.
    """

    def __init__(
        self,
        poles: Sequence[VacuumCircuitBreakerModel],
        controllers: Sequence,
        *,
        name: str = "snub_master",
    ) -> None:
        self.poles = tuple(poles)
        self.controllers = tuple(controllers)
        self.name = str(name)
        self._armed = False
        self._armed_time_s: float | None = None

    @property
    def armed(self) -> bool:
        """``True`` depois da primeira ocorrência de estado de arco."""
        return self._armed

    @property
    def armed_time_s(self) -> float | None:
        """Instante em que a habilitação travou [s]; ``None`` se nunca armou."""
        return self._armed_time_s

    def reset(self) -> None:
        """Desarma e reinicia os controladores de válvula."""
        self._armed = False
        self._armed_time_s = None
        for ctrl in self.controllers:
            reset = getattr(ctrl, "reset", None)
            if callable(reset):
                reset()

    def __call__(self, t: float, solver) -> None:
        if not self._armed:
            for pole in self.poles:
                if pole.state in (STATE_ARCING, STATE_ARCING_HF) or pole.arc_established:
                    self._armed = True
                    self._armed_time_s = float(t)
                    break
        if not self._armed:
            return
        for ctrl in self.controllers:
            ctrl(t, solver)


# ---------------------------------------------------------------------------
# Montagem do caso
# ---------------------------------------------------------------------------

#: Nós do caso, com os nomes do próprio arquivo ATP (variante com amortecedor).
NODE_NEUTRAL: str = "XX0003"
NODE_GROUND: str = "gnd"
NODES_X0029: tuple[str, str, str] = ("X0029A", "X0029B", "X0029C")
NODES_CB_SOURCE: tuple[str, str, str] = ("X0001A", "X0001B", "X0001C")
NODES_CB_LOAD: tuple[str, str, str] = ("X0002A", "X0002B", "X0002C")
NODES_MOTOR: tuple[str, str, str] = ("01ATA", "01ATB", "01ATC")


@dataclass(frozen=True)
class AtpReferenceCase:
    """Parâmetros da montagem do caso do arquivo ATP.

    Todos os padrões são os do arquivo; o que não vem dele está marcado.

    Attributes
    ----------
    with_snubber:
        Monta o ramo amortecedor (variante ``..._com_snubber_...``).
    dt_s, t_end_s:
        Passo e janela [s] — 1 µs e 45 ms do cartão.
    use_card_neutral:
        Repassado a :func:`derive_thevenin`.
    didt_convention:
        Convenção de extinção de alta frequência; o padrão é a do MODEL do
        arquivo (``|di/dt| > crítico``) [FATO: arquivo].
    reignition_factor:
        Fator sobre a suportabilidade no critério de reignição; 1,1 do
        MODEL [FATO: arquivo].
    gap_capacitance_F:
        Capacitância em paralelo com cada polo [F]. ``None`` (padrão) não
        a representa; o arquivo declara ``COPEN = 6 µF``
        (:data:`VCB_OPEN_CAPACITANCE_F`), valor que domina a TRV e cuja
        inclusão muda o caso — por isso é escolha explícita.
    max_reignitions:
        Teto de reignições por polo.
    separation_times_s:
        Sobrepõe os instantes de separação dos contatos [s]. ``None``
        (padrão) usa os do arquivo. Serve para manter o disjuntor FECHADO
        durante toda a janela (instantes além de ``t_end_s``), que é o
        ensaio de ausência de transitório espúrio de partida.
    snubber_breakover_V, snubber_resistance_ohm, snubber_holding_current_A:
        Ramo amortecedor [FATO: listagem/arquivo].
    cable_phasor_reading:
        Leitura da matriz de transformação modal na estampagem fasorial do
        cabo: ``"real"`` (padrão, autoconsistente) ou ``"complexa"`` (a do
        ATP). Ver :func:`build_downstream_cable`.
    reference_path:
        JSON de referência; ``None`` usa o padrão do módulo.
    """

    with_snubber: bool = True
    dt_s: float = DT_S
    t_end_s: float = T_END_S
    use_card_neutral: bool = True
    didt_convention: str = DIDT_INTERRUPT_ABOVE
    reignition_factor: float = VCB_REIGNITION_FACTOR
    gap_capacitance_F: float | None = None
    max_reignitions: int = 200
    separation_times_s: tuple[float, float, float] | None = None
    snubber_breakover_V: float = SNUBBER_BREAKOVER_V
    snubber_resistance_ohm: float = SNUBBER_RESISTANCE_OHM
    snubber_holding_current_A: float = SNUBBER_HOLDING_CURRENT_A
    cable_phasor_reading: str = CABLE_PHASOR_REAL
    atp_model_compatibility: bool = False
    zero_crossing_order: str = ATP_ZERO_ORDER_LITERAL
    reference_path: Path | None = None
    #: Realizações de parâmetros por polo, uma por fase, vindas de
    #: :mod:`app.simulation.emt.vcb_scenarios`. ``None`` (padrão) usa os
    #: valores do arquivo de referência. Um trio de amostras substitui
    #: corrente de corte, recuperação dielétrica, capacidade de extinção
    #: e instante de separação — é o caminho da varredura estatística,
    #: em que os parâmetros do disjuntor entram como FAIXAS da literatura
    #: e não como constantes de um caso.
    vcb_samples: tuple | None = None
    #: Para-raios de óxido metálico no TERMINAL DO MOTOR. ``None`` (padrão)
    #: não os representa, que é a configuração do arquivo. Um valor de
    #: tensão de sistema [V] instala um para-raios por fase, escalado da
    #: curva publicada por Vollet e de Metz-Noblat para essa tensão — ver
    #: :mod:`app.simulation.emt.arrester`. É o elemento cuja ausência põe
    #: a cauda de escalada fora do domínio físico
    #: [REPO: docs/research/rul_isolamento/08_VARREDURA_ESTATISTICA_VCB.md].
    motor_arrester_system_voltage_V: float | None = None
    #: Nível de disrupção da isolação no terminal do motor [V de pico].
    #: ``None`` (padrão) não representa disrupção — que é a configuração
    #: do arquivo. Um valor instala um caminho de disrupção por fase, com
    #: registro do evento; use :func:`app.simulation.emt.flashover.
    #: iec_60034_15_levels` para obtê-lo do envelope normativo. A
    #: travessia é EVENTO TERMINAL a contar, não estresse a integrar —
    #: ver o cabeçalho de :mod:`app.simulation.emt.flashover`.
    motor_flashover_level_V: float | None = None

    def __post_init__(self) -> None:
        for label, value in (("dt_s", self.dt_s), ("t_end_s", self.t_end_s)):
            v = float(value)
            if not math.isfinite(v) or v <= 0.0:
                raise ValueError(f"{label} deve ser finito e > 0, obtido {value!r}")
        if float(self.t_end_s) < float(self.dt_s):
            raise ValueError("t_end_s deve ser >= dt_s")
        if float(self.reignition_factor) <= 0.0:
            raise ValueError(
                f"reignition_factor deve ser > 0, obtido {self.reignition_factor!r}"
            )
        if self.gap_capacitance_F is not None and float(self.gap_capacitance_F) <= 0.0:
            raise ValueError("gap_capacitance_F deve ser > 0 quando informada")
        if self.motor_arrester_system_voltage_V is not None:
            u = float(self.motor_arrester_system_voltage_V)
            if not math.isfinite(u) or u <= 0.0:
                raise ValueError(
                    "motor_arrester_system_voltage_V deve ser finita e > 0, "
                    f"obtida {self.motor_arrester_system_voltage_V!r}"
                )
        if self.motor_flashover_level_V is not None:
            v = float(self.motor_flashover_level_V)
            if not math.isfinite(v) or v <= 0.0:
                raise ValueError(
                    "motor_flashover_level_V deve ser finito e > 0, obtido "
                    f"{self.motor_flashover_level_V!r}"
                )
        if str(self.cable_phasor_reading) not in CABLE_PHASOR_READINGS:
            raise ValueError(
                f"cable_phasor_reading deve ser um de {CABLE_PHASOR_READINGS}, "
                f"obtido {self.cable_phasor_reading!r}"
            )
        if str(self.zero_crossing_order) not in ATP_ZERO_ORDERS:
            raise ValueError(
                f"zero_crossing_order deve ser um de {ATP_ZERO_ORDERS}, "
                f"obtido {self.zero_crossing_order!r}"
            )
        if self.atp_model_compatibility and self.gap_capacitance_F is not None:
            raise ValueError(
                "gap_capacitance_F não se aplica ao modo literal: o polo do "
                "arquivo já traz o ramo série R-L-C comutado em paralelo com "
                "a chave, cuja capacitância de aberto é a própria COPEN"
            )
        if self.separation_times_s is not None:
            times = tuple(self.separation_times_s)
            if len(times) != 3 or any(
                (not math.isfinite(float(t))) or float(t) < 0.0 for t in times
            ):
                raise ValueError(
                    "separation_times_s deve trazer 3 instantes finitos e >= 0, "
                    f"obtido {self.separation_times_s!r}"
                )

    def without_snubber(self) -> "AtpReferenceCase":
        """Cópia sem o ramo amortecedor (variante base do arquivo)."""
        return replace(self, with_snubber=False)

    def with_snubber_branch(self, **kwargs) -> "AtpReferenceCase":
        """Cópia com o ramo amortecedor e eventuais ajustes de parâmetro."""
        return replace(self, with_snubber=True, **kwargs)

    def separation_times(self) -> tuple[float, float, float]:
        """Instantes de separação efetivos [s] — do arquivo ou sobrepostos."""
        if self.separation_times_s is None:
            return VCB_SEPARATION_TIME_S
        return tuple(float(t) for t in self.separation_times_s)  # type: ignore[return-value]

    def recovery(self) -> ParabolicRecovery:
        """Lei de recuperação JÁ multiplicada pelo fator de reignição.

        O MODEL do arquivo reignita com ``|V_gap| > V_wth·1,1``
        [FATO: arquivo]. O kernel compara com a própria lei, sem fator, de
        modo que a equivalência exata se obtém escalando os dois
        coeficientes: ``1,1·(A·t + B·t²) = (1,1A)·t + (1,1B)·t²``
        [CÁLCULO PRÓPRIO].
        """
        f = float(self.reignition_factor)
        return ParabolicRecovery(
            a_kV_per_ms=VCB_RRDS_A_KV_PER_MS * f,
            b_kV_per_ms2=VCB_RRDS_B_KV_PER_MS2 * f,
        )

    def build(self) -> "AtpReferenceModel":
        """Monta circuito, sondas e controladores do caso.

        Returns
        -------
        AtpReferenceModel
            Montagem pronta para ``.run()`` e para
            ``.phasor_validation()``.
        """
        reference = load_reference(self.reference_path)
        thevenin = derive_thevenin(reference, use_card_neutral=self.use_card_neutral)
        ckt = Circuit("atp_referencia_com_amortecedor" if self.with_snubber else "atp_referencia_base")

        # -- equivalente de Thévenin -----------------------------------------
        internal = tuple(f"EQ_{s}" for s in PHASE_SUFFIX)
        ckt.extend(
            three_phase_voltage_sources(
                "E",
                internal,
                NODE_NEUTRAL,
                amplitude_V=thevenin.emf_peak_V,
                frequency_Hz=FREQUENCY_HZ,
                phase_deg=thevenin.emf_angle_deg,
                sequence="acb",  # fase B ADIANTADA de 120°, como o arquivo
                phase_reference="cos",
            )
        )
        r1, l1 = thevenin.series_rl()
        for ph, node_int, node_29 in zip(PHASES, internal, NODES_X0029):
            ckt.add(Resistor(f"z1_r_{ph}", node_int, f"z1_m_{ph}", r1))
            ckt.add(Inductor(f"z1_l_{ph}", f"z1_m_{ph}", node_29, l1))
            ckt.add(
                Resistor(f"rmag_{ph}", node_29, NODE_NEUTRAL, thevenin.z_magnetizing_ohm)
            )
        rn, ln = float(np.real(thevenin.z_neutral_ohm)), float(
            np.imag(thevenin.z_neutral_ohm)
        ) / (2.0 * math.pi * FREQUENCY_HZ)
        if ln > 0.0:
            ckt.add(Resistor("rn", NODE_NEUTRAL, "rn_m", rn))
            ckt.add(Inductor("ln", "rn_m", NODE_GROUND, ln))
        else:
            ckt.add(Resistor("rn", NODE_NEUTRAL, NODE_GROUND, rn))

        # -- ligação X0029 → X0001 (linha a montante reduzida) ---------------
        for ph, node_29, node_cb, (r_l, l_l) in zip(
            PHASES, NODES_X0029, NODES_CB_SOURCE, thevenin.link_rl()
        ):
            ckt.add(Resistor(f"link_r_{ph}", node_29, f"link_m_{ph}", r_l))
            ckt.add(Inductor(f"link_l_{ph}", f"link_m_{ph}", node_cb, l_l))

        # -- disjuntor -------------------------------------------------------
        # No modo LITERAL o polo é o do arquivo — chave ideal em paralelo com
        # o ramo série C-L-R comutado por TACS —, montado aqui para que os
        # nós ``X0001x``/``X0002x`` sejam os mesmos nos dois modos e as sondas
        # não mudem [FATO: arquivo, cartões do polo].
        switches: list[Switch] = []
        literal_poles: tuple[AtpLiteralPole, ...] = ()
        if self.atp_model_compatibility:
            literal_poles = tuple(
                build_atp_literal_pole(
                    f"vcb_{ph}",
                    node_src,
                    node_load,
                    parameters=AtpVcbParameters.for_pole(
                        k,
                        t_open_s=t_sep,
                        reignition_margin=float(self.reignition_factor),
                    ),
                    zero_crossing_order=str(self.zero_crossing_order),
                    timestep_s=float(self.dt_s),
                )
                for k, (ph, node_src, node_load, t_sep) in enumerate(
                    zip(PHASES, NODES_CB_SOURCE, NODES_CB_LOAD, self.separation_times())
                )
            )
            for polo in literal_poles:
                ckt.extend(polo.components)
                switches.append(polo.switch)
        else:
            for ph, node_src, node_load in zip(PHASES, NODES_CB_SOURCE, NODES_CB_LOAD):
                sw = ckt.add(Switch(f"vcb_{ph}", node_src, node_load, closed=True))
                switches.append(sw)
                if self.gap_capacitance_F is not None:
                    ckt.add(
                        Capacitor(
                            f"vcb_c_{ph}",
                            node_src,
                            node_load,
                            float(self.gap_capacitance_F),
                        )
                    )

        # -- cabo a jusante e motor -----------------------------------------
        ckt.add(
            build_downstream_cable(
                "cabo_jusante",
                NODES_CB_LOAD,
                NODES_MOTOR,
                phasor_reading=str(self.cable_phasor_reading),
            )
        )
        for ph, node_mot in zip(PHASES, NODES_MOTOR):
            ckt.add(Resistor(f"mot_r_{ph}", node_mot, f"mot_m_{ph}", MOTOR_RESISTANCE_OHM))
            ckt.add(Inductor(f"mot_l_{ph}", f"mot_m_{ph}", NODE_GROUND, MOTOR_INDUCTANCE_H))

        # -- para-raios no terminal do motor ---------------------------------
        arresters: tuple = ()
        if self.motor_arrester_system_voltage_V is not None:
            arresters = three_phase_arrester(
                "moa_motor",
                NODES_MOTOR,
                NODE_GROUND,
                system_voltage_V=float(self.motor_arrester_system_voltage_V),
            )
            for moa in arresters:
                ckt.add(moa)

        # -- disrupção da isolação no terminal do motor ----------------------
        flashovers: tuple = ()
        if self.motor_flashover_level_V is not None:
            flashovers = three_phase_flashover(
                "disrupcao",
                NODES_MOTOR,
                NODE_GROUND,
                threshold_V=float(self.motor_flashover_level_V),
            )
            for caminho in flashovers:
                ckt.extend(caminho.components)

        # -- polos do disjuntor ----------------------------------------------
        recovery = self.recovery()
        if self.vcb_samples is not None:
            amostras = tuple(self.vcb_samples)
            if len(amostras) != len(PHASES):
                raise ValueError(
                    f"vcb_samples deve trazer {len(PHASES)} realizações, uma por fase, "
                    f"obtidas {len(amostras)}"
                )
            # A convenção de extinção acompanha a AMOSTRA, não o arquivo:
            # uma realização vinda das faixas da literatura traz consigo a
            # convenção física (extingue DENTRO da capacidade de di/dt), e
            # impor sobre ela a convenção invertida do arquivo misturaria
            # duas físicas incompatíveis no mesmo resultado.
            parametros = tuple(
                (
                    a.separation_time_s,
                    a.chopping_current_A,
                    a.recovery(),
                    a.didt_capability_A_per_us,
                    a.as_pole_kwargs()["didt_convention"],
                )
                for a in amostras
            )
        else:
            parametros = tuple(
                (t_sep, i_ch, recovery, didt, self.didt_convention)
                for t_sep, i_ch, didt in zip(
                    self.separation_times(),
                    VCB_CHOPPING_CURRENT_A,
                    VCB_DIDT_CAPABILITY_A_PER_US,
                )
            )
        poles: tuple = tuple(polo.controller for polo in literal_poles) if literal_poles else tuple(
            VacuumCircuitBreakerModel(
                sw,
                separation_time_s=t_sep,
                chopping_current_A=i_ch,
                chopping_range_A=(i_ch, i_ch),
                chopping_distribution="deterministic",
                recovery=rec,
                didt_capability_A_per_us=didt,
                didt_convention=conv,
                max_reignitions=int(self.max_reignitions),
                name=f"vcb_{ph}",
            )
            for ph, sw, (t_sep, i_ch, rec, didt, conv) in zip(PHASES, switches, parametros)
        )

        # -- ramo amortecedor opcional ---------------------------------------
        snubbers: tuple[SnubberBranch, ...] = ()
        gate = None
        if self.with_snubber and self.atp_model_compatibility:
            # Controlador mestre do arquivo: limiar 1,9 sobre o CÓDIGO de
            # estado, isto é, arma no estado ABERTO (2) e não no de arco (1)
            # [FATO: arquivo, MODEL SNUB_CTRL].
            snubbers, gate = three_phase_atp_literal_snubber(
                "snub",
                NODES_CB_LOAD,
                NODE_GROUND,
                poles,
                breakover_voltage_V=float(self.snubber_breakover_V),
                resistance_ohm=float(self.snubber_resistance_ohm),
                holding_current_A=float(self.snubber_holding_current_A),
            )
            for branch in snubbers:
                ckt.extend(branch.components)
        elif self.with_snubber:
            snubbers = three_phase_snubber(
                "snub",
                NODES_CB_LOAD,
                NODE_GROUND,
                breakover_voltage_V=float(self.snubber_breakover_V),
                resistance_ohm=float(self.snubber_resistance_ohm),
                holding_current_A=float(self.snubber_holding_current_A),
            )
            for branch in snubbers:
                ckt.extend(branch.components)
            gate = SnubberArmingGate(poles, [b.controller for b in snubbers])

        # -- solver e sondas --------------------------------------------------
        solver = Solver(
            ckt,
            dt=float(self.dt_s),
            cda_enabled=True,
            cda_full_steps=2,
            init="steady_state",
            init_frequency_Hz=FREQUENCY_HZ,
        )
        trv_probes: dict = {}
        bus_probes: dict = {}
        motor_probes: dict = {}
        current_probes: dict = {}
        for ph, n_src, n_load, n_mot in zip(
            PHASES, NODES_CB_SOURCE, NODES_CB_LOAD, NODES_MOTOR
        ):
            trv_probes[ph] = solver.add_probe(
                DifferentialVoltageProbe(f"trv_{ph}", n_src, n_load)
            )
            bus_probes[ph] = solver.add_probe(NodeVoltageProbe(f"v_{n_load}", n_load))
            motor_probes[ph] = solver.add_probe(NodeVoltageProbe(f"v_{n_mot}", n_mot))
            current_probes[ph] = solver.add_probe(
                BranchCurrentProbe(f"i_vcb_{ph}", ckt.get(f"vcb_{ph}"))
            )

        controllers = (
            tuple(poles)
            + ((gate,) if gate is not None else ())
            + tuple(f.controller for f in flashovers)
        )
        return AtpReferenceModel(
            case=self,
            reference=reference,
            thevenin=thevenin,
            circuit=ckt,
            solver=solver,
            poles=poles,
            snubbers=snubbers,
            snubber_gate=gate,
            literal_poles=literal_poles,
            arresters=arresters,
            flashovers=flashovers,
            controllers=controllers,
            trv_probes=trv_probes,
            bus_probes=bus_probes,
            motor_probes=motor_probes,
            current_probes=current_probes,
        )


# ---------------------------------------------------------------------------
# Montagem executável e confronto com a listagem
# ---------------------------------------------------------------------------


@dataclass
class ValidationRow:
    """Uma grandeza confrontada com a listagem do ATP.

    Attributes
    ----------
    quantity:
        Rótulo da grandeza (nó ou ramo).
    kind:
        ``"tensao"`` ou ``"corrente"``.
    reference:
        Fasor publicado [V ou A de pico].
    obtained:
        Fasor da solução fasorial deste motor.
    """

    quantity: str
    kind: str
    reference: complex
    obtained: complex

    @property
    def error(self) -> float:
        """Erro relativo COMPLEXO ``|obtido − referência| / |referência|``."""
        ref = abs(self.reference)
        if ref <= 0.0:
            return float(abs(self.obtained))
        return float(abs(self.obtained - self.reference) / ref)

    @property
    def magnitude_error(self) -> float:
        """Erro relativo de MÓDULO."""
        ref = abs(self.reference)
        if ref <= 0.0:
            return float(abs(self.obtained))
        return float(abs(abs(self.obtained) - ref) / ref)

    @property
    def angle_error_deg(self) -> float:
        """Diferença de ângulo [graus], no intervalo (−180, 180]."""
        if abs(self.reference) <= 0.0 or abs(self.obtained) <= 0.0:
            return 0.0
        d = math.degrees(cmath.phase(self.obtained / self.reference))
        return float(d)

    def as_dict(self) -> dict:
        """Linha pronta para tabela de laudo."""
        return {
            "grandeza": self.quantity,
            "tipo": self.kind,
            "referencia": f"{abs(self.reference):.6g}∠{math.degrees(cmath.phase(self.reference)):.4f}°",
            "obtido": f"{abs(self.obtained):.6g}∠{math.degrees(cmath.phase(self.obtained)):.4f}°",
            "erro_relativo": self.error,
            "erro_modulo": self.magnitude_error,
            "erro_angulo_graus": self.angle_error_deg,
        }


@dataclass
class AtpReferenceModel:
    """Montagem executável do caso ancorado na listagem do ATP.

    Attributes
    ----------
    case, reference, thevenin:
        Parâmetros, referência lida e equivalente deduzido.
    circuit, solver:
        Circuito montado e solver configurado (partida em regime).
    poles, snubbers, snubber_gate, controllers:
        Controladores da manobra.
    trv_probes, bus_probes, motor_probes, current_probes:
        Sondas por fase.
    """

    case: AtpReferenceCase
    reference: AtpReference
    thevenin: TheveninEquivalent
    circuit: Circuit
    solver: Solver
    poles: tuple
    snubbers: tuple[SnubberBranch, ...]
    snubber_gate: "SnubberArmingGate | SnubberMasterTrigger | None"
    literal_poles: tuple[AtpLiteralPole, ...]
    arresters: tuple = ()
    flashovers: tuple = ()
    controllers: tuple = ()
    trv_probes: dict = field(default_factory=dict)
    bus_probes: dict = field(default_factory=dict)
    motor_probes: dict = field(default_factory=dict)
    current_probes: dict = field(default_factory=dict)
    _phasor: object = None

    # -- execução -----------------------------------------------------------

    def run(self, t_end: float | None = None) -> SolverResult:
        """Executa a janela do caso e devolve as estatísticas do solver."""
        for ctrl in self.controllers:
            reset = getattr(ctrl, "reset", None)
            if callable(reset):
                reset()
        return self.solver.run(
            t_end=float(t_end) if t_end is not None else float(self.case.t_end_s),
            controllers=list(self.controllers),
        )

    # -- solução fasorial ---------------------------------------------------

    def phasor_solution(self):
        """Solução fasorial do circuito montado, com semeadura dos históricos.

        É a MESMA chamada que ``Solver.run`` faz na partida em regime
        permanente, de modo que o que se valida aqui é exatamente o
        estado de que a marcha no tempo parte.
        """
        if self._phasor is None:
            from app.simulation.emt.steady_state import initialize_steady_state

            self._phasor = initialize_steady_state(
                self.circuit, float(self.case.dt_s), frequency_Hz=FREQUENCY_HZ
            )
        return self._phasor

    def _switch_currents(self) -> np.ndarray:
        """Correntes dos três polos no sentido de jusante [A de pico]."""
        sol = self.phasor_solution()
        return np.array(
            [sol.branch_phasor(f"vcb_{ph}")[1] for ph in PHASES], dtype=complex
        )

    def _motor_currents(self) -> np.ndarray:
        """Correntes que entram no ramo do motor [A de pico]."""
        sol = self.phasor_solution()
        return np.array(
            [sol.branch_phasor(f"mot_r_{ph}")[1] for ph in PHASES], dtype=complex
        )

    def phasor_validation(self) -> list[ValidationRow]:
        """Confronta CADA grandeza publicada com a solução deste motor.

        Returns
        -------
        list[ValidationRow]
            Treze tensões nodais (``X0029``, ``X0002``, ``01AT``,
            ``XX0003``) e seis correntes de ramo (disjuntor e motor).
        """
        sol = self.phasor_solution()
        rows: list[ValidationRow] = []
        for prefix in ("X0029", "X0002", "01AT"):
            for s in PHASE_SUFFIX:
                node = f"{prefix}{s}"
                rows.append(
                    ValidationRow(
                        quantity=node,
                        kind="tensao",
                        reference=self.reference.node(node),
                        obtained=sol.node_phasor(node),
                    )
                )
        rows.append(
            ValidationRow(
                quantity=NODE_NEUTRAL,
                kind="tensao",
                reference=self.reference.node(NODE_NEUTRAL),
                obtained=sol.node_phasor(NODE_NEUTRAL),
            )
        )
        i_ref = self.reference.breaker_currents()
        i_obt = self._switch_currents()
        for k, ph in enumerate(PHASE_SUFFIX):
            rows.append(
                ValidationRow(
                    quantity=f"I disjuntor fase {ph}",
                    kind="corrente",
                    reference=i_ref[k],
                    obtained=i_obt[k],
                )
            )
        m_ref = self.reference.motor_currents()
        m_obt = self._motor_currents()
        for k, ph in enumerate(PHASE_SUFFIX):
            rows.append(
                ValidationRow(
                    quantity=f"I motor fase {ph}",
                    kind="corrente",
                    reference=m_ref[k],
                    obtained=m_obt[k],
                )
            )
        return rows

    def max_phasor_error(self, kind: str | None = None) -> float:
        """Maior erro relativo da validação fasorial, opcionalmente por tipo."""
        rows = self.phasor_validation()
        if kind is not None:
            rows = [r for r in rows if r.kind == str(kind)]
        return max((r.error for r in rows), default=0.0)

    # -- balanço de potência ------------------------------------------------

    def power_balance(self) -> dict:
        """Perdas por elemento e confronto com a perda total da listagem.

        Em regime permanente senoidal os elementos reativos não consomem
        potência ativa média, de modo que a potência entregue pelas três
        f.e.m. do equivalente é a perda total da rede montada. Com fasores
        de PICO, ``P = ½·Re{V̂·Î*}``.

        A referência é a perda total de 997 130,9 W impressa pela listagem
        [FATO: listagem]. A rede montada aqui não inclui o ramo
        fonte–triângulo do lado de 13,8 kV nem as perdas transversais da
        linha a montante — donde um déficit esperado da ordem de 10⁻⁴.
        """
        sol = self.phasor_solution()

        def _p(name: str, index: int = 0) -> float:
            v, i = sol.branch_phasor(name, index)
            return 0.5 * float(np.real(v * np.conj(i)))

        delivered = -sum(_p(f"E_{ph}") for ph in PHASES)
        motor = sum(_p(f"mot_r_{ph}") for ph in PHASES)
        link = sum(_p(f"link_r_{ph}") for ph in PHASES)
        z1 = sum(_p(f"z1_r_{ph}") for ph in PHASES)
        magnetizing = sum(_p(f"rmag_{ph}") for ph in PHASES)
        neutral = _p("rn")
        cable = sum(_p("cabo_jusante", k) for k in range(6))
        snubber = sum(_p(f"{b.name}_rs") for b in self.snubbers)
        total = motor + link + z1 + magnetizing + neutral + cable + snubber
        return {
            "fornecida_W": delivered,
            "motor_W": motor,
            "cabo_jusante_W": cable,
            "ligacao_W": link,
            "z1_W": z1,
            "neutro_W": neutral,
            "magnetizacao_W": magnetizing,
            "amortecedor_W": snubber,
            "total_dissipado_W": total,
            "referencia_W": float(self.reference.total_loss_W),
            "erro_relativo": abs(total - float(self.reference.total_loss_W))
            / float(self.reference.total_loss_W),
            "residuo_interno_W": abs(delivered - total),
        }

    # -- leituras da manobra -------------------------------------------------

    @property
    def reignition_counts(self) -> dict[str, int]:
        """Reignições por fase, nos dois modos.

        O contador do modo padrão está no próprio controlador; o do modo
        literal está no registro de auditoria ``result``, porque o MODEL
        do arquivo não publica contador nenhum.
        """
        out: dict[str, int] = {}
        for ph, pole in zip(PHASES, self.poles):
            contador = getattr(pole, "reignition_count", None)
            if contador is None:
                contador = getattr(pole, "result", None)
                contador = getattr(contador, "reignition_count", 0)
            out[ph] = int(contador)
        return out

    @property
    def chopping_times_s(self) -> dict[str, float | None]:
        """Instante do corte de corrente por fase [s], nos dois modos.

        ``None`` quando o polo não chegou a cortar dentro da janela.
        """
        out: dict[str, float | None] = {}
        for ph, pole in zip(PHASES, self.poles):
            t = getattr(pole, "chopping_time_s", None)
            if t is None:
                registro = getattr(pole, "result", None)
                t = getattr(registro, "chopping_time_s", None)
            out[ph] = None if t is None else float(t)
        return out

    def motor_voltage_summary(self) -> dict[str, float]:
        """Maior módulo de tensão no TERMINAL do motor por fase [kV].

        Grandeza que a Tabela III do trabalho de referência NÃO publica e
        que é a que interessa ao modelo de dano do isolamento: é nela que
        a frente de onda incide, depois do cabo.
        """
        out: dict[str, float] = {}
        for ph, probe in self.motor_probes.items():
            if probe.n_samples == 0:
                out[ph] = 0.0
                continue
            out[ph] = float(np.max(np.abs(probe.values))) * 1.0e-3
        return out

    @property
    def snubber_energy_J(self) -> dict[str, float]:
        """Energia dissipada em ``R_s`` por fase [J]."""
        return {
            ph: branch.controller.energy_J
            for ph, branch in zip(PHASES, self.snubbers)
        }

    def trv_summary(self) -> dict[str, tuple[float, float]]:
        """Pico de TRV [kV] com sinal e maior ``dv/dt`` [kV/µs] por fase."""
        out: dict[str, tuple[float, float]] = {}
        for ph, probe in self.trv_probes.items():
            if probe.n_samples < 2:
                out[ph] = (0.0, 0.0)
                continue
            v_kV = probe.values * 1.0e-3
            t_us = probe.time_s * 1.0e6
            idx = int(np.argmax(np.abs(v_kV)))
            dv = np.diff(v_kV)
            dtu = np.diff(t_us)
            with np.errstate(divide="ignore", invalid="ignore"):
                slope = np.where(dtu > 0.0, np.abs(dv) / np.where(dtu > 0.0, dtu, 1.0), 0.0)
            out[ph] = (float(v_kV[idx]), float(np.max(slope)) if slope.size else 0.0)
        return out

    def steady_state_drift(self) -> dict[str, float]:
        """Maior desvio entre a marcha no tempo e a onda fasorial, por fase.

        Compara a série de cada sonda de tensão do motor com
        ``Re{V̂·e^{jωt}}`` da solução fasorial, no intervalo já percorrido.
        Com o disjuntor mantido fechado o resultado mede EXCLUSIVAMENTE o
        transitório espúrio de partida — o que a semeadura de regime deve
        eliminar.
        """
        sol = self.phasor_solution()
        omega = sol.omega_rad_s
        out: dict[str, float] = {}
        for ph, node in zip(PHASES, NODES_MOTOR):
            probe = self.motor_probes[ph]
            if probe.n_samples == 0:
                out[ph] = 0.0
                continue
            v_hat = sol.node_phasor(node)
            expected = np.real(v_hat * np.exp(1j * omega * probe.time_s))
            out[ph] = float(np.max(np.abs(probe.values - expected)))
        return out


def build_reference_model(
    *,
    with_snubber: bool = True,
    **kwargs,
) -> AtpReferenceModel:
    """Devolve o caso do arquivo ATP montado e pronto para simular.

    É o ponto de entrada do módulo::

        modelo = build_reference_model(with_snubber=True)
        modelo.run()
        modelo.trv_summary()

    Parameters
    ----------
    with_snubber:
        ``True`` (padrão) monta a variante com ramo amortecedor, que é a
        da listagem de referência.
    **kwargs:
        Repassados a :class:`AtpReferenceCase`.

    Returns
    -------
    AtpReferenceModel
        Montagem executável, com a referência e o equivalente deduzido
        acessíveis para auditoria.
    """
    return AtpReferenceCase(with_snubber=bool(with_snubber), **kwargs).build()


# ---------------------------------------------------------------------------
# Limitações declaradas do módulo
# ---------------------------------------------------------------------------

KNOWN_LIMITATIONS: dict[str, str] = {
    "emt_atp_ref_transformer_not_decoded": (
        "A matriz acoplada 6×6 do transformador sob a opção USE AR NÃO foi "
        "decodificada. A rede a montante entra pelo equivalente de Thévenin "
        "deduzido da solução fasorial publicada, o que reproduz o REGIME "
        "PERMANENTE e a impedância vista do nó X0029 em 60 Hz, mas NÃO "
        "reproduz a resposta em frequência do transformador nem o caminho "
        "capacitivo entre enrolamentos — que é o caminho dominante de "
        "transferência de surto de frente rápida para o lado de 13,8 kV."
    ),
    "emt_atp_ref_upstream_lumped": (
        "A linha a montante (X0029 → X0001, modelo JMarti no arquivo) é "
        "representada por sua impedância equivalente por fase em 60 Hz, "
        "extraída da própria solução fasorial. A dependência de frequência e "
        "o tempo de trânsito dessa linha NÃO são representados: reflexões no "
        "trecho a montante do disjuntor não aparecem, e a TRV calculada é, "
        "quanto a elas, otimista."
    ),
    "emt_atp_ref_real_modal_matrix": (
        "O cabo a jusante usa a PARTE REAL da matriz de transformação modal "
        "punçada no arquivo, porque o modelo de Bergeron no domínio do tempo "
        "não admite transformação complexa. A leitura complexa que o ATP usa "
        "em sua própria solução fasorial difere desta EXCLUSIVAMENTE em "
        "sequência zero (ΔZ₀ = 0,636 + j0,095 Ω e acoplamento zero–direta de "
        "0,0116 Ω) e é NÃO PASSIVA: Re[Z_ph] tem autovalor −0,513 Ω. Nenhum "
        "modelo fisicamente realizável reproduz exatamente aquela solução; o "
        "resíduo observado é cota inferior do desvio de qualquer modelo "
        "passivo."
    ),
    "emt_atp_ref_arc_branch_not_represented": (
        "O ramo R-L-C de arco em paralelo com cada polo (tipo 91 comandado "
        "por TACS: R de arco 20 Ω, R de aberto 1 MΩ, C de aberto 6 µF) NÃO é "
        "montado por padrão. O polo é a chave IDEAL do kernel; a "
        "capacitância de gap pode ser incluída por gap_capacitance_F, e "
        "muda materialmente a TRV. A listagem declara que as resistências "
        "variáveis no tempo são ignoradas na solução fasorial, de modo que a "
        "ANCORAGEM DE REGIME não é afetada por essa omissão."
    ),
    "emt_atp_ref_literal_model_defect": (
        "No modo de compatibilidade LITERAL (atp_model_compatibility=True) o "
        "caso executa o MODEL do arquivo ao pé da letra, INCLUSIVE o defeito "
        "de ordem em I_PREV: 'I_PREV := I_CB' está dentro do bloco "
        "'IF TNOW > TIME_PREV', que precede o teste de passagem por zero, de "
        "modo que o teste compara a corrente com ela mesma. Consequência "
        "verificada: T_ZERO permanece em -1, V_WITH permanece nulo, NENHUMA "
        "reignição é declarada e a segunda condição de extinção nunca é "
        "atendida. Os valores de TRV obtidos no modo literal são, portanto, "
        "os de uma interrupção ÚNICA no corte de corrente, e não os de uma "
        "sequência de reignições. Use zero_crossing_order="
        "ATP_ZERO_ORDER_DEFERRED para a leitura em que o teste compara "
        "amostras consecutivas — que é [INFERÊNCIA FÍSICA] sobre a intenção "
        "do autor do MODEL, não o que o arquivo executa."
    ),
    "emt_atp_ref_dielectric_timer": (
        "O temporizador da recuperação dielétrica do MODEL do arquivo é "
        "reiniciado a cada PASSAGEM POR ZERO da corrente; o do kernel é "
        "reiniciado na EXTINÇÃO do arco. As duas leis coincidem quando a "
        "extinção ocorre no zero de corrente e divergem após corte de "
        "corrente com reacendimento, em que o MODEL do arquivo é mais "
        "permissivo."
    ),
    "emt_atp_ref_valve_ideal": (
        "As válvulas do ramo amortecedor são o par ideal do módulo de "
        "snubber, sem queda direta de condução nem tempo de desionização "
        "(que a listagem declara nulo). A tensão de disparo de 2404 V é "
        "1,0009 vez a tensão nominal fase-terra eficaz e o pico de regime no "
        "barramento é 3386 V: uma vez habilitado pelo controlador mestre, o "
        "ramo conduz em praticamente todo semiciclo, e é assim que o modelo "
        "se comporta."
    ),
}


__all__ = [
    "REFERENCE_JSON_PATH",
    "PHASES",
    "PHASE_SUFFIX",
    "FREQUENCY_HZ",
    "DT_S",
    "T_END_S",
    "NEUTRAL_RESISTANCE_OHM",
    "MAGNETIZING_RESISTANCE_OHM",
    "MOTOR_RESISTANCE_OHM",
    "MOTOR_INDUCTANCE_H",
    "SOURCE_PEAK_V",
    "CABLE_MODAL_SURGE_OHM",
    "CABLE_MODAL_VELOCITY",
    "CABLE_MODAL_RESISTANCE_OHM",
    "CABLE_TI_COMPLEX",
    "CABLE_PHASOR_REAL",
    "CABLE_PHASOR_COMPLEX",
    "CABLE_PHASOR_READINGS",
    "VCB_SEPARATION_TIME_S",
    "VCB_CHOPPING_CURRENT_A",
    "VCB_DIDT_CAPABILITY_A_PER_US",
    "VCB_REIGNITION_FACTOR",
    "SNUBBER_BREAKOVER_V",
    "SNUBBER_RESISTANCE_OHM",
    "SNUBBER_HOLDING_CURRENT_A",
    "TOTAL_NETWORK_LOSS_W",
    "NODES_X0029",
    "NODES_CB_SOURCE",
    "NODES_CB_LOAD",
    "NODES_MOTOR",
    "NODE_NEUTRAL",
    "AtpReference",
    "load_reference",
    "TheveninEquivalent",
    "derive_thevenin",
    "CoupledBergeronCable",
    "build_downstream_cable",
    "downstream_cable_modal_data",
    "downstream_cable_modal_lc",
    "phase_series_impedance",
    "phase_shunt_admittance",
    "SnubberArmingGate",
    "ATP_ZERO_ORDER_LITERAL",
    "ATP_ZERO_ORDER_DEFERRED",
    "AtpReferenceCase",
    "AtpReferenceModel",
    "ValidationRow",
    "build_reference_model",
    "KNOWN_LIMITATIONS",
]
