from decimal import Decimal

from src.api.services.construction_client_profile_source_context import (
    client_restriction_profile_context,
    sustainability_preference_profile_context,
)
from src.core.construction.vocabulary import ConstructionMethodStatus
from tests.unit.dpm.construction.source_product_context_fixtures import (
    client_restriction_profile_response,
    sustainability_preference_profile_response,
)


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
