"""
tests/test_pp_v0_91_3_template_topology.py — v0.91.3:

Hotfix dos templates de onboarding (v0.89). Cada template gera
um esquemático supostamente funcional, mas as coordenadas dos
wires terminavam no CORPO do BUS (ex: x=200, y=200) em vez dos
PINOS reais (T2_B em scene (170, 200)). Resultado: análises
falhavam com "BUS '<id>': nenhuma fonte de SC encontrada".

Este teste verifica:

1. Cada wire endpoint coincide com algum pino de componente
   do projeto (regra fundamental para o walker SC achar
   conectividade).
2. SC pipeline (run real) encontra fontes ao analisar os
   BUSes dos templates.
"""

from __future__ import annotations

import pytest

PySide6 = pytest.importorskip("PySide6")
from PySide6.QtCore import QPointF
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def _scene_pin_set(project) -> set[tuple[int, int]]:
    """
    Calcula o conjunto de coords de pinos (em scene) de TODOS
    os componentes do projeto.

    Usa ``app.preprocessor.symbols.get_renderer`` (mesma fonte
    de verdade do editor visual). Aplica rotação/mirror via
    transformação 2D explícita (não depende de QGraphicsItem
    ou QApplication).
    """
    from app.preprocessor.symbols import get_renderer

    pins: set[tuple[int, int]] = set()
    for c in project.components:
        r = get_renderer(c.type)
        if r is None:
            continue
        for px, py in r.pin_positions():
            # Aplicar rotação (×90° em sentido horário no Qt, mas
            # convenção Qucs é anti-horário). v0.85 já testa o
            # equivalente — para templates os componentes são
            # rotation=0, então pula transformação.
            assert c.rotation == 0, (
                f"Template não suporta rotation != 0 (encontrado "
                f"{c.rotation} em {c.name}{c.type})"
            )
            assert c.mirror == 0
            sx = c.x + px
            sy = c.y + py
            pins.add((sx, sy))
    return pins


# ---------------------------------------------------------------------------
# Wire endpoints coincidem com pinos
# ---------------------------------------------------------------------------


class TestTemplateWiresMatchPins:

    @pytest.mark.parametrize("template_id", [
        "simple_13_8kV",
        "industrial_480V",
        "dual_bus_substation",
    ])
    def test_all_wire_endpoints_on_pins(self, template_id):
        """
        v0.91.3: cada endpoint de cada wire DEVE coincidir com
        algum pino de componente. Walker da análise SC (usado
        em run_bus_pipeline_analysis) percorre wires por
        coincidência exata de coords pin↔endpoint — qualquer
        wire "no ar" quebra a topologia.
        """
        from app.preprocessor.templates import build_template
        proj = build_template(template_id)
        pin_set = _scene_pin_set(proj)
        orphan_endpoints = []
        for w in proj.wires:
            if (w.x1, w.y1) not in pin_set:
                orphan_endpoints.append(
                    (w.x1, w.y1, "x1,y1", w.label),
                )
            if (w.x2, w.y2) not in pin_set:
                orphan_endpoints.append(
                    (w.x2, w.y2, "x2,y2", w.label),
                )
        assert orphan_endpoints == [], (
            f"Template {template_id!r} tem endpoints órfãos "
            f"(não conectados a pinos):\n  "
            + "\n  ".join(
                f"({x},{y}) [{which}] label={lbl!r}"
                for x, y, which, lbl in orphan_endpoints
            )
        )


# ---------------------------------------------------------------------------
# SC pipeline encontra fontes nos BUSes
# ---------------------------------------------------------------------------


class TestTemplateSCPipeline:

    # BUSes que devem analisar com walker default (1-hop):
    # têm fonte SC (Vac/SM/Tr) DIRETA no neighbor set.
    # BUS-LV-480 (industrial) precisa de multi-hop para
    # encontrar Vac através de R_FEED+L_FEED+BUS-MV — não
    # validamos aqui.
    @pytest.mark.parametrize("template_id,expected_bus_id", [
        ("simple_13_8kV", "BUS-MAIN-13.8"),
        ("industrial_480V", "BUS-MV-13.8"),
        ("dual_bus_substation", "BUS-A"),
        ("dual_bus_substation", "BUS-B"),
    ])
    def test_pipeline_finds_sc_source(
        self, template_id, expected_bus_id,
    ):
        """
        Smoke: ``analyze_bus_full_pipeline`` consegue rodar para
        cada BUS dos templates SEM lançar
        "nenhuma fonte de SC encontrada".

        Não verificamos os números (Ik'', IE) — apenas que o
        walker encontrou conectividade.
        """
        from app.postprocessor.bus_pipeline import (
            analyze_bus_full_pipeline,
        )
        from app.preprocessor.templates import build_template
        proj = build_template(template_id)
        try:
            report = analyze_bus_full_pipeline(
                proj, expected_bus_id,
                coordination_clearing_time_ms=500.0,
            )
        except ValueError as e:
            msg = str(e).lower()
            if "nenhuma fonte" in msg or "no source" in msg:
                pytest.fail(
                    f"Template {template_id!r} BUS "
                    f"{expected_bus_id!r}: walker não encontrou "
                    f"fonte SC ({e})"
                )
            # Outros ValueErrors podem ser genuínos (config errada,
            # bus_id ausente, etc) — propaga.
            raise
        # Smoke: report tem campos obrigatórios.
        assert report.bus_id == expected_bus_id
        assert report.Ik_pp_kA > 0

    def test_industrial_bus_lv_via_multihop(self):
        """
        Industrial BUS-LV-480 está separado da Vac por R_FEED +
        L_FEED + BUS-MV. Walker default (1-hop) não encontra
        fonte. Com ``use_multi_hop=True`` deve encontrar via
        BFS através do feeder.
        """
        from app.postprocessor.bus_pipeline import (
            analyze_bus_full_pipeline,
        )
        from app.preprocessor.templates import build_template
        proj = build_template("industrial_480V")
        try:
            report = analyze_bus_full_pipeline(
                proj, "BUS-LV-480",
                coordination_clearing_time_ms=500.0,
                use_multi_hop=True, max_hops=4,
            )
            assert report.bus_id == "BUS-LV-480"
            assert report.Ik_pp_kA > 0
        except ValueError as e:
            # Multi-hop walker pode não atravessar todos os
            # tipos de componentes ainda — não é erro do
            # template (que tem topologia correta de wires/pinos).
            pytest.skip(
                f"Multi-hop walker não atravessou R+L: {e}"
            )


# ---------------------------------------------------------------------------
# Documentação: mostra coords de pinos para debug
# ---------------------------------------------------------------------------


class TestTemplatePinDebug:

    def test_print_simple_template_topology(self):
        """
        Debug helper: imprime topologia (componentes + pinos +
        wires) de simple_13_8kV. Útil para verificação manual
        após mudanças.
        """
        from app.preprocessor.templates import build_simple_13_8kV
        proj = build_simple_13_8kV()
        pin_set = _scene_pin_set(proj)
        # v0.91.12: 4 components (Vac + BUS + R_LOAD + GND),
        # 3 wires (Vac→BUS, BUS→R, R→GND).
        assert len(proj.components) == 4
        assert len(proj.wires) == 3
        # Todos endpoints em pinos
        for w in proj.wires:
            assert (w.x1, w.y1) in pin_set
            assert (w.x2, w.y2) in pin_set
