# Waveforge Fork Audit

Status: reference
Owner: Engineering
Last verified: 2026-09-17

## Purpose

Direct evidence from Waveforge's actual git fork at `/Users/cory.hacking/Developer/waveforge` (remote `upstream` points at this repository), gathered to validate or correct the six-wave modularity plan against real divergence rather than the RFC's self-description. Companion to `docs/reports/wavefoundry-modularity-rfc.md` and `docs/reports/wavefoundry-implementation-kickoff.md`.

## Scale

Merge-base `86bdbe12` (2026-06-06). Since then: 220 commits on Waveforge's side, 232 on Wavefoundry's — over three months of fully independent, active development on both sides. Waveforge's `server_impl.py` is 18,654 lines versus this repository's 35,345.

## It's a deeper information architecture, not a rename

Wavefoundry's two-tier model (wave contains changes) maps onto a four-tier one in Waveforge: `feature` → `set` (= Wavefoundry's "wave") → `wave` (= Wavefoundry's "change") → `task`. Confirmed in `workflow-config.json`: `set_root: "docs/features/"`, `set-coordinator`, `set-council-readiness`/`set-council-delivery`, plus an entire `feature` tier (`wf_shape_feature`, `_feature_map_path`, `_promote_feature_in_map`, `_feature_slug_from_path`) that has no Wavefoundry equivalent at all.

None of the specific functions `1y042`/`1y044` cite by name — `wf_add_change`, `wf_prepare_wave_response`, `_resolve_change_doc_matches`, `_resolve_unique_change_doc`, the three `_wrap_*` middleware wrappers — exist in Waveforge's tree. Their equivalents (`wf_add_wave`, `wf_prepare_set`, `wf_review_set`, `wf_close_set`) are separately written functions, not renamed copies.

**What is shared by exact name** (verified via AST function-name extraction on both `server_impl.py` files): `list_waves`, `create_wave`, `register_mcp_surface`, `_read_workflow_config`, `_ensure_no_extra_args`, `_load_script`, `_read_project_sensors`, `_read_project_required_review_lanes`. These are the functions any Wavefoundry improvement reaches Waveforge through automatically on merge, with no extra work on either side.

## Confirmed: a git-branch-integrated, PR-gated review workflow with no Wavefoundry equivalent

`workflow-config.json`'s `review_policy` block: `mode: pr_review`, `branch_at: wave` (`wf_prepare_set` mints a branch per wave, format `set-<prefix>/wave-<n>-<slug>`), `allow_self_attestation`. Backed by Waveforge-only functions `_canonical_branch_name`, `_operator_signoff_present`, `_lane_has_signoff`, `_lanes_missing_signoff`, `_read_prepare_authority_lanes`, `_read_close_authority_lane`. `1y0bd`'s `phase_gates` (required sensors, required lanes) has no equivalent for branch emission, PR-gating, or self-attestation toggling — a real, unaddressed policy axis, not yet in scope of the current plan.

## Confirmed: Waveforge is still on the storage engine Wavefoundry retired

`import lancedb` live in `.waveforge/framework/scripts/indexer.py` (11 references) and `server_impl.py` (7). Zero `sqlite_storage_migration.py` / `index_state_store.py` / `sqlite_vector_store.py`-equivalent files exist anywhere in their tree. Wavefoundry's 1.22–1.24 LanceDB-to-SQLite consolidation is the single largest thing separating the two codebases and is outside the scope of the current plan — it is a one-time infrastructure catch-up Waveforge needs to run on their own side, using Wavefoundry's own documented migration path (`sqlite_storage_migration.py`, `wf upgrade`'s migration handling), not new work here.

## Other confirmed gaps outside current scope

- JIRA integration (`wf_sync_jira`, `_fire_jira_hook`, `_fire_jira_create_hook`, `wf_jira_push_state`) — a capability, not a naming difference; no Wavefoundry equivalent.
- A different lifecycle-ID minting scheme (Wavefoundry: `days_since_epoch * 4096 + hash entropy`, epoch 2026-07-03; Waveforge: 5-minute-bucket scheme, epoch 1999-05-01). IDs from either side cannot collide, but carry no cross-project chronological meaning.
- Several of Wavefoundry's more recent operational config sections (`setup` timeouts, `docs_lint` timeouts, `context_efficiency.projection`) are absent from Waveforge's config — those waves were never adopted either, independent of anything in this plan.
- `journal_root: "docs/agents/journals/"` is still live in Waveforge's config; Wavefoundry migrated away from journals into the memory system on this side.

## Good news: the "carve out cleanly" infrastructure is already close to clean

Direct inspection of `.wavefoundry/framework/scripts/chunker.py` and `graph_indexer.py` (the code that builds the semantic, graph, and lexical indexes): nearly every "wave" reference in both files is a provenance comment citing Wavefoundry's own internal development-wave ID (`# wave 1p66e`, `# wave 130ol`) — an unrelated internal meaning, not a dependency on the wave/change document concept. Neither file has section-heading-aware parsing of `wave.md`'s internal structure. Secret-scanning logic shows the same negligible coupling. Once `1y042`/`1y043` land (removing the remaining path-level coupling) and Waveforge separately completes the LanceDB migration, this subsystem should merge close to friction-free — the RFC's original promise, now evidenced rather than assumed.

One small, concrete fix belongs to whoever does the eventual rename: `chunker.py`'s marker-region regex already anticipates multiple product-name prefixes (`r"<!--\s*(?:wave|waveframework|wavefoundry):[\w:-]+\s+begin\s*-->"`) but not `waveforge`. A one-line addition, not a design change.

## New finding: a mostly-unused configuration seam for vocabulary labeling

`docs/workflow-config.json` already declares `"terminology": {"wave": "wave", "change": "change", "task": "task"}` — and Waveforge independently extended the same key with `{"feature": "Feature", "set": "Set", "wave": "Wave", "task": "task"}`. Nothing in `server_impl.py` reads this key on either side. Correction (2026-09-16, verified against the local tree): the key is not entirely unread — `dashboard_lib.py` copies it into the dashboard payload (`config["terminology"]`), so the dashboard is its one live consumer today; the server, renderers, and lint do not read it. This remains the natural home for the vocabulary-labeling half of the terminology gap: a change that makes rendered docs and messages substitute these labels dynamically.

**Caveat on the "zero edits on merge" idea:** the two configs key the map by *different* vocabularies. Wavefoundry's keys name Wavefoundry tiers (`wave` = a wave record, `change` = an admitted change doc). Waveforge's keys name Waveforge tiers, where their `wave` is Wavefoundry's `change` and their `set` is Wavefoundry's `wave`. A label map that Wavefoundry code reads by its own tier names would therefore render Waveforge's `"wave": "Wave"` against the wrong tier. Any change here must first state whose vocabulary the keys belong to (recommended: Wavefoundry's internal tier names as keys, display labels as values), and Waveforge would need a one-time key remap on merge. **Not yet scoped as a change** — recorded here as an open recommendation pending operator decision, sibling in shape and risk to `1y042`/`1y0bd`.

## Reassuring structural point on the feature tier

As long as Waveforge's `feature`-tier code stays additive — new functions calling down into wave/change (their vocabulary) primitives, rather than edits scattered inside Wavefoundry's own functions — it is inherently low merge-risk regardless of anything in this plan, because a three-way merge handles "the other side added an independent layer" far better than "the other side modified the same lines." The concentrated risk is specifically the renamed wave/change-tier primitives, which the operator has already decided to treat as manual rename work rather than a config problem. The plan does not need to solve that; `1y0h1`/`1y0h2` help it stay tractable, since renaming call sites inside a small, focused module is easier to do correctly than renaming them inside a 35,000-line file.

## Net assessment against the six-wave plan

| Wave | Effect of this audit |
| --- | --- |
| `1y0do tool-surface-snapshot` | Unaffected; validates scope is correctly limited to input schemas. |
| `1y0gz record-layout-roots` | Directly validated: Waveforge's `set_root`/`_resolve_wave_doc_matches`/`_plan_wave_doc_path`/`_move_wave_doc` confirm they built their own bespoke path-resolution layer for exactly this need. Chunker/graph-indexer cleanliness confirms the resolver's value extends up through indexing once path-level coupling is removed. |
| `1y0h0 typed-phase-gates` | Validated for what it covers (sensors, lanes); confirmed out of scope for what it doesn't (branch emission, PR-gating, self-attestation) — an honest boundary, not a defect. |
| `1y0h1 tool-registry-dispatch` | Strengthened: `register_mcp_surface`, `_ensure_no_extra_args`, `_load_script`, `_read_workflow_config` are name-identical across both forks today, meaning this wave's improvements reach Waveforge automatically on merge. |
| `1y0h2 handler-module-split` | Strengthened for the reason above; the specific code-navigation/graph tool names were not individually verified against Waveforge's fork and remain an open detail, not a blocking one. |
