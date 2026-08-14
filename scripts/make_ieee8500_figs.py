"""Gera as figuras do módulo de fluxo desbalanceado a partir do
dataset oficial IEEE 8500-Node Test Feeder."""
from __future__ import annotations

import cmath
import json
import math
import os
import pathlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.collections import LineCollection
from matplotlib.colors import LinearSegmentedColormap, Normalize

# --- design tokens do Catálogo Técnico Olivas PSS ------------------------
INK = "#243018"
ACCENT = "#4D9A2E"
BODY = "#5A6157"
BORDER = "#D8DDD4"
CARD = "#FBFCFA"
PH = {1: "#4D9A2E", 2: "#C8811A", 3: "#2E6F9A"}
PHNAME = {1: "Fase A", 2: "Fase B", 3: "Fase C"}

plt.rcParams.update({
    "font.family": "Liberation Sans",
    "font.size": 9,
    "axes.edgecolor": BORDER,
    "axes.labelcolor": INK,
    "text.color": INK,
    "xtick.color": BODY,
    "ytick.color": BODY,
    "axes.facecolor": "white",
    "figure.facecolor": "white",
    "axes.grid": True,
    "grid.color": BORDER,
    "grid.linewidth": 0.6,
    "grid.alpha": 0.9,
    "legend.frameon": False,
})

FEEDER = pathlib.Path(__file__).parent / "ieee8500"
OUT = pathlib.Path(os.environ.get("FIG_OUT", "figs"))
OUT.mkdir(parents=True, exist_ok=True)

A = cmath.exp(2j * math.pi / 3)


def solve(master: str, mult: float | None = None):
    from dss import DSS
    DSS.Text.Command = "Clear"
    DSS.Text.Command = f'Redirect "{FEEDER / master}"'
    # O master oficial não define EnergyMeter; sem ele o OpenDSS não
    # calcula a distância elétrica de cada barra à subestação.
    DSS.Text.Command = (
        "New EnergyMeter.sub element=Line.HVMV_Sub_connector terminal=1"
    )
    for c in ("set maxiterations=300", "set maxcontroliter=200",
              "set tolerance=1e-8"):
        DSS.Text.Command = c
    if mult is not None:
        DSS.Text.Command = f"set loadmult={mult}"
    DSS.ActiveCircuit.Solution.Solve()
    return DSS.ActiveCircuit


def bus_table(ck):
    """Coleta tensões, coordenadas e distância de todas as barras."""
    out = {}
    for bn in ck.AllBusNames:
        ck.SetActiveBus(bn)
        b = ck.ActiveBus
        va = list(b.puVmagAngle)
        out[bn.lower()] = {
            "x": float(b.x), "y": float(b.y),
            "coord": bool(b.Coorddefined),
            "dist": float(b.Distance),
            "kv": float(b.kVBase),
            "nodes": [int(n) for n in b.Nodes],
            "vpu": [float(va[k]) for k in range(0, len(va), 2)],
            "ang": [float(va[k]) for k in range(1, len(va), 2)],
        }
    return out


def vuf_nema(vpu, ang):
    """VUF (IEC 61000-3-13, |V2|/|V1|) e desbalanço NEMA MG-1."""
    V = [vpu[k] * cmath.exp(1j * math.radians(ang[k])) for k in range(3)]
    V1 = (V[0] + A * V[1] + A * A * V[2]) / 3.0
    V2 = (V[0] + A * A * V[1] + A * V[2]) / 3.0
    vuf = 100.0 * abs(V2) / abs(V1) if abs(V1) > 1e-9 else 0.0
    m = sum(vpu[:3]) / 3.0
    nema = 100.0 * max(abs(v - m) for v in vpu[:3]) / m if m > 0 else 0.0
    return vuf, nema


def halo(artist, lw=2.6):
    """Contorno branco: mantém rótulos legíveis sobre a malha."""
    import matplotlib.patheffects as pe
    artist.set_path_effects(
        [pe.withStroke(linewidth=lw, foreground="white")]
    )
    return artist


def footer(fig, text):
    fig.text(0.995, 0.006, text, ha="right", va="bottom",
             fontsize=6.5, color="#8E968F")


# =======================================================================
print("· resolvendo caso desbalanceado…")
ck = solve("Master-unbal.dss")
assert ck.Solution.Converged, "não convergiu"
buses = bus_table(ck)
nnodes = len(ck.AllNodeNames)
total_kw, total_kvar = (-ck.TotalPower[0], -ck.TotalPower[1])
loss_kw = ck.Losses[0] / 1000.0
print(f"  nós de fase={nnodes} P={total_kw:.1f} kW perdas={loss_kw:.1f} kW")

