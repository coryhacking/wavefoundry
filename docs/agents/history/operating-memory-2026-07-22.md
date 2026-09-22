# Historical Operating Memory

Owner: Engineering
Status: archived
Role: operating-memory-2026-07-22
Category: specialist
Last verified: 2026-09-22

Retained historical journal payload, not current operating instructions. Current policy lives in the live role documents and canonical seeds.

## Source: docs/agents/wave-coordinator.md

## Operating Memory (migrated from the retired role journal, 2026-07-22)

The journal system is retired (wave 1t9w9); this section preserves the role journal's content verbatim. Durable new lessons go to typed memory records.

### Operating Identity

- Role: wave-coordinator — the agent role responsible for running wave lifecycle commands (Plan feature, Create wave, Add change to wave, Prepare wave, Implement wave, Review wave, Close wave) on the Wavefoundry repository.
- Responsibilities include: stage gate enforcement before implementation, AC priority recording at Prepare wave, complete closure including journal distillation and memory promotion.

### Salience Triggers

- **High:** Stage gate violated — implementation attempted without a clean Prepare wave pass. Stop, re-sequence.
- **High:** AC priority not recorded at Prepare wave — Review wave reconciliation cannot verify required ACs.
- **Medium:** Closure incomplete — journal distillation skipped or memory not promoted at Close wave.
- **Medium:** Operator requests a lifecycle step that conflicts with the current wave state (e.g., Close wave before Review wave completes).
- **Low:** Shortcut phrase ambiguity — coordinator invokes the wrong prompt due to similar-sounding command names.

### Distillation

- **Self-hosting path invariant:** `.wavefoundry/framework/` contains the canonical framework content. If scripts behave unexpectedly, verify with `ls .wavefoundry/framework/`.
- **Lifecycle ID epoch is fixed:** `epoch_utc: "2022-04-28T00:00:00Z"` was set at init from the greenfield fallback. Do not re-anchor this value — it invalidates all existing wave and change IDs.
- **Stage gate must precede all framework edits:** Any edit to `.wavefoundry/framework/scripts/` or `.wavefoundry/framework/seeds/` requires a clean Prepare wave pass as the immediately preceding lifecycle step.
- **`wf_current_wave` envelope is a list:** `data.waves[]` — not `data.wave`. Every call site reading the current wave must use the list form; the old single-key form no longer exists.
- **`patch.object` on a thin-runner module does not reach the impl module** (wave `12rbc`): When a module is split into a thin runner and an impl, `patch.object(runner_mod, "foo")` sets an attribute on the runner but impl functions call their siblings from their own namespace. Fix: `load_server()` must return `server_impl` (the impl module), not the runner. `patch.object(self.srv, "foo")` then patches the correct namespace. Python module `__setattr__` is not supported (PEP 562 covers `__getattr__`/`__dir__` only) — do not attempt to forward patches via a module-level `__setattr__`.
- **Python late-binding eliminates the need for monkey-patching own-module functions** (wave `12rbc`): A function defined early in a module can reference symbols (`_runner_version`, `version_payload`) defined later, because global-name lookup happens at call time. Prefer a single merged definition over `_orig_func = func; def func(): ... _orig_func() ...` patterns, which are subtle on `importlib.reload` and obscure intent.

### Active Signals

wave-id: `13129 graph-tools-field-feedback-round-2`

- Planned 2026-06-01: six changes addressing Solaris (Swift) + Aceiss (Java) field feedback on `1.2.0+312f`. Diagnostic decompositions (1312b, 1312j), section/view splits (1312d, 1312f, 1312h), and the source-of-truth fix promoting wave 130rj's receiver-type filter to the graph builder (1312l, `GRAPH_BUILDER_VERSION` bump). Pre-implementation council review pending.

wave-id: `12rnv agent-prompt-harness`

- Planned 2026-05-19: two changes — `12rbe` (security seeds) + `12rnv` (full harness). Independent of active wave `12rbc` (hot reload).

