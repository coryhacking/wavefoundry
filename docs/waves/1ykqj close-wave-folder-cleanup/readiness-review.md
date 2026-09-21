# Cleanup Readiness Review

Owner: Engineering
Status: active
Last verified: 2026-09-21

Phase: readiness. Plan: `1yk53-enh close-wave-folder-cleanup.md`.
Receipt: `review-policy-deb9e7f6e415a1c70195`.

The current Prepare receipt selects red-team and docs-contract-reviewer, with standard primer depth. This receipt-specific roster controls this review despite the generic Prepare prose describing four other fixed seats. Actual roles: red-team and moderator share one fresh context; docs-contract-reviewer formed an independent verdict in another context. Neither implemented the change. Host-default models and effort were requested; actual model/effort are unknown. No additional independent seats are claimed.

The initial red-team judgment preceded the docs verdict. Standard primer: adversarial stance challenged deletion of a ledger-cited byte-duplicate or unique probe; constructive stance preferred an existing summary/index to a required folder schema; simplicity stance preferred retaining ambiguous files over deletion automation. Strongest challenge: tidying can erase historical evidence even when report prose appears duplicated. Best alternative: retain ambiguous artifacts and index them in the existing report. Questions: (1) must cited duplicates and same-date unrelated reports be preserved unless reference and ownership conditions are satisfied? (2) is a mandatory evidence layout or new report necessary?

Sources checked: current admitted plan and wave through MCP, current Close Wave and Finalize Feature public prompts through `wf_get_prompt`, and canonical seed 190 task 16 (line 58, a prose anchor) through targeted `code_read`. The existing task uses dates as ownership and is expressly in scope for replacement; finalization already delegates full requirements to Close Wave. No runtime implementation claim was needed.

Readiness scenario observations:

| Scenario | Expected and observed plan decision |
| --- | --- |
| Verified scratch with no unique evidence or reference | Removal permitted by requirement 3. |
| Redundant uncited copy | Removal permitted only after uniqueness and reference checks. |
| Byte-duplicate still cited by the ledger | Naive deletion rejected: requirement 3 requires no live reference, and requires retention of cited paths or a durable reference-preserving mapping. |
| Unique probe or historical fingerprint | Preserve under requirement 2, even if its summary is duplicated. |
| Unrelated report dated during the wave | Do not move: requirement 1 rejects timestamp-only ownership and requirement 3 excludes unrelated files. |
| Mandatory folder migration or new required report | Rejected by optional grouping, use of an existing summary, and explicit scope exclusions. |

The cited-duplicate deletion proposal is the readiness-safe known-bad control: it was explicitly evaluated and rejected against requirements 2–3. These are plan walkthroughs, not filesystem deletion experiments or claims that future agents already comply.

Docs-contract-reviewer independently passed the plan and the three justified, falsifiable required ACs; its primer responses confirmed cited-duplicate preservation, unique-probe preservation and positive ownership, and answered that no mandatory layout or new report is needed because requirements 3–4 use optional grouping and an existing summary. Its typed readiness approval is `ev-approval-docs-contract-reviewer`. Docs and AC/QA reasoning shared that context; no separate QA seat is claimed.

Synthesis: the two substantive outputs agree on the preservation boundary, with no findings or material disagreement. Role labels were excluded when comparing the assertions, then restored for this report; this is a limited two-output merit comparison, not a blind independent moderator. Agreement: unanimous; maximum severity: none. Verdict: PASS for plan readiness. Prefer a short checklist and retain uncertain artifacts; carry that implementation note forward without expanding the plan. Existing validation and a current framework receipt still must be demonstrated during implementation. No source edits, closure, commit, deletion or runtime test was performed by this review.
