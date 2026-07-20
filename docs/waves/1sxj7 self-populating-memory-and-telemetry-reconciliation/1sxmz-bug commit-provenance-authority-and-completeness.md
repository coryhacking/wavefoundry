# Commit provenance authority and completeness

Change ID: `1sxmz-bug commit-provenance-authority-and-completeness`
Change Status: `implemented`
Owner: framework
Status: implemented
Last verified: 2026-07-18
Wave: `1sxj7 self-populating-memory-and-telemetry-reconciliation`

## Rationale

The retrospective review of closed wave `1sufq` proved that the reverse
provenance tool can fabricate ownership and overstate completeness:

- a real blamed line from `context_efficiency.py` resolves to both its actual
  landing wave (`1stwj`) and `1sufq`, solely because the later wave mentions the
  SHA as review evidence;
- the per-commit conflict is lost at the line-response envelope;
- mixed committed/uncommitted ranges silently discard uncommitted coverage;
- every Decision Log in a resolved wave is returned without proving relevance
  to the blamed file; and
- quoted/reverted landing text, malformed SHAs, and dual input modes fail open.

These violate the original required ACs for honest association, conflict,
absence, line completeness, and relevant reasoning. The repair stays local,
read-only, and bounded to the existing tool.

## Requirements

1. **Authoritative commit identity.** Canonicalize a syntactically valid SHA
   through local git and refuse evidence ownership for a commit that does not
   exist. Preserve the requested precision only after it resolves uniquely.
2. **Typed landing association only.** Evidence reverse-search recognizes only
   an explicit landing-commit association in the wave record/ledger. An
   arbitrary SHA mention, fixture value, comparison, or generic digest never
   authorizes ownership. Do not broadly scan `events.jsonl` for hex tokens.
3. **Anchored landing-message grammar.** Commit-message resolution reads the
   subject and accepts only an anchored `Land wave …` / `Land waves …` form
   followed by the approved wave-ID list. Reverted/quoted text and descriptive
   prose cannot add wave IDs.
4. **Exact public input mode.** The MCP response accepts exactly one of commit
   or path+range. Malformed SHAs, dual modes, invalid ranges, and missing paths
   return `invalid_arguments`, not `honest_absence`.
5. **Complete line coverage.** Line/range blame preserves committed,
   uncommitted, and unresolvable coverage. Mixed results are labeled `partial`.
   Any contributing commit conflict propagates to top-level
   `resolution: conflict` with a diagnostic.
6. **Relevant reasoning contract.** Provenance rows carry a structured
   `change_id`, change-doc pointer, relevant Decision Log rows, and the relevant
   Rationale excerpt. Line-mode filtering uses explicit path/symbol anchors;
   when relevance cannot be proved, the response labels the row as broad
   wave-level context rather than claiming file relevance.
7. **Honest telemetry credit.** Context-avoided accounting credits only the
   content-bearing reasoning actually surfaced after relevance filtering.
8. **Regression coverage.** Add public-path and hermetic fixtures for the exact
   retrospective reproductions, plus clean controls for conventional landing,
   non-conventional explicit evidence, rename blame, traversal refusal, and
   read-only behavior.

## Scope

**Problem statement:** `code_commit_provenance` treats generic textual
co-occurrence as ownership and loses completeness/relevance information, so it
can confidently answer the wrong “why is this line here?” question.

**In scope:**

- `.wavefoundry/framework/scripts/commit_provenance.py` — commit
  canonicalization, typed evidence association, anchored subject parser,
  complete blame coverage, structured/relevant reasoning rows.
- `.wavefoundry/framework/scripts/server_impl.py` — exact-one input validation,
  partial/conflict diagnostics, response and telemetry-source shaping.
- `.wavefoundry/framework/scripts/tests/test_commit_provenance.py` — the live
  false-owner case reproduced hermetically and the complete edge matrix.
- `docs/specs/mcp-tool-surface.md` and the provenance reference/docstring —
  response states and relevance semantics.

**Out of scope:**

- Network/hosted provenance or a new authoritative provenance database.
- Per-line reasoning storage or a full history browser.
- Security hardening beyond the already-valid local argv/path containment.

## Acceptance Criteria

- [x] AC-1: Generic SHA prose, nonexistent SHAs, and prefix collisions cannot
  resolve a wave; explicit typed landing evidence and conventional landing
  subjects still resolve. (required)
