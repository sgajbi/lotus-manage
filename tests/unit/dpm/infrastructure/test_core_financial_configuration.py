"""Deployment pins are exact, closed and incapable of selecting source authority."""

import json

import pytest
from pydantic import ValidationError

from src.core.common.canonical import hash_canonical_payload
from src.infrastructure.composites.core_financial_configuration import CoreFinancialConfiguration
from src.infrastructure.composites.core_financial_configuration import CoreReaderConfiguration

H = "sha256:" + "1" * 64


@pytest.mark.parametrize(
    "endpoint",
    [
        "http://core.example",
        "https://user:secret@core.example",
        "https://core.example?tenant=other",
        "https://core.example/path",
        "https://core.example#fragment",
    ],
)
def test_native_transport_is_deployment_pinned(endpoint):
    with pytest.raises(ValueError):
        CoreReaderConfiguration(
            tenant_id="tenant", endpoint=endpoint, credential_env="CORE_NATIVE_TEST_TOKEN"
        )


def test_native_transport_credentials_and_authority_are_not_retained_values():
    config = CoreReaderConfiguration(
        tenant_id="tenant", endpoint="https://core.example", credential_env="CORE_NATIVE_TEST_TOKEN"
    )
    assert "keys" not in config.model_dump()
    assert "credential" not in config.model_dump()
    assert CoreReaderConfiguration(
        tenant_id="tenant",
        endpoint="http://127.0.0.1:8200",
        credential_env="CORE_NATIVE_TEST_TOKEN",
        allow_local_http=True,
    )


@pytest.mark.parametrize("mode", ["bearer", "core_enterprise_hmac_v1"])
def test_reader_authentication_mode_is_explicit_serialized_public_configuration(mode):
    configuration = CoreReaderConfiguration(
        tenant_id="tenant",
        endpoint="https://core.example",
        credential_env="CORE_NATIVE_TEST_TOKEN",
        authentication_mode=mode,
    )
    document = json.loads(configuration.model_dump_json())
    assert document["authentication_mode"] == mode
    assert CoreReaderConfiguration.model_validate_json(json.dumps(document)) == configuration
    default_document = CoreReaderConfiguration(
        tenant_id="tenant", endpoint="https://core.example", credential_env="CORE_NATIVE_TEST_TOKEN"
    ).model_dump(mode="json")
    assert default_document["authentication_mode"] == "bearer"
    assert {key: value for key, value in document.items() if key != "authentication_mode"} == {
        key: value for key, value in default_document.items() if key != "authentication_mode"
    }
    assert (hash_canonical_payload(document) == hash_canonical_payload(default_document)) == (
        mode == "bearer"
    )


@pytest.mark.parametrize("mode", [None, "", "hmac", "BEARER", True, 1])
def test_reader_authentication_mode_refuses_unknown_or_coerced_values(mode):
    with pytest.raises(ValidationError, match="authentication_mode"):
        CoreReaderConfiguration.model_validate_json(
            json.dumps(
                {
                    "tenant_id": "tenant",
                    "endpoint": "https://core.example",
                    "credential_env": "CORE_NATIVE_TEST_TOKEN",
                    "authentication_mode": mode,
                }
            )
        )


def configuration() -> CoreFinancialConfiguration:
    address = dict(
        source_system="producer/opaque",
        registry_scope_id="scope/opaque",
        source_cut_id="registry-cut",
        revision=1,
        content_hash=H,
    )
    return CoreFinancialConfiguration.model_validate_json(
        json.dumps(
            dict(
                tenant_id="tenant",
                composite_id="composite",
                definition_version="v1",
                strategy_code="strategy",
                month="2026-09",
                reporting_currency="SGD",
                registry=address,
                observation_cut_id="normalized-cut",
                observation_revision="1",
                members=[
                    dict(
                        portfolio_id=f"P{index}",
                        provider_namespace="native",
                        source_member_id=f"member{index}",
                        provider_id="core-provider",
                        financial_cut={**address, "source_cut_id": f"financial{index}"},
                    )
                    for index in range(1, 4)
                ],
            )
        )
    )


@pytest.mark.parametrize(
    "field", ["endpoint", "tenant", "key", "credential", "posture", "approval"]
)
def test_configuration_cannot_nominate_transport_or_authority(field):
    payload = configuration().model_dump(mode="json")
    payload[field] = "caller-selected"
    with pytest.raises(ValidationError, match="extra_forbidden"):
        CoreFinancialConfiguration.model_validate_json(json.dumps(payload))


@pytest.mark.parametrize("revision", [True, 0, -1, 1.0, "1"])
def test_exact_positive_revision_never_coerces(revision):
    payload = configuration().model_dump(mode="json")
    payload["registry"]["revision"] = revision
    with pytest.raises(ValidationError):
        CoreFinancialConfiguration.model_validate_json(json.dumps(payload))


def test_opaque_custody_address_is_preserved_but_portfolio_identity_is_not_rewritten():
    original = configuration()
    assert original.registry.source_system == "producer/opaque"
    payload = original.model_dump(mode="json")
    payload["members"][0]["portfolio_id"] = "portfolio/opaque"
    with pytest.raises(ValidationError):
        CoreFinancialConfiguration.model_validate_json(json.dumps(payload))
    payload = original.model_dump(mode="json")
    payload["registry"]["source_system"] = " producer"
    with pytest.raises(ValidationError, match="IDENTITY_INVALID"):
        CoreFinancialConfiguration.model_validate_json(json.dumps(payload))


@pytest.mark.parametrize("mutation", ["order", "portfolio", "source_member", "cap"])
def test_population_mapping_is_unique_canonical_and_bounded(mutation):
    payload = configuration().model_dump(mode="json")
    if mutation == "order":
        payload["members"].reverse()
    elif mutation == "portfolio":
        payload["members"][1]["portfolio_id"] = "P1"
    elif mutation == "source_member":
        payload["members"][1]["source_member_id"] = "member1"
    else:
        payload["members"] = payload["members"] * 334
    with pytest.raises(ValidationError):
        CoreFinancialConfiguration.model_validate_json(json.dumps(payload))


@pytest.mark.parametrize("month", ["2026-13", "2026-9", "2026-09-01"])
def test_month_is_an_exact_business_month(month):
    payload = configuration().model_dump(mode="json")
    payload["month"] = month
    with pytest.raises(ValidationError):
        CoreFinancialConfiguration.model_validate_json(json.dumps(payload))
