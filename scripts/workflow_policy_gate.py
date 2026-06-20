from __future__ import annotations

import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_DIR = REPO_ROOT / ".github" / "workflows"
PR_TEMPLATE_PATH = REPO_ROOT / ".github" / "pull_request_template.md"
BLOCKING_WORKFLOW_NAMES = {
    "feature-lane.yml",
    "pr-merge-gate.yml",
    "main-releasability.yml",
}
COVERAGE_WORKFLOW_NAMES = {
    "pr-merge-gate.yml",
    "main-releasability.yml",
}
EXPECTED_WORKFLOW_PERMISSIONS = {
    "feature-lane.yml": {"contents": "read"},
    "pr-merge-gate.yml": {"contents": "read"},
    "main-releasability.yml": {"contents": "read"},
    "quality-baseline.yml": {"contents": "read"},
    "demo-certification.yml": {"contents": "read"},
    "pr-auto-merge.yml": {"contents": "write", "pull-requests": "write"},
}
USES_PATTERN = re.compile(r"^\s*(?:-\s*)?uses:\s*[\"']?([^\"'\s#]+)", re.MULTILINE)
VERSION_TAG_PATTERN = re.compile(r"^v\d+(?:\.\d+){0,2}$")
FULL_SHA_PATTERN = re.compile(r"^[0-9a-fA-F]{40}$")
PR_TEMPLATE_REQUIRED_TOKENS = {
    "summary": "## Summary",
    "risk": "## Risk / Rollback",
    "local_static": "`make check`",
    "local_pr": "`make ci`",
    "local_parity": "`make ci-local`",
    "workflow_policy": "`make workflow-policy-gate`",
    "quality_report": "`make quality-report-gate`",
    "coverage_gate": "`make coverage-gate`",
    "duplicate_implementation": "`make duplicate-implementation-gate`",
    "openapi": "`make openapi-gate`",
    "api_vocabulary": "`make api-vocabulary-gate`",
    "no_alias": "`make no-alias-gate`",
    "security": "`make security-audit`",
    "feature_lane": "Remote Feature Lane",
    "pr_merge_gate": "Pull Request Merge Gate",
    "main_releasability": "Main Releasability",
    "stranded_truth_fetch": "`git fetch origin --prune`",
    "stranded_truth_branches": "`git branch -r --no-merged origin/main`",
    "wiki_decision": "Wiki decision",
    "guidance_decision": "Guidance decision",
}


def _workflow_files(workflow_dir: Path = WORKFLOW_DIR) -> list[Path]:
    return sorted(workflow_dir.glob("*.yml")) + sorted(workflow_dir.glob("*.yaml"))


def _is_pinned_action_ref(action_ref: str) -> bool:
    if action_ref.startswith("./"):
        return True
    if "@" not in action_ref:
        return False
    ref = action_ref.rsplit("@", 1)[1]
    return bool(VERSION_TAG_PATTERN.fullmatch(ref) or FULL_SHA_PATTERN.fullmatch(ref))


def action_reference_violations(workflow_path: Path) -> list[str]:
    text = workflow_path.read_text(encoding="utf-8")
    violations: list[str] = []
    for action_ref in USES_PATTERN.findall(text):
        if not _is_pinned_action_ref(action_ref):
            violations.append(
                f"{workflow_path.as_posix()}: action reference must use a version tag or full SHA: "
                f"{action_ref}"
            )
    return violations


def _top_level_permissions(text: str) -> dict[str, str] | None:
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if line.strip() != "permissions:" or line.startswith((" ", "\t")):
            continue
        permissions: dict[str, str] = {}
        for child in lines[index + 1 :]:
            if not child.strip():
                continue
            if not child.startswith((" ", "\t")):
                break
            key, separator, value = child.strip().partition(":")
            if not separator:
                continue
            permissions[key.strip()] = value.strip().split("#", 1)[0].strip()
        return permissions
    return None


def permission_violations(workflow_path: Path) -> list[str]:
    expected = EXPECTED_WORKFLOW_PERMISSIONS.get(workflow_path.name)
    if expected is None:
        return [f"{workflow_path.as_posix()}: workflow must declare an expected permission policy"]
    actual = _top_level_permissions(workflow_path.read_text(encoding="utf-8"))
    if actual != expected:
        return [
            f"{workflow_path.as_posix()}: permissions must be {expected}, found {actual or 'missing'}"
        ]
    return []


