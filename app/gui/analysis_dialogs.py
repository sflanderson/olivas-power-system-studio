"""
app.gui.analysis_dialogs — diálogos de parâmetros para os
estudos do postprocessor (v0.28.2-PRO Onda 2).

Expõe na GUI as funcionalidades antes invisíveis:

* SC IEC 60909 (com sequencial 0/1/2 e Methods A/B/C)
* Power Flow Newton-Raphson
* Motor Starting (IEEE 399)
* Arc-flash NBR 17227 / IEEE 1584
* Bus pipeline (estudo completo)

Cada função abre um QDialog para parâmetros, executa a
análise e retorna um Optional[ResultObject]. Caller é
responsável por exibir o resultado.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox,
    QDoubleSpinBox, QFormLayout, QHBoxLayout, QLabel,
    QPlainTextEdit, QPushButton, QSpinBox, QVBoxLayout,
    QWidget,
)


# ---------------------------------------------------------------------------
# Utility — display result in a simple modal text dialog
# ---------------------------------------------------------------------------


def show_result_dialog(
    parent: QWidget,
    title: str,
    text: str,
    *,
    width: int = 800,
    height: int = 600,
) -> None:
    """Modal text-only result dialog with Copy/Close buttons."""
    dlg = QDialog(parent)
    dlg.setWindowTitle(title)
    dlg.resize(width, height)
    layout = QVBoxLayout(dlg)

    edit = QPlainTextEdit(dlg)
    edit.setReadOnly(True)
    edit.setFont_pt = 10
    # Use monospaced font
    from PySide6.QtGui import QFont
    f = QFont("Consolas", 10)
    edit.setFont(f)
    edit.setPlainText(text)
    layout.addWidget(edit, 1)

    btn_box = QDialogButtonBox(QDialogButtonBox.Close)
    btn_copy = QPushButton("Copiar")
    btn_box.addButton(btn_copy, QDialogButtonBox.ActionRole)
    btn_box.rejected.connect(dlg.reject)

    def _copy():
        from PySide6.QtWidgets import QApplication
        QApplication.clipboard().setText(text)
    btn_copy.clicked.connect(_copy)
    layout.addWidget(btn_box)
    dlg.exec()


# ---------------------------------------------------------------------------
# Short-circuit dialog (IEC 60909 + sequencial 0/1/2)
# ---------------------------------------------------------------------------


class ShortCircuitDialog(QDialog):
    """Diálogo para análise de curto-circuito IEC 60909-0."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Curto-circuito (IEC 60909-0)")
        self.setModal(True)
        self.resize(500, 480)

        layout = QFormLayout(self)

        # System parameters
        self.voltage_kV = QDoubleSpinBox()
        self.voltage_kV.setRange(0.208, 1000.0)
        self.voltage_kV.setValue(13.8)
        self.voltage_kV.setDecimals(3)
        self.voltage_kV.setSuffix(" kV")
        layout.addRow("Tensão Un (linha-linha):", self.voltage_kV)

        self.SkQ_MVA = QDoubleSpinBox()
        self.SkQ_MVA.setRange(1.0, 100000.0)
        self.SkQ_MVA.setValue(500.0)
        self.SkQ_MVA.setSuffix(" MVA")
        layout.addRow("S_kQ'' utility:", self.SkQ_MVA)

        self.r_over_x = QDoubleSpinBox()
        self.r_over_x.setRange(0.0, 5.0)
        self.r_over_x.setValue(0.10)
        self.r_over_x.setDecimals(3)
        self.r_over_x.setSingleStep(0.01)
        layout.addRow("R/X da rede:", self.r_over_x)

        # Calculation kind
        self.kind_combo = QComboBox()
        self.kind_combo.addItem("max (dimensionamento)", "max")
        self.kind_combo.addItem("min (sensibilidade proteção)", "min")
        layout.addRow("Tipo de cálculo:", self.kind_combo)

        # Fault types
        self.cb_3p = QCheckBox("Trifásica (Ik''3) — IEC §4.3.1")
        self.cb_3p.setChecked(True)
        self.cb_ll = QCheckBox("Bifásica LL (Ik''2) — IEC §4.3.2")
        self.cb_lg = QCheckBox("Monofásica LG (Ik''1) — IEC §4.3.4")
        self.cb_llg = QCheckBox(
            "Bifásica-terra LLG (Ik''2EG) — IEC §4.3.3"
        )
        layout.addRow(QLabel("<b>Tipos de falta:</b>"))
        layout.addRow(self.cb_3p)
        layout.addRow(self.cb_ll)
        layout.addRow(self.cb_lg)
        layout.addRow(self.cb_llg)

        # Grounding (for LG/LLG)
        self.grounding_combo = QComboBox()
        self.grounding_combo.addItem(
            "Solidamente aterrado (TN)", "solid",
        )
        self.grounding_combo.addItem(
            "Aterrado por resistência (TT/NGR)", "resistance",
        )
        self.grounding_combo.addItem(
            "Alta impedância (IT)", "impedance",
        )
        self.grounding_combo.addItem("Isolado", "ungrounded")
        self.grounding_combo.addItem(
            "Petersen (resonant)", "resonant",
        )
        layout.addRow("Tipo de aterramento:", self.grounding_combo)

        # Method for kappa
        self.kappa_combo = QComboBox()
        self.kappa_combo.addItem("Method A (radial)", "A")
        self.kappa_combo.addItem("Method B (radial + 15%)", "B")
        self.kappa_combo.addItem(
            "Method C (frequência-equivalente, malhada)", "C",
        )
        layout.addRow("Método para κ:", self.kappa_combo)

        # OK/Cancel
        btn_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
        )
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addRow(btn_box)

    def get_parameters(self) -> dict:
        return {
            "voltage_kV": self.voltage_kV.value(),
            "SkQ_MVA": self.SkQ_MVA.value(),
            "r_over_x": self.r_over_x.value(),
            "kind": self.kind_combo.currentData(),
            "fault_3p": self.cb_3p.isChecked(),
            "fault_ll": self.cb_ll.isChecked(),
            "fault_lg": self.cb_lg.isChecked(),
            "fault_llg": self.cb_llg.isChecked(),
            "grounding": self.grounding_combo.currentData(),
            "kappa_method": self.kappa_combo.currentData(),
        }


