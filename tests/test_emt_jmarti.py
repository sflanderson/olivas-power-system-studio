"""
tests/test_emt_jmarti.py — verificação do modelo de linha/cabo com
DEPENDÊNCIA DE FREQUÊNCIA (``app.simulation.emt.jmarti``, método de
J. R. Martí).

Estrutura da bateria:

* **ajuste racional** — o *vector fitting* recupera exatamente os polos
  de uma função racional conhecida, o erro é reportado e a tolerância
  declarada é aplicada;
* **fase mínima e atraso** — a relação de ganho-fase de Bode reconstrói
  a fase de funções racionais conhecidas e extrai ``τ`` de ``A(ω)``;
* **consistência com o Bergeron** — com ``Z_c`` constante e
  ``A = e^{−jωτ}`` o modelo deve reproduzir a linha sem perdas de
  Dommel TERMO A TERMO. É o teste mais importante do arquivo: se ele
  falha, o modelo dependente da frequência está errado no seu próprio
  caso limite;
* **física de ondas viajantes** — reflexão em terminação aberta e
  casada, causalidade, estabilidade, balanço de energia;
* **viés medido** — comparação direta Bergeron × JMarti sobre a MESMA
  frente íngreme, reportando a diferença de ``dv/dt`` e de tempo de
  frente ``T1``, que é o efeito que motivou a implementação.

Todo valor de referência é (a) solução analítica de onda viajante,
(b) identidade algébrica do próprio modelo, ou (c) [CÁLCULO PRÓPRIO]
medido nesta sessão e registrado no comentário.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from app.simulation.emt import (
    KNOWN_LIMITATIONS,
    BergeronLine,
    BranchCurrentProbe,
    Circuit,
    Component,
    NodeVoltageProbe,
    Resistor,
    Solver,
    Switch,
    TimedSwitchController,
    VoltageSource,
)
from app.simulation.emt import __all__ as EMT_ALL
from app.simulation.emt.components import Inductor
from app.simulation.emt.jmarti import (
    DELAY_METHODS,
    JMARTI_LIMITATIONS,
    JMartiError,
    JMartiLine,
    LineDataError,
    LineFrequencyData,
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
from app.simulation.emt.steady_state import UnsupportedComponentError

# --------------------------------------------------------------------------
# Parâmetros de referência
# --------------------------------------------------------------------------

#: Cabo de MT do caso de manobra do Documento A [REPO:
#: app/simulation/emt/cases/motor_switching.py — CableParameters].
CABO_L = 0.35e-6
CABO_C = 0.25e-9
CABO_R = 0.10e-3
CABO_ELL = 500.0

ZC_REF = math.sqrt(CABO_L / CABO_C)
TAU_REF = CABO_ELL * math.sqrt(CABO_L * CABO_C)


def _cabo_data(f_max_Hz: float = 2.0e6, resistance: float = CABO_R) -> LineFrequencyData:
    """Tabelas ``Z_c(ω)``/``A(ω)`` do cabo de referência."""
    omega = frequency_grid_for_delay(TAU_REF, f_min_Hz=1.0, f_max_Hz=f_max_Hz)
    return LineFrequencyData.from_distributed_parameters(
        length_m=CABO_ELL,
        inductance_H_per_m=CABO_L,
        capacitance_F_per_m=CABO_C,
        resistance_ohm_per_m=resistance,
        omega=omega,
        label="cabo de referência",
    )


def _degrau(
    line: Component,
    *,
    dt: float,
    t_end: float,
    r_source: float,
    r_load: float,
    amplitude_V: float = 100.0,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, Solver]:
    """Degrau de tensão sobre uma linha; devolve ``(t, v_k, v_m, solver)``."""
    ckt = Circuit("degrau")
    ckt.add(
        VoltageSource(
            "E", "s", "gnd", amplitude_V=0.0, frequency_Hz=0.0, dc_offset_V=amplitude_V
        )
    )
    ckt.add(Resistor("Rs", "s", "k", r_source))
    ckt.add(line)
    ckt.add(Resistor("Rl", "m", "gnd", r_load))
    solver = Solver(ckt, dt=dt)
    p_k = solver.add_probe(NodeVoltageProbe("v_k", "k"))
    p_m = solver.add_probe(NodeVoltageProbe("v_m", "m"))
    result = solver.run(t_end=t_end)
    return (
        np.asarray(result.time_s),
        np.asarray(p_k.values),
        np.asarray(p_m.values),
        solver,
    )


def _tempo_de_frente(t: np.ndarray, v: np.ndarray) -> tuple[float, float]:
    """``(T1, dv/dt_max)`` da PRIMEIRA subida: 30 %-90 % do pico [s, V/s].

    A janela 30 %-90 % é a de [NORMA: IEC 60060-1, definição de tempo de
    frente de impulso de tensão, ``T1 = 1,67·(t_90 − t_30)``]; aqui
    devolve-se ``t_90 − t_30`` SEM o fator 1,67, para que a comparação
    entre modelos seja direta e sem convenção embutida.
    """
    v_peak = float(np.max(v))
    if v_peak <= 0.0:  # pragma: no cover - defensivo
        return math.nan, math.nan
    i_peak = int(np.argmax(v))
    seg_t = t[: i_peak + 1]
    seg_v = v[: i_peak + 1]
    i30 = int(np.argmax(seg_v >= 0.3 * v_peak))
    i90 = int(np.argmax(seg_v >= 0.9 * v_peak))
    t1 = float(seg_t[i90] - seg_t[i30])
    dvdt = float(np.max(np.diff(seg_v) / np.diff(seg_t))) if seg_t.size > 1 else math.nan
    return t1, dvdt


# --------------------------------------------------------------------------


class TestAjusteRacional:
    """*Vector fitting*: recuperação de polos, erro e tolerância."""

    def test_recupera_polos_reais_de_funcao_conhecida(self) -> None:
        """Função com polos reais conhecidos é recuperada quase exatamente."""
        w = frequency_grid(1.0, 1.0e5, 300)
        polos = np.array([-2.0e3, -5.0e4], dtype=complex)
        residuos = np.array([1.0e3, -4.0e4], dtype=complex)
        s = 1j * w
        f = 0.25 + sum(k / (s - p) for p, k in zip(polos, residuos))
        fit = vector_fit(w, f, n_poles=2, n_iterations=12, label="racional real")
        recuperados = np.sort(fit.poles.real)
        assert np.allclose(recuperados, np.sort(polos.real), rtol=1.0e-6)
        assert fit.d == pytest.approx(0.25, rel=1.0e-8)
        assert fit.rms_error < 1.0e-9

    def test_recupera_par_complexo_conjugado(self) -> None:
        """Par complexo conjugado é recuperado com resíduos conjugados."""
        w = frequency_grid(1.0e2, 1.0e6, 400)
        p = complex(-2.0e4, 3.0e4)
        k = complex(1.0e4, 5.0e3)
        s = 1j * w
        f = 0.5 + k / (s - p) + np.conj(k) / (s - np.conj(p))
        fit = vector_fit(w, f, n_poles=2, n_iterations=12, label="par complexo")
        assert fit.n_poles == 2
        assert fit.poles[1] == pytest.approx(np.conj(fit.poles[0]), rel=1.0e-9)
        assert abs(fit.poles[0].real - p.real) < 1.0e-6 * abs(p)
        assert abs(abs(fit.poles[0].imag) - abs(p.imag)) < 1.0e-6 * abs(p)
        assert fit.rms_error < 1.0e-9

    def test_erro_de_ajuste_abaixo_da_tolerancia_declarada(self) -> None:
        """``Y_c(ω)`` do cabo de referência ajusta bem abaixo de 1 %."""
        data = _cabo_data()
        fit = vector_fit(
            data.omega, data.y_c, n_poles=6, tolerance=1.0e-2, label="Y_c cabo"
        )
        assert fit.rms_error < 1.0e-2
        assert fit.max_error < 5.0e-2
        assert fit.is_stable()

    def test_tolerancia_violada_levanta_erro_com_mensagem_acionavel(self) -> None:
        """Ajuste insuficiente levanta RationalFitError citando a tolerância."""
        data = _cabo_data()
        with pytest.raises(RationalFitError, match="tolerância"):
            vector_fit(
                data.omega,
                data.y_c,
                n_poles=0,
                tolerance=1.0e-6,
                label="Y_c subajustada",
            )

    def test_validacao_de_entradas_do_ajuste(self) -> None:
        """Entradas inconsistentes são recusadas antes de qualquer cálculo."""
        w = frequency_grid(1.0, 1.0e4, 50)
        f = np.ones(50, dtype=complex)
        with pytest.raises(RationalFitError, match="amostras de valor"):
            vector_fit(w, f[:10], n_poles=2)
        with pytest.raises(RationalFitError, match="n_poles"):
            vector_fit(w, f, n_poles=-1)
        with pytest.raises(RationalFitError, match="subdeterminado"):
            vector_fit(w, f, n_poles=80)
        with pytest.raises(RationalFitError, match="weight"):
            vector_fit(w, f, n_poles=2, weight="quadratico")
        with pytest.raises(LineDataError, match="crescente"):
            vector_fit(w[::-1], f, n_poles=2)

    def test_ajuste_sem_polos_devolve_constante(self) -> None:
        """``n_poles = 0`` reduz o ajuste ao termo constante real."""
        w = frequency_grid(1.0, 1.0e4, 60)
        f = np.full(w.size, 3.5 + 0.0j)
        fit = vector_fit(w, f, n_poles=0, label="constante")
        assert fit.n_poles == 0
        assert fit.d == pytest.approx(3.5, rel=1.0e-12)
        assert fit.rms_error < 1.0e-12
        assert fit.is_stable()

    def test_avaliacao_e_ganho_continuo_da_funcao_ajustada(self) -> None:
        """``evaluate`` e ``dc_gain`` reproduzem a definição da racional."""
        p = np.array([-1.0e3], dtype=complex)
        k = np.array([2.0e3], dtype=complex)
        fit = RationalFit(p, k, 0.5)
        w = np.array([0.0, 1.0e3, 1.0e6])
        esperado = 0.5 + k[0] / (1j * w - p[0])
        assert np.allclose(fit.evaluate(w), esperado)
        assert fit.dc_gain() == pytest.approx(0.5 + 2.0, rel=1.0e-12)

    def test_estabilidade_e_reflexao_de_polos_instaveis(self) -> None:
        """Polos no semiplano DIREITO são refletidos; a saída é estável."""
        instavel = RationalFit(
            np.array([1.0e3 + 0.0j]), np.array([1.0 + 0.0j]), 0.0
        )
        assert not instavel.is_stable()
        # Uma função cuja melhor aproximação tende a polos no eixo: o
        # ajuste deve devolver polos estritamente estáveis mesmo assim.
        w = frequency_grid(1.0e2, 1.0e6, 300)
        f = 1.0 / (1.0 + 1j * w / 1.0e4)
        fit = vector_fit(w, f, n_poles=2, label="reflexão")
        assert fit.is_stable()
        assert np.all(fit.poles.real < 0.0)

    def test_condensacao_de_pares_conjugados(self) -> None:
        """Pares conjugados viram um termo de peso 2; reais, peso 1."""
        p = np.array([-1.0e3, -2.0e4 + 3.0e4j, -2.0e4 - 3.0e4j], dtype=complex)
        k = np.array([1.0, 2.0 + 1.0j, 2.0 - 1.0j], dtype=complex)
        pc, kc, wc = RationalFit(p, k, 0.0).condensed()
        assert pc.size == 2
        assert list(wc) == [1.0, 2.0]
        assert kc[0].imag == 0.0
        # Sem conjugado adjacente o ajuste não seria real no tempo.
        with pytest.raises(RationalFitError, match="conjugado"):
            RationalFit(p[:2], k[:2], 0.0).condensed()

    def test_polos_iniciais_tem_estrutura_esperada(self) -> None:
        """Polos de partida: reais/pares com ``Re = −Im/100``, na faixa."""
        w = frequency_grid(1.0, 1.0e6, 100)
        p3 = initial_poles(w, 3)
        assert p3.size == 3
        assert p3[0].imag == 0.0
        assert p3[2] == np.conj(p3[1])
        assert abs(p3[1].real) == pytest.approx(abs(p3[1].imag) / 100.0)
        assert initial_poles(w, 0).size == 0


class TestFaseMinimaEAtraso:
    """Relação de ganho-fase de Bode e extração do atraso puro."""

    def test_reconstroi_fase_de_primeira_ordem(self) -> None:
        """``a/(s+a)`` tem sua fase recuperada a partir só do módulo."""
        w = frequency_grid(1.0, 1.0e6, 400)
        a = 1.0e4
        h = a / (1j * w + a)
        phi = minimum_phase_angle(w, np.abs(h))
        erro = np.max(np.abs(phi - np.angle(h)))
        # [CÁLCULO PRÓPRIO] erro medido: 1,7e−3 rad.
        assert erro < 1.0e-2

    def test_reconstroi_fase_de_segunda_ordem(self) -> None:
        """Par complexo conjugado: fase recuperada dentro de 0,01 rad."""
        w = frequency_grid(1.0, 1.0e6, 400)
        p = np.array([-2.0e4 + 3.0e4j, -2.0e4 - 3.0e4j])
        h = np.prod([(-pp) / (1j * w - pp) for pp in p], axis=0)
        phi = minimum_phase_angle(w, np.abs(h))
        assert np.max(np.abs(phi - np.unwrap(np.angle(h)))) < 1.0e-2

    def test_extrai_atraso_puro_pelos_dois_metodos(self) -> None:
        """``A = e^{−jωτ}``: ambos os métodos devolvem ``τ`` exato."""
        tau = 3.2e-6
        w = frequency_grid_for_delay(tau, f_min_Hz=1.0e2, f_max_Hz=1.0e6)
        a = np.exp(-1j * w * tau)
        for metodo in DELAY_METHODS:
            assert estimate_time_delay(w, a, method=metodo) == pytest.approx(
                tau, rel=1.0e-9
            )

    def test_extrai_atraso_de_linha_com_perdas(self) -> None:
        """Linha ``R'L'C'``: ``τ`` recuperado bate com ``ℓ·sqrt(L'C')``."""
        data = _cabo_data()
        tau = estimate_time_delay(data.omega, data.a)
        assert tau == pytest.approx(TAU_REF, rel=1.0e-6)

    def test_detecta_aliasing_de_fase_em_malha_grosseira(self) -> None:
        """Malha rala falseia ``τ``; o erro diz quantos pontos usar."""
        w = frequency_grid(1.0, 1.0e7, 300)
        data = LineFrequencyData.from_distributed_parameters(
            length_m=CABO_ELL,
            inductance_H_per_m=CABO_L,
            capacitance_F_per_m=CABO_C,
            resistance_ohm_per_m=CABO_R,
            omega=w,
        )
        with pytest.raises(LineDataError, match="pontos por década"):
            estimate_time_delay(w, data.a)

    def test_validacao_do_extrator_de_atraso(self) -> None:
        """Método inválido, faixa inválida e sinal de fase invertido."""
        tau = 2.0e-6
        w = frequency_grid_for_delay(tau, f_min_Hz=1.0e2, f_max_Hz=1.0e6)
        a = np.exp(-1j * w * tau)
        with pytest.raises(LineDataError, match="method"):
            estimate_time_delay(w, a, method="chute")
        with pytest.raises(LineDataError, match="band_fraction"):
            estimate_time_delay(w, a, band_fraction=0.0)
        with pytest.raises(LineDataError, match="não positivo"):
            estimate_time_delay(w, np.conj(a))


