from decimal import Decimal

from src.api.services import construction_client_profile_source_context
from src.api.services.construction_client_profile_source_context import (
    client_restriction_rules,
    client_profile_source_fields,
    client_restriction_profile_context,
    sustainability_preference_profile_context,
    sustainability_preferences,
)
from src.core.common.canonical import hash_canonical_payload
from src.core.construction.vocabulary import ConstructionMethodStatus
from tests.unit.dpm.construction.source_product_context_fixtures import (
    client_restriction_profile_response,
    sustainability_preference_profile_response,
)


def test_client_profile_source_context_exports_only_client_profile_mappers() -> None:
    assert construction_client_profile_source_context.__all__ == [
        "ClientProfileSourceResponse",
        "client_restriction_rules",
        "client_profile_source_fields",
        "client_restriction_profile_context",
        "sustainability_preference_profile_context",
        "sustainability_preferences",
    ]


def test_client_profile_source_fields_preserve_common_restriction_lineage() -> None:
    response = client_restriction_profile_response()
    fields = client_profile_source_fields(response)

    assert fields["supportability_status"] == ConstructionMethodStatus.READY
    assert fields["source_system"] == "lotus-core"
    assert fields["source_product_name"] == "ClientRestrictionProfile"
    assert fields["source_product_version"] == "v1"
    assert fields["source_id"] == "restriction-lineage"
    assert fields["content_hash"] == hash_canonical_payload(
        response.model_dump(mode="json", exclude_none=True)
    )
    assert fields["portfolio_id"] == "PB_SG_GLOBAL_BAL_001"
    assert fields["client_id"] == "client-1"
    assert fields["mandate_id"] == "mandate-1"
    assert fields["as_of_date"] == response.as_of_date


def test_client_profile_source_fields_preserve_common_sustainability_lineage() -> None:
    response = sustainability_preference_profile_response()
    fields = client_profile_source_fields(response)

    assert fields["supportability_status"] == ConstructionMethodStatus.BLOCKED
    assert fields["source_product_name"] == "SustainabilityPreferenceProfile"
    assert fields["source_id"] == "sustainability-lineage"
    assert fields["content_hash"] == hash_canonical_payload(
        response.model_dump(mode="json", exclude_none=True)
    )
    assert fields["portfolio_id"] == "PB_SG_GLOBAL_BAL_001"
    assert fields["client_id"] == "client-1"
    assert fields["mandate_id"] == "mandate-1"


def test_client_restriction_profile_context_preserves_rules_and_lineage() -> None:
    context = client_restriction_profile_context(client_restriction_profile_response())

    assert context.supportability_status == ConstructionMethodStatus.READY
    assert context.source_system == "lotus-core"
    assert context.source_product_name == "ClientRestrictionProfile"
    assert context.source_id == "restriction-lineage"
    assert context.portfolio_id == "PB_SG_GLOBAL_BAL_001"
    assert context.client_id == "client-1"
    assert context.restriction_count == 1
    assert context.reason_codes == ["CLIENT_RESTRICTIONS_READY"]
    assert len(context.restrictions) == 1
    assert context.restrictions[0].restriction_code == "NO_SINGLE_STOCK_A"
    assert context.restrictions[0].instrument_ids == ["EQ_A"]
    assert context.restrictions[0].source_record_id == "restriction-record-1"


def test_client_restriction_rules_project_source_rules() -> None:
    rules = client_restriction_rules(client_restriction_profile_response())

    assert len(rules) == 1
    assert rules[0].restriction_code == "NO_SINGLE_STOCK_A"
    assert rules[0].instrument_ids == ["EQ_A"]
    assert rules[0].source_record_id == "restriction-record-1"


def test_client_restriction_profile_context_falls_back_to_content_hash_source_id() -> None:
    response = client_restriction_profile_response().model_copy(
        update={
            "source_batch_fingerprint": None,
            "lineage": {},
        }
    )
    expected_hash = hash_canonical_payload(response.model_dump(mode="json", exclude_none=True))

    context = client_restriction_profile_context(response)

    assert context.source_id == expected_hash


def test_sustainability_preference_context_preserves_preferences_and_status() -> None:
    context = sustainability_preference_profile_context(
        sustainability_preference_profile_response()
    )

    assert context.supportability_status == ConstructionMethodStatus.BLOCKED
    assert context.source_system == "lotus-core"
    assert context.source_product_name == "SustainabilityPreferenceProfile"
    assert context.source_id == "sustainability-lineage"
    assert context.preference_count == 1
    assert context.missing_data_families == ["classification_review"]
    assert context.reason_codes == ["SUSTAINABILITY_PREFERENCES_PARTIAL"]
    assert len(context.preferences) == 1
    assert context.preferences[0].preference_code == "MIN_ARTICLE_8"
    assert context.preferences[0].minimum_allocation == Decimal("0.40")
    assert context.preferences[0].positive_tilt_codes == ["LOW_CARBON"]


def test_sustainability_preferences_project_source_preferences() -> None:
    preferences = sustainability_preferences(sustainability_preference_profile_response())

    assert len(preferences) == 1
    assert preferences[0].preference_code == "MIN_ARTICLE_8"
    assert preferences[0].minimum_allocation == Decimal("0.40")
    assert preferences[0].positive_tilt_codes == ["LOW_CARBON"]


def test_sustainability_preference_context_falls_back_to_content_hash_source_id() -> None:
    response = sustainability_preference_profile_response().model_copy(
        update={
            "source_batch_fingerprint": None,
            "lineage": {},
        }
    )
    expected_hash = hash_canonical_payload(response.model_dump(mode="json", exclude_none=True))

    context = sustainability_preference_profile_context(response)

    assert context.source_id == expected_hash
