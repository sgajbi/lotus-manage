# Repository Engineering Context

This file provides repository-local engineering context for `lotus-manage`.

Use the startup sequence in `AGENTS.md`: repository contract, platform quickstart, this repository
context, then the platform skill-routing map. Load the wider engineering context only for
cross-repository architecture or shared policy. Use the context reference map to locate a
particular standard, contract, or runbook when needed.

Platform paths resolve from the directory holding the checkouts. If no sibling Platform checkout
exists, use the canonical GitHub fallback in `AGENTS.md`. Repository-local ownership and mandatory
controls remain authoritative; conditional reading does not waive applicable validation or
security requirements.

## Repository Role

`lotus-manage` is the discretionary mandate portfolio-management execution and operational
supportability service.

It owns management-side rebalance execution, what-if orchestration, run supportability, policy-pack
controls, and mandate workflow review for discretionary portfolio management.

## Business And Domain Responsibility

This repository owns:

1. discretionary mandate rebalance simulation and what-if workflow APIs,
2. management-side lifecycle, workflow review, and execution support,
3. operational supportability, deterministic artifacts, lineage, idempotency, and policy-pack
   contracts.
4. tenant-scoped composite definition and effective-dated eligibility revision source records,
   with atomic durable publication cursors and immutable retrieval receipts. Publication
   completeness remains `UNVERIFIED`; `lotus-performance` owns member-return facts and composite
   calculation. Definition/revision list counts are total scoped counts from the same page read
   snapshot, but cross-request offset pages are not stable under writes; consumers use the
   publication cursor for handoff. The caller-asserted identity headers require trusted ingress
   before production use.
5. immutable composite-universe attestations scoped to a pinned membership revision, inclusive
   business-date range, exact portfolio set, policy and named source-product cuts/watermarks, with
   exactly one source product declared as authoritative for the universe. `COMPLETE`
   requires continuous decision coverage; `INCOMPLETE` retains missing/unexpected/gap evidence and
   `UNAVAILABLE` retains source failure. These attestations do not promote the publication envelope
   beyond `UNVERIFIED` or substitute for live producer and Performance consumer proof.

Advisor-led proposal simulation, artifacts, consent, and lifecycle workflows are intentionally
owned by `lotus-advise`.

## Current-State Summary

### Scope and truth ownership

This section records durable `lotus-manage` architecture, supported behavior, and integration
expectations. It deliberately excludes pull-request numbers, commit SHAs, wiki publication hashes,
temporary blockers, and delivery chronology; Git history and the owning GitHub issues preserve that
evidence. An external capability named here is not certified by this repository. Its current
producer contract, supported-feature posture, and operational evidence remain owned by the named
repository, while Manage owns only its declared consumption and fail-closed behavior.

### Runtime and persistence posture

1. `lotus-manage` is the management-side service separated from `lotus-advise`; it owns DPM
   operating workflows, mandate digital twins, monitoring, construction alternatives, proof packs,
   rebalance waves, outcome reviews, portfolio memory, and PM operating-quality records.
2. The canonical local host port is `8001`. Runtime configuration is environment-driven; PostgreSQL
   is the production stateful profile and in-memory adapters are bounded development/test profiles.
3. Database migrations are repository-owned under `src/infrastructure/postgres_migrations/` and are
   applied through the repository migration runner. Production readiness fails closed when required
   migrations or durable persistence prerequisites are absent.
4. `make quarantine-inventory` is the single read-only operator path for the fourteen governed
   nullable-tenant datasets. It uses stable row identities and never attributes, defaults, mutates,
   or exposes quarantined data through normal tenant-scoped reads.
5. Historical mandate reads preserve the resolved source `as_of_date`; Manage supports temporal
   retrieval without allowing Gateway or Workbench to reconstruct or relabel source history.

### Tenant and authority posture

1. Tenant-owned aggregates are fenced at their repository boundaries. NULL or contradictory owner
   records are matched by no tenant and remain quarantined until a separately governed attribution
   mechanism can prove an owner.
2. Monitoring-run creation requires normalized `X-Tenant-Id` to equal the body `tenant_id` before
   Core resolution or repository side effects. The admitted value is persisted as domain owner,
   database owner, payload owner, and retained audit-filter tenant.
3. Mandate refresh requires the same header/body agreement before sourcing or persistence. Manage
   forwards the normalized admitted tenant as a per-request Core header across mandatory and
   optional source products; a selector body is not a substitute for Core tenant admission.
   Stateful rebalance and construction envelopes likewise require matching `X-Tenant-Id` and
   `stateful_input.tenant_id` before resolver construction. Synchronous stateless simulation and
   stateless construction generation also require `X-Tenant-Id` for durable run ownership.
   Construction passes the normalized admitted tenant to every direct method run and persists it
   on alternative sets and selections. Idempotency is scoped to `(tenant_id, key)`, so exact
   same-tenant replay converges while different tenants may independently use the same key.
   Acquire the repository idempotency guard before method execution: PostgreSQL uses a stable
   tenant/key advisory lock on a dedicated autocommit session shared across service instances.
   Those sessions have a separate bounded connection budget and lock-wait timeout, preventing
   waiters from exhausting repository-write permits or inheriting the shorter statement timeout.
   Losing requests cannot record orphan runs, artifacts, or lineage before the canonical set exists,
   and the fence is not exposed to idle-in-transaction session expiry.
   Set/selection reads, selected-alternative proof-pack sourcing, portfolio-memory projection, and
   wave simulation/selection are tenant-fenced. Legacy NULL-owner rows are preserved but match no
   tenant and are never silently adopted. This remains caller-asserted scope, not production
   principal proof. Other stateless surfaces retain their own documented admission contract.
