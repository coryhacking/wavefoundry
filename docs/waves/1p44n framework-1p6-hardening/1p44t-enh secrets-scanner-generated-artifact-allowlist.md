# Secrets Scanner Generated-Artifact Path Allowlist Defaults

Change ID: `1p44t-enh secrets-scanner-generated-artifact-allowlist`
Change Status: `complete`
Owner: Engineering
Status: planned
Last verified: 2026-06-09
Wave: 1p44n framework-1p6-hardening

## Rationale

The framework secrets scanner's path allowlist already short-circuits image, font, office, and binary files plus common lockfiles and `node_modules`, but its coverage of generated/minified web artifacts is narrow and brittle. In `scan-rules.toml:98-131`, the `[allowlist].paths` list covers binary/office EXTENSIONS at `scan-rules.toml:107-109` (png/bin/dll/exe/pdb/gltf...), lockfiles at `scan-rules.toml:110`, `:114`, `:118`, `:122`, and `node_modules` at `scan-rules.toml:117` — but minified and source-map files are only excluded through a LIBRARY-SPECIFIC regex at `scan-rules.toml:120` hardcoded to `angular|bootstrap|jquery|plotly|swagger-ui`. There is NO generic `*.min.js` / `*.min.css`, NO generic `*.map` / `*.js.map` source-map rule, NO `*.snap` (Jest snapshot) rule, and the binary-extension group omits `wasm`/`node`/`a`/`o`/`so`/`dylib`/`class`. Generated artifacts under any other name (a project's own bundle, a non-library vendored minified file, a compiled `.wasm`/`.node` module) therefore reach the scanner's content path and waste read/scan cycles while inflating false-positive surface.

This is defense-in-depth that complements wave 1p44s's engine guards. Path-allowlist matching happens BEFORE `read_text` — `scan_file_raw` at `scan-rules.toml`-consuming `scan_secrets.py:507` and `:522` calls `_path_matches_allowlist` (`scan_secrets.py:181`) prior to reading file bytes — so adding these generic patterns cheaply short-circuits matched files without opening them. Note: the secrets report's claimed "operator mitigation — 4 regexes in `docs/scan-rules.toml`" is NOT present in this repo's project file (it carries only test-dir exclusions), so the framework engine remains fully exposed; these are real defaults to add, not duplicates of an existing project override.

## Requirements

1. Add a generic minified-artifact path rule to `[allowlist].paths` matching `*.min.js` and `*.min.css` (and their `*.min.js.map` / `*.min.css.map` companions) regardless of library name: `(?i)(?:^|/)[^/]+\.min\.(?:js|css)(?:\.map)?$`.
2. Add a generic source-map path rule matching `*.js.map`, `*.css.map`, `*.mjs.map`, `*.cjs.map`: `(?i)(?:^|/)[^/]+\.(?:js|css|mjs|cjs)\.map$`.
3. Add a Jest snapshot path rule matching `*.snap`: `(?:^|/)[^/]+\.snap$`.
4. Broaden the binary-extension allowlist group at `scan-rules.toml:109` to additionally cover compiled/binary module extensions `wasm|node|a|o|so|dylib|class`.
5. The new rules must be inserted into `[allowlist].paths` after the library-specific minified rule at `scan-rules.toml:120` so the generic patterns sit alongside the artifact-oriented entries, and must preserve the existing list ordering and TOML triple-quoted string style.
6. The existing library-specific rule at `scan-rules.toml:120` and all other current entries remain unchanged (the generic additions subsume but do not remove it).
7. These additions are documented in this change as defense-in-depth — a complement to, NOT a substitute for, the 1p44s engine line/size/NUL guards, which still protect against unexpectedly-named giant or binary files.

## Scope

**Problem statement:** The framework secrets scanner's `[allowlist].paths` excludes minified/source-map artifacts only through a library-name-specific regex and omits several compiled-binary extensions and Jest snapshots, so generically-named generated artifacts reach the scanner's content path, wasting cycles and inflating false-positive surface.

