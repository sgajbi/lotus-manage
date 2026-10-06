"""Real PostgreSQL atomic publication, restart and observed conflicting writers.

The producer input is explicitly synthetic; this does not qualify a Core supplier.
"""

from concurrent.futures import ThreadPoolExecutor
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

from src.api.dependencies import get_composite_monthly_eligibility_service
from src.api.main import app
from src.api.services.composite_monthly_eligibility import (
    CompositeMonthlyEligibilityApplicationService,
    MonthlyApprovalRequest,
    MonthlyProposalRequest,
)
from src.api.services.composite_monthly_evaluation import (
    CompositeMonthlyEvaluationApplicationService,
    MonthlyEvaluationRequest,
)
from src.core.composite_eligibility.publication import build_monthly_publication
from src.core.composite_eligibility.source import MonthlyEligibilitySourceResolution
from src.core.composite_repository import DpmCompositeConflictError
from src.core.composite_membership import DpmCompositeMembershipRevision
from src.infrastructure.composites import evaluation_control, universe_store
from src.infrastructure.composites.postgres import PostgresDpmCompositeRepository
from tests.composite_monthly_eligibility_helpers import (
    prospective_proposal_body,
    retained_repository,
    source_snapshot,
)
from tests.integration.dpm.postgres_prerequisite import postgres_dsn_or_skip


@pytest.fixture
def material():
    dsn = postgres_dsn_or_skip("monthly evaluation atomic PostgreSQL publication")
    repository = PostgresDpmCompositeRepository(dsn=dsn)
    snapshot = source_snapshot()
    snapshot.tenant_id += "-" + uuid.uuid4().hex[:12]
    seed, universe = retained_repository(snapshot)
    scope = dict(
        tenant_id=snapshot.tenant_id,
        composite_id=snapshot.composite_id,
        definition_version=snapshot.definition_version,
    )
    repository.save_definition(definition=seed.get_definition(**scope))
    parent = seed.get_membership_revision(**scope, membership_revision="synthetic-membership")
    repository.save_membership_revision(revision=parent)
    repository.save_universe_attestation(attestation=universe)
    state = {"now": "2026-08-20T01:00:00.000000Z"}

    class SyntheticSource:
        def resolve(self, request):
            return MonthlyEligibilitySourceResolution(snapshot, owner_service="synthetic-source")

    configuration = CompositeMonthlyEligibilityApplicationService(
        repository=repository, source=SyntheticSource(), clock=lambda: state["now"]
    )
    policy = configuration.propose_policy(
        **scope,
        month="2026-09",
        proposal_revision="synthetic-config-r1",
        actor_id="synthetic-maker",
        command=MonthlyProposalRequest.model_validate(prospective_proposal_body(universe)),
    )
    approved_policy = configuration.approve_policy(
        **scope,
        month="2026-09",
        proposal_revision=policy.proposal_revision,
        actor_id="synthetic-checker",
        command=MonthlyApprovalRequest(expected_proposal_content_hash=policy.content_hash),
    )
    state["now"] = "2026-10-01T01:00:00.000000Z"
    service = CompositeMonthlyEvaluationApplicationService(configuration=configuration)
    command = MonthlyEvaluationRequest(
        month="2026-09",
        policy_approval_content_hash=approved_policy.content_hash,
        parent_membership_revision=parent.membership_revision,
        parent_membership_content_hash=parent.content_hash,
        attestation_version=universe.attestation_version,
        universe_content_hash=universe.content_hash,
        target_membership_revision="synthetic-evaluated-membership",
        correlation_id="synthetic-evaluation",
    )
    return dsn, repository, scope, configuration, service, command, parent


def candidate(material, revision="synthetic-evaluation-r1", target=None):
    _, _, scope, _, service, command, _ = material
    if target is not None:
        command = command.model_copy(update={"target_membership_revision": target})
    return service.propose(
        **scope, evaluation_revision=revision, actor_id="synthetic-maker", command=command
    )


