# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-07-20
review-evidence-source: events.jsonl
wave-id: `1slep external-wave-event-ledger`
Title: External Wave Event Ledger

## Objective

Move canonical executable review history out of `wave.md` into a fixed sibling `events.jsonl` before the protocol ships. Preserve the human Markdown narrative and generated current-state summary while making lifecycle validation, persistence, install, and upgrade paths depend on one direct machine-readable authority with no dual-format fallback. This wave closes before the next framework release; the temporary inline format will not ship to consumers.

## Changes

Change ID: `1sl65-enh wave-events-jsonl-authority`
Change Status: `complete`

Completed At: 2026-07-15

## Wave Summary

Wave `1slep` (External Wave Event Ledger) delivered one change: External Wave Event Ledger. Notable adjustments during implementation: External Wave Event Ledger: Readiness primer plus architecture/security seats required a stable operation identity, one mutation lock/commit point, canonical byte/hash rules, explicit partial-success recovery, consumer-upgrade non-migration, stale-projection reader behavior, and exact path-scoped index exclusion. The plan was amended before implementation.; External Wave Event Ledger: Red-team found that source-declaration tamper made an adopted ledger indexable while lifecycle correctly failed closed. The bounded repair excludes when either the exact declaration is valid or retained adoption proves the wave, preserving eligibility for unadopted lifecycle-shaped notes and unrelated same-named files. Independent replay closed removed/malformed-source attacks and stale-row cleanup.; External Wave Event Ledger: Final delivery council APPROVED after reconciling code, QA, architecture, security, docs-contract, reality, and red-team PASS. A typed readiness reconciliation was added for the historical pre-cutover Markdown approval. The close dry-run is green except for operator signoff, which remains operator-owned.

**Changes delivered:**

- **External Wave Event Ledger** (`1sl65-enh wave-events-jsonl-authority`) — 9 ACs completed. Key decisions: Select a fixed sibling `events.jsonl` as the sole review-event authority and keep `wave.md` as human narrative plus generated projection.; Make a bounded pre-release cutover with no v1/v2 reader or fallback.
## Journal Watchpoints

- Block implementation until the persistence contract and crash/retry ordering receive readiness review; cross-file authority/projection behavior is the load-bearing boundary.
- Follow up every writer/reader consumer through install, upgrade, dashboard/resource, docs-lint, review, prepare, close, and the typed authoring tool before migration.
- Do not add an inline fallback or v1/v2 routing; this is an unreleased one-format cutover.
- Run the self-hosted migration only after the new writer/validator path is stable, with record-for-record equality evidence and no concurrent wave-record edits.
- Migrate this in-flight wave last, then prove its next lifecycle read and review-evidence append use only the external ledger.
- Keep durability proportional: serialize real concurrent writers and deduplicate response-loss retries from existing event identity; do not add a caller operation-ID protocol or a generic event transaction layer.

## Participants

- Coordinator: Engineering
- Required readiness/delivery lanes: code-reviewer, qa-reviewer, architecture-reviewer, security-reviewer, docs-contract-reviewer, reality-checker, red-team, wave-council
- Product-owner acknowledgment: recorded 2026-07-15 — the operator selected fixed sibling `events.jsonl`, rejected v1/v2 compatibility before release, and directed total path-scoped semantic-index exclusion with the generated Markdown summary remaining searchable.

## Review Checkpoints

