"""
tests/test_emt_caso_referencia_atp.py — ancoragem do caso do arquivo ATP no
motor de transitórios dedicado, confrontada com a solução fasorial impressa
na listagem de saída do próprio ATP.

O que estes testes verificam
============================

1. **Leitura da referência** — o JSON extraído da listagem
   (``tests/fixtures/atp/referencia_regime_permanente.json``) é a fonte
   única da verdade e é lido com a convenção declarada (pico, cosseno).
2. **Dedução do equivalente** — a rede a montante entra por equivalente de
   Thévenin deduzido daquela solução, SEM decodificar a matriz 6×6 do
   transformador. A dedução é conferida por quatro fatos independentes:
   recupera o resistor de neutro de 12,009 Ω do cartão, a relação de
   espiras 4160/13800, a defasagem de 30° do Δ–Y e a identidade
   ``Z₀ − 3R_n ≈ Z₁``.
3. **Decodificação do cartão do cabo a jusante** — a [HIPÓTESE] de leitura
   dos campos sob comprimento negativo é testada contra a queda de tensão
   publicada.
4. **Reprodução de CADA grandeza publicada** — treze tensões nodais e seis
   correntes de ramo, dentro das tolerâncias declaradas abaixo.
5. **Ausência de transitório espúrio de partida** ao longo de vários
   ciclos com o disjuntor fechado.
6. **Conservação de potência** contra a perda total de 997 130,9 W.

Tolerâncias declaradas e sua justificativa
==========================================

O modelo do domínio do TEMPO usa a PARTE REAL da matriz de transformação
modal punçada no arquivo, porque o modelo de Bergeron não admite
transformação complexa. A solução fasorial do próprio ATP usa a matriz
COMPLEXA. A diferença é exclusivamente de sequência zero e vale ≈ 10 V,
que, como a corrente de carga é imposta pela impedância do motor, aparece
integralmente nos nós a montante do cabo.

Que o resíduo é ESSE e não outro fica demonstrado por
:func:`test_leitura_complexa_colapsa_o_residuo`: repetindo a estampagem
fasorial com a matriz complexa — a mesma que o ATP usa — o desvio de
todas as dezenove grandezas cai para 6,7 mV e 1,2 mA. E ele é
irredutível: ``Re[Z_ph]`` da leitura complexa tem autovalor −0,513 Ω, de
modo que nenhum modelo PASSIVO reproduz exatamente aquela solução
(:func:`test_matriz_de_fase_complexa_e_nao_passiva`).

Daí as tolerâncias:

================================  ===========  ==========================
Grandeza                          Tolerância   Justificativa
================================  ===========  ==========================
``01AT`` e correntes de ramo      0,10%        medido 0,063%; margem 1,6×
``X0029`` e ``X0002``             0,35%        medido 0,300%; margem 1,2×
``XX0003`` (neutro, 49 V)         12 V         desvio de sequência zero
                                               de 9,97 V — 0,3% da tensão
                                               de fase, mas 20% de uma
                                               grandeza que é só
                                               sequência zero
Perda total da rede               0,20%        medido 0,111%
Leitura complexa (todas)          0,02%        medido 0,0136%
Desvio da marcha em 3 ciclos      0,05 V       medido 2,0 mV em 5 ciclos
================================  ===========  ==========================
"""

from __future__ import annotations

import cmath
import json
import math

import numpy as np
import pytest

from app.simulation.emt.cases.atp_reference import (
    ATP_ZERO_ORDER_LITERAL,
    CABLE_MODAL_RESISTANCE_OHM,
    CABLE_MODAL_SURGE_OHM,
    CABLE_MODAL_VELOCITY,
    CABLE_PHASOR_COMPLEX,
    CABLE_TI_COMPLEX,
    FREQUENCY_HZ,
    KNOWN_LIMITATIONS,
    MAGNETIZING_RESISTANCE_OHM,
    MOTOR_INDUCTANCE_H,
    MOTOR_RESISTANCE_OHM,
    NEUTRAL_RESISTANCE_OHM,
    NODES_CB_LOAD,
    NODES_MOTOR,
    PHASES,
    REFERENCE_JSON_PATH,
    SNUBBER_BREAKOVER_V,
    SOURCE_PEAK_V,
    TOTAL_NETWORK_LOSS_W,
    VCB_CHOPPING_CURRENT_A,
    VCB_DIDT_CAPABILITY_A_PER_US,
    VCB_RRDS_A_KV_PER_MS,
    VCB_RRDS_B_KV_PER_MS2,
    VCB_SEPARATION_TIME_S,
    AtpReferenceCase,
    CoupledBergeronCable,
    build_downstream_cable,
    SnubberArmingGate,
    build_reference_model,
    derive_thevenin,
    downstream_cable_modal_lc,
    load_reference,
    phase_series_impedance,
    phase_shunt_admittance,
)

OMEGA = 2.0 * math.pi * FREQUENCY_HZ

# -- tolerâncias declaradas (ver o cabeçalho) --------------------------------
TOL_CARGA = 1.0e-3          # 0,10% — nós 01AT e correntes de ramo
TOL_MONTANTE = 3.5e-3       # 0,35% — nós X0029 e X0002
TOL_NEUTRO_V = 12.0         # V absolutos no nó de neutro
TOL_POTENCIA = 2.0e-3       # 0,20% — perda total da rede
TOL_LEITURA_COMPLEXA = 2.0e-4
TOL_DERIVA_V = 0.05         # V — transitório espúrio de partida


# ---------------------------------------------------------------------------
# Fixtures — as montagens caras são compartilhadas pelo módulo
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def referencia():
    """Solução fasorial publicada, lida uma única vez."""
    return load_reference()


@pytest.fixture(scope="module")
def equivalente(referencia):
    """Equivalente de Thévenin deduzido com o resistor de neutro do cartão."""
    return derive_thevenin(referencia)


@pytest.fixture(scope="module")
def modelo():
    """Caso montado com a leitura REAL da matriz modal (padrão)."""
    return build_reference_model(with_snubber=True)


@pytest.fixture(scope="module")
def validacao(modelo):
    """Tabela de confronto com a listagem, calculada uma única vez."""
    return modelo.phasor_validation()


@pytest.fixture(scope="module")
def modelo_complexo():
    """Caso montado com a leitura COMPLEXA — a mesma matriz que o ATP usa."""
    return build_reference_model(
        with_snubber=True, cable_phasor_reading=CABLE_PHASOR_COMPLEX
    )


@pytest.fixture(scope="module")
def marcha_em_regime():
    """Três ciclos com o disjuntor MANTIDO FECHADO, para medir a partida."""
    m = build_reference_model(
        with_snubber=True,
        separation_times_s=(10.0, 10.0, 10.0),
        t_end_s=3.0 / FREQUENCY_HZ,
    )
    m.run()
    return m


@pytest.fixture(scope="module")
def manobra():
    """Janela completa de 45 ms com a manobra do arquivo."""
    m = build_reference_model(with_snubber=True)
    m.run()
    return m


# ---------------------------------------------------------------------------
# 1. Leitura do JSON de referência
# ---------------------------------------------------------------------------


def test_json_de_referencia_existe_e_traz_as_grandezas_esperadas():
    """O JSON extraído da listagem é a fonte única da verdade do caso."""
    assert REFERENCE_JSON_PATH.is_file(), REFERENCE_JSON_PATH
    raw = json.loads(REFERENCE_JSON_PATH.read_text(encoding="utf-8"))
    assert raw["frequencia_Hz"] == pytest.approx(60.0)
    assert len(raw["tensoes_nodais"]) == 13
    assert len(raw["correntes_de_ramo"]) == 6
    assert raw["perda_total_da_rede_W"] == pytest.approx(TOTAL_NETWORK_LOSS_W)


