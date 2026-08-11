# Diagnostics Conflate Information With Failure

Change ID: `1uugg-debt advisory-diagnostics-need-a-severity`
Change Status: `implementing`
Owner: Engineering
Status: planned
Last verified: 2026-08-10
Wave: 1uugh advisory-diagnostic-severity

## Rationale

`wf_prepare_wave_response` decides whether a call failed by asking `if diagnostics:`. That treats "there is something to say" as "this failed", and there is no way to attach an informational diagnostic to a successful response.

**This extends a documented local precedent; it does not restore a global guarantee.** `docs/specs/mcp-tool-surface.md` defines the `diagnostics` array as carrying "Named **warnings**, validation failures, blocked preconditions, or recovery details". Its lifecycle-focus diagnostics are observational because they are appended only after their lifecycle result is derived. Prepare lacks an equivalent carrier for an informational condition that must cross its gates. This change establishes that carrier for prepare only; it neither retroactively classifies every existing non-blocking diagnostic nor widens other lifecycle tools' contracts.

Wave `1usqm` hit this directly and shipped a workaround. `1upba` needed `prepare(mode='dry_run')` to report a pending receipt mint, which is **information**: dry-run writes nothing, and a pending mint is the ordinary state after any change-doc edit. Three placements were attempted:

1. **At the response envelope.** Never reached, because prepare returns early on several paths — a missing council signoff among them, which is exactly when an operator is previewing.
2. **On the shared `diagnostics` list.** Flipped `status` from `dry_run` to `error`. Measured by the `1usqm` architecture review lane:

   ```
   NO pending mint            -> status: dry_run  diag: []                 (15 data keys)
   PENDING mint, wiring ON    -> status: error    diag: [receipt_stale]    (10 data keys)
   ```

   The envelope lost `readied`, `transitioned_to_active`, `council_verdict_present` and `council_verdict_valid`, and the council-verdict validation after the gate never ran. Worse, `error` is not in `LIFECYCLE_ENGAGED_STATUSES` (verified: `frozenset({"ok", "dry_run", "ready_for_council_review"})`), so every ordinary preflight silently reclassified as **not-engaged** in focus and context-efficiency telemetry.
3. **A parallel `_prepare_stale_advisories` list.** This is what shipped: two error returns splat it, and the success return merges it via `_ac_advisories`. The other five returns drop it.

**An earlier revision of this plan claimed the shared `diagnostics` list "reaches every return automatically". That is FALSE and the readiness council falsified it.** An AST walk of `wf_prepare_wave_response` finds **8 return statements, of which only 3 forward the shared list**. Two of the five that drop it construct fresh diagnostic lists post-gate: the `prepare_council_verdict_missing` return sits *between* the two gates and the `review_projection_failed` return sits after both. Today that is harmless because reaching them requires `diagnostics` to be empty; under this change it would not be, so simply moving advisories onto the shared list **reproduces the same defect at two new sites**.

So the fix cannot be "use the other list". It has to be structural: no return site may construct a diagnostics list at all.

## Requirements

1. **Within prepare, non-blocking is a property of the diagnostic, carried as `advisory: bool`.** `_diagnostic(...)` gains `advisory: bool = False`, and the key is **omitted from the payload when `False`**, matching the existing convention for `recovery_tools` and `recovery_usage`. The prepare gates recognize an advisory only when `diagnostic.get("advisory") is True`; absent, `False`, malformed, or truthy non-boolean values stay blocking. Two consequences make this the right shape: no existing diagnostic payload changes shape at all, and the default preserves today's blocking behavior exactly. This is a prepare-local classification change: existing diagnostics outside the explicitly listed prepare contributors remain unchanged and other lifecycle tools retain their current semantics.

   **The field is NOT named `severity`.** That word is already an entrenched five-level scale in this repository — `SEVERITY_ORDER = ["none", "low", "medium", "high", "critical"]`, `ReviewAuthority.max_severity()`, the `high_severity_finding` diagnostic — and `data.max_severity: "high"` appears in the same response envelope an operator would read beside it. Two incompatible `severity` scales one nesting level apart is a worse contract than the one being fixed. "Advisory" is already this repository's noun for a non-blocking diagnostic: `empty_roster_advisory`, `_ac_advisories`, `_mem_advisories`, and the spec's own "reported as a non-blocking advisory".

2. **`advisory` is a property of the CONTRIBUTING CALL SITE — the caller that places a diagnostic into one specific response — never of the diagnostic code, and never of the `_diagnostic(...)` construction.** `review_policy_receipt_stale` has **9 emit sites**. Tagging by code would make a real stale receipt and a real publication failure non-blocking.

   **Construction-site tagging is equally wrong here, and an earlier revision of this requirement got it factually wrong.** It claimed the advisory pending-mint is emitted inside `wf_prepare_wave_response`. It is not. The pending-mint dict is constructed in `_review_policy_receipt_diagnostics`, a **shared helper with five callers**:

   | Caller | Treats a pending mint as |
   |---|---|
   | `transact` in `wf_review_event_response` | blocking |
   | `wf_prepare_wave_response`, dry-run only | **the advisory target** |
   | `_evaluate_shared_delivery_state` | blocking (code-keyed) |
   | `wf_review_wave_response` | blocking |
   | `wf_implement_wave_response` | blocking |

   Tagging the construction would stamp `advisory: true` on diagnostics that **block** at three other tools, contradicting the spec Requirement 6 updates on day one — and would plant a fail-open: when the follow-on converts `wf_implement_wave`'s truthiness gate, a genuinely superseded receipt would stop blocking implementation, letting work proceed on a wave whose roster no longer matches its inputs. That is a review-authority weakening delivered by the follow-on but caused here.

   The mechanism is therefore a keyword on the helper — `_review_policy_receipt_diagnostics(root, wave_md, wave_text, *, advisory: bool = False)`.

   **The helper emits three diagnostics, and an earlier revision said its other two "stay blocking". That is wrong about today's tree and would regress dry-run.** Today ALL THREE land in `_prepare_stale_advisories` on the dry-run path and merge non-blockingly into the success envelope. Under Requirements 2 and 4, any emit left untagged lands on the shared blocking list, so `prepare(mode='dry_run')` would flip to `error`, drop the envelope from 15 keys to 10, and leave `LIFECYCLE_ENGAGED_STATUSES` — precisely the failure this change exists to remove. Each is therefore decided explicitly:

   - **Pending mint** (`receipt_append_required`): advisory on the dry-run path. The informational case.
   - **Policy errors**: blocking, and this changes nothing — `policy_state_errors` from the same `_prepare_policy_state` call is already extended into the shared list in **every** mode, so it already blocks dry-run today.
   - **Roster drift** (`persisted != selected`): **advisory on the dry-run path**, argued rather than assumed. It is checked nowhere else in prepare, and it is reachable *without* a pending mint — the persisted value comes from the wave text's `Required review lanes` line while `receipt_append_required` comes from comparing receipt semantics, so a hand-edited roster line moves one without the other. Leaving it blocking would regress that path from `dry_run` to `error` for exactly the same reason as the pending mint, and dry-run writes nothing either way. Requirement 5's rule that any reclassification beyond the pending mint be argued individually is satisfied here rather than skipped.

   Two existing registries classify by code and are deliberately left alone: `_guided_review_authority_blocker.blocking_codes` and `SHARED_DELIVERY_DIAGNOSTIC_CODES`. Both filter on code and ignore `advisory`, so they cannot be softened by this change. The resulting prepare-advisory / close-blocking asymmetry is correct semantics, not drift: a pending mint at prepare dry-run is the ordinary post-edit state and gates nothing, while the same condition at review, close or implement is a real blocker because those gates consume the receipt as authority. The census records that reasoning.

