"""
tests/test_pp_v0_94_0_modular_studies.py — v0.94.0:

Estudos modulares estilo PTW Power*Tools.

Cobertura:

* StudyCache — get/set/invalidate por estudo + bus
* PrerequisiteError quando strict mode + cache vazio
* short_circuit.run — standalone
* coordination.run — auto-roda SC quando cache vazio
* arc_flash_study.run — auto-roda SC + Coord
* arc_flash_study.run com bus HV → status="out_of_scope"
* Cache invalidation: setting SC invalida coord + arc_flash
* Hash invalidation: mudança no projeto invalida automaticamente
* Cache hit retorna o mesmo objeto (instantâneo)
"""

from __future__ import annotations

import pytest

from app.preprocessor.qucs_sch_parser import parse_sch_file
from app.postprocessor.studies import (
    PrerequisiteError, StudyCache,
    arc_flash_study, coordination, short_circuit,
)


@pytest.fixture
def project_lv():
    """nbr17227_example.sch — SWGR_138 (13.8 kV) em escopo."""
    return parse_sch_file(
        "app/examples/schematics/nbr17227_example.sch",
    )


@pytest.fixture
def project_hv():
    """iec60909_annex_c.sch — BUS_HV (110 kV) e BUS_LV (20 kV)
    fora do escopo arc-flash."""
    return parse_sch_file(
        "app/examples/schematics/iec60909_annex_c.sch",
    )


# ---------------------------------------------------------------------------
# StudyCache mechanics
# ---------------------------------------------------------------------------


class TestStudyCache:

    def test_empty_cache(self):
        c = StudyCache()
        assert not c.has_sc("BUS-1")
        assert not c.has_coord("BUS-1")
        assert not c.has_arc_flash("BUS-1")
        assert c.get_sc("BUS-1") is None

    def test_set_and_get_sc(self):
        c = StudyCache()
        c.set_sc("BUS-1", "fake_result", input_hash="abc")
        assert c.has_sc("BUS-1")
        assert c.get_sc("BUS-1") == "fake_result"

    def test_set_sc_invalidates_derived(self):
        """Mudar SC invalida coord + arc_flash do mesmo bus."""
        c = StudyCache()
        c.set_sc("BUS-1", "sc1", "h1")
        c.set_coord("BUS-1", "coord1", "h2")
        c.set_arc_flash("BUS-1", "af1", "h3")
        assert c.has_coord("BUS-1") and c.has_arc_flash("BUS-1")
        # Re-set SC → invalida derivados
        c.set_sc("BUS-1", "sc2", "h1b")
        assert c.has_sc("BUS-1")
        assert not c.has_coord("BUS-1")
        assert not c.has_arc_flash("BUS-1")

    def test_set_coord_invalidates_arc_flash(self):
        c = StudyCache()
        c.set_sc("BUS-1", "sc1", "h1")
        c.set_coord("BUS-1", "coord1", "h2")
        c.set_arc_flash("BUS-1", "af1", "h3")
        # Re-set Coord → invalida arc_flash, mantém SC
        c.set_coord("BUS-1", "coord2", "h2b")
        assert c.has_sc("BUS-1")
        assert c.has_coord("BUS-1")
        assert not c.has_arc_flash("BUS-1")

    def test_hash_invalidation(self):
        """get_sc_if_valid retorna None se hash mudou."""
        c = StudyCache()
        c.set_sc("BUS-1", "sc1", input_hash="abc")
        assert c.get_sc_if_valid("BUS-1", "abc") == "sc1"
        assert c.get_sc_if_valid("BUS-1", "different") is None

    def test_invalidate_bus(self):
        c = StudyCache()
        c.set_sc("BUS-1", "sc1", "h1")
        c.set_sc("BUS-2", "sc2", "h2")
        c.invalidate_bus("BUS-1")
        assert not c.has_sc("BUS-1")
        assert c.has_sc("BUS-2")  # outros buses preservados

    def test_invalidate_all(self):
        c = StudyCache()
        c.set_sc("BUS-1", "sc1", "h1")
        c.set_coord("BUS-2", "coord", "h2")
        c.set_arc_flash("BUS-3", "af", "h3")
        c.invalidate_all()
        assert not c.has_sc("BUS-1")
        assert not c.has_coord("BUS-2")
        assert not c.has_arc_flash("BUS-3")

    def test_status_summary(self):
        c = StudyCache()
        s = c.status_summary("BUS-1")
        assert s == {"sc": "—", "coord": "—", "arc_flash": "—"}
        c.set_sc("BUS-1", "x", "h")
        s = c.status_summary("BUS-1")
        assert s["sc"] == "✅"
        assert s["coord"] == "—"


