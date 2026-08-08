from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.core.waves import DpmWaveSourceRef
from src.core.waves.campaign_definition_readiness import (
    _actor_entitlement_state,
    _approval_governance_status,
    _candidate_readiness,
    _definition_status_reason_codes,
    _eligible_portfolio_types,
    _expiry_readiness_state,
    build_bulk_review_campaign_definition_preview_readiness,
)
from src.core.waves.campaign_definition_lifecycle import (
    DpmBulkReviewCampaignDefinitionLifecycleError,
    _superseded_campaign_definition,
    _validated_active_replacement,
    _validated_replacement_version,
    retire_bulk_review_campaign_definition,
    supersede_bulk_review_campaign_definition,
)
from src.core.waves.campaign_definition_launch_history import (
    build_bulk_review_campaign_definition_launch_history_page,
    record_bulk_review_campaign_definition_launch,
)
from src.core.waves.campaign_definition_launch_execution import (
    DpmBulkReviewCampaignDefinitionLaunchBlocked,
    build_bulk_review_campaign_definition_launch_command,
)
from src.core.waves.campaign_definition_launch_package import _launch_basis_hash
from src.core.waves.campaign_definition_approval_decisions import (
    _append_approval_decision,
    _approval_decision_input,
    _build_decision,
    _existing_approval_decision,
    _validate_active_campaign_definition,
    build_bulk_review_campaign_definition_approval_decision_page,
    record_bulk_review_campaign_definition_approval_decision,
)
from src.core.waves.campaign_assignment_actions import (
    _build_action,
    build_bulk_review_campaign_definition_assignment_action_page,
    record_bulk_review_campaign_definition_assignment_action,
)
from src.core.waves.campaign_assignment_tasks import (
    _build_task,
    _build_transition,
    _task_hash,
    build_bulk_review_campaign_definition_assignment_task_page,
    open_bulk_review_campaign_definition_assignment_task,
    transition_bulk_review_campaign_definition_assignment_task,
)
from src.core.waves.campaign_maker_checker_controls import (
    _build_control,
    build_bulk_review_campaign_definition_maker_checker_control_page,
    record_bulk_review_campaign_definition_maker_checker_control,
)
from src.core.waves.campaign_definitions import (
    DpmBulkReviewCampaignDefinition,
    DpmBulkReviewCampaignDefinitionCandidate,
    DpmBulkReviewCampaignDefinitionGovernance,
    _apply_campaign_definition_content_hash,
    _campaign_definition_hash_payload,
    _has_eligible_portfolio_type,
    _validate_campaign_definition_structure,
    _validate_lifecycle_fields_absent,
    _validate_required_lifecycle_value,
    bulk_review_campaign_definition_hash,
)
from src.core.waves.campaign_repository import DpmBulkReviewCampaignDefinitionConflictError
from src.infrastructure.waves.campaign_definitions import (
    InMemoryDpmBulkReviewCampaignDefinitionRepository,
    PostgresDpmBulkReviewCampaignDefinitionRepository,
    _definition_matches_filters,
    _definition_sort_key,
    _import_psycopg,
    _load_campaign_definition_payload,
    _paged_definitions,
    _payload,
    _workflow_read_model_projection,
)
import src.infrastructure.waves.campaign_definitions as campaign_definition_infra


def _definition(
    *,
    tenant_id: str = "tenant-sg",
    campaign_id: str = "campaign-holdings-apple-tesla-20260510",
    display_name: str = "Apple and Tesla holdings review",
) -> DpmBulkReviewCampaignDefinition:
    return DpmBulkReviewCampaignDefinition(
        tenant_id=tenant_id,
        campaign_id=campaign_id,
        campaign_version="2026.05",
        display_name=display_name,
        as_of_date="2026-05-10",
        rationale="Review discretionary portfolios affected by the Apple and Tesla campaign.",
        candidates=[
            DpmBulkReviewCampaignDefinitionCandidate(
                portfolio_id="PB_SG_GLOBAL_BAL_001",
                mandate_id="MANDATE_PB_SG_GLOBAL_BAL_001",
                portfolio_type="DISCRETIONARY",
                source_refs=[
                    DpmWaveSourceRef(
                        source_system="lotus-core",
                        source_type="HoldingsAsOf",
                        source_id="holdings-asof-pb-sg-global-bal-001",
                    )
                ],
            )
        ],
        governance=DpmBulkReviewCampaignDefinitionGovernance(
            approval_ref="BRC-APPROVAL-2026-05",
            approved_by="cio_ops_committee",
            approved_at="2026-05-09T09:30:00+08:00",
        ),
        created_by="ops",
        correlation_id="corr-campaign-definition-001",
    )


def _approval_required_definition(*, campaign_id: str) -> DpmBulkReviewCampaignDefinition:
    return DpmBulkReviewCampaignDefinition.model_validate(
        {
            **_definition(
                campaign_id=campaign_id,
                display_name=f"Approval required {campaign_id}",
            ).model_dump(mode="python"),
            "governance": None,
            "content_hash": "",
        }
    )


def test_campaign_definition_validation_rejects_bad_candidates_and_hash() -> None:
    with pytest.raises(ValueError, match="BULK_REVIEW_CAMPAIGN_PORTFOLIO_TYPE_REQUIRED"):
        DpmBulkReviewCampaignDefinitionCandidate(
            portfolio_id="PB_SG_GLOBAL_BAL_001",
            portfolio_type=" ",
            source_refs=[
                DpmWaveSourceRef(
                    source_system="lotus-core",
                    source_type="HoldingsAsOf",
                    source_id="holdings-asof-pb-sg-global-bal-001",
                )
            ],
        )

    with pytest.raises(ValueError, match="BULK_REVIEW_CAMPAIGN_SOURCE_REFS_REQUIRED"):
        DpmBulkReviewCampaignDefinitionCandidate(
            portfolio_id="PB_SG_GLOBAL_BAL_001",
            portfolio_type="DISCRETIONARY",
            source_refs=[],
        )

    with pytest.raises(ValueError, match="BULK_REVIEW_CAMPAIGN_PORTFOLIO_TYPES_REQUIRED"):
        DpmBulkReviewCampaignDefinition(
            tenant_id="tenant-sg",
            campaign_id="campaign-empty-types",
            campaign_version="2026.05",
            display_name="Empty type campaign",
            as_of_date="2026-05-10",
            rationale="Invalid campaign.",
            eligible_portfolio_types=[],
            candidates=[_definition().candidates[0]],
            created_by="ops",
            correlation_id="corr-campaign-definition-001",
        )

    with pytest.raises(ValueError, match="BULK_REVIEW_CAMPAIGN_CANDIDATE_PORTFOLIOS_REQUIRED"):
        DpmBulkReviewCampaignDefinition(
            tenant_id="tenant-sg",
            campaign_id="campaign-empty-candidates",
            campaign_version="2026.05",
            display_name="Empty candidate campaign",
            as_of_date="2026-05-10",
            rationale="Invalid campaign.",
            candidates=[],
            created_by="ops",
            correlation_id="corr-campaign-definition-001",
        )

    with pytest.raises(ValueError, match="BULK_REVIEW_CAMPAIGN_DEFINITION_HASH_MISMATCH"):
        DpmBulkReviewCampaignDefinition(
            tenant_id="tenant-sg",
            campaign_id="campaign-bad-hash",
            campaign_version="2026.05",
            display_name="Bad hash campaign",
            as_of_date="2026-05-10",
            rationale="Invalid campaign.",
            candidates=[_definition().candidates[0]],
            created_by="ops",
            correlation_id="corr-campaign-definition-001",
            content_hash="sha256:bad",
        )


def test_campaign_definition_structure_helpers_require_scope_and_candidates() -> None:
    assert _has_eligible_portfolio_type([" ", "DISCRETIONARY"])
    assert not _has_eligible_portfolio_type([" ", ""])

    valid_definition = _definition()
    _validate_campaign_definition_structure(valid_definition)

    missing_portfolio_types = _definition().model_copy(
        update={"eligible_portfolio_types": [" ", ""]}
    )
    with pytest.raises(ValueError, match="BULK_REVIEW_CAMPAIGN_PORTFOLIO_TYPES_REQUIRED"):
        _validate_campaign_definition_structure(missing_portfolio_types)

    missing_candidates = _definition().model_copy(update={"candidates": []})
    with pytest.raises(ValueError, match="BULK_REVIEW_CAMPAIGN_CANDIDATE_PORTFOLIOS_REQUIRED"):
        _validate_campaign_definition_structure(missing_candidates)


def test_campaign_definition_content_hash_helper_applies_and_rejects_mismatch() -> None:
    definition = _definition().model_copy(update={"content_hash": ""})

    _apply_campaign_definition_content_hash(definition)

    assert definition.content_hash == bulk_review_campaign_definition_hash(definition)

    mismatched = _definition().model_copy(update={"content_hash": "sha256:bad"})
    with pytest.raises(ValueError, match="BULK_REVIEW_CAMPAIGN_DEFINITION_HASH_MISMATCH"):
        _apply_campaign_definition_content_hash(mismatched)


def test_campaign_definition_loader_tolerates_legacy_stored_hash() -> None:
    definition = _definition()
    legacy_payload = definition.model_dump(mode="json")
    legacy_payload["content_hash"] = "sha256:legacy-campaign-definition-hash"

    loaded = _load_campaign_definition_payload(legacy_payload)

    assert loaded.campaign_id == definition.campaign_id
    assert loaded.campaign_version == definition.campaign_version
    assert loaded.content_hash == definition.content_hash


def test_campaign_definition_hash_preserves_pre_approval_decision_payloads() -> None:
    definition = _definition()
    persisted_payload = definition.model_dump(mode="json")
    persisted_payload.pop("approval_decisions", None)

    reloaded = DpmBulkReviewCampaignDefinition.model_validate(persisted_payload)

    assert reloaded.approval_decisions == []
    assert bulk_review_campaign_definition_hash(reloaded) == definition.content_hash


def test_campaign_definition_hash_ignores_generated_creation_timestamp() -> None:
    definition = _definition()
    later_definition = definition.model_copy(
        update={"created_at": datetime(2026, 5, 11, 9, 30, tzinfo=timezone.utc)}
    )

    assert bulk_review_campaign_definition_hash(later_definition) == definition.content_hash


@pytest.mark.parametrize(
    "collection_field",
    [
        "approval_decisions",
        "assignment_actions",
        "assignment_tasks",
        "maker_checker_controls",
    ],
)
def test_campaign_definition_hash_preserves_legacy_empty_evidence_collections(
    collection_field: str,
) -> None:
    definition = _definition()
    persisted_payload = definition.model_dump(mode="json")
    persisted_payload.pop(collection_field, None)

    reloaded = DpmBulkReviewCampaignDefinition.model_validate(persisted_payload)

    assert getattr(reloaded, collection_field) == []
    assert bulk_review_campaign_definition_hash(reloaded) == definition.content_hash


def test_campaign_definition_hash_preserves_absent_source_batch_lineage() -> None:
    definition = _definition()
    hash_payload = _campaign_definition_hash_payload(definition, include_hash=False)
    candidate_source_ref = hash_payload["candidates"][0]["source_refs"][0]

    assert "source_batch_fingerprint" not in candidate_source_ref
    assert bulk_review_campaign_definition_hash(definition) == definition.content_hash

    source_ref_with_batch = DpmWaveSourceRef(
        source_system="lotus-core",
        source_type="HoldingsAsOf",
        source_id="holdings-asof-pb-sg-global-bal-001",
        source_batch_fingerprint="sha256:holdings-source-batch",
    )
    definition_with_batch = DpmBulkReviewCampaignDefinition.model_validate(
        {
            **definition.model_dump(mode="python"),
            "content_hash": "",
            "candidates": [
                {
                    **definition.candidates[0].model_dump(mode="python"),
                    "source_refs": [source_ref_with_batch],
                }
            ],
        }
    )
    batch_hash_payload = _campaign_definition_hash_payload(
        definition_with_batch, include_hash=False
    )
    batch_source_ref = batch_hash_payload["candidates"][0]["source_refs"][0]

    assert batch_source_ref["source_batch_fingerprint"] == "sha256:holdings-source-batch"
    assert bulk_review_campaign_definition_hash(definition_with_batch) != definition.content_hash


def test_campaign_definition_hash_preserves_source_owned_selection_basis_metadata() -> None:
    definition = _definition()
    source_ref_with_source_owned_metadata = DpmWaveSourceRef(
        source_system="lotus-core",
        source_type="HoldingsAsOf",
        source_id="holdings-asof-pb-sg-global-bal-001",
        selection_basis={
            "basis_type": "SOURCE_OWNED_CANDIDATE_SELECTION",
            "source_batch_fingerprint": None,
        },
    )
    definition_with_metadata = DpmBulkReviewCampaignDefinition.model_validate(
        {
            **definition.model_dump(mode="python"),
            "content_hash": "",
            "candidates": [
                {
                    **definition.candidates[0].model_dump(mode="python"),
                    "source_refs": [source_ref_with_source_owned_metadata],
                }
            ],
        }
    )

    hash_payload = _campaign_definition_hash_payload(definition_with_metadata, include_hash=False)
    candidate_source_ref = hash_payload["candidates"][0]["source_refs"][0]

    assert "source_batch_fingerprint" not in candidate_source_ref
    assert candidate_source_ref["selection_basis"]["source_batch_fingerprint"] is None


def test_campaign_launch_basis_hash_preserves_absent_source_batch_lineage() -> None:
    definition = _definition()
    source_ref = definition.candidates[0].source_refs[0]
    explicit_none_ref = DpmWaveSourceRef.model_validate(source_ref.model_dump(mode="json"))
    explicit_none_definition = definition.model_copy(
        deep=True,
        update={
            "candidates": [
                definition.candidates[0].model_copy(
                    deep=True,
                    update={"source_refs": [explicit_none_ref]},
                )
            ]
        },
    )
    batch_ref = source_ref.model_copy(
        update={"source_batch_fingerprint": "sha256:holdings-source-batch"}
    )
    batch_definition = definition.model_copy(
        deep=True,
        update={
            "candidates": [
                definition.candidates[0].model_copy(
                    deep=True,
                    update={"source_refs": [batch_ref]},
                )
            ]
        },
    )

    assert _launch_basis_hash(definition) == _launch_basis_hash(explicit_none_definition)
    assert _launch_basis_hash(batch_definition) != _launch_basis_hash(definition)


