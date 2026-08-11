# Prepare And Close Crash On An Undecodable Change Document

Change ID: `1uu9z-bug prepare-crashes-on-an-undecodable-change-doc`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-08-09
Wave: 1uwpf receipt-and-citation-contract-followups

## Rationale

`wf_prepare_wave_response` reads each admitted change document with `change_text = change_path.read_text(encoding="utf-8")` and does not handle a decode failure. A change document that is not valid UTF-8 raises `UnicodeDecodeError` out of the tool instead of returning a diagnostic.

**The same input is handled deliberately one layer down.** Wave `1usqm`'s change `1upba` classified exactly this condition as *environmental* rather than *repairable*: `_prepare_policy_state` catches `OSError`/`UnicodeError` on its own read and tags the result `PolicyInputError("read", …)`, and `POLICY_INPUT_DEGRADABLE_CAUSES` contains `"read"` alone, so a readiness approval **warns and accepts** on an undecodable document — pinned by `test_an_accepted_degraded_approval_is_actually_appended`. The reasoning was that an unparseable plan must never make approvals unrecordable.

That reasoning applies at least as strongly to prepare. An operator whose change document was corrupted by a bad checkout or a mangled paste gets a stack trace from the tool that exists to tell them what is wrong, on the same input the approval path handles gracefully. The two behaviors are inconsistent, and the harsher one is on the surface an operator reaches first.

**The site set is FIVE, not two, and neither of the two originally named is actually unguarded.** An earlier revision of this plan claimed two unguarded sites. Both readiness seats censused it by AST rather than by grep and produced this:

| Site in `server_impl.py` | Existing guard | Undecodable input | Named originally |
|---|---|---|---|
| `wf_prepare_wave_response` | `except OSError` → `change_doc_unreadable` → `continue` | **raises** | yes |
| `_collect_silent_unchecked_items_for_close` | `except OSError` → `continue` (silent) | **raises** | yes |
| `_generate_wf_close_wave_summary` | none | **raises** | **no** |
| `_wave_code_footprint` | `except OSError` → `return None` | **raises** | **no** |
| `wf_implement_wave_response` | none | raises when reached | **no** |

`UnicodeDecodeError` is not an `OSError` subclass, so every `except OSError` above passes it through.

**The AC-6 census — twelve functions, not five, corrected twice.** The five-site table above records the readiness council's correction of the original two-site claim; the census run at implementation, by AST over `HEAD`'s `server_impl.py`, found the set is larger again. The "Guard at `HEAD`" column lists the handlers present in each **function**, in source order — not the handler enclosing each read; the per-read cells are in the column correction below the table. Recorded here so the count stops moving:

| Function | `read_text` sites | Guard at `HEAD` | Disposition |
|---|---|---|---|
| `wf_prepare_wave_response` | 4 | `OSError`, `(OSError, ValueError)`, `ValueError`, `OSError` | widened; existing `change_doc_unreadable` preserved |
| `wf_implement_wave_response` | 2 | none | handler added |
| `_generate_wf_close_wave_summary` | 1 | none | handler added |
| `_collect_silent_unchecked_items_for_close` | 1 | `OSError` → silent `continue` | widened **and** made visible (AC-4) |
| `_wave_code_footprint` | 2 | `OSError`, `Exception` | widened |
| `_wave_has_gapfill_note` | 1 | `OSError` (whole-loop) | widened **and** moved per-document |
| `wf_get_change_response` | 2 | `OSError` | widened |
| `_resolve_change_doc_matches` | 1 | `OSError` | widened; now matches with `read_error` set |
| `_mark_change_item_response` | 2 | `(OSError, ValueError)` | widened |
| `wf_add_change_response` | 3 | `ValueError`, `OSError`, `OSError` | widened; readability probe added before `_move_change_doc` |
| `_parse_plan_record` (under `wf_list_plans`) | 1 | none | handler added at delivery review — the twelfth function, found by the code lane |
| `_prepare_policy_state` | 0 | `(OSError, UnicodeError)` | **untouched** — ships from `1upba`, out of scope; its message rendering routed through `_read_error_detail` at reverification |

