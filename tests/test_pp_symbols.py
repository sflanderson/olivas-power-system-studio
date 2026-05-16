"""
Tests for ``app.preprocessor.symbols`` — biblioteca visual IEEE 315.

Objetivos
---------

1. **Smoke tests**: cada `SymbolRenderer` do registry pode ser
   instanciado, retorna um *bounding rect* não-degenerado, tem lista
   de pinos, e `paint()` não explode quando chamado num `QImage`
   offscreen.
2. **Consistência com node_coalescer**: para cada tipo que aparece
   em ambos `symbols._REGISTRY` e `node_coalescer._PIN_GEOMETRY`,
   as coordenadas dos pinos devem ser idênticas (caso contrário
   o símbolo desenhado não "encaixa" no nó elétrico calculado).
3. **Cobertura do catálogo**: todo tipo do `catalog` com
   `atp_supported=True` (exceto "Eqn", que é só bloco de equações)
   deve ter um renderer.
4. **Registry lookup**: `get_renderer()` sabe dizer Não (None)
   para códigos inexistentes e Sim (instância) para os 30+
   códigos registrados.
"""

from __future__ import annotations

import pytest

# PySide6 é obrigatório — os símbolos usam QPainter. Se o ambiente
# de CI não tiver Qt, o import falha e os testes são pulados.
pytest.importorskip("PySide6")

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPainter
from PySide6.QtWidgets import QApplication

from app.preprocessor import catalog, symbols
from app.preprocessor.node_coalescer import _PIN_GEOMETRY
from app.preprocessor.symbols import (
    CapacitorSymbol,
    DiodeSymbol,
    GroundSymbol,
    GTOSymbol,
    IacSymbol,
    IdcSymbol,
    IGBTSymbol,
    InductorSymbol,
    IProbeSymbol,
    LineBergeronSymbol,
    LineJMartiSymbol,
    LinePISymbol,
    ModelUseSymbol,
    MOSFETSymbol,
    NonLinearLSymbol,
    NonLinearRSymbol,
    RelaisSymbol,
    ResistorSymbol,
    SwitchIdealSymbol,
    SymbolRenderer,
    TACSSourceSymbol,
    ThyristorSymbol,
    TransformerSymbol,
    VacSymbol,
    VdcSymbol,
    VProbeSymbol,
    ZnOSymbol,
    all_renderers,
    get_renderer,
)


# ---------------------------------------------------------------------------
# QApplication fixture — PySide6 exige que exista uma instância viva
# antes de criar QImage/QPainter em qualquer thread.
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def _paint_on_image(renderer: SymbolRenderer) -> QImage:
    """
    Cria um QImage offscreen e pinta o símbolo no centro.
    Levanta qualquer exceção de render (o teste falha se paint() crashar).
    """
    img = QImage(200, 200, QImage.Format_ARGB32)
    img.fill(Qt.white)
    p = QPainter(img)
    try:
        p.setRenderHint(QPainter.Antialiasing, True)
        p.translate(100, 100)   # desenha no centro
        renderer.paint(p)
    finally:
        p.end()
    return img


# ---------------------------------------------------------------------------
# Registry sanity
# ---------------------------------------------------------------------------


class TestRegistry:

    def test_registry_non_empty(self):
        reg = all_renderers()
        assert len(reg) >= 24, f"registry suspeito de regressão: {len(reg)} entradas"

    def test_get_renderer_returns_instance_for_known(self, qapp):
        r = get_renderer("R")
        assert isinstance(r, ResistorSymbol)

    def test_get_renderer_returns_none_for_unknown(self, qapp):
        assert get_renderer("ZZZ_NAO_EXISTE") is None

    def test_get_renderer_returns_fresh_instance(self, qapp):
        a = get_renderer("C")
        b = get_renderer("C")
        assert a is not b   # não é singleton — cada chamada cria nova instância
        assert type(a) is type(b)

    def test_relais_is_distinct_from_swideal(self, qapp):
        # Regressão: Relais precisa de seu próprio renderer (pinos ±50).
        r = get_renderer("Relais")
        s = get_renderer("SwIdeal")
        assert isinstance(r, RelaisSymbol)
        assert not isinstance(s, RelaisSymbol)
        assert r.pin_positions() != s.pin_positions()


# ---------------------------------------------------------------------------
# Cobertura do catálogo
# ---------------------------------------------------------------------------


