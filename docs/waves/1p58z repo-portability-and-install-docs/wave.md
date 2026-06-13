# Wave Record

Owner: Engineering
Status: planned
Last verified: 2026-06-13

wave-id: `1p58z repo-portability-and-install-docs`
Title: Repo Portability And Install Docs

## Objective

Make a freshly-cloned wavefoundry repo work for contributors with no per-machine fixups, and give install-related docs one clear home. Today the rendered editor/MCP surfaces are committed with the author's absolute paths (so hooks and the MCP command break on clone), and install assets are scattered across four framework subtrees with a framework↔project duplicate. When this wave closes, every tracked file uses project-relative paths and install docs live in a single canonical location.

## Changes

Change ID: `1p590-maint project-relative-tracked-surfaces`
Change Status: `planned`

Change ID: `1p591-ref install-doc-home-consolidation`
Change Status: `planned`

## Wave Summary

Two coordinated repo-hygiene changes. `1p590` makes the platform-surface renderer emit project-relative command paths and reconciles the committed `.claude`/`.cursor`/`.github`/`.junie` surfaces so a clone works unmodified. `1p591` consolidates install docs (templates, release block, format spec, prompts) into one home and removes the framework↔project `install-log-format.md` duplicate, updating every consumer reference.

## Journal Watchpoints

- **Sequencing:** activate after `1p4wz` closes (single-open-wave rule). Both changes are independent of `1p4wz`'s embedding/retrieval scope.
- **Framework-edit gate:** `1p590` edits `render_platform_surfaces.py` + its tests; `1p591` moves framework docs and edits the scripts that reference them (`build_pack.py` reads `release/install-block.md`; setup reads the install templates). Open `framework_edit_allowed` before edits and close immediately after.
- **Blast radius — 1p590 (load-bearing):** the renderer drives EVERY downstream install's surfaces, so a relative-path regression breaks installs, not just this repo. Verify rendered output from a non-author checkout path (fresh-clone simulation) and that a case-insensitive `git grep "/Users/"` over tracked surfaces is empty.
- **Blast radius — 1p591:** moving seeds/templates/release blocks has hard-coded path consumers; move the source-of-truth and update references together, gate on the full suite + docs-lint. Mirrors the `1p4ww` framework/project fold (same dedup discipline).
- **Decision (portability form):** operator chose project-relative paths everywhere in tracked files; only gitignored files may stay machine-specific, and the operator chose to keep the surfaces committed (portable) rather than gitignore them. Prefer relative paths; use `$CLAUDE_PROJECT_DIR` only where a tool cannot resolve a relative command — confirm per-tool support at prepare.
- **Prepare-phase Wave Council readiness review** is the last step before this wave is ready to activate.

## Review Evidence

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies.
