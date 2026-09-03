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
    KNOWN_LIMITATIONS,
    RULE_OF_THREE,
    ManeuverOutcome,
    SwitchingCampaign,
    TerminalRate,
    campaign_from_summary,
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
