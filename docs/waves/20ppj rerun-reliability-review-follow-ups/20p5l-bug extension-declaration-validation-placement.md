# Extension declaration validation: report at declaration time, validate once

Change ID: `20p5l-bug extension-declaration-validation-placement`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-10-15
Wave: `20ppj rerun-reliability-review-follow-ups`

## Rationale

Commit `43621e07` added two extension declaration surfaces whose validation sits in the wrong place:

- `EXTENSION_LEGACY_CLAUDE_HOOK_COMMANDS` is validated only inside `legacy_claude_hook_commands`, which raises `ExtensionDeclarationError` at render time. A malformed entry aborts `wf_sync_surfaces` and upgrade rendering mid-render for every platform, while `declaration_problems` and the extension provenance still report the declaration as valid. `EXTENSION_UPGRADE_PREVIEW_TOOLS`, added in the same commit, was wired into `declaration_problems` correctly.
- `inference_provider.mode()` in extension mode re-imports `mcp_tool_extensions` and re-runs `_module_name_problems` and `_helper_module_problems` over the whole declaration. `_Adapter._operation` calls `mode()` on every embed and rerank batch, and `_select` does the same, so indexing a large repository through a declared provider re-validates the declaration thousands of times to re-derive a constant answer. The generation counter `tc._generation` is already part of the cache key and is the right invalidation signal.

## Requirements

1. `declaration_problems` validates `EXTENSION_LEGACY_CLAUDE_HOOK_COMMANDS` with the same rules `legacy_claude_hook_commands` enforces today (tuple of mappings with exactly `event` and `command`, nonempty strings, at most one `{{repo_root}}` placeholder and no other braces). `legacy_claude_hook_commands` becomes a pure expansion; it may keep a defensive raise but a malformed declaration is reported through `declaration_problems` before any render starts.
2. Declaration validity in extension mode is computed once per `tc._generation` and reused. `mode()` returns the cached verdict for the current generation; `_Adapter._operation` compares only the cheap `PROVIDER` and `ADAPTER_MODULE` values plus the generation it was built under.
3. A declaration that becomes invalid is still detected after the next generation bump, which is the existing contract for every other cached verdict in the provider.
4. Windows, macOS, Linux and WSL2: no platform-specific behaviour; both items are pure validation placement.

## Scope

**Problem statement:** one declaration is validated too late, another is validated too often.

**In scope:**

- `declaration_problems` and `legacy_claude_hook_commands` in `.wavefoundry/framework/scripts/mcp_tool_extensions.py`
- `mode()`, `_Adapter._operation` and `_select` in `.wavefoundry/framework/scripts/inference_provider.py`
- Regressions for both

**Out of scope:**

- Changing the rules themselves, the placeholder syntax, or the provider descriptor contract
- Any change to Tensorwell or local-mode selection

## Acceptance Criteria

- [x] AC-1: A malformed `EXTENSION_LEGACY_CLAUDE_HOOK_COMMANDS` entry (non-mapping, wrong keys, empty string, two placeholders) appears in `declaration_problems()` output; a valid declaration reports no problem.
- [x] AC-2: With a malformed entry declared, Claude settings rendering does not raise from inside the render; the declaration is rejected before rendering begins, through the same path every other declaration problem takes.
- [x] AC-3: In extension mode, a counter on `_module_name_problems` (or an equivalent oracle) shows the declaration validated at most once per generation across many `embed` and `rerank` batches, and validated again after `tc._generation` changes.
- [x] AC-4: An adapter built under generation N still raises `ProviderUnavailable` after the generation advances, proving the cheap check in `_operation` kept its invalidation.
- [x] AC-5: The change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Add the legacy hook rules to `declaration_problems` and a regression for AC-1 and AC-2.
- [x] Cache the extension-mode verdict per generation and reduce `_operation` to the cheap comparison; add the AC-3 and AC-4 oracles.
- [x] Confirm `_select` uses the cached verdict too.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Declaration problems | Implementer | Readiness | Single write owner |
| Provider caching | Implementer | Readiness | Same owner; independent files |
| Delivery review | QA and required reviewers | Both | Read-only |

## Serialization Points

- `.wavefoundry/framework/scripts/mcp_tool_extensions.py`
- `.wavefoundry/framework/scripts/inference_provider.py`
- `.wavefoundry/framework/scripts/tests/`

## Affected Architecture Docs

N/A. Validation placement inside the extension and provider modules; no boundary or contract moves. If `docs/specs/` describes where declaration problems are reported, the sentence already covers this once the legacy hook rules join `declaration_problems`.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Declaration integrity reporting |
| AC-2 | required | Render must not abort mid-way |
| AC-3 | important | Performance on large indexes |
| AC-4 | required | Caching must not weaken invalidation |
| AC-5 | required | Delivery gate |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-15 | Planned from the code review of `43621e07` | Review findings 5 and 6 |

| 2026-10-15 | Implementer preflight readback: Legacy hook rules run only during expansion and provider mode repeats declaration validation per batch. Move the same rules into declaration_problems and cache the extension verdict by generation, retaining cheap profile/generation checks in adapters. Verify malformed pre-render rejection, validation counters and stale-adapter refusal. | Admitted Requirements and AC read before code edits; focused failing reproduction then repair |

| 2026-10-15 | Moved unchanged legacy hook rules into shared declaration validation and included legacy-only declarations in declared(). Discovery found platform main had no shared declaration preflight; coordinator granted narrow ownership and main now rejects through existing roster before any writer. Original regression produced eight malformed/render failures and per-generation counter 164 versus initial 4. Repaired declaration suite 3 tests and provider suite 10 tests pass; cached verdict serves mode/_select and adapters retain cheap profile/generation checks. Three in-memory guard mutants detected (revalidation, generation guard, omitted shared validation). | test_mcp_tool_extensions.py: 3; test_inference_provider.py: 10; /private/tmp/ppj-extensions-mutants.py; synthetic providers only |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-15 | One change for both items | Both are declaration-validation placement in the same extension subsystem and share a reviewer | Two changes (rejected: doubles planning overhead for two small edits in one subsystem) |
| 2026-10-15 | Cache the verdict keyed by `tc._generation` | The generation is already the invalidation signal for the provider cache | (a) Validate once at adapter construction only: misses a declaration that changes without a generation bump, but so does the current code after `_load_provider` caches. (b) Keep per-batch validation but make it cheaper: still linear in declaration size per batch. |

## Risks

| Risk | Mitigation |
| --- | --- |
| A render path other than Claude settings calls `legacy_claude_hook_commands` and relied on its raise | Keep a defensive raise inside the expansion; `declaration_problems` runs first on every render entry |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
