"""
Testes do para-raios de óxido metálico.

Divisão:

1. Os dados PUBLICADOS, transcritos sem alteração, e o expoente ajustado.
2. A qualidade da característica gerada — erro de interpolação em TENSÃO,
   que é a grandeza que importa num dispositivo de proteção.
3. O escalonamento para outra tensão de sistema e sua confrontação com o
   envelope da IEC 60034-15.
4. O comportamento no caso de referência: o para-raios não perturba o
   regime permanente e grampeia a escalada na faixa publicada.

Fontes dos valores: VOLLET, C.; DE METZ-NOBLAT, B. Vacuum circuit breaker
model: application case to motors switching. In: IPST 2007, Lyon, paper
07IPST106 — transcritos no levantamento
``docs/research/rul_isolamento/anexos/pesquisa/fisica_surtos_vcb_isolamento.md``,
§3.6.
"""

from __future__ import annotations

import numpy as np
import pytest

from app.simulation.emt.arrester import (
    KNOWN_LIMITATIONS,
    POINTS_PER_DECADE,
    VOLLET_BUS_ARRESTER,
    VOLLET_MOTOR_ARRESTER,
    ArresterPoints,
    MetalOxideArrester,
    characteristic_from_points,
    exponent_from_points,
    scale_for_system_voltage,
    three_phase_arrester,
)

#: Pico fase-terra do sistema de 4,16 kV [V] — base das conversões em pu.
V_BASE_V = 4160.0 / np.sqrt(3.0) * np.sqrt(2.0)

#: Envelope da IEC 60034-15:2009 para U_N = 4,16 kV [V]
#: [NORMA; ver docs/research/rul_isolamento/01_ETAPA1…md, §3].
IEC_UP_V = 21.64e3
IEC_UP_LINHA_V = 14.07e3


# ---------------------------------------------------------------------------
# 1. Os dados publicados
# ---------------------------------------------------------------------------


class TestDadosPublicados:
    def test_para_raios_do_motor_e_o_transcrito_de_vollet(self):
        p = VOLLET_MOTOR_ARRESTER
        assert (p.low_voltage_V, p.low_current_A) == (18.4e3, 0.1e-3)
        assert (p.high_voltage_V, p.high_current_A) == (36.8e3, 10.0e3)
        assert p.system_voltage_V == 11.0e3
        assert "Vollet" in p.source

    def test_para_raios_do_cubiculo_e_o_transcrito_de_vollet(self):
        p = VOLLET_BUS_ARRESTER
        assert (p.low_voltage_V, p.low_current_A) == (21.6e3, 3.0e-3)
        assert (p.high_voltage_V, p.high_current_A) == (76.9e3, 40.0e3)

    def test_expoente_ajustado_esta_na_ordem_de_grandeza_de_zno(self):
        a_motor = exponent_from_points(VOLLET_MOTOR_ARRESTER)
        a_barra = exponent_from_points(VOLLET_BUS_ARRESTER)
        assert a_motor == pytest.approx(26.58, abs=0.01)
        assert a_barra == pytest.approx(12.92, abs=0.01)
        for a in (a_motor, a_barra):
            assert 10.0 < a < 60.0

    def test_expoente_reproduz_os_dois_pontos(self):
        p = VOLLET_MOTOR_ARRESTER
        a = exponent_from_points(p)
        i = p.low_current_A * (p.high_voltage_V / p.low_voltage_V) ** a
        assert i == pytest.approx(p.high_current_A, rel=1e-12)

    @pytest.mark.parametrize(
        "campo",
        ["low_voltage_V", "low_current_A", "high_voltage_V", "high_current_A",
         "system_voltage_V"],
    )
    def test_valores_nao_positivos_levantam(self, campo):
        kwargs = dict(
            low_voltage_V=1.0,
            low_current_A=1.0e-3,
            high_voltage_V=2.0,
            high_current_A=1.0,
            system_voltage_V=1.0e3,
            source="teste",
        )
        kwargs[campo] = 0.0
        with pytest.raises(ValueError, match=campo):
            ArresterPoints(**kwargs)

    def test_pontos_nao_ordenados_levantam(self):
        base = dict(system_voltage_V=1.0e3, source="teste")
        with pytest.raises(ValueError, match="high_voltage_V"):
            ArresterPoints(
                low_voltage_V=2.0, low_current_A=1e-3,
                high_voltage_V=1.0, high_current_A=1.0, **base
            )
        with pytest.raises(ValueError, match="high_current_A"):
            ArresterPoints(
                low_voltage_V=1.0, low_current_A=1.0,
                high_voltage_V=2.0, high_current_A=0.5, **base
            )


