# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-07-14
review-evidence-source: events.jsonl
wave-id: `1skt1 executable-review-evidence`
Title: Executable Review Evidence

## Objective

Make falsification-driven, executable review evidence a framework-owned behavior that every newly installed and upgraded Wavefoundry project receives. Reviewers will verify material claims through public paths, state transitions, and exact repair replays; synthesize every validated observation into an explicit action; and converge repair review without confusing a technically real cleanup with a reason to reopen the whole system.

## Changes

- `1siu0-enh executable-review-evidence-protocol` — add the shared protocol, reviewer carriers, propagation, and contract tests.

Change ID: `1siu0-enh executable-review-evidence-protocol`
Change Status: `implemented`

Completed At: 2026-07-15

## Wave Summary

Wave `1skt1` (Executable Review Evidence) delivered one change: Executable Review Evidence Protocol. Notable adjustments during implementation: Executable Review Evidence Protocol: Post-prepare operator amendment: added four-way finding actionability and bounded review-convergence semantics after repeated `1ro44` re-reviews showed that validity plus the small-fix heuristic can expand indefinitely. The existing readiness verdict predates this material requirement and must be refreshed before implementation.; Executable Review Evidence Protocol: Canonical protocol implementation landed in seed 209 and canonical QA seed 239 was added. Renderer work began with the typed finite carrier registry, a marker-owned reconciler that runs before the Guru guard, and focused extension-preservation/idempotency/fail-safe tests.; Executable Review Evidence Protocol: Operator-directed bounded usability repair completed: approval chronology is affected-lane scoped; a typed MCP authoring surface captures explicit semantic judgments and derives bookkeeping; one-finding and empty-lightweight forms reduce record count; the generated current-head table reports open gates while collapsed JSONL remains authoritative. The new tool was dogfooded on this wave and honestly recorded that its repair-start evidence postdated the first edits because the authoring surface did not yet exist.

**Changes delivered:**

- **Executable Review Evidence Protocol** (`1siu0-enh executable-review-evidence-protocol`) — 14 ACs completed. Key decisions: Put the full protocol in the shared harness core and use short role-specific references.; Require executable proof proportionally by council depth, not universally.
## Journal Watchpoints

- `1ro44` is closed and the OPEN-wave slot is free. Preparing this wave does not activate it; implementation remains a separate operator-owned lifecycle step.
- The shared seed-209 protocol stabilizes before role-specific carriers; canonical seeds stabilize before rendered self-hosted surfaces.
- Seed edits are behavioral framework changes: implementation requires `seed_edit_allowed` and docs-contract review.
- Preserve proportionality: stronger evidence must not become speculative finding volume or a mandatory full attack matrix for lightweight work.
- Preserve convergence: `do_now` and bounded `maybe_later` work are completed now; `dont_do_later` and `not_issue` create no backlog; non-blocking cleanup receives focused verification rather than a fresh unrestricted council.

## Participants

- Coordinator: `wave-coordinator`
- Implementation: `implementer`
- Required review lanes: `code-reviewer`, `qa-reviewer`, `architecture-reviewer`, `security-reviewer`, `docs-contract-reviewer`
- Readiness council: `red-team`, `architecture-reviewer`, `security-reviewer`, `qa-reviewer`, `reality-checker`, `docs-contract-reviewer` (rotating)

## Review Checkpoints

