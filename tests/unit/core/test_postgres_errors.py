import builtins

from src.core.common.postgres_errors import postgres_connection_exception_types


def test_postgres_connection_exception_types_include_builtin_connection_failures(
    monkeypatch,
) -> None:
    original_import = builtins.__import__

    def _import_with_psycopg_missing(name, *args, **kwargs):
        if name == "psycopg":
            raise ImportError("psycopg unavailable in test")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _import_with_psycopg_missing)

    exception_types = postgres_connection_exception_types()

    assert ConnectionError in exception_types
    assert OSError in exception_types
    assert TimeoutError in exception_types
    assert TypeError in exception_types
    assert ValueError in exception_types
