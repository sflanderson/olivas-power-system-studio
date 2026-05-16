"""
app.gui.equipment_library_dialog — Equipment Library com Apply
(v1.4.2 Sprint E — fecha gap "vendor list sem função").

Filosofia
==========

PTW Power*Tools tem fluxo: usuário abre Library → escolhe modelo
do vendor (SEL-751, ABB REF615, etc.) → clica "Apply" →
configurações do datasheet são copiadas para o componente
selecionado no canvas.

Olivas v1.4.1 tinha library dialog read-only (apenas browse).
v1.4.2 adiciona o **Apply workflow**:
1. Detecta componente selecionado no PpEditor
2. Verifica compatibilidade (relé library → componente RELAY,
   motor library → MOTOR, etc.)
3. Popula properties com vendor specs

Cobertura compatibilidade (v1.4.2)
====================================

* RelayModel → componentes RELAY (preferido) e Relais (legacy)
* MotorModel → componente MOTOR
* TransformerModel → componentes XFMR3 (preferido), Tr, Tr3, sTr
* BreakerModel → componentes VCB, VCB3
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.equipment import library


# Mapping: tipo de model → set de codes de componentes compatíveis
_COMPAT_MAP = {
    "RelayModel": {"RELAY", "Relais"},
    "MotorModel": {"MOTOR"},
    "TransformerModel": {"XFMR3", "Tr3", "Tr", "sTr"},
    # v1.4.3: BREAKER (genérico controlado por relé) é o componente
    # preferido para BreakerModel; VCB/VCB3 ficam como legacy ATP.
    "BreakerModel": {"BREAKER", "VCB", "VCB3"},
}


class EquipmentLibraryDialog(QDialog):
    """
    Library dialog com Apply workflow.

    Public API
    -----------

    * ``selected_model`` — model atualmente selecionado em qualquer tab
    * ``apply_to_component(component)`` — aplica specs ao componente

    Constructor
    -----------

    Aceita ``main_window`` para detectar componente selecionado
    no PpEditor.
    """

    def __init__(
        self,
        main_window=None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.main_window = main_window
        self.setWindowTitle(
            "📚 Biblioteca de Equipamentos — "
            "Olivas Power System Studio"
        )
        self.resize(1100, 720)

        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        stats = library.stats()
        layout.addWidget(QLabel(
            f"<b>{stats['total']} equipamentos</b> de "
            f"<b>{len(library.list_vendors())} fabricantes</b> "
            f"({', '.join(library.list_vendors())})"
        ))

        info_label = QLabel(
            "<i>v1.4.2: clique em um modelo + 'Aplicar ao dispositivo' "
            "para copiar specs do datasheet para o componente "
            "selecionado no esquemático.</i>"
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        # Tabs
        self.tabs = QTabWidget()
        self._build_relays_tab()
        self._build_motors_tab()
        self._build_transformers_tab()
        self._build_breakers_tab()
        layout.addWidget(self.tabs, 1)

        # Action buttons
        action_layout = QHBoxLayout()

        self.btn_apply = QPushButton(
            "✅ Aplicar ao dispositivo selecionado"
        )
        self.btn_apply.clicked.connect(self._on_apply)
        action_layout.addWidget(self.btn_apply)

        action_layout.addStretch()

        bb = QDialogButtonBox(QDialogButtonBox.Close)
        bb.button(QDialogButtonBox.Close).setText("Fechar")
        bb.rejected.connect(self.reject)
        action_layout.addWidget(bb)

        layout.addLayout(action_layout)

    # ---------------------------------------------------------------
    # Tab builders
    # ---------------------------------------------------------------

    def _build_relays_tab(self) -> None:
        self.relays_list = QListWidget()
        for r in library.list_relays():
            ansi_str = ', '.join(r.ansi_devices[:6])
            text = (
                f"{r.model_id}  ·  {r.full_name}\n"
                f"    {r.application.value}  ·  "
                f"{r.voltage_class.value}  ·  "
                f"ANSI: {ansi_str}…  "
                f"{'IEC 61850' if r.iec_61850 else ''}"
            )
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, r)
            self.relays_list.addItem(item)
        self.tabs.addTab(
            self.relays_list,
            f"🛡️ Relés ({len(library.list_relays())})",
        )

    def _build_motors_tab(self) -> None:
        self.motors_list = QListWidget()
        for m in library.list_motors():
            text = (
                f"{m.model_id}  ·  {m.full_name}\n"
                f"    {m.rated_power_kW} kW @ "
                f"{m.rated_voltage_V} V, "
                f"η={m.full_load_efficiency:.1%}, "
                f"{m.ie_class}"
            )
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, m)
            self.motors_list.addItem(item)
        self.tabs.addTab(
            self.motors_list,
            f"⚙️ Motores ({len(library.list_motors())})",
        )

    def _build_transformers_tab(self) -> None:
        self.trafos_list = QListWidget()
        for t in library.list_transformers():
            text = (
                f"{t.model_id}  ·  {t.full_name}\n"
                f"    {t.rated_S_kVA} kVA, "
                f"{t.primary_kV}/{t.secondary_kV} kV, "
                f"Z={t.impedance_pct}%, "
                f"X/R={t.x_over_r:.1f}"
            )
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, t)
            self.trafos_list.addItem(item)
        self.tabs.addTab(
            self.trafos_list,
            f"🔄 Transformadores ({len(library.list_transformers())})",
        )

    def _build_breakers_tab(self) -> None:
        self.breakers_list = QListWidget()
        for b in library.list_breakers():
            text = (
                f"{b.model_id}  ·  {b.full_name}\n"
                f"    {b.rated_voltage_kV} kV, "
                f"{b.rated_current_A} A, "
                f"Iccs={b.breaking_capacity_kA} kA, "
                f"{b.arc_quenching}"
            )
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, b)
            self.breakers_list.addItem(item)
        self.tabs.addTab(
            self.breakers_list,
            f"🔌 Disjuntores ({len(library.list_breakers())})",
        )

    # ---------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------

    def selected_model(self):
        """Retorna o model selecionado na tab atual, ou None."""
        cur_idx = self.tabs.currentIndex()
        list_widgets = [
            self.relays_list, self.motors_list,
            self.trafos_list, self.breakers_list,
        ]
        if 0 <= cur_idx < len(list_widgets):
            cur_list = list_widgets[cur_idx]
            cur_item = cur_list.currentItem()
            if cur_item is not None:
                return cur_item.data(Qt.UserRole)
        return None

    def get_selected_pp_component(self):
        """
        Tenta detectar componente selecionado no PpEditor.
        Returns PpComponent ou None.
        """
        if self.main_window is None:
            return None
        # main_window.schematic_pp é o PpEditor
        try:
            scene = self.main_window.schematic_pp.scene
        except AttributeError:
            return None
        # Itera items selecionados — pega primeiro com .component
        for item in scene.selectedItems():
            comp = getattr(item, "component", None)
            if comp is not None:
                return comp
        return None

    def apply_model_to_component(self, model, component) -> tuple:
        """
        Aplica specs do model ao component (in-place).

        Retorna ``(ok: bool, message: str)``.
        """
        if model is None:
            return False, "Nenhum modelo selecionado na biblioteca."
        if component is None:
            return (
                False,
                "Nenhum componente selecionado no esquemático. "
                "Clique num componente do canvas antes de Aplicar.",
            )

        model_type = type(model).__name__
        compatible_codes = _COMPAT_MAP.get(model_type, set())
        if component.type not in compatible_codes:
            return (
                False,
                f"Incompatibilidade: modelo {model_type} (vendor "
                f"{getattr(model, 'manufacturer', '?')} "
                f"{model.model_id}) não pode ser aplicado a "
                f"componente {component.type!r}.\n\n"
                f"Compatíveis com {model_type}: "
                f"{sorted(compatible_codes)}",
            )

        # Aplica specs por tipo
        applied_fields = self._apply_specs(model, component)
        return (
            True,
            f"Aplicado: {model.model_id} ({model.manufacturer}) → "
            f"{component.type} '{component.name}'\n\n"
            f"Campos atualizados: {', '.join(applied_fields)}",
        )

    def _apply_specs(self, model, component) -> list:
        """
        Aplica specs do model nas properties do component.

        v1.4.2 escopo: copia campos comuns (model_id, manufacturer,
        ratings principais). Mapeamento mais sofisticado por
        property name fica para v1.4.3.

        Returns lista de field names atualizados.
        """
        applied = []

        def _set_prop(prop_name, value):
            """Helper: atualiza propriedade se existir no spec do component."""
            from app.preprocessor.spec import get_default_registry
            spec = get_default_registry().get(component.type)
            if spec is None:
                return False
            for idx, prop_spec in enumerate(spec.properties):
                if prop_spec.name == prop_name:
                    if idx < len(component.properties):
                        component.properties[idx].value = str(value)
                        applied.append(prop_name)
                        return True
            return False

        # vendor_model field — comum a vários
        _set_prop("vendor_model", f"{model.manufacturer} {model.model_id}")

        # Type-specific
        model_type = type(model).__name__
        if model_type == "RelayModel":
            # Aplica curve type default (primeiro suportado)
            if model.curves_supported:
                _set_prop("curve_51", model.curves_supported[0])
        elif model_type == "MotorModel":
            _set_prop("rated_power_kW", model.rated_power_kW)
            _set_prop("rated_voltage_V", model.rated_voltage_V)
            _set_prop("efficiency", model.full_load_efficiency)
        elif model_type == "TransformerModel":
            _set_prop("kVA_rated", model.rated_S_kVA)
            _set_prop("V_pri_kV", model.primary_kV)
            _set_prop("V_sec_kV", model.secondary_kV)
            _set_prop("impedance_pct", model.impedance_pct)
            _set_prop("xr_ratio", model.x_over_r)
        elif model_type == "BreakerModel":
            _set_prop("rated_voltage_kV", model.rated_voltage_kV)
            _set_prop("rated_current_A", model.rated_current_A)
            _set_prop("breaking_capacity_kA", model.breaking_capacity_kA)

        return applied

    # ---------------------------------------------------------------
    # Slot
    # ---------------------------------------------------------------

    def _on_apply(self) -> None:
        """Slot do botão Aplicar."""
        model = self.selected_model()
        component = self.get_selected_pp_component()
        ok, msg = self.apply_model_to_component(model, component)
        if ok:
            QMessageBox.information(self, "Aplicado", msg)
            # Refresh do canvas (atualiza textos das properties)
            try:
                self.main_window.schematic_pp.scene.update()
            except Exception:
                pass
        else:
            QMessageBox.warning(self, "Não aplicado", msg)
