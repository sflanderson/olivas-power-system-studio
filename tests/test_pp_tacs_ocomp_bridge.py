"""
tests/test_pp_tacs_ocomp_bridge.py — v0.26.5: bridge integration
para .ocomp specs PID, Integrator, LowPass, Limiter, TSum.

Cobre:

* PID.ocomp → TacsTransferFunction via make_pid; coeficientes
  na ordem (Ki, Kp, Kd); saturação opcional; props mal-formadas
  geram warning.
* Integrator.ocomp → make_integrator; valor inicial; saturação.
* LowPass.ocomp → make_low_pass; tau<=0 rejeitado.
* Limiter.ocomp → TacsLimiter direto; min>=max rejeitado.
* TSum.ocomp → TacsSum com até 4 pares (signal, weight) +
  bias; entradas vazias filtradas.
* ``_extract_tacs_blocks`` retorna lista mista (TacsBlock,
  TacsTransferFunction, TacsLimiter, TacsSum) e warnings.
* ``to_atp`` integra tudo: cada .ocomp vira cartão na seção
  /TACS HYBRID corretamente.
"""

from __future__ import annotations

import pytest

from app.preprocessor.bridge_to_atp import _extract_tacs_blocks, to_atp
from app.preprocessor.models import PpComponent, PpProject, PpProperty
from app.preprocessor.tacs_blocks import TacsLimiter, TacsSum
from app.preprocessor.tacs_tf import TacsTransferFunction


def _mk(comp_type: str, name: str, props: list[str]) -> PpComponent:
    return PpComponent(
        type=comp_type, name=name, visible=True,
        x=0, y=0, label_dx=0, label_dy=0, mirror=0, rotation=0,
        properties=[PpProperty(p) for p in props],
    )


# ---------------------------------------------------------------------------
# PID.ocomp
# ---------------------------------------------------------------------------


class TestPidBridge:
    def test_extracts_tf(self):
        comp = _mk("PID", "pid1", [
            "err",   # 0: input_signal
            "upid",  # 1: output_name
            "5.0",   # 2: Kp
            "20.0",  # 3: Ki
            "0.001", # 4: Kd
            "-1.0",  # 5: output_min
            "1.0",   # 6: output_max
            "0.0",   # 7: initial_output
        ])
        items, warns = _extract_tacs_blocks(PpProject(components=[comp]))
        assert len(items) == 1
        tf = items[0]
        assert isinstance(tf, TacsTransferFunction)
        # numerator order: (Ki, Kp, Kd) = (20, 5, 0.001)
        assert tf.numerator == (20.0, 5.0, 0.001)
        assert tf.output_min == -1.0
        assert tf.output_max == 1.0

    def test_p_only_pid(self):
        """Ki=0, Kd=0 → P-only."""
        comp = _mk("PID", "p1", [
            "u", "y", "3.0", "0", "0", "", "", "0",
        ])
        items, _ = _extract_tacs_blocks(PpProject(components=[comp]))
        tf = items[0]
        assert tf.numerator == (0.0, 3.0, 0.0)

    def test_no_saturation(self):
        comp = _mk("PID", "p", [
            "err", "u", "1", "0", "0", "", "", "0",
        ])
        items, _ = _extract_tacs_blocks(PpProject(components=[comp]))
        tf = items[0]
        assert tf.output_min is None
        assert tf.output_max is None

    def test_long_name_truncated(self):
        comp = _mk("PID", "controller_pid", [
            "err", "out", "1", "0", "0", "", "", "0",
        ])
        items, _ = _extract_tacs_blocks(PpProject(components=[comp]))
        tf = items[0]
        assert len(tf.name) <= 6

    def test_invalid_kp_warned(self):
        comp = _mk("PID", "p", [
            "err", "u", "abc", "0", "0", "", "", "0",
        ])
        items, warns = _extract_tacs_blocks(PpProject(components=[comp]))
        assert items == []
        assert any("Kp" in w for w in warns)

    def test_to_atp_emits_pid(self):
        comp = _mk("PID", "p1", [
            "err", "u", "1.0", "10.0", "0.01", "", "", "0",
        ])
        atp = to_atp(PpProject(components=[comp]))
        text = "\n".join(atp.raw_lines)
        assert "/TACS HYBRID" in text
        assert "1u" in text  # cartão type-1 com output


