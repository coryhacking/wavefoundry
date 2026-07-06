# Wave Change Manifests and Close-Time Docs Advisory

Change ID: `1rppn-enh wave-change-manifests-close-advisory`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-07-04
Wave: TBD (future wave; depends on `1ro43-enh churn-aware-retrieval-decay` landing in wave `1ro44`; natural companion to `1rolq-enh verify-docs-agentic-review`)

## Rationale

The churn-aware decay machinery (`1ro43`, wave `1ro44`) attributes doc-code drift to waves by deriving each wave's change set from the commit log — the landing-commit convention ("Land wave <id>: …") maps a wave to the files its landing diff touched. That derivation is deliberately heuristic and it has known precision limits: bundle commits attribute coarsely (a single release commit has landed five waves, so all five share one change set), the convention's wording wobbles across history, and target repositories that adopt Wavefoundry may not follow the convention at all. Attribution built on a commit-message grep is a good v1 primitive and a permanent backfill path, but it is not a contract.

This change makes wave→files attribution deterministic at the source: `wave_close` captures a **wave change manifest** — the code files and docs actually changed during the wave — as a first-class, repo-visible artifact in the wave folder. Because commits are operator-owned in this framework, close time usually precedes the landing commit; the manifest therefore captures the union of commits since the wave's baseline and the working-tree changes present at close, rather than assuming a completed commit exists.

The manifest also unlocks the **leading** staleness signal, which post-hoc derivation cannot provide: advisories at the moment drift is created. Every change doc already declares an `## Affected Architecture Docs` section — a hand-authored statement of which docs *should* change with the code — but nothing consumes it mechanically today. At close, two comparisons become possible while context is hottest: docs **declared** affected but never touched during the wave, and docs that **reference** code the wave touched (via graph doc→code edges) but were not updated. Surfacing both as close-time advisories lets the closing agent amend docs immediately or hand attributed review candidates to the Verify docs loop (`1rolq`), instead of letting drift rot silently into the lagging worklist.

## Requirements

1. Record a **wave baseline** when a wave becomes OPEN (activation via `wave_prepare(mode='create')` / `wave_implement` / `wave_reopen`): the current HEAD commit, stored in the wave folder. Reopening an already-baselined wave preserves the original baseline and appends the reopen point (list, not scalar).
2. At `wave_close` (both `dry_run` and `create`), compute the **wave change manifest**: repo-relative paths changed since the baseline, as the union of (a) commits from baseline to current HEAD and (b) uncommitted working-tree changes (staged and unstaged) at close time. Classify entries as code vs docs using the existing include-prefix/docs conventions.
3. Persist the manifest as a machine-readable, repo-visible artifact in the wave folder (working candidate: `docs/waves/<wave-id>/manifest.json`; exact name/format finalized at implementation and recorded in the Decision Log). `mode='dry_run'` computes and reports the manifest without writing it; `mode='create'` writes it as part of close. The artifact is documentation-adjacent state, not a lint target requiring change-doc sections.
4. Close-time **declared-docs advisory**: compare each admitted change doc's `## Affected Architecture Docs` entries against the manifest's touched docs. Declared-but-untouched docs produce a named diagnostic in the close response (dry-run included). Advisory only — it must not block close; `N/A` declarations are respected.
5. Close-time **referencing-docs advisory**: docs that reference code files the wave touched (graph doc→code edges and explicit path references, reusing `1ro43` reference extraction) but were not themselves touched produce a capped, severity-ordered advisory list in the close response, each entry carrying wave attribution. Advisory only.
6. Drift attribution ladder: the `1ro43` drift computation consumes manifests as the **preferred** wave→files source when present, falling back to landing-commit derivation, then raw commit churn. The ladder is a single documented resolution order, and `anchor`/attribution metadata records which rung supplied the answer.
7. Worklist enrichment: drift worklist entries (consumed by `1rolq`) carry wave attribution when a manifest or derivation supplies it — wave id(s) and wave title(s) responsible for the drifting churn — so the reviewing agent can read the wave record instead of diffing blind.
8. Backfill remains derivational: no requirement to generate manifests for historical waves; the landing-commit derivation from `1ro43` covers history. A manifest, when present, always wins over derivation for the same wave.
9. Local-only, no blocking behavior: all computation uses local git; close never gains a new blocking gate from this change; `wave_close` behavior is otherwise unchanged (operator-owned close approval rules are untouched).

