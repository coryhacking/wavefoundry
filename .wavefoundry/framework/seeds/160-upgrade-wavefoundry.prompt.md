# 160 - Upgrade Wavefoundry (Shortcut)

**Primary:** **`Upgrade wave framework`**, **`Install wave framework`** (when this handoff applies). **Backwards-compatible:** **`Upgrade wave context`**, **`Install wave context`** — identical behavior; keep accepting them from operators and older docs.

Use this when you want a single command-style request such as:

- `Upgrade wave framework` (legacy: `Upgrade wave context`)
- `Upgrade wave framework from latest zip` / `Upgrade wave context from latest zip` / `Upgrade the wave framework` (natural-language variants; same flow when a distribution zip is present at the repository root — see step 0)
- `Install wave framework` (legacy: `Install wave context`; migration/install alias when the repository already contains `wave-0` or wave-context artifacts)

Intent:

- Upgrade the project's installed Wave Framework layer to the standard represented by the `.wavefoundry/framework` pack currently available in the workspace for that repository.
- Preserve useful repo-grown behavior while reconciling it with the current local seed pack, whether that seed pack is already committed or still being developed locally.
- Revalidate `AGENTS.md`, `docs/workflow-config.json` (including `lifecycle_id_policy` when present), and the public prompt surface against **current** repository evidence — not only prior init output.
- Refresh repositories after init has already classified legacy material and, when needed, captured it in the reserved legacy baseline wave before the first installed wave (`wave-0`).

Terminology — do not confuse **upgrade** with **packaging**:

- **Upgrade wave framework** (operator phrases such as *Upgrade wave framework*, *Upgrade wave context*, *upgrade the wave framework*, *upgrade from the latest zip*): adopt and reconcile **this** repository. When step 0 applies, it unpacks the **lexicographically greatest** `wavefoundry-YYYY-*.zip` already present at the **repository root**, runs `render_platform_surfaces.py`, then continues with drift detection, backfill, and verification in this prompt. This path **does not build** a new zip and **does not** run **Package Wavefoundry**.
- **Package Wavefoundry** (maintainer / distribution): **creates** a new versioned zip and stamps `VERSION` / manifest `framework_revision` in the tree used for the build. Use only when the operator explicitly asked to **package** or **cut a distribution**. Never substitute packaging for **Upgrade wave framework** when the operator asked to **upgrade** from zips already on disk (legacy phrasing: **Upgrade wave context**).

Execution flow:

0. **Adopting a distribution zip (automatic when present):** When one or more date-shaped `wavefoundry-YYYY-MM-DDx.zip` files exist at the **repository root** (not in a subdirectory), **Upgrade wave framework** must apply the newest pack **before** step 1 — the operator does not need a separate unzip step. Other archive names and zips outside the root **do not** trigger this step — unpack those manually if used. When **no** matching zip exists at the root, skip this entire step with no error and continue at step 1.
   - **Select zip:** from the repository root, compute the selected path with `ls -1 wavefoundry-[0-9][0-9][0-9][0-9]-*.zip 2>/dev/null | sort | tail -1` (POSIX shell; on Windows use Git Bash, WSL, or an equivalent that preserves the same lexical ordering before `unzip`). If that command prints nothing, skip to step 1.
   - **Save old MANIFEST before unpack** (if present) so the prune step can diff old vs new:
     ```bash
     cp .wavefoundry/framework/MANIFEST /tmp/wf-manifest-old.txt 2>/dev/null || true
     ```
   - **Unpack:** `unzip -o <selected-zip> -d .` (repository root as the current working directory) so archive entries land under `.wavefoundry/framework/` per the packaging layout.
   - **Regenerate hooks immediately** after a successful unpack so tracked launcher surfaces match the new pack: `python3 .wavefoundry/framework/scripts/render_platform_surfaces.py`.
   - **Prune pack-removed files** so orphans from prior packs do not shadow or duplicate current-pack code. `unzip -o` overlays files but never removes paths that vanished from the pack. Run `prune_framework.py` — it automatically handles both cases:
     - **If `/tmp/wf-manifest-old.txt` exists** (upgraded from a MANIFEST-aware pack): diffs old vs new and deletes only pack-delivered files that were removed. User-created files are never touched.
     - **If `/tmp/wf-manifest-old.txt` does not exist** (upgrading from a pre-MANIFEST pack, i.e. any pack before `2026-05-02e`): automatically applies the built-in legacy removal list covering all files dropped across packs `2026-04-29a` through `2026-05-02d`.
     ```bash
     python3 .wavefoundry/framework/scripts/prune_framework.py --old-manifest /tmp/wf-manifest-old.txt
     ```
   - **Reconcile journals** after prune and hook regeneration. For each journal file under `docs/agents/journals/`:
     - (a) **Rename known activity-log headings:** rename `Recent Captures` → `Active Signals` if the old heading is present.
     - (b) **Delete all activity-log sections by content, not by name:** identify *any* section — regardless of its heading — whose entries are solely wave-closed records, change-shipped summaries, or test-pass notes. Delete the entire section. The test: would any entry still matter to a new agent inheriting this role with no access to git history? If every entry in a section fails that test, delete the section.
     - (c) **Create `## Distillation` if absent:** if the journal has no Distillation section, create one. Review the Incidents section and any remaining journal entries for lessons that have not yet been extracted as concise bullets. Promote qualifying lessons into the new Distillation section. Do not invent lessons — extract only from existing entries.
     - (d) **Clean up dangling references:** after deleting any sections, scan all remaining sections for references to the deleted section names (e.g. a `## Retirement And Supersession` entry that says "older ## Recent Entries remain…"). Remove or replace those references.
     - (e) **Verify section order:** Operating Identity and Distillation must appear before Active Signals.
     - Do not delete standing directives, operator constraints, active watchpoints, distillation bullets, or genuine durable lessons — only activity-log entries and their containing sections.
   - **Continue automatically in the same run:** step 0 only adopts the pack. After unpack + hook regeneration + prune + journal reconciliation, immediately continue with step 1 and complete the full upgrade workflow (`020`, `150`, drift detection, backfill, verification). Do **not** stop after unpacking or treat unzip success alone as a completed upgrade.
   - **Operator caution:** multiple date-shaped `wavefoundry-YYYY-MM-DDx.zip` files at the root always resolve to the lexicographically greatest filename; archive or delete zips that must not be applied so they are not selected by mistake.
   - Do not delete the zip file unless the operator explicitly asks; root pack drops should stay gitignored per `seed-050` when those rules are present.
