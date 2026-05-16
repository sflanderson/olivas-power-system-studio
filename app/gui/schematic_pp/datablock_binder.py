"""
app.gui.schematic_pp.datablock_binder — substituição de
placeholders nas linhas de :class:`PpDataBlock` a partir de
resultados de análises (v0.87).

Workflow PTW
=============

1. Usuário cria datablock com template (ex: "Curto-circuito"):

   ::

       Ik''  = {Ik_pp_kA:.2f} kA
       ip    = {ip_kA:.2f} kA
       κ     = {kappa:.2f}

2. Usuário roda análise pipeline → ``BusPipelineReport`` é
   gerado.

3. ``DataBlockBinder.refresh_from_report(scene, bus_id, report)``
   substitui os placeholders nas datablocks ancoradas a esse bus.

4. Lines do datablock viram strings finais com valores:

   ::

       Ik''  = 15.30 kA
       ip    = 40.20 kA
       κ     = 1.85

Filosofia
==========

* **Placeholders desconhecidos sobrevivem** — não crash. Se um
  template tem ``{V_LL_kV}`` mas o report não fornece esse campo,
  a string ``{V_LL_kV}`` permanece (avisa o usuário visualmente
  que falta dado, sem bloquear).
* **Substituição idempotente** — re-aplicar duas vezes o mesmo
  report dá o mesmo resultado (não reprocessamos chaves já
  substituídas; chaves originais foram apagadas).
* **Format-spec opcional** — ``{key}`` ou ``{key:fmt}`` (mesma
  sintaxe de ``str.format``).

Para a Phase 2 v0.87 cobrimos APENAS ``BusPipelineReport``.
Suporte a Power-Flow / Motor-Starting / Coordenação fica para
sprints futuras (a estrutura genérica de ``bind_lines`` já
aceita qualquer dict de valores).
"""

from __future__ import annotations

import re
from typing import Any, Optional

from app.preprocessor.models import PpDataBlock


# Padrão para encontrar `{key}` ou `{key:fmt}` dentro de uma linha.
# Usamos non-greedy ([^{}]+) para evitar match em chaves aninhadas.
_PLACEHOLDER_RE = re.compile(r"\{([^{}]+)\}")


def bind_lines(
    lines: list[str], values: dict[str, Any],
) -> list[str]:
    """
    Aplica substituição de placeholders ``{key}`` / ``{key:fmt}``
    em cada linha. Chaves desconhecidas permanecem literais.

    Examples
    --------

    >>> bind_lines(
    ...     ["Ip = {Ip_kA:.2f} kA"],
    ...     {"Ip_kA": 15.3},
    ... )
    ['Ip = 15.30 kA']

    >>> bind_lines(
    ...     ["Falta = {missing}"],
    ...     {"present": 1},
    ... )
    ['Falta = {missing}']
    """
    return [_substitute(line, values) for line in lines]


def _substitute(line: str, values: dict[str, Any]) -> str:
    def repl(match: re.Match) -> str:
        token = match.group(1)
        if ":" in token:
            name, fmt = token.split(":", 1)
        else:
            name, fmt = token, None
        if name not in values:
            return match.group(0)   # mantém literal
        val = values[name]
        if fmt:
            try:
                return format(val, fmt)
            except (ValueError, TypeError):
                return str(val)
        return str(val)

    return _PLACEHOLDER_RE.sub(repl, line)


# ---------------------------------------------------------------------------
# Extractors — convertem objetos de relatório em ``dict[str, Any]``
# ---------------------------------------------------------------------------


