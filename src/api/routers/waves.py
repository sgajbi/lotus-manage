from __future__ import annotations

import hashlib
import json
import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal, cast

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel, Field

from src.api.observability import record_wave_supportability
from src.api.dependencies import (
    get_advise_authority_client,
    get_campaign_definition_repository,
    get_construction_repository,
    get_mandate_repository,
    get_outcome_review_repository,
    get_proof_pack_repository,
    get_risk_authority_client,
    get_wave_repository,
)
from src.api.request_models import RebalanceRequest
from src.api.routers.rebalance_runs import get_dpm_run_support_service
from src.api.services.rebalance_simulation_service import build_core_resolver_client
from src.api.services import wave_service
from src.core.construction.models import ConstructionAuthorityContext
from src.core.construction.repository import ConstructionRepository
from src.core.construction.vocabulary import ConstructionMethod
from src.core.mandate_repository import DpmMandateRepository
from src.core.proof_packs.repository import DpmProofPackRepository
from src.core.outcomes.repository import DpmOutcomeReviewRepository
from src.core.rebalance_runs.service import DpmRunSupportService
from src.core.waves import (
    DpmBulkReviewCampaignDefinition,
    DpmBulkReviewCampaignDefinitionConflictError,
    DpmBulkReviewCampaignDiscoveryPage,
    DpmBulkReviewCampaignDefinitionLaunchPackage,
    DpmBulkReviewCampaignDefinitionPreviewReadiness,
    DpmBulkReviewCampaignDefinitionRepository,
    DpmRebalanceWave,
    DpmWaveReportInput,
    DpmWaveRepository,
    DpmWaveSourceRef,
    build_bulk_review_campaign_discovery_item,
    build_bulk_review_campaign_definition_preview_readiness,
    build_bulk_review_campaign_definition_launch_package,
    record_bulk_review_campaign_definition_launch,
)
from src.core.waves.campaign_definitions import (
    DpmBulkReviewCampaignDefinitionCandidate,
    DpmBulkReviewCampaignDefinitionGovernance,
)
from src.core.waves.campaign_definition_lifecycle import (
    DpmBulkReviewCampaignDefinitionLifecycleError,
    retire_bulk_review_campaign_definition as retire_campaign_definition,
    supersede_bulk_review_campaign_definition as supersede_campaign_definition,
)
from src.core.waves.campaign_definition_events import (
    DpmBulkReviewCampaignDefinitionLifecycleEventPage,
    build_bulk_review_campaign_definition_lifecycle_events,
)
from src.infrastructure.core_sourcing import DpmCoreResolverError, DpmCoreResolverUnavailableError
from src.infrastructure.risk_authority import (
    LotusRiskAuthorityClient,
    LotusRiskAuthorityUnavailableError,
)
from src.infrastructure.advise_authority import (
    LotusAdviseAuthorityClient,
    LotusAdviseAuthorityUnavailableError,
)
from src.core.waves.models import (
    DpmRebalanceWaveItem,
    DpmWaveAggregateMetrics,
    DpmWaveHandoffRef,
)


WAVE_EXAMPLE = {
    "wave": {
        "wave_id": "dwv_001",
        "wave_version": "1.0.0",
        "state": "PREVIEWED",
        "trigger": {
            "trigger_type": "EXPLICIT_PORTFOLIO_LIST",
            "trigger_id": "manual-wave-20260503-001",
            "rationale": "Review explicitly selected portfolios after model drift triage.",
            "source_refs": [],
        },
        "as_of_date": "2026-05-03",
        "created_at": "2026-05-03T09:30:00Z",
        "created_by": "pm_001",
        "correlation_id": "corr-wave-001",
        "version": 2,
        "items": [
            {
                "wave_item_id": "dwi_001",
                "portfolio_id": "PB_SG_GLOBAL_BAL_001",
                "mandate_id": "MANDATE_PB_SG_GLOBAL_BAL_001",
                "state": "CANDIDATE",
                "reason_codes": ["AFFECTED_PORTFOLIO_SOURCE_READY"],
                "source_refs": [
                    {
                        "source_system": "lotus-manage",
                        "source_type": "AFFECTED_PORTFOLIO_MANIFEST",
                        "source_id": "manifest_20260503_001",
                        "source_version": "1.0.0",
                        "supportability_state": "READY",
                        "content_hash": "sha256:manifest-example",
                    }
                ],
                "diagnostics": {"source_posture": "candidate_evidence_available"},
            }
        ],
        "aggregate_metrics": {
            "item_count": 1,
            "state_counts": {"CANDIDATE": 1},
            "ready_item_count": 0,
            "blocked_item_count": 0,
            "review_required_item_count": 0,
            "source_degraded_item_count": 0,
        },
        "events": [],
        "retention_policy": "DPM_WAVE_STANDARD",
    },
    "durable": False,
    "idempotent_replay": False,
}

SOURCE_CHECK_WAVE_EXAMPLE = {
    "wave": {
        **cast(dict[str, object], WAVE_EXAMPLE["wave"]),
        "state": "SOURCE_CHECKED",
        "version": 4,
        "items": [
            {
                "wave_item_id": "dwi_001",
                "portfolio_id": "PB_SG_GLOBAL_BAL_001",
                "mandate_id": "MANDATE_PB_SG_GLOBAL_BAL_001",
                "model_portfolio_id": "MODEL_PB_SG_GLOBAL_BAL_DPM",
                "state": "SOURCE_READY",
                "reason_codes": ["SOURCE_READINESS_READY"],
                "source_refs": [
                    {
                        "source_system": "lotus-manage",
                        "source_type": "MANDATE_DIGITAL_TWIN",
                        "source_id": "MANDATE_PB_SG_GLOBAL_BAL_001",
                        "source_version": "3",
                        "supportability_state": "READY",
                    },
                    {
                        "source_system": "lotus-manage",
                        "source_type": "DPM_MANDATE_HEALTH_SNAPSHOT",
                        "source_id": "mh_20260503_pb_sg_global_bal_001",
                        "source_version": "2026-05-03",
                        "supportability_state": "READY",
                    },
                    {
                        "source_system": "lotus-manage",
                        "source_type": "DPM_SOURCE_READINESS",
                        "source_id": "mh_20260503_pb_sg_global_bal_001",
                        "source_version": "2026-05-03",
                        "supportability_state": "READY",
                    },
                ],
                "diagnostics": {
                    "source_owner": "lotus-manage",
                    "health_state": "READY",
                    "source_readiness_state": "READY",
                },
            }
        ],
        "aggregate_metrics": {
            "item_count": 1,
            "state_counts": {"SOURCE_READY": 1},
            "ready_item_count": 1,
            "blocked_item_count": 0,
            "review_required_item_count": 0,
            "source_degraded_item_count": 0,
        },
    },
    "durable": True,
    "idempotent_replay": False,
}


class DpmWavePortfolioInput(BaseModel):
    portfolio_id: str = Field(
        description="Explicit affected portfolio identifier.",
        examples=["PB_SG_GLOBAL_BAL_001"],
    )
    mandate_id: str | None = Field(
        default=None,
        description="Known mandate id from reviewed source evidence, when supplied.",
        examples=["MANDATE_PB_SG_GLOBAL_BAL_001"],
    )
    portfolio_manager_id: str | None = Field(
        default=None,
        description="Portfolio-manager identifier preserved for source-owned cohort lineage.",
        examples=["PM_SG_DPM_001"],
    )
    exposure_weights: dict[str, float] = Field(
        default_factory=dict,
        description=(
            "Required for `RISK_EVENT`. Source-supplied exposure weights by risk-event bucket; "
            "manage forwards them to lotus-risk and does not calculate risk-event impact locally."
        ),
        examples=[{"EQUITY": 0.55, "FIXED_INCOME": 0.35, "CASH": 0.10}],
    )
    portfolio_type: str | None = Field(
        default=None,
        description=(
            "Source-owned portfolio type used by `BULK_REVIEW_CAMPAIGN` and "
            "`TACTICAL_HOUSE_VIEW` to filter DPM operating cohorts. Manage does not infer this "
            "value."
        ),
        examples=["DISCRETIONARY"],
    )
    discretionary_mandate: bool | None = Field(
        default=None,
        description=(
            "Required for `TACTICAL_HOUSE_VIEW`. Source-owned indicator that the candidate is "
            "managed/discretionary; Manage forwards it to lotus-advise and does not infer it."
        ),
        examples=[True],
    )
    current_exposure_weight: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description=(
            "Optional source-owned tactical-theme exposure weight for `TACTICAL_HOUSE_VIEW`."
        ),
        examples=[0.18],
    )
    alignment_signal: Literal["OVERWEIGHT", "UNDERWEIGHT", "ALIGNED", "UNKNOWN"] = Field(
        default="UNKNOWN",
        description="Source-owned tactical house-view alignment posture for the candidate.",
        examples=["UNDERWEIGHT"],
    )
    source_refs: list[DpmWaveSourceRef] = Field(
        default_factory=list,
        description=(
            "Source refs proving why this portfolio belongs in the affected set. When omitted, "
            "manage attempts to attach an existing mandate digital-twin ref; otherwise the item "
            "is blocked rather than treated as source-ready."
        ),
    )


class DpmTacticalHouseViewInput(BaseModel):
    tactical_view_id: str = Field(
        description="Bank tactical house-view identifier.",
        examples=["THV_2026_Q2_US_QUALITY"],
    )
    tactical_view_version: str = Field(
        description="Immutable tactical house-view version.",
        examples=["2026.05"],
    )
    theme_id: str = Field(
        description="Tactical theme or recommendation identifier.",
        examples=["US_QUALITY_EQUITIES"],
    )
    target_action: Literal["INCREASE", "REDUCE", "REVIEW", "EXCLUDE"] = Field(
        description="Bank tactical action evaluated by lotus-advise.",
        examples=["INCREASE"],
    )
    rationale: str = Field(description="Bank-authored tactical house-view rationale.")
    source_refs: list[DpmWaveSourceRef] = Field(
        description="Governed source refs for the bank-authored tactical house-view decision."
    )


class DpmBulkReviewCampaignGovernanceInput(BaseModel):
    approval_ref: str | None = Field(
        default=None,
        description=(
            "Optional bank approval reference for this bulk-review campaign. When any approval "
            "field is supplied, all approval fields are required."
        ),
        examples=["BRC-APPROVAL-2026-05"],
    )
    approved_by: str | None = Field(
        default=None,
        description="Optional approving actor or committee identifier.",
        examples=["cio_ops_committee"],
    )
    approved_at: str | None = Field(
        default=None,
        description="Optional approval timestamp or business date from the bank control record.",
        examples=["2026-05-14T08:30:00+08:00"],
    )
    expires_on: str | None = Field(
        default=None,
        description=(
            "Optional campaign expiry date. Expired campaigns fail closed for preview/create."
        ),
        examples=["2026-06-30"],
    )
    entitled_actor_ids: list[str] = Field(
        default_factory=list,
        description=(
            "Optional actor allow-list for this campaign. When supplied, actor_id must be listed."
        ),
        examples=[["pm_001", "ops"]],
    )
    access_purpose: str = Field(
        default="DPM_BULK_REVIEW_CAMPAIGN",
        description="Bank access purpose preserved in campaign membership diagnostics.",
        examples=["DPM_BULK_REVIEW_CAMPAIGN"],
    )
    source_refs: list[DpmWaveSourceRef] = Field(
        default_factory=list,
        description="Optional source refs for approval, entitlement, or campaign-control evidence.",
    )


class DpmBulkReviewCampaignDefinitionRequest(BaseModel):
    display_name: str = Field(examples=["Apple and Tesla holdings review"])
    status: Literal["ACTIVE"] = Field(default="ACTIVE")
    as_of_date: str = Field(examples=["2026-05-10"])
    rationale: str = Field(description="Business rationale for the persisted campaign definition.")
    eligible_portfolio_types: list[str] = Field(default_factory=lambda: ["DISCRETIONARY"])
    candidates: list[DpmBulkReviewCampaignDefinitionCandidate] = Field(
        description=(
            "Source-backed candidates captured by the campaign definition. Manage persists this "
            "bounded set but does not discover a global portfolio universe."
        )
    )
    governance: DpmBulkReviewCampaignDefinitionGovernance | None = Field(default=None)
    source_refs: list[DpmWaveSourceRef] = Field(default_factory=list)
    created_by: str = Field(examples=["ops"])
    correlation_id: str = Field(examples=["corr-campaign-definition-001"])


class DpmBulkReviewCampaignDefinitionRetirementRequest(BaseModel):
    retired_by: str = Field(
        description="Actor retiring the campaign definition for future preview/create use.",
        examples=["ops"],
    )
    retirement_reason: str = Field(
        description="Business reason for retiring the persisted campaign definition.",
        examples=["Campaign review completed and no longer available for new waves."],
    )
    correlation_id: str = Field(examples=["corr-campaign-definition-retire-001"])


class DpmBulkReviewCampaignDefinitionSupersessionRequest(BaseModel):
    superseded_by_campaign_version: str = Field(
        description=(
            "Replacement version for the same campaign id. The replacement definition must already "
            "exist and be ACTIVE."
        ),
        examples=["2026.06"],
    )
    superseded_by: str = Field(
        description="Actor superseding the campaign definition for future preview/create use.",
        examples=["ops"],
    )
    supersession_reason: str = Field(
        description="Business reason for replacing the persisted campaign definition.",
        examples=["Updated source-backed candidate set after campaign refresh."],
    )
    correlation_id: str = Field(examples=["corr-campaign-definition-supersede-001"])


class DpmBulkReviewCampaignDefinitionLaunchRequest(BaseModel):
    requested_as_of_date: str = Field(
        description="ISO date used for the durable campaign wave.",
        examples=["2026-05-10"],
    )
    actor_id: str = Field(
        description="Human or service actor launching the persisted campaign definition.",
        examples=["pm_001"],
    )
    correlation_id: str | None = Field(
        default=None,
        description=(
            "Optional correlation id for the durable wave. When omitted, Manage derives the same "
            "deterministic correlation id used by the launch package."
        ),
    )


class DpmBulkReviewCampaignDefinitionPage(BaseModel):
    items: list[DpmBulkReviewCampaignDefinition]
    limit: int
    offset: int
    count: int


