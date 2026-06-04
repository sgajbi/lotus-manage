from typing import Any

from src.api.services import construction_treasury_source_context
from src.api.services.construction_treasury_source_context import (
    TreasuryPrimarySupportability,
    external_treasury_currency_overlay_context,
    treasury_fail_closed_reason_codes,
    treasury_optional_source_identity,
    treasury_primary_supportability,
    treasury_source_identity_fields,
    treasury_source_payloads,
)
from src.core.common.canonical import hash_canonical_payload
from src.core.construction.vocabulary import ConstructionMethodStatus
from tests.unit.dpm.construction.source_product_context_fixtures import (
    currency_exposure_response,
    eligible_hedge_instruments_response,
    fx_forward_curve_response,
    hedge_policy_response,
    hedge_readiness_response,
)


def test_treasury_source_context_exports_only_currency_overlay_mapper() -> None:
    assert construction_treasury_source_context.__all__ == [
        "TreasuryPrimarySupportability",
        "external_treasury_currency_overlay_context",
        "treasury_fail_closed_reason_codes",
        "treasury_optional_source_identity",
        "treasury_primary_supportability",
        "treasury_source_identity_fields",
        "treasury_source_payloads",
    ]


def _without_source_lineage(response: Any) -> Any:
    return response.model_copy(
        update={
            "source_batch_fingerprint": None,
            "lineage": {},
        }
    )


def test_treasury_source_payloads_preserve_aggregate_hash_inputs() -> None:
    hedge_readiness = hedge_readiness_response()
    currency_exposure = currency_exposure_response()

    payloads = treasury_source_payloads(
        hedge_readiness=hedge_readiness,
        currency_exposure=currency_exposure,
        hedge_policy=None,
        eligible_hedge_instruments=None,
        fx_forward_curve=None,
    )

    assert payloads["external_hedge_execution_readiness"] == hedge_readiness.model_dump(
        mode="json",
        exclude_none=True,
    )
    assert payloads["external_currency_exposure"] == currency_exposure.model_dump(
        mode="json",
        exclude_none=True,
    )
    assert payloads["external_hedge_policy"] is None
    assert hash_canonical_payload(payloads)


def test_primary_treasury_supportability_uses_first_available_source_family() -> None:
    primary = treasury_primary_supportability(
        hedge_readiness=None,
        currency_exposure=currency_exposure_response(),
        hedge_policy=hedge_policy_response(),
        eligible_hedge_instruments=None,
        fx_forward_curve=None,
    )

    assert primary is not None
    assert isinstance(primary, TreasuryPrimarySupportability)
    assert primary.state == "UNAVAILABLE"
    assert primary.reason == "EXTERNAL_TREASURY_SOURCE_NOT_INGESTED"
    assert primary.exposure_currencies == ["EUR", "JPY"]


def test_source_identity_fields_project_prefixed_source_product_identity() -> None:
    identity = treasury_optional_source_identity(currency_exposure_response())

    assert identity is not None
    assert treasury_source_identity_fields(
        prefix="external_currency_exposure",
        identity=identity,
    ) == {
        "external_currency_exposure_source_product_name": "ExternalCurrencyExposure",
        "external_currency_exposure_source_product_version": "v1",
        "external_currency_exposure_source_id": "core-currency-exposure",
        "external_currency_exposure_content_hash": identity.content_hash,
    }


def test_source_identity_fields_project_absent_identity_as_nulls() -> None:
    assert treasury_source_identity_fields(
        prefix="external_currency_exposure",
        identity=None,
    ) == {
        "external_currency_exposure_source_product_name": None,
        "external_currency_exposure_source_product_version": None,
        "external_currency_exposure_source_id": None,
        "external_currency_exposure_content_hash": None,
    }


def test_treasury_fail_closed_reason_codes_include_present_source_families() -> None:
    assert treasury_fail_closed_reason_codes(
        primary_reason="EXTERNAL_TREASURY_SOURCE_NOT_INGESTED",
        hedge_readiness=hedge_readiness_response(),
        currency_exposure=currency_exposure_response(),
        hedge_policy=None,
        eligible_hedge_instruments=eligible_hedge_instruments_response(),
        fx_forward_curve=None,
    ) == [
        "EXTERNAL_TREASURY_SOURCE_NOT_INGESTED",
        "EXTERNAL_HEDGE_EXECUTION_READINESS_FAIL_CLOSED",
        "EXTERNAL_CURRENCY_EXPOSURE_FAIL_CLOSED",
        "EXTERNAL_ELIGIBLE_HEDGE_INSTRUMENTS_FAIL_CLOSED",
    ]


def test_external_treasury_currency_overlay_context_preserves_fail_closed_readiness() -> None:
    context = external_treasury_currency_overlay_context(
        hedge_readiness=hedge_readiness_response(),
        currency_exposure=None,
        hedge_policy=None,
        eligible_hedge_instruments=None,
        fx_forward_curve=None,
    )

    assert context is not None
    assert context.supportability_status == ConstructionMethodStatus.BLOCKED
    assert context.source_system == "lotus-core"
    assert context.source_product_name == "ExternalHedgeExecutionReadiness"
    assert context.source_id == "core-hedge-readiness"
    assert context.eligible_currencies == ["EUR", "GBP"]
    assert context.hedge_ratio_min == 0
    assert context.hedge_ratio_max == 0
    assert context.missing_data_families == ["external_treasury_hedge_readiness"]
    assert context.blocked_capabilities == ["execution", "oms", "treasury"]
    assert context.reason_codes == [
        "EXTERNAL_TREASURY_SOURCE_NOT_INGESTED",
        "EXTERNAL_HEDGE_EXECUTION_READINESS_FAIL_CLOSED",
    ]


