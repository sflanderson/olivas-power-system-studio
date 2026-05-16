"""
tests/test_pp_v3_4_0_tcc_extensions.py — v3.4.0.

TCC Editor extensions:
* Sprint 1 — C-lines (constant IE) overlay
* Sprint 2 — TCC Report export (text/markdown/csv)
* Sprint 3 — TCCCoordinogramDialog wiring (buttons accessible)
"""

from __future__ import annotations

import os
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication
    import sys
    return QApplication.instance() or QApplication(sys.argv)


# ===========================================================================
# Sprint 1 — C-lines (constant Incident Energy)
# ===========================================================================


class TestCLinesBackend:

    def test_compute_default_c_lines_returns_5(self):
        """Default 5 C-lines: 1.2/4/8/25/40 cal/cm²."""
        from app.postprocessor.tcc_c_lines import compute_default_c_lines
        lines = compute_default_c_lines()
        assert len(lines) == 5

    def test_c_lines_ie_levels_match_nfpa(self):
        """IE levels match NFPA 70E Annex H thresholds."""
        from app.postprocessor.tcc_c_lines import compute_default_c_lines
        lines = compute_default_c_lines()
        ies = [c.incident_energy_cal_cm2 for c in lines]
        assert ies == [1.2, 4.0, 8.0, 25.0, 40.0]

    def test_c_line_has_points(self):
        """Each C-line has > 0 points (I_kA, t_s)."""
        from app.postprocessor.tcc_c_lines import compute_default_c_lines
        lines = compute_default_c_lines()
        for cl in lines:
            assert len(cl.points) > 0
            for I_kA, t_s in cl.points:
                assert I_kA > 0
                assert t_s > 0

    def test_c_line_t_decreases_with_I(self):
        """t(I) deve diminuir conforme I aumenta (mesmo IE = mais I → menos t)."""
        from app.postprocessor.tcc_c_lines import compute_c_line_ieee_1584
        cl = compute_c_line_ieee_1584(
            incident_energy_cal_cm2=4.0, n_points=10,
        )
        # Points sorted by I; check t monotonically decreases
        ts = [t for I, t in cl.points]
        for i in range(len(ts) - 1):
            assert ts[i] >= ts[i + 1]  # non-increasing

    def test_ppe_category_for_ie(self):
        """ppe_category_for_ie matches NFPA 70E Tab H.3(b)."""
        from app.postprocessor.tcc_c_lines import ppe_category_for_ie
        assert ppe_category_for_ie(0.5) == 0   # below threshold
        assert ppe_category_for_ie(1.5) == 1   # 1.2-4.0
        assert ppe_category_for_ie(4.0) == 1   # boundary
        assert ppe_category_for_ie(6.0) == 2   # 4.0-8.0
        assert ppe_category_for_ie(20.0) == 3  # 8.0-25.0
        assert ppe_category_for_ie(35.0) == 4  # 25.0-40.0
        assert ppe_category_for_ie(50.0) == 5  # above 40 (extreme)

    def test_invalid_ie_raises(self):
        from app.postprocessor.tcc_c_lines import compute_c_line_ieee_1584
        with pytest.raises(ValueError):
            compute_c_line_ieee_1584(incident_energy_cal_cm2=0.0)
        with pytest.raises(ValueError):
            compute_c_line_ieee_1584(
                incident_energy_cal_cm2=4.0, i_min_kA=0.0,
            )


# ===========================================================================
# Sprint 2 — TCC Report
# ===========================================================================