1. Read `seed-020`.
2. Before detecting drift or editing any files, use a **read-only Explore subagent** to map the current actual state of the repository's installed Wave Framework surface: which prompt docs exist, which topical artifact roots exist, which workflow config keys are present, and which wrappers are in place. The exploration lane must not edit files. Use this map as the baseline for drift detection in step 6 — do not rely on assumptions about what a prior init or upgrade produced. This step prevents confusion between stale template expectations and actual installed state.
3. **Version guard:** Read `.wavefoundry/framework/VERSION` (the pack version) and `docs/prompts/prompt-surface-manifest.json` field `framework_revision` (the installed revision). Compare them using date-prefix ordering (strip any suffix letter before comparing dates; treat `2026-04-10b` as `2026-04-10` for date comparison, with suffix `b` meaning a later revision on the same date than the bare date). If the pack version is **older** than the installed revision, stop and present a clear warning to the operator: state both versions and require explicit confirmation before continuing — do not proceed silently with a downgrade. If the pack version equals the installed revision, note this and continue (running for drift/alignment only). If the pack version is newer, proceed normally.
4. Use `seed-150` for targeted or full refresh. When invoked as `Upgrade wave framework` (rather than a targeted reindex), default to **`full` scope** in `150` so the holistic project state evaluation in task 2 runs — this ensures the upgrade reflects how the project actually exists today, not just framework-level drift. Explicitly run `150` task 2 across all dimensions: source module structure, dependency graph, build/test procedure currency, security surface, quality posture, reliability, spec currency, missing-docs gaps, contribution workflow, thin pointers, repo profile archetype, and license compliance. Explicitly run `150` task 12 so that spec gaps and divergence found in task 2 are acted on — not just noted — before the upgrade closes.
5. If the repository still uses the legacy framework or has stale post-init migration drift, apply `seed-220` without redefining baseline-wave semantics.
6. Validate the installed repo-local Wave Framework surface and detect drift across:
   - public prompt docs (including `implement-feature`, `implement-wave`, `plan-feature`, and `index` vs current `seed-100` guard requirements)
   - topical artifact roots and refreshable docs with regeneration paths
   - workflow config schema
   - agent entry files and native wrappers (including **Git commits (operator-owned)** and **Implementation guard** presence and thin-pointer alignment vs `seed-050`)
   - persona docs and journals, including operating identity, salience triggers, governance, taxonomy/routing, immediate-capture rules, retrieval metadata, and retirement/supersession guidance
   - factor-review policy and factor-review history
   - wrapper paths and tracking expectations
   - stale legacy prompt or framework references
   - source module structure vs `docs/repo-index.md` (new modules, removed modules, new entry points, new public API surfaces)
   - dependency graph changes that affect security surface, architecture docs, or factor applicability
   - build and test procedure currency vs `docs/contributing/build-and-verification.md`
   - security surface vs `docs/SECURITY.md` and `docs/architecture/threat-model.md`
   - quality posture vs `docs/QUALITY_SCORE.md` and actual linting/analysis config
   - reliability and performance vs `docs/RELIABILITY.md` and `docs/architecture/performance-budget.md`
   - spec and behavior contract currency vs `docs/specs/*.md`
   - missing-docs list currency vs actual code coverage
   - contribution workflow and governance vs `.github/` config and `CODEOWNERS`
   - thin pointer and platform surface completeness across all entry files
   - repo profile archetype and project identity drift in `docs/repo-profile.json`
   - operating-memory drift: closure-only journal wording, missing salience triggers, missing memory governance, stale role/persona memory responsibilities, or local prompts that still imply journals are written only at close
   - license and compliance implications of new dependencies