`get_change` and `resource_change` carry no handler of their own; they signal on the resolver's `read_error` rather than returning empty content.

**Census correction at delivery review — the set is twelve, not eleven.** The delivery code lane ran its own AST census over all 119 `read_text` calls and found `_parse_plan_record` (under `wf_list_plans`) unguarded — and `wf_list_plans` is the `recovery_tools` entry on `wf_add_change`'s error exits, the exact second-stack-trace shape AC-2b names. Now guarded, reported per entry with `read_error` plus a `change_doc_unreadable` diagnostic, tested for both causes. Two inner `wf_add_change_response` handlers (metadata repair, broken-link scan) sit **behind** the readability probe and are reachable only by a read failing between the probe and a re-read of the same file; they are deliberate TOCTOU backstops and carry no direct test.

**Column correction (readiness reverification, red-team seat): "Guard at `HEAD`" listed handlers present in each function, not the handler enclosing each read.** Re-derived per-read from `HEAD` by mapping every `read_text` to its nearest enclosing `try`: `wf_prepare_wave_response` NONE/`OSError`/NONE/NONE, `wf_get_change_response` NONE/`OSError`, `_mark_change_item_response` NONE/`(OSError, ValueError)`, `wf_add_change_response` NONE/`OSError`/NONE, `wf_implement_wave_response` NONE/NONE, `_generate_wf_close_wave_summary` NONE, `_wave_code_footprint` `OSError`/`OSError`, and the three single-read helpers as listed. The load-bearing conclusion is unchanged — no change-document read at `HEAD` caught `UnicodeError` — but several table cells credited a guard to a read it did not enclose.

**Scope boundary, stated concretely rather than by omission: `wave.md` reads stay unguarded.** The Scope's "reads of documents other than admitted change docs" exclusion covers wave records, and the same crash shape this change fixes survives there — an undecodable `wave.md` raises `UnicodeDecodeError` out of `_parse_wave_record` in the same tools (executed by the red-team seat at reverification). That is a declared boundary, not an oversight, and it needs its own change; the sibling hole of a **missing** (not unreadable) admitted document silently skipped by the close hard gate is recorded with it.

**The close-boundary catch is a TOCTOU backstop too, and is now exercised as one.** In-process, `_collect_silent_unchecked_items_for_close` blocks first over the identical change set, so `_generate_wf_close_wave_summary`'s caller-side catch fires only when a document becomes unreadable between the hard-gate scan and the summary read. The race is simulated under test (hard-gate helper patched to see nothing, every other gate passing) and the boundary returns `change_doc_unreadable` without raising.

Three sites in this census were found neither by the original plan nor by the readiness council: `_wave_has_gapfill_note`, `_resolve_change_doc_matches`, and `wf_add_change_response`. The last is the one that mattered — widening the resolver to *match* unreadable documents let `wf_add_change(mode='create')` reach `_move_change_doc` and relocate a file it could not read, so the guard that made one tool honest made another tool destructive.

**The miss is decisive rather than cosmetic.** `_generate_wf_close_wave_summary` is called from the same `wf_close_wave` body as `_collect_silent_unchecked_items_for_close`, so **AC-2 could not have been met by fixing the site this plan named**. A seat proved it by patching the named site to return `[]` and re-running close, which still raised. The plan's own Requirement 3 exists to prevent exactly this and its census produced the wrong answer; the corrected baseline is recorded here so the census confirms rather than discovers.

`wf_get_change_response` and `_mark_change_item_response` raise on the same input too. `wf_get_change` matters especially: it is the recovery tool `change_doc_unreadable` already names, so today's diagnostic sends the operator into a second stack trace.

All sites predate `1usqm` and none was introduced by it. They are recorded here because `1usqm` is what made the inconsistency visible.