class TestTabelasDeEntrada:
    """Validação e coerência física de :class:`LineFrequencyData`."""

    def test_recusa_tabelas_insuficientes_ou_inconsistentes(self) -> None:
        """Tamanhos distintos, poucas amostras e ω inválido são recusados."""
        w = frequency_grid(1.0, 1.0e4, 10)
        zc = np.full(10, 50.0 + 0j)
        a = np.exp(-1j * w * 1.0e-6)
        with pytest.raises(LineDataError, match="tamanhos distintos"):
            LineFrequencyData(w, zc[:5], a)
        with pytest.raises(LineDataError, match="insuficiente"):
            LineFrequencyData(w[:3], zc[:3], a[:3])
        with pytest.raises(LineDataError, match="positivo"):
            LineFrequencyData(np.linspace(0.0, 10.0, 10), zc, a)

    def test_recusa_funcao_de_propagacao_com_ganho(self) -> None:
        """``|A| > 1`` descreve linha ATIVA e é erro, não aviso."""
        w = frequency_grid(1.0, 1.0e4, 10)
        zc = np.full(10, 50.0 + 0j)
        with pytest.raises(LineDataError, match="linha ATIVA"):
            LineFrequencyData(w, zc, np.full(10, 1.5 + 0j))

    def test_from_series_shunt_reproduz_a_analitica(self) -> None:
        """``γ = sqrt(zy)``, ``Z_c = sqrt(z/y)``, ``A = e^{−γℓ}``."""
        w = frequency_grid(1.0, 1.0e5, 50)
        z = CABO_R + 1j * w * CABO_L
        y = 1j * w * CABO_C
        data = LineFrequencyData.from_series_shunt(w, z, y, length_m=CABO_ELL)
        gamma = np.sqrt(z * y)
        assert np.allclose(data.z_c, np.sqrt(z / y))
        assert np.allclose(data.a, np.exp(-gamma * CABO_ELL))
        assert data.n_samples == 50
        assert np.allclose(data.y_c, 1.0 / data.z_c)

    def test_sem_perdas_z_c_constante_e_a_e_atraso_puro(self) -> None:
        """``R' = G' = 0`` devolve ``Z_c`` constante e ``|A| = 1``."""
        data = LineFrequencyData.from_distributed_parameters(
            length_m=CABO_ELL,
            inductance_H_per_m=CABO_L,
            capacitance_F_per_m=CABO_C,
        )
        assert np.allclose(data.z_c.real, ZC_REF)
        assert np.allclose(np.abs(data.a), 1.0)

    def test_geometria_interna_produz_efeito_pelicular(self) -> None:
        """Caminho interno: ``Z_c`` cai com ω e a resistência cresce."""
        w = frequency_grid(1.0, 1.0e5, 200)
        data = LineFrequencyData.from_overhead_geometry(
            length_m=500.0, radius_m=0.01, height_m=10.0, omega=w
        )
        # Z_c de linha aérea cai com a frequência, aproximando-se de
        # sqrt(L'/C') do modo aéreo [INFERÊNCIA FÍSICA].
        assert abs(data.z_c[0]) > abs(data.z_c[-1])
        assert 200.0 < abs(data.z_c[-1]) < 800.0
        # Atenuação cresce com a frequência.
        assert abs(data.a[0]) > abs(data.a[-1])
        with pytest.raises(ValueError, match="raio"):
            LineFrequencyData.from_overhead_geometry(
                length_m=500.0, radius_m=1.0, height_m=0.5, omega=w
            )


