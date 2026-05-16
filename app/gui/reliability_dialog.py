"""v3.6.0 — ReliabilityDialog (Tier 1 PTW Tutorial §Part 10).

Dialog para inserção manual de eventos de interrupção e cálculo dos
índices IEEE 1366-2012 (SAIFI/SAIDI/CAIDI/ASAI).

Wired in MainWindow menu Análise (per Master Protocol garantia 7).

Reference
---------
* PTW Tutorial v8.0 §Part 10 — Reliability assessment
* IEEE Std 1366-2012 — Reliability indices definitions
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.postprocessor.reliability import (
    InterruptionEvent,
    calculate_indices,
)


class ReliabilityDialog(QDialog):
    """Reliability indices calculator dialog (closes Tier 1 §Part 10).

    User adds interruption events (customers_interrupted, duration),
    sets total_customers, clicks "Calcular" — indices SAIFI/SAIDI/CAIDI/
    ASAI são exibidos em texto formato.

    Acessibilidade: wired no menu Análise via MainWindow
    (Master Protocol garantia 7ª).
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Reliability Indices (IEEE 1366-2012)")
        self.setModal(True)
        self.setMinimumSize(640, 480)

        # --- header --------------------------------------------------------
        header = QLabel(
            "<b>📊 Reliability Indices</b> — IEEE Std 1366-2012<br>"
            "Adicione eventos de interrupção e clique <b>Calcular</b>."
        )
        header.setTextFormat(Qt.RichText)

        # --- total customers ----------------------------------------------
        self._total_customers_spin = QSpinBox()
        self._total_customers_spin.setRange(1, 10_000_000)
        self._total_customers_spin.setValue(1000)
        self._total_customers_spin.setSuffix(" clientes")

        cust_row = QHBoxLayout()
        cust_row.addWidget(QLabel("Clientes totais (N_T):"))
        cust_row.addWidget(self._total_customers_spin)
        cust_row.addStretch(1)
        cust_w = QWidget()
        cust_w.setLayout(cust_row)

        # --- events table --------------------------------------------------
        self._table = QTableWidget(0, 3)
        self._table.setHorizontalHeaderLabels([
            "Clientes interrompidos (N_i)",
            "Duração (horas)",
            "Descrição",
        ])
        self._table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch
        )

        add_btn = QPushButton("➕ Adicionar evento")
        add_btn.clicked.connect(self._on_add_row)
        del_btn = QPushButton("➖ Remover selecionado")
        del_btn.clicked.connect(self._on_del_row)
        clear_btn = QPushButton("🗑 Limpar")
        clear_btn.clicked.connect(self._on_clear)
        calc_btn = QPushButton("📈 Calcular")
        calc_btn.setDefault(True)
        calc_btn.clicked.connect(self._on_calculate)

        # v3.8.0 — Monte Carlo button
        mc_btn = QPushButton("🎲 Monte Carlo (IEEE 493 presets)")
        mc_btn.setToolTip(
            "Roda simulação Monte Carlo time-series usando IEEE 493 "
            "presets típicos. Mostra mean ± 90% CI para SAIFI/SAIDI/CAIDI/ASAI."
        )
        mc_btn.clicked.connect(self._on_run_monte_carlo)

        btn_row = QHBoxLayout()
        btn_row.addWidget(add_btn)
        btn_row.addWidget(del_btn)
        btn_row.addWidget(clear_btn)
        btn_row.addStretch(1)
        btn_row.addWidget(mc_btn)
        btn_row.addWidget(calc_btn)
        btn_row_w = QWidget()
        btn_row_w.setLayout(btn_row)

        # --- result --------------------------------------------------------
        self._result = QPlainTextEdit()
        self._result.setReadOnly(True)
        self._result.setPlaceholderText(
            "Resultados aparecerão aqui após clicar em Calcular..."
        )
        self._result.setFixedHeight(140)

        close_btns = QDialogButtonBox(QDialogButtonBox.Close)
        close_btns.rejected.connect(self.reject)
        close_btns.accepted.connect(self.accept)

        # --- layout --------------------------------------------------------
        root = QVBoxLayout(self)
        root.addWidget(header)
        root.addWidget(cust_w)
        root.addWidget(self._table, 1)
        root.addWidget(btn_row_w)
        root.addWidget(QLabel("<b>Índices calculados:</b>"))
        root.addWidget(self._result)
        root.addWidget(close_btns)

        # Seed with a sample event so user sees the format
        self._on_add_row()

    # ------------------------------------------------------------------
    # Slot handlers
    # ------------------------------------------------------------------

    def _on_add_row(self) -> None:
        """Add a new editable row with sane defaults."""
        row = self._table.rowCount()
        self._table.insertRow(row)
        self._table.setItem(row, 0, QTableWidgetItem("100"))
        self._table.setItem(row, 1, QTableWidgetItem("2.5"))
        self._table.setItem(row, 2, QTableWidgetItem(f"Evento #{row + 1}"))

    def _on_del_row(self) -> None:
        rows = sorted(
            {idx.row() for idx in self._table.selectedIndexes()},
            reverse=True,
        )
        for r in rows:
            self._table.removeRow(r)

    def _on_clear(self) -> None:
        self._table.setRowCount(0)
        self._result.clear()

    def _on_calculate(self) -> None:
        events: list[InterruptionEvent] = []
        for r in range(self._table.rowCount()):
            try:
                ni = int(self._table.item(r, 0).text())
                dur = float(self._table.item(r, 1).text())
                desc = self._table.item(r, 2).text() if self._table.item(r, 2) else ""
                events.append(InterruptionEvent(
                    customers_interrupted=ni,
                    duration_hours=dur,
                    description=desc,
                ))
            except (ValueError, AttributeError) as e:
                self._result.setPlainText(
                    f"❌ Erro na linha {r + 1}: {e}\n\n"
                    "Verifique os valores (N_i inteiro >= 0, duração > 0)."
                )
                return

        if not events:
            self._result.setPlainText(
                "Nenhum evento. Adicione pelo menos 1 linha."
            )
            return

        total = self._total_customers_spin.value()
        try:
            indices = calculate_indices(events, total)
        except ValueError as e:
            self._result.setPlainText(f"❌ Erro: {e}")
            return

        self._result.setPlainText(indices.as_text_report())

    def _on_run_monte_carlo(self) -> None:
        """v3.8.0 — Run Monte Carlo with IEEE 493 typical presets.

        Builds a sample 5-component system (transformer + 2 breakers
        + cable + motor) using IEEE 493 Tab 3-1 typical values and
        simulates 100 runs × 10 years.
        """
        from app.postprocessor.reliability_monte_carlo import (
            make_component_from_preset,
            run_monte_carlo,
        )
        components = [
            make_component_from_preset("T1", "transformer_dry_type"),
            make_component_from_preset("BR1", "circuit_breaker_metalclad"),
            make_component_from_preset("BR2", "circuit_breaker_lv"),
            make_component_from_preset("CBL1", "cable_aerial_mv"),
            make_component_from_preset("M1", "induction_motor_400hp"),
        ]
        try:
            result = run_monte_carlo(
                components,
                customers_per_component=200,
                total_customers=self._total_customers_spin.value(),
                n_years=10,
                n_simulations=100,
                seed=42,
            )
        except Exception as e:  # noqa: BLE001
            self._result.setPlainText(f"❌ Erro Monte Carlo: {e}")
            return
        self._result.setPlainText(result.as_text_report())