def test_campaign_workflow_evidence_hashes_preserve_absent_source_batch_lineage() -> None:
    definition = _definition()
    source_ref = DpmWaveSourceRef(
        source_system="lotus-core",
        source_type="DpmPortfolioUniverseCandidate",
        source_id="dpm-universe-page-001",
        content_hash="sha256:" + ("1" * 64),
    )
    explicit_none_ref = DpmWaveSourceRef.model_validate(source_ref.model_dump(mode="json"))
    batch_ref = source_ref.model_copy(
        update={"source_batch_fingerprint": "sha256:dpm-universe-source-batch"}
    )

    base_decision = _build_decision(
        definition=definition,
        decision_type="APPROVED",
        decision_ref="BRC-APPROVAL-2026-05-001",
        decided_by="cio_ops_committee",
        decision_reason="Approved for bounded DPM campaign launch.",
        correlation_id="corr-campaign-approval-decision-001",
        source_refs=[source_ref],
    )
    explicit_none_decision = _build_decision(
        definition=definition,
        decision_type="APPROVED",
        decision_ref="BRC-APPROVAL-2026-05-001",
        decided_by="cio_ops_committee",
        decision_reason="Approved for bounded DPM campaign launch.",
        correlation_id="corr-campaign-approval-decision-001",
        source_refs=[explicit_none_ref],
    )
    batch_decision = _build_decision(
        definition=definition,
        decision_type="APPROVED",
        decision_ref="BRC-APPROVAL-2026-05-001",
        decided_by="cio_ops_committee",
        decision_reason="Approved for bounded DPM campaign launch.",
        correlation_id="corr-campaign-approval-decision-001",
        source_refs=[batch_ref],
    )

    assert explicit_none_decision.content_hash == base_decision.content_hash
    assert batch_decision.content_hash != base_decision.content_hash

    base_action = _build_action(
        definition=definition,
        action_type="ASSIGNED",
        action_ref="BRC-ASSIGN-2026-05-001",
        recorded_by="campaign_owner",
        action_reason="Assign portfolios for review.",
        assigned_actor_ids=["rm_sg_001"],
        escalation_tier="NONE",
        sla_posture="ON_TRACK",
        correlation_id="corr-campaign-assignment-action-001",
        source_refs=[source_ref],
    )
    explicit_none_action = _build_action(
        definition=definition,
        action_type="ASSIGNED",
        action_ref="BRC-ASSIGN-2026-05-001",
        recorded_by="campaign_owner",
        action_reason="Assign portfolios for review.",
        assigned_actor_ids=["rm_sg_001"],
        escalation_tier="NONE",
        sla_posture="ON_TRACK",
        correlation_id="corr-campaign-assignment-action-001",
        source_refs=[explicit_none_ref],
    )
    batch_action = _build_action(
        definition=definition,
        action_type="ASSIGNED",
        action_ref="BRC-ASSIGN-2026-05-001",
        recorded_by="campaign_owner",
        action_reason="Assign portfolios for review.",
        assigned_actor_ids=["rm_sg_001"],
        escalation_tier="NONE",
        sla_posture="ON_TRACK",
        correlation_id="corr-campaign-assignment-action-001",
        source_refs=[batch_ref],
    )

    assert explicit_none_action.content_hash == base_action.content_hash
    assert batch_action.content_hash != base_action.content_hash

    base_transition = _build_transition(
        definition=definition,
        task_id="brc_assignment_task_001",
        transition_type="OPENED",
        transition_ref="BRC-TASK-001:opened",
        transitioned_by="campaign_owner",
        from_status=None,
        to_status="OPEN",
        transition_reason="Open review task.",
        assigned_actor_ids=["rm_sg_001"],
        escalation_tier="NONE",
        sla_posture="ON_TRACK",
        due_at=None,
        correlation_id="corr-campaign-assignment-task-001",
        source_refs=[source_ref],
    )
    explicit_none_transition = _build_transition(
        definition=definition,
        task_id="brc_assignment_task_001",
        transition_type="OPENED",
        transition_ref="BRC-TASK-001:opened",
        transitioned_by="campaign_owner",
        from_status=None,
        to_status="OPEN",
        transition_reason="Open review task.",
        assigned_actor_ids=["rm_sg_001"],
        escalation_tier="NONE",
        sla_posture="ON_TRACK",
        due_at=None,
        correlation_id="corr-campaign-assignment-task-001",
        source_refs=[explicit_none_ref],
    )
    batch_transition = _build_transition(
        definition=definition,
        task_id="brc_assignment_task_001",
        transition_type="OPENED",
        transition_ref="BRC-TASK-001:opened",
        transitioned_by="campaign_owner",
        from_status=None,
        to_status="OPEN",
        transition_reason="Open review task.",
        assigned_actor_ids=["rm_sg_001"],
        escalation_tier="NONE",
        sla_posture="ON_TRACK",
        due_at=None,
        correlation_id="corr-campaign-assignment-task-001",
        source_refs=[batch_ref],
    )

    assert explicit_none_transition.content_hash == base_transition.content_hash
    assert batch_transition.content_hash != base_transition.content_hash

    base_task = _build_task(
        definition=definition,
        task_ref="BRC-TASK-001",
        task_type="ASSIGNMENT",
        opened_by="campaign_owner",
        task_reason="Open review task.",
        assigned_actor_ids=["rm_sg_001"],
        escalation_tier="NONE",
        sla_posture="ON_TRACK",
        due_at=None,
        correlation_id="corr-campaign-assignment-task-001",
        source_refs=[source_ref],
    )
    explicit_none_task = base_task.model_copy(
        update={"source_refs": [explicit_none_ref], "content_hash": ""}
    )
    batch_task = base_task.model_copy(update={"source_refs": [batch_ref], "content_hash": ""})

    assert _task_hash(explicit_none_task) == base_task.content_hash
    assert _task_hash(batch_task) != base_task.content_hash

    base_control = _build_control(
        definition=definition,
        control_action="SUBMITTED_FOR_REVIEW",
        control_ref="BRC-MC-001",
        recorded_by="campaign_owner",
        submitter_actor_id="campaign_owner",
        reviewer_actor_id=None,
        required_reviewer_role="cio_approver",
        control_outcome="PENDING",
        control_reason="Submit campaign for maker-checker review.",
        correlation_id="corr-campaign-maker-checker-001",
        source_refs=[source_ref],
    )
    explicit_none_control = _build_control(
        definition=definition,
        control_action="SUBMITTED_FOR_REVIEW",
        control_ref="BRC-MC-001",
        recorded_by="campaign_owner",
        submitter_actor_id="campaign_owner",
        reviewer_actor_id=None,
        required_reviewer_role="cio_approver",
        control_outcome="PENDING",
        control_reason="Submit campaign for maker-checker review.",
        correlation_id="corr-campaign-maker-checker-001",
        source_refs=[explicit_none_ref],
    )
    batch_control = _build_control(
        definition=definition,
        control_action="SUBMITTED_FOR_REVIEW",
        control_ref="BRC-MC-001",
        recorded_by="campaign_owner",
        submitter_actor_id="campaign_owner",
        reviewer_actor_id=None,
        required_reviewer_role="cio_approver",
        control_outcome="PENDING",
        control_reason="Submit campaign for maker-checker review.",
        correlation_id="corr-campaign-maker-checker-001",
        source_refs=[batch_ref],
    )

    assert explicit_none_control.content_hash == base_control.content_hash
    assert batch_control.content_hash != base_control.content_hash


def test_campaign_definition_retired_and_superseded_validation_edges() -> None:
    definition = _definition()
    retired_base = {
        **definition.model_dump(mode="python"),
        "status": "RETIRED",
        "retired_at": "2026-05-11T08:00:00Z",
        "retired_by": "ops",
        "retirement_reason": "Campaign completed.",
        "retirement_correlation_id": "corr-campaign-definition-retire-001",
        "content_hash": "",
    }
    for field_name, reason_code in [
        ("retired_at", "BULK_REVIEW_CAMPAIGN_RETIREMENT_TIMESTAMP_REQUIRED"),
        ("retired_by", "BULK_REVIEW_CAMPAIGN_RETIREMENT_ACTOR_REQUIRED"),
        ("retirement_reason", "BULK_REVIEW_CAMPAIGN_RETIREMENT_REASON_REQUIRED"),
        ("retirement_correlation_id", "BULK_REVIEW_CAMPAIGN_RETIREMENT_CORRELATION_REQUIRED"),
    ]:
        payload = {**retired_base, field_name: None}
        with pytest.raises(ValueError, match=reason_code):
            DpmBulkReviewCampaignDefinition.model_validate(payload)

    with pytest.raises(
        ValueError,
        match="BULK_REVIEW_CAMPAIGN_RETIRED_SUPERSESSION_FIELDS_FORBIDDEN",
    ):
        DpmBulkReviewCampaignDefinition.model_validate(
            {**retired_base, "superseded_by": "ops", "content_hash": ""}
        )

    superseded_base = {
        **definition.model_dump(mode="python"),
        "status": "SUPERSEDED",
        "superseded_at": "2026-05-12T08:00:00Z",
        "superseded_by": "ops",
        "supersession_reason": "Campaign candidate set refreshed.",
        "supersession_correlation_id": "corr-campaign-definition-supersede-001",
        "superseded_by_campaign_id": definition.campaign_id,
        "superseded_by_campaign_version": "2026.06",
        "superseded_by_content_hash": "sha256:replacement",
        "content_hash": "",
    }
    for field_name, reason_code in [
        ("superseded_at", "BULK_REVIEW_CAMPAIGN_SUPERSESSION_TIMESTAMP_REQUIRED"),
        ("superseded_by", "BULK_REVIEW_CAMPAIGN_SUPERSESSION_ACTOR_REQUIRED"),
        ("supersession_reason", "BULK_REVIEW_CAMPAIGN_SUPERSESSION_REASON_REQUIRED"),
        ("supersession_correlation_id", "BULK_REVIEW_CAMPAIGN_SUPERSESSION_CORRELATION_REQUIRED"),
        ("superseded_by_campaign_id", "BULK_REVIEW_CAMPAIGN_SUPERSESSION_CAMPAIGN_ID_REQUIRED"),
        (
            "superseded_by_campaign_version",
            "BULK_REVIEW_CAMPAIGN_SUPERSESSION_CAMPAIGN_VERSION_REQUIRED",
        ),
        ("superseded_by_content_hash", "BULK_REVIEW_CAMPAIGN_SUPERSESSION_CONTENT_HASH_REQUIRED"),
    ]:
        payload = {**superseded_base, field_name: None}
        with pytest.raises(ValueError, match=reason_code):
            DpmBulkReviewCampaignDefinition.model_validate(payload)

    with pytest.raises(
        ValueError,
        match="BULK_REVIEW_CAMPAIGN_SUPERSEDED_RETIREMENT_FIELDS_FORBIDDEN",
    ):
        DpmBulkReviewCampaignDefinition.model_validate(
            {**superseded_base, "retired_by": "ops", "content_hash": ""}
        )


def test_campaign_definition_lifecycle_helpers_preserve_reason_codes() -> None:
    definition = _definition()

    with pytest.raises(
        ValueError,
        match="BULK_REVIEW_CAMPAIGN_ACTIVE_LIFECYCLE_FIELDS_FORBIDDEN",
    ):
        definition.model_copy(update={"retired_by": "ops"})._validate_active_lifecycle()

    with pytest.raises(
        ValueError,
        match="BULK_REVIEW_CAMPAIGN_RETIREMENT_TIMESTAMP_REQUIRED",
    ):
        definition.model_copy(
            update={
                "status": "RETIRED",
                "retired_by": "ops",
                "retirement_reason": "Campaign completed.",
                "retirement_correlation_id": "corr-campaign-definition-retire-001",
            }
        )._validate_retired_lifecycle()

    with pytest.raises(
        ValueError,
        match="BULK_REVIEW_CAMPAIGN_SUPERSEDED_RETIREMENT_FIELDS_FORBIDDEN",
    ):
        definition.model_copy(
            update={
                "status": "SUPERSEDED",
                "superseded_at": datetime(2026, 5, 12, 8, 0, tzinfo=timezone.utc),
                "superseded_by": "ops",
                "supersession_reason": "Campaign candidate set refreshed.",
                "supersession_correlation_id": "corr-campaign-definition-supersede-001",
                "superseded_by_campaign_id": definition.campaign_id,
                "superseded_by_campaign_version": "2026.06",
                "superseded_by_content_hash": "sha256:replacement",
                "retired_by": "ops",
            }
        )._validate_superseded_lifecycle()


def test_lifecycle_required_value_helper_rejects_missing_and_blank_values() -> None:
    for value in [None, "  "]:
        with pytest.raises(ValueError, match="LIFECYCLE_VALUE_REQUIRED"):
            _validate_required_lifecycle_value(value, reason_code="LIFECYCLE_VALUE_REQUIRED")


def test_lifecycle_absent_fields_helper_rejects_present_values() -> None:
    with pytest.raises(ValueError, match="LIFECYCLE_FIELDS_FORBIDDEN"):
        _validate_lifecycle_fields_absent(
            [None, "ops"],
            reason_code="LIFECYCLE_FIELDS_FORBIDDEN",
        )


def test_in_memory_campaign_definition_repository_filters_and_conflicts() -> None:
    repository = InMemoryDpmBulkReviewCampaignDefinitionRepository()
    definition = _definition()
    repository.save_definition(definition=definition)
    repository.save_definition(definition=definition)

    assert (
        repository.get_definition(
            tenant_id=definition.tenant_id,
            campaign_id=definition.campaign_id,
            campaign_version=definition.campaign_version,
        )
        == definition
    )
    assert (
        repository.get_definition(
            tenant_id=definition.tenant_id,
            campaign_id="missing",
            campaign_version="2026.05",
        )
        is None
    )
    assert repository.list_definitions(
        tenant_id=definition.tenant_id,
        campaign_id=definition.campaign_id,
    ) == [definition]
    assert repository.list_definitions(
        tenant_id=definition.tenant_id,
        status="ACTIVE",
        as_of_date="2026-05-10",
    ) == [definition]
    assert repository.list_definitions(tenant_id=definition.tenant_id, offset=1) == []

    with pytest.raises(
        DpmBulkReviewCampaignDefinitionConflictError,
        match="BULK_REVIEW_CAMPAIGN_DEFINITION_IMMUTABLE_CONFLICT",
    ):
        repository.save_definition(definition=_definition(display_name="Changed name"))


def test_in_memory_campaign_definition_repository_isolates_tenant_scope() -> None:
    repository = InMemoryDpmBulkReviewCampaignDefinitionRepository()
    tenant_a = _definition(tenant_id="tenant-a", display_name="Tenant A campaign")
    tenant_b = _definition(tenant_id="tenant-b", display_name="Tenant B campaign")

    repository.save_definition(definition=tenant_a)
    repository.save_definition(definition=tenant_b)

    assert (
        repository.get_definition(
            tenant_id="tenant-a",
            campaign_id=tenant_a.campaign_id,
            campaign_version=tenant_a.campaign_version,
        )
        == tenant_a
    )
    assert (
        repository.get_definition(
            tenant_id="tenant-b",
            campaign_id=tenant_b.campaign_id,
            campaign_version=tenant_b.campaign_version,
        )
        == tenant_b
    )
    assert repository.list_definitions(tenant_id="tenant-a") == [tenant_a]
    assert repository.list_definitions(tenant_id="tenant-b") == [tenant_b]
    assert repository.list_definitions(
        tenant_id="tenant-a",
        campaign_id=tenant_b.campaign_id,
    ) == [tenant_a]

    tenant_b_task = open_bulk_review_campaign_definition_assignment_task(
        definition=tenant_b,
        task_ref="BRC-TASK-TENANT-B",
        task_type="ASSIGNMENT",
        opened_by="ops",
        task_reason="Tenant B PM acknowledgement.",
        assigned_actor_ids=["pm_tenant_b"],
        escalation_tier="PM",
        sla_posture="ON_TRACK",
        correlation_id="corr-tenant-b-task",
    )
    repository.record_definition_assignment_task(
        definition=tenant_b_task,
        expected_content_hash=tenant_b.content_hash,
    )

    assert (
        repository.list_definitions_by_workflow_projection(
            tenant_id="tenant-a",
            assigned_actor_id="pm_tenant_b",
            assignment_task_status="OPEN",
        )
        == []
    )
    assert repository.list_definitions_by_workflow_projection(
        tenant_id="tenant-b",
        assigned_actor_id="pm_tenant_b",
        assignment_task_status="OPEN",
    ) == [tenant_b_task]


def test_campaign_definition_list_helpers_filter_sort_and_page_definitions() -> None:
    older = _definition(campaign_id="campaign-alpha").model_copy(
        update={"as_of_date": "2026-05-09"}
    )
    newer = _definition(campaign_id="campaign-zulu").model_copy(update={"as_of_date": "2026-05-11"})
    retired = _definition(campaign_id="campaign-retired").model_copy(
        update={"status": "RETIRED", "as_of_date": "2026-05-12"}
    )

    assert _definition_matches_filters(
        newer,
        tenant_id=newer.tenant_id,
        campaign_id="campaign-zulu",
        status="ACTIVE",
        as_of_date="2026-05-11",
    )
    assert not _definition_matches_filters(
        retired,
        tenant_id=retired.tenant_id,
        campaign_id=None,
        status="ACTIVE",
        as_of_date=None,
    )
    assert _definition_sort_key(newer) > _definition_sort_key(older)
    assert _paged_definitions(
        definitions=[older, newer, retired],
        tenant_id=newer.tenant_id,
        campaign_id=None,
        status="ACTIVE",
        as_of_date=None,
        limit=1,
        offset=0,
    ) == [newer]


