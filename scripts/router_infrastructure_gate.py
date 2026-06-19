from __future__ import annotations

import sys
from collections.abc import Iterable
from pathlib import Path


ROUTER_DIR = Path("src/api/routers")
ROUTER_INFRASTRUCTURE_PATTERNS = (
    "from src.infrastructure",
    "import src.infrastructure",
)


def _matching_lines(path: str, text: str, patterns: Iterable[str]) -> list[str]:
    matches: list[str] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        if any(pattern in line for pattern in patterns):
            matches.append(f"{path}:{lineno}: {line.strip()}")
    return matches


def evaluate_router_infrastructure_imports(router_dir: Path = ROUTER_DIR) -> list[str]:
    violations: list[str] = []
    for path in sorted(router_dir.rglob("*.py")):
        violations.extend(
            _matching_lines(path.as_posix(), path.read_text(), ROUTER_INFRASTRUCTURE_PATTERNS)
        )
    return violations


def main() -> int:
    violations = evaluate_router_infrastructure_imports()
    if violations:
        print("Router infrastructure gate failed:")
        print("\n".join(f"- {violation}" for violation in violations))
        return 1
    print("Router infrastructure gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