**In scope:**

- Adding generic `*.min.{js,css}(.map)`, generic `*.{js,css,mjs,cjs}.map`, and `*.snap` path rules to `[allowlist].paths` in `.wavefoundry/framework/scan-rules.toml`.
- Broadening the binary-extension group at `scan-rules.toml:109` to add `wasm|node|a|o|so|dylib|class`.
- Test coverage asserting representative artifact paths are excluded by the shipped default allowlist.
- A note in this change recording the defense-in-depth relationship to 1p44s.

**Out of scope:**

- Engine-level line-count/size/NUL-byte guards (owned by wave 1p44s).
- Any change to the project-level `docs/scan-rules.toml` override file or to allowlist `regexes`/`stopwords` sections.
- Changing the `_path_matches_allowlist` matching algorithm or where it is invoked in `scan_file_raw`.
- Adding allowlist entries for languages/artifact types not named in this brief.

## Acceptance Criteria

- [x] AC-1: `[allowlist].paths` in `.wavefoundry/framework/scan-rules.toml` contains the generic minified rule `(?i)(?:^|/)[^/]+\.min\.(?:js|css)(?:\.map)?$`, inserted after the existing library-specific rule at line 120. — inserted directly after the library rule.
- [x] AC-2: `[allowlist].paths` contains the generic source-map rule `(?i)(?:^|/)[^/]+\.(?:js|css|mjs|cjs)\.map$`.
- [x] AC-3: `[allowlist].paths` contains the Jest snapshot rule `(?:^|/)[^/]+\.snap$`.
- [x] AC-4: The binary-extension group (currently at `scan-rules.toml:109`) is broadened to include `wasm`, `node`, `a`, `o`, `so`, `dylib`, and `class`, with all pre-existing extensions retained. — appended to the existing alternation; no extensions removed.
- [x] AC-5: The pre-existing library-specific rule and every other current `[allowlist].paths` entry are still present and unmodified (no entries removed or reordered except for the inserted additions). — only insertions (binary group broadened in place; 3 rules added after line 120); `tomllib` parse confirms 31 paths.
- [x] AC-6 (regression/test): A test extends `TestShippedFrameworkSelfExclusions`-style coverage asserting that representative paths — e.g. `app.min.js`, `vendor/foo.min.css`, `dist/bundle.min.js.map`, `src/index.js.map`, `styles.css.map`, `__snapshots__/Component.test.js.snap`, `lib/native.wasm`, `build/addon.node`, `obj/main.o`, `libfoo.so`, `Foo.class` — are excluded by the shipped default allowlist, and that a plain `config.js` source file is NOT excluded. — `test_generated_artifacts_excluded_by_default` + `test_normal_source_not_excluded`.
- [x] AC-7: The full framework test suite (`python3 .wavefoundry/framework/scripts/run_tests.py`) passes, and `scan-rules.toml` still loads/parses without error in the scanner. — toml parses (31 paths); full suite re-confirmed at wave-end.

## Tasks

