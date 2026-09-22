# Review Prompt Efficiency Readiness Review

Owner: Engineering
Status: active
Last verified: 2026-09-22

Phase: readiness. Context: `review-prompt-efficiency-readiness-20260922`. This reviews the three plans, not delivered behavior; nothing is implemented.

## Council

Seats ran in separate fresh contexts against the admitted change docs, the wave record and the readied sibling wave `1ypy6` (for collisions): `red-team` (fixed) and `docs-contract-reviewer` (rotating, bound to the receipt). The code-reviewer, qa-reviewer and architecture-reviewer readiness lanes ran in the same round, fresh and independent. Every seat verified plan claims against the tree (the receipt and digest code, the review-evidence projection, the carrier renderer and its registry, the seeds, the surfaces, the templates, the goldens and the test modules) rather than the plans' prose.

Strongest challenge (all five, independently): the receipt-delta requirement promised a per-document and per-section attribution that the receipt cannot yield, because `policy_input_digest` stores one aggregate hash under a closed schema and nothing persists the previous canonical bodies, while `receipt_supersession_attribution` already emits `review_policy_receipt_superseded` with an honest not-attributable sentence and message pins. Two planned cuts contradicted closed waves' landing pins: the owned block's independence-code paragraph is cross-pinned to the validator constants (wave `1tmb2`), and the mutation-table paragraph is pinned in three seeds and three role docs (wave `1wuju`).

Strongest alternative (architecture): persist the per-change digests the tool already computes as one optional, non-semantic receipt field, kept out of `receipt_semantic_fields` so receipt ids, ledgers and goldens do not move, and extend the existing helper rather than adding a code. Adopted, with the prepare envelope stripping the field so both lifecycle goldens stay unchanged, and with the block keeping the three code names in one sentence so the cross-pin holds.

## Findings and repair

Blocking in the first round, all repaired in one rewrite pass:

- Tools: per-document attribution needs the optional `policy_inputs` field; section-level attribution dropped; the existing code and helper reused with their `wf_mark_ac` and dry-run pins intact; emit sites and the pre-publication capture of `receipt_append_required` named; the status-row wording keyed on `receipt_binding_applies` inside `review_authority_projection` (the residue guard forbids the helper in the server module); the ephemeral check given a token grammar, a root list and its layering (predicate in the validator module, advisory appended to `stale_warnings` on both branches); the registry symbol corrected to `REVIEW_PROTOCOL_CARRIER_REGISTRY` plus native wrappers; seven test modules and the tool-surface spec added to serialization points; both lifecycle goldens named.
- Seeds: the Typed authoring shrink would have deleted the writing-hand sentence `1ypy6` adds, so the four removed enumerations are named and everything else kept; the mutation-table cut names and rewrites the `1wuju` seed pin; `tree_fingerprint` is already a required packet field; the `agent-team-workflow.md` reference is an expected carrier in ten other seeds and the item is withdrawn; counts re-derived (three "exceptional" sites, one literal plus three paraphrases); the de-localization rules for seeds 214 and 221 stated; the census predicate records pre-existing product mentions.
- Surfaces: the memory-capture collapse keeps the `memory_add(status='candidate'` literal; the role-doc pin literals are split into kept and updated; the template packet clause becomes a pointer per seed 100 item 13; the template gains its first content pin; the three step-2 literals and the retired tokens to avoid are named.
- Wave record: architecture-reviewer added to the lanes (recruited by the architecture doc path); the re-render is marker-region only; the receipt disposition path named as expected, not pre-decided, with operator review.

## Focused verification

Two fresh verifiers checked the rewritten packet against the tree. Every original block resolved. The code verifier found three text-level items in the tools plan, folded before this record was written: the attributable message must keep the literal clause the two existing pins assert, the code sentence must contain the literal `not caller`, and the advisory must not fire on a genesis receipt (gate on `supersedes_receipt_id`). The docs and QA verifier found two editorial items, folded: `code-reviewer.md` gains rather than keeps the `accel_embedder` case, and the expected-carrier count is ten seeds.

Known-bad detection in this round: every blocking item was detected by a seat or lane reading the tree, the receipts and the test pins, not the plan; the readiness rule of one full review, one bounded repair and one focused verification was followed, and the focused round's findings were plan-text corrections rather than build-changing defects, so approvals were recorded without a further round. Verdict: approved; no readiness blockers remain.

Requested lane settings: host default model and effort for all seats and lanes. Observed runtime identity: unknown.

Limits: no implementation; no test executed this round beyond the QA lane's baseline runs of the carrier, golden and residue-census modules (all green); the collision analysis against `1ypy6` is by reading its plans, and the seed inventory re-verifies every anchor after that wave lands.