class TestModeloModal:
    """Ajuste completo de um modo e suas validações."""

    def test_modo_a_parametros_constantes_e_exato(self) -> None:
        """``Y_c`` e ``A_min`` constantes, sem polos e sem erro."""
        modelo = ModalLineModel.constant_parameter(
            surge_impedance_ohm=ZC_REF, travel_time_s=TAU_REF
        )
        assert modelo.y_c.n_poles == 0
        assert modelo.a_min.n_poles == 0
        assert modelo.y_c.d == pytest.approx(1.0 / ZC_REF)
        w = np.array([1.0, 1.0e6])
        assert np.allclose(modelo.characteristic_impedance(w), ZC_REF)
        assert np.allclose(np.abs(modelo.propagation(w)), 1.0)

    def test_ajuste_reconstroi_as_tabelas(self) -> None:
        """O modelo ajustado reproduz ``Z_c(ω)`` e ``A(ω)`` tabelados."""
        data = _cabo_data()
        modelo = ModalLineModel.fit(data, n_poles_yc=6, n_poles_a=8)
        zc = modelo.characteristic_impedance(data.omega)
        a = modelo.propagation(data.omega)
        err_zc = np.max(np.abs(zc - data.z_c)) / np.max(np.abs(data.z_c))
        err_a = np.max(np.abs(a - data.a)) / np.max(np.abs(data.a))
        assert err_zc < 1.0e-2
        assert err_a < 1.0e-2
        rel = modelo.fit_report()
        assert rel["yc_poles"] == 6
        assert rel["a_poles"] == 8
        assert float(rel["travel_time_s"]) == pytest.approx(TAU_REF, rel=1.0e-6)

    def test_valida_entradas_do_ajuste_modal(self) -> None:
        """Tipo errado, ``τ`` imposto inválido e ``Y_c(∞)`` não positiva."""
        with pytest.raises(LineDataError, match="LineFrequencyData"):
            ModalLineModel.fit(object())  # type: ignore[arg-type]
        data = _cabo_data()
        with pytest.raises(ValueError, match="travel_time_s"):
            ModalLineModel.fit(data, travel_time_s=-1.0)
        vazio = np.zeros(0, dtype=complex)
        with pytest.raises(RationalFitError, match="não é positiva"):
            ModalLineModel(
                y_c=RationalFit(vazio, vazio, -1.0),
                a_min=RationalFit(vazio, vazio, 1.0),
                travel_time_s=1.0e-6,
            )
        with pytest.raises(RationalFitError, match="semiplano direito"):
            ModalLineModel(
                y_c=RationalFit(
                    np.array([1.0 + 0j]), np.array([1.0 + 0j]), 0.02
                ),
                a_min=RationalFit(vazio, vazio, 1.0),
                travel_time_s=1.0e-6,
            )


