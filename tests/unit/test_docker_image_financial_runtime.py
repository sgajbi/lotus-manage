"""Immutable Docker financial proof and fail-closed evidence contracts."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest
import yaml

from scripts.image_financial_runtime import validate_image, validate_results
from scripts.workflow_policy_gate import docker_image_evidence_violations


REVISION = "a" * 40
IMAGE = {
    "Id": "sha256:" + "b" * 64,
    "Config": {"User": "dpm-user", "Labels": {"org.opencontainers.image.revision": REVISION}},
}
NAMES = (
    "test_native_network_construction_survives_api_process_replacement[USD]",
    "test_native_network_construction_survives_api_process_replacement[EUR]",
    "test_http_wave_worker_recovers_committed_financial_artifact_after_process_death",
)


@pytest.mark.parametrize("name", ["pr-merge-gate.yml", "main-releasability.yml"])
@pytest.mark.parametrize(
    "tamper",
    [
        "workflow-makeflags",
        "job-makeflags",
        "step-makeflags",
        "gnumakeflags",
        "mflags",
        "pytest-options",
        "workflow-shell",
        "job-shell",
        "step-shell",
        "working-directory",
        "coverage-skip",
        "postgres-skip",
        "transitive-skip",
        "prerequisite-step-skip",
        "prerequisite-waiver",
        "missing-dependency",
        "dependency-cycle",
        "invalid-needs",
        "upload-before-proof",
        "extra-command",
        "missing-upload-errors",
        "matrix-exclusion",
        "image-matrix",
        "job-container",
        "checkout-ref",
        "workflow-shellopts",
        "job-shellopts",
        "step-shellopts",
        "bashopts",
        "unknown-env",
        "build-revision",
        "proof-revision",
        "workflow-floor",
        "job-floor",
        "step-floor",
        "postgres-optional",
        "coverage-file",
        "build-branch",
        "coverage-command",
        "postgres-command",
        "suite-command",
        "suite-checkout-ref",
        "postgres-checkout-ref",
        "lint-checkout-ref",
        "coverage-checkout-ref",
        "checkout-path",
        "checkout-repository",
        "duplicate-checkout",
        "missing-checkout",
        "remove-test-dependency",
        "remove-lint-dependency",
        "suite-install-switch",
        "postgres-install-switch",
        "lint-install-switch",
        "coverage-install-switch",
        "extra-local-action",
        "download-worktree",
        "upload-ignore",
        "setup-environment",
    ],
)
def test_structured_policy_rejects_inherited_execution_bypasses(tmp_path, name, tamper):
    workflow = yaml.safe_load(Path(".github/workflows", name).read_text(encoding="utf-8"))
    jobs = workflow["jobs"]
    docker = jobs["docker-build"]
    proof = docker["steps"][4]
    if tamper.endswith("install-switch"):
        job_name = {
            "suite-install-switch": "test-suites",
            "postgres-install-switch": "idea-management-action-postgres",
            "lint-install-switch": "lint-typecheck-security",
            "coverage-install-switch": "coverage-gate",
        }[tamper]
        step = next(
            step for step in jobs[job_name]["steps"] if step.get("run") == "make install-ci"
        )
        step["run"] = "git fetch origin main && git checkout FETCH_HEAD\nmake install-ci"
    elif tamper == "extra-local-action":
        jobs["test-suites"]["steps"].insert(2, {"uses": "./.github/actions/source-switch"})
    elif tamper == "download-worktree":
        step = next(
            step
            for step in jobs["coverage-gate"]["steps"]
            if step.get("uses") == "actions/download-artifact@v8"
        )
        step["with"]["path"] = "."
    elif tamper == "upload-ignore":
        jobs["idea-management-action-postgres"]["steps"][-1]["with"]["if-no-files-found"] = "warn"
    elif tamper == "setup-environment":
        jobs["test-suites"]["steps"][1]["with"]["python-version"] = "3.11"
    elif tamper.endswith("checkout-ref") and tamper != "checkout-ref":
        job_name = {
            "suite-checkout-ref": "test-suites",
            "postgres-checkout-ref": "idea-management-action-postgres",
            "lint-checkout-ref": "lint-typecheck-security",
            "coverage-checkout-ref": "coverage-gate",
        }[tamper]
        jobs[job_name]["steps"][0].setdefault("with", {})["ref"] = "main"
    elif tamper in ("checkout-path", "checkout-repository"):
        key = "path" if tamper == "checkout-path" else "repository"
        jobs["test-suites"]["steps"][0]["with"] = {key: "other-source"}
    elif tamper == "duplicate-checkout":
        jobs["coverage-gate"]["steps"].insert(1, deepcopy(jobs["coverage-gate"]["steps"][0]))
    elif tamper == "missing-checkout":
        jobs["idea-management-action-postgres"]["steps"].pop(0)
    elif tamper == "remove-test-dependency":
        jobs["coverage-gate"]["needs"].remove("test-suites")
    elif tamper == "remove-lint-dependency":
        jobs["idea-management-action-postgres"]["needs"] = []
    elif tamper in ("coverage-command", "postgres-command", "suite-command"):
        job_name = {
            "coverage-command": "coverage-gate",
            "postgres-command": "idea-management-action-postgres",
            "suite-command": "test-suites",
        }[tamper]
        step = next(
            step
            for step in jobs[job_name]["steps"]
            if "run" in step
            and ("coverage_gate.py" in step["run"] or step["run"].startswith("make test-"))
        )
        step["run"] = (
            step["run"].replace("${{ env.COVERAGE_FAIL_UNDER }}", "0")
            if tamper == "coverage-command"
            else step["run"] + " || true"
        )
        step.pop("env", None)
    elif tamper.endswith("floor"):
        scope = {"workflow-floor": workflow, "job-floor": jobs["coverage-gate"]}.get(
            tamper, jobs["coverage-gate"]["steps"][-1]
        )
        scope.setdefault("env", {})["COVERAGE_FAIL_UNDER"] = "0"
    elif tamper == "postgres-optional":
        jobs["idea-management-action-postgres"]["steps"][3]["env"][
            "DPM_POSTGRES_INTEGRATION_REQUIRED"
        ] = "0"
    elif tamper == "coverage-file":
        jobs["test-suites"]["steps"][3]["env"]["COVERAGE_FILE"] = ".coverage.unrelated"
    elif tamper == "build-branch":
        docker["steps"][3]["env"]["GIT_BRANCH"] = "main; true #"
    elif tamper.endswith("shellopts") or tamper in ("bashopts", "unknown-env"):
        scope = {"workflow-shellopts": workflow, "job-shellopts": docker}.get(tamper, proof)
        key = {"bashopts": "BASHOPTS", "unknown-env": "UNRECOGNIZED_CONTROL"}.get(
            tamper, "SHELLOPTS"
        )
        scope.setdefault("env", {})[key] = "noexec"
    elif tamper.endswith("makeflags") or tamper in ("gnumakeflags", "mflags", "pytest-options"):
        scope = {"workflow-makeflags": workflow, "job-makeflags": docker}.get(tamper, proof)
        key = {
            "gnumakeflags": "GNUMAKEFLAGS",
            "mflags": "MFLAGS",
            "pytest-options": "PYTEST_ADDOPTS",
        }.get(tamper, "MAKEFLAGS")
        scope.setdefault("env", {})[key] = "--ignore-errors"
    elif tamper.endswith("shell"):
        scope = {"workflow-shell": workflow, "job-shell": docker}.get(tamper)
        if scope is None:
            proof["shell"] = "/bin/true {0}"
        else:
            scope["defaults"] = {"run": {"shell": "/bin/true {0}"}}
    elif tamper == "working-directory":
        proof["working-directory"] = "/tmp"
    elif tamper in ("coverage-skip", "postgres-skip", "transitive-skip"):
        job = {
            "coverage-skip": "coverage-gate",
            "postgres-skip": "idea-management-action-postgres",
            "transitive-skip": "lint-typecheck-security",
        }[tamper]
        jobs[job]["if"] = "${{ false }}"
    elif tamper == "prerequisite-step-skip":
        jobs["coverage-gate"]["steps"][0]["if"] = False
    elif tamper == "prerequisite-waiver":
        jobs["idea-management-action-postgres"]["continue-on-error"] = True
    elif tamper == "missing-dependency":
        jobs["coverage-gate"]["needs"].append("missing-job")
    elif tamper == "dependency-cycle":
        jobs["coverage-gate"]["needs"].append("docker-build")
    elif tamper == "invalid-needs":
        docker["needs"] = {"coverage-gate": True}
    elif tamper == "upload-before-proof":
        docker["steps"][4:6] = reversed(docker["steps"][4:6])
    elif tamper == "extra-command":
        docker["steps"].insert(4, {"run": "echo MAKEFLAGS=--ignore-errors >> $GITHUB_ENV"})
    elif tamper == "missing-upload-errors":
        docker["steps"][5]["with"]["if-no-files-found"] = "warn"
    elif tamper == "matrix-exclusion":
        jobs["test-suites"]["strategy"]["matrix"]["exclude"] = [{"suite": "unit"}]
    elif tamper == "image-matrix":
        docker["strategy"] = {"matrix": {"include": []}}
    elif tamper == "job-container":
        docker["container"] = "custom-runner:latest"
    elif tamper == "checkout-ref":
        docker["steps"][0]["with"]["ref"] = "main"
    elif tamper in ("build-revision", "proof-revision"):
        docker["steps"][3 if tamper == "build-revision" else 4]["env"]["GIT_SHA"] = (
            "a" * 40 + "; true #"
        )
    path = tmp_path / name
    path.write_text(yaml.safe_dump(workflow), encoding="utf-8")
    assert len(docker_image_evidence_violations(path)) == 1


@pytest.mark.parametrize("name", ["pr-merge-gate.yml", "main-releasability.yml"])
def test_structured_policy_accepts_failure_preserving_bash_and_quoted_keys(tmp_path, name):
    workflow = yaml.safe_load(Path(".github/workflows", name).read_text(encoding="utf-8"))
    workflow["defaults"] = {"run": {"shell": "bash"}}
    workflow["jobs"]["docker-build"]["steps"][4]["shell"] = "bash"
    for job in workflow["jobs"].values():
        for step in job.get("steps", []):
            if "name" in step and step["name"] != "Verify image financial recovery":
                step["name"] = "Validated execution step"
    path = tmp_path / name
    path.write_text(yaml.safe_dump(workflow, default_style='"'), encoding="utf-8")
    assert docker_image_evidence_violations(path) == []


@pytest.mark.parametrize("tamper", ["missing", "malformed", "version", "profile", "duplicate"])
def test_missing_or_invalid_execution_policy_fails_closed(tmp_path, monkeypatch, tamper):
    from scripts import image_workflow_policy

    original = image_workflow_policy.POLICY_PATH.read_text(encoding="utf-8")
    policy_path = tmp_path / "policy.json"
    if tamper == "malformed":
        policy_path.write_text("{", encoding="utf-8")
    elif tamper == "duplicate":
        policy_path.write_text(
            original.replace(
                '"schemaVersion": "v1",', '"schemaVersion": "v1", "schemaVersion": "v1",'
            ),
            encoding="utf-8",
        )
    elif tamper != "missing":
        policy = json.loads(original)
        if tamper == "version":
            policy["schemaVersion"] = "v0"
        else:
            policy["workflows"]["pr-merge-gate.yml"]["lint-typecheck-security"] = []
        policy_path.write_text(json.dumps(policy), encoding="utf-8")
    monkeypatch.setattr(image_workflow_policy, "POLICY_PATH", policy_path)
    assert docker_image_evidence_violations(Path(".github/workflows/pr-merge-gate.yml"))


def test_main_revision_assertion_cannot_be_replaced_with_success(tmp_path):
    name = "main-releasability.yml"
    workflow = yaml.safe_load(Path(".github/workflows", name).read_text(encoding="utf-8"))
    workflow["jobs"]["exact-revision-assertion"]["steps"][1]["run"] = "exit 0"
    path = tmp_path / name
    path.write_text(yaml.safe_dump(workflow), encoding="utf-8")
    assert docker_image_evidence_violations(path)


@pytest.mark.parametrize("tamper", ["duplicate", "escaped-key", "unsafe-tag", "malformed"])
def test_structured_policy_rejects_ambiguous_or_invalid_yaml(tmp_path, tamper):
    name = "pr-merge-gate.yml"
    original = Path(".github/workflows", name).read_text(encoding="utf-8")
    changed = {
        "duplicate": original.replace("  docker-build:", "  docker-build: {}\n  docker-build:"),
        "escaped-key": original.replace(
            "  docker-build:", '  docker-build:\n    "\\u0069f": false'
        ),
        "unsafe-tag": "!!python/object/apply:builtins.dict []",
        "malformed": "jobs: [",
    }[tamper]
    path = tmp_path / name
    path.write_text(changed, encoding="utf-8")
    assert len(docker_image_evidence_violations(path)) == 1


def test_image_requires_exact_revision_and_immutable_identity():
    assert validate_image(IMAGE, REVISION) == IMAGE["Id"]
    for revision in ("", "unknown", "a" * 39, "c" * 40):
        with pytest.raises(ValueError):
            validate_image(IMAGE, revision)


@pytest.mark.parametrize("field,value", [("Id", "tag:latest"), ("Config", {})])
def test_missing_or_mutable_image_metadata_fails(field, value):
    payload = deepcopy(IMAGE)
    payload[field] = value
    with pytest.raises(ValueError):
        validate_image(payload, REVISION)


def test_root_image_is_not_shipped_runtime():
    payload = deepcopy(IMAGE)
    payload["Config"]["User"] = "root"
    with pytest.raises(ValueError):
        validate_image(payload, REVISION)


@pytest.mark.parametrize("outcome", ["", "<skipped/>", "<failure/>", "<error/>"])
def test_result_accounting_rejects_nonexecuted_or_failed_cases(tmp_path, outcome):
    path = tmp_path / "results.xml"
    path.write_text(
        "<testsuites><testsuite>"
        + "".join(f'<testcase name="{name}">{outcome}</testcase>' for name in NAMES)
        + "</testsuite></testsuites>",
        encoding="utf-8",
    )
    if outcome:
        with pytest.raises(ValueError):
            validate_results(path)
    else:
        assert validate_results(path) == list(NAMES)


@pytest.mark.parametrize("names", [(), NAMES[:2], NAMES + (NAMES[0],), ("unrelated",) * 3])
def test_empty_missing_duplicate_or_wrong_cases_fail(tmp_path, names):
    path = tmp_path / "results.xml"
    path.write_text(
        "<testsuites><testsuite>"
        + "".join(f'<testcase name="{name}"/>' for name in names)
        + "</testsuite></testsuites>",
        encoding="utf-8",
    )
    with pytest.raises(ValueError):
        validate_results(path)


@pytest.mark.parametrize(
    "tamper",
    [
        "remove",
        "waive",
        "waive-expression",
        "skip-literal",
        "skip-expression",
        "skip-quoted",
        "job-skip",
        "job-skip-expression",
        "job-skip-quoted",
        "job-waive",
        "job-waive-expression",
        "masked-command",
        "commented-command",
    ],
)
def test_image_financial_workflow_verdict_cannot_be_removed_or_waived(tmp_path, tamper):
    from pathlib import Path

    for name in ("pr-merge-gate.yml", "main-releasability.yml"):
        original = Path(".github/workflows", name).read_text(encoding="utf-8")
        assert docker_image_evidence_violations(Path(".github/workflows", name)) == []
        if tamper == "remove":
            changed = original.replace("run: make test-image-financial-runtime", "run: true")
        elif tamper == "masked-command":
            changed = original.replace(
                "run: make test-image-financial-runtime",
                "run: make test-image-financial-runtime || true",
            )
        elif tamper == "commented-command":
            changed = original.replace(
                "run: make test-image-financial-runtime", "# run: make test-image-financial-runtime"
            )
        elif tamper.startswith("job-"):
            properties = {
                "job-skip": "if: false",
                "job-skip-expression": "if: ${{ false }}",
                "job-skip-quoted": "'if': false",
                "job-waive": "continue-on-error: true",
                "job-waive-expression": "continue-on-error: ${{ true }}",
            }
            changed = original.replace(
                "  docker-build:", "  docker-build:\n    " + properties[tamper]
            )
        elif tamper == "waive":
            changed = original.replace(
                "- name: Verify image financial recovery",
                "- name: Verify image financial recovery\n        continue-on-error: true",
            )
        else:
            properties = {
                "waive-expression": "continue-on-error: ${{ true }}",
                "skip-literal": "if: false",
                "skip-expression": "if: ${{ false }}",
                "skip-quoted": "'if': false",
            }
            changed = original.replace(
                "- name: Verify image financial recovery",
                "- name: Verify image financial recovery\n        " + properties[tamper],
            )
        path = tmp_path / name
        path.write_text(changed, encoding="utf-8")
        assert len(docker_image_evidence_violations(path)) == 1


def test_financial_step_cannot_be_displaced_to_another_job_or_duplicated(tmp_path):
    from pathlib import Path

    from scripts.workflow_policy_gate import _step_block

    for name in ("pr-merge-gate.yml", "main-releasability.yml"):
        original = Path(".github/workflows", name).read_text(encoding="utf-8")
        step = "      " + _step_block(original, "Verify image financial recovery")
        for changed in (
            original.replace(step, "") + "\n  unrelated-job:\n    steps:\n" + step,
            original.replace(step, step + "\n" + step),
            original.replace("  docker-build:", "  renamed-image-job:"),
        ):
            path = tmp_path / name
            path.write_text(changed, encoding="utf-8")
            assert docker_image_evidence_violations(path), changed[-1200:]
