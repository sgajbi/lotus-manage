from __future__ import annotations

from pathlib import Path


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


def _step_block(workflow_text: str, gate_name: str) -> str:
    marker = f"- name: {gate_name}"
    start = workflow_text.index(marker)
    next_step = workflow_text.find("\n      - name:", start + len(marker))
    if next_step == -1:
        return workflow_text[start:]
    return workflow_text[start:next_step]


def test_feature_pr_and_main_quality_gates_are_enforced() -> None:
    for workflow_path in ENFORCED_WORKFLOWS:
        workflow_text = workflow_path.read_text(encoding="utf-8")
        for gate_name in QUALITY_GATE_NAMES:
            block = _step_block(workflow_text, gate_name)
            assert "continue-on-error" not in block, (
                f"{workflow_path.as_posix()} keeps {gate_name} advisory; "
                "remediated quality gates must fail the lane."
            )


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
