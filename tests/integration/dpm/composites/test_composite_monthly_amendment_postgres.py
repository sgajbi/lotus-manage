"""Owning transaction, concurrency and custody guards for source amendments."""

from concurrent.futures import ThreadPoolExecutor
import json

import psycopg
from psycopg.rows import dict_row
import pytest

from src.core.composite_eligibility.monthly_amendment import MonthlyAmendmentProposal
from src.core.composite_eligibility.evaluation_control import MonthlyEvaluationProposal
from src.core.composite_eligibility.publication import build_monthly_publication
from src.infrastructure.composites import membership_store, universe_store
from src.infrastructure.composites.postgres import PostgresDpmCompositeRepository
from tests.composite_monthly_amendment_helpers import (
    corrected_monthly_proposal,
    seed_complete_monthly_root,
    retain_following_month,
)
from tests.integration.dpm.composites.test_composite_staged_upgrade_postgres import payload_rows
from tests.integration.dpm.network_runtime import disposable_database


@pytest.fixture
def correction():
    with disposable_database() as dsn:
        repository = PostgresDpmCompositeRepository(dsn=dsn)
        scope, original, parent = seed_complete_monthly_root(repository, coverage_to="2026-10-31")
        proposal = corrected_monthly_proposal(
            original, parent, sequence=original.publication_sequence
        )
        repository.save_universe_attestation(attestation=proposal.universe)
        yield dsn, repository, scope, original, parent, proposal


def retained_state(dsn):
    with psycopg.connect(dsn, row_factory=dict_row) as connection:
        return payload_rows(connection)


def test_actual_staged_root_refuses_ordinary_amendment_approval_without_writes():
    from tests.composite_monthly_amendment_staged_helpers import staged_root_amendment

    with disposable_database() as dsn:
        repository = PostgresDpmCompositeRepository(dsn=dsn)
        proposal, parent = staged_root_amendment(repository)
        before = retained_state(dsn)
        with pytest.raises(ValueError, match="STAGED_ROOT_UNSUPPORTED"):
            repository.save_monthly_evaluation_approval(approval=approval_for(proposal, parent))
        assert retained_state(dsn) == before


def approval_for(proposal, parent):
    return build_monthly_publication(
        proposal,
        parent,
        approved_by="synthetic-independent-amendment-checker",
        approved_at="2026-10-02T02:00:00.000000Z",
    )[0]


@pytest.mark.parametrize("claim", ["receipt", "original", "sequence"])
def test_invalid_amendment_authority_rolls_back_before_any_custody_write(correction, claim):
    dsn, repository, _, _, _, proposal = correction
    wire = proposal.model_dump(mode="json")
    if claim == "sequence":
        wire["amendment"]["expected_current_publication_sequence"] += 1
        code = "STALE_PROJECTION"
    else:
        field = "predecessor_receipt_binding" if claim == "receipt" else "original_approval_binding"
        wire["amendment"][field]["digest"] = "sha256:" + "a" * 64
        code = "PREDECESSOR_RECEIPT_MISMATCH" if claim == "receipt" else "ORIGINAL_MISMATCH"
    wire["content_hash"] = ""
    invalid = MonthlyAmendmentProposal.model_validate(wire)
    before = retained_state(dsn)
    with pytest.raises(ValueError, match=code):
        repository.save_monthly_evaluation_proposal(proposal=invalid)
    assert retained_state(dsn) == before


def test_failure_after_canonical_writes_rolls_back_approval_and_publication(
    correction, monkeypatch
):
    dsn, repository, _, _, parent, proposal = correction
    repository.save_monthly_evaluation_proposal(proposal=proposal)
    approval = approval_for(proposal, parent)
    before = retained_state(dsn)
    store = universe_store.store_universe_attestation

    def fail_after_store(**kwargs):
        store(**kwargs)
        raise RuntimeError("injected-after-owning-canonical-writes")

    with monkeypatch.context() as failing:
        failing.setattr(universe_store, "store_universe_attestation", fail_after_store)
        with pytest.raises(RuntimeError, match="injected-after-owning-canonical-writes"):
            repository.save_monthly_evaluation_approval(approval=approval)
    assert retained_state(dsn) == before
    repository.save_monthly_evaluation_approval(approval=approval)
    assert len(retained_state(dsn)["dpm_composite_monthly_evaluation_approvals"]) == 2