def test_registered_producer_survives_fresh_default_reader_and_approval(material):
    dsn, repository, scope, configuration, _, command, _ = material
    url = f"/api/v1/rebalance/composites/{scope['composite_id']}/definitions/{scope['definition_version']}/monthly-eligibility/evaluations/synthetic-evaluation-r1"
    maker = {
        "X-Tenant-Id": scope["tenant_id"],
        "X-Actor-Id": "synthetic-maker",
        "X-Role": "DPM_COMPOSITE_ADMIN",
    }
    prior = app.dependency_overrides.copy()
    app.dependency_overrides[get_composite_monthly_eligibility_service] = lambda: configuration
    try:
        with TestClient(app) as client:
            response = client.put(url, json=command.model_dump(mode="json"), headers=maker)
            assert response.status_code == 200, response.text
            proposal = response.json()
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(prior)
    environment = os.environ.copy()
    environment.update(
        DPM_COMPOSITE_POSTGRES_DSN=dsn,
        MONTHLY_PROOF_URL=url,
        MONTHLY_PROOF_TENANT=scope["tenant_id"],
        MONTHLY_PROOF_HASH=proposal["content_hash"],
    )
    script = (
        "import json,os; from fastapi.testclient import TestClient; from src.api.main import app; "
        "assert not app.dependency_overrides; client=TestClient(app)"
        "\nwith client:"
        "\n headers={'X-Tenant-Id':os.environ['MONTHLY_PROOF_TENANT'],'X-Actor-Id':'synthetic-checker','X-Role':'DPM_COMPOSITE_ADMIN'}"
        "\n url=os.environ['MONTHLY_PROOF_URL']"
        "\n proposal=client.get(url,headers=headers); assert proposal.status_code==200,proposal.text"
        "\n body={'expected_proposal_content_hash':os.environ['MONTHLY_PROOF_HASH']}"
        "\n approved=client.put(url+'/approval',headers=headers,json=body); assert approved.status_code==200,approved.text"
        "\n replay=client.put(url+'/approval',headers=headers,json=body); assert replay.json()==approved.json(),replay.text"
        "\n read=client.get(url+'/approval',headers=headers); assert read.json()==approved.json(),read.text"
        "\n print(json.dumps({'proposal':proposal.json(),'approval':approved.json()},sort_keys=True))"
    )
    restarted = subprocess.run(
        [sys.executable, "-c", script],
        env=environment,
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    )
    wire = json.loads(restarted.stdout)
    assert wire["proposal"] == proposal
    assert wire["approval"]["proposal"] == proposal
    membership = repository.get_membership_revision(
        **scope, membership_revision=command.target_membership_revision
    )
    assert membership.content_hash == wire["approval"]["membership_content_hash"]
    assert membership.policy_version == "synthetic-policy" != "synthetic-config-r1"
    assert (
        len(
            repository.list_publications(
                tenant_id=scope["tenant_id"], after_sequence=0, limit=10
            ).items
        )
        == 2
    )


def test_failure_after_membership_and_universe_rolls_back_all_publication_rows(
    material, monkeypatch
):
    _, repository, scope, _, _, _, parent = material
    proposal = candidate(material)
    approval, _, _ = build_monthly_publication(
        proposal, parent, approved_by="synthetic-checker", approved_at="2026-10-01T02:00:00.000000Z"
    )
    original = universe_store.store_universe_attestation

    def fail_after_universe(**kwargs):
        original(**kwargs)
        raise RuntimeError("synthetic injected failure after canonical writes")

    with monkeypatch.context() as patch:
        patch.setattr(universe_store, "store_universe_attestation", fail_after_universe)
        with pytest.raises(RuntimeError, match="injected failure"):
            repository.save_monthly_evaluation_approval(approval=approval)
    assert (
        repository.get_membership_revision(
            **scope, membership_revision=proposal.target_membership_revision
        )
        is None
    )
    assert (
        repository.get_monthly_evaluation_approval(
            **scope, evaluation_revision=proposal.evaluation_revision
        )
        is None
    )
    assert (
        repository.get_universe_attestation(
            **scope,
            membership_revision=proposal.target_membership_revision,
            attestation_version=proposal.evaluation_revision,
        )
        is None
    )
    assert (
        len(
            repository.list_publications(
                tenant_id=scope["tenant_id"], after_sequence=0, limit=10
            ).items
        )
        == 1
    )
    assert (
        repository.get_monthly_evaluation_proposal(
            **scope, evaluation_revision=proposal.evaluation_revision
        )
        == proposal
    )
    repository.save_monthly_evaluation_approval(approval=approval)
    repository.save_monthly_evaluation_approval(approval=approval)
    assert (
        repository.get_monthly_evaluation_approval(
            **scope, evaluation_revision=proposal.evaluation_revision
        )
        == approval
    )
    assert (
        len(
            repository.list_publications(
                tenant_id=scope["tenant_id"], after_sequence=0, limit=10
            ).items
        )
        == 2
    )


