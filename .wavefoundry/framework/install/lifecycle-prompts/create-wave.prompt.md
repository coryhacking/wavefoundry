# Create Wave

Owner: Engineering
Status: active
Last verified: {{generated_at}}

Shortcut: **`Create wave`**

## Purpose

Use the existing wave `## Objective` for the shared outcome of admitted changes: who benefits, what observably improves, and material boundaries. Do not add a second wave-level intent section or duplicate change requirements and tasks.

Create a wave record for a bounded set of already-planned changes. Creation
does not imply readiness, implementation approval, or delivery approval.

## Contract

1. Use `wf_create_wave` when the Wavefoundry MCP server is available.
2. Admit only named specs; do not silently add unrelated work.
3. Create `docs/waves/<wave-id>/wave.md`; create sibling `events.jsonl` as an
   exactly empty file. That fixed sibling ledger is the sole machine authority
   for review evidence.
4. Declare the external evidence authority exactly:

   `review-evidence-source: events.jsonl`

5. Include the generated `## Finding Synthesis` projection in `wave.md`.
   Canonical review events remain in `events.jsonl`; never hand-author JSONL
   inside the Markdown record.

   ```markdown
   ## Finding Synthesis

   No review findings recorded.
   ```
6. Preserve operator and project-authored prose outside framework-owned marker
   regions.
7. Leave the new wave planned. Run **Prepare wave** before implementation.

## Verification

- The admitted change IDs resolve uniquely.
- No duplicate staged and wave-owned specs exist.
- `events.jsonl` is present and empty at creation.
- The wave record names the admitted changes and next action.

## Disposable work

Use the lifecycle-reported `.wavefoundry/work/<wave-id>/`, keyed by the resolved unique prefix, for shared temporary work; include the path and availability notices in coordinator briefs. Follow seed 180’s **Disposable work** and seed 209’s **Review Artifact Discipline**. Reads and dry-runs create nothing; unavailable work is advisory and existing host permissions apply.

Write every file you create for a wave, including coordinator briefs, logs, captured test output and build output, inside that wave's own work folder, in a child folder when that helps; never write a file directly in `.wavefoundry/work/`. Before the wave exists, keep the content in task context until a lifecycle call reports the work area. `wf_audit` and close report files and links left directly in the work root as the advisory `work_root_loose_files`. If you wrote such a file for a wave, move it into that wave's folder while the wave is open, or delete it. Leave any other loose file in place, including one you are not sure you wrote (a name that starts with a wave id does not prove who wrote it), and report it to the operator, who decides. Never move a file you did not write into a wave's folder: close removes that folder with everything in it.
