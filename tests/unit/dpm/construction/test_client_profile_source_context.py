from datetime import date
from decimal import Decimal

from src.api.services.construction_client_profile_source_context import (
    client_restriction_profile_context,
    sustainability_preference_profile_context,
)
from src.core.construction.vocabulary import ConstructionMethodStatus
from src.core.dpm_source_context import (
    DpmCoreClientRestrictionEntry,
    DpmCoreClientRestrictionProfileResponse,
    DpmCoreClientRestrictionSupportability,
    DpmCoreSustainabilityPreferenceEntry,
    DpmCoreSustainabilityPreferenceProfileResponse,
    DpmCoreSustainabilityPreferenceSupportability,
)


def _client_restriction_profile() -> DpmCoreClientRestrictionProfileResponse:
    return DpmCoreClientRestrictionProfileResponse(
        product_name="ClientRestrictionProfile",
        product_version="v1",
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        client_id="client-1",
        mandate_id="mandate-1",
        as_of_date=date(2026, 6, 1),
        restrictions=[
            DpmCoreClientRestrictionEntry(
                restriction_scope="INSTRUMENT",
                restriction_code="NO_SINGLE_STOCK_A",
                restriction_status="ACTIVE",
                restriction_source="CLIENT_MANDATE",
                applies_to_buy=True,
                applies_to_sell=False,
                instrument_ids=["EQ_A"],
                effective_from=date(2026, 1, 1),
                restriction_version=3,
                source_record_id="restriction-record-1",
            )
        ],
        supportability=DpmCoreClientRestrictionSupportability(
            state="READY",
            reason="CLIENT_RESTRICTIONS_READY",
            restriction_count=1,
            missing_data_families=[],
        ),
        lineage={"source_batch_fingerprint": "restriction-lineage"},
    )


def _sustainability_preference_profile() -> DpmCoreSustainabilityPreferenceProfileResponse:
    return DpmCoreSustainabilityPreferenceProfileResponse(
        product_name="SustainabilityPreferenceProfile",
        product_version="v1",
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        client_id="client-1",
        mandate_id="mandate-1",
        as_of_date=date(2026, 6, 1),
        preferences=[
            DpmCoreSustainabilityPreferenceEntry(
                preference_framework="SFDR",
                preference_code="MIN_ARTICLE_8",
                preference_status="ACTIVE",
                preference_source="CLIENT_MANDATE",
                minimum_allocation=Decimal("0.40"),
                applies_to_asset_classes=["EQUITY"],
                exclusion_codes=["THERMAL_COAL"],
                positive_tilt_codes=["LOW_CARBON"],
                effective_from=date(2026, 1, 1),
                preference_version=2,
                source_record_id="preference-record-1",
            )
        ],
        supportability=DpmCoreSustainabilityPreferenceSupportability(
            state="INCOMPLETE",
            reason="SUSTAINABILITY_PREFERENCES_PARTIAL",
            preference_count=1,
            missing_data_families=["classification_review"],
        ),
        lineage={"source_batch_fingerprint": "sustainability-lineage"},
    )


def test_client_restriction_profile_context_preserves_rules_and_lineage() -> None:
    context = client_restriction_profile_context(_client_restriction_profile())

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
    context = sustainability_preference_profile_context(_sustainability_preference_profile())

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
