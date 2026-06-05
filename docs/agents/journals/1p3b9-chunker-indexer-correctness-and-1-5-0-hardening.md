# Journal - Chunker Indexer Correctness And 1.5.0 Hardening

Owner: Engineering
Status: active
Role: wave-coordinator
Last verified: 2026-06-04

Actor: wave-coordinator
Schema version: 1.0
Last distilled: 2026-06-04

wave-id: `1p3b9 chunker-indexer-correctness-and-1-5-0-hardening`

## Operating Identity

- Role: wave-coordinator — coordinating a five-change wave that closes the index-quality defects `1p35d` C3 surfaced (chunker mega-chunks, `file_meta` ↔ Lance drift) plus the Tier 2 enterprise-deployment findings from the `1p35d` pre-close review (lint-exclusions vendoring, upgrade `--dry-run` preview, settings.local strip + recursive Role: backfill + dashboard empty-state component test).
- Responsibilities include: hold the `CHUNKER_VERSION` bump invariant for `1p397` (without it, the fix stays latent on every consumer); ensure `1p397` and `1p399` are tested independently AND together so the synergy is observable; preserve the joint 1.5.0 release contract with `1p35d` (no intermediate version tag); validate that `1p3b6` preview output matches `1p3ay` real-run report shape so operators can correlate.

## Salience Triggers

- **High:** any commit landing changes to `chunk_markdown` or the universal-guard helper without bumping `CHUNKER_VERSION`. Watchpoint — the auto-escalation in `indexer.py:1880-1897` is gated on the constant; missing bump leaves consumers with stale-shape chunks indefinitely.
- **High:** any change to the C7-from-`1p35d` migration helpers (`_backfill_role_field_on_agent_docs`, `_delete_pycache_hook_launchers`, `_strip_pycache_row_from_claude_settings`) in `upgrade_extensions.py` that doesn't also extend the `1p3b6` preview helper covering the same surface — drift between real-run and preview helpers is exactly what `1p3b6` exists to prevent.
- **High:** any move to tag a version `1.5.0` before this wave closes. Joint-release contract with `1p35d`: no intermediate `1.5.0-rc` or similar; the tag fires only when both waves are closed.
- **Medium:** discussion of retiring `1p35d` C3's `get_seed` disk-fallback. Follow-up work for a later wave; out of scope here, but capture the trigger condition (C1 + C2 of this wave landed AND verified against the half-the-seed-catalog defect class).
- **Medium:** structural-unit decomposition behavior for non-prompt markdown — `1p397` AC-9 specifies "decomposition fires only when a unit actually exceeds `MAX_CHUNK_CHARS`" for project-layer doc shapes. Drift toward eager re-splitting (mimicking the seed/prompt path) would break the project-index chunk-shape contract.
- **Low:** routine test-suite churn unrelated to chunker / indexer / upgrade-extension surfaces.

## Default Stance

- Defer to operator judgement on sequencing. The five changes are admit-time orthogonal: C1 and C2 share the "index quality" theme but are technically independent; C3, C4, C5 are smaller and can land in parallel.
- When in doubt about chunker chunk-shape edges, write a fixture-based test BEFORE implementing — the chunker's surface is broad enough that "test-after" implementation produces shape regressions that are subtle and slow to surface.

## Memory Responsibilities

- Capture every observed chunk-shape change during C1 implementation with a concrete before/after example so future chunker work has a regression target catalog.
- Record the joint-release contract decision (no intermediate tag, both waves close before 1.5.0) so a future close-wave operator doesn't accidentally tag mid-flight.
- Track whether `1p397` test fixtures expose any additional chunker edge cases that the existing `test_every_numbered_seed_reachable` generative test missed — if so, expand the generative test's assertion set.

## Active Signals

- Wave admitted 5 planned changes on 2026-06-04. All five had complete change docs (Decision Logs + ACs + Tasks) at admission time, surfaced as findings during `1p35d` close.
- Ships jointly with closed wave `1p35d` (commit `11b3af4`) under the **1.5.0** tag.

## Distillation

- (No distilled lessons yet — this wave just opened. Capture lessons as they accumulate during implementation; promote into this section on close-wave review.)

## Promotion Evidence

- (No promoted entries yet. Promotion targets when entries accumulate: `seed-130` schema fields, the wave-coordinator persona doc at `docs/agents/personas/wave-coordinator.md`, or framework-level memory under `.wavefoundry/framework/`.)

## Retirement And Supersession

- (No retired entries yet.)

## Governance

- This journal follows the operating-memory schema defined in `seed-130`. The wave-coordinator is the sole writer during wave lifetime; on close, the delivery-council review reads and may flag entries for distillation.
- Watchpoint salience markers in this journal are the load-bearing follow-up triggers; do not delete a `High`-severity entry without recording the resolution in this section.
