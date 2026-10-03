# Source-Bound Wave Evidence

Issue #733 adds Core-bound item inputs to synchronous and durable wave simulation. This is
controlled-contract evidence, not execution of Core, bank IAM, capacity, approval or booking proof.

## Contract

Use `input_mode=stateful` with a wave-item or unique portfolio selector and optional engine options.
Manage derives tenant, business date, portfolio, mandate and model from the persisted checked wave.
The shared single/batch resolver enforces mandate reserve authority and retains lineage. A known
checked mandate revision must match. Caller snapshots, mixed modes, arbitrary source context,
unknown options and changed source controls are refused before financial/admission writes.

Durable admission retains the effective financial request, full source context and original options
in existing JSON storage. Exact retries never refetch Core. Workers verify input/context hashes;
corruption is non-retryable. Existing leases, fencing, concurrency budgets and stateless hashes are
unchanged. Synchronous simulation remains bounded and lacks durable admission/recovery guarantees.

## Native Proof

`tests/integration/dpm/waves/test_source_bound_wave_network.py` uses real PostgreSQL and unmodified
native HTTP APIs. Mandate refresh, explicit health input, wave creation/source-check, admission,
worker execution, alternative-set and artifact reads are supported APIs; no database readiness or
financial rows are injected.

- Independent USD arithmetic: `975 * 100 + 2500 = 100000`; a 2% target leaves 2,000 cash and 980 shares,
  so construction buys five shares. Binding version 7, effective dates and authority survive artifacts.
  Zero/absence each yield 1,000 shares and no cash; 50% yields 500 shares and 50,000 cash.
- API replacement with the controlled producer offline preserves artifact reads and exact replay;
  durable work still executes from frozen inputs. Changed durable options conflict rather than refetch.
- Conflicting target, tolerance and buffer; invalid/unknown options; and changed binding revision
  leave no financial runs or admitted operations. Foreign artifact reads return 404.
- Unit guards prove missing revision, altered frozen economics and missing/invalid/context-hash
  evidence fail closed. Existing wave regression suites retain stateless behavior.

## Readiness Dependency

Core's current mandate product does not supply contractual cash-band or turnover applicability.
Raw refresh therefore remains `PENDING_REVIEW`; source-check yields `REVIEW_REQUIRED`, and stateful
wave input is refused without Core resolution or financial writes. Core
[issue #1086](https://github.com/sgajbi/lotus-core/issues/1086) owns publication; Manage must then consume
the governed contract. Do not invent controls, write readiness flags or bypass this gate.

Positive tests separately identify a complete `CALLER_SUPPLIED` synthetic health input. It is not
Core ingestion or proof that Core supplied missing limits. Keep #733 open for actual source-backed
wave qualification. Broader recovery, representative methods/restrictions and measured capacity
remain in #715; review/merge/exact-main/wiki receipts belong on the owning GitHub issues.