class TestTccReport:

    def test_empty_report_creates(self):
        from app.postprocessor.tcc_report import TccReport
        r = TccReport(project_name="X")
        assert r.project_name == "X"
        assert r.devices == []

    def test_add_device_increments(self):
        from app.postprocessor.tcc_report import TccDeviceEntry, TccReport
        r = TccReport(project_name="X")
        r.add_device(TccDeviceEntry(device_id="Q1"))
        r.add_device(TccDeviceEntry(device_id="F1"))
        assert len(r.devices) == 2

    def test_sort_by_bus_voltage_descending(self):
        from app.postprocessor.tcc_report import TccDeviceEntry, TccReport
        r = TccReport(project_name="X")
        r.add_device(TccDeviceEntry(device_id="LV", bus_voltage_kV=0.480))
        r.add_device(TccDeviceEntry(device_id="HV", bus_voltage_kV=13.8))
        r.add_device(TccDeviceEntry(device_id="MV", bus_voltage_kV=4.16))
        r.sort_by_bus_voltage(descending=True)
        assert [d.device_id for d in r.devices] == ["HV", "MV", "LV"]

    def test_format_text_contains_header(self):
        from app.postprocessor.tcc_report import TccReport
        r = TccReport(project_name="MyProject")
        text = r.format_text()
        assert "MyProject" in text
        assert "TCC COORDINATION REPORT" in text
        assert "PTW Tutorial" in text  # anti-alucinação cite

    def test_format_markdown_table(self):
        from app.postprocessor.tcc_report import TccDeviceEntry, TccReport
        r = TccReport(project_name="X")
        r.add_device(TccDeviceEntry(device_id="Q1", bus_voltage_kV=13.8))
        md = r.format_markdown()
        assert "| Device |" in md
        assert "| Q1 |" in md

    def test_format_csv_parseable(self):
        import io
        import csv as csv_mod
        from app.postprocessor.tcc_report import TccDeviceEntry, TccReport
        r = TccReport(project_name="X")
        r.add_device(TccDeviceEntry(
            device_id="Q1", bus_voltage_kV=13.8, pickup_A=400.0,
        ))
        csv_text = r.format_csv()
        rows = list(csv_mod.DictReader(io.StringIO(csv_text)))
        assert len(rows) == 1
        assert rows[0]["device_id"] == "Q1"
        assert float(rows[0]["bus_voltage_kV"]) == pytest.approx(13.8)

    def test_format_csv_escapes_notes_with_pipe(self):
        from app.postprocessor.tcc_report import TccDeviceEntry, TccReport
        r = TccReport(project_name="X")
        r.add_device(TccDeviceEntry(
            device_id="Q1", notes='Note "with quotes"',
        ))
        csv_text = r.format_csv()
        # CSV double-quoted fields should escape internal "
        assert 'Note ""with quotes""' in csv_text


# ===========================================================================
# Sprint 3 — TCCCoordinogramDialog wiring
# ===========================================================================


class TestDialogWiring:

    def test_dialog_has_c_lines_button(self, qapp):
        from app.gui.tcc_coordinogram import TCCCoordinogramDialog
        dlg = TCCCoordinogramDialog()
        assert hasattr(dlg, "_btn_c_lines")
        assert dlg._btn_c_lines.isCheckable()

    def test_dialog_has_export_button(self, qapp):
        from app.gui.tcc_coordinogram import TCCCoordinogramDialog
        dlg = TCCCoordinogramDialog()
        assert hasattr(dlg, "_btn_export_report")

    def test_c_lines_toggle_handler_exists(self, qapp):
        from app.gui.tcc_coordinogram import TCCCoordinogramDialog
        dlg = TCCCoordinogramDialog()
        assert callable(dlg._on_c_lines_toggled)

    def test_export_report_handler_exists(self, qapp):
        from app.gui.tcc_coordinogram import TCCCoordinogramDialog
        dlg = TCCCoordinogramDialog()
        assert callable(dlg._on_export_tcc_report)

    def test_c_lines_toggle_on_off(self, qapp):
        """C-lines toggle ON populates _coord_widget._c_lines."""
        from app.gui.tcc_coordinogram import TCCCoordinogramDialog
        dlg = TCCCoordinogramDialog()
        dlg._on_c_lines_toggled(True)
        # Either widget had set_c_lines or fallback attribute is set
        c_lines_attr = getattr(dlg._coord_widget, "_c_lines", None)
        assert c_lines_attr is not None
        # Toggle off
        dlg._on_c_lines_toggled(False)


# ===========================================================================
# 7ª garantia — accessibility
# ===========================================================================


class TestSeventhGuaranteeAccessibility:

    def test_tcc_dialog_module_documented(self):
        with open(
            "D:/000 - UFMG - DOUTORADO/MVP/app/gui/tcc_coordinogram.py",
            encoding="utf-8",
        ) as f:
            content = f.read()
        assert "_on_c_lines_toggled" in content
        assert "_on_export_tcc_report" in content
        # Cita Tutorial inline
        assert "Tutorial" in content

    def test_c_lines_module_cites_nfpa(self):
        with open(
            "D:/000 - UFMG - DOUTORADO/MVP/app/postprocessor/tcc_c_lines.py",
            encoding="utf-8",
        ) as f:
            content = f.read()
        assert "NFPA 70E" in content
        assert "IEEE 1584" in content
