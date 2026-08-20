from __future__ import annotations

from pathlib import Path

from scripts.workflow_policy_gate import (
    action_reference_violations,
    auto_merge_workflow_violations,
    coverage_gate_violations,
    docker_image_evidence_violations,
    evaluate_workflow_policy,
    merged_pr_main_releasability_dispatch_violations,
    permission_violations,
    pr_template_policy_violations,
    quality_report_gate_violations,
    repo_native_test_target_violations,
    family_inventory_gate_violations,
)


ENFORCED_WORKFLOWS = [
    Path(".github/workflows/feature-lane.yml"),
    Path(".github/workflows/pr-merge-gate.yml"),
    Path(".github/workflows/main-releasability.yml"),
]

ARTIFACT_WORKFLOWS = [
    Path(".github/workflows/pr-merge-gate.yml"),
    Path(".github/workflows/main-releasability.yml"),
    Path(".github/workflows/quality-baseline.yml"),
    Path(".github/workflows/demo-certification.yml"),
]

MERGED_PR_DISPATCHER = Path(".github/workflows/merged-pr-main-releasability.yml")

QUALITY_GATE_NAMES = [
    "Architecture Gate",
    "Complexity Gate",
    "Dependency Hygiene Gate",
    "Dead Code Gate",
]
STATIC_QUALITY_GATE_TARGETS = {
    "lint",
    "no-alias-gate",
    "typecheck",
    "typecheck-tests-critical",
    "openapi-gate",
    "api-vocabulary-gate",
    "service-boundary-gate",
    "router-infrastructure-gate",
    "mesh-contract-validate",
    "architecture-gate",
    "complexity-gate",
    "duplicate-implementation-gate",
    "dependency-hygiene-gate",
    "dead-code-gate",
    "workflow-policy-gate",
    "quality-report-gate",
    "test-family-inventory",
}


def _step_block(workflow_text: str, gate_name: str) -> str:
    marker = f"- name: {gate_name}"
    start = workflow_text.index(marker)
    next_step = workflow_text.find("\n      - name:", start + len(marker))
    if next_step == -1:
        return workflow_text[start:]
    return workflow_text[start:next_step]


def _make_target_prerequisites(makefile_text: str, target_name: str) -> list[str]:
    lines = makefile_text.splitlines()
    for index, line in enumerate(lines):
        if not line.startswith(f"{target_name}:"):
            continue
        parts = []
        current = line.partition(":")[2].strip()
        parts.append(current.rstrip("\\").strip())
        if not current.endswith("\\"):
            return " ".join(parts).split()
        for continuation in lines[index + 1 :]:
            if not continuation.strip():
                break
            current = continuation.strip()
            parts.append(current.rstrip("\\").strip())
            if not current.endswith("\\"):
                break
        return " ".join(parts).split()
    raise AssertionError(f"missing Makefile target: {target_name}")


def _make_target_recipe(makefile_text: str, target_name: str) -> str:
    lines = makefile_text.splitlines()
    for index, line in enumerate(lines):
        if not line.startswith(f"{target_name}:"):
            continue
        recipe_lines = []
        for recipe_line in lines[index + 1 :]:
            if recipe_line and not recipe_line.startswith(("\t", " ")):
                break
            if recipe_line.strip():
                recipe_lines.append(recipe_line.strip())
        return "\n".join(recipe_lines)
    raise AssertionError(f"missing Makefile target: {target_name}")


def test_feature_pr_and_main_quality_gates_are_enforced() -> None:
    for workflow_path in ENFORCED_WORKFLOWS:
        workflow_text = workflow_path.read_text(encoding="utf-8")
        for gate_name in QUALITY_GATE_NAMES:
            block = _step_block(workflow_text, gate_name)
            assert "continue-on-error" not in block, (
                f"{workflow_path.as_posix()} keeps {gate_name} advisory; "
                "remediated quality gates must fail the lane."
            )


def test_local_ci_targets_reuse_static_quality_gate_pack() -> None:
    makefile_text = Path("Makefile").read_text(encoding="utf-8")

    static_gates = set(_make_target_prerequisites(makefile_text, "static-quality-gates"))
    assert static_gates == STATIC_QUALITY_GATE_TARGETS
    assert "static-quality-gates" in _make_target_prerequisites(makefile_text, "check")
    assert "static-quality-gates" in _make_target_prerequisites(makefile_text, "ci")
    assert "static-quality-gates" in _make_target_prerequisites(makefile_text, "ci-local")
    assert "test-all" in _make_target_prerequisites(makefile_text, "ci")
    assert "security-audit" in _make_target_prerequisites(makefile_text, "ci")


def test_security_audit_is_project_scoped_and_blocking() -> None:
    makefile_text = Path("Makefile").read_text(encoding="utf-8")
    recipe = _make_target_recipe(makefile_text, "security-audit")

    assert "python -m bandit -q -r src -c pyproject.toml --severity-level high" in recipe
    assert "python -m pip_audit ." in recipe
    assert "python -m pip_audit --ignore-vuln" not in recipe


def test_local_ci_uses_shared_coverage_gate_script() -> None:
    makefile_text = Path("Makefile").read_text(encoding="utf-8")

    coverage_gate_recipe = _make_target_recipe(makefile_text, "coverage-gate")
    ci_local_recipe = _make_target_recipe(makefile_text, "ci-local")

    assert "python scripts/coverage_gate.py --fail-under $(COVERAGE_FAIL_UNDER)" in (
        coverage_gate_recipe
    )
    assert "$(MAKE) coverage-gate" in ci_local_recipe
    assert "$(MAKE) test-unit-coverage" in ci_local_recipe
    assert "$(MAKE) test-integration-coverage" in ci_local_recipe
    assert "$(MAKE) test-e2e-coverage" in ci_local_recipe
    assert "python -m coverage combine" not in ci_local_recipe
    assert "python -m coverage report" not in ci_local_recipe


