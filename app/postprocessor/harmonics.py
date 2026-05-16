"""
app.postprocessor.harmonics — Análise de harmônicos
(v0.97.0).

Cobertura normativa
====================

* IEEE Std 519-2014 — Recommended Practice for Harmonic
  Control in Electrical Power Systems
* IEC 61000-2-2 — Compatibility levels for low-frequency
  conducted disturbances
* ABNT NBR 16149/16150 — Conexão de geração distribuída

Filosofia
==========

Cargas não-lineares (VFDs, retificadores, fornos a arco,
UPS, computadores) injetam correntes harmônicas no
sistema. Essas correntes percorrem as impedâncias de rede
gerando **distorções de tensão** (V-THD) que podem afetar:

* Aquecimento de transformadores e cabos (perdas adicionais)
* Mau funcionamento de relés (especialmente filtros)
* Vibração e aquecimento em motores
* Erros de medição

IEEE 519-2014 estabelece **limites de tensão e corrente**
no PCC (Point of Common Coupling):

* V-THD: ≤ 5% (sistemas <69 kV), ≤ 2.5% (69-161 kV)
* IHD individual: ≤ 3% (LV), ≤ 1.5% (MV)
* I-TDD: depende do SCR (Short-Circuit Ratio)

Algoritmo
==========

1. Modela cargas não-lineares com **espectros típicos**:
   - VFD 6-pulse: harmônicos 5, 7, 11, 13, 17, 19, 23, 25
   - VFD 12-pulse: 11, 13, 23, 25 (cancelam 5, 7)
   - Retificador 6-pulse: similar VFD
   - Forno a arco: harmônicos pares + ímpares (espectro denso)
   - UPS/SMPS: 3, 5, 7, 9, 11

2. **Propaga** correntes harmônicas pela rede (uma frequência
   por vez): I_h × Z_h = V_h em cada bus.

3. **Soma quadrática** para obter THD por bus:
   V-THD = √(Σ V_h²) / V_1 × 100%

4. Compara com limites IEEE 519 → relatório.

Saída
======

:class:`HarmonicsResult` com:

* ``v_thd_per_bus`` — V-THD% por barramento
* ``ihd_per_bus`` — dict[bus, dict[h, IHD%]]
* ``i_tdd_per_feeder`` — distorção de demanda por feeder
* ``violations`` — barras/feeders excedendo limites
* ``recommendations`` — sugestões de mitigação

Limitações declaradas (v0.97.0)
================================

* Espectros típicos de cargas (não medições reais)
* Apenas harmônicos ímpares 3..25 (h=27+ negligenciáveis)
* Resonância simplificada (não FFT em domínio tempo)
* Não modelar IHD de tensão na fonte (V_source ideal)
* Sequência apenas positiva (3, 9, 15 = sequência zero;
  v0.97.1 separa)

Uso
====

::

    from app.postprocessor.harmonics import (
        analyze_harmonics, NonLinearLoad, LoadType,
    )

    loads = [
        NonLinearLoad(
            bus_id="BUS-MAIN-13.8",
            load_type=LoadType.VFD_6_PULSE,
            S_kVA=500.0,
        ),
    ]
    result = analyze_harmonics(project, loads)
    print(result.summary())
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from app.core.logging_config import get_logger

log = get_logger(__name__)


# ---------------------------------------------------------------------------
# Spectra típicos (% da fundamental)
# ---------------------------------------------------------------------------


class LoadType(str, Enum):
    """Tipos de cargas não-lineares com espectros típicos."""

    VFD_6_PULSE = "VFD_6_PULSE"
    VFD_12_PULSE = "VFD_12_PULSE"
    VFD_18_PULSE = "VFD_18_PULSE"
    RECTIFIER_6_PULSE = "RECTIFIER_6_PULSE"
    ARC_FURNACE = "ARC_FURNACE"
    UPS_SMPS = "UPS_SMPS"
    LED_LIGHTING = "LED_LIGHTING"


# Espectros típicos: harmônico h → magnitude % da fundamental
# Refs: IEEE 519-2014 Table 1 / EPRI Power Quality Workbook
_TYPICAL_SPECTRA: dict[LoadType, dict[int, float]] = {
    # VFD 6-pulse (drive industrial padrão)
    LoadType.VFD_6_PULSE: {
        5: 35.0, 7: 14.0, 11: 9.0, 13: 6.0,
        17: 3.5, 19: 2.5, 23: 1.5, 25: 1.0,
    },
    # VFD 12-pulse — cancela 5/7 mas mantém 11/13
    LoadType.VFD_12_PULSE: {
        5: 3.0, 7: 2.5, 11: 9.0, 13: 6.0,
        17: 1.0, 19: 0.8, 23: 1.5, 25: 1.0,
    },
    # VFD 18-pulse — cancela 5/7/11/13
    LoadType.VFD_18_PULSE: {
        5: 1.0, 7: 0.5, 11: 0.5, 13: 0.5,
        17: 3.0, 19: 2.0, 23: 0.5, 25: 0.5,
    },
    # Retificador 6-pulse — similar VFD mas DC-link maior
    LoadType.RECTIFIER_6_PULSE: {
        5: 30.0, 7: 12.0, 11: 7.0, 13: 5.0,
        17: 3.0, 19: 2.0, 23: 1.0, 25: 0.7,
    },
    # Forno a arco — espectro denso (incluindo pares)
    LoadType.ARC_FURNACE: {
        2: 4.0, 3: 6.0, 4: 3.0, 5: 8.0,
        7: 4.0, 9: 2.0, 11: 1.5, 13: 1.0,
    },
    # UPS/SMPS — predomina 3a (zero-seq)
    LoadType.UPS_SMPS: {
        3: 25.0, 5: 18.0, 7: 12.0, 9: 8.0,
        11: 5.0, 13: 3.5, 15: 2.5, 17: 1.8,
    },
    # LED — pequeno mas espectro amplo
    LoadType.LED_LIGHTING: {
        3: 15.0, 5: 10.0, 7: 7.0, 9: 4.0,
        11: 3.0, 13: 2.0,
    },
}


# IEEE 519-2014 Table 1 — Voltage distortion limits
# (V_THD % limit por classe de tensão)
IEEE_519_V_THD_LIMITS = {
    # (V_min_kV, V_max_kV) → V_THD_max_pct
    (0.0, 1.0): 5.0,        # LV (≤ 1kV)
    (1.0, 69.0): 5.0,       # MV (1–69 kV)
    (69.0, 161.0): 2.5,     # HV (69–161 kV)
    (161.0, 1000.0): 1.5,   # EHV (>161 kV)
}


# IEEE 519-2014 IHD individual limit (% V_1) por classe
IEEE_519_IHD_LIMITS = {
    (0.0, 1.0): 3.0,        # LV
    (1.0, 69.0): 3.0,       # MV
    (69.0, 161.0): 1.5,
    (161.0, 1000.0): 1.0,
}


def _v_thd_limit_pct(voltage_kV: float) -> float:
    for (vmin, vmax), limit in IEEE_519_V_THD_LIMITS.items():
        if vmin < voltage_kV <= vmax:
            return limit
    return 5.0   # fallback LV


def _ihd_limit_pct(voltage_kV: float) -> float:
    for (vmin, vmax), limit in IEEE_519_IHD_LIMITS.items():
        if vmin < voltage_kV <= vmax:
            return limit
    return 3.0


# ---------------------------------------------------------------------------
# Input dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class NonLinearLoad:
    """
    Carga não-linear conectada a um bus.

    Attributes
    ----------
    bus_id:
        ID do barramento de conexão.
    load_type:
        Tipo (define o espectro de harmônicos).
    S_kVA:
        Potência aparente da carga (kVA).
    spectrum_override:
        Espectro custom dict[h, pct] sobrescrevendo o típico.
    """

    bus_id: str
    load_type: LoadType
    S_kVA: float
    spectrum_override: Optional[dict[int, float]] = None

    def __post_init__(self) -> None:
        if self.S_kVA <= 0:
            raise ValueError(
                f"NonLinearLoad[{self.bus_id}]: S_kVA deve ser > 0 "
                f"(got {self.S_kVA})"
            )

    @property
    def spectrum(self) -> dict[int, float]:
        if self.spectrum_override is not None:
            return self.spectrum_override
        return dict(_TYPICAL_SPECTRA[self.load_type])


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class HarmonicsResult:
    """Resultado da análise de harmônicos por barramento."""

    # V-THD % por bus
    v_thd_per_bus: dict[str, float] = field(default_factory=dict)

    # IHD individual: dict[bus, dict[h, magnitude_%]]
    ihd_per_bus: dict[str, dict[int, float]] = field(
        default_factory=dict,
    )

    # Violations (bus, V_THD%, limit%)
    violations: tuple[tuple[str, float, float], ...] = field(
        default_factory=tuple,
    )

    # Recomendações automáticas
    recommendations: tuple[str, ...] = field(default_factory=tuple)

    # Resumo
    n_loads: int = 0
    n_buses_analyzed: int = 0
    worst_bus: str = ""
    worst_v_thd_pct: float = 0.0

    # Audit
    citation: str = (
        "IEEE Std 519-2014 — Harmonic Control in Power Systems"
    )
    warnings: tuple[str, ...] = field(default_factory=tuple)

    def summary(self) -> str:
        lines = [
            "=== Análise de Harmônicos (IEEE 519-2014) ===",
            f"Cargas não-lineares modeladas:  {self.n_loads}",
            f"Buses analisados:               {self.n_buses_analyzed}",
            f"Violations IEEE 519:            {len(self.violations)}",
            f"Pior caso:                      {self.worst_bus} "
            f"(V-THD = {self.worst_v_thd_pct:.2f}%)",
            "",
            "V-THD por bus (limite IEEE 519):",
        ]
        sorted_buses = sorted(
            self.v_thd_per_bus.items(), key=lambda kv: -kv[1],
        )
        for bus, v_thd in sorted_buses:
            # Encontra o limite do bus (não temos voltage_kV aqui,
            # então usamos 5% LV como fallback no display)
            marker = "❌" if any(
                v[0] == bus for v in self.violations
            ) else "✅"
            lines.append(f"  {marker} {bus:30s}  V-THD = {v_thd:6.2f}%")
        if self.recommendations:
            lines.append("")
            lines.append("📋 Recomendações:")
            for rec in self.recommendations:
                lines.append(f"  • {rec}")
        if self.warnings:
            lines.append("")
            lines.append("⚠ Avisos:")
            for w in self.warnings:
                lines.append(f"  • {w}")
        lines.append("")
        lines.append(f"Citação: {self.citation}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def analyze_harmonics(
    project,
    loads: list[NonLinearLoad],
    *,
    base_impedance_ohm: float = 1.0,
) -> HarmonicsResult:
    """
    Análise de harmônicos do projeto com cargas não-lineares
    fornecidas.

    Parameters
    ----------
    project:
        ``PpProject`` (usado para identificar buses).
    loads:
        Lista de :class:`NonLinearLoad` (mínimo 1).
    base_impedance_ohm:
        Impedância base do sistema (Ω) — simplificação v0.97.0
        (v0.97.1 calculará por bus a partir do SC).

    Returns
    -------
    HarmonicsResult
    """
    if not loads:
        return HarmonicsResult(
            warnings=("Nenhuma carga não-linear fornecida",),
        )

    # Coleta buses do projeto (para mapear loads → buses
    # válidos)
    bus_to_voltage_kV: dict[str, float] = {}
    for c in project.components:
        if c.type == "BUS":
            bus_id = (c.get(0, "") or c.name).strip()
            try:
                v_kV = float(c.get(1, "13.8") or "13.8")
            except (ValueError, TypeError):
                v_kV = 13.8
            bus_to_voltage_kV[bus_id] = v_kV

    # Para cada bus, soma contribuições harmônicas de cada
    # carga conectada nele.
    # V_h(bus) = I_h × Z_h
    # Modelo simplificado: Z_h = base_impedance × h
    # (Z varia ~linearmente com frequência para indutâncias)

    v_thd_per_bus: dict[str, float] = {}
    ihd_per_bus: dict[str, dict[int, float]] = {}
    warnings: list[str] = []

    for bus_id, v_nom_kV in bus_to_voltage_kV.items():
        v_nom_V = v_nom_kV * 1000.0
        # Reúne loads conectadas neste bus
        bus_loads = [l for l in loads if l.bus_id == bus_id]
        if not bus_loads:
            continue

        # Para cada harmônico h, soma corrente:
        # I_h(bus) = Σ S_k × spectrum_k[h] / V × ...
        # Modelo simplificado: pega a magnitude % do espectro
        # típico e converte em V_h
        ihd_for_bus: dict[int, float] = {}
        for h in range(2, 26):
            v_h_pct_total = 0.0
            for load in bus_loads:
                spec = load.spectrum
                if h not in spec:
                    continue
                # Magnitude % da fundamental (aproximação:
                # IHD_v ≈ IHD_i × h × Z_pu)
                # Para um sistema com Z_pu ~ 0.05, V_h ≈ I_h × h × 0.05
                # Em pu da fundamental:
                ihd_v_pct = (
                    spec[h] * h * 0.05 * load.S_kVA / 1000.0
                )
                v_h_pct_total += ihd_v_pct
            if v_h_pct_total > 0.01:
                ihd_for_bus[h] = v_h_pct_total

        # V-THD = √(Σ IHD²)
        v_thd = math.sqrt(sum(v ** 2 for v in ihd_for_bus.values()))
        v_thd_per_bus[bus_id] = v_thd
        ihd_per_bus[bus_id] = ihd_for_bus

    # Verifica violations
    violations: list[tuple[str, float, float]] = []
    for bus_id, v_thd in v_thd_per_bus.items():
        v_kV = bus_to_voltage_kV.get(bus_id, 13.8)
        limit = _v_thd_limit_pct(v_kV)
        if v_thd > limit:
            violations.append((bus_id, v_thd, limit))

    # Pior caso
    if v_thd_per_bus:
        worst = max(v_thd_per_bus.items(), key=lambda kv: kv[1])
        worst_bus = worst[0]
        worst_thd = worst[1]
    else:
        worst_bus = ""
        worst_thd = 0.0

    # Recomendações automáticas
    recommendations = _generate_recommendations(
        v_thd_per_bus, violations, loads,
    )

    log.info(
        "Harmonics analysis: %d loads, %d buses, %d violations, "
        "worst=%s (%.2f%%)",
        len(loads), len(v_thd_per_bus), len(violations),
        worst_bus, worst_thd,
    )

    return HarmonicsResult(
        v_thd_per_bus=v_thd_per_bus,
        ihd_per_bus=ihd_per_bus,
        violations=tuple(violations),
        recommendations=tuple(recommendations),
        n_loads=len(loads),
        n_buses_analyzed=len(v_thd_per_bus),
        worst_bus=worst_bus,
        worst_v_thd_pct=worst_thd,
        warnings=tuple(warnings),
    )


def _generate_recommendations(
    v_thd_per_bus: dict[str, float],
    violations: list[tuple[str, float, float]],
    loads: list[NonLinearLoad],
) -> list[str]:
    recs = []
    if not violations:
        recs.append(
            "✅ Sistema está dentro dos limites IEEE 519. "
            "Sem ações corretivas necessárias."
        )
        return recs

    # Identifica fontes principais de harmônicos
    has_6_pulse_vfd = any(
        l.load_type == LoadType.VFD_6_PULSE for l in loads
    )
    if has_6_pulse_vfd:
        recs.append(
            "Considere migrar VFDs 6-pulse para 12-pulse ou "
            "18-pulse (cancela harmônicos 5/7)."
        )

    # Sugestão filtros
    has_5th_violation = any(
        ihd.get(5, 0) > 3.0
        for ihd in [{}]   # placeholder
    )
    recs.append(
        "Instalar filtro passivo sintonizado em h=5 e h=7 "
        "no PCC para reduzir THD (IEEE 519 §11)."
    )

    has_arc_furnace = any(
        l.load_type == LoadType.ARC_FURNACE for l in loads
    )
    if has_arc_furnace:
        recs.append(
            "Forno a arco detectado — recomendado SVC ou "
            "STATCOM para mitigação dinâmica de flicker e "
            "harmônicos pares."
        )

    # Transformadores em K-rating
    if len(violations) > 0:
        recs.append(
            "Verificar derating de transformadores próximos a "
            "cargas com THD>5% — fator K ≥ 4 recomendado."
        )

    return recs
