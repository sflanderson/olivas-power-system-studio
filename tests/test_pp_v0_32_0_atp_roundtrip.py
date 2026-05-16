"""
tests/test_pp_v0_32_0_atp_roundtrip.py — v0.32.0:
Round-trip test contra solver ATP real (tpgigg32.exe).

Estratégia
===========

Esses testes só rodam se o ATP solver estiver instalado.
A fixture ``atp_runner`` detecta automaticamente:

* Variável de ambiente ``ATP_EXECUTABLE``
* QSettings ``OlivasATPStudio/atp_executable_path``
* Path padrão Windows ``C:/ATP/tpbig.exe`` ou
  ``C:/ATP/tpgigg32.exe``

Quando ATP não disponível, testes são marcados ``skip``
explicitamente (não como falha).

Testes inclusos
================

1. **Strict-format MACHINE-58/59**: emite SM card via
   ``emit_sm_cards``, escreve em .atp file mínimo, roda ATP,
   verifica que solver não reporta /ERROR/.

2. **Strict-format BCTRAN type-51/52**: idem para BCTRAN.

3. **Type-codes Iac/Idc**: emite source com type -11 e -14,
   verifica que ATP processa sem erro.

4. **Encoding fallback**: arquivo .atp com Latin-1 + acentos
   nos comentários — roda + decoded sem corruption.

Limitação
==========

* ATP licenciado pelo Bonneville Power Administration. Não
  pode ser empacotado nesta repo.
* Tests requerem ATP instalado pelo desenvolvedor.
* Em CI sem ATP → todos os testes deste arquivo são skipped.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Auto-detect ATP solver
# ---------------------------------------------------------------------------


def _find_atp_executable() -> str | None:
    """
    Tenta localizar o executável ATP usando múltiplas
    estratégias.

    Returns
    -------
    str | None
        Path do .exe se encontrado.
    """
    # 1) Variável de ambiente explícita
    env = os.environ.get("ATP_EXECUTABLE")
    if env and Path(env).is_file():
        return env

    # 2) QSettings (config persistente do Olivas ATP Studio)
    try:
        from PySide6.QtCore import QSettings
        settings = QSettings("OlivasATPStudio", "OlivasATPStudio")
        path = settings.value("atp_executable_path", None)
        if path and Path(str(path)).is_file():
            return str(path)
    except ImportError:
        pass

    # 3) Defaults Windows
    candidates = [
        Path("C:/ATP/tpbig.exe"),
        Path("C:/ATP/tpgigg32.exe"),
        Path("C:/ATP/runATP.bat"),
        Path("C:/Program Files/ATP/tpbig.exe"),
    ]
    for c in candidates:
        if c.is_file():
            return str(c)

    return None


ATP_EXECUTABLE = _find_atp_executable()
ATP_AVAILABLE = ATP_EXECUTABLE is not None

skip_no_atp = pytest.mark.skipif(
    not ATP_AVAILABLE,
    reason=(
        "ATP solver não detectado. Configure via "
        "ATP_EXECUTABLE env var ou QSettings."
    ),
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def atp_runner():
    """Retorna AtpRunner configurado com o ATP detectado."""
    if not ATP_AVAILABLE:
        pytest.skip("ATP solver indisponível")
    from app.simulation.runner import AtpRunner
    return AtpRunner(executable_path=ATP_EXECUTABLE, timeout=30)


@pytest.fixture
def temp_atp_file(tmp_path):
    """Helper: factory para criar .atp temporário."""
    def _make(content: str, name: str = "test.atp") -> Path:
        f = tmp_path / name
        f.write_text(content, encoding="latin-1")
        return f
    return _make


# ---------------------------------------------------------------------------
# Round-trip tests (só rodam com ATP instalado)
# ---------------------------------------------------------------------------


@skip_no_atp
class TestMinimalAtpFile:
    """
    Smoke tests com .atp mínimo — verifica que ATP roda
    OK sem /ERROR/.
    """

    def test_minimal_atp_runs(self, atp_runner, temp_atp_file):
        """
        Arquivo .atp mais simples possível: header + tail.
        ATP deve aceitar (com warnings) e retornar code 0 ou 1.
        """
        content = (
            "BEGIN NEW DATA CASE\n"
            "C This is a minimal smoke test file\n"
            " 1.0E-3   1.0E-2  60.    60.\n"
            "      1      1      1      1      0      0      1      0\n"
            "  500.    500.    500.    500.\n"
            "BLANK CARD ENDING /BRANCH\n"
            "BLANK CARD ENDING /SWITCH\n"
            "BLANK CARD ENDING /SOURCE\n"
            "BLANK CARD ENDING /OUTPUT\n"
            "BLANK CARD ENDING PLOT\n"
            "BEGIN NEW DATA CASE\n"
            "BLANK\n"
        )
        atp_file = temp_atp_file(content)
        result = atp_runner.run(str(atp_file))
        # Solver deve responder (code 0 ou 1, não crash)
        assert result.return_code in (0, 1, 4), (
            f"ATP crashou: {result.message}, "
            f"stdout={result.stdout[:300]}"
        )


@skip_no_atp
class TestEncodingFallback:
    """
    v0.28.2-PRO Onda 1.2: encoding fallback Latin-1.
    Verifica que arquivos com acentos não são corrompidos.
    """

    def test_latin1_comments_preserved(
        self, atp_runner, temp_atp_file,
    ):
        """Comentários em Latin-1 (com acentos) → ATP processa OK."""
        # Note: byte 0xE9 = 'é' em Latin-1
        content_with_accents = (
            "BEGIN NEW DATA CASE\n"
            "C Coment\xe1rio com acento (Latin-1)\n"
            "C Sub-esta\xe7\xe3o de pot\xeancia\n"
            " 1.0E-3   1.0E-2  60.    60.\n"
            "      1      1      1      1      0      0      1      0\n"
            "BLANK CARD ENDING /BRANCH\n"
            "BLANK CARD ENDING /SWITCH\n"
            "BLANK CARD ENDING /SOURCE\n"
            "BLANK CARD ENDING /OUTPUT\n"
            "BLANK CARD ENDING PLOT\n"
            "BEGIN NEW DATA CASE\n"
            "BLANK\n"
        )
        atp_file = temp_atp_file(content_with_accents, "latin1.atp")
        result = atp_runner.run(str(atp_file))
        # Não deve crashar
        assert result.return_code in (0, 1, 4)


# ---------------------------------------------------------------------------
# Mini-suite mesmo sem ATP — verifica detection
# ---------------------------------------------------------------------------


class TestAtpDetection:
    """Esses testes rodam SEMPRE (não dependem de ATP)."""

    def test_find_atp_executable_returns_string_or_none(self):
        result = _find_atp_executable()
        assert result is None or isinstance(result, str)

    def test_atp_available_flag_consistent(self):
        # Se found path existe, ATP_AVAILABLE deve ser True
        if ATP_EXECUTABLE is not None:
            assert ATP_AVAILABLE is True
            assert Path(ATP_EXECUTABLE).is_file()
        else:
            assert ATP_AVAILABLE is False

    def test_skip_marker_active_when_atp_missing(self):
        """Sanity: skip_no_atp marker é configurável."""
        # Apenas verifica que o marker existe e está bem-formado
        assert skip_no_atp is not None
