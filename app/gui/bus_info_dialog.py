"""
app.gui.bus_info_dialog — diálogo rápido de criação de BUS.

Ao adicionar um BUS via paleta/drag-drop ou menu contextual,
o usuário responde 4 campos críticos antes do componente ser
posicionado:

* **ID do painel** (ex: "BUS-MAIN", "MCC-13.8"). Auto-sugerido
  baseado nos BUSes já existentes.
* **Tensão V_LL (kV)**.
* **N° de fases** (1 ou 3).
* **Tipo de painel** (NBR 17227 Tabela 1).
* **Lineside** (checkbox — pior caso arc-flash).

Filosofia (PTW Equipment Tab):
Ao colocar um equipamento crítico no esquemático, vale a pena
gastar 5 segundos preenchendo os campos essenciais — depois é
mais difícil voltar e fazer (custom: "esquece" arc-flash).

Cancelar = não cria o BUS. OK = cria com as propriedades
preenchidas (sem precisar abrir o painel de propriedades
posteriormente).
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


# Tipos de painel da NBR 17227 Tabela 1 (mesmos códigos do .ocomp).
# Tupla: (código, label_pt, faixa_kV).
_PANEL_TYPES = [
    ("swgr_15kv", "Switchgear MT (5–15 kV)", "5 < V ≤ 15"),
    ("ccm_15kv", "CCM MT (5–15 kV)", "5 < V ≤ 15"),
    ("swgr_5kv", "Switchgear MT (1–5 kV)", "1 < V ≤ 5"),
    ("ccm_5kv", "CCM MT (1–5 kV)", "1 < V ≤ 5"),
    ("lv_swgr", "Switchgear BT (≤ 1 kV)", "V ≤ 1"),
    ("lv_panel_typical", "Painel BT típico (≤ 1 kV)", "V ≤ 1"),
    ("lv_panel_shallow", "Painel BT raso (≤ 1 kV)", "V ≤ 1"),
    ("cable_jct_box", "Caixa de junção de cabos", "qualquer"),
]


class BusInfoDialog(QDialog):
    """
    Diálogo rápido para preencher metadata de um BUS recém-criado.

    Uso típico::

        dlg = BusInfoDialog(parent, suggested_id="BUS-2",
                            existing_ids={"BUS-1"})
        if dlg.exec() == QDialog.Accepted:
            bus_id = dlg.bus_id()
            rated_kV = dlg.rated_voltage_kV()
            ...
    """

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        suggested_id: str = "BUS-1",
        existing_ids: Optional[set[str]] = None,
        default_voltage_kV: float = 13.8,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Adicionar Barramento")
        self.setMinimumWidth(420)

        self._existing_ids = existing_ids or set()
        self._build_ui(suggested_id, default_voltage_kV)
        self._wire_signals()
        self._validate()

    # ---- UI ---------------------------------------------------------------

    def _build_ui(self, suggested_id: str, default_voltage_kV: float) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        title = QLabel("<b>Configurar barramento (PTW Equipment)</b>")
        layout.addWidget(title)

        hint = QLabel(
            "<i>Preencha os campos críticos para arc-flash + "
            "coordenação. Pode ajustar depois nas Propriedades.</i>"
        )
        hint.setWordWrap(True)
        layout.addWidget(hint)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)
        form.setHorizontalSpacing(14)
        form.setVerticalSpacing(8)

        # ID
        self._id_edit = QLineEdit(suggested_id)
        self._id_edit.setPlaceholderText("ex: BUS-MAIN, MCC-13.8")
        form.addRow("ID do painel:", self._id_edit)

        # Tensão
        self._kv_spin = QDoubleSpinBox()
        self._kv_spin.setRange(0.1, 800.0)
        self._kv_spin.setSingleStep(0.1)
        self._kv_spin.setDecimals(2)
        self._kv_spin.setSuffix(" kV (V_LL)")
        self._kv_spin.setValue(default_voltage_kV)
        form.addRow("Tensão nominal:", self._kv_spin)

        # Fases
        self._phases_spin = QSpinBox()
        self._phases_spin.setRange(1, 3)
        self._phases_spin.setSingleStep(2)   # 1 ou 3
        self._phases_spin.setValue(3)
        form.addRow("N° de fases:", self._phases_spin)

        # Tipo de painel
        self._panel_combo = QComboBox()
        for code, label, range_str in _PANEL_TYPES:
            self._panel_combo.addItem(f"{label}  [{range_str}]", code)
        # Pre-selecionar swgr_15kv (default do .ocomp)
        idx = self._panel_combo.findData("swgr_15kv")
        if idx >= 0:
            self._panel_combo.setCurrentIndex(idx)
        form.addRow("Tipo de painel:", self._panel_combo)

        # Lineside
        self._lineside_check = QCheckBox(
            "Lineside (alimentação — pior caso arc-flash)"
        )
        self._lineside_check.setChecked(True)
        form.addRow("Posição:", self._lineside_check)

        layout.addLayout(form)

        # Mensagem de validação
        self._error_label = QLabel("")
        self._error_label.setStyleSheet(
            "QLabel { color: #B00020; font-size: 9pt; }"
        )
        layout.addWidget(self._error_label)

        # Buttons
        self._buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            parent=self,
        )
        self._buttons.accepted.connect(self.accept)
        self._buttons.rejected.connect(self.reject)
        layout.addWidget(self._buttons)

    def _wire_signals(self) -> None:
        self._id_edit.textChanged.connect(self._validate)
        self._kv_spin.valueChanged.connect(self._auto_suggest_panel_type)

    # ---- Validação --------------------------------------------------------

    def _validate(self) -> None:
        bus_id = self._id_edit.text().strip()
        ok = QDialogButtonBox.Ok
        ok_btn = self._buttons.button(ok)
        if not bus_id:
            self._error_label.setText("ID não pode ser vazio.")
            ok_btn.setEnabled(False)
            return
        if bus_id in self._existing_ids:
            self._error_label.setText(
                f"Já existe BUS com ID {bus_id!r}."
            )
            ok_btn.setEnabled(False)
            return
        self._error_label.setText("")
        ok_btn.setEnabled(True)

    def _auto_suggest_panel_type(self, kv: float) -> None:
        """
        Quando usuário muda a tensão, auto-ajusta o panel_type
        para a faixa correta (NBR 17227 Tabela 1).

        Apenas sugestão — o usuário pode override no combo.
        """
        if kv <= 1.0:
            target = "lv_panel_typical"
        elif kv <= 5.0:
            target = "swgr_5kv"
        elif kv <= 15.0:
            target = "swgr_15kv"
        else:
            # Tensões > 15 kV não têm classe específica na NBR
            # 17227 → mantém swgr_15kv (mais conservador).
            target = "swgr_15kv"
        idx = self._panel_combo.findData(target)
        if idx >= 0:
            self._panel_combo.setCurrentIndex(idx)

    # ---- Getters ----------------------------------------------------------

    def bus_id(self) -> str:
        return self._id_edit.text().strip()

    def rated_voltage_kV(self) -> float:
        return float(self._kv_spin.value())

    def n_phases(self) -> int:
        return int(self._phases_spin.value())

    def panel_type(self) -> str:
        return str(self._panel_combo.currentData())

    def is_lineside(self) -> bool:
        return self._lineside_check.isChecked()

    # ---- Conveniência ----------------------------------------------------

    def to_property_values(self) -> list[str]:
        """
        Retorna a lista de valores (strings) na ordem em que
        ``BUS.ocomp`` define as propriedades:

        1. bus_id
        2. rated_voltage_kV
        3. n_phases
        4. panel_type
        5. is_lineside
        6. has_AFD ('0' default)
        7. AFD_clearing_time_ms ('10' default)
        8. n_taps ('4' default)
        9. description ('' default)

        Pronto para construção de :class:`PpComponent` ou
        comparação com defaults do catálogo.
        """
        return [
            self.bus_id(),
            f"{self.rated_voltage_kV():g}",
            str(self.n_phases()),
            self.panel_type(),
            "1" if self.is_lineside() else "0",
            "0",     # has_AFD
            "10",    # AFD_clearing_time_ms
            "4",     # n_taps
            "",      # description
        ]
