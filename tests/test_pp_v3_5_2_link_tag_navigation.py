"""v3.5.2 — A.1 (AddLinkTagDialog) + A.2 (multi-doc navigation) tests.

Closes SKIPPED_BACKLOG A.1 e A.2 (registrados v3.1.4, 5 releases sem
revisita após v3.5.1). Reference: PTW Tutorial §Part 1 p.30-42.

Tests cobrem:

* A.1.1 — ``AddLinkTagDialog`` constrói e expõe form_data
* A.1.2 — composição target ``scheme:name`` é correta
* A.1.3 — defaults sane (tcc:CoordA, visible=True, closed_arrow=True)
* A.1.4 — split de target existente preenche scheme combo
* A.2.1 — ``MainWindow.register_document`` adiciona ao registry
* A.2.2 — ``list_documents`` retorna registered names ordenados
* A.2.3 — ``navigate_to_document`` retorna False se não registrado
* A.2.4 — ``unregister_document`` remove do registry
"""

from __future__ import annotations

import os
import sys

import pytest

# Headless Qt — must be set BEFORE QApplication import
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="module")
def qapp():
    """Singleton QApplication for the module."""
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication(sys.argv)
    return app


# ---------------------------------------------------------------------------
# A.1 — AddLinkTagDialog
# ---------------------------------------------------------------------------


class TestAddLinkTagDialog:
    """v3.5.2 A.1 closure — unified Link Tag dialog."""

    def test_dialog_builds_with_defaults(self, qapp) -> None:
        from app.gui.add_link_tag_dialog import AddLinkTagDialog
        dlg = AddLinkTagDialog(parent=None)
        data = dlg.form_data()
        assert data.label == "Ver TCC-A"
        assert data.target == "tcc:CoordA"
        assert data.visible is True
        assert data.closed_arrow is True

    def test_dialog_compose_target_from_scheme_combo(self, qapp) -> None:
        from app.gui.add_link_tag_dialog import AddLinkTagDialog
        dlg = AddLinkTagDialog(
            parent=None,
            default_label="Goto",
            default_target="oneline:DocB",
        )
        data = dlg.form_data()
        assert data.target == "oneline:DocB"
        assert data.label == "Goto"

    def test_dialog_split_target_handles_no_colon(self, qapp) -> None:
        from app.gui.add_link_tag_dialog import AddLinkTagDialog
        # Target without scheme prefix → fallback to tcc:
        dlg = AddLinkTagDialog(
            parent=None,
            default_label="X",
            default_target="JustAName",
        )
        data = dlg.form_data()
        # Form composes scheme:name; default scheme = tcc
        assert data.target.startswith("tcc:")
        assert "JustAName" in data.target

    def test_dialog_visible_closed_arrow_toggles(self, qapp) -> None:
        from app.gui.add_link_tag_dialog import AddLinkTagDialog
        dlg = AddLinkTagDialog(
            parent=None,
            default_visible=False,
            default_closed_arrow=False,
        )
        data = dlg.form_data()
        assert data.visible is False
        assert data.closed_arrow is False

    def test_dialog_form_data_strips_whitespace(self, qapp) -> None:
        from app.gui.add_link_tag_dialog import AddLinkTagDialog
        dlg = AddLinkTagDialog(parent=None, default_label="  hello  ")
        data = dlg.form_data()
        assert data.label == "hello"

    def test_target_schemes_includes_all_four(self, qapp) -> None:
        from app.gui.add_link_tag_dialog import TARGET_SCHEMES
        scheme_ids = [s[0] for s in TARGET_SCHEMES]
        assert "oneline" in scheme_ids
        assert "tcc" in scheme_ids
        assert "report" in scheme_ids
        assert "pdf" in scheme_ids


# ---------------------------------------------------------------------------
# A.2 — Multi-document navigation registry
# ---------------------------------------------------------------------------


class TestDocumentRegistry:
    """v3.5.2 A.2 closure — MainWindow document registry."""

    def test_register_and_list(self, qapp) -> None:
        # Use a stub MainWindow-like object to test registry methods
        # in isolation (avoid heavy MainWindow construction).
        from PySide6.QtWidgets import QWidget
        from app.gui.main_window import MainWindow

        # We test the methods via duck-typing on a minimal stub that
        # mimics the registry attribute. This avoids full GUI startup.
        stub = type("Stub", (), {})()
        stub._documents_registry = {}
        stub.tabs = None  # No tabs in stub

        # Bind unbound methods
        MainWindow.register_document(stub, "DocA", QWidget())
        MainWindow.register_document(stub, "DocB", QWidget())
        names = MainWindow.list_documents(stub)
        assert names == ["DocA", "DocB"]

    def test_navigate_returns_false_for_unknown(self, qapp) -> None:
        from app.gui.main_window import MainWindow
        stub = type("Stub", (), {})()
        stub._documents_registry = {}
        stub.tabs = None
        ok = MainWindow.navigate_to_document(stub, "NotRegistered")
        assert ok is False

    def test_navigate_returns_true_for_registered(self, qapp) -> None:
        from PySide6.QtWidgets import QWidget
        from app.gui.main_window import MainWindow
        stub = type("Stub", (), {})()
        stub._documents_registry = {}
        stub.tabs = None
        widget = QWidget()
        MainWindow.register_document(stub, "DocX", widget)
        ok = MainWindow.navigate_to_document(stub, "DocX")
        assert ok is True

    def test_unregister_removes(self, qapp) -> None:
        from PySide6.QtWidgets import QWidget
        from app.gui.main_window import MainWindow
        stub = type("Stub", (), {})()
        stub._documents_registry = {}
        stub.tabs = None
        MainWindow.register_document(stub, "Tmp", QWidget())
        assert "Tmp" in MainWindow.list_documents(stub)
        MainWindow.unregister_document(stub, "Tmp")
        assert "Tmp" not in MainWindow.list_documents(stub)

    def test_unregister_unknown_is_noop(self, qapp) -> None:
        from app.gui.main_window import MainWindow
        stub = type("Stub", (), {})()
        stub._documents_registry = {}
        # Should not raise
        MainWindow.unregister_document(stub, "DoesNotExist")
        assert MainWindow.list_documents(stub) == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
