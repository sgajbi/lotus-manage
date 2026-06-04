import sys
from types import ModuleType

import pytest
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


def test_psycopg_error_type_none_when_driver_import_fails(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(capabilities, "has_psycopg", lambda: True)

    def missing_driver() -> ModuleType:
        raise ImportError("psycopg unavailable")

    monkeypatch.setattr(capabilities, "_import_psycopg", missing_driver)

    assert capabilities.psycopg_error_type() is None


def test_psycopg_error_type_does_not_hide_non_import_failures(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(capabilities, "has_psycopg", lambda: True)

    def broken_driver() -> ModuleType:
        raise RuntimeError("psycopg import side effect failed")

    monkeypatch.setattr(capabilities, "_import_psycopg", broken_driver)

    with pytest.raises(RuntimeError, match="psycopg import side effect failed"):
        capabilities.psycopg_error_type()


def test_psycopg_error_type_from_driver_module(monkeypatch: MonkeyPatch) -> None:
    fake = ModuleType("psycopg")

    class FakeError(Exception):
        pass

    setattr(fake, "Error", FakeError)
    monkeypatch.setattr(capabilities, "has_psycopg", lambda: True)
    monkeypatch.setitem(sys.modules, "psycopg", fake)

    assert capabilities.psycopg_error_type() is FakeError
