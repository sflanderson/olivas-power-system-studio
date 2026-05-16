"""
app.gui.schematic_pp.saturation_curve_editor — widget especializado
para edição visual de curvas de saturação (i, ψ) em Type-98.

Substitui o QLineEdit genérico que edita CSV "0,0;1,1;5,1.1" por um
``QTableWidget`` com:

* 2 colunas editáveis (corrente em A, fluxo em V·s).
* Botões "+" e "−" para adicionar/remover linhas.
* Validação visual em tempo real: células com ``i`` ou ``ψ`` não-
  monotônico viram vermelhas.
* Botão "Preview" que abre um gráfico matplotlib embutido (opcional
  — matplotlib pode não estar disponível em CI headless).
* Botão "Restaurar default" que aplica a curva canônica (starter
  kit de 5 pontos).

O value serializado (``get_value`` retorna string) segue o mesmo
formato CSV que o bridge já consome ("i1,ψ1;i2,ψ2;..."). Assim
zero mudança no pipeline de emissão ATP — apenas UX melhor.

Uso
---

Ativado via ``PropertySpec.widget_hint = "saturation_curve"``.
O property_editor factory detecta e instancia este widget em vez
do QLineEdit padrão.

Este widget foi desenhado para ser independente de matplotlib
(import lazy) — se matplotlib não estiver instalado, o preview é
simplesmente desabilitado com tooltip explicativo. Isso garante
que o editor rode em containers minimalistas.
"""

from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.preprocessor.type98 import (
    SaturationCurve,
    SaturationPoint,
    default_saturation_curve,
    parse_csv_curve,
)


_INVALID_BRUSH = QBrush(QColor(255, 220, 220))   # rosa pálido
_VALID_BRUSH = QBrush(Qt.NoBrush)


