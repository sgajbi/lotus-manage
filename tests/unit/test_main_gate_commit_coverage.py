"""Guards for per-commit main-gate coverage (found by cross-repo review, 2026-08-31).

This repository merges by rebase, so a merged PR of N commits puts N commits
on main. The dispatcher previously named only ``merge_commit_sha`` - 36 of the
45 commits merged over 28-31 Aug had no releasability run, invisibly, because
a run that is never created is not a failure. These tests pin the two halves
of the fix: the dispatcher enumerates every merged revision, and the daily
audit fails closed rather than passing while verifying nothing.
"""

from __future__ import annotations

import re
from pathlib import Path

from scripts import audit_main_gate_coverage as audit

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_ROOT = ROOT / ".github" / "workflows"


def test_merged_pr_dispatch_gates_every_revision_the_pr_put_on_main() -> None:
    dispatcher = (WORKFLOW_ROOT / "merged-pr-main-releasability.yml").read_text(encoding="utf-8")

    # Enumeration of every revision, oldest first, from full history.
    assert "COMMIT_COUNT: ${{ github.event.pull_request.commits }}" in dispatcher
    assert 'git rev-list -n "$COMMIT_COUNT" "$MERGE_COMMIT_SHA" | tac' in dispatcher
    assert "for revision in $revisions; do" in dispatcher
    assert "fetch-depth: 0" in dispatcher
    # Every dispatch is pinned to its own revision, not the PR head.
    assert 'dispatch_ref="main-releasability-${revision}"' in dispatcher
    assert '-f expected_sha="$revision"' in dispatcher
    # The enumeration is only correct under rebase-only merging; the
    # dispatcher must fail loudly if the repository setting ever changes.
    assert "allow_squash_merge" in dispatcher
    assert '"$merge_methods" != "false,false,true"' in dispatcher
    # Ancestry is judged against the freshly fetched main, and a revision that
    # is not main history is refused BEFORE any tag is created or gate
    # dispatched: the guard must sit inside the loop, after the detach onto
    # FETCH_HEAD and ahead of both the tag write and the workflow dispatch.
    assert "git checkout --quiet --detach FETCH_HEAD" in dispatcher
    guard = 'if ! git merge-base --is-ancestor "$revision" HEAD; then'
    assert guard in dispatcher
    assert dispatcher.index("git fetch origin main --quiet") < dispatcher.index(
        "git checkout --quiet --detach FETCH_HEAD"
    )
    assert dispatcher.index("for revision in $revisions; do") < dispatcher.index(guard)
    assert dispatcher.index(guard) < dispatcher.index(
        'dispatch_ref="main-releasability-${revision}"'
    )
    assert dispatcher.index(guard) < dispatcher.index('gh api "repos/$GITHUB_REPOSITORY/git/refs"')
    assert dispatcher.index(guard) < dispatcher.index("gh workflow run main-releasability.yml")


def test_coverage_audit_workflow_runs_the_fail_closed_audit() -> None:
    workflow = (WORKFLOW_ROOT / "main-gate-coverage-audit.yml").read_text(encoding="utf-8")

    assert "schedule:" in workflow
    assert "workflow_dispatch" in workflow
    assert "python scripts/audit_main_gate_coverage.py" in workflow
    assert "--fail-on-gap" in workflow


def test_audit_counts_only_verdict_bearing_runs_and_fails_closed(monkeypatch, capsys) -> None:
    """A cancelled run evaluated nothing, an unfetchable listing proves
    nothing, and both must fail the audit rather than pass it."""

    commits = {
        "a" * 40: ["success"],
        "b" * 40: ["cancelled"],
        "c" * 40: None,
        "d" * 40: [],
    }
    monkeypatch.setattr(
        audit,
        "_git",
        lambda *args: [f"{sha} {sha[:9]} subject line" for sha in commits],
    )
    monkeypatch.setattr(audit, "_run_conclusions", lambda sha: commits[sha])
    monkeypatch.setattr(audit.shutil, "which", lambda name: "/usr/bin/gh")
    monkeypatch.setattr(
        audit.argparse.ArgumentParser,
        "parse_args",
        lambda self: argparse_namespace(limit=400, since_days=7, fail_on_gap=True),
    )

    exit_code = audit.main()
    output = capsys.readouterr().out

    assert exit_code == 1
    assert "UNGATED  ddddddddd" in output
    assert "1 passing, 0 with a failing verdict" in output
    assert "UNKNOWN  ccccccccc" in output
    assert "UNKNOWN  bbbbbbbbb" in output
    assert "1 with no verdict-bearing" in output


