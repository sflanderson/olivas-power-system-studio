"""
app.preprocessor.templates — esquemáticos pré-prontos para
onboarding rápido (v0.89, topologia corrigida em v0.91.3).

Filosofia
==========

Um usuário novo abrindo o Olivas ATP Studio pela primeira vez
enfrentava um canvas vazio + necessidade de construir todo o
schema do zero (BUS, Vac, GND, conectar tudo) antes de ver
qualquer análise rodar.

Templates resolvem isso: um clique gera um esquemático
funcional que já roda análises completas. O usuário pode
**experimentar** antes de **construir**.

Cada template é uma função pura ``build_*() -> PpProject`` que
retorna um projeto novo. Todos usam coordenadas de scene em
múltiplos de 10 (grid v0.85).

Templates disponíveis
======================

1. **simple_13_8kV** — Sistema simples, 1 BUS lineside
   alimentado por concessionária 13.8 kV, swgr_15kv.

2. **industrial_480V** — Sistema industrial com feeder
   R+L (Thévenin equivalent) entre MT 13.8 kV e BT 480 V.

3. **dual_bus_substation** — Subestação dupla barra
   (2 alimentações, 2 BUSes paralelos via tie wire).

Convenções
============

* Coordenadas em grid 10 px (snap-aware).
* Layout vertical descendente: Vac topo → BUS meio → GND base.
* Wires conectam EXATAMENTE em pinos (não no corpo do BUS).
  - BUS pinos: (-80, ±25/0), (-30, ±25/0), (30, ±25/0), (80, ±25/0).
  - Vac/R/L/C: pinos em (0, ±30) — vertical 60px.
  - GND: pino em (0, 0) — anchor IS o pino.
  - Tr: 4 pinos em (±30, ±20).
* Convenção: BUS deslocado para que pino T2_B (ou T3_B) fique
  alinhado ao eixo principal (x=200). Permite wires verticais
  retas Vac → BUS → GND, mas com BUS visualmente off-center
  (~30px à direita).
* IDs de BUS descritivos.
* PpProperty.visible alinhado ao .ocomp.
"""

from __future__ import annotations

from app.preprocessor.models import (
    PpComponent, PpProject, PpProperty, PpWire,
)


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------


def _bus(
    bus_id: str, x: int, y: int,
    rated_kV: float = 13.8,
    panel_type: str = "swgr_15kv",
    is_lineside: bool = True,
) -> PpComponent:
    """Constrói um PpComponent BUS com props padrão NBR 17227."""
    return PpComponent(
        type="BUS", name=bus_id, visible=True,
        x=x, y=y, label_dx=15, label_dy=-26,
        mirror=0, rotation=0,
        properties=[
            PpProperty(bus_id, True),
            PpProperty(f"{rated_kV:g}", True),
            PpProperty("3", False),
            PpProperty(panel_type, True),
            PpProperty("1" if is_lineside else "0", True),
            PpProperty("0", True),       # has_AFD
            PpProperty("10", False),     # AFD_clearing_time_ms
            PpProperty("4", False),      # n_taps
            PpProperty("", False),       # description
        ],
    )


def _vac(
    name: str, x: int, y: int,
    voltage_V: float = 11270,    # 13.8 kV LL → ~11.27 kV LN peak
    freq_Hz: float = 60.0,
) -> PpComponent:
    """
    Constrói um PpComponent Vac (fonte AC).

    Convenção Qucs: tensão é em V (não kV).
    Para sistema 13.8 kV LL → V_LN_peak = 13800·√2/√3 ≈ 11270 V.
    """
    return PpComponent(
        type="Vac", name=name, visible=True,
        x=x, y=y, label_dx=15, label_dy=-26,
        mirror=0, rotation=0,
        properties=[
            PpProperty(f"{voltage_V:g} V", True),
            PpProperty(f"{freq_Hz:g} Hz", True),
            PpProperty("0", False),
            PpProperty("0", False),
        ],
    )


def _gnd(x: int, y: int) -> PpComponent:
    """GND (terra ideal)."""
    return PpComponent(
        type="GND", name="*", visible=True,
        x=x, y=y, label_dx=0, label_dy=0,
        mirror=0, rotation=0,
        properties=[],
    )


def _transformer(
    name: str, x: int, y: int,
    ratio: str = "1:1", magnetizing_mH: float = 1000.0,
) -> PpComponent:
    """Transformador ideal (Tr) — ratio + magnetizing inductance."""
    return PpComponent(
        type="Tr", name=name, visible=True,
        x=x, y=y, label_dx=15, label_dy=-26,
        mirror=0, rotation=0,
        properties=[
            PpProperty(ratio, True),
            PpProperty(f"{magnetizing_mH:g} mH", True),
        ],
    )


def _wire(x1: int, y1: int, x2: int, y2: int, label: str = "") -> PpWire:
    return PpWire(x1=x1, y1=y1, x2=x2, y2=y2, label=label)


# ---------------------------------------------------------------------------
# Template 1 — Sistema 13.8 kV simples
# ---------------------------------------------------------------------------


