"""
app.gui.plot_widgets — widgets matplotlib dockable para
visualização interativa de resultados (v0.35).

3 widgets profissionais:

1. **PowerFlowVoltageProfile**: barras de tensão por bus
   com linhas de limite (0.95 / 1.05 pu).

2. **ScContributionPie**: pie chart de contribuições
   percentuais por fonte (gerador / utility / motor).

3. **TccCurveOverlay**: log-log plot de curvas TC de
   relés sobrepostas, com pickup markers e Δt entre
   relés.

Cada widget é ``QDockWidget`` autônomo, populado via
``set_data(...)``. Exporta:

* ``save_png(path)`` — salvar como PNG.
* ``copy_to_clipboard()`` — para colar em relatórios.

Tema: respeita dark/light mode do MainWindow via
``apply_theme(is_dark)``.
"""

from __future__ import annotations

import math
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QFont
from PySide6.QtWidgets import (
    QDockWidget, QHBoxLayout, QLabel, QPushButton,
    QStackedWidget, QVBoxLayout, QWidget,
)


# ---------------------------------------------------------------------------
# Base helper
# ---------------------------------------------------------------------------


class _BasePlotDock(QDockWidget):
    """
    Base para QDockWidget com matplotlib FigureCanvas.

    Subclasses implementam ``_render(ax, **data)``.
    """

    def __init__(self, title: str, parent: Optional[QWidget] = None):
        super().__init__(title, parent)
        self.setObjectName(f"dock_{title.lower().replace(' ', '_')}")
        self.setAllowedAreas(Qt.AllDockWidgetAreas)

        from matplotlib.backends.backend_qt5agg import (
            FigureCanvasQTAgg as FigureCanvas,
            NavigationToolbar2QT as NavigationToolbar,
        )
        from matplotlib.figure import Figure

        container = QWidget(self)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(2)

        # v1.4.5 — Empty state usa QStackedWidget: empty label vs plot
        self._stack = QStackedWidget(container)

        # Page 0: Empty state (label central explicativo)
        self._empty_state_label = QLabel()
        self._empty_state_label.setAlignment(Qt.AlignCenter)
        self._empty_state_label.setWordWrap(True)
        self._empty_state_label.setStyleSheet(
            "QLabel { background-color: #FAFAFA; "
            "border: 1px dashed #BDBDBD; "
            "padding: 24px; color: #424242; }"
        )
        font = QFont()
        font.setPointSize(11)
        self._empty_state_label.setFont(font)
        self._stack.addWidget(self._empty_state_label)   # index 0

        # Page 1: Plot canvas + toolbar (criado lazy abaixo)
        plot_page = QWidget()
        plot_layout = QVBoxLayout(plot_page)
        plot_layout.setContentsMargins(0, 0, 0, 0)
        plot_layout.setSpacing(2)

        self._figure = Figure(figsize=(6, 4), tight_layout=True)
        self._canvas = FigureCanvas(self._figure)
        self._toolbar = NavigationToolbar(self._canvas, plot_page)
        plot_layout.addWidget(self._toolbar)
        plot_layout.addWidget(self._canvas, 1)
        self._stack.addWidget(plot_page)   # index 1

        layout.addWidget(self._stack, 1)

        # Action buttons (sempre visíveis)
        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(2, 0, 2, 0)
        btn_save = QPushButton("Salvar PNG")
        btn_save.clicked.connect(self._on_save_png)
        btn_row.addWidget(btn_save)
        btn_copy = QPushButton("Copiar")
        btn_copy.clicked.connect(self._on_copy)
        btn_row.addWidget(btn_copy)
        btn_row.addStretch(1)
        layout.addLayout(btn_row)

        self.setWidget(container)
        self._is_dark = False
        # Inicia em empty state (subclasse chama show_empty_state)
        self._stack.setCurrentIndex(0)

    # -----------------------------------------------------------------
    # v1.4.5 — Empty state API
    # -----------------------------------------------------------------

    def show_empty_state(self, html_msg: str) -> None:
        """
        v1.4.5 (paridade Datablock Reports do PTW): exibe mensagem
        explicativa quando o dock está sem dados (em vez de plot
        vazio).

        ``html_msg`` aceita HTML simples (quebras de linha <br>,
        negrito <b>, etc) — replicando o padrão dos guias PTW.
        """
        self._empty_state_label.setText(html_msg)
        self._stack.setCurrentIndex(0)

    def _show_plot(self) -> None:
        """Comuta para a página do plot (chamado por set_data)."""
        self._stack.setCurrentIndex(1)

    def is_empty(self) -> bool:
        """Retorna True se o dock está em empty state."""
        return self._stack.currentIndex() == 0

    def apply_theme(self, is_dark: bool) -> None:
        """Aplica tema dark/light ao matplotlib."""
        self._is_dark = is_dark
        bg = "#202030" if is_dark else "white"
        fg = "#e0e0e0" if is_dark else "black"
        self._figure.patch.set_facecolor(bg)
        for ax in self._figure.axes:
            ax.set_facecolor(bg)
            ax.tick_params(colors=fg)
            ax.spines["bottom"].set_color(fg)
            ax.spines["top"].set_color(fg)
            ax.spines["left"].set_color(fg)
            ax.spines["right"].set_color(fg)
            ax.title.set_color(fg)
            ax.xaxis.label.set_color(fg)
            ax.yaxis.label.set_color(fg)
        self._canvas.draw_idle()

    def _on_save_png(self) -> None:
        from PySide6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getSaveFileName(
            self, "Salvar plot como PNG", "", "PNG (*.png)",
        )
        if path:
            self.save_png(path)

    def save_png(self, path: str) -> None:
        """Salva figure em PNG."""
        self._figure.savefig(path, dpi=150, bbox_inches="tight")

    def _on_copy(self) -> None:
        """Copia figure pro clipboard como imagem."""
        from PySide6.QtGui import QImage
        import io
        from PySide6.QtWidgets import QApplication
        buf = io.BytesIO()
        self._figure.savefig(buf, format="png", dpi=150, bbox_inches="tight")
        buf.seek(0)
        img = QImage()
        img.loadFromData(buf.getvalue(), "PNG")
        QApplication.clipboard().setImage(img)

    def _clear(self):
        self._figure.clear()