def test_a_full_window_is_not_reported_as_truncated(monkeypatch, capsys) -> None:
    """A window holding exactly --limit commits was fully examined; only a
    commit BEYOND the cap proves the span was cut short. Declaring truncation
    at equality would fail the scheduled audit for no reason."""

    shas = [f"{index:040x}" for index in range(3)]
    monkeypatch.setattr(
        audit,
        "_git",
        lambda *args: [f"{sha} {sha[:9]} subject line" for sha in shas],
    )
    monkeypatch.setattr(audit, "_run_conclusions", lambda sha: ["success"])
    monkeypatch.setattr(audit.shutil, "which", lambda name: "/usr/bin/gh")
    monkeypatch.setattr(
        audit.argparse.ArgumentParser,
        "parse_args",
        lambda self: argparse_namespace(limit=3, since_days=7, fail_on_gap=True),
    )

    exit_code = audit.main()
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "WINDOW TRUNCATED" not in output


def test_a_window_beyond_the_cap_fails_closed(monkeypatch, capsys) -> None:
    shas = [f"{index:040x}" for index in range(4)]
    monkeypatch.setattr(
        audit,
        "_git",
        lambda *args: [f"{sha} {sha[:9]} subject line" for sha in shas],
    )
    monkeypatch.setattr(audit, "_run_conclusions", lambda sha: ["success"])
    monkeypatch.setattr(audit.shutil, "which", lambda name: "/usr/bin/gh")
    monkeypatch.setattr(
        audit.argparse.ArgumentParser,
        "parse_args",
        lambda self: argparse_namespace(limit=3, since_days=7, fail_on_gap=True),
    )

    exit_code = audit.main()
    output = capsys.readouterr().out

    assert exit_code == 1
    assert "WINDOW TRUNCATED" in output
    assert "audited 3 commit(s)" in output


def test_the_window_walks_every_commit_regardless_of_date_order(monkeypatch) -> None:
    """`--since` stops traversal at the first older commit, so a newer-dated
    ancestor behind an older-dated one is silently omitted - a green audit for
    a window it never walked. `--since-as-filter` visits every commit."""

    recorded: list[tuple[str, ...]] = []

    def _record(*args: str) -> list[str]:
        recorded.append(args)
        return []

    monkeypatch.setattr(audit, "_git", _record)
    monkeypatch.setattr(audit.shutil, "which", lambda name: "/usr/bin/gh")
    monkeypatch.setattr(
        audit.argparse.ArgumentParser,
        "parse_args",
        lambda self: argparse_namespace(limit=400, since_days=7, fail_on_gap=True),
    )

    audit.main()

    assert recorded, "the audit never asked git for the window"
    flags = recorded[0]
    assert any(flag.startswith("--since-as-filter=") for flag in flags), flags
    assert not any(flag.startswith("--since=") for flag in flags), (
        "plain --since truncates the window at the first older commit"
    )


def test_audit_fails_closed_when_gh_is_unavailable(monkeypatch) -> None:
    monkeypatch.setattr(audit.shutil, "which", lambda name: None)
    monkeypatch.setattr(
        audit.argparse.ArgumentParser,
        "parse_args",
        lambda self: argparse_namespace(limit=400, since_days=7, fail_on_gap=True),
    )

    assert audit.main() == 1


def test_audit_passes_when_every_commit_has_a_verdict(monkeypatch, capsys) -> None:
    """A failing verdict is information, not a coverage gap: the audit passes
    but reports the split so coverage and releasability stay distinct claims."""

    commits = {"a" * 40: ["success"], "b" * 40: ["failure", "cancelled"]}
    monkeypatch.setattr(
        audit,
        "_git",
        lambda *args: [f"{sha} {sha[:9]} subject line" for sha in commits],
    )
    monkeypatch.setattr(audit, "_run_conclusions", lambda sha: commits[sha])
    monkeypatch.setattr(audit.shutil, "which", lambda name: "/usr/bin/gh")
    monkeypatch.setattr(
        audit.argparse.ArgumentParser,
        "parse_args",
        lambda self: argparse_namespace(limit=400, since_days=7, fail_on_gap=True),
    )

    assert audit.main() == 0
    output = capsys.readouterr().out
    assert "1 passing, 1 with a failing verdict" in output
    assert "FAILING  bbbbbbbbb" in output


def argparse_namespace(**kwargs):
    import argparse

    return argparse.Namespace(**kwargs)


def test_the_dispatcher_passes_only_inputs_this_gate_declares() -> None:
    """A dispatch carrying an undeclared input 422s and the gate never runs.

    This guard is specific to lotus-manage and has no counterpart in the
    repository this implementation was ported from, which is exactly why it is
    here: that dispatcher passes `-f source_branch="main"`, and
    `main-releasability.yml` HERE declares only `expected_sha` and
    `triggering_pr`. Copying it verbatim would have made every dispatch fail
    with 422 - disabling the coverage fix silently, while the dispatcher job
    itself went green.

    So this compares the two files against each other rather than asserting a
    remembered list: the gate's declared inputs are the authority, and a future
    input added to the dispatcher must also be added to the gate.
    """

    dispatcher = (WORKFLOW_ROOT / "merged-pr-main-releasability.yml").read_text(encoding="utf-8")
    gate = (WORKFLOW_ROOT / "main-releasability.yml").read_text(encoding="utf-8")

    declared = set(re.findall(r"^      (\w+):$", gate, re.M))
    assert declared, "could not read any declared workflow_dispatch inputs from the gate"

    # Only the workflow-run invocation, not the `gh api .../git/refs` call
    # beside it: that one passes -f ref= and -f sha= as REST parameters, which
    # are not workflow inputs and would be false positives here.
    invocation = dispatcher.split("gh workflow run main-releasability.yml", 1)
    assert len(invocation) == 2, "no main-releasability dispatch found"
    dispatch_call = invocation[1].split("\n\n", 1)[0]
    passed = set(re.findall(r'-f (\w+)="', dispatch_call))
    assert passed, "the dispatch passes no inputs at all; the pinning is gone"

    undeclared = passed - declared
    assert not undeclared, (
        f"dispatcher passes {sorted(undeclared)}, which main-releasability.yml does not declare; "
        "the dispatch would 422 and no gate run would be created"
    )