def run_short_circuit_analysis(
    parent: QWidget, *, project=None, bus_id: str = "", **kwargs,
) -> None:
    """Abre dialog SC, executa análise, exibe resultado.

    v0.82: aceita ``project`` e ``bus_id`` opcionais do
    RunAnalysisDialog. Por enquanto ainda usa dialog de
    parâmetros (Sk_Q, V, etc) — bus_id pode ser usado em
    futura versão para auto-extrair S_kQ.
    """
    _ = project, bus_id    # silenciar unused
    from app.postprocessor.short_circuit import ShortCircuitNetwork
    from app.standards.iec60909_seq import (
        GroundingType, calculate_all_faults,
        sequence_impedances_from_grounding,
    )
    from app.standards.iec60909_kappa import (
        KappaMethod, kappa_recommended,
    )

    dlg = ShortCircuitDialog(parent)
    if dlg.exec() != QDialog.Accepted:
        return

    p = dlg.get_parameters()
    lines = []

    # Trifásica (sempre disponível via ShortCircuitNetwork)
    if p["fault_3p"]:
        net = ShortCircuitNetwork(rated_voltage_kV=p["voltage_kV"])
        net.add_network_feeder(
            "UTIL", S_kQ_MVA=p["SkQ_MVA"],
            voltage_factor=1.10 if p["kind"] == "max" else 1.00,
            r_over_x=p["r_over_x"],
        )
        sc = net.calculate_at_bus("BUS", kind=p["kind"])
        lines.append(sc.summary())

        # v3.3.0 Sprint 2: wire kappa_method dropdown (era inerte pré-v3.3.0).
        # Recalcula κ + ip via método selecionado pelo usuário (A/B/C).
        # Reference: IEC 60909-0:2016 §4.4.1.2; PTW Tutorial §Part 5 p.128.
        try:
            method_str = p.get("kappa_method", "A").upper()
            method = {
                "A": KappaMethod.METHOD_A,
                "B": KappaMethod.METHOD_B,
                "C": KappaMethod.METHOD_C,
            }.get(method_str, KappaMethod.METHOD_A)
            # Recompute κ via selected method
            # Method C requires z_thevenin_at_fc. Pass z_th_complex (the
            # complex Thevenin Z at nominal frequency) — for Method C the
            # caller would need impedance at reduced freq fc=20Hz; we
            # approximate with z at nominal as fallback.
            kappa_user = kappa_recommended(
                r_over_x_at_fn=p["r_over_x"],
                method=method,
                z_thevenin_at_fc=sc.z_thevenin_ohm,
            )
            import math
            ip_kA_recomputed = kappa_user * math.sqrt(2) * sc.Ik_pp_kA
            lines.append("")
            lines.append(f"κ (Method {method_str}) = {kappa_user:.4f}")
            lines.append(f"ip (Method {method_str}) = {ip_kA_recomputed:.3f} kA")
            lines.append(
                "  (IEC 60909-0:2016 §4.4.1.2 — selected via user dropdown)"
            )
        except Exception as e:  # noqa: BLE001
            lines.append(f"  (kappa_method não aplicável: {e})")
        lines.append("")
        z_th_complex = sc.z_thevenin_ohm
    else:
        # Computa Z_th sintético para os outros tipos de falta
        import math
        c = 1.10 if p["kind"] == "max" else 1.00
        z_mag = c * (p["voltage_kV"] * 1e3) ** 2 / (p["SkQ_MVA"] * 1e6)
        x = z_mag / math.sqrt(1.0 + p["r_over_x"] ** 2)
        r = p["r_over_x"] * x
        z_th_complex = complex(r, x)

    # Faltas assimétricas (LL, LG, LLG)
    if p["fault_ll"] or p["fault_lg"] or p["fault_llg"]:
        try:
            grounding = GroundingType(p["grounding"])
        except ValueError:
            grounding = GroundingType.SOLIDLY_GROUNDED
        seq = sequence_impedances_from_grounding(
            z_th_complex, grounding,
        )
        c = 1.10 if p["kind"] == "max" else 1.00
        result = calculate_all_faults(
            Un_kV=p["voltage_kV"],
            seq_impedances=seq,
            grounding=grounding,
            voltage_factor_c=c,
        )
        lines.append(result.summary())

    text = "\n".join(lines) if lines else "Nenhum tipo de falta selecionado."
    show_result_dialog(parent, "Resultado SC", text)


