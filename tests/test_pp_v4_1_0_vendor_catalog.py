"""
tests/test_pp_v4_1_0_vendor_catalog.py — catálogo de engenharia com
dados digitalizados de datasheets oficiais (FASES 1-5):

* Trip units LSIG (``TripUnitModel``) — 10 unidades, 5 fabricantes
* Fusíveis (``FuseModel``) — I²t pré-arco/total, I1/I3
* Relés IED adicionados ao ``RELAY_MODELS_REGISTRY``
* Constantes de curva por fabricante (``vendor_curve_constants``)
* Cabos Induscabos/Nexans em ``CABLE_CATALOG``

Os testes de "cross-check" codificam as coincidências encontradas
entre fontes independentes durante a digitalização.
"""

from __future__ import annotations

import math

import pytest

from app.equipment import library
from app.equipment.library import SettingRange, VoltageClass
from app.preprocessor.cable_catalog import (
    CABLE_CATALOG, InsulationType, list_cables,
)
from app.standards import iec60255
from app.standards.relay_models import (
    RELAY_MODELS_REGISTRY, get_model, list_models, supports_function,
    validate_tms,
)
from app.standards.vendor_curve_constants import (
    ALL_VENDOR_CURVES, CurveFamily, GE_ANSI_CURVES, GE_IEC_CURVES,
    GE_IEEE_CURVES, SEL_IEC_CURVES, SEL_US_CURVES,
    ABB_REF615R_PROGRAMMABLE_DEFAULTS, find_curve, operate_time_3param_s,
)


# ---------------------------------------------------------------------------
# Stats / vendors
# ---------------------------------------------------------------------------


class TestLibraryStats:

    def test_new_categories_counted(self):
        s = library.stats()
        assert s["trip_units"] >= 10
        assert s["fuses"] >= 12
        assert s["total"] == (
            s["relays"] + s["motors"] + s["transformers"] + s["breakers"]
            + s["trip_units"] + s["fuses"]
        )

    def test_legacy_counts_preserved(self):
        s = library.stats()
        assert s["relays"] >= 15
        assert s["breakers"] >= 5

    def test_new_vendors_present(self):
        vendors = library.list_vendors()
        for v in ("Eaton", "Schneider Electric", "SIBA", "WEG", "Siemens", "ABB"):
            assert v in vendors


# ---------------------------------------------------------------------------
# Trip units
# ---------------------------------------------------------------------------