wave-id: `12cv4 prompt-indexing-quality`

- Closed: prompt indexing quality improvements, `.prompt.md` file extension rename, docs-first index onboarding guidance.

wave-id: `12d4b codebase-qa`

- Closed: Code Insight Agent (CIA) — codebase QA agent, knowledge extraction, code search result diversity, CIA seed distribution and agent guidance.

wave-id: `12bc4 journal-upgrade-coverage-gaps`

- Active: extending journal upgrade and distillation seeds to catch non-standard activity-log sections, missing Distillation sections, and dangling cross-references.

wave-id: `12ec2 index-build-stats-persistence`

- Closed 2026-05-06: persisted index build stats to `index-build-stats.json`; timing estimates in `index_build` notices, `index_build_status`, and `index_health` responses. Fixed placeholder signoff bypass bug (`<approved...>` no longer counts as real signoff). Fixed `build_pack.py` excluding nested `.wavefoundry` dirs.

wave-id: `12dv9 chunk-tags`

- Closed 2026-05-10: `tags: list[str]` field on Chunk, path-pattern heuristics in `_tag_utils.py`, `tags` filter on `docs_search`/`code_search`, CHUNKER_VERSION bumped, seed-211 Tags Filter section complete.

wave-id: `12mns code-ask-retrieval-quality`

- Planned 2026-05-14: five retrieval quality improvements from CDK monorepo field feedback — question-type-aware candidate weighting (CDK path penalty, RRF bias), timing instrumentation, agent guidance (layer recognition, call chain, SQL follow-up), SQL candidate boosting, dynamic VECTOR_TOP_K.

wave-id: `12mc3 agent-detail-panel-blank-section-mismatch`

- Implemented 2026-05-14: replaced `_DETAIL_SECTIONS` allowlist with full-doc markdown render; added `Role:` gate; specialist group fix; status field removed; WavesDialog pending fix; seed-050/006 canonical headings; persona Scope removed from lint; wave-doc path-based detector. Awaiting operator close signoff.

wave-id: `12mgm dashboard-table-render`

- Active 2026-05-14: extend `renderMarkdownish` to render markdown tables as HTML `<table>` elements; single change, small scope.

wave-id: `12m9w dashboard-closed-wave-progress-fixes`

- Closed 2026-05-14: progress bar accuracy for closed/completed waves (JS + Python); `Item Status:` and bare `Status:` parser fallbacks; AC-N scaffold standard in seed-170, plan-template, and MCP scaffold. Code-reviewer caught missing "completed" in `dialogChangesForScope` — fixed before close.

wave-id: `12m6b dashboard-ac-numbered-list-parser`

- Closed 2026-05-14: extended `_AC_LINE_RE` to `(?:-|\d+\.)` prefix; numbered-list ACs now parsed with checkbox support; 2 new tests added.

wave-id: `12hsd dashboard-completed-wave-pending-filter`

- Closed 2026-05-10: two pending-row bugs — exclude `completed` from pendingWaves(); stack title below ID in .pending-wave-left.

wave-id: `12xr1 graph-index-extraction-and-visualization`

- Planned 2026-05-27: first graph wave for deterministic graph export, incremental invalidation, and dashboard validation before query tooling.

wave-id: `12xr2 graph-query-surface`

wave-id: `12xr3 graph-augmentation-promotion`

wave-id: `1304x graph-mcp-parity-and-dashboard-polish`

wave-id: `1305t dashboard-graph-polish-and-dark-mode-fixes`

wave-id: `130et framework-bin-mcp-server-launcher`

wave-id: `12hs9 dashboard-pending-wave-id-wrap`

- Closed 2026-05-10: CSS fix — `.open-wave-id` nowrap scoped to `.pending-wave-left` to prevent wrap/misalignment in compact pending-wave rows.

wave-id: `12jnb project-index-stale-use-index-inputs`

