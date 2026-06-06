# 160 - Upgrade Wave Framework (Shortcut)

**Primary:** **`Upgrade wave framework`**. **Handoff alias:** **`Install wave framework`** (when this handoff applies). **Backwards-compatible:** **`Upgrade Wavefoundry`**, **`Upgrade wave context`**, **`Install wave context`** — identical behavior; keep accepting them from operators and older docs.

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

- **Upgrade wave framework** (operator phrases such as *Upgrade wave framework*, *Upgrade wave context*, *upgrade the wave framework*, *upgrade from the latest zip*): adopt and reconcile **this** repository. When step 0 applies, it selects the highest semver `wavefoundry-MAJOR.MINOR.PATCH.<build>.zip` available from the repository root, `~/.wavefoundry/`, or `~/.wavefoundry/dist/`, runs `render_platform_surfaces.py`, then continues with drift detection, backfill, and verification in this prompt. This path **does not build** a new zip and **does not** run **Package Wavefoundry**.
- **Package Wavefoundry** (maintainer / distribution): **creates** a new versioned zip and stamps `VERSION` / manifest `framework_revision` in the tree used for the build, then updates and compacts the packaged `framework/index/`. Use only when the operator explicitly asked to **package** or **cut a distribution**. Never substitute packaging for **Upgrade wave framework** when the operator asked to **upgrade** from zips already on disk (legacy phrasing: **Upgrade wave context**).

Operator mental model — how framework updates actually work:

1. **Bring the new framework to this repository.**
 - Usually by placing a `wavefoundry-*.zip` pack at the repository root, `~/.wavefoundry/`, or `~/.wavefoundry/dist/`.
 - Or by already having the newer `.wavefoundry/framework/` tree staged locally in the repo.
2. **Run Upgrade wave framework once.**
 - If a root pack zip is present, step 0 adopts it automatically.
 - The rest of this prompt then reconciles prompts, hooks, docs, configs, and local policy surfaces.
3. **Restart MCP after the upgrade completes.**
 - A running MCP process will not automatically pick up upgraded server code or regenerated host config.
4. **Update indexes after restart** (`wave_upgrade(phase="update_index")`).
 - Normal upgrades: incremental update — only re-embeds files that changed. The indexer auto-escalates to a full rebuild when chunker or model versions changed.
 - `CHUNKER_VERSION` or schema shifts: a full rebuild is required — see step 10 for the manual path.

Do not describe upgrade as a manual unzip-only workflow. Do not describe packaging as part of the target-repo upgrade path. Do not imply that unpack success alone completes the framework update.

Execution flow:

0. **Adopting a distribution zip (automatic when present):** When one or more semver-shaped `wavefoundry-MAJOR.MINOR.PATCH.<build>.zip` files exist at the **repository root**, under `~/.wavefoundry/`, or under `~/.wavefoundry/dist/`, **Upgrade wave framework** must apply the highest semver pack **before** step 1 — the operator does not need a separate unzip step. Non-matching archive names are ignored. On Windows, run this flow from **WSL2** rather than native `cmd.exe` or PowerShell. When no matching zip exists in any of those locations, skip this entire step with no error and continue at step 1.
 - **Select zip:** the upgrade script and the MCP `wave_upgrade` tool both select the highest semver pack across the four search paths (repository root, `~/`, `~/.wavefoundry/`, `~/.wavefoundry/dist/`); compare by `MAJOR.MINOR.PATCH` first, then by the 4-character build suffix when versions tie. **Agents must NOT run `ls -1 ~/.wavefoundry/dist/`** to determine the selected pack — `ls` sorts lexicographically and will rank `1.3.9` above `1.3.30`, leading the agent to apply a stale pack. Instead run **`.wavefoundry/bin/upgrade-wavefoundry --detect-zip`** (prints the absolute path of the selected pack, exit 0 / empty output + exit 1 when none found) or **`--list-zips`** (prints every match across all four paths, semver-sorted, with `* ` on the selected pack). When MCP is attached, `wave_upgrade(mode='dry_run')` surfaces the selected pack on a `Zip to apply:` line in its output and is the preferred path.
 - **Save old MANIFEST before unpack** (if present) so the prune step can diff old vs new:
 ```bash
 cp .wavefoundry/framework/MANIFEST /tmp/wf-manifest-old.txt 2>/dev/null || true
 ```
 - **Unpack:** `unzip -o <selected-zip> -d .` (repository root as the current working directory) so archive entries land under `.wavefoundry/framework/` per the packaging layout.
 - **Regenerate hooks and agent surfaces immediately** after a successful unpack so tracked launcher surfaces match the new pack: `python3 .wavefoundry/framework/scripts/render_platform_surfaces.py` (includes `render_agent_surfaces.py` for auto-Guru tier 2–3 files). See **Agent surfaces and auto-Guru upgrade (agent procedure)** below.
 - **Prune pack-removed files** so orphans from prior packs do not shadow or duplicate current-pack code. `unzip -o` overlays files but never removes paths that vanished from the pack. Run `prune_framework.py` — it diffs the saved old MANIFEST against the newly-extracted MANIFEST and deletes only pack-delivered files that were removed. User-created files are never touched.
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
 - **Operator caution:** when multiple semver packs exist, the highest semver zip is selected automatically; archive or delete packs that must not be applied so they are not selected by mistake.
 - Do not delete the zip file unless the operator explicitly asks; root pack drops should stay gitignored per `seed-050` when those rules are present.

### 1.5.0 upgrade — auto-migration (wave `1p35d` / `1p3ay`)

When the installed revision predates **1.5.0**, `upgrade_extensions.post_extract` runs three migrations automatically at the `post_extract` phase boundary (immediately after zip extraction, before surface rendering). The operator does not invoke them; the upgrade machinery fires them inside the standard `Upgrade wave framework` flow. Each migration is idempotent — re-running the upgrade is safe.

The migrations:

1. **`Role:` backfill on every `docs/agents/*.md`** — wave `1p35d` (`1p35l`) made `docs-lint` enforce `Role:` on every agent role doc. Existing repos may have custom agent docs added since their last install that lack this field; without the backfill, the first post-upgrade docs gate run fails. The migration walks `docs/agents/`, `docs/agents/specialists/`, `docs/agents/personas/` (skipping `README.md`, `session-handoff.md`, `platform-mapping.md`, and anything under `journals/`) and inserts `Role: <filename-slug>` into any file missing the field. The `Role:` is placed immediately after the `Status:` line (or after `Owner:` if `Status:` is absent).
2. **Pycache launcher cleanup** — wave `1p35d` (`1p35n`) retired the `pycache-cleanup` Claude Code hook. The migration deletes `.claude/hooks/pycache-cleanup`, `.claude/hooks/pycache-cleanup.py`, and `.claude/hooks/pycache-cleanup.cmd` if any remain.
3. **`.claude/settings.json` pycache row strip** — the stale `PostToolUse` Bash hook row pointing at `.claude/hooks/pycache-cleanup` (or its `.cmd` Windows variant) persists because `render_platform_surfaces.py` merges settings rather than overwriting. The migration parses settings.json, removes the matching row, and preserves all other hook rows (including any operator-added customs).

**Migration report:** when at least one migration performs work, a consolidated report is written to `.wavefoundry/logs/upgrade-migration-1.5.0.log`. The report names each migration and lists the files modified. When no migration performed work, no report is written.

**Defensive isolation:** an exception in one migration is captured to the report (with the migration name and traceback) and does not abort the other migrations.

**Migration preview (operator-side, `--dry-run`):** before committing to the real upgrade, run `upgrade-wavefoundry --dry-run` (or `wave_upgrade(mode='dry_run')`). When the new pack defines `post_extract`, the dry-run path invokes it with `ctx.dry_run=True`, which calls the migration's preview helpers (`_preview_*`) instead of the action helpers. Zero filesystem mutations are performed. The preview output lands at `.wavefoundry/logs/upgrade-migration-1.5.0.preview.log` — a **distinct filename** from the real-run log so a subsequent real run does NOT shadow the preview. The preview log enumerates exactly which files would be modified, which launchers would be deleted, and which `settings.json` row would be stripped. Operators reviewing the preview can compare side-by-side with the real-run log produced by the actual upgrade. Added in wave `1p3b9` / `1p3b6`.

**Post-upgrade verification (operator):** review `.wavefoundry/logs/upgrade-migration-1.5.0.log` if it exists, confirm each modified file looks correct (`git diff` is the audit tool), and re-run `wave_audit` to confirm lint and dashboard surfaces are clean. The framework's `prepare_council` / `delivery_council` paths exercise the same surfaces; passing through them is the cross-check.