# ---------------------------------------------------------------------------
# Short-circuit standalone
# ---------------------------------------------------------------------------


class TestShortCircuitModular:

    def test_sc_standalone_no_cache(self, project_lv):
        """SC roda sem cache e retorna resultado válido."""
        r = short_circuit.run(project_lv, "SWGR_138")
        # bus_id é a propriedade BUS (não o nome do componente);
        # nbr17227_example usa "SWGR-13.8" como bus_id property.
        assert "SWGR" in r.bus_id
        assert r.Ik_pp_kA > 0
        assert r.kappa > 0
        assert r.n_sc_sources >= 1

    def test_sc_with_cache(self, project_lv):
        """SC com cache: 2a chamada retorna o mesmo objeto."""
        cache = StudyCache()
        r1 = short_circuit.run(project_lv, "SWGR_138", cache=cache)
        r2 = short_circuit.run(project_lv, "SWGR_138", cache=cache)
        assert r1 is r2  # mesmo objeto (cache hit)
        assert cache.has_sc("SWGR_138")

    def test_sc_cache_invalidates_on_project_change(self, project_lv):
        """v0.94.0: alterar projeto invalida cache via hash."""
        from app.preprocessor.models import PpComponent
        cache = StudyCache()
        r1 = short_circuit.run(project_lv, "SWGR_138", cache=cache)
        # Modify project
        project_lv.components.append(PpComponent(
            type="R", name="R_NEW", visible=True,
            x=999, y=999, label_dx=0, label_dy=0,
            mirror=0, rotation=0, properties=[],
        ))
        r2 = short_circuit.run(project_lv, "SWGR_138", cache=cache)
        assert r1 is not r2  # objeto novo (hash invalidou)


# ---------------------------------------------------------------------------
# Coordination (REQUIRES SC)
# ---------------------------------------------------------------------------


class TestCoordinationModular:

    def test_coord_auto_runs_sc(self, project_lv):
        """Coord auto-roda SC quando cache vazio."""
        cache = StudyCache()
        coord = coordination.run(project_lv, "SWGR_138", cache=cache)
        # SC foi auto-rodado
        assert cache.has_sc("SWGR_138")
        assert cache.has_coord("SWGR_138")
        assert coord.sc_input_Ik_pp_kA > 0

    def test_coord_strict_mode_no_sc(self, project_lv):
        """Strict mode: PrerequisiteError quando SC ausente."""
        cache = StudyCache()
        with pytest.raises(PrerequisiteError) as exc_info:
            coordination.run(
                project_lv, "SWGR_138", cache=cache,
                auto_run_prereqs=False,
            )
        assert "short_circuit" in exc_info.value.missing
        assert exc_info.value.bus_id == "SWGR_138"

    def test_coord_uses_cached_sc(self, project_lv):
        """Coord não roda SC se já existe no cache."""
        cache = StudyCache()
        sc1 = short_circuit.run(project_lv, "SWGR_138", cache=cache)
        coord = coordination.run(project_lv, "SWGR_138", cache=cache)
        # SC do coord deve coincidir com o cacheado
        assert coord.sc_input_Ik_pp_kA == sc1.Ik_pp_kA


# ---------------------------------------------------------------------------
# Arc-flash (REQUIRES SC + Coord)
# ---------------------------------------------------------------------------


