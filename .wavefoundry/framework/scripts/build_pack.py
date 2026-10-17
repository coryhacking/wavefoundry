#!/usr/bin/env python3
"""Build a semver distribution zip of Wavefoundry's canonical framework tree.

Produces wavefoundry-MAJOR.MINOR.PATCH.<build>.zip in ~/.wavefoundry/dist/
(or a specified output directory), where <build> is a standalone 4-character
base36 pure-time index (5-minute buckets on a pinned build epoch) so packs stay
temporally lex-sortable — see ``compute_build_suffix``.

Before building the archive, writes ``framework/VERSION`` to
``MAJOR.MINOR.PATCH+<build>`` and stamps ``framework_revision`` in
prompt-surface-manifest.json to the same value.

Usage:
    python3 build_pack.py --version MAJOR.MINOR.PATCH [--output <dir>]
"""

import argparse
import datetime
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping, Optional


# Patterns excluded from the zip.
EXCLUDED_NAMES = {".DS_Store"}
EXCLUDED_DIRS = {"__pycache__", ".pytest_cache", ".wavefoundry"}
# Excluded path suffix relative to the framework root (forward-slash separated).
# Tests and the test runner are development-only artifacts; downstream repos that
# vendor the pack have no use for them and seeds must not instruct them to run tests.
EXCLUDED_REL_PATHS = {
    "scripts/tests/tmp",
    "scripts/tests",
    "scripts/run_tests.py",
    "scripts/test_worker_bootstrap",  # source-host test startup only; the guard library ships
    "scripts/build_pack.py",
    "scripts/repair_ppol_memory_staging.py",  # one-off local repair; not a normal upgrade tool
    "scripts/build_scan_allowlist.py",  # source-host-only; top-imports build_pack (excluded) — don't ship
    "scripts/verify_vendored_scripts.py",  # development-only; uses the network (wave 1zls7, 1zltw)
    "scripts/benchmarks",
    "test-cache.json",
}
# Transient/runtime artifact extensions that must never ship in the pack.
# .lock and .log are emitted at runtime by the test runner and the indexer; the
# remaining suffixes are editor/merge-conflict artifacts that should never ship
# even if someone accidentally leaves one behind in the source tree.
TRANSIENT_ARTIFACT_EXTENSIONS = (".lock", ".log", ".bak", ".swp", ".tmp", ".orig", ".rej")

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

# Change 1zyv1: bytecode goes only to the project cache (``bytecode_cache``),
# never beside the sources; writes stay off until configure() enables the cache.
if __name__ == "__main__" or sys.pycache_prefix is None:
    sys.dont_write_bytecode = True
import bytecode_cache  # noqa: E402

if __name__ == "__main__":
    bytecode_cache.configure()

import venv_bootstrap  # the single venv resolver (wave 1p7pl)
from upgrade_protocol import (
    PROTOCOL_METADATA_FILENAME,
    build_protocol_metadata,
)

FRAMEWORK_REL = ".wavefoundry/framework"
ZIP_PREFIX = "wavefoundry-"
# wavefoundry-MAJOR.MINOR.PATCH.<build>.zip
_ZIP_NAME_RE = re.compile(r"^wavefoundry-(\d+\.\d+\.\d+)\.([A-Za-z0-9]+)\.zip$")
_DEFAULT_DIST_DIR = Path("~/.wavefoundry/dist")


def find_repo_root(start: Path) -> Path:
    """Walk up from start until we find the repo root (contains AGENTS.md)."""
    current = start.resolve()
    while current != current.parent:
        if (current / "AGENTS.md").exists():
            return current
        current = current.parent
    raise RuntimeError(f"Could not locate repository root from {start}")