def extract_values_from_pipeline_report(report) -> dict[str, Any]:
    """
    Extrai todos os campos relevantes de um
    :class:`app.postprocessor.bus_pipeline.BusPipelineReport`
    em um dict consumível por :func:`bind_lines`.

    Chaves do dict (estáveis — usar nos templates):

    * ``bus_id``                   — str
    * ``rated_voltage_kV``         — float
    * ``V_LL_kV``                  — alias de rated_voltage_kV
    * ``panel_type``               — str
    * ``is_lineside``              — bool
    * ``has_AFD``                  — bool
    * ``n_neighbors``              — int
    * ``n_sc_sources``             — int
    * ``Ik_pp_kA``                 — float (SC RMS sym)
    * ``ip_kA``                    — float (SC peak)
    * ``kappa``                    — float (peak factor)
    * ``coordination_clearing_time_ms`` — float
    * ``effective_clearing_time_ms``    — float
    * ``t_clear_ms``               — alias de effective_clearing_time_ms
    * ``incident_energy_cal_cm2``  — float
    * ``IE_cal``                   — alias
    * ``arc_flash_boundary_mm``    — float
    * ``AFB_mm``                   — alias
    * ``ppe_category``             — str
    * ``PPE``                      — alias
    """
    if report is None:
        return {}

    values: dict[str, Any] = {}
    # Direct fields (presença defensiva via getattr)
    direct_fields = [
        "bus_id", "rated_voltage_kV", "panel_type",
        "is_lineside", "has_AFD",
        "n_neighbors", "n_sc_sources",
        "Ik_pp_kA", "ip_kA", "kappa",
        "coordination_clearing_time_ms",
        "effective_clearing_time_ms",
        "incident_energy_cal_cm2",
        "arc_flash_boundary_mm",
        "ppe_category",
    ]
    for f in direct_fields:
        if hasattr(report, f):
            values[f] = getattr(report, f)

    # Aliases (UX: nomes mais curtos que ficam bonitos no
    # template).
    alias_map = {
        "V_LL_kV": "rated_voltage_kV",
        "t_clear_ms": "effective_clearing_time_ms",
        "IE_cal": "incident_energy_cal_cm2",
        "AFB_mm": "arc_flash_boundary_mm",
        "PPE": "ppe_category",
        "Sk_pp_MVA": None,   # calculado abaixo
    }
    for alias, src in alias_map.items():
        if src and src in values:
            values[alias] = values[src]

    # Derivado: S_k'' = √3 · V_LL · Ik'' (em MVA com kV·kA)
    try:
        if "rated_voltage_kV" in values and "Ik_pp_kA" in values:
            import math
            values["Sk_pp_MVA"] = (
                math.sqrt(3)
                * float(values["rated_voltage_kV"])
                * float(values["Ik_pp_kA"])
            )
    except (TypeError, ValueError):
        pass

    return values


# ---------------------------------------------------------------------------
# Result cache + refresh helper
# ---------------------------------------------------------------------------


class DataBlockResultCache:
    """
    Cache de relatórios indexado por ``bus_id``. Pendurado
    no :class:`PpScene` (v0.87) para que datablocks possam
    ser refrescados quando o usuário pedir.

    v0.88: 3 namespaces independentes:

    * ``pipeline`` — :class:`BusPipelineReport` (estudo completo)
    * ``sc``       — :class:`ShortCircuitResult` (SC standalone)
    * ``pf``       — :class:`PowerFlowSolution` (PF — armazenada
      pelo bus_id, mas a solution é para a rede toda; o
      extractor filtra por bus_id)
    """

    def __init__(self) -> None:
        self._pipeline_reports: dict[str, Any] = {}
        self._sc_results: dict[str, Any] = {}
        self._pf_solutions: dict[str, Any] = {}

    # -- pipeline -----------------------------------------------------------
    def set_pipeline_report(self, bus_id: str, report) -> None:
        if not bus_id:
            return
        self._pipeline_reports[bus_id] = report

    def get_pipeline_report(self, bus_id: str):
        return self._pipeline_reports.get(bus_id)

    # -- SC standalone ------------------------------------------------------
    def set_sc_result(self, bus_id: str, result) -> None:
        """v0.88: armazena ShortCircuitResult de um bus."""
        if not bus_id:
            return
        self._sc_results[bus_id] = result

    def get_sc_result(self, bus_id: str):
        return self._sc_results.get(bus_id)

    # -- Power Flow --------------------------------------------------------
    def set_pf_solution(self, bus_id: str, solution) -> None:
        """v0.88: armazena PowerFlowSolution para o bus.

        A mesma solution pode ser registrada para vários
        bus_ids (o caller que percorre solution.bus_voltages_pu
        chama set_pf_solution para cada um). O extractor filtra
        pelo bus_id no momento do bind.
        """
        if not bus_id:
            return
        self._pf_solutions[bus_id] = solution

    def get_pf_solution(self, bus_id: str):
        return self._pf_solutions.get(bus_id)

    # -- aggregate -----------------------------------------------------------
    def all_bus_ids(self) -> list[str]:
        """União de bus_ids em todos os namespaces."""
        s = set(self._pipeline_reports)
        s |= set(self._sc_results)
        s |= set(self._pf_solutions)
        return list(s)

    def clear(self) -> None:
        self._pipeline_reports.clear()
        self._sc_results.clear()
        self._pf_solutions.clear()


