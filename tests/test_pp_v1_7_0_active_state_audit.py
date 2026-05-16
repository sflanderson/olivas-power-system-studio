"""
tests/test_pp_v1_7_0_active_state_audit.py — v1.7.0 Sprint D.

**Audit-only**: documenta o estado atual de cobertura "active/inactive"
nos 56 component specs.

**Não modifica specs** nesta release (anti-funcionalidade acidental).
Apenas reporta gap para planejar v1.7.1+ com mudança travada.

Categorização
==============

* **Switching components** (BREAKER, FUSE, SWITCH, CONTACTOR):
  precisam de property explícita ``state`` (open/closed) — afeta
  energization (Sprint B). ⚠ CRÍTICO.

* **Active components** (geradores, motores, fontes):
  precisam de ``out_of_service`` (PTW pattern) — afeta load flow
  e reliability. ⚠ MÉDIO.

* **Passive** (BUS, CABLE, R, L, C, TR):
  ``out_of_service`` opcional mas útil para "what-if" analysis.
  ⚠ BAIXO.
"""

from __future__ import annotations

from pathlib import Path

import pytest


SPECS_DIR = Path(
    "D:/000 - UFMG - DOUTORADO/MVP/app/preprocessor/catalog_specs"
)


# Componentes onde state explícito é REQUIRED (afeta energization)
_CRITICAL_SWITCHING_COMPONENTS = {
    "BREAKER", "FUSE", "CONTACTOR", "SWITCH",
    "VCB", "VCB3", "DISC", "DISCONNECTOR",
}


def _list_specs():
    """Lista todos os arquivos .ocomp."""
    if not SPECS_DIR.is_dir():
        return []
    return sorted(SPECS_DIR.glob("*.ocomp"))


def _has_state_property(yaml_text: str) -> bool:
    """Heurística: spec tem property 'state' ou 'open' ou 'out_of_service'."""
    text = yaml_text.lower()
    return any(
        f"name: {kw}" in text
        for kw in (
            "state", "status", "open", "out_of_service",
            "is_active", "is_open",
        )
    )


class TestActiveStateAudit:

    def test_specs_dir_exists(self):
        assert SPECS_DIR.is_dir(), (
            f"Catalog specs dir não encontrado: {SPECS_DIR}"
        )

    def test_count_specs(self):
        specs = _list_specs()
        assert len(specs) >= 50, (
            f"Esperava >=50 component specs, achei {len(specs)}"
        )

    def test_audit_critical_switching_components(self):
        """
        Audit-only: lista quais switching components TÊM ou NÃO TÊM
        property de estado. Não falha se nenhum tiver — apenas
        reporta para o handoff doc.
        """
        specs = _list_specs()
        with_state = []
        without_state = []
        for s in specs:
            code = s.stem.upper()
            if code not in _CRITICAL_SWITCHING_COMPONENTS:
                continue
            text = s.read_text(encoding="utf-8")
            if _has_state_property(text):
                with_state.append(code)
            else:
                without_state.append(code)

        # Reporta no test name (visible em pytest output)
        report = (
            f"Critical switching with state: {with_state}\n"
            f"Critical switching WITHOUT state: {without_state}"
        )
        # Em v1.7.0: apenas documentamos. Em v1.7.1+ poderá ser
        # `assert not without_state` para enforcement.
        assert isinstance(without_state, list)   # passa sempre
        # Print no log para handoff
        print(f"\n[v1.7.0 audit] {report}")

    def test_audit_total_coverage(self):
        """Reporta overall % de specs com state property."""
        specs = _list_specs()
        with_state = sum(
            1 for s in specs
            if _has_state_property(s.read_text(encoding="utf-8"))
        )
        coverage = with_state / max(len(specs), 1) * 100.0
        print(
            f"\n[v1.7.0 audit] Coverage state property: "
            f"{with_state}/{len(specs)} ({coverage:.1f}%)"
        )
        # Audit-only: aceita qualquer coverage (registro)
        assert with_state >= 0
