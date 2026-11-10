# Make the Writing Guide's Precision Rule Concrete

Change ID: `23040-enh writing-guide-concrete-precision`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-11-10
Wave: 23041 writing-guide-concrete-precision

## Rationale

Since the reader-centered writing guide (`.wavefoundry/framework/docs/writing-guide.md`, wave 224i4, 2026-10-31) took effect, change plans have become shorter but not easier to use. Observed on 2026-11-10:

- Mean sentence length in change docs fell from 25.4 words (261 docs from waves completed 2026-10-01 to 10-30) to 18.7 words (45 docs from 2026-10-31 to 11-09), and the median doc fell from 1,824 to 1,595 words.
- In a blind check, one independent agent reader scored six bug plans, three from each period, with dates and history removed. The three earlier plans (21bzm, 21ayx, 216g8) averaged 4.7 of 5; the three later ones averaged 3.3: 22qp0 scored 5.0, 22o90 2.8 and 22oaz 2.2. The reader put only 22oaz and 22o90 in an "abstract, policy-register" style. Their requirements use terms they never explain ("partial-result semantics"), name things without identifying them ("the actual supported environment variable", with no name), state limits with no number ("bounded explicit diagnostics") and put hedges inside requirements ("where practical", "where necessary"). 22qp0 named the function, the failing inputs and the observed output.
- Per 10,000 words of change docs, "bounded" rose from 11.7 to 19.6 and "consequential" from 0.5 to 4.9. The after window includes the writing waves themselves (224i4, 22sqj) and Envision plans that discuss these words, so this rate overstates any spread from the guide.

The cause is unsettled. 22oaz and 22o90 were planned on the same day (2026-11-05) from external distribution reports, before the source was checked; 22oaz says "Source verification and bounded reproductions are implementation prerequisites". Two high-scoring earlier plans (21ayx, 216g8) also answered distribution feedback but name a verified commit and the function they read. So the weak plans may come from one session planning before verification rather than from the guide. 224i4's own matched test also found no measurable difference between its guide and the earlier guidance. The change is still worth making: the guide forbids this wording only in principle ("keep numerical constraints explicit"), and the operator's priority is accuracy and precise wording over length. The evidence supports a targeted addition, not a rewrite of the guide.

## Product Intent

Readers of plans, specifications and status records get requirements that either name or define the specific setting, file, function, command, term, error text or limit they depend on, or say plainly that it is not yet known and what will identify it. The guide gains this rule, extends its existing worked example to show it, and defines the word it uses most without defining ("consequential"). Accuracy takes precedence over length. It stays one shared document with no new review lane, linter, gate or template.

## Requirements

1. The guide's "Understandable" section gains a paragraph with this rule, for requirements, acceptance criteria and status claims:
   1. When a claim depends on a specific setting, file, function, command, term, error text or limit, name it, and define a term the reader cannot look up. If it is not yet known, say so and say what will identify it, rather than guessing a name.
   2. A limit that a requirement imposes carries its number and unit, or states that the value is undecided and who decides it. Ordinary descriptive adjectives are not limits.
   3. A requirement contains no hedge that leaves the obligation open (for example "if feasible", "as needed" or "where possible"). When the obligation depends on a condition, state the condition; a stated condition is not a hedge.
   4. A plan that fixes a defect shows the observed failure (the input or action, the actual result and the expected result), or says it has not been reproduced.
2. The guide's existing worked example (the importer rejecting a record larger than 8 MiB) gains an abstract version that shows an unnamed setting, an unquantified limit and a hedge. Its quoted text is frozen here: “The importer should reject oversized records where appropriate, using the configured size limit.” The implementer adds one sentence of explanation saying which of the three defects each phrase shows, and that "should" weakens "must". Both are inserted after the paragraph's final sentence ("The shorter sentence loses ..."), so that sentence still refers to the "usually rejected" sentence. Every existing sentence of that paragraph stays unchanged.
3. Immediately after the introduction's sentence "Surface consequential conflicts.", the guide's first use of the word, one added sentence defines it: a consequential point is one that would change the reader's decision, action or result if omitted, missed or misread. The other uses of the word keep their wording and take this meaning.
4. No existing sentence, heading, artifact-table row or limit statement is removed or weakened; the only changes are the additions in Requirements 1 to 3 and the `Last verified` date.
5. There is no word cap. Each added sentence states a rule, an exception, the definition or part of the example, and no added sentence repeats another. The implementer reports the guide's word count before and after with `wc -w`.
6. The root `CHANGELOG.md` gains a `### Changed` subsection under `## [Unreleased]` with one bullet that ends "Wave 23041 / change 23040."

