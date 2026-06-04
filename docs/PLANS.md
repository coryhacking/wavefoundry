# Plans

Owner: Engineering
Status: active
Last verified: 2026-06-04

Hub for in-flight planning work. Active change documents live here until admitted into a wave, at which point **Prepare wave** relocates them into `docs/waves/<wave-id>/`.

## Active Plans

- [`1p397-bug chunker-mega-chunk-fallback-for-unstructured-prompts`](plans/1p397-bug%20chunker-mega-chunk-fallback-for-unstructured-prompts.md) — universal oversized-chunk guard at the chunker dispatcher level (covers markdown, plain text, YAML, JSON, TOML, HTML, XML); markdown gains structural-unit awareness (lists kept whole then per-item; tables kept whole then per-row with header preserved). Surfaced during wave `1p35d` (C3 `1p35j`). Slated for a follow-on wave that closes alongside `1p35d` under one **1.5.0** tag (joint release; both waves' work absorbed by consumers in a single upgrade).
- [`1p399-bug indexer-drift-detection-between-file-meta-and-lance`](plans/1p399-bug%20indexer-drift-detection-between-file-meta-and-lance.md) — incremental-update reconciliation cross-checks `file_meta` against the Lance chunks table; drifted paths force re-chunk + re-embed regardless of hash match. Companion to `1p397`. Slated for the same follow-on wave that ships jointly with `1p35d` under the **1.5.0** tag.
- [`1p3ao-feat dynamic-workflows-framework-application`](plans/1p3ao-feat%20dynamic-workflows-framework-application.md) — roadmap doc inventorying where Claude Code dynamic workflows apply across the framework: all councils (wave + archetype + delivery + red-team) as parallel fan-outs with cross-checked synthesis; install Phase 2 as a 3-stage parallel workflow; guru with multi-path code exploration and confirmation-bias cross-checks; plan-feature multi-angle drafting; wave-readiness multi-dimension audit; coherence/garden/distill fan-outs. First experiment is the per-chunker audit step inside `1p397`. Individual surfaces become their own admitted changes.
- [`1p3b5-enh vendor-docs-lint-exclusions-via-framework-pack`](plans/1p3b5-enh%20vendor-docs-lint-exclusions-via-framework-pack.md) — relocate `docs-lint-exclusions.md` from wavefoundry-source-only `docs/references/` into the framework pack at `.wavefoundry/framework/docs/lint-exclusions.md` so consumers receive the doc on every upgrade. Surfaced as wave 1p35d C6 finding F2.
- [`1p3b6-enh upgrade-dry-run-preview-of-migration-effect`](plans/1p3b6-enh%20upgrade-dry-run-preview-of-migration-effect.md) — extend `--dry-run` to simulate the C7 migration's effect (which files would be modified / deleted / rewritten) without performing mutations. Preview-log written to `.wavefoundry/logs/upgrade-migration-1.5.0.preview.log` with a distinct filename from the real-run report. Surfaced as wave 1p35d C7 advisory C7-DC-1 / pre-close finding F3.
- [`1p3b7-enh upgrade-migration-tier-2-hardening`](plans/1p3b7-enh%20upgrade-migration-tier-2-hardening.md) — three small bundled enterprise-deployment improvements: F4 (`.claude/settings.local.json` strip), F5 (component-level test for dashboard empty-Agents-panel guidance), F6 (recursive walk for Role: backfill so enterprise nested layouts like `docs/agents/teams/<team>/*.md` are covered). Surfaced as wave 1p35d pre-close review findings.

## Template

New change documents use `docs/plans/plan-template.md`. Generate change IDs with:

```bash
python3 .wavefoundry/framework/scripts/lifecycle_id.py --kind <kind> --slug <slug>
```

Kind options: `feat`, `bug`, `enh`, `change`, `doc`, `debt`, `ref`, `task`, `maint`, `ops`.
