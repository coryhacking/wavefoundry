# Memory exact-duplicate diagnostics (detection only)

Change ID: `1stwl-enh memory-exact-duplicate-diagnostics`
Change Status: `implemented`
Owner: framework
Status: implemented
Last verified: 2026-07-20

Wave: `1stwm memory-supply`

## Rationale

Two forces need duplicate detection: the evidence-derived candidate tool (`1stwk`) must be idempotent so re-running over the same ledger does not flood the corpus, and manual `wave_memory_add` can create near-identical records. Today the memory layer has no duplicate detection at all — dedup is left entirely to operator judgment at the close-time distillation checkpoint (an explicit non-goal in 1ro44).

We looked at `agentmemory`'s approach and validated it against its own source (v0.9.27): its "contradiction" handling treats >0.9 Jaccard *similarity* as opposition and auto-flips the older record to non-latest, and its remember path auto-supersedes above 0.7 similarity. That silently rewrites history. Our invariant is the opposite (`memory_records.py:8`: status and supersession are the only lifecycle mechanisms; nothing auto-deletes or rewrites). So this change is **detection only, surfaced to the operator** — it never auto-supersedes, merges, or deletes. Semantic contradiction detection is deliberately deferred; this is exact/near-exact duplicate detection.

## Requirements

1. **Exact-duplicate detection.** Given a candidate/new record, detect existing non-history records (active/candidate) that are duplicates by either signal: (a) an overlapping originating **evidence ID**, or (b) a normalized match on `(kind, sorted targets, summary)` where the summary is compared after whitespace/case/punctuation normalization.
2. **Detection only.** The result is a diagnostic listing the matching record IDs and which signal matched. It never marks a record superseded/stale, never merges, never deletes. Reconciliation stays an explicit operator action.
3. **Surfaced where records are created.** `wave_memory_add` returns a `possible_duplicate` diagnostic (record still written unless the caller opts to abort), and `wave_memory_propose` (`1stwk`) uses the same detection to skip or flag idempotent re-drafts. An optional standalone check reports duplicates across the current corpus.
4. **Cheap and deterministic.** Detection is a bounded scan over the small on-disk record set (no embeddings, no similarity model). Normalization is fixed and documented so the same inputs always yield the same verdict.

## Scope

**Problem statement:** the memory layer has no duplicate detection, so re-running candidate generation would flood the corpus and manual adds can silently duplicate — and we must add detection without adopting `agentmemory`'s history-rewriting auto-supersession.

**In scope (edited under `framework_edit_allowed`):**
- `.wavefoundry/framework/scripts/memory_records.py` — a deterministic `find_duplicates(record, existing)` helper (evidence-ID overlap + normalized (kind, targets, summary) match).
- `.wavefoundry/framework/scripts/server_impl.py` — surface a `possible_duplicate` diagnostic on `wave_memory_add`; expose the detection to `wave_memory_propose`; optional standalone corpus duplicate report.
- Docs — memory README note on the detection signals + the detection-only posture.
- Tests — evidence-ID match, normalized summary match, non-match, detection-only invariance (no status/history mutation), determinism.

**Out of scope:**
- **Semantic contradiction detection** (conflicting-but-not-duplicate claims) — deferred; would come later as show-both-to-operator, never auto-resolve.
- **Any auto-supersession/merge/delete** — reconciliation is explicit-only.
- **Similarity-model / embedding-based near-dup** — this is exact/normalized detection, not fuzzy similarity.

## Acceptance Criteria