def build_simple_13_8kV() -> PpProject:
    """
    Sistema básico de 1 barra alimentada pela concessionária,
    com carga R representativa para simulação ATP runnable:

    ::

        Vac (UTIL-1, 13.8 kV)   anchor=(200,100), bottom=(200,130)
              │
              │ wire
              │
        BUS-MAIN-13.8           anchor=(230,200), T2_B=(200,200)
        ▶▶[BUS body]◀◀
              │
              │ wire
              │
        R_LOAD (carga de 100Ω)   anchor=(200,290), top=(200,260),
                                  bottom=(200,320)
              │
              │ wire
              │
        GND                      anchor=(200,380), pin=(200,380)

    v0.91.12: adicionado R_LOAD de 100Ω entre BUS e GND.
    Antes (v0.91.x): topologia Vac→BUS→GND era curto direto
    (degenerado para ATP — KILL 191 "no transients possible").
    Com a carga, ATP simula corrente de regime ~Vp/100Ω ≈
    113A, suficiente para gerar plot meaningful.

    Topologia corrigida em v0.91.3: BUS deslocado para
    ``x=230`` para que o pino ``T2_B`` fique em ``x=200``.
    """
    proj = PpProject(version="0.0.19")

    # Vac alinhado ao eixo x=200
    proj.components.append(
        _vac("UTIL-1", x=200, y=100, voltage_V=11270),
    )

    # BUS deslocado +30 para T2_B cair em x=200
    proj.components.append(
        _bus(
            "BUS-MAIN-13.8", x=230, y=200,
            rated_kV=13.8, panel_type="swgr_15kv", is_lineside=True,
        ),
    )

    # v0.91.12: R_LOAD entre BUS e GND (transforma em circuito
    # real, não mais curto direto). 100Ω é uma "carga"
    # típica para teste — usuário pode ajustar.
    proj.components.append(
        PpComponent(
            type="R", name="R_LOAD", visible=True,
            x=200, y=290, label_dx=15, label_dy=-26,
            mirror=0, rotation=0,
            properties=[
                PpProperty("100 Ohm", True),
                PpProperty("26.85", False),
                PpProperty("european", False),
            ],
        ),
    )

    # GND deslocado para baixo de R_LOAD
    proj.components.append(_gnd(x=200, y=380))

    # Wires verticalmente alinhados em x=200
    proj.wires.append(_wire(200, 130, 200, 200))   # Vac → BUS T2_B
    proj.wires.append(_wire(200, 200, 200, 260))   # BUS T2_B → R top
    proj.wires.append(_wire(200, 320, 200, 380))   # R bot → GND

    return proj


# ---------------------------------------------------------------------------
# Template 2 — Industrial 13.8 kV / 480 V
# ---------------------------------------------------------------------------


def build_industrial_480V() -> PpProject:
    """
    Sistema industrial alimentador-MT/BT com cabo de feeder
    (R + L como Thévenin equivalent do transformador + cabo):

    ::

        Vac (UTIL, 13.8 kV)        bottom pin (200, 100)
            │
        BUS-MV-13.8 (swgr_15kv, lineside)   T2_B (200, 190)
            │
        R_FEED (resistência do cabo + Tr)   pins (200, 260) / (200, 320)
            │
        L_FEED (indutância do cabo + Tr)    pins (200, 380) / (200, 440)
            │
        BUS-LV-480 (lv_swgr, loadside)      T2_B (200, 510)
            │
        GND                                  pin (200, 600)

    v0.91.3: substituiu o componente ``Tr`` por ``R_FEED + L_FEED``
    porque ``Tr`` tem pinos horizontais (±30, ±20) que não cabem
    bem em layout 1-line vertical sem rotação. R+L vertical com
    pinos (0, ±30) conectam diretamente.

    Útil para análise comparativa de arc-flash entre MT e BT
    (energia tipicamente maior em BT por Z menor + clearing
    mais lento).
    """
    proj = PpProject(version="0.0.19")

    # Vac MT
    proj.components.append(
        _vac("UTIL", x=200, y=70, voltage_V=11270),
    )

    # BUS MT lineside (deslocado +30 para T2_B cair em x=200)
    proj.components.append(
        _bus(
            "BUS-MV-13.8", x=230, y=190,
            rated_kV=13.8, panel_type="swgr_15kv",
            is_lineside=True,
        ),
    )

    # R_FEED — feeder resistance (cabo + perdas Tr)
    proj.components.append(
        PpComponent(
            type="R", name="R_FEED", visible=True,
            x=200, y=290, label_dx=15, label_dy=-26,
            mirror=0, rotation=0,
            properties=[
                PpProperty("0.5 Ohm", True),
                PpProperty("26.85", False),
                PpProperty("european", False),
            ],
        ),
    )
    # L_FEED — feeder inductance
    proj.components.append(
        PpComponent(
            type="L", name="L_FEED", visible=True,
            x=200, y=410, label_dx=15, label_dy=-26,
            mirror=0, rotation=0,
            properties=[
                PpProperty("5 mH", True),
                PpProperty("0", False),
                PpProperty("26.85", False),
            ],
        ),
    )

    # BUS BT loadside
    proj.components.append(
        _bus(
            "BUS-LV-480", x=230, y=510,
            rated_kV=0.480, panel_type="lv_swgr",
            is_lineside=False,
        ),
    )

    # GND
    proj.components.append(_gnd(x=200, y=600))

    # Wires — todos verticais em x=200, conectando pinos exatos
    proj.wires.append(_wire(200, 100, 200, 190))    # Vac.bot → BUS-MV T2_B
    proj.wires.append(_wire(200, 190, 200, 260))    # BUS-MV → R.top
    proj.wires.append(_wire(200, 320, 200, 380))    # R.bot → L.top
    proj.wires.append(_wire(200, 440, 200, 510))    # L.bot → BUS-LV T2_B
    proj.wires.append(_wire(200, 510, 200, 600))    # BUS-LV → GND

    return proj


