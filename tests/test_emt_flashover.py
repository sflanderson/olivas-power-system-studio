"""
Testes da disrupção da isolação como evento terminal.

Divisão:

1. Os níveis normativos, conferidos contra as tabelas do fichamento.
2. A máquina de estados do caminho de disrupção.
3. O comportamento no caso de referência: a cauda de escalada é
   interrompida por um evento contado, e não integrada como estresse.
4. As limitações declaradas — em especial a distinção entre nível de
   SUPORTABILIDADE e tensão de RUPTURA, que é o que o módulo inteiro
   depende de não confundir.

Fontes dos níveis: IEC 60034-15:2009, Tabela 1 (amostra oficial iTeh) e
IEC CDV 60034-15 (2/2199/CDV, 2024), Tabela 1 — provisório. Transcritos e
verificados em
``docs/research/rul_isolamento/01_ETAPA1_monitoramento_degradacao_isolamento.md``,
§4.1.
"""

from __future__ import annotations

import numpy as np
import pytest

from app.simulation.emt.circuit import Circuit, Solver
from app.simulation.emt.components import Resistor, VoltageSource
from app.simulation.emt.flashover import (
    DEFAULT_ARC_RESISTANCE_OHM,
    EDITION_2009,
    EDITION_2025_CDV,
    FLASHOVER_CONDUCTING,
    FLASHOVER_IDLE,
    KNOWN_LIMITATIONS,
    TURN_FRACTION_2009,
    InsulationFlashover,
    build_flashover_path,
    iec_60034_15_levels,
    three_phase_flashover,
)

#: Pico fase-terra do sistema de 4,16 kV [V].
V_BASE_V = 4160.0 / np.sqrt(3.0) * np.sqrt(2.0)


# ---------------------------------------------------------------------------
# 1. Os níveis normativos
# ---------------------------------------------------------------------------