3. **Every consumer of `diagnostics` truthiness is converted, and one of them is a WRITE guard.** `wf_prepare_wave_response` reads that list for truth in **three** places, not one:

   - the failure gate before the council-verdict section,
   - the failure gate after it,
   - **`if _mutating and policy_state is not None and not diagnostics:` — the guard that publishes the review-policy roster and receipt.**

   The third is the dangerous one. Today, skipped publication **implies** a failed call — but not the converse, and an earlier revision asserted the biconditional. The guard runs **before** `missing_wave_council_signoff` and `another_wave_active` are appended, so a `create` or `ready` run carrying either of those already publishes the roster and receipt and *then* returns `error`. The coupling this change breaks is the one-way implication. A blocking-only filter breaks that coupling: an advisory present on a `ready`/`create` run would suppress `_publish_prepare_policy_state` while the call returns `ok` and, at `create`, flips the wave to `active` — **a wave activated with an unpublished receipt and no diagnostic saying so.** All three reads convert together or none do.

4. **No return site constructs a diagnostics list, and advisories live on the SAME list the gates read.** Moving advisories onto the shared list is not sufficient by itself, because 5 of 8 returns do not forward it. Route every envelope through a single prepare-local helper, and have that helper emit **one** list — the same `diagnostics` list the three truthiness consumers evaluate — with advisory entries tagged rather than segregated.

   **This is stated explicitly because a two-list reading makes the whole change vacuous.** If the helper merges a separate advisory list only at the envelope, the advisory never reaches the list the gates read, and then AC-1, AC-2, AC-4, AC-5 and AC-7 all pass **without a single gate being converted** — the two-list convention survives under a new name, which is precisely the defect. The change fails closed in that shape, so it is not a hole; it is worse, it is a green wave that delivered nothing. Requirement 3's conversion is the load-bearing half and must be observable.

   This also absorbs `_ac_advisories`, today the **only** list the success return emits.

5. **A census gates the change.** Enumerate every diagnostic that crosses a gate inside `wf_prepare_wave_response`, with its intended classification, **before** any gate changes. Because the default is blocking, the census is looking for diagnostics that are *wrongly* blocking today. Any reclassification beyond the dry-run pending-mint emit site is argued individually or not made. The census covers **consumers** of `diagnostics` truthiness, not only producers.

   The three lifecycle-focus diagnostics appended by `_append_response_diagnostic` **after** `wf_prepare_wave_response` returns (`focus_target_not_engaged`, `focus_stage_not_applied`, `unknown_lifecycle_outcome`) never reach a gate and are out of the gate census — but they do land in the public `diagnostics` array, so Requirement 6's spec update covers them.

6. **The prepare response-envelope extension is a public MCP contract change, decided here rather than deferred.** `_diagnostic` returns a plain dict placed directly into the envelope, so any key it stores is public by construction; the census cannot answer whether the key ships, only which sites get it. This wave defines `advisory: true` only for the three sanctioned prepare contributors in AC-10c; it does not retrofit historical lifecycle-focus or review-evidence conventions with the field. `docs/specs/mcp-tool-surface.md` is updated at three named sites:

   - `## Response Envelope` — the `diagnostics` row of *Required field semantics*, and the "Diagnostic entries should use stable field names" JSON block, which currently enumerates exactly `code`, `message`, `recovery_tools`, `recovery_usage`.
   - `### Lifecycle Mutations` → *Lifecycle focus reporting (wave 1tmb3)* — distinguish its existing post-result observational convention from this prepare-local flag; lifecycle-focus payloads do not gain `advisory` in this wave.
   - `### Lifecycle Mutations` — the review-evidence-authority paragraph, which already states an empty declared roster "is reported as a non-blocking advisory"; document that this existing convention does not imply a new payload field.

   Consumer impact is disclosed explicitly. Because the key is omitted at default, no existing diagnostic payload changes shape. `_bounded_upgrade_response_envelope` whitelists diagnostic keys to exactly `{code, message, recovery_tools, recovery_usage}` and counts anything else as `omitted_field_count`; it remains unchanged because no advisory reaches that bounded upgrade path (AC-10b proves the other helper callers retain their byte shape).

7. **`1upba`'s workaround is removed with the fix — but no wave record is edited.** The parallel `_prepare_stale_advisories` list and its splat sites go away. The `1usqm` watchpoint recording the fragility is **not** deleted: `AGENTS.md` → *Cleanup and Destructive Operations* prohibits deleting mentions of removed artifacts from wave records and closed-wave archives, and that watchpoint's own closing instruction ("Tracked as its own change; do not tidy this into the shared list without it") is *satisfied* by this wave landing, not falsified. Leaving it makes it accurate history. The resolution is recorded here instead.

8. **Scope stays at the diagnostic contract.** This changes how a detected condition is classified, not which conditions are detected. No new diagnostic ships, and the post-change set of prepare-reachable diagnostic codes is identical to the pre-change set.

## Scope

**Problem statement:** There is no way to attach an informational diagnostic to a successful response, so an informational signal either fails the call or has to be routed around the gate by hand — and the routing cannot be made reliable, because 5 of 8 return sites do not carry the shared list.

**In scope:**

- `advisory: bool = False` on `_diagnostic`, omitted from the payload at default.
- All three `diagnostics` truthiness consumers in `wf_prepare_wave_response`, including the publication guard.
- The single envelope helper that removes per-return diagnostics-list construction.
- Prepare-local advisory classification for exactly the three AC-10c contributors, using a literal-boolean predicate at every prepare gate.
- `_ac_advisories`, folded into that helper.
- The census of gate-crossing diagnostics.
- Removing `_prepare_stale_advisories` and its splat sites.
- The spec update at the three named sites.

**Out of scope:**

