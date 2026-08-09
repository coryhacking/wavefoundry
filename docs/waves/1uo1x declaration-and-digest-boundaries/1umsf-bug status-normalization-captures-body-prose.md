# Status Normalization Captures Body Prose

Change ID: `1umsf-bug status-normalization-captures-body-prose`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-08-07
Wave: 1uo1x declaration-and-digest-boundaries

## Rationale

`normalize_review_tracking_status` (`gardener_metadata.py`) is the digest normalizer that makes workflow-status metadata review-irrelevant. Its docstring states the boundary it is supposed to hold:

> Limit this normalization to the leading metadata carrier so a similarly named prose line remains reviewable.

It does not hold it. Executed against the current tree:

```
# T

Owner: Eng

Problem: the gate fails.

Status: this sentence is real contract prose that a reviewer must read.
```

The body `Status:` line is rewritten to `Status: <workflow-status>`. The frontmatter scan stops at the first line that is neither blank, nor an `# ` heading, nor matched by `_FRONTMATTER_METADATA_RE`, so any prose line shaped `Word: text` keeps the region open. Here `Problem: the gate fails.` is what lets the later body line be captured.

**This is a latent hole, not an active incident.** Independent review confirmed the mechanism and measured the corpus: zero documents currently have a prose `Status:` line captured this way. The defect is real and reachable, but it has no instance here today. That lowers its urgency and it does not make it safe to leave: a false normalization makes a genuine contract edit digest-invisible, so an operator could change a document's meaning and the review-policy receipt would not move. That is the inverse of the guarantee the digest exists to provide, and it is silent.

**An earlier revision of this plan proposed bounding the region at the first `## ` heading. The readiness council disproved that design structurally.** A `## ` heading already closes the current scan: it is non-blank, it does not start with `# ` followed by a space, and it fails `_FRONTMATTER_METADATA_RE`. Every capture instance therefore necessarily lies before the first `## ` heading, so heading-bounding cannot remove a single capture. Worse, it converts the entire pre-heading region into carrier, which widens capture into exactly the prose the docstring protects: the reported reproduction above contains no `## ` heading at all and still captures under heading-bounding, and a `Status:` line inside a pre-heading fenced example would be rewritten too. The plan's own recorded evidence (zero post-heading captures) was the falsifier of its own design, read as reassurance.

**The adopted design is a fixed known-key allowlist.** The metadata carrier is the run of leading lines that are blank, a `# ` title, a blockquote, or a `Key: value` line whose key is in a fixed allowlist stated in the code (`Change ID`, `Change Status`, `Status`, `Owner`, `Wave`, `Last verified`, `Title`, `wave-id`, `review-evidence-source`, `review-policy-reprepare-required`, `Completed At`, `Closed At`, `Previous Change Status`, and the other keys the census observes in real leading carriers; the census proves `Role` and `Category` are mandatory members, because `docs/agents/memory-archive.md` carries a genuine `Status:` line beneath them and would narrow without them). The first line that is none of those closes the region. `Problem: the gate fails.` is shape-identical to `Owner: Eng` but is not a known key, so it closes the region and the later `Status:` line stays reviewable. A fence marker line closes the region the same way, so fenced examples need no special handling. Blockquote tolerance is deliberate: it fixes the one real boundary error the census found in the current scan, which closes early at a `> **REFRAMED...**` blockquote and leaves genuine frontmatter status lines digest-significant.

**Feasibility measured on this tree.** Over 1457 markdown documents (docs tree plus framework markdown), comparing captured status-line sets between the current scan and an allowlist candidate built from every key observed in current leading carriers: exactly **one** document differs, `docs/waves/1p7de graph-edge-trust/1p7dg-enh cross-file-receiver-resolution.md`, where the blockquote at line 3 currently truncates the region and the candidate recovers the two real frontmatter status lines beneath it. The difference **widens** normalization, and wave `1p7de` is closed. Zero non-closed waves are affected; the transition cost here is nil. The shipped allowlist will be curated rather than census-everything, and AC-6 pins that the curated set reproduces exactly this one-document diff.