- pre-implementation-review: passed (2026-07-14) — highest risk is introducing a strict marked-wave validator and carrier reconciler that either invalidates legacy waves or mutates project-authored extensions; the packet addresses this with prospective monotonic adoption, one `review_evidence.py` structural chokepoint, marker-owned sections, a typed carrier registry, public-path integration tests, and explicit extension-preservation/idempotency controls.
- Pre-mortem: avoidable churn would most likely come from (1) duplicating schema/derivation rules across seeds and lifecycle callers, (2) applying marked-wave requirements to unmarked historical records, (3) reconciling whole files instead of framework-owned sections, (4) wiring helpers without exercising setup/upgrade/render entry points, or (5) treating phrase-presence tests as reviewer-behavior evidence. Each has a named requirement, AC, and negative control in `1siu0`.
- Packet completeness: requirements and AC priorities are complete; required builder/reviewer lanes are named; architecture/testing/review docs and the renderer/lifecycle seams are identified; the known complexity risk is accepted only within the finite schemas and exact Requirement-15 matrix; MCP orientation confirmed `render_agent_surfaces`, setup/upgrade render paths, `wave_validators`, and the `wave_prepare_response`/`wave_review_response`/`wave_close_response` lifecycle call sites.
- Ordered lane sequence: `implementer` shared protocol/schema → `implementer` validator/lifecycle integration → `implementer` reviewer carriers and propagation → `qa-reviewer` conformance/public-path verification → `code-reviewer` + `architecture-reviewer` + `security-reviewer` + `docs-contract-reviewer` delivery review.
- Thought: begin with the canonical protocol and executable state derivation because every carrier, renderer row, lifecycle check, and QA fixture depends on those contracts; do not parallelize downstream carrier wording before seed 209 and the validator API stabilize.
- Gapfill: MCP orientation covered production renderer and lifecycle seams, but framework tests are intentionally excluded from the semantic code index; a bounded `rg` lookup located the existing renderer coverage in `test_render_agent_surfaces.py` rather than broad-searching the repository.
- Observe: the shared-protocol lane completed seed 209 plus canonical QA seed 239 without touching downstream carriers; the first propagation slice now has one typed registry/manifest and a marker-owned reconciler that preserves project extensions, runs before the Guru-absent guard, refreshes stale blocks, is idempotent, and fails safe on malformed markers (38 focused renderer tests pass).
- Thought: hold lifecycle integration until the standalone validator lane returns a stable API; meanwhile keep propagation limited to the shared owned block and registry rather than duplicating the full protocol across carriers.
- Observe: the validator lane returned a stable single API with 28 conformance cases; lifecycle/docs-lint integration added one public-path routing case (29 total) and a prepare/review/close attack fixture (23 lifecycle tests total). The carrier lane completed all 12 assigned seeds and removed size-first disposition shortcuts while keeping seed 209 canonical.
- Thought: next stabilize public setup/upgrade/render propagation and self-hosted reconciliation, then opt this wave into `review-evidence-protocol: 1` only when its initial delivery Review Run and complete synthesis rows can be recorded together.
- Thought: finish in dependency order with three bounded lanes: public setup/upgrade/render orchestration and unwired controls; canonical-to-self-host carrier reconciliation plus seed-050/100/150/160 ownership; then QA conformance and delivery dogfooding after both merge. Install and upgrade evidence must execute their public entry paths in temporary repositories, not call the reconciler helper directly.
- Reflect: the public-path lane immediately caught a recursive call accidentally introduced while adding native-carrier expansion, and also confirmed the reconciler still used the base registry. Fixed both at the chokepoint and added registered-only native-wrapper coverage (39 renderer tests green). Remaining propagation work must consume `review_protocol_carrier_manifest(repo_root)` rather than duplicating a destination list.
- Observe: public propagation now executes through setup, upgrade, and direct render against temporary target repositories; setup's `--root` mismatch was repaired so indexing and surface rendering cannot target different repositories. Ownership seeds 050/100/150/160 and the source-to-carrier docs now describe the same reconciler, QA seed 239, marker preservation, non-Guru operation, enabled-only wrappers, and new-wave adoption contract.
- Thought: run a fresh QA conformance pass against the merged runtime, renderer, setup/upgrade fixtures, new-wave creation, and exact Requirement-15 matrix before marking any remaining task or AC complete; QA must reproduce failures through public paths and distinguish structural proof from prompt-behavior dogfooding.
- **Post-prepare finding-actionability/convergence amendment — 2026-07-14: READINESS REFRESH PASS.** Operator direction added a material required contract after the prepare council. The refreshed red-team primer and fixed seats iteratively closed overlap in disposition predicates, free-form optional-value/rejection/blocking/review-depth choices, absent persisted candidate/run/cycle and required-lane authority state, security safe-evidence/waiver gaps, historical-adoption ambiguity, incomplete negative controls, missing Guru/architecture/performance/reality/repo-local reviewer carriers, stale `1ro44` sequencing, and helper-only propagation risk. The final plan uses an ordered actionability state machine whose facts and results are finite/derived; append-only marked-wave Review Run + Finding Synthesis JSONL validated through one `review_evidence.py` chokepoint; typed security/containment/lane/waiver state; named repair-run events and frozen-boundary safe-evidence exception; a monotonic prospective adoption marker; an exact Requirement-15 fixture matrix; a single typed carrier registry with one source-to-target row per surface; and a named reconciler exercised through public setup/upgrade/render paths before the Guru-absent guard. Every fixed and rotating seat re-verified the final text and approved.
- **Prepare-phase Wave Council [prepare-council] — 2026-07-14 refresh: PASS** (moderator: wave-council; primer-depth: full; seats: red-team, architecture-reviewer, security-reviewer, qa-reviewer, reality-checker, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: four disposition labels without ordered derivation, a sealed candidate/run universe, required-lane authority, and a frozen review boundary would remain gameable prose and could either bury a blocker or continue adjacency forever; strongest-alternative: one typed actionability state machine and append-only review-run/finding records validated at a single lifecycle chokepoint, propagated from one typed carrier registry)
- Refreshed council synthesis: the primer initially blocked AC-13; three amendment/re-verification passes converted the operator taxonomy into a deterministic state machine, added safe security evidence and specialist/waiver authority, defined wave-level repair cycles and the cycle-two freeze, closed prospective historical compatibility, enumerated exact negative controls, and replaced hand-maintained carrier lists with a registry exercised through public setup/upgrade/render paths. Final seat agreement is unanimous PASS. No implementation began; readiness remains separate from activation.
- **Prepare-phase Wave Council [prepare-council] — 2026-07-14: PASS** (moderator: wave-council; primer-depth: full; seats: red-team, architecture-reviewer, security-reviewer, qa-reviewer, reality-checker, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: phrase-presence tests and undefined evidence terms could produce performative compliance without executable public-path proof; strongest-alternative: define a prospective structured Evidence Record and bounded conformance corpus first, then propagate thin deterministic framework-owned carrier sections)
- Council synthesis: initial seat agreement was unanimous `blocked` at medium plan-readiness severity. The plan was amended in-session with the additive Evidence Record, readiness/delivery split, finite probe budgets, complete-census contract, fresh/independent restoration rule, safe-execution ceiling, seed-213 security calibration, canonical seed `239-qa-reviewer`, exact seed-050/100/150/160 propagation ownership, deterministic owned-section reconciliation, negative controls, and a bounded conformance corpus. The amendments resolve every blocking seat condition without expanding into a general property-testing or model-evaluation platform; residual limitation is recorded honestly — deterministic tests prove contract/schema/propagation, while delivery dogfooding supplies reviewer-behavior evidence.
- AC priority: AC-1, AC-2, AC-3, AC-4, AC-6, AC-7, AC-8, AC-9, AC-11, and AC-13 are required; AC-5, AC-10, and AC-12 are important. The required rows define the usable, convergent, and safely propagated minimum; the important rows strengthen census rigor, drift resistance, and behavioral dogfooding without blocking the core protocol when their documented evidence exists.
- Product-owner acknowledgment: operator directed that the review method be taught across all projects and explicitly requested preparation of this wave; required carrier propagation and safe proportional review are blocking scope, while no historical records are rewritten.
- **Delivery repair cycle 2 — bounded replay complete; convergence checkpoint recorded (2026-07-14).** The 13 sealed reproductions and named controls closed, and the setup/upgrade evidence correction cites exact runnable known-bad public-orchestrator fixtures without rewriting earlier adopted history. The first replay reused reviewer contexts, so cycle 3 transparently withdraws its overstated freshness and requires new context-free approval review. The final canonical suite passed 5,485 tests across 49 isolated files; `wave_validate` and `git diff --check` are clean. `wave-council-delivery` and all approval Evidence Records remain withheld pending the genuinely fresh lanes and council.