7. Before editing broad framework-maintenance surfaces (the shared pack, repo-local prompt docs, `AGENTS.md`, hook configuration, or prompt-surface manifests), stop and present a concise patch plan naming the intended file edits, protected surfaces, delegated read-only vs write-owning lanes, and verification gates. Do not start broad edits until the operator confirms that plan.
8. Regenerate or normalize:
   - `AGENTS.md` and thin pointers so **Git commits (operator-owned)** matches `seed-050` (agents do not run `git commit` unless the operator explicitly instructs in the **current** request); backfill when missing or when `050` changed in the seed pack
   - `AGENTS.md` and thin pointers so **Implementation guard (product code)** matches `seed-050` when the repo ships product code; backfill when inventory or repo-profile indicates implementation directories but the section is missing
   - tracked platform hook/config surfaces via `python3 .wavefoundry/framework/scripts/render_platform_surfaces.py` so generated hook entrypoints stay aligned with the current framework contract
   - repo-local prompt docs
   - `docs/prompts/agents/` prompt bodies when the repository keeps checked-in project-context/planning helper prompts
   - workflow config schema
   - `docs/references/project-overview.md` when missing or stale
   - `docs/contributing/feature-wave-lifecycle-overview.md` when missing or stale so it stays aligned with `.wavefoundry/framework/seeds/001-feature-wave-framework-overview.md` plus local reviewer/persona policy
   - `docs/prompts/prompt-surface-manifest.json`
   - `docs/agents/session-handoff.md` when missing
   - waves root and journals root
   - durable or refreshable seeded docs that were placed in `docs/generated/` instead of their topical home under `docs/`
   - persona docs and journals when evidence requires them
   - role/persona operating identity and salience-trigger sections when the current framework standard requires them and they are missing or stale
   - journal contracts so they include operating-memory purpose, checked-in memory governance, memory taxonomy/routing, hot-path thresholding, progressive capture fields, operational salience cues, retrieval semantics, and retirement/supersession handling
   - `factor_review_policy`, including which factors are applicable, whether findings are gating or advisory, and subagent-vs-review-lane behavior
   - `persona_review_policy`, including when user/operator personas are invoked and whether their findings are advisory or gating
   - readiness-review behavior, including whether readiness is required before implementation, auto-runs when missing, and reruns before closure
   - **`lifecycle_id_policy`** in `docs/workflow-config.json` — when missing, backfill with the framework default epoch (`2020-02-02T02:02:00Z`) and `hour_offset` `0` (plus optional metadata fields aligned with current seed standard) so greenfield and legacy installs match `lifecycle_id.py` documentation; **never overwrite** an existing `epoch_utc` or `hour_offset` once set, so issued IDs stay valid
   - `indexing.project_include_prefixes` when the repo intentionally extends the default project semantic index to additional roots; preserve explicit repo-local prefixes and backfill the generic structure when the repo already depends on non-default indexed paths
   - canonical workflow docs and role docs when the current framework standard requires them and they are missing or stale
   - `docs/ARCHITECTURE.md` and `docs/architecture/{current-state,domain-map,layering-rules,cross-cutting-concerns,data-and-control-flow,testing-architecture}.md` (and `docs/architecture/decisions/template.md` when ADR seeding changed) when `seed-060`, `seed-030`, or repository topology changed; merge with repo-specific depth per `060` guardrails
   - `docs/prompts/close-wave.md`, `docs/prompts/agents/close-wave.md`, and `docs/contributing/review-and-evals.md` (**Wave closure** / docs-contract-at-close) when the seed pack’s `seed-190` or `seed-100` closure expectations have evolved
   - `docs/prompts/upgrade-wavefoundry.md` and `docs/prompts/agents/upgrade-wavefoundry.md` when the seed pack's upgrade contract changes
   - **`.wavefoundry/bin/docs-lint`**, **`.wavefoundry/bin/docs-gardener`**, and any legacy **`./package-wave-framework`** repo-root wrapper so they point to the **current** script filenames under `.wavefoundry/framework/scripts/` or are retired when packaging is not supported in a target repository. These **bin** launchers (and any repo-root packaging helper) are **not** overwritten blindly by pack unpack, so reconcile them explicitly during upgrade. Required invocations for packs at `2026-04-22a` and later in this repository:
     - `.wavefoundry/bin/docs-lint` must invoke `scripts/docs_lint.py` (underscore) — the retired `scripts/docs-lint.py` path must not be referenced
     - `.wavefoundry/bin/docs-gardener` must invoke `scripts/docs_gardener.py` (underscore) — the retired `scripts/docs-gardener.py` path must not be referenced
     - `./package-wave-framework`, when intentionally retained in a source repository, must invoke `scripts/build_pack.py` — the retired `scripts/build_zip.py` path must not be referenced

     Launcher filenames under **`.wavefoundry/bin/`** remain hyphenated for conventional CLI ergonomics; only the Python module filenames moved to snake_case.
   - `docs/contributing/build-and-verification.md` — ensure a **Git commits** subsection (operator-owned policy, aligned with `050` and **Git commits** in `AGENTS.md`) exists whenever that file is refreshed; backfill when missing or when `050` changed. Ensure a **Wave framework pack upgrade verification** section exists and matches `seed-040` task 17 (ordered checklist: root zip or manual tree update → **Upgrade wave framework** → docs gate (**agents with MCP:** **`wave_garden`** then **`wave_validate`**; **operators / CI / no MCP:** **`.wavefoundry/bin/docs-gardener && .wavefoundry/bin/docs-lint`**) → diff/commit; cross-links to `docs/prompts/upgrade-wavefoundry.md` and `docs/prompts/package-wavefoundry.md` when applicable; step-0 exclusions and product-build N/A note). Note that the framework test suite (`scripts/tests/`, `scripts/run_tests.py`) is a development-only artifact **not included in the distribution pack** — downstream repos must not reference it in upgrade verification steps. Backfill when the repo vendors the pack but the section is missing or stale.
   - `docs/design-system/design-language.md` — backfill when `docs/repo-profile.json` `design_system.design_evidence.detected` is `true` but `docs/design-system/design-language.md` does not exist; use the canonical structure defined in `seed-040` task 13 and re-run `030` design surface scan to gather current evidence before seeding. When `design-language.md` exists but `design_system` in the profile has changed since last verified (check `Last verified:` date in the file vs profile `design_sensitivity` or `ui_roots` changes), flag as stale and prompt the operator to refresh the file before closing the upgrade.
   - **`docs/design-system/` extraction contract backfill (merge-safe upgrade)** — when `docs/design-system/` exists in the target repository, run the extraction contract backfill defined in `seed-040` task 14 and `seed-010` step 8. This backfill is **merge-safe**: never delete or overwrite existing files. Steps:
     1. For each required path in the core tree (see `seed-040` task 14 or `seed-010` step 8 checklist), create the path if it does not yet exist using the stub content defined in those seeds. Never overwrite any existing file.
     2. **Schema-version reconciliation** — read the existing `docs/design-system/manifest.json`. Compare its `schemaVersion` field against the current framework's expected schema version (`"1.0.0"`). Use semver ordering: a manifest `schemaVersion` is stale when it is lexicographically earlier using semver rules (e.g. `"0.9.0"` < `"1.0.0"`). When the manifest's schema version is stale or when required top-level fields are absent, **add** the missing fields with their null/empty defaults (never remove or overwrite existing field values), then append a `meta`-category entry to `docs/design-system/gaps.md`:

        ```
        ### [meta] Schema fields added by upgrade: <comma-separated list>
        **Severity:** nice-to-have
        **Recommended action:** Review added fields and populate as needed.
        ```

        If `manifest.json` does not exist (new install path), it was already created in step 1 with the full stub — no schema reconciliation needed.
     3. **Coexistence rule** — extraction must never rewrite `docs/design-system/design-language.md` or `docs/design-system/index.md` body content. Extraction may only: (a) append a cross-link row to `index.md` listing new extraction artifacts with status `generated`, when that row does not already exist; (b) add a "See extracted contract" pointer at the top of `design-language.md` when that pointer does not already exist. Both operations are idempotent.
     4. **Rollback path** (document in gap log, not automatic) — if the operator needs a clean re-extraction: (a) move the existing `docs/design-system/<subtree>` to a timestamped backup at `docs/design-system/.backup/<ISO-date>/`; (b) regenerate using the seed contract; (c) diff against the backup for review. Record a `meta`-category `gaps.md` entry when a backup is created. Never auto-delete operator artifacts without the backup step.
   - `.gitignore` scoping when broad ignore rules would hide framework-managed files
