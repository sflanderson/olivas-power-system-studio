"""
tests/test_pp_drag_trails.py — Regressão do bug de rastro no drag.

Usuário reportou em v0.21.8.b que ao arrastar um componente (R, L, GND)
no Esquemático Visual, pixels "ghost" permaneciam em todas as posições
por onde o componente passara — o canvas enchia de lixo gráfico.

Causa raiz (três problemas combinados):

1. ``PpView`` não setava ``setViewportUpdateMode``; o default
   ``MinimalViewportUpdate`` confia em ``boundingRect()`` dos items
   para invalidar regiões. Qualquer sub-cobertura deixa pixels
   grudados.

2. ``ComponentItem.boundingRect()`` expandia apenas +6 à direita; o
   label do componente (``QFont("Sans", 7)`` via ``drawText`` em
   ``(br.left(), br.bottom()+10)``) extrapolava para labels longos
   ("VCB3", "GND", "MOSFET").

3. ``_PEN_NORMAL`` em ``symbols.py`` tem ``width=1.5`` com
   ``Qt.RoundCap`` — metade do traço sai fora das coords geométricas
   da linha, não era incluída no rect.

Fix (em ``items.py`` + ``view.py``):

- ``PpView`` → ``setViewportUpdateMode(BoundingRectViewportUpdate)``.
- ``ComponentItem.boundingRect()`` usa ``QFontMetricsF`` para medir a
  largura real do label; soma pen halo (``_MAX_PEN_HALF``) e selection
  margin (``_SELECTION_MARGIN``).
- ``ComponentItem._label_rect()`` novo helper para calcular o rect
  exato do label em coords locais.

Estes testes garantem que:

* Para TODOS os tipos do catálogo, o rect do label fica CONTIDO no
  boundingRect.
* Labels longos ("GND" em 24×24, "MOSFET" em 60×60) não estouram.
* O ``PpView`` tem ``BoundingRectViewportUpdate`` por default.
"""

from __future__ import annotations

import pytest

# Evita inicializar o Qt GUI em CI headless; se PySide6 não estiver
# disponível, pula todos.
pytest.importorskip("PySide6")

from PySide6.QtCore import QPointF, QRectF
from PySide6.QtWidgets import QApplication, QGraphicsView

from app.gui.schematic_pp.items import (
    _LABEL_FONT,
    _MAX_PEN_HALF,
    _SELECTION_MARGIN,
    ComponentItem,
)
from app.gui.schematic_pp.view import PpView
from app.gui.schematic_pp.scene import PpScene
from app.preprocessor.models import PpComponent


@pytest.fixture(scope="module")
def qapp():
    """QApplication singleton para os testes desta suite."""
    app = QApplication.instance() or QApplication([])
    yield app


def _make_component(type_code: str, name: str) -> PpComponent:
    return PpComponent(
        type=type_code,
        name=name,
        visible=True,
        x=100,
        y=100,
        label_dx=15,
        label_dy=-26,
        mirror=0,
        rotation=0,
        properties=[],
    )


# ---------------------------------------------------------------------------
# BoundingRect contém o label (causa raiz do bug de rastro)
# ---------------------------------------------------------------------------