class TestConsistenciaComBergeron:
    """Caso limite: sem dependência de frequência o JMarti É o Bergeron."""

    @pytest.mark.parametrize("tau", [2.0e-6, 2.35e-6])
    def test_reproduz_bergeron_sem_perdas(self, tau: float) -> None:
        """Teste CENTRAL do módulo.

        Com ``Z_c`` constante e ``A_min = 1``, o histórico do JMarti vale
        ``I_k = −(1/Z_c)·F_m(t−τ)`` com ``F_m = v_m + Z_c·i_mk``, que é
        exatamente a eq. (7b) de [FONTE: Dommel 1969, p. 389]. As duas
        implementações devem coincidir até o arredondamento de ponto
        flutuante, com ``τ`` múltiplo ou NÃO múltiplo de ``Δt`` (nesse
        caso exercitando a interpolação linear de histórico).
        """
        dt = 1.0e-7
        zc = 50.0
        berg = BergeronLine(
            "L", "k", "m", surge_impedance_ohm=zc, travel_time_s=tau
        )
        jm = JMartiLine.constant_parameter(
            "L", "k", "m", surge_impedance_ohm=zc, travel_time_s=tau
        )
        t_b, vk_b, vm_b, _ = _degrau(
            berg, dt=dt, t_end=3.0e-5, r_source=zc, r_load=1.0e9
        )
        t_j, vk_j, vm_j, _ = _degrau(
            jm, dt=dt, t_end=3.0e-5, r_source=zc, r_load=1.0e9
        )
        assert np.allclose(t_b, t_j)
        escala = max(float(np.max(np.abs(vm_b))), 1.0)
        assert np.max(np.abs(vk_b - vk_j)) < 1.0e-9 * escala
        assert np.max(np.abs(vm_b - vm_j)) < 1.0e-9 * escala

    def test_condutancia_estampada_igual_a_do_bergeron(self) -> None:
        """A matriz montada é a MESMA nos dois modelos sem perdas."""
        zc = 37.4
        tau = 4.6e-6
        for linha, esperado in (
            (
                BergeronLine("L", "k", "m", surge_impedance_ohm=zc, travel_time_s=tau),
                1.0 / zc,
            ),
            (
                JMartiLine.constant_parameter(
                    "L", "k", "m", surge_impedance_ohm=zc, travel_time_s=tau
                ),
                1.0 / zc,
            ),
        ):
            ckt = Circuit("g")
            ckt.add(linha)
            ckt.add(Resistor("Rk", "k", "gnd", 1.0e9))
            ckt.add(Resistor("Rm", "m", "gnd", 1.0e9))
            ckt.build()
            ckt.prepare(1.0e-6)
            assert linha.conductance_S == pytest.approx(esperado, rel=1.0e-12)


