"""
Figuras do módulo de análise de inversor (VFD) do Catálogo Técnico.

Reproduz o caso VFD-01 (75 kW @ 480 V, 6 pulsos) a partir das premissas
declaradas no estudo. Os quatro parâmetros de saída conferem com a
execução do Olivas PSS v7.x:

    h_r = 18,73 · |Z| = 55 Ω · pico no terminal = 1358 V · L_crit = 7,5 m

Uso::

    pip install matplotlib numpy
    FIG_OUT=docs/assets/vfd python scripts/make_vfd_figs.py
"""
from __future__ import annotations

import math
import os
import pathlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

# --- design tokens do Catálogo Técnico Olivas PSS -----------------------
INK = "#243018"
ACCENT = "#4D9A2E"
BODY = "#5A6157"
BORDER = "#D8DDD4"
AMBER = "#C8811A"
BLUE = "#2E6F9A"
RED = "#B3261E"

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
    "legend.frameon": False,
})

OUT = pathlib.Path(os.environ.get("FIG_OUT", "figs_vfd"))
OUT.mkdir(parents=True, exist_ok=True)


def footer(fig, text):
    fig.text(0.995, 0.006, text, ha="right", va="bottom",
             fontsize=6.5, color="#8E968F")


# --- premissas do caso VFD-01 ------------------------------------------
V_LL = 480.0            # V, barramento
Q_CAP = 50.0e3          # var, banco no barramento (0,050 Mvar)
H_R = 18.73             # ordem da ressonância paralela observada
X_OVER_R = 11.9         # relação X/R do equivalente da rede
P_DETUNE = 0.005        # reator de dessintonia, 0,50 %
F_SW = 4000.0           # Hz, frequência de chaveamento
F_CUT = 600.0           # Hz, corte do filtro senoidal
F_MOTOR = 60.0          # Hz, fundamental do motor
L_CABLE = 150.0         # m, cabo até o motor
T_RISE = 0.1            # µs, tempo de subida do IGBT
V_PROP = 150.0          # m/µs, velocidade de propagação no cabo
V_LIMIT = 1000.0        # V, limite NEMA MG-1 Parte 30 (uso geral)

S_SC = H_R ** 2 * Q_CAP                 # 17,54 MVA no barramento
X_SYS = V_LL ** 2 / S_SC
R_SYS = X_SYS / X_OVER_R
X_C = V_LL ** 2 / Q_CAP
X_L = P_DETUNE * X_C

# Harmônicos característicos de um retificador de 6 pulsos (6k ± 1)
H_CHAR = [5, 7, 11, 13, 17, 19, 23, 25, 29, 31, 35, 37, 41, 43, 47, 49]
SPECTRUM = [70.9, 28.3, 18.2, 12.1, 7.1, 5.1, 3.0, 2.0,
            1.6, 1.4, 1.0, 0.8, 0.6, 0.6, 0.4, 0.4]
THD_I = math.sqrt(sum(x ** 2 for x in SPECTRUM))
LIM_INDIV = 4.0                          # % — premissa até I_sc/I_L do PCC


# =======================================================================
# FIGURA 1 — impedância vista do PCC e ressonância paralela
# =======================================================================
h = np.linspace(1.0, 50.0, 4000)
z_sys = R_SYS + 1j * h * X_SYS
z_pure = -1j * X_C / h
z_tuned = R_SYS * 0.2 + 1j * (h * X_L - X_C / h)


def parallel(a, b):
    return a * b / (a + b)


z1 = np.abs(parallel(z_sys, z_pure))
z2 = np.abs(parallel(z_sys, z_tuned))
h_peak = float(h[np.argmax(z1)])
z_peak = float(z1.max())

fig, ax = plt.subplots(figsize=(7.4, 3.5), dpi=300)
for hc in H_CHAR:
    ax.axvline(hc, color=BORDER, lw=0.8, zorder=0)