# ---------------------------------------------------------------------------
# 2. A característica gerada
# ---------------------------------------------------------------------------


class TestCaracteristicaGerada:
    def test_passa_pelos_dois_pontos_publicados(self):
        p = VOLLET_MOTOR_ARRESTER
        c = characteristic_from_points(p)
        assert c.knee_voltage_V == pytest.approx(p.low_voltage_V, rel=1e-12)
        v_max, i_max = c.max_point
        assert v_max == pytest.approx(p.high_voltage_V, rel=1e-12)
        assert i_max == pytest.approx(p.high_current_A, rel=1e-12)

    @pytest.mark.parametrize(
        "pontos, limite",
        [(VOLLET_MOTOR_ARRESTER, 0.002), (VOLLET_BUS_ARRESTER, 0.004)],
    )
    def test_erro_de_interpolacao_em_tensao_e_pequeno(self, pontos, limite):
        """A grandeza que importa é a TENSÃO, não a corrente.

        O erro em corrente é enorme por construção — ``i`` é uma potência
        de expoente 13 a 27 de ``v`` —, e não diz nada sobre a qualidade
        da proteção. O que se mede aqui é quanto a tensão da curva por
        trechos se afasta da lei de potência para a mesma corrente.
        """
        a = exponent_from_points(pontos)
        c = characteristic_from_points(pontos)
        i_exata = np.logspace(
            np.log10(pontos.low_current_A), np.log10(pontos.high_current_A), 500
        )
        v_exata = pontos.low_voltage_V * (i_exata / pontos.low_current_A) ** (1.0 / a)
        i_pwl = np.array([c.current_A_at(v) for v in v_exata])
        erro_v = np.abs((i_pwl / i_exata) ** (1.0 / a) - 1.0)
        assert erro_v.max() < limite

    def test_densidade_maior_reduz_o_erro(self):
        p = VOLLET_MOTOR_ARRESTER
        a = exponent_from_points(p)
        i = np.logspace(np.log10(p.low_current_A), np.log10(p.high_current_A), 300)
        v = p.low_voltage_V * (i / p.low_current_A) ** (1.0 / a)
        erros = []
        for n in (1, 2, 4, 8):
            c = characteristic_from_points(p, points_per_decade=n)
            i_pwl = np.array([c.current_A_at(x) for x in v])
            erros.append(float(np.max(np.abs((i_pwl / i) ** (1.0 / a) - 1.0))))
        assert erros == sorted(erros, reverse=True)

    def test_densidade_adotada_e_quatro(self):
        assert POINTS_PER_DECADE == 4

    @pytest.mark.parametrize("kwargs", [{"scale": 0.0}, {"scale": -1.0},
                                        {"points_per_decade": 0}])
    def test_parametros_invalidos_levantam(self, kwargs):
        with pytest.raises(ValueError):
            characteristic_from_points(VOLLET_MOTOR_ARRESTER, **kwargs)


# ---------------------------------------------------------------------------
# 3. Escalonamento e envelope normativo
# ---------------------------------------------------------------------------