# ---------------------------------------------------------------------------
# Power flow dialog
# ---------------------------------------------------------------------------


class PowerFlowDialog(QDialog):
    """Diálogo simples 2-bus para fluxo de potência.

    .. deprecated:: 3.7.2 (v3.7.2 closes SKIPPED_BACKLOG C.1)
        Use o N-bus path via :func:`build_pf_system_from_project`
        sempre que o projeto tem ≥2 BUS components. Este dialog 2-bus
        é mantido apenas como fallback para projetos vazios. Será
        removido em v4.0.0.
    """

    DEPRECATED_MESSAGE: str = (
        "⚠️ Dialog 2-bus legacy (DEPRECATED v3.7.2). "
        "Para análise real, adicione BUS components ao projeto "
        "→ N-bus path automático com impedâncias reais (B.1)."
    )

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Fluxo de Potência (Newton-Raphson) [LEGACY 2-bus]")
        self.setModal(True)
        self.resize(450, 430)
        layout = QFormLayout(self)
        # v3.7.2 (closes SKIPPED_BACKLOG C.1) — deprecation banner.
        from PySide6.QtCore import Qt as _Qt
        _dep = QLabel(self.DEPRECATED_MESSAGE)
        _dep.setWordWrap(True)
        _dep.setStyleSheet(
            "QLabel { background: #fff5cc; color: #663300; "
            "padding: 6px; border: 1px solid #cc9966; "
            "font-size: 10pt; }"
        )
        layout.addRow(_dep)

        # Slack bus
        self.V_slack_pu = QDoubleSpinBox()
        self.V_slack_pu.setRange(0.5, 1.5)
        self.V_slack_pu.setValue(1.0)
        self.V_slack_pu.setDecimals(3)
        self.V_slack_pu.setSuffix(" pu")
        layout.addRow("V_slack:", self.V_slack_pu)

        # Load bus
        self.P_load_MW = QDoubleSpinBox()
        self.P_load_MW.setRange(-1000.0, 1000.0)
        self.P_load_MW.setValue(50.0)
        self.P_load_MW.setSuffix(" MW")
        layout.addRow("Carga ativa:", self.P_load_MW)

        self.Q_load_MVAr = QDoubleSpinBox()
        self.Q_load_MVAr.setRange(-1000.0, 1000.0)
        self.Q_load_MVAr.setValue(20.0)
        self.Q_load_MVAr.setSuffix(" MVAr")
        layout.addRow("Carga reativa:", self.Q_load_MVAr)

        # Branch
        self.R_pu = QDoubleSpinBox()
        self.R_pu.setRange(0.0, 1.0)
        self.R_pu.setDecimals(4)
        self.R_pu.setValue(0.01)
        self.R_pu.setSuffix(" pu")
        layout.addRow("R linha:", self.R_pu)

        self.X_pu = QDoubleSpinBox()
        self.X_pu.setRange(0.001, 5.0)
        self.X_pu.setDecimals(4)
        self.X_pu.setValue(0.05)
        self.X_pu.setSuffix(" pu")
        layout.addRow("X linha:", self.X_pu)

        # Base
        self.base_MVA = QDoubleSpinBox()
        self.base_MVA.setRange(1.0, 10000.0)
        self.base_MVA.setValue(100.0)
        self.base_MVA.setSuffix(" MVA")
        layout.addRow("Base:", self.base_MVA)

        btn_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
        )
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addRow(btn_box)

    def get_parameters(self) -> dict:
        return {
            "V_slack": self.V_slack_pu.value(),
            "P_load_MW": self.P_load_MW.value(),
            "Q_load_MVAr": self.Q_load_MVAr.value(),
            "R_pu": self.R_pu.value(),
            "X_pu": self.X_pu.value(),
            "base_MVA": self.base_MVA.value(),
        }


# ---------------------------------------------------------------------------
# v3.7.0 (closes SKIPPED_BACKLOG B.2) — bus_role helpers
# ---------------------------------------------------------------------------


