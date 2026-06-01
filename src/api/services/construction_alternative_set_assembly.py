import uuid
from datetime import datetime, timezone
from typing import Optional

from src.api.services.construction_alternative_set_lineage import alternative_set_lineage_fields
from src.core.construction.alternative_engine import build_alternative_set
from src.core.construction.models import ConstructionAlternative, ConstructionAlternativeSet
from src.core.dpm_source_context import DpmResolvedSourceContext


def build_persistable_alternative_set(
    *,
    portfolio_id: str,
    alternatives: list[ConstructionAlternative],
    request_hash: str,
    source_context: Optional[DpmResolvedSourceContext],
    alternative_set_id: str | None = None,
    as_of: str | None = None,
) -> ConstructionAlternativeSet:
    return build_alternative_set(
        alternative_set_id=alternative_set_id or f"cas_{uuid.uuid4().hex[:12]}",
        portfolio_id=portfolio_id,
        as_of=as_of or datetime.now(timezone.utc).date().isoformat(),
        alternatives=alternatives,
    ).model_copy(
        update=alternative_set_lineage_fields(
            request_hash=request_hash,
            source_context=source_context,
        )
    )


__all__ = ["build_persistable_alternative_set"]