def test_external_treasury_currency_overlay_context_preserves_exposure_fallback() -> None:
    context = external_treasury_currency_overlay_context(
        hedge_readiness=None,
        currency_exposure=currency_exposure_response(),
        hedge_policy=None,
        eligible_hedge_instruments=None,
        fx_forward_curve=None,
    )

    assert context is not None
    assert context.supportability_status == ConstructionMethodStatus.BLOCKED
    assert context.source_product_name is None
    assert context.source_id
    assert context.eligible_currencies == ["EUR", "JPY"]
    assert context.external_currency_exposure_source_id == "core-currency-exposure"
    assert context.external_currency_exposure_count == 1
    assert context.external_currency_exposure_rows == [
        {"currency": "EUR", "net_exposure": "125000"}
    ]
    assert context.reason_codes == [
        "EXTERNAL_TREASURY_SOURCE_NOT_INGESTED",
        "EXTERNAL_CURRENCY_EXPOSURE_FAIL_CLOSED",
    ]


def test_external_treasury_currency_overlay_context_combines_source_family_evidence() -> None:
    context = external_treasury_currency_overlay_context(
        hedge_readiness=hedge_readiness_response(),
        currency_exposure=currency_exposure_response(),
        hedge_policy=hedge_policy_response(),
        eligible_hedge_instruments=eligible_hedge_instruments_response(),
        fx_forward_curve=fx_forward_curve_response(),
    )

    assert context is not None
    assert context.source_id == "core-hedge-readiness"
    assert context.external_currency_exposure_source_id == "core-currency-exposure"
    assert context.external_hedge_policy_source_id == "core-hedge-policy"
    assert context.external_eligible_hedge_instrument_source_id == "core-eligible-hedges"
    assert context.external_fx_forward_curve_source_id == "core-fx-forward-curve"
    assert context.missing_data_families == [
        "external_currency_exposure",
        "external_eligible_hedge_instruments",
        "external_fx_forward_curve",
        "external_hedge_policy",
        "external_treasury_hedge_readiness",
    ]
    assert context.blocked_capabilities == [
        "eligible-instrument",
        "execution",
        "forward-pricing",
        "fx",
        "hedge-policy",
        "oms",
        "suitability",
        "treasury",
    ]
    assert context.reason_codes == [
        "EXTERNAL_TREASURY_SOURCE_NOT_INGESTED",
        "EXTERNAL_HEDGE_EXECUTION_READINESS_FAIL_CLOSED",
        "EXTERNAL_CURRENCY_EXPOSURE_FAIL_CLOSED",
        "EXTERNAL_HEDGE_POLICY_FAIL_CLOSED",
        "EXTERNAL_ELIGIBLE_HEDGE_INSTRUMENTS_FAIL_CLOSED",
        "EXTERNAL_FX_FORWARD_CURVE_FAIL_CLOSED",
    ]


def test_external_treasury_currency_overlay_context_falls_back_to_content_hash_source_ids() -> None:
    hedge_readiness = _without_source_lineage(hedge_readiness_response())
    currency_exposure = _without_source_lineage(currency_exposure_response())
    hedge_policy = _without_source_lineage(hedge_policy_response())
    eligible_hedge_instruments = _without_source_lineage(eligible_hedge_instruments_response())
    fx_forward_curve = _without_source_lineage(fx_forward_curve_response())
    readiness_payload = hedge_readiness.model_dump(mode="json", exclude_none=True)
    exposure_payload = currency_exposure.model_dump(mode="json", exclude_none=True)
    hedge_policy_payload = hedge_policy.model_dump(mode="json", exclude_none=True)
    eligible_payload = eligible_hedge_instruments.model_dump(
        mode="json",
        exclude_none=True,
    )
    fx_forward_curve_payload = fx_forward_curve.model_dump(mode="json", exclude_none=True)
    expected_aggregate_hash = hash_canonical_payload(
        {
            "external_hedge_execution_readiness": readiness_payload,
            "external_currency_exposure": exposure_payload,
            "external_hedge_policy": hedge_policy_payload,
            "external_eligible_hedge_instruments": eligible_payload,
            "external_fx_forward_curve": fx_forward_curve_payload,
        }
    )

    context = external_treasury_currency_overlay_context(
        hedge_readiness=hedge_readiness,
        currency_exposure=currency_exposure,
        hedge_policy=hedge_policy,
        eligible_hedge_instruments=eligible_hedge_instruments,
        fx_forward_curve=fx_forward_curve,
    )

    assert context is not None
    assert context.source_id == expected_aggregate_hash
    assert context.external_currency_exposure_source_id == hash_canonical_payload(exposure_payload)
    assert context.external_hedge_policy_source_id == hash_canonical_payload(hedge_policy_payload)
    assert context.external_eligible_hedge_instrument_source_id == hash_canonical_payload(
        eligible_payload
    )
    assert context.external_fx_forward_curve_source_id == hash_canonical_payload(
        fx_forward_curve_payload
    )


def test_external_treasury_currency_overlay_context_absent_without_source_response() -> None:
    assert (
        external_treasury_currency_overlay_context(
            hedge_readiness=None,
            currency_exposure=None,
            hedge_policy=None,
            eligible_hedge_instruments=None,
            fx_forward_curve=None,
        )
        is None
    )
