# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-07-15
review-evidence-source: events.jsonl

wave-id: `1snq3 credible-threat-gate`
Title: Credible Threat Gate

## Objective

Add a conjunctive credible-threat gate to the executable-review-evidence protocol so security severity, blocking, and approval freshness are driven only by grounded, attacker-reachable findings under Wavefoundry's documented threat model — cutting false-positive security escalation without weakening discovery. When this wave closes, the threat model is documented, seeds 209/213 carry the gate, and the three over-classified `1slep` findings are reclassified as required-contract/correctness (fixes retained).

## Changes

Change ID: `1snq2-enh credible-threat-gate`
Change Status: `complete`

Completed At: 2026-07-15

## Wave Summary

Wave `1snq3` (Credible Threat Gate) delivered one change: Credible-Threat Gate for Security Review. Notable adjustments during implementation: Credible-Threat Gate for Security Review: Implemented AC-1/2/3/5. Threat-model actor classes + credible-threat gate + promotion triggers documented in `threat-model.md` and `SECURITY.md`; five-factor conjunctive gate + symmetric-challenge stance added to seeds `209`/`213` (additive on top of the `1skt1` fact-based severity, which is intact); rendered `docs/agents/security-reviewer.md` stance reconciled. One light authoring check added in `review_evidence.py` (material/critical `authority_delta` must name the capability in `disposition_rationale`), reusing the existing field, no new schema, authoring-time only (historical ledgers untouched).

**Changes delivered:**

- **Credible-Threat Gate for Security Review** (`1snq2-enh credible-threat-gate`) — 4 ACs completed. Key decisions: Use a conjunctive credible-threat gate (all five factors grounded), not an additive risk score.; Keep the gate mostly prose; add at most one light validator check reusing an existing field.
## Reclassification Record — 1slep security findings

Per operator direction (2026-07-15), the three findings below from the **closed** `1slep external-wave-event-ledger` wave are re-characterized as **required-AC / correctness** findings — not attacker-reachable security vulnerabilities — under the now-documented trusted-operator threat model (`docs/architecture/threat-model.md`, `docs/SECURITY.md`). The corrected classification is recorded here in the active wave; `1slep`'s closed ledger is intentionally left immutable because closed-wave history is not rewritten. Every fix and regression test landed for these findings in `1slep` remains in place — only the security characterization is withdrawn. No council was run and `1slep`'s implementation is not reopened.

| 1slep finding (current head) | Was | Now | Basis under the documented threat model |
| --- | --- | --- | --- |
| `security-wave-directory-symlink-escape` (`syn-security-wave-directory-symlink-escape-6-2`) | `attacker_reachability: true`, `authority_delta: material`, do_now/blocking | `attacker_reachability: false`, `authority_delta: none`, required-AC correctness, do_now retained | Only the operator or a same-user process controls the wave-directory path; no less-trusted actor and no authority beyond the operator's own. Root containment stays a required-AC obligation. |
| `security-reserved-review-metadata-digest-poisoning` (`syn-security-reserved-review-metadata-digest-poisoni-2`) | `attacker_reachability: true`, `authority_delta: material`, do_now/blocking | `attacker_reachability: false`, `authority_delta: none`, required-AC correctness, do_now retained | The registered writer is loopback-only and invoked with the operator's authority; no external caller controls the reserved-metadata request. Rejecting caller-supplied `event_identity`/`request_digest` stays a required-AC integrity obligation. |
| `redteam-adopted-ledger-index-tamper` (`syn-redteam-adopted-ledger-index-tamper-10-2`) | `attacker_reachability: true`, `authority_delta: material`, do_now/blocking | `attacker_reachability: false`, `authority_delta: none`, required-AC correctness, do_now retained | Only the operator or a same-user process can tamper the local source declaration; no less-trusted actor controls it. Retained-adoption index exclusion stays a required-AC obligation. |

Each finding remains `do_now` on required-AC grounds (`contract_relevance: required_ac`), so the corrected characterization does not weaken the obligation to have fixed it — it only withdraws the unestablished security-severity claim.

