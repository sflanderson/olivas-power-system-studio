"""
app.postprocessor.dapper_catalog — DAPPER Demand Load Library
(v1.5.1 Sprint A).

Catálogo de **22 categorias** de demanda mapeadas para:

* **NEC 220.x** (16 categorias) — National Electrical Code 2023:
  cálculo de cargas para ramais, alimentadores e serviços
* **Sectors industriais/comerciais BR** (6 categorias) — paridade
  com PTW DAPPER + adições para mercado brasileiro

Cada categoria define:

* ``code`` — identificador único (snake_case ALL_CAPS)
* ``label_pt`` / ``label_en`` — descrições humano-legíveis
* ``nec_section`` — referência NEC (ou None para sectors)
* ``load_type`` — Constant Z / Constant kVA / Constant I
* ``levels`` — multi-level demand factor (1-3 níveis)
* ``lcl_factor`` — design factor (LCL / Long Continuous Load)
* ``typical_pf`` — fator de potência típico
* ``notes_pt`` — observações de aplicação

**Vantagem competitiva sobre PTW**: PTW DAPPER traz 7 defaults
genéricos + 13 slots vazios. Olivas vem com 22 categorias prontas
mapeadas explicitamente para NEC 220.x — usuário brasileiro não
precisa decifrar as tabelas e configurar slot-a-slot.

Cobertura normativa
====================

* NEC 2023 Article 220 — Branch-circuit, feeder, service load calcs
* NBR 5410:2004 — Instalações elétricas de baixa tensão
* IEC 60364-1 — Electrical installations of buildings
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple


# ---------------------------------------------------------------------------
# Enums + dataclasses
# ---------------------------------------------------------------------------


class LoadType(str, Enum):
    """
    Modelo elétrico da categoria — afeta como a carga responde a
    variações de tensão (importa para Power Flow).
    """

    CONSTANT_Z = "Z"      # P ∝ V² (resistivo, iluminação incandescente)
    CONSTANT_KVA = "K"    # P constante (motor com regulação, eletrônica)
    CONSTANT_I = "I"      # I constante (carga resistiva controlada)


@dataclass(frozen=True)
class DemandLevel:
    """
    Um patamar (chunk) da curva multi-level de demand factor.

    Tabela DAPPER típica tem até 3 patamares:
        Level 1: 0..kVA_limit_1   @ pct_1
        Level 2: kVA_limit_1..kVA_limit_2  @ pct_2
        Level 3: kVA_limit_2..∞   @ pct_3   (kVA_limit=None)
    """

    kVA_limit: Optional[float]    # None = "ALL kVA" (último nível)
    demand_pct: float             # 0..200%


@dataclass(frozen=True)
class DemandCategory:
    """
    Categoria de demanda no catálogo DAPPER.

    Identidade: ``code`` deve ser único no catálogo.
    """

    code: str
    label_pt: str
    label_en: str
    nec_section: Optional[str]    # "220.42" ou None
    load_type: LoadType
    levels: Tuple[DemandLevel, ...]
    lcl_factor: float = 1.00
    typical_pf: float = 0.85
    notes_pt: str = ""


# ---------------------------------------------------------------------------
# Catálogo (22 categorias)
# ---------------------------------------------------------------------------


_LEVEL_ALL_100 = (DemandLevel(kVA_limit=None, demand_pct=100.0),)


DAPPER_CATALOG: Tuple[DemandCategory, ...] = (
    # ============== NEC 220 (16 categorias) ==============
    DemandCategory(
        code="NEC_220_42_LIGHTING",
        label_pt="Iluminação geral (NEC 220.42)",
        label_en="General lighting",
        nec_section="220.42",
        load_type=LoadType.CONSTANT_KVA,
        levels=(
            DemandLevel(kVA_limit=3000.0, demand_pct=100.0),
            DemandLevel(kVA_limit=120000.0, demand_pct=35.0),
            DemandLevel(kVA_limit=None, demand_pct=25.0),
        ),
        lcl_factor=1.25,
        typical_pf=0.95,
        notes_pt=(
            "Tabela NEC 220.42 (residential dwelling): 100% até "
            "3000 VA, 35% de 3001-120000 VA, 25% acima."
        ),
    ),
    DemandCategory(
        code="NEC_220_50_MOTORS",
        label_pt="Motores não-MCC (NEC 220.50)",
        label_en="Motors (non-MCC)",
        nec_section="220.50",
        load_type=LoadType.CONSTANT_KVA,
        levels=_LEVEL_ALL_100,
        lcl_factor=1.25,
        typical_pf=0.85,
        notes_pt=(
            "100% da soma dos motores + 25% do maior motor "
            "(NEC 430.24). LCL=1.25 captura o boost do largest motor."
        ),
    ),
    DemandCategory(
        code="NEC_220_51_HEATING",
        label_pt="Aquecimento elétrico fixo (NEC 220.51)",
        label_en="Fixed electric heating",
        nec_section="220.51",
        load_type=LoadType.CONSTANT_Z,
        levels=_LEVEL_ALL_100,
        lcl_factor=1.25,
        typical_pf=1.00,
        notes_pt="100% da carga conectada (NEC 220.51).",
    ),
    DemandCategory(
        code="NEC_220_52_SMALL_APPLIANCE",
        label_pt="Pequenos eletrodomésticos (NEC 220.52)",
        label_en="Small appliance circuits",
        nec_section="220.52",
        load_type=LoadType.CONSTANT_KVA,
        levels=_LEVEL_ALL_100,
        lcl_factor=1.00,
        typical_pf=0.90,
        notes_pt=(
            "Mínimo 1500 VA × 2 circuitos (residencial). "
            "Sujeito ao mesmo DF da iluminação se incorporado."
        ),
    ),
    DemandCategory(
        code="NEC_220_53_LAUNDRY",
        label_pt="Lavanderia (NEC 220.53)",
        label_en="Laundry circuit",
        nec_section="220.53",
        load_type=LoadType.CONSTANT_KVA,
        levels=_LEVEL_ALL_100,
        lcl_factor=1.00,
        typical_pf=0.90,
        notes_pt="Mínimo 1500 VA por circuito de lavanderia.",
    ),
    DemandCategory(
        code="NEC_220_54_DRYER",
        label_pt="Secadora elétrica (NEC 220.54)",
        label_en="Electric dryer",
        nec_section="220.54",
        load_type=LoadType.CONSTANT_Z,
        levels=(
            DemandLevel(kVA_limit=5000.0, demand_pct=100.0),
            DemandLevel(kVA_limit=None, demand_pct=70.0),
        ),
        lcl_factor=1.00,
        typical_pf=1.00,
        notes_pt=(
            "Tabela 220.54: 100% até 5 kVA por unidade; "
            "DF reduzido para múltiplas unidades."
        ),
    ),
    DemandCategory(
        code="NEC_220_55_RANGES",
        label_pt="Fogões elétricos residenciais (NEC 220.55)",
        label_en="Electric ranges (residential)",
        nec_section="220.55",
        load_type=LoadType.CONSTANT_Z,
        levels=(
            DemandLevel(kVA_limit=8000.0, demand_pct=100.0),
            DemandLevel(kVA_limit=None, demand_pct=80.0),
        ),
        lcl_factor=1.00,
        typical_pf=1.00,
        notes_pt=(
            "Tabela 220.55 col A (single unit): 8 kW max + DF para "
            "≥2 unidades."
        ),
    ),
    DemandCategory(
        code="NEC_220_56_KITCHEN_EQUIPMENT",
        label_pt="Equipamentos cozinha comercial (NEC 220.56)",
        label_en="Commercial kitchen equipment",
        nec_section="220.56",
        load_type=LoadType.CONSTANT_Z,
        levels=(
            DemandLevel(kVA_limit=None, demand_pct=65.0),
        ),
        lcl_factor=1.00,
        typical_pf=0.95,
        notes_pt=(
            "Tabela 220.56: 65% para ≥6 unidades; aplicação "
            "típica em restaurantes."
        ),
    ),
    DemandCategory(
        code="NEC_220_60_NONCOINCIDENT",
        label_pt="Cargas não-coincidentes (NEC 220.60)",
        label_en="Non-coincident loads (largest only)",
        nec_section="220.60",
        load_type=LoadType.CONSTANT_KVA,
        levels=_LEVEL_ALL_100,
        lcl_factor=1.00,
        typical_pf=0.90,
        notes_pt=(
            "NEC 220.60: somente a maior carga é considerada "
            "(ex: AC vs. heating)."
        ),
    ),
    DemandCategory(
        code="NEC_220_61_FEEDER_NEUTRAL",
        label_pt="Carga de neutro (NEC 220.61)",
        label_en="Feeder neutral",
        nec_section="220.61",
        load_type=LoadType.CONSTANT_KVA,
        levels=(
            DemandLevel(kVA_limit=200000.0, demand_pct=100.0),
            DemandLevel(kVA_limit=None, demand_pct=70.0),
        ),
        lcl_factor=1.00,
        typical_pf=0.95,
        notes_pt=(
            "100% até 200 A, 70% acima. Aplicável a alimentadores "
            "balanceados."
        ),
    ),
    DemandCategory(
        code="NEC_220_82_OPTIONAL_DWELLING",
        label_pt="Método opcional dwelling (NEC 220.82)",
        label_en="Optional method - dwelling",
        nec_section="220.82",
        load_type=LoadType.CONSTANT_KVA,
        levels=(
            DemandLevel(kVA_limit=10000.0, demand_pct=100.0),
            DemandLevel(kVA_limit=None, demand_pct=40.0),
        ),
        lcl_factor=1.00,
        typical_pf=0.95,
        notes_pt=(
            "Método opcional dwelling unifamiliar: 100% primeiros "
            "10 kVA, 40% acima."
        ),
    ),
    DemandCategory(
        code="NEC_220_83_EXISTING_DWELLING",
        label_pt="Dwelling existente (NEC 220.83)",
        label_en="Existing dwelling",
        nec_section="220.83",
        load_type=LoadType.CONSTANT_KVA,
        levels=(
            DemandLevel(kVA_limit=8000.0, demand_pct=100.0),
            DemandLevel(kVA_limit=None, demand_pct=40.0),
        ),
        lcl_factor=1.00,
        typical_pf=0.95,
        notes_pt=(
            "Existing dwelling com nova carga: 100% até 8 kVA, "
            "40% acima."
        ),
    ),
    DemandCategory(
        code="NEC_220_84_MULTIFAMILY",
        label_pt="Multifamiliar (NEC 220.84)",
        label_en="Multifamily dwelling",
        nec_section="220.84",
        load_type=LoadType.CONSTANT_KVA,
        levels=(
            DemandLevel(kVA_limit=None, demand_pct=45.0),
        ),
        lcl_factor=1.00,
        typical_pf=0.95,
        notes_pt=(
            "Tabela 220.84: 45% para 5+ unidades habitacionais "
            "(simplificado)."
        ),
    ),
    DemandCategory(
        code="NEC_220_86_SCHOOLS",
        label_pt="Escolas (NEC 220.86)",
        label_en="Schools",
        nec_section="220.86",
        load_type=LoadType.CONSTANT_KVA,
        levels=(
            DemandLevel(kVA_limit=33000.0, demand_pct=100.0),
            DemandLevel(kVA_limit=220000.0, demand_pct=75.0),
            DemandLevel(kVA_limit=None, demand_pct=25.0),
        ),
        lcl_factor=1.00,
        typical_pf=0.95,
        notes_pt=(
            "Tabela 220.86: 100% até 33 kVA, 75% até 220 kVA, "
            "25% acima."
        ),
    ),
    DemandCategory(
        code="NEC_220_87_EXISTING_SERVICE",
        label_pt="Serviço existente (NEC 220.87)",
        label_en="Existing services",
        nec_section="220.87",
        load_type=LoadType.CONSTANT_KVA,
        levels=_LEVEL_ALL_100,
        lcl_factor=1.25,
        typical_pf=0.92,
        notes_pt=(
            "125% do peak demand registrado nos últimos 12 meses."
        ),
    ),
    DemandCategory(
        code="NEC_220_88_NEW_RESTAURANTS",
        label_pt="Novos restaurantes (NEC 220.88)",
        label_en="New restaurants",
        nec_section="220.88",
        load_type=LoadType.CONSTANT_KVA,
        levels=(
            DemandLevel(kVA_limit=200000.0, demand_pct=80.0),
            DemandLevel(kVA_limit=None, demand_pct=10.0),
        ),
        lcl_factor=1.00,
        typical_pf=0.92,
        notes_pt=(
            "Tabela 220.88: 80% até 200 kVA, 10% acima "
            "(toda eletricidade)."
        ),
    ),

    # ============== Sectors industriais/comerciais BR (6) ==============
    DemandCategory(
        code="RECEPTACLES_GENERAL",
        label_pt="Tomadas gerais (paridade PTW)",
        label_en="Receptacles general",
        nec_section=None,
        load_type=LoadType.CONSTANT_Z,
        levels=(
            DemandLevel(kVA_limit=10000.0, demand_pct=100.0),
            DemandLevel(kVA_limit=None, demand_pct=50.0),
        ),
        lcl_factor=1.00,
        typical_pf=0.92,
        notes_pt=(
            "Paridade PTW Reference-DAPPER §1.4.10: 10 kVA @ 100%, "
            "resto @ 50%."
        ),
    ),
    DemandCategory(
        code="OFFICE_EQUIPMENT",
        label_pt="Equipamentos de escritório",
        label_en="Office equipment",
        nec_section=None,
        load_type=LoadType.CONSTANT_Z,
        levels=_LEVEL_ALL_100,
        lcl_factor=1.00,
        typical_pf=0.95,
        notes_pt="Paridade PTW (computadores, copiadoras, etc).",
    ),
    DemandCategory(
        code="CAPACITOR_BANK",
        label_pt="Banco de capacitores",
        label_en="Capacitor bank",
        nec_section=None,
        load_type=LoadType.CONSTANT_Z,
        levels=_LEVEL_ALL_100,
        lcl_factor=1.35,
        typical_pf=0.00,
        notes_pt=(
            "Paridade PTW: LCL=1.35 captura energização "
            "(transient inrush)."
        ),
    ),
    DemandCategory(
        code="STANDBY_LOADS",
        label_pt="Cargas standby (UPS / geração)",
        label_en="Standby loads",
        nec_section=None,
        load_type=LoadType.CONSTANT_KVA,
        levels=_LEVEL_ALL_100,
        lcl_factor=1.25,
        typical_pf=0.90,
        notes_pt="Paridade PTW: cargas em UPS/gerador (alta confiabilidade).",
    ),
    DemandCategory(
        code="INDUSTRIAL_PROCESS",
        label_pt="Processo industrial contínuo",
        label_en="Industrial continuous process",
        nec_section=None,
        load_type=LoadType.CONSTANT_KVA,
        levels=_LEVEL_ALL_100,
        lcl_factor=1.25,
        typical_pf=0.85,
        notes_pt=(
            "Processo 24/7 (NBR 5410 §6.2.6 — cargas contínuas): "
            "LCL=1.25."
        ),
    ),
    DemandCategory(
        code="DATA_CENTER",
        label_pt="Data Center / TI",
        label_en="Data center / IT",
        nec_section=None,
        load_type=LoadType.CONSTANT_KVA,
        levels=_LEVEL_ALL_100,
        lcl_factor=1.40,
        typical_pf=0.95,
        notes_pt=(
            "PUE típico 1.4 (TIA-942): inclui IT load + cooling "
            "+ overhead."
        ),
    ),
)


# ---------------------------------------------------------------------------
# Lookup helpers
# ---------------------------------------------------------------------------


_BY_CODE = {c.code: c for c in DAPPER_CATALOG}


def get_category(code: str) -> Optional[DemandCategory]:
    """Lookup por code; retorna None se não existe."""
    return _BY_CODE.get(code)


def get_categories_by_nec(nec_section: str) -> List[DemandCategory]:
    """Lista categorias com a seção NEC dada (ex: '220.42')."""
    return [c for c in DAPPER_CATALOG if c.nec_section == nec_section]


def list_all_categories() -> List[DemandCategory]:
    """Retorna lista de todas as 22 categorias."""
    return list(DAPPER_CATALOG)


def list_nec_categories() -> List[DemandCategory]:
    """Apenas categorias com NEC section explícita (16)."""
    return [c for c in DAPPER_CATALOG if c.nec_section is not None]


def list_sector_categories() -> List[DemandCategory]:
    """Apenas categorias sem NEC section (6 sectors)."""
    return [c for c in DAPPER_CATALOG if c.nec_section is None]
