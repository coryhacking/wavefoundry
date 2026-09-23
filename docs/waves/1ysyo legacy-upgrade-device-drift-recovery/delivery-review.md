# Guidance delivery review

Owner: Engineering
Status: active
Last verified: 2026-09-22

Verdict: QA and docs-contract approved for the guidance-only scope; no blocking finding.

One fresh independent reviewer context, `/root/guidance_delivery`, covered both lanes. This is one assessment from an agent that did not author the guidance, not two independent reviewers. Required orientation exposed earlier evidence; the verdict rests on independent live diff/source inspection and the checks below.

## Executed checks

AC-1: Independently read `v1.25.0` via `git show`: `sqlite_storage_migration.read_receipt` compares the complete root identity; `upgrade_wavefoundry.main` calls `restore_checkpoint` at historical line 4778 before incoming `_load_extension_module` at 5495 (also before earlier phase-specific loaders). Current live MCP `code_read` confirms `read_receipt` uses `same_path` plus `compare_identity`, returns the original record without writing, and `restore_checkpoint` calls it before accepting a complete receipt. `storage_identity.compare_identity` rejects malformed identity, uses available inode, and separately reports device drift. The documented replacement-volume/reused-inode limitation matches its module contract. The original tester revision is still unknown; the guidance requires actual source/hash evidence.

AC-2: Walked the published four-step procedure against the following cases, using the independently read requirements as the oracle:

| Input / transition | Expected and observed instruction |
| --- | --- |
| Complete valid receipt; same resolved path and nonzero inode; only device differs; verified old reader | Collect exact source/archive evidence, verify incoming behavior, obtain qualified repair, present diff/backups/recovery for scoped approval, stop hosts, apply approved repair only, retry same archive in a fresh CLI process |
| Changed path or inode | Step 2 stops before repair authorization; preserve evidence and seek continuation/help |
| Malformed identity or missing inode evidence | Step 2 stops; the procedure deliberately requires stronger evidence than the runtime's path-only fallback |
| Uncertain ownership, incomplete migration, retained setup or upgrade checkpoint | Step 2 stops this exceptional procedure and defers to existing continuation/help |
| Version label matches but actual reader unknown | Step 2 disallows treating the label as proof; cannot reach confirmed-defect repair |
| Confirmed defect but no verified exact-build repair | Step 3 stops and hands collected evidence to maintainer |
| Repair found but no scoped approval | Step 3 does not authorize installed-code mutation |
| Repair applied, original archive retained | Step 4 requires ordinary CLI and normal gates; copy/reload/version label does not establish completion |

Executed one bounded parameterized contract probe with Python, zero skips. It read both actual authored carriers, required the stop/approval clauses from AC-2, then mutated only in-memory copies: replacing `retained upgrade/setup checkpoint stops this procedure` with permission to repair, and replacing `scoped operator approval` with automatic application. Both known-bad copies failed the checks while the live text passed. This proves contract presence and detectability, not future agent adherence or successful installed-code repair.

AC-3: The same probe asserted byte-for-byte equality of the entire new Older reader section, required the new reconciliation clause in both carriers, and compared each carrier's complete renderer marker regions against HEAD with no differences. Live `git diff`/`git status` showed only seed 160, local upgrade prompt and CHANGELOG among preexisting tracked changes; the changelog expressly says no automatic repair. No executable code, identity comparison or manifest/version changed. Direct package-seed reading and authored reconciliation are explicit; rendering alone is explicitly insufficient.

## Limits and evidence

Evidence: this report and `review.md`; resolvable implementation anchors are `read_receipt`, `restore_checkpoint`, `upgrade_wavefoundry.main`, `same_path`, and `compare_identity`. MCP-first `code_ask` reported stale index freshness; live `code_read`/`code_outline` and exact historical `git show` supplied the source evidence. Gapfill: shell was used for historical Git content, live diff, and mechanical prose parity/mutation probes because these inspect history or exact bytes rather than indexed retrieval.

The finite review budget was one parameterized prose-boundary probe plus manual decision walkthroughs and source inspection. No production recovery state or installed code was mutated. The full framework suite remains coordinator-owned and is not claimed as completed by this review. This approval qualifies guidance, not a specific repair, whole old-installation upgrade, host shutdown, or tester reproduction. No new runtime mechanism exists to exercise in this wave.
