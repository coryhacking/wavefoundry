# AC-3 Reply: Credible-Threat Unknown Factor

Owner: Engineering
Status: active
Last verified: 2026-10-24

The reply of the one fresh subagent given `brief.md`, recorded verbatim below, followed by the comparison against AC-3. This is one run: an indication that a reviewer given seed 213 keeps the candidate open, not proof of adherence.

## Reply (verbatim)

~~~~text
Synthesis for the review ledger (reasoning only, no tools or files used):

- `validation_status`: `real`. Factors (a), (b) and (c) are grounded: a named less-trusted actor (fork contributors), a file they control, and a supported CI path that accepts it. The candidate stays on record. Factor (d) is unknown, which is not the same as absent.

- `attacker_reachability`: `true`. The fork contributor is the documented less-trusted actor, and their file demonstrably reaches a supported path.

- `authority_delta`: `unverified`. The token's permissions fall back to an org default the reviewer cannot see. Read-only means no delta. Write scope means `material`. Neither can be confirmed or ruled out, so I would not guess `none` or `material`.

- Disposition: `dont_do_later`, not actionable now and not `not_issue`. The `disposition_rationale` should say the contributor-controlled input reaches a supported path, but the capability gain depends on the unrecorded token default. The finding is not blocking and does not drive severity, because severity cannot be set from an unverified authority delta. It is not dismissed, because the gate's unknown factor is kept open.

- `rejection_basis`: `insufficient_evidence`. Record this as the reason the candidate is not promoted. Do not record it as a rejection of the candidate.

- `promotion_trigger`: factor (d), authority delta. The trigger fires when the effective default token permissions are established as write-capable, or the workflow stops running contributor-controlled config under a token with write scope. The settling evidence is an explicit `permissions:` block in the workflow, or a recorded org default. Fork pull requests are also a named promotion trigger, so re-run the gate if the workflow trigger or token scope changes.

Suggested recommended fix: declare minimal explicit token permissions (`contents: read`) in the workflow. That would settle factor (d) as no delta.
~~~~

## Comparison with AC-3

| Expected | Reply | Match |
| -------- | ----- | ----- |
| `validation_status: real` | `real` | yes |
| `authority_delta: unverified` | `unverified` | yes |
| `rejection_basis: insufficient_evidence` | `insufficient_evidence` | yes |
| `promotion_trigger` names the factor and the settling evidence | names factor (d) and an explicit `permissions:` block or a recorded org default | yes |
| candidate not dropped | `dont_do_later`, kept on record, not `not_issue` | yes |

Result: matched on one run. Limitation: the brief states that no other predicate applies and spells out the uncertainty, so the run shows the guidance is followed when the situation is described plainly; it does not show a reviewer recognizes an unknown factor unprompted in real code.