def test_leitura_converte_para_fasor_de_pico_com_referencia_cosseno(referencia):
    """``X̂ = |X|·e^{jθ}`` — módulo de pico, ângulo em graus [FATO: listagem]."""
    v = referencia.node("X0029A")
    assert abs(v) == pytest.approx(3386.445342208, rel=1e-12)
    assert math.degrees(cmath.phase(v)) == pytest.approx(30.4988358, abs=1e-6)
    # A fonte do arquivo é rigorosamente equilibrada, com B ADIANTADA.
    src = referencia.source_phasors()
    assert abs(src[0]) == pytest.approx(SOURCE_PEAK_V)
    assert math.degrees(cmath.phase(src[1])) == pytest.approx(120.0)
    assert math.degrees(cmath.phase(src[2])) == pytest.approx(-120.0)


def test_leitura_recusa_caminho_inexistente(tmp_path):
    """Sem a referência não há caso: o erro é explícito, não silencioso."""
    with pytest.raises(FileNotFoundError, match="fonte única da verdade"):
        load_reference(tmp_path / "nao_existe.json")


def test_leitura_recusa_json_sem_as_chaves_obrigatorias(tmp_path):
    """Estrutura incompatível é erro de dado, não de programa."""
    p = tmp_path / "ruim.json"
    p.write_text(json.dumps({"frequencia_Hz": 60.0}), encoding="utf-8")
    with pytest.raises(ValueError, match="chave obrigatória"):
        load_reference(p)


def test_convencao_de_sinal_da_corrente_do_motor(referencia):
    """A corrente publicada de ``01ATx->TERRA`` é o SIMÉTRICO da que entra.

    Verificação exata: ``V̂/Ẑ_mot`` reproduz o módulo publicado e o ângulo
    difere de 180,0000° nas três fases [CÁLCULO PRÓPRIO].
    """
    z = MOTOR_RESISTANCE_OHM + 1j * OMEGA * MOTOR_INDUCTANCE_H
    for node, i_pub in zip(NODES_MOTOR, referencia.motor_currents()):
        i_calc = referencia.node(node) / z
        assert abs(i_calc) == pytest.approx(abs(i_pub), rel=1e-9)
        assert abs(i_calc - i_pub) / abs(i_pub) < 1.0e-6


def test_convencao_de_sinal_da_corrente_do_disjuntor(referencia):
    """A corrente publicada do disjuntor é a de JUSANTE — provado por potência.

    Com esse sinal a potência que entra no cabo supera a que chega ao
    motor, e a diferença é a perda série do cabo; com o sinal oposto a
    rede passiva geraria potência [CÁLCULO PRÓPRIO].
    """
    v02 = referencia.node_abc("X0002")
    v01 = referencia.node_abc("01AT")
    i_br = referencia.breaker_currents()
    i_mot = referencia.motor_currents()
    p_in = 0.5 * float(np.real(np.sum(v02 * np.conj(i_br))))
    p_out = 0.5 * float(np.real(np.sum(v01 * np.conj(i_mot))))
    assert p_in > p_out > 0.0
    perda_cabo = 0.5 * float(
        np.real(np.conj(0.5 * (i_br + i_mot)) @ phase_series_impedance(OMEGA) @ (0.5 * (i_br + i_mot)))
    )
    assert (p_in - p_out) == pytest.approx(perda_cabo, rel=2.0e-4)


# ---------------------------------------------------------------------------
# 2. Dedução do equivalente de Thévenin
# ---------------------------------------------------------------------------


def test_deducao_recupera_o_resistor_de_neutro_do_cartao(referencia):
    """Sem informar 12,009 Ω, o termo mútuo do equivalente O RECUPERA.

    Conferência independente mais forte do método: resolvendo o sistema
    exatamente determinado em ``(Ê, Z₁, Z_m)``, o mútuo sai
    12,009204 + j0,010599 Ω contra os 12,009 Ω punçados no cartão
    [FATO: arquivo] — desvio de 1,7·10⁻⁵.
    """
    eq = derive_thevenin(referencia, use_card_neutral=False)
    assert eq.z_mutual_ohm is not None
    assert float(np.real(eq.z_mutual_ohm)) == pytest.approx(
        NEUTRAL_RESISTANCE_OHM, rel=5.0e-5
    )
    assert abs(float(np.imag(eq.z_mutual_ohm))) < 0.02


def test_residuo_dos_minimos_quadrados_confirma_rede_equilibrada(equivalente):
    """Três equações, duas incógnitas: o resíduo testa a hipótese do passo 1.

    Resíduo medido: 2,9·10⁻⁴ V contra tensões de 3,4 kV — 1·10⁻⁷ relativo.
    """
    assert max(equivalente.residual_V) < 1.0e-3
    assert max(equivalente.residual_V) / 3386.0 < 1.0e-6


def test_relacao_de_espiras_e_defasagem_do_equivalente(equivalente):
    """``|Ê|/|V̂_fonte| = 4160/13800`` e ``∠Ê = 30°`` — Δ–Y [INFERÊNCIA FÍSICA]."""
    assert equivalente.turns_ratio == pytest.approx(4160.0 / 13800.0, rel=2.0e-4)
    assert equivalente.emf_angle_deg == pytest.approx(30.0, abs=0.01)
    assert equivalente.emf_peak_V == pytest.approx(3532.1077, rel=1e-6)


def test_impedancia_de_sequencia_zero_do_equivalente(equivalente):
    """``Z₀ − 3R_n ≈ Z₁``: o transformador Δ–Yaterrado tem ``Z₀ = Z₁``."""
    z0 = equivalente.zero_sequence_ohm
    z0_trafo = z0 - 3.0 * NEUTRAL_RESISTANCE_OHM
    assert abs(z0_trafo - equivalente.z_series_ohm) < 0.01
    assert float(np.real(z0)) == pytest.approx(3.0 * NEUTRAL_RESISTANCE_OHM, rel=1e-3)


def test_equivalente_por_fase_nao_e_de_sequencia(equivalente):
    """As três fases NÃO são iguais — a ligação a montante é assimétrica.

    ``Z_link`` vale 0,0049+j0,0585, 0,0282+j0,0427 e 0,0486+j0,0402 Ω: a
    parte resistiva da fase C é dez vezes a da fase A. Nenhuma simetria é
    imposta.
    """
    r = [float(np.real(z)) for z in equivalente.z_link_ohm]
    x = [float(np.imag(z)) for z in equivalente.z_link_ohm]
    assert max(r) / min(r) > 5.0
    assert max(x) / min(x) > 1.3


def test_ligacao_extraida_e_fisicamente_realizavel(equivalente):
    """``R > 0`` e ``L > 0`` nas três fases — o ramo é passivo e montável."""
    for (r, l) in equivalente.link_rl():
        assert r > 0.0
        assert l > 0.0
    r1, l1 = equivalente.series_rl()
    assert r1 > 0.0 and l1 > 0.0
    assert l1 == pytest.approx(0.338714e-3, rel=1e-4)


