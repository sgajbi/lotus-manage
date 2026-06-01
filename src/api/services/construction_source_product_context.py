from decimal import Decimal

from src.core.common.canonical import hash_canonical_payload
from src.core.construction.models import (
    AuthoritativeClientRestrictionContext,
    AuthoritativeClientRestrictionRule,
    AuthoritativeClientIncomeNeedsSchedule,
    AuthoritativeCurrencyOverlayContext,
    AuthoritativeExecutionAcknowledgementContext,
    AuthoritativeLiquidityCashflowProjection,
    AuthoritativeLiquidityContext,
    AuthoritativeLiquidityReserveRequirement,
    AuthoritativePlannedWithdrawalSchedule,
    AuthoritativeSustainabilityPreference,
    AuthoritativeSustainabilityPreferenceContext,
    AuthoritativeTransactionCostContext,
    AuthoritativeTransactionCostPoint,
    ConstructionAuthorityContext,
)
from src.core.construction.vocabulary import ConstructionMethodStatus
from src.core.dpm_source_context import (
    DpmCoreClientIncomeNeedsScheduleResponse,
    DpmCoreClientRestrictionProfileResponse,
    DpmCoreExternalCurrencyExposureResponse,
    DpmCoreExternalEligibleHedgeInstrumentResponse,
    DpmCoreExternalFXForwardCurveResponse,
    DpmCoreExternalHedgeExecutionReadinessResponse,
    DpmCoreExternalHedgePolicyResponse,
    DpmCoreExternalOrderExecutionAcknowledgementResponse,
    DpmCoreExecutionContext,
    DpmCoreLiquidityReserveRequirementResponse,
    DpmCorePlannedWithdrawalScheduleResponse,
    DpmCorePortfolioCashflowProjectionResponse,
    DpmCoreSustainabilityPreferenceProfileResponse,
    DpmCoreTransactionCostCurveResponse,
)
from src.core.models import Money


def client_income_needs_schedule_context(
    income_needs: DpmCoreClientIncomeNeedsScheduleResponse,
) -> AuthoritativeClientIncomeNeedsSchedule:
    payload = income_needs.model_dump(mode="json", exclude_none=True)
    source_hash = hash_canonical_payload(payload)
    return AuthoritativeClientIncomeNeedsSchedule(
        source_product_name=income_needs.product_name,
        source_product_version=income_needs.product_version,
        source_system="lotus-core",
        source_id=income_needs.source_batch_fingerprint
        or income_needs.lineage.get("source_batch_fingerprint")
        or source_hash,
        content_hash=source_hash,
        schedule_count=income_needs.supportability.schedule_count,
        currencies=sorted({entry.currency for entry in income_needs.schedules}),
        highest_priority=(
            min(entry.priority for entry in income_needs.schedules)
            if income_needs.schedules
            else None
        ),
        supportability_status=source_status_to_method_status(income_needs.supportability.state),
        reason_codes=[income_needs.supportability.reason, "CORE_INCOME_NEEDS_PRESENT"],
    )


def liquidity_cashflow_projection_context(
    cashflow_projection: DpmCorePortfolioCashflowProjectionResponse,
) -> AuthoritativeLiquidityCashflowProjection:
    payload = cashflow_projection.model_dump(mode="json", exclude_none=True)
    source_hash = hash_canonical_payload(payload)
    status = (
        cashflow_projection.data_quality_status
        if cashflow_projection.data_quality_status in {"READY", "DEGRADED", "INCOMPLETE"}
        else "READY"
    )
    return AuthoritativeLiquidityCashflowProjection(
        source_product_name=cashflow_projection.product_name,
        source_product_version=cashflow_projection.product_version,
        source_system="lotus-core",
        total_net_cashflow=Money(
            amount=cashflow_projection.total_net_cashflow,
            currency=cashflow_projection.portfolio_currency,
        ),
        projection_start=cashflow_projection.range_start_date,
        projection_end=cashflow_projection.range_end_date,
        include_projected=cashflow_projection.include_projected,
        latest_evidence_timestamp=cashflow_projection.latest_evidence_timestamp,
        source_batch_fingerprint=cashflow_projection.source_batch_fingerprint
        or cashflow_projection.lineage.get("source_batch_fingerprint")
        or source_hash,
        data_quality_status=source_status_to_method_status(status),
        reason_codes=["CORE_CASHFLOW_PROJECTION_READY"],
    )