class TestOndasViajantes:
    """Física de propagação: reflexão, causalidade, estabilidade, energia."""

    def test_terminacao_aberta_dobra_a_tensao(self) -> None:
        """Em circuito aberto o coeficiente de reflexão é +1."""
        zc = 50.0
        tau = 2.0e-6
        jm = JMartiLine.constant_parameter(
            "L", "k", "m", surge_impedance_ohm=zc, travel_time_s=tau
        )
        t, _, vm, _ = _degrau(
            jm, dt=1.0e-8, t_end=1.5 * tau, r_source=zc, r_load=1.0e12
        )
        # Onda incidente = 100·Z_c/(Z_c + R_s) = 50 V; refletida = +50 V.
        assert float(np.max(vm)) == pytest.approx(100.0, rel=1.0e-6)

    def test_terminacao_casada_nao_reflete(self) -> None:
        """Com ``R_load = Z_c`` a tensão no fim é a incidente, sem degraus."""
        zc = 50.0
        tau = 2.0e-6
        jm = JMartiLine.constant_parameter(
            "L", "k", "m", surge_impedance_ohm=zc, travel_time_s=tau
        )
        t, vk, vm, _ = _degrau(jm, dt=1.0e-8, t_end=6.0 * tau, r_source=zc, r_load=zc)
        assert float(np.max(vm)) == pytest.approx(50.0, rel=1.0e-9)
        # Sem reflexão, a tensão do emissor permanece em 50 V o tempo todo.
        depois = vk[t > tau * 0.5]
        assert np.allclose(depois, 50.0, atol=1.0e-9)

    def test_causalidade_nenhuma_resposta_antes_do_atraso(self) -> None:
        """Nada chega ao terminal ``m`` antes de ``t = τ``."""
        tau = 3.0e-6
        dt = 1.0e-8
        data = _cabo_data()
        modelo = ModalLineModel.fit(data, n_poles_yc=6, n_poles_a=8)
        for linha in (
            JMartiLine.constant_parameter(
                "L", "k", "m", surge_impedance_ohm=50.0, travel_time_s=tau
            ),
            JMartiLine("L", "k", "m", model=modelo),
        ):
            atraso = linha.travel_time_s
            t, _, vm, _ = _degrau(
                linha, dt=dt, t_end=2.0 * atraso, r_source=50.0, r_load=1.0e9
            )
            antes = vm[t < atraso - dt]
            assert float(np.max(np.abs(antes))) < 1.0e-9
            assert float(np.max(np.abs(vm))) > 1.0

    def test_polos_ajustados_no_semiplano_esquerdo(self) -> None:
        """Estabilidade: todo polo de ``Y_c`` e de ``A_min`` tem ``Re < 0``."""
        modelo = ModalLineModel.fit(_cabo_data(), n_poles_yc=8, n_poles_a=10)
        assert modelo.y_c.is_stable()
        assert modelo.a_min.is_stable()
        assert np.all(modelo.y_c.poles.real < 0.0)
        assert np.all(modelo.a_min.poles.real < 0.0)

    def test_conservacao_de_energia_em_linha_sem_perdas(self) -> None:
        """Balanço de energia da linha sem perdas com terminação casada.

        Em regime, a energia que ENTROU pelo terminal ``k`` menos a que
        SAIU pelo terminal ``m`` deve ser a energia armazenada na linha,
        ``W = ℓ·(C'V²/2 + L'I²/2) = τ·V²/Z_c`` para tensão e corrente
        uniformes ``V`` e ``I = V/Z_c`` [CÁLCULO PRÓPRIO, integrando o
        perfil uniforme da linha casada].
        """
        zc = 50.0
        tau = 2.0e-6
        dt = 1.0e-9
        jm = JMartiLine.constant_parameter(
            "L", "k", "m", surge_impedance_ohm=zc, travel_time_s=tau
        )
        ckt = Circuit("energia")
        ckt.add(
            VoltageSource(
                "E", "s", "gnd", amplitude_V=0.0, frequency_Hz=0.0, dc_offset_V=100.0
            )
        )
        ckt.add(Resistor("Rs", "s", "k", zc))
        ckt.add(jm)
        ckt.add(Resistor("Rl", "m", "gnd", zc))
        solver = Solver(ckt, dt=dt)
        p_vk = solver.add_probe(NodeVoltageProbe("v_k", "k"))
        p_vm = solver.add_probe(NodeVoltageProbe("v_m", "m"))
        p_ik = solver.add_probe(BranchCurrentProbe("i_k", jm, terminal=0))
        p_im = solver.add_probe(BranchCurrentProbe("i_m", jm, terminal=1))
        res = solver.run(t_end=4.0 * tau)
        t = np.asarray(res.time_s)
        p_in = np.asarray(p_vk.values) * np.asarray(p_ik.values)
        p_out = np.asarray(p_vm.values) * np.asarray(p_im.values)
        e_in = float(np.trapezoid(p_in, t))
        e_out = float(np.trapezoid(p_out, t))
        v_reg = 50.0
        armazenada = tau * v_reg**2 / zc
        assert (e_in + e_out) == pytest.approx(armazenada, rel=2.0e-3)

    def test_linha_com_perdas_atenua_a_onda(self) -> None:
        """Com ``R' > 0`` a onda chega menor que a incidente."""
        modelo = ModalLineModel.fit(
            _cabo_data(resistance=5.0e-3), n_poles_yc=6, n_poles_a=10
        )
        jm = JMartiLine("L", "k", "m", model=modelo)
        zc = 1.0 / modelo.y_c.d
        t, _, vm, _ = _degrau(
            jm, dt=1.0e-8, t_end=1.5 * modelo.travel_time_s, r_source=zc, r_load=zc
        )
        incidente = 100.0 * zc / (2.0 * zc)
        chegou = float(np.max(vm))
        assert 0.0 < chegou < incidente
        assert chegou > 0.5 * incidente


