"""
tests/test_pp_type98.py — v0.24.2: emissor Type-98 (reator
pseudo-não-linear PWL) para estudos de saturação (inrush,
ferrorressonância).

Cobre:

* ``SaturationPoint`` — rejeita negativos.
* ``SaturationCurve`` — exige ≥2 pontos, monotonicidade em i e ψ.
* ``parse_csv_curve`` — aceita formatos bem-formados, rejeita
  malformados, tolera espaços e trailing semicolon.
* ``default_saturation_curve`` — canônica, 5 pontos, origem.
* ``knee_point`` — detecção do joelho.
* ``emit_type98_cards`` — formato ATP: tipo "98" + pontos + "9999".
* ``emit_type98_from_csv`` — atalho.

Não cobre (próximas sub-sprints):
* Integração com BCTRAN em trafos (shunt no node H).
* LNL.ocomp → Type-98 no bridge.
"""

from __future__ import annotations

import pytest

from app.preprocessor.type98 import (
    SaturationCurve,
    SaturationPoint,
    default_saturation_curve,
    emit_type98_cards,
    emit_type98_from_csv,
    parse_csv_curve,
)


# ---------------------------------------------------------------------------
# SaturationPoint
# ---------------------------------------------------------------------------


class TestSaturationPoint:
    def test_zero_is_valid(self):
        p = SaturationPoint(0.0, 0.0)
        assert p.current == 0.0
        assert p.flux == 0.0

    def test_positive_is_valid(self):
        p = SaturationPoint(5.0, 1.05)
        assert p.current == 5.0
        assert p.flux == 1.05

    def test_negative_current_rejected(self):
        with pytest.raises(ValueError, match="current negativo"):
            SaturationPoint(-1.0, 1.0)

    def test_negative_flux_rejected(self):
        with pytest.raises(ValueError, match="flux negativo"):
            SaturationPoint(1.0, -0.5)

    def test_frozen(self):
        """Dataclass frozen — imutável."""
        p = SaturationPoint(1.0, 1.0)
        with pytest.raises((AttributeError, Exception)):
            p.current = 2.0   # type: ignore


# ---------------------------------------------------------------------------
# SaturationCurve
# ---------------------------------------------------------------------------


class TestSaturationCurve:
    def test_single_point_rejected(self):
        with pytest.raises(ValueError, match="pelo menos 2"):
            SaturationCurve(points=[SaturationPoint(1.0, 1.0)])

    def test_empty_rejected(self):
        with pytest.raises(ValueError, match="pelo menos 2"):
            SaturationCurve(points=[])

    def test_valid_2_points(self):
        c = SaturationCurve(points=[
            SaturationPoint(0.0, 0.0),
            SaturationPoint(1.0, 1.0),
        ])
        assert len(c.points) == 2

    def test_non_monotonic_current_rejected(self):
        with pytest.raises(ValueError, match="current não-monotônico"):
            SaturationCurve(points=[
                SaturationPoint(0.0, 0.0),
                SaturationPoint(5.0, 0.5),
                SaturationPoint(3.0, 1.0),  # current decrementou
            ])

    def test_non_monotonic_flux_rejected(self):
        with pytest.raises(ValueError, match="flux não-monotônico"):
            SaturationCurve(points=[
                SaturationPoint(0.0, 1.0),
                SaturationPoint(1.0, 0.5),  # flux decrementou
            ])

    def test_equal_current_rejected(self):
        """Estritamente crescente — iguais também rejeitados."""
        with pytest.raises(ValueError, match="current"):
            SaturationCurve(points=[
                SaturationPoint(1.0, 0.5),
                SaturationPoint(1.0, 1.0),
            ])

    def test_is_canonical_origin_zero(self):
        c = SaturationCurve(points=[
            SaturationPoint(0.0, 0.0),
            SaturationPoint(1.0, 1.0),
        ])
        assert c.is_canonical()

    def test_is_canonical_false_when_offset(self):
        c = SaturationCurve(points=[
            SaturationPoint(0.1, 0.05),
            SaturationPoint(1.0, 1.0),
        ])
        assert not c.is_canonical()

    def test_knee_point_detection_on_canonical(self):
        c = default_saturation_curve()
        knee = c.knee_point()
        # Joelho deve estar no segundo ou terceiro ponto — onde a
        # curva "dobra"
        assert 0.5 < knee.current < 50.0
        assert 0.5 < knee.flux < 1.2

    def test_knee_point_two_points_returns_last(self):
        c = SaturationCurve(points=[
            SaturationPoint(0.0, 0.0),
            SaturationPoint(10.0, 1.0),
        ])
        knee = c.knee_point()
        assert knee.current == 10.0


# ---------------------------------------------------------------------------
# Parsing CSV
# ---------------------------------------------------------------------------