def test_tensao_do_neutro_deduzida_bate_com_a_publicada(referencia):
    """``V̂_N = −R_n·ΣÎ`` reproduz os 49,026 V publicados em ``XX0003``.

    Grandeza NÃO usada no ajuste — conferência independente.
    """
    v_n = -NEUTRAL_RESISTANCE_OHM * complex(np.sum(referencia.breaker_currents()))
    assert abs(v_n) == pytest.approx(abs(referencia.node("XX0003")), rel=1e-4)


def test_corrente_de_magnetizacao_e_pequena_mas_nao_desprezivel(referencia):
    """≈ 3,0 A de pico contra 911 A de carga — 0,33%, e entra no ajuste."""
    v29 = referencia.node_abc("X0029")
    i_mag = (v29 - referencia.node("XX0003")) / MAGNETIZING_RESISTANCE_OHM
    assert 2.9 < float(np.min(np.abs(i_mag))) < 3.1
    assert float(np.max(np.abs(i_mag))) / 911.0 < 0.005


# ---------------------------------------------------------------------------
# 3. Decodificação do cartão do cabo a jusante
# ---------------------------------------------------------------------------


def test_hipotese_do_comprimento_negativo_reproduz_a_queda_publicada(referencia):
    """A [HIPÓTESE] de leitura do cartão é CONFIRMADA pela própria listagem.

    Com ``A = Z_c``, ``B = velocidade`` e ``|ℓ| = 1``, a matriz de fase
    ``Z_ph = (T_i^T)^{-1}·diag(R + jωL)·T_i^{-1}`` reproduz
    ``V̂02 − V̂01AT`` com erro de 1·10⁻⁶ nas três fases. É por isso que a
    substituição do cabo por impedância concentrada NÃO foi necessária.
    """
    dv = referencia.node_abc("X0002") - referencia.node_abc("01AT")
    i_med = 0.5 * (referencia.breaker_currents() + referencia.motor_currents())
    pred = phase_series_impedance(OMEGA) @ i_med
    for k in range(3):
        assert abs(pred[k] - dv[k]) / abs(dv[k]) < 1.0e-5


def test_admitancia_transversal_do_cartao_reproduz_a_corrente_de_carregamento(referencia):
    """A diferença entre corrente de entrada e de saída é a do ``jωC`` do cartão.

    São 0,16 a 0,28 A contra 911 A de carga; reproduzidas dentro de 8%,
    que é a resolução com que a listagem publica correntes dessa ordem.
    """
    i_sh = referencia.breaker_currents() - referencia.motor_currents()
    v_med = 0.5 * (referencia.node_abc("X0002") + referencia.node_abc("01AT"))
    pred = phase_shunt_admittance(OMEGA) @ v_med
    for k in range(3):
        assert abs(abs(pred[k]) - abs(i_sh[k])) / abs(i_sh[k]) < 0.08


def test_parametros_modais_do_cartao_sao_de_cabo_de_media_tensao():
    """``L' = Z_c/v`` e ``C' = 1/(Z_c·v)`` dão valores de cabo POR QUILÔMETRO.

    0,503 / 0,672 / 6,194 mH e 0,2278 / 0,0679 / 0,0064 µF — donde a
    unidade de comprimento do cartão é o quilômetro [INFERÊNCIA FÍSICA].
    """
    l, c = downstream_cable_modal_lc()
    assert l[0] * 1e3 == pytest.approx(0.503025, rel=1e-4)
    assert c[0] * 1e6 == pytest.approx(0.227765, rel=1e-4)
    assert np.all(l > 0.0) and np.all(c > 0.0)
    zc = np.sqrt(l / c)
    assert np.allclose(zc, np.array(CABLE_MODAL_SURGE_OHM), rtol=1e-9)
    tau = np.sqrt(l * c)
    assert np.allclose(tau, 1.0 / np.array(CABLE_MODAL_VELOCITY), rtol=1e-9)


def test_matriz_de_fase_complexa_e_nao_passiva():
    """``Re[Z_ph]`` da leitura complexa tem autovalor −0,513 Ω.

    É o fato que torna IMPOSSÍVEL reproduzir exatamente a solução fasorial
    do ATP com um modelo passivo, e a justificativa da tolerância adotada.
    """
    zph = phase_series_impedance(OMEGA)
    autovalores = np.linalg.eigvalsh(np.real(zph + zph.T) / 2.0)
    assert float(np.min(autovalores)) < -0.5
    # A leitura REAL, ao contrário, é passiva.
    zr = phase_series_impedance(OMEGA, transformation=np.real(CABLE_TI_COMPLEX))
    assert float(np.min(np.linalg.eigvalsh(np.real(zr + zr.T) / 2.0))) > 0.0


def test_cabo_acoplado_valida_os_dados_de_entrada():
    """Matriz singular, τ ≤ 0 e nós repetidos são recusados na montagem."""
    with pytest.raises(ValueError, match="singular"):
        CoupledBergeronCable(
            "x",
            ("a", "b", "c"),
            ("d", "e", "f"),
            surge_impedance_ohm=CABLE_MODAL_SURGE_OHM,
            travel_time_s=(1e-6, 1e-6, 1e-6),
            resistance_ohm=CABLE_MODAL_RESISTANCE_OHM,
            transformation=np.ones((3, 3)),
        )
    with pytest.raises(ValueError, match="τ modal"):
        build_downstream_cable("x", ("a", "b", "c"), ("d", "e", "f")).__class__(
            "x",
            ("a", "b", "c"),
            ("d", "e", "f"),
            surge_impedance_ohm=CABLE_MODAL_SURGE_OHM,
            travel_time_s=(0.0, 1e-6, 1e-6),
            resistance_ohm=CABLE_MODAL_RESISTANCE_OHM,
            transformation=np.real(CABLE_TI_COMPLEX),
        )
    with pytest.raises(ValueError, match="nós repetidos"):
        build_downstream_cable("x", ("a", "b", "c"), ("a", "e", "f"))


def test_cabo_acoplado_estampa_bloco_simetrico():
    """``Y = T·G·Tᵀ`` é simétrica e acopla as três fases de cada extremidade."""
    cabo = build_downstream_cable("cabo", NODES_CB_LOAD, NODES_MOTOR)
    y = cabo.nodal_admittance_S
    assert np.allclose(y, y.T, atol=1e-12)
    fora_da_diagonal = [y[i, j] for i in range(3) for j in range(3) if i != j]
    assert min(abs(v) for v in fora_da_diagonal) > 1.0e-4
    assert cabo.n_branches() == 6


# ---------------------------------------------------------------------------
# 4. Reprodução de cada grandeza publicada
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("node", ["X0029A", "X0029B", "X0029C"])
def test_reproduz_tensao_nodal_de_X0029(validacao, node):
    """Tensão do barramento de 4,16 kV, dentro da tolerância declarada."""
    row = next(r for r in validacao if r.quantity == node)
    assert row.error < TOL_MONTANTE, row.as_dict()


@pytest.mark.parametrize("node", ["X0002A", "X0002B", "X0002C"])
def test_reproduz_tensao_nodal_de_X0002(validacao, node):
    """Tensão do barramento do painel (lado carga do disjuntor)."""
    row = next(r for r in validacao if r.quantity == node)
    assert row.error < TOL_MONTANTE, row.as_dict()


@pytest.mark.parametrize("node", ["01ATA", "01ATB", "01ATC"])
def test_reproduz_tensao_nodal_do_motor(validacao, node):
    """Tensão nos terminais do motor — o nó que interessa ao isolamento."""
    row = next(r for r in validacao if r.quantity == node)
    assert row.error < TOL_CARGA, row.as_dict()