1. Read `seed-020`.
2. Before detecting drift or editing any files, use a **read-only Explore subagent** to map the current actual state of the repository's installed Wave Framework surface: which prompt docs exist, which topical artifact roots exist, which workflow config keys are present, and which wrappers are in place. The exploration lane must not edit files. Use this map as the baseline for drift detection in step 6 — do not rely on assumptions about what a prior init or upgrade produced. This step prevents confusion between stale template expectations and actual installed state.
3. **Version guard:** Read `.wavefoundry/framework/VERSION` (the pack version) and `docs/prompts/prompt-surface-manifest.json` field `framework_revision` (the installed revision). Compare them using semver ordering on `MAJOR.MINOR.PATCH`, ignoring build metadata for precedence. If the pack version is **older** than the installed revision, stop and present a clear warning to the operator: state both versions and require explicit confirmation before continuing — do not proceed silently with a downgrade. If the pack version equals the installed revision, note this and continue (running for drift/alignment only). If the pack version is newer, proceed normally.
4. Use `seed-150` for targeted or full refresh. When invoked as `Upgrade wave framework` (rather than a targeted reindex), default to **`full` scope** in `150` so the holistic project state evaluation in task 2 runs — this ensures the upgrade reflects how the project actually exists today, not just framework-level drift. Explicitly run `150` task 2 across all dimensions: source module structure, dependency graph, build/test procedure currency, security surface, quality posture, reliability, spec currency, missing-docs gaps, contribution workflow, thin pointers, repo profile archetype, and license compliance. Explicitly run `150` task 12 so that spec gaps and divergence found in task 2 are acted on — not just noted — before the upgrade closes.
5. If the repository still uses the legacy framework or has stale post-init migration drift, apply `seed-220` without redefining baseline-wave semantics.
6. Validate the installed repo-local Wave Framework surface and detect drift across:
 - public prompt docs (including `implement-feature`, `implement-wave`, `plan-feature`, and `index` vs current `seed-100` guard requirements)
 - topical artifact roots and refreshable docs with regeneration paths
 - workflow config schema
 - agent entry files and native wrappers (including **Git commits (operator-owned)** and **Implementation guard** presence and thin-pointer alignment vs `seed-050`)
 - persona docs and journals, including operating identity, salience triggers, governance, taxonomy/routing, immediate-capture rules, retrieval metadata, and retirement/supersession guidance
 - factor-review policy and factor-review history
 - framework upgrade note: when the pack moves factor docs to `docs/agents/factor-<nn>-<name>.md` or introduces `Category:` dashboard grouping, reconcile the canonical docs and regenerate wrappers instead of treating `.claude/agents/` as the source of truth
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
 - `AGENTS.md` so **Codebase and documentation questions (auto-Guru)** and **Agent platform routing** match `seed-050`; run `python3 .wavefoundry/framework/scripts/render_platform_surfaces.py` (includes `render_agent_surfaces.py`) when `docs/agents/guru.md` exists to refresh tier-2 marker blocks and tier-3 native surfaces
 - tracked platform hook/config surfaces via `python3 .wavefoundry/framework/scripts/render_platform_surfaces.py` so generated hook entrypoints stay aligned with the current framework contract
 - repo-local prompt docs
   - `docs/agents/guru.md` — Guru role doc (`seed-211`); backfill when missing, regenerate when stale. Ensure it carries `Role: guru` so it appears in the dashboard Agents panel. When `seed-211` changed (e.g. multi-angle research protocol: Question Decomposition, Hypothesis Check, null-result surfacing), regenerate from the updated seed and update `Last verified`.
   - `docs/agents/wave-council.md` — Wave Council role doc (`seed-215`); regenerate when present and stale. The council protocol evolves across versions: Phase 2 seat instructions may be restructured (numbered steps, pre-primer independence discipline), synthesis may gain new required steps (Recommendations Verdict table with red-team closing reconciliation, pre-primer read quality check, output verbosity guidance). Regenerate whenever `seed-215` changed.
   - `docs/agents/archetype-council.md` — Archetype Council role doc (`seed-236`); regenerate when present and stale. Same protocol evolution applies: axis-declaration sequencing, null-finding requirements, Recommendations Verdict table, falsification check, output verbosity. Regenerate whenever `seed-236` changed.
 - `docs/prompts/agents/` prompt bodies when the repository keeps checked-in project-context/planning helper prompts; backfill missing specialist agent bodies introduced in `seed-212` through `seed-214` when not present:
 - `docs/prompts/agents/performance-reviewer.prompt.md` (`performance-reviewer` lane — `seed-212`)
   - `docs/prompts/agents/security-reviewer.prompt.md` (`security-reviewer` lane — `seed-213`)
   - `docs/prompts/agents/architecture-reviewer.prompt.md` (`architecture-reviewer` lane — `seed-214`)
   - `docs/prompts/agents/code-reviewer.prompt.md` (`code-review` lane — `seed-221`) when the repository keeps checked-in agent-oriented prompt bodies
 - **Senior builder specialist evaluation (seeds 222–224):** Read `docs/repo-profile.json` archetype and stack evidence to decide which lanes are relevant, then generate the matching role docs via `seed-050` / `render_agent_surfaces.py`:
   - `docs/agents/software-engineer.md` (`seed-222`) — relevant when the project ships backend/API/service code; generate when stack evidence confirms and the role doc is absent.
   - `docs/agents/frontend-developer.md` (`seed-223`) — relevant when the project has a UI layer or `design_system.design_evidence.detected` is `true`; generate when evidence confirms and the role doc is absent. Verify `docs/workflow-config.json` `design_system_policy` is present (backfill with `"evolvable"` if not).
   - `docs/agents/data-engineer.md` (`seed-224`) — relevant when the project has SQL schemas, migrations, ETL pipelines, or data-contract surfaces; generate when evidence confirms and the role doc is absent.
   - For each generated role doc, verify `docs/prompts/implement-wave.prompt.md` (or the local equivalent) references builder-lane selection so the coordinator allocates work from repository evidence, not habit.
 - **`red-team` role doc (seed-225):** `red-team` is a universal specialist whenever Wave Council is enabled. When council is enabled:
   - Generate `docs/agents/specialists/red-team.md` (or `docs/agents/red-team.md`) from `seed-225` if absent — the role doc must always be present and invokable.
   - Leave `fixed_seats` and `rotating_seat_policy` configuration to the project; do not add or remove `red-team` from council seats without operator instruction.
 - workflow config schema
 - `docs/workflow-config.json` `design_system_policy` — backfill when absent using `{"governance": "evolvable", "notes": "..."}`. The `"evolvable"` default is safe for all existing projects: it enforces no gate and allows design-system surfaces to evolve within normal implementation scope. Only set to `"read-only"` or `"review-governed"` when the operator explicitly requires protected design-system surfaces.
 - `AGENTS.md` and `CLAUDE.md` gate-tool references — when either file references `wave_open_gate` or `wave_close_gate`, update to `wave_gate_open`, `wave_gate_close`, and add `wave_gate_status` as the read-only gate inspection tool; reconcile against current `seed-050` wording. These surfaces are not regenerated automatically by `render_platform_surfaces.py` so they must be updated explicitly.
 - `docs/plans/plan-template.md` `## Acceptance Criteria` — when the section still uses plain bullet format (`- AC-1: ...`), update to checkbox syntax (`- [ ] AC-1: ...`) so newly scaffolded change docs are trackable during implementation. The docs-lint forward contract requires checkbox ACs in wave-admitted change docs.
 - `docs/plans/plan-template.md` `## Tasks` — when the section still uses plain bullets, update to checkbox syntax (`- [ ] <step>`) so newly scaffolded change docs support live task tracking during implementation.
 - `server_impl.py` `_default_template()` `## Acceptance Criteria` — when the function's scaffold still uses plain bullet format (`- AC-1:` without `[ ]`), update to `- [ ] AC-1:` and `- [ ] AC-2:` so the scaffold produced by `wave_new_enhancement`, `wave_new_feature`, and related tools generates checkbox ACs by default.
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
 - canonical workflow docs and role docs when the current framework standard requires them and they are missing or stale, including `wave-council` when `wave_review` is present or backfilled
 - `docs/ARCHITECTURE.md` and `docs/architecture/{current-state,domain-map,layering-rules,cross-cutting-concerns,data-and-control-flow,testing-architecture}.md` (and `docs/architecture/decisions/template.md` when ADR seeding changed) when `seed-060`, `seed-030`, or repository topology changed; merge with repo-specific depth per `060` guardrails
 - `docs/prompts/pause-wave.prompt.md` when the seed pack’s `seed-100` pause-wave rule changed — verify the standardized handoff structure (Done / Next / Files touched / Test state / Open questions) is present; backfill when missing
 - `docs/prompts/close-wave.prompt.md`, `docs/prompts/agents/close-wave.prompt.md`, and `docs/contributing/review-and-evals.md` (**Wave closure** / docs-contract-at-close) when the seed pack’s `seed-190` or `seed-100` closure expectations have evolved — verify the retrospective step (memory-candidate prompt) and idle handoff update (last-closed-wave summary + Open questions section) are present
 - **Pre-implementation review gate evaluation (seeds 180/100):** When `seed-180` or `seed-100` added the pre-implementation review gate, evaluate the local prompt surface:
   - `docs/prompts/implement-wave.prompt.md` — verify a **Pre-Implementation Review Gate** section exists describing the three-step gate (pre-mortem, packet completeness check, recorded verdict) and that it blocks the first code edit; backfill from current `seed-100` / `seed-180` contract when missing or absent.
   - `docs/prompts/review-wave.prompt.md` — verify a **Pre-Implementation Gate Reconciliation** section exists so reviewers confirm the gate ran before implementation; backfill when missing.
   - `docs/prompts/prepare-wave.prompt.md` — verify a lifecycle-sequence clarification note explains the order: plan → admit → Prepare wave → pre-implementation review gate → first edit; backfill when missing.
 - **AC verification truth hierarchy (seeds 170/180/100):** When these seeds added the checkbox AC contract and truth-hierarchy review language, evaluate local reviewer surfaces:
   - `docs/agents/qa-reviewer.md` — verify the operating identity states that code/tests are the truth source, checked boxes are claims not proof, and the refusal conditions include rejecting unchecked-AC completion claims; backfill from current framework standard when absent.
   - `docs/agents/code-reviewer.md` — verify the review rubric includes a truth-hierarchy note (document is coordination layer, not authority); backfill when absent.
   - `docs/prompts/review-wave.prompt.md` — verify an **AC and Task Verification Truth Hierarchy** section exists defining the three-layer truth stack (code/tests → review evidence → documentation); backfill when absent.
 - `docs/prompts/upgrade-wavefoundry.prompt.md` and `docs/prompts/agents/upgrade-wavefoundry.md` when the seed pack’s upgrade contract changes
 - **`.wavefoundry/bin/docs-lint`**, **`.wavefoundry/bin/docs-gardener`**, and any legacy **`./package-wave-framework`** repo-root wrapper so they point to the **current** script filenames under `.wavefoundry/framework/scripts/` or are retired when packaging is not supported in a target repository. These **bin** launchers (and any repo-root packaging helper) are **not** overwritten blindly by pack unpack, so reconcile them explicitly during upgrade. Required invocations:
 - `.wavefoundry/bin/docs-lint` must invoke `scripts/docs_lint.py`
 - `.wavefoundry/bin/docs-gardener` must invoke `scripts/docs_gardener.py`
 - `.wavefoundry/bin/wave-dashboard` must exist when `scripts/dashboard_server.py` is present in the pack; if missing, create it per `seed-152` task 2
 - `./package-wave-framework`, when intentionally retained in a source repository, must invoke `scripts/build_pack.py`

 Launcher filenames under **`.wavefoundry/bin/`** remain hyphenated for conventional CLI ergonomics; only the Python module filenames moved to snake_case.
 - `docs/contributing/build-and-verification.md` — ensure a **Git commits** subsection (operator-owned policy, aligned with `050` and **Git commits** in `AGENTS.md`) exists whenever that file is refreshed; backfill when missing or when `050` changed. Ensure a **Wave framework pack upgrade verification** section exists and matches `seed-040` task 17 (ordered checklist: root zip or manual tree update → **Upgrade wave framework** → docs gate (**agents with MCP:** **`wave_garden`** then **`wave_validate`**; **operators / CI / no MCP:** **`.wavefoundry/bin/docs-gardener && .wavefoundry/bin/docs-lint`**) → diff/commit; cross-links to `docs/prompts/upgrade-wavefoundry.prompt.md` and `docs/prompts/package-wavefoundry.prompt.md` when applicable; step-0 exclusions and product-build N/A note). Note that the framework test suite (`scripts/tests/`, `scripts/run_tests.py`) is a development-only artifact **not included in the distribution pack** — downstream repos must not reference it in upgrade verification steps. Backfill when the repo vendors the pack but the section is missing or stale.
 - `docs/design-system/design-language.md` — backfill when `docs/repo-profile.json` `design_system.design_evidence.detected` is `true` but `docs/design-system/design-language.md` does not exist; use the canonical structure defined in `seed-040` task 13 and re-run `030` design surface scan to gather current evidence before seeding. When `design-language.md` exists but `design_system` in the profile has changed since last verified (check `Last verified:` date in the file vs profile `design_sensitivity` or `ui_roots` changes), flag as stale and prompt the operator to refresh the file before closing the upgrade.
 - **`docs/design-system/` extraction contract backfill (merge-safe upgrade)** — when `docs/design-system/` exists in the target repository, run the extraction contract backfill defined in `seed-040` task 14 and `seed-010` step 8. This backfill is **merge-safe**: never delete or overwrite existing files. Steps:
 1. For each required path in the core tree (see `seed-040` task 14 or `seed-010` step 8 checklist), create the path if it does not yet exist using the stub content defined in those seeds. Never overwrite any existing file.
 2. **Schema-version reconciliation** — read the existing `docs/design-system/manifest.json`. Compare its `schemaVersion` field against the current framework's expected schema version (`"1.0.0"`). Use semver ordering: a manifest `schemaVersion` is stale when it is lexicographically earlier using semver rules (e.g. `"0.8.0"` < `"1.0.0"`). When the manifest's schema version is stale or when required top-level fields are absent, **add** the missing fields with their null/empty defaults (never remove or overwrite existing field values), then append a `meta`-category entry to `docs/design-system/gaps.md`:

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
10. **Full index rebuild after `CHUNKER_VERSION` bump:** If the pack upgrade changed `CHUNKER_VERSION` (visible in `.wavefoundry/framework/scripts/chunker.py`), a full index rebuild is required (the `update_index` phase handles this automatically, but you can also trigger it manually). `wave_index_health` will emit a `chunker_version_mismatch` advisory when the index was built with an older version. Use the docs-first approach so MCP is available immediately:
 ```bash
 # Phase 1: docs index — unblocks MCP immediately (~2.5 min)
 python3 .wavefoundry/framework/scripts/setup_wavefoundry.py --full
 # Phase 2: code index in background — foreground returns immediately
 python3 .wavefoundry/framework/scripts/setup_wavefoundry.py --background-code --full
 ```
 If either setup command fails specifically because a required model cannot be downloaded, keep recovery on the canonical setup path: in agent-driven sessions, ask the operator for permission to rerun the same setup command with network access or host escalation enabled. Do not replace this with a separate manual model-download step.
 Call `wave_index_health()` after phase 1 to confirm MCP is ready. See `docs/contributing/build-and-verification.md` **Upgrade rebuild requirement** for full details.

