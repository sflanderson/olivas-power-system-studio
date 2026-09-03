"""
Testes da campanha de manobras — os dois caminhos de fim de vida.

O que se valida:

1. A taxa terminal e, sobretudo, o tratamento do caso de ZERO eventos —
   onde a estimativa pontual não informa nada e o que vale é a cota.
2. A separação das duas populações e a exclusão deliberada das manobras
   terminais do acumulador de dano.
3. O resumo que põe os dois caminhos lado a lado e diz qual domina.
4. Os números do caso de referência, lidos do conjunto convergido.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from app.postprocessor.prognosis.damage_models import (
    CombinedDamageAccumulator,
    DamageModelParams,
)
from app.postprocessor.prognosis.stress_profile import StressEvent, StressProfile
from app.postprocessor.prognosis.switching_campaign import (
    EXPONENT_LITERATURE_RANGE,
    KNOWN_LIMITATIONS,
    RULE_OF_THREE,
    ManeuverOutcome,
    PeakDistribution,
    SwitchingCampaign,
    TerminalRate,
    campaign_from_summary,
    exponent_robustness,
    survival,
)

#: Envelope da IEC 60034-15:2009 para 4,16 kV [kV de pico].
ENVELOPE_KV = 21.64

#: Conjunto convergido da varredura (Δt = 0,2 µs).
CONJUNTO = (
    "docs/research/rul_isolamento/anexos/dados/varredura_vcb_n150_dt200ns.json"
)


def _perfil(pico_kV: float, n: int = 1, rotulo: str = "m") -> StressProfile:
    """Perfil de uma manobra com ``n`` excursões de mesmo pico."""
    return StressProfile(
        events=[
            StressEvent(
                V_pk_kV=pico_kV,
                T1_us=0.2,
                dvdt_kV_per_us=pico_kV / 0.2,
                n_reignitions=n,
                source=rotulo,
            )
            for _ in range(n)
        ],
        label=rotulo,
    )


# ---------------------------------------------------------------------------
# 1. A taxa terminal
# ---------------------------------------------------------------------------


class TestTaxaTerminal:
    def test_estimativa_pontual_e_a_fracao(self):
        t = TerminalRate(n_crossed=8, n_total=150)
        assert t.point_estimate == pytest.approx(8 / 150)
        assert t.expected_maneuvers == pytest.approx(150 / 8)

    def test_zero_eventos_usa_a_regra_de_tres(self):
        """O caso que mais importa: nenhuma travessia NÃO é impossibilidade."""
        t = TerminalRate(n_crossed=0, n_total=150)
        assert t.point_estimate == 0.0
        assert t.expected_maneuvers == math.inf
        assert t.upper_bound_95 == pytest.approx(RULE_OF_THREE / 150)
        assert t.minimum_expected_maneuvers == pytest.approx(50.0)
        assert "mais de 50" in t.describe()

    def test_com_eventos_a_cota_e_a_normal(self):
        t = TerminalRate(n_crossed=8, n_total=150)
        p = 8 / 150
        esperado = p + 1.96 * math.sqrt(p * (1 - p) / 150)
        assert t.upper_bound_95 == pytest.approx(esperado)
        assert t.upper_bound_95 > t.point_estimate

    def test_a_cota_satura_em_um(self):
        t = TerminalRate(n_crossed=3, n_total=3)
        assert t.upper_bound_95 == 1.0
        assert t.minimum_expected_maneuvers == pytest.approx(1.0)

    def test_zero_eventos_em_amostra_pequena_da_cota_larga(self):
        """Com n = 3, a regra de três já satura: nada se pode afirmar."""
        t = TerminalRate(n_crossed=0, n_total=3)
        assert t.upper_bound_95 == 1.0

    def test_a_descricao_distingue_ponto_de_cota(self):
        com = TerminalRate(n_crossed=8, n_total=150).describe()
        sem = TerminalRate(n_crossed=0, n_total=150).describe()
        assert "esperadas até a primeira" in com
        assert "nenhuma travessia" in sem and "95 %" in sem

    @pytest.mark.parametrize(
        "kwargs",
        [
            {"n_crossed": 0, "n_total": 0},
            {"n_crossed": -1, "n_total": 10},
            {"n_crossed": 11, "n_total": 10},
        ],
    )
    def test_contagens_invalidas_levantam(self, kwargs):
        with pytest.raises(ValueError):
            TerminalRate(**kwargs)


# ---------------------------------------------------------------------------
# 2. As duas populações
# ---------------------------------------------------------------------------


class TestSeparacaoDasPopulacoes:
    @staticmethod
    def _campanha():
        c = SwitchingCampaign(withstand_level_kV=ENVELOPE_KV, label="teste")
        for i in range(8):
            c.add(
                ManeuverOutcome(
                    index=i, peak_pu=2.0, reignitions=2, profile=_perfil(6.8)
                )
            )
        for i in range(8, 10):
            c.add(
                ManeuverOutcome(
                    index=i,
                    peak_pu=6.6,
                    reignitions=90,
                    crossed_withstand=True,
                    profile=_perfil(22.5, n=5),
                )
            )
        return c

    def test_as_populacoes_sao_disjuntas_e_cobrem_tudo(self):
        c = self._campanha()
        assert len(c.aging) == 8
        assert len(c.terminal) == 2
        assert len(c.aging) + len(c.terminal) == c.n_maneuvers == 10

    def test_a_taxa_vem_da_contagem(self):
        c = self._campanha()
        assert c.terminal_rate().point_estimate == pytest.approx(0.2)

    def test_o_acumulador_ignora_as_manobras_terminais(self):
        """O ponto central do módulo, verificado por contagem."""
        c = self._campanha()
        acc = c.accumulate(params=DamageModelParams())
        assert acc.n_operations == 8, "só as manobras de envelhecimento entram"
        assert acc.n_events == 8

    def test_incluir_as_terminais_daria_dano_maior(self):
        """Mede o erro que a exclusão evita, para que ele não seja abstrato."""
        c = self._campanha()
        correto = c.accumulate(params=DamageModelParams())
        errado = CombinedDamageAccumulator(params=DamageModelParams())
        for o in c.outcomes:
            errado.add_profile(o.profile)
        assert errado.D_total > correto.D_total
        assert errado.n_operations == 10

    def test_manobra_de_envelhecimento_sem_perfil_levanta(self):
        c = SwitchingCampaign(withstand_level_kV=ENVELOPE_KV)
        c.add(ManeuverOutcome(index=0, peak_pu=2.0))
        with pytest.raises(ValueError, match="sem perfil de estresse"):
            c.accumulate()

    def test_manobra_terminal_sem_perfil_e_admissivel(self):
        """A terminal não entra no dano: seu perfil é dispensável."""
        c = SwitchingCampaign(withstand_level_kV=ENVELOPE_KV)
        c.add(ManeuverOutcome(index=0, peak_pu=2.0, profile=_perfil(6.8)))
        c.add(ManeuverOutcome(index=1, peak_pu=7.0, crossed_withstand=True))
        acc = c.accumulate()
        assert acc.n_operations == 1

    def test_campanha_vazia_nao_tem_taxa(self):
        c = SwitchingCampaign(withstand_level_kV=ENVELOPE_KV)
        with pytest.raises(ValueError, match="sem manobras"):
            c.terminal_rate()

    def test_extend_e_add_sao_equivalentes(self):
        a = SwitchingCampaign(withstand_level_kV=ENVELOPE_KV)
        b = SwitchingCampaign(withstand_level_kV=ENVELOPE_KV)
        eventos = [
            ManeuverOutcome(index=i, peak_pu=2.0, profile=_perfil(6.8))
            for i in range(3)
        ]
        for e in eventos:
            a.add(e)
        b.extend(eventos)
        assert a.outcomes == b.outcomes

    @pytest.mark.parametrize("nivel", [0.0, -1.0, float("nan")])
    def test_envelope_invalido_levanta(self, nivel):
        with pytest.raises(ValueError, match="withstand_level_kV"):
            SwitchingCampaign(withstand_level_kV=nivel)

    def test_tipo_errado_em_outcomes_levanta(self):
        with pytest.raises(TypeError, match="ManeuverOutcome"):
            SwitchingCampaign(withstand_level_kV=ENVELOPE_KV, outcomes=(1,))

    @pytest.mark.parametrize(
        "kwargs",
        [
            {"index": -1, "peak_pu": 1.0},
            {"index": 0, "peak_pu": -1.0},
            {"index": 0, "peak_pu": float("nan")},
            {"index": 0, "peak_pu": 1.0, "reignitions": -1},
        ],
    )
    def test_desfecho_invalido_levanta(self, kwargs):
        with pytest.raises(ValueError):
            ManeuverOutcome(**kwargs)

    def test_perfil_de_tipo_errado_levanta(self):
        with pytest.raises(TypeError, match="StressProfile"):
            ManeuverOutcome(index=0, peak_pu=1.0, profile="perfil")


# ---------------------------------------------------------------------------
# 3. Os dois caminhos juntos
# ---------------------------------------------------------------------------


class TestResumoDeVida:
    def test_o_fim_e_o_minimo_dos_dois_caminhos(self):
        c = SwitchingCampaign(withstand_level_kV=ENVELOPE_KV)
        # Envelhecimento desprezível, travessia frequente: domina a travessia.
        for i in range(9):
            c.add(ManeuverOutcome(index=i, peak_pu=1.5, profile=_perfil(5.1)))
        c.add(ManeuverOutcome(index=9, peak_pu=7.0, crossed_withstand=True))
        acc = c.accumulate()
        r = c.life_summary(acc)
        assert r["manobras_ate_travessia"] == pytest.approx(10.0)
        assert r["manobras_ate_o_fim"] == min(
            r["manobras_por_envelhecimento"], r["manobras_ate_travessia"]
        )

    def test_sem_travessia_o_envelhecimento_domina(self):
        c = SwitchingCampaign(withstand_level_kV=ENVELOPE_KV)
        for i in range(10):
            c.add(ManeuverOutcome(index=i, peak_pu=3.0, profile=_perfil(12.0)))
        acc = c.accumulate()
        r = c.life_summary(acc)
        assert r["manobras_ate_travessia"] == math.inf
        assert r["caminho_dominante"] == "envelhecimento"
        assert math.isfinite(r["manobras_ate_o_fim"])
        # A cota inferior continua finita e é o que se reporta.
        assert math.isfinite(r["manobras_ate_travessia_cota_inferior"])

    def test_o_resumo_declara_que_o_dano_e_cota_inferior(self):
        c = SwitchingCampaign(withstand_level_kV=ENVELOPE_KV)
        c.add(ManeuverOutcome(index=0, peak_pu=3.0, profile=_perfil(12.0)))
        acc = c.accumulate()
        assert c.life_summary(acc)["dano_e_cota_inferior"] is True

    def test_dano_nulo_da_vida_infinita_por_envelhecimento(self):
        c = SwitchingCampaign(withstand_level_kV=ENVELOPE_KV)
        # Pico abaixo do limiar de dano: não acumula.
        for i in range(5):
            c.add(ManeuverOutcome(index=i, peak_pu=0.5, profile=_perfil(1.0)))
        acc = c.accumulate(
            params=DamageModelParams(V_th_kV=10.0)
        )
        assert c.maneuvers_to_damage_limit(acc) == math.inf

    def test_extrapolar_sem_acumular_levanta(self):
        c = SwitchingCampaign(withstand_level_kV=ENVELOPE_KV)
        c.add(ManeuverOutcome(index=0, peak_pu=3.0, profile=_perfil(12.0)))
        with pytest.raises(ValueError, match="manobra nenhuma"):
            c.maneuvers_to_damage_limit(
                CombinedDamageAccumulator(params=DamageModelParams())
            )


# ---------------------------------------------------------------------------
# 4. Os números do caso de referência
# ---------------------------------------------------------------------------


class TestCasoDeReferencia:
    """Lê o conjunto convergido e reproduz os números citados no estudo."""

    @classmethod
    def _conjunto(cls):
        caminho = Path(__file__).resolve().parents[1] / CONJUNTO
        if not caminho.exists():  # pragma: no cover - conjunto opcional
            pytest.skip(f"conjunto ausente: {CONJUNTO}")
        return json.loads(caminho.read_text(encoding="utf-8"))

    @classmethod
    def _campanha(cls, mitigacao: str) -> SwitchingCampaign:
        d = cls._conjunto()
        grupo = sorted(
            (l for l in d["realizacoes"] if l.get("mitigacao") == mitigacao),
            key=lambda l: l["indice"],
        )
        assert grupo, f"mitigação {mitigacao!r} ausente do conjunto"
        base_kV = d["configuracao"]["v_base_fase_terra_V"] / 1.0e3
        picos = [max(l["motor_pu"].values()) for l in grupo]
        return campaign_from_summary(
            withstand_level_kV=ENVELOPE_KV,
            peaks_pu=picos,
            crossed=[p * base_kV >= ENVELOPE_KV for p in picos],
            reignitions=[sum(l["reignicoes"].values()) for l in grupo],
            label=mitigacao,
        )

    def test_o_conjunto_e_o_convergido(self):
        d = self._conjunto()
        assert d["configuracao"]["dt_s"] == pytest.approx(2.0e-7)
        assert d["configuracao"]["n_por_cenario"] == 150

    def test_sem_mitigacao_uma_manobra_em_dezenove_atravessa(self):
        c = self._campanha("nenhuma")
        t = c.terminal_rate()
        assert t.n_total == 150
        assert t.n_crossed == 8
        assert t.point_estimate == pytest.approx(0.0533, abs=0.001)
        assert t.expected_maneuvers == pytest.approx(18.75, abs=0.1)
        assert t.upper_bound_95 == pytest.approx(0.089, abs=0.002)

    def test_com_para_raios_nenhuma_travessia_e_a_cota_e_o_resultado(self):
        c = self._campanha("para_raios")
        t = c.terminal_rate()
        assert t.n_crossed == 0
        assert t.expected_maneuvers == math.inf
        # O número REPORTÁVEL é a cota, não o infinito.
        assert t.minimum_expected_maneuvers == pytest.approx(50.0)
        assert t.upper_bound_95 == pytest.approx(0.02)

    def test_a_mitigacao_muda_o_caminho_dominante(self):
        """A leitura de engenharia: o para-raios tira a travessia da frente."""
        sem = self._campanha("nenhuma").terminal_rate()
        com = self._campanha("para_raios").terminal_rate()
        assert com.minimum_expected_maneuvers > sem.expected_maneuvers

    def test_o_registro_de_disrupcao_da_a_mesma_taxa(self):
        """O caminho de disrupção conta o mesmo que o critério de pico."""
        a = self._campanha("nenhuma").terminal_rate()
        b = self._campanha("disrupcao").terminal_rate()
        assert a.n_crossed == b.n_crossed


class TestConstrucaoDeResumo:
    def test_comprimentos_incompativeis_levantam(self):
        with pytest.raises(ValueError, match="crossed"):
            campaign_from_summary(
                withstand_level_kV=ENVELOPE_KV,
                peaks_pu=[1.0, 2.0],
                crossed=[False],
            )
        with pytest.raises(ValueError, match="reignitions"):
            campaign_from_summary(
                withstand_level_kV=ENVELOPE_KV,
                peaks_pu=[1.0, 2.0],
                crossed=[False, True],
                reignitions=[1],
            )

    def test_sequencia_vazia_levanta(self):
        with pytest.raises(ValueError, match="peaks_pu"):
            campaign_from_summary(
                withstand_level_kV=ENVELOPE_KV, peaks_pu=[], crossed=[]
            )

    def test_campanha_de_resumo_nao_integra_dano(self):
        """Sem forma de onda não há dano — e o erro diz isso."""
        c = campaign_from_summary(
            withstand_level_kV=ENVELOPE_KV, peaks_pu=[2.0], crossed=[False]
        )
        with pytest.raises(ValueError, match="sem perfil de estresse"):
            c.accumulate()


# ---------------------------------------------------------------------------
# 5. Limitações
# ---------------------------------------------------------------------------


def test_limitacoes_declaradas_e_sem_colisao():
    from app.postprocessor.prognosis import KNOWN_LIMITATIONS as FACHADA

    assert "rul_campaign_terminal_and_aging_are_not_additive" in KNOWN_LIMITATIONS
    texto = KNOWN_LIMITATIONS["rul_campaign_terminal_and_aging_are_not_additive"]
    # A dependência não modelada que torna o resultado cota superior.
    assert "COTA SUPERIOR" in texto
    for chave, t in KNOWN_LIMITATIONS.items():
        assert chave.startswith("rul_campaign_")
        assert len(t) > 80
    # A fachada agrega as chaves novas sem colisão.
    for chave in KNOWN_LIMITATIONS:
        assert chave in FACHADA


# ---------------------------------------------------------------------------
# 6. A conversão de falha em envelhecimento
# ---------------------------------------------------------------------------


class TestConversaoDeFalhaEmEnvelhecimento:
    """Por que comparar dano entre configurações pode inverter a conclusão.

    Medido na campanha de 60 manobras: o para-raios aumenta o dano
    acumulado em 4,3 vezes, e o número lido isoladamente recomendaria não
    instalá-lo. A causa é uma única realização — a que atravessa o
    envelope sem para-raios e sobrevive com ele:

    * sem para-raios: pico de 10,67 pu, ATRAVESSA, contribui **zero**
      excursões de estresse (não há mais o que envelhecer);
    * com para-raios: pico de 3,31 pu, não atravessa, contribui **138**
      excursões.

    Excluindo essa realização os dois conjuntos ficam idênticos, com 389
    excursões cada [REPO: ``10_CAMPANHA_DOIS_CAMINHOS_DE_FIM_DE_VIDA.md``,
    §3.1].

    A regra que daí decorre e que estes testes fixam: **dano acumulado só
    é comparável entre configurações que produzem o mesmo conjunto de
    sobreviventes**; entre as que mudam quem sobrevive, a comparação é
    sobre ``min(N_env, N_term)``.
    """

    @staticmethod
    def _par_de_campanhas():
        """Duas campanhas idênticas, salvo por uma manobra decisiva."""
        comuns = [
            ManeuverOutcome(index=i, peak_pu=2.0, profile=_perfil(7.0))
            for i in range(9)
        ]
        sem = SwitchingCampaign(withstand_level_kV=ENVELOPE_KV, label="sem")
        sem.extend(comuns)
        # Sem mitigação a décima manobra ATRAVESSA: evento terminal, sem
        # estresse a integrar.
        sem.add(
            ManeuverOutcome(index=9, peak_pu=10.7, crossed_withstand=True)
        )

        com = SwitchingCampaign(withstand_level_kV=ENVELOPE_KV, label="com")
        com.extend(comuns)
        # Com mitigação a mesma manobra sobrevive, grampeada — e paga
        # estresse por sobreviver.
        com.add(
            ManeuverOutcome(index=9, peak_pu=3.3, profile=_perfil(11.2, n=6))
        )
        return sem, com

    def test_a_mitigacao_aumenta_o_dano_acumulado(self):
        sem, com = self._par_de_campanhas()
        d_sem = sem.accumulate().D_total
        d_com = com.accumulate().D_total
        assert d_com > d_sem, "sobreviver custa dano; falhar não custa nenhum"

    def test_e_mesmo_assim_a_mitigacao_prolonga_a_vida(self):
        """O critério correto inverte a conclusão do dano isolado."""
        sem, com = self._par_de_campanhas()
        vida_sem = sem.life_summary(sem.accumulate())
        vida_com = com.life_summary(com.accumulate())
        assert vida_sem["caminho_dominante"] == "travessia_do_envelope"
        assert vida_com["caminho_dominante"] == "envelhecimento"
        assert vida_com["manobras_ate_o_fim"] > vida_sem["manobras_ate_o_fim"]

    def test_as_manobras_comuns_contribuem_o_mesmo_nos_dois(self):
        """A mitigação não toca o que fica abaixo do seu limiar de atuação."""
        sem, com = self._par_de_campanhas()
        comuns_sem = [o for o in sem.aging if o.index < 9]
        comuns_com = [o for o in com.aging if o.index < 9]
        assert len(comuns_sem) == len(comuns_com) == 9
        a = CombinedDamageAccumulator(params=DamageModelParams())
        b = CombinedDamageAccumulator(params=DamageModelParams())
        for o in comuns_sem:
            a.add_profile(o.profile)
        for o in comuns_com:
            b.add_profile(o.profile)
        assert a.D_total == pytest.approx(b.D_total, rel=1e-12)

    def test_a_manobra_terminal_nao_contribui_estresse(self):
        sem, _com = self._par_de_campanhas()
        acc = sem.accumulate()
        assert acc.n_operations == 9, "a décima manobra é terminal, não entra"


# ---------------------------------------------------------------------------
# 7. Acoplamento: p depende do dano acumulado
# ---------------------------------------------------------------------------


class TestDistribuicaoDePicos:
    def test_excedencia_e_a_contagem(self):
        d = PeakDistribution(peaks_kV=(1.0, 5.0, 10.0, 30.0))
        assert d.n == 4
        assert d.max_kV == 30.0
        assert d.exceedance(9.0) == pytest.approx(0.5)
        # A igualdade conta: é o critério do motor, que dispara em >=.
        assert d.exceedance(30.0) == pytest.approx(0.25)
        assert d.exceedance(30.001) == 0.0
        assert d.exceedance(0.0) == 1.0

    def test_os_picos_ficam_ordenados(self):
        d = PeakDistribution(peaks_kV=(30.0, 1.0, 10.0))
        assert d.peaks_kV == (1.0, 10.0, 30.0)

    def test_pontos_de_quebra_vem_em_ordem_decrescente(self):
        d = PeakDistribution(peaks_kV=(1.0, 5.0, 10.0, 30.0))
        assert d.breakpoints_kV(above_kV=4.0) == (30.0, 10.0, 5.0)

    def test_taxa_traz_o_intervalo(self):
        d = PeakDistribution(peaks_kV=tuple([1.0] * 142 + [100.0] * 8))
        t = d.rate(21.64)
        assert (t.n_crossed, t.n_total) == (8, 150)
        assert t.expected_maneuvers == pytest.approx(18.75)

    @pytest.mark.parametrize(
        "picos", [(), (float("nan"),), (-1.0,)]
    )
    def test_picos_invalidos_levantam(self, picos):
        with pytest.raises(ValueError):
            PeakDistribution(peaks_kV=picos)


class TestCurvaDeSobrevivencia:
    """O acoplamento resolvido por trechos, sem iterar manobra a manobra."""

    def test_distribuicao_com_lacuna_da_taxa_constante(self):
        """O caso do circuito sem mitigação: p não muda em toda a vida.

        O corpo termina muito abaixo do limiar degradado e a cauda está
        muito acima dele: nenhum pico entra na faixa que ψ(D) varre, e a
        taxa fixa é EXATA, não conservadora.
        """
        d = PeakDistribution(peaks_kV=tuple([9.0] * 142 + [200.0] * 8))
        c = survival(
            d, withstand0_kV=21.64, maneuvers_to_damage_limit=1.0e6
        )
        assert c.rate_is_constant
        assert c.critical_damage is None
        assert len(c.segments) == 1
        assert c.segments[0].p == pytest.approx(8 / 150)
        assert c.expected_maneuvers == pytest.approx(150 / 8, rel=1e-6)

    def test_distribuicao_sem_lacuna_da_taxa_crescente(self):
        """O caso com para-raios: os picos grampeados entram no fim da vida."""
        d = PeakDistribution(peaks_kV=tuple([9.0] * 142 + [11.7] * 8))
        c = survival(
            d, withstand0_kV=21.64, maneuvers_to_damage_limit=1.0e6, psi_min=0.5
        )
        assert not c.rate_is_constant
        assert c.critical_damage is not None
        # ψ·21,64 = 11,7 → ψ = 0,5406 → D = (1 − 0,5406)/0,5 = 0,919
        assert c.critical_damage == pytest.approx(0.919, abs=0.005)
        assert c.segments[0].p == 0.0
        assert c.segments[-1].p > 0.0

    def test_a_sobrevivencia_decai_geometricamente_no_trecho(self):
        d = PeakDistribution(peaks_kV=(9.0, 200.0))
        c = survival(d, withstand0_kV=21.64, maneuvers_to_damage_limit=10.0)
        seg = c.segments[0]
        assert seg.survival_end == pytest.approx((1.0 - seg.p) ** 10.0)

    def test_taxa_nula_nao_consome_sobrevivencia(self):
        d = PeakDistribution(peaks_kV=(1.0, 2.0, 3.0))
        c = survival(d, withstand0_kV=100.0, maneuvers_to_damage_limit=1.0e6)
        assert c.expected_maneuvers == pytest.approx(1.0e6)
        assert c.survival_at_damage_limit == pytest.approx(1.0)

    def test_esperanca_coincide_com_a_geometrica_quando_p_e_constante(self):
        """Sanidade: sem acoplamento, E[N] tem de recair em 1/p."""
        d = PeakDistribution(peaks_kV=tuple([1.0] * 90 + [500.0] * 10))
        c = survival(d, withstand0_kV=21.64, maneuvers_to_damage_limit=1.0e9)
        assert c.rate_is_constant
        assert c.expected_maneuvers == pytest.approx(10.0, rel=1e-6)

    def test_psi_min_unitario_desliga_o_acoplamento(self):
        """Sem degradação da suportabilidade não há acoplamento."""
        d = PeakDistribution(peaks_kV=tuple([9.0] * 142 + [11.7] * 8))
        c = survival(
            d, withstand0_kV=21.64, maneuvers_to_damage_limit=1.0e6, psi_min=1.0
        )
        assert c.rate_is_constant

    @pytest.mark.parametrize(
        "kwargs",
        [
            {"withstand0_kV": 0.0},
            {"withstand0_kV": float("nan")},
            {"maneuvers_to_damage_limit": math.inf},
            {"maneuvers_to_damage_limit": 0.0},
            {"psi_min": 0.0},
            {"psi_min": 1.5},
        ],
    )
    def test_parametros_invalidos_levantam(self, kwargs):
        d = PeakDistribution(peaks_kV=(1.0, 2.0))
        base = {"withstand0_kV": 21.64, "maneuvers_to_damage_limit": 1.0e6}
        base.update(kwargs)
        with pytest.raises(ValueError):
            survival(d, **base)


class TestAcoplamentoNoCasoDeReferencia:
    """Os dois vereditos que o acoplamento entrega, sobre os dados reais."""

    @classmethod
    def _distribuicao(cls, mitigacao: str) -> PeakDistribution:
        caminho = Path(__file__).resolve().parents[1] / CONJUNTO
        if not caminho.exists():  # pragma: no cover
            pytest.skip(f"conjunto ausente: {CONJUNTO}")
        d = json.loads(caminho.read_text(encoding="utf-8"))
        base_kV = d["configuracao"]["v_base_fase_terra_V"] / 1.0e3
        grupo = [l for l in d["realizacoes"] if l.get("mitigacao") == mitigacao]
        return PeakDistribution(
            peaks_kV=[max(l["motor_pu"].values()) * base_kV for l in grupo],
            label=mitigacao,
        )

    def test_sem_mitigacao_o_acoplamento_e_inocuo(self):
        """A lacuna de 19x na distribuição torna a taxa fixa EXATA."""
        d = self._distribuicao("nenhuma")
        c = survival(
            d, withstand0_kV=ENVELOPE_KV, maneuvers_to_damage_limit=5.534e7
        )
        assert c.rate_is_constant
        assert c.expected_maneuvers == pytest.approx(18.75, abs=0.05)

    def test_a_lacuna_existe_e_e_de_uma_ordem_de_grandeza(self):
        d = self._distribuicao("nenhuma")
        picos = d.peaks_kV
        corpo = max(v for v in picos if v < 100.0)
        cauda = min(v for v in picos if v >= 100.0)
        assert cauda / corpo > 10.0

    def test_com_para_raios_o_acoplamento_acorda_no_fim_da_vida(self):
        """O para-raios ADIA a travessia; não a elimina."""
        d = self._distribuicao("para_raios")
        c = survival(
            d, withstand0_kV=ENVELOPE_KV, maneuvers_to_damage_limit=1.322e7
        )
        assert not c.rate_is_constant
        assert c.critical_damage == pytest.approx(0.92, abs=0.01)
        assert c.segments[0].p == 0.0

    def test_a_mitigacao_prolonga_a_vida_por_ordens_de_grandeza(self):
        sem = survival(
            self._distribuicao("nenhuma"),
            withstand0_kV=ENVELOPE_KV,
            maneuvers_to_damage_limit=5.534e7,
        )
        com = survival(
            self._distribuicao("para_raios"),
            withstand0_kV=ENVELOPE_KV,
            maneuvers_to_damage_limit=1.322e7,
        )
        assert com.expected_maneuvers / sem.expected_maneuvers > 1.0e4


# ---------------------------------------------------------------------------
# 8. Robustez da decisão ao expoente não calibrado
# ---------------------------------------------------------------------------


class TestRobustezAoExpoente:
    @staticmethod
    def _par():
        """Uma configuração dominada pela travessia, outra pelo dano."""
        sem = SwitchingCampaign(withstand_level_kV=ENVELOPE_KV, label="sem")
        for i in range(9):
            sem.add(ManeuverOutcome(index=i, peak_pu=2.0, profile=_perfil(7.0)))
        sem.add(ManeuverOutcome(index=9, peak_pu=10.7, crossed_withstand=True))

        com = SwitchingCampaign(withstand_level_kV=ENVELOPE_KV, label="com")
        for i in range(10):
            com.add(ManeuverOutcome(index=i, peak_pu=3.4, profile=_perfil(11.7)))
        return {"sem": sem, "com": com}

    def test_a_faixa_padrao_e_a_da_literatura(self):
        assert EXPONENT_LITERATURE_RANGE == (3.8, 11.7)

    def test_a_ordenacao_resiste_a_faixa_inteira(self):
        r = exponent_robustness(self._par())
        assert r.is_robust
        assert r.winner == "com"
        assert "LIVRE de calibração" in r.describe()

    def test_a_configuracao_dominada_pela_travessia_nao_depende_do_expoente(self):
        """O ponto que extingue a limitação para efeito de DECISÃO.

        Quando o caminho terminal domina, a vida é ``1/p`` e o expoente
        não calibrado **não entra na conta**: a dispersão é exatamente 1.
        """
        r = exponent_robustness(self._par())
        assert r.spread["sem"] == pytest.approx(1.0)
        assert r.spread["com"] > 10.0

    def test_o_numero_absoluto_continua_dependendo_do_expoente(self):
        """A decisão fica livre; a vida absoluta, não."""
        r = exponent_robustness(self._par())
        vidas = r.lives["com"]
        assert vidas[-1] > vidas[0]
        assert max(vidas) / min(vidas) > 100.0

    def test_expoentes_explicitos_sao_respeitados(self):
        r = exponent_robustness(self._par(), exponents=(4.0, 8.0))
        assert r.exponents == (4.0, 8.0)
        assert len(r.lives["sem"]) == 2

    def test_uma_campanha_so_levanta(self):
        with pytest.raises(ValueError, match="ao menos duas"):
            exponent_robustness({"unica": self._par()["sem"]})

    def test_lista_de_expoentes_vazia_levanta(self):
        with pytest.raises(ValueError, match="exponents"):
            exponent_robustness(self._par(), exponents=())


# ---------------------------------------------------------------------------
# 9. Perfil vazio e a contagem correta de manobras
# ---------------------------------------------------------------------------


class TestPerfilVazioEDenominador:
    """Duas distinções que a campanha de 150 manobras revelou por falha.

    A primeira: ``None`` e perfil VAZIO são coisas diferentes. ``None`` é
    ausência de medição e impede integrar; vazio é medição que não
    encontrou excursão acima do limiar de detecção — dano nulo, e uma
    manobra que ocorreu.

    A segunda: ``accumulator.n_operations`` conta GRUPOS de reignição
    dentro do perfil, não manobras da campanha. Um perfil que reúne as
    três fases declara até três grupos. O denominador correto é
    ``len(campanha.aging)``.
    """

    def test_perfil_vazio_e_aceito_e_contribui_dano_nulo(self):
        c = SwitchingCampaign(withstand_level_kV=ENVELOPE_KV)
        c.add(ManeuverOutcome(index=0, peak_pu=1.2, profile=StressProfile(events=[])))
        acc = c.accumulate(params=DamageModelParams())
        assert acc.D_total == 0.0
        assert c.maneuvers_to_damage_limit(acc) == math.inf

    def test_perfil_vazio_entra_no_denominador(self):
        """A manobra branda ocorreu: ignorá-la superestimaria a taxa de dano."""
        com_vazio = SwitchingCampaign(withstand_level_kV=ENVELOPE_KV)
        com_vazio.add(ManeuverOutcome(index=0, peak_pu=3.0, profile=_perfil(12.0)))
        for i in (1, 2, 3):
            com_vazio.add(
                ManeuverOutcome(
                    index=i, peak_pu=1.2, profile=StressProfile(events=[])
                )
            )
        so_a_severa = SwitchingCampaign(withstand_level_kV=ENVELOPE_KV)
        so_a_severa.add(ManeuverOutcome(index=0, peak_pu=3.0, profile=_perfil(12.0)))

        n_com = com_vazio.maneuvers_to_damage_limit(com_vazio.accumulate())
        n_so = so_a_severa.maneuvers_to_damage_limit(so_a_severa.accumulate())
        # Mesmo dano, quatro manobras em vez de uma: a vida quadruplica.
        assert n_com == pytest.approx(4.0 * n_so, rel=1e-9)

    def test_none_continua_sendo_erro_e_a_mensagem_ensina(self):
        c = SwitchingCampaign(withstand_level_kV=ENVELOPE_KV)
        c.add(ManeuverOutcome(index=0, peak_pu=2.0))
        with pytest.raises(ValueError, match="VAZIO"):
            c.accumulate()

    def test_o_denominador_ignora_o_contador_do_acumulador(self):
        """Um perfil de três grupos numa manobra não vira três manobras."""
        tres_grupos = StressProfile(
            events=[
                StressEvent(
                    V_pk_kV=12.0, T1_us=0.2, dvdt_kV_per_us=60.0, n_reignitions=1
                )
                for _ in range(3)
            ]
        )
        c = SwitchingCampaign(withstand_level_kV=ENVELOPE_KV)
        c.add(ManeuverOutcome(index=0, peak_pu=3.0, profile=tres_grupos))
        acc = c.accumulate()
        assert acc.n_operations == 3, "o acumulador vê três grupos"
        assert len(c.aging) == 1, "a campanha vê uma manobra"
        # A vida usa a contagem da CAMPANHA.
        assert c.maneuvers_to_damage_limit(acc) == pytest.approx(
            1.0 / acc.D_total, rel=1e-12
        )
