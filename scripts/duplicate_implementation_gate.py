from __future__ import annotations

import argparse
import ast
import hashlib
import json
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASELINE_PATH = REPO_ROOT / "quality" / "duplicate_implementation_baseline.json"
DEFAULT_REPORT_PATH = REPO_ROOT / "quality" / "duplicate_code_inventory.md"
DEFAULT_SCAN_ROOTS = ("src", "scripts")
DEFAULT_MIN_LINES = 8
BASELINE_SCHEMA_VERSION = 1
EXCLUDED_DIR_NAMES = {
    "__pycache__",
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    ".venv-codex",
    "output",
}


@dataclass(frozen=True)
class DuplicateOccurrence:
    path: str
    function: str
    line: int
    lines: int

    @property
    def identity(self) -> str:
        return f"{self.path}:{self.function}"


@dataclass(frozen=True)
class DuplicateGroup:
    fingerprint: str
    occurrences: tuple[DuplicateOccurrence, ...]

    @property
    def identity(self) -> str:
        occurrence_ids = ",".join(occurrence.identity for occurrence in self.occurrences)
        return f"{self.fingerprint}:{occurrence_ids}"


@dataclass(frozen=True)
class DuplicateEvaluation:
    groups: tuple[DuplicateGroup, ...]
    new_groups: tuple[DuplicateGroup, ...]
    stale_baseline_groups: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return not self.new_groups and not self.stale_baseline_groups


