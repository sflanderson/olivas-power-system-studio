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
    # Proveniência (entradas digitalizadas de datasheet oficial).
    # Vazio = valor representativo genérico (entradas legadas v0.43).
    manufacturer: str = ""
    source: str = ""


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


# ---------------------------------------------------------------------------
# Catálogo: Induscabos INDULINK 3,6/6 kV — parâmetros elétricos oficiais
# Fonte: Induscabos, "Parâmetros Elétricos — Cabos de Média Tensão"
# (sem data/revisão no texto do documento). Cu, 90 °C, 60 Hz, NBR 14039.
# Colunas usadas: RCC 20 °C, RCA 90 °C (3 cond., S=D), Xl trifólio, C,
# I ao ar (trifólio, 30 °C), I enterrado (trifólio, 25 °C). Xl para S=D
# e S=2D em ``notes``. Tabela transcrita: "CABO INDULINK 3,6/6 kV" (a
# tabela 6/10 kV do mesmo documento tem Xl/C distintos e NÃO foi
# transcrita). Isolação não declarada (só "90 °C"): XLPE assumido.
# icw = 0.143·S (K=143 Cu, convenção deste módulo; não consta na fonte).
# ---------------------------------------------------------------------------

_INDUSCABOS_SRC = "Induscabos — Parâmetros Elétricos Cabos MT, tabela INDULINK 3,6/6 kV"


def _induscabos(
    s: float, rdc20: float, rac90: float, x_tri: float, c: float,
    i_air: float, i_bur: float, x_sd: float, x_s2d: float,
) -> CatalogCable:
    return CatalogCable(
        name=f"Induscabos INDULINK Cu {s:g}mm² 3.6/6kV",
        conductor_material=ConductorMaterial.COPPER,
        insulation=InsulationType.XLPE,
        rated_voltage_kV=6.0, cross_section_mm2=s,
        R_dc_ohm_per_km_at_20C=rdc20, R_ac_ohm_per_km_at_90C=rac90,
        X_ohm_per_km=x_tri, C_uF_per_km=c,
        ampacity_air_A=i_air, ampacity_buried_A=i_bur,
        icw_kA_1s=round(0.143 * s, 3),
        notes=(
            f"Xl S=D {x_sd} Ω/km; Xl S=2D {x_s2d} Ω/km (trifólio em X). "
            "Isolação assumida XLPE (tabela só informa 90 °C)."
        ),
        manufacturer="Induscabos", source=_INDUSCABOS_SRC,
    )


_INDUSCABOS_INDULINK_6kV: tuple[CatalogCable, ...] = (
    _induscabos(10, 1.830, 2.33350, 0.17615, 0.2004, 87, 65, 0.19355, 0.24575),
    _induscabos(16, 1.150, 1.46648, 0.16331, 0.2291, 114, 84, 0.18071, 0.23292),
    _induscabos(25, 0.727, 0.92719, 0.15184, 0.2634, 150, 107, 0.16924, 0.22145),
    _induscabos(35, 0.524, 0.66844, 0.14375, 0.2946, 183, 128, 0.16115, 0.21335),
    _induscabos(50, 0.387, 0.49389, 0.13668, 0.3285, 221, 150, 0.15409, 0.20629),
    _induscabos(70, 0.268, 0.34239, 0.13051, 0.3651, 275, 183, 0.14791, 0.20011),
    _induscabos(95, 0.193, 0.24708, 0.12471, 0.4128, 337, 218, 0.14211, 0.19431),
    _induscabos(120, 0.153, 0.19640, 0.12097, 0.4520, 390, 247, 0.13837, 0.19057),
    _induscabos(150, 0.124, 0.15980, 0.11800, 0.4828, 445, 276, 0.13540, 0.18761),
    _induscabos(185, 0.0991, 0.12857, 0.11462, 0.5303, 510, 311, 0.13202, 0.18422),
    _induscabos(240, 0.0754, 0.09923, 0.10970, 0.5902, 602, 358, 0.12711, 0.17931),
    _induscabos(300, 0.0601, 0.08055, 0.10791, 0.6050, 687, 402, 0.12531, 0.17751),
    _induscabos(400, 0.0470, 0.06492, 0.10596, 0.6340, 796, 453, 0.12337, 0.17557),
    _induscabos(500, 0.0366, 0.05298, 0.10373, 0.6660, 907, 506, 0.12113, 0.17333),
)


