# Decision: Readiness amendments: activation candidates are only change…

Owner: Engineering
Status: rejected
Last verified: 2026-10-03

Memory ID: `1zn7j-mem decision-readiness-amendments-activation-candidates-are-only`
Kind: `decision`
Confidence: 0.6
Created: 2026-10-03
Updated: 2026-10-03
Source exploration cost: 132912
Source event: `decision-log:1zlu2-enh close-one-change-and-activate-dependents:5ab33dc0f93434ca`
Validation: reject
Validated by: agent
Action delta: No durable action: wf_close_change behaviour is specified in docs/specs/mcp-tool-surface.md and pinned by test_close_change.py.
Validation rationale: The amendment list records readiness findings that are now the tool's documented contract and tests; it carries no lesson beyond the spec.
Evidence verified: true
Current target verified: true
Canonical overlap: duplicates

## Summary

Decision (wave 1zlu1): Readiness amendments: activation candidates are only changes whose wave-record `Depends On:` names the closed change, with AC-3 cases for a no-dependency change and an already-satisfied one (B1); `wave_lint_lib/constants.py` and the `test_docs_lint.py` transition test added to targets and tasks (N1); `cache.invalidate()` on success (N2); registry census widened to every literal `wf_close_wave` outside tests (N3); rollback only on lint failures the write introduced, against a pre-write baseline, and docs-lint confirmed lock-free under the publication lock (N4); one existing parser, `wave_validators._parse_change_records`, and an out-of-wave target counts as not done (N5); `@_fail_closed_on_record_layout("wf_close_change")` and the hand-listed test tables in AC-6 (N6); the packaged implement-wave template and seeds `100` and `180` planned so distributions see the tool (N8); architecture docs in tasks and ACs (N11); blocked-dependent risk recorded. Rationale: Readiness review findings, 2026-10-02. Operator decisions above are unchanged.

## Evidence

- `1zlu2-enh close-one-change-and-activate-dependents`
- `1zlu1`

## Targets

- `wave_lint_lib/constants.py`
- `test_docs_lint.py`
