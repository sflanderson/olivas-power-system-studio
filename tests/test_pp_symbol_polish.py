"""
tests/test_pp_symbol_polish.py — Regressão do redesign v0.21.8.d.

A sprint v0.21.8.d refinou os símbolos visuais (hierarquia leads/corpo
via pens distintas, zigzag IEEE 315 mais canônico, 4 arcos no indutor,
placas mais largas no capacitor, GND com barra principal espessa,
marcadores +/- mais visíveis nas fontes DC, senoide simétrica no AC,
contatos filled na chave, cátodo THICK no diodo, câmara a vácuo
arredondada no VCB3).

Estes testes garantem:

1. Cada ``paint()`` termina sem exceção (smoke).
2. Todos os pixels pintados caem DENTRO do ``bounding_rect()`` —
   garantia anti-rastro (o bug de v0.21.8.c volta se algum renderer
   pintar fora).
3. Cada símbolo tem uma "assinatura visual" mínima — pixel count e
   posições-chave — que detecta regressão acidental (ex: alguém
   apagar o zigzag e deixar um simples retângulo).

Nota: não comparamos imagens pixel-a-pixel com um reference (frágil
em relação à versão do Qt e ao rendering backend). Em vez disso,
usamos INVARIANTES:
- "um pixel de linha em (x, y) ± 1"
- "área total ≥ N px" (impede símbolos vazios)
- "simetria em torno de x=0 dentro de uma tolerância"
"""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import QRectF
from PySide6.QtGui import QImage, QPainter
from PySide6.QtWidgets import QApplication

from app.preprocessor.symbols import (
    CapacitorSymbol,
    DiodeSymbol,
    GroundSymbol,
    InductorSymbol,
    ResistorSymbol,
    SwitchIdealSymbol,
    VacSymbol,
    VCB3PhaseSymbol,
    VdcSymbol,
    _PEN_LEAD,
    _PEN_NORMAL,
    _PEN_THICK,
)


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


_RENDERERS = [
    ("R", ResistorSymbol),
    ("L", InductorSymbol),
    ("C", CapacitorSymbol),
    ("GND", GroundSymbol),
    ("Vdc", VdcSymbol),
    ("Vac", VacSymbol),
    ("SwIdeal", SwitchIdealSymbol),
    ("Diode", DiodeSymbol),
    ("VCB3", VCB3PhaseSymbol),
]


def _render_to_image(renderer, pad: int = 20) -> tuple[QImage, QRectF]:
    """
    Renderiza o símbolo num QImage com ``pad`` px extra em cada lado.
    Retorna (imagem, bounding_rect original).

    Canvas total tem ``pad`` px de margem em torno do ``bounding_rect``
    — se o ``paint()`` desenhar fora do rect, o pixel cai nessa margem
    (capturável; se desenhar mais que ``pad`` px fora, o pixel é
    silenciosamente clippado pelo QImage, o que também é um bug).
    """
    br = renderer.bounding_rect()
    w = int(br.width() + 2 * pad)
    h = int(br.height() + 2 * pad)
    img = QImage(w, h, QImage.Format_ARGB32)
    img.fill(0xFFFFFFFF)  # branco opaco
    painter = QPainter(img)
    painter.setRenderHint(QPainter.Antialiasing, True)
    painter.translate(-br.left() + pad, -br.top() + pad)
    renderer.paint(painter)
    painter.end()
    return img, br


def _painted_pixels(img: QImage) -> list[tuple[int, int]]:
    """Coords (x, y) de pixels não-brancos (algo foi desenhado)."""
    out: list[tuple[int, int]] = []
    for y in range(img.height()):
        for x in range(img.width()):
            rgb = img.pixel(x, y) & 0xFFFFFF
            # Desenhado = não-branco (pode ter alphas intermediários
            # pela antialiasing; comparação frouxa).
            if rgb != 0xFFFFFF:
                out.append((x, y))
    return out


# ---------------------------------------------------------------------------
# Smoke: todos os paint() rodam
# ---------------------------------------------------------------------------


class TestPaintSmoke:
    @pytest.mark.parametrize("code,cls", _RENDERERS)
    def test_paint_runs_without_exception(self, qapp, code, cls):
        renderer = cls()
        img, _ = _render_to_image(renderer)
        assert img.width() > 0 and img.height() > 0


# ---------------------------------------------------------------------------
# Anti-rastro: todos os pixels pintados caem DENTRO do bounding_rect
# ---------------------------------------------------------------------------


class TestPaintInsideBoundingRect:
    """
    Invariante crítico: paint() NÃO pode desenhar fora do
    bounding_rect(). Se isso acontecer, o bug de rastro (v0.21.8.c)
    volta em cenários específicos.

    Método: renderiza num canvas com margem de ``pad=20`` px em torno
    do rect. Verifica que todos os pixels não-brancos caem dentro do
    retângulo esperado (com tolerância de 2 px para antialiasing).
    """

    PAD = 20
    ANTIALIAS_TOL = 2

    @pytest.mark.parametrize("code,cls", _RENDERERS)
    def test_paint_stays_within_bounding_rect(self, qapp, code, cls):
        renderer = cls()
        img, br = _render_to_image(renderer, pad=self.PAD)
        pixels = _painted_pixels(img)
        assert pixels, (
            f"[{code}] paint não desenhou nada — símbolo vazio?"
        )
        # O rect "permitido" é o bounding_rect trazido ao canvas
        # (deslocado em PAD). Adiciona ANTIALIAS_TOL de tolerância.
        x_min = self.PAD - self.ANTIALIAS_TOL
        y_min = self.PAD - self.ANTIALIAS_TOL
        x_max = self.PAD + int(br.width()) + self.ANTIALIAS_TOL
        y_max = self.PAD + int(br.height()) + self.ANTIALIAS_TOL
        outside = [
            (x, y) for (x, y) in pixels
            if not (x_min <= x <= x_max and y_min <= y <= y_max)
        ]
        if outside:
            pytest.fail(
                f"[{code}] {len(outside)} pixels pintados FORA do "
                f"bounding_rect (rect permitido x∈[{x_min},{x_max}], "
                f"y∈[{y_min},{y_max}]): primeiros 10 = {outside[:10]}"
            )


