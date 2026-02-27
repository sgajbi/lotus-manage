from importlib.util import find_spec
def has_optional_dependency(module_name: str) -> bool:
    return find_spec(module_name) is not None


def has_solver_dependencies() -> bool:
    return has_optional_dependency("cvxpy") and has_optional_dependency("numpy")


def has_psycopg() -> bool:
    return has_optional_dependency("psycopg")


def psycopg_error_type() -> type[BaseException] | None:
    if not has_psycopg():
        return None
    try:
        import psycopg
    except Exception:
        return None
    return getattr(psycopg, "Error", None)


__all__ = [
    "has_optional_dependency",
    "has_solver_dependencies",
    "has_psycopg",
    "psycopg_error_type",
]