class TestCatalogCoverage:
    """Todo tipo atp_supported precisa de renderer (exceto Eqn)."""

    # Eqn é um bloco de equações — não tem visual; é só metadata.
    _EXEMPT = {"Eqn"}

    @pytest.mark.parametrize("entry", catalog.all_entries(),
                              ids=lambda e: e.code)
    def test_every_supported_type_has_renderer(self, entry, qapp):
        if not entry.atp_supported or entry.code in self._EXEMPT:
            pytest.skip(f"{entry.code} não precisa de renderer")
        assert get_renderer(entry.code) is not None, \
            f"catálogo promete {entry.code} mas symbols._REGISTRY não tem"


# ---------------------------------------------------------------------------
# Consistência de pinos entre symbols e node_coalescer
# ---------------------------------------------------------------------------


class TestPinConsistency:
    """
    Para cada tipo em symbols._REGISTRY, se também está em
    node_coalescer._PIN_GEOMETRY, os pinos devem ser idênticos.
    """

    @pytest.mark.parametrize("code", sorted(all_renderers().keys()))
    def test_pins_match_node_coalescer(self, code, qapp):
        if code not in _PIN_GEOMETRY:
            pytest.skip(f"{code} não tem geometria explícita no coalescer")
        sym = get_renderer(code)
        pins_sym = sym.pin_positions()
        pins_nc = _PIN_GEOMETRY[code]
        assert pins_sym == pins_nc, (
            f"Inconsistência em {code}: symbols diz {pins_sym}, "
            f"node_coalescer diz {pins_nc}. As duas tabelas precisam "
            f"estar alinhadas ou o pino desenhado não cai em cima "
            f"do nó calculado."
        )


# ---------------------------------------------------------------------------
# Bounding rect + paint smoke test em cada tipo registrado
# ---------------------------------------------------------------------------


class TestRendererSmoke:
    """
    Instancia cada renderer do registry, confere bounding rect e
    pinta num QImage offscreen. Qualquer exceção reprova o teste.
    """

    @pytest.mark.parametrize("code", sorted(all_renderers().keys()))
    def test_bounding_rect_non_degenerate(self, code, qapp):
        sym = get_renderer(code)
        br = sym.bounding_rect()
        assert br.width() > 0, f"{code}: bounding rect degenerado em X"
        assert br.height() > 0, f"{code}: bounding rect degenerado em Y"

    @pytest.mark.parametrize("code", sorted(all_renderers().keys()))
    def test_paint_does_not_raise(self, code, qapp):
        sym = get_renderer(code)
        img = _paint_on_image(sym)
        # Se paint() não modificou nada, a imagem continua toda branca;
        # isso indica que o símbolo é efetivamente invisível — bug.
        # Amostra central (onde pintamos).
        c = img.pixelColor(100, 100)
        # Com alta probabilidade, a pintura tocou o quadrado central
        # pelo menos em algum lugar (bounding rect ≥ 24x24). Checamos
        # uma área em torno do centro para capturar traços.
        found_ink = False
        for dx in range(-20, 21, 2):
            for dy in range(-20, 21, 2):
                px = img.pixelColor(100 + dx, 100 + dy)
                if px.red() < 250 or px.green() < 250 or px.blue() < 250:
                    found_ink = True
                    break
            if found_ink:
                break
        assert found_ink, f"{code}: paint() não deixou nenhum traço visível"

    @pytest.mark.parametrize("code", sorted(all_renderers().keys()))
    def test_pin_positions_are_tuples(self, code, qapp):
        sym = get_renderer(code)
        pins = sym.pin_positions()
        assert isinstance(pins, list)
        for p in pins:
            assert isinstance(p, tuple)
            assert len(p) == 2
            assert isinstance(p[0], int)
            assert isinstance(p[1], int)


# ---------------------------------------------------------------------------
# Regras por família
# ---------------------------------------------------------------------------


