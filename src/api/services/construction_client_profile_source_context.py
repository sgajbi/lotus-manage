from src.api.services.construction_source_product_status import source_status_to_method_status
from src.api.services.construction_source_identity import source_product_identity
from src.core.construction.models import (
    AuthoritativeClientRestrictionContext,
    AuthoritativeClientRestrictionRule,
    AuthoritativeSustainabilityPreference,
    AuthoritativeSustainabilityPreferenceContext,
)
from src.core.dpm_source_context import (
    DpmCoreClientRestrictionProfileResponse,
    DpmCoreSustainabilityPreferenceProfileResponse,
)


def client_restriction_profile_context(
    restriction_profile: DpmCoreClientRestrictionProfileResponse,
) -> AuthoritativeClientRestrictionContext:
    identity = source_product_identity(restriction_profile)
    return AuthoritativeClientRestrictionContext(
        supportability_status=source_status_to_method_status(
            restriction_profile.supportability.state
        ),
        source_system=identity.source_system,
        source_product_name=identity.source_product_name,
        source_product_version=identity.source_product_version,
        source_id=identity.source_id,
        content_hash=identity.content_hash,
        portfolio_id=restriction_profile.portfolio_id,
        client_id=restriction_profile.client_id,
        mandate_id=restriction_profile.mandate_id,
        as_of_date=restriction_profile.as_of_date,
        restriction_count=restriction_profile.supportability.restriction_count,
        missing_data_families=restriction_profile.supportability.missing_data_families,
        restrictions=[
            AuthoritativeClientRestrictionRule.model_validate(rule.model_dump(mode="python"))
            for rule in restriction_profile.restrictions
        ],
        reason_codes=[restriction_profile.supportability.reason],
    )


def sustainability_preference_profile_context(
    sustainability_profile: DpmCoreSustainabilityPreferenceProfileResponse,
) -> AuthoritativeSustainabilityPreferenceContext:
    identity = source_product_identity(sustainability_profile)
    return AuthoritativeSustainabilityPreferenceContext(
        supportability_status=source_status_to_method_status(
            sustainability_profile.supportability.state
        ),
        source_system=identity.source_system,
        source_product_name=identity.source_product_name,
        source_product_version=identity.source_product_version,
        source_id=identity.source_id,
        content_hash=identity.content_hash,
        portfolio_id=sustainability_profile.portfolio_id,
        client_id=sustainability_profile.client_id,
        mandate_id=sustainability_profile.mandate_id,
        as_of_date=sustainability_profile.as_of_date,
        preference_count=sustainability_profile.supportability.preference_count,
        missing_data_families=sustainability_profile.supportability.missing_data_families,
        preferences=[
            AuthoritativeSustainabilityPreference.model_validate(
                preference.model_dump(mode="python")
            )
            for preference in sustainability_profile.preferences
        ],
        reason_codes=[sustainability_profile.supportability.reason],
    )


__all__ = [
    "client_restriction_profile_context",
    "sustainability_preference_profile_context",
]
