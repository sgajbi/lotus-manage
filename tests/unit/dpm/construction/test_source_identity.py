from pydantic import BaseModel

from src.api.services.construction_source_identity import (
    response_source_id,
    source_hash,
    source_payload,
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