- Planned 2026-05-12: investigate idle project-index rebuild loops and align project-layer stale detection with indexed project inputs instead of broad git-history/runtime-state signals.

wave-id: `12g47 dashboard-framework`

- Closed 2026-05-10: React+Python loopback dashboard, auto-index daemon, design system, gradient tile borders, dark mode fixes, docs-lint extended for dashboard-required fields. ADR naming convention enforced (`<id>-adr slug.md`). `_index_stats` fixed to read from actual chunk files. `dashboard-server.json` gitignored.

### Promotion Evidence

- Lessons about self-hosting path resolution and lifecycle ID epoch have been promoted to `docs/references/project-context-memory.md` at init.
- Future promotions: record incident here with reference to the target doc (e.g., `docs/references/project-context-memory.md`).

### Retirement And Supersession

- No entries are retired at init.
- Retire an entry when: its root cause is structurally resolved, the constraint no longer applies, or the context has been superseded by a wave decision. Mark as superseded with a note referencing the superseding wave.

### Governance

- No secrets, credentials, or PII in journals.
- Sensitive coordinator findings (e.g., trust boundary violations, security-relevant decisions): redact detail; note that the full record is in a secure channel.
- Review: distill at every wave closure; promote repeated, validated lessons to `docs/references/project-context-memory.md`.
- Retire entries when the constraint is no longer load-bearing. Delete retired entries after one wave cycle.

### Active Waves

wave-id: `12rbc mcp-impl-hot-reload`
- **Closed** 2026-05-20: server split (`server.py` thin runner + `server_impl.py`), `wf_reload_mcp`, upgrade hook, version fields, dashboard browser suppression, 1482 tests. Package `2026-05-19h`.

wave-id: `12rnv agent-prompt-harness`
- **Active** 2026-05-20: four changes — `12rbe` (seed-213 security generalization), `12rnv` (harness core 209 + specialists + bootstrap), `12rcp` (preflight rubric), `12rcd` (AGENTS.md implementation principles). Prepare wave passed; seed-209 must land before other seeds wire references.

wave-id: `12r09 automated-upgrade`
- Planned 2026-05-19: scripted upgrade path — upgrade-wavefoundry bin, check_version.py, upgrade_lib.py, dashboard upgrade-awareness, wf_upgrade_status MCP tool, wf_restart_dashboard guard.

wave-id: `12sg7 implementation-governance-upgrades`
- Planned 2026-05-21: five implementation-governance changes — senior builder roles (`12sf9`), MCP-first code navigation defaults (`12sfb`), checkbox AC/task tracking with dashboard alignment (`12sfj`), a formal prepare-phase review gate (`12sg4`), and dashboard dialog width/AC ID presentation (`12s5r`).

wave-id: `12qmg dashboard-ux`
- Planned 2026-05-18: `wf_open_dashboard` MCP tool — opens browser to running dashboard or starts it; `wf_start_dashboard` gains `next_tools` hint when already running.
- Added 2026-05-18: bug fix `12qmp` — `_make_lance_rows` None→"" normalization for `language`/`section` prevents LanceDB Null-column type crash on mixed-batch rebuilds.

wave-id: `12pn3 search-retrieval-quality`
- Planned 2026-05-17: five retrieval quality improvements — jina-v2-base-code for CODE_MODEL, LanceDB hybrid FTS+dense retrieval, chunk context enrichment at embed time, bge-reranker-v2-m3 upgrade with score propagation, and nomic-embed-text-v1.5-Q evaluation with EMBEDDING_PREFIXES infrastructure.

wave-id: `12nbr code-intelligence-expansion`
- Five code-intelligence changes: `code_callhierarchy`, LanceDB vector index, `code_hover`, `code_impact`, `code_outline` TS/SQL bug fix. Status: planned. Bug fix (`12nbp`) is independently deployable and highest-priority.

### Active Waves

wave-id: `12xfr id-generation-and-planning-improvements`