class TestComparacaoDireta:
    """Bergeron × JMarti sobre a MESMA frente íngreme — o viés medido."""

    def test_frente_ingreme_diferenca_de_dvdt_e_de_t1(self) -> None:
        """Mede e registra o viés de ``dv/dt`` e de ``T1`` entre modelos.

        É o efeito que motivou a implementação: com parâmetros
        constantes a frente chega praticamente sem deformação, enquanto
        o modelo dependente da frequência a atenua e a alarga. O teste
        NÃO fixa o valor da diferença — que depende dos parâmetros do
        cabo —, mas exige que ela exista e tenha o SINAL fisicamente
        esperado, e deixa os números na mensagem do ``assert``.

        [CÁLCULO PRÓPRIO] Medida nesta sessão, cabo de 500 m com
        ``R' = 20 mΩ/m``, ``Δt = 5 ns``, degrau em fonte casada e
        terminação aberta:

        ===================== ========= ============ ==============
        modelo                pico [V]  T1 [µs]      dv/dt [V/s]
        ===================== ========= ============ ==============
        Bergeron sem perdas   100,000   0,00         2,000e10
        Bergeron R/4,R/2,R/4   97,583   0,00         1,814e10
        JMarti (ajustado)      99,194   1,29         1,750e10
        ===================== ========= ============ ==============

        O viés está sobretudo em ``T1``: com parâmetros constantes a
        frente sobe em UM passo de integração (``T1 = 0`` na resolução
        de ``Δt``, qualquer que seja o comprimento do cabo), enquanto o
        modelo dependente da frequência produz frente de 1,29 µs. Em
        ``dv/dt`` a diferença é de −12,5 % contra o Bergeron sem perdas
        e de −3,5 % contra o Bergeron com perdas concentradas.
        """
        dt = 5.0e-9
        # Perdas deliberadamente altas para tornar o efeito mensurável em
        # 500 m; com R' = 0,1 mΩ/m o cabo é quase sem perdas.
        data = _cabo_data(resistance=2.0e-2)
        modelo = ModalLineModel.fit(data, n_poles_yc=8, n_poles_a=12)
        zc = 1.0 / modelo.y_c.d
        tau = modelo.travel_time_s

        jm = JMartiLine("L", "k", "m", model=modelo)
        t_j, _, vm_j, _ = _degrau(
            jm, dt=dt, t_end=3.0 * tau, r_source=zc, r_load=1.0e12
        )
        berg = BergeronLine(
            "L",
            "k",
            "m",
            surge_impedance_ohm=zc,
            travel_time_s=tau,
            resistance_ohm=2.0e-2 * CABO_ELL,
        )
        t_b, _, vm_b, _ = _degrau(
            berg, dt=dt, t_end=3.0 * tau, r_source=zc, r_load=1.0e12
        )

        t1_j, dvdt_j = _tempo_de_frente(t_j, vm_j)
        t1_b, dvdt_b = _tempo_de_frente(t_b, vm_b)
        assert math.isfinite(t1_j) and math.isfinite(t1_b)
        assert dvdt_j > 0.0 and dvdt_b > 0.0

        # (1) O Bergeron entrega uma frente ao menos tão íngreme quanto a
        #     do JMarti: com parâmetros constantes só a interpolação de
        #     histórico amortece a frente, e não há dispersão física.
        assert dvdt_b >= dvdt_j * (1.0 - 1.0e-9)
        # (2) A frente do JMarti é ao menos tão larga quanto a do
        #     Bergeron.
        assert t1_j >= t1_b
        # (3) A diferença é MENSURÁVEL — se fosse nula, o modelo
        #     dependente da frequência não estaria fazendo nada.
        variacao_dvdt = (dvdt_b - dvdt_j) / dvdt_b
        assert variacao_dvdt > 1.0e-3, (
            f"dv/dt Bergeron = {dvdt_b:.4e} V/s, JMarti = {dvdt_j:.4e} V/s, "
            f"diferença relativa = {variacao_dvdt:.4%}; T1 Bergeron = "
            f"{t1_b:.4e} s, JMarti = {t1_j:.4e} s"
        )
        # (4) A DISPERSÃO é o efeito qualitativo: com parâmetros
        #     constantes a frente sobe em UM passo (T1 = 0 na resolução
        #     de Δt), enquanto com dependência de frequência ela passa a
        #     ter tempo de frente mensurável.
        assert t1_b == 0.0
        assert t1_j > 10.0 * dt
        # (5) O pico do Bergeron SEM PERDAS é a cota superior de estresse
        #     declarada em KNOWN_LIMITATIONS['emt_constant_parameter_line'].
        #     Note-se que o Bergeron COM perdas concentradas dá pico MENOR
        #     que o JMarti (97,58 V contra 99,19 V): a aproximação R/4,
        #     R/2, R/4 atenua também a componente de baixa frequência,
        #     que a linha com perdas distribuídas praticamente preserva.
        #     A cota superior vale para o modelo sem perdas, não para o
        #     Bergeron com perdas concentradas.
        berg_ideal = BergeronLine(
            "L", "k", "m", surge_impedance_ohm=zc, travel_time_s=tau
        )
        t_0, _, vm_0, _ = _degrau(
            berg_ideal, dt=dt, t_end=3.0 * tau, r_source=zc, r_load=1.0e12
        )
        t1_0, dvdt_0 = _tempo_de_frente(t_0, vm_0)
        assert float(np.max(vm_0)) >= float(np.max(vm_j))
        assert dvdt_0 > dvdt_j


