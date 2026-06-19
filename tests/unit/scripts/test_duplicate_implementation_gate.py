from __future__ import annotations

from pathlib import Path

from scripts.duplicate_implementation_gate import (
    baseline_group,
    discover_duplicate_groups,
    evaluate_duplicate_baseline,
)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_detects_exact_non_trivial_duplicate_function_bodies(tmp_path: Path) -> None:
    src = tmp_path / "src"
    duplicated_body = """
def first(value: int) -> int:
    result = value + 1
    if result > 10:
        return result
    return 10
"""
    _write(src / "alpha.py", duplicated_body)
    _write(src / "beta.py", duplicated_body.replace("first", "second"))

    groups = discover_duplicate_groups(scan_roots=(src,), min_lines=4)

    assert len(groups) == 1
    assert [occurrence.function for occurrence in groups[0].occurrences] == ["first", "second"]


def test_duplicate_baseline_accepts_current_groups(tmp_path: Path) -> None:
    src = tmp_path / "src"
    duplicated_body = """
def alpha(value: int) -> int:
    result = value + 1
    if result > 10:
        return result
    return 10
"""
    _write(src / "one.py", duplicated_body)
    _write(src / "two.py", duplicated_body.replace("alpha", "beta"))
    groups = discover_duplicate_groups(scan_roots=(src,), min_lines=4)
    baseline = {
        "schema_version": 1,
        "accepted_duplicate_groups": [baseline_group(groups[0])],
    }

    evaluation = evaluate_duplicate_baseline(groups=groups, baseline=baseline)

    assert evaluation.passed
    assert evaluation.new_groups == ()
    assert evaluation.stale_baseline_groups == ()


def test_duplicate_baseline_blocks_new_groups(tmp_path: Path) -> None:
    src = tmp_path / "src"
    duplicated_body = """
def alpha(value: int) -> int:
    result = value + 1
    if result > 10:
        return result
    return 10
"""
    _write(src / "one.py", duplicated_body)
    _write(src / "two.py", duplicated_body.replace("alpha", "beta"))
    groups = discover_duplicate_groups(scan_roots=(src,), min_lines=4)

    evaluation = evaluate_duplicate_baseline(
        groups=groups,
        baseline={"schema_version": 1, "accepted_duplicate_groups": []},
    )

    assert not evaluation.passed
    assert evaluation.new_groups == groups
    assert evaluation.stale_baseline_groups == ()


def test_duplicate_baseline_blocks_stale_accepted_groups(tmp_path: Path) -> None:
    src = tmp_path / "src"
    duplicated_body = """
def alpha(value: int) -> int:
    result = value + 1
    if result > 10:
        return result
    return 10
"""
    _write(src / "one.py", duplicated_body)
    _write(src / "two.py", duplicated_body.replace("alpha", "beta"))
    groups = discover_duplicate_groups(scan_roots=(src,), min_lines=4)
    baseline = {
        "schema_version": 1,
        "accepted_duplicate_groups": [baseline_group(groups[0])],
    }

    evaluation = evaluate_duplicate_baseline(groups=(), baseline=baseline)

    assert not evaluation.passed
    assert evaluation.new_groups == ()
    assert len(evaluation.stale_baseline_groups) == 1