class DpmWavePreviewRequest(BaseModel):
    trigger_type: Literal[
        "EXPLICIT_PORTFOLIO_LIST",
        "PM_BOOK_REVIEW",
        "CIO_MODEL_CHANGE",
        "TACTICAL_HOUSE_VIEW",
        "RISK_EVENT",
        "BULK_REVIEW_CAMPAIGN",
    ] = Field(description="Wave trigger type.", examples=["EXPLICIT_PORTFOLIO_LIST"])
    trigger_id: str = Field(description="Business trigger identifier.", examples=["manual-001"])
    rationale: str = Field(
        description="Business rationale for reviewing the affected portfolio set.",
        examples=["Review explicit portfolio list after CIO desk model-change triage."],
    )
    as_of_date: str = Field(description="Business as-of date.", examples=["2026-05-03"])
    actor_id: str = Field(description="Human or service actor.", examples=["pm_001"])
    portfolios: list[DpmWavePortfolioInput] = Field(
        default_factory=list,
        description="Explicit affected portfolios for the first supported RFC-0041 trigger.",
        examples=[
            [
                {
                    "portfolio_id": "PB_SG_GLOBAL_BAL_001",
                    "mandate_id": "MANDATE_PB_SG_GLOBAL_BAL_001",
                    "source_refs": [
                        {
                            "source_system": "lotus-manage",
                            "source_type": "AFFECTED_PORTFOLIO_MANIFEST",
                            "source_id": "manifest_20260503_001",
                            "source_version": "1.0.0",
                            "supportability_state": "READY",
                        }
                    ],
                }
            ]
        ],
    )
    portfolio_manager_id: str | None = Field(
        default=None,
        description=(
            "Required for `PM_BOOK_REVIEW`. Manage resolves the affected cohort from the "
            "lotus-core `PortfolioManagerBookMembership:v1` source product."
        ),
        examples=["PM_SG_DPM_001"],
    )
    model_portfolio_id: str | None = Field(
        default=None,
        description=(
            "Required for `CIO_MODEL_CHANGE`. Manage resolves the affected cohort from the "
            "lotus-core `CioModelChangeAffectedCohort:v1` source product."
        ),
        examples=["MODEL_PB_SG_GLOBAL_BAL_DPM"],
    )
    risk_event_id: str | None = Field(
        default=None,
        description=(
            "Required for `RISK_EVENT`. Manage evaluates the candidate set through lotus-risk "
            "`RiskEventAffectedCohort:v1` and preserves source-owned membership evidence."
        ),
        examples=["RISK_EVENT_2026_Q2_RATES_UP"],
    )
    tactical_house_view: DpmTacticalHouseViewInput | None = Field(
        default=None,
        description=(
            "Required for `TACTICAL_HOUSE_VIEW`. Manage forwards this bank-authored house-view "
            "instruction and source-backed candidate portfolios to lotus-advise "
            "`TacticalHouseViewAffectedCohort:v1`."
        ),
    )
    campaign_definition_id: str | None = Field(
        default=None,
        description=(
            "Optional persisted Manage-owned bulk-review campaign definition id. When supplied "
            "for `BULK_REVIEW_CAMPAIGN`, Manage uses the persisted source-backed candidate set."
        ),
        examples=["campaign-holdings-apple-tesla-20260510"],
    )
    campaign_definition_version: str | None = Field(
        default=None,
        description="Required with campaign_definition_id.",
        examples=["2026.05"],
    )
    minimum_impact_score: float = Field(
        default=0.05,
        ge=0.0,
        description="Minimum source-owned risk-event impact score required for cohort inclusion.",
        examples=[0.05],
    )
    min_tactical_exposure_weight: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description=(
            "Optional minimum source-owned tactical-theme exposure weight forwarded to "
            "lotus-advise for `TACTICAL_HOUSE_VIEW` cohort evaluation."
        ),
        examples=[0.05],
    )
    tenant_id: str | None = Field(
        default=None,
        description="Optional tenant selector forwarded to source products where supported.",
        examples=["default"],
    )
    booking_center_code: str | None = Field(
        default=None,
        description="Optional booking-center filter for PM-book discovery.",
        examples=["Singapore"],
    )
    portfolio_types: list[str] = Field(
        default_factory=lambda: ["DISCRETIONARY"],
        description="PM-book portfolio types eligible for automatic wave discovery.",
        examples=[["DISCRETIONARY"]],
    )
    campaign_governance: DpmBulkReviewCampaignGovernanceInput | None = Field(
        default=None,
        description=(
            "Optional Manage-owned governance evidence for `BULK_REVIEW_CAMPAIGN`, covering "
            "approval reference, expiry, actor entitlement, access purpose, and source refs. "
            "Manage validates this envelope but does not infer source-owned cohort facts."
        ),
    )


class DpmWaveResponse(BaseModel):
    wave: DpmRebalanceWave = Field(description="Previewed or durable rebalance wave.")
    durable: bool = Field(
        description="Whether this response was durably persisted.", examples=[False]
    )
    supportability: "DpmWaveSupportabilityResponse" = Field(
        description=(
            "Product-safe wave supportability derived by lotus-manage from item states. "
            "Gateway and Workbench must preserve this authority-owned posture instead of "
            "reconstructing readiness."
        )
    )
    idempotent_replay: bool = Field(
        default=False,
        description="True when create returned an already persisted wave for the idempotency key.",
        examples=[False],
    )


class DpmWaveSearchItem(BaseModel):
    wave_id: str = Field(description="Wave identifier.", examples=["dwv_001"])
    wave_state: str = Field(description="Current wave state.", examples=["HANDOFF_READY"])
    trigger_type: str = Field(
        description="Bounded trigger type used to create the wave.",
        examples=["EXPLICIT_PORTFOLIO_LIST"],
    )
    trigger_id: str = Field(description="Business trigger identifier.", examples=["manual-001"])
    as_of_date: str = Field(description="Business as-of date.", examples=["2026-05-03"])
    created_at: datetime = Field(
        description="UTC timestamp when the wave was created.",
        examples=["2026-05-03T09:30:00Z"],
    )
    created_by: str = Field(description="Actor that created the wave.", examples=["pm_001"])
    item_count: int = Field(description="Number of wave items.", examples=[2])
    aggregate_metrics: DpmWaveAggregateMetrics = Field(
        description="Aggregate item counts reconciled from persisted wave state."
    )
    supportability_state: Literal["ready", "degraded", "blocked"] = Field(
        description="Product-safe supportability posture for search and triage.",
        examples=["ready"],
    )
    supportability_reason: str = Field(
        description="Bounded reason for the supportability state.",
        examples=["wave_supportability_ready"],
    )
    latest_event_type: str | None = Field(
        default=None,
        description="Latest persisted event type for operator context.",
        examples=["STATE_TRANSITION"],
    )
    latest_event_reason_code: str | None = Field(
        default=None,
        description="Latest persisted event reason code for operator context.",
        examples=["WAVE_HANDOFF_READY"],
    )


class DpmWaveSearchResponse(BaseModel):
    items: list[DpmWaveSearchItem] = Field(
        description="Bounded page of persisted waves matching the search filters."
    )
    limit: int = Field(description="Requested page size.", examples=[50])
    offset: int = Field(description="Requested page offset.", examples=[0])
    returned_count: int = Field(description="Number of waves returned.", examples=[1])


class DpmWaveSourceCheckRequest(BaseModel):
    actor_id: str = Field(
        description="Human or service actor requesting the source-check.",
        examples=["pm_001"],
    )


class DpmWaveSimulationItemInput(BaseModel):
    wave_item_id: str | None = Field(
        default=None,
        description="Wave item id receiving this construction input.",
        examples=["dwi_001"],
    )
    portfolio_id: str | None = Field(
        default=None,
        description="Portfolio id fallback when the caller does not know the wave item id.",
        examples=["PB_SG_GLOBAL_BAL_001"],
    )
    stateless_input: RebalanceRequest = Field(
        description=(
            "Complete RFC-0039 stateless construction input for this ready item. "
            "Wave simulation does not synthesize holdings, market data, or shelf data."
        )
    )
    authority_context: ConstructionAuthorityContext | None = Field(
        default=None,
        description=(
            "Optional source-backed risk/performance authority context for this item. "
            "Risk context may also be resolved from lotus-risk when `DPM_RISK_BASE_URL` is "
            "configured and `RISK_AWARE` is requested; performance context must be supplied "
            "from lotus-performance until a dedicated manage performance client is promoted."
        ),
    )


class DpmWaveSimulationRequest(BaseModel):
    actor_id: str = Field(
        description="Human or service actor requesting wave simulation.",
        examples=["pm_001"],
    )
    item_inputs: list[DpmWaveSimulationItemInput] = Field(
        default_factory=list,
        description="Per-item RFC-0039 construction inputs for source-ready items.",
    )
    methods: list[ConstructionMethod] | None = Field(
        default=None,
        description="Optional RFC-0039 construction methods. Omit for the first-wave default.",
        examples=[["DO_NOTHING_BASELINE", "HEURISTIC_EXPLAINABLE", "MIN_TURNOVER"]],
    )


class DpmWaveSelectionRequest(BaseModel):
    alternative_id: str = Field(
        description="Construction alternative id selected for the wave item.",
        examples=["alt_min_turnover"],
    )
    actor_id: str = Field(
        description="Human or service actor recording the selection.",
        examples=["pm_001"],
    )
    reason_code: str = Field(
        description="Bounded reason code explaining the selection.",
        examples=["LOWER_TURNOVER_WITH_ACCEPTABLE_DRIFT"],
    )
    comment: str | None = Field(
        default=None,
        description="Optional business comment for audit.",
        examples=["Chosen before month-end liquidity window."],
    )
    generate_proof_pack: bool = Field(
        default=True,
        description=(
            "When true, generate an RFC-0040 proof pack from the selected alternative. "
            "Failures degrade the item rather than fabricating proof-pack readiness."
        ),
        examples=[True],
    )


class DpmWaveWorkflowCommandRequest(BaseModel):
    actor_id: str = Field(
        description="Human or service actor applying the workflow command.",
        examples=["pm_001"],
    )
    reason_code: str = Field(
        description="Bounded business reason code for the workflow command.",
        examples=["READY_FOR_OPERATIONS_REVIEW"],
    )
    comment: str | None = Field(
        default=None,
        description="Optional business comment for audit.",
        examples=["Approved after proof-pack review."],
    )


class DpmWaveSupportabilityIssue(BaseModel):
    support_ref: str = Field(
        description="Opaque support reference that avoids portfolio or client identifiers.",
        examples=["wave:dwv_001:item:1"],
    )
    item_state: str = Field(description="Wave item workflow state.", examples=["SOURCE_BLOCKED"])
    severity: Literal["INFO", "WARNING", "CRITICAL"] = Field(
        description="Operator severity for this issue.",
        examples=["CRITICAL"],
    )
    source_owner: str = Field(
        description="Owning product or route responsible for remediation.",
        examples=["lotus-manage"],
    )
    reason_codes: list[str] = Field(
        description="Bounded reason codes explaining supportability posture.",
        examples=[["MANDATE_DIGITAL_TWIN_MISSING"]],
    )
    remediation_route: str = Field(
        description="Product-safe remediation route or action.",
        examples=["REPAIR_SOURCE_DATA"],
    )


class DpmWaveSupportabilityResponse(BaseModel):
    wave_id: str = Field(description="Wave identifier.", examples=["dwv_001"])
    wave_state: str = Field(description="Current wave state.", examples=["SOURCE_CHECKED"])
    supportability_state: Literal["ready", "degraded", "blocked"] = Field(
        description="Bounded supportability state for the wave.",
        examples=["blocked"],
    )
    reason: str = Field(
        description="Bounded supportability reason.",
        examples=["wave_blocked_items"],
    )
    item_count: int = Field(description="Number of wave items inspected.", examples=[2])
    issue_counts: dict[str, int] = Field(
        description="Issue count by severity.",
        examples=[{"critical": 1, "warning": 0, "info": 1}],
    )
    issues: list[DpmWaveSupportabilityIssue] = Field(
        description=(
            "Product-safe issues without portfolio ids, client ids, raw requests, raw responses, "
            "secrets, or trace values."
        )
    )
    operator_actions: list[str] = Field(
        description="Deduplicated product-safe remediation actions.",
        examples=[["REPAIR_SOURCE_DATA", "RUN_WAVE_SIMULATION"]],
    )


class DpmWaveDetailResponse(BaseModel):
    wave: DpmRebalanceWave = Field(description="Persisted wave detail.")
    supportability: DpmWaveSupportabilityResponse = Field(
        description="Latest product-safe supportability derived from persisted item states."
    )
    proof_pack_posture: "DpmWaveProofPackPostureResponse" = Field(
        description="Wave proof-pack and internal operations handoff posture."
    )


class DpmWaveItemsResponse(BaseModel):
    wave_id: str = Field(description="Wave identifier.", examples=["dwv_001"])
    wave_state: str = Field(description="Current wave state.", examples=["HANDOFF_READY"])
    items: list[DpmRebalanceWaveItem] = Field(
        description="Persisted item list with source readiness, selection, proof-pack, and handoff posture."
    )
    aggregate_metrics: DpmWaveAggregateMetrics = Field(
        description="Aggregate item counts reconciled from persisted wave state."
    )


class DpmWaveProofPackRef(BaseModel):
    wave_item_id: str = Field(description="Wave item identifier.", examples=["dwi_001"])
    proof_pack_id: str | None = Field(
        default=None,
        description="Linked RFC-0040 proof-pack id when generated.",
        examples=["dpp_001"],
    )
    item_state: str = Field(description="Current item state.", examples=["PROOF_PACK_READY"])
    proof_pack_state: str | None = Field(
        default=None,
        description="Proof-pack posture captured in item diagnostics.",
        examples=["READY"],
    )
    selected_alternative_id: str | None = Field(
        default=None,
        description="Selected RFC-0039 construction alternative id.",
        examples=["alt_min_turnover"],
    )