## Requirements

1. **No site raises out of a tool.** An undecodable admitted change document produces a diagnostic naming the document and the cause at the **tool boundary** — `wf_prepare_wave_response`, `wf_close_wave`, `wf_implement_wave`, `wf_get_change`. Helper-level sites (`_collect_silent_unchecked_items_for_close`, `_generate_wf_close_wave_summary`, `_wave_code_footprint`) surface the condition to their caller rather than emitting diagnostics themselves; `_collect_silent_unchecked_items_for_close` returns `list[dict[str, str]]` and has no diagnostics channel, so requiring it to emit one is not implementable.

2. **Prepare REFUSES, and this requirement previously said the opposite.** An earlier revision inferred "degrade and continue" from `_prepare_policy_state`'s handling. Both seats rejected the inference, and prepare already ships the refusal: its `except OSError` emits `change_doc_unreadable`, which is **blocking** — executed with an unreadable document, prepare returns `status: error`.

   The inference does not transfer, and the reason is worth stating because it is the load-bearing judgment of this change. `_prepare_policy_state` is a **selection** helper whose degradation protects one narrow invariant: an unparseable plan must not make an *approval* unrecordable. It degrades by dropping the document from `change_inputs`, computing the digest over a **subset** of admitted changes. Prepare is a **decision** tool — it selects lanes, mints a roster, and publishes a receipt over the full admitted set. Degrading there would publish a receipt whose digest silently omits an admitted change, which is a weaker authority artifact, not a friendlier one.

   So: **report and refuse, naming the document**, at every tool boundary. Close refuses for the same reason — the close hard gate cannot be verified over a document that cannot be read. This also removes the tension with Requirement 1's visibility rule, which refusal satisfies trivially.

3. **A census establishes the real site set before any fix.** Two sites are known. The fix covers every unguarded `read_text` over an *admitted change document* in the lifecycle tools, enumerated first. A fix applied to the two known sites while a third exists is the shape this plan exists to correct.

4. **Each site is fixed from its actual starting position, which differs.** An earlier revision asserted every site was unguarded and that `OSError` needed adding everywhere. Three of the five already catch `OSError`; two do not.

   - Where `OSError` is already caught (`wf_prepare_wave_response`, `_collect_silent_unchecked_items_for_close`, `_wave_code_footprint`): **widen the existing except to `(OSError, UnicodeError)`** and preserve the existing diagnostic and control flow. At prepare this ships **no new diagnostic** — `change_doc_unreadable` already exists with the right message and recovery tools.
   - Where nothing is caught (`_generate_wf_close_wave_summary`, `wf_implement_wave_response`): add the paired handler.

   `wf_get_change_response` is fixed in the same change, because it is the recovery tool `change_doc_unreadable` names and it raises on the same input.

5. **No change to what prepare decides.** This adds error handling to a read. It must not alter lane selection, the receipt, the roster, or any gate outcome for a document that decodes normally.

## Scope

**Problem statement:** Two lifecycle tools crash on an input that a third layer handles deliberately and gracefully, and the crash surfaces on the tool an operator reaches first.

**In scope:**

- The five change-document read sites enumerated in the Rationale, plus `wf_get_change_response` and `_mark_change_item_response`, plus any further site the Requirement 3 census finds.
- The deliberate behavior change at the close boundary (Requirement 1 / AC-4): an unreadable document stops being silently skipped.
- Regression tests reproducing the crash red-first at each tool boundary.

**Out of scope:**

- `_prepare_policy_state`'s handling, which already ships and is pinned.
- The degradable-cause taxonomy. `POLICY_INPUT_DEGRADABLE_CAUSES` and `PolicyInputError` shipped in `1upba` and were verified by four delivery lanes; this change consumes that classification rather than revisiting it.
- Reads of documents other than admitted change docs.

## Acceptance Criteria

