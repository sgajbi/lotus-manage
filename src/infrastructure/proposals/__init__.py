from src.infrastructure.proposals.in_memory import InMemoryProposalRepository
from src.infrastructure.proposals.postgres import PostgresProposalRepository

__all__ = ["InMemoryProposalRepository", "PostgresProposalRepository"]