**Failure direction is chosen deliberately.** If a future document uses a metadata key outside the allowlist, the region closes early and a genuine `Status:` line below it stays digest-significant, so advancing that document's status moves the digest and lapses approvals. That errs toward visible churn, which operators notice and this project has machinery to repair, rather than toward silent capture of contract prose, which nobody notices. The census confirms the churn direction has zero instances today.

**The sibling guard contract cannot be copied literally, and an earlier revision of this plan would have caused a mass approval lapse by doing so.** `normalize_gardener_date` and `normalize_progress_log` return the input unchanged when `len(matches) != 1` (`gardener_metadata.py:47`, `:128`). But a change document legitimately carries two leading status lines, `Change Status:` and `Status:`. Measured under the current scan over the 1457-document population, the match-count buckets are `{0: 76, 1: 587, 2: 794}`; under the allowlist boundary the two-bucket becomes 795 because `1p7dg` recovers its pair. A literal `!= 1` guard would stop normalizing every one of those two-line documents, moving the digest on every status advance and lapsing approvals across the corpus. The admissible count set must be stated explicitly rather than inherited by analogy.

**The guard also cannot be the backstop for a wrong boundary.** No document has three or more leading status lines under either boundary, so a `> 2` guard never fires, and a boundary error that captures one extra line in a one-line-frontmatter document produces a count of two, which is admissible. The guard defends against a shape the corpus cannot currently produce; the boundary itself is what AC-3 pins.

## Requirements

1. A `Status:` or `Change Status:` line in a document's body must not be normalized. Only the leading metadata carrier is in scope, exactly as the docstring promises.
2. The carrier boundary must be decided by a fixed known-key allowlist stated in the code, not by line shape. The region consists of leading lines that are blank, a `# ` title, a blockquote, or a known-key metadata line; the first line that is none of those closes it. Prose shaped `Word: text` with an unknown key closes the region; a blockquote does not.
3. The ambiguity guard must state its admissible match counts explicitly. One and two are both legitimate; the guard exists to catch a count outside what the document shape can produce, not to enforce a single match.
4. Genuine frontmatter must still normalize. Both `Change Status:` and `Status:` in the leading carrier remain digest-neutral, so advancing a change's status stays progress-only.
5. The change must report its own transition cost, measured under the shipped allowlist, and must report the direction of each difference.

## Scope

**Problem statement:** The digest normalizer can rewrite body prose it promises to leave alone, which would make a real contract edit invisible to the review-policy receipt.

**In scope:**

- The frontmatter boundary in `normalize_review_tracking_status`: known-key allowlist with blockquote tolerance.
- An ambiguity guard with an explicitly stated admissible count set.
- A census comparing captured status-line sets under the current scan and the shipped allowlist across the corpus, reporting every differing document, the direction, and non-closed-wave exposure.
- Regression coverage, including a control proving legitimate frontmatter still normalizes.

**Out of scope:**

- `normalize_gardener_date` and `normalize_progress_log`. Their guards are correct for their shapes and this change does not touch them. This leaves a deliberate in-module asymmetry: `normalize_gardener_date` keeps the shape-based scan while `normalize_review_tracking_status` moves to the allowlist, so for the reported repro the date normalizer would still capture a body date while the status normalizer would not. No test pins the two boundaries equal (`test_review_policy.py:1089` pins the date boundary alone and carries no status lines, so it stays green), which is exactly why the divergence needs an in-code comment at the split, matching the precedent already at `gardener_metadata.py:13-15`. Whether the date normalizer should follow is a separate change.
- `_FRONTMATTER_METADATA_RE`, which other callers share. This change gives `normalize_review_tracking_status` its own boundary; it does not alter the shared shape predicate.
- Whether `Change Status` should be digest-neutral at all. Settled: it is progress, not a contract change, and this change preserves that.
- Re-Preparing any wave. If a downstream repository's census is non-zero, the re-Prepare is the operator's decision, disclosed rather than performed.