wave-id: `130rj graph-tools-field-feedback-tier-1-and-2`

### Active Watchpoints

- **Watchpoint:** Self-hosting mode — `.wavefoundry/framework/` is a real directory containing the canonical framework content. If this directory is missing or corrupted, all framework scripts fail. Check `ls .wavefoundry/framework/` if scripts behave unexpectedly; restore with `git checkout HEAD -- .wavefoundry/framework` if needed.
- **Watchpoint:** Stage gate must be enforced before any code edit to `.wavefoundry/framework/scripts/` or `.wavefoundry/framework/seeds/`. The coordinator must verify Prepare wave passed before delegating to an implementer.
- **Follow-up:** When MCP server scaffolding begins, update `docs/architecture/current-state.md` and re-evaluate factor 07 (port binding) and factor 09 (disposability) in `docs/repo-profile.json`.

## Source: docs/agents/implementer.md

## Operating Memory (migrated from the retired role journal, 2026-07-22)

The journal system is retired (wave 1t9w9); this section preserves the role journal's content verbatim. Durable new lessons go to typed memory records.

### Operating Identity

- Role: implementer — the agent role responsible for executing code changes per the admitted change doc on the Wavefoundry repository.
- Responsibilities include: following the change doc Requirements/Scope/AC, detecting code patterns before implementing, running framework tests and **preferring MCP `wf_validate_docs` / `wf_garden_docs`** for the docs gate after changes (bin launchers only without MCP), handing off diff and suggested commit message without committing.

### Salience Triggers

- **High:** Pre-edit hook blocks a framework script edit — confirm guard-override is set before retrying; do not bypass the hook itself.
- **High:** `python3 .wavefoundry/framework/scripts/run_tests.py` fails after implementation — do not signal complete until fixed.
- **Medium:** A pattern problem in `.wavefoundry/framework/scripts/` is severe enough to warrant deviation — surface with rationale and wait for operator approval before deviating.
- **Medium:** A tool or environment failure causes significant lost time — journal the failure mode so future sessions know the recovery path.
- **Low:** `__pycache__` appears in `git status` — the post-Bash hook may have failed; investigate `.claude/hooks/pycache-cleanup.py`.

### Distillation

- **Framework edit guard pattern:** To edit protected framework files, set `framework_edit_allowed: true` in `.wavefoundry/guard-overrides.json` (gitignored). Remove the override after the implementation session ends. The guard is not a shortcut to skip — it is the authorized bypass path.
- **Run tests before handoff:** `python3 .wavefoundry/framework/scripts/run_tests.py` must pass before signaling implementation complete. Do not rely on type checking or docs-lint alone.

### Active Signals

wave-id: `12c7n indexer-noise-exclusion`
- Binary files, lock files, and snapshot files generating index noise; line-window cap at 60 lines; TS export const truncation; micro-chunk merging. See wave for details.

wave-id: `12c86 tree-sitter-chunker`
- Replace regex chunkers with tree-sitter AST chunking. Depends on 12c7n. Verify grammar package version compatibility before starting.

wave-id: `12sg7 implementation-governance-upgrades`
- Includes `12s5r-enh dashboard-dialog-wider-ac-id-column`: widen agent-dialog from 800px to 1000px and add no-wrap AC ID column to AcsDialog. Edits confined to dashboard.css and dashboard.js under framework_edit_allowed gate.

wave-id: `12tms python-env-and-semver-implementation`
- `12tm5-enh python-tool-venv-bootstrap`: bootstrap `~/.wavefoundry/venv`; rewrite `_install_deps()` to use venv Python; remove `--break-system-packages`; add `pyproject.toml`. Implement before semver change so `pyproject.toml` exists when `packaging` dependency is added.
- `12tm5-enh migrate-versioning-to-semver`: add `_to_version()` + rewrite `compare_versions()` in `check_version.py` first; then `build_pack.py` semver input + `~/.wavefoundry/dist/` output; then `upgrade_wavefoundry.py` dist-dir discovery + hook rewrites. Do not stamp `VERSION` to `1.0.0` until `build_pack.py` semver support is complete.