def _read_bus_role(bus_component) -> str:
    """Read the ``bus_role`` property from a BUS component (v3.7.0 B.2).

    Returns one of: ``"slack"`` / ``"pv"`` / ``"pq"`` / ``"auto"``.
    Defaults to ``"auto"`` if property absent or value invalid.

    Per BUS.ocomp v3.7.0 schema; see PTW Tutorial §Part 2 p.63.
    """
    valid = {"slack", "pv", "pq", "auto"}
    for prop in getattr(bus_component, "properties", []):
        if getattr(prop, "name", "") == "bus_role":
            val = (prop.value or "").strip().lower()
            return val if val in valid else "auto"
    return "auto"


def _read_bus_voltage_pu(bus_component) -> float:
    """Read voltage set point for slack/PV bus (default 1.0 pu)."""
    # Currently the schema does not expose a slack V_pu setpoint
    # explicitly; default to 1.0. Refinement deferred to v3.7.x.
    return 1.0


def _find_explicit_slack(bus_components):
    """Return the BUS marked ``bus_role: slack``, or None if none."""
    for bus in bus_components:
        if _read_bus_role(bus) == "slack":
            return bus
    return None


def build_pf_system_from_project(project, base_MVA: float = 100.0):
    """v3.3.1 Sub-sprint A: build N-bus :class:`PowerFlowSystem` from PpProject.

    Per audit `v3.3.0_TIER1_AUDIT.md` §A.3: pré-v3.3.1 PowerFlowDialog era
    hard-coded a 2-bus. Esta função extrai topologia real do `.sch`:

    * BUS components → SLACK (first) / PQ (others) buses
    * Tr/sTr/Tr3/CABLE/TLIN components conectam pares de BUS via wire path
    * MOTOR/LOAD components → contribuição P/Q ao bus mais próximo

    Heurística defensiva: se project não tem buses suficientes, retorna
    None (caller cai no fluxo dialog 2-bus legacy).

    Returns
    -------
    PowerFlowSystem | None
        Sistema construído, ou None se project vazio/sem buses.

    References
    ----------
    PTW Tutorial §Part 2 p.63-76 (Run > Balanced System Studies).
    """
    from app.postprocessor.power_flow import PowerFlowSystem
    if project is None or not getattr(project, "components", []):
        return None
    bus_components = [c for c in project.components if c.type == "BUS"]
    if len(bus_components) < 1:
        return None

    sys = PowerFlowSystem(base_MVA=base_MVA)
    # v3.7.0 (closes SKIPPED_BACKLOG B.2) — read bus_role property; fall back
    # to legacy "first BUS = SLACK" heuristic when role is "auto" or absent.
    # Per IEEE 399 §5 + PTW Tutorial §Part 2 p.63.
    explicit_slack = _find_explicit_slack(bus_components)
    slack_bus = explicit_slack or bus_components[0]
    sys.add_slack(id=slack_bus.name, V_pu=_read_bus_voltage_pu(slack_bus))

    for bus in bus_components:
        if bus.name == slack_bus.name:
            continue  # already added as slack
        role = _read_bus_role(bus)
        if role == "pv":
            # PV bus — needs V and P; default V=1.0, P=0
            sys.add_pv(
                id=bus.name,
                V_pu=_read_bus_voltage_pu(bus),
                P_pu=0.0,
            ) if hasattr(sys, "add_pv") else sys.add_pq(
                id=bus.name, P_pu=0.0, Q_pu=0.0,
            )
        elif role == "slack":
            # Multiple slacks declared — defensive fallback to PQ for the
            # extras (only one slack is mathematically meaningful).
            sys.add_pq(id=bus.name, P_pu=0.0, Q_pu=0.0)
        else:
            # role in ("pq", "auto", or unknown)
            sys.add_pq(id=bus.name, P_pu=0.0, Q_pu=0.0)

    # Apply LOAD components — assign to bus that shares (x,y) area heuristic
    for comp in project.components:
        if comp.type != "LOAD":
            continue
        # Find nearest BUS by Manhattan distance
        nearest = min(
            bus_components,
            key=lambda b: abs(b.x - comp.x) + abs(b.y - comp.y),
            default=None,
        )
        if nearest is None or nearest.name == bus_components[0].name:
            continue
        # Extract kW / kVAR from properties (heuristic per build_equipment_from_project)
        kw_val = 0.0
        kvar_val = 0.0
        for prop in comp.properties:
            v_str = prop.value.strip().lower() if prop.value else ""
            try:
                val = float(v_str.split()[0])
            except (ValueError, IndexError):
                continue
            if "kvar" in v_str:
                kvar_val = val
            elif "kw" in v_str:
                kw_val = val
        # Update existing PQ bus
        for b in sys.buses:
            if b.id == nearest.name:
                b.P_pu_set -= kw_val / (base_MVA * 1000)  # MW base
                b.Q_pu_set -= kvar_val / (base_MVA * 1000)
                break

    # v3.7.1 (closes SKIPPED_BACKLOG B.1) — extract real R/X from
    # Tr/sTr/Tr3/CABLE/TLIN components. For each adjacent bus pair, find
    # the best matching branch component (by Manhattan proximity) and
    # use its impedance. Falls back to default (R=0.01, X=0.05) if no
    # matching component found. Per IEC 60076-1 (Tr) + IEC 60364 (CABLE).
    from app.postprocessor.branch_impedance import (
        extract_branch_impedance,
        DEFAULT_BRANCH_R_PU,
        DEFAULT_BRANCH_X_PU,
    )
    branch_components = [
        c for c in project.components
        if (getattr(c, "type", "") in ("Tr", "sTr", "Tr3", "CABLE", "TLIN"))
    ]
    for i in range(len(bus_components) - 1):
        b_from = bus_components[i]
        b_to = bus_components[i + 1]
        # Heuristic: pick the branch component closest to the midpoint
        # of the two buses (Manhattan distance).
        mid_x = (b_from.x + b_to.x) / 2
        mid_y = (b_from.y + b_to.y) / 2
        best = min(
            branch_components,
            key=lambda c: abs(c.x - mid_x) + abs(c.y - mid_y),
            default=None,
        )
        if best is not None:
            v_base = 13.8  # heuristic; refinement via b_from rated_voltage_kV
            for prop in getattr(b_from, "properties", []):
                if getattr(prop, "name", "") == "rated_voltage_kV":
                    try:
                        v_base = float(str(prop.value).split()[0])
                    except (ValueError, IndexError):
                        pass
                    break
            z = extract_branch_impedance(
                best, base_MVA=base_MVA, voltage_base_kV=v_base,
            )
            R_pu, X_pu, B_pu = z.R_pu, z.X_pu, z.B_pu
        else:
            R_pu, X_pu, B_pu = DEFAULT_BRANCH_R_PU, DEFAULT_BRANCH_X_PU, 0.0
        sys.add_branch(
            from_bus=b_from.name,
            to_bus=b_to.name,
            R_pu=R_pu, X_pu=X_pu, B_pu=B_pu,
        )
    return sys