# ---------------------------------------------------------------------------
# Catálogo: Nexans (NZ/AU) TR-XLPE 6.35/11 (12) kV unipolar Cu, tela de fios
# Fonte: Nexans "Medium Voltage TR-XLPE Cables, Section Four", Product
# Sheet 231-13 B, Issue June 2019 (AS/NZS 1429.1, 50 Hz). R_ac a 90 °C,
# X_L a 50 Hz, C condutor-tela (cabeçalho impresso "µF/km"). Correntes
# (ícones da folha, decodificados na página renderizada): 1ª coluna =
# ao ar (30 °C), 2ª = trifólio diretamente enterrado, 3ª = em duto
# (solo 15 °C, 1.2 K·m/W, 1.0 m, telas aterradas nas duas pontas).
# R_dc 20 °C NÃO consta na folha: valor nominal IEC 60228 classe 2
# (coincide com Prysmian Tab. 18 e Induscabos para as seções comuns;
# 630 mm² sem corroboração nas fontes digitalizadas). X a 50 Hz: em
# sistemas 60 Hz escalar ×1.2. icw = 0.143·S (convenção do módulo; a
# folha só dá a fórmula da tela, Isc = 148.6·S_tela/√t).
# ---------------------------------------------------------------------------

_NEXANS_SRC = "Nexans NZ — MV TR-XLPE Cables Section Four, sheet 231-13 B (11 kV Cu), Jun/2019"


def _nexans(s: float, rdc20_iec: float, rac90: float, x: float, c: float,
            i_air: float, i_bur: float, i_duct: float) -> CatalogCable:
    return CatalogCable(
        name=f"Nexans TR-XLPE Cu {s:g}mm² 6.35/11kV",
        conductor_material=ConductorMaterial.COPPER,
        insulation=InsulationType.XLPE,
        rated_voltage_kV=11.0, cross_section_mm2=s,
        R_dc_ohm_per_km_at_20C=rdc20_iec, R_ac_ohm_per_km_at_90C=rac90,
        X_ohm_per_km=x, C_uF_per_km=c,
        ampacity_air_A=i_air, ampacity_buried_A=i_bur,
        icw_kA_1s=round(0.143 * s, 3),
        notes=(
            f"50 Hz (X ×1.2 em 60 Hz). Em duto: {i_duct:g} A. "
            "R_dc = IEC 60228 cl. 2 (não consta na folha Nexans)."
        ),
        manufacturer="Nexans", source=_NEXANS_SRC,
    )


_NEXANS_TRXLPE_11kV: tuple[CatalogCable, ...] = (
    _nexans(16, 1.15, 1.47, 0.154, 0.18, 125, 120, 101),
    _nexans(25, 0.727, 0.927, 0.144, 0.21, 163, 154, 129),
    _nexans(35, 0.524, 0.668, 0.137, 0.23, 197, 183, 153),
    _nexans(50, 0.387, 0.494, 0.130, 0.26, 237, 216, 181),
    _nexans(70, 0.268, 0.342, 0.121, 0.29, 294, 263, 221),
    _nexans(95, 0.193, 0.247, 0.115, 0.33, 359, 313, 264),
    _nexans(120, 0.153, 0.196, 0.111, 0.36, 413, 355, 305),
    _nexans(150, 0.124, 0.159, 0.107, 0.39, 470, 397, 341),
    _nexans(185, 0.0991, 0.128, 0.103, 0.43, 539, 447, 384),
    _nexans(240, 0.0754, 0.0981, 0.099, 0.47, 636, 516, 443),
    _nexans(300, 0.0601, 0.0791, 0.096, 0.52, 730, 579, 509),
    _nexans(400, 0.0470, 0.0632, 0.093, 0.59, 847, 655, 575),
    _nexans(500, 0.0366, 0.0510, 0.090, 0.66, 978, 737, 647),
    _nexans(630, 0.0283, 0.0416, 0.087, 0.74, 1122, 823, 722),
)


# ---------------------------------------------------------------------------
# Catálogo: Prysmian Eprotenax Compact 105 3,6/6 kV unipolar Cu, HEPR 105 °C
# Fonte: Prysmian "Média Tensão — Uso Geral", capítulos "Parâmetros
# Elétricos" (Rcc 20 °C IEC/NBR NM 280 cl. 2; Rca e X_L a 105 °C/60 Hz,
# arranjo trifólio; Xc condutor-blindagem) e "Capacidade de Condução de
# Corrente" (NBR 14039 Tab. 30 — ar livre 30 °C / diretamente enterrado
# 20 °C, ρ_solo=2,5 K·m/W, 3 cabos unipolares em trifólio). C_uF_per_km
# derivado de Xc (Ω·km) por C=1/(2π·60·Xc) — não impresso diretamente.
# icw usa K=134 (seção "Correntes de Curto-Circuito no Condutor", Cu,
# conexões prensadas, T1=105°C→T2=250°C — específico deste produto, não
# o K=143/142 genérico usado nas demais entradas do módulo, calibrado
# para T1=90°C). Isolação HEPR 105 °C (Eprotenax Compact 105 — nome
# comercial Prysmian; a classificação HEPR não aparece literalmente
# neste documento, mas é a isolação padrão da linha): Rca/ampacidade/icw
# em referência de temperatura MAIS ALTA que as demais entradas do
# catálogo (XLPE 90 °C).
# ---------------------------------------------------------------------------

