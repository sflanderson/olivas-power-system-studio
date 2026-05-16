"""
app.postprocessor.studies.demand_load — Demand Load Study (DAPPER)
(v1.5.1 Sprint B + C).

Implementa o algorithm DAPPER (Reference-DAPPER §1.2 + §1.3):

::

    Connected → Demand → Design

* **Connected Load** = Σ rated kVA das cargas conectadas
* **Demand Load** = aplica multi-level demand factor por categoria
* **Design Load** = Demand × LCL factor (Long Continuous Load)

Suporta 22 categorias do :mod:`app.postprocessor.dapper_catalog`
(NEC 220.x + sectors industriais/comerciais BR).

Diversity (NEC 220.61) é capturada implicitamente: somar entries
da mesma categoria → aplicar multi-level → o "second/third level"
inerentemente reduz o demand vs soma 100%-coincident.

Cobertura normativa
====================

* NEC 2023 Article 220 — Demand factors
* NBR 5410:2004 §6 — Cálculo de cargas
* PTW DAPPER (Reference-DAPPER, paridade visual + algorítmica)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from app.core.logging_config import get_logger
from app.postprocessor.dapper_catalog import (
    DemandCategory, DemandLevel, get_category,
)

log = get_logger(__name__)


# ---------------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LoadEntry:
    """
    Uma carga individual a ser computada no estudo.

    Attributes
    ----------
    name:
        Identificador humano-legível (ex: "Bay 1 lighting").
    category_code:
        Código de :class:`DemandCategory` no catálogo.
    connected_kVA:
        Carga rated em kVA.
    pf:
        Fator de potência opcional — se None, usa
        ``category.typical_pf``.
    """

    name: str
    category_code: str
    connected_kVA: float
    pf: Optional[float] = None


# ---------------------------------------------------------------------------
# Outputs
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CategoryResult:
    """
    Resultado agregado para uma categoria.

    Mantém Connected / Demand / Design (paridade output PTW).
    """

    category_code: str
    category_label_pt: str
    nec_section: Optional[str]
    n_entries: int
    connected_kVA: float
    demand_kVA: float
    design_kVA: float
    pf: float
    lcl_factor: float


@dataclass(frozen=True)
class DemandReport:
    """
    Relatório consolidado do estudo de demand load.

    Estrutura:

    * ``entries`` — input original (preservado)
    * ``by_category`` — agregação por categoria
    * Totais Connected / Demand / Design
    * ``weighted_pf`` — média ponderada por demand_kVA
    """

    entries: List[LoadEntry]
    by_category: List[CategoryResult]
    total_connected_kVA: float
    total_demand_kVA: float
    total_design_kVA: float
    weighted_pf: float

    @property
    def overall_demand_factor(self) -> float:
        """demand / connected (0..1)."""
        if self.total_connected_kVA <= 0:
            return 0.0
        return self.total_demand_kVA / self.total_connected_kVA

    def summary(self) -> str:
        """Texto humano-legível do relatório (paridade PTW LOAD SCHEDULE)."""
        lines = []
        lines.append("=" * 70)
        lines.append(
            "  DEMAND LOAD STUDY (DAPPER) — Olivas Power System Studio"
        )
        lines.append("=" * 70)
        lines.append("")
        lines.append("RESUMO TOTAL")
        lines.append("-" * 70)
        lines.append(
            f"  Connected Load : {self.total_connected_kVA:>10,.1f} kVA"
        )
        lines.append(
            f"  Demand Load    : {self.total_demand_kVA:>10,.1f} kVA  "
            f"(DF total = {self.overall_demand_factor*100:.1f}%)"
        )
        lines.append(
            f"  Design Load    : {self.total_design_kVA:>10,.1f} kVA  "
            f"(LCL aplicado)"
        )
        lines.append(
            f"  Weighted PF    : {self.weighted_pf:>10.3f}"
        )
        lines.append("")
        lines.append("POR CATEGORIA")
        lines.append("-" * 70)
        lines.append(
            f"  {'Categoria':<35} "
            f"{'Conn':>9} {'Demand':>9} {'Design':>9}"
        )
        for cr in self.by_category:
            label = cr.category_label_pt[:35]
            lines.append(
                f"  {label:<35} "
                f"{cr.connected_kVA:>9,.1f} "
                f"{cr.demand_kVA:>9,.1f} "
                f"{cr.design_kVA:>9,.1f}"
            )
        lines.append("")
        lines.append("DETALHE POR ITEM (entries)")
        lines.append("-" * 70)
        for e in self.entries:
            lines.append(
                f"  {e.name[:35]:<35} "
                f"{e.connected_kVA:>9,.1f} kVA  "
                f"({e.category_code})"
            )
        lines.append("=" * 70)
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Algorithm: multi-level demand
# ---------------------------------------------------------------------------


def apply_demand_levels(
    connected_kVA: float, levels: Tuple[DemandLevel, ...],
) -> float:
    """
    Aplica multi-level demand factor (até 3 patamares).

    Cada level consume um "chunk" do connected restante:

    * Se ``kVA_limit`` é None: chunk = todo o restante
    * Caso contrário: chunk = min(remaining, kVA_limit)

    Exemplo (NEC 220.42, levels = [3000@100%, 120000@35%, ALL@25%]):

      Connected = 200_000:
        L1: chunk=3000 × 100%  =   3_000
        L2: chunk=120000 × 35% =  42_000
        L3: chunk=77000 × 25%  =  19_250
        ──────────────────────  ────────
        total demand           =  64_250

    Returns
    -------
    float
        Demand load em kVA.
    """
    if connected_kVA <= 0:
        return 0.0
    if not levels:
        return connected_kVA

    remaining = connected_kVA
    total = 0.0
    for lvl in levels:
        if remaining <= 0:
            break
        if lvl.kVA_limit is None:
            chunk = remaining
        else:
            chunk = min(remaining, lvl.kVA_limit)
        total += chunk * (lvl.demand_pct / 100.0)
        remaining -= chunk
        if lvl.kVA_limit is None:
            break
    return total


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def compute_demand(
    entries: List[LoadEntry],
) -> DemandReport:
    """
    Calcula Connected / Demand / Design para todas as entries.

    1. Agrupa entries por ``category_code``
    2. Soma connected_kVA dentro de cada grupo
    3. Aplica :func:`apply_demand_levels` por categoria
    4. Multiplica por LCL → design
    5. Soma totais com PF ponderado por demand

    Parameters
    ----------
    entries:
        Lista de :class:`LoadEntry`.

    Returns
    -------
    DemandReport
        Relatório consolidado.

    Raises
    ------
    KeyError
        Se ``category_code`` não existe no catálogo.
    """
    # Group by category
    groups: Dict[str, List[LoadEntry]] = {}
    for e in entries:
        groups.setdefault(e.category_code, []).append(e)

    by_category: List[CategoryResult] = []
    total_connected = 0.0
    total_demand = 0.0
    total_design = 0.0
    pf_weighted_sum = 0.0   # Σ (demand × pf)

    for code, items in groups.items():
        cat = get_category(code)
        if cat is None:
            raise KeyError(
                f"Categoria desconhecida: {code!r}. "
                f"Veja app.postprocessor.dapper_catalog.DAPPER_CATALOG"
            )

        connected = sum(e.connected_kVA for e in items)
        demand = apply_demand_levels(connected, cat.levels)
        design = demand * cat.lcl_factor

        # PF: usa override do entry ou fallback para typical
        # (média ponderada por connected_kVA dos entries da categoria)
        pf_num = 0.0
        pf_den = 0.0
        for e in items:
            pf = e.pf if e.pf is not None else cat.typical_pf
            pf_num += pf * e.connected_kVA
            pf_den += e.connected_kVA
        cat_pf = (pf_num / pf_den) if pf_den > 0 else cat.typical_pf

        cr = CategoryResult(
            category_code=cat.code,
            category_label_pt=cat.label_pt,
            nec_section=cat.nec_section,
            n_entries=len(items),
            connected_kVA=connected,
            demand_kVA=demand,
            design_kVA=design,
            pf=cat_pf,
            lcl_factor=cat.lcl_factor,
        )
        by_category.append(cr)

        total_connected += connected
        total_demand += demand
        total_design += design
        pf_weighted_sum += demand * cat_pf

    weighted_pf = (
        (pf_weighted_sum / total_demand) if total_demand > 0 else 0.0
    )

    log.info(
        "compute_demand: %d entries → %d categorias, "
        "connected=%.1f kVA → demand=%.1f kVA → design=%.1f kVA "
        "(weighted PF %.3f)",
        len(entries), len(by_category),
        total_connected, total_demand, total_design, weighted_pf,
    )

    return DemandReport(
        entries=list(entries),
        by_category=by_category,
        total_connected_kVA=total_connected,
        total_demand_kVA=total_demand,
        total_design_kVA=total_design,
        weighted_pf=weighted_pf,
    )