11. Re-run the docs gate (**MCP:** **`wave_garden`** then **`wave_validate`** when attached; **CLI:** **`.wavefoundry/bin/docs-gardener && .wavefoundry/bin/docs-lint`**).

12. **Reload/restart MCP and update indexes:** After the docs gate passes, reload the MCP server so the upgraded server code and any newly rendered hook/config surfaces take effect. Use the MCP call first:
 ```
 wave_mcp_reload()
 ```
 This reloads the implementation module in-process AND re-registers the FastMCP tool surface so parameter schemas, response shapes, and tool function callables land in the registry — no full server restart required for those (wave 131bt — 131d8). The host (Claude Code) needs an `/mcp` reconnect to refetch the tool list once the server re-introspects schemas; ask the operator to run `/mcp` after the reload.

 **Description string changes propagate via `notifications/tools/list_changed`** (wave 131bt — 131bu). When `wave_mcp_reload()` detects that any tool's docstring changed between the pre-reload and post-reload snapshots, it sends the MCP `notifications/tools/list_changed` protocol notification to the connected client. Spec-conformant clients re-fetch `tools/list` on receipt and surface the new descriptions automatically — no operator action, no `/mcp` reconnect, no host restart required. The response carries:

 - `description_changed_tools` — list of tool names whose description differs from the pre-reload snapshot (empty when nothing changed)
 - `tool_list_changed_notification_sent` — `true` when the notification fired successfully, `false` when sending failed (e.g., no active session at reload time)
 - A structured diagnostic — `tool_list_changed_notification_sent` (success) or `tool_list_changed_notification_failed` (failure) — with actionable next steps

 **If the operator reports new descriptions are still not visible after this reload:** the client may not honor the notification (host-specific behavior). Fall back to a full Claude Code restart (quit and relaunch). The diagnostic explains this. The MCP protocol primitive is the standard re-fetch trigger; whether the host acts on it is host-implementation-dependent.

 **Exception:** if the wave changed `server.py` itself (the thin runner module rather than `server_impl.py` or any tool definitions), a full session restart is still required because `server.py` cannot reload itself in-process. This case is rare and called out explicitly in the release notes when it applies. After reload or restart, check whether the dashboard is running and restart it if so:
 ```
 wave_dashboard_restart()
 ```
 (If the dashboard was not running, skip this step — do not start it uninstructed.) Then run `wave_index_build(content="docs", mode="update")` for the project layer. The framework index is shipped inside the pack and should not be rebuilt during an ordinary upgrade; only reindex the framework layer when the pack itself invalidated it or you are intentionally reindexing the Wavefoundry source repo. If `CHUNKER_VERSION` changed, a full rebuild is required instead — see step 10. **Semantic vs graph index callout (wave 1316n):** `wave_index_build` with `content="docs"`, `content="code"`, or `content="all"` rebuilds the semantic embedding indexes only — **the graph layer is NOT touched**. When the upgrade pack bumps `GRAPH_BUILDER_VERSION` (visible in `.wavefoundry/framework/scripts/graph_indexer.py`), running `wave_index_build(content="graph")` is the eager path. **Wave 131bt (131e2) safety net:** if you skip the eager rebuild, the FIRST graph query after upgrade (`code_callhierarchy`, `code_impact`, `code_graph_path`, `wave_graph_report`, `code_graph_community`) detects the version mismatch and synchronously rebuilds the graph in-process before returning — ~10–30 s once per upgrade. The response carries a `graph_auto_rebuilt` structured diagnostic with `from_builder_version`, `to_builder_version`, and `rebuild_duration_ms` so the rebuild is observable. The build response also includes `graph_rebuilt: false` and a clarifying notice when the call did not touch the graph; `wave_index_health` surfaces `graph.<layer>.last_built_at` per layer for explicit freshness checks. Eager rebuild remains preferred for predictability; auto-rebuild covers the agent-driven case where no operator runs the explicit step.

