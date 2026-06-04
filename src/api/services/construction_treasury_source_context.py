from decimal import Decimal
from typing import NamedTuple, TypeAlias

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


def treasury_source_payload(response: _TreasurySourceResponse | None) -> JsonPayload | None:
    return source_payload(response) if response is not None else None


def treasury_source_payloads(
    *,
    hedge_readiness: DpmCoreExternalHedgeExecutionReadinessResponse | None,
    currency_exposure: DpmCoreExternalCurrencyExposureResponse | None,
    hedge_policy: DpmCoreExternalHedgePolicyResponse | None,
    eligible_hedge_instruments: DpmCoreExternalEligibleHedgeInstrumentResponse | None,
    fx_forward_curve: DpmCoreExternalFXForwardCurveResponse | None,
) -> dict[str, JsonPayload | None]:
    return {
        "external_hedge_execution_readiness": treasury_source_payload(hedge_readiness),
        "external_currency_exposure": treasury_source_payload(currency_exposure),
        "external_hedge_policy": treasury_source_payload(hedge_policy),
        "external_eligible_hedge_instruments": treasury_source_payload(eligible_hedge_instruments),
        "external_fx_forward_curve": treasury_source_payload(fx_forward_curve),
    }


def treasury_optional_source_identity(
    response: _TreasurySourceResponse | None,
    fallback_source_id: str | None = None,
) -> SourceProductIdentity | None:
    if response is None:
        return None
    return source_product_identity(response, fallback_source_id=fallback_source_id)


def treasury_source_identity_fields(
    *,
    prefix: str,
    identity: SourceProductIdentity | None,
) -> dict[str, str | None]:
    return {
        f"{prefix}_source_product_name": (
            identity.source_product_name if identity is not None else None
        ),
        f"{prefix}_source_product_version": (
            identity.source_product_version if identity is not None else None
        ),
        f"{prefix}_source_id": identity.source_id if identity is not None else None,
        f"{prefix}_content_hash": identity.content_hash if identity is not None else None,
    }


def treasury_response_missing_data_families(
    response: _TreasurySourceResponse | None,
) -> list[str]:
    return response.supportability.missing_data_families if response is not None else []


def treasury_response_blocked_capabilities(
    response: _TreasurySourceResponse | None,
) -> list[str]:
    return response.supportability.blocked_capabilities if response is not None else []


def treasury_missing_data_families(
    *responses: _TreasurySourceResponse | None,
) -> list[str]:
    return sorted(
        {
            family
            for response in responses
            for family in treasury_response_missing_data_families(response)
        }
    )


def treasury_blocked_capabilities(
    *responses: _TreasurySourceResponse | None,
) -> list[str]:
    return sorted(
        {
            capability
            for response in responses
            for capability in treasury_response_blocked_capabilities(response)
        }
    )


