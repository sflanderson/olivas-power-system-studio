"""
tests/test_pp_v0_34_distribution.py — v0.34: validação da
infraestrutura de build PyInstaller.
"""

from __future__ import annotations

from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent


class TestBuildArtifacts:

    def test_spec_exists(self):
        spec = REPO_ROOT / "build" / "olivas_atp_studio.spec"
        assert spec.is_file(), f"{spec} não encontrado"

    def test_build_script_exists(self):
        script = REPO_ROOT / "build" / "build_distribution.py"
        assert script.is_file()

    def test_readme_exists(self):
        f = REPO_ROOT / "build" / "README.md"
        assert f.is_file()


class TestSpecContent:

    def test_spec_includes_app_main(self):
        spec = REPO_ROOT / "build" / "olivas_atp_studio.spec"
        text = spec.read_text(encoding="utf-8")
        assert "main.py" in text

    def test_spec_includes_pyside6_hidden_imports(self):
        spec = REPO_ROOT / "build" / "olivas_atp_studio.spec"
        text = spec.read_text(encoding="utf-8")
        assert "PySide6.QtCore" in text
        assert "PySide6.QtWidgets" in text

    def test_spec_includes_examples(self):
        """Exemplos lazy-imported via registry — devem ser
        explicitamente declarados em hiddenimports."""
        spec = REPO_ROOT / "build" / "olivas_atp_studio.spec"
        text = spec.read_text(encoding="utf-8")
        assert "stevenson_pf_3bus" in text
        assert "iec60909_annex_c" in text
        assert "ieee1584_ex_d2" in text
        assert "nbr17227_example" in text

    def test_spec_excludes_unused_qt_modules(self):
        spec = REPO_ROOT / "build" / "olivas_atp_studio.spec"
        text = spec.read_text(encoding="utf-8")
        assert "QtWebEngine" in text   # excluído
        assert "tkinter" in text       # excluído

    def test_spec_no_upx(self):
        """UPX desativado para evitar AV false-positive."""
        spec = REPO_ROOT / "build" / "olivas_atp_studio.spec"
        text = spec.read_text(encoding="utf-8")
        assert "upx=False" in text


class TestBuildScript:

    def test_script_has_main(self):
        script = REPO_ROOT / "build" / "build_distribution.py"
        text = script.read_text(encoding="utf-8")
        assert "def main()" in text

    def test_script_has_clean_flag(self):
        script = REPO_ROOT / "build" / "build_distribution.py"
        text = script.read_text(encoding="utf-8")
        assert "--clean" in text