## Scope

**Problem statement:** Wave→files attribution is heuristic (commit-message derivation) and staleness signals are lagging-only. Nothing captures what a wave actually changed at the moment of close, nothing consumes the declared `Affected Architecture Docs` contract, and drift is discovered long after the wave context that created it has gone cold.

**In scope:**

- Baseline capture at wave activation; manifest computation and persistence at `wave_close` (dry-run reporting + create-time write).
- Manifest artifact format in the wave folder (machine-readable, repo-visible, diff-reviewable).
- Declared-docs and referencing-docs close-time advisories in the `wave_close` response envelope.
- Drift attribution ladder (manifest → landing-commit derivation → raw churn) in the `1ro43` computation path.
- Wave attribution fields on drift worklist entries.
- Tests: baseline capture/reopen semantics, manifest union (commits + working tree), classification, advisory correctness (declared and referencing), non-blocking behavior, attribution-ladder precedence, dry-run purity (no writes).
- Seed/prompt guidance updates for close-wave describing the advisories (gated seed edits).

**Out of scope:**

- Any blocking close gate on documentation state — advisories only.
- Historical manifest backfill (derivation covers history by design).
- The agentic disposal of advisories (owned by `1rolq`); this change only produces attributed candidates.
- Dashboard visualization beyond whatever the close response already surfaces.
- Cross-repository manifest aggregation; network calls of any kind.

## Acceptance Criteria

- [ ] AC-1: Activating a wave records its baseline commit in the wave folder; reopen appends rather than overwrites; a wave activated before this change (no baseline) degrades to derivation-only with a clear diagnostic, not an error.
- [ ] AC-2: `wave_close(mode='dry_run')` reports the manifest (code/docs classification, commit + working-tree union) without writing; `mode='create'` persists the artifact; a fixture wave with both committed and uncommitted changes yields the correct union.
- [ ] AC-3: Declared-but-untouched `Affected Architecture Docs` entries produce a named advisory diagnostic listing the specific docs and their declaring change docs; `N/A` declarations produce no advisory; close is never blocked.
- [ ] AC-4: Docs referencing wave-touched code but untouched in the wave appear in a capped, severity-ordered advisory with wave attribution; the cap and ordering fields are named constants.
- [ ] AC-5: The drift attribution ladder resolves manifest → derivation → churn in that order, records which rung answered, and a fixture demonstrates a manifest overriding a conflicting derivation for the same wave.
- [ ] AC-6: Drift worklist entries carry wave id/title attribution when available; entries without attributable waves still appear (attribution is enrichment, not a filter).
- [ ] AC-7: Close-wave guidance surfaces describe both advisories and route disposal to the Verify docs loop; no gate language is added (verified by reading the touched seeds/prompts).
- [ ] AC-8: Full framework tests run bytecode-free and docs validation passes.

## Tasks

- [ ] Implement baseline capture at wave activation (prepare-create / implement / reopen paths) with reopen-append semantics.
- [ ] Implement manifest computation at close: baseline→HEAD commit walk + working-tree status union, code/docs classification.
- [ ] Define and persist the manifest artifact; record format/name decision in the Decision Log; ensure dry-run purity.
- [ ] Implement the declared-docs advisory (parse `Affected Architecture Docs` from admitted change docs, honor `N/A`).
- [ ] Implement the referencing-docs advisory reusing `1ro43` reference extraction; cap + severity ordering as named constants.
- [ ] Wire the attribution ladder into the `1ro43` drift computation and add wave attribution to worklist entries.
- [ ] Update close-wave seed/prompt guidance (open/close `seed_edit_allowed` around seed edits; advisory language only, no gates).
- [ ] Tests per AC list; run `python3 .wavefoundry/framework/scripts/run_tests.py` and `wave_validate`.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| baseline-manifest | implementer | — | Baseline capture, manifest computation/persistence |
| close-advisories | implementer | baseline-manifest | Declared-docs + referencing-docs advisories |
| attribution-ladder | implementer | baseline-manifest | Ladder in drift computation, worklist enrichment |
| guidance | implementer | close-advisories | Close-wave seed/prompt advisory text (gated) |
| tests-docs | qa-reviewer | all implementation streams | Fixtures, dry-run purity, non-blocking proofs, validation |


## Serialization Points