class TestTripUnits:

    def test_five_vendors_mccb_and_acb(self):
        vendors = {t.manufacturer for t in library.list_trip_units()}
        assert {"ABB", "Schneider Electric", "WEG", "Eaton", "Siemens"} <= vendors
        assert len(library.list_trip_units(category="MCCB")) >= 5
        assert len(library.list_trip_units(category="ACB")) >= 5

    def test_get_abb_ekip_touch(self):
        t = library.get_trip_unit("ABB-XT2-XT4-EKIP-TOUCH-LSIG")
        assert t is not None
        assert t.L_pickup_Ir.min == 0.4 and t.L_pickup_Ir.max == 1.0
        assert t.L_pickup_Ir.step == 0.001
        assert t.L_delay_tr.min == 3.0 and t.L_delay_tr.max == 60.0
        assert t.S_pickup_Isd.min == 0.6 and t.S_pickup_Isd.max == 10.0
        assert t.S_delay_tsd.min == 0.05 and t.S_delay_tsd.max == 0.4
        assert t.I_pickup_Ii.min == 1.5 and t.I_pickup_Ii.max == 10.0
        assert t.G_pickup_Ig.min == 0.1 and t.G_pickup_Ig.max == 1.0
        assert t.G_delay_tg.min == 0.1 and t.G_delay_tg.max == 1.0
        assert t.tr_reference_multiple == 3.0
        assert t.has_ground_fault

    def test_case_insensitive_lookup(self):
        assert library.get_trip_unit("se-mtz-micrologic-x") is not None
        assert library.get_trip_unit("NOPE-000") is None

    def test_ir_never_exceeds_1xIn(self):
        """Ir ≤ 1.0 × In em todas as unidades (IEC/UL): sobrecarga
        nunca acima da corrente nominal do disparador."""
        for t in library.list_trip_units():
            if t.L_pickup_Ir is not None:
                assert t.L_pickup_Ir.unit == "xIn"
                assert t.L_pickup_Ir.max <= 1.0, t.model_id
                assert t.L_pickup_Ir.min >= 0.4, t.model_id

    def test_setting_ranges_consistent(self):
        for t in library.list_trip_units():
            for name in ("L_pickup_Ir", "L_delay_tr", "S_pickup_Isd",
                         "S_delay_tsd", "I_pickup_Ii", "G_pickup_Ig",
                         "G_delay_tg"):
                sr = getattr(t, name)
                if sr is None:
                    continue
                assert isinstance(sr, SettingRange)
                assert sr.min <= sr.max, (t.model_id, name)
                if sr.discrete:
                    assert sr.min == min(sr.discrete)
                    assert sr.max == max(sr.discrete)
                    assert list(sr.discrete) == sorted(sr.discrete), (t.model_id, name)
                if sr.default is not None:
                    assert sr.min <= sr.default <= sr.max, (t.model_id, name)

    def test_ground_fault_filter(self):
        with_g = library.list_trip_units(ground_fault_only=True)
        assert all(t.has_ground_fault for t in with_g)
        ul_dip = library.get_trip_unit("ABB-XT5-EKIP-DIP-LSI-LSIG-UL")
        assert ul_dip not in with_g          # curva G em doc separado
        assert "G" not in ul_dip.functions_available

    def test_discrete_dial_units(self):
        xt5 = library.get_trip_unit("ABB-XT5-EKIP-DIP-LSI-LSIG-UL")
        assert xt5.adjustment_mode == "discrete_dial"
        assert xt5.L_delay_tr.discrete == (3.0, 12.0, 36.0, 48.0)
        assert xt5.S_pickup_Isd.off_selectable
        assert len(xt5.S_pickup_Isd.discrete) == 15
        weg = library.get_trip_unit("WEG-ABW-OCR-TIPO-P")
        assert weg.I_pickup_Ii.discrete == (2.0, 3.0, 4.0, 6.0, 8.0, 10.0, 12.0, 15.0)
        assert weg.S_delay_tsd.unit == "s"    # erro tipográfico da fonte corrigido

    def test_micrologic_x_isd_in_xIr(self):
        mtz = library.get_trip_unit("SE-MTZ-MICROLOGIC-X")
        assert mtz.S_pickup_Isd.unit == "xIr"
        assert mtz.S_pickup_Isd.min == 1.5 and mtz.S_pickup_Isd.max == 10.0
        assert mtz.I_pickup_Ii.min == 2.0 and mtz.I_pickup_Ii.max == 15.0

    def test_eaton_pxr25_table4(self):
        p = library.get_trip_unit("EATON-NZM-PXR25")
        assert p.L_delay_tr.min == 2.0 and p.L_delay_tr.max == 20.0
        assert p.S_pickup_Isd.min == 2.0 and p.S_pickup_Isd.max == 10.0
        assert p.I_pickup_Ii.min == 2.0 and p.I_pickup_Ii.max == 18.0
        assert p.S_delay_tsd.max == 1.0 and p.S_delay_tsd.step == 0.01
        assert p.G_delay_tg.max == 1.0

    def test_siemens_3wl_ig_in_amperes(self):
        s = library.get_trip_unit("SIEMENS-3WL1-ETU45B")
        assert s.G_pickup_Ig.unit == "A"
        assert s.G_pickup_Ig.discrete == (100.0, 300.0, 600.0, 900.0, 1200.0)
        assert s.L_delay_tr.discrete[-1] == 30.0

    def test_all_have_source_doc(self):
        for t in library.list_trip_units():
            assert t.source_doc
            assert t.category in ("MCCB", "ACB")
            assert t.adjustment_mode in ("discrete_dial", "fine_digital")


