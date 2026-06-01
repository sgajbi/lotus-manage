from decimal import Decimal
from typing import TypeAlias

from src.api.services.construction_source_product_status import source_status_to_method_status
from src.api.services.construction_source_identity import (
    JsonPayload,
    SourceProductIdentity,
    source_product_identity,
    source_payload,
)
from src.core.common.canonical import hash_canonical_payload
from src.core.construction.models import AuthoritativeCurrencyOverlayContext
from src.core.dpm_source_context import (
    DpmCoreExternalCurrencyExposureResponse,
    DpmCoreExternalEligibleHedgeInstrumentResponse,
    DpmCoreExternalFXForwardCurveResponse,
    DpmCoreExternalHedgeExecutionReadinessResponse,
    DpmCoreExternalHedgePolicyResponse,
)

_TreasurySourceResponse: TypeAlias = (
    DpmCoreExternalHedgeExecutionReadinessResponse
    | DpmCoreExternalCurrencyExposureResponse
    | DpmCoreExternalHedgePolicyResponse
    | DpmCoreExternalEligibleHedgeInstrumentResponse
    | DpmCoreExternalFXForwardCurveResponse
)


def _optional_source_payload(response: _TreasurySourceResponse | None) -> JsonPayload | None:
    return source_payload(response) if response is not None else None


def _optional_source_identity(
    response: _TreasurySourceResponse | None,
    fallback_source_id: str | None = None,
) -> SourceProductIdentity | None:
    if response is None:
        return None
    return source_product_identity(response, fallback_source_id=fallback_source_id)


def _missing_data_families(response: _TreasurySourceResponse | None) -> list[str]:
    return response.supportability.missing_data_families if response is not None else []


def _blocked_capabilities(response: _TreasurySourceResponse | None) -> list[str]:
    return response.supportability.blocked_capabilities if response is not None else []


def _merged_missing_data_families(
    *responses: _TreasurySourceResponse | None,
) -> list[str]:
    return sorted({family for response in responses for family in _missing_data_families(response)})


def _merged_blocked_capabilities(
    *responses: _TreasurySourceResponse | None,
) -> list[str]:
    return sorted(
        {capability for response in responses for capability in _blocked_capabilities(response)}
    )