# ---------------------------------------------------------------------------
# 1. Power Flow voltage profile
# ---------------------------------------------------------------------------


class PowerFlowVoltageProfileDock(_BasePlotDock):
    """
    Voltage profile chart — barras horizontais com limites
    operacionais marcados (0.95 / 1.05 pu).

    set_data signature:
    ``set_data(bus_ids: list[str], voltages_pu: list[float])``
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__("Power Flow — Voltage Profile", parent)
        self.show_empty_state(
            "<h3>📊 Perfil de Tensão (Power Flow)</h3>"
            "<p>Esta janela mostra <b>V/V_nom por barramento</b> "
            "após executar Power Flow (IEEE 399).</p>"
            "<p><b>Como popular:</b><br>"
            "1. Pressione <b>F5</b> (Executar Análise)<br>"
            "2. Marque <b>Power Flow</b><br>"
            "3. Clique <b>Executar</b></p>"
            "<p><i>Limites IEEE 1547 / NBR 5410: 0.95 ≤ V_pu ≤ 1.05</i></p>"
        )

    def set_data(
        self, bus_ids: list[str], voltages_pu: list[float],
    ) -> None:
        self._clear()
        ax = self._figure.add_subplot(111)

        n = len(bus_ids)
        if n == 0:
            self.show_empty_state(
                "<h3>📊 Perfil de Tensão</h3>"
                "<p>Power Flow rodou mas <b>não retornou buses</b>. "
                "Verifique se o esquemático tem fontes conectadas.</p>"
            )
            return
        # Mostra plot
        self._show_plot()

        positions = list(range(n))
        # Cor por status (verde/laranja/vermelho)
        colors = []
        for v in voltages_pu:
            if 0.95 <= v <= 1.05:
                colors.append("#2ca02c")    # verde
            elif 0.90 <= v < 0.95 or 1.05 < v <= 1.10:
                colors.append("#ff7f0e")    # laranja
            else:
                colors.append("#d62728")    # vermelho

        ax.barh(positions, voltages_pu, color=colors, edgecolor="black")
        ax.set_yticks(positions)
        ax.set_yticklabels(bus_ids)
        ax.invert_yaxis()
        ax.set_xlabel("Tensão (pu)")
        ax.set_title("Voltage Profile by Bus")
        ax.set_xlim(0.85, 1.15)
        # Limites
        ax.axvline(0.95, color="orange", linestyle="--",
                   linewidth=1, alpha=0.7, label="0.95 pu (limite mín)")
        ax.axvline(1.05, color="orange", linestyle="--",
                   linewidth=1, alpha=0.7, label="1.05 pu (limite máx)")
        ax.axvline(1.00, color="gray", linestyle=":",
                   linewidth=0.8, alpha=0.5)
        ax.legend(loc="lower right", fontsize=8)
        ax.grid(axis="x", linestyle=":", alpha=0.4)

        # Anotação de valores
        for i, v in enumerate(voltages_pu):
            ax.text(v + 0.005, i, f"{v:.4f}",
                    va="center", fontsize=8)

        self.apply_theme(self._is_dark)
        self._canvas.draw_idle()


# ---------------------------------------------------------------------------
# 2. SC contribution pie chart
# ---------------------------------------------------------------------------


class ScContributionPieDock(_BasePlotDock):
    """
    Pie chart de contribuição percentual de cada fonte SC.

    set_data signature:
    ``set_data(contributions: dict[str, float])``  — frações
    {nome_fonte: 0..1}, soma ≈ 1.
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__("SC — Source Contributions", parent)
        self.show_empty_state(
            "<h3>🥧 Contribuição das Fontes (Curto-Circuito)</h3>"
            "<p>Esta janela mostra a <b>fração percentual de cada fonte</b> "
            "(geradores, utility, motores) na corrente de falta total.</p>"
            "<p><b>Como popular:</b><br>"
            "1. Pressione <b>F5</b> (Executar Análise)<br>"
            "2. Marque <b>Curto-circuito (IEC 60909)</b><br>"
            "3. Clique <b>Executar</b></p>"
            "<p><i>Útil para identificar quais fontes contribuem mais "
            "para o pico de falta (Ip).</i></p>"
        )

    def set_data(self, contributions: dict) -> None:
        self._clear()
        ax = self._figure.add_subplot(111)

        if not contributions:
            self.show_empty_state(
                "<h3>🥧 Contribuição das Fontes</h3>"
                "<p>Análise SC rodou mas <b>nenhuma fonte foi identificada</b>. "
                "Verifique se há geradores/utility/motores no esquemático.</p>"
            )
            return
        self._show_plot()

        labels = list(contributions.keys())
        sizes = [contributions[k] for k in labels]
        # Cores consistentes com paleta tableau10
        colors = [
            "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728",
            "#9467bd", "#8c564b", "#e377c2", "#7f7f7f",
        ]
        n = len(sizes)
        pie_colors = [colors[i % len(colors)] for i in range(n)]

        wedges, texts, autotexts = ax.pie(
            sizes, labels=labels, colors=pie_colors,
            autopct="%1.1f%%", startangle=90,
            wedgeprops={"edgecolor": "white", "linewidth": 1.5},
        )
        for at in autotexts:
            at.set_color("white")
            at.set_fontsize(9)
            at.set_fontweight("bold")
        ax.set_title("Short-Circuit Source Contributions")

        self.apply_theme(self._is_dark)
        self._canvas.draw_idle()


