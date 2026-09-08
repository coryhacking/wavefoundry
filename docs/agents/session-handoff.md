# Session Handoff

Owner: Engineering
Status: idle
Last verified: 2026-09-08

## Current Session

Active wave: none.

Last closed wave: `1xgbe context-efficiency-marker-placement` (2026-09-08), change `1xgbd`. Context Efficiency headings now precede their begin markers. Renderer and replacement remain compatible with old checkpoints;118 existing wave records were normalized without changing accounting data.

All 3 ACs and tasks complete; independent code/QA delivery reviews passed with no actionable findings. Current full suite: 8,560 tests across 75 files, three skips; docs validation passed. Evidence is in wave.md and events.jsonl. No deferrals or new memory candidates. All edit gates closed.

Prior waves 1xgbc (lexical dashboard) and1xfbh (upgrade retry pruning) are closed. The operator requested a combined commit of these closed waves, the local TechDocs refresh, and the 1.22.0 changelog updates. Destination upgrade does not bulk-reformat closed waves; new/subsequent checkpoint publications use the new renderer. Dashboard remains running at http://127.0.0.1:43127/dashboard.html.

## Open questions / Deferred decisions

None. Packaging and release publication have not been requested. TechDocs validation passed with zero publication findings; the audience comparison remains non-informative because the startup pages are unchanged from HEAD.

## Upgrade instruction decision (2026-09-08)

The operator explicitly accepted the first-hop retry risk when upgrading an older protocol-2 installation into 1.22.0 and requested retaining the standard MCP-first `wf_upgrade` path. Removed the mandatory staged-runner exception from the canonical seed and local upgrade prompt; aligned TechDocs and the 1.22.0 changelog. Recovery implementation is unchanged. This is an instruction-only maintenance edit under the Stage Gate documentation exemption; it does not reopen the closed recovery wave. The planned LanceDB evaluation wave `1xhbo` remains separate and unimplemented.

The operator approved a scoped Stage Gate waiver to update the existing upgrade-guidance test in `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py` to match this decision. The waiver covers that test adjustment only; recovery behavior and its runtime tests remain unchanged.
