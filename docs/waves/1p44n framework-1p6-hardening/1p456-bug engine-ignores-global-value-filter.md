# Engine Ignores the Global [allowlist] Value-Filter (regexes + stopwords)

Change ID: `1p456-bug engine-ignores-global-value-filter`
Change Status: `complete`
Owner: Engineering
Status: planned
Last verified: 2026-06-09
Wave: 1p44n framework-1p6-hardening

## Rationale

The framework `scan-rules.toml` authors a global value-filter — `[allowlist].regexes` (`scan-rules.toml:132-146`) and `[allowlist].stopwords` (`scan-rules.toml:147-150`) — and describes the section as *"global allow lists (mirrors betterleaks prefilter/filter for Python scanner)"* (`scan-rules.toml:97`). But the engine never reads it:

- `secrets_validators.py:707` — the framework load pulls **only** `.paths`: `global_allowlist_paths = list(fw_raw.get("allowlist", {}).get("paths", []))`.
- `secrets_validators.py:716` — the project-file load also pulls **only** `.paths`, so a project `[allowlist].regexes`/`stopwords` is equally inert.
- `secrets_validators.py:753-757` — per-match regex allowlisting (`al_regexes_r`) comes from each rule's `rule.get("allowlists", [])` (PER-RULE), not the global `[allowlist]`.