def liquidity_reserve_requirement_context(
    reserve_requirement: DpmCoreLiquidityReserveRequirementResponse,
) -> AuthoritativeLiquidityReserveRequirement:
    payload = reserve_requirement.model_dump(mode="json", exclude_none=True)
    source_hash = hash_canonical_payload(payload)
    return AuthoritativeLiquidityReserveRequirement(
        source_product_name=reserve_requirement.product_name,
        source_product_version=reserve_requirement.product_version,
        source_system="lotus-core",
        source_id=reserve_requirement.source_batch_fingerprint
        or reserve_requirement.lineage.get("source_batch_fingerprint")
        or source_hash,
        content_hash=source_hash,
        requirement_count=reserve_requirement.supportability.requirement_count,
        currencies=sorted({entry.currency for entry in reserve_requirement.requirements}),
        maximum_horizon_days=(
            max(entry.horizon_days for entry in reserve_requirement.requirements)
            if reserve_requirement.requirements
            else None
        ),
        supportability_status=source_status_to_method_status(
            reserve_requirement.supportability.state
        ),
        reason_codes=[
            reserve_requirement.supportability.reason,
            "CORE_LIQUIDITY_RESERVE_PRESENT",
        ],
    )


def planned_withdrawal_schedule_context(
    planned_withdrawals: DpmCorePlannedWithdrawalScheduleResponse,
) -> AuthoritativePlannedWithdrawalSchedule:
    payload = planned_withdrawals.model_dump(mode="json", exclude_none=True)
    source_hash = hash_canonical_payload(payload)
    return AuthoritativePlannedWithdrawalSchedule(
        source_product_name=planned_withdrawals.product_name,
        source_product_version=planned_withdrawals.product_version,
        source_system="lotus-core",
        source_id=planned_withdrawals.source_batch_fingerprint
        or planned_withdrawals.lineage.get("source_batch_fingerprint")
        or source_hash,
        content_hash=source_hash,
        withdrawal_count=planned_withdrawals.supportability.withdrawal_count,
        currencies=sorted({entry.currency for entry in planned_withdrawals.withdrawals}),
        horizon_days=planned_withdrawals.horizon_days,
        supportability_status=source_status_to_method_status(
            planned_withdrawals.supportability.state
        ),
        reason_codes=[
            planned_withdrawals.supportability.reason,
            "CORE_PLANNED_WITHDRAWALS_PRESENT",
        ],
    )


def source_liquidity_context(
    *,
    cashflow_projection: DpmCorePortfolioCashflowProjectionResponse | None,
    income_needs: DpmCoreClientIncomeNeedsScheduleResponse | None,
    reserve_requirement: DpmCoreLiquidityReserveRequirementResponse | None,
    planned_withdrawals: DpmCorePlannedWithdrawalScheduleResponse | None,
) -> AuthoritativeLiquidityContext | None:
    if (
        cashflow_projection is None
        and income_needs is None
        and reserve_requirement is None
        and planned_withdrawals is None
    ):
        return None

    source_reason_codes = [
        "LIQUIDITY_POLICY_DERIVED_FROM_MANAGE_SETTLEMENT_RULES",
        "CORE_LIQUIDITY_SOURCE_CONTEXT_PRESENT",
    ]
    cashflow_context = (
        liquidity_cashflow_projection_context(cashflow_projection)
        if cashflow_projection is not None
        else None
    )
    income_context = (
        client_income_needs_schedule_context(income_needs) if income_needs is not None else None
    )
    reserve_context = (
        liquidity_reserve_requirement_context(reserve_requirement)
        if reserve_requirement is not None
        else None
    )
    withdrawal_context = (
        planned_withdrawal_schedule_context(planned_withdrawals)
        if planned_withdrawals is not None
        else None
    )
    if income_context is not None:
        source_reason_codes.append("CLIENT_INCOME_NEEDS_SOURCE_PRESENT")
    if reserve_context is not None:
        source_reason_codes.append("LIQUIDITY_RESERVE_SOURCE_PRESENT")
    if withdrawal_context is not None:
        source_reason_codes.append("PLANNED_WITHDRAWAL_SOURCE_PRESENT")

    return AuthoritativeLiquidityContext(
        supportability_status=ConstructionMethodStatus.READY,
        source_system="lotus-manage-settlement-engine",
        policy_id="manage-liquidity-policy.v1",
        minimum_cash_weight=Decimal("0.02"),
        allowed_liquidity_tiers=["L1", "L2", "L3"],
        cashflow_projection=cashflow_context,
        client_income_needs_schedule=income_context,
        liquidity_reserve_requirement=reserve_context,
        planned_withdrawal_schedule=withdrawal_context,
        reason_codes=source_reason_codes,
    )