def test_makefile_exposes_repo_native_suite_coverage_targets() -> None:
    makefile_text = Path("Makefile").read_text(encoding="utf-8")

    assert "UNIT_TESTS ?= tests/unit" in makefile_text
    assert "INTEGRATION_TESTS ?= tests/integration" in makefile_text
    assert "E2E_TESTS ?= tests/e2e" in makefile_text
    assert "test-unit-coverage" in _make_target_prerequisites(makefile_text, ".PHONY")
    assert "python -m pytest $(UNIT_TESTS) --cov=src --cov-report=" in (
        _make_target_recipe(makefile_text, "test-unit-coverage")
    )
    assert "python -m pytest $(INTEGRATION_TESTS) --cov=src --cov-report=" in (
        _make_target_recipe(makefile_text, "test-integration-coverage")
    )
    assert "python -m pytest $(E2E_TESTS) --cov=src --cov-report=" in (
        _make_target_recipe(makefile_text, "test-e2e-coverage")
    )


def test_blocking_workflows_use_repo_native_test_targets() -> None:
    feature_text = Path(".github/workflows/feature-lane.yml").read_text(encoding="utf-8")
    assert "run: make test-unit" in feature_text
    assert "run: python -m pytest tests/unit" not in feature_text

    for workflow_path in [
        Path(".github/workflows/pr-merge-gate.yml"),
        Path(".github/workflows/main-releasability.yml"),
    ]:
        workflow_text = workflow_path.read_text(encoding="utf-8")
        assert "run: make test-${{ matrix.suite }}-coverage" in workflow_text
        assert "python -m pytest ${{ matrix.path }}" not in workflow_text


def test_blocking_workflows_use_shared_coverage_gate_script() -> None:
    for workflow_path in [
        Path(".github/workflows/pr-merge-gate.yml"),
        Path(".github/workflows/main-releasability.yml"),
    ]:
        workflow_text = workflow_path.read_text(encoding="utf-8")
        assert (
            "python scripts/coverage_gate.py --coverage-dir coverage-data --fail-under "
            "${{ env.COVERAGE_FAIL_UNDER }}"
        ) in workflow_text
        assert "python -m coverage combine coverage-data" not in workflow_text
        assert "python -m coverage report --fail-under" not in workflow_text


def test_blocking_workflows_upload_docker_image_evidence() -> None:
    for workflow_path in [
        Path(".github/workflows/pr-merge-gate.yml"),
        Path(".github/workflows/main-releasability.yml"),
    ]:
        workflow_text = workflow_path.read_text(encoding="utf-8")
        assert "make docker-image-evidence" in workflow_text
        assert "actions/upload-artifact@v7" in workflow_text
        assert "output/docker-image-evidence" in workflow_text
        assert "run: make docker-build" not in workflow_text


def test_artifact_workflows_opt_into_node24_action_runtime() -> None:
    for workflow_path in ARTIFACT_WORKFLOWS:
        workflow_text = workflow_path.read_text(encoding="utf-8")
        assert "actions/upload-artifact@v7" in workflow_text or (
            "actions/download-artifact@v8" in workflow_text
        )
        assert "actions/upload-artifact@v4" not in workflow_text
        assert "actions/download-artifact@v4" not in workflow_text


def test_quality_baseline_uses_node24_setup_node_action() -> None:
    workflow_text = Path(".github/workflows/quality-baseline.yml").read_text(encoding="utf-8")

    assert "actions/setup-node@v6" in workflow_text
    assert 'node-version: "24"' in workflow_text
    assert "actions/setup-node@v4" not in workflow_text
    assert 'node-version: "20"' not in workflow_text


def test_quality_baseline_uses_project_scoped_security_audit() -> None:
    workflow_text = Path(".github/workflows/quality-baseline.yml").read_text(encoding="utf-8")

    assert "python -m pip_audit ." in workflow_text
    assert "pip-audit -r pyproject.toml" not in workflow_text


def test_demo_certification_is_manual_and_evidence_backed() -> None:
    workflow_text = Path(".github/workflows/demo-certification.yml").read_text(encoding="utf-8")

    assert "workflow_dispatch:" in workflow_text
    assert "schedule:" not in workflow_text
    assert "pull_request:" not in workflow_text
    assert "make demo-certify" in workflow_text
    assert "LOTUS_MANAGE_DEMO_CERT_OUTPUT: output/live-api/demo-certification/summary.json" in (
        workflow_text
    )
    assert "actions/upload-artifact@v7" in workflow_text


def test_quality_baseline_keeps_demo_certification_contract_report_only() -> None:
    workflow_text = Path(".github/workflows/quality-baseline.yml").read_text(encoding="utf-8")
    block = _step_block(workflow_text, "Demo Certification Contract")

    assert "continue-on-error: true" in block
    assert "tests/unit/test_validate_live_api.py" in block
    assert "tests/unit/test_run_demo_pack_live.py" in block
    assert "make demo-certify" not in block


def test_workflow_policy_gate_passes_current_repository_workflows() -> None:
    assert evaluate_workflow_policy() == []


def test_pr_auto_merge_uses_governed_rebase_actor() -> None:
    workflow_text = Path(".github/workflows/pr-auto-merge.yml").read_text(encoding="utf-8")

    assert "secrets.LOTUS_AUTOMERGE_TOKEN" in workflow_text
    assert "LOTUS_AUTOMERGE_TOKEN is required" in workflow_text
    assert "--auto --rebase --delete-branch" in workflow_text
    assert "timeout-minutes: 10" in workflow_text
    assert "github.token" not in workflow_text
    assert "--auto --merge" not in workflow_text


