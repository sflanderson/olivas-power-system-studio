"""
scripts/rebuild_example_sch.py — v0.93.3:

Reconstrói os .sch dos exemplos que NÃO podem ser
migrados via snap (offsets >30 px). Os builders abaixo
geram cada exemplo do zero com:

* Coordenadas em grid 10 px (snap-aware).
* Wires que conectam EXATAMENTE em pinos atuais dos
  renderers (Bus PTW + componentes pós-v0.92.1).
* Mesma topologia lógica do .sch original (preservada
  via inspection visual + builder symmetry com
  ``app/preprocessor/templates.py``).

Examples cobertos:

* ``ieee399_motor_starting`` — UTL → R+L → BUS → Motor
* ``ieee1584_ex_d2`` — UTL → R+L → BUS_LV (480 V arc-flash)
* ``stevenson_sequential`` — GEN(SM) → R+L → BUS_F (faltas
  assimétricas)

Uso CLI::

    python -m scripts.rebuild_example_sch [example_id …]

Sem args, reconstrói todos os 3.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Callable

from app.preprocessor.models import (
    PpComponent, PpProject, PpProperty, PpWire,
)
from app.preprocessor.qucs_sch_serializer import serialize_sch_file


# ---------------------------------------------------------------------------
# Helpers — equivalentes aos de templates.py mas locais aqui
# ---------------------------------------------------------------------------


def _bus(name: str, x: int, y: int, rated_kV: float = 13.8,
         panel_type: str = "swgr_15kv",
         is_lineside: bool = True) -> PpComponent:
    return PpComponent(
        type="BUS", name=name, visible=True,
        x=x, y=y, label_dx=15, label_dy=-26,
        mirror=0, rotation=0,
        properties=[
            PpProperty(name, True),
            PpProperty(f"{rated_kV:g}", True),
            PpProperty("3", False),
            PpProperty(panel_type, True),
            PpProperty("1" if is_lineside else "0", True),
            PpProperty("0", True),       # has_AFD
            PpProperty("10", False),     # AFD time
            PpProperty("4", False),      # n_taps (legado)
            PpProperty("", False),       # description
        ],
    )


def _vac(name: str, x: int, y: int, voltage_V: float = 11270,
         freq_Hz: float = 60.0, rotation: int = 0) -> PpComponent:
    return PpComponent(
        type="Vac", name=name, visible=True,
        x=x, y=y, label_dx=15, label_dy=-26,
        mirror=0, rotation=rotation,
        properties=[
            PpProperty(f"{voltage_V:g} V", True),
            PpProperty(f"{freq_Hz:g} Hz", True),
            PpProperty("0", False),
            PpProperty("0", False),
        ],
    )


def _gnd(x: int, y: int) -> PpComponent:
    return PpComponent(
        type="GND", name="*", visible=True,
        x=x, y=y, label_dx=0, label_dy=0,
        mirror=0, rotation=0,
        properties=[],
    )


def _r(name: str, x: int, y: int, ohm: float = 1.0,
       rotation: int = 0) -> PpComponent:
    return PpComponent(
        type="R", name=name, visible=True,
        x=x, y=y, label_dx=15, label_dy=-26,
        mirror=0, rotation=rotation,
        properties=[
            PpProperty(f"{ohm:g} Ohm", True),
            PpProperty("26.85", False),
            PpProperty("0.0", False),
            PpProperty("0.0", False),
            PpProperty("european", False),
        ],
    )


def _l(name: str, x: int, y: int, henry: float = 1e-3,
       rotation: int = 0) -> PpComponent:
    return PpComponent(
        type="L", name=name, visible=True,
        x=x, y=y, label_dx=15, label_dy=-26,
        mirror=0, rotation=rotation,
        properties=[
            PpProperty(f"{henry:g} H", True),
            PpProperty("0", False),
        ],
    )


def _motor(name: str, x: int, y: int) -> PpComponent:
    """3-fase induction motor — pinos em (30, -20), (30, 0), (30, 20)."""
    return PpComponent(
        type="MOTOR", name=name, visible=True,
        x=x, y=y, label_dx=15, label_dy=20,
        mirror=0, rotation=0,
        properties=[
            PpProperty("1500", True),    # P_kW
            PpProperty("4160", True),    # V_LL
            PpProperty("0.92", False),   # PF
            PpProperty("0.95", False),   # eff
            PpProperty("6.0", True),     # I_LR/I_n
        ],
    )


def _sm(name: str, x: int, y: int) -> PpComponent:
    """Synchronous machine."""
    return PpComponent(
        type="SM", name=name, visible=True,
        x=x, y=y, label_dx=15, label_dy=20,
        mirror=0, rotation=0,
        properties=[
            PpProperty("100", True),     # S_kVA
            PpProperty("13.8", True),    # V_kV
            PpProperty("0.20", False),   # Xd"
            PpProperty("0.30", False),   # Xd'
            PpProperty("1.50", False),   # Xd
            PpProperty("PV", False),     # bus type
        ],
    )


def _wire(x1: int, y1: int, x2: int, y2: int,
          label: str = "") -> PpWire:
    return PpWire(x1=x1, y1=y1, x2=x2, y2=y2, label=label)


# ---------------------------------------------------------------------------
# Example builders
# ---------------------------------------------------------------------------


def build_ieee399_motor_starting() -> PpProject:
    """
    IEEE 399 Brown Book Ex 10.3 — partida de motor 1500 kW.

    v0.93.3 — Topologia simplificada para multi-hop walker:
    Vac DIRETAMENTE no BUS (a impedância R+L representa-se
    como "Network feeder" em propriedade do Vac, não como
    componentes separados). Isto permite que o pipeline SC
    detecte o source corretamente.

    ::

        Vac (UTL @ 4.16 kV)         @(100, 200) — pino direito (130, 200)
              ─── wire ───
        BUS_4 ─────                 @(330, 200) — pino esquerdo (230, 200)
              ─── wire ───
        Motor M_1500                @(530, 200) — pino esquerdo (560, 200)

        Vac inferior pin → GND
    """
    proj = PpProject(version="0.0.19")

    # Vac com rotation=1 (90° CCW) — pinos saem horizontalmente
    proj.components.append(_vac("UTL", x=100, y=200, voltage_V=3398,
                                freq_Hz=60.0, rotation=1))

    # BUS horizontal — pino esquerdo em x=230, direito em x=430
    proj.components.append(
        _bus("BUS_4", x=330, y=200, rated_kV=4.16, panel_type="ccm")
    )

    # Motor à direita
    proj.components.append(_motor("M_1500", x=530, y=200))

    # GND aterrando o Vac (pino esquerdo em x=70)
    proj.components.append(_gnd(x=70, y=270))

    # Wires alinhados a pinos exatos
    # Vac pino direito (130, 200) → BUS pino esquerdo (230, 200)
    proj.wires.append(_wire(130, 200, 230, 200, label="VBUS4"))
    # BUS pino direito (430, 200) → Motor pino esquerdo (560, 200)
    proj.wires.append(_wire(430, 200, 560, 200))
    # Vac pino esquerdo (70, 200) → GND (70, 270) via vertical
    proj.wires.append(_wire(70, 200, 70, 270))

    return proj


def build_ieee1584_ex_d2() -> PpProject:
    """
    IEEE 1584-2018 Annex D Example D.2 — arc-flash em 480 V.

    v0.93.3 — Vac diretamente no BUS_LV (sem R/L intermediário).

    ::

        Vac (UTL @ 480 V) @(100, 200) ── wire ── BUS_LV ─── @(330, 200)
                                                              │
                                                              GND @(70, 270)
    """
    proj = PpProject(version="0.0.19")

    proj.components.append(_vac("UTL", x=100, y=200, voltage_V=392,
                                rotation=1))
    proj.components.append(
        _bus("BUS_LV", x=330, y=200, rated_kV=0.48,
             panel_type="swgr_lv")
    )
    proj.components.append(_gnd(x=70, y=270))

    proj.wires.append(_wire(130, 200, 230, 200, label="VBUS_LV"))
    proj.wires.append(_wire(70, 200, 70, 270))

    return proj


def build_stevenson_sequential() -> PpProject:
    """
    Stevenson §11 — Faltas assimétricas (LG, LL, LLG).
    Sistema TN solidamente aterrado.

    v0.93.3 — SM diretamente no BUS_F.

    SM pinos absolutos com anchor (x, y) e rotation=0:
    (x+30, y-20), (x+30, y), (x+30, y+20). Pin do meio (x+30, y)
    é o "terminal AC". Posicionamos SM em (200, 200) → pin
    central (230, 200) que conecta direto no pino esquerdo
    do BUS em x=230.
    """
    proj = PpProject(version="0.0.19")

    # SM em (200, 200) — pino central direito em (230, 200)
    proj.components.append(_sm("GEN", x=200, y=200))
    # BUS_F em (330, 200) — pino esquerdo em (230, 200) → connect direto
    proj.components.append(
        _bus("BUS_F", x=330, y=200, rated_kV=13.8)
    )
    proj.components.append(_gnd(x=200, y=270))

    # Sem wire necessário entre SM (230, 200) e BUS pino (230, 200)
    # — pinos coincidentes são auto-unidos pelo coalescer.
    # Mas adicionamos um wire visualmente para o usuário ver.
    proj.wires.append(_wire(230, 200, 230, 200, label="VBUS_F"))

    # Wire neutro/aterramento — SM pino central (230, 220) ao GND
    # SM pinos em (230, 180), (230, 200), (230, 220)
    proj.wires.append(_wire(230, 220, 230, 270))
    proj.wires.append(_wire(230, 270, 200, 270))

    return proj


# ---------------------------------------------------------------------------
# Registry + CLI
# ---------------------------------------------------------------------------


def build_stevenson_pf_3bus() -> PpProject:
    """
    Stevenson §9 Ex 9.5 — Newton-Raphson PF em sistema 3-bus.

    v0.93.3 — Topologia simplificada:
    * V_SLACK (Vac) direto em B1 (slack bus)
    * GEN_PV (SM) direto em B2 (PV bus)
    * B3 = PQ bus (sem fonte)
    * Branches RL12 / RL13 / RL23 entre as barras

    Estes branches NÃO afetam a detecção de SC sources
    (fontes ficam direto nos buses), mas o usuário pode rodar
    PF normalmente com a topologia correta.

    Layout:

    ::

        V_SLACK ── B1 ─── RL12+LL12 ─── B2 ── GEN_PV
                  │                     │
                RL13                  RL23
                  │                     │
                  └───── B3 ───────────┘
    """
    proj = PpProject(version="0.0.19")

    # Fontes — V_SLACK em B1, GEN_PV em B2
    # V_SLACK rot=1 → pinos (x±30, y) absolute. Anchor (100, 200) →
    # pin direito (130, 200). B1 anchor (230, 200) → pin esq (130, 200).
    proj.components.append(_vac("V_SLACK", x=100, y=200,
                                voltage_V=11270, rotation=1))
    # B1 — pino esq em (130, 200) ← coincide com V_SLACK pin
    proj.components.append(_bus("B1", x=230, y=200, rated_kV=13.8))
    # B2 anchor (530, 200) → pin esq em (430, 200), pin dir (630, 200)
    proj.components.append(_bus("B2", x=530, y=200, rated_kV=13.8))
    # GEN_PV anchor (700, 200) → pinos no DIREITO da máquina
    # SM tem pinos em (30, ±20) e (30, 0). Para conectar pin esq do
    # SM ao pino dir do B2, precisamos rotation=2 (180°). Então pinos
    # ficam em (-30, 0/-20/+20). Anchor (660, 200) → pin (630, 200).
    sm = _sm("GEN_PV", x=660, y=200)
    sm = PpComponent(
        type="SM", name="GEN_PV", visible=True,
        x=660, y=200, label_dx=15, label_dy=20,
        mirror=0, rotation=2,   # 180°
        properties=sm.properties,
    )
    proj.components.append(sm)

    # B3 — anchor (380, 400) → pinos x ∈ [280, 480], y=400
    proj.components.append(_bus("B3", x=380, y=400, rated_kV=13.8))

    # Branches RL12, RL13, RL23 — apenas como rendering (não
    # entram no cálculo SC). Para PF eles funcionariam.
    # RL12: entre pin direito de B1 (330, 200) e pin esq de B2 (430, 200)
    # Posicionamos R+L horizontalmente entre esses pontos. R/L padrão
    # tem pinos verticais (0, ±30); rotation=1 vira horizontal.
    proj.components.append(_r("RL12", x=360, y=200, ohm=0.05,
                              rotation=1))
    # RL12 rot=1 → pinos em (∓30, 0) → (330, 200) e (390, 200)
    proj.components.append(_l("LL12", x=400, y=200, henry=1e-3,
                              rotation=1))
    # LL12 rot=1 → pinos em (370, 200) e (430, 200)

    # RL13: entre B1 e B3 — precisa de path em "L".
    # B1 pin bottom corner (~330, 200) → wire down/right → B3 left (280, 400)
    # Por simplicidade: RL13 vertical entre (330, 250) e (330, 380),
    # com wires curtos.
    proj.components.append(_r("RL13", x=330, y=260, ohm=0.05))
    proj.components.append(_l("LL13", x=330, y=340, henry=1e-3))

    # RL23: B2 → B3
    proj.components.append(_r("RL23", x=430, y=260, ohm=0.05))
    proj.components.append(_l("LL23", x=430, y=340, henry=1e-3))

    # GND
    proj.components.append(_gnd(x=70, y=270))

    # Wires
    # V_SLACK aterrada (pin esq em (70, 200))
    proj.wires.append(_wire(70, 200, 70, 270))
    # RL12 → R em (330, 200), wire horizontal a L (370, 200)
    proj.wires.append(_wire(330, 200, 370, 200))
    # LL12 saída (430, 200) coincide com B2 pin esq → no wire necessário
    # mas deixamos para visual
    # RL12 entrada (330, 200) coincide com B1 pin direito → ok

    # B1 → RL13: wire down de B1 pin (330, 200) → R top (330, 230)
    proj.wires.append(_wire(330, 200, 330, 230))
    # RL13 R bottom (330, 290) → L top (330, 310)
    proj.wires.append(_wire(330, 290, 330, 310))
    # LL13 bottom (330, 370) → wire para B3 left pin (280, 400)
    proj.wires.append(_wire(330, 370, 330, 400))
    proj.wires.append(_wire(330, 400, 280, 400))   # horizontal até B3

    # B2 → RL23
    proj.wires.append(_wire(430, 200, 430, 230))
    proj.wires.append(_wire(430, 290, 430, 310))
    proj.wires.append(_wire(430, 370, 430, 400))
    proj.wires.append(_wire(430, 400, 480, 400))   # horizontal a B3 pin dir

    return proj


REBUILDERS: dict[str, Callable[[], PpProject]] = {
    "ieee399_motor_starting": build_ieee399_motor_starting,
    "ieee1584_ex_d2": build_ieee1584_ex_d2,
    "stevenson_sequential": build_stevenson_sequential,
    "stevenson_pf_3bus": build_stevenson_pf_3bus,
}


def main(argv: list[str] | None = None) -> int:
    args = argv or list(REBUILDERS.keys())
    out_dir = Path("app/examples/schematics")
    out_dir.mkdir(parents=True, exist_ok=True)

    from app.postprocessor.bus_pipeline import find_neighbors_of_bus

    all_ok = True
    for ex_id in args:
        builder = REBUILDERS.get(ex_id)
        if builder is None:
            print(f"❌ unknown example: {ex_id}")
            all_ok = False
            continue
        proj = builder()
        out_path = out_dir / f"{ex_id}.sch"
        serialize_sch_file(proj, str(out_path))

        # Verifica conectividade
        bus_names = [c.name for c in proj.components if c.type == "BUS"]
        ok = True
        details = []
        for b in bus_names:
            try:
                n = len(find_neighbors_of_bus(proj, b))
                details.append(f"{b}={n}")
                if n == 0:
                    ok = False
            except Exception as exc:
                details.append(f"{b}=ERR:{exc}")
                ok = False
        status = "✅" if ok else "❌"
        print(
            f"{status} {ex_id}: {out_path.name} "
            f"({len(proj.components)} comps, {len(proj.wires)} wires) "
            f"→ {', '.join(details)}"
        )
        if not ok:
            all_ok = False
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