## Journal Watchpoints

- Resolved: `1slep` is closed and `1snq3` is OPEN (it took the single OPEN slot after `1slep` closed). The earlier "cannot activate until 1slep closes" blocker no longer applies.
- Resolved: the seed stance change BUILT ON, not reverted, the `1skt1` seed-213 severity reconciliation (verified — the `1skt1` fact-based severity line is intact and the gate composes as a precondition).
- Watchpoint: keep the generic security seeds (209/213/229) **project-neutral** — no project-specific trust classes (delivery review caught one WF-specific assumption in generic seed 213 and it was removed); project specifics live only in `threat-model.md`/`SECURITY.md` and the rendered project surfaces.
- Watchpoint: mechanization stayed minimal — **no** `review_evidence.py` validator check and no new schema fields; the capability-naming requirement is reviewer-owned semantic guidance in the seeds.
- Resolved: the three `1slep` reclassifications are recorded as a **decision record** in this `wave.md` (`## Reclassification Record`), citing the landed threat-model docs; the closed `1slep` ledger is not reopened or mutated and no council was commissioned for the correction.

## Finding Synthesis

<!-- waveframework:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| — | — | — | — | — |

<details class="wavefoundry-review-evidence">
<summary>Machine review evidence — 6 records; 2 runs; 0 findings; current: do_now 0, maybe_later 0, dont_do_later 0, not_issue 0</summary>
</details>
<!-- waveframework:finding-synthesis end -->

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-07-15: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: the append-only reclassification of the three `1slep` findings is a full finding-event re-author rather than a one-field flip, and the adoption proof must re-advance via `record_protocol_state` or validation reports an unadopted suffix — both are implementation notes, not readiness blockers; strongest-alternative: none material)
- Council conduct + per-seat evidence: run as one consolidated independent, code-grounded pass by a fresh reviewer with no prior-conclusion context, applying the red-team claim-falsification and docs-contract seed/doc-feasibility lenses; the change is small and twice prior-reviewed, so the seats were run as one isolated independent pass. red-team — every load-bearing premise verified against the tree: the three findings exist with the claimed `attacker_reachability:true` / `authority_delta:material` heads; `attacker_reachability` / `authority_delta` / `disposition_rationale` are real `_SYNTHESIS_REQUIRED` fields and `disposition_rationale` is already required non-empty, so "reuse it, no new field" holds; seeds 209/213 already derive severity from facts, so the credible-threat gate is a composable precondition and does not revert `1skt1`; append-only supersession keeps `do_now` via `required_ac` and derives focused non-council review depth. docs-contract-reviewer — `threat-model.md` / `SECURITY.md` / AGENTS.md support the trusted-operator model; the seed-213 edit must be diffed against the `1skt1` baseline, which AC-2 covers. Verdict: READY-WITH-NOTES, no blockers.

- **Delivery Wave Council [wave-council-delivery] — 2026-07-15: NEEDS-REVISION → repaired** (operator-conducted delivery review). Four do-now findings, all repaired in-session:
  - **P1 (carrier consistency):** generic security seeds were inconsistent — seed 229 still carried "assume every trust boundary is exploitable"; seed 213 had Wavefoundry-specific trust classes (a project-specific assumption in a generic seed) and a location-based "all repository/filesystem content is untrusted" rule contradicting the provenance default; and seeds 209/213 gave no safe behavior when a target project's threat model is missing. Fixed: seed 229 + rendered `security-engineer.md` reconciled to the symmetric gate; generic 213 de-Wavefoundry-ified (project specifics live only in `threat-model.md`/`SECURITY.md`/the rendered surface); repository-content trust made provenance-based; and a missing-model rule added — a directly evidenced external actor grounds the gate even with no docs (recording a threat-model documentation gap), unknown local-only cases become `unverified` (never auto-trusted or auto-attacker-reachable).
  - **P1 (validator not substantive):** the 24-character `disposition_rationale` floor was bypassable (generic 50-char prose passed) and rejected valid concise bases ("read API keys"). Fixed: removed the character-count check and constant entirely; the capability-naming requirement is now a reviewer-owned semantic requirement stated in the seeds (the plan permits adding no validator check).
  - **P1 (pre-implementation gate):** recorded the explicit `pre-implementation-review: passed` mapping below (the prepare-phase council was the actual pre-implementation checkpoint, run before the first code edit — honest chronology, not a retroactive pass).
  - **P2 (stale records):** wave/change records still described the superseded append-only-supersession plan (Wave: TBD, "activate after 1slep closes", ledger-reclassification workstream). Reconciled to the decision-record approach.