def test_reproduz_tensao_do_neutro(validacao):
    """``XX0003`` é grandeza de sequência PURA (49 V): tolerância absoluta."""
    row = next(r for r in validacao if r.quantity == "XX0003")
    assert abs(row.obtained - row.reference) < TOL_NEUTRO_V, row.as_dict()


@pytest.mark.parametrize("phase", ["A", "B", "C"])
def test_reproduz_corrente_do_disjuntor(validacao, phase):
    """Corrente de ramo do polo, módulo e ângulo."""
    row = next(r for r in validacao if r.quantity == f"I disjuntor fase {phase}")
    assert row.error < TOL_CARGA, row.as_dict()


@pytest.mark.parametrize("phase", ["A", "B", "C"])
def test_reproduz_corrente_do_motor(validacao, phase):
    """Corrente de ramo do motor, módulo e ângulo."""
    row = next(r for r in validacao if r.quantity == f"I motor fase {phase}")
    assert row.error < TOL_CARGA, row.as_dict()


def test_validacao_cobre_todas_as_grandezas_publicadas(validacao, referencia):
    """A tabela confronta as 13 tensões (menos as internas) e as 6 correntes."""
    tensoes = [r for r in validacao if r.kind == "tensao"]
    correntes = [r for r in validacao if r.kind == "corrente"]
    assert len(tensoes) == 10  # X0029, X0002, 01AT e XX0003
    assert len(correntes) == 6
    # X0028 e as fontes ficam DENTRO do equivalente e não são reproduzíveis.
    assert "X0028A" in referencia.node_voltages


def test_desequilibrio_publicado_e_reproduzido(modelo, referencia):
    """As três fases têm módulos diferentes, e o modelo os segue.

    3386,4 / 3462,5 / 3397,0 V na listagem: a fase B é 2,2% maior que a A.
    Não há simetria imposta em lugar nenhum do modelo.
    """
    sol = modelo.phasor_solution()
    obtido = np.array([abs(sol.node_phasor(f"X0029{s}")) for s in ("A", "B", "C")])
    publicado = np.abs(referencia.node_abc("X0029"))
    assert publicado[1] / publicado[0] == pytest.approx(1.0224, rel=1e-3)
    assert obtido[1] / obtido[0] == pytest.approx(
        publicado[1] / publicado[0], rel=2.0e-3
    )


def test_leitura_complexa_colapsa_o_residuo(modelo_complexo):
    """Com a MESMA matriz que o ATP usa, o desvio cai para 6,7 mV.

    Atribuição do resíduo: o que sobra na leitura real é a matriz de
    transformação, e não o equivalente, o cabo, a ligação ou o motor —
    todos esses continuam iguais entre as duas montagens.
    """
    linhas = modelo_complexo.phasor_validation()
    assert max(r.error for r in linhas) < TOL_LEITURA_COMPLEXA
    for r in linhas:
        if r.kind == "tensao":
            assert abs(r.obtained - r.reference) < 0.02, r.as_dict()
        else:
            assert abs(r.obtained - r.reference) < 0.005, r.as_dict()


def test_residuo_da_leitura_real_e_de_sequencia_zero(validacao):
    """O resíduo é o MESMO fasor nos seis nós a montante e no neutro.

    9,94 a 10,01 V — assinatura inequívoca de sequência zero, coerente com
    ``ΔZ₀₁·Î₁`` calculado no cabeçalho do módulo.
    """
    alvos = ["X0029A", "X0029B", "X0029C", "X0002A", "X0002B", "X0002C", "XX0003"]
    desvios = [
        next(r for r in validacao if r.quantity == n) for n in alvos
    ]
    modulos = [abs(r.obtained - r.reference) for r in desvios]
    assert min(modulos) > 9.5 and max(modulos) < 10.5
    # E é comum: os fasores de desvio são praticamente o mesmo número.
    fasores = [r.obtained - r.reference for r in desvios]
    espalhamento = max(abs(f - fasores[0]) for f in fasores)
    assert espalhamento < 0.35 * abs(fasores[0])


# ---------------------------------------------------------------------------
# 5. Conservação de potência
# ---------------------------------------------------------------------------


def test_conservacao_de_potencia_contra_a_perda_total_da_listagem(modelo):
    """A perda total montada bate com os 997 130,9 W da listagem.

    Decomposição obtida: motor 866 986 + cabo 61 574 + ligação 34 106 +
    ``Z₁`` 17 875 + neutro 121 + magnetização 15 366 = 996 028 W, contra
    997 131 W — 0,11%. O déficit residual é do ramo fonte–triângulo do
    lado de 13,8 kV e das perdas transversais da linha a montante, nenhum
    dos dois representado [FATO: arquivo].
    """
    b = modelo.power_balance()
    assert b["erro_relativo"] < TOL_POTENCIA
    assert b["total_dissipado_W"] < b["referencia_W"]  # déficit, não excesso
    assert b["motor_W"] == pytest.approx(867000.0, rel=1e-3)
    assert b["magnetizacao_W"] == pytest.approx(15366.0, rel=1e-3)


def test_potencia_fornecida_iguala_a_dissipada(modelo):
    """Fechamento interno: as f.e.m. entregam exatamente o que se dissipa."""
    b = modelo.power_balance()
    assert b["residuo_interno_W"] < 1.0e-3
    assert b["fornecida_W"] == pytest.approx(b["total_dissipado_W"], rel=1e-9)


def test_conservacao_de_potencia_na_leitura_complexa(modelo_complexo):
    """Com a matriz do ATP o fechamento vai a 0,0088% — 12 vezes melhor."""
    b = modelo_complexo.power_balance()
    assert b["erro_relativo"] < 1.0e-4


def test_amortecedor_nao_dissipa_em_regime(modelo):
    """O ramo amortecedor é transparente no regime — a listagem diz "aberta"."""
    b = modelo.power_balance()
    assert b["amortecedor_W"] == pytest.approx(0.0, abs=1e-9)


# ---------------------------------------------------------------------------
# 6. Ausência de transitório espúrio de partida
# ---------------------------------------------------------------------------


def test_marcha_no_tempo_nao_tem_transitorio_espurio_de_partida(marcha_em_regime):
    """Três ciclos com o disjuntor fechado, contra a onda fasorial.

    Desvio máximo medido: 2,0 mV em 3149 V — 6,4·10⁻⁷ relativo. É a
    prova de que a semeadura de regime é coerente com o modelo integrado,
    o cabo acoplado inclusive.
    """
    deriva = marcha_em_regime.steady_state_drift()
    assert max(deriva.values()) < TOL_DERIVA_V, deriva


def test_marcha_reproduz_o_pico_de_regime_em_todas_as_fases(marcha_em_regime):
    """O pico da série simulada é o módulo do fasor, fase a fase."""
    sol = marcha_em_regime.phasor_solution()
    for ph, node in zip(PHASES, NODES_MOTOR):
        probe = marcha_em_regime.motor_probes[ph]
        assert float(np.max(np.abs(probe.values))) == pytest.approx(
            abs(sol.node_phasor(node)), rel=1e-5
        )


def test_marcha_mantem_a_corrente_de_regime_no_disjuntor(marcha_em_regime, referencia):
    """A corrente do polo na marcha tem o pico publicado pela listagem."""
    for ph, i_ref in zip(PHASES, referencia.breaker_currents()):
        probe = marcha_em_regime.current_probes[ph]
        assert float(np.max(np.abs(probe.values))) == pytest.approx(
            abs(i_ref), rel=2.0e-3
        )


