# 209 — Agent Harness Core

Owner: Engineering
Status: active
Last verified: 2026-07-14

## Purpose

Define the shared contracts that all harness participants use: evidence grounding, briefing packet format, finding record schema, reachability labels, and coordination behaviors.

## Evidence Grounding

| Source | Weight | Rule |
|--------|--------|------|
| Repository evidence (code, docs, configs, wave records) | Highest | Prefer over memory, assumptions, or inferred behavior |
| Stricter project rule in `docs/` | Wins over framework default | When a project-specific rule contradicts a generic framework default, the project rule applies in that context |
| Missing docs | Gap to record | Do not assume absence means absence of constraint; record the gap as a finding |

Separate facts (evidenced in the repository), inferences (derived from patterns), and unknowns (no evidence found) in all outputs.

## Briefing Packet

A briefing packet is the structured context shared with every council seat or review lane before it runs in isolation.

**Required fields:**

| Field | Description |
|-------|-------------|
| `wave_id` | Active wave identifier |
| `phase` | `readiness` or `delivery` |
| `change_ids` | List of admitted change IDs in scope |
| `trust_boundaries_touched` | Which trust or security boundaries this wave crosses |
| `files_in_scope` | File paths or glob patterns directly modified by the wave |

**Optional fields:**

| Field | Description |
|-------|-------------|
| `architecture_refs` | Relevant architecture docs consulted |
| `prior_artifacts` | Prior review outputs, journals, or prior-wave findings that are still relevant |
| `explicit_non_goals` | What is intentionally out of scope |
| `recommended_model_tier` | Suggested model capability tier for complex seats |

The briefing packet is assembled once per phase (readiness or delivery) before any seat runs. Seats must not expand the briefing packet; they may flag missing evidence as a gap.

## Finding Record Schema

Every finding produced by any harness participant must use this schema:

| Field | Required | Description |
|-------|----------|-------------|
| `finding_id` | Yes | Stable identifier, e.g. `SEC-001`, `CODE-003` |
| `file` | Yes | Repo-relative path |
| `lines` | Yes | Line range, e.g. `42-48` |
| `class` | Yes | Vulnerability or defect class (e.g. `path-traversal`, `missing-branch`, `complexity-regression`) |
| `summary` | Yes | One-line description of the finding |
| `reachability` | Yes | One of the reachability labels below |
| `confidence` | Yes | `high`, `medium`, or `low` — reviewer confidence in the finding |
| `severity` | Yes | `critical`, `high`, `medium`, `low`, or `none` |
| `recommended_fix` | Yes | What should be done to resolve the finding |
| `components` | No | For exploit-chain findings: list of contributing component finding IDs |

## Executable Review Evidence Protocol

This protocol is the canonical contract for material approval claims and blocking findings. Role seeds carry short obligations back to this section; they must not invent a second evidence schema or a different disposition rule.

The protocol is **prospective and additive**. Existing finding and approval records remain valid. After a project or wave adopts this protocol, every material approval claim or blocking finding adds an Executable Evidence Record linked to the original record; it does not replace the Finding Record Schema. `inferred`, `unverified`, and `not_applicable` evidence cannot satisfy a required delivery approval claim.

### Executable Evidence Record

