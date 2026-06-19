from src.core.dpm_source_context import (
    DpmCoreInstrumentEligibilityBulkResponse,
    DpmCoreMandateBindingResponse,
    DpmCoreModelPortfolioTargetResponse,
    DpmCorePolicyContext,
    DpmCoreSourceLineage,
    DpmCoreSupportability,
    DpmStatefulInput,
)
from src.core.models import PortfolioSnapshot
from src.infrastructure.core_sourcing import snapshot_mapping as _snapshot_mapping


def requested_execution_instrument_ids(
    *,
    portfolio_snapshot: PortfolioSnapshot,
    model_targets: DpmCoreModelPortfolioTargetResponse,
) -> list[str]:
    held_instrument_ids = _snapshot_mapping.held_instrument_ids(portfolio_snapshot)
    target_instrument_ids = [target.instrument_id for target in model_targets.targets]
    return sorted(set(held_instrument_ids + target_instrument_ids))


def execution_context_currency_pairs(
    portfolio_snapshot: PortfolioSnapshot,
) -> list[tuple[str, str]]:
    return _snapshot_mapping.required_currency_pairs(
        portfolio_snapshot=portfolio_snapshot,
        base_currency=portfolio_snapshot.base_currency,
    )


def execution_context_exposure_currencies(
    currency_pairs: list[tuple[str, str]],
) -> list[str]:
    return sorted({source_currency for source_currency, _ in currency_pairs})


def execution_context_policy(
    *,
    stateful_input: DpmStatefulInput,
    policy_context: DpmCorePolicyContext,
) -> DpmCorePolicyContext:
    return DpmCorePolicyContext(
        recommended_policy_pack_id=(
            stateful_input.policy_pack_id or policy_context.recommended_policy_pack_id
        ),
        tenant_id=policy_context.tenant_id,
        booking_center_code=policy_context.booking_center_code,
        mandate_id=policy_context.mandate_id,
    )


def execution_context_lineage(
    *,
    stateful_input: DpmStatefulInput,
    portfolio_snapshot: PortfolioSnapshot,
    model_targets: DpmCoreModelPortfolioTargetResponse,
    eligibility: DpmCoreInstrumentEligibilityBulkResponse,
    mandate: DpmCoreMandateBindingResponse,
) -> DpmCoreSourceLineage:
    as_of_date = stateful_input.as_of.isoformat()
    return DpmCoreSourceLineage(
        portfolio_snapshot_id=portfolio_snapshot.snapshot_id
        or f"core-snapshot:{stateful_input.portfolio_id}:{as_of_date}",
        market_data_snapshot_id=f"market-data-coverage:{as_of_date}",
        model_portfolio_id=model_targets.model_portfolio_id,
        model_portfolio_version=model_targets.model_portfolio_version,
        shelf_version=eligibility.lineage.get("contract_version"),
        integration_policy_version=mandate.lineage.get("contract_version"),
        source_lineage_bundle_id=f"rfc-087:{stateful_input.portfolio_id}:{as_of_date}",
    )


def ready_execution_context_supportability() -> DpmCoreSupportability:
    return DpmCoreSupportability(
        state="READY",
        reason="DPM_CORE_CONTEXT_READY",
        freshness_bucket="current",
        missing_source_families=[],
        degraded_source_families=[],
    )