def test_the_dispatcher_asserts_it_enumerated_one_revision_per_commit() -> None:
    """A loop that silently produces nothing is the shape of the gap being closed.

    Enumerating zero or too few revisions would leave the job green with no
    coverage created - indistinguishable, from the outside, from the defect this
    issue reports. The count is asserted against the PR's own commit count.

    Enumeration and dispatch are separate jobs so the dispatch step stays a flat
    lookup / conditional ref creation / dispatch sequence: workflow_policy_gate
    validates that structure, and a shell `for` loop around it nests the whole
    thing out of that control's reach.
    """

    dispatcher = (WORKFLOW_ROOT / "merged-pr-main-releasability.yml").read_text(encoding="utf-8")

    assert 'if [ "$enumerated" -ne "$COMMIT_COUNT" ]; then' in dispatcher
    assert "enumerated=$((enumerated + 1))" in dispatcher
    # One dispatch job per enumerated revision, fed from the enumerating job so
    # the dispatched SHA stays bound to the merge event rather than to anything
    # a later edit could supply.
    assert "revisions: ${{ steps.enumerate.outputs.revisions }}" in dispatcher
    assert (
        "revision: ${{ fromJson(needs.enumerate-merged-revisions.outputs.revisions) }}"
        in dispatcher
    )
    # Sequential: concurrent jobs creating dispatch tags race on the refs API,
    # and a failed tag creation drops a revision's gate run silently.
    assert "max-parallel: 1" in dispatcher
    # One revision failing must not cancel the others' gate runs.
    assert "fail-fast: false" in dispatcher


def test_a_mixed_sha_binding_is_rejected(tmp_path) -> None:
    """One coherent pinning mode, not two accepted independently.

    Accepting $MERGE_COMMIT_SHA and $revision at each point separately lets a
    mixed dispatcher through: a ref named from $revision while expected_sha is
    still bound to $MERGE_COMMIT_SHA checks out one tree and asserts against
    another. The gate's exact-revision assertion then fails - and a failure is a
    VERDICT, so the coverage audit would count that revision as evaluated when
    nothing evaluated it.

    Falsely reported coverage is the defect this whole change exists to remove,
    so a permissive checker here would defeat its own purpose.
    """

    from scripts.workflow_policy_gate import merged_pr_main_releasability_dispatch_violations

    workflow_dir = tmp_path / "workflows"
    workflow_dir.mkdir()
    mixed = (WORKFLOW_ROOT / "merged-pr-main-releasability.yml").read_text(encoding="utf-8")
    mixed = mixed.replace('-f expected_sha="$revision"', '-f expected_sha="$MERGE_COMMIT_SHA"', 1)
    assert '-f expected_sha="$MERGE_COMMIT_SHA"' in mixed, "mutation did not apply"
    (workflow_dir / "merged-pr-main-releasability.yml").write_text(mixed, encoding="utf-8")
    (workflow_dir / "main-releasability.yml").write_text(
        (WORKFLOW_ROOT / "main-releasability.yml").read_text(encoding="utf-8"), encoding="utf-8"
    )

    violations = merged_pr_main_releasability_dispatch_violations(workflow_dir)

    assert any("ONE consistent SHA variable" in violation for violation in violations), violations


def test_a_coherent_single_commit_binding_is_still_accepted(tmp_path) -> None:
    """Divergence half: coherence must not mean 'only the per-revision mode'.

    A dispatcher pinning every point with $MERGE_COMMIT_SHA is internally
    consistent and must stay valid - rejecting it would make the coherence rule
    a disguised requirement for one implementation rather than a rule about
    self-consistency.
    """

    from scripts.workflow_policy_gate import _pinned_sha_variable

    head_bound = (WORKFLOW_ROOT / "merged-pr-main-releasability.yml").read_text(encoding="utf-8")
    head_bound = head_bound.replace("$revision", "$MERGE_COMMIT_SHA").replace(
        "${revision}", "${MERGE_COMMIT_SHA}"
    )

    assert _pinned_sha_variable(head_bound) == "$MERGE_COMMIT_SHA"
