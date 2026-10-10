# Waveforge follow-up readiness briefing

Owner: Engineering
Status: draft
Last verified: 2026-10-08


Current review scope: C1–C5 only. Change204mo (C6) moved intact to wave206is after the original primer; its pending source-location decision is not a blocker for the remaining independent public fixes. The original briefing below is retained as review history, not current admission authority. Reviewers must use the three currently admitted change docs and current receipt.

Wave: `204mp waveforge-follow-up`

## Review boundary

Phase: readiness. Changes: 204ml (C1–C3 test oracles), 204mm (C4 legacy actors), 204mn (C5 role links), 204mo (C6 journal hook). No implementation is authorized until the entire settled packet is readied. Root coordinator has explicitly requested independent review of settled C1–C5 and non-presence C6 contracts while the operator answers C6's source-location question. Do not record wave-wide approval with that decision unresolved. Findings and evidence can be collected now; final focused verification must cover the completed decision and current receipt.

Trust boundaries: declared actor compatibility affects approval and repair identity; renderer rewrites project-owned Markdown; extracted-pack callback loading and preview execution separation. No network or external changes. Source/test/seed targets are listed in each change document. The source tree is shared with Rust206og implementation; no edits to source or that wave are permitted by this readiness assignment. Targeted scratch-only probes are permitted; full suites are not needed for readiness.

## Settled choices to falsify

- C1: explicit upstream text ownership inventory, including zero-hit production files and owned tests/fixtures; downstream-added files do not become census input. Check maintainability of explicit regeneration and missing-file behavior without Git at downstream runtime.
- C2: shipped seed/controlled contract fixture, never checkout-owned project spec.
- C3: frozen historical tiny-payload encoder, independent of current production normalization/digest functions, with shipped-default and no-phases golden cross-checks. Preserve profile-derived legacy spellings and neutral synthetic slug-chain controls without adding profile skips.
- C4: empty-by-default extra actor tuple, deterministic deduplication, canonical council write identity, byte-preserved ledgers, actual reload. Non-council/operator roles must not become aliases; alias pairs remain the same actor for repair-independence checks; digest identity stays built-in.
- C5: exact local Markdown destination span edits in current project docs, preserving custom content/mode, with explicit history exclusions beyond is_history_path. Inline/reference destinations and code masking are required; unsupported/ambiguous syntax remains unchanged with a report. Confirm retry after old-absent/new-present and collision handling without multi-file atomicity claims. Strict docs gate remains.
- C6 settled part: opt-in EXTENSION_JOURNAL_PRE_MIGRATION_TRIGGER, legacy_cutover default / journals_present; existing pre_docs_gate boundary, at most once per invocation, idempotent retries. Built-in migration remains pre1.15 only; preview executes no callback or declaration module. Existing source discovers only direct *.md under docs/agents/journals. Other source locations are not yet authorized or assumed.

## Requested evidence

Use MCP-first live source retrieval; discover and confirm deferred tools before the first retrieval. Setup reports changed inputs, so do not infer semantic freshness; live reads and executed scratch controls ground claims. Consult relevant role prompts and seeds180/209/215. Choose a bounded readiness-safe control that can falsify a concrete plan premise; record exact observed result and limits. Future product ACs are unimplemented, not skipped readiness tests. No source mutation, full-suite rerun, wave activation, closure or publication.

Red-team runs first in an isolated context. Phase2 reviewers form their independent packet read before engaging the primer; answer its strongest challenge and questions, then contribute lane findings and explicit null finding if appropriate. Council roster is determined by the final receipt; requested specialist lanes are code, QA, architecture, docs-contract and security. A single reviewer covering multiple dimensions must say so and must not claim separate corroboration.

## Pending decision

The operator has been asked where Waveforge journals live immediately before the relocation hook. Only this dependent scope is held; review settled behavior now. Do not add an optional roots declaration or recursive scanner without the answer. Root coordinator owns the question and eventual scope decision.

## Coordinator grounding controls

Executed before independent review in one fresh stdlib Python process with scripts/tests on PYTHONPATH; no source writes and temporary fixtures only. These observations are coordinator evidence, not independent reviewer approval:

- C1: created only scripts/tests/distribution_only.py containing the current derived legacy actor in a temporary framework root. Current actor_token_census returned that downstream-only file with one occurrence. The explicit expected dictionary assertion passed, reproducing ownership leakage.
- C5: created the first COUNCIL_ROLE_RENAMES source and a customized adjacent Markdown doc with an exact old-name fragment link. Current migrate_council_role_renames moved the role, retained the custom bytes including the now-stale link, and reported custom.md:1. Assertions confirmed old absent/new present and unchanged custom bytes. This is a narrow migration reproduction, not a full upgrade-driver fixture.
- C3: independently constructed the historical seven-field payload using explicit schema1/evaluator7, profile-derived legacy signoff keys and built-in actor, the tiny literal fixture body hash, canonical JSON and hashlib. It matched the existing historical golden e9890bb019dede839a4db0108256ffd250220007af7836d1870d3dd5db2a1082 without calling current production digest/normalization functions. Changing evaluator_version to8 changed the digest and was rejected by the golden comparison. This supports feasibility of the independent test-local oracle; no renamed profile implementation is claimed.

MCP now reports index_runtime_stale because another authorized wave is editing producer code. Current live reads and exact inspected mechanisms support these controls; no indexed freshness claim or runtime reload is needed for them.