def test_amortecedor_permanece_bloqueado_com_o_disjuntor_fechado(marcha_em_regime):
    """Sem estado de arco não há habilitação — nem disparo, nem energia."""
    assert marcha_em_regime.snubber_gate is not None
    assert marcha_em_regime.snubber_gate.armed is False
    assert all(v == 0.0 for v in marcha_em_regime.snubber_energy_J.values())
    assert all(not b.switch.closed for b in marcha_em_regime.snubbers)


# ---------------------------------------------------------------------------
# 7. Manobra: os fatos da listagem que mudam a modelagem
# ---------------------------------------------------------------------------


def test_controlador_mestre_arma_no_primeiro_arco_e_nao_desarma(manobra):
    """MODEL ``SNUB_CTRL``: ``FM`` trava em 1 e nunca volta [FATO: arquivo].

    A habilitação ocorre no primeiro passo após a separação do polo R
    (14,55 ms), que é o primeiro estado de arco da janela.
    """
    gate = manobra.snubber_gate
    assert gate is not None and gate.armed
    assert gate.armed_time_s == pytest.approx(VCB_SEPARATION_TIME_S[0], abs=2e-5)


class _PoloFalso:
    """Duplo de polo para exercitar a trava do controlador mestre."""

    def __init__(self) -> None:
        self.state = "closed"
        self.arc_established = False


def test_controlador_mestre_trava_a_habilitacao():
    """Uma vez em arco, a habilitação NÃO volta a zero [FATO: arquivo].

    O MODEL do arquivo escreve ``IF (... OR FM > 0.5) THEN FM := 1.0`` e
    nunca atribui zero fora do bloco ``INIT``.
    """
    polo = _PoloFalso()
    disparos: list[float] = []
    gate = SnubberArmingGate([polo], [lambda t, solver: disparos.append(t)])
    gate(0.001, None)
    assert not gate.armed and disparos == []
    polo.state = "arcing"
    gate(0.002, None)
    assert gate.armed and gate.armed_time_s == pytest.approx(0.002)
    polo.state = "cleared"
    polo.arc_established = False
    gate(0.003, None)
    assert gate.armed  # a trava não é liberada
    assert disparos == [0.002, 0.003]
    gate.reset()
    assert not gate.armed and gate.armed_time_s is None


def test_valvula_conduz_em_praticamente_todo_semiciclo_apos_armada(manobra):
    """2404 V de disparo contra 3386 V de pico: uma vez armada, conduz sempre.

    Consequência declarada do [FATO: listagem] "Valve. 2.404E+03" — a
    energia dissipada nos 30 Ω é de milhares de joules por fase, e não de
    dezenas como seria num amortecedor que só atua nas reignições.
    """
    assert SNUBBER_BREAKOVER_V < 3386.0
    energia = manobra.snubber_energy_J
    assert min(energia.values()) > 1.0e3
    assert all(b.controller.n_firings >= 1 for b in manobra.snubbers)


def test_polos_recebem_os_dados_por_polo_do_arquivo(modelo):
    """Instantes, correntes de corte e capacidades são FIXOS e distintos."""
    for pole, t_sep, i_ch, didt in zip(
        modelo.poles,
        VCB_SEPARATION_TIME_S,
        VCB_CHOPPING_CURRENT_A,
        VCB_DIDT_CAPABILITY_A_PER_US,
    ):
        assert pole.separation_time_s == pytest.approx(t_sep)
        assert pole.sampled_chopping_current_A == pytest.approx(i_ch)
        assert pole.didt_capability_A_per_us == pytest.approx(didt)
        assert pole.didt_convention == "interrupt_above"


def test_criterio_de_reignicao_traz_o_fator_de_dez_por_cento(modelo):
    """``|V_gap| > V_wth·1,1`` entra escalando os dois coeficientes da lei."""
    rec = modelo.poles[0].recovery
    assert rec.a_kV_per_ms == pytest.approx(VCB_RRDS_A_KV_PER_MS * 1.1)
    assert rec.b_kV_per_ms2 == pytest.approx(VCB_RRDS_B_KV_PER_MS2 * 1.1)
    # Em 1 ms: 1,1·(0,801 + 1,226) = 2,2297 kV.
    assert rec.withstand_V(1.0e-3) == pytest.approx(2229.7, rel=1e-4)


def test_variante_sem_amortecedor_nao_monta_o_ramo():
    """O arquivo base não tem o ramo; a montagem correspondente também não."""
    m = build_reference_model(with_snubber=False)
    assert m.snubbers == ()
    assert m.snubber_gate is None
    assert m.max_phasor_error("corrente") < TOL_CARGA


def test_caso_valida_os_parametros():
    """Parâmetros fora de faixa são recusados na construção do caso."""
    with pytest.raises(ValueError, match="dt_s"):
        AtpReferenceCase(dt_s=0.0)
    with pytest.raises(ValueError, match="cable_phasor_reading"):
        AtpReferenceCase(cable_phasor_reading="outra")
    with pytest.raises(ValueError, match="separation_times_s"):
        AtpReferenceCase(separation_times_s=(1.0, 2.0))
    with pytest.raises(ValueError, match="gap_capacitance_F"):
        AtpReferenceCase(gap_capacitance_F=-1.0)


def test_limitacoes_declaradas_cobrem_o_que_foi_substituido():
    """Toda substituição feita no caminho está declarada no catálogo."""
    for chave in (
        "emt_atp_ref_transformer_not_decoded",
        "emt_atp_ref_upstream_lumped",
        "emt_atp_ref_real_modal_matrix",
        "emt_atp_ref_arc_branch_not_represented",
        "emt_atp_ref_dielectric_timer",
        "emt_atp_ref_valve_ideal",
        "emt_atp_ref_literal_model_defect",
    ):
        assert chave in KNOWN_LIMITATIONS
        assert len(KNOWN_LIMITATIONS[chave]) > 120


def test_modelo_pronto_para_simular_expoe_a_auditoria(modelo):
    """A função de entrada devolve montagem executável e auditável."""
    assert modelo.circuit.is_built or modelo.circuit.build() > 0
    assert set(modelo.trv_probes) == set(PHASES)
    assert modelo.reference.path.is_file()
    assert modelo.thevenin.emf_peak_V > 0.0
    linhas = [r.as_dict() for r in modelo.phasor_validation()]
    assert all("erro_relativo" in linha for linha in linhas)