def test_merged_pr_main_releasability_dispatcher_is_governed() -> None:
    dispatcher_text = MERGED_PR_DISPATCHER.read_text(encoding="utf-8")
    main_text = Path(".github/workflows/main-releasability.yml").read_text(encoding="utf-8")
    main_trigger_section = main_text.split("\nconcurrency:", maxsplit=1)[0]

    assert merged_pr_main_releasability_dispatch_violations() == []
    assert "pull_request_target:" in dispatcher_text
    assert "types: [closed]" in dispatcher_text
    assert "github.event.pull_request.merged == true" in dispatcher_text
    assert "github.event.pull_request.base.ref == 'main'" in dispatcher_text
    assert "github.event.pull_request.merge_commit_sha" in dispatcher_text
    assert "contents: write" in dispatcher_text
    assert 'dispatch_ref="main-releasability-${MERGE_COMMIT_SHA}"' in dispatcher_text
    assert (
        'if existing_ref_sha="$(gh api "repos/$GITHUB_REPOSITORY/git/ref/tags/$dispatch_ref"'
        in dispatcher_text
    )
    assert "else" in dispatcher_text
    assert 'existing_ref_sha=""' in dispatcher_text
    assert "Dispatch ref $dispatch_ref points to $existing_ref_sha" in dispatcher_text
    assert 'gh api "repos/$GITHUB_REPOSITORY/git/refs"' in dispatcher_text
    assert "gh workflow run main-releasability.yml" in dispatcher_text
    assert '--ref "$dispatch_ref"' in dispatcher_text
    assert '-f expected_sha="$MERGE_COMMIT_SHA"' in dispatcher_text
    assert '-f triggering_pr="$PR_NUMBER"' in dispatcher_text
    assert "workflow_dispatch:" in main_trigger_section
    assert "expected_sha:" in main_trigger_section
    assert "triggering_pr:" in main_trigger_section
    assert "${{ inputs.expected_sha || github.sha }}" in main_text
    assert "LOTUS_RELEASE_GIT_REF: ${{ inputs.expected_sha && 'main' || github.ref_name }}" in (
        main_text
    )
    assert "LOTUS_QUALITY_REF_NAME: ${{ inputs.expected_sha && 'main' || github.ref_name }}" in (
        main_text
    )
    assert 'actual_sha="$(git rev-parse HEAD)"' in main_text
    assert 'if [ "$actual_sha" != "$EXPECTED_SHA" ]; then' in main_text
    assert "does not match expected merged PR SHA" in main_text
    assert "GIT_BRANCH: ${{ env.LOTUS_RELEASE_GIT_REF }}" in main_text
    assert "push:" not in main_trigger_section


def test_merged_pr_dispatch_gate_rejects_duplicate_main_push_trigger(tmp_path: Path) -> None:
    workflow_dir = tmp_path / "workflows"
    workflow_dir.mkdir()
    (workflow_dir / "merged-pr-main-releasability.yml").write_text(
        "\n".join(
            [
                "on:",
                "  pull_request_target:",
                "    types: [closed]",
                "jobs:",
                "  dispatch:",
                "    if: >",
                "      github.event.pull_request.merged == true &&",
                "      github.event.pull_request.base.ref == 'main'",
                "    steps:",
                "      - env:",
                "          MERGE_COMMIT_SHA: ${{ github.event.pull_request.merge_commit_sha }}",
                "        run: |",
                '          dispatch_ref="main-releasability-${MERGE_COMMIT_SHA}"',
                '          gh api "repos/$GITHUB_REPOSITORY/git/refs" -f ref="refs/tags/$dispatch_ref" -f sha="$MERGE_COMMIT_SHA"',
                '          gh workflow run main-releasability.yml --ref "$dispatch_ref" -f expected_sha=$MERGE_COMMIT_SHA',
            ]
        ),
        encoding="utf-8",
    )
    (workflow_dir / "main-releasability.yml").write_text(
        "\n".join(
            [
                "on:",
                "  push:",
                '    branches: ["main"]',
                "  workflow_dispatch:",
                "    inputs:",
                "      expected_sha:",
                "        required: false",
                "concurrency:",
                "  group: ${{ github.workflow }}-${{ inputs.expected_sha || github.sha }}",
                "jobs:",
                "  exact-revision-assertion:",
                "    steps:",
                "      - run: |",
                '          actual_sha="$(git rev-parse HEAD)"',
                '          if [ "$actual_sha" != "$EXPECTED_SHA" ]; then',
                '            echo "does not match expected merged PR SHA"',
                "            exit 1",
                "          fi",
            ]
        ),
        encoding="utf-8",
    )

    violations = merged_pr_main_releasability_dispatch_violations(workflow_dir)

    assert (
        f"{(workflow_dir / 'main-releasability.yml').as_posix()}: direct push trigger must not "
        "coexist with merged-pr-main-releasability.yml because it creates duplicate automatic "
        "mainline proof runs"
    ) in violations