## Prepare Review Evidence

- red-team: approved refresh — strongest challenge closed by ordered derived predicates, sealed Review Run candidate universes, append-only synthesis/supersession, typed lane/waiver state, and the cycle-two safe-evidence exception
- architecture-reviewer: approved refresh — single `review_evidence.py` parser/validator ownership, persisted run/cycle lifecycle, objective full-council triggers, complete architecture/performance carriers, and public renderer propagation are coherent and bounded
- security-reviewer: approved refresh — typed reachability/authority/containment fields, exact blocker predicate, safe-boundary evidence, material-regression threshold, and required-lane/operator-waiver state prevent downgrade or unauthorized probing
- qa-reviewer: approved refresh — finite enum/state domains, sealed candidate universe, exact Requirement-15 matrix, public-path propagation/unwired controls, and contract-presence versus behavior-evidence distinctions are objectively testable
- reality-checker: approved refresh — named modules and setup/upgrade/render seams exist or are valid planned additions; `1ro44` is closed; typed optional-value/rejection facts and registry-derived carrier coverage close remaining reality drift
- docs-contract-reviewer: approved refresh — seed 209 remains the single detailed owner; every active/conditional carrier is registry-enumerated; adoption is monotonic/prospective; disposition, blocker, cross-run, and rejection contracts are internally consistent
- red-team: approved after amendment — full-depth primer exposed performative prompt compliance, undefined evidence terms, circular phrase tests, and vague propagation; all prescribed schema/phase/budget/census/independence/safety/propagation amendments are admitted.
- architecture-reviewer: approved after amendment — additive prospective record preserves historical schema compatibility; seed 239 plus seed-050/100/150/160 ownership and deterministic owned-section reconciliation close the source-to-carrier boundary.
- security-reviewer: approved after amendment — public-path evidence now has an explicit authority ceiling, disposable/read-only defaults, honest unsafe fallback, and seed 213 severity calibration based on impact, reachability, and authority gained.
- qa-reviewer: approved after amendment — finite budgets and N/A rules are testable; negative controls, real init/upgrade/self-host fixtures, and conformance cases prevent phrase-only tests from being presented as behavioral proof.
- reality-checker: approved after amendment — current seed ownership was reconciled against the tree; readiness and delivery evidence are distinct, and exact carrier ownership replaces “as applicable.”
- docs-contract-reviewer: approved after amendment — seed 209 is the single detailed source, carrier obligations remain thin, the source-to-carrier table is explicit, and contract-presence versus reviewer-behavior evidence is clearly distinguished.