segs = []
L = ck.Lines
i = L.First
while i:
    b1 = L.Bus1.split(".")[0].lower()
    b2 = L.Bus2.split(".")[0].lower()
    d1, d2 = buses.get(b1), buses.get(b2)
    if d1 and d2 and d1["coord"] and d2["coord"]:
        v = [x for x in d2["vpu"] if x > 0.1] or [1.0]
        segs.append(((d1["x"], d1["y"]), (d2["x"], d2["y"]),
                     sum(v) / len(v), int(L.Phases)))
    i = L.Next
print(f"  segmentos georreferenciados={len(segs)}")

# =======================================================================
# FIGURA 1 — mapa geográfico colorido por tensão
# =======================================================================
cmap = LinearSegmentedColormap.from_list("olivas_v", [
    (0.00, "#B3261E"), (0.35, "#D68A1E"),
    (0.55, "#4D9A2E"), (0.80, "#2E8B8B"), (1.00, "#2E6F9A"),
])
norm = Normalize(vmin=0.92, vmax=1.06)

fig, ax = plt.subplots(figsize=(7.4, 4.6), dpi=300)
lc = LineCollection(
    [(a, b) for a, b, _, _ in segs],
    linewidths=[1.35 if p == 3 else 0.55 for *_, p in segs],
    colors=[cmap(norm(v)) for _, _, v, _ in segs],
    capstyle="round",
)
ax.add_collection(lc)

sub = buses.get("hvmv_sub_lsb") or buses.get("_hvmv_sub_lsb")
if sub and sub["coord"]:
    ax.plot(sub["x"], sub["y"], marker="s", ms=8, color=INK,
            mec="white", mew=1.2, zorder=5)
    halo(ax.annotate("Subestação 115/12,47 kV", (sub["x"], sub["y"]),
                     textcoords="offset points", xytext=(9, 8),
                     ha="left", fontsize=7.5, color=INK,
                     fontweight="bold", zorder=6))

for reg, lbl in (("190-8593", "VREG2"), ("190-8581", "VREG3"),
                 ("190-7361", "VREG4")):
    d = buses.get(reg.lower())
    if d and d["coord"]:
        ax.plot(d["x"], d["y"], marker="o", ms=5, color="white",
                mec=INK, mew=1.3, zorder=5)
        halo(ax.annotate(lbl, (d["x"], d["y"]),
                         textcoords="offset points", xytext=(6, 5),
                         fontsize=6.5, color=INK, fontweight="bold",
                         zorder=6))

ax.autoscale()
ax.set_aspect("equal")
ax.axis("off")
ax.grid(False)
cax = ax.inset_axes([0.015, 0.02, 0.26, 0.028])
cb = fig.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=cmap), cax=cax,
                  orientation="horizontal")
cb.set_label("Tensão (pu)", fontsize=7.5, color=INK, labelpad=3)
cb.outline.set_edgecolor(BORDER)
cb.ax.tick_params(labelsize=6.8, length=2, pad=1.5)
ax.set_title(
    "IEEE 8500-Node Test Feeder — topologia georreferenciada por tensão",
    fontsize=10.5, color=INK, fontweight="bold", loc="left", pad=8)
ax.text(0, 1.005,
        f"{len(buses):,} barras · {len(segs):,} segmentos · "
        f"traço grosso = trecho trifásico".replace(",", "."),
        transform=ax.transAxes, fontsize=7.5, color=BODY, va="bottom")
footer(fig, "IEEE 8500-Node Test Feeder · caso desbalanceado (dataset oficial)")
fig.tight_layout()
fig.savefig(OUT / "ieee8500_mapa.png", bbox_inches="tight")
plt.close(fig)
print("  ✓ ieee8500_mapa.png")

# =======================================================================
# FIGURA 2 — perfil de tensão por fase vs distância
# =======================================================================
mv = {k: v for k, v in buses.items() if 6.9 < v["kv"] < 7.5}
fig, ax = plt.subplots(figsize=(7.4, 3.5), dpi=300)
for ph in (1, 2, 3):
    xs, ys = [], []
    for d in mv.values():
        if ph in d["nodes"]:
            k = d["nodes"].index(ph)
            if d["vpu"][k] > 0.1:
                xs.append(d["dist"])
                ys.append(d["vpu"][k])
    ax.scatter(xs, ys, s=1.6, c=PH[ph], alpha=0.55, linewidths=0,
               label=f"{PHNAME[ph]} ({len(xs)} nós)")