| Field | Required | Contract |
|-------|----------|----------|
| `record_type` | Yes | Literal `executable_evidence` in the wave's sibling `events.jsonl` ledger |
| `evidence_record_id` | Yes | Wave-unique append-only identifier referenced by Review Run/Finding Synthesis records |
| `claim_id` | Yes | Stable ID of the linked finding; approval evidence uses exactly `approval:<signoff-key>` |
| `claim_kind` | Yes | `finding`, `approval`, `dedup`, `lane_reassessment`, or `census` |
| `required_for_approval` | Yes | Boolean; true makes executed delivery evidence mandatory |
| `phase` | Yes | `readiness` or `delivery` |
| `proposition` | Yes | One falsifiable statement being checked |
| `counterexample_or_failure_condition` | Yes | State or observation that would disprove the proposition |
| `execution_status` | Yes | `executed`, `inferred`, `unverified`, or `not_applicable` |
| `public_path` | Yes | Registered tool, CLI entry point, endpoint/process, lifecycle gate, or real parser/subprocess boundary exercised; name the closest faithful boundary when the public path cannot be run safely |
| `command_or_fixture` | Yes | Reproducible command, fixture, or probe identifier; redact secrets |
| `expected` | Yes | Expected result under the contract |
| `observed` | Yes | Actual result; do not replace with “passed” |
| `artifact_or_test_id` | Yes | Durable log, test, fixture, or artifact identifier |
| `adjacent_controls` | Yes | Legitimate-state or baseline controls run beside the counterexample; may be an empty list with rationale |
| `test_ran_without_unintended_skip` | Yes | Boolean evidence-integrity result |
| `public_path_reached` | Yes | Boolean evidence-integrity result |
| `boundary_values_realistic` | Yes | Boolean evidence-integrity result |
| `assertions_non_vacuous` | Yes | Boolean evidence-integrity result |
| `known_bad_detected` | Yes | Boolean; true only when the pre-fix/focused-mutation/injected-old behavior failed as intended |
| `known_bad_detection_method` | Yes | The pre-fix, focused-mutation, injected-old-behavior, or closest safe method used |
| `limitations` | Yes | Residual uncertainty, unavailable paths, truncation, or tool failures |
| `safety_and_authorization` | Yes | Why the probe is authorized and safe, or why execution stopped at a faithful boundary |
| `probe_class` | Yes | `local_safe`, `external_or_destructive`, or `none` |
| `authorization_status` | Yes | `authorized`, `not_authorized`, or `not_required`; external/destructive execution requires `authorized` |
| `safe_boundary` | Yes | Boolean; true only for an inferred faithful-boundary demonstration |
| `unexecuted_remainder_prohibited` | Yes | Boolean; required with `safe_boundary: true` and otherwise false |
| `universal_claim` | Yes | Boolean; true requires the closed census object below |
| `verification_context.actor` | Yes | Exact authority that produced the evidence: the specialist lane name for specialist approval/reassessment, `wave-council` for council approval, or `operator` for operator approval |
| `verification_context.context_id` | Yes | Stable run/context identifier |
| `verification_context.fresh_context` | Yes | Boolean; true only when no implementation/recheck context was retained |
| `verification_context.independent` | Yes | Boolean; true only when the reviewer did not implement the repair and formed its own current-tree/test assessment before relying on prior findings, evidence claims, or verdicts |

Mandatory project orientation may disclose status or review history (for example, through `AGENTS.md` or a required session handoff) without making an otherwise fresh review ineligible. That orientation is context, never proof: the reviewer must inspect and execute the current artifacts, form its own assessment, and cite that evidence before relying on earlier conclusions. Copying, accepting, or using an earlier finding or verdict as the basis of the assessment is not independent verification.

Universal claims add a `census` object with exactly: `claim`, `boundary`, `inclusion_policy`, `tools_and_queries`, `enumerated_sites`, `total_count`, `registration_checks`, `exclusions`, `result_truncated`, `index_freshness`, `tool_errors`, `residual_uncertainty`, `residual_uncertainty_status`, and `universe_closed`. `index_freshness = current | stale | unknown`; `residual_uncertainty_status = none | bounded | unresolved`. A failed, truncated, stale, uncertain, unknown, or unclosed universe is `unverified`. Narrow the proposition rather than present sampled evidence as proof of “all”, “every”, or “no other site”.

### Typed authoring and human view

Use `wave_record_review_evidence` instead of hand-serializing JSONL when MCP is available. The tool accepts `approval`, `finding`, and empty lightweight `run` events, previews by default, and writes only with `mode: create`. For a finding, the reviewer must explicitly provide the ten load-bearing judgment facts: `validation_status`, `scope_relation`, `introduced_or_worsened_by_wave`, `contract_relevance`, `supported_reachability`, `attacker_reachability`, `authority_domain`, `authority_delta`, `observable_impact`, and `containment`. A real proposition that is not already action-required must additionally provide the repair/proportionality facts that distinguish `maybe_later` from `dont_do_later`. The tool never guesses those judgments; it derives only IDs, integrity expansion after explicit confirmation, actionability, disposition, blocking, review depth, supersession, cycle linkage, and append ordering.

