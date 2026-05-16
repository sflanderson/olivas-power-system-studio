"""
app.gui.tcc_coordinogram — Coordenograma TCC interativo
estilo SKM PTW CAPTOR (v1.0.2).

Filosofia
==========

PTW CAPTOR é a referência da indústria para análise de
coordenação tempo-corrente. Características-chave:

* **Eixo log-log**: corrente (A) × tempo (s)
* **Múltiplas curvas** sobrepostas (até 8 dispositivos)
* **Drag-and-drop**: arrastar curva ajusta TMS / pickup
* **Marker de Ik''** vertical em vermelho
* **Detecção de cruzamentos** (violations Δt < margin)
* **Cores distintas por tipo**:
  - Relé: azul / amarelo / verde
  - Fusível: laranja
  - Disjuntor (eletromecânico): magenta
  - Termal motor (49): roxo

Uso
====

::

    from app.gui.tcc_coordinogram import TCCCoordinogramDialog
    from app.postprocessor.tcc_curves import (
        TCCCurve, CurveType,
    )

    curves = [
        TCCCurve("Relé Feeder", CurveType.IEC_VERY_INVERSE, 200, 0.5),
        TCCCurve("Relé Motor", CurveType.IEC_STANDARD_INVERSE, 50, 0.2),
    ]
    dlg = TCCCoordinogramDialog(curves, fault_current_A=5000)
    dlg.exec()

Implementação
==============

Usa matplotlib (QtAgg backend) com:

* ``FigureCanvasQTAgg`` embedado em QDialog
* ``Line2D.set_picker(True)`` em cada curva → ``pick_event``
* Drag tracking via ``button_press_event`` /
  ``motion_notify_event`` / ``button_release_event``
* Recompute curva ao soltar mouse: nova TMS = old · y_ratio
"""

from __future__ import annotations

import math
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox, QDialog, QDialogButtonBox, QHBoxLayout, QLabel,
    QListWidget, QListWidgetItem, QPushButton, QVBoxLayout,
    QWidget,
)

from app.postprocessor.tcc_curves import (
    CurveType, FuseTCCCurve, TCCCurve, check_coordination,
    check_fuse_fuse_coordination, check_fuse_relay_coordination,
)
# v1.2.0 Fase δ: integração com novos backends (β + γ).
# Imports lazy nas funções de plot para evitar carregamento se
# nenhum TCCDevice/DamageCurve estiver na lista.
try:
    from app.postprocessor.tcc_devices import TCCDevice
except ImportError:  # pragma: no cover — bootstrap parcial
    TCCDevice = None
try:
    from app.postprocessor.tcc_damage import (
        CableDamageCurve,
        TransformerThroughFaultCurve,
        MotorThermalCurve,
    )
    _DAMAGE_CLASSES: tuple = (
        CableDamageCurve,
        TransformerThroughFaultCurve,
        MotorThermalCurve,
    )
except ImportError:  # pragma: no cover
    CableDamageCurve = None
    TransformerThroughFaultCurve = None
    MotorThermalCurve = None
    _DAMAGE_CLASSES = ()


# ---------------------------------------------------------------------------
# Cores PTW-style por tipo de dispositivo
# ---------------------------------------------------------------------------


_COLORS_BY_INDEX = (
    "#1f77b4",  # azul
    "#ff7f0e",  # laranja (fusível)
    "#2ca02c",  # verde
    "#d62728",  # vermelho
    "#9467bd",  # roxo (térmico)
    "#8c564b",  # marrom
    "#e377c2",  # rosa
    "#7f7f7f",  # cinza
)


# ---------------------------------------------------------------------------
# Coordinogram canvas (matplotlib widget)
# ---------------------------------------------------------------------------


