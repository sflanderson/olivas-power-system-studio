"""
tests.test_v1_4_5_user_gate_fixes — User Gate v1.4.4 → v1.4.5.

Cobre os 4 fixes do user audit pós-v1.4.4:

  Sprint A: Remover menções PTW enganosas (sem integração real)
  Sprint B: Layout dos plots (constrained_layout + subplot spacing)
  Sprint C: Workflow exige TC selecionado no canvas
  Sprint D: Menu Visualizar > Gráficos com empty states
"""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


# ===========================================================================
# Sprint A — Fix 1: Remover menções PTW enganosas
# ===========================================================================


class TestFixA_RemovePTWMentions:

    def test_ctsat_button_no_ptw_in_label(self, qapp):
        """Botão de carregar JSON NÃO deve conter substring 'PTW' visível."""
        from app.gui.ct_saturation_dialog import CTSaturationDialog
        dlg = CTSaturationDialog()
        text = dlg.btn_load_json.text()
        assert "PTW" not in text, (
            f"Botão de import contém 'PTW' (engano): {text!r}"
        )

    def test_ctsat_button_tooltip_or_label_describes_purpose(self, qapp):
        """Tooltip OU label deve descrever que importa dados de TCs."""
        from app.gui.ct_saturation_dialog import CTSaturationDialog
        dlg = CTSaturationDialog()
        combined = (
            (dlg.btn_load_json.text() or "") + " "
            + (dlg.btn_load_json.toolTip() or "")
        )
        # Aceita variações: "TC", "TCs", "JSON", "Importar"
        assert any(
            kw in combined
            for kw in ("TC", "JSON", "Importar", "importar")
        ), f"Botão sem descrição clara de propósito: {combined!r}"

    def test_io_module_docstring_mentions_neutral_format(self):
        """Docstring de ct_saturation_io NÃO deve dizer 'PTW' como
        produto integrado — só como compatibilidade."""
        from app.postprocessor import ct_saturation_io
        doc = ct_saturation_io.__doc__ or ""
        # Permitido se contextualizado ("compatível com PTW")
        # Proibido se for "do PTW" como integração ativa
        if "PTW" in doc:
            assert (
                "compatível" in doc.lower()
                or "compat" in doc.lower()
                or "exportado de" in doc.lower()
                or "outras ferramentas" in doc.lower()
            ), (
                "Menção a PTW deve ser apenas como compatibilidade, "
                "não integração."
            )


# ===========================================================================
# Sprint B — Fix 2: Layout dos plots
# ===========================================================================


@pytest.fixture
def passing_report():
    """Report didático para testes de layout."""
    from app.postprocessor.ct_saturation import (
        CTFaultContext, CTSpec, analyze_full,
        typical_magnetization_curve,
    )
    fault = CTFaultContext(
        bus_id="BUS-OK", rated_voltage_kV=13.8,
        I_fault_rms_kA=10.0, X_over_R=8.0,
    )
    ct = CTSpec(
        tag="CT-OK", tipo_TC="ANSI_C",
        I_pri_nom_tap=1200, I_pri_nom_full=1200, I_sn=5,
        CT_Rating_C=800.0, R_s=0.5, R_b=0.3,
        curve=typical_magnetization_curve(800.0),
        Kr=0.1,
    )
    return analyze_full(ct, fault)


class TestFixB_PlotLayout:

    def test_level3_uses_constrained_layout(self, passing_report):
        """Plot N3 deve usar constrained_layout (evita sobreposição)."""
        from app.gui.ct_saturation_plots import plot_level3_dynamic
        fig = plot_level3_dynamic(passing_report)
        # constrained_layout=True deixa engine como 'constrained'
        engine = fig.get_layout_engine()
        engine_name = type(engine).__name__ if engine else "None"
        assert "Constrained" in engine_name or "constrained" in engine_name, (
            f"Plot N3 deveria usar constrained_layout; engine={engine_name}"
        )

    def test_level3_subplot2_no_title_overlapping(self, passing_report):
        """
        Subplot 2 (correntes) NÃO deve ter set_title (que sobrepõe
        eixo do subplot 1). Em vez disso, info vai no ylabel.
        """
        from app.gui.ct_saturation_plots import plot_level3_dynamic
        fig = plot_level3_dynamic(passing_report)
        ax2 = fig.axes[1]
        title = ax2.get_title()
        assert title == "" or len(title) < 5, (
            f"Subplot 2 ainda tem título sobreposto: {title!r}"
        )

    def test_dialog_size_is_at_least_1280_wide(self, qapp):
        """Janela do dialog ≥ 1280 px de largura para acomodar plots."""
        from app.gui.ct_saturation_dialog import CTSaturationDialog
        dlg = CTSaturationDialog()
        # size().width() pode ser inicial ou de resize — ambos OK
        w = max(dlg.width(), dlg.minimumWidth(), 0)
        assert w >= 1280, f"Dialog largura={w} < 1280"


