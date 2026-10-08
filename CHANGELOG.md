# Changelog

All notable changes to this project are documented in this file and in
the individual wave records under [`docs/waves/`](docs/waves/).

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **A distribution can declare its own skills.** `mcp_tool_extensions.EXTENSION_SKILLS`, `{name: {"title": text, "description": text, "prompt_doc": "docs/prompts/<name>.prompt.md", "summary": [line, ...]}}`, renders each entry as a thin-pointer `SKILL.md` on every active skill host (`.codex/skills/`, `.claude/skills/`, `.agents/skills/`) after the framework's skills, only where its prompt doc exists, so a distribution no longer edits the framework renderer to give its prompt docs a skill. Names are lower-case kebab-case, at most 64 characters, never `wf-` (which the framework's skills keep) and never containing `claude` or `anthropic`; titles, descriptions and summary lines must be single-line YAML-safe text; `prompt_doc` is a POSIX path under `docs/prompts/` ending in `.prompt.md` on every platform. `mcp_tool_extensions.skill_declaration_problems()` reports every problem, and an invalid declaration refuses the whole surface render before anything is written. The declaration is read only by the renderer and never stops the MCP server: `wf_server_info` lists the declared names under `extensions.skills`, with `skill_problems` when any are found. Each rendered declared skill carries a `<!-- wavefoundry:declared-skill -->` marker as its first body line, so the renderer never overwrites a hand-written `SKILL.md` that shares a declared name (it skips that skill on that host and prints a `NOTICE` naming the path and the remedy) and removes the marked folder of a skill the distribution stops declaring, without following a linked folder and leaving a folder with extra files in place. A skill rendered before the marker is adopted when its bytes are unchanged. The optional `prompt_doc_template`, a path under the framework `install/` directory, creates a missing prompt doc from a shipped template and never overwrites one or writes through a link at its path. The shipped declaration is empty and changes nothing. Requested by the Waveforge maintainers. Waves 1zv8c / 1zv89 and 1zyb3 / 1zxnu.
- An offline check for the vendored dashboard scripts. `verify_vendored_scripts.py --offline` hashes each file under `dashboard/vendor/` and compares it with the SHA-256 recorded in the vendor README, with no network request. It exits 0 when every file matches, 1 when a file differs or is missing (each is named), and 2 when the README cannot be parsed. The default test suite runs the same comparison and also fails when a `.js`, `.mjs` or `.cjs` file under `dashboard/vendor/` is not listed in the file table, and `build_pack` runs it before writing a pack and refuses to build on any mismatch, naming the file. Requested by the Waveforge maintainers. Wave 1zv8c / 1zv8a.
- **A distribution can teach the journal migration its own scaffolds.** `mcp_tool_extensions.EXTENSION_JOURNAL_TEMPLATES` lists extra pristine journal scaffolds using the placeholders `{{wave_id}}`, `{{title}}` and `{{date}}`; on an upgrade from a release before 1.15.0, a journal that fully matches one (CRLF read as LF, each placeholder one line fragment of at most 512 characters, every occurrence of a placeholder the same text) is deleted like the built-in scaffold, and the preview `migrate_journals(root, apply=False)` reports it under `deleted`. `EXTENSION_JOURNAL_PRE_MIGRATION_HOOK`, `"module:function"` in a declared helper module, is called once with the repository root right before the migration applies. `mcp_tool_extensions.journal_declaration_problems()` reports every problem; an invalid declaration, or a hook that cannot be loaded, refuses that upgrade before any pre-1.15.0 migration changes anything, and a hook that raises skips the migration with a warning naming the hook and the exception class only. Both are read only by the upgrade, never stop the MCP server, and ship empty, which changes nothing. Requested by the Waveforge maintainers. Wave 1zyb3 / 1zxnv.
- `upgrade_extensions.migrate_journals(root, apply=False)` previews or performs the journal migration on demand. It now follows the record vocabulary profile's id key (and the legacy `wave-id`), finds nested waves, and leaves in place a journal whose wave is archived (the archive is read-only) or whose id is ambiguous. Requested by the Waveforge maintainers. Wave 1zv87 / 1zuq6.
- **An extension alias can rename and pin parameters.** The extension declaration gains `EXTENSION_TOOL_PARAMETERS`, `{alias: {"rename": {alias_param: canonical_param}, "fixed": {canonical_param: value}, "description": text}}`, so a distribution with its own vocabulary can serve, for example, `wf_add_wave(set_id, wave_id)` for `wf_add_change(wave_id, change_id)`, or a tool with `phase="prepare"` pinned. The alias's schema is the canonical schema with fields renamed and fixed ones removed; a call is translated in one pass into the canonical tool as served, so the lifecycle lock, the upgrade publication guard, cost accounting and the permission tier stay keyed on the canonical name and apply once. Any argument outside the alias's parameters is refused with `unknown_arguments`, naming the alias's parameters, and is never forwarded. Fixed values are validated strictly at startup and the validated value is forwarded. Response hints name a pinned alias only in a call whose pinned values match, name the preferred unpinned alias in prose and list hints, and never give an alias name canonical parameter names; tool descriptions are the canonical ones unless the entry declares `description`. That optional key (a string, non-blank, at most 16,384 characters, only on an entry that renames or pins) becomes the alias's listed description; a framework without it refuses the key, so a distribution that declares it needs this release or later. A call through a mapped alias returns the top-level `data` keys that echo its renamed parameters under the alias's names, values unchanged; nested `data`, diagnostic messages and pinned parameters keep canonical names, and a rename that would duplicate a key leaves `data` as it is. `wf_server_info` lists the mappings, with any declared description, under `extensions.parameters`. An override can now delegate to the core tool with `mcp.core_handler(name)` during `register`, without copying core internals. Invalid mappings refuse startup and leave only runner tools served; the shipped declaration is empty and changes nothing. Wave 1zim3 / 1zim0.

- **Extension handlers have public helpers.** `server_impl.EXTENSION_PUBLIC_HELPERS` names the stable surface a distribution's extension modules may rely on: `ensure_no_extra_args(tool_name, kwargs)` (the typed `unknown_arguments` envelope, or `None`), `make_response(status, data=None, *, diagnostics=None, next_tools=None, usage="")`, `make_diagnostic(code, message, *, recovery_tools=None, recovery_usage="", advisory=False)` and `change_doc_response(root, kind, slug, *, cache=None)`. The first three return exactly what their private counterparts return; `change_doc_response` also refuses a kind not in `CHANGE_KINDS` before creating the doc. Each looks its private counterpart up at call time, so it follows a reload. Removing or renaming one, or changing its signature, will be a breaking change. The loader's refusals for an override or replacement that does not reject undeclared arguments now name `server_impl.ensure_no_extra_args`. Extensions that call the underscore-prefixed helpers keep working. Wave 1zimf.
- **A distribution's own tools can take the lifecycle lock and earn artifact credit.** The extension declaration gains `EXTENSION_LIFECYCLE_TOOLS`, new write-tier extension tools that run under the lifecycle mutation lock with exactly the core wrapper (busy `lifecycle_mutation_locked` response, process-hold registry, refused re-entry), and `EXTENSION_ARTIFACT_PATH_FIELDS`, `{tool: data_field}`, which credits the repository-relative paths in that response field as derived artifacts under the core contract. Both accept only new extension tools declared `write`; core names, override and replacement targets, aliases, runner and edit-gate tools, read tools, undeclared names, duplicates and invalid fields are refused, and a wrong container type is reported, not raised. A new extension tool that writes wave lifecycle records must be declared in `EXTENSION_LIFECYCLE_TOOLS`. `wf_server_info` reports both under `extensions.declaration`; the shipped declarations are empty and change nothing. Artifact credit, core and declared, now counts each resolved file once per response, however many names reach it. Wave 1zimf.
- **A distribution can declare extra change kinds.** `vocabulary_profile.EXTRA_CHANGE_KINDS` adds change kinds such as `decision` to the core kinds, validated at import (lowercase letters and digits, 2 to 16 characters, not a core kind, not `wave`, `mem`, `sec`, `adr` or `jrnl`, no duplicates). Docs-lint, the server and `wf lifecycle-id --kind` take their kinds from `vocabulary_profile.CHANGE_KINDS`, and a change id whose kind is not declared now lints as `uses undeclared change kind '<kind>'` instead of a missing or unstable identifier. `wf_new_change` stays `kind=change`; a distribution creates its own kind through its own extension tool calling `server_impl.change_doc_response`. With the shipped empty declaration every pattern and message for valid documents is unchanged. Wave 1zimf.
- **A misplaced prepare-council verdict gets a location hint.** When Prepare or Implement reports `prepare_council_verdict_missing` and a verdict line sits under another `wave.md` heading or in an admitted change document, the advisory `prepare_council_verdict_misplaced` names where it was found and says the verdict belongs in `wave.md` under `## Review Checkpoints`. On a declared wave missing `council-readiness`, it says a prose verdict is not readiness authority and points at `wf_review_event`. It never changes a status, a blocker or the recommended next step. Wave 1zls7.
- **Opt-in online check for the vendored dashboard scripts.** `python3 .wavefoundry/framework/scripts/verify_vendored_scripts.py` downloads each recorded npm tarball from the registry only, compares it with the recorded `dist.integrity`, and compares each vendored file with its tarball member, exiting 0 on a match, 1 on a mismatch (even when another package could not be checked) and 2 when the check could not be made; a deliberate refusal (a non-registry URL, a redirect off the registry, a tarball over the size cap) is labelled `refused:`, apart from a `download failed:` line. Every redirect target is checked before it is followed, so an off-registry host is never contacted and a chain that leaves the registry is refused even if it would return; each README table is found by its exact header, and a row in either table that does not match its format, an indented row, a row missing its leading pipe, or a row after a blank line inside the table is refused (exit 2, naming the line) instead of skipped. It is development-only, outside the default offline suite and not in the distribution, and is an optional packaging step. Wave 1zls7.
- **Extensions can reach the lifecycle helpers and share hashed helper modules.** `server_impl.EXTENSION_PUBLIC_HELPERS` now lists eleven names: the four earlier helpers, five new wrappers that call their private counterparts at call time (`find_wave_record(root, wave_id_or_prefix, wave_dirs=None)`, `refuse_if_archived(root, token, kind)`, `fail_closed_on_record_layout(tool)`, `attach_lint(envelope, root, mode)` and `refresh_index_for_paths(root, paths)`), and the module-level `list_waves(root, wave_dirs=None)` and `wf_review_wave_response(root, wave_id, phase="implementation")`, so a distribution that wraps core lifecycle tools no longer reaches underscore names. Removing, renaming or re-signing a listed name is a breaking change. The extension declaration gains `EXTENSION_HELPER_MODULES`, flat helper modules that extension modules import: each is loaded before any extension module through the extension loader, executed from the bytes it hashes, reported under `wf_server_info.extensions.helper_modules` with its SHA-256, and evicted and re-executed on `wf_reload_mcp`, so an edited helper is served after a reload and a dropped one is no longer importable. A helper's `register` is never called, a helper may import only helpers declared before it, and a failed install drops what it imported so a fixed declaration reloads without a restart. Extension and helper modules may not take the name of a framework flat script, and the loader now requires a file named exactly `<name>.py`, so a mis-cased declaration is refused on every platform, including a case-insensitive volume with `PYTHONCASEOK` set. A module name must be ASCII, and a non-ASCII extension or helper module name is refused at declaration. Imports of declared helper modules are hashed and reloaded; any other import is neither. Wave 1zls8.
- **A mapped alias can answer in its own response keys.** An `EXTENSION_TOOL_PARAMETERS` entry may declare `response_keys`, `{path: new_key}`, where a path names one key of the canonical response `data` in canonical names, dot-separated, with `[]` for each element of a list (for example `{"changes": "items", "changes[].id": "item_id"}`). The renames apply after the call in one walk together with the echoed-parameter renames, change only keys (values keep their identity and the canonical result is never mutated), skip absent or wrongly typed paths, and leave an object canonical when a renamed key would duplicate one already present, adding one advisory `response_key_rename_skipped` that names each skipped path. Paths are validated when the declaration loads (at most 8 segments and 64 entries), a `description` is allowed on an alias that declares only `response_keys`, and `wf_server_info` reports the map under `extensions.parameters.<alias>.response_keys`. An entry without `response_keys` answers exactly as before; an older server refuses the new key and serves only runner tools. Wave 1zls8.

- **One change can be closed inside an open wave.** The new `wf_close_change(wave_id, change_id, mode)` tool (`dry_run`, or `create`) closes one admitted change to `complete` in both its change document and the wave record (with `Previous Change Status` in the wave record only, so review approvals do not lapse) and moves each change whose wave-record `Depends On:` names it, and whose dependencies are now all done, from `planned` or `blocked` to `ready`. It refuses, listing every reason, unless the wave is open, the change is `ready`, `active`, `review` or `implemented` in both files, its ACs and tasks are all marked and its dependencies are done; docs-lint on the written documents runs before and after, and a failure the write introduced restores every file. Docs-lint now accepts the `implemented` -> `complete` transition. Wave 1zlu1.

- **A wave can be created inside a grouping folder.** Under the nested record layout, `wf_create_wave` takes an optional `parent`, an existing folder relative to the waves root such as `q4/auth`, and creates the wave there; `data.parent` names the folder as spelled on disk. A flat layout, an empty, absolute, `..`, dot-prefixed or symlinked path, a folder inside a wave folder, one too deep to be discovered, or a missing folder is refused before a lifecycle id is used, and an id already used at another path is refused with `ambiguous_wave_id`. `wf_list_waves` reports each wave's `parent` (`null` for a direct child). A distribution override of `wf_create_wave` may omit `parent`: the server then refuses any call passing it with `unknown_arguments` before the override's handler, the lifecycle lock or cost recording runs, and `wf_server_info` lists it under `omitted_core_parameters`. Declare `parent`, with the core schema, to offer it. Wave 1zlu1.

- **A project review lane can be required at one phase only.** `docs/workflow-config.json` `phase_gates.prepare.required_lanes` and `phase_gates.close.required_lanes` name lanes required at readiness (Prepare) only or at delivery (Review and Close) only, validated as strictly as `required_sensors`; `required_review_lanes` still means both phases. Prepare reports delivery-only lanes in `delivery_only_lanes` and writes a `- Required delivery lanes:` line after `- Required review lanes:` when the two rosters differ, and every lifecycle reader takes its phase's lanes from one helper. Configs without `phase_gates` keep their review-policy digest; adopting `required_lanes` moves it, so open waves re-Prepare, as adding a required sensor does. Wave 1zlu1.

- **A stale helper reference after a reload is reported.** A module that imports a declared helper module but is not itself declared is not re-executed on `wf_reload_mcp`, so it keeps calling the old helper. The server now keeps the modules each extension install evicts until a scan at the end of the install, then releases them, also when the install fails. The scan reports every module-level global under the scripts directory, subpackages included, that still holds an evicted module or an object the old module bound under a name the new one rebinds (cached immutables such as `None`, numbers, strings and tuples, and dunder names, are not compared). `wf_server_info` lists them under `extensions.stale_helper_references`, always present and empty when nothing is stale, and adds the advisory `extension_helper_stale_reference`, which says to declare the importer as a helper or restart the host. Only module-level bindings are checked. The scan reads module namespaces and compares identities only, so it runs no module code, and a module it cannot read is skipped and named by exception class. Wave 1zoju.

- **An approval can carry the recording person's own name.** `wf_review_event` takes an optional `attested_by`, the name the person recording the event states for themselves, stored as `verification_context.attested_by` on every record the event writes. It is self-attested and unverified, recorded only when supplied (no default from `docs/contributors.json` or git), and appears in the committed ledger and `wave.md`, where the approval reads `by <name> (<handle>)` or `by <name>`; rows without a name render as before. Names that are empty, longer than 100 characters, or that contain control, format, surrogate or line-separator characters or `<`, `>`, a backtick, `|`, `[`, `]` or a backslash are refused before anything is written. The name is outside the request digest, so a replay keeps the original and an advisory notes a different supplied name. Framework versions before 1.29.0 read a ledger carrying the key as invalid. Requested by the Waveforge maintainers. Wave 1zyc3 / 1zyc1.
- **Each profile that declares tools has its own tool-surface golden.** Every test profile asset under `tests/fixtures/profiles/` whose `mcp_tool_extensions` entry declares anything, a distribution's own asset included, now has a committed golden at `tests/fixtures/tool-surface-golden/<profile>.json` of the tool surface served under that declaration alone (aliases with their tiers, renamed and pinned parameters, hidden names, extension tools and overrides). The default suite compares each one with the live surface and fails with a per-tool diff; `WF_UPDATE_TOOL_SURFACE_GOLDEN=1` regenerates them with the shipped golden, and now rewrites a golden only when its content changes. A declaring asset without a golden fails naming the file and the flag, and an invalid declaration fails with its problems. The shipped golden and its test are unchanged. Requested by the Waveforge maintainers. Wave 1zyc3 / 1zyc2.

- **A distribution can rename the tier-named lifecycle prompts.** `vocabulary_profile.PROMPT_NAME_OVERRIDES` maps any of the eleven lifecycle prompts (`plan-change`, `create-wave`, `add-change-to-wave`, `remove-change-from-wave`, `prepare-wave`, `implement-wave`, `implement-change`, `pause-wave`, `review-wave`, `close-wave`, `close-change`) to a new slug, shortcut and aliases, and every consumer reads the result: prompt paths, agent bodies, skill names and their descriptions, materialized lifecycle baselines (heading and `Shortcut:` line only), the review-policy carriers and their region texts, docs-lint's required prompt files and the reconcile scan's suggestions. A chain, such as the item prompt taking the file name the container prompt gives up, is valid; the profile refuses unknown keys, malformed or fixed slugs, colliding names and rename cycles at import. The renderer moves already-rendered prompts and their agent bodies byte-for-byte to the new names before skills and baselines render, records the names it applied under a new `prompt_names` object in `docs/prompts/prompt-surface-manifest.json` key by key (so a rerun after an interruption converges), refuses and writes nothing when a target already holds other content, and reports links to moved prompts as `file:line`. docs-lint reports a pending migration while `prompt_names` differs from the profile. With the shipped empty override nothing changes: every name, rendered file and manifest stays as before. Wave 1zyb4 / 1zxnw.
- **A Linux-only test checks that record locks are open file description locks.** A host-independent probe checks the test's own assertions on every platform, so the Linux run cannot pass vacuously. Wave 200xy / 200v2.

### Changed

- **The test suite can run under a second vocabulary and layout profile, and a distribution's suite skips only tests marked default-profile-only.** `run_tests.py --profile second` copies the tracked and untracked tree into a temporary git repository, applies the profile asset under `tests/fixtures/profiles/`, and runs the suite there without touching the framework test receipt; its result is not delivery evidence. Tests take record paths, file names and labels from `record_paths`, `vocabulary_profile` or the shared fixture builders, and a test whose subject is the default profile carries a `default_profile_only` marker with a reason, so a distribution that renames its records runs the same suite. A distribution marks its own profile asset `"active": true` so its default run checks exactly that profile; `--profile NAME` layers the named asset over it through `WAVEFOUNDRY_TEST_PROFILE`, and a receipt-writing run refuses while that variable is set. Wave 1zim5 / 1zim1, 1zim6.

- **Lifecycle responses name the real next step when readiness or closure is blocked.** A blocked `wf_prepare_wave`, `wf_review_wave` or `wf_close_wave` envelope takes its `usage` and `next_tools` from the first blocking diagnostic's recovery instead of always recommending `wf_validate_docs()`; on a declared wave a missing `council-readiness` approval or readiness lane recovers to `wf_review_wave(phase='prepare')` and `wf_review_event`, a failing readiness review no longer recommends `wf_implement_wave`, and a readiness block keeps the caller's mode. Prepare reports `data.pending_readiness_lanes`, words a first readiness pass apart from a lapsed approval, and adds the advisory `wave_objective_unpopulated` while the wave's `## Objective` is still the scaffold placeholder. On a declared wave the council brief now says to record the verdict as the typed `council-readiness` approval through `wf_review_event`, not as a `## Review Checkpoints` line. No gate outcome changes. Wave 1zime.

- **The `feat` change kind is retired for new change docs.** A change doc is one scoped change, so a large feature is now planned as several changes (usually `enh`), possibly across waves. `wf_new_feature` stays registered but returns a `change_kind_retired` error naming `wf_new_enhancement` and writes nothing; `wf lifecycle-id --kind feat` exits 2 with the same message. The extension helper `change_doc_response(root, "feat", slug)` now returns `change_kind_retired` instead of creating the doc. Existing `feat` ids in plans, change docs, wave records and archives stay valid and lint unchanged. `wf_help` and `wf_list_plans` now recommend `wf_new_enhancement`. An upgrade does not rewrite a consuming repository's Plan feature prompts: drop the `feat` row from `docs/prompts/plan-feature.prompt.md` and `docs/prompts/agents/plan-feature.prompt.md` by hand. Wave 1zli8.