def transaction_cost_context_from_curve(
    curve: DpmCoreTransactionCostCurveResponse,
) -> AuthoritativeTransactionCostContext:
    curve_payload = curve.model_dump(mode="json", exclude_none=True)
    source_hash = hash_canonical_payload(curve_payload)
    source_id = (
        curve.source_batch_fingerprint
        or curve.lineage.get("source_batch_fingerprint")
        or curve.page.request_scope_fingerprint
    )
    return AuthoritativeTransactionCostContext(
        supportability_status=source_status_to_method_status(curve.supportability.state),
        source_system="lotus-core",
        source_product_name=curve.product_name,
        source_product_version=curve.product_version,
        source_id=source_id,
        content_hash=source_hash,
        as_of_date=curve.as_of_date,
        window_start_date=curve.window.start_date,
        window_end_date=curve.window.end_date,
        returned_curve_point_count=curve.supportability.returned_curve_point_count,
        missing_security_ids=curve.supportability.missing_security_ids,
        curve_points=[
            AuthoritativeTransactionCostPoint(
                security_id=point.security_id,
                transaction_type=point.transaction_type,
                currency=point.currency,
                observation_count=point.observation_count,
                total_notional=point.total_notional,
                total_cost=point.total_cost,
                average_cost_bps=point.average_cost_bps,
                min_cost_bps=point.min_cost_bps,
                max_cost_bps=point.max_cost_bps,
                first_observed_date=point.first_observed_date,
                last_observed_date=point.last_observed_date,
                sample_transaction_ids=point.sample_transaction_ids[:5],
            )
            for point in curve.curve_points[:10]
        ],
        reason_codes=[curve.supportability.reason],
    )