# ---------------------------------------------------------------------------
# Fuses
# ---------------------------------------------------------------------------


class TestFuses:

    def test_families_present(self):
        ids = {f.model_id for f in library.list_fuses()}
        for expected in (
            "BUSSMANN-NH000-GG-500V", "BUSSMANN-NH-AM-500-690V",
            "BUSSMANN-12KV-DIN-MV", "SIBA-HHM-12KV", "ABB-CMF-12KV",
            "ABB-CEF-12KV", "WEG-AR-NH-CONTATO-FACA-100KA",
        ):
            assert expected in ids

    def test_i2t_total_not_below_prearcing(self):
        """Energia total de interrupção ≥ energia mínima de fusão."""
        for f in library.list_fuses():
            for r in f.ratings:
                if r.i2t_prearcing_A2s > 0 and r.i2t_total_A2s > 0:
                    assert r.i2t_total_A2s >= r.i2t_prearcing_A2s, (
                        f.model_id, r.part_number
                    )

    def test_bussmann_gg_size000_values(self):
        f = library.get_fuse("BUSSMANN-NH000-GG-500V")
        assert f.breaking_capacity_kA == 120.0
        r = f.get_rating(100)
        assert r.i2t_prearcing_A2s == 18100 and r.i2t_total_A2s == 72300
        assert f.current_range_A == (2.0, 100.0)
        assert len(f.ratings) == 14

    def test_bussmann_am_anomaly_preserved(self):
        """25 A (3500) > 32 A (2200) no pré-arco — impresso assim na
        fonte; não deve ter sido 'corrigido' na transcrição."""
        f = library.get_fuse("BUSSMANN-NH-AM-500-690V")
        r25 = [r for r in f.ratings if r.part_number == "25NHM000B"][0]
        r32 = [r for r in f.ratings if r.part_number == "32NHM000B"][0]
        assert r25.i2t_prearcing_A2s == 3500 and r32.i2t_prearcing_A2s == 2200

    def test_mv_fuses_have_i3_and_voltage_class(self):
        for mid in ("BUSSMANN-12KV-DIN-MV", "SIBA-HHM-12KV", "SIBA-HHM-3.6KV",
                    "ABB-CMF-12KV", "ABB-CEF-12KV"):
            f = library.get_fuse(mid)
            assert f.voltage_class == VoltageClass.MV
            assert all(r.min_breaking_current_I3_A > 0 for r in f.ratings), mid
            currents = [r.min_breaking_current_I3_A for r in f.ratings]
            # I3 cresce com In dentro de cada referência de corpo
            assert currents[-1] > currents[0]

    def test_bussmann_12kv_per_rating_breaking_capacity(self):
        f = library.get_fuse("BUSSMANN-12KV-DIN-MV")
        by_pn = {r.part_number: r for r in f.ratings}
        assert by_pn["12AILSJ100"].breaking_capacity_kA == 31.5
        assert by_pn["12TFMSJ160"].breaking_capacity_kA == 50.0
        assert by_pn["12TDLEJ6.3"].breaking_capacity_kA == 63.0
        assert len(f.ratings) == 17

    def test_siba_same_element_across_voltages(self):
        """Mesma corrente → mesmo I3 e mesmo I²t de pré-arco em 3.6 e
        12 kV (mesmo elemento, corpo mais longo); I²t total maior em 12 kV."""
        s36 = library.get_fuse("SIBA-HHM-3.6KV").get_rating(50)
        s12 = library.get_fuse("SIBA-HHM-12KV").get_rating(50)
        assert s36.min_breaking_current_I3_A == s12.min_breaking_current_I3_A == 140
        assert s36.i2t_prearcing_A2s == s12.i2t_prearcing_A2s == 3400
        assert s12.i2t_total_A2s > s36.i2t_total_A2s

    def test_weg_ar_full_tables(self):
        blade = library.get_fuse("WEG-AR-NH-CONTATO-FACA-100KA")
        flush = library.get_fuse("WEG-AR-NH-FLUSH-END-200KA")
        # Catálogo WEG: 12 FNH00 + 10 FNH1 + 8 FNH2 + 8 FNH3 = 38 linhas.
        assert len(blade.ratings) == 38
        assert len(flush.ratings) == 17
        assert blade.current_range_A == (20.0, 1000.0)
        assert flush.current_range_A == (450.0, 2000.0)
        assert flush.breaking_capacity_kA == 200.0

    def test_filters(self):
        assert all(f.fuse_class == "aM" for f in library.list_fuses(fuse_class="aM"))
        assert all(f.manufacturer == "SIBA" for f in library.list_fuses(vendor="siba"))
        mv12 = library.list_fuses(rated_voltage_kV=12.0)
        assert {f.model_id for f in mv12} >= {"SIBA-HHM-12KV", "ABB-CMF-12KV",
                                               "ABB-CEF-12KV", "BUSSMANN-12KV-DIN-MV"}
        assert library.get_fuse("nope") is None


