from __future__ import annotations

import argparse
import fnmatch
import os
import shutil
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

ROOT_GENERATED_DIRECTORIES = (
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    "htmlcov",
    "build",
    "dist",
    "output",
)
NESTED_GENERATED_DIRECTORY_NAMES = {"__pycache__"}
GENERATED_FILE_PATTERNS = (
    "*.pyc",
    ".coverage*",
    "manage-*.log",
)
WALK_SKIP_DIRECTORIES = {
    ".git",
    ".github",
    ".venv",
    ".venv-codex",
    "node_modules",
}


def _resolve_repo_root(repo_root: Path) -> Path:
    resolved = repo_root.resolve()
    if not resolved.exists() or not resolved.is_dir():
        raise ValueError(f"Repository root does not exist or is not a directory: {repo_root}")
    return resolved


def _ensure_within_repo(path: Path, repo_root: Path) -> None:
    resolved_path = path.resolve()
    try:
        resolved_path.relative_to(repo_root)
    except ValueError as exc:
        raise ValueError(f"Refusing to delete outside repository root: {path}") from exc


def _relative_key(path: Path, repo_root: Path) -> str:
    return path.resolve().relative_to(repo_root).as_posix()


def _load_tracked_paths(repo_root: Path) -> set[str]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=repo_root,
        check=False,
        capture_output=True,
    )
    if result.returncode != 0:
        return set()
    return {entry.decode("utf-8") for entry in result.stdout.split(b"\0") if entry}


def _has_tracked_descendant(path: Path, repo_root: Path, tracked_paths: set[str]) -> bool:
    relative_path = _relative_key(path, repo_root)
    return any(
        tracked_path == relative_path or tracked_path.startswith(f"{relative_path}/")
        for tracked_path in tracked_paths
    )


def _can_remove_path(path: Path, repo_root: Path, tracked_paths: set[str]) -> bool:
    _ensure_within_repo(path, repo_root)
    return not _has_tracked_descendant(path, repo_root, tracked_paths)


def _iter_walk(repo_root: Path) -> Iterator[tuple[Path, list[str], list[str]]]:
    for current_root, dirnames, filenames in os.walk(repo_root):
        dirnames[:] = [
            dirname
            for dirname in dirnames
            if dirname not in WALK_SKIP_DIRECTORIES and dirname not in ROOT_GENERATED_DIRECTORIES
        ]
        yield Path(current_root), dirnames, filenames


def _collect_untracked_descendants(
    directory: Path,
    repo_root: Path,
    tracked_paths: set[str],
) -> set[Path]:
    candidates: set[Path] = set()
    for current_root, dirnames, filenames in os.walk(directory):
        for filename in filenames:
            candidate = Path(current_root) / filename
            if _can_remove_path(candidate, repo_root, tracked_paths):
                candidates.add(candidate)
        for dirname in dirnames:
            candidate = Path(current_root) / dirname
            if _can_remove_path(candidate, repo_root, tracked_paths):
                candidates.add(candidate)
    return candidates


def collect_generated_artifacts(repo_root: Path = ROOT) -> list[Path]:
    repo_root = _resolve_repo_root(repo_root)
    tracked_paths = _load_tracked_paths(repo_root)
    candidates: set[Path] = set()

    for directory_name in ROOT_GENERATED_DIRECTORIES:
        candidate = repo_root / directory_name
        if not candidate.exists():
            continue
        if _can_remove_path(candidate, repo_root, tracked_paths):
            candidates.add(candidate)
        else:
            candidates.update(_collect_untracked_descendants(candidate, repo_root, tracked_paths))

    for current_root, dirnames, filenames in _iter_walk(repo_root):
        for dirname in dirnames:
            candidate = current_root / dirname
            if dirname in NESTED_GENERATED_DIRECTORY_NAMES and _can_remove_path(
                candidate,
                repo_root,
                tracked_paths,
            ):
                candidates.add(candidate)
        for filename in filenames:
            candidate = current_root / filename
            if any(
                fnmatch.fnmatch(filename, pattern) for pattern in GENERATED_FILE_PATTERNS
            ) and _can_remove_path(candidate, repo_root, tracked_paths):
                candidates.add(candidate)

    return sorted(candidates, key=lambda path: (len(path.parts), str(path)), reverse=True)


def remove_generated_artifact(path: Path, repo_root: Path) -> None:
    _ensure_within_repo(path, repo_root)
    if not path.exists():
        return
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
        return
    path.unlink()


def clean_generated_artifacts(repo_root: Path = ROOT, *, dry_run: bool = False) -> list[Path]:
    repo_root = _resolve_repo_root(repo_root)
    candidates = collect_generated_artifacts(repo_root)
    for candidate in candidates:
        if dry_run:
            _ensure_within_repo(candidate, repo_root)
            continue
        remove_generated_artifact(candidate, repo_root)
    return candidates


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Remove repo-local generated caches, logs, build output, and evidence output."
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=ROOT,
        help="Repository root to clean. Defaults to the lotus-manage checkout.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Count matching generated artifacts without deleting them.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print every matching generated artifact path.",
    )
    args = parser.parse_args(argv)

    try:
        removed = clean_generated_artifacts(args.repo_root, dry_run=args.dry_run)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    action = "Would remove" if args.dry_run else "Removed"
    if args.verbose:
        for path in removed:
            print(path)
    print(f"{action} {len(removed)} generated artifact path(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