14. **Operating-memory upgrade reconciliation:** When `seed-006`, `seed-050`, `seed-120`, `seed-130`, `seed-140`, `seed-160`, `seed-170`, `seed-180`, `seed-190`, `seed-200`, or `seed-210` changed the journal/role/persona memory contract, upgrade existing projects using this checklist: When `seed-006`, `seed-050`, `seed-120`, `seed-130`, `seed-140`, `seed-160`, `seed-170`, `seed-180`, `seed-190`, `seed-200`, or `seed-210` changed the journal/role/persona memory contract, upgrade existing projects using this checklist:
 - Preserve operator standing directives, active cautions, security/release-sensitive notes, and evidence refs unless explicitly superseded with evidence.
 - Do not bulk-rewrite historical journal entries. Keep historical sections readable, add current operating-memory sections around them, and migrate only entries needed for current retrieval, promotion, or retirement.
 - Add or reconcile `Operating Identity`, `Salience Triggers`, and memory responsibilities in generated/local role and persona docs.
 - Reconcile `docs/agents/journals/README.md` and existing journal files to the current operating-memory contract: governance, taxonomy/routing, hot-path thresholds, progressive immediate capture, operational salience, retrieval semantics, validity windows, supersession, and retirement.
 - Replace closure-only phrasing with lifecycle-wide capture language: critical/high operating-memory signals may be journaled during planning, implementation, review, handoff, reindex, or closure.
 - Prefer seed-derived wording over local forks, but preserve project-specific constraints and repo-grown policy that remains valid.
 - Update local lifecycle prompts and contributing docs when they still route all journal work to `Close wave` only.
 - Rename `## Follow-up Signals` to `## Active Watchpoints` in all journal files where the old section name is present; preserve all content under the renamed header.
 - Run the docs gate after reconciliation (**MCP:** **`wave_garden`** then **`wave_validate`** when attached; otherwise **`.wavefoundry/bin/docs-gardener && .wavefoundry/bin/docs-lint`**).

