"""
app.simulation.emt.cases.motor_switching — caso de manobra de motor do
Documento A, montado parametricamente sobre o kernel EMT dedicado.

Cenário
=======

Interrupção **intempestiva** da partida de um motor de indução de
1250 kW / 4,16 kV / 60 Hz, comandada pela proteção enquanto a máquina
drena a corrente de partida — "the chopping of a large inductive current
under the worst possible conditions" [FATO: doc A, p. 3, V].

Topologia montada (uma célula por fase)::

    fonte 60 Hz ──[R_tx, L_tx]── barra ──[cabo a montante]── VCB ──┬── [cabo a jusante] ── motor R–L ── neutro
     (src_X)                     (bus_X)   (cb_src_X)  (cb_load_X) │      (mot_X)              │
                                                                   └── snubber (opcional) ─────┘

* fonte trifásica equilibrada de 60 Hz, com a fase inicial comum
  ``phase_deg`` — **o parâmetro do Monte Carlo de instante de abertura**;
* transformador abaixador representado pela impedância de dispersão
  referida ao lado de 4,16 kV (ramo R–L série por fase);
* dois cabos a parâmetros distribuídos, a montante e a jusante do
  disjuntor, no modelo de Bergeron (padrão) ou JMarti dependente da
  frequência (``CableParameters(model="jmarti")``);
* um polo de :class:`~app.simulation.emt.vcb.VacuumCircuitBreakerModel`
  por fase, com escalonamento dos instantes de separação;
* *snubber* ativo opcional
  (:class:`~app.simulation.emt.snubber.ThyristorSnubber`) entre a barra
  do lado de carga do VCB e o neutro;
* motor representado por ramo R–L série concentrado, em paralelo com a
  capacitância parasita para a terra.

As duas parametrizações do ramo R–L
====================================

A Etapa 2 §1.3 do estudo de RUL registra uma **inconsistência interna do
Documento A** que este módulo NÃO resolve — expõe
[REPO: docs/research/rul_isolamento/02_ETAPA2_cruzamento_A_x_B.md:83]:

* a **Tabela I** de A declara ``I_p/I_n = 6,5``, o que com
  ``I_n = 207,52 A`` significa ``1348,9 A``
  [FATO: doc A, Tabela I, p. 3];
* o **quadro da Fig. 2** ("MOTOR R-L MODEL REPORT FOR ATP (TRV)") declara
  ``|Z_eq| = 3,4550 Ω``, ``R_eq = 0,691 Ω``, ``L_eq = 8,9795 mH``, que a
  ``2401,78 V`` de fase drenam ``695,2 A = 3,35 I_n`` — e **não**
  ``6,5 I_n`` [FATO: doc A, Fig. 2, p. 4 — leitura de figura;
  CÁLCULO PRÓPRIO].

A energia magnética do reservatório difere por ``(6,5/3,35)² = 3,77×``
entre as duas leituras, e todo pico de TRV que dela dependa herda esse
fator. Por isso os dois conjuntos são oferecidos:

* :data:`RL_VARIANT_FIG2` — o ramo **tal como parametrizado** na Fig. 2
  (3,35 ``I_n``). É o padrão, porque é o que o modelo de A efetivamente
  simulou, e portanto o que reproduz a Tabela III.
* :data:`RL_VARIANT_TABLE_I` — o ramo **reescalado** para drenar os
  ``6,5 I_n`` da Tabela I, mantido o mesmo fator de potência de rotor
  bloqueado (0,200). É o cenário que o rótulo do artigo promete.

Nenhum dos dois é "o correto": a discrepância é pergunta aberta dirigida
aos autores de A (Q3 da Etapa 2 §11.3).

Advertência de comparação
==========================

A Tabela III de A (:data:`DOC_A_TABLE_III`) é reproduzida aqui como
referência de confronto, **não** como critério de aceite deste módulo. O
kernel usa linha de parâmetros CONSTANTES (Bergeron) e A usa JMARTI
dependente da frequência; A não publica comprimento do cabo a jusante,
capacitância parasita do motor, impedância de fonte, nível de *breakover*
do DIAC nem o módulo da tensão de fonte [FATO por omissão]. Concordância
numérica com a Tabela III seria coincidência, não validação.

Sem I/O, sem GUI. Determinístico para uma dada semente.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, replace

import numpy as np

from app.core.logging_config import get_logger
from app.simulation.emt.circuit import Circuit, Solver, SolverResult
from app.simulation.emt.components import (
    Capacitor,
    Inductor,
    Resistor,
    Switch,
    three_phase_voltage_sources,
)
from app.simulation.emt.jmarti import (
    JMartiLine,
    LineFrequencyData,
    ModalLineModel,
    frequency_grid_for_delay,
)
from app.simulation.emt.line import BergeronLine
from app.simulation.emt.probes import (
    BranchCurrentProbe,
    DifferentialVoltageProbe,
    NodeVoltageProbe,
)
from app.simulation.emt.snubber import (
    DOC_A_SNUBBER_RESISTANCE_OHM,
    SnubberBranch,
    three_phase_snubber,
)
from app.simulation.emt.vcb import (
    DIDT_INTERRUPT_WITHIN,
    DOC_A_CHOPPING_RANGE_A,
    DOC_A_DIDT_RANGE_A_PER_US,
    DOC_A_RRDS_A_KV_PER_MS,
    DOC_A_RRDS_B_KV_PER_MS2,
    DOC_A_STAGGER_RANGE_S,
    DOC_A_TIME_STEP_S,
    DOC_A_WINDOW_S,
    ParabolicRecovery,
    VacuumCircuitBreakerModel,
    stagger_times,
)

log = get_logger(__name__)

#: Nomes das fases, na ordem A, B, C.
PHASES: tuple[str, ...] = ("a", "b", "c")

#: Variante do ramo R–L **tal como parametrizado** na Fig. 2 de A
#: (``R = 0,691 Ω``, ``L = 8,9795 mH``, corrente resultante 3,35 ``I_n``).
RL_VARIANT_FIG2: str = "fig2"

#: Variante reescalada para os ``6,5 I_n`` da Tabela I de A, com o mesmo
#: fator de potência de rotor bloqueado da Fig. 2.
RL_VARIANT_TABLE_I: str = "table_i"

#: Variantes aceitas.
RL_VARIANTS: tuple[str, ...] = (RL_VARIANT_FIG2, RL_VARIANT_TABLE_I)

#: Impedância equivalente por fase lida no quadro da Fig. 2 [Ω]
#: [FATO: doc A, Fig. 2, p. 4 — leitura de figura].
DOC_A_FIG2_R_OHM: float = 0.691
DOC_A_FIG2_L_H: float = 8.9795e-3

#: Tabela III de A — pico de TRV [kV] e RRRV [kV/µs] no disjuntor
#: [FATO: doc A, Tabela III, p. 3]. Referência de CONFRONTO, não de
#: aceite — ver a advertência no cabeçalho do módulo.
DOC_A_TABLE_III: dict[str, dict[str, tuple[float, float]]] = {
    "sem_snubber": {
        "a": (-30.24, 13.90),
        "b": (41.44, 15.05),
        "c": (-38.30, 19.00),
    },
    "com_snubber": {
        "a": (6.35, 3.28),
        "b": (13.65, 13.11),
        "c": (-9.98, 9.43),
    },
}


# ---------------------------------------------------------------------------
# Parâmetros
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SourceParameters:
    """Fonte trifásica equilibrada a montante.

    Attributes
    ----------
    line_voltage_V:
        Tensão de linha eficaz [V]; padrão 4160 [FATO: doc A, Tabela I].
    frequency_Hz:
        Frequência [Hz]; padrão 60 [FATO: doc A, Tabela I].
    phase_deg:
        Fase inicial comum das três fontes [graus]. **É o parâmetro do
        Monte Carlo de instante de abertura**: varrer ``phase_deg`` em
        [0, 360) equivale a varrer o ponto da onda em que os contatos se
        separam, mantendo fixos os instantes de separação.
    sequence:
        ``"abc"`` (padrão) ou ``"acb"``.
    magnitude_pu:
        Módulo da tensão de fonte em pu da nominal; padrão 1,0.
        **[HIPÓTESE]** A não declara o módulo da tensão de fonte
        [FATO por omissão]; 1,0 pu é a hipótese da Etapa 2 §10.2, item 2.
        A corrida a ``V_min`` (afundamento por partida sob N-1) é o caso
        novo e não tem referência publicada.
    """

    line_voltage_V: float = 4160.0
    frequency_Hz: float = 60.0
    phase_deg: float = 0.0
    sequence: str = "abc"
    magnitude_pu: float = 1.0

    def __post_init__(self) -> None:
        _require_positive(self.line_voltage_V, "line_voltage_V")
        _require_positive(self.frequency_Hz, "frequency_Hz")
        _require_positive(self.magnitude_pu, "magnitude_pu")
        if not math.isfinite(float(self.phase_deg)):
            raise ValueError(f"phase_deg deve ser finito, obtido {self.phase_deg!r}")
        if str(self.sequence) not in ("abc", "acb"):
            raise ValueError(f"sequence deve ser 'abc' ou 'acb', obtida {self.sequence!r}")

    @property
    def phase_voltage_rms_V(self) -> float:
        """Tensão de fase eficaz [V] — 2401,78 V para 4,16 kV."""
        return self.magnitude_pu * self.line_voltage_V / math.sqrt(3.0)

    @property
    def phase_voltage_peak_V(self) -> float:
        """Tensão de fase de pico [V] — 3396,6 V para 4,16 kV (base 1 pu)."""
        return math.sqrt(2.0) * self.phase_voltage_rms_V


@dataclass(frozen=True)
class TransformerParameters:
    """Transformador abaixador pela impedância de dispersão.

    A Fig. 2 de A mostra um transformador Δ–Y ("BCT") entre a fonte e a
    barra de 4,16 kV, mas **nenhum dado elétrico é publicado**
    [FATO: doc A, Fig. 2, p. 4; FATO por omissão]. Os padrões vêm da
    reconstrução da planta feita na Etapa 2 §10.1 a partir do Documento B
    (7,5/9 MVA, ``X_HL = 8 %`` na base de 7,5 MVA) — **[HIPÓTESE]** quanto
    a A.

    O ramo é modelado como ``R + jX`` série por fase, referido ao lado de
    4,16 kV. A defasagem angular de 30° do Δ–Y e a capacitância entre
    enrolamentos — caminho dominante de transferência de surto de frente
    rápida — **não** são representadas (limitação
    ``emt_linear_components_only`` do kernel).

    Attributes
    ----------
    rating_MVA:
        Potência nominal da base da impedância percentual [MVA].
    impedance_pct:
        Impedância percentual na base ``rating_MVA``.
    x_over_r:
        Relação X/R do ramo de dispersão.
    """

    rating_MVA: float = 7.5
    impedance_pct: float = 8.0
    x_over_r: float = 10.0

    def __post_init__(self) -> None:
        _require_positive(self.rating_MVA, "rating_MVA")
        _require_positive(self.impedance_pct, "impedance_pct")
        _require_positive(self.x_over_r, "x_over_r")

    def series_rl(self, line_voltage_V: float, frequency_Hz: float) -> tuple[float, float]:
        """Devolve ``(R [Ω], L [H])`` por fase, referidos a ``line_voltage_V``.

        ``Z_base = U²/S``; ``|Z| = z% · Z_base / 100``;
        ``R = |Z|/sqrt(1 + (X/R)²)``; ``X = R·(X/R)``; ``L = X/(2πf)``.
        """
        u = _require_positive(line_voltage_V, "line_voltage_V")
        f = _require_positive(frequency_Hz, "frequency_Hz")
        z_base = u * u / (self.rating_MVA * 1.0e6)
        z_mag = self.impedance_pct * z_base / 100.0
        r = z_mag / math.sqrt(1.0 + self.x_over_r**2)
        x = r * self.x_over_r
        return r, x / (2.0 * math.pi * f)


#: Modelo de cabo a parâmetros CONSTANTES (Bergeron) — padrão do caso.
CABLE_MODEL_BERGERON: str = "bergeron"

#: Modelo de cabo com DEPENDÊNCIA DE FREQUÊNCIA (JMarti), o que o
#: Documento A declara ter usado ("LCC/JMARTI") [FATO: doc A, p. 3].
CABLE_MODEL_JMARTI: str = "jmarti"

#: Modelos de cabo aceitos por :attr:`CableParameters.model`.
CABLE_MODELS: tuple[str, ...] = (CABLE_MODEL_BERGERON, CABLE_MODEL_JMARTI)


@dataclass(frozen=True)
class CableParameters:
    """Cabo de média tensão a parâmetros distribuídos constantes.

    A Fig. 2 de A rotula o cabo a montante do VCB como "0.5 km" e
    "185mm²" e o cabo a jusante como "240mm²" **sem comprimento**
    [FATO: doc A, Fig. 2, p. 4 — leitura de figura; FATO por omissão para
    o comprimento a jusante]. A não publica ``L'``, ``C'`` nem ``R'`` de
    nenhum dos dois.

    Os padrões de ``L'`` e ``C'`` são valores de ordem de grandeza para
    cabo unipolar de MT com isolação XLPE, e produzem
    ``Z_c = 37,4 Ω`` e velocidade de propagação ``1,07·10⁸ m/s``
    (0,36 c) [CÁLCULO PRÓPRIO], compatíveis com a faixa de 30 a 80 Ω
    reportada para cabos de MT na Etapa 1 §2.3. **[HIPÓTESE]** — devem
    ser substituídos pelos dados do cabo real do estudo.

    Attributes
    ----------
    length_m:
        Comprimento [m], > 0.
    inductance_H_per_m, capacitance_F_per_m, resistance_ohm_per_m:
        Parâmetros distribuídos.
    model:
        ``"bergeron"`` (padrão, parâmetros constantes) ou ``"jmarti"``
        (dependente da frequência). A Fig. 2 de A declara cabos
        ``LCC/JMARTI`` [FATO: doc A, p. 3], de modo que ``"jmarti"`` é o
        que se aproxima do modelo do artigo; o padrão continua sendo o
        Bergeron para preservar a comparabilidade com os resultados já
        publicados deste módulo.
    fit_f_min_Hz, fit_f_max_Hz:
        Faixa de frequência das tabelas geradas para o ajuste racional
        [Hz]. O teto de 2 MHz cobre uma frente de ~0,2 µs
        [INFERÊNCIA FÍSICA: ``f ≈ 0,35/t_f``].
    fit_poles_zc, fit_poles_a:
        Ordem do ajuste de ``Z_c`` e de ``A_min``.
    fit_tolerance:
        Erro RMS relativo máximo tolerado no ajuste; acima dele a
        montagem levanta ``RationalFitError``.
    """

    length_m: float = 500.0
    inductance_H_per_m: float = 0.35e-6
    capacitance_F_per_m: float = 0.25e-9
    resistance_ohm_per_m: float = 0.10e-3
    model: str = CABLE_MODEL_BERGERON
    fit_f_min_Hz: float = 1.0
    fit_f_max_Hz: float = 2.0e6
    fit_poles_zc: int = 6
    fit_poles_a: int = 10
    fit_tolerance: float = 2.0e-2

    def __post_init__(self) -> None:
        _require_positive(self.length_m, "length_m")
        _require_positive(self.inductance_H_per_m, "inductance_H_per_m")
        _require_positive(self.capacitance_F_per_m, "capacitance_F_per_m")
        if float(self.resistance_ohm_per_m) < 0.0:
            raise ValueError(
                f"resistance_ohm_per_m deve ser >= 0, obtido {self.resistance_ohm_per_m!r}"
            )
        if str(self.model) not in CABLE_MODELS:
            raise ValueError(
                f"model deve ser um de {CABLE_MODELS}, obtido {self.model!r}"
            )
        _require_positive(self.fit_f_min_Hz, "fit_f_min_Hz")
        _require_positive(self.fit_f_max_Hz, "fit_f_max_Hz")
        if float(self.fit_f_max_Hz) <= float(self.fit_f_min_Hz):
            raise ValueError(
                f"fit_f_max_Hz ({self.fit_f_max_Hz!r}) deve ser > fit_f_min_Hz "
                f"({self.fit_f_min_Hz!r})"
            )
        if int(self.fit_poles_zc) < 0 or int(self.fit_poles_a) < 0:
            raise ValueError("fit_poles_zc e fit_poles_a devem ser >= 0")
        _require_positive(self.fit_tolerance, "fit_tolerance")

    @property
    def surge_impedance_ohm(self) -> float:
        """``Z_c = sqrt(L'/C')`` [Ω]."""
        return math.sqrt(self.inductance_H_per_m / self.capacitance_F_per_m)

    @property
    def travel_time_s(self) -> float:
        """``τ = ℓ·sqrt(L'C')`` [s]."""
        return self.length_m * math.sqrt(
            self.inductance_H_per_m * self.capacitance_F_per_m
        )

    def frequency_data(self, label: str = "cabo") -> LineFrequencyData:
        """Tabelas ``Z_c(ω)``/``A(ω)`` deste cabo, para o ajuste JMarti.

        A malha é dimensionada por
        :func:`~app.simulation.emt.jmarti.frequency_grid_for_delay` a
        partir do ``τ`` nominal, de modo que a extração do atraso não
        sofra *aliasing* de fase.

        **[HIPÓTESE]** As tabelas são geradas do modelo ``R'L'C'`` com
        ``R'`` CONSTANTE — não há efeito pelicular nem retorno pela
        terra. A dependência de frequência resultante é a de uma linha
        com perdas ôhmicas puras, que é MENOS acentuada que a real. Para
        o estudo definitivo, substitua por tabelas do cálculo de
        parâmetros do próprio caso ATP (``CABLE CONSTANTS``), que é o
        caminho primário previsto em
        :class:`~app.simulation.emt.jmarti.LineFrequencyData`.
        """
        omega = frequency_grid_for_delay(
            self.travel_time_s,
            f_min_Hz=float(self.fit_f_min_Hz),
            f_max_Hz=float(self.fit_f_max_Hz),
        )
        return LineFrequencyData.from_distributed_parameters(
            length_m=self.length_m,
            inductance_H_per_m=self.inductance_H_per_m,
            capacitance_F_per_m=self.capacitance_F_per_m,
            resistance_ohm_per_m=self.resistance_ohm_per_m,
            omega=omega,
            label=label,
        )

    def modal_model(self, label: str = "cabo") -> ModalLineModel:
        """Ajusta o modelo JMarti deste cabo (um modo)."""
        return ModalLineModel.fit(
            self.frequency_data(label),
            n_poles_yc=int(self.fit_poles_zc),
            n_poles_a=int(self.fit_poles_a),
            tolerance=float(self.fit_tolerance),
            label=label,
        )

    def build(self, name: str, node_k: str, node_m: str) -> BergeronLine | JMartiLine:
        """Instancia a linha no modelo selecionado por :attr:`model`.

        ``"bergeron"`` (padrão) devolve
        :class:`~app.simulation.emt.line.BergeronLine`; ``"jmarti"``
        devolve :class:`~app.simulation.emt.jmarti.JMartiLine` com
        ajuste racional feito na hora. As duas classes têm a MESMA
        interface de componente, de modo que nada mais do caso muda.
        """
        if str(self.model) == CABLE_MODEL_JMARTI:
            return JMartiLine(name, node_k, node_m, model=self.modal_model(name))
        return BergeronLine.from_distributed_parameters(
            name,
            node_k,
            node_m,
            length_m=self.length_m,
            inductance_H_per_m=self.inductance_H_per_m,
            capacitance_F_per_m=self.capacitance_F_per_m,
            resistance_ohm_per_m=self.resistance_ohm_per_m,
        )


@dataclass(frozen=True)
class MotorParameters:
    """Motor de indução equivalente (Tabela I de A).

    Todos os valores de placa são [FATO: doc A, Tabela I, p. 3].

    Attributes
    ----------
    rated_power_W:
        Potência nominal no eixo [W]; 1 250 000.
    line_voltage_V:
        Tensão de linha [V]; 4160.
    frequency_Hz:
        Frequência [Hz]; 60.
    efficiency:
        Rendimento; 0,95.
    power_factor:
        Fator de potência nominal; 0,88.
    starting_ratio:
        ``I_p/I_n``; 6,5.
    locked_rotor_power_factor:
        Fator de potência de rotor bloqueado; 0,200, obtido de
        ``R_eq/|Z_eq| = 0,691/3,4550`` do quadro da Fig. 2
        [FATO: doc A, Fig. 2, p. 4 — leitura de figura; CÁLCULO PRÓPRIO].
    stray_capacitance_F:
        Capacitância parasita fase-terra dos terminais e do enrolamento
        [F]. **[HIPÓTESE]** A não a publica [FATO por omissão]; 5 nF é
        valor de ordem de grandeza para máquina de MT desta faixa de
        potência. É o parâmetro que fixa a impedância de surto do
        reservatório: o pico de corte vale ``I_ch·sqrt(L/C)``, de modo
        que reduzi-la para 2 nF eleva o pico em ``sqrt(5/2) = 1,58×``
        [CÁLCULO PRÓPRIO].
    """

    rated_power_W: float = 1.25e6
    line_voltage_V: float = 4160.0
    frequency_Hz: float = 60.0
    efficiency: float = 0.95
    power_factor: float = 0.88
    starting_ratio: float = 6.5
    locked_rotor_power_factor: float = DOC_A_FIG2_R_OHM / 3.4550
    stray_capacitance_F: float = 5.0e-9

    def __post_init__(self) -> None:
        _require_positive(self.rated_power_W, "rated_power_W")
        _require_positive(self.line_voltage_V, "line_voltage_V")
        _require_positive(self.frequency_Hz, "frequency_Hz")
        _require_positive(self.starting_ratio, "starting_ratio")
        _require_positive(self.stray_capacitance_F, "stray_capacitance_F")
        for label, value in (
            ("efficiency", self.efficiency),
            ("power_factor", self.power_factor),
            ("locked_rotor_power_factor", self.locked_rotor_power_factor),
        ):
            v = float(value)
            if not (0.0 < v <= 1.0):
                raise ValueError(f"{label} deve estar em (0, 1], obtido {value!r}")

    @property
    def phase_voltage_rms_V(self) -> float:
        """Tensão de fase eficaz nominal [V] — 2401,78 V."""
        return self.line_voltage_V / math.sqrt(3.0)

    @property
    def rated_current_A(self) -> float:
        """``I_n = P/(sqrt(3)·U·η·fp)`` [A] — 207,52 A [CÁLCULO PRÓPRIO]."""
        return self.rated_power_W / (
            math.sqrt(3.0) * self.line_voltage_V * self.efficiency * self.power_factor
        )

    @property
    def starting_current_A(self) -> float:
        """``I_p = (I_p/I_n)·I_n`` [A] — 1348,85 A [CÁLCULO PRÓPRIO]."""
        return self.starting_ratio * self.rated_current_A

    def locked_rotor_branch(self, variant: str = RL_VARIANT_FIG2) -> tuple[float, float]:
        """Devolve ``(R [Ω], L [H])`` do ramo R–L da variante escolhida.

        ``RL_VARIANT_FIG2`` devolve exatamente os valores lidos no quadro
        da Fig. 2 (``0,691 Ω`` e ``8,9795 mH``). ``RL_VARIANT_TABLE_I``
        recalcula ``|Z| = V_fase/I_p`` mantendo o mesmo fator de potência
        de rotor bloqueado — 0,356 Ω e 4,628 mH [CÁLCULO PRÓPRIO].

        Raises
        ------
        ValueError
            Variante desconhecida.
        """
        v = str(variant)
        if v == RL_VARIANT_FIG2:
            return DOC_A_FIG2_R_OHM, DOC_A_FIG2_L_H
        if v == RL_VARIANT_TABLE_I:
            z = self.phase_voltage_rms_V / self.starting_current_A
            cos_phi = float(self.locked_rotor_power_factor)
            sin_phi = math.sqrt(max(0.0, 1.0 - cos_phi * cos_phi))
            r = z * cos_phi
            x = z * sin_phi
            return r, x / (2.0 * math.pi * self.frequency_Hz)
        raise ValueError(f"variante de ramo R–L deve ser uma de {RL_VARIANTS}, obtida {variant!r}")

    def chopping_peak_V(self, chopping_current_A: float, variant: str = RL_VARIANT_FIG2) -> float:
        """Pico do primeiro corte por balanço de energia [V].

        ``½L·I_ch² = ½C·V²`` ⇒ ``V = I_ch·sqrt(L/C)``
        [LITERATURA: A. Greenwood, *Electrical Transients in Power
        Systems*, 2. ed., Wiley, 1991, cap. 5]. É a **cota superior sem
        amortecimento e sem reignição** do primeiro pico, não o pico da
        sequência.
        """
        _, l_h = self.locked_rotor_branch(variant)
        return float(chopping_current_A) * math.sqrt(l_h / self.stray_capacitance_F)


@dataclass(frozen=True)
class VCBParameters:
    """Disjuntor a vácuo (Tabela II de A).

    Attributes
    ----------
    separation_times_s:
        Instantes de separação por polo [s]. ``None`` (padrão) usa
        :func:`~app.simulation.emt.vcb.stagger_times` sobre a faixa de A
        (14 a 25 ms).
    chopping_range_A:
        Faixa de ``I_ch`` [A]; (1,0; 2,0) de A.
    chopping_current_A:
        ``I_ch`` determinístico [A]; ``None`` usa faixa + distribuição.
    seed:
        Semente EXPLÍCITA do Monte Carlo de ``I_ch``; ``None`` ⇒
        realização determinística (ponto médio da faixa).
    rrds_a_kV_per_ms, rrds_b_kV_per_ms2:
        Constantes da lei parabólica ``V_wth = A·t + B·t²``.
    didt_capability_A_per_us:
        Capacidade de extinção de alta frequência [A/µs].
    didt_convention:
        Convenção do critério de ``di/dt`` — ver
        :mod:`app.simulation.emt.vcb`.
    max_reignitions:
        Teto de reignições por polo.
    """

    separation_times_s: tuple[float, ...] | None = None
    chopping_range_A: tuple[float, float] = DOC_A_CHOPPING_RANGE_A
    chopping_current_A: float | None = None
    seed: int | None = None
    rrds_a_kV_per_ms: float = DOC_A_RRDS_A_KV_PER_MS
    rrds_b_kV_per_ms2: float = DOC_A_RRDS_B_KV_PER_MS2
    didt_capability_A_per_us: float = DOC_A_DIDT_RANGE_A_PER_US[1]
    didt_convention: str = DIDT_INTERRUPT_WITHIN
    max_reignitions: int = 200

    def times(self, n_poles: int = 3) -> tuple[float, ...]:
        """Instantes de separação efetivos [s]."""
        if self.separation_times_s is None:
            return stagger_times(n_poles, span_s=DOC_A_STAGGER_RANGE_S)
        times = tuple(float(t) for t in self.separation_times_s)
        if len(times) != n_poles:
            raise ValueError(
                f"separation_times_s tem {len(times)} instantes para {n_poles} polos"
            )
        return times

    @property
    def recovery(self) -> ParabolicRecovery:
        """Lei de recuperação dielétrica correspondente."""
        return ParabolicRecovery(
            a_kV_per_ms=self.rrds_a_kV_per_ms, b_kV_per_ms2=self.rrds_b_kV_per_ms2
        )


@dataclass(frozen=True)
class SnubberParameters:
    """*Snubber* ativo a tiristor (Seção III de A).

    Attributes
    ----------
    enabled:
        Insere ou não o ramo. ``False`` (padrão) reproduz o caso "sem
        snubber" da Tabela III.
    resistance_ohm:
        ``R_s`` por fase [Ω]; 30,0 de A.
    breakover_voltage_V:
        Nível de disparo do DIAC [V]. **Obrigatório quando
        ``enabled=True``**: A não o publica [FATO por omissão].
    holding_current_A:
        Corrente de manutenção [A].
    single_shot:
        Dispara uma única vez por manobra.
    """

    enabled: bool = False
    resistance_ohm: float = DOC_A_SNUBBER_RESISTANCE_OHM
    breakover_voltage_V: float | None = None
    holding_current_A: float = 0.0
    single_shot: bool = False

    def __post_init__(self) -> None:
        if self.enabled and self.breakover_voltage_V is None:
            raise ValueError(
                "snubber habilitado exige breakover_voltage_V explícito: o "
                "Documento A NÃO informa o nível de breakover do DIAC "
                "[FATO por omissão] e um padrão silencioso disfarçaria uma "
                "escolha do implementador como dado do artigo"
            )
        _require_positive(self.resistance_ohm, "resistance_ohm")


# ---------------------------------------------------------------------------
# Caso e modelo montado
# ---------------------------------------------------------------------------


@dataclass
class MotorSwitchingModel:
    """Montagem executável do caso.

    Attributes
    ----------
    case:
        Parâmetros que geraram esta montagem.
    circuit:
        Circuito montado.
    solver:
        Solver configurado com ``dt`` do caso.
    poles:
        Um :class:`VacuumCircuitBreakerModel` por fase.
    snubbers:
        Ramos de *snubber* por fase (vazio se desabilitado).
    controllers:
        Todos os controladores, na ordem de avaliação (VCB antes do
        *snubber*: o *snubber* deve reagir à tensão já produzida pela
        manobra do passo).
    trv_probes, bus_probes, motor_probes, current_probes:
        Sondas por fase, indexadas pelo rótulo ``"a"``, ``"b"``, ``"c"``.
    """

    case: "MotorSwitchingCase"
    circuit: Circuit
    solver: Solver
    poles: tuple[VacuumCircuitBreakerModel, ...]
    snubbers: tuple[SnubberBranch, ...]
    controllers: tuple
    trv_probes: dict = field(default_factory=dict)
    bus_probes: dict = field(default_factory=dict)
    motor_probes: dict = field(default_factory=dict)
    current_probes: dict = field(default_factory=dict)

    def run(self, t_end: float | None = None) -> SolverResult:
        """Executa a janela do caso e devolve as estatísticas do solver."""
        for ctrl in self.controllers:
            reset = getattr(ctrl, "reset", None)
            if callable(reset):
                reset()
        return self.solver.run(
            t_end=float(t_end) if t_end is not None else self.case.t_end_s,
            controllers=list(self.controllers),
        )

    @property
    def reignition_counts(self) -> dict[str, int]:
        """Reignições por fase — o ``n_r`` de ``s_{m,j}`` por polo."""
        return {ph: pole.reignition_count for ph, pole in zip(PHASES, self.poles)}

    @property
    def snubber_energy_J(self) -> dict[str, float]:
        """Energia dissipada em ``R_s`` por fase [J]."""
        return {
            ph: branch.controller.energy_J
            for ph, branch in zip(PHASES, self.snubbers)
        }

    def trv_summary(self) -> dict[str, tuple[float, float]]:
        """Pico de TRV [kV] e RRRV máxima [kV/µs] por fase.

        O pico é reportado **com sinal** (o da amostra de maior módulo),
        como na Tabela III de A. A RRRV é a maior derivada numérica de
        primeira ordem entre amostras consecutivas, em kV/µs — leia-a
        como **cota inferior** do valor real quando o passo for da ordem
        do tempo de frente (Etapa 1 §3.3).
        """
        out: dict[str, tuple[float, float]] = {}
        for ph, probe in self.trv_probes.items():
            if probe.n_samples < 2:
                out[ph] = (0.0, 0.0)
                continue
            v_kV = probe.values * 1.0e-3
            t_us = probe.time_s * 1.0e6
            idx = int(np.argmax(np.abs(v_kV)))
            dv = np.diff(v_kV)
            dtu = np.diff(t_us)
            with np.errstate(divide="ignore", invalid="ignore"):
                slope = np.where(dtu > 0.0, np.abs(dv) / np.where(dtu > 0.0, dtu, 1.0), 0.0)
            out[ph] = (float(v_kV[idx]), float(np.max(slope)) if slope.size else 0.0)
        return out


@dataclass(frozen=True)
class MotorSwitchingCase:
    """Parâmetros completos do caso do Documento A.

    Attributes
    ----------
    source, transformer, cable_upstream, cable_downstream, motor, vcb, snubber:
        Blocos de parâmetros.
    rl_variant:
        :data:`RL_VARIANT_FIG2` (padrão) ou :data:`RL_VARIANT_TABLE_I` —
        ver a discussão no cabeçalho do módulo.
    dt_s:
        Passo de integração [s]; padrão 1 µs [FATO: doc A, Tabela II].
    t_end_s:
        Janela simulada [s]; padrão 45 ms [FATO: doc A, Tabela II].
    grounded_neutral:
        Neutro do motor e referência do *snubber* solidamente aterrados.
        **[HIPÓTESE]** A não declara o aterramento do neutro; a Fig. 1
        mostra o *snubber* ligado "between the bus and the neutral".
    cda_full_steps:
        Passos de CDA por manobra; 2 (e não o padrão 1 do kernel) porque
        a interrupção de corrente indutiva contra capacitância pequena é
        exatamente o caso rígido descrito na limitação
        ``emt_cda_residual_in_stiff_networks``.
    """

    source: SourceParameters = field(default_factory=SourceParameters)
    transformer: TransformerParameters = field(default_factory=TransformerParameters)
    cable_upstream: CableParameters = field(default_factory=CableParameters)
    cable_downstream: CableParameters = field(
        default_factory=lambda: CableParameters(length_m=200.0)
    )
    motor: MotorParameters = field(default_factory=MotorParameters)
    vcb: VCBParameters = field(default_factory=VCBParameters)
    snubber: SnubberParameters = field(default_factory=SnubberParameters)
    rl_variant: str = RL_VARIANT_FIG2
    dt_s: float = DOC_A_TIME_STEP_S
    t_end_s: float = DOC_A_WINDOW_S
    grounded_neutral: bool = True
    cda_full_steps: int = 2

    def __post_init__(self) -> None:
        if str(self.rl_variant) not in RL_VARIANTS:
            raise ValueError(
                f"rl_variant deve ser uma de {RL_VARIANTS}, obtida {self.rl_variant!r}"
            )
        _require_positive(self.dt_s, "dt_s")
        _require_positive(self.t_end_s, "t_end_s")
        if self.t_end_s < self.dt_s:
            raise ValueError(
                f"t_end_s ({self.t_end_s:.6g} s) menor que dt_s ({self.dt_s:.6g} s)"
            )
        if int(self.cda_full_steps) < 1:
            raise ValueError(f"cda_full_steps deve ser >= 1, obtido {self.cda_full_steps!r}")

    # -- variações convenientes --------------------------------------------

    def with_snubber(self, breakover_voltage_V: float, **kwargs) -> "MotorSwitchingCase":
        """Devolve uma cópia com o *snubber* habilitado."""
        return replace(
            self,
            snubber=replace(
                self.snubber,
                enabled=True,
                breakover_voltage_V=float(breakover_voltage_V),
                **kwargs,
            ),
        )

    def without_snubber(self) -> "MotorSwitchingCase":
        """Devolve uma cópia com o *snubber* desabilitado."""
        return replace(self, snubber=replace(self.snubber, enabled=False))

    def with_phase_deg(self, phase_deg: float) -> "MotorSwitchingCase":
        """Devolve uma cópia com outro ponto da onda — passo do Monte Carlo."""
        return replace(self, source=replace(self.source, phase_deg=float(phase_deg)))

    def with_cable_model(self, model: str) -> "MotorSwitchingCase":
        """Devolve uma cópia com OS DOIS cabos no modelo indicado.

        ``model`` deve ser ``"bergeron"`` ou ``"jmarti"``
        (:data:`CABLE_MODELS`). É o único parâmetro necessário para
        trocar de modelo de linha: a interface de componente é a mesma
        nos dois casos.
        """
        m = str(model)
        if m not in CABLE_MODELS:
            raise ValueError(f"model deve ser um de {CABLE_MODELS}, obtido {model!r}")
        return replace(
            self,
            cable_upstream=replace(self.cable_upstream, model=m),
            cable_downstream=replace(self.cable_downstream, model=m),
        )

    # -- montagem -----------------------------------------------------------

    def build(self) -> MotorSwitchingModel:
        """Monta circuito, sondas e controladores.

        Returns
        -------
        MotorSwitchingModel
            Montagem pronta para ``.run()``.
        """
        neutral = "gnd" if self.grounded_neutral else "neutro"
        ckt = Circuit("doc_a_manobra_motor")

        # -- fonte trifásica ------------------------------------------------
        src_nodes = tuple(f"src_{ph}" for ph in PHASES)
        ckt.extend(
            three_phase_voltage_sources(
                "E",
                src_nodes,
                neutral,
                amplitude_V=self.source.phase_voltage_peak_V,
                frequency_Hz=self.source.frequency_Hz,
                phase_deg=self.source.phase_deg,
                sequence=self.source.sequence,
            )
        )

        # -- transformador (impedância de dispersão referida a 4,16 kV) -----
        r_tx, l_tx = self.transformer.series_rl(
            self.source.line_voltage_V, self.source.frequency_Hz
        )
        r_mot, l_mot = self.motor.locked_rotor_branch(self.rl_variant)

        poles: list[VacuumCircuitBreakerModel] = []
        trv_probes: dict = {}
        bus_probes: dict = {}
        motor_probes: dict = {}
        current_probes: dict = {}
        sep_times = self.vcb.times(len(PHASES))
        recovery = self.vcb.recovery

        for ph, t_sep in zip(PHASES, sep_times):
            ckt.add(Resistor(f"tx_r_{ph}", f"src_{ph}", f"tx_{ph}", r_tx))
            ckt.add(Inductor(f"tx_l_{ph}", f"tx_{ph}", f"bus_{ph}", l_tx))
            ckt.add(self.cable_upstream.build(f"cabo_up_{ph}", f"bus_{ph}", f"cb_src_{ph}"))
            switch = ckt.add(
                Switch(f"vcb_{ph}", f"cb_src_{ph}", f"cb_load_{ph}", closed=True)
            )
            ckt.add(
                self.cable_downstream.build(f"cabo_dn_{ph}", f"cb_load_{ph}", f"mot_{ph}")
            )
            ckt.add(Resistor(f"mot_r_{ph}", f"mot_{ph}", f"mot_x_{ph}", r_mot))
            ckt.add(Inductor(f"mot_l_{ph}", f"mot_x_{ph}", neutral, l_mot))
            ckt.add(
                Capacitor(f"mot_c_{ph}", f"mot_{ph}", neutral, self.motor.stray_capacitance_F)
            )
            poles.append(
                VacuumCircuitBreakerModel(
                    switch,
                    separation_time_s=float(t_sep),
                    chopping_current_A=self.vcb.chopping_current_A,
                    chopping_range_A=self.vcb.chopping_range_A,
                    seed=self.vcb.seed,
                    recovery=recovery,
                    didt_capability_A_per_us=self.vcb.didt_capability_A_per_us,
                    didt_convention=self.vcb.didt_convention,
                    max_reignitions=self.vcb.max_reignitions,
                    name=f"vcb_{ph}",
                )
            )

        # -- snubber opcional -----------------------------------------------
        snubbers: tuple[SnubberBranch, ...] = ()
        if self.snubber.enabled:
            snubbers = three_phase_snubber(
                "snub",
                tuple(f"cb_load_{ph}" for ph in PHASES),
                neutral,
                breakover_voltage_V=float(self.snubber.breakover_voltage_V or 0.0),
                resistance_ohm=self.snubber.resistance_ohm,
                holding_current_A=self.snubber.holding_current_A,
                single_shot=self.snubber.single_shot,
            )
            for branch in snubbers:
                ckt.extend(branch.components)

        # -- solver e sondas -------------------------------------------------
        solver = Solver(
            ckt,
            dt=self.dt_s,
            cda_enabled=True,
            cda_full_steps=int(self.cda_full_steps),
        )
        for ph in PHASES:
            trv_probes[ph] = solver.add_probe(
                DifferentialVoltageProbe(f"trv_{ph}", f"cb_src_{ph}", f"cb_load_{ph}")
            )
            bus_probes[ph] = solver.add_probe(NodeVoltageProbe(f"v_cb_load_{ph}", f"cb_load_{ph}"))
            motor_probes[ph] = solver.add_probe(NodeVoltageProbe(f"v_mot_{ph}", f"mot_{ph}"))
            current_probes[ph] = solver.add_probe(
                BranchCurrentProbe(f"i_vcb_{ph}", ckt.get(f"vcb_{ph}"))
            )

        controllers = tuple(poles) + tuple(b.controller for b in snubbers)
        return MotorSwitchingModel(
            case=self,
            circuit=ckt,
            solver=solver,
            poles=tuple(poles),
            snubbers=snubbers,
            controllers=controllers,
            trv_probes=trv_probes,
            bus_probes=bus_probes,
            motor_probes=motor_probes,
            current_probes=current_probes,
        )


# ---------------------------------------------------------------------------
# Auxiliares
# ---------------------------------------------------------------------------


def _require_positive(value: float, label: str) -> float:
    """Valida ``value`` finito e > 0; devolve-o como ``float``."""
    v = float(value)
    if not math.isfinite(v) or v <= 0.0:
        raise ValueError(f"{label} deve ser finito e > 0, obtido {value!r}")
    return v


# ---------------------------------------------------------------------------
# Limitações declaradas do caso
# ---------------------------------------------------------------------------

KNOWN_LIMITATIONS: dict[str, str] = {
    "emt_case_rl_branch_ambiguous": (
        "O Documento A é internamente inconsistente quanto ao ramo R–L do "
        "motor: a Tabela I declara I_p/I_n = 6,5 (1348,9 A) e o quadro da "
        "Fig. 2 declara |Z_eq| = 3,455 Ω, que a 2401,78 V drena 695,2 A = "
        "3,35 I_n. A energia magnética do reservatório difere por 3,77× entre "
        "as duas leituras. Este módulo NÃO resolve a inconsistência: oferece "
        "as duas variantes (rl_variant) e exige que a escolha seja declarada. "
        "Todo resultado de pico de TRV herda esse fator de incerteza."
    ),
    "emt_case_undisclosed_network_data": (
        "A NÃO publica: impedância da fonte a montante, dados elétricos do "
        "transformador Δ–Y, parâmetros distribuídos e comprimento do cabo a "
        "jusante do disjuntor, capacitância parasita do motor, nível de "
        "breakover do DIAC e módulo da tensão de fonte [FATO por omissão]. "
        "Todos esses são padrões DESTE módulo, rotulados [HIPÓTESE] nas "
        "docstrings, e nenhum deles vem do artigo. A reprodução numérica da "
        "Tabela III é, por isso, impossível a partir do artigo isolado."
    ),
    "emt_case_constant_parameter_cables": (
        "Os cabos são, POR PADRÃO, de parâmetros CONSTANTES (Bergeron), "
        "enquanto A usa JMARTI dependente da frequência. Sem efeito pelicular "
        "nem retorno pela terra, a frente chega ao motor praticamente sem "
        "atenuação e o dv/dt reportado é COTA SUPERIOR. Herda a limitação "
        "emt_constant_parameter_line do kernel. Desde a implementação de "
        "app/simulation/emt/jmarti.py o caso aceita "
        "CableParameters(model='jmarti') — ou "
        "MotorSwitchingCase.with_cable_model('jmarti') —, mas as tabelas "
        "Z_c(ω)/A(ω) então geradas vêm do modelo R'L'C' com R' CONSTANTE "
        "[HIPÓTESE], e NÃO de um cálculo de parâmetros de cabo real: a "
        "dependência de frequência representada é a das perdas ôhmicas "
        "puras, menos acentuada que a real. A troca de modelo muda o "
        "resultado, e a diferença medida entre os dois modelos está "
        "registrada em tests/test_emt_jmarti.py."
    ),
    "emt_case_no_phase_coupling": (
        "As três fases são células ELETRICAMENTE INDEPENDENTES, acopladas "
        "apenas pela fonte e pelo neutro comum. Não há acoplamento mútuo "
        "entre condutores do mesmo cabo tripolar nem entre enrolamentos do "
        "motor, de modo que a reignição de um polo não induz tensão nos "
        "outros — mecanismo que, em disjuntor real, é uma das origens da "
        "escalada de tensão entre fases."
    ),
    "emt_case_transformer_leakage_only": (
        "O transformador é a impedância de dispersão série. Não há "
        "capacitância entre enrolamentos (caminho dominante de transferência "
        "de surto de frente rápida), corrente de magnetização, saturação nem "
        "a defasagem de 30° do Δ–Y. A barra de 4,16 kV é, para o transitório, "
        "terminada por uma indutância — o que aproxima o comportamento "
        "correto abaixo de algumas dezenas de kHz e o subestima acima disso."
    ),
    "emt_case_motor_lumped_rl": (
        "O motor é um ramo R–L série concentrado em paralelo com uma "
        "capacitância — a mesma representação de A (Fig. 2). Não há "
        "distribuição da tensão entre espiras, e portanto o V_pk no nó do "
        "motor NÃO é a tensão entre as primeiras espiras, que é a grandeza "
        "que degrada o isolamento entre espiras (Etapa 1 §3.4). A fração da "
        "frente que aparece nas primeiras espiras é entrada externa do "
        "modelo de dano, não saída deste caso."
    ),
    "emt_case_doc_a_rrds_prevents_clearing": (
        "Resultado observado nesta implementação, com os parâmetros "
        "publicados de A (RRDS A = 0,801 kV/ms, B = 1,226 kV/ms², Δt = 1 µs) "
        "e a convenção FÍSICA de di/dt: nenhum polo alcança a primeira "
        "interrupção bem-sucedida. Um passo depois do corte a "
        "suportabilidade vale 0,801 V, a TRV já vale dezenas de volts e o "
        "gap reignita; a sequência se repete a cada zero de corrente de "
        "60 Hz e o pico de TRV registrado fica na casa de 0,1 kV, contra os "
        "41,44 kV da Tabela III [CÁLCULO PRÓPRIO]. Elevar A para 200 kV/ms "
        "— dentro da faixa publicada de 2 a 50 kV/ms apenas por uma ordem de "
        "grandeza acima — produz interrupção limpa e TRV de 6,6 a 7,1 kV, "
        "isto é, cerca de 2 pu, que é o valor clássico. Enquanto os dados de "
        "rede omitidos por A (§emt_case_undisclosed_network_data) não forem "
        "obtidos, NÃO se deve concluir daqui nem que os 41,44 kV estão "
        "errados, nem que este modelo os reproduz: a conclusão defensável é "
        "que a Tabela III NÃO é reprodutível a partir do artigo isolado."
    ),
    "emt_case_no_steady_state_start": (
        "A simulação do caso parte do REPOUSO: o kernel já oferece a partida "
        "fasorial (Solver(init='steady_state')), mas o caso mantém "
        "deliberadamente init='zero', porque a Tabela III do Documento A não "
        "informa o estado de regime da rede a montante "
        "(§emt_case_undisclosed_network_data) e uma semeadura fasorial sobre "
        "dados presumidos daria falsa precisão. Consequência do repouso: "
        "os instantes de separação padrão (14 a 25 ms) dão de 0,8 a "
        "1,5 ciclo de acomodação, o que NÃO é suficiente para extinguir o "
        "transitório de energização do ramo R–L do motor: com L/R = 13,0 ms "
        "na variante da Fig. 2 [CÁLCULO PRÓPRIO], a componente contínua ainda "
        "vale 34 % em t = 14 ms. Use instantes de separação maiores, ou "
        "condição inicial explícita nos indutores, quando o valor absoluto do "
        "pico importar."
    ),
}


__all__ = [
    "PHASES",
    "RL_VARIANT_FIG2",
    "RL_VARIANT_TABLE_I",
    "RL_VARIANTS",
    "DOC_A_FIG2_R_OHM",
    "DOC_A_FIG2_L_H",
    "DOC_A_TABLE_III",
    "SourceParameters",
    "TransformerParameters",
    "CableParameters",
    "MotorParameters",
    "VCBParameters",
    "SnubberParameters",
    "MotorSwitchingCase",
    "MotorSwitchingModel",
    "KNOWN_LIMITATIONS",
]
