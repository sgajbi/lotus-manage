from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from scripts.clean_generated_artifacts import (
    clean_generated_artifacts,
    remove_generated_artifact,
)


def _touch(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("generated", encoding="utf-8")


def test_clean_generated_artifacts_removes_allowed_generated_paths(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    source_files = [
        repo_root / ".git" / "HEAD",
        repo_root / "src" / "core" / "service.py",
        repo_root / "docs" / "README.md",
        repo_root / "wiki" / "Home.md",
        repo_root / "contracts" / "domain-data-products" / "lotus-manage-products.v1.json",
    ]
    generated_files = [
        repo_root / ".pytest_cache" / "v" / "cache" / "nodeids",
        repo_root / ".ruff_cache" / "cache",
        repo_root / ".mypy_cache" / "3.13" / "module.meta.json",
        repo_root / "htmlcov" / "index.html",
        repo_root / "build" / "artifact.whl",
        repo_root / "dist" / "artifact.tar.gz",
        repo_root / "output" / "live-api" / "evidence.json",
        repo_root / ".coverage",
        repo_root / ".coverage.unit",
        repo_root / "manage-local.log",
        repo_root / "scripts" / "__pycache__" / "gate.cpython-313.pyc",
        repo_root / "src" / "core" / "__pycache__" / "service.cpython-313.pyc",
        repo_root / "tests" / "unit" / "__pycache__" / "test_service.cpython-313.pyc",
    ]
    for path in source_files + generated_files:
        _touch(path)

    removed = clean_generated_artifacts(repo_root)

    assert removed != []
    for path in generated_files:
        assert not path.exists()
    for cache_dir in repo_root.rglob("__pycache__"):
        assert not cache_dir.exists()
    for path in source_files:
        assert path.exists()


def test_clean_generated_artifacts_preserves_tracked_output_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    tracked_output = repo_root / "output" / "retained" / "critical-review.json"
    untracked_output = repo_root / "output" / "live-api" / "evidence.json"
    untracked_cache = repo_root / "src" / "__pycache__" / "module.pyc"
    _touch(tracked_output)
    _touch(untracked_output)
    _touch(untracked_cache)

    monkeypatch.chdir(repo_root)
    subprocess.run(["git", "init", "--quiet"], cwd=repo_root, check=True)
    subprocess.run(
        ["git", "add", "output/retained/critical-review.json"],
        cwd=repo_root,
        check=True,
    )

    removed = clean_generated_artifacts(repo_root)

    assert tracked_output.exists()
    assert untracked_output in removed
    assert not untracked_output.exists()
    assert untracked_cache in removed
    assert not untracked_cache.exists()


def test_clean_generated_artifacts_dry_run_preserves_matches(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    _touch(repo_root / "output" / "live-api" / "evidence.json")
    _touch(repo_root / "src" / "__pycache__" / "module.pyc")

    matches = clean_generated_artifacts(repo_root, dry_run=True)

    assert {path.name for path in matches} >= {"output", "__pycache__"}
    assert (repo_root / "output" / "live-api" / "evidence.json").exists()
    assert (repo_root / "src" / "__pycache__" / "module.pyc").exists()


def test_remove_generated_artifact_refuses_outside_repo_root(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    outside = tmp_path / "outside" / ".coverage"
    repo_root.mkdir()
    _touch(outside)

    with pytest.raises(ValueError, match="outside repository root"):
        remove_generated_artifact(outside, repo_root.resolve())

    assert outside.exists()
