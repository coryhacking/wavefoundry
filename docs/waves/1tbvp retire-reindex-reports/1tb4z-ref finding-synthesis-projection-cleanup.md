# Finding Synthesis Projection Cleanup (Plain Summary, wave- Class)

Change ID: `1tb4z-ref finding-synthesis-projection-cleanup`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-07-22
Wave: `1tbvp retire-reindex-reports`

## Rationale

Operator observations during the 1tbvp review: (a) the projection's `<details class="wavefoundry-review-evidence">` class does not match the `wave:` marker vocabulary, and (b) the block is HTML in a human-readable document. Investigation confirmed the HTML earned its keep only on the LEGACY inline-authority path, where `<details>` collapses an embedded ` ```jsonl ` fence of full machine records in rendered views; on the external-ledger path every current wave uses (records in `events.jsonl` since 1slep), the renderer emits the same wrapper around nothing but the one-line summary — a vestige. A third option considered and rejected: mirroring `wave:context-efficiency-state`'s JSON comment. CE embeds JSON because wave.md IS its durable per-wave record; review evidence's machine authority is the sibling `events.jsonl`, structured counts are already served by `wf_review_evidence`/`wf_review_wave`, and a census found nothing parsing the summary prose — a JSON duplicate would add a second machine encoding with its own staleness obligation.

## Requirements

1. **External-ledger projections drop the HTML.** `render_review_evidence_projection` and `empty_external_finding_synthesis_section` emit the summary as a plain italic markdown line (`*<summary text>*`) instead of a `<details>` wrapper. The human table and the `wave:finding-synthesis` markers are unchanged.
2. **Legacy inline-authority projections keep `<details>`** (they collapse a real JSONL body) **with the class renamed** to `wave-review-evidence`, matching the marker vocabulary (`empty_finding_synthesis_section` and the inline renderer).
3. **History is never rewritten:** `canonicalize_finding_synthesis_markers` (the existing legacy-namespace seam) additionally normalizes (a) the legacy `wavefoundry-review-evidence` class to the new spelling and (b) a BODYLESS details block (either class) to the plain summary line, so the stale-projection comparison passes on closed-wave archives as-is. Bodied (inline JSONL) details blocks are never collapsed. Active waves converge to the new form on their next projection rebuild.
4. **No JSON state comment is added** (decision recorded above); consumers needing counts read `events.jsonl` or the tool envelopes.
5. **Tests updated:** the projection-form assertions (`test_server_tools.py`, `test_dashboard_server.py` fixture) pin the new forms; a canonicalization test proves a legacy-form archive still validates as fresh; the docs-lint legacy fixture stays as legacy-acceptance coverage.

## Scope

**Problem statement:** the external-ledger projection carries a vestigial HTML wrapper with an off-vocabulary class name in a human-first document.

**In scope:**

- `review_evidence.py`: the four render sites, the details constants, and the canonicalizer
- Projection-form test assertions and a legacy-acceptance regression
- Regeneration of active-wave projections (next ledger write; no manual sweep needed)

**Out of scope:**

- Rewriting closed-wave archives (canonicalization covers validation)
- Any JSON machine-state comment in wave.md (rejected; see Rationale)
- Dashboard STYLING (censused: no CSS rule or JS parser touches the class or summary prose). The dashboard's projection-FRESHNESS comparison turned out to be in scope — see the Progress Log.

## Acceptance Criteria

- [x] AC-1: a rendered external-ledger projection contains the plain italic summary line and NO `<details>`/`<summary>`/class markup; the empty-scaffold form matches.
- [x] AC-2: the legacy inline renderer emits `wave-review-evidence` and still wraps its JSONL body in `<details>`; a bodyless legacy-form projection (old class, details-wrapped summary) validates as fresh through canonicalization without the file changing on disk.
- [x] AC-3: docs gate and full framework suite green; the active wave's projection converges to the new form on its next ledger write.

## Tasks

- [x] Renderer + constants + canonicalizer changes with tests.
- [x] Update projection-form assertions and fixtures; add the legacy-acceptance regression.
- [x] Docs gate; full suite; verify live convergence on this wave's own projection.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| renderer | implementer | — | review_evidence.py + tests |

## Serialization Points

