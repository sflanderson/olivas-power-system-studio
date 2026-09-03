"""
app.postprocessor.prognosis.health_index — índice de saúde de ativo (AHI)
0-100 com decomposição explicável.

Escopo
======

Compõe um índice de saúde 0-100 do isolamento de estator a partir de até
seis contribuições, todas opcionais exceto as de dano:

(i)   dano elétrico acumulado ``D_el`` (D7 / eq. 5.2);
(ii)  dano térmico acumulado ``D_th`` (D6 / eq. 5.1);
(iii) margem de coordenação ``γ = U_w/U_s`` (Etapa 1 §6);
(iv)  resistência de isolamento e índice de polarização (IR/PI);
(v)   fator de dissipação tan δ;
(vi)  magnitude de descargas parciais ``Q_m``.

Requisito de explicabilidade
=============================

:meth:`AssetHealthIndex.explain` devolve a decomposição por
contribuição, cujos percentuais **somam 100 %**. Nenhuma contribuição é
implícita: componentes sem dado medido são declarados ``available=False``
e ficam fora da renormalização de pesos.

Limiares — o que é normativo e o que é configurável
====================================================

Limiares com origem normativa ou de literatura verificada (Etapa 1 §7.2):

* **PI mínimo 1,5 (classe A) / 2,0 (classes B, F, H)**
  [NORMA: ABNT NBR 17094-3:2018, 6.8.3].
* **IR mínimo 100 MΩ** (bobinas pré-formadas pós-1970, 40 °C, 1 min);
  "isolação boa típica 10 a 100 × o mínimo"
  [NORMA: ABNT NBR 17094-3:2018, 6.8.2, Tab. 2].
* **tan δ ≤ 20 × 10⁻³** em ``0,2 U_N`` para bobinas novas
  [LITERATURA: Iris Power, citando IEC 60034-27-3, Tab. 1]. Nota: a
  IEC 60034-27-3:2015 é formalmente aplicável a ≥ 6 kV com revestimento
  condutor de ranhura — **não** é formalmente aplicável a 4,16 kV
  (Etapa 1 §7.1).
* **Q_m percentil 90 = 208 mV** para 2 a < 6 kV e **488 mV** para
  13 a < 16 kV, instrumentação VHF com acopladores de 80 pF, 10 pps
  [LITERATURA: Warren, IRMC 2022, Tab. 1]. "Calibration of on-line PD
  test results is theoretically not possible" [idem, p. 1]: transferir
  esses percentis a outra instrumentação é [HIPÓTESE].
* **γ → 1 é o critério de fim de vida por coordenação**
  [Etapa 1 §6, formalização própria ancorada em IEC 60071-1:2019, 3.31
  e 3.34].

Limiares SEM origem normativa, **declarados configuráveis e não
calibrados**: ``ir_good_Mohm``, ``tan_delta_good``, ``pd_qm_good_mV``,
``gamma_healthy``, os pesos de :class:`HealthIndexWeights` e as faixas de
semáforo de :data:`DEFAULT_BANDS`.

Advertência de método
======================

IR/PI, tan δ e DP são indicadores de ``groundwall`` com sensibilidade
**nula/baixa** ou **indireta** ao dano espira-a-espira, que é o modo
crítico deste estudo (Etapa 1 §1.2, §7.1). As próprias normas declaram
que suas tendências "cannot be used to predict the time to failure"
[NORMA: IEC 60034-27-4:2018, Introdução; IEC 60034-27-3:2015, Introdução;
IEC 60034-27-2:2023, Introdução]. Eles entram no AHI como **evidência
corroborativa de estado**, nunca como preditores de RUL.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Faixas de classificação (semáforo)
# ---------------------------------------------------------------------------

#: Faixas de classificação ``(limite_inferior, rótulo, semáforo)``, em
#: ordem decrescente. **NÃO NORMATIVAS** — convenção do módulo,
#: configuráveis pelo chamador via ``bands``.
DEFAULT_BANDS: tuple[tuple[float, str, str], ...] = (
    (85.0, "BOM", "verde"),
    (70.0, "ACEITAVEL", "amarelo"),
    (50.0, "DEGRADADO", "laranja"),
    (0.0, "CRITICO", "vermelho"),
)


@dataclass(frozen=True)
class HealthIndexWeights:
    """Pesos das contribuições do AHI.

    **NÃO CALIBRADOS** — convenção do módulo, rastreável e configurável.
    A soma não precisa ser 1: os pesos são renormalizados sobre os
    componentes efetivamente disponíveis.

    Justificativa da hierarquia adotada [INFERÊNCIA]: as parcelas de dano
    e a margem de coordenação são as únicas ligadas ao modo de falha
    espira-a-espira modelado (D7 / eq. 5.2); IR/PI, tan δ e DP têm
    sensibilidade nula/baixa ou indireta a esse modo (Etapa 1 §7.1) e por
    isso recebem peso menor.
    """

    damage_electrical: float = 0.30
    damage_thermal: float = 0.25
    coordination_margin: float = 0.25
    insulation_resistance: float = 0.075
    dissipation_factor: float = 0.075
    partial_discharge: float = 0.05

    def __post_init__(self) -> None:
        for name in (
            "damage_electrical",
            "damage_thermal",
            "coordination_margin",
            "insulation_resistance",
            "dissipation_factor",
            "partial_discharge",
        ):
            value = getattr(self, name)
            if not math.isfinite(value) or value < 0.0:
                raise ValueError(f"{name} deve ser >= 0, obtido {value}")
        if self.total <= 0.0:
            raise ValueError("a soma dos pesos deve ser > 0")

    @property
    def total(self) -> float:
        """Soma dos pesos declarados."""
        return (
            self.damage_electrical
            + self.damage_thermal
            + self.coordination_margin
            + self.insulation_resistance
            + self.dissipation_factor
            + self.partial_discharge
        )

    def as_dict(self) -> dict[str, float]:
        """Pesos como dicionário, na ordem de composição."""
        return {
            "damage_electrical": self.damage_electrical,
            "damage_thermal": self.damage_thermal,
            "coordination_margin": self.coordination_margin,
            "insulation_resistance": self.insulation_resistance,
            "dissipation_factor": self.dissipation_factor,
            "partial_discharge": self.partial_discharge,
        }


@dataclass(frozen=True)
class HealthIndexThresholds:
    """Limiares de pontuação dos indicadores medidos.

    Cada campo declara sua origem: ``[NORMA]``/``[LITERATURA]`` para os
    verificados, ``CONFIGURÁVEL — NÃO CALIBRADO`` para os demais.
    """

    # [NORMA: ABNT NBR 17094-3:2018, 6.8.3] — PI mínimo classes B, F, H.
    pi_min: float = 2.0
    # [NORMA: ABNT NBR 17094-3:2018, 6.8.2, Tab. 2] — IR mínimo de
    # bobinas pré-formadas pós-1970, 40 °C, 1 min.
    ir_min_Mohm: float = 100.0
    # "isolação boa típica 10 a 100 × o mínimo" [NORMA: idem]. O valor de
    # 10× é o limite INFERIOR dessa faixa — CONFIGURÁVEL.
    ir_good_Mohm: float = 1000.0
    # [LITERATURA: Iris Power, citando IEC 60034-27-3, Tab. 1] — bobinas
    # novas a 0,2 U_N.
    tan_delta_max: float = 20.0e-3
    # CONFIGURÁVEL — NÃO CALIBRADO. Ancorado na ordem de grandeza do
    # Δtan δ por degrau e do tip-up admissíveis (5 × 10⁻³) [idem].
    tan_delta_good: float = 5.0e-3
    # [LITERATURA: Warren, IRMC 2022, Tab. 1] — percentil 90 de Q_m para
    # 2 a < 6 kV, instrumentação VHF / acopladores de 80 pF / 10 pps.
    pd_qm_alarm_mV: float = 208.0
    # [LITERATURA: idem] — percentil 25 da mesma tabela.
    pd_qm_good_mV: float = 7.0
    # [Etapa 1 §6] — fim de vida por coordenação em γ → 1.
    gamma_end_of_life: float = 1.0
    # CONFIGURÁVEL — NÃO CALIBRADO. γ = 2 como "margem sadia" é
    # convenção do módulo, não critério normativo.
    gamma_healthy: float = 2.0

    def __post_init__(self) -> None:
        if not math.isfinite(self.pi_min) or self.pi_min <= 0.0:
            raise ValueError(f"pi_min deve ser > 0, obtido {self.pi_min}")
        if not math.isfinite(self.ir_min_Mohm) or self.ir_min_Mohm <= 0.0:
            raise ValueError(
                f"ir_min_Mohm deve ser > 0 [MΩ], obtido {self.ir_min_Mohm}"
            )
        if self.ir_good_Mohm <= self.ir_min_Mohm:
            raise ValueError(
                f"ir_good_Mohm ({self.ir_good_Mohm}) deve ser > ir_min_Mohm "
                f"({self.ir_min_Mohm})"
            )
        if not math.isfinite(self.tan_delta_good) or self.tan_delta_good <= 0.0:
            raise ValueError(
                f"tan_delta_good deve ser > 0, obtido {self.tan_delta_good}"
            )
        if self.tan_delta_max <= self.tan_delta_good:
            raise ValueError(
                f"tan_delta_max ({self.tan_delta_max}) deve ser > "
                f"tan_delta_good ({self.tan_delta_good})"
            )
        if not math.isfinite(self.pd_qm_good_mV) or self.pd_qm_good_mV <= 0.0:
            raise ValueError(
                f"pd_qm_good_mV deve ser > 0 [mV], obtido {self.pd_qm_good_mV}"
            )
        if self.pd_qm_alarm_mV <= self.pd_qm_good_mV:
            raise ValueError(
                f"pd_qm_alarm_mV ({self.pd_qm_alarm_mV}) deve ser > "
                f"pd_qm_good_mV ({self.pd_qm_good_mV})"
            )
        if not math.isfinite(self.gamma_end_of_life) or self.gamma_end_of_life <= 0.0:
            raise ValueError(
                f"gamma_end_of_life deve ser > 0, obtido {self.gamma_end_of_life}"
            )
        if self.gamma_healthy <= self.gamma_end_of_life:
            raise ValueError(
                f"gamma_healthy ({self.gamma_healthy}) deve ser > "
                f"gamma_end_of_life ({self.gamma_end_of_life})"
            )


@dataclass(frozen=True)
class HealthContribution:
    """Contribuição de um componente ao AHI (saída de :meth:`explain`)."""

    name: str
    label: str
    available: bool
    score: float
    weight: float
    normalized_weight: float
    contribution_points: float
    contribution_pct: float
    basis: str


def _clamp01(x: float) -> float:
    return min(1.0, max(0.0, x))


def _linear_score(value: float, worst: float, best: float) -> float:
    """Pontuação 0-100 linear entre ``worst`` (0) e ``best`` (100)."""
    if best == worst:
        raise ValueError("best e worst não podem ser iguais")
    return 100.0 * _clamp01((value - worst) / (best - worst))


def _log_score(value: float, worst: float, best: float) -> float:
    """Pontuação 0-100 linear em escala logarítmica (decadal)."""
    if value <= 0.0 or worst <= 0.0 or best <= 0.0:
        raise ValueError("escala logarítmica exige valores > 0")
    return _linear_score(math.log10(value), math.log10(worst), math.log10(best))


@dataclass
class AssetHealthIndex:
    """Índice de saúde 0-100 do isolamento, com decomposição explicável.

    Parameters
    ----------
    D_el, D_th:
        Dano elétrico e térmico acumulados (>= 0). ``D = 1`` é a falha
        convencionada (D4, eq. 5.1).
    gamma:
        Margem de coordenação ``γ = U_w/U_s`` (Etapa 1 §6). ``None`` ⇒
        componente indisponível.
    ir_Mohm, pi:
        Resistência de isolamento a 1 min [MΩ] e índice de polarização
        [NORMA: ABNT NBR 17094-3:2018, 6.8.2-6.8.3]. Quando ambos são
        informados, o componente adota o **menor** dos dois escores
        (leitura conservadora). ``None`` em ambos ⇒ indisponível.
    tan_delta:
        Fator de dissipação a ``0,2 U_N`` [adimensional].
    pd_qm_mV:
        Magnitude de DP ``Q_m`` a 10 pulsos/s [mV].
    weights, thresholds:
        Pesos e limiares (ver as classes correspondentes).
    bands:
        Faixas de classificação; padrão :data:`DEFAULT_BANDS`
        (não normativas).
    asset_id:
        Identificação do ativo, para rastreabilidade no laudo.

    Raises
    ------
    ValueError
        Qualquer entrada fisicamente impossível: dano negativo, ``γ <= 0``,
        ``IR <= 0``, ``PI <= 0``, ``tan δ < 0``, ``Q_m < 0``, valores não
        finitos, ou ``bands`` malformadas/vazias.
    """

    D_el: float = 0.0
    D_th: float = 0.0
    gamma: float | None = None
    ir_Mohm: float | None = None
    pi: float | None = None
    tan_delta: float | None = None
    pd_qm_mV: float | None = None
    weights: HealthIndexWeights = field(default_factory=HealthIndexWeights)
    thresholds: HealthIndexThresholds = field(
        default_factory=HealthIndexThresholds
    )
    bands: tuple[tuple[float, str, str], ...] = DEFAULT_BANDS
    asset_id: str = ""

    def __post_init__(self) -> None:
        for name in ("D_el", "D_th"):
            value = getattr(self, name)
            if not math.isfinite(value) or value < 0.0:
                raise ValueError(f"{name} deve ser >= 0, obtido {value}")
        if self.gamma is not None and (
            not math.isfinite(self.gamma) or self.gamma <= 0.0
        ):
            raise ValueError(
                f"gamma (= U_w/U_s) deve ser > 0 ou None, obtido {self.gamma}"
            )
        if self.ir_Mohm is not None and (
            not math.isfinite(self.ir_Mohm) or self.ir_Mohm <= 0.0
        ):
            raise ValueError(
                f"ir_Mohm deve ser > 0 [MΩ] ou None, obtido {self.ir_Mohm}"
            )
        if self.pi is not None and (not math.isfinite(self.pi) or self.pi <= 0.0):
            raise ValueError(f"pi deve ser > 0 ou None, obtido {self.pi}")
        if self.tan_delta is not None and (
            not math.isfinite(self.tan_delta) or self.tan_delta < 0.0
        ):
            raise ValueError(
                f"tan_delta deve ser >= 0 ou None, obtido {self.tan_delta}"
            )
        if self.pd_qm_mV is not None and (
            not math.isfinite(self.pd_qm_mV) or self.pd_qm_mV < 0.0
        ):
            raise ValueError(
                f"pd_qm_mV deve ser >= 0 [mV] ou None, obtido {self.pd_qm_mV}"
            )
        if not isinstance(self.weights, HealthIndexWeights):
            raise ValueError(
                f"weights deve ser HealthIndexWeights, obtido "
                f"{type(self.weights).__name__}"
            )
        if not isinstance(self.thresholds, HealthIndexThresholds):
            raise ValueError(
                f"thresholds deve ser HealthIndexThresholds, obtido "
                f"{type(self.thresholds).__name__}"
            )
        if not self.bands:
            raise ValueError("bands não pode ser vazio")
        for band in self.bands:
            if len(band) != 3:
                raise ValueError(
                    f"cada faixa deve ser (limite, rótulo, semáforo), "
                    f"obtido {band!r}"
                )
            if not math.isfinite(float(band[0])):
                raise ValueError(f"limite de faixa não finito em {band!r}")

    # -- escores por componente --------------------------------------------

    def _score_damage_electrical(self) -> float:
        """100 (1 - min(D_el, 1)) — dano elétrico de D7 / eq. 5.2."""
        return 100.0 * (1.0 - _clamp01(self.D_el))

    def _score_damage_thermal(self) -> float:
        """100 (1 - min(D_th, 1)) — dano térmico de D6 / eq. 5.1."""
        return 100.0 * (1.0 - _clamp01(self.D_th))

    def _score_coordination(self) -> float | None:
        """Escore da margem γ entre ``gamma_end_of_life`` e ``gamma_healthy``.

        γ = 1 (fim de vida por coordenação, Etapa 1 §6) pontua 0.
        """
        if self.gamma is None:
            return None
        th = self.thresholds
        return _linear_score(self.gamma, th.gamma_end_of_life, th.gamma_healthy)

    def _score_insulation_resistance(self) -> float | None:
        """Menor entre o escore de IR (log) e o de PI (linear).

        IR: 0 pontos em ``ir_min_Mohm``, 100 em ``ir_good_Mohm``
        [NORMA: ABNT NBR 17094-3:2018, 6.8.2, Tab. 2].
        PI: 0 pontos em ``pi_min``, 100 em ``2 × pi_min``
        [NORMA: idem, 6.8.3]. O fator 2× é CONFIGURÁVEL e não normativo.
        """
        th = self.thresholds
        scores: list[float] = []
        if self.ir_Mohm is not None:
            scores.append(
                _log_score(self.ir_Mohm, th.ir_min_Mohm, th.ir_good_Mohm)
            )
        if self.pi is not None:
            scores.append(_linear_score(self.pi, th.pi_min, 2.0 * th.pi_min))
        if not scores:
            return None
        return min(scores)

    def _score_dissipation_factor(self) -> float | None:
        """100 em ``tan_delta_good``, 0 em ``tan_delta_max``."""
        if self.tan_delta is None:
            return None
        th = self.thresholds
        return _linear_score(self.tan_delta, th.tan_delta_max, th.tan_delta_good)

    def _score_partial_discharge(self) -> float | None:
        """Escore log de ``Q_m``: 100 no percentil 25, 0 no percentil 90."""
        if self.pd_qm_mV is None:
            return None
        th = self.thresholds
        value = max(self.pd_qm_mV, 1.0e-6)  # log exige > 0
        return _log_score(value, th.pd_qm_alarm_mV, th.pd_qm_good_mV)

    # -- composição ---------------------------------------------------------

    def _components(self) -> list[tuple[str, str, float | None, float, str]]:
        """``(nome, rótulo, escore ou None, peso, base de rastreabilidade)``."""
        w = self.weights
        return [
            (
                "damage_electrical",
                "Dano elétrico acumulado D_el",
                self._score_damage_electrical(),
                w.damage_electrical,
                "D7 / eq. (5.2) — Etapa 1 §5.4; Etapa 2 §5.2",
            ),
            (
                "damage_thermal",
                "Dano térmico acumulado D_th",
                self._score_damage_thermal(),
                w.damage_thermal,
                "D6 / eq. (5.1) — Miner contínuo, Arrhenius/Montsinger",
            ),
            (
                "coordination_margin",
                "Margem de coordenação γ = U_w/U_s",
                self._score_coordination(),
                w.coordination_margin,
                "Etapa 1 §6; IEC 60071-1:2019, 3.31 e 3.34",
            ),
            (
                "insulation_resistance",
                "IR / PI",
                self._score_insulation_resistance(),
                w.insulation_resistance,
                "ABNT NBR 17094-3:2018, 6.8.2 Tab. 2 e 6.8.3",
            ),
            (
                "dissipation_factor",
                "Fator de dissipação tan δ",
                self._score_dissipation_factor(),
                w.dissipation_factor,
                "IEC 60034-27-3:2015, Tab. 1 (via Iris Power)",
            ),
            (
                "partial_discharge",
                "Descargas parciais Q_m",
                self._score_partial_discharge(),
                w.partial_discharge,
                "Warren, IRMC 2022, Tab. 1 (VHF, 80 pF, 10 pps)",
            ),
        ]

    @property
    def index(self) -> float:
        """AHI 0-100: média dos escores disponíveis ponderada pelos pesos."""
        num = 0.0
        den = 0.0
        for _, _, score, weight, _ in self._components():
            if score is None or weight <= 0.0:
                continue
            num += weight * score
            den += weight
        if den <= 0.0:
            raise ValueError(
                "nenhum componente disponível com peso > 0: o AHI não pode "
                "ser calculado"
            )
        return num / den

    @property
    def classification(self) -> str:
        """Rótulo da faixa (``BOM``/``ACEITAVEL``/``DEGRADADO``/``CRITICO``)."""
        return self._band()[1]

    @property
    def traffic_light(self) -> str:
        """Semáforo da faixa (``verde``/``amarelo``/``laranja``/``vermelho``)."""
        return self._band()[2]

    def _band(self) -> tuple[float, str, str]:
        value = self.index
        for lower, label, light in self.bands:
            if value >= lower:
                return (float(lower), str(label), str(light))
        return (
            float(self.bands[-1][0]),
            str(self.bands[-1][1]),
            str(self.bands[-1][2]),
        )

    def explain(self) -> list[HealthContribution]:
        """Decomposição do AHI por contribuição.

        ``contribution_pct`` **soma 100 %** sobre os componentes
        disponíveis. Quando o índice é 0 (todos os escores nulos), a
        participação percentual degrada para a participação de peso, de
        modo que a soma continua sendo 100 %.

        Componentes indisponíveis aparecem com ``available=False``,
        ``normalized_weight=0`` e contribuição nula — o requisito de
        explicabilidade exige que a ausência de dado seja visível, não
        omitida.
        """
        comps = self._components()
        den = sum(w for _, _, s, w, _ in comps if s is not None and w > 0.0)
        if den <= 0.0:
            raise ValueError(
                "nenhum componente disponível com peso > 0: o AHI não pode "
                "ser explicado"
            )
        total_index = self.index
        out: list[HealthContribution] = []
        for name, label, score, weight, basis in comps:
            available = score is not None and weight > 0.0
            nw = (weight / den) if available else 0.0
            points = nw * (score or 0.0)
            if not available:
                pct = 0.0
            elif total_index > 0.0:
                pct = 100.0 * points / total_index
            else:
                pct = 100.0 * nw
            out.append(
                HealthContribution(
                    name=name,
                    label=label,
                    available=available,
                    score=float(score) if score is not None else 0.0,
                    weight=weight,
                    normalized_weight=nw,
                    contribution_points=points,
                    contribution_pct=pct,
                    basis=basis,
                )
            )
        return out

    def summary(self) -> str:
        """Resumo textual determinístico para laudo/console."""
        lines = [
            f"Índice de saúde do isolamento (AHI) — "
            f"{self.asset_id or '(ativo sem identificação)'}",
            f"  AHI ............ {self.index:.2f} / 100 "
            f"[{self.classification} / {self.traffic_light}]",
            "  Decomposição por contribuição:",
        ]
        for c in self.explain():
            if c.available:
                lines.append(
                    f"    • {c.label}: escore {c.score:.2f}, peso "
                    f"{c.normalized_weight * 100:.1f} %, contribuição "
                    f"{c.contribution_pct:.1f} % — {c.basis}"
                )
            else:
                lines.append(
                    f"    • {c.label}: SEM DADO (excluído da renormalização) "
                    f"— {c.basis}"
                )
        lines.append(
            "  Faixas de classificação NÃO NORMATIVAS (convenção do módulo, "
            "configuráveis)."
        )
        lines.append(
            "  IR/PI, tan δ e DP têm sensibilidade nula/baixa ou indireta ao "
            "dano espira-a-espira e não predizem tempo até a falha "
            "[IEC 60034-27-2:2023 e -27-4:2018, Introdução]."
        )
        return "\n".join(lines)
