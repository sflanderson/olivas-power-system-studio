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
    DOC_A_SNUBBER_RESISTANCE_OHM,
    SNUBBER_BLOCKED,
    SNUBBER_CONDUCTING,
    ThyristorSnubber,
    build_snubber_branch,
    three_phase_snubber,
)
from app.simulation.emt.snubber import KNOWN_LIMITATIONS as SNUBBER_LIMITATIONS
from app.simulation.emt.vcb import (
    DIDT_INTERRUPT_ABOVE,
    DIDT_INTERRUPT_WITHIN,
    DOC_A_CHOPPING_RANGE_A,
    DOC_A_RRDS_A_KV_PER_MS,
    DOC_A_RRDS_B_KV_PER_MS2,
    DOC_A_STAGGER_RANGE_S,
    STATE_CLEARED,
    STATE_CLOSED,
    STATE_OPEN,
    LinearRecovery,
    ParabolicRecovery,
    VacuumCircuitBreakerModel,
    stagger_times,
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
#: condição inicial CONSISTENTE exigida pela limitação declarada
#: ``emt_no_steady_state_init`` do kernel: sem ela a bancada — que não tem
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
    """Nenhuma chave nova repete uma das 10 do kernel EMT."""
    from app.simulation.emt import KNOWN_LIMITATIONS as KERNEL_LIMITATIONS

    assert len(KERNEL_LIMITATIONS) == 10
    novas = (
        set(VCB_LIMITATIONS)
        | set(SNUBBER_LIMITATIONS)
        | set(case_mod.KNOWN_LIMITATIONS)
    )
    assert not (novas & set(KERNEL_LIMITATIONS))
