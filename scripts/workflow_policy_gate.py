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
RAW_PYTEST_PATTERN = re.compile(r"(^|\n)\s+(?:run:\s*)?python\s+-m\s+pytest\b")
EXPECTED_WORKFLOW_PERMISSIONS = {
    "feature-lane.yml": {"contents": "read"},
    "pr-merge-gate.yml": {"contents": "read"},
    "main-releasability.yml": {"contents": "read"},
    "merged-pr-main-releasability.yml": {"actions": "write", "contents": "write"},
    "quality-baseline.yml": {"contents": "read"},
    "demo-certification.yml": {"contents": "read"},
    "pr-auto-merge.yml": {"contents": "read"},
}
USES_PATTERN = re.compile(r"^\s*(?:-\s*)?uses:\s*[\"']?([^\"'\s#]+)", re.MULTILINE)
VERSION_TAG_PATTERN = re.compile(r"^v\d+(?:\.\d+){0,2}$")
FULL_SHA_PATTERN = re.compile(r"^[0-9a-fA-F]{40}$")
IMMUTABLE_DISPATCH_REF_LOOKUP_CONDITIONS = (
    (
        'if existing_ref_sha="$(gh api '
        '"repos/$GITHUB_REPOSITORY/git/ref/tags/$dispatch_ref" '
        '--jq .object.sha 2>/dev/null)"; then'
    ),
    (
        'if existing_ref_sha="$(gh api '
        '"repos/$GITHUB_REPOSITORY/git/ref/tags/${dispatch_ref}" '
        '--jq .object.sha 2>/dev/null)"; then'
    ),
)
IMMUTABLE_DISPATCH_REF_MISMATCH_CONDITION = (
    'if [ "$existing_ref_sha" != "$MERGE_COMMIT_SHA" ]; then'
)
IMMUTABLE_DISPATCH_REF_CREATION_CONDITION = 'if [ -z "$existing_ref_sha" ]; then'
IMMUTABLE_DISPATCH_REF_CREATION_COMMAND = 'gh api "repos/$GITHUB_REPOSITORY/git/refs"'
IMMUTABLE_DISPATCH_REF_CREATION_REF_FIELD = '-f ref="refs/tags/$dispatch_ref"'
IMMUTABLE_DISPATCH_REF_CREATION_SHA_FIELD = '-f sha="$MERGE_COMMIT_SHA"'
PR_TEMPLATE_REQUIRED_TOKENS = {
    "summary": "## Summary",
    "risk": "## Risk / Rollback",
    "local_static": "`make check`",
    "local_pr": "`make ci`",
    "local_parity": "`make ci-local`",
    "workflow_policy": "`make workflow-policy-gate`",
    "quality_report": "`make quality-report-gate`",
    "test_family_inventory": "`make test-family-inventory`",
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


def _opens_nested_shell_scope(stripped_line: str) -> bool:
    return (
        stripped_line == "("
        or stripped_line.startswith("(")
        or stripped_line.startswith(("if ", "for ", "while ", "until ", "case "))
        or stripped_line.startswith("function ")
        or stripped_line.endswith("() {")
        or stripped_line.endswith("(){")
        or stripped_line.endswith(" {")
    )


def _closes_nested_shell_scope(stripped_line: str) -> bool:
    return stripped_line in {"fi", "done", "esac", "}"} or stripped_line.startswith(")")


def _is_shell_comment(stripped_line: str) -> bool:
    return stripped_line.startswith("#")


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


def _step_block(text: str, step_name: str) -> str:
    start = text.find(f"- name: {step_name}")
    if start == -1:
        return ""
    next_step = text.find("\n      - name:", start + 1)
    next_uses = text.find("\n      - uses:", start + 1)
    candidates = [index for index in (next_step, next_uses) if index != -1]
    end = min(candidates) if candidates else len(text)
    return text[start:end]


def _contains_immutable_dispatch_ref_lookup(text: str) -> bool:
    return "git/ref/tags/$dispatch_ref" in text or "git/ref/tags/${dispatch_ref}" in text


def _immutable_ref_lookup_blocks(text: str) -> list[str]:
    lines = text.splitlines()
    blocks: list[str] = []
    for index, line in enumerate(lines):
        stripped_line = line.strip()
        if _is_shell_comment(stripped_line) or not _contains_immutable_dispatch_ref_lookup(line):
            continue

        block_lines = [line]
        if (
            stripped_line == "then"
            or stripped_line.endswith("; then")
            or stripped_line.endswith(')"')
        ):
            blocks.append("\n".join(block_lines))
            continue
        for follow in lines[index + 1 :]:
            block_lines.append(follow)
            stripped = follow.strip()
            if stripped == "then" or stripped.endswith("; then"):
                break
            if not follow.rstrip().endswith("\\") and stripped.endswith(')"'):
                break
        blocks.append("\n".join(block_lines))
    return blocks


def _immutable_ref_lookup_guard_blocks(text: str) -> list[str]:
    lines = text.splitlines()
    blocks: list[str] = []
    for index, line in enumerate(lines):
        stripped_line = line.strip()
        if stripped_line not in IMMUTABLE_DISPATCH_REF_LOOKUP_CONDITIONS:
            continue

        block_lines = [line]
        depth = 1
        for follow in lines[index + 1 :]:
            block_lines.append(follow)
            stripped_follow = follow.strip()
            if _opens_nested_shell_scope(stripped_follow):
                depth += 1
            if _closes_nested_shell_scope(stripped_follow):
                depth -= 1
            if depth == 0:
                break
        blocks.append("\n".join(block_lines))
    return blocks


def _outer_lookup_else_arm_has_unconditional_reset(block: str) -> bool:
    lines = block.splitlines()
    else_index: int | None = None
    depth = 1
    for index, line in enumerate(lines[1:], start=1):
        stripped = line.strip()
        if stripped == "else" and depth == 1:
            else_index = index
            break
        if stripped.startswith("if "):
            depth += 1
        if stripped == "fi":
            depth -= 1

    if else_index is None:
        return False

    executable_commands: list[str] = []
    depth = 1
    for line in lines[else_index + 1 :]:
        stripped = line.strip()
        if stripped == "fi" and depth == 1:
            break
        if not stripped or stripped.startswith("#"):
            continue
        executable_commands.append(stripped)
        if stripped.startswith("if "):
            depth += 1
        if stripped == "fi":
            depth -= 1
    return executable_commands == ['existing_ref_sha=""']


def _outer_lookup_then_arm_has_mismatch_exit(block: str) -> bool:
    lines = block.splitlines()
    then_arm: list[str] = []
    depth = 1
    for line in lines[1:]:
        stripped = line.strip()
        if stripped == "else" and depth == 1:
            break
        then_arm.append(line)
        if stripped.startswith("if "):
            depth += 1
        if stripped == "fi":
            depth -= 1

    condition_depth = 1
    for index, line in enumerate(then_arm):
        stripped_line = line.strip()
        if stripped_line != IMMUTABLE_DISPATCH_REF_MISMATCH_CONDITION or condition_depth != 1:
            if _opens_nested_shell_scope(stripped_line):
                condition_depth += 1
            if _closes_nested_shell_scope(stripped_line):
                condition_depth -= 1
            continue

        direct_executable_commands: list[str] = []
        depth = 1
        for follow in then_arm[index + 1 :]:
            stripped_follow = follow.strip()
            if stripped_follow == "fi" and depth == 1:
                break
            if not stripped_follow or stripped_follow.startswith("#"):
                continue
            if depth == 1:
                direct_executable_commands.append(stripped_follow)
            if _opens_nested_shell_scope(stripped_follow):
                depth += 1
            if _closes_nested_shell_scope(stripped_follow):
                depth -= 1
        return "exit 1" in direct_executable_commands
    return False


def _is_conditionally_guarded_immutable_ref_lookup_block(block: str) -> bool:
    return (
        _contains_immutable_dispatch_ref_lookup(block)
        and "\n" in block
        and "else" in block
        and _outer_lookup_else_arm_has_unconditional_reset(block)
        and block.strip().endswith("fi")
    )


def _has_conditionally_guarded_immutable_ref_lookup(text: str) -> bool:
    lookup_blocks = _immutable_ref_lookup_blocks(text)
    guarded_blocks = _immutable_ref_lookup_guard_blocks(text)
    return (
        bool(lookup_blocks)
        and len(lookup_blocks) == len(guarded_blocks)
        and all(
            _is_conditionally_guarded_immutable_ref_lookup_block(block) for block in guarded_blocks
        )
    )


def _guarded_lookup_success_arms_fail_on_ref_mismatch(text: str) -> bool:
    guarded_blocks = _immutable_ref_lookup_guard_blocks(text)
    return bool(guarded_blocks) and all(
        _outer_lookup_then_arm_has_mismatch_exit(block) for block in guarded_blocks
    )


def _conditionally_creates_absent_immutable_ref(text: str) -> bool:
    lines = text.splitlines()
    depth = 0
    for index, line in enumerate(lines):
        stripped_line = line.strip()
        if stripped_line == IMMUTABLE_DISPATCH_REF_CREATION_CONDITION and depth == 0:
            direct_executable_commands: list[str] = []
            creation_depth = 1
            for follow in lines[index + 1 :]:
                stripped_follow = follow.strip()
                if stripped_follow == "fi" and creation_depth == 1:
                    break
                if not stripped_follow or _is_shell_comment(stripped_follow):
                    continue
                if creation_depth == 1:
                    direct_executable_commands.append(stripped_follow)
                if _opens_nested_shell_scope(stripped_follow):
                    creation_depth += 1
                if _closes_nested_shell_scope(stripped_follow):
                    creation_depth -= 1
            creation_text = "\n".join(direct_executable_commands)
            return (
                any(
                    command == IMMUTABLE_DISPATCH_REF_CREATION_COMMAND
                    or command.startswith(f"{IMMUTABLE_DISPATCH_REF_CREATION_COMMAND} ")
                    for command in direct_executable_commands
                )
                and IMMUTABLE_DISPATCH_REF_CREATION_REF_FIELD in creation_text
                and IMMUTABLE_DISPATCH_REF_CREATION_SHA_FIELD in creation_text
            )
        if not stripped_line or _is_shell_comment(stripped_line):
            continue
        if _opens_nested_shell_scope(stripped_line):
            depth += 1
        if _closes_nested_shell_scope(stripped_line):
            depth -= 1
    return False


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


def family_inventory_gate_violations(workflow_path: Path) -> list[str]:
    if workflow_path.name not in BLOCKING_WORKFLOW_NAMES:
        return []
    text = workflow_path.read_text(encoding="utf-8")
    if "make test-family-inventory" not in text:
        return [
            f"{workflow_path.as_posix()}: blocking workflow must run make test-family-inventory"
        ]
    start = text.index("make test-family-inventory")
    step_start = text.rfind("\n      - name:", 0, start)
    step_end = text.find("\n      - name:", start)
    step_block = text[step_start:] if step_end == -1 else text[step_start:step_end]
    if "continue-on-error" in step_block:
        return [
            f"{workflow_path.as_posix()}: test-family inventory gate must be blocking, "
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


def repo_native_test_target_violations(workflow_path: Path) -> list[str]:
    if workflow_path.name not in BLOCKING_WORKFLOW_NAMES:
        return []
    text = workflow_path.read_text(encoding="utf-8")
    violations: list[str] = []
    if RAW_PYTEST_PATTERN.search(text):
        violations.append(
            f"{workflow_path.as_posix()}: blocking workflow test jobs must use "
            "repo-native Make test targets instead of raw python -m pytest"
        )
    if workflow_path.name == "feature-lane.yml" and "make test-unit" not in text:
        violations.append(
            f"{workflow_path.as_posix()}: Feature Lane unit tests must run make test-unit"
        )
    if workflow_path.name in COVERAGE_WORKFLOW_NAMES and (
        "make test-${{ matrix.suite }}-coverage" not in text
    ):
        violations.append(
            f"{workflow_path.as_posix()}: suite coverage jobs must run "
            "make test-${{ matrix.suite }}-coverage"
        )
    return violations


def docker_image_evidence_violations(workflow_path: Path) -> list[str]:
    if workflow_path.name not in COVERAGE_WORKFLOW_NAMES:
        return []
    text = workflow_path.read_text(encoding="utf-8")
    violations: list[str] = []
    if "make docker-image-evidence" not in text:
        violations.append(
            f"{workflow_path.as_posix()}: blocking Docker workflow must run "
            "make docker-image-evidence"
        )
    if "run: make docker-build" in text:
        violations.append(
            f"{workflow_path.as_posix()}: blocking Docker workflow must not stop at "
            "build-only validation"
        )
    if "output/docker-image-evidence" not in text or "actions/upload-artifact@v7" not in text:
        violations.append(
            f"{workflow_path.as_posix()}: Docker workflow must upload image evidence artifacts"
        )
    return violations


def auto_merge_workflow_violations(workflow_path: Path) -> list[str]:
    if workflow_path.name != "pr-auto-merge.yml":
        return []
    text = workflow_path.read_text(encoding="utf-8")
    violations: list[str] = []
    required_tokens = {
        "secrets.LOTUS_AUTOMERGE_TOKEN": (
            "auto-merge must use LOTUS_AUTOMERGE_TOKEN so the merge actor is not GITHUB_TOKEN"
        ),
        "LOTUS_AUTOMERGE_TOKEN is required": (
            "auto-merge must warn and skip cleanly when LOTUS_AUTOMERGE_TOKEN is absent"
        ),
        "--auto --rebase --delete-branch": (
            "auto-merge must queue rebase merge and branch deletion for linear history"
        ),
        "timeout-minutes: 10": "auto-merge workflow must have a bounded job timeout",
    }
    for token, reason in required_tokens.items():
        if token not in text:
            violations.append(f"{workflow_path.as_posix()}: {reason}")
    forbidden_tokens = {
        "github.token": "auto-merge must not authenticate with GITHUB_TOKEN",
        "--auto --merge": "auto-merge must not queue merge commits",
    }
    for token, reason in forbidden_tokens.items():
        if token in text:
            violations.append(f"{workflow_path.as_posix()}: {reason}")
    return violations


def merged_pr_main_releasability_dispatch_violations(
    workflow_dir: Path = WORKFLOW_DIR,
) -> list[str]:
    main_releasability = workflow_dir / "main-releasability.yml"
    dispatcher = workflow_dir / "merged-pr-main-releasability.yml"
    violations: list[str] = []

    if not dispatcher.exists():
        violations.append(
            f"{dispatcher.as_posix()}: merged PR dispatcher is required so main releasability "
            "runs for the exact post-merge main SHA"
        )
    else:
        dispatcher_text = dispatcher.read_text(encoding="utf-8")
        required_tokens = {
            "pull_request_target:": "dispatcher must run from pull_request_target close events",
            "types: [closed]": "dispatcher must be limited to closed pull request events",
            "github.event.pull_request.merged == true": "dispatcher must require a merged PR",
            "github.event.pull_request.base.ref == 'main'": "dispatcher must target main merges only",
            "github.event.pull_request.merge_commit_sha": (
                "dispatcher must bind dispatch evidence to the merged PR SHA"
            ),
            'dispatch_ref="main-releasability-${MERGE_COMMIT_SHA}"': (
                "dispatcher must create an immutable dispatch ref for the merged PR SHA"
            ),
            "Dispatch ref $dispatch_ref points to $existing_ref_sha": (
                "dispatcher must fail closed if an existing dispatch ref points to a different SHA"
            ),
            'gh api "repos/$GITHUB_REPOSITORY/git/refs"': (
                "dispatcher must create the immutable dispatch ref before workflow dispatch"
            ),
            "gh workflow run main-releasability.yml": (
                "dispatcher must start the governed main releasability workflow"
            ),
            '--ref "$dispatch_ref"': (
                "dispatcher must dispatch against the immutable merged-PR ref"
            ),
            "-f expected_sha=": (
                "dispatcher must pass the merged PR SHA as an expected mainline SHA"
            ),
        }
        for token, reason in required_tokens.items():
            if token not in dispatcher_text:
                violations.append(f"{dispatcher.as_posix()}: {reason}")
        if not _has_conditionally_guarded_immutable_ref_lookup(dispatcher_text):
            violations.append(
                f"{dispatcher.as_posix()}: dispatcher must guard immutable-ref lookup with "
                "an if/else reset so a missing ref is treated as absent instead of terminating "
                "the workflow or capturing an error body as an existing ref SHA"
            )
        elif not _guarded_lookup_success_arms_fail_on_ref_mismatch(dispatcher_text):
            violations.append(
                f"{dispatcher.as_posix()}: dispatcher must fail closed with exit 1 when an "
                "existing immutable dispatch ref points to a different SHA"
            )
        if any("||" in block for block in _immutable_ref_lookup_blocks(dispatcher_text)):
            violations.append(
                f"{dispatcher.as_posix()}: dispatcher must not mask immutable-ref lookup "
                "failures with shell OR fallbacks because GitHub 404 response bodies can be "
                "captured as existing ref SHAs"
            )
        if not _conditionally_creates_absent_immutable_ref(dispatcher_text):
            violations.append(
                f"{dispatcher.as_posix()}: dispatcher must create the immutable dispatch ref only "
                "inside the empty existing-ref branch with exact ref and SHA fields so reruns do "
                "not recreate an existing tag or dispatch the wrong revision"
            )

    if main_releasability.exists():
        main_text = main_releasability.read_text(encoding="utf-8")
        trigger_section = main_text.split("\nconcurrency:", maxsplit=1)[0]
        if "workflow_dispatch:" not in trigger_section:
            violations.append(
                f"{main_releasability.as_posix()}: main releasability must keep manual "
                "workflow_dispatch support"
            )
        assertion_step = _step_block(main_text, "Assert expected merged PR SHA")
        required_assertion_tokens = {
            "expected_sha:": trigger_section,
            'actual_sha="$(git rev-parse HEAD)"': assertion_step,
            'if [ "$actual_sha" != "$EXPECTED_SHA" ]; then': assertion_step,
            "does not match expected merged PR SHA": assertion_step,
            "exit 1": assertion_step,
        }
        missing_assertion_tokens = [
            token
            for token, search_text in required_assertion_tokens.items()
            if token not in search_text
        ]
        if missing_assertion_tokens:
            violations.append(
                f"{main_releasability.as_posix()}: main releasability must assert "
                "expected_sha against the checked-out main commit and fail on mismatch when "
                f"dispatched by a merged PR; missing {', '.join(missing_assertion_tokens)}"
            )
        if "${{ inputs.expected_sha || github.sha }}" not in main_text:
            violations.append(
                f"{main_releasability.as_posix()}: main releasability concurrency must be "
                "revision-aware so stale merged-PR dispatches cannot cancel newer validation"
            )
        if "push:" in trigger_section:
            violations.append(
                f"{main_releasability.as_posix()}: direct push trigger must not coexist with "
                "merged-pr-main-releasability.yml because it creates duplicate automatic "
                "mainline proof runs"
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
        violations.extend(family_inventory_gate_violations(workflow_path))
        violations.extend(repo_native_test_target_violations(workflow_path))
        violations.extend(coverage_gate_violations(workflow_path))
        violations.extend(docker_image_evidence_violations(workflow_path))
        violations.extend(auto_merge_workflow_violations(workflow_path))
    violations.extend(merged_pr_main_releasability_dispatch_violations(workflow_dir))
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
