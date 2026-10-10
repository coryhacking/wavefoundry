# Local 1.29.0 test pack qualification

Owner: Engineering
Status: complete
Last verified: 2026-10-09

## Current artifact

`1.29.0+pvkw`: `/Users/coryhacking/.wavefoundry/dist/wavefoundry-1.29.0.pvkw.zip`.

- SHA-256: `d17d7ae11a5421c7fc54ad5cd23a49f6470ead2d029448090366da6e51bd6f7e`.
- Size: 10345958 bytes; 252 ZIP members; CRC check passes.
- All241 present canonical framework members match current source byte-for-byte; packed changelog matches root CHANGELOG.md. VERSION and prompt manifest match the build. Protocol bridge entry point is present.
- Tests, runner, receipts, indexes, bytecode caches and wave evidence are absent. No model-set asset, tag, publication, commit or push was requested.

## Qualification

| Check | Result |
| --- | --- |
| Default | Matching green12057-test/178-file receipt from2026-10-10T00:55:10.191968+00:00; current command reuses it. Framework inputs_hash92a62480d6b7a6e1a876f32c1880e0f948939e7d868ea9cb9e5d1800aca54ab5. |
| Second vocabulary/layout | 12049tests/178files/28skips;692.016s; every file passes. |
| Declared tools | 12057tests/178files/13skips;688.685s; every file passes. |
| Exact skip comparison | Current baseline identities/reasons checked using10 isolated selected checks and the full620-test lifecycle worker. All356 profile worker records present, distinct and successful. Second has15additional default_profile_only skips; declared equals baseline. One shared second-profile reason changes to its explicit default-only marker. |
| Vendored assets | Online registry integrity and file comparisons pass for elkjs0.10.0, react-dom18.3.1 and react18.3.1. |
| Documentation/package gates | Build garden/lint/manifest gates enabled and pass. No source-framework test receipt or profile gate waived. |

Profile runs are packaging checks, not wave delivery receipts. The receipt attests framework code rather than the whole repository. A preliminary diagnostic lifecycle run was invalidated by coordinator handoff edits; it is excluded. Its quiet rerun passes620tests/3skips in228.729s and supplies actual baseline output. Native Windows execution remains pending; platform skips remain visible.

The reviewed0.12.4 bootstrap pin/hash table is retained for this same-version local non-release rebuild; the mature0.12.15 candidate remains a next-release source change, as already recorded. [PyPI metadata](https://pypi.org/pypi/uv/0.12.15/json). All four advisory sensors have decided_wave; no sensor policy was changed.

## Evidence retention

Current exact worker/skip metadata occupies one replaceable, ignored `.wavefoundry/cache/local-pack-qualification.json`; verbose current captures and commands stay in `/private/tmp/wf-local-pack-current/`. Source identities, limits and wave delivery evidence remain in the closed2071n/2071p wave summaries and immutable ledgers. The historical [exact inventory](../waves/2071n%20profile-skip-qualification/evidence/delivery/final/skip-inventory.json) has the same skip identities/reasons, with its original execution counts preserved.

## Earlier build

The earlier1.29.0+pviw local pack (SHA256ba0a8fc6538929b73fe599c41373e1be8565c5815cc32222237c3e8e5e39d1ab) predates205jp and2071p. Its additional-profile-skip waiver applied only to that archive; it was not release qualification. The previous detailed diagnostics remain temporary. No waiver applies to the current pack.
