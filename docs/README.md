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

Useful validation commands:

```powershell
python -m pytest tests\unit\test_documentation_current_state.py -q
python C:\Users\Sandeep\projects\lotus-platform\codex\skills\lotus-readme-wiki-governance\scripts\audit_wiki_quality.py --wiki-dir wiki --changed-page <Page>.md
powershell -NoProfile -ExecutionPolicy Bypass -File C:\Users\Sandeep\projects\lotus-platform\automation\Sync-RepoWikis.ps1 -CheckOnly -Repository lotus-manage
```

