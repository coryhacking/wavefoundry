# Wave Framework Maintenance Contract

This document defines the maintainer-facing contracts that make the Wave Framework auditable and repeatable: package completeness, repo-generation expectations, golden-path examples, and prompt-to-doc anti-drift rules.

## 1. Framework Completeness Contract

Treat the Wave Framework as complete enough for active use only when all of the following are true:

1. The shared package has a clear entry stack:
   - `README.md` indexes the package, public commands, numbered overview docs, and prompt map.
   - `001-feature-wave-framework-overview.md` explains the conceptual operating model.
   - `002-wave-framework-seeding-overview.md` explains init, upgrade, migration, and seeded-output behavior.
2. Every public command has a canonical shared prompt and a documented repo-local counterpart or generation path.
3. Shared subsystem docs exist for numbering, wave memory, personas, journals, and review, with links from the package README.
4. The package includes a maintainer-facing framework map and maintainer-facing maintenance rules.
5. Init and upgrade expectations are explicit enough to audit what a seeded project should create, refresh, preserve, or reconcile in its repository.
6. The framework includes example flows that demonstrate the intended operating model end to end.
7. The repo-local specialization story is explicit: shared docs stay generic, while seeded repositories hold local reviewers, personas, exact artifact paths, and operating exceptions.
8. The docs gate passes after framework doc changes.
9. Maintainer docs and seeded `package-wavefoundry` / `build-and-verification` text stay aligned with `scripts/build_pack.py`: `--version MAJOR.MINOR.PATCH` is required and packaging is blocked below `1.0.0`; the zip is written to `~/.wavefoundry/dist/` by default as `wavefoundry-MAJOR.MINOR.PATCH.<build>.zip`; `docs/prompts/prompt-surface-manifest.json` **`framework_revision`** must match the packaged revision unless `--skip-manifest-check` is intentionally used; then `VERSION` is stamped to `MAJOR.MINOR.PATCH+<build>` using the rightmost 4 characters of the lifecycle prefix and a source-only zip is written (no framework index is built or shipped — the framework's seeds and README fold into each project's docs index at setup/upgrade).

When one or more items above are false, treat the framework as still hardening rather than complete.

## 2. Repo-Generation Contract

### Shared vs repo-local ownership

- The shared package owns reusable concepts, prompt implementations, generic subsystem guidance, and generation rules.
- A seeded project owns its generated docs, prompt surface, local workflow config, local reviewer/persona guidance, wave state, and other repo-specific outputs in the repository.
- Do not push project-specific reviewer names, personas, or path exceptions back into the shared pack unless they become durable framework rules shared across many seeded projects.

### Init contract

**`Init Wavefoundry`** (legacy aliases: **`Init wave framework`**, **`Install wave framework`**, **`Init wave context`**, **`Install wave context`**) should create the project's first complete Wave Framework layer in the repository when no prior install already exists. At minimum it should create or normalize:

- the canonical `docs/` structure and top-level indexes
- repo-local orientation docs such as `docs/references/project-overview.md`
- the repo-local lifecycle companion at `docs/contributing/feature-wave-lifecycle-overview.md`
- the public prompt surface under `docs/prompts/`
- supporting prompt bodies under `docs/prompts/agents/` when the project keeps them checked in
- wave, journal, persona, handoff, and memory artifact roots in topical homes
- `docs/workflow-config.json`
- root wrappers and supported agent entry files

### Upgrade contract

**`Upgrade Wavefoundry`** (legacy aliases: **`Upgrade wave framework`**, **`Upgrade wave context`**) should refresh an existing wave-context or legacy project-context installation by:

- when dated `wavefoundry-*.zip` files are present at the repository root, adopting the newest pack per `160-upgrade-wavefoundry.prompt.md` **step 0** before reconciling repo-local outputs (unpack, `wf render-surfaces`, then the standard upgrade sequence)
- reading the current local docs, prompts, config, and artifact roots before writing changes
- reconciling still-valid repo-grown adaptations instead of overwriting them blindly
- migrating legacy project-context artifacts into wave-native locations and vocabulary when needed
- refreshing the repo-local lifecycle companion, prompt surface, workflow config, and supporting artifact docs when the shared framework contract changes
- preserving repo-local operating detail that remains supported by evidence in the repository and the current framework rules