# ---------------------------------------------------------------------------
# Densidade mínima: cada símbolo tem área de pintura razoável
# ---------------------------------------------------------------------------


class TestSymbolHasMeaningfulContent:
    """
    Regressão contra "alguém apagou o corpo do símbolo e só sobraram
    os leads". Cada símbolo deve pintar pelo menos N pixels (com
    antialias, um R simples pinta ~500+).
    """

    # Threshold mínimo de pixels pintados, por código.
    # Calibrado empiricamente a partir de render offscreen com
    # antialias; valores reais em qpa=offscreen:
    #   R=242, L=188, C=228, GND=120, Vdc=324, Vac=348,
    #   SwIdeal=225, Diode=354, VCB3=1102.
    # Threshold = ~70% do valor real para tolerar diferenças de
    # renderer (font rendering, Qt version) sem falsos positivos.
    _MIN_PIXELS = {
        "R":       170,
        "L":       130,
        "C":       160,
        "GND":     80,
        "Vdc":     220,
        "Vac":     240,
        "SwIdeal": 150,
        "Diode":   240,
        "VCB3":    700,
    }

    @pytest.mark.parametrize("code,cls", _RENDERERS)
    def test_symbol_has_min_pixel_count(self, qapp, code, cls):
        renderer = cls()
        img, _ = _render_to_image(renderer)
        pixels = _painted_pixels(img)
        threshold = self._MIN_PIXELS[code]
        assert len(pixels) >= threshold, (
            f"[{code}] símbolo muito 'magro' — apenas {len(pixels)} "
            f"pixels pintados, threshold mínimo é {threshold}. "
            f"Alguém pode ter apagado parte do paint()."
        )


# ---------------------------------------------------------------------------
# Simetria (parcial): apenas C, GND e Vdc são simétricos em x=0
# ---------------------------------------------------------------------------


class TestSymbolSymmetry:
    """
    Apenas Capacitor (placas horizontais), GND (barras horizontais) e
    Vdc (marcadores centralizados) são genuinamente simétricos no eixo
    vertical.

    Símbolos DELIBERADAMENTE assimétricos (não aplicam este teste):

    * Resistor — zigzag IEEE 315 alterna lados. Primeiro pico em x=+5
      cria viés para a direita.
    * Inductor — 4 arcos semicirculares TODOS abrem para a direita
      (convenção IEEE).
    * Vac — senoide passa alternadamente acima e abaixo do eixo, mas
      o eixo horizontal se mantém (pequena assimetria nas junções).
    * Diode — aponta para a direita (assimetria definidora).
    * SwIdeal — alavanca inclinada; chave VCB3 mesmo padrão.
    """

    SYMMETRIC = [
        ("C",   CapacitorSymbol),
        ("GND", GroundSymbol),
        ("Vdc", VdcSymbol),
    ]

    @pytest.mark.parametrize("code,cls", SYMMETRIC)
    def test_vertical_axis_symmetry(self, qapp, code, cls):
        renderer = cls()
        img, br = _render_to_image(renderer)
        pixels = _painted_pixels(img)
        # Eixo de simetria = centro horizontal do canvas = PAD - br.left().
        cx = 20 - br.left()  # PAD=20
        left_count = sum(1 for (x, _) in pixels if x < cx - 1)
        right_count = sum(1 for (x, _) in pixels if x > cx + 1)
        total = left_count + right_count
        if total == 0:
            pytest.skip(f"[{code}] sem pixels fora do eixo — nada a comparar")
        # Desvio tolerado: 15% (antialiasing + round caps criam leve
        # ruído subpixel).
        delta = abs(left_count - right_count) / total
        assert delta < 0.15, (
            f"[{code}] símbolo assimétrico: left={left_count}, "
            f"right={right_count} (delta {delta:.1%} > 15%)"
        )


# ---------------------------------------------------------------------------
# Pen hierarchy: v0.21.8.d introduziu _PEN_LEAD < _PEN_NORMAL < _PEN_THICK
# ---------------------------------------------------------------------------


class TestPenHierarchy:
    """Garantir que a hierarquia de pen-widths está correta."""

    def test_pen_widths_are_ordered(self):
        """LEAD < NORMAL < THICK — hierarquia visual."""
        assert _PEN_LEAD.widthF() < _PEN_NORMAL.widthF() < _PEN_THICK.widthF(), (
            f"Pens fora de ordem: LEAD={_PEN_LEAD.widthF()}, "
            f"NORMAL={_PEN_NORMAL.widthF()}, THICK={_PEN_THICK.widthF()}"
        )

    def test_all_pens_use_round_cap(self):
        """RoundCap = sem serrilha nos endpoints, junções suaves."""
        from PySide6.QtCore import Qt
        for name, pen in [("LEAD", _PEN_LEAD), ("NORMAL", _PEN_NORMAL), ("THICK", _PEN_THICK)]:
            assert pen.capStyle() == Qt.RoundCap, (
                f"_PEN_{name} com capStyle={pen.capStyle()} — "
                f"esperado Qt.RoundCap para traços suaves."
            )
