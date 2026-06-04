from pydantic import BaseModel

from src.api.services.construction_source_identity import (
    SourceProductIdentity,
    response_lineage_source_id,
    response_source_id,
    source_hash,
    source_payload,
    source_product_identity,
)
from src.core.common.canonical import hash_canonical_payload
from tests.unit.dpm.construction.source_product_context_fixtures import (
    client_income_needs_schedule_response,
)


class _MinimalSourceResponse(BaseModel):
    source_batch_fingerprint: str | None = None
    lineage: dict[str, str] = {}


def test_source_payload_and_hash_use_canonical_json_payload() -> None:
    response = client_income_needs_schedule_response()

    payload = source_payload(response)

    assert payload == response.model_dump(mode="json", exclude_none=True)
    assert source_hash(payload) == hash_canonical_payload(payload)


def test_response_source_id_prefers_top_level_fingerprint() -> None:
    response = _MinimalSourceResponse(
        source_batch_fingerprint="top-level-fingerprint",
        lineage={"source_batch_fingerprint": "lineage-fingerprint"},
    )

    assert response_source_id(response, "sha256:fallback") == "top-level-fingerprint"


def test_response_source_id_falls_back_to_lineage_then_hash() -> None:
    assert (
        response_source_id(
            _MinimalSourceResponse(lineage={"source_batch_fingerprint": "lineage-fingerprint"}),
            "sha256:fallback",
        )
        == "lineage-fingerprint"
    )
    assert response_source_id(_MinimalSourceResponse(), "sha256:fallback") == "sha256:fallback"


def test_response_lineage_source_id_returns_only_valid_lineage_fingerprint() -> None:
    assert (
        response_lineage_source_id(
            _MinimalSourceResponse(lineage={"source_batch_fingerprint": "lineage-fingerprint"})
        )
        == "lineage-fingerprint"
    )
    assert response_lineage_source_id(_MinimalSourceResponse()) is None
    assert (
        response_lineage_source_id(
            _MinimalSourceResponse.model_construct(lineage={"source_batch_fingerprint": ""})
        )
        is None
    )


def test_source_product_identity_bundles_product_and_lineage_fields() -> None:
    response = client_income_needs_schedule_response()
    expected_payload = response.model_dump(mode="json", exclude_none=True)
    expected_hash = hash_canonical_payload(expected_payload)

    identity = source_product_identity(response)

    assert identity == SourceProductIdentity(
        source_product_name="ClientIncomeNeedsSchedule",
        source_product_version=response.product_version,
        source_system="lotus-core",
        source_id="income-lineage",
        content_hash=expected_hash,
    )


def test_source_product_identity_uses_explicit_fallback_when_lineage_is_absent() -> None:
    response = client_income_needs_schedule_response().model_copy(
        update={"source_batch_fingerprint": None, "lineage": {}}
    )

    identity = source_product_identity(response, fallback_source_id="page-fingerprint")

    assert identity.source_id == "page-fingerprint"
