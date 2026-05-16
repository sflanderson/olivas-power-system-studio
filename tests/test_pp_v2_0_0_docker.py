"""
tests/test_pp_v2_0_0_docker.py — v2.0.0 Sprint C.

Audit-only: verifica Dockerfile + docker-compose.yml existem
e têm estrutura mínima.

Não roda Docker (requer daemon), apenas valida arquivos.
"""

from __future__ import annotations

from pathlib import Path

import pytest


PROJECT_ROOT = Path("D:/000 - UFMG - DOUTORADO/MVP")
DOCKERFILE = PROJECT_ROOT / "Dockerfile"
COMPOSE = PROJECT_ROOT / "docker-compose.yml"


class TestDockerfileExists:

    def test_dockerfile_present(self):
        assert DOCKERFILE.is_file(), (
            f"Dockerfile esperado em {DOCKERFILE}"
        )

    def test_dockerfile_has_python_311(self):
        text = DOCKERFILE.read_text(encoding="utf-8")
        assert "python:3.11" in text or "python:3.12" in text

    def test_dockerfile_copies_app(self):
        text = DOCKERFILE.read_text(encoding="utf-8")
        assert "COPY app" in text
        assert "COPY requirements.txt" in text

    def test_dockerfile_has_healthcheck(self):
        text = DOCKERFILE.read_text(encoding="utf-8")
        assert "HEALTHCHECK" in text

    def test_dockerfile_uses_offscreen_qt(self):
        """Anti-perda: container roda em modo headless (sem GUI)."""
        text = DOCKERFILE.read_text(encoding="utf-8")
        assert "offscreen" in text.lower()


class TestDockerCompose:

    def test_compose_present(self):
        assert COMPOSE.is_file()

    def test_compose_has_olivas_service(self):
        text = COMPOSE.read_text(encoding="utf-8")
        assert "olivas:" in text

    def test_compose_uses_v2_image(self):
        text = COMPOSE.read_text(encoding="utf-8")
        assert "olivas:2.0.0" in text or "olivas:2" in text