# ---------------------------------------------------------------------------
# Additional extractors (v0.88)
# ---------------------------------------------------------------------------


def extract_values_from_sc_result(result) -> dict[str, Any]:
    """
    v0.88: dict consumível por :func:`bind_lines` a partir de
    :class:`app.standards.iec60909.ShortCircuitResult`.

    Chaves alinhadas com o template "Curto-circuito":
    ``Ik_pp_kA``, ``ip_kA``, ``kappa``, ``Sk_pp_MVA``,
    ``r_over_x``, ``rated_voltage_kV``.
    """
    if result is None:
        return {}
    values: dict[str, Any] = {}
    fields = [
        "Ik_pp_kA", "ip_kA", "idc_at_50ms_kA", "Ib_kA",
        "Ik_steady_kA", "kappa", "voltage_factor_c",
        "rated_voltage_kV", "r_over_x",
    ]
    for f in fields:
        if hasattr(result, f):
            values[f] = getattr(result, f)
    # Aliases
    if "rated_voltage_kV" in values:
        values["V_LL_kV"] = values["rated_voltage_kV"]
    # Sk'' derivado
    try:
        if "rated_voltage_kV" in values and "Ik_pp_kA" in values:
            import math
            values["Sk_pp_MVA"] = (
                math.sqrt(3)
                * float(values["rated_voltage_kV"])
                * float(values["Ik_pp_kA"])
            )
    except (TypeError, ValueError):
        pass
    return values


def extract_values_from_pf_solution(
    solution, bus_id: str,
) -> dict[str, Any]:
    """
    v0.88: dict de :class:`PowerFlowSolution` filtrado por
    ``bus_id``.

    Chaves alinhadas com o template "Fluxo de potência":
    ``V_pu``, ``V_angle_deg``, ``pf_converged``,
    ``pf_iterations``, ``total_losses_kW``.
    """
    if solution is None:
        return {}
    values: dict[str, Any] = {}
    if hasattr(solution, "converged"):
        values["pf_converged"] = bool(solution.converged)
    if hasattr(solution, "iterations"):
        values["pf_iterations"] = int(solution.iterations)
    if hasattr(solution, "total_losses_pu"):
        try:
            losses = solution.total_losses_pu
            # Sem rated_S no escopo PF — devolvemos em pu.
            values["total_losses_pu_real"] = float(losses.real)
            values["total_losses_pu_imag"] = float(losses.imag)
        except (TypeError, ValueError):
            pass
    # Per-bus voltage
    if hasattr(solution, "bus_voltages_pu"):
        bv = solution.bus_voltages_pu or {}
        V = bv.get(bus_id)
        if V is not None:
            try:
                import math
                values["V_pu"] = abs(V)
                values["V_angle_deg"] = math.degrees(
                    math.atan2(V.imag, V.real)
                )
            except (TypeError, ValueError):
                pass
    return values