class DpmWaveProofPackPostureResponse(BaseModel):
    wave_id: str = Field(description="Wave identifier.", examples=["dwv_001"])
    wave_state: str = Field(description="Current wave state.", examples=["HANDOFF_READY"])
    item_count: int = Field(description="Total item count.", examples=[2])
    linked_item_count: int = Field(description="Items with linked proof packs.", examples=[1])
    ready_proof_pack_count: int = Field(
        description="Linked proof packs that are not degraded.", examples=[1]
    )
    degraded_proof_pack_count: int = Field(
        description="Items with degraded proof-pack posture.", examples=[0]
    )
    proof_pack_refs: list[DpmWaveProofPackRef] = Field(
        description="Item-level proof-pack references and posture."
    )
    handoff_refs: list[DpmWaveHandoffRef] = Field(
        description="Append-only internal operations handoff evidence refs."
    )
    external_execution_claimed: bool = Field(
        description=(
            "Always false for valid manage-owned handoff evidence. If persisted evidence ever "
            "contains an external execution claim, downstream report input is blocked until an "
            "external OMS/execution owner contract exists."
        ),
        examples=[False],
    )


router = APIRouter(prefix="/rebalance/waves", tags=["lotus-manage Rebalance Waves"])
logger = logging.getLogger(__name__)


def _wave_response(
    *,
    wave: DpmRebalanceWave,
    durable: bool,
    idempotent_replay: bool = False,
) -> DpmWaveResponse:
    return DpmWaveResponse(
        wave=wave,
        durable=durable,
        supportability=DpmWaveSupportabilityResponse.model_validate(
            wave_service.wave_supportability_payload(wave)
        ),
        idempotent_replay=idempotent_replay,
    )


def _portfolio_inputs_for_request(
    *,
    request: DpmWavePreviewRequest,
    correlation_id: str,
    advise_authority_client: LotusAdviseAuthorityClient | None,
    risk_authority_client: LotusRiskAuthorityClient | None,
    campaign_definition_repository: DpmBulkReviewCampaignDefinitionRepository,
) -> list[dict[str, object]]:
    if request.trigger_type == "EXPLICIT_PORTFOLIO_LIST":
        return [portfolio.model_dump(mode="json") for portfolio in request.portfolios]
    if request.trigger_type == "PM_BOOK_REVIEW":
        return _resolve_pm_book_portfolios(request=request, correlation_id=correlation_id)
    if request.trigger_type == "CIO_MODEL_CHANGE":
        return _resolve_cio_model_change_portfolios(
            request=request,
            correlation_id=correlation_id,
        )
    if request.trigger_type == "RISK_EVENT":
        return _resolve_risk_event_portfolios(
            request=request,
            correlation_id=correlation_id,
            risk_authority_client=risk_authority_client,
        )
    if request.trigger_type == "TACTICAL_HOUSE_VIEW":
        return _resolve_tactical_house_view_portfolios(
            request=request,
            correlation_id=correlation_id,
            advise_authority_client=advise_authority_client,
        )
    if request.trigger_type == "BULK_REVIEW_CAMPAIGN":
        resolved_request = _request_with_campaign_definition(
            request=request,
            repository=campaign_definition_repository,
        )
        return _resolve_bulk_review_campaign_portfolios(request=resolved_request)
    return [portfolio.model_dump(mode="json") for portfolio in request.portfolios]


def _request_with_campaign_definition(
    *,
    request: DpmWavePreviewRequest,
    repository: DpmBulkReviewCampaignDefinitionRepository,
) -> DpmWavePreviewRequest:
    if request.campaign_definition_id is None and request.campaign_definition_version is None:
        return request
    if not request.campaign_definition_id or not request.campaign_definition_version:
        raise wave_service.DpmWaveValidationError(
            "BULK_REVIEW_CAMPAIGN_DEFINITION_REF_INCOMPLETE",
            "campaign_definition_id and campaign_definition_version must be supplied together.",
        )
    if request.portfolios:
        raise wave_service.DpmWaveValidationError(
            "BULK_REVIEW_CAMPAIGN_DEFINITION_REJECTS_CALLER_PORTFOLIOS",
            "Persisted campaign definitions supply the candidate portfolio set.",
        )
    definition = repository.get_definition(
        campaign_id=request.campaign_definition_id,
        campaign_version=request.campaign_definition_version,
    )
    if definition is None:
        raise wave_service.DpmWaveValidationError(
            "BULK_REVIEW_CAMPAIGN_DEFINITION_NOT_FOUND",
            "Persisted bulk-review campaign definition was not found.",
        )
    if definition.status == "RETIRED":
        raise wave_service.DpmWaveValidationError(
            "BULK_REVIEW_CAMPAIGN_DEFINITION_RETIRED",
            "Retired bulk-review campaign definitions cannot be used for new wave preview/create.",
        )
    if definition.status == "SUPERSEDED":
        raise wave_service.DpmWaveValidationError(
            "BULK_REVIEW_CAMPAIGN_DEFINITION_SUPERSEDED",
            "Superseded bulk-review campaign definitions cannot be used for new wave preview/create.",
        )
    if definition.as_of_date != request.as_of_date:
        raise wave_service.DpmWaveValidationError(
            "BULK_REVIEW_CAMPAIGN_DEFINITION_AS_OF_DATE_MISMATCH",
            "campaign definition as_of_date must match the wave request as_of_date.",
        )
    definition_ref = DpmWaveSourceRef(
        source_system="lotus-manage",
        source_type="BulkReviewCampaignDefinition",
        source_id=f"campaign-definition:{definition.campaign_id}:{definition.campaign_version}",
        source_version=definition.product_version,
        supportability_state="READY",
        content_hash=definition.content_hash,
    )
    portfolios = [
        DpmWavePortfolioInput(
            portfolio_id=candidate.portfolio_id,
            mandate_id=candidate.mandate_id,
            portfolio_manager_id=candidate.portfolio_manager_id,
            portfolio_type=candidate.portfolio_type,
            source_refs=[definition_ref, *candidate.source_refs],
        )
        for candidate in definition.candidates
    ]
    governance = (
        DpmBulkReviewCampaignGovernanceInput.model_validate(
            definition.governance.model_dump(mode="json")
        )
        if definition.governance is not None
        else request.campaign_governance
    )
    return request.model_copy(
        update={
            "trigger_id": definition.campaign_id,
            "rationale": definition.rationale,
            "portfolios": portfolios,
            "portfolio_types": definition.eligible_portfolio_types,
            "campaign_governance": governance,
        },
        deep=True,
    )


def _resolve_pm_book_portfolios(
    *,
    request: DpmWavePreviewRequest,
    correlation_id: str,
) -> list[dict[str, object]]:
    if request.portfolios:
        raise wave_service.DpmWaveValidationError(
            "PM_BOOK_REVIEW_REJECTS_CALLER_PORTFOLIOS",
            "PM_BOOK_REVIEW resolves the affected portfolio set from lotus-core.",
        )
    portfolio_manager_id = (request.portfolio_manager_id or "").strip()
    if not portfolio_manager_id:
        raise wave_service.DpmWaveValidationError(
            "PM_BOOK_REVIEW_PORTFOLIO_MANAGER_REQUIRED",
            "PM_BOOK_REVIEW requires portfolio_manager_id.",
        )
    try:
        as_of_date = date.fromisoformat(request.as_of_date)
    except ValueError as exc:
        raise wave_service.DpmWaveValidationError(
            "INVALID_AS_OF_DATE",
            "as_of_date must be an ISO date.",
        ) from exc
    portfolio_types = [value.strip().upper() for value in request.portfolio_types if value.strip()]
    if not portfolio_types:
        raise wave_service.DpmWaveValidationError(
            "PM_BOOK_REVIEW_PORTFOLIO_TYPES_REQUIRED",
            "PM_BOOK_REVIEW requires at least one portfolio type.",
        )
    try:
        membership = build_core_resolver_client().resolve_portfolio_manager_book_membership(
            portfolio_manager_id=portfolio_manager_id,
            as_of_date=as_of_date,
            tenant_id=request.tenant_id,
            booking_center_code=request.booking_center_code,
            portfolio_types=portfolio_types,
            include_inactive=False,
            correlation_id=correlation_id,
        )
    except DpmCoreResolverUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": str(exc) or "DPM_CORE_PM_BOOK_MEMBERSHIP_UNAVAILABLE"},
        ) from exc
    except DpmCoreResolverError as exc:
        raise HTTPException(
            status_code=status.HTTP_424_FAILED_DEPENDENCY,
            detail={"code": str(exc) or "DPM_CORE_PM_BOOK_MEMBERSHIP_INCOMPLETE"},
        ) from exc
    if membership.supportability.state != "READY":
        raise HTTPException(
            status_code=status.HTTP_424_FAILED_DEPENDENCY,
            detail={
                "code": membership.supportability.reason,
                "message": "PM-book membership is not source-ready.",
            },
        )
    if not membership.members:
        raise HTTPException(
            status_code=status.HTTP_424_FAILED_DEPENDENCY,
            detail={
                "code": "DPM_CORE_PM_BOOK_MEMBERSHIP_EMPTY",
                "message": "PM-book membership returned no affected portfolios.",
            },
        )
    source_id = (
        membership.snapshot_id
        or membership.source_batch_fingerprint
        or f"pm_book:{membership.portfolio_manager_id}:{membership.as_of_date.isoformat()}"
    )
    book_ref = {
        "source_system": "lotus-core",
        "source_type": "PortfolioManagerBookMembership",
        "source_id": source_id,
        "source_version": membership.product_version,
        "supportability_state": membership.supportability.state,
        "content_hash": membership.source_batch_fingerprint,
    }
    return [
        {
            "portfolio_id": member.portfolio_id,
            "source_refs": [
                book_ref,
                {
                    "source_system": "lotus-core",
                    "source_type": "PORTFOLIO_MANAGER_BOOK_MEMBER",
                    "source_id": member.source_record_id or member.portfolio_id,
                    "source_version": membership.as_of_date.isoformat(),
                    "supportability_state": "READY",
                },
            ],
        }
        for member in membership.members
    ]


def _resolve_cio_model_change_portfolios(
    *,
    request: DpmWavePreviewRequest,
    correlation_id: str,
) -> list[dict[str, object]]:
    if request.portfolios:
        raise wave_service.DpmWaveValidationError(
            "CIO_MODEL_CHANGE_REJECTS_CALLER_PORTFOLIOS",
            "CIO_MODEL_CHANGE resolves the affected portfolio set from lotus-core.",
        )
    model_portfolio_id = (request.model_portfolio_id or "").strip()
    if not model_portfolio_id:
        raise wave_service.DpmWaveValidationError(
            "CIO_MODEL_CHANGE_MODEL_PORTFOLIO_REQUIRED",
            "CIO_MODEL_CHANGE requires model_portfolio_id.",
        )
    try:
        as_of_date = date.fromisoformat(request.as_of_date)
    except ValueError as exc:
        raise wave_service.DpmWaveValidationError(
            "INVALID_AS_OF_DATE",
            "as_of_date must be an ISO date.",
        ) from exc
    try:
        cohort = build_core_resolver_client().resolve_cio_model_change_affected_cohort(
            model_portfolio_id=model_portfolio_id,
            as_of_date=as_of_date,
            tenant_id=request.tenant_id,
            booking_center_code=request.booking_center_code,
            include_inactive_mandates=False,
            correlation_id=correlation_id,
        )
    except DpmCoreResolverUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": str(exc) or "DPM_CORE_CIO_MODEL_CHANGE_COHORT_UNAVAILABLE"},
        ) from exc
    except DpmCoreResolverError as exc:
        raise HTTPException(
            status_code=status.HTTP_424_FAILED_DEPENDENCY,
            detail={"code": str(exc) or "DPM_CORE_CIO_MODEL_CHANGE_COHORT_INCOMPLETE"},
        ) from exc
    if cohort.supportability.state != "READY":
        raise HTTPException(
            status_code=status.HTTP_424_FAILED_DEPENDENCY,
            detail={
                "code": cohort.supportability.reason,
                "message": "CIO model-change affected cohort is not source-ready.",
            },
        )
    if not cohort.affected_mandates:
        raise HTTPException(
            status_code=status.HTTP_424_FAILED_DEPENDENCY,
            detail={
                "code": "DPM_CORE_CIO_MODEL_CHANGE_COHORT_EMPTY",
                "message": "CIO model-change affected cohort returned no portfolios.",
            },
        )
    source_id = (
        cohort.snapshot_id or cohort.source_batch_fingerprint or cohort.model_change_event_id
    )
    cohort_ref = {
        "source_system": "lotus-core",
        "source_type": "CioModelChangeAffectedCohort",
        "source_id": source_id,
        "source_version": cohort.product_version,
        "supportability_state": cohort.supportability.state,
        "content_hash": cohort.source_batch_fingerprint,
    }
    event_ref = {
        "source_system": "lotus-core",
        "source_type": "CIO_MODEL_CHANGE_EVENT",
        "source_id": cohort.model_change_event_id,
        "source_version": cohort.model_portfolio_version,
        "supportability_state": cohort.supportability.state,
        "content_hash": cohort.source_batch_fingerprint,
    }
    return [
        {
            "portfolio_id": mandate.portfolio_id,
            "mandate_id": mandate.mandate_id,
            "source_refs": [
                cohort_ref,
                event_ref,
                {
                    "source_system": "lotus-core",
                    "source_type": "CIO_MODEL_CHANGE_AFFECTED_MANDATE",
                    "source_id": mandate.source_record_id or mandate.mandate_id,
                    "source_version": str(mandate.binding_version),
                    "supportability_state": "READY",
                },
            ],
        }
        for mandate in cohort.affected_mandates
    ]