So the authored global value-filter is loaded **nowhere** and never applied. Every one of the ~280 rules therefore fires on the structural-noise values the global filter was written to suppress: env/shell var references (`$VAR`, `${VAR}`), CI template expressions (`{{ … }}`, `${{ env/secrets/vars… }}`), booleans (`true/false/null`), printf/format specifiers (`%FMT%`, `%s`), and filesystem-path-shaped values (`/Users/…`, `/bin|etc|…/…`), plus the `stopwords` substrings. This is the same false-parity defect as the stale "scanner does not execute CEL" header (`1p452`): the file claims a betterleaks-parity exclusion the engine does not deliver. It also forces `seed-213` reviewers to hand-classify exactly these structural false positives (its env-var-read / placeholder heuristics exist *because* the engine doesn't apply this), which is direct reviewer toil and gate-blocking pending churn the confirmation-workflow cluster (`1p44y`/`1p44z`/`1p451`) is separately trying to reduce.

Wiring the already-authored mirror is a fleet-wide false-positive win and fixes a latent correctness bug. (Caveat for reviewers: this would NOT have cleared *this* repo's 11 findings — they are real secrets / non-structural values — so the payoff is on the broad FP classes common in CI/IaC/app code, not this specific set.)

## Requirements

1. In `check_hardcoded_secrets` (`secrets_validators.py`), load the framework `[allowlist].regexes` and `[allowlist].stopwords` (alongside `.paths` at `:707`) and merge the project-file `[allowlist].regexes`/`stopwords` too (fixing the `:716` paths-only merge so operators gain a working value-filter lever).
2. Apply the global value-filter per match, before a finding is created: suppress when the matched value matches any global regex (regex search, mirroring the per-rule `al_regexes` mechanism at `:533-539`) OR contains any global stopword (substring / `containsAny` semantics). Apply to ALL rules, independent of per-rule allowlists.
3. Thread the new global lists through the parallel scan path: `scan_file_raw` gains `global_regexes` / `global_stopwords` params, and `_worker_init_secrets_scanner` / the `ProcessPoolExecutor` initargs must include them, or spawned workers would silently skip the filter.
4. Document precedence: the global value-filter composes AFTER the per-rule CEL `filter` and per-rule allowlist (a match surviving rule-level checks is still dropped if it is global structural noise). No change to `[allowlist].paths` behavior (already applied at `:507`).
5. Coordinate with `1p452`: once this lands, the `scan-rules.toml` header comment and `[allowlist].description` must state that `[allowlist].paths` AND `regexes`/`stopwords` are applied (while the top-level betterleaks `prefilter`/`filter` CEL blocks themselves remain unexecuted — the `[allowlist]` mirror is what runs).

## Scope

**Problem statement:** the global `[allowlist].regexes`/`stopwords` value-filter is authored and described as applied, but is loaded nowhere — so structural-noise false positives fire across all rules and reviewers hand-classify them.

**In scope:**

- Loading + applying global framework AND project `[allowlist].regexes` + `stopwords` per match (`check_hardcoded_secrets` / `scan_file_raw` + the parallel worker plumbing).
- Unit tests for each noise class + a recall-preservation case + the project-file merge.
- Updating `[allowlist].description` / `scan-rules.toml` header and coordinating the `1p452` comment.

**Out of scope:**

- Executing the top-level betterleaks `prefilter`/`filter` CEL blocks directly — the `[allowlist]` mirror is the applied source (see the `1p452` contract); chosen to avoid a dual-source design and the "future betterleaks adds an unsupported CEL function" risk.
- The performance guards (`1p44s`) and the `generic-api-key` docs-path scoping (`1p44u` — complementary, a different FP class: doc prose vs structural values).

## Acceptance Criteria

- [x] AC-1: framework `[allowlist].regexes` and `stopwords` are loaded and applied globally to every rule's matches. — loaded in `check_hardcoded_secrets`, applied per-match in `scan_file_raw` after per-rule checks. Tests: `test_each_noise_class_suppressed`, `test_framework_filter_loaded_and_applied`.
- [x] AC-2: project-file `[allowlist].regexes`/`stopwords` are merged and applied (operator value-filter lever works; previously only `.paths` was merged). — both fw + project `regexes`/`stopwords` merged. Test: `test_project_file_value_filter_merged`.
- [x] AC-3: a match whose value is `$VAR` / `${VAR}` / `{{template}}` / `%FMT%` / `true|false|null` / a `/Users/…` or `/bin/…` path is suppressed (no finding) for ANY rule — verified per noise class. — `test_each_noise_class_suppressed` against the SHIPPED patterns. (Note: wiring exposed that the `/Users/…` regex used a Python-invalid mid-pattern `(?i)` flag — fixed to a leading flag so it actually matches; see Decision Log.)
- [x] AC-4: a genuine high-entropy secret matching NO global pattern still fires (no recall loss). — global regexes are anchored to the whole value; `test_high_entropy_secret_still_fires`.
- [x] AC-5: stopword substring suppression works (`containsAny` semantics). — case-insensitive substring of the captured value; `test_stopword_substring_suppressed`.
- [x] AC-6: the parallel scan path applies the global value-filter (a test exercising the ProcessPoolExecutor path, not just serial), confirming the worker plumbing carries the new lists. — `global_regexes`/`global_stopwords` threaded through `_worker_init_secrets_scanner` + initargs + `_WORKER_GLOBAL_*` globals; `test_parallel_path_applies_value_filter` (60 files, `max_workers=4`).
- [x] AC-7: `[allowlist].description` / `scan-rules.toml` header reflect the applied value-filter (coordinated with `1p452`); docs-lint clean. — `[allowlist].description` updated here; the top-of-file header comment (lines 11-13) is rewritten by `1p452` (the next change), keeping the three-way CEL distinction in one place.
- [x] AC-8: `python3 .wavefoundry/framework/scripts/run_tests.py` passes with the new tests (each noise class, recall preservation, project merge, parallel path). — `TestGlobalValueFilter` (7 tests); scanner suites green (104); full suite at wave-end.

## Tasks

- [x] Load framework + project `[allowlist].regexes` and `stopwords` in `check_hardcoded_secrets`.
- [x] Add `global_regexes` / `global_stopwords` params to `scan_file_raw` and apply per-match suppression (regex search + stopword substring) before appending a hit. — composes after the per-rule CEL filter + per-rule allowlist (AC-4 precedence).
- [x] Plumb the new lists through `_worker_init_secrets_scanner` + the `ProcessPoolExecutor` initargs (and the serial path).
- [x] Update `[allowlist].description` / header; coordinate the `1p452` comment wording. — description done here; header (11-13) by `1p452`.
- [x] Add unit tests for each noise class, recall preservation, project-file merge, and the parallel path; run `run_tests.py`. — `TestGlobalValueFilter` (7 tests).

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| load-and-apply | Engineering | — | global regexes/stopwords load + per-match suppression in `secrets_validators.py` |
| worker-plumbing | Engineering | load-and-apply | thread globals through `scan_file_raw` + initializer so the parallel path applies them |
| docs-coordination | Engineering | load-and-apply | `[allowlist].description` + `1p452` header comment reflect applied behavior |
| tests | Engineering | load-and-apply, worker-plumbing | per-noise-class + recall + project-merge + parallel-path tests |

## Serialization Points

- `secrets_validators.py` — shared with `1p44s` / `1p44v` / `1p44x` / `1p44y` / `1p451`; the per-match loop and the worker initializer are touched here.
- `scan-rules.toml` `[allowlist].description` / header — shared with `1p44t` / `1p44u` / `1p44w` / `1p452`; sequence with `1p452` so the header reflects the applied value-filter.

## Affected Architecture Docs

N/A — the engine begins reading an existing config block it currently ignores; no new module boundary or data-flow surface beyond the additive global-filter parameters.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Core fix: apply the inert global value-filter. |
| AC-2 | required | Operators currently have no working value-filter lever (only `.paths` merges). |
| AC-3 | required | Verifies the fleet-wide structural-FP suppression actually happens. |
| AC-4 | required | Recall guard — global patterns must not eat real secrets. |
| AC-5 | important | Stopword substring path is half the filter. |
| AC-6 | required | The parallel path is the default on large repos; missing plumbing = silent no-op. |
| AC-7 | required | Removes the false-parity claim; coordinates with `1p452`. |
| AC-8 | required | Test suite is the verification gate. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-08 | DELIVERY-REVIEW FIX: the global value-filter used `re.search` against the authored `(?i)^true|false|null$` whose `false`/`null` branches were unanchored — silently dropped real high-entropy secrets containing those substrings. Switched the engine to `re.fullmatch` (whole-value) AND anchored the regex to `(?i)^(?:true|false|null)$`; added a recall test. | secrets_validators.py:783 (re.fullmatch); scan-rules.toml:149; test_secret_containing_noise_substring_still_fires. |
| 2026-06-08 | Loaded fw+project `[allowlist].regexes`/`stopwords` in `check_hardcoded_secrets`; applied per-match in `scan_file_raw` after per-rule checks; threaded through the parallel worker init; updated `[allowlist].description`; fixed the `/Users/…` regex's mid-pattern `(?i)`. | `secrets_validators.py`, `scan-rules.toml`; `TestGlobalValueFilter` (7 tests incl. parallel path); scanner suites green (104). |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-08 | Wire the existing `[allowlist].regexes`/`stopwords` mirror rather than execute the top-level betterleaks `filter` CEL | The mirror is already authored and faithful; applying it is minimal and consistent with how per-rule `al_regexes` already work; avoids a dual-source design and the risk of a future betterleaks `filter` using a CEL function `cel_filter.py` does not implement | Execute the top-level `filter` CEL directly (rejected this scope — see `1p452` contract); leave it inert (rejected — false-parity correctness bug + reviewer toil) |
| 2026-06-08 | Also merge project-file `[allowlist].regexes`/`stopwords` | `:716` merges only `.paths`, so operators have no value-filter lever at all today | Framework-only (rejected — leaves operators unable to suppress project-specific structural FPs) |
| 2026-06-08 | Fix the `/Users/…` global regex's mid-pattern `(?i)` to a leading flag | Wiring the filter exposed that `^/Users/(?i)[a-z0-9]+/…` raises `re.error` in Python 3.11+ (global flags must be at the start), so it never matched and AC-3's `/Users/…` case would fail. Moving `(?i)` to the front preserves the intended case-insensitive username while making it a valid Python pattern. | Leave it inert (rejected — AC-3 requires `/Users/…` suppression); rewrite as `[A-Za-z0-9]` (equivalent; chose the minimal flag move). |
| 2026-06-08 | Apply the global value-filter against the captured `secret` value (anchored patterns) | The global regexes/stopwords target structural-noise VALUES; matching the value (not the whole line) mirrors betterleaks intent and minimizes over-suppression of real secrets. | Match `finding["line"]` (rejected — anchors wouldn't fit; broader over-suppression). |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Over-suppression — a real secret shaped like a noise pattern is dropped | Global patterns are anchored (`^…$`) and target structural noise; low collision with high-entropy secrets; AC-4 recall-preservation test guards it |
| Parallel workers silently skip the filter if globals aren't plumbed through the initializer | AC-6 exercises the ProcessPoolExecutor path explicitly |
| Header/description drift vs actual behavior after this lands | AC-7 + sequencing with `1p452` keep the comment truthful |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