- **`wf setup` installs dependencies only through uv.** The plain-pip fallback, which installed dependencies without the 21-day package-age guard when no uv existed and the pinned uv bootstrap failed, is removed. When uv cannot be found or bootstrapped, setup installs nothing and stops with exit code 2 (the upgrade reports a dependency failure and skips the steps that need them), with guidance: rerun `wf setup` (`.\.wavefoundry\bin\wf.cmd setup` on Windows) once network, proxy or TLS access to the package index works, which retries the hash-verified bootstrap (a mirror must be configured both in pip's settings, for the bootstrap, and in `UV_INDEX_URL`, for the dependency install), or install uv through one of its official methods (the standalone installer, an OS package manager or `pipx install uv`) so it is on `PATH`. Do not install the dependencies with pip by hand, which bypasses the guard. An existing uv of any version, operator index settings and the hash-pinned bootstrap are unchanged. Wave 1zls6.

- **Tests that patch a module the server evicts on reload now patch the module in use, and the core lifecycle tool schemas are compared in full.** The eight-tool schema golden compares types, defaults, titles and the required set, allowing only extra optional parameters an override adds. Wave 1zls7.

- **An override of a self-recording tool now records what it adds.** For an override of a lifecycle or retrieval tool that records its own cost (`_COST_EXEMPT_TOOLS`), `core_handler(name)` returns a thin measuring wrapper that returns the core result unchanged, and the server records one extra cost event for the core name holding only the response size the override added after the core call (none when it added nothing), or the request and whole response when the override never delegates. A delegating override that adds fields therefore counts as two events in the context-efficiency **Tool calls** column. Call `core_handler` on the thread that runs the override; a core call made in a thread-pool worker is not subtracted. An override of a lifecycle-locked tool already runs entirely under the lifecycle lock and the upgrade publication guard. Overrides of other tools, replacements and every name without an override record exactly what they recorded before. Wave 1zls8.

- **A `required_review_lanes` that is not a list is now a config error.** A string or object value was read as no project lanes, so a typo silently dropped every project-required review. Docs-lint now reports `required_review_lanes must be a list`, Prepare refuses through its policy-state config error, and Implement, Review and Close report the blocking `required_review_lanes_invalid`. The signoff projection now drops a list entry that is not a non-empty string, as the gates already did, instead of turning it into a lane name. Wave 1zlu1.

- **The single-change lifecycle prompts are named for the change, and Close change replaces Finalize feature.** Plan feature and Implement feature are now **Plan change** and **Implement change** (`docs/prompts/plan-change.prompt.md`, `docs/prompts/implement-change.prompt.md`, their `docs/prompts/agents/` bodies, seeds `170-plan-change.prompt.md` and `180-implement-change.prompt.md`), and the planning skill is `wf-plan-change`. Finalize feature is retired: **Close wave** is the only wave close, and the new **Close change** prompt (`docs/prompts/close-change.prompt.md`, a missing-only lifecycle baseline) and `wf-close-change` skill close one reviewed change inside the open wave with `wf_close_change`. Seed 190 is now `190-close-wave.prompt.md` and carries a Close change section. `wf_help(goal='plan_change')` replaces the old planning goal, and no old name is kept as an alias. Lifecycle wording says close instead of finalize. On upgrade, the renderer moves the plan and implement prompts and agent bodies to the new names byte-for-byte and rewrites their manifest entries; if an old and a new prompt both exist, or an old path is a symlink, it stops before writing anything so the operator can merge. The retired finalize prompts are never deleted automatically: the reconcile scan reports each by file identity, and the operator merges any unique guidance into `docs/prompts/close-wave.prompt.md` or `docs/prompts/close-change.prompt.md` and removes it. Recovery after upgrade: the render and the reconcile scan report each markdown link that still targets a moved prompt as `file:line`; edit each link to the new path, then rerun the docs gate. The scan also flags the `description:` line of `.claude/agents/guru.md`, which the renderer preserves; edit it to say Plan change. Wave 1zyc5.

- **Journal and snapshot history is one shared definition, and `wf_audit` reports vendored dashboard script drift.** A new stdlib-only module, `history_paths`, names the history directories (`HISTORY_PATH_COMPONENTS = ('journals', 'snapshots')`) and tests a path relative to the scan root, component by component. The docs-lint agent validators, the agent-surface integrity scan, the renderer's review-role slug, the upgrade role backfill, the reconcile scanner and the retrieval demotion all use it. Behavior change: every site except the reconcile scanner now also treats a `snapshots/` directory as history (the retrieval demotion applies the history test to document results only, so source code under a `journals/` or `snapshots/` directory is no longer demoted), and a checkout placed under an ancestor directory named `journals`, `snapshots` or `memory` no longer has its agent docs skipped. `wf_audit` adds a report-only `data.vendored_scripts` object (`ok`, `mismatch`, `unavailable` or `unreadable`) from an offline hash check of the audited repository's vendored dashboard scripts; a mismatch or an unreadable table adds an advisory diagnostic and never changes `ready`. A malformed row in the vendored scripts table is now named by its line number and cause, without echoing the row text. The offline check now ships with the framework as `vendored_integrity`, so installed targets run it too. Also: the change-document fence scan no longer rescans for repeated unclosed fences of the same shape, which made long documents quadratic. Reported by the Waveforge maintainers. Wave 1zyb2 / 1zxnt.

- **The council signoff keys no longer name the container tier.** New approvals are written as `council-readiness` and `council-delivery`, and these are the default keys in configs without `wave_review.phases`. The earlier `wave-council-` prefixed keys are read everywhere forever: every gate, the close check and docs-lint compare keys in one canonical form, so recorded ledgers, wave records and archives keep passing unchanged, and a wave whose review-status block already labels a council row with the earlier key keeps that label. The earlier keys also stay accepted as `wf_review_event` input (recorded under the new key, with an informational `signoff_key_alias` diagnostic) and as `signoff_key` config values from this release through at least the next minor release; retiring that input alias is a separate later change. Retrying an approval that was first recorded under an earlier key, with the same `context_id`, replays that record instead of appending a second one. No ledger, wave record or config is rewritten, and a config naming either spelling produces the same review-policy receipt digest, so no receipt rotates and no approval lapses. The approving actor and role remain `wave-council`. Wave 1zyb4 / 1zxnx.
- **Reconciled prompts name the tier-neutral council key, and a profiled fresh install converges.** Prompts reconciled by the upgrade now name the council key `council-readiness`, and this repository's own review config uses `council-readiness` and `council-delivery`. Because the reconciled prompt text changes, the upgrade marks each open or readied wave for one re-Prepare in repositories that hold one, together with the earlier key change in this release. The earlier keys `wave-council-readiness` and `wave-council-delivery` stay accepted everywhere. A fresh install under a prompt-name profile no longer writes renamed lifecycle prompts before the prompt-surface manifest exists, so the next render converges instead of stopping on a name conflict, and the reconcile scan also reports a renamed prompt's earlier aliases. Wave 200xy / 200xx.
- **Framework Python bytecode is cached in the project, never beside the sources.** Hooks, `wf` commands, the MCP server, setup and index children and the test runner now keep compiled bytecode under `.wavefoundry/cache/pycache/` instead of recompiling the framework modules on every start, and no longer leave `__pycache__` directories under `.wavefoundry/framework/`. The cache is flushed by the first framework process after `.wavefoundry/framework/VERSION` changes, so every upgrade starts clean. It is gitignored (the managed gitignore block gains `.wavefoundry/cache/`) and excluded from the pack, the indexes, the secrets and reconcile scans and the test receipt. `PYTHONDONTWRITEBYTECODE=1` or `python3 -B` makes a process read the cache without writing to it. A cache directory that is a symlink, or on Windows a junction or other reparse point, is refused and caching stays off. The upgrade replaces the earlier hygiene paragraph in a target's `AGENTS.md` when it matches the shipped wording exactly and reports any other wording. Wave 200xy / 1zyv1.

### Security

- Path and id containment for wave records, journals, vendored files and extension provenance. Change ids read from a wave record or passed to a lifecycle tool are now checked against one allow-list (`<prefix>-<kind> <slug>`) before any path is built from them. Member change documents are read only as regular files inside their own folder and inside the repository, through a size-capped read; staged plan listings and the dashboard apply the same rule, and docs-lint refuses a linked or non-regular member document in its wave-document check. On POSIX the upgrade's journal migration now creates and removes files only through directory handles reached by a no-follow walk, and its messages carry no absolute path. The offline vendored-script check reads only regular files confined to the vendor folder, under a size cap, and names a refused table row by its position rather than echoing it. `wf_server_info` extension paths are never absolute (`framework:` and `external:` labels). Bulk `wf_get_change` matches each member by its exact name instead of a substring. A wave-record member line whose id fails the allow-list is never read: the phase tools block with `change_id_invalid`, naming the record and line number; recover by editing that line by hand, then run `wf_validate_docs`. Behavior change: a wave folder that is a symbolic link resolving outside the repository no longer serves member change documents to the lifecycle tools; in-repository folder links keep working. Reported by the Waveforge maintainers. Wave 1zxo0 / 1zxns.
- Taking the lifecycle lock now refuses, and releases the lock again, when a reader in the same process could release it through a link: the lock file has another hard link; a symlink or Windows junction resolves to a runtime lock anywhere in the record roots and archive, `docs/`, all of `.wavefoundry/` except a project-local `venv`, or the repository root's own entries; or a record-root directory link leads outside the repository. A link that names the checkout in another case, Unicode form or firmlink spelling is judged by file identity. The check opens no file, and an in-repository pnpm-style `node_modules` is not refused; it also refuses (`link_scan_limit`) when more than 50,000 entries are reachable only through directory links. The server reports `lifecycle_lock_link_refused` with the repository-relative link and its remedy, and `wf setup` and the upgrade runner report the same refusal instead of a busy lock. Found in review of wave 1zv87. Wave 1zv8c / 1zv8b.
- The upgrade's journal migration no longer follows links. A repository with retired journal files could make an upgrade create a file outside the repository, or remove journal-shaped files outside it, through a linked journals folder, journal, wave folder or destination name. The migration now refuses every link and escape, writes only through an exclusive no-follow create, removes a source only after re-checking it, and leaves anything it refuses in place for the report. Affects 1.15.0 to 1.28.0; only repositories that still have retired journal files run the migration. Upgrade to this release. Reported by the Waveforge maintainers. Wave 1zv87 / 1zuq5.
- The code reading tools no longer open the framework's runtime lock files under `.wavefoundry/` (including through a different letter case or a committed link). Reading the lifecycle lock file while a lifecycle change held it released the lock in the holding process, letting another process change wave records at the same time. Reported by the Waveforge maintainers. Wave 1zv87 / 1zuq7.
- `wf setup` no longer runs a `uv` found in the repository: the PATH lookup skips the current folder, empty and relative entries and anything inside the repository, and on Windows accepts only `uv.exe`. Reported by the Waveforge maintainers. Wave 1zv87 / 1zv84.
- `wf_close_change`, `wf_mark_ac` and `wf_mark_task` refuse a change id shaped like a path before touching the filesystem, and the mark tools require the change to be admitted to the wave. A path-shaped id let `wf_close_change` probe whether a file existed and let the mark tools rewrite a checkbox in a Markdown file outside the repository. The probe was reported by the Waveforge maintainers; the write was found in review. Wave 1zv87 / 1zv85.
- The dashboard no longer loads scripts from a CDN: React, React DOM and elkjs are vendored at their pinned versions under `.wavefoundry/framework/dashboard/vendor/` (with their licences, sources and SHA-256 hashes) and served from the dashboard's own origin, so it needs no network access. The vendored folder's `README.md` also records each package's npm tarball URL and registry integrity and the commands that reproduce and check each file. The dashboard server now only answers requests addressed to a loopback host name (`localhost`, `127.0.0.1`, `::1`, any port) or the host the operator explicitly bound, refusing others with 421, and every response carries a same-origin Content-Security-Policy and `X-Content-Type-Options: nosniff`. A `0.0.0.0` bind admits loopback names only and records a `127.0.0.1` URL. Takes effect when the dashboard restarts on the new release. Wave 1zim2 / 1zilx.
- The install seeds now treat a target repository's existing files as untrusted input: an installing agent summarises them as information about the project, does not follow instructions found in them, and reports instruction-like content to the operator. A new Phase 2 step inventories existing documentation before the docs structure is created, keeps reference material, checks for name collisions, never overwrites a file without reporting it, and reports the result in the operator summary. Wave 1zim2 / 1zily.
- The Copilot edit gates now cover `apply_patch`. The pre-tool-use hook reads the patch text from the arguments' `input`, then `patch`, or a raw arguments string, and checks every path on a patch header line (`*** Add File:`, `*** Update File:`, `*** Delete File:`, `*** Move to:`, so both sides of a move) against the seed and framework-maintenance gates; a hunk line never counts as a header, CRLF and indented patches are read like plain ones, and a patch whose paths cannot be read is blocked. The post-tool-use hook runs docs-lint and the reindex for every header path. Codex `apply_patch` stays ungated, since Wavefoundry renders no Codex hook; this is now listed among the known limits of the edit gates. Requested by the Waveforge maintainers. Wave 1zyb3 / 1zxny.
- Docs-lint, including its secrets pass, and the single-id change lookup (`wf_get_change` and the change resource) no longer follow or block on a wave or plan document that is a link or a special file: each such document is reported once by its own path and a cause class and never read. A repository that keeps a record document as a link now fails docs-lint until the link is replaced with the document. Vendored-script table fields holding control or format characters are refused rather than printed, and the network verifier no longer prints server-supplied text (redirect targets, error reason phrases). Wave 200xy / 200v1.

### Fixed

- **The lifecycle and index-build locks can no longer be lost to an unrelated descriptor close, and `wf_reload_mcp` loads new `runtime_lock` code.** On POSIX these locks were classic record locks, which the kernel releases when the holding process closes any descriptor of the lock file, so lock safety depended on every in-process reader avoiding lock files. On Linux and macOS (64-bit, x86_64 or arm64) they are now open file description (OFD) locks, which belong to the lock's own open file description; other platforms, and kernels or filesystems that reject OFD as unsupported, fall back to `lockf` as before. OFD and `lockf` locks exclude each other, so a process from an older release still running during an upgrade stays excluded. While another process holds an OFD index-build lock, `index_build_status` takes the owner pid from the lock metadata, because the kernel reports no pid for an OFD holder. As defense in depth for the fallback, the session handoff reader and writers, prompt lookup and the read-only resources refuse a target that resolves to a runtime lock without opening it (`runtime_lock_target_refused`, or a `# Refused` page); `wf_get_prompt` skips such a candidate and keeps searching. Separately, `wf_reload_mcp` failed with an import error when a release added a name to `runtime_lock`, because that module was never reloaded; it is now reloaded in place, keeping the in-process hold registry and its exception classes, and a test fails when a reloaded module imports a module the reload leaves stale without a recorded reason. A future release that changes a `runtime_lock` exception class definition will say that a host restart is needed. Native Windows is unchanged. Wave 1zxnz / 1zx02.
- Four framework tests no longer fail a distribution whose extension declarations or vocabulary are valid but not the stock ones. The wrapper-order test passes each wrapper its own declared keywords in every permutation. The timeout-routing census accepts a `run_with_tree_kill` call in a distribution's own flat module (a raw timed call there still fails). The framework-script census reads the declaration on disk, stays exact on a stock declaration, and on a declared distribution requires only the modules the server or a framework script imports. The invalid-profile upgrade test corrupts whatever container name is declared. Requested by the Waveforge maintainers. Wave 1zv88 / 1zv86.
- A `wf setup` rerun on an installed repository no longer ends with first-install instructions (mark Phase 1 complete in the install log, call `wf_audit_install()`). That text now appears only while `.wavefoundry/install-log.md` exists with a Phase 1 row still pending (or cannot be read or parsed); otherwise setup ends with the restart guidance and `index_health()` or `wf setup --check` to confirm. Wave 1zuq3 / 1zuq1.
- `wf setup --check` retries before reporting a transient result: when every reason is `inputs_changed` or `probe_timeout` (typically an index refresh writing during the check) it reassesses after 2, 5 and 10 seconds, noting each wait on stderr, as upgrade cleanup already does; a result still transient after the last wait is reported as before (exit 2). Wave 1zuq3 / 1zuq2.
- Setup, upgrade and `wf render-surfaces` no longer rewrite unchanged platform surfaces. Identical rewrites changed every file's modification time, so a target whose `.gitattributes` holds only the Wavefoundry line-ending block had it re-indexed as a "drifted" file on every setup. Wave 1zuq3 / 1zuq4.
- The upgrade summary no longer reports `Setup: ready` when cleanup leaves an outdated setup baseline in place (the last `wf setup` ran in another environment, such as an older Python, or the index or dependency step failed). The summary's setup fields now report the same assessment later readiness checks make against that baseline, typically `action_required (setup_inputs_changed)` with `wf setup --root <repo>` as the next step. The fields come from the new-code cleanup process, so this applies on the upgrade that installs it. Wave 1zu53 / 1zu51.
- Terminal `wf setup` runs on macOS no longer lose GPU acceleration: the isolated CoreML safety probe imported numpy before activating the Wavefoundry tool environment, so on a system `python3` without numpy it always failed and indexing fell back to the CPU. The probe now activates the tool environment first (Windows was unaffected, since its probe already runs inside that environment). When a probe does fail, setup now ends with a line naming the CPU fallback and `wf setup --check-gpu`; setup readiness stays ready, because the CPU path is valid. Wave 1zu53 / 1zu52.
- Lifecycle mutation lock holds can no longer be lost to a same-process re-entry or to the publication lock's lifecycle probe: a re-entry from another thread of the holding process is refused with the busy response, and one from the same thread with `lifecycle_lock_reentry`, and the probe consults the in-process hold registry, so it never opens the lock file while this process holds it. A publication-lock request inside the upgrade's lifecycle publication transaction on the same thread is now refused at once instead of waiting on its own hold. Two intended behaviour changes follow: a publication-lock wait from one thread now fails fast while another thread of the same process holds the lifecycle lock, and on Windows a caller that holds the lifecycle lock now waits for a busy publication lock instead of failing fast. The secrets scanner never reads Wavefoundry's own lock files (anything under `.wavefoundry/locks/` and any `.lock` file elsewhere under `.wavefoundry/`), on every file-selection path and for an explicit file list, and drops any recorded finding for such a file; `.lock` files elsewhere in the repository, such as `Cargo.lock`, are still scanned. Wave 1zimc.
- The harnessability audit no longer reports the best debt score when its marker scan fails: a `git grep` exit other than 0 or 1 (not a repository, or one git refuses) now gives `debt_density` "unknown" with the exit code and git's first error line, and a scan that raises names the exception. Wave 1zim2 / 1zilz.
- `wf setup` and the upgrade's dependency step no longer apply a repository's `uv.toml` or `[tool.uv]` to the shared tool environment: installs run from the tool-environment folder with uv's configuration discovery off, as the MCP startup install already did. This takes effect in the upgrade that installs it. Wave 1zicq / 1zhmd.
- When no uv exists, setup bootstraps an exact pinned uv wheel instead of the newest release; an existing uv of any version is still used as-is. The bootstrap installs only a wheel whose SHA-256 matches one recorded for the pinned version and refuses other bytes and reports the failure. Wave 1zicq / 1zhmd; hash verification wave 1zimd.
- The setup deadlines that hold the shared install lock are capped at twice their defaults (`dep_install_timeout_seconds` at 3600 s). Wave 1zicq / 1zhmd.
- An extension replacement can no longer declare `tier: read` for a core write tool, which would have put it in hosts' read-tier allow lists; the server's extension load and the permission roster both refuse the declaration. The edit-gate tools `wf_open_gate` and `wf_close_gate` can no longer be overridden, replaced or hidden by an extension declaration (aliases are still allowed). Wave 1zicq / 1zhme.
- With an archive root configured, an archived wave's `events.jsonl` review ledger is treated like a live one: kept out of semantic retrieval and recognised as machine authority by the secrets scan's non-git fallback walk. Wave 1zilw / 1zicn.
- The upgrade's retired-model cleanup now also removes the caches of `Snowflake/snowflake-arctic-embed-xs`, the docs model from 1.6.0 to 1.15.4 (four directories under `~/.wavefoundry/cache`, about 190 MB of CoreML compiles on macOS), behind the same safety checks as the BAAI caches. The cache is shared per user, so a repository still on 1.6 to 1.15 re-downloads it if it needs it. Wave 1zilw / 1zico.
- With an archive root configured, records under it are no longer treated as live: the memory id migration no longer rewrites legacy memory references in archived records (live documents and live memory records are still repaired), and the review-policy upgrade preflight no longer reports archived records as retired lifecycle prose to rewrite by hand. Without an archive root nothing changes. Wave 1zim5 / 1zim7.
- A failed MCP startup install now names the likely cause (network, proxy or TLS access to the package index); uv already gives up on an unreachable index within about a minute. Wave 1zicq / 1zhmd.
- One denied file stat no longer aborts indexing, `index_health`, the docs fallback or code navigation: the repository walk skips an entry it cannot stat (for example a `.env` symlink into a protected directory), names it on stderr unless the entry is excluded or ignored (those are filtered before any stat) and keeps its index rows, hashes and bookkeeping until it is readable again, while a dangling symlink still reads as removed. The upgrade's docs gate and the post-edit hook's docs-lint now pin `PROJECT_ROOT` to the repository they check, so an inherited value naming another repository can no longer garden or lint that tree. The embedding provider probe runs in a child process with a 600 s bound, so a native crash, an abnormal exit or a hang rejects the accelerated provider with a reason naming the signal, exception code, exit status or timeout, and `wf setup`, `gpu_doctor.py` and `wf_gpu_doctor` continue on CPU. The dashboard's Windows `taskkill` is bounded at 10 s, so a hung kill reports the dashboard as not stopped instead of blocking `wf_stop_dashboard` and `wf_restart_dashboard`. `index_health` does not report such a kept file as removed or stale. Wave 1zime.
- The close-time checkbox gate no longer passes an open acceptance criterion or task written with a list marker other than `-` (`*`, `+`, `1.`, `1)`), under a missing, misspelled, suffixed or demoted `## Acceptance Criteria` or `## Tasks` heading (including a `## Tasks (remaining)` section beside an empty exact `## Tasks`), under a second section with the same heading, or citing a not-this-scope AC later in its text. One shared checklist parser reads every list marker, every section with the exact heading (CRLF as LF) and takes an AC id only from the start of the item; close refuses a document without both exact headings (`change_doc_missing_sections`, the section may be empty); Prepare checks those two headings exactly and refuses a non-dash checklist item or a near-miss heading on any wave status (`change_doc_noncanonical_checklist`); and docs-lint fails a non-dash checklist item or a near-miss heading in a ready, active or implementing wave, naming the canonical `- [ ] ...` form. Wave 1zime.
- The close-time checkbox gate no longer passes three shapes of open item: a blockquoted item (`> - [ ] x`), an item with a single-character mark other than `x`, `X` or `~` (`[-]`, `[/]`, now open and shown with its mark), and an item after a fenced code block holding a `## ` line. The shared checklist parser accepts a blockquote prefix and any single-character mark, sets closed fenced code aside (an unterminated fence, or a quoted fence that ends with its blockquote, hides nothing), and reads near-miss `## Acceptance Criteria` and `## Tasks` headings regardless of case, inner whitespace and up to three spaces of indent. docs-lint and Prepare report an unusual mark and ask for `[ ]`, `[x]` or `[~]`; `wf_mark_ac` and `wf_mark_task` find items through the same parser, so every item that blocks close can be marked, rewriting only the mark; and the gate finds admitted changes with docs-lint's record parser, so an indented `Change ID:` block no longer escapes it. Wave 1zls7.
- `wf_close_wave` no longer closes a wave while a change is `blocked`, `review`, `retry` or in a status no framework set defines. Close refuses with `open_changes_remaining` unless every change is done: `DONE_CHANGE_STATUSES` in `wave_lint_lib/constants.py` is the terminal statuses plus `implemented` (which does not block close and stays non-terminal), and a legacy item is done in a terminal item status. Records are read with docs-lint's record parser, and every status line attributed to a record counts: a record is open when any of its status lines is not done (so a later duplicate, fenced example or indented line reading `complete` cannot hide an open status), when one cannot be read, or when it has none; an `Item Status` line inside a change record is read too, and a status line outside every record also refuses close. An id label with no backticked id (prose such as `Change ID: assigned at planning`) starts no record. The refusal names each open change with its status. The docs-lint dependency rule reads the same done set, so an `implemented` dependency now satisfies a dependent change. Wave 1zls7.
- Lifecycle lock refusals name the lock actually held, without absolute paths. A lifecycle tool refused at the lifecycle mutation lock now names `.wavefoundry/lifecycle-mutation.lock` by its repository-relative path and no longer repeats the lower-level exception text; `lifecycle_mutation_locked` says whether another process or another call in this server process holds it. A lock whose ownership cannot be proven returns `lifecycle_lock_unavailable`, which is not busy and says retrying will not help. A call that re-enters the lock on its own thread, directly or through a nested locked tool, returns the new `lifecycle_lock_reentry` instead of blaming another session. Lock refusals raised by the tool body are no longer reported as contention, and other body exceptions propagate unchanged. `project_publication_busy` refusals from `wf_mark_ac` and the upgrade publication guard, the root-resolution refusal and the context-efficiency `publication_lock_busy` error are path-free too, and so are the context-efficiency projection's `index_source_busy`, `index_source_unavailable` and failure rows that `index_health` reports under `background_monitors` (the exception class and errno name, with the repository-relative lock path). Wave 1zls7.
- `memory_consolidate` and `memory_purge` are now registered publication writers, like `memory_add`, `memory_propose` and `memory_reconcile`: during an upgrade checkpoint they are refused with `upgrade_in_progress`, and a held publication lock returns the path-free `project_publication_busy` refusal with `publication_applied: false` instead of an error carrying absolute lock paths. The `memory_purge_failed` and `memory_consolidation_failed` diagnostics (including a failed rollback) no longer echo an absolute filename. Wave 1zls7.
- The context-efficiency projection's `monitor_error` and `authority_unavailable` rows that `index_health` reports under `background_monitors` no longer carry absolute paths: an `OSError` is shown as its class and errno name with its repository-relative filename (dropped when outside the repository), and other error text is kept only when it names no absolute path. Wave 1zls7.
- MCP startup no longer reads a `.env` file in the server's working directory for FastMCP settings, so an unreadable or undecodable `.env` (for example one belonging to an unrelated project) no longer stops the server from starting. Wave 1zls7.
- A `Depends On:` line inside a fenced code block in a wave record or change document is now an example, not a dependency: `wf_close_change` no longer moves a change to `ready` because of one, docs-lint no longer reports an unmet, unknown or unbackticked dependency for one, and `wf_implement_wave` no longer lists one in `depends_on`. A `## ` line inside a fence no longer ends `wf_implement_wave`'s reading of the member section. Docs-lint warns about each fenced `Depends On:` line in a wave record's member section, so a dependency fenced by mistake is visible. An unterminated fence is still read as ordinary lines, and fenced status lines are still read, so an example cannot hide an open change from wave close. Wave 1zoju.
- `wf_close_wave` no longer closes a wave while a change's status in the wave record differs from the status in its change document's header, which is how closed waves acquired status drift: dry run and create refuse with a blocking `change_status_drift` diagnostic naming each change and both values, before close writes anything of its own. A wave already `closed` or `completed` re-closes as before. Docs-lint now warns (never fails) about the same drift for every wave that is not closed or completed, including from an edited change document on the incremental post-edit path, and `wf_current_wave`'s drift advisory now reads the change document only at its exact path and only from its header, instead of the first file whose name contains the id and the first status line anywhere in it. Wave 1zoju.
- The dashboard now counts a change as done by the framework's one done set (`DONE_CHANGE_STATUSES`: the terminal statuses plus `implemented`), the set wave close and the docs-lint dependency rule read, instead of two hand-kept lists that disagreed with it and with each other. An `implemented`, `deferred`, `moved` or `superseded` change in an open wave now counts as done in the progress figures, and `closed` and `approved`, which are not change statuses, no longer do. The snapshot carries the set as `config.done_change_statuses`, and the page reads it from there. Status badge colours are unchanged. Wave 1zoju.
- An exception that no tool handler catches no longer reaches the MCP client as raw text that can carry absolute paths (an `OSError` names its file; a lock refusal names the lock's absolute path). It is now returned as a standard error envelope with `data.tool` and one `tool_unhandled_exception` diagnostic whose message keeps the exception class, the errno name and a repository-relative filename but no absolute path, while the full traceback still goes to stderr. This applies to every served tool, including extension tools, overrides, replacements and aliases, and to exceptions raised by the server's own wrappers. Like every other error envelope it is a normal tool result whose JSON carries `isError: true`, so a client that read the protocol-level `isError` flag of a crash now sees it false and should read the envelope's `status` instead. Interrupts propagate as before. Wave 1zoju.
- No exception-derived text in a `wf_reload_mcp` response carries an absolute path any more. An exception escaping the reload tool now returns the same path-free `tool_unhandled_exception` envelope as every other tool instead of raw text, and its handled diagnostics built from an exception (`handler_close_warning`, `reload_failed`, `tool_remove_warning`, `register_surface_failed`, `setup_readiness_unavailable`, `tool_list_changed_notification_failed` and `runner_identity_unrecorded`) keep the class, errno name and repository-relative filename but no absolute path, while the original text goes to stderr. A `reload_failed` message now starts with the exception class (`ValueError: bad id`, or `PermissionError EACCES on docs/x.md`) instead of the bare exception text. The path-free reload diagnostics also reach `wf_upgrade`, which forwards them when it reloads in process, and its `mcp_reload_skipped` no longer echoes a reload exception's absolute path. Cancellation still propagates. Most of this lives in the server runner, so a running host picks it up after a restart (`runner_stale` reports it); before then, its first reload of the new implementation already renders an exception escaping the reload tool. Wave 1zqe4 / 1zqe3.
- `wf setup` now repairs a tool venv built for another Python minor version. After `python3` moved to a new minor version (for example Homebrew 3.13 to 3.14), setup exited 2 with `the tool venv was built for Python 3.13 but this is 3.14 - run wf setup to rebuild it` before it could rebuild the venv. Setup now records in its own process that it deferred activation, so a later activation in that process returns instead of exiting until the rebuilt venv activates. The storage probe no longer imports the native SQLite runtime while activation is deferred, so the check after dependency provisioning reads the real schema, and setup no longer writes a spurious schema-8 migration receipt over a current index. Every other command still stops with the same message and exit 2 on a mismatched venv. Wave 1zqe4 / 1zrag.
- A storage receipt that fails with `storage_receipt_supersedes_invalid` now recovers through ordinary `wf setup`. Setup could write a schema-8 migration record over a completed one and then refuse to read it, which blocked setup, upgrade and every index reader. The receipt reader and its three writers now share one rule: a schema-8 record may supersede a completed schema-8 record, embedded unchanged, and every nested level is checked. After dependency provisioning, setup retires a setup-owned record that never started staging when a probe with the provisioned runtime shows the index is already at schema 8, in one write. When the record's parent is a completed schema-8 record, the shape this defect wrote, setup writes that parent back unchanged: releases 1.24 to 1.28 read it, so the recovered receipt needs no host restart and an older release can still be reinstalled. Otherwise setup closes the record as `complete` with disposition `already_current` and rebinds it to the installed framework. The record must be in state `restart_required` or `quiesced`, with no work directory or candidate, read from the current database name, with nothing under the retired name and a recorded identity equal to the live database. Any other record keeps its existing refusals, and a record whose database is not at schema 8 still refuses with `storage_setup_source_changed` and is left unchanged. Restart every MCP host and the dashboard after installing this release: until then `runner_stale` reports the `venv_bootstrap.py` change and `loaded_code_stale` the storage modules, and runners from 1.24 to 1.28 refuse a receipt in which one schema-8 record supersedes another, which this release can write for a genuine second conversion. Wave 1zqe4 / 1zrag.
  - Apply this remedy before upgrading from 1.24 to 1.28. An upgrade from those releases reads the stuck receipt in the installed release's own upgrade command, before this release's code runs, so it refuses with `storage_receipt_supersedes_invalid` and changes nothing. A repository whose installed framework already includes this fix needs no remedy: ordinary `wf setup` recovers it.
  - Remedy on a release without this fix (1.24 to 1.28): restore the completed record embedded in the receipt; do not move the receipt aside, which drops the version-2 record that fences old runners. With every Wavefoundry host (MCP servers and the dashboard) stopped, first check every condition below from the repository root. On Windows, run each `python3` command below as `python`, and read `~/.wavefoundry/venv` as `%USERPROFILE%\.wavefoundry\venv`.
    - The receipt's parent is a completed schema-8 record: in `.wavefoundry/index/sqlite-migration.json`, `supersedes.receipt_version` is `2`, `supersedes.kind` is `index_sqlite_schema8` and `supersedes.state` is `complete`.
    - The index is already at schema 8: `python3 -c "import sqlite3; c = sqlite3.connect('file:.wavefoundry/index/index.sqlite?mode=ro', uri=True); print(c.execute('SELECT value FROM meta WHERE key=?', ('store_schema_version',)).fetchone()[0])"` prints `8`.
    - Nothing exists under the retired database name: `.wavefoundry/index/index-state.sqlite` and its `-wal` and `-shm` files are absent.
    - The receipt has no `work_dir` key.
    - `.wavefoundry/upgrade-in-progress.json` is absent, or its `storage_migration_id` equals `supersedes.migration_id`.
    - The tool venv matches the interpreter: the `version` line in `~/.wavefoundry/venv/pyvenv.cfg` (or under `WAVEFOUNDRY_TOOL_VENV` when set) has the same major and minor version as `python3 --version`. The setup run that wrote the stuck receipt has normally already built a matching venv; without one, setup on these releases writes the same stuck receipt again.

    If only the tool venv condition fails, rebuild the venv without reading the receipt, then check every condition again: rename the venv directory aside (for example `~/.wavefoundry/venv` to `~/.wavefoundry/venv.stale`; on Windows the rename fails while any host still has the venv's files open, so stop every host first), then run `python3 .wavefoundry/framework/scripts/setup_index.py --root . --deps-only` (Windows: `python .wavefoundry\framework\scripts\setup_index.py --root . --deps-only`). On these releases that command over the stale venv itself still exits 2 with the version message, so the rename comes first. If any other condition fails, do not edit, move or delete the receipt and do not upgrade: keep `.wavefoundry/index/` as it is and report the receipt for a supported recovery.

    When every condition holds, copy `sqlite-migration.json` aside as evidence, rewrite it as its own `supersedes` value, for example `python3 -c "import json, pathlib; p = pathlib.Path('.wavefoundry/index/sqlite-migration.json'); p.write_text(json.dumps(json.loads(p.read_text())['supersedes'], indent=2))"`, and rerun `wf setup` (`.\.wavefoundry\bin\wf.cmd setup` on Windows). Releases 1.24 to 1.28 accept the restored record, whose own parent, when it has one, is a version-1 record, and treat it as finished history.
- Rendered hooks no longer exit 2 when the tool venv was built for another Python version. The hook bootstrap caught `Exception`, but the venv version guard raises `SystemExit`, so after a Python upgrade the Claude Code pre-edit hook blocked every edit and the `Stop` hooks looped. Hooks now activate with setup's allowance. When the venv was built for another Python version, or activation raised anything, a hook writes one line to stderr saying to run `wf setup`, and nothing to stdout. Edit gates keep their verdicts: a closed seed or framework gate still blocks with the host's usual signal, and an open gate or an ungated path is allowed. The post-edit, docs-lint and `Stop` hooks exit 0, skip their docs-lint and reindex children and keep the reindex-pending marker, so the first hook run after `wf setup` flushes it. A venv that is not built yet behaves as before. The regenerated hooks reach a repository through `wf setup` or an upgrade. Wave 1zqe4 / 1zrag.
- An upgrade from 1.28.0 no longer fails at the lifecycle-ID policy phase with `AttributeError: module 'vocabulary_profile' has no attribute 'CHANGE_KINDS'`. The 1.28.0 upgrade command keeps the modules it imported before extraction, so the newly extracted lifecycle-ID code read the old vocabulary profile. The upgrade's post-extraction step now re-executes the cached `vocabulary_profile`, `path_containment` and `record_paths` from the extracted files in place, keeping each module and its exception classes, before the old upgrade command imports any other newly extracted module. If one of them cannot be re-executed, the upgrade stops with exit 3 and a message naming the module and asking to rerun the same upgrade command. An operator who already hit the `AttributeError` reruns the same upgrade command: the rerun runs the new release's code and passes that phase. Wave 1zqe4 / 1zrah.
- Python 3.14 fixes. A native crash in the embedding provider probe again reports the Python frame that crashed: Python 3.14's `faulthandler` also prints the C stack by default, which pushed the Python frames out of the five-line stderr tail, so the probe turns the C stack off on 3.14 and leaves 3.11 to 3.13 unchanged. The review authority guard no longer passes a wave directory it could not inspect: Python 3.14 `pathlib` predicates return `False` on any `OSError`, so an untraversable wave directory read as safe and the later read failed as unreadable. The guard now uses `os.lstat` on every interpreter: any error on the wave directory, or a wave directory that is not a directory, is "not safely resolvable"; a missing `wave.md` or `events.jsonl` (`FileNotFoundError` or `NotADirectoryError`) is still absent; and any other error on them, including a symlink loop, which older interpreters read as absent, is "not safely resolvable". Messages stay path-free and the symlink and escape rejections are unchanged. A dead `lancedb` import is removed from a SQLite-only test. Wave 1zqe4 / 1zrai.
- More Python 3.14 fixes for checks that relied on `pathlib` predicates raising. On 3.14 `Path.exists`, `is_symlink`, `is_file` and `is_dir` return `False` on any `OSError`, so a path the framework could not inspect read as absent. These checks now use `os.lstat` or `os.stat` on every interpreter: only a missing path (`FileNotFoundError` or `NotADirectoryError`) is absent, and any other error refuses or is reported. Upgrade's retired review-evidence sidecar cleanup refuses an uninspectable `docs/waves` or sidecar instead of skipping it, and its refusals no longer include absolute paths: each names the member, the cause and the recovery. An uninspectable index database name reads as present again, so it is never treated as absent and replaced. An upgrade lock that cannot be inspected reads as present but is never treated as stale, cleared or rewritten: setup and upgrade preflight refuse with a message naming `.wavefoundry/upgrade-in-progress.json`, the cause and the recovery (restore access to it, or remove it if no upgrade is running) instead of reporting a foreign or running upgrade, the dashboard stays paused, and `wf_upgrade_status` adds a `lock_unreadable` field with the same message. Historical-memory inventory refuses an uninspectable waves or archive root instead of finding no waves. Memory purge refuses when it cannot inspect a candidate body. Upgrade's review-policy migration, its lifecycle-ID policy step and setup's workflow defaults no longer overwrite a `docs/workflow-config.json` they cannot inspect, and the lifecycle-ID policy step's refusals for an unparseable or non-object config no longer include absolute paths. Pack discovery records an inaccessible search location, legacy `meta.json` removal and declaring-scaffold repair report a file they cannot inspect, the model-cache check reports an unreadable snapshot (which, as on 3.13, quarantines the cache and retries the download once), and a memory consolidation rollback reports itself incomplete when it cannot inspect a member. ELOOP, EBADF and the Windows errors WinError 21, 123 and 1921, which Python 3.11 to 3.13 also read as absent, now refuse too. Wave 1zrak / 1zraj.
- Wave discovery, docs-lint inputs and index removal validation no longer read what they cannot inspect as absent. A waves or archive root that cannot be inspected or listed, which read as "no waves" (on Python 3.14 for a root under an untraversable parent, and on every Python for an unlistable root), now refuses with `record_root_unreadable`, and a wave or archive folder discovery uses below it (a candidate whose record file cannot be checked, a nested grouping folder it cannot list), which was silently left out, refuses with `record_folder_unreadable`. Both name the repository-relative path, the cause and the recovery (restore access, or move a non-wave folder out of the root), never an absolute path. Every lifecycle tool that discovers waves returns that refusal and writes nothing, including a change lookup by id, which no longer reports `change_not_found` for a change held in a wave folder, plans root or archived folder it cannot list; `wf_create_wave` and the `wf_new_*` tools never mint an id that an unlisted folder, plans root or `docs/architecture/decisions` may already use; the `lifecycle_id.py` CLI exits 2 with the same message; docs-lint reports it once as an error; the dashboard answers a document request with `503`; the historical-memory backfill and the upgrade's review-policy preflight refuse through their existing errors. Dot-prefixed folders, symlink targets, folders beyond `MAX_DEPTH` and a wave folder's own subfolders never refuse. Docs-lint reports `docs_lint_input_unreadable` for a `docs/workflow-config.json`, a constants-claims document or legacy memory pointer residue it cannot inspect or read, instead of passing as if absent. An incremental index build no longer removes a requested file it cannot stat: the removal is refused as "became unreadable", as the full walk already did. Wave 1zrak / 1zu4y.
- The upgrade dry-run migration preview no longer reports an error for targets older than 1.5.0; it evaluates history paths with the incoming framework's predicate. Wave 200xy / 200v2.
- A failure to remove an undeclared skill file now reports the repository-relative path and the error class instead of the operating-system error text. Wave 200xy / 200v2.
- Journal migration date patterns accept ASCII digits only. Wave 200xy / 200v2.
- `wf setup` no longer adds framework test files to the documentation index. Setup now resolves include prefixes the same way as every other index build, so setup and incremental refreshes agree on the corpus and a setup that follows a refresh no longer re-embeds unchanged files. A docs-only or code-only setup now gives the graph the same docs and code scope as every other build. The first index build after upgrading removes the framework test-file rows an earlier setup added; this is expected. Wave 204jj / 2038p.

## [1.28.0] - 2026-09-30

### Added

- **A distribution can serve Wavefoundry tools under its own names.** The extension declaration in `mcp_tool_extensions.py` gains `EXTENSION_TOOL_ALIASES` (extra served names), `EXTENSION_HIDDEN_TOOLS` (canonical names that are not served) and `EXTENSION_REPLACEMENTS` (a core name reused by an extension handler with a different schema, with the core behaviour kept under another name). An alias is a copy of the tool as served, so the lifecycle lock, the upgrade publication guard and cost accounting keyed on the canonical name apply to it. The core behaviour of a replaced name is wrapped separately under the core name, and the replacing handler neither triggers the core's argument-parsing extractors nor has its own hints rewritten. `next_tools`, `usage` and diagnostic recovery hints name the served tools; prose keeps canonical names, and `wf_server_info` publishes the canonical-to-served map. The permission allowlist includes aliases at their tier and omits hidden names. An invalid declaration refuses startup and leaves only runner tools served. The shipped declarations are empty and change nothing. Wave `1z8oz`.
- **Record vocabulary profiles.** What the record markers are called now lives in one place, the new `vocabulary_profile.py` module: the record file name (`wave.md`), the `wave-id` key, the record title, the `## Wave Summary` and `## Changes` headings, the `Change ID` and `Change Status` labels and the `Wave:` back-reference, plus the tier names. A downstream distribution renames them by editing those constants at merge time, the same way it relocates record roots in `record_paths.py`; nothing is read from configuration, and an invalid profile refuses to import with a message naming the field. Every reader and writer uses the profile (discovery, docs-lint, the lifecycle tools, review evidence, memory, the dashboard, the review-policy digest and the Claude Stop hook), and new change documents get the profile's labels. The shipped defaults are today's names, so nothing changes unless a distribution edits them. Run **Upgrade Wavefoundry** (or `wf render-surfaces`) to re-render the Stop hook. Wave `1z8mm`.
- **Record labels may share a prefix.** A vocabulary profile may use labels that are prefixes of one another, such as `Wave`, `Wave ID` and `Wave Status`, because every label is written and read as `Label:` at the start of a line; every reader matches a label only at the start of a line, and a census test keeps it so. The profile refuses duplicate labels, including ones that differ only in case, and a label that differs from a fixed label only in case (for example `status`). The shipped labels are unchanged. Wave `1z8ou`.
- **A read-only archive of older records.** A distribution that renames its record vocabulary can keep its closed records, under their old names, in an archive: set `ARCHIVE_ROOT` in `record_paths.py` and, when the names differ, `ARCHIVE_PROFILE` in `vocabulary_profile.py`. `wf_get_change` and the dashboard document view find archived waves and changes by id (marked archived), and new ids never collide with archived ones. Nothing writes to the archive: lifecycle tools refuse an archived id with `archived_record_read_only`, the docs gardener skips it, and docs-lint checks only that archived records can be read. Both constants are unset by default, so nothing changes unless a distribution sets them. Wave `1z8ts`.
- **Memory backfill reads archived waves.** With a read-only archive configured, memory backfill now inventories and drafts from its closed waves, read with the archive's vocabulary, and writes nothing there; `memory_propose` also accepts an archived wave id. If an archived wave has the same id as a live one, the live wave is used and backfill reports `archived_wave_shadowed`. Nothing changes without an archive. Wave `1z8tz`.
- **A warning when no wave record can be found.** When the waves root holds folders with files but none contains the record file the profile names (for example after a rename), docs-lint warns and `wf_list_waves` and `wf_current_wave` add an advisory `record_file_not_found` diagnostic, instead of reporting no waves without explanation. Folders without files (empty, only subfolders, or only dot-files such as `.gitkeep`) are ignored, so a fresh install or empty grouping folders do not trigger it. Wave `1z8mm`.

### Changed

- **An upgrade or a pull now leaves the required packages installed, or says to run `wf setup`.** When missing or version-incompatible required packages are the only thing stopping the MCP server from starting (typically after a `git pull` of a teammate's committed upgrade), the server now installs them itself: exactly the reported packages, through uv with its 21-day package-age guard (never pip), into the existing tool environment, with nothing written to the MCP output stream and no repository `uv.toml` or `[tool.uv]` settings applied. Packages the server can run without, such as `psutil`, install in the background after it starts; others install before it starts, and if it still cannot start it exits with the `wf setup` guidance. `wf_server_info` reports the install as `startup_install`. One lock now serializes every change to the shared tool environment (creating or recreating it, and every dependency install by `wf setup`, the upgrade and startup); if the lock cannot be taken, nothing is installed, and a check that finds nothing to install takes no lock. The upgrade installs dependencies as its own step before the index update: a failed install is reported as `dependency_provisioning_failed` naming `wf setup`, and the index update is skipped rather than reported as a failed publication. The same handling covers the legacy storage-migration reader: when a storage migration is required and its dependencies cannot be installed, the index phase fails before anything migrates, keeps the migration receipt and legacy sources, and names `wf setup` (the resume-after-memory path no longer lets that failure escape its own handling). The cleanup summary adds `setup_status`, `setup_reasons` and `setup_command`, and when setup is not ready `wf_upgrade`'s next step recommends the command before reloading. A server running when a pull lands now says its restart will install newly required packages, and the Claude Code session-start hook says the server attempts the install. Operator notes: startup uses the network when a requirement changed, and there is no opt-out; the startup install reads the operator's user-level `uv.toml`, or the system-level one when there is none (uv would merge both); in locked-down environments the install fails within `setup.dep_install_timeout_seconds` and the server reports `wf setup`. The tool environment is shared by every repository on the machine, so two repositories on framework versions with different pins re-pin a package on each host start; on Windows a package in use by another host, an index build or the dashboard cannot be replaced, and the install says what to stop. The upgrade's separate dependency step takes effect from the upgrade after the one that installs it on the default `wf upgrade` and `wf_upgrade()` paths, and the new `wf_upgrade` next step after an MCP reload or restart. ADR `1zcxi-adr startup-dependency-install`. Waves `1zfd9`, `1zep5`.
- **Process information comes from `psutil`.** The MCP server and the indexer now read pid liveness, zombie state, command lines, working directories and start times through one module backed by `psutil`, a new required dependency (`psutil>=6.1,<8`), instead of spawning `tasklist`, `ps` and PowerShell queries. On Windows this replaces branches that had never run on a real Windows host, and process-status calls no longer spawn processes. The MCP server now treats a process it may not signal (for example another user's) as running, and a zombie as not running, like the indexer. When a process's start time can be read, a pid recorded by a build and later reused by another process no longer reads as a running build. Dashboard stop no longer deletes the dashboard's lock file: it clears the metadata in place while holding the dashboard's lock, and leaves it untouched when the lock is held or cannot be taken, so a stop racing a starting dashboard can no longer leave two dashboards running. Operator notes: the upgrade installs `psutil` as its own step, and after a `git pull` of a committed upgrade the MCP server installs it at its next start (in the background); `wf setup` also installs it. Until it is installed, readiness reports `dependencies_missing`, `index_health`, `index_build_status` and `wf_server_info` report `process_info_unavailable` recommending `wf setup`, index builds still run (the OS locks decide), and status may show a running build or dashboard as not running. An offline upgrade reports `dependency_provisioning_failed` and skips the index update until `psutil` can be installed. The upgrade that first installs this step does not have it yet: if that install fails, the upgrade completes but reports an index publication failure recommending `index_build`; follow the cleanup summary's `setup_command` (`wf setup`) instead, since `index_build` cannot install a missing package; air-gapped sites can pre-stage the wheel (for example `pip download "psutil>=6.1,<8"` into a local index). On Windows, application control must allow `psutil`'s extension in the tool environment, as it already must for `apsw` and `sqlite-vec`. A change to `process_info.py` takes effect after an MCP server restart, not `wf_reload_mcp`. Wave `1zc7n`.
- **The prompt-surface manifest no longer records a gardening date.** The docs gardener stamped `last_gardened_at` in `docs/prompts/prompt-surface-manifest.json` with the day's date whenever it stamped any other document, so the file changed on every gardening day although nothing read the date. The gardener no longer writes it and removes it from an existing manifest, so each repository sees a one-time diff that deletes that line, and afterwards the manifest changes only when its content does. Wave `1z8tv`.

### Fixed

- **`wf_upgrade` no longer reports an error after a successful upgrade.** Its automatic post-upgrade reload re-executes the server module during the call, which swapped the context variable the tool wrapper resets, so a successful upgrade or cleanup returned `Token ... was created by a different ContextVar` and agents had to read `.wavefoundry/logs/upgrade.log` to learn the outcome. The wrapper now resets the variable it set. A server running a build without the fix reports the error once, on the call that performs the reload; that reload installs the fixed wrapper, so no restart is needed. Wave `1zeyo`.
- **A crash after the docs gate is labelled as what it is and has a targeted recovery.** A failure in the `post_docs_gate` hook or the memory bootstrap used to be recorded as `failed_phase: awaiting_memory_validation`, the name of the normal historical-memory pause, and `wf_upgrade` reported it as a pre-flight failure; no targeted recovery accepted it, so only a full rerun worked. It is now `failed_phase: post_docs_gate`, `wf_upgrade` names it and points at `wf_upgrade(phase="resume_after_gate")`, and that recovery (also `wf upgrade --resume-after-gate`, and the protocol-bridge package's recovery command) re-runs the docs gate and establishes the memory checkpoint without re-extracting; if that recovery itself fails after the gate, the lock keeps the `post_docs_gate` label so the same command can be retried. When the recovery ends at the normal historical-memory pause, it records that pause the way a full upgrade does, so `wf_upgrade` reports the pause and its next step instead of an error. Index and cleanup refuse such a lock with the same pointer, and the summary reports the docs gate as passed. The recovery also accepts the label an older runner writes for the same crash (`awaiting_memory_validation` with the docs gate complete and no action-required block). `wf_upgrade` identifies the failure from the lock itself, so a server reloaded mid-upgrade still names it correctly. The new label applies from the upgrade after the one that installs it; the recovery runs new code at once. Wave `1zeyo`.
- **An upgrade driven by an older MCP server no longer crashes in the memory step.** Upgrading from 1.27 with `wf_upgrade` from a running 1.27 server failed after the docs gate with `'RecordRoots' object has no attribute 'archive'`: the upgrade's memory hook refreshed only `memory_backfill` while the old server kept its own `record_paths`. The hook now refreshes, in place and leaf-first, every pure framework module the memory bootstrap uses, so the old server's own later import of `memory_backfill` also runs consistent code; modules that hold locks or transactions are never reloaded, and exception classes keep their identity across the refresh so code that imported them by name still catches them. The review-module reloads before the docs gate refresh the same record-layout modules first. This fix is in the upgrade's extension hook, which the running upgrade loads from the new pack, so it applies to the upgrade that installs it, including from 1.27. Wave `1zeyo`.
- **The end of an upgrade no longer repeats finished steps.** The primary `wf_upgrade` call already updates the index, but its next step (and the upgrade prompt) told agents to call `wf_upgrade(phase="update_index")` again before cleanup, which re-ran the whole index update for nothing. It now goes straight to `wf_upgrade(phase="cleanup")`, calling `update_index` first only when the editing pass changed indexed files or the summary reports an index publication failure. Cleanup also no longer ends its log by telling you to run `--update-index` and `--cleanup`: a successful cleanup says the upgrade is complete and lists only the editing-pass steps still to do, and a failed one ends with its recovery instruction. The lifecycle lock file, which stays on disk by design, now records when it was released, so its PID no longer looks like an abandoned lock, and the extraction log names the pack members it withheld instead of only counting them. The shorter sequence applies once the new MCP server is loaded; the upgrade that installs it still shows the old next step, and the withheld names appear from the following upgrade, whose extraction the new runner performs. Wave `1zf1u`.
- **CoreML acceleration survives ONNX Runtime upgrades.** The compiled-model cache for the embedder and reranker was keyed only by the model file's path, so after an ONNX Runtime upgrade that splits the graph differently, the reranker loaded a stale compile, its safety probe failed with `output_features has no value for logits`, and search reranking quietly fell back to the CPU. The cache folder now carries the ONNX Runtime version and a digest of the model graph and CoreML options, so a runtime or model change compiles fresh (once, on the first search or index after upgrading), and superseded compiles for that model are removed, which on an affected Mac frees several hundred megabytes. Removal never follows symlinks or leaves the model's cache folder. Other GPU providers and the CPU path are unchanged. Wave `1zf1w`.
- **The upgrade guidance says when a reload is not enough.** An in-process reload (`wf_reload_mcp`, or the reload `wf_upgrade` runs automatically) re-executes only the implementation module and re-registers the tools; modules the server already imported for indexing, storage, setup and models keep the version the host started with, so the process can run a mix of old and new code. The upgrade prompt used to say ordinary upgrades need only the reload and pointed at `runner_stale`, which covers just `server.py` and `venv_bootstrap.py`, so a `loaded_code_stale` warning after an upgrade read as noise. The prompt and the cleanup next step now say that `loaded_code_stale` after an upgrade means restart the host. The warning also no longer counts the implementation module itself once a reload has re-executed it, so an upgrade that changed only that module no longer asks for a restart; this part takes effect after the first restart onto this release. Wave `1zf1y`.
- **Code navigation tools no longer read files the index excludes.** When the server could not load the indexer module (for example while an upgrade was replacing it), the tools that walk the working tree (such as `code_list_files`, `code_keyword`, `code_constants`, `code_pattern`, `code_definition`, `code_references` and `code_impact`) fell back to walking every file under the repository, so they listed virtual environments, build output and ignored files, and `code_constants` could return raw bytes from `index.sqlite`. They now keep using the indexer the server already loaded; if the server never loaded one, the tool returns a `navigation_indexer_unavailable` error that says to restart the MCP server. When the index code on disk has changed since the server started, the answer carries an `index_runtime_stale` warning: `wf_reload_mcp` does not load new index code, so restart the server. Wave `1za2y`.
- **`**/` in a navigation glob matches files at every depth.** `code_list_files`, `code_keyword`, `code_constants` and `code_pattern` matched globs with `fnmatch`, where `**/` needs at least one directory, so `**/*.py` skipped top-level files and `src/**/*.py` skipped files directly in `src/`. `**/` now also matches no directory. Globs without `**/` match as before. Wave `1za2y`.
- **`index_build_status` no longer reports a finished background build as running, and checking status no longer releases a build's lock.** The background build was reported `running` whenever the pid in `background-build.pid` was alive, including a finished but unreaped child or a pid now used by another program; it is now `running` only while that pid is an index build or a `wf setup` / `wf update-indexes` run for this repository. When the MCP server itself held the index build lock (the `fts` rebuild or `index_optimize`), a status check in the same process opened the lock file, which releases a POSIX record lock, so another build could start alongside it. The server now records its own holds in memory, answers `lock.held: true` from that record without opening the file, and refuses a second in-process build. A build that finds a stale lock file now reuses it and rewrites its metadata instead of deleting it first; the deletion raced another build that had just locked the old file, so a third could lock a new file and run alongside it. When the setup process is running but not holding the lock, a `state_note` says `lock.held` is authoritative. When the recorded lock owner is an earlier build or cannot be identified, the conflict message now names `index_build_status` `lock.held` as the check. Wave `1za2y`.
- **The `tags` filter on `docs_search` and `code_search` works again.** Since 1.4 (the move to stored tag filtering), no indexed chunk carried tags, so filtering by `wave`, `agent`, `test` or any other tag returned nothing. The indexer now tags each chunk from its path, following the configured waves root and the archive root, and `memory` is listed in the vocabulary. Operator note: the next index refresh after upgrading re-chunks every file once to add the tags; embeddings are reused, so nothing is re-embedded. If you later change `WAVES_ROOT` or `ARCHIVE_ROOT` without moving files, run `index_build(mode='rechunk')` to re-tag. Wave `1z8tz`.
- **Review ledgers under relocated or nested record roots stay out of retrieval.** Retrieval recognized a wave's `events.jsonl` ledger only at `docs/waves/<wave>/events.jsonl`, so with relocated or nested record roots the raw ledger was indexed as ordinary content. It now uses the configured waves root and depth. Wave `1z8mm`.
- **Fresh installs can start the MCP server again.** `mcp` 2.x (published 2026-07-28, now past setup's 21-day package-age guard) removed `mcp.server.fastmcp`, so a new `wf setup` installed an `mcp` the server could not import. `mcp[cli]` is now pinned below 2 in the setup requirements and `pyproject.toml`; an environment that already installed 2.x is reported as needing setup, and `wf setup` reinstalls a 1.x release. Wave `1z822`.
- **Seed and framework edit gates work with absolute paths.** The rendered edit hooks compared the host's path with repo-relative prefixes, and Claude Code always sends absolute paths, so on Claude Code the seed and framework-maintenance gates never blocked and the post-edit docs-lint never ran; `..`, `./`, symlinks and case variants slipped past on every host. Every hook now resolves the path against the repository first (case-insensitively where the filesystem is), and a path outside the repository is ignored. Operator note: the gates now block edits they silently allowed before; open them with `wf_open_gate` as the message says. Run **Upgrade Wavefoundry** (or `wf render-surfaces`) to re-render the hooks. Wave `1z822`.
- **Pre-edit hooks fail closed.** A Claude PreToolUse, Copilot pre-tool-use or Windsurf seed-protect hook that could not start (missing `CLAUDE_PROJECT_DIR`, or a hook body that raised) exited 1, which hosts treat as a warning, so the edit went through. They now exit 2 and block it; post-edit, Stop and SessionStart hooks keep exit 1. Post-edit hooks also mark the reindex before reporting a docs-lint failure or a Cursor warning, so an edit that fails lint is still indexed. Wave `1z822`.
- **Lock files never follow a symlink.** A symlink committed at a Wavefoundry lock path could make a lock or metadata write truncate the file it pointed to. Lock carriers are now opened without following a final-component symlink (on Windows, a symlink or reparse point is refused), and a dangling link is refused instead of creating its target. Wave `1z822`.
- **Timed-out helpers end their whole process tree.** A sensor or MCP helper that timed out had only its direct child killed; a grandchild kept running and, on Windows, could hang the call on pipes it held. Timed sensors and helper subprocesses now start in their own process group and the whole group is ended on timeout. Wave `1z822`.
- **Setup installs, upgrade hooks and the techdocs audit also end their whole process tree on timeout.** The venv, `pip` and `uv` steps of `wf setup`, upgrade convention hook scripts, the upgrade's summary child and graph-builder probe, and the techdocs audit worker killed only their direct child on timeout, so a build, resolver or hook subprocess could keep running, and on Windows the step could hang instead of timing out. They now end the whole process group, and the wait checks for Ctrl-C every half second so an interrupted `wf setup` stops promptly (the Windows behavior follows from the same design but has not been exercised on a Windows host). An upgrade from 1.27.0 keeps working: setup falls back to the previous behavior while the older upgrade runner is the one running it, and the upgrade's own steps are protected from the next upgrade on. Wave `1z8tr`.
- **Timed git commands and system probes end their whole process tree too.** The remaining timed calls to git (the dashboard's git statistics, diffs and changed-file list, the docs gardener's changed-file list, the graph indexer's ignored-path listing, the index freshness, history and drift checks, commit provenance, the techdocs baseline, operator identity, the platform-surface renderer's tracked-runtime check, the retrieval evaluator's provenance probes, the server's working-tree checks and the test runner's repository-state listing) and to system probes and process queries (`sysctl`, `ldconfig`, `nvidia-smi`, `lsof`, `ps`, PowerShell, the CoreML probe and the upgrade import probe) killed only their direct child on timeout, so a git hook or credential helper could keep running. They now end the whole process group, and fall back to the previous behavior when an older upgrade runner has loaded them. The group is signalled only while the timed-out child has not been reaped, so its id cannot have been reused by an unrelated process. The graph-quality evaluator's provenance probe (`git rev-parse HEAD` and `git status --porcelain`) is routed too, and its shipped reports were re-measured. Waves `1z8ox` and `1za2y`.
- **The framework test suite no longer writes into the repository it runs in.** A census of a full run in a clean clone found a test that updated the secret scanner's skip ledger under `.wavefoundry/index/scan/`, tests that opened the project index in place and left its SQLite `-wal` and `-shm` files behind, and Python children that wrote bytecode next to the scripts. Those tests now write under temporary roots (the index tests read a copy), and the runner sets `PYTHONDONTWRITEBYTECODE=1` for every worker. `run_tests.py` also fails a run that creates, modifies or deletes a tracked or non-ignored file, or changes the edit-gate file `.wavefoundry/guard-overrides.json`, names the paths, and writes no receipt; a concurrent edit by an operator or agent during the run trips it too. The one change it tolerates is the framework's own context-efficiency projection rewriting an open wave record during the run: a wave record whose text is unchanged once the context-efficiency and exploration-avoided blocks are removed is not a change, and an edit outside those blocks still fails. The edit-gate file is compared by content, and the repository listing is timed. Wave `1z8ox`.
- **Memory lint no longer mistakes a generated decision-log source event for a secret.** A memory record drafted from a Decision Log row whose change slug ends in a word such as `secret`, `password`, `passwd`, `token` or `api-key` failed the memory content lint, because the `:` between the change identifier and the 16-character decision hash in its `Source event:` line read as a secret assignment, and rewording the line would break its link to the source. The lint now ignores that one separator when the whole line is a generated decision-log event (a lifecycle change identifier followed by exactly 16 lowercase hex characters). Every other match on the line and in the record is still checked, including secrets inside finding identifiers and targets and anything after the closing backtick. Finding and repeated-repairs events get no exemption. Downstream repositories can remove any local exemption for this after upgrading to the release that contains this fix. Wave `1zbrr`.
- **Claude Code edit hooks cover every built-in edit tool.** The `PreToolUse` and `PostToolUse` matchers were `Edit|Write`, so `NotebookEdit` and `MultiEdit` skipped the seed and framework gates and the post-edit docs-lint and reindex. They are now `Edit|Write|MultiEdit|NotebookEdit`, and the hooks read `NotebookEdit`'s `tool_input.notebook_path`. The Claude pre-edit hook now blocks a payload it cannot inspect (empty stdin, invalid JSON, a non-object payload, or an edit tool with no recognisable path) and names the keys it looked for; other tools are still allowed. Wave `1z8ot`.
- **The Copilot pre-tool-use gate sees Copilot edits.** It read only Claude-style payload keys, so no Copilot edit reached it. It now reads Copilot CLI's `toolArgs` (a JSON string) and VS Code's `tool_input.filePath` and `tool_input.files`, and gates only Copilot's file-editing tools, so shell and read tools are never blocked, and a text-editor `view` is treated as a read; a Copilot edit it cannot inspect is blocked. The post-tool-use hook reads the same shapes. Wave `1z8ot`.
- **The Windsurf docs-lint hook reindexes.** It now triggers the debounced incremental reindex for every edit, before reporting a lint failure; it previously triggered none. Wave `1z8ot`.
- **Seed 050 states the edit gates' known limits.** Shell writes are not gated on any host, file-writing MCP tools are not gated on Claude, a path can change between the hook's check and the host's write, and a missing `python3` fails open on Claude and Windsurf. `docs/architecture/threat-model.md` points at the list. Operator note for the four entries above: run **Upgrade Wavefoundry** (or `wf render-surfaces`) to re-render `.claude/settings.json` and the Claude, Copilot, Cursor and Windsurf hooks. Wave `1z8ot`.
- **Lock files no longer follow a symlinked directory.** Wavefoundry now refuses to create or open a lock when `.wavefoundry`, or any directory under it on the way to the lock, is a symlink (on Windows, a symlink or junction). Before, a committed `.wavefoundry/locks` link put every lock and the dashboard metadata write outside the repository. The upgrade bridge follows the same rule and reports a refusal as a bridge error. OneDrive and other cloud-file directories are not affected, and the repository root and the folders above it may still be symlinks. On macOS, two processes creating the same lock file at the same moment could see a spurious "No such file or directory"; the lock open now retries it. Operator note: if you moved `.wavefoundry/index` or another folder under `.wavefoundry` with a symlink, locked operations now stop with a message naming the link; replace it with a real directory (the location is fixed). On native Windows each folder is checked just before it is created or opened, so a link swapped in during that brief window is not caught; doing that needs someone who can already write the repository. Wave `1z8ot`.
- **Wavefoundry turns off onnxruntime telemetry.** onnxruntime 1.29 and later, which a fresh install pulls in, write a device id and an event store under your home directory on import, or `:memory:.ses` in the working directory when the home is not writable. The shared bootstrap now sets `ORT_DISABLE_TELEMETRY=1` when the variable is unset or empty, which prevents this on macOS and Linux, and every onnxruntime and fastembed import also calls `onnxruntime.disable_telemetry_events()`, which disables onnxruntime's API-controlled telemetry events and is the only control on Windows. Setting `ORT_DISABLE_TELEMETRY=0` opts back in to both: the variable is kept and the call is skipped. Wave `1z8ot`.

## [1.27.0] - 2026-09-26

### Added

- **The agent is told when setup needs you, after a start or a reload.** The server already ran the `wf setup --check` assessment, but a non-ready result went only to stderr and to `index_health`, so after a reload you had to ask the agent to check. Now the next tool response carries one `setup_not_ready` diagnostic naming the reason and the recommended command, and the agent is told to report it and ask before running anything. It appears once per distinct result, only when there is something to do (so not while an index build is running). `wf_reload_mcp` also assesses setup at once and returns `setup_readiness`. The reload part lives in the runner, so restart the MCP host once after upgrading. Wave `1z2mc`.

- **Setup readiness at session start.** A Claude Code `SessionStart` hook runs the read-only `wf setup --check` assessment when a session starts or resumes. It is silent when setup is ready; otherwise it adds a short report to the agent's context naming the reasons and the recommended command, and the agent asks before running anything. Operator note: the committed `.claude/settings.json` gains a `SessionStart` entry (operator hook entries are preserved); nothing runs setup automatically and no Git hooks are installed. Existing targets receive the matching `AGENTS.md` sentence through the upgrade reconciliation pass. Wave `1yzcz`.

- **Setup baseline on upgrade and first start.** A successful upgrade refreshes the local setup fingerprint once its live readiness check passes, and the MCP server records one at startup when none exists, so a later pulled framework update is reported by `wf setup --check` and the startup notice. Operator note: installs that were only upgraded now gain a baseline, so `wf setup --check` can begin reporting `setup_inputs_changed` after a later pull; running `wf setup` clears it. Wave `1yzcz`.

- **Extension tools may use core prefixes.** A distribution can name its own tools with `wf_` or another core prefix; a distribution-specific prefix remains the recommendation. Reuse of an existing tool name still requires a declared override, and names that core treats specially, such as lifecycle-locked, cost-accounted, publication-guarded and retired tool names, stay reserved. Wave `1yyoj`.

- **Warning for inert record-layout config keys.** Docs-lint now warns, without failing, when `docs/workflow-config.json` contains `record_layout` or `wave_root`; record roots are the `record_paths` constants. Wave `1yyoj`.

- **Distribution extension tools on the one MCP server.** A downstream distribution declares its own tool modules in `mcp_tool_extensions.py` to add tools, or explicitly override existing tools under their original names, without editing core registration. Declared modules are staged and validated before anything is served, receive the same permission tiers and wrappers as core tools, reload with `wf_reload_mcp`, and appear with content hashes in `wf_server_info`; any invalid declaration refuses to serve rather than serving a partial surface. The shipped declaration is empty. Wave `1yv9l`.

### Changed

- **The acceptance-criteria locality check stays a warning.** The docs-lint check that flags an acceptance criterion asserting repository-wide state (for example "the full suite is green") remains advisory by recorded decision: in this repository its hits fell from about half of change documents before it shipped to one in 85 since, with no false positive observed. Its warning now says it is advisory by decision instead of promising a flip, and the release checklist no longer asks about sensors that carry a recorded decision; `inert_record_layout_config` is recorded the same way.

- **The MCP server implementation lives in a `wf_server` package.** `server_impl`, the tool registry and the ten handler modules moved from `.wavefoundry/framework/scripts/` into `scripts/wf_server/`. Only `server_impl` and `dashboard_handlers` keep a flat file of the same name, which resolves to the package module, so `import server_impl`, private helpers reached through it, and patches on those two flat names keep working; the server refuses to start its implementation when either flat file has been replaced by a full copy, naming the file. The other ten have no flat file: fork and extension code imports them as `import wf_server.<name> as <name>` or `from wf_server.<name> import ...`, patches `wf_server.<name>.<attr>`, and never uses `from wf_server import <name>` in code that must survive `wf_reload_mcp`. Extension override modules that import a handler module switch the same way, and fork edits to any moved module go to `scripts/wf_server/<name>.py`. The entry point `scripts/server.py` and the distribution declarations `mcp_tool_extensions.py`, `mcp_tool_roster.py` and `record_paths.py` are unchanged, and extension modules stay flat files in `scripts/`. Upgrading from 1.25 or 1.26 works with the installed upgrade runner, and an upgrade from 1.26 deletes the old flat files (1.25 never had them); restart the MCP host afterwards, because a reload on the old runner serves the new code but keeps reporting stale loaded code until restart. If an old flat file of a retired name remains (the upgrade could not prove what the previous version installed), the upgrade output and `wf_server_info` warn to delete it, because while it remains a flat import of that name loads the stale copy. `wf_server` and the twelve moved module names are reserved extension module names.

### Fixed

- **`wf.cmd` no longer tells you to diagnose Python after ordinary failures.** The Windows launcher printed its "diagnose this workstation" hint after every non-zero exit, including `wf docs-lint` finding errors and `wf setup --check` reporting that setup needs attention. It now shows the hint only when `python3` itself cannot start, and passes every command's exit code through unchanged. Run **Upgrade Wavefoundry** (or `wf render-surfaces`) to re-render the launcher.
- **Required phase sensors can run `npm`, `npx` and `pnpm` on Windows.** A list-form sensor command naming a `.cmd` wrapper failed to start, which blocked wave close. The first element is now resolved through `PATH` and `PATHEXT` on Windows. A wrapper that is only in the repository root, not on `PATH`, still needs its full path; on Windows a relative path resolves against the MCP server's working directory, not the repository.
- **The session-start hook explains an old `python3` instead of failing.** On Python 3.7 to 3.10 (Ubuntu 22.04, the macOS command-line tools) every session reported a `tomllib` import failure; it now says which Python it found and that Wavefoundry needs 3.11 or newer.
- **The setup baseline is recorded on filesystems without hard links.** On exFAT, many SMB/NAS shares and VM shared folders the baseline was never adopted and every MCP start warned about it; the create-only write now falls back to an exclusive create.
- **Blocking file locks wait on Windows as they do elsewhere.** They gave up after about ten seconds, so an index build could fail while another writer held the source guard, and the review-evidence publication lock could report itself unavailable. They now wait until the lock is free.
- **A failed Context Efficiency write is kept and retried instead of blanking the numbers.** An event whose write still fails after the busy retry is saved as one small file under `.wavefoundry/logs/context-efficiency-spool/` and replayed on the next projection-monitor tick or lifecycle boundary, so a transient failure only delays the numbers. Health reports `spooled_events` and `oldest_spooled_at` without changing its status. Closing a wave replays first; an event it still cannot write marks that wave `accounting_gap` instead of publishing an undercount. The store-wide gap is now written only when the spool itself cannot take the event. Wave `1z2ma`.
- **One lock timeout no longer blanks Context Efficiency for good.** A context-efficiency write that met a database lock held by another attached MCP server for more than 50 ms wrote the durable accounting gap at once. From then on every wave's `## Context Efficiency` showed `accounting_gap`, with no recorded cause and no supported way out. Busy and locked writes are now retried for up to 10 seconds before the write is given up (and, with the spool above, kept for later). The gap file records when and why it began, and `read_store_health` and its diagnostic report that. `wf clear-accounting-gap` clears it and keeps every wave that lived through the gap marked `accounting_gap`, so no undercount is published as complete. Wave `1z2m4`.
- **The automatic reload after `wf_upgrade` now reaches the running server.** It used to import `server.py` a second time as a new module with no handler, so it reported `handler_not_ready` and the upgraded code was not served until `wf_reload_mcp` or a restart. It now reloads the runner that is serving, and when none is loaded it says the reload was skipped and names `wf_reload_mcp`. The upgrade that installs this fix still runs the previous code, so call `wf_reload_mcp` once afterwards (or restart the MCP host).
- **Upgrade cleanup records the setup baseline even while the index is still updating.** Cleanup used to check setup readiness once; when the post-upgrade reindex was still writing, the check came back `indeterminate` and cleanup skipped the baseline with a misleading warning (the server recorded it at the next start). Cleanup now retries a transient result up to three more times over about 17 seconds, and still never fails the upgrade over it.
- **Setup no longer reports its own inputs as changed.** After an ordinary `wf setup`, `wf setup --check` and the MCP startup notice reported `setup_inputs_changed` on every run, because setup recorded a provider variable it sets in its own process. The fingerprint now compares only setup-relevant environment fields: the tool environment, the Python version and the operator's provider and reranker settings. Wave `1yzcz`.

## [1.26.0] - 2026-09-23

### Added

- **Dashboard tier labels.** The dashboard consumes `dashboard.terminology` using Wavefoundry tier keys and shows ignored keys in an advisory. Keys must be the framework tier names `wave`, `change` and `task`; a fork with its own tier vocabulary remaps its keys once when it adopts this release. Wave `1ym4h`.

- **Relocate wave and plan records in a fork.** Record roots and nesting depth are module constants a downstream fork edits at merge time; the shipped constants reproduce today's `docs/waves` and `docs/plans` layout byte for byte, and nested wave records resolve by lookup. Wave `1y0gz`.

- **Require additional review sensors per phase.** Prepare, review and close checks are named gate units in ordered per-phase lists, and a target repository can require extra named sensors through a typed `phase_gates` configuration block, with no repository code loaded by the server and nothing executed in dry-run. Wave `1y0h0`.

- **A pinned public tool surface.** Every registered MCP tool's name, roster tier, input schema and annotations are checked against a committed golden fixture by the ordinary test suite, so an unintended change to the tool surface fails a test instead of reaching a host. Wave `1y0do`.

### Changed

- **Guidance for older upgrade readers after device-number drift.** Diagnose the installed-reader failure before attempting a reviewed, operator-approved repair; preserve recovery records and stop on uncertain identity or pending recovery. No automatic repair is added. Wave `1ysyo`.

- **Prefer clearing inherited agent model pins during upgrade.** Upgrade guidance recommends removing verified framework defaults while retaining deliberate operator choices and asking about unclear provenance. The renderer continues to preserve existing headers. Wave `1ysym`.

- **Clearer review guidance and diagnostics.** Receipt rotation identifies changed policy inputs when available and reminds only lanes still carrying old readiness approvals; delivery approvals remain finding-scoped. Temporary-only evidence paths receive an advisory. Review prompts point to the shared protocol, distinguish delivery context from readiness, and require controlled comparisons for causal measurement claims. The Review wave prompt states the delivery-council gate correctly (the current receipt's delivery-council requirement, not a config flag), and the fresh-install review template now carries the phase and provenance sentences, the Truth Hierarchy and a project-specifics section. Wave `1ypxw`.

- **Implement-wave guidance and review integrity.** Dependency planning reads declared wave edges instead of prose mentions. Fresh review claims cannot reuse a prior repair context; current-authority audits preserve valid supersession and expose context history. The implementation entry prompt is shorter, retired role journals move verbatim to history, and seed guidance clarifies string-reference checks, measurement attribution and readiness. Wave `1ypy6`.

- **Handler ownership.** Context-efficiency, documentation hygiene, dashboard, edit-gate, upgrade and index responses now live in dedicated modules with unchanged MCP registration and reload support. Upgrade dashboard calls retain compatibility with older installations. Wave `1ymzq`.

- **Shared containment comparison.** Existing path guards retain their resolution and error policies while sharing a pure already-resolved comparison; the resolving utility also supports strict and symlink-component refusal modes. Wave `1ymzq`.

- **TechDocs and memory handlers in their own modules.** Responses move to `techdocs_handlers.py` and `memory_handlers.py`, with public tool registration, behavior and reload compatibility preserved. The memory CLI imports its handler module directly; lifecycle close-gate compositions stay in the server. Wave `1ymzk`.

- **Bounded readiness review and clearer Prepare diagnostics.** Readiness guidance calls for one full review, one bounded repair pass and one focused verification, then operator escalation for remaining blockers. Focused packets carry the repair diff and directly affected contracts. Prepare reports receipt-publication counts, warns about unusual churn and identifies lanes missing current readiness approvals; these diagnostics do not add a runtime round limit. Wave `1yfzu`.

- **Declared sensors bind approvals on close as well as prepare.** The readiness digest that ties declared sensors to approvals now controls both mutating phases, and two guards left defeatable by the phase-gate work are closed. Wave `1yd97`.

- **More faithful lifecycle test fixtures.** A shared helper builds declared waves through the real lifecycle producers; a census requires classification of remaining hand-built fixtures. Shared reviewer guidance requires tests to reach the claimed path and derive expectations from an independent reference. The census makes exceptions visible rather than proving their correctness. Wave `1yd24`.

- **An enumerable tool registry and one middleware chain.** The MCP server builds a runtime registry of tool specifications by introspection and applies one explicit, ordered wrapper chain, with no handler moved and the public tool surface unchanged. Wave `1y0h1`.

- **Code-navigation and graph handlers in their own modules.** The two handler families live in `codenav_handlers.py` and `graph_handlers.py`, are unit-tested without the transport, stay fresh across `wf_reload_mcp`, and the public tool surface is unchanged. Wave `1y0h2`.

- **Tidy wave folders during close.** Closure guidance distinguishes disposable scratch from durable evidence, preserves ledger references, and organizes supporting artifacts before final validation. Wave `1ykqj`.

- **Choose agent models for the assignment.** Fresh Claude wrappers omit fixed model/effort defaults; rendering preserves existing frontmatter, including operator model/effort choices and BOM-prefixed headers, and skips malformed frontmatter unchanged. Upgrade guidance calls out stale preserved tool allowlists for explicit reconciliation. Shared guidance makes delegation-time selection explicit without provider rankings or new gates. Wave `1ycrj`.

### Fixed

- **Consistent memory heading spacing.** Metadata updates preserve exactly one blank line before `## Summary`, including repeated updates, without rewriting section bodies or bulk-migrating historical records. Wave `1yq6a`.

- **Install prerequisite diagnosis and consumer validation.** Setup checks the required `python3` before mutation and preserves failure evidence; Windows users can diagnose an existing seeded checkout before MCP starts, with policy-respecting guidance. Internal documentation constants now require an explicit source-repository opt-in. Install guidance uses the existing MCP surface renderer and inventories partial prompt setup before completion. The standalone PowerShell diagnostic does not require Python or MCP, never substitutes `python.exe` for `python3`, and provides non-admin and policy-blocked IT guidance. Native Windows execution and fresh-host repair qualification are explicitly deferred to external testing after the next release. Wave `1yp0y`.

- **Provider fallback no longer silently rebuilds the corpus.** Ordinary index updates refuse a change between recorded `full` and `int8` embedding precision before embedding or changing the published epoch. The refusal identifies affected layers and directs operators to restore a compatible provider environment or explicitly request `wf setup --full`. Compatible incremental updates and fresh CPU-only builds remain supported. Wave `1yljp`.

- **Shared marker recognition.** Chunking, code navigation and legacy-section stripping share namespaces including `waveforge`, with named ends and annotated begins recognized. No chunker version bump ships with this change; existing indexes may retain old chunk output for affected files until they are edited or a full rebuild runs. Wave `1ym4h`.

- **The index survives a reboot.** Persisted storage identities no longer refuse the index, `wf setup --check` and an interrupted upgrade after the operating system renumbers a filesystem device; comparison uses the path and available inode, preserves existing recovery records and retains device values as historical evidence. Different paths or available inodes still refuse; a replacement volume reusing the same path and inode remains indistinguishable. Wave `1yja8`.

- **The server no longer races its own index builds.** Automatic document writes coordinate with active builds, and source drift triggers at most one complete re-preparation and retry. A verified precommit rollback can restore the previous complete snapshot with truthful stale-state diagnostics. Crashes, uncertain commits and postcommit failures remain fail-closed. Wave `1yj14`.

## [1.25.0] - 2026-09-17

### Added

- **See who contributed to a review.** Review records and wave summaries include contributor identity when available, without blocking work when identity cannot be resolved. Wave `1y9sv`.

### Changed

- **Match agent effort to the task.** Shared guidance helps teams choose suitable models from planning through closure, preserve handoffs across agent hosts, and keep reviews independent. Wave `1y3hb`.

- **Find useful project memories faster, even with different wording.** Memory search combines semantic and keyword matches with focused relevance checks, helping agents recall applicable lessons without filling results with weak matches. Source evidence remains available for agent review, and keyword fallback keeps search usable when semantic retrieval is unavailable. Wave `1yad2`.

- **Clear guidance for Wavefoundry’s Python tooling.** Python 3.11/3.12 remain usable, with one advisory per command or MCP startup recommending 3.13+. Setup guidance explains how to change the tooling interpreter safely without changing the host project’s application runtime requirements. Wave `1y6hg`.

- **One setup command after cloning or pulling updates.** `wf setup` reconciles local dependencies and indexes without an upgrade archive, preserves recovery data until verification, and keeps core search usable while historical memory review remains pending. `wf setup --check` and MCP notices identify when setup, a restart or recovery is needed. Wave `1y3og`.

### Fixed

- **More credible context estimates.** Binary databases and runtime files no longer inflate source-text credits. New wave summaries label the figure Estimated context avoided and explain its whole-file baseline; existing records remain readable. Wave `1yab2`.

- **Portable Windows-path regression coverage.** Developers running the framework tests on non-Windows Python 3.11 can now verify quoted, case-insensitive Windows root matching without a platform-path error. Production behavior is unchanged. Wave `1y4j8`.

## [1.24.0] - 2026-09-13

### Changed

- **One local database for search and the code graph.** Related index updates publish together, keeping search results and code relationships consistent while simplifying storage, maintenance and recovery. Wave `1xny6`.
- **Less temporary disk activity.** Index updates prepare in memory and spill to disk only for larger batches. Wave `1xny6`.
- **Preserve updated indexes across agent sessions.** Older protected processes cannot overwrite newer search or graph data; restart guidance helps bring stale sessions up to date. Wave `1xxc9`.
- **Upgrade without an intermediate release.** Existing embeddings are preserved, the graph is rebuilt from current sources, and superseded storage is reclaimed after verification. Interrupted conversions resume through the standard upgrade. Waves `1xny6`, `1xxcd`.
- **Upgrade action:** stop all hosts attached to the project when prompted, then use the supplied CLI command to continue. Waves `1xny6`, `1xxc9`.

### Fixed

- **More accurate impact analysis and call graphs.** Chained and indexed calls resolve to methods instead of similarly named fields, with uncertainty identified when a receiver cannot be resolved. Wave `1xtnr`.
- **Useful call-hierarchy navigation.** Callee locations lead to their definitions, while `call_site` shows where each call occurs in the caller. Wave `1xtnr`.
- **Reliable dashboard controls.** Start, stop and restart handle project paths containing spaces, report startup outcomes clearly, and leave unrelated processes alone. Wave `1xq4f`.
- **Targeted index updates preserve unrelated results.** Updating selected files retains the rest of the search and graph index; requests that require a full rebuild explain what is needed. Wave `1xq4f`.


## [1.23.0]

### Fixed

- **Older indexes can recover through a full storage rebuild.** Upgrades blocked by historical chunk-ID collisions can regenerate search from current project files while preserving auxiliary data and recovery copies until verification succeeds. The upgrade editing pass also brings recovery instructions into existing project prompts while preserving local customizations. Wave `1xjmm`.

- **Storage upgrades give a clear restart handoff.** The expected restart pause preserves recovery state, identifies observable Wavefoundry hosts still attached to the project, and supplies the exact CLI continuation before MCP stops. Wave `1xjmm`.

- **Reranked results on CPU no longer depend on which other results share a batch.** Without a supported GPU the reranker runs an 8-bit model whose quantized activation range was set by every passage in the batch, so a result's position could shift because of unrelated candidates in the same request. Each passage is now scored on its own, so ranking is stable and reproducible for the same query. GPU reranking is unchanged. Wave `1xhbo`.

### Changed

- **Projects use a smaller, unified local search index.** Docs and code share SQLite storage, keeping text, keyword search and vectors consistent through file changes. Standard upgrades preserve recovery data and remove retired LanceDB files only after verification. Fresh installs no longer need LanceDB. Wave close also reclaims excess graph storage without re-embedding. Scripts reading health or retrieval coverage must use `vector_rows` in place of the removed `lance_rows` field. Wave `1xjmm`.
- **Index failures explain how to recover.** Setup checks that the index sits on local WAL-capable storage. An unavailable native runtime or a failed search is reported explicitly, naming the condition rather than returning an empty result. Upgrading requires stopping old database-owning hosts when prompted; see the packaged framework README for supported binaries and filesystem requirements. Wave `1xjmm`.
- **`index_health` recommends the specific recovery each condition needs.** Missing native dependencies point at `wf setup --root .` followed by an MCP restart, a stale layer points at an incremental index update, a chunker-version mismatch points at a full rebuild, and storage or filesystem failures give recovery that preserves the existing index instead of rebuilding it. The per-condition diagnostics and the recommended next step now agree, including when several conditions apply at once. Wave `1xjmm`.
- **Graph storage converts to incremental space reclamation once.** New graph stores enable it at creation; an existing store converts during ordinary setup, upgrade, or an explicit `index_optimize`, and that first pass needs one full rewrite of the graph database. Graph rows are preserved, and nothing is re-extracted or re-embedded. Wave `1xjmm`.

## [1.22.0]

### Added

- **The Index dialog now shows lexical index statistics.** See the indexed entries,
  term occurrences, distinct terms, and FTS5 BM25 ranking alongside Semantic
  and Graph, with distinct terms also shown on the home Index tile. Cached counts keep
  dashboard refreshes lightweight; incomplete or unavailable
  statistics are clearly labeled. Wave `1xgbc` / change `1uqec`.

- **Failed upgrades retain the information needed to remove retired framework files on retry.**
  Recovery reuses the original manifest even after partial extraction, preserves project-created
  files, and refuses switching targets while recovery is unfinished. Keep the standard
  `wf_upgrade` path: this protection applies to upgrades launched with the fixed installed
  runner; the first hop into 1.22.0 still uses the older runner's retry behavior.
  Wave `1xfbh` / change `1w3bs`.

- **Planning and implementation now check understanding before dependent work.** Agents reuse
  known context, ask only consequential questions, and briefly restate intended behavior.
  Optional plan review checks the draft against the brief, helping catch misunderstandings
  without adding approval steps or extra documents. Upgrade guidance carries these changes
  into existing project prompts while preserving local customizations. Wave `1xhgc`.

- **Refresh TechDocs now recommends repairs that change the published result.** Its guidance
  explains that removing a page from navigation does not unpublish it, adding `repo_url` does not
  rewrite Markdown links, and `exclude_docs` rules have distinct file and directory precedence.
  Users can resolve publication-boundary findings without repeating ineffective configuration
  changes. Wave `1xdlx techdocs-boundary-guidance` / change
  `1w3bt-doc techdocs-boundary-remediation-guidance`.

- **Codebase maps no longer link to unpublished agent guidance.** Area-context entries show the
  complete repository-relative `AGENTS.md` path as readable text, so users can still find the
  relevant guidance without encountering broken TechDocs links. The map also explains exactly
  when it refreshes, making generated output easier to keep current. Wave
  `1vt2t techdocs-cost-ceiling-and-map-links` / change
  `1vt2s-enh codebase-map-area-agents-prose-paths`.

- **Review outputs reuse existing wave records by default.** Briefings, reviewer reports,
  rechecks and smoke-test results go through the coordinator into the existing review ledger
  and wave summary. Separate Markdown artifacts need a distinct lasting purpose or an explicit
  operator request. Wave `1x5tr` also consolidates its historical readiness reports into one
  archive with a relocation map, preserving the original evidence and immutable ledger.

- **A secrets-scanner guard skip now leaves a durable record that close surfaces.** The scanner has
  always declined to regex-scan a file that is over the size cap, carries a line over the length cap,
  has a binary extension, or starts with a NUL byte, and said so only on stderr, so a skipped `.pptx`
  reached close with no signal. Every guard skip is now published to a root-local ledger at
  `.wavefoundry/index/scan/guard-skips.json` (path, reason and detail only, never content), from
  serial and worker scans alike, and `wf_close_wave` reports the outstanding rows as
  `data.scanner_skips` on dry-run, successful create and the normal gate-error return. The rows are
  advisory: they change no finding classification and block no close. A record retires only when the
  path is later scanned in full or is confirmed absent from the filesystem; a re-skip, a cache hit, an
  unrelated scan, an allowlisted or unreadable candidate and an I/O error all retain it. A malformed
  or unreadable ledger is reported as `data.scanner_skips_error`, a persistence failure is a
  non-blocking `WARNING` that preserves the prior bytes, a path the ledger cannot name is warned once
  without vetoing the rest of the run, and when a run's observations do not reach the ledger none of
  that run's files is cached as scanned, on the indexer scan and the `wf_scan_secrets` subprocess
  alike, so the next run re-observes them. Missing or empty history means no recorded skips, not
  complete coverage. Wave `1x5tr scanner-correctness-and-visibility` / change
  `1x4om`.

- **The non-git secrets candidate walk no longer scans the index's own internals.** On a target
  without git the fallback walk fed `.wavefoundry/index/` state, locks and logs to the scanner, so
  each full scan grew the scan cache with rows for files the scanner itself produces, and two
  identical full scans disagreed about membership. The walk now shares the semantic indexer's
  machine-authority exclusions, owned by one module: the index and log prefixes, the runtime lock
  directory, the guard-override and purge-disposition records, the memory archive and pointer
  directories, the per-wave `events.jsonl` ledgers and the committed findings ledger. Two full scans of an unchanged non-git tree now record the same cache membership.
  The git-tracked candidate set is unchanged, including the wide walk that a transient `git ls-files`
  failure inside a real worktree falls back to, so the memory-archive and event-ledger prose that git
  tracks is still scanned there; on a non-git target those families are excluded by design. Wave
  `1x5tr` / change `1x550`.

- **A deferred or preserved eligibility reap is visible through the registered tools.** A build that
  defers a mass-absent reap behind the breaker, or serves a walk-shadowed subtree as of its last
  readable build, said so only in the Python build result and the logs; an agent running builds
  through `index_build` could not see either state. The build now persists both summaries in the
  index-state store, epoch-free, at every summary-carrying return (replaced on every build, removed
  when neither applies and on a full rebuild, skipped on a dry run, never failing the build), and
  `index_build_status` carries a `reap` block in every state while `index_health` carries the same
  block and raises `stranded_reap_deferred` and `stranded_reap_preserved` with the remedy for each,
  both surfaces reading the one record through one reader. Wave
  `1x6ti reap-state-visibility-and-dangling-edges` / change `1x551`.

- **A graph rebuild costs what the graph costs.** `index_build(content='graph', mode='rebuild')` took
  about 203 seconds on this repository, and 198.5 of them were a full secrets re-scan the graph had no
  reason to trigger: the build forwarded its own "rebuild the graph from scratch" flag to the scanner as
  "re-read every file", which bypassed the per-file content-hash cache. The flag is now scoped to
  docs and code rebuilds; a graph-only build takes the scanner's incremental path, where a file is
  skipped only when its content hash AND the rules fingerprint match a cached row, and the scanner's
  own escalations (a rules change, a scanner version change, a missing findings ledger) still force a
  full pass on their own. Measured on the same machine: the command went from 203 seconds to 52, the
  secrets phase from 198.5 seconds to 6.4 with 2,069 files cache-skipped. Wave
  `1x4ol index-build-cost-and-scanner-bounds` / change `1x4oj`.

- **The secrets scanner's super-linear cost is removed without changing what it detects.** The
  ruleset is Gitleaks schema written for Go's RE2, which guarantees linear time; it runs on Python's
  backtracking `re`. Eleven rules open with two nested bounded lazy spans over the same character
  class, a shape a backtracking engine explores at roughly 2,600 split points per start position, and
  one 1.15 MB identifier-dense evidence artifact cost 173.6 seconds of a 198.5 second full scan. The
  engine now collapses that exact shape to a single span of the combined width at load, in the
  RE2-to-Python shim rather than in the ruleset, so the fix survives the next upstream refresh. The
  rewrite accepts the same regular language, and that is proven rather than assumed: original and
  collapsed patterns produce identical spans and captured groups over a seeded random corpus, a
  hand-authored true-positive fixture, and every match recorded over the real repository, all frozen
  before the engine edit existed. Every file scanned before is scanned after; no time bound or skip
  condition was added. The isolated full scan went from 198.8 seconds to 18.2. The scan summary now
  names the most expensive rule per file, so the next runaway pattern is diagnosed from a report.
  Wave `1x4ol` / change `1x4ok`.

- **Machine evidence no longer crowds real architecture out of the graph report.** On this
  repository the third-largest community was 987 nodes of a single archived test-timing artifact,
  ranked alongside genuine code domains. `wf_graph_report` now classifies an artifact as a machine
  result from its own CONTENT, either explicit producer/schema provenance or a capture timestamp
  paired with a digest or a run field, and partitions those rows out BEFORE top-N selection. Five
  sections gain an exact parallel array: `communities`, `fan_in`, `fan_out`, `chokepoints`, and
  `file_hubs`. The evidence array is present and empty when nothing qualifies, including when its
  production section was not requested, so a consumer never has to tell "nothing qualified" from "an
  older build". The public `limit` applies independently to each half, `exclude_generated` does not
  erase evidence rows because the two classifications are orthogonal, and the communities stay
  queryable through `code_graph_community` with cross-boundary edges intact. Nothing is inferred
  from extension, path, size, key shape, or co-clustering, which is what keeps the rule invariant
  under moving or renaming a file. The `wavefoundry://graph/communities` catalog applies the same rule
  from the same place: architectural communities come first, Evidence/Data communities are listed last
  under their own heading with their evidence share and the reason they were classified, and their ids
  stay discoverable and queryable. That surface matters because `AGENTS.md` and the exploration seeds
  send a reader there before `code_graph_community`, so a machine artifact presented as an architectural
  domain would have survived exactly where orientation starts. Wave
  `1wpih index-quality-evaluation-and-ranking` / change `1wpie`.

- **Graph fidelity is measured instead of assumed.** `graph_quality_eval.py` scores a committed
  mixed-language corpus through a frozen relation-to-public-tool matrix, reporting per-relation true
  positives, false positives, and false negatives across `calls`, `imports`, `defines`,
  `reads_config`, and `doc_references_code`. Every scored relation must carry both an expected edge
  and a forbidden opportunity or the corpus is refused at load, because a relation with only one
  side scores vacuously. Recall gaps are declared rather than hidden: each entry in `known_gaps`
  names an edge the extractor does not currently produce and the evidence that isolated it, and the
  suite asserts the declared set equals the actual miss set exactly, so both a new miss and a
  repaired one force the list to be revisited. The runner writes an identity-bound baseline/post
  report pair: corpus digest, evaluator source, the extraction and query sources actually loaded,
  builder and schema versions, the graph input fingerprint, repository provenance, and environment.
  Evaluator identity and production identity are recorded separately, because the normal comparison
  is one instrument reading two productions and a single combined digest would hide exactly the
  difference being measured. A pair whose corpus or instrument moved reports the delta as
  unattributable rather than presenting it as a quality change. Wave `1wpih` / change `1wpie`.

- **`code_ask` says why its confidence is what it is.** The envelope carries `confidence_basis`
  alongside `confidence`: `semantic_lead`, `exact_owner`, `no_citations`, `unranked_similarity`, or
  `lexical_fallback`. It reads the LEAD citation rather than the best score anywhere in the set, so
  a strong result buried at rank seven no longer flatters the answer the response actually opens
  with. Wave `1wpih` / change `1wscp`.

- **A standing measurement sequence cannot quietly grow.** Checkpoint runs of the retrieval gate are
  now bounded in code rather than by discipline: nine named slots, each usable once, with
  per-invocation and cumulative ceilings on time, report bytes, and public calls. Every refusal
  names which ceiling it hit. Two properties are deliberate. Failed attempts consume budget, because
  a run that burned the time and the calls spent what the cap exists to bound and excluding them
  would let unfavourable runs be discarded. A damaged ledger fails closed rather than reading as an
  empty list, since "no budget consumed" is the most dangerous way to misread a corrupt record.
  Wave `1wpih` / change `1wscp`.

- **Approximate vector search is certified against exact search before it ships.** `ann_reference_eval.py`
  measures approximate retrieval against a `bypass_vector_index()` exact reference over fixed slices,
  requiring a quality gain, or neutrality inside a declared band with a real latency win, before a
  tuning value is adopted. The report binds evaluator, production, and environment identity, and a
  report whose bindings do not verify is refused rather than read. Wave `1wpih` / change `1wsc8`.

- **Acceptance criteria you can actually mark.** A criterion asserting repository-wide state, most
  often "the full framework test suite passes", measures the tree at a moment in time rather than
  the change, so marking it depends on timing and on other people's work. Seed
  `170-plan-feature.prompt.md` now teaches the local shape ("the change's own suites and every test
  it adds pass; the documents this change authors or edits validate; and no failure elsewhere is
  attributable to this change"), and `docs-lint` reports violations as advisory `WARNING:` lines
  that name the offending phrase and supply the replacement. Only change documents in a readied,
  active, or implementing wave are in scope, so closed records and parked drafts are never
  retroactively failed and an in-flight document cannot halt an upgrade. Wave
  `1wur7 evaluator-identity-and-ac-locality` / change `1wuui`.

- **Review-cycle churn controls in the seeds.** Wave `1wur7` spent five repair rounds on one
  finding because guards shipped with tests that would survive their own removal and lanes reviewed
  a tree that moved under them. Seed 209 now carries the landing rule (a guard is landed only when a
  named test fails with it deleted, with the mutant recorded before review), a frozen-tree round
  protocol with `tree_fingerprint`, `time_budget`, and `sweep_rule` briefing fields, once-per-round
  repair, external-blocker escalation, and census re-derivation; seeds 180 and 190 carry the
  implementer and close-side hooks, and the code, qa, and architecture lane seeds require a mutation
  table in every delivery report. Wave `1wuju review-churn-and-evaluator-baseline` / change `1wujr`.

- **A new docs-lint rule can no longer halt anyone's upgrade.** Sensors used to ship blocking on day
  one with no field data, so a heuristic's first false positive was a hard stop for every consumer
  holding an open wave. `wave_lint_lib/constants.py` `SENSOR_POLARITY_REGISTRY` now records each
  sensor's polarity and introducing wave; an `advisory` sensor's findings travel the `WARNING:`
  channel and surface at every lifecycle gate as `docs_lint_warning` diagnostics with
  `advisory: true`, blocking nothing, and the release checklist lists every advisory entry so each
  flip to blocking is a decided change made on evidence. Separately, a `docs_lint.py` run that exits
  non-zero without printing an `ERROR:` line now reaches every gate as one synthesized
  `docs_lint_error` instead of passing as clean. Wave `1wuju` / change `1wujs`.

- **Serialization Points scaffolds state the token grammar of both declaration forms.** A change
  document naming a review target the parser cannot read silently loses that lane: three `1wuju`
  documents and one `1wpig` document did. A declared path token needs at least one `/`, so a
  root-level file is never a token, and a bullet declares all or nothing, so one bad token turns the
  whole bullet into prose and every path beside it goes undeclared. Inside the explicit
  `**Review targets (repo-relative paths):**` block a span is kept only when
  its last segment carries an extension or the span ends in `/`; a qualifying `*` span becomes a
  phantom that matches no file and recruits only the lanes its trigger tokens carry, and any other
  `*` span turns its bullet into prose. Seeds `170`, `040`, and `160`, both plan templates, and the
  shipped Prepare lifecycle prompt now say so with the remedy, pinned against the parser in both
  forms; the parser itself is unchanged. Wave `1wybs review-churn-follow-ups` / change `1wxe6`.

- **A wave can no longer close claiming a suite it never ran.** `wf_close_wave` reads the existing
  `.wavefoundry/framework/test-cache.json` receipt and requires `result == "ok"` with an
  `inputs_hash` matching the current framework tree, reporting a missing, red, stale, or unreadable
  receipt as `framework_test_receipt_not_proven` rather than assuming green. It runs no suite and
  spawns no subprocess. Where `run_tests.py` is absent, which is every repository consuming the
  packaged framework, the check is a documented no-op that neither blocks nor claims proof. Wave
  `1wur7` / change `1wuui`.

### Changed

- **Wavefoundry's documentation makes installation and upgrades easier to follow.**
  Direct navigation links surface installation, dashboard, and release guidance. Updated
  instructions explain the first upgrade to 1.22.0 and how to check the installed dashboard
  without development-only tests, alongside an introduction to lexical index statistics.

- **Context Efficiency sections use consistent formatting in wave records.**
  New and refreshed sections keep their heading outside the managed content, matching other
  sections. Existing records remain compatible; upgrades do not bulk-reformat closed waves.
  Wave `1xgbe` / change `1xgbd`.

- **Lexical results from different tables are merged by rank, not by raw score.** BM25 is normalized
  per table, so concatenating `fts_code` and `fts_docs` hits let unrelated growth in one table
  reorder the other. Merging now uses reciprocal rank, which is scale-free, while each row keeps its
  own `bm25` so per-table diagnostics stay observable. This removes the defect structurally instead
  of compensating for it, and introduces no corpus-fitted constant that could drift. The standing
  corpus moved with it, `code_lexical` recall at 10 from 0.389 to 0.500 and nDCG at 10 from 0.255 to
  0.410 across the wave, but that corpus holds nine cases and no gain-eligible fixture, so those
  figures are recorded as non-regression evidence rather than as a measured improvement claim. The
  reason to prefer rank fusion is structural, not the deltas. Wave `1wpih` / change `1wpid`.

- **Long queries keep their most distinctive terms.** The full-text match expression is capped, and
  the cap used to take whichever terms came first, so a rare compound identifier could be dropped in
  favour of common words. Terms are now selected by distinctiveness, with snake_case compounds
  weighted highest, and emitted in their original order. Wave `1wpih` / change `1wpid`.

- **A controlled rebuild no longer invalidates evaluator comparisons.** The repository root, index
  directory, and store path bind every comparison kind, but the state-store file's device and inode
  now bind only receipts sharing one index generation. Binding the inode across generations refused
  exactly the case `cross_generation` exists to cover. Wave `1wur7` / change `1wtpl`.

- **Contended benchmark runs are caught instead of passing as clean.** Pair jitter derives from the
  warm-sample floor and median rather than `warm_p95_ms` alone, which is one near-max order
  statistic per run and blind to a floor shift. Receipts record `warm_floor_ms`, `warm_median_ms`,
  `p95_is_maximum`, and `small_sample_estimate` per tool; a pair whose floor or median moved past 5%
  is marked `pair_contended`, and a later comparison inheriting its jitter reports
  `inherited_contended_baseline` with the recovery rather than refusing. **Latency is advisory for
  every comparison kind** and routes to `operator_review_required`, since machine noise cannot be
  told from a real regression on a shared machine; retrieval-quality floors and the response-size
  ceiling stay hard. Wave `1wur7` / change `1wuuh`.

- **Receipts recorded before this release are not comparable against ones recorded after it.** The
  evaluator's own bytes bind every comparison and the new full-distribution fields are required, so
  the discontinuity is deliberate; the next wave that changes production retrieval bytes records its
  own before-receipt and after-receipt. Wave `1wur7`.

- **One quiet evaluator run is enough to set a baseline.** Requiring a pair cost two quiet-machine
  windows for every standing baseline. A receipt with no pair-derived `jitter_ratio` is now accepted
  at the existing 25% floor with `jitter_source: single_run_floor` and `contention_judged: false`,
  and the old `invalid_baseline` refusal is gone; a pair stays optional and preferred. No within-run
  jitter estimator is computed, because the recorded fixture pairs refuted every candidate at
  readiness. Floors and the response-size ceiling are unchanged. Wave `1wuju` / change `1wujt`.

- **An evaluator-only edit records no close-time baseline.** Editing the evaluator moves its
  identity but cannot change retrieval quality, so the wave that touches it used to pay for a
  quiet-machine run measuring nothing. The standing receipt simply becomes incomparable; the next
  wave that changes production retrieval bytes records a before-receipt on its pre-change tree and
  an after-receipt on its delivered tree and compares them, which in this repository is a
  `cross_generation` pair because production modules are indexed and every completed build advances
  the generation. A cross-generation comparison attributes corpus drift to the change, since the
  regression rule has no tolerance, so a `fail` is read together with the production diff between
  the two receipts' identity blocks. Wave `1wybs` / change `1wybq`.

- **Verdict-gap and install-audit hardening**: a crashed docs-lint run now reaches every gate as one
  bounded, path-free message, and the install audit's operator-facing paths are readable. The
  synthesized cause is capped at 240 characters keeping its head and tail around a marker, applied
  after the repository root is stripped; the sanitizer ignores a filesystem-root or relative root
  spelling and also strips the repr-doubled spelling a Windows traceback renders. The
  `checked_but_missing` envelope renders `expected_artifact`, `all_missing[].expected_artifact`,
  `next_action`, and its diagnostic relative to the repository root, with leading `..` segments for
  an artifact outside the repository rather than failing the audit, and `install-log-format.md` now
  names the fields the envelope actually emits. Wave `1wybs` / change `1wybr`.

- **Ranking changes now cite a repeatable retrieval benchmark.** `retrieval_eval.py` evaluates the
  public `code_ask`, `code_search`, `docs_search`, and `code_lexical` paths over a versioned
  calibration/holdout golden corpus on a generation-frozen, cached-model run, replacing the bespoke
  harnesses each change used to bring. Reports are `wavefoundry.retrieval-eval/v1` receipts bound to
  the evaluator bytes, the production retrieval modules, the index generation, the run time, and the
  effective state of every retrieval kill switch; symbol anchors score only a result whose line span
  intersects the resolved declaration. Wave `1seaw retrieval-intent-golden-queries` / change
  `1sear`.

- **`code_ask` recognizes review-shaped questions.** "Where are the biggest gaps in X" used to route
  as a mechanism question and return implementation chunks. Such questions now classify as the
  public `assessment` type: artifact anchoring is evaluated before phrase signals, an explanatory
  lead keeps a mechanism question explanatory even when an assessment noun appears later, and
  assessment routes like explanatory retrieval with one bounded derived docs query. Citations carry
  the chunk's section path in `section`. The standing gate reports assessment retrieval as a
  measured baseline weakness of the local model stack: the classification ships, but retrieving a
  findings register for a broad question does not. Wave `1seaw` / change `1seas`.

- **A question about an ignore file now cites that file first.** The seven ignore-file names index
  as line-window code units (`WALKER_VERSION` moves to 16) and a directly named path's published
  rows are injected before reranking, so asking what `.aiignore` excludes returns the file at rank
  one, mixed-case names included. Dot-directory paths anchor as whole paths while prose slash pairs
  such as "input/output" do not, and a question about the mechanism around a named file keeps the
  injection but lets reranked evidence lead. Unnamed ignore files, lockfiles, dependency manifests,
  and generated agent surfaces carry a bounded low-information down-weight, never an exclusion.
  Wave `1seaw` / change `1seas`.


### Fixed

- **Table chunks keep complete rows with their headers.** Oversized rows and headers
  stay together even above the normal 2,000-character target, including small tables
  beside a large prelude or postlude. Large surrounding prose still line-windows under
  the universal limit. An indivisible row plus headers may exceed it; when a header
  itself remains irreducible, it is emitted once with all complete rows to keep output
  linear instead of copying that header per row. Every recognized table in a section receives the same complete-row handling. Copied
  headers compact cosmetic padding without changing the first source-bearing header,
  escaped pipes or alignment. Mapped non-table wrapping drops generated-only windows
  before numbering parts. Wave `1xa00` / change `1x81x`.

> **Upgrading:** `CHUNKER_VERSION` moves to 42; eligible files re-chunk on the next index update.
> With the model and walker unchanged, content-identical chunks reuse embeddings by
> hash; only new or changed text needs embedding.

- **Links to files created later recover without editing the referring document.** Graph
  artifacts retain unresolved local targets and selectively retry when those paths become
  current, including targets with no graph node. Failed reads keep the obligation for an
  unchanged build; successful resolution stops repair rescans. Graph builder 51 refreshes
  older fragments. Wave `1x5tq` / change `1x8e1`.

- **Interrupted graph publication recovers on the next unchanged build.** A repair could
  commit its resolved links before writing the graph payload, then lose its retry trigger
  if publication failed. Idle planning now checks the same payload binding as graph
  finalization, including the merge fingerprint and file size/mtime. Missing or unbound
  payloads trigger the existing locked recovery; dry runs report that work without writing.
  Wave `1x5tq` / change `1x8e1`, delivery finding `ARCH-DEL-1`.

- **An idle dry run reports maintenance without executing it.** Drift clearing, reaping,
  healing, dirty-epoch recovery, orphan reconciliation and pending graph repair are planned
  before the unlocked dry-run return. Real idle graph repairs run under the build lock and
  epoch. Wave `1x5tq` / change `1x81w`.

- **The served graph no longer carries an edge to a node that does not exist.** When a doc that another
  doc linked to was deleted, the first build pruned the link edge, and the next build that did not touch
  the linking doc brought it back with no target node, where it stayed until a full rebuild; a doc left
  unread behind a permissions outage did the same with its mention of a symbol renamed during the
  outage. The merge now drops, at payload assembly, every edge whose endpoint is neither a node, nor an
  unresolved `external::` id, nor a current path of the build, nor (under a directory the walk could
  not read this build) an endpoint whose edge the last published payload served, before the zero-edge doc prune, so an
  incremental build serves the same edge set as a from-scratch build for both sequences and a doc whose
  only link was deleted is pruned as a rebuild prunes it. Links to files the graph never nodes (a
  `.gitignore`, a scan-excluded doc, a memory target into `docs/waves/`) are kept; a from-scratch
  build of this repository with the filter in place dropped nothing and kept all six such edges. The
  dropped count rides the merge line as `dangling: dropped=N`. The graph builder version advances so
  persisted payloads re-extract. Wave `1x6ti reap-state-visibility-and-dangling-edges` / change `1x5pc`.

- **A transiently unreadable directory no longer deletes its subtree from the index.** `os.walk` skips a
  directory whose `scandir` fails (a permissions incident, an agent sandbox, a torn mount) without saying
  so, and every path under it read as deleted to the build: the incremental write removed its rows, the
  layer-hash commit dropped its hashes, the graph merge pruned its nodes, the eligibility reap took what
  was left, and the next readable build re-embedded the whole subtree from scratch. The walk now reports
  those directories, change detection treats the paths under them as unchanged (bookkeeping carried
  forward, nothing removed), the graph merge keeps their nodes and edges (a doc re-extracted during the outage keeps its links into them, and a symbol change elsewhere does not rescan a doc inside the unreadable directory: its stored artifact stays as it was until the doc is next re-scanned), and the reap classifies every
  stranded candidate before deleting it through the stat seam the orphan-store reconciliation already
  uses, which now shares the walk's report: absent and out-of-scope paths reap exactly as before,
  unreadable ones keep their rows and hashes, and a set of at least eight absent paths that is more than
  half a table's distinct paths defers loudly, at the zero-change preflight and the build-path seam alike,
  with the deferral and the preserved counts reported in the build result. Present-but-out-of-scope paths
  never count toward the breaker, so a scope narrowing reaps whatever its size. While the directory is
  unreadable its subtree is served as of the last readable build; a file modified or deleted inside it is
  reconciled on the first readable build, and nothing else re-embeds. Two boundaries are recorded: at the
  build-path seam the incremental write deletes a first-time mass absence (an unmounted volume on its
  first build) before the reap can judge it, and a full rebuild during the outage rebuilds from the
  current corpus and re-embeds the subtree on recovery, so the deferral message asks for the rebuild once
  the volume is readable again. Wave `1x54z eligibility-reap-absence-guards` / change `1u8o3`.

> **Upgrading:** this release moves two builder versions, the graph builder and the cluster builder. Until a
> repository rebuilds its graph index, `wf_graph_report(sections=["betweenness"])` returns
> `betweenness_artifact_stale` where it previously served rows, because the persisted centrality artifact was
> written by the older cluster builder and its ranking no longer describes the current graph. Run
> `index_build(content="graph", mode="rebuild")`, or simply let the next graph build run: the reuse gate
> falls through to a full recompute on a version mismatch, so it self-heals. Reload the MCP server after
> upgrading, since a server still running the previous code reports the older builder version and will
> disagree with the rebuilt artifact.

> **Upgrading:** the secrets scanner version moved from 1 to 2 so that the first indexed scan after this
> upgrade runs in full and records guard skips for candidates the cache had already accepted. Expect that
> one build to take the full-scan time (about 18 seconds on this repository against 6 seconds
> incremental); a target upgrading from 1.21.0 or earlier already pays that full scan for the changed
> scan rules, so the version bump adds nothing there. Guard history lives in the gitignored index
> directory: deleting `.wavefoundry/index/` or the ledger loses it until later scans repopulate it.
>
> The graph builder moves several more times in this release, so the same rebuild is what makes the new
> behaviour appear, and the last of those moves clears the dangling edges described under Fixed: the first
> graph query on a server running the new code re-extracts the graph synchronously in-process if no build
> has run since the upgrade, so reload the server and let a build run before relying on graph latency. JSON artifacts only carry their Evidence/Data classification once they have been re-extracted,
> which means `wf_graph_report` returns empty evidence arrays on a pre-upgrade graph even where machine
> results exist. External-call resolution also changes, so a repository that never rebuilds keeps the
> phantom edges described under Fixed.

- **An imported third-party call no longer binds to an unrelated project function.** When a
  qualified external target had no exact match, cross-file resolution fell back to the last segment
  alone, so `sqlite3.connect()` in `context_efficiency.py` became a call to `App.connect` in
  `dashboard.js`, a JavaScript method reached from Python. The receiver
  head is now authoritative whenever the source file explicitly imported it and the import names a
  module outside the project, the same principle the Go package-qualified branch already applied.
  The guard is deliberately narrow: an unimported head still falls back as before, and an imported
  head naming a project module also still falls back, so `from svc import loader` followed by
  `loader.load_settings()` keeps binding. Measured by rebuilding the whole repository graph on both
  sides, this removed 123 wrong edges out of 69,313, every sampled one flagrantly false: besides the
  cross-language bind above, `accel_embedder.py` calling `onnx.load()` reached a fake defined inside
  a test class, and `cli_stdio.py` calling `sys.stdout.fileno()` reached a test helper. This
  population is DISJOINT from the similarly sized one in the `1wpig` entry below: that fix stopped
  `calls` edges targeting structural JSON and YAML data nodes, while this one stops them targeting
  project FUNCTIONS through an explicitly imported external receiver. The two were measured across
  different builder versions and neither count includes the other. Wave `1wpih` / change `1wpie`.

- **The assessment prior stops inventing scores.** Re-weighting multiplied `result.get("score") or
  0.0`, which wrote `score: 0.0` onto a row the ranker never scored, presenting a number as if it
  had been produced. Rows without a score are now left alone. Ordering is unchanged either way,
  because the sort already reads a missing score as zero. Wave `1wpih` / change `1wscp`.

- **The call graph no longer claims your code calls a JSON key.** Cross-file name resolution
  rewrote an external call to the only project node sharing that simple name, whatever kind of node
  it was, so `os.cpu_count()` bound to a wave-evidence field named `cpu_count`. On this repository
  that produced 123 phantom call edges, and the largest family fused production code with evidence
  keys into a publicly ranked community. A `calls` edge can no longer target a structural JSON or
  YAML node. Node kind cannot make that distinction, since config keys are minted with the same kind
  a constructible class carries, so the rule names one predicate and adds no classifier. Wave
  `1wpig graph-correctness-and-trust-contracts` / change `1wpai`.

- **Config-read edges stop binding to schemas and test fixtures.** A JSON Schema document is no
  longer a config target, schema keywords no longer bind whether written bare or as a dotted leaf,
  and paths in a fixture tree are excluded. Declaring a schema is deliberately not treated as being
  one, because real project config files carry that key. Loader provenance stays additive rather than
  required: demanding it would have deleted the true population, whose reads are ordinary dictionary
  lookups several frames from any loader. Measured across a rebuild of both sides, false bindings
  went 64 to 0 while true bindings went 102 to 134, the increase because removing the fixture copy
  left previously ambiguous keys with a single candidate. Wave `1wpig` / change `1wpai`.

- **A filtered graph report returns as many rows as you asked for.** Filters ran on the already
  truncated rows, so a project-only request came back short, or empty. On this repository `fan_in`
  at `limit=1` returned nothing and at `limit=10` returned a single row. Eligibility now runs before
  truncation at every ranked section, including communities. Filtered centrality refills from a
  complete persisted order rather than the compatibility prefix, so `betweenness_metadata.top_n` no
  longer describes how deep the ranking went and `betweenness_served_from` says which view answered.
  Two contract changes ride along: the generated filter now reaches `file_hubs`, and centrality
  requested alongside a collapse flag is refused rather than served from the base topology. Wave
  `1wpig` / change `1wpaj`.

- **Call hierarchy entries carry their own trust evidence.** Incoming and outgoing entries now expose
  node identity, kind, relation, and confidence, so a caller can keep only trusted attribution
  classes from one response instead of making a second graph call. Wave `1wpig` / change `1wpaj`.

- **A stale centrality artifact is refused instead of served.** The betweenness serve path gates on
  the persisted cluster builder version and reports a mismatch, or a missing version, as its own skip
  reason rather than as an absent section. Wave `1wpig` / change `1wpaj`.


- **A citation's line range now contains the text it quotes.** Table row-group parts were all
  anchored at the table head, so every part after the first cited the header's lines, and a
  generated `-L{n}` id could collide with one the chunker emitted natively. Ranges are now
  splice-aware absolute coordinates carried per part, ids are resolved against the full original id
  multiset at the file boundary, and rst/adoc preambles carry per-line numbers. A census over the
  whole repository corpus reports zero wrong ranges and zero duplicate ids, against 150 collision
  groups on the same tree before the fix. Those coordinate repairs shipped in chunker version 41. Wave
  `1wpif index-content-and-retrieval-correctness` / change `1wngv`.

- **A damaged lexical index heals itself, and a query it cannot serve says so.** The FTS probe is
  now part of ordinary reconciliation and of serving. `code_lexical`, the hybrid lexical half, and
  the degraded fallbacks all serve through one chokepoint that checks a keyed integrity digest
  cached per completed epoch, so a corrupted or out-of-parity table returns a typed `query_failed`
  with a bounded, path-sanitized detail instead of quietly returning nothing. Healing executes only
  under the build lock through the ordinary rebuild path, leaving the query path free of store
  writes, and health payloads carry per-table parity state. Wave `1wpif` / change `1wpag`.

- **A busy index no longer costs you the state store.** Opening or rebuilding the store treated any
  database error as corruption and answered by deleting and recreating the file, so an ordinary lock
  wait during a concurrent rebuild destroyed a healthy store. Only a missing table, missing column,
  or unknown schema version now resets and retries; a lock or busy error is durably logged and
  re-raised with the store untouched. Wave `1wpif` / change `1wpag`.

- **Filters and per-file caps stop discarding candidates.** A language filter resolves through one
  allowlist and pushes down into both Lance and FTS, per-file caps refill over a bounded window
  sequence without re-querying an exhausted source, and every merge seam keys on the chunk id rather
  than on `(path, lines)`, so a lexical twin sharing coordinates is no longer mislabeled or dropped.
  `code_search` and `code_ask` report `retrieval_accounting` with substrate queries and examined rows
  against the stated ceiling, and an unknown language exits with zero rounds naming the language.
  The inert ANN tuning constants are retired with the defaults actually in force documented in their
  place. Wave `1wpif` / change `1wpah`.


## [1.21.0] - 2026-08-29

### Added

- **Notebook code cells are now searchable.** Code cells in `.ipynb` files previously reached
  neither retrieval table; they now route into the docs index as `doc-code` chunks with their
  cell breadcrumbs, cell ids and kernel language unchanged, outputs still never indexed. On the
  frozen notebook golden queries, recall at 5 went from 0.2 to 1.0. Wave `1wl7u
  retrieval-loose-ends` / change `1wh1b`.

- **Duplicate-titled documentation sections no longer silently lose index rows.** Sections with
  the same title in one file emitted identical chunk ids, and the id-keyed index planner kept
  only the last one. Repeats now get a `~2`, `~3` ordinal suffix while first occurrences keep
  their existing ids, across markdown (including sub-section and long-section splits),
  reStructuredText, AsciiDoc, and the HTML/XML chunkers. The `~` character cannot appear in a
  heading-derived slug, so a literal title can never collide with a generated ordinal. Wave
  `1wl7u` / change `1wh1b`.

- **Stale changelog version constants can no longer ship inside a pack.** The docs gate now
  checks version-constant claims in the `[Unreleased]` section, and the packaging gate refuses
  any build whose packed changelog section claims a `CHUNKER_VERSION`, `WALKER_VERSION`, or
  `GRAPH_BUILDER_VERSION` numeral that does not match the code, the escape path a 1.20.0 local
  pack briefly shipped through. Dated release history is never checked, so post-release bumps
  cannot block the gate. Wave `1wip2 guidance-surface-drift-guards` / `1wgwn`.

- **The seed-211 / guru.md Index Scope mirror is machine-guarded.** A byte-parity test now fails
  on any divergence between the canonical seed's Index Scope section and its hand-maintained
  `docs/agents/guru.md` mirror, and the drifted registration passages found by review are
  converged to the seed's `wf setup` wording. Wave `1wip2` / `1wgwn`.

- **draw.io and Excalidraw diagrams are now searchable.** `.drawio` files chunk one docs-routed
  label unit per diagram page (node, edge, and Edit-Data wrapper labels, both the compressed and
  plain save forms, HTML markup stripped) and `.excalidraw` files one unit of text and frame
  labels (deleted elements skipped), each breadcrumbed and filterable via
  `docs_search(kind='doc-code')`. On the frozen diagram golden set both formats went from zero
  to 1.0 recall at 5 with every query ranking its diagram first, and the existing
  Mermaid/PlantUML/DOT queries held 1.0. Raw geometry serializations are never indexed, and
  malformed or decompression-bomb inputs degrade to zero chunks behind a bounded per-page
  inflate cap that a delivered hostile fixture provably pins. Wave `1wl7w
  diagram-label-retrieval` / change `1wl7v`.

### Changed

- **Both tool-diagram extensions walk again, with value this time.** A `1wl7u` census had
  excluded `.drawio` from the walk because it shipped zero retrieval rows; with label extraction
  landed, `.drawio` and `.excalidraw` leave the generated-file exclusions as a recorded
  supersession. Across the two waves `CHUNKER_VERSION` moves to 39 and `WALKER_VERSION` to 15,
  so existing indexes converge with a one-time re-walk and re-chunk on the next index build
  after upgrade. Waves `1wl7u` / `1wl7w`.

## [1.20.0] - 2026-08-27

### Added

- **Fenced code blocks and diagrams inside documentation are now searchable.** Code examples,
  config snippets, and mermaid blocks embedded in markdown, reStructuredText, and AsciiDoc files
  previously reached neither retrieval table; they now route into the docs index as `doc-code`
  chunks with section breadcrumbs, filterable via `docs_search(kind='doc-code')`. Fence-targeted
  queries went from zero to 1.0 recall at 5 on all three formats with prose retrieval unchanged.
  Reconnect MCP hosts after upgrading: the kind filter is a tool-schema change. Wave `1wik9` /
  change `1whup`.

- **Standalone diagram files are docs-search citizens.** Mermaid, PlantUML, and Graphviz DOT
  files previously produced zero retrieval rows; each now chunks as one breadcrumbed unit whose
  node and edge labels carry the architecture prose. Diagram retrieval went from zero to 1.0
  recall at 5 on the frozen golden set. Tool-generated formats stay out. Change `1whuq`.

- **AsyncAPI, GraphQL SDL, and Protobuf join the structure-aware spec family, default-on.**
  AsyncAPI chunks at channel, operation, and message level; SDL per type and described field;
  Protobuf pairs leading comments with message, field, enum, and RPC symbols, all behind the
  same `indexing.spec_aware_chunking` gate as OpenAPI. Each format shipped on its own recorded
  measurement, and coverage differentials prove detected files lose no content. Change `1wfso`.

- **reStructuredText and AsciiDoc documentation is now searchable.** `.rst`, `.adoc`, and
  `.asciidoc` files chunk into breadcrumbed doc sections exactly like markdown, so Sphinx- and
  AsciiDoc-documented repositories get `docs_search` and `code_ask` coverage for the first time.
  Measured rst retrieval quality equals markdown; markdown chunking itself stays byte-identical,
  pinned by a differential test. Wave `1wfsl` / change `1wfsm`.

- **OpenAPI specs and JSON Schemas chunk structure-aware, default-on.** Detected specs chunk at
  operation and definition/property level with the breadcrumb baked into the embedded text.
  Recall at 5 rose from 0.833 to 1.0 on the committed golden set with zero per-query
  regressions; disable per project with `indexing.spec_aware_chunking: false`. Detection is
  guarded: config and data files that merely look schema-shaped chunk byte-identically to
  before. Change `1wfr8`.

- **A per-project re-include hatch for name-excluded files.** `indexing.walk_reinclude_filenames`
  restores exact filenames excluded by the name layer; it never overrides the binary-extension,
  content-sniff, or machine-authority exclusions. Change `1wfsn`.

- **Focused diagnostic runs for repair loops.** `run_tests.py --file <basename>` runs only the
  named test files through the same lock, timeout, and guard path as a full run and never
  touches the last-green cache. Focused runs are diagnostic only; one complete run remains the
  delivery authority.

### Changed

- **The corpus exclusion story is consolidated and the last machine-generated stragglers are
  closed.** `npm-shrinkwrap.json`, `packages.lock.json`, and minified assets no longer index,
  and the committed secret-scan findings ledger joined the machine-authority exclusions no
  configuration can re-include. `WALKER_VERSION` moved to 13 and `CHUNKER_VERSION` finishes this
  release at 37, so existing indexes converge with a one-time full re-walk and re-chunk on the
  next index build. Change `1wfsn`.

- **Operator guidance states the accurate retrieval contract.** Seed 211 and its mirrors now
  teach that the code index covers the whole repository by default, with a missing-spec
  checklist and the include-prefixes opt-in scoped to its real role: re-admitting
  `.wavefoundry/`-nested subpaths. Change `1wdvr`.

- **The framework test suite runs 37% faster with no coverage change.** The dominant test
  monolith is now a three-shard family with shared fixtures; the split preserved the exact
  frozen test identity set, proven by a mutant-checked harness. Wave `1tmtx` / change `1tm6d`.

- **The runner reports real per-file telemetry and true test counts.** Per-file timings, a
  slowest-file summary, and skip counts print on every run, and three counting defects are
  fixed, including inflated totals from tests that print runner-style lines.

## [1.19.0] - 2026-08-22

### Added

- **TechDocs publication audit, read-only.** `wf techdocs-audit` and the `wf_techdocs_audit` MCP
  tool report what the built site actually publishes: the effective page set, `nav` targets that
  are missing or excluded, dangling or boundary-escaping links, ownership of the
  Backstage/TechDocs trio, and agent startup-order integrity. Findings are data, never a gate; a
  run that could not compute something reports `degraded` rather than `clean`, symlinks escaping
  the repository are refused and named, and MCP responses are bounded with true totals. Exit
  codes follow content: `1` for any finding, `2` when the audit could not run, `0` otherwise.
  Reconnect MCP hosts once after upgrading to see the new tool. Wave `1vqqi` / change `1vmt2`.

- **Backstage catalog and TechDocs baseline, one command.** `wf techdocs-baseline` (and the
  `wf_techdocs_baseline` MCP tool) generates `catalog-info.yaml`, `mkdocs.yml`, and a landing
  page, missing-only and with conservative deny-by-default publication scope. Existing files are
  preserved byte-for-byte, generated files carry a stamp, and a mixed trio prints one warning
  naming the project-owned members. Nothing runs automatically at setup or upgrade. Wave `1vj4e`
  / change `1vj4d`.

- **Refresh TechDocs workflow and `wf-techdocs` skill.** The public shortcut runs the baseline
  and then has the technical-writer specialist author the published pages with cited facts,
  bounded by an audience invariant (agent startup-order content is framed, never removed) and a
  link-boundary rule. Fresh installs run it at the end of Phase 2; upgrades that first ship the
  seed re-render surfaces so the skill appears. Change `1vmpz`.

### Changed

- **Plan review uses the product's review vocabulary.** The optional plan stress test is now
  **Review plan** / `wf-review-plan`, with **Interrogate this plan** and **Stress-test this
  plan** as accepted aliases. Upgrade migrates recognized old prompt profiles, preserves
  project-authored prose, and fails closed on customized or conflicting copies. **Review wave**
  remains the distinct required-lane delivery review.

- **Reconciliation dispositions are finding-specific.** New `v2:` keys bind the file, retired
  surface, matched token, logical line, and nearest heading without line numbers; old keys are
  preserved but fail open and request explicit reclassification.

- **Refresh TechDocs no longer asks you to run an external renderer.** Validation is entirely
  Python and in-repo; no Wavefoundry surface requires Docker, Node, the TechDocs CLI, or MkDocs.
  One caveat for existing installs: `docs/prompts/refresh-techdocs.prompt.md` is project-owned
  after first materialization and no upgrade rewrites it, so a repository that already has the
  old copy keeps the external-renderer instructions until it reconciles the file by hand against
  the shipped seed. This is general: no upgrade overwrites an existing prompt doc, so prompt
  docs can lag the release notes; compare against the shipped seeds when behavior differs.

### Fixed

- **`nav` targets containing spaces are audited instead of dropped.** Plain, single-quoted, and
  double-quoted nav paths now yield the same target; genuinely unreadable nav shapes still
  degrade rather than being guessed at. Wave `1vvei`.

- **Council role-doc citations in freshly materialized prompt docs resolve again.** Six seed
  citations pointed at the flat `docs/agents/` layout while the framework renders those role
  docs under `specialists/`; the citations now match the shipped layout, and existing
  project-owned prompt docs are not rewritten. Wave `1vwyc`.

- **TechDocs audit patterns are faster and honest about unsupported escapes.** Redundant
  `**/` prefixes compile to one matcher, and a pattern MkDocs itself would refuse is named in
  `unsupported_patterns` instead of being guessed at. Wave `1vry5`.

- **`wf_reload_mcp` reports what actually happened to its tool-list notification.** The tool
  awaits the notification instead of reporting optimistic success. The fix lives in the
  un-reloadable runner, so it takes effect after the next full host restart. Wave `1vt2q`.

- **Fresh installs pass their own docs gate.** A new target repository no longer ends Phase 2
  with docs-lint errors to hand-repair: setup provisions the required workflow-config sections
  absent-only, the plan template is materialized from a shipped file instead of authored from
  prose, the install audit carries not-yet-existing files as `pending_lint` instead of blocking
  Phase 2 entry, shipped lifecycle prompt baselines carry lint-required metadata, and the
  install-log template drops a retired row. Existing metadata-less baselines are not rewritten
  by upgrade; add the three metadata lines by hand or delete the untouched copy and re-render.
  Wave `1viyu`.

## [1.17.1] - 2026-08-16

### Added

- **Agent-role integrity audit, advisory.** When an upgraded repository holds two live documents
  for one review-carrier role (the canonical rendered carrier plus an older repo-grown copy),
  `wf_audit` now names every contributing path, the canonical destination, and the
  merge-before-retire remediation, and the upgrade summary prints the same advisory. Read-only:
  nothing is deleted or rewritten. Wave `1vgep` / change `1vflu`.

### Fixed

- **The reconciliation scan no longer reports archived resolution rows as stale references.**
  Rows under the exact `## Resolved / closed` heading of `docs/missing-docs.md` are excluded
  structurally, fence-aware and failing toward reporting; the same text anywhere else still
  reports. Drop any stopgap `historical-record` disposition you recorded for such a row, since
  it also silences the same path in live tables. Wave `1vk4c` / change `1vk4b`.

- **`platform-mapping.md` § Skills is now specified.** Seed-050 defines the section every
  repository's prompt index already pointed at (active skill hosts, the rendered set, the gating
  rules), and the upgrade checklist re-verifies it on every upgrade. Change `1vk4a`.

- **Offline model set 3: first-lookup cache misses are gone and the one-command release path is
  restored.** Set 2 shipped one Hugging Face ref file with a trailing newline, so the first
  index build missed the installed snapshot and re-downloaded ~100 MB unpinned. Set 3 carries
  byte-identical weights and the same embedding fingerprint (no index re-embeds); ref files are
  now normalized at build, install, and attestation, and the online fallback is pinned to the
  canonical revision. Wave `1vglb` / change `1vgla`.

## [1.17.0] - 2026-08-15

### Added

- **Wavefoundry skills: the operator lifecycle is `/wf`-discoverable in skill-supporting
  hosts.** One registry renders `SKILL.md` files into each active host directory under a `wf-`
  namespace, so typing `/wf` filters the host's command list to the whole family. Twelve skills
  ship, all thin pointers to the backing `docs/prompts/` workflow docs so they cannot drift from
  the prompts that own behavior; stale pre-namespace skill files are cleaned on render with a
  symlink-containment check. Wave `1p6lp` / changes `1p6lo`, `1p6lw`.

- **New operator command: Red-team review (`Red team this`).** Runs the red-team specialist in
  isolation against one artifact with `improvement-review` as the default lens; records no
  signoffs and satisfies no gate. Change `1v877`.

- **Doc-gated skills.** A skill can require its backing prompt doc, so `wf-package` and
  `wf-code-cleanup` render only in repositories that carry the capability instead of
  everywhere. Wave `1ve3a` / changes `1vbpl`, `1ve3b`.

### Fixed

- **The `accel_embedder` docstring no longer mislabels the resident-model fallback as
  unreachable.** The branch is the live degradation route when a clean-export fetch fails;
  the docstring now says so, preventing a future cleanup from re-deriving a removal verdict.
  Comment-only. Wave `1ve3e` / change `1ve3c`.

- **Seed 160 no longer directs upgrades at agents-prompt bodies that do not exist.** The
  specialist-body list carries the directory's actual reconcile-when-present semantics and a
  ghost reference is removed. Change `1ve3d`.

- **The cleanup review distinguishes two kinds of "dead", and `code_impact` flags invisible test
  callers.** Condition-reachability claims now require enumerating every producer of the
  guarding sentinel before recommending removal, and `code_impact(include_tests=true)` attaches
  `test_callers_not_visible` when index-excluded test trees hide callers. Change `1vbut`.

### Documentation

- **The skills are documented where operators look:** README section with the full `/wf-…`
  table, prompt-index and project-overview usage notes, and seed guidance so target
  repositories' indexes carry the same note when a skill host is active.

## [1.16.4] - 2026-08-13

### Fixed

- **`wf setup` works on the supported Python 3.11 runtime again.** A nested f-string that only
  Python 3.12 accepts broke import before setup could start; the expression is resolved before
  formatting, and a regression parses the source with 3.11. Wave `1v4yf` / change `1v4or`.

## [1.16.3] - 2026-08-13

### Fixed

- **The Claude MCP registration names the server file instead of embedding an inline Python
  program.** A Git-tracked config that executes a code string is flagged by enterprise security
  tooling; `.mcp.json` now reads `"args": [".wavefoundry/framework/scripts/server.py"]`, matching
  the other host registrations. Existing repositories migrate on the upgrade that installs this;
  a non-Wavefoundry server in the same file is untouched. The server still anchors on its own
  install location, so nothing changes in how it finds your repository, and hook launchers
  deliberately keep `CLAUDE_PROJECT_DIR` for their unknown working directory. Wave `1v7a3` /
  change `1v7a2`.

## [1.16.2] - 2026-08-12

### Fixed

- **A broken review-protocol marker now fails the docs gate instead of silently freezing the
  content it guards.** Malformed marker pairs previously left role docs stuck without updates
  while lint reported ok; both marker families now share one fail-on-malformed rule, and a
  well-formed region whose content drifted from its source fails too. A repository whose markers
  are already broken will fail its next docs gate rather than pass quietly; repair the markers
  and re-render. Wave `1v4mw` / change `1v4mt`.

- **The upgrade summary reports carriers the render skipped.** `renderer_warnings` now sits in
  the structured summary and prints in the operator summary instead of hiding in stderr; unlike
  provenance flags, these do not self-heal. Change `1v4mt`.

- **A rejected CoreML probe now says why.** The warning carries the child's return code and a
  bounded, path-scrubbed stderr tail, so a field rejection is diagnosable without a
  reverse-engineering session. A passing probe stays silent. Change `1v4mu`.

- **The upgrade no longer instructs a retired step, and the reconciliation scan covers two more
  retired surfaces.** The journal-reconciliation instruction is removed, and the scan now
  reports references to the retired journal system and to `.md` prompt paths that now carry
  `.prompt.md`, resolved against your tree so genuine `.md` prompts are never flagged. Findings
  stay report-only. Change `1v4mv`.

- **The generated-surface manifest reconciles against the framework default instead of freezing
  at install time.** Entries retired from the framework no longer linger forever, and entries
  added later now reach repositories installed before they existed; operator keys the default
  does not model are untouched. Change `1v7a0`.

- **A reconciliation finding that is correct as written can be settled once.** Mark it as a
  historical record in `docs/reconcile-dispositions.json` and it stops reporting, per finding
  and keyed to the matched text, so a live stale reference in the same file still reports.
  Change `1v7a1`.

### Changed

- **The small-batch CPU routing message no longer reads like a failure.** It states that routing
  a sub-batch-sized run to the CPU embedder is an optimization and GPU use is unchanged for
  larger runs. Change `1v4mu`.

## [1.16.1] - 2026-08-12

### Fixed

- **INT8 embedding vectors no longer depend on which other chunks shared their inference
  batch.** CPU-bound hosts only: batch-wide activation scales made re-indexing unreproducible
  and encoded queries in a different regime from the bulk index. The INT8 path now encodes one
  row per call, so a vector is a function of its own text alone and query and index agree
  exactly; throughput is unchanged and peak query memory drops from ~1353 MiB to ~245 MiB.
  Upgrade cost: CPU-bound repositories re-embed both semantic layers once; GPU-class
  repositories are unaffected. Wave `1v454` / change `1v453`; ADR `1v22e`.

## [1.16.0] - 2026-08-11

### Changed

- **Retrieval uses one supplier-lineage-compliant Snowflake Arctic S embedder for documents and
  code.** CPU runs INT8, supported GPUs run FP16, and MiniLM L6 remains the reranker. Upgrades
  remove retired BAAI cache components only after the new model epoch is durable; the model
  cache is machine-global, so sibling repositories on older versions re-fetch retired models on
  their next build, and offline machines should upgrade all repositories together. Wave `1v0r0`
  / change `1v0qz`.

- **The first index build after this upgrade is a one-time full re-embed of both semantic
  layers.** The embedding fingerprint changed with model set v2; upgrades now build both layers
  in the foreground, so when the upgrade reports complete the index is fully published.

- **Review-policy receipts move to evaluator version 7, one re-Prepare in total.** This release
  carries every intermediate evaluator step, so upgrading is a single transition: any readied or
  open wave goes stale once at its next `wf_prepare_wave`, its readiness approvals are
  re-recorded, and the receipt settles. Closed waves are untouched.

- **Advancing a change's `Change Status` no longer lapses readiness approvals.** Marking a
  change complete is progress, not a contract change, so it is digest-neutral; an AC `[~]`
  deferral still lapses approvals, and close still requires the delivery approvals regardless.

- **The retrieval-posture advisory is bounded to the wave's declared files,** so unrelated
  working-tree dirt can no longer become evidence about your wave; a wave declaring no
  Serialization Points gets silence rather than guesses. **Automatic lanes are no longer
  recruited by prose that merely mentions a path**; declaring Serialization Points replaces the
  legacy fallback with exact per-path reasons, decided per document so one migrated plan never
  reduces a sibling's coverage.

### Fixed

- **`code_ask` puts an exact, source-current declaration first when a question names a known
  symbol.** Language-neutral wherever the graph provides a declaration node, and fails closed to
  ordinary retrieval when the graph is stale or ambiguous. Change `1v08v`.

- **Stale readiness approvals are refused instead of silently accepted.** Recording an approval
  after a policy input moved used to write a permanently unusable ledger record; it is now
  refused with the differing receipt fields named, recovery is one re-Prepare plus one approval
  per lane, and the close-time gate no longer weakens when an approval is absent because it was
  refused. Lapsed approvals also now name the actual failing condition instead of one generic
  reason.

- **Recordkeeping edits no longer lapse review approvals.** Whitespace normalization, newline
  style, boilerplate `## Session Handoff` bodies, and reordered `## Changes` entries are
  digest-neutral; measured across every change doc in this repository, zero review lanes were
  lost. Lane triggers also stopped depending on invisible trailing whitespace. A heading
  variant that silently re-enables digesting is now reported by name.

- **Declared review targets are parsed strictly, in both directions.** A template or scaffold
  that declares example paths is now a lint error and the upgrade fences the shipped shapes for
  you; one prose sentence in `## Serialization Points` no longer switches a document out of
  whole-document scoring (measured: 95 documents gain lanes, none lose); paths containing
  spaces are declarable without shredding into fragments that emptied the roster.

- **Unreadable records fail closed everywhere instead of crashing or weakening gates.** A change
  doc or wave record that is not valid UTF-8 now returns a named diagnostic from every lifecycle
  boundary rather than a stack trace, enumeration tools list the readable siblings with a
  per-entry error, a missing admitted document blocks close instead of vanishing from it, an
  unreadable wave record no longer drops the council-readiness requirement from the close
  roster, and the dashboard renders broken entries as degraded rows instead of crashing the
  snapshot. No message carries your absolute filesystem path.

- **The review-policy digest stops rewriting body prose it promised to leave alone.** The
  metadata carrier is bounded by a known-key allowlist, so a `Status:` line in the body can no
  longer be normalized away and hidden from the receipt.

- **Upgrade preflight fixes.** A config carrying `"wave_review": {}` upgrades again (it means
  what an absent key means); the retired-prose scan treats the whole `.wavefoundry/` tree as
  framework-owned instead of asking you to rewrite shipped files; and admitting a change fills
  an angle-bracket `<wave-id>` placeholder. On protocol-2 installs the preflight runs pre-extraction,
  so these take effect from the next upgrade after the one that installs them.

- **Diagnostics teach their own fix.** Validation errors render the valid value set from the
  same constant the check used; `wf_review_wave` accepts the `readiness`/`delivery` vocabulary;
  `wf_prepare_wave(mode='evaluate')` is documented; the dry-run preview reports a pending
  receipt mint; and `wf_mark_ac(state='~')` says when it superseded your receipt.

- **Review findings that cite code anchor by symbol.** The citation rule reaches the evidence
  record, the council seat guidance, and the runtime prepare brief; the five deliberate
  line-anchor cases stay legitimate and must be named inline. Every carrier of the rule is now
  test-pinned so a weakened copy cannot reach targets through an upgrade unnoticed.

- **docs-lint catches a rendered review-policy region that drifted from its source block,**
  compared using the renderer's own composition, closing the drift window between upgrades.

- **The upgrade's rollback-failure detail no longer embeds absolute filesystem paths,** and five
  receipt-authority documentation claims are corrected to match the code.

## [1.15.4] - 2026-08-06

### Fixed

- **Installations from 1.8.0 onward upgrade directly to the current release.** The bridge
  previously accepted only an exact 1.14.0 source; it now enforces a 1.8.0 minimum floor, so any
  supported protocol-1 installation crosses in a single run, with the same fail-closed refusals
  below the floor.

- **Admitting a change fills its `Wave:` field, and preparing a declared wave no longer demands
  legacy prose.** Scaffold placeholders are replaced with the containing wave id (never an
  operator-authored value), and readiness on declared waves derives from the typed approval
  instead of also requiring a hand-authored checkpoint verdict.

- **Upgrades reconcile all scalar docs-vs-code facts they own:** embedding and reranker model
  names plus chunker, state-store, and graph-builder versions, across extraction and
  crash-resume.

- **Routine checkbox tracking no longer reopens review; an AC deferral still does.** AC
  completion and task marks are progress-only; `wf_mark_ac(state='~')` publishes the changed
  contract and returns fresh review actions in the same operation. Wave `1uj12` / `1ulnu`.

- **Automatic review lanes come only from declared `## Serialization Points` paths, not plan
  prose,** removing false lanes triggered by quoted filenames and change ids; the wave-level
  `Requested review lanes` field is the explicit route for security and performance risks.

- **Recording a repair in `## Progress Log` no longer lapses untouched approvals.** The digest
  replaces the Progress Log body with a stable sentinel, hash-only, while every
  requirement-bearing section still lapses approvals on edit. One-time cost: the evaluator
  version bump gives every readied or open wave exactly one re-Prepare; closed waves are
  untouched. The change is server-resident and takes effect after `wf_reload_mcp` or a restart.

- **The review seeds state when an editorial finding stays inline** (a true-but-imprecise
  wording fix opens no repair cycle; a claim made false is a correctness defect) **and that the
  Progress Log narrates rather than amends**, which is what keeps the digest exclusion safe.

### Changed

- **Newly scaffolded change docs fill the AC Priority table at plan time, not at Prepare.** The
  old `(Populated at Prepare wave.)` instruction invalidated the readiness approval at exactly
  the moment it was collected; the ordering is fixed and the upgrade migrates existing plan
  templates.

## [1.15.3] - 2026-08-04

### Fixed

- **Every upgrade summary now carries the `summary_schema_version` freshness token,** including
  memory-checkpoint pauses, resumes, and ordinary cleanups, so an absent token means something
  specific instead of being routine. The token claims which code rendered the summary;
  `failed_phase` remains the success discriminator. Response bounding can never drop a present
  token; that half is server-resident and takes effect after a full host restart.

- **Four documentation surfaces no longer promise a heavier review posture than the upgrade
  configures.** They claimed enabled review maps to a full Council on every wave when it has
  been risk-tiered (`targeted`) since delivery review shipped that way; all now state the
  delivered modes, and an executable census pins the corrected claims.

- **The secrets scan no longer walks native Windows virtual environments, and neither the scan
  nor the index walks Graphify's default output directory.** The dot-prefixed `.venv/Lib` layout
  is excluded in both the allowlist and the prefilter, `graphify-out/` is pruned before descent,
  and one ordinary incremental update reaps the former paths; the exclusions stay narrow, so a
  source file like `src/graphify-output.ts` remains scannable.

## [1.15.2] - 2026-08-04

### Fixed

- **The five `integrity_checks` booleans have defined phase-aware semantics.** Seed 209 gives
  each a plain-language definition and a readiness/delivery phase rule, and both validator
  messages teach the attestation contract (affirm honestly, or do not record the claim as
  executed) instead of demanding `=true`. Wave `1uf65` / change `1uf64`.

- **The docs-constants lint states the exact one-line fix,** naming file, line, both values, and
  the change to make, so a `GRAPH_BUILDER_VERSION` bump can no longer strand a docs gate.
  Change `1uf66`.

- **A routine memory-checkpoint pause no longer prints failure prose or stamps a failure
  marker.** The runner recognizes the typed action-required pause and prints checkpoint wording
  naming `wf_upgrade(phase='resume_after_memory')`; genuine failures keep the failure report.
  The upgrade that installs this still runs the pre-fix parent once. Change `1uf67`.

- **A no-op review-policy migration no longer marks every readied wave for re-Prepare.** A
  byte-identical migrated config with zero planned edits skips the markers entirely; a genuine
  policy delta still marks every non-closed declared wave. The installing run itself still marks
  one final time; recovery stays one `wf_prepare_wave(mode='ready')` with the typed approval
  surviving. Change `1uf69`.

## [1.15.1] - 2026-08-03

### Added

- **Verified online model downloads converge with the offline model-set identity.** After a
  normal download, setup writes the same identity marker as offline materialization, but only
  when every declared file hash and revision matches; incomplete or mixed caches remain
  unmanaged. Wave `1uas8` / change `1uas7`.

## [1.15.0] - 2026-08-03

### Upgrading to 1.15.0

**From 1.14.0 or earlier** (protocol change; treat it as a short maintenance window):

1. Stop the dashboard and disconnect every attached MCP/agent host for the repository.
2. Run the upgrade with the release zip as usual; if `wf_upgrade` refuses, run the exact argv
   the refusal returns.
3. When it finishes, **fully restart every attached host**, then follow the returned recovery
   action (`resume_after_memory` if reported, then `cleanup`).

**What changes for you after upgrading:**

- `wf_review_evidence` is renamed **`wf_review_event`** (no alias), and `wf_reopen_wave` now
  requires `purpose` (`"review"` or `"implement"`). Update host permission rules that pin old
  names; the upgrade's reconciliation output lists them.
- The upgrade writes a read-only wavefoundry allowlist into your committed
  `.claude/settings.json` and names the delta; review that diff deliberately. The mutating tool
  tier stays off unless you set `wavefoundryAllowWriteTools` yourself.
- Check `wf_server_info` afterward: `runner_stale: true` means a full host restart is still
  owed.
- Offline model assets now ship separately as `wavefoundry-models-<set>.zip`, downloaded once
  per model set and hash- and license-validated before use.

### Added

- **Offline model assets are independently versioned.** The feature zip remains the sole upgrade
  input; when the pinned model set changes, `--with-models` additionally publishes the models
  zip, and upgrade and setup locate, validate, and materialize the declared set atomically.
  Wave `1u95o` / change `1uat8`. Model warm failures print the exact asset name and placement
  locations for offline recovery. Change `1ua8u`.

- **Memory maintenance has a deployable public shortcut.** **Review memories** runs reviewed
  validation, bounded consolidation, history-worthy archive, and irreversible purge with
  before/after results; purge stores only SHA-256 identities in a repo-visible disposition file
  so deleted history cannot regenerate after an index reset. Setup and upgrade migrate the
  retired pointer directory and backfill the prompt without touching project prose. Wave `1u8r2`
  / changes `1u75c`, `1u8r1`.

- **One package installs, bridges protocols, and rolls back.** The release builder emits only
  `wavefoundry-<version>.zip`; that package verifies its embedded bridge, installs protocol 2
  with rollback, and runs the feature hop in one invocation on every supported platform.
  Wave `1tz6l` / change `1txh7`.

- **Docs-lint detects orphaned review ledgers:** a non-empty `events.jsonl` whose sibling
  `wave.md` is missing or undeclared fails lint with an actionable message; empty scaffolds
  pass.

- **Memory-retrieval quality is measurable in any project.** The read-only `wf_memory_eval`
  tool runs the curated eval over the repository's own memory records, reporting aggregate
  metrics and never record bodies, and returns an explicit unavailable report when the backend
  or corpus is missing.

- **The wavefoundry MCP allowlist in `.claude/settings.json` is rendered and self-healing.**
  Install and upgrade merge the read-only tool tier into `permissions.allow` under an explicit
  provenance key, so tool renames no longer leave stale prompting rules; operator-authored
  rules, deny/ask entries, and unknown keys survive every render, and the mutating tier renders
  only when `wavefoundryAllowWriteTools` is set. Wave `1u2b0` / change `1u2az`.

### Changed

- **Each wave's `events.jsonl` ledger is the sole review-evidence authority.** On declared
  waves, every gate reads typed ledger records through one authority facade; prose signoff
  lines and stray severity words in `wave.md` are inert in both directions. Legacy waves keep
  the prose mechanism. Retired sidecars are removed one-way on upgrade with historical files
  byte-untouched; the cutover requires a full host restart, scoped to runs that actually
  crossed the boundary, and cleanup holds both publication locks through sidecar deletion.

- **`wf_review_evidence` is now `wf_review_event`** (it appends typed review events, of which an
  evidence record is only one), a clean rename with no alias; rendered surfaces reconcile
  automatically, host allowlists pinning exact names need a one-time update, and the host must
  restart to pick up the renamed surface. **`wf_reopen_wave` requires an explicit `purpose`**
  (`"review"` or `"implement"`) so pre-close reviews stop being silently attributed to
  implementation; there is no fallback.

### Fixed

- **Historical-memory publication checkpoints no longer report as `index_update` failures.** A
  ready-for-publication checkpoint retains recovery state and exits without an `ERROR`; reload
  or reconnect, then `wf_upgrade(phase='resume_after_memory')`.

- **Phase 4 index publication is no longer refused by the upgrade's own checkpoint.** Spawned
  index children now carry a value-bound publisher grant, a failed docs-layer child exit is
  reported instead of swallowed, and the refusal message states the complete recovery path.

- **The primary-phase upgrade summary is produced by the freshly extracted code** behind a
  pinned entry-point contract, so a reconciliation report can no longer be silently emptied by
  an old orchestrator unpacking newer modules; any delegation failure degrades to a marked
  in-process summary. Wave `1u5vl` / change `1u44o`.

- **The upgrade no longer extracts the release zip's installer members into the project root.**
  Extraction is allowlist-filtered to `.wavefoundry/**`, so runner members can never overwrite
  same-named project files; manual instructions now use scoped extraction. Change `1u0cc`.

- **Gardener-only dates no longer stale review-policy receipts.** The digest normalizes the
  canonical `Last verified` value; evaluator version 2 gives non-closed waves one deterministic
  re-Prepare. Change `1tz6k`.

- **Graph and sidecar stores reconcile orphaned rows on incremental builds,** with an ENOENT
  reap, a mass-removal circuit breaker, and consistent graph retirement, so out-of-band cleanup
  residue no longer survives every zero-change build.

- **A deleted living doc no longer freezes the doc-drift classifier,** and a frozen evaluation
  can no longer read as clean: `wf_audit`'s `doc_drift` now distinguishes evaluated-clean from
  stale from never-evaluated.

- **Upgrade and coherence-scan noise removed:** graph-builder version transitions no longer fail
  their own docs gate; space-containing document paths parse in drift evaluation; `.aiignore`
  stops growing two blank lines per render; pack-owned migration text is no longer flagged as
  stale tool references; MCP reload reporting distinguishes queued notification work from client
  adoption; and repair-chain guidance names the `repair_start` prerequisite and the
  implementer/reverifier split.

- **`wf_server_info` can tell a stale MCP runner from a current one.** `runner_stale` is a
  tri-state comparison of the launch-time runner hash against disk, never a fabricated value,
  so the one field whose job is to say "restart owed" can finally say it. Change `1u2ay`.

- **`wf_reopen_wave` no longer reports a focus stage it did not apply,** and memory candidates
  no longer target the test runner instead of the module a decision governs.

## [1.14.0] - 2026-07-21

### Added

- **The MCP tool surface uses subsystem-prefixed names.** Lifecycle tools are `wf_*`, memory
  tools `memory_*`, index tools `index_*`; the old `wave_` names are retired with no aliases.
  Rendered surfaces reconcile automatically; host allowlists pinning exact names may need a
  one-time update, and the host must fully restart after upgrading.

- **`wf_audit` answers instantly with a bounded index-readiness snapshot,** deferring the
  unbounded hash-walk verification to `index_health`; this removes a field-reported
  native-Windows hang on first call.

- **The review-evidence ledger has a standardized read surface.** The list event returns a
  per-record index, per-finding chain summaries composed from the close gate's own derivations,
  and approval currency, replacing hand-parsing of the ledger file.

- **Wave records render a current-state review projection:** a generated signoff table and
  finding-synthesis summary derived from the ledger, readable at a glance while `events.jsonl`
  remains the only authority.

- **Context-efficiency telemetry measures per-wave token savings end to end,** with durable
  per-wave recording, lifecycle checkpoints, and honest crediting rules; a paired-evaluation
  scaffold lets counterfactual claims graduate from estimates to measurements.

- **An in-band MCP-first retrieval directive with a measuring sensor:** every wave activation
  and review response carries the retrieval-posture rule, and a sensor flags near-zero
  retrieval telemetry against a non-trivial diff, cleared by a recorded rationale.

- **Commits trace back to their reasoning.** `code_commit_provenance` maps a commit or blamed
  line to the wave(s) that produced it and their recorded decision-log reasoning.

- **The agent memory layer supplies, validates, and populates its own records:**
  evidence-derived candidates draft conservatively, duplicate detection is diagnostic only,
  close requires explicit validation of each candidate, and historical backfill runs at install
  and upgrade with exactly-once publication protection.

### Fixed

- **Lifecycle mutations are serialized and forward-recoverable** behind an advisory
  per-repository lock, with multi-file mutations written referencing-record-last so an
  interruption converges on retry.

- **The test suite and background index builds no longer interfere:** mutual exclusion with
  atomic post-acquire rechecks in both directions, holding nothing while waiting.

- **Public search vocabularies have one source of truth:** a canonical contract module feeds
  both the serving handlers and a docs-vs-code constants lint, so documented names and versions
  fail the docs gate when they drift.

- **Silent telemetry losses repaired:** non-writing review responses record their costs,
  per-stage savings reconcile exactly with the total, and general-bucket savings survive
  restarts.

- **Memory retrieval ranking respects policy tiers:** semantic similarity tie-breaks within a
  confidence tier instead of demoting high-trust records below fresher matches.

- **Operational polish:** `memory_propose` extracts repair targets from the right fields; the
  dashboard renders multi-line ACs and current wave records; the `wf` CLI resolves its
  repository root from any cwd; fresh wave scaffolds pass docs-lint as generated; RELIABILITY
  and the performance budget cite recorded measurements with lint-bound claims; upgrades
  crossing the tool rename no longer fail at the dashboard stop; post-extraction hooks reload
  the newly extracted code; a recovered memory resume clears its own failure marker;
  publication success survives trailing index passes; and prepare-activated waves attribute
  work to the implement stage.

### Changed

- **MCP-first retrieval guidance covers the full lifecycle,** naming review verification,
  repair work, and briefed subagents explicitly.

- **`wf_sync_surfaces` reports a structured changed-file manifest** instead of an opaque render
  log; **lock files consolidate under `.wavefoundry/locks/`** with a one-way migration; and
  **short operational subprocesses are time-bounded** with truncation-flagged captured output.

## [1.13.0] - 2026-07-16

### Added

- **Java static and instance initializer blocks are now indexed as their own code chunks.** Literal-rich `static { … }` / `{ … }` bodies — message and error tables, lookup-map registration, enum bootstrap — were previously in no chunk at all and invisible to search; they are now emitted as stable, size-bounded chunks in both the tree-sitter and regex-fallback Java paths, across class/enum/record containers. Java records also become first-class in the tree-sitter path. An upgrade re-chunks the code index, reusing embeddings for unchanged chunks.

- **A prior-learning memory layer surfaces relevant lessons before risky actions.** Typed, evidence-backed memory records attached to the code graph are surfaced at action time, and retrieval is now churn-aware: index-time freshness/churn metadata and doc↔code drift detection let every retrieval response distinguish current documentation from documentation that has drifted from the code it describes.

- **Ranked search reports index freshness and degrades gracefully when the embedding model is unavailable.** `code_ask` carries an honest three-state freshness verdict computed from a cheap per-layer signal (replacing an expensive, incorrect per-question corpus walk), and semantic-path failure now degrades to full-text search with preserved filters and a uniform, typed `search_mode` / `fallback_reason` contract instead of disabling search or silently dropping filters.

- **Reviewers now verify changed work against an independent reference.** A framework-owned review protocol asks reviewers to test material claims through public paths, state transitions, and exact repair replays, and — for any changed implementation — to verify behavior against a reference that does not share the implementation's assumptions (a specification, the independently-read acceptance criteria, a materially independent implementation, or a metamorphic invariant), never relabeling implementer-authored evidence as independent approval. Executable review evidence is recorded in a typed, machine-readable event ledger.

- **Security severity now requires a grounded, attacker-reachable threat.** A conjunctive credible-threat gate drives security severity, blocking, and approval-freshness only from findings reachable under the documented threat model — cutting false-positive security escalation without weakening discovery.

### Changed

- **A single SQLite store is now the authority for semantic-index state.** `meta.json` is retired; index state lives in `index-state.sqlite` with a durable build-generation contract and reset/rebuild-or-fail semantics, while Lance remains the chunk/vector authority. Every MCP, dashboard, health, upgrade, and setup consumer reads the one authority — no dual-format fallback.

### Fixed

- **Incremental code indexing no longer freezes on hook-enabled repositories.** A content-scoped build stamped broad file hashes while embedding only its own content type, freezing the other type's index — so automatic post-edit indexing had effectively never kept the code index current, and the documented `content=code` recovery was a no-op. Change detection is now coherent under any build scope, and the automatic hook path keeps both semantic layers fresh.

- **`code_ask` no longer reports a permanent false "stale" index on repositories with a generated codebase map.** The freshness check compared recorded index state against ignore-filtered inputs, so the always-regenerated codebase map read as "gone" forever — every query reported stale and the prescribed rebuild was a no-op. The ignore filter is now applied uniformly; the fix heals an already-built index in place, no rebuild required.

- **Upgrading no longer halts at the documentation gate on freshly rendered specialist agent files.** Newly rendered specialist reviewer carriers lacked the role/category frontmatter that the same release's docs-lint enforces; the seeds now carry it and the render path injects it as a destination-aware fallback.

## [1.12.0] - 2026-07-11

### Added

- **Ranked code search gains a real lexical signal, fused with semantic retrieval.** A new SQLite FTS5 full-text layer indexes every docs and code chunk and feeds BM25 candidates into ranked retrieval before the cross-encoder rerank, closing the documented weak spots of dense-only search — exact identifiers, rare tokens, and error strings. Compound identifiers stay whole search tokens, results found by both passes carry a multi-source agreement marker, hostile query syntax degrades safely to semantic-only, and interpreters whose SQLite lacks FTS5 keep working unchanged. Codebase Q&A (`code_ask`) and code search both use it; exact keyword search is untouched.
- **A transactional state store now backs the semantic index.** One derived-only SQLite sidecar carries per-file freshness/churn data (extracted from local git history in one batched pass per build), per-path build bookkeeping with the index metadata file preserved as an exported snapshot for existing readers, a chunk registry that lets incremental builds skip reading unchanged rows entirely, and the new full-text tables. Everything in it rebuilds from the repository, git, or the vector store — a missing, corrupt, or out-of-date store is repaired automatically with no data loss, and schema upgrades never require migration steps.
- **Secret scanning remembers what it already scanned.** A per-file cache keyed on content and ruleset fingerprints skips files whose exact bytes were already scanned clean under the exact same rules — precise across branch switches, whitespace-only touches, and touch-and-revert — while a differential harness proves the cached path reports findings identical to a full scan, and any cache problem falls back to scanning everything. A repo-wide re-check that took seconds now completes in well under a tenth of one.
- **The graph tools now see classes that implement or extend third-party types.** A class whose only supertypes are external (for example an SDK interface) previously showed no inheritance relationships at all, with no signal that any existed. Impact analysis can now resolve an external interface by name and return every project class that implements or extends it as the blast radius; the implementor side reports its declared supertypes with always-on external counts; and a name shared by several distinct external types returns a grouped breakdown instead of a merged guess. Works against existing graphs immediately — no re-extraction needed.
- **One command now maintains every index.** The index-optimize tool covers the vector tables and both SQLite stores in a single pass — compaction, space reclamation, planner statistics, full-text segment merging, and a two-layer integrity check (structural soundness plus staleness against each store's source of truth) — and still runs automatically at install and upgrade. Index health reporting shows the state store's presence, schema version, and integrity verdict.
- **A new `code_lexical` tool searches the lexical layer directly.** BM25-ranked exact-token search over the same indexed full-text corpus that ranked retrieval fuses — built for exact-identifier lookups (compound identifiers, error strings, rare tokens) and for verifying what the lexical layer actually holds, with per-table coverage reporting so empty results on an unhealed store are never mistaken for absence from the corpus. Regex stays with pattern search; live-file substring match stays with keyword search. Agent guidance now also documents how to read the multi-source citation markers and why compound identifiers must be queried whole.

### Fixed

- **Ruleset changes now actually trigger the promised full secret re-scan.** The scanner's change detector hashed a rules path that never exists, leaving the primary framework ruleset outside the fingerprint entirely — so a rules update (including one delivered by upgrade) silently kept stale per-file scan decisions. The fingerprint now covers the real ruleset locations; the first scan after upgrading performs one full pass, then returns to incremental.
- **The full-text backfill now works against real vector tables (it never had).** The end-of-build reconcile that populates the lexical layer from the vector store projected a column no production table has ever carried, failed on every repository, and was silently swallowed — leaving exact-token search running on a near-empty index while health reported everything fine. The read is now schema-tolerant (absent optional columns default empty; genuinely unreadable tables still take the safe skip path), the store heals in place on the next build with no forced rebuild — including builds where no files changed, so an upgraded-but-idle repository heals too — and the one-time provisioning, repair, and skip diagnostics persist to a bounded log under the local logs directory instead of vanishing with the build process. Index health now reports per-table lexical coverage against the vector store and flags a materially under-covered index instead of reading healthy.
- **A large on-disk search-index leak is closed at its source.** The previous full-text index rebuilt itself wholesale on every build that changed a table and accumulated superseded copies that ordinary compaction could never reclaim — over a hundred megabytes of dead index data on an active repository. That engine is retired: the new lexical layer maintains itself incrementally with no version accumulation, code search's lexical half reads it directly with identical result quality on the recorded evaluation set, and upgrade automatically drops the legacy indexes and reclaims their space.

### Changed

- **Incremental index builds got faster and more crash-consistent.** Provably-unchanged files skip their vector-store reads entirely during re-chunking passes (with drift-repair paths explicitly exempted so out-of-band data loss is still healed), all derived index state commits transactionally ordered after the vector-store writes with an end-of-build reconciliation that repairs any crash window, and first builds after install or upgrade log a calm provisioning note instead of a repair warning.

## [1.11.2] - 2026-07-06

### Fixed

- **Upgrading from an older version now removes the one-time `install-wavefoundry.md` bootstrap file from the project root.** The cleanup added in 1.11.1 only ran during the extract step, which executes the previously-installed code when upgrading through the MCP server — so an upgrade from a version that predated the cleanup left the file behind, and it was cleared only on the following upgrade. The cleanup now also runs during the index-update step, which always executes the freshly installed code, so an upgrade from any prior version removes the file in the same run. The archive still ships the file at its root by design; only the extracted copy is removed.

## [1.11.1] - 2026-07-06

### Fixed

- **Upgrading from a version before 1.10.1 now provisions the collision-resistant lifecycle-ID scheme automatically.** A repository upgraded from an older version through the MCP server could silently keep minting the previous, collision-prone ID scheme, because the code that installs the new scheme was not yet running when the upgrade was orchestrated — so a manual provisioning step was required. The upgrade's index phase, which always runs the freshly installed code, now provisions the new scheme idempotently and fail-safe, so a from-old-version upgrade self-heals without any manual step.
- **Install and upgrade no longer leave the one-time `install-wavefoundry.md` bootstrap file in the project root.** The distribution ships that single-use file at the archive root so the install agent can find it before the framework is unpacked, but nothing removed the extracted copy afterward, and every upgrade re-dropped it. Install and upgrade now delete it once it has been consumed; the archive-root packaging contract is unchanged.

### Changed

- **Closing a wave now reclaims search-index storage that has grown large.** A heavy documentation session could balloon the on-disk docs index, because its full-text index accumulates stale versions that only a deep optimization reclaims — and that optimization previously ran only at install and upgrade. Wave close now runs a bloat-gated, lock-aware optimization that reclaims the leaked storage when the index has grown well beyond its expected size, and does nothing when the index is already compact. It never delays or blocks the close, and never triggers a heavy rebuild.

## [1.11.0] - 2026-07-06

### Added

- **The code graph extracts SQL far more accurately, including Oracle and T-SQL dialects.** SQL graph extraction now recovers data-manipulation edges inside procedural loop bodies (so a routine's writes are no longer lost when they sit inside a `WHILE`/`LOOP`), distinguishes foreign-key / `LIKE` / `CREATE TABLE AS` references from ordinary column-type mentions in `CREATE TABLE`, handles `CREATE TYPE`, `MERGE`, and `SELECT … INTO` (including temp-table sigils so a `#tmp`/`SELECT INTO #x` target is not minted as a permanent table), and recognizes Oracle/T-SQL forms — pseudo-types, built-in scalar types, `DUAL`, `FOR UPDATE SKIP LOCKED`/`NOWAIT`, and bracket-qualified names. Schema DDL and stored-routine bodies now produce correct nodes and edges instead of phantom or missing relations. An upgrade materializes the new extraction automatically.

### Fixed

- **The local dashboard's stop and restart work on a dead instance.** When a dashboard process exited without being reaped it lingered as a zombie that the stop/restart tools mistook for a live process and failed to clear, returning a stop failure with nothing actually stopped. The server now reaps the dashboard children it spawns — including opportunistically during ordinary editing — and classifies a recorded process with a zombie-safe check, so stop and restart reliably clear a dead dashboard and start fresh. Windows process handling is unchanged.
- **The running dashboard no longer silently stops reflecting repository changes.** Three compounding gaps could leave the page stale while the server kept serving: the single watcher thread could wedge on a slow filesystem call with no timeout, its directory-level watch missed edits to files nested inside a watched folder (the common wave-document editing pattern), and the browser had no recovery when the event stream was "connected" but no longer delivering updates. The watcher's snapshot collection is now bounded per cycle and surfaces a staleness signal on the dashboard API and event stream, change detection catches nested-file edits promptly, the client falls back to an active poll when updates stop arriving, and watcher activity is always written to `dashboard.log` so a future stall is diagnosable even under the MCP launch path.

### Changed

- **Reload the MCP server after an upgrade that changes the graph builder, or the graph is silently downgraded.** An already-running MCP server keeps the previous graph extractor in memory for its whole lifetime. An upgrade re-extracts the graph at the new version, but the first graph query on a server that was not reloaded re-extracts the graph back down to the old version using its stale in-memory extractor — reverting the upgrade's graph work. The upgrade instructions now state plainly that reloading the server (`wave_mcp_reload`) or restarting the host after a graph-builder change is mandatory before issuing graph queries, and the upgrade's own code comments were corrected to describe how the graph phase actually works (it re-extracts during the upgrade; the first-query rebuild is only a safety net).

## [1.10.1] - 2026-07-03

### Changed

- **First setup now builds the code index by default and verifies SOCKS proxy support.** `wf setup` validates the `httpx[socks]` dependency through `socksio`, builds docs and code indexes synchronously unless an explicit background-layer flag is used, and preserves the setup-selected CPU provider for accelerator prewarm/index subprocesses. Wave 1p9gr / 1p9gq.
- **FTS indexes use no-position storage with compatible query shaping.** Index rebuild and rewrite paths create FTS indexes without positional data, while docs/code query construction avoids phrase-shaped identifier searches that no-position FTS cannot satisfy. Wave 1p9jn / 1p9j1.
- **Server-side full docs-lint scans have a configurable timeout.** Lifecycle tools now use the full-scan timeout setting and return a clear validation failure on timeout instead of surfacing a raw subprocess timeout. Wave 1p9j0 / 1p9iu.

### Fixed

- **Setup fails closed when `python3` is missing or too old.** Setup now requires `python3 --version` to resolve to Python 3.11 or newer and gives repair guidance instead of implying a tool-venv MCP fallback can bypass the committed launch contract. Wave 1p9hi / 1p9hh.
- **Native Windows lifecycle paths no longer corrupt stdout or fail common process checks.** In-process server helpers keep diagnostics off the MCP JSON-RPC stdout channel, dashboard/process liveness uses Windows-safe checks, install-log reads tolerate non-UTF-8 logs, venv recreation detects failed removal, spaced dashboard roots parse correctly, line endings and cosmetic paths normalize, and server startup detects a missing venv before handshake. Wave 1p9hn / 1p9io, 1p9hi, 1p9hj, 1p9hk, 1p9hl, 1p9hm, 1p9i7.
- **Setup/index child processes are bounded and keep the operator informed.** Phase-1 setup children and model warmup paths now have per-step deadlines, no-progress watchdogs, clean timeout exits, corruption-quarantine bypass for model-warm timeouts, bounded post-EOF indexer waits, and unconditional indexer heartbeat prints during long embed/finalize phases. Wave 1p9j0 / 1p9it.
- **Rendered hooks decode host stdin as UTF-8 across host surfaces.** Generated Claude, Cursor, Windsurf, and GitHub/Copilot hooks reconfigure stdin consistently so non-ASCII file paths no longer mis-decode under cp1252-style host encodings. Wave 1p9j0 / 1p9iv.
- **Windows metadata writes and development test paths are more robust.** Atomic metadata replacement retries Windows sharing violations, rendered surfaces and secret-scan path filters keep forward-slash/line-ending behavior consistent, and the framework test runner uses a cross-platform run lock plus UTF-8 subprocess capture. Wave 1p9j0 / 1p9iw, 1p9ix, 1p9iy.
- **Change and wave lookups report ambiguous lifecycle IDs instead of silently choosing one match.** Lookup tools/resources now return candidate lists for ambiguous change or wave prefixes, keep change and wave namespaces separate, exclude `wave.md` from change lookup, and preserve token-anchored matching. Wave 1p9jn / 1p9ip.
- **Apple Silicon CoreML provider-probe temp-dir failures fall back safely to CPU.** Provider selection retries a bounded private temp-dir repair inside the probe window, records setup-cache/fresh-probe/operator-request provenance consistently, and reports recovery guidance without masking persistent CoreML failure. Wave 1p9j0 / 1p9lj.

## [1.10.0] - 2026-07-01

### Added

- **`wave_index_optimize` — reclaim on-disk index bloat without re-embedding.** The semantic index tables accumulate on-disk bloat from incremental, edit-driven refreshes (superseded data fragments, stale full-text-search artifacts, old index versions). This new tool runs a tiered ladder — compact in place; if in-place compaction fails because of a LanceDB list-column corruption, rewrite the table fresh (which recomputes offsets and sidesteps the bug) and rebuild its vector and full-text indexes; fall back to a full rebuild only if a table is entirely unreadable — reclaiming the space with no embedding cost in the common case. It also runs automatically at the end of install and upgrade. A new MCP tool requires a one-time reconnect after upgrade to appear.
- **Index size is visible in `wave_index_health`.** The health response now includes a `size` object — the total on-disk index size plus a per-component breakdown (the docs and code tables and the graph) — so index growth and bloat are diagnosable without shelling out to `du`.
- **`wave_index_build_status` reports an authoritative build-lock state.** The response now carries a `lock` object whose `held` is determined by testing the real operating-system lock (not the presence of the lock file, which persists by design as a last-owner record), plus the last build's owner and whether it finished cleanly or was interrupted. Read `lock.held` to tell whether a build is actually running — do not read the lock file.

### Changed

- **Index refreshes are coalesced to the end of a turn instead of firing on every edit.** Previously each file edit spawned a background reindex; a session of many edits churned the index — and re-grew its on-disk size — continuously. The post-edit hook now marks the index dirty and a single coalesced refresh runs when the turn ends (on hosts with a turn-end hook; other hosts use a longer debounce). The in-session staleness monitor is now a quiet-period safety net — it refreshes only once editing has settled and a recent build has not just run — so the two triggers no longer compete. A new `indexing.monitor.quiet_period_seconds` setting (default 5 minutes) tunes the safety net. Trade-off: semantic search reflects edits made earlier in the same turn only after the turn ends.
- **Embedding precision is provider-aware: half-precision on a GPU, 8-bit on CPU.** The indexer selects embedding precision from the active hardware — FP16 on a GPU/accelerator, INT8 on CPU — for faster indexing with no quality regression, and the reranker follows the same single machine classification so the two never disagree. Small incremental edit batches are routed to the CPU path to skip GPU padding waste, while full rebuilds always use the accelerator.
- **Switching machines no longer forces a needless full re-embed.** The index records the embedding precision *class* (full-precision vs. quantized), so moving a repository between a GPU and a CPU machine re-embeds only when the class actually changes, not on every provider switch.
- **Dependency sync installs pinned version bumps, not just missing packages.** Setup and upgrade now compare installed versions against the pinned specifications and install a newer pin even when the package is already present — so a bumped dependency (such as the LanceDB upgrade in this release) actually lands on upgrade instead of being skipped as "already installed."
- **Index builds self-heal corruption-driven bloat.** When in-place compaction fails because of the LanceDB list-column corruption, the build and the incremental refresh now automatically reclaim the table by rewriting it fresh — so a corrupted table recovers on the next build instead of growing unbounded.
- **Shipped agent guidance no longer references the removed framework index.** Seed prompts and rendered command docs that still described the retired separate "framework" index layer (removed when the framework's own seeds and docs were folded into each project's single index) now state the current single-index reality, so an upgrading repository's agent no longer follows stale guidance.
- **Seed prompts state the journal/persona/manifest structure contracts verbatim.** The seeds that guide an install agent to author agent journals, personas, and the prompt-surface manifest now list the exact required section headings (with case), the per-section bullet rule, the accepted salience markers, the persona `Role:`/`Category:` frontmatter, and the required manifest keys — so an agent produces a compliant artifact on the first pass instead of discovering the structure through repeated validation failures.
- **Factor-review reconciliation is self-seeding and no longer noisy on a fresh install.** A fresh install now seeds the factor-review lane set from the repository profile's applicable factors as a prunable default; and when the lane set is left empty while the profile still marks several factors applicable, the audit emits one consolidated, actionable advisory (naming the factors and the remediation) instead of a separate warning per factor on every audit. The review gate still keys off the configured lane set, not the profile.
- **The post-edit docs-lint is incremental.** Docs-lint was the last post-edit reaction that still scanned the whole `docs/` tree on every edit (the index refresh and secret scan were already incremental). The post-edit hook now self-detects the git working-tree changed set and runs only the per-file checks on changed docs; a changed config file falls back to the full lint. The authoritative full corpus lint is unchanged and still runs at prepare, close, install, and upgrade — so a large repo gets fast per-edit feedback without weakening the gate.
- **docs-lint has a configurable file-size guard.** A markdown document larger than `docs_lint.max_file_bytes` (default 5 MB, matching the secret-scan and index file caps) now has its content validators skipped with a single loud, non-blocking warning naming the file, its size, and the remedy — so a pathological multi-megabyte generated document can't stall the regex passes or balloon lint memory, while a legitimately large document never fails the gate.
- **docs-lint reads each file once per run and can report per-phase timings.** The full lint previously re-read the same doc several times (once per validator that touches it); a transparent content cache keyed on file identity removes the redundant reads. A new `--timings` flag reports per-phase wall-clock (secrets/corpus/metadata/links) to help diagnose full-scan cost on large repositories.

### Fixed

- **Index tables no longer accumulate unbounded on-disk bloat.** A full rebuild's finalize now compacts and reclaims the stale index artifacts a rebuild leaves behind (old vector/full-text index versions and data fragments), and incremental refreshes clean reliably — so the on-disk index no longer grows far past its working set over repeated builds.
- **The index-build lock correctly detects a crashed or recycled owner.** The lock's liveness check no longer trusts a bare process-exists signal (which a zombie or a recycled PID could pass), and background index builds launched by the long-running MCP server are now reaped instead of lingering as zombies — so a stale lock is reliably reclaimed on the next build and status surfaces stop reporting a dead build as running.
- **The index-build lock recovery guidance no longer tells you to delete the lock file.** The lock file persists by design as a last-owner record; the early-exit message now points at `wave_index_build_status` to check whether a build is actually running, and the "wait for the running build" case stays actionable.
- **Embedding-model downloads succeed behind a corporate TLS proxy outside of `wf setup`.** The corporate-CA trust bundle was previously applied only during setup's model prewarm; a model download triggered later — by `wave_index_build`, a background index refresh, or the first `code_search` / `code_ask` — ran without it and failed certificate verification behind a proxy. The trust bundle (with a reactive fallback ladder) is now applied at every model-download entry point, so first-use downloads succeed behind a proxy too.
- **LanceDB auto-install no longer fails behind a corporate TLS proxy.** When the indexer auto-installs LanceDB via pip on first use, it now applies the same TLS-conflict mitigation setup already used (removing the exclusive certificate-file variable and enabling native trust), so the auto-install succeeds behind a proxy instead of failing certificate verification.
- **The post-edit docs-lint gate no longer hangs or fails early on a large repository.** The docs-lint hook ran the linter unbounded (and was capped too low in an earlier build), so on a large docs tree it could stall the editing agent or reject an edit. It now runs under a generous, configurable timeout (`docs_lint.hook_timeout_seconds` in `docs/workflow-config.json`, default 120 s) and treats a timeout as advisory — the edit proceeds and `wave_validate` / wave-close remain the authoritative docs gate — so a slow lint never blocks or hangs the session.
- **The install audit no longer reports a mis-encoded install log as "complete."** When the install log was written by a non-UTF-8 tool (for example Windows PowerShell without `-Encoding utf8`), its em-dash row separators became mojibake and the parser matched zero rows — which then read as vacuously complete. The row parser now tolerates any separator encoding, the completeness check treats an empty parse as not-complete, and the audit reports a distinct "install log unparseable" error instead of silent success; new logs are written UTF-8.
- **docs-lint no longer stalls on large or link-dense documents (and behaves correctly on Windows).** The link checker called a full path-resolution (realpath) for every link in a document — O(links) filesystem syscalls — which on a link-heavy document (a generated reference, a long changelog) on a slower filesystem (Windows/WSL2/network) could take tens of seconds and trip the post-edit hook timeout. It now uses a single lightweight existence check per link (measured ~67× faster on a large synthetic document) with identical results. Separately, relative paths in lint comparisons and messages are now normalized to forward slashes on all platforms, so the historical-doc link-check skips (which used forward-slash prefixes) actually take effect on Windows and lint messages no longer show backslash paths.
- **A journal can document its own content rules without failing docs-lint.** The check that rejects pasted raw transcripts and secrets no longer fires on a line that is *forbidding* such content — a journal's Governance section naming what it disallows ("Do not include raw transcript content") now passes, while an actual pasted transcript or secret value is still caught. The validator's missing-salience-marker message also now lists the accepted marker vocabulary so the fix is obvious from the error.

## [1.9.8] - 2026-06-29

### Fixed

- **Upgrades no longer abort when a pack-search location is sandboxed.** The upgrade scans common pack-drop folders (including `~/Downloads`) for a newer release zip; on macOS a privacy-sandboxed folder made that scan raise a permission error and stop the whole upgrade. A location it can't read is now logged, skipped, and listed under `skipped_scan_locations` in the upgrade summary — so you can grant access and re-run if a newer pack lives there, while the upgrade proceeds with the best pack it could reach.
- **Shipped seeds no longer point at a wavefoundry-internal decision record.** The stage-gate guidance added in 1.9.7 referenced an internal architecture-decision file that target repositories don't have, so an upgrading project's agent could cite a missing document. The references are removed (the rationale stays inline); the stage-gate reconciliation behavior is unchanged.

## [1.9.7] - 2026-06-29

### Fixed

- **The MCP server no longer hangs on the first model-loading call.** Loading onnxruntime (for the GPU/provider probe behind `wave_gpu_doctor`, and for embedding/reranking on the first `code_search` / `code_ask` / `docs_search`) can make its native execution provider write diagnostics directly to the process's stdout file descriptor — which is the MCP JSON-RPC channel — corrupting the protocol on the first cold call after a host restart. The server now hands the protocol a private copy of stdout and points the real stdout file descriptor at the null device at startup, so no native library write can corrupt the channel; the GPU probe keeps an additional fd-level guard.
- **`uv` dependency install no longer fails behind a corporate TLS proxy.** When `SSL_CERT_FILE` pointed at a single corporate-root certificate (set so the embedding-model download trusts the proxy), `uv` treated that file as its exclusive trust anchor and rejected PyPI. Setup now runs `uv` with the certificate-file variables removed from its environment and native TLS enabled (OS trust store), and assembles a merged superset trust bundle for the certifi/requests consumers — so both dependency install and the model download succeed. The previous per-store model-download trust ladder is unchanged.
- **The runtime `.gitignore` block is written programmatically and self-heals.** The Wavefoundry runtime ignore entries (semantic index, logs, lock/state files, pack-drop archives) are now written by the surface renderer on every install / `wf render-surfaces` / upgrade, instead of relying on an agent following prose. A repository that wasn't a git repo at install time — or whose ignore step was skipped — now gets the block automatically on its next upgrade, with operator-authored entries preserved.
- **Wave-close summaries no longer show stray dashes.** A Markdown table separator row in a change doc's Decision Log no longer leaks a `--------` entry into the generated close summary's key-decisions list.

### Changed

- **Secret-scan finding IDs: the legacy `exc-###` migration was removed.** The one-release shim that auto-converted legacy `exc-###` finding IDs to the lifecycle `<prefix>-sec` form has been removed. The secrets gate keys on a finding's status, not its ID shape, so an existing ledger with old IDs still reads and gates correctly; new findings continue to mint `<prefix>-sec` IDs.
- **The stage-gate sections stay a fixed contract on upgrade.** Upgrade reconciliation now keeps the two named stage-gate sections in `AGENTS.md` (repository-code gate and product-code guard) as separate named sections rather than letting them be consolidated, because they're referenced by name across host entry docs and lifecycle prompts.

## [1.9.6] - 2026-06-29

### Fixed

- **No console windows flash on Windows.** Framework subprocesses that don't need a console — the upgrade/index/graph pipeline spawns, the dashboard server, and the rendered hook bodies — now launch via `pythonw.exe` on Windows when their output is redirected. A console-subsystem `python.exe` could still flash a window despite `CREATE_NO_WINDOW`, especially for long-running detached or rapidly-spawned processes. POSIX and the MCP server launch are unchanged.
- **The dashboard starts cleanly on Windows.** The dashboard server now launches windowless, and the start path no longer false-reports `url_not_ready` or spawns duplicates that climb ports: it reconciles an already-serving dashboard before spawning and accepts a serving dashboard by URL reachability instead of requiring an exact recorded-PID match. The Windows lifetime lock was also moved off the byte the metadata occupies, so the dashboard can publish its URL while holding the lock (Windows mandatory byte-range locking had blocked that write).
- **The dashboard renders horizontal rules.** A `---` (or `***`/`___`) separator line now renders as a horizontal rule in the dashboard's document view instead of as literal dashes.

## [1.9.5] - 2026-06-28

### Added

- **`wf gpu-doctor`.** The GPU/provider diagnostics previously reachable only through the `wave_gpu_doctor` MCP tool now have a `wf gpu-doctor` CLI subcommand, for CLI or no-MCP use. It reuses the same provider detection (no duplicated logic).

### Changed

- **`wave_upgrade` returns its structured `summary` on the primary call.** The `summary` block (versions, files pruned, docs-gate result, index state, and the retired-surface reconciliation findings) is now emitted on the primary `wave_upgrade()` response, not only on the later cleanup phase — so agents read the computed fields, including the reconciliation list, directly from the main upgrade call.
- **Retired-surface reconciliation runs on every upgrade.** The reconciliation scan (stale `.wavefoundry/bin/*` references that should now be `wf` forms) now runs on any upgrade — including patch bumps and same-version build-successors — rather than only on major/minor bumps, since a patch can change or retire a surface during testing. The scan stays report-only and exclusion-aware.
- **Secret-scan finding IDs now use the lifecycle format.** `docs/scan-findings.json` findings use lifecycle-backed `<prefix>-sec` IDs (for example `1p8l0-sec`) instead of the legacy `exc-###` sequence — new findings immediately, and existing findings are migrated once (idempotent and lossless) with a `legacy_id` recorded for traceability. New and migrated IDs are collision-safe against other lifecycle IDs and findings; the secrets-gate behavior and the file/rule/hash finding re-binding are unchanged, and legacy `exc-###` IDs are still tolerated.
- **Reconciliation scan output is cleaner.** Host permission/allow-rule files (e.g. `.claude/settings.local.json`) are now reported in a separate `host_permission_flags` channel in the `wave_upgrade` summary — operator-flagged, kept out of the auto-editable `reconciliation` list — and the scan no longer false-flags `CHANGELOG.md` (at any path) or the generated prompt-surface manifest.
- **The secret scan always writes its ledger.** A clean scan now writes `docs/scan-findings.json` as an empty `[]`, so the file's presence confirms the scan ran; it changes only when findings change (no repeat-scan churn).

### Fixed

- **No more flashing console windows on native Windows.** Every framework-spawned subprocess — including the indexing, graph, and secret-scanning multiprocessing pools (which the earlier per-spawn fix did not cover) — now runs window-free on Windows: the pools launch via the console-free `pythonw.exe`, falling back to serial execution when it is unavailable. No spawn inherits a blocking stdin, which previously could hang the upgrade.
- **Native-Windows upgrade no longer crashes on encoding or paths.** The upgrade uses the platform temp directory instead of a POSIX `/tmp` fallback (absent on Windows), forces UTF-8 on stdout at every CLI entry point so a non-ASCII glyph no longer raises a `UnicodeEncodeError` in a cp1252 console, and gives spawned indexer/graph/secrets children their own UTF-8 stdio — fixing the silent index-build failure and the garbled output.
- **`wave_install_audit` validates artifacts correctly.** The install-log parser no longer misreads an artifact's description text as a file path, so the install-state check verifies real on-disk artifacts again.
- **MCP `handler_not_ready` during upgrade/reload.** The server now lazily builds its handler from the known repository root, so a started server no longer reports `handler_not_ready` in the startup or post-reload window.

## [1.9.4] - 2026-06-27

### Added

- **New `wf` subcommands for agent-run framework scripts.** `wf codebase-map`, `wf render-surfaces`, and `wf secrets-scan` join the cross-OS `wf` dispatcher so operators and agents stop guessing raw `python3 .wavefoundry/framework/scripts/*.py` invocations. Framework upgrade cleanup stays a manual `python3 .wavefoundry/framework/scripts/prune_framework.py` step — it needs the pre-upgrade MANIFEST that only the operator running the upgrade holds.
- **Upgrade-time retired-surface reconciliation.** A minor-or-major `wf upgrade` now scans the repository for stale references to retired framework surfaces (such as the per-command `.wavefoundry/bin/*` wrappers replaced by the cross-OS `wf` dispatcher) and reports an actionable `file:line → suggested wf form` list in place of generic recommend-only prose. The scan is report-only and exclusion-aware (it skips the framework pack, the generated index, historical records, and tests) and matches both forward-slash and backslash path references. Reconciliation guidance also names host permission/allow-rule files (for example `.claude/settings.local.json`) as a surface to flag for the operator rather than self-edit, and clarifies the gate-before-reload window during upgrade.
- **Structured `wave_upgrade` summary.** `wave_upgrade` now returns a parsed `summary` block (from/to version, files pruned, docs-gate result, index-update state, failed phase, and the reconciliation findings) plus a top-level `next_step` and `next_tools`, so agents read computed fields instead of scraping the raw output. The existing `output` and `exit_code` are unchanged and parsing is fail-safe.

### Changed

- **Committed MCP configs standardize on `python3`.** Every generated host MCP config launches the server with `command: "python3"` and the repo-relative `server.py`, byte-identical across macOS, Linux, and native Windows. `wf setup` **verifies** `python3` resolves to Python 3.11+ and, when it does not, fails closed with platform-aware guidance (install via Scoop/Microsoft Store on Windows, or your package manager / a symlink on macOS/Linux) plus the no-PATH per-machine fallback config. Setup does not modify your Python installation or PATH.

### Fixed

- **MCP helper subprocesses no longer contend with the host's JSON-RPC stdio.** Server-side helper processes (docs-lint, gardener, sync-surfaces, upgrade phases, sensors) now run with `stdin` detached and intentional stdout/stderr handling — fixing `wave_validate`/docs-lint-over-MCP timeouts seen on some hosts — and suppress their console window on native Windows.
- **Setup fails loudly instead of silently shipping a dead MCP config.** When `wf setup` finds `python3` does not resolve to Python 3.11+ on PATH, it reports the exact problem and exits non-zero with platform-aware guidance (make `python3` resolve — Scoop/Microsoft Store on Windows, your package manager or a symlink on macOS/Linux — or use the per-machine absolute-venv-path fallback) rather than reporting success for a `command: "python3"` config the host cannot launch. Setup does not modify your Python installation or PATH.

## [1.9.3] - 2026-06-26

### Changed

- **MCP startup no longer starts model prewarm.** The MCP handler no longer launches background embedding/reranker cache work while the host is still negotiating stdio and loading tool schemas; semantic search starts the optional prewarm after startup instead. Install guidance now reinforces the generated config contract: launch MCP with PATH `python3` on `server.py`, not a hardcoded tool-venv Python path, and start a fresh host session after config/Python fixes. `wf setup` now smoke-tests the same `python3 server.py --dry-run` launch shape used by generated MCP configs.
- **Model-fetch CA discovery honors Node's CA bundle env var.** The setup/model-download trust-store fallback now recognizes `NODE_EXTRA_CA_CERTS` after `CODEX_CA_CERTIFICATE` / `CLAUDE_CODE_CERT_STORE` and before `SSL_CERT_FILE` / `REQUESTS_CA_BUNDLE`, so native Windows users launched from Node-based agent hosts can reuse the same corporate CA bundle the host process already trusts. Wave 1p7pk / native-Windows field follow-up.

## [1.9.2] - 2026-06-26

### Changed

- **Windows and no-PATH setup guidance leads with `wf`.** Operator-facing install, upgrade, prompt index, framework-operator, dashboard, and install-seed guidance now treats `wf setup` and `wf` subcommands as the primary command surface, with repo-local `wf.cmd` / POSIX shim paths only as no-PATH fallbacks. This closes the guidance hole where agents guessed a plain-Python invocation of `.wavefoundry/bin/wf` on native Windows. Wave 1p7pk / native-Windows field follow-up. Current guidance standardizes launcher commands on `python3`.

### Fixed

- **Native-Windows MCP stdio framing hardening.** The MCP runner now configures stdin/stdout/stderr to UTF-8 with LF-only newlines before building the server and entering the stdio transport, with stdout/stderr write-through enabled. This keeps Wavefoundry's side of the JSON-RPC stdio boundary byte-stable on native Windows text streams while preserving stderr-only diagnostics. Wave 1p7pk / native-Windows field follow-up.

## [1.9.1] - 2026-06-26

### Fixed

- **Native-Windows MCP server reliability (broken pipe on startup).** The tool venv is now activated **in-process** (`site.addsitedir`) instead of re-execing into the venv interpreter. The re-exec used a subprocess child on Windows (no in-place exec there), which became a second process holding the same stdout pipe the MCP host owns — causing an intermittent broken pipe when the tool list arrives and orphaned processes across reconnects. In-process activation keeps a single host-spawned process on every OS while preserving the byte-identical `command: "python3"`. If the venv was built for a different Python `(major, minor)` than the running interpreter (e.g. after a system Python upgrade), normal entries fail loud with a clear "run `wf setup` to rebuild" message, while `wf setup` bypasses activation and recreates the stale tool venv. Wave 1p7pk / 1p802.

## [1.9.0] - 2026-06-25

> **Native Windows (no WSL2), and a single runtime surface.** Every committed launcher and config now names one byte-identical `command: "python3"` and runs from a single checkout on macOS, Linux, and native Windows for CLI hosts. Upgrading retires the nine `.wavefoundry/bin/*` wrappers for one cross-OS `wf` CLI and flips the MCP/hook commands to `python3` — so **`setup` / upgrade makes `python3` resolve** without creating a `python` symlink. Drive the upgrade with `wave_upgrade()` (MCP) or `wf upgrade`. GUI-launched hosts that don't inherit the shell PATH use the printed absolute-venv-path fallback.

### Added

- **Native Windows support without WSL2 (CLI hosts).** The MCP server, hooks, git hooks, and operator CLI run from a single committed checkout on native Windows. The committed `command` is the byte-identical `python3`; the tool venv is activated **in-process** (`site.addsitedir`) so the server stays a single host-spawned process on every OS (no re-exec/child — see *Fixed* above); the venv layout (`Scripts\python.exe` vs `bin/python`) resolves in one place; rendered surfaces are written with byte-fixed line endings on every host; and a repo `.gitattributes` pins shebang-bearing files to LF (and `wf.cmd` to CRLF) so `autocrlf` can't corrupt them.
- **Host-agent TLS CA discovery for model downloads.** The model-fetch trust-store fallback now also honors the host coding agent's own CA bundle — `CODEX_CA_CERTIFICATE` (Codex) and `CLAUDE_CODE_CERT_STORE` (Claude Code) — ahead of `SSL_CERT_FILE`/`REQUESTS_CA_BUNDLE`, used proactively when set, with the OS platform stores and the `certifi` default as the ordered fallbacks. Verification stays on throughout; only the trusted CA bundle changes.

### Changed

- **One cross-OS `wf` operator CLI replaces the nine `.wavefoundry/bin/*` wrappers.** The bash-only `docs-lint`, `docs-gardener`, `wave-gate`, `update-indexes`, `lifecycle-id`, `wave-dashboard`, `upgrade-wavefoundry`, `setup-wavefoundry`, and `mcp-server` launchers are retired in favor of a single self-bootstrapping `wf` dispatcher behind a `wf` (bash) + `wf.cmd` (Windows) shim pair, so the operator CLI runs identically on macOS, Linux, and native Windows. Use `wf docs-lint`, `wf docs-gardener`, `wf gate open|close|status`, `wf dashboard`, `wf update-indexes`, `wf lifecycle-id`, `wf upgrade`, and `wf setup` (run `wf --help` for the list). `wf setup` stays on the system interpreter pre-symlink so a fresh bootstrap still works.
- **Single runtime execution surface.** Every framework entry point — the MCP server, setup, upgrade, indexer, hooks, git hooks, and the `wf` CLI — self-bootstraps into the shared tool venv through one resolver; no config, launcher, hook body, or spawner re-derives the venv path (enforced by a standing scan). Inner spawns use the running interpreter, so the whole fleet stays on the venv Python.
- **MCP-first upgrade routing.** The upgrade guidance now leads with the `wave_upgrade()` MCP tool (poll/inspect with `wave_upgrade_status()`); the manual procedure is relabeled the no-MCP `wf upgrade` CLI fallback. `wave_upgrade` and `wave_upgrade_status` are now listed in the available-tools surface, and `wave_upgrade_status` is documented in the MCP tool spec.
- **Minor-bump reconciliation recommendation.** A major/minor framework upgrade now surfaces a recommendation to reconcile local surfaces that referenced a changed or retired framework surface (e.g. the `.wavefoundry/bin/*` → `wf` cutover); patch bumps do not surface it.
- **Git hooks, line endings, and the dashboard daemon are cross-OS.** The commit/merge incremental-reindex git hooks route through the shared bootstrap (so native-Windows git fires them), and the local dashboard self-daemonizes in Python with an OS-correct detach instead of a bash-only `nohup`.

## [1.8.1] - 2026-06-23

> **Upgrading runs a one-time graph re-extract.** This release bumps the graph builder version (the call graph's edge/node shape changed), so the graph is re-extracted once after upgrade — graph-only and fast (~10–30 s), not a semantic re-embed (`CHUNKER_VERSION` is unchanged, so there is no re-chunk/re-embed). The upgrade's final index phase now does this automatically alongside the semantic update — version-aware, the same way it handles a chunker bump — so no manual step is required. (If the graph step is skipped, the first graph query still rebuilds it in-process as a safety net.)
>
> **Two behavior changes to know:** CPU index builds now use a smaller default embedding batch (much lower peak memory — see below), and the local dashboard is now a read-only viewer that no longer runs index builds (the `auto_index` setting was removed; index updates come from the post-edit hook, the MCP server, and `wave_index_build`).

### Added

- **Config-key → reader edges.** A code site that reads a config key by literal name now links to that key in the graph — Python `.get("KEY")`/`cfg["KEY"]` against JSON config, and Java/Spring `@Value("${key}")`/`getProperty("key")` against `application.{yml,properties}` keys (`.properties`/`.yml`/`.yaml` now contribute config-key nodes). Bounded to real config surfaces and unique, distinctive keys so ordinary dictionary access does not create false links.
- **Instrumentation targets on advice classes.** OpenTelemetry `TypeInstrumentation` classes carry an `instruments` property naming the types their `typeMatcher()` weaves into — including `namedOneOf` lists and matchers nested in `implementsInterface`/`hasSuperType` — so "what does this advice instrument" is answerable from the graph without hand-searching. Method/argument matchers are excluded.
- **Model downloads fall back to the OS trust store.** When a model download fails TLS verification (`CERTIFICATE_VERIFY_FAILED`) — common behind a corporate proxy whose root CA is in the OS trust store but not the bundled `certifi` — the fetch retries against the OS trust store (honoring a preset `SSL_CERT_FILE`/`REQUESTS_CA_BUNDLE`). Verification stays on throughout; only the trusted CA bundle changes.

### Changed

- **Cross-language call-confidence promotion.** A call that resolves to a unique definition by construction (same-file, or an exact cross-file match) is now recorded at full confidence instead of the heuristic tier, across all languages — sharpening blast-radius and change-risk ranking. Only the confidence label changes; no edge target is altered.
- **Transitive blast-radius confidence.** `code_risk_score` propagates edge confidence along the whole path and reports `transitive_extracted_fraction`, so a blast radius reached only through low-trust edges is discounted rather than over-counted.
- **Much lower memory for CPU index builds.** The embedding forward batch is now per-model and defaults to 32 (down from 256), cutting peak RSS of the CPU embedding pass ~3.5–3.8× at equal-or-better throughput (measured on an M2 Max CPU path). Tune per model via `indexing.code_embed_batch_size` / `docs_embed_batch_size`. The GPU/CoreML path is unaffected. On a constrained low-RAM CPU/WSL2 host this is projected to bring the build well under the memory cap and clear the out-of-memory failure — field-confirmation on such a host is still pending.
- **The local dashboard is a read-only viewer.** It no longer triggers index builds; index freshness is owned by the post-edit hook, the MCP server's background refresh, and `wave_index_build`. The dashboard's build-status panel now reflects those builds.

### Fixed

- **Index health no longer hides a missing code layer.** When code sources are in scope but the code index is absent (e.g. an interrupted or OOM-killed code embedding pass), `wave_index_health` now reports `incomplete` with the code layer in `missing_layers` and a remediation diagnostic, instead of `ready`.
- **Out-of-memory index builds fail loudly.** A code embedding pass killed by the OS OOM-killer now surfaces a clear out-of-memory error with remediation (lower the embedding batch, raise host/WSL2 memory) instead of appearing to succeed.

### Removed

- **Dashboard `auto_index` / `auto_index_delay_seconds` settings.** The dashboard no longer runs index builds, so these settings were removed; index updates are background/MCP-owned.

## [1.8.0] - 2026-06-22

> **Upgrading runs a new factor-review surface check.** The docs gate now verifies the factor-review agent docs: every active factor lane needs its canonical `docs/agents/factor-<nn>-<name>.md`, and any `.claude/agents/` wrapper needs a matching canonical source and valid frontmatter. If your factor surface drifted — wrappers without their sources, or wrappers missing frontmatter — the gate flags it, and the upgrade flow regenerates the missing canonical docs. Repos that run no factor lanes are unaffected.

### Added

- **Design-system foundation.** A machine-readable DTCG design-token contract under `docs/design-system/`, extracted from the dashboard's own styling rather than invented; a no-Node token build pipeline (`build.config.json` + `bin/build-tokens`) that emits CSS, Tailwind, TypeScript, and JSON exports; and a reusable dashboard primitive module the dashboard consumes, with its styling bound to the semantic tokens.
- **Adopt an existing design system in place.** When a target repo already maintains its own design system — a published token package, a Style-Dictionary/DTCG source, or Figma libraries — the contract records a thin reference to it instead of extracting a parallel, drift-prone mirror. The framework defers to what is already there rather than imposing its own structure.
- **Factor-review surface gate.** `docs-lint` turns a previously-silent broken factor-review surface into an actionable finding: an active factor lane missing its canonical doc, an orphaned wrapper with no source, or a wrapper that cannot load as a subagent (no frontmatter). The requirement keys off the active review-lane set; a factor assessed as relevant but with no active lane surfaces as a non-blocking warning, not a hard failure.

### Changed

- **Dashboard navigation polish.** The collapsible sidebar gains clearer dark-mode separation, a smaller theme toggle beside the project title, a `Wavefoundry` version + live-status footer (full build in the tooltip), and a more visible active-section highlight in dark mode.
- **Delegated code work prefers the code-navigation tools.** Code investigation and implementation handed to a subagent must run through a role-typed agent or carry the code-navigation directive in its prompt — subagents inherit the available tools, so reaching for shell search by habit in a subagent is the same defect as in the main thread.
- **Vendor-neutral distribution.** Removed references to external consumer projects from the packaged framework — comments, test fixtures, examples, and the shipped changelog — so the distribution names no project outside Wavefoundry.

## [1.7.3] - 2026-06-19

### Added

- **Antigravity host support.** Wavefoundry renders a workspace-local `.agents/mcp_config.json` for the Antigravity CLI (`render_platform_surfaces --platform antigravity`), auto-detected from `.agents/` and using the portable `.wavefoundry/bin/mcp-server` wrapper (no absolute paths). Antigravity reads the project-root `AGENTS.md` natively, so no separate entry file is rendered.

### Fixed

- **Host-support documentation accuracy.** Corrected the hosts badge and split the MCP-attachment tiers in the docs (auto-rendered config vs. manual stdio paste); added Windsurf and Warp rows to the MCP-enabling tables so every listed host has a resolvable attachment path; described Windsurf accurately (hooks are auto-rendered, MCP attachment is manual).

## [1.7.2] - 2026-06-18

### Added

- **GPU / embedding-provider diagnostic.** `setup-wavefoundry --check-gpu` (and the `wave_gpu_doctor` MCP tool) print what embedding backend this host will actually use — platform, onnxruntime, GPU detection, available ONNX execution providers, the provider that would be selected (with reason), and a CUDA 12/13 ABI-gap check. It runs the same bounded provider probe setup uses, so on Apple Silicon it reports CoreML (not CPU); remote/cloud providers (e.g. Azure) are excluded from the listing.
- **Windows via WSL2 is a supported, documented target.** A single Supported Platforms statement (README + project overview), the WSL2 gotchas that matter (keep the repo on the Linux filesystem, venv lives inside the distro, CUDA via GPU passthrough), and a reproducible smoke checklist. WSL2 runs the identical Linux code path — no separate install.

### Fixed

- **Native-Windows execution hardening (forward-compat).** The Python execution layer now branches correctly on Windows — venv interpreter path and re-exec, process liveness via `tasklist`, background-process detachment flags, codebase-map link separators, text encoding, read-only directory removal, and model-cache integrity checks — with zero change to macOS/Linux/WSL2 behavior. Native Windows is not yet runnable end-to-end; this stages the execution layer ahead of the launcher work.
- **Windows dashboard orphan reconciliation.** The dashboard's stale-process cleanup now works on Windows (a command-line process scan via PowerShell) instead of falling back to bare PID checks, so orphaned dashboards no longer accumulate.

### Changed

- **Generated file paths always use forward slashes.** Every path Wavefoundry writes — secrets-scan findings and the shipped allowlist, reindex reports, agent-surface listings, and the rendered launcher/hook commands — now uses `/` on every OS, so an artifact generated on Windows matches one generated on macOS/Linux.

## [1.7.1] - 2026-06-17

> **Upgrading re-extracts the code graph once.** The graph builder advanced (the determinism fix below changes the emitted edge set), so the first index after upgrading re-extracts the graph from scratch — minutes, not a full semantic rebuild. The semantic (docs/code) index is unaffected. The upgrade flow runs it automatically.

### Fixed

- **`code_ask` no longer answers confidently when it found nothing.** On a zero-signal query (retrieval scores all near zero) it now returns `confidence: low`, adds a "no confident match" gap, and flags the weak citations (`weak: true`) instead of presenting off-topic results as evidence — while still returning them as navigation leads (never empty). When the cross-encoder reranker did not run, confidence is capped (never the old count-based "high"), and the response carries a loud gap naming the degraded vector-only fallback and its cause, so a misconfigured reranker is visible rather than silently lowering answer quality. Citation fidelity is unchanged — every citation still points at a real `file:line`. A capitalized leading question word ("Which…", "Where…", "Tell me about…") is no longer mistaken for a code symbol, which had been inflating off-topic results above the relevance floor and defeating abstention for those phrasings.
- **Code-graph extraction is reproducible.** The same source tree now produces the same graph across rebuilds — cross-file call/reference resolution was order-dependent, so identical input could yield different edge counts (and, downstream, different codebase-map areas) from one rebuild to the next. Resolution is now order-independent with explicit, faithful tie-breaks, and each graph carries an input fingerprint so reproducibility is verifiable. Existing correct bindings are unchanged (no wrong-symbol rebinding).
- **Per-area `AGENTS.md` is found at the project root.** The codebase map's area link and the `wavefoundry://area/{id}` resource now walk up from an area's directory to the nearest ancestor `AGENTS.md`, so a single `AGENTS.md` placed at a project root (the conventional location) serves all of that project's deep areas — previously only a file at the area's exact deep path was linked, leaving conventionally-placed files unlinked.

### Changed

- **`code_ask` surfaces implementing code over prose for code questions.** For "how does X work" / "where is X" questions, reference docs (architecture notes, specs, ADRs, plans, journals) are down-weighted so the implementing source ranks above prose — including above a stale spec — while docs still appear as secondary context (a down-weight, not an exclusion).
- **`code_ask` recovers cross-file and enumeration answers.** Cross-file structural neighbors (callers/readers/importers) that semantic search missed are now merged into the citations (flagged `from_graph`), not just listed separately, so a cross-file chain reaches the answer. Enumeration questions ("which/all X are …") widen retrieval and carry a gap noting the list is a ranked sample that may be incomplete, routing exhaustive enumeration to the exact-search tools instead of implying completeness.
- **Faster reranking.** The cross-encoder reranker now uses a batch sized to the query-time candidate pool rather than the embedder's index-time batch, cutting wasted padding — roughly a third faster per query on Apple Silicon with identical ranking output.

## [1.7.0] - 2026-06-17

### Added

- **Codebase map.** A generated, read-only orientation map of the project's own codebase at `docs/references/codebase-map.md` — bounded areas (domain/package/directory) with their key files, entry points, and `code_*` drill-in handles, built offline from the index. It scales from a small repo (compact, near-flat) to a large monorepo (bounded top tier with leveled drill-down) and acts as the index to the index: it routes you to the right area, then the code tools take over. Served as the `wavefoundry://codebase-map` MCP resource.
- **Per-area context.** Major subsystems carry a vendor-neutral `AGENTS.md` (local conventions, gotchas, intent) that the map links and the index surfaces in `code_ask`/`docs_search` when you work in that area. During inventory the agent now authors a grounded initial draft for major areas (humans refine), and upgrades backfill it. Read a specific one via the `wavefoundry://area/{area_id}` MCP resource.
- **Vendored and generated code is kept out of orientation.** The map excludes bundled third-party and generated code from its areas, key files, and drill-in hubs — driven by `docs/repo-profile.json` `vendored_paths` globs, `.gitattributes` `linguist-vendored`/`linguist-generated`, and generated-code detection — so a cold-start agent lands on the product, not on a dependency. Excluded trees stay fully searchable via the `code_*` tools.
- Code-reviewer maintainability and dead-code review mode for surfacing unused or over-complex code during review.
- Session-stop context capture and a framework-config review prompt for keeping long sessions and project config honest.

### Changed

- **TS/JS symbol extraction is faithful.** Interface and object type members and type aliases are no longer mislabeled as functions, and anonymous-function and route-path junk symbols are no longer emitted as graph nodes, so entry-point lists and the map reflect real callables. Consumer graphs re-extract automatically on upgrade.
- **Codebase-map clustering is reproducible and cohesive.** Community detection is seeded for stable results across rebuilds, cross-directory grab-bag areas are split, opaque structural and version directory names (`v1`, `shared`, …) are qualified by a distinctive ancestor, and same-package type-only files collapse into one area. Consumer graphs re-cluster automatically on upgrade.
- **Single dashboard sidecar.** The dashboard's two state files were merged into one lock file that also holds the startup metadata.

### Fixed

- **Dashboard process lifecycle.** `start`/`stop`/`restart` now reconcile against the actual running processes (by command line) instead of trusting a recorded PID: no more orphan dashboards accumulating across restarts, no more climbing ports, and a killed dashboard is no longer reported as still running. The upgrade path's dashboard detection is hardened the same way.
- Index freshness signals are reported more accurately during long sessions.

## [1.6.2] - 2026-06-15

### Fixed

- **The secret scanner no longer reads files outside its scope.** Framework runtime artifacts — the local index (LanceDB segments), caches, logs, and built packs — are excluded before any file is read, in every project. When the working tree isn't a clean git checkout (so file selection falls back to a directory walk), the scanner now honors `.gitignore` via `git check-ignore` instead of sweeping in ignored files. Versioned shared objects (`libfoo.so.13`) are now recognized as binary and skipped. This removes the slow docs-gate scans previously seen on repositories that weren't a usable git worktree; detection of secrets in real source files is unchanged.

## [1.6.1] - 2026-06-15

### Changed

- **Secret findings are enforced only at wave close.** The hardcoded-secrets scan still detects and records findings to `docs/scan-findings.json` continuously, but no longer fails `docs-lint`, the post-edit hook, validation, or upgrades — those run in record-only mode. `wave_close` is the single secrets gate: `pending` and `suspected-secret` (and any unrecognized status) hard-block close until classified; a confirmed real secret is **non-blocking** and surfaces a standing reminder on every close listing the project's confirmed secrets; cleared false positives pass. The per-wave `acknowledged_for_wave`/`override_reason` acknowledgment was dropped (legacy entries are tolerated). Only a malformed inline-suppression directive remains a lint error.

### Fixed

- **GPU acceleration no longer fails silently on CUDA 13 hosts.** On an NVIDIA host where `onnxruntime-gpu` (built for the CUDA 12 ABI) cannot load against a CUDA 13 runtime, indexing previously dropped to CPU with no signal. It now surfaces a clear, one-time warning naming the cause and the remediation — build `onnxruntime-gpu` from source against CUDA 13, or install a CUDA-13 wheel once available (a `.so.13`→`.so.12` symlink does **not** work; CUDA 13's cuBLAS exports different ELF version symbols). The warning fires even when the CUDA provider isn't listed at all. Set `WAVEFOUNDRY_EMBED_PROVIDER=cpu` to silence it and run on CPU intentionally.
- **Secret scanner skips binary and data files by extension.** Known binary/data files (archives, shared objects, LanceDB segments, media, model weights) are now skipped before being read, so repositories with many such files no longer slow the docs gate (previously every file was read for a binary sniff). The existing size, null-byte, and long-line guards still cover files without a recognized extension.

## [1.6.0] - 2026-06-13

> **Upgrading to 1.6.0 forces a full index rebuild.** The embedding models changed — documentation now embeds with `snowflake-arctic-embed-xs` and code with `bge-small-en-v1.5` — and both `CHUNKER_VERSION` and `GRAPH_BUILDER_VERSION` advanced, so the first index build after upgrading re-chunks, re-embeds, and re-extracts the graph from scratch. Expect a full rebuild (minutes, not an incremental update) on the first post-upgrade index. The upgrade flow runs it automatically.

### Changed

- **Nested-type constants are retrievable by their qualified name.** A constant declared inside a type-within-a-type (a Swift `static let` in a nested `struct`/`enum`, or a nested class in other languages) is now chunked under its qualified owner (`Outer.Inner.x`), matching the graph layer — previously it was flattened onto the outermost type. `code_constants` resolves it by the bare leaf, the full qualified name, or any intermediate dotted suffix, and `code_ask` value/where-is questions now surface the declaration (symbol-first injection fires for navigational questions, not just explanatory). The graph-seed extractor also ignores generic decoy words (`value`/`flag`/…) so they don't hijack traversal.
- **Single-index semantic retrieval with split embedding models and a reranker.** The previous two-layer search path is folded into one index. Documentation embeds with `snowflake-arctic-embed-xs` and code with `bge-small-en-v1.5`, each tuned to its content, and a `cross-encoder/ms-marco-MiniLM-L-6-v2` cross-encoder reranks candidates — wired into `code_ask` as the rerank-first path. On Apple Silicon the embedders and reranker run FP16 on a static-shape CoreML graph with an on-disk compile cache under `~/.wavefoundry`; CPU elsewhere.
- **Streaming index build with bounded memory.** A full rebuild streams files through a bounded buffer (chunk → embed → append → flush) instead of materializing every chunk and vector for a layer up front, so peak memory is bounded by the buffer rather than the corpus and progress reports "file N / M". The produced index is identical to the previous batch path. Reindex model loads are cached-first (no Hub round-trip on a warm cache), and an incremental update loads only the embedder for a layer that actually changed.
- **Oversized-file guard in the indexer.** Files larger than a hard cap (default 5 MB) are dropped from the index walk, and files over a tree-sitter parse cap (default 2 MB) skip AST graph extraction — bounding index time on pathological inputs such as a large data dump. Both caps are overridable via `docs/workflow-config.json` (`indexing.max_file_bytes` / `indexing.max_treesitter_parse_bytes`).
- **Portable tracked editor/MCP surfaces.** The rendered hook and MCP-launcher surfaces are committed with project-relative paths instead of absolute author paths, so a fresh clone works for contributors with no per-machine fixups. Install assets are consolidated under `framework/install/` with a discoverability index.
- **Hardware-aware embedding provider selection.** `setup_index.py` now chooses among CUDA, CoreML, explicit named secondary ONNX providers, and CPU fallback using a shared provider policy module. It logs the selected provider and why CPU fallback was used when the active hardware could not be verified as materially faster.

### Added

- **Hardcoded secrets detection.** A Gitleaks-schema TOML ruleset (`.wavefoundry/scan-rules.toml`, seeded from the Gitleaks community rules; operator-overridable at `docs/scan-rules.toml`) drives a pure-Python regex validator in `wave_lint_lib`. Every `docs-lint` run and `wave_scan_secrets` MCP call checks tracked files against the ruleset. Findings are recorded in `docs/scan-findings.json` with a `pending → false-positive / suspected-secret / confirmed-secret` lifecycle: `pending` requires classification, `false-positive` requires multi-user confirmation, and `confirmed-secret` requires operator acknowledgment (wave-scoped, re-acknowledgment required per wave). `wave_close` hard-blocks on any `pending` entry and soft-blocks on any unresolved `suspected-secret` or unacknowledged `confirmed-secret`.
- **`wave_scan_secrets` MCP tool.** On-demand secrets scan with `mode: "incremental"` (default, git-diff scope) or `mode: "full"` (all tracked files). Runs in an isolated subprocess so ProcessPoolExecutor workers and the resource tracker do not bleed into the MCP server process. Auto-escalates to a full scan when the rules hash changes (SHA-256 of both rule files, null-byte separator). Response includes `effective_mode`, `rules_hash_changed`, `escalated_to_full`, `clean`, `elapsed_s`, `total_findings`, `by_status`, `failures_total`, and `failures`.
- **Rules-hash auto-escalation.** Both the indexer path (`scan_secrets.py`) and the MCP path (`run_secrets_scan.py`) compute a SHA-256 hash of the two rule files and persist it in `.wavefoundry/index/scan/scan-state.json`. Any change to either file (framework upgrade, operator edit) triggers a full scan on the next run without operator intervention.
- **Committer-threshold auto-detection for scan-rules.toml.** The required confirmation threshold for reclassifying a `pending` finding is derived from repository committer count (24-month window, all-time fallback): 0–1 committers → 1 confirmation, 2–6 → 2, 7+ → 3.
- **Security-reviewer pre-scope scan step.** `seed-213` (security reviewer) now runs a scan of wave-touched files before entering explicit non-goals, classifies each finding via the heuristic priority order (env-var-read → real-credential → test-fixture → placeholder → ambiguous), and writes or updates entries in `scan-findings.json` before proceeding with the normal review scope.
- **Time-bounded false-positive confirmations.** A `[policy] confirmation_valid_days` window (default `365`; `0` disables) expires stale false-positive confirmations so they must be re-verified yearly. Expired or undated confirmations are ignored for the clear-count (fail-closed) but left in place; re-verifying appends a new dated confirmation rather than mutating the old one.
- **False-positive override and reviewer-count clamp.** A non-empty `override_reason` dismisses a `false-positive` regardless of confirmation count (operator escape, parity with the confirmed-secret acknowledgment path), and the required-confirmation threshold is clamped down to the number of currently-confirmable (recent, non-bot) reviewers so a lone active maintainer is never deadlocked. The clamp never raises the threshold above the configured policy value.
- **JWT expiry awareness.** JWT findings surface a human-readable `exp` claim and mark expired tokens `(EXPIRED)` for triage. Surfacing only — an expired token is still flagged.
- **Full-repo secrets baseline at install and upgrade.** Install and upgrade run one full-tree secrets scan so secrets in untouched files are classified against the current ruleset up front, instead of dribbling out file-by-file across later waves.
- **Resumable upgrade after a docs-gate failure.** When the docs gate fails mid-upgrade (for example on a secrets finding), the upgrade can be resumed after the operator resolves the blocker (`--resume-after-gate`) instead of restarting from scratch; the resume path is idempotent on an already-advanced tree.
- **`scan-findings-format.md` reference doc.** A canonical reference for the `docs/scan-findings.json` schema, the `pending → false-positive / suspected-secret / confirmed-secret` lifecycle, the `[policy]` confirmation contract, and the self-scan/`[allowlist]` self-exclusion. Shipped in the pack and provisioned into every project on install, and refreshed on upgrade.
- **`code_risk_score` MCP tool.** Ranks the symbols in a scope (path, directory, or glob) by how risky they are to change — a composite of upstream blast radius times log-dampened incoming call-degree (`weighted_affected_file_count * log1p(weighted_fan_in)`). Both terms are weighted by call-edge attribution confidence: heuristic name-based edges count fractionally while type-resolved edges count in full, so a ubiquitous accessor name (`getKey`, `getValue`, `toString`) can't top the ranking purely on a name collision with an unrelated symbol. Each result also carries the raw `affected_file_count`/`fan_in` and an `extracted_edge_fraction` so a high-but-mostly-heuristic score is visibly discountable. `fan_out` (what the symbol itself calls) is surfaced as an independent component, not folded into the score. The response carries `score_formula` and `score_components` so the ranking is transparent and re-weightable; `top` caps the result and a candidate-cap guard asks to narrow the scope rather than running an unbounded per-symbol traversal. It ranks *many* symbols across a scope, where `code_impact` sizes *one*.
- **`install-log-format.md` reference doc provisioned to projects.** The install-log row-format and trustworthy-marker reference is now shipped in the pack and provisioned on install / refreshed on upgrade, so the install seeds that point at it resolve in every project instead of dangling (previously the doc existed only in the self-host).
- **Constant retrieval across all languages.** Module-, class-, and type-level constants are now chunked for semantic search and emitted as graph nodes in every supported language, with a function→constant `reads` edge (faithfulness-gated: same-scope or explicitly-imported only, never a coincidental same-name twin). `code_definition` resolves a constant by name, `code_references` lists its readers in a distinct `reads` bucket (not merged into callers), and `code_ask` surfaces constants alongside code. `reads` is opt-in for default graph traversal so a hot constant does not balloon neighbor sets.

### Changed

- **Scan auto-escalation in indexer.** `update_secrets_scan()` escalates to a full scan on scanner-version mismatch, missing findings file, or rules-hash change — previously only version mismatch and missing file triggered escalation.
- **Scanner skips files it should never scan.** Binary files (null-byte sniff), files larger than 5 MB, and individual lines longer than 32 KB are skipped and recorded as skips rather than scanned — bounding scan time and avoiding garbage matches on minified or generated blobs. Default `[allowlist].paths` now also cover common generated artifacts (lockfiles, minified bundles, vendored trees) and binary extensions.
- **Fewer false positives in prose and on structural noise.** The `generic-api-key` rule is scoped in Markdown/docs prose by a path clause plus an entropy ceiling and a prose-shape signal, so ordinary documentation sentences no longer trip it. The global `[allowlist]` `regexes`/`stopwords` value-filters now apply across every rule, suppressing `$VAR`, `{{template}}`, `%FMT%`, `/Users/…`-path and similar structural-noise values. Overlapping matches on the same secret are de-duplicated, and matches on comment lines are flagged for triage rather than auto-suppressed.
- **Tighter redaction of short secrets.** `matched_text` redaction is length-scaled — short values expose at most a 2+2 window and never more than ~40% of characters; the wider 4+4 window applies only at length ≥ 20. Raw secrets are never written to the ledger.
- **Clearer secrets-gate failure handling.** A docs-gate failure on a secrets finding now states which findings block, their status, and how to resolve them, and the upgrade flow routes the operator to the resolution loop before retrying the gate.
- **Project secrets policy is materialized before the first upgrade gate.** The upgrade flow writes `docs/scan-rules.toml` (committer-derived confirmation threshold) before the first docs gate runs, so the common "policy file missing" case can no longer fail the gate. The later editing-pass step is now an audit that only completes the rarer "file exists but lacks the policy key" case.
- **Full-scan reconciliation of stale findings.** A full secrets scan now drops `pending` findings the current ruleset no longer produces — e.g. after a rule or allowlist change has since suppressed them — so a ruleset improvement no longer leaves a phantom `pending` entry blocking `wave_close`. Strictly `pending`-only: operator classifications (`false-positive` / `suspected-secret` / `confirmed-secret`) are never auto-removed, and incremental scans (which re-evaluate only changed files) never prune.
- **Cross-file calls through Python sibling-script loaders now resolve.** Calls reached through the lazy `_load_script("module")` loader idiom — a module obtained via a thin loader wrapper, then called as `loaded.Class.method()` or `loaded.func()` — now resolve to the loaded module's symbols instead of emitting no edge at all. This closes a blast-radius blind spot where heavily-called symbols (reached only through the loader) reported zero incoming calls, so `code_impact` and `code_risk_score` now see their true reach.
- **Ambiguous cross-file receivers are disambiguated by import.** When a method call's receiver type shares its simple name with classes in other packages, the call is now resolved to the class the source file actually imported (using the file's import edges), instead of staying unresolved on the name collision. Applies where a per-type import carries the receiver name — Python `from a import Foo` and Java/Kotlin single-type imports. Unique-name cross-file calls already resolved; this fixes the same-name-collision case.
- **Cross-file method resolution extended to Go, Rust, C#, and same-package Java/Kotlin.** Go methods are keyed by receiver type (`Type.method`), and a package-qualified receiver (`var h foo.Helper`) resolves to the method in the named package — matched by the candidate's package directory, and left external when no project package matches. Rust associated functions (`Bar::build()`) and struct-literal / `::new()` let-bindings resolve to their type. C# calls across namespaces disambiguate by namespace membership — the caller's own declared namespace (read from the file's namespace declarations, so a caller in a nested class resolves correctly) plus its `using` directives. A same-package / same-directory fallback resolves Java/Kotlin/Go receivers used without an import. Every path binds only a unique package- or namespace-faithful candidate and otherwise leaves the call external — it never binds a wrong same-named twin.
- **Cleaner import edges for Rust, Kotlin, Go, Swift, and C.** Import extraction no longer emits junk `external::<keyword>` edges. The grammar root node was being mis-detected as an import (it shares a substring with an import keyword), which regexed entire files into one edge per token; statement keywords such as `import`, `use`, and `as` also leaked. Rust `use` declarations now produce clean dotted module targets with `as` aliases honored.
- **`code_impact` graph mode bounds its edge list.** The `edges` array is capped at `max_results` (with `edges_total` reporting the true count) so a high-fan-in symbol no longer blows the response past the tool's token limit, and the graph-mode `resolved` field is populated instead of returning null.

- **Upgrade lock no longer strands a half-replaced tree.** A docs-gate failure mid-upgrade records the failed phase and leaves a recoverable lock instead of a stuck in-progress marker, so the dashboard and the next upgrade invocation detect and resume the interrupted upgrade rather than reporting a healthy state over a partially-migrated tree.
- **Correct upgrade version resolution and prune reporting.** `from_version` is resolved from the installed framework revision (manifest `framework_revision`, with `VERSION` fallback) consolidated in one place, and the upgrade's prune count is read from the prune step's actual output rather than mis-derived — so the summary reports the real number of removed files.
- **Lifecycle IDs dedup across plans, waves, and ADRs.** ID minting now scans existing plan, wave, and ADR prefixes together when choosing the next available prefix, so a new plan, wave, or ADR can no longer collide with an ID already issued in a sibling family.
- **26 silently-dead secret detectors revived.** The ruleset is Gitleaks-schema (RE2), and 26 of its regexes used syntax Python's `re` rejects — an inline `(?i)` flag placed mid-pattern, and the `\z` end-of-text anchor — so they failed to compile and were silently skipped, leaving their secret types undetected (Adobe, SendGrid, Slack session cookies, Sentry, PlanetScale, Postman, Linear, GoCardless, Facebook page tokens, Alibaba, Authress, and more). A load-time RE2→Python translation shim now adapts these patterns faithfully (inline flags relocated to scoped groups preserving their original scope, `\z`→`\Z`) — applied only to patterns that fail to compile, so the already-valid rules are untouched and the ruleset stays Gitleaks-schema for future imports.

### Removed

- **Canonical-names rename manifest retired.** The `canonical-names.json` rename manifest and its docs-lint alias machinery are removed. `docs/workflow-config.json` must use the canonical keys (`wave_implement`, `wave_review`); docs-lint no longer accepts the legacy spellings, no longer escalates them by version, and no longer warns on retired role slugs. A one-shot convergence migration still rewrites the legacy config keys (`wave_execution` → `wave_implement`, `wave_council_policy` → `wave_review`) to canonical on every upgrade, so existing projects converge automatically; that migration is itself slated for removal at 2.0.0. The runtime `wave_council_policy` reader-fallback is removed. This pulls the previously-published 2.0.0 config-key removal forward. See ADR `1p5be`.

## [1.5.1] - 2026-06-06

### Changed

- **Guru multi-angle research protocol.** Guru now enumerates 2–3 independent angles before retrieval on `explanatory` and `navigational` questions, explicitly falsifies its working hypothesis after initial retrieval, surfaces null results as explicit negative evidence, and names contradictions when angles disagree rather than silently resolving them. Exemptions: single-symbol quick lookups and `instructional` questions. Framing layer around the existing 3-pass structure — passes unchanged.
- **Wave Council and Archetype Council protocol hardening.** Wave Council Phase 2 seats now open with a pre-primer statement (one sentence of independent read + whether the primer confirmed/extended/changed it — explanation mandatory, label alone not valid), explicitly state "No findings in my lane" rather than going silent, and flag same-findings across sequential seats as potentially correlated rather than independent confirmation. Moderator synthesis adds: a pre-primer read quality check (flags verbatim phrase echo of primer framing as contamination signal), a mandatory Recommendations Verdict table with red-team closing reconciliation folded into a single list (every advisory verdicted `fix now` / `defer` / `accept` with rationale and red-team challenge), and a falsification check (condensed on clean PASS, full detail when findings are present). Archetype Council seats declare their axis before reading the artifact; same null-finding, falsification-check, and recommendations verdict requirements apply. Phase 2 seat instructions in both councils are structured as explicit numbered steps with "do not read yet" guards. Both councils specify summary-level output verbosity — seat details internal, operator sees summaries and the recommendations verdict table.

## [1.5.0] - 2026-06-05

### Changed

- **Chunker per-kind size caps.** Doc, seed, JSON, YAML, TOML, HTML, XML chunks now respect the embedder's 512-token budget — previously only code chunks were capped, so the bottom 45-62% of every structured chunk was silently invisible to semantic search. Markdown lists and tables decompose at logical boundaries; section breadcrumbs preserved on every split. `CHUNKER_VERSION` bumped; indexer auto-rebuilds on mismatch.
- **Self-repairing indexer.** Cross-checks `file_meta` against Lance chunks every update and re-chunks drifted files. Closes the legacy mega-chunk pattern that left some files indexed-but-empty until their mtime changed.
- **`Upgrade wave framework` is one step, end-to-end.** Auto-migrates 1.4.x → 1.5.0 (backfills `Role:` in `docs/agents/*.md`, removes orphan `.claude/hooks/pycache-cleanup*` launchers, strips the stale `PostToolUse` row from `.claude/settings.json`). Always runs the index update at the end of the main flow — no separate `--update-index` invocation. Framework version transitions (`CHUNKER_VERSION` / `WALKER_VERSION` / `GRAPH_BUILDER_VERSION`) logged prominently; MCP server reloads in-process after extract. `--dry-run` previews everything with zero filesystem mutations. Supported upgrade floor is now 1.4.0.
- **MCP code-navigation polish.** `code_read` enriched for the read-then-edit flow — range-aware streaming, `read_invocation` hint (exact args for the built-in `Read` tool), `mtime`, `marker_regions`, `edit_governance`, and a `structural` field with containing-symbol + mid-construct flags + clean-range suggestion. Tree-sitter parses share a single LRU cache across all navigation tools — `code_definition` → `code_outline` → `code_callhierarchy` on the same file parses once. `code_keyword` defaults to `limit=50` (matching `code_pattern` / `code_references`); response includes `truncated` and `total_matches_found` when capped. `code_pattern`'s `max_results` parameter renamed to `limit` for cross-tool consistency (alias retained).
- **Auto-Guru routing strengthened.** Pre-flight intent question, positive/negative examples table anchored on the verbatim failure-mode phrase, and a retrieval-intent backstop catching misses the pre-flight skipped. MCP-first rule extends to literal-identifier sweeps across docs, config, and prompts (not only source-code navigation); legitimate shell exceptions (`git status`/`diff`/`log`, byte-level file-state checks, key-presence verification) named explicitly.
- **Drift-convergence lint family.** `docs-lint` warns on retired role slugs (`council-moderator` → `wave-council`; `code-insight-agent` → `guru`) in hand-authored project docs; warns when `docs/workflow-config.json` satisfies a required-keys alias via the legacy spelling (e.g., `wave_council_policy` vs canonical `wave_review`); fails on duplicate seed numeric prefixes; defers all transient Python caches (`__pycache__`, `.pytest_cache`, `.mypy_cache`, etc.) to `.gitignore`. `docs/agents/specialists/` location downgraded from `MUST` to fresh-install convention — established flat-layout repos may keep their existing location. Back-compat preserved everywhere (warnings are informational; returncode unchanged on alias-key usage).
- **Wave MCP tool polish.** Every write-side tool reports post-write `docs-lint` state in `data.lint` (`{clean, error_count, warning_count, first_errors}`); failures don't block the structural write. `wave_create_wave` produces lint-clean output with a pre-populated journal stub. Lifecycle IDs no longer burned by dry_run — `next_available_prefix` and `build_id` gain a `commit: bool` parameter; preview followed by apply returns the same ID.
- **Build & release.** Root `CHANGELOG.md` is now the single canonical release-history source; `build_pack.py` copies it into the pack zip at `.wavefoundry/CHANGELOG.md` so consumers still receive an in-tree changelog on upgrade. `Package Wavefoundry` seed removed from the consumer pack — packaging is wavefoundry-internal; consumer installs auto-prune via MANIFEST-prune. GitHub Release notes prepend an `## Install` block so the install steps appear alongside the download link.
- **JVM and monorepo harnessability detection.** `_audit_harnessability` recognizes JVM build files (`pom.xml`, `build.gradle*`) and source files (`*.java`/`.kt`/`.scala`/`.groovy`) in canonical roots — Spring Boot and JVM-ecosystem projects now report actual type coverage. Monorepo workspace detection added: Nx, Lerna, Rush, pnpm, Bazel, Pants, Buck, npm/yarn workspaces, Cargo workspaces, Maven multi-module POMs.
- **README install walkthrough restructured.** Two-phase shape (Phase 1 harness bootstrap → MCP restart → Phase 2 project discovery) reflects the actual install seeds. Claude Code and Codex CLI recommended as first-install hosts. `For enterprise forks` section names every upstream URL that needs redirecting.
- **Reality-checker routes to the new code-correctness patterns.** `seed-216` (reality-checker) gains a `## State And Assumption Correctness Patterns (Cross-Reference)` section listing the 7 patterns from `seed-221` with their applies-when hints and pointing to `seed-221` for full definitions. Cross-reference, not duplicate — code-reviewer owns the canonical pattern definitions; reality-checker routes assumption-audit findings to them when assumption-falsifiability is the dominant concern.
- **Config-key renames now converge.** `canonical-names.json` sets `removed_in: "2.0.0"` for both `wave_council_policy` → `wave_review` and `wave_execution` → `wave_implement`. `wave_upgrade` runs an unconditional convergence migration in `post_extract` (no `from_version` gate, idempotent) that rewrites legacy keys to canonical in `docs/workflow-config.json`; when both spellings are present, canonical wins and the legacy entry is dropped with its value captured in `.wavefoundry/logs/upgrade-convergence-migration.log` so operators can recover from the log without consulting git history. Dry-run writes `.wavefoundry/logs/upgrade-convergence-migration.preview.log` (parity with the 1.4 → 1.5 migration preview-report shape). Stderr summaries distinguish rename from drop so the both-present case isn't mislabeled. `docs-lint` adds `check_workflow_config_removed_keys` — at or past `removed_in`, legacy spellings produce an ERROR (returncode flips); below, they continue to produce the existing WARNING (now annotated with the removal version). VERSION-file degraded modes (missing / unparseable) defer to no-escalation. Role renames stay at `removed_in: null` — config-key scope only. Closes the indefinite-deprecation gap from field-feedback item #1.
- **Canonical-names manifest is the single source for framework renames.** `.wavefoundry/framework/canonical-names.json` (schema v1) declares every role-slug and config-key rename with its deprecated alias and an optional `removed_in` semver for bounded deprecation. `wave_lint_lib/canonical_names.py` provides the loader (fail-safe to empty on missing/malformed input — `docs-lint` stays operational). `constants.RETIRED_ROLE_NAMES` and `constants.WORKFLOW_REQUIRED_KEYS` now derive from the manifest at module-load time; public surface unchanged for backward compat. Required-key list (`agent_memory`, `project_persona_generation`, etc.) stays in code — manifest scope is renames only. Enables downstream consumers (renderers, upgrade migrator) to migrate to the manifest incrementally. Wave 1p3iv prep for the convergence half of `wave_council_policy` → `wave_review`.
- **Red-team routes to the new failure-path patterns.** `seed-225` (red-team) gains a `## Failure Path And Boundary Correctness Patterns (Cross-Reference)` section listing the 6 patterns from `seed-221` with their applies-when scopes and a one-line adversarial-probe framing per pattern (e.g., "what unbounded input would exhaust a resource?"). Reviewers in `abuse-path-review`, `failure-pressure-test`, and `council-adversarial-primer` modes anchor probes to the canonical patterns without leaving `seed-225`. Cross-reference, not duplicate.
- **Code-reviewer review surface expanded.** `seed-221` `## What to Check` gains 13 generic code-correctness review patterns across two new sections — **State And Assumption Correctness** (7 patterns: re-entrancy, convergence after correction, legitimate-state enumeration, idempotence, cache-key completeness, schema evolution, negation correctness) and **Failure Path And Boundary Correctness** (6 patterns: error handling, resource cleanup, diagnostic quality, boundary arithmetic, trust-boundary input validation, failure-path test coverage). Each pattern carries an "applies when" hint so reviewers route effort by PR scope.

### Fixed

- **`code_search` finds re-export and barrel files.** The chunker gains a symbolless-code-file fallback: when a code file has no docstring AND no extractable symbols (re-export `__init__.py`, TypeScript barrel `index.ts`, Go single-file packages, Rust `mod.rs` re-exports, module-level constants files), it now emits a `kind="code"` module chunk with `id="<path>::__module__"` and the top-level non-comment lines so semantic search can find the public surface. Previously these files emitted zero chunks and were invisible to `code_search` (only `code_keyword` text-backed search found them). Per-language comment-prefix awareness (Python `#`, C-family `//`/`/*`, SQL `--`, HTML `<!--`); cap at 50 lines per module chunk. Files with even one extracted symbol use the existing docstring + symbols summary unchanged — fallback only fires when symbol extraction yields nothing. Marker-region-only files still emit zero chunks and remain outside semantic search. Wave 1p3iw `chunks_emitted` tracking stays accurate: post-fallback, re-export files record `chunks_emitted: 1` and exit the legitimate-zero set. `CHUNKER_VERSION` bumps from `"24"` to `"25"`; `indexer.py` auto-escalates incremental updates to a full rebuild on the version mismatch so consumer indexes regenerate transparently on upgrade.
- **Self-repairing indexer no longer thrashes on legitimately-empty files.** `file_meta` records `chunks_emitted` per file after each indexing run; drift detection skips paths with explicit `chunks_emitted == 0` (empty files, all-whitespace, marker-region-dominated content). Legacy entries (no field) go through the drift check once to learn the count, then skip silently. Real-drift convergence preserved.

### Removed

- **`pycache-cleanup` Claude Code hook surface.** The `PostToolUse` Bash row in `.claude/settings.json` and `.claude/hooks/pycache-cleanup*` launchers are no longer rendered. Existing consumer installs auto-clean on next `Upgrade wave framework`.

## [1.4.1] - 2026-06-03

### Fixed

- Published GitHub Release zips now include the pre-built framework semantic index (`.lance` embeddings, graph state, manifest). Prior 1.4.0 release was missing the index because CI lacked the index-build dependencies (`numpy`/`fastembed`/`lancedb`); consumers had to rebuild the framework index locally on first `docs_search` call. Releases now come from the maintainer's machine via `build_pack.py --release`, which always includes the optimized + vacuumed index.

### Changed

- `build_pack.py` is now the official release CLI. The new `--release` flag handles tag, push, and GitHub Release upload after a successful local build, with pre-flight refusals on dirty working tree, non-main branch, existing tag, missing CHANGELOG section, or unauthenticated `gh`. Bare `build_pack.py --version X.Y.Z` is unchanged for testing and local-only builds. A `--release-dry-run` mode walks the entire pipeline without side effects for smoke-testing.
- `docs/references/release-flow.md` added — operator-facing documentation for the release command, pre-flight gates, and partial-state recovery paths.

### Removed

- `.github/workflows/release.yml` deleted. The CI workflow shipped a strictly worse artifact (no framework index) than the maintainer's local build; replaced by `build_pack.py --release`. PR-tests CI (scoped to lint/tests, not publishing) may be added in a future change if/when needed.

## [1.4.0] - 2026-06-03

### Fixed

- Runtime Wave Council policy reader now accepts the new `wave_review` key in `workflow-config.json` with a legacy fallback to `wave_council_policy`. Consumers who follow upgraded seed guidance and rename the key keep their Wave Council enforcement; consumers who haven't migrated yet continue to work unchanged. A one-line deprecation note fires to stderr at most once per process on legacy-key read.
- docs-lint required-keys check accepts either `wave_implement` (new canonical name) or `wave_execution` (legacy) in `workflow-config.json`. Error message names both acceptable keys when neither is set so the migration path is discoverable inline.

### Changed

- `WORKFLOW_REQUIRED_KEYS` data structure generalized to support alias-tuple entries — future seed-prose key renames can add back-compat without changing the validator logic.
- Active operational docs migrated to the canonical renamed config-key names (`wave_review`, `wave_implement`); two high-traffic operator surfaces carry a `(formerly wave_council_policy)` annotation for migrating-operator discoverability. Historical wave records left untouched per the no-retrofit principle.
- Self-host `docs/workflow-config.json` top-level keys renamed to the canonical names — dogfoods the back-compat fix end-to-end against the canonical example.
- Framework project skeleton now ships `wave_review: { enabled: true }` by default so the Wave Council surface is available in every new install. Enforcement (`required_for_all_waves: true`) stays operator opt-in — the council is enabled, not enforced. Mirrors how red-team is wired in as an always-available council seat. docs-lint required-keys check now names `wave_review` (with `wave_council_policy` as the legacy alias) so installs missing the section fail discoverably.
- Review surfaces unified as specialist agents. The Wave Council moderator role moves from `docs/agents/council-moderator.md` to `docs/agents/specialists/wave-council.md` (named after the surface, matching `red-team.md`). A new `docs/agents/specialists/archetype-council.md` makes the operator-invoked Archetype Council discoverable as a peer — applicable to any artifact (plans, design docs, code, prose, decision narratives, naming, AC formulation) where orthogonal stance-based lenses are what the work rewards, not text-only. Role-string identity flips from `council-moderator` to `wave-council` across seeds, code, tests, and active docs. Historical wave records and in-flight 1p337 council-verdict text preserved verbatim per the no-retrofit principle. No behavior change — verdict shape and protocol mechanics are unchanged.

## [1.3.32] - 2026-06-03

### Added

- Public-launch README rewrite: symptom-first opening, audience qualifier, install walkthrough with named operator-visible signals, "Your first wave" three-turn transcript with intentional close-gate refusal, "What is installed" tree with per-directory roles and gitignore footnote, host coverage table, Design principles, "For teams" evaluation answers, Built-with-Wavefoundry as Contributing introduction
- Auto-syncing version badge derived from GitHub Releases
- Archetype Council review surface — stance-based council with five canonical seats (Sun Tzu, Yoda, Spock, Marcus Aurelius, Feynman) and documented Hemingway / Munger swap-ins; optional, operator-invoked; complements Wave Council
- New shortcut phrase `Archetype review` / `Archetype council` added to public command catalog and AGENTS.md
- `[~]` AC and task checkbox state for "intentionally not met" — required-priority `[~]` ACs lint-require an inline status note; tasks accept `[~]` without note (asymmetric per priority weight)
- `wave_close` close-time hard gate: every AC and task across admitted changes must be `[x]` or `[~]` before close; silent `[ ]` blocks with `silent_unchecked_items_at_close` diagnostic naming change-id + item-type + identifier; `not-this-scope` priority ACs exempt
- Dashboard renders `[~]` items with distinct glyph (`~`), italic muted text, "deferred" badge replacing the priority badge, and "· N deferred" suffix on progress fractions
- Dashboard progress denominators exclude `[~]` items so a fully-met change with deferred ACs renders as complete
- `wave_index_build` response carries `stranded_rows_reaped` and `stranded_rows_reaped_by_table`

### Changed

- `docs/prompts/index.md` opening framing rewritten without internal seed-IDs; Public Commands table and Legacy Aliases table preserved verbatim
- `docs/references/project-overview.md` refreshed
- AC dialog and Task dialog glyphs are bold and slightly larger (1rem) so all three states stand out

### Fixed

- LanceDB orphan-row reaper on incremental index update — reconciles the LanceDB row set against the current eligible set on every `mode='update'` so rows for paths excluded by workflow-config narrowing are removed without requiring a full rebuild; reaps both `docs` and `code` tables regardless of `content` arg
- Project-layer audit eligibility filter (`_layer_current_hashes`) now honors workflow-config `project_include_prefixes` opt-ins, matching the indexer's actual `files_for_meta` computation; eliminates false-positive "removed paths" signal when a repo opts in framework paths via `code.project_include_prefixes`

## [1.0.0] - 2026-05-24

### Added

- Full Wave Framework lifecycle: plan, create, prepare, implement, review, close
- Local MCP server with 47 tools across wave lifecycle, docs/code search, audit, and framework navigation
- Semantic search index built on fastembed and BAAI/bge-base-en-v1.5 (fully offline)
- Three-dimension feedback harness: maintainability (computational sensors), architecture and security/performance (inferential sensor lanes)
- Wave Council protocol for multi-reviewer governance
- 214 seed prompts covering the full agent operating surface
- Stage gates enforced by the server: prepare gate, required reviewer lanes, operator signoff
- Distribution packaging (`build_pack.py`) and upgrade flow (`upgrade_wavefoundry.py`)
- Multi-host agent support: Claude Code, Cursor, Codex, Copilot, Junie, Windsurf, Air, Warp
- Semver versioning with lifecycle-prefix build metadata
- Python tool venv at `~/.wavefoundry/venv` (no system Python modification)
- Dashboard server for portfolio visibility