def _get_build_prefix() -> str:
    """Return the current base36 lifecycle prefix from lifecycle_id.py --prefix-only.

    Retained for callers that need the full 5-character lifecycle prefix (waves,
    changes, plans). The build pack itself uses ``compute_build_suffix`` directly
    so the suffix is temporally lex-sortable; the lifecycle prefix's tail char
    (minute mod 36) is not.
    """
    script_dir = Path(__file__).resolve().parent
    result = subprocess.run(
        [sys.executable, str(script_dir / "lifecycle_id.py"), "--prefix-only"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    return result.stdout.strip()


def _build_suffix(prefix: str) -> str:
    """Legacy: return the rightmost 4 characters of a lifecycle prefix.

    Kept for the test surface and any out-of-tree caller. The packaged build
    suffix now goes through ``compute_build_suffix`` directly so two consecutive
    builds always lex-sort in temporal order.
    """
    return prefix[-4:] if len(prefix) > 4 else prefix


# Build suffix — standalone pure-time index, fully decoupled from the
# lifecycle-ID mint (which under scheme v2 carries a provisioning offset and
# per-mint hash entropy that a build number must not inherit).
#
# Encoding: ``base36((days_since_build_epoch * 288 + bucket_5min) mod 36^4)``,
# min-width 4 — 5-minute resolution so consecutive same-day builds still
# differ, ~15.97 years (5,832 days) of lex-sortable runway per ``mod 36^4``
# lap. The build epoch is a pinned constant, NOT the per-repo lifecycle policy
# epoch: builds happen only in the framework repo, and pinning the epoch this
# repo's policy already used keeps new suffixes value-identical with every
# shipped pack (…1.10.0.p9cr.zip etc.). The inherited lap boundary (~2031-04
# from this epoch) is the status quo; cross-version ordering rides semver and
# same-semver repackages ride the upgrade-selector mtime tie-break (131ht), so
# the lap boundary is cosmetic. Builds within the same 5-minute bucket produce
# identical suffixes — covered by the same-semver-collision warning below.
BUILD_EPOCH_UTC = datetime(1999, 5, 1, tzinfo=timezone.utc)
_SUFFIX_BUCKETS_PER_DAY = 288
_SUFFIX_BUCKET_WIDTH_MIN = 5
_SUFFIX_MOD = 36 ** 4  # 1,679,616


def compute_build_suffix(now_utc: datetime, epoch_utc: datetime | None = None) -> str:
    """Return the 4-character build suffix for ``now_utc``.

    Pure time — no lifecycle policy read, no offset, no entropy: changing the
    repo's lifecycle scheme/epoch/offset never moves the build suffix.
    ``rjust(4)`` keeps the width stable when a post-lap value dips below 36^3.
    """
    from lifecycle_id import encode_base36
    epoch = epoch_utc if epoch_utc is not None else BUILD_EPOCH_UTC
    now = now_utc.astimezone(timezone.utc)
    days = (now.date() - epoch.astimezone(timezone.utc).date()).days
    if days < 0:
        raise ValueError(
            f"build timestamp must not be earlier than the build epoch "
            f"({epoch.isoformat()}); got {now.isoformat()}"
        )
    bucket = (now.hour * 60 + now.minute) // _SUFFIX_BUCKET_WIDTH_MIN
    packed = (days * _SUFFIX_BUCKETS_PER_DAY + bucket) % _SUFFIX_MOD
    return encode_base36(packed).rjust(4, "0")


def _current_build_suffix() -> str:
    """Return the build suffix for the current wall-clock time on the pinned build epoch."""
    return compute_build_suffix(datetime.now(timezone.utc))


def _warn_on_same_semver_collision(output_dir: Path, version: str) -> None:
    """Emit a warning when ``version`` already has pack(s) in ``output_dir``.

    Non-blocking. Operators have legitimate reasons to repackage at the same
    semver (e.g., reproducing a bad build, content-only fix). The warning
    surfaces the existing pack filenames so the operator can choose to bump
    semver instead — bumping makes the upgrade selector path unambiguous
    independent of mtime tie-break behavior.
    """
    if not output_dir.is_dir():
        return
    # Width-tolerant on the suffix segment: a `{4}` pin here would go silently
    # vacuous (warning never fires) if the suffix width ever changed.
    pattern = re.compile(
        rf"^{re.escape(ZIP_PREFIX)}{re.escape(version)}\.[A-Za-z0-9]+\.zip$"
    )
    existing = sorted(p.name for p in output_dir.iterdir() if pattern.match(p.name))
    if not existing:
        return
    print(
        f"build_pack: WARNING: {len(existing)} existing pack(s) at version "
        f"{version} found in {output_dir}:",
        file=sys.stderr,
    )
    for name in existing:
        print(f"  - {name}", file=sys.stderr)
    print(
        "  Consider bumping semver (MAJOR.MINOR.PATCH) — same-version repackages "
        "rely on the upgrade selector's mtime tie-break to surface the newest. "
        "Bumping semver makes the selection unambiguous.",
        file=sys.stderr,
    )


def should_exclude(rel_path: str, name: str) -> bool:
    """Return True if this file or directory should be excluded from the zip."""
    if name in EXCLUDED_NAMES:
        return True
    # rel_path uses forward slashes relative to the framework root.
    for excl in EXCLUDED_DIRS:
        parts = rel_path.split("/")
        if excl in parts:
            return True
    for excl_rel in EXCLUDED_REL_PATHS:
        if rel_path == excl_rel or rel_path.startswith(excl_rel + "/"):
            return True
    if name.endswith(".pyc"):
        return True
    if name.endswith(TRANSIENT_ARTIFACT_EXTENSIONS):
        return True
    return False


def collect_files(framework_dir: Path) -> list[tuple[Path, str]]:
    """Return [(abs_path, zip_arcname)] for every file under framework_dir."""
    entries: list[tuple[Path, str]] = []
    for dirpath, dirnames, filenames in os.walk(framework_dir):
        dirpath = Path(dirpath)
        # Compute path relative to framework_dir using forward slashes.
        rel_dir = dirpath.relative_to(framework_dir).as_posix()
        rel_dir = "" if rel_dir == "." else rel_dir

        # Filter out excluded dirs in-place so os.walk skips them.
        dirnames[:] = [
            d for d in dirnames
            if not should_exclude(
                (rel_dir + "/" + d).lstrip("/"), d
            )
        ]

        for filename in filenames:
            rel_file = (rel_dir + "/" + filename).lstrip("/")
            if should_exclude(rel_file, filename):
                continue
            abs_path = dirpath / filename
            # arcname preserves the full path from repo root so that
            # `unzip -o zip -d <repo-root>` restores the correct layout.
            arcname = FRAMEWORK_REL + ("/" + rel_file if rel_file else "")
            entries.append((abs_path, arcname))
    return entries


def write_manifest(framework_dir: Path, entries: list[tuple[Path, str]]) -> Path:
    """Write MANIFEST listing all packed paths (relative to framework root).

    The manifest is written to disk so it can be saved before the next upgrade
    and used to prune files that were pack-delivered in the old version but
    absent from the new one.  MANIFEST always lists itself.
    """
    prefix = FRAMEWORK_REL + "/"
    rel_paths = sorted({
        *(arcname[len(prefix):] for _, arcname in entries if arcname.startswith(prefix)),
        "MANIFEST",
    })
    manifest_path = framework_dir / "MANIFEST"
    manifest_path.write_text("\n".join(rel_paths) + "\n", encoding="utf-8")
    return manifest_path


def write_pack_version(framework_dir: Path, version: str, build_prefix: str) -> None:
    """Stamp VERSION with MAJOR.MINOR.PATCH+<build_prefix> so the archive is traceable."""
    version_path = framework_dir / "VERSION"
    version_path.write_text(f"{version}+{build_prefix}\n", encoding="utf-8")


def update_manifest_revision(repo_root: Path, full_version: str) -> None:
    """Write full_version into framework_revision in prompt-surface-manifest.json.

    The build number is set by the packager, so the manifest is updated as a
    post-build step rather than checked as a pre-flight.  Missing or unparseable
    manifest emits a warning but does not fail the build.
    """
    import json

    manifest_path = repo_root / "docs" / "prompts" / "prompt-surface-manifest.json"
    if not manifest_path.exists():
        print(f"warning: manifest not found at {manifest_path}; skipping update.", file=sys.stderr)
        return
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        print(f"warning: could not parse manifest: {exc}; skipping update.", file=sys.stderr)
        return
    data["framework_revision"] = full_version
    manifest_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def check_docs_gate(repo_root: Path) -> None:
    """Run docs-gardener and docs-lint as a pre-packaging gate.

    Invokes the scripts directly under the current (venv) interpreter — the
    ``bin/*`` wrappers were consolidated into ``wf`` in 1p7tz. Exits 1 if a
    script is missing or returns a non-zero exit code.
    """
    import subprocess

    scripts_dir = repo_root / ".wavefoundry" / "framework" / "scripts"
    for cmd_name, module in (("docs-gardener", "docs_gardener.py"), ("docs-lint", "docs_lint.py")):
        script = scripts_dir / module
        if not script.exists():
            print(
                f"error: {module} not found at {script}",
                file=sys.stderr,
            )
            sys.exit(1)
        result = subprocess.run([sys.executable, str(script)], cwd=str(repo_root))
        if result.returncode != 0:
            print(
                f"error: {cmd_name} failed — fix docs issues before packaging.",
                file=sys.stderr,
            )
            sys.exit(1)


# ---------------------------------------------------------------------------
# Release-orchestration helpers (wave 1p347)
# ---------------------------------------------------------------------------
#
# These helpers support the `--release` flag, which extends `build_pack.py`
# from a local-build CLI into the official release CLI: after a successful
# local build, `--release` tags the commit, pushes the tag to origin, and
# uploads the zip as a GitHub Release asset via `gh release create`.
#
# Pre-flight checks run BEFORE the build so failures (dirty tree, wrong
# branch, missing CHANGELOG section, gh not auth'd) abort cheaply. Wave 1p4ww
# removed the shipped framework index, so there is no post-build index
# assertion. The full --release order (matches _run_release_orchestration and
# the ordering test): (1) preflight checks, (2) LOCAL build (archive written,
# VERSION/manifest/README-badge stamped), (3) commit the stamps, (4) tag the
# stamp commit locally, (5) push HEAD to origin/main, (6) push the tag,
# (7) publish the GitHub release with the zip attached.
# `--release-dry-run` runs (1)-(2) for real and only PRINTS (3)-(7) — no
# commit, tag, push, or upload — so the archive and stamps remain and the
# tree is left dirty; the orchestration logic can be smoke-tested before a
# real release.


RELEASE_NOTES_INSTALL_BLOCK_REL = Path(".wavefoundry/framework/install/install-block.md")


def _read_release_install_block(repo_root: Path) -> str:
    """Read the install block that gets prepended to every release's notes.

    Returns the block content (no trailing newline normalization beyond what
    the file itself carries) or empty string if the file is missing. Missing
    file is recoverable — callers fall through to CHANGELOG-only notes.
    """
    path = repo_root / RELEASE_NOTES_INSTALL_BLOCK_REL
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8")


def _assemble_release_notes(repo_root: Path, changelog_body: str) -> str:
    """Prepend the install block to the CHANGELOG-extracted notes.

    Wave 1p35d (1p35p): every published release carries an `## Install` block
    at the top of its notes so an agent or operator landing on the Releases
    page sees the zip-at-root → shortcut-phrase flow alongside the download
    link. Source of truth is `.wavefoundry/framework/install/install-block.md`.
    """
    block = _read_release_install_block(repo_root)
    if not block.strip():
        return changelog_body
    # Single blank line between block and changelog body. The block itself
    # ends with `---\n\n` so the join produces clean visual separation.
    joined = block.rstrip() + "\n\n" + changelog_body.lstrip()
    return joined


def _extract_changelog_section(changelog_path: Path, version: str) -> str:
    """Extract the body of the ``## [<version>]`` section from CHANGELOG.md.

    Returns the section body (excluding the heading) as a string. Empty
    string if the section is missing. The section ends at the next ``## [``
    heading or end of file.
    """
    if not changelog_path.exists():
        return ""
    text = changelog_path.read_text(encoding="utf-8")
    section_pat = re.compile(rf"^## \[{re.escape(version)}\](?:\s|$)")
    next_pat = re.compile(r"^## \[")
    out: list[str] = []
    in_section = False
    for line in text.splitlines():
        if not in_section:
            if section_pat.match(line):
                in_section = True
            continue
        if next_pat.match(line):
            break
        out.append(line)
    # Trim leading and trailing blank lines.
    while out and not out[0].strip():
        out.pop(0)
    while out and not out[-1].strip():
        out.pop()
    return "\n".join(out)


def _check_changelog_claims(section_body: str, version: str) -> list[str]:
    """Wave 1wip2 (1wgwn): run the shared docs-constants claims engine over
    the changelog section being packed. One engine, two homes — the docs gate
    checks the [Unreleased] top section; this gate checks the packed section,
    version-explicitly, so a stale constant can never ship inside a pack."""
    from wave_lint_lib.docs_constants_validators import (
        check_changelog_section_constants,
    )
    return check_changelog_section_constants(
        section_body, f"CHANGELOG.md [{version}]"
    )


def _check_git_working_tree_clean(repo_root: Path) -> None:
    """Refuse if any tracked file is modified or any untracked-non-ignored file exists."""
    import subprocess

    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=str(repo_root),
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if result.returncode != 0:
        raise RuntimeError(f"git status failed: {result.stderr.strip()}")
    if result.stdout.strip():
        raise RuntimeError(
            "working tree is not clean — commit or stash changes before --release. "
            "Uncommitted work is a signal the release isn't ready.\n"
            f"  git status --porcelain output:\n{result.stdout}"
        )


def _check_on_main_branch(repo_root: Path) -> None:
    """Refuse on any branch other than `main`."""
    import subprocess

    result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=str(repo_root),
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if result.returncode != 0:
        raise RuntimeError(f"git rev-parse failed: {result.stderr.strip()}")
    branch = result.stdout.strip()
    if branch != "main":
        raise RuntimeError(
            f"current branch is `{branch}` — releases must be cut from `main`."
        )


def _check_tag_does_not_exist(repo_root: Path, tag: str) -> None:
    """Refuse if the target tag exists locally or on the `origin` remote."""
    import subprocess

    local = subprocess.run(
        ["git", "rev-parse", "--verify", f"refs/tags/{tag}"],
        cwd=str(repo_root),
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if local.returncode == 0:
        raise RuntimeError(
            f"local tag `{tag}` already exists. Delete it explicitly "
            f"(`git tag -d {tag}`) before re-running --release for the same version."
        )

    remote = subprocess.run(
        ["git", "ls-remote", "--tags", "origin", f"refs/tags/{tag}"],
        cwd=str(repo_root),
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if remote.returncode != 0:
        # Network failure or no remote configured — surface but don't fail
        # the check on inability to verify. Reuse subprocess.CalledProcessError
        # semantics: empty stdout means no matching ref.
        raise RuntimeError(
            f"git ls-remote failed: {remote.stderr.strip() or 'unknown error'}"
        )
    if remote.stdout.strip():
        raise RuntimeError(
            f"remote tag `{tag}` already exists on `origin`. Delete it explicitly "
            f"(`git push origin :refs/tags/{tag}`) before re-running --release."
        )


BUILD_PROVENANCE_FILENAME = "BUILD-PROVENANCE.json"
_QUALIFICATION_DIR_REL = ".wavefoundry/cache/qualification"
_QUALIFICATION_COMMANDS = {
    "default": "python3 -B .wavefoundry/framework/scripts/run_tests.py --no-cache --qualification-report "
               ".wavefoundry/cache/qualification/default.json",
    "second": "python3 -B .wavefoundry/framework/scripts/run_tests.py --qualify-profile second "
              "--qualification-report .wavefoundry/cache/qualification/second.json",
    "declared": "python3 -B .wavefoundry/framework/scripts/run_tests.py --qualify-profile declared "
                "--qualification-report .wavefoundry/cache/qualification/declared.json",
}
# Comparator refusals an operator exception may admit once the report's
# return codes are set aside: a skip difference on an otherwise valid report.
_EXCEPTABLE_SKIP_REFUSALS = (
    "missing skip or changed reason",
    "declared profile has unexpected skips",
    "unexpected second-profile skip",
)
_HEX64_RE = re.compile(r"[0-9a-f]{64}")


def _read_source_provenance(repo_root: Path) -> tuple[Optional[str], Optional[bool]]:
    """Return ``(HEAD, tree_clean)`` for the checkout the pack is built from.

    Both are ``None`` unless Git runs and this folder is the top of its own
    checkout: inherited ``GIT_*`` variables are dropped and the reported top
    level must be ``repo_root``, so a parent repository or a foreign
    ``GIT_DIR`` never supplies the commit.  Output other than 40 lowercase
    hex characters (for example a SHA-256 repository) also gives ``None``.
    Git's stderr is never recorded.
    """
    env = {key: value for key, value in os.environ.items() if not key.upper().startswith("GIT_")}

    def git(*args: str) -> "subprocess.CompletedProcess[str]":
        return subprocess.run(["git", *args], cwd=str(repo_root), check=False, capture_output=True,
                              text=True, encoding="utf-8", errors="replace", env=env)

    try:
        top = git("rev-parse", "--show-toplevel")
        if top.returncode != 0 or not top.stdout.strip():
            return None, None
        if Path(top.stdout.strip()).resolve() != Path(repo_root).resolve():
            return None, None
        head = git("rev-parse", "HEAD")
        commit = head.stdout.strip()
        if head.returncode != 0 or not re.fullmatch(r"[0-9a-f]{40}", commit):
            return None, None
        status = git("--no-optional-locks", "status", "--porcelain")
        if status.returncode != 0:
            return None, None
        return commit, status.stdout.strip() == ""
    except (OSError, subprocess.SubprocessError, ValueError):
        return None, None


def build_provenance(*, release_version: str, build_id: str, source_commit: Optional[str],
                     source_tree_clean: Optional[bool], release_tag: Optional[str]) -> dict:
    """The exact six-field ``BUILD-PROVENANCE.json`` record."""
    return {
        "schema_version": 1,
        "release_version": release_version,
        "build_id": build_id,
        "source_commit": source_commit,
        "source_tree_clean": source_tree_clean,
        "release_tag": release_tag,
    }


def _parse_qualification_exceptions(values: Optional[list]) -> dict[str, str]:
    """Parse repeated ``PROFILE=REASON`` values into ``{profile: reason}``."""
    import unicodedata

    parsed: dict[str, str] = {}
    for raw in values or []:
        profile, sep, reason = str(raw).partition("=")
        profile = profile.strip()
        if not sep:
            raise RuntimeError("--accept-qualification-exception takes PROFILE=REASON")
        if profile not in ("second", "declared"):
            raise RuntimeError(
                f"--accept-qualification-exception profile must be second or declared, got {profile!r}; "
                "the default profile never takes an exception"
            )
        if profile in parsed:
            raise RuntimeError(f"--accept-qualification-exception names {profile} more than once")
        if (not 1 <= len(reason) <= 500 or not reason.strip()
                or reason.splitlines() != [reason]
                or any(unicodedata.category(ch) in ("Cc", "Cf") for ch in reason)):
            raise RuntimeError(
                f"--accept-qualification-exception reason for {profile} must be one line of 1 to 500 "
                "characters with no control or format characters"
            )
        parsed[profile] = reason
    return parsed


def _current_framework_inputs_hash(repo_root: Path) -> str:
    """The framework inputs hash the test runner writes into every report.

    Borrowed from this checkout's own ``run_tests.py`` through the close
    gate's loader, which undoes the runner's import-time side effects.  Unlike
    the close gate, an absent or unloadable runner refuses: a release must be
    qualified from the source host.
    """
    import lifecycle_gate_support

    runner = Path(repo_root) / lifecycle_gate_support._FRAMEWORK_TEST_RUNNER_REL
    if not runner.is_file():
        raise RuntimeError(f"`{lifecycle_gate_support._FRAMEWORK_TEST_RUNNER_REL}` is absent, so release "
                           "qualification cannot be proven")
    try:
        contained = runner.resolve().is_relative_to(Path(repo_root).resolve())
    except OSError as exc:
        raise RuntimeError(f"the test runner could not be resolved: {exc}") from None
    if not contained:
        raise RuntimeError("the test runner resolves outside this repository; qualification not proven")
    module = lifecycle_gate_support._load_framework_test_runner(runner)
    if module is None or not hasattr(module, "_hash_inputs"):
        raise RuntimeError("the test runner could not be loaded, so release qualification cannot be proven")
    try:
        value = module._hash_inputs()
    except (Exception, SystemExit) as exc:  # noqa: BLE001 - any failure is "not proven"
        raise RuntimeError(f"the framework inputs hash could not be computed ({type(exc).__name__})") from None
    if not isinstance(value, str) or not _HEX64_RE.fullmatch(value):
        raise RuntimeError("the framework inputs hash is malformed; qualification not proven")
    return value


def _report_counts(report: dict) -> tuple[int, int, int]:
    workers = report.get("workers") or []
    return (sum(int(w.get("tests", 0)) for w in workers), len(workers),
            sum(int(w.get("skipped", 0)) for w in workers))


def _check_release_qualification(repo_root: Path, exceptions: Mapping[str, str],
                                 *, inputs_hash: Optional[str] = None) -> str:
    """Refuse a release whose default, second and declared reports do not qualify this tree.

    Returns the ``### Qualification`` release-notes section.  Reports are read
    only through ``qualification_report.read_report``.  A ``second`` or
    ``declared`` report under an operator exception is admitted only when it
    is present, owned, names its profile, carries the current source hash and
    would pass ``compare`` (or differ only in skips) once its return codes are
    set aside; anything else refuses, exception or not.  The gate prevents
    accidents; it is not an attestation, since any process running as the
    maintainer can write these reports.
    """
    import copy

    import qualification_report

    current = inputs_hash if inputs_hash is not None else _current_framework_inputs_hash(repo_root)

    def regen(profile: str) -> str:
        return f"regenerate with: {_QUALIFICATION_COMMANDS[profile]}"

    def load(profile: str) -> dict:
        rel = f"{_QUALIFICATION_DIR_REL}/{profile}.json"
        try:
            report = qualification_report.read_report(repo_root, rel)
        except FileNotFoundError:
            raise RuntimeError(f"qualification report for {profile} is missing ({rel}); {regen(profile)}") from None
        except (OSError, ValueError, TypeError) as exc:
            raise RuntimeError(f"qualification report for {profile} is unreadable or refused "
                               f"({type(exc).__name__}: {str(exc)[:200]}); {regen(profile)}") from None
        identity = report.get("identity")
        if not isinstance(identity, dict) or identity.get("profile") != profile:
            raise RuntimeError(f"qualification report {rel} does not name profile {profile}; {regen(profile)}")
        if identity.get("source_hash") != current:
            raise RuntimeError(f"qualification report for {profile} is stale: it was written for a different "
                               f"framework tree; {regen(profile)}")
        return report

    default = load("default")
    try:
        qualification_report.validate(default)
    except (ValueError, KeyError, TypeError) as exc:
        raise RuntimeError(f"default qualification does not pass ({str(exc)[:200]}); {regen('default')}") from None
    scope = default.get("scope")
    if (not isinstance(scope, dict) or scope.get("kind") != "full"
            or scope.get("discovered_workers") != default.get("expected_workers")):
        raise RuntimeError(f"default qualification report is not a full run; {regen('default')}")
    tests, files, skips = _report_counts(default)
    lines = ["### Qualification", "",
             f"- default: passed, {tests} tests in {files} worker files, {skips} skips "
             f"(source {current[:12]})"]
    for profile in ("second", "declared"):
        candidate = load(profile)
        try:
            qualification_report.compare(default, candidate, profile, root=repo_root)
        except ValueError as exc:
            refusal = str(exc)[:256]
            if profile not in exceptions:
                raise RuntimeError(
                    f"{profile} qualification refused: {refusal}; {regen(profile)}, or record a named "
                    f"exception with --accept-qualification-exception {profile}=REASON"
                ) from None
            projection = copy.deepcopy(candidate)
            projection["returncode"] = 0
            for row in projection.get("workers") or []:
                if isinstance(row, dict):
                    row["returncode"] = 0
            skip_difference = None
            try:
                qualification_report.compare(default, projection, profile, root=repo_root)
            except ValueError as structural:
                if str(structural) not in _EXCEPTABLE_SKIP_REFUSALS:
                    raise RuntimeError(
                        f"{profile} qualification cannot take an exception: {str(structural)[:256]}; "
                        f"{regen(profile)}"
                    ) from None
                skip_difference = str(structural)
            except Exception as structural:  # noqa: BLE001 - never embedded, never excused
                raise RuntimeError(f"{profile} qualification could not be compared "
                                   f"({type(structural).__name__}); {regen(profile)}") from None
            failing = sorted(str(row.get("name")) for row in candidate.get("workers") or []
                             if isinstance(row, dict) and row.get("returncode") != 0)
            if not failing and (skip_difference is None or candidate.get("returncode") != 0):
                # A nonzero run with every worker green is a runner or repository
                # guard failure, never a failing test, and a skip difference cannot
                # explain it: not excusable.
                raise RuntimeError(
                    f"{profile} qualification cannot take an exception: the run failed with no failing "
                    f"worker (a runner or repository guard failure); {regen(profile)}"
                )
            tests, files, skips = _report_counts(candidate)
            excused = f"; skip difference: {skip_difference}" if skip_difference and skip_difference != refusal else ""
            lines.append(
                f"- {profile}: accepted exception: {exceptions[profile]} (refusal: {refusal}{excused}; "
                f"failing workers: {', '.join(failing) or 'none'}; {tests} tests in {files} worker files, "
                f"{skips} skips, source {current[:12]})"
            )
            continue
        except Exception as exc:  # noqa: BLE001 - never embedded, never excused
            raise RuntimeError(f"{profile} qualification could not be compared ({type(exc).__name__}); "
                               f"{regen(profile)}") from None
        if profile in exceptions:
            raise RuntimeError(f"qualification exception for {profile} is stale: its report passes; "
                               "drop --accept-qualification-exception for it")
        tests, files, skips = _report_counts(candidate)
        lines.append(f"- {profile}: passed, {tests} tests in {files} worker files, {skips} skips "
                     f"(source {current[:12]})")
    return "\n".join(lines) + "\n"


def _check_gh_authenticated() -> None:
    """Refuse if `gh auth status` fails — the upload would fail anyway."""
    import subprocess

    result = subprocess.run(
        ["gh", "auth", "status"],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if result.returncode != 0:
        raise RuntimeError(
            "`gh auth status` failed — sign in with `gh auth login` (or `gh auth switch` "
            "to select the account that owns the release repo) before --release."
        )


def _derive_tag_message(repo_root: Path, version: str) -> str:
    """Derive an annotated-tag message from the most recent wave-close commit subject.

    Looks for commit subjects matching `Close wave <id> and ship <prev> -> <new>`
    (with either unicode `→` or ASCII `->`). On match, returns the close-wave subject
    verbatim. Falls back to a generic `Release v<version>` if no match.
    """
    import subprocess

    result = subprocess.run(
        ["git", "log", "-1", "--format=%s"],
        cwd=str(repo_root),
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if result.returncode != 0:
        return f"Release v{version}"
    subject = result.stdout.strip()
    close_pat = re.compile(r"^Close wave \S+ and ship .+\s*(?:→|->)\s*.+$")
    if close_pat.match(subject):
        return subject
    return f"Release v{version}"


# Wave 1p5s1: the README version badge is a STATIC shields badge stamped at
# release (no dynamic GitHub-API dependency). This rewrites its version to the
# release version, alongside the VERSION/manifest stamp.
_README_VERSION_BADGE_RE = re.compile(r"(img\.shields\.io/badge/version-)[0-9][^-)\s]*(-purple)")


def _stamp_readme_version_badge(repo_root: Path, version: str) -> bool:
    """Rewrite the static README version badge to ``version``. Returns True if changed.

    Idempotent; no-ops (returns False) when README.md is absent or has no matching badge.
    Never raises.
    """
    readme = repo_root / "README.md"
    try:
        text = readme.read_text(encoding="utf-8")
    except OSError:
        return False
    new = _README_VERSION_BADGE_RE.sub(rf"\g<1>{version}\g<2>", text)
    if new == text:
        return False
    try:
        readme.write_text(new, encoding="utf-8")
    except OSError:
        return False
    return True


_RELEASE_ASSET_NAME_RE = re.compile(r"[A-Za-z0-9._+-]+")


def _release_checksum_lines(assets: list) -> list[str]:
    """``<sha256>  <basename>`` lines for every release asset, sorted by name.

    GitHub names an uploaded asset after its file, so each basename must be
    unique and plain; anything else refuses before any release step runs.
    """
    names: dict[str, Path] = {}
    for asset in assets:
        path = Path(asset)
        name = path.name
        if not _RELEASE_ASSET_NAME_RE.fullmatch(name) or name == "SHA256SUMS":
            raise RuntimeError(f"release asset name {name!r} is not a plain file name")
        if name in names:
            raise RuntimeError(f"two release assets share the name {name!r}")
        names[name] = path
    try:
        return [f"{_file_sha256(names[name])}  {name}" for name in sorted(names)]
    except OSError as exc:
        raise RuntimeError(f"a release asset could not be read for SHA256SUMS: {exc}") from None


def _run_release_orchestration(
    repo_root: Path,
    version: str,
    zip_path: Path,
    release_notes_body: str,
    *,
    dry_run: bool,
    extra_assets: list[Path] | None = None,
) -> None:
    """Commit the build stamp, tag, push main + tag, and upload via `gh release create`.

    Ordering (wave 1p5l4 fix): ``build_zip`` stamps ``VERSION`` +
    ``prompt-surface-manifest.json`` AFTER the clean-tree preflight, so those
    edits are uncommitted when this runs. We commit them FIRST, so the
    annotated tag lands on the stamp commit — matching the v1.4/v1.5 release
    convention where ``vX`` points at the "Bump VERSION to X" commit, not the
    pre-stamp commit. Then push ``main`` (so origin reflects the tagged commit)
    and the tag, then create the Release.

    On any step failure, raises RuntimeError with an actionable recovery hint
    that names the exact command to re-run the failed step manually. Partial
    state (e.g., tag pushed but `gh release create` failed) is documented
    inline in the error message.
    """
    import subprocess
    import tempfile

    tag = f"v{version}"
    tag_message = _derive_tag_message(repo_root, version)
    stamp = (repo_root / FRAMEWORK_REL / "VERSION").read_text(encoding="utf-8").strip()
    stamp_message = f"Bump VERSION to {stamp} after release"
    assets = [zip_path, *(extra_assets or [])]
    # Wave 20wq7: digests first, so an unreadable asset leaves the tree untouched.
    checksum_lines = _release_checksum_lines(assets)

    if dry_run:
        print("[--release-dry-run] would upload SHA256SUMS:", file=sys.stderr)
        for line in checksum_lines:
            print(f"  {line}", file=sys.stderr)
        print(f"[--release-dry-run] would run: stamp README version badge -> {version}", file=sys.stderr)
        print(f"[--release-dry-run] would run: git add -A && git commit -m {stamp_message!r}", file=sys.stderr)
        print(f"[--release-dry-run] would run: git tag -a {tag} -m {tag_message!r}", file=sys.stderr)
        print(f"[--release-dry-run] would run: git push origin HEAD:main", file=sys.stderr)
        print(f"[--release-dry-run] would run: git push origin {tag}", file=sys.stderr)
        print(
            f"[--release-dry-run] would run: gh release create {tag} "
            f"--title {version!r} --notes-file <tmp> "
            + " ".join(str(asset) for asset in assets) + " <tmp>/SHA256SUMS",
            file=sys.stderr,
        )
        print(
            f"[--release-dry-run] release notes (first 200 chars): {release_notes_body[:200]!r}",
            file=sys.stderr,
        )
        return

    # Wave 1p5s1: stamp the static README version badge to this release, so it's
    # captured in the same stamp commit below (before the tag).
    _stamp_readme_version_badge(repo_root, version)

    # Step 1: commit the build stamp so the tag lands on it (not the pre-stamp
    # commit). Everything dirty here is build output — the preflight guaranteed a
    # clean tree before build_zip ran — so `git add -A` captures exactly the
    # stamp (VERSION + manifest, plus any gardener output from the docs gate).
    add_result = subprocess.run(
        ["git", "add", "-A"],
        cwd=str(repo_root),
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if add_result.returncode != 0:
        raise RuntimeError(
            f"step 1/5 (git add stamp) failed: {add_result.stderr.strip()}\n"
            f"  recovery: investigate the error above; the local repo is untouched."
        )
    # Commit only if the stamp changed something (normally it does).
    staged = subprocess.run(
        ["git", "diff", "--cached", "--quiet"],
        cwd=str(repo_root),
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if staged.returncode != 0:
        commit_result = subprocess.run(
            ["git", "commit", "-m", stamp_message],
            cwd=str(repo_root),
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if commit_result.returncode != 0:
            raise RuntimeError(
                f"step 1/5 (git commit stamp) failed: {commit_result.stderr.strip()}\n"
                f"  recovery: the stamp is staged; commit it manually "
                f"(`git commit -m {stamp_message!r}`) and re-run the remaining steps."
            )

    # Step 2: create the annotated tag locally — now on the stamp commit.
    tag_result = subprocess.run(
        ["git", "tag", "-a", tag, "-m", tag_message],
        cwd=str(repo_root),
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if tag_result.returncode != 0:
        raise RuntimeError(
            f"step 2/5 (git tag) failed: {tag_result.stderr.strip()}\n"
            f"  recovery: the stamp commit is in place; investigate the tag error, "
            f"then re-run the tag + push + release steps manually."
        )

    # Step 3: push main so origin reflects the stamp commit the tag points at.
    push_main = subprocess.run(
        ["git", "push", "origin", "HEAD:main"],
        cwd=str(repo_root),
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if push_main.returncode != 0:
        raise RuntimeError(
            f"step 3/5 (git push main) failed: {push_main.stderr.strip()}\n"
            f"  recovery: the stamp commit and local tag `{tag}` exist but nothing "
            f"was pushed. Fix the push issue, then run `git push origin HEAD:main`, "
            f"`git push origin {tag}`, and the gh release step manually — or delete "
            f"the tag (`git tag -d {tag}`) and re-run --release."
        )

    # Step 4: push the tag to origin.
    push_result = subprocess.run(
        ["git", "push", "origin", tag],
        cwd=str(repo_root),
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if push_result.returncode != 0:
        raise RuntimeError(
            f"step 4/5 (git push tag) failed: {push_result.stderr.strip()}\n"
            f"  recovery: main is pushed and local tag `{tag}` was created. Push it "
            f"manually (`git push origin {tag}`) once the underlying issue is fixed."
        )

    # Step 5: publish the one Wavefoundry package. It is both the normal
    # extractable feature pack and the executable protocol-bridge carrier.
    # The notes and SHA256SUMS live in a fresh folder outside the repository
    # (step 1 ran `git add -A`) and outside the output folder (its public
    # package census); it is kept when the upload fails so recovery can use it.
    staging = Path(tempfile.mkdtemp(prefix="wavefoundry-release-"))
    notes_path = staging / "release-notes.md"
    notes_path.write_bytes(release_notes_body.encode("utf-8"))
    sums_path = staging / "SHA256SUMS"
    sums_path.write_bytes(("\n".join(checksum_lines) + "\n").encode("ascii"))
    upload = [*assets, sums_path]
    release_argv = [
        "gh", "release", "create", tag,
        "--title", version,
        "--notes-file", str(notes_path),
        *[str(asset) for asset in upload],
    ]
    try:
        release_result = subprocess.run(
            release_argv,
            cwd=str(repo_root),
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
    except OSError as exc:
        release_result = subprocess.CompletedProcess(release_argv, 127, "", f"could not run gh: {exc}")
    if release_result.returncode == 0:
        shutil.rmtree(staging, ignore_errors=True)

    if release_result.returncode != 0:
        raise RuntimeError(
            f"step 5/5 (gh release create) failed: {release_result.stderr.strip()}\n"
            f"  recovery: tag `{tag}` is already on origin. The release notes and "
            f"SHA256SUMS are kept in {staging}. Re-run only the release-create step:\n"
            f"    gh release create {tag} --title {version} "
            f"--notes-file {notes_path} "
            + " ".join(str(asset) for asset in upload)
            + "\n"
            f"  Or, if the wrong tag was pushed, delete it "
            f"(`git push origin :refs/tags/{tag}` and `git tag -d {tag}`) "
            f"and re-run --release."
        )

    print(release_result.stdout.strip(), file=sys.stderr)


def _check_vendored_scripts(framework_dir: Path) -> None:
    """Refuse to build when a vendored dashboard script differs from its pinned SHA-256.

    Offline: it hashes the files named in ``dashboard/vendor/README.md`` and makes no network
    request. A framework tree with no vendor folder has nothing to check.
    """
    vendor_dir = framework_dir / "dashboard" / "vendor"
    if not vendor_dir.is_dir():
        return
    # Lazy: only the packaging path needs it. The shipped offline module, not the
    # network verifier that re-exports it (wave 1zyb2, 1zxnt).
    import vendored_integrity

    try:
        problems = vendored_integrity.offline_problems(vendor_dir)
    except vendored_integrity.ReadmeError as exc:
        raise SystemExit(f"error: vendored scripts cannot be checked: {exc}")
    if problems:
        raise SystemExit("error: vendored scripts do not match their pinned hashes:\n  " + "\n  ".join(problems))


def build_zip(
    output_dir: Path,
    version: str,
    build_prefix: str,
    *,
    framework_dir: Optional[Path] = None,
    write_version: bool = True,
    update_manifest: bool = True,
    inject_install_templates: bool = True,
    verbose: bool = False,
    release_tag: Optional[str] = None,
) -> Path:
    # Wave 1p4ww: the framework index is no longer built or shipped — framework
    # seeds/README fold into each project's docs index at setup/upgrade time.
    zip_name = f"{ZIP_PREFIX}{version}.{build_prefix}.zip"
    zip_path = output_dir / zip_name

    script_dir = Path(__file__).resolve().parent
    fw = framework_dir if framework_dir is not None else script_dir.parent
    repo_root = fw.parent.parent if fw.parent.name == ".wavefoundry" else fw.parent

    _check_vendored_scripts(fw)

    # Read before VERSION is stamped, so the clean flag describes the source.
    source_commit, source_tree_clean = _read_source_provenance(repo_root)

    protocol_metadata_path = fw / PROTOCOL_METADATA_FILENAME
    provenance_path = fw / BUILD_PROVENANCE_FILENAME
    try:
        return _build_zip_body(
            fw, repo_root, zip_path, version, build_prefix,
            write_version=write_version, update_manifest=update_manifest,
            inject_install_templates=inject_install_templates,
            protocol_metadata_path=protocol_metadata_path, provenance_path=provenance_path,
            provenance=build_provenance(
                release_version=f"{version}+{build_prefix}", build_id=build_prefix,
                source_commit=source_commit, source_tree_clean=source_tree_clean,
                release_tag=release_tag,
            ),
        )
    finally:
        # Generated packaging files never linger in the source tree, whether the
        # build succeeded or failed: they would change the framework inputs hash.
        for generated in (fw / "MANIFEST", protocol_metadata_path, provenance_path):
            try:
                generated.unlink(missing_ok=True)
            except OSError:
                pass


def _build_zip_body(
    fw: Path,
    repo_root: Path,
    zip_path: Path,
    version: str,
    build_prefix: str,
    *,
    write_version: bool,
    update_manifest: bool,
    inject_install_templates: bool,
    protocol_metadata_path: Path,
    provenance_path: Path,
    provenance: dict,
) -> Path:
    if write_version:
        write_pack_version(fw, version, build_prefix)
    if update_manifest:
        update_manifest_revision(repo_root, f"{version}+{build_prefix}")

    provenance_path.write_bytes((json.dumps(provenance, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    protocol_metadata_path.write_text(
        json.dumps(
            build_protocol_metadata(
                release_version=f"{version}+{build_prefix}",
                build_id=build_prefix,
                artifact_type="feature",
            ),
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    # Remove .DS_Store files from the repo root before collecting files.
    for ds in repo_root.rglob(".DS_Store"):
        try:
            ds.unlink()
        except OSError:
            pass

    entries = collect_files(fw)
    # Write MANIFEST (always lists itself) before zipping so it is included.
    manifest_path = write_manifest(fw, entries)
    manifest_arcname = FRAMEWORK_REL + "/MANIFEST"
    # Always replace any pre-existing MANIFEST entry with the freshly written file.
    entries = [(abs_path, arcname) for abs_path, arcname in entries if arcname != manifest_arcname]
    entries.append((manifest_path, manifest_arcname))

    # Include .wavefoundry/README.md (project-owner orientation doc) if it exists.
    # This file sits outside the framework dir so must be added explicitly.
    wavefoundry_readme = fw.parent / "README.md"
    readme_arcname = ".wavefoundry/README.md"
    if wavefoundry_readme.exists() and not any(a == readme_arcname for _, a in entries):
        entries.append((wavefoundry_readme, readme_arcname))

    # Source CHANGELOG.md from the wavefoundry repo root (the canonical single
    # source of truth) and place it into the pack zip at .wavefoundry/CHANGELOG.md.
    # Consumers receive the file at .wavefoundry/CHANGELOG.md on every upgrade —
    # they read it but never edit it; the wavefoundry repo's root CHANGELOG.md is
    # the only place release history is maintained. The wavefoundry repo itself
    # carries no .wavefoundry/CHANGELOG.md, so there is no duplication in git.
    # Wave 1p3i6 supersedes wave 131at's vendored-canonical design.
    root_changelog = repo_root / "CHANGELOG.md"
    changelog_arcname = ".wavefoundry/CHANGELOG.md"
    if root_changelog.exists() and not any(a == changelog_arcname for _, a in entries):
        entries.append((root_changelog, changelog_arcname))

    # Top-level entry doc sits OUTSIDE .wavefoundry/ so the unzipped folder
    # has a visible file at the root. Without it, macOS Finder shows the
    # extracted folder as empty because the only entry is `.wavefoundry/`
    # (dot-prefixed = hidden by default). The entry doc is reference
    # content — overwritten on every install/upgrade extract.
    #
    # The LIVE install log (.wavefoundry/install-log.md) is intentionally
    # NOT written to the zip. The agent copies the template to that path on
    # first install; on upgrades, the live log is preserved (not in the zip
    # to overwrite). This separates framework artifact (template, overwrites)
    # from operator state (live log, preserved).
    #
    # Wave 1p35d (1p35f): templates source-of-truth lives at
    # .wavefoundry/framework/install/. Filename convention follows the
    # framework's prompt.md pattern: foo.template.md (NOT foo.md.template).
    # Variables {{version}} and {{generated_at}} are replaced at packaging
    # time. Tests using stub framework dirs pass inject_install_templates=False.
    install_wavefoundry_md = None
    if inject_install_templates:
        install_dir = fw / "install"
        install_wavefoundry_template = install_dir / "install-wavefoundry.template.md"
        install_log_template = install_dir / "install-log.template.md"

        if not install_wavefoundry_template.exists():
            raise RuntimeError(
                f"missing template: {install_wavefoundry_template} — expected at "
                "`.wavefoundry/framework/install/install-wavefoundry.template.md`"
            )
        if not install_log_template.exists():
            raise RuntimeError(
                f"missing template: {install_log_template} — expected at "
                "`.wavefoundry/framework/install/install-log.template.md`"
            )

        install_wavefoundry_md = install_wavefoundry_template.read_text(encoding="utf-8")
        install_wavefoundry_md = install_wavefoundry_md.replace("{{version}}", version)

        # NOTE: install-log.template.md ships in the zip via the framework
        # tree scan (it lives under .wavefoundry/framework/install/ which
        # collect_files() includes). No explicit writestr for it here.
        # The template's {{generated_at}} substitution happens when the
        # agent copies it to .wavefoundry/install-log.md, not at packaging.

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for abs_path, arcname in entries:
            zf.write(abs_path, arcname)
        if install_wavefoundry_md is not None:
            zf.writestr("install-wavefoundry.md", install_wavefoundry_md)

    # MANIFEST, the protocol metadata and the build provenance are packaging
    # artifacts; build_zip removes all three from the source tree in its
    # finally, after they have been written into the zip.
    return zip_path


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def build_protocol_bridge_artifacts(
    feature_zip: Path,
    *,
    version: str,
    build_prefix: str,
    bootstrap_source: Path | None = None,
) -> dict[str, Path]:
    """Emit the framework-only bridge, standalone bootstrap, and selection ABI."""

    output_dir = feature_zip.parent
    bridge_build_id = f"bridge-{build_prefix}-p2"
    bridge_zip = output_dir / f"wavefoundry-bridge-{version}.{build_prefix}.zip"
    bootstrap = output_dir / f"wavefoundry-bridge-{version}.{build_prefix}.py"
    selection = output_dir / f"wavefoundry-upgrade-{version}.{build_prefix}.json"
    source = bootstrap_source or (Path(__file__).resolve().parent / "upgrade_bridge_bootstrap.py")
    if not source.is_file():
        raise RuntimeError(f"bridge bootstrap source is missing: {source}")

    protocol_arc = FRAMEWORK_REL + f"/{PROTOCOL_METADATA_FILENAME}"
    version_arc = FRAMEWORK_REL + "/VERSION"
    with zipfile.ZipFile(feature_zip, "r") as incoming, zipfile.ZipFile(
        bridge_zip, "w", compression=zipfile.ZIP_DEFLATED
    ) as outgoing:
        for info in incoming.infolist():
            if not info.filename.startswith(FRAMEWORK_REL + "/"):
                continue
            body = incoming.read(info.filename)
            if info.filename == protocol_arc:
                body = (
                    json.dumps(
                        build_protocol_metadata(
                            release_version=f"{version}+{build_prefix}",
                            build_id=bridge_build_id,
                            artifact_type="bridge",
                        ),
                        indent=2,
                        sort_keys=True,
                    )
                    + "\n"
                ).encode("utf-8")
            elif info.filename == version_arc:
                # The bridge is a protocol carrier, not a product release.
                # The bootstrap restores the installed VERSION bytes before
                # the atomic swap; only the feature archive carries the new
                # product version.
                body = b"protocol-bridge-2\n"
            outgoing.writestr(info, body)

    shutil.copy2(source, bootstrap)
    metadata = {
        "schema_version": 1,
        "bridge_build_id": bridge_build_id,
        "upgrade_protocol_version": 2,
        "minimum_runner_protocol": 2,
        "minimum_source_version": "1.8.0",
        "supported_source_protocol": 1,
        "feature_release_version": version,
        "bridge_archive": bridge_zip.name,
        "bridge_sha256": _file_sha256(bridge_zip),
        "feature_archive": feature_zip.name,
        "feature_sha256": _file_sha256(feature_zip),
    }
    selection.write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return {"bridge": bridge_zip, "bootstrap": bootstrap, "selection": selection}


def build_upgrade_bundle(
    feature_zip: Path,
    bridge_artifacts: dict[str, Path],
    *,
    version: str,
    build_prefix: str,
    bundle_source: Path | None = None,
) -> Path:
    """Add the verified bridge runner to the normal Wavefoundry package.

    The public distribution remains the single ``wavefoundry-*.zip``.  A
    byte-exact copy of its feature-only form is nested as the selected feature
    payload before the executable runner is appended to the outer archive.
    """

    required = {"bridge", "selection"}
    if not required.issubset(bridge_artifacts):
        raise RuntimeError("protocol bridge artifacts are incomplete")
    payload_copy: Path | None = None
    assembled: Path | None = None
    try:
        source = bundle_source or (Path(__file__).resolve().parent / "upgrade_bundle.py")
        bootstrap_source = Path(__file__).resolve().parent / "upgrade_bridge_bootstrap.py"
        subprocess_source = Path(__file__).resolve().parent / "subprocess_util.py"
        if (
            not source.is_file()
            or not bootstrap_source.is_file()
            or not subprocess_source.is_file()
        ):
            raise RuntimeError("upgrade bundle sources are missing")
        selection = json.loads(
            bridge_artifacts["selection"].read_text(encoding="utf-8")
        )
        bridge = bridge_artifacts["bridge"]
        if _file_sha256(bridge) != selection.get("bridge_sha256"):
            raise RuntimeError("bridge artifact no longer matches selection metadata")
        if _file_sha256(feature_zip) != selection.get("feature_sha256"):
            raise RuntimeError("feature artifact no longer matches selection metadata")
        payload_fd, payload_name = tempfile.mkstemp(
            prefix=f".{feature_zip.name}.",
            suffix=".payload",
            dir=feature_zip.parent,
        )
        os.close(payload_fd)
        payload_copy = Path(payload_name)
        bundle_fd, bundle_name = tempfile.mkstemp(
            prefix=f".{feature_zip.name}.",
            suffix=".assembling",
            dir=feature_zip.parent,
        )
        os.close(bundle_fd)
        assembled = Path(bundle_name)
        shutil.copyfile(feature_zip, payload_copy)
        shutil.copyfile(feature_zip, assembled)
        with zipfile.ZipFile(assembled, "a", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.write(source, "__main__.py")
            archive.write(bootstrap_source, "upgrade_bridge_bootstrap.py")
            archive.write(subprocess_source, "subprocess_util.py")
            archive.write(source.parent / "embedded_model_bundle.py", "embedded_model_bundle.py")
            archive.write(
                bridge_artifacts["selection"],
                "payload/" + bridge_artifacts["selection"].name,
            )
            archive.write(bridge, "payload/" + bridge.name)
            archive.write(payload_copy, "payload/" + feature_zip.name)
        if not zipfile.is_zipfile(assembled):
            raise RuntimeError("assembled Wavefoundry package is not a readable zip")
        os.replace(assembled, feature_zip)
        return feature_zip
    finally:
        if payload_copy is not None:
            payload_copy.unlink(missing_ok=True)
        if assembled is not None:
            assembled.unlink(missing_ok=True)
        for artifact in bridge_artifacts.values():
            artifact.unlink(missing_ok=True)


def build_embedded_package(lean: Path, model: Path) -> Path:
    """Append the companion once; preserve the executable and nested lean payload."""
    import embedded_model_bundle as envelope
    import model_bundle
    with zipfile.ZipFile(model) as archive:
        model_bundle.verify_bundle_archive(archive, model_bundle.MODEL_SET_VERSION)
    destination = lean.with_name(lean.stem + ".with-models.zip")
    descriptor = {"schema_version": 1, "model_set_version": model_bundle.MODEL_SET_VERSION,
                  "member": envelope.PREFIX + model_bundle.bundle_name(),
                  "size_bytes": model.stat().st_size, "sha256": _file_sha256(model)}
    if descriptor["size_bytes"] > envelope.MAX_BUNDLE_BYTES:
        raise RuntimeError("model companion exceeds combined-package byte limit")
    fd, name = tempfile.mkstemp(prefix=".combined-", dir=lean.parent)
    os.close(fd)
    staged = Path(name)
    try:
        shutil.copyfile(lean, staged)
        with zipfile.ZipFile(staged, "a") as archive:
            archive.writestr(envelope.DESCRIPTOR, json.dumps(descriptor, sort_keys=True))
            archive.write(model, descriptor["member"], compress_type=zipfile.ZIP_STORED)
            envelope.inspect(archive, model_bundle.MODEL_SET_VERSION)
        os.replace(staged, destination)
        return destination
    finally:
        staged.unlink(missing_ok=True)


def _public_package_snapshot(output_dir: Path) -> dict[Path, tuple[int, str]]:
    """Fingerprint every top-level Wavefoundry-named release artifact."""

    snapshot: dict[Path, tuple[int, str]] = {}
    for path in output_dir.iterdir():
        if (
            not path.is_file()
            or not path.name.startswith(ZIP_PREFIX)
        ):
            continue
        snapshot[path] = (path.stat().st_size, _file_sha256(path))
    return snapshot


def _is_normal_release_zip(path: Path) -> bool:
    return bool(
        re.fullmatch(
            r"wavefoundry-\d+\.\d+\.\d+\.[A-Za-z0-9]+(?:\.with-models)?\.zip",
            path.name,
        )
    )


def _is_model_companion_zip(path: Path) -> bool:
    return bool(
        re.fullmatch(
            r"wavefoundry-models-(?:\d+(?:\.\d+)*|\d+\.\d+\.\d+\.[A-Za-z0-9]+)\.zip",
            path.name,
        )
    )


def _is_allowed_release_asset(path: Path) -> bool:
    return _is_normal_release_zip(path) or _is_model_companion_zip(path)


def _reject_stale_public_build_artifacts(
    before: Mapping[Path, tuple[int, str]],
) -> None:
    stale = sorted(path.name for path in before if not _is_allowed_release_asset(path))
    if stale:
        raise RuntimeError(
            "remove stale public bridge/composition artifact(s) before building: "
            + ", ".join(stale)
        )


def _enforce_single_public_package(
    output_dir: Path,
    expected_package: Path,
    before: Mapping[Path, tuple[int, str]],
    *,
    extra_expected: list[Path] | None = None,
) -> None:
    """Require this invocation to leave exactly its declared release assets.

    Older package files already present in ``output_dir`` are preserved and do
    not count against the current build. Any newly created or modified sibling
    package does: bridge/bootstrap artifacts are internal assembly inputs, not
    a second distributable.
    """

    after = _public_package_snapshot(output_dir)
    expected = {expected_package, *(extra_expected or [])}
    if expected_package not in after or not _is_normal_release_zip(expected_package):
        raise RuntimeError(
            f"release build did not produce the expected feature zip: {expected_package}"
        )
    if any(asset not in after or not (_is_model_companion_zip(asset) or (asset.name == expected_package.stem + ".with-models.zip" and _is_normal_release_zip(asset))) for asset in (extra_expected or [])):
        raise RuntimeError("release build did not produce the expected model companion")
    removed = sorted(path.name for path in before if path not in after)
    changed = {
        path for path, fingerprint in after.items()
        if before.get(path) != fingerprint
    }
    unexpected = sorted(path.name for path in changed if path not in expected)
    if removed or unexpected:
        detail = []
        if unexpected:
            detail.append("unexpected current-build package(s): " + ", ".join(unexpected))
        if removed:
            detail.append("pre-existing package(s) removed: " + ", ".join(removed))
        raise RuntimeError(
            "release build must leave only its declared current-build public Wavefoundry assets; "
            + "; ".join(detail)
        )


def _reexec_with_venv_if_needed() -> None:
    """Activate the wavefoundry venv in-process when numpy is not importable (wave 1p7pl/1p802).

    The index build step loads indexer.py in-process, which requires numpy and
    the pinned SQLite runtime. When build_pack.py is invoked with system Python those imports fail.
    In-process activation (``site.addsitedir`` via the single bootstrap) makes the
    venv packages importable in this process — no re-exec, no child. The numpy
    short-circuit is preserved so an interpreter that already has numpy (e.g. a CI
    env with deps installed) never re-activates. (Name kept for back-compat with
    callers/tests; the behavior is now activate, not re-exec.)
    """
    try:
        import numpy  # noqa: F401
        return
    except ImportError:
        pass
    # Delegate to the single bootstrap (wave 1p7pl/1p802). No-op when the venv is
    # absent or already active.
    venv_bootstrap.activate_tool_venv()


def main():
    _reexec_with_venv_if_needed()
    parser = argparse.ArgumentParser(
        description="Build a semver distribution zip of Wavefoundry's framework tree."
    )
    parser.add_argument(
        "--version",
        metavar="MAJOR.MINOR.PATCH",
        required=True,
        help="Semver base version for this release (e.g. 1.0.0).",
    )
    parser.add_argument(
        "--output",
        metavar="DIR",
        help=(
            "Directory to write the zip into "
            "(default: ~/.wavefoundry/dist/, created if absent)."
        ),
    )
    parser.add_argument(
        "--skip-manifest-update",
        action="store_true",
        help="Skip writing framework_revision to prompt-surface-manifest.json after packaging.",
    )
    parser.add_argument(
        "--skip-docs-gate",
        action="store_true",
        help="Skip the docs-gardener / docs-lint pre-flight gate.",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Print index build progress")
    parser.add_argument(
        "--with-models",
        action="store_true",
        help="Also build the independently versioned offline model-set asset from a warmed local cache.",
    )
    parser.add_argument(
        "--release",
        action="store_true",
        help=(
            "After a successful local build, also tag the commit, push the tag "
            "to origin, and publish a GitHub Release with the local zip attached. "
            "Pre-flight checks refuse on dirty tree, non-main branch, existing "
            "tag, missing CHANGELOG section, or unauthenticated gh."
        ),
    )
    parser.add_argument(
        "--release-dry-run",
        action="store_true",
        help=(
            "Walk the --release pre-flight checks and orchestration without "
            "any REMOTE side effects (no commit, no git tag, no push, no gh "
            "upload) — but the LOCAL build still runs: the archive is built "
            "and VERSION/manifest are stamped, leaving the working tree "
            "dirty (restore with: git restore -- "
            ".wavefoundry/framework/VERSION "
            "docs/prompts/prompt-surface-manifest.json README.md). "
            "Use to smoke-test "
            "the release pipeline before a real --release."
        ),
    )
    parser.add_argument("--with-embedded-models", action="store_true",
                        help="Also build a directly upgradeable ZIP containing the model companion.")
    parser.add_argument(
        "--accept-qualification-exception",
        action="append",
        metavar="PROFILE=REASON",
        default=[],
        help=(
            "Release modes only: publish despite a failing, current second or declared "
            "qualification report, recording REASON (one line, at most 500 characters) in "
            "the release notes. Repeat once per profile. Never applies to default, or to a "
            "missing, stale or malformed report."
        ),
    )
    args = parser.parse_args()
    args.with_models = args.with_models or args.with_embedded_models

    # Validate version format.
    if not re.match(r"^\d+\.\d+\.\d+$", args.version):
        print(
            f"error: --version must be MAJOR.MINOR.PATCH (e.g. 1.0.0), got: {args.version!r}",
            file=sys.stderr,
        )
        sys.exit(1)
    if (args.release or args.release_dry_run) and not args.with_models:
        print(
            "error: --release and --release-dry-run require --with-models so the "
            "matching offline model-set asset ships with the feature archive",
            file=sys.stderr,
        )
        sys.exit(1)
    version_parts = tuple(int(part) for part in args.version.split("."))
    if version_parts < (1, 0, 0):
        print(
            f"error: --version must be 1.0.0 or later; pre-1.0.0 packaging targets are no longer supported ({args.version!r})",
            file=sys.stderr,
        )
        sys.exit(1)


    # Resolve output directory; create ~/.wavefoundry/dist/ if needed.
    if args.output:
        output_dir = Path(args.output).expanduser()
        if not output_dir.exists():
            print(f"error: output directory does not exist: {output_dir}", file=sys.stderr)
            sys.exit(1)
        if not output_dir.is_dir():
            print(f"error: output path is not a directory: {output_dir}", file=sys.stderr)
            sys.exit(1)
    else:
        output_dir = _DEFAULT_DIST_DIR.expanduser()
        output_dir.mkdir(parents=True, exist_ok=True)

    # Always resolve the repo root from the script's location for pre-flight checks.
    _script_dir = Path(__file__).resolve().parent
    try:
        repo_root = find_repo_root(_script_dir)
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)

    # Wave 131bt close-out: 4-character base36 build suffix that is temporally
    # lex-sortable. Replaces the prior lifecycle-prefix tail (which wrapped
    # every 36 minutes and broke `_find_latest_release_zip`'s lex tie-break).
    try:
        build_prefix = _current_build_suffix()
    except (ImportError, ValueError, OSError) as exc:
        print(f"error: failed to compute build suffix: {exc}", file=sys.stderr)
        sys.exit(1)

    # Full version string: MAJOR.MINOR.PATCH+<build_prefix>
    full_version = f"{args.version}+{build_prefix}"

    # Pre-flight: release-mode gates run BEFORE the build so failures abort
    # cheaply without wasting time on a packaging pass that's about to be
    # discarded.
    release_notes_body = ""
    qualified_hash: Optional[str] = None
    if args.accept_qualification_exception and not (args.release or args.release_dry_run):
        print("error: --accept-qualification-exception applies only with --release or --release-dry-run",
              file=sys.stderr)
        sys.exit(1)
    if args.release or args.release_dry_run:
        try:
            _check_git_working_tree_clean(repo_root)
            _check_on_main_branch(repo_root)
            _check_tag_does_not_exist(repo_root, f"v{args.version}")
            _check_gh_authenticated()
            changelog_body = _extract_changelog_section(
                repo_root / "CHANGELOG.md", args.version
            )
            if not changelog_body.strip():
                raise RuntimeError(
                    f"CHANGELOG.md has no `## [{args.version}]` section. "
                    "Add the section (with release notes) before --release."
                )
            claim_failures = _check_changelog_claims(changelog_body, args.version)
            if claim_failures:
                raise RuntimeError(
                    "changelog version-constant claims do not match the code "
                    "constants:\n  " + "\n  ".join(claim_failures)
                )
            release_notes_body = _assemble_release_notes(repo_root, changelog_body)
            # Wave 20wq7: the qualification gate runs last in preflight, before
            # the docs gate and any build or stamp.
            qualification_exceptions = _parse_qualification_exceptions(
                args.accept_qualification_exception
            )
            qualified_hash = _current_framework_inputs_hash(repo_root)
            qualification_section = _check_release_qualification(
                repo_root, qualification_exceptions, inputs_hash=qualified_hash
            )
            if qualification_section:
                release_notes_body = release_notes_body.rstrip() + "\n\n" + qualification_section
            if args.release_dry_run:
                print("[--release-dry-run] release notes qualification section:", file=sys.stderr)
                print(qualification_section, file=sys.stderr)
        except RuntimeError as exc:
            print(f"error: release preflight failed: {exc}", file=sys.stderr)
            sys.exit(1)
    else:
        # Pre-flight: every versioned build requires its changelog entry
        # (wave 1t9tj). The pack ships CHANGELOG.md as its only offline
        # release surface, so the entry must exist before any zip is built —
        # otherwise a circulating pack carries a stale release history, as the
        # published 1.14.0 archive did. The release path performs the same
        # check inside its own preflight above.
        packed_section = _extract_changelog_section(
            repo_root / "CHANGELOG.md", args.version
        )
        if not packed_section.strip():
            print(
                f"error: CHANGELOG.md has no `## [{args.version}]` section. "
                "Create the changelog entry first — the pack ships "
                "CHANGELOG.md, and every build must carry the release "
                "history for the version it stamps.",
                file=sys.stderr,
            )
            sys.exit(1)
        # Wave 1wip2 (1wgwn): the section being packed must not carry stale
        # version-constant claims — the coverage the 1.20.0 pm1l pack escaped
        # through (its internal changelog shipped `CHUNKER_VERSION` "to 34"
        # while the delivered tree was 37).
        claim_failures = _check_changelog_claims(packed_section, args.version)
        if claim_failures:
            print(
                "error: changelog version-constant claims do not match the "
                "code constants:\n  " + "\n  ".join(claim_failures),
                file=sys.stderr,
            )
            sys.exit(1)

    # Pre-flight: docs gate (gardener + lint).
    if not args.skip_docs_gate:
        check_docs_gate(repo_root)

    # Pre-flight: same-semver collision warning (wave 131bt 131ht). When packs at
    # the same MAJOR.MINOR.PATCH already exist in the dist dir, surface the existing
    # filenames so the operator can decide whether to bump semver or proceed. Non-
    # blocking: same-semver repackages have legitimate uses (bad-artifact recovery,
    # content-only fixes). Mtime tie-break in `_find_latest_release_zip` ensures the
    # newest pack still wins on `wave_upgrade`, but bumping semver makes it explicit.
    _warn_on_same_semver_collision(output_dir, args.version)
    public_packages_before = _public_package_snapshot(output_dir)
    try:
        _reject_stale_public_build_artifacts(public_packages_before)
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)

    model_zip: Path | None = None
    combined_zip: Path | None = None
    if qualified_hash is not None:
        # The docs gate ran after preflight; the pack must be the qualified tree.
        try:
            rebuilt_hash = _current_framework_inputs_hash(repo_root)
        except RuntimeError as exc:
            print(f"error: release preflight failed: {exc}", file=sys.stderr)
            sys.exit(1)
        if rebuilt_hash != qualified_hash:
            print(
                "error: the framework tree changed after release qualification was checked "
                "(the docs gate or another process edited it); requalify and rerun",
                file=sys.stderr,
            )
            sys.exit(1)
    try:
        zip_path = build_zip(
            output_dir,
            args.version,
            build_prefix,
            update_manifest=not args.skip_manifest_update,
            # 1p4ww: the framework index is no longer shipped — framework seeds/README
            # fold into each project's own docs index. The pack ships framework SOURCE only.
            verbose=args.verbose,
            release_tag=f"v{args.version}" if args.release else None,
        )
        bridge_artifacts = (
            build_protocol_bridge_artifacts(
                zip_path,
                version=args.version,
                build_prefix=build_prefix,
            )
            if zip_path.is_file()
            else {}
        )
        release_package = (
            build_upgrade_bundle(
                zip_path,
                bridge_artifacts,
                version=args.version,
                build_prefix=build_prefix,
            )
            if bridge_artifacts
            else None
        )
        if release_package is not None and release_package != zip_path:
            raise RuntimeError(
                "upgrade assembly must preserve the single public package path"
            )
        if args.with_models:
            import model_bundle
            model_zip = model_bundle.build_bundle(output_dir)
            print(f"Model companion: {model_zip}", file=sys.stderr)
        if args.with_embedded_models:
            combined_zip = build_embedded_package(zip_path, model_zip)
            print(f"Combined upgrade package: {combined_zip}", file=sys.stderr)
        _enforce_single_public_package(
            output_dir,
            zip_path,
            public_packages_before,
            extra_expected=[p for p in (model_zip, combined_zip) if p is not None],
        )
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)

    version_path = Path(__file__).resolve().parent.parent / "VERSION"
    stamp = version_path.read_text(encoding="utf-8").strip()
    print(zip_path)
    print(f"Stamped VERSION: {stamp}", file=sys.stderr)

    # Release mode: post-build assertion + orchestration. Post-build because
    # the zip-contains-index check has to actually inspect the produced zip;
    # nothing earlier can verify it.
    if args.release or args.release_dry_run:
        # 1p4ww: the framework index is no longer shipped (folded into each project's
        # docs index), so the old "published zip must contain a framework index" guard
        # is removed. The dead build/guard functions are cleaned up in Stage 4.
        try:
            _run_release_orchestration(
                repo_root,
                args.version,
                zip_path,
                release_notes_body,
                dry_run=args.release_dry_run,
                extra_assets=[p for p in (model_zip, combined_zip) if p is not None],
            )
        except RuntimeError as exc:
            print(f"error: release orchestration failed: {exc}", file=sys.stderr)
            sys.exit(1)
        if args.release_dry_run:
            print(
                "[--release-dry-run] complete; no commit, tag, push, or GitHub "
                "release was created. Local archive and VERSION/manifest/README "
                "stamps remain — the working tree may be dirty (restore with: "
                "git restore -- .wavefoundry/framework/VERSION "
                "docs/prompts/prompt-surface-manifest.json README.md).",
                file=sys.stderr,
            )
        else:
            print(f"Released v{args.version}.", file=sys.stderr)


if __name__ == "__main__":
    main()
