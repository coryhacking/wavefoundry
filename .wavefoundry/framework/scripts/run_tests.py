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


def _stray_artifact_failure(preexisting: list[str]) -> str | None:
    """Return a failure message when the run created new stray artifacts."""
    created = [p for p in stray_artifact_paths() if p not in preexisting]
    if not created:
        return None
    return (
        "STRAY TEST ARTIFACTS: a test wrote durable state relative to cwd "
        "instead of its fixture root:\n  "
        + "\n  ".join(created)
        + "\nFix the offending test (see the 1t231 pattern: unmocked "
        "cwd-relative write paths) and delete the artifacts."
    )


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
    opts: dict = {"no_cache": False, "files": [], "schedule_control": None, "timings_file": None}
    args = argv[1:]
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--no-cache":
            opts["no_cache"] = True
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


def _validate_focus_selectors(selectors: list[str],
                              test_files: list[Path]) -> tuple[list[Path] | None, str | None]:
    """Validate ``--file`` selectors against the discovered direct-child set.

    Selectors are exact discovered ``test_*.py`` basenames. Duplicates,
    path-like values, non-test names, and absent files fail deterministically
    (Requirement 9 of 1tm6d). Validation runs before any hashing, cache, or
    timing-map access — focused runs never reach those seams at all.
    """
    discovered = {p.name: p for p in test_files}
    seen: set[str] = set()
    selected: list[Path] = []
    for raw in selectors:
        if raw in seen:
            return None, f"duplicate --file selector {raw!r}"
        seen.add(raw)
        if not raw or "/" in raw or "\\" in raw or Path(raw).is_absolute() or Path(raw).name != raw:
            return None, f"--file takes an exact test file basename, not a path: {raw!r}"
        if not (raw.startswith("test_") and raw.endswith(".py")):
            return None, f"--file selector {raw!r} is not a test_*.py basename"
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
        if failed_files:
            print(f"FAILED ({', '.join(failed_files)})")
            print(f"Ran {total_tests} tests across {len(ordered_files)} files in {wall_elapsed:.3f}s")
            _clean_pycache()
            return 1, file_results

        stray_failure = _stray_artifact_failure(preexisting_strays)
        if stray_failure is not None:
            print(f"\n{stray_failure}", file=sys.stderr)
            print(f"Ran {total_tests} tests across {len(ordered_files)} files in {wall_elapsed:.3f}s")
            print("FAILED (stray test artifacts)")
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


def main() -> int:
    # Strict mode validation first (Requirement 9 of 1tm6d): every flag is
    # parsed and validated before any input hashing, cache, or timing read.
    try:
        opts = _parse_args(sys.argv)
    except _UsageError as exc:
        print(f"run_tests: {exc}", file=sys.stderr)
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