The fixed sibling `events.jsonl` remains the canonical append-only authority because evidence includes nested lists, verification contexts, optional census objects, and conditional waiver/reassessment fields that do not have a stable Markdown-table encoding. The tool generates a concise Markdown table/summary of current finding heads in `wave.md`; that projection is presentation only, and the next locked typed write or reconciler refreshes it from the ledger. A one-candidate run may reuse its finding evidence as the sealed-universe proof. An empty `lightweight` readiness/initial-delivery run emits one Review Run row with reviewer `verification_context` and no separate dedup evidence row.

### Public-path and phase rules

- Exercise the public or registered behavior path when one exists. Helper-only evidence is insufficient when a consumer can miswire, reorder, transform, or bypass the helper.
- **Readiness** may execute existing topology, current defective baselines, caller/render censuses, feasibility, compatibility, and proof that a planned delivery probe is executable. It must not claim that unimplemented behavior ran.
- **Delivery** executes the implemented public path, required-AC evidence, the applicable transition/interleaving matrix, and exact repair replay. Readiness N/A or planned evidence never carries forward as delivery evidence.
- Select a finite risk budget in both phases: `lightweight` permits 0–1 probe (zero only for genuinely non-behavioral work with cited rationale); `standard` requires 1–3 highest-risk public-path probes, including the baseline and highest-risk failure/retry or interleaving for each changed stateful mechanism; `full` requires 3–8 prioritized probes, adding at most one partial-failure/interleaving per changed trust boundary. One parameterized fixture may cover multiple cells. More probes require moderator justification.
- For stateful, persistent, cached, concurrent, recovery, and lifecycle behavior, name the selected transition/interleaving cells. `not_applicable` is per cell and must cite the contract fact proving the state/path does not exist. Time, inconvenience, or unavailable tooling is `unverified`, not N/A.

### Evidence integrity and classification

Before accepting a claimed test, confirm that it runs with zero unintended skips, reaches the claimed production/public path, uses realistic boundary return shapes, contains non-vacuous assertions, and would fail against the known-bad behavior. When reverting a fix is unsafe or expensive, a focused mutation, injected old behavior, or explicit pre-fix fixture demonstration is acceptable. Prompt or phrase presence is contract-presence evidence only; it never proves that an agent followed the protocol.

Classify the observed state before assigning severity: distinguish supported capability absence or a valid degraded state, active-provider failure, malformed/corrupt data, correctness impact, attacker reachability, and authority gained. Severity follows reproducible observable impact, supported reachability, and authority delta—not the defect-class label. Supported no-Git, no-model, or no-index states are not provider failures. An unsupported payload delivered through a supported public entry point still has supported attacker reachability.

### Credible-threat gate — trust classification before security severity

A candidate is a **credible security threat** only when ALL five factors are grounded (a conjunctive gate, not an additive risk score); assess severity only after it passes:

1. **Actor** — a named, less-trusted actor present in the project's documented threat model.
2. **Controlled surface** — an input, file, request, repository, or state that actor actually controls.
3. **Supported path** — a real product path that accepts that surface.
4. **Authority/asset delta** — a capability or asset the program can then reach that the actor could **not already** reach with its own authority.
5. **Concrete impact** — a specific confidentiality, integrity, availability, or privilege consequence.

Set `attacker_reachability: true` only when factors 1–3 hold: the named controlling actor must be less-trusted and present in the threat model. When the only actor who controls the affected surface is the operator, operator-owned repository content, or a same-user process that already holds the program's authority, `attacker_reachability` is `false` — the defect may still be a real `required_ac`/correctness proposition worth fixing, but it does not drive security severity, blocking, or approval freshness. Set `authority_delta ∈ {material, critical}` only when factor 4 holds, and name the specific capability or asset the actor otherwise lacks in `disposition_rationale`; there is no separate actor/entry-point/citation field, so that grounding lives in the rationale. Operator-owned repository content read as data is trusted by default unless the project declares an untrusted-repository mode or another promotion trigger fires (remote/non-loopback binding, multi-user operation, untrusted-repository analysis, forked-PR CI, or execution under credentials unavailable to the caller).