## Scope

**Problem statement:** the writing guide shortened plans but did not stop abstract wording in requirements, and states the needed precision only in principle.

**In scope:**

- `.wavefoundry/framework/docs/writing-guide.md`
- One CHANGELOG bullet.
- One reader check of a single batch, defined in AC-3, using the fixtures frozen under `.wavefoundry/work/23041/ac3/`.

**Out of scope:**

- Rewording the guide's existing uses of "consequential", "bounded" or "relevant", including the ISO principle name "Relevant" and the artifact-table rows; Requirement 3 defines "consequential" instead. The same words also stay unchanged in the guide's pointers (`AGENTS.md`, `docs/prompts/index.md`, seeds 020, 050, 100 and 209). A later change can revisit them if field evidence warrants.
- Rewriting existing plans, wave records, memories or released CHANGELOG sections.
- Seeds, prompts and their local copies. They reference the guide only by path; no file quotes its headings or sentences, and `test_writing_guide_delivery.py` checks only the path, packed bytes and non-empty content.
- A prose linter, readability score, word list or new review lane.
- The wave summary generator's missing line break before `## Watchpoints` (wave 22vgm). That is a separate code defect.

**Platform behavior:** documentation only. It is the same on Windows, macOS, Linux and WSL2, and delivery uses the existing pack and upgrade path checked by `test_writing_guide_delivery.py`.

## Acceptance Criteria

- [x] AC-1: The revised guide contains the rule from Requirement 1, the abstract version from Requirement 2 (with an unnamed setting, an unquantified limit and a hedge) after the unchanged 8 MiB paragraph's final sentence, and the definition from Requirement 3 immediately after "Surface consequential conflicts.". A docs-contract reviewer compares the revised guide with the frozen control copy (`.wavefoundry/work/23041/ac3/control-writing-guide.md`) and confirms all of these:
   1. Only these additions and the `Last verified` date differ.
   2. The abstract example's quoted text matches Requirement 2 exactly.
   3. Every added sentence other than that quoted text is free of the three defect classes; a quoted example of a defect is not an instance of it.
   4. Each added sentence meets Requirement 5.
   5. A fixed-string grep of `.wavefoundry/work/23041/ac3/plans/` finds none of the added text's example phrases ("if feasible", "as needed", "where possible", "where appropriate", "oversized", "configured size limit") and the added text contains none of the key and contestable phrases or the words "where practical", "where necessary", "bounded", "partial", "relevant", "representative" and "intended".
   6. The word counts before and after are recorded.
- [x] AC-2: `test_writing_guide_delivery.py` passes and `wf_validate_docs` passes. This is a delivery regression check only; it does not test the guide's content.
- [~] AC-3 (intent check, with a control): two fresh readers run in one batch, in separate contexts. Neither has seen this change doc or any earlier result, and both are told to read only the files they are given. Each receives the reader prompt below and the six frozen plans in `.wavefoundry/work/23041/ac3/plans/` (labelled A to F, with Change ID lines removed). The control reader gets the frozen control guide; the candidate reader gets the revised guide. The coordinator reduces each output to rows of document, quote, stated class and a one-line reason, removes any prose that cites the guide, and labels the two outputs X and Y. The docs-contract reviewer scores both with the answer key below, which was frozen before the guide was edited, records every ruling with its reason, and only then learns which output is the candidate. The result is one of:
   1. Pass: the candidate matches more key items than the control and reports no more false positives than the control.
   2. Inconclusive: the control matches all nine key items, so the candidate cannot score higher.
   3. Fail: any other result, including a tie.
  *Status: Failed by the rule decided at readiness: a tie. Scored blind, the candidate (revised guide) and control (prior guide) each matched 5 of 9 key items (A2, A3, C1, C3, C4) with 0 false positives. The rule ships on AC-1 and AC-2; no improvement is claimed and there is no second attempt. Evidence: .wavefoundry/work/23041/ac3/run/rulings.md.*