class TestNiveisNormativos:
    def test_edicao_2009_e_a_formula_da_tabela_1(self):
        """``U_P = 4U_N + 5 kV`` e ``U'_P = 0,65 U_P``."""
        sli, sfi = iec_60034_15_levels(4160.0)
        assert sli == pytest.approx(21.64e3, rel=1e-12)
        assert sfi == pytest.approx(14.066e3, rel=1e-4)
        assert sfi / sli == pytest.approx(TURN_FRACTION_2009, rel=1e-12)

    @pytest.mark.parametrize(
        "u_n, sli_kV, sfi_kV",
        [(4000.0, 16.33, 11.43), (6600.0, 26.94, 18.86), (13800.0, 56.34, 39.44)],
    )
    def test_edicao_2025_reproduz_a_tabela_do_cdv(self, u_n, sli_kV, sfi_kV):
        """Verificação de forma: ``5√(2/3)U_N`` e ``3,5√(2/3)U_N``.

        A tabela do CDV traz 16,3/11,4; 26,9/18,9; 56,3/39,4 — os valores
        calculados coincidem em três dígitos [CÁLCULO PRÓPRIO; ver o
        fichamento normativo, §4.1].
        """
        sli, sfi = iec_60034_15_levels(u_n, edition=EDITION_2025_CDV)
        assert sli / 1e3 == pytest.approx(sli_kV, abs=0.01)
        assert sfi / 1e3 == pytest.approx(sfi_kV, abs=0.01)

    def test_edicao_2025_tem_pisos(self):
        sli, sfi = iec_60034_15_levels(100.0, edition=EDITION_2025_CDV)
        assert sli == pytest.approx(8.0e3)
        assert sfi == pytest.approx(5.6e3)

    def test_nivel_reforcado_soma_os_acrescimos_do_cdv(self):
        """Padrão + 15 kV (SLI) e + 11 kV (SFI), limitado a 2× o padrão."""
        base = iec_60034_15_levels(4160.0, edition=EDITION_2025_CDV)
        ref = iec_60034_15_levels(4160.0, edition=EDITION_2025_CDV, enhanced=True)
        # 16,98 kV: 2× = 33,96 > 16,98 + 15 = 31,98, logo vale a soma.
        assert ref[0] == pytest.approx(base[0] + 15.0e3, rel=1e-9)
        assert ref[1] == pytest.approx(base[1] + 11.0e3, rel=1e-9)

    def test_limite_de_duas_vezes_o_padrao_morde_em_tensao_baixa(self):
        base = iec_60034_15_levels(100.0, edition=EDITION_2025_CDV)
        ref = iec_60034_15_levels(100.0, edition=EDITION_2025_CDV, enhanced=True)
        assert ref[0] == pytest.approx(2.0 * base[0])
        assert ref[1] == pytest.approx(2.0 * base[1])

    def test_para_4_16_kV_o_envelope_em_pu(self):
        """6,37 pu na isolação principal e 4,14 pu entre espiras."""
        sli, sfi = iec_60034_15_levels(4160.0)
        assert sli / V_BASE_V == pytest.approx(6.37, abs=0.01)
        assert sfi / V_BASE_V == pytest.approx(4.14, abs=0.01)

    def test_a_edicao_2025_e_mais_severa_em_4_16_kV(self):
        """Abaixo de ~12,6 kV a edição 2025 fixa níveis MENORES."""
        a = iec_60034_15_levels(4160.0)
        b = iec_60034_15_levels(4160.0, edition=EDITION_2025_CDV)
        assert b[0] < a[0] and b[1] < a[1]

    @pytest.mark.parametrize("u", [0.0, -1.0, float("nan")])
    def test_tensao_invalida_levanta(self, u):
        with pytest.raises(ValueError, match="rated_voltage_V"):
            iec_60034_15_levels(u)

    def test_edicao_desconhecida_levanta(self):
        with pytest.raises(ValueError, match="edition"):
            iec_60034_15_levels(4160.0, edition="1990")

    def test_reforcado_na_edicao_2009_levanta(self):
        with pytest.raises(ValueError, match="não define nível reforçado"):
            iec_60034_15_levels(4160.0, edition=EDITION_2009, enhanced=True)


# ---------------------------------------------------------------------------
# 2. A máquina de estados
# ---------------------------------------------------------------------------


