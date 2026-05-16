"""v3.5.2 — AddLinkTagDialog (closes SKIPPED_BACKLOG A.1).

Substitui os 2 ``QInputDialog`` usados em ``editor._on_add_link_tag``
(v3.1.3 → v3.5.1) por dialog único com:

* Label (texto exibido na tag)
* Target type combo (oneline/tcc/report/pdf)
* Target name/path (com Browse... para PDFs)
* Visible (default True)
* Closed arrow (default True)
* Preview live (label "<label> →  <target>")

Reference
---------
PTW Tutorial v8.0 §Part 1 p.35-42 — Link Tags são hyperlinks
clicáveis que navegam para outros documentos.
"""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


# ---------------------------------------------------------------------------
# Target schemes per PTW Tutorial §Part 1 p.36
# ---------------------------------------------------------------------------

TARGET_SCHEMES: tuple[tuple[str, str], ...] = (
    ("oneline", "Outro one-line drawing (oneline:DocName)"),
    ("tcc", "TCC drawing (tcc:CoordName)"),
    ("report", "Relatório (report:RPT_Name)"),
    ("pdf", "Arquivo PDF externo (pdf:path/to/file.pdf)"),
)


@dataclass
class LinkTagFormData:
    """Result of dialog acceptance."""

    label: str
    target: str
    visible: bool
    closed_arrow: bool


# ---------------------------------------------------------------------------
# Dialog
# ---------------------------------------------------------------------------


class AddLinkTagDialog(QDialog):
    """Unified Link Tag editor (closes SKIPPED_BACKLOG A.1).

    Replaces the two ``QInputDialog`` previously used in
    :meth:`SchematicEditor._on_add_link_tag`. Provides:

    * Browser of target schemes (combobox)
    * Live preview of label + target
    * Optional Browse... button for PDF target
    * Toggles for ``visible`` / ``closed_arrow``

    Use::

        dialog = AddLinkTagDialog(parent, default_label="Ver TCC-A",
                                  default_target="tcc:CoordA")
        if dialog.exec() == QDialog.Accepted:
            data = dialog.form_data()  # LinkTagFormData

    References
    ----------
    PTW Tutorial v8.0 §Part 1 p.35-42.
    """

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        default_label: str = "Ver TCC-A",
        default_target: str = "tcc:CoordA",
        default_visible: bool = True,
        default_closed_arrow: bool = True,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Inserir Link Tag")
        self.setModal(True)
        self.setMinimumWidth(440)

        # --- form fields ---------------------------------------------------
        self._label_edit = QLineEdit(default_label)
        self._label_edit.setToolTip("Texto exibido na tag no canvas.")

        # Parse default target into scheme + name
        default_scheme, default_name = self._split_target(default_target)

        self._scheme_combo = QComboBox()
        for scheme_id, scheme_label in TARGET_SCHEMES:
            self._scheme_combo.addItem(scheme_label, userData=scheme_id)
        # Set default scheme
        for i in range(self._scheme_combo.count()):
            if self._scheme_combo.itemData(i) == default_scheme:
                self._scheme_combo.setCurrentIndex(i)
                break

        self._target_edit = QLineEdit(default_name)
        self._target_edit.setToolTip(
            "Nome do documento (oneline/tcc/report) ou caminho (pdf)."
        )

        self._browse_btn = QPushButton("Procurar...")
        self._browse_btn.setToolTip("Selecionar arquivo PDF (apenas para target=pdf).")
        self._browse_btn.clicked.connect(self._on_browse)

        self._visible_chk = QCheckBox("Visível (renderizar no canvas)")
        self._visible_chk.setChecked(default_visible)
        self._closed_arrow_chk = QCheckBox(
            "Seta fechada (estilo PTW: triângulo preenchido)"
        )
        self._closed_arrow_chk.setChecked(default_closed_arrow)

        # --- preview -------------------------------------------------------
        self._preview = QLabel()
        self._preview.setFrameShape(QFrame.StyledPanel)
        self._preview.setAlignment(Qt.AlignCenter)
        self._preview.setMinimumHeight(40)
        self._preview.setStyleSheet(
            "QLabel { background: #fff7c0; color: #444; "
            "font-weight: bold; padding: 8px; }"
        )

        # --- layout --------------------------------------------------------
        form = QFormLayout()
        form.addRow("Texto na tag:", self._label_edit)
        form.addRow("Tipo de target:", self._scheme_combo)

        target_row = QHBoxLayout()
        target_row.addWidget(self._target_edit, 1)
        target_row.addWidget(self._browse_btn)
        target_row_w = QWidget()
        target_row_w.setLayout(target_row)
        form.addRow("Target:", target_row_w)

        form.addRow("", self._visible_chk)
        form.addRow("", self._closed_arrow_chk)
        form.addRow("Preview:", self._preview)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        root = QVBoxLayout(self)
        root.addLayout(form)
        root.addWidget(buttons)

        # --- live wiring ---------------------------------------------------
        self._label_edit.textChanged.connect(self._refresh_preview)
        self._target_edit.textChanged.connect(self._refresh_preview)
        self._scheme_combo.currentIndexChanged.connect(self._refresh_preview)
        self._scheme_combo.currentIndexChanged.connect(self._update_browse_state)

        self._update_browse_state()
        self._refresh_preview()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def form_data(self) -> LinkTagFormData:
        """Return current form values (call after :meth:`exec` accepted)."""
        return LinkTagFormData(
            label=self._label_edit.text().strip(),
            target=self._compose_target(),
            visible=self._visible_chk.isChecked(),
            closed_arrow=self._closed_arrow_chk.isChecked(),
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _split_target(target: str) -> tuple[str, str]:
        """Split ``"scheme:name"`` into ``(scheme, name)``."""
        if ":" in target:
            scheme, _, name = target.partition(":")
            return scheme.strip().lower(), name.strip()
        return "tcc", target.strip()

    def _compose_target(self) -> str:
        """Build ``"scheme:name"`` from current form state."""
        scheme = self._scheme_combo.currentData() or "tcc"
        name = self._target_edit.text().strip()
        return f"{scheme}:{name}"

    def _refresh_preview(self) -> None:
        label = self._label_edit.text().strip() or "(sem texto)"
        target = self._compose_target()
        self._preview.setText(f"📎 {label}  →  {target}")

    def _update_browse_state(self) -> None:
        scheme = self._scheme_combo.currentData()
        self._browse_btn.setEnabled(scheme == "pdf")

    def _on_browse(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Selecionar arquivo PDF", "", "PDF (*.pdf);;Todos (*.*)"
        )
        if path:
            self._target_edit.setText(path)
