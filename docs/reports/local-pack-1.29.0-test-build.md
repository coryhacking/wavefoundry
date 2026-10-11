# Local 1.29.0 test pack qualification

Owner: Engineering
Status: complete
Last verified: 2026-10-10

## Current artifact

`1.29.0+pvqp`: `/Users/coryhacking/.wavefoundry/dist/wavefoundry-1.29.0.pvqp.zip`.

- SHA-256: `775f1f1536040424b8f413af6ca476043d876a2bcb702cf9258b00febeed14f4`.
- Size: 10,395,945 bytes; 256 ZIP members; outer and embedded feature ZIP CRC checks pass.
- All 245 source framework members match the tested snapshot byte-for-byte. The two additional generated members, MANIFEST and UPGRADE-PROTOCOL.json, match the exact inventory, version and protocol contract. Packed changelog matches root CHANGELOG.md; VERSION and prompt manifest agree. The executable protocol bridge is present and temporary composition files were removed.
- Tests, runner, receipts, indexes, bytecode caches, benchmark captures and private wave records are absent. This is a local feature-only pack; no model asset or release was built.

## Qualification

The operator-authorized isolated checkout used public reachable history and intended 2071o/2080c/20asl working files, excluding unrelated queued waves and private ignored records. All three fresh runs used two workers and disabled bytecode caching. Framework hash stayed `c8d6a4134e202a505142cdd7ac3958048682eec85fad6207da27ac3671ffc88e` through qualification, packaging and genuine receipt/stamp copyback.

| Check | Result |
| --- | --- |
| Default | 12,134 tests / 181 files / 12 skips; 1244.080s. Genuine green receipt dated 2026-10-10T19:26:17.934365+00:00. |
| Second vocabulary/layout | 12,126 tests / 181 files / 28 skips; 1253.143s; every file passes. |
| Declared tools | 12,134 tests / 181 files / 12 skips; 1254.164s; every file passes. |
| Exact skip comparison | Both deterministic readers pass. Second has exactly 16 explicitly marked default-only skips beyond baseline; declared matches baseline IDs and reasons exactly. |
| Vendored assets | Registry integrity and file comparisons pass for elkjs 0.10.0, react-dom 18.3.1 and react 18.3.1; these assets remain unchanged in the tested source. |
| Documentation/package gates | Garden, full lint and manifest gates enabled and passing. No qualification waiver. |

Reproduce with `run_tests.py --qualification-report .wavefoundry/cache/qualification/default.json`, then the same command with `--profile second` and `--profile declared`; compare each profile with `qualification_report.py --compare ... --profile <profile>`. Build command: `python3 -B .wavefoundry/framework/scripts/build_pack.py --version 1.29.0`. Complete executed commands, identities and worker records remain in the ignored qualification cache.

Profiles are packaging checks, not independent wave delivery approvals. The receipt attests framework inputs rather than unrelated project docs. Earlier runs invalidated by changing inputs, timing failures or the historical fixture's false skip are excluded. Native Windows execution remains pending; platform skips remain visible. This archive precedes queued waves 20b39/20b3a/20b3b.

The reviewed 0.12.4 bootstrap pin/hash table remains unchanged for this same-version local rebuild; the mature 0.12.15 candidate remains a next-release source change. All four advisory sensors have decided_wave; no sensor policy changed.

## Evidence retention

Exact execution-origin reports occupy three replaceable files under ignored `.wavefoundry/cache/qualification/`; one replaceable `.wavefoundry/cache/local-pack-qualification.json` records their genuine contents, comparisons, archive metadata and snapshot origin. Verbose captures stay under `/private/tmp/wf-local-pack-2087n/`. Final implementation evidence is in the 2071o, 2080c and 20asl wave summaries and immutable ledgers. No permanent supporting folder was added.

## Earlier builds

`1.29.0+pvkw` (SHA-256 `d17d7ae11a5421c7fc54ad5cd23a49f6470ead2d029448090366da6e51bd6f7e`) predates these graph and fixture repairs. `1.29.0+pviw` (SHA-256 `ba0a8fc6538929b73fe599c41373e1be8565c5815cc32222237c3e8e5e39d1ab`) predates 205jp/2071p; its skip waiver applied only to that archive. Earlier diagnostic results retain their original counts and limitations. No waiver applies to pvqp. No commit, push, tag or publication was performed.
