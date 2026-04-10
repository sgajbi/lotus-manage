# Repository Engineering Context

This file provides repository-local engineering context for `lotus-manage`.

For platform-wide truth, read:

1. `C:\Users\Sandeep\projects\lotus-platform\context\LOTUS-QUICKSTART-CONTEXT.md`
2. `C:\Users\Sandeep\projects\lotus-platform\context\LOTUS-ENGINEERING-CONTEXT.md`
3. `C:\Users\Sandeep\projects\lotus-platform\context\CONTEXT-REFERENCE-MAP.md`

## Repository Role

`lotus-manage` is the discretionary portfolio-management and operational workflow service.

It owns management-side execution, supportability, and lifecycle workflows that are not advisory-only.

## Business And Domain Responsibility

This repository owns:

1. discretionary portfolio-management workflow APIs,
2. management-side lifecycle and execution support,
3. operational supportability and related management contracts.

Advisor-led proposal workflows are intentionally owned by `lotus-advise`.

## Current-State Summary

Current repository posture:

1. `lotus-manage` is the management-side service after the split from `lotus-advise`,
2. canonical local host runtime uses port `8001` so it can coexist with `lotus-advise`,
3. local CI and Docker parity are already standardized under the RFC-0072 lane model,
4. the service remains part of the canonical front-office validation path through `lotus-gateway`.

## Architecture And Module Map

Primary areas:

1. `src/`
   management APIs, workflow logic, and supporting modules.
2. `scripts/`
   OpenAPI, vocabulary, migration, and governance scripts.
3. `tests/`
   unit, integration, and e2e validation.

## Runtime And Integration Boundaries

Runtime model:

1. FastAPI service,
2. depends on `lotus-core`,
3. primarily consumed through `lotus-gateway`,
4. canonical host runtime is exposed through `manage.dev.lotus`.

Boundary rules:

1. management workflows belong here,
2. proposal and advisor-led flows belong in `lotus-advise`,
3. host runtime identity and coexistence with `lotus-advise` are part of the operational contract,
4. management capabilities should remain aligned with gateway-facing product expectations.

## Repo-Native Commands

Use these commands as the primary local contract:

1. install
   `make install`
2. fast local gate
   `make check`
3. PR-grade local gate
   `make ci`
4. feature-lane local gate
   `make ci-local`
5. Docker parity
   `make ci-local-docker`
6. canonical host runtime
   `make run-canonical`

## Validation And CI Expectations

`lotus-manage` uses explicit CI lanes:

1. `Remote Feature Lane`
2. `Pull Request Merge Gate`
3. `Main Releasability Gate`

Important validation expectations:

1. no-alias, OpenAPI, API vocabulary, migration smoke, and security audit are active,
2. PR-grade validation includes coverage-backed full test execution,
3. host/runtime coexistence assumptions matter for canonical front-office startup.

## Standards And RFCs That Govern This Repository

Most relevant current governance:

1. `C:\Users\Sandeep\projects\lotus-platform\rfcs\RFC-0066-lotus-advise-to-lotus-advise-and-lotus-manage-split.md`
2. `C:\Users\Sandeep\projects\lotus-platform\rfcs\RFC-0067-centralized-api-vocabulary-inventory-and-openapi-documentation-governance.md`
3. `C:\Users\Sandeep\projects\lotus-platform\rfcs\RFC-0071-centralized-environment-scoped-service-addressing-and-ingress-governance.md`
4. `C:\Users\Sandeep\projects\lotus-platform\rfcs\RFC-0072-platform-wide-multi-lane-ci-validation-and-release-governance.md`
5. `C:\Users\Sandeep\projects\lotus-platform\rfcs\RFC-0073-lotus-ecosystem-engineering-context-and-agent-guidance-system.md`

## Known Constraints And Implementation Notes

1. management/advisory boundary clarity is a real quality concern after the split,
2. canonical local host runtime matters because port coexistence with `lotus-advise` is intentional,
3. local `pip check` and project-scoped security posture still matter for repo truth here,
4. this repo should stay operationally aligned with gateway and platform startup sequences.

## Context Maintenance Rule

Update this document when:

1. management workflow ownership changes,
2. runtime or coexistence assumptions with `lotus-advise` change,
3. repo-native commands or CI expectations change,
4. upstream or downstream integration posture changes materially,
5. current-state rollout posture changes.

## Cross-Links

1. `C:\Users\Sandeep\projects\lotus-platform\context\LOTUS-QUICKSTART-CONTEXT.md`
2. `C:\Users\Sandeep\projects\lotus-platform\context\LOTUS-ENGINEERING-CONTEXT.md`
3. `C:\Users\Sandeep\projects\lotus-platform\context\CONTEXT-REFERENCE-MAP.md`
4. `C:\Users\Sandeep\projects\lotus-platform\context\Repository-Engineering-Context-Contract.md`
