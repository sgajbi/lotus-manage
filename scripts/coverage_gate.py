from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import coverage
from coverage.results import should_fail_under

# Every lane that uploads coverage-data-* must be named here: the gate
# combines this list, and a lane missing from it is downloaded and silently
# ignored - the combined total then reads a smaller world than CI proved.
DEFAULT_COVERAGE_FILES = (
    ".coverage.unit",
    ".coverage.integration",
    ".coverage.e2e",
    ".coverage.idea-postgres",
)
DEFAULT_FAIL_UNDER = 99.0
REPORT_PRECISION = 2


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Combine Lotus Manage coverage data and enforce the repository coverage floor."
    )
    parser.add_argument(
        "--coverage-dir",
        default=".",
        help="Directory containing coverage files. Defaults to the repository root.",
    )
    parser.add_argument(
        "--coverage-file",
        action="append",
        dest="coverage_files",
        help=(
            "Coverage data file name relative to --coverage-dir. May be repeated. "
            "Defaults to unit, integration, and e2e coverage files."
        ),
    )
    parser.add_argument(
        "--fail-under",
        type=float,
        default=float(os.environ.get("COVERAGE_FAIL_UNDER", DEFAULT_FAIL_UNDER)),
        help="Minimum total coverage percentage. Defaults to COVERAGE_FAIL_UNDER or 99.",
    )
    return parser.parse_args()


def _coverage_paths(coverage_dir: Path, coverage_files: list[str] | None) -> list[Path]:
    file_names = coverage_files or list(DEFAULT_COVERAGE_FILES)
    return [coverage_dir / file_name for file_name in file_names]


def enforce_coverage_gate(
    coverage_dir: Path = Path("."),
    coverage_files: list[str] | None = None,
    fail_under: float = DEFAULT_FAIL_UNDER,
) -> int:
    files = _coverage_paths(coverage_dir, coverage_files)
    missing = [path.as_posix() for path in files if not path.exists()]
    if missing:
        print(f"Missing coverage files: {missing}")
        return 1
    if len(files) == 1:
        cov = coverage.Coverage(data_file=files[0].as_posix())
        cov.load()
    else:
        cov = coverage.Coverage()
        cov.combine([path.as_posix() for path in files])
        cov.save()
    total = cov.report()
    if should_fail_under(total, fail_under, REPORT_PRECISION):
        print(f"Coverage gate failed: {total:.2f} < {fail_under:.2f}")
        return 1
    print(f"Coverage gate passed: {total:.2f}")
    return 0


def main() -> int:
    args = _parse_args()
    return enforce_coverage_gate(
        coverage_dir=Path(args.coverage_dir),
        coverage_files=args.coverage_files,
        fail_under=args.fail_under,
    )


if __name__ == "__main__":
    sys.exit(main())