**Evaluator-version coupling:** this change alters `canonical_review_policy_body` output for any document the boundary change affects, and therefore participates in the same digest transition as `1uo1w`. The wave ships one `REVIEW_POLICY_EVALUATOR_VERSION` bump covering both changes. If this change were ever shipped without `1uo1w`, it would need its own bump; that coupling is stated here so splitting the wave cannot silently drop it.

**Spec wording owned by the sibling change:** `docs/specs/mcp-tool-surface.md:637` describes what the digest normalizes ("leading `Status` / `Change Status` tracking metadata"), which this change redefines from a line-shape scan to a known-key carrier. That edit is carried by `1uo1w`'s AC-8 together with the same bullet's evaluator-version statement, so the sentence has one owner and one editor rather than two changes racing on the same line. This change is not done until that wording is correct, which `1uo1w` AC-8 and the wave's docs gate enforce.

## Acceptance Criteria

- [x] AC-1: A body `Status:` line preceded by prose shaped `Word: text` is left byte-identical, reproducing the reported failure as a red test first. The fixture contains no `## ` heading, pinning the case that disproved the heading-bounded design.
- [x] AC-2: A leading `Change Status:` and `Status:` pair still normalizes, so advancing a change's status remains digest-neutral. Without this a normalizer that did nothing would satisfy AC-1.
- [x] AC-3: The boundary is pinned in both directions: an unknown-key line (`Problem: the gate fails.`) closes the region even though it is shape-identical to metadata; a blockquote does not close it, so frontmatter beneath a `> **REFRAMED...**` blockquote normalizes (the `1p7dg` case); a fence marker closes it, so a `Status:` line inside a leading fenced example is never rewritten. Two of these are **red on current code** (unknown-key closure, blockquote non-closure) and belong in the red-test workstream, not after the boundary lands; the fence case is **already green today** and is a preserved-behavior control, so the implementer should expect two red tests here, not three.
- [x] AC-4: The guard's admissible match counts are stated in the code as one or two, with the reason: a change document legitimately carries `Change Status:` and `Status:`, and the corpus census (1457 documents, current-scan buckets `{0: 76, 1: 587, 2: 794}`) shows the pair is the dominant change-doc shape. A count outside the set returns the input byte-for-byte.
- [x] AC-5: A literal `len(matches) != 1` guard is proven wrong by test, not just by comment: a two-status-line document must still normalize. An incumbent detector already exists and must stay green rather than be rediscovered: `test_review_policy.py:1322` uses a `Change Status:` plus `Status:` fixture and asserts digest equality across a status advance, so the literal guard breaks it. Its public-path sibling `test_server_tools.py:28530` carries only one status line and therefore does **not** catch the guard, which is why the named AC-5 pin is still worth adding.
- [x] AC-6: The census compares captured status-line sets under the current scan and the shipped allowlist across the corpus and reports each differing document with its direction and wave status. On this repository the expected result is exactly one document (`1p7dg`, widening, closed wave); the test asserts the census runs and reports, not a fixed number, and the measured result is recorded in the Progress Log.
- [x] AC-7: The full framework suite and docs-lint pass.

## Tasks