4. Caller-asserted tenant, actor, and role headers are routing and authorization inputs in the
   current runtime; they are not proof of an authenticated principal. Production identity and grant
   resolution remain external security-governance responsibilities.
5. Wave and proof-pack reads, writes, transitions, replay, and retained-row handling use explicit
   tenant ownership. Source-product selectors remain distinct from aggregate ownership and must not
   be silently treated as interchangeable authority. Durable wave creation binds each
   tenant-scoped idempotency key to one canonical request fingerprint. Omitted correlation ids are
   derived from `(tenant_id, Idempotency-Key)`, not the business trigger; explicit correlation ids
   are unique per tenant. Both persistence adapters reject changed-key and correlation collisions
   consistently, and competing exact creates converge without an orphan aggregate.
6. Synchronous rebalance admission requires normalized `X-Tenant-Id` for both stateless and
   stateful requests. PostgreSQL atomically owns `(tenant_id, Idempotency-Key)` before calculation,
   binds that identity to one immutable canonical request hash, and atomically publishes the run,
   artifact, mapping, history, and lineage. Active competing requests either recover the winner or
   receive a bounded in-progress response; expired claims may be fenced and retried. Historical
   runs and mappings without verified tenant ownership remain preserved but unreachable through
   normal tenant-scoped APIs.
7. Async scenario execution persists an `OPERATION_TO_RUN` lineage edge with scenario key and
   fenced execution attempt in the same repository transaction as its run. The terminal operation
   result identifies authoritative run IDs;
   earlier-attempt rows remain historical evidence. The operation support-bundle response is a
   multi-scenario contract (`scenarios` and `historical_runs`), unlike the singular direct run
   bundle. Never use root/scenario correlation-prefix guessing for membership. Fresh async retry
   correlations include the attempt to avoid the PostgreSQL tenant/correlation uniqueness conflict.

### Supported capability posture

1. The RFC-0038 foundation provides source-mapped mandate twins, deterministic mandate-health
   scoring, monitoring runs, health snapshots, exceptions, and the command-center summary.
2. The RFC-0039 foundation provides persisted construction alternatives and selected-alternative
   decisions. Manage consumes source-owned context but does not calculate external risk,
   performance, market-data, treasury, tax, advice, execution, order, fill, or settlement truth.
   `DO_NOTHING_BASELINE` carries zero action and before-state metrics. Its audit-only
   `evaluation_context` is separate from the null economic `rebalance_run_id`; never resolve it
   as a proposal or approval source. Legacy borrowed references are normalized on read without
   rewriting retained rows. No-action proof packs cannot authorize instructions or borrowed-run
   outcome economics. Wave selection replaces candidate diagnostics with the selected proposal.
   Blocked proof packs stay linked for audit, surface critical supportability, and cannot advance
   wave approval, staging or handoff; this also applies to retained ready-state items.
   A comparison-only baseline does not carry a transaction-cost estimate, including a fabricated
   zero estimate; this field remains null rather than claiming a calculation was performed.
3. The RFC-0040 foundation provides deterministic proof-pack generation, persistence, report and AI
   evidence inputs, and downstream handoff metadata without taking ownership of rendering, archive,
   report materialization, or AI-generated content.
4. The RFC-0041 foundation provides explicit-list and source-resolved rebalance waves, simulations,
   lifecycle controls, evidence, campaigns, and bounded source readiness. Book-scale simulation is
   admitted through durable tenant-scoped operations with persisted immutable item inputs/source
   identity, operation-wide concurrency/attempt budgets, leased fenced worker claims, incremental
   item checkpoints, stable paging, retry, and cancellation. Financial work stays outside claim
   transactions and uses deterministic operation/item construction identity for restart recovery.
   Tenant/wave projection uses a separate bounded coordination budget and fresh checkpoints;
   historical operations cannot overwrite a newer admission. Cancellation preserves terminal
   failure dispositions and their timestamps.
   Publication atomically makes a failure non-retryable when cancellation has already committed.
   Admitted tenant and effective cash/restriction authority remain attached through construction;
   policy-blocked alternatives are not selectable.
   The synchronous simulation route remains bounded and is not a restart-safe worker substitute.
   RFC-0041 does not claim client contact, maker-checker approval outside implemented controls, OMS
   execution, or suitability approval.
5. The RFC-0042 foundation provides outcome-review creation, refresh, comparison, search, and
   handoffs over source-owned realized evidence; missing or incomplete upstream evidence remains
   explicit rather than inferred.
6. Portfolio memory projects supported Manage aggregates and source-event lineage. It is not a
   cross-application event store or a substitute for source-owned payloads.
7. PM operating quality owns its policy, score-run, fairness-analysis, review-action, and summary
   records. It provides bounded operational evidence, not employee ranking, conduct adjudication,
   client-contact, execution, or HR decisions.
8. Approved DPM instruction packages are immutable, tenant-scoped retrieval records built only
   from a `HANDOFF_READY` wave item, READY proof pack, current mandate/model, persisted READY run,
   exact mapping evidence, funding posture, and an approval binding over canonical material. Preview
   material remains pending external approval; package receipt proves retrieval only. Packages do
   not submit orders or establish acknowledgement, fill, settlement, reconciliation, or core-booking
   truth. PostgreSQL migration `0035_approved_instruction_packages.sql` is required for durable
   production persistence; in-memory storage is development/test only.

### Integration truth ownership