class TestFamilyInvariants:

    def test_ground_has_single_pin_at_origin(self, qapp):
        g = GroundSymbol()
        assert g.pin_positions() == [(0, 0)]

    def test_resistor_default_vertical(self, qapp):
        assert ResistorSymbol().pin_positions() == [(0, -30), (0, 30)]

    def test_inductor_default_vertical(self, qapp):
        assert InductorSymbol().pin_positions() == [(0, -30), (0, 30)]

    def test_capacitor_default_vertical(self, qapp):
        assert CapacitorSymbol().pin_positions() == [(0, -30), (0, 30)]

    def test_diode_is_horizontal(self, qapp):
        # Diodos no Qucs vêm horizontais por default.
        assert DiodeSymbol().pin_positions() == [(-30, 0), (30, 0)]

    def test_thyristor_has_gate(self, qapp):
        pins = ThyristorSymbol().pin_positions()
        assert len(pins) == 3
        # 2 primeiros são A, K horizontais; terceiro é o gate.
        assert (-30, 0) in pins and (30, 0) in pins

    def test_gto_inherits_thyristor_gate(self, qapp):
        assert len(GTOSymbol().pin_positions()) == 3

    def test_igbt_has_gate(self, qapp):
        pins = IGBTSymbol().pin_positions()
        assert len(pins) == 3

    def test_mosfet_has_gate(self, qapp):
        pins = MOSFETSymbol().pin_positions()
        assert len(pins) == 3

    def test_transformer_has_four_pins(self, qapp):
        pins = TransformerSymbol().pin_positions()
        assert len(pins) == 4
        # 2 na esquerda, 2 na direita
        left = [p for p in pins if p[0] < 0]
        right = [p for p in pins if p[0] > 0]
        assert len(left) == 2
        assert len(right) == 2

    def test_switch_is_horizontal(self, qapp):
        assert SwitchIdealSymbol().pin_positions() == [(-30, 0), (30, 0)]

    def test_relais_has_long_leads(self, qapp):
        # Qucs Relais: pinos em ±50 em vez de ±30.
        assert RelaisSymbol().pin_positions() == [(-50, 0), (50, 0)]

    def test_line_symbols_horizontal(self, qapp):
        for cls in (LinePISymbol, LineBergeronSymbol, LineJMartiSymbol):
            assert cls().pin_positions() == [(-30, 0), (30, 0)]

    def test_control_blocks_have_no_pins(self, qapp):
        # TACS source e MODEL são blocos de controle — sem pinos
        # elétricos (topologia só via labels de TACS / variáveis).
        assert TACSSourceSymbol().pin_positions() == []
        assert ModelUseSymbol().pin_positions() == []

    def test_v_probe_inherits_vertical_pair(self, qapp):
        assert VProbeSymbol().pin_positions() == [(0, -30), (0, 30)]

    def test_i_probe_inherits_horizontal_pair(self, qapp):
        assert IProbeSymbol().pin_positions() == [(-30, 0), (30, 0)]


# ---------------------------------------------------------------------------
# Contrato do base class
# ---------------------------------------------------------------------------


class TestSymbolRendererBase:

    def test_abstract_paint_raises(self, qapp):
        base = SymbolRenderer()
        img = QImage(50, 50, QImage.Format_ARGB32)
        img.fill(Qt.white)
        p = QPainter(img)
        try:
            with pytest.raises(NotImplementedError):
                base.paint(p)
        finally:
            p.end()

    def test_default_bounding_rect_is_symmetric_square(self, qapp):
        class Dummy(SymbolRenderer):
            SIZE = 40

            def paint(self, p):
                pass

        d = Dummy()
        br = d.bounding_rect()
        assert br.width() == 40
        assert br.height() == 40
        assert br.x() == -20
        assert br.y() == -20

    def test_default_pins_are_2_terminal_vertical(self, qapp):
        class Dummy(SymbolRenderer):
            def paint(self, p):
                pass

        assert Dummy().pin_positions() == [(0, -30), (0, 30)]


# ---------------------------------------------------------------------------
# Herança (smoke): classes derivadas não quebram o protocolo
# ---------------------------------------------------------------------------


class TestInheritance:

    @pytest.mark.parametrize("derived_cls,parent_cls", [
        (IdcSymbol, VdcSymbol),
        (IacSymbol, VacSymbol),
        (ThyristorSymbol, DiodeSymbol),
        (GTOSymbol, ThyristorSymbol),
        (MOSFETSymbol, IGBTSymbol),
        (NonLinearRSymbol, ResistorSymbol),
        (NonLinearLSymbol, InductorSymbol),
        (LinePISymbol, symbols._LineBox),
        (LineBergeronSymbol, symbols._LineBox),
        (LineJMartiSymbol, symbols._LineBox),
        (TACSSourceSymbol, symbols._TextBox),
        (ModelUseSymbol, symbols._TextBox),
        (RelaisSymbol, SwitchIdealSymbol),
    ])
    def test_inheritance_is_preserved(self, derived_cls, parent_cls, qapp):
        assert issubclass(derived_cls, parent_cls)
        # E a instância herda todo o protocolo base.
        assert isinstance(derived_cls(), SymbolRenderer)
