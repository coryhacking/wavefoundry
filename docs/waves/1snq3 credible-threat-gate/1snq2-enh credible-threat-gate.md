# Credible-Threat Gate for Security Review

Change ID: `1snq2-enh credible-threat-gate`
Change Status: `complete`
Owner: Engineering
Status: complete
Wave: `1snq3 credible-threat-gate`
Last verified: 2026-07-15

## Rationale

The executable-review-evidence protocol (wave `1skt1`) inherited an aggressive security stance — effectively "assume every trust boundary is exploitable." Applied to Wavefoundry's own work it over-classified **trusted-operator / same-user integrity issues** as attacker-reachable P1 security vulnerabilities. The `1slep` ledger contains three such current-head findings — `security-wave-directory-symlink-escape`, `security-reserved-review-metadata-digest-poisoning`, and `redteam-adopted-ledger-index-tamper` — each asserting `attacker_reachability: true` and `authority_delta: material` even though the only actor who controls the affected file/state is the operator, who already has full filesystem authority. Those are real **required-contract / correctness** findings (worth the fixes, which stay) but not demonstrated security vulnerabilities under this project's threat model.

Wavefoundry's actual threat model (see `docs/architecture/threat-model.md`, `docs/SECURITY.md`): the repository filesystem is trusted, target roots are operator-approved, network surfaces are loopback-only, and Wavefoundry runs with the operator's own authority — not a more privileged identity. A defect the operator (or a same-user process) could trigger, using capabilities the operator already has, is not an authority escalation.

This change adds a **conjunctive credible-threat gate** so only grounded findings drive severity, blocking, and approval freshness — without weakening discovery. It preserves aggressive candidate-finding while preventing same-authority, theoretical scenarios from consuming implementation and council rounds. It is a small, mostly-prose follow-up; it deliberately does **not** add schema fields or a mechanized multi-factor gate, because that would feed the per-finding authoring burden the protocol is separately trying to reduce.

## Requirements

1. **Document the threat model explicitly** in `docs/architecture/threat-model.md` and `docs/SECURITY.md`: Trusted — operator, operator-owned repository contents, same-user local processes. Untrusted — genuinely external callers or content explicitly accepted from third parties. Out of scope today — malicious same-user concurrent processes and privilege-separated attackers. Promotion triggers (any one flips the posture): remote/non-loopback MCP or network binding, multi-user service operation, untrusted-repository analysis, CI on untrusted/forked pull requests, or execution under credentials unavailable to the caller. "External" includes untrusted archives, webhook payloads, third-party repositories, forked-PR CI, plugins, imported configuration, and shared-workspace users when a less-trusted actor controls them.
2. **Add the credible-threat gate as guidance** to the shared security stance in seed `209` and the security-reviewer seed `213` (building on — not undoing — the seed-213 severity reconciliation already made in `1skt1`). A credible security threat requires ALL five factors grounded: (a) a named less-trusted actor; (b) input/file/request/repository/state that actor controls; (c) a supported product path that accepts it; (d) an authority or asset delta — something the program can do or access that the actor cannot already; (e) a concrete confidentiality/integrity/availability/privilege impact. Severity is assessed only after this gate passes; it is a conjunctive gate, not an additive risk score.
3. **Make the challenge symmetric.** Change the stance from "assume every trust boundary is exploitable" to "challenge every *evidenced* trust boundary; do not invent one — and do not invent *trust* either: establish that no less-trusted actor controls the path before labeling something operator-only." Reviewers may report security candidates freely; only grounded findings affect severity, blocking, or approval freshness.
4. **Minimal field rules (at most one light validator check; no new schema fields).** In review guidance and, only if a check is added, in `review_evidence.py`: `attacker_reachability: true` is rejected/challenged when the named actor is trusted or absent from the threat model; `authority_delta ∈ {material, critical}` must name the specific capability/asset the actor otherwise lacks, reusing the existing `disposition_rationale` field (do not add `actor`/`entry_point`/`threat_model_citation` fields); operator-owned repository content defaults to trusted unless the project declares an untrusted-repository mode.
5. **Reclassify the three `1slep` findings** by append-only supersession in that wave's ledger: `attacker_reachability → false`, `authority_delta → none`, re-ground `contract_relevance` to `required_ac` (root containment; ledger append-only/tamper-evidence integrity), keep `disposition: do_now` and every existing fix and regression test. This is a classification correction only — no implementation reopen and no council, per the convergence rules for a repair that does not change the fix.
6. **Bound the follow-up.** Unresolved threat validation is limited to one bounded pass; further expansion requires an explicit operator decision, not another autonomous review cycle.