The challenge is **symmetric**: challenge every *evidenced* trust boundary and do not invent one — and do not invent *trust* either. Before labeling a surface trusted-only, establish that no less-trusted actor controls the path; where untrusted input demonstrably reaches a supported path, the gate passes and the finding stands at full severity. Report security candidates freely; only gated findings affect severity, blocking, or approval freshness.

Trust follows **provenance, not file location**: a surface is trusted because a trusted party controls it, not because it lives inside the repository or on the local filesystem. When the project's threat model is **missing or incomplete**, do not fail the gate open or closed: a *directly evidenced* external actor (untrusted input demonstrably reaching a supported path) still grounds factors 1–3 even with no documented model — set `attacker_reachability: true` and additionally record the threat-model documentation gap as a finding. Conversely, a surface whose controlling actor cannot be established from evidence or model is `unverified` — never silently trusted and never assumed attacker-reachable; state the evidence gap rather than guessing either way.

### Safe execution and authority ceiling

Executable review never broadens task authority. Prefer disposable temporary roots, local fakes, and read-only/dry-run public paths. Do not perform destructive or irreversible operations, remote messages, releases, pushes, cost-bearing calls, network calls, or credential-bearing calls without explicit current operator authorization; redact secrets. If the real path cannot be exercised safely, use the closest faithful boundary fixture and label the remaining proposition `inferred` or `unverified`. Exact replay never overrides permissions. Lack of authorization never converts a candidate into `dont_do_later` or `not_issue`.

### Repair re-verification

After a blocking finding is repaired, withdraw only the affected approval until a fresh delivery re-verification reruns the exact original reproduction, runs the named adjacent legitimate-state controls, and checks for a replacement defect. Each synthesis may carry explicit `approval_recheck_lanes`; specialist approval chronology is compared only with later synthesis rows naming that exact lane. Wave Council approval is compared with later full-depth or council-named synthesis, while operator approval remains final-wave scoped. Legacy synthesis rows without the field conservatively derive affected lanes from `source_lanes` plus `blocking_required_lanes`. `fresh_context` and `independent` have the meanings in the Evidence Record above. A reviewer that implemented the repair is not independent even in a new context; a reviewer that retained the implementation/recheck context is not fresh. Required project orientation may be read first, but its status summaries and prior conclusions are not evidence. A withdrawn required-lane approval is restored only by eligible independent evidence. Lane reassessment evidence must be executed in delivery, name the exact reassessing lane as `verification_context.actor`, be fresh and independent, link to that finding, and may clear only one supersession transition. An explicit operator waiver may accept scoped residual risk, but it must record `waiver_id`, `waiver_scope`, `waiver_reason`, and `waiver_risk` and must never be labeled independent confirmation, specialist approval, completion, or unconditional approval.

## Finding Actionability and Review Convergence Gate

Run this ordered state machine after deduplication and evidence collection and before fix scheduling. The moderator records the semantic facts; tools derive actionability, disposition, blocking, and review depth. Fix difficulty or a harmful proposed repair cannot downgrade the underlying proposition: reject the bad repair separately and synthesize the unresolved finding again.

1. `validation_status in {invalid, conforming}` -> `not_issue`. A required AC or public-contract violation is `real`, not `conforming`; absence of observed harm alone never overrides a required contract.
2. `validation_status == real` and derived `action_required == true` -> `do_now`. `action_required` is true exactly when at least one is true:
   - `contract_relevance in {required_ac, public_contract}`;
   - `introduced_or_worsened_by_wave == true` and `supported_reachability == true`;
   - `supported_reachability == true`, `observable_impact in {material, critical}`, and `containment in {detect_only, none, unverified}`; or
   - `supported_reachability == true`, `attacker_reachability == true`, `authority_delta in {material, critical}`, and `containment != preventive`.