def quality_report_gate_violations(workflow_path: Path) -> list[str]:
    if workflow_path.name not in BLOCKING_WORKFLOW_NAMES:
        return []
    text = workflow_path.read_text(encoding="utf-8")
    violations: list[str] = []
    if "make quality-report-gate" not in text:
        return [f"{workflow_path.as_posix()}: blocking workflow must run make quality-report-gate"]
    start = text.index("make quality-report-gate")
    checkout_start = text.rfind("uses: actions/checkout@", 0, start)
    if checkout_start == -1:
        violations.append(
            f"{workflow_path.as_posix()}: quality report gate job must checkout repository first"
        )
    else:
        checkout_block_end = text.find("\n      - ", checkout_start)
        checkout_block = (
            text[checkout_start:]
            if checkout_block_end == -1
            else text[checkout_start:checkout_block_end]
        )
        if "fetch-depth: 0" not in checkout_block:
            violations.append(
                f"{workflow_path.as_posix()}: quality report gate job must use "
                "actions/checkout with fetch-depth: 0 so origin/main is available"
            )
    step_start = text.rfind("\n      - name:", 0, start)
    step_end = text.find("\n      - name:", start)
    step_block = text[step_start:] if step_end == -1 else text[step_start:step_end]
    if "continue-on-error" in step_block:
        violations.append(
            f"{workflow_path.as_posix()}: quality report freshness gate must be blocking, "
            "not continue-on-error"
        )
    return violations


def duplicate_implementation_gate_violations(workflow_path: Path) -> list[str]:
    if workflow_path.name not in BLOCKING_WORKFLOW_NAMES:
        return []
    text = workflow_path.read_text(encoding="utf-8")
    if "make duplicate-implementation-gate" not in text:
        return [
            f"{workflow_path.as_posix()}: blocking workflow must run "
            "make duplicate-implementation-gate"
        ]
    start = text.index("make duplicate-implementation-gate")
    step_start = text.rfind("\n      - name:", 0, start)
    step_end = text.find("\n      - name:", start)
    step_block = text[step_start:] if step_end == -1 else text[step_start:step_end]
    if "continue-on-error" in step_block:
        return [
            f"{workflow_path.as_posix()}: duplicate implementation gate must be blocking, "
            "not continue-on-error"
        ]
    return []


def coverage_gate_violations(workflow_path: Path) -> list[str]:
    if workflow_path.name not in COVERAGE_WORKFLOW_NAMES:
        return []
    text = workflow_path.read_text(encoding="utf-8")
    violations: list[str] = []
    if "python scripts/coverage_gate.py --coverage-dir coverage-data" not in text:
        violations.append(
            f"{workflow_path.as_posix()}: blocking coverage workflow must use "
            "scripts/coverage_gate.py"
        )
    if "python -m coverage combine coverage-data" in text or (
        "python -m coverage report --fail-under" in text
    ):
        violations.append(
            f"{workflow_path.as_posix()}: coverage enforcement must not duplicate ad hoc "
            "coverage combine/report commands"
        )
    return violations


def pr_template_policy_violations(template_path: Path = PR_TEMPLATE_PATH) -> list[str]:
    if not template_path.exists():
        return [f"{template_path.as_posix()}: PR template is missing"]
    text = template_path.read_text(encoding="utf-8")
    violations = []
    for requirement, token in PR_TEMPLATE_REQUIRED_TOKENS.items():
        if token not in text:
            violations.append(
                f"{template_path.as_posix()}: PR template must include {requirement} evidence "
                f"token {token!r}"
            )
    return violations


def evaluate_workflow_policy(workflow_dir: Path = WORKFLOW_DIR) -> list[str]:
    violations: list[str] = []
    for workflow_path in _workflow_files(workflow_dir):
        violations.extend(permission_violations(workflow_path))
        violations.extend(action_reference_violations(workflow_path))
        violations.extend(quality_report_gate_violations(workflow_path))
        violations.extend(duplicate_implementation_gate_violations(workflow_path))
        violations.extend(coverage_gate_violations(workflow_path))
    violations.extend(pr_template_policy_violations())
    return violations


def main() -> None:
    violations = evaluate_workflow_policy()
    if violations:
        print("Workflow policy gate failed:")
        for violation in violations:
            print(f"- {violation}")
        raise SystemExit(1)
    print("Workflow policy gate passed")


if __name__ == "__main__":
    main()