def run_power_flow_analysis(
    parent: QWidget, *, project=None, **kwargs,
) -> None:
    try:
        import numpy  # noqa: F401
    except ImportError:
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.critical(
            parent, "Numpy não disponível",
            "Power Flow requer numpy. Instale com `pip install numpy`.",
        )
        return

    from app.postprocessor.power_flow import PowerFlowSystem

    # v3.3.1 Sub-sprint A: try N-bus from project first, fall back to 2-bus dialog.
    sys = build_pf_system_from_project(project) if project else None
    if sys is not None and len(sys.buses) >= 2:
        # N-bus path: skip dialog, run directly with project topology
        try:
            sol = sys.solve()
        except Exception as e:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(parent, "Erro PF (N-bus)", str(e))
            return
        # Skip the rest (datablock cache + result dialog) to common path
        text = sol.summary()
        text = (
            f"Power Flow Newton-Raphson — {len(sys.buses)}-bus from project\n"
            f"Reference: PTW Tutorial §Part 2 p.63-76\n"
            "=" * 60 + "\n" + text
        )
        try:
            if hasattr(parent, "study_cache"):
                parent.study_cache.set_pf(
                    sol, system_hash=hash(tuple(b.id for b in sys.buses)),
                )
            from app.gui.plot_dock_refresh import refresh_pf_dock_if_open
            refresh_pf_dock_if_open(parent)
        except Exception:  # noqa: BLE001
            pass
        show_result_dialog(parent, "Resultado PF (N-bus)", text)
        return

    # 2-bus legacy path (no project or project too small)
    dlg = PowerFlowDialog(parent)
    if dlg.exec() != QDialog.Accepted:
        return
    p = dlg.get_parameters()

    sys = PowerFlowSystem(base_MVA=p["base_MVA"])
    sys.add_slack(id="SLACK", V_pu=p["V_slack"])
    sys.add_pq(
        id="LOAD",
        P_pu=-p["P_load_MW"] / p["base_MVA"],
        Q_pu=-p["Q_load_MVAr"] / p["base_MVA"],
    )
    sys.add_branch(
        from_bus="SLACK", to_bus="LOAD",
        R_pu=p["R_pu"], X_pu=p["X_pu"],
    )
    try:
        sol = sys.solve()
    except Exception as e:
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.critical(parent, "Erro PF", str(e))
        return

    # v0.88: armazena PF solution no cache (best-effort) e refresh
    # datablocks. Os bus_ids vêm de ``sol.bus_voltages_pu``; se
    # corresponderem a BUSes do schematic, datablocks com template
    # PF serão substituídos. Caso contrário, nada acontece — sem
    # erro.
    try:
        _store_pf_and_refresh_datablocks(parent, sol)
    except Exception:
        pass

    show_result_dialog(parent, "Fluxo de Potência", sol.summary())


def _store_pf_and_refresh_datablocks(parent, solution) -> int:
    """v0.88: armazena PowerFlowSolution no cache (1 entry por
    bus_id presente em ``solution.bus_voltages_pu``) e refresca
    todos os datablocks. Retorna # datablocks atualizados.
    """
    try:
        scene = parent.schematic_pp.scene  # type: ignore[attr-defined]
    except AttributeError:
        return 0
    cache = getattr(scene, "results_cache", None)
    if cache is None:
        return 0
    bv = getattr(solution, "bus_voltages_pu", None) or {}
    for bus_id in bv.keys():
        cache.set_pf_solution(str(bus_id), solution)
    from app.gui.schematic_pp.datablock_binder import (
        refresh_datablocks_from_cache,
    )
    return refresh_datablocks_from_cache(scene, cache)


