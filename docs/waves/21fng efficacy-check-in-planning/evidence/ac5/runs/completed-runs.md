# AC-5 Completed Run Replies

Owner: Engineering
Status: active
Last verified: 2026-10-23

These are the replies from the seven runs that produced output, transcribed with their substance, structure and conclusions preserved; minor formatting was normalized. All other runs were stopped by a safety classifier and returned nothing.

## Case (a), new arm, run 1

Approaches:

- **A, fully automatic derivation:** checkbox states record delivery, not whether the intended benefit was achieved.
- **B, derived draft with mandatory confirmation:** risks rubber-stamping.
- **C, surface the AC tally as evidence beside the operator-authored line:** still relies on the operator.

Selected C, with B's prefill limited to evidence references; it keeps the assessment an explicit judgment.

Mechanism efficacy:

- **Replay:** a wave with every AC `[x]` but the benefit not materialized would be written "achieved" by A, wrongly; `inferred`.
- **Control or advice:** A controls the outcome and a wrong default would stand; C advises, and the line staying required is what makes someone act on it.
- **Wrongly flagged:** "achieved" for a delivered but ineffective wave; "partial" for a harmless `[~]`.
- **Existing mechanism:** the tally and the composer already exist.
- **Measure:** sample closed waves against later outcome evidence; count overrides and empty or boilerplate lines.

The run noted the proposal reverses the prior row "Preserve explicit outcome assessment; never infer it from task completion", whose reason was withheld.

Concerns:

- the conflict with that prior decision;
- the checkbox-to-verdict mapping conflates delivery with outcome;
- "absent ACs = not established" misreads doc-only changes;
- uniform wording hides variation;
- an AC is needed that fails with the fix absent;
- mechanism claims are unverified.

## Case (a), new arm, run 2

Approaches:

- **A, automatic derivation:** the checkbox state measures delivery of the stated criteria, not whether intent was established; this is the task-completion inference the lifecycle avoids.
- **B, derived draft with explicit confirmation before write:** keeps an authoring step and risks habit clicks.
- **C, evidence-linked scaffold with no verdict:** the repetitive wording remains.

Selected B, narrowed: the derived verdict appears only when Product Intent names an intent-testing AC and it is `[x]`.

Mechanism efficacy:

- **Replay:** a change whose ACs only prove a renderer emitted text would be written "achieved" by A; B lets the operator correct it.
- **Control or advice:** A controls; B advises, with close refusing until the line is confirmed.
- **Wrongly flagged:** `[~]` conflates narrowed and failed; an empty AC list misreads doc-only changes; "achieved" lines become boilerplate.
- **Existing data:** the composer and the checkboxes carry most of the value.
- **Measure:** the rewrite rate, and spot-checks that "achieved" has an intent-testing AC behind it.

Concerns:

- it restates the rejected alternative "Synthesize success from checked ACs" without its reason;
- it equates checked ACs with achieved benefit;
- the default verdict invites non-checking;
- the uniformity goal conflicts with explicit assessment;
- a known-bad AC is needed.

## Case (b), new arm, run 1

Approaches:

- **A, Serialization Points union:** Serialization Points name contended files, not the edit set, so it is noise.
- **B, expected set from Scope, Tasks and Affected docs paths:** fuzzy prose extraction.
- **C, no sensor, a grouped diff stat for the reviewer:** stays manual.

Selected B, advisory, pending evidence.

Mechanism efficacy:

- **Replay:** not possible from two files; precision and recall unverified; run a census over closed waves first.
- **Control or advice:** advisory, and a long list gets skimmed.
- **False positives:** tests, generated files, docs, changelog and handoff.
- **False negatives:** an edit to a file declared by another change.
- **Existing mechanism:** the existing diff view.
- **Measure:** median listed files and the send-back rate.

Concerns:

- the union is the wrong oracle;
- "no new authoring" is unproven;
- noise from generated, test and docs files;
- no acting mechanism;
- the close run duplicates review;
- commit attribution is ambiguous and work is uncommitted.

## Case (b), new arm, run 2

Approaches:

- **A, the union as proposed:** Serialization Points likely under-declare, so legitimate edits get flagged.
- **B, a per-change declared edit set:** new authoring.
- **C, files named anywhere in change docs, with the union as one input:** fuzzy.

Selected C, narrow and advisory.

Mechanism efficacy:

- **Replay:** run offline over closed waves' diffs first; unverified.
- **Control or advice:** advisory; acted on only if the list is short and true.
- **Wrong flags:** tests, generated files and docs.
- **Misses:** in-scope paths changed for unrelated reasons.
- **Existing data:** `wf_audit` and the diff may give most of the value.
- **Measure:** the send-back rate, retuning below about 20 percent.

Concerns:

- Serialization Points are a poor proxy;
- generated and test files are not handled;
- the commit range and uncommitted work are undefined;
- the close run is redundant;
- no success measure is given.

## Case (b), baseline arm, run 1

Approaches:

- **A, the union:** Serialization Points declare contention, not a manifest, so the listing is noisy and gets ignored.
- **B, a purpose-built declaration:** new authoring.
- **C, derive from Scope, Tasks, ACs and Serialization Points:** heuristic.
- **D, a reviewer checklist:** manual.

Selected C, advisory.

Concerns:

- the load-bearing assumption is untested, and Serialization Points likely list hotspots;
- generated, test and wave-record files would be flagged;
- the diff base is undefined and work is uncommitted;
- multi-commit attribution;
- the close rerun duplicates review;
- "no new authoring" is unproven.

## Case (b), baseline arm, run 2

Approaches:

- **A, the union as proposed:** assumes Serialization Points are a complete path list.
- **B, a dedicated Expected Files section:** new authoring.
- **C, derive from evidence and commit attribution:** heuristic.

Selected A, with the set-deriving rule stated explicitly.

Concerns:

- the Serialization Points format is unconfirmed;
- no treatment of generated, test or wave files;
- changes with no Serialization Points flag their whole diff;
- the diff base is undefined;
- other waves' files appear at close;
- the advisory registration is unstated.

## Case (c), new arm, run 1

Approaches:

- **1, allowlist Grep and Glob (the proposal):** a hand-maintained list.
- **2, invert to a write-tool denylist:** fails open for unknown tools.
- **3, narrow the hook matcher:** wider blast radius and loses fail-closed behaviour.

Selected 1; it is smallest and preserves fail-closed behaviour.

Mechanism efficacy:

- **Replay:** a Grep payload under seeds takes the early pass; `inferred`.
- **Control or advice:** it controls.
- **Wrong flags:** other read-only tools are still refused; a Grep payload with a write-capable field is unverified.
- **Existing mechanism:** extends the Read and Bash allowlist.
- **Measure:** the downstream report stops recurring, and hook tests cover Grep, Glob, edit and unknown tools.

Concerns:

- claims are unverified against the tree;
- confirm no Grep or Glob option writes;
- add an AC for the unknown-tool negative case;
- tool-name casing (reply truncated).
