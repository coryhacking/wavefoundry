# Kwargs Published As Required Mcp Parameter

Change ID: `1tmaz-bug kwargs-published-as-required-mcp-parameter`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-07-26
Wave: `1tj0l cwd-independent-host-surface-launchers`

## Rationale

Every first-party Wavefoundry tool declares `**kwargs: Any`. FastMCP turns that into an ordinary
schema property and marks it **required**, so the published contract for every tool demands a
meaningless argument:

```
wf_reopen_wave    required = ['wave_id', 'purpose', 'kwargs']
wf_current_wave   required = ['kwargs']
wf_list_waves     required = ['kwargs']
code_read         required = ['path', 'kwargs']
```

`wf_current_wave` takes no real parameters at all and still requires one. A caller that sends only
the genuine arguments is rejected with `kwargs | Field required`.

The defect is universal across the registered surface. Two independent live probes measured it: an
earlier one reported 84 of 84 registered tools, a prepare-council probe of `register_mcp_surface`
measured 83 of 83, and a source count of `kwargs: Any` returns 85 (the tools plus the helper). The
counts differ by how each probe enumerated the surface; **the load-bearing fact is that the set is
universal with no exemptions**, which all three agree on. Do not treat any of these numbers as the
contract.

### The fix point is the pydantic arg model, not the published schema

A prepare-council red-team seat falsified the first version of this plan by executing it. That
version scoped the fix to removing `kwargs` from each tool's published `required` and `properties`.
The seat applied exactly that to a live tool object and re-ran real dispatch:
`await mcp.call_tool("wf_current_wave", {})` **still** raised `ToolError: ... kwargs Field required`.

Dispatch validates against `fn_metadata.arg_model`, not against `tool.parameters`. The published dict
and the validating model are independent, and only the former was in scope. The correction must give
the `kwargs` field on the arg model a default so it is not required, with the published schema
corrected as the visible consequence.

### `_ensure_no_extra_args` does not do what this plan assumed

The first version justified keeping `**kwargs` on the grounds that it lets `_ensure_no_extra_args`
return a typed `unknown_arguments` envelope instead of a raw validation error, and required that the
fix "preserve" that behavior. **That behavior does not exist on the dispatch path.** The seat executed
three argument shapes against `wf_help` through `mcp.call_tool`:

| Sent | Result |
| --- | --- |
| `{"kwargs": {}, "bogus": 1}` | `status: ok` — pydantic's `extra` is unset, so `bogus` is dropped before the handler |
| `{"kwargs": {"bogus": 1}}` | `status: ok` — `_ensure_no_extra_args` strips the whole `kwargs` key including its payload |
| `{"bogus": 1}` | raw pydantic `kwargs Field required`, not the typed envelope |

No unknown-argument shape reaches the envelope through dispatch. The single test asserting otherwise
calls `_ensure_no_extra_args` directly, which is the raw-callable pattern this document's own AC-2
correctly forbids.

Two consequences. First, the requirement is to **establish** typed unknown-argument rejection, not to
preserve it. Second, the Decision Log's original reason for keeping `**kwargs` over removing it, that
its behavior was "worth keeping", was false, so that choice was made against a benefit the code does
not deliver. It is re-decided below on grounds that hold.

This defect is pre-existing and unrelated to the wave that surfaced it; it was found by a delivery
council reviewing `1ti11` and reproduced against the live registry.

## Requirements

1. No registered first-party tool publishes `kwargs` as a required parameter, and no registered
   first-party tool **rejects** a call that omits `kwargs`. The second clause is the real contract;
   the first is its visible form.
2. A caller that supplies only a tool's genuine arguments succeeds through the real MCP dispatch
   path, not merely through the underlying Python callable.
3. A caller that still sends the legacy empty `kwargs: {}` object continues to succeed. Compatibility
   does not extend to populated nested payloads that the server never meaningfully supported.