def _resolve_tactical_house_view_portfolios(
    *,
    request: DpmWavePreviewRequest,
    correlation_id: str,
    advise_authority_client: LotusAdviseAuthorityClient | None,
) -> list[dict[str, object]]:
    tactical_view = request.tactical_house_view
    if tactical_view is None:
        raise wave_service.DpmWaveValidationError(
            "TACTICAL_HOUSE_VIEW_REQUIRED",
            "TACTICAL_HOUSE_VIEW requires tactical_house_view source evidence.",
        )
    if not request.portfolios:
        raise wave_service.DpmWaveValidationError(
            "TACTICAL_HOUSE_VIEW_CANDIDATE_PORTFOLIOS_REQUIRED",
            "TACTICAL_HOUSE_VIEW requires source-backed candidate portfolios.",
        )
    if not tactical_view.source_refs:
        raise wave_service.DpmWaveValidationError(
            "TACTICAL_HOUSE_VIEW_SOURCE_REFS_REQUIRED",
            "TACTICAL_HOUSE_VIEW requires tactical house-view source_refs.",
        )
    if advise_authority_client is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "DPM_TACTICAL_HOUSE_VIEW_COHORT_UNAVAILABLE",
                "message": "DPM_ADVISE_BASE_URL is not configured.",
            },
        )
    try:
        as_of_date = date.fromisoformat(request.as_of_date)
    except ValueError as exc:
        raise wave_service.DpmWaveValidationError(
            "INVALID_AS_OF_DATE",
            "as_of_date must be an ISO date.",
        ) from exc
    eligible_portfolio_types = [
        value.strip().upper() for value in request.portfolio_types if value.strip()
    ]
    if not eligible_portfolio_types:
        raise wave_service.DpmWaveValidationError(
            "TACTICAL_HOUSE_VIEW_PORTFOLIO_TYPES_REQUIRED",
            "TACTICAL_HOUSE_VIEW requires at least one eligible portfolio type.",
        )

    candidate_payloads: list[dict[str, object]] = []
    for candidate in request.portfolios:
        portfolio_type = (candidate.portfolio_type or "").strip().upper()
        if not portfolio_type:
            raise wave_service.DpmWaveValidationError(
                "TACTICAL_HOUSE_VIEW_PORTFOLIO_TYPE_REQUIRED",
                "TACTICAL_HOUSE_VIEW candidate portfolios require source-owned portfolio_type.",
            )
        if candidate.discretionary_mandate is None:
            raise wave_service.DpmWaveValidationError(
                "TACTICAL_HOUSE_VIEW_DISCRETIONARY_MANDATE_REQUIRED",
                "TACTICAL_HOUSE_VIEW candidate portfolios require source-owned discretionary_mandate.",
            )
        if not candidate.source_refs:
            raise wave_service.DpmWaveValidationError(
                "TACTICAL_HOUSE_VIEW_CANDIDATE_SOURCE_REFS_REQUIRED",
                "TACTICAL_HOUSE_VIEW candidate portfolios require source_refs.",
            )
        candidate_payloads.append(
            {
                "portfolio_id": candidate.portfolio_id,
                "mandate_id": candidate.mandate_id,
                "portfolio_type": portfolio_type,
                "discretionary_mandate": candidate.discretionary_mandate,
                "current_exposure_weight": (
                    str(candidate.current_exposure_weight)
                    if candidate.current_exposure_weight is not None
                    else None
                ),
                "alignment_signal": candidate.alignment_signal,
                "source_refs": [ref.model_dump(mode="json") for ref in candidate.source_refs],
                "reason_codes": ["TACTICAL_HOUSE_VIEW_CANDIDATE_SOURCE_BACKED"],
            }
        )

    try:
        cohort = advise_authority_client.tactical_house_view_affected_cohort(
            tactical_view={
                "tactical_view_id": tactical_view.tactical_view_id,
                "tactical_view_version": tactical_view.tactical_view_version,
                "theme_id": tactical_view.theme_id,
                "as_of_date": as_of_date.isoformat(),
                "target_action": tactical_view.target_action,
                "rationale": tactical_view.rationale,
                "source_refs": [ref.model_dump(mode="json") for ref in tactical_view.source_refs],
                "reason_codes": ["TACTICAL_HOUSE_VIEW_BANK_AUTHORED"],
            },
            candidate_portfolios=candidate_payloads,
            eligible_portfolio_types=eligible_portfolio_types,
            min_exposure_weight=(
                Decimal(str(request.min_tactical_exposure_weight))
                if request.min_tactical_exposure_weight is not None
                else None
            ),
            correlation_id=correlation_id,
        )
    except LotusAdviseAuthorityUnavailableError as exc:
        error_code = str(exc) or "DPM_TACTICAL_HOUSE_VIEW_COHORT_UNAVAILABLE"
        status_code = (
            status.HTTP_424_FAILED_DEPENDENCY
            if error_code == "LOTUS_ADVISE_TACTICAL_HOUSE_VIEW_COHORT_REJECTED"
            else status.HTTP_503_SERVICE_UNAVAILABLE
        )
        raise HTTPException(status_code=status_code, detail={"code": error_code}) from exc

    if cohort.supportability_state != "READY":
        raise HTTPException(
            status_code=status.HTTP_424_FAILED_DEPENDENCY,
            detail={
                "code": "DPM_TACTICAL_HOUSE_VIEW_COHORT_EMPTY"
                if cohort.supportability_state == "EMPTY"
                else "DPM_TACTICAL_HOUSE_VIEW_COHORT_INCOMPLETE",
                "message": "Tactical house-view affected cohort is not source-ready.",
                "reason_codes": list(cohort.supportability_reason_codes),
            },
        )
    if not cohort.affected_portfolios:
        raise HTTPException(
            status_code=status.HTTP_424_FAILED_DEPENDENCY,
            detail={
                "code": "DPM_TACTICAL_HOUSE_VIEW_COHORT_EMPTY",
                "message": "Tactical house-view cohort returned no affected portfolios.",
            },
        )

    cohort_ref = {
        "source_system": cohort.source_service,
        "source_type": cohort.product_name,
        "source_id": cohort.cohort_id,
        "source_version": cohort.product_version,
        "supportability_state": cohort.supportability_state,
        "content_hash": cohort.content_hash,
    }
    house_view_ref = {
        "source_system": cohort.source_service,
        "source_type": "TACTICAL_HOUSE_VIEW",
        "source_id": cohort.tactical_view_id,
        "source_version": cohort.tactical_view_version,
        "supportability_state": cohort.supportability_state,
        "content_hash": cohort.content_hash,
    }
    return [
        {
            "portfolio_id": affected.portfolio_id,
            "mandate_id": affected.mandate_id,
            "source_refs": [
                cohort_ref,
                house_view_ref,
                {
                    "source_system": cohort.source_service,
                    "source_type": "TACTICAL_HOUSE_VIEW_AFFECTED_PORTFOLIO",
                    "source_id": f"{cohort.cohort_id}:{affected.portfolio_id}",
                    "source_version": cohort.product_version,
                    "supportability_state": cohort.supportability_state,
                    "content_hash": cohort.content_hash,
                },
                *affected.source_refs,
            ],
            "diagnostics": {
                "source_owner": cohort.source_service,
                "source_product": f"{cohort.product_name}:{cohort.product_version}",
                "tactical_view_id": cohort.tactical_view_id,
                "tactical_view_version": cohort.tactical_view_version,
                "theme_id": cohort.theme_id,
                "target_action": cohort.target_action,
                "cohort_supportability_state": cohort.supportability_state,
                "cohort_reason_codes": list(cohort.supportability_reason_codes),
                "inclusion_reason_codes": list(affected.inclusion_reason_codes),
            },
        }
        for affected in cohort.affected_portfolios
    ]


def _resolve_risk_event_portfolios(
    *,
    request: DpmWavePreviewRequest,
    correlation_id: str,
    risk_authority_client: LotusRiskAuthorityClient | None,
) -> list[dict[str, object]]:
    risk_event_id = (request.risk_event_id or "").strip()
    if not risk_event_id:
        raise wave_service.DpmWaveValidationError(
            "RISK_EVENT_ID_REQUIRED",
            "RISK_EVENT requires risk_event_id.",
        )
    if not request.portfolios:
        raise wave_service.DpmWaveValidationError(
            "RISK_EVENT_CANDIDATE_PORTFOLIOS_REQUIRED",
            "RISK_EVENT requires candidate portfolios with source-supplied exposure weights.",
        )
    try:
        as_of_date = date.fromisoformat(request.as_of_date)
    except ValueError as exc:
        raise wave_service.DpmWaveValidationError(
            "INVALID_AS_OF_DATE",
            "as_of_date must be an ISO date.",
        ) from exc
    if risk_authority_client is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "DPM_RISK_EVENT_COHORT_UNAVAILABLE",
                "message": "DPM_RISK_BASE_URL is not configured.",
            },
        )

    candidate_by_portfolio_id: dict[str, DpmWavePortfolioInput] = {}
    risk_portfolios: list[dict[str, object]] = []
    for candidate in request.portfolios:
        exposure_weights = {
            bucket.strip().upper(): weight
            for bucket, weight in candidate.exposure_weights.items()
            if bucket.strip()
        }
        if not exposure_weights:
            raise wave_service.DpmWaveValidationError(
                "RISK_EVENT_EXPOSURE_WEIGHTS_REQUIRED",
                "RISK_EVENT candidate portfolios require source-supplied exposure_weights.",
            )
        if any(weight < 0 for weight in exposure_weights.values()):
            raise wave_service.DpmWaveValidationError(
                "RISK_EVENT_EXPOSURE_WEIGHTS_INVALID",
                "RISK_EVENT exposure_weights must be non-negative.",
            )
        candidate_by_portfolio_id[candidate.portfolio_id] = candidate
        risk_portfolios.append(
            {
                "portfolio_id": candidate.portfolio_id,
                "mandate_id": candidate.mandate_id,
                "portfolio_manager_id": candidate.portfolio_manager_id,
                "exposure_weights": exposure_weights,
            }
        )

    try:
        cohort = risk_authority_client.risk_event_affected_cohort(
            risk_event_id=risk_event_id,
            as_of_date=as_of_date,
            portfolios=risk_portfolios,
            minimum_impact_score=Decimal(str(request.minimum_impact_score)),
            correlation_id=correlation_id,
        )
    except LotusRiskAuthorityUnavailableError as exc:
        error_code = str(exc) or "DPM_RISK_EVENT_COHORT_UNAVAILABLE"
        status_code = (
            status.HTTP_424_FAILED_DEPENDENCY
            if error_code == "LOTUS_RISK_EVENT_COHORT_REJECTED"
            else status.HTTP_503_SERVICE_UNAVAILABLE
        )
        raise HTTPException(
            status_code=status_code,
            detail={"code": error_code},
        ) from exc

    if cohort.calculation_supportability != "ready":
        raise HTTPException(
            status_code=status.HTTP_424_FAILED_DEPENDENCY,
            detail={
                "code": "DPM_RISK_EVENT_COHORT_INCOMPLETE",
                "message": "Risk-event affected cohort is not source-ready.",
                "reason_codes": list(cohort.reason_codes),
            },
        )
    if not cohort.affected_portfolios:
        raise HTTPException(
            status_code=status.HTTP_424_FAILED_DEPENDENCY,
            detail={
                "code": "DPM_RISK_EVENT_COHORT_EMPTY",
                "message": "Risk-event affected cohort returned no affected portfolios.",
            },
        )

    source_id = cohort.cohort_id or cohort.request_fingerprint or risk_event_id
    cohort_ref = {
        "source_system": cohort.source_service,
        "source_type": cohort.product_name,
        "source_id": source_id,
        "source_version": cohort.product_version,
        "supportability_state": cohort.calculation_supportability.upper(),
        "content_hash": cohort.request_fingerprint,
    }
    event_ref = {
        "source_system": cohort.source_service,
        "source_type": "RISK_EVENT",
        "source_id": cohort.risk_event_id,
        "source_version": cohort.product_version,
        "supportability_state": cohort.calculation_supportability.upper(),
        "content_hash": cohort.request_fingerprint,
    }
    portfolios: list[dict[str, object]] = []
    for affected in cohort.affected_portfolios:
        matched_candidate = candidate_by_portfolio_id.get(affected.portfolio_id)
        candidate_refs = matched_candidate.source_refs if matched_candidate is not None else []
        portfolios.append(
            {
                "portfolio_id": affected.portfolio_id,
                "mandate_id": affected.mandate_id,
                "source_refs": [
                    cohort_ref,
                    event_ref,
                    {
                        "source_system": cohort.source_service,
                        "source_type": "RISK_EVENT_AFFECTED_PORTFOLIO",
                        "source_id": affected.source_ref,
                        "source_version": cohort.product_version,
                        "supportability_state": cohort.calculation_supportability.upper(),
                        "content_hash": cohort.request_fingerprint,
                    },
                    *[ref.model_dump(mode="json") for ref in candidate_refs],
                ],
            }
        )
    return portfolios


