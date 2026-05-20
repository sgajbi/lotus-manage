from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from src.api.request_models import RebalanceRequest
from src.api.routers.wave_campaign_models import DpmBulkReviewCampaignGovernanceInput
from src.core.construction.models import ConstructionAuthorityContext
from src.core.construction.vocabulary import ConstructionMethod
from src.core.waves import DpmWaveSourceRef


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