9. Retire or rewrite stale local prompt/docs references that still point at legacy framework names or obsolete helper surfaces after replacement artifacts are in place. **Delete fully-superseded prompt files** rather than leaving tombstone files with "RETIRED" notices — a tombstone that is no longer needed as a migration alias only adds noise and confusion. A prompt file should be deleted when: (a) a replacement file exists at the canonical path, (b) no live references to the old file remain in AGENTS.md, docs/prompts/index.md, or prompt-surface-manifest.json, and (c) the migration window is over. Remove the corresponding entry from `docs/prompts/index.md` legacy aliases section when deleting tombstones. Also remove any empty legacy workspace directories (`docs/exec-plans/`, `docs/product-specs/`, `docs/gaps/`, `docs/performance/`, `docs/generated/`) that may have been left as shells by the init or a prior upgrade run.
10. Re-run the docs gate (**MCP:** **`wave_garden`** then **`wave_validate`** when attached; **CLI:** **`.wavefoundry/bin/docs-gardener && .wavefoundry/bin/docs-lint`**).

11. **Operating-memory upgrade reconciliation:** When `seed-006`, `seed-050`, `seed-120`, `seed-130`, `seed-140`, `seed-160`, `seed-170`, `seed-180`, `seed-190`, `seed-200`, or `seed-210` changed the journal/role/persona memory contract, upgrade existing projects using this checklist:
   - Preserve operator standing directives, active cautions, security/release-sensitive notes, and evidence refs unless explicitly superseded with evidence.
   - Do not bulk-rewrite historical journal entries. Keep historical sections readable, add current operating-memory sections around them, and migrate only entries needed for current retrieval, promotion, or retirement.
   - Add or reconcile `Operating Identity`, `Salience Triggers`, and memory responsibilities in generated/local role and persona docs.
   - Reconcile `docs/agents/journals/README.md` and existing journal files to the current operating-memory contract: governance, taxonomy/routing, hot-path thresholds, progressive immediate capture, operational salience, retrieval semantics, validity windows, supersession, and retirement.
   - Replace closure-only phrasing with lifecycle-wide capture language: critical/high operating-memory signals may be journaled during planning, implementation, review, handoff, reindex, or closure.
   - Prefer seed-derived wording over local forks, but preserve project-specific constraints and repo-grown policy that remains valid.
   - Update local lifecycle prompts and contributing docs when they still route all journal work to `Close wave` only.
   - Rename `## Follow-up Signals` to `## Active Watchpoints` in all journal files where the old section name is present; preserve all content under the renamed header.
   - Run the docs gate after reconciliation (**MCP:** **`wave_garden`** then **`wave_validate`** when attached; otherwise **`.wavefoundry/bin/docs-gardener && .wavefoundry/bin/docs-lint`**).

