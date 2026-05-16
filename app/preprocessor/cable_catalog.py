"""
app.preprocessor.cable_catalog — biblioteca de cabos
elétricos brasileiros conforme NBR 5356, NBR 6251 e
NBR 7286 (v0.43).

Cobertura
==========

* **Cabos de cobre nu** (LV/MV) NBR 5356 — usado em malhas
  de aterramento e barramentos abertos.
* **Cabos isolados extrudados** EPR/XLPE 0.6/1 kV até
  20 kV, NBR 6251 / IEC 60502 — uso geral em distribuição.
* **Cabos de potência** com armadura para média tensão,
  NBR 7286 — instalação enterrada / industrial.

Cada entrada inclui:

* Bitola nominal (mm²) — AWG/MCM aproximado
* Material (cobre, alumínio)
* Resistência DC e AC @ 90°C (Ω/km)
* Reatância indutiva (Ω/km) — depende da geometria
* Capacitância (μF/km) — para cabos isolados longos
* Ampacidade (A) em condições de instalação típicas
* Curto-circuito ICW (kA, 1s) — IEC 60364-4-43

API similar a equipment_catalog: ``find_cable``,
``list_cables``.

Limitação
==========

Valores nominais são REPRESENTATIVOS de fabricantes
brasileiros (Prysmian Draka, Nexans BR, Furukawa). Para
projeto final, USAR datasheet do fabricante.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class ConductorMaterial(str, Enum):
    """Material do condutor."""
    COPPER = "Cu"
    ALUMINUM = "Al"


class InsulationType(str, Enum):
    """Tipo de isolação."""
    BARE = "Nu"            # condutor nu (sem isolação)
    PVC = "PVC"            # 0.6/1 kV padrão
    EPR = "EPR"            # média tensão até 36 kV
    XLPE = "XLPE"          # média tensão (mais comum BR)
    HEPR = "HEPR"          # alta resistência ao calor


class InstallationType(str, Enum):
    """Método de instalação (afeta ampacidade)."""
    AIR = "ar"               # eletroduto aparente / bandeja
    BURIED = "enterrado"     # diretamente enterrado
    UNDERGROUND_DUCT = "duto" # em duto enterrado
    TRAY = "leito"           # leito ventilado


@dataclass(frozen=True)
class CatalogCable:
    """
    Entrada de catálogo para cabo elétrico industrial.

    Attributes
    ----------
    name:
        Identificador (ex: "Cu 35 mm² EPR 8.7/15kV").
    conductor_material:
        Cu ou Al.
    insulation:
        Tipo de isolação (BARE, PVC, EPR, XLPE, HEPR).
    rated_voltage_kV:
        V isolação (0.6, 1, 8.7/15, 12/20, 18/30).
    cross_section_mm2:
        Bitola nominal em mm².
    R_dc_ohm_per_km_at_20C:
        Resistência DC a 20°C (Ω/km).
    R_ac_ohm_per_km_at_90C:
        Resistência AC a 90°C (Ω/km) — temperatura operacional
        típica de cabo carregado.
    X_ohm_per_km:
        Reatância indutiva positiva (Ω/km) — depende da
        geometria, valor típico para trifólio.
    C_uF_per_km:
        Capacitância para terra (μF/km) — relevante para cabos
        longos MT (>1 km).
    ampacity_air_A:
        Ampacidade típica em ar (eletroduto/bandeja).
    ampacity_buried_A:
        Ampacidade enterrado.
    icw_kA_1s:
        Corrente de curto-circuito admissível 1s
        (= K·S/√t, K=143 Cu/95 Al para EPR/XLPE).
    """
    name: str
    conductor_material: ConductorMaterial
    insulation: InsulationType
    rated_voltage_kV: float
    cross_section_mm2: float
    R_dc_ohm_per_km_at_20C: float
    R_ac_ohm_per_km_at_90C: float
    X_ohm_per_km: float
    C_uF_per_km: float = 0.0    # 0 = não relevante (BARE/PVC curto)
    ampacity_air_A: float = 0.0
    ampacity_buried_A: float = 0.0
    icw_kA_1s: float = 0.0
    notes: str = ""


# ---------------------------------------------------------------------------
# Catálogo: cabos cobre PVC 0.6/1 kV (BT industrial)
# Fonte: NBR 6251 + Prysmian Draka EUROFORCE catalog
# ---------------------------------------------------------------------------


_CU_PVC_LV: tuple[CatalogCable, ...] = (
    CatalogCable(
        name="Cu 2.5mm² PVC 0.6/1kV",
        conductor_material=ConductorMaterial.COPPER,
        insulation=InsulationType.PVC,
        rated_voltage_kV=1.0, cross_section_mm2=2.5,
        R_dc_ohm_per_km_at_20C=7.41, R_ac_ohm_per_km_at_90C=9.41,
        X_ohm_per_km=0.116, ampacity_air_A=24.0, ampacity_buried_A=33.0,
        icw_kA_1s=0.357,
        notes="Bitola mínima de circuito de iluminação (NBR 5410)",
    ),
    CatalogCable(
        name="Cu 4mm² PVC 0.6/1kV",
        conductor_material=ConductorMaterial.COPPER,
        insulation=InsulationType.PVC,
        rated_voltage_kV=1.0, cross_section_mm2=4.0,
        R_dc_ohm_per_km_at_20C=4.61, R_ac_ohm_per_km_at_90C=5.85,
        X_ohm_per_km=0.107, ampacity_air_A=32.0, ampacity_buried_A=43.0,
        icw_kA_1s=0.572,
    ),
    CatalogCable(
        name="Cu 10mm² PVC 0.6/1kV",
        conductor_material=ConductorMaterial.COPPER,
        insulation=InsulationType.PVC,
        rated_voltage_kV=1.0, cross_section_mm2=10.0,
        R_dc_ohm_per_km_at_20C=1.83, R_ac_ohm_per_km_at_90C=2.33,
        X_ohm_per_km=0.092, ampacity_air_A=57.0, ampacity_buried_A=75.0,
        icw_kA_1s=1.430,
    ),
    CatalogCable(
        name="Cu 25mm² PVC 0.6/1kV",
        conductor_material=ConductorMaterial.COPPER,
        insulation=InsulationType.PVC,
        rated_voltage_kV=1.0, cross_section_mm2=25.0,
        R_dc_ohm_per_km_at_20C=0.727, R_ac_ohm_per_km_at_90C=0.927,
        X_ohm_per_km=0.084, ampacity_air_A=101.0, ampacity_buried_A=132.0,
        icw_kA_1s=3.575,
    ),
    CatalogCable(
        name="Cu 50mm² PVC 0.6/1kV",
        conductor_material=ConductorMaterial.COPPER,
        insulation=InsulationType.PVC,
        rated_voltage_kV=1.0, cross_section_mm2=50.0,
        R_dc_ohm_per_km_at_20C=0.387, R_ac_ohm_per_km_at_90C=0.494,
        X_ohm_per_km=0.082, ampacity_air_A=150.0, ampacity_buried_A=192.0,
        icw_kA_1s=7.150,
    ),
    CatalogCable(
        name="Cu 95mm² PVC 0.6/1kV",
        conductor_material=ConductorMaterial.COPPER,
        insulation=InsulationType.PVC,
        rated_voltage_kV=1.0, cross_section_mm2=95.0,
        R_dc_ohm_per_km_at_20C=0.193, R_ac_ohm_per_km_at_90C=0.247,
        X_ohm_per_km=0.080, ampacity_air_A=232.0, ampacity_buried_A=290.0,
        icw_kA_1s=13.59,
    ),
    CatalogCable(
        name="Cu 240mm² PVC 0.6/1kV",
        conductor_material=ConductorMaterial.COPPER,
        insulation=InsulationType.PVC,
        rated_voltage_kV=1.0, cross_section_mm2=240.0,
        R_dc_ohm_per_km_at_20C=0.0754, R_ac_ohm_per_km_at_90C=0.0972,
        X_ohm_per_km=0.077, ampacity_air_A=434.0, ampacity_buried_A=496.0,
        icw_kA_1s=34.32,
    ),
    CatalogCable(
        name="Cu 500mm² PVC 0.6/1kV",
        conductor_material=ConductorMaterial.COPPER,
        insulation=InsulationType.PVC,
        rated_voltage_kV=1.0, cross_section_mm2=500.0,
        R_dc_ohm_per_km_at_20C=0.0366, R_ac_ohm_per_km_at_90C=0.0490,
        X_ohm_per_km=0.075, ampacity_air_A=685.0, ampacity_buried_A=706.0,
        icw_kA_1s=71.50,
    ),
)


# ---------------------------------------------------------------------------
# Catálogo: cabos cobre EPR 8.7/15 kV (MT 15kV class)
# Fonte: NBR 7286 + Prysmian Voltal EPR
# ---------------------------------------------------------------------------


_CU_EPR_15kV: tuple[CatalogCable, ...] = (
    CatalogCable(
        name="Cu 35mm² EPR 8.7/15kV",
        conductor_material=ConductorMaterial.COPPER,
        insulation=InsulationType.EPR,
        rated_voltage_kV=15.0, cross_section_mm2=35.0,
        R_dc_ohm_per_km_at_20C=0.524, R_ac_ohm_per_km_at_90C=0.668,
        X_ohm_per_km=0.176, C_uF_per_km=0.151,
        ampacity_air_A=125.0, ampacity_buried_A=155.0,
        icw_kA_1s=5.005,
    ),
    CatalogCable(
        name="Cu 70mm² EPR 8.7/15kV",
        conductor_material=ConductorMaterial.COPPER,
        insulation=InsulationType.EPR,
        rated_voltage_kV=15.0, cross_section_mm2=70.0,
        R_dc_ohm_per_km_at_20C=0.268, R_ac_ohm_per_km_at_90C=0.342,
        X_ohm_per_km=0.166, C_uF_per_km=0.184,
        ampacity_air_A=180.0, ampacity_buried_A=215.0,
        icw_kA_1s=10.01,
    ),
    CatalogCable(
        name="Cu 120mm² EPR 8.7/15kV",
        conductor_material=ConductorMaterial.COPPER,
        insulation=InsulationType.EPR,
        rated_voltage_kV=15.0, cross_section_mm2=120.0,
        R_dc_ohm_per_km_at_20C=0.153, R_ac_ohm_per_km_at_90C=0.196,
        X_ohm_per_km=0.157, C_uF_per_km=0.227,
        ampacity_air_A=245.0, ampacity_buried_A=285.0,
        icw_kA_1s=17.16,
    ),
    CatalogCable(
        name="Cu 240mm² EPR 8.7/15kV",
        conductor_material=ConductorMaterial.COPPER,
        insulation=InsulationType.EPR,
        rated_voltage_kV=15.0, cross_section_mm2=240.0,
        R_dc_ohm_per_km_at_20C=0.0754, R_ac_ohm_per_km_at_90C=0.0972,
        X_ohm_per_km=0.151, C_uF_per_km=0.298,
        ampacity_air_A=355.0, ampacity_buried_A=400.0,
        icw_kA_1s=34.32,
    ),
    CatalogCable(
        name="Cu 500mm² EPR 8.7/15kV",
        conductor_material=ConductorMaterial.COPPER,
        insulation=InsulationType.EPR,
        rated_voltage_kV=15.0, cross_section_mm2=500.0,
        R_dc_ohm_per_km_at_20C=0.0366, R_ac_ohm_per_km_at_90C=0.0490,
        X_ohm_per_km=0.144, C_uF_per_km=0.392,
        ampacity_air_A=565.0, ampacity_buried_A=600.0,
        icw_kA_1s=71.50,
    ),
)


# ---------------------------------------------------------------------------
# Catálogo: cabos XLPE 12/20 kV (MT 20-25 kV class)
# Fonte: NBR 7286 + Furukawa Voltax XLPE
# ---------------------------------------------------------------------------


_CU_XLPE_20kV: tuple[CatalogCable, ...] = (
    CatalogCable(
        name="Cu 95mm² XLPE 12/20kV",
        conductor_material=ConductorMaterial.COPPER,
        insulation=InsulationType.XLPE,
        rated_voltage_kV=20.0, cross_section_mm2=95.0,
        R_dc_ohm_per_km_at_20C=0.193, R_ac_ohm_per_km_at_90C=0.247,
        X_ohm_per_km=0.171, C_uF_per_km=0.180,
        ampacity_air_A=215.0, ampacity_buried_A=250.0,
        icw_kA_1s=13.59,
    ),
    CatalogCable(
        name="Cu 185mm² XLPE 12/20kV",
        conductor_material=ConductorMaterial.COPPER,
        insulation=InsulationType.XLPE,
        rated_voltage_kV=20.0, cross_section_mm2=185.0,
        R_dc_ohm_per_km_at_20C=0.0991, R_ac_ohm_per_km_at_90C=0.128,
        X_ohm_per_km=0.163, C_uF_per_km=0.230,
        ampacity_air_A=315.0, ampacity_buried_A=355.0,
        icw_kA_1s=26.46,
    ),
    CatalogCable(
        name="Cu 400mm² XLPE 12/20kV",
        conductor_material=ConductorMaterial.COPPER,
        insulation=InsulationType.XLPE,
        rated_voltage_kV=20.0, cross_section_mm2=400.0,
        R_dc_ohm_per_km_at_20C=0.0470, R_ac_ohm_per_km_at_90C=0.0612,
        X_ohm_per_km=0.155, C_uF_per_km=0.310,
        ampacity_air_A=505.0, ampacity_buried_A=540.0,
        icw_kA_1s=57.20,
    ),
)


# ---------------------------------------------------------------------------
# Catálogo: cobre nu (NBR 5356) — aterramento / barramento
# ---------------------------------------------------------------------------


_CU_BARE: tuple[CatalogCable, ...] = (
    CatalogCable(
        name="Cobre nu 16mm² (NBR 5356)",
        conductor_material=ConductorMaterial.COPPER,
        insulation=InsulationType.BARE,
        rated_voltage_kV=0.0, cross_section_mm2=16.0,
        R_dc_ohm_per_km_at_20C=1.150, R_ac_ohm_per_km_at_90C=1.460,
        X_ohm_per_km=0.0, ampacity_air_A=80.0,
        icw_kA_1s=2.288,
        notes="Mínimo recomendado p/ malha de aterramento de SE",
    ),
    CatalogCable(
        name="Cobre nu 35mm² (NBR 5356)",
        conductor_material=ConductorMaterial.COPPER,
        insulation=InsulationType.BARE,
        rated_voltage_kV=0.0, cross_section_mm2=35.0,
        R_dc_ohm_per_km_at_20C=0.524, R_ac_ohm_per_km_at_90C=0.668,
        X_ohm_per_km=0.0, ampacity_air_A=140.0,
        icw_kA_1s=5.005,
    ),
    CatalogCable(
        name="Cobre nu 70mm² (NBR 5356)",
        conductor_material=ConductorMaterial.COPPER,
        insulation=InsulationType.BARE,
        rated_voltage_kV=0.0, cross_section_mm2=70.0,
        R_dc_ohm_per_km_at_20C=0.268, R_ac_ohm_per_km_at_90C=0.342,
        X_ohm_per_km=0.0, ampacity_air_A=240.0,
        icw_kA_1s=10.01,
    ),
)


# Catálogo total
CABLE_CATALOG: tuple[CatalogCable, ...] = (
    _CU_PVC_LV + _CU_EPR_15kV + _CU_XLPE_20kV + _CU_BARE
)


# ---------------------------------------------------------------------------
# Search/lookup helpers
# ---------------------------------------------------------------------------


def list_cables(
    *,
    cross_section_min: float = 0.0,
    cross_section_max: float = 1.0e6,
    rated_voltage_kV: Optional[float] = None,
    voltage_tolerance_pct: float = 50.0,
    material: Optional[ConductorMaterial] = None,
    insulation: Optional[InsulationType] = None,
    min_ampacity_air_A: float = 0.0,
    min_icw_kA: float = 0.0,
) -> list[CatalogCable]:
    """
    Lista cabos compatíveis com filtros.

    Parameters
    ----------
    cross_section_min / cross_section_max:
        Range de bitola (mm²).
    rated_voltage_kV:
        Tensão de isolação alvo (filtra ±voltage_tolerance_pct).
    material:
        Cu ou Al.
    insulation:
        BARE/PVC/EPR/XLPE/HEPR.
    min_ampacity_air_A:
        Filtra cabos com ampacidade ≥ valor.
    min_icw_kA:
        Filtra cabos com ICW (1s) ≥ valor.
    """
    out = []
    for c in CABLE_CATALOG:
        if not (cross_section_min <= c.cross_section_mm2 <= cross_section_max):
            continue
        if rated_voltage_kV is not None:
            tol = max(0.5, rated_voltage_kV * voltage_tolerance_pct / 100.0)
            if abs(c.rated_voltage_kV - rated_voltage_kV) > tol:
                continue
        if material is not None and c.conductor_material != material:
            continue
        if insulation is not None and c.insulation != insulation:
            continue
        if min_ampacity_air_A > 0 and c.ampacity_air_A < min_ampacity_air_A:
            continue
        if min_icw_kA > 0 and c.icw_kA_1s < min_icw_kA:
            continue
        out.append(c)
    return out


def find_cable(
    *,
    cross_section_mm2: float,
    rated_voltage_kV: float,
    material: ConductorMaterial = ConductorMaterial.COPPER,
    insulation: Optional[InsulationType] = None,
) -> Optional[CatalogCable]:
    """
    Encontra o cabo mais próximo da bitola dada para a
    tensão+material+isolação escolhidos.
    """
    candidates = list_cables(
        rated_voltage_kV=rated_voltage_kV,
        material=material,
        insulation=insulation,
    )
    if not candidates:
        return None
    return min(
        candidates,
        key=lambda c: abs(c.cross_section_mm2 - cross_section_mm2),
    )


def find_cable_by_ampacity(
    *,
    required_ampacity_A: float,
    rated_voltage_kV: float,
    installation: InstallationType = InstallationType.AIR,
    material: ConductorMaterial = ConductorMaterial.COPPER,
    insulation: Optional[InsulationType] = None,
) -> Optional[CatalogCable]:
    """
    Encontra o MENOR cabo com ampacidade suficiente para a
    corrente de carga + método de instalação.

    Returns o cabo de menor bitola que atende ao critério;
    retorna None se nenhum candidato.
    """
    if installation == InstallationType.AIR:
        candidates = list_cables(
            rated_voltage_kV=rated_voltage_kV,
            material=material,
            insulation=insulation,
            min_ampacity_air_A=required_ampacity_A,
        )
    else:
        # Treat all "buried" methods using ampacity_buried_A
        candidates = [
            c for c in list_cables(
                rated_voltage_kV=rated_voltage_kV,
                material=material,
                insulation=insulation,
            )
            if c.ampacity_buried_A >= required_ampacity_A
        ]
    if not candidates:
        return None
    # Menor bitola entre os candidatos
    return min(candidates, key=lambda c: c.cross_section_mm2)


def cable_impedance_per_km_complex(
    cable: CatalogCable,
) -> complex:
    """
    Retorna Z = R_ac + jX em Ω/km (a 90°C, frequência 60 Hz).

    Útil para cálculo de queda de tensão e SC ao longo da linha.
    """
    return complex(cable.R_ac_ohm_per_km_at_90C, cable.X_ohm_per_km)


def cable_impedance_total_ohm(
    cable: CatalogCable, length_m: float,
) -> complex:
    """Z total (R+jX) em ohms para um trecho de length_m metros."""
    return cable_impedance_per_km_complex(cable) * (length_m / 1000.0)
