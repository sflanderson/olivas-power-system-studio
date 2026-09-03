"""
app.postprocessor.prognosis.stress_profile — vetor de estresse dielétrico
por evento de manobra e extração a partir de forma de onda.

Escopo
======

Converte uma forma de onda de tensão (oscilografia de manobra ou saída
de simulação ATP/EMTP) na sequência de **eventos de estresse** que
alimenta o acumulador de dano de :mod:`damage_models`.

O vetor de estresse por evento é o definido na Etapa 1 do estudo de RUL
de isolamento::

    s_{m,j} = [V_pk, T1, dv/dt, E, n_r, theta]

com ``m`` indexando a manobra e ``j`` a reignição dentro da manobra.

Cobertura normativa
====================

* **IEC 60034-15:2009 §2.4** — tempo de frente do impulso de máquina,
  ``T1 = 1,67 (t_90% - t_30%)``. Esta é a definição adotada aqui.
* **IEC 60034-15:2009 §4.2** — forma de onda de referência 1,2/50 µs
  (isolação principal) e 0,2 ± 0,1 µs (entre espiras, SFI).
* **IEC 60034-15:2009 §A.1** — a norma admite frentes de serviço de até
  0,1 µs; formas de onda amostradas com passo grosseiro **não** resolvem
  essa faixa.
* **IEC 60034-18-41:2014 §3.13** — define ``t_r = t_90% - t_10%``,
  grandeza DISTINTA de ``T1``; não é a usada aqui.

Advertência de método (Etapa 1 §3.3, p. 201-224)
=================================================

A razão ``V_pk / RRRV`` **não é** um tempo de frente: o pico é atingido
após a escalada por reignições sucessivas e a maior RRRV pode pertencer
a outra fase. Por isso ``T1_us`` é medido pela definição normativa e a
razão ``V_pk/dv/dt`` é exposta apenas como :meth:`StressEvent.front_time_from_rrrv_us`,
rotulada como indicativa.

Quando o passo de amostragem é da ordem do tempo de frente (o Documento
A usa passo de integração de 1 µs), a derivada numérica é calculada
sobre 1 a 3 amostras e o dv/dt reportado deve ser lido como **limite
inferior** do dv/dt real (Etapa 1 §3.3, item 3). Esta condição é
detectada e registrada em :attr:`StressProfile.warnings`.

Limitações declaradas
======================

* Sem I/O: a forma de onda é entregue pelo chamador (listas ou
  sequências de ``float``); este módulo não lê PL4/COMTRADE.
* A energia por evento é uma aproximação por impedância de surto
  (``E = ∫ v²/Z dt``) e só é calculada quando ``surge_impedance_ohm``
  é informado; caso contrário vale 0,0 (não medida).
* A temperatura ``theta_C`` do enrolamento no instante do evento **não**
  é extraível da forma de onda de tensão; é entrada do chamador.
* A tensão de entrada é a do ponto de medição do chamador. Se for a TRV
  no disjuntor, ela **não** é a tensão nos terminais do motor
  (Etapa 1 §3.4).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Sequence

# ---------------------------------------------------------------------------
# Constantes físicas / normativas
# ---------------------------------------------------------------------------

#: Zero absoluto em °C — usado apenas para validação física de temperatura.
ABSOLUTE_ZERO_C: float = -273.15

#: Fator normativo de tempo de frente de máquinas girantes:
#: T1 = 1,67 (t_90% - t_30%) [NORMA: IEC 60034-15:2009, §2.4].
IEC_60034_15_T1_FACTOR: float = 1.67

#: Níveis relativos usados na definição de T1 [NORMA: IEC 60034-15:2009, §2.4].
IEC_60034_15_LOWER_LEVEL: float = 0.30
IEC_60034_15_UPPER_LEVEL: float = 0.90

#: Passo de amostragem a partir do qual se considera a frente NÃO resolvida.
#: Origem: passo de integração de 1 µs do Documento A (Tabela II) e a
#: frente mínima de serviço de 0,1 µs admitida pela IEC 60034-15:2009 §A.1
#: [Etapa 1 §3.3]. NÃO é limite normativo — é regra de auditoria do módulo.
DEFAULT_COARSE_STEP_S: float = 1.0e-6

#: Número mínimo de amostras exigido no intervalo (t30, t90) para que a
#: derivada numérica seja considerada resolvida. Valor de engenharia,
#: NÃO CALIBRADO e NÃO normativo — configurável pelo chamador.
DEFAULT_MIN_SAMPLES_PER_FRONT: int = 5

#: Janela para agrupar excursões consecutivas na MESMA manobra (reignições).
#: Ordem de grandeza do intervalo entre reignições sucessivas de um VCB.
#: NÃO CALIBRADO — configurável pelo chamador.
DEFAULT_GROUP_WINDOW_S: float = 1.0e-3

#: Constante de largura de banda equivalente de um degrau: f ≈ 0,35 / t_r.
#: Regra clássica de instrumentação, usada aqui apenas para o aviso de
#: Nyquist. NÃO normativa.
RISE_TIME_BANDWIDTH_CONSTANT: float = 0.35


# ---------------------------------------------------------------------------
# Evento de estresse
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class StressEvent:
    """Uma excursão de tensão (uma reignição) com seu vetor de estresse.

    Corresponde a ``s_{m,j} = [V_pk, T1, dv/dt, E, n_r, theta]``
    (Etapa 1 §5.4, D7; Etapa 2 §5.2, eq. 5.2).

    Parameters
    ----------
    V_pk_kV:
        Pico de tensão da excursão, **com sinal** [kV]. O sinal é
        preservado porque a polaridade do impulso é informação de
        diagnóstico; os modelos de dano usam ``abs_V_pk_kV``.
    T1_us:
        Tempo de frente ``T1 = 1,67 (t_90% - t_30%)`` [µs]
        [NORMA: IEC 60034-15:2009, §2.4]. Deve ser > 0.
    dvdt_kV_per_us:
        Máxima derivada de tensão na frente da excursão [kV/µs]. Com
        passo de amostragem grosseiro é **limite inferior** do valor real
        (Etapa 1 §3.3, item 3).
    energy_J:
        Energia associada à excursão [J], por aproximação de impedância
        de surto. 0,0 significa "não medida".
    n_reignitions:
        Número de excursões da manobra à qual este evento pertence
        (``n_{r,m}`` em D7). Vale 1 para evento isolado.
    theta_C:
        Temperatura do enrolamento no instante do evento [°C]
        (``theta_j`` em D7). Não é extraível da forma de onda de tensão.
    timestamp_s:
        Instante do pico da excursão [s], na base de tempo do chamador.
    source:
        Rótulo de origem (ex.: ``"doc A Tabela III fase B"``,
        ``"PL4 barra MOTOR-1"``).
    """

    V_pk_kV: float
    T1_us: float
    dvdt_kV_per_us: float
    energy_J: float = 0.0
    n_reignitions: int = 1
    # Default NÃO CALIBRADO: 40 °C é a temperatura de referência de ensaio
    # de resistência de isolamento [NORMA: ABNT NBR 17094-3:2018, 6.8.2],
    # usada aqui apenas como valor neutro quando o chamador não informa θ.
    theta_C: float = 40.0
    timestamp_s: float = 0.0
    source: str = ""

    def __post_init__(self) -> None:
        if not math.isfinite(self.V_pk_kV):
            raise ValueError(f"V_pk_kV deve ser finito, obtido {self.V_pk_kV}")
        if self.V_pk_kV == 0.0:
            raise ValueError("V_pk_kV deve ser != 0 (excursão de amplitude nula)")
        if not math.isfinite(self.T1_us) or self.T1_us <= 0.0:
            raise ValueError(
                f"T1_us deve ser > 0 [µs] (IEC 60034-15:2009 §2.4), "
                f"obtido {self.T1_us}"
            )
        if not math.isfinite(self.dvdt_kV_per_us) or self.dvdt_kV_per_us < 0.0:
            raise ValueError(
                f"dvdt_kV_per_us deve ser >= 0 [kV/µs], obtido {self.dvdt_kV_per_us}"
            )
        if not math.isfinite(self.energy_J) or self.energy_J < 0.0:
            raise ValueError(f"energy_J deve ser >= 0 [J], obtido {self.energy_J}")
        if int(self.n_reignitions) != self.n_reignitions:
            raise ValueError(
                f"n_reignitions deve ser inteiro, obtido {self.n_reignitions!r}"
            )
        if self.n_reignitions < 1:
            raise ValueError(
                f"n_reignitions deve ser >= 1, obtido {self.n_reignitions}"
            )
        if not math.isfinite(self.theta_C) or self.theta_C <= ABSOLUTE_ZERO_C:
            raise ValueError(
                f"theta_C deve ser > {ABSOLUTE_ZERO_C} °C (zero absoluto), "
                f"obtido {self.theta_C}"
            )
        if not math.isfinite(self.timestamp_s):
            raise ValueError(f"timestamp_s deve ser finito, obtido {self.timestamp_s}")

    # -- grandezas derivadas ------------------------------------------------

    @property
    def abs_V_pk_kV(self) -> float:
        """Módulo do pico [kV] — grandeza usada pelos modelos de dano."""
        return abs(self.V_pk_kV)

    @property
    def theta_K(self) -> float:
        """Temperatura do evento em kelvin."""
        return self.theta_C - ABSOLUTE_ZERO_C

    @property
    def front_time_from_rrrv_us(self) -> float:
        """``V_pk / dv/dt`` [µs] — **apenas indicativo**.

        Etapa 1 §3.3, p. 201-224: esta razão NÃO é um tempo de frente,
        porque o pico é atingido após a escalada por reignições e a maior
        RRRV pode pertencer a outra fase. Use :attr:`T1_us` para qualquer
        comparação com envelope normativo.
        """
        if self.dvdt_kV_per_us <= 0.0:
            return math.inf
        return self.abs_V_pk_kV / self.dvdt_kV_per_us

    def in_per_unit(self, base_kV: float) -> float:
        """Pico em pu sobre a base fase-terra informada [kV]."""
        if base_kV <= 0.0:
            raise ValueError(f"base_kV deve ser > 0, obtido {base_kV}")
        return self.abs_V_pk_kV / base_kV


# ---------------------------------------------------------------------------
# Perfil de estresse
# ---------------------------------------------------------------------------


@dataclass
class StressProfile:
    """Coleção de :class:`StressEvent` com estatísticas de auditoria.

    Attributes
    ----------
    events:
        Eventos em ordem cronológica (não reordenados por este módulo).
    sampling_step_s:
        Passo mediano de amostragem da forma de onda de origem [s], ou
        ``None`` quando o perfil foi montado manualmente.
    warnings:
        Avisos de qualidade de amostragem e de extração (ver
        :func:`extract_stress_events`).
    label:
        Rótulo do perfil (motor, barramento, cenário).
    """

    events: list[StressEvent] = field(default_factory=list)
    sampling_step_s: float | None = None
    warnings: list[str] = field(default_factory=list)
    label: str = ""

    def __post_init__(self) -> None:
        for ev in self.events:
            if not isinstance(ev, StressEvent):
                raise ValueError(
                    f"events deve conter apenas StressEvent, obtido {type(ev).__name__}"
                )
        if self.sampling_step_s is not None:
            if not math.isfinite(self.sampling_step_s) or self.sampling_step_s <= 0.0:
                raise ValueError(
                    f"sampling_step_s deve ser > 0 [s] ou None, "
                    f"obtido {self.sampling_step_s}"
                )

    # -- estatísticas -------------------------------------------------------

    def __len__(self) -> int:
        return len(self.events)

    @property
    def n_events(self) -> int:
        """Número de excursões (reignições) no perfil."""
        return len(self.events)

    @property
    def n_operations(self) -> int:
        """Número de manobras distintas identificadas no perfil.

        Uma manobra é um grupo de excursões com o mesmo
        ``n_reignitions``/instante de agrupamento; aqui é contado pelo
        número de grupos criados na extração (ver
        :func:`extract_stress_events`), reconstruído como
        ``ceil(n_events / n_reignitions)`` por grupo homogêneo. Para
        perfis montados manualmente com ``n_reignitions=1`` retorna
        ``n_events``.
        """
        if not self.events:
            return 0
        # Reconstrução conservadora: soma de 1/n_r por evento.
        return max(1, round(sum(1.0 / ev.n_reignitions for ev in self.events)))

    @property
    def peak_max_kV(self) -> float:
        """Maior pico em módulo [kV]. 0,0 se o perfil estiver vazio."""
        if not self.events:
            return 0.0
        return max(ev.abs_V_pk_kV for ev in self.events)

    @property
    def peak_mean_kV(self) -> float:
        """Média dos picos em módulo [kV]."""
        if not self.events:
            return 0.0
        return sum(ev.abs_V_pk_kV for ev in self.events) / len(self.events)

    @property
    def dvdt_max_kV_per_us(self) -> float:
        """Maior dv/dt do perfil [kV/µs]."""
        if not self.events:
            return 0.0
        return max(ev.dvdt_kV_per_us for ev in self.events)

    @property
    def T1_min_us(self) -> float:
        """Menor tempo de frente T1 do perfil [µs] (frente mais severa)."""
        if not self.events:
            return math.inf
        return min(ev.T1_us for ev in self.events)

    @property
    def energy_total_J(self) -> float:
        """Soma das energias por evento [J]."""
        return sum(ev.energy_J for ev in self.events)

    @property
    def theta_max_C(self) -> float:
        """Maior temperatura de evento [°C]."""
        if not self.events:
            return ABSOLUTE_ZERO_C
        return max(ev.theta_C for ev in self.events)

    def events_above(self, threshold_kV: float) -> list[StressEvent]:
        """Eventos cujo pico em módulo excede ``threshold_kV``."""
        if threshold_kV < 0.0:
            raise ValueError(
                f"threshold_kV deve ser >= 0, obtido {threshold_kV}"
            )
        return [ev for ev in self.events if ev.abs_V_pk_kV > threshold_kV]

    def equivalent_events(self, n_exponent: float) -> float:
        """``n_eq = Σ_j (V_j / V_max)^n`` — eventos equivalentes ao pico.

        Etapa 1 §5.5, Passo 1: sob lei de potência inversa com expoente
        ``n``, o dano da manobra é dominado pela maior reignição; ``n_eq``
        quantifica quantas excursões "valem" a maior. Retorna 0,0 para
        perfil vazio.
        """
        if n_exponent < 0.0:
            raise ValueError(
                f"n_exponent deve ser >= 0, obtido {n_exponent}"
            )
        if not self.events:
            return 0.0
        v_max = self.peak_max_kV
        if v_max <= 0.0:
            return 0.0
        return sum((ev.abs_V_pk_kV / v_max) ** n_exponent for ev in self.events)

    def summary(self) -> str:
        """Resumo textual determinístico para laudo/console."""
        lines = [
            f"Perfil de estresse dielétrico — {self.label or '(sem rótulo)'}",
            f"  Excursões (reignições) ............ {self.n_events}",
            f"  Pico máximo ...................... {self.peak_max_kV:.3f} kV",
            f"  Pico médio ....................... {self.peak_mean_kV:.3f} kV",
            f"  dv/dt máximo ..................... {self.dvdt_max_kV_per_us:.3f} kV/µs",
            f"  T1 mínimo (IEC 60034-15 §2.4) .... {self.T1_min_us:.4f} µs",
            f"  Energia total .................... {self.energy_total_J:.4g} J",
        ]
        if self.sampling_step_s is not None:
            lines.append(
                f"  Passo de amostragem .............. "
                f"{self.sampling_step_s * 1.0e6:.4g} µs"
            )
        if self.warnings:
            lines.append("  Avisos de qualidade de amostragem:")
            lines.extend(f"    • {w}" for w in self.warnings)
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Extração a partir de forma de onda
# ---------------------------------------------------------------------------


def _median(values: Sequence[float]) -> float:
    ordered = sorted(values)
    k = len(ordered)
    mid = k // 2
    if k % 2 == 1:
        return ordered[mid]
    return 0.5 * (ordered[mid - 1] + ordered[mid])


def _interp_crossing(
    t_lo: float, v_lo: float, t_hi: float, v_hi: float, level: float
) -> float:
    """Instante em que o segmento (t_lo, v_lo)-(t_hi, v_hi) cruza ``level``."""
    dv = v_hi - v_lo
    if dv == 0.0:
        return t_hi
    frac = (level - v_lo) / dv
    frac = min(1.0, max(0.0, frac))
    return t_lo + frac * (t_hi - t_lo)


def extract_stress_events(
    time_s: Sequence[float],
    voltage_kV: Sequence[float],
    *,
    threshold_kV: float,
    surge_impedance_ohm: float | None = None,
    theta_C: float = 40.0,
    group_window_s: float = DEFAULT_GROUP_WINDOW_S,
    min_samples_per_front: int = DEFAULT_MIN_SAMPLES_PER_FRONT,
    coarse_step_s: float = DEFAULT_COARSE_STEP_S,
    source: str = "",
    label: str = "",
) -> StressProfile:
    """Extrai o perfil de estresse de uma forma de onda de tensão.

    Algoritmo (determinístico, sem estado global):

    1. Detecta **excursões**: sequências contíguas de amostras com
       ``|v| >= threshold_kV``.
    2. Para cada excursão, localiza o pico em módulo e mede na frente
       ascendente os instantes ``t_30%`` e ``t_90%`` do pico por
       interpolação linear entre amostras.
    3. ``T1 = 1,67 (t_90% - t_30%)`` [NORMA: IEC 60034-15:2009, §2.4].
    4. ``dv/dt`` = máxima derivada numérica de primeira ordem na frente
       (de ``t_30%`` ao pico), em kV/µs.
    5. Energia (opcional) por impedância de surto: ``E = ∫ v²/Z dt``,
       regra do trapézio, com ``v`` convertido para volts.
    6. Agrupa excursões separadas por menos de ``group_window_s`` na
       mesma manobra; ``n_reignitions`` de cada evento recebe o tamanho
       do grupo (``n_{r,m}`` de D7).

    Parameters
    ----------
    time_s, voltage_kV:
        Sequências de mesmo comprimento (>= 3), com ``time_s``
        estritamente crescente [s] e tensão em [kV].
    threshold_kV:
        Limiar de detecção de excursão [kV], > 0. É um limiar de
        DETECÇÃO, não o limiar de dano ``V_th`` de D2/D7.
    surge_impedance_ohm:
        Impedância de surto do cabo [Ω] para a estimativa de energia.
        ``None`` (padrão) ⇒ ``energy_J = 0,0`` (não medida). Faixa
        reportada na Etapa 1 §2.3 para cabos de MT: ≈ 30 a 80 Ω.
    theta_C:
        Temperatura do enrolamento atribuída a todos os eventos [°C].
        Não é extraível da tensão (Etapa 2 §3.3).
    group_window_s:
        Janela de agrupamento de reignições na mesma manobra [s].
    min_samples_per_front:
        Mínimo de amostras exigido no intervalo (t30, t90) para não
        emitir aviso de passo grosseiro.
    coarse_step_s:
        Passo de amostragem a partir do qual se emite o aviso do
        Documento A / Etapa 1 §3.3 (padrão 1 µs).
    source, label:
        Rótulos de rastreabilidade.

    Returns
    -------
    StressProfile
        Perfil com eventos, passo de amostragem e avisos.

    Raises
    ------
    ValueError
        Comprimentos diferentes, menos de 3 amostras, base de tempo não
        estritamente crescente, ``threshold_kV <= 0``,
        ``surge_impedance_ohm <= 0``, ``group_window_s <= 0``,
        ``min_samples_per_front < 1`` ou valores não finitos.
    """
    n = len(time_s)
    if n != len(voltage_kV):
        raise ValueError(
            f"time_s e voltage_kV devem ter o mesmo comprimento, "
            f"obtidos {n} e {len(voltage_kV)}"
        )
    if n < 3:
        raise ValueError(f"são necessárias pelo menos 3 amostras, obtidas {n}")
    if threshold_kV <= 0.0 or not math.isfinite(threshold_kV):
        raise ValueError(f"threshold_kV deve ser > 0 [kV], obtido {threshold_kV}")
    if surge_impedance_ohm is not None and (
        not math.isfinite(surge_impedance_ohm) or surge_impedance_ohm <= 0.0
    ):
        raise ValueError(
            f"surge_impedance_ohm deve ser > 0 [Ω] ou None, "
            f"obtido {surge_impedance_ohm}"
        )
    if group_window_s <= 0.0 or not math.isfinite(group_window_s):
        raise ValueError(
            f"group_window_s deve ser > 0 [s], obtido {group_window_s}"
        )
    if min_samples_per_front < 1:
        raise ValueError(
            f"min_samples_per_front deve ser >= 1, obtido {min_samples_per_front}"
        )
    if coarse_step_s <= 0.0 or not math.isfinite(coarse_step_s):
        raise ValueError(
            f"coarse_step_s deve ser > 0 [s], obtido {coarse_step_s}"
        )

    t = [float(x) for x in time_s]
    v = [float(x) for x in voltage_kV]
    for idx in range(n):
        if not math.isfinite(t[idx]) or not math.isfinite(v[idx]):
            raise ValueError(
                f"amostra não finita no índice {idx}: t={t[idx]}, v={v[idx]}"
            )
    steps = [t[i + 1] - t[i] for i in range(n - 1)]
    if min(steps) <= 0.0:
        raise ValueError("time_s deve ser estritamente crescente")

    dt = _median(steps)
    av = [abs(x) for x in v]

    warnings: list[str] = []
    if dt >= coarse_step_s:
        warnings.append(
            f"Passo de amostragem Δt = {dt * 1.0e6:.4g} µs ≥ "
            f"{coarse_step_s * 1.0e6:.4g} µs: frentes sub-microssegundo não são "
            f"resolvidas; os valores de dv/dt são LIMITES INFERIORES do real "
            f"[Etapa 1 §3.3, item 3; IEC 60034-15:2009 §A.1 admite frentes de "
            f"até 0,1 µs]."
        )

    # -- 1. excursões -------------------------------------------------------
    runs: list[tuple[int, int]] = []
    i = 0
    while i < n:
        if av[i] >= threshold_kV:
            j = i
            while j + 1 < n and av[j + 1] >= threshold_kV:
                j += 1
            runs.append((i, j))
            i = j + 1
        else:
            i += 1

    raw: list[dict[str, float]] = []
    n_undersampled = 0
    n_nyquist = 0
    prev_end = -1
    for (i0, i1) in runs:
        peak_idx = i0
        for k in range(i0, i1 + 1):
            if av[k] > av[peak_idx]:
                peak_idx = k
        v_pk = v[peak_idx]
        a_pk = av[peak_idx]
        lower = IEC_60034_15_LOWER_LEVEL * a_pk
        upper = IEC_60034_15_UPPER_LEVEL * a_pk

        # -- 2. frente ascendente (busca retroativa a partir do pico) -------
        floor_idx = prev_end + 1
        k30 = None
        k90 = None
        for k in range(peak_idx, floor_idx, -1):
            if k90 is None and av[k - 1] <= upper <= av[k]:
                k90 = k - 1
            if av[k - 1] <= lower <= av[k]:
                k30 = k - 1
                break
        if k30 is not None:
            t30 = _interp_crossing(t[k30], av[k30], t[k30 + 1], av[k30 + 1], lower)
        else:
            t30 = t[max(floor_idx, i0)]
        if k90 is not None:
            t90 = _interp_crossing(t[k90], av[k90], t[k90 + 1], av[k90 + 1], upper)
        else:
            t90 = t[peak_idx]

        rise = t90 - t30
        if rise <= 0.0:
            # Frente não observável na janela fornecida: adota-se um passo
            # de amostragem como cota inferior, com aviso.
            rise = dt
            n_undersampled += 1
        elif rise < min_samples_per_front * dt:
            n_undersampled += 1

        t1_us = IEC_60034_15_T1_FACTOR * rise * 1.0e6

        # Aviso de Nyquist: banda equivalente do degrau f ≈ 0,35 / t_r,
        # com t_r (10-90 %) ≈ (4/3)(t90 - t30).
        t_r = (4.0 / 3.0) * rise
        f_eq = RISE_TIME_BANDWIDTH_CONSTANT / t_r if t_r > 0.0 else math.inf
        if (1.0 / dt) < 2.0 * f_eq:
            n_nyquist += 1

        # -- 4. dv/dt máximo na frente --------------------------------------
        start_slope = k30 if k30 is not None else max(floor_idx, i0)
        start_slope = min(start_slope, max(peak_idx - 1, 0))
        dvdt = 0.0
        for k in range(start_slope, peak_idx):
            slope = abs(v[k + 1] - v[k]) / (t[k + 1] - t[k]) / 1.0e6
            if slope > dvdt:
                dvdt = slope
        if dvdt == 0.0 and peak_idx > 0:
            dvdt = (
                abs(v[peak_idx] - v[peak_idx - 1])
                / (t[peak_idx] - t[peak_idx - 1])
                / 1.0e6
            )

        # -- 5. energia por impedância de surto -----------------------------
        energy = 0.0
        if surge_impedance_ohm is not None:
            for k in range(i0, i1):
                p_lo = (v[k] * 1.0e3) ** 2 / surge_impedance_ohm
                p_hi = (v[k + 1] * 1.0e3) ** 2 / surge_impedance_ohm
                energy += 0.5 * (p_lo + p_hi) * (t[k + 1] - t[k])

        raw.append(
            {
                "V_pk_kV": v_pk,
                "T1_us": t1_us,
                "dvdt": dvdt,
                "energy": energy,
                "t_peak": t[peak_idx],
            }
        )
        prev_end = i1

    if n_undersampled:
        warnings.append(
            f"{n_undersampled} excursão(ões) com (t90 − t30) < "
            f"{min_samples_per_front}·Δt: T1 e dv/dt derivados de poucas "
            f"amostras — derivada numérica sobre 1 a 3 pontos [Etapa 1 §3.3]."
        )
    if n_nyquist:
        warnings.append(
            f"{n_nyquist} excursão(ões) violam o critério de Nyquist para a "
            f"banda equivalente da frente (f ≈ 0,35/t_r): a taxa de amostragem "
            f"1/Δt = {1.0 / dt:.4g} Sa/s é inferior a 2·f_eq. O espectro da "
            f"frente NÃO está representado."
        )

    # -- 6. agrupamento em manobras -----------------------------------------
    groups: list[list[int]] = []
    for idx, item in enumerate(raw):
        if groups and (item["t_peak"] - raw[groups[-1][-1]]["t_peak"]) <= group_window_s:
            groups[-1].append(idx)
        else:
            groups.append([idx])

    events: list[StressEvent] = []
    for grp in groups:
        n_r = len(grp)
        for idx in grp:
            item = raw[idx]
            events.append(
                StressEvent(
                    V_pk_kV=item["V_pk_kV"],
                    T1_us=item["T1_us"],
                    dvdt_kV_per_us=item["dvdt"],
                    energy_J=item["energy"],
                    n_reignitions=n_r,
                    theta_C=theta_C,
                    timestamp_s=item["t_peak"],
                    source=source,
                )
            )

    return StressProfile(
        events=events,
        sampling_step_s=dt,
        warnings=warnings,
        label=label,
    )
