"""Thread-safe development/test storage for immutable instruction packages."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from threading import Lock

from src.core.instruction_packages import (
    DpmApprovedInstructionPackage,
    DpmInstructionPackageConflictError,
    DpmInstructionPackageReceipt,
    DpmInstructionPackageRepository,
)


class InMemoryDpmInstructionPackageRepository(DpmInstructionPackageRepository):
    def __init__(self) -> None:
        self._lock = Lock()
        self._packages: dict[tuple[str, str, str], DpmApprovedInstructionPackage] = {}
        self._receipts: dict[tuple[str, str, str, str], DpmInstructionPackageReceipt] = {}

    def save_package(self, *, package: DpmApprovedInstructionPackage) -> bool:
        key = (package.tenant_id, package.package_id, package.package_version)
        with self._lock:
            existing = self._packages.get(key)
            if existing is not None:
                if existing.content_hash != package.content_hash:
                    raise DpmInstructionPackageConflictError(
                        "INSTRUCTION_PACKAGE_IMMUTABLE_CONFLICT"
                    )
                return False
            self._packages[key] = deepcopy(package)
            return True

    def get_package(
        self, *, tenant_id: str, package_id: str, package_version: str
    ) -> DpmApprovedInstructionPackage | None:
        with self._lock:
            package = self._packages.get((tenant_id, package_id, package_version))
            return deepcopy(package) if package is not None else None

    def list_packages(
        self,
        *,
        tenant_id: str,
        created_before: datetime,
        limit: int,
        offset: int,
    ) -> tuple[list[DpmApprovedInstructionPackage], int]:
        with self._lock:
            matching = sorted(
                (
                    package
                    for (stored_tenant_id, _, _), package in self._packages.items()
                    if stored_tenant_id == tenant_id and package.created_at <= created_before
                ),
                key=lambda package: (
                    package.created_at,
                    package.package_id,
                    package.package_version,
                ),
                reverse=True,
            )
            return deepcopy(matching[offset : offset + limit]), len(matching)

    def get_package_by_wave_item(
        self, *, tenant_id: str, wave_id: str, wave_item_id: str
    ) -> list[DpmApprovedInstructionPackage]:
        with self._lock:
            return deepcopy(
                sorted(
                    (
                        package
                        for (stored_tenant_id, _, _), package in self._packages.items()
                        if stored_tenant_id == tenant_id
                        and package.wave_id == wave_id
                        and package.wave_item_id == wave_item_id
                    ),
                    key=lambda package: (
                        package.created_at,
                        package.package_id,
                        package.package_version,
                    ),
                    reverse=True,
                )
            )

    def save_receipt(self, *, receipt: DpmInstructionPackageReceipt) -> bool:
        key = (
            receipt.tenant_id,
            receipt.package_id,
            receipt.package_version,
            receipt.consumer_id,
        )
        with self._lock:
            existing = self._receipts.get(key)
            if existing is not None:
                if existing.receipt_evidence_hash != receipt.receipt_evidence_hash:
                    raise DpmInstructionPackageConflictError(
                        "INSTRUCTION_PACKAGE_RECEIPT_IMMUTABLE_CONFLICT"
                    )
                return False
            self._receipts[key] = deepcopy(receipt)
            return True

    def get_receipt(
        self,
        *,
        tenant_id: str,
        package_id: str,
        package_version: str,
        consumer_id: str,
    ) -> DpmInstructionPackageReceipt | None:
        with self._lock:
            receipt = self._receipts.get((tenant_id, package_id, package_version, consumer_id))
            return deepcopy(receipt) if receipt is not None else None


__all__ = ["InMemoryDpmInstructionPackageRepository"]
