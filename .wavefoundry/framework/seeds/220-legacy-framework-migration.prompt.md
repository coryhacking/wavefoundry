# 220 - Legacy Framework Migration (Internal Helper)

**Applicable when:** the project has a pre-existing framework or convention layer being migrated INTO Wavefoundry.

Intent:

- Migrate a project's repository from legacy non-wave context footprints to Wavefoundry's `.wavefoundry/framework` layout.
- Treat the legacy footprint as historical source material that should be captured in the reserved legacy baseline wave, then normalized into the project's first installed wave layer (`wave-0`) in the repository rather than as a continuing parallel framework mode.

Migration tasks:

1. Detect legacy references to:
   - legacy non-wave context framework packs or paths under `agent-workflows/`
   - legacy init/upgrade phrases from older context systems
   - repositories whose installed context should now be classified as `wave-0`
2. Migrate those references to:
   - `.wavefoundry/framework/`
   - **`Init Wavefoundry`** (legacy: **`Init wave framework`** / **`Init wave context`**)
   - **`Upgrade Wavefoundry`** (legacy: **`Upgrade wave framework`** / **`Upgrade wave context`**)
3. Update dispatcher references so `wf docs-lint` and `wf docs-gardener` (routed by the `wf` shim pair through `wf_cli.py`) stop pointing at the legacy framework path. **Agent-facing docs** should still prefer MCP **`wf_validate_docs`** / **`wf_garden_docs`** over shelling to the `wf` dispatcher when MCP is available (`seed-050`).
4. Create or preserve the reserved `wave-0` baseline wave when legacy pre-wave docs are still the source corpus:
   - Use `00000 wave-zero-plans-and-specs` as the `wave-id`
   - Give it a `Title` that starts with `Legacy`
   - Write everything into `docs/waves/00000 wave-zero-plans-and-specs/wave.md` as a single file — do not create subdirectories inside the wave folder
   - **Physically move** completed plan files from `docs/plans/completed/` into `docs/waves/00000 wave-zero-plans-and-specs/`; `docs/plans/completed/` must be empty after baseline capture; do not merely reference them at their original location
   - `wave.md` must include: all required wave anchors, a `## Corpus` table indexing each captured plan/change (change ID, file path within the wave folder, kind, title), a `## Wave Summary` recording what was detected, what was seeded, and which active plans were excluded, one `Change ID` per captured plan at `complete` status, explicit review checkpoints with real findings, and a `## Reports` section summarizing archived reports
   - Move all reports from `docs/reports/` into `docs/waves/00000 wave-zero-plans-and-specs/` alongside the plan files; `docs/reports/` must be empty after baseline capture; the wave folder is self-contained with all artifacts from the pre-wave period
5. Backfill missing wave-context-only artifacts:
   - prompt-surface manifest
   - waves root
   - journals root
   - persona docs and persona journals when evidence supports them
   - expanded workflow-config sections for wave execution, memory, persona generation, and prompt generation
   - generated index and session-handoff artifacts when missing
   - canonical wave-context prompt docs when missing
6. Migrate or normalize lifecycle workspace expectations:
   - use `docs/plans/<change-id>.md` as the single consolidated change document for each in-flight change; do not create or continue to use `docs/specs/changes/` as an in-flight workspace
   - if any active `docs/specs/changes/<id>/` or `docs/product-specs/changes/<id>/` packages still exist, fold their `proposal.md` rationale, `spec.md` requirements, and `tasks.md` tasks into the corresponding plan file as `## Rationale`, `## Requirements`, and `## Tasks` sections, then remove the now-redundant spec folder
   - after migrating all packages, **remove the legacy workspace directories** if they are now empty: `docs/exec-plans/`, `docs/product-specs/`, `docs/gaps/`, `docs/performance/`, `docs/specs/changes/`; do not leave empty shell directories
   - if a `docs/tasks.md` pre-wave scratch backlog exists, review it for items worth promoting to `docs/references/tech-debt-tracker.md`, then remove it — a flat uncategorized task list has no place in the wave model
   - if `docs/gaps/missing-docs.md` exists alongside `docs/missing-docs.md`, consolidate into `docs/missing-docs.md` (the canonical wave-context path) and remove `docs/gaps/` — update any references to the old path in journals, session-handoff, or agent docs
   - if `docs/performance/` exists as a legacy location for a performance budget doc, check whether `docs/architecture/performance-budget.md` now exists with richer content; if so, remove `docs/performance/` and update any references
   - if legacy lifecycle roots or alternate spec workspaces exist, preserve their contents before retiring them
   - stop and report conflicts rather than overwriting divergent lifecycle artifacts
   - do not move durable `docs/specs/*.md` behavior contracts — they are canonical reference docs that stay in place