def test_campaign_definition_workflow_projection_pages_after_projection_filters() -> None:
    repository = InMemoryDpmBulkReviewCampaignDefinitionRepository()
    leading_non_match = _definition(campaign_id="campaign-z-non-match")
    first_match = _approval_required_definition(campaign_id="campaign-m-approval-required")
    second_match = _approval_required_definition(campaign_id="campaign-a-approval-required")
    for definition in [leading_non_match, first_match, second_match]:
        repository.save_definition(definition=definition)

    page = repository.list_definitions_by_workflow_projection(
        tenant_id=leading_non_match.tenant_id,
        next_action="RECORD_APPROVAL_DECISION",
        limit=1,
        offset=1,
    )

    assert page == [second_match]


def test_campaign_definition_launch_history_is_append_only_and_idempotent() -> None:
    repository = InMemoryDpmBulkReviewCampaignDefinitionRepository()
    definition = _definition()
    repository.save_definition(definition=definition)

    launched = record_bulk_review_campaign_definition_launch(
        definition=definition,
        wave_id="dwv_campaign_launch_001",
        launched_by="pm_001",
        requested_as_of_date="2026-05-10",
        correlation_id="corr-campaign-definition-launch-001",
        idempotency_key="campaign-launch:campaign-holdings-apple-tesla-20260510:2026.05:ready",
        launched_at=datetime(2026, 5, 10, tzinfo=timezone.utc),
    )
    replayed = record_bulk_review_campaign_definition_launch(
        definition=launched,
        wave_id="dwv_campaign_launch_001",
        launched_by="pm_001",
        requested_as_of_date="2026-05-10",
        correlation_id="corr-campaign-definition-launch-001",
        idempotency_key="campaign-launch:campaign-holdings-apple-tesla-20260510:2026.05:ready",
    )

    returned = repository.record_definition_launch(
        definition=launched,
        expected_content_hash=definition.content_hash,
    )

    assert returned == launched
    assert replayed == launched
    assert launched.content_hash != definition.content_hash
    assert len(launched.launch_history) == 1
    assert launched.launch_history[0].wave_id == "dwv_campaign_launch_001"
    assert (
        repository.get_definition(
            tenant_id=definition.tenant_id,
            campaign_id=definition.campaign_id,
            campaign_version=definition.campaign_version,
        )
        == launched
    )
    assert (
        repository.record_definition_launch(
            definition=launched,
            expected_content_hash=definition.content_hash,
        )
        == launched
    )
    assert (
        repository.record_definition_launch(
            expected_content_hash=definition.content_hash,
            definition=DpmBulkReviewCampaignDefinition.model_validate(
                {
                    **launched.model_dump(mode="python"),
                    "campaign_id": "missing-campaign",
                    "content_hash": "",
                }
            ),
        )
        is None
    )


def test_campaign_definition_launch_review_and_assignment_lifecycle_conflicts() -> None:
    definition = _definition()
    retired = DpmBulkReviewCampaignDefinition.model_validate(
        {
            **definition.model_dump(mode="python"),
            "status": "RETIRED",
            "retired_at": "2026-05-11T08:00:00Z",
            "retired_by": "ops",
            "retirement_reason": "Campaign completed.",
            "retirement_correlation_id": "corr-campaign-definition-retire-001",
            "content_hash": "",
        }
    )
    launched = record_bulk_review_campaign_definition_launch(
        definition=definition,
        wave_id="dwv_campaign_launch_001",
        launched_by="pm_001",
        requested_as_of_date="2026-05-10",
        correlation_id="corr-campaign-definition-launch-001",
        idempotency_key="campaign-launch:campaign-holdings-apple-tesla-20260510:2026.05:ready",
    )
    approved = record_bulk_review_campaign_definition_approval_decision(
        definition=definition,
        decision_type="APPROVED",
        decision_ref="BRC-APPROVAL-2026-05-001",
        decided_by="cio_ops_committee",
        decision_reason="Approved for bounded DPM campaign launch.",
        correlation_id="corr-campaign-approval-decision-001",
    )
    assigned = record_bulk_review_campaign_definition_assignment_action(
        definition=definition,
        action_type="ASSIGNED",
        action_ref="BRC-ASSIGN-2026-05-001",
        recorded_by="ops",
        action_reason="Route campaign to assigned PM.",
        assigned_actor_ids=["pm_001"],
        escalation_tier="PM",
        sla_posture="ON_TRACK",
        correlation_id="corr-campaign-assignment-action-001",
    )

    for updated in [launched, approved, assigned]:
        repository = InMemoryDpmBulkReviewCampaignDefinitionRepository()
        repository.save_definition(definition=retired)
        with pytest.raises(
            DpmBulkReviewCampaignDefinitionConflictError,
            match="BULK_REVIEW_CAMPAIGN_DEFINITION_LIFECYCLE_CONFLICT",
        ):
            if updated is launched:
                repository.record_definition_launch(
                    definition=updated,
                    expected_content_hash=definition.content_hash,
                )
            elif updated is approved:
                repository.record_definition_approval_decision(
                    definition=updated,
                    expected_content_hash=definition.content_hash,
                )
            else:
                repository.record_definition_assignment_action(
                    definition=updated,
                    expected_content_hash=definition.content_hash,
                )


@pytest.mark.parametrize(
    ("method_name", "first_builder", "second_builder"),
    [
        (
            "record_definition_launch",
            lambda definition: record_bulk_review_campaign_definition_launch(
                definition=definition,
                wave_id="dwv_campaign_launch_001",
                launched_by="pm_001",
                requested_as_of_date="2026-05-10",
                correlation_id="corr-campaign-definition-launch-001",
                idempotency_key=(
                    "campaign-launch:campaign-holdings-apple-tesla-20260510:2026.05:ready"
                ),
            ),
            lambda definition: record_bulk_review_campaign_definition_launch(
                definition=definition,
                wave_id="dwv_campaign_launch_002",
                launched_by="pm_002",
                requested_as_of_date="2026-05-10",
                correlation_id="corr-campaign-definition-launch-002",
                idempotency_key=(
                    "campaign-launch:campaign-holdings-apple-tesla-20260510:2026.05:retry"
                ),
            ),
        ),
        (
            "record_definition_approval_decision",
            lambda definition: record_bulk_review_campaign_definition_approval_decision(
                definition=definition,
                decision_type="APPROVED",
                decision_ref="BRC-APPROVAL-2026-05-001",
                decided_by="cio_ops_committee",
                decision_reason="Approved for bounded DPM campaign launch.",
                correlation_id="corr-campaign-approval-decision-001",
            ),
            lambda definition: record_bulk_review_campaign_definition_approval_decision(
                definition=definition,
                decision_type="REJECTED",
                decision_ref="BRC-APPROVAL-2026-05-002",
                decided_by="cio_ops_committee",
                decision_reason="Rejected by an independent review path.",
                correlation_id="corr-campaign-approval-decision-002",
            ),
        ),
        (
            "record_definition_assignment_action",
            lambda definition: record_bulk_review_campaign_definition_assignment_action(
                definition=definition,
                action_type="ASSIGNED",
                action_ref="BRC-ASSIGN-2026-05-001",
                recorded_by="ops",
                action_reason="Route campaign to assigned PM.",
                assigned_actor_ids=["pm_001"],
                escalation_tier="PM",
                sla_posture="ON_TRACK",
                correlation_id="corr-campaign-assignment-action-001",
            ),
            lambda definition: record_bulk_review_campaign_definition_assignment_action(
                definition=definition,
                action_type="ESCALATED",
                action_ref="BRC-ASSIGN-2026-05-002",
                recorded_by="ops",
                action_reason="Escalate campaign to governance operations.",
                assigned_actor_ids=["governance_ops"],
                escalation_tier="GOVERNANCE",
                sla_posture="ATTENTION",
                correlation_id="corr-campaign-assignment-action-002",
            ),
        ),
        (
            "record_definition_assignment_task",
            lambda definition: open_bulk_review_campaign_definition_assignment_task(
                definition=definition,
                task_ref="BRC-TASK-2026-05-001",
                task_type="ASSIGNMENT",
                opened_by="ops",
                task_reason="Campaign requires PM acknowledgement.",
                assigned_actor_ids=["pm_001"],
                escalation_tier="PM",
                sla_posture="ON_TRACK",
                correlation_id="corr-campaign-assignment-task-001",
            ),
            lambda definition: open_bulk_review_campaign_definition_assignment_task(
                definition=definition,
                task_ref="BRC-TASK-2026-05-002",
                task_type="ESCALATION",
                opened_by="ops",
                task_reason="Campaign requires operations escalation.",
                assigned_actor_ids=["ops_lead"],
                escalation_tier="OPS",
                sla_posture="ATTENTION",
                correlation_id="corr-campaign-assignment-task-002",
            ),
        ),
        (
            "record_definition_maker_checker_control",
            lambda definition: record_bulk_review_campaign_definition_maker_checker_control(
                definition=definition,
                control_action="SUBMITTED_FOR_REVIEW",
                control_ref="BRC-MC-2026-05-001",
                recorded_by="ops",
                submitter_actor_id="pm_001",
                control_outcome="PENDING",
                control_reason="Campaign definition submitted for independent review.",
                correlation_id="corr-campaign-maker-checker-control-001",
            ),
            lambda definition: record_bulk_review_campaign_definition_maker_checker_control(
                definition=definition,
                control_action="SUBMITTED_FOR_REVIEW",
                control_ref="BRC-MC-2026-05-002",
                recorded_by="ops",
                submitter_actor_id="pm_002",
                control_outcome="PENDING",
                control_reason="Parallel campaign definition review submission.",
                correlation_id="corr-campaign-maker-checker-control-002",
            ),
        ),
    ],
)
def test_campaign_definition_repository_rejects_stale_independent_workflow_appends(
    method_name: str,
    first_builder,
    second_builder,
) -> None:
    repository = InMemoryDpmBulkReviewCampaignDefinitionRepository()
    definition = _definition()
    repository.save_definition(definition=definition)
    first_update = first_builder(definition)
    stale_update = second_builder(definition)

    assert (
        getattr(repository, method_name)(
            definition=first_update,
            expected_content_hash=definition.content_hash,
        )
        == first_update
    )
    with pytest.raises(
        DpmBulkReviewCampaignDefinitionConflictError,
        match="BULK_REVIEW_CAMPAIGN_DEFINITION_STALE_WRITE",
    ):
        getattr(repository, method_name)(
            definition=stale_update,
            expected_content_hash=definition.content_hash,
        )

    assert (
        repository.get_definition(
            tenant_id=definition.tenant_id,
            campaign_id=definition.campaign_id,
            campaign_version=definition.campaign_version,
        )
        == first_update
    )


def test_campaign_definition_launch_history_page_is_bounded_audit_evidence() -> None:
    definition = record_bulk_review_campaign_definition_launch(
        definition=_definition(),
        wave_id="dwv_campaign_launch_001",
        launched_by="pm_001",
        requested_as_of_date="2026-05-10",
        correlation_id="corr-campaign-definition-launch-001",
        idempotency_key="campaign-launch:campaign-holdings-apple-tesla-20260510:2026.05:ready",
        launched_at=datetime(2026, 5, 10, tzinfo=timezone.utc),
    )

    page = build_bulk_review_campaign_definition_launch_history_page(
        definition=definition,
        limit=1,
        offset=0,
    )
    empty_page = build_bulk_review_campaign_definition_launch_history_page(
        definition=definition,
        limit=1,
        offset=1,
    )

    assert page.product_name == "BulkReviewCampaignDefinitionLaunchHistory"
    assert page.campaign_id == definition.campaign_id
    assert page.count == 1
    assert page.total_count == 1
    assert page.items[0].wave_id == "dwv_campaign_launch_001"
    assert "NO_ORDER_GENERATION" in page.operating_boundaries
    assert "NO_OMS_EXECUTION_CLAIM" in page.operating_boundaries
    assert empty_page.count == 0
    assert empty_page.total_count == 1


def test_campaign_definition_approval_decisions_are_append_only() -> None:
    repository = InMemoryDpmBulkReviewCampaignDefinitionRepository()
    definition = _definition()
    repository.save_definition(definition=definition)

    approved = record_bulk_review_campaign_definition_approval_decision(
        definition=definition,
        decision_type="APPROVED",
        decision_ref="BRC-APPROVAL-2026-05-001",
        decided_by="cio_ops_committee",
        decision_reason="Approved for bounded DPM campaign launch.",
        correlation_id="corr-campaign-approval-decision-001",
        source_refs=[
            DpmWaveSourceRef(
                source_system="lotus-manage",
                source_type="BulkReviewCampaignApprovalMinutes",
                source_id="minutes-001",
            )
        ],
    )
    replayed = record_bulk_review_campaign_definition_approval_decision(
        definition=approved,
        decision_type="APPROVED",
        decision_ref="BRC-APPROVAL-2026-05-001",
        decided_by="cio_ops_committee",
        decision_reason="Approved for bounded DPM campaign launch.",
        correlation_id="corr-campaign-approval-decision-001",
        source_refs=[
            DpmWaveSourceRef(
                source_system="lotus-manage",
                source_type="BulkReviewCampaignApprovalMinutes",
                source_id="minutes-001",
            )
        ],
    )
    returned = repository.record_definition_approval_decision(
        definition=approved,
        expected_content_hash=definition.content_hash,
    )
    page = build_bulk_review_campaign_definition_approval_decision_page(
        definition=approved,
        limit=1,
        offset=0,
    )

    assert returned == approved
    assert replayed == approved
    assert approved.content_hash != definition.content_hash
    assert len(approved.approval_decisions) == 1
    assert approved.approval_decisions[0].decision_type == "APPROVED"
    assert "trade_approval" in approved.approval_decisions[0].forbidden_actions
    assert page.product_name == "BulkReviewCampaignDefinitionApprovalDecisionPage"
    assert page.latest_decision_type == "APPROVED"
    assert page.count == 1
    assert (
        repository.get_definition(
            tenant_id=definition.tenant_id,
            campaign_id=definition.campaign_id,
            campaign_version=definition.campaign_version,
        )
        == approved
    )
    assert (
        repository.record_definition_approval_decision(
            expected_content_hash=definition.content_hash,
            definition=DpmBulkReviewCampaignDefinition.model_validate(
                {
                    **approved.model_dump(mode="python"),
                    "campaign_id": "missing-campaign",
                    "content_hash": "",
                }
            ),
        )
        is None
    )
    assert (
        repository.record_definition_approval_decision(
            definition=approved,
            expected_content_hash=definition.content_hash,
        )
        == approved
    )

    with pytest.raises(
        ValueError,
        match="BULK_REVIEW_CAMPAIGN_APPROVAL_DECISION_REF_CONFLICT",
    ):
        record_bulk_review_campaign_definition_approval_decision(
            definition=approved,
            decision_type="REJECTED",
            decision_ref="BRC-APPROVAL-2026-05-001",
            decided_by="cio_ops_committee",
            decision_reason="Conflicting decision.",
            correlation_id="corr-campaign-approval-decision-002",
        )


def test_campaign_definition_approval_decision_validation_edges() -> None:
    definition = _definition()
    retired = DpmBulkReviewCampaignDefinition.model_validate(
        {
            **definition.model_dump(mode="python"),
            "status": "RETIRED",
            "retired_at": "2026-05-11T08:00:00Z",
            "retired_by": "ops",
            "retirement_reason": "Campaign completed.",
            "retirement_correlation_id": "corr-campaign-definition-retire-001",
            "content_hash": "",
        }
    )

    for patch, reason_code in [
        ({"definition": retired}, "BULK_REVIEW_CAMPAIGN_APPROVAL_DECISION_ACTIVE_REQUIRED"),
        ({"decision_ref": " "}, "BULK_REVIEW_CAMPAIGN_APPROVAL_DECISION_REF_REQUIRED"),
        ({"decided_by": " "}, "BULK_REVIEW_CAMPAIGN_APPROVAL_DECISION_ACTOR_REQUIRED"),
        ({"decision_reason": " "}, "BULK_REVIEW_CAMPAIGN_APPROVAL_DECISION_REASON_REQUIRED"),
        ({"correlation_id": " "}, "BULK_REVIEW_CAMPAIGN_APPROVAL_DECISION_CORRELATION_REQUIRED"),
    ]:
        request = {
            "definition": definition,
            "decision_type": "APPROVED",
            "decision_ref": "BRC-APPROVAL-2026-05-001",
            "decided_by": "cio_ops_committee",
            "decision_reason": "Approved for bounded DPM campaign launch.",
            "correlation_id": "corr-campaign-approval-decision-001",
            **patch,
        }
        with pytest.raises(ValueError, match=reason_code):
            record_bulk_review_campaign_definition_approval_decision(**request)


