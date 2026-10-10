"""Present admission races and unavailable fresh writes preserve one immutable winner."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from threading import Barrier, Lock

import pytest

from src.api.services.composite_monthly_eligibility import (
    CompositeMonthlyEligibilityApplicationService,
    MonthlyApprovalRequest,
)
from src.api.services.historical_policy_admission import (
    HistoricalPolicyAdmissionApplicationService,
    HistoricalPolicyAdmissionRequest,
)
from src.infrastructure.composites.in_memory import InMemoryDpmCompositeRepository
from src.core.composite_repository import DpmCompositeConflictError
from tests.composite_historical_policy_helpers import historical_contract_material
from tests.composite_monthly_amendment_helpers import seed_complete_monthly_root


@pytest.mark.parametrize(
    "actors", [("current-maker", "current-maker"), ("current-maker", "other-maker")]
)
def test_concurrent_policy_admission_returns_exact_retained_winner(actors):
    port, expected, *_ = historical_contract_material()
    original = InMemoryDpmCompositeRepository()
    scope, _, _ = seed_complete_monthly_root(original)
    repository = InMemoryDpmCompositeRepository()
    repository.save_definition(definition=original.get_definition(**scope))
    barrier = Barrier(2)
    verify = port.verify
    counter = 0
    lock = Lock()

    def clock():
        nonlocal counter
        with lock:
            counter += 1
            return (
                datetime.fromisoformat(expected.proposed_at) + timedelta(seconds=counter)
            ).strftime("%Y-%m-%dT%H:%M:%S.%fZ")

    def simultaneous(request):
        proof = verify(request)
        barrier.wait(timeout=10)
        return proof

    port.verify = simultaneous
    service = HistoricalPolicyAdmissionApplicationService(repository, port, clock)
    command = HistoricalPolicyAdmissionRequest(reference=port.mapping.reference)

    def propose(actor):
        try:
            return service.propose(
                **scope,
                month="2026-09",
                proposal_revision=expected.proposal_revision,
                actor_id=actor,
                command=command,
            )
        except ValueError as error:
            return str(error)

    with ThreadPoolExecutor(max_workers=2) as workers:
        results = list(workers.map(propose, actors))
    proposals = [item for item in results if not isinstance(item, str)]
    assert len({item.content_hash for item in proposals}) == 1
    assert len(proposals) == (2 if len(set(actors)) == 1 else 1)
    if len(set(actors)) > 1:
        assert any("IMMUTABLE_CONFLICT" in item for item in results if isinstance(item, str))
    port.available = False
    # Exact retained intent returns without reaching the now unavailable/barrier port.
    assert propose(proposals[0].proposed_by) == proposals[0]
    assert repository.get_monthly_policy_approval(**scope, month="2026-09") is None


def test_missing_definition_and_atomic_store_failure_do_not_create_admission(monkeypatch):
    port, proposal, *_ = historical_contract_material()
    repository = InMemoryDpmCompositeRepository()
    original = InMemoryDpmCompositeRepository()
    scope, _, _ = seed_complete_monthly_root(original)
    service = HistoricalPolicyAdmissionApplicationService(
        repository, port, lambda: proposal.proposed_at
    )
    command = HistoricalPolicyAdmissionRequest(reference=port.mapping.reference)
    key = dict(**scope, month="2026-09", proposal_revision=proposal.proposal_revision)
    with pytest.raises(ValueError, match="DEFINITION_NOT_FOUND"):
        service.propose(**key, actor_id=proposal.proposed_by, command=command)
    repository.save_definition(definition=original.get_definition(**scope))
    failure = DpmCompositeConflictError("controlled-atomic-store-failure")

    def fail(**kwargs):
        raise failure

    monkeypatch.setattr(repository, "save_monthly_policy_proposal", fail)
    with pytest.raises(DpmCompositeConflictError) as refused:
        service.propose(**key, actor_id=proposal.proposed_by, command=command)
    assert refused.value is failure
    assert repository.get_monthly_policy_proposal(**key) is None


def test_unavailable_current_policy_check_does_not_publish_or_change_original_proposal():
    port, proposal, *_ = historical_contract_material()
    repository = InMemoryDpmCompositeRepository()
    original = InMemoryDpmCompositeRepository()
    scope, _, _ = seed_complete_monthly_root(original)
    repository.save_definition(definition=original.get_definition(**scope))
    repository.save_monthly_policy_proposal(proposal=proposal)
    port.available = False
    service = CompositeMonthlyEligibilityApplicationService(
        repository, historical_admission=port, clock=lambda: "2026-10-10T01:01:00.000000Z"
    )
    with pytest.raises(ValueError, match="ADMISSION_UNAVAILABLE"):
        service.approve_policy(
            **scope,
            month="2026-09",
            proposal_revision=proposal.proposal_revision,
            actor_id="independent-checker",
            command=MonthlyApprovalRequest(expected_proposal_content_hash=proposal.content_hash),
        )
    assert (
        repository.get_monthly_policy_proposal(
            **scope, month="2026-09", proposal_revision=proposal.proposal_revision
        )
        == proposal
    )
    assert repository.get_monthly_policy_approval(**scope, month="2026-09") is None
    assert (
        repository.list_publications(
            tenant_id=scope["tenant_id"], after_sequence=0, limit=100
        ).items
        == []
    )
