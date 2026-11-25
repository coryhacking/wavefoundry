# Consumer upgrade rehearsal

Owner: Engineering
Status: active
Last verified: 2026-11-24

Three offline macOS runs started with Wavefoundry 1.51.0+q5hc and a small Git project containing one existing memory, one wave, five stock lifecycle prompts, a stamped plan template and repository-level host permissions. Each route used a disposable checkout and an isolated home. The stdio MCP client invoked the installed server, listed its registered tools and called memory_brief. Models and dependencies came from the local cache.

## Final pair

**Result.** All six hops passed their 18 post-upgrade checks, reached the expected build, and produced exactly one terminal summary. Both CLI paths automatically cleaned up when their executing runner contained the fix. The legacy installed CLI required one manual cleanup. MCP required explicit cleanup after each primary.

Every route started from the same fully set up, lint-clean 1.51.0+q5hc checkout at the same path. Between routes we restored its APFS clone, kept the same private home and removed the previous route's staged candidate archives from the private discovery directory. The three routes ran sequentially. All used the explicit CPU setting documented below.

| Archive path relative to the source checkout | SHA-256 |
| --- | --- |
| `.wavefoundry/work/24buu/package/dist/wavefoundry-1.53.0.q5u0.zip` | `81ed6d2cc28b3e78d912b63514197addb55951ca8daea5e02583c8843006ab1d` |
| `.wavefoundry/work/24buu/package/dist/wavefoundry-1.53.0.q5u1.zip` | `c0b771482678830533d6660c11c40f391b537a417c19bb319a083fa2cd1b0043` |

Each archive contained the VERSION named in its filename. Both ZIP and embedded feature payload passed every CRC check. The 285 embedded framework members matched the outer archive. All 238 shipped scripts and seeds matched both the staging checkout and the final live checkout byte for byte. Across all 285 members, the only differences against live were the generated BUILD-PROVENANCE.json, UPGRADE-PROTOCOL.json, VERSION and MANIFEST. See `final-archives.json` for member counts and the generated package metadata differences.

| Actual public entry | 1.51.0 → q5u0 | q5u0 → q5u1 | Evidence directory |
| --- | --- | --- | --- |
| `python -B <release.zip> --root <target> --confirm-hosts-stopped` | Automatic cleanup | Automatic cleanup | `final-cli/cli/` |
| Installed `wf upgrade --pack <release.zip> --yes --confirm-hosts-stopped` | The installed 1.51 runner published the index, stopped at index_complete and printed the instruction to run `wf upgrade --cleanup`. We ran it once. | Automatic cleanup | `final-installed/cli/` |
| Served `wf_upgrade(phase="preflight_to_docs_gate", confirm_hosts_stopped=true)` | Fresh host, then explicit `wf_upgrade(phase="cleanup")` | Fresh host, then explicit cleanup | `final-mcp/mcp/` |

The direct archive saw source protocol 2 on both hops, checked the feature archive’s digest, extracted its runner to a temporary directory and executed it. Both direct calls reported `incoming_runner_ready` and `cleanup_complete`. The installed 1.51 CLI ran its existing runner. The direct archive cleanup still reported preserved verified ZIPs because it could not establish the parent directory’s ownership. The upgrade lock itself was removed.

For each hop, `hopN-primary-checkpoint.json` contains the retained record or JSON null when the CLI removed it. The corresponding `hopN-terminal.summary.json` holds the terminal summary, `hopN-inspect.checks.json` the 18 post-upgrade assertions, and `hopN-inspect.inventory.json` the response from a fresh MCP inventory and memory call. The upgrade log includes an additional nonterminal summary on paths with separate cleanup. Setup readiness and full docs lint were checked after each hop.

## First pair of candidate archives

Paths below are relative to the Wavefoundry checkout. SHA-256 covers the whole archive. Each internal VERSION matched the build label.

| Archive | SHA-256 |
| --- | --- |
| `.wavefoundry/work/24buu/package/dist/wavefoundry-1.53.0.q5ts.zip` | `b298cacc2f12938c11e969a592ee466df758316095274ceda545ae8fe8ddd6bc` |
| `.wavefoundry/work/24buu/package/dist/wavefoundry-1.53.0.q5tt.zip` | `ce2c96e77a2693031cabad53af689871a9ce3295c8bd092a86591af51c17ad15` |

Both 1.53.0 CLI entry points required a separate cleanup after successful publication on the second hop. The new CLI therefore missed its automatic cleanup requirement. The installed server correctly retained the separate MCP cleanup phase. All six final inventories passed after their required interventions.

| Route | 1.51.0 → q5ts | q5ts → q5tt | Evidence directory under this report |
| --- | --- | --- | --- |
| Direct release archive | Executed the ZIP successfully, then ran the installed CLI cleanup | Ran the installed CLI cleanup again | `pinned-cpu/cli/` |
| Installed CLI with --pack | Ran the CLI cleanup. The relocated baseline required one ordinary setup before its readiness check passed | Ran the CLI cleanup again | `installed-cli/cli/` |
| Served wf_upgrade | Called primary then cleanup through separate stdio sessions. The client logged a teardown exception after receiving the successful primary response | Called primary then cleanup through separate stdio sessions | `pinned-cpu/mcp/` |

All inventory checks covered the five new spec routes, absence of all five retired routes, allow and deny rules, five migrated prompts, the keep guidance, retired prompt references, the plan template ID and date, read-only memory revalidation counts, memory and event-ledger bytes, setup readiness and full docs lint. The direct archive migration changed the open fixture wave's review-policy re-prepare marker. All three routes retained its ID and planned status. The direct archive cleanup also reported that it preserved the private embedded ZIP because it lacked ownership proof for its parent.

With automatic provider selection, the first direct ZIP and MCP attempts stopped before publishing their new indexes. Legacy setup had published CPU INT8. An isolated runtime probe confirmed that the new automatic selection predicted full precision despite selecting the CPU execution provider. Setting WAVEFOUNDRY_EMBED_PROVIDER=cpu produced INT8. New checkouts used that supported setting from legacy setup through both upgrades. The original refused runs and checkpoints remain in `cli/` and `mcp/`.

The retained nonrequired handoff caused the redundant CLI cleanup. A second isolated replay preserved the actual q5ts → q5tt checkpoint in `diagnostic/cli/forward-lock.json`. It recorded successful index publication, no failure or required action, and `index_guard_handoff.required=false`. The unfixed classifier withheld cleanup. On an in-memory copy, removing only the optional handoff produced the expected cleanup continuation. The final archives passed with the real unmodified handoff records.

## Rehearsal limits

The fixture models a Phase 1 installation with enough project documentation for a real successful docs gate. It has no authored AGENTS.md or completed seed-by-seed Phase 2. The rehearsals exercised stock prompts and local exact-name host rules. Platform coverage is native Apple Silicon only. Network access was unnecessary. These are working-tree test packages.