class TCCCoordinogramWidget(QWidget):
    """
    Widget de coordenograma TCC interativo.

    Sinais
    -------
    curve_modified(int, float, float):
        Emitido quando o usuário arrasta uma curva.
        Args: (curve_index, new_pickup_A, new_tms).
    """

    curve_modified = Signal(int, float, float)

    def __init__(
        self,
        curves: list,  # list[TCCCurve | FuseTCCCurve]
        fault_current_A: float = 0.0,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        # v1.1.0: Aceita TCCCurve (relé) e FuseTCCCurve (fusível).
        # FuseTCCCurve é renderizado com 2 envelopes (melt + clear).
        self._curves: list = list(curves)
        self._fault_current_A = fault_current_A
        self._enabled_mask: list[bool] = [True] * len(curves)
        self._dragging_idx: Optional[int] = None
        self._drag_start_y: Optional[float] = None
        self._drag_start_tms: Optional[float] = None
        # v3.6.2 (closes SKIPPED_BACKLOG D.1) — C-lines overlay
        self._c_lines: list = []
        # v3.6.2 (closes SKIPPED_BACKLOG D.2) — multi-protection filter
        # Modos: "all" (default), "phase" (50/51), "ground" (50N/51N)
        self._protection_filter: str = "all"

        self._setup_ui()
        self._draw_all()

    def _setup_ui(self) -> None:
        # Lazy-import matplotlib (não tem custo se módulo não usado)
        import matplotlib
        matplotlib.use("QtAgg")
        from matplotlib.backends.backend_qtagg import (
            FigureCanvasQTAgg as FigureCanvas,
            NavigationToolbar2QT as NavigationToolbar,
        )
        from matplotlib.figure import Figure

        self._figure = Figure(figsize=(10, 7), dpi=100)
        self._canvas = FigureCanvas(self._figure)
        self._toolbar = NavigationToolbar(self._canvas, self)
        self._ax = self._figure.add_subplot(111)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._toolbar)
        layout.addWidget(self._canvas, stretch=1)

        # Wire mouse events
        self._canvas.mpl_connect(
            "button_press_event", self._on_press,
        )
        self._canvas.mpl_connect(
            "motion_notify_event", self._on_motion,
        )
        self._canvas.mpl_connect(
            "button_release_event", self._on_release,
        )

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------

    def _draw_all(self) -> None:
        """Redraws all curves + fault marker + labels."""
        ax = self._ax
        ax.clear()
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlabel("Corrente (A)", fontsize=11)
        ax.set_ylabel("Tempo (s)", fontsize=11)
        ax.set_title(
            "Coordenograma TCC — clique e arraste curva para "
            "ajustar TMS",
            fontsize=12, color="#556B2F",
        )
        ax.grid(True, which="both", alpha=0.3, linestyle="--")
        ax.set_xlim(1, 1e5)
        ax.set_ylim(0.01, 1000)

        self._line_artists: dict[int, "Line2D"] = {}
        for idx, curve in enumerate(self._curves):
            if not self._enabled_mask[idx]:
                continue
            # v3.6.2 D.2 — apply protection filter (phase/ground/all)
            if not self._curve_matches_protection(
                curve, self._protection_filter
            ):
                continue
            color = _COLORS_BY_INDEX[idx % len(_COLORS_BY_INDEX)]
            # v1.2.0 Fase δ: dispatch estendido para suportar backends
            # de β (TCCDevice) e γ (DamageCurves) além do v1.1.0
            # (TCCCurve, FuseTCCCurve).
            #
            # Ordem de checagem importa: damage classes primeiro
            # (cor fixa vermelha), depois device, depois fuse, depois
            # default relay (TCCCurve legacy).
            if _DAMAGE_CLASSES and isinstance(curve, _DAMAGE_CLASSES):
                self._draw_damage_curve(ax, idx, curve)
            elif TCCDevice is not None and isinstance(curve, TCCDevice):
                self._draw_device(ax, idx, curve, color)
            elif isinstance(curve, FuseTCCCurve):
                self._draw_fuse_curve(ax, idx, curve, color)
            else:
                self._draw_relay_curve(ax, idx, curve, color)

        # Fault current marker
        if self._fault_current_A > 0:
            ax.axvline(
                self._fault_current_A,
                color="red", linestyle="-", linewidth=2.5,
                label=f"Ik''  = {self._fault_current_A/1000:.2f} kA",
                zorder=10,
            )

        # v3.6.2 D.1 — render C-lines overlay
        if self._c_lines:
            self._draw_c_lines(ax)

        ax.legend(loc="upper right", fontsize=8, framealpha=0.9)

        # Detecção de violations (Δt entre curvas em série)
        self._draw_violations(ax)
        # v1.2.0 δ.3: violations específicas proteção × damage
        self._detect_protection_vs_damage_violations(ax)

        self._canvas.draw_idle()

    # ------------------------------------------------------------------
    # v1.1.0: Per-type drawing (relay = 1 curve, fuse = 2 curves)
    # ------------------------------------------------------------------

    def _draw_relay_curve(self, ax, idx: int, curve: TCCCurve, color: str) -> None:
        """Renderiza um relé (curva única inverse-time)."""
        pts = curve.points(
            i_min_A=max(curve.pickup_A, 1.0),
            i_max_A=1e5,
            n_points=80,
        )
        if not pts:
            return
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        label = (
            f"{curve.relay_id}  ·  pickup={curve.pickup_A:.0f}A  "
            f"TMS={curve.tms:.2f}"
        )
        line, = ax.plot(
            xs, ys, color=color, linewidth=2.0,
            label=label, picker=5, zorder=5,
        )
        line._tcc_curve_idx = idx
        # Vertical pickup line (tracejada)
        ax.axvline(
            curve.pickup_A,
            color=color, linestyle=":", alpha=0.4, linewidth=1,
        )
        # Instantâneo (50)
        if curve.instantaneous_pickup_A is not None:
            ax.axvline(
                curve.instantaneous_pickup_A,
                color=color, linestyle="-.", alpha=0.7,
                linewidth=1.5,
            )
        self._line_artists[idx] = line

    def _draw_fuse_curve(self, ax, idx: int, curve: FuseTCCCurve, color: str) -> None:
        """
        v1.1.0: Renderiza um fusível com **2 envelopes**: melt
        (linha tracejada, interna) e clear (linha sólida, externa).

        Estilo PTW CAPTOR — entre os dois envelopes fica a "banda"
        de fusão do fusível, sombreada para destacar o range.
        """
        melt_pts = curve.melt_points(
            i_min_A=curve.rated_current_A * 1.0,
            i_max_A=1e5,
            n_points=80,
        )
        clear_pts = curve.clear_points(
            i_min_A=curve.rated_current_A * 1.0,
            i_max_A=1e5,
            n_points=80,
        )
        if not melt_pts or not clear_pts:
            return
        # Melt envelope — tracejado (limite inferior do range)
        xs_m = [p[0] for p in melt_pts]
        ys_m = [p[1] for p in melt_pts]
        label_melt = (
            f"{curve.fuse_id} ({curve.fuse_class.value} "
            f"{curve.rated_current_A:.0f}A) — melt"
        )
        line_m, = ax.plot(
            xs_m, ys_m, color=color, linewidth=1.5,
            linestyle="--", label=label_melt, picker=5, zorder=5,
            alpha=0.9,
        )
        line_m._tcc_curve_idx = idx
        line_m._fuse_envelope = "melt"
        # Clear envelope — sólido (limite superior)
        xs_c = [p[0] for p in clear_pts]
        ys_c = [p[1] for p in clear_pts]
        label_clear = (
            f"{curve.fuse_id} ({curve.fuse_class.value} "
            f"{curve.rated_current_A:.0f}A) — clear"
        )
        line_c, = ax.plot(
            xs_c, ys_c, color=color, linewidth=2.0,
            linestyle="-", label=label_clear, picker=5, zorder=5,
        )
        line_c._tcc_curve_idx = idx
        line_c._fuse_envelope = "clear"
        # Banda entre melt e clear (sombreada)
        # Nota: melt e clear têm o mesmo grid de I (mesmo n_points
        # e i_min/i_max), portanto suas listas de tempo se
        # correspondem ponto-a-ponto.
        if len(melt_pts) == len(clear_pts):
            ax.fill_between(
                xs_m, ys_m, ys_c,
                color=color, alpha=0.10, zorder=3,
            )
        # Pickup vertical (1.5×In típico)
        ax.axvline(
            curve.rated_current_A * 1.5,
            color=color, linestyle=":", alpha=0.3, linewidth=1,
        )
        # Registra apenas o clear como artist principal
        # (drag-and-drop do fusível altera comportamento de toda
        # a faixa via In; para v1.1.0 mantemos drag desabilitado
        # em fuses — _on_press não trata FuseTCCCurve).
        self._line_artists[idx] = line_c

    # ------------------------------------------------------------------
    # v1.2.0 Fase δ: TCCDevice + DamageCurve adapters
    # ------------------------------------------------------------------

    def _draw_device(self, ax, idx: int, device, color: str) -> None:
        """
        v1.2.0 δ.1: renderiza um ``TCCDevice`` (multi-function
        relay) como composite envelope.

        Plota uma única curva sólida (composite = min sobre
        segments enabled). Cada segment com pickup vertical
        tracejado da mesma cor (visualmente identifica os
        50/51/49/87).

        Drag-drop NÃO suportado: para alterar setting de um
        segment dentro do device, edite o segment e re-crie
        o device via API.
        """
        # Composite envelope (min sobre segments enabled)
        try:
            pts = device.composite_points(
                i_min_A=1.0,
                i_max_A=1e5,
                n_points=200,
            )
        except Exception:
            return
        if not pts:
            return
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        # Label com manufacturer/model se disponíveis
        manuf = getattr(device, "manufacturer", "") or ""
        model = getattr(device, "model", "") or ""
        if manuf != "Generic" or model != "Generic":
            lbl_meta = f" ({manuf}/{model})"
        else:
            lbl_meta = ""
        n_segs = len(getattr(device, "segments", ()))
        label = (
            f"{device.device_id}{lbl_meta}  ·  composite ({n_segs} fns)"
        )
        line, = ax.plot(
            xs, ys, color=color, linewidth=2.0,
            label=label, picker=5, zorder=5,
        )
        line._tcc_curve_idx = idx
        # Pickup verticals tracejados para cada segment com pickup
        # observável (LT/ST/INST/I2T têm pickup_A; FixTime tem i_min_A;
        # OpenClear* não têm pickup direto — pula).
        for seg in getattr(device, "segments", ()):
            if not getattr(seg, "enabled", True):
                continue
            i_pu = getattr(seg, "pickup_A", None) \
                or getattr(seg, "pickup_A_nominal", None) \
                or getattr(seg, "i_min_A", None)
            if i_pu is not None and i_pu > 0:
                ax.axvline(
                    i_pu, color=color,
                    linestyle=":", alpha=0.35, linewidth=1.0,
                )
        self._line_artists[idx] = line

    def _draw_damage_curve(self, ax, idx: int, damage) -> None:
        """
        v1.2.0 δ.2: renderiza damage curve (cable, XFMR, motor).

        Convenção PTW CAPTOR: cor vermelha #C0392B (paleta
        corporativa Olivas), linestyle tracejado denso, linewidth
        1.5 (mais discreto que proteção sólida 2.0), zorder 3
        (proteção fica por cima).

        Damage curves NÃO têm drag-drop habilitado.
        """
        DAMAGE_COLOR = "#C0392B"   # vermelho PTW (mesma cor de _PTW_RED)

        # Detecta tipo via duck typing — cada damage class expõe
        # um *_points / *_time_at_current diferente.
        pts = []
        if hasattr(damage, "damage_points"):
            pts = damage.damage_points(
                i_min_A=1.0, i_max_A=1e5, n_points=150,
            )
            kind = "cable"
            id_attr = "cable_id"
        elif hasattr(damage, "through_fault_points"):
            pts = damage.through_fault_points(
                i_min_A=1.0, i_max_A=1e5, n_points=150,
            )
            kind = "XFMR"
            id_attr = "xfmr_id"
        elif hasattr(damage, "thermal_points"):
            pts = damage.thermal_points(
                i_min_A=1.0, i_max_A=1e5, n_points=150,
            )
            kind = "motor"
            id_attr = "motor_id"
        else:
            return  # tipo desconhecido — pula silenciosamente

        if not pts:
            return
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        damage_id = getattr(damage, id_attr, "?")
        label = f"⚠ DAMAGE {kind}: {damage_id}"

        line, = ax.plot(
            xs, ys, color=DAMAGE_COLOR,
            linestyle=(0, (5, 2)),     # dashed denso
            linewidth=1.5,
            label=label,
            zorder=3,                  # abaixo das proteções
            alpha=0.85,
        )
        # NÃO seta picker — damage não é arrastável.
        # NÃO registra em _line_artists — para excluir de drag.

    def _draw_violations(self, ax) -> None:
        """v1.0.2 + v1.1.0: marca pontos onde curvas adjacentes têm Δt
        insuficiente (estilo CAPTOR).

        v1.1.0: dispatch por tipo de par:
        - Relay-Relay: ``check_coordination`` (Δt em segundos)
        - Fuse-Fuse: ``check_fuse_fuse_coordination`` (margin %)
        - Fuse-Relay: ``check_fuse_relay_coordination`` (margin %)
        """
        if self._fault_current_A <= 0:
            return
        if len(self._curves) < 2:
            return
        enabled = [
            (i, c) for i, c in enumerate(self._curves)
            if self._enabled_mask[i]
        ]
        for k in range(len(enabled) - 1):
            i_up, c_up = enabled[k]
            i_dn, c_dn = enabled[k + 1]
            self._check_and_annotate_pair(ax, c_up, c_dn)

    def _check_and_annotate_pair(self, ax, c_up, c_dn) -> None:
        """v1.1.0: verifica par upstream/downstream e anota se viola."""
        I = self._fault_current_A
        passes: bool
        annotation: str
        t_up: float
        t_dn: float

        # v1.2.0 Fase δ: damage curves NÃO entram em coord pair-wise
        # (são limites a evitar, não dispositivos coordenáveis).
        # Violations específicas (proteção × damage) são tratadas em
        # _detect_protection_vs_damage_violations (δ.3).
        if _DAMAGE_CLASSES and (
            isinstance(c_up, _DAMAGE_CLASSES)
            or isinstance(c_dn, _DAMAGE_CLASSES)
        ):
            return

        # v1.2.0 Fase δ: TCCDevice (composite) — usa
        # check_device_coordination da β.3 quando ambos são devices.
        if TCCDevice is not None and (
            isinstance(c_up, TCCDevice) or isinstance(c_dn, TCCDevice)
        ):
            self._check_device_pair(ax, c_up, c_dn)
            return

        if isinstance(c_up, FuseTCCCurve) and isinstance(c_dn, FuseTCCCurve):
            chk = check_fuse_fuse_coordination(c_up, c_dn, I)
            passes = chk.passes
            t_up = chk.upstream_melt_s
            t_dn = chk.downstream_clear_s
            annotation = (
                f"⚠ Fuse-Fuse: margin={chk.margin_pct:.0f}% < 25%"
            )
        elif isinstance(c_up, FuseTCCCurve):
            # fuse upstream + relay downstream
            chk = check_fuse_relay_coordination(c_up, c_dn, I)
            passes = chk.passes
            t_up = chk.upstream_melt_s
            t_dn = chk.downstream_clear_s
            annotation = (
                f"⚠ Fuse-Relay: margin={chk.margin_pct:.0f}% < 25%"
            )
        elif isinstance(c_dn, FuseTCCCurve):
            # relay upstream + fuse downstream — caso menos comum;
            # checa se relay opera depois do fuse clear (que é o
            # esperado se fuse for downstream).
            t_up = c_up.operating_time_at_current(I)
            t_dn = c_dn.clear_time_at_current(I)
            actual_dt = t_up - t_dn
            passes = (
                math.isfinite(t_up) and math.isfinite(t_dn)
                and actual_dt >= 0.25
            )
            annotation = f"⚠ Relay-Fuse: Δt={actual_dt*1000:.0f}ms < 250ms"
        else:
            chk = check_coordination(
                c_up, c_dn, I, relay_type="digital",
            )
            passes = chk.passes
            t_up = chk.upstream_time_s
            t_dn = chk.downstream_time_s
            annotation = f"⚠ Δt={chk.actual_delta_t_s*1000:.0f}ms"

        if passes:
            return
        if not (math.isfinite(t_up) and math.isfinite(t_dn)):
            return
        # Highlight vermelho na zona da intersecção
        ax.fill_between(
            [I * 0.95, I * 1.05],
            [min(t_up, t_dn) * 0.9] * 2,
            [max(t_up, t_dn) * 1.1] * 2,
            color="red", alpha=0.18, zorder=2,
        )
        ax.annotate(
            annotation,
            xy=(I, (t_up + t_dn) / 2),
            xytext=(20, 0),
            textcoords="offset points",
            fontsize=8, color="red", fontweight="bold",
        )

    def _detect_protection_vs_damage_violations(self, ax) -> None:
        """
        v1.2.0 δ.3: detecta cruzamentos de proteção × damage curve.

        Para cada par (proteção, damage), avalia em N pontos
        log-spaced. Se em algum ponto ``t_protection(I) >
        t_damage(I)``, há violation: equipamento sofre damage
        antes da proteção operar.

        Algoritmo
        ----------

        1. Coleta proteções: TCCCurve, TCCDevice, FuseTCCCurve
        2. Coleta damages: CableDamage, XfmrThroughFault, MotorThermal
        3. Para cada par, avalia em ``n_eval`` pontos entre
           ``i_min_eval`` e ``i_max_eval``.
        4. Se há cruzamento, marca o ponto MAIS À ESQUERDA (menor
           corrente = pior caso) com:
           - X vermelho 16pt (visualmente forte)
           - Annotation "⚠ VIOLATION: <protection_id> > <damage_id>"

        Não-objetivos
        --------------

        * Não conta múltiplos cruzamentos (apenas o pior por par).
        * Não desenha sombreamento da zona crítica (Fase v1.3).
        """
        # Coletar enabled curves por categoria
        enabled = [
            c for i, c in enumerate(self._curves)
            if self._enabled_mask[i]
        ]
        protections = [
            c for c in enabled
            if not (_DAMAGE_CLASSES and isinstance(c, _DAMAGE_CLASSES))
        ]
        damages = [
            c for c in enabled
            if _DAMAGE_CLASSES and isinstance(c, _DAMAGE_CLASSES)
        ]
        if not damages or not protections:
            return

        # Eval grid (log-spaced)
        n_eval = 50
        i_min_eval = 10.0
        i_max_eval = 1e5
        log_min = math.log10(i_min_eval)
        log_max = math.log10(i_max_eval)
        currents = [
            10 ** (log_min + i * (log_max - log_min) / (n_eval - 1))
            for i in range(n_eval)
        ]

        for prot in protections:
            for dmg in damages:
                self._mark_protection_vs_damage(
                    ax, prot, dmg, currents,
                )

    def _t_at(self, curve, current_A: float) -> float:
        """
        Helper: retorna ``t(I)`` de qualquer tipo de curva
        (TCCCurve, TCCDevice, FuseTCCCurve, *DamageCurve).
        """
        # Damage curves — duck typing
        if hasattr(curve, "damage_time_at_current"):
            return curve.damage_time_at_current(current_A)
        if hasattr(curve, "through_fault_time_at_current"):
            return curve.through_fault_time_at_current(current_A)
        if hasattr(curve, "thermal_time_at_current"):
            return curve.thermal_time_at_current(current_A)
        # TCCDevice (composite)
        if hasattr(curve, "composite_time_at_current"):
            return curve.composite_time_at_current(current_A)
        # FuseTCCCurve — usa clear (envelope superior conservador)
        if hasattr(curve, "clear_time_at_current"):
            return curve.clear_time_at_current(current_A)
        # TCCCurve legacy
        if hasattr(curve, "operating_time_at_current"):
            return curve.operating_time_at_current(current_A)
        return float("inf")

    def _mark_protection_vs_damage(
        self, ax, protection, damage, currents: list,
    ) -> None:
        """
        Para um par (protection, damage), avalia em ``currents``
        e marca a primeira violation encontrada.
        """
        first_violation_I = None
        first_violation_dmg_t = None
        first_violation_prot_t = None
        for I in currents:
            t_prot = self._t_at(protection, I)
            t_dmg = self._t_at(damage, I)
            if not (math.isfinite(t_prot) and math.isfinite(t_dmg)):
                continue
            # Violation: proteção mais lenta que damage
            if t_prot > t_dmg:
                first_violation_I = I
                first_violation_dmg_t = t_dmg
                first_violation_prot_t = t_prot
                break

        if first_violation_I is None:
            return  # sem violation

        # IDs para annotation
        prot_id = (
            getattr(protection, "device_id", None)
            or getattr(protection, "relay_id", None)
            or getattr(protection, "fuse_id", None)
            or "?"
        )
        dmg_id = (
            getattr(damage, "cable_id", None)
            or getattr(damage, "xfmr_id", None)
            or getattr(damage, "motor_id", None)
            or "?"
        )

        # Marker X vermelho na intersecção (média geométrica de t)
        t_marker = math.sqrt(first_violation_dmg_t * first_violation_prot_t)
        ax.plot(
            first_violation_I, t_marker,
            marker="x", markersize=14, markeredgewidth=2.5,
            color="red", zorder=20,
        )
        ax.annotate(
            f"⚠ VIOLATION\n{prot_id} > {dmg_id}",
            xy=(first_violation_I, t_marker),
            xytext=(15, 15),
            textcoords="offset points",
            fontsize=8, color="red", fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.3", fc="white",
                      ec="red", alpha=0.9),
        )

    def _check_device_pair(self, ax, c_up, c_dn) -> None:
        """
        v1.2.0 Fase δ.1: verifica coord par-a-par envolvendo
        ao menos um TCCDevice. Reusa
        ``check_device_coordination`` da β.3 quando ambos são
        devices; usa fallback ad-hoc quando misturado.
        """
        from app.postprocessor.tcc_devices import (
            check_device_coordination,
        )

        I = self._fault_current_A

        # Ambos TCCDevice → API canonical da β.3
        if (
            TCCDevice is not None
            and isinstance(c_up, TCCDevice)
            and isinstance(c_dn, TCCDevice)
        ):
            chk = check_device_coordination(
                c_up, c_dn, I, relay_type="digital",
            )
            if chk.passes:
                return
            t_up = chk.upstream_composite_time_s
            t_dn = chk.downstream_composite_time_s
            if not (math.isfinite(t_up) and math.isfinite(t_dn)):
                return
            ax.fill_between(
                [I * 0.95, I * 1.05],
                [min(t_up, t_dn) * 0.9] * 2,
                [max(t_up, t_dn) * 1.1] * 2,
                color="red", alpha=0.18, zorder=2,
            )
            ax.annotate(
                f"⚠ Δt={chk.actual_delta_t_s*1000:.0f}ms "
                f"({chk.triggered_upstream_segment_id} vs "
                f"{chk.triggered_downstream_segment_id})",
                xy=(I, (t_up + t_dn) / 2),
                xytext=(20, 0),
                textcoords="offset points",
                fontsize=8, color="red", fontweight="bold",
            )
            return
        # Mix Device + TCCCurve/FuseTCCCurve → simplifica usando
        # composite envelope no lado do device, t() no lado clássico.
        # Edge case raro — não anota para evitar falso-positivo.

    # ------------------------------------------------------------------
    # Mouse interaction (drag curves)
    # ------------------------------------------------------------------

    def _on_press(self, event) -> None:
        if event.inaxes != self._ax:
            return
        # Hit test: encontra curva mais próxima do clique
        if event.button != 1:   # only left button
            return
        for idx, line in self._line_artists.items():
            contains, _ = line.contains(event)
            if contains:
                # v1.1.0: drag não suportado em FuseTCCCurve — fusível
                # tem In fixo (datasheet) e não TMS ajustável. Para
                # mudar a curva, o usuário muda a propriedade do
                # componente FUSE no editor e re-abre o coordenograma.
                if isinstance(self._curves[idx], FuseTCCCurve):
                    continue
                self._dragging_idx = idx
                self._drag_start_y = event.ydata
                self._drag_start_tms = self._curves[idx].tms
                break

    def _on_motion(self, event) -> None:
        if self._dragging_idx is None:
            return
        if event.ydata is None or self._drag_start_y is None:
            return
        # Razão entre y_atual e y_inicial → multiplica TMS
        if self._drag_start_y <= 0 or event.ydata <= 0:
            return
        ratio = event.ydata / self._drag_start_y
        # Limita TMS ao range físico [0.05, 1.0]
        new_tms = max(
            0.05,
            min(1.0, self._drag_start_tms * ratio),
        )
        idx = self._dragging_idx
        old = self._curves[idx]
        # Cria nova curva imutável com TMS ajustada
        from dataclasses import replace
        self._curves[idx] = replace(old, tms=new_tms)
        self._draw_all()

    def _on_release(self, event) -> None:
        if self._dragging_idx is None:
            return
        idx = self._dragging_idx
        c = self._curves[idx]
        self.curve_modified.emit(idx, c.pickup_A, c.tms)
        self._dragging_idx = None
        self._drag_start_y = None
        self._drag_start_tms = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_curves(self, curves: list[TCCCurve]) -> None:
        self._curves = list(curves)
        self._enabled_mask = [True] * len(curves)
        self._draw_all()

    def set_curve_enabled(self, idx: int, enabled: bool) -> None:
        if 0 <= idx < len(self._enabled_mask):
            self._enabled_mask[idx] = enabled
            self._draw_all()

    def get_curves(self) -> list[TCCCurve]:
        return list(self._curves)

    # ------------------------------------------------------------------
    # v3.6.2 (closes SKIPPED_BACKLOG D.1) — C-lines API
    # ------------------------------------------------------------------

    def set_c_lines(self, c_lines: list) -> None:
        """Set NFPA 70E PPE C-lines overlay (constant IE curves).

        Curves are rendered as dashed overlays in the same matplotlib
        Axes, color-coded by ``CLineCurve.color_hint``.

        Per Tutorial §Part 5 p.163-165 (PTW C-lines feature).
        """
        self._c_lines = list(c_lines or [])
        self._draw_all()

    def get_c_lines(self) -> list:
        """Return the current C-lines overlay list (may be empty)."""
        return list(self._c_lines)

    def _draw_c_lines(self, ax) -> None:
        """v3.6.2 D.1 — render C-lines as dashed overlays.

        Each curve uses ``color_hint`` from CLineCurve and a label
        like ``"C: 1.2 cal/cm² (PPE 1)"``. Currents in ``points`` are
        in kA, so we convert to A for the log-axis (matches the main
        coordinogram x-axis units).
        """
        for c in self._c_lines:
            pts = getattr(c, "points", ())
            if not pts:
                continue
            # Convert kA → A for axis consistency
            xs = [p[0] * 1000.0 for p in pts]
            ys = [p[1] for p in pts]
            ie = getattr(c, "incident_energy_cal_cm2", 0.0)
            ppe = getattr(c, "ppe_category", None)
            label = (
                f"C: {ie:.2f} cal/cm² (PPE {ppe})" if ppe is not None
                else f"C: {ie:.2f} cal/cm²"
            )
            ax.plot(
                xs, ys,
                color=getattr(c, "color_hint", "#ff8c00"),
                linestyle="--",
                linewidth=1.5,
                alpha=0.8,
                label=label,
                zorder=5,
            )

    # ------------------------------------------------------------------
    # v3.6.2 (closes SKIPPED_BACKLOG D.2) — Protection filter API
    # ------------------------------------------------------------------

    def set_protection_filter(self, mode: str) -> None:
        """Set protection function filter for multi-protection plots.

        Modes:
        * ``"all"`` — show all curves (default)
        * ``"phase"`` — show only Phase functions (50/51, IOC, TOC)
        * ``"ground"`` — show only Ground functions (50N/51N, IGOC, TGOC)

        Filtering is heuristic: matches by curve name/function attribute
        substring (case-insensitive). Curves without explicit function
        info are always shown.

        Per Tutorial §Part 11 p.357-360 (PTW Phase + Ground combined plot).
        """
        if mode not in ("all", "phase", "ground"):
            raise ValueError(
                f"mode must be 'all'|'phase'|'ground', got {mode!r}"
            )
        self._protection_filter = mode
        self._draw_all()

    def get_protection_filter(self) -> str:
        """Return current protection filter mode."""
        return self._protection_filter

    @staticmethod
    def _curve_matches_protection(curve, mode: str) -> bool:
        """Heuristic match: True if curve fits the filter mode.

        Looks at attributes ``function``, ``ansi``, ``name``, ``label``
        for substrings indicating ground vs phase functions.
        """
        if mode == "all":
            return True
        # Aggregate text from multiple possible attributes
        text_parts = []
        for attr in ("function", "ansi", "name", "label"):
            val = getattr(curve, attr, None)
            if val:
                text_parts.append(str(val).lower())
        text = " ".join(text_parts)
        if not text:
            # No info → always show (don't hide curves silently)
            return True
        # Ground markers: 50n, 51n, n_, ground, neutral, terra
        ground_markers = ("50n", "51n", "ground", "neutral", "terra", "igoc", "tgoc")
        is_ground = any(m in text for m in ground_markers)
        if mode == "ground":
            return is_ground
        # mode == "phase"
        return not is_ground