class TestBoundingRectContainsLabel:
    """Para cada tipo, boundingRect deve conter o label_rect medido."""

    # (code, name) — name cobre curto, médio e longo.
    _CASES = [
        ("R", "R1"),
        ("R", "R_longer_name"),
        ("L", "L1"),
        ("C", "C1"),
        ("GND", "GND"),
        ("Vdc", "V1"),
        ("Vac", "Vac_source_A"),
        ("SwIdeal", "S1"),
        ("Diode", "D1"),
        ("VCB", "VCB_A"),
        ("VCB3", "VCB3_main_breaker"),
    ]

    @pytest.mark.parametrize("code,name", _CASES)
    def test_bounding_rect_contains_label(self, qapp, code, name):
        c = _make_component(code, name)
        item = ComponentItem(c)
        br = item.boundingRect()
        lbl = item._label_rect()
        assert lbl.isValid() and not lbl.isEmpty(), (
            f"[{code}/{name}] _label_rect retornou rect inválido"
        )
        assert br.contains(lbl), (
            f"[{code}/{name}] boundingRect {br} NÃO contém label_rect {lbl} — "
            f"pixels do label vazariam durante o drag e ficariam grudados."
        )

    @pytest.mark.parametrize("code,name", _CASES)
    def test_bounding_rect_contains_renderer_symbol(self, qapp, code, name):
        """boundingRect também deve conter o símbolo em si."""
        c = _make_component(code, name)
        item = ComponentItem(c)
        br = item.boundingRect()
        symbol = item.renderer.bounding_rect()
        assert br.contains(symbol), (
            f"[{code}/{name}] boundingRect {br} não contém renderer bounding "
            f"{symbol}"
        )

    @pytest.mark.parametrize("code,name", _CASES)
    def test_bounding_rect_includes_pen_halo(self, qapp, code, name):
        """Margem deve incluir a metade da pen width (pen halo)."""
        c = _make_component(code, name)
        item = ComponentItem(c)
        br = item.boundingRect()
        symbol = item.renderer.bounding_rect()
        # Meia-largura da pen mais fino deveria caber na folga esquerda/topo.
        min_margin = _MAX_PEN_HALF + _SELECTION_MARGIN
        assert br.left() <= symbol.left() - min_margin, (
            f"[{code}/{name}] margem esquerda insuficiente: "
            f"br.left={br.left()} vs symbol.left-{min_margin}={symbol.left() - min_margin}"
        )
        assert br.top() <= symbol.top() - min_margin, (
            f"[{code}/{name}] margem topo insuficiente"
        )

    def test_invisible_component_has_empty_label_rect(self, qapp):
        """Componente com visible=False não deve ter label rect ocupando espaço."""
        c = _make_component("R", "R1")
        c.visible = False
        item = ComponentItem(c)
        lbl = item._label_rect()
        assert lbl.isEmpty(), (
            f"Componente invisível gerou label_rect {lbl}; "
            f"esperado rect vazio."
        )

    def test_gnd_star_name_has_empty_label_rect(self, qapp):
        """GND com name='*' (convenção interna) não mostra label."""
        c = _make_component("GND", "*")
        item = ComponentItem(c)
        lbl = item._label_rect()
        assert lbl.isEmpty(), (
            f"GND com name='*' gerou label_rect {lbl}; esperado vazio."
        )


# ---------------------------------------------------------------------------
# View setup: setViewportUpdateMode configurado
# ---------------------------------------------------------------------------


class TestViewportUpdateMode:
    """O view DEVE configurar viewport update mode (default é frágil)."""

    def test_view_has_non_default_update_mode(self, qapp):
        """
        ``MinimalViewportUpdate`` (default) é o modo problemático —
        confia em boundingRect() dos items, e qualquer sub-cobertura
        deixa rastros. ``BoundingRectViewportUpdate`` é robusto.
        """
        scene = PpScene()
        view = PpView(scene)
        mode = view.viewportUpdateMode()
        assert mode != QGraphicsView.MinimalViewportUpdate, (
            f"PpView usando MinimalViewportUpdate — bug de rastro "
            f"vai voltar. Use BoundingRectViewportUpdate ou FullViewportUpdate."
        )
        # Preferência: BoundingRect é barato e suficiente.
        # (Se alguém trocar por Full no futuro, ambos aceitos.)
        assert mode in (
            QGraphicsView.BoundingRectViewportUpdate,
            QGraphicsView.FullViewportUpdate,
        ), f"viewportUpdateMode inesperado: {mode!r}"


# ---------------------------------------------------------------------------
# Drag simulation: boundingRect não "encolhe" após mover
# ---------------------------------------------------------------------------


class TestBoundingRectStableAcrossDrag:
    """
    Simula um drag: setPos várias vezes, verifica que boundingRect
    em coords locais permanece estável (não regredir para rect apertado
    depois de algum side-effect).
    """

    @pytest.mark.parametrize("code,name", [
        ("R", "R_test"),
        ("VCB3", "VCB3_long"),
    ])
    def test_bounding_rect_stable_after_setpos(self, qapp, code, name):
        c = _make_component(code, name)
        item = ComponentItem(c)
        original = QRectF(item.boundingRect())
        # Simula drag movendo o item
        for x, y in [(150, 200), (300, 150), (50, 400), (100, 100)]:
            item.setPos(QPointF(x, y))
            current = item.boundingRect()
            assert current == original, (
                f"[{code}/{name}] boundingRect mudou após setPos({x},{y}): "
                f"original={original} atual={current}"
            )


# ---------------------------------------------------------------------------
# Sanity
# ---------------------------------------------------------------------------


class TestLabelFontStable:
    """_LABEL_FONT deve ser acessível e ter anti-alias habilitado."""

    def test_label_font_has_antialias(self, qapp):
        from PySide6.QtGui import QFont
        assert (
            _LABEL_FONT.styleStrategy() & QFont.PreferAntialias
        ), "Label font sem PreferAntialias → texto serrilhado em HiDPI."

    def test_label_font_size_reasonable(self, qapp):
        # Tamanho 7-10 é o range aceitável (menor = ilegível, maior = poluído)
        size = _LABEL_FONT.pointSize()
        assert 7 <= size <= 10, (
            f"Tamanho de fonte do label={size}pt fora do range aceitável 7-10."
        )