- Prepare wave — technical checks pass; full-depth council changes requested against the initial plan. Transaction identity, canonical bytes/hash, recovery, migration, reader, install/upgrade, and indexing contracts are amended. Readiness remains withheld pending the isolated docs-contract rotating seat and focused affected-seat recheck.
- External plan review — changes requested on durability proportionality and in-flight self-migration. Repaired in plan: existing event/context inputs now provide retry identity under one lock, caller-supplied operation IDs are removed, `1slep` migrates last and re-reads externally, and pre-release landing is explicit. Readiness remains withheld pending the required council completion.
- Prepare seat evidence — `architecture-reviewer` and `reality-checker` changes are incorporated; `security-reviewer` focused recheck PASS; `qa-reviewer` PASS with the required executable evidence matrix carried by AC-3 through AC-8; `docs-contract-reviewer` isolated rotating-seat PASS with no remaining `do_now` or `maybe_later`; red-team supplied the full-depth adversarial primer.
- **Prepare-phase Wave Council [prepare-council] — 2026-07-15: PASS** (moderator: wave-council; primer-depth: full; seats: red-team, architecture-reviewer, security-reviewer, qa-reviewer, reality-checker, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: concurrent writers and response-loss retries could lose or duplicate review events without serialized identity-aware persistence; strongest-alternative: caller operation IDs plus a replay registry were rejected as disproportionate in favor of derived event identity under the existing project-global lock)
- Operator plan revision focused re-readiness — PASS. The per-event identity now includes `finding_id` for multi-finding review contexts. Review found and repaired one adjacent fixed-width assumption: lifecycle IDs use the canonical 5-or-6-character grammar. `security-reviewer` PASS on fail-closed replay/conflict semantics; `qa-reviewer` PASS after AC-4 pinned structured identity, multi-finding fan-out, same-context replay/conflict, new-context legitimate repetition, both lifecycle-prefix lengths, and delimiter-shaped inputs. No full-council boundary changed and no remaining `do_now` or `maybe_later` concern exists.
- pre-implementation-review: passed (2026-07-15) — highest risks are premature self-migration, consumer-history mutation, cross-file partial writes, incomplete index exclusion, and identity/schema drift. The plan's serialization order, event-authority commit point, consumer non-migration boundary, full/incremental cleanup fixtures, and `1slep`-last proof address them. Ordered lanes: implementer core ledger/parser → implementer public writer/lifecycle consumers → install/upgrade/index integration → QA migration/fault matrix → required delivery reviewers.
- Implementation checkpoint — the canonical external ledger, count/hash adoption proof, identity-aware serialized writer, lifecycle/lint/dashboard/resource readers, exact semantic-index exclusion, and failure-recovery paths are implemented and focused-test green. The one-time census migrated exactly `1skt1` (186 records) and `1slep` (2 records), in that order, with identical source/target proofs; `1slep` was immediately re-read through the external-only path before this post-migration checkpoint was recorded. Install/upgrade/package verification and full-suite delivery review remain in progress.
- Delivery repair checkpoint — all nine executable delivery findings recorded so far are repaired and independently re-verified. The latest round closed two security defects (symlinked wave-directory escape before read/lock/write and reserved metadata digest poisoning), aligned the public atomic convergence contract with the implemented cycle-2 transaction, refreshed the session handoff, and corrected the canonical-path expectation in the adjacent background-refresh test. Focused regressions, the 66 review-evidence tests, rendered-carrier checks, and docs lint are green; reality-checker, red-team, final council synthesis, and the final canonical suite remain.
- Red-team convergence checkpoint — retained adoption now independently keeps an exact canonical ledger out of semantic retrieval after source-declaration removal or malformation, while unadopted lifecycle-shaped notes and root/nested/deeper `events.jsonl` controls remain eligible. The exact pre-fix attack was reproduced, the bounded predicate repair was independently re-verified, incremental stale-row cleanup remains green, and reality-checker PASS covered setup, upgrade, package, migration, lifecycle, dashboard/resource, and index flows. Final canonical verification: 5,596 tests across 50 isolated files, OK; docs lint, carrier registry, and `git diff --check` green. Final focused code/docs verdicts and Wave Council synthesis remain.
- **Delivery Wave Council — APPROVED.** All required specialist seats reconcile to PASS; all ten executable finding heads are completed with empty blocking lanes. The strongest final challenge—source tamper admitting an adopted ledger into semantic retrieval—is closed by the narrower valid-source-or-retained-adoption predicate with unadopted controls preserved. The council also recorded typed reconciliation for the pre-cutover readiness marker. Close dry-run now passes lint, garden, both council approvals, tasks, ACs, and change completion; only operator-signoff remains, by design.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| code-adoption-applicability-fail-open | do_now | no | completed | code-reviewer |
| code-index-ledger-exclusion-scope | do_now | no | completed | code-reviewer |
| code-resource-missing-projection | do_now | no | completed | code-reviewer |
| docs-convergence-checkpoint-atomic-contract | do_now | no | completed | docs-contract-reviewer |
| docs-session-handoff-external-ledger-state | do_now | no | completed | docs-contract-reviewer |
| qa-build-pack-direct-run | do_now | no | completed | qa-reviewer |
| qa-convergence-checkpoint-atomicity | do_now | no | completed | qa-reviewer |
| redteam-adopted-ledger-index-tamper | do_now | no | completed | red-team |
| security-reserved-review-metadata-digest-poisoning | do_now | no | completed | security-reviewer |
| security-wave-directory-symlink-escape | do_now | no | completed | security-reviewer |

<details class="wavefoundry-review-evidence">
<summary>Machine review evidence — 87 records; 25 runs; 10 findings; current: do_now 10, maybe_later 0, dont_do_later 0, not_issue 0</summary>
</details>
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval follows every affected repair | none |
| wave-council-delivery | approved | current executed approval follows every affected repair | none |
| operator-signoff | approved | current executed approval follows every affected repair | none |
| qa-reviewer | approved | current executed approval follows every affected repair | none |
| architecture-reviewer | approved | current executed approval follows every affected repair | none |
| security-reviewer | approved | current executed approval follows every affected repair | none |
| reality-checker | approved | current executed approval follows every affected repair | none |
| red-team | approved | current executed approval follows every affected repair | none |
| code-reviewer | approved | current executed approval follows every affected repair | none |
| docs-contract-reviewer | approved | current executed approval follows every affected repair | none |
<!-- wave:review-status end -->

- wave-council-readiness: approved (moderator: wave-council — full-depth readiness council completed; the amended plan resolves sole authority, bounded concurrency/retry, canonical integrity, self-host migration, target install/upgrade, reader, and indexing boundaries)
- wave-council-readiness: approved (superseding prior readiness state after focused 2026-07-15 operator-plan recheck — security and QA PASS on the clarified per-event identity; no other review boundary changed)

## Dependencies

- No external wave dependencies.
