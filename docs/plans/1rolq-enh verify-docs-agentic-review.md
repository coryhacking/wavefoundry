# Verify Docs: Agentic Doc-Code Applicability Review

Change ID: `1rolq-enh verify-docs-agentic-review`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-07-20
Wave: TBD (future wave; depends on `1ro43-enh churn-aware-retrieval-decay` landing in wave `1ro44`)

## Rationale

The churn-aware decay machinery (`1ro43-enh churn-aware-retrieval-decay`, wave `1ro44`) ships the mechanical tier of documentation decay: per-chunk churn metadata, a doc-code drift signal anchored to the doc's last content change or verification stamp, annotation on retrieval citations, and a drift worklist. That tier can only ever **propose** staleness. Churn is suspicion, not a verdict: code can churn through thirty commits without invalidating a doc that describes it, and a single rename can invalidate a doc whose referenced files never changed. Deciding whether a document still applies requires reading it against the current code — judgment, not computation.

Nothing in the framework performs that judgment today. `wf_garden_docs` stamps `Last verified` mechanically on any git-changed doc (`docs_gardener.refresh_last_verified` is a regex date substitution) — it records "this file was touched," not "someone confirmed this doc matches the code." Without a deliberate verification workflow, drift flags accumulate with no disposal path, stamped dates launder non-verification into apparent verification, and the decay signal decays into noise itself.

This change adds the **agentic tier**: a Verify Docs review loop, shipped as a prompt surface rather than a server-side computation. The MCP server stays mechanical (the same boundary `code_ask` observes — tools retrieve, agents synthesize); a prompted agent consumes the drift worklist, reads each flagged doc against the code it describes, and disposes it with evidence: **verified** (write a commit-SHA verification stamp), **amend** (fix the doc), or **stale** (mark superseded). Verification stamps reset the drift clock exactly (drift = commits touching referenced files after the stamp SHA), and stamps age visibly — once post-stamp churn crosses the threshold the doc re-enters the worklist, making verification a recurring maintenance cycle rather than one-shot false comfort. The pattern mirrors the propose/dispose reconciliation loop of `1p8gy-enh graph-backed-agent-memory`: mechanical signals propose, deliberate review disposes.

## Requirements

1. Add a **Verify docs** shortcut phrase and prompt surface (`docs/prompts/verify-docs.prompt.md` rendered from a new canonical seed under `.wavefoundry/framework/seeds/`) that defines the agentic review loop end to end: worklist intake, per-doc review procedure, disposition rules, evidence requirements, and write-back mechanics.
2. Worklist intake: the loop consumes the drift worklist shipped by `1ro43` (audit/report drift summary), ordered by drift severity — `commits_since` and, where the graph provides it, centrality of the drifted referenced files. The prompt must instruct the agent to work the list top-down and to cap a single pass at a reviewable batch rather than attempting exhaustive sweeps.
3. Per-doc review procedure: for each flagged doc the agent reads the doc and the current state of its referenced code (`code_read` / `code_outline` of `drift_refs`, plus `docs_search`/`code_search` where references are indirect) and judges applicability. The prompt forbids disposing a doc from memory or from the drift metadata alone — the code must actually be read.
4. Exactly three dispositions, each with a mandatory write-back:
   - **verified** — the doc still matches the code: write the verification stamp (the frontmatter field shipped by `1ro43`) at the current commit SHA. Silent stamp-bumping without reading the code is prohibited and the prompt text says so explicitly.
   - **amend** — the doc is partially stale: edit the doc to match current code (which resets the drift anchor via content change); the normal docs gate applies to the edit.
   - **stale** — the doc no longer applies and is not worth amending: mark it superseded/deprecated per existing docs conventions, preserving history (no deletion).
5. Every disposition records evidence: which referenced files were read, what changed since the anchor, and why the disposition follows. Evidence lands in the pass report (Requirement 6) — dispositions without evidence are a defect the prompt must name.
6. Each Verify docs pass produces a compact pass report (reviewed count, dispositions by type, remaining worklist depth) appended to a running log location decided at implementation (candidates: a `docs/reports/` report per pass, or a rolling section in the drift report; record the choice in the Decision Log).
7. Integration without gating: the loop is invokable on demand via the shortcut phrase and referenced as an **optional** maintenance step from `wf_garden_docs` guidance and the close-wave/distill-journals surfaces. It must not become a blocking gate on any lifecycle transition in this change.
8. Stamp-writing stays deliberate: `docs_gardener` and every other mechanical surface remain excluded from writing verification stamps (enforced by `1ro43`); this change adds the only sanctioned writer — the agentic pass with evidence — plus direct operator edits.
9. Local-only: the loop uses existing local MCP retrieval tools; no network dependency and no LLM invocation inside the MCP server.

