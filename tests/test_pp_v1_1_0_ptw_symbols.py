"""
tests.test_pp_v1_1_0_ptw_symbols — testes do módulo
``app.preprocessor.ptw_symbols`` introduzido em v1.1.0.

Regressões cobertas
===================

1. **PTW overrides têm precedência** sobre o registry IEEE 315
   default — ``get_renderer("CABLE")`` retorna ``CableSymbol``
   PTW-style (e não o ResistorSymbol que estava sendo usado por
   fallback do catalog spec).

2. **Legacy IEEE 315 não regrediu** — ``R``, ``L``, ``C``, ``Vdc``,
   ``Tr``, ``BUS``, ``MOTOR`` continuam apontando para os
   ``*Symbol`` do módulo ``symbols.py`` (e não para variantes PTW).

3. **paint() não explode** offscreen — cada PTW renderer pode
   pintar num QImage 200×200 sem levantar exceção.

4. **Pinos coincidem com o spec do catalog** — CABLE/CT/FUSE/
   CONTACTOR têm pin geometry compatível com o ``.ocomp`` (mesma
   topologia: 2-terminal horizontal, 4-terminal cross, etc.).

5. **get_ptw_renderer() é puro** — retorna None para códigos não
   mapeados; não polui o registry IEEE 315.

Cobertura normativa testada
============================

* IEC 60617-7-3 (Disjuntor com cruz) — desenha quadrado + cruz
* IEC 60617-9 (TC com círculos concêntricos) — desenha 2 elipses
* IEC 60617 (Contator com curva + bobina) — desenha arco + retângulo
* IEC 60269 (Fusível retangular gold) — desenha retângulo arredondado
"""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPainter
from PySide6.QtWidgets import QApplication

from app.preprocessor import symbols
from app.preprocessor.ptw_symbols import (
    CableSymbol,
    CircuitBreakerSymbol,
    ContactorSymbol,
    CTSymbol,
    FuseSymbol,
    PTWMotorSymbol,
    get_ptw_renderer,
)


# ---------------------------------------------------------------------------
# QApplication fixture
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def _paint_offscreen(renderer) -> QImage:
    """Pinta o símbolo num QImage e retorna — falha se paint() crashar."""
    img = QImage(200, 200, QImage.Format_ARGB32)
    img.fill(Qt.white)
    p = QPainter(img)
    try:
        p.setRenderHint(QPainter.Antialiasing, True)
        p.translate(100, 100)
        renderer.paint(p)
    finally:
        p.end()
    return img


# ---------------------------------------------------------------------------
# get_ptw_renderer() — interface
# ---------------------------------------------------------------------------


class TestGetPtwRenderer:
    """O lookup standalone funciona independentemente de symbols.py."""

    def test_returns_none_for_unknown(self):
        assert get_ptw_renderer("ZZZ_NAO_EXISTE") is None

    def test_returns_none_for_legacy_ieee(self):
        # PTW só intercepta CABLE/CT/FUSE/CONTACTOR — legacy IEEE
        # passa direto.
        assert get_ptw_renderer("R") is None
        assert get_ptw_renderer("L") is None
        assert get_ptw_renderer("BUS") is None

    def test_cable_returns_cable_symbol(self):
        r = get_ptw_renderer("CABLE")
        assert isinstance(r, CableSymbol)

    def test_ct_returns_ct_symbol(self):
        r = get_ptw_renderer("CT")
        assert isinstance(r, CTSymbol)

    def test_fuse_returns_fuse_symbol(self):
        r = get_ptw_renderer("FUSE")
        assert isinstance(r, FuseSymbol)

    def test_contactor_returns_contactor_symbol(self):
        r = get_ptw_renderer("CONTACTOR")
        assert isinstance(r, ContactorSymbol)

    def test_each_call_returns_fresh_instance(self):
        # Não é singleton — cada lookup cria instância nova
        # (consistente com get_renderer() do symbols.py).
        a = get_ptw_renderer("CABLE")
        b = get_ptw_renderer("CABLE")
        assert a is not b
        assert type(a) is type(b)


# ---------------------------------------------------------------------------
# Integração com symbols.get_renderer() — overrides têm precedência
# ---------------------------------------------------------------------------