class TestCaminhoDeDisrupcao:
    @staticmethod
    def _bancada(amplitude_V: float, threshold_V: float, r_fonte: float = 100.0):
        """Fonte senoidal alimentando o nó monitorado por um resistor."""
        caminho = build_flashover_path(
            "d", "n", "gnd", threshold_V=threshold_V
        )
        ckt = Circuit("disrupcao")
        ckt.extend(
            [
                VoltageSource(
                    "e", "s", "gnd", amplitude_V=amplitude_V, frequency_Hz=60.0,
                    phase_reference="cos",
                ),
                Resistor("r", "s", "n", r_fonte),
                Resistor("carga", "n", "gnd", 1.0e5),
            ]
        )
        ckt.extend(caminho.components)
        solver = Solver(ckt, dt=1.0e-6, init="zero", cda_at_start=False)
        solver.run(t_end=20.0e-3, controllers=[caminho.controller])
        return caminho.controller

    def test_abaixo_do_limiar_nao_dispara(self):
        ctrl = self._bancada(amplitude_V=10.0e3, threshold_V=21.64e3)
        assert ctrl.count == 0
        assert ctrl.state == FLASHOVER_IDLE
        assert ctrl.result.energy_J == 0.0

    def test_acima_do_limiar_dispara_e_registra(self):
        ctrl = self._bancada(amplitude_V=30.0e3, threshold_V=21.64e3)
        assert ctrl.count > 0
        assert len(ctrl.result.times_s) == ctrl.count
        assert len(ctrl.result.voltages_V) == ctrl.count
        assert ctrl.result.peak_voltage_V >= 21.64e3
        assert ctrl.result.energy_J > 0.0

    def test_dispara_nos_dois_semiciclos(self):
        """A disrupção não tem polaridade."""
        ctrl = self._bancada(amplitude_V=30.0e3, threshold_V=21.64e3)
        sinais = {np.sign(v) for v in ctrl.result.voltages_V}
        assert sinais == {-1.0, 1.0}

    def test_arco_se_extingue_e_o_caminho_rearma(self):
        """Um arco no ar se apaga na passagem por zero e pode reacender."""
        ctrl = self._bancada(amplitude_V=30.0e3, threshold_V=21.64e3)
        # 20 ms a 60 Hz são 1,2 ciclos: dois semiciclos completos acima do
        # limiar, logo pelo menos duas disrupções.
        assert ctrl.count >= 2

    def test_teto_de_eventos_trava_o_caminho(self, caplog):
        caminho = build_flashover_path(
            "d", "n", "gnd", threshold_V=1.0e3, max_events=1
        )
        ckt = Circuit("teto")
        ckt.extend(
            [
                VoltageSource(
                    "e", "s", "gnd", amplitude_V=30.0e3, frequency_Hz=60.0,
                    phase_reference="cos",
                ),
                Resistor("r", "s", "n", 100.0),
                Resistor("carga", "n", "gnd", 1.0e5),
            ]
        )
        ckt.extend(caminho.components)
        solver = Solver(ckt, dt=1.0e-6, init="zero", cda_at_start=False)
        with caplog.at_level("WARNING"):
            solver.run(t_end=20.0e-3, controllers=[caminho.controller])
        assert caminho.controller.count == 1
        assert any("teto de" in r.message for r in caplog.records)

    def test_reset_zera_o_registro(self):
        ctrl = self._bancada(amplitude_V=30.0e3, threshold_V=21.64e3)
        assert ctrl.count > 0
        ctrl.reset()
        assert ctrl.count == 0
        assert ctrl.state == FLASHOVER_IDLE
        assert ctrl.result.times_s == []

    def test_primeira_disrupcao_e_registrada_em_log(self, caplog):
        with caplog.at_level("WARNING"):
            self._bancada(amplitude_V=30.0e3, threshold_V=21.64e3)
        mensagens = [r.message for r in caplog.records]
        assert any("DISRUPÇÃO" in m for m in mensagens)
        assert any("TERMINAL" in m for m in mensagens)


class TestConstrucao:
    def test_tres_fases(self):
        caminhos = three_phase_flashover(
            "d", ("a", "b", "c"), "gnd", threshold_V=21.64e3
        )
        assert [c.name for c in caminhos] == ["d_a", "d_b", "d_c"]
        for c in caminhos:
            assert c.resistor.resistance_ohm == DEFAULT_ARC_RESISTANCE_OHM
            assert len(c.components) == 2

    def test_nome_vazio_levanta(self):
        with pytest.raises(ValueError, match="nome não vazio"):
            build_flashover_path("", "n", "gnd", threshold_V=1.0e3)

    def test_lista_de_nos_vazia_levanta(self):
        with pytest.raises(ValueError, match="pelo menos um nó"):
            three_phase_flashover("d", (), "gnd", threshold_V=1.0e3)

    @pytest.mark.parametrize("r", [0.0, -1.0, float("inf")])
    def test_resistencia_de_arco_invalida_levanta(self, r):
        with pytest.raises(ValueError, match="arc_resistance_ohm"):
            build_flashover_path(
                "d", "n", "gnd", threshold_V=1.0e3, arc_resistance_ohm=r
            )

    @pytest.mark.parametrize(
        "kwargs",
        [
            {"threshold_V": 0.0},
            {"threshold_V": float("nan")},
            {"holding_current_A": 0.0},
            {"max_events": -1},
        ],
    )
    def test_parametros_do_controlador_invalidos_levantam(self, kwargs):
        from app.simulation.emt.components import Resistor as R
        from app.simulation.emt.components import Switch

        base = dict(threshold_V=1.0e3)
        base.update(kwargs)
        with pytest.raises(ValueError):
            InsulationFlashover(
                Switch("sw", "n", "m", closed=False),
                R("arc", "m", "gnd", 1.0),
                **base,
            )

    def test_componentes_de_tipo_errado_levantam(self):
        from app.simulation.emt.components import Resistor as R
        from app.simulation.emt.components import Switch

        with pytest.raises(ValueError, match="Switch"):
            InsulationFlashover(
                R("x", "n", "m", 1.0), R("arc", "m", "gnd", 1.0), threshold_V=1.0e3
            )
        with pytest.raises(ValueError, match="Resistor"):
            InsulationFlashover(
                Switch("sw", "n", "m", closed=False),
                Switch("sw2", "m", "gnd", closed=False),
                threshold_V=1.0e3,
            )