## Scope

**Problem statement:** Drift flags from the mechanical decay tier have no disposal path. Nothing in the framework reads a flagged doc against the current code and renders an applicability verdict, so stale docs stay flagged forever, verified docs cannot prove it, and the drift worklist only grows.

**In scope:**

- New canonical seed + rendered `docs/prompts/verify-docs.prompt.md` prompt surface and shortcut-phrase registration (`docs/prompts/index.md`, `AGENTS.md` shortcut table via the normal render path).
- Worklist intake, batch-capped review procedure, three-disposition contract, evidence requirements, and pass-report format.
- Pointer updates in gardening/close/distill guidance surfaces (seeds + rendered prompts) referencing the loop as optional maintenance.
- Tests/fixtures for the prompt-surface contract where the framework tests prompt content (shortcut registration, required sections, disposition language present).

**Out of scope:**

- The verification stamp field itself, drift anchor semantics, gardener exclusion, drift computation, worklist generation, and retrieval annotation — all owned by `1ro43` (wave `1ro44`).
- Any blocking lifecycle gate on doc verification (explicitly deferred; revisit only with operator direction after the loop has usage history).
- Automated/scheduled verification runs; the loop is operator- or agent-invoked.
- LLM execution inside the MCP server; server tools remain mechanical.
- Bulk initial verification of the whole docs tree (the worklist is severity-ordered precisely so verification is incremental).
- Historical wave documents (`docs/waves/` records and change docs): frozen archives are never verified, amended, or marked stale for decay reasons — `1ro43` excludes them from the worklist by construction (annotation-only historical class), so they never reach this loop.

## Acceptance Criteria

- [ ] AC-1: A **Verify docs** shortcut phrase exists end to end: canonical seed, rendered `docs/prompts/verify-docs.prompt.md`, and a row in `docs/prompts/index.md`; the rendered surface defines worklist intake, the read-the-code requirement, all three dispositions, and evidence requirements.
- [ ] AC-2: The prompt surface consumes the `1ro43` drift worklist severity-ordered and caps a single pass at a named batch size (constant with rationale in the prompt), not an exhaustive sweep.
- [ ] AC-3: The verified disposition writes a commit-SHA verification stamp and the prompt explicitly prohibits stamping without reading the referenced code; the amend and stale dispositions route through the normal docs gate and existing supersession conventions respectively.
- [ ] AC-4: Each pass produces a report with reviewed count, dispositions by type, per-doc evidence, and remaining worklist depth; the report location decision is recorded in the Decision Log.
- [ ] AC-5: Gardening/close/distill guidance surfaces reference the loop as optional maintenance; no lifecycle transition gains a blocking dependency on doc verification (verified by reading the touched seeds/prompts — no gate language added).
- [ ] AC-6: Prompt-surface content tests cover shortcut registration and the presence of the disposition/evidence contract; full framework tests run bytecode-free and docs validation passes.

## Tasks

- [ ] Author the canonical verify-docs seed (open/close `seed_edit_allowed` around the edit) and render `docs/prompts/verify-docs.prompt.md` through the normal render path.
- [ ] Register the shortcut phrase in `docs/prompts/index.md` and the `AGENTS.md` shortcut table via the render pipeline.
- [ ] Define the pass-report format and location; record the decision in the Decision Log.
- [ ] Add optional-maintenance pointers in gardening/close/distill seeds and rendered surfaces (gate `seed_edit_allowed` as above; no gate language).
- [ ] Add prompt-surface content tests (registration, sections, disposition/evidence contract).
- [ ] Run a first live pass on this repository's actual drift worklist; capture the pass report as fixture evidence.
- [ ] Run `python3 .wavefoundry/framework/scripts/run_tests.py` and `wf_validate_docs`.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| prompt-surface | implementer | — | Seed + rendered prompt + shortcut registration |
| guidance-pointers | implementer | prompt-surface | Gardening/close/distill optional-maintenance pointers |
| first-pass-evidence | qa-reviewer | prompt-surface | Live pass on this repo's worklist; fixture report |
| tests-docs | qa-reviewer | all implementation streams | Content tests, validation, suite |