| Boundary | Manage-owned current truth | External source of current truth |
| --- | --- | --- |
| Core source data | Typed clients, source-lineage preservation, completeness checks, and fail-closed mapping in `src/infrastructure/core_sourcing/` | `lotus-core` served OpenAPI, supported features, and repository engineering context |
| DPM portfolio universe | `DpmPortfolioUniverseCandidate:v1` is bounded candidate input for campaign discovery; unavailable, incomplete, degraded, empty, duplicate, non-terminating, or truncated pages fail closed | `lotus-core` owns candidate semantics and population truth |
| PM-book and cohort resolution | Manage consumes typed membership/cohort products and records selected source evidence; it does not infer membership locally | The producing Core, Risk, or Advise repository owns each served cohort contract |
| Risk and performance | Manage validates and preserves typed source context and supportability posture without recomputing external methodology | `lotus-risk` and `lotus-performance` own methodology, figures, thresholds, and source-product availability |
| Observed transaction costs | Manage applies source-owned average bps only when `TransactionCostCurve:v1` covers every candidate `(security_id, transaction_type)` key exactly once; duplicate keys, including identical rows or differing currencies, cannot yield a READY estimate. Caller-supplied duplicates fail validation; Core duplicates degrade with `TRANSACTION_COST_CURVE_DUPLICATE_POINT` and no aggregate. Missing-side reasons remain explicit. | `lotus-core` owns observed booked-fee grouping, curve methodology, lineage, and availability; predictive execution costs remain unsupported |
| Approved instruction retrieval | Manage publishes immutable approved package material and retrieval-only receipts with source, mapping, funding, and approval lineage; batch release refuses blocked candidates without authorizing them | An execution adapter owns order submission/acknowledgement; the core owner owns fills, settlement, authoritative booking, and reconciliation |
| Gateway and Workbench | Manage owns backend contracts and refusal semantics; consumer compatibility is proven in their repositories | `lotus-gateway` owns BFF admission/forwarding and `lotus-workbench` owns UI behavior and browser evidence |
| Reports, rendering, archive, and AI | Manage emits bounded handoff and evidence inputs with stable lineage | `lotus-report`, `lotus-render`, `lotus-archive`, and `lotus-ai` own downstream persistence, materialization, signing, and generated content |
| Platform contracts and canonical journeys | Manage declares repository-native contracts and participates in governed validation | `lotus-platform` owns shared contracts, routing standards, canonical runtime orchestration, and cross-repository evidence |

`BulkReviewCampaignMembership:v1` remains catalog-visible but is not promoted as an active Manage
source dependency without product-specific declaration, runtime support, and evidence. Repository-
native consumer declarations under `contracts/domain-data-products/`, the served OpenAPI document,
and supported-feature/wiki source are the checkable Manage truth; another repository's historical
delivery receipt is never a substitute.

For mandate health, a configured `max_tracking_error` makes `RISK_DRIFT` applicable. Manage may
assess it from an explicit tracking-error measurement or a usable source-owned Risk health context,
but it must not turn absent evidence into a zero or a passed control. Missing evidence is score 60,
`PENDING_REVIEW`, `TRACKING_ERROR_EVIDENCE_MISSING`, and `FIX_SOURCE_DATA`; explicit zero remains a
valid pass, and a mandate without the limit remains non-applicable. This is consumer scoring policy,
not Manage ownership of tracking-error methodology. Supplied `tracking_error` is an observed
non-negative, finite Decimal at the public health-input boundary, independent of a mandate limit
or source Risk context; a negative/non-finite value must fail validation before recalculation or
derived exception persistence, while `None` remains missing evidence and explicit zero is valid.

For the explicit mandate-health input, `tax_budget_base` is a non-negative cumulative realized-gain
allowance in the twin base currency, not an estimate of tax payable. `tax_budget_used_base` is the
caller-provided cumulative amount through the twin as-of date. Omitted currency and as-of fields
assert that base/date; supplied contradictions remain `TAX_BUDGET_BASIS_MISMATCH`. If either the
declared limit or usage states a period start, both must match. Missing usage is not zero; equality
exhausts the allowance and excess blocks health. The ten-percent `TAX_TURNOVER` weight is applied
once, while `budget_assessments` and distinct monitoring exceptions preserve both tax and turnover
findings. These caller-declared references and comparisons do not verify Core tax-period authority,
realized-gain ingestion, tax liability, or execution permission.
For turnover health, a declared limit is a cumulative fraction of portfolio value through the
twin as-of date. Missing usage is `TURNOVER_BUDGET_USAGE_MISSING`/PENDING_REVIEW, not zero or
READY. Optional declared period starts must match and an explicit usage as-of cut must equal the
twin cut; contradictory claims remain unassessed. Explicit zero is measured evidence; 80% through
below the limit is near-limit/review, equality exhausts the allowance, and excess blocks. A null
limit with unknown applicability is unsourced/PENDING_REVIEW; only an explicit source-declared
`turnover_budget_applicable=false` is non-applicable. These fields and lineage are caller-supplied
claims in the recalculation API, not a live Core turnover feed or release authority. Wave source
readiness inherits missing-usage review posture rather than treating it as a ready mandate.
An explicit Core unsourced field-gap marker defeats a contradictory caller non-applicability claim.

## Architecture And Module Map

Primary areas:

1. `src/`
   management APIs, workflow logic, and supporting modules.
   RFC-0038 mandate digital-twin and health-scoring domain primitives live in
   `src/core/mandates.py`; repository and persistence primitives live in
   `src/core/mandate_repository.py` and `src/infrastructure/mandates/`; mandate API orchestration
   lives in `src/api/services/mandate_service.py`, `src/api/routers/mandates.py`, and
   `src/api/routers/monitoring.py`, including the bounded command-center summary endpoint.
   RFC-0039 construction-alternative domain primitives live in `src/core/construction/`;
   construction persistence lives in `src/core/construction/repository.py` and
   `src/infrastructure/construction/`; construction API orchestration lives in
   `src/api/services/construction_service.py` and `src/api/routers/construction.py`.
   RFC-0042 outcome-review authority lives in `src/core/outcomes/`; outcome persistence lives in
   `src/infrastructure/outcomes/`; API orchestration lives in
   `src/api/services/outcome_review_service.py` and `src/api/routers/outcome_reviews.py`.
   RFC-0039/RFC-0040/RFC-0041/RFC-0042 portfolio-memory read-model primitives live in
   `src/core/portfolio_memory/`; construction event listing depends on
   `src/core/construction/repository.py`; API orchestration lives in
   `src/api/routers/portfolio_memory.py`.
2. `scripts/`
   OpenAPI, vocabulary, migration, and governance scripts.
3. `docs/`
   project overview, runbooks, standards, demo evidence, and RFC documentation.
4. `wiki/`
   canonical authored source for repository wiki publication and operator onboarding summaries.
5. `tests/`
   unit, integration, and e2e validation.
6. `contracts/domain-data-products/`
   repo-native producer and consumer declarations for governed upstream domain data products and
   management workflow products.
7. `contracts/trust-telemetry/`
   repo-native RFC-0087/RFC-0091 trust telemetry snapshots for governed management products.
   Snapshot coverage proves catalog fixture coverage only; product-specific snapshots, including
   PM-quality, may be blocked/operator-only until linked certification blockers are merged to
   `main` and runtime trust evidence is regenerated.

## Runtime And Integration Boundaries

Runtime model:

1. FastAPI service,
2. depends on `lotus-core` as source-data authority for governed stateful source-data resolution,
   while default execution consumes explicit stateless request bundles,
3. primarily consumed through `lotus-gateway`,
4. canonical host runtime is exposed through `manage.dev.lotus`.

Boundary rules:

1. management workflows belong here,
2. proposal and advisor-led flows belong in `lotus-advise` and should not be reintroduced here,
3. host runtime identity and coexistence with `lotus-advise` are part of the operational contract,
4. management capabilities should remain aligned with gateway-facing product expectations,
5. `lotus-core` remains the source-data authority for core-referenced portfolio, market-data, price, and FX inputs,
6. REST/OpenAPI remains the canonical integration contract; gRPC is not justified for current management workflows.

## Repo-Native Commands

Use these commands as the primary local contract:

1. install
   `make install`
2. fast local gate
   `make check`
3. PR-grade local gate
   `make ci`
   The monolithic full-suite coverage run delegates threshold enforcement to
   `scripts/coverage_gate.py --coverage-file .coverage`, the same governed two-decimal validator
   used by protected combined coverage. Do not reintroduce pytest-cov `--cov-fail-under` on
   `test-all`, `test-all-fast`, or `test-all-parallel`; its default precision can false-green a
   result that protected CI correctly rejects.
4. feature-lane local gate
   `make ci-local`
5. Docker parity
   `make ci-local-docker`
   The CI-local Docker lifecycle uses a stable checkout-specific project name from
   `scripts/ci_local_compose_project.py` for both startup and cleanup. Preserve that symmetric
   identity so CI teardown cannot remove the live product Compose project; orchestrators may set
   `CI_LOCAL_COMPOSE_PROJECT` to another unique value.
6. canonical host runtime
   `make run-canonical`
7. app-level demo certification
   `make demo-certify`
8. domain-data-product contract validation
   `make domain-product-validate`
9. test-family proof-breadth validation
   `make test-family-inventory`
10. NULL-tenant quarantine inventory
    `make quarantine-inventory`
    This operator-only command is the canonical observation path for the fourteen datasets retained
    without verified tenant attribution by migrations `0003`, `0024` through `0029`, `0032`, and
    `0033`, plus construction migration `0037`; partial quarantine indexes keep the census bounded
    as history grows. The command
    must remain bounded, sanitized, migration-provenanced, and transactionally read-only. A
    successful zero is distinct from failure; nonzero results do not authorize tenant inference or
    mutation.
11. Async analyze operations require tenant ownership. Durable execution uses an atomic expiring
    claim and opaque terminal-publication fence; TTL retention must not delete RUNNING recovery
    state. `DPM_ASYNC_EXECUTION_LEASE_SECONDS` defaults to 300 seconds. Attempt and lease expiry are
    operator-visible, while the fence token must never cross an API or log boundary.

## Repo-Scoped Testing Practice

The construction network recovery test uses actual Uvicorn/HTTP and PostgreSQL, with no dependency
overrides. The wave network recovery test uses the same owned runtime helper and aborts only an
observed, lock-blocked publication session after killing its API process. PostgreSQL queries can
outlive client death; verify the exact financial-commit/checkpoint boundary rather than assuming
process termination cancels database work. All fault locks and backend termination are confined
to the test's disposable database. The required PostgreSQL lane runs these tests through `make test-idea-management-action-postgres`
from this repository root, on Windows or POSIX with the supported environment activated.
Set `DPM_POSTGRES_INTEGRATION_DSN` to an isolated test server and
`DPM_POSTGRES_INTEGRATION_REQUIRED=1`. Its test account needs `CREATEDB`: each case creates and
removes only its UUID database. Never point this lane at production. API listeners bind ephemeral
localhost ports; a killed API process must be joined without signalling its potentially abandoned
shared Event lock. This proves bounded USD/FX durability, not Core authority, production IAM or capacity.