def test_merged_pr_dispatch_gate_rejects_masked_dispatch_ref_lookup(tmp_path: Path) -> None:
    workflow_dir = tmp_path / "workflows"
    workflow_dir.mkdir()
    (workflow_dir / "merged-pr-main-releasability.yml").write_text(
        "\n".join(
            [
                "on:",
                "  pull_request_target:",
                "    types: [closed]",
                "jobs:",
                "  dispatch:",
                "    if: >",
                "      github.event.pull_request.merged == true &&",
                "      github.event.pull_request.base.ref == 'main'",
                "    steps:",
                "      - env:",
                "          MERGE_COMMIT_SHA: ${{ github.event.pull_request.merge_commit_sha }}",
                "        run: |",
                '          dispatch_ref="main-releasability-${MERGE_COMMIT_SHA}"',
                '          existing_ref_sha="$(gh api "repos/$GITHUB_REPOSITORY/git/ref/tags/$dispatch_ref" --jq .object.sha 2>/dev/null || true)"',
                '          gh api "repos/$GITHUB_REPOSITORY/git/refs" -f ref="refs/tags/$dispatch_ref" -f sha="$MERGE_COMMIT_SHA"',
                '          gh workflow run main-releasability.yml --ref "$dispatch_ref" -f expected_sha=$MERGE_COMMIT_SHA',
            ]
        ),
        encoding="utf-8",
    )

    violations = merged_pr_main_releasability_dispatch_violations(workflow_dir)

    assert any(
        "must not mask immutable-ref lookup failures with shell OR fallbacks" in violation
        for violation in violations
    )


def test_merged_pr_dispatch_gate_rejects_equivalent_masked_dispatch_ref_lookup(
    tmp_path: Path,
) -> None:
    workflow_dir = tmp_path / "workflows"
    workflow_dir.mkdir()
    (workflow_dir / "merged-pr-main-releasability.yml").write_text(
        "\n".join(
            [
                "on:",
                "  pull_request_target:",
                "    types: [closed]",
                "jobs:",
                "  dispatch:",
                "    if: >",
                "      github.event.pull_request.merged == true &&",
                "      github.event.pull_request.base.ref == 'main'",
                "    steps:",
                "      - env:",
                "          MERGE_COMMIT_SHA: ${{ github.event.pull_request.merge_commit_sha }}",
                "        run: |",
                '          dispatch_ref="main-releasability-${MERGE_COMMIT_SHA}"',
                '          existing_ref_sha="$(gh api "repos/$GITHUB_REPOSITORY/git/ref/tags/$dispatch_ref" --jq .object.sha 2>/dev/null || :)"',
                '          gh api "repos/$GITHUB_REPOSITORY/git/refs" -f ref="refs/tags/$dispatch_ref" -f sha="$MERGE_COMMIT_SHA"',
                '          gh workflow run main-releasability.yml --ref "$dispatch_ref" -f expected_sha=$MERGE_COMMIT_SHA',
            ]
        ),
        encoding="utf-8",
    )

    violations = merged_pr_main_releasability_dispatch_violations(workflow_dir)

    assert any(
        "must not mask immutable-ref lookup failures with shell OR fallbacks" in violation
        for violation in violations
    )


def test_merged_pr_dispatch_gate_rejects_unguarded_dispatch_ref_lookup(
    tmp_path: Path,
) -> None:
    workflow_dir = tmp_path / "workflows"
    workflow_dir.mkdir()
    (workflow_dir / "merged-pr-main-releasability.yml").write_text(
        "\n".join(
            [
                "on:",
                "  pull_request_target:",
                "    types: [closed]",
                "jobs:",
                "  dispatch:",
                "    if: >",
                "      github.event.pull_request.merged == true &&",
                "      github.event.pull_request.base.ref == 'main'",
                "    steps:",
                "      - env:",
                "          MERGE_COMMIT_SHA: ${{ github.event.pull_request.merge_commit_sha }}",
                "        run: |",
                '          dispatch_ref="main-releasability-${MERGE_COMMIT_SHA}"',
                '          existing_ref_sha="$(gh api "repos/$GITHUB_REPOSITORY/git/ref/tags/$dispatch_ref" --jq .object.sha 2>/dev/null)"',
                '          echo "Dispatch ref $dispatch_ref points to $existing_ref_sha"',
                '          gh api "repos/$GITHUB_REPOSITORY/git/refs" -f ref="refs/tags/$dispatch_ref" -f sha="$MERGE_COMMIT_SHA"',
                '          gh workflow run main-releasability.yml --ref "$dispatch_ref" -f expected_sha="$MERGE_COMMIT_SHA"',
            ]
        ),
        encoding="utf-8",
    )

    violations = merged_pr_main_releasability_dispatch_violations(workflow_dir)

    assert any(
        "must guard immutable-ref lookup with an if/else reset" in violation
        for violation in violations
    )


def test_merged_pr_dispatch_gate_rejects_lookup_reset_in_success_branch(
    tmp_path: Path,
) -> None:
    workflow_dir = tmp_path / "workflows"
    workflow_dir.mkdir()
    (workflow_dir / "merged-pr-main-releasability.yml").write_text(
        "\n".join(
            [
                "on:",
                "  pull_request_target:",
                "    types: [closed]",
                "jobs:",
                "  dispatch:",
                "    if: >",
                "      github.event.pull_request.merged == true &&",
                "      github.event.pull_request.base.ref == 'main'",
                "    steps:",
                "      - env:",
                "          MERGE_COMMIT_SHA: ${{ github.event.pull_request.merge_commit_sha }}",
                "        run: |",
                '          dispatch_ref="main-releasability-${MERGE_COMMIT_SHA}"',
                '          if existing_ref_sha="$(gh api "repos/$GITHUB_REPOSITORY/git/ref/tags/$dispatch_ref" --jq .object.sha 2>/dev/null)"; then',
                '            existing_ref_sha=""',
                "          else",
                '            echo "Dispatch ref $dispatch_ref is absent"',
                "          fi",
                '          echo "Dispatch ref $dispatch_ref points to $existing_ref_sha"',
                '          gh api "repos/$GITHUB_REPOSITORY/git/refs" -f ref="refs/tags/$dispatch_ref" -f sha="$MERGE_COMMIT_SHA"',
                '          gh workflow run main-releasability.yml --ref "$dispatch_ref" -f expected_sha="$MERGE_COMMIT_SHA"',
            ]
        ),
        encoding="utf-8",
    )

    violations = merged_pr_main_releasability_dispatch_violations(workflow_dir)

    assert any(
        "must guard immutable-ref lookup with an if/else reset" in violation
        for violation in violations
    )


