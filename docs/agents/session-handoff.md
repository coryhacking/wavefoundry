# Session Handoff

Owner: Engineering
Status: active
Last verified: 2026-07-12

## Current State

**1.12.0 RELEASED** (2026-07-11, GitHub tag `v1.12.0`, artifact `wavefoundry-1.12.0.pblj.zip`) — bundles waves `1rsh9` (SQLite substrate + FTS5 hybrid lexical + scan cache + Tantivy retirement), `1sbfi` (external-supertype visibility), and `1sbfk` (chunk-index backfill repair + `code_lexical` tool + lexical-fusion guidance). Landing commit `5313af5b`, version bump `fce67748`, main in sync with origin. Field-verified pre-release on two downstream repos; post-release `code_lexical` smoke batteries 8/8 on both.

**Uncommitted (operator-directed, post-release):** a small guidance addition to seed-211 + rendered `docs/agents/guru.md` — "multi-identifier `code_lexical` queries surface summary chunks first (BM25 length normalization); follow through with `code_read`", from the field smoke report. **Stage-gate waiver:** operator explicitly directed this docs/seed prose edit outside a wave (2026-07-12, "make that guidance to the guru now"); no behavioral code touched; docs-lint clean. Include in the next commit.

## Review-Derived Waves (READIED 2026-07-12, external code review — all claims source-validated)

Three waves stood up from the validated 2026-07-12 external code review; all READIED (council-passed), none OPEN:

1. **`1seav search-freshness-degraded-retrieval`** — `1sbxq` (code_ask freshness: per-call O(corpus) walk removed, three honest states incl. `unknown`, build-invalidated cache) + `1seaq` (FTS-first degraded fallback for code_search/docs_search with preserved filters, live walk demoted to store-absent-only, typed `search_mode`/`fallback_reason` contract). Highest value; 1.12.1 fold candidate with `1sbfl`.
2. **`1seaw retrieval-intent-golden-queries`** — `1sear` (standing golden-query eval suite: 8 classes, verbatim misranked queries, baseline + tolerance) then `1seas` (classifier artifact-anchoring, assessment intent, low-information-path penalty) BLOCKED on the recorded baseline. Ranking changes are eval-gated, period.
3. **`1seax lifecycle-ops-hardening`** — `1seat` (advisory lifecycle-mutation lock, forward-recoverability audit + idempotent-retry fixtures, selective subprocess bounds; the review's transaction-journal proposal REJECTED as disproportionate, recorded with escalation path) + `1seau` (RELIABILITY/performance-budget evidence-based rewrite + docs-vs-code-constants lint).

Review findings NOT adopted: correlation IDs, blanket subprocess deadlines, transaction journal/rollback (all recorded with rationale in the change docs). CI adoption = separate operator infra decision (the eval suite is CI-invocable by design).

## Next Steps

1. **Wave `1sek8` (content-scoped builds poison code-index freshness)** — the priority fast-follow. Plan doc at `docs/plans/1sek8-…` with full evidence: broad meta stamping erases the other content type's change signal; the post-edit hook's bare spawn defaults to docs-content (code indexes frozen at last full build fleet-wide); `content=all` vs `content=code` corpus divergence. Needs a design pass first — the three defects interact. Interim field recovery documented in `build-and-verification.md` (rechunk, not a plain code update).
2. **Wave `1ro44` (agent memory + churn decay)** — readied and unblocked.
3. **`1sbfl` (Java static-initializer chunker gap)** — needs a `CHUNKER_VERSION` bump; batch with other chunker work.

## Follow-ups recorded (not blocking)

- Retire the `1rycf` close-time bloat gate once field data confirms (Tantivy leak source removed by 1rsh9/1sauc).
- Tier 2 rule-delta secret scanning (spike: partially viable).
- `meta.json` reader migration; graph build-path auto-maintenance (deferred per 1rq4h AC-7).
- Extraction-side: qualification-via-import-facts for unqualified external supertype declarations (census note in `1sbfh`).
- `wave_scan_secrets` files_scanned/files_skipped response passthrough (field-noted shape gap).
- Sub-token/camelCase FTS indexing: eval-gated consideration only (trades away the exact-identifier precision the tokenizer was chosen for; see quality-log memory).
- Intermittent test_indexer full-suite flake observed twice while concurrent live index builds ran on this machine; never reproduced quiescent (5× clean); no traceback captured — watch item.

## Session Notes

- The pre-edit hook fails when the shell cwd is inside `.wavefoundry/framework/scripts/` — `cd` back to repo root before Edit calls.
- Stale-code-navigation recovery on any repo until `1sek8` lands: `indexer.py --content code --rechunk` (a plain `content=code` update is a no-op on poisoned meta).

## Current Session

**Active wave:** *(none)*
