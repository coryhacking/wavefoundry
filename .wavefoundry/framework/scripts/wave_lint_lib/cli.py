from __future__ import annotations

import argparse
import sys
import time
from contextlib import contextmanager
from pathlib import Path

from .context import build_context
from .constants import AUDIT_DEFAULT_REPORT
from .core_validators import check_forbidden_root_wrappers, check_prompt_file_extensions, check_prompt_surface_manifest, check_pycache, check_required_files, check_seed_prefix_uniqueness, check_workflow_config
from .design_system_validators import check_design_system
from .design_system_governance_validators import check_design_governance
from .design_system_surface_validators import check_design_surface
from .constants import DOCS_LINT_MAX_FILE_BYTES_DEFAULT
from .helpers import (
    _ENTRY_FILES,
    iter_linkable_docs,
    iter_markdown_docs,
    load_json,
    read_text_cache_clear,
    relative_to_root,
    write_if_changed,
)
from .link_validators import check_markdown_links
from .metadata_validators import check_metadata
from .secrets_validators import _get_changed_files, _is_inside_git, check_hardcoded_secrets
from .wave_validators import (
    check_closed_wave_requirements,
    check_cross_artifact_consistency,
    check_factor_surface,
    check_prepare_council_roster_evidence,
    check_prepare_council_verdict,
    _check_agent_category_metadata,
    _check_agent_role_metadata,
    check_journal_docs,
    check_migration_edges,
    check_persona_docs,
    check_plan_filenames,
    check_wave_docs,
    check_wave_roots,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Wave framework docs lint")
    parser.add_argument(
        "--write-migration-audit",
        action="store_true",
        help="Write a stable migration-audit report for warnings/info using write-if-changed semantics",
    )
    parser.add_argument(
        "--migration-audit-path",
        default=AUDIT_DEFAULT_REPORT,
        help="Project-root-relative output path for the optional migration audit report",
    )
    parser.add_argument(
        "--scan-all",
        action="store_true",
        help="Scan all repo files for secrets (default: wave-touched files only)",
    )
    parser.add_argument(
        "--changed",
        action="store_true",
        help=(
            "Incremental mode (wave 1p9c1): self-detect the git working-tree changed set and run "
            "only the per-file validators on changed docs/ markdown, skipping corpus-wide checks. "
            "A changed config file falls back to the full lint. The authoritative full gate stays "
            "at wave_validate / wave_close / prepare / install / upgrade (which call without this flag)."
        ),
    )
    parser.add_argument(
        "--timings",
        action="store_true",
        help=(
            "Measurement (wave 1p9c6): print `TIMING: <phase> <ms>` per full-lint phase "
            "(secrets/corpus/metadata/links) plus `TIMING: total <ms>` to stderr, without changing "
            "pass/fail, the `docs-lint: ok` line, or the exit code. Inert in incremental (--changed) mode."
        ),
    )
    return parser.parse_args()


@contextmanager
def _timed(timings, name: str):
    """Accumulate wall-clock ms for a phase into ``timings`` (a no-op when ``timings`` is None)."""
    if timings is None:
        yield
        return
    start = time.perf_counter()
    try:
        yield
    finally:
        timings[name] = timings.get(name, 0.0) + (time.perf_counter() - start) * 1000.0


def _docs_lint_max_file_bytes(root: Path) -> int:
    """Wave 1p9cj: the docs-lint file-size cap. Reads docs/workflow-config.json `docs_lint.max_file_bytes`
    (fail-safe to the 5 MB default on missing/malformed), mirroring `docs_lint.hook_timeout_seconds`."""
    cfg = root / "docs" / "workflow-config.json"
    if cfg.is_file():
        data, err = load_json(cfg)
        if err is None and isinstance(data, dict):
            dl = data.get("docs_lint")
            if isinstance(dl, dict):
                value = dl.get("max_file_bytes")
                if isinstance(value, int) and not isinstance(value, bool) and value > 0:
                    return value
    return DOCS_LINT_MAX_FILE_BYTES_DEFAULT


def _oversized_docs(root: Path, paths, cap: int) -> "tuple[set, list]":
    """Wave 1p9cj: one `stat` pass — return (oversized_paths, warnings). An oversized doc's content
    validators are skipped (the file is never read into the cache by those checks) with a loud
    non-blocking WARNING naming the size, cap, and remedy. docs-lint is a correctness gate, so this is a
    WARNING (visible), never a silent skip and never a blocking ERROR (a legit large generated doc must
    not fail-close)."""
    oversized: set = set()
    warnings: list = []
    for path in paths:
        try:
            size = path.stat().st_size
        except OSError:
            continue
        if size > cap:
            oversized.add(path)
            rel = relative_to_root(root, path)
            warnings.append(
                f"{rel}: {size} bytes exceeds the docs-lint file-size cap ({cap} bytes) — content "
                f"validators skipped for this doc; split it, move it under docs/reports/, or raise "
                f"`docs_lint.max_file_bytes` in docs/workflow-config.json"
            )
    return oversized, warnings


def _render_audit_report(warnings: list[str], infos: list[str]) -> str:
    lines = [
        "# Wave Migration Audit",
        "",
        "This report is generated by `.wavefoundry/framework/scripts/docs_lint.py`.",
        "It is report-first and does not imply metadata normalization.",
        "",
        "## Warnings",
        "",
    ]
    if warnings:
        lines.extend(f"- {warning}" for warning in warnings)
    else:
        lines.append("- none")
    lines.extend(["", "## Info", ""])
    if infos:
        lines.extend(f"- {info}" for info in infos)
    else:
        lines.append("- none")
    lines.append("")
    return "\n".join(lines)


# Wave 1p9c1: config/corpus files whose correctness is inherently cross-file. A change to any of
# these forces the incremental path to fall back to the full lint — the per-file validators do not
# cover JSON, and the cross-artifact / factor-surface checks need the whole set.
# Review-fix (1p9pe follow-up hardening): public constant — `server_impl.run_validate_changed`
# imports it to PREDICT the full-lint fallback and bound the subprocess with the full-scan
# timeout knob instead of the lighter hook knob (the two must not cross over).
INCREMENTAL_FULL_FALLBACK_FILES = (
    "docs/workflow-config.json",
    "docs/prompts/prompt-surface-manifest.json",
    "docs/repo-profile.json",
)


def _run_incremental_checks(root: Path):
    """Post-edit incremental lint (wave 1p9c1).

    Self-detects the git working-tree changed set (reusing secrets' ``_get_changed_files`` — the same
    signal secrets already lints on) and runs only the per-file validators on changed ``docs/``
    markdown, skipping the corpus-wide checks. Returns ``(failures, warnings)``, or ``None`` to signal
    the caller to run the FULL lint (a changed config file whose correctness is cross-file). An empty
    or non-git changed set is a safe ok no-op (``([], [])``) — it never falls through to a whole-tree
    scan. The authoritative corpus lint stays at wave_validate / wave_close / prepare / install /
    upgrade, which call the cli without ``--changed``."""
    changed = _get_changed_files(root)
    fallback_files = {root / rel for rel in INCREMENTAL_FULL_FALLBACK_FILES}
    if any(path in fallback_files for path in changed):
        return None  # a config/corpus file changed → run the full lint

    failures: list[str] = []
    warnings: list[str] = []

    # Secrets stays incremental (scan_all=False → git-touched only) and record-only, run on every
    # edit — secrets live in code as well as docs, so this must not be gated on a docs change.
    failures.extend(check_hardcoded_secrets(root, scan_all=False, record_only=True))

    docs_root = root / "docs"
    changed_docs = {p for p in changed if p.suffix == ".md" and docs_root in p.parents}
    changed_entry = {p for p in changed if p.parent == root and p.name in _ENTRY_FILES}

    # Wave 1p9cj: the file-size guard applies incrementally too — an oversized changed doc is skipped
    # with a loud non-blocking WARNING rather than pulled through the regex/section passes + the cache.
    cap = _docs_lint_max_file_bytes(root)
    oversized, size_warnings = _oversized_docs(root, changed_docs | changed_entry, cap)
    warnings.extend(size_warnings)

    # Metadata is checked for docs/**/*.md; links for docs/**/*.md plus the root entry files.
    for path in sorted(changed_docs):
        if path in oversized:
            continue
        failures.extend(check_metadata(root, path))
    for path in sorted(changed_docs | changed_entry):
        if path in oversized:
            continue
        failures.extend(check_markdown_links(root, path))

    if changed_docs:
        failures.extend(check_journal_docs(root, only=changed_docs, skip=oversized))
        failures.extend(check_persona_docs(root, only=changed_docs, skip=oversized))
        failures.extend(check_wave_docs(root, only=changed_docs, skip=oversized))
        failures.extend(check_plan_filenames(root, only=changed_docs, skip=oversized))
        failures.extend(_check_agent_role_metadata(root, only=changed_docs, skip=oversized))
        failures.extend(_check_agent_category_metadata(root, only=changed_docs, skip=oversized))

    return (failures, warnings)


def _run_full_checks(root: Path, args: argparse.Namespace, timings: dict | None = None):
    failures: list[str] = []
    warnings: list[str] = []
    infos: list[str] = []

    # Wave 1p9cj: file-size guard — one stat pass; oversized docs skip their content validators (below)
    # with a loud non-blocking WARNING. Protects the regex/section passes + the read cache from a
    # pathological multi-MB doc, matching the secrets/indexing file caps.
    cap = _docs_lint_max_file_bytes(root)
    oversized, size_warnings = _oversized_docs(root, iter_markdown_docs(root), cap)
    warnings.extend(size_warnings)

    # Wave 1p5pz: docs-lint detects + records secret findings but does NOT block on
    # them (record_only) — the secrets gate is enforced solely at wave_close. This keeps
    # the post-edit hook, wave_validate, and the upgrade docs gate from blocking on a
    # found secret; only a malformed inline-suppression directive (a real lint error) fails.
    with _timed(timings, "secrets"):
        failures.extend(check_hardcoded_secrets(root, scan_all=args.scan_all, record_only=True))
    # Wave 1p9c6: the corpus-wide + structural checks are grouped as one timing phase; the two per-file
    # loops (metadata/links) are timed separately since those are the parallelization candidates.
    with _timed(timings, "corpus"):
        failures.extend(check_required_files(root))
        failures.extend(check_forbidden_root_wrappers(root))
        failures.extend(check_prompt_file_extensions(root))
        failures.extend(check_pycache(root))
        failures.extend(check_seed_prefix_uniqueness(root))
        failures.extend(check_wave_roots(root))
        failures.extend(check_workflow_config(root))
        failures.extend(check_prompt_surface_manifest(root))
        failures.extend(check_wave_docs(root, skip=oversized))
        failures.extend(check_closed_wave_requirements(root))
        failures.extend(check_plan_filenames(root, skip=oversized))
        failures.extend(_check_agent_role_metadata(root, skip=oversized))
        failures.extend(_check_agent_category_metadata(root, skip=oversized))
        factor_failures, factor_warnings = check_factor_surface(root)
        failures.extend(factor_failures)
        warnings.extend(factor_warnings)
        failures.extend(check_journal_docs(root, skip=oversized))
        failures.extend(check_persona_docs(root, skip=oversized))
        failures.extend(check_cross_artifact_consistency(root))
        warnings.extend(check_migration_edges(root))
        council_errors, council_warnings = check_prepare_council_verdict(root)
        failures.extend(council_errors)
        warnings.extend(council_warnings)
        roster_errors, roster_warnings = check_prepare_council_roster_evidence(root)
        failures.extend(roster_errors)
        warnings.extend(roster_warnings)
        ds_failures, ds_warnings = check_design_system(root)
        failures.extend(ds_failures)
        warnings.extend(ds_warnings)
        gov_failures, gov_warnings = check_design_governance(root)
        failures.extend(gov_failures)
        warnings.extend(gov_warnings)
        surface_failures, surface_warnings = check_design_surface(root)
        failures.extend(surface_failures)
        warnings.extend(surface_warnings)

    with _timed(timings, "metadata"):
        for path in iter_markdown_docs(root):
            if path in oversized:
                continue
            failures.extend(check_metadata(root, path))

    with _timed(timings, "links"):
        for path in iter_linkable_docs(root):
            if path in oversized:
                continue
            failures.extend(check_markdown_links(root, path))

    return failures, warnings, infos


def _emit(
    failures: list[str],
    warnings: list[str],
    infos: list[str],
    root: Path,
    args: argparse.Namespace,
    incremental: bool,
    skipped: bool = False,
) -> int:
    """Shared output/exit contract for both the full and incremental paths.

    ``skipped`` (review-fix, 1p9pe follow-up hardening): the incremental path had no git
    changed-set to inspect (non-git checkout), so per-file docs checks ran on NOTHING. The
    final status line says so — ``docs-lint: skipped (no git changed-set available)`` —
    instead of an indistinguishable-from-checked ``docs-lint: ok``. Exit code stays 0: the
    advisory no-op contract is unchanged; only the honesty of the summary line changes.
    """
    if failures:
        for failure in failures:
            print(f"ERROR: {failure}", file=sys.stderr)
        for warning in warnings:
            print(f"WARNING: {warning}", file=sys.stderr)
        return 1

    for warning in warnings:
        print(f"WARNING: {warning}", file=sys.stderr)
    for info in infos:
        print(f"INFO: {info}", file=sys.stderr)

    # The migration-audit report is a whole-tree summary — only written by the full lint.
    if not incremental and args.write_migration_audit:
        report_path = root / Path(args.migration_audit_path)
        changed = write_if_changed(report_path, _render_audit_report(warnings, infos))
        print(
            f"migration-audit: {'updated' if changed else 'unchanged'} {report_path.relative_to(root)}",
            file=sys.stderr,
        )

    if incremental and skipped:
        print("docs-lint: skipped (no git changed-set available)")
    else:
        print("docs-lint: ok")
    return 0


def main() -> int:
    args = parse_args()
    context = build_context()
    root = context.root

    if not context.docs_root.exists():
        print("docs/: missing repository docs root", file=sys.stderr)
        return 1

    # Wave 1p9c6: clear the transparent read cache at the start of each run so a fresh invocation always
    # reflects on-disk state deterministically (the stat-identity key already handles cross-run edits;
    # this makes the guarantee explicit and keeps the cache bounded per run).
    read_text_cache_clear()

    # Wave 1p9c1: incremental (post-edit) mode runs only the per-file validators on the git-detected
    # changed docs. A changed config/corpus file returns None here → fall through to the full lint.
    # Wave 1p9c6: --timings is inert here — the incremental hot path stays quiet.
    if args.changed:
        incremental = _run_incremental_checks(root)
        if incremental is not None:
            failures, warnings = incremental
            # Review-fix (1p9pe follow-up hardening): distinguish "checked the changed set,
            # clean" from "had no changed set to check" — a non-git checkout's advisory
            # summary must not read as checked-and-clean.
            skipped = not _is_inside_git(root)
            return _emit(failures, warnings, [], root, args, incremental=True, skipped=skipped)

    # Wave 1p9c6: --timings records per-phase wall-clock without altering pass/fail or the exit contract.
    timings: dict | None = {} if args.timings else None
    total_start = time.perf_counter()
    failures, warnings, infos = _run_full_checks(root, args, timings=timings)
    if timings is not None:
        timings["total"] = (time.perf_counter() - total_start) * 1000.0
        for name in ("secrets", "corpus", "metadata", "links"):
            if name in timings:
                print(f"TIMING: {name} {timings[name]:.1f}", file=sys.stderr)
        print(f"TIMING: total {timings['total']:.1f}", file=sys.stderr)
    return _emit(failures, warnings, infos, root, args, incremental=False)
