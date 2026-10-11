# Local 1.29.0 test pack qualification

Owner: Engineering
Status: complete
Last verified: 2026-10-11

## Current artifact

`1.29.0+pvyg`: `/Users/coryhacking/.wavefoundry/dist/wavefoundry-1.29.0.pvyg.zip`.

- SHA256: `f8f08baa3a18680c541a66f89896eabfd7b6f70b2d01160be141df63f5e0a630`.
- Size: 10,469,987 bytes; 258 outer ZIP members.
- Includes closed waves `20bw2`, `20cw2`, `20dkg`, `20d90`, `20d91`, `20d92` and `20dkl`, committed as `6717540a`; qualification used clean source commit `2d079a8f`.
- All 247 shipped framework source members match the qualified source exactly. Outer/embedded CRCs, selection hashes, executable bridge sources, protocol metadata and MANIFEST inventory pass. Packed changelog equals the committed root changelog; VERSION and prompt manifest agree on `1.29.0+pvyg`.
- Tests, runner, receipts, indexes, bytecode, benchmark captures and private wave records are absent. One self-contained local feature pack; no models, push, tag or published release.

## Qualification

All profiles executed sequentially in an isolated checkout with four workers and bytecode caching disabled. Every file passed. Framework hash stayed `de46cb4635a4aea5ea516912ce587ce911fd0958abd07c25fe80c1c0796cdc22` through qualification, packaging and stamp copyback. Required docs/garden/manifest gates remained enabled; the build ran once.

| Check | Result |
| --- | --- |
| Default | 12,336 tests /185 successful workers /12 skips; 1031.575s. |
| Second vocabulary/layout | 12,328 tests /185 successful workers /28 skips; 1143.963s. |
| Declared tools | 12,336 tests /185 successful workers /12 skips; 1121.622s. |
| Exact skip comparisons | Both deterministic readers pass. Second has exactly 16 explicitly marked default-only extras; declared matches baseline IDs and reasons exactly. |
| Assets and bootstrap | Seven vendor members and the bootstrap requirement/wheel hash table match the prior approved pack. Pin 0.12.4 is unchanged for this same-version local rebuild; no fresh online registry verification. All four advisory sensor decisions remain settled. |

The genuine default receipt dated `2026-10-11T18:42:48.975913+00:00` was transferred byte-identically after checking source identity; SHA256 `17295d4e81dc3374f95a6729a7a3a5e78c859fe266c029dd3a9ccd23080ce140`. No source/assertion changes, composite receipts or waivers were used during packaging. Profiles qualify packaging; independent delivery authority remains in the closed wave ledgers.

Native Windows, live consumer upgrades, actual model/network downloads and live host/index behavior were not exercised. Archive verification establishes source and composition; select this exact ZIP for testing.

## Reproduction and retention

Run `run_tests.py --qualification-report .wavefoundry/cache/qualification/default.json --no-cache`, then complete `--profile second` and `--profile declared` runs sequentially with their own report paths. Compare both with `qualification_report.py --compare ... --profile <profile>`. Build: `python3 -B .wavefoundry/framework/scripts/build_pack.py --version 1.29.0 --output <temporary-dist>`.

Three replaceable execution-origin reports and the build summary remain in ignored `.wavefoundry/cache/`; no permanent evidence folder was added. Duplicate temporary checkouts/caches, including the new package tree, were removed after verified artifact/report transfer. Unique historical baselines and cited diagnostics were preserved. Lasting decisions remain in wave records and authoritative ledgers.

## Previous artifact

`1.29.0+pvto`, SHA256 `3517c7e425e3f4c04b5eeaf0f3bac57a05542ea202f1d91f3366eb63d6c6e6b5`, predates these seven waves. Its qualification hash `1b296ff8983a72a297a04f22e9f4b35dd68ccdeadfd392cc8f3dff32136b0640` does not qualify this build. Older waived packs supply no authority for `1.29.0+pvyg`.