7. Execute the full baseline wave closure procedure so durable lessons are not left trapped in moved source files:
   - Run applicable agent review lanes (architecture, QA, docs-contract, security, performance) for the change types present in the baseline and document real findings — not pass/fail placeholders — as review checkpoint sections in `wave.md`
   - Seed journal files with `## Observations` and `## Distillation` bullets drawn from the moved plans; do not use generic placeholder text
   - Promote reusable workflow lessons to `docs/references/project-context-memory.md`; this file must have at least one substantive entry after baseline closure
   - Update `docs/RELIABILITY.md`, `docs/ARCHITECTURE.md`, and `docs/QUALITY_SCORE.md` with any durable patterns introduced by baseline changes
   - Refresh persona agent invocation signals and failure modes when the baseline corpus reveals new user-facing patterns
   - Mark the wave `Status: completed` only after all reviews, journals, and core-doc promotions are recorded
8. Retire or rewrite stale local prompt docs and generated-doc references that still point to legacy project-context phrasing or obsolete helper names after replacement artifacts are in place.
9. Document **`Init Wavefoundry`** (legacy: **`Init wave framework`** / **`Init wave context`**) as the first-phase detector for baseline capture and **`Upgrade Wavefoundry`** (legacy: **`Upgrade wave framework`** / **`Upgrade wave context`**) as the refresh handoff for already-installed wave repos; treat **`Install Wavefoundry`** / **`Install wave framework`** / **`Install wave context`** only as convenience aliases that resolve through init detection.
10. Preserve useful repo-grown behavior instead of flattening it.
11. Flag leftover legacy artifacts for retirement only after replacement artifacts are valid.
12. If migration is interrupted, leave the repository in an additive mixed state that still points to valid prompt and wrapper paths rather than deleting the old framework first.

Migration validation checks:

- prompt docs point at `.wavefoundry/framework` rather than the legacy framework
- root wrappers point at the wave-context scripts
- workflow config contains wave/memory/persona/prompt-generation sections
- generated roots for waves, journals, and manifests exist
- generated indexes reflect the new artifact set
- any migrated `wave-0` baseline wave is a single `wave.md` (no subdirectories), plan files were physically moved into the wave folder (not left in `docs/plans/completed/`), all reports from `docs/reports/` were moved into the wave folder (not left in `docs/reports/`), `## Corpus` table paths reflect the wave folder locations, `wave.md` has a `## Reports` section summarizing archived reports, `docs/plans/completed/` is empty, `docs/reports/` is empty, review checkpoints contain actual findings, journal files have real distilled lessons, and `docs/references/project-context-memory.md` has at least one promoted entry
- legacy helper or wrapper references are either migrated or explicitly reported
- factor-review policy survives migration when still relevant

Conflict-handling rules:

- preserve durable repo-specific guidance before removing legacy wrappers or helper surfaces
- stop and report when a legacy artifact mixes durable guidance with obsolete wrapper behavior and the correct migration target is unclear
- prefer additive migration and explicit retirement over destructive cleanup
- during cleanup, remove only live working docs and deprecated files that have explicit replacements; do not remove historical references from changelogs, closed-wave records, release notes, or archived documentation — retiring a file removes the file, not the historical record of it
- when asked to clean up legacy content, scope removal to only the explicitly named deprecated artifacts; do not expand scope to adjacent historical records, prior wave archives, or references in closed wave docs without explicit instruction

Guardrails:

- Prefer additive migration before deletion.
- Preserve history where it remains useful.
- Distinguish live working docs (removable when superseded) from historical records (never removed by cleanup).
