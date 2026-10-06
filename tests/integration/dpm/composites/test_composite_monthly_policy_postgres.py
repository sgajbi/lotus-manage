"""Registered configuration control, real PostgreSQL custody and observed lock conflicts."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import json
import os
import subprocess
import sys
import time
import uuid

import psycopg
from psycopg.rows import dict_row
import pytest
from fastapi.testclient import TestClient

import src.api.dependencies as dependencies
from src.api.main import app
from src.core.composite_eligibility.approval import MonthlyPolicyApproval, MonthlyPolicyProposal
from src.core.composite_eligibility.policy import (
    MonthlyPolicyLayer,
    MonthlyPolicyScope,
    month_window,
    resolve_monthly_policy,
)
from src.core.composite_authority_models import EvidenceBinding
from src.core.composite_membership import DpmCompositeDefinition, DpmCompositeSourceAuthority
from src.core.composite_repository import DpmCompositeConflictError
from src.infrastructure.composites.postgres import PostgresDpmCompositeRepository
from src.infrastructure.composites import policy_control
from tests.integration.dpm.postgres_prerequisite import postgres_dsn_or_skip


def configuration(
    repository, tenant, composite, definition_version="synthetic-definition", revision="r1"
):
    future = datetime.now(timezone.utc).date().replace(day=1) + timedelta(days=62)
    month = future.isoformat()[:7]
    first, last = month_window(month)
    definition = DpmCompositeDefinition(
        tenant_id=tenant,
        composite_id=composite,
        definition_version=definition_version,
        display_name="Synthetic monthly control",
        strategy_code="synthetic-strategy",
        reporting_currency="USD",
        inception_date="2000-01-01",
        eligibility_policy_version="synthetic-policy",
        source_authority=DpmCompositeSourceAuthority(policy_version="synthetic-authority"),
        created_by="synthetic-maker",
        correlation_id="synthetic-definition",
    )
    if (
        repository.get_definition(
            tenant_id=tenant, composite_id=composite, definition_version=definition_version
        )
        is None
    ):
        repository.save_definition(definition=definition)
    layer = MonthlyPolicyLayer(
        level="PLATFORM",
        policy_id="synthetic-policy",
        revision=revision,
        effective_from=first,
        effective_to=last,
        flow_threshold="0.10",
        cash_threshold="0.05",
        permitted_overrides=[],
    )
    policy = resolve_monthly_policy(
        [layer],
        month=month,
        scope=MonthlyPolicyScope(
            tenant_id=tenant,
            composite_id=composite,
            definition_version=definition_version,
            strategy_code=definition.strategy_code,
        ),
    )
    instant = datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")
    proposal = MonthlyPolicyProposal(
        proposal_revision=revision,
        eligibility_policy_version=definition.eligibility_policy_version,
        policy=policy,
        proposed_by="synthetic-maker",
        proposed_at=instant,
        attachments=[
            EvidenceBinding(
                product_name="SyntheticMethodEvidence",
                product_version="v1",
                revision="r1",
                digest="sha256:" + "b" * 64,
            )
        ],
    )
    return proposal


def test_registered_policy_control_survives_fresh_process_without_overrides(monkeypatch):
    dsn = postgres_dsn_or_skip("monthly policy registered PostgreSQL custody")
    repository = PostgresDpmCompositeRepository(dsn=dsn)
    suffix = uuid.uuid4().hex[:12]
    tenant, composite = "synthetic-tenant-" + suffix, "synthetic-composite-" + suffix
    material = configuration(repository, tenant, composite)
    scope = material.policy.scope
    month = material.policy.month
    url = f"/api/v1/rebalance/composites/{composite}/definitions/{scope.definition_version}/monthly-eligibility/policies/{month}"
    monkeypatch.setenv("DPM_COMPOSITE_POSTGRES_DSN", dsn)
    monkeypatch.setattr(dependencies, "_POSTGRES_COMPOSITE_REPOSITORY", None)
    assert not app.dependency_overrides
    maker = {
        "X-Tenant-Id": tenant,
        "X-Actor-Id": "synthetic-maker",
        "X-Role": "DPM_COMPOSITE_ADMIN",
    }
    body = {
        "layers": [layer.model_dump(mode="json") for layer in material.policy.layers],
        "attachments": [item.model_dump(mode="json") for item in material.attachments],
    }
    with TestClient(app) as client:
        response = client.put(url + "/proposals/r1", json=body, headers=maker)
        assert response.status_code == 200, response.text
        proposal = response.json()
        assert client.put(url + "/proposals/r1", json=body, headers=maker).json() == proposal
        approved = client.put(
            url + "/proposals/r1/approval",
            headers=maker | {"X-Actor-Id": "synthetic-checker"},
            json={"expected_proposal_content_hash": proposal["content_hash"]},
        )
        assert approved.status_code == 200, approved.text
        wire = approved.json()
        assert wire["proposal"] == proposal
        assert wire["official_activation"] == "UNAVAILABLE"
    environment = os.environ.copy()
    environment["MONTHLY_PROOF_URL"] = url + "/approval"
    environment["MONTHLY_PROOF_TENANT"] = tenant
    script = (
        "import json,os; from fastapi.testclient import TestClient; from src.api.main import app; "
        "assert not app.dependency_overrides; "
        "client=TestClient(app); "
        "\nwith client:"
        "\n response=client.get(os.environ['MONTHLY_PROOF_URL'],headers={'X-Tenant-Id':os.environ['MONTHLY_PROOF_TENANT'],'X-Actor-Id':'synthetic-reader','X-Role':'DPM_COMPOSITE_ADMIN'})"
        "\n assert response.status_code==200,response.text"
        "\n print(json.dumps(response.json(),sort_keys=True))"
    )
    restarted = subprocess.run(
        [sys.executable, "-c", script],
        env=environment,
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    )
    assert json.loads(restarted.stdout) == wire
    assert repository.list_publications(tenant_id=tenant, after_sequence=0, limit=10).items == []


@pytest.mark.parametrize("other_definition", [False, True])
def test_real_overlapping_approvals_preserve_one_configuration_across_versions(other_definition):
    dsn = postgres_dsn_or_skip("monthly policy observed PostgreSQL conflict")
    repository = PostgresDpmCompositeRepository(dsn=dsn)
    suffix = uuid.uuid4().hex[:12]
    tenant, composite = "synthetic-tenant-" + suffix, "synthetic-composite-" + suffix
    first = configuration(repository, tenant, composite)
    second = configuration(
        repository,
        tenant,
        composite,
        definition_version="synthetic-definition-v2"
        if other_definition
        else "synthetic-definition",
        revision="r2",
    )
    repository.save_monthly_policy_proposal(proposal=first)
    repository.save_monthly_policy_proposal(proposal=second)
    instant = datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")
    first_approval = MonthlyPolicyApproval(
        proposal=first, approved_by="synthetic-checker", approved_at=instant
    )
    second_approval = MonthlyPolicyApproval(
        proposal=second, approved_by="synthetic-checker", approved_at=instant
    )
    with psycopg.connect(dsn, row_factory=dict_row) as blocker:
        blocker_pid = blocker.info.backend_pid
        policy_control.save_approval(blocker, first_approval)
        with ThreadPoolExecutor(max_workers=1) as executor:
            competing = executor.submit(
                repository.save_monthly_policy_approval, approval=second_approval
            )
            observed = False
            deadline = time.monotonic() + 10
            try:
                with psycopg.connect(dsn, autocommit=True, row_factory=dict_row) as observer:
                    while time.monotonic() < deadline:
                        row = observer.execute(
                            """SELECT 1 FROM pg_stat_activity WHERE datname=current_database()
                            AND application_name='lotus-manage-composite-repository'
                            AND wait_event_type='Lock' AND %s=ANY(pg_blocking_pids(pid))
                            AND query LIKE '%%INSERT INTO dpm_composite_monthly_policy_approvals%%'""",
                            (blocker_pid,),
                        ).fetchone()
                        if row is not None:
                            observed = True
                            break
                        time.sleep(0.025)
                assert observed, (
                    "No overlapping unique-key wait was observed; a call-entry barrier is insufficient"
                )
            finally:
                blocker.commit()
            with pytest.raises(DpmCompositeConflictError, match="ACTIVE_POLICY_CONFLICT"):
                competing.result(timeout=10)
    repository.save_monthly_policy_approval(approval=first_approval)
    retained = repository.get_monthly_policy_approval(
        tenant_id=tenant,
        composite_id=composite,
        definition_version=first.policy.scope.definition_version,
        month=first.policy.month,
    )
    assert retained == first_approval
    assert (
        repository.get_monthly_policy_approval(
            tenant_id="foreign",
            composite_id=composite,
            definition_version=first.policy.scope.definition_version,
            month=first.policy.month,
        )
        is None
    )
