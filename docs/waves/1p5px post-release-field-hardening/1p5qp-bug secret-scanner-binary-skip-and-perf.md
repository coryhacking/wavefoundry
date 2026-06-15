# Secret scanner: binary fast-skip + perf hardening

Change ID: `1p5qp-bug secret-scanner-binary-skip-and-perf`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-06-15
Wave: `1p5px post-release-field-hardening`

## Rationale

Field report **091yo** (CUDA-on-Linux host): `wave_close` and all `wave_new_*` tools **time out** because the docs gate's secrets scan takes ~54s — `scan_file_raw` reads `BINARY_SNIFF_BYTES` (8 KB) from **every** file to detect binary content before skipping it, and the repo has ~300 LanceDB segment files, zip archives, and `.so` files. The 8 KB read × hundreds of binaries dominates the scan.

Two related observations from the same operator: the scanner *considered* a gitignored framework `.zip` (the `rglob` fallback in `_get_all_files` doesn't respect `.gitignore`), and "we added size limits for semantic search / treesitter — do the same for secret scanning."

Investigation: the scanner already has the *content* guards (`MAX_FILE_BYTES` 5 MB skip; `MAX_LINE_BYTES` 32 KB per-line guard from wave 1p44s; NUL-byte sniff) — so binaries don't produce findings and long lines don't spin the regex. The missing piece is a **cheap extension fast-skip before the per-file read**, so known-binary/data artifacts never reach the 8 KB sniff at all.

## Requirements

1. **Extension fast-skip before any stat/read.** `scan_file_raw` skips files whose extension is a known binary/data type (archives, shared objects, LanceDB `.lance` segments, media, model weights, compiled artifacts) before the stat and the NUL-byte sniff — recorded as a `"binary file (extension)"` scan-skip. This is the 091yo fix.
2. **No change to detection correctness** for real source: a secret in a real source file (`.py`/`.js`/`.env`/…) is still flagged; only known-binary extensions are fast-skipped.
3. **Existing guards preserved**: `MAX_FILE_BYTES`, `MAX_LINE_BYTES` (32 KB), and the NUL-byte content sniff remain the fallback for non-extensioned binaries.

## Scope

**In scope:**

- `wave_lint_lib/secrets_validators.py`: `_BINARY_SKIP_EXTENSIONS` set + the fast-skip in `scan_file_raw` (before stat/read); tests.

**Out of scope (captured as remaining follow-ups, low severity — the extension skip already removes the spin):**

- Making the `rglob("*")` fallback in `_get_all_files` respect `.gitignore` (only runs in non-git / `git ls-files`-failure contexts; binaries reached this way are now extension-skipped anyway).
- Adding `wavefoundry-*.zip` / `.wavefoundry/index/**` to the scan `[allowlist].paths` (the extension skip covers `.zip`/`.lance`; a path allowlist would also skip non-extensioned LanceDB manifest/txn files — minor).
- Reading the scanner's `MAX_FILE_BYTES` from the indexer's `indexing.max_file_bytes` config for a single knob (nice-to-have; the 5 MB defaults already align).

## Acceptance Criteria

- [x] AC-1: a secret-looking string inside a binary-extension file (`.lance`/`.zip`/`.so`) is **skipped by extension** (no finding, recorded skip) without the 8 KB sniff; the same content in a `.py` source file is still flagged. Asserted by `test_binary_extension_files_are_skipped`; the pre-existing NUL-byte test repointed to a non-binary extension so it still exercises the content sniff.
- [x] AC-2: full suite + docs-lint green; no regression to existing scanner guards.

## Tasks

- [x] `_BINARY_SKIP_EXTENSIONS` + fast-skip in `scan_file_raw` before stat/read.
- [x] Test: binary-extension files skipped, `.py` control still flagged; repoint the NUL-byte test off `.dat`.
- [~] (deferred) rglob fallback `.gitignore` respect; pack/index path allowlist; config-aligned file cap.

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes |
| ---------- | ----------- | ---------- | ----- |
| scan-skip  | Engineering | —          | extension fast-skip + tests in `secrets_validators.py` |


## Serialization Points

- Shares `secrets_validators.py` with no other in-flight change.

## Affected Architecture Docs

`N/A` — perf guard within the secrets scanner; no contract/behavior change to detection of real source secrets.

## AC Priority

(Populated at Prepare wave.)

| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The 8 KB-per-binary sniff is what times out `wave_*` tools on the reporter's repo. |
| AC-2 | required | Must not regress real-source detection or the existing guards. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-15 | Field report 091yo: `wave_*` tools time out (~54s) — `scan_file_raw` reads 8 KB from every file (~300 binaries: LanceDB/.zip/.so). Confirmed the content guards (`MAX_FILE_BYTES`, `MAX_LINE_BYTES`, NUL sniff) already exist; missing piece is a pre-read extension skip. | `secrets_validators.py:scan_file_raw` |
| 2026-06-15 | **Implemented + verified.** Added `_BINARY_SKIP_EXTENSIONS` + fast-skip before stat/read (records `"binary file (extension)"`). Test added; repointed the NUL-byte test off `.dat`. **Full suite 3138 OK**; docs-lint clean. Lower-severity rglob/allowlist/config-cap items deferred (extension skip removes the spin). | `secrets_validators.py`, `test_secrets_validators.py` |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-15 | Extension fast-skip before the per-file read; defer rglob-gitignore + path-allowlist + config-cap | The extension skip is the targeted fix for the 091yo timeout (the 8 KB sniff over binaries); the deferred items are lower-severity and partly subsumed (binaries via the rglob fallback are now extension-skipped too). | (a) only raise/lower MAX_FILE_BYTES (rejected — doesn't help under-cap binaries); (b) do all four now (deferred the three low-severity ones to keep the change tight) |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| A real secret hidden in a binary-extension file is now skipped | By design — secrets in binaries are not the threat model; the content NUL-sniff still catches non-extensioned binaries, and source files are unaffected (test-guarded) |
| Extension denylist misses a binary type → still sniffed | The NUL-byte + size guards remain the fallback; the denylist just makes the common cases cheap |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
