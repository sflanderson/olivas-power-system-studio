"""
app.gui.ct_saturation_plots — v1.4.4 Sprint A/B/C.

Três funções de plot especializadas para CT Saturation Study,
replicando paridade visual com MATLAB CT_STUDY (LANDERSON F SILVA):

  * :func:`plot_level1_ansi`     — barras condicionais V_tap vs V_req
                                    (paridade: run_level1_ansi.m §5)
  * :func:`plot_level2_iec`      — log-log com joelho + ponto requerido
                                    (paridade: run_level2_iec.m §3)
  * :func:`plot_level3_dynamic`  — 2 subplots (fluxo + correntes)
                                    (paridade: run_level3_dynamic.m §5)

Cada função recebe um :class:`CTSaturationReport` (do backend
``app.postprocessor.ct_saturation``) e retorna um ``matplotlib.Figure``.
Não conhece Qt — quem embarca via ``FigureCanvasQTAgg`` é o dialog.

Cobertura normativa visual
===========================

A semântica de cores foi calibrada para ser **acessível** (CB friendly:
verde escuro vs vermelho saturado) e **alinhada com normas**:

* IEEE C57.13.1-2017 §6.4 — critério (1+X/R) (Plot N1)
* IEC 61869-2:2012 §5.6 — joelho 10/50 (Plot N2)
* CIGRÉ WG 23-15 — saturação dinâmica com remanência (Plot N3)
"""

from __future__ import annotations

from typing import Optional

import matplotlib

# Garante backend headless quando importado fora do dialog Qt
# (matplotlib é singleton — só aplica se ainda não setado).
if matplotlib.get_backend().lower() not in ("qtagg", "qt5agg", "qt6agg"):
    try:
        matplotlib.use("Agg", force=False)
    except Exception:
        pass

from matplotlib.figure import Figure   # noqa: E402


# ---------------------------------------------------------------------------
# Paleta de cores (paridade MATLAB CT_STUDY)
# ---------------------------------------------------------------------------


COLOR_PASS = (0.466, 0.674, 0.188)    # verde MATLAB (req OK)
COLOR_FAIL = (0.85, 0.325, 0.098)     # vermelho MATLAB (req FAIL)
COLOR_PRIMARY = (0.0, 0.447, 0.741)   # azul barra capacidade
COLOR_KNEE = (0.0, 0.5, 0.0)          # verde escuro joelho IEC

# Zonas dinâmicas (Plot N3) — RGB com transparência via alpha
ZONE_SAFE = (0.85, 1.0, 0.85)         # verde claro (pré-trip)
ZONE_TOLERANCE = (1.0, 1.0, 0.9)      # amarelo claro (margem)
ZONE_SATURATION = (1.0, 0.85, 0.85)   # vermelho claro (saturação)


# ---------------------------------------------------------------------------
# Helper — figura padrão
# ---------------------------------------------------------------------------


def _ensure_fig(
    fig: Optional[Figure], figsize=(8, 5), dpi: int = 100,
    constrained: bool = True,
) -> Figure:
    """
    Reusa fig se passada (limpa axes); senão cria nova.

    v1.4.5: ``constrained=True`` por default — evita sobreposição
    entre subplots e títulos (substitui ``tight_layout``).
    """
    if fig is None:
        return Figure(
            figsize=figsize, dpi=dpi,
            constrained_layout=constrained,
        )
    fig.clear()
    return fig


# ===========================================================================
# Sprint A — Plot Nível 1 (ANSI estático)
# ===========================================================================


