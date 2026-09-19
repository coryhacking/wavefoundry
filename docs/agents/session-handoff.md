# Session Handoff

Owner: Engineering
Status: active
Last verified: 2026-09-18

## Current Session

**Active wave:** *(none)*
**Last closed waves:** `1y0h0 typed-phase-gates` and `1yd97 phase-gate-follow-ups`, both closed 2026-09-18 by explicit operator instruction after independent delivery review, and committed 2026-09-19. `1y0h0` extracted the close, review and prepare checks into named gate units (`lifecycle_gates.py`, `lifecycle_gate_support.py`) and added config-declared `phase_gates` sensors run by `sensor_runner.py`. `1yd97` gave close-phase sensor execution a precondition: a close that has already accumulated a blocking diagnostic reports its sensors `would_run` instead of executing them. It also cleared the eleven observations `1y0h0` carried. Full suite green at 9,335 tests, receipt current.

**Next:** Remaining Waveforge order: `1y0h1 tool-registry-dispatch`, then `1y0h2 handler-module-split`. Both are readied, but against a tree that predates the gate extraction, which removed roughly 2,000 lines from `server_impl.py`. Their receipts are current only in the sense that their documents are unchanged, so re-verify each plan's code claims against the tree before opening. `1yd24 fixture-fidelity` is planned only, with no receipt and no readiness approval. `1ycrj task-fit-agent-model-policy` (separate session) remains readied and unimplemented.

The operator asked on 2026-09-19 for a review of how readiness rounds work, targeting at most one round once the code is settled. `1yd97` took ten readiness rounds, and every round after the fourth was spent on the amendment-record criteria rather than code.

## Release

Release target `1.25.0` approved 2026-09-17. Two local projects reported successful upgrades to the test package, clean docs/reconciliation checks and completed prompt editing passes. The follow-up clarifies that Python guidance applies only to Wavefoundry tooling, not the host application language. The official path builds the feature archive and verified model set 3 through `build_pack.py --with-models --release`.

Local test build `1.25.0+pqmt` created 2026-09-17 at `~/.wavefoundry/dist/wavefoundry-1.25.0.pqmt.zip` (7,486,022 bytes). SHA-256: `09defc0419ff5b8c176084161090b1ed27673a6b1aff0ad28c058a2521b70f2a`. Docs gate passed; 9152-test receipt current. Outer archive and inner upgrade payload verified, including exact changelog, version and source bytes. VERSION and prompt manifest match. Feature-only local build; no models bundled, tag, commit or publication. Advisory sensor `ac_asserts_repository_state` (1wur7) remains advisory.

Official 1.24.0+ppq7 published on 2026-09-13; tag v1.24.0 and framework/model asset hashes verified. Source commit 3433fb03; release stamp f8e4732e. Host-neutral orchestration is subsequent source work, not a new packaged release.

## Open questions / Deferred decisions

- Not yet scoped: give the `terminology` workflow-config key real consumers beyond the dashboard (rendered docs and messages). Premise correction recorded in `docs/reports/waveforge-fork-audit.md`: the key is read by `dashboard_lib.py` today, and Waveforge's values are keyed by Waveforge tier names (their `wave` is Wavefoundry's `change`), so a change must fix whose vocabulary the keys use before it can claim zero-edit merges.
- Graph-expansion/reranking quality comparison (evaluation AC-4) remains intentionally deferred; current retrieval ordering unchanged.
- Native Windows/Linux/Intel execution remains release follow-through.
- Investigate MCP's initial `graph_rebuilt=false` notice on an all-content full rebuild.
- The CoreML reranker probe fell back to CPU after `output_features has no value for logits`; no reranker fix included.
- Any other unfinished povc receipt must retain its original archive; qualified revision-2 repair: `/Users/coryhacking/.wavefoundry/dist/povc-storage-rebuild-repair-v2.zip`.
- Follow-ups recorded by the 1xtnr council, not in scope: bind the two `graph-index-system.md` builder-version mirrors to `docs_constants_validators._claims()`; a kind-aware `symbol_lookup` once `reads` binds get their own table; route `_scan_all_call_sites_in_file` through `_resolve_repo_path`.

- Record-layout follow-ups: conventional-root seed prose and an explicit nested-create parent argument remain outside this wave; canonical architecture and regression tests retain the consumer-identity lessons.
