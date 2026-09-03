"""
tests/test_emt_referencia_eee873.py — TESTES DE ACEITAÇÃO do motor EMT
dedicado contra os casos de referência das listas de exercícios de
EEE873 (Análise de Redes Elétricas no Domínio do Tempo, PPGEE/UFMG,
prof. Alberto de Conti), resolvidos pelo autor em rotina própria e
validados contra o ATP.

Diferença em relação aos demais arquivos de teste do pacote
==========================================================

``test_emt_kernel.py`` e ``test_emt_vcb_snubber.py`` verificam o motor
contra soluções fechadas montadas nesta sessão. Aqui a referência é
EXTERNA e PUBLICADA: cada valor confrontado consta de tabela, figura ou
listagem de [LISTA: 01] ou [LISTA: 02], e a maior parte deles foi
conferida pelo próprio autor contra o ATP. São, portanto, testes de
ACEITAÇÃO — não medem a coerência interna do motor, medem se ele
reproduz um resultado já auditado por um solucionador independente.

O critério de aceite mais forte do conjunto é o pico da TRV da Questão 2
da Lista 02, **504,292 V**, valor que o autor obteve tanto na rotina
própria quanto no ATP [LISTA: 02, Tabela 3].

Política de tolerâncias
=======================

Nenhuma tolerância é ajustada para fazer um teste passar. A regra
adotada, declarada teste a teste, é:

1. Valor publicado com ``d`` casas decimais ⇒ tolerância de MEIA UNIDADE
   na última casa publicada (é a incerteza do próprio arredondamento).
   É o caso do pico da TRV: publicado como 504,292 V ⇒ tolerância
   5·10⁻⁴ V.
2. Valor publicado com ``s`` algarismos significativos em notação
   científica (tabelas de desvio, p. ex. ``2,055 × 10⁻³ A``) ⇒
   tolerância relativa de meia unidade no último significativo.
3. Expoente de convergência estimado por ajuste linear ⇒ tolerância
   absoluta de 0,02 no expoente, que é a resolução com que o autor o
   publica (``p = 2,00``, ``p = 1,00``, ``p = 1,02``, ``p = 1,998``).
4. Configuração do motor DIFERENTE da do autor (CDA ligado, onde a
   rotina dele é trapezoidal pura) ⇒ a tolerância é afrouxada, mas o
   afrouxamento é JUSTIFICADO no próprio teste e o valor obtido fica
   registrado no comentário.

Correspondência entre a rotina do autor e a API do motor
========================================================

Instante de comutação. O controlador
:class:`app.simulation.emt.TimedSwitchController` é chamado com o
instante JÁ RESOLVIDO (início do passo), de modo que a mudança de estado
só se reflete na solução do passo SEGUINTE — a convenção do ATP. A
rotina do autor decide dentro do passo (``fechada = t(n) >= t0``, a
regra das notas de aula). As duas convenções são obtidas deslocando
``close_time_s``:

* regra das notas (fechada em ``t >= t0``): ``close_time_s = t0 − 1,25·Δt``
  — o controlador comuta em ``t = t0 − Δt`` e o passo que CHEGA em ``t0``
  já é resolvido com a chave fechada;
* convenção do ATP (fechada em ``t > t0``): ``close_time_s = t0 − 0,25·Δt``
  — o controlador comuta em ``t = t0`` e o passo que chega em ``t0 + Δt``
  é o primeiro fechado.

O deslocamento fracionário (−1,25 e −0,25 em vez de −1 e 0) é apenas
robustez de ponto flutuante: coloca o limiar no MEIO do intervalo entre
dois pontos da malha.

Abertura por margem de corrente. Pela mesma razão,
``ctrl.effective_open_time_s`` é o instante em que a DECISÃO foi tomada
— e é exatamente o que o ATP imprime na listagem
(``*** Open switch "N3" to "N4" after 3.23600000E-02 sec.``,
[LISTA: 02, §3.6]). O ``t_c`` tabelado pelo autor [LISTA: 02, Tabela 4]
é o primeiro instante cuja SOLUÇÃO já tem a chave aberta, isto é
``effective_open_time_s + Δt``. A função :func:`tc_numerico` faz essa
conversão em um só lugar.

Euler regressivo de passo inteiro. O motor tem dois modos de
integração: trapezoidal e Euler regressivo de MEIO passo
``h = Δt/2`` — este último é o do procedimento CDA de Lin & Martí, e foi
escolhido justamente porque produz ``G_L = h/L = Δt/(2L)`` e
``G_C = C/h = 2C/Δt``, IDÊNTICOS aos trapezoidais, mantendo a matriz
invariante. O Euler regressivo de PASSO INTEIRO pedido pela Questão 5 da
Lista 01 (``R_L = L/Δt``, ``R_C = Δt/C`` — [LISTA: 01, Tabela 1]) é o
mesmo modo com ``h = Δt``, e se obtém exatamente instanciando o
``Solver`` com ``dt = 2Δt``, forçando todos os passos a serem pares de
meios-passos (``cda_full_steps`` maior que o número de passos) e
registrando a amostra intermediária (``record_half_steps=True``). A
malha de saída resultante é ``Δt, 2Δt, 3Δt, …`` e as condutâncias
companheiras são as da Tabela 1 da Lista 01 — o que
:func:`test_l01_euler_reproduz_resistencias_da_tabela_1` verifica antes
de qualquer comparação de forma de onda. Não há aproximação envolvida:
é uma identidade algébrica entre as duas parametrizações.

Referências
===========

* [LISTA: 01] L. F. Silva, "Lista de Exercícios nº 01 — Modelagem
  numérica de indutores e capacitores e solução de circuitos lineares no
  domínio do tempo", EEE873, PPGEE/UFMG, 24 ago. 2026.
* [LISTA: 02] L. F. Silva, "Lista de Exercícios nº 02 — Análise nodal
  modificada (MNA) e modelagem de chaves na solução de transitórios de
  manobra", EEE873, PPGEE/UFMG, 14 set. 2026.
* [FONTE: H. W. Dommel, IEEE Trans. PAS-88, n. 4, pp. 388-399, 1969].
* [FONTE: C.-W. Ho, A. E. Ruehli, P. A. Brennan, IEEE Trans. CAS-22,
  n. 6, pp. 504-509, 1975].
* [FONTE: J. Lin, J. R. Martí, IEEE Trans. Power Systems, v. 5, n. 2,
  pp. 394-402, 1990].
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from app.simulation.emt import (
    MODE_BACKWARD_EULER_HALF,
    MODE_TRAPEZOIDAL,
    BranchCurrentProbe,
    Capacitor,
    Circuit,
    Inductor,
    NodeVoltageProbe,
    Resistor,
    Solver,
    Switch,
    TimedSwitchController,
    VoltageSource,
)

# ---------------------------------------------------------------------------
# Utilidades comuns
# ---------------------------------------------------------------------------


def ordem_de_convergencia(passos, erros) -> float:
    """Expoente ``p`` de ``erro ∝ Δt^p`` por ajuste linear bilogarítmico.

    Mesmo estimador das listas — ``polyfit(log(dts), log(E), 1)``
    [LISTA: 01, §6.2; LISTA: 02, §2.7].
    """
    return float(np.polyfit(np.log(np.asarray(passos, dtype=float)),
                            np.log(np.asarray(erros, dtype=float)), 1)[0])


def picos_locais(y) -> list[float]:
    """Máximos locais estritos de uma série (equivalente a ``islocalmax``)."""
    v = np.asarray(y, dtype=float)
    return [float(v[k]) for k in range(1, v.size - 1)
            if v[k] > v[k - 1] and v[k] > v[k + 1]]


def tc_numerico(controller: TimedSwitchController, dt: float) -> float:
    """``t_c`` na convenção da Tabela 4 da Lista 02 [s].

    ``effective_open_time_s`` é o instante em que a decisão de abrir foi
    tomada — o que o ATP imprime na listagem. O ``t_c`` tabelado é o
    primeiro instante cuja SOLUÇÃO já tem a chave aberta, um passo
    adiante.
    """
    assert controller.effective_open_time_s is not None, "a chave não abriu"
    return float(controller.effective_open_time_s) + float(dt)


# ===========================================================================
# LISTA 01 — Exemplo A: RLC série excitado por degrau
# ===========================================================================
#
#   v1 ──[R]── v2 ──[L]── v3 ──[C]── gnd
#   (fonte)
#
#   vs(t) = 10·u(t) V, R = 100 Ω, L = 1 mH, C = 1 nF, c.i. nulas
#   [LISTA: 01, §3 e Apêndice A, parametros_exemploA.m]

L01_VS = 10.0          # amplitude do degrau [V]
L01_R = 100.0          # [Ω]
L01_L = 1.0e-3         # [H]
L01_C = 1.0e-9         # [F]
L01_DT = 0.1e-6        # passo adotado [s] — [LISTA: 01, §4.2]
L01_TMAX = 40.0e-6     # 2 constantes de tempo do envelope [s]

L01_ALPHA = L01_R / (2.0 * L01_L)                       # 5,0e4 Np/s
L01_W0 = 1.0 / math.sqrt(L01_L * L01_C)                 # 1,0e6 rad/s
L01_WD = math.sqrt(L01_W0 ** 2 - L01_ALPHA ** 2)        # 9,98749e5 rad/s

#: Passos usados no estudo de convergência [LISTA: 01, §6.2, Figura 9].
L01_PASSOS = (0.4e-6, 0.2e-6, 0.1e-6, 0.05e-6, 0.025e-6, 0.0125e-6)


def l01_analitico(t):
    """Solução de Laplace do Exemplo A [LISTA: 01, §3].

    ``i(t) = Vs/(L·ω_d)·e^{−αt}·sen(ω_d t)`` e
    ``v(t) = Vs·{1 − e^{−αt}·[cos(ω_d t) + (α/ω_d)·sen(ω_d t)]}``.
    """
    t = np.asarray(t, dtype=float)
    env = np.exp(-L01_ALPHA * t)
    i = (L01_VS / (L01_L * L01_WD)) * env * np.sin(L01_WD * t)
    v = L01_VS * (1.0 - env * (np.cos(L01_WD * t)
                               + (L01_ALPHA / L01_WD) * np.sin(L01_WD * t)))
    return v, i


def l01_circuito(*, partida_corrigida: bool = False) -> Circuit:
    """Monta o Exemplo A.

    ``partida_corrigida`` semeia o histórico do indutor com
    ``v_L(0⁺) = Vs − R·i_L(0) − v_C(0) = Vs``, isto é
    ``I_L(0) = i_L(0) + G_L·v_L(0⁺) = (Δt/2L)·Vs`` — a verificação 2 de
    [LISTA: 01, §6.2], que restaura a ordem 2 da regra trapezoidal.
    """
    ckt = Circuit("lista01_exemplo_a")
    ckt.add(VoltageSource("E", "1", "gnd", amplitude_V=0.0,
                          frequency_Hz=0.0, dc_offset_V=L01_VS))
    ckt.add(Resistor("R", "1", "2", L01_R))
    ckt.add(Inductor("L", "2", "3", L01_L,
                     initial_voltage_V=(L01_VS if partida_corrigida else 0.0)))
    ckt.add(Capacitor("C", "3", "gnd", L01_C))
    return ckt


def l01_trapezoidal(dt: float, tmax: float, *, partida_corrigida: bool = False):
    """Marcha trapezoidal pura, sem CDA — a rotina ``simula_exemploA``.

    ``cda_enabled=False`` e ``cda_at_start=False`` são obrigatórios: o
    autor parte de históricos NULOS em ``t = 0`` (partida "padrão"), sem
    o par de meios-passos de Euler regressivo que o motor aplica por
    omissão quando ``init="zero"``. Ligar o CDA na partida é justamente
    a "partida corrigida", e produziria outro número.
    """
    ckt = l01_circuito(partida_corrigida=partida_corrigida)
    solver = Solver(ckt, dt=dt, cda_enabled=False, cda_at_start=False)
    p_v = solver.add_probe(NodeVoltageProbe("v3", "3"))
    p_i = solver.add_probe(BranchCurrentProbe("i", ckt.get("R")))
    solver.run(t_end=tmax)
    return p_v.time_s, p_v.values, p_i.values


def l01_euler_regressivo(dt: float, tmax: float):
    """Marcha de Euler regressivo de PASSO INTEIRO ``Δt``.

    Obtida com ``Solver(dt=2Δt)`` e todos os passos convertidos em pares
    de meios-passos de Euler regressivo de ``h = Δt`` — ver a discussão
    no docstring do módulo. As condutâncias companheiras resultantes são
    ``G_L = 2Δt/(2L) = Δt/L`` e ``G_C = 2C/(2Δt) = C/Δt``, isto é
    ``R_L = L/Δt`` e ``R_C = Δt/C``, a linha "Euler regr." da Tabela 1 de
    [LISTA: 01].
    """
    n = int(round(tmax / dt))
    assert n % 2 == 0, "o número de passos deve ser par para fechar os pares"
    ckt = l01_circuito()
    solver = Solver(ckt, dt=2.0 * dt, cda_enabled=True, cda_at_start=True,
                    cda_full_steps=n + 2, record_half_steps=True)
    p_v = solver.add_probe(NodeVoltageProbe("v3", "3"))
    p_i = solver.add_probe(BranchCurrentProbe("i", ckt.get("R")))
    solver.run(t_end=2.0 * dt * (n // 2))
    return p_v.time_s, p_v.values, p_i.values


@pytest.fixture(scope="module")
def l01_trap():
    return l01_trapezoidal(L01_DT, L01_TMAX)


@pytest.fixture(scope="module")
def l01_euler():
    return l01_euler_regressivo(L01_DT, L01_TMAX)


@pytest.fixture(scope="module")
def l01_trap_corrigida():
    return l01_trapezoidal(L01_DT, L01_TMAX, partida_corrigida=True)


def test_l01_resistencias_companheiras_da_tabela_1():
    """``R_L = 2L/Δt = 20 kΩ`` e ``R_C = Δt/(2C) = 50 Ω``.

    Valores impressos nas notas de aula e conferidos em
    ``valida_tabela_notas.m`` [LISTA: 01, Apêndice A].
    """
    ckt = l01_circuito()
    ckt.build()
    ckt.prepare(L01_DT)
    assert ckt.get("L").conductance_S == pytest.approx(1.0 / 20000.0, rel=1e-12)
    assert ckt.get("C").conductance_S == pytest.approx(1.0 / 50.0, rel=1e-12)


def test_l01_euler_reproduz_resistencias_da_tabela_1():
    """``R_L = L/Δt`` e ``R_C = Δt/C`` na linha "Euler regr." da Tabela 1.

    Verifica a identidade que sustenta :func:`l01_euler_regressivo`
    ANTES de qualquer comparação de forma de onda: o Euler regressivo de
    passo inteiro ``Δt`` é o meio-passo do motor com ``dt = 2Δt``.
    """
    ckt = l01_circuito()
    ckt.build()
    ckt.prepare(2.0 * L01_DT)
    assert ckt.get("L").conductance_S == pytest.approx(L01_DT / L01_L, rel=1e-12)
    assert ckt.get("C").conductance_S == pytest.approx(L01_C / L01_DT, rel=1e-12)
    # Termos históricos da Tabela 1: I_L^h = i_L(t) (só a corrente) e
    # I_C^h = −(1/R_C)·v_C(t) (só a tensão), sem os termos cruzados da
    # regra trapezoidal. Os estados são impostos pelas condições iniciais
    # públicas e materializados por ``reset()``.
    ind = Inductor("Lref", "a", "b", L01_L,
                   initial_current_A=3.0, initial_voltage_V=7.0)
    cap = Capacitor("Cref", "a", "b", L01_C,
                    initial_voltage_V=7.0, initial_current_A=3.0)
    for comp in (ind, cap):
        comp.prepare(2.0 * L01_DT)
        comp.reset()
    assert ind.history_current_A(MODE_BACKWARD_EULER_HALF) == pytest.approx(3.0)
    assert cap.history_current_A(MODE_BACKWARD_EULER_HALF) == pytest.approx(
        -(L01_C / L01_DT) * 7.0, rel=1e-12
    )
    # E, para contraste, os termos trapezoidais da mesma Tabela 1, que
    # dependem dos DOIS estados.
    assert ind.history_current_A(MODE_TRAPEZOIDAL) == pytest.approx(
        3.0 + (L01_DT / L01_L) * 7.0, rel=1e-12
    )
    assert cap.history_current_A(MODE_TRAPEZOIDAL) == pytest.approx(
        -3.0 - (L01_C / L01_DT) * 7.0, rel=1e-12
    )


def test_l01_primeiro_passo_bate_com_o_atp(l01_trap):
    """``v₃(0,1 µs) = 0,024814 V`` e ``i(0,1 µs) = 0,496278 mA``.

    Valores impressos pelo ATP (solucionador ``tpbigg32``) e reproduzidos
    pela rotina do autor com a inversa exata de ``G_BB``; são distintos
    dos 0,025 V e 0,5 mA da tabela das notas de aula, que foi construída
    com coeficientes arredondados em quatro casas [LISTA: 01, §4.3].
    Tolerância: meia unidade na 6ª casa decimal publicada.
    """
    t, v, i = l01_trap
    assert t[0] == pytest.approx(L01_DT, rel=1e-12)
    assert v[0] == pytest.approx(0.024814, abs=5.0e-7)
    assert i[0] * 1e3 == pytest.approx(0.496278, abs=5.0e-7)


def test_l01_trapezoidal_contra_laplace(l01_trap):
    """Tabela 2, linha "Regra trapezoidal": 0,4749 V e 0,4971 mA.

    Percentuais publicados: 2,56 % e 5,37 % do pico. Tolerância: meia
    unidade no último algarismo publicado (5·10⁻⁵ V e 5·10⁻⁵ mA).
    """
    t, v, i = l01_trap
    v_a, i_a = l01_analitico(t)
    dv = float(np.max(np.abs(v - v_a)))
    di = float(np.max(np.abs(i - i_a)))
    assert dv == pytest.approx(0.4749, abs=5.0e-5)
    assert di * 1e3 == pytest.approx(0.4971, abs=5.0e-5)
    assert 100.0 * dv / float(np.max(np.abs(v_a))) == pytest.approx(2.56, abs=5.0e-3)
    assert 100.0 * di / float(np.max(np.abs(i_a))) == pytest.approx(5.37, abs=5.0e-3)


def test_l01_euler_regressivo_contra_laplace(l01_euler):
    """Tabela 2, linha "Euler regressivo": 2,4881 V e 2,4998 mA.

    Percentuais publicados: 13,42 % e 26,98 % — "uma ordem de grandeza
    acima do erro da regra trapezoidal para o mesmo passo"
    [LISTA: 01, §5].
    """
    t, v, i = l01_euler
    assert t[0] == pytest.approx(L01_DT, rel=1e-9)
    assert t[-1] == pytest.approx(L01_TMAX, rel=1e-9)
    v_a, i_a = l01_analitico(t)
    dv = float(np.max(np.abs(v - v_a)))
    di = float(np.max(np.abs(i - i_a)))
    assert dv == pytest.approx(2.4881, abs=5.0e-5)
    assert di * 1e3 == pytest.approx(2.4998, abs=5.0e-5)
    assert 100.0 * dv / float(np.max(np.abs(v_a))) == pytest.approx(13.42, abs=5.0e-3)
    assert 100.0 * di / float(np.max(np.abs(i_a))) == pytest.approx(26.98, abs=5.0e-3)


def test_l01_euler_e_uma_ordem_de_grandeza_pior(l01_trap, l01_euler):
    """Conclusão qualitativa de [LISTA: 01, §5], verificada como razão."""
    t, v_t, _ = l01_trap
    _, v_e, _ = l01_euler
    v_a, _ = l01_analitico(t)
    razao = float(np.max(np.abs(v_e - v_a))) / float(np.max(np.abs(v_t - v_a)))
    assert razao > 5.0


def test_l01_picos_sucessivos_tabela_3(l01_trap, l01_euler):
    """Tabela 3 — picos sucessivos da corrente e desvio percentual.

    É este o teste que distingue a NATUREZA dos dois erros
    [LISTA: 01, §6.1]:

    * trapezoidal — erro de FASE: a amplitude é preservada, o desvio
      permanece abaixo de 0,15 % e NÃO se acumula (chega a trocar de
      sinal no 5º pico);
    * Euler regressivo — erro de AMPLITUDE: amortecimento numérico que
      cresce monotonicamente de −7,18 % no 1º pico a −73,54 % no 5º.
    """
    _, _, i_t = l01_trap
    _, _, i_e = l01_euler
    t, _, _ = l01_trap
    _, i_a = l01_analitico(t)

    pa = picos_locais(i_a)
    pt = picos_locais(i_t)
    pe = picos_locais(i_e)
    assert min(len(pa), len(pt), len(pe)) >= 5

    ref_analitico = (9.2645, 6.7653, 4.9398, 3.6067, 2.6331)      # [mA]
    ref_trap = (9.2534, 6.7589, 4.9368, 3.6058, 2.6337)           # [mA]
    ref_euler = (8.5995, 4.5875, 2.4480, 1.3067, 0.6968)          # [mA]
    ref_desvio_trap = (-0.12, -0.09, -0.06, -0.02, +0.02)         # [%]
    ref_desvio_euler = (-7.18, -32.19, -50.44, -63.77, -73.54)    # [%]

    for k in range(5):
        assert pa[k] * 1e3 == pytest.approx(ref_analitico[k], abs=5.0e-5)
        assert pt[k] * 1e3 == pytest.approx(ref_trap[k], abs=5.0e-5)
        assert pe[k] * 1e3 == pytest.approx(ref_euler[k], abs=5.0e-5)
        d_t = 100.0 * (pt[k] - pa[k]) / pa[k]
        d_e = 100.0 * (pe[k] - pa[k]) / pa[k]
        assert d_t == pytest.approx(ref_desvio_trap[k], abs=5.0e-3)
        assert d_e == pytest.approx(ref_desvio_euler[k], abs=5.0e-3)

    # Natureza do erro, enunciada em §6.1 e verificada aqui.
    assert max(abs(100.0 * (pt[k] - pa[k]) / pa[k]) for k in range(5)) < 0.15
    desvios_euler = [100.0 * (pe[k] - pa[k]) / pa[k] for k in range(5)]
    assert all(desvios_euler[k + 1] < desvios_euler[k] for k in range(4)), (
        "o amortecimento numérico do Euler regressivo deve crescer "
        "monotonicamente pico a pico"
    )


def test_l01_erro_trapezoidal_e_de_fase_nao_de_amplitude(l01_trap):
    """Assinatura de erro de fase: a analítica DESLOCADA de Δt/2 cola.

    "Comparando a solução numérica com a analítica avaliada em
    ``t − Δt/2``, o erro máximo em v(t) cai de 0,4749 V para 0,0613 V,
    uma redução de 7,8 vezes" [LISTA: 01, §6.2, verificação 1].

    Tolerância afrouxada de 5·10⁻⁵ para 1·10⁻⁴ V, com justificativa: o
    autor cita o MESMO 0,0613 V para as duas verificações do §6.2 (a
    analítica deslocada e a partida corrigida), ao passo que as duas
    dão valores ligeiramente distintos — 0,06125 V aqui e 0,06130 V na
    partida corrigida, que é a entrada da Tabela 2 e é reproduzida com a
    tolerância estrita em
    :func:`test_l01_partida_corrigida_tabela_2`. A afirmação verificável
    é a do "mesmo patamar" e a da redução de 7,8 vezes.
    """
    t, v, _ = l01_trap
    v_a, _ = l01_analitico(t)
    v_shift, _ = l01_analitico(t - 0.5 * L01_DT)
    e0 = float(np.max(np.abs(v - v_a)))
    e1 = float(np.max(np.abs(v - v_shift)))
    assert e1 == pytest.approx(0.0613, abs=1.0e-4)
    assert e0 / e1 == pytest.approx(7.8, abs=0.1)


def test_l01_partida_corrigida_tabela_2(l01_trap_corrigida):
    """Tabela 2, linha "Trapezoidal, partida corrigida": 0,0613 V / 0,0612 mA.

    Semeadura ``I_L(0) = (Δt/2L)·Vs``, que no motor é o par
    ``initial_current_A = 0`` e ``initial_voltage_V = Vs`` do indutor —
    exatamente ``I_L(0) = i_L(0) + G_L·v_L(0)`` [LISTA: 02, eq. (6)].
    """
    t, v, i = l01_trap_corrigida
    v_a, i_a = l01_analitico(t)
    dv = float(np.max(np.abs(v - v_a)))
    di = float(np.max(np.abs(i - i_a)))
    assert dv == pytest.approx(0.0613, abs=5.0e-5)
    assert di * 1e3 == pytest.approx(0.0612, abs=5.0e-5)
    assert 100.0 * dv / float(np.max(np.abs(v_a))) == pytest.approx(0.33, abs=5.0e-3)
    assert 100.0 * di / float(np.max(np.abs(i_a))) == pytest.approx(0.66, abs=5.0e-3)


@pytest.fixture(scope="module")
def l01_convergencia():
    """Erro máximo em ``v(t)`` para cada passo e cada método."""
    e_trap, e_euler, e_corr = [], [], []
    for dt in L01_PASSOS:
        t, v, _ = l01_trapezoidal(dt, L01_TMAX)
        v_a, _ = l01_analitico(t)
        e_trap.append(float(np.max(np.abs(v - v_a))))

        t, v, _ = l01_trapezoidal(dt, L01_TMAX, partida_corrigida=True)
        v_a, _ = l01_analitico(t)
        e_corr.append(float(np.max(np.abs(v - v_a))))

        t, v, _ = l01_euler_regressivo(dt, L01_TMAX)
        v_a, _ = l01_analitico(t)
        e_euler.append(float(np.max(np.abs(v - v_a))))
    return e_trap, e_corr, e_euler


def test_l01_ordem_de_convergencia_observada(l01_convergencia):
    """[LISTA: 01, §6.2, Figura 9]: p = 1,02 / 1,998 / 0,73.

    Reproduz a CONCLUSÃO da lista, não apenas os números:

    * o Euler regressivo mede ``p = 0,73``, "compatível com a ordem 1
      esperada";
    * a regra trapezoidal com partida padrão mede ``p = 1,02``, e NÃO os
      2 teóricos, porque a integração do primeiro intervalo usa
      ``v_L(0⁻) = 0`` e não ``v_L(0⁺) = Vs``, o que equivale a aplicar o
      degrau em ``t = Δt/2`` — um atraso fixo de meio passo, de PRIMEIRA
      ordem em Δt, que domina o erro;
    * corrigida a partida, ``p = 1,998`` — a ordem 2 teórica é
      recuperada.
    """
    e_trap, e_corr, e_euler = l01_convergencia
    p_trap = ordem_de_convergencia(L01_PASSOS, e_trap)
    p_corr = ordem_de_convergencia(L01_PASSOS, e_corr)
    p_euler = ordem_de_convergencia(L01_PASSOS, e_euler)

    assert p_trap == pytest.approx(1.02, abs=0.02)
    assert p_corr == pytest.approx(1.998, abs=0.02)
    assert p_euler == pytest.approx(0.73, abs=0.02)

    # A conclusão física: a correção de partida sobe a ordem de ~1 para ~2.
    assert p_corr - p_trap > 0.9
    # E o Euler regressivo é de primeira ordem, abaixo da trapezoidal.
    assert p_euler < p_trap < p_corr


def test_l01_erro_decresce_monotonicamente_com_o_passo(l01_convergencia):
    """Sanidade da malha de convergência: nenhum patamar de arredondamento."""
    for serie in l01_convergencia:
        assert all(serie[k + 1] < serie[k] for k in range(len(serie) - 1))


# ===========================================================================
# LISTA 02 — Questão 1: curto-circuito na carga de um circuito RL
# ===========================================================================
#
#   1 ──[R1]── 2 ──[L]── 3 ──┬──[R2]── gnd
#                            └──/ chave (fecha em t0)
#
#   vs(t) = 100·cos(377 t) V, R1 = 0,5 Ω, L = 25 mH, R2 = 20 Ω, t0 = 80 ms
#   [LISTA: 02, §2.1 e Apêndice A, parametros_lista02.m]

L02_VM = 100.0                       # amplitude da fonte [V]
L02_W = 377.0                        # [rad/s]
L02_F = L02_W / (2.0 * math.pi)      # 60,001414 Hz — o valor do cartão do ATP

Q1_R1, Q1_L, Q1_R2 = 0.5, 25.0e-3, 20.0
Q1_T0 = 80.0e-3
Q1_DT = 10.0e-6
Q1_TMAX = 0.40

Q1_Z_ABERTA = Q1_R1 + 1j * L02_W * Q1_L + Q1_R2
Q1_Z_FECHADA = Q1_R1 + 1j * L02_W * Q1_L
Q1_I_ABERTA = L02_VM / Q1_Z_ABERTA
Q1_I_FECHADA = L02_VM / Q1_Z_FECHADA
Q1_TAU = Q1_L / Q1_R1
Q1_I_T0_MENOS = float(np.real(Q1_I_ABERTA * np.exp(1j * L02_W * Q1_T0)))
Q1_I_T0_MAIS = float(np.real(Q1_I_FECHADA * np.exp(1j * L02_W * Q1_T0)))
Q1_A_NATURAL = Q1_I_T0_MENOS - Q1_I_T0_MAIS

#: Passos da Tabela 2 [LISTA: 02, §2.7]. Escritos como literais exatos
#: (``1e-4``, não ``100*1e-6``) para que ``n·Δt`` caia exatamente sobre
#: ``t0`` em precisão dupla.
Q1_PASSOS = (1.0e-4, 5.0e-5, 2.0e-5, 1.0e-5, 5.0e-6, 2.0e-6)


def q1_analitico(t):
    """Resposta completa da corrente [LISTA: 02, Apêndice A, analitico_q1.m]."""
    t = np.asarray(t, dtype=float)
    i = np.real(Q1_I_ABERTA * np.exp(1j * L02_W * t))
    m = t >= Q1_T0 - 1e-12
    i = np.array(i, dtype=float)
    i[m] = (np.real(Q1_I_FECHADA * np.exp(1j * L02_W * t[m]))
            + Q1_A_NATURAL * np.exp(-(t[m] - Q1_T0) / Q1_TAU))
    return i


def q1_circuito() -> Circuit:
    ckt = Circuit("lista02_q1")
    ckt.add(VoltageSource("E", "1", "gnd", amplitude_V=L02_VM,
                          frequency_Hz=L02_F, phase_reference="cos"))
    ckt.add(Resistor("R1", "1", "2", Q1_R1))
    ckt.add(Inductor("L", "2", "3", Q1_L))
    ckt.add(Resistor("R2", "3", "gnd", Q1_R2))
    ckt.add(Switch("SW", "3", "gnd", closed=False))
    return ckt


def q1_simula(dt: float, tmax: float, *, convencao: str = "notas",
              cda_enabled: bool = False):
    """Marcha da Questão 1, partindo do regime permanente senoidal.

    ``cda_enabled=False`` por omissão para reproduzir a rotina do autor,
    que é trapezoidal pura. O caso com CDA tem teste próprio.
    """
    ckt = q1_circuito()
    desloc = -1.25 * dt if convencao == "notas" else -0.25 * dt
    ctrl = TimedSwitchController(ckt.get("SW"), close_time_s=Q1_T0 + desloc)
    solver = Solver(ckt, dt=dt, init="steady_state", cda_enabled=cda_enabled)
    p_i = solver.add_probe(BranchCurrentProbe("i", ckt.get("L")))
    solver.run(t_end=tmax, controllers=[ctrl])
    return p_i.time_s, p_i.values, solver


@pytest.fixture(scope="module")
def q1_notas():
    return q1_simula(Q1_DT, Q1_TMAX, convencao="notas")


def test_q1_solucao_fasorial_de_partida():
    """Regime permanente com a chave aberta [LISTA: 02, §2.3, eqs. (12)-(14)].

    ``Z₁ = 22,562815 ∠24,6909° Ω``, ``Î = 4,432071 ∠−24,6909° A`` — "em
    acordo com os 4,43 A e −24,7° das notas de aula" — e a listagem do
    ATP imprime ``Î = 4,4320710624 ∠−24,6908953° A`` e
    ``i(0) = 4,02686705 A``.

    Tolerância contra a listagem do ATP: ``1·10⁻⁸`` no módulo e
    ``5·10⁻⁷`` no ângulo. Não é meia unidade no último dígito impresso
    porque o ATP resolve a solução fasorial em precisão SIMPLES e
    imprime mais dígitos do que carrega: o módulo em precisão dupla vale
    4,432071068 A (o ATP imprime …0624, desvio de 5,9·10⁻⁹) e o ângulo
    −24,690895171° (o ATP imprime …8953°, desvio de 1,3·10⁻⁷°). O desvio
    é o do próprio ATP, não do motor.
    """
    assert abs(Q1_Z_ABERTA) == pytest.approx(22.562815, abs=5.0e-7)
    assert math.degrees(np.angle(Q1_Z_ABERTA)) == pytest.approx(24.6909, abs=5.0e-5)
    assert abs(Q1_I_ABERTA) == pytest.approx(4.4320710624, abs=1.0e-8)
    assert math.degrees(np.angle(Q1_I_ABERTA)) == pytest.approx(-24.6908953,
                                                                abs=5.0e-7)

    _, _, solver = q1_simula(Q1_DT, 5.0 * Q1_DT)
    fasor = solver.steady_state_solution
    assert fasor is not None
    # Valores instantâneos em t = 0 — a condição inicial não nula pedida
    # no enunciado [LISTA: 02, eq. (14)].
    v2 = fasor.node_value_at("2", 0.0)
    v3 = fasor.node_value_at("3", 0.0)
    v_l, i_l = fasor.branch_phasor("L")
    assert float(np.real(i_l)) == pytest.approx(4.026867, abs=5.0e-7)
    assert v2 == pytest.approx(97.986566, abs=5.0e-7)
    assert v3 == pytest.approx(80.537341, abs=5.0e-7)
    assert float(np.real(v_l)) == pytest.approx(17.449225, abs=5.0e-7)


def test_q1_resposta_esperada_pos_curto():
    """[LISTA: 02, §2.4, eq. (15)]: Z₂, resposta forçada e natural.

    ``Z₂ = 9,438253 ∠86,9633° Ω``, ``i_f = 10,595181 cos(ωt − 86,9633°)``
    (notas: 10,60 A, −86,9°), ``i(t₀⁻) = −0,513266 A``,
    ``i_f(t₀⁺) = −9,886313 A`` e amplitude natural 9,373048 A (notas:
    9,37 A), com ``τ = L/R₁ = 50 ms``.
    """
    assert abs(Q1_Z_FECHADA) == pytest.approx(9.438253, abs=5.0e-7)
    assert math.degrees(np.angle(Q1_Z_FECHADA)) == pytest.approx(86.9633, abs=5.0e-5)
    assert abs(Q1_I_FECHADA) == pytest.approx(10.595181, abs=5.0e-7)
    assert Q1_I_T0_MENOS == pytest.approx(-0.513266, abs=5.0e-7)
    assert Q1_I_T0_MAIS == pytest.approx(-9.886313, abs=5.0e-7)
    assert Q1_A_NATURAL == pytest.approx(9.373048, abs=5.0e-7)
    assert Q1_TAU == pytest.approx(50.0e-3, rel=1e-12)


def test_q1_regime_permanente_antes_do_curto(q1_notas):
    """Antes de t₀ o desvio é o da própria integração: 2,201·10⁻⁶ A.

    É a primeira linha da coluna "antes do curto" da Tabela 2 para
    ``Δt = 10 µs`` [LISTA: 02, §2.7], e mostra que a semeadura por
    ``I_L(0) = i_L(0) + G_L·v_L(0)`` não introduz transitório espúrio de
    partida.
    """
    t, i, _ = q1_notas
    i_a = q1_analitico(t)
    pre = np.abs(i - i_a)[t < Q1_T0 - 0.5 * Q1_DT]
    assert float(np.max(pre)) == pytest.approx(2.201e-6, rel=5.0e-4)


def test_q1_primeiro_pico_de_corrente(q1_notas):
    """Pico de 18,69 A, "cerca de 1,76 vez a amplitude de regime final".

    [LISTA: 02, §2.6 e legenda da Tabela 1]. A amplitude de regime final
    é ``|Î₂| = 10,595181 A``.
    """
    t, i, _ = q1_notas
    pico = float(np.max(np.abs(i)))
    assert pico == pytest.approx(18.69, abs=5.0e-3)
    assert pico / abs(Q1_I_FECHADA) == pytest.approx(1.76, abs=5.0e-3)
    # O pico é o PRIMEIRO máximo depois do curto, e ocorre dentro de um
    # ciclo da fonte após t0.
    k = int(np.argmax(np.abs(i)))
    assert Q1_T0 < t[k] < Q1_T0 + 1.0 / L02_F


def test_q1_desvio_contra_a_solucao_analitica_tabela_1(q1_notas):
    """Tabela 1, linha 1: ``max|Δi| = 2,055·10⁻³ A`` (0,0110 % do pico)."""
    t, i, _ = q1_notas
    i_a = q1_analitico(t)
    di = float(np.max(np.abs(i - i_a)))
    assert di == pytest.approx(2.055e-3, rel=5.0e-4)
    assert 100.0 * di / float(np.max(np.abs(i_a))) == pytest.approx(0.0110,
                                                                    abs=5.0e-5)


def test_q1_convencao_do_instante_de_comutacao():
    """Tabela 1, linha 2: ``4,106·10⁻³ A`` entre as duas convenções.

    "A regra das notas de aula manda fechar a chave em todo passo com
    ``t >= t0``; o ATP avalia o estado das chaves antes de resolver cada
    passo, usando o instante anterior, de modo que o fechamento só se
    reflete na solução um passo depois. […] A diferença é de um único
    passo de tempo, fisicamente irrelevante, mas responde integralmente
    pelo desvio observado" [LISTA: 02, §2.7].

    O autor mede esse desvio contra o ATP: 4,106·10⁻³ A com a regra das
    notas, contra 1,210·10⁻⁵ A adotando a convenção do ATP. Sem o
    arquivo ``.pl4`` não há como refazer a comparação com o ATP, mas a
    grandeza que a explica é interna e reprodutível: a diferença entre
    as DUAS marchas do próprio motor, que deve valer os mesmos
    4,106·10⁻³ A — a convenção "atp" do motor é, por construção, a que
    concorda com o ATP a 1,2·10⁻⁵ A.

    Verifica-se ainda que essa diferença é uma resposta natural pura:
    injetada em ``t0``, decai com ``τ = L/R₁ = 50 ms`` e nada mais.
    """
    t_n, i_n, _ = q1_simula(Q1_DT, Q1_TMAX, convencao="notas")
    t_a, i_a, _ = q1_simula(Q1_DT, Q1_TMAX, convencao="atp")
    assert np.allclose(t_n, t_a, rtol=0, atol=1e-15)

    # Idênticas antes de t0: a divergência nasce EXATAMENTE na comutação.
    antes = t_n < Q1_T0 - 0.5 * Q1_DT
    assert float(np.max(np.abs(i_n[antes] - i_a[antes]))) < 1e-12

    d = np.abs(i_n - i_a)
    assert float(np.max(d)) == pytest.approx(4.106e-3, rel=5.0e-4)
    k_max = int(np.argmax(d))
    assert t_n[k_max] == pytest.approx(Q1_T0 + Q1_DT, abs=0.5 * Q1_DT)

    # Decaimento exponencial com τ = L/R1, sem componente forçada.
    k0 = int(np.argmin(np.abs(t_n - Q1_T0)))
    for m in range(1, 7):
        km = int(np.argmin(np.abs(t_n - (Q1_T0 + m * Q1_TAU))))
        assert d[km] == pytest.approx(float(np.max(d)) * math.exp(-m), rel=0.01)
    assert d[k0] > 1e-3

    # As duas ficam igualmente próximas da analítica — a diferença é de
    # convenção, não de qualidade.
    ana = q1_analitico(t_n)
    assert float(np.max(np.abs(i_a - ana))) == pytest.approx(
        float(np.max(np.abs(i_n - ana))), rel=0.05
    )


@pytest.fixture(scope="module")
def q1_convergencia():
    """Erro máximo antes e depois do curto, para cada passo da Tabela 2."""
    pre, pos = [], []
    for dt in Q1_PASSOS:
        t, i, _ = q1_simula(dt, Q1_TMAX)
        e = np.abs(i - q1_analitico(t))
        pre.append(float(np.max(e[t < Q1_T0 - 0.5 * dt])))
        pos.append(float(np.max(e[t > Q1_T0 - 0.5 * dt])))
    return pre, pos


def test_q1_ordem_2_antes_da_comutacao(q1_convergencia):
    """Coluna "antes do curto" da Tabela 2, reproduzida termo a termo.

    2,201·10⁻⁴ / 5,503·10⁻⁵ / 8,805·10⁻⁶ / 2,201·10⁻⁶ / 5,503·10⁻⁷ /
    8,805·10⁻⁸ A, com ``p = 2,00`` — a ordem esperada da regra
    trapezoidal entre comutações.
    """
    pre, _ = q1_convergencia
    referencia = (2.201e-4, 5.503e-5, 8.805e-6, 2.201e-6, 5.503e-7, 8.805e-8)
    for obtido, esperado in zip(pre, referencia):
        assert obtido == pytest.approx(esperado, rel=5.0e-4)
    assert ordem_de_convergencia(Q1_PASSOS, pre) == pytest.approx(2.00, abs=0.02)


def test_q1_comutacao_custa_uma_ordem_de_precisao(q1_convergencia):
    """Coluna "depois do curto": ``p = 1,00`` e a previsão fechada (16).

    ``ΔI = G_L·v₃(t₀⁻) = (Δt/2L)·R₂·|i(t₀⁻)|``, com
    ``R₂·|i(t₀⁻)| = 10,265314 V``. O autor verifica a previsão "sem
    nenhum ajuste": a razão medido/previsto converge monotonicamente
    para a unidade [LISTA: 02, Tabela 2].

    Registro honesto de uma pequena divergência. Os valores absolutos
    tabelados pelo autor (2,031·10⁻² … 4,107·10⁻⁴ A) trazem razões
    medido/previsto de 0,9894 a 1,0002; aqui elas vão de 1,0085 a
    1,0002. A causa é o instante em que a chave fecha: nas rotinas do
    autor a malha de tempo é ``(0:N−1)·Δt`` com ``Δt = 100*1e-6``, que em
    precisão dupla vale 9,999999999999999·10⁻⁵ — de modo que ``t(801)``
    cai LOGO ABAIXO de 0,08 s e a chave fecha um passo depois. Este teste
    usa os literais exatos e fecha em ``t₀``. As duas famílias
    convergem para a MESMA previsão (16) e concordam a menos de 0,2 % já
    em ``Δt = 10 µs`` — ver
    :func:`test_q1_erro_pos_comutacao_bate_com_a_tabela_2_em_passo_fino`.
    """
    _, pos = q1_convergencia
    previsto = [(dt / (2.0 * Q1_L)) * Q1_R2 * abs(Q1_I_T0_MENOS)
                for dt in Q1_PASSOS]
    assert Q1_R2 * abs(Q1_I_T0_MENOS) == pytest.approx(10.265314, abs=5.0e-7)

    razoes = [p / q for p, q in zip(pos, previsto)]
    # Convergência monotônica para a unidade, sem nenhum ajuste.
    for r in razoes:
        assert 0.98 < r < 1.02
    assert all(abs(razoes[k + 1] - 1.0) < abs(razoes[k] - 1.0)
               for k in range(len(razoes) - 1))
    assert razoes[-1] == pytest.approx(1.0, abs=5.0e-4)
    assert ordem_de_convergencia(Q1_PASSOS, pos) == pytest.approx(1.00, abs=0.02)


def test_q1_erro_pos_comutacao_bate_com_a_tabela_2_em_passo_fino(q1_convergencia):
    """Tabela 2, coluna "depois do curto", nos três passos mais finos.

    Nos passos em que a quantização do instante de comutação já é
    desprezível (10, 5 e 2 µs) os valores do autor — 2,051·10⁻³,
    1,026·10⁻³ e 4,107·10⁻⁴ A — são reproduzidos com desvio relativo
    abaixo de 0,2 %.
    """
    _, pos = q1_convergencia
    referencia = {1.0e-5: 2.051e-3, 5.0e-6: 1.026e-3, 2.0e-6: 4.107e-4}
    for dt, esperado in referencia.items():
        obtido = pos[Q1_PASSOS.index(dt)]
        assert obtido == pytest.approx(esperado, rel=2.0e-3)


def test_q1_com_cda_permanece_no_mesmo_patamar():
    """O CDA não degrada a Questão 1 — configuração padrão do motor.

    A rotina do autor é trapezoidal pura; o motor, por omissão, aplica
    dois meios-passos de Euler regressivo no fechamento
    [FONTE: Lin & Martí 1990, §2]. O desvio contra a analítica passa de
    2,055·10⁻³ A para 4,14·10⁻³ A [CÁLCULO PRÓPRIO] — mesma ordem de
    grandeza, ainda 0,022 % do pico —, e o pico de corrente continua em
    18,69 A. O CDA amortece deliberadamente o passo da manobra; o preço
    é este, e é declarado.
    """
    t, i, _ = q1_simula(Q1_DT, Q1_TMAX, cda_enabled=True)
    i_a = q1_analitico(t)
    di = float(np.max(np.abs(i - i_a)))
    assert di < 5.0e-3
    assert 100.0 * di / float(np.max(np.abs(i_a))) < 0.03
    assert float(np.max(np.abs(i))) == pytest.approx(18.69, abs=5.0e-3)


# ===========================================================================
# LISTA 02 — Questão 2: abertura de disjuntor a vácuo alimentando reator
# ===========================================================================
#
#   1 ──[R1]── 2 ──[L1]── 3 ──/ ── 4 ──┬──[C]── gnd
#                        disjuntor      └──[R2]── 5 ──[L2]── gnd
#
#   vs = 100·cos(377 t) V, R1 = 0,5 Ω, L1 = 5 mH,
#   R2 = 5 Ω, L2 = 50 mH, C = 50 nF, t0 = 30 ms, Imar = 0,5 A
#   [LISTA: 02, §3.1 e Apêndice A]
#
# É o Documento A em miniatura: corte de corrente indutiva por disjuntor
# a vácuo, com a sobretensão vindo da energia magnética do reator
# transferida à capacitância parasita pela impedância de surto
# Z0 = sqrt(L2/C) = 1000 Ω.

Q2_R1, Q2_L1 = 0.5, 5.0e-3
Q2_R2, Q2_L2, Q2_C = 5.0, 50.0e-3, 50.0e-9
Q2_T0 = 30.0e-3
Q2_IMAR = 0.5
Q2_DT = 1.0e-6
Q2_TMAX = 0.10

Q2_Z_SERIE = Q2_R2 + 1j * L02_W * Q2_L2
Q2_Z_C = 1.0 / (1j * L02_W * Q2_C)
Q2_Z_REATOR = Q2_Z_SERIE * Q2_Z_C / (Q2_Z_SERIE + Q2_Z_C)
Q2_Z_TOTAL = Q2_R1 + 1j * L02_W * Q2_L1 + Q2_Z_REATOR
Q2_I_FONTE = L02_VM / Q2_Z_TOTAL
Q2_V_REATOR = Q2_I_FONTE * Q2_Z_REATOR
Q2_I_REATOR = Q2_V_REATOR / Q2_Z_SERIE
Q2_I_CAP = Q2_V_REATOR / Q2_Z_C

Q2_ALPHA = Q2_R2 / (2.0 * Q2_L2)                      # 50 Np/s
Q2_W0 = 1.0 / math.sqrt(Q2_L2 * Q2_C)                 # 20 000 rad/s
Q2_WD = math.sqrt(Q2_W0 ** 2 - Q2_ALPHA ** 2)         # 19 999,9375 rad/s
Q2_Z0 = math.sqrt(Q2_L2 / Q2_C)                       # 1000 Ω


def _q2_instante_de_corte_exato() -> float:
    """Primeiro ``t >= t0`` com ``|i_s(t)| = Imar``, em forma fechada.

    Mesmo procedimento de ``instante_de_corte`` [LISTA: 02, Apêndice A],
    independente do passo de simulação.
    """
    amp = abs(Q2_I_FONTE)
    fase = float(np.angle(Q2_I_FONTE))
    theta0 = L02_W * Q2_T0 + fase
    r = Q2_IMAR / amp
    base = (math.acos(r), math.acos(-r),
            2.0 * math.pi - math.acos(-r), 2.0 * math.pi - math.acos(r))
    k = math.floor(theta0 / (2.0 * math.pi))
    todas = sorted([x + 2.0 * math.pi * k for x in base]
                   + [x + 2.0 * math.pi * (k + 1) for x in base])
    theta = next(x for x in todas if x > theta0)
    return (theta - fase) / L02_W


Q2_TC = _q2_instante_de_corte_exato()
Q2_V0 = float(np.real(Q2_V_REATOR * np.exp(1j * L02_W * Q2_TC)))
Q2_I0 = float(np.real(Q2_I_REATOR * np.exp(1j * L02_W * Q2_TC)))
Q2_A0 = math.hypot(Q2_V0, Q2_ALPHA * Q2_V0 / Q2_WD - Q2_I0 / (Q2_WD * Q2_C))

#: Passos da Tabela 4 [LISTA: 02, §3.7].
Q2_PASSOS = (4.0e-6, 2.0e-6, 1.0e-6, 5.0e-7, 2.5e-7)


def q2_analitico(t):
    """Regime permanente e TRV [LISTA: 02, eqs. (26)-(27)]."""
    t = np.asarray(t, dtype=float)
    v = np.array(np.real(Q2_V_REATOR * np.exp(1j * L02_W * t)), dtype=float)
    i = np.array(np.real(Q2_I_REATOR * np.exp(1j * L02_W * t)), dtype=float)
    m = t >= Q2_TC
    d = t[m] - Q2_TC
    env = np.exp(-Q2_ALPHA * d)
    cw, sw = np.cos(Q2_WD * d), np.sin(Q2_WD * d)
    v[m] = (Q2_V0 * cw
            + (Q2_ALPHA * Q2_V0 / Q2_WD - Q2_I0 / (Q2_WD * Q2_C)) * sw) * env
    i[m] = (Q2_I0 * cw
            + (Q2_V0 / (Q2_L2 * Q2_WD) - Q2_ALPHA * Q2_I0 / Q2_WD) * sw) * env
    return v, i


def q2_circuito(*, resistor_amortecimento_ohm: float | None = None) -> Circuit:
    ckt = Circuit("lista02_q2")
    ckt.add(VoltageSource("E", "1", "gnd", amplitude_V=L02_VM,
                          frequency_Hz=L02_F, phase_reference="cos"))
    ckt.add(Resistor("R1", "1", "2", Q2_R1))
    ckt.add(Inductor("L1", "2", "3", Q2_L1))
    ckt.add(Switch("SW", "3", "4", closed=True, current_margin_A=Q2_IMAR))
    ckt.add(Capacitor("C", "4", "gnd", Q2_C))
    ckt.add(Resistor("R2", "4", "5", Q2_R2))
    ckt.add(Inductor("L2", "5", "gnd", Q2_L2))
    if resistor_amortecimento_ohm is not None:
        # Paliativo da Seção 6 das notas de aula: Rp em PARALELO com L1
        # [LISTA: 02, §3.8, eqs. (30)-(31)].
        ckt.add(Resistor("Rp", "2", "3", resistor_amortecimento_ohm))
    return ckt


def q2_simula(dt: float, tmax: float, *, cda_enabled: bool = False,
              resistor_amortecimento_ohm: float | None = None):
    """Marcha da Questão 2 partindo do regime permanente, disjuntor fechado.

    ``cda_enabled=False`` por omissão para reproduzir a rotina do autor
    (trapezoidal pura). ``open_time_s = t0 − Δt/2`` põe o limiar do
    comando de abertura no meio do intervalo, de modo que a primeira
    avaliação com ``t >= t0`` seja a do passo que chega em ``t0`` — a
    convenção de ``simula_q2``.
    """
    ckt = q2_circuito(resistor_amortecimento_ohm=resistor_amortecimento_ohm)
    ctrl = TimedSwitchController(ckt.get("SW"), open_time_s=Q2_T0 - 0.5 * dt)
    solver = Solver(ckt, dt=dt, init="steady_state", cda_enabled=cda_enabled)
    p_v = solver.add_probe(NodeVoltageProbe("v", "4"))
    p_v3 = solver.add_probe(NodeVoltageProbe("v3", "3"))
    p_i = solver.add_probe(BranchCurrentProbe("i", ckt.get("L2")))
    p_is = solver.add_probe(BranchCurrentProbe("is", ckt.get("SW")))
    solver.run(t_end=tmax, controllers=[ctrl])
    return {
        "t": p_v.time_s, "v": p_v.values, "v3": p_v3.values,
        "i": p_i.values, "is": p_is.values,
        "ctrl": ctrl, "solver": solver, "dt": dt,
    }


@pytest.fixture(scope="module")
def q2_base():
    """Caso de referência: Δt = 1 µs, t_max = 100 ms, trapezoidal pura."""
    return q2_simula(Q2_DT, Q2_TMAX, cda_enabled=False)


@pytest.fixture(scope="module")
def q2_com_cda():
    """Mesmo caso com o CDA ligado — configuração padrão do motor."""
    return q2_simula(Q2_DT, Q2_TMAX, cda_enabled=True)


def test_q2_regime_permanente_fasorial():
    """[LISTA: 02, §3.3, eqs. (19)-(23)] e os parâmetros da ressonância.

    ``Z_reat = 19,508791 ∠75,1389° Ω``, ``Z_tot = 21,458977 ∠75,1394° Ω``,
    ``i_s = 4,660054 ∠−75,1394° A``, ``v = 90,912028 ∠−0,0005° V``,
    ``i = 4,661711 ∠−75,1448° A``; a capacitância conduz apenas 1,71 mA
    em 60 Hz "mas é ela que define todo o transitório posterior".
    """
    assert abs(Q2_Z_REATOR) == pytest.approx(19.508791, abs=5.0e-7)
    assert math.degrees(np.angle(Q2_Z_REATOR)) == pytest.approx(75.1389, abs=5.0e-5)
    assert abs(Q2_Z_TOTAL) == pytest.approx(21.458977, abs=5.0e-7)
    assert math.degrees(np.angle(Q2_Z_TOTAL)) == pytest.approx(75.1394, abs=5.0e-5)
    assert abs(Q2_I_FONTE) == pytest.approx(4.660054, abs=5.0e-7)
    assert abs(Q2_V_REATOR) == pytest.approx(90.912028, abs=5.0e-7)
    assert abs(Q2_I_REATOR) == pytest.approx(4.661711, abs=5.0e-7)
    assert abs(Q2_I_CAP) * 1e3 == pytest.approx(1.71, abs=5.0e-3)

    assert Q2_ALPHA == pytest.approx(50.0, rel=1e-12)
    assert Q2_W0 == pytest.approx(20000.0, rel=1e-12)
    assert Q2_WD == pytest.approx(19999.9375, abs=5.0e-5)
    assert Q2_WD / (2.0 * math.pi) == pytest.approx(3183.09, abs=5.0e-3)
    assert 2.0 * math.pi / Q2_WD * 1e6 == pytest.approx(314.16, abs=5.0e-3)
    assert 1.0 / Q2_ALPHA == pytest.approx(20.0e-3, rel=1e-12)
    assert Q2_Z0 == pytest.approx(1000.0, rel=1e-12)


def test_q2_instante_de_corte_e_condicoes_no_corte():
    """[LISTA: 02, §3.4, eq. (24)].

    ``i_s(t₀) = −3,9137 A`` (acima da margem, a interrupção não ocorre
    de imediato), ``t_c = 32,359422 ms``, ``v₀ = 84,862016 V`` e
    ``i₀ = −0,500615 A``. O termo dominante da TRV é
    ``i₀/(ω_d C) = 500,6 V`` — a sobretensão vem da energia MAGNÉTICA do
    reator, não da carga do capacitor — e a envoltória inicial vale
    ``A₀ = 507,967 V``.
    """
    is_t0 = float(np.real(Q2_I_FONTE * np.exp(1j * L02_W * Q2_T0)))
    assert is_t0 == pytest.approx(-3.9137, abs=5.0e-5)
    assert abs(is_t0) > Q2_IMAR
    assert Q2_TC * 1e3 == pytest.approx(32.359422, abs=5.0e-7)
    assert Q2_V0 == pytest.approx(84.862016, abs=5.0e-7)
    assert Q2_I0 == pytest.approx(-0.500615, abs=5.0e-7)
    assert abs(Q2_I0) / (Q2_WD * Q2_C) == pytest.approx(500.6, abs=5.0e-2)
    assert Q2_A0 == pytest.approx(507.967, abs=5.0e-4)
    # i0 é a corrente do INDUTOR L2, não a da chave: as duas diferem pela
    # corrente capacitiva, 0,615 mA [LISTA: 02, §3.4].
    is_tc = float(np.real(Q2_I_FONTE * np.exp(1j * L02_W * Q2_TC)))
    assert abs(Q2_I0 - is_tc) * 1e3 == pytest.approx(0.615, abs=5.0e-3)


def test_q2_a_partida_em_regime_permanente_e_exata(q2_base):
    """(a) Tabela 3, linha 1: ``1,39·10⁻¹⁰ V`` contra a solução fasorial.

    "A partida em regime permanente é exata: antes de t₀, a solução
    numérica reproduz o resultado fasorial com desvio máximo de
    1,4 × 10⁻¹⁰ V. Não há transitório espúrio de energização"
    [LISTA: 02, §3.7]. Tolerância: meia unidade no último algarismo
    publicado do valor da Tabela 3 (1,39·10⁻¹⁰ ⇒ ±0,005·10⁻¹⁰).
    """
    t, v = q2_base["t"], q2_base["v"]
    m = t < Q2_T0
    fasorial = np.real(Q2_V_REATOR * np.exp(1j * L02_W * t[m]))
    desvio = float(np.max(np.abs(v[m] - fasorial)))
    assert desvio == pytest.approx(1.39e-10, abs=5.0e-13)


def test_q2_pico_da_trv_e_o_valor_do_atp(q2_base):
    """(b) CRITÉRIO DE ACEITE PRINCIPAL — pico da TRV = **504,292 V**.

    É o valor que o autor obteve na rotina própria E no ATP
    [LISTA: 02, Tabela 3], com coincidência nas seis casas publicadas.
    Como os dois programas são implementações independentes, é o
    resultado mais forte disponível para aceitar o motor.

    TOLERÂNCIA ADOTADA: ``5·10⁻⁴ V`` — meia unidade na última casa
    decimal publicada (o valor é dado como 504,292 V, isto é com três
    casas). Não há razão para afrouxar: a configuração usada aqui é a
    mesma do autor (regra trapezoidal pura, sem CDA, partida em regime
    permanente, ``Δt = 1 µs``, mesmo critério de margem de corrente), e o
    motor é determinístico. Em termos relativos a tolerância vale
    ``1·10⁻⁶``, mais de duas ordens de grandeza abaixo do desvio de
    ``4,27·10⁻⁴ V`` que o autor mediu entre a própria rotina e o ATP —
    ou seja, o teste é mais exigente do que a concordância que ele
    publicou, e ainda assim passa.

    Valor obtido: 504,29235 V [CÁLCULO PRÓPRIO].
    """
    v = q2_base["v"]
    pico = float(np.max(np.abs(v)))
    assert pico == pytest.approx(504.292, abs=5.0e-4)
    # Relação com o regime, também publicada: 5,55 vezes os 90,91 V.
    assert pico / abs(Q2_V_REATOR) == pytest.approx(5.55, abs=5.0e-3)


def test_q2_pico_analitico_com_corte_exato(q2_base):
    """Pico analítico 506,170 V e a diferença de 0,37 % explicada.

    "A diferença de 1,9 V (0,37 %) entre o pico numérico e o analítico
    não é erro de integração: ela decorre de o corte só poder ocorrer
    sobre um ponto da malha de tempo" [LISTA: 02, §3.7].
    """
    t = q2_base["t"]
    v_a, _ = q2_analitico(t)
    pico_analitico = float(np.max(np.abs(v_a)))
    pico_numerico = float(np.max(np.abs(q2_base["v"])))
    assert pico_analitico == pytest.approx(506.170, abs=5.0e-4)
    assert pico_analitico - pico_numerico == pytest.approx(1.9, abs=5.0e-2)
    assert 100.0 * (pico_analitico - pico_numerico) / pico_analitico == (
        pytest.approx(0.37, abs=5.0e-3)
    )


def test_q2_instante_de_corte_numerico(q2_base):
    """(c) O corte cai sobre a malha: ``t_c^num = 32,361 ms`` (Δt = 1 µs).

    E a DECISÃO de abrir é tomada em 32,360 ms — exatamente o que a
    listagem do ATP imprime: ``*** Open switch "N3" to "N4" after
    3.23600000E-02 sec.`` [LISTA: 02, §3.6].
    """
    ctrl = q2_base["ctrl"]
    assert ctrl.effective_open_time_s is not None
    assert ctrl.effective_open_time_s * 1e3 == pytest.approx(32.360, abs=5.0e-7)
    assert tc_numerico(ctrl, Q2_DT) * 1e3 == pytest.approx(32.361, abs=5.0e-7)
    # O corte é POSTERIOR ao comando e ocorre com |i_sw| <= Imar.
    assert tc_numerico(ctrl, Q2_DT) > Q2_T0
    k = int(np.argmin(np.abs(q2_base["t"] - ctrl.effective_open_time_s)))
    assert abs(float(q2_base["is"][k])) <= Q2_IMAR
    # E a corrente da chave é nula a partir do corte.
    assert float(np.max(np.abs(q2_base["is"][k + 1:]))) < 1e-12


@pytest.fixture(scope="module")
def q2_tabela_4():
    """Instante de corte e pico da TRV para cada passo da Tabela 4."""
    linhas = []
    for dt in Q2_PASSOS:
        r = q2_simula(dt, 0.045, cda_enabled=False)
        linhas.append((dt, tc_numerico(r["ctrl"], dt),
                       float(np.max(np.abs(r["v"])))))
    return linhas


def test_q2_convergencia_do_corte_e_do_pico_tabela_4(q2_tabela_4):
    """(c) Tabela 4 reproduzida linha a linha.

    ============ ============== ================== ==============
    Δt [µs]      t_c^num [ms]   t_c^num − t_c [µs] pico TRV [V]
    ============ ============== ================== ==============
    4,00         32,364000      +4,578             501,37
    2,00         32,362000      +2,578             503,29
    1,00         32,361000      +1,578             504,29
    0,50         32,360000      +0,578             505,62
    0,25         32,359750      +0,328             505,84
    ============ ============== ================== ==============

    Reduzindo o passo, "tanto o atraso quanto o pico convergem para os
    valores analíticos" — 32,359422 ms e 506,170 V.
    """
    ref_tc = (32.364000, 32.362000, 32.361000, 32.360000, 32.359750)
    ref_atraso = (4.578, 2.578, 1.578, 0.578, 0.328)
    ref_pico = (501.37, 503.29, 504.29, 505.62, 505.84)

    for (dt, tc, pico), tc_ref, atr_ref, pk_ref in zip(
        q2_tabela_4, ref_tc, ref_atraso, ref_pico
    ):
        assert tc * 1e3 == pytest.approx(tc_ref, abs=5.0e-7), f"Δt = {dt}"
        assert (tc - Q2_TC) * 1e6 == pytest.approx(atr_ref, abs=5.0e-4), f"Δt = {dt}"
        assert pico == pytest.approx(pk_ref, abs=5.0e-3), f"Δt = {dt}"

    atrasos = [(tc - Q2_TC) for _, tc, _ in q2_tabela_4]
    picos = [pk for _, _, pk in q2_tabela_4]
    # Monotonicidade das duas convergências.
    assert all(atrasos[k + 1] < atrasos[k] for k in range(len(atrasos) - 1))
    assert all(picos[k + 1] > picos[k] for k in range(len(picos) - 1))
    # E o pico converge PARA o analítico, sem ultrapassá-lo. O valor
    # publicado, 506,170 V, é a expressão fechada (26) AMOSTRADA na malha
    # da simulação, ``n·Δt`` com Δt = 1 µs — que é como a rotina do autor
    # a avalia (``analitico_q2(S2.t, par)``). Como t_c = 32,359422 ms não
    # é múltiplo de 1 µs, essa malha não passa pelo máximo: o supremo
    # CONTÍNUO da mesma expressão vale 506,190 V [CÁLCULO PRÓPRIO], e a
    # diferença de 0,02 V é resolução de amostragem, não do método.
    k0 = int(math.floor(Q2_TC / Q2_DT))
    t_malha = (k0 + np.arange(0, 1001)) * Q2_DT
    pico_analitico = float(np.max(np.abs(q2_analitico(t_malha)[0])))
    assert pico_analitico == pytest.approx(506.170, abs=5.0e-4)
    t_fino = np.linspace(Q2_TC, Q2_TC + 1.0e-3, 200001)
    assert float(np.max(np.abs(q2_analitico(t_fino)[0]))) == pytest.approx(
        506.190, abs=5.0e-3
    )
    assert picos[-1] < pico_analitico
    assert pico_analitico - picos[-1] < 0.35


def test_q2_oscilacao_numerica_sem_cda(q2_base):
    """(d) §3.8 — oscilação de período 2Δt no nó da fonte, SEM CDA.

    Aberta a chave, a LKC no nó 3 impõe ``G_L1(v₂ − v₃) + I_L1 = 0`` e a
    atualização trapezoidal degenera em ``I_L1(t) = −I_L1(t − Δt)``
    [eq. (28)]: o termo histórico troca de sinal a cada passo e ``v₃``
    oscila com amplitude ``R_L1·|I_L1(t_c)| = (2L₁/Δt)·|i_cortada|
    ≈ 4990 V`` [eq. (29)].

    O autor registra que a rotina própria e o ATP percorrem a MESMA
    sequência, dígito a dígito: −4887,8; +5074,5; −4887,8; +5074,6 V.
    Tolerância: meia unidade na primeira casa decimal publicada.
    """
    t, v3, dt = q2_base["t"], q2_base["v3"], q2_base["dt"]
    k = int(np.argmin(np.abs(t - tc_numerico(q2_base["ctrl"], dt))))

    sequencia = [round(float(x), 1) for x in v3[k:k + 4]]
    assert sequencia[0] == pytest.approx(-4887.8, abs=5.0e-2)
    assert sequencia[1] == pytest.approx(+5074.5, abs=5.0e-2)
    assert sequencia[2] == pytest.approx(-4887.8, abs=5.0e-2)
    assert sequencia[3] == pytest.approx(+5074.6, abs=5.0e-2)

    # Amplitude prevista pela eq. (29) — "≈ 4990 V".
    i_cortada = abs(float(q2_base["is"][k - 1]))
    assert (2.0 * Q2_L1 / dt) * i_cortada == pytest.approx(4990.0, abs=0.5)

    # Oscilação SUSTENTADA: o sinal alterna e a amplitude não decai.
    trecho = v3[k:k + 200]
    assert np.all(np.sign(trecho[:-1]) * np.sign(trecho[1:]) < 0.0)
    assert float(np.max(np.abs(trecho))) > 4800.0
    # E permanece até o fim da simulação, 68 ms depois.
    assert float(np.max(np.abs(v3[-200:]))) > 4800.0

    # A grandeza pedida no enunciado NÃO é afetada: o reator fica
    # eletricamente isolado da fonte [LISTA: 02, §3.8].
    assert float(np.max(np.abs(q2_base["v"]))) == pytest.approx(504.292, abs=5.0e-4)


def test_q2_cda_suprime_a_oscilacao_numerica(q2_com_cda, q2_base):
    """(d) Com o CDA a oscilação de 2Δt desaparece em um passo.

    Os dois meios-passos de Euler regressivo aplicados após a mudança de
    topologia [FONTE: Lin & Martí 1990, §2, p. 394] anulam o fator −1 da
    recursão (28). É o mesmo efeito que o autor obteve com o resistor de
    amortecimento ``Rp = 2L₁/Δt`` [§3.8], por um caminho que não altera
    o circuito: depois do primeiro passo ``v₃`` passa a acompanhar
    ``v_s(t)``, "que é o valor fisicamente correto, já que sem corrente
    não há queda em R₁ nem em L₁".
    """
    t, v3, dt = q2_com_cda["t"], q2_com_cda["v3"], q2_com_cda["dt"]
    k = int(np.argmin(np.abs(t - tc_numerico(q2_com_cda["ctrl"], dt))))

    # Sem CDA a oscilação chega a 5 kV; com CDA fica limitada à própria
    # tensão da fonte (100 V de amplitude).
    assert float(np.max(np.abs(q2_base["v3"][k:]))) > 4800.0
    assert float(np.max(np.abs(v3[k:]))) <= 100.0 + 1e-6

    # v3 acompanha vs(t) a partir do passo seguinte ao corte.
    vs = L02_VM * np.cos(L02_W * t[k:k + 50])
    assert float(np.max(np.abs(v3[k:k + 50] - vs))) < 1e-6
    # Nenhuma alternância de sinal passo a passo no trecho.
    trecho = v3[k:k + 50]
    assert not np.any(np.sign(trecho[:-1]) * np.sign(trecho[1:]) < 0.0)


def test_q2_resistor_de_amortecimento_do_autor(q2_base):
    """(d) Paliativo das notas de aula: ``Rp = 2L₁/Δt = 10 kΩ``.

    O fator de propagação de ``I_L1`` vale ``(G_p − G_L1)/(G_p + G_L1)``
    [eq. (30)] e se ANULA para ``Rp = 1/G_L1 = 2L₁/Δt`` [eq. (31)]. A
    oscilação é extinta em um único passo, "após o qual v₃ passa a
    acompanhar vs(t)"; resta apenas o degrau do próprio passo de
    interrupção, que é inevitável.

    Divergência registrada. O autor mede como preço do paliativo um
    desvio de 0,249 V em ``v(t)``, 0,049 % do pico da TRV; aqui mede-se
    0,076 V, 0,015 % [CÁLCULO PRÓPRIO] — três vezes MENOR. A hipótese
    é a semeadura: ``simula_q2(..., Rp)`` reaproveita as condições
    iniciais calculadas SEM ``Rp`` (elas vêm de ``parametros_lista02``,
    que não conhece o argumento), ao passo que
    ``Solver(init="steady_state")`` resolve o fasor do circuito
    EFETIVAMENTE montado, ``Rp`` incluído — o que remove um pequeno
    transitório de partida [HIPÓTESE]. O teste verifica o limite
    publicado (0,05 % do pico), que o valor obtido satisfaz com folga, e
    não o número em si.
    """
    dt = Q2_DT
    rp = 2.0 * Q2_L1 / dt
    assert rp == pytest.approx(10.0e3, rel=1e-12)

    # Fator de propagação da eq. (30): −1 sem Rp, 0 com Rp = 2L1/Δt.
    g_l1 = dt / (2.0 * Q2_L1)
    assert (0.0 - g_l1) / (0.0 + g_l1) == pytest.approx(-1.0, rel=1e-12)
    assert ((1.0 / rp) - g_l1) / ((1.0 / rp) + g_l1) == pytest.approx(0.0, abs=1e-15)

    r = q2_simula(dt, 0.034, cda_enabled=False, resistor_amortecimento_ohm=rp)
    t, v3 = r["t"], r["v3"]
    k = int(np.argmin(np.abs(t - tc_numerico(r["ctrl"], dt))))

    # Um único passo de degrau e, em seguida, vs(t).
    assert abs(float(v3[k])) > 1000.0
    vs = L02_VM * np.cos(L02_W * t[k + 1:k + 50])
    assert float(np.max(np.abs(v3[k + 1:k + 50] - vs))) < 1e-6
    assert float(np.max(np.abs(v3[k + 1:]))) <= 100.0 + 1e-6

    # Preço pago em v(t), contra a marcha sem Rp — limite publicado.
    n = min(len(r["v"]), len(q2_base["v"]))
    desvio = float(np.max(np.abs(r["v"][:n] - q2_base["v"][:n])))
    pico = float(np.max(np.abs(q2_base["v"])))
    assert desvio < 0.30
    assert 100.0 * desvio / pico < 0.05


def test_q2_pico_da_trv_com_cda(q2_com_cda):
    """Pico da TRV na configuração PADRÃO do motor (CDA ligado).

    Aqui a configuração DIFERE da do autor, e a tolerância é afrouxada
    com justificativa (regra 4 da política do módulo). O CDA substitui o
    passo da manobra por dois meios-passos de Euler regressivo, isto é,
    discretiza de outra forma exatamente o passo da descontinuidade; o
    pico obtido, 505,148 V [CÁLCULO PRÓPRIO], fica ENTRE o da
    trapezoidal pura (504,292 V) e o analítico com corte exato
    (506,170 V). Ou seja, o CDA não degrada a estimativa de sobretensão:
    aproxima-a. Tolerância adotada: 1,0 V (0,2 %) em torno do valor
    medido, e a exigência estrutural de que o pico permaneça no
    intervalo aberto entre os dois valores publicados.
    """
    pico = float(np.max(np.abs(q2_com_cda["v"])))
    assert pico == pytest.approx(505.148, abs=1.0)
    assert 504.292 < pico < 506.170
    # A partida em regime permanente continua exata com o CDA das
    # manobras ligado — são coisas distintas [LISTA: 02, §1.4].
    t, v = q2_com_cda["t"], q2_com_cda["v"]
    m = t < Q2_T0
    fasorial = np.real(Q2_V_REATOR * np.exp(1j * L02_W * t[m]))
    assert float(np.max(np.abs(v[m] - fasorial))) == pytest.approx(1.39e-10,
                                                                   abs=5.0e-13)
    # E o instante de corte é o mesmo: o critério é de CORRENTE, não de
    # relógio [LISTA: 02, §3.7].
    assert tc_numerico(q2_com_cda["ctrl"], Q2_DT) * 1e3 == pytest.approx(
        32.361, abs=5.0e-7
    )


def test_q2_envoltoria_e_amortecimento_da_trv(q2_base):
    """A TRV decai dentro da envoltória ``±A₀·e^{−α(t−t_c)}``.

    ``A₀ = 507,967 V`` e ``τ = 1/α = 20 ms`` [LISTA: 02, §3.4 e Figura 7];
    ``t_max = 100 ms`` cobre 3,4 constantes de tempo.
    """
    t, v = q2_base["t"], q2_base["v"]
    tc = tc_numerico(q2_base["ctrl"], Q2_DT)
    m = t >= tc
    envoltoria = Q2_A0 * np.exp(-Q2_ALPHA * (t[m] - tc))
    # Tolerância de 1 V para o degrau do próprio passo de interrupção.
    assert np.all(np.abs(v[m]) <= envoltoria + 1.0)
    # E o amortecimento é o físico: em 3,4τ o sinal caiu por e^{−3,4}.
    final = float(np.max(np.abs(v[t > Q2_TMAX - 2.0 * 314.16e-6])))
    esperado = Q2_A0 * math.exp(-Q2_ALPHA * (Q2_TMAX - tc))
    assert final == pytest.approx(esperado, rel=0.05)


def test_q2_corrente_do_reator_apos_o_corte(q2_base):
    """A corrente do ramo R₂–L₂ passa a oscilar na frequência natural.

    Comparação contra a eq. (27) na janela dos primeiros ciclos da TRV,
    onde o atraso de 1,578 µs do corte ainda não acumulou defasagem
    perceptível [LISTA: 02, Figura 9].
    """
    t, i = q2_base["t"], q2_base["i"]
    tc = tc_numerico(q2_base["ctrl"], Q2_DT)
    janela = (t >= tc) & (t <= tc + 2.0 * 314.16e-6)
    _, i_a = q2_analitico(t[janela])
    # Amplitude: o pico da corrente é v0/(L2·ωd) ≈ 0,085 A somado a i0.
    assert float(np.max(np.abs(i[janela]))) == pytest.approx(
        float(np.max(np.abs(i_a))), rel=0.05
    )
    # Frequência: conta-se o número de cruzamentos por zero em 2 períodos.
    trecho = i[janela]
    cruzamentos = int(np.sum(np.sign(trecho[:-1]) * np.sign(trecho[1:]) < 0.0))
    assert cruzamentos in (4, 5)


def test_q2_sem_margem_de_corrente_a_sobretensao_desaparece():
    """"Sem o campo Imar o ATP esperaria um zero natural de corrente e a
    sobretensão praticamente desapareceria" [LISTA: 02, §3.6].

    Verificação do papel do campo. Com ``Imar = 0,5 A`` o disjuntor
    corta 0,5 A de corrente indutiva e a TRV chega a 504,29 V. Baixando
    a margem para 2 mA — que é o que o passo de 1 µs consegue resolver em
    torno do zero natural, já que a corrente de 4,66 A a 60 Hz varia
    1,76 mA por passo — a interrupção passa a ocorrer praticamente NO
    zero de corrente, a energia magnética armazenada em ``L₂`` é
    desprezível e não há sobretensão alguma: a tensão do reator segue no
    patamar de regime, 90,91 V.

    É esse o contraste que justifica o campo ``Imar`` como o modelo do
    corte de corrente do disjuntor a vácuo — e é o mecanismo do
    Documento A, onde a corrente de *chopping* de 1 a 2 A é o que gera a
    solicitação sobre o isolamento do motor.
    """
    margem = 2.0e-3
    ckt = q2_circuito()
    ckt.get("SW").current_margin_A = margem
    ctrl = TimedSwitchController(ckt.get("SW"),
                                 open_time_s=Q2_T0 - 0.5 * Q2_DT,
                                 current_margin_A=margem)
    solver = Solver(ckt, dt=Q2_DT, init="steady_state", cda_enabled=False)
    p_v = solver.add_probe(NodeVoltageProbe("v", "4"))
    p_is = solver.add_probe(BranchCurrentProbe("is", ckt.get("SW")))
    solver.run(t_end=0.045, controllers=[ctrl])

    # A interrupção ocorre, e no zero natural de corrente.
    assert ctrl.effective_open_time_s is not None
    k = int(np.argmin(np.abs(p_v.time_s - ctrl.effective_open_time_s)))
    i_cortada = abs(float(p_is.values[k]))
    assert i_cortada <= margem

    pico_sem_chopping = float(np.max(np.abs(p_v.values)))
    assert pico_sem_chopping == pytest.approx(abs(Q2_V_REATOR), abs=5.0e-3)
    assert pico_sem_chopping < 0.20 * 504.292