# ---------------------------------------------------------------------------
# Relay registry (FASE 2)
# ---------------------------------------------------------------------------


class TestRelayRegistryAdditions:

    def test_legacy_keys_untouched(self):
        for k in ("SEL-751", "ABB-REF615", "ABB-RET615",
                  "Schneider-P3U30", "Schneider-P3U10"):
            assert k in RELAY_MODELS_REGISTRY

    def test_new_models_registered(self):
        ids = list_models()
        for k in ("ABB-REF615R", "Siemens-7SJ82", "GE-850",
                  "Schneider-MiCOM-P127", "WEG-SRW01"):
            assert k in ids

    def test_ref615r_ranges(self):
        m = get_model("ABB-REF615R")
        assert m.pickup_range_per_in == (0.05, 5.0)
        assert m.tms_range == (0.05, 15.0)
        assert validate_tms(m, 15.0) and not validate_tms(m, 15.01)
        assert supports_function(m, "51P") and supports_function(m, "50N-3")

    def test_tms_ceiling_convergence_abb_siemens(self):
        """Teto 15.00 idêntico em ABB REF615R e Siemens 7SJ82 (fontes
        independentes)."""
        assert get_model("ABB-REF615R").tms_range[1] == 15.0
        assert get_model("Siemens-7SJ82").tms_range[1] == 15.0

    def test_micom_tms_scale_differs(self):
        m = get_model("Schneider-MiCOM-P127")
        assert m.tms_range == (0.025, 1.5)
        assert m.pickup_range_per_in == (0.1, 25.0)

    def test_ge_850_tdm_range(self):
        m = get_model("GE-850")
        assert m.time_dial_range == (0.05, 600.0)
        assert m.pickup_range_per_in == (0.05, 30.0)

    def test_weg_srw01_is_motor_relay_without_idmt(self):
        m = get_model("WEG-SRW01")
        assert m.application == "motor"
        assert supports_function(m, "49")
        assert iec60255.CurveStandard.IEC not in m.tc_curve_standards


# ---------------------------------------------------------------------------
# Vendor curve constants — cross-checks entre fontes independentes
# ---------------------------------------------------------------------------