def treasury_fail_closed_reason_codes(
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


class TreasuryPrimarySupportability(NamedTuple):
    state: str
    reason: str
    exposure_currencies: list[str]


class TreasurySourceIdentities(NamedTuple):
    readiness: SourceProductIdentity | None
    exposure: SourceProductIdentity | None
    hedge_policy: SourceProductIdentity | None
    eligible_hedge_instruments: SourceProductIdentity | None
    fx_forward_curve: SourceProductIdentity | None


def treasury_primary_supportability(
    *,
    hedge_readiness: DpmCoreExternalHedgeExecutionReadinessResponse | None,
    currency_exposure: DpmCoreExternalCurrencyExposureResponse | None,
    hedge_policy: DpmCoreExternalHedgePolicyResponse | None,
    eligible_hedge_instruments: DpmCoreExternalEligibleHedgeInstrumentResponse | None,
    fx_forward_curve: DpmCoreExternalFXForwardCurveResponse | None,
) -> TreasuryPrimarySupportability | None:
    for response in (
        hedge_readiness,
        currency_exposure,
        hedge_policy,
        eligible_hedge_instruments,
        fx_forward_curve,
    ):
        if response is not None:
            return TreasuryPrimarySupportability(
                state=response.supportability.state,
                reason=response.supportability.reason,
                exposure_currencies=response.exposure_currencies,
            )
    return None


def treasury_source_identities(
    *,
    source_hash: str,
    hedge_readiness: DpmCoreExternalHedgeExecutionReadinessResponse | None,
    currency_exposure: DpmCoreExternalCurrencyExposureResponse | None,
    hedge_policy: DpmCoreExternalHedgePolicyResponse | None,
    eligible_hedge_instruments: DpmCoreExternalEligibleHedgeInstrumentResponse | None,
    fx_forward_curve: DpmCoreExternalFXForwardCurveResponse | None,
) -> TreasurySourceIdentities:
    return TreasurySourceIdentities(
        readiness=treasury_optional_source_identity(hedge_readiness, source_hash),
        exposure=treasury_optional_source_identity(currency_exposure),
        hedge_policy=treasury_optional_source_identity(hedge_policy),
        eligible_hedge_instruments=treasury_optional_source_identity(eligible_hedge_instruments),
        fx_forward_curve=treasury_optional_source_identity(fx_forward_curve),
    )


def external_treasury_currency_overlay_context(
    *,
    hedge_readiness: DpmCoreExternalHedgeExecutionReadinessResponse | None,
    currency_exposure: DpmCoreExternalCurrencyExposureResponse | None,
    hedge_policy: DpmCoreExternalHedgePolicyResponse | None,
    eligible_hedge_instruments: DpmCoreExternalEligibleHedgeInstrumentResponse | None,
    fx_forward_curve: DpmCoreExternalFXForwardCurveResponse | None,
) -> AuthoritativeCurrencyOverlayContext | None:
    primary_supportability = treasury_primary_supportability(
        hedge_readiness=hedge_readiness,
        currency_exposure=currency_exposure,
        hedge_policy=hedge_policy,
        eligible_hedge_instruments=eligible_hedge_instruments,
        fx_forward_curve=fx_forward_curve,
    )
    if primary_supportability is None:
        return None

    source_hash = hash_canonical_payload(
        treasury_source_payloads(
            hedge_readiness=hedge_readiness,
            currency_exposure=currency_exposure,
            hedge_policy=hedge_policy,
            eligible_hedge_instruments=eligible_hedge_instruments,
            fx_forward_curve=fx_forward_curve,
        )
    )

    identities = treasury_source_identities(
        source_hash=source_hash,
        hedge_readiness=hedge_readiness,
        currency_exposure=currency_exposure,
        hedge_policy=hedge_policy,
        eligible_hedge_instruments=eligible_hedge_instruments,
        fx_forward_curve=fx_forward_curve,
    )
    reason_codes = treasury_fail_closed_reason_codes(
        primary_reason=primary_supportability.reason,
        hedge_readiness=hedge_readiness,
        currency_exposure=currency_exposure,
        hedge_policy=hedge_policy,
        eligible_hedge_instruments=eligible_hedge_instruments,
        fx_forward_curve=fx_forward_curve,
    )

    return AuthoritativeCurrencyOverlayContext(
        supportability_status=source_status_to_method_status(primary_supportability.state),
        source_system="lotus-core",
        policy_id="external-hedge-execution-readiness.v1",
        hedge_ratio_min=Decimal("0.00"),
        hedge_ratio_max=Decimal("0.00"),
        eligible_currencies=primary_supportability.exposure_currencies,
        source_product_name=(
            identities.readiness.source_product_name if identities.readiness is not None else None
        ),
        source_product_version=(
            identities.readiness.source_product_version
            if identities.readiness is not None
            else None
        ),
        source_id=identities.readiness.source_id
        if identities.readiness is not None
        else source_hash,
        content_hash=source_hash,
        missing_data_families=treasury_missing_data_families(
            hedge_readiness,
            currency_exposure,
            hedge_policy,
            eligible_hedge_instruments,
            fx_forward_curve,
        ),
        blocked_capabilities=treasury_blocked_capabilities(
            hedge_readiness,
            currency_exposure,
            hedge_policy,
            eligible_hedge_instruments,
            fx_forward_curve,
        ),
        readiness_checks=hedge_readiness.readiness_checks if hedge_readiness is not None else [],
        **treasury_source_identity_fields(
            prefix="external_currency_exposure",
            identity=identities.exposure,
        ),
        external_currency_exposure_count=(
            currency_exposure.supportability.exposure_count if currency_exposure is not None else 0
        ),
        external_currency_exposure_rows=(
            currency_exposure.exposures if currency_exposure is not None else []
        ),
        **treasury_source_identity_fields(
            prefix="external_hedge_policy",
            identity=identities.hedge_policy,
        ),
        external_hedge_policy_rule_count=(
            hedge_policy.supportability.policy_rule_count if hedge_policy is not None else 0
        ),
        external_hedge_policy_rules=(hedge_policy.policy_rules if hedge_policy is not None else []),
        **treasury_source_identity_fields(
            prefix="external_eligible_hedge_instrument",
            identity=identities.eligible_hedge_instruments,
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
        **treasury_source_identity_fields(
            prefix="external_fx_forward_curve",
            identity=identities.fx_forward_curve,
        ),
        external_fx_forward_curve_point_count=(
            fx_forward_curve.supportability.curve_point_count if fx_forward_curve is not None else 0
        ),
        external_fx_forward_curve_points=(
            fx_forward_curve.curve_points if fx_forward_curve is not None else []
        ),
        reason_codes=reason_codes,
    )


__all__ = [
    "TreasuryPrimarySupportability",
    "TreasurySourceIdentities",
    "external_treasury_currency_overlay_context",
    "treasury_blocked_capabilities",
    "treasury_fail_closed_reason_codes",
    "treasury_missing_data_families",
    "treasury_optional_source_identity",
    "treasury_primary_supportability",
    "treasury_response_blocked_capabilities",
    "treasury_response_missing_data_families",
    "treasury_source_identities",
    "treasury_source_identity_fields",
    "treasury_source_payload",
    "treasury_source_payloads",
]
