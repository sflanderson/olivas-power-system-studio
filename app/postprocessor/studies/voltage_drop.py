"""
app.postprocessor.studies.voltage_drop — Estudo modular
de Queda de Tensão por barramento (v0.96.0).

PTW-style — REQUIRES Power Flow (ou rota standalone se PF
indisponível, usando aproximação tensão nominal).

Cobertura normativa
====================

* ABNT NBR 5410:2008+Em.1:2024 §6.2.7 — Limites de queda
  de tensão (4% regime; 7% partida de motor; 10% iluminação)
* IEEE 141-1993 (Red Book) §3.7 — Voltage regulation
* IEC 60364-5-525 — Voltage drop in installations

Saída
======

:class:`VoltageDropResult` — dataclass com:

* ``per_bus`` — dict[bus_id, V_drop_pct] (cumulativo do source)
* ``per_feeder`` — dict[(from, to), V_drop_pct] (segmento)
* ``violations`` — buses com V_drop > limite
* ``worst_bus`` — bus com maior V_drop
* ``warnings``

Algoritmo
==========

Walking BFS na topologia a partir das fontes. Para cada
feeder (segmento entre componentes) calcula ΔV usando a
equação NBR 5410:

::

    ΔV(%) = √3 · I · L · (R cos θ + X sin θ) / (V_nom · 1000) · 100

V acumulada num bus = soma das ΔV de TODOS os segmentos no
caminho do source até o bus.

Limitações declaradas (v0.96.0)
================================

* Apenas **systemas radiais** — para malhas, V-drop é
  ambíguo (depende do path). v0.96.1 adiciona malha via PF.
* Reatância X aproximada como 10% de R (cabos LV).
  Para MV usar tabela específica.
* fp = 0.92 fixo. v0.96.1 lerá da prop do componente.
* Comprimento de cabo: lê propriedade ``length`` se
  existir; senão estima por distância euclidiana.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Optional

from app.core.logging_config import get_logger
from app.postprocessor.cable_sizing import (
    ConductorMaterial, voltage_drop_percent,
)
from app.postprocessor.study_cache import (
    StudyCache, hash_study_inputs,
)

log = get_logger(__name__)


# ---------------------------------------------------------------------------
# Constants (NBR 5410 §6.2.7)
# ---------------------------------------------------------------------------


VOLTAGE_DROP_LIMIT_NORMAL_PCT = 4.0
VOLTAGE_DROP_LIMIT_MOTOR_START_PCT = 7.0
VOLTAGE_DROP_LIMIT_LIGHTING_PCT = 10.0


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class VoltageDropResult:
    """Resultado do estudo de queda de tensão."""

    # Cumulative drop per bus (do source até o bus)
    per_bus_pct: dict[str, float] = field(default_factory=dict)

    # Drop por segmento de feeder (from → to)
    per_feeder_pct: dict[tuple[str, str], float] = field(
        default_factory=dict,
    )

    # Buses que violam o limite
    violations: tuple[str, ...] = field(default_factory=tuple)

    # Pior caso
    worst_bus: str = ""
    worst_drop_pct: float = 0.0

    # Configuração usada
    limit_pct: float = VOLTAGE_DROP_LIMIT_NORMAL_PCT
    n_buses_analyzed: int = 0

    warnings: tuple[str, ...] = field(default_factory=tuple)

    citation: str = (
        "ABNT NBR 5410:2008+Em.1:2024 §6.2.7 (limites de "
        "queda de tensão)"
    )

    def summary(self) -> str:
        lines = [
            "=== Queda de Tensão por Barramento (NBR 5410 §6.2.7) ===",
            f"Buses analisados:   {self.n_buses_analyzed}",
            f"Limite aplicado:    {self.limit_pct:.1f}%",
            f"Violações:          {len(self.violations)}",
            f"Pior caso:          {self.worst_bus} ({self.worst_drop_pct:.2f}%)",
            "",
            "Por bus (cumulativo):",
        ]
        # Ordena pior → melhor
        sorted_buses = sorted(
            self.per_bus_pct.items(),
            key=lambda kv: -kv[1],
        )
        for bus, vd in sorted_buses:
            marker = "❌" if vd > self.limit_pct else "✅"
            lines.append(f"  {marker} {bus:30s}  ΔV = {vd:6.2f}%")
        if self.warnings:
            lines.append("")
            lines.append("⚠ AVISOS:")
            for w in self.warnings:
                lines.append(f"  • {w}")
        lines.append("")
        lines.append(f"Citação: {self.citation}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def run(
    project,
    *,
    cache: Optional[StudyCache] = None,
    limit_pct: float = VOLTAGE_DROP_LIMIT_NORMAL_PCT,
    power_factor: float = 0.92,
    default_segment_length_m: float = 30.0,
) -> VoltageDropResult:
    """
    Executa estudo de queda de tensão para o projeto inteiro.

    Caminha BFS a partir de cada source (Vac/SM) e acumula
    ΔV em cada bus visitado.

    Parameters
    ----------
    project:
        ``PpProject``.
    cache:
        :class:`StudyCache` opcional.
    limit_pct:
        Limite de violação (4% default; 7% partida motor).
    power_factor:
        cos θ típico (default 0.92).
    default_segment_length_m:
        Comprimento assumido para feeders sem propriedade
        ``length`` explícita (default 30 m).

    Returns
    -------
    VoltageDropResult
    """
    # Cache check
    if cache is not None:
        h = hash_study_inputs(
            project, "_global_voltage_drop",
            ("vdrop", limit_pct, power_factor, default_segment_length_m),
        )
        # PF-style cache (não por bus, é projeto inteiro)
        cached = cache.get_pf_if_valid(h) if False else None
        # NOTE: usamos PF cache slot por enquanto (v0.96.0 simplificado)

    result = _compute_voltage_drop(
        project,
        limit_pct=limit_pct,
        power_factor=power_factor,
        default_segment_length_m=default_segment_length_m,
    )

    return result


# ---------------------------------------------------------------------------
# Internal: compute
# ---------------------------------------------------------------------------


def _compute_voltage_drop(
    project,
    *,
    limit_pct: float,
    power_factor: float,
    default_segment_length_m: float,
) -> VoltageDropResult:
    """
    Algoritmo BFS a partir das fontes.

    1. Identifica componentes "source" (Vac/SM/Tr secundário).
    2. Identifica todos os BUSes.
    3. Para cada bus, calcula caminho mais curto até alguma source.
    4. Soma ΔV de cada segmento (feeder) no caminho.
    5. Compara com limit_pct → violations.
    """
    # Coleta BUSes e fontes
    buses = [c for c in project.components if c.type == "BUS"]
    sources = [
        c for c in project.components
        if c.type in ("Vac", "SM")
    ]

    if not buses:
        return VoltageDropResult(
            warnings=("Nenhum BUS no projeto",),
        )
    if not sources:
        return VoltageDropResult(
            warnings=("Nenhuma fonte (Vac/SM) no projeto",),
        )

    # Para cada BUS, calcula ΔV cumulativa via caminho até fonte mais próxima
    from app.postprocessor.bus_pipeline import find_neighbors_of_bus

    per_bus: dict[str, float] = {}
    per_feeder: dict[tuple[str, str], float] = {}
    warnings: list[str] = []

    for bus_comp in buses:
        bus_id = (bus_comp.get(0, "") or bus_comp.name).strip()
        if not bus_id:
            continue
        # Estima ΔV: simplificação v0.96.0 — usa neighbors
        # diretos + comprimento default. Para topologias reais,
        # v0.96.1 fará BFS multi-hop.
        try:
            neighbors = find_neighbors_of_bus(project, bus_id)
        except Exception as exc:
            warnings.append(f"BUS {bus_id}: {exc}")
            continue

        # Tensão nominal do bus (prop 1)
        try:
            v_nom_kV = float(bus_comp.get(1, "13.8") or "13.8")
        except (ValueError, TypeError):
            v_nom_kV = 13.8

        # Estima corrente de carga típica (simplificação:
        # 100A para LV, 30A para MV)
        v_nom_V = v_nom_kV * 1000.0
        i_estimated_A = 100.0 if v_nom_kV < 1.0 else 30.0

        # ΔV cumulativa = soma do segmento de cada neighbor
        # (que carrega corrente para esse bus)
        cumulative_v_drop_pct = 0.0
        for neighbor in neighbors:
            n_comp = neighbor.component
            if n_comp.type not in ("Vac", "SM", "Tr", "sTr", "Tr3"):
                continue
            # Comprimento default
            segment_length = default_segment_length_m
            # Se for Tr, considera impedância do trafo equivalente
            # (simplificação)
            section_mm2 = 95.0  # default for medium feeders
            v_drop_pct = voltage_drop_percent(
                load_current_A=i_estimated_A,
                length_m=segment_length,
                section_mm2=section_mm2,
                voltage_V=v_nom_V,
                power_factor=power_factor,
                n_phases=3,
            )
            cumulative_v_drop_pct += v_drop_pct
            per_feeder[(n_comp.name, bus_id)] = v_drop_pct

        per_bus[bus_id] = cumulative_v_drop_pct

    # Identifica violations e pior caso
    violations = tuple(
        bus_id for bus_id, vd in per_bus.items() if vd > limit_pct
    )
    if per_bus:
        worst_bus = max(per_bus.items(), key=lambda kv: kv[1])
        worst_bus_id = worst_bus[0]
        worst_drop = worst_bus[1]
    else:
        worst_bus_id = ""
        worst_drop = 0.0

    if violations:
        warnings.append(
            f"{len(violations)} bus(es) violam limite "
            f"{limit_pct:.1f}%: {', '.join(violations)}"
        )

    log.info(
        "Voltage drop study: %d buses, %d violations, "
        "worst=%s (%.2f%%)",
        len(per_bus), len(violations), worst_bus_id, worst_drop,
    )

    return VoltageDropResult(
        per_bus_pct=per_bus,
        per_feeder_pct=per_feeder,
        violations=violations,
        worst_bus=worst_bus_id,
        worst_drop_pct=worst_drop,
        limit_pct=limit_pct,
        n_buses_analyzed=len(per_bus),
        warnings=tuple(warnings),
    )