## Serialization Points

- Hard dependency: `1ro43-enh churn-aware-retrieval-decay` (wave `1ro44`) must land first — this change consumes its drift worklist and writes its stamp field; do not admit this change to a wave before `1ro44` closes.
- Prompt-surface maintenance: intended edits are the new verify-docs seed + rendered prompt, `docs/prompts/index.md`, the `AGENTS.md` shortcut table (render-owned), and pointer edits in gardening/close/distill seeds. Seed edits require the `seed_edit_allowed` gate opened and closed around each edit. All other surfaces are read-only for this change.
- Seeds must not cite wavefoundry-internal change/wave IDs; rationale for the loop is stated inline in the seed text.

## Affected Architecture Docs

- `docs/architecture/search-architecture.md` — close the decay loop description: mechanical propose (1ro43) + agentic dispose (this change).
- `docs/architecture/data-and-control-flow.md` — Verify docs flow: worklist → review → disposition write-backs.
- N/A for layering/testing beyond the above: the change is a prompt-surface workflow over existing tools, with no new server code paths.

## AC Priority

(Proposed; confirmed at Prepare wave.)


| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The prompt surface is the deliverable; without it there is no agentic tier. |
| AC-2 | required | Severity-ordered, batch-capped intake is what keeps the loop usable instead of abandoned. |
| AC-3 | required | Disposition write-backs with the no-blind-stamping rule are the integrity contract of the whole decay system. |
| AC-4 | important | Pass reports make the loop auditable, but a first version without perfect reporting still disposes drift. |
| AC-5 | required | Non-gating integration is an explicit operator decision; accidental gate language would change lifecycle behavior. |
| AC-6 | required | Standard verification gate plus the only automated protection the prompt contract has. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-04 | Drafted from operator direction during wave `1ro44` planning: the agentic review tier is written up separately for a future wave; the mechanical tier (drift anchor, stamp field, gardener exclusion, worklist) stays in `1ro43`. | Discussion in `1ro43` Decision Log (two-tier decay); `docs_gardener.py` `refresh_last_verified` mechanical stamping. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-04 | Ship the agentic tier as a prompt-surface workflow in a future wave, decoupled from the mechanical tier in wave `1ro44`. | The mechanical tier delivers annotation value on its own and defines the stamp/worklist contracts this loop consumes; sequencing them lets the census (`1ro43` AC-8) and real drift data shape the review procedure before it ships. | **Bundle both tiers in wave `1ro44`:** weakness — grows an already two-change wave with seed-gated prompt work that has a hard data dependency on the tier it would ship beside. **Server-side LLM evaluation of doc applicability:** weakness — violates the mechanical-tools boundary, adds model cost and nondeterminism to builds, and duplicates what a prompted agent does better with full context. |
| 2026-07-04 | Verification is optional maintenance, never a lifecycle gate, in this change. | A new mandatory gate on doc freshness would hold waves hostage to documentation review before the loop has any usage history; tightening later is cheap, loosening a shipped gate is not. | **Blocking gate at close-wave:** weakness — converts a quality signal into a tax before its precision is known. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| The loop ships but goes unused, so drift flags still accumulate | Severity-ordered, batch-capped passes keep single sessions cheap; optional-maintenance pointers put it in existing gardening/close flows; the first-pass fixture proves the loop on real data before close. |
| Agents blind-stamp to clear the worklist | Explicit prohibition in the prompt, mandatory per-doc evidence in the pass report, and stamps re-enter the worklist as post-stamp churn accumulates — a bad stamp is self-correcting, not permanent. |
| Disposition language drifts across seeds and rendered prompts | Single canonical seed owns the contract; content tests assert the disposition/evidence sections exist in the rendered surface. |
| Amend dispositions balloon into large doc rewrites mid-pass | The prompt scopes amend to matching current code for the flagged references; larger rewrites route to Plan feature as ordinary doc changes. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