## AC-3 Reader Prompt and Answer Key

The outcome is decided now. On a pass, AC-3 is marked `[x]`. On an inconclusive or failed result, AC-3 is marked `[~]` with the counts. The rule still ships, because AC-1 and AC-2 establish its delivery, and the change claims no improvement. There is no second attempt in this wave. The result is evidence from one agent reader pair. It does not test whether writers produce fewer defects, or Requirement 1's "undecided, and who decides" and observed-failure parts.

Reader prompt (frozen):

> You are reviewing six planning documents, labelled A to F, against the writing guide you are given. Read only the guide and the six files provided; do not open any other file or search the repository. For each document, list every place where a requirement, acceptance criterion or status claim fails to name or define a specific thing it depends on, states an imposed limit without a number, or contains a hedge that leaves an obligation open. Quote each passage (at most 25 words) and say which of the three it is. A condition that is stated explicitly is not a hedge. List nothing that does not fit one of the three. If a document has none, say "none".

Answer key (frozen before the guide edit; nine scored items):

- A: A1 "the required compatible model-set" (unnamed); A2 "a relevant misnamed model archive in existing search folders" (folders unnamed); A3 "representative POSIX/Windows paths" (unnamed); A4 AC-2 "emits the intended single remedy" (unnamed).
- C: C1 "bounded explicit diagnostics" (limit without a number); C2 "partial-result semantics" (undefined); C3 "Preserve existing callers/return types where practical" (hedge); C4 "Skip the affected name where necessary" (hedge); C5 "compatible partial diagnostics" (undefined).

Scoring rules:

- A listed quote matches a key item when it quotes or overlaps the key's phrase, or a restatement of the same defect elsewhere in the same document, and its stated class fits the item: an unnamed or undefined item is class 1, a limit without a number class 2, a hedge class 3. One listed quote matches at most one key item, and each key item counts once. A quote that overlaps both a key item and a contestable item matches the key item only when its stated class fits that item.
- Contestable, not scored either way: in A, "actual supported environment variable, validated from source" (says what will identify it), "one bounded found-but-not-used hint" (capped at 120 characters in the same requirement) and "narrowly scoped messages" (a task, not a requirement). In C, "the existing render/sync/upgrade reporting channels". Any other item listed for A or C that is not in the key scores zero.
- Accepted true positives, not scored: "the existing link-metadata helper" (E), "keeps the fragment ... allowlists" (F), and the shared AC "The change's own suites and every test it adds pass" (B, D, E, F).
- Any other item listed for B, D, E or F is a false positive unless the docs-contract reviewer rules, blind to which output it came from, that it fits one of the three classes; the ruling and reason are recorded.

## Tasks

- [x] Freeze the AC-3 fixtures, the control guide, the reader prompt and the answer key before any guide edit.
- [x] Revise the guide per Requirements 1 to 4 and add the CHANGELOG bullet.
- [x] Run `test_writing_guide_delivery.py` and `wf_validate_docs`, record `wc -w` before and after, and refresh the guide's `Last verified` date.
- [x] Run the AC-3 reader pair and the delivery reviews; record counts and limits in the Progress Log.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Guide revision | implementer | readiness | One writer; fixtures already frozen |
| Reader pair | qa-reviewer | guide revision | Two fresh read-only contexts, one batch |
| Contract review and false-positive judging | docs-contract-reviewer | reader pair | Diff against the control copy |

## Serialization Points

- `.wavefoundry/framework/docs/writing-guide.md`

The root `CHANGELOG.md` is a documentation edit made by the same writer.

## Affected Architecture Docs

