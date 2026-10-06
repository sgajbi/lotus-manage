"""One frozen cross-owner pack and test-only provider registration injection."""

import copy
import hashlib
import json
from pathlib import Path

from src.core.composite_provider_trust import (
    CompositeProviderTrustRequest,
    CompositeProviderTrustResolution,
)

FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures/composites/source-authority.v2.json"


def frozen_authority_pack() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def independent_digest(payload: dict) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def rebind_definition(wire: dict, *, refresh_approval: bool = False) -> dict:
    wire = copy.deepcopy(wire)
    authority = wire["source_authority"]
    authority["profile_digest"] = independent_digest(authority["payload"])
    wire["definition_payload_digest"] = independent_digest(
        {
            k: v
            for k, v in wire.items()
            if k not in {"content_hash", "authority_approval", "definition_payload_digest"}
        }
    )
    if refresh_approval:
        claims = wire["authority_approval"]["claims"]
        claims["profile_digest"] = authority["profile_digest"]
        claims["definition_payload_digest"] = wire["definition_payload_digest"]
    wire["content_hash"] = independent_digest(
        {k: v for k, v in wire.items() if k != "content_hash"}
    )
    return wire


def definition_request(wire: dict) -> dict:
    return {
        key: value
        for key, value in wire.items()
        if key
        not in {"product_name", "tenant_id", "composite_id", "definition_version", "created_by"}
    }


def ending_assets_example() -> tuple[dict, dict]:
    """Separate synthetic identities; never edits or replaces the frozen shared pack."""
    item = frozen_authority_pack()["external_versions"]["original"]
    wire = copy.deepcopy(item["definition"])
    registry = copy.deepcopy(item["supporting_payloads"]["registry"])
    registry["registry_revision"] = "synthetic.ending.registry.r1"
    registry["allowed_products"].append("SyntheticEndingAssetObservations")
    profile = wire["source_authority"]["payload"]
    profile["profile_id"] = "synthetic.ending.authority"
    profile["profile_revision"] = "synthetic.ending.r1"
    profile["providers"][0]["registry_revision"] = registry["registry_revision"]
    profile["providers"][0]["registry_digest"] = independent_digest(registry)
    ending = copy.deepcopy(profile["selections"][0])
    ending.update(
        selection_id="ending_assets",
        fact="ENDING_ASSETS",
        source_product="SyntheticEndingAssetObservations",
        source_revision="synthetic.ending.observations.r1",
        source_watermark="synthetic.ending.watermark.r1",
        source_cut_id="synthetic.ending.cut.r1",
        source_digest=independent_digest({"posture": "SYNTHETIC_ENDING_SOURCE_ONLY"}),
    )
    profile["selections"].append(ending)
    profile["selections"].sort(key=lambda selection: selection["selection_id"])
    wire["definition_version"] = "synthetic.definition.ending.r1"
    claims = wire["authority_approval"]["claims"]
    claims["definition_version"] = wire["definition_version"]
    claims["profile_id"] = profile["profile_id"]
    claims["profile_revision"] = profile["profile_revision"]
    return rebind_definition(wire, refresh_approval=True), registry


def institutional_reference_wire(wire: dict) -> dict:
    """Unqualified artifact reference for representation/refusal, not an approval."""
    wire = copy.deepcopy(wire)
    claims = wire["authority_approval"]["claims"]
    claims["schema_version"] = "composite-authority-approval-claims.v1"
    wire["authority_approval"] = {
        "evidence_kind": "INSTITUTIONAL_ATTESTATION_REFERENCE",
        "claims": claims,
        "attestation": {
            "contract_version": "composite-authority-attestation.v1",
            "issuer_id": "synthetic-unqualified-issuer",
            "attestation_id": "synthetic-unqualified",
            "revision": "synthetic.r1",
            "digest": independent_digest(
                {"claims": claims, "posture": "SYNTHETIC_UNQUALIFIED_ARTIFACT"}
            ),
        },
        "official_activation": "UNAVAILABLE",
    }
    return rebind_definition(wire)


class SyntheticFixtureProviderTrust:
    """Never wired by application composition or selected from a request field."""

    def __init__(self, registry: dict):
        self._registry = copy.deepcopy(registry)

    def resolve(self, request: CompositeProviderTrustRequest) -> CompositeProviderTrustResolution:
        registry = self._registry
        if (
            request.tenant_id,
            request.provider_id,
            request.registry_revision,
            request.registry_digest,
            request.effective_from,
            request.effective_to,
        ) != (
            registry["tenant_id"],
            registry["provider_id"],
            registry["registry_revision"],
            independent_digest(registry),
            registry["effective_from"],
            registry["effective_to"],
        ) or request.source_product not in registry["allowed_products"]:
            return CompositeProviderTrustResolution("UNAVAILABLE", "SYNTHETIC_REGISTRATION_REFUSED")
        return CompositeProviderTrustResolution(
            "SYNTHETIC_TEST_ONLY", "SYNTHETIC_REGISTRATION_ONLY", independent_digest(registry)
        )