def _resolve_bulk_review_campaign_portfolios(
    *,
    request: DpmWavePreviewRequest,
) -> list[dict[str, object]]:
    if not request.portfolios:
        raise wave_service.DpmWaveValidationError(
            "BULK_REVIEW_CAMPAIGN_CANDIDATE_PORTFOLIOS_REQUIRED",
            "BULK_REVIEW_CAMPAIGN requires source-backed candidate portfolios.",
        )
    try:
        campaign_as_of_date = date.fromisoformat(request.as_of_date)
    except ValueError as exc:
        raise wave_service.DpmWaveValidationError(
            "INVALID_AS_OF_DATE",
            "as_of_date must be an ISO date.",
        ) from exc
    governance_diagnostics, governance_refs = _resolve_bulk_review_campaign_governance(
        request=request,
        campaign_as_of_date=campaign_as_of_date,
    )
    eligible_portfolio_types = {
        value.strip().upper() for value in request.portfolio_types if value.strip()
    }
    if not eligible_portfolio_types:
        raise wave_service.DpmWaveValidationError(
            "BULK_REVIEW_CAMPAIGN_PORTFOLIO_TYPES_REQUIRED",
            "BULK_REVIEW_CAMPAIGN requires at least one eligible portfolio type.",
        )

    included_candidates: list[DpmWavePortfolioInput] = []
    excluded_count = 0
    for candidate in request.portfolios:
        portfolio_type = (candidate.portfolio_type or "").strip().upper()
        if not portfolio_type:
            raise wave_service.DpmWaveValidationError(
                "BULK_REVIEW_CAMPAIGN_PORTFOLIO_TYPE_REQUIRED",
                "BULK_REVIEW_CAMPAIGN candidate portfolios require source-owned portfolio_type.",
            )
        if portfolio_type not in eligible_portfolio_types:
            excluded_count += 1
            continue
        if not candidate.source_refs:
            raise wave_service.DpmWaveValidationError(
                "BULK_REVIEW_CAMPAIGN_SOURCE_REFS_REQUIRED",
                "BULK_REVIEW_CAMPAIGN candidate portfolios require source_refs.",
            )
        included_candidates.append(candidate)

    if not included_candidates:
        raise HTTPException(
            status_code=status.HTTP_424_FAILED_DEPENDENCY,
            detail={
                "code": "BULK_REVIEW_CAMPAIGN_MEMBERSHIP_EMPTY",
                "message": "Bulk-review campaign membership returned no eligible DPM portfolios.",
            },
        )

    membership_hash = _campaign_membership_hash(
        trigger_id=request.trigger_id,
        as_of_date=campaign_as_of_date,
        portfolio_types=sorted(eligible_portfolio_types),
        portfolios=[candidate.model_dump(mode="json") for candidate in included_candidates],
    )
    membership_ref = {
        "source_system": "lotus-manage",
        "source_type": "BulkReviewCampaignMembership",
        "source_id": f"campaign:{request.trigger_id}:{campaign_as_of_date.isoformat()}",
        "source_version": "v1",
        "supportability_state": "READY",
        "content_hash": membership_hash,
    }
    return [
        {
            "portfolio_id": candidate.portfolio_id,
            "mandate_id": candidate.mandate_id,
            "source_refs": [
                membership_ref,
                *governance_refs,
                {
                    "source_system": "lotus-manage",
                    "source_type": "BULK_REVIEW_CAMPAIGN_MEMBER",
                    "source_id": f"{request.trigger_id}:{candidate.portfolio_id}",
                    "source_version": campaign_as_of_date.isoformat(),
                    "supportability_state": "READY",
                    "content_hash": membership_hash,
                },
                *[ref.model_dump(mode="json") for ref in candidate.source_refs],
            ],
            "diagnostics": {
                "source_owner": "lotus-manage",
                "source_product": "BulkReviewCampaignMembership:v1",
                "campaign_id": request.trigger_id,
                "campaign_as_of_date": campaign_as_of_date.isoformat(),
                "portfolio_type": candidate.portfolio_type.strip().upper()
                if candidate.portfolio_type
                else None,
                "eligible_portfolio_types": sorted(eligible_portfolio_types),
                "excluded_candidate_count": excluded_count,
                "membership_supportability_state": "READY",
                **governance_diagnostics,
            },
        }
        for candidate in included_candidates
    ]


def _resolve_bulk_review_campaign_governance(
    *,
    request: DpmWavePreviewRequest,
    campaign_as_of_date: date,
) -> tuple[dict[str, object], list[dict[str, object]]]:
    governance = request.campaign_governance
    if governance is None:
        return (
            {
                "campaign_governance_status": "NOT_SUPPLIED",
                "campaign_access_purpose": None,
                "campaign_expiry_state": "NOT_SUPPLIED",
                "campaign_actor_entitlement_state": "NOT_SUPPLIED",
            },
            [],
        )

    approval_fields = [governance.approval_ref, governance.approved_by, governance.approved_at]
    supplied_approval_fields = [value for value in approval_fields if value]
    if supplied_approval_fields and len(supplied_approval_fields) != len(approval_fields):
        raise wave_service.DpmWaveValidationError(
            "BULK_REVIEW_CAMPAIGN_APPROVAL_EVIDENCE_INCOMPLETE",
            "Bulk-review campaign approval evidence requires approval_ref, approved_by, and approved_at.",
        )

    expiry_state = "NOT_SUPPLIED"
    if governance.expires_on:
        try:
            expires_on = date.fromisoformat(governance.expires_on)
        except ValueError as exc:
            raise wave_service.DpmWaveValidationError(
                "BULK_REVIEW_CAMPAIGN_EXPIRY_DATE_INVALID",
                "campaign_governance.expires_on must be an ISO date.",
            ) from exc
        if expires_on < campaign_as_of_date:
            raise wave_service.DpmWaveValidationError(
                "BULK_REVIEW_CAMPAIGN_EXPIRED",
                "Bulk-review campaign governance is expired for the requested as_of_date.",
            )
        expiry_state = "ACTIVE"

    entitled_actor_ids = {actor.strip() for actor in governance.entitled_actor_ids if actor.strip()}
    actor_entitlement_state = "NOT_SUPPLIED"
    if entitled_actor_ids:
        actor_entitlement_state = "AUTHORIZED"
        if request.actor_id not in entitled_actor_ids:
            raise wave_service.DpmWaveValidationError(
                "BULK_REVIEW_CAMPAIGN_ACTOR_NOT_ENTITLED",
                "actor_id is not entitled for this bulk-review campaign.",
            )

    governance_hash = _campaign_governance_hash(
        trigger_id=request.trigger_id,
        actor_id=request.actor_id,
        governance=governance.model_dump(mode="json"),
    )
    governance_refs = [
        {
            "source_system": "lotus-manage",
            "source_type": "BulkReviewCampaignGovernance",
            "source_id": f"campaign-governance:{request.trigger_id}",
            "source_version": governance.approved_at or campaign_as_of_date.isoformat(),
            "supportability_state": "READY",
            "content_hash": governance_hash,
        },
        *[ref.model_dump(mode="json") for ref in governance.source_refs],
    ]
    return (
        {
            "campaign_governance_status": "APPROVED"
            if len(supplied_approval_fields) == len(approval_fields)
            else "NOT_SUPPLIED",
            "campaign_approval_ref": governance.approval_ref,
            "campaign_approved_by": governance.approved_by,
            "campaign_approved_at": governance.approved_at,
            "campaign_access_purpose": governance.access_purpose,
            "campaign_expiry_state": expiry_state,
            "campaign_expires_on": governance.expires_on,
            "campaign_actor_entitlement_state": actor_entitlement_state,
        },
        governance_refs,
    )


def _campaign_governance_hash(
    *,
    trigger_id: str,
    actor_id: str,
    governance: dict[str, object],
) -> str:
    payload = {
        "product_name": "BulkReviewCampaignGovernance",
        "product_version": "v1",
        "trigger_id": trigger_id,
        "actor_id": actor_id,
        "governance": governance,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return f"sha256:{hashlib.sha256(canonical.encode()).hexdigest()}"


def _campaign_membership_hash(
    *,
    trigger_id: str,
    as_of_date: date,
    portfolio_types: list[str],
    portfolios: list[dict[str, object]],
) -> str:
    payload = {
        "product_name": "BulkReviewCampaignMembership",
        "product_version": "v1",
        "trigger_id": trigger_id,
        "as_of_date": as_of_date.isoformat(),
        "portfolio_types": portfolio_types,
        "portfolios": portfolios,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return f"sha256:{hashlib.sha256(canonical.encode()).hexdigest()}"


@router.put(
    "/campaign-definitions/{campaign_id}/versions/{campaign_version}",
    response_model=DpmBulkReviewCampaignDefinition,
    status_code=status.HTTP_200_OK,
    summary="Persist bulk-review campaign definition",
    description=(
        "Persists an immutable Manage-owned `BulkReviewCampaignDefinition:v1` over a bounded, "
        "source-backed candidate portfolio set. This endpoint does not discover the global book, "
        "own source facts, run maker-checker workflow, expose downstream UI, or claim OMS "
        "execution."
    ),
)
def put_bulk_review_campaign_definition(
    campaign_id: str,
    campaign_version: str,
    request: DpmBulkReviewCampaignDefinitionRequest,
    repository: DpmBulkReviewCampaignDefinitionRepository = Depends(
        get_campaign_definition_repository
    ),
) -> DpmBulkReviewCampaignDefinition:
    try:
        definition = DpmBulkReviewCampaignDefinition(
            campaign_id=campaign_id,
            campaign_version=campaign_version,
            display_name=request.display_name,
            status=request.status,
            as_of_date=request.as_of_date,
            rationale=request.rationale,
            eligible_portfolio_types=request.eligible_portfolio_types,
            candidates=request.candidates,
            governance=request.governance,
            source_refs=request.source_refs,
            created_by=request.created_by,
            correlation_id=request.correlation_id,
        )
        repository.save_definition(definition=definition)
    except DpmBulkReviewCampaignDefinitionConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": str(exc), "message": str(exc)},
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"code": str(exc), "message": str(exc)},
        ) from exc
    return definition


@router.get(
    "/campaign-definitions",
    response_model=DpmBulkReviewCampaignDefinitionPage,
    status_code=status.HTTP_200_OK,
    summary="List bulk-review campaign definitions",
    description="Lists immutable Manage-owned bulk-review campaign definitions.",
)
def list_bulk_review_campaign_definitions(
    campaign_id: str | None = Query(default=None),
    campaign_status: Literal["ACTIVE", "RETIRED", "SUPERSEDED"] | None = Query(default=None),
    as_of_date: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    repository: DpmBulkReviewCampaignDefinitionRepository = Depends(
        get_campaign_definition_repository
    ),
) -> DpmBulkReviewCampaignDefinitionPage:
    items = repository.list_definitions(
        campaign_id=campaign_id,
        status=campaign_status,
        as_of_date=as_of_date,
        limit=limit,
        offset=offset,
    )
    return DpmBulkReviewCampaignDefinitionPage(
        items=items,
        limit=limit,
        offset=offset,
        count=len(items),
    )


@router.post(
    "/campaign-definitions/{campaign_id}/versions/{campaign_version}/retire",
    response_model=DpmBulkReviewCampaignDefinition,
    status_code=status.HTTP_200_OK,
    summary="Retire bulk-review campaign definition",
    description=(
        "Retires a persisted Manage-owned `BulkReviewCampaignDefinition:v1` so it remains "
        "auditable but can no longer be used for new `BULK_REVIEW_CAMPAIGN` preview/create "
        "requests. This lifecycle action does not change the source-backed candidate set, "
        "discover a global portfolio universe, run maker-checker workflow, or claim OMS execution."
    ),
)
def retire_bulk_review_campaign_definition(
    campaign_id: str,
    campaign_version: str,
    request: DpmBulkReviewCampaignDefinitionRetirementRequest,
    repository: DpmBulkReviewCampaignDefinitionRepository = Depends(
        get_campaign_definition_repository
    ),
) -> DpmBulkReviewCampaignDefinition:
    try:
        retired = retire_campaign_definition(
            repository=repository,
            campaign_id=campaign_id,
            campaign_version=campaign_version,
            retired_by=request.retired_by,
            retirement_reason=request.retirement_reason,
            correlation_id=request.correlation_id,
        )
    except DpmBulkReviewCampaignDefinitionConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": str(exc), "message": str(exc)},
        ) from exc
    except DpmBulkReviewCampaignDefinitionLifecycleError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": exc.code, "message": exc.message},
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"code": str(exc), "message": str(exc)},
        ) from exc
    if retired is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "BULK_REVIEW_CAMPAIGN_DEFINITION_NOT_FOUND",
                "message": "Bulk-review campaign definition was not found.",
            },
        )
    return retired


@router.post(
    "/campaign-definitions/{campaign_id}/versions/{campaign_version}/supersede",
    response_model=DpmBulkReviewCampaignDefinition,
    status_code=status.HTTP_200_OK,
    summary="Supersede bulk-review campaign definition",
    description=(
        "Supersedes a persisted Manage-owned `BulkReviewCampaignDefinition:v1` with an already "
        "persisted ACTIVE replacement version for the same campaign id. Superseded definitions "
        "remain auditable but cannot be used for new `BULK_REVIEW_CAMPAIGN` preview/create "
        "requests. This lifecycle action does not discover the global portfolio universe, "
        "recalculate source facts, run maker-checker workflow, or claim OMS execution."
    ),
)
def supersede_bulk_review_campaign_definition(
    campaign_id: str,
    campaign_version: str,
    request: DpmBulkReviewCampaignDefinitionSupersessionRequest,
    repository: DpmBulkReviewCampaignDefinitionRepository = Depends(
        get_campaign_definition_repository
    ),
) -> DpmBulkReviewCampaignDefinition:
    try:
        superseded = supersede_campaign_definition(
            repository=repository,
            campaign_id=campaign_id,
            campaign_version=campaign_version,
            replacement_version=request.superseded_by_campaign_version,
            superseded_by=request.superseded_by,
            supersession_reason=request.supersession_reason,
            correlation_id=request.correlation_id,
        )
    except DpmBulkReviewCampaignDefinitionConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": str(exc), "message": str(exc)},
        ) from exc
    except DpmBulkReviewCampaignDefinitionLifecycleError as exc:
        status_code = (
            status.HTTP_404_NOT_FOUND
            if exc.code == "BULK_REVIEW_CAMPAIGN_SUPERSESSION_REPLACEMENT_NOT_FOUND"
            else status.HTTP_422_UNPROCESSABLE_CONTENT
            if exc.code == "BULK_REVIEW_CAMPAIGN_SUPERSESSION_REPLACEMENT_VERSION_INVALID"
            else status.HTTP_409_CONFLICT
        )
        raise HTTPException(
            status_code=status_code,
            detail={"code": exc.code, "message": exc.message},
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"code": str(exc), "message": str(exc)},
        ) from exc
    if superseded is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "BULK_REVIEW_CAMPAIGN_DEFINITION_NOT_FOUND",
                "message": "Bulk-review campaign definition was not found.",
            },
        )
    return superseded


@router.get(
    "/campaign-discovery",
    response_model=DpmBulkReviewCampaignDiscoveryPage,
    status_code=status.HTTP_200_OK,
    summary="Discover persisted bulk-review campaigns",
    description=(
        "Discovers persisted Manage-owned `BulkReviewCampaignDefinition:v1` records as a bounded "
        "front-office operating read model. This endpoint summarizes campaign identity, governance "
        "posture, expiry posture, source-ref count, and source-backed candidate counts. It does not "
        "discover the global portfolio universe, calculate source facts, run maker-checker workflow, "
        "or claim OMS execution."
    ),
)
def discover_bulk_review_campaigns(
    campaign_id: str | None = Query(default=None),
    campaign_status: Literal["ACTIVE", "RETIRED", "SUPERSEDED"] | None = Query(default="ACTIVE"),
    as_of_date: str | None = Query(default=None),
    active_on: str | None = Query(
        default=None,
        description=(
            "Optional ISO date used to classify and filter campaign expiry posture. When supplied "
            "with include_expired=false, expired campaigns are omitted."
        ),
    ),
    include_expired: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    repository: DpmBulkReviewCampaignDefinitionRepository = Depends(
        get_campaign_definition_repository
    ),
) -> DpmBulkReviewCampaignDiscoveryPage:
    active_on_date = _parse_optional_campaign_discovery_date(
        value=active_on,
        field_name="active_on",
    )
    definitions = repository.list_definitions(
        campaign_id=campaign_id,
        status=campaign_status,
        as_of_date=as_of_date,
        limit=limit,
        offset=offset,
    )
    items = [
        build_bulk_review_campaign_discovery_item(definition=definition, active_on=active_on_date)
        for definition in definitions
    ]
    if active_on_date is not None and not include_expired:
        items = [item for item in items if item.expiry_state != "EXPIRED"]
    return DpmBulkReviewCampaignDiscoveryPage(
        items=items,
        limit=limit,
        offset=offset,
        count=len(items),
    )


