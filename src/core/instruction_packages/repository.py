"""Persistence port for immutable approved-instruction packages."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from src.core.instruction_packages.models import (
    DpmApprovedInstructionPackage,
    DpmInstructionPackageReceipt,
)


class DpmInstructionPackageConflictError(ValueError):
    """Raised when an immutable package or receipt identity changes."""


class DpmInstructionPackageRepository(Protocol):
    def save_package(self, *, package: DpmApprovedInstructionPackage) -> bool:
        """Save one immutable tenant package; return True only when newly created."""

    def get_package(
        self, *, tenant_id: str, package_id: str, package_version: str
    ) -> DpmApprovedInstructionPackage | None:
        """Read one exact package version inside its admitted tenant."""

    def list_packages(
        self,
        *,
        tenant_id: str,
        created_before: datetime,
        limit: int,
        offset: int,
    ) -> tuple[list[DpmApprovedInstructionPackage], int]:
        """Read a page and exact count from an immutable time-bounded snapshot."""

    def get_package_by_wave_item(
        self, *, tenant_id: str, wave_id: str, wave_item_id: str
    ) -> list[DpmApprovedInstructionPackage]:
        """Read prior versions to validate explicit supersession."""

    def save_receipt(self, *, receipt: DpmInstructionPackageReceipt) -> bool:
        """Save one consumer receipt; return True only when newly created."""

    def get_receipt(
        self,
        *,
        tenant_id: str,
        package_id: str,
        package_version: str,
        consumer_id: str,
    ) -> DpmInstructionPackageReceipt | None:
        """Read an adapter's own durable retrieval receipt."""


__all__ = ["DpmInstructionPackageConflictError", "DpmInstructionPackageRepository"]