class TestVendorCurveConstants:

    def test_iec_operate_constants_universal(self):
        """k/α da curva de OPERAÇÃO IEC coincidem em SEL, GE e iec60255."""
        sel = {c.code: c for c in SEL_IEC_CURVES}
        ge = {c.code: c for c in GE_IEC_CURVES}
        pairs = [
            ("C1", "IEC-A", iec60255.IecCurveType.STANDARD_INVERSE),
            ("C2", "IEC-B", iec60255.IecCurveType.VERY_INVERSE),
            ("C3", "IEC-C", iec60255.IecCurveType.EXTREMELY_INVERSE),
        ]
        for s, g, t in pairs:
            ref = iec60255.IEC_CURVE_COEFFICIENTS[t]
            assert sel[s].a == ge[g].a == ref.k
            assert sel[s].p == ge[g].p == ref.alpha

    def test_iec_reset_constants_are_vendor_specific(self):
        """A norma padroniza operação, não reset: SEL ≠ GE."""
        sel = {c.code: c for c in SEL_IEC_CURVES}
        ge = {c.code: c for c in GE_IEC_CURVES}
        assert sel["C1"].reset_tr == 13.5 and ge["IEC-A"].reset_tr == 9.7
        assert sel["C3"].reset_tr == 80.0 and ge["IEC-C"].reset_tr == 58.2

    def test_ieee_annex_a_triple_confirmation(self):
        """GE Tab. 4-34 == defaults programáveis ABB == iec60255 (EI)."""
        ge_ei = find_curve(vendor="GE", code="IEEE-EI")[0]
        abb = ABB_REF615R_PROGRAMMABLE_DEFAULTS
        ref = iec60255.IEEE_CURVE_COEFFICIENTS[iec60255.IeeeCurveType.EXTREMELY_INVERSE]
        assert ge_ei.a == abb.a == ref.k == 28.2
        assert ge_ei.b == abb.b == ref.beta == 0.1217
        assert ge_ei.p == abb.p == ref.alpha == 2.0
        assert ge_ei.reset_tr == abb.reset_tr == 29.1

    def test_us_legacy_family_sel_equals_ge_by_reset(self):
        """SEL U1-U4 e GE ANSI descrevem a mesma curva física: ``tr``
        coincide exatamente entre os dois fabricantes."""
        sel = {c.curve_name: c for c in SEL_US_CURVES}
        ge = {c.curve_name.replace("ANSI ", ""): c for c in GE_ANSI_CURVES}
        assert sel["Extremely Inverse"].reset_tr == ge["Extremely Inverse"].reset_tr == 5.67
        assert sel["Very Inverse"].reset_tr == ge["Very Inverse"].reset_tr == 3.88
        assert sel["Inverse"].reset_tr == ge["Normally Inverse"].reset_tr == 5.95
        assert sel["Moderately Inverse"].reset_tr == ge["Moderately Inverse"].reset_tr == 1.08

    def test_two_families_are_numerically_distinct(self):
        """'Extremely Inverse' do Anexo A ≠ 'Extremely Inverse' legada."""
        annex = find_curve(vendor="GE", code="IEEE-EI")[0]
        legacy = find_curve(vendor="SEL", code="U4")[0]
        assert annex.family == CurveFamily.IEEE_C37112_ANNEX_A
        assert legacy.family == CurveFamily.US_LEGACY_CO
        assert annex.a != legacy.a and annex.b != legacy.b

    def test_iec60255_generic_ieee_table_is_mixed(self):
        """Documenta o estado pré-existente: a linha CO8 da tabela
        genérica carrega constantes da família legada (SEL U2)."""
        co8 = iec60255.IEEE_CURVE_COEFFICIENTS[iec60255.IeeeCurveType.INVERSE]
        u2 = find_curve(vendor="SEL", code="U2")[0]
        assert co8.k == u2.a == 5.95
        assert math.isclose(co8.beta, u2.b, rel_tol=1e-9)

    def test_operate_time_3param_sanity(self):
        c3 = find_curve(vendor="SEL", code="C3")[0]
        # IEC EI, TMS=1, M=2 → 80/(4-1) = 26.667 s
        assert math.isclose(operate_time_3param_s(200, 100, 1.0, c3), 80 / 3, rel_tol=1e-9)
        assert operate_time_3param_s(100, 100, 1.0, c3) == float("inf")
        ge_5p = find_curve(vendor="GE", code="ANSI-EI")[0]
        with pytest.raises(ValueError):
            operate_time_3param_s(200, 100, 1.0, ge_5p)

    def test_registry_integrity(self):
        assert len(ALL_VENDOR_CURVES) == 5 + 5 + 3 + 4 + 4 + 4 + 1
        assert all(c.source for c in ALL_VENDOR_CURVES)
        assert len(GE_IEEE_CURVES) == 3