def test_campaign_approval_decision_helpers_normalize_request_fields() -> None:
    source_ref = DpmWaveSourceRef(
        source_system="lotus-manage",
        source_type="BulkReviewCampaignApprovalMinutes",
        source_id="minutes-001",
    )
    decision_input = _approval_decision_input(
        decision_ref=" BRC-APPROVAL-2026-05-001 ",
        decided_by=" cio_ops_committee ",
        decision_reason=" Approved for bounded DPM campaign launch. ",
        correlation_id=" corr-campaign-approval-decision-001 ",
        source_refs=[source_ref],
    )

    assert decision_input.decision_ref == "BRC-APPROVAL-2026-05-001"
    assert decision_input.decided_by == "cio_ops_committee"
    assert decision_input.decision_reason == "Approved for bounded DPM campaign launch."
    assert decision_input.correlation_id == "corr-campaign-approval-decision-001"
    assert decision_input.source_refs == [source_ref]

    with pytest.raises(ValueError, match="BULK_REVIEW_CAMPAIGN_APPROVAL_DECISION_REF_REQUIRED"):
        _approval_decision_input(
            decision_ref=" ",
            decided_by="cio_ops_committee",
            decision_reason="Approved for bounded DPM campaign launch.",
            correlation_id="corr-campaign-approval-decision-001",
            source_refs=None,
        )


def test_campaign_approval_decision_helpers_detect_active_and_existing_posture() -> None:
    definition = _definition()
    _validate_active_campaign_definition(definition)
    decision = _build_decision(
        definition=definition,
        decision_type="APPROVED",
        decision_ref="BRC-APPROVAL-2026-05-001",
        decided_by="cio_ops_committee",
        decision_reason="Approved for bounded DPM campaign launch.",
        correlation_id="corr-campaign-approval-decision-001",
        source_refs=[],
    )

    updated = _append_approval_decision(definition=definition, decision=decision)

    assert _existing_approval_decision(definition=updated, decision=decision) == decision
    assert updated.approval_decisions == [decision]
    assert updated.content_hash != definition.content_hash

    retired = DpmBulkReviewCampaignDefinition.model_validate(
        {
            **definition.model_dump(mode="python"),
            "status": "RETIRED",
            "retired_at": "2026-05-11T08:00:00Z",
            "retired_by": "ops",
            "retirement_reason": "Campaign completed.",
            "retirement_correlation_id": "corr-campaign-definition-retire-001",
            "content_hash": "",
        }
    )
    with pytest.raises(
        ValueError,
        match="BULK_REVIEW_CAMPAIGN_APPROVAL_DECISION_ACTIVE_REQUIRED",
    ):
        _validate_active_campaign_definition(retired)


def test_campaign_definition_preview_readiness_records_ineligible_and_entitlement_edges() -> None:
    definition = _definition()
    readiness = build_bulk_review_campaign_definition_preview_readiness(
        definition=DpmBulkReviewCampaignDefinition.model_validate(
            {
                **definition.model_dump(mode="python"),
                "as_of_date": "bad-date",
                "eligible_portfolio_types": ["ADVISORY"],
                "governance": {
                    **definition.governance.model_dump(mode="python"),
                    "expires_on": "2026-05-09",
                    "entitled_actor_ids": ["pm_001"],
                },
                "content_hash": "",
            }
        ),
        requested_as_of_date="2026-05-10",
        actor_id="pm_002",
    )

    assert readiness.preview_create_allowed is False
    assert "BULK_REVIEW_CAMPAIGN_DEFINITION_AS_OF_DATE_MISMATCH" in readiness.reason_codes
    assert "BULK_REVIEW_CAMPAIGN_MEMBERSHIP_EMPTY" in readiness.reason_codes
    assert "BULK_REVIEW_CAMPAIGN_EXPIRED" in readiness.reason_codes
    assert "BULK_REVIEW_CAMPAIGN_ACTOR_NOT_ENTITLED" in readiness.reason_codes
    assert readiness.actor_entitlement_state == "UNAUTHORIZED"

    actor_required = build_bulk_review_campaign_definition_preview_readiness(
        definition=DpmBulkReviewCampaignDefinition.model_validate(
            {
                **definition.model_dump(mode="python"),
                "governance": {
                    **definition.governance.model_dump(mode="python"),
                    "entitled_actor_ids": ["pm_001"],
                },
                "content_hash": "",
            }
        ),
        requested_as_of_date="2026-05-10",
        actor_id=None,
    )

    assert actor_required.actor_entitlement_state == "ACTOR_REQUIRED"
    assert "BULK_REVIEW_CAMPAIGN_ACTOR_REQUIRED_FOR_ENTITLEMENT" in actor_required.reason_codes

    structurally_incomplete = build_bulk_review_campaign_definition_preview_readiness(
        definition=definition.model_copy(
            update={
                "status": "SUPERSEDED",
                "eligible_portfolio_types": [],
                "candidates": [],
            }
        ),
        requested_as_of_date="bad-date",
        actor_id="pm_001",
    )

    assert "BULK_REVIEW_CAMPAIGN_DEFINITION_SUPERSEDED" in structurally_incomplete.reason_codes
    assert "BULK_REVIEW_CAMPAIGN_PORTFOLIO_TYPES_REQUIRED" in structurally_incomplete.reason_codes
    assert (
        "BULK_REVIEW_CAMPAIGN_CANDIDATE_PORTFOLIOS_REQUIRED" in structurally_incomplete.reason_codes
    )
    assert (
        "BULK_REVIEW_CAMPAIGN_DEFINITION_REQUESTED_AS_OF_DATE_INVALID"
        in structurally_incomplete.reason_codes
    )

    invalid_expiry = build_bulk_review_campaign_definition_preview_readiness(
        definition=DpmBulkReviewCampaignDefinition.model_validate(
            {
                **definition.model_dump(mode="python"),
                "governance": {
                    **definition.governance.model_dump(mode="python"),
                    "expires_on": "bad-date",
                },
                "content_hash": "",
            }
        ),
        requested_as_of_date="2026-05-10",
        actor_id="pm_001",
    )

    assert invalid_expiry.expiry_state == "INVALID"
    assert "BULK_REVIEW_CAMPAIGN_EXPIRY_DATE_INVALID" in invalid_expiry.reason_codes


def test_campaign_definition_governance_readiness_helpers_fail_closed() -> None:
    reason_codes: list[str] = []
    governance = DpmBulkReviewCampaignDefinitionGovernance(
        approval_ref="BRC-APPROVAL-2026-05",
        expires_on="2026-05-09",
        entitled_actor_ids=["pm_001"],
    )

    assert (
        _approval_governance_status(governance=governance, reason_codes=reason_codes)
        == "INCOMPLETE"
    )
    assert (
        _expiry_readiness_state(
            governance=governance,
            requested_date=datetime(2026, 5, 10, tzinfo=timezone.utc).date(),
            reason_codes=reason_codes,
        )
        == "EXPIRED"
    )
    assert (
        _actor_entitlement_state(
            governance=governance,
            actor_id="pm_002",
            reason_codes=reason_codes,
        )
        == "UNAUTHORIZED"
    )

    assert "BULK_REVIEW_CAMPAIGN_APPROVAL_EVIDENCE_INCOMPLETE" in reason_codes
    assert "BULK_REVIEW_CAMPAIGN_EXPIRED" in reason_codes
    assert "BULK_REVIEW_CAMPAIGN_ACTOR_NOT_ENTITLED" in reason_codes


def test_campaign_definition_candidate_readiness_helpers_fail_closed() -> None:
    definition = _definition()
    reason_codes: list[str] = []

    assert _eligible_portfolio_types(
        definition.model_copy(update={"eligible_portfolio_types": [" dpm ", "DPM"]})
    ) == ["DPM"]

    readiness = _candidate_readiness(
        definition=definition.model_copy(update={"eligible_portfolio_types": ["ADVISORY"]}),
        reason_codes=reason_codes,
    )

    assert readiness.eligible_portfolio_types == ["ADVISORY"]
    assert readiness.eligible_candidate_count == 0
    assert readiness.excluded_candidate_count == len(definition.candidates)
    assert "BULK_REVIEW_CAMPAIGN_MEMBERSHIP_EMPTY" in reason_codes

    reason_codes = []
    _definition_status_reason_codes(
        definition=definition.model_copy(update={"status": "SUPERSEDED"}),
        requested_as_of_date="2026-05-11",
        reason_codes=reason_codes,
    )

    assert "BULK_REVIEW_CAMPAIGN_DEFINITION_SUPERSEDED" in reason_codes
    assert "BULK_REVIEW_CAMPAIGN_DEFINITION_AS_OF_DATE_MISMATCH" in reason_codes


def test_campaign_definition_assignment_actions_are_append_only() -> None:
    repository = InMemoryDpmBulkReviewCampaignDefinitionRepository()
    definition = _definition()
    repository.save_definition(definition=definition)

    assigned = record_bulk_review_campaign_definition_assignment_action(
        definition=definition,
        action_type="ASSIGNED",
        action_ref="BRC-ASSIGN-2026-05-001",
        recorded_by="ops",
        action_reason="Route campaign to assigned PM.",
        assigned_actor_ids=["pm_001"],
        escalation_tier="PM",
        sla_posture="ON_TRACK",
        correlation_id="corr-campaign-assignment-action-001",
    )
    escalated = record_bulk_review_campaign_definition_assignment_action(
        definition=assigned,
        action_type="ESCALATED",
        action_ref="BRC-ASSIGN-2026-05-002",
        recorded_by="ops",
        action_reason="Approval evidence requires governance attention.",
        assigned_actor_ids=["governance_ops"],
        escalation_tier="GOVERNANCE",
        sla_posture="ATTENTION",
        correlation_id="corr-campaign-assignment-action-002",
    )
    replayed = record_bulk_review_campaign_definition_assignment_action(
        definition=escalated,
        action_type="ESCALATED",
        action_ref="BRC-ASSIGN-2026-05-002",
        recorded_by="ops",
        action_reason="Approval evidence requires governance attention.",
        assigned_actor_ids=["governance_ops"],
        escalation_tier="GOVERNANCE",
        sla_posture="ATTENTION",
        correlation_id="corr-campaign-assignment-action-002",
    )
    returned = repository.record_definition_assignment_action(
        definition=escalated,
        expected_content_hash=definition.content_hash,
    )
    page = build_bulk_review_campaign_definition_assignment_action_page(
        definition=escalated,
        limit=50,
        offset=0,
    )

    assert returned == escalated
    assert replayed == escalated
    assert escalated.content_hash != definition.content_hash
    assert len(escalated.assignment_actions) == 2
    assert escalated.assignment_actions[1].action_type == "ESCALATED"
    assert "approval_state_mutation" in escalated.assignment_actions[1].forbidden_actions
    assert page.product_name == "BulkReviewCampaignDefinitionAssignmentActionPage"
    assert page.latest_action_type == "ESCALATED"
    assert page.current_assigned_actor_ids == ["governance_ops"]
    assert page.current_escalation_tier == "GOVERNANCE"
    assert page.current_sla_posture == "ATTENTION"
    assert (
        repository.get_definition(
            tenant_id=definition.tenant_id,
            campaign_id=definition.campaign_id,
            campaign_version=definition.campaign_version,
        )
        == escalated
    )
    assert (
        repository.record_definition_assignment_action(
            expected_content_hash=definition.content_hash,
            definition=DpmBulkReviewCampaignDefinition.model_validate(
                {
                    **escalated.model_dump(mode="python"),
                    "campaign_id": "missing-campaign",
                    "content_hash": "",
                }
            ),
        )
        is None
    )

    with pytest.raises(
        ValueError,
        match="BULK_REVIEW_CAMPAIGN_ASSIGNMENT_ACTION_REF_CONFLICT",
    ):
        record_bulk_review_campaign_definition_assignment_action(
            definition=escalated,
            action_type="RESOLVED",
            action_ref="BRC-ASSIGN-2026-05-002",
            recorded_by="ops",
            action_reason="Conflicting assignment action.",
            assigned_actor_ids=[],
            escalation_tier="NONE",
            sla_posture="ON_TRACK",
            correlation_id="corr-campaign-assignment-action-conflict",
        )


def test_campaign_definition_assignment_tasks_persist_current_state_and_transition_ledger() -> None:
    repository = InMemoryDpmBulkReviewCampaignDefinitionRepository()
    definition = _definition()
    repository.save_definition(definition=definition)

    opened = open_bulk_review_campaign_definition_assignment_task(
        definition=definition,
        task_ref="BRC-TASK-2026-05-001",
        task_type="ASSIGNMENT",
        opened_by="ops",
        task_reason="Campaign requires PM acknowledgement.",
        assigned_actor_ids=["pm_001"],
        escalation_tier="PM",
        sla_posture="ON_TRACK",
        correlation_id="corr-campaign-assignment-task-001",
    )
    started = transition_bulk_review_campaign_definition_assignment_task(
        definition=opened,
        task_ref="BRC-TASK-2026-05-001",
        transition_type="STARTED",
        transition_ref="BRC-TASK-2026-05-001:start",
        transitioned_by="pm_001",
        transition_reason="PM started campaign review.",
        correlation_id="corr-campaign-assignment-task-transition-001",
    )
    returned = repository.record_definition_assignment_task(
        definition=started,
        expected_content_hash=definition.content_hash,
    )
    page = build_bulk_review_campaign_definition_assignment_task_page(
        definition=started,
        limit=50,
        offset=0,
    )

    assert returned == started
    assert started.content_hash != definition.content_hash
    assert started.assignment_tasks[0].status == "IN_PROGRESS"
    assert len(started.assignment_tasks[0].transitions) == 2
    assert page.product_name == "BulkReviewCampaignDefinitionAssignmentTaskPage"
    assert page.status_counts == {"IN_PROGRESS": 1}
    assert page.open_task_count == 1
    assert (
        repository.get_definition(
            tenant_id=definition.tenant_id,
            campaign_id=definition.campaign_id,
            campaign_version=definition.campaign_version,
        )
        == started
    )


def test_campaign_definition_assignment_task_repository_edges() -> None:
    repository = InMemoryDpmBulkReviewCampaignDefinitionRepository()
    definition = _definition()
    opened = open_bulk_review_campaign_definition_assignment_task(
        definition=definition,
        task_ref="BRC-TASK-2026-05-001",
        task_type="ASSIGNMENT",
        opened_by="ops",
        task_reason="Campaign requires PM acknowledgement.",
        assigned_actor_ids=["pm_001"],
        escalation_tier="PM",
        sla_posture="ON_TRACK",
        correlation_id="corr-campaign-assignment-task-001",
    )

    assert (
        repository.record_definition_assignment_task(
            definition=opened,
            expected_content_hash=definition.content_hash,
        )
        is None
    )

    repository.save_definition(definition=opened)
    assert (
        repository.record_definition_assignment_task(
            definition=opened,
            expected_content_hash=definition.content_hash,
        )
        == opened
    )

    retired = DpmBulkReviewCampaignDefinition.model_validate(
        {
            **definition.model_dump(mode="python"),
            "status": "RETIRED",
            "retired_at": "2026-05-11T08:00:00Z",
            "retired_by": "ops",
            "retirement_reason": "Campaign completed.",
            "retirement_correlation_id": "corr-campaign-definition-retire-001",
            "content_hash": "",
        }
    )
    updated_retired = open_bulk_review_campaign_definition_assignment_task(
        definition=definition,
        task_ref="BRC-TASK-2026-05-002",
        task_type="ESCALATION",
        opened_by="ops",
        task_reason="Campaign requires operations escalation.",
        assigned_actor_ids=["ops_lead"],
        escalation_tier="OPS",
        sla_posture="ATTENTION",
        correlation_id="corr-campaign-assignment-task-002",
    )
    repository = InMemoryDpmBulkReviewCampaignDefinitionRepository()
    repository.save_definition(definition=retired)
    with pytest.raises(
        DpmBulkReviewCampaignDefinitionConflictError,
        match="BULK_REVIEW_CAMPAIGN_DEFINITION_LIFECYCLE_CONFLICT",
    ):
        repository.record_definition_assignment_task(
            definition=updated_retired,
            expected_content_hash=definition.content_hash,
        )


