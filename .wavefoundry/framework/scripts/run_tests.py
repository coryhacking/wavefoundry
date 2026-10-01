#!/usr/bin/env python3
"""Run Wavefoundry framework unit tests without writing __pycache__ under scripts/.

Test cache
----------
After a successful run, the result is recorded in
``.wavefoundry/framework/test-cache.json`` (gitignored, excluded from the
distribution zip).  Subsequent invocations hash all test-relevant files under
the framework directory and compare to the stored hash.  If the hash matches
the last green run, the suite is skipped and the cached count is reported.

    python3 run_tests.py              # skip if nothing has changed
    python3 run_tests.py --no-cache   # force a full run regardless
    python3 run_tests.py --help       # every option

The hash covers every file under ``.wavefoundry/framework/`` except packaging
artifacts (``VERSION``, ``MANIFEST``), the cache file itself, and the binary
index directory.  This includes all Python scripts, seed documents, dashboard
assets, and any test fixture files — anything that could change a test result.

Parallel execution
------------------
Each test file runs in its own subprocess.  Up to 6 files run concurrently
(capped below cpu_count to leave headroom for subprocess-heavy test files).
Output is buffered and printed file-by-file after all workers finish so that
output lines are never interleaved.
"""

from __future__ import annotations

import concurrent.futures
import datetime
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import NamedTuple

sys.dont_write_bytecode = True

# Suppress dashboard browser open for the entire test suite (see dashboard_lib).
os.environ.setdefault("WAVEFOUNDRY_SUPPRESS_DASHBOARD_BROWSER", "1")

_SCRIPT_DIR = Path(__file__).resolve().parent
_TESTS_DIR = _SCRIPT_DIR / "tests"
_FRAMEWORK_DIR = _SCRIPT_DIR.parent
_CACHE_FILE = _FRAMEWORK_DIR / "test-cache.json"
_LOCK_FILE = _FRAMEWORK_DIR / "test-run.lock"
# Wave 1z8ox (1z8ov): the repository the standing repository-state guard
# snapshots, the edit-gate file it always includes, and the only paths it
# excludes (the receipt and lock this runner writes itself).
_REPO_ROOT = _FRAMEWORK_DIR.parent.parent
_GUARD_OVERRIDES_REL = ".wavefoundry/guard-overrides.json"
_REPO_GUARD_EXCLUDE = frozenset({
    ".wavefoundry/framework/test-cache.json",
    ".wavefoundry/framework/test-run.lock",
})

# Wave 1p9j0: msvcrt.locking (native Windows) is mandatory byte-range, so the run lock is taken on
# a SENTINEL byte at this high fixed offset — NOT byte 0 — so the same-handle pid write/truncate at
# byte 0 below is not blocked, mirroring dashboard_lib.py's sentinel-offset rationale.
_LOCK_BYTE_OFFSET = 1 << 30  # 1 GiB — well beyond the short pid line written at byte 0

# Wave 1t72b (1t727): defense-in-depth exclusion against the background project
# indexer. A bounded reproduction effort (isolated x3, full suite vs live code
# rebuild, six parallel runs vs rebuild) could NOT reproduce the test_indexer
# interference on demand, so the suite waits for a running index build rather
# than racing it. Bounded: on timeout the run fails with a diagnostic naming
# the holder instead of starting a contended run.
_INDEX_BUILD_WAIT_SECONDS = 600
_INDEX_BUILD_POLL_SECONDS = 2.0
_INDEX_BUILD_PROBE = None  # test seam; defaults to indexer._index_build_lock_held


def _probe_index_build_lock() -> "tuple[bool, object]":
    """One non-destructive probe of the project index-build lock."""
    index_dir = _FRAMEWORK_DIR.parent / "index"
    probe = _INDEX_BUILD_PROBE
    if probe is None:
        try:
            import indexer as _indexer
            probe = _indexer._index_build_lock_held
        except Exception:
            return (False, None)
    try:
        held, holder = probe(index_dir)
    except Exception:
        return (False, None)
    return (bool(held), holder)


def _wait_for_index_build() -> "str | None":
    """Wait (bounded) for a running project index build; None means proceed."""
    index_dir = _FRAMEWORK_DIR.parent / "index"
    probe = _INDEX_BUILD_PROBE
    if probe is None:
        try:
            import indexer as _indexer
            probe = _indexer._index_build_lock_held
        except Exception:
            return None  # best-effort: never let the guard break the runner
    deadline = time.monotonic() + _INDEX_BUILD_WAIT_SECONDS
    announced = False
    while True:
        try:
            held, holder_pid = probe(index_dir)
        except Exception:
            return None
        if not held:  # False or undetermined (None): proceed
            return None
        if not announced:
            print(
                "run_tests: waiting for the running project index build to "
                f"finish (holder pid {holder_pid or 'unknown'}) …"
            )
            announced = True
        if time.monotonic() >= deadline:
            return (
                "run_tests: a project index build is still running after "
                f"{_INDEX_BUILD_WAIT_SECONDS}s (holder pid {holder_pid or 'unknown'}, "
                f"lock {index_dir / 'index-build.lock'}); refusing to start a "
                "contended run. Re-run once the build finishes."
            )
        time.sleep(_INDEX_BUILD_POLL_SECONDS)

# Ensure scripts/ is on sys.path explicitly — tests/__init__.py handles this
# for individual-file runs; repeat it here so run_tests.py is self-contained
# and does not rely on Python's implicit entry-point path insertion.
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

import subprocess_util  # UTF-8 child env for worker spawns (wave 1p9j0)
import venv_bootstrap  # the single venv resolver (wave 1p7pl)

# Activate the shared tool venv IN-PROCESS before any heavy work (wave 1p7pl/1p802 AC-3): every
# direct-launch entry self-bootstraps so a bare `python run_tests.py` runs the suite with the venv
# packages. No-op when already in the venv or when it does not exist yet (fresh bootstrap).
venv_bootstrap.activate_tool_venv()


# Files and directories under _FRAMEWORK_DIR excluded from the cache hash.
# These are packaging artifacts, runtime state, or generated bytecode — changes
# to them do not affect test outcomes.
_HASH_EXCLUDE_NAMES = {"VERSION", "MANIFEST", "test-cache.json", "test-run.lock"}
_HASH_EXCLUDE_DIRS = {"index", "__pycache__", ".pytest_cache"}

# Per-file worker timeout (seconds). Also the upper validity bound for
# advisory ``durations_s`` values (Requirement 3 of 1tm6d).
_FILE_TIMEOUT_SECONDS = 600

# Benchmark-only schedule-control modes (Requirement 4 of 1tm6d).
_SCHEDULE_MODES = ("bootstrap", "alphabetical", "timing")

_USAGE = """usage: run_tests.py [--no-cache | --file NAME ... | --profile NAME [--file NAME ...]
                    | --schedule-control MODE --timings-file PATH]

Run the framework test suite, one subprocess per test file.

  (no option)               full run; skipped when the last green receipt
                            matches the framework tree, and a green run
                            writes the receipt (test-cache.json); refused
                            (exit 2) while WAVEFOUNDRY_TEST_PROFILE is set
  --no-cache                full run even when the receipt is current
  --file NAME               focused run of one discovered test_*.py file
                            (repeatable); writes no receipt and is not
                            delivery evidence
  --profile NAME            second-profile run (change 1zim1): copy the
                            git-tracked and untracked non-ignored files into a
                            temporary git repository, apply the profile asset
                            tests/fixtures/profiles/NAME.json to its
                            vocabulary_profile.py, record_paths.py and
                            mcp_tool_extensions.py, write
                            the configured waves-root README, and run the
                            suite there as a focused run (all files, or the
                            --file selection) with WAVEFOUNDRY_TEST_PROFILE=NAME
                            set for the copy, so its guards expect the
                            profile. Reports a per-file result,
                            never writes this tree's receipt, and is not
                            delivery evidence. On demand and at release.
  --schedule-control MODE   benchmark-only run (bootstrap|alphabetical|timing);
                            needs --timings-file PATH
  --help                    show this message
"""