## Scope

**Problem statement:** The protocol's security stance lets unsupported `attacker_reachability`/`authority_delta` values be asserted without a grounded basis, over-classifying same-authority integrity/correctness issues as attacker-reachable security vulnerabilities.

**In scope:**

- Threat-model documentation (trusted/untrusted/out-of-scope/promotion triggers) in `threat-model.md` + `SECURITY.md`.
- The conjunctive credible-threat gate and symmetric-challenge stance as prose in seeds `209` and `213`, plus rendered security-reviewer surface reconciliation.
- At most one light validator check reusing existing fields (`authority_delta` material/critical requires a non-empty capability basis in `disposition_rationale`).
- Append-only reclassification of the three identified `1slep` findings.

**Out of scope:**

- New evidence-record schema fields or a mechanized multi-factor gate (would grow the per-finding authoring burden).
- Re-auditing historical closed waves or re-running councils on reclassified findings.
- Changing which specialist lanes own the security, architecture, performance, or QA verdicts.
- Weakening containment/append-only implementations or their regression tests (the fixes stay; only the characterization changes).
- Any change to network exposure, multi-user, or untrusted-repository handling (those are promotion-trigger futures, not this change).

## Acceptance Criteria

- [x] AC-1: `threat-model.md` and `SECURITY.md` state the trusted/untrusted/out-of-scope sets and the promotion triggers (including remote/non-loopback MCP), and a reviewer can cite them to justify a trust classification.
- [x] AC-2: Seeds `209` and `213` state the five-factor conjunctive gate and the symmetric-challenge stance, reconciled with (not reverting) the `1skt1` seed-213 severity reconciliation; the rendered security-reviewer surface matches.
- [x] AC-3: Guidance requires `attacker_reachability: true` to name a less-trusted actor present in the threat model, and `authority_delta ∈ {material, critical}` to name the specific capability/asset in `disposition_rationale`; operator-owned repo content is trusted by default. Any added validator check reuses existing fields and adds no new schema field. **Implemented as reviewer-owned semantic guidance in seeds `209`/`213`/`229` with NO validator check** — a prose-length floor was prototyped then removed in delivery review (bypassable by generic filler, over-strict on valid concise bases like "read API keys"); the plan permits adding no check. Trust is provenance-based (not file location); a directly evidenced external actor grounds the gate even when a project's threat model is missing (recording the documentation gap), and unknown local-only surfaces are `unverified` (never auto-trusted or auto-attacker-reachable).
- [~] AC-4: **Narrowed by operator direction (2026-07-15):** the three `1slep` findings are reclassified to `attacker_reachability: false`, `authority_delta: none`, required-AC/correctness (do_now retained, fixes/tests preserved) — but recorded as a **decision record in this wave's `wave.md` (## Reclassification Record)**, NOT by appending repair cycles to the closed `1slep` ledger. The ledger's only head-changing mechanism is a `repair_start → reverification` repair cycle; applying it to a closed wave would rewrite shipped history and recreate the review loop this change avoids. Closed-wave history is left immutable per project policy. No council run; no implementation reopened.
- [x] AC-5: Full canonical framework tests and docs lint pass; a negative fixture proves a grounded external-actor finding is still severity-affecting (the gate reduces false positives, not real findings).

## Tasks