def external_treasury_currency_overlay_context(
    *,
    hedge_readiness: DpmCoreExternalHedgeExecutionReadinessResponse | None,
    currency_exposure: DpmCoreExternalCurrencyExposureResponse | None,
    hedge_policy: DpmCoreExternalHedgePolicyResponse | None,
    eligible_hedge_instruments: DpmCoreExternalEligibleHedgeInstrumentResponse | None,
    fx_forward_curve: DpmCoreExternalFXForwardCurveResponse | None,
) -> AuthoritativeCurrencyOverlayContext | None:
    if (
        hedge_readiness is None
        and currency_exposure is None
        and hedge_policy is None
        and eligible_hedge_instruments is None
        and fx_forward_curve is None
    ):
        return None

    readiness_payload = (
        hedge_readiness.model_dump(mode="json", exclude_none=True)
        if hedge_readiness is not None
        else None
    )
    exposure_payload = (
        currency_exposure.model_dump(mode="json", exclude_none=True)
        if currency_exposure is not None
        else None
    )
    hedge_policy_payload = (
        hedge_policy.model_dump(mode="json", exclude_none=True)
        if hedge_policy is not None
        else None
    )
    eligible_hedge_instruments_payload = (
        eligible_hedge_instruments.model_dump(mode="json", exclude_none=True)
        if eligible_hedge_instruments is not None
        else None
    )
    fx_forward_curve_payload = (
        fx_forward_curve.model_dump(mode="json", exclude_none=True)
        if fx_forward_curve is not None
        else None
    )
    source_hash = hash_canonical_payload(
        {
            "external_hedge_execution_readiness": readiness_payload,
            "external_currency_exposure": exposure_payload,
            "external_hedge_policy": hedge_policy_payload,
            "external_eligible_hedge_instruments": eligible_hedge_instruments_payload,
            "external_fx_forward_curve": fx_forward_curve_payload,
        }
    )
    if hedge_readiness is not None:
        supportability_state = hedge_readiness.supportability.state
        supportability_reason = hedge_readiness.supportability.reason
        exposure_currencies = hedge_readiness.exposure_currencies
    elif currency_exposure is not None:
        supportability_state = currency_exposure.supportability.state
        supportability_reason = currency_exposure.supportability.reason
        exposure_currencies = currency_exposure.exposure_currencies
    elif hedge_policy is not None:
        supportability_state = hedge_policy.supportability.state
        supportability_reason = hedge_policy.supportability.reason
        exposure_currencies = hedge_policy.exposure_currencies
    elif eligible_hedge_instruments is not None:
        supportability_state = eligible_hedge_instruments.supportability.state
        supportability_reason = eligible_hedge_instruments.supportability.reason
        exposure_currencies = eligible_hedge_instruments.exposure_currencies
    else:
        assert fx_forward_curve is not None
        supportability_state = fx_forward_curve.supportability.state
        supportability_reason = fx_forward_curve.supportability.reason
        exposure_currencies = fx_forward_curve.exposure_currencies

    exposure_source_hash = (
        hash_canonical_payload(exposure_payload) if exposure_payload is not None else None
    )
    hedge_policy_source_hash = (
        hash_canonical_payload(hedge_policy_payload) if hedge_policy_payload is not None else None
    )
    eligible_hedge_instruments_source_hash = (
        hash_canonical_payload(eligible_hedge_instruments_payload)
        if eligible_hedge_instruments_payload is not None
        else None
    )
    fx_forward_curve_source_hash = (
        hash_canonical_payload(fx_forward_curve_payload)
        if fx_forward_curve_payload is not None
        else None
    )
    readiness_missing = (
        hedge_readiness.supportability.missing_data_families if hedge_readiness is not None else []
    )
    exposure_missing = (
        currency_exposure.supportability.missing_data_families
        if currency_exposure is not None
        else []
    )
    hedge_policy_missing = (
        hedge_policy.supportability.missing_data_families if hedge_policy is not None else []
    )
    eligible_hedge_instruments_missing = (
        eligible_hedge_instruments.supportability.missing_data_families
        if eligible_hedge_instruments is not None
        else []
    )
    fx_forward_curve_missing = (
        fx_forward_curve.supportability.missing_data_families
        if fx_forward_curve is not None
        else []
    )
    readiness_blocked = (
        hedge_readiness.supportability.blocked_capabilities if hedge_readiness is not None else []
    )
    exposure_blocked = (
        currency_exposure.supportability.blocked_capabilities
        if currency_exposure is not None
        else []
    )
    hedge_policy_blocked = (
        hedge_policy.supportability.blocked_capabilities if hedge_policy is not None else []
    )
    eligible_hedge_instruments_blocked = (
        eligible_hedge_instruments.supportability.blocked_capabilities
        if eligible_hedge_instruments is not None
        else []
    )
    fx_forward_curve_blocked = (
        fx_forward_curve.supportability.blocked_capabilities if fx_forward_curve is not None else []
    )
    reason_codes: list[str] = [supportability_reason]
    if hedge_readiness is not None:
        reason_codes.append("EXTERNAL_HEDGE_EXECUTION_READINESS_FAIL_CLOSED")
    if currency_exposure is not None:
        reason_codes.append("EXTERNAL_CURRENCY_EXPOSURE_FAIL_CLOSED")
    if hedge_policy is not None:
        reason_codes.append("EXTERNAL_HEDGE_POLICY_FAIL_CLOSED")
    if eligible_hedge_instruments is not None:
        reason_codes.append("EXTERNAL_ELIGIBLE_HEDGE_INSTRUMENTS_FAIL_CLOSED")
    if fx_forward_curve is not None:
        reason_codes.append("EXTERNAL_FX_FORWARD_CURVE_FAIL_CLOSED")

    return AuthoritativeCurrencyOverlayContext(
        supportability_status=source_status_to_method_status(supportability_state),
        source_system="lotus-core",
        policy_id="external-hedge-execution-readiness.v1",
        hedge_ratio_min=Decimal("0.00"),
        hedge_ratio_max=Decimal("0.00"),
        eligible_currencies=exposure_currencies,
        source_product_name=hedge_readiness.product_name if hedge_readiness is not None else None,
        source_product_version=(
            hedge_readiness.product_version if hedge_readiness is not None else None
        ),
        source_id=(
            hedge_readiness.source_batch_fingerprint
            or hedge_readiness.lineage.get("source_batch_fingerprint")
            or source_hash
            if hedge_readiness is not None
            else source_hash
        ),
        content_hash=source_hash,
        missing_data_families=sorted(
            {
                *readiness_missing,
                *exposure_missing,
                *hedge_policy_missing,
                *eligible_hedge_instruments_missing,
                *fx_forward_curve_missing,
            }
        ),
        blocked_capabilities=sorted(
            {
                *readiness_blocked,
                *exposure_blocked,
                *hedge_policy_blocked,
                *eligible_hedge_instruments_blocked,
                *fx_forward_curve_blocked,
            }
        ),
        readiness_checks=hedge_readiness.readiness_checks if hedge_readiness is not None else [],
        external_currency_exposure_source_product_name=(
            currency_exposure.product_name if currency_exposure is not None else None
        ),
        external_currency_exposure_source_product_version=(
            currency_exposure.product_version if currency_exposure is not None else None
        ),
        external_currency_exposure_source_id=(
            currency_exposure.source_batch_fingerprint
            or currency_exposure.lineage.get("source_batch_fingerprint")
            or exposure_source_hash
            if currency_exposure is not None
            else None
        ),
        external_currency_exposure_content_hash=exposure_source_hash,
        external_currency_exposure_count=(
            currency_exposure.supportability.exposure_count if currency_exposure is not None else 0
        ),
        external_currency_exposure_rows=(
            currency_exposure.exposures if currency_exposure is not None else []
        ),
        external_hedge_policy_source_product_name=(
            hedge_policy.product_name if hedge_policy is not None else None
        ),
        external_hedge_policy_source_product_version=(
            hedge_policy.product_version if hedge_policy is not None else None
        ),
        external_hedge_policy_source_id=(
            hedge_policy.source_batch_fingerprint
            or hedge_policy.lineage.get("source_batch_fingerprint")
            or hedge_policy_source_hash
            if hedge_policy is not None
            else None
        ),
        external_hedge_policy_content_hash=hedge_policy_source_hash,
        external_hedge_policy_rule_count=(
            hedge_policy.supportability.policy_rule_count if hedge_policy is not None else 0
        ),
        external_hedge_policy_rules=(hedge_policy.policy_rules if hedge_policy is not None else []),
        external_eligible_hedge_instrument_source_product_name=(
            eligible_hedge_instruments.product_name
            if eligible_hedge_instruments is not None
            else None
        ),
        external_eligible_hedge_instrument_source_product_version=(
            eligible_hedge_instruments.product_version
            if eligible_hedge_instruments is not None
            else None
        ),
        external_eligible_hedge_instrument_source_id=(
            eligible_hedge_instruments.source_batch_fingerprint
            or eligible_hedge_instruments.lineage.get("source_batch_fingerprint")
            or eligible_hedge_instruments_source_hash
            if eligible_hedge_instruments is not None
            else None
        ),
        external_eligible_hedge_instrument_content_hash=(eligible_hedge_instruments_source_hash),
        external_eligible_hedge_instrument_count=(
            eligible_hedge_instruments.supportability.instrument_count
            if eligible_hedge_instruments is not None
            else 0
        ),
        external_eligible_hedge_instruments=(
            eligible_hedge_instruments.eligible_instruments
            if eligible_hedge_instruments is not None
            else []
        ),
        external_fx_forward_curve_source_product_name=(
            fx_forward_curve.product_name if fx_forward_curve is not None else None
        ),
        external_fx_forward_curve_source_product_version=(
            fx_forward_curve.product_version if fx_forward_curve is not None else None
        ),
        external_fx_forward_curve_source_id=(
            fx_forward_curve.source_batch_fingerprint
            or fx_forward_curve.lineage.get("source_batch_fingerprint")
            or fx_forward_curve_source_hash
            if fx_forward_curve is not None
            else None
        ),
        external_fx_forward_curve_content_hash=fx_forward_curve_source_hash,
        external_fx_forward_curve_point_count=(
            fx_forward_curve.supportability.curve_point_count if fx_forward_curve is not None else 0
        ),
        external_fx_forward_curve_points=(
            fx_forward_curve.curve_points if fx_forward_curve is not None else []
        ),
        reason_codes=reason_codes,
    )