@router.get(
    "/campaign-definitions/{campaign_id}/versions/{campaign_version}",
    response_model=DpmBulkReviewCampaignDefinition,
    status_code=status.HTTP_200_OK,
    summary="Get bulk-review campaign definition",
    description="Retrieves one immutable Manage-owned bulk-review campaign definition.",
)
def get_bulk_review_campaign_definition(
    campaign_id: str,
    campaign_version: str,
    repository: DpmBulkReviewCampaignDefinitionRepository = Depends(
        get_campaign_definition_repository
    ),
) -> DpmBulkReviewCampaignDefinition:
    definition = repository.get_definition(
        campaign_id=campaign_id,
        campaign_version=campaign_version,
    )
    if definition is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "BULK_REVIEW_CAMPAIGN_DEFINITION_NOT_FOUND",
                "message": "Bulk-review campaign definition was not found.",
            },
        )
    return definition


@router.get(
    "/campaign-definitions/{campaign_id}/versions/{campaign_version}/lifecycle-events",
    response_model=DpmBulkReviewCampaignDefinitionLifecycleEventPage,
    status_code=status.HTTP_200_OK,
    summary="List bulk-review campaign definition lifecycle events",
    description=(
        "Projects bounded lifecycle events for one persisted Manage-owned "
        "`BulkReviewCampaignDefinition:v1`. Events are derived from the immutable definition "
        "record and show create, retire, and supersede posture without discovering the global "
        "portfolio universe, recalculating campaign membership, running maker-checker workflow, "
        "or claiming OMS execution."
    ),
)
def list_bulk_review_campaign_definition_lifecycle_events(
    campaign_id: str,
    campaign_version: str,
    repository: DpmBulkReviewCampaignDefinitionRepository = Depends(
        get_campaign_definition_repository
    ),
) -> DpmBulkReviewCampaignDefinitionLifecycleEventPage:
    definition = repository.get_definition(
        campaign_id=campaign_id,
        campaign_version=campaign_version,
    )
    if definition is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "BULK_REVIEW_CAMPAIGN_DEFINITION_NOT_FOUND",
                "message": "Bulk-review campaign definition was not found.",
            },
        )
    return build_bulk_review_campaign_definition_lifecycle_events(definition=definition)


@router.get(
    "/campaign-definitions/{campaign_id}/versions/{campaign_version}/preview-readiness",
    response_model=DpmBulkReviewCampaignDefinitionPreviewReadiness,
    status_code=status.HTTP_200_OK,
    summary="Check bulk-review campaign definition preview readiness",
    description=(
        "Evaluates whether one persisted Manage-owned `BulkReviewCampaignDefinition:v1` can be "
        "used for new `BULK_REVIEW_CAMPAIGN` preview/create. The response is a bounded "
        "fail-closed supportability check over lifecycle status, as-of date, source-backed "
        "candidate eligibility, approval evidence, expiry, and optional actor entitlement. It "
        "does not create a wave, discover the global portfolio universe, recalculate membership, "
        "run maker-checker workflow, approve trades, or claim OMS execution."
    ),
)
def get_bulk_review_campaign_definition_preview_readiness(
    campaign_id: str,
    campaign_version: str,
    requested_as_of_date: str = Query(
        description="ISO date that the future wave preview/create request would use.",
        examples=["2026-05-10"],
    ),
    actor_id: str | None = Query(
        default=None,
        description="Optional actor id to evaluate against campaign entitlement evidence.",
    ),
    repository: DpmBulkReviewCampaignDefinitionRepository = Depends(
        get_campaign_definition_repository
    ),
) -> DpmBulkReviewCampaignDefinitionPreviewReadiness:
    definition = repository.get_definition(
        campaign_id=campaign_id,
        campaign_version=campaign_version,
    )
    if definition is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "BULK_REVIEW_CAMPAIGN_DEFINITION_NOT_FOUND",
                "message": "Bulk-review campaign definition was not found.",
            },
        )
    return build_bulk_review_campaign_definition_preview_readiness(
        definition=definition,
        requested_as_of_date=requested_as_of_date,
        actor_id=actor_id,
    )


@router.get(
    "/campaign-definitions/{campaign_id}/versions/{campaign_version}/launch-package",
    response_model=DpmBulkReviewCampaignDefinitionLaunchPackage,
    status_code=status.HTTP_200_OK,
    summary="Build bulk-review campaign definition launch package",
    description=(
        "Builds an operator launch package for one persisted Manage-owned "
        "`BulkReviewCampaignDefinition:v1`. The package contains fail-closed preview readiness, "
        "a bounded preview/create request draft, idempotency and correlation headers, and explicit "
        "operating boundaries for downstream consumers. It does not create a wave, discover the "
        "global portfolio universe, recalculate membership, run maker-checker workflow, approve "
        "trades, or claim OMS execution."
    ),
)
def get_bulk_review_campaign_definition_launch_package(
    campaign_id: str,
    campaign_version: str,
    requested_as_of_date: str = Query(
        description="ISO date that the future wave preview/create request would use.",
        examples=["2026-05-10"],
    ),
    actor_id: str = Query(
        description="Actor id to place in the preview/create request draft.",
        examples=["pm_001"],
    ),
    correlation_id: str | None = Query(
        default=None,
        description="Optional correlation id to carry into the create header draft.",
    ),
    repository: DpmBulkReviewCampaignDefinitionRepository = Depends(
        get_campaign_definition_repository
    ),
) -> DpmBulkReviewCampaignDefinitionLaunchPackage:
    definition = repository.get_definition(
        campaign_id=campaign_id,
        campaign_version=campaign_version,
    )
    if definition is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "BULK_REVIEW_CAMPAIGN_DEFINITION_NOT_FOUND",
                "message": "Bulk-review campaign definition was not found.",
            },
        )
    return build_bulk_review_campaign_definition_launch_package(
        definition=definition,
        requested_as_of_date=requested_as_of_date,
        actor_id=actor_id,
        correlation_id=correlation_id,
    )


@router.post(
    "/campaign-definitions/{campaign_id}/versions/{campaign_version}/launch",
    response_model=DpmWaveResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Launch bulk-review campaign definition",
    description=(
        "Creates a durable `BULK_REVIEW_CAMPAIGN` wave from one persisted Manage-owned "
        "`BulkReviewCampaignDefinition:v1` only when its launch package is ready. The endpoint "
        "uses the persisted source-backed candidate set and deterministic launch idempotency key; "
        "it does not discover the global portfolio universe, recalculate membership, run "
        "maker-checker workflow, approve trades, route orders, or claim OMS execution."
    ),
)
def launch_bulk_review_campaign_definition(
    campaign_id: str,
    campaign_version: str,
    request: DpmBulkReviewCampaignDefinitionLaunchRequest,
    mandate_repository: DpmMandateRepository = Depends(get_mandate_repository),
    wave_repository: DpmWaveRepository = Depends(get_wave_repository),
    campaign_definition_repository: DpmBulkReviewCampaignDefinitionRepository = Depends(
        get_campaign_definition_repository
    ),
) -> DpmWaveResponse:
    definition = campaign_definition_repository.get_definition(
        campaign_id=campaign_id,
        campaign_version=campaign_version,
    )
    if definition is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "BULK_REVIEW_CAMPAIGN_DEFINITION_NOT_FOUND",
                "message": "Bulk-review campaign definition was not found.",
            },
        )
    launch_package = build_bulk_review_campaign_definition_launch_package(
        definition=definition,
        requested_as_of_date=request.requested_as_of_date,
        actor_id=request.actor_id,
        correlation_id=request.correlation_id,
    )
    if (
        launch_package.launch_state != "READY"
        or not launch_package.readiness.preview_create_allowed
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "BULK_REVIEW_CAMPAIGN_DEFINITION_LAUNCH_BLOCKED",
                "message": "Bulk-review campaign definition is not ready for durable launch.",
                "reason_codes": launch_package.reason_codes,
                "readiness": launch_package.readiness.model_dump(mode="json"),
            },
        )
    wave_request = DpmWavePreviewRequest.model_validate(
        launch_package.create_request.model_dump(mode="json")
    )
    try:
        portfolios = _portfolio_inputs_for_request(
            request=wave_request,
            correlation_id=launch_package.correlation_id,
            advise_authority_client=None,
            risk_authority_client=None,
            campaign_definition_repository=campaign_definition_repository,
        )
        wave, replay = wave_service.create_wave(
            trigger_type=wave_request.trigger_type,
            trigger_id=wave_request.trigger_id,
            rationale=wave_request.rationale,
            as_of_date=wave_request.as_of_date,
            actor_id=wave_request.actor_id,
            correlation_id=launch_package.correlation_id,
            portfolios=portfolios,
            idempotency_key=launch_package.create_headers["Idempotency-Key"],
            mandate_repository=mandate_repository,
            wave_repository=wave_repository,
        )
        launched_definition = record_bulk_review_campaign_definition_launch(
            definition=definition,
            wave_id=wave.wave_id,
            launched_by=wave_request.actor_id,
            requested_as_of_date=wave_request.as_of_date,
            correlation_id=launch_package.correlation_id,
            idempotency_key=launch_package.create_headers["Idempotency-Key"],
        )
        if launched_definition.content_hash != definition.content_hash:
            campaign_definition_repository.record_definition_launch(definition=launched_definition)
    except wave_service.DpmWaveValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"code": exc.code, "message": exc.message},
        ) from exc
    except DpmBulkReviewCampaignDefinitionConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": str(exc),
                "message": "Bulk-review campaign definition launch audit could not be recorded.",
            },
        ) from exc
    return _wave_response(wave=wave, durable=True, idempotent_replay=replay)


def _parse_optional_campaign_discovery_date(
    *,
    value: str | None,
    field_name: str,
) -> date | None:
    if value is None:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "BULK_REVIEW_CAMPAIGN_DISCOVERY_DATE_INVALID",
                "message": f"{field_name} must be an ISO date.",
            },
        ) from exc


@router.post(
    "/preview",
    response_model=DpmWaveResponse,
    status_code=status.HTTP_200_OK,
    summary="Preview an affected-portfolio rebalance wave",
    description=(
        "Builds a non-durable RFC-0041 affected-portfolio wave preview. "
        "`EXPLICIT_PORTFOLIO_LIST` preserves source refs from the request or existing mandate "
        "digital twins. `PM_BOOK_REVIEW` resolves the cohort from the lotus-core "
        "`PortfolioManagerBookMembership:v1` source product. `CIO_MODEL_CHANGE` resolves the "
        "cohort from lotus-core `CioModelChangeAffectedCohort:v1`. `RISK_EVENT` evaluates the "
        "candidate set through lotus-risk `RiskEventAffectedCohort:v1` and preserves source-owned "
        "membership evidence. `TACTICAL_HOUSE_VIEW` evaluates the candidate set through "
        "lotus-advise `TacticalHouseViewAffectedCohort:v1` and preserves source-owned "
        "house-view/candidate evidence. `BULK_REVIEW_CAMPAIGN` builds the Manage-owned "
        "`BulkReviewCampaignMembership:v1` envelope from source-backed candidate portfolios and "
        "DPM portfolio-type filters. Unsupported trigger types remain blocked; the endpoint does "
        "not recompute house-view, holdings, risk, performance, simulation, approval, staging, or "
        "operations handoff."
    ),
    responses={
        200: {
            "description": "Non-durable wave preview with explicit candidate and blocked states.",
            "content": {"application/json": {"example": WAVE_EXAMPLE}},
        },
        422: {
            "description": "Unsupported trigger, missing source evidence, or invalid request.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": {
                            "code": "TACTICAL_HOUSE_VIEW_REQUIRED",
                            "message": "TACTICAL_HOUSE_VIEW requires tactical_house_view source evidence.",
                        }
                    }
                }
            },
        },
    },
)
def preview_wave(
    request: DpmWavePreviewRequest,
    x_correlation_id: Annotated[
        str | None,
        Header(
            description="Optional correlation id for supportability.", examples=["corr-wave-001"]
        ),
    ] = None,
    mandate_repository: DpmMandateRepository = Depends(get_mandate_repository),
    advise_authority_client: LotusAdviseAuthorityClient | None = Depends(
        get_advise_authority_client
    ),
    risk_authority_client: LotusRiskAuthorityClient | None = Depends(get_risk_authority_client),
    campaign_definition_repository: DpmBulkReviewCampaignDefinitionRepository = Depends(
        get_campaign_definition_repository
    ),
) -> DpmWaveResponse:
    correlation_id = x_correlation_id or f"corr_wave_preview_{request.trigger_id}"
    try:
        portfolios = _portfolio_inputs_for_request(
            request=request,
            correlation_id=correlation_id,
            advise_authority_client=advise_authority_client,
            risk_authority_client=risk_authority_client,
            campaign_definition_repository=campaign_definition_repository,
        )
        wave = wave_service.preview_wave(
            trigger_type=request.trigger_type,
            trigger_id=request.trigger_id,
            rationale=request.rationale,
            as_of_date=request.as_of_date,
            actor_id=request.actor_id,
            correlation_id=correlation_id,
            portfolios=portfolios,
            mandate_repository=mandate_repository,
        )
    except wave_service.DpmWaveValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"code": exc.code, "message": exc.message},
        ) from exc
    return _wave_response(wave=wave, durable=False)


