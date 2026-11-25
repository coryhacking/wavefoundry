# Security review: wave 24buu readiness

Owner: Engineering
Status: active
Last verified: 2026-11-24

- Lane: security-reviewer, readiness phase, fresh context, independent of the planner and red team.
- Verdict: needs-revision. One required finding (S1) on 24ax3. No approval recorded.
- Retrieval: wavefoundry MCP first (`code_keyword`, `wf_review_wave`). Gapfill: shell `sed`/`grep` for line ranges in long files, and one `python3 -B` read-only check that no framework script name shadows a stdlib module. No repository file was edited; no real user or system settings file was read.
- Read: `wave.md`, all five specs, the red-team primer, `spec_tool_permissions.py` (whole file), `render_platform_surfaces.selected_permission_rules` and `render_claude_permissions`, `mcp_tool_roster.spec_permission_holds`, `contained_files.read_contained_bytes`, `render_agent_surfaces._comparable_baseline` and `_baseline_marker_pairs`, `upgrade_bundle` path handling, the threat model and `.gitignore`.

## F1 and F2: does the 24ax3 revision close them?

Mostly yes, inside the repository.

- **Receipt meaning (F1).** Requirement 7 gives the upgrade receipt its own body, and `_review_held` accepts it next to `_RECEIPT`. A receipt no longer claims an operator review that did not happen. The scope stays `_receipt_path` (workstation, `Path.home()`, absolute checkout). The cache is gitignored (`.gitignore` `.wavefoundry/cache/`), and the writer shared with `acknowledge` uses `write_contained_bytes(..., mode=0o600, no_links=True)`.
- **Separated holds (F2).** Requirement 4 splits repository, outside-layer and review holds. Requirement 7 writes a receipt only when there is no repository hold and no outside-layer hold. Repository holds are evaluated live on every `assess` call, so a receipt never overrides a later repository rule.
- **Repository pattern rules.** `_claude` matches with `fnmatchcase`. A deny or ask on `mcp__wavefoundry__wf_*_change` matches the old name and not the new one, so `equivalent` is false and the route is held. Requirement 2.3 and AC-5 keep this.
- **Constrained rules.** Requirement 3 accepts only an identical constraint in the same list. Copying a rule within its own category never moves it between deny, ask and allow, and Claude's precedence (deny, then ask, then allow) keeps the copied deny or ask over a managed allow.
- **Managed grants.** Requirement 2.1 leaves `wavefoundryManagedAllow` entries to the render, the same filter `_claude` applies. Managed grants therefore never become unmanaged permanent grants. After migration, `selected_permission_rules` still suppresses the managed allow for a held route and for a manual allow with no managed predecessor. Its `retained` branch keeps the old managed rule only while the route is held.
- **Malformed or symlinked repository files.** `_read` uses `follow_links=False`. A refusal or parse error falls into `assess`'s `except (OSError, ValueError)` and holds every route, which fails closed. Requirement 8 and AC-3 keep this.

## S1 (required, 24ax3): the outside-layer hold rule is narrower than the Boundary it implements

The Boundary says upgrade "never serves a tool that a readable layer restricts under its old name without the same restriction on the new name". Requirement 5 implements this only for exact Claude-style `deny` or `ask` rules. Three host-effective restrictions are left out. Each one gets an upgrade receipt and serves the new name with nothing restricting it:

1. **Codex user config has no hold mapping.** Requirement 5 reads `$CODEX_HOME/config.toml` but defines holds only in Claude vocabulary. Codex has no deny or ask lists; its restrictions are `disabled_tools` and per-tool `tools.<name>` tables. The repository reader already treats both as policy (`spec_tool_permissions._codex`). With a user-level `disabled_tools = ["wf_close_change"]`, or a `tools.wf_close_change` approval table, the requirement as written holds nothing. AC-4 tests only Claude. Repair: reuse `_codex` on the outside file in restriction-only mode. Hold on an old name in `disabled_tools` without the new name, and on a `tools.<old>` table that differs from `tools.<new>`. An `enabled_tools` mismatch narrows the grant, so it only recommends. Add an AC-4 Codex row.
2. **Outside pattern rules are ignored.** Requirement 5 says "exact old name". In the repository, a deny on a pattern such as `*_change` holds the route (requirement 2.3, AC-5), but in `~/.claude/settings.json` the same pattern holds nothing. Repair: use `_claude`'s matcher for outside layers, so that any deny or ask that matches the old name but not the new one holds the route. Whether the host honors partial globs is unverified. The repository reader already assumes it does, and the outside reader should be consistent with it.
3. **Unreadable outside files fail open.** Requirement 5 says "An unreadable or malformed outside file ... holds no route." Dotfile managers commonly make `~/.claude/settings.json` a symlink. If the reader reuses `_read` or `read_contained_bytes(follow_links=False)`, as the rest of the module does, a symlinked user file reads as unreadable. The user's deny is then skipped while the host follows the link and applies it. A UTF-8 BOM or another parser difference has the same effect. Repair: read outside files read-only and follow links. When a file exists but cannot be read or parsed, hold every route whose old name appears as a token in whatever bytes can be read (the Cursor rule in `assess`), or hold every route when no bytes can be read.