- Any change to which conditions produce a diagnostic.
- Extending the model to the other lifecycle tools' gates. Prepare is the measured case; generalize once this is proven.
- Retrofitting lifecycle-focus, empty-roster, or any other existing non-blocking convention with an `advisory` payload key, or changing `_bounded_upgrade_response_envelope`.
- The two code-keyed registries (`_guided_review_authority_blocker.blocking_codes`, `SHARED_DELIVERY_DIAGNOSTIC_CODES`). They classify by code for a different purpose and are deliberately untouched; the census records why.
- Editing **other waves'** records and closed-wave archives (Requirement 7). This wave's own `wave.md` is not frozen, but its current Objective, Summary and Watchpoints already state the live `advisory: bool` design. Historical references to the rejected `severity` design remain as review history rather than creating a live reconciliation task. `AGENTS.md` prohibits deleting mentions of removed artifacts from wave records; it does not freeze an active wave's own summary against its own change.

## Diagnostic Census

**Recorded after the gate change rather than before it.** Requirement 5 and AC-6 specify this census as a gate that runs *before* any consumer is converted. It did not; the conversion shipped first and the census was written during delivery review, when the docs-contract lane found AC-6 marked `[x]` with no such section anywhere in the document and three forward references pointing at it. The census is therefore a confirmation rather than a gate, and that ordering failure is recorded rather than papered over. Everything below is derived from `server_impl.py` by AST walk, not from this plan's prose.

### Consumers of `diagnostics` truthiness

All three convert together, via one predicate:

```python
def _has_blocking_diagnostics() -> bool:
    return any(diagnostic.get("advisory") is not True for diagnostic in diagnostics)
```

| Consumer | Role |
|---|---|
| `if _mutating and policy_state is not None and not _has_blocking_diagnostics():` | **WRITE guard** — publishes the roster and receipt |
| `if _has_blocking_diagnostics():` (first) | Failure gate, before the council-verdict section |
| `if _has_blocking_diagnostics():` (second) | Failure gate, after it |

The predicate is a **deny-list**: absent, `False`, `"false"` and `1` all block; only literal `True` is advisory. An allow-list would fail open on every untagged diagnostic in the tree.

### Diagnostics constructed inside `wf_prepare_wave_response`

21 `_diagnostic(...)` constructions. **Two** carry `advisory=True`:

| Code | Classification |
|---|---|
| `ac_priority_unpopulated` | **advisory** — all modes |
| `prepare_council_verdict_missing` | **advisory** on the dry-run path; **untagged** at its mutating-path (`ready` and `create`) construction. Untagged rather than blocking is the precise word: no gate evaluates it, because the next statement returns `ready_for_council_review` |

`prepare_council_verdict_missing` appearing in both columns is the site-scoping rule working as intended, and is the clearest evidence that classification is a property of the emit site rather than the code.

The other 19 are untagged and unchanged. Eighteen are listed here; the nineteenth is the mutating-path `prepare_council_verdict_missing` recorded in the table above: `invalid_arguments`, `wave_not_found`, `no_admitted_changes`, `review_policy_receipt_stale` (×2 — the `policy_state_errors` loop and the publish-failure handler, both deliberately blocking per AC-10), `another_wave_active`, `duplicate_change_doc_locations`, `change_doc_missing_sections`, `docs_gardener_failed`, `docs_lint_error`, `missing_wave_council_signoff`, `change_not_found`, `change_doc_unreadable`, `review_projection_failed`, `change_doc_not_relocated`, `council_seats_misaligned`, `prepare_council_verdict_invalid`, `change_relocation_failed`.

### Diagnostics contributed by helpers

Prepare extends its list from three helpers. These are **not** visible to a pin scoped to prepare's own source:

| Helper | Call sites in prepare | Classification |
|---|---|---|
| `_wave_review_policy_diagnostics` | 1 | blocking (untagged) |
| `_review_evidence_diagnostics` | 3 | blocking (untagged) |
| `_review_policy_receipt_diagnostics` | 1, dry-run only | **advisory** via the `advisory=True` keyword |

The third advisory site is this helper call. Total sanctioned advisory contributions: **three** — the two direct constructions above plus this one, matching AC-10c.

**This table is why AC-10c must parse the whole module.** A mistag inside `_wave_review_policy_diagnostics` or `_review_evidence_diagnostics` never changes the count of `advisory=True` occurrences in prepare's own source. The delivery code lane demonstrated the consequence: patching `_review_evidence_diagnostics` to tag its blocker advisory fired the publication **write** on a wave with an invalid review-evidence ledger, while the prepare-scoped pin still read 3.

### Code-keyed registries, deliberately untouched

Both filter on `diagnostic.get("code") in <set>` and ignore `advisory`, so neither can be softened by this change:

- `_guided_review_authority_blocker.blocking_codes`
- `SHARED_DELIVERY_DIAGNOSTIC_CODES` — `docs_lint_error`, `missing_executable_approval_evidence`, `missing_operator_signoff`, `missing_required_lane`, `missing_wave_council_signoff`, `review_evidence_invalid`, `review_policy_receipt_stale`, `review_policy_reprepare_required`

The resulting prepare-advisory / elsewhere-blocking asymmetry is correct semantics rather than drift: a pending mint at prepare dry-run is the ordinary post-edit state and gates nothing, while the same condition at review, close or implement is a real blocker, because those gates consume the receipt as authority.

### Code-set equality (Requirement 8)

The set of diagnostic **codes** reachable from `wf_prepare_wave_response` is identical before and after this change. No code was added, removed or renamed; only the classification of three emit sites changed, and `advisory` is omitted from the payload at default so no non-advisory diagnostic changed shape.

## Acceptance Criteria