def test_merged_pr_dispatch_gate_rejects_later_unguarded_lookup(
    tmp_path: Path,
) -> None:
    workflow_dir = tmp_path / "workflows"
    workflow_dir.mkdir()
    (workflow_dir / "merged-pr-main-releasability.yml").write_text(
        "\n".join(
            [
                "on:",
                "  pull_request_target:",
                "    types: [closed]",
                "jobs:",
                "  dispatch:",
                "    if: >",
                "      github.event.pull_request.merged == true &&",
                "      github.event.pull_request.base.ref == 'main'",
                "    steps:",
                "      - env:",
                "          MERGE_COMMIT_SHA: ${{ github.event.pull_request.merge_commit_sha }}",
                "        run: |",
                '          dispatch_ref="main-releasability-${MERGE_COMMIT_SHA}"',
                '          if existing_ref_sha="$(gh api "repos/$GITHUB_REPOSITORY/git/ref/tags/$dispatch_ref" --jq .object.sha 2>/dev/null)"; then',
                '            echo "Dispatch ref $dispatch_ref points to $existing_ref_sha"',
                "          else",
                '            existing_ref_sha=""',
                "          fi",
                '          existing_ref_sha="$(gh api "repos/$GITHUB_REPOSITORY/git/ref/tags/$dispatch_ref" --jq .object.sha 2>/dev/null)"',
                '          gh api "repos/$GITHUB_REPOSITORY/git/refs" -f ref="refs/tags/$dispatch_ref" -f sha="$MERGE_COMMIT_SHA"',
                '          gh workflow run main-releasability.yml --ref "$dispatch_ref" -f expected_sha="$MERGE_COMMIT_SHA"',
            ]
        ),
        encoding="utf-8",
    )

    violations = merged_pr_main_releasability_dispatch_violations(workflow_dir)

    assert any(
        "must guard immutable-ref lookup with an if/else reset" in violation
        for violation in violations
    )


def test_merged_pr_dispatch_gate_rejects_commented_else_reset(
    tmp_path: Path,
) -> None:
    workflow_dir = tmp_path / "workflows"
    workflow_dir.mkdir()
    (workflow_dir / "merged-pr-main-releasability.yml").write_text(
        "\n".join(
            [
                "on:",
                "  pull_request_target:",
                "    types: [closed]",
                "jobs:",
                "  dispatch:",
                "    if: >",
                "      github.event.pull_request.merged == true &&",
                "      github.event.pull_request.base.ref == 'main'",
                "    steps:",
                "      - env:",
                "          MERGE_COMMIT_SHA: ${{ github.event.pull_request.merge_commit_sha }}",
                "        run: |",
                '          dispatch_ref="main-releasability-${MERGE_COMMIT_SHA}"',
                '          if existing_ref_sha="$(gh api "repos/$GITHUB_REPOSITORY/git/ref/tags/$dispatch_ref" --jq .object.sha 2>/dev/null)"; then',
                '            echo "Dispatch ref $dispatch_ref points to $existing_ref_sha"',
                "          else",
                '            # existing_ref_sha=""',
                "          fi",
                '          gh api "repos/$GITHUB_REPOSITORY/git/refs" -f ref="refs/tags/$dispatch_ref" -f sha="$MERGE_COMMIT_SHA"',
                '          gh workflow run main-releasability.yml --ref "$dispatch_ref" -f expected_sha="$MERGE_COMMIT_SHA"',
            ]
        ),
        encoding="utf-8",
    )

    violations = merged_pr_main_releasability_dispatch_violations(workflow_dir)

    assert any(
        "must guard immutable-ref lookup with an if/else reset" in violation
        for violation in violations
    )


def test_merged_pr_dispatch_gate_rejects_nested_else_reset(
    tmp_path: Path,
) -> None:
    workflow_dir = tmp_path / "workflows"
    workflow_dir.mkdir()
    (workflow_dir / "merged-pr-main-releasability.yml").write_text(
        "\n".join(
            [
                "on:",
                "  pull_request_target:",
                "    types: [closed]",
                "jobs:",
                "  dispatch:",
                "    if: >",
                "      github.event.pull_request.merged == true &&",
                "      github.event.pull_request.base.ref == 'main'",
                "    steps:",
                "      - env:",
                "          MERGE_COMMIT_SHA: ${{ github.event.pull_request.merge_commit_sha }}",
                "        run: |",
                '          dispatch_ref="main-releasability-${MERGE_COMMIT_SHA}"',
                '          if existing_ref_sha="$(gh api "repos/$GITHUB_REPOSITORY/git/ref/tags/$dispatch_ref" --jq .object.sha 2>/dev/null)"; then',
                '            echo "Dispatch ref $dispatch_ref points to $existing_ref_sha"',
                "          else",
                '            if [ -n "$dispatch_ref" ]; then',
                '              existing_ref_sha=""',
                "            fi",
                "          fi",
                '          gh api "repos/$GITHUB_REPOSITORY/git/refs" -f ref="refs/tags/$dispatch_ref" -f sha="$MERGE_COMMIT_SHA"',
                '          gh workflow run main-releasability.yml --ref "$dispatch_ref" -f expected_sha="$MERGE_COMMIT_SHA"',
            ]
        ),
        encoding="utf-8",
    )

    violations = merged_pr_main_releasability_dispatch_violations(workflow_dir)

    assert any(
        "must guard immutable-ref lookup with an if/else reset" in violation
        for violation in violations
    )