- [x] In `.wavefoundry/framework/scan-rules.toml`, broaden the binary-extension entry at line 109 to add `wasm|node|a|o|so|dylib|class`.
- [x] After the library-specific minified rule at line 120, insert the three new triple-quoted path rules (generic `*.min.{js,css}(.map)`, generic `*.{js,css,mjs,cjs}.map`, `*.snap`).
- [x] Add/extend a `TestShippedFrameworkSelfExclusions`-style test in the scanner test suite asserting the representative artifact paths from AC-6 are allowlisted and that a normal source file is not.
- [x] Add a defense-in-depth note (in this change's Decision Log / commit message) clarifying the relationship to the 1p44s engine guards. — TOML comment on the inserted block + existing Decision Log row.
- [x] Run `python3 .wavefoundry/framework/scripts/run_tests.py` and `.wavefoundry/bin/docs-lint`; fix any failures. — scanner suites green; full suite + docs-lint at wave-end.

## Agent Execution Graph


| Workstream            | Owner       | Depends On  | Notes                                                                 |
| --------------------- | ----------- | ----------- | --------------------------------------------------------------------- |
| toml-allowlist-edit   | Engineering | —           | Add 3 generic rules after line 120; broaden binary group at line 109. |
| scanner-test-coverage | Engineering | toml-allowlist-edit | Extend `TestShippedFrameworkSelfExclusions`-style coverage. |
| verification          | Engineering | scanner-test-coverage | Run framework tests + docs-lint; confirm toml parses.       |


## Serialization Points

- `.wavefoundry/framework/scan-rules.toml` — shared with waves 1p44u, 1p44w, and 1p452; coordinate edits to `[allowlist].paths` to avoid conflicting concurrent modifications to this file.

## Affected Architecture Docs

N/A — change is confined to a single framework config file (`scan-rules.toml`) and its scanner test suite; it adds default allowlist patterns and test coverage with no module-boundary, control-flow, or verification-architecture impact.

## AC Priority


| AC   | Priority   | Rationale                                                                                          |
| ---- | ---------- | -------------------------------------------------------------------------------------------------- |
| AC-1 | required   | Generic minified rule is the core gap the change closes.                                           |
| AC-2 | required   | Generic source-map rule is a core gap; library-specific rule misses most maps.                     |
| AC-3 | important  | Jest snapshots are a common generated artifact but narrower in impact than min/map.                |
| AC-4 | important  | Broadened binary extensions close compiled-module exposure (wasm/node/so/etc.).                    |
| AC-5 | required   | Non-regression of existing allowlist coverage; removing/reordering entries would regress scanning. |
| AC-6 | required   | Test lock-in proving the defaults exclude representative artifacts and not real source.            |
| AC-7 | required   | Suite + parse pass is the gate that the toml edit is valid and nothing else broke.                 |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-08 | Added 3 generic generated-artifact path rules (min.js/css(.map), js/css/mjs/cjs.map, .snap) after the library rule; broadened the binary-extension group with wasm/node/a/o/so/dylib/class. | `scan-rules.toml` `[allowlist].paths` (now 31 entries, parses); `test_generated_artifacts_excluded_by_default` + `test_normal_source_not_excluded` green. |


## Decision Log


| Date       | Decision                                                                                                  | Reason                                                                                                                         | Alternatives                                                                                                       |
| ---------- | --------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| 2026-06-08 | Add generic name-agnostic min/map/snap path rules rather than extend the hardcoded library list at line 120. | Library-specific list never covers project-own or non-listed minified bundles; generic patterns close the gap cheaply pre-read. | Keep extending the `angular|bootstrap|...` alternation — rejected: unbounded maintenance, still misses unknown names. |
| 2026-06-08 | Scope this change to path-allowlist defaults only; engine line/size/NUL guards stay with 1p44s.            | Defense-in-depth layering — path allowlist short-circuits known artifacts; engine guards protect unexpectedly-named giant/binary files. | Fold both into one wave — rejected: separates cheap path-prefilter defaults from the engine-guard contract.        |


## Risks


| Risk                                                                                              | Mitigation                                                                                                          |
| ------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| An overly broad generic rule allowlists a real secret-bearing file (e.g. a misnamed `.map`).      | Anchor patterns to specific artifact extensions/suffixes; AC-6 includes a negative case (`config.js` not excluded). |
| Concurrent edits to `scan-rules.toml` by waves 1p44u/1p44w/1p452 cause merge conflicts.           | Serialization Point coordination; keep additions to a contiguous block after line 120 to minimize conflict surface. |
| Treating these defaults as a substitute for the 1p44s engine guards leaves giant/binary files exposed. | Decision Log + change note record that this is defense-in-depth only; engine guards remain required.               |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