@router.post(
    "",
    response_model=DpmWaveResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a durable affected-portfolio rebalance wave",
    description=(
        "Creates a durable RFC-0041 rebalance wave. `EXPLICIT_PORTFOLIO_LIST` uses caller-supplied "
        "affected portfolios, while `PM_BOOK_REVIEW` and `CIO_MODEL_CHANGE` resolve cohorts from "
        "lotus-core source products and `RISK_EVENT` evaluates the candidate set through "
        "lotus-risk `RiskEventAffectedCohort:v1` before persistence. `TACTICAL_HOUSE_VIEW` "
        "evaluates the candidate set through lotus-advise "
        "`TacticalHouseViewAffectedCohort:v1` before persistence. `BULK_REVIEW_CAMPAIGN` persists "
        "a Manage-owned campaign membership wave from source-backed candidates. Required header: "
        "`Idempotency-Key`. Unsupported trigger types are rejected and missing source evidence "
        "produces blocked items, not false readiness."
    ),
    responses={
        201: {
            "description": "Durable wave created.",
            "content": {"application/json": {"example": {**WAVE_EXAMPLE, "durable": True}}},
        },
        409: {
            "description": "Wave identity or idempotency conflict.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": {
                            "code": "WAVE_CREATE_CONFLICT",
                            "message": "DPM_WAVE_IDEMPOTENCY_CONFLICT",
                        }
                    }
                }
            },
        },
        422: {
            "description": "Unsupported trigger, missing source evidence, or invalid request.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": {
                            "code": "TACTICAL_HOUSE_VIEW_REQUIRED",
                            "message": "TACTICAL_HOUSE_VIEW requires tactical_house_view source evidence.",
                        }
                    }
                }
            },
        },
    },
)
def create_wave(
    request: DpmWavePreviewRequest,
    idempotency_key: Annotated[
        str,
        Header(
            description="Required idempotency token for durable wave create.",
            examples=["wave-idem-001"],
        ),
    ],
    x_correlation_id: Annotated[
        str | None,
        Header(
            description="Optional correlation id for supportability.", examples=["corr-wave-001"]
        ),
    ] = None,
    mandate_repository: DpmMandateRepository = Depends(get_mandate_repository),
    wave_repository: DpmWaveRepository = Depends(get_wave_repository),
    advise_authority_client: LotusAdviseAuthorityClient | None = Depends(
        get_advise_authority_client
    ),
    risk_authority_client: LotusRiskAuthorityClient | None = Depends(get_risk_authority_client),
    campaign_definition_repository: DpmBulkReviewCampaignDefinitionRepository = Depends(
        get_campaign_definition_repository
    ),
) -> DpmWaveResponse:
    correlation_id = x_correlation_id or f"corr_wave_create_{request.trigger_id}"
    try:
        portfolios = _portfolio_inputs_for_request(
            request=request,
            correlation_id=correlation_id,
            advise_authority_client=advise_authority_client,
            risk_authority_client=risk_authority_client,
            campaign_definition_repository=campaign_definition_repository,
        )
        wave, replayed = wave_service.create_wave(
            trigger_type=request.trigger_type,
            trigger_id=request.trigger_id,
            rationale=request.rationale,
            as_of_date=request.as_of_date,
            actor_id=request.actor_id,
            correlation_id=correlation_id,
            portfolios=portfolios,
            idempotency_key=idempotency_key,
            mandate_repository=mandate_repository,
            wave_repository=wave_repository,
        )
    except wave_service.DpmWaveValidationError as exc:
        status_code = (
            status.HTTP_409_CONFLICT
            if exc.code == "WAVE_CREATE_CONFLICT"
            else status.HTTP_422_UNPROCESSABLE_CONTENT
        )
        raise HTTPException(
            status_code=status_code,
            detail={"code": exc.code, "message": exc.message},
        ) from exc
    return _wave_response(wave=wave, durable=True, idempotent_replay=replayed)


@router.get(
    "",
    response_model=DpmWaveSearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Search durable rebalance waves",
    description=(
        "Returns a bounded search page over durable RFC-0041 waves. Search reads persisted manage "
        "wave truth and derives supportability from item states; it does not recalculate source "
        "readiness, construction alternatives, proof-pack state, or handoff posture."
    ),
    responses={
        200: {
            "description": "Bounded search page of durable waves.",
            "content": {
                "application/json": {
                    "example": {
                        "items": [
                            {
                                "wave_id": "dwv_001",
                                "wave_state": "HANDOFF_READY",
                                "trigger_type": "EXPLICIT_PORTFOLIO_LIST",
                                "trigger_id": "manual-wave-001",
                                "as_of_date": "2026-05-03",
                                "created_at": "2026-05-03T09:30:00Z",
                                "created_by": "pm_001",
                                "item_count": 1,
                                "aggregate_metrics": {
                                    "item_count": 1,
                                    "state_counts": {"HANDOFF_READY": 1},
                                    "ready_item_count": 1,
                                    "blocked_item_count": 0,
                                    "review_required_item_count": 0,
                                    "source_degraded_item_count": 0,
                                },
                                "supportability_state": "ready",
                                "supportability_reason": "wave_supportability_ready",
                                "latest_event_type": "STATE_TRANSITION",
                                "latest_event_reason_code": "WAVE_HANDOFF_READY",
                            }
                        ],
                        "limit": 50,
                        "offset": 0,
                        "returned_count": 1,
                    }
                }
            },
        }
    },
)
def search_waves(
    state: Annotated[
        str | None,
        Query(
            description="Optional wave state filter, for example HANDOFF_READY.",
            examples=["HANDOFF_READY"],
        ),
    ] = None,
    trigger_type: Annotated[
        str | None,
        Query(
            description="Optional trigger type filter.",
            examples=["EXPLICIT_PORTFOLIO_LIST"],
        ),
    ] = None,
    as_of_date: Annotated[
        str | None,
        Query(description="Optional business as-of date filter.", examples=["2026-05-03"]),
    ] = None,
    supportability_state: Annotated[
        Literal["ready", "degraded", "blocked"] | None,
        Query(
            description="Optional derived supportability filter.",
            examples=["ready"],
        ),
    ] = None,
    limit: Annotated[
        int,
        Query(ge=1, le=100, description="Maximum number of waves to return.", examples=[50]),
    ] = 50,
    offset: Annotated[
        int,
        Query(ge=0, description="Zero-based page offset.", examples=[0]),
    ] = 0,
    wave_repository: DpmWaveRepository = Depends(get_wave_repository),
) -> DpmWaveSearchResponse:
    items = wave_service.search_waves(
        wave_repository=wave_repository,
        state=state,
        trigger_type=trigger_type,
        as_of_date=as_of_date,
        supportability_state=supportability_state,
        limit=limit,
        offset=offset,
    )
    return DpmWaveSearchResponse(
        items=[DpmWaveSearchItem.model_validate(item) for item in items],
        limit=limit,
        offset=offset,
        returned_count=len(items),
    )


@router.get(
    "/{wave_id}",
    response_model=DpmWaveDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve durable rebalance wave detail",
    description=(
        "Returns one persisted RFC-0041 wave with items, aggregate metrics, events, source refs, "
        "latest supportability, and proof-pack/handoff posture. The endpoint reads durable manage "
        "state and does not regenerate downstream construction or proof-pack artifacts."
    ),
    responses={
        200: {"description": "Persisted wave detail."},
        404: {"description": "Wave not found."},
    },
)
def get_wave_detail(
    wave_id: str,
    wave_repository: DpmWaveRepository = Depends(get_wave_repository),
) -> DpmWaveDetailResponse:
    try:
        payload = wave_service.retrieve_wave_detail(
            wave_id=wave_id,
            wave_repository=wave_repository,
        )
    except wave_service.DpmWaveLookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": exc.code, "message": exc.message},
        ) from exc
    return DpmWaveDetailResponse.model_validate(payload)


@router.get(
    "/{wave_id}/items",
    response_model=DpmWaveItemsResponse,
    status_code=status.HTTP_200_OK,
    summary="List rebalance wave items",
    description=(
        "Returns persisted item-level wave posture for source readiness, construction selection, "
        "proof-pack linkage, and internal operations handoff. The response is intended for Gateway "
        "and Workbench command-center realization without UI-side recomputation."
    ),
    responses={
        200: {"description": "Persisted wave item list."},
        404: {"description": "Wave not found."},
    },
)
def get_wave_items(
    wave_id: str,
    wave_repository: DpmWaveRepository = Depends(get_wave_repository),
) -> DpmWaveItemsResponse:
    try:
        payload = wave_service.list_wave_items(
            wave_id=wave_id,
            wave_repository=wave_repository,
        )
    except wave_service.DpmWaveLookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": exc.code, "message": exc.message},
        ) from exc
    return DpmWaveItemsResponse.model_validate(payload)


@router.post(
    "/{wave_id}/source-check",
    response_model=DpmWaveResponse,
    status_code=status.HTTP_200_OK,
    summary="Source-check a durable rebalance wave",
    description=(
        "Evaluates RFC-0041 source readiness for each durable wave item using persisted mandate "
        "digital twins, mandate health snapshots, and their source lineage. Items are classified "
        "as `SOURCE_READY`, `SOURCE_DEGRADED`, `REVIEW_REQUIRED`, or `SOURCE_BLOCKED`; caller "
        "portfolio ids or supplied refs alone never promote an item to ready. Repeating the call "
        "after the wave is already `SOURCE_CHECKED` returns the persisted wave as an idempotent "
        "replay without appending a duplicate event."
    ),
    responses={
        200: {
            "description": "Durable source-checked wave with item classifications.",
            "content": {"application/json": {"example": SOURCE_CHECK_WAVE_EXAMPLE}},
        },
        404: {
            "description": "Wave not found.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": {
                            "code": "DPM_WAVE_NOT_FOUND",
                            "message": "Wave dwv_missing was not found.",
                        }
                    }
                }
            },
        },
        409: {
            "description": "Wave version conflict during optimistic update.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": {
                            "code": "DPM_WAVE_VERSION_CONFLICT",
                            "message": "DPM_WAVE_VERSION_CONFLICT",
                        }
                    }
                }
            },
        },
        422: {
            "description": "Wave is not in a state that can be source-checked.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": {
                            "code": "DPM_WAVE_SOURCE_CHECK_INVALID_STATE",
                            "message": "Wave dwv_001 cannot be source-checked from state DRAFT.",
                        }
                    }
                }
            },
        },
    },
)
def source_check_wave(
    wave_id: str,
    request: DpmWaveSourceCheckRequest,
    x_correlation_id: Annotated[
        str | None,
        Header(
            description="Optional correlation id for supportability.",
            examples=["corr-wave-source-check-001"],
        ),
    ] = None,
    mandate_repository: DpmMandateRepository = Depends(get_mandate_repository),
    wave_repository: DpmWaveRepository = Depends(get_wave_repository),
) -> DpmWaveResponse:
    try:
        wave, replayed = wave_service.source_check_wave(
            wave_id=wave_id,
            actor_id=request.actor_id,
            correlation_id=x_correlation_id or f"corr_wave_source_check_{wave_id}",
            mandate_repository=mandate_repository,
            wave_repository=wave_repository,
        )
    except wave_service.DpmWaveLookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": exc.code, "message": exc.message},
        ) from exc
    except wave_service.DpmWaveValidationError as exc:
        status_code = (
            status.HTTP_409_CONFLICT
            if exc.code == "DPM_WAVE_VERSION_CONFLICT"
            else status.HTTP_422_UNPROCESSABLE_CONTENT
        )
        raise HTTPException(
            status_code=status_code,
            detail={"code": exc.code, "message": exc.message},
        ) from exc
    return _wave_response(wave=wave, durable=True, idempotent_replay=replayed)


@router.post(
    "/{wave_id}/simulate",
    response_model=DpmWaveResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate construction alternatives for source-ready wave items",
    description=(
        "Calls the RFC-0039 construction alternative authority for source-ready wave items that "
        "have caller-supplied construction inputs. Source-blocked, degraded, and review-required "
        "items are preserved with their reasons. Ready items without construction input become "
        "`SIMULATION_BLOCKED`; the endpoint does not synthesize portfolio holdings, market data, "
        "model targets, or shelf data from mandate identifiers."
    ),
    responses={
        200: {"description": "Durable simulated or partially simulated wave."},
        404: {"description": "Wave not found."},
        409: {"description": "Wave version conflict during optimistic update."},
        422: {"description": "Wave is not source-checked or request is invalid."},
    },
)
def simulate_wave(
    wave_id: str,
    request: DpmWaveSimulationRequest,
    x_correlation_id: Annotated[
        str | None,
        Header(
            description="Optional correlation id for supportability.",
            examples=["corr-wave-simulate-001"],
        ),
    ] = None,
    construction_repository: ConstructionRepository = Depends(get_construction_repository),
    risk_authority_client: LotusRiskAuthorityClient | None = Depends(get_risk_authority_client),
    run_service: DpmRunSupportService = Depends(get_dpm_run_support_service),
    wave_repository: DpmWaveRepository = Depends(get_wave_repository),
) -> DpmWaveResponse:
    item_inputs: dict[str, RebalanceRequest | wave_service.DpmWaveSimulationInput] = {}
    for item_input in request.item_inputs:
        simulation_input = wave_service.DpmWaveSimulationInput(
            stateless_input=item_input.stateless_input,
            authority_context=item_input.authority_context,
        )
        if item_input.wave_item_id:
            item_inputs[item_input.wave_item_id] = simulation_input
        if item_input.portfolio_id:
            item_inputs[item_input.portfolio_id] = simulation_input
    try:
        wave, replayed = wave_service.simulate_wave(
            wave_id=wave_id,
            actor_id=request.actor_id,
            correlation_id=x_correlation_id or f"corr_wave_simulate_{wave_id}",
            item_inputs=item_inputs,
            methods=request.methods,
            construction_repository=construction_repository,
            run_service=run_service,
            wave_repository=wave_repository,
            risk_authority_client=risk_authority_client,
        )
    except wave_service.DpmWaveLookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": exc.code, "message": exc.message},
        ) from exc
    except wave_service.DpmWaveValidationError as exc:
        raise _wave_validation_http_exception(exc) from exc
    return _wave_response(wave=wave, durable=True, idempotent_replay=replayed)