class TestIntegracaoComOSolver:
    """Interface de componente, CDA, avisos e limites de uso."""

    def test_interface_identica_a_do_bergeron(self) -> None:
        """Mesma classe base e mesmo conjunto de métodos públicos."""
        jm = JMartiLine.constant_parameter(
            "L", "k", "m", surge_impedance_ohm=50.0, travel_time_s=1.0e-6
        )
        berg = BergeronLine(
            "L", "k", "m", surge_impedance_ohm=50.0, travel_time_s=1.0e-6
        )
        assert isinstance(jm, Component) and isinstance(berg, Component)
        assert jm.n_branches() == berg.n_branches() == 2
        for metodo in (
            "stamp_matrix",
            "stamp_rhs",
            "commit",
            "prepare",
            "reset",
            "branch_voltage",
            "branch_current",
            "topology_signature",
        ):
            assert callable(getattr(jm, metodo))
        assert jm.topology_signature() is None
        with pytest.raises(ValueError, match="terminal inválido"):
            jm.branch_voltage(2)
        with pytest.raises(ValueError, match="terminal inválido"):
            jm.branch_current(2)

    def test_matriz_invariante_nos_meios_passos_do_cda(self) -> None:
        """O CDA não força refatoração — condutância independente de ``h``.

        É a razão de projeto do esquema híbrido de recursão: o solver não
        reavalia a topologia entre os dois meios-passos, de modo que uma
        condutância dependente do passo estamparia matriz errada.
        """
        modelo = ModalLineModel.fit(_cabo_data(), n_poles_yc=6, n_poles_a=8)
        ckt = Circuit("cda")
        ckt.add(VoltageSource("E", "1", "gnd", amplitude_V=100.0, frequency_Hz=60.0))
        ckt.add(Resistor("R", "1", "2", 0.5))
        ckt.add(JMartiLine("L", "2", "3", model=modelo))
        sw = ckt.add(Switch("S", "3", "4", closed=True))
        ckt.add(Inductor("Lm", "4", "gnd", 5.0e-3))
        solver = Solver(ckt, dt=1.0e-6, cda_enabled=True)
        probe = solver.add_probe(NodeVoltageProbe("v3", "3"))
        res = solver.run(
            t_end=2.0e-2, controllers=(TimedSwitchController(sw, open_time_s=1.0e-2),)
        )
        assert res.cda_events >= 1
        # Uma fatoração para a topologia fechada, outra para a aberta.
        assert res.factorizations == 2
        v = np.asarray(probe.values)
        assert np.all(np.isfinite(v))

    def test_avisa_atraso_menor_que_o_passo(self, caplog) -> None:
        """``τ < Δt`` é sinalizado, como no Bergeron."""
        jm = JMartiLine.constant_parameter(
            "L", "k", "m", surge_impedance_ohm=50.0, travel_time_s=1.0e-8
        )
        with caplog.at_level("WARNING"):
            jm.prepare(1.0e-6)
        assert any("menor que o passo" in r.message for r in caplog.records)

    def test_partida_em_regime_permanente_nao_e_suportada(self) -> None:
        """``init='steady_state'`` recusa a linha JMarti explicitamente."""
        ckt = Circuit("regime")
        ckt.add(VoltageSource("E", "1", "gnd", amplitude_V=100.0, frequency_Hz=60.0))
        ckt.add(Resistor("R", "1", "k", 0.5))
        ckt.add(
            JMartiLine.constant_parameter(
                "L", "k", "m", surge_impedance_ohm=50.0, travel_time_s=1.0e-6
            )
        )
        ckt.add(Resistor("Rl", "m", "gnd", 50.0))
        solver = Solver(ckt, dt=1.0e-6, init="steady_state")
        with pytest.raises(UnsupportedComponentError):
            solver.run(t_end=1.0e-3)

    def test_validacao_de_construcao_do_componente(self) -> None:
        """Nós coincidentes e modelo de tipo errado são recusados."""
        modelo = ModalLineModel.constant_parameter(
            surge_impedance_ohm=50.0, travel_time_s=1.0e-6
        )
        with pytest.raises(JMartiError, match="mesmo nó"):
            JMartiLine("L", "k", "k", model=modelo)
        with pytest.raises(JMartiError, match="ModalLineModel"):
            JMartiLine("L", "k", "m", model=object())  # type: ignore[arg-type]

    def test_reset_devolve_a_linha_ao_repouso(self) -> None:
        """Reexecutar o solver reproduz exatamente a mesma série."""
        jm = JMartiLine.constant_parameter(
            "L", "k", "m", surge_impedance_ohm=50.0, travel_time_s=1.0e-6
        )
        ckt = Circuit("reset")
        ckt.add(
            VoltageSource(
                "E", "s", "gnd", amplitude_V=0.0, frequency_Hz=0.0, dc_offset_V=100.0
            )
        )
        ckt.add(Resistor("Rs", "s", "k", 50.0))
        ckt.add(jm)
        ckt.add(Resistor("Rl", "m", "gnd", 1.0e9))
        solver = Solver(ckt, dt=1.0e-8)
        probe = solver.add_probe(NodeVoltageProbe("v_m", "m"))
        solver.run(t_end=5.0e-6)
        primeira = np.asarray(probe.values).copy()
        solver.run(t_end=5.0e-6)
        assert np.array_equal(primeira, np.asarray(probe.values))


