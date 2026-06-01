from decimal import Decimal

from src.core.common.canonical import hash_canonical_payload
from src.api.services.construction_source_product_status import source_status_to_method_status
from src.core.construction.models import AuthoritativeCurrencyOverlayContext
from src.core.dpm_source_context import (
    DpmCoreExternalCurrencyExposureResponse,
    DpmCoreExternalEligibleHedgeInstrumentResponse,
    DpmCoreExternalFXForwardCurveResponse,
    DpmCoreExternalHedgeExecutionReadinessResponse,
    DpmCoreExternalHedgePolicyResponse,
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


__all__ = ["external_treasury_currency_overlay_context"]