# ---------------------------------------------------------------------------
# 3. TCC curve overlay
# ---------------------------------------------------------------------------


class TccCurveOverlayDock(_BasePlotDock):
    """
    Time-current characteristic overlay (log-log).

    set_data signature:
    ``set_data(curves: list[dict])``  onde cada dict:
    ``{"name": str, "currents_A": list[float],
       "times_s": list[float], "color": str (opcional),
       "linestyle": str (opcional)}``

    Adiciona automaticamente:
    * Eixo log-log (current × time).
    * Grid log-log.
    * Legend com nomes dos relés.
    * Anotação opcional de pickup (vertical line).
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__("TCC — Coordination Curves", parent)
        self.show_empty_state(
            "<h3>📉 Curvas de Coordenação (TCC)</h3>"
            "<p>Esta janela mostra <b>curvas tempo-corrente sobrepostas</b> "
            "dos relés/fusíveis em escala log-log, com pickup markers e "
            "Δt de seletividade.</p>"
            "<p><b>Como popular:</b><br>"
            "1. Pressione <b>F5</b> (Executar Análise)<br>"
            "2. Marque <b>Coordenação e Seletividade (IEEE 242)</b><br>"
            "3. Clique <b>Executar</b></p>"
            "<p><i>Para visualização completa do coordinograma, "
            "use Análise → Coordenação → Coordinograma.</i></p>"
        )

    def set_data(
        self, curves: list,
        *,
        fault_current_kA: Optional[float] = None,
    ) -> None:
        self._clear()
        ax = self._figure.add_subplot(111)

        if not curves:
            self.show_empty_state(
                "<h3>📉 Curvas de Coordenação</h3>"
                "<p>Análise rodou mas <b>nenhuma curva TC foi gerada</b>. "
                "Verifique se há relés configurados no esquemático.</p>"
            )
            return
        self._show_plot()

        default_colors = [
            "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728",
            "#9467bd",
        ]
        for i, curve in enumerate(curves):
            name = curve.get("name", f"Relay {i+1}")
            currents = curve.get("currents_A", [])
            times = curve.get("times_s", [])
            color = curve.get("color", default_colors[i % len(default_colors)])
            linestyle = curve.get("linestyle", "-")
            if currents and times:
                ax.plot(
                    currents, times, label=name,
                    color=color, linestyle=linestyle,
                    linewidth=2,
                )

        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlabel("Corrente (A)")
        ax.set_ylabel("Tempo (s)")
        ax.set_title("Time-Current Coordination")
        ax.grid(True, which="both", linestyle=":", alpha=0.5)
        ax.legend(loc="upper right", fontsize=9)

        # Linha vertical para fault_current
        if fault_current_kA and fault_current_kA > 0:
            ax.axvline(
                fault_current_kA * 1000, color="red", linestyle="--",
                linewidth=1.5, alpha=0.7,
                label=f"Ik''={fault_current_kA:.1f} kA",
            )
            ax.legend(loc="upper right", fontsize=9)

        # Limites razoáveis
        ax.set_ylim(0.01, 100)
        if curves and curves[0].get("currents_A"):
            all_I = [
                I for c in curves for I in c.get("currents_A", [])
                if I > 0
            ]
            if all_I:
                ax.set_xlim(min(all_I) * 0.5, max(all_I) * 2)

        self.apply_theme(self._is_dark)
        self._canvas.draw_idle()


# ---------------------------------------------------------------------------
# 4. Monte Carlo histogram (v0.44 integration bonus)
# ---------------------------------------------------------------------------


class MonteCarloHistogramDock(_BasePlotDock):
    """
    Histograma de E (energia incidente) Monte Carlo + linhas
    P50/P95/P99 e categoria PPE.

    set_data signature:
    ``set_data(samples_J_per_cm2: list[float],
               P50: float, P95: float, P99: float)``
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__("Monte Carlo — Arc-Flash E", parent)
        self.show_empty_state(
            "<h3>🎲 Histograma Monte Carlo (Arc-Flash)</h3>"
            "<p>Esta janela mostra a <b>distribuição de probabilidade "
            "da energia incidente</b> (cal/cm²) com linhas P50/P95/P99 "
            "e categorias NFPA 70E PPE.</p>"
            "<p><b>Como popular:</b><br>"
            "1. Pressione <b>F5</b> (Executar Análise)<br>"
            "2. Marque <b>Arc-flash (NBR 17227 / IEEE 1584)</b><br>"
            "3. Marque <b>Reliability Monte Carlo</b><br>"
            "4. Clique <b>Executar</b></p>"
            "<p><i>P95 é o critério recomendado para PPE selection.</i></p>"
        )

    def set_data(
        self, samples_J_per_cm2: list,
        P50: float, P95: float, P99: float,
    ) -> None:
        self._clear()
        ax = self._figure.add_subplot(111)

        if not samples_J_per_cm2:
            self.show_empty_state(
                "<h3>🎲 Histograma Monte Carlo</h3>"
                "<p>Análise Monte Carlo rodou mas <b>nenhuma amostra "
                "foi gerada</b>. Verifique a configuração de N_samples.</p>"
            )
            return
        self._show_plot()

        # Histograma em cal/cm² (mais intuitivo)
        samples_cal = [s / 4.184 for s in samples_J_per_cm2]
        ax.hist(samples_cal, bins=40, color="#1f77b4",
                edgecolor="white", alpha=0.85)
        ax.set_xlabel("Energia incidente E (cal/cm²)")
        ax.set_ylabel("Frequência")
        ax.set_title("Distribuição Monte Carlo de E")

        # Linhas de percentis
        ax.axvline(
            P50 / 4.184, color="green", linestyle="-",
            linewidth=2, label=f"P50 = {P50/4.184:.2f}",
        )
        ax.axvline(
            P95 / 4.184, color="orange", linestyle="--",
            linewidth=2, label=f"P95 = {P95/4.184:.2f}",
        )
        ax.axvline(
            P99 / 4.184, color="red", linestyle="--",
            linewidth=2, label=f"P99 = {P99/4.184:.2f}",
        )

        # Linhas de Cat PPE
        for cat_value, cat_label in [
            (1.2, "Cat 0/1"), (4.0, "Cat 1/2"),
            (8.0, "Cat 2/3"), (25.0, "Cat 3/4"),
            (40.0, "Cat 4/DANGER"),
        ]:
            if cat_value < max(samples_cal) * 1.1:
                ax.axvline(
                    cat_value, color="gray", linestyle=":",
                    linewidth=1, alpha=0.5,
                )
                ax.text(
                    cat_value, ax.get_ylim()[1] * 0.95,
                    cat_label, rotation=90,
                    va="top", ha="right", fontsize=7, color="gray",
                )

        ax.legend(loc="upper right", fontsize=9)
        ax.grid(axis="y", linestyle=":", alpha=0.4)

        self.apply_theme(self._is_dark)
        self._canvas.draw_idle()

    def populate_from_cache(self, cache) -> None:
        """v1.7.0: extrai amostras MC do cache se disponíveis."""
        # Monte Carlo arc-flash não é cacheado canonicamente em
        # StudyCache (ainda); placeholder mantém empty state.
        # Quando cache.has_montecarlo() existir, popular aqui.
        if hasattr(cache, "has_montecarlo") and cache.has_montecarlo():
            r = cache.get_montecarlo()
            if r and getattr(r, "samples_J_per_cm2", None):
                self.set_data(
                    samples_J_per_cm2=r.samples_J_per_cm2,
                    P50=r.P50,
                    P95=r.P95,
                    P99=r.P99,
                )