wave-id: `12sq2 enterprise-role-seeds-and-lint`
- `12smw`: rename ui-ux-engineer → frontend-developer (seed 223, seed 050, other seeds); enhance software-engineer seed (222) with stack detection; author seeds for 7 existing specialists + 2 new specialist docs. All seed edits under single seed_edit_allowed gate; adding -developer to _BUILD_SUFFIXES requires framework_edit_allowed.
- `12sp5`: new lint validator in wave_validators.py enforcing pre-implementation gate verdict; requires framework_edit_allowed gate.
- `12sq4`: wf_close_wave summary generation in server_impl.py; requires framework_edit_allowed gate; implement after 12sp5 to avoid conflicts.

### Promotion Evidence

- No lessons promoted yet at init. Future promotions: reference `docs/references/project-context-memory.md` when an implementer-discovered pattern deviation becomes recurring.

### Retirement And Supersession

- No entries are retired at init.
- Retire the guard-override lesson if the pre-edit hook mechanism is replaced by a different guard in a future wave.
- Retire the run_tests lesson if the test runner command changes — update the lesson rather than letting it go stale.

### Governance

- No secrets, credentials, or PII in journals.
- Guard-override files (`.wavefoundry/guard-overrides.json`) are gitignored and must never appear in journal entries as raw content — note only that the override was set, not its contents.
- Review: distill at wave closure; promote approved pattern deviations to `docs/references/project-context-memory.md`.
- Delete retired entries after one wave cycle.

### Active Watchpoints

- **Watchpoint:** All framework scripts in `.wavefoundry/framework/scripts/` are protected by the pre-edit hook. Any edit attempt will be blocked unless `seed_edit_allowed` or `framework_edit_allowed` is set in `.wavefoundry/guard-overrides.json`. Verify the guard-override is set before attempting edits; do not bypass by editing the hook itself.
- **Watchpoint:** After any framework script edit, run `python3 .wavefoundry/framework/scripts/run_tests.py` before signaling implementation complete. Do not skip this step.
- **Watchpoint:** `__pycache__` directories are cleaned by the post-Bash hook. If a `__pycache__` appears in `git status`, the hook may have failed — check `.claude/hooks/pycache-cleanup.py`.

## Source: docs/agents/planner.md

## Operating Memory (migrated from the retired role journal, 2026-07-22)

The journal system is retired (wave 1t9w9); this section preserves the role journal's content verbatim. Durable new lessons go to typed memory records.

### Operating Identity

- Role: planner — the agent role responsible for discovery, change document authoring, and pre-admission interrogation on the Wavefoundry repository.
- Responsibilities include: scoping change docs using `docs/plans/plan-template.md`, surfacing affected architecture docs, generating lifecycle IDs, and making assumptions explicit before admission.

### Salience Triggers

- **High:** A discovery finding invalidates a planning assumption shared in a prior session — journal immediately; do not proceed on the invalidated assumption.
- **High:** An MCP tool contract change is being planned without `docs/specs/mcp-tool-surface.md` existing — this is a Level 3 blocker.
- **Medium:** A new architectural constraint discovered during planning affects the Affected architecture docs section — surface before admission.
- **Low:** Operator provides a scope directive that changes the planning approach mid-session — record the directive and the rationale.

### Distillation

- **code_patterns is not yet authoritative:** `docs/repo-profile.json` `code_patterns` status is `insufficient_history`. When planning changes to `.wavefoundry/framework/scripts/`, detect patterns by reading the existing scripts directly rather than relying on the profile field.
- **MCP spec is a prerequisite for MCP implementation:** Any wave touching MCP tool contracts requires `docs/specs/mcp-tool-surface.md` to exist before Prepare wave can pass. If this file is missing, record it as a Level 3 blocker in the change doc Risks section.

### Active Signals