class TestParseCsvCurve:
    def test_basic_csv(self):
        c = parse_csv_curve("0,0; 1,1; 5,2")
        assert len(c.points) == 3
        assert c.points[0].current == 0.0
        assert c.points[2].flux == 2.0

    def test_spaces_ignored(self):
        c = parse_csv_curve("  0 , 0 ;  5 , 1.0  ;  50 , 1.1  ")
        assert len(c.points) == 3

    def test_trailing_semicolon(self):
        c = parse_csv_curve("0,0; 1,1; 5,2;")
        assert len(c.points) == 3

    def test_empty_csv_rejected(self):
        with pytest.raises(ValueError, match="CSV vazio"):
            parse_csv_curve("")

    def test_empty_csv_whitespace_rejected(self):
        with pytest.raises(ValueError, match="CSV vazio"):
            parse_csv_curve("   ")

    def test_malformed_triple_comma_rejected(self):
        """Ponto com 3 valores → rejeitar."""
        with pytest.raises(ValueError, match="malformado"):
            parse_csv_curve("0,0,0; 1,1")

    def test_non_numeric_rejected(self):
        with pytest.raises(ValueError, match="não-numérico"):
            parse_csv_curve("0,0; abc,1.0")

    def test_scientific_notation_accepted(self):
        c = parse_csv_curve("0,0; 1e-3,1e-2; 1e2,1.5")
        assert c.points[1].current == pytest.approx(1e-3)
        assert c.points[1].flux == pytest.approx(1e-2)

    def test_parsing_propagates_monotonic_validation(self):
        """Parser delega validação para SaturationCurve.__post_init__."""
        with pytest.raises(ValueError, match="current não-monotônico"):
            parse_csv_curve("0,0; 5,1.0; 3,1.5")


# ---------------------------------------------------------------------------
# default_saturation_curve
# ---------------------------------------------------------------------------


class TestDefaultCurve:
    def test_default_is_canonical(self):
        c = default_saturation_curve()
        assert c.is_canonical()

    def test_default_has_5_points(self):
        c = default_saturation_curve()
        assert len(c.points) == 5

    def test_default_is_monotonic(self):
        """Já validado pelo __post_init__ — smoke check."""
        c = default_saturation_curve()
        for i in range(1, len(c.points)):
            assert c.points[i].current > c.points[i - 1].current
            assert c.points[i].flux > c.points[i - 1].flux

    def test_default_has_reasonable_saturation(self):
        """Último ponto deve ter i >> 1 (saturação profunda)."""
        c = default_saturation_curve()
        assert c.points[-1].current > 50.0


# ---------------------------------------------------------------------------
# emit_type98_cards
# ---------------------------------------------------------------------------


class TestEmitCards:
    def test_minimal_output(self):
        c = SaturationCurve(points=[
            SaturationPoint(0.0, 0.0),
            SaturationPoint(1.0, 1.0),
        ])
        cards = emit_type98_cards("BUS1", "GND", c)
        # Header + 2 pontos + terminador = 4 linhas (sem comentário)
        assert len(cards) == 4

    def test_header_starts_with_98(self):
        c = SaturationCurve(points=[
            SaturationPoint(0.0, 0.0), SaturationPoint(1.0, 1.0),
        ])
        cards = emit_type98_cards("BUS1", "GND", c)
        assert cards[0].startswith("98")

    def test_terminator_is_9999(self):
        c = SaturationCurve(points=[
            SaturationPoint(0.0, 0.0), SaturationPoint(1.0, 1.0),
        ])
        cards = emit_type98_cards("BUS1", "GND", c)
        assert cards[-1] == "9999"

    def test_comment_inserted_first(self):
        c = SaturationCurve(points=[
            SaturationPoint(0.0, 0.0), SaturationPoint(1.0, 1.0),
        ])
        cards = emit_type98_cards("B", "G", c, comment="Trafo 100 MVA")
        assert cards[0].startswith("C Trafo 100 MVA")
        assert cards[1].startswith("98")

    def test_nodes_in_header(self):
        c = SaturationCurve(points=[
            SaturationPoint(0.0, 0.0), SaturationPoint(1.0, 1.0),
        ])
        cards = emit_type98_cards("BUSH", "NEUTR", c)
        assert "BUSH" in cards[0]
        assert "NEUTR" in cards[0]

    def test_points_emitted_in_order(self):
        c = SaturationCurve(points=[
            SaturationPoint(0.0, 0.0),
            SaturationPoint(5.0, 1.0),
            SaturationPoint(50.0, 1.1),
        ])
        cards = emit_type98_cards("B", "G", c)
        # Cards 1 (header) + 2..4 (pontos) + 5 (terminator) = 5 linhas
        assert len(cards) == 5
        # Pontos em ordem
        assert "0.0000E+00" in cards[1]  # i=0 ponto 1
        assert "5.0000E+00" in cards[2]  # i=5 ponto 2
        assert "5.0000E+01" in cards[3]  # i=50 ponto 3

    def test_initial_ss_values_in_header(self):
        c = SaturationCurve(
            points=[SaturationPoint(0.0, 0.0), SaturationPoint(1.0, 1.0)],
            i_ss=0.5, flux_ss=0.9,
        )
        cards = emit_type98_cards("B", "G", c)
        # 0.5 e 0.9 aparecem no header em notação científica
        assert "5.0000E-01" in cards[0]
        assert "9.0000E-01" in cards[0]


# ---------------------------------------------------------------------------
# emit_type98_from_csv — atalho
# ---------------------------------------------------------------------------


class TestEmitFromCsv:
    def test_happy_path(self):
        cards = emit_type98_from_csv(
            "BUS1", "GND", "0,0; 1,1; 5,1.1",
        )
        assert cards[0].startswith("98")
        assert cards[-1] == "9999"

    def test_invalid_csv_propagates_error(self):
        with pytest.raises(ValueError):
            emit_type98_from_csv("B", "G", "0,0; 1,x")

    def test_comment_supported(self):
        cards = emit_type98_from_csv(
            "B", "G", "0,0; 1,1", comment="Reator saturável",
        )
        assert "Reator saturável" in cards[0]