- [x] AC-1: A diagnostic emitted with `advisory=True` does not make `wf_prepare_wave_response` return `error`, reproduced red-first against the current gate.
- [x] AC-2: A diagnostic **not** built by `_diagnostic` — a bare `{"code": ..., "message": ...}` dict — still blocks. The predicate is exactly `diagnostic.get("advisory") is True`: tests cover absent, `False`, and malformed truthy values such as `"false"` and `1`, all of which must block. This pins the predicate direction and type. The deny-list form `not d.get("advisory")` returns `True` for every diagnostic in the tree and so fails closed; the allow-list form `d.get("blocking") is True` fails open on all of them. (An earlier revision stated this comparison in `"blocking"`/`"advisory"` string tokens, which belong to the `severity` design Requirement 1 abolished and cannot be asserted against a boolean.)
- [x] AC-3: `prepare(mode='dry_run')` with a pending mint returns the same status class and the same envelope key set as the no-pending-mint case, and still carries `review_policy_receipt_stale`. **Both fixtures must be docs-lint clean**, or both return `error` and the assertion compares `error` to `error` — the exact vacuity that shipped in `1usqm`'s version of this test. The fixture must also hold the **persisted roster equal to the selected roster**: `required_lanes` is a receipt-semantic field, so the ordinary add-a-change case moves the roster and the digest together, and a co-occurring roster-drift diagnostic would otherwise make this assertion fail for a second, unrelated reason.
- [x] AC-3b: `prepare(mode='dry_run')` on a wave whose **persisted roster has drifted** but whose receipt has no pending mint still returns `status: "dry_run"` and carries the roster-drift diagnostic as advisory. This is the reclassification Requirement 2 argues explicitly; it is reachable without a pending mint by editing the `Required review lanes` line, and without this AC it is pinned by nothing.
- [x] AC-4: A test parses `server_impl.py` with `ast`, locates `wf_prepare_wave_response`, and enumerates every `Return` whose response call is lexically after the shared `diagnostics` list is defined. It asserts each one routes through the single envelope helper rather than constructing its own diagnostics list. The enumeration is derived from source, so a return added later is covered without editing the test.
- [x] AC-5: An advisory-only diagnostic on a `mode='create'` run still **publishes** the receipt and roster, and the wave still activates. **An earlier revision marked this `[~]`; that narrowing is WITHDRAWN.** It rested on the premise that publication rotates the receipt identity and therefore stales the prior readiness approval in the same call, making activation unreachable. That holds only when `receipt_append_required` is True. On the ordinary ready-approve-create flow it is False, publication is a re-render, the approval stays current, and the wave activates — so the requirement was satisfiable as written. Proved by spy trace during delivery review and pinned by `test_an_advisory_only_create_publishes_and_activates`.
- [x] AC-5b: The negative twin. A `create` run carrying **one advisory and one blocking** diagnostic leaves the roster, receipt ledger and projection untouched and returns `error`. The blocking diagnostic must be one appended **before** the publication guard — a `docs_lint_error` is the canonical choice. It must NOT be `missing_wave_council_signoff` or `another_wave_active`: both are appended after the guard, so a test using either fails against pre-change code for reasons unrelated to this change. Without this, a mis-parenthesized predicate — or one that filters the list before the docs-gate diagnostics are appended — satisfies AC-5 while publishing a receipt on a lint-failed wave. Today that invariant is enforced by the same expression that fails the call; after this change it rests on classification correctness alone.
- [x] AC-5c: The advisory is present in the **same list** each of the three truthiness consumers evaluates, asserted at the moment of evaluation — the consumer saw a non-empty list containing the advisory and still did not fail or suppress. Without this, a two-list implementation passes every other AC while converting no gate. **The fixture is named per consumer, because one advisory cannot reach all three:** `_mutating` is false on `dry_run`, so the publication guard short-circuits and never evaluates the list, which makes the dry-run pending mint unusable there. Use `ac_priority_unpopulated` on a `create` run for the publication guard and the first gate — it is appended before both and survives to both — and the dry-run pending mint for the second gate.
- [~] AC-6: The census is recorded in this document — every gate-crossing diagnostic with its classification, every **consumer** of `diagnostics` truthiness, and the two code-keyed registries with why they are untouched — before any gate changes. **Ordering NOT met:** the census was recorded after the gate conversion, during delivery review. Content is complete and independently verified by three lanes; the ordering failure is disclosed in `## Diagnostic Census` and repeated here so the checkbox does not imply a control that was not exercised. It also records that the post-change set of prepare-reachable diagnostic **codes** is identical to the pre-change set, which is Requirement 8's property and was otherwise pinned by nothing. *The census was recorded after the gate conversion, so its required before-conversion ordering cannot be truthfully marked completed; the complete independently verified census remains recorded in this change document.*
- [x] AC-7: `_prepare_stale_advisories` and `_ac_advisories` are gone from `.wavefoundry/framework/scripts/`, verified by a search **scoped to Python sources** returning zero hits. The symbols deliberately survive in prose — this document, this wave's record, and `1usqm`'s record all name them as history — so a repo-wide zero-hit census is unachievable by construction and is not the pin.
- [x] AC-8: Focus and context-efficiency classification is unchanged for a dry-run preflight with a pending mint, asserted against `LIFECYCLE_ENGAGED_STATUSES`.
- [x] AC-9: `docs/specs/mcp-tool-surface.md` states the prepare-local blocking/advisory distinction at the three sites named in Requirement 6, records default omission, explicitly preserves the shape of historical non-blocking conventions, and leaves no unstated consumer impact.
- [x] AC-10: The `review_policy_receipt_stale` emissions from the `policy_state_errors` loop and the publish-failure handler remain **blocking**, asserted directly. Tagging by code rather than by site would make both non-blocking.
- [x] AC-10b: **The other four callers of `_review_policy_receipt_diagnostics` are unaffected.** The diagnostic payloads reaching `wf_review_event`, `wf_review_wave`, `wf_implement_wave` and `_evaluate_shared_delivery_state` are byte-identical to today — no `advisory` key present — asserted per caller. This is the P1 the security seat found: tagging the shared construction rather than prepare's call would stamp `advisory` on diagnostics that block at three other tools and plant a fail-open for the follow-on wave.
- [x] AC-10c: A source-derived pin against future drift, in AC-4's style: parse `server_impl.py`, collect every contribution of an advisory diagnostic into prepare's shared list, and assert the set equals **exactly the sanctioned set** — which is **three** sites, not one: the dry-run `_review_policy_receipt_diagnostics(..., advisory=True)` call, plus the two emits folded in from `_ac_advisories` (`ac_priority_unpopulated` and the dry-run `prepare_council_verdict_missing`). Both of the latter **must** be tagged once Requirement 4 folds that list, or prepare starts returning `error` on conditions that today only decorate a successful envelope. No historical lifecycle-focus or review-evidence convention is tagged. An earlier revision demanded "exactly one sanctioned site", which fails against a correct implementation. The pin is **syntactic** — it catches literal `advisory=True` keywords, not a helper that hardcodes the tag internally — and says so, as AC-4 does. This matters because everything accumulated before the first gate is one mistag away from bypass, including `missing_wave_council_signoff` (the readiness stage gate) and `another_wave_active` (the single-OPEN guard).
- [x] AC-11: The full framework suite and docs-lint pass.

## Tasks

