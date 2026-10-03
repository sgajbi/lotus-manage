"""Structured, fail-closed execution policy for the image financial proof lane."""

from __future__ import annotations

import json
from pathlib import Path

import yaml


POLICY_PATH = (
    Path(__file__).resolve().parents[1] / "contracts/ci/image-financial-execution-policy.v1.json"
)
ROOT_ENV = {
    "PIP_DISABLE_PIP_VERSION_CHECK": "1",
    "PYTHONUNBUFFERED": "1",
    "PYTHON_VERSION": "3.12",
    "COVERAGE_FAIL_UNDER": "99",
}
MAIN_REF = "${{ inputs.expected_sha && 'main' || github.ref_name }}"
REQUIRED_NEEDS = {
    "docker-build": {"coverage-gate", "idea-management-action-postgres"},
    "coverage-gate": {"test-suites", "idea-management-action-postgres"},
    "test-suites": {"lint-typecheck-security"},
    "idea-management-action-postgres": {"lint-typecheck-security"},
    "lint-typecheck-security": set(),
    "exact-revision-assertion": set(),
}


def _workflow_env(path):
    env = dict(ROOT_ENV)
    if path.name == "main-releasability.yml":
        env.update(LOTUS_RELEASE_GIT_REF=MAIN_REF, LOTUS_QUALITY_REF_NAME=MAIN_REF)
    return env


class _UniqueSafeLoader(yaml.SafeLoader):
    def construct_mapping(self, node, deep=False):
        keys = [self.construct_object(key, deep=deep) for key, _ in node.value]
        if any(not isinstance(key, (str, bool)) for key in keys):
            raise ValueError("Workflow mapping keys must be scalar names")
        if len(keys) != len(set(keys)) or "<<" in keys:
            raise ValueError("Duplicate or merged workflow keys are not permitted")
        return super().construct_mapping(node, deep=deep)


def _mapping(value, location):
    if not isinstance(value, dict):
        raise ValueError(f"{location} must be a mapping")
    return value


def _unique_json_mapping(pairs):
    result = dict(pairs)
    if len(result) != len(pairs):
        raise ValueError("Duplicate execution-policy keys are not permitted")
    return result


def _execution_controls(scope, location, *, step=False, expected_env=None):
    env = _mapping(scope.get("env", {}), f"{location} env")
    if not step and env != (expected_env or {}):
        raise ValueError(f"{location} requires canonical native-lane environment values and scope")
    run = (
        scope
        if step
        else _mapping(
            _mapping(scope.get("defaults", {}), f"{location} defaults").get("run", {}),
            f"{location} run defaults",
        )
    )
    if run.get("shell") not in (None, "bash") or "working-directory" in run:
        raise ValueError(f"{location} requires the failure-preserving repository-root shell")


def _required_jobs(jobs, name, active=None, completed=None):
    active = set() if active is None else active
    completed = set() if completed is None else completed
    if name in active:
        raise ValueError("Image proof dependency cycle")
    if name in completed:
        return
    if name not in jobs:
        raise ValueError(f"Image proof dependency job is missing: {name}")
    job = _mapping(jobs[name], f"job {name}")
    active.add(name)
    needs = job.get("needs", [])
    needs = [needs] if isinstance(needs, str) else needs
    if not isinstance(needs, list) or any(not isinstance(item, str) for item in needs):
        raise ValueError(f"job {name} needs must identify actual jobs")
    for dependency in needs:
        yield from _required_jobs(jobs, dependency, active, completed)
    active.remove(name)
    completed.add(name)
    yield name, job


def image_workflow_violations(path: Path) -> list[str]:
    try:
        policy = _mapping(
            json.loads(
                POLICY_PATH.read_text(encoding="utf-8"), object_pairs_hook=_unique_json_mapping
            ),
            "execution policy",
        )
        if policy.get("schemaVersion") != "v1":
            raise ValueError("Image execution policy requires supported schema v1")
        profiles = _mapping(policy.get("stepSequences"), "execution-policy step sequences")
        workflow_profiles = _mapping(
            _mapping(policy.get("workflows"), "execution-policy workflows").get(path.name),
            "execution-policy workflow profiles",
        )
        workflow = _mapping(
            yaml.load(path.read_text(encoding="utf-8"), Loader=_UniqueSafeLoader), "workflow"
        )
        jobs = _mapping(workflow.get("jobs"), "workflow jobs")
        _execution_controls(workflow, "workflow", expected_env=_workflow_env(path))
        for name, job in _required_jobs(jobs, "docker-build"):
            expected_needs = REQUIRED_NEEDS.get(name)
            if name == "lint-typecheck-security" and path.name == "main-releasability.yml":
                expected_needs = {"exact-revision-assertion"}
            needs = job.get("needs", [])
            needs = [needs] if isinstance(needs, str) else needs
            if set(needs) != expected_needs:
                raise ValueError(f"required job {name} must retain its canonical prerequisites")
            if "if" in job or "continue-on-error" in job:
                raise ValueError(
                    f"required job {name} must execute unconditionally without waivers"
                )
            _execution_controls(job, f"job {name}")
            if "container" in job:
                raise ValueError(f"required job {name} must use the native runner")
            if "strategy" in job:
                strategy = _mapping(job["strategy"], f"job {name} strategy")
                matrix = _mapping(strategy.get("matrix"), f"job {name} matrix")
                expected = [
                    {"suite": suite, "path": f"tests/{suite}"}
                    for suite in ("unit", "integration", "e2e")
                ]
                if name != "test-suites" or matrix != {"include": expected}:
                    raise ValueError(f"required job {name} must retain its complete test matrix")
            steps = job.get("steps")
            if not isinstance(steps, list) or not steps:
                raise ValueError(f"required job {name} has no executable steps")
            for index, value in enumerate(steps):
                step = _mapping(value, f"job {name} step {index}")
                if "if" in step or "continue-on-error" in step:
                    raise ValueError(
                        f"required job {name} step {index} must execute without waivers"
                    )
                _execution_controls(step, f"job {name} step {index}", step=True)
            checkouts = [step for step in steps if step.get("uses") == "actions/checkout@v6"]
            checkout_inputs = (
                {"fetch-depth": 0} if name in {"lint-typecheck-security", "docker-build"} else {}
            )
            if len(checkouts) != 1 or checkouts[0].get("with", {}) != checkout_inputs:
                raise ValueError(f"required job {name} must check out only the evaluated revision")
            actual_sequence = [
                {
                    key: value
                    for key, value in step.items()
                    if key != "name" and not (key == "shell" and value == "bash")
                }
                for step in steps
            ]
            profile = workflow_profiles.get(name)
            if not isinstance(profile, str):
                raise ValueError(f"required job {name} has no valid execution-policy profile")
            expected_sequence = profiles.get(profile)
            if not isinstance(expected_sequence, list) or actual_sequence != expected_sequence:
                raise ValueError(f"required job {name} must retain its complete execution sequence")
        docker = jobs["docker-build"]
        steps = docker["steps"]
        if steps[4].get("name") != "Verify image financial recovery":
            raise ValueError("Image proof requires its named financial recovery step")
    except (ValueError, OSError, yaml.YAMLError) as exc:
        return [f"{path.as_posix()}: {exc}"]
    return []