class TestEscalonamento:
    def test_escala_e_a_razao_das_tensoes_de_sistema(self):
        k = scale_for_system_voltage(VOLLET_MOTOR_ARRESTER, 4160.0)
        assert k == pytest.approx(4160.0 / 11.0e3, rel=1e-12)

    def test_escala_unitaria_no_sistema_de_origem(self):
        assert scale_for_system_voltage(VOLLET_MOTOR_ARRESTER, 11.0e3) == 1.0

    @pytest.mark.parametrize("u", [0.0, -1.0, float("nan")])
    def test_tensao_invalida_levanta(self, u):
        with pytest.raises(ValueError, match="system_voltage_V"):
            scale_for_system_voltage(VOLLET_MOTOR_ARRESTER, u)

    def test_escalonamento_preserva_a_margem_de_protecao(self):
        """A razão residual/joelho é invariante — é o que o escalonamento afirma."""
        c0 = characteristic_from_points(VOLLET_MOTOR_ARRESTER)
        k = scale_for_system_voltage(VOLLET_MOTOR_ARRESTER, 4160.0)
        c1 = characteristic_from_points(VOLLET_MOTOR_ARRESTER, scale=k)
        assert c1.max_point[0] / c1.knee_voltage_V == pytest.approx(
            c0.max_point[0] / c0.knee_voltage_V, rel=1e-12
        )

    def test_para_raios_de_4_16_kV_protege_no_envelope_da_iec_60034_15(self):
        """Coerência independente entre a curva de Vollet e a norma.

        Escalado para 4,16 kV, o para-raios do motor de Vollet dá tensão
        residual de 13,92 kV — 1,1 % ABAIXO do nível espira-a-espira
        ``U'_P = 14,07 kV`` da IEC 60034-15:2009, e 36 % abaixo de
        ``U_P = 21,64 kV``. Os dois dados vêm de fontes independentes e
        coincidem, o que sustenta o escalonamento [CÁLCULO PRÓPRIO].
        """
        k = scale_for_system_voltage(VOLLET_MOTOR_ARRESTER, 4160.0)
        c = characteristic_from_points(VOLLET_MOTOR_ARRESTER, scale=k)
        residual = c.max_point[0]
        assert residual == pytest.approx(13.917e3, rel=1e-3)
        assert residual < IEC_UP_LINHA_V
        assert residual < 0.65 * IEC_UP_V + 1.0
        assert residual / V_BASE_V == pytest.approx(4.10, abs=0.02)
        # O joelho fica bem acima do pico de regime (3,4 kV): o para-raios
        # não conduz em operação normal.
        assert c.knee_voltage_V / V_BASE_V == pytest.approx(2.05, abs=0.02)


# ---------------------------------------------------------------------------
# 4. O ramo
# ---------------------------------------------------------------------------


class TestRamoDoParaRaios:
    def test_construcao_a_partir_da_curva_publicada(self):
        moa = MetalOxideArrester.from_published("moa", "n", "gnd")
        assert moa.reference_voltage_V == pytest.approx(18.4e3, rel=1e-12)
        assert moa.protective_level_V == pytest.approx(36.8e3, rel=1e-12)
        assert moa.is_compensated() is True

    def test_construcao_escalada(self):
        moa = MetalOxideArrester.from_published(
            "moa", "n", "gnd", system_voltage_V=4160.0
        )
        assert moa.protective_level_V == pytest.approx(13.917e3, rel=1e-3)

    def test_tres_fases(self):
        moas = three_phase_arrester("moa", ("a", "b", "c"), "gnd")
        assert [m.name for m in moas] == ["moa_a", "moa_b", "moa_c"]
        assert all(m.nodes[1] == "gnd" for m in moas)

    def test_lista_de_nos_vazia_levanta(self):
        with pytest.raises(ValueError, match="pelo menos um nó"):
            three_phase_arrester("moa", (), "gnd")

    def test_numero_de_fases_diferente_de_tres_usa_indices(self):
        moas = three_phase_arrester("moa", ("x", "y"), "gnd")
        assert [m.name for m in moas] == ["moa_0", "moa_1"]


# ---------------------------------------------------------------------------
# 5. No caso de referência
# ---------------------------------------------------------------------------


