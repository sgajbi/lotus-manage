"""Durable adapters for Manage-owned composite eligibility evidence."""

from src.infrastructure.composites.in_memory import InMemoryDpmCompositeRepository
from src.infrastructure.composites.postgres import PostgresDpmCompositeRepository

__all__ = ["InMemoryDpmCompositeRepository", "PostgresDpmCompositeRepository"]
