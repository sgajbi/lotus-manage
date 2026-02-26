from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, cast

from src.core.advisory.artifact_models import (
    ProposalArtifact,
    ProposalArtifactAssumptionsAndLimits,
    ProposalArtifactDisclosures,
    ProposalArtifactEngineOutputs,
    ProposalArtifactEvidenceBundle,
    ProposalArtifactEvidenceInputs,
    ProposalArtifactExecutionNote,
    ProposalArtifactFx,
    ProposalArtifactHashes,
    ProposalArtifactInclusionFlag,
    ProposalArtifactPortfolioDelta,
    ProposalArtifactPortfolioImpact,
    ProposalArtifactPortfolioState,
    ProposalArtifactPricingAssumptions,
    ProposalArtifactProductDoc,
    ProposalArtifactSuitabilityHighlight,
    ProposalArtifactSuitabilitySummary,
    ProposalArtifactSummary,
    ProposalArtifactTakeaway,
    ProposalArtifactTrade,
    ProposalArtifactTradeRationale,
    ProposalArtifactTradesAndFunding,
    ProposalArtifactWeightChange,
)
from src.core.common.canonical import hash_canonical_payload, strip_keys
from src.core.common.workflow_gates import evaluate_gate_decision
from src.core.models import ProposalResult, ProposalSimulateRequest

_ZERO = Decimal("0")


def _decimal_to_str(value: Decimal) -> str:
    normalized = format(value, "f")
    if "." in normalized:
        normalized = normalized.rstrip("0").rstrip(".")
    return normalized or "0"


def _quantized_weight_str(value: Decimal) -> str:
    return format(value.quantize(Decimal("0.0001")), "f")


def _sorted_allocations(allocations: list[Any]) -> list[Any]:
    return sorted(allocations, key=lambda item: (-item.weight, item.key))


def _state_payload(state: Any) -> ProposalArtifactPortfolioState:
    return ProposalArtifactPortfolioState(
        total_value=state.total_value,
        allocation_by_asset_class=[
            item.model_dump(mode="json")
            for item in _sorted_allocations(state.allocation_by_asset_class)
        ],
        allocation_by_instrument=[
            item.model_dump(mode="json")
            for item in _sorted_allocations(state.allocation_by_instrument)
        ],
    )


def _largest_weight_changes(
    before_state: Any, after_state: Any, *, limit: int
) -> list[ProposalArtifactWeightChange]:
    before_by_id = {row.key: row.weight for row in before_state.allocation_by_instrument}
    after_by_id = {row.key: row.weight for row in after_state.allocation_by_instrument}
    rows = []
    for instrument_id in sorted(set(before_by_id) | set(after_by_id)):
        before_weight = before_by_id.get(instrument_id, _ZERO)
        after_weight = after_by_id.get(instrument_id, _ZERO)
        delta = after_weight - before_weight
        if delta == _ZERO:
            continue
        rows.append((instrument_id, before_weight, after_weight, delta))
    rows.sort(key=lambda item: (-abs(item[3]), item[0]))
    return [
        ProposalArtifactWeightChange(
            bucket_type="INSTRUMENT",
            bucket_id=instrument_id,
            weight_before=_quantized_weight_str(before_weight),
            weight_after=_quantized_weight_str(after_weight),
            delta=_quantized_weight_str(delta),
        )
        for instrument_id, before_weight, after_weight, delta in rows[:limit]
    ]


def _resolve_objective_tags(
    *, request: ProposalSimulateRequest, result: ProposalResult
) -> list[str]:
    tags = []
    has_cash_flow = bool(request.proposed_cash_flows)
    has_trade = any(intent.intent_type == "SECURITY_TRADE" for intent in result.intents)
    if has_trade:
        tags.append("RISK_ALIGNMENT")
    if has_cash_flow:
        tags.append("CASH_DEPLOYMENT")
    if result.drift_analysis is not None:
        if (
            result.drift_analysis.asset_class.drift_total_after
            < result.drift_analysis.asset_class.drift_total_before
        ):
            tags.append("DRIFT_REDUCTION")
    if not tags:
        tags.append("PORTFOLIO_MAINTENANCE")
    return tags