ax.axhspan(0.95, 1.05, color=ACCENT, alpha=0.07, zorder=0)
for y, lbl in ((1.05, "ANSI C84.1 Range A — 1,05 pu"),
               (0.95, "ANSI C84.1 Range A — 0,95 pu")):
    ax.axhline(y, color=BODY, lw=0.9, ls="--", zorder=1)
    ax.annotate(lbl, (ax.get_xlim()[1], y), xytext=(-4, 3),
                textcoords="offset points", ha="right", fontsize=6.8,
                color=BODY)
ax.set_xlabel("Distância elétrica à subestação (km)", fontsize=8.5)
ax.set_ylabel("Tensão (pu)", fontsize=8.5)
ax.set_title("Perfil de tensão por fase — rede primária 7,2 kV (fase-neutro)",
             fontsize=10.5, color=INK, fontweight="bold", loc="left", pad=8)
leg = ax.legend(loc="lower left", fontsize=7.5, markerscale=5,
                handletextpad=0.4, ncols=3)
for t in leg.get_texts():
    t.set_color(BODY)
ax.tick_params(labelsize=7.5)
footer(fig, "Degraus = atuação dos 4 bancos de reguladores de tensão")
fig.tight_layout()
fig.savefig(OUT / "ieee8500_perfil.png", bbox_inches="tight")
plt.close(fig)
print("  ✓ ieee8500_perfil.png")

# =======================================================================
# FIGURA 3 — desbalanço de tensão
# =======================================================================
mv3 = {k: v for k, v in mv.items()
       if len(v["nodes"]) >= 3 and set(v["nodes"][:3]) == {1, 2, 3}}
vufs, nemas = [], []
for d in mv3.values():
    u, n = vuf_nema(d["vpu"], d["ang"])
    vufs.append(u)
    nemas.append(n)
vufs = np.array(vufs)
nemas = np.array(nemas)
print(f"  VUF: máx={vufs.max():.2f}% p95={np.percentile(vufs,95):.2f}% "
      f"acima de 2%={100*(vufs>2).mean():.1f}%")

fig, ax = plt.subplots(figsize=(7.4, 3.3), dpi=300)
bins = np.linspace(0, max(4.0, vufs.max() * 1.05), 45)
ax.hist(vufs, bins=bins, color=ACCENT, alpha=0.75, edgecolor="white",
        linewidth=0.4, label="VUF — IEC 61000-3-13 (|V₂|/|V₁|)")
ax.hist(nemas, bins=bins, histtype="step", color="#C8811A", linewidth=1.4,
        label="Desbalanço NEMA MG-1")
ax.axvline(2.0, color="#B3261E", lw=1.4, ls="--")
ax.annotate("Limite 2,0 %\nIEEE 1159-2019 / NBR", (2.0, ax.get_ylim()[1]),
            xytext=(6, -12), textcoords="offset points", fontsize=7,
            color="#B3261E", fontweight="bold", va="top")
ax.set_xlabel("Fator de desbalanço de tensão (%)", fontsize=8.5)
ax.set_ylabel("Barras trifásicas", fontsize=8.5)
ax.set_title(
    f"Desbalanço de tensão — {len(mv3)} barras trifásicas da rede primária",
    fontsize=10.5, color=INK, fontweight="bold", loc="left", pad=8)
leg = ax.legend(loc="upper right", fontsize=7.5)
for t in leg.get_texts():
    t.set_color(BODY)
ax.tick_params(labelsize=7.5)
footer(fig, f"{100*(vufs>2).mean():.0f} % das barras acima do limite "
            f"de 2 % · VUF máx {vufs.max():.2f} %".replace(".", ","))
fig.tight_layout()
fig.savefig(OUT / "ieee8500_desbalanco.png", bbox_inches="tight")
plt.close(fig)
print("  ✓ ieee8500_desbalanco.png")

# =======================================================================
# FIGURA 4 — QSTS 24 passos
# =======================================================================
if os.environ.get("SKIP_QSTS"):
    print("QSTS pulado (SKIP_QSTS)")
    raise SystemExit(0)

MULT = [0.550, 0.500, 0.470, 0.450, 0.460, 0.520, 0.620, 0.720,
        0.780, 0.800, 0.820, 0.850, 0.830, 0.850, 0.880, 0.900,
        0.930, 0.970, 1.000, 0.980, 0.920, 0.800, 0.650, 0.580]