_PRYSMIAN_SRC = "Prysmian — Média Tensão Uso Geral, EPROTENAX COMPACT 105 3,6/6 kV"


def _prysmian(s: float, rcc20: float, rac105: float, x_tri: float,
              c_uf_km: float, i_air: float, i_bur: float) -> CatalogCable:
    return CatalogCable(
        name=f"Prysmian Eprotenax Compact 105 Cu {s:g}mm² 3.6/6kV",
        conductor_material=ConductorMaterial.COPPER,
        insulation=InsulationType.HEPR,
        rated_voltage_kV=6.0, cross_section_mm2=s,
        R_dc_ohm_per_km_at_20C=rcc20, R_ac_ohm_per_km_at_90C=rac105,
        X_ohm_per_km=x_tri, C_uF_per_km=round(c_uf_km, 4),
        ampacity_air_A=i_air, ampacity_buried_A=i_bur,
        # K=134 (Cu, conexões prensadas, T1=105°C→T2=250°C) — NÃO o K=143
        # genérico do módulo (que é o K=142 de T1=90°C arredondado); a
        # fonte publica a tabela específica para este produto de 105 °C.
        icw_kA_1s=round(0.134 * s, 3),
        notes=(
            "R_ac, ampacidade e I²t (K=134, não o K=143/142 genérico do "
            "módulo) referenciados a 105 °C (isolação HEPR — Eprotenax "
            "Compact 105; classificação HEPR de catálogo comercial "
            "Prysmian, não impressa literalmente neste documento), não "
            "90 °C como as demais entradas do catálogo — não comparar R_ac "
            "nem icw diretamente entre fabricantes sem ajustar a "
            "temperatura de referência. Arranjo trifólio (3 cabos "
            "unipolares). Ampacidade ao ar: 30 °C ambiente, bandeja. "
            "Ampacidade enterrada: NBR 14039 Tab. 30, 20 °C ambiente, "
            "ρ_solo=2,5 K·m/W (coluna a, a mais conservadora). "
            "C_uF_per_km calculado de Xc (não impresso na fonte)."
        ),
        manufacturer="Prysmian", source=_PRYSMIAN_SRC,
    )


_PRYSMIAN_EPROTENAX_6kV: tuple[CatalogCable, ...] = (
    _prysmian(10, 1.830, 2.443, 0.178, 0.2335, 97, 70),
    _prysmian(16, 1.150, 1.536, 0.165, 0.2646, 127, 90),
    _prysmian(25, 0.727, 0.971, 0.154, 0.3024, 167, 115),
    _prysmian(35, 0.524, 0.701, 0.145, 0.3399, 204, 137),
    _prysmian(50, 0.387, 0.518, 0.137, 0.3840, 246, 162),
    _prysmian(70, 0.268, 0.359, 0.130, 0.4313, 307, 197),
    _prysmian(95, 0.193, 0.260, 0.125, 0.4852, 376, 235),
    _prysmian(120, 0.153, 0.207, 0.120, 0.5323, 435, 266),
    _prysmian(150, 0.124, 0.168, 0.117, 0.5793, 496, 298),
    _prysmian(185, 0.099, 0.135, 0.114, 0.6296, 568, 335),
    _prysmian(240, 0.075, 0.105, 0.111, 0.6363, 672, 387),
    _prysmian(300, 0.060, 0.085, 0.109, 0.6960, 767, 434),
    _prysmian(400, 0.047, 0.069, 0.105, 0.7888, 890, 490),
    _prysmian(500, 0.037, 0.056, 0.102, 0.8663, 1015, 548),
)


# Catálogo total
CABLE_CATALOG: tuple[CatalogCable, ...] = (
    _CU_PVC_LV + _CU_EPR_15kV + _CU_XLPE_20kV + _CU_BARE
    + _INDUSCABOS_INDULINK_6kV + _NEXANS_TRXLPE_11kV
    + _PRYSMIAN_EPROTENAX_6kV
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