# ===========================================================================
# CARACTERIZAÇÃO DA MANOBRA NO MODO DE COMPATIBILIDADE LITERAL
# ===========================================================================
#
# ATENÇÃO — LEIA ANTES DE USAR ESTES NÚMEROS
# ------------------------------------------
# Tudo o que segue é CARACTERIZAÇÃO DO MOTOR, não validação contra o
# trabalho de referência. Os valores fixados abaixo registram o que ESTE
# motor produz hoje, com o caso montado a partir do ARQUIVO, para que
# qualquer mudança futura do kernel apareça como quebra de teste. Eles
# NÃO concordam com a Tabela III do trabalho de referência e não foram
# ajustados para concordar: nenhum parâmetro foi movido, nenhuma
# tolerância foi afrouxada e nenhuma janela de medição foi escolhida a
# posteriori.
#
# Protocolo de medição, fixado antes de olhar os números e idêntico para
# as três fases, as duas configurações e os dois passos de integração:
#
# * janela PRIMÁRIA: a janela inteira do arquivo, 0 a 45 ms;
# * taxa de crescimento: maior variação em janela deslizante FIXA de
#   1 µs — e não entre amostras consecutivas —, para que 1 µs e 50 ns
#   sejam comparáveis entre si;
# * pico da tensão através do disjuntor COM SINAL, na convenção
#   ``V(X0001x) − V(X0002x)`` (lado fonte menos lado carga);
# * tensão no terminal do motor: maior módulo de ``V(01ATx)``, grandeza
#   que a Tabela III NÃO publica e que é a que interessa ao modelo de
#   dano do isolamento.
#
# Confronto com a Tabela III do trabalho (p. 3), janela inteira, 1 µs
# ---------------------------------------------------------------------
#
# ==========  ==================  ==================  ==============
# Fase        Tabela III          Obtido (literal)    Razão
# ==========  ==================  ==================  ==============
# SEM ramo amortecedor
# A           −30,24 kV           +688,23 kV          22,8×
# B           +41,44 kV           −631,34 kV          15,2×
# C           −38,30 kV           +703,32 kV          18,4×
# COM ramo amortecedor
# A           +6,35 kV            −20,89 kV           3,3×
# B           +13,65 kV           −98,19 kV           7,2×
# C           −9,98 kV            +81,67 kV           8,2×
# ==========  ==================  ==================  ==============
#
# A causa dominante está no PRÓPRIO ARQUIVO e é verificável linha a
# linha, não no motor:
#
# 1. ``SW_STATEr := 0.0`` é executado na transição de estado 0 para 1,
#    isto é, na SEPARAÇÃO DOS CONTATOS [FATO: arquivo, MODEL VCB_Rr,
#    linhas 144-156]. A chave ideal abre com a corrente instantânea que
#    houver, e não no limiar de corte. O texto do trabalho de referência
#    diz o contrário — "the arc is forced to extinguish when the
#    instantaneous current falls below a chopping level Ich of 1 A to
#    2 A" [FATO: doc A, p. 2, IV-B]. Da corrente de regime publicada
#    resulta, no instante de separação de cada polo: 8,1 % do pico no
#    polo R (t = 14,55 ms), 40,2 % no polo S (24,75 ms) e 99,0 % no polo
#    T (24,81 ms) [CÁLCULO PRÓPRIO]. Os zeros naturais seguintes estão
#    em 14,764 / 25,848 / 28,598 ms. Interromper 900 A na indutância de
#    8,9795 mH do motor contra a capacitância do cabo produz
#    ``sqrt(2E/C)`` da ordem de centenas de quilovolts — que é
#    exatamente o que se obtém.
# 2. ``I_PREV := I_CBr`` está DENTRO do bloco ``IF TNOW > TIME_PREVr``,
#    que precede o teste ``IF I_PREV * I_CBr <= 0`` [FATO: arquivo,
#    linhas 117-128]. O teste compara a corrente com ela mesma;
#    ``T_ZEROr`` nunca é atribuído, ``V_WITHr`` permanece nulo e NENHUMA
#    reignição é declarada — enquanto o trabalho relata "the abrupt
#    interruption and the successive reignitions" [FATO: doc A, p. 3,
#    V-A]. É por isso que todas as contagens fixadas abaixo são ZERO.
# 3. A entrada de corrente do MODEL é declarada como TENSÃO NODAL:
#    ``MM0003 {v(XX0027)}`` [FATO: arquivo, linha 17], sendo ``XX0027``
#    um nó entre duas chaves ``MEASURING``. Lida como corrente da chave
#    — que é a leitura adotada aqui —, ela vale zero no passo seguinte à
#    abertura, de modo que ``ABS(I_CBr) <= I_CHOPr`` dispara sempre um
#    passo depois da separação, com corrente registrada de 0 A e não de
#    1 A ou 2 A.
#
# O contraexemplo que fecha o diagnóstico está em
# :func:`test_caracterizacao_polo_R_isolado_1us`: o polo R, ÚNICO cuja
# separação cai a 0,21 ms de um zero natural de corrente, produz 29,91 kV
# de pico contra os 30,24 kV da Tabela III — 1,1 % de desvio, sem ajuste
# nenhum. O erro dos outros dois polos não é, portanto, do modelo do
# circuito.
#
# Influência do passo de integração (janela inteira, medida em execução
# dedicada de ~90 s por cenário, fora da suíte)
# ---------------------------------------------------------------------
#
# =====  ===================  ===================  ===================
# Fase   1 µs pico / dv/dt    50 ns pico / dv/dt   razão pico
# =====  ===================  ===================  ===================
# SEM ramo amortecedor
# A      688,23 / 240,82      824,45 / 407,30      1,20
# B      −631,34 / 264,92     839,96 / 765,77      1,33
# C      703,32 / 287,57      907,45 / 804,84      1,29
# COM ramo amortecedor
# A      −20,89 / 16,03       −71,67 / 71,67       3,43
# B      −98,19 / 69,31       −563,82 / 563,82     5,74
# C      81,67 / 55,57        479,08 / 479,08      5,87
# =====  ===================  ===================  ===================
#
# (picos em kV, taxas em kV/µs.) O resultado NÃO está convergido no
# passo: reduzir o passo de 20 vezes aumenta o pico de 20 a 33 % sem
# amortecedor e de 3,4 a 5,9 vezes com amortecedor. É o comportamento
# esperado de uma interrupção descontínua de corrente indutiva grande,
# em que o pico é fixado por como a descontinuidade é resolvida — de
# modo que o pico do caso original não é grandeza convergida, e a
# concordância de 1,1 % do polo R vale para o passo de 1 µs do arquivo,
# não como propriedade independente do passo.
#
# Os testes de 50 ns abaixo usam o polo R isolado e janela de 14,7 ms
# (≈ 294 000 passos, ~30 s cada) porque a janela inteira a 50 ns custa
# ~90 s e não cabe no limite de 60 s por teste da integração contínua.

#: Valores obtidos, modo literal, passo de 1 µs, janela inteira de 45 ms.
#: Por fase: (pico da TRV [kV], instante do pico [ms], dv/dt máxima em
#: janela de 1 µs [kV/µs], reignições, instante do corte [ms], pico da
#: tensão no terminal do motor [kV]).
CARACT_LITERAL_1US_SEM_AMORTECEDOR: dict[str, tuple] = {
    "a": (688.2305, 24.824, 240.8221, 0, 14.552, 504.3848),
    "b": (-631.3355, 24.853, 264.9194, 0, 24.751, 541.4999),
    "c": (703.3198, 24.824, 287.5703, 0, 24.811, 490.6169),
}

CARACT_LITERAL_1US_COM_AMORTECEDOR: dict[str, tuple] = {
    "a": (-20.8935, 24.750, 16.0288, 0, 14.552, 32.4603),
    "b": (-98.1937, 24.751, 69.3143, 0, 24.751, 34.7156),
    "c": (81.6689, 24.811, 55.5693, 0, 24.811, 28.7898),
}

#: Tabela III do trabalho de referência [FATO: doc A, p. 3]: por fase,
#: (pico [kV], RRRV [kV/µs]) sem e com ramo amortecedor. Está aqui para
#: o teste que REGISTRA a divergência, não para servir de critério.
TABELA_III_SEM_AMORTECEDOR: dict[str, tuple[float, float]] = {
    "a": (-30.24, 13.90),
    "b": (41.44, 15.05),
    "c": (-38.30, 19.00),
}

