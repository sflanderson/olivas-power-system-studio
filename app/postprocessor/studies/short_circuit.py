"""
app.postprocessor.studies.short_circuit — Estudo de Curto-
Circuito MODULAR (v0.94.0).

PTW-style standalone — sem pré-requisitos. Pode ser
executado em qualquer bus que tenha fonte SC conectada
(direta ou via multi-hop walking).

Cobertura normativa
====================

* IEC 60909-0:2016 §4.3 — Cálculo de Ik''
* IEC 60909-0:2016 §4.3.1.2 — Factor κ (Method B)
* IEC 60909-0:2016 §4.6 — Decay near-to-generator (μ·q)
* IEC 60909-0:2016 §4.3.2-4.3.4 — Faltas assimétricas
  (LG / LL / LLG via componentes simétricas)

Saída
======

:class:`ShortCircuitStudyResult` — dataclass frozen com:

* ``Ik_pp_kA`` — corrente subtransitória (kA RMS)
* ``ip_kA`` — pico assimétrico
* ``Ib_kA`` — breaking current
* ``Ik_steady_kA`` — corrente de regime
* ``kappa`` — factor de assimetria
* ``r_over_x`` — razão R/X
* ``z_thevenin_ohm`` — impedância de Thevenin (complex)
* ``voltage_factor_c`` — fator c IEC
* ``rated_voltage_kV`` — tensão nominal
* ``warnings`` — lista de avisos

Uso
====

::

    from app.postprocessor.studies import short_circuit

    # Standalone (sem cache)
    result = short_circuit.run(project, "BUS-MAIN-13.8")

    # Com cache (recomendado em UI multi-step)
    cache = StudyCache()
    result = short_circuit.run(project, "BUS-MAIN-13.8", cache=cache)
    # 2a chamada: instantânea (cache hit)
    result2 = short_circuit.run(project, "BUS-MAIN-13.8", cache=cache)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from app.postprocessor.study_cache import StudyCache, hash_study_inputs


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ShortCircuitStudyResult:
    """Resultado do estudo de curto-circuito (modular v0.94)."""

    bus_id: str
    rated_voltage_kV: float

    # Correntes principais (IEC 60909)
    Ik_pp_kA: float                  # Ik'' subtransiente
    ip_kA: float                     # peak asymmetric
    Ib_kA: float                     # breaking
    Ik_steady_kA: float              # steady-state

    # Parâmetros
    kappa: float
    r_over_x: float
    voltage_factor_c: float

    # Impedância de Thevenin (real, imag) em Ω
    z_thevenin_real_ohm: float
    z_thevenin_imag_ohm: float

    # Diagnóstico
    n_sc_sources: int
    sources_summary: tuple[str, ...] = field(default_factory=tuple)
    n_neighbors: int = 0
    topology_chains: tuple = field(default_factory=tuple)

    # Faltas assimétricas (opcional)
    asymmetric_fault_result: Optional[Any] = None
    decay_result: Optional[Any] = None

    # Method usado
    kappa_method_used: str = "B"

    warnings: tuple[str, ...] = field(default_factory=tuple)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def run(
    project,
    bus_id: str,
    *,
    cache: Optional[StudyCache] = None,
    config: Optional[Any] = None,
    use_multi_hop: bool = True,
    pre_fault_voltage_pu: Optional[float] = None,
) -> ShortCircuitStudyResult:
    """
    Executa o estudo de curto-circuito para ``bus_id``.

    Standalone — não requer outros estudos prévios.

    Parameters
    ----------
    project:
        ``PpProject`` carregado.
    bus_id:
        ID do barramento alvo.
    cache:
        :class:`StudyCache` opcional para reuso de resultados.
    config:
        :class:`BusPipelineConfig` (sera usado internamente).
        Se None, usa defaults.
    use_multi_hop:
        Walking de transformadores upstream (default True).
    pre_fault_voltage_pu:
        V real do PF (se já rodado) para escalar Ik''.

    Returns
    -------
    ShortCircuitStudyResult
    """
    from app.postprocessor.bus_pipeline import (
        BusPipelineConfig,
    )

    if config is None:
        config = BusPipelineConfig()

    # Cache check
    if cache is not None:
        h = hash_study_inputs(
            project, bus_id, ("sc", config, use_multi_hop, pre_fault_voltage_pu),
        )
        cached = cache.get_sc_if_valid(bus_id, h)
        if cached is not None:
            return cached

    # Compute
    result = _compute_short_circuit(
        project, bus_id, config,
        use_multi_hop=use_multi_hop,
        pre_fault_voltage_pu=pre_fault_voltage_pu,
    )

    # Store
    if cache is not None:
        cache.set_sc(bus_id, result, h)

    return result


# ---------------------------------------------------------------------------
# Internal: compute
# ---------------------------------------------------------------------------


def _compute_short_circuit(
    project,
    bus_id: str,
    config,
    *,
    use_multi_hop: bool,
    pre_fault_voltage_pu: Optional[float],
) -> ShortCircuitStudyResult:
    """
    Núcleo do cálculo. Usa as funções privadas de
    :mod:`app.postprocessor.bus_pipeline` para construir
    a network e calcular.

    v0.94.0: separa o que era o miolo do
    ``analyze_bus_full_pipeline`` linhas 913–1180 (sem
    arc-flash, sem sugestões de relé).
    """
    import math
    from app.postprocessor.bus_pipeline import (
        _bus_from_pp_component,
        build_sc_network_from_bus,
        find_bus_component,
        find_neighbors_of_bus,
    )

    bus_comp = find_bus_component(project, bus_id)
    if bus_comp is None:
        raise ValueError(f"BUS {bus_id!r} não encontrado.")

    bus = _bus_from_pp_component(bus_comp)

    # 1+2: walking + network build (com multi-hop se ativado)
    walk_warnings: list[str] = []
    topology_chains: tuple = ()
    if use_multi_hop:
        from app.postprocessor.multihop_walker import (
            build_sc_network_multi_hop,
        )
        net, chains_list, walk_warnings_list = (
            build_sc_network_multi_hop(
                project, bus_id, max_hops=4, config=config,
            )
        )
        walk_warnings.extend(walk_warnings_list)
        topology_chains = tuple(chains_list)
    else:
        net, walk_warnings_list = build_sc_network_from_bus(
            project, bus_id, config,
        )
        walk_warnings.extend(walk_warnings_list)

    # 3: SC analysis
    if not net.sources:
        raise ValueError(
            f"BUS {bus_id!r}: nenhuma fonte de SC encontrada. "
            "Conecte Vac/SM/Tr ao bus antes de analisar."
        )

    sc_result = net.calculate_at_bus(
        bus.bus_id, kind=config.calculation_kind,
    )

    # Pre-fault voltage scaling (se PF já rodado)
    if pre_fault_voltage_pu is not None and pre_fault_voltage_pu > 0:
        c_used = config.resolve_voltage_factor_c(bus.rated_voltage_kV)
        scale = pre_fault_voltage_pu / c_used
        from app.standards.iec60909 import ShortCircuitResult
        sc_result = ShortCircuitResult(
            Ik_pp_kA=sc_result.Ik_pp_kA * scale,
            ip_kA=sc_result.ip_kA * scale,
            idc_at_50ms_kA=sc_result.idc_at_50ms_kA * scale,
            Ib_kA=sc_result.Ib_kA * scale,
            Ik_steady_kA=sc_result.Ik_steady_kA * scale,
            z_thevenin_ohm=sc_result.z_thevenin_ohm,
            r_over_x=sc_result.r_over_x,
            kappa=sc_result.kappa,
            voltage_factor_c=sc_result.voltage_factor_c,
            rated_voltage_kV=sc_result.rated_voltage_kV,
            fault_distance=sc_result.fault_distance,
        )

    # κ Method B/C
    kappa_method_used = config.kappa_method.upper()
    if kappa_method_used in ("B", "C"):
        from app.standards.iec60909_kappa import (
            kappa_method_B, kappa_method_C,
        )
        from app.standards.iec60909 import ShortCircuitResult
        if kappa_method_used == "B":
            new_kappa = kappa_method_B(sc_result.r_over_x)
        else:
            fc_over_fn = config.fc_Hz / 60.0
            z_at_fc = complex(
                sc_result.z_thevenin_ohm.real,
                sc_result.z_thevenin_ohm.imag * fc_over_fn,
            )
            new_kappa = kappa_method_C(
                z_at_fc, nominal_frequency_Hz=60.0, fc_Hz=config.fc_Hz,
            )
        new_ip = math.sqrt(2.0) * new_kappa * sc_result.Ik_pp_kA
        sc_result = ShortCircuitResult(
            Ik_pp_kA=sc_result.Ik_pp_kA,
            ip_kA=new_ip,
            idc_at_50ms_kA=sc_result.idc_at_50ms_kA,
            Ib_kA=sc_result.Ib_kA,
            Ik_steady_kA=sc_result.Ik_steady_kA,
            z_thevenin_ohm=sc_result.z_thevenin_ohm,
            r_over_x=sc_result.r_over_x,
            kappa=new_kappa,
            voltage_factor_c=sc_result.voltage_factor_c,
            rated_voltage_kV=sc_result.rated_voltage_kV,
            fault_distance=sc_result.fault_distance,
        )
        walk_warnings.append(
            f"κ Method {kappa_method_used} aplicado: "
            f"κ={new_kappa:.3f}, ip={new_ip:.3f} kA"
        )

    # Decay near-to-generator
    decay_result = None
    Ib_kA_final = sc_result.Ib_kA
    Ik_steady_kA_final = sc_result.Ik_steady_kA
    if config.apply_near_to_generator_decay:
        from app.postprocessor.bus_pipeline import (
            _estimate_rated_current_from_sources,
        )
        from app.standards.iec60909_decay import (
            apply_near_to_generator_decay,
        )
        I_rG_kA = _estimate_rated_current_from_sources(
            net, bus.rated_voltage_kV,
        )
        if I_rG_kA > 0:
            try:
                decay_result = apply_near_to_generator_decay(
                    Ik_pp_kA=sc_result.Ik_pp_kA,
                    IrG_kA=I_rG_kA,
                    minimum_clearing_time_s=config.minimum_clearing_time_s,
                )
                Ib_kA_final = decay_result.Ib_kA
                Ik_steady_kA_final = decay_result.Ik_steady_kA
                if decay_result.is_near_to_generator:
                    walk_warnings.append(
                        f"Decay near-to-gen aplicado: "
                        f"μ={decay_result.mu:.3f}, "
                        f"q={decay_result.q:.3f}"
                    )
            except (ValueError, ZeroDivisionError):
                decay_result = None

    # Faltas assimétricas
    asymmetric_fault_result = None
    if config.compute_asymmetric_faults:
        from app.standards.iec60909_seq import (
            calculate_all_faults, GroundingType,
            sequence_impedances_from_grounding,
        )
        grounding = (
            config.grounding_type
            if isinstance(config.grounding_type, GroundingType)
            else GroundingType[config.grounding_type.upper()]
        )
        seq = sequence_impedances_from_grounding(
            sc_result.z_thevenin_ohm,
            grounding,
            R_N_ohm=config.grounding_R_N_ohm,
        )
        c_used = config.resolve_voltage_factor_c(bus.rated_voltage_kV)
        asymmetric_fault_result = calculate_all_faults(
            Un_kV=bus.rated_voltage_kV,
            seq_impedances=seq,
            grounding=grounding,
            voltage_factor_c=c_used,
        )

    # Sources summary (texto descritivo)
    sources_summary: list[str] = []
    for src in net.sources:
        sources_summary.append(repr(src))

    n_neighbors = len(find_neighbors_of_bus(project, bus_id))

    return ShortCircuitStudyResult(
        bus_id=bus.bus_id,
        rated_voltage_kV=bus.rated_voltage_kV,
        Ik_pp_kA=sc_result.Ik_pp_kA,
        ip_kA=sc_result.ip_kA,
        Ib_kA=Ib_kA_final,
        Ik_steady_kA=Ik_steady_kA_final,
        kappa=sc_result.kappa,
        r_over_x=sc_result.r_over_x,
        voltage_factor_c=sc_result.voltage_factor_c,
        z_thevenin_real_ohm=sc_result.z_thevenin_ohm.real,
        z_thevenin_imag_ohm=sc_result.z_thevenin_ohm.imag,
        n_sc_sources=len(net.sources),
        sources_summary=tuple(sources_summary),
        n_neighbors=n_neighbors,
        topology_chains=topology_chains,
        asymmetric_fault_result=asymmetric_fault_result,
        decay_result=decay_result,
        kappa_method_used=kappa_method_used,
        warnings=tuple(walk_warnings),
    )