# ---------------------------------------------------------------------------
# Integrator.ocomp
# ---------------------------------------------------------------------------


class TestIntegratorBridge:
    def test_extracts(self):
        comp = _mk("Integrator", "i1", [
            "u",   # input_signal
            "y",   # output_name
            "10",  # K
            "0",   # initial_output
            "",    # output_min
            "",    # output_max
        ])
        items, warns = _extract_tacs_blocks(PpProject(components=[comp]))
        assert len(items) == 1
        assert warns == []
        tf = items[0]
        assert tf.gain == 10.0
        # K/s ⇒ N=(1,), D=(0, 1)
        assert tf.numerator == (1.0,)
        assert tf.denominator == (0.0, 1.0)

    def test_with_initial(self):
        comp = _mk("Integrator", "i1", [
            "u", "y", "1", "3.5", "", "",
        ])
        items, _ = _extract_tacs_blocks(PpProject(components=[comp]))
        assert items[0].initial_output == 3.5

    def test_with_saturation(self):
        comp = _mk("Integrator", "i1", [
            "u", "y", "1", "0", "-100", "100",
        ])
        items, _ = _extract_tacs_blocks(PpProject(components=[comp]))
        tf = items[0]
        assert tf.output_min == -100.0
        assert tf.output_max == 100.0


# ---------------------------------------------------------------------------
# LowPass.ocomp
# ---------------------------------------------------------------------------


class TestLowPassBridge:
    def test_extracts(self):
        comp = _mk("LowPass", "lp1", [
            "u", "y", "1.0", "0.001",
        ])
        items, warns = _extract_tacs_blocks(PpProject(components=[comp]))
        assert len(items) == 1
        assert warns == []
        tf = items[0]
        assert tf.numerator == (1.0,)
        assert tf.denominator == (1.0, 0.001)

    def test_zero_tau_rejected(self):
        comp = _mk("LowPass", "lp", [
            "u", "y", "1.0", "0",
        ])
        items, warns = _extract_tacs_blocks(PpProject(components=[comp]))
        assert items == []
        assert any("tau" in w for w in warns)

    def test_negative_tau_rejected(self):
        comp = _mk("LowPass", "lp", [
            "u", "y", "1.0", "-0.001",
        ])
        items, warns = _extract_tacs_blocks(PpProject(components=[comp]))
        assert items == []


# ---------------------------------------------------------------------------
# Limiter.ocomp
# ---------------------------------------------------------------------------


class TestLimiterBridge:
    def test_extracts(self):
        comp = _mk("Limiter", "lim", [
            "u", "y", "-1.0", "1.0",
        ])
        items, warns = _extract_tacs_blocks(PpProject(components=[comp]))
        assert len(items) == 1
        assert warns == []
        lim = items[0]
        assert isinstance(lim, TacsLimiter)
        assert lim.output_min == -1.0
        assert lim.output_max == 1.0

    def test_min_ge_max_rejected(self):
        comp = _mk("Limiter", "lim", [
            "u", "y", "1.0", "-1.0",
        ])
        items, warns = _extract_tacs_blocks(PpProject(components=[comp]))
        assert items == []
        assert any("output_min" in w for w in warns)

    def test_to_atp_emits_card_54(self):
        comp = _mk("Limiter", "lim", [
            "u", "y", "-2.0", "2.0",
        ])
        atp = to_atp(PpProject(components=[comp]))
        text = "\n".join(atp.raw_lines)
        assert "54" in text


# ---------------------------------------------------------------------------
# TSum.ocomp
# ---------------------------------------------------------------------------


