"""Side-by-side comparison of two ATP cases.

Compares header, models, components, and USE DATA parameters between
two AtpProject instances and returns structured diff results.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.core.project_model import AtpProject


@dataclass
class ParamDiff:
    """A single parameter difference between two cases."""
    category: str  # "header", "model_data", "use_data", "component"
    label: str
    value_a: str
    value_b: str


@dataclass
class CompareResult:
    """Result of comparing two ATP cases."""
    file_a: str
    file_b: str
    diffs: list[ParamDiff] = field(default_factory=list)
    summary_a: dict[str, Any] = field(default_factory=dict)
    summary_b: dict[str, Any] = field(default_factory=dict)

    @property
    def has_diffs(self) -> bool:
        return len(self.diffs) > 0


def compare_cases(a: AtpProject, b: AtpProject) -> CompareResult:
    """Compare two ATP projects and return differences."""
    result = CompareResult(
        file_a=a.file_path,
        file_b=b.file_path,
        summary_a=_summary(a),
        summary_b=_summary(b),
    )

    _compare_header(a, b, result)
    _compare_models(a, b, result)
    _compare_uses(a, b, result)
    _compare_counts(a, b, result)

    return result


def _summary(p: AtpProject) -> dict[str, Any]:
    return {
        "models": len(p.models),
        "uses": len(p.uses),
        "branches": len(p.branches),
        "switches": len(p.switches),
        "sources": len(p.sources),
        "nodes": len(p.nodes),
    }


def _fmt(v: Any) -> str:
    if v is None:
        return "—"
    return str(v)


def _compare_header(a: AtpProject, b: AtpProject, result: CompareResult) -> None:
    for attr, label in [
        ("delta_t", "Header: delta_t"),
        ("t_max", "Header: t_max"),
        ("frequency", "Header: frequency"),
    ]:
        va = getattr(a.header, attr, None)
        vb = getattr(b.header, attr, None)
        if va != vb:
            result.diffs.append(ParamDiff("header", label, _fmt(va), _fmt(vb)))


def _compare_models(a: AtpProject, b: AtpProject, result: CompareResult) -> None:
    names_a = {m.name.upper(): m for m in a.models}
    names_b = {m.name.upper(): m for m in b.models}

    all_names = sorted(set(names_a) | set(names_b))
    for name in all_names:
        ma = names_a.get(name)
        mb = names_b.get(name)

        if ma and not mb:
            result.diffs.append(ParamDiff("model_data", f"MODEL {name}", "presente", "ausente"))
            continue
        if not ma and mb:
            result.diffs.append(ParamDiff("model_data", f"MODEL {name}", "ausente", "presente"))
            continue

        # Compare DATA defaults
        data_a = {d.name.upper(): d.default_value for d in ma.data}
        data_b = {d.name.upper(): d.default_value for d in mb.data}
        for pname in sorted(set(data_a) | set(data_b)):
            va = data_a.get(pname)
            vb = data_b.get(pname)
            if va != vb:
                result.diffs.append(ParamDiff(
                    "model_data",
                    f"MODEL {name}.{pname}",
                    _fmt(va), _fmt(vb),
                ))


def _compare_uses(a: AtpProject, b: AtpProject, result: CompareResult) -> None:
    uses_a = {u.model_name.upper(): u for u in a.uses}
    uses_b = {u.model_name.upper(): u for u in b.uses}

    all_names = sorted(set(uses_a) | set(uses_b))
    for name in all_names:
        ua = uses_a.get(name)
        ub = uses_b.get(name)

        if ua and not ub:
            result.diffs.append(ParamDiff("use_data", f"USE {name}", "presente", "ausente"))
            continue
        if not ua and ub:
            result.diffs.append(ParamDiff("use_data", f"USE {name}", "ausente", "presente"))
            continue

        # Compare DATA assigned values
        data_a = {d.name.upper(): (d.assigned_value or d.default_value) for d in ua.data}
        data_b = {d.name.upper(): (d.assigned_value or d.default_value) for d in ub.data}
        for pname in sorted(set(data_a) | set(data_b)):
            va = data_a.get(pname)
            vb = data_b.get(pname)
            if va != vb:
                result.diffs.append(ParamDiff(
                    "use_data",
                    f"USE {name}.{pname}",
                    _fmt(va), _fmt(vb),
                ))


def _compare_counts(a: AtpProject, b: AtpProject, result: CompareResult) -> None:
    for attr, label in [
        ("branches", "Contagem: BRANCH"),
        ("switches", "Contagem: SWITCH"),
        ("sources", "Contagem: SOURCE"),
    ]:
        ca = len(getattr(a, attr))
        cb = len(getattr(b, attr))
        if ca != cb:
            result.diffs.append(ParamDiff("component", label, str(ca), str(cb)))