# ---------------------------------------------------------------------------
# Template 3 — Subestação dupla barra
# ---------------------------------------------------------------------------


def build_dual_bus_substation() -> PpProject:
    """
    Subestação dupla barra com 2 alimentações independentes
    + tie wire entre os BUSes.

    ::

        Vac-A (130, 80)            Vac-B (370, 80)
            │                          │
        BUS-A (160, 200)        BUS-B (340, 200)
        ▶▶[BUS]◀◀──TIE──────────▶▶[BUS]◀◀
            │                          │
        GND-A (130, 290)          GND-B (370, 290)

    v0.91.3: BUSes deslocados ±30 para que ``T2_B`` de cada um
    fique alinhado com Vac/GND da respectiva coluna. Tie wire
    conecta ``T4_B`` de BUS-A (160+80, 200) = (240, 200) ao
    ``T1_B`` de BUS-B (340-80, 200) = (260, 200).
    """
    proj = PpProject(version="0.0.19")

    # Vac A (coluna x=130)
    proj.components.append(
        _vac("UTIL-A", x=130, y=80, voltage_V=11270),
    )
    # Vac B (coluna x=370)
    proj.components.append(
        _vac("UTIL-B", x=370, y=80, voltage_V=11270),
    )

    # BUS-A: anchor (160, 200) → T2_B em (130, 200)
    proj.components.append(
        _bus(
            "BUS-A", x=160, y=200,
            rated_kV=13.8, panel_type="swgr_15kv",
            is_lineside=True,
        ),
    )
    # BUS-B: anchor (340, 200) → T3_B em (370, 200)
    proj.components.append(
        _bus(
            "BUS-B", x=340, y=200,
            rated_kV=13.8, panel_type="swgr_15kv",
            is_lineside=True,
        ),
    )

    # GNDs (anchor=pino, coluna alinhada com Vac/BUS T2_B/T3_B)
    proj.components.append(_gnd(x=130, y=290))
    proj.components.append(_gnd(x=370, y=290))

    # Wires verticais Vac → BUS T2_B/T3_B → GND
    # Vac-A.bot (130, 110) → BUS-A.T2_B (130, 200)
    proj.wires.append(_wire(130, 110, 130, 200))
    # Vac-B.bot (370, 110) → BUS-B.T3_B (370, 200)
    proj.wires.append(_wire(370, 110, 370, 200))
    # BUS-A.T2_B (130, 200) → GND-A (130, 290)
    proj.wires.append(_wire(130, 200, 130, 290))
    # BUS-B.T3_B (370, 200) → GND-B (370, 290)
    proj.wires.append(_wire(370, 200, 370, 290))
    # TIE: BUS-A.T4_B (240, 200) → BUS-B.T1_B (260, 200)
    proj.wires.append(_wire(240, 200, 260, 200, label="TIE"))

    return proj


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


# Cada entry: (id, label_pt, description, builder).
# O ``id`` é estável para QSettings/preferences; ``label_pt`` é
# para a UI; ``description`` aparece no card.
TEMPLATES = [
    (
        "simple_13_8kV",
        "Sistema 13.8 kV simples",
        "1 BUS lineside alimentado por concessionária. "
        "Mínimo viável para SC + arc-flash.",
        build_simple_13_8kV,
    ),
    (
        "industrial_480V",
        "Industrial 13.8 kV → 480 V",
        "2 níveis de tensão com transformador. Compara "
        "arc-flash MT vs BT.",
        build_industrial_480V,
    ),
    (
        "dual_bus_substation",
        "Subestação dupla barra",
        "2 alimentações + 2 BUSes paralelos com tie. "
        "Coordenação redundante.",
        build_dual_bus_substation,
    ),
]


def get_template_builder(template_id: str):
    """
    Retorna a função builder para o ``template_id`` ou ``None``
    se não houver tal template.
    """
    for tid, _label, _desc, builder in TEMPLATES:
        if tid == template_id:
            return builder
    return None


def build_template(template_id: str) -> PpProject:
    """
    Conveniência: retorna ``PpProject`` construído pelo
    template. Levanta ``KeyError`` se o id não existe.
    """
    builder = get_template_builder(template_id)
    if builder is None:
        raise KeyError(f"Template {template_id!r} desconhecido.")
    return builder()
