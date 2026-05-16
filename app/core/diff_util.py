from __future__ import annotations

import difflib


def compute_diff(original: str, modified: str) -> str:
    """Return a unified diff between original and modified text."""
    orig_lines = original.splitlines(keepends=True)
    mod_lines = modified.splitlines(keepends=True)

    diff = difflib.unified_diff(
        orig_lines,
        mod_lines,
        fromfile="original.atp",
        tofile="modified.atp",
        lineterm="",
    )
    return "".join(diff)


def has_changes(original: str, modified: str) -> bool:
    return original != modified


def compute_context_diff(original: str, modified: str, context: int = 3) -> list[str]:
    """Return context diff as list of lines, useful for display."""
    orig_lines = original.splitlines()
    mod_lines = modified.splitlines()

    diff = difflib.unified_diff(
        orig_lines,
        mod_lines,
        fromfile="original.atp",
        tofile="modified.atp",
        n=context,
    )
    return list(diff)
