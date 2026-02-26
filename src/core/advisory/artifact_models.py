from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from src.core.models import GateDecision, Money, SuitabilityIssue


class ProposalArtifactSummaryNote(BaseModel):
    code: str = Field(description="Deterministic summary note code.", examples=["NOTE"])
    text: str = Field(
        description="Deterministic summary note text suitable for UI rendering.",
        examples=["Client requested partial risk increase and cash deployment."],
    )


class ProposalArtifactTakeaway(BaseModel):
    code: str = Field(description="Machine-readable takeaway code.", examples=["DRIFT"])
    value: str = Field(
        description="Deterministic takeaway statement derived from simulation data.",
        examples=["Asset-class drift reduced from 0.1200 to 0.0700."],
    )


class ProposalArtifactSummary(BaseModel):
    title: str = Field(
        description="Artifact title for advisor/client views.",
        examples=["Proposal for pf_advisory_01"],
    )
    objective_tags: List[str] = Field(
        default_factory=list,
        description="Deterministic objective tags derived from proposal inputs and outputs.",
        examples=[["DRIFT_REDUCTION", "RISK_ALIGNMENT", "CASH_DEPLOYMENT"]],
    )
    advisor_notes: List[ProposalArtifactSummaryNote] = Field(
        default_factory=list,
        description="Structured advisor note placeholders.",
    )
    recommended_next_step: Literal[
        "CLIENT_CONSENT",
        "RISK_REVIEW",
        "COMPLIANCE_REVIEW",
        "EXECUTION_READY",
        "NONE",
    ] = Field(
        description="Deterministic post-simulation workflow recommendation.",
        examples=["CLIENT_CONSENT"],
    )
    key_takeaways: List[ProposalArtifactTakeaway] = Field(
        default_factory=list,
        description="Deterministic machine-derived proposal takeaways.",
    )


class ProposalArtifactPortfolioState(BaseModel):
    total_value: Money = Field(description="Total portfolio value in base currency.")
    allocation_by_asset_class: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Deterministically ordered asset-class allocation rows.",
        examples=[
            [
                {
                    "key": "EQUITY",
                    "weight": "0.6200",
                    "value": {"amount": "620000.00", "currency": "USD"},
                }
            ]
        ],
    )
    allocation_by_instrument: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Deterministically ordered instrument allocation rows.",
        examples=[
            [
                {
                    "key": "US_EQ_ETF",
                    "weight": "0.1800",
                    "value": {"amount": "180000.00", "currency": "USD"},
                }
            ]
        ],
    )


class ProposalArtifactWeightChange(BaseModel):
    bucket_type: Literal["INSTRUMENT"] = Field(
        description="Bucket type used for weight-change entries.",
        examples=["INSTRUMENT"],
    )
    bucket_id: str = Field(
        description="Instrument id for the weight-change row.", examples=["EQ_1"]
    )
    weight_before: str = Field(
        description="Before-state weight as a quantized string.",
        examples=["0.1200"],
    )
    weight_after: str = Field(
        description="After-state weight as a quantized string.",
        examples=["0.1800"],
    )
    delta: str = Field(
        description="After-minus-before weight delta as a quantized string.",
        examples=["0.0600"],
    )


class ProposalArtifactPortfolioDelta(BaseModel):
    total_value_delta: Money = Field(description="After minus before total value.")
    largest_weight_changes: List[ProposalArtifactWeightChange] = Field(
        default_factory=list,
        description="Top absolute instrument weight changes in deterministic order.",
    )


class ProposalArtifactPortfolioImpact(BaseModel):
    before: ProposalArtifactPortfolioState = Field(description="Before-state allocation snapshot.")
    after: ProposalArtifactPortfolioState = Field(description="After-state allocation snapshot.")
    delta: ProposalArtifactPortfolioDelta = Field(description="Computed portfolio deltas.")
    reconciliation: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Reconciliation payload copied from proposal simulation output.",
    )


class ProposalArtifactTradeRationale(BaseModel):
    code: str = Field(
        description="Machine-readable trade rationale code.", examples=["MANUAL_PROPOSAL"]
    )
    message: str = Field(
        description="Deterministic rationale message for trade presentation.",
        examples=["Manual advisory trade from proposal simulation."],
    )