TABELA_III_COM_AMORTECEDOR: dict[str, tuple[float, float]] = {
    "a": (6.35, 3.28),
    "b": (13.65, 13.11),
    "c": (-9.98, 9.43),
}

#: Tolerância dos valores FIXADOS de caracterização. A marcha é
#: determinística; a folga cobre só a aritmética de ponto flutuante.
TOL_CARACT = 1.0e-4


def _taxa_kV_por_us(tempo_s, valores_V, janela_s: float = 1.0e-6) -> float:
    """Maior variação em janela deslizante FIXA [kV/µs].

    A janela é fixa em tempo, e não em número de amostras, justamente
    para que dois passos de integração diferentes sejam comparáveis: a
    taxa entre amostras consecutivas cresce com o refinamento do passo
    sem que nada de físico tenha mudado.
    """
    t = np.asarray(tempo_s, dtype=float)
    v = np.asarray(valores_V, dtype=float) * 1.0e-3
    if t.size < 2:
        return 0.0
    passo = float(np.median(np.diff(t)))
    n = max(1, int(round(float(janela_s) / passo)))
    if v.size <= n:
        n = 1
    return float(np.max(np.abs((v[n:] - v[:-n]) / (t[n:] - t[:-n])))) / 1.0e6


@pytest.fixture(scope="module")
def manobra_literal_sem():
    """Janela inteira, modo literal, variante BASE do arquivo."""
    m = build_reference_model(with_snubber=False, atp_model_compatibility=True)
    m.run()
    return m


@pytest.fixture(scope="module")
def manobra_literal_com():
    """Janela inteira, modo literal, variante COM ramo amortecedor."""
    m = build_reference_model(with_snubber=True, atp_model_compatibility=True)
    m.run()
    return m


def _confere_caracterizacao(modelo, esperado: dict[str, tuple]) -> None:
    """Confronta as seis grandezas fixadas, fase a fase."""
    reig = modelo.reignition_counts
    corte = modelo.chopping_times_s
    for ph, (pico, t_pico, taxa, n_reig, t_corte, v_motor) in esperado.items():
        sonda = modelo.trv_probes[ph]
        v = np.asarray(sonda.values)
        t = np.asarray(sonda.time_s)
        k = int(np.argmax(np.abs(v)))
        assert v[k] * 1.0e-3 == pytest.approx(pico, rel=TOL_CARACT)
        assert t[k] * 1.0e3 == pytest.approx(t_pico, rel=TOL_CARACT)
        assert _taxa_kV_por_us(t, v) == pytest.approx(taxa, rel=TOL_CARACT)
        assert reig[ph] == n_reig
        assert corte[ph] is not None
        assert corte[ph] * 1.0e3 == pytest.approx(t_corte, rel=TOL_CARACT)
        v_mot = float(np.max(np.abs(modelo.motor_probes[ph].values))) * 1.0e-3
        assert v_mot == pytest.approx(v_motor, rel=TOL_CARACT)


def test_caracterizacao_literal_sem_amortecedor_1us(manobra_literal_sem):
    """Fixa o que o motor produz hoje na variante BASE — não é aceite."""
    _confere_caracterizacao(manobra_literal_sem, CARACT_LITERAL_1US_SEM_AMORTECEDOR)
    assert manobra_literal_sem.snubbers == ()
    assert manobra_literal_sem.snubber_gate is None


def test_caracterizacao_literal_com_amortecedor_1us(manobra_literal_com):
    """Fixa o que o motor produz hoje na variante COM amortecedor."""
    _confere_caracterizacao(manobra_literal_com, CARACT_LITERAL_1US_COM_AMORTECEDOR)
    # O controlador mestre do arquivo arma no estado 2 (aberto), que o
    # polo literal alcança no passo seguinte à separação do polo R.
    assert manobra_literal_com.snubber_gate.armed
    assert manobra_literal_com.snubber_gate.armed_time_s * 1.0e3 == pytest.approx(
        14.551, rel=TOL_CARACT
    )
    energia = manobra_literal_com.snubber_energy_J
    assert energia["a"] == pytest.approx(26.44, rel=1.0e-3)
    assert energia["b"] == pytest.approx(2326.37, rel=1.0e-3)
    assert energia["c"] == pytest.approx(3506.03, rel=1.0e-3)


def test_amortecedor_reduz_o_pico_em_todas_as_fases(
    manobra_literal_sem, manobra_literal_com
):
    """Efeito qualitativo que sobrevive à divergência: o ramo mitiga.

    Os valores absolutos divergem da Tabela III por mais de uma ordem de
    grandeza, mas o SINAL do efeito do ramo amortecedor é o mesmo do
    trabalho — e é a única conclusão que esta caracterização sustenta.
    """
    for ph in PHASES:
        sem = float(np.max(np.abs(manobra_literal_sem.trv_probes[ph].values)))
        com = float(np.max(np.abs(manobra_literal_com.trv_probes[ph].values)))
        assert com < sem
        v_sem = float(np.max(np.abs(manobra_literal_sem.motor_probes[ph].values)))
        v_com = float(np.max(np.abs(manobra_literal_com.motor_probes[ph].values)))
        assert v_com < v_sem


def test_divergencia_contra_a_tabela_III_e_registrada_e_nao_mascarada(
    manobra_literal_sem, manobra_literal_com
):
    """REGISTRA a divergência: nenhuma fase chega perto da Tabela III.

    Este teste falha se alguém, no futuro, "consertar" a divergência
    ajustando parâmetros sem registrar o ajuste: a discordância é o
    resultado honesto do caso como está no arquivo, e mudá-la exige
    mudar este teste e dizer por quê.
    """
    for modelo, tabela in (
        (manobra_literal_sem, TABELA_III_SEM_AMORTECEDOR),
        (manobra_literal_com, TABELA_III_COM_AMORTECEDOR),
    ):
        for ph, (pico_ref, _rrrv) in tabela.items():
            obtido = float(np.max(np.abs(modelo.trv_probes[ph].values))) * 1.0e-3
            assert obtido > 3.0 * abs(pico_ref), (
                f"fase {ph}: obtido {obtido:.2f} kV contra {pico_ref:.2f} kV da "
                f"Tabela III — se a razão caiu, a causa precisa ser explicada"
            )
        # E nenhuma reignição, contra as "successive reignitions" do texto.
        assert set(modelo.reignition_counts.values()) == {0}


def test_causa_da_divergencia_e_a_corrente_no_instante_da_separacao():
    """A separação de cada polo NÃO cai em zero de corrente — e isso é o caso.

    Da corrente de regime publicada pela listagem, no instante de
    separação de cada polo [CÁLCULO PRÓPRIO]. O polo R separa a 8 % do
    pico, o S a 40 % e o T a 99 %: é a razão de o polo R quase reproduzir
    a Tabela III e os outros dois não.
    """
    ref = load_reference()
    fracoes = []
    for k, t_sep in enumerate(VCB_SEPARATION_TIME_S):
        fasor = ref.breaker_currents()[k]
        instantanea = (fasor * cmath.exp(1j * OMEGA * t_sep)).real
        fracoes.append(abs(instantanea) / abs(fasor))
    assert fracoes[0] == pytest.approx(0.081, abs=0.002)
    assert fracoes[1] == pytest.approx(0.402, abs=0.002)
    assert fracoes[2] == pytest.approx(0.990, abs=0.002)