def test_campaign_definition_maker_checker_controls_are_append_only() -> None:
    repository = InMemoryDpmBulkReviewCampaignDefinitionRepository()
    definition = _definition()
    repository.save_definition(definition=definition)

    submitted = record_bulk_review_campaign_definition_maker_checker_control(
        definition=definition,
        control_action="SUBMITTED_FOR_REVIEW",
        control_ref="BRC-MC-2026-05-001",
        recorded_by="ops",
        submitter_actor_id="pm_001",
        control_outcome="PENDING",
        control_reason="Campaign definition submitted for independent review.",
        correlation_id="corr-campaign-maker-checker-control-001",
    )
    reviewed = record_bulk_review_campaign_definition_maker_checker_control(
        definition=submitted,
        control_action="REVIEW_COMPLETED",
        control_ref="BRC-MC-2026-05-002",
        recorded_by="ops",
        submitter_actor_id="pm_001",
        reviewer_actor_id="cio_ops_committee",
        required_reviewer_role="CIO_OPERATIONS_REVIEWER",
        control_outcome="PASSED",
        control_reason="Independent reviewer accepted the campaign definition evidence.",
        correlation_id="corr-campaign-maker-checker-control-002",
    )
    replayed = record_bulk_review_campaign_definition_maker_checker_control(
        definition=reviewed,
        control_action="REVIEW_COMPLETED",
        control_ref="BRC-MC-2026-05-002",
        recorded_by="ops",
        submitter_actor_id="pm_001",
        reviewer_actor_id="cio_ops_committee",
        required_reviewer_role="CIO_OPERATIONS_REVIEWER",
        control_outcome="PASSED",
        control_reason="Independent reviewer accepted the campaign definition evidence.",
        correlation_id="corr-campaign-maker-checker-control-002",
    )
    returned = repository.record_definition_maker_checker_control(
        definition=reviewed,
        expected_content_hash=definition.content_hash,
    )
    page = build_bulk_review_campaign_definition_maker_checker_control_page(
        definition=reviewed,
        limit=50,
        offset=0,
    )

    assert returned == reviewed
    assert replayed == reviewed
    assert reviewed.content_hash != definition.content_hash
    assert len(reviewed.maker_checker_controls) == 2
    assert reviewed.maker_checker_controls[1].control_action == "REVIEW_COMPLETED"
    assert "external_workflow_orchestration" in reviewed.maker_checker_controls[1].forbidden_actions
    assert page.product_name == "BulkReviewCampaignDefinitionMakerCheckerControlPage"
    assert page.latest_control_action == "REVIEW_COMPLETED"
    assert page.current_control_outcome == "PASSED"
    assert page.current_reviewer_actor_id == "cio_ops_committee"
    assert (
        repository.get_definition(
            tenant_id=definition.tenant_id,
            campaign_id=definition.campaign_id,
            campaign_version=definition.campaign_version,
        )
        == reviewed
    )


def test_campaign_definition_maker_checker_repository_edges() -> None:
    repository = InMemoryDpmBulkReviewCampaignDefinitionRepository()
    definition = _definition()
    submitted = record_bulk_review_campaign_definition_maker_checker_control(
        definition=definition,
        control_action="SUBMITTED_FOR_REVIEW",
        control_ref="BRC-MC-2026-05-001",
        recorded_by="ops",
        submitter_actor_id="pm_001",
        control_outcome="PENDING",
        control_reason="Campaign definition submitted for independent review.",
        correlation_id="corr-campaign-maker-checker-control-001",
    )

    assert (
        repository.record_definition_maker_checker_control(
            definition=submitted,
            expected_content_hash=definition.content_hash,
        )
        is None
    )

    repository.save_definition(definition=submitted)
    assert (
        repository.record_definition_maker_checker_control(
            definition=submitted,
            expected_content_hash=definition.content_hash,
        )
        == submitted
    )

    retired = DpmBulkReviewCampaignDefinition.model_validate(
        {
            **definition.model_dump(mode="python"),
            "status": "RETIRED",
            "retired_at": "2026-05-11T08:00:00Z",
            "retired_by": "ops",
            "retirement_reason": "Campaign completed.",
            "retirement_correlation_id": "corr-campaign-definition-retire-001",
            "content_hash": "",
        }
    )
    updated_retired = record_bulk_review_campaign_definition_maker_checker_control(
        definition=definition,
        control_action="SUBMITTED_FOR_REVIEW",
        control_ref="BRC-MC-2026-05-002",
        recorded_by="ops",
        submitter_actor_id="pm_001",
        control_outcome="PENDING",
        control_reason="Campaign definition submitted for independent review.",
        correlation_id="corr-campaign-maker-checker-control-002",
    )
    repository = InMemoryDpmBulkReviewCampaignDefinitionRepository()
    repository.save_definition(definition=retired)
    with pytest.raises(
        DpmBulkReviewCampaignDefinitionConflictError,
        match="BULK_REVIEW_CAMPAIGN_DEFINITION_LIFECYCLE_CONFLICT",
    ):
        repository.record_definition_maker_checker_control(
            definition=updated_retired,
            expected_content_hash=definition.content_hash,
        )


def test_campaign_definition_launch_command_is_ready_only() -> None:
    definition = _definition()

    command = build_bulk_review_campaign_definition_launch_command(
        definition=definition,
        requested_as_of_date="2026-05-10",
        actor_id="ops",
        correlation_id="corr-campaign-definition-launch-001",
    )

    assert command.create_request.trigger_type == "BULK_REVIEW_CAMPAIGN"
    assert command.create_request.campaign_definition_id == definition.campaign_id
    assert command.correlation_id == "corr-campaign-definition-launch-001"
    assert command.idempotency_key.startswith(
        "campaign-launch:campaign-holdings-apple-tesla-20260510:2026.05:"
    )
    assert command.launch_package.launch_state == "READY"

    expired = DpmBulkReviewCampaignDefinition.model_validate(
        {
            **definition.model_dump(mode="python"),
            "governance": {
                **definition.governance.model_dump(mode="python"),
                "expires_on": "2026-05-09",
            },
            "content_hash": "",
        }
    )
    with pytest.raises(DpmBulkReviewCampaignDefinitionLaunchBlocked) as blocked:
        build_bulk_review_campaign_definition_launch_command(
            definition=expired,
            requested_as_of_date="2026-05-10",
            actor_id="ops",
            correlation_id=None,
        )

    assert "BULK_REVIEW_CAMPAIGN_EXPIRED" in blocked.value.reason_codes
    assert blocked.value.readiness.preview_create_allowed is False


def test_campaign_definition_retirement_validation_and_in_memory_lifecycle() -> None:
    repository = InMemoryDpmBulkReviewCampaignDefinitionRepository()
    definition = _definition()
    repository.save_definition(definition=definition)

    with pytest.raises(
        ValueError,
        match="BULK_REVIEW_CAMPAIGN_ACTIVE_LIFECYCLE_FIELDS_FORBIDDEN",
    ):
        DpmBulkReviewCampaignDefinition.model_validate(
            {
                **definition.model_dump(mode="python"),
                "retired_by": "ops",
                "content_hash": "",
            }
        )

    retired = DpmBulkReviewCampaignDefinition.model_validate(
        {
            **definition.model_dump(mode="python"),
            "status": "RETIRED",
            "retired_at": "2026-05-11T08:00:00Z",
            "retired_by": "ops",
            "retirement_reason": "Campaign completed.",
            "retirement_correlation_id": "corr-campaign-definition-retire-001",
            "content_hash": "",
        }
    )

    returned = repository.retire_definition(definition=retired)

    assert returned is not None
    assert returned == retired
    assert returned.content_hash != definition.content_hash
    assert (
        repository.get_definition(
            tenant_id=definition.tenant_id,
            campaign_id=definition.campaign_id,
            campaign_version=definition.campaign_version,
        )
        == retired
    )
    assert repository.list_definitions(tenant_id=definition.tenant_id, status="ACTIVE") == []
    assert repository.list_definitions(tenant_id=definition.tenant_id, status="RETIRED") == [
        retired
    ]
    assert repository.retire_definition(definition=retired) == retired
    assert (
        repository.retire_definition(
            definition=DpmBulkReviewCampaignDefinition.model_validate(
                {
                    **retired.model_dump(mode="python"),
                    "campaign_id": "missing-campaign",
                    "content_hash": "",
                }
            )
        )
        is None
    )


def test_campaign_definition_supersession_validation_and_in_memory_lifecycle() -> None:
    repository = InMemoryDpmBulkReviewCampaignDefinitionRepository()
    original = _definition()
    replacement = _definition(display_name="Refreshed Apple and Tesla holdings review")
    replacement = DpmBulkReviewCampaignDefinition.model_validate(
        {
            **replacement.model_dump(mode="python"),
            "campaign_version": "2026.06",
            "content_hash": "",
        }
    )
    repository.save_definition(definition=original)
    repository.save_definition(definition=replacement)

    with pytest.raises(
        ValueError,
        match="BULK_REVIEW_CAMPAIGN_SUPERSESSION_CONTENT_HASH_REQUIRED",
    ):
        DpmBulkReviewCampaignDefinition.model_validate(
            {
                **original.model_dump(mode="python"),
                "status": "SUPERSEDED",
                "superseded_at": "2026-05-12T08:00:00Z",
                "superseded_by": "ops",
                "supersession_reason": "Campaign candidate set refreshed.",
                "supersession_correlation_id": "corr-campaign-definition-supersede-001",
                "superseded_by_campaign_id": replacement.campaign_id,
                "superseded_by_campaign_version": replacement.campaign_version,
                "content_hash": "",
            }
        )

    superseded = DpmBulkReviewCampaignDefinition.model_validate(
        {
            **original.model_dump(mode="python"),
            "status": "SUPERSEDED",
            "superseded_at": "2026-05-12T08:00:00Z",
            "superseded_by": "ops",
            "supersession_reason": "Campaign candidate set refreshed.",
            "supersession_correlation_id": "corr-campaign-definition-supersede-001",
            "superseded_by_campaign_id": replacement.campaign_id,
            "superseded_by_campaign_version": replacement.campaign_version,
            "superseded_by_content_hash": replacement.content_hash,
            "content_hash": "",
        }
    )

    returned = repository.supersede_definition(definition=superseded)

    assert returned is not None
    assert returned == superseded
    assert repository.list_definitions(tenant_id=original.tenant_id, status="ACTIVE") == [
        replacement
    ]
    assert repository.list_definitions(tenant_id=original.tenant_id, status="SUPERSEDED") == [
        superseded
    ]
    assert repository.supersede_definition(definition=superseded) == superseded
    assert (
        repository.supersede_definition(
            definition=DpmBulkReviewCampaignDefinition.model_validate(
                {
                    **superseded.model_dump(mode="python"),
                    "campaign_id": "missing-campaign",
                    "content_hash": "",
                }
            )
        )
        is None
    )


def test_campaign_definition_lifecycle_helpers_are_idempotent_and_fail_closed() -> None:
    repository = InMemoryDpmBulkReviewCampaignDefinitionRepository()
    original = _definition()
    replacement = DpmBulkReviewCampaignDefinition.model_validate(
        {
            **_definition(display_name="Refreshed Apple and Tesla holdings review").model_dump(
                mode="python"
            ),
            "campaign_version": "2026.06",
            "content_hash": "",
        }
    )
    repository.save_definition(definition=original)
    repository.save_definition(definition=replacement)

    assert (
        retire_bulk_review_campaign_definition(
            repository=repository,
            tenant_id=original.tenant_id,
            campaign_id="missing",
            campaign_version="2026.05",
            retired_by="ops",
            retirement_reason="Not found.",
            correlation_id="corr-retire-missing",
        )
        is None
    )
    superseded = supersede_bulk_review_campaign_definition(
        repository=repository,
        tenant_id=original.tenant_id,
        campaign_id=original.campaign_id,
        campaign_version=original.campaign_version,
        replacement_version=replacement.campaign_version,
        superseded_by="ops",
        supersession_reason="Campaign candidate set refreshed.",
        correlation_id="corr-supersede-original",
        superseded_at=datetime(2026, 5, 12, tzinfo=timezone.utc),
    )

    assert superseded is not None
    assert superseded.status == "SUPERSEDED"
    assert (
        supersede_bulk_review_campaign_definition(
            repository=repository,
            tenant_id=original.tenant_id,
            campaign_id=original.campaign_id,
            campaign_version=original.campaign_version,
            replacement_version=replacement.campaign_version,
            superseded_by="ops",
            supersession_reason="Already superseded.",
            correlation_id="corr-supersede-idempotent",
        )
        == superseded
    )
    with pytest.raises(
        DpmBulkReviewCampaignDefinitionLifecycleError,
        match="BULK_REVIEW_CAMPAIGN_DEFINITION_LIFECYCLE_CONFLICT",
    ):
        retire_bulk_review_campaign_definition(
            repository=repository,
            tenant_id=original.tenant_id,
            campaign_id=original.campaign_id,
            campaign_version=original.campaign_version,
            retired_by="ops",
            retirement_reason="Cannot retire superseded.",
            correlation_id="corr-retire-superseded",
        )
    with pytest.raises(
        DpmBulkReviewCampaignDefinitionLifecycleError,
        match="BULK_REVIEW_CAMPAIGN_SUPERSESSION_REPLACEMENT_VERSION_INVALID",
    ):
        supersede_bulk_review_campaign_definition(
            repository=repository,
            tenant_id=replacement.tenant_id,
            campaign_id=replacement.campaign_id,
            campaign_version=replacement.campaign_version,
            replacement_version=replacement.campaign_version,
            superseded_by="ops",
            supersession_reason="Invalid replacement.",
            correlation_id="corr-supersede-invalid-version",
        )
    with pytest.raises(
        DpmBulkReviewCampaignDefinitionLifecycleError,
        match="BULK_REVIEW_CAMPAIGN_SUPERSESSION_REPLACEMENT_NOT_FOUND",
    ):
        supersede_bulk_review_campaign_definition(
            repository=repository,
            tenant_id=replacement.tenant_id,
            campaign_id=replacement.campaign_id,
            campaign_version=replacement.campaign_version,
            replacement_version="2026.07",
            superseded_by="ops",
            supersession_reason="Missing replacement.",
            correlation_id="corr-supersede-missing-replacement",
        )

    assert (
        supersede_bulk_review_campaign_definition(
            repository=repository,
            tenant_id=original.tenant_id,
            campaign_id="missing",
            campaign_version="2026.05",
            replacement_version=replacement.campaign_version,
            superseded_by="ops",
            supersession_reason="Missing definition.",
            correlation_id="corr-supersede-missing-definition",
        )
        is None
    )

    retired_replacement = retire_bulk_review_campaign_definition(
        repository=repository,
        tenant_id=replacement.tenant_id,
        campaign_id=replacement.campaign_id,
        campaign_version=replacement.campaign_version,
        retired_by="ops",
        retirement_reason="Replacement completed.",
        correlation_id="corr-retire-replacement",
        retired_at=datetime(2026, 5, 13, tzinfo=timezone.utc),
    )
    assert retired_replacement is not None
    assert retired_replacement.status == "RETIRED"
    assert (
        retire_bulk_review_campaign_definition(
            repository=repository,
            tenant_id=replacement.tenant_id,
            campaign_id=replacement.campaign_id,
            campaign_version=replacement.campaign_version,
            retired_by="ops",
            retirement_reason="Already retired.",
            correlation_id="corr-retire-idempotent",
        )
        == retired_replacement
    )
    with pytest.raises(
        DpmBulkReviewCampaignDefinitionLifecycleError,
        match="BULK_REVIEW_CAMPAIGN_DEFINITION_LIFECYCLE_CONFLICT",
    ):
        supersede_bulk_review_campaign_definition(
            repository=repository,
            tenant_id=replacement.tenant_id,
            campaign_id=replacement.campaign_id,
            campaign_version=replacement.campaign_version,
            replacement_version="2026.08",
            superseded_by="ops",
            supersession_reason="Cannot supersede retired.",
            correlation_id="corr-supersede-retired",
        )

    not_active_repository = InMemoryDpmBulkReviewCampaignDefinitionRepository()
    not_active_original = _definition(campaign_id="campaign-not-active-replacement")
    not_active_replacement = DpmBulkReviewCampaignDefinition.model_validate(
        {
            **_definition(
                campaign_id="campaign-not-active-replacement",
                display_name="Retired replacement",
            ).model_dump(mode="python"),
            "campaign_version": "2026.06",
            "status": "RETIRED",
            "retired_at": "2026-05-13T08:00:00Z",
            "retired_by": "ops",
            "retirement_reason": "Replacement retired.",
            "retirement_correlation_id": "corr-retired-replacement",
            "content_hash": "",
        }
    )
    not_active_repository.save_definition(definition=not_active_original)
    not_active_repository.save_definition(definition=not_active_replacement)
    with pytest.raises(
        DpmBulkReviewCampaignDefinitionLifecycleError,
        match="BULK_REVIEW_CAMPAIGN_SUPERSESSION_REPLACEMENT_NOT_ACTIVE",
    ):
        supersede_bulk_review_campaign_definition(
            repository=not_active_repository,
            tenant_id=not_active_original.tenant_id,
            campaign_id=not_active_original.campaign_id,
            campaign_version=not_active_original.campaign_version,
            replacement_version=not_active_replacement.campaign_version,
            superseded_by="ops",
            supersession_reason="Replacement not active.",
            correlation_id="corr-supersede-not-active-replacement",
        )


