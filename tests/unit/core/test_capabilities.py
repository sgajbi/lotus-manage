import sys
from types import ModuleType

from _pytest.monkeypatch import MonkeyPatch

from src.core.common import capabilities


def test_solver_dependency_flag_matches_component_flags() -> None:
    assert capabilities.has_solver_dependencies() == (
        capabilities.has_optional_dependency("cvxpy")
        and capabilities.has_optional_dependency("numpy")
    )


def test_psycopg_error_type_none_when_driver_missing(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(capabilities, "has_psycopg", lambda: False)
    assert capabilities.psycopg_error_type() is None


def test_psycopg_error_type_from_driver_module(monkeypatch: MonkeyPatch) -> None:
    fake = ModuleType("psycopg")

    class FakeError(Exception):
        pass

    setattr(fake, "Error", FakeError)
    monkeypatch.setattr(capabilities, "has_psycopg", lambda: True)
    monkeypatch.setitem(sys.modules, "psycopg", fake)

    assert capabilities.psycopg_error_type() is FakeError
