# Journal — Wave Coordinator

Owner: Engineering
Status: active
Last verified: 2026-05-01

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

## Recent Captures

wave-id: `12as7 wave-lifecycle-tool-fixes`
Closed: 2026-05-01
Change ID: `12as3-bug wave-create-scaffold-and-admit-placement`
Change ID: `12as6-enh single-active-wave-guard`

wave-id: `12as1 design-system-extraction`
Change ID: `12akr-enh design-system-directory-structure-extraction`
Change ID: `12arn-enh design-system-pattern-and-surface-depth`
Change ID: `12arn-enh design-system-bootstrap-and-governance`

wave-id: `12axj chunker-and-pack-improvements`
Change ID: `12avt-enh exclude-tests-from-framework-pack`
Change ID: `12avx-enh markdown-chunker-heading-hierarchy`
Change ID: `12aw5-enh structure-aware-code-chunker`

wave-id: `12awg mcp-tool-cleanup`
Change ID: `12awg-maint remove-wave-change-create`
Change ID: `12ax9-maint edit-gate-tools`
Change ID: `12axd-bug wave-close-overwrites-metadata`

wave-id: `12ahv mcp-agent-surface`
Change ID: `1297t-feat mcp-change-creation-coverage`
Change ID: `1298v-feat mcp-resource-template-surface`
Change ID: `12991-feat mcp-code-navigation-tools`

wave-id: `129p8 mcp-docs-search-reliability` (**closed** 2026-04-30)
Change ID: `129p7-bug mcp-docs-search-reliability`
Change ID: `129nj-enh agent-catalog-expansion`
Change ID: `129pc-enh wave-admit-relocates-change-doc`
Change ID: `129q6-enh mcp-index-watch-control`
Change ID: `12a0c-debt framework-script-code-quality`
Change ID: `12a0x-enh mcp-tool-annotations-and-search-limit`
Change ID: `12a17-feat multi-host-mcp-registration`
Change ID: `12a1j-feat wavefoundry-bin-cli-wrappers`
Change ID: `12a46-enh mcp-round2-review-fixes`
Change ID: `12a4d-enh wave-audit-tool`
- `2026-05-01` — Wave `12as7 wave-lifecycle-tool-fixes` **closed**. Two changes delivered: 12as3 fixed wave_create_wave `Last verified: <date>` scaffold bug and wave_add_change misplaced change blocks (6 tests); 12as6 added single-active-wave guard in wave_prepare (`another_wave_active` diagnostic + wave_pause recovery), extended wave_pause to transition `active→paused`, and migrated `wave_current` from `data.wave` (single) to `data.waves[]` (list of all non-closed waves; active→planned→paused; paused entries get `next_action: "resume_wave"`) — hard-break envelope change with full in-tree call-site migration (17 tests). 429/429 framework tests pass. Two architecture docs updated (`current-state.md`, `data-and-control-flow.md`). Prompt docs updated: `prepare-wave.md` (Single-Active-Wave Rule), `pause-wave.md` (status-transition semantics), `AGENTS.md` (envelope shape + guard rule). Lessons: pause is now a lifecycle state change (not just handoff); `wave_current` consumers must read `data.waves[]`; `resume_wave` is a next-action hint, not a new tool.
- `2026-05-01` — Wave `12as7 wave-lifecycle-tool-fixes` **opened**. Two independent server.py fixes: 12as3 fixes wave_create_wave `Last verified: <date>` placeholder and wave_add_change misplaced change blocks; 12as6 adds single-active-wave guard in wave_prepare with `another_wave_active` diagnostic + wave_pause recovery. Both discovered while opening `12as1 design-system-extraction`. Parallel-safe (different functions). No dependency on `12as1`.
- `2026-05-01` — Wave `12as1 design-system-extraction` **opened**. Three admitted changes split from an oversized single plan after pre-admission interrogation: 12akr core extraction contract (tree, DTCG tokens, manifest/gaps schema, install/upgrade backfill, chunker.py JSON-as-doc routing, rollback path, design-language.md coexistence); 12arn pattern-and-surface-depth (patterns subtrees, deep foundations/a11y, extended tokens, asset contract, semantic validators); 12arn bootstrap-and-governance (no-DS visual bootstrap, multi-surface targetSurfaces, HIG reference versions, deprecation/lineage, conditional product-class extensions). Hard ordering: 12akr first; the two 12arn changes depend on 12akr and are parallel-safe between themselves. `seed-040` is the serialization point across all three.
- `2026-05-01` — Wave `12ahv mcp-agent-surface` **opened**. Three admitted changes: MCP-first routing + 6 missing `wave_new_*` tools (1297t), MCP resource/template surface (1298v), exact code-navigation tools milestone 1 (12991). Prepare wave passes. Implement in order: 1297t → 1298v → 12991.
- `2026-04-30` — Wave `129p8 mcp-docs-search-reliability` **closed**. Ten admitted changes completed (MCP search/index health, specialist catalog + seeds, admit-time relocation + lifecycle tests, index watcher + `wave_index_build` + mutation freshness, script quality, MCP annotations round 1, multi-host MCP JSON merge, `.wavefoundry/bin/` + seed sweep, MCP round-2 correctness, **`wave_audit`** aggregate). Prefer **`wave_audit`** for combined readiness; follow **`next_tools`** on failure. Memory: `docs/references/project-context-memory.md` **MCP audit landing**.

## Distillation

- **Self-hosting path invariant:** `.wavefoundry/framework/` contains the canonical framework content. If scripts behave unexpectedly, verify with `ls .wavefoundry/framework/`.
- **Lifecycle ID epoch is fixed:** `epoch_utc: "2022-04-28T00:00:00Z"` was set at init from the greenfield fallback. Do not re-anchor this value — it invalidates all existing wave and change IDs.
- **Stage gate must precede all framework edits:** Any edit to `.wavefoundry/framework/scripts/` or `.wavefoundry/framework/seeds/` requires a clean Prepare wave pass as the immediately preceding lifecycle step.

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

## Active Watchpoints

- **Watchpoint:** Self-hosting mode — `.wavefoundry/framework/` is a real directory containing the canonical framework content. If this directory is missing or corrupted, all framework scripts fail. Check `ls .wavefoundry/framework/` if scripts behave unexpectedly; restore with `git checkout HEAD -- .wavefoundry/framework` if needed.
- **Watchpoint:** Stage gate must be enforced before any code edit to `.wavefoundry/framework/scripts/` or `.wavefoundry/framework/seeds/`. The coordinator must verify Prepare wave passed before delegating to an implementer.
- **Follow-up:** When MCP server scaffolding begins, update `docs/architecture/current-state.md` and re-evaluate factor 07 (port binding) and factor 09 (disposability) in `docs/repo-profile.json`.
