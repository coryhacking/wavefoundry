# RELIABILITY.md Graph-Builder Claim Strands the Target's Docs Gate When the Advancer's Preconditions Miss

Change ID: `1uf66-bug reliability-doc-claim-strands-docs-gate-on-version-bump`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-08-04
Wave: `1uf65 integrity-checks-guidance`

## Rationale

Target-repo field report (2026-08-04, recurring; the reporter's one remaining open item): the
framework injects a graph-builder-version fact into the target's `docs/RELIABILITY.md` outside
any marker region, then a later `GRAPH_BUILDER_VERSION` bump hard-fails the target's own docs
gate because the doc still claims the old version.

Mechanism verified in this tree: the docs-constants lint validates the doc claim against the
code constant and HARD-FAILS on mismatch (`wave_lint_lib/docs_constants_validators.py:77-95`),
while the only thing that ever advances the claim is the upgrade-time reconciler
(`upgrade_extensions.py:387-448`), which is deliberately conservative: it rewrites only when a
pre-extract snapshot captured an EXACT code/doc match (`_snapshot_graph_builder_doc_claim`,
:401-407: exactly one claim AND its value equals the installed version) and the post-extract doc
still carries exactly that old claim (`_reconcile_graph_builder_doc_claim`, :438-443). Any
precondition miss (zero or multiple claim matches, a pre-existing mismatch, an unreadable file,
a missed snapshot) silently returns False, and the target is stranded: the lint demands the new
value, nothing will ever write it, and the fact block sits outside a renderer-owned marker
region so no surface-render regenerates it either. The failure recurs on every future
`GRAPH_BUILDER_VERSION` bump.

The asymmetry is the defect: the advancer fails safe toward "do not edit" while the gate fails
hard toward "block everything". Council corrections (2026-08-04, code-grounded): the MISMATCH
branch already names file, line, current, and expected (`docs_constants_validators.py:136-141`);
the real message gaps are the MISSING-claim branch (:128-135, names neither line nor expected)
and the absent one-line-fix instruction on both branches. Three additional miss shapes join the
census: version-probe failure (`_graph_builder_version` returns empty on an unreadable
`graph_indexer.py` or a regex-shape change, killing both snapshot and reconcile), non-upgrade
flows (the advancer runs only from upgrade hooks, so nothing ever writes outside an upgrade),
and the absorbing-state property (once mismatched, the snapshot precondition can never
re-qualify on any future upgrade, and the lint fails continuously between upgrades). The
injection-site question is ANSWERED: no code writes the fact block; `docs/RELIABILITY.md` is
agent-authored at install (seed-012:131 via seed-070) and the claim line is lint-coerced by the
missing-claim branch, so no renderer or marker machinery exists for this doc.

## Requirements

1. **Both lint branches state the exact one-line fix:** the mismatch branch keeps its existing
   file/line/current/expected naming and adds the fix instruction (change `<current>` to
   `<expected>` on that line); the missing-claim branch gains the line-to-add, the expected
   value, and the same instruction. Reproduce red-first with a real temp-repo docs gate run per
   branch.
2. **Mechanism DECIDED at Prepare (2026-08-04): actionable messages ARE the convergence; the
   advancer is untouched.** Rationale in the Decision Log. Every formerly-stranding shape
   (no snapshot, pre-existing mismatch, version-probe failure, non-upgrade drift, absorbing
   state, multiple claims, unreadable file) resolves through the docs gate telling the target's
   agent the exact edit; target repos are agent-operated, so a fully specified one-line fix is
   self-healing in practice without any automatic writer that could clobber operator-customized
   text.
3. **The decision is proven on the recurrence path:** a test drives a version bump over a doc
   in each formerly-stranding shape and shows the gate fails with the Requirement 1 actionable
   message (never a mystery wedge); applying the stated fix verbatim makes the gate pass.
4. **No behavior change for the advancer:** the exact-match advance and its byte-preservation
   pins (`test_upgrade_wavefoundry.py:7777-7792` customized-claim preservation, :7794-7805
   pre-existing-mismatch preservation) stay green unmodified.

## Scope

**Problem statement:** a framework-injected doc fact has a hard-fail validator but only a
narrow-precondition writer, so version bumps strand target repos' docs gates with no actionable
message.

**In scope:** `wave_lint_lib/docs_constants_validators.py` claim-check messages (:109-142) and
`test_docs_constants_lint.py`; `test_upgrade_wavefoundry.py` only if its RELIABILITY fixtures
pin message text (verify; the advancer itself is untouched). Serialization note: 1uf67 also
edits `test_upgrade_wavefoundry.py`; implement the two changes serially in one workstream.

**Out of scope:** other docs-constants claims; `GRAPH_BUILDER_VERSION` semantics; the advancer
(`upgrade_extensions.py:387-453`) and its byte-preservation pins; any automatic writer or
marker-region machinery (rejected mechanisms).

## Acceptance Criteria

- [x] AC-1: Each formerly-stranding precondition-miss shape produces the actionable lint
  message naming the exact one-line fix, and applying that fix verbatim passes the gate
  (red-first per branch).
- [x] AC-2: The advancer and its byte-preservation pins are byte-unchanged and green.
- [x] AC-3: One mechanism only (messages-only, per the recorded Prepare decision); no writer,
  no marker machinery, no lint-tier change.
- [x] AC-4: Full framework suite passes.

## Tasks

- [x] Red-first: reproduce both lint branches in a temp repo through the real docs gate
- [x] Add the one-line-fix instruction to both branches; line and expected value on the
  missing-claim branch
- [x] Tests per formerly-stranding shape; verify the advancer pins untouched; full suite
- [x] CHANGELOG bullet (current unreleased section)

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes |
| ---------- | ----------- | ---------- | ----- |
| fix        | implementer | —          |       |


## Serialization Points

- `upgrade_extensions.py`, `wave_lint_lib/docs_constants_validators.py` and their tests

## Affected Architecture Docs

Candidates at Prepare: CHANGELOG; possibly the RELIABILITY fact-block documentation wherever the
injection site is documented.

## AC Priority

| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The actionable message is the entire chosen mechanism; without it targets stay stranded |
| AC-2 | required | The advancer's byte-preservation pins encode deliberate operator-text protection |
| AC-3 | required | The simplicity constraint is binding; a second mechanism is scope creep by definition |
| AC-4 | required | Lint changes ripple into every docs gate; the full suite is the recurrence guard |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-08-04 | Filed from a recurring target-repo field report; mechanism verified in this tree (conservative advancer at upgrade_extensions.py:401-407/:438-443 vs hard-fail lint at docs_constants_validators.py:77-95; every precondition miss returns False silently). | Field report 2026-08-04; code_read/code_keyword this session |
| 2026-08-04 | Red-first reproduction: two new temp-repo tests in test_docs_constants_lint.py (mismatch branch incl. duplicate-claim shape, missing-claim branch) failed on the current tree exactly at the absent fix instruction (3 failures in 19 tests). | Red run: `python3 -B -m unittest discover ... test_docs_constants_lint.py` FAILED (failures=3) |
| 2026-08-04 | Both lint branches now append the one-line fix instruction (mismatch: change current to expected on the named line; missing: add the named claim line with the expected value); tests parse the message and apply the stated fix verbatim, then the gate passes. Green: 19/19. | docs_constants_validators.py:128-147; test_docs_constants_lint.py DocsConstantsLintTests; green run OK (19 tests) |
| 2026-08-04 | Advancer untouched and byte-preservation pins reverified green (customized-claim and pre-existing-mismatch preservation, plus the legacy checkpoint compatibility class): 16/16 OK. | `unittest tests.test_upgrade_wavefoundry.HistoricalMemoryUpgradeExtensionBootstrapTests tests.test_upgrade_wavefoundry.ArchivedLegacyMemoryCheckpointCompatibilityTests` OK (16 tests) |
| 2026-08-04 | Full framework suite green after both wave changes landed: 6805 tests across 62 files, OK. Docs gate green (`wf_validate_docs` passed). | `run_tests.py` OK (6805 tests); wf_validate_docs ok |
| 2026-08-04 | Gapfill: shell `grep`/`sed` used to locate the `## [1.15.2] - unreleased` CHANGELOG section, and `git status`/`git diff --stat` used to prove upgrade_extensions.py is byte-unchanged (no MCP tool exposes working-tree diff state). | Bash: CHANGELOG.md:9; `git diff --stat upgrade_extensions.py` empty |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-08-04 | Test shape mapping: the seven formerly-stranding miss shapes collapse onto the two observable doc states the lint can see (wrong value present, claim absent), so the branch tests cover them via one mismatch test with stale-claim and duplicate-claim subtests plus one dropped-claim test; the version-probe-failure shape resolves through the pre-existing expected-None message (unchanged, already names its fix), and the unreadable-file shape keeps the documented out-of-scope skip | The lint is stateless: no-snapshot, pre-existing mismatch, absorbing state, and non-upgrade drift are indistinguishable at lint time and all present as a mismatched claim; testing them separately would duplicate one assertion four times | Seven separate fixture histories (rejected: identical observable input to the validator) |
| 2026-08-04 | Convergence mechanism: actionable messages only; the advancer stays byte-unchanged | Target repos are agent-operated, so a docs-gate error naming the exact one-line edit is self-healing in practice for EVERY miss shape including the absorbing state; every automatic-writer variant either cannot heal already-stranded targets (narrow widening: claim no longer equals the old installed version) or clobbers deliberately-preserved operator text and breaks the byte-preservation pins at test_upgrade_wavefoundry.py:7777-7805 | (a) widen the advancer (rejected: narrow form heals nothing already stranded; wide form breaks the customized-claim pins that encode deliberate design); (b) marker-region ownership (rejected: no renderer owns this agent-authored doc; building one plus migrating stranded targets is the heaviest option against the simplicity constraint); (c) lint warning tier (rejected: docs-lint has no warning tier for this check, it reopens the silent-drift hole the lint exists to close, and it contradicts docs/RELIABILITY.md:65's own documented contract) |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Widening the advancer overwrites operator-authored doc text | Requirement 2's decision weighs this explicitly; option (b) marker-region ownership removes the hand-edit surface entirely |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