- [x] AC-2: Reverted/quoted/descriptive commit subjects cannot fabricate or
  overcapture wave IDs. (required)
- [x] AC-3: The public tool enforces exactly one valid input mode and returns
  typed invalid-argument diagnostics. (required)
- [x] AC-4: Mixed committed/uncommitted ranges report partial coverage and any
  per-commit conflict reaches the top-level response. (required)
- [x] AC-5: Line provenance returns structured change IDs and only
  file-relevant reasoning as relevant; broad fallbacks are explicitly labeled.
  (required)
- [x] AC-6: Context-avoided source credit includes only reasoning actually
  surfaced after the relevance decision. (important)
- [x] AC-7: Existing local-only, read-only, traversal, rename, absence, and
  conflict controls remain green. (required)
- [x] AC-8: Focused and full framework suites pass; docs-lint is clean.
  (required)

## Tasks

- [x] Replace loose SHA-text ownership with canonical commit + typed landing
  association.
- [x] Anchor the commit-subject grammar and enforce the public input union.
- [x] Preserve blame coverage and aggregate partial/conflict state.
- [x] Parse structured change identity/rationale and filter reasoning by
  explicit file/symbol anchors.
- [x] Update telemetry source extraction, docs, and regression fixtures.
- [x] Run focused tests, full suite, docs-lint, and live public-path controls.

## Agent Execution Graph


| Workstream     | Owner  | Depends On   | Notes |
| -------------- | ------ | ------------ | ----- |
| resolver | framework | — | association, message grammar, blame coverage |
| response | framework | resolver | validation, relevance, telemetry shaping |
| verify | QA | response | retrospective repros + clean controls |


## Serialization Points

- `commit_provenance.py` and `server_impl.py` are shared framework files; edit
  under `framework_edit_allowed`.
- The response schema and telemetry source extractor change together.

## Affected Architecture Docs

`docs/specs/mcp-tool-surface.md` and the provenance reference are updated.
Architecture hubs remain unchanged: this repairs a read-only tool contract
without moving a boundary.

## AC Priority

(Populated at Prepare wave.)


| AC   | Priority                                             | Rationale |
| ---- | ---------------------------------------------------- | --------- |
| AC-1 | required | Ownership must be authoritative |
| AC-2 | required | Landing grammar cannot fabricate ownership |
| AC-3 | required | Public input contract must fail closed |
| AC-4 | required | Line-range completeness/conflict honesty |
| AC-5 | required | Core reasoning relevance contract |
| AC-6 | important | Do not credit content the tool did not use |
| AC-7 | required | Preserve verified safety/correctness controls |
| AC-8 | required | No regression |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-18 | Retrospective review admitted four root findings into 1sxj7 | `1sufq/events.jsonl`; live `context_efficiency.py:1` false-owner probe |
| 2026-07-18 | Implemented canonical commit identity, typed landing evidence, anchored subject parsing, complete blame coverage, relevance labels, and exact public input validation | `commit_provenance.py`; `server_impl.py`; 23 provenance tests |
| 2026-07-18 | Re-ran the original false-owner probe against the live repository | `context_efficiency.py:1` resolves only `1stwj`; committed coverage 1, uncommitted 0, no conflict |
| 2026-07-18 | Verified focused, integration, and full-suite behavior | 188 focused memory/context/provenance tests; 362 setup/upgrade/server-context tests; canonical suite 5,832 OK; docs-lint clean |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-18 | Repair in the current wave, but keep provenance as a separate change | Shared release boundary; distinct code/tests from memory telemetry | Reopen closed 1sufq (rejected — history remains closed and findings are linked) |
| 2026-07-18 | Evidence ownership requires a typed landing association | Generic SHA co-occurrence is not provenance | Scan more prose/events (rejected — increases false authority) |
| 2026-07-18 | Top-level conflict takes precedence over partial coverage while retaining both diagnostics | A conflicting committed contributor is more actionable than an otherwise partial range; coverage must still remain visible | Collapse to one condition (rejected — loses evidence) |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Existing non-conventional landing records lack a typed marker | Preserve honest absence or add an explicit supported legacy marker; never guess from prose |
| Relevance filtering omits useful broad context | Return it as labeled wave-level context, not as file-relevant reasoning |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
