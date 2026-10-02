# Declared Extra Change Kinds

Change ID: `1zimp-enh declared-extra-change-kinds`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-10-01
Wave: 1zimf extension-seams

## Rationale

The change-kind token in a change id (`<prefix>-<kind> <slug>`) is fixed in three separate literals: `CHANGE_KIND_PATTERN` in `wave_lint_lib/constants.py` (from which `CHANGE_ID_PATTERN` is built), `VALID_CHANGE_KINDS` in `wf_server/server_impl.py`, and the `--kind` choices of the `lifecycle_id.py` CLI. A downstream distribution that records decisions as their own kind cannot mint or lint a `decision` change, so it stores them as `change` and loses the kind. Today an undeclared kind is reported misleadingly: in a plan file as "plan is missing a `Change ID:` ... identifier line", and in a wave record as "unstable `Change ID`".

The vocabulary profile (`vocabulary_profile.py`, wave `1z8mm`) is the model for a distribution-edited, import-validated, fail-closed declaration of record grammar, and the kind token is record grammar. Declaring extra kinds there, and deriving all three literals from one source, removes the restriction without new configuration.

## Requirements

1. **One source of kinds.** `vocabulary_profile.py` gains:
   - `CORE_CHANGE_KINDS = ("bug", "feat", "enh", "change", "doc", "debt", "ref", "task", "maint", "ops")`, fixed (not distribution-edited), in today's order;
   - `EXTRA_CHANGE_KINDS: tuple[str, ...] = ()`, distribution-edited, written on one line like the other constants;
   - derived `CHANGE_KINDS = CORE_CHANGE_KINDS + EXTRA_CHANGE_KINDS` and `CHANGE_KIND_RE`, a non-capturing alternation of the escaped kinds (a fragment, as the module's other exports are).
2. **Validation (in `validation_errors`, so it fails closed at import with `VocabularyProfileInvalid`).** `EXTRA_CHANGE_KINDS` must be a tuple of strings; each must match `^[a-z][a-z0-9]{1,15}$` (lowercase ASCII, no `-`, no space, 2 to 16 characters); none may equal a core kind; none may repeat; none may be a reserved non-change token: `wave` (lifecycle-id CLI kind), `mem` (memory ids), `sec` (scanner finding ids), `adr` (decision records) or `jrnl` (migrated journal files the upgrade writes into wave folders). The whole token must match: a trailing newline is refused. `ARCHIVE_PROFILE` is unchanged: it stays exactly the twelve `FIELD_NAMES`, and kinds apply to live and archived records alike.
3. **Consumers derive.** `CHANGE_KIND_PATTERN` in `wave_lint_lib/constants.py` becomes `_vocab.CHANGE_KIND_RE`, so `CHANGE_ID_PATTERN`, `CHANGE_REFERENCE_PATTERN` and the decision-log source-event exemption in `wave_validators.py` accept declared kinds; `VALID_CHANGE_KINDS` becomes `frozenset(_vocab.CHANGE_KINDS)`; the `lifecycle_id.py` CLI `--kind` choices become `_vocab.CHANGE_KINDS + ("wave",)`. No kind literal list remains in non-test framework code (`.py` files under `.wavefoundry/framework/scripts/` and `.wavefoundry/framework/dashboard/*.js`) outside `vocabulary_profile.py`, the per-kind `wf_new_<kind>` registrations, the legacy lane-trigger tokens in `review_policy.py` and the reserved `-sec` and `-mem` id patterns; a census test pins that. Seeds and framework docs are documentation sites, dispositioned in the census and not scanned by the test.
4. **Undeclared kinds lint by name.** When a member-id line has the change-id shape (`<prefix>-<token> <slug>` with a lowercase token) but the token is not a declared kind, docs-lint reports `uses undeclared change kind '<token>'`, naming the declared kinds and `vocabulary_profile.EXTRA_CHANGE_KINDS`, in place of the "missing identifier line" and "unstable" messages for that line. It remains an error. Any other malformed id keeps today's messages.
5. **`wf_new_change` keeps `kind=change`.** No core `wf_new_*` tool gains a `kind` parameter and no core tool is added per extra kind. Instead `server_impl.change_doc_response(root, kind, slug, *, cache=None)` is added to `EXTENSION_PUBLIC_HELPERS` (change `1zimn-enh extension-public-helpers`): it creates the change doc exactly as `wf_new_<kind>` does (lifecycle id, template, index refresh, attached lint) for any kind in `CHANGE_KINDS`, and refuses any other kind with `invalid_arguments`. A distribution serves its kind through its own write-tier extension tool calling it, and declares that tool's `path` field in `EXTENSION_ARTIFACT_PATH_FIELDS` (change `1zimo-enh extension-lifecycle-tools-and-artifact-credit`) for the same credit core creation tools get. The CLI fallback `wf lifecycle-id --kind <kind>` accepts declared kinds. Adding `change_doc_response` updates the `EXTENSION_PUBLIC_HELPERS` pin from change `1zimn-enh extension-public-helpers` (its AC-3) to four names, with this signature.
6. **Kind census (recorded in the Progress Log).** Predicate: every non-test file under `.wavefoundry/framework/` (scripts, `wave_lint_lib`, `wf_server`, dashboard assets, seeds, install and framework docs) that names a change-kind token as a literal, builds a pattern from one, or parses a change id from a record line. Each entry is dispositioned as kind-dependent (changed here) or kind-agnostic (unchanged, with a test where the brief named it).
7. **Profile coverage.** `SHIPPED_DEFAULTS["vocabulary_profile"]` in `tests/record_layout_support.py` (and so `_EDITABLE`) gains `"EXTRA_CHANGE_KINDS": ()`; `_SHIPPED_VOCABULARY` and `_Vocabulary` stay the twelve `FIELD_NAMES`. `expected_profile_mismatch` compares loaded and expected values in JSON form (tuples as lists), as `declaration_profile_mismatch` already does, so a loaded `("decision",)` matches the asset's `["decision"]`. `test_snapshot_covers_every_editable_constant` pins `SHIPPED_DEFAULTS["vocabulary_profile"]` to `FIELD_NAMES | {"ARCHIVE_PROFILE", "EXTRA_CHANGE_KINDS"}`, and `SHIPPED_VOCABULARY` in `test_profile_support.py` excludes `EXTRA_CHANGE_KINDS` as well as `ARCHIVE_PROFILE`. The `second.json` asset sets `"EXTRA_CHANGE_KINDS": ["decision"]`; the whole suite passes under `run_tests.py --profile second` with a planted `decision` change doc linting clean in a named test, and the expected-profile guards (wave `1zimb`) cover the new constant. The tests for AC-1 and AC-4 build a scratch tree with `EXTRA_CHANGE_KINDS = ()`, so they hold under `--profile second`.
8. **Docs.** `docs/architecture/layering-rules.md` (vocabulary profile paragraph) states that the profile owns the change kinds and the validation rules; seed `170-plan-feature` keeps its core kind list and adds one sentence that a distribution may declare more in `vocabulary_profile.EXTRA_CHANGE_KINDS`; `docs/specs/mcp-tool-surface.md` documents `change_doc_response` and that `wf_new_change` stays `kind=change`; one `### Added` entry in `## [Unreleased]`.
9. **Platforms.** Windows, macOS, Linux and WSL2 behave the same. Kinds are lowercase ASCII, so a change doc file name cannot differ only by case on a case-insensitive file system (Windows, macOS default); the 16-character cap adds at most 10 characters to a change doc path, which stays inside the path budget the slug already uses.
10. **Transition.** With the shipped empty `EXTRA_CHANGE_KINDS`, every pattern matches exactly what it matches today, and lint output for valid documents is unchanged. Kinds are additive: removing a declared kind that existing records use makes those records fail lint by name.

## Scope

**Problem statement:** change kinds are fixed in three literals, so a distribution's own kind is stored as `change`, and an undeclared kind lints with a misleading message.

**In scope:**

- `vocabulary_profile.py` constants and validation; `wave_lint_lib/constants.py`, `wave_lint_lib/wave_validators.py` (undeclared-kind message), `wf_server/server_impl.py` (`VALID_CHANGE_KINDS`, `change_doc_response`), `lifecycle_id.py` CLI choices.
- Tests: profile validation, consumers, the undeclared-kind message, the census, `change_doc_response`, the `second.json` asset and its support tables.
- The docs in Requirement 8.

**Out of scope:**

- A `kind` parameter on `wf_new_change` or new core `wf_new_*` tools (Requirement 5).
- Review-lane triggers for extra kinds: the legacy whole-document kind tokens in `review_policy.py` stay core-only; declared Serialization Points are the routing path.
- Kinds per archive vocabulary, and renaming core kinds.

## Acceptance Criteria

- [x] AC-1: with `EXTRA_CHANGE_KINDS = ()`, `CHANGE_KINDS == CORE_CHANGE_KINDS`, `VALID_CHANGE_KINDS`, `CHANGE_KIND_PATTERN` and the CLI choices equal today's sets, and a test asserts the default `CHANGE_ID_PATTERN` accepts and rejects exactly what the frozen pre-change pattern does on a fixed corpus.
- [x] AC-2: `validation_errors` refuses, each with a message naming `EXTRA_CHANGE_KINDS`: a non-tuple, a non-string, an uppercase, hyphenated, spaced, one-character or 17-character token, a core kind, a duplicate, and each of `wave`, `mem`, `sec`, `adr`; importing a module with such a value raises `VocabularyProfileInvalid`.
- [x] AC-3: in a scratch tree with `EXTRA_CHANGE_KINDS = ("decision",)`, a plan `docs/plans/<prefix>-decision <slug>.md` and a wave record listing it lint clean, the decision-log source-event exemption accepts `decision-log:<prefix>-decision <slug>:<hash>`, `wf lifecycle-id --kind decision` mints an id, and `change_doc_response(root, "decision", slug)` creates the doc and returns the `wf_new_<kind>` envelope.
- [x] AC-4: with the shipped declaration, a change doc and a wave record using `<prefix>-decision <slug>` fail lint with `uses undeclared change kind 'decision'`, naming the declared kinds; `change_doc_response` with an undeclared kind returns `invalid_arguments`; a malformed id that is not change-id shaped keeps today's message.
- [x] AC-5: the census test fails when a kind literal list or kind alternation appears in a non-test `.py` file under `.wavefoundry/framework/scripts/` or in `.wavefoundry/framework/dashboard/*.js`, outside the allowed sites in Requirement 3, and the Progress Log records the census with its predicate, including the documentation sites (seeds `001`, `110` and `170`).
- [x] AC-6: the whole suite passes under `run_tests.py --profile second` with `second.json` declaring `["decision"]`, and under the default and `--profile declared` runs.
- [x] AC-7: layering-rules, seed `170-plan-feature`, the tool-surface spec and the CHANGELOG describe the declaration, the rules and the creation path.
- [x] AC-8: the change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Add `CORE_CHANGE_KINDS`, `EXTRA_CHANGE_KINDS`, `CHANGE_KINDS`, `CHANGE_KIND_RE` and their validation to `vocabulary_profile.py`.
- [x] Derive `CHANGE_KIND_PATTERN`, `VALID_CHANGE_KINDS` and the CLI choices from the profile.
- [x] Add the undeclared-kind lint message.
- [x] Add `change_doc_response` to the public helpers.
- [x] Add `EXTRA_CHANGE_KINDS` to the profile support tables and `second.json`.
- [x] Census test and the tests for AC-1 to AC-6.
- [x] Docs, seed sentence and CHANGELOG entry.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Profile constants and consumers | implementer | readiness | profile, lint constants, server, CLI |
| Lint message and creation helper | implementer | profile constants, change `1zimn-enh extension-public-helpers` | `wave_validators`, `server_impl` |
| Profile asset and census | implementer | profile constants | test support and `second.json` |
| Docs | implementer | implementation | seed edit needs the `seed_edit_allowed` gate |
| Review | code-reviewer, qa-reviewer, security-reviewer, architecture-reviewer | implementation | |

## Serialization Points

- `.wavefoundry/framework/scripts/vocabulary_profile.py`, `.wavefoundry/framework/scripts/lifecycle_id.py`
- `.wavefoundry/framework/scripts/wave_lint_lib/constants.py`, `.wavefoundry/framework/scripts/wave_lint_lib/wave_validators.py`
- `.wavefoundry/framework/scripts/wf_server/server_impl.py`
- `.wavefoundry/framework/scripts/tests/record_layout_support.py`, `.wavefoundry/framework/scripts/tests/fixtures/profiles/second.json`
- `.wavefoundry/framework/scripts/tests/test_profile_support.py`
- `.wavefoundry/framework/seeds/170-plan-feature.prompt.md`
- `docs/architecture/layering-rules.md`, `docs/specs/mcp-tool-surface.md`

## Affected Architecture Docs

`docs/architecture/layering-rules.md` (vocabulary profile paragraph: the profile owns the change kinds). `docs/architecture/testing-architecture.md` only if its profile section lists the second profile's constants.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The default must be byte-for-byte today's grammar |
| AC-2 | required | A bad declaration must fail closed |
| AC-3 | required | A declared kind must work end to end |
| AC-4 | required | An undeclared kind must be named, not misreported |
| AC-5 | required | One source of kinds must stay one source |
| AC-6 | required | The suite must hold with an extra kind declared |
| AC-7 | required | Distributions need the contract documented |
| AC-8 | required | Standard verification |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-02 | Delivery review repair (red-team, QA and docs, non-blocking). The kind check uses `fullmatch`, so a trailing newline is refused (`$` matched before it); `jrnl` joins `RESERVED_KIND_TOKENS` because the upgrade writes `<prefix>-jrnl <slug>.md` into wave folders; a wave record member `00059-Feat fixture` (uppercase kind, valid slug) keeps the unstable-id message; the CHANGELOG 1zimn bullet no longer says `change_doc_response` returns exactly what its private counterpart returns. The import test now substitutes through a function so a repr's escape is not expanded. Follow-up, not 1zimf: a member line that fails the id pattern attaches its `Depends On:` to the previous record, so lint also reports a self-dependency. | `ExtraKindValidationTests` (`jrnl`, trailing newline cases), `UndeclaredKindTests`; match and `jrnl` mutations killed in a scratch copy |
| 2026-10-01 | Implemented. `vocabulary_profile` gains `CORE_CHANGE_KINDS`, `EXTRA_CHANGE_KINDS` (one line), derived `CHANGE_KINDS` and `CHANGE_KIND_RE`, `RESERVED_KIND_TOKENS` and `change_kind_errors` inside `validation_errors` (live profile only; non-tuple and non-string values reported, failing closed at import). `CHANGE_KIND_PATTERN`, `VALID_CHANGE_KINDS` (now a frozenset) and `lifecycle_id.KIND_CHOICES` derive from it; docs-lint names `uses undeclared change kind '<kind>'` for change-id-shaped member-id lines in plans and wave artifacts; `server_impl.change_doc_response` joins `EXTENSION_PUBLIC_HELPERS`. Test support: `SHIPPED_DEFAULTS` gains `EXTRA_CHANGE_KINDS`, `expected_profile_mismatch` compares in JSON form, the snapshot pin and `SHIPPED_VOCABULARY` updated, `second.json` declares `["decision"]`. Seed 170 gains the one sentence. Census (AC-5) as a test: `tests/test_change_kinds.py` scans non-test `.py` under `scripts/` and `dashboard/*.js` for a tuple, list or set of three or more core kinds or a kind alternation; before the change it found `lifecycle_id.py:614`, `wave_lint_lib/constants.py:294` and `wf_server/server_impl.py:670`, after it only `vocabulary_profile.py`; seeds `001`, `110` and `170` are documentation sites, not scanned. Tests failed first, then passed: AC-1 `DefaultGrammarTests` and AC-4 `UndeclaredKindTests` in a scratch tree with `EXTRA_CHANGE_KINDS = ()`; AC-2 `ExtraKindValidationTests`; AC-3 `DeclaredKindTests` in a scratch tree with `("decision",)`; AC-5 `KindCensusTests`; Requirement 7 `LoadedProfileDecisionKindTests` and `test_profile_support` (`test_tuple_constants_match_their_json_form`). Verification: full suite (`run_tests.py --no-cache`) in a scratch copy, 10,567 tests in 153 files OK (34 skipped); `--profile second` 10,564 OK and `--profile declared` 10,567 OK; 16 mutations of the new guards, all killed. | `vocabulary_profile.py`, `wave_lint_lib/constants.py`, `wave_lint_lib/wave_validators.py`, `wf_server/server_impl.py`, `lifecycle_id.py`, `tests/test_change_kinds.py`, `tests/record_layout_support.py`, `tests/test_profile_support.py`, `tests/fixtures/profiles/second.json`, `seeds/170-plan-feature.prompt.md`, `docs/architecture/layering-rules.md`, `docs/architecture/testing-architecture.md`, `docs/specs/mcp-tool-surface.md`, `CHANGELOG.md` |
| 2026-10-01 | Kind census, predicate as in Requirement 6, from keyword searches for `CHANGE_KIND_PATTERN`, `CHANGE_ID_PATTERN`, `VALID_CHANGE_KINDS`, the kind literals and the member-id label readers. Kind-dependent: `wave_lint_lib/constants.py` `CHANGE_KIND_PATTERN` (feeds `CHANGE_ID_PATTERN`, `CHANGE_REFERENCE_PATTERN`, and in `wave_validators.py` the change-record parser, plan filename check, unstable-id check and wave-owned-doc check); `wave_validators.py` `_DECISION_LOG_SOURCE_EVENT_RE` (memory forbidden-content exemption for the `decision-log:<change id>:<hash>` events `memory_supply` writes for any change id); `server_impl.VALID_CHANGE_KINDS` (only `change_create`, behind the ten `wf_new_<kind>` tools); `lifecycle_id.py` CLI `--kind` choices; seed 170 kind lists (two lines) and the `wf_new_change` docstring. Kind-specific by design, unchanged: `review_policy.py` legacy lane tokens (`-feat `, `-enh `, `-bug `, and `-refactor `, which is not a kind); `_SEC_ID_RE` and the memory id pattern (reserved tokens). Kind-agnostic, unchanged: `lifecycle_gate_support._CHANGE_ID_PATTERN` (any backticked value; used by `server_impl` and `dashboard_lib.parse_change_doc`), `memory_supply._admitted_change_re_for`, `commit_provenance._CHANGE_ID_RE`, the lifecycle prefix regexes in `review_evidence`, `lifecycle_id` and `server_impl`, `lifecycle_id.build_id` (no kind check), `dashboard.js` `renderChangeIdParts` (splits on `-`). The indexer, chunker, tag utilities and graph modules name no change kind (their `kind` is a chunk or node kind). Documentation sites, unchanged apart from seed 170: seed `001-feature-wave-framework-overview.md` (line 38) and seed `110-wave-memory-bootstrap.prompt.md` (line 72) list the core kinds and are kept, since they describe the core set; the `wf_new_<kind>` row of `docs/specs/mcp-tool-surface.md` is kept and Requirement 8 adds `change_doc_response` beside it | `wave_lint_lib/constants.py`, `wave_lint_lib/wave_validators.py`, `wf_server/server_impl.py`, `lifecycle_id.py`, `review_policy.py`, `lifecycle_gate_support.py`, `memory_supply.py`, `commit_provenance.py`, `dashboard_lib.py`, `dashboard/dashboard.js` |
| 2026-10-01 | Planned from the downstream request. Verified: an undeclared kind in a plan file reports the missing-identifier message, and in a wave record the unstable-id message; `wf_new_change` takes only `slug` and passes `kind="change"`; `vocabulary_profile` imports only `re` and validates at import; `apply_profile` keeps a tuple constant's type | `wave_lint_lib/wave_validators.py`, `wf_server/server_impl.py`, `vocabulary_profile.py`, `tests/record_layout_support.py` |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-01 | Declare extra kinds in `vocabulary_profile.py`, with the core kinds moved there as the single source | The kind token is record grammar; the profile is the distribution-edited, import-validated, fail-closed home for record grammar, is already imported by lint constants and the server, and is covered by the test profile assets | `mcp_tool_extensions.py` (a tool declaration that lint does not import); `docs/workflow-config.json` (per-repository configuration, which the profile deliberately avoids, and lint would read the kinds at run time) |
| 2026-10-01 | Token rule `^[a-z][a-z0-9]{1,15}$`, no core kind, no duplicate, not `wave`, `mem`, `sec` or `adr` | Lowercase only avoids case-only file-name collisions on Windows and macOS; no `-` or space keeps the prefix, kind and slug split unambiguous; the reserved tokens already name other lifecycle ids | Allow hyphens; no reserved list |
| 2026-10-01 | An undeclared kind is a named lint error | The current messages point the author at the wrong fix; leaving it an error keeps a typo from becoming a silent new kind | Advisory warning |
| 2026-10-01 | `wf_new_change` does not accept extra kinds; a public `change_doc_response` serves distribution tools | A new core `kind` parameter changes the `wf_new_change` schema, which would make an existing distribution override of it fail call-compatibility (`drops parameters`); per-kind tools keep per-kind guidance; a distribution tool plus the 1zimo artifact field gives the same creation path and credit | Optional `kind` parameter on `wf_new_change` limited to extra kinds |
| 2026-10-01 | Extra kinds do not recruit review lanes by kind token | The legacy kind tokens apply only to documents without declared targets; declared Serialization Points are the routing path | Map each extra kind to a lane |

## Risks

| Risk | Mitigation |
| --- | --- |
| A distribution removes a kind its records use | Requirement 10 makes kinds additive and the lint names the undeclared kind |
| A kind literal reappears outside the profile | The census test in AC-5 |
| A later core release adds a kind a distribution already declared | Validation refuses the collision at import, naming the kind; the distribution drops its declaration at merge, and its records keep linting because the kind is now core |
| The new constant drifts from the expected-profile guards | Requirement 7 adds it to the support tables the guards compare |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