# ---------------------------------------------------------------------------
# 3. No caso de referência
# ---------------------------------------------------------------------------


class TestNoCasoDeReferencia:
    #: A pior realização da varredura de 150, transcrita de
    #: ``anexos/dados/varredura_vcb_n150.json``.
    T_SEP = 0.014686548756377423
    PARAMETROS = (
        (2.711434269810338, 459.75322834158004, 44.25892757065691),
        (2.83534334843704, 456.84415739510047, 7.017730425986475),
        (5.405288719190455, 198.90601064862238, 46.884966495674895),
    )

    @classmethod
    def _amostras(cls):
        from app.simulation.emt.vcb_scenarios import VcbSample

        return tuple(
            VcbSample("literatura", corte, didt, rrds, 0.0, cls.T_SEP, None)
            for corte, didt, rrds in cls.PARAMETROS
        )

    def test_regime_permanente_nao_disrupta(self):
        from app.simulation.emt.cases.atp_reference import AtpReferenceCase

        sli, _sfi = iec_60034_15_levels(4160.0)
        modelo = AtpReferenceCase(
            with_snubber=False, motor_flashover_level_V=sli
        ).build()
        modelo.run()
        assert len(modelo.flashovers) == 3
        assert all(f.controller.count == 0 for f in modelo.flashovers)

    def test_a_escalada_atravessa_o_envelope_normativo(self):
        """A leitura que importa: a realização é FALHA, não estresse.

        Sem disrupção o motor calcula 77,5 pu — tensão que a máquina não
        suportaria. Com o limiar no envelope da IEC 60034-15, a escalada
        atravessa o nível e o evento é contado; o pico fica logo acima do
        limiar, com a ultrapassagem de um passo antes do fechamento.
        """
        from app.simulation.emt.cases.atp_reference import AtpReferenceCase

        sli, _sfi = iec_60034_15_levels(4160.0)
        sem = AtpReferenceCase(
            with_snubber=False, vcb_samples=self._amostras()
        ).build()
        sem.run()
        pico_sem = max(sem.motor_voltage_summary().values()) * 1.0e3 / V_BASE_V

        com = AtpReferenceCase(
            with_snubber=False,
            vcb_samples=self._amostras(),
            motor_flashover_level_V=sli,
        ).build()
        com.run()
        pico_com = max(com.motor_voltage_summary().values()) * 1.0e3 / V_BASE_V
        eventos = sum(f.controller.count for f in com.flashovers)

        assert pico_sem > 50.0
        assert eventos >= 1
        # O pico grampeado ultrapassa o limiar — o caminho fecha um passo
        # depois do cruzamento e a frente é íngreme —, mas fica uma ordem
        # de grandeza abaixo do valor sem grampo. A ultrapassagem medida
        # sobre as oito realizações em escalada vai de 1,04 a 1,87 vezes o
        # limiar; ver ``emt_flashover_clamped_waveform_is_not_a_result``.
        assert pico_com >= sli / V_BASE_V
        assert pico_com < 0.3 * pico_sem

    def test_disrupcao_ocorre_em_menos_de_um_milissegundo_apos_a_separacao(self):
        """Quando a escalada começa, o envelope cai depressa."""
        from app.simulation.emt.cases.atp_reference import AtpReferenceCase

        sli, _sfi = iec_60034_15_levels(4160.0)
        modelo = AtpReferenceCase(
            with_snubber=False,
            vcb_samples=self._amostras(),
            motor_flashover_level_V=sli,
        ).build()
        modelo.run()
        instantes = [
            t
            for f in modelo.flashovers
            for t in f.controller.result.times_s
        ]
        assert instantes
        assert min(instantes) - self.T_SEP < 1.0e-3

    def test_nivel_invalido_levanta(self):
        from app.simulation.emt.cases.atp_reference import AtpReferenceCase

        with pytest.raises(ValueError, match="motor_flashover_level_V"):
            AtpReferenceCase(motor_flashover_level_V=0.0)

    def test_sem_o_parametro_o_caso_nao_tem_caminho_de_disrupcao(self):
        from app.simulation.emt.cases.atp_reference import AtpReferenceCase

        modelo = AtpReferenceCase(with_snubber=False).build()
        assert modelo.flashovers == ()

    def test_para_raios_evita_a_disrupcao(self):
        """A comparação que fecha o argumento de mitigação.

        Com o para-raios a mesma realização não chega ao envelope; sem
        ele, chega. É a diferença entre uma manobra que envelhece a
        isolação e uma que a rompe.
        """
        from app.simulation.emt.cases.atp_reference import AtpReferenceCase

        sli, _sfi = iec_60034_15_levels(4160.0)
        modelo = AtpReferenceCase(
            with_snubber=False,
            vcb_samples=self._amostras(),
            motor_flashover_level_V=sli,
            motor_arrester_system_voltage_V=4160.0,
        ).build()
        modelo.run()
        assert sum(f.controller.count for f in modelo.flashovers) == 0
        pico = max(modelo.motor_voltage_summary().values()) * 1.0e3 / V_BASE_V
        assert pico < sli / V_BASE_V


