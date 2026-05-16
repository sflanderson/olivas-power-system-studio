"""
tests.test_pp_v1_1_0_online_overlay — testes do modo
**Single-Line Diagram Online** (v1.1.0).

Cobre o módulo ``app.gui.schematic_pp.online_overlay`` e a
integração com ``app.gui.schematic_pp.items.ComponentItem``.

Cenários cobertos
==================

1. **Annotation builders (puros)**:
   - ``annotation_from_sc()`` mapeia Ik''/ip/rating → linhas + severidade
   - ``annotation_from_pf()`` aplica limites NBR 5410 (5%)
   - severidade ok/warn/violation conforme utilization

2. **OnlineOverlayManager**:
   - ``set_enabled()`` ON/OFF
   - ``refresh()`` lê StudyCache e anota componentes BUS
   - ``set_enabled(False)`` limpa todas anotações

3. **ComponentItem**:
   - ``set_online_annotation()`` / ``online_annotation()`` API
   - ``boundingRect()`` cresce para incluir o badge
   - ``paint()`` desenha o badge sem crashar
   - ``set_online_annotation(None)`` retira o badge

4. **Cobertura por tipo de componente**:
   - BUS recebe annotation se há SC no cache
   - Outros tipos (R, L, C) não recebem anotação
"""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPainter
from PySide6.QtWidgets import (
    QApplication, QGraphicsScene, QStyleOptionGraphicsItem,
)