wave-id: `12t9b public-rollout-readiness-decisions`

- Planned 2026-05-22: three rollout-readiness changes admitted for semver migration, cross-platform support policy, and Python tool-environment standardization. The current output is planning-only; implementation sequencing remains deferred behind the active unrelated wave.

wave-id: `12br9 code-search-language-filter`

- Language filter fix and extension normalization are implemented and tested (734 tests passing). Index rebuild needed after close to reindex existing code chunks with correct language tags.
- Embedding evaluation plan (`1297p-feat`) admitted to this wave for tracking; implementation deferred pending benchmark harness.

### Promotion Evidence

- No lessons promoted yet at init. Future promotions: reference `docs/references/project-context-memory.md` and the lesson being promoted (e.g., `code_patterns` semantics once they stabilize).

### Retirement And Supersession

- No entries are retired at init.
- Retire the `code_patterns` lesson once real implementation waves have run and the profile is updated to reflect stable patterns.
- Retire the MCP spec prerequisite lesson once `docs/specs/mcp-tool-surface.md` is created and validated.

### Governance

- No secrets, credentials, or PII in journals.
- Sensitive planning findings: redact and note the secure channel.
- Review: distill at wave closure; promote repeated tradeoffs to `docs/references/project-context-memory.md`.
- Delete retired entries after one wave cycle to keep the journal load-bearing.

### Active Watchpoints

- **Watchpoint:** `docs/repo-profile.json` `code_patterns` status is `insufficient_history`. Until real implementation waves complete and patterns stabilize, do not cite code_patterns as an authority — inspect the actual scripts for patterns at planning time.
- **Watchpoint:** `docs/missing-docs.md` lists `docs/specs/mcp-tool-surface.md` and two ADRs as gaps. Any change doc touching MCP tool contracts or major architectural decisions must note these gaps in the Risks section until the missing docs are created.
- **Watchpoint:** Factor 13 (API first) requires `docs/specs/mcp-tool-surface.md` to exist before MCP implementation begins. A planning pass that admits an MCP implementation change without this spec doc must be blocked at Prepare wave.

## Source: docs/agents/guru.md

## Operating Memory (migrated from the retired role journal, 2026-07-22)

The journal system is retired (wave 1t9w9); this section preserves the role journal's content verbatim. Durable new lessons go to typed memory records.

### Operating Identity

- Role: guru — the research and documentation agent responsible for answering natural-language questions about the codebase with grounded, cited responses.
- Responsibilities include: retrieval-grounded answers using the semantic index, edge case detection during discovery, operator Q&A for architectural ambiguity, external lookup against framework/library/spec docs, and recording durable findings in `docs/architecture/`, `docs/specs/`, and this journal.
- Write permissions: `docs/agents/guru.md` (this file), `docs/architecture/`, `docs/specs/`. All other paths are read-only.
- Operates under assumption discipline: every claim is either code-validated (cited) or explicitly flagged as pattern-inferred.

### Salience Triggers

- **High:** A retrieval pass returns no results for a topic that the operator expects to exist — this is an index gap; journal it with the query and the expected file so it can be investigated.
- **High:** An edge case is found that contradicts what the code's documentation or comments imply — journal immediately and surface in the answer.
- **High:** An operator question reveals an architectural intent that is not reflected anywhere in `docs/architecture/` — record the question and the answer; consider writing an ADR entry.
- **Medium:** External lookup reveals a framework behavior that differs from how the codebase uses it — record the discrepancy and the source URL.
- **Medium:** The same topic produces conflicting evidence across two or more files — record both files and the nature of the conflict; flag in the answer as requiring operator clarification.
- **Low:** A retrieval pass consistently requires Pass 3 (targeted structural) before producing useful results for a specific module — this may indicate the module needs a better docstring for `code-summary` indexing.

### Distillation

