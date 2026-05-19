# Journal — Wave Coordinator

Owner: Engineering
Status: active
Last verified: 2026-05-18

Actor: wave-coordinator
Schema version: 1.0
Last distilled: 2026-04-30

## Operating Identity

- Role: wave-coordinator — the agent role responsible for running wave lifecycle commands (Plan feature, Create wave, Add change to wave, Prepare wave, Implement wave, Review wave, Close wave) on the Wavefoundry repository.
- Responsibilities include: stage gate enforcement before implementation, AC priority recording at Prepare wave, complete closure including journal distillation and memory promotion.

## Salience Triggers

- **High:** Stage gate violated — implementation attempted without a clean Prepare wave pass. Stop, re-sequence.
- **High:** AC priority not recorded at Prepare wave — Review wave reconciliation cannot verify required ACs.
- **Medium:** Closure incomplete — journal distillation skipped or memory not promoted at Close wave.
- **Medium:** Operator requests a lifecycle step that conflicts with the current wave state (e.g., Close wave before Review wave completes).
- **Low:** Shortcut phrase ambiguity — coordinator invokes the wrong prompt due to similar-sounding command names.

## Distillation

- **Self-hosting path invariant:** `.wavefoundry/framework/` contains the canonical framework content. If scripts behave unexpectedly, verify with `ls .wavefoundry/framework/`.
- **Lifecycle ID epoch is fixed:** `epoch_utc: "2022-04-28T00:00:00Z"` was set at init from the greenfield fallback. Do not re-anchor this value — it invalidates all existing wave and change IDs.
- **Stage gate must precede all framework edits:** Any edit to `.wavefoundry/framework/scripts/` or `.wavefoundry/framework/seeds/` requires a clean Prepare wave pass as the immediately preceding lifecycle step.
- **`wave_current` envelope is a list:** `data.waves[]` — not `data.wave`. Every call site reading the current wave must use the list form; the old single-key form no longer exists.

## Active Signals

wave-id: `12cv4 prompt-indexing-quality`

- Closed: prompt indexing quality improvements, `.prompt.md` file extension rename, docs-first index onboarding guidance.

wave-id: `12d4b codebase-qa`

- Closed: Code Insight Agent (CIA) — codebase QA agent, knowledge extraction, code search result diversity, CIA seed distribution and agent guidance.

wave-id: `12bc4 journal-upgrade-coverage-gaps`

- Active: extending journal upgrade and distillation seeds to catch non-standard activity-log sections, missing Distillation sections, and dangling cross-references.

wave-id: `12ec2 index-build-stats-persistence`

- Closed 2026-05-06: persisted index build stats to `index-build-stats.json`; timing estimates in `wave_index_build` notices, `wave_index_build_status`, and `wave_index_health` responses. Fixed placeholder signoff bypass bug (`<approved...>` no longer counts as real signoff). Fixed `build_pack.py` excluding nested `.wavefoundry` dirs.

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

wave-id: `12hs9 dashboard-pending-wave-id-wrap`

- Closed 2026-05-10: CSS fix — `.open-wave-id` nowrap scoped to `.pending-wave-left` to prevent wrap/misalignment in compact pending-wave rows.

wave-id: `12jnb project-index-stale-use-index-inputs`

- Planned 2026-05-12: investigate idle project-index rebuild loops and align project-layer stale detection with indexed project inputs instead of broad git-history/runtime-state signals.

wave-id: `12g47 dashboard-framework`

- Closed 2026-05-10: React+Python loopback dashboard, auto-index daemon, design system, gradient tile borders, dark mode fixes, docs-lint extended for dashboard-required fields. ADR naming convention enforced (`<id>-adr slug.md`). `_index_stats` fixed to read from actual chunk files. `dashboard-server.json` gitignored.

## Promotion Evidence

- Lessons about self-hosting path resolution and lifecycle ID epoch have been promoted to `docs/references/project-context-memory.md` at init.
- Future promotions: record incident here with reference to the target doc (e.g., `docs/references/project-context-memory.md`).

## Retirement And Supersession

- No entries are retired at init.
- Retire an entry when: its root cause is structurally resolved, the constraint no longer applies, or the context has been superseded by a wave decision. Mark as superseded with a note referencing the superseding wave.

## Governance

- No secrets, credentials, or PII in journals.
- Sensitive coordinator findings (e.g., trust boundary violations, security-relevant decisions): redact detail; note that the full record is in a secure channel.
- Review: distill at every wave closure; promote repeated, validated lessons to `docs/references/project-context-memory.md`.
- Retire entries when the constraint is no longer load-bearing. Delete retired entries after one wave cycle.

## Active Waves

wave-id: `12pn3 search-retrieval-quality`
- Planned 2026-05-17: five retrieval quality improvements — jina-v2-base-code for CODE_MODEL, LanceDB hybrid FTS+dense retrieval, chunk context enrichment at embed time, bge-reranker-v2-m3 upgrade with score propagation, and nomic-embed-text-v1.5-Q evaluation with EMBEDDING_PREFIXES infrastructure.

wave-id: `12nbr code-intelligence-expansion`
- Five code-intelligence changes: `code_callhierarchy`, LanceDB vector index, `code_hover`, `code_impact`, `code_outline` TS/SQL bug fix. Status: planned. Bug fix (`12nbp`) is independently deployable and highest-priority.

## Active Watchpoints

- **Watchpoint:** Self-hosting mode — `.wavefoundry/framework/` is a real directory containing the canonical framework content. If this directory is missing or corrupted, all framework scripts fail. Check `ls .wavefoundry/framework/` if scripts behave unexpectedly; restore with `git checkout HEAD -- .wavefoundry/framework` if needed.
- **Watchpoint:** Stage gate must be enforced before any code edit to `.wavefoundry/framework/scripts/` or `.wavefoundry/framework/seeds/`. The coordinator must verify Prepare wave passed before delegating to an implementer.
- **Follow-up:** When MCP server scaffolding begins, update `docs/architecture/current-state.md` and re-evaluate factor 07 (port binding) and factor 09 (disposability) in `docs/repo-profile.json`.