4. Unknown-argument rejection is **established, and never net-weakened by this change**. Removing the
   phantom required field also removes the only rejection that existed today, which was accidental:
   `{"bogus": 1}` is rejected now solely because `kwargs` is missing, so the fix alone converts that
   into a silent accept. The correction therefore lets the runtime model carry extra keys to
   `_ensure_no_extra_args`, which returns the typed `unknown_arguments` envelope, while the published
   schema remains strict with `additionalProperties: false`. A non-empty nested `kwargs` mapping is
   flattened for diagnostics and rejected through the same envelope; its payload is never silently
   stripped.
   **No shape may end up more permissive after this change than before it.**
5. The correction survives `wf_reload_mcp`, which re-registers the tool surface in place.
6. The fix tolerates FastMCP version variance, matching the existing `getattr`-with-fallback pattern
   used by `_registered_mcp_tool_names` and `_registered_mcp_tool_descriptions`.

## Scope

**Problem statement:** `**kwargs` in tool signatures is published as a required MCP parameter and
enforced as one by the dispatch-time arg model, so the documented call shape for every tool is wrong
and a schema-conforming client must send a meaningless argument. Separately, the unknown-argument
rejection those signatures exist to provide never fires through dispatch.

**In scope:**

- A registration-time correction to each tool's **`fn_metadata.arg_model`** so the `kwargs` field is
  not required (a default, then `model_rebuild(force=True)`), applied wherever the tool surface is
  built or rebuilt.
- Setting `extra="allow"` on the runtime arg model only so unknown keys reach
  `_ensure_no_extra_args`; this is a transport seam, not semantic acceptance.
- Correcting the published `required`/`properties` as the visible consequence, so the schema and the
  validator agree.
- Establishing typed unknown-argument rejection on the dispatch path for sibling unknown keys and
  keys nested inside a non-empty legacy `kwargs` mapping.
- Reapplication on `wf_reload_mcp`.
- Regression coverage over the live registry and the real dispatch path.
- Any live doc that shows a tool signature including `kwargs`.

**Out of scope:**

- Removing `**kwargs` from the tool signatures. See the re-decided Decision Log row: the reason is no
  longer "preserve valuable behavior" but "the whole-surface refactor is larger than this defect
  warrants, and the two can be separated".
- Rewriting closed-wave archives under `docs/waves/` to satisfy the docs sweep. Those are historical
  records and `AGENTS.md` forbids editing them.
- The `schema_version: true` scorer looseness and the `code_commit_provenance` attribution quirk,
  both raised by the same council and both judged non-blocking.

## Acceptance Criteria

- [x] AC-1: A red test asserts no registered first-party tool has `kwargs` in its published
  `required` list. It fails against the current code naming at least one offending tool, and passes
  after the fix. Asserted over the whole registry, not a sampled few.
- [x] AC-2: Calling a representative tool through the **real MCP dispatch path** with only its
  genuine arguments succeeds. A test that calls the underlying Python function directly does not
  satisfy this AC, because that path never applied the schema. This AC is the one that failed against
  the superseded published-schema-only fix, so it must be executed against the arg-model fix and seen
  to pass for that reason.
- [x] AC-3: Calling the same tool through the real dispatch path with legacy `kwargs: {}` still
  succeeds, proving existing generated callers are not broken. A populated mapping is a negative
  control and must not be treated as compatible.
- [x] AC-4: **A before/after matrix over all three probed shapes**, executed through real dispatch,
  recording each shape's behavior with the current code and with the fix. The required property is
  monotonic: **no cell may move from rejecting to accepting.** The runtime model deliberately uses
  `extra="allow"` only to route unknown sibling keys into Wavefoundry's typed rejection envelope;
  `{"bogus": 1}`, `{"kwargs": {}, "bogus": 1}`, and `{"kwargs": {"bogus": 1}}` are all rejected;
  the nested form reaches the typed envelope naming `bogus` rather than disappearing in
  `_ensure_no_extra_args`. A shape that regresses fails this AC and may not be resolved by documenting it.
- [x] AC-4b: The typed `unknown_arguments` envelope is reached through executed dispatch for both a
  sibling unknown key and a key nested inside legacy `kwargs`. Do not claim the envelope without an
  executed call producing it.