# ---------------------------------------------------------------------------
# Motor starting dialog
# ---------------------------------------------------------------------------


class MotorStartingDialog(QDialog):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Partida de Motor (IEEE 399)")
        self.setModal(True)
        self.resize(450, 500)
        layout = QFormLayout(self)

        self.power_kW = QDoubleSpinBox()
        self.power_kW.setRange(1.0, 100000.0)
        self.power_kW.setValue(1000.0)
        self.power_kW.setSuffix(" kW")
        layout.addRow("Potência nominal:", self.power_kW)

        self.voltage_kV = QDoubleSpinBox()
        self.voltage_kV.setRange(0.208, 15.0)
        self.voltage_kV.setValue(4.16)
        self.voltage_kV.setDecimals(3)
        self.voltage_kV.setSuffix(" kV")
        layout.addRow("Tensão nominal:", self.voltage_kV)

        self.pf = QDoubleSpinBox()
        self.pf.setRange(0.5, 1.0)
        self.pf.setDecimals(3)
        self.pf.setValue(0.85)
        layout.addRow("PF nominal:", self.pf)

        self.efficiency = QDoubleSpinBox()
        self.efficiency.setRange(0.5, 1.0)
        self.efficiency.setDecimals(3)
        self.efficiency.setValue(0.95)
        layout.addRow("Rendimento:", self.efficiency)

        self.lr_ratio = QDoubleSpinBox()
        self.lr_ratio.setRange(3.0, 12.0)
        self.lr_ratio.setValue(6.0)
        layout.addRow("I_LR / I_n:", self.lr_ratio)

        self.starting_pf = QDoubleSpinBox()
        self.starting_pf.setRange(0.10, 0.50)
        self.starting_pf.setDecimals(3)
        self.starting_pf.setValue(0.30)
        layout.addRow("PF na partida:", self.starting_pf)

        self.starting_torque = QDoubleSpinBox()
        self.starting_torque.setRange(0.1, 3.0)
        self.starting_torque.setValue(1.5)
        self.starting_torque.setSuffix(" pu")
        layout.addRow("Torque partida:", self.starting_torque)

        self.inertia = QDoubleSpinBox()
        self.inertia.setRange(0.1, 1000.0)
        self.inertia.setValue(20.0)
        self.inertia.setSuffix(" kg·m²")
        layout.addRow("Inércia:", self.inertia)

        self.bus_v_pu = QDoubleSpinBox()
        self.bus_v_pu.setRange(0.5, 1.2)
        self.bus_v_pu.setValue(1.0)
        self.bus_v_pu.setDecimals(3)
        self.bus_v_pu.setSuffix(" pu")
        layout.addRow("V pré-partida:", self.bus_v_pu)

        self.zth_ohm = QDoubleSpinBox()
        self.zth_ohm.setRange(0.001, 100.0)
        self.zth_ohm.setDecimals(4)
        self.zth_ohm.setValue(0.5)
        self.zth_ohm.setSuffix(" Ω")
        layout.addRow("|Z_th| sistema:", self.zth_ohm)

        self.load_combo = QComboBox()
        self.load_combo.addItem("Constante (guincho/esteira)", "constant")
        self.load_combo.addItem("Linear (ventilador axial)", "linear")
        self.load_combo.addItem(
            "Quadrática (ventilador centrífugo, bomba)", "quadratic",
        )
        self.load_combo.addItem("Cúbica (compressor)", "cubic")
        layout.addRow("Tipo de carga:", self.load_combo)

        btn_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
        )
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addRow(btn_box)

    def get_parameters(self) -> dict:
        return {
            "power_kW": self.power_kW.value(),
            "voltage_kV": self.voltage_kV.value(),
            "pf": self.pf.value(),
            "efficiency": self.efficiency.value(),
            "lr_ratio": self.lr_ratio.value(),
            "starting_pf": self.starting_pf.value(),
            "starting_torque": self.starting_torque.value(),
            "inertia": self.inertia.value(),
            "bus_v_pu": self.bus_v_pu.value(),
            "zth_ohm": self.zth_ohm.value(),
            "load_type": self.load_combo.currentData(),
        }