- No distilled lessons yet. Journal was created at wave 12dhh. Future lessons: record patterns that recur across multiple research sessions — topics the index handles well or poorly, common edge cases by module area, and operator Q&A answers that reveal non-obvious architectural constraints.

### Active Signals

wave-id: `12dhh cia-research-role`
wave-id: `12dkb doc-summary-frontmatter`
wave-id: `12dv9 chunk-tags`

- No other active signals at creation.

### Index Gaps

Record topics here when retrieval consistently fails to find expected content:

| Query pattern | Expected location | Notes |
|---|---|---|
| (none yet) | | |

### Promotion Evidence

- Repeated retrieval heuristics from recurring friction cases should be promoted into `docs/architecture/search-architecture.md` or kept here as a journal note once the pattern is stable enough to matter across sessions. The 2026-05-26 build-number retrieval case is the current example: owner-file bias for implementation verbs, exact-token follow-up for concrete artifacts, and two-hop expansion for prefix/suffix/build/stamp/version queries.
- No other lessons promoted yet. Future promotions: promote recurring edge cases to `docs/architecture/` or `docs/specs/` when they affect multiple implementers.

### Retirement And Supersession

- No entries retired at creation.
- Retire index gap entries once the relevant files have been reindexed and the gap is resolved.

### Governance

- No secrets, credentials, or PII in this journal.
- External lookup citations must include URL and retrieval date.
- Distill at wave closure; promote durable findings to `docs/architecture/` or `docs/specs/` rather than letting the journal grow unbounded.
- Discovery documentation follows the same assumption discipline as answers — do not record speculative or unvalidated findings.

## Source: docs/agents/personas/wave-coordinator.md

## Operating Memory (migrated from the retired role journal, 2026-07-22)

The journal system is retired (wave 1t9w9); this section preserves the role journal's content verbatim. Durable new lessons go to typed memory records.

### Operating Identity

- Persona: wave-coordinator — represents the developer or engineering lead in a target repository who runs wave lifecycle commands and drives readiness confirmation.
- Perspective: the coordinator expects the lifecycle to be well-defined and predictable. They notice when stage gate requirements are ambiguous, readiness criteria are underspecified, or closure requirements are unclear.

### Salience Triggers

- **High:** A behavior change makes the prepare→implement→review→close sequence ambiguous or harder to follow — record before accepting the change.
- **High:** A change would cause a coordinator to accidentally skip a required closure step — this is a persona-level regression.
- **Medium:** A shortcut phrase change creates confusion between similar-sounding commands — test phrase distinctiveness before accepting.
- **Low:** AC priority category definitions are unclear — coordinator cannot confidently record required vs. recommended ACs at Prepare wave.

### Distillation

- **Shortcut phrase surface must stay in sync:** The coordinator learns shortcut phrases from `AGENTS.md`. The prompt docs live in `docs/prompts/`. If these diverge, the coordinator will invoke the wrong prompt. Any shortcut phrase name change must update both surfaces atomically.
- **Prepare wave is not optional:** Any change to the lifecycle that softens the Prepare wave requirement (makes it conditional, adds an override path, or makes the stage gate ambiguous) must be reviewed against this persona. Skipping Prepare wave produces an unreviewed implementation.

### Active Signals

- None. This journal was seeded at framework install with no prior wave history.

### Promotion Evidence

- No lessons promoted yet at init. Future promotions: reference `docs/references/project-context-memory.md` when coordinator-facing regressions recur across waves (e.g., shortcut phrase divergence being a recurring stumbling block).

### Retirement And Supersession

- No entries are retired at init.
- Retire the shortcut phrase sync lesson if a formal sync validation is added to docs-lint.
- Retire the Prepare wave lesson if the stage gate is mechanically enforced by a CI check rather than relying on coordinator discipline.

### Governance

- No secrets, credentials, or PII in journals.
- Sensitive coordinator observations (e.g., security-relevant lifecycle gaps): redact and note the secure channel.
- Review: distill at wave closure; promote repeated coordinator pain points to `docs/references/project-context-memory.md`.
- Delete retired entries after one wave cycle.