def test_campaign_supersession_helpers_validate_replacement_version() -> None:
    assert (
        _validated_replacement_version(
            replacement_version=" 2026.06 ",
            current_version="2026.05",
        )
        == "2026.06"
    )

    with pytest.raises(
        DpmBulkReviewCampaignDefinitionLifecycleError,
        match="BULK_REVIEW_CAMPAIGN_SUPERSESSION_REPLACEMENT_VERSION_INVALID",
    ):
        _validated_replacement_version(
            replacement_version="2026.05",
            current_version="2026.05",
        )


def test_campaign_supersession_helpers_require_active_replacement() -> None:
    active = _definition()
    assert _validated_active_replacement(active) == active

    with pytest.raises(
        DpmBulkReviewCampaignDefinitionLifecycleError,
        match="BULK_REVIEW_CAMPAIGN_SUPERSESSION_REPLACEMENT_NOT_FOUND",
    ):
        _validated_active_replacement(None)

    with pytest.raises(
        DpmBulkReviewCampaignDefinitionLifecycleError,
        match="BULK_REVIEW_CAMPAIGN_SUPERSESSION_REPLACEMENT_NOT_ACTIVE",
    ):
        _validated_active_replacement(
            DpmBulkReviewCampaignDefinition.model_validate(
                {
                    **active.model_dump(mode="python"),
                    "status": "RETIRED",
                    "retired_at": "2026-05-11T08:00:00Z",
                    "retired_by": "ops",
                    "retirement_reason": "Retired replacement.",
                    "retirement_correlation_id": "corr-retired-replacement",
                    "content_hash": "",
                }
            )
        )


def test_campaign_supersession_helper_builds_superseded_definition_lineage() -> None:
    existing = _definition()
    replacement = DpmBulkReviewCampaignDefinition.model_validate(
        {
            **_definition(display_name="Refreshed Apple and Tesla holdings review").model_dump(
                mode="python"
            ),
            "campaign_version": "2026.06",
            "content_hash": "",
        }
    )

    superseded = _superseded_campaign_definition(
        existing=existing,
        replacement=replacement,
        superseded_by="ops",
        supersession_reason="Campaign candidate set refreshed.",
        correlation_id="corr-supersede-original",
        superseded_at=datetime(2026, 5, 12, tzinfo=timezone.utc),
    )

    assert superseded.status == "SUPERSEDED"
    assert superseded.superseded_by == "ops"
    assert superseded.superseded_by_campaign_id == replacement.campaign_id
    assert superseded.superseded_by_campaign_version == "2026.06"
    assert superseded.superseded_by_content_hash == replacement.content_hash
    assert superseded.supersession_correlation_id == "corr-supersede-original"


def test_in_memory_campaign_definition_repository_rejects_direct_invalid_lifecycle_state() -> None:
    repository = InMemoryDpmBulkReviewCampaignDefinitionRepository()
    active = _definition()
    retired = DpmBulkReviewCampaignDefinition.model_validate(
        {
            **active.model_dump(mode="python"),
            "status": "RETIRED",
            "retired_at": "2026-05-11T08:00:00Z",
            "retired_by": "ops",
            "retirement_reason": "Campaign completed.",
            "retirement_correlation_id": "corr-campaign-definition-retire-001",
            "content_hash": "",
        }
    )
    superseded = DpmBulkReviewCampaignDefinition.model_validate(
        {
            **active.model_dump(mode="python"),
            "status": "SUPERSEDED",
            "superseded_at": "2026-05-12T08:00:00Z",
            "superseded_by": "ops",
            "supersession_reason": "Campaign candidate set refreshed.",
            "supersession_correlation_id": "corr-campaign-definition-supersede-001",
            "superseded_by_campaign_id": active.campaign_id,
            "superseded_by_campaign_version": "2026.06",
            "superseded_by_content_hash": "sha256:replacement",
            "content_hash": "",
        }
    )
    repository.save_definition(definition=retired)
    with pytest.raises(
        DpmBulkReviewCampaignDefinitionConflictError,
        match="BULK_REVIEW_CAMPAIGN_DEFINITION_LIFECYCLE_CONFLICT",
    ):
        repository.supersede_definition(definition=superseded)

    repository = InMemoryDpmBulkReviewCampaignDefinitionRepository()
    repository.save_definition(definition=superseded)
    with pytest.raises(
        DpmBulkReviewCampaignDefinitionConflictError,
        match="BULK_REVIEW_CAMPAIGN_DEFINITION_LIFECYCLE_CONFLICT",
    ):
        repository.retire_definition(definition=retired)


class _Cursor:
    def __init__(
        self, row: dict[str, object] | None = None, rows: list[dict[str, object]] | None = None
    ):
        self._row = row
        self._rows = rows or []

    def fetchone(self) -> dict[str, object] | None:
        return self._row

    def fetchall(self) -> list[dict[str, object]]:
        return self._rows


class _Connection:
    def __init__(self, cursors: list[_Cursor]) -> None:
        self._cursors = cursors
        self.statements: list[tuple[str, object]] = []
        self.committed = False
        self.rolled_back = False

    def execute(self, _sql: str, _args: object = None) -> _Cursor:
        self.statements.append((_sql, _args))
        if not self._cursors:
            return _Cursor()
        return self._cursors.pop(0)

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.rolled_back = True

    def close(self) -> None:
        pass


def test_postgres_campaign_definition_repository_uses_payload_rows() -> None:
    definition = _definition()
    row = {"payload_json": definition.model_dump(mode="json")}
    repository = object.__new__(PostgresDpmBulkReviewCampaignDefinitionRepository)
    connection = _Connection(
        [
            _Cursor(),
            _Cursor(row={"content_hash": definition.content_hash}),
            _Cursor(),
            _Cursor(row=row),
            _Cursor(rows=[row]),
        ]
    )
    repository._connect = lambda: connection  # type: ignore[attr-defined, method-assign]

    repository.save_definition(definition=definition)
    fetched = repository.get_definition(
        tenant_id=definition.tenant_id,
        campaign_id=definition.campaign_id,
        campaign_version=definition.campaign_version,
    )
    listed = repository.list_definitions(
        tenant_id=definition.tenant_id,
        campaign_id=definition.campaign_id,
        status="ACTIVE",
        as_of_date="2026-05-10",
    )

    assert connection.committed is True
    assert fetched == definition
    assert listed == [definition]
    assert _payload({"payload_json": {"campaign_id": "dict"}}) == {"campaign_id": "dict"}
    assert _payload({"payload_json": 1}) == "1"
    assert any(
        "dpm_bulk_review_campaign_workflow_read_model" in sql
        and "ON CONFLICT (tenant_id, campaign_id, campaign_version) DO UPDATE" in sql
        for sql, _ in connection.statements
    )


def test_campaign_workflow_projection_captures_indexable_operator_filters() -> None:
    definition = _definition()
    with_task = open_bulk_review_campaign_definition_assignment_task(
        definition=definition,
        task_ref="BRC-TASK-2026-05-001",
        task_type="ASSIGNMENT",
        opened_by="ops",
        task_reason="Campaign requires PM acknowledgement.",
        assigned_actor_ids=["pm_001"],
        escalation_tier="PM",
        sla_posture="ON_TRACK",
        correlation_id="corr-campaign-assignment-task-001",
    )
    controlled = record_bulk_review_campaign_definition_maker_checker_control(
        definition=with_task,
        control_action="SUBMITTED_FOR_REVIEW",
        control_ref="BRC-MC-2026-05-001",
        recorded_by="ops",
        submitter_actor_id="pm_001",
        control_outcome="PENDING",
        control_reason="Campaign definition submitted for independent review.",
        correlation_id="corr-campaign-maker-checker-control-001",
    )

    projection = _workflow_read_model_projection(controlled)

    assert projection["projection_name"] == "BulkReviewCampaignWorkflowReadModel"
    assert projection["durable_source_table"] == "dpm_bulk_review_campaign_definitions"
    assert projection["definition_content_hash"] == controlled.content_hash
    assert projection["board_status"] in {"READY_FOR_ACTOR", "ATTENTION_FOR_ACTOR", "CLOSED"}
    assert projection["next_action"]
    assert projection["assigned_actor_ids"] == ["pm_001"]
    assert projection["assignment_task_statuses"] == ["OPEN"]
    assert projection["assignment_task_escalation_tiers"] == ["PM"]
    assert projection["assignment_task_sla_postures"] == ["ON_TRACK"]
    assert projection["maker_checker_outcomes"] == ["PENDING"]
    assert projection["assignment_task_transition_count"] == 1
    assert str(projection["workflow_read_model_hash"]).startswith("sha256:")


def test_in_memory_campaign_definition_repository_filters_workflow_projection() -> None:
    definition = _definition()
    with_task = open_bulk_review_campaign_definition_assignment_task(
        definition=definition,
        task_ref="BRC-TASK-2026-05-001",
        task_type="ASSIGNMENT",
        opened_by="ops",
        task_reason="Campaign requires PM acknowledgement.",
        assigned_actor_ids=["pm_001"],
        escalation_tier="PM",
        sla_posture="ON_TRACK",
        correlation_id="corr-campaign-assignment-task-001",
    )
    repository = InMemoryDpmBulkReviewCampaignDefinitionRepository()
    repository.save_definition(definition=with_task)

    assert repository.list_definitions_by_workflow_projection(
        tenant_id=definition.tenant_id,
        assigned_actor_id="pm_001",
        assignment_task_status="OPEN",
        assignment_sla_posture="ON_TRACK",
    ) == [with_task]
    assert (
        repository.list_definitions_by_workflow_projection(
            tenant_id=definition.tenant_id,
            assigned_actor_id="ops_lead",
            assignment_task_status="OPEN",
        )
        == []
    )


def test_postgres_campaign_definition_repository_filters_using_workflow_projection() -> None:
    definition = _definition()
    repository = object.__new__(PostgresDpmBulkReviewCampaignDefinitionRepository)
    connection = _Connection(
        [
            _Cursor(rows=[{"payload_json": definition.model_dump(mode="json")}]),
        ]
    )
    repository._connect = lambda: connection  # type: ignore[attr-defined, method-assign]

    rows = repository.list_definitions_by_workflow_projection(
        tenant_id=definition.tenant_id,
        campaign_id=definition.campaign_id,
        status="ACTIVE",
        as_of_date=definition.as_of_date,
        include_closed=False,
        board_status="ATTENTION_FOR_ACTOR",
        next_action="REVIEW_CAMPAIGN_ATTENTION",
        assignment_escalation_tier="OPS",
        assignment_task_status="OPEN",
        assigned_actor_id="pm_001",
        assignment_sla_posture="ATTENTION",
        maker_checker_outcome="PENDING",
        limit=2,
        offset=0,
    )

    assert rows == [definition]
    sql, args = connection.statements[0]
    assert "JOIN dpm_bulk_review_campaign_workflow_read_model w" in sql
    assert "w.tenant_id = d.tenant_id" in sql
    assert "d.tenant_id = %s" in sql
    assert "w.tenant_id = %s" in sql
    assert "w.board_status = %s" in sql
    assert "w.next_action = %s" in sql
    assert "w.assignment_escalation_tier = %s" in sql
    assert "w.assignment_sla_posture = %s" in sql
    assert "%s = ANY(w.assignment_task_statuses)" in sql
    assert "%s = ANY(w.assigned_actor_ids)" in sql
    assert "%s = ANY(w.maker_checker_outcomes)" in sql
    assert "LIMIT %s OFFSET %s" in sql
    assert args == (
        definition.tenant_id,
        definition.tenant_id,
        definition.campaign_id,
        "ACTIVE",
        definition.as_of_date,
        "ATTENTION_FOR_ACTOR",
        "REVIEW_CAMPAIGN_ATTENTION",
        "OPS",
        "ATTENTION",
        "OPEN",
        "pm_001",
        "PENDING",
        2,
        0,
    )


def test_postgres_campaign_definition_repository_retires_active_definition() -> None:
    definition = _definition()
    retired = DpmBulkReviewCampaignDefinition.model_validate(
        {
            **definition.model_dump(mode="python"),
            "status": "RETIRED",
            "retired_at": "2026-05-11T08:00:00Z",
            "retired_by": "ops",
            "retirement_reason": "Campaign completed.",
            "retirement_correlation_id": "corr-campaign-definition-retire-001",
            "content_hash": "",
        }
    )
    repository = object.__new__(PostgresDpmBulkReviewCampaignDefinitionRepository)
    connection = _Connection(
        [
            _Cursor(
                row={
                    "status": "ACTIVE",
                    "payload_json": definition.model_dump(mode="json"),
                }
            ),
            _Cursor(),
        ]
    )
    repository._connect = lambda: connection  # type: ignore[attr-defined, method-assign]

    assert repository.retire_definition(definition=retired) == retired
    assert connection.committed is True


def test_postgres_campaign_definition_repository_supersedes_active_definition() -> None:
    definition = _definition()
    replacement = DpmBulkReviewCampaignDefinition.model_validate(
        {
            **_definition(display_name="Refreshed Apple and Tesla holdings review").model_dump(
                mode="python"
            ),
            "campaign_version": "2026.06",
            "content_hash": "",
        }
    )
    superseded = DpmBulkReviewCampaignDefinition.model_validate(
        {
            **definition.model_dump(mode="python"),
            "status": "SUPERSEDED",
            "superseded_at": "2026-05-12T08:00:00Z",
            "superseded_by": "ops",
            "supersession_reason": "Campaign candidate set refreshed.",
            "supersession_correlation_id": "corr-campaign-definition-supersede-001",
            "superseded_by_campaign_id": replacement.campaign_id,
            "superseded_by_campaign_version": replacement.campaign_version,
            "superseded_by_content_hash": replacement.content_hash,
            "content_hash": "",
        }
    )
    repository = object.__new__(PostgresDpmBulkReviewCampaignDefinitionRepository)
    connection = _Connection(
        [
            _Cursor(
                row={
                    "status": "ACTIVE",
                    "payload_json": definition.model_dump(mode="json"),
                }
            ),
            _Cursor(),
        ]
    )
    repository._connect = lambda: connection  # type: ignore[attr-defined, method-assign]

    assert repository.supersede_definition(definition=superseded) == superseded
    assert connection.committed is True