class SaturationCurveEditor(QWidget):
    """
    Editor visual de curva (i, ψ) para Type-98.

    Signals
    -------
    value_changed(str):
        Emitido com o CSV serializado quando o usuário edita
        qualquer célula e a tabela inteira está monotônica válida.
    invalid_state(str):
        Emitido com mensagem de erro quando a tabela tem estado
        inválido (não-monotônico, vazio, valor não-numérico). Widgets
        consumidores (ex: PropertyRow) podem exibir em tooltip ou
        barra de status.
    """

    value_changed = Signal(str)
    invalid_state = Signal(str)

    #: colunas da tabela (ordem fixa).
    COL_CURRENT = 0
    COL_FLUX = 1

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        *,
        initial_csv: str = "",
        unit_i: str = "A",
        unit_psi: str = "V·s",
    ) -> None:
        super().__init__(parent)
        self._unit_i = unit_i
        self._unit_psi = unit_psi

        self._build_ui()
        # Populate inicial (após build_ui para ter tabela pronta)
        if initial_csv.strip():
            try:
                curve = parse_csv_curve(initial_csv)
                self.set_curve(curve)
            except ValueError:
                # CSV ruim — começa com curva vazia (2 linhas 0,0)
                self._fill_default_empty()
        else:
            self._fill_default_empty()

    # ---- UI construction --------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(4)

        # Tabela
        self._table = QTableWidget(0, 2, self)
        self._table.setHorizontalHeaderLabels([
            f"Corrente [{self._unit_i}]",
            f"Fluxo [{self._unit_psi}]",
        ])
        self._table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch,
        )
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setEditTriggers(
            QAbstractItemView.DoubleClicked
            | QAbstractItemView.EditKeyPressed
            | QAbstractItemView.AnyKeyPressed
        )
        self._table.verticalHeader().setVisible(False)
        self._table.itemChanged.connect(self._on_cell_changed)
        root.addWidget(self._table, stretch=1)

        # Toolbar
        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(0, 0, 0, 0)
        toolbar.setSpacing(4)

        self._btn_add = QPushButton("+ Linha", self)
        self._btn_add.setToolTip("Adicionar linha (ponto)")
        self._btn_add.clicked.connect(self._on_add_row)
        toolbar.addWidget(self._btn_add)

        self._btn_del = QPushButton("− Linha", self)
        self._btn_del.setToolTip("Remover linha(s) selecionada(s)")
        self._btn_del.clicked.connect(self._on_delete_row)
        toolbar.addWidget(self._btn_del)

        self._btn_default = QPushButton("⟲ Default", self)
        self._btn_default.setToolTip("Aplicar curva canônica (5 pontos)")
        self._btn_default.clicked.connect(self._on_apply_default)
        toolbar.addWidget(self._btn_default)

        self._btn_preview = QPushButton("📈 Preview", self)
        self._btn_preview.setToolTip(
            "Abrir gráfico da curva (requer matplotlib)"
        )
        self._btn_preview.clicked.connect(self._on_preview)
        toolbar.addWidget(self._btn_preview)

        toolbar.addStretch(1)
        root.addLayout(toolbar)

    # ---- Public API -------------------------------------------------------

    def get_value(self) -> str:
        """
        Retorna a curva como CSV "i1,ψ1;i2,ψ2;...".

        Se a tabela contém valores não-numéricos, retorna CSV parcial
        com apenas linhas válidas. Valide com ``is_valid()`` antes de
        consumir.
        """
        parts: list[str] = []
        for r in range(self._table.rowCount()):
            i_cell = self._table.item(r, self.COL_CURRENT)
            f_cell = self._table.item(r, self.COL_FLUX)
            if i_cell is None or f_cell is None:
                continue
            i_txt = (i_cell.text() or "").strip()
            f_txt = (f_cell.text() or "").strip()
            if not i_txt or not f_txt:
                continue
            parts.append(f"{i_txt},{f_txt}")
        return "; ".join(parts)

    def is_valid(self) -> bool:
        """
        True se a curva atual é válida (≥2 pontos monotônicos).
        """
        csv = self.get_value()
        if not csv:
            return False
        try:
            parse_csv_curve(csv)
            return True
        except ValueError:
            return False

    def set_curve(self, curve: SaturationCurve) -> None:
        """Popula a tabela a partir de uma SaturationCurve."""
        self._table.blockSignals(True)
        self._table.setRowCount(0)
        for pt in curve.points:
            self._append_row(pt.current, pt.flux)
        self._table.blockSignals(False)
        self._revalidate()

    def set_csv(self, csv: str) -> None:
        """Popula a tabela a partir de string CSV."""
        try:
            curve = parse_csv_curve(csv)
            self.set_curve(curve)
        except ValueError:
            self._fill_default_empty()

    # ---- Internals --------------------------------------------------------

    def _fill_default_empty(self) -> None:
        """Preenche com 2 linhas vazias (estado inicial quando sem CSV)."""
        self._table.blockSignals(True)
        self._table.setRowCount(0)
        self._append_row(0.0, 0.0)
        self._append_row(1.0, 1.0)
        self._table.blockSignals(False)
        self._revalidate()

    def _append_row(self, i: float, f: float) -> None:
        r = self._table.rowCount()
        self._table.insertRow(r)
        self._table.setItem(r, self.COL_CURRENT, QTableWidgetItem(_fmt(i)))
        self._table.setItem(r, self.COL_FLUX, QTableWidgetItem(_fmt(f)))

    def _on_add_row(self) -> None:
        # Adiciona linha no final — valores sugeridos crescem monotonicamente
        last_i = 0.0
        last_f = 0.0
        n = self._table.rowCount()
        if n > 0:
            last_i = _parse_cell(self._table.item(n - 1, self.COL_CURRENT))
            last_f = _parse_cell(self._table.item(n - 1, self.COL_FLUX))
        self._append_row(last_i + 1.0, last_f + 0.1)
        self._revalidate()

    def _on_delete_row(self) -> None:
        rows = sorted(
            {idx.row() for idx in self._table.selectionModel().selectedRows()},
            reverse=True,
        )
        if not rows:
            # Se nenhuma selecionada, remove a última
            if self._table.rowCount() > 0:
                rows = [self._table.rowCount() - 1]
        for r in rows:
            self._table.removeRow(r)
        self._revalidate()

    def _on_apply_default(self) -> None:
        self.set_curve(default_saturation_curve())

    def _on_preview(self) -> None:
        """Abre janela matplotlib com a curva atual."""
        try:
            import matplotlib
            matplotlib.use("Agg")  # backend não-interativo para o plot
            import matplotlib.pyplot as plt
        except ImportError:
            QMessageBox.information(
                self, "Preview indisponível",
                "matplotlib não está instalado. Instale com "
                "'pip install matplotlib' para habilitar o preview.",
            )
            return

        csv = self.get_value()
        if not csv:
            QMessageBox.warning(
                self, "Curva vazia",
                "Preencha pelo menos 2 pontos antes de fazer o preview.",
            )
            return
        try:
            curve = parse_csv_curve(csv)
        except ValueError as e:
            QMessageBox.warning(
                self, "Curva inválida", f"Erro: {e}",
            )
            return

        xs = [p.current for p in curve.points]
        ys = [p.flux for p in curve.points]

        # Plot interativo em janela separada
        try:
            matplotlib.use("Qt6Agg")  # troca para backend interativo
            import matplotlib.pyplot as plt2
            fig, ax = plt2.subplots(figsize=(6, 4))
            ax.plot(xs, ys, "-o", color="tab:blue")
            ax.set_xlabel(f"Corrente [{self._unit_i}]")
            ax.set_ylabel(f"Fluxo [{self._unit_psi}]")
            ax.set_title("Curva de saturação (Type-98)")
            ax.grid(True, alpha=0.3)
            fig.tight_layout()
            plt2.show()
        except Exception as e:  # pragma: no cover
            QMessageBox.warning(
                self, "Erro no preview",
                f"Não foi possível exibir o gráfico: {e}",
            )

    def _on_cell_changed(self, _item) -> None:
        self._revalidate()

    def _revalidate(self) -> None:
        """
        Releva a tabela: marca em vermelho células não-monotônicas
        e emite ``value_changed`` ou ``invalid_state``.

        Nota: ``item.setBackground`` dispararia ``itemChanged`` e
        causaria recursão infinita. Bloqueamos signals da tabela
        durante a fase de highlight; só o emit dos signals do widget
        (value_changed/invalid_state) escapa ao final.
        """
        # Bloqueia signals para evitar recursão via setBackground →
        # itemChanged → _on_cell_changed → _revalidate.
        self._table.blockSignals(True)
        try:
            # Remove highlights
            for r in range(self._table.rowCount()):
                for c in (self.COL_CURRENT, self.COL_FLUX):
                    item = self._table.item(r, c)
                    if item is not None:
                        item.setBackground(_VALID_BRUSH)

            # Avalia validade da curva
            csv = self.get_value()
            if not csv:
                signal_to_emit = ("invalid", "Curva vazia — adicione linhas.")
            else:
                try:
                    parse_csv_curve(csv)
                    signal_to_emit = ("valid", csv)
                except ValueError as e:
                    self._mark_violations_internal()
                    signal_to_emit = ("invalid", str(e))
        finally:
            self._table.blockSignals(False)

        # Emit signals DEPOIS de desbloquear — não interfere mais
        # no itemChanged interno da tabela.
        kind, payload = signal_to_emit
        if kind == "valid":
            self.value_changed.emit(payload)
        else:
            self.invalid_state.emit(payload)

    def _mark_violations_internal(self) -> None:
        """
        Marca linhas não-monotônicas em vermelho.

        **Deve ser chamada COM signals bloqueados no _table** —
        setBackground dispara itemChanged que recursaria em
        _revalidate (chamador). O contrato do método é "assume
        blockSignals already active".
        """
        prev_i = None
        prev_f = None
        for r in range(self._table.rowCount()):
            i = _parse_cell(self._table.item(r, self.COL_CURRENT), default=None)
            f = _parse_cell(self._table.item(r, self.COL_FLUX), default=None)
            bad = False
            if i is None or f is None:
                bad = True
            elif prev_i is not None and i <= prev_i:
                bad = True
            elif prev_f is not None and f <= prev_f:
                bad = True
            if bad:
                for c in (self.COL_CURRENT, self.COL_FLUX):
                    item = self._table.item(r, c)
                    if item is not None:
                        item.setBackground(_INVALID_BRUSH)
            if i is not None:
                prev_i = i
            if f is not None:
                prev_f = f


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fmt(val: float) -> str:
    """Formata float com precisão razoável sem trailing zeros."""
    return f"{val:g}"


def _parse_cell(item: Optional[QTableWidgetItem], default: Optional[float] = 0.0):
    """Parseia o texto de uma QTableWidgetItem como float, ou retorna default."""
    if item is None:
        return default
    txt = (item.text() or "").strip()
    if not txt:
        return default
    try:
        return float(txt)
    except ValueError:
        return default