# ===========================================================================
# Sprint C — Fix 3: Workflow exige TC selecionado
# ===========================================================================


class TestFixC_CTSelectionRequired:

    def test_ctselection_dataclass_loadable(self):
        from app.postprocessor.ct_saturation_io import CTSelection
        assert CTSelection is not None

    def test_ctselection_from_pp_component(self):
        """CTSelection.from_pp_component lê properties do CT.ocomp."""
        from app.preprocessor.models import PpComponent, PpProperty
        from app.preprocessor.spec import get_default_registry
        from app.postprocessor.ct_saturation_io import CTSelection

        spec = get_default_registry().get("CT")
        assert spec is not None, "CT spec deve existir em catalog_specs"

        props = []
        for p in spec.properties:
            default = str(p.default) if p.default is not None else ""
            props.append(PpProperty(value=default, visible=p.visible))

        comp = PpComponent(
            type="CT", name="CT-TEST",
            visible=True, x=0, y=0,
            label_dx=0, label_dy=0, mirror=0, rotation=0,
            properties=props,
        )
        sel = CTSelection.from_pp_component(comp)
        assert sel.tag is not None
        assert sel.ratio_pri_A > 0
        assert sel.classe in ("ANSI_C", "IEC_P", "IEC_PR")

    def test_dialog_with_selection_populates_form(self, qapp):
        """Dialog construído com selection popula tag + ratio + classe."""
        from app.gui.ct_saturation_dialog import CTSaturationDialog
        from app.postprocessor.ct_saturation_io import CTSelection

        sel = CTSelection(
            tag="CT-SEL",
            ratio_pri_A=600.0,
            ratio_sec_A=5.0,
            classe="ANSI_C",
            c_rating_V=400.0,
            rs_ohm=0.4,
            rb_ohm=0.5,
            kr=0.1,
            t_relay_ms=20.0,
            t_breaker_ms=50.0,
            bus_id="BUS-13.8",
            rated_voltage_kV=13.8,
            I_fault_rms_kA=15.0,
            X_over_R=8.0,
        )
        dlg = CTSaturationDialog(selection=sel)
        # tag
        assert dlg.tag.currentText() == "CT-SEL"
        # bus_id
        assert "BUS-13.8" in dlg.bus_id.currentText()
        # ratings
        assert dlg.I_pri_nom_tap.value() == 600
        assert dlg.CT_Rating_C.value() == 400.0

    def test_dialog_without_selection_uses_didactic_defaults(self, qapp):
        """Dialog sem selection mantém comportamento didático antigo."""
        from app.gui.ct_saturation_dialog import CTSaturationDialog
        dlg = CTSaturationDialog()
        # default tag não vazio
        assert dlg.tag.currentText() != ""
        # form preenchido para rodar análise auto
        assert dlg._last_report is not None


# ===========================================================================
# Sprint D — Fix 4: Menu Visualizar > Gráficos com empty states
# ===========================================================================


class TestFixD_EmptyStates:

    def test_voltage_profile_dock_has_empty_state_method(self, qapp):
        """
        PowerFlowVoltageProfileDock deve expor empty_state_visible
        ou método show_empty_state quando aberto sem dados.
        """
        from app.gui.plot_widgets import PowerFlowVoltageProfileDock
        dock = PowerFlowVoltageProfileDock()
        # Pelo menos um dos atributos abaixo:
        has_empty_api = (
            hasattr(dock, "show_empty_state")
            or hasattr(dock, "_empty_state_label")
            or hasattr(dock, "is_empty")
        )
        assert has_empty_api, (
            "Dock sem API para empty state — precisa show_empty_state, "
            "_empty_state_label ou is_empty"
        )

    def test_voltage_profile_dock_default_state_is_empty(self, qapp):
        """Sem update_data, dock está em empty state."""
        from app.gui.plot_widgets import PowerFlowVoltageProfileDock
        dock = PowerFlowVoltageProfileDock()
        # API é_empty deve retornar True por default
        if hasattr(dock, "is_empty"):
            assert dock.is_empty() is True

    def test_sc_pie_dock_empty_state_explains_prereq(self, qapp):
        """Dock de Source Contributions deve explicar prerequisito."""
        from app.gui.plot_widgets import ScContributionPieDock
        dock = ScContributionPieDock()
        # Procura QLabel central com texto "Curto-circuito" ou "Short"
        from PySide6.QtWidgets import QLabel
        labels = dock.findChildren(QLabel)
        text_concat = " ".join(
            (lb.text() or "") for lb in labels
        )
        assert any(
            kw in text_concat.lower()
            for kw in ("curto", "short", "executar", "f5")
        ), f"Dock SC sem texto explicativo de prereq: {text_concat!r}"