`test_construction_method_network.py` covers the complete construction-method vocabulary in
stateless and controlled-source stateful modes, including hard-policy-blocked candidates. It checks
independent economics, tenant-fenced run/artifact/support-bundle reads, selection refusal, retained
PostgreSQL owner/lineage and exact replay after API-process death. Source-aware methods retain
missing-authority qualifications; this is not live Core, downstream release or bank identity proof.

The native restriction matrix also covers direct simulation and every trading construction method
across buy/sell, inclusive effective dates, lifecycle, issuer/country/asset/global selectors and
missing-versus-empty profiles. Construction execution persists the shared hard-policy qualification
while returning mechanical comparison context; keep no-action comparison semantics independent.
Legacy artifacts are not rewritten. New artifacts retain decision, source hash/scope and versioned
rule references; missing authority remains non-release-ready. Complete database rows survive API death.

The PR/Main Docker job repeats these cases against the built image with
`make test-image-financial-runtime` from this repository root (Windows or POSIX).
`make workflow-policy-gate` parses PR/Main workflow structure and protects the image proof's
ordered steps and transitive prerequisites against skipping, failure waivers and execution overrides.
Complete step sequences are pinned in `contracts/ci/image-financial-execution-policy.v1.json`;
intentional lane changes must update that policy and its positive/negative regressions together.
Use an isolated loopback PostgreSQL test DSN with `CREATEDB`; containers reach its published port
through `host.docker.internal` (`host-gateway` on Linux). On Linux the isolated test port must be
reachable from that gateway; a host-only loopback listener is insufficient. Never expose a production
database for this proof. The runner resolves an immutable image ID, checks OCI and `/version` Git
revision, mounts no source, and fails on missing/skipped cases.
Only its exact application-container IDs and per-case UUID databases are removed. This command
does not start, reserve or certify the canonical front-office runtime.

## Validation And CI Expectations

`lotus-manage` uses explicit CI lanes:

1. `Remote Feature Lane`
2. `Pull Request Merge Gate`
3. `Main Releasability Gate`

Important validation expectations:

1. no-alias, OpenAPI, API vocabulary, migration smoke, and security audit are active,
2. profile admission accepts only normalized `LOCAL` or `PRODUCTION`; an unset variable defaults
   to `LOCAL` natively (`PRODUCTION` in Compose only when unset). Compose preserves explicit blanks;
   blank or unknown values raise value-safe `PERSISTENCE_PROFILE_UNSUPPORTED` before migration
   database access or API startup. Production profile readiness requires explicit write authorization enforcement, enterprise
   primary key id, a non-empty capability policy, and a valid bounded Postgres access policy in
   addition to Postgres persistence guardrails; PM-quality read/write routes require trusted actor,
   tenant, and role headers, reject body/header actor or tenant mismatches, and persist/list policy,
   score-run, fairness-analysis, review-action, summary-invocation, and portfolio-memory PM-quality
   source reads under the trusted tenant scope. Write-request admission also rejects malformed or
   negative `Content-Length`, pre-rejects a declared oversized body, and then streams and measures
   authorized request bytes before replaying the bounded body unchanged to route handling; preserve
   this received-byte enforcement so missing or under-declared lengths cannot bypass
   `ENTERPRISE_MAX_WRITE_PAYLOAD_BYTES`,
3. architecture, complexity, exact duplicate implementation non-regression, dependency-hygiene,
   and dead-code gates are active in Remote Feature Lane, Pull Request Merge Gate, and Main
   Releasability; the separate Quality Baseline workflow remains report-only for expanded trend
   capture,
   and static-analysis tool versions should retain bounded upper ranges until a branch intentionally
   absorbs and fixes the new rule family. PR #625 pins Ruff below the next minor family after CI
   resolved `ruff 0.16.0` and surfaced repository-wide pre-existing Linux executable-bit/import
   findings unrelated to the RFC-0002 temporal-evidence change. Checked-in quality reports pin
   clean branch validation to their recorded immutable baseline SHA;
   do not replace that behavior with moving `origin/main` comparison or normalize away absolute
   measurements. The PR merge gate validates static and test integration on GitHub's merge result,
   while a separate blocking job checks report freshness on the immutable pull-request head; this
   prevents unrelated base-branch changes from making branch-owned evidence stale. Dirty worktrees
   and missing recorded refs retain the safe `origin/main` fallback.
4. PR-grade validation includes coverage-backed full test execution,
   Solver tests load a shared `cvxpy`/`numpy` prerequisite directly during collection and execute
   unconditionally because those packages are required `dev` dependencies for test lanes (and
   remain in the optional `solver` extra for production installs). Do not suppress the collection
   prerequisite or reintroduce availability probes, import timeouts, or skip markers: a missing,
   slow, or broken solver test runtime is a failed prerequisite and must fail the lane rather than
   alter its coverage denominator.
5. `make static-quality-gates` includes `make test-family-inventory`, which blocks loss of the
   measured API/runtime, contract/governance, observability/security, domain/lifecycle/methodology,
   and integration/runtime proof-family floors in `quality/test_family_inventory_baseline.json`;
   coverage remains a separate combined execution floor rather than the only test-quality signal,