def test_merged_pr_dispatch_gate_rejects_function_body_else_reset(
    tmp_path: Path,
) -> None:
    workflow_dir = tmp_path / "workflows"
    workflow_dir.mkdir()
    (workflow_dir / "merged-pr-main-releasability.yml").write_text(
        "\n".join(
            [
                "on:",
                "  pull_request_target:",
                "    types: [closed]",
                "jobs:",
                "  dispatch:",
                "    if: >",
                "      github.event.pull_request.merged == true &&",
                "      github.event.pull_request.base.ref == 'main'",
                "    steps:",
                "      - env:",
                "          MERGE_COMMIT_SHA: ${{ github.event.pull_request.merge_commit_sha }}",
                "        run: |",
                '          dispatch_ref="main-releasability-${MERGE_COMMIT_SHA}"',
                '          if existing_ref_sha="$(gh api "repos/$GITHUB_REPOSITORY/git/ref/tags/$dispatch_ref" --jq .object.sha 2>/dev/null)"; then',
                '            echo "Dispatch ref $dispatch_ref points to $existing_ref_sha"',
                "          else",
                "            reset_lookup() {",
                '              existing_ref_sha=""',
                "            }",
                "          fi",
                '          gh api "repos/$GITHUB_REPOSITORY/git/refs" -f ref="refs/tags/$dispatch_ref" -f sha="$MERGE_COMMIT_SHA"',
                '          gh workflow run main-releasability.yml --ref "$dispatch_ref" -f expected_sha="$MERGE_COMMIT_SHA"',
            ]
        ),
        encoding="utf-8",
    )

    violations = merged_pr_main_releasability_dispatch_violations(workflow_dir)

    assert any(
        "must guard immutable-ref lookup with an if/else reset" in violation
        for violation in violations
    )


def test_merged_pr_dispatch_gate_allows_unrelated_best_effort_commands(
    tmp_path: Path,
) -> None:
    workflow_dir = tmp_path / "workflows"
    workflow_dir.mkdir()
    (workflow_dir / "merged-pr-main-releasability.yml").write_text(
        "\n".join(
            [
                "on:",
                "  pull_request_target:",
                "    types: [closed]",
                "jobs:",
                "  dispatch:",
                "    if: >",
                "      github.event.pull_request.merged == true &&",
                "      github.event.pull_request.base.ref == 'main'",
                "    steps:",
                "      - env:",
                "          MERGE_COMMIT_SHA: ${{ github.event.pull_request.merge_commit_sha }}",
                "        run: |",
                '          dispatch_ref="main-releasability-${MERGE_COMMIT_SHA}"',
                '          if existing_ref_sha="$(gh api "repos/$GITHUB_REPOSITORY/git/ref/tags/$dispatch_ref" --jq .object.sha 2>/dev/null)"; then',
                '            echo "Dispatch ref $dispatch_ref points to $existing_ref_sha"',
                "          else",
                '            existing_ref_sha=""',
                "          fi",
                '          gh api "repos/$GITHUB_REPOSITORY/git/refs" -f ref="refs/tags/$dispatch_ref" -f sha="$MERGE_COMMIT_SHA"',
                '          gh workflow run main-releasability.yml --ref "$dispatch_ref" -f expected_sha="$MERGE_COMMIT_SHA"',
                '          gh api "repos/$GITHUB_REPOSITORY/actions/runs?per_page=1" >/dev/null || true',
            ]
        ),
        encoding="utf-8",
    )

    violations = merged_pr_main_releasability_dispatch_violations(workflow_dir)

    assert not any(
        "must not mask immutable-ref lookup failures with shell OR fallbacks" in violation
        for violation in violations
    )
    assert not any(
        "must guard immutable-ref lookup with an if/else reset" in violation
        for violation in violations
    )


def test_merged_pr_dispatch_gate_rejects_token_only_revision_assertion(tmp_path: Path) -> None:
    workflow_dir = tmp_path / "workflows"
    workflow_dir.mkdir()
    (workflow_dir / "merged-pr-main-releasability.yml").write_text(
        "\n".join(
            [
                "on:",
                "  pull_request_target:",
                "    types: [closed]",
                "jobs:",
                "  dispatch:",
                "    if: >",
                "      github.event.pull_request.merged == true &&",
                "      github.event.pull_request.base.ref == 'main'",
                "    steps:",
                "      - env:",
                "          MERGE_COMMIT_SHA: ${{ github.event.pull_request.merge_commit_sha }}",
                "        run: |",
                '          dispatch_ref="main-releasability-${MERGE_COMMIT_SHA}"',
                '          gh api "repos/$GITHUB_REPOSITORY/git/refs" -f ref="refs/tags/$dispatch_ref" -f sha="$MERGE_COMMIT_SHA"',
                '          gh workflow run main-releasability.yml --ref "$dispatch_ref" -f expected_sha=$MERGE_COMMIT_SHA',
            ]
        ),
        encoding="utf-8",
    )
    (workflow_dir / "main-releasability.yml").write_text(
        "\n".join(
            [
                "on:",
                "  workflow_dispatch:",
                "    inputs:",
                "      expected_sha:",
                "        required: false",
                "concurrency:",
                "  group: ${{ github.workflow }}-${{ inputs.expected_sha || github.sha }}",
                "jobs:",
                "  exact-revision-assertion:",
                "    steps:",
                "      - run: git rev-parse HEAD",
            ]
        ),
        encoding="utf-8",
    )

    violations = merged_pr_main_releasability_dispatch_violations(workflow_dir)

    assert any(
        "main releasability must assert expected_sha against the checked-out main commit and fail on mismatch"
        in violation
        for violation in violations
    )


