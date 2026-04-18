# Troubleshooting

## Common checks

- if readiness fails, inspect persistence and migration posture first
- if supportability endpoints return inconsistent results, verify run persistence and lineage stores
- if local host startup collides with advisory runtime, confirm `lotus-manage` is using port `8001`
- if capability discovery fails, check query parameter shape and backend route availability

## Useful commands

```bash
make check
make ci
python -m pytest tests/unit/test_local_docker_runtime_contract.py -q
python -m pytest tests/unit/dpm/contracts/test_contract_openapi_supportability_docs.py -q
```

## References

- [docs/runbooks/service-operations.md](../docs/runbooks/service-operations.md)
- [docs/documentation/postgres-migration-rollout-runbook.md](../docs/documentation/postgres-migration-rollout-runbook.md)