5. Feature, PR Merge, and Main Releasability workflows must invoke repo-native Make test targets
   (`make test-unit` and `make test-${{ matrix.suite }}-coverage`) instead of raw workflow-level
   pytest commands. `UNIT_TESTS`, `INTEGRATION_TESTS`, and `E2E_TESTS` provide focused path
   overrides without bypassing the Make contract,
6. host/runtime coexistence assumptions matter for canonical front-office startup,
7. README changes should preserve the local Docker runtime contract language enforced by
   `tests/unit/test_local_docker_runtime_contract.py`,
8. DPM supportability and OpenAPI-facing docs changes should respect the targeted contract tests in
   `tests/unit/dpm/contracts/test_contract_openapi_supportability_docs.py`,
9. current operational evidence docs under `docs/demo/` and runbooks should preserve canonical
   `lotus-manage` service, image, and ingress identity while clearly labeling historical local-only
   debug paths.
10. app-level demo certification is repo-native through `make demo-certify`; it is exposed through a
   manual GitHub workflow with uploaded evidence and report-only command-contract coverage until the
   canonical live stack is proven stable inside CI.
11. RFC/docs/wiki/context work must include stranded-truth reconciliation before RFC start, final
   closure, post-merge audit, and move-on to the next RFC. Run `git fetch origin --prune` and
   `git branch -r --no-merged origin/main`, inspect unmerged branches touching `docs/rfcs/`,
   `wiki/`, `README.md`, `REPOSITORY-ENGINEERING-CONTEXT.md`, `AGENTS.md`, contracts, standards,
   OpenAPI/vocabulary, migrations, CI workflows, or supported-features material, and classify each
   branch as `must-merge`, `cherry-pick`, `superseded`, `delete`, or `active`. This is mandatory
   because RFC-0036 through RFC-0042 work previously exposed a failure mode where
   `docs/rfcs/RFC-worktobedone.md` and an RFC-0041 post-closure documentation correction were
   stranded on unmerged side branches instead of reaching `main`.
10. PR auto-merge follows the platform linear-history posture: `.github/workflows/pr-auto-merge.yml`
    uses `LOTUS_AUTOMERGE_TOKEN`, queues `gh pr merge --auto --rebase --delete-branch`, skips
    cleanly with a warning when the token is absent, and is protected by `make workflow-policy-gate`.
    The helper must not authenticate with `GITHUB_TOKEN` or queue merge commits.