# ---------------------------------------------------------------------------
# 4. Limitações
# ---------------------------------------------------------------------------


def test_limitacoes_declaradas_e_sem_colisao():
    from app.simulation.emt import KNOWN_LIMITATIONS as KERNEL
    from app.simulation.emt.arrester import KNOWN_LIMITATIONS as MOA
    from app.simulation.emt.nonlinear import KNOWN_LIMITATIONS as NAO_LINEAR

    chave = "emt_flashover_withstand_is_not_breakdown"
    assert chave in KNOWN_LIMITATIONS
    texto = KNOWN_LIMITATIONS[chave]
    # A distinção de que tudo depende, dita explicitamente.
    assert "SUPORTABILIDADE DE ENSAIO" in texto and "ruptura" in texto
    assert "ANTICONSERVADOR" in texto
    assert not set(KNOWN_LIMITATIONS) & (set(KERNEL) | set(MOA) | set(NAO_LINEAR))
    for k, t in KNOWN_LIMITATIONS.items():
        assert k.startswith("emt_flashover_")
        assert len(t) > 80


# ---------------------------------------------------------------------------
# 5. Convergência em passo da cauda
# ---------------------------------------------------------------------------


class TestConvergenciaEmPassoDaCauda:
    """A cadeia de decisões que leva à travessia não é convergida.

    A escalada é uma sequência de decisões de limiar sobre o ``di/dt`` nos
    zeros de alta frequência. Para realizações marginais essa cadeia
    diverge com o passo, e o desfecho — escalar ou não — muda. O que se
    fixa aqui é o FATO, para que nenhum resultado de realização individual
    seja lido como convergido.
    """

    #: Realização que escala nos dois passos [dados da varredura de 150].
    ROBUSTA = (
        0.014686548756377423,
        (
            (2.711434269810338, 459.75322834158004, 44.25892757065691),
            (2.83534334843704, 456.84415739510047, 7.017730425986475),
            (5.405288719190455, 198.90601064862238, 46.884966495674895),
        ),
    )

    @staticmethod
    def _pico_e_reignicoes(t_sep, parametros, dt_s):
        from app.simulation.emt.cases.atp_reference import AtpReferenceCase
        from app.simulation.emt.vcb_scenarios import VcbSample

        amostras = tuple(
            VcbSample("literatura", corte, didt, rrds, 0.0, t_sep, None)
            for corte, didt, rrds in parametros
        )
        modelo = AtpReferenceCase(
            with_snubber=False, vcb_samples=amostras, dt_s=dt_s
        ).build()
        modelo.run()
        return (
            max(modelo.motor_voltage_summary().values()) * 1.0e3 / V_BASE_V,
            sum(modelo.reignition_counts.values()),
        )

    def test_realizacao_robusta_escala_nos_dois_passos(self):
        """O envelope da escalada, quando existe, é insensível ao passo."""
        t_sep, par = self.ROBUSTA
        p1, r1 = self._pico_e_reignicoes(t_sep, par, 1.0e-6)
        p2, r2 = self._pico_e_reignicoes(t_sep, par, 2.0e-7)
        assert p1 > 50.0 and p2 > 50.0
        assert p2 == pytest.approx(p1, rel=0.15)
        assert r1 > 50 and r2 > 50

    def test_a_limitacao_de_convergencia_esta_declarada(self):
        chave = "emt_flashover_marginal_realizations_are_not_step_converged"
        assert chave in KNOWN_LIMITATIONS
        texto = KNOWN_LIMITATIONS[chave]
        assert "0,2 µs" in texto
        assert "estatística de população" in texto
        # A medição que sustenta a afirmação, e não só a afirmação.
        assert "8 de 150" in texto

    def test_a_limitacao_do_pico_grampeado_esta_declarada(self):
        chave = "emt_flashover_clamped_waveform_is_not_a_result"
        assert chave in KNOWN_LIMITATIONS
        assert "CONTAGEM" in KNOWN_LIMITATIONS[chave]