def client_restriction_profile_context(
    restriction_profile: DpmCoreClientRestrictionProfileResponse,
) -> AuthoritativeClientRestrictionContext:
    payload = restriction_profile.model_dump(mode="json", exclude_none=True)
    source_hash = hash_canonical_payload(payload)
    return AuthoritativeClientRestrictionContext(
        supportability_status=source_status_to_method_status(
            restriction_profile.supportability.state
        ),
        source_system="lotus-core",
        source_product_name=restriction_profile.product_name,
        source_product_version=restriction_profile.product_version,
        source_id=restriction_profile.source_batch_fingerprint
        or restriction_profile.lineage.get("source_batch_fingerprint")
        or source_hash,
        content_hash=source_hash,
        portfolio_id=restriction_profile.portfolio_id,
        client_id=restriction_profile.client_id,
        mandate_id=restriction_profile.mandate_id,
        as_of_date=restriction_profile.as_of_date,
        restriction_count=restriction_profile.supportability.restriction_count,
        missing_data_families=restriction_profile.supportability.missing_data_families,
        restrictions=[
            AuthoritativeClientRestrictionRule.model_validate(rule.model_dump(mode="python"))
            for rule in restriction_profile.restrictions
        ],
        reason_codes=[restriction_profile.supportability.reason],
    )