## Finding Synthesis

<!-- waveframework:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| approval-actor-binding | do_now | no | completed | code-reviewer |
| approval-scope-and-authoring-burden | do_now | no | completed | code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, wave-council-delivery |
| architecture-state-contract-drift | do_now | no | completed | architecture-reviewer |
| carrier-contract-create-wave | do_now | no | completed | docs-contract-reviewer |
| carrier-symlink-root-escape | do_now | no | completed | security-reviewer |
| concurrent-platform-namespace-substitution | dont_do_later | no | not_required | docs-contract-reviewer, reality-checker, wave-council |
| create-wave-guidance | do_now | no | completed | qa-reviewer |
| delivery-phase | do_now | no | completed | qa-reviewer |
| dogfood-evidence-misattribution | do_now | no | completed | docs-contract-reviewer |
| durable-adoption | do_now | no | completed | qa-reviewer |
| evidence-schema | do_now | no | completed | qa-reviewer |
| handoff-tracking | do_now | no | completed | docs-contract-reviewer |
| install-carriers | do_now | no | completed | qa-reviewer |
| lifecycle-test-export | do_now | no | completed | qa-reviewer |
| mandatory-convergence-checkpoint | do_now | no | completed | code-reviewer |
| marker-enclosure | do_now | no | completed | qa-reviewer |
| native-carriers | do_now | no | completed | qa-reviewer |
| non-mcp-scaffold-literals | do_now | no | completed | docs-contract-reviewer |
| participant-lane-parser | do_now | no | completed | code-reviewer |
| platform-render-common-ancestor-escape | do_now | no | completed | wave-council |
| reverification-freshness-misattribution | do_now | no | completed | docs-contract-reviewer |
| review-status-ok | do_now | no | completed | qa-reviewer |
| review-transition-completion | do_now | no | completed | code-reviewer |
| schema-contract-parity | do_now | no | completed | docs-contract-reviewer |
| synthesis-evidence-order-kind | do_now | no | completed | code-reviewer |
| typed-evidence-semantic-key-collision | do_now | no | completed | code-reviewer, qa-reviewer, architecture-reviewer, security-reviewer, docs-contract-reviewer, wave-council-delivery |
| upgrade-order-fixture | do_now | no | completed | qa-reviewer |

