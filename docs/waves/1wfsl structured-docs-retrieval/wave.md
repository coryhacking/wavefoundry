# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-08-27
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1wfsl structured-docs-retrieval`
Title: Structured Docs Retrieval

## Objective

Make the retrieval corpus match what target repositories actually contain: teach the
existing include-prefixes lever through shipped guidance with an accurate docs-layer
contract, give OpenAPI and JSON Schema measurement-gated structure-aware chunking with
a committed golden-set harness, extend the docs layer to reStructuredText and AsciiDoc
so Sphinx- and AsciiDoc-documented targets get docs retrieval at all, and consolidate
the fragmented corpus-exclusion mechanisms while closing the genuinely indexed
machine-generated stragglers. The spec-format family extension (AsyncAPI, GraphQL SDL,
Protobuf) is deliberately parked, admission-gated on this wave's measured outcome.

## Changes

Change ID: `1wdvr-doc index-include-prefixes-operator-guidance`
Change Status: `implemented`

Change ID: `1wfr8-enh spec-aware-structured-chunking`
Change Status: `implemented`

Change ID: `1wfsm-enh docs-layer-rst-adoc-prose-formats`
Change Status: `implemented`

Change ID: `1wfsn-enh corpus-hygiene-lockfile-generated-exclusions`
Change Status: `implemented`


## Participants

- Coordinator: primary Claude Code coordinator / wave-council
- Write-owning roles: implementer (chunker/indexer lane, serialized),
  docs-contract-reviewer (seed and guidance surfaces), performance-reviewer
  (measurements), qa-reviewer (regression proofs)
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer

Completed At: 2026-08-27

## Wave Summary

Wave `1wfsl` (Structured Docs Retrieval) delivered 4 changes: Operator Guidance: Making Structured-Format Directories Searchable, Spec-Aware Chunking for OpenAPI and JSON Schema, Docs-Layer Support for reStructuredText and AsciiDoc, and Corpus Hygiene: Consolidate Exclusion Mechanisms and Close the Stragglers. Notable adjustments during implementation: Operator Guidance: Making Structured-Format Directories Searchable: CENSUS-CONSTRUCTED surface list (recorded before editing, per Task 1): SHIPPED seed layer — `seeds/211-guru.prompt.md` Index Scope corpus-boundary section (the canonical carrier to extend), `seeds/160-upgrade-wavefoundry.prompt.md` line ~225 (upgrade preservation mention of `indexing.project_include_prefixes`; verified compatible, no edit), `seeds/150-refresh-wavefoundry.prompt.md` indexing-contract reconciliation clause (the propagation mechanism, not a content carrier). SELF-HOSTED twins — `docs/agents/guru.md` Index Scope (byte-parity carrier of seed 211; no renderer fences in that region), `docs/specs/mcp-tool-surface.md` (semantic-index rebuild note ~line 1167 and the docs-search description line ~1418), `docs/contributing/build-and-verification.md` (extra project index roots, ~line 129), `docs/architecture/chunking-and-indexing-pipeline.md` (include-prefix architecture prose at lines ~67 and ~197-198 plus the config example ~789-797; this row ORIGINALLY recorded the config example as already updated by siblings 1wfsn/1wfsm, which the delivery lane DISPROVED by byte-identity diff against HEAD — a false census disposition, finding DOCS-DEL-1; the Configuration Reference section was rewritten to opt-back-in semantics under that finding's repair), `docs/architecture/data-and-control-flow.md` line ~90 (one-sentence exclusion mention; verified compatible), `docs/architecture/decisions/1p4xx-adr` (historical ADR, not edited), `AGENTS.md` (MCP/indexing notes; originally dispositioned as carrying no include-prefix recipe — a second census miss: its graph-index parenthetical DID misdescribe include-prefixes as a scope restriction and was corrected under DOCS-DEL-1). Census method: repo-wide token sweep for `project_include_prefixes` plus the readiness-lane docs-layer-contract pins, excluding wave records and plans.; Operator Guidance: Making Structured-Format Directories Searchable: IMPLEMENTATION FALSIFICATION (the wave's third, caught by the executable walkthrough): the plan's recipe premise — that `indexing.project_include_prefixes.code` selects the code roots and a directory outside them needs adding — was DISPROVEN by executing the real filters (`_filter_project_index_excludes` excludes only `.wavefoundry/`-prefixed paths, with the prefixes list as the opt-back-in; `_effective_project_include_prefixes` confirms). An ordinary `api-contracts/` spec directory is in the code corpus with NO configuration. The Rationale and Requirement 1 were corrected in place (marked), and the shipped guidance was rewritten to the accurate contract: default whole-repo coverage, a missing-spec checklist (ignore files first), and the prefix opt-in scoped to `.wavefoundry/`-nested (self-hosting) content.; Operator Guidance: Making Structured-Format Directories Searchable: IMPLEMENTED (landing last per the wave watchpoint, after all sibling outcomes settled): seed 211 Index Scope extended under `seed_edit_allowed` (opened and closed around each edit) with the corrected framework-generic guidance — default coverage, missing-spec checklist, `.wavefoundry/`-nested opt-in recipe, spec-aware chunking note reflecting 1wfr8's measured DEFAULT-ON, the accurate non-exhaustive docs-layer prose contract reflecting 1wfsm's landed rst/adoc set, machine-authority exclusions reflecting 1wfsn's landed scan-findings predicate, CSV/markdown-carrier position, and the `walk_reinclude_filenames` name-layer-only boundary. Byte-parity mirror applied to `docs/agents/guru.md`; twins reconciled (`docs/contributing/build-and-verification.md` extra-roots section; `docs/specs/mcp-tool-surface.md` docs-search description line + index_build include-prefixes note). AC-1 walkthrough EXECUTED with the real build + embedder + Lance vector search: Part A default-coverage hit (ordinary directory, no config), Part B blanket-excluded spec opted in via the prefix, rebuilt, top hit rank 1 on the 1wfr8-breadcrumbed operation chunk.

**Changes delivered:**

- **Operator Guidance: Making Structured-Format Directories Searchable** (`1wdvr-doc index-include-prefixes-operator-guidance`) — 3 ACs completed. Key decisions: Documentation-only: teach the existing include-prefixes lever through the seed layer and self-hosted twins.
- **Spec-Aware Chunking for OpenAPI and JSON Schema** (`1wfr8-enh spec-aware-structured-chunking`) — 5 ACs completed. Key decisions: Curated domain chunkers for exactly OpenAPI and JSON Schema, content-detected, measurement-gated.; CSV stays excluded everywhere.
- **Docs-Layer Support for reStructuredText and AsciiDoc** (`1wfsm-enh docs-layer-rst-adoc-prose-formats`) — 5 ACs completed. Key decisions: Framework-internal section parsers for rst and adoc with breadcrumbed chunks; coverage ships, quality is measurement-checked.; `.txt` and extensionless documentation files keep their EXISTING plain-text doc-chunk path unchanged (readiness council correction: the original row wrongly described the status quo as excluding them).
- **Corpus Hygiene: Consolidate Exclusion Mechanisms and Close the Stragglers** (`1wfsn-enh corpus-hygiene-lockfile-generated-exclusions`) — 5 ACs completed. Key decisions: Re-plan as consolidation-plus-stragglers on the corrected baseline; keep every existing exclusion's behavior.; Scope the re-include escape hatch to the name-based layer only.
## Watchpoints

- Blocking: `1wfr8-enh` records its pre-change baseline measurement over the frozen
  golden set BEFORE any chunker edit, and the shipped default follows the measured
  outcome; either outcome (default-on or config-gated off) closes the change, matching
  the project's evaluated-and-recorded retrieval history.
- Watchpoint: seed 211 edits in `1wdvr-doc` propagate to every target through refresh
  parity; run behind the seed gate, keep wording framework-generic, and verify the
  shipped-reference parity tests.
- Watchpoint: detection false positives are the leak path for `1wfr8-enh`; the non-spec
  negative corpus and the byte-identical differential proof (AC-1/AC-3) are the guards.
- Follow-up boundary: CSV indexing, generic YAML/JSON prose extraction, docs-layer format
  changes, additional spec formats (AsyncAPI etc.), and setup-time spec-directory
  detection are all explicitly outside this wave; the last is a recorded alternative in
  `1wdvr-doc`'s Decision Log.
- Blocking: `1wfso-enh` is PARKED (not admitted); its enforcement is the admission gate
  itself, after `1wfr8-enh` records its measured default decision, with an explicit
  operator go/no-go if that decision is config-gated off.
- Watchpoint: three changes (`1wfr8`, `1wfsm`, `1wfsn`) edit `chunker.py` and/or
  `indexer.py`; serialize all edits to those files through one implementation lane, and
  compose the `CHUNKER_VERSION` and `WALKER_VERSION` bumps per landing with their
  documented rationale lines rather than batching silent bumps.
- Watchpoint: the false planning census that originally underpinned `1wfsn` (and the
  coordinator's session claim that "no name-based lockfile exclusion exists") is
  CORRECTED in that change's re-planned document; implementation censuses in this wave
  run through the real walk and filters, never through grep pipelines with exclusion
  chains.
- Watchpoint (implementation addition): a THIRD planning claim fell during
  implementation — `1wdvr`'s include-prefixes-as-root-selector premise, falsified by the
  executable walkthrough (the code corpus spans the whole repository by default; the
  prefixes list is the `.wavefoundry/` opt-back-in). Corrected in the change doc and in
  every shipped guidance carrier before landing; the walkthrough evidence records the
  failing pre-correction assertion.
- Watchpoint: the measurement harness is OWNED by `1wfr8-enh` (committed golden set,
  fixed metrics, numeric bar, in-repo fixtures); the parked `1sear-enh` suite in wave
  `1seaw` is the broader follow-up and no AC in this wave depends on it. Operator-side
  validation on the operator's local Java/Swift/JS-TS consumer projects after a pack
  build is a disclosed, non-gating evidence tier across the wave.
- Watchpoint: `1wfsn-enh` must not narrow secret scanning in any form; its AC-3
  regression is the guard.
- Watchpoint (lane convention): every before/after measurement pair brackets ONLY its
  own change's landing; no sibling change lands between a change's baseline and its
  post-change measurement, so each recorded delta is attributable.
- Sequencing: `1wdvr-doc` guidance wording lands last or is amended in-cycle so it
  reflects the final docs-layer extension set (`1wfsm`) and the exclusion story
  (`1wfsn`), and never promises chunking behavior (`1wfr8`, `1wfso`) ahead of its
  measured default decision.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| ARCH-DEL-1 | do_now | no | completed | — |
| DOCS-DEL-1 | do_now | no | completed | — |
| QA-DEL-1 | do_now | no | completed | — |

*Machine review state — 3 findings; current: do_now 3, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-08-27: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: the wave's evidentiary foundation was falsified by the tree in two of five changes, the `1wfsn` lockfile census most severely (`HARDCODED_EXCLUDE_FILENAMES`, the `.lock` binary-extension entry, and the code-corpus filter already exclude most listed names) alongside the shipped-bound "markdown-only docs layer" claim, while the measurement spine rested on an uncommitted harness with no metrics or bars; resolved before readiness by restructuring in place: `1wfsn` re-planned as consolidation-plus-stragglers with an executed-census requirement, the docs-layer contract corrected across every carrier, `1wfr8` made the committed harness owner with fixed metrics and a numeric default-on bar, and `1wfso` PARKED behind the enforceable admission gate; strongest-alternative: extracting the harness as its own admitted change by reviving `1sear-enh` was adopted in spirit but scoped down, with `1wfr8` owning a bounded in-repo harness and `1sear-enh` remaining the cross-referenced broader follow-up. Docs-contract seat verdict PASS-WITH-REPAIRS; all five required wording repairs (N1-N4, N6) plus advisory N5 and a final falsified-phrase sweep were applied before this recording. The coordinator's own false session census is corrected in the `1wfsn` Progress Log and the wave watchpoints.)

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval follows every affected repair | none |
| code-reviewer | approved | current executed approval follows every affected repair | none |
| qa-reviewer | approved | current executed approval follows every affected repair | none |
| architecture-reviewer | approved | current executed approval follows every affected repair | none |
| docs-contract-reviewer | approved | current executed approval follows every affected repair | none |
| operator-signoff | approved | current executed approval follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies.

<!-- wave:context-efficiency begin -->
## Context Efficiency

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| plan | 121 | 2,396,492 |
| implement | 128 | 996,167 |
| review | 46 | 1,725,267 |
| **Total** | **295** | **5,117,926** |

<!-- wave:context-efficiency-state {"generation":296,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":128,"content_source_credit":1070865,"derived_artifact_credit":282,"direct_net":996167,"estimated_tokens_saved":996167,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":6610,"response_debit":73786,"source_credit_count":25,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":5416},"plan":{"calls":121,"content_source_credit":2586865,"derived_artifact_credit":7230,"direct_net":2396492,"estimated_tokens_saved":2396492,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":12708,"response_debit":192781,"source_credit_count":100,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":7886},"review":{"calls":46,"content_source_credit":1838662,"derived_artifact_credit":1285,"direct_net":1725267,"estimated_tokens_saved":1725267,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":11934,"response_debit":104092,"source_credit_count":53,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1346}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":295,"content_source_credit":5496392,"derived_artifact_credit":8797,"direct_net":5117926,"estimated_tokens_saved":5117926,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":31252,"response_debit":370659,"source_credit_count":178,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":14648},"wave_id":"1wfsl structured-docs-retrieval"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 3 | 0 | 2 | 562,320 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":2,"estimated_exploration_avoided":562320,"surfaced_events":3} -->
<!-- wave:exploration-avoided end -->
