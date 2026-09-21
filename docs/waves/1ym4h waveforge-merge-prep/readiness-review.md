# Waveforge Merge Prep Readiness Review

Owner: Engineering
Status: active
Last verified: 2026-09-21

Revision note (2026-09-21): the operator subsequently approved plan changes for runtime source coverage, call-time stripper binding, namespace census wording, and rendered advisory verification. The version bump remains assigned to the downstream merge by explicit operator direction. The sections through Focused verification record the earlier plan; the Delta round section below reviews those revisions and is the basis for the re-recorded approvals.

Phase: readiness. Verdict: approved after one bounded repair and one focused verification; no readiness blockers remain. Context: `waveforge-merge-prep-readiness-20260921`. This reviews the two plans, not delivered behavior; nothing is implemented.

## Council

Seats ran in separate fresh contexts against the admitted change docs and wave record: `red-team` (fixed) and `docs-contract-reviewer` (rotating, bound to the receipt). The code-reviewer and qa-reviewer readiness lanes ran in the same round, also fresh and independent. All four verified plan claims against the tree with live reads and probes rather than the plans' own prose.

Strongest challenge (red-team): both plans were written against claims the tree refutes. The terminology plan named a normalization target that does not exist and set a census requirement over a literal population it had not counted. The marker plan said behavior on existing input was unchanged, but the chunker's end regex is bare-only today, so routing it through a shared named-or-bare end pattern changes chunk output for marker-first documents, and its self-mutant could not work against patterns compiled at import.

Strongest alternative: for the chunker, keep the bare-only end and derive only the begin alternation. Rejected because the bare-only end is a latent defect (every renderer writes named ends, so marker-first files with prose emit zero chunks today) and keeping it would preserve a known bug for no benefit. The plan adopts the shared end and pins the change.

## Findings and repair

Blocking, all repaired in the change docs in one pass:

- Terminology: the reader is `dashboard_lib.read_dashboard_config` and the payload builder is `dashboard_lib.collect_dashboard_snapshot`, which copies named keys, so the new field is added explicitly. The census predicate is now stated (capitalized tier noun in a string literal, `p()` calls with tier-noun arguments, spaced literals with a lowercase tier noun; identifiers excluded by construction) and the label surfaces are enumerated by symbol; `FRAMEWORK_FLOW` is evaluated at load before any fetch, so the helper reads a register `App` updates per snapshot.
- Terminology: AC-1 no longer claims a byte-identical rendered page. The suite has no default-on JavaScript renderer; the only browser test is opt-in and renders the design-system script. AC-1 now rests on node-gated slice tests with a pinned default literal list, with the Python census as the non-skipping gate.
- Marker: the chunker adopts the shared named-or-bare end and the server's `begin\b` form; the resulting changes on existing input (named ends close chunker regions, annotated begins are recognized, all-`waveforge` documents zero-chunk) are stated and pinned. Working-tree census: 161 marker-bearing markdown files, 29 with annotated-only begins, zero chunk-count or zero-content flips.
- Marker: the module exposes a builder and an alternation source fragment, sites look patterns up at call time, the stripper's pattern is hoisted with its anchoring preserved, and `codenav_handlers` reads the module directly, so the self-mutant is implementable.

Nonblocking, also folded: no test calls the stripper today (baseline pinned first); the literal census needs no allowlist; the framework-owned module list was corrected (`exploration_avoided` is canonical-only; `review_policy_reconcile`, `memory_supply` and `_LEGACY_OWNED_MARKERS` added); plain `import` form for the purge census; explicit `_SOURCE_NAMES` decision; pack inclusion; four existing tests named; the `hero-meta` pill as the advisory target; helper-side casing so a fork's capitalized values work; four seed-attribution sentences in the install-upgrade doc; the review-policy carrier region in the adapter-model doc as a risk; CHANGELOG bullets and test paths in both docs; AC-4 made local.

## Focused verification

Two fresh verifiers, one per plan, checked every finding against the repaired text and the tree. Both approved; every item resolved. Each raised precision notes (the begin-form choice, the census predicate wording, a task count, two surface names), folded in before this record was written. Known-bad detection in this round: the invented symbol, the false "unchanged on existing input" claim, and the unverifiable AC-1 were all detected by the lanes and corrected; the 2026-09-17 readiness rule of one full review, one bounded repair and one focused verification was followed.