def plot_level1_ansi(
    report, fig: Optional[Figure] = None,
) -> Figure:
    """
    Bar plot condicional V_tap vs V_req com cores semânticas.

    Replica MATLAB ``run_level1_ansi.m §5`` (PLOTAGEM):

    * Barra 1 (azul): V_tap (capacidade no tap atual)
    * Barra 2 (verde se passou / vermelho se falhou): V_req
    * Anotações numéricas em cima de cada barra
    * Linha tracejada preta: limite do tape (V_tap)
    * Título dinâmico com cor refletindo status

    Parameters
    ----------
    report:
        :class:`app.postprocessor.ct_saturation.CTSaturationReport`
    fig:
        Figura matplotlib opcional para reuso (limpa antes).

    Returns
    -------
    matplotlib.figure.Figure
        Figura com 1 axes contendo o gráfico de barras.
    """
    fig = _ensure_fig(fig, figsize=(9, 5))
    ax = fig.add_subplot(111)

    L1 = report.level1
    V_tap = L1.V_tap
    V_req = L1.V_req
    passed = L1.passed
    req_color = COLOR_PASS if passed else COLOR_FAIL
    status_text = "PASSOU" if passed else "FALHOU"

    # Barras lado a lado
    x_positions = [1, 2]
    bars = ax.bar(
        x_positions, [V_tap, V_req],
        width=0.6,
        color=[COLOR_PRIMARY, req_color],
        edgecolor="black", linewidth=0.8,
    )

    # Anotação numérica em cima de cada barra
    ax.text(
        1, V_tap, f" {V_tap:.0f} V",
        ha="center", va="bottom", fontweight="bold",
    )
    ax.text(
        2, V_req, f" {V_req:.0f} V",
        ha="center", va="bottom", fontweight="bold",
        color=req_color,
    )

    # Linha tracejada — limite do tape
    ax.axhline(
        V_tap, linestyle="--", color="black", linewidth=1.0,
        alpha=0.6, label="Limite do Tape",
    )

    # Eixos e ticks
    ax.set_xticks(x_positions)
    ax.set_xticklabels(
        ["Capacidade $V_{cap}$", "Requerido $V_{req}$"],
        fontsize=10,
    )
    ax.set_ylabel("Tensão Secundária (V)", fontweight="bold")
    ax.set_title(
        f"Análise Estática (ANSI 1+X/R) — TC {report.ct.tag}: "
        f"{status_text}",
        fontsize=12, fontweight="bold", color=req_color,
    )
    ax.grid(True, axis="y", alpha=0.3)

    # Margem visual no topo
    y_max = max(V_tap, V_req) * 1.15
    ax.set_ylim(0, y_max)

    # Subtítulo com recomendação
    ax.text(
        0.02, 0.97,
        f"Classe ANSI recomendada: {L1.recommended_class_C}",
        transform=ax.transAxes, fontsize=9,
        verticalalignment="top",
        bbox=dict(boxstyle="round,pad=0.4", fc="white", ec="gray"),
    )

    # v1.4.5: removido fig.tight_layout() — incompatível com
    # constrained_layout. Constrained engine cuida do spacing.
    return fig


# ===========================================================================
# Sprint B — Plot Nível 2 (IEC log-log joelho + zonas)
# ===========================================================================


def plot_level2_iec(
    report, fig: Optional[Figure] = None,
) -> Figure:
    """
    Plot log-log da curva V-I de excitação com:

    * Curva preta sólida da magnetização do TC
    * Marcador verde (joelho real, IEC 10/50)
    * Marcador azul/vermelho do ponto requerido pela falta
    * Linha tracejada horizontal Ek_req
    * Anotações ``REGIÃO LINEAR`` e ``SATURAÇÃO``
    * Título com margem de tensão

    Replica MATLAB ``run_level2_iec.m §3``.

    Se a curva for ausente (Level2 = None), retorna fig com texto
    de skip.
    """
    fig = _ensure_fig(fig, figsize=(9, 6))
    ax = fig.add_subplot(111)

    L2 = report.level2
    curve = report.ct.curve

    # Caso skip (sem curva ou Level2 não rodou)
    if L2 is None or curve is None or len(curve.Ie) < 2:
        ax.text(
            0.5, 0.5,
            "Análise IEC pulada\n(curva de magnetização ausente)",
            ha="center", va="center",
            fontsize=12, transform=ax.transAxes,
            bbox=dict(boxstyle="round,pad=0.5", fc="lightyellow", ec="gray"),
        )
        ax.set_axis_off()
        return fig

    # Curva de magnetização (log-log)
    Ie = list(curve.Ie)
    Ve = list(curve.Ve)
    ax.loglog(
        Ie, Ve, color="black", linewidth=2.0,
        label="Curva de Excitação do TC",
    )
    ax.grid(True, which="both", alpha=0.3)

    # Marcador joelho real (verde grande)
    Ek_actual = L2.Ek_actual
    # Estima I_knee correspondente via interpolação
    I_knee = curve.excitation_current(Ek_actual)
    ax.plot(
        I_knee, Ek_actual,
        marker="o", color="green",
        markerfacecolor="green", markersize=14,
        linestyle="None",
        label="Joelho Real (Capacidade)",
    )
    ax.annotate(
        f"  $E_k$ = {Ek_actual:.0f} V",
        xy=(I_knee, Ek_actual),
        xytext=(I_knee * 1.1, Ek_actual * 0.85),
        color=COLOR_KNEE, fontsize=10, fontweight="bold",
    )

    # Ponto requerido (cor depende de pass/fail)
    Ek_req = L2.Ek_req
    if L2.passed:
        marker_color = "blue"
    else:
        marker_color = "red"
    I_req = curve.excitation_current(Ek_req)
    ax.plot(
        I_req, Ek_req,
        marker="x", color=marker_color,
        markersize=14, markeredgewidth=3,
        linestyle="None",
        label="Ponto Requerido (Falta)",
    )

    # Linha tracejada horizontal — tensão requerida
    ax.axhline(
        Ek_req, linestyle="--", color=marker_color,
        linewidth=1.3, alpha=0.7,
        label=f"Requerido: {Ek_req:.0f} V",
    )

    # Anotações regiões
    if Ie:
        ax.text(
            min(Ie), Ek_actual * 0.4,
            "REGIÃO LINEAR",
            color="gray", fontsize=11, fontweight="bold",
        )
        ax.text(
            max(Ie) * 0.3, max(Ve) * 0.95,
            "SATURAÇÃO",
            color="darkred", fontsize=11, fontweight="bold",
            verticalalignment="top",
        )

    # Eixos
    ax.set_xlabel("Corrente de Excitação $I_e$ (A, RMS)")
    ax.set_ylabel("Tensão Secundária $V_e$ (V, RMS)")

    margin_v = Ek_actual - Ek_req
    ax.set_title(
        f"Análise IEC Classe P/PR — TC {report.ct.tag}\n"
        f"Margem de Tensão: {margin_v:+.1f} V "
        f"({'PASSOU' if L2.passed else 'FALHOU'})",
        fontsize=11,
    )
    ax.legend(loc="lower right", fontsize=9)

    # constrained_layout cuida do spacing (sem tight_layout)
    return fig