Upgrade execution contract:

- Treat **`seed-150`** (and, when applicable, **`seed-220`**) as the authoritative refresh instructions for each artifact class; **`160`** orchestrates sequencing and validation.
- Upgrade is **incomplete** if required repo-local outputs remain missing, if **`docs/prompts/prompt-surface-manifest.json`** and **`docs/workflow-config.json`** `prompt_generation.seed_framework_source` **diverge**, or if the **docs gate fails** after upgrade when `.wavefoundry/framework/scripts/docs_lint.py` is present — i.e. **`wave_validate`** does not report success over MCP (when that is how the run was verified), or **`.wavefoundry/bin/docs-lint` exits non-zero** when verified via CLI.

Operator summary (required handoff):

After upgrade completes successfully, deliver a concise **high-level overview** to the human operator so they know **what was refreshed**, **what stayed stable**, and **what to run next**. Mirror the init handoff structure but emphasize reconciliation rather than first-time bootstrap.

Include the following topics in plain language:

1. **What was refreshed**
   - Prompt surface (`docs/prompts/`, optional `docs/prompts/agents/`), `AGENTS.md` and thin pointers, `docs/workflow-config.json` / `docs/repo-profile.json` when schema or policy standard moved, manifests (`docs/prompts/prompt-surface-manifest.json`), build-and-verification and lifecycle companion docs if regenerated, **`.wavefoundry/bin/docs-lint`** and **`.wavefoundry/bin/docs-gardener`** launchers, native role wrappers when `enabled_agent_roles` or platform generation changed.
   - Explicit callout if **Git commits (operator-owned)**, **Implementation guard**, **close-wave / docs-contract-at-close**, or **framework script hygiene** were backfilled or updated (per `050-` / `100-` / `190-` seed prompts).

2. **What was preserved**
   - Closed legacy baseline wave `docs/waves/00000 wave-zero-plans-and-specs/` (if present), existing journals and persona history, standing directives and active cautions, repo-grown policy in workflow docs unless migration replaced stale text, durable `docs/specs/*.md` contracts (never relocated as legacy corpus).

3. **High-level workflow** (unchanged unless docs explicitly evolved)
   - Same public phrase ladder as init: **Plan feature** through **Close wave** / **Finalize feature**; pointer to `docs/contributing/change-workflow.md`, `docs/contributing/feature-wave-lifecycle-overview.md`, and `AGENTS.md` stage gate / implementation guard.

4. **Commands and trigger phrases**
   - **`Upgrade wave framework`** vs **`Install wave framework`** (legacy: **`Install wave context`**; alias after detection); **`Init wave framework`** (legacy: **`Init wave context`**) for first-time or legacy baseline capture only when appropriate.
   - Lifecycle IDs remain `python3 .wavefoundry/framework/scripts/lifecycle_id.py`.

5. **Agents and personas**
   - Note any added/retired generic role wrappers or factor-review agents tied to `docs/repo-profile.json` `factor_review` changes; persona policy changes from `persona_review_policy`; operating-identity or salience-trigger updates applied to roles/personas.