- [x] AC-5: After `wf_reload_mcp`, the registry still publishes no required `kwargs` and dispatch
  still accepts a call without it. **The test must route through the real reload path**
  (`server.py:196-207`, `_refresh_mcp_tool_surface` / `perform_mcp_reload`), which calls
  `remove_tool(name)` for every non-survivor before re-registering. A test that simulates reload with
  a second bare `register_mcp_surface(...)` call **passes vacuously**: `ToolManager.add_tool` returns
  the existing tool on a duplicate name and never rebuilds, so the assertion holds even with the fix
  never re-applied. The AC additionally requires a **negative control**: omitting the re-application
  must make the test fail. A green result without that control does not satisfy this AC.
- [x] AC-6: The correction degrades safely on a FastMCP layout it does not recognize: it leaves both
  the arg model and the schema untouched rather than raising, and the tool surface still builds.
  Proven with a patched registry shape.
- [x] AC-7: No **live** doc shows a tool signature carrying `kwargs`. Audit-and-skip is an acceptable
  outcome and is the expected one: a council census found zero live occurrences, with every remaining
  hit inside closed-wave archives that must not be edited. Record the audit result either way.
- [~] AC-9: Pin the SDK assumption required by `extra="forbid"`. — intentionally not met: the final
  runtime model does not use `extra="forbid"`; it accepts extras only long enough to return the typed
  `unknown_arguments` envelope, so this external assumption no longer exists.
- [x] AC-8: Docs gate and full framework suite green.

## Tasks

- [x] Write the AC-1 red test over the whole registry and confirm it fails for the stated reason.
- [x] Write the AC-2 dispatch test FIRST and confirm it fails when only the published schema is
  corrected, so the test discriminates the real fix point from the superseded one.
- [x] Add a version-tolerant post-registration pass that gives the `kwargs` field a default on
  `fn_metadata.arg_model` and strips it from the published `required`/`properties`, following the
  `getattr`-with-fallback pattern already used by the registry helpers.
- [x] Determine what unknown-argument rejection is actually reachable through dispatch for each of the
  three shapes, implement what is reachable, and record the rest.
- [x] Apply it wherever the surface is built, and confirm the `wf_reload_mcp` path re-applies it.
- [x] Add the dispatch-path tests for AC-3 and AC-4.
- [x] Audit live docs for published tool signatures containing `kwargs`; do not touch wave archives.
- [~] Add the AC-9 standing test pinning the `arguments`-injection assumption against the SDK request
  model — intentionally not met because the implemented typed-rejection seam does not rely on that assumption.
- [x] Full suite and docs gate.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| red-tests | implementer | — | Registry census AND the dispatch test that discriminates the fix point |
| arg-model-fix | implementer | red-tests | `fn_metadata.arg_model` default; schema corrected as consequence |
| unknown-args | implementer | arg-model-fix | Establish what is reachable; document what is not |
| reload-path | implementer | arg-model-fix | Re-apply on `wf_reload_mcp` |
| docs | implementer | arg-model-fix | Live-doc audit only; archives untouched |

## Serialization Points

- No shared files with the rest of the wave. This change edits `server_impl.py` tool registration;
  `1tjjj`, `1tjjk` and `1tjjl` all edit the renderers. Sequence it independently of the launcher work.

## Affected Architecture Docs

`docs/specs/mcp-tool-surface.md` if any documented signature shows `kwargs` (a census found none). No
ADR: this corrects a published schema and its validator to match the intended contract rather than
changing the contract.

## AC Priority