def test_merged_pr_dispatch_gate_rejects_non_failing_mismatch_branch(tmp_path: Path) -> None:
    workflow_dir = tmp_path / "workflows"
    workflow_dir.mkdir()
    (workflow_dir / "merged-pr-main-releasability.yml").write_text(
        "\n".join(
            [
                "on:",
                "  pull_request_target:",
                "    types: [closed]",
                "jobs:",
                "  dispatch:",
                "    if: >",
                "      github.event.pull_request.merged == true &&",
                "      github.event.pull_request.base.ref == 'main'",
                "    steps:",
                "      - env:",
                "          MERGE_COMMIT_SHA: ${{ github.event.pull_request.merge_commit_sha }}",
                "        run: |",
                '          dispatch_ref="main-releasability-${MERGE_COMMIT_SHA}"',
                '          gh api "repos/$GITHUB_REPOSITORY/git/refs" -f ref="refs/tags/$dispatch_ref" -f sha="$MERGE_COMMIT_SHA"',
                '          gh workflow run main-releasability.yml --ref "$dispatch_ref" -f expected_sha=$MERGE_COMMIT_SHA',
            ]
        ),
        encoding="utf-8",
    )
    (workflow_dir / "main-releasability.yml").write_text(
        "\n".join(
            [
                "on:",
                "  workflow_dispatch:",
                "    inputs:",
                "      expected_sha:",
                "        required: false",
                "concurrency:",
                "  group: ${{ github.workflow }}-${{ inputs.expected_sha || github.sha }}",
                "jobs:",
                "  exact-revision-assertion:",
                "    steps:",
                "      - name: Assert expected merged PR SHA",
                "        run: |",
                '          actual_sha="$(git rev-parse HEAD)"',
                '          if [ "$actual_sha" != "$EXPECTED_SHA" ]; then',
                '            echo "does not match expected merged PR SHA"',
                "            exit 0",
                "          fi",
                "      - name: Unrelated failure",
                "        run: exit 1",
            ]
        ),
        encoding="utf-8",
    )

    violations = merged_pr_main_releasability_dispatch_violations(workflow_dir)

    assert any(
        "main releasability must assert expected_sha against the checked-out main commit and fail on mismatch"
        in violation
        for violation in violations
    )


def test_pr_template_policy_gate_passes_current_template() -> None:
    assert pr_template_policy_violations() == []


def test_pr_template_policy_gate_rejects_missing_required_evidence(tmp_path: Path) -> None:
    template = tmp_path / "pull_request_template.md"
    template.write_text(
        "\n".join(
            [
                "## Summary",
                "-",
                "## Validation Evidence",
                "- [ ] `make check`",
                "- [ ] `make ci`",
            ]
        ),
        encoding="utf-8",
    )

    violations = pr_template_policy_violations(template)

    assert (
        f"{template.as_posix()}: PR template must include local_parity evidence token "
        "'`make ci-local`'"
    ) in violations
    assert (
        f"{template.as_posix()}: PR template must include coverage_gate evidence token "
        "'`make coverage-gate`'"
    ) in violations
    assert (
        f"{template.as_posix()}: PR template must include stranded_truth_fetch evidence token "
        "'`git fetch origin --prune`'"
    ) in violations
    assert (
        f"{template.as_posix()}: PR template must include guidance_decision evidence token "
        "'Guidance decision'"
    ) in violations


def test_workflow_policy_gate_rejects_unpinned_action_refs(tmp_path: Path) -> None:
    workflow = tmp_path / "feature-lane.yml"
    workflow.write_text(
        "\n".join(
            [
                "permissions:",
                "  contents: read",
                "jobs:",
                "  lint:",
                "    steps:",
                "      - uses: actions/checkout@main",
                "      - uses: actions/setup-python@v6",
            ]
        ),
        encoding="utf-8",
    )

    assert action_reference_violations(workflow) == [
        f"{workflow.as_posix()}: action reference must use a version tag or full SHA: "
        "actions/checkout@main"
    ]


def test_workflow_policy_gate_rejects_permission_creep(tmp_path: Path) -> None:
    workflow = tmp_path / "feature-lane.yml"
    workflow.write_text(
        "\n".join(
            [
                "permissions:",
                "  contents: write",
                "  actions: write",
                "jobs:",
                "  lint:",
                "    steps:",
                "      - uses: actions/checkout@v6",
            ]
        ),
        encoding="utf-8",
    )

    assert permission_violations(workflow) == [
        f"{workflow.as_posix()}: permissions must be {{'contents': 'read'}}, "
        "found {'contents': 'write', 'actions': 'write'}"
    ]


def test_workflow_policy_gate_rejects_merge_commit_auto_merge(tmp_path: Path) -> None:
    workflow = tmp_path / "pr-auto-merge.yml"
    workflow.write_text(
        "\n".join(
            [
                "permissions:",
                "  contents: write",
                "  pull-requests: write",
                "jobs:",
                "  queue-auto-merge:",
                "    runs-on: ubuntu-latest",
                "    steps:",
                "      - name: Enable auto-merge queue (merge commit)",
                "        env:",
                "          GH_TOKEN: ${{ github.token }}",
                "        run: gh pr merge 1 --auto --merge --delete-branch",
            ]
        ),
        encoding="utf-8",
    )

    violations = auto_merge_workflow_violations(workflow)

    assert (
        f"{workflow.as_posix()}: auto-merge must use LOTUS_AUTOMERGE_TOKEN so the merge actor "
        "is not GITHUB_TOKEN"
    ) in violations
    assert (
        f"{workflow.as_posix()}: auto-merge must queue rebase merge and branch deletion for "
        "linear history"
    ) in violations
    assert f"{workflow.as_posix()}: auto-merge must not authenticate with GITHUB_TOKEN" in (
        violations
    )
    assert f"{workflow.as_posix()}: auto-merge must not queue merge commits" in violations