# ===========================================================================
# Sprint C — Plot Nível 3 (Dinâmico, 2 subplots)
# ===========================================================================


def plot_level3_dynamic(
    report, fig: Optional[Figure] = None,
) -> Figure:
    """
    2 subplots empilhados — replica MATLAB ``run_level3_dynamic.m §5``.

    **Subplot 1 — Fluxo λ(t):**

    * 3 zonas coloridas (axvspan):
      - Verde clara: pré-trip (segura)
      - Amarela: margem tolerância (entre trip e saturação)
      - Vermelha clara: zona saturação
    * Curva fluxo preta sólida
    * Linhas vermelhas em ±λ_joelho (limites físicos)
    * Linha verde TRIP, linha vermelha tracejada SAT
    * Marcador azul + info-box no instante do trip

    **Subplot 2 — Correntes ideal vs real:**

    * Mesmas zonas coloridas (alpha menor)
    * Linha vermelha tracejada I_sec ideal
    * Linha azul sólida I_sec real
    * fill_between vermelho (área de erro)
    """
    # v1.4.5: figsize maior + constrained_layout para evitar
    # sobreposição entre subplot 1 (fluxo) e subplot 2 (correntes).
    fig = _ensure_fig(fig, figsize=(11, 9))
    L3 = report.level3
    ct = report.ct

    # Caso skip
    if "PULADO" in (L3.status or "") or len(L3.flux_curve_t_ms) < 2:
        ax = fig.add_subplot(111)
        ax.text(
            0.5, 0.5,
            "Análise Dinâmica pulada\n(curva de magnetização ausente)",
            ha="center", va="center",
            fontsize=12, transform=ax.transAxes,
            bbox=dict(boxstyle="round,pad=0.5", fc="lightyellow", ec="gray"),
        )
        ax.set_axis_off()
        return fig

    # ---------- Dados ----------
    t_ms = list(L3.flux_curve_t_ms)
    flux = list(L3.flux_curve_wb_e)
    i_st = list(L3.secondary_current_ideal)
    i_s = list(L3.secondary_current_real)
    t_relay = ct.t_relay_ms
    t_sat = L3.t_sat_ms
    t_end = t_ms[-1] if t_ms else 200.0

    # λ_joelho aproximado: máximo absoluto da curva (referência visual)
    abs_flux = [abs(x) for x in flux] or [1.0]
    # Estima λ_joelho como o threshold de saturação real
    if t_sat != float("inf") and t_sat > 0:
        # Encontra λ no instante t_sat → é exatamente λ_joelho
        from app.postprocessor.ct_saturation import _interp_linear
        lambda_joelho = abs(_interp_linear(
            tuple(t_ms), tuple(flux), t_sat,
        ))
        if lambda_joelho < 1e-9:
            lambda_joelho = max(abs_flux)
    else:
        lambda_joelho = max(abs_flux) * 1.05

    # Cor do status
    if "FALHOU" in L3.status:
        status_color = COLOR_FAIL
    elif "TOLERANCIA" in L3.status or "TOLERÂNCIA" in L3.status:
        status_color = (0.6, 0.4, 0.0)
    else:
        status_color = (0.0, 0.5, 0.0)

    # ===== SUBPLOT 1 — FLUXO =====
    ax1 = fig.add_subplot(2, 1, 1)
    yl = (-lambda_joelho * 1.2, lambda_joelho * 1.2)

    # Zona segura
    ax1.axvspan(
        0, t_relay, color=ZONE_SAFE, alpha=0.5,
        label="Zona Segura (Pré-Trip)",
    )

    # Zonas condicionais
    if t_sat != float("inf"):
        # Zona saturação
        ax1.axvspan(
            t_sat, t_end, color=ZONE_SATURATION, alpha=0.5,
            label="Zona de Saturação",
        )
        # Linha vertical SAT
        ax1.axvline(
            t_sat, color="red", linestyle="--", linewidth=1.5,
        )
        ax1.text(
            t_sat, yl[1] * 0.92, "Início SAT",
            color="red", fontsize=9, fontweight="bold",
            ha="left", va="top",
        )

        # Zona tolerância
        if t_sat > t_relay:
            ax1.axvspan(
                t_relay, t_sat, color=ZONE_TOLERANCE, alpha=0.5,
                label="Margem Tolerância",
            )
            mid_x = (t_relay + t_sat) / 2.0
            ax1.text(
                mid_x, yl[1] * 0.85,
                f"Margem:\n+{L3.margin_ms:.1f} ms",
                ha="center", va="top",
                color=(0.6, 0.4, 0.0), fontweight="bold", fontsize=9,
            )

    # Curva fluxo
    ax1.plot(
        t_ms, flux, color="black", linewidth=2.0,
        label="Fluxo Real $\\lambda(t)$",
    )

    # Limites joelho (±)
    ax1.axhline(
        lambda_joelho, color="red", linewidth=2.0,
        label="Limite Joelho $\\lambda_{joelho}$",
    )
    ax1.axhline(-lambda_joelho, color="red", linewidth=2.0)

    # Linha vertical TRIP
    ax1.axvline(
        t_relay, color="green", linewidth=2.0,
    )
    ax1.text(
        t_relay, yl[1] * 0.92, "TRIP",
        color="green", fontsize=10, fontweight="bold",
        ha="right", va="top",
    )

    # Marcador no trip + info box
    from app.postprocessor.ct_saturation import _interp_linear
    lambda_at_trip = _interp_linear(
        tuple(t_ms), tuple(flux), t_relay,
    )
    ax1.plot(
        t_relay, lambda_at_trip,
        marker="o", color="blue",
        markerfacecolor="blue", markersize=8,
        linestyle="None",
        label="Ponto de Trip",
    )
    info_str = (
        f"Uso no Trip: {L3.sat_at_trip_pct:.1f}%\n"
        f"Fluxo: {lambda_at_trip:+.3f} Wb-e"
    )
    ax1.text(
        t_relay, lambda_at_trip + lambda_joelho * 0.15,
        info_str,
        ha="center", va="bottom",
        fontsize=9,
        bbox=dict(
            boxstyle="round,pad=0.4",
            fc="white", ec="blue", lw=1.0,
        ),
    )

    ax1.set_ylim(yl)
    ax1.set_xlim(0, t_end)
    ax1.set_ylabel("Fluxo $\\lambda$ (Wb-e)")
    ax1.set_title(
        f"Análise de Fluxo — TC {report.ct.tag}: {L3.status}",
        fontsize=12, color=status_color, fontweight="bold",
    )
    ax1.legend(loc="lower right", fontsize=8)
    ax1.grid(True, alpha=0.3)

    # ===== SUBPLOT 2 — CORRENTES =====
    ax2 = fig.add_subplot(2, 1, 2)

    # Mesmas zonas (alpha menor para fundo)
    ax2.axvspan(0, t_relay, color=ZONE_SAFE, alpha=0.3)
    if t_sat != float("inf"):
        ax2.axvspan(t_sat, t_end, color=ZONE_SATURATION, alpha=0.3)
        if t_sat > t_relay:
            ax2.axvspan(
                t_relay, t_sat, color=ZONE_TOLERANCE, alpha=0.3,
            )

    # Correntes
    ax2.plot(
        t_ms, i_st, color="red", linestyle="--", linewidth=1.0,
        label="$I_{sec}$ Ideal (sem saturação)",
    )
    ax2.plot(
        t_ms, i_s, color="blue", linestyle="-", linewidth=1.5,
        label="$I_{sec}$ Real (com distorção)",
    )

    # Área de erro (distorção)
    ax2.fill_between(
        t_ms, i_st, i_s, color="red", alpha=0.2,
        label="Erro (Distorção)",
    )

    # Linhas verticais
    ax2.axvline(t_relay, color="green", linewidth=2.0)
    if t_sat != float("inf"):
        ax2.axvline(
            t_sat, color="red", linestyle="--", linewidth=1.5,
        )

    ax2.set_xlim(0, t_end)
    ax2.set_xlabel("Tempo (ms)")
    # v1.4.5: ylabel em 2 linhas (substitui o set_title que sobrepunha
    # o eixo do subplot 1 — feedback do user gate v1.4.4).
    ax2.set_ylabel("Corrente Sec. (A)\n— Distorção da onda —")
    ax2.legend(loc="upper right", fontsize=8)
    ax2.grid(True, alpha=0.3)

    # constrained_layout cuida do spacing entre subplots.
    return fig