- [x] Write the threat-model and SECURITY sections (trusted/untrusted/out-of-scope/promotion triggers, incl. MCP).
- [x] Add the conjunctive gate + symmetric-challenge stance to seeds `209`/`213`; reconcile the rendered security-reviewer surface.
- [x] Add at most one light `review_evidence.py` check reusing `disposition_rationale`; add its fixture plus a grounded-external-finding negative control.
- [~] Supersede the three `1slep` findings via the typed authoring tool (classification-only correction) and confirm ledger + projection. **Narrowed:** recorded as a decision record in `1snq3` `wave.md` (## Reclassification Record); the closed `1slep` ledger is left immutable per operator direction (see AC-4).
- [x] Run targeted tests, the full bytecode-free suite, and docs lint.

## Agent Execution Graph


| Workstream     | Owner  | Depends On   | Notes |
| -------------- | ------ | ------------ | ----- |
| threat-model-and-stance | implementer | — | Docs + seed 209/213/229 gate prose (generic seeds stay project-neutral; provenance-based trust; missing-model behavior; symmetric challenge) + rendered security-reviewer/security-engineer surfaces |
| minimal-field-rule | implementer | threat-model-and-stance | **Outcome: no validator check** — the capability-naming requirement is a reviewer-owned semantic requirement in the seeds; a prose-length floor was prototyped then removed in delivery review (bypassable + over-strict) |
| reclassification-record | implementer | threat-model-and-stance | **Decision record** in `1snq3` `wave.md` (`## Reclassification Record`); the closed `1slep` ledger is left immutable (operator direction) |
| verification | qa-reviewer | all above | Controls: missing-model external path stays security-affecting; trusted operator-owned state stays correctness-only; concise capability basis accepted (no length gate); full suite + lint |


## Serialization Points

- Seed `209`/`213`/`229` gate prose must stabilize before the rendered security-reviewer and security-engineer surfaces are reconciled.
- The threat-model documentation must land before the `1slep` reclassification **decision record** in `1snq3` `wave.md` cites it as the basis (the closed `1slep` ledger is not mutated).

## Affected Architecture Docs

- `docs/architecture/threat-model.md` — trusted/untrusted/out-of-scope sets and promotion triggers.
- `docs/SECURITY.md` — operator-facing posture and the credible-threat gate summary.
- No boundary/flow change to `data-and-control-flow.md`; ADR only if the field-level check is deemed a durable contract choice.

## AC Priority

(Populated at Prepare wave.)


| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The gate is meaningless without a written threat model to cite. |
| AC-2 | required | The stance change is the mechanism; it must not revert `1skt1`'s seed-213 work. |
| AC-3 | required | Prevents ungrounded severity while avoiding new per-finding fields. |
| AC-4 | required | Corrects the standing over-classification in the shipping ledger. |
| AC-5 | required | Proves the gate cuts false positives without suppressing real findings. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-15 | Planned from operator direction after a proportionality review found three `1slep` findings over-classified as attacker-reachable security P1s under a trusted-operator/same-user threat model. The fixes stay; only the security characterization is withdrawn, and the framework gains a credible-threat gate. | `1slep` ledger audit: `security-wave-directory-symlink-escape`, `security-reserved-review-metadata-digest-poisoning`, `redteam-adopted-ledger-index-tamper` all assert `attacker_reachability: true` + `authority_delta: material` with the operator as the only controlling actor; `threat-model.md`, `SECURITY.md`, `AGENTS.md` safety rules. |
| 2026-07-15 | Implemented AC-1/2/3/5. Threat-model actor classes + credible-threat gate + promotion triggers documented in `threat-model.md` and `SECURITY.md`; five-factor conjunctive gate + symmetric-challenge stance added to seeds `209`/`213` (additive on top of the `1skt1` fact-based severity, which is intact); rendered `docs/agents/security-reviewer.md` stance reconciled. One light authoring check added in `review_evidence.py` (material/critical `authority_delta` must name the capability in `disposition_rationale`), reusing the existing field, no new schema, authoring-time only (historical ledgers untouched). | Seeds 209 §"Credible-threat gate", 213 §"Credible-Threat Gate"; `review_evidence.py` `_AUTHORITY_DELTA_RATIONALE_MIN_CHARS`; 3 new tests in `test_review_evidence.py` (grounded-external stays do_now/blocking; vacuous material claim rejected; none-delta reclassification unaffected) — targeted 68/68 OK; `wave_validate` docs-lint ok. |
| 2026-07-15 | AC-4 narrowed by operator direction: reclassification recorded as a decision record in `1snq3` `wave.md`; closed `1slep` ledger left immutable (history not rewritten). | Operator selected "record in 1snq3, leave 1slep immutable" when the ledger's only head-changing mechanism (a `repair_start → reverification` repair cycle) would have rewritten the closed wave. See `## Reclassification Record` in `wave.md` and the Decision Log. |
| 2026-07-15 | Delivery review (operator-conducted) returned needs-revision with four do-now findings; all repaired in-session. Reflect: generic seeds must stay project-neutral (a WF-specific assumption slipped into generic seed 213 — review-wave.prompt.md:30 flags exactly this); prose-length heuristics are the wrong tool for a semantic requirement. | (P1) seed 229 + rendered `security-engineer.md` reconciled to the symmetric gate; generic seed 213 de-Wavefoundry-ified with provenance-based (not location-based) content trust; seeds 209/213 gained missing-threat-model behavior (evidenced external actor still grounds the gate + records a doc gap; unknown local-only → `unverified`). (P1) removed the character-count validator check + `_AUTHORITY_DELTA_RATIONALE_MIN_CHARS`; capability-naming is now reviewer-owned semantic guidance; controls updated (concise "read API keys" accepted; generic filler not machine-rejected). (P1) recorded explicit `pre-implementation-review: passed` mapping to the prepare council. (P2) reconciled wave/change records to the decision-record approach (Wave set, execution graph + serialization + watchpoints + dependencies updated). Targeted `test_review_evidence` 68 OK. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-15 | Use a conjunctive credible-threat gate (all five factors grounded), not an additive risk score. | An additive score lets weak signals accumulate into false severity; a gate requires every factor to be real. | Keep the additive/aggressive stance — rejected as the source of the over-classification. |
| 2026-07-15 | Keep the gate mostly prose; add at most one light validator check reusing an existing field. | Mechanizing a multi-factor gate would add schema fields and grow the per-finding authoring burden the protocol is separately reducing. | Full mechanized gate with `actor`/`entry_point`/`threat_model_citation` fields — rejected as burden-additive. |
| 2026-07-15 | Make the challenge symmetric: challenge invented boundaries AND invented trust. | Rejecting `attacker_reachability: true` for trusted actors must not become a rubber stamp that suppresses real findings where untrusted input reaches a supported path. | One-directional "don't invent boundaries" only — rejected as suppression-prone. |
| 2026-07-15 | Reclassify the three `1slep` findings as required-contract/correctness via append-only supersession; keep the fixes. | The defects and repairs are real; only the security severity was unestablished. | Reopen `1slep` implementation / new council — rejected as the review-loop this avoids. Rewrite ledger history — rejected as non-append-only. |
| 2026-07-15 | Put the framework-wide policy here, not in `1slep`. | Expanding `1slep` again would recreate the exact review-loop problem. | Fold into `1slep` — rejected. |
| 2026-07-15 | Record the three-finding reclassification as a decision record in `1snq3` `wave.md`; leave the closed `1slep` ledger immutable. | The ledger's only head-changing mechanism is a `repair_start → reverification` repair cycle; applying it to a closed wave would rewrite shipped history and recreate the review loop this change avoids. Project policy does not rewrite closed-wave history. Typed findings in `1snq3` were also rejected because a real required-AC finding derives `do_now`, which would inject phantom repair work into `1snq3` for fixes already landed in `1slep`. | Append repair cycles to the closed `1slep` ledger — rejected (history rewrite). Author typed `1snq3` findings — rejected (phantom do_now work). |
| 2026-07-15 | Do not add a lightweight reclassify-without-repair run kind for open waves now. | For open waves the existing `repair_start → reverification` cycle already updates a finding head during normal iteration; a reclassification-only affordance would grow the schema surface this effort is trimming, and the need is first-seen and rare. | Add a reclassification run kind — deferred to an explicit small wave if the pattern recurs. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| The gate is misused to suppress a genuine external finding by mislabeling the actor as trusted | Symmetric challenge: require establishing that no less-trusted actor controls the path; AC-5 negative control proves grounded external findings still affect severity. |
| The stance change accidentally reverts `1skt1`'s seed-213 severity reconciliation | Explicit reconcile task and AC-2; diff-review the seed-213 changes against the `1skt1` baseline. |
| "Trusted repo content" is over-applied where Wavefoundry treats repo content as executable/authoritative | Scope the default to repo content read as data; promotion trigger covers untrusted-repository analysis; note config/inputs that drive behavior remain operator-owned. |
| Mechanizing the gate reintroduces per-finding burden | Cap at one check reusing `disposition_rationale`; no new fields (out-of-scope boundary). |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