Classification:

- **Attacker reachability:** false. No less-trusted actor controls these files; they are operator-owned policy.
- **Supported reachability:** true. A user-level Codex `disabled_tools`, or a symlinked Claude user file, is a supported configuration.
- **Authority:** integrity. Agents gain unprompted use of a tool the operator's own policy restricted under its old name, which is the delta F1 was about.
- **Severity:** required_ac. This is a correctness defect in a safety control, not an escalation. The repair is bounded and safe: it is text in requirement 5 plus AC-4 rows.
- **Anchors:** `spec_tool_permissions._codex`, `spec_tool_permissions._claude`, `spec_tool_permissions._read`, `spec_tool_permissions.assess`; 24ax3 Boundaries, requirement 5 and AC-4.

## Notes (non-blocking)

- **N1 (24ax3, layers the upgrade cannot read).** These host layers are standard, not "nonstandard": macOS MDM plist policy, the Windows registry policy, server-managed settings, a possible `managed-settings.d` drop-in directory (unconfirmed), and launch flags. Name them in the requirement 10 guidance. Have the receipt body list the files the upgrade actually read, so the attestation can be audited.
- **N2 (24ax3, environment mismatch).** The CLI upgrade reads `CLAUDE_CONFIG_DIR` and `CODEX_HOME` from the terminal. The host may have been launched with different values. Requirement 5 should state this residual, and the summary should print the resolved paths.
- **N3 (24ax3, existing receipts).** The upgrade writer must leave an existing valid operator or upgrade receipt unchanged. This is consistent with requirement 9.
- **N4 (24ax3, Codex text insertion).** After the insertion, re-parse with `tomllib` and confirm that the only semantic change is the intended addition under `mcp_servers.<server>`; otherwise do not write and keep the hold. Inline tables, dotted keys and multi-line arrays with comments are the risk shapes.
- **N5 (24ax3, docstring).** Update `render_claude_permissions`'s boundary docstring. The agent-callable `wf_upgrade` now also writes `.claude/settings.local.json` and `.codex/config.toml`. It copies rules only and never adds authority.
- **24bn8.** The overwrite cannot clobber a project edit. `_comparable_baseline` removes only newline style, the `Last verified` date and renderer-owned regions, and the renderer re-renders those regions in the same pass. Requirement 2 adds header labels to the normalized form, so an edit to a label token alone would be replaced. That is acceptable. The digest check, the symlink and outside-checkout skip and contained atomic writes (requirements 1, 3 and 4, AC-4) prevent link following. Residual: a same-user edit between the check and the write.
- **24bn7.** A sys.path entry of `<zip>/.wavefoundry/framework/scripts` resolves only through zipimport inside the archive file. No framework script name shadows a stdlib module (checked). The documented command is not `-I`, so a `PYTHONPATH` entry could shadow `contained_files` if the zip entry is appended. Insert the entry directly after the zip root (index 1) and build it from the zip's own `__file__`. The PYTHONPATH case is a same-user residual.
- **24bn9.** Automatic cleanup runs the same extracted `--cleanup` the operator already authorized, so it adds no new authority. The MCP discriminator (F8) is a correctness matter for the architecture lane. If a stale MCP handler runs a 1.52 primary without `--no-auto-cleanup`, cleanup removes the lock early. That is an availability issue, not a security one.
- **24but.** No trust-boundary change.

## Exploit chains

None. S1 concerns the operator's own policy, so no less-trusted actor and no chain is involved.