def _resolve_next_step(result: ProposalResult) -> str:
    if result.gate_decision is not None:
        if result.gate_decision.gate == "BLOCKED":
            has_high_suitability = any(
                reason.source == "SUITABILITY" and reason.severity == "HIGH"
                for reason in result.gate_decision.reasons
            )
            return "COMPLIANCE_REVIEW" if has_high_suitability else "RISK_REVIEW"
        if result.gate_decision.gate == "COMPLIANCE_REVIEW_REQUIRED":
            return "COMPLIANCE_REVIEW"
        if result.gate_decision.gate == "RISK_REVIEW_REQUIRED":
            return "RISK_REVIEW"
        if result.gate_decision.gate == "CLIENT_CONSENT_REQUIRED":
            return "CLIENT_CONSENT"
        if result.gate_decision.gate == "EXECUTION_READY":
            return "EXECUTION_READY"
        return "RISK_REVIEW"
    if result.suitability is not None:
        if result.suitability.recommended_gate == "COMPLIANCE_REVIEW":
            return "COMPLIANCE_REVIEW"
        if result.suitability.recommended_gate == "RISK_REVIEW":
            return "RISK_REVIEW"
    if result.status == "READY":
        return "CLIENT_CONSENT"
    if result.status == "PENDING_REVIEW":
        return "RISK_REVIEW"
    return "RISK_REVIEW"


def _cash_weight(state: Any) -> Decimal:
    for row in state.allocation_by_asset_class:
        if row.key == "CASH":
            return cast(Decimal, row.weight)
    return _ZERO


def _build_takeaways(
    *, request: ProposalSimulateRequest, result: ProposalResult
) -> list[ProposalArtifactTakeaway]:
    security_trade_count = sum(1 for item in result.intents if item.intent_type == "SECURITY_TRADE")
    fx_intent_count = sum(1 for item in result.intents if item.intent_type == "FX_SPOT")
    takeaways = [
        ProposalArtifactTakeaway(
            code="STATUS",
            value=f"Proposal status is {result.status}.",
        ),
        ProposalArtifactTakeaway(
            code="INTENTS",
            value=(
                f"Generated {security_trade_count} security trades and "
                f"{fx_intent_count} FX intents."
            ),
        ),
        ProposalArtifactTakeaway(
            code="CASH",
            value=(
                f"Cash weight changed from {_quantized_weight_str(_cash_weight(result.before))} "
                f"to {_quantized_weight_str(_cash_weight(result.after_simulated))}."
            ),
        ),
    ]
    if result.drift_analysis is not None:
        drift_before = _quantized_weight_str(result.drift_analysis.asset_class.drift_total_before)
        drift_after = _quantized_weight_str(result.drift_analysis.asset_class.drift_total_after)
        takeaways.append(
            ProposalArtifactTakeaway(
                code="DRIFT",
                value=f"Asset-class drift changed from {drift_before} to {drift_after}.",
            )
        )
    if request.options.enable_suitability_scanner and result.suitability is not None:
        takeaways.append(
            ProposalArtifactTakeaway(
                code="SUITABILITY",
                value=(
                    f"Suitability issues: new={result.suitability.summary.new_count}, "
                    f"resolved={result.suitability.summary.resolved_count}, "
                    f"persistent={result.suitability.summary.persistent_count}."
                ),
            )
        )
    return takeaways