# ---------------------------------------------------------------------------
# Cable catalog additions
# ---------------------------------------------------------------------------


class TestCableCatalogAdditions:

    def test_legacy_entries_preserved(self):
        assert len(CABLE_CATALOG) >= 19 + 14 + 14
        legacy = [c for c in CABLE_CATALOG if not c.manufacturer]
        assert len(legacy) >= 19

    def test_induscabos_entries(self):
        ind = [c for c in CABLE_CATALOG if c.manufacturer == "Induscabos"]
        assert len(ind) == 14
        c240 = [c for c in ind if c.cross_section_mm2 == 240][0]
        assert c240.R_dc_ohm_per_km_at_20C == 0.0754
        assert c240.R_ac_ohm_per_km_at_90C == 0.09923
        assert c240.X_ohm_per_km == 0.10970
        assert c240.C_uF_per_km == 0.5902
        assert c240.ampacity_air_A == 602 and c240.ampacity_buried_A == 358
        assert c240.rated_voltage_kV == 6.0
        assert c240.source

    def test_induscabos_physics(self):
        """Rca(90) > Rcc(20); X trifólio < X S=D (em notes); ampacidade
        ao ar > enterrado; tudo monotônico em S."""
        ind = sorted(
            (c for c in CABLE_CATALOG if c.manufacturer == "Induscabos"),
            key=lambda c: c.cross_section_mm2,
        )
        for prev, cur in zip(ind, ind[1:]):
            assert cur.R_dc_ohm_per_km_at_20C < prev.R_dc_ohm_per_km_at_20C
            assert cur.X_ohm_per_km < prev.X_ohm_per_km
            assert cur.ampacity_air_A > prev.ampacity_air_A
        for c in ind:
            assert c.R_ac_ohm_per_km_at_90C > c.R_dc_ohm_per_km_at_20C
            assert c.ampacity_air_A > c.ampacity_buried_A

    def test_nexans_entries(self):
        nx = [c for c in CABLE_CATALOG if c.manufacturer == "Nexans"]
        assert len(nx) == 14
        c630 = [c for c in nx if c.cross_section_mm2 == 630][0]
        assert c630.R_ac_ohm_per_km_at_90C == 0.0416
        assert c630.X_ohm_per_km == 0.087
        assert c630.ampacity_air_A == 1122
        assert c630.rated_voltage_kV == 11.0
        assert "IEC 60228" in c630.notes

    def test_common_sections_share_iec60228_rdc(self):
        """R_dc 20 °C das seções comuns coincide entre Induscabos (fonte)
        e Nexans (IEC 60228 cl. 2 nominal)."""
        ind = {c.cross_section_mm2: c for c in CABLE_CATALOG if c.manufacturer == "Induscabos"}
        nx = {c.cross_section_mm2: c for c in CABLE_CATALOG if c.manufacturer == "Nexans"}
        for s in (16, 25, 50, 95, 120, 240, 500):
            assert ind[s].R_dc_ohm_per_km_at_20C == nx[s].R_dc_ohm_per_km_at_20C

    def test_list_cables_filters_new_voltage_classes(self):
        assert len(list_cables(rated_voltage_kV=6.0, insulation=InsulationType.XLPE)) >= 14
        assert len(list_cables(rated_voltage_kV=11.0, insulation=InsulationType.XLPE)) >= 14
