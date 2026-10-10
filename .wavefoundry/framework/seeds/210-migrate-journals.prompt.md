# 210 - Migrate Journals (Operator-Invoked, One-Time)

Intent:

- Complete the retirement of the journal system in a repository that still carries journal files: promote still-valuable findings into typed memory candidates, archive role-journal content in a history document, relocate historical wave journals into their wave directories, and remove only what has been captured or provably carries nothing.

Context:

- Wave journals and the distill-at-close pipeline are retired. The memory system owns durable capture: `memory_add(status='candidate', ...)` for in-flight lessons, `memory_propose` plus `memory_validate` at wave close.
- The upgrade's built-in mechanical migration runs only on an upgrade from a release before 1.15.0. It deletes journals byte-identical to a pristine scaffold (zero information loss), moves content-bearing wave journals into their wave directories when those directories exist, and reports everything left behind for this prompt to finish with judgment. It follows the record vocabulary profile's id key and nested waves, refuses linked journal/folder paths, and leaves journals whose wave is archived or whose id is ambiguous.
- A distribution declares its pristine scaffolds and pre-migration hook in `mcp_tool_extensions.py` through `EXTENSION_JOURNAL_TEMPLATES` and `EXTENSION_JOURNAL_PRE_MIGRATION_HOOK` (`"module:function"` in `EXTENSION_HELPER_MODULES`). The default trigger, `EXTENSION_JOURNAL_PRE_MIGRATION_TRIGGER = "legacy_cutover"`, retains the legacy contract: the hook runs only on an upgrade from a release before 1.15.0, is never retried by a later upgrade, and is never called by the Migrate journals prompt. An absent trigger constant uses this default; the legacy hook can run even when no journal source remains.
- A distribution can explicitly opt in with `EXTENSION_JOURNAL_PRE_MIGRATION_TRIGGER = "journals_present"`. During upgrade apply, at `pre_docs_gate`, this calls the hook when `docs/agents/journals/` contains a direct regular singly linked `*.md` file other than `README.md`, regardless of from-version. Missing, empty, README-only, nested-only, symlink or hardlink sources cause no invocation on any version. Presence uses bounded metadata checks, without reading journal content or inferring eligibility from the migration preview's `left` entries. There is no recursive scan or configurable journal source root. The built-in migration still independently requires an upgrade from before 1.15.0, even after an opted-in hook succeeds.

Static trigger decisions:

| Declaration source / binding | Upgrade apply | Dry-run / public preview |
| --- | --- | --- |
| Missing module or absent trigger | Use `legacy_cutover`; later versions import no declaration or hook | Report the default without extension execution |
| Exactly one direct plain or annotated module-level literal `"legacy_cutover"` assignment | Retain the legacy cutover, including a legacy hook with no journal source | Report the legacy policy; execute no hook |
| Exactly one direct plain or annotated module-level literal `"journals_present"` assignment | Invoke only with qualifying source journals; built-in migration remains independently version-gated | Report policy and current bounded presence; execute no hook |
| Empty, non-string or unsupported literal; nonliteral expression; conditional or duplicate binding | Refuse before declaration execution or dependent migration | Report invalid policy without executing it |
| Unreadable/refused or unparseable source | Later versions skip with a path-free uncertainty diagnostic and no declaration execution; the original pre-1.15 validated apply-time load/refusal remains | Report unknown, never silently default or execute extensions |

- Upgrade apply loads selected declarations and the hook from the extracted pack. A journal-only import context gives incoming top-level modules/packages and their descendants precedence over cached old modules during declaration validation, hook loading and its call. It restores previous `sys.modules` identities and `sys.path`, and removes newly introduced matching modules, on success and failure, including when the incoming directory was already later on `sys.path`.
- The hook runs at most once per upgrade invocation. Opted-in retries require a hook that is idempotent; there is no exactly-once-across-crashes guarantee. A hook failure skips dependent migration with a diagnostic naming the hook and exception class only. The framework does not roll back hook-owned partial effects.
- To preview the mechanical half on demand, call `upgrade_extensions.migrate_journals(<repository root>, apply=False)` with the framework scripts on `sys.path`. It changes nothing, never calls the hook, and executes no declaration or distribution helper; trusted shipped read-only framework helpers may supply bounded reads. Templates and trigger policy are read statically. Its `deleted`, `moved`, `left` and `warnings` lists retain their meanings, and `hook_preview` reports `policy` (`legacy_cutover`, `journals_present` or null), `status` (`valid`, `invalid` or `unknown`), `qualifying_journals`, `hook_executed: false` and `invocation: "upgrade_apply_only"`, with optional path-free `detail` for invalid/unknown policy. If `zip_path` is supplied, policy comes from that incoming pack; otherwise it comes from the target declaration. Upgrade dry-run's `post_extract` prints this static hook preview. Current source presence is an observation, not a promise of eligibility when apply reaches `pre_docs_gate`. Public `migrate_journals(..., apply=True)` performs the mechanical migration and still never calls the hook.

Tasks:

1. List the remaining files under `docs/agents/journals/` (the latest upgrade output already names them).
2. For each remaining WAVE journal: move it into its wave's directory when one exists, naming the relocated file `<prefix>-jrnl <slug>.md` (the wave id split on its first space — the same typed form the upgrade's mechanical relocation mints); extract any still-current lesson into a typed memory candidate with evidence references; delete only when the content has been relocated or captured.
3. For each ROLE journal: preserve its content in a history document under `docs/agents/history/`, with its source role identified and the required role metadata; promote durable role lessons as memory candidates; remove the journal reference (and any `## Associated journal` section) from persona docs; then retire the file.
4. When the directory is empty, remove `docs/agents/journals/` and its README, and update any remaining live references.
5. Validate every extracted candidate with `memory_validate` (promote, retain, reject, or rewrite) — never leave candidates pending.
6. Finish with the docs gate: `wf_garden_docs`, then `wf_validate_docs`.

Guardrails:

- Never delete content that has not been either relocated or captured as a validated memory record.
- Closed-wave archives and events ledgers keep their historical journal references; do not rewrite history.
- Do not invent lessons — extract only from existing entries.
- Do not promote unvalidated lessons.