3. A remaining `real` proposition -> `maybe_later` only when all are true: `optional_value == positive`, `repair_scope_bounded == true`, `repair_safety == safe`, `scope_relation == admitted`, and `benefit_vs_fix_risk == greater`.
4. Every other `real` proposition -> `dont_do_later`.

`maybe_later` is an assessment category, not an instruction to defer: it means optional-but-worth-doing-now and is completed in-session before closure with focused verification. `dont_do_later` is a deliberate rejection, creates no plan or backlog item, and cannot be selected merely because execution exceeds authorization, no field incident has happened, the repair is difficult, a diagnostic exists, or the first proposed repair is harmful. `not_issue` also creates no follow-on debt.

### Review Run and Finding Synthesis records

Protocol applicability is explicit and monotonic through the exact unversioned wave-header declaration `review-evidence-source: events.jsonl` plus retained adoption state. New waves receive the declaration, an exactly empty sibling `events.jsonl`, a generated Markdown current-state projection, and a zero-record adoption proof at creation. Install, setup, package extraction, and upgrade never scan, parse, migrate, or rewrite target-project historical waves; they deliver the current lifecycle implementation and carriers so the next public wave creation uses this format. The public lifecycle persists each adopted wave's bounded `record_count` plus the domain-separated SHA-256 of its exact canonical prefix in `docs/waves/review-evidence-adoptions.json`. While that project-visible proof is retained, source-declaration removal or downgrade, missing authority, proof-ahead state, prefix replacement, or an unknown unadopted suffix fails closed without invoking Git. An adopted wave must satisfy the complete protocol; its source declaration may not be removed or downgraded, and prior event records may not be edited or removed. Deleting both adoption state and the only declaration destroys every repository-local proof of prior adoption and is indistinguishable from a never-adopted legacy wave; this protocol does not claim tamper-proof persistence against deletion of all local authorities. Protect adoption state with the same source-control, backup, and access policy as the wave records.

Persist append-only, machine-readable JSONL only in the fixed sibling `docs/waves/<wave>/events.jsonl`. `wave.md` contains human narrative plus a generated `## Finding Synthesis` current-head table/summary and is never an independent authority. The ledger uses canonical UTF-8 JSON objects serialized with sorted keys, compact separators, no NaN, and one LF-terminated object per physical line; BOM, CRLF, blank lines, missing terminal LF, malformed/non-object JSON, and noncanonical serialization fail closed. Do not selectively index event fields: structured lifecycle tools read the canonical ledger directly, while semantic retrieval uses the generated Markdown projection. Semantic indexing excludes an exact declared ledger and continues to exclude it when retained adoption proves the wave after a missing or malformed declaration; unrelated and unadopted lifecycle-shaped `events.jsonl` files remain eligible.

- A **Review Run Record** seals the universe checked by the validator: `record_type`, `review_run_id`, `run_kind`, `cycle`, `candidate_finding_ids`, `source_record_ids`, `dedup_evidence_id`, and the conditional `frozen_boundary`, `deviation_ids`, `reopened_finding_ids`, and `verification_context`. An empty lightweight readiness/initial-delivery run uses `dedup_evidence_id: null` and records the reviewer's `verification_context` on that one row; a one-candidate run may point `dedup_evidence_id` at that candidate's executed finding evidence.
- A **Finding Synthesis Record** contains `record_type`, `record_id`, `review_run_id`, `cycle`, optional `supersedes_record_id`, `finding_id`, `validation_status`, `scope_relation`, `introduced_or_worsened_by_wave`, `contract_relevance`, `supported_reachability`, `attacker_reachability`, `authority_domain`, `authority_delta`, `observable_impact`, `containment`, `fix_risk`, `optional_value`, `repair_scope_bounded`, `repair_safety`, `benefit_vs_fix_risk`, `rejection_basis`, `disposition`, `blocking`, `source_lanes`, `blocking_required_lanes`, optional `approval_recheck_lanes`, conditional `lane_reassessment_evidence_id`, all five full-council trigger booleans, `review_depth`, `repair_execution_state`, `evidence_record_id`, `decision_authority`, `disposition_rationale`, and conditional `promotion_trigger`, `waiver_id`, `waiver_scope`, `waiver_reason`, and `waiver_risk`.