class TestNoCasoDeReferencia:
    def test_regime_permanente_nao_e_perturbado(self):
        """O para-raios conduz microampères e dissipa milijoules em regime."""
        from app.simulation.emt.cases.atp_reference import AtpReferenceCase

        modelo = AtpReferenceCase(
            with_snubber=False, motor_arrester_system_voltage_V=4160.0
        ).build()
        modelo.run()
        assert len(modelo.arresters) == 3
        for moa in modelo.arresters:
            assert abs(moa.peak_current_A) < 1.0e-3  # microampères
            assert moa.energy_J < 1.0  # milijoules na janela de 45 ms
            assert moa.extrapolated is False
            # Sem manobra o pico fica abaixo do joelho — o ramo não atua.
            assert abs(moa.peak_voltage_V) < moa.reference_voltage_V

    def test_para_raios_grampeia_a_escalada_na_faixa_publicada(self):
        """O critério de aceitação da §4 do documento da varredura.

        Sem para-raios a realização escala até dezenas de pu, porque nada
        no modelo representa o limite dielétrico da carga. Com ele, o pico
        cai para a faixa que campo e simulação reportam — ~3 pu em
        operação, até 4,6 pu [F18], 4,3 pu com escalada [F24] — e a
        contagem de reignições volta à ordem publicada, "até 10"
        [Vollet 2007, p. 2].
        """
        from app.simulation.emt.cases.atp_reference import AtpReferenceCase
        from app.simulation.emt.vcb_scenarios import VcbSample

        # A pior realização da varredura de 150, transcrita de
        # ``docs/research/rul_isolamento/anexos/dados/varredura_vcb_n150.json``.
        t_sep = 0.014686548756377423
        amostras = tuple(
            VcbSample("literatura", corte, didt, rrds, 0.0, t_sep, None)
            for corte, didt, rrds in (
                (2.711434269810338, 459.75322834158004, 44.25892757065691),
                (2.83534334843704, 456.84415739510047, 7.017730425986475),
                (5.405288719190455, 198.90601064862238, 46.884966495674895),
            )
        )
        sem = AtpReferenceCase(with_snubber=False, vcb_samples=amostras).build()
        sem.run()
        pico_sem = max(sem.motor_voltage_summary().values()) * 1.0e3 / V_BASE_V
        reig_sem = sum(sem.reignition_counts.values())

        com = AtpReferenceCase(
            with_snubber=False,
            vcb_samples=amostras,
            motor_arrester_system_voltage_V=4160.0,
        ).build()
        com.run()
        pico_com = max(com.motor_voltage_summary().values()) * 1.0e3 / V_BASE_V
        reig_com = sum(com.reignition_counts.values())

        assert pico_sem > 10.0, "a realização precisa escalar sem para-raios"
        assert pico_com < 4.6, "com para-raios o pico deve cair no teto de campo"
        assert reig_com < reig_sem
        # Mas NÃO elimina as reignições: "arresters do not limit the
        # multiple reignitions" [Vollet 2007, p. 5].
        assert reig_com > 0

    def test_energia_do_para_raios_e_medida(self):
        from app.simulation.emt.cases.atp_reference import AtpReferenceCase
        from app.simulation.emt.vcb_scenarios import VcbSample

        amostras = tuple(
            VcbSample(
                "literatura",
                2.711434269810338,
                459.75322834158004,
                44.25892757065691,
                0.0,
                0.014686548756377423,
                None,
            )
            for _ in range(3)
        )
        modelo = AtpReferenceCase(
            with_snubber=False,
            vcb_samples=amostras,
            motor_arrester_system_voltage_V=4160.0,
        ).build()
        modelo.run()
        energia = max(m.energy_J for m in modelo.arresters)
        assert energia > 0.0
        # Ordem de grandeza de dezenas a centenas de joules por manobra —
        # confrontar MANUALMENTE com a classe de descarga do para-raios
        # escolhido (limitação emt_arrester_no_energy_rating).
        assert energia < 1.0e4

    def test_tensao_de_sistema_invalida_levanta(self):
        from app.simulation.emt.cases.atp_reference import AtpReferenceCase

        with pytest.raises(ValueError, match="motor_arrester_system_voltage_V"):
            AtpReferenceCase(motor_arrester_system_voltage_V=0.0)

    def test_sem_o_parametro_o_caso_nao_tem_para_raios(self):
        from app.simulation.emt.cases.atp_reference import AtpReferenceCase

        modelo = AtpReferenceCase(with_snubber=False).build()
        assert modelo.arresters == ()


# ---------------------------------------------------------------------------
# 6. Limitações declaradas
# ---------------------------------------------------------------------------


def test_limitacoes_declaradas_e_sem_colisao():
    from app.simulation.emt import KNOWN_LIMITATIONS as KERNEL
    from app.simulation.emt.nonlinear import KNOWN_LIMITATIONS as NAO_LINEAR

    assert "emt_arrester_two_point_curve" in KNOWN_LIMITATIONS
    assert "emt_arrester_scaling_by_system_voltage" in KNOWN_LIMITATIONS
    assert "emt_arrester_no_energy_rating" in KNOWN_LIMITATIONS
    assert not set(KNOWN_LIMITATIONS) & set(KERNEL)
    assert not set(KNOWN_LIMITATIONS) & set(NAO_LINEAR)
    for chave, texto in KNOWN_LIMITATIONS.items():
        assert chave.startswith("emt_arrester_")
        assert len(texto) > 80