### Overwrite vs preserve rules

- Overwrite or regenerate when the shared framework owns the semantic contract and the local file is meant to be refreshable.
- Preserve or merge when the local file expresses repo-specific evidence, reviewer assignments, personas, or justified workflow deviations that remain compatible with the current framework.
- If upgrade cannot safely preserve a local customization, document the conflict in the nearest canonical local doc or upgrade notes rather than silently dropping it.

**Standing decision — the stage-gate headings are a fixed two-section contract.** The `## Stage Gate (repository code)` and `## Implementation guard (product code)` sections in seeded `AGENTS.md` are referenced by literal name across host entry docs and lifecycle prompts, so they are the one named **carve-out** from the preserve/merge rules above: upgrade re-establishes them as two separately named sections (preserving each gate's documented preconditions, never the prose) rather than preserving a consolidated local table. The framework deliberately does **not** add a docs-lint check asserting these heading strings — the carve-out is enforced by the `seed-050` / `seed-160` guidance, not a brittle heading-string validator. Do not introduce such a validator; revisit only if a concrete machine-consumer of the gate ever appears.

## 3. Golden-Path Examples

### Example A: feature planning into wave start

1. A non-trivial change is identified and routed into `Plan feature`.
2. Planning creates or updates one `change-id`, acceptance criteria, and the next delivery slice.
3. The wave is defined only after the change scope and shared assumptions are stable enough to execute together.
4. The seeded project runs the readiness gate, records the required implementer, reviewer, and persona lanes, and blocks start until that evaluation is clean.
5. The seeded project begins implementation using the local prompt surface and local review/verification docs.

### Example B: wave carry-forward

1. The active wave reaches review or reconciliation with some items still incomplete.
2. The project records what shipped, what did not, and why the remainder is not closed yet.
3. The unfinished work is moved into the next planned wave under the same `change-id`.
4. Wave memory, handoff state, journals, and next-wave notes are refreshed so the feature thread continues cleanly.

### Example C: feature finalization

1. All planned wave work is complete, archived, or intentionally deferred.
2. `Finalize feature` reruns the readiness evaluation during final review, then reconciles the final wave state and checks behind-the-scenes maintenance work.
3. Durable lessons are promoted into canonical docs, workflow memory, personas, and journals where appropriate.
4. Temporary execution artifacts are archived or frozen, and the feature closes with a clear final review outcome.

## 4. Prompt-to-Doc Maintenance Rules

Use these anti-drift rules whenever the shared framework changes:

1. If a public prompt changes meaning, routing, required outputs, or lifecycle expectations, update the relevant overview docs and README entries in the same change.
2. If init/upgrade changes generated artifacts or overwrite/preserve behavior, update `002-wave-framework-seeding-overview.md`, this contract, and any repo-local pointer docs that describe generated outputs.
3. If a subsystem prompt changes durable behavior for memory, personas, journals, or review, update the corresponding numbered subsystem overview doc.
4. If a new numbered overview doc is added or renamed, update `README.md`, repo-local framework pointers, and any docs indexes that surface the shared pack.
5. If a change affects generated repo-local lifecycle guidance, update both the shared conceptual source and the documented generation path for `docs/contributing/feature-wave-lifecycle-overview.md`.
6. Run the docs gate after shared framework doc or prompt changes, and treat failing docs verification as a blocker for calling the package coherent.

## 5. Final Review Checklist

Use this checklist when reviewing whether the remaining hardening work is complete:

- Framework map exists and is linked from the package README.
- Completeness contract exists and is linked from the package README.
- Repo-generation contract is explicit about create/refresh/preserve behavior.
- Golden-path examples cover planning, carry-forward, and finalization.
- Prompt-to-doc maintenance rules are explicit and discoverable.
- Repo-local pointer docs can route maintainers from project docs in the repository into the shared package docs.
- Docs verification passes.

## Related Docs

- `.wavefoundry/framework/seeds/008-framework-map.md`
- `.wavefoundry/framework/seeds/002-wave-framework-seeding-overview.md`
- `.wavefoundry/framework/README.md`