### Active Watchpoints

- **Watchpoint:** The coordinator-facing shortcut phrase surface (`AGENTS.md` `## Shortcut Phrases` table and `docs/prompts/index.md` public commands table) must stay in sync. If a shortcut phrase is renamed in one location, both must be updated in the same change.
- **Watchpoint:** The prepare→implement→review→close sequence is the core contract for the coordinator. Any change that makes this sequence ambiguous is a coordinator-facing regression.
- **Watchpoint:** AC priority recording happens at Prepare wave. If the prepare-wave prompt doc does not explicitly require AC priority to be recorded in the change doc, the reviewer cannot verify required ACs at Review wave.

## Source: docs/agents/personas/framework-operator.md

## Operating Memory (migrated from the retired role journal, 2026-07-22)

The journal system is retired (wave 1t9w9); this section preserves the role journal's content verbatim. Durable new lessons go to typed memory records.

### Operating Identity

- Persona: framework-operator — represents the developer or engineering lead who installs, upgrades, and operates the Wave Framework in a target repository, consuming it as a dependency rather than as a maintainer.
- Perspective: the operator trusts the framework to handle complexity correctly and is not reading seed prompts directly — they read the rendered local surface and expect it to be self-contained.

### Salience Triggers

- **High:** A change makes the install or upgrade experience confusing for a first-time operator — record before accepting the change.
- **High:** A change could cause an operator to overwrite their own project-specific customizations unknowingly during upgrade — this is a regression.
- **Medium:** A change breaks the generated operator summary or makes it incomplete — the summary is a first-class deliverable.
- **Low:** Docs-lint failure after upgrade has an unclear fix path — the operator needs a clear error message pointing to `framework_revision` alignment.

### Distillation

- **Operator summary is a first-class deliverable:** The operator does not read seed prompts. The init output is the primary orientation artifact. Any change to seed-010 that reduces information density of the operator summary is a breaking change from the operator's perspective.
- **Upgrade overwrites risk:** Operator-customized prompt docs in `docs/prompts/` may be overwritten during upgrade if the upgrade seed does not distinguish framework-owned from operator-owned files. This risk is tracked in `docs/references/tech-debt-tracker.md` (DEBT-03 / DEBT-04).

### Active Signals

- None. This journal was seeded at framework install with no prior operator interaction history.

### Promotion Evidence

- No lessons promoted yet at init. Future promotions: reference `docs/references/project-context-memory.md` when operator-facing regressions recur across waves (e.g., `framework_revision` mismatch being a recurring stumbling block).

### Retirement And Supersession

- No entries are retired at init.
- Retire the upgrade overwrites lesson once the upgrade seed implements a clear operator-owned vs. framework-owned file distinction.
- Retire the operator summary lesson if the init output format is formally specified in `docs/specs/`.

### Governance

- No secrets, credentials, or PII in journals.
- Operator-specific configuration details (e.g., epoch values from operator installations): do not record in this shared journal — these belong in the operator's own project journal.
- Review: distill at install-wave or upgrade-wave closure; promote recurring operator pain points to `docs/references/project-context-memory.md`.
- Delete retired entries after one wave cycle.

### Active Watchpoints

- **Watchpoint:** The operator-facing upgrade workflow has one release contract: `wavefoundry-MAJOR.MINOR.PATCH.<build>.zip` is both the extractable feature pack and the executable protocol-1→2 carrier. If its filename format, search path, or handoff changes, update the **Upgrade wave framework** prompt and release block simultaneously.
- **Watchpoint:** The operator summary (output of Init wave framework) must tell the operator: what files were installed, what the lifecycle looks like, how to generate IDs, and where config lives.
- **Watchpoint:** Docs-lint failure after upgrade is the most common operator failure mode. The fix path (`framework_revision` must match `.wavefoundry/framework/VERSION`) should be surfaced clearly in any upgrade error output.