- Hard dependency: `1ro43-enh churn-aware-retrieval-decay` (wave `1ro44`) must land first — this change extends its drift computation, reference extraction, and worklist format. Do not admit before `1ro44` closes.
- Companion sequencing with `1rolq-enh verify-docs-agentic-review`: both target the same future-wave window and both enrich the worklist; if admitted to the same wave, the worklist-format edits serialize (attribution fields land before or with the prompt surface that reads them).
- Prompt-surface maintenance: intended edits are close-wave guidance seeds + rendered prompts only, gated by `seed_edit_allowed` per edit; no new shortcut phrases; all other surfaces read-only. Seeds must not cite wavefoundry-internal change/wave IDs.
- Baseline capture touches the wave activation paths guarded by the single-OPEN rule — no change to activation semantics, recording only.

## Affected Architecture Docs

- `docs/architecture/data-and-control-flow.md` — baseline capture at activation, manifest computation at close, advisory flow into the worklist.
- `docs/architecture/search-architecture.md` — attribution ladder position in the drift computation.
- `docs/architecture/current-state.md` — wave-folder manifest artifact in the topology.
- ADR optional: manifest-at-close vs derivation-only attribution (the Decision Log here may suffice; decide at Prepare wave).

## AC Priority

(Proposed; confirmed at Prepare wave.)


| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | Baseline is the substrate; without it the manifest has no anchor. |
| AC-2 | required | The manifest artifact is the deliverable; the commit+working-tree union is what makes it correct pre-landing. |
| AC-3 | required | The declared-docs advisory makes the existing Affected Architecture Docs contract load-bearing — the leading signal this change exists for. |
| AC-4 | important | The referencing-docs advisory is high-value but derivable later from the worklist; the declared advisory is the novel contract. |
| AC-5 | required | A single documented attribution ladder prevents two sources of truth from disagreeing silently. |
| AC-6 | important | Attribution enriches review; the worklist functions without it. |
| AC-7 | required | Advisory-not-gate is an explicit operator decision; accidental gate language changes lifecycle behavior. |
| AC-8 | required | Standard framework verification gate. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-04 | Drafted from operator direction during wave `1ro44` planning: wave-attributed decay tracking, with commit-log derivation as the v1 primitive in `1ro43` and this change as the deterministic close-time hardening plus leading-signal advisories. | Discussion recorded in `1ro43` Decision Log; `_detect_wave_status_drift` (status-only close drift today); landing-commit convention in git history. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-04 | Capture manifests at close (baseline→HEAD commits ∪ working-tree changes) rather than relying solely on landing-commit derivation. | Commits are operator-owned and typically happen after close, so the landing commit does not exist at close time; the union is the only accurate capture point, and it makes attribution deterministic for waves closed after this ships while derivation covers history. | **Derivation-only forever:** weakness — bundle commits and convention wobble permanently cap attribution precision, and target repos without the convention get nothing. **Manifest from landing commit post-hoc (a later reconcile step):** weakness — requires a second operator-driven touchpoint after commit, which experience says will be skipped. |
| 2026-07-04 | Advisories at close are non-blocking, and the declared-docs comparison consumes the existing `Affected Architecture Docs` section rather than introducing new declaration syntax. | The section already exists in every change doc and is already reviewed at prepare; making it load-bearing costs nothing at authoring time. Blocking close on doc updates would hold waves hostage before advisory precision is known. | **New machine-readable declaration block in change docs:** weakness — duplicate declaration surface, more lint, no added information. **Blocking gate at close:** weakness — converts an unproven signal into a tax; tightening later is cheap. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Working-tree noise at close (unrelated local edits) pollutes the manifest | Manifest computation respects the same ignore/include rules as indexing; the dry-run report shows the manifest before create writes it, so the closing operator sees pollution before it persists. |
| Baseline missing for waves opened before this ships | Explicit degrade path (AC-1): derivation-only attribution with a diagnostic, never an error. |
| Advisory noise trains agents to ignore the close response | Referencing-docs advisory is capped and severity-ordered; declared-docs advisory only fires on explicit declarations; both route to the worklist rather than demanding inline action. |
| Manifest format churn breaks downstream consumers | Format decided once at implementation, recorded in the Decision Log, versioned field included from v1; the attribution ladder isolates consumers from source details. |
| Multi-wave bundle landings still blur post-close code attribution in derivation fallback | Manifests eliminate the blur for post-ship waves; derivation coarseness is documented as wave-set attribution rather than silently wrong per-wave claims. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