class TestDecomposicaoModal:
    """Transformação modal real e constante e a linha multifásica."""

    def test_clarke_e_ortonormal(self) -> None:
        """``T_v`` ortonormal ⇒ ``T_i = T_v`` e ``T_vᵀT_v = I``."""
        tr = clarke_transform(3)
        assert tr.n == 3
        assert np.allclose(tr.t_v.T @ tr.t_v, np.eye(3), atol=1.0e-12)
        assert np.allclose(tr.t_i, tr.t_v, atol=1.0e-12)
        assert np.allclose(tr.t_v[:, 0], np.ones(3) / math.sqrt(3.0))

    def test_valida_matriz_modal(self) -> None:
        """Matriz não quadrada ou singular é recusada."""
        with pytest.raises(JMartiError, match="quadrada"):
            ModalTransform(np.ones((2, 3)))
        with pytest.raises(JMartiError, match="singular"):
            ModalTransform(np.ones((2, 2)))
        with pytest.raises(JMartiError, match="condutâncias modais"):
            clarke_transform(3).conductance_block([1.0, 2.0])

    def test_modos_identicos_equivalem_a_linhas_independentes(self) -> None:
        """Com modos iguais e ``T`` ortonormal as fases se desacoplam.

        ``T_i·diag(g)·T_v⁻¹ = g·(T_vT_vᵀ)⁻¹ = g·I`` — o bloco vira
        diagonal e a linha modal reproduz três linhas monofásicas
        [CÁLCULO PRÓPRIO].
        """
        dt = 1.0e-8
        tau = 2.0e-6
        zc = 50.0
        modelos = [
            ModalLineModel.constant_parameter(
                surge_impedance_ohm=zc, travel_time_s=tau
            )
            for _ in range(3)
        ]
        modal = ModalJMartiLine(
            "ml",
            ("a", "b", "c"),
            ("x", "y", "z"),
            models=modelos,
            transform=clarke_transform(3),
        )
        ckt_m = Circuit("modal")
        ckt_m.add(modal)
        ckt_i = Circuit("independente")
        for i, (n1, n2) in enumerate(zip("abc", "xyz")):
            for ckt in (ckt_m, ckt_i):
                ckt.add(
                    VoltageSource(
                        f"E{i}",
                        f"s{n1}",
                        "gnd",
                        amplitude_V=0.0,
                        frequency_Hz=0.0,
                        dc_offset_V=100.0 * (i + 1),
                    )
                )
                ckt.add(Resistor(f"R{i}", f"s{n1}", n1, zc))
                ckt.add(Resistor(f"Rl{i}", n2, "gnd", 1.0e9))
            ckt_i.add(
                JMartiLine.constant_parameter(
                    f"L{i}", n1, n2, surge_impedance_ohm=zc, travel_time_s=tau
                )
            )
        sol_m = Solver(ckt_m, dt=dt)
        sol_i = Solver(ckt_i, dt=dt)
        pm = [sol_m.add_probe(NodeVoltageProbe(f"m{n}", n)) for n in "xyz"]
        pi = [sol_i.add_probe(NodeVoltageProbe(f"i{n}", n)) for n in "xyz"]
        sol_m.run(t_end=8.0e-6)
        sol_i.run(t_end=8.0e-6)
        for a, b in zip(pm, pi):
            assert np.max(
                np.abs(np.asarray(a.values) - np.asarray(b.values))
            ) < 1.0e-9

    def test_valida_dimensoes_da_linha_modal(self) -> None:
        """Nós, modelos e transformação devem concordar em quantidade."""
        modelo = ModalLineModel.constant_parameter(
            surge_impedance_ohm=50.0, travel_time_s=1.0e-6
        )
        with pytest.raises(JMartiError, match="nós em k"):
            ModalJMartiLine(
                "ml",
                ("a", "b"),
                ("x",),
                models=[modelo, modelo],
                transform=clarke_transform(2),
            )
        with pytest.raises(JMartiError, match="modelos modais"):
            ModalJMartiLine(
                "ml",
                ("a", "b"),
                ("x", "y"),
                models=[modelo],
                transform=clarke_transform(2),
            )
        with pytest.raises(JMartiError, match="modos para"):
            ModalJMartiLine(
                "ml",
                ("a", "b"),
                ("x", "y"),
                models=[modelo, modelo],
                transform=clarke_transform(3),
            )
        linha = ModalJMartiLine(
            "ml",
            ("a", "b"),
            ("x", "y"),
            models=[modelo, modelo],
            transform=clarke_transform(2),
        )
        assert linha.n_branches() == 4
        with pytest.raises(ValueError, match="terminal inválido"):
            linha.branch_voltage(4)
        with pytest.raises(ValueError, match="terminal inválido"):
            linha.branch_current(9)


class TestCasoDeManobra:
    """Seleção do modelo de linha no caso do Documento A."""

    def test_caso_aceita_jmarti_e_muda_apenas_o_modelo(self) -> None:
        """``with_cable_model('jmarti')`` monta o caso com JMartiLine."""
        from app.simulation.emt.cases.motor_switching import (
            CABLE_MODELS,
            MotorSwitchingCase,
        )

        caso = MotorSwitchingCase().with_cable_model("jmarti")
        assert caso.cable_upstream.model == "jmarti"
        assert caso.cable_downstream.model == "jmarti"
        modelo = caso.build()
        linhas = [
            c for c in modelo.circuit.components if isinstance(c, (JMartiLine, BergeronLine))
        ]
        assert linhas and all(isinstance(c, JMartiLine) for c in linhas)
        base = MotorSwitchingCase().build()
        assert len(base.circuit.components) == len(modelo.circuit.components)
        assert set(CABLE_MODELS) == {"bergeron", "jmarti"}

    def test_caso_valida_modelo_desconhecido(self) -> None:
        """Nome de modelo inválido é recusado na construção."""
        from app.simulation.emt.cases.motor_switching import (
            CableParameters,
            MotorSwitchingCase,
        )

        with pytest.raises(ValueError, match="model deve ser"):
            CableParameters(model="universal")
        with pytest.raises(ValueError, match="model deve ser"):
            MotorSwitchingCase().with_cable_model("universal")

    def test_caso_expoe_tabelas_e_modelo_modal(self) -> None:
        """O cabo do caso sabe gerar suas próprias tabelas e ajuste."""
        from app.simulation.emt.cases.motor_switching import CableParameters

        cabo = CableParameters()
        dados = cabo.frequency_data("cabo_up")
        assert dados.n_samples > 100
        modal = cabo.modal_model("cabo_up")
        assert modal.travel_time_s == pytest.approx(cabo.travel_time_s, rel=1.0e-5)
        assert modal.y_c.rms_error < float(cabo.fit_tolerance)


class TestAuditoria:
    """Catálogo de limitações e superfície pública do pacote."""

    def test_limitacoes_do_jmarti_estao_no_catalogo_do_kernel(self) -> None:
        """Toda chave ``emt_jmarti_`` aparece em ``KNOWN_LIMITATIONS``."""
        assert JMARTI_LIMITATIONS
        for chave, texto in JMARTI_LIMITATIONS.items():
            assert chave.startswith("emt_jmarti_")
            assert chave in KNOWN_LIMITATIONS
            assert KNOWN_LIMITATIONS[chave] == texto
            assert len(texto) > 120

    def test_api_publica_exporta_o_novo_modelo(self) -> None:
        """Os nomes do modelo dependente da frequência estão em ``__all__``."""
        for nome in (
            "JMartiLine",
            "ModalJMartiLine",
            "ModalTransform",
            "ModalLineModel",
            "LineFrequencyData",
            "RationalFit",
            "vector_fit",
            "minimum_phase_angle",
            "estimate_time_delay",
            "clarke_transform",
            "JMARTI_LIMITATIONS",
        ):
            assert nome in EMT_ALL
        import app.simulation.emt as emt

        for nome in EMT_ALL:
            assert hasattr(emt, nome), nome