N/A: the guide's ownership, delivery route and references are unchanged. This adds content to one shared guidance document.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Delivers the rule and example without weakening existing guidance |
| AC-2 | required | Delivery must keep working |
| AC-3 | required | Tests, against a control, whether the revision makes these defects easier to identify; the outcome handling is decided in advance |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-11-10 | Planned from the operator's review of how the ISO-based guide is working. Blind check key: A 22oaz, B 21bzm, C 22o90, D 22qp0, E 21ayx, F 216g8. Average scores (1 to 5 across main point, obligations, evidence, effort, actionability): A 2.2, B 4.8, C 2.8, D 5.0, E 4.4, F 4.8. | Change-doc census over waves completed 2026-10-01 to 11-09; blind reader report from this session |
| 2026-11-10 | Readiness review: QA, docs-contract and red-team found that AC-3 lacked a control and frozen key, Requirement 4 conflicted with the ISO heading and table, the naming rule could force guessed names, the confounds were understated and the 250-word cap had no basis. Revised: control reader and frozen key and prompt added; rewording of existing words dropped; "not yet identified" and descriptive-adjective exemptions added; confounds stated; the existing example extended instead of a new one; cap set to 150 words. Fixtures frozen with Change ID lines removed. | `.wavefoundry/work/23041/ac3/` (plans, control-writing-guide.md, provenance-map.json) |
| 2026-11-10 | Round-2 readiness: docs-contract approved; QA and red-team blocked on AC-3 scoring (rule hedge examples matched two key answers; unblinded false-positive judging; undefined matching; key items contestable under the new rule; clean plans contain fair instances; ceiling risk) and asked for the outcome to be decided in advance. Operator: accuracy and precise language matter more than content length. Revised: word caps removed; "consequential" defined at first use; hedge examples replaced with strings absent from the fixtures; X/Y blind scoring; matching, contestable and accepted-item rules; nine scored key items; pass, inconclusive and fail decided in advance; the abstract example placed after the paragraph's last sentence. key.json renamed provenance-map.json; it maps letters to plans and is never given to readers. The control guide equals the guide at commit `02c70a62`. | Round-2 review reports from this session; `.wavefoundry/work/23041/ac3/` |
| 2026-11-10 | Round-3 readiness: docs-contract approved; red-team and QA blocked on the abstract example (unconstrained wording could reuse key phrases, and AC-1 required it to be defect-free) and the wave.md watchpoint contradicting the decided outcome. Revised: the example's quoted text frozen and grep-checked against the fixtures, AC-1 exempts only that quoted text, quoted examples are not instances, no added sentence repeats another, matching requires a fitting class and one item per quote, outputs are reduced to rows before blind scoring, the definition placed immediately after "Surface consequential conflicts." and widened to "omitted, missed or misread", and the watchpoint corrected. | Round-3 review reports from this session; fixed-string grep of the example phrases over `.wavefoundry/work/23041/ac3/plans/` found none |
| 2026-11-10 | Round-4 readiness: QA, docs-contract and red-team approved; no blocking findings. Implementation commitments from their notes: the abstract example and its explanation sentence go in the same paragraph, after its final sentence, using the guide's curly quotes for inline words. In AC-3, the coordinator's reduction keeps one verbatim row per listed quote, drops or merges none, and keeps both raw outputs beside the rows for audit; masking removes only sentences that cite the guide. "should" occurs in the fixtures (for example plan D) and is deliberately not in the AC-1 grep list; a listed "should" outside a requirement fits no class, and this bias works against the candidate. | Round-4 review reports from this session |
| 2026-11-10 | Implemented. Guide 1,156 words before, 1,363 after (`wc -w`; +207). Added: the definition of "consequential" immediately after "Surface consequential conflicts."; the rule paragraph in "Understandable" after the instruction paragraph; the frozen abstract example plus one explanation sentence at the end of the 8 MiB paragraph; `Last verified` 2026-11-10. Diff against the control copy shows only these changes. Added text contains none of the forbidden words; fixed-string grep of the fixture plans finds 0 matches for each example phrase. CHANGELOG `[Unreleased]` / Changed bullet added. Gapfill: shell diff and grep for the mechanical AC-1 checks over known paths. | `test_writing_guide_delivery.py` 5 OK; `wf_validate_docs` pass; `.wavefoundry/work/23041/ac3/candidate-writing-guide.md` |
| 2026-11-10 | AC-3 run: two fresh readers (one with the frozen control guide, one with the revised guide) read the six frozen plans with the frozen prompt and only their own staged folder. Outputs kept raw, reduced to verbatim rows (none dropped or merged; only the opening prose removed) and labelled X and Y. The docs-contract judge recorded every ruling blind: X 5/9 key matches (A2, A3, C1, C3, C4) and 0 false positives; Y 5/9 (the same items) and 0 false positives. Neither found A1, A4, C2 or C5. Un-blinded after recording: X was the candidate, Y the control. Result: fail (a tie), so AC-3 is `[~]` by the rule decided at readiness; no improvement is claimed and there is no second attempt. Marking `[~]` rotated the review receipt. | `.wavefoundry/work/23041/ac3/run/` (r1-raw.md, r2-raw.md, r1-intro.md, r2-intro.md, X-rows.md, Y-rows.md, rulings.md, xy-assignment.json) |
| 2026-11-10 | Delivery review: QA, docs-contract and red-team approved; all three confirmed the readiness verdict after AC-3 was marked `[~]`. At the operator's direction (fix now), three red-team precision notes were applied to the rule paragraph: an acceptable not-yet-known example; an adjective is a limit when a requirement acts on it (replacing "ordinary descriptive adjectives are not limits"); removing a hedge must not turn a recommendation into a requirement. Guide now 1,421 words (+265 from 1,156). The new example phrases occur 0 times in the fixture plans. The AC-3 result applies to the guide as tested (`.wavefoundry/work/23041/ac3/candidate-writing-guide.md`), not to these later additions. Not changed: the AC-3 note sits after "The result is one of:" (cosmetic, left to avoid another receipt rotation). | `test_writing_guide_delivery.py` 5 OK; delivery review reports from this session |
| 2026-11-10 | Recheck of the three additions: QA and docs-contract approved; red-team approved with notes. Applied: the adjective test now requires that the adjective stand for a quantity, and a categorical adjective (example "reject corrupt records") is a term to define, which closes a false-precision gap; the recommendation sentence now says to use **should** or "we recommend" and is tied to removing a hedge; the not-yet-known example names who identifies the setting. Guide now 1,453 words. New example phrases ("corrupt", "we recommend") occur 0 times in the fixture plans. | `test_writing_guide_delivery.py` 5 OK; recheck reports from this session |
| 2026-11-10 | Final recheck: docs-contract approved (AC-1 met, items 1 to 6); red-team approved with two notes, both applied. The hedge sentence now says to keep **must** and state the condition when removing a hedge from an obligation, and to use **should** or "we recommend" only for text that was a recommendation, closing a reading that permitted downgrading **must**. A quality adjective a requirement acts on (example "return a helpful error") needs a definition or the observable result; any other adjective is a description. Guide now 1,487 words (+331 from 1,156). New example phrases occur 0 times in the fixture plans. | `test_writing_guide_delivery.py` 5 OK; final recheck reports from this session |
| 2026-11-10 | Focused verification by red-team: approve, both notes closed. Applied its suggested wording to remove an overlap: "When removing a hedge from an obligation, keep **must**; if the obligation is conditional, state the condition." Iteration stops here. AC-1 met per the docs-contract final recheck (items 1 to 6). Guide final: 1,487 words. | Focused verification report from this session |
| 2026-11-10 | Change 23042 moved the AC-3 deferral note from the end of the criterion's first line to a `*Status: ...*` line after its numbered outcomes, with the `Status: ` prefix added and the note's wording otherwise unchanged. This changes this document's review digest. | `23042-bug mark-ac-reason-splits-multiline-criterion` Requirement 6 |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-11-10 | Add one rule paragraph, extend the existing 8 MiB example and define "consequential". | The guide forbids the observed wording only in principle, and uses "consequential" seven times without saying what it means; the operator puts accuracy and precise language ahead of length. | Prose linter or word list: the guide rules out linters; new standalone example: duplicates the existing one; rewrite the guide's own vocabulary: the evidence is confounded by the writing waves, so deferred. |
| 2026-11-10 | Test the intent with a control and candidate reader pair on frozen real plans. | Without a control, any reader could find these defects with no guide at all. | Single reader: cannot fail; matched authoring batch: 224i4 found no difference at this sample size. |

## Risks

| Risk | Mitigation |
| --- | --- |
| Writers invent a name or number to satisfy the rule | The rule allows "not yet identified, and what will identify it" and "undecided, and who decides" |
| The rule pushes implementation detail into intent sections | It applies to requirements, acceptance criteria and status claims, not Product Intent |
| The weak plans came from planning before verification, which the guide cannot fix | Stated in the Rationale; AC-3 claims only identifiability, and a tie or loss is reported as such |
| Six plans picked by the planner bias the check | The control reader faces the same bias, so only the difference between the two readers counts |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
