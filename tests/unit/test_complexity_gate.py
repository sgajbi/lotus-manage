from __future__ import annotations

import ast
import json
import os
import subprocess
from pathlib import Path

import pytest

from scripts import complexity_gate as gate


BASE_SHA = "a" * 40
HEAD_SHA = "b" * 40


def function_source(branches: int, name: str = "evaluate") -> str:
    body = "".join(
        f"    if value == {index}:\n        return {index}\n" for index in range(branches)
    )
    return f"def {name}(value):\n{body}    return None\n"


def measure(source: str) -> tuple[gate.FunctionComplexity, ...]:
    return gate.measure_sources({"src/policy.py": source}, gate.radon_scanner())


@pytest.mark.parametrize("branches", [0, 9])
def test_new_functions_accept_a_and_b_ranks(branches: int) -> None:
    result = gate.evaluate(measure(function_source(0, "old")), measure(function_source(branches)))
    assert result.violations == ()
    assert result.legacy_debt == ()


def test_new_c_rank_function_fails_even_when_other_legacy_debt_improves() -> None:
    baseline = measure(function_source(15, "old"))
    current = measure(function_source(11, "old") + function_source(10, "new"))
    result = gate.evaluate(baseline, current)
    assert len(result.violations) == 1
    assert "new function/method" in result.violations[0]
    assert "CC 11 exceeds 10" in result.violations[0]
    assert [metric.complexity for metric in result.legacy_debt] == [12]


@pytest.mark.parametrize("current_branches", [10, 12])
def test_existing_high_complexity_is_explicit_debt_when_unchanged_or_improved(
    current_branches: int,
) -> None:
    result = gate.evaluate(measure(function_source(12)), measure(function_source(current_branches)))
    assert result.violations == ()
    assert [metric.complexity for metric in result.legacy_debt] == [current_branches + 1]


@pytest.mark.parametrize("old_branches,new_branches", [(12, 13), (9, 10)])
def test_existing_complexity_cannot_increase_above_the_exact_policy_ceiling(
    old_branches: int, new_branches: int
) -> None:
    result = gate.evaluate(
        measure(function_source(old_branches)), measure(function_source(new_branches))
    )
    assert len(result.violations) == 1
    assert f"baseline CC {old_branches + 1}" in result.violations[0]
    assert not result.legacy_debt


def test_improvement_to_b_rank_retires_legacy_debt() -> None:
    result = gate.evaluate(measure(function_source(12)), measure(function_source(9)))
    assert result == gate.Evaluation((), ())


def test_renamed_or_moved_high_function_is_new_and_cannot_inherit_legacy_debt() -> None:
    old = measure(function_source(12, "old"))
    renamed = measure(function_source(12, "new"))
    moved = gate.measure_sources({"src/moved.py": function_source(12, "old")}, gate.radon_scanner())
    assert gate.evaluate(old, renamed).violations
    assert gate.evaluate(old, moved).violations


def test_radon_scores_methods_async_nested_functions_and_nested_class_methods() -> None:
    metrics = measure(
        "class Policy:\n"
        "    def check(self, value):\n"
        "        def local(flag):\n"
        "            if flag: return 1\n"
        "        class Nested:\n"
        "            async def validate(self, flag):\n"
        "                if flag: return 2\n"
        "        return local(value)\n"
        "    @property\n"
        "    def value(self): return 1\n"
        "    @value.setter\n"
        "    def value(self, value): pass\n"
    )
    assert {metric.name: metric.complexity for metric in metrics} == {
        "Policy.check": 1,
        "Policy.check.local": 2,
        "Policy.check.Nested.validate": 2,
        "Policy.value": 1,
        "Policy.value#2": 1,
    }
    assert gate.evaluate(metrics, metrics).legacy_debt == ()


def test_high_class_aggregate_does_not_reject_b_rank_methods() -> None:
    source = "class Policy:\n" + "\n".join(
        "\n".join(f"    {line}" for line in function_source(9, f"method_{index}").splitlines())
        for index in range(3)
    )
    blocks = gate.radon_scanner()(ast.parse(source))
    assert blocks[0].complexity > 10
    current = measure(source)
    assert [metric.complexity for metric in current] == [10, 10, 10]
    result = gate.evaluate(measure(function_source(0, "old")), current)
    assert result == gate.Evaluation((), ())


