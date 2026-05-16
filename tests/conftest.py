"""Shared fixtures for Olivas Power System Studio tests."""
from __future__ import annotations

from pathlib import Path

import pytest

from app.core.parser import parse_file
from app.core.project_model import AtpProject

# Reference ATP file used across all test modules
REF_FILE = str(Path(__file__).parent.parent / "trt_all_motors_dt_ea.atp")


@pytest.fixture(scope="session")
def ref_project() -> AtpProject:
    """Parse the reference ATP file once per test session."""
    return parse_file(REF_FILE)


@pytest.fixture(autouse=True)
def _commercial_tier_override():
    """
    v4.1.0 commercial Sprint 1: garante tier 'enterprise' durante
    testes para que decorators @requires_feature não bloqueiem.

    Testes que precisam validar o gating real (test_pp_v4_1_0_*)
    chamam ``set_tier_override(None)`` explicitamente em
    ``setup_method``, sobrescrevendo este default.
    """
    from app.commercial.feature_gates import set_tier_override

    set_tier_override("enterprise")
    yield
    set_tier_override(None)