class TestArcFlashModular:

    def test_arc_flash_auto_runs_prereqs(self, project_lv):
        """Arc-flash auto-roda SC + Coord quando cache vazio."""
        cache = StudyCache()
        af = arc_flash_study.run(project_lv, "SWGR_138", cache=cache)
        assert cache.has_sc("SWGR_138")
        assert cache.has_coord("SWGR_138")
        assert cache.has_arc_flash("SWGR_138")
        assert af.status == "computed"
        assert af.incident_energy_cal_cm2 > 0
        assert af.ppe_category in ("0", "1", "2", "3", "4", "DANGER")

    def test_arc_flash_strict_mode(self, project_lv):
        """Strict mode: PrerequisiteError quando SC + Coord ausentes."""
        cache = StudyCache()
        with pytest.raises(PrerequisiteError) as exc_info:
            arc_flash_study.run(
                project_lv, "SWGR_138", cache=cache,
                auto_run_prereqs=False,
            )
        assert "short_circuit" in exc_info.value.missing
        assert "coordination" in exc_info.value.missing

    def test_arc_flash_strict_with_only_sc(self, project_lv):
        """Strict mode: ainda raises se Coord falta (mas SC tem)."""
        cache = StudyCache()
        short_circuit.run(project_lv, "SWGR_138", cache=cache)
        with pytest.raises(PrerequisiteError) as exc_info:
            arc_flash_study.run(
                project_lv, "SWGR_138", cache=cache,
                auto_run_prereqs=False,
            )
        assert "coordination" in exc_info.value.missing
        assert "short_circuit" not in exc_info.value.missing

    def test_arc_flash_out_of_scope_HV(self, project_hv):
        """v0.94.0: bus HV (>15 kV) → status='out_of_scope'.
        Não levanta exceção; SC + Coord são válidos."""
        cache = StudyCache()
        af = arc_flash_study.run(project_hv, "BUS_HV", cache=cache)
        assert af.status == "out_of_scope"
        assert af.incident_energy_cal_cm2 == 0
        assert af.ppe_category == "N/A"
        assert "fora do escopo" in af.out_of_scope_reason
        # SC e Coord foram cacheados normalmente
        assert cache.has_sc("BUS_HV")
        assert cache.has_coord("BUS_HV")


# ---------------------------------------------------------------------------
# Modular chain integration
# ---------------------------------------------------------------------------


class TestModularChain:

    def test_full_chain_sc_coord_af(self, project_lv):
        """Cadeia completa: SC → Coord → Arc-flash. Cada passo
        usa o cache do anterior."""
        cache = StudyCache()
        # Step 1
        sc = short_circuit.run(project_lv, "SWGR_138", cache=cache)
        assert sc.Ik_pp_kA > 0
        # Step 2 (deve usar SC do cache)
        coord = coordination.run(project_lv, "SWGR_138", cache=cache)
        assert coord.sc_input_Ik_pp_kA == sc.Ik_pp_kA
        # Step 3 (deve usar SC + Coord do cache)
        af = arc_flash_study.run(project_lv, "SWGR_138", cache=cache)
        assert af.sc_input_Ibf_kA == sc.Ik_pp_kA
        # Status final
        s = cache.status_summary("SWGR_138")
        assert s == {"sc": "✅", "coord": "✅", "arc_flash": "✅"}

    def test_chain_idempotent(self, project_lv):
        """Re-rodar o mesmo estudo retorna mesmo objeto."""
        cache = StudyCache()
        sc1 = short_circuit.run(project_lv, "SWGR_138", cache=cache)
        coord1 = coordination.run(project_lv, "SWGR_138", cache=cache)
        af1 = arc_flash_study.run(project_lv, "SWGR_138", cache=cache)
        # 2nd round
        sc2 = short_circuit.run(project_lv, "SWGR_138", cache=cache)
        coord2 = coordination.run(project_lv, "SWGR_138", cache=cache)
        af2 = arc_flash_study.run(project_lv, "SWGR_138", cache=cache)
        assert sc1 is sc2
        assert coord1 is coord2
        assert af1 is af2