def _build_trades_and_funding(
    *, request: ProposalSimulateRequest, result: ProposalResult
) -> ProposalArtifactTradesAndFunding:
    fx_rates = {row.pair: row.rate for row in request.market_data_snapshot.fx_rates}
    trade_list = []
    fx_list = []
    has_dependencies = False

    for intent in result.intents:
        if intent.intent_type == "SECURITY_TRADE":
            has_dependencies = has_dependencies or bool(intent.dependencies)
            trade_list.append(
                ProposalArtifactTrade(
                    intent_id=intent.intent_id,
                    type="SECURITY_TRADE",
                    instrument_id=intent.instrument_id,
                    side=intent.side,
                    quantity=_decimal_to_str(intent.quantity or _ZERO),
                    estimated_notional=intent.notional,
                    estimated_notional_base=intent.notional_base,
                    dependencies=intent.dependencies,
                    rationale=ProposalArtifactTradeRationale(
                        code=(intent.rationale.code if intent.rationale else "MANUAL_PROPOSAL"),
                        message=(
                            intent.rationale.message
                            if intent.rationale
                            else "Manual advisory trade from proposal simulation."
                        ),
                    ),
                )
            )
        if intent.intent_type == "FX_SPOT":
            fx_list.append(
                ProposalArtifactFx(
                    intent_id=intent.intent_id,
                    pair=intent.pair,
                    buy_amount=_decimal_to_str(intent.buy_amount),
                    sell_amount_estimated=_decimal_to_str(intent.sell_amount_estimated),
                    rate=(
                        _quantized_weight_str(fx_rates[intent.pair])
                        if intent.pair in fx_rates
                        else None
                    ),
                )
            )

    fx_list = sorted(fx_list, key=lambda item: (item.pair, item.intent_id))
    execution_notes = []
    if has_dependencies:
        execution_notes.append(
            ProposalArtifactExecutionNote(
                code="DEPENDENCY",
                text="One or more BUY intents depend on generated FX intents.",
            )
        )

    return ProposalArtifactTradesAndFunding(
        trade_list=trade_list,
        fx_list=fx_list,
        ordering_policy="CASH_FLOW->SELL->FX->BUY",
        execution_notes=execution_notes,
    )


def _build_suitability_summary(
    *, request: ProposalSimulateRequest, result: ProposalResult
) -> ProposalArtifactSuitabilitySummary:
    if not request.options.enable_suitability_scanner or result.suitability is None:
        return ProposalArtifactSuitabilitySummary(
            status="NOT_AVAILABLE",
            new_issues=0,
            resolved_issues=0,
            persistent_issues=0,
            highest_severity_new=None,
            highlights=[],
            issues=[],
        )

    highlights = [
        ProposalArtifactSuitabilityHighlight(
            code=issue.status_change,
            text=f"{issue.status_change.title()} issue: {issue.issue_id}.",
        )
        for issue in result.suitability.issues[: request.options.drift_top_contributors_limit]
    ]
    return ProposalArtifactSuitabilitySummary(
        status="AVAILABLE",
        new_issues=result.suitability.summary.new_count,
        resolved_issues=result.suitability.summary.resolved_count,
        persistent_issues=result.suitability.summary.persistent_count,
        highest_severity_new=result.suitability.summary.highest_severity_new,
        highlights=highlights,
        issues=result.suitability.issues,
    )


