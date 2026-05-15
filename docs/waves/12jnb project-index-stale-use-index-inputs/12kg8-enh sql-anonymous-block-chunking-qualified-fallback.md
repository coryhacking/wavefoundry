# SQL Anonymous Block Chunking and Qualified Fallback

Change ID: `12kg8-enh sql-anonymous-block-chunking-qualified-fallback`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-05-13
Wave: `12jnb project-index-stale-use-index-inputs`

## Rationale

The recent SQL test pass showed that named SQL objects are usable, but anonymous `DO $$ ... $$` blocks can still disappear from semantic search and schema-qualified identifiers can fall back too early. This change combines the strongest follow-up fixes into one scope so SQL migration scripts remain searchable even when they are procedural, anonymous, or not structured as a named object.

## Requirements

1. SQL `DO` blocks should be chunked into meaningful units instead of being treated as a single opaque blob or skipped entirely.
2. Anonymous SQL blocks should be recognized for both `DO $$ ... $$` and `DO $tag$ ... $tag$` forms.
3. Schema-qualified SQL identifiers should retry lookup without the schema prefix before falling back to keyword search.
4. SQL files that would otherwise produce zero searchable SQL chunks should still contribute one file-level safety-net chunk.
5. Existing SQL chunking and navigation behavior for named objects must remain intact.

## Scope

**In scope:**

- `.wavefoundry/framework/scripts/chunker.py`
- `.wavefoundry/framework/scripts/server.py`
- `.wavefoundry/framework/scripts/tests/test_chunker.py`
- `.wavefoundry/framework/scripts/tests/test_server_tools.py`

**Out of scope:**

- Changing SQL alias detection
- Reworking the broader semantic index format
- Removing tree-sitter or regex fallback behavior

## Acceptance Criteria

- Anonymous `DO $$` and tagged `DO $tag$` SQL blocks appear as chunkable/searchable units, with one chunk per block.
- `code_definition` and `code_references` can resolve common schema-qualified SQL symbols by retrying the unqualified name before falling back.
- SQL files with no searchable SQL chunks still emit a file-level chunk so they are not completely dark to semantic search.
- The existing broad retrieval contract remains unchanged for other languages and for SQL named-object cases.

## Tasks

- Add anonymous SQL block detection and chunk emission
- Add schema-qualified name fallback for SQL symbol lookup
- Add file-level safety-net chunking for SQL files with no named chunks
- Add tests covering each gap surfaced by the SQL report

## AC Priority

| AC | Priority | Rationale |
| -- | -------- | --------- |
| AC-1 | required | Anonymous migration blocks are the biggest search gap |
| AC-2 | required | Qualified SQL names are common in real repositories |
| AC-3 | required | Files that otherwise yield zero searchable SQL chunks still need a fallback chunk |
| AC-4 | required | Existing broad behavior must remain stable |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Anonymous block detection over-splits procedural SQL | Keep the block detector conservative and test with representative migration files |
| Unqualified fallback produces false positives | Retry the schema-stripped name only after the qualified lookup fails |
| Safety-net chunks reduce precision in script-heavy repos | Limit the safety net to files that would otherwise yield zero named chunks |