def test_earlier_month_refuses_later_retained_approval_under_current_projection(correction):
    dsn, repository, scope, original, parent, _ = correction
    following = retain_following_month(repository, original, parent)
    publications = repository.list_publications(
        tenant_id=scope["tenant_id"], after_sequence=0, limit=10
    )
    proposal = corrected_monthly_proposal(
        original, following, sequence=publications.items[-1].sequence
    )
    repository.save_universe_attestation(attestation=proposal.universe)
    before = retained_state(dsn)
    with pytest.raises(ValueError, match="DEPENDENT_MONTH_UNSUPPORTED"):
        repository.save_monthly_evaluation_proposal(proposal=proposal)
    assert retained_state(dsn) == before


def test_concurrent_source_corrections_have_one_atomic_postgres_winner(correction):
    dsn, repository, scope, original, parent, proposal = correction
    competitor = corrected_monthly_proposal(
        original, parent, sequence=original.publication_sequence, cash="200", revision=3
    )
    for item in (proposal, competitor):
        repository.save_universe_attestation(attestation=item.universe)
        repository.save_monthly_evaluation_proposal(proposal=item)

    def compete(item):
        try:
            approval = approval_for(item, parent)
            repository.save_monthly_evaluation_approval(approval=approval)
            return approval
        except ValueError as error:
            assert "STALE_AUTHORITY" in str(error)
            return None

    with ThreadPoolExecutor(max_workers=2) as workers:
        results = list(workers.map(compete, (proposal, competitor)))
    assert len([item for item in results if item is not None]) == 1
    state = retained_state(dsn)
    assert len(state["dpm_composite_monthly_evaluation_approvals"]) == 2
    assert len(state["dpm_composite_membership_publications"]) == 3
    assert (
        repository.resolve_monthly_eligibility_evidence(
            **scope,
            evaluation_revision=original.approval.proposal.evaluation_revision,
            approval_content_hash=original.approval.content_hash,
        )
        == original
    )


@pytest.mark.parametrize("mutation", ["null", "kind", "version", "predecessor"])
def test_database_proposal_shape_and_predecessor_guards_refuse_invalid_rows(correction, mutation):
    dsn, repository, _, _, _, proposal = correction
    repository.save_monthly_evaluation_proposal(proposal=proposal)
    wire = proposal.model_dump(mode="json")
    constraint = "monthly_evaluation_amendment_wire"
    if mutation == "null":
        wire["amendment"] = None
    elif mutation == "kind":
        wire["amendment"]["correction_kind"] = "POLICY_CHANGE"
    elif mutation == "version":
        wire["product_version"] = "v3"
    else:
        for field in ("predecessor_approval_binding", "expected_authority_binding"):
            wire["amendment"][field]["digest"] = "sha256:" + "a" * 64
        constraint = "monthly_evaluation_proposal_predecessor_fk"
    before = retained_state(dsn)
    with pytest.raises(psycopg.IntegrityError) as refused:
        with psycopg.connect(dsn) as connection:
            connection.execute(
                "UPDATE dpm_composite_monthly_evaluation_proposals SET payload_json=%s::jsonb "
                "WHERE evaluation_revision=%s",
                (json.dumps(wire), proposal.evaluation_revision),
            )
    assert refused.value.diag.constraint_name == constraint
    assert retained_state(dsn) == before


@pytest.mark.parametrize("mutation", ["null", "kind", "version"])
def test_database_approval_shape_guard_refuses_invalid_wire(correction, mutation):
    dsn, repository, _, _, parent, proposal = correction
    repository.save_monthly_evaluation_proposal(proposal=proposal)
    approval = approval_for(proposal, parent)
    repository.save_monthly_evaluation_approval(approval=approval)
    wire = approval.model_dump(mode="json")
    if mutation == "null":
        wire["proposal"]["amendment"] = None
    elif mutation == "kind":
        wire["proposal"]["amendment"]["correction_kind"] = "POLICY_CHANGE"
    else:
        wire["product_version"] = "v1"
    before = retained_state(dsn)
    with pytest.raises(psycopg.errors.CheckViolation) as refused:
        with psycopg.connect(dsn) as connection:
            connection.execute(
                "UPDATE dpm_composite_monthly_evaluation_approvals SET payload_json=%s::jsonb "
                "WHERE evaluation_revision=%s",
                (json.dumps(wire), proposal.evaluation_revision),
            )
    assert refused.value.diag.constraint_name == "monthly_evaluation_approval_amendment_wire"
    assert retained_state(dsn) == before


def insert_approval(connection, approval):
    proposal = approval.proposal
    scope = proposal.policy_approval.proposal.policy.scope
    connection.execute(
        """INSERT INTO dpm_composite_monthly_evaluation_approvals
        (tenant_id, composite_id, definition_version, month, evaluation_revision,
        membership_revision, content_hash, payload_json)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s::jsonb)""",
        (
            scope.tenant_id,
            scope.composite_id,
            scope.definition_version,
            proposal.evaluation.month,
            proposal.evaluation_revision,
            proposal.target_membership_revision,
            approval.content_hash,
            approval.model_dump_json(),
        ),
    )


