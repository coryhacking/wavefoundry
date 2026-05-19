#!/usr/bin/env python3
"""Automated Wavefoundry upgrade script.

Handles the mechanical phases of a framework upgrade so the agent retains
ownership of high-judgment editing work (drift detection, journal
reconciliation, spec gap remediation).

Usage:
    python3 .wavefoundry/framework/scripts/upgrade_wavefoundry.py [options]

Phases (run in order when no phase flag given):
    Phase 0 — Pre-flight: dashboard check, version guard, MANIFEST backup,
              zip detection, change plan, confirmation prompt, lock file write.
    Phase 1 — Surface rendering: render_platform_surfaces.py
    Phase 2 — Pruning: prune_framework.py --old-manifest <saved MANIFEST>
    Phase 3 — Docs gate: docs-gardener && docs-lint

Separate phase (called after agent editing pass):
    Phase 4 — Index rebuild: setup_index.py --full (docs) then
              setup_index.py --background-code --full (code, background)

Phase 5 — Cleanup (called after phase 4, or via --cleanup):
    Remove upgrade lock; print operator summary.

Exit codes:
    0 — success
    1 — docs gate failed
    2 — surface rendering failed
    3 — pre-flight check failed (downgrade detected, lock already present, etc.)
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

# ── Resolve paths ─────────────────────────────────────────────────────────────

SCRIPTS_DIR = Path(__file__).resolve().parent
FRAMEWORK_DIR = SCRIPTS_DIR.parent
BIN_DIR = FRAMEWORK_DIR / "bin"

OLD_MANIFEST_TMP = Path(
    os.environ.get("TMPDIR", "/tmp")
) / "wf-manifest-old.txt"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _log(msg: str) -> None:
    print(msg, flush=True)


def _err(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr, flush=True)


def _detect_dashboard(root: Path) -> tuple[bool, int | None, str | None]:
    """Return (running, pid, url) for the local dashboard."""
    meta = root / ".wavefoundry" / "dashboard-server.json"
    if not meta.exists():
        return False, None, None
    try:
        data = json.loads(meta.read_text(encoding="utf-8"))
        pid = data.get("pid")
        url = data.get("url")
        if isinstance(pid, int) and pid > 0:
            # Quick liveness check
            try:
                os.kill(pid, 0)
                return True, pid, url
            except (ProcessLookupError, OSError):
                pass
    except (OSError, json.JSONDecodeError):
        pass
    return False, None, None


def _find_zip(root: Path) -> Path | None:
    """Return the latest wavefoundry-*.zip at repo root, or None."""
    candidates = sorted(root.glob("wavefoundry-[0-9][0-9][0-9][0-9]-*.zip"))
    return candidates[-1] if candidates else None


def _read_pack_version(root: Path) -> str | None:
    p = root / ".wavefoundry" / "framework" / "VERSION"
    try:
        return p.read_text(encoding="utf-8").strip() or None
    except OSError:
        return None


def _read_installed_revision(root: Path) -> str | None:
    p = root / ".wavefoundry" / "framework" / "MANIFEST"
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return str(data.get("framework_revision", "")).strip() or None
    except (OSError, json.JSONDecodeError):
        return None


def _read_zip_version(zip_path: Path) -> str | None:
    """Read VERSION from inside the zip without extracting."""
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            names = zf.namelist()
            # VERSION lives at .wavefoundry/framework/VERSION inside the zip
            for candidate in (".wavefoundry/framework/VERSION", "framework/VERSION"):
                if candidate in names:
                    return zf.read(candidate).decode("utf-8").strip() or None
    except (OSError, zipfile.BadZipFile, KeyError):
        pass
    return None


def _detect_prompt_files(root: Path) -> list[str]:
    """Find docs/prompts/*.md files that lack .prompt.md extension (migration needed)."""
    prompts_dir = root / "docs" / "prompts"
    if not prompts_dir.is_dir():
        return []
    results = []
    for p in sorted(prompts_dir.rglob("*.md")):
        if p.name in ("index.md", "README.md"):
            continue
        if p.name.endswith(".prompt.md"):
            continue
        rel = p.relative_to(root)
        # Only maxdepth 2 from docs/prompts
        if len(rel.parts) <= 4:
            results.append(str(rel))
    return results


def _is_interactive() -> bool:
    return sys.stdin.isatty()


def _confirm_proceed(yes: bool) -> bool:
    if yes or not _is_interactive():
        return True
    try:
        answer = input("Proceed? [y/N] ").strip().lower()
        return answer in ("y", "yes")
    except (EOFError, KeyboardInterrupt):
        return False


def _run(cmd: list[str], root: Path, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=str(root), check=check)


def _bin_path(root: Path, name: str) -> str:
    """Return the platform-appropriate path for a bin script."""
    candidate = root / ".wavefoundry" / "bin" / name
    if candidate.exists():
        return str(candidate)
    # Fallback: call the Python script directly
    py = SCRIPTS_DIR / f"{name.replace('-', '_')}.py"
    return f"python3 {py}"


# ── Phase 0 — Pre-flight ──────────────────────────────────────────────────────

def phase_preflight(root: Path, yes: bool) -> tuple[str | None, str | None, Path | None]:
    """Run pre-flight checks and print change plan.

    Returns (from_version, to_version, zip_path).
    Exits with code 3 on any blocking pre-flight failure.
    """
    import upgrade_lib

    # Check for existing lock
    existing_lock = upgrade_lib.read_upgrade_lock(root)
    if existing_lock is not None:
        if upgrade_lib.is_lock_stale(root):
            _log("⚠  Stale upgrade lock detected (PID not running) — clearing it.")
            upgrade_lib.remove_upgrade_lock(root)
        else:
            _err(
                "Upgrade already in progress (upgrade-in-progress.json exists and PID is running).\n"
                f"  Lock: {upgrade_lib.upgrade_lock_path(root)}\n"
                "  If the previous upgrade crashed, remove the lock manually:\n"
                f"    rm {upgrade_lib.upgrade_lock_path(root)}"
            )
            sys.exit(3)

    # Dashboard check
    dash_running, dash_pid, dash_url = _detect_dashboard(root)
    if dash_running:
        _log(f"⚠  Dashboard is running (pid={dash_pid}, url={dash_url}) — it will pause during upgrade.")

    # Installed revision
    from_version = _read_installed_revision(root)

    # Detect zip
    zip_path = _find_zip(root)
    if zip_path:
        zip_version = _read_zip_version(zip_path) or "unknown"
        to_version = zip_version
    else:
        # No zip — upgrading using the current tree as-is
        to_version = _read_pack_version(root) or "unknown"
        zip_path = None

    # Version guard (R4)
    from check_version import compare_versions
    if from_version and to_version and to_version != "unknown":
        direction = compare_versions(to_version, from_version)
        if direction == "downgrade":
            _err(
                f"Pack downgrade detected: installed={from_version}, pack={to_version}.\n"
                "Downgrade is not supported. To force, manually unzip and run phases individually."
            )
            sys.exit(3)

    # Prompt file detection (R9)
    prompt_files = _detect_prompt_files(root)

    # Change plan (R6)
    _print_change_plan(
        root=root,
        from_version=from_version,
        to_version=to_version,
        zip_path=zip_path,
        dash_running=dash_running,
        prompt_files=prompt_files,
    )

    if not _confirm_proceed(yes):
        _log("Aborted.")
        sys.exit(0)

    return from_version, to_version, zip_path


def _print_change_plan(
    root: Path,
    from_version: str | None,
    to_version: str | None,
    zip_path: Path | None,
    dash_running: bool,
    prompt_files: list[str],
) -> None:
    _log("")
    _log("Wavefoundry Upgrade Plan")
    _log("=" * 40)
    _log(f"Pack version:       {to_version or '(unknown)'}")
    _log(f"Installed revision: {from_version or '(none)'}")
    if zip_path:
        _log(f"Zip to apply:       {zip_path.name}")
    else:
        _log("Zip to apply:       none (using current tree)")
    _log("Surfaces to render: hooks, MCP config, bin launchers, agent surfaces")
    if from_version:
        _log(f"Prune mode:         MANIFEST diff (old={from_version})")
    else:
        _log("Prune mode:         legacy removal list (no prior MANIFEST)")
    _log("Docs gate:          .wavefoundry/bin/docs-gardener && .wavefoundry/bin/docs-lint")
    if dash_running:
        _log("Dashboard:          running — will pause during upgrade, auto-restart after")
    else:
        _log("Dashboard:          not running")
    if prompt_files:
        _log("Prompt files needing .prompt.md rename:")
        for f in prompt_files:
            _log(f"  {f}")
    else:
        _log("Prompt files:       none (all already use .prompt.md extension)")
    _log("")


# ── Phase 1 — Surface rendering ───────────────────────────────────────────────

def phase_surface_rendering(root: Path) -> None:
    _log("\n── Phase 1: Surface rendering ──")
    script = SCRIPTS_DIR / "render_platform_surfaces.py"
    if not script.exists():
        _log("  render_platform_surfaces.py not found — skipping surface rendering.")
        return
    result = subprocess.run(
        [sys.executable, str(script), "--root", str(root)],
        cwd=str(root),
        check=False,
    )
    if result.returncode != 0:
        _err("Surface rendering failed.")
        sys.exit(2)
    _log("  Surfaces rendered.")


# ── Phase 2 — Pruning ─────────────────────────────────────────────────────────

def phase_pruning(root: Path) -> int:
    """Run prune_framework.py.  Returns number of files pruned."""
    _log("\n── Phase 2: Pruning ──")
    script = SCRIPTS_DIR / "prune_framework.py"
    if not script.exists():
        _log("  prune_framework.py not found — skipping pruning.")
        return 0
    cmd = [sys.executable, str(script)]
    if OLD_MANIFEST_TMP.exists():
        cmd += ["--old-manifest", str(OLD_MANIFEST_TMP)]
    result = subprocess.run(cmd, cwd=str(root), capture_output=True, text=True, check=False)
    if result.stdout:
        _log(result.stdout.rstrip())
    if result.returncode != 0:
        _log(f"  Pruning exited {result.returncode} — continuing (non-fatal).")
        return 0
    # Count pruned lines heuristically
    pruned = sum(1 for line in result.stdout.splitlines() if "removed" in line.lower() or "pruned" in line.lower())
    _log(f"  Pruning complete.")
    return pruned


# ── Phase 3 — Docs gate ───────────────────────────────────────────────────────

def phase_docs_gate(root: Path) -> None:
    _log("\n── Phase 3: Docs gate ──")
    gardener = root / ".wavefoundry" / "bin" / "docs-gardener"
    linter = root / ".wavefoundry" / "bin" / "docs-lint"

    for label, script in [("docs-gardener", gardener), ("docs-lint", linter)]:
        if script.exists():
            cmd: list[str] = [str(script)]
        else:
            # Fallback to Python script directly
            py_name = label.replace("-", "_") + ".py"
            py_script = SCRIPTS_DIR / py_name
            if py_script.exists():
                cmd = [sys.executable, str(py_script), "--root", str(root)]
            else:
                _log(f"  {label} not found — skipping.")
                continue

        result = subprocess.run(cmd, cwd=str(root), check=False)
        if result.returncode != 0:
            _err(f"Docs gate failed: {label} exited {result.returncode}")
            sys.exit(1)

    _log("  Docs gate: PASSED")


# ── Phase 4 — Index rebuild ───────────────────────────────────────────────────

def phase_index_rebuild(root: Path) -> None:
    _log("\n── Phase 4: Index rebuild ──")
    setup_script = SCRIPTS_DIR / "setup_index.py"
    if not setup_script.exists():
        _log("  setup_index.py not found — skipping index rebuild.")
        return

    _log("  Phase 4a: rebuilding docs index (blocking) ...")
    result = subprocess.run(
        [sys.executable, str(setup_script), "--root", str(root), "--full"],
        cwd=str(root),
        check=False,
    )
    if result.returncode != 0:
        _log(f"  ⚠  Docs index rebuild exited {result.returncode} — continuing.")

    _log("  Phase 4b: launching code index rebuild in background ...")
    background_cmd = [
        sys.executable, str(setup_script),
        "--root", str(root),
        "--background-code",
        "--full",
    ]
    kwargs: dict = {
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
        "stdin": subprocess.DEVNULL,
        "cwd": str(root),
    }
    if os.name == "nt":
        kwargs["creationflags"] = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True
    subprocess.Popen(background_cmd, **kwargs)
    _log("  Code index rebuild running in background.")


# ── Phase 5 — Cleanup & summary ───────────────────────────────────────────────

def phase_cleanup(
    root: Path,
    from_version: str | None,
    to_version: str | None,
    zip_path: Path | None,
    pruned_count: int,
    ran_index_rebuild: bool,
) -> None:
    import upgrade_lib

    _log("\n── Phase 5: Cleanup ──")
    upgrade_lib.remove_upgrade_lock(root)
    _log("  Upgrade lock removed — dashboard will trigger post-upgrade reindex.")

    _print_operator_summary(
        from_version=from_version,
        to_version=to_version,
        zip_path=zip_path,
        pruned_count=pruned_count,
        ran_index_rebuild=ran_index_rebuild,
    )


def _print_operator_summary(
    from_version: str | None,
    to_version: str | None,
    zip_path: Path | None,
    pruned_count: int,
    ran_index_rebuild: bool,
) -> None:
    from_str = from_version or "(none)"
    to_str = to_version or "(unknown)"
    _log("")
    _log("Upgrade complete")
    _log("=" * 40)
    _log(f"Version:            {from_str} → {to_str}")
    if zip_path:
        _log(f"Zip applied:        {zip_path.name}")
        _log("Zip retained:       yes (gitignored per seed-050)")
    else:
        _log("Zip applied:        none (upgraded from current tree)")
    _log("Surfaces rendered:  hooks, MCP config, bin launchers, agent surfaces")
    _log(f"Files pruned:       {pruned_count}")
    _log("Docs gate:          PASSED")
    if ran_index_rebuild:
        _log("Index rebuild:      docs layer complete, code layer running in background")
    else:
        _log("Index rebuild:      not run — call with --rebuild-index after editing pass")
    _log("Dashboard:          lock removed; auto-reindex will trigger on lock removal")
    _log("MCP restart needed: YES — restart MCP server to load upgraded server code")
    _log("")
    _log("Next steps for agent editing pass:")
    _log("  1. Drift detection (seed-160 step 6)")
    _log("  2. Journal reconciliation (seed-160 step 0e)")
    _log("  3. Spec gaps via seed-230 (seed-160 step 4 / 160 step 8)")
    _log("  4. Docs gate re-run after edits (wave_garden → wave_validate, or bin/docs-lint)")
    _log("  5. Index rebuild: upgrade-wavefoundry --rebuild-index")
    _log("  6. Cleanup lock after rebuild: upgrade-wavefoundry --cleanup")
    _log("")


# ── Main ──────────────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Automated Wavefoundry framework upgrade.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--root",
        default=".",
        help="Repository root (default: current directory)",
    )
    parser.add_argument(
        "--yes", "-y",
        action="store_true",
        help="Non-interactive mode: skip confirmation prompt",
    )
    parser.add_argument(
        "--rebuild-index",
        action="store_true",
        help="Run phase 4 (index rebuild) only — call after agent editing pass",
    )
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Run phase 5 (cleanup) only — removes the upgrade lock and prints summary",
    )
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()

    # Ensure upgrade_lib is importable (same directory as this script)
    if str(SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_DIR))

    import upgrade_lib

    # ── Standalone --rebuild-index ─────────────────────────────────────────
    if args.rebuild_index:
        phase_index_rebuild(root)
        return 0

    # ── Standalone --cleanup ───────────────────────────────────────────────
    if args.cleanup:
        lock = upgrade_lib.read_upgrade_lock(root)
        from_version = lock.get("from_version") if lock else None
        to_version = lock.get("to_version") if lock else None
        phase_cleanup(
            root=root,
            from_version=from_version,
            to_version=to_version,
            zip_path=None,
            pruned_count=0,
            ran_index_rebuild=False,
        )
        return 0

    # ── Full upgrade: phases 0–3 ───────────────────────────────────────────
    _log(f"\nWavefoundry Upgrade — {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")
    _log(f"Repository root: {root}")

    # Phase 0 — Pre-flight
    from_version, to_version, zip_path = phase_preflight(root, yes=args.yes)

    # Save old MANIFEST before zip extraction overwrites it
    old_manifest = root / ".wavefoundry" / "framework" / "MANIFEST"
    if old_manifest.exists():
        try:
            shutil.copy2(old_manifest, OLD_MANIFEST_TMP)
            _log(f"  Saved old MANIFEST to {OLD_MANIFEST_TMP}")
        except OSError as exc:
            _log(f"  ⚠  Could not save old MANIFEST: {exc}")

    # Write upgrade lock
    upgrade_lib.write_upgrade_lock(root, from_version=from_version, to_version=to_version or "unknown")
    _log(f"  Upgrade lock written — dashboard will pause indexing.")

    try:
        # Apply zip if found
        if zip_path:
            _log(f"\n── Phase 0b: Applying zip {zip_path.name} ──")
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(str(root))
            _log(f"  Extracted {zip_path.name}")

        # Phase 1
        phase_surface_rendering(root)

        # Phase 2
        pruned_count = phase_pruning(root)

        # Phase 3
        phase_docs_gate(root)

    except SystemExit:
        # Docs gate or surface rendering failed — remove lock before exiting
        upgrade_lib.remove_upgrade_lock(root)
        raise

    _log(
        "\n✓ Phases 0–3 complete. Proceed with agent editing pass, then run:\n"
        "    upgrade-wavefoundry --rebuild-index\n"
        "    upgrade-wavefoundry --cleanup\n"
        "\nOr to rebuild and clean in one step:\n"
        "    upgrade-wavefoundry --rebuild-index && upgrade-wavefoundry --cleanup"
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