ax.semilogy(h, z1, color=AMBER, lw=1.9, label="Banco puro (sem reator)")
ax.semilogy(h, z2, color=BLUE, lw=1.9,
            label="Com reator de dessintonia (0,5 %)")
ax.axvline(h_peak, color=AMBER, lw=1.1, ls="--")
ax.annotate(f"h_r = {h_peak:.2f}\n{z_peak:.0f} Ω".replace(".", ","),
            (h_peak, z_peak),
            xytext=(8, -4), textcoords="offset points", fontsize=7.5,
            color=AMBER, fontweight="bold", va="top")
ax.set_xlabel("Ordem harmônica h", fontsize=8.5)
ax.set_ylabel("|Z| vista do PCC (Ω)", fontsize=8.5)
ax.set_title(
    f"Ressonância paralela em h = {h_peak:.2f} — risco ALTO "
    f"(harmônico mais próximo: 19º)".replace("18.73", "18,73"),
    fontsize=10.5, color=INK, fontweight="bold", loc="left", pad=8)
ax.set_xlim(1, 50)
leg = ax.legend(loc="upper right", fontsize=7.5)
for t in leg.get_texts():
    t.set_color(BODY)
ax.tick_params(labelsize=7.5)
footer(fig, "Linhas cinzas = harmônicos característicos de 6 pulsos · a "
            "POSIÇÃO do pico é robusta; a ALTURA depende do amortecimento "
            "(X/R = 11,9)")
fig.tight_layout()
fig.savefig(OUT / "vfd_ressonancia.png", bbox_inches="tight")
plt.close(fig)
print(f"  ✓ vfd_ressonancia.png  (h_r={h_peak:.2f}, |Z|={z_peak:.1f} Ω)")

# =======================================================================
# FIGURA 2 — espectro harmônico de entrada
# =======================================================================
fig, ax = plt.subplots(figsize=(7.4, 3.3), dpi=300)
cols = [RED if v > LIM_INDIV else ACCENT for v in SPECTRUM]
bars = ax.bar(range(len(H_CHAR)), SPECTRUM, color=cols, width=0.66,
              edgecolor="white", linewidth=0.5)
for b, v in zip(bars, SPECTRUM):
    ax.annotate(f"{v:.1f}", (b.get_x() + b.get_width() / 2, v),
                xytext=(0, 2), textcoords="offset points",
                ha="center", fontsize=6.2, color=BODY)
ax.axhline(LIM_INDIV, color=BODY, lw=1.1, ls="--")
ax.annotate("limite individual 4 % (premissa)", (len(H_CHAR) - 0.4,
            LIM_INDIV), xytext=(0, 4), textcoords="offset points",
            ha="right", fontsize=7, color=BODY)
ax.set_xticks(range(len(H_CHAR)))
ax.set_xticklabels([str(x) for x in H_CHAR])
ax.set_xlabel("Ordem harmônica", fontsize=8.5)
ax.set_ylabel("Corrente harmônica (% da fundamental)", fontsize=8.5)
ax.set_title(f"Espectro de entrada — 6 pulsos, THD_I = {THD_I:.1f} %"
             .replace(".", ","),
             fontsize=10.5, color=INK, fontweight="bold", loc="left", pad=8)
ax.tick_params(labelsize=7.5)
ax.set_axisbelow(True)
footer(fig, "O limite individual do IEEE Std 519 depende da razão "
            "I_sc/I_L no PCC — enquanto ela não é informada, o valor "
            "mostrado é PREMISSA")
fig.tight_layout()
fig.savefig(OUT / "vfd_espectro.png", bbox_inches="tight")
plt.close(fig)
print(f"  ✓ vfd_espectro.png  (THD_I={THD_I:.1f} %)")

# =======================================================================
# FIGURA 3 — sobretensão no motor (onda refletida)
# =======================================================================
l_crit = T_RISE * V_PROP / 2.0
v_base = math.sqrt(2) * V_LL
lens = np.linspace(0, 300, 1500)
gamma = np.minimum(lens / l_crit, 1.0)
v_peak = v_base * (1.0 + gamma)
v_project = float(v_base * (1.0 + min(L_CABLE / l_crit, 1.0)))