11. Exact-main releasability is **per commit, not per merged pull request**
    (issue #659). `.github/workflows/merged-pr-main-releasability.yml` listens for merged `main`
    pull requests and dispatches `.github/workflows/main-releasability.yml` once for **every
    revision the pull request put on main**, each pinned to its own immutable
    `main-releasability-<sha>` tag. Dispatching only the head left 38 of 40 recent commits with no
    verdict at all: this repository merges by rebase, so a merged PR of N commits puts N on main,
    and a commit that was never the head still becomes the deployed tree on rollback and bisect.
    A run that is never created is not a failure, so nothing else reports the loss.

    Three constraints govern any future change here:

    - **Rebase-only merging is a prerequisite, not an assumption.** The enumeration is correct only
      because squash and merge-commit are disabled. The dispatcher asserts
      `[squash, merge, rebase] == [false, false, true]` and fails loudly if that changes, because
      gating the wrong trees while reporting success is worse than the gap it closes.
    - **Enumeration and dispatch are separate jobs on purpose.** The dispatch step must stay a flat
      lookup / conditional ref creation / dispatch sequence: `scripts/workflow_policy_gate.py`
      validates that structure, and wrapping it in a shell loop nests it out of that control's
      reach. A matrix fed from the enumerating job's output gives one un-nested dispatch per
      revision, runs sequentially so concurrent tag creation cannot race, and keeps the dispatched
      SHA bound to the merge event.
    - **One coherent SHA binding.** The ref name, the mismatch check, the created ref SHA and the
      dispatched `expected_sha` must all use the same variable. A mixed binding checks out one
      revision and asserts against another; the resulting failure is a *verdict*, which the
      coverage audit would count as evaluation - falsely reporting coverage.

    `.github/workflows/main-gate-coverage-audit.yml` runs `scripts/audit_main_gate_coverage.py`
    daily with `--fail-on-gap` and is fail-closed by design: a missing `gh`, an unfetchable run
    listing, or a cancelled run all fail rather than pass, because only a verdict-bearing run
    (success or failure) evidences evaluation. Its `Fixed Historical Recovery Ledger` names the
    inclusive `393ee58d..d5c92dbf` 100-commit population observed in Cycle 6; it must stay fixed
    until each previously ungated revision carries a governed verdict, so a rolling window cannot
    age the evidence gap away. Its separate recent-window job remains the live-control watch. A
    failing historical verdict is recorded outcome, not missing coverage or current-release proof.
    Its permissions are read-only - a watchdog able to dispatch could manufacture the coverage it
    audits.

    The main releasability workflow keeps manual `workflow_dispatch` support but must not also
    carry a direct `push` trigger, because that creates duplicate automatic proof runs for the same
    merged SHA. `make workflow-policy-gate` enforces the dispatcher contract, the coherent binding
    and the duplicate-trigger prohibition; `make test-family-inventory` requires new guard suites to
    declare their family.

## Standards And RFCs That Govern This Repository

Most relevant current governance:

1. `../lotus-platform/rfcs/RFC-0066-lotus-advise-to-lotus-advise-and-lotus-manage-split.md`
2. `../lotus-platform/rfcs/RFC-0067-centralized-api-vocabulary-inventory-and-openapi-documentation-governance.md`
3. `../lotus-platform/rfcs/RFC-0071-centralized-environment-scoped-service-addressing-and-ingress-governance.md`
4. `../lotus-platform/rfcs/RFC-0072-platform-wide-multi-lane-ci-validation-and-release-governance.md`
5. `../lotus-platform/rfcs/RFC-0073-lotus-ecosystem-engineering-context-and-agent-guidance-system.md`
6. `../lotus-platform/rfcs/RFC-0082-lotus-core-domain-authority-and-analytics-serving-boundary-hardening.md`
7. `docs/standards/RFC-0082-upstream-contract-family-map.md`

## Known Constraints And Implementation Notes

1. management/advisory boundary clarity remains a real quality concern after the split,
2. canonical local host runtime matters because port coexistence with `lotus-advise` is intentional,
3. local `pip check` and project-scoped security posture still matter for repo truth here,
4. stateful `portfolio_id` mode is disabled by default through
   `DPM_STATEFUL_CORE_SOURCING_ENABLED=false`; integration capabilities must not publish
   `stateful` unless `DPM_CAP_INPUT_MODE_PORTFOLIO_ID_ENABLED=true`,
   `DPM_STATEFUL_CORE_SOURCING_ENABLED=true`, `DPM_CORE_BASE_URL` is configured, and any configured
   core resolver path is not the retired monolithic `dpm-execution-context` route,
5. `DpmModelPortfolioTarget:v1`, `DiscretionaryMandateBinding:v1`,
   `InstrumentEligibilityProfile:v1`, `PortfolioTaxLotWindow:v1`,
   `MarketDataCoverageWindow:v1`, and `DpmSourceReadiness:v1` are the core source products used to
   prove stateful manage execution against the canonical mandate portfolio,
6. this repo should stay operationally aligned with gateway and platform startup sequences,
7. repo-local `wiki/` content should stay concise, operator-focused, and derived from repo truth
   rather than duplicating the full `docs/` tree,
8. enterprise audit and readiness surfaces must emit `lotus-manage` service identity rather than
   stale split-era names; the `enterprise_readiness` emitter's structured `audit` field must survive
   the shipped `JsonFormatter` as a whitelisted, redacted envelope. Registered-API audit tests must
   cover identity and outcome, while asserted headers and JSON serialization must not be described
   as verified ingress identity or durable audit delivery,
9. ordinary logger `extra_fields` are a separate allowlisted scalar boundary. Credential and
   identity keys are normalized and redacted case-insensitively; unknown fields and structured
   dictionaries/lists are discarded. Keep the producer-inventory regression synchronized when a
   new operational field is intentionally introduced,
10. request observability must remain the outer application middleware envelope. Enterprise
    authorization, malformed-length, declared-size, and streamed-size refusals must retain one
    bounded completion observation, correlated Problem Details, hardened headers, and the policy
    version without invoking route persistence. Pre-routing metrics use `unmatched`, never a raw
    request path,
11. `make check` may refresh generated API vocabulary output; docs-only slices should inspect that
   diff and avoid committing timestamp-only churn when the semantic inventory is unchanged,
12. the current repo-native domain-data-product declaration intentionally records only governed
    `PortfolioStateSnapshot` input consumption through caller-supplied management request payloads;
    market-data and future stateful `portfolio_id` resolution must be added only after upstream
    producer approval and an explicit source-data retrieval design.
13. target-state RFC-0037 through RFC-0043 work may redesign or remove stale manage APIs because
    no production downstream dependency is assumed for the revamp surface. Any downstream usage
    discovered during implementation should be documented and migrated to the certified target
    contract rather than preserved through permanent compatibility aliases.
14. durable RFC control artifacts such as `docs/rfcs/RFC-worktobedone.md`, source maps, proof
    indexes, and supported-feature ledgers must be referenced from stable navigation docs and pinned
    by `tests/unit/test_documentation_current_state.py` or an equivalent docs/current-state test
    whenever practical.
15. Core and Risk source-product adapter mappings must fail closed on incomplete response payloads.
    Do not reintroduce implicit `USD`, `v1`, empty-fingerprint, empty-section, or zero-metric
    defaults for missing source facts. Valid zero values are allowed only when explicitly supplied
    by the source response and must stay distinguishable from omission.
    The mandatory Core mandate binding must be accepted before model resolution, and the model
    target product must be accepted before dependent portfolio-source calls. Model-target identity
    and as-of date must exactly match the requested selectors; explicit caller-selected models
    remain valid only when the returned identity matches that selection.
    Core `ClientRestrictionProfile:v1` is an optional product only when unavailable. A present
    profile with mismatched portfolio/date/mandate or a scoped rule without usable selectors is
    invalid source evidence and must not be swallowed by the optional-source fallback. Preserve
    intentional selector-free `client` and `mandate` restrictions.
    Mandatory hard client-policy qualification is shared across stateful direct simulation and
    construction methods, not owned by `ESG_AWARE`. A verified empty profile permits evaluation;
    unavailable profile or missing rule classification must not infer permission. Direct stateless
    simulation is a raw counterfactual with review-required consumer gate, not an approval. Source
    profile changes are part of the direct simulation request hash. Instruction-package release
    refuses runs without READY source-backed policy evidence and matching portfolio scope; wave
    simulation must propagate that evidence before end-to-end enforcement can be claimed.
    Preserve `DiscretionaryMandateBinding:v1` cash reserve as an effective-dated target, including
    binding version and lineage. Apply it to heuristic and solver construction, reject conflicting
    request or tolerance overrides, and report post-trade deviation; do not reinterpret it as a
    cash band or make successful target scaling review-required. Reject bindings outside the
    requested date and persist lineage on construction runs. Require the producer's total-portfolio
    market-value scope, portfolio-base-currency basis, mandate authority and explicit false
    consumer-override permission; never infer these facts locally. Invalid legacy targets are
    incomplete, not ordinary absence. Reject them at shared binding DTO ingestion so mandate
    refresh cannot persist invalid evidence before rebalance policy resolution. Retained legacy
    contexts remain readable, but cannot execute a non-null source target without its authority
    metadata. Enforce explicit no-override authority even for an absent source target; preserve the
    separately modeled request-level cash buffer without inventing a mandate target.
    Native HTTP/PostgreSQL reserve proof
    uses `tests/integration/dpm/supportability/test_source_cash_reserve_network.py` with the controlled
    source fixture; it is not real Core, bank IAM or capacity evidence. Wave stateful item inputs
    derive scope from the persisted wave and reuse this resolver. Durable admission freezes the
    effective request, full source context and original options; workers validate hashes and exact
    retries never refetch Core. Serialize source resolution/admission by tenant/idempotency key
    using the repository guard; PostgreSQL uses a separate coordination session, not a financial
    transaction held across network I/O. Validate binding portfolio/mandate/model identity before
    downstream reads; verify whole input hashes before accepting missing financial inputs.
    Stateless hashes remain unchanged. Source-ready items require a
    matching known mandate revision; review-required health is not promoted. Native wave proof
    uses separately identified complete caller-supplied synthetic health, not Core ingestion;
    current source cash-band/turnover gaps still block real source-backed wave qualification.
    For Risk-event waves, reject duplicate candidate IDs before the authority call and verify
    the returned event/date, affected/excluded uniqueness, candidate membership, and mandate echo
    before constructing wave source refs or writing a wave. Excluded members are validation
    evidence, not wave items; do not recompute Risk impact scores locally.
14. Tax-aware construction is evidence-gated. When `enable_tax_awareness=true`, sell candidates
    require complete open-lot coverage from `PortfolioTaxLotWindow:v1` and lot-cost FX where
    needed; missing lots, partial lots, closed/depleted-only lots, or missing lot-cost FX must block
    tax-aware output rather than falling back to a normal non-tax-aware sell.
15. Core `DpmPortfolioUniverseCandidate:v1` campaign-wave sourcing must consume the producer's
    canonical `content_hash`/`source_digest` identity for page-level campaign source refs.
    `source_batch_fingerprint` is optional upstream source-batch lineage and must not be required or
    silently reused as the canonical content hash when Core returns a valid no-batch response. Manage
    must fail closed on missing, blank, malformed, or conflicting content identity before publishing
    Core-sourced bulk-review campaign membership as READY.
16. `mandate_version` is TEXT holding `str(binding_version)`, and the in-memory and PostgreSQL
    mandate stores must order it identically, because both answer "which version is current" and a
    disagreement resolves the same data to different twins depending on configuration. The contract
    is: digit-only versions compare by significant-digit length then by the digits, non-digit
    versions sort last, and the raw column breaks ties so `'1'` precedes `'01'`. Three specific
    traps are worth knowing before touching it. Do not compare through a numeric conversion:
    `int()` raises above `sys.get_int_max_str_digits()` (4300 by default) and `NUMERIC` overflows
    past 131,072 digits, so a version one store accepts can abort the other. Use `re.fullmatch`
    rather than `re.match`, because Python's `$` also matches before a trailing newline while
    PostgreSQL's `~` does not, so `'9\n'` is numeric on one side only. Keep `COLLATE "C"` on the SQL
    comparisons so byte order matches Python's code-point order under any database collation. A
    shared adversarial corpus in `tests/support/mandate_version_corpus.py` is asserted by both the
    unit suite and the database lane so a divergence fails on one side rather than passing quietly
    on both.
17. Minimum-trade suppression selects the request threshold before the shelf fallback, then
    normalizes that selected `Money` into the candidate security's price currency through the
    request/source-resolved `MarketDataSnapshot`. Direct quotes use `threshold/trade`; inverse
    quotes use `trade/threshold` and an exact Decimal reciprocal. Missing, zero, or negative quotes
    must add blocking data-quality evidence and must never fall back to comparing unqualified
    numeric amounts. Diagnostics preserve the configured threshold, normalized threshold, observed
    quote, applied conversion rate, direction, candidate side, and outcome.

## Context Maintenance Rule

Update this document when:

1. management workflow ownership changes,
2. runtime or coexistence assumptions with `lotus-advise` change,
3. repo-native commands or CI expectations change,
4. upstream or downstream integration posture changes materially,
5. RFC-0082 contract-family classification changes,
6. current-state rollout posture changes,
7. README or `wiki/` structure changes the repository-local onboarding or operator navigation model.

## Cross-Links

1. `../lotus-platform/context/LOTUS-QUICKSTART-CONTEXT.md`
2. `../lotus-platform/context/LOTUS-ENGINEERING-CONTEXT.md`
3. `../lotus-platform/context/CONTEXT-REFERENCE-MAP.md`
4. `../lotus-platform/context/Repository-Engineering-Context-Contract.md`
5. [Lotus Developer Onboarding](../lotus-platform/docs/onboarding/LOTUS-DEVELOPER-ONBOARDING.md)
6. [Lotus Agent Ramp-Up](../lotus-platform/docs/onboarding/LOTUS-AGENT-RAMP-UP.md)