@router.post(
    "/{wave_id}/items/{wave_item_id}/select",
    response_model=DpmWaveResponse,
    status_code=status.HTTP_200_OK,
    summary="Select a construction alternative for a wave item",
    description=(
        "Records item-level RFC-0039 alternative selection with actor, reason, and optional "
        "comment. When requested, it generates an RFC-0040 proof pack from the selected "
        "alternative. Proof-pack failures are represented as degraded selection posture instead "
        "of unsupported proof-pack readiness."
    ),
    responses={
        200: {"description": "Wave item selection recorded and persisted."},
        404: {"description": "Wave, item, alternative set, or alternative id was not found."},
        409: {"description": "Wave version conflict during optimistic update."},
        422: {"description": "Wave or item is not eligible for selection."},
    },
)
def select_wave_item_alternative(
    wave_id: str,
    wave_item_id: str,
    request: DpmWaveSelectionRequest,
    x_correlation_id: Annotated[
        str | None,
        Header(
            description="Optional correlation id for supportability.",
            examples=["corr-wave-select-001"],
        ),
    ] = None,
    construction_repository: ConstructionRepository = Depends(get_construction_repository),
    proof_pack_repository: DpmProofPackRepository = Depends(get_proof_pack_repository),
    mandate_repository: DpmMandateRepository = Depends(get_mandate_repository),
    run_service: DpmRunSupportService = Depends(get_dpm_run_support_service),
    wave_repository: DpmWaveRepository = Depends(get_wave_repository),
) -> DpmWaveResponse:
    try:
        wave = wave_service.select_wave_item_alternative(
            wave_id=wave_id,
            wave_item_id=wave_item_id,
            alternative_id=request.alternative_id,
            actor_id=request.actor_id,
            reason_code=request.reason_code,
            comment=request.comment,
            correlation_id=x_correlation_id or f"corr_wave_select_{wave_id}_{wave_item_id}",
            generate_proof_pack=request.generate_proof_pack,
            construction_repository=construction_repository,
            proof_pack_repository=proof_pack_repository,
            mandate_repository=mandate_repository,
            run_service=run_service,
            wave_repository=wave_repository,
        )
    except wave_service.DpmWaveLookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": exc.code, "message": exc.message},
        ) from exc
    except wave_service.DpmWaveValidationError as exc:
        raise _wave_validation_http_exception(exc) from exc
    return _wave_response(wave=wave, durable=True)


@router.post(
    "/{wave_id}/approve",
    response_model=DpmWaveResponse,
    status_code=status.HTTP_200_OK,
    summary="Approve selected rebalance wave items",
    description=(
        "Approves selected or proof-pack-ready wave items with actor attribution. Source-blocked, "
        "simulation-blocked, degraded, failed, or otherwise unselected items are never approved; "
        "mixed waves become `APPROVED_WITH_EXCEPTIONS`. Repeating the command after approval "
        "returns the persisted wave without appending duplicate approval evidence."
    ),
    responses={
        200: {"description": "Wave approval recorded or replayed."},
        404: {"description": "Wave not found."},
        409: {"description": "Wave version conflict during optimistic update."},
        422: {"description": "Wave has no eligible items or is not approval-ready."},
    },
)
def approve_wave(
    wave_id: str,
    request: DpmWaveWorkflowCommandRequest,
    x_correlation_id: Annotated[
        str | None,
        Header(
            description="Optional correlation id for supportability.",
            examples=["corr-wave-approve-001"],
        ),
    ] = None,
    wave_repository: DpmWaveRepository = Depends(get_wave_repository),
) -> DpmWaveResponse:
    try:
        wave, replayed = wave_service.approve_wave(
            wave_id=wave_id,
            actor_id=request.actor_id,
            reason_code=request.reason_code,
            comment=request.comment,
            correlation_id=x_correlation_id or f"corr_wave_approve_{wave_id}",
            wave_repository=wave_repository,
        )
    except wave_service.DpmWaveLookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": exc.code, "message": exc.message},
        ) from exc
    except wave_service.DpmWaveValidationError as exc:
        raise _wave_validation_http_exception(exc) from exc
    return _wave_response(wave=wave, durable=True, idempotent_replay=replayed)


@router.post(
    "/{wave_id}/stage",
    response_model=DpmWaveResponse,
    status_code=status.HTTP_200_OK,
    summary="Stage approved rebalance wave items",
    description=(
        "Stages approved wave items for internal operations handoff. The endpoint does not stage "
        "blocked or unapproved items and does not claim external order execution. Repeating the "
        "command after staging or handoff readiness returns the persisted wave without duplicate "
        "events."
    ),
    responses={
        200: {"description": "Wave staging recorded or replayed."},
        404: {"description": "Wave not found."},
        409: {"description": "Wave version conflict during optimistic update."},
        422: {"description": "Wave has no approved items or is not stage-ready."},
    },
)
def stage_wave(
    wave_id: str,
    request: DpmWaveWorkflowCommandRequest,
    x_correlation_id: Annotated[
        str | None,
        Header(
            description="Optional correlation id for supportability.",
            examples=["corr-wave-stage-001"],
        ),
    ] = None,
    wave_repository: DpmWaveRepository = Depends(get_wave_repository),
) -> DpmWaveResponse:
    try:
        wave, replayed = wave_service.stage_wave(
            wave_id=wave_id,
            actor_id=request.actor_id,
            reason_code=request.reason_code,
            comment=request.comment,
            correlation_id=x_correlation_id or f"corr_wave_stage_{wave_id}",
            wave_repository=wave_repository,
        )
    except wave_service.DpmWaveLookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": exc.code, "message": exc.message},
        ) from exc
    except wave_service.DpmWaveValidationError as exc:
        raise _wave_validation_http_exception(exc) from exc
    return _wave_response(wave=wave, durable=True, idempotent_replay=replayed)


@router.post(
    "/{wave_id}/handoff",
    response_model=DpmWaveResponse,
    status_code=status.HTTP_200_OK,
    summary="Create internal operations handoff evidence",
    description=(
        "Creates append-only internal operations handoff evidence for staged wave items. This is "
        "a manage-owned readiness package only: it records `external_execution_claimed=false` and "
        "does not send orders, client communications, or external execution instructions."
    ),
    responses={
        200: {"description": "Wave handoff evidence recorded or replayed."},
        404: {"description": "Wave not found."},
        409: {"description": "Wave version conflict during optimistic update."},
        422: {"description": "Wave has no staged items or is not handoff-ready."},
    },
)
def handoff_wave(
    wave_id: str,
    request: DpmWaveWorkflowCommandRequest,
    x_correlation_id: Annotated[
        str | None,
        Header(
            description="Optional correlation id for supportability.",
            examples=["corr-wave-handoff-001"],
        ),
    ] = None,
    wave_repository: DpmWaveRepository = Depends(get_wave_repository),
) -> DpmWaveResponse:
    try:
        wave, replayed = wave_service.handoff_wave(
            wave_id=wave_id,
            actor_id=request.actor_id,
            reason_code=request.reason_code,
            comment=request.comment,
            correlation_id=x_correlation_id or f"corr_wave_handoff_{wave_id}",
            wave_repository=wave_repository,
        )
    except wave_service.DpmWaveLookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": exc.code, "message": exc.message},
        ) from exc
    except wave_service.DpmWaveValidationError as exc:
        raise _wave_validation_http_exception(exc) from exc
    return _wave_response(wave=wave, durable=True, idempotent_replay=replayed)


@router.post(
    "/{wave_id}/cancel",
    response_model=DpmWaveResponse,
    status_code=status.HTTP_200_OK,
    summary="Cancel a rebalance wave before external execution",
    description=(
        "Cancels an eligible RFC-0041 wave with actor attribution and preserves all item evidence. "
        "Items that have not reached internal handoff are marked `EXCLUDED` with cancellation "
        "diagnostics; manage still records `external_execution_claimed=false`. The endpoint does "
        "not cancel external orders, because manage wave handoff is an internal readiness package "
        "and not an execution instruction. Repeating the command after cancellation returns the "
        "persisted wave without duplicate cancellation events."
    ),
    responses={
        200: {"description": "Wave cancellation recorded or replayed."},
        404: {"description": "Wave not found."},
        409: {"description": "Wave version conflict during optimistic update."},
        422: {"description": "Wave state cannot be cancelled."},
    },
)
def cancel_wave(
    wave_id: str,
    request: DpmWaveWorkflowCommandRequest,
    x_correlation_id: Annotated[
        str | None,
        Header(
            description="Optional correlation id for supportability.",
            examples=["corr-wave-cancel-001"],
        ),
    ] = None,
    wave_repository: DpmWaveRepository = Depends(get_wave_repository),
) -> DpmWaveResponse:
    try:
        wave, replayed = wave_service.cancel_wave(
            wave_id=wave_id,
            actor_id=request.actor_id,
            reason_code=request.reason_code,
            comment=request.comment,
            correlation_id=x_correlation_id or f"corr_wave_cancel_{wave_id}",
            wave_repository=wave_repository,
        )
    except wave_service.DpmWaveLookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": exc.code, "message": exc.message},
        ) from exc
    except wave_service.DpmWaveValidationError as exc:
        raise _wave_validation_http_exception(exc) from exc
    return _wave_response(wave=wave, durable=True, idempotent_replay=replayed)


@router.get(
    "/{wave_id}/proof-pack",
    response_model=DpmWaveProofPackPostureResponse,
    status_code=status.HTTP_200_OK,
    summary="Get wave proof-pack and handoff posture",
    description=(
        "Returns item-level RFC-0040 proof-pack refs, degraded proof-pack posture, append-only "
        "handoff refs, and the no-external-execution boundary for a persisted wave. The endpoint "
        "does not rebuild proof packs or claim external execution."
    ),
    responses={
        200: {"description": "Wave proof-pack and handoff posture."},
        404: {"description": "Wave not found."},
    },
)
def get_wave_proof_pack_posture(
    wave_id: str,
    wave_repository: DpmWaveRepository = Depends(get_wave_repository),
) -> DpmWaveProofPackPostureResponse:
    try:
        payload = wave_service.proof_pack_posture(
            wave_id=wave_id,
            wave_repository=wave_repository,
        )
    except wave_service.DpmWaveLookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": exc.code, "message": exc.message},
        ) from exc
    return DpmWaveProofPackPostureResponse.model_validate(payload)


@router.get(
    "/{wave_id}/report-input",
    response_model=DpmWaveReportInput,
    status_code=status.HTTP_200_OK,
    summary="Get wave report input",
    description=(
        "Returns deterministic `DpmWaveReportInput` for a persisted RFC-0041 rebalance wave. "
        "`lotus-report`, `lotus-render`, and `lotus-archive` can use this payload to materialize "
        "and govern wave evidence without reconstructing wave state, proof-pack linkage, internal "
        "handoff refs, source hashes, or supportability posture. `lotus-manage` does not generate "
        "rendered reports, archive records, or external execution claims."
    ),
    responses={
        200: {"description": "Generated wave report-input payload."},
        404: {"description": "Wave not found."},
        422: {
            "description": (
                "Wave evidence crosses the unsupported external OMS/execution boundary and cannot "
                "be emitted as manage report input."
            )
        },
    },
)
def get_wave_report_input(
    wave_id: str,
    wave_repository: DpmWaveRepository = Depends(get_wave_repository),
    proof_pack_repository: DpmProofPackRepository = Depends(get_proof_pack_repository),
    outcome_review_repository: DpmOutcomeReviewRepository = Depends(get_outcome_review_repository),
    mandate_repository: DpmMandateRepository = Depends(get_mandate_repository),
) -> DpmWaveReportInput:
    try:
        return wave_service.get_report_input(
            wave_id=wave_id,
            wave_repository=wave_repository,
            proof_pack_repository=proof_pack_repository,
            outcome_review_repository=outcome_review_repository,
            mandate_repository=mandate_repository,
        )
    except wave_service.DpmWaveLookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": exc.code, "message": exc.message},
        ) from exc
    except wave_service.DpmWaveValidationError as exc:
        raise _wave_validation_http_exception(exc) from exc


@router.get(
    "/{wave_id}/supportability",
    response_model=DpmWaveSupportabilityResponse,
    status_code=status.HTTP_200_OK,
    summary="Get product-safe wave supportability diagnostics",
    description=(
        "Returns operator-safe RFC-0041 wave supportability diagnostics. The response excludes "
        "portfolio identifiers, client identifiers, raw request bodies, raw response bodies, "
        "secrets, and trace details. Use this endpoint to understand blocked/degraded item states, "
        "source owners, bounded reason codes, remediation routes, and support references."
    ),
    responses={
        200: {"description": "Product-safe wave supportability diagnostics."},
        404: {"description": "Wave not found."},
    },
)
def get_wave_supportability(
    wave_id: str,
    wave_repository: DpmWaveRepository = Depends(get_wave_repository),
) -> DpmWaveSupportabilityResponse:
    try:
        payload = wave_service.wave_supportability(
            wave_id=wave_id,
            wave_repository=wave_repository,
        )
    except wave_service.DpmWaveLookupError as exc:
        record_wave_supportability(
            surface="rebalance/waves/supportability",
            supportability_state="not_found",
            reason="wave_not_found",
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": exc.code, "message": exc.message},
        ) from exc
    supportability_state = str(payload["supportability_state"])
    reason = str(payload["reason"])
    record_wave_supportability(
        surface="rebalance/waves/supportability",
        supportability_state=supportability_state,
        reason=reason,
    )
    logger.info(
        "wave.supportability.inspected",
        extra={
            "extra_fields": {
                "wave_state": payload["wave_state"],
                "supportability_state": supportability_state,
                "reason": reason,
                "issue_count": len(cast(list[object], payload["issues"])),
            }
        },
    )
    return DpmWaveSupportabilityResponse.model_validate(payload)


def _wave_validation_http_exception(exc: wave_service.DpmWaveValidationError) -> HTTPException:
    status_code = (
        status.HTTP_409_CONFLICT
        if exc.code == "DPM_WAVE_VERSION_CONFLICT"
        else status.HTTP_422_UNPROCESSABLE_CONTENT
    )
    return HTTPException(
        status_code=status_code,
        detail={"code": exc.code, "message": exc.message},
    )