| AC | Priority | Rationale |
| -- | -------- | --------- |
| AC-1 | required | The visible form of the defect: the published contract for every tool is wrong. |
| AC-2 | required | The AC that falsified the first design. It must be executed against the arg-model fix and pass for that reason, not by coincidence. |
| AC-3 | required | Compatibility. Every existing caller sends `kwargs` because the schema demanded it. |
| AC-4 | required | Without the monotonic constraint, the fix silently removes the only unknown-argument rejection that exists; all three observed shapes must reject unknown data after the fix. |
| AC-4b | required | Separates "rejection happens" from "the framework's typed envelope happens". Conflating them is how the original plan came to assert behavior that never fired. |
| AC-5 | required | `wf_reload_mcp` rebuilds tool objects, so a fix applied only at first registration would regress invisibly. The negative control is required because the obvious way to write this test passes without the fix. |
| AC-6 | important | Startup must not break on an unrecognized FastMCP layout; degrade to leaving both model and schema untouched rather than raising. |
| AC-7 | required | Standard sweep, expected to be audit-and-skip. Recorded either way so a future reader knows it was checked, not skipped. |
| AC-9 | intentionally not met | The final design does not use `extra="forbid"`, so the external SDK-injection assumption this AC would have guarded no longer exists. |
| AC-8 | required | Standard gates. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-25 | Drafted from a delivery-council finding on wave `1ti11`, reproduced against the live registry: `wf_current_wave` and `wf_list_waves` publish `required = ['kwargs']` despite taking no real parameters. | Live registry probe over four tools; `server_impl.py:3039-3046`; 84 of 84 registered tools publishing required `kwargs` |
| 2026-07-26 | **Fix point corrected.** The published-schema-only design was falsified by execution: applying it to a live tool still produced `kwargs | Field required` through real dispatch, because dispatch validates `fn_metadata.arg_model`. Rewritten to target the arg model. | Prepare-council red-team seat, finding F2 |
| 2026-07-26 | Re-check repairs. The `preserve`-to-`establish` reframing introduced an escape hatch: because `{"bogus": 1}` is rejected today only as a side effect of the phantom required field, the fix alone would silently remove the sole existing rejection, and AC-4's "document the unreachable shape" clause would have permitted recording that new regression as behavior. AC-4 is now a monotonic before/after matrix, `extra="forbid"` is in scope, and AC-4b separates "rejection happens" from "the typed envelope happens". AC-5 additionally requires routing through the real reload path with a negative control, because a bare second `register_mcp_surface` call passes vacuously (`ToolManager.add_tool` returns the existing tool and never rebuilds). | Prepare-council red-team seat, findings F11 and F12, both executed including the vacuous-test demonstration |
| 2026-07-26 | Independent review closed the remaining compatibility escape hatch: only empty legacy `kwargs` is accepted; a populated mapping must reach the typed unknown-argument envelope. | Finding `legacy-kwargs-payload-remains-silently-accepted`; direct `_ensure_no_extra_args` counterexample |
| 2026-07-26 | **Justification corrected.** Requirement 4, AC-4 and the Decision Log rested on a typed `unknown_arguments` envelope that never fires through dispatch; three executed argument shapes returned `ok`, `ok`, and a raw pydantic error. Requirement reframed from preserve to establish, and the keep-`**kwargs` decision re-made on grounds that hold. | Prepare-council red-team seat, finding F3; `tests/test_server_tools.py:1766-1770` asserts via the raw callable |
| 2026-07-26 | Implemented a registry-wide normalization pass over the real FastMCP argument models. Public schemas omit `kwargs` and reject unknown properties; runtime models route sibling and populated nested unknowns into the typed handler, while empty `kwargs: {}` remains accepted. The pass runs at startup and after MCP reload and degrades safely on unknown registry layouts. | `test_server_tools.py` registry census, dispatch matrix, reload negative control and unknown-layout fixtures |
| 2026-07-26 | Final simplification audit removed redundant runner calls, and the canonical suite proved one was not redundant: runner-owned `wf_reload_mcp` registers after the implementation surface. Restored one post-runner normalization with a scope comment; reload reconstruction remains normalized at the implementation registration chokepoint. | Pre-repair whole-registry census failed only for `wf_reload_mcp`; focused census and dispatch controls pass |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-25 | Correct the published schema at registration rather than removing `**kwargs` from every tool signature. | The signatures exist so unknown arguments get a typed `unknown_arguments` envelope instead of a raw validation error, which is behavior worth keeping. | Remove `**kwargs` from every tool (rejected: whole-surface refactor); document the phantom parameter as intended (rejected: it is not intended). |
| 2026-07-26 | Set `extra="forbid"` alongside the default, rather than accepting the permissiveness the fix would otherwise introduce. | The `{"bogus": 1}` shape is rejected today only because `kwargs` is missing, so removing the phantom field converts the one existing rejection into a silent accept. A prepare-council probe executed the matrix and confirmed `extra="forbid"` restores rejection for both sibling-key shapes while AC-2 and AC-3 still pass. The nested `{"kwargs": {"bogus": 1}}` shape stays unreachable either way, because `_ensure_no_extra_args` strips the key with its payload; that limitation is pre-existing and honest to document. | Ship the default alone and document the shape-3 regression (rejected: records a defect this change introduces as if it were behavior, which is the laundering AC-4 now forbids); leave the phantom field in place to keep its accidental rejection (rejected: that is the defect). |
| 2026-07-26 | **Supersedes the row above on both counts.** Correct the pydantic arg model, with the published schema following as its consequence. And keep `**kwargs` for a different reason than originally given. | The published schema is not what dispatch validates, so the original fix point could not work and was proven not to. The original reason for keeping `**kwargs` was that its unknown-argument behavior was worth preserving; that behavior does not exist, so the reason was false. The surviving reason to keep the signatures is narrower and honest: removing them from every tool is a whole-surface refactor that changes error shape everywhere, and it is separable from this defect. | Remove `**kwargs` surface-wide now (rejected: larger blast radius than the defect warrants, and it would conflate two changes); keep the published-schema-only fix (rejected: falsified by execution); keep `**kwargs` on the original rationale (rejected: the rationale was false). |
| 2026-07-26 | Limit legacy compatibility to empty `kwargs: {}` and reject populated nested payloads through the typed envelope. | Generated callers need the empty shape only. Silently discarding a populated mapping is neither compatibility nor a defensible public contract. | Preserve arbitrary populated mappings (rejected: loses caller intent silently); remove every `**kwargs` signature now (rejected: larger independent refactor). |
| 2026-07-26 | Use a permissive runtime model only as the transport seam, with semantic rejection remaining in `_ensure_no_extra_args`; publish a strict schema independently. | `extra="forbid"` prevents the typed handler from seeing sibling unknowns, while `extra="allow"` plus the existing handler produces one consistent envelope. This is not public permissiveness because the handler rejects the extras. | `extra="forbid"` (rejected by real dispatch); remove all `**kwargs` signatures (separate surface-wide refactor). |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| The fix is applied to the published schema only and appears to work because a test never exercised dispatch | AC-2 is written to fail against exactly that mistake, and a task requires confirming it does before the real fix lands. |
| A strict validator rejects callers that still send `kwargs` once it leaves `properties` | **Server-side this cannot happen:** FastMCP registers the lowlevel handler with `validate_input=False`, so the published `inputSchema` is never server-validated here. The residual is purely client-side, and since no registered schema carries `additionalProperties: false`, a conforming client validator still accepts an extra `kwargs` property under JSON Schema defaults. AC-3 executes both forms through real dispatch. |
| A future SDK or host places a key inside `arguments` | The runtime model transports it to `_ensure_no_extra_args`, which returns the typed rejection envelope instead of raising a raw validation error or silently accepting it. |
| Making `kwargs` optional on the arg model changes validation behavior in ways the schema edit would not have | The arg model is the real validator, so this is the intended blast radius rather than a side effect; AC-3, AC-4 and AC-6 bound it, and AC-5 covers rebuild. |
| Unknown-argument rejection is claimed as established when only some shapes work | AC-4 and AC-4b require all three probed shapes and the typed envelope for both sibling and nested unknown keys. |
| A FastMCP version exposes the arg model differently and the pass raises during startup | AC-6 requires safe degradation on an unrecognized layout, leaving both model and schema untouched. |
| The docs sweep rewrites closed-wave archives to satisfy an AC | AC-7 states audit-and-skip is the expected outcome and Out of scope names the archives explicitly. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
