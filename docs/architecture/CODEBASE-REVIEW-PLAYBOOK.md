# Codebase Review Playbook

This playbook is the repository-local review control for RFC-0036 cleanup work. It keeps cleanup
evidence repeatable without turning the RFC into a file-by-file audit log.

## Review Units

| Unit | Scope | Primary evidence |
| --- | --- | --- |
| Runtime API surface | FastAPI router mounts, OpenAPI paths, health routes, duplicate aliases | route inventory, OpenAPI quality gate |
| DPM domain code | rebalance engine, run supportability, policy packs, workflow gates | unit contracts, focused module review |
| Retired advisory namespaces | advisory/proposal packages, routes, migrations, demo payloads, docs | search ledger, documentation current-state tests |
| Documentation and wiki source | README, repo docs, RFC index, wiki authored pages | docs regression tests, wiki link checks |
| Platform and mesh controls | API certification, supported-features material, data-product dependencies | RFC evidence, endpoint certification ledger |

## Review Rules

1. Prefer deletion over compatibility when behavior is outside the target DPM mandate.
2. Keep repo docs implementation-focused and use the wiki for long-lived product/operator material.
3. Do not move endpoint behavior between slices; record the finding and fix it in the owning slice.
4. Every cleanup finding must have one of these outcomes: fixed, deliberately retained, deferred to
   a named slice, or filed in the owning downstream/upstream repository.
5. Add a test when the finding represents a regression risk that future work could reintroduce.

## Minimum Slice Evidence

Each cleanup slice must record:

- reviewed paths or search patterns,
- concrete findings,
- action taken or deferral owner,
- validation commands,
- wiki decision.