**Graph extractor regression signal (framework-maintainer QA):** When a pack upgrade changes the graph extractor for any language, compare `code_callhierarchy.external_outgoing_count` / `external_incoming_count` on a representative project-internal symbol before and after the upgrade. A large drop (e.g. Solaris's `47 → 3` after wave `130qf` shipped the Swift positional-callee fallback) is diagnostic of the extractor fix landing — calls that were resolving to `external::*` now resolve to project nodes. A large increase suggests a regression in cross-file resolution. This is a maintainer-side QA signal across pack versions, not an in-session agent decision input.

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
 - If the upgraded pack includes the dashboard feature, call out **`Start dashboard`**, **`Stop dashboard`**, and **`Restart dashboard`** as the operator-facing loopback UI commands.
 - Lifecycle IDs remain `python3 .wavefoundry/framework/scripts/lifecycle_id.py`.

5. **Agents and personas**
- Note any added/retired generic role wrappers or factor-review agents tied to `docs/repo-profile.json` `factor_review` changes; call out factor-doc relocations to `docs/agents/factor-<nn>-<name>.md`, `Category:` grouping changes, persona policy changes from `persona_review_policy`, and operating-identity or salience-trigger updates applied to roles/personas.

6. **Documentation setup and verification**
 - Reiterate canonical entry: `docs/README.md`, `docs/prompts/index.md`, `docs/references/project-overview.md`.
 - Confirm post-upgrade docs gate ran or must run per `docs/contributing/build-and-verification.md`: **agents with MCP** — **`wave_garden`** then **`wave_validate`**; **operators / CI / no MCP** — **`.wavefoundry/bin/docs-gardener`** and **`.wavefoundry/bin/docs-lint`** (pass `--date <YYYY-MM-DD>` only when overriding today's date).

7. **Important configuration and precondition**
 - When step 0 ran, call out which zip was unpacked and that hooks were regenerated immediately afterward.
 - When step 0 did not run, upgrade applies the pack **already** in `.wavefoundry/framework/` on disk before this command started.
 - **Upgrade wave framework** does not download a newer framework. To adopt a newer pack without a local checkout patch, place a semver pack in the repository root, `~/.wavefoundry/`, or `~/.wavefoundry/dist/`, then run **Upgrade wave framework** again so step 0 adopts it automatically.
 - `docs/workflow-config.json` and `docs/repo-profile.json` remain the primary configuration surfaces for wave execution, reviews, factors, and personas.

8. **Operators new to wave-context (or re-onboarding after upgrade)**
 - Point them at **`AGENTS.md` → Start Here** and **`docs/prompts/index.md` Usage Notes** for the authoritative rules: **Git commits (operator-owned)** (agents do not `git commit` unless explicitly instructed in the **current** request), **stage gate** (plan + admit + **Prepare wave** / **Ready wave** before **repository code** edits), **Implementation guard** for product implementation source (and **in-session waiver** recording), **Implement wave** vs **Implement feature**, **docs-contract review** at **Close wave** / **Finalize feature** when specs changed, and **`docs/prompts/agent-routing-concurrency.prompt.md`** when plans need explicit concurrency.
 - If this upgrade changed closure or guard semantics, call that out explicitly so returning operators re-read **`docs/prompts/close-wave.prompt.md`** and **`AGENTS.md`** for the current bar. When the retrospective step or idle handoff format was added or updated, note that closure now includes a memory-candidate prompt and that the idle handoff must carry the last-closed-wave summary and an Open questions section.
 - If this upgrade changed pause-wave semantics, call that out explicitly so returning operators re-read **`docs/prompts/pause-wave.prompt.md`** — the standardized handoff structure (Done / Next / Files touched / Test state / Open questions) is now required.

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
- update `docs/plans/plan-template.md` `## Acceptance Criteria` to checkbox syntax (`- [ ] AC-N: ...`) when it still uses plain bullets; this is the forward contract required by the docs-lint checker for wave-admitted change docs
- update `docs/plans/plan-template.md` `## Tasks` to checkbox syntax (`- [ ] <step>`) when it still uses plain bullets so implementation tracking is consistent with Acceptance Criteria
- when `AGENTS.md` or `CLAUDE.md` still reference `wave_open_gate` or `wave_close_gate`, rename to `wave_gate_open`, `wave_gate_close`, and add `wave_gate_status` as the read-only gate inspection surface; these files are not regenerated by `render_platform_surfaces.py` so they must be reconciled explicitly
- backfill `design_system_policy` in `docs/workflow-config.json` when absent; the safe default is `{"governance": "evolvable"}` which enforces no gate on design-system surfaces and is appropriate for all existing projects unless the operator explicitly requires `"read-only"` or `"review-governed"` protection
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
- reconcile closure-process surfaces on upgrade whenever seed closure contract changed: `docs/prompts/close-wave.prompt.md`, `docs/prompts/agents/close-wave.prompt.md`, and `docs/contributing/review-and-evals.md` must explicitly enforce chronology reconciliation (`Status`, `Current state`, change states, `Completed at`), required-reviewer reconciliation from readiness to review checkpoints, closure-artifact reconciliation (journals/memory/handoff), docs-contract disposition rules, the retrospective step (memory-candidate prompt for architectural decisions and validated approaches), and the idle handoff update (last-closed-wave summary + Open questions section)
- reconcile pause-wave surfaces on upgrade whenever `seed-100` pause-wave rule changed: `docs/prompts/pause-wave.prompt.md` must include the standardized handoff structure with labeled sections (Done / Next / Files touched / Test state / Open questions); backfill when missing
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

## Agent surfaces and auto-Guru upgrade (agent procedure)

Agents performing **Upgrade wave framework** in a target repository must apply **all** steps below when the pack includes `seed-050` auto-Guru routing, `render_agent_surfaces.py`, or `seed-211` Guru changes. Do not stop after unpack or hook regeneration alone.

**Order of operations**

1. **Adopt pack** (step 0 when a root zip exists) or confirm `.wavefoundry/framework/` is current.
2. **Regenerate platform surfaces** (required every upgrade):
   ```bash
   python3 .wavefoundry/framework/scripts/render_platform_surfaces.py
   ```
   This materializes hooks, MCP host config (`.cursor/mcp.json`, `.mcp.json`, `.junie/mcp/mcp.json`), `.wavefoundry/bin/` launchers, and calls **`render_agent_surfaces.py`** when `docs/agents/guru.md` exists.
3. **Backfill tier 1 in `AGENTS.md`** (merge-safe; not overwritten by the renderer):
   - `## Codebase and documentation questions (auto-Guru)` — per `seed-050` template
   - `### Agent platform routing` — three tiers; optional native table; instruction-only hosts (Junie, Air, Windsurf, Copilot, Warp) use tier 1–2 only
   - Reconcile when missing or when `050` changed in the pack
4. **Ensure Guru role doc exists** (`seed-211`):
   - Target: `docs/agents/guru.md` with `Role: guru` in metadata
   - Update `docs/prompts/index.md` **Guru** row and legacy aliases
5. **Regenerate tier 2–3 agent routing** (required when `docs/agents/guru.md` exists):
   ```bash
   python3 .wavefoundry/framework/scripts/render_agent_surfaces.py
   ```
   Or re-run step 2. **Do not hand-edit** regions between `<!-- waveframework:auto-guru begin` and `end -->` — change `.wavefoundry/framework/scripts/render_agent_surfaces.py` in the framework source repo instead.
6. **Verify generated outputs** (see validation checklist bullets for auto-Guru).
7. **Per-host operator follow-up** (document in upgrade summary; operator executes):
   - **Cursor:** enable `wavefoundry` MCP from `.cursor/mcp.json` if not auto-loaded
   - **Claude Code:** restart session so `.mcp.json` and `.claude/agents/guru.md` load; subagent delegates per `description`
   - **Codex:** MCP server loads automatically from the committed `.codex/config.toml`; attach the `wavefoundry` server from the project-local config
   - **Junie / Copilot / Windsurf / Air / Warp:** tier-1 `AGENTS.md` + tier-2 thin-pointer bullet only; attach MCP per `AGENTS.md` MCP table
8. **Docs gate, MCP restart, project index** — continue with existing upgrade verification (not optional).

**Files written or updated by `render_agent_surfaces.py` when Guru is present**

| Path | Tier |
|------|------|
| `.cursor/rules/auto-guru.mdc` | 3 (when `.cursor/` exists) |
| `.claude/agents/guru.md` | 3 (when `.claude/` exists) |
| `.codex/skills/auto-guru/SKILL.md` | 3 |
| `CLAUDE.md` | 2 (marked block) |
| `.cursor/rules/project-context.mdc` | 2 (when Cursor) |
| `.junie/guidelines.md`, `WARP.md`, `.github/copilot-instructions.md` | 2 (when present) |

**Agent rules**

- Run `render_platform_surfaces.py` **after** tier-1 `AGENTS.md` backfill so thin pointers can be patched correctly.
- If tier-1 sections were just added, run `render_platform_surfaces.py` (or `render_agent_surfaces.py`) **again** after the merge.
- Record in the upgrade handoff which paths were created vs updated and whether Guru migration ran.
- Inventory/drift subagents stay **read-only**; only the upgrade owner (or delegated write lane) edits `AGENTS.md`, thin pointers, and generated marker blocks.

Validation areas that should be checked explicitly:

- required repo-local prompt docs exist and expose the intended public surface
- supporting repo-local prompt bodies exist in `docs/prompts/agents/` when the installed surface uses checked-in agent-oriented prompt bodies
- required canonical docs and topical artifact roots exist
- `docs/references/project-overview.md` exists and explains the project workflow plus role/persona collaboration model
- workflow config contains wave, memory, persona, prompt-generation, factor-review, and persona-review sections (`factor_review_policy` and `persona_review_policy` as separate keys)
- workflow config `required_review_lanes` key is present when the project declares required inferential sensor lanes (`security-review`, `architecture-review`, `performance-review`, `code-review`, or project-custom lanes); if absent and the project uses reviewer agents, prompt the operator to add it
- workflow config `sensors` key is present when the project registers computational sensors; document the format (`name`, `command`, `dimension`, `description`) in `docs/contributing/build-and-verification.md` when backfilling
- workflow config includes **`lifecycle_id_policy`** when the project vendors `lifecycle_id.py` in the repository, either present already or backfilled without mutating an existing epoch/offset
- workflow config `review_policies` includes `require_qa_reviewer_for_bug_fixes` when the project follows `docs/contributing/agent-team-workflow.md` bug-fix QA rules
- workflow config `wave_review` is present when the project adopts the framework-standard council model; when backfilling it, preserve repo-local seat overrides and transition policy rather than overwriting them
- workflow config wave-execution section contains readiness-review expectations when non-trivial wave execution is enabled
- wrappers point at the wave framework scripts rather than legacy script paths
- agent entry files are semantically aligned and still thin
- factor-review policy is still justified by evidence from the repository
- stale legacy helper references are either migrated or reported
- refreshable artifacts exist in their expected topical homes
- `AGENTS.md` and `CLAUDE.md` reference `wave_gate_open`, `wave_gate_close`, and `wave_gate_status` in any gate-usage guidance — not the retired `wave_open_gate` / `wave_close_gate` names; reconcile when the old names are still present
- `docs/plans/plan-template.md` uses checkbox syntax in `## Acceptance Criteria` (`- [ ] AC-N:`) so newly created change docs scaffold trackable ACs by default
- `docs/plans/plan-template.md` uses checkbox syntax in `## Tasks` (`- [ ] <step>`) so newly created change docs scaffold trackable task checklists by default
- senior builder role docs (`docs/agents/software-engineer.md`, `docs/agents/frontend-developer.md`, `docs/agents/data-engineer.md`) exist when repository evidence or operator configuration enables those specialist lanes; absent when not applicable
- `docs/agents/specialists/red-team.md` (or `docs/agents/red-team.md`) exists when Wave Council is enabled; `docs/workflow-config.json` `wave_review` reflects the project's chosen seat policy and is consistent with the role doc
- `docs/agents/wave-council.md` is regenerated from current `seed-215` when present — verify it reflects the current protocol (Phase 2 numbered steps, pre-primer independence discipline, Recommendations Verdict table with red-team closing reconciliation, pre-primer read quality check, output verbosity guidance); regenerate when stale
- `docs/agents/archetype-council.md` is regenerated from current `seed-236` when present — verify it reflects the current protocol (axis-declaration Step 1 before reading artifact, null-finding requirements, Recommendations Verdict table, falsification check, output verbosity); regenerate when stale
- `docs/prompts/implement-wave.prompt.md` contains a **Pre-Implementation Review Gate** section blocking first edit until the gate passes; `docs/prompts/review-wave.prompt.md` contains a **Pre-Implementation Gate Reconciliation** section
- `docs/agents/qa-reviewer.md` operating identity states the truth hierarchy (code/tests → review evidence → documentation) and refusal conditions include unsupported completion claims; `docs/agents/code-reviewer.md` review rubric includes a truth-hierarchy note
- `AGENTS.md` contains **Framework Script Hygiene** per `seed-050`; backfill from the canonical rule when missing
- `AGENTS.md` contains **Git commits (operator-owned)** per `seed-050`; `docs/contributing/build-and-verification.md` contains a **Git commits** section aligned with that policy when the file exists
- `AGENTS.md` contains **Implementation Principles** (four behavioral rules: Ask don't assume, Simplest solution first, Don't touch unrelated code, Flag uncertainty explicitly) per `seed-050` task 16; placed before `## Stage Gate`
- `AGENTS.md` contains **Implementation guard (product code)** when `docs/repo-profile.json` / `docs/repo-index.md` indicates shipped product code, per `seed-050`; backfill the section and thin-pointer startup lines when missing but the project is not documentation-only
- `AGENTS.md` contains **Codebase and documentation questions (auto-Guru)** and **Agent platform routing** per `seed-050`; backfill when missing or when `050` changed
- `AGENTS.md` is compact: scan for planning sections that predate the current implementation (dot-notation API calls, milestone lists, MVP definition-of-done blocks) and for inline MCP tool-detail prose that belongs in `docs/specs/mcp-tool-surface.md`; remove stale planning sections outright and replace inline tool-detail blocks with a one-line pointer to the spec; target file length ≤ 320 lines after compaction
- `docs/agents/guru.md` exists when the project uses Guru (`seed-211`)
- `python3 .wavefoundry/framework/scripts/render_platform_surfaces.py` ran during upgrade (hooks + MCP + bin launchers + `render_agent_surfaces.py`)
- when `docs/agents/guru.md` exists: `.codex/skills/auto-guru/SKILL.md` present; `.cursor/rules/auto-guru.mdc` when `.cursor/` exists; `.claude/agents/guru.md` when `.claude/` exists; tier-2 `waveframework:auto-guru` marker blocks on `CLAUDE.md` and each enabled thin pointer (`project-context.mdc`, `.junie/guidelines.md`, `WARP.md`, `.github/copilot-instructions.md`) with no duplicate unmarked bullets outside markers
- `docs/agents/platform-mapping.md` documents auto-Guru tier 1–3 routing when present in the repo
- do not hand-maintain hook logic or auto-Guru marker bodies when the renderer can own them
- Hook regeneration may manage Copilot agent files under `.github/hooks/`, but it must not create or modify GitHub Actions workflows under `.github/workflows/` and must not touch local git hooks under `.git/hooks/`
- `.claude/settings.json` contains the tracked launcher wiring rendered for the current host platform: `PreToolUse` Edit|Write -> `.claude/hooks/pre-edit` (or `cmd.exe /c .claude\\hooks\\pre-edit.cmd` on Windows) and `PostToolUse` Edit|Write -> `.claude/hooks/post-edit` (or Windows launcher); add or merge if partial. (Wave `1p35d` / `1p35n` retired the previous `PostToolUse` Bash -> `.claude/hooks/pycache-cleanup` row in favor of fixing `docs-lint` to exclude `__pycache__`.)
- `.claude/hooks/pre-edit.py`, `.claude/hooks/post-edit.py`, and `.claude/hooks/simulate-hooks.py` exist alongside their generated POSIX and Windows launchers; add if missing per `seed-050`. Any leftover `.claude/hooks/pycache-cleanup*` files from a pre-`1p35n` install may be deleted.
- `.claude/skills/upgrade-wave.md` exists with the verified upgrade gate sequence, including the repo-global `.wavefoundry/guard-overrides.json` approval flow for `framework_edit_allowed` and `seed_edit_allowed`; seed from `seed-050` if missing
- when the repository uses Cursor: `.cursor/hooks.json`, `.cursor/hooks/after-file-edit.py`, `.cursor/hooks/seed-warn.py`, `.cursor/hooks/framework-plan-warn.py`, and `.cursor/hooks/docs-lint.py` exist alongside their generated POSIX and Windows launchers, and `.cursor/hooks.json` points at the launcher form rendered for the current host platform; add if missing per `seed-050` Cursor Hook Contract
- when the repository uses Windsurf: `.windsurf/hooks.json` and `.windsurf/hooks/seed-protect.py` and `.windsurf/hooks/docs-lint.py` exist alongside their generated POSIX and Windows launchers, and `.windsurf/hooks.json` points at the launcher form rendered for the current host platform; add if missing per `seed-050` Windsurf Hook Contract
- when the repository uses GitHub Copilot coding agent: `.github/hooks/hooks.json`, `.github/hooks/pre-tool-use.py`, and `.github/hooks/post-tool-use.py` exist alongside their generated POSIX and Windows launchers, and the config points at the launcher form rendered for the current host platform; add if missing per `seed-050` GitHub Copilot Hook Contract
- `docs/agents/platform-mapping.md` reflects which supported platforms receive executable hooks (`claude`, `cursor`, `copilot`) and which stay prompt-driven (`codex`, `air`, `junie`, `warp`)
- `docs/prompts/index.md` contains an **Operating Rules** section (or equivalent) that references `.wavefoundry/framework/seeds/020-run-contract.prompt.md` as the authoritative run contract and carries the key behavioral rules inline; backfill when missing per `seed-100`
- canonical role docs (`docs/agents/implementer.md`, `docs/agents/planner.md`, `docs/agents/wave-coordinator.md`) each contain an **Execution contract** section with the role-relevant subset of rules from `seed-020`; backfill when missing per `seed-050` **Execution Contract in Canonical Role Docs**
- reviewer role docs (`docs/agents/code-reviewer.md`, `docs/agents/qa-reviewer.md`, `docs/agents/wave-council.md`) contain a **Review Rubric** or equivalent section referencing the preflight checks from `seed-020` **Prompt Preflight**
- `docs/contributing/agent-team-workflow.md` contains an **Execution contract** section with all six rules from `seed-020` and a reference to it; backfill when missing per `seed-150` task 5
- `docs/prompts/index.md`, `docs/prompts/prompt-surface-manifest.json`, and `AGENTS.md` shortcut tables remain **triplet-consistent** (no orphan public prompts, no duplicate shortcuts)
- `docs/workflow-config.json` retains top-level **`wave_implement`**, **`agent_memory`**, **`project_persona_generation`**, **`prompt_generation`**, **`factor_review_policy`**, **`persona_review_policy`**, and **`design_system_policy`** sections expected by the docs gate; `design_system_policy` is backfilled with `{"governance": "evolvable"}` when absent
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
