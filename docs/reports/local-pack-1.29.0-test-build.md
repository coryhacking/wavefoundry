# Local 1.29.0 test pack qualification

Owner: Engineering
Status: complete
Last verified: 2026-10-10

## Current artifact

`1.29.0+pvto`: `/Users/coryhacking/.wavefoundry/dist/wavefoundry-1.29.0.pvto.zip`.

- SHA256: `3517c7e425e3f4c04b5eeaf0f3bac57a05542ea202f1d91f3366eb63d6c6e6b5`.
- Size: 10,449,911 bytes; 258 outer ZIP members.
- Includes the completed graph, fixture, Windows/CRLF, upgrade diagnostics and resilience changes closed in waves `2071o`, `2080c`, `20asl`, `20b39`, `20b3a` and `20b3b`, committed and pushed as `91578966` before packaging.
- All 247 framework source members match the qualified source exactly. Outer and embedded feature CRCs, selection hashes, executable bridge sources, protocol metadata and MANIFEST inventory pass. Packed changelog equals the complete root 1.29.0 section; VERSION and prompt manifest both read `1.29.0+pvto`. Internal composition files were removed.
- Tests, runner, receipts, indexes, bytecode caches, benchmark captures and private wave records are absent. This is a local feature-only pack; no model asset, tag or GitHub release was built.

## Qualification

Framework hash stayed `1b296ff8983a72a297a04f22e9f4b35dd68ccdeadfd392cc8f3dff32136b0640` through qualification, packaging and stamp copyback. The new local build reused all three complete execution-origin qualification reports after verifying unchanged framework inputs, worker inventory and exact skip comparisons. The qualified source is unchanged from pvta; only the build stamp is new. Tests used the operator-authorized isolated checkout and two workers, with bytecode caching disabled. Packaging used the clean source checkout before creating the next waves. Required docs/garden/manifest gates remained enabled.

| Check | Result |
| --- | --- |
| Default | Reused genuine current green: 12,266 tests / 185 complete successful workers / 12 skips; 1207.635s. Receipt dated 2026-10-11T02:29:32.596839+00:00, byte-identical after packaging. |
| Second vocabulary/layout | 12,258 tests / 185 complete successful workers / 28 skips; 1876.540s. |
| Declared tools | 12,266 tests / 185 complete successful workers / 12 skips; 1384.869s, standalone rerun. |
| Exact skip comparison | Both deterministic readers pass. Second has exactly 16 explicitly marked default-only extras; declared matches baseline IDs and reasons exactly. |
| Vendored assets and bootstrap | All seven dashboard vendor members and the bootstrap requirement/wheel hash table match the prior approved pack exactly; its registry verification is reused. Pin 0.12.4 remains unchanged for this same-version local rebuild. All four advisory sensor decisions are settled. |

One initial concurrent declared run failed `DashboardManagedIdentityTests.test_mcp_start_confirms_serving_own_child`: its child exited before serving. The unchanged focused dashboard file then passed all 228 tests with its one baseline skip; the complete standalone declared run passed every file. Dashboard fixtures share the fixed localhost range 43127–43129, so run packaging profiles sequentially to avoid competing fixtures. Port contention is consistent with the observations, but the historical child's stderr was discarded and its exact exit cause is not proven. The initial red report is diagnostic only; no source, assertion or skip change, composite receipt or waiver was used.

Profiles are packaging checks, not independent wave delivery approvals. Native Windows execution, actual model/network downloads and a live consumer upgrade were not performed. Archive verification establishes its source and composition, not every target's runtime behavior. Same-version local builds intentionally retain 1.29.0 and use a fresh time suffix; select this exact archive for testing.

## Reproduction and retention

Run `run_tests.py --qualification-report .wavefoundry/cache/qualification/default.json` when the standing default receipt is not current, then run the complete suite with `--profile second` and `--profile declared` sequentially. Compare each with `qualification_report.py --compare ... --profile <profile>`. Build command: `python3 -B .wavefoundry/framework/scripts/build_pack.py --version 1.29.0`. The build ran once with all gates enabled and a temporary output directory; the verified archive was copied byte-identically to the standard durable dist path.

Three replaceable execution-origin reports remain under ignored `.wavefoundry/cache/qualification/`; `.wavefoundry/cache/local-pack-qualification.json` records current comparisons and archive metadata. The existing `20b3b-default.json` stays because the wave qualification cites it. Raw probes, logs and the excluded initial red report remain temporary under `/private/tmp/wf-local-pack-20b3b/`; no permanent supporting folder was added. Implementation decisions and review authority remain in the closed wave records and immutable ledgers.

## Previous artifact

`1.29.0+pvqp`, SHA256 `775f1f1536040424b8f413af6ca476043d876a2bcb702cf9258b00febeed14f4`, predates `20b39`, `20b3a` and `20b3b`. Its default/second/declared runs passed for source hash `c8d6a4134e202a505142cdd7ac3958048682eec85fad6207da27ac3671ffc88e`; those results do not qualify the current source. Older waived builds do not supply authority for pvto.