def run_motor_starting_analysis(
    parent: QWidget, *, project=None, bus_id: str = "", **kwargs,
) -> None:
    from app.postprocessor.motor_starting import (
        LoadType, MotorStartingCase, analyze_motor_starting,
    )
    dlg = MotorStartingDialog(parent)
    if dlg.exec() != QDialog.Accepted:
        return
    p = dlg.get_parameters()
    case = MotorStartingCase(
        motor_name="MOTOR",
        motor_rated_power_kW=p["power_kW"],
        motor_rated_voltage_kV=p["voltage_kV"],
        motor_rated_pf=p["pf"],
        motor_efficiency=p["efficiency"],
        locked_rotor_current_pu=p["lr_ratio"],
        starting_pf=p["starting_pf"],
        starting_torque_pu=p["starting_torque"],
        load_torque_pu=1.0,
        inertia_motor_kg_m2=p["inertia"],
        bus_pre_fault_voltage_pu=p["bus_v_pu"],
        bus_thevenin_impedance_ohm=p["zth_ohm"],
        bus_rated_voltage_kV=p["voltage_kV"],
        load_type=LoadType(p["load_type"]),
    )
    rpt = analyze_motor_starting(case)
    show_result_dialog(parent, "Partida de Motor", rpt.summary())


# ---------------------------------------------------------------------------
# Arc-flash dialog
# ---------------------------------------------------------------------------


class ArcFlashDialog(QDialog):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Arc-Flash (IEEE 1584 / NBR 17227)")
        self.setModal(True)
        self.resize(500, 450)
        layout = QFormLayout(self)

        self.voltage_kV = QDoubleSpinBox()
        self.voltage_kV.setRange(0.208, 15.0)
        self.voltage_kV.setValue(13.8)
        self.voltage_kV.setDecimals(3)
        self.voltage_kV.setSuffix(" kV")
        layout.addRow("Tensão (Voc):", self.voltage_kV)

        self.Ibf_kA = QDoubleSpinBox()
        self.Ibf_kA.setRange(0.2, 106.0)
        self.Ibf_kA.setValue(20.0)
        self.Ibf_kA.setSuffix(" kA")
        layout.addRow("Ibf (falta franca):", self.Ibf_kA)

        self.T_ms = QDoubleSpinBox()
        self.T_ms.setRange(10.0, 5000.0)
        self.T_ms.setValue(200.0)
        self.T_ms.setSuffix(" ms")
        layout.addRow("Tempo de extinção:", self.T_ms)

        self.equipment_combo = QComboBox()
        self.equipment_combo.addItem("CCM 15 kV", "ccm_15kv")
        self.equipment_combo.addItem("Switchgear 15 kV", "swgr_15kv")
        self.equipment_combo.addItem("CCM 5 kV", "ccm_5kv")
        self.equipment_combo.addItem("Switchgear 5 kV", "swgr_5kv")
        self.equipment_combo.addItem("Painel BT raso", "lv_panel_shallow")
        self.equipment_combo.addItem("Painel BT típico", "lv_panel_typical")
        self.equipment_combo.addItem("Switchgear BT", "lv_swgr")
        self.equipment_combo.addItem("Caixa de junção", "cable_jct_box")
        layout.addRow("Tipo de equipamento:", self.equipment_combo)

        self.electrode_combo = QComboBox()
        self.electrode_combo.addItem(
            "VCB — Vertical em invólucro", "VCB",
        )
        self.electrode_combo.addItem(
            "VCBB — Vertical com barreira", "VCBB",
        )
        self.electrode_combo.addItem(
            "HCB — Horizontal em invólucro", "HCB",
        )
        self.electrode_combo.addItem("VOA — Vertical ar livre", "VOA")
        self.electrode_combo.addItem("HOA — Horizontal ar livre", "HOA")
        layout.addRow("Configuração eletrodos:", self.electrode_combo)

        btn_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
        )
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addRow(btn_box)

    def get_parameters(self) -> dict:
        return {
            "voltage_kV": self.voltage_kV.value(),
            "Ibf_kA": self.Ibf_kA.value(),
            "T_ms": self.T_ms.value(),
            "equipment": self.equipment_combo.currentData(),
            "electrode": self.electrode_combo.currentData(),
        }


def run_arc_flash_analysis(
    parent: QWidget, *, project=None, bus_id: str = "", **kwargs,
) -> None:
    from app.postprocessor.arc_flash import (
        ArcFlashCase, calculate_arc_flash,
    )
    from app.standards.nbr17227 import (
        ElectrodeConfig, EquipmentClass,
    )

    dlg = ArcFlashDialog(parent)
    if dlg.exec() != QDialog.Accepted:
        return
    p = dlg.get_parameters()
    try:
        case = ArcFlashCase(
            bus_name="BUS",
            rated_voltage_kV=p["voltage_kV"],
            bolted_fault_current_kA=p["Ibf_kA"],
            arc_clearing_time_ms=p["T_ms"],
            equipment_class=EquipmentClass(p["equipment"]),
            electrode_config=ElectrodeConfig(p["electrode"]),
        )
        rpt = calculate_arc_flash(case)
        show_result_dialog(
            parent, "Arc-Flash — Resultado", rpt.summary(),
        )
    except Exception as e:
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.critical(parent, "Erro Arc-Flash", str(e))


# ---------------------------------------------------------------------------
# Bus pipeline (full study) — uses current ATP/PP project if available
# ---------------------------------------------------------------------------