def test_workflow_policy_gate_requires_blocking_quality_report_gate(tmp_path: Path) -> None:
    workflow = tmp_path / "pr-merge-gate.yml"
    workflow.write_text(
        "\n".join(
            [
                "permissions:",
                "  contents: read",
                "jobs:",
                "  lint:",
                "    steps:",
                "      - name: Quality Report Freshness Gate",
                "        continue-on-error: true",
                "        run: make quality-report-gate",
            ]
        ),
        encoding="utf-8",
    )

    assert quality_report_gate_violations(workflow) == [
        f"{workflow.as_posix()}: quality report gate job must checkout repository first",
        f"{workflow.as_posix()}: quality report freshness gate must be blocking, "
        "not continue-on-error",
    ]


def test_workflow_policy_gate_requires_blocking_test_family_inventory_gate(
    tmp_path: Path,
) -> None:
    workflow = tmp_path / "pr-merge-gate.yml"
    workflow.write_text(
        "\n".join(
            [
                "permissions:",
                "  contents: read",
                "jobs:",
                "  lint:",
                "    steps:",
                "      - name: Test Family Inventory Gate",
                "        continue-on-error: true",
                "        run: make test-family-inventory",
            ]
        ),
        encoding="utf-8",
    )

    assert family_inventory_gate_violations(workflow) == [
        f"{workflow.as_posix()}: test-family inventory gate must be blocking, "
        "not continue-on-error",
    ]


def test_workflow_policy_gate_requires_full_history_for_quality_report_gate(
    tmp_path: Path,
) -> None:
    workflow = tmp_path / "pr-merge-gate.yml"
    workflow.write_text(
        "\n".join(
            [
                "permissions:",
                "  contents: read",
                "jobs:",
                "  lint:",
                "    steps:",
                "      - uses: actions/checkout@v6",
                "      - name: Quality Report Freshness Gate",
                "        run: make quality-report-gate",
            ]
        ),
        encoding="utf-8",
    )

    assert quality_report_gate_violations(workflow) == [
        f"{workflow.as_posix()}: quality report gate job must use actions/checkout with "
        "fetch-depth: 0 so origin/main is available"
    ]


def test_workflow_policy_gate_rejects_ad_hoc_coverage_commands(tmp_path: Path) -> None:
    workflow = tmp_path / "pr-merge-gate.yml"
    workflow.write_text(
        "\n".join(
            [
                "permissions:",
                "  contents: read",
                "jobs:",
                "  coverage:",
                "    steps:",
                "      - name: Enforce Coverage Floor",
                "        run: |",
                "          python -m coverage combine coverage-data",
                "          python -m coverage report --fail-under=${{ env.COVERAGE_FAIL_UNDER }}",
            ]
        ),
        encoding="utf-8",
    )

    assert coverage_gate_violations(workflow) == [
        f"{workflow.as_posix()}: blocking coverage workflow must use scripts/coverage_gate.py",
        f"{workflow.as_posix()}: coverage enforcement must not duplicate ad hoc coverage "
        "combine/report commands",
    ]


def test_workflow_policy_gate_rejects_raw_pytest_workflow_shortcuts(
    tmp_path: Path,
) -> None:
    workflow = tmp_path / "pr-merge-gate.yml"
    workflow.write_text(
        "\n".join(
            [
                "permissions:",
                "  contents: read",
                "jobs:",
                "  test-suites:",
                "    steps:",
                "      - name: Run tests with coverage data",
                "        run: python -m pytest ${{ matrix.path }} --cov=src --cov-report=",
            ]
        ),
        encoding="utf-8",
    )

    assert repo_native_test_target_violations(workflow) == [
        f"{workflow.as_posix()}: blocking workflow test jobs must use repo-native Make "
        "test targets instead of raw python -m pytest",
        f"{workflow.as_posix()}: suite coverage jobs must run "
        "make test-${{ matrix.suite }}-coverage",
    ]


def test_workflow_policy_gate_accepts_make_backed_suite_targets(tmp_path: Path) -> None:
    workflow = tmp_path / "pr-merge-gate.yml"
    workflow.write_text(
        "\n".join(
            [
                "permissions:",
                "  contents: read",
                "jobs:",
                "  test-suites:",
                "    steps:",
                "      - name: Run tests with coverage data",
                "        run: make test-${{ matrix.suite }}-coverage",
            ]
        ),
        encoding="utf-8",
    )

    assert repo_native_test_target_violations(workflow) == []


def test_workflow_policy_gate_rejects_build_only_docker_lane(tmp_path: Path) -> None:
    workflow = tmp_path / "pr-merge-gate.yml"
    workflow.write_text(
        "\n".join(
            [
                "permissions:",
                "  contents: read",
                "jobs:",
                "  docker-build:",
                "    steps:",
                "      - uses: actions/checkout@v6",
                "      - name: Build Docker image",
                "        run: make docker-build",
            ]
        ),
        encoding="utf-8",
    )

    assert docker_image_evidence_violations(workflow) == [
        f"{workflow.as_posix()}: blocking Docker workflow must run make docker-image-evidence",
        f"{workflow.as_posix()}: blocking Docker workflow must not stop at build-only validation",
        f"{workflow.as_posix()}: Docker workflow must upload image evidence artifacts",
    ]