fig, ax = plt.subplots(figsize=(7.4, 3.3), dpi=300)
ax.plot(lens, v_peak, color=RED, lw=2.0, label="Pico no terminal (Γ = 1,00)")
ax.axhline(V_LIMIT, color=BODY, lw=1.1, ls="--")
ax.annotate("limite 1000 V (NEMA MG-1 Parte 30, uso geral)",
            (300, V_LIMIT), xytext=(-4, 5), textcoords="offset points",
            ha="right", fontsize=7, color=BODY)
ax.axvline(l_crit, color=BODY, lw=0.9, ls=":")
ax.annotate(f"L_crit = {l_crit:.1f} m".replace(".", ","), (l_crit, v_base),
            xytext=(6, 2), textcoords="offset points", fontsize=7,
            color=BODY)
ax.plot([L_CABLE], [v_project], marker="o", ms=7, color=RED,
        mec="white", mew=1.2, zorder=5,
        label=f"Este projeto ({L_CABLE:.0f} m) — {v_project:.0f} V")
ax.set_xlabel("Comprimento do cabo até o motor (m)", fontsize=8.5)
ax.set_ylabel("Tensão de pico no terminal (V)", fontsize=8.5)
ax.set_title(f"Onda refletida — REPROVADO: {v_project:.0f} V com "
             f"{L_CABLE:.0f} m de cabo",
             fontsize=10.5, color=RED, fontweight="bold", loc="left", pad=8)
ax.set_xlim(0, 300)
leg = ax.legend(loc="lower right", fontsize=7.5)
for t in leg.get_texts():
    t.set_color(BODY)
ax.tick_params(labelsize=7.5)
footer(fig, f"t_subida = {T_RISE:.1f} µs · velocidade de propagação "
            f"{V_PROP:.0f} m/µs · acima de L_crit o pico satura em "
            f"2·√2·V_LL".replace("0.1", "0,1"))
fig.tight_layout()
fig.savefig(OUT / "vfd_onda_refletida.png", bbox_inches="tight")
plt.close(fig)
print(f"  ✓ vfd_onda_refletida.png  (pico={v_project:.0f} V)")

# =======================================================================
# FIGURA 4 — filtro de saída
# =======================================================================
fig, ax = plt.subplots(figsize=(7.4, 3.3), dpi=300)
rows = [("Fundamental do motor", F_MOTOR, "#9AA398"),
        ("Corte do filtro senoidal", F_CUT, BLUE),
        ("Chaveamento (f_sw)", F_SW, AMBER)]
for i, (lbl, f, col) in enumerate(rows):
    ax.barh(i, f, color=col, height=0.44, left=40)
    ax.annotate(f"{f:.0f} Hz", (f, i), xytext=(6, 0),
                textcoords="offset points", va="center", fontsize=8,
                color=INK, fontweight="bold")
ax.set_yticks(range(len(rows)))
ax.set_yticklabels([r[0] for r in rows], fontsize=8)
ax.set_xscale("log")
ax.set_xlim(40, 9000)
ax.set_xlabel("Frequência (Hz)", fontsize=8.5)
ax.set_title("Filtro de saída — o senoidal corta em 600 Hz; o dv/dt "
             "alonga t_subida para ≈ 1,0 µs",
             fontsize=10.5, color=INK, fontweight="bold", loc="left", pad=8)
ax.tick_params(labelsize=7.5)
ax.grid(axis="y", visible=False)
ax.set_axisbelow(True)
footer(fig, "Senoidal: L = 0,407 mH · C = 172,7 µF   |   dv/dt: "
            "L = 0,0318 mH · C = 0,0032 µF · R = 100 Ω (casado à "
            "impedância de surto do cabo)")
fig.tight_layout()
fig.savefig(OUT / "vfd_filtro.png", bbox_inches="tight")
plt.close(fig)
print("  ✓ vfd_filtro.png")
print("FEITO →", OUT)