Finite domains are authoritative:

- `record_type = executable_evidence | review_run | finding_synthesis`
- `run_kind = readiness | initial_delivery | repair_start | reverification | convergence_checkpoint`
- `validation_status = invalid | conforming | real`
- `scope_relation = admitted | adjacent | outside`
- `introduced_or_worsened_by_wave = true | false`
- `contract_relevance = none | important_ac | required_ac | public_contract`
- `supported_reachability`, `attacker_reachability = false | true | unverified`
- `authority_domain = none | confidentiality | integrity | availability | privilege | unverified`
- `authority_delta = none | low | material | critical | unverified`
- `observable_impact = none | low | material | critical | unverified`
- `containment = preventive | impact_bounding | detect_only | none | unverified`
- `fix_risk = lower | comparable | higher | unverified`
- `optional_value = none | positive | unverified`
- `repair_scope_bounded = false | true | unverified`
- `repair_safety = safe | unsafe | unverified`
- `benefit_vs_fix_risk = greater | equal | less | unverified`
- `rejection_basis = none | categorical | insufficient_evidence | unsupported_reachability | disproportionate_repair`
- `disposition = do_now | maybe_later | dont_do_later | not_issue`
- `blocking = true | false`
- `decision_authority = moderator | required_specialist | operator`
- `review_depth = none | focused | full`
- `repair_execution_state = not_required | pending | completed | operator_waived`

The individually named full-council booleans are `contract_or_required_ac_semantics_changed`, `trust_boundary_changed`, `architecture_or_ownership_changed`, `cross_component_protocol_or_state_changed`, and `failure_or_readiness_semantics_changed`. Probe execution exists only in the linked Executable Evidence Record; do not duplicate it in synthesis rows.

### Derived and lifecycle invariants

- Do not persist a separately authored `action_required`. `observable_impact` is residual supported-path impact after credited containment.
- `blocking` is true exactly when `disposition == do_now` and at least one holds: (a) `contract_relevance in {required_ac, public_contract}`; (b) the wave introduced/worsened it, reachability is supported, and impact is material/critical; (c) reachability is supported, impact is material/critical, and containment is detect-only/none/unverified; or (d) reachability and attacker reachability are supported, authority delta is material/critical, and containment is not preventive. An immaterial supported regression is non-blocking `do_now`. Detect-only diagnostics, logging, retry, or post-effect reporting are never adequate containment for confidentiality, integrity, or privilege gain.
- `do_now` and `maybe_later` require `repair_execution_state == completed` before closure. An explicit operator residual-risk waiver keeps the derived disposition/blocking truth unchanged and records `operator_waived`, `decision_authority: operator`, `waiver_id`, and `waiver_scope`.
- `not_issue` and `dont_do_later` require `repair_execution_state == not_required` and may not carry a follow-on identifier. `do_now`, `maybe_later`, and `not_issue` require `rejection_basis == none`; `dont_do_later` requires a non-`none` rejection basis. `promotion_trigger` is required for `insufficient_evidence`, `unsupported_reachability`, or `disproportionate_repair` and optional for `categorical`.
- `source_lanes` contains every originating lane. `blocking_required_lanes` contains required lanes whose current verdict blocks. A moderator cannot remove or downgrade an entry. Clearing it requires `lane_reassessment_evidence_id` accepted by that lane or explicit operator-waiver fields.
- `approval_recheck_lanes` contains every approval whose review domain the repair plausibly changes, not merely the lane that originated the finding. The moderator must consider affected contracts, trust boundaries, state/failure semantics, and cross-component consumers when selecting it. Approval freshness is finding/lane scoped as defined above; a later unrelated synthesis must not stale an unaffected specialist approval.
- Every Finding Synthesis Record must link to an earlier Executable Evidence Record with `claim_kind: finding` and `claim_id` equal to the synthesis `finding_id`; evidence appended after the synthesis or evidence of another kind cannot authorize it.
- Approval evidence must be executed delivery evidence with `required_for_approval: true`, exact `claim_id: approval:<signoff-key>`, and the matching authority actor. Specialist and Wave Council approval evidence must also be fresh and independent; operator approval is actor-bound to `operator` but is not mislabeled as independent review.
- Derive `review_depth == full` only when a repair changes public-contract/required-AC text, meaning, scope, or acceptance obligation; a trust boundary; architecture/ownership; a cross-component protocol/state model; or failure/readiness semantics. A repair that merely satisfies an unchanged contract does not trigger a full council. All other corrections receive focused re-verification; every blocking repair still receives exact-reproduction replay.

