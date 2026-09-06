# Manage Documentation

This directory contains authored repository documentation. Keep docs close to implementation truth:
when a route, contract, command, supportability posture, or ownership boundary changes, update the
nearest durable doc in the same slice.

| Area | Purpose | Edit rule |
| --- | --- | --- |
| `architecture/` | Architecture ledger, review playbooks, and cross-app handoff records. | Add issue-fix evidence to `CODEBASE-REVIEW-LEDGER.md` for governed findings. |
| `documentation/` | Project overview, engine know-how, and migration rollout notes. | Keep operational examples executable and current. |
| `operations/` | Development workflow and CI strategy. | Keep Make targets and CI lane names exact. |
| `runbooks/` | Service operations and recovery guidance. | Include observable symptoms, commands, and rollback/recovery posture. |
| `rfcs/` | RFC source, conventions, and work-to-be-done ledger. | Do not claim RFC closure until code, tests, docs, wiki, and merge posture agree. |
| `standards/` | Repo-local standards and generated API vocabulary inventory. | Regenerate or validate inventories with the owning script before committing. |
| `demo/` | Demo payloads and demo README. | Keep examples aligned with implemented API contracts. |

Wiki pages are authored in `wiki/`, not in a separate `*.wiki.git` clone. `wiki/` intentionally has
no local `README.md` because every Markdown file there is publishable wiki source.

Useful validation commands. Run them from the repository root; the last two invoke
scripts that live in the `lotus-platform` checkout, so set `$LotusRoot` to the directory
that contains your Lotus checkouts first. The expansion is quoted so a path containing a
space still works.

```powershell
$LotusRoot = "C:\src\lotus"   # the parent of lotus-manage and lotus-platform

python -m pytest tests\unit\test_documentation_current_state.py -q

python "$LotusRoot\lotus-platform\codex\skills\lotus-readme-wiki-governance\scripts\audit_wiki_quality.py" --wiki-dir wiki --changed-page Supported-Features.md

powershell -NoProfile -ExecutionPolicy Bypass -File "$LotusRoot\lotus-platform\automation\Sync-RepoWikis.ps1" -CheckOnly -Repository lotus-manage
```

`--changed-page` takes the wiki page you actually changed; `Supported-Features.md` is an
example, not a fixed argument.

When the branch intentionally changes repo-local `wiki/` source, run the same wiki check with
`-AllowUnpublishedSourceChanges` before merge, then publish after merge and rerun the strict
`-CheckOnly` command.
