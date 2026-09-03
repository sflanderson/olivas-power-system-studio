"""
tests/test_emt_vcb_snubber.py — verificação dos modelos de manobra do
motor EMT dedicado: disjuntor a vácuo dinâmico
(:mod:`app.simulation.emt.vcb`), *snubber* ativo a tiristor
(:mod:`app.simulation.emt.snubber`) e o caso paramétrico do Documento A
(:mod:`app.simulation.emt.cases.motor_switching`).

Todo valor de referência é (a) solução analítica fechada do balanço de
energia do circuito, (b) valor publicado na Tabela I, II ou III do
Documento A, (c) valor lido no ``vcb_reignition.mod`` do repositório, ou
(d) [CÁLCULO PRÓPRIO] medido nesta sessão e documentado no comentário do
teste.

Bancada canônica de manobra
============================

Quase todos os testes de VCB usam o mesmo circuito mínimo, que é a menor
rede capaz de reproduzir os três fenômenos de interesse::

    E(60 Hz) ──[L_s]── p ──[chave/VCB]── n1 ──┬── L ── gnd
                                              └── C ── gnd

* ``L = 10 mH`` e ``C = 10 nF`` ⇒ ``sqrt(L/C) = 1000 Ω`` e frequência
  natural de 15,92 kHz — é o reservatório magnético cuja energia o corte
  transfere para a capacitância;
* ``L_s = 1 mH`` é a indutância do lado da fonte, sem a qual a reignição
  não produz malha de alta frequência (a chave ligaria a fonte ideal
  diretamente ao nó de carga) e a escalada por reignições não existe;
* fase inicial de 90° para que a fonte parta do próprio pico, anulando a
  componente contínua da corrente do indutor e garantindo cruzamentos por
  zero em 8,33 ms e múltiplos [CÁLCULO PRÓPRIO].
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from app.simulation.emt import (
    BranchCurrentProbe,
    Capacitor,
    Circuit,
    DifferentialVoltageProbe,
    Inductor,
    NodeVoltageProbe,
    Resistor,
    Solver,
    Switch,
    VoltageSource,
)
from app.simulation.emt.cases import (
    DOC_A_TABLE_III,
    RL_VARIANT_FIG2,
    RL_VARIANT_TABLE_I,
    CableParameters,
    MotorParameters,
    MotorSwitchingCase,
    SnubberParameters,
    SourceParameters,
    TransformerParameters,
    VCBParameters,
)
from app.simulation.emt.cases import motor_switching as case_mod
from app.simulation.emt.probes import to_stress_profile
from app.simulation.emt.snubber import (
    ATP_SNUBBER_BREAKOVER_V,
    ATP_SNUBBER_DEIONIZATION_TIME_S,
    ATP_SNUBBER_GATE_NAMES,
    ATP_SNUBBER_HOLDING_CURRENT_A,
    ATP_SNUBBER_LATCH_THRESHOLD,
    ATP_SNUBBER_RESISTANCE_OHM,
    DOC_A_SNUBBER_RESISTANCE_OHM,
    SNUBBER_BLOCKED,
    SNUBBER_CONDUCTING,
    SnubberMasterTrigger,
    ThyristorSnubber,
    atp_state_code,
    build_atp_literal_snubber_branch,
    build_snubber_branch,
    three_phase_snubber,
)
from app.simulation.emt.snubber import KNOWN_LIMITATIONS as SNUBBER_LIMITATIONS
from app.simulation.emt.vcb import (
    ATP_C_ARC_F,
    ATP_C_CLOSED_F,
    ATP_C_OPEN_F,
    ATP_CB_ARCING,
    ATP_CB_ARCING_HF,
    ATP_CB_CLOSED,
    ATP_CB_OPEN,
    ATP_CURRENT_FROM_POLE,
    ATP_CURRENT_FROM_SWITCH,
    ATP_DIDT_CRIT_A_PER_US,
    ATP_I_CHOP_A,
    ATP_L_ARC_H,
    ATP_L_CLOSED_H,
    ATP_L_OPEN_H,
    ATP_R_ARC_OHM,
    ATP_R_CLOSED_OHM,
    ATP_R_OPEN_OHM,
    ATP_REIGNITION_MARGIN,
    ATP_RRDS_A_KV_PER_MS,
    ATP_RRDS_B_KV_PER_MS2,
    ATP_T_OPEN_S,
    ATP_ZERO_ORDER_DEFERRED,
    ATP_ZERO_ORDER_LITERAL,
    DIDT_INTERRUPT_ABOVE,
    DIDT_INTERRUPT_WITHIN,
    DOC_A_CHOPPING_RANGE_A,
    DOC_A_RRDS_A_KV_PER_MS,
    DOC_A_RRDS_B_KV_PER_MS2,
    DOC_A_STAGGER_RANGE_S,
    STATE_CLEARED,
    STATE_CLOSED,
    STATE_OPEN,
    AtpLiteralPole,
    AtpModelCompatibility,
    AtpVcbParameters,
    LinearRecovery,
    ParabolicRecovery,
    SwitchedCapacitor,
    SwitchedInductor,
    SwitchedResistor,
    VacuumCircuitBreakerModel,
    VcbPole,
    build_atp_literal_pole,
    build_vcb_pole,
    stagger_times,
    three_phase_atp_literal_poles,
    three_phase_vcb,
    vcb_from_mod_parameters,
)
from app.simulation.emt.vcb import KNOWN_LIMITATIONS as VCB_LIMITATIONS

# ---------------------------------------------------------------------------
# Bancada canônica
# ---------------------------------------------------------------------------

L_LOAD_H: float = 10.0e-3
C_LOAD_F: float = 10.0e-9
L_SOURCE_H: float = 1.0e-3
SOURCE_AMPLITUDE_V: float = 1000.0
#: sqrt(L/C) = 1000 Ω — impedância de surto do reservatório [CÁLCULO PRÓPRIO].
SURGE_OHM: float = math.sqrt(L_LOAD_H / C_LOAD_F)
#: Tensão do capacitor em regime no instante t = 0, com a fonte no próprio
#: pico: divisor indutivo ``V·L/(L+L_s) = 909,09 V`` [CÁLCULO PRÓPRIO]. É a
#: condição inicial CONSISTENTE semeada à mão (equivalente ao que
#: ``Solver(init="steady_state")`` faria): sem ela a bancada — que não tem
#: nenhuma resistência — mantém para sempre a oscilação de energização de
#: 50,3 kHz da malha L_s–C, que contamina todo pico medido.
C_INITIAL_V: float = SOURCE_AMPLITUDE_V * L_LOAD_H / (L_LOAD_H + L_SOURCE_H)
#: Recuperação dielétrica tão rápida que nenhuma reignição é possível —
#: isola o fenômeno de corte nos testes de balanço de energia.
NO_REIGNITION = ParabolicRecovery(a_kV_per_ms=1.0e6, b_kV_per_ms2=0.0)


def _bench(
    *,
    snubber_breakover_V: float | None = None,
    snubber_resistance_ohm: float = DOC_A_SNUBBER_RESISTANCE_OHM,
    snubber_kwargs: dict | None = None,
    source_inductance_H: float = L_SOURCE_H,
):
    """Monta a bancada canônica; devolve ``(circuito, chave, ramo_snubber)``."""
    ckt = Circuit("bancada_manobra")
    ckt.add(
        VoltageSource(
            "E", "src", "gnd",
            amplitude_V=SOURCE_AMPLITUDE_V, frequency_Hz=60.0, phase_deg=90.0,
        )
    )
    ckt.add(Inductor("Ls", "src", "p", source_inductance_H))
    switch = ckt.add(Switch("cb", "p", "n1", closed=True))
    ckt.add(Inductor("L", "n1", "gnd", L_LOAD_H))
    ckt.add(Capacitor("C", "n1", "gnd", C_LOAD_F, initial_voltage_V=C_INITIAL_V))
    branch = None
    if snubber_breakover_V is not None:
        branch = build_snubber_branch(
            "snub", "n1", "gnd",
            breakover_voltage_V=float(snubber_breakover_V),
            resistance_ohm=float(snubber_resistance_ohm),
            **(snubber_kwargs or {}),
        )
        ckt.extend(branch.components)
    return ckt, switch, branch


def _run_bench(
    *,
    recovery=NO_REIGNITION,
    chopping_current_A: float = 2.0,
    didt_capability_A_per_us: float = 15.0,
    didt_convention: str = DIDT_INTERRUPT_WITHIN,
    separation_time_s: float = 5.0e-3,
    max_reignitions: int = 200,
    dt: float = 2.0e-7,
    t_end: float = 9.0e-3,
    snubber_breakover_V: float | None = None,
    snubber_resistance_ohm: float = DOC_A_SNUBBER_RESISTANCE_OHM,
    snubber_kwargs: dict | None = None,
    source_inductance_H: float = L_SOURCE_H,
    vcb_kwargs: dict | None = None,
):
    """Executa a bancada; devolve um dicionário com modelo, sondas e ramo."""
    ckt, switch, branch = _bench(
        snubber_breakover_V=snubber_breakover_V,
        snubber_resistance_ohm=snubber_resistance_ohm,
        snubber_kwargs=snubber_kwargs,
        source_inductance_H=source_inductance_H,
    )
    solver = Solver(ckt, dt=dt, cda_full_steps=2)
    probes = {
        "v_load": solver.add_probe(NodeVoltageProbe("v_load", "n1")),
        "trv": solver.add_probe(DifferentialVoltageProbe("trv", "p", "n1")),
        "i_cb": solver.add_probe(BranchCurrentProbe("i_cb", switch)),
    }
    if branch is not None:
        probes["i_snub"] = solver.add_probe(
            BranchCurrentProbe("i_snub", branch.switch)
        )
    vcb = VacuumCircuitBreakerModel(
        switch,
        separation_time_s=separation_time_s,
        chopping_current_A=chopping_current_A,
        recovery=recovery,
        didt_capability_A_per_us=didt_capability_A_per_us,
        didt_convention=didt_convention,
        max_reignitions=max_reignitions,
        **(vcb_kwargs or {}),
    )
    controllers = [vcb] + ([branch.controller] if branch is not None else [])
    stats = solver.run(t_end=t_end, controllers=controllers)
    return {
        "circuit": ckt,
        "solver": solver,
        "switch": switch,
        "vcb": vcb,
        "branch": branch,
        "probes": probes,
        "stats": stats,
    }


def _trapz(y, x) -> float:
    """Integral pelo trapézio, compatível com numpy antigo e recente."""
    integrator = getattr(np, "trapezoid", None) or np.trapz
    return float(integrator(y, x))


# ===========================================================================
# 1. Leis de recuperação dielétrica
# ===========================================================================


def test_recuperacao_parabolica_reproduz_valor_do_documento_a():
    """``V_wth(1 ms) = A + B = 2,027 kV`` com os valores da Tabela II de A."""
    rec = ParabolicRecovery()
    assert rec.a_kV_per_ms == pytest.approx(DOC_A_RRDS_A_KV_PER_MS)
    assert rec.b_kV_per_ms2 == pytest.approx(DOC_A_RRDS_B_KV_PER_MS2)
    # 0,801·1 + 1,226·1² = 2,027 kV [CÁLCULO PRÓPRIO sobre a Tabela II].
    assert rec.withstand_V(1.0e-3) == pytest.approx(2027.0, rel=1e-9)
    # Em t = 0 a suportabilidade é NULA — o gap acabou de extinguir.
    assert rec.withstand_V(0.0) == 0.0
    # Tempo negativo (antes da extinção) é saturado em zero, não extrapolado.
    assert rec.withstand_V(-1.0e-3) == 0.0


def test_recuperacao_parabolica_inclinacao_alcanca_a_lei_linear_do_repositorio():
    """A inclinação ``A + 2Bt`` alcança os 17 kV/ms do ``.mod`` em 6,6 ms.

    [CÁLCULO PRÓPRIO; cf. Etapa 2 §9.2:
    ``t = (17 − 0,801)/(2·1,226) = 6,606 ms``.]
    """
    rec = ParabolicRecovery()
    assert rec.slope_kV_per_ms(0.0) == pytest.approx(DOC_A_RRDS_A_KV_PER_MS)
    t_ms = (17.0 - DOC_A_RRDS_A_KV_PER_MS) / (2.0 * DOC_A_RRDS_B_KV_PER_MS2)
    assert t_ms == pytest.approx(6.606, abs=1e-3)
    assert rec.slope_kV_per_ms(t_ms * 1.0e-3) == pytest.approx(17.0, rel=1e-9)


def test_recuperacao_linear_reproduz_os_defaults_do_mod_legado():
    """``U0 + k·t`` do ``.mod``: 17,69 kV em 1 ms, 8,7× a lei de A.

    [REPO: app/preprocessor/atp_templates/vcb_reignition.mod:52-53,115;
    razão 17690/2027 = 8,73 — CÁLCULO PRÓPRIO, cf. Etapa 2 §9.2.]
    """
    rec = LinearRecovery()
    assert rec.u0_V == pytest.approx(690.0)
    assert rec.k_V_per_us == pytest.approx(17.0)
    assert rec.withstand_V(1.0e-3) == pytest.approx(690.0 + 17.0 * 1000.0)
    razao = rec.withstand_V(1.0e-3) / ParabolicRecovery().withstand_V(1.0e-3)
    assert razao == pytest.approx(8.73, abs=0.01)


def test_leis_de_recuperacao_rejeitam_parametros_sem_sentido_fisico():
    """Constantes negativas ou lei identicamente nula são recusadas."""
    with pytest.raises(ValueError, match="a_kV_per_ms"):
        ParabolicRecovery(a_kV_per_ms=-1.0)
    with pytest.raises(ValueError, match="b_kV_per_ms2"):
        ParabolicRecovery(b_kV_per_ms2=-1.0)
    with pytest.raises(ValueError, match="nula"):
        ParabolicRecovery(a_kV_per_ms=0.0, b_kV_per_ms2=0.0)
    with pytest.raises(ValueError, match="u0_V"):
        LinearRecovery(u0_V=-1.0)
    with pytest.raises(ValueError, match="k_V_per_us"):
        LinearRecovery(k_V_per_us=-1.0)


# ===========================================================================
# 2. Construção e amostragem de I_ch
# ===========================================================================


def test_vcb_valida_entradas_do_construtor():
    """Tipo da chave, tempo, capacidade e convenção são validados."""
    ckt, switch, _ = _bench()
    with pytest.raises(ValueError, match="Switch"):
        VacuumCircuitBreakerModel(object(), separation_time_s=1.0e-3)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="separation_time_s"):
        VacuumCircuitBreakerModel(switch, separation_time_s=-1.0e-3)
    with pytest.raises(ValueError, match="didt_capability_A_per_us"):
        VacuumCircuitBreakerModel(switch, separation_time_s=1.0e-3, didt_capability_A_per_us=0.0)
    with pytest.raises(ValueError, match="didt_convention"):
        VacuumCircuitBreakerModel(switch, separation_time_s=1.0e-3, didt_convention="talvez")
    with pytest.raises(ValueError, match="chopping_range_A"):
        VacuumCircuitBreakerModel(switch, separation_time_s=1.0e-3, chopping_range_A=(2.0, 1.0))


def test_vcb_determinista_usa_o_ponto_medio_da_faixa_do_documento_a():
    """Sem semente e sem valor explícito, ``I_ch`` = 1,5 A (média de 1 a 2 A)."""
    _, switch, _ = _bench()
    vcb = VacuumCircuitBreakerModel(switch, separation_time_s=1.0e-3)
    assert vcb.chopping_distribution == "deterministic"
    assert vcb.sampled_chopping_current_A == pytest.approx(
        0.5 * (DOC_A_CHOPPING_RANGE_A[0] + DOC_A_CHOPPING_RANGE_A[1])
    )


def test_vcb_monte_carlo_exige_semente_explicita_e_e_reprodutivel():
    """Sem semente não há amostragem; com semente a realização se repete."""
    _, switch, _ = _bench()
    with pytest.raises(ValueError, match="semente"):
        VacuumCircuitBreakerModel(
            switch, separation_time_s=1.0e-3, chopping_distribution="uniform"
        )
    amostras = []
    for seed in (7, 7, 11):
        vcb = VacuumCircuitBreakerModel(switch, separation_time_s=1.0e-3, seed=seed)
        assert vcb.chopping_distribution == "uniform"
        i_ch = vcb.sampled_chopping_current_A
        assert DOC_A_CHOPPING_RANGE_A[0] <= i_ch <= DOC_A_CHOPPING_RANGE_A[1]
        amostras.append(i_ch)
    assert amostras[0] == amostras[1]
    assert amostras[0] != amostras[2]


def test_vcb_distribuicao_normal_exige_media_desvio_e_semente():
    """A normal (convenção do ``.mod``) exige os três parâmetros."""
    _, switch, _ = _bench()
    with pytest.raises(ValueError, match="média"):
        VacuumCircuitBreakerModel(
            switch, separation_time_s=1.0e-3,
            chopping_distribution="normal", chopping_sigma_A=1.0, seed=1,
        )
    with pytest.raises(ValueError, match="chopping_sigma_A > 0"):
        VacuumCircuitBreakerModel(
            switch, separation_time_s=1.0e-3, chopping_distribution="normal",
            chopping_current_A=5.0, seed=1,
        )
    vcb = VacuumCircuitBreakerModel(
        switch, separation_time_s=1.0e-3, chopping_distribution="normal",
        chopping_current_A=5.0, chopping_sigma_A=1.0, seed=1,
    )
    assert vcb.sampled_chopping_current_A > 0.0


# ===========================================================================
# 3. Corte de corrente e balanço de energia
# ===========================================================================


def test_balanco_de_energia_lc_e_a_referencia_do_teste_de_corte():
    """``½L·I² = ½C·V²`` ⇒ ``V_pico = I·sqrt(L/C)`` no kernel, sem manobra.

    Verificação da fórmula de referência diretamente sobre o kernel:
    um indutor com corrente inicial ``I0`` em paralelo com um capacitor
    descarregado oscila com pico ``I0·sqrt(L/C)``
    [LITERATURA: A. Greenwood, *Electrical Transients in Power Systems*,
    2. ed., Wiley, 1991, cap. 5].
    """
    i0 = 2.0
    ckt = Circuit("lc_livre")
    ckt.add(Inductor("L", "n1", "gnd", L_LOAD_H, initial_current_A=i0))
    ckt.add(Capacitor("C", "n1", "gnd", C_LOAD_F))
    solver = Solver(ckt, dt=1.0e-7, cda_full_steps=2)
    v = solver.add_probe(NodeVoltageProbe("v", "n1"))
    solver.run(t_end=40.0e-6)  # ≈ 0,64 período natural de 15,92 kHz
    esperado = i0 * SURGE_OHM
    assert float(np.max(np.abs(v.values))) == pytest.approx(esperado, rel=2.0e-3)


def test_corte_no_vcb_confere_com_o_balanco_de_energia():
    """O pico após o corte é ``sqrt(v_C0² + (I_ch·sqrt(L/C))²)``.

    No instante do corte o capacitor NÃO está descarregado — para carga
    indutiva, o zero de corrente coincide com o pico de tensão. A energia
    total do reservatório é, portanto, ``½C·v_C0² + ½L·I_ch²`` e o pico
    da oscilação subsequente é a hipotenusa [CÁLCULO PRÓPRIO].
    """
    out = _run_bench(dt=1.0e-7, chopping_current_A=2.0, t_end=9.5e-3)
    vcb = out["vcb"]
    assert vcb.chopping_time_s is not None
    assert vcb.state == STATE_OPEN
    # O corte ocorre no primeiro zero de corrente após a separação (8,33 ms).
    assert vcb.chopping_time_s == pytest.approx(8.311e-3, abs=1.0e-4)
    assert abs(vcb.result.chopping_current_at_chop_A) <= 2.0

    probe = out["probes"]["v_load"]
    t, v = probe.time_s, probe.values
    k = int(np.argmin(np.abs(t - vcb.chopping_time_s)))
    v_c0 = float(v[k])
    esperado = math.hypot(v_c0, vcb.result.chopping_current_at_chop_A * SURGE_OHM)
    observado = float(np.max(np.abs(v[k : k + 3000])))
    assert observado == pytest.approx(esperado, rel=1.0e-2)


def test_vcb_nao_corta_antes_do_instante_de_separacao():
    """Antes de ``separation_time_s`` a chave permanece fechada."""
    out = _run_bench(separation_time_s=20.0e-3, t_end=9.0e-3)
    vcb = out["vcb"]
    assert vcb.state == STATE_CLOSED
    assert vcb.chopping_time_s is None
    assert vcb.reignition_count == 0
    assert out["switch"].closed is True
    # A corrente do disjuntor cruzou o zero de 8,33 ms sem qualquer corte.
    i = out["probes"]["i_cb"].values
    assert float(np.min(np.abs(i))) < 2.0


def test_corte_ocorre_com_corrente_abaixo_do_nivel_de_chopping():
    """A corrente no passo do corte respeita ``|i| <= I_ch``."""
    for i_ch in (1.0, 1.5, 2.0):
        out = _run_bench(chopping_current_A=i_ch, dt=1.0e-7)
        vcb = out["vcb"]
        assert vcb.chopping_time_s is not None
        assert abs(vcb.result.chopping_current_at_chop_A) <= i_ch


def test_pico_de_corte_escala_linearmente_com_o_nivel_de_chopping():
    """Dobrar ``I_ch`` dobra a parcela magnética do pico [CÁLCULO PRÓPRIO]."""
    picos = {}
    for i_ch in (1.0, 2.0):
        out = _run_bench(chopping_current_A=i_ch, dt=1.0e-7)
        vcb = out["vcb"]
        probe = out["probes"]["v_load"]
        k = int(np.argmin(np.abs(probe.time_s - vcb.chopping_time_s)))
        v_c0 = float(probe.values[k])
        pico = float(np.max(np.abs(probe.values[k : k + 3000])))
        # Remove a parcela capacitiva já presente no instante do corte.
        picos[i_ch] = math.sqrt(max(0.0, pico**2 - v_c0**2))
    assert picos[2.0] / picos[1.0] == pytest.approx(2.0, rel=5.0e-2)


# ===========================================================================
# 4. Recuperação dielétrica e reignição
# ===========================================================================


def test_sem_reignicao_quando_a_suportabilidade_cresce_mais_rapido_que_a_trv():
    """Suportabilidade rápida ⇒ interrupção limpa e TRV plena.

    Com ``A = 10⁴ kV/ms`` (10 V/ns) o gap suporta 2 kV em 0,2 µs, muito
    acima da taxa de subida da TRV desta bancada [CÁLCULO PRÓPRIO].
    """
    out = _run_bench(recovery=ParabolicRecovery(a_kV_per_ms=1.0e4, b_kV_per_ms2=0.0))
    vcb = out["vcb"]
    assert vcb.reignition_count == 0
    assert vcb.state == STATE_OPEN
    assert vcb.result.cleared is True
    # A TRV alcança a plena tensão de restabelecimento (vários kV).
    assert abs(out["probes"]["trv"].peak()) > 2.0e3


def test_reignicao_ocorre_quando_a_suportabilidade_nao_acompanha_a_trv():
    """Suportabilidade lenta ⇒ o gap rompe e o contador incrementa."""
    out = _run_bench(recovery=ParabolicRecovery(a_kV_per_ms=200.0, b_kV_per_ms2=0.0))
    vcb = out["vcb"]
    assert vcb.reignition_count > 0
    assert len(vcb.result.reignition_times_s) == vcb.reignition_count
    assert len(vcb.result.reignition_voltages_V) == vcb.reignition_count
    # Toda reignição ocorre depois do corte e em ordem cronológica.
    assert vcb.chopping_time_s is not None
    assert all(t > vcb.chopping_time_s for t in vcb.result.reignition_times_s)
    assert vcb.result.reignition_times_s == sorted(vcb.result.reignition_times_s)


def test_toda_reignicao_registra_tensao_maior_que_a_suportabilidade_vencida():
    """Invariante do critério: ``|v_gap| > V_wth`` em cada reignição."""
    out = _run_bench(recovery=ParabolicRecovery(a_kV_per_ms=200.0, b_kV_per_ms2=0.0))
    vcb = out["vcb"]
    assert vcb.reignition_count > 0
    for v_gap, v_wth in zip(
        vcb.result.reignition_voltages_V, vcb.result.reignition_withstand_V
    ):
        assert abs(v_gap) > v_wth


def test_contagem_de_reignicoes_e_monotonica_na_reducao_de_a_e_b():
    """Reduzir ``A`` e ``B`` juntos nunca reduz o número de reignições.

    Um gap que endurece mais devagar não pode interromper mais cedo: a
    contagem é monótona NÃO DECRESCENTE ao percorrer fatores de escala
    decrescentes [INFERÊNCIA FÍSICA, verificada aqui].
    """
    base_a, base_b = 2.0e4, 2.0e6
    fatores = (1.0, 0.5, 0.2, 0.05, 0.02, 0.01, 0.005, 0.002)
    contagens = []
    for k in fatores:
        out = _run_bench(
            recovery=ParabolicRecovery(a_kV_per_ms=base_a * k, b_kV_per_ms2=base_b * k)
        )
        contagens.append(out["vcb"].reignition_count)
    assert contagens == sorted(contagens), contagens
    # [CÁLCULO PRÓPRIO nesta bancada: 0 reignições até A = 400 kV/ms e
    # 5 reignições a partir de A = 200 kV/ms — a transição é abrupta,
    # o que é esperado: a primeira reignição decide toda a sequência.]
    assert contagens[0] == 0
    assert contagens[-1] > 0


def test_escalada_de_amplitude_ao_longo_da_sequencia_de_reignicoes():
    """A tensão de reignição cresce ao longo da sequência.

    É o mecanismo de escalada descrito em A: cada extinção do arco de
    alta frequência deixa carga presa na capacitância, de modo que a
    excursão seguinte parte de um patamar maior
    [FATO: doc A, p. 2, II-A; CÁLCULO PRÓPRIO nesta bancada: de 51,3 V a
    662,7 V em 5 reignições com ``A = 200 kV/ms``].
    """
    out = _run_bench(recovery=ParabolicRecovery(a_kV_per_ms=200.0, b_kV_per_ms2=0.0))
    vcb = out["vcb"]
    tensoes = [abs(v) for v in vcb.result.reignition_voltages_V]
    assert len(tensoes) >= 4, tensoes
    assert max(tensoes) > 1.5 * tensoes[0]
    # O pico da segunda metade da sequência supera o da primeira.
    meio = len(tensoes) // 2
    assert max(tensoes[meio:]) > max(tensoes[:meio])


def test_teto_de_reignicoes_trava_o_polo_e_e_declarado_como_salvaguarda():
    """``max_reignitions`` trava em ``cleared`` — resultado numérico, não físico."""
    out = _run_bench(
        recovery=ParabolicRecovery(a_kV_per_ms=200.0, b_kV_per_ms2=0.0),
        max_reignitions=2,
    )
    vcb = out["vcb"]
    assert vcb.reignition_count == 2
    assert vcb.state == STATE_CLEARED
    assert "emt_vcb_constant_didt_capability" in VCB_LIMITATIONS


def test_suportabilidade_instantanea_e_nula_durante_a_conducao():
    """``withstand_V`` vale 0 enquanto há arco — gap em arco não isola."""
    _, switch, _ = _bench()
    vcb = VacuumCircuitBreakerModel(switch, separation_time_s=1.0e-3)
    assert vcb.state == STATE_CLOSED
    assert vcb.withstand_V(5.0e-3) == 0.0


# ===========================================================================
# 5. Convenção de di/dt (ambiguidade declarada do Documento A)
# ===========================================================================


def test_a_convencao_padrao_de_didt_e_a_fisica():
    """O padrão interrompe quando ``|di/dt| <= capacidade`` (Wong, Abdulahovic)."""
    _, switch, _ = _bench()
    vcb = VacuumCircuitBreakerModel(switch, separation_time_s=1.0e-3)
    assert vcb.didt_convention == DIDT_INTERRUPT_WITHIN
    assert "emt_vcb_didt_convention_ambiguous" in VCB_LIMITATIONS


def test_convencao_invertida_de_didt_muda_o_resultado_da_manobra():
    """A convenção do texto de A produz sequência distinta da física.

    A divergência é material — a Etapa 2 §9.2, item 4, registra que o
    sinal do efeito sobre ``n_r`` é indeterminado enquanto a fonte não
    for esclarecida. Este teste apenas certifica que a *flag* muda o
    resultado, não que uma das convenções é a correta.
    """
    rec = ParabolicRecovery(a_kV_per_ms=200.0, b_kV_per_ms2=0.0)
    fisica = _run_bench(recovery=rec, didt_convention=DIDT_INTERRUPT_WITHIN)
    literal = _run_bench(recovery=rec, didt_convention=DIDT_INTERRUPT_ABOVE)
    assert fisica["vcb"].reignition_count != literal["vcb"].reignition_count
    assert abs(fisica["probes"]["trv"].peak()) != pytest.approx(
        abs(literal["probes"]["trv"].peak()), rel=1.0e-6
    )


# ===========================================================================
# 6. Adaptador de compatibilidade com o MODEL legado
# ===========================================================================


def test_adaptador_do_mod_usa_recuperacao_linear_e_os_defaults_do_repositorio():
    """``vcb_from_mod_parameters`` reproduz o bloco ``DATA`` do ``.mod``."""
    _, switch, _ = _bench()
    vcb = vcb_from_mod_parameters(switch)
    assert isinstance(vcb.recovery, LinearRecovery)
    assert vcb.recovery.u0_V == pytest.approx(690.0)
    assert vcb.recovery.k_V_per_us == pytest.approx(17.0)
    assert vcb.separation_time_s == pytest.approx(0.05)
    assert vcb.didt_capability_A_per_us == pytest.approx(16.0)
    assert vcb.chopping_distribution == "normal"
    assert vcb.sampled_chopping_current_A > 0.0
    # O adaptador NÃO adota a convenção invertida do .mod por padrão.
    assert vcb.didt_convention == DIDT_INTERRUPT_WITHIN


def test_adaptador_do_mod_aceita_a_convencao_invertida_por_flag():
    """A convenção do ``.mod`` (reignita acima do crítico) é opcional."""
    _, switch, _ = _bench()
    vcb = vcb_from_mod_parameters(switch, didt_convention=DIDT_INTERRUPT_ABOVE)
    assert vcb.didt_convention == DIDT_INTERRUPT_ABOVE


def test_adaptador_do_mod_roda_a_bancada_sem_quebrar_o_kernel():
    """Os parâmetros legados produzem manobra válida na bancada canônica."""
    ckt, switch, _ = _bench()
    solver = Solver(ckt, dt=2.0e-7, cda_full_steps=2)
    trv = solver.add_probe(DifferentialVoltageProbe("trv", "p", "n1"))
    vcb = vcb_from_mod_parameters(switch, t_open=5.0e-3, seed=3)
    solver.run(t_end=9.0e-3, controllers=[vcb])
    assert vcb.state != STATE_CLOSED
    assert vcb.chopping_time_s is not None
    assert trv.n_samples > 0


# ===========================================================================
# 7. Escalonamento (stagger) e montagem trifásica
# ===========================================================================


def test_stagger_reproduz_a_faixa_de_14_a_25_ms_do_documento_a():
    """Três polos igualmente espaçados em [14; 25] ms ⇒ 14; 19,5; 25 ms."""
    t = stagger_times(3)
    assert t == pytest.approx((14.0e-3, 19.5e-3, 25.0e-3))
    assert t[0] == pytest.approx(DOC_A_STAGGER_RANGE_S[0])
    assert t[-1] == pytest.approx(DOC_A_STAGGER_RANGE_S[1])
    assert stagger_times(1) == pytest.approx((14.0e-3,))
    with pytest.raises(ValueError, match="n_poles"):
        stagger_times(0)


def test_montagem_trifasica_aplica_o_escalonamento_por_polo():
    """``three_phase_vcb`` distribui os instantes e aceita sementes por polo."""
    ckt = Circuit("tri")
    chaves = [ckt.add(Switch(f"cb_{p}", f"a_{p}", f"b_{p}", closed=True)) for p in "abc"]
    polos = three_phase_vcb(chaves, seeds=(1, 2, 3))
    assert [p.separation_time_s for p in polos] == pytest.approx(
        [14.0e-3, 19.5e-3, 25.0e-3]
    )
    assert len({p.sampled_chopping_current_A for p in polos}) == 3
    with pytest.raises(ValueError, match="stagger_s"):
        three_phase_vcb(chaves, stagger_s=(1.0e-3, 2.0e-3))


# ===========================================================================
# 8. Snubber ativo a tiristor
# ===========================================================================


def test_snubber_exige_nivel_de_breakover_explicito():
    """O Documento A não publica o nível: o parâmetro é obrigatório."""
    ckt = Circuit("s")
    sw = ckt.add(Switch("sw", "n1", "mid"))
    r = ckt.add(Resistor("r", "mid", "gnd", 30.0))
    with pytest.raises(TypeError):
        ThyristorSnubber(sw, r)  # type: ignore[call-arg]
    with pytest.raises(ValueError, match="FATO por omissão"):
        ThyristorSnubber(sw, r, breakover_voltage_V=0.0)
    assert "emt_snubber_breakover_not_published" in SNUBBER_LIMITATIONS


def test_snubber_recusa_ramo_mal_formado():
    """Chave e resistor precisam compartilhar o nó intermediário."""
    ckt = Circuit("s")
    sw = ckt.add(Switch("sw", "n1", "mid"))
    r = ckt.add(Resistor("r", "outro", "gnd", 30.0))
    with pytest.raises(ValueError, match="não formam um ramo série|não compartilham nó"):
        ThyristorSnubber(sw, r, breakover_voltage_V=1000.0)


def test_snubber_e_transparente_em_regime_corrente_nula_antes_do_disparo():
    """Item 1 do ciclo de A: ramo aberto, corrente EXATAMENTE nula.

    O nível de disparo (1,5 kV) está acima do pico de regime no nó de
    carga (909,1 V) e abaixo do pico do corte (2191 V), de modo que o
    ramo não conduz um único passo antes da manobra [CÁLCULO PRÓPRIO].
    """
    out = _run_bench(snubber_breakover_V=1.5e3)
    ctrl = out["branch"].controller
    t = out["probes"]["i_snub"].time_s
    i = out["probes"]["i_snub"].values
    t_corte = out["vcb"].chopping_time_s
    assert t_corte is not None
    antes = i[t < t_corte]
    assert antes.size > 1000
    assert float(np.max(np.abs(antes))) == 0.0
    assert ctrl.n_firings >= 1


def test_snubber_dispara_no_nivel_de_breakover_e_registra_a_janela():
    """Disparo por nível local, sem comando digital (item 2 do ciclo de A)."""
    out = _run_bench(snubber_breakover_V=1.5e3)
    ctrl = out["branch"].controller
    assert ctrl.n_firings == 1
    assert ctrl.state == SNUBBER_CONDUCTING
    probe = out["probes"]["i_snub"]
    # No passo anterior ao primeiro passo com corrente não nula, a tensão
    # do ramo já havia ultrapassado o nível de breakover.
    idx = int(np.argmax(np.abs(probe.values) > 0.0))
    v_load = out["probes"]["v_load"].values
    assert abs(float(v_load[idx - 1])) >= 1.5e3


def test_snubber_reduz_o_pico_apos_o_disparo():
    """O ramo amortecedor limita a excursão de tensão (item 3 do ciclo de A).

    [CÁLCULO PRÓPRIO nesta bancada: 2190,9 V sem snubber contra 1521,6 V
    com breakover de 1,5 kV — redução de 30,5 %.]
    """
    sem = _run_bench()
    com = _run_bench(snubber_breakover_V=1.5e3)
    pico_sem = float(np.max(np.abs(sem["probes"]["v_load"].values)))
    pico_com = float(np.max(np.abs(com["probes"]["v_load"].values)))
    assert com["branch"].controller.n_firings >= 1
    assert pico_com < 0.8 * pico_sem
    assert pico_com < 1.10 * 1.5e3  # o pico fica junto ao nível de disparo


def test_snubber_bloqueia_no_zero_de_corrente_do_ramo():
    """Bloqueio natural: a janela fecha em troca de sinal da corrente.

    Nível de disparo abaixo do pico de regime (909,1 V) e disjuntor que
    nunca abre na janela: o ramo conduz a corrente de 60 Hz e bloqueia
    sozinho em cada zero, exercitando o item 4 do ciclo de A isoladamente.
    """
    out = _run_bench(
        snubber_breakover_V=800.0, separation_time_s=50.0e-3, t_end=25.0e-3
    )
    ctrl = out["branch"].controller
    assert ctrl.conduction_windows, "nenhuma janela de condução fechada"
    janela = ctrl.conduction_windows[0]
    assert janela.end_s is not None and janela.end_s > janela.start_s
    probe = out["probes"]["i_snub"]
    k = int(np.argmin(np.abs(probe.time_s - janela.end_s)))
    # No passo do bloqueio a corrente trocou de sinal em relação ao anterior.
    assert probe.values[k] * probe.values[k - 1] <= 0.0


def test_snubber_bloqueia_por_corrente_de_manutencao():
    """Corrente que decai sem cruzar zero bloqueia pelo limiar de manutenção.

    Após a abertura do disjuntor a corrente presa no indutor decai
    exponencialmente por ``R_s`` (``τ = L/R_s = 333 µs``) SEM cruzar
    zero: sem corrente de manutenção a válvula ideal jamais bloquearia
    [CÁLCULO PRÓPRIO].
    """
    sem_ih = _run_bench(snubber_breakover_V=1.5e3)
    com_ih = _run_bench(
        snubber_breakover_V=1.5e3, snubber_kwargs={"holding_current_A": 1.0}
    )
    assert sem_ih["branch"].controller.state == SNUBBER_CONDUCTING
    assert com_ih["branch"].controller.state == SNUBBER_BLOCKED
    assert com_ih["branch"].controller.conduction_windows


def test_energia_dissipada_e_positiva_e_confere_com_a_integral_independente():
    """``E_s = ∫R_s·i² dt`` bate com a integral sobre a série da sonda."""
    out = _run_bench(
        snubber_breakover_V=800.0, separation_time_s=50.0e-3, t_end=25.0e-3
    )
    ctrl = out["branch"].controller
    probe = out["probes"]["i_snub"]
    assert ctrl.energy_J > 0.0
    esperado = _trapz(DOC_A_SNUBBER_RESISTANCE_OHM * probe.values**2, probe.time_s)
    # A diferença residual (≈ 2·10⁻⁵ relativo) é o intervalo do PASSO DO
    # DISPARO, em que a corrente salta de 0 ao valor de condução: o
    # controlador não o integra (a válvula estava bloqueada no início do
    # intervalo) e a integral sobre a série inteira o inclui
    # [CÁLCULO PRÓPRIO].
    assert ctrl.energy_J == pytest.approx(esperado, rel=1.0e-3)
    assert ctrl.energy_J <= esperado
    assert ctrl.result.peak_current_A > 0.0


def test_energia_dissipada_escala_com_o_resistor_de_amortecimento():
    """Com o mesmo disparo, ``R_s`` maior dissipa em corrente menor.

    Verificação de coerência dimensional: a energia é finita e positiva
    nas duas parametrizações, e o pico de corrente cai com ``R_s``
    [CÁLCULO PRÓPRIO].
    """
    a = _run_bench(snubber_breakover_V=1.5e3, snubber_resistance_ohm=30.0)
    b = _run_bench(snubber_breakover_V=1.5e3, snubber_resistance_ohm=120.0)
    pico_30 = a["branch"].controller.result.peak_current_A
    pico_120 = b["branch"].controller.result.peak_current_A
    assert pico_30 > pico_120 > 0.0
    assert a["branch"].controller.energy_J > 0.0
    assert b["branch"].controller.energy_J > 0.0


def test_snubber_rearma_apos_o_bloqueio_e_o_modo_disparo_unico_o_impede():
    """O ciclo de A é rearmável; ``single_shot`` trava após um disparo."""
    rearmavel = _run_bench(
        snubber_breakover_V=800.0, separation_time_s=50.0e-3, t_end=25.0e-3
    )
    unico = _run_bench(
        snubber_breakover_V=800.0, separation_time_s=50.0e-3, t_end=25.0e-3,
        snubber_kwargs={"single_shot": True},
    )
    assert rearmavel["branch"].controller.n_firings >= 2
    assert unico["branch"].controller.n_firings == 1


def test_montagem_trifasica_do_snubber_gera_um_ramo_por_fase():
    """``three_phase_snubber`` replica a célula da Fig. 1 de A."""
    ramos = three_phase_snubber(
        "snub", ("a", "b", "c"), "gnd", breakover_voltage_V=6.0e3
    )
    assert len(ramos) == 3
    assert [r.name for r in ramos] == ["snub_a", "snub_b", "snub_c"]
    for r in ramos:
        assert r.resistor.resistance_ohm == pytest.approx(DOC_A_SNUBBER_RESISTANCE_OHM)
        assert r.switch.closed is False
        assert len(r.components) == 2
    with pytest.raises(ValueError, match="pelo menos um nó"):
        three_phase_snubber("snub", (), "gnd", breakover_voltage_V=6.0e3)


# ===========================================================================
# 9. Caso paramétrico do Documento A
# ===========================================================================


def test_placa_do_motor_reproduz_a_tabela_i_do_documento_a():
    """``I_n = 207,52 A`` e ``I_p = 1348,85 A`` [CÁLCULO PRÓPRIO sobre a Tabela I]."""
    m = MotorParameters()
    assert m.rated_current_A == pytest.approx(207.52, abs=0.01)
    assert m.starting_current_A == pytest.approx(1348.85, abs=0.05)
    assert m.phase_voltage_rms_V == pytest.approx(2401.78, abs=0.01)


def test_as_duas_variantes_do_ramo_rl_diferem_pelo_fator_registrado_na_etapa_2():
    """Fig. 2 drena 3,35 ``I_n``; a Tabela I exige 6,5 ``I_n`` — razão 1,94.

    [FATO: doc A, Tabela I e Fig. 2, p. 3-4; CÁLCULO PRÓPRIO:
    ``|Z|_fig2/|Z|_tabelaI = 3,4550/1,7807 = 1,940`` e a energia magnética
    difere por ``(6,5/3,35)² = 3,77×`` — Etapa 2 §1.3.]
    """
    m = MotorParameters()
    r_fig2, l_fig2 = m.locked_rotor_branch(RL_VARIANT_FIG2)
    r_tab, l_tab = m.locked_rotor_branch(RL_VARIANT_TABLE_I)
    assert (r_fig2, l_fig2) == pytest.approx((0.691, 8.9795e-3))
    assert r_tab == pytest.approx(0.3561, abs=1.0e-4)
    assert l_tab == pytest.approx(4.6278e-3, abs=1.0e-6)
    w = 2.0 * math.pi * m.frequency_Hz
    z_fig2 = math.hypot(r_fig2, w * l_fig2)
    z_tab = math.hypot(r_tab, w * l_tab)
    assert z_fig2 / z_tab == pytest.approx(1.940, abs=5.0e-3)
    # Corrente drenada pela variante da Fig. 2: 3,35 I_n.
    assert (m.phase_voltage_rms_V / z_fig2) / m.rated_current_A == pytest.approx(
        3.35, abs=0.01
    )
    with pytest.raises(ValueError, match="variante"):
        m.locked_rotor_branch("inexistente")


def test_caso_exige_breakover_quando_o_snubber_e_habilitado():
    """Habilitar o snubber sem o nível de disparo é erro declarado."""
    with pytest.raises(ValueError, match="FATO por omissão"):
        SnubberParameters(enabled=True)
    caso = MotorSwitchingCase()
    assert caso.snubber.enabled is False
    com = caso.with_snubber(6.0e3)
    assert com.snubber.enabled is True
    assert com.snubber.breakover_voltage_V == pytest.approx(6.0e3)
    assert com.without_snubber().snubber.enabled is False


def test_caso_monta_o_circuito_completo_com_os_defaults_do_documento_a():
    """A montagem tem as três células, o VCB por polo e o passo de 1 µs."""
    caso = MotorSwitchingCase()
    assert caso.dt_s == pytest.approx(1.0e-6)
    assert caso.t_end_s == pytest.approx(45.0e-3)
    modelo = caso.build()
    assert len(modelo.poles) == 3
    assert modelo.snubbers == ()
    assert [p.separation_time_s for p in modelo.poles] == pytest.approx(
        [14.0e-3, 19.5e-3, 25.0e-3]
    )
    assert set(modelo.trv_probes) == {"a", "b", "c"}
    assert modelo.circuit.dimension > 0
    # Com snubber habilitado surgem três ramos e três controladores a mais.
    com = caso.with_snubber(6.0e3).build()
    assert len(com.snubbers) == 3
    assert len(com.controllers) == len(modelo.controllers) + 3


def test_caso_executa_e_produz_manobra_com_corte_por_polo():
    """Execução ponta a ponta: cada polo corta e o resumo de TRV existe."""
    caso = MotorSwitchingCase(
        vcb=VCBParameters(separation_times_s=(6.0e-3, 7.0e-3, 8.0e-3)),
        t_end_s=16.0e-3,
    )
    modelo = caso.build()
    stats = modelo.run()
    assert stats.steps == 16000
    assert stats.topology_changes > 0
    for polo in modelo.poles:
        assert polo.chopping_time_s is not None
        assert polo.chopping_time_s >= polo.separation_time_s
    resumo = modelo.trv_summary()
    assert set(resumo) == {"a", "b", "c"}
    for pico_kV, rrrv in resumo.values():
        assert math.isfinite(pico_kV)
        assert rrrv >= 0.0
    assert set(modelo.reignition_counts) == {"a", "b", "c"}


def test_caso_com_recuperacao_rapida_interrompe_e_atinge_a_tensao_de_restabelecimento():
    """Gap rápido ⇒ sem reignição e TRV da ordem de 2 pu (6,8 kV).

    A tensão de fase de pico é 3,397 kV; com o polo aberto e o lado da
    carga oscilando, a TRV alcança aproximadamente o dobro
    [LITERATURA: Greenwood, 1991, cap. 5; CÁLCULO PRÓPRIO nesta
    montagem: 6,65 a 7,10 kV].
    """
    caso = MotorSwitchingCase(
        vcb=VCBParameters(
            separation_times_s=(6.0e-3, 7.0e-3, 8.0e-3),
            rrds_a_kV_per_ms=200.0,
            rrds_b_kV_per_ms2=0.0,
        ),
        t_end_s=16.0e-3,
    )
    modelo = caso.build()
    modelo.run()
    assert modelo.reignition_counts == {"a": 0, "b": 0, "c": 0}
    picos = [abs(v[0]) for v in modelo.trv_summary().values()]
    for pico_kV in picos:
        assert 4.0 < pico_kV < 12.0


def test_caso_alimenta_o_nucleo_de_prognostico_com_o_vetor_de_estresse():
    """Integração ponta a ponta: a sonda vira ``StressProfile`` de ``s_{m,j}``.

    A forma de onda da sonda do terminal do motor é entregue a
    ``extract_stress_events`` pelo adaptador
    :func:`app.simulation.emt.probes.to_stress_profile`, produzindo o
    vetor ``s_{m,j} = [V_pk, T1, dv/dt, E, n_r, θ]`` (Etapa 1 §5.4, D7).
    """
    caso = MotorSwitchingCase(
        vcb=VCBParameters(separation_times_s=(6.0e-3, 7.0e-3, 8.0e-3)),
        t_end_s=16.0e-3,
    )
    modelo = caso.build()
    modelo.run()
    perfil = to_stress_profile(
        modelo.motor_probes["b"],
        threshold_kV=2.5,
        surge_impedance_ohm=caso.cable_downstream.surge_impedance_ohm,
        theta_C=90.0,
        label="doc_a_fase_b",
    )
    assert perfil.n_events > 0
    for evento in perfil.events:
        assert abs(evento.V_pk_kV) >= 2.5
        assert evento.T1_us >= 0.0
        assert evento.dvdt_kV_per_us >= 0.0
        assert evento.energy_J >= 0.0
        assert evento.theta_C == pytest.approx(90.0)
        assert evento.n_reignitions >= 1
    assert perfil.sampling_step_s == pytest.approx(caso.dt_s, rel=1.0e-6)


def test_tabela_iii_do_documento_a_esta_disponivel_para_confronto():
    """Os seis pares pico/RRRV da Tabela III são expostos como referência."""
    assert set(DOC_A_TABLE_III) == {"sem_snubber", "com_snubber"}
    assert DOC_A_TABLE_III["sem_snubber"]["b"] == (41.44, 15.05)
    assert DOC_A_TABLE_III["com_snubber"]["b"] == (13.65, 13.11)
    assert DOC_A_TABLE_III["sem_snubber"]["c"] == (-38.30, 19.00)
    # Redução de pico da fase B declarada por A: cerca de 67 %.
    pico_sem = abs(DOC_A_TABLE_III["sem_snubber"]["b"][0])
    pico_com = abs(DOC_A_TABLE_III["com_snubber"]["b"][0])
    assert 1.0 - pico_com / pico_sem == pytest.approx(0.67, abs=0.01)


def test_parametros_do_caso_validam_entradas_fisicas():
    """Dataclasses de parâmetro rejeitam valores sem sentido físico."""
    with pytest.raises(ValueError, match="line_voltage_V"):
        SourceParameters(line_voltage_V=0.0)
    with pytest.raises(ValueError, match="sequence"):
        SourceParameters(sequence="cba")
    with pytest.raises(ValueError, match="rating_MVA"):
        TransformerParameters(rating_MVA=0.0)
    with pytest.raises(ValueError, match="length_m"):
        CableParameters(length_m=0.0)
    with pytest.raises(ValueError, match="efficiency"):
        MotorParameters(efficiency=0.0)
    with pytest.raises(ValueError, match="rl_variant"):
        MotorSwitchingCase(rl_variant="outra")
    with pytest.raises(ValueError, match="dt_s"):
        MotorSwitchingCase(dt_s=0.0)


def test_impedancia_de_surto_e_tempo_de_transito_do_cabo():
    """``Z_c = 37,42 Ω`` e ``v = 1,07·10⁸ m/s`` com os padrões [CÁLCULO PRÓPRIO]."""
    cabo = CableParameters()
    assert cabo.surge_impedance_ohm == pytest.approx(37.42, abs=0.01)
    assert cabo.travel_time_s == pytest.approx(4.677e-6, rel=1.0e-3)
    # A faixa de 30 a 80 Ω reportada na Etapa 1 §2.3 para cabos de MT.
    assert 30.0 <= cabo.surge_impedance_ohm <= 80.0
    # O tempo de trânsito do cabo a jusante supera o passo de 1 µs de A.
    assert CableParameters(length_m=200.0).travel_time_s > 1.0e-6


def test_impedancia_de_dispersao_do_transformador():
    """``|Z| = 8 %`` na base de 7,5 MVA a 4,16 kV ⇒ 0,1846 Ω [CÁLCULO PRÓPRIO]."""
    tx = TransformerParameters()
    r, indutancia = tx.series_rl(4160.0, 60.0)
    x = 2.0 * math.pi * 60.0 * indutancia
    assert math.hypot(r, x) == pytest.approx(0.18459, rel=1.0e-4)
    assert x / r == pytest.approx(10.0, rel=1.0e-9)


def test_ponto_da_onda_e_parametro_declarado_do_monte_carlo():
    """``phase_deg`` desloca a manobra na onda e muda a manobra resultante."""
    base = MotorSwitchingCase(
        vcb=VCBParameters(separation_times_s=(6.0e-3, 7.0e-3, 8.0e-3)),
        t_end_s=12.0e-3,
    )
    tempos = []
    for angulo in (0.0, 90.0):
        modelo = base.with_phase_deg(angulo).build()
        modelo.run()
        tempos.append(modelo.poles[0].chopping_time_s)
    assert tempos[0] != tempos[1]


# ===========================================================================
# 10. Auditoria — limitações declaradas
# ===========================================================================


# ===========================================================================
# 8. Modo de compatibilidade LITERAL com o arquivo ATP
# ===========================================================================
#
# Um teste por item da lógica escrita no arquivo. A referência destes
# testes NÃO é a física idealizada do disjuntor a vácuo: é o texto do
# MODEL ``VCB_R*`` e do MODEL ``SNUB_CTRL``
# [REPO: tests/fixtures/atp/trt_all_motors_dt_ea.atp:110-199 e
# tests/fixtures/atp/trt_all_motors_com_snubber_2026-04.atp:532-581].


#: Parâmetros de bancada do modo literal: separação em 1 ms para caber na
#: janela curta dos testes, o resto com os valores do arquivo.
def _par_literal(**overrides) -> AtpVcbParameters:
    base = {"t_open_s": 1.0e-3}
    base.update(overrides)
    return AtpVcbParameters(**base)


def _polo_literal(**kwargs):
    """Polo literal solto (não ligado a circuito), acionado por ``step``."""
    par = kwargs.pop("parameters", _par_literal())
    kwargs.setdefault("zero_crossing_order", ATP_ZERO_ORDER_DEFERRED)
    return build_atp_literal_pole("cb", "p", "n1", parameters=par, **kwargs)


def _rlc(ctrl) -> tuple[float, float, float]:
    return (ctrl.r_val, ctrl.l_val, ctrl.c_val)


def test_literal_reproduz_as_quatro_transicoes_e_as_atribuicoes_de_rlc():
    """Item 1: quatro estados, mesmas transições, mesmas atribuições R-L-C.

    Percorre a sequência fechado → arco → aberto → arco de alta
    frequência → aberto conferindo, em cada passo, o código de estado do
    ARQUIVO (0, 1, 2, 3 — que não é a ordem de ``VCB_STATES``) e a terna
    ``(R_VAL, L_VAL, C_VAL)`` que o MODEL atribui naquela transição.
    """
    polo = _polo_literal()
    c = polo.controller
    fechado = (ATP_R_CLOSED_OHM, ATP_L_CLOSED_H, ATP_C_CLOSED_F)
    arco = (ATP_R_ARC_OHM, ATP_L_ARC_H, ATP_C_ARC_F)
    aberto = (ATP_R_OPEN_OHM, ATP_L_OPEN_H, ATP_C_OPEN_F)

    # INIT: fechado, chave conduzindo, ramo série com os valores de fechado.
    assert c.state == ATP_CB_CLOSED and c.sw_state == 1.0
    assert _rlc(c) == fechado

    # Antes de T_OPEN nada muda.
    c.step(v_cb=0.0, i_cb=100.0, tnow=0.5e-3)
    assert c.state == ATP_CB_CLOSED and _rlc(c) == fechado

    # TNOW >= T_OPEN: 0 → 1, a chave ideal abre e o ramo assume o arco.
    c.step(v_cb=0.0, i_cb=100.0, tnow=1.0e-3)
    assert c.state == ATP_CB_ARCING
    assert c.sw_state == 0.0
    assert _rlc(c) == arco

    # |I_CB| <= I_CHOP com CHOPPED = 0: 1 → 2, ramo assume o aberto.
    c.step(v_cb=0.0, i_cb=0.5, tnow=1.001e-3)
    assert c.state == ATP_CB_OPEN and _rlc(c) == aberto
    assert c.chopped == 1
    assert c.result.chopping_time_s == pytest.approx(1.001e-3)

    # Passagem por zero: arma o temporizador da recuperação.
    c.step(v_cb=0.0, i_cb=-0.5, tnow=1.002e-3)
    assert c.state == ATP_CB_OPEN
    assert c.t_zero == pytest.approx(1.002e-3)

    # TRV acima da suportabilidade: 2 → 3, ramo volta ao arco.
    c.step(v_cb=2.0e3, i_cb=-0.5, tnow=1.102e-3)
    assert c.state == ATP_CB_ARCING_HF and _rlc(c) == arco
    assert c.result.reignition_count == 1

    # Extinção de alta frequência: 3 → 2, ramo volta ao aberto.
    c.step(v_cb=0.0, i_cb=-10.0, tnow=1.103e-3)
    assert c.state == ATP_CB_ARCING_HF
    c.step(v_cb=0.0, i_cb=0.05, tnow=1.104e-3)
    assert c.state == ATP_CB_OPEN and _rlc(c) == aberto
    assert c.chopped == 0

    # A trilha de estados percorreu os quatro códigos do arquivo.
    assert [s for _, s in c.result.state_changes] == [
        ATP_CB_ARCING,
        ATP_CB_OPEN,
        ATP_CB_ARCING_HF,
        ATP_CB_OPEN,
    ]
    assert c.outputs["CB_STATE"] == float(ATP_CB_OPEN)
    assert c.outputs["SW_STATE"] == 0.0


def test_literal_aplica_a_margem_de_dez_por_cento_no_criterio_de_reignicao():
    """Item 2: reignita com ``|V_CB| > V_wth·1,1``, e não com ``> V_wth``.

    Dois polos idênticos são levados ao estado aberto e submetidos, no
    MESMO instante desde o zero de corrente, a duas tensões: uma 5 % acima
    da suportabilidade (que reignitaria sem a margem) e outra 15 % acima.
    Só a segunda reignita.
    """

    def _ate_aberto_com_zero(polo):
        c = polo.controller
        c.step(v_cb=0.0, i_cb=100.0, tnow=1.0e-3)
        c.step(v_cb=0.0, i_cb=0.5, tnow=1.001e-3)
        c.step(v_cb=0.0, i_cb=-0.5, tnow=1.002e-3)
        assert c.state == ATP_CB_OPEN and c.t_zero >= 0.0
        return c

    # V_wth em 0,1 ms após o zero: A·0,1 + B·0,01 = 92,36 V [CÁLCULO PRÓPRIO].
    v_wth = (ATP_RRDS_A_KV_PER_MS * 0.1 + ATP_RRDS_B_KV_PER_MS2 * 0.01) * 1.0e3
    assert v_wth == pytest.approx(92.36, rel=1e-6)

    baixo = _ate_aberto_com_zero(_polo_literal())
    baixo.step(v_cb=1.05 * v_wth, i_cb=-0.5, tnow=1.102e-3)
    assert baixo.withstand_V() == pytest.approx(v_wth, rel=1e-9)
    assert baixo.state == ATP_CB_OPEN, "reignitou dentro da margem de 10 %"
    assert baixo.result.reignition_count == 0

    alto = _ate_aberto_com_zero(_polo_literal())
    alto.step(v_cb=1.15 * v_wth, i_cb=-0.5, tnow=1.102e-3)
    assert alto.state == ATP_CB_ARCING_HF
    assert alto.result.reignition_count == 1
    assert alto.result.reignition_withstand_V[0] == pytest.approx(v_wth, rel=1e-9)
    # O fator do arquivo é exatamente 1,1 e está parametrizado.
    assert alto.parameters.reignition_margin == pytest.approx(ATP_REIGNITION_MARGIN)
    assert ATP_REIGNITION_MARGIN == 1.1


def test_literal_extingue_alta_frequencia_acima_do_didt_critico_e_declara_a_inversao():
    """Item 3: ``|di/dt| > crítico`` extingue — convenção INVERTIDA.

    A física usual é a oposta: o arco de alta frequência se extingue
    quando a taxa de variação da corrente no zero é PEQUENA o bastante
    para a câmara acompanhar. O arquivo escreve o contrário, e o modo
    literal publica isso como saída (``DIDT_INVERTED``) em vez de
    corrigir em silêncio.

    O contador ``hf_extinction_count`` conta SÓ as extinções atribuídas
    ao critério de di/dt. Com a taxa acima do crítico ele incrementa; com
    a taxa abaixo do crítico o polo ainda assim abre, mas pela SEGUNDA
    condição — o que mostra, de quebra, que o critério de di/dt é
    redundante no arquivo (ver o teste do item 5).
    """

    def _ate_arco_af(polo):
        c = polo.controller
        c.step(v_cb=0.0, i_cb=100.0, tnow=1.0e-3)
        c.step(v_cb=0.0, i_cb=0.5, tnow=1.001e-3)
        c.step(v_cb=0.0, i_cb=-0.5, tnow=1.002e-3)
        c.step(v_cb=2.0e3, i_cb=-0.5, tnow=1.102e-3)
        assert c.state == ATP_CB_ARCING_HF
        return c

    # A saída adicional existe e é a do arquivo.
    polo = _polo_literal()
    assert polo.controller.didt_convention == DIDT_INTERRUPT_ABOVE
    assert polo.controller.didt_convention_inverted is True
    assert polo.controller.outputs["DIDT_INVERTED"] is True
    assert polo.controller.result.didt_convention_inverted is True
    assert polo.controller.result.didt_convention == DIDT_INTERRUPT_ABOVE

    # ACIMA do crítico (Δi = 10,05 A em 1 µs ⇒ 10,05 A/µs > 5 A/µs).
    acima = _ate_arco_af(_polo_literal())
    acima.step(v_cb=0.0, i_cb=-10.0, tnow=1.103e-3)
    assert acima.state == ATP_CB_ARCING_HF, "não extingue com |I| acima de 0,1 A"
    acima.step(v_cb=0.0, i_cb=0.05, tnow=1.104e-3)
    assert abs(acima.di_dt) > acima.parameters.didt_crit_A_per_us * 1.0e6
    assert acima.state == ATP_CB_OPEN
    assert acima.result.hf_extinction_count == 1

    # ABAIXO do crítico (Δi = 0,55 A em 1 µs ⇒ 0,55 A/µs < 5 A/µs): o
    # critério de di/dt NÃO atua; a abertura vem da segunda condição.
    abaixo = _ate_arco_af(_polo_literal())
    abaixo.step(v_cb=0.0, i_cb=0.05, tnow=1.103e-3)
    assert abs(abaixo.di_dt) < abaixo.parameters.didt_crit_A_per_us * 1.0e6
    assert abaixo.state == ATP_CB_OPEN
    assert abaixo.result.hf_extinction_count == 0


def test_literal_reinicia_o_temporizador_a_cada_zero_com_limiar_de_dez_miliamperes():
    """Item 4: ``T_ZERO := TNOW`` a cada zero de corrente, se ``|I| > 0,01 A``.

    Duas propriedades do arquivo, ambas diferentes de um modelo usual de
    disjuntor:

    1. o temporizador da recuperação dielétrica parte do último ZERO DE
       CORRENTE, e não do instante de extinção do arco;
    2. a passagem por zero só é VALIDADA se a corrente que a antecede
       exceder 0,01 A em módulo — cruzamentos dentro do ruído numérico
       são ignorados.
    """
    polo = _polo_literal()
    c = polo.controller
    c.step(v_cb=0.0, i_cb=100.0, tnow=1.0e-3)
    c.step(v_cb=0.0, i_cb=0.5, tnow=1.001e-3)
    assert c.state == ATP_CB_OPEN and c.t_zero == -1.0

    # Cruzamento com corrente ABAIXO do limiar: não conta.
    c.step(v_cb=0.0, i_cb=0.005, tnow=1.002e-3)
    c.step(v_cb=0.0, i_cb=-0.005, tnow=1.003e-3)
    assert c.t_zero == -1.0
    assert c.result.zero_crossing_times_s == []
    assert c.withstand_V() == 0.0

    # Cruzamento com corrente ACIMA do limiar: arma o temporizador.
    c.step(v_cb=0.0, i_cb=0.02, tnow=1.004e-3)
    c.step(v_cb=0.0, i_cb=-0.02, tnow=1.005e-3)
    assert c.t_zero == pytest.approx(1.005e-3)
    assert c.result.zero_crossing_times_s == [pytest.approx(1.005e-3)]

    # A suportabilidade cresce a partir DESSE zero.
    c.step(v_cb=0.0, i_cb=-0.02, tnow=1.105e-3)
    v_primeiro = c.withstand_V()
    assert v_primeiro == pytest.approx(92.36, rel=1e-6)

    # NOVA passagem por zero, sem qualquer extinção pelo meio: o
    # temporizador REINICIA e a suportabilidade volta a zero.
    c.step(v_cb=0.0, i_cb=0.02, tnow=1.106e-3)
    assert c.t_zero == pytest.approx(1.106e-3)
    assert c.t_azero == pytest.approx(0.0)
    assert c.withstand_V() == pytest.approx(0.0)
    assert len(c.result.zero_crossing_times_s) == 2
    assert c.parameters.zero_crossing_threshold_A == pytest.approx(0.01)


def test_literal_segunda_condicao_de_extincao_abaixo_de_cem_miliamperes():
    """Item 5: ``|I_CB| < 0,1 A E T_ZERO >= 0`` também extingue, e zera CHOPPED.

    A condição existe nos estados 1 e 3 e é INDEPENDENTE de ``I_CHOP``:
    ela abre o polo por corrente pequena depois que houve pelo menos uma
    passagem por zero, e repõe ``CHOPPED`` em 0, rearmando o corte por
    ``I_CHOP``.

    Verifica-se também a consequência estrutural: no estado 3 essa
    condição SUBSUME o critério de di/dt (as duas usam o mesmo limiar de
    0,1 A e, para se chegar ao estado 3, ``T_ZERO`` já é não negativo),
    de modo que ``DIDT_CRIT`` não altera o instante de extinção.
    """
    # Corte por I_CHOP no estado 1 e, depois, extinção pela segunda
    # condição — que devolve CHOPPED a zero.
    polo = _polo_literal(parameters=_par_literal(i_chop_A=1.0))
    c = polo.controller
    c.step(v_cb=0.0, i_cb=100.0, tnow=1.0e-3)
    c.step(v_cb=0.0, i_cb=0.5, tnow=1.001e-3)
    assert c.state == ATP_CB_OPEN and c.chopped == 1
    c.step(v_cb=0.0, i_cb=-0.5, tnow=1.002e-3)
    c.step(v_cb=2.0e3, i_cb=-0.5, tnow=1.102e-3)
    assert c.state == ATP_CB_ARCING_HF
    # Corrente pequena com T_ZERO já armado: extingue e rearma o corte.
    c.step(v_cb=0.0, i_cb=0.05, tnow=1.103e-3)
    assert c.state == ATP_CB_OPEN
    assert c.chopped == 0
    assert c.parameters.extinction_current_A == pytest.approx(0.1)
    assert c.result.hf_extinction_count == 0

    # 0,1 A é limiar ESTRITO: em 0,1 A exatos a condição não atende.
    borda = _polo_literal()
    cb = borda.controller
    cb.step(v_cb=0.0, i_cb=100.0, tnow=1.0e-3)
    cb.step(v_cb=0.0, i_cb=0.5, tnow=1.001e-3)
    cb.step(v_cb=0.0, i_cb=-0.5, tnow=1.002e-3)
    cb.step(v_cb=2.0e3, i_cb=-0.5, tnow=1.102e-3)
    cb.step(v_cb=0.0, i_cb=0.1, tnow=1.103e-3)
    assert cb.state == ATP_CB_ARCING_HF

    # Redundância: mudar DIDT_CRIT em quatro ordens de grandeza não move
    # o instante de extinção do arco de alta frequência.
    instantes = []
    for didt in (5.0, 5.0e4):
        p = _polo_literal(parameters=_par_literal(didt_crit_A_per_us=didt))
        cc = p.controller
        cc.step(v_cb=0.0, i_cb=100.0, tnow=1.0e-3)
        cc.step(v_cb=0.0, i_cb=0.5, tnow=1.001e-3)
        cc.step(v_cb=0.0, i_cb=-0.5, tnow=1.002e-3)
        cc.step(v_cb=2.0e3, i_cb=-0.5, tnow=1.102e-3)
        cc.step(v_cb=0.0, i_cb=-10.0, tnow=1.103e-3)
        cc.step(v_cb=0.0, i_cb=0.05, tnow=1.104e-3)
        assert cc.state == ATP_CB_OPEN
        instantes.append(cc.result.extinction_times_s[-1])
    assert instantes[0] == pytest.approx(instantes[1])


def test_literal_monta_ramo_rlc_serie_comutado_em_paralelo_com_a_chave_ideal():
    """Item 6: o polo é chave ideal ‖ (C série L série R), não chave isolada.

    Confere a topologia montada, a comutação efetiva dos três valores ao
    longo da manobra e — o que distingue o modo literal de uma chave
    ideal — que o polo CONTINUA conduzindo depois de a chave abrir,
    pelos 6 µF do estado aberto.
    """
    polo = build_atp_literal_pole(
        "cb", "p", "n1", parameters=_par_literal(),
        zero_crossing_order=ATP_ZERO_ORDER_DEFERRED,
    )
    # Quatro componentes: a chave e os três elementos do ramo série.
    assert len(polo.components) == 4
    assert isinstance(polo.resistor, SwitchedResistor)
    assert isinstance(polo.inductor, SwitchedInductor)
    assert isinstance(polo.capacitor, SwitchedCapacitor)
    # Ramo série contíguo entre os MESMOS nós da chave.
    assert polo.switch.nodes == ("p", "n1")
    assert polo.capacitor.nodes[0] == "p"
    assert polo.capacitor.nodes[1] == polo.inductor.nodes[0]
    assert polo.inductor.nodes[1] == polo.resistor.nodes[0]
    assert polo.resistor.nodes[1] == "n1"

    ckt = Circuit("bancada_literal")
    ckt.add(
        VoltageSource(
            "E", "src", "gnd",
            amplitude_V=SOURCE_AMPLITUDE_V, frequency_Hz=60.0, phase_deg=90.0,
        )
    )
    ckt.add(Inductor("Ls", "src", "p", L_SOURCE_H))
    ckt.extend(polo.components)
    ckt.add(Inductor("L", "n1", "gnd", L_LOAD_H))
    ckt.add(Capacitor("C", "n1", "gnd", C_LOAD_F, initial_voltage_V=C_INITIAL_V))
    solver = Solver(ckt, dt=1.0e-6)
    i_ramo = solver.add_probe(BranchCurrentProbe("i_ramo", polo.resistor))
    i_chave = solver.add_probe(BranchCurrentProbe("i_chave", polo.switch))
    trv = solver.add_probe(DifferentialVoltageProbe("trv", "p", "n1"))
    solver.run(t_end=12.0e-3, controllers=[polo.controller])
    # Semântica tipo 13: a chave só abre no zero de corrente seguinte ao
    # comando (t_open = 1 ms); observa-se o pólo a partir desse instante.
    t_abre = polo.controller.result.switch_opening_time_s
    assert t_abre is not None and t_abre >= 1.0e-3

    c = polo.controller
    # A manobra ocorreu e os valores comutaram para os de aberto.
    assert c.sw_state == 0.0 and not polo.switch.closed
    assert polo.resistor.resistance_ohm == pytest.approx(ATP_R_OPEN_OHM)
    assert polo.inductor.inductance_H == pytest.approx(ATP_L_OPEN_H)
    assert polo.capacitor.capacitance_F == pytest.approx(ATP_C_OPEN_F)

    # A comutação dos valores é vista pelo solver como mudança de
    # topologia: refatora e dispara o CDA, como faz uma chave.
    assert solver.stats.topology_changes >= 2

    # Depois de a chave abrir a corrente do POLO não é nula: ela passa
    # pelo ramo série. Uma chave ideal isolada daria ZERO — é essa a
    # diferença que o item 6 exige. No estado aberto quem governa é o
    # 1 MΩ em série: a 6 µF vale 26,5 Ω em 1 kHz e a 0,6 µH vale 3,8 mΩ,
    # ambas desprezíveis ao lado dele [CÁLCULO PRÓPRIO], de modo que a
    # corrente do ramo é a tensão do gap dividida por ROPEN.
    t = np.asarray(i_ramo.time_s)
    depois = t > t_abre + 0.5e-3
    i_depois = np.asarray(i_ramo.values)[depois]
    v_depois = np.asarray(i_chave.values)[depois]
    assert float(np.max(np.abs(i_depois))) > 1.0e-3
    assert float(np.max(np.abs(v_depois))) < 1.0e-9
    k = int(np.argmax(np.abs(i_depois)))
    v_gap_pico = float(np.max(np.abs(np.asarray(trv.values)[depois])))
    assert abs(i_depois[k]) == pytest.approx(v_gap_pico / ATP_R_OPEN_OHM, rel=0.05)

    # É por isso que a leitura de I_CB importa: as duas fontes divergem.
    assert c.current_source == ATP_CURRENT_FROM_SWITCH
    assert c.measured_current_A() == pytest.approx(polo.switch.branch_current(0))
    c.current_source = ATP_CURRENT_FROM_POLE
    assert abs(c.measured_current_A()) > abs(polo.switch.branch_current(0))


def test_ordem_literal_de_iprev_impede_qualquer_passagem_por_zero():
    """O arquivo sobrescreve ``I_PREV`` ANTES do teste de zero — e isso paralisa.

    No arquivo, ``I_PREV := I_CBr`` está dentro do bloco
    ``IF TNOW > TIME_PREVr``, que é verdadeiro em todo passo e precede o
    teste ``IF I_PREV * I_CBr <= 0.0``. O teste passa a comparar a
    corrente com ela mesma: o produto é ``I_CB²``, nunca negativo, e o
    caso em que se anula reprova a guarda ``ABS(I_PREV) > 0,01``.

    Consequência EXECUTADA pelo arquivo: ``T_ZERO`` fica em −1,0,
    ``V_WITH`` fica em zero e não há reignição nenhuma. O modo literal
    reproduz isso por padrão; a ordem adiada é opção declarada.
    """
    literal = build_atp_literal_pole(
        "cb_lit", "p", "n1", parameters=_par_literal(),
        zero_crossing_order=ATP_ZERO_ORDER_LITERAL,
    )
    adiado = build_atp_literal_pole(
        "cb_adi", "p", "n1", parameters=_par_literal(),
        zero_crossing_order=ATP_ZERO_ORDER_DEFERRED,
    )
    sequencia = [
        (1.0e-3, 100.0, 0.0),
        (1.001e-3, 0.5, 0.0),
        (1.002e-3, -0.5, 0.0),
        (1.102e-3, -0.5, 5.0e3),
    ]
    for polo in (literal, adiado):
        for tnow, i, v in sequencia:
            polo.controller.step(v_cb=v, i_cb=i, tnow=tnow)

    assert literal.controller.zero_crossing_order == ATP_ZERO_ORDER_LITERAL
    assert literal.controller.t_zero == -1.0
    assert literal.controller.withstand_V() == 0.0
    assert literal.controller.result.reignition_count == 0
    assert literal.controller.state == ATP_CB_OPEN

    assert adiado.controller.t_zero == pytest.approx(1.002e-3)
    assert adiado.controller.result.reignition_count == 1
    assert adiado.controller.state == ATP_CB_ARCING_HF


def test_modo_literal_e_selecionado_por_parametro_e_nao_muda_o_padrao():
    """``build_vcb_pole`` escolhe o modo; o padrão continua a chave ideal."""
    padrao = build_vcb_pole(
        "cb", "p", "n1", separation_time_s=1.0e-3, chopping_current_A=2.0
    )
    assert isinstance(padrao, VcbPole)
    assert isinstance(padrao.controller, VacuumCircuitBreakerModel)
    assert padrao.components == (padrao.switch,)
    assert padrao.controller.didt_convention == DIDT_INTERRUPT_WITHIN
    assert padrao.switch.closed

    literal = build_vcb_pole(
        "cb2", "p", "n1", atp_model_compatibility=True, parameters=_par_literal()
    )
    assert isinstance(literal, AtpLiteralPole)
    assert isinstance(literal.controller, AtpModelCompatibility)
    assert len(literal.components) == 4

    # ``parameters`` é do modo literal e não é aceito em silêncio no padrão.
    with pytest.raises(ValueError, match="modo literal"):
        build_vcb_pole("cb3", "p", "n1", parameters=_par_literal(), separation_time_s=1e-3)


def test_parametros_literais_reproduzem_os_blocos_use_do_arquivo():
    """Os três polos do arquivo diferem em T_OPEN, I_CHOP e DIDT_CRIT."""
    polos = [AtpVcbParameters.for_pole(k) for k in range(3)]
    assert tuple(p.t_open_s for p in polos) == ATP_T_OPEN_S
    assert tuple(p.i_chop_A for p in polos) == ATP_I_CHOP_A
    assert tuple(p.didt_crit_A_per_us for p in polos) == ATP_DIDT_CRIT_A_PER_US
    # O resto é comum aos três.
    assert {p.rrds_a_kV_per_ms for p in polos} == {ATP_RRDS_A_KV_PER_MS}
    assert {p.r_arc_ohm for p in polos} == {ATP_R_ARC_OHM}
    assert {p.c_open_F for p in polos} == {ATP_C_OPEN_F}
    with pytest.raises(ValueError, match="index"):
        AtpVcbParameters.for_pole(3)
    with pytest.raises(ValueError, match="r_arc_ohm"):
        AtpVcbParameters(r_arc_ohm=0.0)

    trifasico = three_phase_atp_literal_poles(
        "cb", ("pa", "pb", "pc"), ("na", "nb", "nc")
    )
    assert len(trifasico) == 3
    assert [p.controller.parameters.t_open_s for p in trifasico] == list(ATP_T_OPEN_S)


def test_elementos_comutaveis_publicam_o_valor_na_assinatura_de_topologia():
    """Mudar R, L ou C é mudança de TOPOLOGIA — obriga refatoração e CDA."""
    r = SwitchedResistor("r", "a", "b", 20.0)
    l = SwitchedInductor("l", "b", "c", 50.0e-6)
    c = SwitchedCapacitor("c", "c", "gnd", 0.0)
    assert r.topology_signature() == ("R", 20.0)
    assert l.topology_signature() == ("L", 50.0e-6)
    assert c.topology_signature() == ("C", 0.0)
    assert r.set_resistance(1.0e6) and not r.set_resistance(1.0e6)
    assert r.topology_signature() == ("R", 1.0e6)
    # C = 0 é o valor de CCLOSED no arquivo: ramo série ABERTO.
    assert c.capacitance_F == 0.0
    assert c.set_capacitance(6.0e-6)
    with pytest.raises(ValueError, match="capacitance_F"):
        c.set_capacitance(-1.0)
    with pytest.raises(ValueError, match="resistance_ohm"):
        r.set_resistance(0.0)
    with pytest.raises(ValueError, match="inductance_H"):
        l.set_inductance(0.0)


def test_controlador_mestre_literal_arma_no_estado_dois_e_nunca_libera():
    """``SNUB_CTRL``: trava comum às três fases, sem liberação.

    O limiar do arquivo é ``STA > 1.9``: nos códigos do MODEL do
    disjuntor a trava NÃO fecha no estado de arco (1), fecha no estado
    aberto (2) — a primeira interrupção declarada — ou no de arco de alta
    frequência (3).
    """

    class _PoloATP:
        def __init__(self) -> None:
            self.cb_state = ATP_CB_CLOSED

    a, b, c = _PoloATP(), _PoloATP(), _PoloATP()
    disparos: list[float] = []
    mestre = SnubberMasterTrigger([a, b, c], [lambda t, solver: disparos.append(t)])
    assert mestre.latch_threshold == pytest.approx(ATP_SNUBBER_LATCH_THRESHOLD)

    mestre(1.0e-3, None)
    assert not mestre.armed and mestre.fm == 0.0

    # Estado de arco (1) NÃO arma: 1 não é maior que 1,9.
    b.cb_state = ATP_CB_ARCING
    mestre(2.0e-3, None)
    assert not mestre.armed

    # Estado aberto (2) arma, e arma pelas TRÊS fases de uma vez.
    b.cb_state = ATP_CB_OPEN
    mestre(3.0e-3, None)
    assert mestre.armed and mestre.fm == 1.0
    assert mestre.armed_time_s == pytest.approx(3.0e-3)
    assert set(mestre.gates) == set(ATP_SNUBBER_GATE_NAMES)
    assert all(v == 1.0 for v in mestre.gates.values())

    # Volta ao estado fechado: a trava NÃO é liberada.
    b.cb_state = ATP_CB_CLOSED
    mestre(4.0e-3, None)
    assert mestre.armed and mestre.gate() is True
    assert disparos == [1.0e-3, 2.0e-3, 3.0e-3, 4.0e-3]

    mestre.reset()
    assert not mestre.armed and mestre.armed_time_s is None

    # O mesmo limiar lê os polos do modo PADRÃO, por tradução de nome.
    assert atp_state_code(_PoloATP()) == 0.0
    padrao = build_vcb_pole("cbp", "p", "n1", separation_time_s=1.0e-3)
    assert atp_state_code(padrao.controller) == 0.0
    with pytest.raises(ValueError, match="cb_state"):
        atp_state_code(object())


def test_valvula_literal_so_dispara_depois_da_porta_do_controlador_mestre():
    """A porta inibe o disparo; a tensão de disparo sozinha não basta."""
    porta = {"on": False}
    ckt = Circuit("porta_da_valvula")
    ckt.add(
        VoltageSource(
            "E", "bus", "gnd", amplitude_V=3386.0, frequency_Hz=60.0, phase_deg=0.0
        )
    )
    branch = build_atp_literal_snubber_branch(
        "sn", "bus", "gnd", gate=lambda: porta["on"]
    )
    ckt.extend(branch.components)
    assert branch.controller.breakover_voltage_V == pytest.approx(ATP_SNUBBER_BREAKOVER_V)
    assert branch.controller.holding_current_A == pytest.approx(
        ATP_SNUBBER_HOLDING_CURRENT_A
    )
    assert branch.resistor.resistance_ohm == pytest.approx(ATP_SNUBBER_RESISTANCE_OHM)
    assert branch.controller.deionization_time_s == pytest.approx(
        ATP_SNUBBER_DEIONIZATION_TIME_S
    )

    solver = Solver(ckt, dt=1.0e-6)
    solver.run(t_end=8.0e-3, controllers=[branch.controller])
    assert branch.controller.n_firings == 0, "disparou sem a porta"
    assert branch.controller.state == SNUBBER_BLOCKED

    porta["on"] = True
    solver.run(t_end=8.0e-3, controllers=[branch.controller])
    assert branch.controller.n_firings >= 1
    assert branch.controller.energy_J > 0.0


def test_valvula_literal_de_2404_V_conduz_em_regime_e_carrega_os_30_ohms():
    """Consequência do item do amortecedor: 2404 V de disparo, 3386 V de pico.

    Com a trava do ``SNUB_CTRL`` fechada, a válvula dispara em todo
    semiciclo em que a tensão do barramento excede 2404 V e só bloqueia
    quando a corrente cai à corrente de manutenção de 1 A, isto é,
    praticamente no zero de tensão. O ramo deixa de ser um amortecedor de
    transitório e passa a ser uma CARGA PERMANENTE.

    Medida desta bancada, com fonte ideal de 3386 V de pico a 60 Hz sobre
    o resistor de 30 Ω, dois ciclos após o armamento
    [CÁLCULO PRÓPRIO, medido nesta sessão]::

        disparos por período .......... 2
        corrente de pico .............. 112,87 A
        corrente eficaz ............... 74,96 A
        potência média ................ 168,6 kW por fase
        energia em 34,3 ms ............ 5,78 kJ por fase
        fração do tempo em condução ... 72,5 %

    O valor analítico da potência, integrando ``v²/R`` do ângulo de
    disparo ``asin(2404/3386) = 45,2°`` ao zero de tensão, é 173,5 kW
    [CÁLCULO PRÓPRIO]; a diferença de 3 % é o trecho final, em que a
    válvula bloqueia em ``|i| = 1 A`` (isto é, ``|v| = 30 V``) e não em
    zero, mais a janela parcial do primeiro semiciclo.
    """

    class _PoloATP:
        def __init__(self) -> None:
            self.cb_state = ATP_CB_CLOSED

    pico_V = 3386.0
    polo = _PoloATP()
    mestre = SnubberMasterTrigger([polo], ())
    ckt = Circuit("regime_com_valvula")
    ckt.add(
        VoltageSource(
            "E", "bus", "gnd", amplitude_V=pico_V, frequency_Hz=60.0, phase_deg=0.0
        )
    )
    ramo = build_atp_literal_snubber_branch("sn", "bus", "gnd", gate=mestre.gate)
    ckt.extend(ramo.components)
    mestre.controllers = (ramo.controller,)

    solver = Solver(ckt, dt=1.0e-6)
    sonda = solver.add_probe(BranchCurrentProbe("i_rs", ramo.resistor))

    def _arma(t, _solver):
        if t >= 1.0e-3:
            polo.cb_state = ATP_CB_OPEN

    # Antes da trava o ramo é transparente: nenhuma condução em regime.
    solver.run(t_end=1.0e-3, controllers=[_arma, mestre])
    assert not mestre.armed
    assert ramo.controller.n_firings == 0
    assert float(np.max(np.abs(np.asarray(sonda.values)))) < 1.0e-9
    n0 = len(sonda.time_s)
    energia_0 = ramo.controller.energy_J

    # Dois períodos completos depois da trava.
    solver.run(t_end=2.0 / 60.0 + 0.6e-3, controllers=[_arma, mestre], reset=False)
    assert mestre.armed and mestre.fm == 1.0

    t = np.asarray(sonda.time_s)[n0:]
    i = np.asarray(sonda.values)[n0:]
    janela_s = float(t[-1] - t[0])
    energia_J = ramo.controller.energy_J - energia_0
    pico_A = float(np.max(np.abs(i)))
    eficaz_A = float(np.sqrt(np.mean(i**2)))
    potencia_W = energia_J / janela_s
    fracao = ramo.controller.conduction_time_s / janela_s

    # Dois disparos por período: um em cada semiciclo.
    assert ramo.controller.n_firings == pytest.approx(4, abs=1)
    # O pico é o da tensão de pico sobre 30 Ω — a válvula está conduzindo
    # quando a tensão passa pelo máximo.
    assert pico_A == pytest.approx(pico_V / ATP_SNUBBER_RESISTANCE_OHM, rel=0.02)
    assert pico_A == pytest.approx(112.87, rel=0.02)
    assert eficaz_A == pytest.approx(74.96, rel=0.02)
    assert potencia_W == pytest.approx(168.6e3, rel=0.03)
    assert potencia_W == pytest.approx(
        ATP_SNUBBER_RESISTANCE_OHM * eficaz_A**2, rel=1.0e-3
    )
    assert energia_J == pytest.approx(5.78e3, rel=0.03)
    assert fracao > 0.70, "a válvula conduz em praticamente todo semiciclo"
    # A trava explica o resultado: o comando nunca é liberado.
    assert mestre.gate() is True
    assert ATP_SNUBBER_BREAKOVER_V < pico_V


def test_limitacoes_declaradas_seguem_o_padrao_do_projeto():
    """Chaves com prefixo ``emt_``, textos não vazios e sem colisão."""
    catalogos = (
        VCB_LIMITATIONS,
        SNUBBER_LIMITATIONS,
        case_mod.KNOWN_LIMITATIONS,
    )
    vistas: set[str] = set()
    for catalogo in catalogos:
        assert catalogo, "catálogo de limitações vazio"
        for chave, texto in catalogo.items():
            assert chave.startswith("emt_"), chave
            assert isinstance(texto, str) and len(texto) > 80, chave
            assert chave not in vistas, f"chave duplicada: {chave}"
            vistas.add(chave)
    # As lacunas materiais do estudo estão declaradas nominalmente.
    assert "emt_snubber_breakover_not_published" in SNUBBER_LIMITATIONS
    assert "emt_vcb_didt_convention_ambiguous" in VCB_LIMITATIONS
    assert "emt_case_rl_branch_ambiguous" in case_mod.KNOWN_LIMITATIONS
    assert "emt_vcb_zero_initial_withstand" in VCB_LIMITATIONS
    assert "emt_case_doc_a_rrds_prevents_clearing" in case_mod.KNOWN_LIMITATIONS


def test_limitacoes_dos_modulos_novos_nao_colidem_com_as_do_kernel():
    """Nenhuma chave nova repete uma das do kernel EMT."""
    from app.simulation.emt import KNOWN_LIMITATIONS as KERNEL_LIMITATIONS

    # O catálogo do kernel cresce quando o kernel cresce (a partida em
    # regime permanente acrescentou três chaves e removeu a de ausência
    # de inicialização); o que este teste protege é a AUSÊNCIA DE COLISÃO.
    assert len(KERNEL_LIMITATIONS) >= 10
    novas = (
        set(VCB_LIMITATIONS)
        | set(SNUBBER_LIMITATIONS)
        | set(case_mod.KNOWN_LIMITATIONS)
    )
    assert not (novas & set(KERNEL_LIMITATIONS))


# ---------------------------------------------------------------------------
# Regressão: a chave ideal do polo literal obedece à semântica tipo 13
# ---------------------------------------------------------------------------


class TestPoloLiteralAberturaNaPassagemPorZero:
    """``SW_STATE = 0`` é comando; a abertura só se efetiva no zero de corrente.

    Antes desta correção a chave abria no instante de ``T_OPEN`` carregando
    a corrente de carga (74 A no polo R do caso de referência), que era
    descarregada no ramo série de arco de 20 Ω / 50 nH / 20 pF e produzia
    um degrau de dezenas a centenas de quilovolts em um único passo
    [CÁLCULO PRÓPRIO: ``i·Δt/C``]. A chave tipo 13 do ATP abre no primeiro
    instante em que ``|i| <= Imar``; com ``Imar`` em branco, na passagem
    natural por zero [LISTA: 02, §1.3 e §3.6].
    """

    def _modelo(self, t_end_s: float = 0.016):
        from app.simulation.emt.cases.atp_reference import AtpReferenceCase

        m = AtpReferenceCase(
            with_snubber=False, atp_model_compatibility=True, t_end_s=t_end_s
        ).build()
        m.run()
        return m

    def test_chave_abre_depois_do_comando_e_com_corrente_no_zero(self):
        m = self._modelo()
        res = m.poles[0].result
        assert res.switch_opening_time_s is not None
        assert res.switch_opening_time_s >= 0.01455
        # 60 Hz, ~911 A de pico: |di/dt| <= 0,35 A/µs -> no passo do zero,
        # |i| fica abaixo de 0,5 A; antes da correção era 74 A.
        assert abs(res.switch_opening_current_A) < 0.5

    def test_sem_degrau_espurio_na_abertura_do_polo_r(self):
        import numpy as np

        m = self._modelo()
        v_kV = m.trv_probes["a"].values * 1e-3
        pu = np.sqrt(2.0) * 4160.0 / np.sqrt(3.0) * 1e-3
        # Sem o artefato o pico fica na ordem da TRV do caso (Tabela III do
        # trabalho: 30,24 kV), nunca nos 688 kV do estado anterior.
        assert np.max(np.abs(v_kV)) < 15.0 * pu

    def test_margem_numerica_abre_dentro_da_margem(self):
        from app.simulation.emt.vcb import AtpVcbParameters

        p = AtpVcbParameters(switch_current_margin_A=2.0)
        assert p.switch_current_margin_A == 2.0
        with __import__("pytest").raises(ValueError):
            AtpVcbParameters(switch_current_margin_A=-1.0)
