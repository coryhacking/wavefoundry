# Wave Record

Owner: Engineering
Status: planned
Last verified: 2026-07-04

wave-id: `1roqn lance-drift-eligibility`
Title: Lance Drift Eligibility

## Objective

Stop the Lance drift-repair loop from permanently re-flagging files that are excluded from semantic chunking: drift candidacy is gated on current-build chunk eligibility, so the incremental build's zero-change fast path (shipped in wave `1p9q3`) is actually realized on repos with meta-tracked, chunking-excluded files — including this one, which pays ~1 s + ~1.35 MB per hook fire today.

## Changes

Change ID: `1rmaf-bug lance-drift-repair-loop-excluded-files`
Change Status: `planned`

## Wave Summary

Single bug fix scoped from wave `1p9q3`'s delivery review: `_detect_lance_drift`'s candidate set (all of `meta.json`) is wider than the repair path's reach (content-filtered files), so excluded files loop forever — the self-healing `chunks_emitted` assumption structurally cannot hold for files that never reach the chunk-write path. Fix = per-build eligibility intersection at the call site, docstring truth, verbose diagnostics, and tests covering both field states plus the include-flag transition; live before/after verification on the self-hosted repo is the closing proof.

## Journal Watchpoints

- Blocking: implementation cannot start until wave `1p9q3` closes (single-OPEN rule); no code overlap with `1p9q3`'s diff — this wave touches `indexer.py`'s semantic-index drift path only.
- Follow-up watchpoint: after the fix lands, watch one week of self-hosted hook builds for any recurrence of drift-repair lines on excluded files (a second contributing cause would surface here).
- Guard: the eligibility narrowing must not weaken legitimate drift repair for eligible files (AC-2 guard test) — the 1p3b9 repair contract stands; only the candidate set narrows.
- Include-flag transitions (`--include-tests` / `--include-generated` flips) are the edge where over-broad exclusion would strand real drift — eligibility is computed per build, never persisted (AC-3).
- Closing proof is the live self-hosted before/after (AC-4): a graph-excluded doc edit must take the `merge[zero-change]` path with no drift-repair line for `test_graph_incremental_merge.py`.

## Participants

- code-reviewer — `indexer.py` drift-detection logic is framework-script code
- qa-reviewer — required (bug fix per `review_policies.require_qa_reviewer_for_bug_fixes`); AC priority table present

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-07-04: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, architecture-reviewer, security-reviewer, qa-reviewer, reality-checker, performance-reviewer; rotating-seat: performance-reviewer; strongest-challenge: the original eligibility intersection was a no-op for content=graph incrementals — files_for_content is the unfiltered code walk while zero rows are writable, so the loop would survive in that mode — resolved by amendment, Requirement 7 write-capability guard + AC-6 pin; strongest-alternative: narrow files_for_meta to kill the loop at the root — declined, it breaks the meta-stability contract, blinds graph change detection, and mis-scopes the idle reap)
- Prepare council synthesis detail — 2026-07-04 (seats as above; rotating seat chosen as performance-reviewer because the wave protects a shipped performance win). **Primer:** strongest challenge — the original eligibility intersection was a NO-OP for `content="graph"` incrementals (`files_for_content` = unfiltered code walk while zero rows are writable), so the loop would have survived in one mode; resolved by amendment (Requirement 7 write-capability guard + AC-6, "chunk-eligible = row-writable this build"). Primer also pinned fixture content modes (AC-1 docs mode — the hook's bare-invocation default and the live loop's mode; AC-3 code mode with the flag-sensitive file class, the live file's own carve-out being unconditional), the reaper parameter-naming firewall (Requirement 8), the per-kind residual (named-deferred), and the AC-4 token dependency on wave `1p9q3` landing. **Challenge round (one, per protocol):** the qa seat initially returned NOT READY on a claim that the docs-mode derivation was also a no-op; the moderator put the counter-evidence (the `files` content-scoped reassignment at `indexer.py:3103-3112` precedes `files_for_content = files`, plus the empirical discriminator — the live file's `chunks_emitted` stays ABSENT under continuous hook builds, impossible under the challenged model) and the qa seat verified independently, WITHDREW the finding (its read had entered the function past the reassignment), and restated READY. The refuted claim's residual truth (a docs-walk-included file emitting only code-kind chunks still loops) is exactly the already-named per-kind deferral. **seat_agreement_aggregate:** post-challenge `unanimous` READY; max_severity at finding time `high` (the graph-mode no-op — the defect surviving in one mode), resolved by amendment before readiness. **Seat contributions adopted:** required keyword-only `chunk_eligible_rel_paths` with all ~12 direct test callers updated (qa); reaper-wide-set tripwire test — the idle reap runs on the zero-change fast path this fix makes common (security); guard on the `build_docs or build_code` booleans not the content string + standard path normalization (architecture); per-branch eligibility docstring semantics (qa challenge-round advisory); AC-6 asserts absence of the "repairing" stderr line (qa); reasoned verbose line (security); AC-4 trial-validity line pair (rotating seat). **Rotating fifth seat (best alternative):** bless the path — alternatives dismantled on code anchors: narrowing `files_for_meta` breaks the meta-stability contract, blinds graph change detection, and mis-scopes the reap; per-kind `chunks_emitted` doesn't touch the primary defect (schema migration for the deferred residual only); force-include into `files_to_index` violates the unconditional framework-test guarantee and converts the loop to its stale-positive variant; repair backoff needs the persistence primitive the Decision Log rightly rejects. Perf framing confirmed end-to-end (`drifted → changed_broad → changed_for_graph → _build_graph_artifacts`); bonus: the fix also stops cross-mode drift from forcing graph merges in docs builds. **Reality seat:** all five load-bearing factual claims re-derived true; the live loop empirically re-verified in exactly the predicted state. AC priorities recorded. Product-owner acknowledgment: not applicable (framework-internal defect fix).

## Review Evidence

- wave-council-readiness: approved 2026-07-04 — prepare council synthesis verdict READY after amendments (write-capability guard, fixture mode pins, signature migration, reaper tripwire, docstring semantics); one challenge round run and resolved by withdrawal; seats unanimous
- operator-signoff: pending operator confirmation at closure

## Dependencies

- Wave `1p9q3 graph-index-efficiency` must close before this wave opens (single-OPEN rule); the fix protects that wave's shipped fast path.
