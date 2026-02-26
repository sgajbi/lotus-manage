from src.core.dpm.policy_packs import DpmPolicyPackDefinition, parse_policy_pack_catalog


class EnvJsonDpmPolicyPackRepository:
    def __init__(self, *, catalog_json: str | None) -> None:
        self._policy_packs = parse_policy_pack_catalog(catalog_json)

    def list_policy_packs(self) -> list[DpmPolicyPackDefinition]:
        return sorted(self._policy_packs.values(), key=lambda item: item.policy_pack_id)

    def get_policy_pack(self, *, policy_pack_id: str) -> DpmPolicyPackDefinition | None:
        return self._policy_packs.get(policy_pack_id)

    def upsert_policy_pack(self, policy_pack: DpmPolicyPackDefinition) -> None:
        self._policy_packs[policy_pack.policy_pack_id] = policy_pack

    def delete_policy_pack(self, *, policy_pack_id: str) -> bool:
        return self._policy_packs.pop(policy_pack_id, None) is not None