class ProposalArtifactTrade(BaseModel):
    intent_id: str = Field(description="Intent identifier from proposal output.", examples=["oi_1"])
    type: Literal["SECURITY_TRADE"] = Field(
        description="Artifact trade entry type.", examples=["SECURITY_TRADE"]
    )
    instrument_id: str = Field(description="Security instrument id.", examples=["US_EQ_ETF"])
    side: Literal["BUY", "SELL"] = Field(description="Trade side.", examples=["BUY"])
    quantity: str = Field(description="Trade quantity as a decimal string.", examples=["10"])
    estimated_notional: Optional[Money] = Field(
        default=None,
        description="Estimated trade notional in instrument currency.",
    )
    estimated_notional_base: Optional[Money] = Field(
        default=None,
        description="Estimated trade notional in portfolio base currency.",
    )
    dependencies: List[str] = Field(
        default_factory=list,
        description="Intent dependencies that must execute first.",
        examples=[["oi_fx_1"]],
    )
    rationale: ProposalArtifactTradeRationale = Field(description="Deterministic trade rationale.")


class ProposalArtifactFx(BaseModel):
    intent_id: str = Field(description="FX intent identifier.", examples=["oi_fx_1"])
    pair: str = Field(description="FX pair identifier.", examples=["USD/SGD"])
    buy_amount: str = Field(
        description="Buy amount in buy currency as a decimal string.",
        examples=["1500.00"],
    )
    sell_amount_estimated: str = Field(
        description="Estimated sell amount in funding currency as a decimal string.",
        examples=["2025.00"],
    )
    rate: Optional[str] = Field(
        default=None,
        description="Resolved FX rate string when available from market snapshot.",
        examples=["1.3500"],
    )


class ProposalArtifactExecutionNote(BaseModel):
    code: str = Field(description="Execution note code.", examples=["DEPENDENCY"])
    text: str = Field(
        description="Deterministic execution note text.",
        examples=["One or more BUY intents depend on generated FX intents."],
    )


class ProposalArtifactTradesAndFunding(BaseModel):
    trade_list: List[ProposalArtifactTrade] = Field(
        default_factory=list,
        description="Deterministically ordered security trades.",
    )
    fx_list: List[ProposalArtifactFx] = Field(
        default_factory=list,
        description="Deterministically ordered FX intents for funding.",
    )
    ordering_policy: str = Field(
        description="Execution ordering policy used when rendering the package.",
        examples=["CASH_FLOW->SELL->FX->BUY"],
    )
    execution_notes: List[ProposalArtifactExecutionNote] = Field(
        default_factory=list,
        description="Structured deterministic execution notes.",
    )


class ProposalArtifactSuitabilityHighlight(BaseModel):
    code: Literal["NEW", "RESOLVED", "PERSISTENT"] = Field(
        description="Suitability status-change highlight code.",
        examples=["NEW"],
    )
    text: str = Field(
        description="Deterministic suitability highlight text for presentation.",
        examples=["New issue: SUIT_ISSUER_MAX."],
    )


class ProposalArtifactSuitabilitySummary(BaseModel):
    status: Literal["AVAILABLE", "NOT_AVAILABLE"] = Field(
        description="Suitability section availability.",
        examples=["AVAILABLE"],
    )
    new_issues: int = Field(description="Count of NEW suitability issues.", examples=[1])
    resolved_issues: int = Field(description="Count of RESOLVED suitability issues.", examples=[0])
    persistent_issues: int = Field(
        description="Count of PERSISTENT suitability issues.",
        examples=[2],
    )
    highest_severity_new: Optional[Literal["LOW", "MEDIUM", "HIGH"]] = Field(
        default=None,
        description="Highest severity among NEW issues when present.",
        examples=["HIGH"],
    )
    highlights: List[ProposalArtifactSuitabilityHighlight] = Field(
        default_factory=list,
        description="Deterministic suitability highlights.",
    )
    issues: List[SuitabilityIssue] = Field(
        default_factory=list,
        description="Detailed deterministic suitability issue list.",
    )


class ProposalArtifactPricingAssumptions(BaseModel):
    market_data_snapshot_id: str = Field(
        description="Market-data snapshot identifier used by simulation.",
        examples=["md_2026_02_19"],
    )
    prices_as_of: str = Field(
        description="Price snapshot as-of identifier used by artifact assumptions.",
        examples=["md_2026_02_19"],
    )
    fx_as_of: str = Field(
        description="FX snapshot as-of identifier used by artifact assumptions.",
        examples=["md_2026_02_19"],
    )
    valuation_mode: str = Field(
        description="Valuation mode effective for the simulation.",
        examples=["CALCULATED"],
    )


class ProposalArtifactInclusionFlag(BaseModel):
    included: bool = Field(
        description="Whether the component is included in simulation.", examples=[False]
    )
    notes: str = Field(
        description="Deterministic note describing inclusion/exclusion scope.",
        examples=["Transaction costs and bid/ask spread are not modeled."],
    )