def test_caracterizacao_polo_R_isolado_1us():
    """Polo R sozinho: 29,91 kV contra 30,24 kV da Tabela III.

    Mantidos FECHADOS os polos S e T, o polo R interrompe a 0,21 ms do
    zero natural de sua corrente e o pico obtido fica a 1,1 % do valor
    publicado, sem ajuste nenhum. É o contraexemplo que separa a causa:
    o circuito e o equivalente estão certos; o que diverge é a lógica de
    abertura do MODEL nos polos que separam longe do zero.

    O número segue sendo CARACTERIZAÇÃO — a concordância vale para o
    passo de 1 µs do arquivo e não sobrevive ao refino do passo, como
    :func:`test_influencia_do_passo_no_polo_R_sem_amortecedor` mostra.
    """
    m = build_reference_model(
        with_snubber=False,
        atp_model_compatibility=True,
        separation_times_s=(0.01455, 10.0, 10.0),
        t_end_s=14.7e-3,
    )
    m.run()
    sonda = m.trv_probes["a"]
    v = np.asarray(sonda.values)
    t = np.asarray(sonda.time_s)
    k = int(np.argmax(np.abs(v)))
    assert v[k] * 1.0e-3 == pytest.approx(29.9106, rel=TOL_CARACT)
    assert t[k] * 1.0e3 == pytest.approx(14.690, rel=TOL_CARACT)
    assert _taxa_kV_por_us(t, v) == pytest.approx(19.5309, rel=TOL_CARACT)
    v_mot = float(np.max(np.abs(m.motor_probes["a"].values))) * 1.0e-3
    assert v_mot == pytest.approx(26.9744, rel=TOL_CARACT)
    # Distância ao valor publicado, registrada como número e não como
    # aprovação: 1,1 % no pico, 41 % na taxa.
    assert abs(abs(v[k]) * 1.0e-3 - 30.24) / 30.24 < 0.02
    assert _taxa_kV_por_us(t, v) / 13.90 > 1.35


def test_caracterizacao_polo_R_isolado_com_amortecedor_1us():
    """O mesmo polo R isolado, com o ramo amortecedor armado."""
    m = build_reference_model(
        with_snubber=True,
        atp_model_compatibility=True,
        separation_times_s=(0.01455, 10.0, 10.0),
        t_end_s=14.7e-3,
    )
    m.run()
    sonda = m.trv_probes["a"]
    v = np.asarray(sonda.values)
    t = np.asarray(sonda.time_s)
    k = int(np.argmax(np.abs(v)))
    assert v[k] * 1.0e-3 == pytest.approx(-9.9123, rel=TOL_CARACT)
    assert _taxa_kV_por_us(t, v) == pytest.approx(8.6921, rel=TOL_CARACT)
    v_mot = float(np.max(np.abs(m.motor_probes["a"].values))) * 1.0e-3
    assert v_mot == pytest.approx(6.3229, rel=TOL_CARACT)


def test_influencia_do_passo_no_polo_R_sem_amortecedor():
    """Passo de 50 ns no lugar de 1 µs: o pico do polo R triplica.

    Segundo cenário pedido pelo protocolo. A mesma montagem, a mesma
    janela e o mesmo estimador de taxa (janela fixa de 1 µs) — só o
    passo muda. O resultado NÃO está convergido no passo, e é por isso
    que o pico do caso original não pode ser lido como grandeza física
    independente da discretização.
    """
    m = build_reference_model(
        with_snubber=False,
        atp_model_compatibility=True,
        separation_times_s=(0.01455, 10.0, 10.0),
        dt_s=50.0e-9,
        t_end_s=14.7e-3,
    )
    m.run()
    sonda = m.trv_probes["a"]
    v = np.asarray(sonda.values)
    t = np.asarray(sonda.time_s)
    k = int(np.argmax(np.abs(v)))
    assert v[k] * 1.0e-3 == pytest.approx(-95.8441, rel=TOL_CARACT)
    assert t[k] * 1.0e3 == pytest.approx(14.5501, rel=TOL_CARACT)
    assert _taxa_kV_por_us(t, v) == pytest.approx(95.8441, rel=TOL_CARACT)
    v_mot = float(np.max(np.abs(m.motor_probes["a"].values))) * 1.0e-3
    assert v_mot == pytest.approx(38.5218, rel=TOL_CARACT)
    # Contra os 29,9106 kV do mesmo ensaio a 1 µs: 3,2 vezes.
    assert abs(v[k]) * 1.0e-3 / 29.9106 == pytest.approx(3.204, rel=2.0e-3)


def test_influencia_do_passo_no_polo_R_com_amortecedor():
    """O mesmo refino de passo com o ramo amortecedor armado: 7,2 vezes."""
    m = build_reference_model(
        with_snubber=True,
        atp_model_compatibility=True,
        separation_times_s=(0.01455, 10.0, 10.0),
        dt_s=50.0e-9,
        t_end_s=14.7e-3,
    )
    m.run()
    sonda = m.trv_probes["a"]
    v = np.asarray(sonda.values)
    t = np.asarray(sonda.time_s)
    k = int(np.argmax(np.abs(v)))
    assert v[k] * 1.0e-3 == pytest.approx(-71.6687, rel=TOL_CARACT)
    assert _taxa_kV_por_us(t, v) == pytest.approx(71.6687, rel=TOL_CARACT)
    v_mot = float(np.max(np.abs(m.motor_probes["a"].values))) * 1.0e-3
    assert v_mot == pytest.approx(9.8652, rel=TOL_CARACT)
    assert abs(v[k]) * 1.0e-3 / 9.9123 == pytest.approx(7.230, rel=2.0e-3)


def test_modo_literal_e_selecionado_por_parametro_e_nao_muda_o_padrao():
    """O modo literal é OPCIONAL: sem o parâmetro nada do caso muda."""
    padrao = AtpReferenceCase()
    assert padrao.atp_model_compatibility is False
    assert padrao.zero_crossing_order == ATP_ZERO_ORDER_LITERAL
    m_padrao = build_reference_model(with_snubber=True, t_end_s=1.0e-4)
    assert m_padrao.literal_poles == ()
    assert isinstance(m_padrao.snubber_gate, SnubberArmingGate)
    m_literal = build_reference_model(
        with_snubber=True, atp_model_compatibility=True, t_end_s=1.0e-4
    )
    assert len(m_literal.literal_poles) == 3
    # No modo literal o polo é chave ideal MAIS o ramo série R-L-C.
    assert len(m_literal.literal_poles[0].components) == 4
    with pytest.raises(ValueError, match="zero_crossing_order"):
        AtpReferenceCase(zero_crossing_order="outra")
    with pytest.raises(ValueError, match="gap_capacitance_F"):
        AtpReferenceCase(atp_model_compatibility=True, gap_capacitance_F=6.0e-6)


def test_defeito_de_ordem_do_MODEL_esta_declarado_e_e_o_que_o_arquivo_executa():
    """Sem reignição porque ``T_ZERO`` nunca parte — e isso está declarado."""
    m = build_reference_model(
        with_snubber=False, atp_model_compatibility=True, t_end_s=20.0e-3
    )
    m.run()
    for polo in m.poles:
        assert polo.zero_crossing_order == ATP_ZERO_ORDER_LITERAL
        assert polo.t_zero == -1.0
        assert polo.withstand_V() == 0.0
        assert polo.result.reignition_count == 0
        assert polo.result.zero_crossing_times_s == []
    assert "emt_atp_ref_literal_model_defect" in KNOWN_LIMITATIONS
    assert "I_PREV" in KNOWN_LIMITATIONS["emt_atp_ref_literal_model_defect"]