def sustainability_preference_profile_context(
    sustainability_profile: DpmCoreSustainabilityPreferenceProfileResponse,
) -> AuthoritativeSustainabilityPreferenceContext:
    payload = sustainability_profile.model_dump(mode="json", exclude_none=True)
    source_hash = hash_canonical_payload(payload)
    return AuthoritativeSustainabilityPreferenceContext(
        supportability_status=source_status_to_method_status(
            sustainability_profile.supportability.state
        ),
        source_system="lotus-core",
        source_product_name=sustainability_profile.product_name,
        source_product_version=sustainability_profile.product_version,
        source_id=sustainability_profile.source_batch_fingerprint
        or sustainability_profile.lineage.get("source_batch_fingerprint")
        or source_hash,
        content_hash=source_hash,
        portfolio_id=sustainability_profile.portfolio_id,
        client_id=sustainability_profile.client_id,
        mandate_id=sustainability_profile.mandate_id,
        as_of_date=sustainability_profile.as_of_date,
        preference_count=sustainability_profile.supportability.preference_count,
        missing_data_families=sustainability_profile.supportability.missing_data_families,
        preferences=[
            AuthoritativeSustainabilityPreference.model_validate(
                preference.model_dump(mode="python")
            )
            for preference in sustainability_profile.preferences
        ],
        reason_codes=[sustainability_profile.supportability.reason],
    )