def refresh_datablocks_from_cache(
    scene,
    cache: DataBlockResultCache,
) -> int:
    """
    Aplica :func:`bind_lines` em todos os datablocks da cena
    cujo ``component_name`` tem algum resultado no ``cache``.

    v0.88: usa ``db.effective_template()`` como fonte de
    substituição (não ``db.lines``) — assim refresh é
    idempotente entre análises sucessivas e o template original
    é preservado.

    Aggrega valores de TODOS os reports cacheados para o bus:
    pipeline → SC standalone → PF solution. O dict resultante é
    passado para ``bind_lines`` em uma única operação.

    Retorna o número de datablocks atualizados.

    Empilha um único :class:`EditDataBlockLinesCommand` por
    datablock atualizado (undoable).
    """
    if scene is None or cache is None:
        return 0
    # Lazy import — evita ciclo
    from .commands import EditDataBlockLinesCommand
    stack = getattr(scene, "undo_stack", None)
    n_updated = 0
    for db_item in scene.datablock_items():
        db = db_item.datablock
        bus_id = _resolve_bus_id_for_component(scene, db.component_name)
        if bus_id is None:
            continue
        values = aggregate_values_for_bus(cache, bus_id)
        if not values:
            continue
        # Migra legacy datablocks (sem template) na primeira
        # tentativa: salvamos lines atuais como template antes
        # de re-render. Garante que re-runs não destruam o
        # template original.
        if not db.template_lines:
            db.template_lines = list(db.lines)
        template = db.effective_template()
        new_lines = bind_lines(template, values)
        if new_lines == db.lines:
            continue   # nada a atualizar
        if stack is not None:
            stack.push(
                EditDataBlockLinesCommand(scene, db, new_lines)
            )
        else:
            # Fallback sem undo: mutação direta.
            db.lines = new_lines
            db_item.prepareGeometryChange()
            db_item.sync_from_model()
        n_updated += 1
    return n_updated


def aggregate_values_for_bus(
    cache: "DataBlockResultCache", bus_id: str,
) -> dict:
    """
    v0.88: agrega valores de TODOS os reports cacheados para
    ``bus_id`` em um único dict consumível por ``bind_lines``.

    Ordem de merge (last wins):
    1. ``pipeline_report`` (mais completo — SC + AF + topology)
    2. ``sc_result`` (refina/sobrescreve SC se rodado isoladamente)
    3. ``pf_solution`` (V_pu, V_angle_deg deste bus)
    """
    values: dict = {}
    pl = cache.get_pipeline_report(bus_id)
    if pl is not None:
        values.update(extract_values_from_pipeline_report(pl))
    sc = cache.get_sc_result(bus_id)
    if sc is not None:
        values.update(extract_values_from_sc_result(sc))
    pf = cache.get_pf_solution(bus_id)
    if pf is not None:
        values.update(extract_values_from_pf_solution(pf, bus_id))
    return values


def _resolve_bus_id_for_component(
    scene, component_name: str,
) -> Optional[str]:
    """
    Para componentes BUS, ``component_name`` pode ser tanto o
    ``PpComponent.name`` quanto o ``bus_id`` (1ª propriedade
    do BUS — ID do painel preenchido pelo usuário).

    Esta função tenta as duas formas e retorna o ``bus_id``
    canônico (que casa com a chave do cache do
    ``run_bus_pipeline_analysis``, que usa props[0]).

    Se o componente não for BUS, retorna ``None``.
    """
    if not component_name or scene is None:
        return None
    # Procura componente com nome direto
    for ci in scene.component_items():
        comp = ci.component
        if comp.type != "BUS":
            continue
        if comp.name == component_name:
            # Bus encontrado — bus_id vem de props[0]
            return (comp.get(0, "") or "").strip() or comp.name
        # Também pode ser que component_name seja já o bus_id
        if (comp.get(0, "") or "").strip() == component_name:
            return component_name
    return None