Requested lane settings: host default model and effort for all seats and lanes, chosen because plan review against code needs judgment and each lane is bounded. Observed runtime identity: unknown.

Limits: no implementation, no test executed beyond five existing tests run by the QA lane and regex probes in scratch; consumer repositories not censused; Waveforge's own reader of the terminology key not inspected (recorded as a merge-time check).

## Delta round

Context: `waveforge-merge-prep-readiness-delta-20260921`. One fresh, independent reviewer checked the operator's revisions against the tree; both plans approved with six nonblocking wording findings, all folded in before the approvals below were re-recorded.

Verified against the tree: `index_compatibility.ensure_runtime_current` raises `IndexCompatibilityError("index_runtime_stale", name, ...)` with the module in `component`, so a per-module assertion needs no contract change; the copyable test shape is `test_loaded_model_and_lazy_producer_refuse_same_stat_source_replacement`, whose copy list derives from `_SOURCE_NAMES` and therefore auto-includes the new module; guard-owned means only that the upgrade parses `INDEX_GUARD_CAPABILITY` from the file and refuses symlink components, so editing `_SOURCE_NAMES` carries no pack or manifest obligation. The stripper already compiles inside its function body today, so per-call construction is the status quo and lets a module-attribute patch reach it. The changelog claims regex matches only a backticked constant followed within eighty characters by `to N` or `at N`. `Dashboard` uses nine state hooks, routing and storage, so it cannot be rendered honestly as a slice; the advisory becomes a hook-free `TerminologyAdvisoryPill` beside `GitPills`, rendered by the slice, with one structural check for the wiring.

Folded: the census excludes `tests/` and requires two or more distinct `MARKER_NAMESPACES` names (a single-namespace quoted alternation exists in the renderer and must not trip it); `test_index_compatibility.py` added to serialization points; the absent `register_loaded_source()` call is explained; the changelog numeral caveat; the unremapped-map outcome stated; the pill component named in Requirements 4 and 5, AC-2 and Task 3.

Requested settings: host default model and effort; observed runtime identity unknown.


## Currency reconciliation

Independent docs-contract reviewer, context `1ym4h-docs-currency-20260921`, checked the current admitted plans, the Delta round above, the typed ledger history through `wf_review_event(event="list", verbose=true)`, and a fresh `wf_prepare_wave(mode="dry_run")`. This is a bounded currency reconciliation, not another full readiness critique.

The dry-run recomputed policy-input digest `ead1a24c76992e82e5ec8946cec80a1f01f7dc565de6edf0b207950729a282e0`, exactly matching the previously approved receipt `review-policy-528f006f79719ae55d12` and current receipt `review-policy-39dbc73503b7cef18841`. Their evaluator version, council seats, requested/required lanes, delivery mode and delivery-Council requirement also match. The intervening receipt `review-policy-9aee54e687bf452014f7` has a different digest, demonstrating that the binding check distinguished the temporary input change; current approvals remain stale solely because the receipt identity rotated. The fresh dry-run reports lint/garden passed, zero repairs needed and no receipt append required, while refusing readiness for missing current approval bindings.

The baseline-test evidence paragraph was moved from the marker plan's trailing Session Handoff section into Progress Log. The current requirements still include module-source coverage, call-time shared patterns, named ends, annotated begins, exact census bounds, rendered advisory verification, the overlapping-key limitation and downstream version/invalidation responsibility reviewed in the Delta round. No substantive readiness-policy input change remains. On this evidence, rebind the original delta code, QA, docs-contract and Council readiness conclusions to the current identical-input receipt by synthesis. This statement does not claim a new four-seat review or delivery approval.

Integrity: selected checks executed without skip; canonical prepare and typed history boundaries reached; real current/prior receipts compared; exact digest equality and refusal assertions are non-vacuous; the intervening unequal digest and stale-binding refusal provide the negative control. No ledger mutation was performed by this reviewer. Limitation: the canonical digest establishes identity of policy inputs, not byte identity of operational progress logs or an independent rerun of the earlier specialists' review.