- [x] AC-1: `wf_prepare_wave_response` on a wave with an undecodable admitted change document returns a response rather than raising, reproduced **red-first** — the test must fail with `UnicodeDecodeError` against current code.
- [x] AC-2: `wf_close_wave` on the same wave returns a response rather than raising, red-first. **Both** close-path sites must be fixed for this to pass — `_collect_silent_unchecked_items_for_close` and `_generate_wf_close_wave_summary` are called from the same `wf_close_wave` body, and a seat proved that patching only the first still raises from the second.
- [x] AC-2b: `wf_implement_wave` and `wf_get_change` on the same wave return responses rather than raising. `wf_get_change` is required rather than optional: it is the recovery tool `change_doc_unreadable` already names, so leaving it broken sends the operator from the diagnostic into a second stack trace.
- [x] AC-3: The diagnostic names the offending change document and the cause, asserted on message content rather than on the diagnostic code alone.
- [x] AC-4: The unreadable document is **visible** in the response, not silently dropped. Asserted directly, because "handle the error" and "skip the file" produce the same non-crashing result and only one is correct. This is a **deliberate behavior change at the close boundary**: `_collect_silent_unchecked_items_for_close` currently catches `OSError` and skips silently, so an unreadable document is excluded from the close hard gate today and close proceeds. Making it visible turns that into a blocker, which is the correct outcome — the gate cannot be verified over a document that cannot be read — and is disclosed rather than discovered.
- [x] AC-5: `OSError` is covered at each site, asserted separately from the decode case. At the three sites that already catch it, the existing diagnostic and control flow are **preserved rather than replaced**, verified by diff — at prepare this means `change_doc_unreadable` still carries its message and recovery tools and no new diagnostic ships.
- [x] AC-6: The census from Requirement 3 is recorded in this document, listing every admitted-change-document read in the lifecycle tools with its existing guard and its disposition. It is run with an **AST guard-analysis** — mapping each `read_text` to its enclosing function and enclosing `try` — not a grep for the literal string, which is the method that produced the wrong count of two.
- [x] AC-7: A wave whose change documents all decode normally produces a byte-identical response before and after this change, at every touched tool. Baseline captured **after `1uugh` settles**, since that wave is concurrently rewriting prepare's envelope construction in the same uncommitted file, and normalized for the temp root path. Responses were confirmed deterministic across repeated runs, so the comparison is sound.
- [x] AC-9: Any return or diagnostic added inside `wf_prepare_wave_response` routes through `_prepare_envelope`. Wave `1uugh` AC-4 is a source-derived AST test asserting every return in that function does; a new bare return would fail it.
- [x] AC-10: `wf_add_change` refuses an unreadable change document **before any move**, in both `dry_run` and `create`, for both causes — the source stays in `docs/plans/` and no file appears in the wave directory. Added during delivery review: the behavior shipped and was disclosed in the CHANGELOG but was pinned by no AC, and it exists because widening the resolver to *match* unreadable documents let `create` reach `_move_change_doc` and relocate a file it could not read.
- [x] AC-11: One unreadable document no longer disables the retrieval-posture scan for the whole wave — `_wave_has_gapfill_note` guards per document, with the unreadable file sorting **before** a later document carrying the note, so a per-loop guard cannot pass it. Added during delivery review for the same reason as AC-10.
- [x] AC-12: No read-failure message carries the absolute repository path. Found red-first when AC-5's permission subtests were added: an OSError's `str` embeds the absolute path ("Permission denied: '/…'"), so every site interpolating the raw exception re-leaked the path its message had just rendered repo-relative. All read-failure text routes through one helper (`_read_error_detail`), asserted across prepare, get_change, mark, and close.
- [x] AC-8: The full framework suite and docs-lint pass.

## Tasks