class TestTSumBridge:
    def test_subtractor(self):
        """TSum como err = ref - meas."""
        comp = _mk("TSum", "esub", [
            "err",  # 0: output_name
            "ref",  # 1: input1_name
            "1.0",  # 2: input1_weight
            "meas", # 3: input2_name
            "-1.0", # 4: input2_weight
            "",     # 5: input3_name (vazio, ignorado)
            "0",    # 6: input3_weight (ignorado)
            "",     # 7: input4_name
            "0",    # 8: input4_weight
            "0",    # 9: bias
        ])
        items, warns = _extract_tacs_blocks(PpProject(components=[comp]))
        assert len(items) == 1
        assert warns == []
        s = items[0]
        assert isinstance(s, TacsSum)
        assert s.inputs == (("ref", 1.0), ("meas", -1.0))
        assert s.bias == 0.0

    def test_three_inputs(self):
        comp = _mk("TSum", "s", [
            "y", "x1", "1", "x2", "0.5", "x3", "0.25",
            "", "0", "0",
        ])
        items, _ = _extract_tacs_blocks(PpProject(components=[comp]))
        assert len(items[0].inputs) == 3

    def test_with_bias(self):
        comp = _mk("TSum", "s", [
            "y", "x1", "1", "", "0", "", "0", "", "0", "10",
        ])
        items, _ = _extract_tacs_blocks(PpProject(components=[comp]))
        assert items[0].bias == 10.0

    def test_no_inputs_rejected(self):
        comp = _mk("TSum", "s", [
            "y", "", "1", "", "0", "", "0", "", "0", "0",
        ])
        items, warns = _extract_tacs_blocks(PpProject(components=[comp]))
        assert items == []
        assert any("sem inputs" in w for w in warns)


# ---------------------------------------------------------------------------
# Mixed pipeline via to_atp
# ---------------------------------------------------------------------------


class TestMixedPipeline:
    def test_full_pid_loop(self):
        """TSum subtractor → PID → Limiter → LowPass — 4 cartões."""
        comps = [
            _mk("TSum", "es", [
                "err", "ref", "1", "meas", "-1",
                "", "0", "", "0", "0",
            ]),
            _mk("PID", "pid1", [
                "err", "upid", "5", "20", "0.001", "-1", "1", "0",
            ]),
            _mk("Limiter", "lim", [
                "upid", "ulim", "-0.9", "0.9",
            ]),
            _mk("LowPass", "lp", [
                "ulim", "uf", "1", "0.0001",
            ]),
        ]
        atp = to_atp(PpProject(components=comps))
        text = "\n".join(atp.raw_lines)
        # Cada device aparece pelo menos 1×
        assert "98err" in text          # TSum
        assert "1upid" in text          # PID type-1
        assert "54ulim" in text         # Limiter
        assert "1uf" in text or " 1uf" in text  # LowPass type-1
        # Ordem preservada
        idx_sum = text.find("98err")
        idx_pid = text.find("1upid")
        idx_lim = text.find("54ulim")
        assert 0 < idx_sum < idx_pid < idx_lim

    def test_pid_with_other_components(self):
        """PID coexiste com R/L/C (lado elétrico)."""
        comps = [
            _mk("PID", "pid1", [
                "err", "u", "1", "10", "0", "", "", "0",
            ]),
            _mk("R", "R1", ["100 Ohm"]),
        ]
        atp = to_atp(PpProject(components=comps))
        # PID gera item TACS, R gera branch
        text = "\n".join(atp.raw_lines)
        assert "/TACS HYBRID" in text
        assert len(atp.branches) == 1

    def test_invalid_pid_warning_keeps_others(self):
        """PID inválido warned mas outros components emergem."""
        comps = [
            _mk("PID", "bad", [
                "err", "u", "abc", "0", "0", "", "", "0",
            ]),
            _mk("Limiter", "ok", [
                "u", "ulim", "-1", "1",
            ]),
        ]
        atp = to_atp(PpProject(components=comps))
        text = "\n".join(atp.raw_lines)
        assert "54ulim" in text
        assert any("Kp" in w for w in atp.warnings)

    def test_tacs_block_and_pid_coexist(self):
        """TACS.ocomp (expressão) coexiste com PID.ocomp (TF)."""
        comps = [
            _mk("TACS", "trig", ["step(t - 0.05)"]),
            _mk("PID", "pid1", [
                "err", "u", "1", "10", "0.001", "", "", "0",
            ]),
        ]
        atp = to_atp(PpProject(components=comps))
        text = "\n".join(atp.raw_lines)
        # TACS bloco device-88
        assert "88trig" in text
        # PID device-1
        assert "1u" in text
