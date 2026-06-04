from src.api.services import construction_source_product_profile_context
from src.api.services import construction_source_product_financial_context
from src.api.services.construction_authority_context_updates import (
    merge_authority_context_update_maps,
)
from src.core.construction.models import ConstructionAuthorityContext
from src.core.dpm_source_context import DpmCoreExecutionContext, DpmResolvedSourceContext


def source_product_authority_context_updates(
    *,
    source_context: DpmCoreExecutionContext,
    authority_context: ConstructionAuthorityContext,
) -> dict[str, object]:
    return merge_authority_context_update_maps(
        construction_source_product_profile_context.source_profile_context_updates(
            source_context=source_context,
            authority_context=authority_context,
        ),
        construction_source_product_financial_context.source_financial_context_updates(
            source_context=source_context,
            authority_context=authority_context,
        ),
    )


def authority_context_with_source_products(
    *,
    authority_context: ConstructionAuthorityContext,
    source_context: DpmResolvedSourceContext | None,
) -> ConstructionAuthorityContext:
    if source_context is None:
        return authority_context
    context_updates = source_product_authority_context_updates(
        source_context=source_context.context,
        authority_context=authority_context,
    )
    if not context_updates:
        return authority_context
    return authority_context.model_copy(update=context_updates)


__all__ = [
    "authority_context_with_source_products",
    "source_product_authority_context_updates",
]