- [x] Run and record the census (AC-6). Recorded AFTER the gate conversion rather than before it; disclosed in `## Diagnostic Census` and in AC-6.
- [x] Add `advisory: bool = False` to `_diagnostic`, omitted at default; pin AC-2 first with absent, false, and malformed truthy values blocking.
- [x] Introduce the single prepare envelope helper and route **all 8** returns through it. The delivered implementation declares `diagnostics` as the function's first statement, so there are no pre-list returns and AC-4's lexical clause now selects all 8 — an earlier version of this bullet described the HEAD layout, where two returns preceded the declaration.
- [x] Fold `_ac_advisories` into it and delete the symbol.
- [x] Convert all three `diagnostics` truthiness consumers, including the publication guard.
- [x] Tag only the three prepare contributors in AC-10c advisory; leave policy errors, publish failure, other helper callers, and historical non-blocking conventions unchanged.
- [x] Delete `_prepare_stale_advisories` and its splat sites. Edit no wave record.
- [x] Update `docs/specs/mcp-tool-surface.md` at the three named sites.
- [x] Run the full suite and docs-lint.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| census | implementer | — | Specified as a gate; in delivery it ran AFTER the gate conversion. Recorded in this doc; covers consumers not just producers |
| advisory-field | implementer | census | Omit-at-default; AC-2 written first |
| envelope-helper | implementer | advisory-field | Single merge point; absorbs `_ac_advisories`; the structural half |
| gate-conversion | implementer | envelope-helper | All three truthiness reads, publication guard included |
| remove-workaround | implementer | gate-conversion | `_prepare_stale_advisories` only; no wave-record edit |
| spec-update | implementer | gate-conversion | Three named sites |


## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/server_impl.py`
- `.wavefoundry/framework/scripts/tests/test_server_tools.py`
- `docs/specs/mcp-tool-surface.md`

`docs/specs/mcp-tool-surface.md` is declared for **editing**, not only reading: Requirement 6 updates it at three named sites.

## Affected Architecture Docs

`docs/specs/mcp-tool-surface.md` is updated unconditionally per Requirement 6 — the visibility question is decided at plan time, not deferred. No architecture boundary, data flow, or test topology moves, so no `docs/architecture/` doc needs a change.

## AC Priority


| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The capability that does not exist today. |
| AC-2 | required | Pins the predicate direction. An allow-list predicate fails open on every unclassified diagnostic in the tree, turning gates into no-ops. |
| AC-3 | required | The measured `1usqm` regression. The lint-clean fixture clause exists because the first version of this test was vacuous for exactly that reason. |
| AC-3b | required | The roster-drift reclassification is argued in Requirement 2 and reachable without a pending mint; without this it ships unpinned. |
| AC-4 | required | The structural property. Without it the fix is "everyone remembers", which is the defect. |
| AC-5 | required | The publication guard is a WRITE. Getting this wrong activates a wave with an unpublished receipt — worse than the defect being fixed. |
| AC-5b | required | AC-5 alone is half-pinned. Without the negative twin, a predicate that filters before the docs-gate diagnostics are appended publishes a receipt on a lint-failed wave and still passes. |
| AC-5c | required | Without it a two-list implementation passes every other AC while converting no gate — a green wave that delivered nothing. |
| AC-6 | required | The gate change alters failure semantics for every prepare diagnostic. |
| AC-7 | required | Leaving a workaround beside the fix is how two conventions coexist. |
| AC-8 | important | The telemetry reclassification was the non-obvious half of the original defect. |
| AC-9 | required | Requirement 6 is the public-contract requirement and would otherwise be pinned by nothing. |
| AC-10 | required | Site-scoped versus code-scoped is the difference between a correct fix and silently unblocking two real failure paths. |
| AC-10b | required | The shared helper has five callers. Tagging its construction rather than prepare's call stamps `advisory` on diagnostics that block at three other tools and plants a fail-open for the follow-on wave. |
| AC-10c | required | Site-scoping is not otherwise enforceable. Everything accumulated before the first gate — including the readiness stage gate and the single-OPEN guard — is one mistag away from bypass. |
| AC-11 | required | Standard gate. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-08-10 | THREE-LANE REVERIFICATION after the coordinator became a co-author. Splice damage independently cleared: an AST diff of all 34,431 lines against HEAD found ZERO methods removed anywhere, and each of the four restored tests is mutation-killed rather than merely present. QA ran 23 mutants; the three operator-found defects are all genuinely fixed, and AC-5c's `>= 3` probe bound was judged TIGHT rather than a proxy — `.get("advisory")` is read at exactly one place with exactly three call sites, the fixture holds one dict so `any()` cannot short-circuit, and the measured count is exactly 3 | 7053 tests OK; census independently re-derived TRUE by two lanes including code-set equality against HEAD |
| 2026-08-10 | TWO LANES CONVERGED on a fix of this wave breaking a fix of `1upba`: the `policy_state is not None` guard added for Requirement 8 made `1upba`'s `_seen_stale` dedupe UNREACHABLE, because entering the block forces `policy_state_errors == ()` and the two producers become mutually exclusive. Deleting the dedupe survived all 55 tests, and the surrounding comments still asserted the old two-producer mechanism. Dedupe and comments removed; the test survives its mechanism, re-founded on the property that still holds | QA mutant M21 survived; code lane probe showed the helper is never invoked on that path |
| 2026-08-10 | AC-10b covered 2 of the 4 callers it names, and its `wf_review_event` arm inspected a diagnostic from a DIFFERENT producer — the `1upba` readiness-refusal path — while the `run` response that does reach the helper was discarded. Probed both modes: `wf_review_event` surfaces no helper diagnostics at all. Rebuilt to assert per caller across the three tools that do surface it, with `wf_close_wave` covering `_evaluate_shared_delivery_state`, and to check `wf_review_event`'s seam directly rather than through a response that never carries it | tagging all three non-prepare call sites now fails 3 subTests |
| 2026-08-10 | AC-4 admitted `_attach_lint_to_response` without inspecting its argument, so a return constructing its own diagnostics list INSIDE the wrapper survived. Now traces the wrapped value — an inline call must be `_prepare_envelope`, and a name must be bound from one — verified against that exact mutant | QA mutant M19 |
| 2026-08-10 | Three record corrections. The retired census-as-gate claim survived at FOUR live surfaces (AC-6 body, a task, the AEG row, a Risks row) while the census itself disclaimed it — the partial-fold pattern this repository keeps paying for, committed here. All four now state the ordering was not met. The census enumeration was off by one, found independently by all three lanes. And AC-11's green suite depends on an edit to wave `1uwpf`'s `1uu0f` change doc, outside this wave's declared surfaces: that edit moved a sentence out of a `## Serialization Points` block where its backtick-quoted paths made the legacy scan over-recruit a lane, reddening the corpus invariant | recorded because the delivery boundary should match what was touched |
| 2026-08-10 | The FIRST splice deletion, previously referenced but never recorded. It happened in wave `1usqm` while folding that wave's delivery findings: a line-index splice removed the AC-6, AC-8 and AC-10 tests from `WaveCouncilPolicyTests`, caught only when the class count fell 34 to 31, and restored by anchored edit. It is recorded there in `1upba`'s Progress Log; noted here because this wave's own row called itself "the second of this session" against an event a reader of this document could not find | docs-contract lane N2 |
| 2026-08-10 | OPERATOR REVIEW: changes requested, four findings, all correct. Three were the same defect class this wave kept catching in others — tests that INFER rather than OBSERVE. AC-5c asserted publication, `ok`, and an exact envelope list, all of which a restored parallel advisory list satisfies; AC-10 claimed both blocking stale-receipt paths were covered while exercising only the `policy_state_errors` loop; AC-10b called the shared helper directly rather than the four production callers it names | operator focused regression run: 54 tests, docs-lint clean |
| 2026-08-10 | AC-5c rebuilt to OBSERVE. The advisory payload is now a dict that records every `get("advisory")` call, so the assertion is that the three truthiness consumers each interrogated THAT object. Verified against the exact mutant the operator described: with a parallel advisory list restored and merged only at the envelope, the recorder is probed 0 times and the test fails. The previous form passed that mutant | probed 0 vs required 3 |
| 2026-08-10 | AC-10 gained the publish-failure path, reachable only when `_publish_prepare_policy_state` raises; if that emit were advisory, prepare would report `ok` after failing to write the roster and receipt. AC-10b rebuilt to drive `wf_review_wave`, `wf_implement_wave` and `wf_review_event` and assert the key is ABSENT in what each actually returns, with a guard asserting the fixture really surfaces a stale receipt so the loop cannot pass vacuously | both mutants killed |
| 2026-08-10 | SELF-INFLICTED REGRESSION, the second of this session and the same cause: rewriting AC-5c by line-range splice silently DELETED four tests that sat between it and the end marker — AC-3b, AC-10, AC-10b and the Requirement 8 guard test. Three of those ACs were marked `[x]` against tests that no longer existed, which is exactly the defect this wave's own review had just criticised. Caught only because the operator's finding sent me back to the anchor. All four restored via anchored edits; class count 50 to 55 | range splicing across a region another edit has shifted is not safe on a 34,000-line file |
| 2026-08-10 | Closure state reconciled: `wave.md` said `planned` while the change doc said `implementing`, and the run-the-suite task was unchecked against a passing run. Both corrected | 7053 tests across 62 files OK; docs-lint ok |
| 2026-08-09 | DELIVERY REVIEW, three lanes. The mechanism was sound: every property the lanes checked by execution or AST was already CORRECT in the code. What was missing was proof — six ACs sat unmet, and they were the security-critical pins. Every survivor at QA's first snapshot (the shared-helper mistag, the unconverted publication guard, the two in-prepare blockers) was explained exactly by an unmet AC and by nothing else | QA: no survivor indicated a defect in delivered work |
| 2026-08-09 | AC-6 was marked `[x]` with NO census anywhere in the document — the docs-contract lane found three forward references pointing at a section that was never written, leaving Requirements 5 and 8 delivered by nothing. Census now written from an AST walk rather than from plan prose, and it records that it ran AFTER the gates changed rather than before, which is the ordering Requirement 5 specified and did not get | 21 in-prepare constructions enumerated, 2 advisory; 3 contributing helpers; both code-keyed registries |
| 2026-08-09 | AC-5's `[~]` narrowing WITHDRAWN after the code lane disproved its premise by spy trace. It claimed publication rotates the receipt and stales the approval in the same call, making activation unreachable; that holds only when `receipt_append_required` is True. On the ordinary ready-approve-create flow it is False, publication is a re-render, the approval stays current, and the wave activates — reproduced independently. The requirement was satisfiable as written. Note the two lanes CONTRADICTED each other here: docs-contract judged the narrowing legitimate after verifying the pending-mint path only, which was correct but not general | spy on `_publish_prepare_policy_state`: 1 call, status ok, transitioned_to_active True, receipt rotated False |
| 2026-08-09 | AC-10c's pin was defeatable in THREE successive forms, each caught by a different check. `inspect.getsource(prepare)` could not see a mistag in a contributing helper — demonstrated by firing the publication WRITE on a wave with an invalid review-evidence ledger while the pin still read 3. Adding enclosing-function and cardinality checks still passed when the tag was MOVED onto `another_wave_active` (the single-OPEN guard) or `missing_wave_council_signoff` (the readiness stage gate), holding the count at 3. It now asserts the sanctioned SET of tagged diagnostic codes, which is what AC-10c always specified | three mutants, each verified to pass the prior form and fail the current one |
| 2026-08-09 | AC-4's test asserted hardcoded counts rather than enumerating returns, so both halves of its stated claim were false — it never checked that EACH return routes through the helper, and a correctly-added return would break the count instead of being covered. Rewritten to walk `Return` nodes and assert each one's call target | `_prepare_envelope` or `_attach_lint_to_response`, derived from source |
| 2026-08-09 | Two behavioral repairs beyond the pins. The dry-run advisory call was guarded one conjunct weaker than prepare's own policy block, so a declared wave with an ABSENT `wave_review` section got a blocking config error on a preview where prepare itself stayed silent — a detection change, which Requirement 8 forbids. Guard aligned and pinned. And a stale docstring claiming to kill a mutant that Requirement 4 had already eliminated was corrected rather than left | `wave_review` absent: no stale diagnostic; invalid: still blocks |
| 2026-08-09 | Split out of `1usqm` at operator direction after the dry-run advisory needed three placements to land, none of them structurally sound | `1usqm` architecture lane executed the three-way status comparison |
| 2026-08-09 | READINESS COUNCIL, both seats WITHHELD, and red-team FALSIFIED this plan's central premise. An earlier revision claimed the shared `diagnostics` list "reaches every return automatically"; an AST walk found 8 returns of which only 3 forward it, and two that drop it construct fresh lists AFTER both gates. Moving advisories onto the shared list would have reproduced the defect at two new sites. The fix was re-founded as structural — a single envelope helper so no return constructs a diagnostics list at all | red-team AST walk, re-derived on two independent byte snapshots |
| 2026-08-09 | RED-TEAM P1: `if diagnostics:` is three reads, not one, and one of them is a WRITE guard. `if _mutating and policy_state is not None and not diagnostics:` gates publication of the roster and receipt. Today non-empty diagnostics there guarantees `error`, so skipped-publication and failed-call are the same event; a blocking-only filter decouples them and would let a `create` run activate a wave with an unpublished receipt while returning `ok`. Folded as Requirement 3 and AC-5 | red-team read of all three truthiness sites |
| 2026-08-09 | RED-TEAM P1: the plan was ambiguous between code-scoped and site-scoped tagging, and the code-scoped reading is dangerous. `review_policy_receipt_stale` has 10 emit sites; within prepare alone it is emitted both as the advisory pending-mint and as genuine blockers from the `policy_state_errors` loop and the publish-failure handler. Two existing registries also classify by code. Requirement 2 now states site-scoped explicitly and AC-10 pins the two blocking emissions | red-team emit-site census |
| 2026-08-09 | BOTH SEATS P1, convergent: AC-6's "repo-wide zero hits" was unachievable — 5 of 9 hits for `_prepare_stale_advisories` are prose that must survive, including this plan's own Rationale, Requirement and AC text. A doc describing a symbol keeps the symbol alive in its own census. Rescoped to Python sources | executed grep, aggregated by file |
| 2026-08-09 | BOTH SEATS P1, convergent: the old AC-6 also directed deletion of `1usqm`'s wave watchpoint, which `AGENTS.md` *Cleanup and Destructive Operations* prohibits for wave records and closed-wave archives, restated in four seeds. The sequencing made it worse — waiting for `1usqm` to close guaranteed the edit would land on an archive. Requirement 7 now forbids editing any wave record; the watchpoint's own instruction is satisfied by this wave landing, so leaving it makes it accurate history | docs-contract seat quoted the rule and the watchpoint verbatim |
| 2026-08-09 | DOCS-CONTRACT P2: `severity` collides with an entrenched five-level scale (`SEVERITY_ORDER`, `max_severity()`, `high_severity_finding`) that appears in the SAME response envelope as `data.max_severity`. Renamed to `advisory: bool = False`, omitted at default — which also means no existing diagnostic payload changes shape, keeps `_bounded_upgrade_response_envelope`'s `omitted_field_count` unchanged, and reuses the noun this repository already has for the concept | docs-contract seat's seven-site vocabulary census |
| 2026-08-09 | DOCS-CONTRACT P2: `_ac_advisories` is a THIRD list the plan never mentioned, and it is the only one the success return emits — so an advisory on the shared list would still not reach a successful response. Requirement 5's own coexisting-conventions argument applied to it verbatim. Folded into Requirement 4 and In scope | docs-contract read of the success return |
| 2026-08-09 | DOCS-CONTRACT P2: Requirement 4 was a gesture — it named a file, no heading, and deferred a decision it could make now. `_diagnostic` returns a dict placed directly into the envelope, so any key it stores is public by construction and the census cannot answer whether the key ships. Three spec sites now named, and two existing spec sentences under `### Lifecycle Mutations` were identified as actively falsified by a blocking-by-default key | docs-contract read of all three spec sites |
| 2026-08-09 | DOCS-CONTRACT: coverage trace found two orphan Requirements (the public-contract one had NO AC) and one orphan AC. Added AC-9 and AC-10, folded AC-8's property into Requirement 3, and folded the no-new-diagnostics check into the census requirement | full 6-Requirement by 8-AC trace |
| 2026-08-09 | FOURTH-ROUND REVERIFICATION, two more P1s and the fourth unreproducible claim. P1: Requirement 2 said the helper's policy-error and roster-drift emits "stay blocking" — false about the tree. TODAY all three of its emits land in `_prepare_stale_advisories` on the dry-run path and merge non-blockingly; under this plan the two untagged ones would land on the shared blocking list and flip `dry_run` to `error`, dropping the envelope from 15 keys to 10 and leaving `LIFECYCLE_ENGAGED_STATUSES` — the exact failure the change exists to remove. Each emit is now decided explicitly, and the roster-drift reclassification is argued rather than assumed because it is checked nowhere else in prepare and is reachable WITHOUT a pending mint | reviewer AST pass over the helper and both gates |
| 2026-08-10 | Fresh independent readiness review narrowed the public contract to prepare-local advisory classification and rejected the claim that all existing non-blocking diagnostics share a new payload field. The gate predicate is now explicitly literal `advisory is True`; absent, false, and malformed truthy values remain blocking. | independent docs/security review; AC-2 and AC-9/10c repair |
| 2026-08-10 | Implementation opened after current council and required-lane readiness approval. Added default-omitted `advisory`, a prepare-local shared envelope/list, literal-boolean blocking predicate at both gates and publication, site-scoped receipt-helper tagging, and the public contract wording. Focused regression tests passed; full server-tools regression was run. | `test_prepare_advisory_requires_literal_true`; preview/council focused baselines; `python3 -B -m unittest test_server_tools` |
| 2026-08-09 | P1: AC-10c demanded the advisory set equal "exactly the one sanctioned site", which fails against a correct implementation. Folding `_ac_advisories` per Requirement 4 means `ac_priority_unpopulated` and the dry-run `prepare_council_verdict_missing` must BOTH be tagged, or prepare begins returning `error` on conditions that today only decorate a successful envelope. The sanctioned set is three sites, and the pin is now stated as syntactic | reviewer traced the fold's consequences |
| 2026-08-09 | Three further corrections. Requirement 3 asserted skipped-publication and failed-call are "the same event"; it is a one-way implication only, because the publication guard runs BEFORE `missing_wave_council_signoff` and `another_wave_active` are appended, so a run carrying either already publishes and then fails — AC-5b now names a pre-guard `docs_lint_error` as its blocker so the test does not fail against pre-change code. AC-5c was unsatisfiable with the dry-run advisory at the publication guard, since `_mutating` is false on dry_run and the guard short-circuits; the fixture is now named per consumer. And Requirement 8 was an orphan, folded into AC-6 | reviewer, each verified against the tree |
| 2026-08-09 | The fourth unreproducible measured claim, found because the round was briefed to assume one existed: the Decision Log said `review_policy_receipt_stale` is emitted at 10 sites while Requirement 2 and an earlier Progress Log row both said 9. The tree gives 9 emits plus 2 registry-membership strings. Corrected. Also: Requirement 7's blanket ban on editing any wave record was self-locking — it forbade reconciling THIS wave's own `wave.md`, which still described the abolished `severity` design. Narrowed to other waves' records and closed archives, which is what `AGENTS.md` actually protects | reviewer |
| 2026-08-09 | SECURITY SEAT P1, the most consequential finding of this readiness round: Requirement 2 was FACTUALLY WRONG about where the advisory is emitted. It claimed the pending-mint diagnostic is constructed inside `wf_prepare_wave_response`; it is constructed in `_review_policy_receipt_diagnostics`, a shared helper with FIVE callers, four of which treat a pending mint as blocking. An implementer following the plan literally would stamp `advisory: true` on diagnostics that block `wf_implement_wave`, `wf_review_wave` and `wf_review_event`, contradicting the spec this change updates on day one — and would plant a fail-open for the named follow-on: once that gate converts, a genuinely superseded receipt stops blocking implementation. AC-10 pinned the two sites that were not the problem. Requirement 2 re-founded on the CONTRIBUTING CALL SITE with a helper keyword; AC-10b added | security seat, five-caller census re-derived by AST |
| 2026-08-09 | SECURITY SEAT P2: Requirements 3 and 4 described two different designs, and under the two-list reading EVERY AC passed with zero gate conversion — the parallel-list convention surviving under a new name, which is the defect this change exists to remove. It fails closed, so not a hole, but the security-critical half would have been pinned by nothing. Requirement 4 now states advisories ride the SAME list the gates read, and AC-5c asserts the gate saw the advisory in that list at evaluation time | security seat traced all 11 ACs against the two-list reading |
| 2026-08-09 | Three further security findings folded: AC-5 was half-pinned with no negative twin, so a predicate filtering before the docs-gate diagnostics are appended would publish a receipt on a lint-failed wave and still pass (AC-5b); AC-2 stated its predicate in the `"blocking"`/`"advisory"` string tokens belonging to the abolished `severity` design and could not be asserted against a boolean; and nothing enforced site-scoping against future drift, with the readiness stage gate and single-OPEN guard both accumulating before the first gate and one mistag from bypass (AC-10c, source-derived) | security seat |
| 2026-08-09 | Security seat recorded explicit NO-ISSUE findings worth keeping: the two code-keyed registries are correctly left alone and fail closed, and the prepare-advisory / close-blocking asymmetry is right semantics rather than drift; no diagnostic dict on prepare's path originates outside the process, so `advisory` cannot be attacker-influenced (config, ledger and change-doc content reach message strings only, never keys); AC-5's publish-and-activate outcome is the safe one, since the alternative leaves an OPEN wave whose readiness approvals are rejected as stale only after it is open; and nothing in code, lint or the close gate reads the `1usqm` watchpoint, so leaving it costs no integrity | security seat, stated explicitly rather than padded |
| 2026-08-09 | Two factual corrections from the same seat: `review_policy_receipt_stale` has 9 emit sites, not 10 — the earlier count included two registry membership strings — and the `prepare_council_verdict_missing` return sits BETWEEN the two gates, not after both. Neither changes a conclusion, both recorded because the plan asserts them as measurements | security seat re-derived by AST |
| 2026-08-09 | A finding that STRENGTHENS the plan and was added to the Rationale: the spec already defines `diagnostics` as carrying "Named warnings" and states they "can never overturn a successful lifecycle mutation". Today's gate is therefore already out of contract, so this change restores the documented behavior rather than widening the contract | docs-contract seat |
| 2026-08-09 | Pre-implementation review corrected the stale Scope instruction that said this wave's own current Objective, Summary and Watchpoints still used the rejected `severity` design. They already describe `advisory: bool`; historical references remain review history, not an implementation task | current `wave.md` Objective, Wave Summary, and Watchpoints inspection |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-08-09 | Name the field `advisory: bool`, not `severity` | `severity` is an entrenched five-level review-finding scale that ships in the same envelope as `data.max_severity`; two incompatible scales one nesting level apart is a worse contract than the one being fixed. "Advisory" is already this repository's noun for a non-blocking diagnostic | `severity: "blocking" \| "advisory"` (rejected: collides); `diagnostic_class` (held as second choice if a tri-state is ever needed) |
| 2026-08-09 | Omit the key at default rather than always emitting it | No existing diagnostic payload changes shape, `_bounded_upgrade_response_envelope`'s whitelist keeps `omitted_field_count` unchanged, and it matches the existing `recovery_tools` / `recovery_usage` convention | Always emit `advisory: false` (rejected: changes every payload and every whitelist count for no benefit) |
| 2026-08-09 | Route every return through one envelope helper rather than moving advisories to the shared list | The shared list reaches only 3 of 8 returns, and two of the five that drop it build their own lists after the gates. Moving lists is "everyone remembers"; a single merge point makes it structural | Splat at every site (rejected: the shipped `1usqm` workaround, and the reason this change exists); amend the claim and require the two post-gate returns to forward the list (rejected: fixes the instance, not the class) |
| 2026-08-09 | Classify by emit site, never by diagnostic code | `review_policy_receipt_stale` is emitted at 9 sites (11 string occurrences less two registry-membership strings), including two genuine blockers inside prepare itself. Code-scoped tagging would silently unblock a real stale receipt and a real publication failure | Code-scoped tagging (rejected: fails open on live gates); a per-code allow-list registry (rejected: two such registries already exist for other purposes and adding a third compounds the problem) |
| 2026-08-09 | Do not edit any wave record | `AGENTS.md` prohibits deleting mentions of removed artifacts from wave records and closed-wave archives. The `1usqm` watchpoint is satisfied by this wave landing, so it becomes accurate history rather than stale debris | Delete the watchpoint when this lands (rejected: prohibited, and the sequencing guaranteed it would hit an archive); amend it in place (rejected: still an archive edit, and unnecessary) |
| 2026-08-09 | Classify at the CONTRIBUTING CALL SITE, not at the `_diagnostic` construction | `_review_policy_receipt_diagnostics` is shared by five callers with opposite intent. Construction-site tagging is indistinguishable from code-scoped tagging for a shared helper, and carries the same fail-open into the follow-on wave | Tag the construction (rejected: stamps `advisory` on four blocking consumers); re-tag in prepare after the helper returns (viable second choice, but a keyword on the helper keeps the intent at the point of decision) |
| 2026-08-09 | Default `advisory` to False | Many diagnostics in the tree are unclassified. An advisory default would silently convert unreviewed blocking conditions into non-blocking ones — a fail-open change to every gate at once | Advisory default with opt-in blocking (rejected: fails open across the whole surface) |
| 2026-08-10 | Scope `advisory` semantics to prepare and require literal boolean `True` at its gates | Existing lifecycle-focus and review-evidence advisories have their own established behavior and payload shape. A prepare-local contract avoids falsely claiming a global migration; exact boolean recognition keeps malformed internal data fail-closed. | Global payload migration/census (rejected: materially broader); truthiness predicate (rejected: malformed truthy values would bypass a gate) |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| The publication guard is converted without noticing it is a write | Requirement 3 names it explicitly as the dangerous one of the three reads, and AC-5 pins that an advisory-only `create` run still publishes and still activates |
| Tagging by code silently unblocks real failures | Requirement 2 states site-scoped explicitly; AC-10 asserts the two in-prepare blocking emissions of the same code stay blocking |
| The gate change makes a real failure non-blocking | AC-2 pins the blocking default in its mutation-resistant form (a dict not built by `_diagnostic`). AC-6 requires the census, which in delivery was recorded after the gate conversion rather than before it — so it confirmed rather than gated, and three lanes verified its content independently |
| AC-3 repeats `1usqm`'s vacuity | AC-3 requires BOTH fixtures to be docs-lint clean; the earlier version compared `error` to `error` because the fixture failed lint and prepare never reached the code under test |
| A future return site drops advisories again | AC-4 derives its enumeration from the source with `ast`, so a return added later is covered without editing the test |
| Two advisory conventions survive | AC-7 removes `_prepare_stale_advisories` and `_ac_advisories` together, scoped to Python sources |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
