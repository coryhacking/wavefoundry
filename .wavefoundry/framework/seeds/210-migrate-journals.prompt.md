# 210 - Migrate Journals (Operator-Invoked, One-Time)

Intent:

- Complete the retirement of the journal system in a repository that still carries journal files: promote still-valuable findings into typed memory candidates, archive role-journal content in a history document, relocate historical wave journals into their wave directories, and remove only what has been captured or provably carries nothing.

Context:

- Wave journals and the distill-at-close pipeline are retired. The memory system owns durable capture: `memory_add(status='candidate', ...)` for in-flight lessons, `memory_propose` plus `memory_validate` at wave close.
- Upgrades already perform the mechanical half automatically: a journal byte-identical to the pristine generated scaffold is deleted (zero information loss), and a content-bearing wave journal moves into its wave's directory when that directory exists. The upgrade report lists everything it left behind — role journals, template drift, or journals whose wave directory is missing. This prompt finishes that remainder with judgment. To preview the mechanical half on demand, call `upgrade_extensions.migrate_journals(<repository root>, apply=False)` with `.wavefoundry/framework/scripts` on `sys.path`: it reports what it would delete, move and leave (with reasons) and changes nothing; `apply=True` performs it. It follows the record vocabulary profile's id key and nested waves, refuses any journal or folder reached through a link, and leaves a journal whose wave is archived (the archive is read-only) or whose id is ambiguous. A distribution can declare its own pristine journal scaffolds and a hook that runs right before the upgrade's migration in `mcp_tool_extensions.py` (`EXTENSION_JOURNAL_TEMPLATES` and `EXTENSION_JOURNAL_PRE_MIGRATION_HOOK`); the preview uses the same templates and never calls the hook.

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
