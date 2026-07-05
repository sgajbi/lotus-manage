# Manage Tests

Tests are the executable contract for Manage behavior, API shape, docs truth, and governance
guardrails.

| Folder | Scope | Command |
| --- | --- | --- |
| `unit/` | Fast deterministic domain, API, contract, docs, and governance tests. | `make test-unit` |
| `integration/` | Cross-component and persistence-facing tests. | `make test-integration` |
| `e2e/` | End-to-end service behavior and runtime scenarios. | `make test-e2e` |
| `shared/` | Shared fixtures and helpers used by multiple families. | Called by the owning tests. |

Do not add superficial coverage just to satisfy a number. Add tests that prove the risk being
fixed: boundary behavior, failure mode, idempotency, source-lineage preservation, contract drift,
or supportability evidence.

Common verification:

```powershell
make test-fast
make coverage-gate
python -m pytest tests\unit\test_documentation_current_state.py -q
```