@pytest.mark.parametrize("texts", [{}, {"src/empty.py": ""}, {"src/data.py": "VALUE = 1"}])
def test_empty_function_population_fails_closed(texts: dict[str, str]) -> None:
    with pytest.raises(gate.GateError, match="empty|no functions"):
        gate.measure_sources(texts, gate.radon_scanner())


def test_malformed_syntax_fails_closed() -> None:
    with pytest.raises(SyntaxError):
        measure("def broken(:\n")


def test_missing_source_directory_fails_closed(tmp_path: Path) -> None:
    with pytest.raises(gate.GateError, match="missing"):
        gate.current_sources(tmp_path)


def test_source_collection_cannot_hide_high_complexity_in_dot_paths(tmp_path: Path) -> None:
    path = tmp_path / "src/.hidden/policy.py"
    path.parent.mkdir(parents=True)
    path.write_text(function_source(10), encoding="utf-8")
    texts = gate.current_sources(tmp_path)
    assert set(texts) == {"src/.hidden/policy.py"}
    current = gate.measure_sources(texts, gate.radon_scanner())
    assert gate.evaluate(measure(function_source(0, "old")), current).violations


def test_missing_radon_measurement_fails_closed() -> None:
    with pytest.raises(gate.GateError, match="uniquely measure"):
        gate.measure_sources({"src/policy.py": function_source(1)}, lambda _node: [])


@pytest.mark.parametrize("score", [0, -1, True, "2", None])
def test_invalid_scanner_score_fails_closed(score: object) -> None:
    class Block:
        lineno = 1
        col_offset = 0
        name = "evaluate"
        complexity = score

    with pytest.raises(gate.GateError, match="Invalid Radon score"):
        gate.measure_sources({"src/policy.py": function_source(1)}, lambda _node: [Block()])


def baseline_environment(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    *,
    branch: str = "feature/test",
    dirty: bool = False,
    recorded: str | None = BASE_SHA,
) -> None:
    for name in ("GITHUB_BASE_REF", "GITHUB_REF_NAME", "LOTUS_QUALITY_REF_NAME"):
        monkeypatch.delenv(name, raising=False)
    if recorded is not None:
        (tmp_path / "quality").mkdir(exist_ok=True)
        (tmp_path / "quality/refactor_health_report.md").write_text(
            f"{gate.BASELINE_PREFIX}{recorded}`\n", encoding="utf-8"
        )

    def fake_git(_root: Path, *args: str) -> str:
        if args == ("rev-parse", "--abbrev-ref", "HEAD"):
            return branch
        if args == ("status", "--porcelain"):
            return " M src/policy.py" if dirty else ""
        if args == ("merge-base", HEAD_SHA, BASE_SHA):
            return BASE_SHA
        if args == ("merge-base", HEAD_SHA, HEAD_SHA):
            return HEAD_SHA
        if args[:2] == ("rev-parse", "--verify"):
            ref = args[2].removesuffix("^{commit}")
            if ref == "HEAD":
                return HEAD_SHA
            if ref in {BASE_SHA, "origin/main", "origin/release", "HEAD^"}:
                return BASE_SHA
            if ref == HEAD_SHA:
                return HEAD_SHA
        raise subprocess.CalledProcessError(1, ["git", *args])

    monkeypatch.setattr(gate, "git", fake_git)
    monkeypatch.setattr(gate, "source_differs_from_commit", lambda _root, _ref: dirty)


@pytest.mark.parametrize(
    "branch,dirty",
    [("feature/test", False), ("feature/test", True), ("main", False), ("main", True)],
)
def test_local_feature_and_main_resolve_immutable_nonself_baselines(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, branch: str, dirty: bool
) -> None:
    baseline_environment(monkeypatch, tmp_path, branch=branch, dirty=dirty)
    expected = HEAD_SHA if branch == "main" and dirty else BASE_SHA
    assert gate.select_baseline(tmp_path) == expected


