"""Collection-time prerequisite for test suites that prove solver behavior."""

import cvxpy
import numpy


def require_solver_test_dependencies() -> tuple[object, object]:
    """Make the required imports explicit at each solver-proof surface."""
    return cvxpy, numpy