# ---------------------------------------------------------------------------
# 7. O critério de aceitação de Wong
# ---------------------------------------------------------------------------


class TestCriterioDeAceitacaoDeWong:
    """A dependência da escalada com a RRDS deve ter MÁXIMO INTERIOR.

    Wong, Snider e Lo mostram que a escalada é mais severa em RRDS
    intermediária: recuperação rápida demais impede a reignição, lenta
    demais permite a extinção no primeiro zero de alta frequência
    [LITERATURA: IPST 2003, p. 5-6]. Antes da correção o motor produzia
    dependência monotônica crescente até 92 pu; a forma correta é a que se
    fixa aqui.

    A LOCALIZAÇÃO do máximo é de circuito: 40 a 60 kV/ms neste caso,
    contra 20 a 30 kV/ms no sistema de ensaio de Wong. O limiar é a
    corrida entre a rampa RRDS·(t − t_sep) e a TRV da rede, e a TRV deste
    caso não é a do dele. O que se testa é a FORMA.

    Medições consolidadas em
    ``docs/research/rul_isolamento/anexos/dados/varredura_rrds_*.json``.
    """

    #: RRDS abaixo da banda de escalada, dentro dela e acima [kV/ms].
    ABAIXO, DENTRO, ACIMA = 20.0, 45.0, 120.0

    @staticmethod
    def _roda(rrds_kV_per_ms: float, t_sep: float = 0.014686548756377423):
        from app.simulation.emt.cases.atp_reference import AtpReferenceCase
        from app.simulation.emt.vcb_scenarios import VcbSample

        amostras = tuple(
            VcbSample("wong", 2.71, 255.0, float(rrds_kV_per_ms), 0.0, t_sep, None, -0.034)
            for _ in range(3)
        )
        modelo = AtpReferenceCase(
            with_snubber=False,
            vcb_samples=amostras,
            motor_arrester_system_voltage_V=4160.0,
        ).build()
        modelo.run()
        return (
            max(modelo.motor_voltage_summary().values()) * 1.0e3 / V_BASE_V,
            sum(modelo.reignition_counts.values()),
        )

    def test_recuperacao_rapida_demais_impede_a_reignicao(self):
        """A cauda SUPERIOR: acima da banda o disjuntor simplesmente abre."""
        _pico, reig = self._roda(self.ACIMA)
        assert reig <= 1

    def test_dentro_da_banda_ha_escalada(self):
        _pico, reig = self._roda(self.DENTRO)
        assert reig > 1

    def test_a_dependencia_nao_e_monotonica(self):
        """A forma exigida: mais reignições no meio do que nos dois extremos."""
        _p_baixo, r_baixo = self._roda(self.ABAIXO)
        _p_meio, r_meio = self._roda(self.DENTRO)
        _p_alto, r_alto = self._roda(self.ACIMA)
        assert r_meio > r_alto
        assert r_meio >= r_baixo

    def test_a_cauda_superior_independe_do_para_raios(self):
        """Quem suprime a reignição em RRDS alta é a corrida com a TRV.

        O para-raios só atua dentro da banda de escalada, grampeando a
        amplitude; acima dela o resultado é o mesmo com e sem ele.
        """
        from app.simulation.emt.cases.atp_reference import AtpReferenceCase
        from app.simulation.emt.vcb_scenarios import VcbSample

        amostras = tuple(
            VcbSample(
                "wong", 2.71, 255.0, self.ACIMA, 0.0, 0.014686548756377423, None, -0.034
            )
            for _ in range(3)
        )
        picos, reignicoes = [], []
        for moa in (None, 4160.0):
            modelo = AtpReferenceCase(
                with_snubber=False,
                vcb_samples=amostras,
                motor_arrester_system_voltage_V=moa,
            ).build()
            modelo.run()
            picos.append(max(modelo.motor_voltage_summary().values()))
            reignicoes.append(sum(modelo.reignition_counts.values()))
        assert reignicoes[0] == reignicoes[1]
        # A diferença que resta é a corrente de fuga do para-raios abaixo
        # do joelho — microampères carregando o nó, na quinta casa.
        assert picos[1] == pytest.approx(picos[0], rel=1.0e-4)