def run_bus_pipeline_analysis(
    parent: QWidget, project=None, *, bus_id: str = "", **kwargs,
) -> None:
    """
    Pipeline completo do bus. Requer um PpProject com ao menos um
    componente BUS conectado a fontes (Vac/SM/TR).
    """
    from PySide6.QtWidgets import QMessageBox

    if project is None:
        QMessageBox.warning(
            parent, "Estudo do Barramento",
            "Carregue primeiro um projeto .sch (Esquemático Visual) "
            "com componentes BUS conectados a fontes de SC.",
        )
        return

    from app.postprocessor.bus_pipeline import analyze_bus_full_pipeline

    # Lista buses disponíveis
    bus_ids = []
    for c in project.components:
        if c.type == "BUS":
            bus_id = (c.get(0, "") or "").strip() or c.name
            bus_ids.append(bus_id)
    if not bus_ids:
        QMessageBox.warning(
            parent, "Estudo do Barramento",
            "Nenhum componente BUS encontrado no projeto.",
        )
        return

    # Picker simples
    from PySide6.QtWidgets import QInputDialog
    bus_id, ok = QInputDialog.getItem(
        parent, "Selecione o BUS",
        "Para qual barramento deseja executar o pipeline?",
        bus_ids, editable=False,
    )
    if not ok:
        return

    try:
        report = analyze_bus_full_pipeline(
            project, bus_id,
            coordination_clearing_time_ms=500.0,
        )
        # v0.87: armazena no cache do scene + atualiza datablocks
        # ancorados a este bus. Best-effort — se algo der errado
        # no scene/datablocks, o relatório principal não trava.
        try:
            _store_report_and_refresh_datablocks(parent, bus_id, report)
        except Exception:
            pass
        show_result_dialog(
            parent,
            f"Estudo Completo — {bus_id}",
            report.summary(),
            width=900, height=700,
        )
    except Exception as e:
        QMessageBox.critical(parent, "Erro Pipeline", str(e))


def _store_report_and_refresh_datablocks(
    parent, bus_id: str, report,
) -> int:
    """
    v0.87: localiza o ``PpScene`` ativo via ``parent.schematic_pp.scene``,
    armazena ``report`` no ``results_cache`` e refresca todos os
    datablocks ancorados a esse bus. Retorna # datablocks atualizados.

    Em testes ou contextos sem MainWindow, retorna 0 silentemente.
    """
    try:
        scene = parent.schematic_pp.scene  # type: ignore[attr-defined]
    except AttributeError:
        return 0
    cache = getattr(scene, "results_cache", None)
    if cache is None:
        return 0
    cache.set_pipeline_report(bus_id, report)
    from app.gui.schematic_pp.datablock_binder import (
        refresh_datablocks_from_cache,
    )
    return refresh_datablocks_from_cache(scene, cache)


# ---------------------------------------------------------------------------
# HTML/PDF report (rich, from postprocessor.report_html / report_pdf)
# ---------------------------------------------------------------------------


def run_pipeline_report_export(parent: QWidget, project=None) -> None:
    """Exporta relatório rico HTML+PDF de um BUS via bus_pipeline."""
    from PySide6.QtWidgets import (
        QFileDialog, QInputDialog, QMessageBox,
    )

    if project is None:
        QMessageBox.warning(
            parent, "Relatório completo",
            "Carregue primeiro um projeto .sch com BUS.",
        )
        return

    from app.postprocessor.bus_pipeline import analyze_bus_full_pipeline

    bus_ids = []
    for c in project.components:
        if c.type == "BUS":
            bus_id = (c.get(0, "") or "").strip() or c.name
            bus_ids.append(bus_id)
    if not bus_ids:
        QMessageBox.warning(
            parent, "Relatório completo", "Nenhum BUS encontrado.",
        )
        return

    bus_id, ok = QInputDialog.getItem(
        parent, "Selecione o BUS",
        "Bus para gerar relatório completo:",
        bus_ids, editable=False,
    )
    if not ok:
        return

    fmt, ok = QInputDialog.getItem(
        parent, "Formato",
        "Formato do relatório:",
        ["HTML", "PDF"], editable=False,
    )
    if not ok:
        return

    suffix = ".html" if fmt == "HTML" else ".pdf"
    path, _ = QFileDialog.getSaveFileName(
        parent, f"Salvar relatório {fmt}",
        f"report-{bus_id}{suffix}",
        f"{fmt} files (*{suffix})",
    )
    if not path:
        return

    try:
        report = analyze_bus_full_pipeline(
            project, bus_id,
            coordination_clearing_time_ms=500.0,
            multi_vendor_suggestions=True,
        )
        if fmt == "HTML":
            from app.postprocessor.report_html import save_html_report
            save_html_report(report, path)
        else:
            from app.postprocessor.report_pdf import save_pdf_report
            save_pdf_report(report, path)
        QMessageBox.information(
            parent, "Relatório gerado",
            f"Salvo em: {path}",
        )
    except Exception as e:
        QMessageBox.critical(parent, "Erro relatório", str(e))