<details class="wavefoundry-review-evidence">
<summary>Machine review evidence — 186 records; 19 runs; 27 findings; current: do_now 26, maybe_later 0, dont_do_later 1, not_issue 0</summary>
</details>
<!-- waveframework:finding-synthesis end -->

## Review Evidence

- wave-council-readiness: approved 2026-07-14 — full-depth prepare council passed after all blocking amendments were incorporated; structured synthesis and seat evidence recorded above
- wave-council-readiness: withdrawn 2026-07-14 — approval predates the material AC-13 finding-actionability/convergence amendment; refresh readiness before implementation
- wave-council-readiness: approved 2026-07-14 refresh — full-depth council unanimously approved the final AC-13 state machine, convergence, security-authority, evidence, and carrier-propagation contracts
- code-reviewer: approved 2026-07-14 — fresh post-repair code review; exact transition and stale-approval attacks closed
- qa-reviewer: approved 2026-07-14 — fresh public-path QA; 435 focused tests and 20 named replays passed with zero skips
- architecture-reviewer: approved 2026-07-14 — fresh source-to-contract trace and 470 relevant focused tests passed
- security-reviewer: approved 2026-07-14 — fresh 11-cell renderer/setup/upgrade escape matrix passed with no external writes
- docs-contract-reviewer: approved 2026-07-14 — fresh seed/render/schema/lifecycle contract review passed
- reality-checker: approved 2026-07-14 — strongest guidance-only alternative rejected; 448 normal-path tests passed with zero skips
- code-reviewer: withdrawn 2026-07-14 — approval predates cycle-6 platform-render ordering repair
- qa-reviewer: withdrawn 2026-07-14 — approval predates cycle-6 platform-render ordering repair
- architecture-reviewer: withdrawn 2026-07-14 — approval predates cycle-6 platform-render ordering repair
- security-reviewer: withdrawn 2026-07-14 — approval predates cycle-6 platform-render ordering repair
- docs-contract-reviewer: withdrawn 2026-07-14 — approval predates cycle-6 platform-render ordering repair
- reality-checker: withdrawn 2026-07-14 — approval predates cycle-6 platform-render ordering repair
- wave-council-delivery: changes requested 2026-07-14 — `.claude` common-ancestor escape wrote six external files before late refusal
- operator-signoff: <approved when operator confirms closure>
- code-reviewer: withdrawn — approval-scope-and-authoring-burden requires affected-lane re-verification
- qa-reviewer: withdrawn — approval-scope-and-authoring-burden requires affected-lane re-verification
- architecture-reviewer: withdrawn — approval-scope-and-authoring-burden requires affected-lane re-verification
- docs-contract-reviewer: withdrawn — approval-scope-and-authoring-burden requires affected-lane re-verification
- wave-council-delivery: withdrawn — approval-scope-and-authoring-burden requires affected-lane re-verification
- code-reviewer: withdrawn — approval-scope-and-authoring-burden requires affected-lane re-verification
- qa-reviewer: withdrawn — approval-scope-and-authoring-burden requires affected-lane re-verification
- architecture-reviewer: withdrawn — approval-scope-and-authoring-burden requires affected-lane re-verification
- docs-contract-reviewer: withdrawn — approval-scope-and-authoring-burden requires affected-lane re-verification
- wave-council-delivery: withdrawn — approval-scope-and-authoring-burden requires affected-lane re-verification
- code-reviewer: withdrawn — typed-evidence-semantic-key-collision requires affected-lane re-verification
- qa-reviewer: withdrawn — typed-evidence-semantic-key-collision requires affected-lane re-verification
- architecture-reviewer: withdrawn — typed-evidence-semantic-key-collision requires affected-lane re-verification
- security-reviewer: withdrawn — typed-evidence-semantic-key-collision requires affected-lane re-verification
- docs-contract-reviewer: withdrawn — typed-evidence-semantic-key-collision requires affected-lane re-verification
- wave-council-delivery: withdrawn — typed-evidence-semantic-key-collision requires affected-lane re-verification
- code-reviewer: withdrawn — typed-evidence-semantic-key-collision requires affected-lane re-verification
- qa-reviewer: withdrawn — typed-evidence-semantic-key-collision requires affected-lane re-verification
- architecture-reviewer: withdrawn — typed-evidence-semantic-key-collision requires affected-lane re-verification
- security-reviewer: withdrawn — typed-evidence-semantic-key-collision requires affected-lane re-verification
- docs-contract-reviewer: withdrawn — typed-evidence-semantic-key-collision requires affected-lane re-verification
- wave-council-delivery: withdrawn — typed-evidence-semantic-key-collision requires affected-lane re-verification
- code-reviewer: approved — APPROVED — current merge-boundary source review and the registered MCP attack/control matrix show protected semantic keys are rejected before construction, exact actor binding remains enforced, and legitimate approvals remain accepted; the focused regression and canonical 5,516-test run pass.
- qa-reviewer: approved — APPROVED — the exact actor collision is refused, the mismatch-only negative control is refused, the legitimate QA dry-run succeeds, the named regression ran one test with zero skips and passed, and the canonical isolated suite passed 5,516 tests across 49 files.
- architecture-reviewer: approved — APPROVED — the repair is localized to the typed response merge chokepoint, derives protected keys from the semantic event itself, changes no schema or ownership boundary, preserves downstream actor validation, and passes the canonical 5,516-test run.
- security-reviewer: approved — APPROVED — the registered actor-spoof collision now fails closed, the underlying mismatched-actor control also fails closed, and the legitimate exact-actor control succeeds; no replacement authority defect was found at the bounded merge boundary.
- docs-contract-reviewer: approved — APPROVED — the current typed public path matches the explicit top-level actor and documented evidence-field contract, affected-lane chronology and compact authoring remain consistent, and the canonical isolated suite passed 5,516 tests.
- wave-council-delivery: approved — APPROVED — cycle-7 approval-scope evidence and cycle-8 collision evidence are completed; every affected specialist lane approves; the exact registered attack and adjacent controls pass; no replacement defect or changed review boundary was found; canonical isolated suite: 5,516 tests across 49 files OK.
- operator-signoff: approved — The operator explicitly instructed in the current thread: "Ok, close the wave, let's do this change next."
- wave-council-readiness: approved — Existing refreshed readiness council approved the amended executable-review-evidence plan before implementation; this companion record supplies the machine linkage after the typed authoring surface became available.

## Dependencies

- No external sequencing blocker: `1ro44` is closed. Activation remains separate from readiness and operator-owned.
