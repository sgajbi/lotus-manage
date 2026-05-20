"""RFC-0040 portfolio memory read-model primitives."""

from src.core.portfolio_memory.models import (
    DpmPortfolioMemory,
    DpmPortfolioMemoryEvent,
    DpmPortfolioMemoryExternalExecutionBoundaryEvidence,
    DpmPortfolioMemorySearchItem,
    DpmPortfolioMemorySearchPage,
    DpmPortfolioMemorySourceRef,
)
from src.core.portfolio_memory.handoffs import (
    DpmPortfolioMemoryReportContext,
    DpmPortfolioMemoryReportEventRef,
    build_portfolio_memory_report_context,
)

__all__ = [
    "DpmPortfolioMemory",
    "DpmPortfolioMemoryEvent",
    "DpmPortfolioMemoryExternalExecutionBoundaryEvidence",
    "DpmPortfolioMemorySearchItem",
    "DpmPortfolioMemorySearchPage",
    "DpmPortfolioMemoryReportContext",
    "DpmPortfolioMemoryReportEventRef",
    "DpmPortfolioMemorySourceRef",
    "build_portfolio_memory_report_context",
]
