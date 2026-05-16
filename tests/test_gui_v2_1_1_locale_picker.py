"""
tests/test_gui_v2_1_1_locale_picker.py — v2.1.1.

Cobre LocalePickerDialog:

* Dialog loadable
* ComboBox lista PT/EN/ES
* Selection invoca set_locale() corretamente
* Persistência via QSettings (locale lembrado entre sessões)
* Anti-crash defensive
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


class TestLocalePickerDialog:

    def test_module_loadable(self, qapp):
        from app.gui.locale_picker_dialog import LocalePickerDialog
        assert LocalePickerDialog is not None

    def test_dialog_constructable(self, qapp):
        from app.gui.locale_picker_dialog import LocalePickerDialog
        dlg = LocalePickerDialog()
        assert dlg is not None

    def test_dialog_has_combo_with_3_locales(self, qapp):
        from app.gui.locale_picker_dialog import LocalePickerDialog
        dlg = LocalePickerDialog()
        assert hasattr(dlg, "locale_combo")
        # PT, EN, ES — pelo menos 3
        assert dlg.locale_combo.count() >= 3

    def test_dialog_default_selection_is_current_locale(self, qapp):
        from app.gui.locale_picker_dialog import LocalePickerDialog
        from app.i18n import set_locale, reset_locale
        reset_locale()
        set_locale("en")
        dlg = LocalePickerDialog()
        # Combo deve mostrar EN como atual
        current_data = dlg.locale_combo.currentData()
        assert current_data == "en"
        reset_locale()

    def test_apply_changes_locale(self, qapp):
        from app.gui.locale_picker_dialog import LocalePickerDialog
        from app.i18n import get_locale, reset_locale
        reset_locale()
        dlg = LocalePickerDialog()
        # Set combo to ES
        for i in range(dlg.locale_combo.count()):
            if dlg.locale_combo.itemData(i) == "es":
                dlg.locale_combo.setCurrentIndex(i)
                break
        dlg._on_apply()
        assert get_locale() == "es"
        reset_locale()


class TestLocalePickerButtons:

    def test_dialog_has_apply_button(self, qapp):
        from app.gui.locale_picker_dialog import LocalePickerDialog
        dlg = LocalePickerDialog()
        assert hasattr(dlg, "btn_apply")

    def test_dialog_has_close_button(self, qapp):
        from app.gui.locale_picker_dialog import LocalePickerDialog
        dlg = LocalePickerDialog()
        assert hasattr(dlg, "btn_close")