def test_database_successor_uniqueness_refuses_a_fork_and_rolls_back_projection(correction):
    dsn, repository, _, original, parent, proposal = correction
    competitor = corrected_monthly_proposal(
        original, parent, sequence=original.publication_sequence, cash="200", revision=3
    )
    for item in (proposal, competitor):
        repository.save_universe_attestation(attestation=item.universe)
        repository.save_monthly_evaluation_proposal(proposal=item)
    repository.save_monthly_evaluation_approval(approval=approval_for(proposal, parent))
    approval, member, universe = build_monthly_publication(
        competitor,
        parent,
        approved_by="synthetic-independent-checker",
        approved_at="2026-10-02T02:00:00.000000Z",
    )
    before = retained_state(dsn)
    with pytest.raises(psycopg.errors.UniqueViolation) as refused:
        with psycopg.connect(dsn, row_factory=dict_row) as connection:
            membership_store.store_membership_revision(connection=connection, revision=member)
            universe_store.store_universe_attestation(connection=connection, attestation=universe)
            insert_approval(connection, approval)
    assert refused.value.diag.constraint_name == "monthly_evaluation_amendment_one_successor"
    assert retained_state(dsn) == before


def test_database_monthly_root_guard_still_refuses_another_ordinary_approval(correction):
    dsn, repository, _, _, parent, proposal = correction
    wire = proposal.model_dump(mode="json")
    wire.pop("amendment")
    wire.update(product_version="v1", content_hash="")
    ordinary = MonthlyEvaluationProposal.model_validate(wire)
    repository.save_monthly_evaluation_proposal(proposal=ordinary)
    approval, member, universe = build_monthly_publication(
        ordinary,
        parent,
        approved_by="synthetic-independent-checker",
        approved_at="2026-10-02T02:00:00.000000Z",
    )
    before = retained_state(dsn)
    with pytest.raises(psycopg.errors.UniqueViolation) as refused:
        with psycopg.connect(dsn, row_factory=dict_row) as connection:
            membership_store.store_membership_revision(connection=connection, revision=member)
            universe_store.store_universe_attestation(connection=connection, attestation=universe)
            insert_approval(connection, approval)
    assert refused.value.diag.constraint_name == "monthly_evaluation_one_root"
    assert retained_state(dsn) == before
    with pytest.raises(ValueError, match="ACTIVE_EVALUATION_CONFLICT"):
        repository.save_monthly_evaluation_approval(approval=approval)
    assert retained_state(dsn) == before


@pytest.mark.parametrize("profile", ["v1", "v2"])
def test_retained_source_correction_reopens_exact_original_and_amended_graphs(profile):
    with disposable_database() as dsn:
        repository = PostgresDpmCompositeRepository(dsn=dsn)
        scope, original, parent = seed_complete_monthly_root(
            repository, definition_product_version=profile
        )
        proposal = corrected_monthly_proposal(
            original, parent, sequence=original.publication_sequence
        )
        repository.save_universe_attestation(attestation=proposal.universe)
        repository.save_monthly_evaluation_proposal(proposal=proposal)
        approval, corrected, _ = build_monthly_publication(
            proposal,
            parent,
            approved_by="synthetic-independent-amendment-checker",
            approved_at="2026-10-02T02:00:00.000000Z",
        )
        repository.save_monthly_evaluation_approval(approval=approval)
        amended = repository.resolve_monthly_eligibility_evidence(
            **scope,
            evaluation_revision=proposal.evaluation_revision,
            approval_content_hash=approval.content_hash,
        )
        assert amended.product_version == "v2"
        assert amended.lineage == proposal.amendment
        assert corrected.content_hash != parent.content_hash
        assert amended.approval.proposal.evaluation.included_count == 0
        assert original.approval.proposal.evaluation.included_count == 1
        fresh = PostgresDpmCompositeRepository(dsn=dsn)
        for receipt in (original, amended):
            assert (
                fresh.resolve_monthly_eligibility_evidence(
                    **scope,
                    evaluation_revision=receipt.approval.proposal.evaluation_revision,
                    approval_content_hash=receipt.approval.content_hash,
                )
                == receipt
            )
            fresh.save_monthly_evaluation_proposal(proposal=receipt.approval.proposal)
            fresh.save_monthly_evaluation_approval(approval=receipt.approval)
        with psycopg.connect(dsn, row_factory=dict_row) as connection:
            assert (
                connection.execute(
                    "SELECT count(*) AS count FROM dpm_composite_membership_publications"
                ).fetchone()["count"]
                == 3
            )
