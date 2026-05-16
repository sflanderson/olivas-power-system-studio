"""
app/postprocessor/ansi_fault_report.py — Unified ANSI C37 Fault Report.

Integra os 3 reports do PTW A_FAULT em uma classe coerente:

* **LV Fault Report** — sym RMS no LV bus + X/R + Z + contribuições
* **Momentary Report** — E/Z, X/R, asym factors (1.6, 2.7), Mom, Crest
* **Interrupting Report** — E/Z, NACD, MF, DUTY, contribuições LOCAL/REMOTE

Composição com módulos v3.0.2-v3.0.4:
* `ansi_c37` — machine multipliers, NACD, MF, asym withstand
* `transformer_tap` — TAPS YES/NO scenario
* `pre_fault_voltage` — tolerance scenarios
* `mis_coordination` — cleared fault threshold

Reproduz o formato dos reports publicados no manual A_Fault §1.4.x:
- §1.4.1 Case 1 p. 1-27/28 (small motors example, B2 bus)
- §1.4.3 Case 2 p. 1-36/41 (industrial cogen, PROC A MTR)
- §1.4.4 p. 1-41/50 (Plant Project, 5 buses)

Reference
---------
PTW Reference-A_Fault.pdf §1.4.1 a §1.4.4 (formato de reports).
ANSI/IEEE C37.5-1979, ANSI/IEEE C37.010-1979.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

# Imports dos módulos v3.0.2-v3.0.4 (composição)
from app.standards.ansi_c37 import (
    AnsiStandard,
    BreakerCycle,
    DeviceClass,
    FaultType,
    GeneratorContribution,
    NacdMode,
    asym_withstand_average_3ph,
    asym_withstand_phase_a,
    get_test_xr,
    lv_duty_adjusted,
    mf_by_mode,
    momentary_peak_multiplier,
    momentary_rms_multiplier,
    nacd_ratio,
)


@dataclass
class AnsiFaultBus:
    """Unified container para fault calculation em um bus.

    Combina dados estáticos (bus_name, kV, X/R, I_sym) com geradores
    contribuintes e expõe métodos para gerar os 3 tipos de report do
    PTW A_FAULT (LV, Momentary, Interrupting).

    Attributes
    ----------
    bus_name
        Identificador do bus.
    kv_base
        Voltagem L-L do bus, em kV.
    sym_rms_kA
        Corrente symmetrical RMS no fault, em kA (E/Z method).
    x_over_r
        X/R ratio (separately-derived, conforme §1.2.3 p. 1-6).
    fault_type
        Tipo de fault: ``"3ph"`` (default) ou ``"slg"``.
    contributions
        Lista de :class:`GeneratorContribution` para cada source.

    References
    ----------
    PTW A_FAULT §1.4.1 a §1.4.4 (format reports).
    """

    bus_name: str
    kv_base: float
    sym_rms_kA: float
    x_over_r: float
    fault_type: str = "3ph"
    contributions: list[GeneratorContribution] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.kv_base <= 0:
            raise ValueError(
                f"kv_base must be > 0; got {self.kv_base!r}"
            )
        if self.sym_rms_kA < 0:
            raise ValueError(
                f"sym_rms_kA must be ≥ 0; got {self.sym_rms_kA!r}"
            )
        if self.x_over_r <= 0:
            raise ValueError(
                f"x_over_r must be > 0; got {self.x_over_r!r}"
            )

    @property
    def z_total_ohm(self) -> float:
        """Z = V_LL / (√3 · I_fault) em Ohms.

        Per Stevenson Ch. 12: Z = V_phase / I_phase = (V_LL/√3) / I_phase.
        Para 3-φ fault: I_phase = I_LL = sym_rms_kA.
        """
        if self.sym_rms_kA == 0:
            return math.inf
        return (self.kv_base * 1000.0) / (math.sqrt(3) * self.sym_rms_kA * 1000.0)

    def momentary_duty(self) -> dict[str, Any]:
        """Generate Momentary Duty Report (§1.4.1 format, 7 fields).

        Reproduz o formato do manual:
        ``E/Z, X/R, SYM·1.6, SYM·2.7, Mom-X/R, Crest-X/R``

        Returns
        -------
        dict
            Chaves: ``e_over_z_kA``, ``x_over_r``, ``sym_x_1_6``,
            ``sym_x_2_7``, ``mom_x_over_r_kA``, ``crest_x_over_r_kA``.

        References
        ----------
        PTW A_Fault §1.4.1 Case 1 p. 1-27/28 (linhas 1664-1685).
        """
        mom_factor = momentary_rms_multiplier(self.x_over_r, cycles=0.5)
        crest_factor = momentary_peak_multiplier(self.x_over_r, cycles=0.5)
        return {
            "e_over_z_kA": self.sym_rms_kA,
            "x_over_r": self.x_over_r,
            "sym_x_1_6": self.sym_rms_kA * 1.6,            # PTW simplified
            "sym_x_2_7": self.sym_rms_kA * 2.7,            # PTW simplified peak
            "mom_x_over_r_kA": self.sym_rms_kA * mom_factor,
            "crest_x_over_r_kA": self.sym_rms_kA * crest_factor,
        }

    def interrupting_duty(
        self,
        breaker_cycle: int = 5,
        nacd_mode: NacdMode = NacdMode.INTERPOLATED,
        ansi_std: AnsiStandard = AnsiStandard.C37_010,
    ) -> dict[str, Any]:
        """Generate Interrupting Duty Report (NACD + MF + DUTY).

        Reproduz formato do manual:
        ``E/Z, X/R, contributions L/R, TOTAL REMOTE, NACD, SYM/TOT MF, DUTY``

        Parameters
        ----------
        breaker_cycle
            Breaker rated cycle (2/3/5/8). Default 5.
        nacd_mode
            NACD mode (ALL_REMOTE/PREDOMINANT/INTERPOLATED).
        ansi_std
            ANSI standard (C37.5 or C37.010).

        Returns
        -------
        dict
            Reports field-by-field.

        References
        ----------
        PTW A_Fault §1.4.3 Case 2 p. 1-36/41 (linhas 2310-2499).
        """
        breaker = BreakerCycle(breaker_cycle)
        fault = FaultType.THREE_PHASE if self.fault_type == "3ph" else FaultType.SLG

        i_remote_total = sum(
            g.i_kA for g in self.contributions if not g.is_local()
        )
        nacd = nacd_ratio(self.contributions, self.sym_rms_kA)

        mf = mf_by_mode(
            x_over_r=self.x_over_r, nacd=nacd, mode=nacd_mode,
            breaker=breaker, fault=fault, std=ansi_std,
        )

        return {
            "e_over_z_kA": self.sym_rms_kA,
            "i_total_kA": self.sym_rms_kA,
            "x_over_r": self.x_over_r,
            "i_remote_kA": i_remote_total,
            "i_local_kA": self.sym_rms_kA - i_remote_total,
            "nacd": nacd,
            "nacd_mode": nacd_mode.value,
            "breaker_cycle": breaker_cycle,
            "ansi_std": ansi_std.value,
            "mf": mf,
            "duty_kA": self.sym_rms_kA * mf,
        }

    def lv_duty(
        self,
        device_class: str = "MCCB_GT_20KA",
    ) -> dict[str, Any]:
        """Generate LV Duty Report (LV PCB / MCCB / Fuse adjustment).

        Per §1.2.3 p. 1-6 + §1.4.4 (LV bus reports):

        .. math::
            I_{LVF} = I_{symm} \\cdot \\frac{\\sqrt{1 + e^{-\\pi/(X/R)_{sys}}}}
                                            {\\sqrt{1 + e^{-\\pi/(X/R)_{test}}}}

        Parameters
        ----------
        device_class
            ``"LV_PCB"``, ``"LV_FUSE"``, ``"MCCB_GT_20KA"``,
            ``"MCCB_10_20KA"``, ``"MCCB_LT_10KA"``, or ``"HV_FUSE"``.

        Returns
        -------
        dict
            Adjusted duty + test parameters.

        References
        ----------
        PTW A_Fault §1.2.3 p. 1-6, §1.4.4 p. 1-42/45.
        """
        device = DeviceClass[device_class]
        test_xr = get_test_xr(device)
        adjusted = lv_duty_adjusted(
            sym_rms_kA=self.sym_rms_kA,
            system_x_over_r=self.x_over_r,
            test_x_over_r=test_xr,
        )
        return {
            "device_class": device_class,
            "test_x_over_r": test_xr,
            "system_x_over_r": self.x_over_r,
            "sym_rms_kA": self.sym_rms_kA,
            "adjusted_kA": adjusted,
            "boost_or_attenuation": adjusted / self.sym_rms_kA,
        }

    def asymmetrical_withstand(
        self,
        formulation: str = "phase_a",
    ) -> float:
        """Asymmetrical withstand current at ½ cycle.

        Per §1.2.3 p. 1-6/1-7:
        * ``"phase_a"`` — Phase A worst-case (B.2)
        * ``"average_3ph"`` — average das 3 fases (B.3, IEEE Std 551 §7.6)

        Returns
        -------
        float
            I_asym RMS at ½ cycle, kA.
        """
        if formulation == "phase_a":
            return asym_withstand_phase_a(self.sym_rms_kA, self.x_over_r)
        if formulation == "average_3ph":
            return asym_withstand_average_3ph(self.sym_rms_kA, self.x_over_r)
        raise ValueError(
            f"formulation must be 'phase_a' or 'average_3ph'; got {formulation!r}"
        )


@dataclass
class AnsiFaultReport:
    """Container para múltiplos AnsiFaultBus + formatters de output.

    Reproduz o formato dos reports publicados em PTW A_Fault §1.4.x
    (Cases §1.4.1 a §1.4.4), com 3 formatters:

    * **text** — PTW-style fixed-width output (paridade)
    * **markdown** — tables + headers (superação visual vs PTW text-only)
    * **csv** — datablock-style export (compatível Excel/Pandas)

    References
    ----------
    PTW A_Fault §1.4.1 a §1.4.4 (formato reports).
    """

    project_name: str
    buses: list[AnsiFaultBus] = field(default_factory=list)

    def add_bus(self, bus: AnsiFaultBus) -> None:
        """Adiciona um bus ao report."""
        self.buses.append(bus)

    def format_text(self) -> str:
        """Formato PTW-style text (fixed width, ANSI report header).

        Reproduz aparência do manual A_Fault §1.4.x:
        - Header com project name + ANSI standard
        - Por bus: linhas com Bus name, kV, I_sym, X/R, Z

        References
        ----------
        PTW A_Fault §1.4.1 (linhas 1644-1685 — exemplo de B2 fault report).
        """
        lines: list[str] = []
        lines.append("=" * 78)
        lines.append(f" ANSI/IEEE C37.5/C37.010 FAULT REPORT — {self.project_name}")
        lines.append(" Generated by Olivas Power System Studio (Reference: PTW A_Fault)")
        lines.append("=" * 78)
        lines.append("")
        lines.append(f"{'Bus Name':<20} {'kV':>8} {'I_sym (kA)':>12} {'X/R':>8} {'Z (Ohm)':>10}")
        lines.append("-" * 78)
        for bus in self.buses:
            lines.append(
                f"{bus.bus_name:<20} {bus.kv_base:>8.3f} "
                f"{bus.sym_rms_kA:>12.3f} {bus.x_over_r:>8.2f} "
                f"{bus.z_total_ohm:>10.4f}"
            )
        lines.append("=" * 78)
        return "\n".join(lines)

    def format_markdown(self) -> str:
        """Formato Markdown — superação visual vs PTW text-only.

        Output:
        - H1 com project name
        - Tabela com fault data por bus
        - H2 por bus com sub-reports (Mom, Int, LV)
        """
        md: list[str] = []
        md.append(f"# ANSI Fault Report — {self.project_name}")
        md.append("")
        md.append("**Reference**: PTW A_Fault §1.4 + ANSI/IEEE C37.5/C37.010-1979")
        md.append("")
        md.append("## Summary table")
        md.append("")
        md.append("| Bus Name | kV | I_sym (kA) | X/R | Z (Ohm) |")
        md.append("|----------|----|----|----|---------|")
        for bus in self.buses:
            md.append(
                f"| {bus.bus_name} | {bus.kv_base:.3f} | "
                f"{bus.sym_rms_kA:.3f} | {bus.x_over_r:.2f} | "
                f"{bus.z_total_ohm:.4f} |"
            )
        md.append("")
        for bus in self.buses:
            md.append(f"## Bus {bus.bus_name}")
            md.append("")
            md.append(f"- kV base: {bus.kv_base:.3f}")
            md.append(f"- Symmetrical RMS: {bus.sym_rms_kA:.3f} kA")
            md.append(f"- X/R (separately-derived, §1.2.3): {bus.x_over_r:.2f}")
            md.append(f"- Fault type: {bus.fault_type}")
            md.append("")
        return "\n".join(md)

    def format_csv(self) -> str:
        """Formato CSV — datablock export style (Excel/Pandas compatível)."""
        lines: list[str] = []
        # Header
        lines.append("bus_name,kv_base,sym_rms_kA,x_over_r,z_total_ohm,fault_type")
        for bus in self.buses:
            lines.append(
                f"{bus.bus_name},{bus.kv_base:.4f},"
                f"{bus.sym_rms_kA:.4f},{bus.x_over_r:.4f},"
                f"{bus.z_total_ohm:.6f},{bus.fault_type}"
            )
        return "\n".join(lines)


__all__ = [
    "AnsiFaultBus",
    "AnsiFaultReport",
]
