# RFC-0040 Slice 8 Gateway and Workbench Realization Evidence

This slice aligns downstream realization RFCs after the manage proof-pack contracts became stable.
It does not implement Gateway routes, Workbench UI, report materialization, AI memo generation, or
full front-office product realization.

## Downstream Commits

| Repository | Branch | Commit | Evidence |
| --- | --- | --- | --- |
| `lotus-gateway` | `feat/dpm-command-center-composition-rfc` | `6099ffe` | `docs/rfcs/RFC-0098-dpm-command-center-composition-contract.md`, `tests/unit/test_rfc0098_documentation.py` |
| `lotus-workbench` | `feat/dpm-command-center-experience-rfc` | `4b150d6` | `docs/rfcs/RFC-0098-dpm-mandate-command-center-experience.md`, `tests/unit/test_rfc0098_documentation.py` |

## Contract Decisions

1. `lotus-manage` remains the authoritative source for proof-pack JSON, section states, section
   hashes, aggregate content hash, source hashes, lineage, retention, Markdown summary,
   report-input payloads, and AI-evidence payloads.
2. `lotus-gateway` composes a Workbench-facing command-center contract from manage proof-pack APIs,
   report materialization posture, archive posture, entitlement posture, and workflow affordances.
   It must not rebuild proof-pack sections or recalculate proof-pack hashes.
3. `lotus-workbench` renders Gateway truth only. Browser code must not call `lotus-manage`,
   `lotus-report`, or `lotus-ai` directly and must not generate proof-pack facts, report inputs,
   AI evidence, or AI memos.
4. `lotus-report` remains the report materialization owner. It is not proof-pack authority.
5. `lotus-ai` remains the AI execution and memo owner. RFC-0043 governs AI PM copilot outputs.

## Gateway Alignment

`lotus-gateway` RFC-0098 now consumes the following manage APIs as the proof-pack authority:

1. `POST /api/v1/rebalance/proof-packs`,
2. `GET /api/v1/rebalance/proof-packs/{proof_pack_id}`,
3. `GET /api/v1/rebalance/proof-packs/{proof_pack_id}/summary.md`,
4. `GET /api/v1/rebalance/proof-packs/{proof_pack_id}/report-input`,
5. `GET /api/v1/rebalance/proof-packs/{proof_pack_id}/ai-evidence-input`.

The RFC and wiki source explicitly require Gateway to preserve manage-owned identifiers, section
states, hashes, reason codes, source refs, lineage refs, report-input refs, and AI-evidence refs.

## Workbench Alignment

`lotus-workbench` RFC-0098 now defines a proof-pack review workspace that must render Gateway
composition only. Required user-facing panels are:

1. proof-pack header,
2. section matrix,
3. Markdown preview,
4. evidence drawer,
5. report and AI handoff rail.

The RFC distinguishes manage-ready handoff payloads from unavailable downstream outputs. For
example, the UI must represent `report-input ready but report output unavailable` and
`AI-evidence ready but AI memo unavailable` as truthful states instead of implying complete report
or AI product support.

## Validation

Gateway validation:

```bash
python -m pytest tests\unit\test_rfc0098_documentation.py -q
python -m ruff check tests\unit\test_rfc0098_documentation.py
git diff --check
..\lotus-platform\automation\Sync-RepoWikis.ps1 -CheckOnly -Repository lotus-gateway
```

Results:

1. documentation-contract test passed,
2. ruff passed,
3. diff whitespace check passed with only expected LF-to-CRLF warnings,
4. wiki check failed as expected because repo-authored wiki source changed and must be published
   after merge.

Workbench validation:

```bash
python -m pytest tests\unit\test_rfc0098_documentation.py -q
python -m ruff check tests\unit\test_rfc0098_documentation.py
git diff --check
..\lotus-platform\automation\Sync-RepoWikis.ps1 -CheckOnly -Repository lotus-workbench
```

Results:

1. documentation-contract test passed,
2. ruff passed,
3. diff whitespace check passed with only expected LF-to-CRLF warnings,
4. wiki check failed as expected because repo-authored wiki source changed and must be published
   after merge.

## No Supported-Feature Promotion

Slice 8 completes downstream realization RFC alignment only. RFC-0040 remains in progress.
Gateway implementation, Workbench implementation, canonical browser validation, report
materialization, AI memo generation, live evidence capture, final gold-pass assessment, PR merge,
and wiki publication remain later work.