- [x] Write the red tests before any fix: the reported body-prose capture with no `## ` heading in the fixture, and the blockquote non-closure direction (`1p7dg`'s shape), which is also red today.
- [x] Replace the shape-based scan with the known-key allowlist boundary, blockquote-tolerant.
- [x] Add the ambiguity guard with its admissible set stated in code.
- [x] Add the AC-2 control, the AC-3 boundary pins in both directions, and the AC-5 anti-regression test for the literal sibling guard.
- [x] Run the census under the shipped allowlist and record the result and direction in the Progress Log.
- [x] Run the full suite and docs-lint.

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes                                                    |
| ---------- | ----------- | ---------- | ---------------------------------------------------------- |
| red-test   | implementer | none       | Reproduce the capture before any fix                       |
| boundary   | implementer | red-test   | Known-key allowlist, blockquote-tolerant                    |
| guard      | implementer | red-test   | Admissible set stated in code, not inherited by analogy     |
| census     | implementer | boundary   | Captured-set diff, direction, and non-closed-wave exposure  |


## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/gardener_metadata.py`
- `.wavefoundry/framework/scripts/tests/test_review_policy.py`

List real repository-relative paths here. Prepare uses these paths—not Scope, Rationale, or other narrative—to select automatic review lanes. Path scoring is a floor, not a ceiling: ANY lane may also be requested by judgment through the wave's `Requested review lanes` field, and the coordinator is expected to use it. Architecture review especially is usually a judgment call, since an ownership shift or a protocol change can live entirely in files whose paths recruit only the code lane. A requested lane is always honored and costs no receipt churn.

## Affected Architecture Docs

`N/A`. The change replaces one function's boundary heuristic with an explicit allowlist inside its current owner. No boundary moves between modules and no control flow changes; what the digest covers is corrected to match what the docstring already claims.

## AC Priority


| AC   | Priority  | Rationale                                                                                       |
| ---- | --------- | ------------------------------------------------------------------------------------------------ |
| AC-1 | required  | The reported defect, pinned on the fixture that also disproved the heading-bounded design.        |
| AC-2 | required  | Without it the fix could stop normalizing frontmatter entirely and still pass AC-1.               |
| AC-3 | required  | The boundary is the whole fix; both directions plus the fence case must be pinned.                |
| AC-4 | required  | A guard copied literally from the siblings would lapse approvals on 794 documents.                 |
| AC-5 | required  | Pins the specific wrong implementation an earlier revision of this plan called for.                |
| AC-6 | important | Transition cost and its direction must be measured under the shipped allowlist; a downstream repository will differ. |
| AC-7 | required  | Standard gate.                                                                                     |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-08-07 | Census at plan time: 2 docs differ under a heading-bounded candidate, neither able to lapse an approval | current normalizer vs heading-bounded candidate |
| 2026-08-07 | First independent review reproduced the census, corrected its direction (widens, not narrows), found the defect has zero live instances, and found the literal sibling guard would mass-lapse approvals | independent sandboxed review |
| 2026-08-07 | Readiness council (red-team seat) disproved the heading-bounded design structurally: a `## ` heading already closes the current scan, so zero post-heading captures is a property of the code, not the corpus; heading-bounding fixes nothing and widens capture into pre-heading prose and fenced examples, and the plan's own repro (no heading) still captured under it. Design replaced with the known-key allowlist the seat proposed | readiness council probe, `probe_1umsf.py` |
| 2026-08-07 | Allowlist feasibility measured: over 1457 docs, captured-set diff between the current scan and a corpus-key allowlist is exactly one document, `1p7dg`, whose line-3 blockquote currently truncates the region; direction widening, wave closed. Current-scan buckets `{0: 76, 1: 587, 2: 794}`. The enterprise-delivery doc from the earlier census no longer differs: its subtitle line closes both scans, correcting an AC-3 claim that both differing docs exhibited the blockquote case | revision-3 census probe |
| 2026-08-07 | Council also found the digest-semantics change needed an explicitly stated evaluator-bump coupling; added to Scope | readiness council P2 |
| 2026-08-07 | IMPLEMENTED. Red tests written first and confirmed failing on current code (body prose rewritten; blockquote truncating the carrier). Shape-based scan replaced by the known-key allowlist with blockquote tolerance and the {1,2} guard stated in code | `tests.test_review_policy` 64 tests OK |
| 2026-08-07 | AC-6 census run against the SHIPPED allowlist, not a prototype: 1457 docs, current buckets `{0:76, 1:587, 2:794}`, shipped `{0:75, 1:587, 2:795}`, exactly ONE differing document (`1p7dg`, widening, closed wave), zero non-closed waves, zero inadmissible match counts. Matches the plan-time prediction exactly | `ac6-census.py` against shipped code |
| 2026-08-07 | Mutation-tested all three load-bearing branches: the literal `!=1` guard kills 4 tests (including the incumbent `:1322` detector the QA lane named), removing blockquote tolerance kills 1, ignoring the allowlist kills 1. The census test itself caught a defect IN ITSELF first: counting the `<workflow-status>` marker reported a false 3 for this very document, which quotes the marker in its Rationale; switched to a corpus-unique sentinel | mutation runs, restored clean |
| 2026-08-07 | Readiness QA lane APPROVED, reproduced the census independently (1459 docs, same single differing document, buckets matching on the 1- and 2-buckets AC-4 and AC-5 rest on), and found three things the plan had not stated: `test_review_policy.py:1322` is an INCUMBENT detector of the literal `!=1` guard that must stay green, the fence direction of AC-3 is already green today so only two of its three pins are red, and the in-module boundary asymmetry with `normalize_gardener_date` needs an in-code comment because no test pins the two boundaries equal | readiness QA lane |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-08-07 | Replace the heading-bounded design with a fixed known-key allowlist | Heading-bounding was structurally incapable of removing any capture (a `## ` heading already closes the scan) and widened the carrier into prose and fenced examples. The allowlist distinguishes `Owner: Eng` from `Problem: the gate fails.` by the only thing that actually differs, the key | Heading-bounded scan, disproved by the readiness council; tightening the shared `_FRONTMATTER_METADATA_RE`, which other callers depend on |
| 2026-08-07 | Tolerate blockquotes inside the carrier | The one real boundary error the census found is early truncation at a `> **REFRAMED...**` blockquote, leaving genuine frontmatter digest-significant. Tolerance fixes it; the census pins that nothing else changes | Keep blockquote-closes-region, preserving a measured wrong result |
| 2026-08-07 | Unknown keys close the region | Erring toward early closure produces visible approval churn on a status advance, which operators notice and can repair; erring toward capture silently erases contract edits from the digest. Churn direction measured at zero instances today | Census-everything allowlist frozen forever, which would admit junk keys observed once; shape-based scan, which is the defect |
| 2026-08-07 | State the guard's admissible counts explicitly rather than copying the siblings | The siblings normalize a single line; this function normalizes a legitimate pair. Copying `!= 1` would stop normalizing 794 documents and lapse approvals on every subsequent status advance | Literal sibling guard, measured as a mass-lapse; no guard at all, leaving anomalous shapes silent |
| 2026-08-07 | Keep the change despite zero live instances | The digest decides which edits lapse approvals, so a hole in it is a correctness defect whether or not it has fired. The transition cost is measured at zero non-closed waves, so fixing it now is cheaper than fixing it after it fires | Defer until an instance appears, accepting that the first instance is by definition an undetected contract change |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| The allowlist misses a key a real document uses, closing the region early | Failure direction is churn, not silence: the un-normalized status line makes the digest move on a status advance, which is visible. AC-6's captured-set census proves the shipped allowlist changes exactly the one intended document today |
| The fix stops normalizing legitimate frontmatter | AC-2 is the control; without it a normalizer that did nothing would satisfy AC-1 |
| The guard is copied from the siblings and lapses 794 documents | AC-4 states the admissible set in code and AC-5 pins the wrong implementation as a failing test |
| A downstream repository pays a re-Prepare we never see | AC-6 makes the census part of the deliverable, and the changelog states the transition alongside the wave's evaluator bump |
| Blockquote tolerance admits a prose blockquote that precedes a body status line | The region still closes at the first unknown-key or non-metadata line after the blockquote; AC-3 pins the fence and unknown-key closures. A blockquote alone cannot reopen a closed region. One residual vector is real and accepted: a `Status:` prose line sitting immediately beneath a title blockquote would be admitted into the region and normalized. Zero corpus instances today, proven by the census diff being exactly one document, and the shape requires status prose directly under a title blockquote, which no template produces |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