- **pre-implementation-review: passed** — mapped to the prepare-phase Wave Council verdict recorded above (2026-07-15 PASS), which ran as the pre-implementation gate before the first code edit when `wave_prepare(mode='create')` opened the wave. No code was edited before that verdict; this is an explicit mapping of the existing checkpoint, not a new retroactive pass.
- **Delivery re-verification — 2026-07-15: PASS.** Focused re-verification after the four repairs over the canonical security carriers (seeds 209/213/229 + rendered surfaces), the two new controls (missing-threat-model external path stays security-affecting; trusted operator-owned local state stays correctness-only), and the rationale behavior (no character-count gate). Full canonical suite green; docs-lint clean. No new broad council run, per operator direction.

## Review Evidence

- operator-signoff: <approved when operator confirms closure>
- wave-council-readiness: approved — Independent fresh-reviewer readiness pass: VERDICT READY-WITH-NOTES, no blockers. Verified the three 1slep findings exist with the claimed attacker_reachability:true/authority_delta:material heads; confirmed attacker_reachability/authority_delta/disposition_rationale are real fields and disposition_rationale is already required non-empty (no new field needed); confirmed seeds 209/213 derive severity from facts so the gate composes without reverting 1skt1; confirmed append-only supersession keeps do_now via required_ac and yields focused (no council) review depth.
- wave-council-delivery: approved — Independent fresh-context delivery review verified derivation untouched, the gate is authoring-time only (not in _validate_synthesis_shape), the 1skt1 severity line is intact, no new schema field, and no silent scope expansion; full suite 5,598 OK; targeted test_review_evidence 68 OK. Verdict approved-with-notes, max severity none, no blockers.
- wave-council-delivery: approved — This supersedes the premature pre-repair council-delivery approval. All four findings repaired: seed 229 + rendered security-engineer.md reconciled to the symmetric gate; generic seed 213 de-Wavefoundry-ified and provenance-based; seeds 209/213 gained missing-threat-model behavior; the character-count check and _AUTHORITY_DELTA_RATIONALE_MIN_CHARS were removed (capability-naming is reviewer-owned semantic guidance); pre-implementation-review:passed mapped to the prepare council; wave/change records reconciled to the decision-record approach. Two new controls pass (missing-model external stays security-affecting; trusted operator-owned stays correctness-only); concise 'read API keys' basis accepted. Full suite 5,598 OK; targeted test_review_evidence 68 OK; docs-lint clean.
- operator-signoff: approved — Operator final re-review PASS: seeds 209/213/229 consistent/project-neutral/provenance-based with safe missing-model handling; character-count validator removed (capability grounding reviewer-owned); both external-actor and trusted-operator controls pass; pre-implementation chronology honestly recorded; change status/wave metadata/decision-record wording reconciled; latest delivery approval fresh, independent, supersedes the premature one. Independent checks: test_review_evidence 68/68 OK, docs-lint clean, git diff --check clean, close dry-run blocks only on operator signoff.

## Dependencies

- Was sequenced after `1slep external-wave-event-ledger` for the single OPEN slot; `1slep` is now closed and `1snq3` is OPEN, so that ordering is satisfied. No code dependency — the reclassification decision record reads the `1slep` ledger but does not require or mutate its implementation.