def _fail_closed_reason_codes(
    *,
    primary_reason: str,
    hedge_readiness: DpmCoreExternalHedgeExecutionReadinessResponse | None,
    currency_exposure: DpmCoreExternalCurrencyExposureResponse | None,
    hedge_policy: DpmCoreExternalHedgePolicyResponse | None,
    eligible_hedge_instruments: DpmCoreExternalEligibleHedgeInstrumentResponse | None,
    fx_forward_curve: DpmCoreExternalFXForwardCurveResponse | None,
) -> list[str]:
    reason_codes = [primary_reason]
    for response, reason_code in (
        (hedge_readiness, "EXTERNAL_HEDGE_EXECUTION_READINESS_FAIL_CLOSED"),
        (currency_exposure, "EXTERNAL_CURRENCY_EXPOSURE_FAIL_CLOSED"),
        (hedge_policy, "EXTERNAL_HEDGE_POLICY_FAIL_CLOSED"),
        (
            eligible_hedge_instruments,
            "EXTERNAL_ELIGIBLE_HEDGE_INSTRUMENTS_FAIL_CLOSED",
        ),
        (fx_forward_curve, "EXTERNAL_FX_FORWARD_CURVE_FAIL_CLOSED"),
    ):
        if response is not None:
            reason_codes.append(reason_code)
    return reason_codes


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

    readiness_payload = _optional_source_payload(hedge_readiness)
    exposure_payload = _optional_source_payload(currency_exposure)
    hedge_policy_payload = _optional_source_payload(hedge_policy)
    eligible_hedge_instruments_payload = _optional_source_payload(eligible_hedge_instruments)
    fx_forward_curve_payload = _optional_source_payload(fx_forward_curve)
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

    readiness_identity = _optional_source_identity(hedge_readiness, source_hash)
    exposure_identity = _optional_source_identity(currency_exposure)
    hedge_policy_identity = _optional_source_identity(hedge_policy)
    eligible_hedge_instruments_identity = _optional_source_identity(eligible_hedge_instruments)
    fx_forward_curve_identity = _optional_source_identity(fx_forward_curve)
    reason_codes = _fail_closed_reason_codes(
        primary_reason=supportability_reason,
        hedge_readiness=hedge_readiness,
        currency_exposure=currency_exposure,
        hedge_policy=hedge_policy,
        eligible_hedge_instruments=eligible_hedge_instruments,
        fx_forward_curve=fx_forward_curve,
    )

    return AuthoritativeCurrencyOverlayContext(
        supportability_status=source_status_to_method_status(supportability_state),
        source_system="lotus-core",
        policy_id="external-hedge-execution-readiness.v1",
        hedge_ratio_min=Decimal("0.00"),
        hedge_ratio_max=Decimal("0.00"),
        eligible_currencies=exposure_currencies,
        source_product_name=(
            readiness_identity.source_product_name if readiness_identity is not None else None
        ),
        source_product_version=(
            readiness_identity.source_product_version if readiness_identity is not None else None
        ),
        source_id=readiness_identity.source_id if readiness_identity is not None else source_hash,
        content_hash=source_hash,
        missing_data_families=_merged_missing_data_families(
            hedge_readiness,
            currency_exposure,
            hedge_policy,
            eligible_hedge_instruments,
            fx_forward_curve,
        ),
        blocked_capabilities=_merged_blocked_capabilities(
            hedge_readiness,
            currency_exposure,
            hedge_policy,
            eligible_hedge_instruments,
            fx_forward_curve,
        ),
        readiness_checks=hedge_readiness.readiness_checks if hedge_readiness is not None else [],
        external_currency_exposure_source_product_name=(
            exposure_identity.source_product_name if exposure_identity is not None else None
        ),
        external_currency_exposure_source_product_version=(
            exposure_identity.source_product_version if exposure_identity is not None else None
        ),
        external_currency_exposure_source_id=(
            exposure_identity.source_id if exposure_identity is not None else None
        ),
        external_currency_exposure_content_hash=(
            exposure_identity.content_hash if exposure_identity is not None else None
        ),
        external_currency_exposure_count=(
            currency_exposure.supportability.exposure_count if currency_exposure is not None else 0
        ),
        external_currency_exposure_rows=(
            currency_exposure.exposures if currency_exposure is not None else []
        ),
        external_hedge_policy_source_product_name=(
            hedge_policy_identity.source_product_name if hedge_policy_identity is not None else None
        ),
        external_hedge_policy_source_product_version=(
            hedge_policy_identity.source_product_version
            if hedge_policy_identity is not None
            else None
        ),
        external_hedge_policy_source_id=(
            hedge_policy_identity.source_id if hedge_policy_identity is not None else None
        ),
        external_hedge_policy_content_hash=(
            hedge_policy_identity.content_hash if hedge_policy_identity is not None else None
        ),
        external_hedge_policy_rule_count=(
            hedge_policy.supportability.policy_rule_count if hedge_policy is not None else 0
        ),
        external_hedge_policy_rules=(hedge_policy.policy_rules if hedge_policy is not None else []),
        external_eligible_hedge_instrument_source_product_name=(
            eligible_hedge_instruments_identity.source_product_name
            if eligible_hedge_instruments_identity is not None
            else None
        ),
        external_eligible_hedge_instrument_source_product_version=(
            eligible_hedge_instruments_identity.source_product_version
            if eligible_hedge_instruments_identity is not None
            else None
        ),
        external_eligible_hedge_instrument_source_id=(
            eligible_hedge_instruments_identity.source_id
            if eligible_hedge_instruments_identity is not None
            else None
        ),
        external_eligible_hedge_instrument_content_hash=(
            eligible_hedge_instruments_identity.content_hash
            if eligible_hedge_instruments_identity is not None
            else None
        ),
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
            fx_forward_curve_identity.source_product_name
            if fx_forward_curve_identity is not None
            else None
        ),
        external_fx_forward_curve_source_product_version=(
            fx_forward_curve_identity.source_product_version
            if fx_forward_curve_identity is not None
            else None
        ),
        external_fx_forward_curve_source_id=(
            fx_forward_curve_identity.source_id if fx_forward_curve_identity is not None else None
        ),
        external_fx_forward_curve_content_hash=(
            fx_forward_curve_identity.content_hash
            if fx_forward_curve_identity is not None
            else None
        ),
        external_fx_forward_curve_point_count=(
            fx_forward_curve.supportability.curve_point_count if fx_forward_curve is not None else 0
        ),
        external_fx_forward_curve_points=(
            fx_forward_curve.curve_points if fx_forward_curve is not None else []
        ),
        reason_codes=reason_codes,
    )


__all__ = ["external_treasury_currency_overlay_context"]