Every Review Run has unique `candidate_finding_ids` and exactly one synthesis row for each sealed candidate and none outside the set. Across runs, each `finding_id` forms one acyclic supersession chain with exactly one unsuperseded wave-current head. Record IDs are wave-unique. Missing/extra rows, duplicate candidates, broken or cyclic supersession, and multiple current heads fail validation. An actionable current head may become `completed` only in a `reverification` or `convergence_checkpoint` run; prose or an earlier repair-start record cannot complete it.

A repair cycle starts when an authoritative post-implementation synthesis contains `do_now` or `maybe_later` and a `repair_start` run is recorded before mutation. It ends at the next bounded `reverification` synthesis for that cycle. Readiness amendments and initial implementation before the first delivery synthesis are not repair cycles; cycle count is monotonic and cannot reset through a fresh council.

When a typed `reverification` completes repair cycle 2 after cycle 1 is already complete, the authoring tool automatically appends the mandatory `convergence_checkpoint` in the same identified event bundle and authority replacement. The caller must not author a second lightweight checkpoint event. The tool derives the checkpoint's `frozen_boundary` from the wave-current synthesis heads after applying that reverification and carries the same verification context; later run records carry unresolved current findings through their candidate set and identify any boundary extension through `deviation_ids` or `reopened_finding_ids`. Review then freezes to exact reproductions, already named adjacent legitimate-state controls, and regressions introduced by the latest repair. Fresh adjacency exploration within existing scope/authority requires `Deviation:` plus moderator acknowledgment; task-scope or authority expansion requires operator authorization. The freeze never suppresses a newly safely evidenced material blocker: executed public-path evidence or a faithful safe-boundary demonstration is sufficient when the only unexecuted remainder is prohibited by the authority ceiling.

One structural validator owns these records. It derives and checks disposition, blocking, repair state, review depth, sealed-candidate completeness, supersession, lane authority, run transitions, cycles, and freeze state. The moderator owns semantic facts; the validator neither declares a proposition true nor approves a wave.

## Reachability Labels

Use exactly these labels (no others):

| Label | Meaning |
|-------|---------|
| `reachable-from-caller-input` | An attacker or untrusted caller can reach this code through normal API or tool inputs |
| `reachable-from-untrusted-content` | The vulnerable behavior is triggered by content read from an untrusted source (e.g. user files, repository content, config) |
| `not-externally-reachable` | The code path is only reachable from internal or trusted caller contexts |

## Harness Behaviors

**Narrow scope:** Each participant reviews only the files and boundaries in scope per the briefing packet. Do not expand scope to adjacent files without recording a `Deviation:` and returning it to the coordinator.

**No self-approval:** Code or changes being reviewed may not be signed off by the author. When the same agent that implemented a change also runs the reviewer lane, record the conflict and escalate.

**Split questions:** Defect questions (is this code correct?) and reachability questions (can an attacker reach this?) are separate. Do not conflate correctness and reachability in a single finding.

**Parallel tasks with merge and deduplicate:** When multiple lanes run concurrently and produce overlapping findings, the coordinator deduplicates by `finding_id` before recording the merged Observe. Two findings with different IDs that describe the same defect must be merged by the coordinator before the next Thought.

**Gapfill pointer:** After all lanes complete, if any evidence referenced in the briefing packet was absent or incomplete, the coordinator records a `Gapfill:` entry in Progress Log noting what was missing and where it should be added before the next wave.

## Project Harness Extensions

<!-- Fill from target repository evidence during upgrade render. Never add product-specific content to this seed body. -->