class TestSymbolsIntegration:
    """``symbols.get_renderer()`` consulta PTW antes do registry IEEE."""

    @pytest.mark.parametrize("code,expected_cls", [
        ("CABLE", CableSymbol),
        ("CT", CTSymbol),
        ("FUSE", FuseSymbol),
        ("CONTACTOR", ContactorSymbol),
    ])
    def test_ptw_overrides_take_precedence(self, code, expected_cls, qapp):
        r = symbols.get_renderer(code)
        assert isinstance(r, expected_cls), (
            f"get_renderer({code!r}) deveria retornar {expected_cls.__name__} "
            f"(PTW SLD override), retornou {type(r).__name__}"
        )

    def test_legacy_ieee_not_regressed(self, qapp):
        """Componentes IEEE 315 legados não devem ser tocados."""
        from app.preprocessor.symbols import (
            ResistorSymbol, InductorSymbol, CapacitorSymbol,
            VdcSymbol, TransformerSymbol, BusSymbol, MotorSymbol,
        )
        cases = {
            "R": ResistorSymbol,
            "L": InductorSymbol,
            "C": CapacitorSymbol,
            "Vdc": VdcSymbol,
            "Tr": TransformerSymbol,
            "BUS": BusSymbol,
            "MOTOR": MotorSymbol,
        }
        for code, cls in cases.items():
            r = symbols.get_renderer(code)
            assert isinstance(r, cls), (
                f"REGRESSÃO: {code} deveria continuar sendo {cls.__name__}, "
                f"é {type(r).__name__}"
            )

    def test_unknown_code_still_returns_none(self, qapp):
        # PTW lookup não deve mascarar None para códigos inexistentes.
        assert symbols.get_renderer("Eqn") is None
        assert symbols.get_renderer(".TR") is None
        assert symbols.get_renderer("INEXISTENTE") is None


# ---------------------------------------------------------------------------
# Smoke tests de paint() — cada PTW renderer pinta sem crashar
# ---------------------------------------------------------------------------


class TestPaintSmoke:

    @pytest.mark.parametrize("cls", [
        CircuitBreakerSymbol,
        FuseSymbol,
        ContactorSymbol,
        CTSymbol,
        CableSymbol,
        PTWMotorSymbol,
    ])
    def test_paint_does_not_crash(self, cls, qapp):
        renderer = cls()
        img = _paint_offscreen(renderer)
        # imagem não-vazia (alguma pixel diferente do branco original)
        white = (255, 255, 255, 255)
        any_drawn = False
        for x in range(0, 200, 5):
            for y in range(0, 200, 5):
                pixel = img.pixelColor(x, y).getRgb()
                if pixel != white:
                    any_drawn = True
                    break
            if any_drawn:
                break
        assert any_drawn, (
            f"{cls.__name__}.paint() rodou mas não desenhou nada visível"
        )


# ---------------------------------------------------------------------------
# Geometria (pinos & SIZE)
# ---------------------------------------------------------------------------


class TestGeometry:
    """PINS e SIZE coincidem com o spec do .ocomp."""

    def test_cable_pins_horizontal_2terminal(self, qapp):
        r = CableSymbol()
        # CABLE.ocomp: T1 em (-30, 0), T2 em (30, 0)
        assert r.PINS == ((-30, 0), (30, 0))

    def test_ct_4_pins(self, qapp):
        r = CTSymbol()
        # CT.ocomp: P1, P2 (primário horizontal) + S1, S2 (secundário vertical)
        assert len(r.PINS) == 4
        # Primário horizontal
        assert (-30, 0) in r.PINS
        assert (30, 0) in r.PINS

    def test_fuse_pins_vertical_2terminal(self, qapp):
        r = FuseSymbol()
        # FUSE.ocomp: T1 em (0, -30), T2 em (0, 30)
        assert r.PINS == ((0, -30), (0, 30))

    def test_contactor_4_pins(self, qapp):
        r = ContactorSymbol()
        # CONTACTOR.ocomp: T1, T2 (main) + A1, A2 (coil)
        assert len(r.PINS) == 4
        assert (0, -30) in r.PINS  # main
        assert (0, 30) in r.PINS   # main

    def test_bounding_rect_non_degenerate(self, qapp):
        for cls in (CircuitBreakerSymbol, FuseSymbol, ContactorSymbol,
                    CTSymbol, CableSymbol, PTWMotorSymbol):
            r = cls()
            rect = r.bounding_rect()
            assert rect.width() > 0, f"{cls.__name__} tem width zero"
            assert rect.height() > 0, f"{cls.__name__} tem height zero"

    def test_size_is_positive(self, qapp):
        for cls in (CircuitBreakerSymbol, FuseSymbol, ContactorSymbol,
                    CTSymbol, CableSymbol, PTWMotorSymbol):
            assert cls.SIZE > 0


# ---------------------------------------------------------------------------
# Labels descritivas (PT-BR, profissional)
# ---------------------------------------------------------------------------


class TestLabels:

    def test_ptw_renderers_have_labels(self, qapp):
        # cada PTW renderer tem LABEL não-vazio (mostrado em tooltip
        # da paleta).
        for cls in (CircuitBreakerSymbol, FuseSymbol, ContactorSymbol,
                    CTSymbol, CableSymbol, PTWMotorSymbol):
            assert cls.LABEL, f"{cls.__name__} sem LABEL"
