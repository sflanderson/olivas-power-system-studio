"""
tests/test_pp_v3_1_1_tags.py — v3.1.1 Sprint 4.

Link Tags + Legend Tags — PTW Tutorial §Part 1 p.35-52.

Cobre:
* PpLinkTag dataclass (label, target URI, x/y, visible, closed_arrow)
* PpLegendTag dataclass (text, shape ∈ Diamond/Hexagon/Circle/Rectangle, color)
* PpProject.link_tags / legend_tags lists default empty (backward-compat)
* Invalid shape raises ValueError
"""

from __future__ import annotations

import pytest


class TestPpLinkTag:

    def test_default_construction(self):
        from app.preprocessor.models import PpLinkTag
        tag = PpLinkTag(label="Go to TCC-A", target="tcc:CoordA")
        assert tag.label == "Go to TCC-A"
        assert tag.target == "tcc:CoordA"
        assert tag.x == 0 and tag.y == 0
        assert tag.visible is True
        assert tag.closed_arrow is True

    def test_target_uri_prefixes_supported(self):
        """4 prefixes per Tutorial §Part 1 p.35: oneline / tcc / report / pdf."""
        from app.preprocessor.models import PpLinkTag
        for prefix in ("oneline:", "tcc:", "report:", "pdf:"):
            tag = PpLinkTag(label="X", target=f"{prefix}target")
            assert tag.target.startswith(prefix)

    def test_position_and_visibility(self):
        from app.preprocessor.models import PpLinkTag
        tag = PpLinkTag(
            label="Hide me", target="report:foo",
            x=100, y=200, visible=False, closed_arrow=False,
        )
        assert (tag.x, tag.y) == (100, 200)
        assert tag.visible is False
        assert tag.closed_arrow is False


class TestPpLegendTag:

    def test_default_diamond_shape(self):
        from app.preprocessor.models import PpLegendTag
        tag = PpLegendTag(text="Zone A")
        assert tag.shape == "Diamond"  # default
        assert tag.color == "#fff7c0"  # PTW yellow
        assert tag.visible is True

    def test_all_4_shapes_valid(self):
        from app.preprocessor.models import PpLegendTag
        for shape in ("Diamond", "Hexagon", "Circle", "Rectangle"):
            tag = PpLegendTag(text="Test", shape=shape)
            assert tag.shape == shape

    def test_invalid_shape_raises(self):
        from app.preprocessor.models import PpLegendTag
        with pytest.raises(ValueError, match="shape must be"):
            PpLegendTag(text="Bad", shape="Triangle")
        with pytest.raises(ValueError):
            PpLegendTag(text="Bad", shape="")

    def test_custom_color(self):
        from app.preprocessor.models import PpLegendTag
        tag = PpLegendTag(text="Critical", shape="Hexagon", color="#ff0000")
        assert tag.color == "#ff0000"


class TestPpProjectIntegration:

    def test_project_default_empty_tag_lists(self):
        """PpProject sem tags = listas vazias (backward-compat)."""
        from app.preprocessor.models import PpProject
        p = PpProject()
        assert p.link_tags == []
        assert p.legend_tags == []

    def test_project_with_tags(self):
        """PpProject pode conter ambos tipos de tag."""
        from app.preprocessor.models import (
            PpLegendTag, PpLinkTag, PpProject,
        )
        p = PpProject()
        p.link_tags.append(PpLinkTag(
            label="See TCC-A", target="tcc:CoordA", x=50, y=50,
        ))
        p.legend_tags.append(PpLegendTag(
            text="Zone HV", shape="Diamond", x=200, y=100,
        ))
        p.legend_tags.append(PpLegendTag(
            text="Zone LV", shape="Hexagon", x=200, y=200, color="#80c0ff",
        ))
        assert len(p.link_tags) == 1
        assert len(p.legend_tags) == 2
        assert p.legend_tags[0].shape == "Diamond"
        assert p.legend_tags[1].shape == "Hexagon"


class TestSeventhGuaranteeAccessibility:

    def test_models_documents_link_tags(self):
        """Docstring de PpLinkTag cita Tutorial §Part 1."""
        with open(
            "D:/000 - UFMG - DOUTORADO/MVP/app/preprocessor/models.py",
            encoding="utf-8",
        ) as f:
            content = f.read()
        assert "PpLinkTag" in content
        assert "PpLegendTag" in content
        assert "§Part 1" in content
        assert "Tutorial" in content