def test_postgres_campaign_definition_repository_records_launch_history() -> None:
    definition = _definition()
    launched = record_bulk_review_campaign_definition_launch(
        definition=definition,
        wave_id="dwv_campaign_launch_001",
        launched_by="pm_001",
        requested_as_of_date="2026-05-10",
        correlation_id="corr-campaign-definition-launch-001",
        idempotency_key="campaign-launch:campaign-holdings-apple-tesla-20260510:2026.05:ready",
        launched_at=datetime(2026, 5, 10, tzinfo=timezone.utc),
    )
    repository = object.__new__(PostgresDpmBulkReviewCampaignDefinitionRepository)
    connection = _Connection(
        [
            _Cursor(
                row={
                    "status": "ACTIVE",
                    "content_hash": definition.content_hash,
                    "payload_json": definition.model_dump(mode="json"),
                }
            ),
            _Cursor(),
        ]
    )
    repository._connect = lambda: connection  # type: ignore[attr-defined, method-assign]

    assert (
        repository.record_definition_launch(
            definition=launched,
            expected_content_hash=definition.content_hash,
        )
        == launched
    )
    assert connection.committed is True
    update_sql, update_args = connection.statements[1]
    assert "AND content_hash = %s" in update_sql
    assert update_args[-1] == definition.content_hash


def test_postgres_campaign_definition_repository_records_approval_decisions() -> None:
    definition = _definition()
    approved = record_bulk_review_campaign_definition_approval_decision(
        definition=definition,
        decision_type="APPROVED",
        decision_ref="BRC-APPROVAL-2026-05-001",
        decided_by="cio_ops_committee",
        decision_reason="Approved for bounded DPM campaign launch.",
        correlation_id="corr-campaign-approval-decision-001",
    )
    repository = object.__new__(PostgresDpmBulkReviewCampaignDefinitionRepository)
    connection = _Connection(
        [
            _Cursor(
                row={
                    "status": "ACTIVE",
                    "content_hash": definition.content_hash,
                    "payload_json": definition.model_dump(mode="json"),
                }
            ),
            _Cursor(),
        ]
    )
    repository._connect = lambda: connection  # type: ignore[attr-defined, method-assign]

    assert (
        repository.record_definition_approval_decision(
            definition=approved,
            expected_content_hash=definition.content_hash,
        )
        == approved
    )
    assert connection.committed is True


def test_postgres_campaign_definition_repository_records_assignment_actions() -> None:
    definition = _definition()
    assigned = record_bulk_review_campaign_definition_assignment_action(
        definition=definition,
        action_type="ASSIGNED",
        action_ref="BRC-ASSIGN-2026-05-001",
        recorded_by="ops",
        action_reason="Route campaign to assigned PM.",
        assigned_actor_ids=["pm_001"],
        escalation_tier="PM",
        sla_posture="ON_TRACK",
        correlation_id="corr-campaign-assignment-action-001",
    )
    repository = object.__new__(PostgresDpmBulkReviewCampaignDefinitionRepository)
    connection = _Connection(
        [
            _Cursor(
                row={
                    "status": "ACTIVE",
                    "content_hash": definition.content_hash,
                    "payload_json": definition.model_dump(mode="json"),
                }
            ),
            _Cursor(),
        ]
    )
    repository._connect = lambda: connection  # type: ignore[attr-defined, method-assign]

    assert (
        repository.record_definition_assignment_action(
            definition=assigned,
            expected_content_hash=definition.content_hash,
        )
        == assigned
    )
    assert connection.committed is True


@pytest.mark.parametrize(
    ("method_name", "updated_builder"),
    [
        (
            "record_definition_launch",
            lambda definition: record_bulk_review_campaign_definition_launch(
                definition=definition,
                wave_id="dwv_campaign_launch_001",
                launched_by="pm_001",
                requested_as_of_date="2026-05-10",
                correlation_id="corr-campaign-definition-launch-001",
                idempotency_key=(
                    "campaign-launch:campaign-holdings-apple-tesla-20260510:2026.05:ready"
                ),
            ),
        ),
        (
            "record_definition_approval_decision",
            lambda definition: record_bulk_review_campaign_definition_approval_decision(
                definition=definition,
                decision_type="APPROVED",
                decision_ref="BRC-APPROVAL-2026-05-001",
                decided_by="cio_ops_committee",
                decision_reason="Approved for bounded DPM campaign launch.",
                correlation_id="corr-campaign-approval-decision-001",
            ),
        ),
        (
            "record_definition_assignment_action",
            lambda definition: record_bulk_review_campaign_definition_assignment_action(
                definition=definition,
                action_type="ASSIGNED",
                action_ref="BRC-ASSIGN-2026-05-001",
                recorded_by="ops",
                action_reason="Route campaign to assigned PM.",
                assigned_actor_ids=["pm_001"],
                escalation_tier="PM",
                sla_posture="ON_TRACK",
                correlation_id="corr-campaign-assignment-action-001",
            ),
        ),
    ],
)
def test_postgres_campaign_definition_repository_record_mutation_edges(
    method_name: str,
    updated_builder,
) -> None:
    definition = _definition()
    updated = updated_builder(definition)
    repository = object.__new__(PostgresDpmBulkReviewCampaignDefinitionRepository)

    missing_connection = _Connection([_Cursor(row=None)])
    repository._connect = lambda: missing_connection  # type: ignore[attr-defined, method-assign]
    assert (
        getattr(repository, method_name)(
            definition=updated,
            expected_content_hash=definition.content_hash,
        )
        is None
    )
    assert missing_connection.rolled_back is True

    replay_connection = _Connection(
        [
            _Cursor(
                row={
                    "status": "ACTIVE",
                    "content_hash": updated.content_hash,
                    "payload_json": updated.model_dump(mode="json"),
                }
            )
        ]
    )
    repository._connect = lambda: replay_connection  # type: ignore[attr-defined, method-assign]
    assert (
        getattr(repository, method_name)(
            definition=updated,
            expected_content_hash=definition.content_hash,
        )
        == updated
    )
    assert replay_connection.rolled_back is True

    retired = DpmBulkReviewCampaignDefinition.model_validate(
        {
            **definition.model_dump(mode="python"),
            "status": "RETIRED",
            "retired_at": "2026-05-11T08:00:00Z",
            "retired_by": "ops",
            "retirement_reason": "Campaign completed.",
            "retirement_correlation_id": "corr-campaign-definition-retire-001",
            "content_hash": "",
        }
    )
    inactive_connection = _Connection(
        [
            _Cursor(
                row={
                    "status": "RETIRED",
                    "content_hash": retired.content_hash,
                    "payload_json": retired.model_dump(mode="json"),
                }
            )
        ]
    )
    repository._connect = lambda: inactive_connection  # type: ignore[attr-defined, method-assign]
    with pytest.raises(
        DpmBulkReviewCampaignDefinitionConflictError,
        match="BULK_REVIEW_CAMPAIGN_DEFINITION_LIFECYCLE_CONFLICT",
    ):
        getattr(repository, method_name)(
            definition=updated,
            expected_content_hash=definition.content_hash,
        )
    assert inactive_connection.rolled_back is True

    update_cursor = _Cursor()
    update_cursor.rowcount = 0
    rowcount_connection = _Connection(
        [
            _Cursor(
                row={
                    "status": "ACTIVE",
                    "content_hash": definition.content_hash,
                    "payload_json": definition.model_dump(mode="json"),
                }
            ),
            update_cursor,
        ]
    )
    repository._connect = lambda: rowcount_connection  # type: ignore[attr-defined, method-assign]
    with pytest.raises(
        DpmBulkReviewCampaignDefinitionConflictError,
        match="BULK_REVIEW_CAMPAIGN_DEFINITION_STALE_WRITE",
    ):
        getattr(repository, method_name)(
            definition=updated,
            expected_content_hash=definition.content_hash,
        )
    assert rowcount_connection.rolled_back is True


@pytest.mark.parametrize(
    ("method_name", "stale_builder", "persisted_builder"),
    [
        (
            "record_definition_launch",
            lambda definition: record_bulk_review_campaign_definition_launch(
                definition=definition,
                wave_id="dwv_campaign_launch_001",
                launched_by="pm_001",
                requested_as_of_date="2026-05-10",
                correlation_id="corr-campaign-definition-launch-001",
                idempotency_key=(
                    "campaign-launch:campaign-holdings-apple-tesla-20260510:2026.05:ready"
                ),
            ),
            lambda definition: record_bulk_review_campaign_definition_launch(
                definition=definition,
                wave_id="dwv_campaign_launch_002",
                launched_by="pm_002",
                requested_as_of_date="2026-05-10",
                correlation_id="corr-campaign-definition-launch-002",
                idempotency_key=(
                    "campaign-launch:campaign-holdings-apple-tesla-20260510:2026.05:retry"
                ),
            ),
        ),
        (
            "record_definition_approval_decision",
            lambda definition: record_bulk_review_campaign_definition_approval_decision(
                definition=definition,
                decision_type="APPROVED",
                decision_ref="BRC-APPROVAL-2026-05-001",
                decided_by="cio_ops_committee",
                decision_reason="Approved for bounded DPM campaign launch.",
                correlation_id="corr-campaign-approval-decision-001",
            ),
            lambda definition: record_bulk_review_campaign_definition_approval_decision(
                definition=definition,
                decision_type="REJECTED",
                decision_ref="BRC-APPROVAL-2026-05-002",
                decided_by="cio_ops_committee",
                decision_reason="Rejected by an independent review path.",
                correlation_id="corr-campaign-approval-decision-002",
            ),
        ),
        (
            "record_definition_assignment_action",
            lambda definition: record_bulk_review_campaign_definition_assignment_action(
                definition=definition,
                action_type="ASSIGNED",
                action_ref="BRC-ASSIGN-2026-05-001",
                recorded_by="ops",
                action_reason="Route campaign to assigned PM.",
                assigned_actor_ids=["pm_001"],
                escalation_tier="PM",
                sla_posture="ON_TRACK",
                correlation_id="corr-campaign-assignment-action-001",
            ),
            lambda definition: record_bulk_review_campaign_definition_assignment_action(
                definition=definition,
                action_type="ESCALATED",
                action_ref="BRC-ASSIGN-2026-05-002",
                recorded_by="ops",
                action_reason="Escalate campaign to governance operations.",
                assigned_actor_ids=["governance_ops"],
                escalation_tier="GOVERNANCE",
                sla_posture="ATTENTION",
                correlation_id="corr-campaign-assignment-action-002",
            ),
        ),
        (
            "record_definition_assignment_task",
            lambda definition: open_bulk_review_campaign_definition_assignment_task(
                definition=definition,
                task_ref="BRC-TASK-2026-05-001",
                task_type="ASSIGNMENT",
                opened_by="ops",
                task_reason="Campaign requires PM acknowledgement.",
                assigned_actor_ids=["pm_001"],
                escalation_tier="PM",
                sla_posture="ON_TRACK",
                correlation_id="corr-campaign-assignment-task-001",
            ),
            lambda definition: open_bulk_review_campaign_definition_assignment_task(
                definition=definition,
                task_ref="BRC-TASK-2026-05-002",
                task_type="ESCALATION",
                opened_by="ops",
                task_reason="Campaign requires operations escalation.",
                assigned_actor_ids=["ops_lead"],
                escalation_tier="OPS",
                sla_posture="ATTENTION",
                correlation_id="corr-campaign-assignment-task-002",
            ),
        ),
        (
            "record_definition_maker_checker_control",
            lambda definition: record_bulk_review_campaign_definition_maker_checker_control(
                definition=definition,
                control_action="SUBMITTED_FOR_REVIEW",
                control_ref="BRC-MC-2026-05-001",
                recorded_by="ops",
                submitter_actor_id="pm_001",
                control_outcome="PENDING",
                control_reason="Campaign definition submitted for independent review.",
                correlation_id="corr-campaign-maker-checker-control-001",
            ),
            lambda definition: record_bulk_review_campaign_definition_maker_checker_control(
                definition=definition,
                control_action="SUBMITTED_FOR_REVIEW",
                control_ref="BRC-MC-2026-05-002",
                recorded_by="ops",
                submitter_actor_id="pm_002",
                control_outcome="PENDING",
                control_reason="Parallel campaign definition review submission.",
                correlation_id="corr-campaign-maker-checker-control-002",
            ),
        ),
    ],
)
def test_postgres_campaign_definition_repository_rejects_stale_workflow_append(
    method_name: str,
    stale_builder,
    persisted_builder,
) -> None:
    definition = _definition()
    stale_update = stale_builder(definition)
    persisted_update = persisted_builder(definition)
    repository = object.__new__(PostgresDpmBulkReviewCampaignDefinitionRepository)
    connection = _Connection(
        [
            _Cursor(
                row={
                    "status": "ACTIVE",
                    "content_hash": persisted_update.content_hash,
                    "payload_json": persisted_update.model_dump(mode="json"),
                }
            ),
        ]
    )
    repository._connect = lambda: connection  # type: ignore[attr-defined, method-assign]

    with pytest.raises(
        DpmBulkReviewCampaignDefinitionConflictError,
        match="BULK_REVIEW_CAMPAIGN_DEFINITION_STALE_WRITE",
    ):
        getattr(repository, method_name)(
            definition=stale_update,
            expected_content_hash=definition.content_hash,
        )

    assert connection.rolled_back is True
    assert len(connection.statements) == 1


def test_postgres_campaign_definition_repository_records_assignment_tasks() -> None:
    definition = _definition()
    opened = open_bulk_review_campaign_definition_assignment_task(
        definition=definition,
        task_ref="BRC-TASK-2026-05-001",
        task_type="ASSIGNMENT",
        opened_by="ops",
        task_reason="Campaign requires PM acknowledgement.",
        assigned_actor_ids=["pm_001"],
        escalation_tier="PM",
        sla_posture="ON_TRACK",
        correlation_id="corr-campaign-assignment-task-001",
    )
    repository = object.__new__(PostgresDpmBulkReviewCampaignDefinitionRepository)
    connection = _Connection(
        [
            _Cursor(
                row={
                    "status": "ACTIVE",
                    "content_hash": definition.content_hash,
                    "payload_json": definition.model_dump(mode="json"),
                }
            ),
            _Cursor(),
        ]
    )
    repository._connect = lambda: connection  # type: ignore[attr-defined, method-assign]

    assert (
        repository.record_definition_assignment_task(
            definition=opened,
            expected_content_hash=definition.content_hash,
        )
        == opened
    )
    assert connection.committed is True


def test_postgres_campaign_definition_repository_records_assignment_task_edges() -> None:
    definition = _definition()
    opened = open_bulk_review_campaign_definition_assignment_task(
        definition=definition,
        task_ref="BRC-TASK-2026-05-001",
        task_type="ASSIGNMENT",
        opened_by="ops",
        task_reason="Campaign requires PM acknowledgement.",
        assigned_actor_ids=["pm_001"],
        escalation_tier="PM",
        sla_posture="ON_TRACK",
        correlation_id="corr-campaign-assignment-task-001",
    )

    repository = object.__new__(PostgresDpmBulkReviewCampaignDefinitionRepository)
    missing_connection = _Connection([_Cursor(row=None)])
    repository._connect = lambda: missing_connection  # type: ignore[attr-defined, method-assign]
    assert (
        repository.record_definition_assignment_task(
            definition=opened,
            expected_content_hash=definition.content_hash,
        )
        is None
    )
    assert missing_connection.rolled_back is True

    replay_connection = _Connection(
        [
            _Cursor(
                row={
                    "status": "ACTIVE",
                    "content_hash": opened.content_hash,
                    "payload_json": opened.model_dump(mode="json"),
                }
            )
        ]
    )
    repository._connect = lambda: replay_connection  # type: ignore[attr-defined, method-assign]
    assert (
        repository.record_definition_assignment_task(
            definition=opened,
            expected_content_hash=definition.content_hash,
        )
        == opened
    )
    assert replay_connection.rolled_back is True

    retired = DpmBulkReviewCampaignDefinition.model_validate(
        {
            **definition.model_dump(mode="python"),
            "status": "RETIRED",
            "retired_at": "2026-05-11T08:00:00Z",
            "retired_by": "ops",
            "retirement_reason": "Campaign completed.",
            "retirement_correlation_id": "corr-campaign-definition-retire-001",
            "content_hash": "",
        }
    )
    inactive_connection = _Connection(
        [
            _Cursor(
                row={
                    "status": "RETIRED",
                    "content_hash": retired.content_hash,
                    "payload_json": retired.model_dump(mode="json"),
                }
            )
        ]
    )
    repository._connect = lambda: inactive_connection  # type: ignore[attr-defined, method-assign]
    with pytest.raises(
        DpmBulkReviewCampaignDefinitionConflictError,
        match="BULK_REVIEW_CAMPAIGN_DEFINITION_LIFECYCLE_CONFLICT",
    ):
        repository.record_definition_assignment_task(
            definition=opened,
            expected_content_hash=definition.content_hash,
        )
    assert inactive_connection.rolled_back is True

    update_cursor = _Cursor()
    update_cursor.rowcount = 0
    rowcount_connection = _Connection(
        [
            _Cursor(
                row={
                    "status": "ACTIVE",
                    "content_hash": definition.content_hash,
                    "payload_json": definition.model_dump(mode="json"),
                }
            ),
            update_cursor,
        ]
    )
    repository._connect = lambda: rowcount_connection  # type: ignore[attr-defined, method-assign]
    with pytest.raises(
        DpmBulkReviewCampaignDefinitionConflictError,
        match="BULK_REVIEW_CAMPAIGN_DEFINITION_STALE_WRITE",
    ):
        repository.record_definition_assignment_task(
            definition=opened,
            expected_content_hash=definition.content_hash,
        )
    assert rowcount_connection.rolled_back is True


