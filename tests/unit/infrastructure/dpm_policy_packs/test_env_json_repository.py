from src.core.dpm.policy_packs import DpmPolicyPackDefinition
from src.infrastructure.dpm_policy_packs.env_json import EnvJsonDpmPolicyPackRepository


def test_env_json_repository_supports_crud_operations() -> None:
    repository = EnvJsonDpmPolicyPackRepository(catalog_json="{}")
    assert repository.list_policy_packs() == []
    assert repository.get_policy_pack(policy_pack_id="missing") is None

    first = DpmPolicyPackDefinition(policy_pack_id="pack_b", version="1")
    second = DpmPolicyPackDefinition(policy_pack_id="pack_a", version="1")

    repository.upsert_policy_pack(first)
    repository.upsert_policy_pack(second)
    listed = repository.list_policy_packs()

    assert [item.policy_pack_id for item in listed] == ["pack_a", "pack_b"]
    assert repository.get_policy_pack(policy_pack_id="pack_b") is not None
    assert repository.delete_policy_pack(policy_pack_id="pack_b") is True
    assert repository.delete_policy_pack(policy_pack_id="pack_b") is False