rows = []
for h, m in enumerate(MULT):
    ck = solve("Master-unbal.dss", mult=m)
    bt = bus_table(ck)
    vals = [x for d in bt.values() for x in d["vpu"] if x > 0.1]
    m3 = [d for d in bt.values()
          if 6.9 < d["kv"] < 7.5 and len(d["nodes"]) >= 3
          and set(d["nodes"][:3]) == {1, 2, 3}]
    un = [vuf_nema(d["vpu"], d["ang"]) for d in m3]
    viol = sum(1 for v in vals if v < 0.95 or v > 1.05)
    rows.append(dict(h=h, mult=m, kw=-ck.TotalPower[0],
                     kvar=-ck.TotalPower[1], vmin=min(vals),
                     vmax=max(vals), viol=viol,
                     vuf=max(u for u, _ in un),
                     nema=max(n for _, n in un)))
    print(f"  h={h:02d} m={m:.2f} P={rows[-1]['kw']:8.1f} kW "
          f"Vmin={rows[-1]['vmin']:.4f} viol={viol:4d} "
          f"NEMA={rows[-1]['nema']:.2f}%")
json.dump(rows, open(OUT / "qsts.json", "w"), indent=1)

hrs = [r["h"] for r in rows]
fig, (ax1, ax2) = plt.subplots(
    2, 1, figsize=(7.4, 4.2), dpi=300, sharex=True,
    gridspec_kw={"height_ratios": [1.15, 1]})

ax1.fill_between(hrs, [r["kw"] / 1000 for r in rows], color=ACCENT,
                 alpha=0.18)
ax1.plot(hrs, [r["kw"] / 1000 for r in rows], color=ACCENT, lw=1.8,
         label="Potência ativa da fonte (MW)")
ax1.set_ylabel("MW", fontsize=8.5)
ax1.set_title("QSTS desbalanceado — curva diária de 24 passos",
              fontsize=10.5, color=INK, fontweight="bold", loc="left",
              pad=8)
leg = ax1.legend(loc="upper left", fontsize=7.5)
for t in leg.get_texts():
    t.set_color(BODY)
ax1.tick_params(labelsize=7.5)

ax2.plot(hrs, [r["vmin"] for r in rows], color="#B3261E", lw=1.8,
         marker="o", ms=2.6, label="V mín (pu)")
ax2.plot(hrs, [r["vmax"] for r in rows], color="#2E6F9A", lw=1.8,
         marker="o", ms=2.6, label="V máx (pu)")
ax2.axhline(0.95, color=BODY, lw=0.9, ls="--")
ax2.axhline(1.05, color=BODY, lw=0.9, ls="--")
ax2.set_ylabel("Tensão (pu)", fontsize=8.5)
ax2.set_xlabel("Passo horário", fontsize=8.5)
ax2.tick_params(labelsize=7.5)
ax2.set_xticks(range(0, 24, 2))

ax3 = ax2.twinx()
ax3.bar(hrs, [r["nema"] for r in rows], color="#C8811A", alpha=0.28,
        width=0.62, label="Desbalanço NEMA máx (%)", zorder=0)
ax3.set_ylabel("Desb. NEMA (%)", fontsize=8.5, color="#C8811A")
ax3.tick_params(labelsize=7.5, colors="#C8811A")
ax3.grid(False)

h1, l1 = ax2.get_legend_handles_labels()
h2, l2 = ax3.get_legend_handles_labels()
leg = ax2.legend(h1 + h2, l1 + l2, loc="lower left", fontsize=7.5, ncols=3)
for t in leg.get_texts():
    t.set_color(BODY)

worst = min(r["vmin"] for r in rows)
wn = max(r["nema"] for r in rows)
footer(fig, f"Pior V mín {worst:.4f} pu · pior desbalanço NEMA "
            f"{wn:.2f} %".replace(".", ","))
fig.tight_layout()
fig.savefig(OUT / "ieee8500_qsts.png", bbox_inches="tight")
plt.close(fig)
print("  ✓ ieee8500_qsts.png")

json.dump({
    "nodes": nnodes, "buses": len(buses), "segments": len(segs),
    "P_kW": total_kw, "Q_kvar": total_kvar, "loss_kW": loss_kw,
    "vmin": min(x for d in buses.values() for x in d["vpu"] if x > 0.1),
    "vmax": max(x for d in buses.values() for x in d["vpu"] if x > 0.1),
    "vuf_max": float(vufs.max()), "vuf_p95": float(np.percentile(vufs, 95)),
    "nema_max": float(nemas.max()),
    "mv3_buses": len(mv3),
    "qsts_worst_vmin": worst, "qsts_worst_nema": wn,
}, open(OUT / "stats.json", "w"), indent=1)
print("FEITO →", OUT)