class TestPassoAdequado:
    """Qual passo o caso exige, medido e não estipulado.

    Vinte realizações sem escalada em três passos deram desvio relativo
    mediano de 20,89 % entre 1,0 e 0,2 µs, e de 2,70 % entre 0,2 e
    0,05 µs [CÁLCULO PRÓPRIO; ver
    ``09_PARA_RAIOS_E_CRITERIO_DE_ACEITACAO.md``, §7.1]. Logo 0,2 µs é o
    passo adequado e 1 µs não é.

    O teste executa apenas UMA realização, para custo aceitável na suíte;
    o que ele fixa é a direção e a ordem de grandeza do efeito.
    """

    T_SEP = 0.014686548756377423

    def test_um_microssegundo_subestima_o_pico(self):
        from app.simulation.emt.cases.atp_reference import AtpReferenceCase
        from app.simulation.emt.vcb_scenarios import VcbSample

        # Realização SEM escalada: o efeito medido é sobre o corpo da
        # distribuição, não sobre a cauda.
        amostras = tuple(
            VcbSample("literatura", 5.0, 300.0, 12.0, 0.0, self.T_SEP, None)
            for _ in range(3)
        )
        picos = []
        for dt in (1.0e-6, 2.0e-7):
            modelo = AtpReferenceCase(
                with_snubber=False, vcb_samples=amostras, dt_s=dt
            ).build()
            modelo.run()
            picos.append(
                max(modelo.motor_voltage_summary().values()) * 1.0e3 / V_BASE_V
            )
        assert picos[0] < 4.6 and picos[1] < 4.6, "a realização não deve escalar"
        assert picos[1] > picos[0], "refinar o passo eleva o pico"
        assert (picos[1] - picos[0]) / picos[0] > 0.05