def _hash_inputs() -> str:
    """Return a SHA-256 digest of all test-relevant files under the framework directory.

    Covers Python scripts, seed documents, dashboard assets, and any other
    fixture files that could change a test result.  Excludes packaging
    artifacts (VERSION, MANIFEST), the cache file itself, and the binary
    index directory.

    Both relative paths and file contents are hashed so renames, additions,
    deletions, and edits all produce a different digest.
    """
    h = hashlib.sha256()
    for path in sorted(_FRAMEWORK_DIR.rglob("*")):
        if path.is_dir():
            continue
        rel = path.relative_to(_FRAMEWORK_DIR)
        # Any component match (wave 1tmtx): a NESTED scripts/__pycache__/*.pyc
        # (created by an external import of run_tests before its
        # dont_write_bytecode takes effect) slipped past the old parts[0]
        # check and, together with the per-run test-run.lock pid write, made
        # the digest unstable across runs — found when it invalidated the
        # schedule-control comparison.
        if any(part in _HASH_EXCLUDE_DIRS for part in rel.parts[:-1]):
            continue
        if rel.name in _HASH_EXCLUDE_NAMES:
            continue
        h.update(rel.as_posix().encode())
        h.update(path.read_bytes())
    return h.hexdigest()


def _read_cache() -> dict | None:
    """Read and parse the test cache file, returning None on any error."""
    try:
        return json.loads(_CACHE_FILE.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None


def _write_cache(inputs_hash: str, test_count: int,
                 durations: dict[str, float] | None = None) -> None:
    """Write a successful test cache entry atomically.  Silent on failure (non-fatal).

    ``durations`` (wave 1tmtx): optional advisory per-file elapsed seconds,
    persisted as ``durations_s`` beside the last-green fields. Values are
    clamped to the per-file timeout so a written entry is always valid under
    the reader's schema. Advisory only — never skip authority.
    """
    data = {
        "inputs_hash": inputs_hash,
        "ran_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "test_count": test_count,
        "result": "ok",
    }
    if durations:
        data["durations_s"] = {
            name: round(min(float(seconds), float(_FILE_TIMEOUT_SECONDS)), 3)
            for name, seconds in sorted(durations.items())
        }
    try:
        tmp = _CACHE_FILE.with_name(_CACHE_FILE.name + ".tmp")
        tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        os.replace(tmp, _CACHE_FILE)
    except Exception:  # noqa: BLE001
        pass  # cache write failure is non-fatal


def _clean_pycache() -> None:
    """Remove all __pycache__ directories under the framework directory.

    Called immediately before running the test suite to ensure no stale
    bytecode affects test behaviour.  Silent on any I/O error.
    """
    import shutil
    for pycache in _FRAMEWORK_DIR.rglob("__pycache__"):
        if pycache.is_dir():
            try:
                shutil.rmtree(pycache)
            except Exception:  # noqa: BLE001
                pass


def stray_artifact_paths(scripts_dir: Path | None = None) -> list[str]:
    """Wave 1t3ek (1t231): paths of stray state artifacts a test run created.

    A test that writes durable state relative to cwd (instead of its fixture
    root) lands a nested ``.wavefoundry`` directory under the scripts
    directory. Returns repo-style relative paths; empty when clean.
    """
    base = (scripts_dir or _SCRIPT_DIR) / ".wavefoundry"
    if not base.exists():
        return []
    if base.is_file():
        return [base.name]
    return sorted(
        str(p.relative_to(base.parent)) for p in base.rglob("*") if p.is_file()
    ) or [base.name]


# Wave 1z8ox (1z8ov, delivery finding DEL-F1): regions of a wave record the
# framework rewrites on its own while tests run. MCP calls record context
# usage, and the Claude Stop hook and the MCP quiet-period monitor publish it by
# rewriting the open wave record (context_efficiency.replace_checkpoint_block,
# then exploration_avoided.replace_checkpoint_block). Each entry is (optional
# heading, begin marker, end marker); the state comments sit inside the
# markers. Pinned against the owning modules' constants by
# tests/test_run_tests_repo_guard.py, so run_tests never imports them.
_PROJECTED_WAVE_REGIONS = (
    ("## Context Efficiency",
     "<!-- wave:context-efficiency begin -->",
     "<!-- wave:context-efficiency end -->"),
    ("## Estimated Exploration Avoided",
     "<!-- wave:exploration-avoided begin -->",
     "<!-- wave:exploration-avoided end -->"),
)
# Legacy marker names the context-efficiency projection canonicalizes in the
# whole record (context_efficiency._LEGACY_CONTEXT_EFFICIENCY_MARKERS).
_LEGACY_PROJECTION_MARKERS = (
    ("<!-- wavefoundry:context-efficiency begin -->", "<!-- wave:context-efficiency begin -->"),
    ("<!-- wavefoundry:context-efficiency end -->", "<!-- wave:context-efficiency end -->"),
    ("<!-- wavefoundry:context-efficiency-state ", "<!-- wave:context-efficiency-state "),
    ("<!-- wavefoundry:context-efficiency-carrier begin -->", "<!-- wave:context-efficiency-carrier begin -->"),
    ("<!-- wavefoundry:context-efficiency-carrier end -->", "<!-- wave:context-efficiency-carrier end -->"),
)
_PROJECTED_REGION_PATTERNS = tuple(
    re.compile(
        r"(?:" + re.escape(heading) + r"[ \t]*\r?\n\s*)?"
        + re.escape(begin) + r".*?" + re.escape(end),
        re.S,
    )
    for heading, begin, end in _PROJECTED_WAVE_REGIONS
)
_REGION_SEAM = "\x00"
_GIT_LISTING_TIMEOUT_SECONDS = 60
# Why the most recent repo_state_snapshot returned None (stated to the operator).
_repo_state_unavailable_reason = ""


def _run_tree_kill(cmd, **kwargs):
    """Run ``cmd`` so a timeout ends its whole process tree (wave 1z8ox, 1z8ow).

    The helper is resolved at call time: an upgrade runner may have an older
    ``subprocess_util`` loaded that lacks ``run_with_tree_kill``, so fall back
    to ``isolated_run``. Raises ``AttributeError`` when neither exists.
    """
    run = getattr(subprocess_util, "run_with_tree_kill", None) or subprocess_util.isolated_run
    return run(cmd, **kwargs)


def _wave_record_matcher(root: Path) -> "tuple[str, str] | None":
    """(waves-root prefix, record file name) for ``root``, or ``None``.

    Both come from the stdlib-only layout modules (``record_paths``,
    ``vocabulary_profile``). When they cannot be imported there is no matcher:
    no file is treated as a wave record, so the projection tolerance is off and
    the guard stays strict rather than guessing a layout.
    """
    try:
        import record_paths as _record_paths
        import vocabulary_profile as _vocabulary_profile
        waves_rel = _record_paths.unvalidated_record_roots(root).waves_rel
        record_name = _vocabulary_profile.RECORD_FILENAME
        if waves_rel and isinstance(record_name, str) and record_name:
            return waves_rel.rstrip("/") + "/", record_name
    except Exception:  # noqa: BLE001
        pass
    return None


def _is_wave_record(rel: str, matcher: "tuple[str, str] | None") -> bool:
    if matcher is None:
        return False
    prefix, record_name = matcher
    return rel.startswith(prefix) and rel.rsplit("/", 1)[-1] == record_name


def _content_digest(path: Path, st: os.stat_result) -> str:
    """SHA-256 of a file's content, or of its link target for a symlink."""
    import stat as _stat
    if _stat.S_ISLNK(st.st_mode):
        return "link:" + hashlib.sha256(os.fsencode(os.readlink(path))).hexdigest()
    return hashlib.sha256(path.read_bytes()).hexdigest()


def repo_state_snapshot(repo_root: Path | None = None) -> "dict[str, tuple | None] | None":
    """Wave 1z8ox (1z8ov): snapshot of the repository state a test must never change.

    Covers every tracked file and every untracked file git does not ignore
    (``git ls-files -co --exclude-standard``), plus the edit-gate state file
    ``.wavefoundry/guard-overrides.json`` (ignored by git, but a security
    control). Each entry maps a repo-relative POSIX path to ``(size,
    mtime_ns)``, or ``None`` when the path is absent. The edit-gate file is
    compared by content hash (``("sha256", digest)``), not size and mtime, and
    each wave record also keeps its bytes (``(size, mtime_ns, bytes)``) so
    ``_repo_state_changes`` can tolerate the framework's own context-efficiency
    projection. Other files are stat only: the tree holds thousands. Ignored
    runtime paths (logs, index, locks, ``__pycache__``) and ``.git/`` are
    outside the snapshot; the isolated census covers those. The runner's own
    receipt and lock are excluded. Returns ``None`` when git is unavailable,
    the root is not a git checkout or the listing timed out, with the cause in
    ``_repo_state_unavailable_reason``, so the caller can state it.
    """
    global _repo_state_unavailable_reason
    _repo_state_unavailable_reason = ""
    root = repo_root or _REPO_ROOT
    try:
        # The listing ends its whole process tree on timeout (wave 1z8ox, 1z8ow).
        listing = _run_tree_kill(
            ["git", "ls-files", "-co", "--exclude-standard", "-z"],
            cwd=str(root),
            capture_output=True,
            check=False,
            stdin=subprocess.DEVNULL,
            timeout=_GIT_LISTING_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        _repo_state_unavailable_reason = (
            f"git ls-files did not finish within {_GIT_LISTING_TIMEOUT_SECONDS}s"
        )
        return None
    except AttributeError:
        _repo_state_unavailable_reason = "subprocess_util has no process runner"
        return None
    except (OSError, subprocess.SubprocessError):
        _repo_state_unavailable_reason = "git is unavailable"
        return None
    if listing.returncode != 0:
        _repo_state_unavailable_reason = "the root is not a git checkout"
        return None
    rels = {p for p in listing.stdout.decode("utf-8", errors="surrogateescape").split("\0") if p}
    rels.add(_GUARD_OVERRIDES_REL)
    matcher = _wave_record_matcher(root)
    snapshot: dict[str, tuple | None] = {}
    for rel in rels:
        if rel in _REPO_GUARD_EXCLUDE:
            continue
        path = root / rel
        try:
            st = os.lstat(path)
            if rel == _GUARD_OVERRIDES_REL:
                snapshot[rel] = ("sha256", _content_digest(path, st))
            elif _is_wave_record(rel, matcher) and not os.path.islink(path):
                snapshot[rel] = (st.st_size, st.st_mtime_ns, path.read_bytes())
            else:
                snapshot[rel] = (st.st_size, st.st_mtime_ns)
        except OSError:
            snapshot[rel] = None
    return snapshot


def _strip_projected_regions(data: bytes) -> str:
    """A wave record's text with the framework-projected regions removed.

    Legacy marker names are canonicalized first (the projection does the same
    to the whole record), each projected region and its heading becomes one
    seam, the whitespace the projection rewrites around a region collapses
    into that seam, and seams at the ends of the record are dropped (the
    projection appends a region the record lacked).
    """
    text = data.decode("utf-8", errors="surrogateescape")
    for legacy, canonical in _LEGACY_PROJECTION_MARKERS:
        text = text.replace(legacy, canonical)
    for pattern in _PROJECTED_REGION_PATTERNS:
        text = pattern.sub(_REGION_SEAM, text)
    text = re.sub(r"\s*" + _REGION_SEAM + r"\s*", _REGION_SEAM, text)
    text = re.sub(_REGION_SEAM + "+", _REGION_SEAM, text)
    return text.strip().strip(_REGION_SEAM).strip()


def _projection_only_change(before: "tuple | None", after: "tuple | None") -> bool:
    """True when two wave-record entries differ only inside projected regions."""
    if not (isinstance(before, tuple) and isinstance(after, tuple)
            and len(before) == 3 and len(after) == 3):
        return False
    if before[:2] == after[:2]:
        return True  # size and mtime unchanged: not a change
    return _strip_projected_regions(before[2]) == _strip_projected_regions(after[2])


def _repo_state_changes(before: "dict[str, tuple | None]",
                        after: "dict[str, tuple | None]") -> list[str]:
    """Paths created, modified or deleted between two ``repo_state_snapshot`` results.

    A wave record whose only difference is the framework's own
    context-efficiency projection (DEL-F1) is not a change.
    """
    changed = []
    for rel in sorted(set(before) | set(after)):
        b, a = before.get(rel), after.get(rel)
        if b != a and not _projection_only_change(b, a):
            changed.append(rel)
    return changed


def _stray_artifact_failure(preexisting: list[str],
                            repo_before: "dict[str, tuple | None] | None" = None,
                            repo_root: Path | None = None) -> str | None:
    """Return a failure message when the run created stray artifacts or changed repository state.

    ``repo_before`` (wave 1z8ox, 1z8ov) is the ``repo_state_snapshot`` taken
    after the run lock was acquired; when given, the repository is snapshotted
    again and every created, modified or deleted tracked or non-ignored file,
    and any change to the edit-gate file, fails the run. A second snapshot
    that cannot be taken (for example a timed-out listing) also fails the run,
    with the cause stated.
    """
    created = [p for p in stray_artifact_paths() if p not in preexisting]
    changed: list[str] = []
    unverified = ""
    if repo_before is not None:
        repo_after = repo_state_snapshot(repo_root)
        if repo_after is None:
            unverified = _repo_state_unavailable_reason or "the second snapshot failed"
        else:
            changed = _repo_state_changes(repo_before, repo_after)
    if not created and not changed and not unverified:
        return None
    parts = []
    if created:
        parts.append(
            "STRAY TEST ARTIFACTS: a test wrote durable state relative to cwd "
            "instead of its fixture root:\n  "
            + "\n  ".join(created)
            + "\nFix the offending test (see the 1t231 pattern: unmocked "
            "cwd-relative write paths) and delete the artifacts."
        )
    if changed:
        parts.append(
            "REPOSITORY CHANGED DURING THE TEST RUN: tests must write only under "
            "temporary roots, but these tracked, non-ignored or edit-gate paths "
            "were created, modified or deleted:\n  "
            + "\n  ".join(changed)
            + "\nA concurrent edit by an operator or agent during the run, "
            "including opening or closing an edit gate, also trips this guard; "
            "if that is the cause, re-run once the tree is quiet. Otherwise fix "
            "the offending test to write under a temporary root."
        )
    if unverified:
        parts.append(
            "REPOSITORY STATE NOT VERIFIED AFTER THE TEST RUN: the end-of-run "
            f"snapshot could not be taken ({unverified}), so the run cannot show "
            "it left the repository unchanged. Re-run once git responds."
        )
    return "\n\n".join(parts)


def _cache_hit(inputs_hash: str, cache: dict | None = None) -> dict | None:
    """Return the cached entry if its hash matches and the run was passing, else None.

    ``cache`` lets main() pass its single up-front ``_read_cache()`` result
    (Requirement 3 of 1tm6d: an ordinary run reads the cache once); calling
    without it preserves the standalone read-then-check behavior.
    """
    if cache is None:
        cache = _read_cache()
    # Valid-JSON-but-not-an-object cache content (a list, string, or number)
    # must degrade to a miss, not an AttributeError (delivery-review finding).
    if not isinstance(cache, dict):
        return None
    if cache.get("inputs_hash") == inputs_hash and cache.get("result") == "ok":
        return cache
    return None


def _validated_durations(cache: dict | None, test_files: list[Path]) -> dict[str, float]:
    """Advisory per-file durations from a cache-shaped entry, independently validated.

    Keeps only entries whose key is a currently discovered test-file basename
    and whose value is a finite, non-boolean, nonnegative number no greater
    than the per-file timeout (Requirement 3 of 1tm6d). Malformed containers
    and entries, and unknown/stale keys, are dropped independently and never
    invalidate the surrounding last-green entry. Timing is advisory ordering
    input only; it never authorizes a skip or a pass.
    """
    if not isinstance(cache, dict):
        return {}
    raw = cache.get("durations_s")
    if not isinstance(raw, dict):
        return {}
    current = {p.name for p in test_files}
    validated: dict[str, float] = {}
    for key, value in raw.items():
        if not isinstance(key, str) or key not in current:
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        seconds = float(value)
        if not math.isfinite(seconds) or seconds < 0 or seconds > _FILE_TIMEOUT_SECONDS:
            continue
        validated[key] = seconds
    return validated


def _write_timings_manifest(path_str: str, source_digest: str,
                            results: list["FileResult"]) -> str | None:
    """Atomically write the schedule-control timing manifest; error string on failure.

    Unlike the last-green cache, a bootstrap manifest write failure is loud —
    the manifest IS the bootstrap deliverable (Requirement 4 of 1tm6d).
    """
    data = {
        "source_digest": source_digest,
        "durations_s": {
            r.name: round(min(r.elapsed_s, float(_FILE_TIMEOUT_SECONDS)), 3)
            for r in sorted(results, key=lambda r: r.name)
        },
    }
    try:
        path = Path(path_str)
        tmp = path.with_name(path.name + ".tmp")
        tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        os.replace(tmp, path)
    except Exception as exc:  # noqa: BLE001
        return f"failed to write timings manifest {path_str}: {exc}"
    return None


def _read_timings_manifest(path_str: str, source_digest: str,
                           test_files: list[Path]) -> tuple[dict[str, float] | None, str | None]:
    """Validate and read the manifest for a schedule-control candidate run.

    The comparison is invalid (error) when the manifest is unreadable or
    malformed, its source digest does not match the current tree, or any
    discovered file lacks a valid measured duration (Requirement 4 of 1tm6d).
    Candidate runs never modify the manifest.
    """
    try:
        data = json.loads(Path(path_str).read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return None, f"timings manifest {path_str} is unreadable: {exc}"
    if not isinstance(data, dict) or data.get("source_digest") != source_digest:
        return None, (
            "timings manifest source digest does not match the current tree; "
            "re-run --schedule-control bootstrap on the frozen layout"
        )
    durations = _validated_durations({"durations_s": data.get("durations_s")}, test_files)
    missing = sorted(p.name for p in test_files if p.name not in durations)
    if missing:
        return None, (
            "timings manifest lacks a valid duration for: "
            + ", ".join(missing)
            + "; the schedule comparison is invalid"
        )
    return durations, None


class _UsageError(Exception):
    """Invalid command line; the message is printed to stderr and main exits 2."""


def _parse_args(argv: list[str]) -> dict:
    """Strict argv parsing (Requirement 9 of 1tm6d).

    Unknown options, positional arguments, missing values, and invalid flag
    combinations fail clearly and deterministically — and always before any
    input hashing, cache read, or timing-map read. A prepare-time caller
    census (2026-08-27) confirmed every in-tree invocation is the bare form
    or ``--no-cache`` only, so this narrowing strands no caller.
    """
    opts: dict = {"no_cache": False, "files": [], "schedule_control": None, "timings_file": None,
                  "profile": None, "help": False}
    args = argv[1:]
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--no-cache":
            opts["no_cache"] = True
        elif arg in ("--help", "-h"):
            opts["help"] = True
        elif arg == "--profile":
            if i + 1 >= len(args):
                raise _UsageError("--profile requires a value (a profile asset name under tests/fixtures/profiles)")
            if opts["profile"] is not None:
                raise _UsageError("--profile may be given only once")
            opts["profile"] = args[i + 1]
            i += 1
        elif arg == "--file":
            if i + 1 >= len(args):
                raise _UsageError("--file requires a value (a discovered test_*.py basename)")
            opts["files"].append(args[i + 1])
            i += 1
        elif arg == "--schedule-control":
            if i + 1 >= len(args):
                raise _UsageError("--schedule-control requires a value (bootstrap|alphabetical|timing)")
            if opts["schedule_control"] is not None:
                raise _UsageError("--schedule-control may be given only once")
            value = args[i + 1]
            if value not in _SCHEDULE_MODES:
                raise _UsageError(
                    f"invalid --schedule-control value {value!r} (bootstrap|alphabetical|timing)"
                )
            opts["schedule_control"] = value
            i += 1
        elif arg == "--timings-file":
            if i + 1 >= len(args):
                raise _UsageError("--timings-file requires a path value")
            if opts["timings_file"] is not None:
                raise _UsageError("--timings-file may be given only once")
            opts["timings_file"] = args[i + 1]
            i += 1
        else:
            kind = "unknown option" if arg.startswith("-") else "positional argument"
            raise _UsageError(f"{kind} {arg!r} is not accepted")
        i += 1
    if opts["profile"] is not None and (
        opts["no_cache"] or opts["schedule_control"] is not None or opts["timings_file"] is not None
    ):
        raise _UsageError(
            "--profile is mutually exclusive with --no-cache, --schedule-control and --timings-file"
        )
    if opts["files"] and opts["no_cache"]:
        raise _UsageError(
            "--file and --no-cache are mutually exclusive (focused runs never touch the cache)"
        )
    if opts["schedule_control"] is not None:
        if opts["files"] or opts["no_cache"]:
            raise _UsageError("--schedule-control is mutually exclusive with --file and --no-cache")
        if opts["timings_file"] is None:
            raise _UsageError("--schedule-control requires --timings-file <path>")
    elif opts["timings_file"] is not None:
        raise _UsageError("--timings-file requires --schedule-control")
    return opts


def _selector_format_error(selectors: list[str]) -> str | None:
    """The first ``--file`` selector that is not a unique ``test_*.py``
    basename, as a message; ``None`` when every selector is well-formed.
    Needs no discovered set, so the second-profile run checks it before it
    copies the tree."""
    seen: set[str] = set()
    for raw in selectors:
        if raw in seen:
            return f"duplicate --file selector {raw!r}"
        seen.add(raw)
        if not raw or "/" in raw or "\\" in raw or Path(raw).is_absolute() or Path(raw).name != raw:
            return f"--file takes an exact test file basename, not a path: {raw!r}"
        if not (raw.startswith("test_") and raw.endswith(".py")):
            return f"--file selector {raw!r} is not a test_*.py basename"
    return None


def _validate_focus_selectors(selectors: list[str],
                              test_files: list[Path]) -> tuple[list[Path] | None, str | None]:
    """Validate ``--file`` selectors against the discovered direct-child set.

    Selectors are exact discovered ``test_*.py`` basenames. Duplicates,
    path-like values, non-test names, and absent files fail deterministically
    (Requirement 9 of 1tm6d). Validation runs before any hashing, cache, or
    timing-map access — focused runs never reach those seams at all.
    """
    error = _selector_format_error(selectors)
    if error is not None:
        return None, error
    discovered = {p.name: p for p in test_files}
    selected: list[Path] = []
    for raw in selectors:
        if raw not in discovered:
            return None, f"--file selector {raw!r} is not a discovered test file under {_TESTS_DIR}"
        selected.append(discovered[raw])
    return selected, None


def _test_runner_python() -> str:
    """Return the Python executable used for per-file test workers.

    Builds the path via the single resolver (wave 1p7pl); semantics unchanged
    (venv Python when it exists, else the current interpreter).
    """
    venv_python = venv_bootstrap.tool_venv_python()
    return str(venv_python if venv_python.exists() else Path(sys.executable))


def _acquire_run_lock():
    """Acquire the runner lock or return (None, diagnostic) when already held.

    Wave 1p9j0: branch on ``os.name`` so the runner imports and runs on native Windows —
    ``fcntl`` does not exist there. Mirrors dashboard_lib.py's fcntl/msvcrt split: POSIX uses
    ``fcntl.flock``; Windows uses ``msvcrt.locking`` on a SENTINEL byte (``_LOCK_BYTE_OFFSET``)
    so the same-handle pid write/truncate at byte 0 below is not blocked. POSIX mutual-exclusion
    ("already running" busy diagnostic) is preserved unchanged.
    """
    try:
        lock_file = _LOCK_FILE.open("a+", encoding="utf-8")
    except Exception as exc:  # noqa: BLE001
        return None, f"Could not open test runner lock file {_LOCK_FILE}: {exc}"

    busy_msg = f"Another run_tests.py invocation is already running; lock file busy: {_LOCK_FILE}"
    try:
        if os.name == "nt":
            import msvcrt
            lock_file.seek(_LOCK_BYTE_OFFSET)
            acquired = False
            for attempt in range(3):
                try:
                    msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
                    acquired = True
                    break
                except OSError:
                    # Wave 1t72b (1t727): a lock PROBE (indexer deferral check)
                    # holds the lock for microseconds; retry briefly before
                    # concluding another suite run is active.
                    time.sleep(0.1)
            if not acquired:
                lock_file.close()
                return None, busy_msg
        else:
            import fcntl
            acquired = False
            for attempt in range(3):
                try:
                    fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    acquired = True
                    break
                except BlockingIOError:
                    # Wave 1t72b (1t727): see the probe-collision note above.
                    time.sleep(0.1)
            if not acquired:
                lock_file.close()
                return None, busy_msg
    except Exception as exc:  # noqa: BLE001
        lock_file.close()
        return None, f"Could not acquire test runner lock: {exc}"

    try:
        lock_file.seek(0)
        lock_file.truncate()
        lock_file.write(f"{os.getpid()}\n")
        lock_file.flush()
    except Exception:  # noqa: BLE001
        pass

    return lock_file, None


def _release_run_lock(lock_file) -> None:
    """Release the runner lock and close the underlying file handle."""
    try:
        if os.name == "nt":
            import msvcrt
            lock_file.seek(_LOCK_BYTE_OFFSET)  # unlock the SAME sentinel byte we locked
            msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(lock_file, fcntl.LOCK_UN)
    except Exception:  # noqa: BLE001
        pass
    try:
        lock_file.close()
    except Exception:  # noqa: BLE001
        pass


class FileResult(NamedTuple):
    """Outcome of one per-file worker, with telemetry (wave 1tmtx / 1tm6d).

    ``elapsed_s`` is the child-subprocess elapsed time measured around the
    worker invocation; ``skip_count`` is parsed from the unittest result tail
    (``OK (skipped=N)`` / ``FAILED (..., skipped=N)``). Telemetry is advisory:
    it never affects pass/fail or cache authority.
    """

    name: str
    returncode: int
    output: str
    test_count: int
    elapsed_s: float
    skip_count: int


def _run_file(file_path: Path) -> FileResult:
    """Run one test file in a subprocess.

    Returns a FileResult (filename, returncode, combined_output, test_count,
    child elapsed seconds, skipped-test count).
    unittest writes its verbose output to stderr; stdout carries any print()
    calls made by tests themselves.  Both are captured and merged.
    A 600 s per-file timeout prevents a hung test from blocking the whole run;
    timeout is surfaced as a failure rather than propagating.
    """
    env = os.environ.copy()
    env["WAVEFOUNDRY_SUPPRESS_DASHBOARD_BROWSER"] = "1"
    # Wave 1p52p: the test suite is hardware-INDEPENDENT (CI has no GPU, so it must pass on CPU).
    # Force the CPU provider so tests never build/run the real CoreML/CUDA embedder OR cross-encoder
    # reranker — that downloads models, pays the ~20s CoreML compile per process, runs ~0.8s/rerank
    # across the many code_ask integration tests, and (with 6 files in parallel) widens the
    # onnx/protobuf+CoreML abort surface. The GPU accel paths are unit-tested via mocks
    # (make_embedder/make_reranker dispatch); real-GPU parity is an operator-side validation.
    # A test that specifically needs a GPU provider can override this in its own env.
    env.setdefault("WAVEFOUNDRY_EMBED_PROVIDER", "cpu")
    # Wave 1p52p (CPU reranker fallback): with the CPU INT8 reranker, `EMBED_PROVIDER=cpu` would now
    # build a REAL CPU reranker in the integration tests (~960 ms/query → slow suite). The dedicated
    # disable flag turns reranking off entirely for the suite — fast + deterministic. Tests that
    # exercise the reranker mock `_get_reranker`/`make_reranker` directly.
    env.setdefault("WAVEFOUNDRY_DISABLE_RERANKER", "1")
    # Wave 1p9j0 (F13): force UTF-8 in the worker so its output is emitted as UTF-8 regardless of
    # the host locale (native Windows defaults to cp1252), and decode the captured text as UTF-8
    # with an error-tolerant policy — consistent with the timeout branch's replace-decode below.
    # utf8_child_env sets PYTHONUTF8=1 AND PYTHONIOENCODING=utf-8: an inherited
    # PYTHONIOENCODING=cp1252 would otherwise win over PYTHONUTF8 in the child.
    env = subprocess_util.utf8_child_env(env)
    # Wave 1z8ox (1z8ov): ``-B`` below covers only the worker interpreter; the
    # environment variable also reaches every Python child a test spawns, so
    # none of them writes ``__pycache__`` into the repository.
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    start = time.monotonic()
    try:
        result = subprocess.run(
            [_test_runner_python(), "-B", "-m", "unittest", "discover",
             "-s", str(_TESTS_DIR), "-p", file_path.name, "-v"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(_SCRIPT_DIR),
            env=env,
            timeout=_FILE_TIMEOUT_SECONDS,
        )
        output = (result.stdout + result.stderr) if result.stdout else result.stderr
        rc = result.returncode
    except subprocess.TimeoutExpired as exc:
        out = exc.stdout.decode(errors="replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        err = exc.stderr.decode(errors="replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        output = (out + err if out else err) + (
            f"\nTIMEOUT: {file_path.name} exceeded {_FILE_TIMEOUT_SECONDS} s per-file limit.\n"
        )
        rc = 1
    elapsed = time.monotonic() - start
    # Parse counts from unittest's OWN final summary — the LAST anchored
    # "Ran N tests in X.XXXs" match — never from earlier output. Tests that
    # exercise main() print runner-style "Ran N tests across M files" lines to
    # stdout, and a first-unanchored match read those mock lines as the file's
    # count (found 2026-08-27 during 1tm6d: test_run_tests_cache.py reported
    # its mock default 42 instead of its real count, inflating the suite
    # total). Skip counts bind to the same final summary block.
    tail_matches = list(re.finditer(r"Ran (\d+) tests? in [\d.]+s", output))
    if tail_matches:
        count = int(tail_matches[-1].group(1))
        tail = output[tail_matches[-1].end():]
        skip_matches = re.findall(r"\bskipped=(\d+)", tail)
        skipped = int(skip_matches[-1]) if skip_matches else 0
    else:
        count = 0
        skipped = 0
    return FileResult(file_path.name, rc, output, count, elapsed, skipped)


def _schedule_order(test_files: list[Path], durations: dict[str, float], mode: str) -> list[Path]:
    """Deterministic submission order for the worker pool (Requirement 4 of 1tm6d).

    ``timing`` orders longest-first by measured seconds with a stable name
    tiebreak; schedule-control candidates enforce map completeness before
    calling. Every other mode — including the production default until the
    measured schedule winner is recorded — is the existing alphabetical name
    ordering, which is also the fallback when timing data is absent or
    invalid. Ordering is advisory: it never authorizes a skip or a pass.
    """
    if mode == "timing":
        return sorted(test_files, key=lambda p: (-durations.get(p.name, 0.0), p.name))
    return sorted(test_files)


def _execute_files(ordered_files: list[Path]) -> tuple[int, list[FileResult]]:
    """Run the given files through the canonical lock/subprocess/guard path.

    Shared by full, focused, and schedule-control runs. Owns the index-build
    yield loop, the runner lock, bytecode cleanup, the stray-artifact guard,
    per-file telemetry output, and the summary lines. Never touches the
    last-green cache or any timing file — callers own persistence decisions.
    """
    # Wave 1t72b (1t727 TOCTOU repair): check-then-act raced the indexer's
    # mirrored sequence — both sides could see the other's lock free, then
    # acquire their own and run concurrently. Both sides now re-check the
    # other's lock only AFTER acquiring their own (atomic with ownership) and
    # neither waits while holding: the suite releases and re-waits here when a
    # build holds; the build releases its lock before waiting on the suite.
    # Bounded cycles with safe endgames on both sides make ties converge.
    lock_file = None
    for _yield_cycle in range(3):
        build_wait_error = _wait_for_index_build()
        if build_wait_error is not None:
            print(build_wait_error, file=sys.stderr)
            return 1, []
        lock_file, lock_error = _acquire_run_lock()
        if lock_error is not None:
            print(lock_error, file=sys.stderr)
            return 1, []
        held, _holder = _probe_index_build_lock()
        if not held:
            break
        _release_run_lock(lock_file)
        lock_file = None
    if lock_file is None:
        print(
            "run_tests: an index build kept starting during three yield "
            "cycles; refusing to start a contended run. Re-run once builds "
            "settle.",
            file=sys.stderr,
        )
        return 1, []
    # Wave 1t3ek (1t231): snapshot pre-existing stray artifacts so the
    # end-of-run guard flags only what THIS run created.
    preexisting_strays = stray_artifact_paths()
    # Wave 1z8ox (1z8ov): snapshot tracked and non-ignored files plus the
    # edit-gate file, after the lock, so the end-of-run guard can name any
    # repository path the run created, modified or deleted.
    repo_before = repo_state_snapshot()
    if repo_before is None:
        print(
            f"run_tests: {_REPO_ROOT} could not be snapshotted "
            f"({_repo_state_unavailable_reason or 'not a git checkout, or git is unavailable'}); "
            "the repository-state guard is skipped for this run.",
            flush=True,
        )

    try:
        # Remove stale bytecode before spawning workers.
        _clean_pycache()

        # Cap at 6: many test files spawn subprocesses; beyond 6 concurrent workers
        # the system gets CPU/IO-saturated and individual file times balloon.
        workers = min(len(ordered_files), min(os.cpu_count() or 4, 6))

        wall_start = time.monotonic()
        file_results: list[FileResult] = []

        print(f"Running {len(ordered_files)} test files across {workers} workers …", flush=True)

        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {executor.submit(_run_file, f): f for f in ordered_files}
            done_count = 0
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                done_count += 1
                status = "ok" if result.returncode == 0 else "FAIL"
                print(
                    f"  [{done_count}/{len(ordered_files)}] {result.name} — "
                    f"{result.test_count} tests {status} ({result.elapsed_s:.1f}s)",
                    flush=True,
                )
                file_results.append(result)

        wall_elapsed = time.monotonic() - wall_start

        # Print each file's full output in stable filename order.
        file_results.sort(key=lambda r: r.name)
        failed_files: list[str] = []
        total_tests = 0

        for res in file_results:
            total_tests += res.test_count
            if res.returncode != 0:
                failed_files.append(res.name)
                print(f"\n{'=' * 70}")
                print(f"FAILED: {res.name}")
                print("=" * 70)
                print(res.output, end="")

        print(f"\n{'-' * 70}")
        # Telemetry summary (wave 1tmtx): advisory measurement only — never
        # affects pass/fail, cache authority, or the lines below it.
        slowest = sorted(file_results, key=lambda r: r.elapsed_s, reverse=True)[:10]
        print(f"Slowest files (top {len(slowest)} of {len(file_results)}):")
        for res in slowest:
            print(f"  {res.name:<44} {res.elapsed_s:9.3f}s  ({res.test_count} tests)")
        service_time = sum(r.elapsed_s for r in file_results)
        total_skipped = sum(r.skip_count for r in file_results)
        print(
            f"Worker service time: {service_time:.3f}s across "
            f"{len(file_results)} files; skipped {total_skipped} tests"
        )
        # Evaluated before the failed-files branch so a failing run still
        # names any repository path it changed (wave 1z8ox, 1z8ov).
        stray_failure = _stray_artifact_failure(preexisting_strays, repo_before)
        if failed_files:
            if stray_failure is not None:
                print(f"\n{stray_failure}", file=sys.stderr)
            print(f"FAILED ({', '.join(failed_files)})")
            print(f"Ran {total_tests} tests across {len(ordered_files)} files in {wall_elapsed:.3f}s")
            _clean_pycache()
            return 1, file_results

        if stray_failure is not None:
            print(f"\n{stray_failure}", file=sys.stderr)
            print(f"Ran {total_tests} tests across {len(ordered_files)} files in {wall_elapsed:.3f}s")
            print("FAILED (stray test artifacts or repository changes)")
            _clean_pycache()
            return 1, file_results

        print(f"Ran {total_tests} tests across {len(ordered_files)} files in {wall_elapsed:.3f}s")
        print("OK")
        _clean_pycache()
        return 0, file_results
    finally:
        _release_run_lock(lock_file)


def _run_schedule_control(mode: str, timings_file: str, test_files: list[Path]) -> int:
    """Benchmark-only schedule-control runs (Requirement 4 of 1tm6d).

    ``bootstrap`` executes alphabetically and, only after a fully green,
    artifact-clean run, atomically writes the digest-bound timing manifest.
    ``alphabetical`` and ``timing`` validate and read that manifest, execute
    their candidate order, and modify nothing. No mode reads or writes the
    production last-green cache; the manifest cannot authorize a skip.
    """
    source_digest = _hash_inputs()
    durations: dict[str, float] = {}
    if mode in ("alphabetical", "timing"):
        read, error = _read_timings_manifest(timings_file, source_digest, test_files)
        if error is not None:
            print(f"run_tests: {error}", file=sys.stderr)
            return 2
        durations = read or {}
    order = _schedule_order(test_files, durations, "timing" if mode == "timing" else "alphabetical")
    print(
        f"SCHEDULE CONTROL ({mode}) — benchmark-only run; production cache untouched.",
        flush=True,
    )
    rc, results = _execute_files(order)
    if mode == "bootstrap":
        if rc != 0:
            print(
                "run_tests: bootstrap run was not green; no timing manifest written.",
                file=sys.stderr,
            )
            return rc
        error = _write_timings_manifest(timings_file, source_digest, results)
        if error is not None:
            print(f"run_tests: {error}", file=sys.stderr)
            return 1
        print(f"Timing manifest written: {timings_file}", flush=True)
    return rc


# Change 1zim1 (wave 1zim5): the second-profile run. The copy's own runner is
# launched as a focused run, so the copy never writes a receipt, and this
# tree's receipt is checked byte-for-byte before and after.
_PROFILE_GIT_TIMEOUT_SECONDS = 300
_PROFILE_NOT_EVIDENCE = (
    "SECOND-PROFILE run ({name}): not delivery evidence; this tree's framework "
    "test receipt is never written."
)
# The copy's per-file progress line: ``  [3/146] test_x.py <dash> 12 tests FAIL (1.2s)``.
_PROFILE_PROGRESS_RE = re.compile(r"^\s*\[\d+/\d+\] (test_\S+\.py) \S+ (\d+) tests? (ok|FAIL) \(", re.M)
_PROFILE_FAILED_HEADER_RE = re.compile(r"^={70}\nFAILED: (test_\S+\.py)\n={70}\n", re.M)
_PROFILE_SUMMARY_RE = re.compile(r"^FAILED \(([^)]*)\)\s*$", re.M)
_PROFILE_CLOSING_RE = re.compile(r"^-{70}\nSlowest files \(top", re.M)


def _git_env() -> dict:
    """The environment for git in the temporary repository: no inherited
    repository selection (a hook's ``GIT_DIR``), no system configuration."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env["GIT_CONFIG_NOSYSTEM"] = "1"
    return env


def _beneath_copied_symlink(dest: Path, dst: Path) -> bool:
    """Whether a directory between ``dest`` and ``dst`` is a symlink in the copy."""
    current = dest
    for part in dst.relative_to(dest).parts[:-1]:
        current = current / part
        if os.path.islink(current):
            return True
        if not os.path.lexists(current):
            return False
    return False


def _copy_listed_tree(source: Path, dest: Path) -> "tuple[int, str | None]":
    """Copy ``git ls-files -co --exclude-standard`` of ``source`` into ``dest``.

    Returns (files copied, error). A listed path that is gone from disk (a
    tracked deletion) is skipped; a symlink is copied as a symlink, or as its
    target's content where symlinks cannot be created. The profile's writes
    into the copy replace a symlinked file instead of following it and refuse
    a directory that resolves outside the copy, so a kept symlink never
    carries a write out of the temporary repository."""
    import shutil
    try:
        listing = _run_tree_kill(
            ["git", "-C", str(source), "ls-files", "-z", "-co", "--exclude-standard"],
            capture_output=True, timeout=_PROFILE_GIT_TIMEOUT_SECONDS, env=_git_env(),
        )
    except Exception as exc:  # noqa: BLE001
        return 0, f"git ls-files failed: {exc}"
    if listing.returncode != 0:
        detail = listing.stderr.decode("utf-8", "replace") if isinstance(listing.stderr, bytes) else listing.stderr
        return 0, f"git ls-files failed: {(detail or '').strip()}"
    raw = listing.stdout if isinstance(listing.stdout, bytes) else listing.stdout.encode("utf-8")
    copied = 0
    for rel in sorted({p for p in raw.decode("utf-8", "surrogateescape").split("\0") if p}):
        src = source / rel
        dst = dest / rel
        if not os.path.lexists(src) or (src.is_dir() and not src.is_symlink()):
            continue
        if _beneath_copied_symlink(dest, dst):
            # A listed file under a directory the copy already holds as a
            # symlink (a tracked directory replaced on disk by a link): the
            # link carries what the working tree shows, and writing through
            # it could land outside the temporary repository.
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.is_symlink():
            try:
                os.symlink(os.readlink(src), dst)
                copied += 1
                continue
            except OSError:
                if not src.exists():
                    continue
        shutil.copy2(src, dst)
        copied += 1
    return copied, None


def _profile_run_report(output: str) -> "list[dict]":
    """Per-file results parsed from the copy's focused-run output: name,
    status, tests, failures and errors (``None`` when the file has no unittest
    summary, for example a timeout), sorted by failures plus errors, then name.

    The progress lines are read only before the first failure block and each
    block only up to the runner's closing summary, so test output that quotes
    runner-style lines is never counted."""
    closing = list(_PROFILE_CLOSING_RE.finditer(output))
    body = output[:closing[-1].start()] if closing else output
    headers = list(_PROFILE_FAILED_HEADER_RE.finditer(body))
    progress = body[:headers[0].start()] if headers else body
    rows: dict[str, dict] = {}
    for match in _PROFILE_PROGRESS_RE.finditer(progress):
        rows[match.group(1)] = {"name": match.group(1), "tests": int(match.group(2)),
                                "status": match.group(3), "failures": 0, "errors": 0}
    seen: set[str] = set()
    for index, header in enumerate(headers):
        name = header.group(1)
        row = rows.get(name)
        if row is None or row["status"] != "FAIL" or name in seen:
            continue
        seen.add(name)
        end = headers[index + 1].start() if index + 1 < len(headers) else len(body)
        summaries = _PROFILE_SUMMARY_RE.findall(body[header.end():end])
        if not summaries:
            row["failures"] = row["errors"] = None
            continue
        counts = dict(re.findall(r"(\w+)=(\d+)", summaries[-1]))
        row["failures"] = int(counts.get("failures", 0))
        row["errors"] = int(counts.get("errors", 0))
    return sorted(rows.values(), key=lambda r: (-((r["failures"] or 0) + (r["errors"] or 0)), r["name"]))


def _print_profile_report(name: str, rows: "list[dict]", expected: str = "") -> None:
    """The per-file result. ``expected`` names the expected profile the
    copy's guards check, with each layer's source (change 1zima)."""
    failing = [r for r in rows if r["status"] != "ok"]
    print(f"\n{'-' * 70}")
    where = f"; expected profile: {expected}" if expected else ""
    print(f"Second-profile per-file result (profile {name!r}{where}): "
          f"{len(failing)} of {len(rows)} files failed")
    for row in failing:
        counts = ("no unittest summary" if row["failures"] is None
                  else f"failures={row['failures']} errors={row['errors']}")
        print(f"  {row['name']:<52} {row['tests']:>5} tests  {counts}")
    total = sum((r["failures"] or 0) + (r["errors"] or 0) for r in failing)
    print(f"Total failures and errors: {total} in {len(failing)} files; "
          f"{len(rows) - len(failing)} files passed")


def _remove_work_tree(path: Path) -> None:
    """Remove the run's temporary tree, read-only entries included.

    Git writes its object files read-only, and on Windows ``rmtree`` cannot
    delete a read-only file, so a plain ``ignore_errors`` removal would leave
    the whole copy behind. The retry clears the read-only bit on the entry and
    makes its parent writable (a read-only directory blocks deleting its
    entries on POSIX), the pattern ``setup_index`` uses for the venv."""
    import shutil
    import stat

    def _clear_readonly_and_retry(func, entry, _exc):
        try:
            os.chmod(os.path.dirname(entry) or ".", stat.S_IRWXU)
            os.chmod(entry, stat.S_IWRITE | stat.S_IREAD | (stat.S_IXUSR if os.path.isdir(entry) else 0))
            func(entry)
        except OSError:
            pass

    kwargs = ({"onexc": _clear_readonly_and_retry} if sys.version_info >= (3, 12)
              else {"onerror": _clear_readonly_and_retry})
    if os.path.lexists(path):
        shutil.rmtree(path, **kwargs)


def _child_runner_env(profile_env: "dict[str, str] | None" = None) -> dict:
    """The copy's runner environment: UTF-8, no bytecode, and no inherited
    ``GIT_*`` repository selection, so its tests read the temporary repository.
    ``profile_env`` names the run-mode profile (change 1zima:
    ``WAVEFOUNDRY_TEST_PROFILE``), so the copy's guards expect the profile
    the run applied."""
    env = subprocess_util.utf8_child_env({k: v for k, v in os.environ.items() if not k.startswith("GIT_")})
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env.update(profile_env or {})
    return env


def _install_sigterm_as_interrupt():
    """Make SIGTERM raise ``KeyboardInterrupt`` so the run's cleanup runs;
    returns the previous handler, or ``None`` when not installed (Windows, or
    not the main thread)."""
    import signal
    import threading

    if os.name == "nt" or not hasattr(signal, "SIGTERM") or threading.current_thread() is not threading.main_thread():
        return None

    def _interrupt(_signum, _frame):
        raise KeyboardInterrupt

    return signal.signal(signal.SIGTERM, _interrupt)


def _restore_sigterm(previous) -> None:
    if previous is not None:
        import signal
        signal.signal(signal.SIGTERM, previous)


def _profile_run_in(work: Path, name: str, profile: dict, profiles, scripts_rel: Path,
                    selectors: "list[str]", state: dict) -> "tuple[int, str, bool]":
    """Copy, apply, commit and run inside ``work``: (rc, output, ran). The
    child process is kept in ``state['proc']`` so the caller can end it."""
    repo = work / "repo"
    repo.mkdir()
    copied, error = _copy_listed_tree(_REPO_ROOT, repo)
    if error is not None:
        print(f"run_tests: {error}", file=sys.stderr)
        return 1, "", False
    scripts = repo / scripts_rel
    copied_tests = sorted((scripts / "tests").glob("test_*.py"))
    names = [p.name for p in copied_tests]
    if selectors:
        selected, error = _validate_focus_selectors(selectors, copied_tests)
        if error is not None:
            print(f"run_tests: {error}", file=sys.stderr)
            return 2, "", False
        names = [p.name for p in selected]
    try:
        loaded = profiles.apply_profile(scripts, profile, repo_root=repo, python=_test_runner_python())
    except profiles.ProfileInvalid as exc:
        print(f"run_tests: profile {name!r} does not apply: {exc}", file=sys.stderr)
        return 1, "", False
    try:
        readme = profiles.write_waves_readme(
            repo, vocabulary=loaded["vocabulary_profile"], layout=loaded["record_paths"])
    except profiles.ProfileInvalid as exc:
        print(f"run_tests: profile {name!r} does not apply: {exc}", file=sys.stderr)
        return 1, "", False
    # No background gc or maintenance: it could outlive the run and hold the tree.
    git = ["git", "-C", str(repo), "-c", "user.name=wf-profile-run",
           "-c", "user.email=wf-profile-run@localhost", "-c", "commit.gpgsign=false",
           "-c", "gc.auto=0", "-c", "maintenance.auto=false"]
    for args in (["init", "-q"], ["add", "-A"],
                 ["commit", "-q", "--no-verify", "-m", f"Second-profile run ({name})"]):
        done = _run_tree_kill(git + args, capture_output=True, text=True,
                              timeout=_PROFILE_GIT_TIMEOUT_SECONDS, env=_git_env())
        if done.returncode != 0:
            print(f"run_tests: git {args[0]} failed in the temporary repository: "
                  f"{(done.stderr or '').strip()}", file=sys.stderr)
            return 1, "", False
    print(
        f"Copied {copied} files into a temporary git repository; applied profile {name!r}; "
        f"waves root {loaded['record_paths']['WAVES_ROOT']} (README {readme.relative_to(repo).as_posix()}).",
        flush=True,
    )
    cmd = [_test_runner_python(), "-B", str(scripts / "run_tests.py")]
    for test_name in names:
        cmd += ["--file", test_name]
    # Its own process group, so the cleanup can end the runner and its workers together.
    group = ({"creationflags": int(getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0))}
             if os.name == "nt" else {"start_new_session": True})
    proc = subprocess.Popen(cmd, cwd=str(repo), env=_child_runner_env({profiles.TEST_PROFILE_ENV: name}),
                            stdin=subprocess.DEVNULL,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, encoding="utf-8", errors="replace", **group)
    state["proc"] = proc
    lines: list[str] = []
    assert proc.stdout is not None
    for line in proc.stdout:
        sys.stdout.write(line)
        sys.stdout.flush()
        lines.append(line)
    return proc.wait(), "".join(lines), True


def _run_profile(name: str, selectors: "list[str]") -> int:
    """The second-profile run (change 1zim1, Requirement 4)."""
    import tempfile
    # The runner is test infrastructure, so it may use the test support's
    # profile helpers; production code never imports them.
    from tests import record_layout_support as profiles

    error = _selector_format_error(selectors)
    if error is not None:
        print(f"run_tests: {error}", file=sys.stderr)
        return 2
    try:
        profile = profiles.load_profile(name)
        # What the copy's guards will expect (change 1zima): the base (the
        # active asset, else the shipped defaults) with this profile over it.
        expected = profiles.expected_profile({profiles.TEST_PROFILE_ENV: name}).describe()
    except profiles.ProfileInvalid as exc:
        print(f"run_tests: {exc}", file=sys.stderr)
        return 2
    try:
        scripts_rel = _SCRIPT_DIR.relative_to(_REPO_ROOT)
    except ValueError:
        print(f"run_tests: {_SCRIPT_DIR} is not inside {_REPO_ROOT}", file=sys.stderr)
        return 2
    receipt_before = _CACHE_FILE.read_bytes() if _CACHE_FILE.exists() else None
    print(_PROFILE_NOT_EVIDENCE.format(name=name), flush=True)
    print(f"Expected profile: {expected}.", flush=True)
    work = Path(tempfile.mkdtemp(prefix="wf-profile-run-"))
    state: dict = {"proc": None}
    previous = _install_sigterm_as_interrupt()
    rc, output, ran = 1, "", False
    try:
        rc, output, ran = _profile_run_in(work, name, profile, profiles, scripts_rel, selectors, state)
    finally:
        proc = state["proc"]
        try:
            if proc is not None and proc.returncode is None:
                # Interrupted while the copy's runner was going: end its group, then reap it.
                subprocess_util._kill_process_tree(proc)
                proc.wait()
        finally:
            _remove_work_tree(work)
            _restore_sigterm(previous)
    receipt_after = _CACHE_FILE.read_bytes() if _CACHE_FILE.exists() else None
    if receipt_after != receipt_before:
        print(f"run_tests: {_CACHE_FILE} changed during the second-profile run", file=sys.stderr)
        rc = 1
    if ran:
        _print_profile_report(name, _profile_run_report(output), expected)
        print(_PROFILE_NOT_EVIDENCE.format(name=name))
    return rc


def _profile_support():
    """The test support's profile helpers (test infrastructure, like this runner)."""
    if str(_SCRIPT_DIR) not in sys.path:
        sys.path.insert(0, str(_SCRIPT_DIR))
    from tests import record_layout_support
    return record_layout_support


def _stray_profile_refusal(environ=None) -> "str | None":
    """The refusal message when ``WAVEFOUNDRY_TEST_PROFILE`` is set for a run
    that can write the receipt, else ``None``. The variable is read through
    the test support's one reader."""
    profiles = _profile_support()
    name = profiles.run_mode_profile_name(environ)
    if name is None:
        return None
    return (f"run_tests: {profiles.TEST_PROFILE_ENV} is set ({name!r}); a full run writes the framework test "
            f"receipt, so it does not run under a run-mode profile. Unset {profiles.TEST_PROFILE_ENV}, or use "
            "--profile NAME (or --file NAME for a focused run).")


def main() -> int:
    # Strict mode validation first (Requirement 9 of 1tm6d): every flag is
    # parsed and validated before any input hashing, cache, or timing read.
    try:
        opts = _parse_args(sys.argv)
    except _UsageError as exc:
        print(f"run_tests: {exc}", file=sys.stderr)
        return 2

    if opts["help"]:
        print(_USAGE, end="")
        return 0

    if opts["profile"] is not None:
        return _run_profile(opts["profile"], opts["files"])

    if not opts["files"] and opts["schedule_control"] is None:
        # A run that can write the receipt (change 1zima, Requirement 10):
        # refused before anything is hashed, read or run while a run-mode
        # profile is named, so a stray variable never yields a green receipt.
        refusal = _stray_profile_refusal()
        if refusal is not None:
            print(refusal, file=sys.stderr)
            return 2

    test_files = sorted(_TESTS_DIR.glob("test_*.py"))

    if opts["files"]:
        selected, error = _validate_focus_selectors(opts["files"], test_files)
        if error is not None:
            print(f"run_tests: {error}", file=sys.stderr)
            return 2
        # Focused diagnostic run (Requirements 8/9 of 1tm6d): same lock,
        # subprocess, environment, timeout, and artifact-guard path as a full
        # run, but no hash/cache/timing seam is ever reached and nothing is
        # persisted — focused output is never delivery evidence.
        print(
            f"FOCUSED diagnostic run ({len(selected)} of {len(test_files)} test files) — "
            "not delivery evidence; the full-suite cache is untouched.",
            flush=True,
        )
        rc, _results = _execute_files(selected)
        return rc

    if opts["schedule_control"] is not None:
        return _run_schedule_control(opts["schedule_control"], opts["timings_file"], test_files)

    # Ordinary complete run. Compute the hash once — before any test execution —
    # so the cache entry always reflects the state that caused the run, not
    # post-run file changes.
    inputs_hash = _hash_inputs()

    # One cache read per ordinary run (Requirement 3 of 1tm6d). Only a matching
    # inputs_hash with result "ok" authorizes a skip. The advisory durations_s
    # map is validated independently and survives a hash mismatch and
    # --no-cache as scheduling input — never as skip or pass authority.
    cache = _read_cache()
    if not opts["no_cache"] and cache is not None:
        hit = _cache_hit(inputs_hash, cache)
        if hit:
            ts = hit.get("ran_at", "")[:19].replace("T", " ")
            print(
                f"Tests current — {hit.get('test_count', '?')} passed"
                + (f" at {ts} UTC" if ts else "")
                + ". Run with --no-cache to force."
            )
            return 0
    durations = _validated_durations(cache, test_files)

    # Production order: alphabetical until the measured schedule winner is
    # recorded by the counterbalanced control comparison (Requirement 4).
    order = _schedule_order(test_files, durations, "alphabetical")
    rc, results = _execute_files(order)
    if rc == 0:
        _write_cache(
            inputs_hash,
            sum(r.test_count for r in results),
            {r.name: r.elapsed_s for r in results},
        )
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
