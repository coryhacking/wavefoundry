# Create Wave

Shortcut: **`Create wave`**

## Purpose

Create a wave record for a bounded set of already-planned changes. Creation
does not imply readiness, implementation approval, or delivery approval.

## Contract

1. Use `wf_create_wave` when the Wavefoundry MCP server is available.
2. Admit only named change documents; do not silently add unrelated work.
3. Create `docs/waves/<wave-id>/wave.md`; create sibling `events.jsonl` as an
   exactly empty file, and record the zero-record adoption proof in
   `docs/waves/review-evidence-adoptions.json`.
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
- No duplicate staged and wave-owned change documents exist.
- `events.jsonl` is present and empty at creation.
- The wave record names the admitted changes and next action.
