from __future__ import annotations

from pathlib import Path

from scripts.workflow_policy_gate import (
    action_reference_violations,
    evaluate_workflow_policy,
    permission_violations,
    quality_report_gate_violations,
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
]

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
    "dependency-hygiene-gate",
    "dead-code-gate",
    "workflow-policy-gate",
    "quality-report-gate",
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


def test_workflow_policy_gate_passes_current_repository_workflows() -> None:
    assert evaluate_workflow_policy() == []


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
        f"{workflow.as_posix()}: quality report freshness gate must be blocking, "
        "not continue-on-error"
    ]