class ProposalArtifactAssumptionsAndLimits(BaseModel):
    pricing: ProposalArtifactPricingAssumptions = Field(
        description="Pricing and valuation assumptions."
    )
    costs_and_fees: ProposalArtifactInclusionFlag = Field(
        description="Costs and fees inclusion statement."
    )
    tax: ProposalArtifactInclusionFlag = Field(description="Tax inclusion statement.")
    execution: ProposalArtifactInclusionFlag = Field(description="Execution inclusion statement.")


class ProposalArtifactProductDoc(BaseModel):
    instrument_id: str = Field(description="Instrument identifier.", examples=["US_EQ_ETF"])
    doc_ref: str = Field(
        description="Product-document placeholder reference.",
        examples=["KID/FactSheet placeholder"],
    )


class ProposalArtifactDisclosures(BaseModel):
    risk_disclaimer: str = Field(
        description="Deterministic generic risk disclaimer placeholder.",
        examples=[
            "This proposal is based on market-data snapshots and does not guarantee "
            "future performance."
        ],
    )
    product_docs: List[ProposalArtifactProductDoc] = Field(
        default_factory=list,
        description="Product-document placeholder references for traded instruments.",
    )


class ProposalArtifactEvidenceInputs(BaseModel):
    portfolio_snapshot: Dict[str, Any] = Field(
        description="Original portfolio snapshot input payload."
    )
    market_data_snapshot: Dict[str, Any] = Field(
        description="Original market-data snapshot input payload."
    )
    shelf_entries: List[Dict[str, Any]] = Field(description="Original shelf entries input payload.")
    options: Dict[str, Any] = Field(description="Original request options payload.")
    proposed_cash_flows: List[Dict[str, Any]] = Field(
        description="Original proposed cash-flow payload rows."
    )
    proposed_trades: List[Dict[str, Any]] = Field(
        description="Original proposed trade payload rows."
    )
    reference_model: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Original optional reference model payload.",
    )


class ProposalArtifactEngineOutputs(BaseModel):
    proposal_result: Dict[str, Any] = Field(
        description="Full proposal simulation output payload used to build artifact."
    )


class ProposalArtifactHashes(BaseModel):
    request_hash: str = Field(
        description="Canonical request hash from proposal lineage.",
        examples=["sha256:4e2baf..."],
    )
    artifact_hash: str = Field(
        description="Canonical artifact hash excluding volatile fields.",
        examples=["sha256:10ffab..."],
    )


class ProposalArtifactEvidenceBundle(BaseModel):
    inputs: ProposalArtifactEvidenceInputs = Field(description="Input evidence payloads.")
    engine_outputs: ProposalArtifactEngineOutputs = Field(
        description="Engine output evidence payloads."
    )
    hashes: ProposalArtifactHashes = Field(description="Request and artifact hashes.")
    engine_version: str = Field(
        description="Engine version captured in proposal lineage.",
        examples=["0.1.0"],
    )


class ProposalArtifact(BaseModel):
    artifact_id: str = Field(description="Artifact identifier.", examples=["pa_abc12345"])
    proposal_run_id: str = Field(description="Proposal run identifier.", examples=["pr_abc12345"])
    correlation_id: str = Field(description="Correlation identifier.", examples=["corr_123abc"])
    created_at: str = Field(
        description="Artifact creation timestamp in UTC ISO8601.",
        examples=["2026-02-19T12:00:00+00:00"],
    )
    status: Literal["READY", "PENDING_REVIEW", "BLOCKED"] = Field(
        description="Top-level artifact domain status copied from proposal output.",
        examples=["READY"],
    )
    gate_decision: GateDecision = Field(
        description="Deterministic workflow gate decision copied from proposal simulation output."
    )
    summary: ProposalArtifactSummary = Field(description="Artifact summary section.")
    portfolio_impact: ProposalArtifactPortfolioImpact = Field(
        description="Before/after allocation and delta section."
    )
    trades_and_funding: ProposalArtifactTradesAndFunding = Field(
        description="Deterministic trade and funding section."
    )
    suitability_summary: ProposalArtifactSuitabilitySummary = Field(
        description="Suitability summary section."
    )
    assumptions_and_limits: ProposalArtifactAssumptionsAndLimits = Field(
        description="Assumptions and model limits section."
    )
    disclosures: ProposalArtifactDisclosures = Field(description="Disclosure placeholders section.")
    evidence_bundle: ProposalArtifactEvidenceBundle = Field(
        description="Evidence payload section for reproducibility."
    )