def build_proposal_artifact(
    *,
    request: ProposalSimulateRequest,
    proposal_result: ProposalResult,
    created_at: str | None = None,
) -> ProposalArtifact:
    before_state = proposal_result.before
    after_state = proposal_result.after_simulated
    largest_weight_changes = _largest_weight_changes(
        before_state,
        after_state,
        limit=request.options.drift_top_contributors_limit,
    )

    assumptions = ProposalArtifactAssumptionsAndLimits(
        pricing=ProposalArtifactPricingAssumptions(
            market_data_snapshot_id=proposal_result.lineage.market_data_snapshot_id,
            prices_as_of=proposal_result.lineage.market_data_snapshot_id,
            fx_as_of=proposal_result.lineage.market_data_snapshot_id,
            valuation_mode=request.options.valuation_mode.value,
        ),
        costs_and_fees=ProposalArtifactInclusionFlag(
            included=False,
            notes="Transaction costs, fees, and bid/ask spreads are not modeled.",
        ),
        tax=ProposalArtifactInclusionFlag(
            included=False,
            notes="Tax impact is not modeled in the proposal artifact.",
        ),
        execution=ProposalArtifactInclusionFlag(
            included=False,
            notes="Execution timing and slippage are not modeled.",
        ),
    )

    traded_instruments = sorted(
        {
            intent.instrument_id
            for intent in proposal_result.intents
            if intent.intent_type == "SECURITY_TRADE"
        }
    )

    artifact = ProposalArtifact(
        gate_decision=(
            proposal_result.gate_decision
            or evaluate_gate_decision(
                status=proposal_result.status,
                rule_results=proposal_result.rule_results,
                suitability=proposal_result.suitability,
                diagnostics=proposal_result.diagnostics,
                options=request.options,
                default_requires_client_consent=True,
            )
        ),
        artifact_id=proposal_result.proposal_run_id.replace("pr_", "pa_", 1),
        proposal_run_id=proposal_result.proposal_run_id,
        correlation_id=proposal_result.correlation_id,
        created_at=created_at or datetime.now(timezone.utc).isoformat(),
        status=proposal_result.status,
        summary=ProposalArtifactSummary(
            title=f"Proposal for {request.portfolio_snapshot.portfolio_id}",
            objective_tags=_resolve_objective_tags(request=request, result=proposal_result),
            advisor_notes=[],
            recommended_next_step=_resolve_next_step(proposal_result),
            key_takeaways=_build_takeaways(request=request, result=proposal_result),
        ),
        portfolio_impact=ProposalArtifactPortfolioImpact(
            before=_state_payload(before_state),
            after=_state_payload(after_state),
            delta=ProposalArtifactPortfolioDelta(
                total_value_delta={
                    "amount": after_state.total_value.amount - before_state.total_value.amount,
                    "currency": before_state.total_value.currency,
                },
                largest_weight_changes=largest_weight_changes,
            ),
            reconciliation=(
                proposal_result.reconciliation.model_dump(mode="json")
                if proposal_result.reconciliation is not None
                else None
            ),
        ),
        trades_and_funding=_build_trades_and_funding(request=request, result=proposal_result),
        suitability_summary=_build_suitability_summary(request=request, result=proposal_result),
        assumptions_and_limits=assumptions,
        disclosures=ProposalArtifactDisclosures(
            risk_disclaimer=(
                "This proposal is based on market-data snapshots and does not guarantee "
                "future performance."
            ),
            product_docs=[
                ProposalArtifactProductDoc(
                    instrument_id=instrument_id,
                    doc_ref="KID/FactSheet placeholder",
                )
                for instrument_id in traded_instruments
            ],
        ),
        evidence_bundle=ProposalArtifactEvidenceBundle(
            inputs=ProposalArtifactEvidenceInputs(
                portfolio_snapshot=request.portfolio_snapshot.model_dump(mode="json"),
                market_data_snapshot=request.market_data_snapshot.model_dump(mode="json"),
                shelf_entries=[entry.model_dump(mode="json") for entry in request.shelf_entries],
                options=request.options.model_dump(mode="json"),
                proposed_cash_flows=[
                    item.model_dump(mode="json") for item in request.proposed_cash_flows
                ],
                proposed_trades=[item.model_dump(mode="json") for item in request.proposed_trades],
                reference_model=(
                    request.reference_model.model_dump(mode="json")
                    if request.reference_model is not None
                    else None
                ),
            ),
            engine_outputs=ProposalArtifactEngineOutputs(
                proposal_result=proposal_result.model_dump(mode="json")
            ),
            hashes=ProposalArtifactHashes(
                request_hash=proposal_result.lineage.request_hash,
                artifact_hash="",
            ),
            engine_version=proposal_result.lineage.engine_version or "unknown",
        ),
    )
    payload = artifact.model_dump(mode="json")
    canonical_payload = strip_keys(payload, exclude={"created_at", "artifact_hash"})
    artifact_hash = hash_canonical_payload(canonical_payload)
    payload["evidence_bundle"]["hashes"]["artifact_hash"] = artifact_hash
    return cast(ProposalArtifact, ProposalArtifact.model_validate(payload))