def external_order_execution_acknowledgement_context(
    acknowledgement: DpmCoreExternalOrderExecutionAcknowledgementResponse | None,
) -> AuthoritativeExecutionAcknowledgementContext | None:
    if acknowledgement is None:
        return None
    payload = acknowledgement.model_dump(mode="json", exclude_none=True)
    source_hash = hash_canonical_payload(payload)
    return AuthoritativeExecutionAcknowledgementContext(
        supportability_status=source_status_to_method_status(acknowledgement.supportability.state),
        source_system="lotus-core",
        source_product_name=acknowledgement.product_name,
        source_product_version=acknowledgement.product_version,
        source_id=(
            acknowledgement.source_batch_fingerprint
            or acknowledgement.lineage.get("source_batch_fingerprint")
            or source_hash
        ),
        content_hash=source_hash,
        acknowledgement_count=acknowledgement.supportability.acknowledgement_count,
        missing_data_families=acknowledgement.supportability.missing_data_families,
        blocked_capabilities=acknowledgement.supportability.blocked_capabilities,
        acknowledgements=acknowledgement.acknowledgements,
        reason_codes=[
            acknowledgement.supportability.reason,
            "EXTERNAL_ORDER_EXECUTION_ACKNOWLEDGEMENT_FAIL_CLOSED",
        ],
    )


def source_product_authority_context_updates(
    *,
    source_context: DpmCoreExecutionContext,
    authority_context: ConstructionAuthorityContext,
) -> dict[str, object]:
    context_updates: dict[str, object] = {}
    if authority_context.transaction_cost_context is None:
        curve = getattr(source_context, "transaction_cost_curve", None)
        if curve is not None:
            context_updates["transaction_cost_context"] = transaction_cost_context_from_curve(curve)
    if authority_context.liquidity_context is None:
        liquidity_context = source_liquidity_context(
            cashflow_projection=getattr(source_context, "portfolio_cashflow_projection", None),
            income_needs=getattr(source_context, "client_income_needs_schedule", None),
            reserve_requirement=getattr(source_context, "liquidity_reserve_requirement", None),
            planned_withdrawals=getattr(source_context, "planned_withdrawal_schedule", None),
        )
        if liquidity_context is not None:
            context_updates["liquidity_context"] = liquidity_context
    if authority_context.currency_overlay_context is None:
        currency_context = external_treasury_currency_overlay_context(
            hedge_readiness=getattr(source_context, "external_hedge_execution_readiness", None),
            currency_exposure=getattr(source_context, "external_currency_exposure", None),
            hedge_policy=getattr(source_context, "external_hedge_policy", None),
            eligible_hedge_instruments=getattr(
                source_context, "external_eligible_hedge_instruments", None
            ),
            fx_forward_curve=getattr(source_context, "external_fx_forward_curve", None),
        )
        if currency_context is not None:
            context_updates["currency_overlay_context"] = currency_context
    if authority_context.execution_acknowledgement_context is None:
        acknowledgement_context = external_order_execution_acknowledgement_context(
            getattr(source_context, "external_order_execution_acknowledgement", None)
        )
        if acknowledgement_context is not None:
            context_updates["execution_acknowledgement_context"] = acknowledgement_context
    if authority_context.client_restriction_context is None:
        restriction_profile = getattr(source_context, "client_restriction_profile", None)
        if restriction_profile is not None:
            context_updates["client_restriction_context"] = client_restriction_profile_context(
                restriction_profile
            )
    if authority_context.sustainability_preference_context is None:
        sustainability_profile = getattr(source_context, "sustainability_preference_profile", None)
        if sustainability_profile is not None:
            context_updates["sustainability_preference_context"] = (
                sustainability_preference_profile_context(sustainability_profile)
            )
    return context_updates


def source_status_to_method_status(status: str) -> ConstructionMethodStatus:
    if status == "READY":
        return ConstructionMethodStatus.READY
    if status == "DEGRADED":
        return ConstructionMethodStatus.DEGRADED
    return ConstructionMethodStatus.BLOCKED


__all__ = [
    "client_restriction_profile_context",
    "external_order_execution_acknowledgement_context",
    "external_treasury_currency_overlay_context",
    "client_income_needs_schedule_context",
    "liquidity_cashflow_projection_context",
    "liquidity_reserve_requirement_context",
    "planned_withdrawal_schedule_context",
    "source_status_to_method_status",
    "source_liquidity_context",
    "source_product_authority_context_updates",
    "sustainability_preference_profile_context",
    "transaction_cost_context_from_curve",
]