- None beyond the single-file renderer edit; the live-convergence check runs after the next ledger write on the host wave.

## Affected Architecture Docs

N/A — presentation form of a generated projection; the projection contract (markers, human table, events.jsonl authority) is unchanged.

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The cleanup itself. |
| AC-2 | required | History must keep validating without rewrites. |
| AC-3 | required | Standard gates + live convergence proof. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-22 | Drafted from the operator's two review-time observations plus the JSON-state question; renderer paths and consumers censused (4 render sites; no CSS/parser consumers of class or summary prose; canonicalizer precedent at `_canonicalize_finding_synthesis_markers`). | Session investigation |
| 2026-07-22 | Implemented: external-ledger render sites emit `*<summary>*` plain line (`review_evidence_plain_summary`); inline sites keep `<details>` with class `wave-review-evidence`; canonicalizer collapses bodyless details blocks (either class spelling) to the plain line and normalizes the legacy class on bodied blocks. Four regressions added (plain-form render, legacy bodyless-form freshness equality, bodied-inline non-collapse, class normalization); `test_review_evidence` 92 OK. Live convergence verified on this wave's own projection at the next ledger write; docs gate clean over all old-form archives with zero rewrites. | `review_evidence.py` diff; module run; `wf_validate_docs` ok; wave.md projection |
| 2026-07-22 | Full-suite run live-caught a consumer my census missed: the DASHBOARD computes projection freshness itself (`dashboard_lib.py` `_review_evidence_dashboard_state`) and compared the canonical-form render against RAW on-disk text, so every old-form archive would have shown `stale` on the dashboard. Fixed by comparing against `canonicalize_finding_synthesis_markers(text)` — the identical seam the lint path uses; the dashboard test's old-form fixture now doubles as the legacy-shows-current regression. Scope note corrected: "no dashboard changes" was true for styling/parsing, wrong for the freshness comparison. | `tests/test_dashboard_server.py` `test_review_evidence_projection_is_derived_from_external_ledger`; module 188 OK |
| 2026-07-22 | Full suite green with everything included: 6,147 tests across 59 files OK in a single run (P2 over-cap regression, projection-cleanup regressions, dashboard canonical-comparison fix). AC-1 through AC-3 met. | Suite output |
| 2026-07-22 | Third operator review P1 (`lifecycle-upgrade-miss-canonicalization`): TWO more raw-text projection comparisons the consumer census missed — the lifecycle diagnostics (`_review_evidence_diagnostics`) flagged closed old-form archives stale (reproduced on 1slep), and the upgrade's `phase_review_status_projection` REWROTE a byte-for-byte archive copy (projected 1). With 26 legacy-class archives this was supported existing state. Repair: both comparisons now run through `canonicalize_finding_synthesis_markers` (the identical seam as lint and dashboard); two regressions added per the operator's shape — old-form archive yields no stale lifecycle diagnostic (with a tampered-content counter-case proving real staleness still detects) and the upgrade byte-preserves the old-form archive with projected 0. Consumer census now totals SIX comparison sites: lint, dashboard, lifecycle diagnostics, upgrade projector, plus the two renderers. | `events.jsonl` finding chain; `test_legacy_form_projection_yields_no_stale_lifecycle_diagnostic`; `test_legacy_form_external_archive_is_byte_preserved` |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-22 | Plain markdown summary line on the external path; details retained only where it collapses a real JSONL body. | The HTML's collapse purpose left with the records when 1slep externalized them; a human-first document should not carry markup that wraps nothing. | Keeping details everywhere with only a class rename (keeps the vestige); JSON state comment (rejected — events.jsonl is the authority, nothing parses the prose, and CE's JSON exists because wave.md IS its store). |
| 2026-07-22 | Normalize legacy forms in the canonicalizer; never rewrite archives. | Same pattern as the legacy `waveframework:` marker namespace and the `## Journal Watchpoints` heading acceptance. | One-time archive rewrite sweep (touches closed history for a presentation change). |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| The canonicalizer's bodyless-details collapse accidentally matches a bodied inline block. | The collapse pattern requires `</summary>` immediately followed by `</details>` (whitespace only); the inline form always has a ```jsonl fence between them; regression covers both. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