def test_intervening_canonical_publication_refuses_stale_evaluation_parent(material):
    _, repository, scope, _, _, _, parent = material
    proposal = candidate(material)
    approval, _, _ = build_monthly_publication(
        proposal, parent, approved_by="synthetic-checker", approved_at="2026-10-01T02:00:00.000000Z"
    )
    body = parent.model_dump(mode="json", exclude={"content_hash"})
    body.update(
        membership_revision="synthetic-intervening-membership",
        supersedes_membership_revision=parent.membership_revision,
        affected_from="2026-09-01",
        affected_to="2026-09-30",
    )
    intervening = DpmCompositeMembershipRevision.model_validate(body)
    repository.save_membership_revision(revision=intervening)
    with pytest.raises(DpmCompositeConflictError, match="STALE_MEMBERSHIP"):
        repository.save_monthly_evaluation_approval(approval=approval)
    assert (
        repository.get_monthly_evaluation_approval(
            **scope, evaluation_revision=proposal.evaluation_revision
        )
        is None
    )
    assert (
        repository.get_membership_revision(
            **scope, membership_revision=proposal.target_membership_revision
        )
        is None
    )
    assert (
        repository.get_monthly_evaluation_proposal(
            **scope, evaluation_revision=proposal.evaluation_revision
        )
        == proposal
    )
    assert (
        len(
            repository.list_publications(
                tenant_id=scope["tenant_id"], after_sequence=0, limit=10
            ).items
        )
        == 2
    )


def test_observed_publication_lock_serializes_competing_month_approvals(material):
    dsn, repository, scope, _, _, _, parent = material
    first = candidate(material)
    second = candidate(material, "synthetic-evaluation-r2", "synthetic-other-membership")
    instant = "2026-10-01T02:00:00.000000Z"
    first_approval, _, _ = build_monthly_publication(
        first, parent, approved_by="synthetic-checker", approved_at=instant
    )
    second_approval, _, _ = build_monthly_publication(
        second, parent, approved_by="synthetic-checker", approved_at=instant
    )
    with psycopg.connect(dsn, row_factory=dict_row) as blocker:
        blocker_pid = blocker.info.backend_pid
        evaluation_control.save_approval(blocker, first_approval)
        with ThreadPoolExecutor(max_workers=1) as executor:
            competing = executor.submit(
                repository.save_monthly_evaluation_approval, approval=second_approval
            )
            observed = False
            try:
                deadline = time.monotonic() + 10
                with psycopg.connect(dsn, autocommit=True, row_factory=dict_row) as observer:
                    while time.monotonic() < deadline:
                        if (
                            observer.execute(
                                """SELECT 1 FROM pg_stat_activity WHERE datname=current_database()
                            AND application_name='lotus-manage-composite-repository' AND wait_event_type='Lock'
                            AND %s=ANY(pg_blocking_pids(pid)) AND query LIKE '%%pg_advisory_xact_lock%%'""",
                                (blocker_pid,),
                            ).fetchone()
                            is not None
                        ):
                            observed = True
                            break
                        time.sleep(0.025)
                assert observed, "A real overlapping publication-lock wait must be observed"
            finally:
                blocker.commit()
            with pytest.raises(DpmCompositeConflictError, match="ACTIVE_EVALUATION_CONFLICT"):
                competing.result(timeout=10)
    assert (
        repository.get_monthly_evaluation_approval(
            **scope, evaluation_revision=first.evaluation_revision
        )
        == first_approval
    )
    assert (
        repository.get_membership_revision(
            **scope, membership_revision=second.target_membership_revision
        )
        is None
    )
    assert (
        len(
            repository.list_publications(
                tenant_id=scope["tenant_id"], after_sequence=0, limit=10
            ).items
        )
        == 2
    )
