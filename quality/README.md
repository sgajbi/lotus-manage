# Manage Quality Evidence

This directory stores quality rules, scorecards, baselines, and generated review evidence used by
repo-native quality gates.

| File family | Purpose | Owner command |
| --- | --- | --- |
| `*_rules.md` | Human-readable governance rules for API and architecture quality. | Keep aligned with Make targets and CI. |
| `*_report.md` | Generated or refreshed quality reports; their recorded baseline keeps clean branch checks stable when `origin/main` advances. | `make quality-report-gate` |
| `duplicate_*` | Duplicate implementation inventory and baseline. | `make duplicate-implementation-gate` |
| `test_family_inventory_baseline.json` | Baseline floors for semantic test proof-family breadth and uncategorized-test exceptions. | `make test-family-inventory` |
| `quality_scorecard.md` | Current repository quality scorecard. | `make static-quality-gates` or the focused owning gate. |

When changing generated quality evidence, document the command used and avoid hand-editing numbers
without regenerating or proving the source. Use focused gates for quick proof and `make
static-quality-gates` before PR readiness when quality posture changed.
