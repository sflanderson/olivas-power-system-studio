"""
app.gui.datablock_dialog — diálogo de criação/edição de
:class:`PpDataBlock` (v0.86).

Datablock = caixa de texto livre fixada a um componente, mostrando
resultados de análises ou observações. Inspirado em SKM PowerTools
Workstation Equipment datablocks.

Convenção UX:
* Lines separadas por ``\\n`` no QTextEdit
* Pré-preenchimento via templates por categoria (SC / PF / AF /
  Custom) — usuário pode escolher um template e ajustar
* Cancel = nenhuma mudança
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


# Templates pré-prontos por categoria. Usuário escolhe um e os
# placeholders ``{name:fmt}`` ficam para o ``DataBlockBinder``
# substituir após uma análise. Sintaxe Python format-spec.
#
# v0.87: nomes alinhados com BusPipelineReport fields para
# auto-binding após pipeline run.
_TEMPLATES: dict[str, list[str]] = {
    "(em branco)": [],
    "Curto-circuito (IEC 60909)": [
        "Ik''  = {Ik_pp_kA:.2f} kA",
        "ip    = {ip_kA:.2f} kA",
        "κ     = {kappa:.2f}",
        "Sk''  = {Sk_pp_MVA:.1f} MVA",
    ],
    "Fluxo de potência": [
        "V    = {V_pu:.3f} pu ∠ {V_angle_deg:.1f}°",
        "P    = {P_kW:.1f} kW",
        "Q    = {Q_kVar:.1f} kVar",
        "Loading = {loading_pct:.1f} %",
    ],
    "Arc-Flash (NBR 17227)": [
        "IE      = {IE_cal:.2f} cal/cm²",
        "AFB     = {AFB_mm:.0f} mm",
        "PPE     = {PPE}",
        "t_clear = {t_clear_ms:.0f} ms",
    ],
    "Equipamento (PTW Equipment)": [
        "Tag:  {bus_id}",
        "V_LL = {V_LL_kV} kV",
        "ICC  = {Ik_pp_kA:.1f} kA",
        "Trip = {t_clear_ms:.0f} ms",
    ],
    "Coordenação IEEE 242": [
        "Relé: {relay_tag}",
        "TMS = {TMS:.2f}",
        "I_pickup = {I_pickup_A:.0f} A",
        "Margem CTI = {CTI_ms:.0f} ms",
    ],
}


class DataBlockEditDialog(QDialog):
    """
    Diálogo modal para criar / editar lines de um datablock.

    Usage::

        dlg = DataBlockEditDialog(parent, initial_lines=["foo", "bar"])
        if dlg.exec() == QDialog.Accepted:
            new_lines = dlg.lines()
    """

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        initial_lines: Optional[list[str]] = None,
        title: str = "Datablock",
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(420)
        self.setMinimumHeight(320)

        self._build_ui(initial_lines or [])

    def _build_ui(self, initial_lines: list[str]) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        title = QLabel("<b>Editar datablock</b>")
        layout.addWidget(title)

        hint = QLabel(
            "<i>Cada linha do texto vira uma linha do datablock no "
            "canvas. Use o template como ponto de partida.</i>"
        )
        hint.setWordWrap(True)
        layout.addWidget(hint)

        # Template selector
        tpl_row = QHBoxLayout()
        tpl_row.addWidget(QLabel("Template:"))
        self._template_combo = QComboBox()
        for name in _TEMPLATES:
            self._template_combo.addItem(name)
        tpl_row.addWidget(self._template_combo, stretch=1)
        apply_btn = QPushButton("Aplicar →")
        apply_btn.clicked.connect(self._apply_template)
        tpl_row.addWidget(apply_btn)
        layout.addLayout(tpl_row)

        # Text editor
        self._text_edit = QTextEdit()
        self._text_edit.setAcceptRichText(False)
        self._text_edit.setLineWrapMode(QTextEdit.NoWrap)
        self._text_edit.setPlainText("\n".join(initial_lines))
        layout.addWidget(self._text_edit, stretch=1)

        # Buttons
        self._buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            parent=self,
        )
        self._buttons.accepted.connect(self.accept)
        self._buttons.rejected.connect(self.reject)
        layout.addWidget(self._buttons)

    def _apply_template(self) -> None:
        name = self._template_combo.currentText()
        lines = _TEMPLATES.get(name, [])
        self._text_edit.setPlainText("\n".join(lines))

    # ---- API --------------------------------------------------------------

    def lines(self) -> list[str]:
        """Retorna a lista de linhas (sem trailing newlines vazios)."""
        text = self._text_edit.toPlainText()
        # Tira lines completamente vazias do final (mas preserva no meio)
        result = text.split("\n")
        while result and not result[-1].strip():
            result.pop()
        return result
