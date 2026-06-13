from __future__ import annotations

import sys
from collections.abc import Iterable
from pathlib import Path


SERVICE_DIR = Path("src/api/services")
SERVICE_LEAKAGE_PATTERNS = (
    "from src.api.routers",
    "import src.api.routers",
    "HTTPException",
    "status.HTTP",
    "from fastapi",
    "import fastapi",
    "from starlette",
    "import starlette",
)


def _matching_lines(path: str, text: str, patterns: Iterable[str]) -> list[str]:
    matches: list[str] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        if any(pattern in line for pattern in patterns):
            matches.append(f"{path}:{lineno}: {line.strip()}")
    return matches


def evaluate_service_boundary(service_dir: Path = SERVICE_DIR) -> list[str]:
    violations: list[str] = []
    for path in sorted(service_dir.rglob("*.py")):
        violations.extend(
            _matching_lines(path.as_posix(), path.read_text(), SERVICE_LEAKAGE_PATTERNS)
        )
    return violations


def main() -> int:
    violations = evaluate_service_boundary()
    if violations:
        print("Service boundary gate failed:")
        print("\n".join(f"- {violation}" for violation in violations))
        return 1
    print("Service boundary gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