# ---------------------------------------------------------------------------
# v1.7.0 Sprint C — populate_from_cache for the other 3 docks
# (added at module bottom to avoid touching original implementations
# above; method-injection pattern keeps anti-perda guarantee)
# ---------------------------------------------------------------------------


def _pf_populate_from_cache(self, cache) -> None:
    """Popula PowerFlowVoltageProfileDock a partir de StudyCache."""
    if not hasattr(cache, "has_pf") or not cache.has_pf():
        return   # mantém empty state
    pf = cache.get_pf()
    if pf is None:
        return
    bus_voltages = getattr(pf, "bus_voltages_pu", None)
    if not bus_voltages:
        return
    bus_ids = list(bus_voltages.keys())
    voltages = [
        abs(v) if isinstance(v, complex) else float(v)
        for v in bus_voltages.values()
    ]
    self.set_data(bus_ids, voltages)


def _sc_populate_from_cache(self, cache) -> None:
    """Popula ScContributionPieDock a partir de StudyCache.

    SC é cacheado por bus_id; populamos com o último (qualquer) bus
    que tem resultado SC com source_contributions.
    """
    if not hasattr(cache, "_sc"):
        return
    for bus_id, entry in cache._sc.items():
        result = entry.result
        contribs = getattr(result, "source_contributions", None)
        if contribs:
            self.set_data(contribs)
            return


def _tcc_populate_from_cache(self, cache) -> None:
    """Popula TccCurveOverlayDock a partir de StudyCache (Coordination)."""
    if not hasattr(cache, "_coord"):
        return
    for bus_id, entry in cache._coord.items():
        result = entry.result
        curves = getattr(result, "tcc_curves", None)
        if curves:
            self.set_data(curves)
            return


# Method injection (anti-perda: NÃO modifica classes originalmente
# definidas, só injeta novo método)
PowerFlowVoltageProfileDock.populate_from_cache = _pf_populate_from_cache
ScContributionPieDock.populate_from_cache = _sc_populate_from_cache
TccCurveOverlayDock.populate_from_cache = _tcc_populate_from_cache