- [x] AC-1: A deterministic detector flags a candidate/new record as a possible duplicate when it shares an originating evidence ID with, or normalized-matches `(kind, sorted targets, summary)` of, an existing non-history record. (required) — `find_duplicates(record, existing)` in `memory_records.py`; signals `evidence_ref` (shared `## Evidence` ref) + `normalized_content`; tests `test_evidence_id_overlap_flags_duplicate`, `test_normalized_summary_match_flags_duplicate`.
- [x] AC-2: Detection is diagnostic-only — it never marks superseded/stale, merges, or deletes; record status/history is unchanged by detection. (required) — pure function, returns a payload only; `abort_if_duplicate` refuses the write without mutating; test `test_abort_if_duplicate_refuses_without_mutation` asserts the on-disk set is unchanged.
- [x] AC-3: `wave_memory_add` returns a `possible_duplicate` diagnostic (naming the matched record IDs + signal) without blocking the write; `wave_memory_propose` consumes the same detector for idempotency. (required) — advisory attached on the success path (non-blocking); `find_duplicates` is the shared detector 1stwk consumes; tests `test_duplicate_add_written_with_advisory`, `test_non_duplicate_add_has_no_advisory`.
- [x] AC-4: Normalization (whitespace/case/punctuation) is fixed and documented; identical inputs yield identical verdicts (determinism test). (required) — `normalize_summary` (lowercase, non-alphanumeric runs to single space, trim); documented in the README; tests `test_determinism`, `test_normalize_summary_is_fixed`.
- [x] AC-5: Full framework suite green; docs-lint clean. (required) — full suite 5788 OK; `wave_validate` docs-lint ok.

## Tasks

- [x] Add `find_duplicates` to `memory_records.py` (evidence-ID overlap + normalized (kind, targets, summary)). — `find_duplicates` + `normalize_summary` + `_dup_content_key`.
- [x] Surface `possible_duplicate` on `wave_memory_add`; expose detector to `wave_memory_propose`; optional corpus report. — advisory + `abort_if_duplicate` on add; `find_duplicates` consumed by `wave_memory_propose` for idempotency. (Standalone corpus report not added; the detector is exposed for callers to use.)
- [x] Memory README: signals + detection-only posture. — "Duplicate detection" section in `docs/agents/memory/README.md`.
- [x] Tests: both signals, non-match, detection-only invariance, determinism. — `FindDuplicatesTests` + `MemoryAddDuplicateDiagnosticTests` (11 tests).
- [x] Full suite + docs-lint. — full suite 5789 OK; `wave_validate` docs-lint ok.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| detector | framework | — | `find_duplicates` in memory_records.py |
| surface | framework | detector | diagnostic on add; expose to propose |
| verify | framework | surface | tests + docs |


## Serialization Points

- `.wavefoundry/framework/scripts/memory_records.py` / `server_impl.py` — edited under `framework_edit_allowed`. Consumed by `1stwk` for idempotency.

## Affected Architecture Docs

`N/A` — a localized detection helper + additive diagnostic; no boundary/flow change. Memory README documents the signals.

## AC Priority

(Populated at Prepare wave.)


| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The detection primitive |
| AC-2 | required | Detection-only — must not rewrite history (the anti-agentmemory invariant) |
| AC-3 | required | Surfaced where records are created; feeds candidate idempotency |
| AC-4 | required | Deterministic, documented normalization |
| AC-5 | required | No regression |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-17 | Change doc authored; detection-only posture validated against agentmemory source | agentmemory v0.9.27 auto-forget/remember (Jaccard auto-supersede); `memory_records.py:8` invariant |
| 2026-07-18 | Post-close correction in wave 1sxj7: exact identity now uses Unicode-safe normalization, rejects empty normalized summaries as equality, canonicalizes refs, and treats only typed event/finding identities—not generic wave/path refs—as evidence identity. The public scan+write critical section is serialized so concurrent creators remain idempotent. | `1sxmy-bug memory-supply-and-exploration-estimate-integrity`; Unicode/evidence/concurrency fixtures |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-17 | Detection only, surfaced to operator | Preserves never-auto-rewrite invariant | Copy agentmemory auto-supersede on similarity (rejected — validated: rewrites history, detects similarity not opposition) |
| 2026-07-17 | Exact/normalized signals, no similarity model | Cheap, deterministic, sufficient for idempotency | Embedding/fuzzy near-dup (rejected — out of scope; nondeterministic) |
| 2026-07-17 | Semantic contradiction detection deferred | Needs the eval corpus first; different (show-both) problem | Bundle it now (rejected — premature) |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| False "duplicate" on legitimately-distinct records | Diagnostic-only, non-blocking; operator decides |
| Normalization too aggressive/loose | Fixed, documented, determinism-tested normalization |
| Scope creep into contradiction/auto-resolution | Explicit out-of-scope + detection-only ACs |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