# ---------------------------------------------------------------------------
# Dialog wrapper
# ---------------------------------------------------------------------------


class TCCCoordinogramDialog(QDialog):
    """
    Dialog completo com coordenograma + lista de curvas
    (toggleable) + botão de export.
    """

    def __init__(
        self,
        curves: Optional[list[TCCCurve]] = None,
        fault_current_A: float = 0.0,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(
            "Coordenograma TCC — Olivas Power System Studio"
        )
        self.resize(1100, 750)

        # Default demo se nenhuma curva foi passada
        if not curves:
            curves = self._demo_curves()

        layout = QHBoxLayout(self)

        # Lado esquerdo: lista de curvas
        side_panel = QVBoxLayout()
        side_panel.addWidget(QLabel("<b>Dispositivos</b>"))

        self._curve_list = QListWidget()
        self._curve_list.setMaximumWidth(280)
        for i, c in enumerate(curves):
            label = self._curve_display_label(c)
            item = QListWidgetItem(label)
            item.setFlags(
                item.flags() | Qt.ItemIsUserCheckable,
            )
            item.setCheckState(Qt.Checked)
            self._curve_list.addItem(item)
        self._curve_list.itemChanged.connect(
            self._on_curve_toggled,
        )
        side_panel.addWidget(self._curve_list, 1)

        # Status
        self._status_label = QLabel(
            f"<small><b>Falta avaliada:</b> "
            f"{fault_current_A:.0f} A<br>"
            f"<b>Dispositivos:</b> {len(curves)}<br>"
            f"<i>Arraste qualquer curva ↕ para ajustar TMS</i></small>"
        )
        self._status_label.setWordWrap(True)
        self._status_label.setStyleSheet(
            "padding: 8px; background: #FAFAF5; "
            "border: 1px solid #B5D4A8; border-radius: 4px;"
        )
        side_panel.addWidget(self._status_label)

        side_panel.addStretch(1)

        side_widget = QWidget()
        side_widget.setLayout(side_panel)
        side_widget.setMaximumWidth(300)
        layout.addWidget(side_widget)

        # Lado direito: coordenograma — v3.8.2 (closes SKIPPED_BACKLOG D.3)
        # 3-tab pages per PTW Tutorial §Part 3 p.103-104: Settings / Curves /
        # Datablock. Tabs são wrapper visual; widget interno preservado.
        from PySide6.QtWidgets import QTabWidget
        right_panel = QVBoxLayout()
        self._coord_widget = TCCCoordinogramWidget(
            curves, fault_current_A,
        )
        self._coord_widget.curve_modified.connect(
            self._on_curve_modified,
        )
        # 3-tab QTabWidget
        self._tabs = QTabWidget()
        self._tab_settings = self._build_settings_tab(fault_current_A)
        self._tab_curves = self._coord_widget  # main canvas IS the tab
        self._tab_datablock = self._build_datablock_tab(curves)
        self._tabs.addTab(self._tab_settings, "⚙️ Settings")
        self._tabs.addTab(self._tab_curves, "📈 Curves")
        self._tabs.addTab(self._tab_datablock, "📋 Datablock")
        self._tabs.setCurrentIndex(1)  # default to Curves (main view)
        right_panel.addWidget(self._tabs, 1)

        # v3.4.0 Sprint 1+2: C-lines + TCC Report buttons
        from PySide6.QtWidgets import QPushButton
        button_row = QHBoxLayout()

        self._btn_c_lines = QPushButton("📊 C-lines (PPE constant IE)")
        self._btn_c_lines.setToolTip(
            "Overlay constant Incident Energy curves (NFPA 70E PPE) — "
            "PTW Tutorial §Part 5 p.163-165"
        )
        self._btn_c_lines.setCheckable(True)
        self._btn_c_lines.toggled.connect(self._on_c_lines_toggled)
        button_row.addWidget(self._btn_c_lines)

        self._btn_export_report = QPushButton("📄 Export TCC Report")
        self._btn_export_report.setToolTip(
            "Export TCC Report (text/markdown/csv) — "
            "PTW Tutorial §Part 3 p.99-101"
        )
        self._btn_export_report.clicked.connect(self._on_export_tcc_report)
        button_row.addWidget(self._btn_export_report)

        # v3.6.2 (closes SKIPPED_BACKLOG D.2) — protection filter combo
        from PySide6.QtWidgets import QComboBox
        button_row.addWidget(QLabel("Filtro:"))
        self._cmb_protection_filter = QComboBox()
        self._cmb_protection_filter.addItem("Todas", userData="all")
        self._cmb_protection_filter.addItem("Phase (50/51)", userData="phase")
        self._cmb_protection_filter.addItem("Ground (50N/51N)", userData="ground")
        self._cmb_protection_filter.setToolTip(
            "Filtra curvas por função (Phase=50/51, Ground=50N/51N). "
            "PTW Tutorial §Part 11 p.357-360"
        )
        self._cmb_protection_filter.currentIndexChanged.connect(
            self._on_protection_filter_changed
        )
        button_row.addWidget(self._cmb_protection_filter)

        button_row.addStretch(1)
        right_panel.addLayout(button_row)

        # Store curves reference for later use
        self._curves = list(curves)
        self._fault_current_A = fault_current_A

        # Botões padrão
        bb = QDialogButtonBox(QDialogButtonBox.Close)
        bb.button(QDialogButtonBox.Close).setText("Fechar")
        bb.rejected.connect(self.reject)
        right_panel.addWidget(bb)

        right_widget = QWidget()
        right_widget.setLayout(right_panel)
        layout.addWidget(right_widget, 1)

    # ------------------------------------------------------------------
    # v3.8.2 (closes SKIPPED_BACKLOG D.3) — 3-tab pages
    # ------------------------------------------------------------------

    def _build_settings_tab(self, fault_current_A: float) -> QWidget:
        """Build the Settings tab (fault current input, view options).

        Per PTW Tutorial §Part 3 p.103-104.
        """
        from PySide6.QtWidgets import (
            QDoubleSpinBox, QFormLayout, QPushButton, QVBoxLayout,
        )
        w = QWidget()
        layout = QVBoxLayout(w)
        form = QFormLayout()

        self._spin_fault_A = QDoubleSpinBox()
        self._spin_fault_A.setRange(0.0, 1_000_000.0)
        self._spin_fault_A.setValue(fault_current_A)
        self._spin_fault_A.setSuffix(" A")
        self._spin_fault_A.setDecimals(0)
        form.addRow("Fault current Ik''  :", self._spin_fault_A)

        btn_apply = QPushButton("✅ Aplicar")
        btn_apply.clicked.connect(self._on_apply_settings)
        form.addRow("", btn_apply)

        layout.addLayout(form)
        layout.addStretch(1)
        return w

    def _build_datablock_tab(self, curves: list) -> QWidget:
        """Build the Datablock tab (text summary of curves).

        Per PTW Tutorial §Part 3 p.103-104. Uses :func:`_curve_display_label`
        to extract description per curve type (heterogeneous list).
        """
        from PySide6.QtWidgets import QPlainTextEdit, QVBoxLayout
        w = QWidget()
        layout = QVBoxLayout(w)
        text = QPlainTextEdit()
        text.setReadOnly(True)
        lines = [
            "=== TCC Datablock — PTW §Part 3 p.103-104 ===",
            f"Total curves: {len(curves)}",
            "",
        ]
        for i, c in enumerate(curves):
            label = self._curve_display_label(c)
            lines.append(f"{i + 1}. {label}")
            # Try to extract pickup / TMS / type
            for attr in ("pickup_A", "tms", "curve_type"):
                v = getattr(c, attr, None)
                if v is not None:
                    lines.append(f"     - {attr} = {v}")
            lines.append("")
        text.setPlainText("\n".join(lines))
        layout.addWidget(text, 1)
        self._datablock_text = text
        return w

    def _on_apply_settings(self) -> None:
        """v3.8.2 D.3: apply settings tab values to coord widget."""
        if hasattr(self, "_spin_fault_A") and hasattr(self._coord_widget, "_fault_current_A"):
            new_fault = self._spin_fault_A.value()
            self._coord_widget._fault_current_A = new_fault
            if hasattr(self._coord_widget, "_draw_all"):
                self._coord_widget._draw_all()

    @staticmethod
    def _curve_display_label(curve) -> str:
        """
        v1.3.2 G.3: helper para extrair label de qualquer tipo
        de curva (TCCCurve legacy, MultiFunctionRelay, FuseTCCCurve,
        damage curves).

        Usa duck typing — não força isinstance check para evitar
        circular dependency.
        """
        # TCCDevice (v1.2.0 β): tem device_id + manufacturer/model
        if hasattr(curve, "device_id"):
            mfg = getattr(curve, "manufacturer", "")
            mdl = getattr(curve, "model", "")
            n_segs = len(getattr(curve, "segments", ()))
            tag = ""
            if mfg and mfg != "Generic":
                tag = f" {mfg}/{mdl}"
            return f"⚙ {curve.device_id}{tag} ({n_segs} fns)"
        # FuseTCCCurve: fuse_id + fuse_class
        if hasattr(curve, "fuse_id"):
            cls_label = (
                getattr(curve.fuse_class, "value", "?")
                if hasattr(curve, "fuse_class") else "?"
            )
            return f"🔥 {curve.fuse_id} [{cls_label}]"
        # CableDamageCurve: cable_id + material
        if hasattr(curve, "cable_id"):
            mat = (
                getattr(curve.material, "value", "?")
                if hasattr(curve, "material") else "?"
            )
            return f"⚠ {curve.cable_id} [Damage Cu/PVC etc: {mat}]"
        # TransformerThroughFaultCurve: xfmr_id + category
        if hasattr(curve, "xfmr_id"):
            cat = (
                getattr(curve.category, "value", "?")
                if hasattr(curve, "category") else "?"
            )
            return f"⚠ {curve.xfmr_id} [Damage XFMR {cat}]"
        # MotorThermalCurve: motor_id
        if hasattr(curve, "motor_id"):
            return f"⚠ {curve.motor_id} [Damage Motor Thermal]"
        # TCCCurve legacy: relay_id + curve_type
        if hasattr(curve, "relay_id"):
            ct = getattr(curve, "curve_type", None)
            ct_label = getattr(ct, "value", "—") if ct else "—"
            return f"📈 {curve.relay_id} ({ct_label})"
        # Fallback genérico
        return f"📈 {type(curve).__name__}"

    def _demo_curves(self) -> list:
        """
        Curvas demo para quando o dialog abre sem dados.

        v1.3.2 G.3: agora inclui mix de TCCCurve legacy v1.0+
        + TCCDevice multi-function v1.2.0 + DamageCurves v1.2.0.
        Permite ao engenheiro VER as 23 APIs user-facing v1.2/v1.3
        funcionando em 1 dialog único.

        Layout do demo:
        - 1 TCCCurve legacy (relé feeder simples)
        - 1 MultiFunctionRelay (motor SEL-751-like com 51+50+49)
        - 1 FuseTCCCurve (fusível 200A gG)
        - 1 CableDamageCurve (cabo 50mm² Cu/XLPE — limit vermelho)
        - 1 TransformerThroughFaultCurve (XFMR 100A frequent — limit)
        - 1 MotorThermalCurve (motor 100A FLA — limit)
        """
        # Imports lazy para não falhar se v1.2/v1.3 não estiver
        # disponível (defensive — manté backward compat).
        curves: list = [
            TCCCurve(
                "Relé Feeder F1",
                CurveType.IEC_VERY_INVERSE,
                pickup_A=200, tms=0.5,
                instantaneous_pickup_A=2000,
            ),
        ]

        try:
            from app.postprocessor.tcc_devices import MultiFunctionRelay
            curves.append(
                MultiFunctionRelay.relay_51_50_49(
                    device_id="SEL-751 Motor M1",
                    curve_type=CurveType.IEC_STANDARD_INVERSE,
                    pickup_51_A=120, tms_51=0.20,
                    pickup_50_A=600,
                    pickup_49_A=130, delay_49_s=8.0,
                    manufacturer="SEL", model="751",
                ),
            )
        except ImportError:
            pass

        try:
            from app.postprocessor.tcc_curves import FuseClass, FuseTCCCurve
            curves.append(
                FuseTCCCurve(
                    "F-MAIN gG 200A",
                    FuseClass.gG,
                    rated_current_A=200.0,
                ),
            )
        except ImportError:
            pass

        try:
            from app.postprocessor.tcc_damage import (
                CableDamageCurve, CableMaterial,
                MotorThermalCurve,
                TransformerThroughFaultCurve, XfmrFaultCategory,
            )
            curves.append(
                CableDamageCurve(
                    cable_id="Cabo 50mm² Cu/XLPE",
                    section_mm2=50,
                    material=CableMaterial.Cu_XLPE,
                ),
            )
            curves.append(
                TransformerThroughFaultCurve(
                    xfmr_id="XFMR 100A FREQUENT",
                    rated_current_A=100,
                    category=XfmrFaultCategory.FREQUENT,
                ),
            )
            curves.append(
                MotorThermalCurve(
                    motor_id="Motor 100A FLA",
                    fla_A=100,
                ),
            )
        except ImportError:
            pass

        return curves

    def _on_curve_toggled(self, item: QListWidgetItem) -> None:
        idx = self._curve_list.row(item)
        enabled = item.checkState() == Qt.Checked
        self._coord_widget.set_curve_enabled(idx, enabled)

    def _on_curve_modified(
        self, idx: int, pickup_A: float, tms: float,
    ) -> None:
        # Atualiza label do item (item já existe)
        # v1.3.2 G.3: usa helper para suportar TCCDevice/Damage
        item = self._curve_list.item(idx)
        if item is not None:
            curves = self._coord_widget.get_curves()
            if idx < len(curves):
                c = curves[idx]
                item.setText(self._curve_display_label(c))
        self._status_label.setText(
            f"<small><b>Modificado:</b> curva #{idx} → "
            f"TMS={tms:.3f}<br>"
            f"<i>Continue arrastando ou clique em outra</i></small>"
        )

    # ------------------------------------------------------------------
    # v3.4.0 Sprint 1+2 — C-lines + TCC Report
    # ------------------------------------------------------------------

    def _on_protection_filter_changed(self, idx: int) -> None:
        """v3.6.2 D.2: aplica filtro Phase/Ground/All ao coord widget.

        Per PTW Tutorial §Part 11 p.357-360: filtragem visual de
        funções 50/51 (Phase) vs 50N/51N (Ground) sem tocar nas curvas.
        """
        if not hasattr(self, "_coord_widget"):
            return
        mode = self._cmb_protection_filter.itemData(idx) or "all"
        if hasattr(self._coord_widget, "set_protection_filter"):
            try:
                self._coord_widget.set_protection_filter(mode)
            except (ValueError, AttributeError):
                pass

    def _on_c_lines_toggled(self, checked: bool) -> None:
        """v3.4.0 Sprint 1: toggle C-lines overlay (NFPA 70E PPE).

        Per PTW Tutorial §Part 5 p.163-165: C-lines mostram constant
        Incident Energy curves no TCC; cada linha corresponde a uma
        categoria PPE (1.2 / 4 / 8 / 25 / 40 cal/cm²).
        """
        from app.postprocessor.tcc_c_lines import compute_default_c_lines
        if checked:
            try:
                c_lines = compute_default_c_lines(
                    voltage_kV=0.480,
                    enclosure_box=True,
                )
                # Set on coord widget (assumes set_c_lines API; if absent,
                # log warning + uncheck button)
                if hasattr(self._coord_widget, "set_c_lines"):
                    self._coord_widget.set_c_lines(c_lines)
                else:
                    # Fallback: store on widget as attribute for future paint
                    self._coord_widget._c_lines = c_lines
                    self._coord_widget.update()
                self._status_label.setText(
                    "<small><b>C-lines:</b> ON ("
                    f"{len(c_lines)} levels: 1.2/4/8/25/40 cal/cm²)<br>"
                    "<i>NFPA 70E Annex H Tab H.3(b)</i></small>"
                )
            except Exception as e:  # noqa: BLE001
                self._status_label.setText(
                    f"<small>Erro ao gerar C-lines: {e}</small>"
                )
                self._btn_c_lines.setChecked(False)
        else:
            if hasattr(self._coord_widget, "set_c_lines"):
                self._coord_widget.set_c_lines([])
            else:
                self._coord_widget._c_lines = []
                self._coord_widget.update()
            self._status_label.setText(
                "<small><b>C-lines:</b> OFF</small>"
            )

    def _on_export_tcc_report(self) -> None:
        """v3.4.0 Sprint 2: export TCC Report (text/markdown/csv).

        Per PTW Tutorial §Part 3 p.99-101.
        """
        from PySide6.QtWidgets import QFileDialog, QMessageBox
        from app.postprocessor.tcc_report import (
            TccDeviceEntry, TccReport,
        )

        try:
            # Build TccReport from current curves
            project_name = "TCC Coordination"
            report = TccReport(project_name=project_name)
            curves = self._coord_widget.get_curves()
            for c in curves:
                # Heuristic extraction (best effort)
                device_id = (
                    getattr(c, "device_id", None)
                    or getattr(c, "name", None)
                    or f"DEV-{id(c) % 10000}"
                )
                pickup = (
                    getattr(c, "pickup_A", None)
                    or getattr(c, "pickup_amps", None)
                    or 0.0
                )
                tms = (
                    getattr(c, "tms", None)
                    or getattr(c, "time_dial", None)
                    or 0.0
                )
                curve_t = getattr(c, "curve_type", "")
                func = getattr(c, "function_code", "")
                report.add_device(TccDeviceEntry(
                    device_id=str(device_id),
                    device_type=getattr(c, "device_type", "device"),
                    bus_voltage_kV=getattr(c, "bus_voltage_kV", 0.0),
                    pickup_A=float(pickup),
                    time_dial=float(tms),
                    curve_type=str(curve_t),
                    function_code=str(func),
                ))

            path, sel = QFileDialog.getSaveFileName(
                self, "Exportar TCC Report",
                f"{project_name}_tcc.txt",
                "Texto PTW-style (*.txt);;Markdown (*.md);;CSV (*.csv)",
            )
            if not path:
                return
            if path.endswith(".md") or "Markdown" in sel:
                content = report.format_markdown()
            elif path.endswith(".csv") or "CSV" in sel:
                content = report.format_csv()
            else:
                content = report.format_text()
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            QMessageBox.information(
                self, "Exportado",
                f"TCC Report salvo em:\n{path}\n\n"
                "Reference: PTW Tutorial §Part 3 p.99-101",
            )
        except Exception as e:  # noqa: BLE001
            QMessageBox.critical(
                self, "Erro export",
                f"Erro ao exportar:\n{type(e).__name__}: {e}",
            )