def _relative_path(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def _python_paths(scan_roots: tuple[Path, ...]) -> list[Path]:
    paths: list[Path] = []
    for root in scan_roots:
        for path in root.rglob("*.py"):
            if any(part in EXCLUDED_DIR_NAMES for part in path.parts):
                continue
            paths.append(path)
    return sorted(paths)


def _line_count(node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    return getattr(node, "end_lineno", node.lineno) - node.lineno + 1


def _normalized_function_dump(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    clone = ast.fix_missing_locations(ast.parse(ast.unparse(node))).body[0]
    if not isinstance(clone, ast.FunctionDef | ast.AsyncFunctionDef):
        raise TypeError("Expected a parsed function clone")
    clone.name = "<function>"
    clone.decorator_list = []
    clone.returns = None
    for child in ast.walk(clone):
        for attribute in ("lineno", "col_offset", "end_lineno", "end_col_offset"):
            if hasattr(child, attribute):
                setattr(child, attribute, None)
    return ast.dump(clone, include_attributes=False)


def _fingerprint(normalized_dump: str) -> str:
    return hashlib.sha256(normalized_dump.encode("utf-8")).hexdigest()


def discover_duplicate_groups(
    *,
    scan_roots: tuple[Path, ...] | None = None,
    min_lines: int = DEFAULT_MIN_LINES,
) -> tuple[DuplicateGroup, ...]:
    roots = scan_roots or tuple(REPO_ROOT / root for root in DEFAULT_SCAN_ROOTS)
    occurrences_by_fingerprint: dict[str, list[DuplicateOccurrence]] = defaultdict(list)
    for path in _python_paths(roots):
        text = path.read_text(encoding="utf-8")
        try:
            tree = ast.parse(text)
        except SyntaxError as exc:
            raise ValueError(f"Could not parse {path.as_posix()}: {exc}") from exc
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                continue
            lines = _line_count(node)
            if lines < min_lines:
                continue
            normalized_dump = _normalized_function_dump(node)
            occurrences_by_fingerprint[_fingerprint(normalized_dump)].append(
                DuplicateOccurrence(
                    path=_relative_path(path)
                    if path.is_relative_to(REPO_ROOT)
                    else path.as_posix(),
                    function=node.name,
                    line=node.lineno,
                    lines=lines,
                )
            )
    groups = [
        DuplicateGroup(
            fingerprint=fingerprint,
            occurrences=tuple(sorted(occurrences, key=lambda item: item.identity)),
        )
        for fingerprint, occurrences in occurrences_by_fingerprint.items()
        if len(occurrences) > 1
    ]
    return tuple(sorted(groups, key=lambda group: group.identity))


def _baseline_group_id(group: dict[str, Any]) -> str:
    occurrence_ids = ",".join(sorted(str(item) for item in group["occurrence_identities"]))
    return f"{group['fingerprint']}:{occurrence_ids}"


def baseline_group(group: DuplicateGroup) -> dict[str, Any]:
    return {
        "fingerprint": group.fingerprint,
        "occurrence_identities": [occurrence.identity for occurrence in group.occurrences],
        "reason": "Current exact duplicate implementation baseline; future work must remove or consolidate this group before changing the baseline.",
    }


def build_baseline(groups: tuple[DuplicateGroup, ...], *, min_lines: int) -> dict[str, Any]:
    return {
        "schema_version": BASELINE_SCHEMA_VERSION,
        "scan_roots": list(DEFAULT_SCAN_ROOTS),
        "min_lines": min_lines,
        "accepted_duplicate_groups": [baseline_group(group) for group in groups],
    }


def load_baseline(path: Path = DEFAULT_BASELINE_PATH) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(
            f"{path.relative_to(REPO_ROOT).as_posix()} is missing. "
            "Run python scripts/duplicate_implementation_gate.py --update-baseline."
        )
    baseline = cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))
    if baseline.get("schema_version") != BASELINE_SCHEMA_VERSION:
        raise ValueError(
            f"Unsupported duplicate baseline schema version: {baseline.get('schema_version')}"
        )
    return baseline


def evaluate_duplicate_baseline(
    *,
    groups: tuple[DuplicateGroup, ...],
    baseline: dict[str, Any],
) -> DuplicateEvaluation:
    accepted_ids = {
        _baseline_group_id(group) for group in baseline.get("accepted_duplicate_groups", [])
    }
    current_ids = {group.identity for group in groups}
    new_groups = tuple(group for group in groups if group.identity not in accepted_ids)
    stale_baseline_groups = tuple(sorted(accepted_ids - current_ids))
    return DuplicateEvaluation(
        groups=groups,
        new_groups=new_groups,
        stale_baseline_groups=stale_baseline_groups,
    )


def build_inventory_report(groups: tuple[DuplicateGroup, ...], *, min_lines: int) -> str:
    lines = [
        "# lotus-manage Duplicate Implementation Inventory",
        "",
        "- Detector: exact normalized Python function-body duplicates.",
        f"- Scope: `{', '.join(DEFAULT_SCAN_ROOTS)}`.",
        f"- Minimum function size: `{min_lines}` lines.",
        "- Gate posture: active non-regression gate via `make duplicate-implementation-gate`; existing groups are explicitly baselined and future exact duplicate groups fail.",
        "",
        "## Current Duplicate Groups",
        "",
    ]
    if not groups:
        lines.append("No exact duplicate implementation groups found.")
    for index, group in enumerate(groups, start=1):
        lines.extend(
            [
                f"### Group {index}",
                "",
                f"- Fingerprint: `{group.fingerprint}`",
                "",
                "| File | Function | Line | Lines |",
                "| --- | --- | --- | --- |",
            ]
        )
        for occurrence in group.occurrences:
            lines.append(
                f"| `{occurrence.path}` | `{occurrence.function}` | {occurrence.line} | {occurrence.lines} |"
            )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def write_baseline(path: Path, groups: tuple[DuplicateGroup, ...], *, min_lines: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(build_baseline(groups, min_lines=min_lines), indent=2) + "\n")


def write_report(path: Path, groups: tuple[DuplicateGroup, ...], *, min_lines: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(build_inventory_report(groups, min_lines=min_lines), encoding="utf-8")


def _print_group(group: DuplicateGroup) -> None:
    print(f"- fingerprint {group.fingerprint}")
    for occurrence in group.occurrences:
        print(
            f"  - {occurrence.path}:{occurrence.line} "
            f"{occurrence.function} ({occurrence.lines} lines)"
        )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Detect exact duplicate first-party Python implementation hotspots."
    )
    parser.add_argument("--min-lines", type=int, default=DEFAULT_MIN_LINES)
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE_PATH)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--update-baseline", action="store_true")
    parser.add_argument("--write-report", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    groups = discover_duplicate_groups(min_lines=args.min_lines)
    if args.update_baseline:
        write_baseline(args.baseline, groups, min_lines=args.min_lines)
        write_report(args.report, groups, min_lines=args.min_lines)
        print(f"Updated duplicate implementation baseline with {len(groups)} accepted group(s).")
        return 0
    if args.write_report:
        write_report(args.report, groups, min_lines=args.min_lines)
        print(f"Wrote {args.report.relative_to(REPO_ROOT).as_posix()}")
        return 0

    baseline = load_baseline(args.baseline)
    evaluation = evaluate_duplicate_baseline(groups=groups, baseline=baseline)
    if evaluation.passed:
        print(
            "Duplicate implementation gate passed: "
            f"{len(evaluation.groups)} accepted exact duplicate group(s), no new groups."
        )
        return 0
    print("Duplicate implementation gate failed.")
    if evaluation.new_groups:
        print("New exact duplicate implementation group(s):")
        for group in evaluation.new_groups:
            _print_group(group)
    if evaluation.stale_baseline_groups:
        print("Stale accepted duplicate baseline group(s); remove or refresh the baseline:")
        for group_id in evaluation.stale_baseline_groups:
            print(f"- {group_id}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
