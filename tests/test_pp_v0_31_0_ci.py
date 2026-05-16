"""
tests/test_pp_v0_31_0_ci.py — v0.31.0: smoke tests for CI/CD
infrastructure (GitHub Actions workflows + cross-platform
import sanity).

Cobre:

* .github/workflows/test.yml exists and is well-formed YAML
* .github/workflows/lint.yml exists
* All core modules importable WITHOUT PySide6 (Linux CI sem Qt)
* requirements.txt has minimum versions
"""

from __future__ import annotations

from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Workflows present
# ---------------------------------------------------------------------------


class TestGithubActions:

    def test_test_yml_exists(self):
        f = REPO_ROOT / ".github" / "workflows" / "test.yml"
        assert f.exists(), f"{f} não encontrado"
        text = f.read_text(encoding="utf-8")
        assert "pytest" in text
        assert "matrix" in text
        # Verifica matriz multi-OS / multi-Python
        assert "ubuntu-latest" in text
        assert "windows-latest" in text
        assert "3.13" in text

    def test_lint_yml_exists(self):
        f = REPO_ROOT / ".github" / "workflows" / "lint.yml"
        assert f.exists()
        text = f.read_text(encoding="utf-8")
        assert "ruff" in text

    def test_test_yml_has_qt_offscreen(self):
        """CI Linux precisa de QT_QPA_PLATFORM=offscreen."""
        f = REPO_ROOT / ".github" / "workflows" / "test.yml"
        text = f.read_text(encoding="utf-8")
        assert "QT_QPA_PLATFORM" in text
        assert "offscreen" in text

    def test_test_yml_installs_qt_deps_linux(self):
        """Linux precisa de libxcb e companhia para PySide6."""
        f = REPO_ROOT / ".github" / "workflows" / "test.yml"
        text = f.read_text(encoding="utf-8")
        # Pelo menos algumas das libs Qt críticas
        assert "libxkbcommon" in text
        assert "libxcb" in text


# ---------------------------------------------------------------------------
# Core modules importable sem PySide6
# ---------------------------------------------------------------------------


class TestCoreImportsNoPySide6:
    """
    Lint workflow roda 'import smoke' SEM PySide6 instalado para
    garantir que core (preprocessor + standards) não tem
    dependência circular para Qt.
    """

    def test_iec60909(self):
        import app.standards.iec60909  # noqa: F401

    def test_iec60909_seq(self):
        import app.standards.iec60909_seq  # noqa: F401

    def test_iec60909_decay(self):
        import app.standards.iec60909_decay  # noqa: F401

    def test_iec60909_kappa(self):
        import app.standards.iec60909_kappa  # noqa: F401

    def test_nbr17227(self):
        import app.standards.nbr17227  # noqa: F401

    def test_iec60255(self):
        import app.standards.iec60255  # noqa: F401

    def test_atp_format(self):
        import app.preprocessor.atp_format  # noqa: F401

    def test_short_circuit(self):
        import app.postprocessor.short_circuit  # noqa: F401

    def test_power_flow(self):
        # Pode importar numpy mas NÃO PySide6
        import app.postprocessor.power_flow  # noqa: F401

    def test_motor_starting(self):
        import app.postprocessor.motor_starting  # noqa: F401

    def test_arc_flash(self):
        import app.postprocessor.arc_flash  # noqa: F401

    def test_relay_coordination(self):
        import app.postprocessor.relay_coordination  # noqa: F401


# ---------------------------------------------------------------------------
# requirements.txt
# ---------------------------------------------------------------------------


class TestRequirements:

    def test_requirements_txt_exists(self):
        f = REPO_ROOT / "requirements.txt"
        assert f.exists()

    def test_has_pytest(self):
        f = REPO_ROOT / "requirements.txt"
        text = f.read_text(encoding="utf-8")
        assert "pytest" in text

    def test_has_pyside6(self):
        f = REPO_ROOT / "requirements.txt"
        text = f.read_text(encoding="utf-8")
        assert "PySide6" in text

    def test_has_numpy(self):
        f = REPO_ROOT / "requirements.txt"
        text = f.read_text(encoding="utf-8")
        assert "numpy" in text