6. **Documentation setup and verification**
   - Reiterate canonical entry: `docs/README.md`, `docs/prompts/index.md`, `docs/references/project-overview.md`.
   - Confirm post-upgrade docs gate ran or must run per `docs/contributing/build-and-verification.md`: **agents with MCP** — **`wave_garden`** then **`wave_validate`**; **operators / CI / no MCP** — **`.wavefoundry/bin/docs-gardener`** and **`.wavefoundry/bin/docs-lint`** (pass `--date <YYYY-MM-DD>` only when overriding today's date).

7. **Important configuration and precondition**
   - When step 0 ran, call out which zip was unpacked and that hooks were regenerated immediately afterward.
   - When step 0 did not run, upgrade applies the pack **already** in `.wavefoundry/framework/` on disk before this command started.
   - **Upgrade wave framework** does not download a newer framework. To adopt a newer pack without a root zip, replace or patch `.wavefoundry/framework/` first, then run **Upgrade wave framework** again (or drop a dated `wavefoundry-YYYY-MM-DDx.zip` at the repository root and run **Upgrade wave framework** so step 0 unpacks it automatically).
   - `docs/workflow-config.json` and `docs/repo-profile.json` remain the primary configuration surfaces for wave execution, reviews, factors, and personas.

8. **Operators new to wave-context (or re-onboarding after upgrade)**
   - Point them at **`AGENTS.md` → Start Here** and **`docs/prompts/index.md` Usage Notes** for the authoritative rules: **Git commits (operator-owned)** (agents do not `git commit` unless explicitly instructed in the **current** request), **stage gate** (plan + admit + **Prepare wave** / **Ready wave** before **repository code** edits), **Implementation guard** for product implementation source (and **in-session waiver** recording), **Implement wave** vs **Implement feature**, **docs-contract review** at **Close wave** / **Finalize feature** when specs changed, and **`docs/prompts/agent-routing-concurrency.md`** when plans need explicit concurrency.
   - If this upgrade changed closure or guard semantics, call that out explicitly so returning operators re-read **`docs/prompts/close-wave.md`** and **`AGENTS.md`** for the current bar.

Tailor the summary to **this run's** drift summary and concrete files touched.

Required upgrade behaviors:

- preserve journals
- preserve standing directives, active cautions, and historical journal evidence unless explicitly superseded
- preserve persona history when still supported by evidence from the repository
- preserve factor-review history, prior factor-review findings, and factor-review relevance when they remain supported by evidence from the repository
- preserve prompt-surface customizations derived from durable local behavior
- preserve a closed reserved legacy baseline wave when it already exists and keep it distinct from normal delivery waves
- preserve the repo-local split between public prompt docs and agent-oriented prompt bodies when that split is already installed
- migrate any remaining legacy init/upgrade docs and references to **`Init wave framework` / `Upgrade wave framework`** (keep **`Init wave context` / `Upgrade wave context`** as accepted aliases)
- migrate any active `docs/specs/changes/<id>/` packages to the consolidated change document model: fold `proposal.md`, `spec.md`, and `tasks.md` into the corresponding `docs/plans/<change-id>.md` as `## Rationale`, `## Requirements`, and `## Tasks` sections, then archive the redundant spec folder
- do not move durable `docs/specs/*.md` behavior contracts — they are canonical reference docs and stay in place regardless of lifecycle workspace changes
- invoke `230-author-spec` for each spec-worthy component flagged by task 2 or step 6 as lacking a spec or having a diverged spec; do not leave spec gaps unresolved and do not merely report them as recommendations when the source code is available to derive the contract from
- update `docs/plans/plan-template.md` to the consolidated format when it still uses the old `## Spec Refs` shape
- treat **`Upgrade wave framework`** (legacy: **`Upgrade wave context`**) as the canonical refresh command for already-installed wave context in the repository after `wave-0`, while allowing init-phase detection or **`Install wave framework`** (legacy: **`Install wave context`**) convenience routing to hand work here when refresh semantics are required
- prefer additive migration and explicit retirement over destructive replacement when interrupted upgrades would otherwise strand the repository in a mixed state
- move or regenerate seeded docs into their topical `docs/` homes when earlier installs placed them under `docs/generated/`
- do not leave checked-in framework artifacts in `docs/generated/`; keep topical locations explicit for manifests, handoffs, waves, journals, and memory docs
- generate or retain factor-review agent files only for factors marked `applicable` in `docs/repo-profile.json`; re-evaluate skipped factors when project scope changes materially; do not invent factor-review agents without evidence
- backfill missing repo-local outputs required by the current framework standard rather than only reporting drift
- backfill **`lifecycle_id_policy`** when absent and the repo vendors `lifecycle_id.py`, without changing existing epoch/offset values when already present
- when seed lifecycle docs (`001`, `170`, `180`, `190`, `200`, `100`, `110`) changed, reconcile repo-local prompts and lifecycle companions so **prepare-time relocation** stays consistent with the **docs gate** (`wave_validate` / `wave_garden` over MCP, or `.wavefoundry/bin/docs-lint` rules) and `seed-100` (coordinate with `seed-150` task 5)
- ensure lifecycle ID generation is co-located with framework scripts by keeping `.wavefoundry/framework/scripts/lifecycle_id.py` as the canonical entrypoint and updating stale legacy path references
- reconcile **Git commits (operator-owned)** in `AGENTS.md` and the **Git commits** subsection in `docs/contributing/build-and-verification.md` on every upgrade when `seed-050` changed, or when either surface predates the policy; treat upgrade as the peer of init for this contract, not an optional follow-up
- reconcile **Implementation guard (product code)** on every upgrade when `seed-050` or `seed-100` changed, or when `AGENTS.md` / implement prompts predate the guard; treat upgrade as the peer of init for this policy, not an optional follow-up
- reconcile closure-process surfaces on upgrade whenever seed closure contract changed: `docs/prompts/close-wave.md`, `docs/prompts/agents/close-wave.md`, and `docs/contributing/review-and-evals.md` must explicitly enforce chronology reconciliation (`Status`, `Current state`, change states, `Completed at`), required-reviewer reconciliation from readiness to review checkpoints, closure-artifact reconciliation (journals/memory/handoff), and docs-contract disposition rules
- preserve and reconcile reviewer-journal expectations during upgrade: important implementation/review lessons should be journaled when role journals exist; when role journals are absent, closure guidance should route lessons to canonical existing journals without making missing role-journal files a hard closure blocker
- reconcile operating-memory expectations during upgrade: journals may be written before closure for critical/high durable signals; closure distills, promotes, retires, and reconciles rather than serving as the only write point
- generate or refresh the repo-local project overview when needed so it still explains the canonical docs, workflow, generic roles, synthesized personas, and collaboration model for the current project
- generate or refresh the repo-local feature/wave lifecycle companion when needed so it reflects the shared lifecycle model plus the project's actual reviewer roles, personas, and artifact paths
- refresh manifests and any artifact-purpose docs when refreshable artifacts change
- after any subagent completes work during an upgrade pass, re-read each file the subagent reported modifying and confirm its content matches the intended change; do not accept a subagent's self-report as sufficient — silently reverted edits are a known failure mode
- keep inventory and drift-detection subagents read-only unless a later step explicitly assigns them owned write paths; any write-capable subagent must have explicit owned paths and forbidden paths before it starts
- before creating a new canonical doc, verify no existing file already covers the same content area; when an existing file covers the same scope, edit that file rather than creating a parallel one — new files are appropriate only when no canonical home exists
- during cleanup, remove only live working docs and deprecated prompt/wrapper files that have valid replacements; do not delete historical references from changelogs, closed-wave records, release notes, or archived docs — retiring a file removes the file, not the historical record of it
- when cleaning up legacy content, scope removal to only the explicitly named deprecated artifacts; do not expand to adjacent historical records, prior wave archives, or references in closed-wave docs without explicit instruction
- stop and report conflicts when a legacy artifact mixes durable guidance with obsolete wrapper behavior and the correct migration target is unclear

Validation areas that should be checked explicitly:

- required repo-local prompt docs exist and expose the intended public surface
- supporting repo-local prompt bodies exist in `docs/prompts/agents/` when the installed surface uses checked-in agent-oriented prompt bodies
- required canonical docs and topical artifact roots exist
- `docs/references/project-overview.md` exists and explains the project workflow plus role/persona collaboration model
- workflow config contains wave, memory, persona, prompt-generation, factor-review, and persona-review sections (`factor_review_policy` and `persona_review_policy` as separate keys)
- workflow config includes **`lifecycle_id_policy`** when the project vendors `lifecycle_id.py` in the repository, either present already or backfilled without mutating an existing epoch/offset
- workflow config `review_policies` includes `require_qa_reviewer_for_bug_fixes` when the project follows `docs/contributing/agent-team-workflow.md` bug-fix QA rules
- workflow config wave-execution section contains readiness-review expectations when non-trivial wave execution is enabled
- wrappers point at the wave framework scripts rather than legacy script paths
- agent entry files are semantically aligned and still thin
- factor-review policy is still justified by evidence from the repository
- stale legacy helper references are either migrated or reported
- refreshable artifacts exist in their expected topical homes
- `AGENTS.md` contains **Framework Script Hygiene** per `seed-050`; backfill from the canonical rule when missing
- `AGENTS.md` contains **Git commits (operator-owned)** per `seed-050`; `docs/contributing/build-and-verification.md` contains a **Git commits** section aligned with that policy when the file exists
- `AGENTS.md` contains **Implementation guard (product code)** when `docs/repo-profile.json` / `docs/repo-index.md` indicates shipped product code, per `seed-050`; backfill the section and thin-pointer startup lines when missing but the project is not documentation-only
- `python3 .wavefoundry/framework/scripts/render_platform_surfaces.py` is the preferred regeneration path for tracked platform hooks/configs; do not hand-maintain hook logic independently when the renderer can own it
- Hook regeneration may manage Copilot agent files under `.github/hooks/`, but it must not create or modify GitHub Actions workflows under `.github/workflows/` and must not touch local git hooks under `.git/hooks/`
- `.claude/settings.json` contains the tracked launcher wiring rendered for the current host platform: `PreToolUse` Edit|Write -> `.claude/hooks/pre-edit` (or `cmd.exe /c .claude\\hooks\\pre-edit.cmd` on Windows), `PostToolUse` Bash -> `.claude/hooks/pycache-cleanup` (or Windows launcher), and `PostToolUse` Edit|Write -> `.claude/hooks/post-edit` (or Windows launcher); add or merge if partial
- `.claude/hooks/pre-edit.py`, `.claude/hooks/post-edit.py`, `.claude/hooks/pycache-cleanup.py`, and `.claude/hooks/simulate-hooks.py` exist alongside their generated POSIX and Windows launchers; add if missing per `seed-050`
- `.claude/skills/upgrade-wave.md` exists with the verified upgrade gate sequence, including the repo-global `.wavefoundry/guard-overrides.json` approval flow for `framework_edit_allowed` and `seed_edit_allowed`; seed from `seed-050` if missing
- when the repository uses Cursor: `.cursor/hooks.json`, `.cursor/hooks/after-file-edit.py`, `.cursor/hooks/seed-warn.py`, `.cursor/hooks/framework-plan-warn.py`, and `.cursor/hooks/docs-lint.py` exist alongside their generated POSIX and Windows launchers, and `.cursor/hooks.json` points at the launcher form rendered for the current host platform; add if missing per `seed-050` Cursor Hook Contract
- when the repository uses Windsurf: `.windsurf/hooks.json` and `.windsurf/hooks/seed-protect.py` and `.windsurf/hooks/docs-lint.py` exist alongside their generated POSIX and Windows launchers, and `.windsurf/hooks.json` points at the launcher form rendered for the current host platform; add if missing per `seed-050` Windsurf Hook Contract
- when the repository uses GitHub Copilot coding agent: `.github/hooks/hooks.json`, `.github/hooks/pre-tool-use.py`, and `.github/hooks/post-tool-use.py` exist alongside their generated POSIX and Windows launchers, and the config points at the launcher form rendered for the current host platform; add if missing per `seed-050` GitHub Copilot Hook Contract
- `docs/agents/platform-mapping.md` reflects which supported platforms receive executable hooks (`claude`, `cursor`, `copilot`) and which stay prompt-driven (`codex`, `air`, `junie`, `warp`)
- `docs/prompts/index.md` contains an **Operating Rules** section (or equivalent) that references `.wavefoundry/framework/seeds/020-run-contract.prompt.md` as the authoritative run contract and carries the key behavioral rules inline; backfill when missing per `seed-100`
- canonical role docs (`docs/agents/implementer.md`, `docs/agents/planner.md`, `docs/agents/wave-coordinator.md`) each contain an **Execution contract** section with the role-relevant subset of rules from `seed-020`; backfill when missing per `seed-050` **Execution Contract in Canonical Role Docs**
- `docs/contributing/agent-team-workflow.md` contains an **Execution contract** section with all six rules from `seed-020` and a reference to it; backfill when missing per `seed-150` task 5
- `docs/prompts/index.md`, `docs/prompts/prompt-surface-manifest.json`, and `AGENTS.md` shortcut tables remain **triplet-consistent** (no orphan public prompts, no duplicate shortcuts)
- `docs/workflow-config.json` retains top-level **`wave_execution`**, **`agent_memory`**, **`project_persona_generation`**, **`prompt_generation`**, **`factor_review_policy`**, and **`persona_review_policy`** sections expected by the docs gate
- `docs/references/roles.md` exists and stays aligned with metadata conventions when present in **Start Here**
- architecture hub and child docs under `docs/architecture/` reflect current `docs/repo-index.md` module roots and integration edges, or document explicit gaps
- `docs/repo-index.md` reflects the current source module structure — no missing modules, no stale module descriptions for code that no longer exists
- `docs/contributing/build-and-verification.md` reflects current build commands, test commands, required tool versions, and pre-commit hooks — and, when the repository vendors `.wavefoundry/framework/`, includes current **Wave framework pack upgrade verification** aligned with `040` task 16 and **Upgrade wave framework** / step 0 semantics
- `docs/agents/journals/README.md`, role docs, persona docs, and local lifecycle prompts reflect the current operating-memory contract; no live surface still implies journal capture is close-wave-only
- `docs/SECURITY.md` and `docs/architecture/threat-model.md` reflect the current security surface — no undocumented endpoints, auth mechanisms, PII flows, or trust boundaries
- `docs/QUALITY_SCORE.md` reflects current enforced quality gates (linting rules, coverage thresholds, static analysis tools)
- `docs/RELIABILITY.md` and `docs/architecture/performance-budget.md` reflect current SLOs, runbooks, and capacity expectations
- `docs/specs/*.md` behavior contracts are still consistent with current implementation; divergence and missing specs for spec-worthy components are acted on via `230-author-spec` (not only noted)
- `docs/missing-docs.md` (or `docs/gaps/missing-docs.md`) is current — new undocumented code areas are listed, resolved items are removed
- thin pointers (`CLAUDE.md`, `.cursor/rules/project-context.mdc`, `.junie/guidelines.md`, `.github/copilot-instructions.md`, `WARP.md`) route accurately to current `AGENTS.md` content with no stale command references
- `.claude/agents/*.md` native agent files exist for all roles in `enabled_agent_roles` and are absent for roles not in that set; factor-review agents exist only for `applicable` factors in `docs/repo-profile.json`
- `docs/repo-profile.json` archetype and project identity fields accurately describe the current project scope (not the scope at init time)

Guardrails:

- This upgrades the project's Wave Framework layer in the repository to the framework version currently available at `.wavefoundry/framework/` **after** step 0 when step 0 unpacks a root distribution zip, whether or not that version has been committed yet.
- It does not fetch a newer framework release on its own (step 0 only unpacks zips already present at the repository root).
- Step 0 is never a terminal success condition by itself; unpacking without the subsequent reconciliation and verification steps is an incomplete upgrade.
- Upgrade is incomplete if required repo-local outputs are still missing after the run.