def test_postgres_campaign_definition_repository_records_maker_checker_controls() -> None:
    definition = _definition()
    submitted = record_bulk_review_campaign_definition_maker_checker_control(
        definition=definition,
        control_action="SUBMITTED_FOR_REVIEW",
        control_ref="BRC-MC-2026-05-001",
        recorded_by="ops",
        submitter_actor_id="pm_001",
        control_outcome="PENDING",
        control_reason="Campaign definition submitted for independent review.",
        correlation_id="corr-campaign-maker-checker-control-001",
    )
    repository = object.__new__(PostgresDpmBulkReviewCampaignDefinitionRepository)
    connection = _Connection(
        [
            _Cursor(
                row={
                    "status": "ACTIVE",
                    "content_hash": definition.content_hash,
                    "payload_json": definition.model_dump(mode="json"),
                }
            ),
            _Cursor(),
        ]
    )
    repository._connect = lambda: connection  # type: ignore[attr-defined, method-assign]

    assert (
        repository.record_definition_maker_checker_control(
            definition=submitted,
            expected_content_hash=definition.content_hash,
        )
        == submitted
    )
    assert connection.committed is True


def test_postgres_campaign_definition_repository_records_maker_checker_control_edges() -> None:
    definition = _definition()
    submitted = record_bulk_review_campaign_definition_maker_checker_control(
        definition=definition,
        control_action="SUBMITTED_FOR_REVIEW",
        control_ref="BRC-MC-2026-05-001",
        recorded_by="ops",
        submitter_actor_id="pm_001",
        control_outcome="PENDING",
        control_reason="Campaign definition submitted for independent review.",
        correlation_id="corr-campaign-maker-checker-control-001",
    )

    repository = object.__new__(PostgresDpmBulkReviewCampaignDefinitionRepository)
    missing_connection = _Connection([_Cursor(row=None)])
    repository._connect = lambda: missing_connection  # type: ignore[attr-defined, method-assign]
    assert (
        repository.record_definition_maker_checker_control(
            definition=submitted,
            expected_content_hash=definition.content_hash,
        )
        is None
    )
    assert missing_connection.rolled_back is True

    replay_connection = _Connection(
        [
            _Cursor(
                row={
                    "status": "ACTIVE",
                    "content_hash": submitted.content_hash,
                    "payload_json": submitted.model_dump(mode="json"),
                }
            )
        ]
    )
    repository._connect = lambda: replay_connection  # type: ignore[attr-defined, method-assign]
    assert (
        repository.record_definition_maker_checker_control(
            definition=submitted,
            expected_content_hash=definition.content_hash,
        )
        == submitted
    )
    assert replay_connection.rolled_back is True

    retired = DpmBulkReviewCampaignDefinition.model_validate(
        {
            **definition.model_dump(mode="python"),
            "status": "RETIRED",
            "retired_at": "2026-05-11T08:00:00Z",
            "retired_by": "ops",
            "retirement_reason": "Campaign completed.",
            "retirement_correlation_id": "corr-campaign-definition-retire-001",
            "content_hash": "",
        }
    )
    inactive_connection = _Connection(
        [
            _Cursor(
                row={
                    "status": "RETIRED",
                    "content_hash": retired.content_hash,
                    "payload_json": retired.model_dump(mode="json"),
                }
            )
        ]
    )
    repository._connect = lambda: inactive_connection  # type: ignore[attr-defined, method-assign]
    with pytest.raises(
        DpmBulkReviewCampaignDefinitionConflictError,
        match="BULK_REVIEW_CAMPAIGN_DEFINITION_LIFECYCLE_CONFLICT",
    ):
        repository.record_definition_maker_checker_control(
            definition=submitted,
            expected_content_hash=definition.content_hash,
        )
    assert inactive_connection.rolled_back is True

    update_cursor = _Cursor()
    update_cursor.rowcount = 0
    rowcount_connection = _Connection(
        [
            _Cursor(
                row={
                    "status": "ACTIVE",
                    "content_hash": definition.content_hash,
                    "payload_json": definition.model_dump(mode="json"),
                }
            ),
            update_cursor,
        ]
    )
    repository._connect = lambda: rowcount_connection  # type: ignore[attr-defined, method-assign]
    with pytest.raises(
        DpmBulkReviewCampaignDefinitionConflictError,
        match="BULK_REVIEW_CAMPAIGN_DEFINITION_STALE_WRITE",
    ):
        repository.record_definition_maker_checker_control(
            definition=submitted,
            expected_content_hash=definition.content_hash,
        )
    assert rowcount_connection.rolled_back is True


def test_postgres_campaign_definition_repository_retirement_edges() -> None:
    definition = _definition()
    repository = object.__new__(PostgresDpmBulkReviewCampaignDefinitionRepository)
    missing_connection = _Connection([_Cursor(row=None)])
    repository._connect = lambda: missing_connection  # type: ignore[attr-defined, method-assign]

    assert repository.retire_definition(definition=definition) is None
    assert missing_connection.rolled_back is True

    retired = DpmBulkReviewCampaignDefinition.model_validate(
        {
            **definition.model_dump(mode="python"),
            "status": "RETIRED",
            "retired_at": "2026-05-11T08:00:00Z",
            "retired_by": "ops",
            "retirement_reason": "Campaign completed.",
            "retirement_correlation_id": "corr-campaign-definition-retire-001",
            "content_hash": "",
        }
    )
    retired_connection = _Connection(
        [
            _Cursor(
                row={
                    "status": "RETIRED",
                    "payload_json": retired.model_dump(mode="json"),
                }
            )
        ]
    )
    repository._connect = lambda: retired_connection  # type: ignore[attr-defined, method-assign]

    assert repository.retire_definition(definition=retired) == retired
    assert retired_connection.rolled_back is True


def test_postgres_campaign_definition_repository_lifecycle_conflict_edges() -> None:
    definition = _definition()
    retired = DpmBulkReviewCampaignDefinition.model_validate(
        {
            **definition.model_dump(mode="python"),
            "status": "RETIRED",
            "retired_at": "2026-05-11T08:00:00Z",
            "retired_by": "ops",
            "retirement_reason": "Campaign completed.",
            "retirement_correlation_id": "corr-campaign-definition-retire-001",
            "content_hash": "",
        }
    )
    superseded = DpmBulkReviewCampaignDefinition.model_validate(
        {
            **definition.model_dump(mode="python"),
            "status": "SUPERSEDED",
            "superseded_at": "2026-05-12T08:00:00Z",
            "superseded_by": "ops",
            "supersession_reason": "Campaign candidate set refreshed.",
            "supersession_correlation_id": "corr-campaign-definition-supersede-001",
            "superseded_by_campaign_id": definition.campaign_id,
            "superseded_by_campaign_version": "2026.06",
            "superseded_by_content_hash": "sha256:replacement",
            "content_hash": "",
        }
    )
    failed_update = _Cursor()
    failed_update.rowcount = 0
    repository = object.__new__(PostgresDpmBulkReviewCampaignDefinitionRepository)
    retire_connection = _Connection(
        [
            _Cursor(row={"status": "ACTIVE", "payload_json": definition.model_dump(mode="json")}),
            failed_update,
        ]
    )
    repository._connect = lambda: retire_connection  # type: ignore[attr-defined, method-assign]

    with pytest.raises(
        DpmBulkReviewCampaignDefinitionConflictError,
        match="BULK_REVIEW_CAMPAIGN_DEFINITION_LIFECYCLE_CONFLICT",
    ):
        repository.retire_definition(definition=retired)
    assert retire_connection.rolled_back is True

    failed_supersede = _Cursor()
    failed_supersede.rowcount = 0
    supersede_connection = _Connection(
        [
            _Cursor(row={"status": "ACTIVE", "payload_json": definition.model_dump(mode="json")}),
            failed_supersede,
        ]
    )
    repository._connect = lambda: supersede_connection  # type: ignore[attr-defined, method-assign]

    with pytest.raises(
        DpmBulkReviewCampaignDefinitionConflictError,
        match="BULK_REVIEW_CAMPAIGN_DEFINITION_LIFECYCLE_CONFLICT",
    ):
        repository.supersede_definition(definition=superseded)
    assert supersede_connection.rolled_back is True

    superseded_connection = _Connection(
        [
            _Cursor(
                row={
                    "status": "SUPERSEDED",
                    "payload_json": superseded.model_dump(mode="json"),
                }
            )
        ]
    )
    repository._connect = lambda: superseded_connection  # type: ignore[attr-defined, method-assign]

    assert repository.supersede_definition(definition=superseded) == superseded
    assert superseded_connection.rolled_back is True

    missing_supersede_connection = _Connection([_Cursor(row=None)])
    repository._connect = lambda: missing_supersede_connection  # type: ignore[attr-defined, method-assign]

    assert repository.supersede_definition(definition=superseded) is None
    assert missing_supersede_connection.rolled_back is True


def test_postgres_campaign_definition_repository_init_guards(monkeypatch) -> None:
    with pytest.raises(RuntimeError, match="DPM_CAMPAIGN_DEFINITION_POSTGRES_DSN_REQUIRED"):
        PostgresDpmBulkReviewCampaignDefinitionRepository(dsn="")

    monkeypatch.setattr(campaign_definition_infra, "has_psycopg", lambda: False)
    with pytest.raises(RuntimeError, match="DPM_CAMPAIGN_DEFINITION_POSTGRES_DRIVER_MISSING"):
        PostgresDpmBulkReviewCampaignDefinitionRepository(dsn="postgresql://campaigns")


def test_postgres_campaign_definition_repository_connects_and_initializes(monkeypatch) -> None:
    first_expected_connection = _Connection([_Cursor()])
    init_expected_connection = _Connection([_Cursor()])
    connections = [first_expected_connection, init_expected_connection]
    connect_calls: list[dict[str, object]] = []
    migrations: list[tuple[_Connection, str]] = []
    dict_row = object()

    class FakePsycopg:
        @staticmethod
        def connect(dsn: str, **kwargs: object) -> _Connection:
            connect_calls.append({"dsn": dsn, **kwargs})
            return connections.pop(0)

    monkeypatch.setattr(
        campaign_definition_infra,
        "_import_psycopg",
        lambda: (FakePsycopg, dict_row),
    )
    monkeypatch.setattr(
        campaign_definition_infra,
        "apply_postgres_migrations",
        lambda *, connection, namespace: migrations.append((connection, namespace)),
    )
    repository = object.__new__(PostgresDpmBulkReviewCampaignDefinitionRepository)
    repository._dsn = "postgresql://campaigns"

    first_connection = repository._connect()
    repository._init_db()

    try:
        assert first_connection._connection is first_expected_connection  # noqa: SLF001
    finally:
        first_connection.close()
    assert [call["dsn"] for call in connect_calls] == [
        "postgresql://campaigns",
        "postgresql://campaigns",
    ]
    assert [call["row_factory"] for call in connect_calls] == [dict_row, dict_row]
    assert migrations[0][0]._connection is init_expected_connection  # noqa: SLF001
    assert migrations[0][1] == "dpm"


def test_postgres_campaign_definition_repository_init_stores_dsn(monkeypatch) -> None:
    init_calls: list[str] = []

    monkeypatch.setattr(campaign_definition_infra, "has_psycopg", lambda: True)
    monkeypatch.setattr(
        PostgresDpmBulkReviewCampaignDefinitionRepository,
        "_init_db",
        lambda self: init_calls.append(self._dsn),
    )

    repository = PostgresDpmBulkReviewCampaignDefinitionRepository(dsn="postgresql://campaigns")

    assert repository._dsn == "postgresql://campaigns"
    assert init_calls == ["postgresql://campaigns"]


def test_postgres_campaign_definition_payload_and_driver_import_edges() -> None:
    assert _payload({"payload_json": "raw-json"}) == "raw-json"
    psycopg, dict_row = _import_psycopg()

    assert psycopg is not None
    assert dict_row is not None


def test_campaign_workflow_read_model_migration_declares_projection_contract() -> None:
    migration = (
        Path(__file__).parents[4]
        / "src"
        / "infrastructure"
        / "postgres_migrations"
        / "dpm"
        / "0015_bulk_review_campaign_workflow_read_model.sql"
    ).read_text(encoding="utf-8")
    required_tokens = [
        "dpm_bulk_review_campaign_workflow_read_model",
        "definition_content_hash TEXT NOT NULL",
        "workflow_read_model_hash TEXT NOT NULL",
        "board_status TEXT NOT NULL",
        "next_action TEXT NOT NULL",
        "assignment_escalation_tier TEXT NOT NULL",
        "assignment_sla_posture TEXT NOT NULL",
        "assigned_actor_ids TEXT[] NOT NULL DEFAULT '{}'",
        "assignment_task_statuses TEXT[] NOT NULL DEFAULT '{}'",
        "maker_checker_outcomes TEXT[] NOT NULL DEFAULT '{}'",
        "approval_decision_count INTEGER NOT NULL DEFAULT 0",
        "assignment_action_count INTEGER NOT NULL DEFAULT 0",
        "assignment_task_transition_count INTEGER NOT NULL DEFAULT 0",
        "FOREIGN KEY (campaign_id, campaign_version)",
        "USING GIN (assignment_task_statuses)",
        "USING GIN (assigned_actor_ids)",
        "USING GIN (maker_checker_outcomes)",
        "INSERT INTO dpm_bulk_review_campaign_workflow_read_model",
        "jsonb_array_elements(COALESCE(payload_json -> 'assignment_tasks'",
        "AS actor_ids(actor_id)",
        "ON CONFLICT (campaign_id, campaign_version) DO NOTHING",
    ]

    assert [token for token in required_tokens if token not in migration] == []


def test_postgres_campaign_definition_repository_returns_none_for_missing_definition() -> None:
    repository = object.__new__(PostgresDpmBulkReviewCampaignDefinitionRepository)
    connection = _Connection([_Cursor(row=None)])
    repository._connect = lambda: connection  # type: ignore[attr-defined, method-assign]

    assert (
        repository.get_definition(
            tenant_id="tenant-sg",
            campaign_id="missing",
            campaign_version="2026.05",
        )
        is None
    )


def test_postgres_campaign_definition_repository_detects_conflict() -> None:
    definition = _definition()
    repository = object.__new__(PostgresDpmBulkReviewCampaignDefinitionRepository)
    connection = _Connection([_Cursor(), _Cursor(row={"content_hash": "sha256:different"})])
    repository._connect = lambda: connection  # type: ignore[attr-defined, method-assign]

    with pytest.raises(
        DpmBulkReviewCampaignDefinitionConflictError,
        match="BULK_REVIEW_CAMPAIGN_DEFINITION_IMMUTABLE_CONFLICT",
    ):
        repository.save_definition(definition=definition)

    assert connection.rolled_back is True