def test_pull_request_uses_base_branch_instead_of_detached_merge_head(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    baseline_environment(monkeypatch, tmp_path, branch="HEAD", recorded=None)
    monkeypatch.setenv("GITHUB_BASE_REF", "release")
    monkeypatch.setenv("GITHUB_REF_NAME", "123/merge")
    assert gate.select_baseline(tmp_path) == BASE_SHA


def test_feature_measures_actual_upstream_tip_after_main_improves_legacy_complexity(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    baseline_environment(monkeypatch, tmp_path, dirty=True)
    previous_git = gate.git
    upstream = "c" * 40

    def advanced_git(root: Path, *args: str) -> str:
        if args == ("rev-parse", "--verify", "origin/main^{commit}"):
            return upstream
        if args == ("merge-base", HEAD_SHA, upstream):
            return BASE_SHA
        if args == ("rev-parse", "--verify", f"{upstream}^{{commit}}"):
            return upstream
        return previous_git(root, *args)

    monkeypatch.setattr(gate, "git", advanced_git)
    assert gate.select_baseline(tmp_path) == upstream
    old_recorded = measure(function_source(12))
    improved_main = measure(function_source(10))
    reintroduced = measure(function_source(12))
    assert gate.evaluate(old_recorded, reintroduced).violations == ()
    assert gate.evaluate(improved_main, reintroduced).violations


@pytest.mark.parametrize("branch", ["feature/test", "main"])
def test_absent_report_uses_existing_origin_or_parent_policy(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, branch: str
) -> None:
    baseline_environment(monkeypatch, tmp_path, branch=branch, recorded=None)
    assert gate.select_baseline(tmp_path) == BASE_SHA


@pytest.mark.parametrize("ref", [HEAD_SHA, "HEAD"])
def test_explicit_self_comparison_is_rejected(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, ref: str
) -> None:
    baseline_environment(monkeypatch, tmp_path)
    with pytest.raises(gate.GateError, match="itself"):
        gate.select_baseline(tmp_path, ref)


def test_recorded_provenance_cannot_replace_actual_main_parent_baseline(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    baseline_environment(monkeypatch, tmp_path, branch="main", recorded=HEAD_SHA)
    assert gate.select_baseline(tmp_path) == BASE_SHA


@pytest.mark.parametrize("recorded", ["origin/main", "", "c" * 40])
def test_malformed_or_unresolved_recorded_baseline_cannot_silently_fall_back(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, recorded: str
) -> None:
    baseline_environment(monkeypatch, tmp_path, dirty=True, recorded=recorded)
    with pytest.raises((gate.GateError, subprocess.CalledProcessError)):
        gate.select_baseline(tmp_path)


def test_missing_baseline_and_nonancestor_fail_closed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    baseline_environment(monkeypatch, tmp_path)
    with pytest.raises(subprocess.CalledProcessError):
        gate.select_baseline(tmp_path, "missing")
    previous_git = gate.git

    def divergent_git(root: Path, *args: str) -> str:
        return HEAD_SHA if args[0] == "merge-base" else previous_git(root, *args)

    monkeypatch.setattr(gate, "git", divergent_git)
    with pytest.raises(gate.GateError, match="ancestor"):
        gate.select_baseline(tmp_path, BASE_SHA)


@pytest.mark.parametrize("resolved", ["", "origin/main", "a" * 39, "a" * 41])
def test_git_resolution_must_return_one_immutable_commit(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, resolved: str
) -> None:
    monkeypatch.setattr(gate, "git", lambda _root, *_args: resolved)
    with pytest.raises(gate.GateError, match="immutable commit"):
        gate.resolve_commit(tmp_path, "origin/main")


@pytest.mark.parametrize("branches,expected", [(9, 0), (10, 1)])
def test_cli_returns_real_pass_fail_without_writing_artifacts(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    branches: int,
    expected: int,
) -> None:
    monkeypatch.setattr(gate, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(gate, "select_baseline", lambda _root, _ref: BASE_SHA)
    monkeypatch.setattr(gate, "released_revision_violations", lambda _root, _scanner: ())
    monkeypatch.setattr(
        gate, "baseline_sources", lambda _root, _ref: {"src/old.py": function_source(0, "old")}
    )
    monkeypatch.setattr(
        gate, "current_sources", lambda _root: {"src/new.py": function_source(branches)}
    )
    before = list(tmp_path.rglob("*"))
    assert gate.main([]) == expected
    assert list(tmp_path.rglob("*")) == before
    assert ("FAIL " in capsys.readouterr().out) is bool(expected)


@pytest.mark.parametrize("failure", ["missing-baseline", "empty-baseline", "syntax", "scanner"])
def test_cli_input_or_scanner_failure_is_nonzero(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, failure: str
) -> None:
    monkeypatch.setattr(gate, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(gate, "select_baseline", lambda _root, _ref: BASE_SHA)
    monkeypatch.setattr(
        gate, "baseline_sources", lambda _root, _ref: {"src/old.py": function_source(0)}
    )
    monkeypatch.setattr(gate, "current_sources", lambda _root: {"src/new.py": function_source(0)})
    if failure == "empty-baseline":
        monkeypatch.setattr(gate, "baseline_sources", lambda _root, _ref: {})
    elif failure == "syntax":
        monkeypatch.setattr(gate, "current_sources", lambda _root: {"src/new.py": "def broken(:"})
    else:

        def fail(*_args: object) -> list[ast.AST]:
            raise RuntimeError("unavailable")

        monkeypatch.setattr(
            gate, "select_baseline" if failure == "missing-baseline" else "radon_scanner", fail
        )
    assert gate.main([]) == 1


def test_policy_cannot_be_relaxed_with_threshold_or_allowlist_arguments() -> None:
    with pytest.raises(SystemExit) as exc:
        gate.main(["--max-new-complexity", "20"])
    assert exc.value.code == 2


class GitFixture:
    """Owned, remote-free synthetic Git data; never operates on the Lotus checkout."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.root.mkdir()
        self.hooks = self.root / "empty-hooks"
        self.hooks.mkdir()
        self.receipts: list[dict[str, object]] = []
        self.git("init", "--initial-branch=main")
        (self.root / ".git/info/exclude").write_text(
            "empty-hooks/\nfixture-commands.json\npush-event.json\n", encoding="utf-8"
        )
        (self.root / "src").mkdir()

    def git(self, *args: str) -> str:
        assert self.root.name == "synthetic-git-repository"
        env = dict(os.environ, GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull)
        command = [
            "git",
            "-c",
            "user.name=Complexity Policy Fixture",
            "-c",
            "user.email=complexity-fixture@example.invalid",
            "-c",
            "commit.gpgsign=false",
            "-c",
            f"core.hooksPath={self.hooks}",
            *args,
        ]
        result = subprocess.run(command, cwd=self.root, env=env, capture_output=True, text=True)
        self.receipts.append(
            {
                "command": command,
                "cwd": str(self.root),
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }
        )
        (self.root / "fixture-commands.json").write_text(
            json.dumps(self.receipts, indent=2), encoding="utf-8"
        )
        result.check_returncode()
        return result.stdout.strip()

    def source(self, branches: int, name: str = "evaluate") -> None:
        (self.root / "src/policy.py").write_text(function_source(branches, name), encoding="utf-8")

    def commit(self, label: str) -> str:
        self.git("add", "--", "src")
        self.git("commit", "--message", f"synthetic fixture: {label}")
        return self.git("rev-parse", "HEAD")

    def record(self, commit: str) -> None:
        (self.root / "quality").mkdir(exist_ok=True)
        (self.root / "quality/refactor_health_report.md").write_text(
            f"{gate.BASELINE_PREFIX}{commit}`\n", encoding="utf-8"
        )


@pytest.fixture
def real_git(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> GitFixture:
    authorized_root = Path(os.environ.get("LOTUS_COMPLEXITY_FIXTURE_ROOT", str(tmp_path))).resolve()
    assert tmp_path.resolve().is_relative_to(authorized_root)
    fixture = GitFixture(tmp_path / "synthetic-git-repository")
    for name in (
        "GITHUB_BASE_REF",
        "GITHUB_REF_NAME",
        "LOTUS_QUALITY_REF_NAME",
        "GITHUB_EVENT_PATH",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(gate, "REPO_ROOT", fixture.root)
    return fixture


@pytest.mark.parametrize("branches,expected", [(9, 0), (10, 1)])
def test_real_equal_tip_feature_accepts_dirty_b_and_rejects_dirty_c(
    real_git: GitFixture, branches: int, expected: int
) -> None:
    real_git.source(0, "old")
    baseline = real_git.commit("original source")
    real_git.git("branch", "origin/main", baseline)
    real_git.git("switch", "-c", "feature/test")
    real_git.source(branches, "new")
    assert gate.resolve_commit(real_git.root, "HEAD") == gate.resolve_commit(
        real_git.root, "origin/main"
    )
    assert gate.source_differs_from_commit(real_git.root, baseline)
    assert gate.select_baseline(real_git.root) == baseline
    assert gate.main([]) == expected


def test_real_identical_source_and_explicit_self_fail_closed(real_git: GitFixture) -> None:
    real_git.source(0)
    baseline = real_git.commit("original source")
    real_git.git("branch", "origin/main", baseline)
    real_git.git("switch", "-c", "feature/test")
    assert gate.main([]) == 1
    real_git.source(1)
    assert gate.main(["--base-ref", "HEAD"]) == 1
    assert gate.main(["--base-ref", "missing-ref"]) == 1


@pytest.mark.parametrize("pr", [False, True])
def test_real_divergent_local_and_pr_use_improved_target_not_stale_recorded_debt(
    real_git: GitFixture, monkeypatch: pytest.MonkeyPatch, pr: bool
) -> None:
    real_git.source(12)
    stale = real_git.commit("legacy CC13")
    real_git.git("branch", "feature/test", stale)
    real_git.source(10)
    improved = real_git.commit("main improves to CC11")
    real_git.git("branch", "origin/main", improved)
    real_git.git("switch", "feature/test")
    real_git.source(12)
    (real_git.root / "src/feature.py").write_text(function_source(0, "feature"), encoding="utf-8")
    feature = real_git.commit("feature retains stale CC13")
    real_git.record(stale)
    real_git.git("add", "--", "quality")
    feature = real_git.commit("record exact stale report provenance")
    assert real_git.git("status", "--porcelain") == ""
    if pr:
        monkeypatch.setenv("GITHUB_BASE_REF", "main")
        monkeypatch.setenv("GITHUB_REF_NAME", "123/merge")
    assert real_git.git("merge-base", improved, feature) == stale
    assert gate.select_baseline(real_git.root) == improved
    scanner = gate.radon_scanner()
    before = gate.measure_sources(gate.baseline_sources(real_git.root, stale), scanner)
    current = gate.measure_sources(gate.current_sources(real_git.root), scanner)
    assert not gate.evaluate(before, current).violations
    assert gate.main([]) == 1


def test_main_release_audit_catches_intermediate_rebased_violation_even_when_final_source_is_fixed(
    real_git: GitFixture,
) -> None:
    real_git.source(0, "old")
    release_base = real_git.commit("reviewed release baseline")
    real_git.record(release_base)
    real_git.source(10, "new")
    bad_revision = real_git.commit("intermediate new CC11")
    real_git.source(9, "new")
    real_git.commit("final new CC10")
    scanner = gate.radon_scanner()
    assert not gate.evaluate(
        gate.measure_sources(gate.baseline_sources(real_git.root, bad_revision), scanner),
        gate.measure_sources(gate.current_sources(real_git.root), scanner),
    ).violations
    violations = gate.released_revision_violations(real_git.root, scanner)
    assert len(violations) == 1 and bad_revision in violations[0]
    assert gate.main([]) == 1


def test_main_valid_revisions_and_push_before_provenance_pass(
    real_git: GitFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    real_git.source(0, "old")
    release_base = real_git.commit("reviewed release baseline")
    real_git.record(release_base)
    real_git.source(8, "new")
    real_git.commit("new CC9")
    real_git.source(9, "new")
    real_git.commit("new CC10")
    event = real_git.root / "push-event.json"
    event.write_text('{"before": "' + release_base + '"}', encoding="utf-8")
    monkeypatch.setenv("GITHUB_EVENT_PATH", str(event))
    assert gate.main([]) == 0


def test_clean_main_missing_release_history_provenance_fails_closed(real_git: GitFixture) -> None:
    real_git.source(0)
    real_git.commit("original source")
    real_git.source(1)
    real_git.commit("valid source")
    assert gate.main([]) == 1