- [x] Run and record the census (AC-6) before editing.
- [x] Write the red-first reproductions for both known sites.
- [x] Add the guards, matching `_prepare_policy_state`'s `OSError`/`UnicodeError` pairing.
- [x] Pin AC-4 and AC-7 explicitly; both are ways a plausible fix goes wrong.
- [x] Run the full suite and docs-lint.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| census | implementer | — | AC-6; the site set is not assumed to be two |
| red-tests | implementer | census | Must fail with `UnicodeDecodeError` before the fix |
| guards | implementer | red-tests | Mirror the shipped `_prepare_policy_state` pairing |


## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/server_impl.py`
- `.wavefoundry/framework/scripts/tests/test_server_tools.py`
- `docs/specs/mcp-tool-surface.md`

## Affected Architecture Docs

`docs/architecture/data-and-control-flow.md` is **read, not edited**, and the reason it is named rather than `N/A` is that this change alters a gate outcome the document describes.

No boundary moves and no data-flow changes. Two corrections to what an earlier revision of this section claimed:

- It said "two existing reads". The AST census (AC-6, corrected at delivery review) puts the paired `(OSError, UnicodeError)` handler in **12 functions**, of which `_prepare_policy_state` predates this change and ships from `1upba` — so **11** are touched here: `wf_prepare_wave_response`, `wf_implement_wave_response`, `wf_get_change_response`, `wf_add_change_response` (three sites), `_resolve_change_doc_matches`, `_mark_change_item_response`, `_collect_silent_unchecked_items_for_close`, `_generate_wf_close_wave_summary`, `_wave_code_footprint`, `_wave_has_gapfill_note`, and `_parse_plan_record` (under `wf_list_plans`). `get_change` and `resource_change` change behavior without adding a handler, by signalling on the resolver's `read_error` instead of returning empty content.
- It said "no gate outcome changes", qualified by "for input that decodes". The qualifier is true but the sentence read as a denial of the change AC-4 exists to disclose. **For an undecodable or unreadable document the close gate outcome does change deliberately**: `_collect_silent_unchecked_items_for_close` skipped it silently, so close proceeded; it is now a blocker. `_wave_has_gapfill_note` changes the same way — a single unreadable document no longer disables the retrieval-posture scan for the whole wave. For input that decodes, behavior is unchanged and AC-7 pins it.

## AC Priority


| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The reported defect, on the surface an operator reaches first. |
| AC-2 | required | Proved unsatisfiable by the original two-site scope: patching the named close site still raised from the second. |
| AC-2b | required | `wf_get_change` is the recovery tool the diagnostic names; a broken recovery path turns one crash into two. |
| AC-3 | required | A bare code reproduces the confusion the crash already causes — the operator still would not know which document. |
| AC-4 | required | "Handle the error" and "silently skip the document" are indistinguishable by a non-crash assertion, and only one is correct. |
| AC-5 | important | Same operator problem, same class; splitting them would leave half the case. |
| AC-6 | required | The site count went from one to two while writing this plan. It should not go to three during review. |
| AC-7 | required | The change must be invisible for normal input. |
| AC-9 | required | `1uugh` restructured this function and pins the property by AST; a bare return added here fails that wave's test. |
| AC-10 | required | Shipped behavior on a public lifecycle tool; undisclosed-in-contract until delivery review flagged it. |
| AC-11 | important | Advisory-path behavior change; disclosed in Affected Architecture Docs but previously pinned by no AC. |
| AC-12 | required | Operator-facing text leaked the filesystem layout; the decode-only pin could not see it. |
| AC-8 | required | Standard gate. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-08-10 | Both WITHHELD lanes confirmed the folds and moved to APPROVE, making the round 6/6. The code lane re-proved the leak-fix non-vacuity independently (helper monkeypatched back to the raw formatter, read-only: test fails on the exact absolute-path assertion) and diffed the delta since its review down to the three one-line routings. Docs-contract independently re-derived all twelve census site counts from HEAD. One out-of-scope residual recorded for a future wave: `_replace_artifacts_transactionally` raises a synthetic single-arg `OSError` whose detail embeds absolute rollback paths, defeating `strerror` at the publish handler for that one exception shape; the cheap fix is at the raise site | confirmation reports, both executed |
| 2026-08-10 | REVERIFICATION ROUND, five focused lanes: readiness 2/2 APPROVE; delivery qa and architecture APPROVE, code and docs-contract WITHHELD with prescribed fixes, all folded here. The code lane found the leak repair had missed `_prepare_policy_state`'s policy-selection message — the sanitized and the leaking string sat ADJACENT in one real-config prepare envelope — and proved the leak test vacuous for prepare (its fixture had no `wave_review` config, so the leaking line was never reached). Routed through `_read_error_detail`, fixture widened with a reachability assertion, and the reverted-leak mutant now fails the test | executed repro by the code lane; red-proof re-run after the fix |
| 2026-08-10 | The two TOCTOU-only raw interpolations (`change_metadata_repair_failed`, the publish handler) routed through the same helper, closing qa's AC-12-prose gap. qa's cause-half mutants (message drops the exception type at prepare/implement/close) now die: assertions added at all three surfaces | qa mutants C25a, C12, C-close-detail |
| 2026-08-10 | Twelve-count propagated everywhere it was stated after the docs-contract lane found the census correction had landed in code and tests but not in four enumerations — the CHANGELOG's "Eleven read sites" and its closed boundary list, the spec's silent `wf_list_plans` entry, this document's own Affected Architecture Docs, and the census heading itself. The same defect class this cycle repaired in `1uu0f`'s entry, reintroduced one entry over | all four reconciled; spec documents `read_error`, the per-entry diagnostic, and the post-`limit` non-scan |
| 2026-08-10 | qa reverification (scratch-tree sweep, zero repo mutations): every named survivor killed — A4/B4, A10/B10, B2, B13, C14, C17 — with the race test PROVEN to reach the summary site by instrumentation. A14/B14 are equivalent mutants (`UnicodeError` subclasses `ValueError`; no `OSError` escapes the summary), so the boundary tuple carries dead breadth, recorded as cosmetic. Four fresh mutants against `_read_error_detail` all die | qa mutation table |
| 2026-08-10 | Architecture reverification settled the intermittent suite failure that recurred all session: `test_repeated_warm_estimator_and_projection_budgets`, a p95 perf budget that fails under full-suite parallelism AT HEAD TOO (41.6ms there vs 25ms budget, from a clean `git archive` extract). Pre-existing machine contention, not this wave; passes in isolation every time | executed at HEAD and working tree |
| 2026-08-10 | DELIVERY REVIEW REPAIR CYCLE, six lanes all WITHHELD on the wave (primarily on since-withdrawn `1us4q`; this change's own findings folded here). The twelfth census site fixed: `wf_list_plans` raised `UnicodeDecodeError` on an unreadable plan doc. The close diagnostic partitioned: an unreadable document is its own `change_doc_unreadable` diagnostic naming the file and a repair action, no longer a false `silent_unchecked_items_at_close` count with an impossible instruction | code lane census; both fixes tested both causes |
| 2026-08-10 | AC-2's boundary claim repaired honestly. The tool-boundary test asserted only that the document name appeared somewhere in the response; the second close-path site was reached ZERO times under test because this change's own hard-gate repair returns first, and all three narrowings of the boundary handler survived qa's mutation sweep. The catch is a TOCTOU backstop and is now tested as one, by simulating the race | qa traced-probe evidence; race test added |
| 2026-08-10 | AC-5 completed at the sites qa proved unpinned: `_mark_change_item_response` (both causes), `_wave_code_footprint` (both causes, degrades to None), bulk `wf_get_change` OSError direction, and `_generate_wf_close_wave_summary` both causes. The two `wf_add_change` inner handlers are recorded as untested TOCTOU backstops rather than silently counted as covered. A vacuous assertion qa found (a stem asserted against a dict repr the comprehension already guaranteed) replaced with assertions on `item_text` content | mutation survivors A4/B4, A7-A10, B2, B13 now killed or explicitly dispositioned |
| 2026-08-10 | AC-12 found red-first BY the AC-5 repair: extending the wave-relative-path pin to the permission cause failed immediately, because `PermissionError.__str__` embeds the absolute path. Every read-failure message now routes through `_read_error_detail` (strerror-only for OSError), asserted across four surfaces. The decode-only pin structurally could not catch this — `UnicodeDecodeError.__str__` carries no path | red test first, then the helper; leak audit across five tools |
| 2026-08-10 | AC-7's test docstring corrected to what it holds: ok status, zero read diagnostics, determinism. It is not the before/after proof; qa showed a field-adding mutant survives it. The real comparison ran once against the reconstructed pre-guard shape across eight surfaces (byte-identical, recorded above) and is not reproducible from HEAD without mutating the tree | qa mutant C27; docstring now states the boundary |
| 2026-08-10 | AC-6 census re-run at implementation by AST over `HEAD`: the site set is ELEVEN functions, not the five the readiness council corrected it to. Three were found by neither the plan nor the council. The decisive one: widening `_resolve_change_doc_matches` to MATCH unreadable documents let `wf_add_change(mode='create')` reach `_move_change_doc` and RELOCATE a file it could not read, so the guard that made one tool honest made another destructive. A readability probe now refuses before any move, verified for both decode and PermissionError in `dry_run` and `create` | AST census recorded in `## Rationale`; executed both modes, source still in `docs/plans/`, target absent |
| 2026-08-10 | MUTATION TESTING: the delivered suite killed 3 of 12 guard mutants, including a survivor of AC-4's OWN falsifying mutant (catch-then-`continue`, which is non-crashing and indistinguishable from the fix without a visibility assertion). Nine tests added across the tool boundaries; the sweep now kills 12 of 12, each naming the killing test | mutation sweep, restored byte-identical after every mutant |
| 2026-08-10 | AC-2 was met only at the helper, not the boundary the AC names. `_collect_silent_unchecked_items_for_close` was asserted directly, which is exactly the shape a readiness seat proved insufficient — patching that helper alone left `wf_close_wave` raising from `_generate_wf_close_wave_summary`. A `wf_close_wave_response` test now covers both sites | test added; mutant removing the second handler is killed |
| 2026-08-10 | AC-7 verified as a real before/after rather than a self-comparison. The delivered test compared two calls of the SAME build, which cannot detect a regression. Re-run against the pre-guard code shape (every paired handler narrowed to `OSError`, probe removed) across eight touched surfaces: byte-identical for input that decodes | executed both builds, responses normalized for the temp root |
| 2026-08-10 | Close diagnostic leaked the absolute repository path: `_generate_wf_close_wave_summary` has no root to hand `_repo_rel`, so its first version interpolated `change_path`. Now wave-relative, pinned by a test asserting the root string is absent | mutant restoring the absolute path is killed |
| 2026-08-10 | Three out-of-scope widenings reverted: `_index_dir_size`, `_memory_cache_key`, `wf_start_dashboard_response` had been widened to `(OSError, UnicodeError)` although none reads a change document. Every review lane flagged them as dead handlers | reverted; paired-handler count 16 to 13 |
| 2026-08-09 | READINESS COUNCIL: the census was wrong in BOTH directions and the plan's central premise failed. Not two sites but five, and neither of the two named was actually "unguarded" — both already catch `OSError`, which `UnicodeDecodeError` does not subclass. Decisively, a seat patched the named close site to return `[]` and re-ran close: it STILL raised, from `_generate_wf_close_wave_summary` in the same `wf_close_wave` body. AC-2 was unsatisfiable by the declared scope. Requirement 3 exists to prevent exactly this and its own census produced the wrong answer, because it grepped a literal string instead of walking the AST for enclosing guards | both seats, AST census plus an executed fix simulation |
| 2026-08-09 | Requirement 2 was BACKWARDS and is rewritten. It inferred "degrade and continue" from `_prepare_policy_state`; prepare already REFUSES via a blocking `change_doc_unreadable`, verified by execution. Red-team supplied the argument for keeping that: `_prepare_policy_state` is a SELECTION helper that degrades by computing the digest over a subset, protecting the narrow invariant that an unparseable plan must not make an approval unrecordable, whereas prepare is a DECISION tool that mints a roster and publishes a receipt over the full admitted set — degrading there would publish a receipt whose digest silently omits an admitted change. Report and refuse, at every boundary | red-team, executed against a chmod-000 fixture |
| 2026-08-09 | Three consequences folded that the original framing hid: the close-boundary fix is a deliberate GATE-OUTCOME change (an unreadable doc is silently skipped today, so close currently proceeds), `wf_get_change` must be fixed in the same change because it is the recovery tool the diagnostic already names and it raises on the same input, and `_collect_silent_unchecked_items_for_close` cannot emit a diagnostic at all since it returns a list with no diagnostics channel — so Requirement 1 now separates tool boundaries from helper sites | both seats |
| 2026-08-09 | Ordering constraint added after the council found wave `1uugh` is `implementing`, not readied: its implementation is in the uncommitted tree and it restructured `wf_prepare_wave_response`, the function this change edits. AC-9 now requires any added return to route through `_prepare_envelope`, because `1uugh` AC-4 pins that property by AST test, and AC-7's baseline is captured after `1uugh` settles | red-team verified `Status: implementing` and the symbols in the tree |
| 2026-08-09 | Found by the code-reviewer delivery lane during wave `1usqm` and recorded as pre-existing and out of scope there. Both sites predate that wave; `1usqm` made the inconsistency visible by handling the same input deliberately one layer down | `1usqm` code lane |
| 2026-08-09 | SECOND SITE found while writing this plan rather than taken from the lane report: `_collect_silent_unchecked_items_for_close` performs the same unguarded read, so the corrupted document that crashes prepare also crashes close. That is why Requirement 3 makes the census a gate instead of assuming the reported site is the only one | census of the `change_path.read_text` pattern |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-08-09 | Report and REFUSE rather than degrade | An earlier revision chose degradation by inference from `_prepare_policy_state`. Both seats rejected it and prepare already refuses. Degrading in a decision tool would publish a receipt whose digest silently omits an admitted change — a weaker authority artifact, not a friendlier one. Refusal is fail-closed and also makes the visibility requirement trivially satisfied | Degrade and continue (rejected: the selection-helper inference does not transfer to a tool that mints authority); keep the crash (rejected: it is the defect) |
| 2026-08-09 | SUPERSEDED — Degrade with a diagnostic rather than refuse | `1upba` already classified an undecodable change document as environmental and degrades on it, with the reasoning that an unparseable plan must never make approvals unrecordable. Prepare being stricter than the approval path about the same input is the inconsistency this change removes | Refuse and require repair before prepare proceeds (rejected: inconsistent with the shipped classification, and prepare is where an operator goes to find out what is wrong) |
| 2026-08-09 | Keep out of `1uugh advisory-diagnostic-severity` despite touching the same function | `1uugh` is scoped to how a diagnostic is CLASSIFIED and its Requirement 8 forbids shipping new diagnostics. This change ships new diagnostics for a different failure class, and admitting it would move `1uugh`'s canonical text and re-open a readiness cycle that took four review rounds | Fold into `1uugh` (rejected on both scope and readiness cost) |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| The fix silently skips the unreadable document | AC-4 asserts the document is visible in the response; a non-crash assertion alone cannot tell the two apart |
| A third unguarded site exists | AC-6 requires the census before editing, which is how the second site was found |
| The guard changes behavior for documents that decode normally | AC-7 pins byte-identical responses for the normal case at both tools |
| The reproduction passes without proving the defect | AC-1 and AC-2 require red-first, failing specifically with `UnicodeDecodeError` |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