from app.gui.schematic_pp.online_overlay import (
    OnlineAnnotation,
    OnlineOverlayManager,
    annotation_from_pf,
    annotation_from_sc,
    severity_colors,
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


# ---------------------------------------------------------------------------
# Fakes (avoid coupling com a API real do StudyCache no teste)
# ---------------------------------------------------------------------------


class _FakeSC:
    """Fake ScResult com apenas Ik_pp_kA e ip_kA."""

    def __init__(self, Ik_pp_kA: float, ip_kA: float = 0.0):
        self.Ik_pp_kA = Ik_pp_kA
        self.ip_kA = ip_kA


class _FakeCache:
    """Fake StudyCache com apenas get_sc()."""

    def __init__(self):
        self._sc: dict = {}

    def get_sc(self, bus_id: str):
        return self._sc.get(bus_id)

    def set_sc(self, bus_id: str, result):
        self._sc[bus_id] = result


# ---------------------------------------------------------------------------
# annotation_from_sc()
# ---------------------------------------------------------------------------


class TestAnnotationFromSc:

    def test_includes_Ik_and_ip(self):
        ann = annotation_from_sc(_FakeSC(Ik_pp_kA=12.5, ip_kA=30.1))
        assert any("12.50 kA" in line for line in ann.lines)
        assert any("30.10 kA" in line for line in ann.lines)

    def test_severity_ok_under_80percent(self):
        ann = annotation_from_sc(
            _FakeSC(Ik_pp_kA=10.0), bus_rating_kA=20.0,
        )
        # 50% utilization -> ok
        assert ann.severity == "ok"

    def test_severity_warn_at_80_to_99_percent(self):
        ann = annotation_from_sc(
            _FakeSC(Ik_pp_kA=12.0), bus_rating_kA=15.0,
        )
        # 80% utilization -> warn
        assert ann.severity == "warn"

    def test_severity_violation_at_100plus_percent(self):
        ann = annotation_from_sc(
            _FakeSC(Ik_pp_kA=20.0), bus_rating_kA=15.0,
        )
        # 133% utilization -> violation
        assert ann.severity == "violation"

    def test_severity_info_when_no_rating(self):
        ann = annotation_from_sc(_FakeSC(Ik_pp_kA=10.0))
        assert ann.severity == "info"

    def test_invalid_result_returns_warn(self):
        class _Broken:
            pass
        ann = annotation_from_sc(_Broken())
        assert ann.severity == "warn"
        assert "inválido" in ann.lines[0].lower()


# ---------------------------------------------------------------------------
# annotation_from_pf()
# ---------------------------------------------------------------------------


class TestAnnotationFromPf:

    def test_violation_below_95pu(self):
        # NBR 5410 §6.2.7 — limite 5% queda = 0.95 pu
        ann = annotation_from_pf(0.92)
        assert ann.severity == "violation"

    def test_ok_at_nominal(self):
        ann = annotation_from_pf(1.00)
        assert ann.severity == "ok"

    def test_warn_at_overvoltage(self):
        ann = annotation_from_pf(1.06)
        assert ann.severity == "warn"

    def test_includes_kV_when_nominal_provided(self):
        ann = annotation_from_pf(0.98, voltage_kV_nominal=13.8)
        # 0.98 * 13.8 = 13.524 kV
        assert any("13.52" in line for line in ann.lines)


# ---------------------------------------------------------------------------
# severity_colors
# ---------------------------------------------------------------------------


class TestSeverityColors:

    def test_known_severities(self):
        for sev in ("info", "ok", "warn", "violation"):
            text, bg = severity_colors(sev)
            assert text is not None and bg is not None

    def test_unknown_severity_falls_back_to_info(self):
        text_unknown, bg_unknown = severity_colors("nonsense")
        text_info, bg_info = severity_colors("info")
        assert text_unknown.name() == text_info.name()
        assert bg_unknown.name() == bg_info.name()


# ---------------------------------------------------------------------------
# OnlineOverlayManager — manager state
# ---------------------------------------------------------------------------


class TestOnlineOverlayManagerLifecycle:

    def test_starts_disabled(self):
        mgr = OnlineOverlayManager()
        assert mgr.is_enabled() is False

    def test_set_enabled_toggles_state(self):
        mgr = OnlineOverlayManager()
        mgr.set_enabled(True)
        assert mgr.is_enabled() is True
        mgr.set_enabled(False)
        assert mgr.is_enabled() is False

    def test_refresh_when_disabled_is_noop(self):
        mgr = OnlineOverlayManager()
        cache = _FakeCache()
        cache.set_sc("BUS-MAIN", _FakeSC(Ik_pp_kA=10.0))
        # Disabled — refresh should be no-op and return 0
        n = mgr.refresh(scene=None, study_cache=cache)
        assert n == 0


# ---------------------------------------------------------------------------
# Integration: OverlayManager + scene + ComponentItem
# ---------------------------------------------------------------------------


class TestOverlayManagerIntegration:

    def _make_bus_item(self, name: str = "BUS-MAIN"):
        from app.gui.schematic_pp.items import ComponentItem
        from app.preprocessor.models import PpComponent, PpProperty
        comp = PpComponent(
            type="BUS", name=name, visible=True,
            x=0, y=0, label_dx=0, label_dy=0,
            mirror=0, rotation=0,
            properties=[PpProperty(value="200", visible=False)],
        )
        return ComponentItem(comp)

    def _make_resistor_item(self, name: str = "R1"):
        from app.gui.schematic_pp.items import ComponentItem
        from app.preprocessor.models import PpComponent, PpProperty
        comp = PpComponent(
            type="R", name=name, visible=True,
            x=0, y=0, label_dx=0, label_dy=0,
            mirror=0, rotation=0,
            properties=[PpProperty(value="1 kOhm", visible=True)],
        )
        return ComponentItem(comp)

    def test_refresh_annotates_bus_with_sc_in_cache(self, qapp):
        scene = QGraphicsScene()
        bus_item = self._make_bus_item("BUS-MAIN")
        scene.addItem(bus_item)

        cache = _FakeCache()
        cache.set_sc("BUS-MAIN", _FakeSC(Ik_pp_kA=12.5, ip_kA=30.0))

        mgr = OnlineOverlayManager()
        mgr.set_enabled(True)
        n = mgr.refresh(scene, cache)

        assert n == 1
        ann = bus_item.online_annotation()
        assert ann is not None
        assert any("12.50" in line for line in ann.lines)

    def test_refresh_skips_buses_without_sc_in_cache(self, qapp):
        scene = QGraphicsScene()
        bus_item = self._make_bus_item("BUS-OTHER")
        scene.addItem(bus_item)

        cache = _FakeCache()
        # cache vazio — nenhum SC para BUS-OTHER

        mgr = OnlineOverlayManager()
        mgr.set_enabled(True)
        n = mgr.refresh(scene, cache)

        assert n == 0
        assert bus_item.online_annotation() is None

    def test_refresh_does_not_annotate_resistors(self, qapp):
        scene = QGraphicsScene()
        r_item = self._make_resistor_item("R1")
        scene.addItem(r_item)

        cache = _FakeCache()
        # mesmo se houver entrada para "R1" no cache, R não recebe ann
        cache.set_sc("R1", _FakeSC(Ik_pp_kA=10.0))

        mgr = OnlineOverlayManager()
        mgr.set_enabled(True)
        n = mgr.refresh(scene, cache)

        assert n == 0
        assert r_item.online_annotation() is None

    def test_set_enabled_false_clears_annotations(self, qapp):
        scene = QGraphicsScene()
        bus_item = self._make_bus_item("BUS-MAIN")
        scene.addItem(bus_item)

        cache = _FakeCache()
        cache.set_sc("BUS-MAIN", _FakeSC(Ik_pp_kA=12.5))

        mgr = OnlineOverlayManager()
        mgr.set_enabled(True)
        mgr.refresh(scene, cache)
        assert bus_item.online_annotation() is not None

        # Disable -> deve limpar tudo
        mgr.set_enabled(False)
        assert bus_item.online_annotation() is None

    def test_refresh_replaces_old_annotations(self, qapp):
        scene = QGraphicsScene()
        bus_item = self._make_bus_item("BUS-MAIN")
        scene.addItem(bus_item)

        cache = _FakeCache()
        cache.set_sc("BUS-MAIN", _FakeSC(Ik_pp_kA=10.0))

        mgr = OnlineOverlayManager()
        mgr.set_enabled(True)
        mgr.refresh(scene, cache)
        first_ann = bus_item.online_annotation()
        assert first_ann is not None
        assert any("10.00" in line for line in first_ann.lines)

        # Recompute SC — cache muda
        cache.set_sc("BUS-MAIN", _FakeSC(Ik_pp_kA=15.0))
        mgr.refresh(scene, cache)
        new_ann = bus_item.online_annotation()
        assert new_ann is not None
        assert any("15.00" in line for line in new_ann.lines)


# ---------------------------------------------------------------------------
# ComponentItem — annotation API + paint
# ---------------------------------------------------------------------------


class TestComponentItemOnlineApi:

    def _make_bus_item(self):
        from app.gui.schematic_pp.items import ComponentItem
        from app.preprocessor.models import PpComponent, PpProperty
        comp = PpComponent(
            type="BUS", name="BUS-MAIN", visible=True,
            x=0, y=0, label_dx=0, label_dy=0,
            mirror=0, rotation=0,
            properties=[PpProperty(value="200", visible=False)],
        )
        return ComponentItem(comp)

    def test_initial_annotation_is_none(self, qapp):
        item = self._make_bus_item()
        assert item.online_annotation() is None

    def test_set_and_get_annotation(self, qapp):
        item = self._make_bus_item()
        ann = OnlineAnnotation(lines=("Ik\" = 10 kA",), severity="ok")
        item.set_online_annotation(ann)
        got = item.online_annotation()
        assert got is ann

    def test_set_none_clears_annotation(self, qapp):
        item = self._make_bus_item()
        ann = OnlineAnnotation(lines=("X",))
        item.set_online_annotation(ann)
        assert item.online_annotation() is not None
        item.set_online_annotation(None)
        assert item.online_annotation() is None

    def test_bounding_rect_grows_with_annotation(self, qapp):
        item = self._make_bus_item()
        rect_no = item.boundingRect()
        item.set_online_annotation(
            OnlineAnnotation(lines=("Ik\" = 999.99 kA",), severity="warn"),
        )
        rect_yes = item.boundingRect()
        # Com badge ao lado direito, o right deve aumentar
        assert rect_yes.right() > rect_no.right(), (
            f"boundingRect deveria crescer para incluir o badge — "
            f"sem={rect_no.right()}, com={rect_yes.right()}"
        )

    def test_paint_with_annotation_does_not_crash(self, qapp):
        item = self._make_bus_item()
        ann = OnlineAnnotation(
            lines=("Ik\" = 12.5 kA", "ip  = 30.1 kA", "Util: 83%"),
            severity="warn",
        )
        item.set_online_annotation(ann)

        img = QImage(800, 400, QImage.Format_ARGB32)
        img.fill(Qt.white)
        p = QPainter(img)
        try:
            p.setRenderHint(QPainter.Antialiasing, True)
            p.translate(400, 200)
            opt = QStyleOptionGraphicsItem()
            item.paint(p, opt)
        finally:
            p.end()

        # Verificar que algum pixel não-branco foi pintado à direita
        # (onde o badge está)
        white = (255, 255, 255, 255)
        any_drawn_right = False
        for x in range(450, 700, 5):
            for y in range(150, 250, 5):
                pixel = img.pixelColor(x, y).getRgb()
                if pixel != white:
                    any_drawn_right = True
                    break
            if any_drawn_right:
                break
        assert any_drawn_right, (
            "Badge Online deveria ter sido desenhado à direita do símbolo"
        )

    @pytest.mark.parametrize("sev", ["info", "ok", "warn", "violation"])
    def test_paint_for_all_severities(self, sev, qapp):
        item = self._make_bus_item()
        ann = OnlineAnnotation(lines=(f"sev={sev}",), severity=sev)
        item.set_online_annotation(ann)

        img = QImage(400, 200, QImage.Format_ARGB32)
        img.fill(Qt.white)
        p = QPainter(img)
        try:
            p.translate(200, 100)
            opt = QStyleOptionGraphicsItem()
            item.paint(p, opt)
        finally:
            p.end()
        # Smoke — não crashou
