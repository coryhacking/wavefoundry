"""Tests for upgrade_wavefoundry.py — _compute_seed_diffs (12r1b) and extension hooks (12r1y)."""
from __future__ import annotations

import contextlib
import datetime
import hashlib
import importlib.util
import io
import json
import multiprocessing
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import types
import unittest
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch


SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
UPGRADE_PATH = SCRIPTS_ROOT / "upgrade_wavefoundry.py"
REVIEW_PROTOCOL_SEEDS = (
    "209-agent-harness-core.prompt.md",
    "221-code-reviewer.prompt.md",
    "239-qa-reviewer.prompt.md",
)


def _stage_review_protocol_seeds(root: Path) -> Path:
    target_seeds = root / ".wavefoundry" / "framework" / "seeds"
    target_seeds.mkdir(parents=True, exist_ok=True)
    for name in REVIEW_PROTOCOL_SEEDS:
        target_seeds.joinpath(name).write_bytes(
            (SCRIPTS_ROOT.parent / "seeds" / name).read_bytes()
        )
    shutil.copytree(
        SCRIPTS_ROOT.parent / "install" / "lifecycle-prompts",
        root
        / ".wavefoundry"
        / "framework"
        / "install"
        / "lifecycle-prompts",
        dirs_exist_ok=True,
    )
    return target_seeds


def _assert_review_protocol_contract(test: unittest.TestCase, root: Path) -> None:
    target_seeds = root / ".wavefoundry" / "framework" / "seeds"
    canonical_text = target_seeds.joinpath(
        "209-agent-harness-core.prompt.md"
    ).read_text(encoding="utf-8")
    test.assertIn(
        "Independent-reference verification",
        canonical_text,
    )
    test.assertIn(
        "Implementer-authored evidence remains `independent: false`",
        canonical_text,
    )
    for name in REVIEW_PROTOCOL_SEEDS:
        test.assertEqual(
            target_seeds.joinpath(name).read_bytes(),
            (SCRIPTS_ROOT.parent / "seeds" / name).read_bytes(),
        )
    for rel in ("docs/agents/code-reviewer.md", "docs/agents/qa-reviewer.md"):
        role_text = (root / rel).read_text(encoding="utf-8")
        test.assertIn("Independent-reference verification", role_text)
        test.assertIn("`independent: false`", role_text)
    test.assertIn(
        "assertion that would falsify",
        (root / "docs" / "agents" / "qa-reviewer.md").read_text(encoding="utf-8"),
    )
    # Wave 1tmb2: staged seeds and rendered carriers carry the chain-aware
    # independence contract (enforced-versus-declared split); the pre-1tmb2
    # carrier revision without it must not survive.
    test.assertIn("Enforced versus declared independence", canonical_text)
    test.assertIn("`reverification_context_not_fresh`", canonical_text)
    test.assertIn("`reverification_actor_not_distinct`", canonical_text)
    test.assertIn("`review_evidence_independence_invalid`", canonical_text)
    qa_seed_text = target_seeds.joinpath("239-qa-reviewer.prompt.md").read_text(
        encoding="utf-8"
    )
    test.assertIn("`reverification_actor_not_distinct`", qa_seed_text)
    test.assertIn("without claiming caller identity", qa_seed_text)
    for rel in ("docs/agents/qa-reviewer.md", "docs/contributing/review-and-evals.md"):
        carrier_text = (root / rel).read_text(encoding="utf-8")
        test.assertIn("`reverification_context_not_fresh`", carrier_text)
        test.assertIn("`reverification_actor_not_distinct`", carrier_text)
        test.assertIn("not caller", carrier_text)
    test.assertIn(
        "must not reverify its own",
        (root / "docs" / "agents" / "qa-reviewer.md").read_text(encoding="utf-8"),
    )
    for name in ("review-wave.prompt.md", "close-wave.prompt.md"):
        test.assertIn(
            "memory_validate",
            (root / "docs" / "prompts" / name).read_text(encoding="utf-8"),
            f"{name} must carry the agent-validation memory checkpoint",
        )


def load_upgrade_module():
    spec = importlib.util.spec_from_file_location("upgrade_wavefoundry", UPGRADE_PATH)
    mod = importlib.util.module_from_spec(spec)
    # upgrade_wavefoundry imports upgrade_lib and check_version at call time;
    # those imports are deferred inside functions so loading the module is safe.
    sys.modules["upgrade_wavefoundry"] = mod
    spec.loader.exec_module(mod)
    return mod


def _sidecar_cleanup_worker(
    root: str,
    rendezvous_dir: str,
    from_version: str | None,
    outcomes: object,
) -> None:
    """Run the REAL sidecar cleanup with a rendezvous pause inside the deletion window.

    Wave 1to78 AC-2: the concurrency in this control is real — two spawned OS
    processes contend on the real lock carriers, and every acquire, unlink, and
    release is the production code path. The only instrumentation is a
    rendezvous wrapper around ``_retired_sidecar_path_error`` (a pure path
    guard) that pauses the cleanup inside its deletion window long enough for
    the peer process to start a blocking acquire; it then delegates to the real
    guard. Under the retired probe-then-release-then-unlink shape this pause
    sits in the unprotected window and the peer observes partial deletion, so
    the control fails (mutation-proven); under hold-through-deletion the peer
    stays blocked until every deletion, including the last root-lock unlink,
    is complete.
    """
    mod = load_upgrade_module()
    inside = Path(rendezvous_dir) / "inside-deletion-window.marker"
    acquirer_started = Path(rendezvous_dir) / "acquirer-started.marker"
    real_guard = mod._retired_sidecar_path_error
    state = {"paused": False}

    def pausing_guard(guard_root, candidate):
        if not state["paused"]:
            state["paused"] = True
            inside.write_text("inside", encoding="utf-8")
            deadline = time.monotonic() + 15
            while not acquirer_started.exists() and time.monotonic() < deadline:
                time.sleep(0.01)
            # Grace so the peer's blocking acquire is actually in flight.
            time.sleep(0.5)
        return real_guard(guard_root, candidate)

    mod._retired_sidecar_path_error = pausing_guard
    try:
        counts = mod.phase_review_evidence_sidecar_cleanup(
            Path(root), from_version=from_version
        )
        outcomes.put(("cleanup", counts))
    except SystemExit as exc:
        outcomes.put(("cleanup_refused", str(exc)))


def _blocking_acquirer_worker(
    root: str,
    rendezvous_dir: str,
    outcomes: object,
) -> None:
    """Blocking-acquire the current publication lock during the deletion window.

    Records the sidecar/root-lock filesystem state observed at the moment the
    blocking acquire returns. Hold-through-deletion guarantees that moment is
    after every deletion has finished; any observed partial state is an
    interleaving.
    """
    if str(SCRIPTS_ROOT) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_ROOT))
    import review_evidence
    from runtime_lock import RuntimeFileLock

    root_path = Path(root)
    inside = Path(rendezvous_dir) / "inside-deletion-window.marker"
    acquirer_started = Path(rendezvous_dir) / "acquirer-started.marker"
    deadline = time.monotonic() + 15
    while not inside.exists() and time.monotonic() < deadline:
        time.sleep(0.01)
    if not inside.exists():
        outcomes.put(("acquirer_timeout", None))
        return
    acquirer_started.write_text("started", encoding="utf-8")
    lock = RuntimeFileLock(
        root_path / review_evidence.PROJECT_STATE_PUBLICATION_LOCK_REL,
        blocking=True,
    )
    lock.acquire()
    try:
        waves = root_path / "docs" / "waves"
        observed = {
            "adoptions": (waves / "review-evidence-adoptions.json").exists(),
            "migration": (waves / "review-evidence-migration.json").exists(),
            "root_lock": (
                root_path / ".wavefoundry" / "review-evidence-adoptions.lock"
            ).exists(),
        }
    finally:
        lock.release()
    outcomes.put(("acquirer", observed))


def _make_zip(entries: dict[str, str], prefix: str = ".wavefoundry/framework/seeds/") -> bytes:
    """Build an in-memory zip with seeds at *prefix*."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, content in entries.items():
            zf.writestr(prefix + name, content)
    return buf.getvalue()


class ComputeSeedDiffsTests(unittest.TestCase):
    """Unit tests for _compute_seed_diffs (AC-1 through AC-6)."""

    def setUp(self):
        self.mod = load_upgrade_module()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.seeds_dir = self.root / ".wavefoundry" / "framework" / "seeds"
        self.seeds_dir.mkdir(parents=True)

    def tearDown(self):
        self.tmp.cleanup()

    def _write_disk_seed(self, name: str, content: str) -> None:
        (self.seeds_dir / name).write_text(content, encoding="utf-8")

    def _make_zip_file(self, entries: dict[str, str], prefix: str = ".wavefoundry/framework/seeds/") -> Path:
        zip_path = self.root / "wavefoundry-test.zip"
        zip_path.write_bytes(_make_zip(entries, prefix=prefix))
        return zip_path

    # ── AC-3: unchanged seeds are omitted ─────────────────────────────────────

    def test_unchanged_seed_not_in_results(self):
        content = "# Seed\n\nNo change here.\n"
        self._write_disk_seed("seed-001.md", content)
        zip_path = self._make_zip_file({"seed-001.md": content})

        results = self.mod._compute_seed_diffs(self.root, zip_path)
        self.assertEqual(results, [])

    # ── AC-2: modified seed appears with unified diff ─────────────────────────

    def test_modified_seed_returns_diff(self):
        self._write_disk_seed("seed-010.md", "# Old\n\nOriginal content.\n")
        zip_path = self._make_zip_file({"seed-010.md": "# New\n\nUpdated content.\n"})

        results = self.mod._compute_seed_diffs(self.root, zip_path)
        self.assertEqual(len(results), 1)
        filename, status, diff = results[0]
        self.assertEqual(filename, "seed-010.md")
        self.assertEqual(status, "modified")
        self.assertIn("--- a/seed-010.md", diff)
        self.assertIn("+++ b/seed-010.md", diff)
        self.assertIn("-Original content.", diff)
        self.assertIn("+Updated content.", diff)

    # ── AC-4: added seed is labeled correctly ─────────────────────────────────

    def test_added_seed_status_is_added(self):
        # Not present on disk — only in zip
        zip_path = self._make_zip_file({"seed-new.md": "# Brand new seed\n"})

        results = self.mod._compute_seed_diffs(self.root, zip_path)
        self.assertEqual(len(results), 1)
        filename, status, diff = results[0]
        self.assertEqual(filename, "seed-new.md")
        self.assertEqual(status, "added")
        self.assertIn("/dev/null", diff)
        self.assertIn("+++ b/seed-new.md", diff)

    # ── AC-4: removed seed is labeled correctly ───────────────────────────────

    def test_removed_seed_status_is_removed(self):
        # Present on disk — absent in zip
        self._write_disk_seed("seed-old.md", "# Old seed to be removed\n")
        zip_path = self._make_zip_file({})  # empty zip

        results = self.mod._compute_seed_diffs(self.root, zip_path)
        self.assertEqual(len(results), 1)
        filename, status, diff = results[0]
        self.assertEqual(filename, "seed-old.md")
        self.assertEqual(status, "removed")
        self.assertIn("--- a/seed-old.md", diff)
        self.assertIn("/dev/null", diff)

    # ── AC-6: bad zip does not crash ──────────────────────────────────────────

    def test_bad_zip_returns_empty_list(self):
        bad_zip = self.root / "bad.zip"
        bad_zip.write_bytes(b"not a zip file")

        results = self.mod._compute_seed_diffs(self.root, bad_zip)
        self.assertEqual(results, [])

    # ── Alt zip prefix (framework/seeds/) ────────────────────────────────────

    def test_alt_zip_prefix_is_recognised(self):
        self._write_disk_seed("seed-010.md", "# Old\n")
        zip_path = self._make_zip_file(
            {"seed-010.md": "# New\n"}, prefix="framework/seeds/"
        )

        results = self.mod._compute_seed_diffs(self.root, zip_path)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0][0], "seed-010.md")
        self.assertEqual(results[0][1], "modified")

    # ── Multiple seeds — mixed statuses ──────────────────────────────────────

    def test_multiple_seeds_mixed_statuses(self):
        self._write_disk_seed("seed-001.md", "unchanged\n")
        self._write_disk_seed("seed-002.md", "old content\n")
        self._write_disk_seed("seed-003.md", "to be removed\n")
        zip_path = self._make_zip_file({
            "seed-001.md": "unchanged\n",       # no change
            "seed-002.md": "new content\n",     # modified
            "seed-004.md": "brand new\n",       # added
            # seed-003.md absent → removed
        })

        results = self.mod._compute_seed_diffs(self.root, zip_path)
        statuses = {name: status for name, status, _ in results}
        self.assertNotIn("seed-001.md", statuses)
        self.assertEqual(statuses.get("seed-002.md"), "modified")
        self.assertEqual(statuses.get("seed-003.md"), "removed")
        self.assertEqual(statuses.get("seed-004.md"), "added")
        self.assertEqual(len(results), 3)


# ---------------------------------------------------------------------------
# Extension hook tests (12r1y)
# ---------------------------------------------------------------------------

def _make_zip_with_extension(source: str, prefix: str = ".wavefoundry/framework/scripts/") -> bytes:
    """Build an in-memory zip containing upgrade_extensions.py."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(prefix + "upgrade_extensions.py", source)
    return buf.getvalue()


class LoadExtensionModuleTests(unittest.TestCase):
    """Tests for _load_extension_module (AC-1)."""

    def setUp(self):
        self.mod = load_upgrade_module()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _zip_with(self, source: str, prefix: str = ".wavefoundry/framework/scripts/") -> Path:
        p = self.root / "wf-test.zip"
        p.write_bytes(_make_zip_with_extension(source, prefix=prefix))
        return p

    def test_returns_none_when_no_zip(self):
        self.assertIsNone(self.mod._load_extension_module(None))

    def test_returns_none_when_zip_has_no_extension_module(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("some-other-file.txt", "hello")
        p = self.root / "empty.zip"
        p.write_bytes(buf.getvalue())
        self.assertIsNone(self.mod._load_extension_module(p))

    def test_loads_module_from_primary_prefix(self):
        zip_path = self._zip_with("MY_MARKER = 'loaded'\n")
        ext = self.mod._load_extension_module(zip_path)
        self.assertIsNotNone(ext)
        self.assertEqual(ext.MY_MARKER, "loaded")

    def test_loads_module_from_alt_prefix(self):
        zip_path = self._zip_with("MY_MARKER = 'alt'\n", prefix="framework/scripts/")
        ext = self.mod._load_extension_module(zip_path)
        self.assertIsNotNone(ext)
        self.assertEqual(ext.MY_MARKER, "alt")

    def test_returns_none_on_syntax_error(self):
        zip_path = self._zip_with("def broken(:\n    pass\n")
        result = self.mod._load_extension_module(zip_path)
        self.assertIsNone(result)

    def test_returns_none_on_bad_zip(self):
        p = self.root / "bad.zip"
        p.write_bytes(b"not a zip")
        self.assertIsNone(self.mod._load_extension_module(p))


class RunHookTests(unittest.TestCase):
    """Tests for _run_hook (AC-2 through AC-5)."""

    def setUp(self):
        self.mod = load_upgrade_module()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.ctx = self.mod.UpgradeContext(
            root=self.root,
            from_version="2026-05-10a",
            to_version="2026-05-19a",
            zip_path=None,
            yes=True,
        )

    def tearDown(self):
        self.tmp.cleanup()

    def _make_ext(self, source: str):
        import types as _types
        m = _types.ModuleType("upgrade_extensions")
        exec(compile(source, "<test>", "exec"), m.__dict__)
        return m

    def _make_convention_hook(self, name: str, exit_code: int = 0) -> Path:
        hooks_dir = self.root / ".wavefoundry" / "hooks"
        hooks_dir.mkdir(parents=True, exist_ok=True)
        script = hooks_dir / name
        script.write_text(f"#!/bin/sh\nexit {exit_code}\n", encoding="utf-8")
        script.chmod(0o755)
        return script

    # AC-5: no-op when neither layer defines the hook
    def test_noop_when_no_hooks_defined(self):
        ext = self._make_ext("")  # empty module
        self.mod._run_hook("pre_surface_rendering", self.ctx, ext)  # must not raise

    def test_noop_when_ext_mod_is_none(self):
        self.mod._run_hook("pre_surface_rendering", self.ctx, None)

    # AC-2: extension module hook called
    def test_extension_module_hook_is_called(self):
        called = []
        ext = self._make_ext(
            "def pre_surface_rendering(ctx): called.append(ctx.from_version)"
        )
        ext.__dict__["called"] = called
        ext.pre_surface_rendering = lambda ctx: called.append(ctx.from_version)
        self.mod._run_hook("pre_surface_rendering", self.ctx, ext)
        self.assertEqual(called, ["2026-05-10a"])

    # AC-2: convention script hook called
    def test_convention_script_hook_is_called(self):
        sentinel = self.root / "hook-ran"
        hooks_dir = self.root / ".wavefoundry" / "hooks"
        hooks_dir.mkdir(parents=True, exist_ok=True)
        script = hooks_dir / "pre-pruning"
        script.write_text(
            f"#!/bin/sh\ntouch {sentinel}\n", encoding="utf-8"
        )
        script.chmod(0o755)
        self.mod._run_hook("pre_pruning", self.ctx, None)
        self.assertTrue(sentinel.exists())

    # AC-2: both layers called in order
    def test_both_layers_called_in_order(self):
        order = []
        sentinel = self.root / "convention-ran"
        # Extension module appends "ext"
        ext = self._make_ext("")
        ext.post_extract = lambda ctx: order.append("ext")
        # Convention script appends "conv" via a file
        hooks_dir = self.root / ".wavefoundry" / "hooks"
        hooks_dir.mkdir(parents=True, exist_ok=True)
        script = hooks_dir / "post-extract"
        script.write_text(
            f"#!/bin/sh\ntouch {sentinel}\n", encoding="utf-8"
        )
        script.chmod(0o755)
        self.mod._run_hook("post_extract", self.ctx, ext)
        self.assertEqual(order, ["ext"])       # ext ran
        self.assertTrue(sentinel.exists())      # convention ran

    # AC-3: extension module exception aborts (sys.exit(3))
    def test_extension_hook_exception_exits_3(self):
        ext = self._make_ext("")
        ext.pre_docs_gate = lambda ctx: (_ for _ in ()).throw(RuntimeError("boom"))
        with self.assertRaises(SystemExit) as cm:
            self.mod._run_hook("pre_docs_gate", self.ctx, ext)
        self.assertEqual(cm.exception.code, 3)

    # AC-4: convention script non-zero exit aborts (sys.exit(3))
    def test_convention_hook_nonzero_exits_3(self):
        self._make_convention_hook("post-docs-gate", exit_code=1)
        with self.assertRaises(SystemExit) as cm:
            self.mod._run_hook("post_docs_gate", self.ctx, None)
        self.assertEqual(cm.exception.code, 3)

    # Wave 1p9hm (L-4c): on Windows a bare extensionless convention hook cannot be spawned by path.
    # It must be SKIPPED (logged) — not spawned — so the OSError that previously escaped the
    # TimeoutExpired-only except never crashes the upgrade. Exercised on POSIX by patching os.name.
    def test_convention_hook_windows_skips_extensionless_without_spawn(self):
        hooks_dir = self.root / ".wavefoundry" / "hooks"
        hooks_dir.mkdir(parents=True, exist_ok=True)
        (hooks_dir / "pre-pruning").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")  # extensionless
        with patch.object(self.mod.os, "name", "nt"):
            with patch.object(self.mod.subprocess_util, "isolated_run") as run:
                self.mod._run_hook("pre_pruning", self.ctx, None)  # must NOT raise
        run.assert_not_called()  # extensionless hook is skipped on Windows, never spawned by path

    # Wave 1p9hm (L-4c): on Windows a `<name>.py` convention hook is dispatched via the interpreter.
    def test_convention_hook_windows_dispatches_py_via_interpreter(self):
        from types import SimpleNamespace
        hooks_dir = self.root / ".wavefoundry" / "hooks"
        hooks_dir.mkdir(parents=True, exist_ok=True)
        (hooks_dir / "pre-pruning.py").write_text("import sys; sys.exit(0)\n", encoding="utf-8")
        with patch.object(self.mod.os, "name", "nt"):
            with patch.object(self.mod, "_preferred_python", return_value="PY"):
                with patch.object(self.mod.subprocess_util, "isolated_run",
                                  return_value=SimpleNamespace(returncode=0)) as run:
                    self.mod._run_hook("pre_pruning", self.ctx, None)
        run.assert_called_once()
        cmd = run.call_args[0][0]
        self.assertEqual(cmd, ["PY", str(hooks_dir / "pre-pruning.py")])

    # Wave 1p9hm (L-4c): a `<name>.cmd` convention hook must be launched via `cmd /c` — NOT by bare
    # path — because subprocess.run(shell=False) + Windows CreateProcess cannot execute a batch file
    # by path (WinError 193). Guards against reintroducing that crash class.
    def test_convention_hook_windows_dispatches_cmd_via_cmd_shell(self):
        from types import SimpleNamespace
        hooks_dir = self.root / ".wavefoundry" / "hooks"
        hooks_dir.mkdir(parents=True, exist_ok=True)
        (hooks_dir / "pre-pruning.cmd").write_text("@echo off\r\nexit /b 0\r\n", encoding="utf-8")
        with patch.object(self.mod.os, "name", "nt"):
            with patch.object(self.mod.subprocess_util, "isolated_run",
                              return_value=SimpleNamespace(returncode=0)) as run:
                self.mod._run_hook("pre_pruning", self.ctx, None)
        run.assert_called_once()
        cmd = run.call_args[0][0]
        self.assertEqual(cmd, ["cmd", "/c", str(hooks_dir / "pre-pruning.cmd")])


class UpgradeContextTests(unittest.TestCase):
    """Tests for UpgradeContext attribute population (AC-6)."""

    def setUp(self):
        self.mod = load_upgrade_module()

    def test_attributes_set_correctly(self):
        root = Path("/tmp/fake-root")
        ctx = self.mod.UpgradeContext(
            root=root,
            from_version="2026-05-10a",
            to_version="2026-05-19a",
            zip_path=Path("/tmp/wf.zip"),
            yes=True,
        )
        self.assertEqual(ctx.root, root)
        self.assertEqual(ctx.from_version, "2026-05-10a")
        self.assertEqual(ctx.to_version, "2026-05-19a")
        self.assertEqual(ctx.zip_path, Path("/tmp/wf.zip"))
        self.assertTrue(ctx.yes)

    def test_none_versions_allowed(self):
        ctx = self.mod.UpgradeContext(Path("."), None, None, None, False)
        self.assertIsNone(ctx.from_version)
        self.assertIsNone(ctx.to_version)
        self.assertIsNone(ctx.zip_path)
        self.assertFalse(ctx.yes)


# ---------------------------------------------------------------------------
# _print_change_plan — seed_diffs=None must show "n/a" (AC-5 regression guard)
# ---------------------------------------------------------------------------

class PrintChangePlanSeedDiffsTests(unittest.TestCase):
    """Regression tests for AC-5: no-zip path shows n/a, not none."""

    def setUp(self):
        self.mod = load_upgrade_module()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _capture_plan(self, seed_diffs):
        lines = []
        orig_log = self.mod._log
        self.mod._log = lambda msg: lines.append(msg)
        try:
            self.mod._print_change_plan(
                root=self.root,
                from_version="2026-05-10a",
                to_version="2026-05-19a",
                zip_path=None,
                dash_running=False,
                prompt_files=[],
                seed_diffs=seed_diffs,
            )
        finally:
            self.mod._log = orig_log
        return "\n".join(lines)

    def test_no_zip_shows_na(self):
        """seed_diffs=None (no zip) must emit 'n/a', not 'none'."""
        output = self._capture_plan(seed_diffs=None)
        self.assertIn("n/a", output)
        self.assertNotIn("Seeds changed:      none", output)

    def test_empty_diffs_shows_none(self):
        """seed_diffs=[] (zip present, nothing changed) must emit 'none'."""
        output = self._capture_plan(seed_diffs=[])
        self.assertIn("Seeds changed:      none", output)
        self.assertNotIn("n/a", output)


# ---------------------------------------------------------------------------
# _read_extension_source
# ---------------------------------------------------------------------------

class ReadExtensionSourceTests(unittest.TestCase):
    """Tests for _read_extension_source (dry-run helper)."""

    def setUp(self):
        self.mod = load_upgrade_module()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _zip_with(self, source: str, prefix: str = ".wavefoundry/framework/scripts/") -> Path:
        import io as _io
        buf = _io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr(prefix + "upgrade_extensions.py", source)
        p = self.root / "test.zip"
        p.write_bytes(buf.getvalue())
        return p

    def test_returns_none_when_no_zip(self):
        self.assertIsNone(self.mod._read_extension_source(None))

    def test_returns_source_from_primary_prefix(self):
        zip_path = self._zip_with("MY_MARKER = 'hello'\n")
        result = self.mod._read_extension_source(zip_path)
        self.assertIsNotNone(result)
        candidate, source = result
        self.assertIn("upgrade_extensions.py", candidate)
        self.assertIn("MY_MARKER", source)

    def test_returns_source_from_alt_prefix(self):
        zip_path = self._zip_with("MY_MARKER = 'alt'\n", prefix="framework/scripts/")
        result = self.mod._read_extension_source(zip_path)
        self.assertIsNotNone(result)
        _, source = result
        self.assertIn("MY_MARKER", source)

    def test_returns_none_when_not_in_zip(self):
        import io as _io
        buf = _io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("other.txt", "hi")
        p = self.root / "no-ext.zip"
        p.write_bytes(buf.getvalue())
        self.assertIsNone(self.mod._read_extension_source(p))

    def test_returns_none_on_bad_zip(self):
        p = self.root / "bad.zip"
        p.write_bytes(b"not a zip")
        self.assertIsNone(self.mod._read_extension_source(p))

    def test_does_not_execute_source(self):
        """_read_extension_source must not exec the code — side-effects must not run."""
        sentinel = self.root / "should-not-exist"
        # Write code that would create a file if executed
        source = f"open({str(sentinel)!r}, 'w').close()\n"
        zip_path = self._zip_with(source)
        self.mod._read_extension_source(zip_path)
        self.assertFalse(sentinel.exists(), "Extension source was exec'd during dry-run read")


# ---------------------------------------------------------------------------
# phase_dry_run
# ---------------------------------------------------------------------------

class FindLatestReleaseZipTests(unittest.TestCase):
    """Tests for _find_latest_release_zip() multi-location semver discovery."""

    def setUp(self):
        self.mod = load_upgrade_module()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "repo"
        self.user_home = Path(self.tmp.name) / "home"
        self.home_dir = Path(self.tmp.name) / "home-wavefoundry"
        self.dist_dir = self.home_dir / "dist"
        self.downloads_dir = Path(self.tmp.name) / "downloads"
        self.root.mkdir(parents=True)
        self.user_home.mkdir(parents=True)
        self.home_dir.mkdir(parents=True)
        self.dist_dir.mkdir(parents=True)
        self.downloads_dir.mkdir(parents=True)

    def tearDown(self):
        self.tmp.cleanup()

    def _write_zip(self, directory: Path, name: str) -> Path:
        p = directory / name
        p.write_bytes(b"fake")
        return p

    def _run(self) -> Path | None:
        with unittest.mock.patch.object(
            self.mod, "_HOME_DIR", self.user_home
        ), unittest.mock.patch.object(
            self.mod, "_HOME_WAVEFOUNDRY_DIR", self.home_dir
        ), unittest.mock.patch.object(
            self.mod, "_DIST_DIR", self.dist_dir
        ), unittest.mock.patch.object(
            self.mod, "_DOWNLOADS_DIR", self.downloads_dir
        ):
            return self.mod._find_latest_release_zip(self.root)

    def test_returns_none_when_dir_absent(self):
        import shutil
        shutil.rmtree(self.root)
        shutil.rmtree(self.user_home)
        shutil.rmtree(self.home_dir)
        with unittest.mock.patch.object(
            self.mod, "_HOME_DIR", self.user_home
        ), unittest.mock.patch.object(
            self.mod, "_HOME_WAVEFOUNDRY_DIR", self.home_dir
        ), unittest.mock.patch.object(
            self.mod, "_DIST_DIR", self.dist_dir
        ), unittest.mock.patch.object(self.mod, "_DOWNLOADS_DIR", self.downloads_dir):
            result = self.mod._find_latest_release_zip(self.root)
        self.assertIsNone(result)

    def test_returns_none_when_dir_empty(self):
        result = self._run()
        self.assertIsNone(result)

    def test_finds_zip_in_user_home(self):
        self._write_zip(self.user_home, "wavefoundry-1.2.0.2abc.zip")
        result = self._run()
        self.assertIsNotNone(result)
        self.assertEqual(result.name, "wavefoundry-1.2.0.2abc.zip")

    def test_finds_zip_in_downloads(self):
        # 1p5dk: browser-downloaded packs commonly land in ~/Downloads — discovery must see them.
        self._write_zip(self.downloads_dir, "wavefoundry-1.2.0.2abc.zip")
        result = self._run()
        self.assertIsNotNone(result)
        self.assertEqual(result.name, "wavefoundry-1.2.0.2abc.zip")

    def test_downloads_competes_on_semver(self):
        # A higher-semver pack in Downloads wins over a lower one in dist (all paths pooled).
        self._write_zip(self.dist_dir, "wavefoundry-1.0.0.2abc.zip")
        self._write_zip(self.downloads_dir, "wavefoundry-1.6.0.p5ec.zip")
        result = self._run()
        self.assertIsNotNone(result)
        self.assertEqual(result.name, "wavefoundry-1.6.0.p5ec.zip")

    def test_returns_highest_semver_zip(self):
        self._write_zip(self.root, "wavefoundry-0.8.0.2abc.zip")
        self._write_zip(self.home_dir, "wavefoundry-1.0.0.2tm5.zip")
        self._write_zip(self.dist_dir, "wavefoundry-0.8.1.2def.zip")
        result = self._run()
        self.assertIsNotNone(result)
        self.assertEqual(result.name, "wavefoundry-1.0.0.2tm5.zip")

    def test_skips_non_matching_filenames(self):
        self._write_zip(self.dist_dir, "wavefoundry-1.0.0.2abc.zip")
        (self.home_dir / "unrelated.zip").write_bytes(b"x")
        (self.root / "wavefoundry-2026-05-20i.zip").write_bytes(b"x")
        result = self._run()
        self.assertIsNotNone(result)
        self.assertEqual(result.name, "wavefoundry-1.0.0.2abc.zip")

    def test_multi_digit_minor_beats_single_digit(self):
        """1.10.0 must rank above 1.9.0 — not lexicographic comparison."""
        self._write_zip(self.home_dir, "wavefoundry-1.9.0.2abc.zip")
        self._write_zip(self.dist_dir, "wavefoundry-1.10.0.2xyz.zip")
        result = self._run()
        self.assertIsNotNone(result)
        self.assertEqual(result.name, "wavefoundry-1.10.0.2xyz.zip")

    def test_same_version_returns_lexicographically_greatest_build(self):
        """When MAJOR.MINOR.PATCH is tied, pick greatest build prefix (most recent build)."""
        self._write_zip(self.root, "wavefoundry-1.0.0.2abc.zip")
        self._write_zip(self.dist_dir, "wavefoundry-1.0.0.2zzz.zip")
        result = self._run()
        self.assertIsNotNone(result)
        self.assertEqual(result.name, "wavefoundry-1.0.0.2zzz.zip")

    def test_prefers_root_over_home_only_when_root_has_higher_version(self):
        self._write_zip(self.root, "wavefoundry-1.1.0.2zzz.zip")
        self._write_zip(self.home_dir, "wavefoundry-1.0.0.2abc.zip")
        result = self._run()
        self.assertIsNotNone(result)
        self.assertEqual(result.name, "wavefoundry-1.1.0.2zzz.zip")


import unittest.mock  # ensure mock is imported for FindLatestReleaseZipTests


class DryRunTests(unittest.TestCase):
    """Tests for phase_dry_run (--dry-run / -n)."""

    def setUp(self):
        self.mod = load_upgrade_module()
        # Save and restore the module-level _log_file global so dry-run's
        # _log() calls don't bleed into any log file opened by another test
        # class, and vice-versa.
        self._saved_log_file = self.mod._log_file
        self.mod._close_log()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        # Minimal repo structure
        (self.root / ".wavefoundry" / "framework").mkdir(parents=True)
        # Isolate from real ~/.wavefoundry/dist/ AND ~/Downloads/ so tests are not polluted by
        # actual release zips present on the developer's machine (1p5dk added ~/Downloads to the
        # search paths — a very common landing spot for real packs).
        self._dist_patch = patch.object(self.mod, "_DIST_DIR", Path(self.tmp.name) / "dist")
        self._dist_patch.start()
        self._downloads_patch = patch.object(self.mod, "_DOWNLOADS_DIR", Path(self.tmp.name) / "downloads")
        self._downloads_patch.start()

    def tearDown(self):
        self._downloads_patch.stop()
        self._dist_patch.stop()
        self.mod._close_log()
        self.mod._log_file = self._saved_log_file  # restore (normally None)
        self.tmp.cleanup()

    def _run_dry(self) -> str:
        lines = []
        orig_log = self.mod._log
        self.mod._log = lambda msg: lines.append(msg)
        try:
            self.mod.phase_dry_run(self.root)
        finally:
            self.mod._log = orig_log
        return "\n".join(lines)

    def test_returns_zero(self):
        result = self.mod.phase_dry_run(self.root)
        self.assertEqual(result, 0)

    def test_no_disk_writes(self):
        """Dry-run must not create the upgrade lock or any other files."""
        ul = _load_upgrade_lib()
        self.mod.phase_dry_run(self.root)
        self.assertIsNone(ul.read_upgrade_lock(self.root))

    def test_output_contains_dry_run_header(self):
        output = self._run_dry()
        self.assertIn("Dry Run", output)
        self.assertIn("no changes will be made", output)

    def test_output_contains_hook_inventory_section(self):
        output = self._run_dry()
        self.assertIn("Hook Inventory", output)

    def test_no_extension_module_when_no_zip(self):
        output = self._run_dry()
        self.assertIn("n/a (no zip)", output)

    def test_extension_module_source_surfaced(self):
        """When zip has upgrade_extensions.py, its source appears in dry-run output."""
        import io as _io
        buf = _io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr(
                ".wavefoundry/framework/scripts/upgrade_extensions.py",
                "# MARKER_IN_SOURCE\n",
            )
        zip_path = self.root / "wavefoundry-1.0.0.2abc.zip"
        zip_path.write_bytes(buf.getvalue())
        output = self._run_dry()
        self.assertIn("MARKER_IN_SOURCE", output)

    def test_convention_hook_source_surfaced(self):
        """Convention hook scripts found on disk appear in dry-run output."""
        hooks_dir = self.root / ".wavefoundry" / "hooks"
        hooks_dir.mkdir(parents=True)
        hook = hooks_dir / "post-extract"
        hook.write_text("#!/bin/sh\n# HOOK_MARKER\nexit 0\n", encoding="utf-8")
        hook.chmod(0o755)
        output = self._run_dry()
        self.assertIn("HOOK_MARKER", output)

    def test_no_convention_hooks_message(self):
        output = self._run_dry()
        self.assertIn("none", output.lower())


# ---------------------------------------------------------------------------
# update_upgrade_lock (upgrade_lib)
# ---------------------------------------------------------------------------

def _load_upgrade_lib():
    import importlib.util as _ilu
    import sys as _sys
    scripts_root = Path(__file__).resolve().parents[1]
    spec = _ilu.spec_from_file_location("upgrade_lib", scripts_root / "upgrade_lib.py")
    mod = _ilu.module_from_spec(spec)
    _sys.modules["upgrade_lib"] = mod
    spec.loader.exec_module(mod)
    return mod


class UpdateUpgradeLockTests(unittest.TestCase):
    """Tests for upgrade_lib.update_upgrade_lock and zip_path in write_upgrade_lock."""

    def setUp(self):
        self.lib = _load_upgrade_lib()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / ".wavefoundry").mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def test_update_returns_false_when_no_lock(self):
        result = self.lib.update_upgrade_lock(self.root, pruned_count=5)
        self.assertFalse(result)

    def test_update_merges_fields(self):
        self.lib.write_upgrade_lock(self.root, "2026-05-10a", "2026-05-19a")
        result = self.lib.update_upgrade_lock(self.root, pruned_count=7)
        self.assertTrue(result)
        lock = self.lib.read_upgrade_lock(self.root)
        self.assertEqual(lock["pruned_count"], 7)
        # Existing fields preserved
        self.assertEqual(lock["from_version"], "2026-05-10a")

    def test_write_lock_records_zip_path(self):
        fake_zip = Path("/tmp/wavefoundry-2026-05-19a.zip")
        self.lib.write_upgrade_lock(self.root, "2026-05-10a", "2026-05-19a", zip_path=fake_zip)
        lock = self.lib.read_upgrade_lock(self.root)
        self.assertEqual(lock["zip_path"], str(fake_zip))

    def test_write_lock_zip_path_none(self):
        self.lib.write_upgrade_lock(self.root, None, "2026-05-19a", zip_path=None)
        lock = self.lib.read_upgrade_lock(self.root)
        self.assertIsNone(lock["zip_path"])

    def test_recovery_write_carries_dashboard_restart_intent(self):
        self.lib.write_upgrade_lock(self.root, "1.12.0", "1.13.0")
        self.lib.update_upgrade_lock(
            self.root,
            failed_phase="docs_gate",
            dashboard_restart_pending=True,
            dashboard_restart_port=43210,
        )
        self.lib.write_upgrade_lock(self.root, "1.12.0", "1.13.0")
        lock = self.lib.read_upgrade_lock(self.root)
        self.assertIsNone(lock["failed_phase"])
        self.assertTrue(lock["dashboard_restart_pending"])
        self.assertEqual(lock["dashboard_restart_port"], 43210)

    def test_pruned_count_initially_none(self):
        self.lib.write_upgrade_lock(self.root, None, "2026-05-19a")
        lock = self.lib.read_upgrade_lock(self.root)
        self.assertIsNone(lock["pruned_count"])

    def test_index_rebuilt_at_recorded(self):
        """1u44n outcome-derived contract (rewritten from the pre-fix
        intent-derived pin): index_rebuilt_at is stamped only when the writer
        OBSERVED a successful publication; an observed failure clears it and
        records index_publication_failed, which --cleanup reads as the
        "publication failed" index_update value instead of success."""
        self.lib.write_upgrade_lock(self.root, None, "2026-05-19a")
        mod = load_upgrade_module()
        mod._record_index_publication_outcome(self.root, True)
        lock = self.lib.read_upgrade_lock(self.root)
        self.assertTrue(bool(lock.get("index_rebuilt_at")))
        self.assertFalse(bool(lock.get("index_publication_failed")))
        mod._record_index_publication_outcome(self.root, False)
        lock = self.lib.read_upgrade_lock(self.root)
        self.assertFalse(bool(lock.get("index_rebuilt_at")))
        self.assertTrue(bool(lock.get("index_publication_failed")))
        # A later observed success supersedes the failure marker.
        mod._record_index_publication_outcome(self.root, True)
        lock = self.lib.read_upgrade_lock(self.root)
        self.assertTrue(bool(lock.get("index_rebuilt_at")))
        self.assertFalse(bool(lock.get("index_publication_failed")))
        # No lock present: recording is a safe no-op.
        self.lib.remove_upgrade_lock(self.root)
        mod._record_index_publication_outcome(self.root, True)
        self.assertIsNone(self.lib.read_upgrade_lock(self.root))


class FailureMarkerLockTests(unittest.TestCase):
    """Wave 1p44o — failed_phase/failed_at persistence in the upgrade lock."""

    def setUp(self):
        self.lib = _load_upgrade_lib()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / ".wavefoundry").mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def test_failure_markers_seeded_none(self):
        """write_upgrade_lock seeds failed_phase/failed_at None for schema clarity."""
        self.lib.write_upgrade_lock(self.root, None, "2026-05-19a")
        lock = self.lib.read_upgrade_lock(self.root)
        self.assertIsNone(lock["failed_phase"])
        self.assertIsNone(lock["failed_at"])

    def test_failure_markers_persist_via_update(self):
        self.lib.write_upgrade_lock(self.root, "2026-05-10a", "2026-05-19a")
        self.lib.update_upgrade_lock(
            self.root, failed_phase="docs_gate", failed_at="2026-06-08T00:00:00+00:00"
        )
        lock = self.lib.read_upgrade_lock(self.root)
        self.assertEqual(lock["failed_phase"], "docs_gate")
        self.assertEqual(lock["failed_at"], "2026-06-08T00:00:00+00:00")
        # Pre-existing fields preserved.
        self.assertEqual(lock["from_version"], "2026-05-10a")

    def test_old_lock_without_markers_still_parses(self):
        """read_upgrade_lock tolerates older locks lacking the new fields."""
        lock_path = self.lib.upgrade_lock_path(self.root)
        lock_path.write_text(
            json.dumps({"from_version": "a", "to_version": "b", "pid": 123}),
            encoding="utf-8",
        )
        lock = self.lib.read_upgrade_lock(self.root)
        self.assertIsNone(lock.get("failed_phase"))


class FinalizeFailedUpgradeTests(unittest.TestCase):
    """Wave 1p44o — the except SystemExit handler's data-safety decision.

    Post-mutation failure RETAINS the lock with a marker; pre-mutation failure
    removes it. Tested via the extracted ``_finalize_failed_upgrade`` helper.
    """

    def setUp(self):
        self.mod = load_upgrade_module()
        self.lib = _load_upgrade_lib()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / ".wavefoundry").mkdir()
        # A lock exists (it is written at upgrade start, before the try body).
        self.lib.write_upgrade_lock(self.root, "2026-05-10a", "2026-05-19a")

    def tearDown(self):
        self.tmp.cleanup()

    def test_post_mutation_retains_lock_with_marker(self):
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            self.mod._finalize_failed_upgrade(
                self.root, tree_mutated=True, current_phase="docs_gate"
            )
        lock = self.lib.read_upgrade_lock(self.root)
        self.assertIsNotNone(lock, "lock must be RETAINED on a post-mutation failure")
        self.assertEqual(lock["failed_phase"], "docs_gate")
        self.assertTrue(lock["failed_at"], "failed_at timestamp must be stamped")
        self.assertIn("--resume-after-gate", stderr.getvalue())
        self.assertNotIn("--cleanup to acknowledge", stderr.getvalue())

    def test_non_gate_failure_never_suggests_cleanup_can_acknowledge_it(self):
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            self.mod._finalize_failed_upgrade(
                self.root, tree_mutated=True, current_phase="surface_rendering"
            )
        self.assertIn("re-run the full upgrade", stderr.getvalue())
        self.assertNotIn("--cleanup to acknowledge", stderr.getvalue())

    def test_pre_mutation_removes_lock(self):
        with contextlib.redirect_stderr(io.StringIO()):
            self.mod._finalize_failed_upgrade(
                self.root, tree_mutated=False, current_phase="extract"
            )
        lock = self.lib.read_upgrade_lock(self.root)
        self.assertIsNone(lock, "lock must be removed on a pre-mutation failure")


class OperatorSummaryGateLineTests(unittest.TestCase):
    """Wave 1p44o — Docs gate summary line derives from lock state (AC-5)."""

    def setUp(self):
        self.mod = load_upgrade_module()

    def _capture_summary(self, **kwargs):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.mod._print_operator_summary(
                from_version="2026-05-10a",
                to_version="2026-05-19a",
                zip_path=None,
                pruned_count=3,
                ran_index_rebuild=True,
                **kwargs,
            )
        return buf.getvalue()

    def test_gate_line_passed_when_no_failure(self):
        self.assertEqual(self.mod._docs_gate_summary_line(None), "PASSED")

    def test_gate_line_failed_when_docs_gate_failed(self):
        self.assertEqual(self.mod._docs_gate_summary_line("docs_gate"), "FAILED")

    def test_gate_line_not_run_for_earlier_phase(self):
        line = self.mod._docs_gate_summary_line("surface_rendering")
        self.assertIn("NOT RUN", line)
        self.assertIn("surface_rendering", line)

    def test_summary_passed_state(self):
        out = self._capture_summary(failed_phase=None)
        self.assertIn("Upgrade complete", out)
        self.assertIn("Docs gate:", out)
        self.assertIn("PASSED", out)
        self.assertNotIn("FAILED", out)

    def test_summary_failed_state_not_hardcoded(self):
        out = self._capture_summary(failed_phase="docs_gate")
        self.assertIn("Docs gate:", out)
        self.assertIn("FAILED", out)
        # The header must not falsely claim success on a failed upgrade.
        self.assertNotIn("Upgrade complete", out)
        self.assertIn("Upgrade INCOMPLETE", out)

    def test_summary_default_failed_phase_is_passed(self):
        """Back-compat: omitting failed_phase renders PASSED (success cleanup)."""
        out = self._capture_summary()
        self.assertIn("PASSED", out)

    def test_next_steps_defers_to_seed_160(self):  # wave 1p454
        out = self._capture_summary()
        self.assertIn("See seed-160 for the full editing-pass sequence", out)  # AC-1
        # Wave 1p454's AC-2 pinned a "seed-160 step 0 / Reconcile journals"
        # step here. Wave 1v4mv REMOVED it: the journal system is retired
        # (seed-120, seed-160) and seed-160's step 0 is pack adoption, not
        # journal work, so the line was wrong on both counts. The absence is
        # pinned by EditingPassStepsAreCurrentTests; this assertion is inverted
        # rather than deleted so the reversal is visible at the original site.
        self.assertNotIn("Reconcile journals", out)
        self.assertNotIn("step 0e", out)                                        # AC-2
        self.assertIn("docs/scan-findings.json", out)                           # AC-3
        self.assertIn("seed-213", out)                                          # AC-3
        # secrets-resolution ordered BEFORE the docs-gate re-run (AC-3)
        self.assertLess(out.index("scan-findings.json"), out.index("Docs gate re-run"))
        # does NOT enumerate seed-160 step-8 backfills verbatim (AC-4)
        self.assertNotIn("lifecycle_id_policy", out)
        self.assertNotIn(".gitignore runtime contract", out)


class PhaseCleanupLockStateTests(unittest.TestCase):
    """Wave 1p44o — phase_cleanup warns on absent lock (AC-4); reflects failed state."""

    def setUp(self):
        self.mod = load_upgrade_module()
        self.lib = _load_upgrade_lib()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / ".wavefoundry").mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def _capture_cleanup(self, **kwargs):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.mod.phase_cleanup(
                root=self.root,
                from_version=None,
                to_version=None,
                zip_path=None,
                pruned_count=0,
                ran_index_rebuild=False,
                **kwargs,
            )
        return buf.getvalue()

    def test_absent_lock_warns_no_phantom_summary(self):
        out = self._capture_cleanup(failed_phase=None, lock_present=False)
        self.assertIn("No upgrade lock found", out)
        # No all-defaults "Upgrade complete" summary masquerading as a real upgrade.
        self.assertNotIn("Upgrade complete", out)
        self.assertNotIn("Version:", out)

    def test_present_lock_prints_summary(self):
        self.lib.write_upgrade_lock(self.root, "2026-05-10a", "2026-05-19a")
        out = self._capture_cleanup(failed_phase=None, lock_present=True)
        self.assertIn("Upgrade complete", out)
        self.assertIn("Docs gate:", out)
        self.assertIn("PASSED", out)

    def test_failed_lock_marks_incomplete(self):
        self.lib.write_upgrade_lock(self.root, "2026-05-10a", "2026-05-19a")
        self.lib.update_upgrade_lock(self.root, failed_phase="docs_gate")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            with self.assertRaises(SystemExit):
                self.mod.phase_cleanup(
                    root=self.root,
                    from_version=None,
                    to_version=None,
                    zip_path=None,
                    pruned_count=0,
                    ran_index_rebuild=False,
                    failed_phase="docs_gate",
                    lock_present=True,
                )
        out = buf.getvalue()
        self.assertIn("Upgrade INCOMPLETE", out)
        self.assertIn("FAILED", out)
        self.assertIn("failure marker", out)
        self.assertIsNotNone(self.lib.read_upgrade_lock(self.root))

    def test_successful_cleanup_regenerates_codebase_map(self):
        # Wave 1p601: a clean upgrade regenerates the codebase map once, after the
        # index phase (so a fresh install has it — a "not generated" field report).
        self.lib.write_upgrade_lock(self.root, "2026-05-10a", "2026-05-19a")
        with patch.object(self.mod, "_regenerate_codebase_map_on_upgrade") as regen:
            self._capture_cleanup(failed_phase=None, lock_present=True)
        regen.assert_called_once_with(self.root)

    def test_failed_cleanup_does_not_regenerate_codebase_map(self):
        # A half-replaced tree (failed phase) must NOT regenerate the map.
        self.lib.write_upgrade_lock(self.root, "2026-05-10a", "2026-05-19a")
        self.lib.update_upgrade_lock(self.root, failed_phase="docs_gate")
        with patch.object(self.mod, "_regenerate_codebase_map_on_upgrade") as regen:
            with self.assertRaises(SystemExit):
                self._capture_cleanup(failed_phase="docs_gate", lock_present=True)
        regen.assert_not_called()

    def test_failed_cleanup_retains_dashboard_restart_intent(self):
        self.lib.write_upgrade_lock(self.root, "1.12.0", "1.13.0")
        self.lib.update_upgrade_lock(
            self.root,
            failed_phase="docs_gate",
            dashboard_restart_pending=True,
            dashboard_restart_port=43210,
        )
        start = MagicMock()
        fake_server = MagicMock(wf_start_dashboard_response=start)
        with patch.dict(sys.modules, {"server_impl": fake_server}):
            with self.assertRaises(SystemExit):
                self._capture_cleanup(failed_phase="docs_gate", lock_present=True)
        start.assert_not_called()
        state = self.lib.read_upgrade_lock(self.root)
        self.assertIsNotNone(state)
        self.assertTrue(state["dashboard_restart_pending"])
        self.assertEqual(state["dashboard_restart_port"], 43210)

    def test_full_retry_preserves_failed_dashboard_restart_intent(self):
        self.lib.write_upgrade_lock(self.root, "1.12.0", "1.13.0")
        self.lib.update_upgrade_lock(
            self.root,
            failed_phase="render",
            dashboard_restart_pending=True,
            dashboard_restart_port=43210,
        )
        with patch.object(self.lib, "is_lock_stale", return_value=True):
            self.mod._clear_stale_upgrade_lock_for_preflight(self.root, self.lib)
        self.assertIsNotNone(self.lib.read_upgrade_lock(self.root))
        self.lib.write_upgrade_lock(self.root, "1.12.0", "1.13.0")
        state = self.lib.read_upgrade_lock(self.root)
        self.assertTrue(state["dashboard_restart_pending"])
        self.assertEqual(state["dashboard_restart_port"], 43210)

    def test_lock_reinitialization_carries_graph_doc_snapshot_only_for_same_target(self):
        packs = self.root / "packs"
        packs.mkdir()
        pack = packs / "wavefoundry-first.zip"
        retry_pack = packs / "wavefoundry-retry.zip"
        other_pack = packs / "wavefoundry-other.zip"
        pack.write_bytes(b"same verified pack")
        retry_pack.write_bytes(pack.read_bytes())
        other_pack.write_bytes(b"different pack")
        pack_sha = hashlib.sha256(pack.read_bytes()).hexdigest()
        self.lib.write_upgrade_lock(self.root, "1.14.0", "1.15.0+pgi2", pack)
        self.lib.update_upgrade_lock(
            self.root,
            graph_builder_doc_claim_pre_extract="44",
            graph_builder_doc_claim_pack_sha256=pack_sha,
        )
        with patch.object(self.lib, "is_lock_stale", return_value=True):
            self.mod._clear_stale_upgrade_lock_for_preflight(self.root, self.lib)
        self.assertIsNotNone(self.lib.read_upgrade_lock(self.root))

        self.lib.write_upgrade_lock(
            self.root, "1.15.0+pgi2", "1.15.0+pgi2", retry_pack
        )
        state = self.lib.read_upgrade_lock(self.root) or {}
        self.assertEqual(state["graph_builder_doc_claim_pre_extract"], "44")

        self.lib.write_upgrade_lock(
            self.root, "1.15.0+pgi2", "1.15.0+pgi3", retry_pack
        )
        state = self.lib.read_upgrade_lock(self.root) or {}
        self.assertNotIn("graph_builder_doc_claim_pre_extract", state)

        self.lib.update_upgrade_lock(
            self.root,
            to_version="1.15.0+pgi2",
            graph_builder_doc_claim_pre_extract="44",
            graph_builder_doc_claim_pack_sha256=pack_sha,
        )
        self.lib.write_upgrade_lock(
            self.root, "1.15.0+pgi2", "1.15.0+pgi2", other_pack
        )
        state = self.lib.read_upgrade_lock(self.root) or {}
        self.assertNotIn("graph_builder_doc_claim_pre_extract", state)

    def test_successful_cleanup_restarts_dashboard_before_removing_upgrade_state(self):
        self.lib.write_upgrade_lock(self.root, "1.12.0", "1.13.0")
        self.lib.update_upgrade_lock(
            self.root,
            dashboard_restart_pending=True,
            dashboard_restart_port=43210,
            runtime_lock_cutover_complete=True,
        )
        start = MagicMock(return_value={"status": "ok", "data": {"started": True}})
        fake_server = MagicMock(wf_start_dashboard_response=start)
        with patch.dict(sys.modules, {"server_impl": fake_server}):
            self._capture_cleanup(failed_phase=None, lock_present=True)
        start.assert_called_once_with(self.root, port=43210)
        self.assertIsNone(self.lib.read_upgrade_lock(self.root))

    def test_restart_failure_retains_upgrade_state_and_restart_intent(self):
        self.lib.write_upgrade_lock(self.root, "1.12.0", "1.13.0")
        self.lib.update_upgrade_lock(
            self.root,
            dashboard_restart_pending=True,
            dashboard_restart_port=43210,
            runtime_lock_cutover_complete=True,
        )
        fake_server = MagicMock(
            wf_start_dashboard_response=MagicMock(
                return_value={"status": "error", "data": {}}
            )
        )
        with patch.dict(sys.modules, {"server_impl": fake_server}):
            with self.assertRaises(SystemExit):
                self._capture_cleanup(failed_phase=None, lock_present=True)
        state = self.lib.read_upgrade_lock(self.root)
        self.assertIsNotNone(state)
        self.assertTrue(state["dashboard_restart_pending"])
        self.assertEqual(state["failed_phase"], "dashboard_restart")

    def test_regenerate_codebase_map_on_upgrade_is_fail_safe(self):
        # Fail-safe contract: a generator error must never propagate out of the
        # upgrade. Force the generator to be unavailable and assert no raise.
        with patch.object(self.mod, "SCRIPTS_DIR", self.root / "no-such-dir"):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                self.mod._regenerate_codebase_map_on_upgrade(self.root)  # must not raise


class ReadInstalledRevisionDelegationTests(unittest.TestCase):
    """Wave 1p44p — upgrade_wavefoundry._read_installed_revision routes through the
    single canonical resolver in check_version (no MANIFEST json.loads)."""

    def setUp(self):
        self.mod = load_upgrade_module()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_delegates_to_manifest_revision(self):
        p = self.root / "docs" / "prompts" / "prompt-surface-manifest.json"
        p.parent.mkdir(parents=True)
        p.write_text(json.dumps({"framework_revision": "1.6.0+xyz"}), encoding="utf-8")
        self.assertEqual(self.mod._read_installed_revision(self.root), "1.6.0+xyz")

    def test_returns_none_when_unresolvable(self):
        self.assertIsNone(self.mod._read_installed_revision(self.root))


class MaterializeSecretsPolicyTests(unittest.TestCase):
    """Wave 1p44z — pre-gate secrets-policy materialization (committer count →
    threshold; create only when absent; never overwrite operator values)."""

    def setUp(self):
        self.mod = load_upgrade_module()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _init_git(self, emails):
        import subprocess as _sp
        _sp.run(["git", "init", "-q"], cwd=self.root, check=True)
        for i, email in enumerate(emails):
            (self.root / f"c{i}.txt").write_text(str(i), encoding="utf-8")
            _sp.run(["git", "add", "."], cwd=self.root, check=True)
            _sp.run(
                ["git", "-c", f"user.email={email}", "-c", f"user.name=A{i}",
                 "-c", "commit.gpgsign=false", "commit", "-q", "-m", f"c{i}"],
                cwd=self.root, check=True,
            )

    def _policy(self) -> Path:
        return self.root / "docs" / "scan-rules.toml"

    def test_threshold_mapping(self):  # AC-3
        m = self.mod._committer_threshold
        self.assertEqual([m(0), m(1)], [1, 1])
        self.assertEqual([m(2), m(6)], [2, 2])
        self.assertEqual([m(7), m(99)], [3, 3])

    def test_single_committer_threshold_one(self):  # AC-2 / AC-3
        self._init_git(["solo@example.com"])
        msg = self.mod.materialize_secrets_policy(self.root)
        self.assertTrue(self._policy().exists())
        self.assertIn("false_positive_confirmations_required = 1", self._policy().read_text())
        self.assertIn("committer", msg)  # observable status (AC-6 surfaces this in the upgrade log)

    def test_small_team_threshold_two(self):  # AC-3
        self._init_git(["a@x.com", "b@x.com", "c@x.com"])
        self.mod.materialize_secrets_policy(self.root)
        self.assertIn("false_positive_confirmations_required = 2", self._policy().read_text())

    def test_existing_file_not_overwritten(self):  # AC-3 / AC-5
        self._policy().parent.mkdir(parents=True)
        self._policy().write_text(
            "[policy]\nfalse_positive_confirmations_required = 5\n", encoding="utf-8"
        )
        msg = self.mod.materialize_secrets_policy(self.root)
        self.assertIn("already present", msg)
        self.assertIn("= 5", self._policy().read_text())  # operator value preserved

    def test_no_git_repo_defaults_to_one(self):  # AC-2 (fresh / no history)
        msg = self.mod.materialize_secrets_policy(self.root)
        self.assertTrue(self._policy().exists())
        self.assertIn("false_positive_confirmations_required = 1", self._policy().read_text())
        self.assertEqual(self.mod._count_committers(self.root), 0)

    def test_materialize_emits_confirmation_valid_days(self):  # 1p457 follow-up
        # The expiry window must be written into the project file (not left as an
        # invisible implicit default), with the operator-facing tunability hint.
        self.mod.materialize_secrets_policy(self.root)
        text = self._policy().read_text()
        self.assertIn("confirmation_valid_days = 365", text)
        self.assertIn("set 0 to disable", text)


class StampManifestRevisionTests(unittest.TestCase):
    """Wave 1p44p follow-up — `_stamp_manifest_revision` writes framework/VERSION into
    `docs/prompts/prompt-surface-manifest.json` `framework_revision` after upgrade so
    the installed-revision marker tracks the pack instead of freezing at the
    pre-upgrade value (never creates the manifest; never clobbers other keys)."""

    def setUp(self):
        self.mod = load_upgrade_module()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _set_version(self, v):
        p = self.root / ".wavefoundry" / "framework" / "VERSION"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(v + "\n", encoding="utf-8")

    def _manifest(self) -> Path:
        return self.root / "docs" / "prompts" / "prompt-surface-manifest.json"

    def _write_manifest(self, data):
        self._manifest().parent.mkdir(parents=True, exist_ok=True)
        self._manifest().write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    def test_stamps_stale_revision(self):
        self._set_version("1.6.0+p49k")
        self._write_manifest({"framework_revision": "1.5.1+p3qj", "other": 1})
        self.assertTrue(self.mod._stamp_manifest_revision(self.root))
        self.assertEqual(
            json.loads(self._manifest().read_text())["framework_revision"], "1.6.0+p49k")

    def test_preserves_other_keys(self):
        self._set_version("1.6.0+p49k")
        self._write_manifest({"framework_revision": "1.5.1+p3qj", "surfaces": ["a", "b"], "n": 3})
        self.mod._stamp_manifest_revision(self.root)
        data = json.loads(self._manifest().read_text())
        self.assertEqual(data["surfaces"], ["a", "b"])
        self.assertEqual(data["n"], 3)

    def test_noop_when_already_current(self):
        self._set_version("1.6.0+p49k")
        self._write_manifest({"framework_revision": "1.6.0+p49k"})
        self.assertFalse(self.mod._stamp_manifest_revision(self.root))

    def test_noop_when_manifest_absent(self):
        self._set_version("1.6.0+p49k")
        self.assertFalse(self.mod._stamp_manifest_revision(self.root))
        self.assertFalse(self._manifest().exists())  # never created

    def test_noop_when_version_absent(self):
        self._write_manifest({"framework_revision": "1.5.1+p3qj"})
        self.assertFalse(self.mod._stamp_manifest_revision(self.root))
        self.assertEqual(
            json.loads(self._manifest().read_text())["framework_revision"], "1.5.1+p3qj")

    def test_noop_when_manifest_unparseable(self):
        self._set_version("1.6.0+p49k")
        self._manifest().parent.mkdir(parents=True, exist_ok=True)
        self._manifest().write_text("{ not json", encoding="utf-8")
        self.assertFalse(self.mod._stamp_manifest_revision(self.root))


class ResumeAfterGateTests(unittest.TestCase):
    """Resume reruns only the docs gate against the retained-lock tree.

    Wave 1tomw: the upgrade projector is retired — resume neither enumerates
    nor reprojects historical waves, and a `review_status_projection` failure
    phase no longer exists.
    """

    def setUp(self):
        self.mod = load_upgrade_module()
        self.lib = _load_upgrade_lib()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / ".wavefoundry").mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def _resume(self):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return self.mod.main(["--resume-after-gate", "--root", str(self.root)])

    def _failed_gate_lock(self):
        self.lib.write_upgrade_lock(self.root, "1.5.0", "1.6.0")
        self.lib.update_upgrade_lock(self.root, failed_phase="docs_gate", failed_at="t")

    # AC-2 / AC-6b — extract idempotence decision.
    def test_tree_already_at_target(self):
        (self.root / "framework").mkdir()
        (self.root / ".wavefoundry" / "framework").mkdir(parents=True)
        (self.root / ".wavefoundry" / "framework" / "VERSION").write_text("1.6.0\n", encoding="utf-8")
        self.assertTrue(self.mod._tree_already_at(self.root, "1.6.0"))
        self.assertFalse(self.mod._tree_already_at(self.root, "1.7.0"))
        self.assertFalse(self.mod._tree_already_at(self.root, "unknown"))
        self.assertFalse(self.mod._tree_already_at(self.root, None))

    def test_tree_already_at_no_version_file(self):
        self.assertFalse(self.mod._tree_already_at(self.root, "1.6.0"))

    def test_resume_runs_only_the_docs_gate_and_clears_marker_on_pass(self):
        self._failed_gate_lock()
        called = []
        with patch.object(
            self.mod,
            "phase_docs_gate",
            lambda r: called.append(("docs", r)),
        ):
            rc = self._resume()
        self.assertEqual(rc, 0)
        self.assertEqual([name for name, _root in called], ["docs"])
        self.assertTrue(all(path.resolve() == self.root.resolve() for _, path in called))
        lock = self.lib.read_upgrade_lock(self.root)
        self.assertIsNone(lock.get("failed_phase"))
        self.assertEqual(lock.get("current_phase"), "awaiting_memory_validation")
        self.assertTrue(str(lock.get("memory_backfill_run_id") or "").strip())

    def test_projector_is_retired_without_replacement(self):
        # Wave 1tomw (AC-11): no projector symbol, recovery marker key, or
        # resume branch for it survives in the upgrade module.
        self.assertFalse(hasattr(self.mod, "phase_review_status_projection"))
        source = UPGRADE_PATH.read_text(encoding="utf-8")
        self.assertNotIn("phase_review_status_projection", source)
        self.assertNotIn("review_status_projection_failure", source)
        self.assertNotIn('"review_status_projection"', source)

    # AC-5 — non-zero exit on repeated gate failure; marker retained.
    def test_resume_nonzero_on_repeated_failure(self):
        self._failed_gate_lock()

        def _fail(_root):
            raise SystemExit(1)

        with patch.object(self.mod, "phase_docs_gate", _fail):
            with self.assertRaises(SystemExit) as cm:
                self._resume()
        self.assertEqual(cm.exception.code, 1)
        lock = self.lib.read_upgrade_lock(self.root)
        self.assertEqual(lock.get("failed_phase"), "docs_gate")

    # AC-3 — refuse to resume when the prior failure was NOT the docs gate.
    def test_resume_refuses_non_gate_failure(self):
        self.lib.write_upgrade_lock(self.root, "1.5.0", "1.6.0")
        self.lib.update_upgrade_lock(self.root, failed_phase="extract", failed_at="t")
        called = []
        with patch.object(
            self.mod, "phase_docs_gate", lambda r: called.append(r)
        ):
            rc = self._resume()
        self.assertEqual(rc, 1)
        self.assertEqual(called, [])  # gate must NOT run

    def test_resume_refuses_sidecar_cleanup_failure(self):
        # A held-lock refusal is not resumable: the operator must stop every
        # attached host and re-run the full upgrade.
        self.lib.write_upgrade_lock(self.root, "1.5.0", "1.6.0")
        self.lib.update_upgrade_lock(
            self.root, failed_phase="review_sidecar_cleanup", failed_at="t"
        )
        called = []
        with patch.object(
            self.mod, "phase_docs_gate", lambda r: called.append(r)
        ):
            rc = self._resume()
        self.assertEqual(rc, 1)
        self.assertEqual(called, [])

    def test_resume_refuses_when_no_lock(self):
        self.assertEqual(self._resume(), 1)


class PhasePruningCountTests(unittest.TestCase):
    """Wave 1p44q — phase_pruning reads the pruned count from prune_framework.py's
    stderr summary, not the old (always-zero) stdout substring heuristic."""

    def setUp(self):
        self.mod = load_upgrade_module()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _prune(self, stderr, stdout="", returncode=0):
        from types import SimpleNamespace
        fake = SimpleNamespace(stdout=stdout, stderr=stderr, returncode=returncode)
        with patch.object(self.mod.subprocess, "run", return_value=fake), \
             contextlib.redirect_stdout(io.StringIO()):
            return self.mod.phase_pruning(self.root)

    def test_deleted_count_parsed(self):
        self.assertEqual(self._prune("prune: deleted 7 item(s)\n"), 7)

    def test_dry_run_would_delete_count_parsed(self):
        self.assertEqual(self._prune("prune: would delete 3 item(s)\n"), 3)

    def test_nothing_to_remove_is_zero(self):
        self.assertEqual(self._prune("prune: nothing to remove\n"), 0)

    def test_old_stdout_heuristic_no_longer_used(self):
        # Per-file stdout lines say "deleted:", never "removed"/"pruned"; the count
        # must come from the stderr summary, so absent-stderr → 0 (not a stdout scan).
        self.assertEqual(self._prune("", stdout="deleted: a\ndeleted: b\n"), 0)

    def test_nonzero_exit_returns_zero(self):
        self.assertEqual(self._prune("prune: deleted 5 item(s)\n", returncode=1), 0)


class PreferredPythonTests(unittest.TestCase):
    """Regression coverage for explicit shared-venv subprocess routing."""

    def setUp(self):
        self.mod = load_upgrade_module()
        # Wave 1p7pm: phase_surface_rendering calls venv_bootstrap.ensure_python_resolves(), which is
        # SIDE-EFFECTING (creates ~/.local/bin/python3 + may append to the shell rc). Patch it to a
        # no-op so driving phase_surface_rendering here never mutates the operator's box. (The real
        # heal is exercised, safely isolated into a tempdir, only in test_venv_bootstrap.py.)
        if str(SCRIPTS_ROOT) not in sys.path:
            sys.path.insert(0, str(SCRIPTS_ROOT))
        import venv_bootstrap
        heal = patch.object(venv_bootstrap, "ensure_python_resolves", return_value="ok")
        self.ensure_python_resolves_mock = heal.start()
        self.addCleanup(heal.stop)
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _make_venv_python(self) -> Path:
        venv_root = self.root / ".venv-test"
        venv_python = venv_root / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        venv_python.parent.mkdir(parents=True, exist_ok=True)
        venv_python.write_text("", encoding="utf-8")
        return venv_python

    def test_phase_surface_rendering_prefers_tool_venv_python(self):
        venv_python = self._make_venv_python()
        mock_proc = MagicMock(returncode=0)
        script = self.root / "render_platform_surfaces.py"
        script.write_text("", encoding="utf-8")
        with patch.dict(os.environ, {"WAVEFOUNDRY_TOOL_VENV": str(venv_python.parents[1])}), \
             patch.object(self.mod, "SCRIPTS_DIR", self.root), \
             patch("subprocess.run", return_value=mock_proc) as run_mock:
            self.mod.phase_surface_rendering(self.root)
        self.assertEqual(run_mock.call_args.args[0][0], str(venv_python))

    def test_phase_index_update_prefers_tool_venv_python(self):
        venv_python = self._make_venv_python()
        mock_proc = MagicMock(returncode=0)
        setup_script = self.root / "setup_index.py"
        setup_script.write_text("", encoding="utf-8")
        with patch.dict(os.environ, {"WAVEFOUNDRY_TOOL_VENV": str(venv_python.parents[1])}), \
             patch.object(self.mod, "SCRIPTS_DIR", self.root), \
             patch("subprocess.run", return_value=mock_proc) as run_mock, \
             patch("subprocess.Popen") as popen_mock:
            self.mod.phase_index_update(self.root)
        self.assertEqual(run_mock.call_args.args[0][0], str(venv_python))
        popen_mock.assert_not_called()

    def test_phase_index_update_runs_graph_only_update(self):
        # Wave 1p7dh: the upgrade index phase updates the GRAPH too (symmetric
        # with semantic) so a GRAPH_BUILDER_VERSION bump materializes during the
        # upgrade. `--graph-only` WITHOUT `--full` → update-or-escalate, not a
        # forced rebuild.
        venv_python = self._make_venv_python()
        mock_proc = MagicMock(returncode=0)
        setup_script = self.root / "setup_index.py"
        setup_script.write_text("", encoding="utf-8")
        with patch.dict(os.environ, {"WAVEFOUNDRY_TOOL_VENV": str(venv_python.parents[1])}), \
             patch.object(self.mod, "SCRIPTS_DIR", self.root), \
             patch("subprocess.run", return_value=mock_proc) as run_mock, \
             patch("subprocess.Popen"):
            self.mod.phase_index_update(self.root)
        graph_calls = [c for c in run_mock.call_args_list if "--graph-only" in c.args[0]]
        self.assertEqual(len(graph_calls), 1, f"expected one --graph-only update call: {run_mock.call_args_list}")
        self.assertNotIn("--full", graph_calls[0].args[0], "update path must be update-or-escalate, not forced --full")

    def test_phase_index_update_passes_durable_model_companion_to_docs_child(self):
        import upgrade_lib

        upgrade_lib.write_upgrade_lock(self.root, "1.14.0", "1.15.0")
        upgrade_lib.update_upgrade_lock(
            self.root,
            model_bundle_path="/tmp/wavefoundry-models-1.zip",
            model_bundle_model_set_version="1",
        )
        setup_script = self.root / "setup_index.py"
        setup_script.write_text("", encoding="utf-8")
        result = MagicMock(returncode=0)
        with patch.object(self.mod, "SCRIPTS_DIR", self.root), \
             patch.object(self.mod.subprocess_util, "isolated_run", return_value=result) as run_mock, \
             patch.object(self.mod.subprocess_util, "isolated_popen"):
            self.mod.phase_index_update(self.root)
        docs_call = next(call for call in run_mock.call_args_list if "--graph-only" not in call.args[0])
        env = docs_call.kwargs["env"]
        self.assertEqual(env["WAVEFOUNDRY_MODEL_BUNDLE"], "/tmp/wavefoundry-models-1.zip")
        self.assertEqual(env["WAVEFOUNDRY_MODEL_BUNDLE_MODEL_SET_VERSION"], "1")

    def test_phase_index_rebuild_runs_graph_only_full(self):
        venv_python = self._make_venv_python()
        mock_proc = MagicMock(returncode=0)
        setup_script = self.root / "setup_index.py"
        setup_script.write_text("", encoding="utf-8")
        with patch.dict(os.environ, {"WAVEFOUNDRY_TOOL_VENV": str(venv_python.parents[1])}), \
             patch.object(self.mod, "SCRIPTS_DIR", self.root), \
             patch("subprocess.run", return_value=mock_proc) as run_mock, \
             patch("subprocess.Popen"):
            self.mod.phase_index_rebuild(self.root)
        graph_calls = [c for c in run_mock.call_args_list if "--graph-only" in c.args[0]]
        self.assertEqual(len(graph_calls), 1, f"expected one --graph-only rebuild call: {run_mock.call_args_list}")
        self.assertIn("--full", graph_calls[0].args[0], "rebuild path runs a full graph rebuild")


class RetiredModelCleanupTests(unittest.TestCase):
    def setUp(self):
        self.mod = load_upgrade_module()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_semver_boundary_ignores_build_metadata_and_fails_closed(self):
        self.assertFalse(self.mod._cleanup_version_eligible("1.15.9"))
        self.assertTrue(self.mod._cleanup_version_eligible("1.16.0"))
        self.assertTrue(self.mod._cleanup_version_eligible("v1.16.0"))
        self.assertTrue(self.mod._cleanup_version_eligible("1.16.0+build.7"))
        self.assertTrue(self.mod._cleanup_version_eligible("1.16.1"))
        self.assertTrue(self.mod._cleanup_version_eligible("1.16.1-rc.1"))
        self.assertFalse(self.mod._cleanup_version_eligible("1.16.0-rc.1"))
        for malformed in (
            "unknown",
            "1.16.0+",
            "1.16.0+bad!",
            "01.16.0",
            "vv1.16.0",
            "1.16.0-",
            "1.16.1-01",
            "1.1٦.0",
            "1.16٢.0",
            " 1.16.0",
            "1.16.0 ",
            "\t1.16.0\n",
        ):
            with self.subTest(malformed=malformed):
                self.assertFalse(self.mod._cleanup_version_eligible(malformed))
        self.assertFalse(self.mod._cleanup_version_eligible(None))

    def test_default_exact_component_removal_is_idempotent(self):
        cache = self.root / "cache"
        target = cache / "models--BAAI--bge-small-en-v1.5"
        target.mkdir(parents=True)
        (target / "payload").write_text("retired", encoding="utf-8")
        self.assertEqual(
            self.mod._remove_retired_component(
                cache, target.name, custom=False
            ),
            "removed",
        )
        self.assertEqual(
            self.mod._remove_retired_component(
                cache, target.name, custom=False
            ),
            "absent",
        )
        self.assertTrue(cache.is_dir())

    def _write_valid_custom_component(self, component: Path) -> None:
        import hashlib

        (component / "refs").mkdir(parents=True)
        (component / "snapshots" / "rev").mkdir(parents=True)
        (component / "blobs").mkdir()
        (component / "refs" / "main").write_text("rev", encoding="utf-8")
        blob = component / "blobs" / "abc"
        blob.write_bytes(b"weights")
        (component / "snapshots" / "rev" / "model.onnx").symlink_to(
            Path("../../blobs/abc")
        )
        files = {
            "refs/main": hashlib.sha256(b"rev").hexdigest(),
            "snapshots/rev/model.onnx": hashlib.sha256(b"weights").hexdigest(),
        }
        (component / ".wavefoundry-model-bundle.json").write_text(
            json.dumps(
                {
                    "model_set_version": "1",
                    "fingerprint": "wf-model-set-1-20260803",
                    "files": files,
                }
            ),
            encoding="utf-8",
        )

    def test_custom_marker_requires_exact_legacy_inventory(self):
        component = self.root / "custom" / "models--BAAI--bge-small-en-v1.5"
        self._write_valid_custom_component(component)
        self.assertTrue(self.mod._legacy_custom_component_owned(component))
        (component / "blobs" / "unreferenced").write_bytes(b"extra")
        self.assertFalse(self.mod._legacy_custom_component_owned(component))

    def test_symlink_component_never_traverses_external_referent(self):
        cache = self.root / "cache"
        cache.mkdir()
        external = self.root / "external"
        external.mkdir()
        sentinel = external / "keep"
        sentinel.write_text("safe", encoding="utf-8")
        link = cache / "models--BAAI--bge-small-en-v1.5"
        link.symlink_to(external, target_is_directory=True)
        self.assertEqual(
            self.mod._remove_retired_component(cache, link.name, custom=False),
            "removed",
        )
        self.assertEqual(sentinel.read_text(encoding="utf-8"), "safe")

    def test_mutation_boundary_substitution_preserves_external_referent(self):
        cache = self.root / "cache"
        target = cache / "models--BAAI--bge-small-en-v1.5"
        target.mkdir(parents=True)
        external = self.root / "external"
        external.mkdir()
        sentinel = external / "keep"
        sentinel.write_text("safe", encoding="utf-8")
        real_rmtree = self.mod.shutil.rmtree
        swapped = False

        def substitute(path, *args, **kwargs):
            # 1v0r0 repair (F4): mirror the production call signature
            # (component name + dir_fd kwarg); the previous single-argument
            # substitute raised TypeError before the swap ever ran, so the
            # test passed vacuously. `target` (closure) is the absolute path
            # of the component the relative `path` addresses.
            nonlocal swapped
            target.rmdir()
            target.symlink_to(external, target_is_directory=True)
            swapped = True
            return real_rmtree(path, *args, **kwargs)

        with patch.object(self.mod.shutil, "rmtree", side_effect=substitute):
            outcome = self.mod._remove_retired_component(
                cache, target.name, custom=False
            )
        self.assertTrue(swapped, "the symlink substitution must execute")
        self.assertEqual(outcome, "failed")
        self.assertEqual(sentinel.read_text(encoding="utf-8"), "safe")

    def test_cache_root_substitution_cannot_redirect_recursive_removal(self):
        cache = self.root / "cache"
        component = "models--BAAI--bge-small-en-v1.5"
        target = cache / component
        target.mkdir(parents=True)
        (target / "retired").write_text("remove", encoding="utf-8")
        moved_cache = self.root / "checked-cache"
        external = self.root / "external"
        external_target = external / component
        external_target.mkdir(parents=True)
        sentinel = external_target / "DO_NOT_DELETE"
        sentinel.write_text("safe", encoding="utf-8")
        real_rmtree = self.mod.shutil.rmtree
        swapped = False

        def substitute(path, *args, **kwargs):
            nonlocal swapped
            if not swapped:
                cache.rename(moved_cache)
                cache.symlink_to(external, target_is_directory=True)
                swapped = True
            return real_rmtree(path, *args, **kwargs)

        with patch.object(self.mod.shutil, "rmtree", side_effect=substitute):
            outcome = self.mod._remove_retired_component(
                cache, component, custom=False
            )
        self.assertEqual(outcome, "removed")
        self.assertTrue(swapped, "the known-bad root substitution must execute")
        self.assertEqual(sentinel.read_text(encoding="utf-8"), "safe")
        self.assertFalse((moved_cache / component).exists())

    def mod_int8_revision(self) -> str:
        """The int8 encoding-revision token, read from its single source of truth (wave 1v454)."""
        import indexer

        return str(indexer.INT8_ENCODING_REVISION)

    def test_stable_epoch_requires_both_layers_and_canonical_composites(self):
        # Wave 1v454: an int8 layer records the single-row encoding revision appended to the
        # model-set fingerprint; a full layer records the bare one. Both shapes must validate.
        summary = {
            "content": ["docs", "code"],
            "model_versions": {
                "docs": "Snowflake/snowflake-arctic-embed-s@full@fp-v2",
                "code": f"Snowflake/snowflake-arctic-embed-s@int8@fp-v2-{self.mod_int8_revision()}",
            },
        }
        fake_store = MagicMock()
        fake_store.build_epoch_token.side_effect = [("a", 2), ("a", 2)]
        fake_store.read_build_summary.return_value = summary
        with patch.dict(sys.modules, {"index_state_store": fake_store}):
            self.assertTrue(
                self.mod._semantic_epoch_matches_active_models(
                    self.root,
                    (
                        "Snowflake/snowflake-arctic-embed-s",
                        "Snowflake/snowflake-arctic-embed-s",
                        "fp-v2",
                    ),
                )
            )
        fake_store.build_epoch_token.side_effect = [("v3", 7), ("v3", 7)]
        fake_store.read_build_summary.return_value = {
            "content": ["docs", "code"],
            "model_versions": {
                "docs": "future/docs@full@fp-v3",
                "code": f"future/code@int8@fp-v3-{self.mod_int8_revision()}",
            },
        }
        with patch.dict(sys.modules, {"index_state_store": fake_store}):
            self.assertTrue(
                self.mod._semantic_epoch_matches_active_models(
                    self.root, ("future/docs", "future/code", "fp-v3")
                )
            )
        # Wave 1v454: an int8 layer still carrying the PRE-revision bare fingerprint is a stale
        # epoch. It must be rejected, or the retired-model cleanup would run against vectors
        # produced by the old batched encoding. This is the guard that forces the one-time
        # re-embed on a CPU-bound host before cleanup is allowed to proceed.
        fake_store.build_epoch_token.side_effect = [("v3", 7), ("v3", 7)]
        fake_store.read_build_summary.return_value = {
            "content": ["docs", "code"],
            "model_versions": {
                "docs": "future/docs@full@fp-v3",
                "code": "future/code@int8@fp-v3",
            },
        }
        with patch.dict(sys.modules, {"index_state_store": fake_store}):
            self.assertFalse(
                self.mod._semantic_epoch_matches_active_models(
                    self.root, ("future/docs", "future/code", "fp-v3")
                ),
                "a pre-revision int8 identity must not satisfy the active-model epoch",
            )
        fake_store.build_epoch_token.side_effect = [None, None]
        with patch.dict(sys.modules, {"index_state_store": fake_store}):
            self.assertFalse(
                self.mod._semantic_epoch_matches_active_models(
                    self.root,
                    ("x", "x", "fp-v2"),
                )
            )

    def test_cleanup_result_projection_is_exact_sorted_and_failure_visible(self):
        targets = [
            ("z-target", "default", self.root / "a", "z"),
            ("a-target", "default", self.root / "b", "a"),
            ("u-target", "custom", self.root / "c", "u"),
            ("f-target", "default", self.root / "d", "f"),
        ]
        outcomes = iter(["removed", "absent", "unowned", "failed"])
        with patch.object(
            self.mod,
            "_verified_active_model_authority",
            return_value=("docs/model", "code/model", "fingerprint"),
        ), patch.object(
            self.mod, "_semantic_epoch_matches_active_models", return_value=True
        ), patch.object(
            self.mod, "_retired_cleanup_targets", return_value=targets
        ), patch.object(
            self.mod, "_remove_retired_component", side_effect=lambda *_args, **_kwargs: next(outcomes)
        ):
            result = self.mod._run_retired_model_cleanup(self.root, "1.16.0+build.9")
        self.assertEqual(
            result,
            {
                "retired_model_cleanup_status": "failed",
                "retired_model_cleanup_removed": ["z-target"],
                "retired_model_cleanup_absent": ["a-target"],
                "retired_model_cleanup_unowned": ["u-target"],
                "retired_model_cleanup_failed": ["f-target|remove_failed"],
            },
        )

    def test_active_manifest_vetoes_a_retired_allowlist_component(self):
        active = next(iter(self.mod._RETIRED_MODEL_ALLOWLIST["fastembed"]))
        fake_bundle = types.SimpleNamespace(
            load_canonical_verification_manifest=lambda: {
                "model_set_version": "2",
                "embedding_compatibility_fingerprint": "fp-v2",
                "components": [
                    {
                        "directory": active,
                        "upstream": "Snowflake/snowflake-arctic-embed-s",
                    }
                ],
            },
            local_model_set_status=lambda: "current",
        )
        fake_indexer = types.SimpleNamespace(
            DOCS_MODEL="Snowflake/snowflake-arctic-embed-s",
            CODE_MODEL="Snowflake/snowflake-arctic-embed-s",
            EMBEDDING_MODEL_SET_FINGERPRINT="fp-v2",
        )
        with patch.dict(
            sys.modules, {"model_bundle": fake_bundle, "indexer": fake_indexer}
        ):
            self.assertIsNone(self.mod._verified_active_model_authority(self.root))

    def test_failed_cleanup_retains_lock_and_never_restarts_dashboard(self):
        lock = {
            "dashboard_restart_pending": True,
            "dashboard_restart_port": 4567,
        }
        fake_lib = types.SimpleNamespace(
            read_upgrade_lock=lambda _root: lock,
            remove_upgrade_lock=MagicMock(),
            update_upgrade_lock=MagicMock(),
        )
        failed = {
            "retired_model_cleanup_status": "failed",
            "retired_model_cleanup_removed": [],
            "retired_model_cleanup_absent": [],
            "retired_model_cleanup_unowned": [],
            "retired_model_cleanup_failed": ["coreml:retired|remove_failed"],
        }
        fake_server = MagicMock()
        with patch.dict(sys.modules, {"upgrade_lib": fake_lib}), patch.object(
            self.mod, "_print_operator_summary"
        ), patch.dict(sys.modules, {"server_impl": fake_server}):
            with self.assertRaises(SystemExit) as raised:
                self.mod.phase_cleanup(
                    self.root,
                    "1.15.9",
                    "1.16.0",
                    None,
                    0,
                    True,
                    failed_phase="retired_model_cleanup",
                    retired_model_cleanup=failed,
                )
        self.assertEqual(raised.exception.code, 1)
        fake_lib.remove_upgrade_lock.assert_not_called()
        fake_server.wf_start_dashboard_response.assert_not_called()

    def test_flat_key_guard_refuses_separator_and_traversal_keys(self):
        """1v0r0 repair (F5): a non-flat component key is refused as
        `unowned` before any filesystem access. Permanent form of the
        executed falsification probe: without the guard, a `../victim` key
        rode the dir_fd anchor OUT of the cache root and deleted a sibling
        directory with outcome `removed`."""
        cache = self.root / "cache"
        cache.mkdir()
        victim = self.root / "victim"
        victim.mkdir()
        sentinel = victim / "DO_NOT_DELETE"
        sentinel.write_text("safe", encoding="utf-8")
        for hostile in ("../victim", "..", ".", "", "a/b", "a\\b", "victim/.."):
            with self.subTest(component=hostile):
                self.assertEqual(
                    self.mod._remove_retired_component(
                        cache, hostile, custom=False
                    ),
                    "unowned",
                )
        self.assertTrue(victim.is_dir())
        self.assertEqual(sentinel.read_text(encoding="utf-8"), "safe")

    def test_default_target_enumeration_is_the_exact_allowlist(self):
        """1v0r0 repair (F5): the EXECUTED enumeration equals the 13 pinned
        retired components across the four cache kinds, and a custom root
        adds exactly its custom-scope targets."""
        expected_default = [
            "clean-onnx:default:models--Xenova--bge-reranker-base",
            "clean-onnx:default:models--Xenova--bge-small-en-v1.5",
            "coreml:default:BAAI__bge-base-en-v1.5",
            "coreml:default:BAAI__bge-reranker-base",
            "coreml:default:BAAI__bge-small-en-v1.5",
            "fastembed:default:models--BAAI--bge-base-en-v1.5",
            "fastembed:default:models--BAAI--bge-reranker-base",
            "fastembed:default:models--BAAI--bge-small-en-v1.5",
            "fastembed:default:models--qdrant--bge-base-en-v1.5-onnx-q",
            "fastembed:default:models--qdrant--bge-small-en-v1.5-onnx-q",
            "static-onnx:default:BAAI__bge-base-en-v1.5",
            "static-onnx:default:BAAI__bge-reranker-base",
            "static-onnx:default:BAAI__bge-small-en-v1.5",
        ]
        base_env = {
            key: value
            for key, value in os.environ.items()
            if key not in {"FASTEMBED_CACHE_PATH", "WAVEFOUNDRY_ONNX_SRC_CACHE"}
        }
        with patch.dict(os.environ, base_env, clear=True):
            default_targets = self.mod._retired_cleanup_targets()
        self.assertEqual(
            [target[0] for target in default_targets], expected_default
        )
        self.assertTrue(
            all(target[1] == "default" for target in default_targets)
        )

        custom_fast = self.root / "custom-fastembed"
        custom_onnx = self.root / "custom-onnx-src"
        custom_env = dict(base_env)
        custom_env["FASTEMBED_CACHE_PATH"] = str(custom_fast)
        custom_env["WAVEFOUNDRY_ONNX_SRC_CACHE"] = str(custom_onnx)
        expected_custom = sorted(
            expected_default
            + [
                "clean-onnx:custom:models--Xenova--bge-reranker-base",
                "clean-onnx:custom:models--Xenova--bge-small-en-v1.5",
                "fastembed:custom:models--BAAI--bge-base-en-v1.5",
                "fastembed:custom:models--BAAI--bge-reranker-base",
                "fastembed:custom:models--BAAI--bge-small-en-v1.5",
                "fastembed:custom:models--qdrant--bge-base-en-v1.5-onnx-q",
                "fastembed:custom:models--qdrant--bge-small-en-v1.5-onnx-q",
            ]
        )
        with patch.dict(os.environ, custom_env, clear=True):
            custom_targets = self.mod._retired_cleanup_targets()
        self.assertEqual(
            [target[0] for target in custom_targets], expected_custom
        )
        for target_id, scope, cache_root, _component in custom_targets:
            if scope == "custom":
                expected_root = (
                    custom_fast
                    if target_id.startswith("fastembed:")
                    else custom_onnx
                )
                self.assertEqual(cache_root, expected_root, target_id)

    def test_removal_preserves_prefix_siblings_and_active_components(self):
        """1v0r0 repair (F5): removal takes ONLY the exact allowlisted
        component; a prefix-named sibling and the active Arctic S / L6
        component directories survive byte-intact."""
        cache = self.root / "fastembed-cache"
        retired_name = "models--BAAI--bge-small-en-v1.5"
        retired = cache / retired_name
        retired.mkdir(parents=True)
        (retired / "payload").write_text("retired", encoding="utf-8")
        preserved = {
            "models--BAAI--bge-small-en-v1.5-extra": b"prefix sibling",
            "models--snowflake--snowflake-arctic-embed-s": b"arctic embedder",
            "models--Xenova--ms-marco-MiniLM-L-6-v2": b"l6 reranker",
        }
        for name, payload in preserved.items():
            directory = cache / name
            directory.mkdir()
            (directory / "weights.bin").write_bytes(payload)
        outcomes = {
            component: self.mod._remove_retired_component(
                cache, component, custom=False
            )
            for component in self.mod._RETIRED_MODEL_ALLOWLIST["fastembed"]
        }
        self.assertEqual(outcomes.pop(retired_name), "removed")
        self.assertEqual(set(outcomes.values()), {"absent"})
        self.assertFalse(retired.exists())
        for name, payload in preserved.items():
            self.assertEqual(
                (cache / name / "weights.bin").read_bytes(), payload, name
            )

    def _patch_missing_fd_capabilities(self):
        """Simulate a host without the fd-anchored deletion capabilities
        (permanently true on native Windows): strip the ``dir_fd`` support
        set and the ``rmtree`` symlink-attack guarantee, mirroring the
        red-team probes."""
        stack = contextlib.ExitStack()
        stack.enter_context(
            patch.object(self.mod.os, "supports_dir_fd", frozenset())
        )
        stack.enter_context(
            patch.object(
                self.mod.shutil.rmtree, "avoids_symlink_attacks", False
            )
        )
        return stack

    def test_fallback_removes_component_without_fd_capabilities(self):
        """1v0r0 repair (F1): on hosts without the fd-anchored deletion
        capabilities (native Windows), a present owned component is removed
        via the revalidated no-follow fallback instead of wedging every
        upgrade with outcome `failed`."""
        cache = self.root / "cache"
        target = cache / "models--BAAI--bge-small-en-v1.5"
        (target / "snapshots" / "rev").mkdir(parents=True)
        (target / "payload").write_text("retired", encoding="utf-8")
        (target / "snapshots" / "rev" / "weights.bin").write_bytes(b"old")
        with self._patch_missing_fd_capabilities():
            outcome = self.mod._remove_retired_component(
                cache, target.name, custom=False
            )
        self.assertEqual(outcome, "removed")
        self.assertFalse(target.exists())
        self.assertTrue(cache.is_dir())
        with self._patch_missing_fd_capabilities():
            self.assertEqual(
                self.mod._remove_retired_component(
                    cache, target.name, custom=False
                ),
                "absent",
            )

    def test_fallback_unlinks_symlink_component_node_only(self):
        """1v0r0 repair (F1): under the fallback, a component that is
        itself a symlink is unlinked as a NODE; the external referent
        survives byte-intact."""
        cache = self.root / "cache"
        cache.mkdir()
        external = self.root / "external"
        external.mkdir()
        sentinel = external / "keep"
        sentinel.write_bytes(b"safe bytes")
        link = cache / "models--BAAI--bge-small-en-v1.5"
        link.symlink_to(external, target_is_directory=True)
        with self._patch_missing_fd_capabilities():
            outcome = self.mod._remove_retired_component(
                cache, link.name, custom=False
            )
        self.assertEqual(outcome, "removed")
        self.assertFalse(link.is_symlink())
        self.assertFalse(link.exists())
        self.assertTrue(external.is_dir())
        self.assertEqual(sentinel.read_bytes(), b"safe bytes")

    def test_fallback_never_follows_symlink_entries_inside_component(self):
        """1v0r0 repair (F1): under the fallback, symlink ENTRIES inside
        the component directory (to an external directory and to an
        external file) are unlinked as nodes; the referents survive
        byte-intact."""
        cache = self.root / "cache"
        target = cache / "models--BAAI--bge-small-en-v1.5"
        (target / "snapshots").mkdir(parents=True)
        external = self.root / "external"
        (external / "nested").mkdir(parents=True)
        file_sentinel = external / "weights.bin"
        file_sentinel.write_bytes(b"external weights")
        nested_sentinel = external / "nested" / "keep"
        nested_sentinel.write_bytes(b"nested safe")
        (target / "dir-link").symlink_to(external, target_is_directory=True)
        (target / "snapshots" / "file-link").symlink_to(file_sentinel)
        (target / "payload").write_text("retired", encoding="utf-8")
        with self._patch_missing_fd_capabilities():
            outcome = self.mod._remove_retired_component(
                cache, target.name, custom=False
            )
        self.assertEqual(outcome, "removed")
        self.assertFalse(target.exists())
        self.assertTrue(external.is_dir())
        self.assertEqual(file_sentinel.read_bytes(), b"external weights")
        self.assertEqual(nested_sentinel.read_bytes(), b"nested safe")

    def test_fallback_refuses_top_level_dir_to_symlink_swap_before_descent(self):
        """1v0r0 repair (F9): the no-follow fallback re-lstats the top target
        immediately before descent, so a directory swapped for a symlink to an
        external victim in the entry-lstat -> descent window is refused instead
        of walked and the external referent is never deleted.

        Red-first discriminator: against the prior bare
        ``os.walk(topdown=False, followlinks=False)`` fallback the external
        sentinel was DELETED, because ``followlinks=False`` governs only
        sub-symlinks encountered during the walk, never the walk ROOT."""
        cache = self.root / "cache"
        target = cache / "models--BAAI--bge-small-en-v1.5"
        (target / "payload").mkdir(parents=True)
        (target / "payload" / "inner").write_text("retired", encoding="utf-8")
        external = self.root / "external"
        external.mkdir()
        sentinel = external / "DO_NOT_DELETE"
        sentinel.write_bytes(b"victim bytes")

        real_stat = self.mod.os.stat
        real_lstat = self.mod.os.lstat
        real_rmtree = self.mod.shutil.rmtree
        state = {"swapped": False}

        def _maybe_swap(path):
            # Swap the real directory for a symlink to the external victim
            # AFTER the entry lstat already classified it as a directory (the
            # check-to-use window the pre-descent re-lstat closes).
            if state["swapped"]:
                return
            try:
                is_target = os.fspath(path) == os.fspath(target)
            except TypeError:
                return
            if is_target:
                state["swapped"] = True
                real_rmtree(target)
                target.symlink_to(external, target_is_directory=True)

        # On CPython 3.13 ``Path.lstat()`` routes through
        # ``os.stat(follow_symlinks=False)``; patch both so the injection is
        # version-robust and fires only on the no-follow classification.
        def swapping_stat(path, *args, **kwargs):
            result = real_stat(path, *args, **kwargs)
            if kwargs.get("follow_symlinks", True) is False:
                _maybe_swap(path)
            return result

        def swapping_lstat(path, *args, **kwargs):
            result = real_lstat(path, *args, **kwargs)
            _maybe_swap(path)
            return result

        with patch.object(self.mod.os, "stat", swapping_stat), \
                patch.object(self.mod.os, "lstat", swapping_lstat):
            outcome = self.mod._remove_retired_component_no_follow(target)

        self.assertTrue(state["swapped"], "the in-window swap must execute")
        self.assertIn(outcome, ("failed", "unowned"))
        self.assertTrue(external.is_dir())
        self.assertTrue(sentinel.exists(), "the external referent must survive")
        self.assertEqual(sentinel.read_bytes(), b"victim bytes")

    def test_fallback_classifies_junction_entry_as_node_not_descended(self):
        """1v0r0 repair (F10): a Windows directory junction is NOT a symlink on
        CPython 3.12+, so ``DirEntry.is_symlink()`` is False and a bare
        ``os.walk`` descends it, deleting content the junction points at
        outside the cache root. The fallback classifies every reparse point
        (symlink OR junction) as a NODE via ``os.path.isjunction``.

        This host cannot create a real junction, so ``os.path.isjunction`` is
        monkeypatched True for a crafted directory entry; the assertion is that
        the recursion does NOT descend it (its child survives byte-intact) and
        the entry is handled on the node-unlink path rather than walked."""
        cache = self.root / "cache"
        target = cache / "models--BAAI--bge-small-en-v1.5"
        target.mkdir(parents=True)
        fake_junction = target / "reparse-node"
        fake_junction.mkdir()
        referent = fake_junction / "referent-child"
        referent.write_bytes(b"outside-cache bytes")

        def fake_isjunction(path):
            try:
                return os.fspath(path) == os.fspath(fake_junction)
            except TypeError:
                return False

        with patch.object(self.mod.os.path, "isjunction", fake_isjunction):
            outcome = self.mod._remove_retired_component_no_follow(target)

        # Classified as a node, not descended: the child was never visited, so
        # it survives byte-intact. A non-empty real directory cannot be removed
        # as a node here (a real junction's rmdir would succeed on Windows), so
        # the outcome is `failed` — the load-bearing guarantee is non-descent.
        self.assertTrue(fake_junction.is_dir())
        self.assertEqual(referent.read_bytes(), b"outside-cache bytes")
        self.assertEqual(outcome, "failed")

    def _cleanup_root_with_lock(self, **lock_fields):
        """A repo whose lock passes main()'s pre-cleanup memory gate."""
        import memory_backfill

        lib = _load_upgrade_lib()
        (self.root / ".wavefoundry" / "index").mkdir(parents=True, exist_ok=True)
        (self.root / "docs" / "waves").mkdir(parents=True, exist_ok=True)
        run_id = memory_backfill.ensure_run(self.root, "upgrade")
        memory_backfill.sync_inventory(self.root, run_id)
        memory_backfill.mark_indexed(self.root, run_id)
        lib.write_upgrade_lock(self.root, "1.15.9", "1.16.0")
        lib.update_upgrade_lock(
            self.root,
            memory_backfill_run_id=run_id,
            memory_backfill_state="indexed",
            **lock_fields,
        )
        return lib

    def test_refused_retry_keeps_failed_phase_and_partial_lists(self):
        """1v0r0 repair (F2): a RETRY of a failed retired-model cleanup whose
        authority revalidation refuses (`not_applicable`, e.g. an in-flight
        index build) must keep `failed_phase=retired_model_cleanup`, keep the
        preserved partial lists in the lock, and exit nonzero. Only a
        `complete` retry clears the failure."""
        partial_removed = ["fastembed:default:models--BAAI--bge-base-en-v1.5"]
        partial_failed = [
            "fastembed:default:models--BAAI--bge-small-en-v1.5|remove_failed"
        ]
        lib = self._cleanup_root_with_lock(
            failed_phase="retired_model_cleanup",
            failed_at="t",
            retired_model_cleanup_status="failed",
            retired_model_cleanup_removed=partial_removed,
            retired_model_cleanup_absent=["coreml:default:BAAI__bge-base-en-v1.5"],
            retired_model_cleanup_unowned=[],
            retired_model_cleanup_failed=partial_failed,
        )
        stdout, stderr = io.StringIO(), io.StringIO()
        with patch.object(
            self.mod,
            "_run_retired_model_cleanup",
            return_value=self.mod._retired_model_cleanup_result(),
        ), patch.object(self.mod, "_ensure_rendered_permissions_backstop"), \
                contextlib.redirect_stdout(stdout), \
                contextlib.redirect_stderr(stderr):
            with self.assertRaises(SystemExit) as caught:
                self.mod.main(["--root", str(self.root), "--cleanup"])
        self.assertEqual(caught.exception.code, 1)
        lock = lib.read_upgrade_lock(self.root)
        self.assertIsNotNone(lock, "the upgrade lock must be retained")
        self.assertEqual(lock.get("failed_phase"), "retired_model_cleanup")
        self.assertEqual(lock.get("retired_model_cleanup_status"), "failed")
        self.assertEqual(lock.get("retired_model_cleanup_removed"), partial_removed)
        self.assertEqual(lock.get("retired_model_cleanup_failed"), partial_failed)
        self.assertIn("retry refused", stderr.getvalue())
        self.assertIn("authority", stderr.getvalue())

    def test_first_run_not_applicable_cleanup_stays_benign(self):
        """1v0r0 repair (F2) boundary: with NO prior cleanup failure, a
        `not_applicable` result keeps the existing benign behavior (lock
        updated, cleanup proceeds to lock removal, exit zero)."""
        lib = self._cleanup_root_with_lock()
        stdout, stderr = io.StringIO(), io.StringIO()
        with patch.object(
            self.mod,
            "_run_retired_model_cleanup",
            return_value=self.mod._retired_model_cleanup_result(),
        ), patch.object(self.mod, "_ensure_rendered_permissions_backstop"), \
                contextlib.redirect_stdout(stdout), \
                contextlib.redirect_stderr(stderr):
            code = self.mod.main(["--root", str(self.root), "--cleanup"])
        self.assertEqual(code, 0, stdout.getvalue() + stderr.getvalue())
        self.assertIsNone(lib.read_upgrade_lock(self.root))


class Phase4PublisherGrantTests(unittest.TestCase):
    """Blocking Phase 4 children carry the value-bound publisher grant."""

    def setUp(self):
        self.mod = load_upgrade_module()
        self.lib = _load_upgrade_lib()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / ".wavefoundry").mkdir()
        (self.root / "setup_index.py").write_text("", encoding="utf-8")
        env_guard = patch.dict(os.environ, {}, clear=False)
        env_guard.start()
        self.addCleanup(env_guard.stop)
        os.environ.pop("WAVEFOUNDRY_UPGRADE_PUBLISHER_TOKEN", None)
        os.environ.pop("WAVEFOUNDRY_UPGRADE_PARENT_FINALIZE_RECEIPT", None)
        os.environ.pop("WAVEFOUNDRY_MEMORY_BACKFILL_RUN_ID", None)

    def _run_phase(self, fn_name, returncode=0):
        mock_proc = MagicMock(returncode=returncode)
        with patch.object(self.mod, "SCRIPTS_DIR", self.root), \
             patch("subprocess.run", return_value=mock_proc) as run_mock, \
             patch("subprocess.Popen") as popen_mock, \
             contextlib.redirect_stderr(io.StringIO()) as stderr:
            result = getattr(self.mod, fn_name)(self.root)
        return result, run_mock, popen_mock, stderr

    def test_update_children_granted_and_detached_child_suppressed(self):
        self.lib.write_upgrade_lock(self.root, "1.14.0", "1.15.0")
        result, run_mock, popen_mock, _ = self._run_phase("phase_index_update")
        self.assertTrue(result)
        token = self.lib.read_upgrade_lock(self.root).get("publisher_grant")
        self.assertTrue(token, "the runner must mint publisher_grant into the lock")
        self.assertEqual(len(run_mock.call_args_list), 2)
        for call in run_mock.call_args_list:  # docs child + graph child
            self.assertEqual(
                call.kwargs["env"]["WAVEFOUNDRY_UPGRADE_PUBLISHER_TOKEN"], token
            )
        popen_mock.assert_not_called()

    def test_detached_child_suppressed_even_when_bridge_exported_token(self):
        self.lib.write_upgrade_lock(self.root, "1.14.0", "1.15.0")
        self.lib.update_upgrade_lock(self.root, publisher_grant="bridge-token")
        os.environ["WAVEFOUNDRY_UPGRADE_PUBLISHER_TOKEN"] = "bridge-token"
        result, run_mock, popen_mock, _ = self._run_phase("phase_index_update")
        self.assertTrue(result)
        for call in run_mock.call_args_list:
            self.assertEqual(
                call.kwargs["env"]["WAVEFOUNDRY_UPGRADE_PUBLISHER_TOKEN"],
                "bridge-token",
            )
        popen_mock.assert_not_called()

    def test_rebuild_children_granted_and_detached_child_suppressed(self):
        self.lib.write_upgrade_lock(self.root, "1.14.0", "1.15.0")
        result, run_mock, popen_mock, _ = self._run_phase("phase_index_rebuild")
        self.assertTrue(result)
        token = self.lib.read_upgrade_lock(self.root).get("publisher_grant")
        self.assertTrue(token)
        for call in run_mock.call_args_list:
            self.assertEqual(
                call.kwargs["env"]["WAVEFOUNDRY_UPGRADE_PUBLISHER_TOKEN"], token
            )
        popen_mock.assert_not_called()

    def test_no_lock_means_no_grant_and_no_lock_creation(self):
        result, run_mock, _popen, _ = self._run_phase("phase_index_update")
        self.assertTrue(result)
        self.assertIsNone(self.lib.read_upgrade_lock(self.root))
        for call in run_mock.call_args_list:
            self.assertNotIn(
                "WAVEFOUNDRY_UPGRADE_PUBLISHER_TOKEN", call.kwargs["env"] or {}
            )

    def test_docs_child_failure_is_observed_not_swallowed(self):
        # Requirement 7 end-to-end stub boundary: subprocess (isolated_run)
        # exits non-zero; the observability chain reports False and the
        # failure text names the recovery pair.
        self.lib.write_upgrade_lock(self.root, "1.14.0", "1.15.0")
        result, _run, _popen, stderr = self._run_phase(
            "phase_index_update", returncode=7
        )
        self.assertFalse(result)
        err_text = stderr.getvalue()
        self.assertIn("Index publication FAILED", err_text)
        self.assertIn("index_build", err_text)
        self.assertIn("index_health", err_text)

    def test_rebuild_docs_child_failure_is_observed_not_swallowed(self):
        self.lib.write_upgrade_lock(self.root, "1.14.0", "1.15.0")
        result, _run, _popen, stderr = self._run_phase(
            "phase_index_rebuild", returncode=7
        )
        self.assertFalse(result)
        self.assertIn("Index publication FAILED", stderr.getvalue())

    def test_memory_bound_docs_child_failure_still_raises(self):
        self.lib.write_upgrade_lock(self.root, "1.14.0", "1.15.0")
        os.environ["WAVEFOUNDRY_MEMORY_BACKFILL_RUN_ID"] = "run-1"
        mock_proc = MagicMock(returncode=7)
        with patch.object(self.mod, "SCRIPTS_DIR", self.root), \
             patch("subprocess.run", return_value=mock_proc), \
             patch("subprocess.Popen"):
            with self.assertRaisesRegex(RuntimeError, "retryable"):
                self.mod.phase_index_update(self.root)

    def test_failed_publication_reaches_primary_sentinel(self):
        # End-to-end to the PRIMARY emit site: failing child exit -> observed
        # False -> sentinel index_update says publication failed + recovery.
        self.lib.write_upgrade_lock(self.root, "1.14.0", "1.15.0")
        published, _run, _popen, _ = self._run_phase(
            "phase_index_update", returncode=7
        )
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.mod._emit_primary_phase_summary(
                from_version="1.14.0", to_version="1.15.0", zip_path=None,
                pruned_count=0, root=None, index_published=published,
            )
        sentinel = self.mod.WAVE_UPGRADE_SUMMARY_SENTINEL
        summary = next(
            json.loads(line[len(sentinel):])
            for line in buf.getvalue().splitlines()
            if line.startswith(sentinel)
        )
        self.assertTrue(summary["index_update"].startswith("publication failed"))
        self.assertIn("index_health", summary["index_update"])

    def test_failed_publication_reaches_cleanup_sentinel(self):
        # End-to-end to the CLEANUP emit site: failing child exit -> observed
        # False -> lock records the outcome -> the cleanup derivation renders
        # the failed value (never success, never "not run").
        self.lib.write_upgrade_lock(self.root, "1.14.0", "1.15.0")
        published, _run, _popen, _ = self._run_phase(
            "phase_index_update", returncode=7
        )
        self.mod._record_index_publication_outcome(self.root, published)
        lock = self.lib.read_upgrade_lock(self.root)
        rebuilt = bool(lock.get("index_rebuilt_at"))
        failed = bool(lock.get("index_publication_failed"))
        self.assertFalse(rebuilt)
        self.assertTrue(failed)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.mod._print_operator_summary(
                from_version="1.14.0", to_version="1.15.0", zip_path=None,
                pruned_count=0, ran_index_rebuild=rebuilt, failed_phase=None,
                root=None, index_update_failed=failed,
            )
        sentinel = self.mod.WAVE_UPGRADE_SUMMARY_SENTINEL
        summary = next(
            json.loads(line[len(sentinel):])
            for line in buf.getvalue().splitlines()
            if line.startswith(sentinel)
        )
        self.assertTrue(summary["index_update"].startswith("publication failed"))
        self.assertIn("index_health", summary["index_update"])

    def test_cleanup_branch_derives_outcome_fields_from_lock(self):
        # Structural pin (same shape as the 1rych/1ryce source assertions):
        # the --cleanup handler derives _cl_index_failed from the lock and
        # passes index_update_failed into phase_cleanup.
        src = UPGRADE_PATH.read_text(encoding="utf-8")
        self.assertIn('bool(lock.get("index_publication_failed")) if lock else False', src)
        self.assertIn("index_update_failed=_cl_index_failed", src)
        # And both standalone writers record the OBSERVED outcome.
        self.assertIn("_record_index_publication_outcome(root, _ui_published)", src)
        self.assertIn("_record_index_publication_outcome(root, _ri_published)", src)


class PreIndexUpdateBridgeTests(unittest.TestCase):
    """Wave 1u44n (AC-3): the new pack's ``pre_index_update`` hook makes the
    fix effective on the upgrade that INSTALLS it, executing inside the old
    parent runner via ``_load_extension_module`` from a real zip."""

    def setUp(self):
        self.mod = load_upgrade_module()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / ".wavefoundry").mkdir()
        self.lock_path = self.root / ".wavefoundry" / "upgrade-in-progress.json"
        self.zip_path = self.root / "wavefoundry-1.15.0-test.zip"
        with zipfile.ZipFile(self.zip_path, "w") as zf:
            zf.write(
                SCRIPTS_ROOT / "upgrade_extensions.py",
                ".wavefoundry/framework/scripts/upgrade_extensions.py",
            )
        env_guard = patch.dict(os.environ, {}, clear=False)
        env_guard.start()
        self.addCleanup(env_guard.stop)
        os.environ.pop("WAVEFOUNDRY_UPGRADE_PUBLISHER_TOKEN", None)
        os.environ.pop("WAVEFOUNDRY_UPGRADE_PARENT_FINALIZE_RECEIPT", None)
        os.environ.pop("WAVEFOUNDRY_MEMORY_BACKFILL_RUN_ID", None)
        if str(SCRIPTS_ROOT) not in sys.path:
            sys.path.insert(0, str(SCRIPTS_ROOT))

    def _load_ext(self):
        with contextlib.redirect_stdout(io.StringIO()):
            ext = self.mod._load_extension_module(self.zip_path)
        self.assertIsNotNone(ext, "the fixture zip must yield the extension module")
        return ext

    def _ctx(self):
        return self.mod.UpgradeContext(
            self.root, "1.15.0+pfxp", "1.15.0", self.zip_path, True
        )

    def test_bridge_authorizes_non_owner_child_with_no_memory_run(self):
        # The pass/fail observable is post-hook ADMISSION at begin_build_epoch
        # for a simulated non-owner child (checkpoint pid -1, child-inherited
        # env), not merely that a flag or env var was set.
        import index_state_store

        self.lock_path.write_text(
            json.dumps({"current_phase": "index_update", "pid": -1}),
            encoding="utf-8",
        )
        ext = self._load_ext()
        ext.pre_index_update(self._ctx())
        lock = json.loads(self.lock_path.read_text(encoding="utf-8"))
        token = lock.get("publisher_grant")
        self.assertTrue(token, "the bridge must record publisher_grant in the checkpoint")
        self.assertEqual(
            os.environ.get("WAVEFOUNDRY_UPGRADE_PUBLISHER_TOKEN"), token
        )
        index_dir = self.root / ".wavefoundry" / "index"
        attempt = index_state_store.begin_build_epoch(index_dir, "docs")
        self.assertTrue(index_state_store.finalize_build_epoch(index_dir, attempt))

    def test_bridge_is_idempotent_and_noop_when_authorized(self):
        self.lock_path.write_text(
            json.dumps({"current_phase": "index_update", "pid": -1}),
            encoding="utf-8",
        )
        ext = self._load_ext()
        ext.pre_index_update(self._ctx())
        first_lock = self.lock_path.read_text(encoding="utf-8")
        first_token = os.environ["WAVEFOUNDRY_UPGRADE_PUBLISHER_TOKEN"]
        ext.pre_index_update(self._ctx())
        self.assertEqual(self.lock_path.read_text(encoding="utf-8"), first_lock)
        self.assertEqual(
            os.environ["WAVEFOUNDRY_UPGRADE_PUBLISHER_TOKEN"], first_token
        )

    def test_bridge_noop_without_a_lock(self):
        ext = self._load_ext()
        ext.pre_index_update(self._ctx())
        self.assertFalse(self.lock_path.exists())
        self.assertNotIn("WAVEFOUNDRY_UPGRADE_PUBLISHER_TOKEN", os.environ)

    def test_raising_bridge_is_absorbed_and_pause_branches_still_raise(self):
        # Fail-safety lives INSIDE the hook body: an actually-raising bridge
        # must not escape (the dispatcher would turn it into a fatal exit-3
        # retained-lock failure), while the INTENTIONAL ACTION_REQUIRED_EXIT
        # pause branches keep raising.
        self.lock_path.write_text(
            json.dumps({"current_phase": "index_update", "pid": -1}),
            encoding="utf-8",
        )
        ext = self._load_ext()
        with patch.object(
            ext,
            "_bridge_index_publisher_grant",
            side_effect=RuntimeError("bridge boom"),
        ):
            # No memory run id: the hook must return normally.
            ext.pre_index_update(self._ctx())
        self.assertNotIn("WAVEFOUNDRY_UPGRADE_PUBLISHER_TOKEN", os.environ)
        # With a memory run id and a genuinely paused run, the pause branch
        # still raises even while the bridge is broken.
        self.lock_path.write_text(
            json.dumps(
                {
                    "current_phase": "awaiting_memory_validation",
                    "pid": -1,
                    "memory_backfill_run_id": "run-1",
                }
            ),
            encoding="utf-8",
        )
        fake_backfill = MagicMock()
        fake_backfill.ACTION_REQUIRED_EXIT = 4
        fake_backfill.reconcile_index_publication.return_value = {
            "state": "awaiting_validation"
        }
        with patch.object(
            ext,
            "_bridge_index_publisher_grant",
            side_effect=RuntimeError("bridge boom"),
        ), patch.object(
            ext, "_installed_memory_backfill", return_value=fake_backfill
        ):
            with self.assertRaises(SystemExit) as raised:
                ext.pre_index_update(self._ctx())
        self.assertEqual(raised.exception.code, 4)


class PublicUpgradeReviewProtocolIntegrationTests(unittest.TestCase):
    """The real upgrade surface phase repairs existing project carriers."""

    def test_upgrade_surface_phase_refuses_claude_ancestor_before_external_write(self):
        mod = load_upgrade_module()
        import venv_bootstrap

        with tempfile.TemporaryDirectory() as temp_dir:
            outer = Path(temp_dir)
            root = (outer / "repo").resolve()
            outside = outer / "outside"
            root.mkdir()
            outside.mkdir()
            try:
                (root / ".claude").symlink_to(outside, target_is_directory=True)
            except OSError as exc:
                self.skipTest(f"directory symlinks unavailable: {exc}")

            with patch.object(mod, "_preferred_python", return_value=sys.executable), \
                 patch.object(venv_bootstrap, "ensure_python_resolves", return_value="ok"), \
                 patch.dict(os.environ, {"WAVEFOUNDRY_SKIP_PYTHON_HEAL": "1"}, clear=False), \
                 self.assertRaises(SystemExit) as raised:
                mod.phase_surface_rendering(root)

            self.assertEqual(raised.exception.code, 2)
            self.assertEqual(list(outside.rglob("*")), [])

    def test_upgrade_surface_phase_refuses_final_carrier_symlink_escape(self):
        mod = load_upgrade_module()
        import venv_bootstrap

        with tempfile.TemporaryDirectory() as temp_dir:
            outer = Path(temp_dir)
            root = (outer / "repo").resolve()
            outside = outer / "outside.md"
            target = root / "docs" / "agents" / "qa-reviewer.md"
            target.parent.mkdir(parents=True)
            outside.write_text("external sentinel\n", encoding="utf-8")
            target.symlink_to(outside)

            with patch.object(mod, "_preferred_python", return_value=sys.executable), \
                 patch.object(venv_bootstrap, "ensure_python_resolves", return_value="ok"), \
                 patch.dict(os.environ, {"WAVEFOUNDRY_SKIP_PYTHON_HEAL": "1"}, clear=False), \
                 self.assertRaises(SystemExit) as raised:
                mod.phase_surface_rendering(root)

            self.assertEqual(raised.exception.code, 2)
            self.assertEqual(outside.read_text(encoding="utf-8"), "external sentinel\n")

    def test_upgrade_surface_phase_refuses_dangling_native_wrapper_parent(self):
        mod = load_upgrade_module()
        import venv_bootstrap

        with tempfile.TemporaryDirectory() as temp_dir:
            outer = Path(temp_dir)
            root = (outer / "repo").resolve()
            outside = outer / "outside"
            (root / "docs" / "agents").mkdir(parents=True)
            (root / "docs" / "agents" / "guru.md").write_text("# Guru\n", encoding="utf-8")
            wrapper = root / ".codex" / "skills" / "auto-guru"
            wrapper.parent.mkdir(parents=True)
            outside.mkdir()
            wrapper.symlink_to(outside, target_is_directory=True)

            with patch.object(mod, "_preferred_python", return_value=sys.executable), \
                 patch.object(venv_bootstrap, "ensure_python_resolves", return_value="ok"), \
                 patch.dict(os.environ, {"WAVEFOUNDRY_SKIP_PYTHON_HEAL": "1"}, clear=False), \
                 self.assertRaises(SystemExit) as raised:
                mod.phase_surface_rendering(root)

            self.assertEqual(raised.exception.code, 2)
            self.assertFalse((outside / "SKILL.md").exists())

    def test_surface_phase_reconciles_stale_carrier_preserves_extensions_and_is_idempotent(self):
        mod = load_upgrade_module()
        import render_agent_surfaces as ras
        import review_policy
        import venv_bootstrap

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir).resolve()
            _stage_review_protocol_seeds(root)
            codex_config = root / ".codex" / "config.toml"
            codex_config.parent.mkdir(parents=True)
            operator_tail = (
                "[mcp_servers.wavefoundry]\n"
                'command = "python3"\n'
                'args = [".wavefoundry/framework/scripts/server.py"]\n\n'
                "[mcp_servers.wavefoundry.tools.wf_close_wave]\n"
                'approval_mode = "approve"\n'
            )
            codex_config.write_text(operator_tail, encoding="utf-8")
            target = root / "docs" / "agents" / "security-reviewer.md"
            target.parent.mkdir(parents=True)
            prefix = "# Project Security Reviewer\n\nproject-prefix\n\n"
            suffix = "\n\n## Project extension\n\n- preserve this exactly\n"
            target.write_text(
                prefix
                + ras.REVIEW_PROTOCOL_MARKER_BEGIN
                + "\nold protocol revision\n"
                + ras.REVIEW_PROTOCOL_MARKER_END
                + suffix,
                encoding="utf-8",
            )

            with patch.object(mod, "_preferred_python", return_value=sys.executable), \
                 patch.object(venv_bootstrap, "ensure_python_resolves", return_value="ok"), \
                 patch.dict(os.environ, {"WAVEFOUNDRY_SKIP_PYTHON_HEAL": "1"}, clear=False):
                mod.phase_surface_rendering(root)
                first = target.read_bytes()
                mod.phase_surface_rendering(root)

            text = first.decode("utf-8")
            self.assertTrue(text.startswith(prefix))
            self.assertTrue(text.endswith(suffix))
            self.assertNotIn("old protocol revision", text)
            self.assertIn("four-way actionability gate", text)
            for rel in (
                "docs/agents/qa-reviewer.md",
                "docs/prompts/review-wave.prompt.md",
                "docs/prompts/create-wave.prompt.md",
                "docs/contributing/review-and-evals.md",
            ):
                created = root / rel
                self.assertTrue(created.is_file(), rel)
                created_text = created.read_text(encoding="utf-8")
                self.assertIn(ras.REVIEW_PROTOCOL_MARKER_BEGIN, created_text)
                self.assertNotIn("waveframework:", created_text)
                self.assertNotIn("wavefoundry:context-efficiency", created_text)
            self.assertIn(
                "zero unintended skips",
                (root / "docs" / "agents" / "qa-reviewer.md").read_text(encoding="utf-8"),
            )
            _assert_review_protocol_contract(self, root)
            self.assertEqual(target.read_bytes(), first)
            self.assertFalse(
                (root / "docs" / "agents" / "guru.md").exists(),
                "upgrade reconciliation must run before the Guru-availability guard",
            )
            upgraded_codex = codex_config.read_text(encoding="utf-8")
            self.assertIn("generated by render_platform_surfaces.py", upgraded_codex)
            self.assertIn(
                "[mcp_servers.wavefoundry.tools.wf_close_wave]",
                upgraded_codex,
                "upgrade must preserve operator-authored Codex configuration",
            )

    def test_surface_phase_rewrites_stale_host_launchers_in_one_pass(self):
        """1tjjk/1tjjl: existing projects converge during the first upgrade render."""
        mod = load_upgrade_module()
        import venv_bootstrap

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir).resolve()
            _stage_review_protocol_seeds(root)
            stale = 'python3 ".wavefoundry/old-relative.py"'
            claude_stale = 'python3 ".claude/hooks/pre-edit.py"'
            (root / ".claude").mkdir()
            (root / ".claude" / "settings.json").write_text(
                json.dumps({"hooks": {"PreToolUse": [{"hooks": [{"type": "command", "command": claude_stale}]}]}}),
                encoding="utf-8",
            )
            (root / ".mcp.json").write_text(
                json.dumps({"mcpServers": {"wavefoundry": {"command": "python3", "args": ["old.py"]}}}),
                encoding="utf-8",
            )
            (root / ".github" / "hooks").mkdir(parents=True)
            (root / ".github" / "copilot-instructions.md").write_text("", encoding="utf-8")
            (root / ".github" / "hooks" / "hooks.json").write_text(
                json.dumps({"version": 1, "hooks": {"preToolUse": [{"type": "command", "bash": stale}]}}),
                encoding="utf-8",
            )
            (root / ".windsurf").mkdir()
            (root / ".windsurf" / "hooks.json").write_text(
                json.dumps({"hooks": {"pre_write_code": [{"command": stale}]}}),
                encoding="utf-8",
            )
            (root / ".junie").mkdir()
            (root / ".junie" / "guidelines.md").write_text("", encoding="utf-8")

            with patch.object(mod, "_preferred_python", return_value=sys.executable), \
                 patch.object(venv_bootstrap, "ensure_python_resolves", return_value="ok"), \
                 patch.dict(os.environ, {"WAVEFOUNDRY_SKIP_PYTHON_HEAL": "1"}, clear=False):
                mod.phase_surface_rendering(root)

            claude = json.loads((root / ".claude" / "settings.json").read_text(encoding="utf-8"))
            self.assertIn(
                "CLAUDE_PROJECT_DIR",
                claude["hooks"]["PreToolUse"][0]["hooks"][0]["command"],
            )
            # 1v7a2: the MCP stanza converges on the PATH form, while the hook
            # assertion directly above still requires CLAUDE_PROJECT_DIR. That
            # contrast is the point and is asserted in one place deliberately:
            # hooks are invoked by the host from an unknown cwd and their
            # failure was reproduced in 1tjjk-bug, whereas an MCP server is
            # spawned once per session by a client that supplies the workspace
            # root, and 1tjjl-bug recorded that exposure as latent. This is also
            # the upgrade-side half of AC-5: an existing project carrying the
            # inline launcher must converge on the first upgrade render.
            claude_mcp = json.loads((root / ".mcp.json").read_text(encoding="utf-8"))
            self.assertEqual(
                claude_mcp["mcpServers"]["wavefoundry"]["args"],
                [".wavefoundry/framework/scripts/server.py"],
            )
            copilot = json.loads((root / ".github" / "hooks" / "hooks.json").read_text(encoding="utf-8"))
            copilot_pre = copilot["hooks"]["preToolUse"][0]
            self.assertEqual(copilot_pre["cwd"], ".")
            self.assertEqual(copilot_pre["bash"], copilot_pre["powershell"])
            windsurf = json.loads((root / ".windsurf" / "hooks.json").read_text(encoding="utf-8"))
            self.assertEqual(
                windsurf["hooks"]["pre_write_code"][0]["working_directory"], "."
            )
            junie = json.loads((root / ".junie" / "mcp" / "mcp.json").read_text(encoding="utf-8"))
            self.assertEqual(
                junie["mcpServers"]["wavefoundry"]["args"],
                ["../../.wavefoundry/framework/scripts/server.py"],
            )
            self.assertTrue((root / ".codex" / "config.toml").is_file())

    def test_full_upgrade_main_reaches_real_surface_phase_for_missing_carriers(self):
        """Negative-control complement: exercise main, not phase helper only."""

        mod = load_upgrade_module()
        import render_agent_surfaces as ras
        import memory_records
        import review_policy
        import venv_bootstrap

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir).resolve()
            (root / ".wavefoundry").mkdir()
            _stage_review_protocol_seeds(root)
            (root / "docs").mkdir()
            (root / "docs" / "workflow-config.json").write_text("{}\n", encoding="utf-8")
            historical = root / "docs" / "waves" / "abcde historical" / "wave.md"
            historical.parent.mkdir(parents=True)
            historical.write_bytes(
                b"# Historical target wave\n\nproject-authored bytes: do not parse or rewrite\n"
            )
            historical_snapshot = historical.read_bytes()
            historical_events = historical.parent / "events.jsonl"
            historical_events.write_bytes(b'{"historical":true,"opaque":"keep"}\n')
            historical_events_snapshot = historical_events.read_bytes()
            memory_archive = root / "docs" / "agents" / "memory" / "archive" / "historic.md"
            memory_archive.parent.mkdir(parents=True)
            memory_archive.write_bytes(b"historical memory body\n")
            memory_register = root / "docs" / "agents" / "memory-archive.md"
            memory_register.write_bytes(b"# Memory Archive\n\nproject history\n")
            purge_dispositions = root / ".wavefoundry" / "memory-purge-dispositions.json"
            purge_dispositions.write_bytes(
                b'{"schema_version":1,"source_event_sha256":["aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"]}\n'
            )
            memory_snapshot = {
                memory_archive: memory_archive.read_bytes(),
                memory_register: memory_register.read_bytes(),
                purge_dispositions: purge_dispositions.read_bytes(),
            }
            prompt_root = root / "docs" / "prompts"
            upgrade_prompt = prompt_root / "upgrade-wavefoundry.prompt.md"
            upgrade_prompt.parent.mkdir(parents=True, exist_ok=True)
            upgrade_prefix = "# Project Upgrade\n\nproject prefix\n\n"
            upgrade_suffix = "\n\n## Project extension\n\nkeep exactly\n"
            old_policy_block = review_policy.UPGRADE_POLICY_BLOCK.replace(
                "**Review memories**", "**Old memory command**"
            )
            upgrade_prompt.write_text(
                upgrade_prefix + old_policy_block + upgrade_suffix,
                encoding="utf-8",
            )

            def assert_carriers_before_index(_root):
                self.assertEqual(_root, root)
                for rel in (
                    "docs/agents/qa-reviewer.md",
                    "docs/prompts/create-wave.prompt.md",
                    "docs/prompts/review-wave.prompt.md",
                    "docs/contributing/review-and-evals.md",
                ):
                    self.assertTrue((root / rel).is_file(), f"{rel} must exist before index update")

            with patch.object(mod, "phase_preflight", return_value=(None, None, None)), \
                 patch.object(mod, "_load_extension_module", return_value=None), \
                 patch.object(mod, "_run_hook"), \
                 patch.object(mod, "_snapshot_pre_extract_chunker_versions", return_value={}), \
                 patch.object(mod, "_snapshot_pre_extract_versions", return_value={}), \
                 patch.object(mod, "_stamp_manifest_revision", return_value=False), \
                 patch.object(mod, "phase_pruning", return_value=0), \
                 patch.object(
                     memory_records,
                     "migrate_legacy_memory_pointers",
                     wraps=memory_records.migrate_legacy_memory_pointers,
                 ) as pointer_migration, \
                 patch.object(mod, "materialize_secrets_policy", return_value="ok"), \
                 patch.object(mod, "materialize_lifecycle_policy", return_value="ok"), \
                 patch.object(mod, "phase_docs_gate"), \
                 patch.object(mod, "phase_index_update", side_effect=assert_carriers_before_index), \
                 patch.object(mod, "_emit_primary_summary_via_delegate_or_fallback"), \
                 patch.object(venv_bootstrap, "ensure_python_resolves", return_value="ok"), \
                 patch.dict(os.environ, {"WAVEFOUNDRY_SKIP_PYTHON_HEAL": "1"}, clear=False):
                self.assertEqual(mod.main(["--root", str(root), "--yes"]), 0)

            self.assertEqual(pointer_migration.call_count, 1)

            for rel in (
                "docs/agents/code-reviewer.md",
                "docs/agents/qa-reviewer.md",
                "docs/prompts/review-wave.prompt.md",
                "docs/prompts/create-wave.prompt.md",
                "docs/contributing/review-and-evals.md",
            ):
                path = root / rel
                self.assertTrue(path.is_file(), rel)
                path_text = path.read_text(encoding="utf-8")
                self.assertIn(ras.REVIEW_PROTOCOL_MARKER_BEGIN, path_text)
                self.assertNotIn("waveframework:", path_text)
                self.assertNotIn("wavefoundry:context-efficiency", path_text)
            _assert_review_protocol_contract(self, root)
            create_text = (
                root / "docs" / "prompts" / "create-wave.prompt.md"
            ).read_text(encoding="utf-8")
            self.assertIn("review-evidence-source: events.jsonl", create_text)
            self.assertEqual(
                create_text.count(ras.CONTEXT_EFFICIENCY_CARRIER_MARKER_BEGIN), 1
            )
            self.assertEqual(
                create_text.count(ras.CONTEXT_EFFICIENCY_CARRIER_MARKER_END), 1
            )
            self.assertIn(ras._context_efficiency_carrier_block(), create_text)
            self.assertNotIn("review-evidence-protocol: 1", create_text)
            self.assertNotIn("```jsonl", create_text)
            self.assertEqual(historical.read_bytes(), historical_snapshot)
            self.assertEqual(historical_events.read_bytes(), historical_events_snapshot)
            self.assertEqual(
                {path: path.read_bytes() for path in memory_snapshot},
                memory_snapshot,
            )
            upgraded_policy = upgrade_prompt.read_text(encoding="utf-8")
            self.assertTrue(upgraded_policy.startswith(upgrade_prefix))
            self.assertTrue(upgraded_policy.endswith(upgrade_suffix))
            self.assertIn("**Review memories**", upgraded_policy)
            self.assertNotIn("**Old memory command**", upgraded_policy)
            for prompt_name in (
                "create-wave.prompt.md",
                "prepare-wave.prompt.md",
                "implement-wave.prompt.md",
                "review-wave.prompt.md",
                "close-wave.prompt.md",
                "memory-review.prompt.md",
            ):
                self.assertTrue(prompt_root.joinpath(prompt_name).is_file())
                self.assertGreater(
                    prompt_root.joinpath(prompt_name).stat().st_size,
                    500,
                )
            self.assertIn(
                ".wavefoundry/logs/",
                (root / ".gitignore").read_text(encoding="utf-8"),
            )
            self.assertFalse(
                (root / ".wavefoundry" / "logs" / "context-efficiency.sqlite").exists()
            )
            self.assertFalse(
                (
                    root
                    / ".wavefoundry"
                    / "locks"
                    / "producers"
                ).exists()
            )
    def test_full_upgrade_extracts_compact_review_authoring_into_target_project(self):
        """A real upgrade extraction replaces the target's old server/protocol modules."""

        mod = load_upgrade_module()

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir).resolve()
            scripts = root / ".wavefoundry" / "framework" / "scripts"
            scripts.mkdir(parents=True)
            scripts.joinpath("review_evidence.py").write_text("# old protocol\n", encoding="utf-8")
            scripts.joinpath("server_impl.py").write_text("# old server\n", encoding="utf-8")
            historical = root / "docs" / "waves" / "abcde historical" / "wave.md"
            historical.parent.mkdir(parents=True)
            historical.write_bytes(b"# Historical target wave\n\nopaque sentinel\n")
            historical_snapshot = historical.read_bytes()
            zip_path = root / "wavefoundry-upgrade.zip"
            with zipfile.ZipFile(zip_path, "w") as zf:
                for name in (
                    "review_evidence.py",
                    "review_policy.py",
                    "gardener_metadata.py",
                    "lifecycle_lock.py",
                    "publication_control.py",
                    "public_contract.py",
                    "server_impl.py",
                    "context_efficiency.py",
                    "score_context_efficiency_pairs.py",
                    "memory_backfill.py",
                    "memory_cli.py",
                    "runtime_lock.py",
                    "dashboard_lib.py",
                ):
                    zf.writestr(
                        f".wavefoundry/framework/scripts/{name}",
                        SCRIPTS_ROOT.joinpath(name).read_text(encoding="utf-8"),
                    )
                for relative in (
                    "dashboard/ds/wfds.js",
                    "dashboard/dashboard.css",
                ):
                    zf.writestr(
                        f".wavefoundry/framework/{relative}",
                        SCRIPTS_ROOT.parent.joinpath(relative).read_text(
                            encoding="utf-8"
                        ),
                    )
            with patch.object(
                mod,
                "phase_preflight",
                return_value=("1.12.0", "1.13.0", zip_path),
            ), patch.object(
                mod, "_stage_pack_for_consumption", return_value=zip_path
            ), patch.object(mod, "_load_extension_module", return_value=None), patch.object(
                mod, "_run_hook"
            ), patch.object(
                mod, "_snapshot_pre_extract_chunker_versions", return_value={}
            ), patch.object(
                mod, "_snapshot_pre_extract_versions", return_value={}
            ), patch.object(
                mod, "_tree_already_at", return_value=False
            ), patch.object(
                mod, "_detect_version_transitions", return_value=[]
            ), patch.object(
                mod, "_warn_if_no_version_baseline", return_value=False
            ), patch.object(
                mod, "phase_surface_rendering"
            ), patch.object(
                mod, "_stamp_manifest_revision", return_value=False
            ), patch.object(
                mod, "phase_pruning", return_value=0
            ), patch.object(
                mod, "materialize_secrets_policy", return_value="ok"
            ), patch.object(
                mod, "materialize_lifecycle_policy", return_value="ok"
            ), patch.object(
                mod, "phase_docs_gate"
            ), patch.object(
                mod, "phase_index_update"
            ), patch.object(
                mod, "_emit_primary_summary_via_delegate_or_fallback"
            ):
                self.assertEqual(mod.main(["--root", str(root), "--yes"]), 0)

            self.assertIn(
                "def build_compact_review_event(",
                scripts.joinpath("review_evidence.py").read_text(encoding="utf-8"),
            )
            self.assertIn(
                "def wf_review_event(",
                scripts.joinpath("server_impl.py").read_text(encoding="utf-8"),
            )
            self.assertIn(
                "EVENTS_FILENAME = \"events.jsonl\"",
                scripts.joinpath("review_evidence.py").read_text(encoding="utf-8"),
            )
            self.assertIn(
                "class ProcessTelemetry",
                scripts.joinpath("context_efficiency.py").read_text(
                    encoding="utf-8"
                ),
            )
            telemetry_source = scripts.joinpath(
                "context_efficiency.py"
            ).read_text(encoding="utf-8")
            self.assertIn("PRODUCER_LEASE_RELATIVE_DIR", telemetry_source)
            self.assertIn("CREATE TABLE IF NOT EXISTS producer_state", telemetry_source)
            self.assertIn("def compact_published_wave(", telemetry_source)
            self.assertIn(
                "def score_pairs",
                scripts.joinpath(
                    "score_context_efficiency_pairs.py"
                ).read_text(encoding="utf-8"),
            )
            self.assertFalse(
                scripts.parent.joinpath(
                    "evals", "context-efficiency-pairs.schema.json"
                ).is_file()
            )
            self.assertEqual(historical.read_bytes(), historical_snapshot)
            self.assertFalse((historical.parent / "events.jsonl").exists())
            # Execute the newly extracted upgrade assets. Source-substring
            # presence alone does not prove that an upgraded target can load
            # the projector/backfill modules or run the shared renderer.
            probe = r"""
import json, sys
import types
from pathlib import Path
scripts = Path(sys.argv[1])
root = Path(sys.argv[2])
sys.path.insert(0, str(scripts))
import memory_backfill
import review_evidence
# The focused parser probe does not exercise dashboard process discovery; the
# real installed tree supplies these modules, while this deliberately minimal
# upgrade archive stubs only the unused imports needed to load dashboard_lib.
sys.modules.setdefault("server", types.ModuleType("server"))
sys.modules.setdefault("subprocess_util", types.ModuleType("subprocess_util"))
import dashboard_lib
rendered = review_evidence.render_review_status_projection(
    "# Wave\n\nStatus: implementing\n\n## Review Evidence\n\n",
    [],
    ["operator-signoff"],
)
acs = dashboard_lib._parse_ac_items(
    "- [x] AC-1: upgraded first line\n  upgraded continuation\n",
    "| AC | Priority | Rationale |\n| --- | --- | --- |\n| AC-1 | required | Core. |\n",
    "planned",
)
tasks = dashboard_lib._parse_tasks(
    "- [ ] upgraded task\n  upgraded task continuation\n",
    "planned",
)
print(json.dumps({
    "status_marker": "<!-- wave:review-status begin -->" in rendered,
    "closed_waves": len(memory_backfill.inventory_closed_waves(root)),
    "ac_text": acs[0]["text"],
    "ac_priority": acs[0]["priority"],
    "task_text": tasks["items"][0]["label"],
}))
"""
            executed = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    "-c",
                    probe,
                    str(scripts),
                    str(root),
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
            self.assertEqual(executed.returncode, 0, executed.stderr)
            executed_out = json.loads(executed.stdout)
            self.assertTrue(executed_out["status_marker"])
            self.assertEqual(executed_out["closed_waves"], 1)
            self.assertEqual(
                executed_out["ac_text"],
                "AC-1: upgraded first line upgraded continuation",
            )
            self.assertEqual(executed_out["ac_priority"], "required")
            self.assertEqual(
                executed_out["task_text"],
                "upgraded task upgraded task continuation",
            )
            if shutil.which("node"):
                renderer = scripts.parent / "dashboard" / "ds" / "wfds.js"
                node_probe = r"""
const fs = require("fs"), vm = require("vm");
function createElement(type, props, ...children) {
  return {type, props: props || {}, children: children.flat()};
}
const root = {React: {createElement, useState(){}, useEffect(){}, useRef(){}, useCallback(){}}};
vm.runInNewContext(fs.readFileSync(process.argv[1], "utf8"),
  {window: root, globalThis: root, console});
const nodes = root.WFDS.renderMarkdownish(
  "<!-- wave:test begin -->\nSoft wrapped\nparagraph.\n<!-- wave:test end -->"
);
function text(n) { return typeof n === "string" ? n : (n.children || []).map(text).join(""); }
process.stdout.write(JSON.stringify(nodes.map(text)));
"""
                node = subprocess.run(
                    ["node", "-e", node_probe, str(renderer)],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                self.assertEqual(node.returncode, 0, node.stderr)
                self.assertEqual(json.loads(node.stdout), ["Soft wrapped paragraph."])

    def test_full_upgrade_known_bad_unwired_surface_phase_is_detected_before_index(self):
        """The integration fixture fails against the old helper-present-but-unwired behavior."""

        mod = load_upgrade_module()
        import venv_bootstrap

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir).resolve()
            (root / ".wavefoundry" / "framework" / "seeds").mkdir(parents=True)
            (root / "docs").mkdir()
            (root / "docs" / "workflow-config.json").write_text("{}\n", encoding="utf-8")

            def detect_missing_carriers(_root):
                self.assertFalse((root / "docs" / "agents" / "qa-reviewer.md").exists())
                raise AssertionError("known-bad upgrade reached index before review carriers")

            with patch.object(mod, "phase_preflight", return_value=(None, None, None)), \
                 patch.object(mod, "_load_extension_module", return_value=None), \
                 patch.object(mod, "_run_hook"), \
                 patch.object(mod, "_snapshot_pre_extract_chunker_versions", return_value={}), \
                 patch.object(mod, "_snapshot_pre_extract_versions", return_value={}), \
                 patch.object(mod, "phase_surface_rendering", return_value=None), \
                 patch.object(mod, "_stamp_manifest_revision", return_value=False), \
                 patch.object(mod, "phase_pruning", return_value=0), \
                 patch.object(mod, "materialize_secrets_policy", return_value="ok"), \
                 patch.object(mod, "materialize_lifecycle_policy", return_value="ok"), \
                 patch.object(mod, "phase_docs_gate"), \
                 patch.object(mod, "phase_index_update", side_effect=detect_missing_carriers), \
                 patch.object(venv_bootstrap, "ensure_python_resolves", return_value="ok"), \
                 patch.dict(os.environ, {"WAVEFOUNDRY_SKIP_PYTHON_HEAL": "1"}, clear=False):
                with self.assertRaisesRegex(AssertionError, "known-bad upgrade"):
                    mod.main(["--root", str(root), "--yes"])


# ---------------------------------------------------------------------------
# Upgrade log file (12r21)
# ---------------------------------------------------------------------------

class UpgradeLogTests(unittest.TestCase):
    """Tests for _open_log / _close_log / _log tee behaviour."""

    def setUp(self):
        self.mod = load_upgrade_module()
        self.mod._close_log()   # defensive: ensure clean global state entering this test
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / ".wavefoundry").mkdir()

    def tearDown(self):
        self.mod._close_log()   # release handle so tmp dir can be deleted
        self.tmp.cleanup()

    def _log_path(self) -> Path:
        return self.root / ".wavefoundry" / "logs" / "upgrade.log"

    def test_log_file_created_on_open(self):
        self.mod._open_log(self.root, mode="w")
        self.mod._close_log()
        self.assertTrue(self._log_path().exists())

    def test_log_contains_message(self):
        self.mod._open_log(self.root, mode="w")
        self.mod._log("hello from test")
        self.mod._close_log()
        content = self._log_path().read_text(encoding="utf-8")
        self.assertIn("hello from test", content)

    def test_log_contains_timestamp(self):
        self.mod._open_log(self.root, mode="w")
        self.mod._log("timestamped line")
        self.mod._close_log()
        content = self._log_path().read_text(encoding="utf-8")
        # Timestamps are absolute UTC date-time stamps.
        import re
        self.assertRegex(content, r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+00:00 timestamped line")

    def test_err_also_written_to_log(self):
        self.mod._open_log(self.root, mode="w")
        self.mod._err("something went wrong")
        self.mod._close_log()
        content = self._log_path().read_text(encoding="utf-8")
        self.assertIn("ERROR: something went wrong", content)

    def test_append_mode_preserves_prior_content(self):
        self.mod._open_log(self.root, mode="w")
        self.mod._log("phase 0 line")
        self.mod._close_log()

        self.mod._open_log(self.root, mode="a")
        self.mod._log("phase 4 line")
        self.mod._close_log()

        content = self._log_path().read_text(encoding="utf-8")
        self.assertIn("phase 0 line", content)
        self.assertIn("phase 4 line", content)

    def test_write_mode_truncates_prior_log(self):
        self.mod._open_log(self.root, mode="w")
        self.mod._log("old content")
        self.mod._close_log()

        self.mod._open_log(self.root, mode="w")
        self.mod._log("new content")
        self.mod._close_log()

        content = self._log_path().read_text(encoding="utf-8")
        self.assertNotIn("old content", content)
        self.assertIn("new content", content)

    def test_no_log_written_when_not_open(self):
        """_log() is a no-op for the file when log is closed."""
        self.mod._log("should not appear in file")
        self.assertFalse(self._log_path().exists())

    def test_upgrade_log_path_helper(self):
        expected = self.root / ".wavefoundry" / "logs" / "upgrade.log"
        self.assertEqual(self.mod.upgrade_log_path(self.root), expected)


# ---------------------------------------------------------------------------
# 1.4.x → 1.5.0 migration helpers (wave 1p35d / 1p3ay)
# ---------------------------------------------------------------------------

def _load_upgrade_extensions():
    """Load the canonical upgrade_extensions.py (not from a zip)."""
    import importlib.util
    scripts_root = Path(__file__).resolve().parents[1]
    path = scripts_root / "upgrade_extensions.py"
    spec = importlib.util.spec_from_file_location("upgrade_extensions_canonical", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class RuntimeLockCutoverMigrationTests(unittest.TestCase):
    """1sxxx: packaged pre-extract migration performs one canonical cutover."""

    def setUp(self):
        self.ext = _load_upgrade_extensions()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()
        self.wf = self.root / ".wavefoundry"
        self.wf.mkdir(parents=True)
        self.upgrade_state = self.wf / "upgrade-in-progress.json"
        self.upgrade_state.write_text('{"pid": 1}\n', encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def _fake_server(self):
        return MagicMock(
            wf_stop_dashboard_response=MagicMock(
                return_value={
                    "status": "ok",
                    "data": {"stopped": True, "already_stopped": False},
                }
            )
        )

    def test_cutover_stops_dashboard_removes_old_carriers_and_persists_restart(self):
        (self.wf / "dashboard-server.lock").write_text(
            '{"pid": 42, "port": 43210}\n',
            encoding="utf-8",
        )
        (self.wf / "dashboard-start.lock").write_bytes(b"")
        (self.wf / "review-evidence-adoptions.lock").write_bytes(b"")
        producers = self.wf / "logs" / "context-efficiency-producers"
        producers.mkdir(parents=True)
        (producers / "producer.lock").write_bytes(b"")

        with patch.dict(sys.modules, {"server_impl": self._fake_server()}):
            self.ext._cut_over_runtime_locks(self.root)

        for name, _offset in self.ext._LEGACY_RUNTIME_LOCKS:
            self.assertFalse((self.wf / name).exists())
        self.assertFalse(producers.exists())
        state = json.loads(self.upgrade_state.read_text(encoding="utf-8"))
        self.assertTrue(state["runtime_lock_cutover_complete"])
        self.assertTrue(state["dashboard_restart_pending"])
        self.assertEqual(state["dashboard_restart_port"], 43210)
        self.assertFalse((self.wf / "locks").exists())

    def test_cutover_falls_back_to_pre_rename_dashboard_stop_symbol(self):
        """1t49m: the hook runs from the NEW archive against an INSTALLED
        server_impl that may predate the wf_ tool rename (field report:
        upgrading across the rename aborted at pre_extract)."""
        import types

        calls: list[Path] = []

        def old_stop(root):
            calls.append(root)
            return {
                "status": "ok",
                "data": {"stopped": False, "already_stopped": True},
            }

        pre_rename = types.SimpleNamespace(wave_dashboard_stop_response=old_stop)
        with patch.dict(sys.modules, {"server_impl": pre_rename}):
            stopped, port = self.ext._stop_dashboard_for_lock_cutover(self.root)
        self.assertFalse(stopped)
        self.assertIsNone(port)
        self.assertEqual(calls, [self.root])

    def test_cutover_prefers_current_symbol_when_both_exist(self):
        import types

        def new_stop(root):
            return {"status": "ok", "data": {"stopped": True}}

        def old_stop(root):
            raise AssertionError("retired symbol must not be preferred")

        both = types.SimpleNamespace(
            wf_stop_dashboard_response=new_stop,
            wave_dashboard_stop_response=old_stop,
        )
        with patch.dict(sys.modules, {"server_impl": both}):
            stopped, _port = self.ext._stop_dashboard_for_lock_cutover(self.root)
        self.assertTrue(stopped)

    def test_cutover_fails_legibly_when_no_stop_symbol_exists(self):
        import types

        with patch.dict(sys.modules, {"server_impl": types.SimpleNamespace()}):
            with self.assertRaisesRegex(
                RuntimeError, "wave_dashboard_stop_response"
            ):
                self.ext._stop_dashboard_for_lock_cutover(self.root)

    @unittest.skipIf(os.name == "nt", "POSIX flock contention fixture")
    def test_held_old_adoption_lock_blocks_without_deleting_carrier(self):
        import fcntl

        adoption = self.wf / "review-evidence-adoptions.lock"
        handle = adoption.open("a+b")
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            with patch.dict(sys.modules, {"server_impl": self._fake_server()}):
                with self.assertRaisesRegex(RuntimeError, "still held"):
                    self.ext._cut_over_runtime_locks(self.root)
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            handle.close()
        self.assertTrue(adoption.exists())
        state = json.loads(self.upgrade_state.read_text(encoding="utf-8"))
        self.assertFalse(state["runtime_lock_cutover_complete"])

    @unittest.skipIf(os.name == "nt", "POSIX flock contention fixture")
    def test_held_old_producer_blocks_before_any_old_carrier_is_deleted(self):
        import fcntl

        adoption = self.wf / "review-evidence-adoptions.lock"
        adoption.write_bytes(b"")
        producers = self.wf / "logs" / "context-efficiency-producers"
        producers.mkdir(parents=True)
        lease = producers / "producer.lock"
        handle = lease.open("a+b")
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            with patch.dict(sys.modules, {"server_impl": self._fake_server()}):
                with self.assertRaisesRegex(RuntimeError, "producer lease"):
                    self.ext._cut_over_runtime_locks(self.root)
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            handle.close()
        self.assertTrue(adoption.exists())
        self.assertTrue(lease.exists())
        state = json.loads(self.upgrade_state.read_text(encoding="utf-8"))
        self.assertFalse(state["runtime_lock_cutover_complete"])


class FromVersionPredatesTests(unittest.TestCase):
    """AC-2, AC-3: version-gate correctness for 1.4.x → 1.5.0 migration."""

    def setUp(self):
        self.ext = _load_upgrade_extensions()

    def test_pre_1_5_0_semver_strings_return_true(self):
        for v in ("1.0.0", "1.3.32", "1.4.0", "1.4.1", "1.4.1+p347", "0.9.0"):
            self.assertTrue(
                self.ext._from_version_predates(v, "1.5.0"),
                f"{v} should be older than 1.5.0",
            )

    def test_at_or_after_1_5_0_returns_false(self):
        for v in ("1.5.0", "1.5.0+x", "1.5.1", "1.6.0", "2.0.0", "10.0.0"):
            self.assertFalse(
                self.ext._from_version_predates(v, "1.5.0"),
                f"{v} should be at or after 1.5.0",
            )

    def test_unknown_or_unparseable_returns_true_safe_default(self):
        """Idempotent migrations are safe to re-run; treating unknown as 'old'
        means we never silently skip migration on a state that needs it."""
        for v in (None, "", "2026-05-19a", "garbage", "v1.5.0"):
            self.assertTrue(
                self.ext._from_version_predates(v, "1.5.0"),
                f"{v!r} should be treated as predating (safe default)",
            )


class RoleBackfillMigrationTests(unittest.TestCase):
    """AC-4 through AC-6: Role: backfill on docs/agents/*.md."""

    def setUp(self):
        self.ext = _load_upgrade_extensions()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()
        (self.root / "docs" / "agents").mkdir(parents=True)
        (self.root / "docs" / "agents" / "specialists").mkdir(parents=True)
        (self.root / "docs" / "agents" / "personas").mkdir(parents=True)
        (self.root / "docs" / "agents" / "journals").mkdir(parents=True)

    def tearDown(self):
        self.tmp.cleanup()

    def _write(self, rel: str, body: str) -> Path:
        path = self.root / rel
        path.write_text(body, encoding="utf-8")
        return path

    def test_inserts_role_when_missing_after_status_line(self):
        path = self._write(
            "docs/agents/code-reviewer.md",
            "# Code Reviewer\n\n"
            "Owner: Engineering\n"
            "Status: active\n"
            "Category: review\n"
            "Last verified: 2026-05-01\n\n"
            "## Operating Identity\n\nReviews code.\n",
        )
        modified = self.ext._backfill_role_field_on_agent_docs(self.root)
        self.assertEqual(modified, ["docs/agents/code-reviewer.md"])
        text = path.read_text(encoding="utf-8")
        self.assertIn("Role: code-reviewer", text)
        # Inserted right after Status:
        self.assertRegex(text, r"Status: active\nRole: code-reviewer\nCategory: review")

    def test_falls_back_to_owner_anchor_when_no_status_line(self):
        path = self._write(
            "docs/agents/specialists/my-spec.md",
            "# My Spec\n\n"
            "Owner: Engineering\n"
            "Category: specialist\n"
            "Last verified: 2026-05-01\n\n"
            "## Identity\n\nFoo.\n",
        )
        modified = self.ext._backfill_role_field_on_agent_docs(self.root)
        self.assertEqual(modified, ["docs/agents/specialists/my-spec.md"])
        text = path.read_text(encoding="utf-8")
        self.assertRegex(text, r"Owner: Engineering\nRole: my-spec\nCategory: specialist")

    def test_already_present_role_not_modified(self):
        body = (
            "# Existing\n\n"
            "Owner: Engineering\n"
            "Status: active\n"
            "Role: existing\n"
            "Category: review\n\n"
            "## Identity\n\nFoo.\n"
        )
        path = self._write("docs/agents/existing.md", body)
        original = path.read_text(encoding="utf-8")
        modified = self.ext._backfill_role_field_on_agent_docs(self.root)
        self.assertEqual(modified, [])
        self.assertEqual(path.read_text(encoding="utf-8"), original)

    def test_exempt_filenames_skipped(self):
        for exempt in ("README.md", "session-handoff.md", "platform-mapping.md"):
            self._write(
                f"docs/agents/{exempt}",
                "# X\n\nOwner: Engineering\nStatus: active\n\n## Body\n",
            )
        modified = self.ext._backfill_role_field_on_agent_docs(self.root)
        self.assertEqual(modified, [])

    def test_journals_directory_skipped(self):
        path = self._write(
            "docs/agents/journals/wave-coordinator.md",
            "# Journal\n\nOwner: Engineering\nStatus: active\n\n## Captures\n",
        )
        modified = self.ext._backfill_role_field_on_agent_docs(self.root)
        self.assertEqual(modified, [])
        # Verify the journal file was not modified
        self.assertNotIn("Role:", path.read_text(encoding="utf-8"))

    def test_F6_recursive_walk_finds_nested_layout(self):
        """Wave 1p3b9 (1p3b7 F6): the migration walks docs/agents/ recursively
        so enterprise nested layouts (e.g., `docs/agents/teams/<team>/<role>.md`)
        are covered. Previously the migration walked three fixed subdirs and
        missed deeper nesting."""
        nested = self.root / "docs" / "agents" / "teams" / "auth-team"
        nested.mkdir(parents=True)
        (nested / "code-reviewer.md").write_text(
            "Owner: Engineering\nStatus: active\nCategory: review\n", encoding="utf-8"
        )
        modified = self.ext._backfill_role_field_on_agent_docs(self.root)
        self.assertEqual(modified, ["docs/agents/teams/auth-team/code-reviewer.md"])
        # File was rewritten with Role: line
        text = (nested / "code-reviewer.md").read_text(encoding="utf-8")
        self.assertIn("Role: code-reviewer", text)

    def test_F6_journals_skipped_at_any_depth(self):
        """Wave 1p3b9 (1p3b7 F6): the `journals` skip applies at any depth in
        the agents tree. A team's journal doc deep in the tree must NOT get
        a Role: insertion."""
        deep_journal = self.root / "docs" / "agents" / "teams" / "auth" / "journals" / "note.md"
        deep_journal.parent.mkdir(parents=True)
        original = "Owner: x\nStatus: active\n## Captures\n"
        deep_journal.write_text(original, encoding="utf-8")
        modified = self.ext._backfill_role_field_on_agent_docs(self.root)
        self.assertEqual(modified, [])
        # File unchanged
        self.assertEqual(deep_journal.read_text(encoding="utf-8"), original)

    def test_walks_specialists_and_personas_subdirs(self):
        self._write(
            "docs/agents/specialists/red-team.md",
            "Owner: Engineering\nStatus: active\nCategory: specialist\n",
        )
        self._write(
            "docs/agents/personas/admin.md",
            "Owner: Engineering\nStatus: active\nCategory: persona\n",
        )
        modified = self.ext._backfill_role_field_on_agent_docs(self.root)
        self.assertEqual(sorted(modified), [
            "docs/agents/personas/admin.md",
            "docs/agents/specialists/red-team.md",
        ])

    def test_idempotent_second_run_is_noop(self):
        """AC-13: re-running performs zero modifications once Role: is set."""
        self._write(
            "docs/agents/code-reviewer.md",
            "Owner: Engineering\nStatus: active\nCategory: review\n",
        )
        first = self.ext._backfill_role_field_on_agent_docs(self.root)
        self.assertEqual(len(first), 1)
        second = self.ext._backfill_role_field_on_agent_docs(self.root)
        self.assertEqual(second, [])

    def test_missing_agents_dir_safe(self):
        # Fresh tmp without docs/agents/
        with tempfile.TemporaryDirectory() as t:
            bare_root = Path(t).resolve()
            self.assertEqual(self.ext._backfill_role_field_on_agent_docs(bare_root), [])


class PycacheLauncherCleanupTests(unittest.TestCase):
    """AC-7: deletes .claude/hooks/pycache-cleanup* launcher files."""

    def setUp(self):
        self.ext = _load_upgrade_extensions()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()
        (self.root / ".claude" / "hooks").mkdir(parents=True)

    def tearDown(self):
        self.tmp.cleanup()

    def test_deletes_all_three_launcher_variants(self):
        for name in ("pycache-cleanup", "pycache-cleanup.py", "pycache-cleanup.cmd"):
            (self.root / ".claude" / "hooks" / name).write_text("legacy\n", encoding="utf-8")
        deleted = self.ext._delete_pycache_hook_launchers(self.root)
        self.assertEqual(sorted(deleted), [
            ".claude/hooks/pycache-cleanup",
            ".claude/hooks/pycache-cleanup.cmd",
            ".claude/hooks/pycache-cleanup.py",
        ])
        for name in ("pycache-cleanup", "pycache-cleanup.py", "pycache-cleanup.cmd"):
            self.assertFalse((self.root / ".claude" / "hooks" / name).exists())

    def test_deletes_only_existing(self):
        (self.root / ".claude" / "hooks" / "pycache-cleanup.py").write_text("legacy\n", encoding="utf-8")
        deleted = self.ext._delete_pycache_hook_launchers(self.root)
        self.assertEqual(deleted, [".claude/hooks/pycache-cleanup.py"])

    def test_idempotent_when_no_launchers_present(self):
        self.assertEqual(self.ext._delete_pycache_hook_launchers(self.root), [])
        # Second call still a no-op
        self.assertEqual(self.ext._delete_pycache_hook_launchers(self.root), [])

    def test_does_not_touch_other_launcher_files(self):
        for name in ("pre-edit.py", "post-edit", "simulate-hooks.cmd"):
            (self.root / ".claude" / "hooks" / name).write_text("framework\n", encoding="utf-8")
        self.ext._delete_pycache_hook_launchers(self.root)
        for name in ("pre-edit.py", "post-edit", "simulate-hooks.cmd"):
            self.assertTrue((self.root / ".claude" / "hooks" / name).exists())

    def test_missing_claude_dir_safe(self):
        with tempfile.TemporaryDirectory() as t:
            bare_root = Path(t).resolve()
            self.assertEqual(self.ext._delete_pycache_hook_launchers(bare_root), [])


class SettingsJsonPycacheRowStripTests(unittest.TestCase):
    """AC-8, AC-9: removes the retired PostToolUse Bash pycache row,
    preserves operator-added customs."""

    def setUp(self):
        self.ext = _load_upgrade_extensions()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()
        self.settings_path = self.root / ".claude" / "settings.json"
        self.settings_path.parent.mkdir(parents=True)

    def tearDown(self):
        self.tmp.cleanup()

    def _write(self, data) -> None:
        self.settings_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    def _read(self):
        return json.loads(self.settings_path.read_text(encoding="utf-8"))

    def test_strips_legacy_pycache_row(self):
        self._write({
            "hooks": {
                "PreToolUse": [
                    {"matcher": "Edit|Write",
                     "hooks": [{"type": "command", "command": ".claude/hooks/pre-edit"}]},
                ],
                "PostToolUse": [
                    {"matcher": "Bash",
                     "hooks": [{"type": "command", "command": ".claude/hooks/pycache-cleanup",
                                "statusMessage": "Cleaning __pycache__..."}]},
                    {"matcher": "Edit|Write",
                     "hooks": [{"type": "command", "command": ".claude/hooks/post-edit"}]},
                ],
            },
        })
        result = self.ext._strip_pycache_row_from_claude_settings(self.root)
        # Wave 1p3b9 (1p3b7 F4): function now returns list of paths modified.
        self.assertEqual(result, [".claude/settings.json"])
        data = self._read()
        post = data["hooks"]["PostToolUse"]
        self.assertEqual(len(post), 1)
        self.assertEqual(post[0]["matcher"], "Edit|Write")
        # PreToolUse preserved
        self.assertEqual(len(data["hooks"]["PreToolUse"]), 1)

    def test_strips_cmd_variant(self):
        self._write({
            "hooks": {"PostToolUse": [
                {"matcher": "Bash",
                 "hooks": [{"type": "command",
                            "command": "cmd.exe /c .claude\\hooks\\pycache-cleanup.cmd"}]},
            ]},
        })
        result = self.ext._strip_pycache_row_from_claude_settings(self.root)
        self.assertEqual(result, [".claude/settings.json"])
        self.assertEqual(self._read()["hooks"]["PostToolUse"], [])

    def test_preserves_operator_custom_bash_hook(self):
        """An operator-added Bash hook with a DIFFERENT command must be preserved."""
        self._write({
            "hooks": {"PostToolUse": [
                {"matcher": "Bash",
                 "hooks": [{"type": "command", "command": ".claude/hooks/pycache-cleanup"}]},
                {"matcher": "Bash",
                 "hooks": [{"type": "command", "command": "/operator/custom/audit-log"}]},
            ]},
        })
        result = self.ext._strip_pycache_row_from_claude_settings(self.root)
        self.assertEqual(result, [".claude/settings.json"])
        post = self._read()["hooks"]["PostToolUse"]
        self.assertEqual(len(post), 1)
        self.assertIn("audit-log", post[0]["hooks"][0]["command"])

    def test_noop_when_no_pycache_row(self):
        """AC-9: when no pycache row present, no file rewrite, return empty list."""
        self._write({
            "hooks": {"PostToolUse": [
                {"matcher": "Edit|Write",
                 "hooks": [{"type": "command", "command": ".claude/hooks/post-edit"}]},
            ]},
        })
        before = self.settings_path.read_text(encoding="utf-8")
        result = self.ext._strip_pycache_row_from_claude_settings(self.root)
        self.assertEqual(result, [])
        self.assertEqual(self.settings_path.read_text(encoding="utf-8"), before)

    def test_missing_settings_file_returns_empty_list(self):
        # setUp creates the parent dir but never writes settings.json
        self.assertFalse(self.settings_path.exists())
        self.assertEqual(self.ext._strip_pycache_row_from_claude_settings(self.root), [])

    def test_malformed_settings_returns_empty_list(self):
        self.settings_path.write_text("{not valid json", encoding="utf-8")
        self.assertEqual(self.ext._strip_pycache_row_from_claude_settings(self.root), [])

    def test_idempotent_second_run_is_noop(self):
        """AC-13: after first strip, second call returns empty list and doesn't rewrite."""
        self._write({
            "hooks": {"PostToolUse": [
                {"matcher": "Bash",
                 "hooks": [{"type": "command", "command": ".claude/hooks/pycache-cleanup"}]},
            ]},
        })
        first = self.ext._strip_pycache_row_from_claude_settings(self.root)
        self.assertEqual(first, [".claude/settings.json"])
        second = self.ext._strip_pycache_row_from_claude_settings(self.root)
        self.assertEqual(second, [])

    def test_F4_strips_from_settings_local_json_too(self):
        """Wave 1p3b9 (1p3b7 F4): personal-override settings.local.json gets
        stripped alongside the committed settings.json. Enterprise consumers
        with shared local-overrides don't leave the orphan row behind."""
        self._write({
            "hooks": {"PostToolUse": [
                {"matcher": "Bash",
                 "hooks": [{"type": "command", "command": ".claude/hooks/pycache-cleanup"}]},
            ]},
        })
        local_path = self.root / ".claude" / "settings.local.json"
        local_path.write_text(
            json.dumps({"hooks": {"PostToolUse": [
                {"matcher": "Bash",
                 "hooks": [{"type": "command",
                            "command": ".claude/hooks/pycache-cleanup"}]},
            ]}}, indent=2),
            encoding="utf-8",
        )
        result = self.ext._strip_pycache_row_from_claude_settings(self.root)
        self.assertEqual(sorted(result), [
            ".claude/settings.json",
            ".claude/settings.local.json",
        ])
        # Both files have the row removed
        for rel in (".claude/settings.json", ".claude/settings.local.json"):
            data = json.loads((self.root / rel).read_text(encoding="utf-8"))
            self.assertEqual(data["hooks"]["PostToolUse"], [])

    def test_F4_settings_local_only(self):
        """Only settings.local.json has the row; settings.json absent.
        Strip operates on whichever file exists and has the row."""
        local_path = self.root / ".claude" / "settings.local.json"
        local_path.write_text(
            json.dumps({"hooks": {"PostToolUse": [
                {"matcher": "Bash",
                 "hooks": [{"type": "command",
                            "command": ".claude/hooks/pycache-cleanup"}]},
            ]}}, indent=2),
            encoding="utf-8",
        )
        result = self.ext._strip_pycache_row_from_claude_settings(self.root)
        self.assertEqual(result, [".claude/settings.local.json"])


class ConvergenceMigrationTests(unittest.TestCase):
    """Wave 1p3iv (1p3j7): convergence half — `post_extract` always runs the
    legacy-config-key rewrite (no version gate), driven by the canonical-names
    manifest. Tests cover the rewrite helpers in isolation; integration with
    `post_extract` is verified by `PostExtractHookOrchestrationTests`."""

    def setUp(self):
        self.ext = _load_upgrade_extensions()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()
        (self.root / "docs").mkdir()
        (self.root / ".wavefoundry" / "framework").mkdir(parents=True)
        # Plant a minimal canonical-names manifest in the test repo so the
        # rewrite helpers can resolve aliases against it.
        manifest = {
            "schema_version": 1,
            "role_renames": {},
            "config_key_renames": {
                "wave_council_policy": {
                    "canonical": "wave_review", "removed_in": "2.0.0",
                },
                "wave_execution": {
                    "canonical": "wave_implement", "removed_in": "2.0.0",
                },
            },
        }
        (self.root / ".wavefoundry/framework/canonical-names.json").write_text(
            json.dumps(manifest), encoding="utf-8",
        )

    def tearDown(self):
        self.tmp.cleanup()

    def _write_config(self, data):
        (self.root / "docs/workflow-config.json").write_text(
            json.dumps(data, indent=2) + "\n", encoding="utf-8",
        )

    def _read_config(self):
        return json.loads((self.root / "docs/workflow-config.json").read_text(encoding="utf-8"))

    def test_rewrite_renames_legacy_to_canonical(self):
        """Legacy-only key → renamed in-place; performed tuple carries
        action='rename' and dropped_value=None."""
        self._write_config({"wave_council_policy": {"enabled": True}, "other": 1})
        performed = self.ext._rewrite_legacy_config_keys(self.root)
        self.assertEqual(
            performed,
            [("wave_council_policy", "wave_review", "rename", None)],
        )
        result = self._read_config()
        self.assertIn("wave_review", result)
        self.assertNotIn("wave_council_policy", result)
        self.assertEqual(result["wave_review"], {"enabled": True})
        # Other keys preserved
        self.assertEqual(result["other"], 1)

    def test_rewrite_drops_legacy_when_canonical_already_present(self):
        """Both legacy AND canonical → canonical wins (operator-explicit),
        legacy entry is dropped; the dropped value is captured in the
        returned tuple so operators can recover it from the log."""
        self._write_config({
            "wave_review": {"enabled": True, "explicit": True},
            "wave_council_policy": {"enabled": False},
        })
        performed = self.ext._rewrite_legacy_config_keys(self.root)
        # Action discriminator distinguishes drop from rename, and the dropped
        # value is captured for log fidelity (1p3iv post-review fix).
        self.assertEqual(
            performed,
            [(
                "wave_council_policy",
                "wave_review",
                "drop",
                {"enabled": False},
            )],
        )
        result = self._read_config()
        self.assertNotIn("wave_council_policy", result)
        self.assertEqual(result["wave_review"], {"enabled": True, "explicit": True})

    def test_rewrite_is_noop_when_canonical_only(self):
        """No legacy keys present → no work; performed list is empty."""
        self._write_config({"wave_review": {"enabled": True}})
        performed = self.ext._rewrite_legacy_config_keys(self.root)
        self.assertEqual(performed, [])
        # File untouched (still contains canonical only)
        self.assertEqual(self._read_config(), {"wave_review": {"enabled": True}})

    def test_rewrite_handles_multiple_legacy_keys_in_one_pass(self):
        """Both legacy spellings present → both renamed in one call."""
        self._write_config({
            "wave_council_policy": {"a": 1},
            "wave_execution": {"b": 2},
        })
        performed = self.ext._rewrite_legacy_config_keys(self.root)
        legacies = {item[0] for item in performed}
        self.assertEqual(legacies, {"wave_council_policy", "wave_execution"})
        actions = {item[2] for item in performed}
        self.assertEqual(actions, {"rename"})
        result = self._read_config()
        self.assertIn("wave_review", result)
        self.assertIn("wave_implement", result)

    def test_rewrite_is_idempotent(self):
        """Running the rewrite twice yields no work on the second invocation."""
        self._write_config({"wave_council_policy": {"enabled": True}})
        first = self.ext._rewrite_legacy_config_keys(self.root)
        second = self.ext._rewrite_legacy_config_keys(self.root)
        self.assertEqual(
            first,
            [("wave_council_policy", "wave_review", "rename", None)],
        )
        self.assertEqual(second, [])

    def test_rewrite_captures_dropped_value_for_complex_legacy_state(self):
        """When the legacy entry holds a non-trivial dict, the dropped value
        is captured in full so the log line can render it as JSON."""
        legacy_value = {
            "enabled": False,
            "policy": {"required_for_all_waves": True},
            "fixed_seats": ["red-team"],
        }
        self._write_config({
            "wave_review": {"enabled": True},
            "wave_council_policy": legacy_value,
        })
        performed = self.ext._rewrite_legacy_config_keys(self.root)
        self.assertEqual(len(performed), 1)
        _legacy, _canonical, action, dropped_value = performed[0]
        self.assertEqual(action, "drop")
        self.assertEqual(dropped_value, legacy_value)

    # --- Report file writers (1p3iv post-review fix #2) ---

    def test_real_run_writes_convergence_log_file(self):
        """Real-run with renames performed → writes
        upgrade-convergence-migration.log with a record per performed item."""
        self._write_config({"wave_council_policy": {"enabled": True}})

        class _Ctx:
            pass
        ctx = _Ctx()
        ctx.root = self.root
        ctx.dry_run = False
        ctx.from_version = "1.5.0+abcd"
        ctx.to_version = "1.5.0+efgh"
        ctx.zip_path = None
        ctx.yes = True

        self.ext._run_convergence_migration(ctx)

        log_path = self.root / ".wavefoundry/logs/upgrade-convergence-migration.log"
        self.assertTrue(log_path.exists())
        body = log_path.read_text(encoding="utf-8")
        self.assertIn("REAL RUN", body)
        self.assertIn("renamed `wave_council_policy` → `wave_review`", body)

    def test_real_run_log_records_dropped_value_for_drop_case(self):
        """Real-run with a drop → log records the dropped value as JSON so
        operators can recover from the file alone."""
        self._write_config({
            "wave_review": {"enabled": True},
            "wave_council_policy": {"enabled": False, "marker": "operator-set"},
        })

        class _Ctx:
            pass
        ctx = _Ctx()
        ctx.root = self.root
        ctx.dry_run = False
        ctx.from_version = "1.5.0+abcd"
        ctx.to_version = "1.5.0+efgh"
        ctx.zip_path = None
        ctx.yes = True

        self.ext._run_convergence_migration(ctx)

        log_path = self.root / ".wavefoundry/logs/upgrade-convergence-migration.log"
        body = log_path.read_text(encoding="utf-8")
        self.assertIn("dropped legacy `wave_council_policy`", body)
        # The dropped value (a JSON dict) appears in the log so the operator
        # can recover it without consulting git history.
        self.assertIn('"marker": "operator-set"', body)

    def test_dry_run_writes_convergence_preview_log_file(self):
        """Dry-run with planned actions → writes
        upgrade-convergence-migration.preview.log (parity with the 1.4 → 1.5
        migration preview report shape)."""
        self._write_config({"wave_council_policy": {"enabled": True}})

        class _Ctx:
            pass
        ctx = _Ctx()
        ctx.root = self.root
        ctx.dry_run = True
        ctx.from_version = "1.5.0+abcd"
        ctx.to_version = "1.5.0+efgh"
        ctx.zip_path = None
        ctx.yes = True

        self.ext._run_convergence_migration(ctx)

        preview_path = self.root / ".wavefoundry/logs/upgrade-convergence-migration.preview.log"
        self.assertTrue(preview_path.exists())
        body = preview_path.read_text(encoding="utf-8")
        self.assertIn("PREVIEW", body)
        self.assertIn("would rename `wave_council_policy` → `wave_review`", body)
        # File on disk is untouched
        self.assertEqual(
            self._read_config(),
            {"wave_council_policy": {"enabled": True}},
        )

    def test_no_log_files_when_no_renames_apply(self):
        """No legacy keys → no log files written (silent no-op)."""
        self._write_config({"wave_review": {"enabled": True}})

        class _Ctx:
            pass
        ctx = _Ctx()
        ctx.root = self.root
        ctx.dry_run = False
        ctx.from_version = "1.5.0+abcd"
        ctx.to_version = "1.5.0+efgh"
        ctx.zip_path = None
        ctx.yes = True

        self.ext._run_convergence_migration(ctx)

        self.assertFalse((self.root / ".wavefoundry/logs/upgrade-convergence-migration.log").exists())
        self.assertFalse((self.root / ".wavefoundry/logs/upgrade-convergence-migration.preview.log").exists())

    def test_rewrite_is_noop_when_workflow_config_missing(self):
        """No workflow-config.json → no error, empty result."""
        self.assertEqual(self.ext._rewrite_legacy_config_keys(self.root), [])

    def test_rewrite_is_noop_when_workflow_config_malformed(self):
        """Malformed JSON → no error, empty result (degraded mode)."""
        (self.root / "docs/workflow-config.json").write_text("{not valid", encoding="utf-8")
        self.assertEqual(self.ext._rewrite_legacy_config_keys(self.root), [])

    def test_preview_plans_renames_without_touching_disk(self):
        """Preview returns the planned-action strings; file is unchanged."""
        self._write_config({"wave_council_policy": {"enabled": True}})
        before = (self.root / "docs/workflow-config.json").read_text(encoding="utf-8")
        planned = self.ext._preview_legacy_config_key_rewrite(self.root)
        after = (self.root / "docs/workflow-config.json").read_text(encoding="utf-8")
        self.assertEqual(after, before)
        self.assertEqual(len(planned), 1)
        self.assertIn("wave_council_policy", planned[0])
        self.assertIn("wave_review", planned[0])

    def test_preview_distinguishes_rename_vs_drop_when_both_present(self):
        """When both legacy and canonical exist, preview wording reflects the
        drop-legacy outcome (not a rename)."""
        self._write_config({
            "wave_review": {"explicit": True},
            "wave_council_policy": {"legacy": True},
        })
        planned = self.ext._preview_legacy_config_key_rewrite(self.root)
        self.assertEqual(len(planned), 1)
        self.assertIn("drop legacy", planned[0])


class PostExtractHookOrchestrationTests(unittest.TestCase):
    """AC-1, AC-10, AC-11, AC-12, AC-14: post_extract integration."""

    def setUp(self):
        self.ext = _load_upgrade_extensions()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()

    def tearDown(self):
        self.tmp.cleanup()

    def _ctx(self, from_version: str | None = "1.4.1+p347"):
        class _Ctx:
            pass
        ctx = _Ctx()
        ctx.root = self.root
        ctx.from_version = from_version
        ctx.to_version = "1.5.0"
        ctx.zip_path = None
        ctx.yes = True
        return ctx

    def _report_path(self) -> Path:
        return self.root / ".wavefoundry" / "logs" / "upgrade-migration-1.5.0.log"

    def test_version_gate_skips_when_from_at_cutoff(self):
        """AC-14: from_version = 1.5.0 → zero work, no report."""
        # Plant a state that WOULD be migrated if the gate ran
        (self.root / ".claude" / "hooks").mkdir(parents=True)
        (self.root / ".claude" / "hooks" / "pycache-cleanup.py").write_text("legacy\n", encoding="utf-8")
        self.ext.post_extract(self._ctx(from_version="1.5.0"))
        # Launcher still present; report not written
        self.assertTrue((self.root / ".claude" / "hooks" / "pycache-cleanup.py").exists())
        self.assertFalse(self._report_path().exists())

    def test_version_gate_fires_when_pre_cutoff(self):
        """AC-1: from_version = 1.4.1 → migrations run."""
        (self.root / ".claude" / "hooks").mkdir(parents=True)
        (self.root / ".claude" / "hooks" / "pycache-cleanup.py").write_text("legacy\n", encoding="utf-8")
        self.ext.post_extract(self._ctx(from_version="1.4.1"))
        self.assertFalse((self.root / ".claude" / "hooks" / "pycache-cleanup.py").exists())
        self.assertTrue(self._report_path().exists())

    def test_no_report_written_when_no_work_done(self):
        """AC-11: pre-1.5.0 from_version but already-clean state → no report."""
        # No agent docs, no claude/hooks, no settings.json
        self.ext.post_extract(self._ctx(from_version="1.4.1"))
        self.assertFalse(self._report_path().exists())

    def test_report_lists_all_three_migration_sections(self):
        """AC-10: report names each migration and what fired."""
        # Plant work for migrations 1, 2, 3
        (self.root / "docs" / "agents").mkdir(parents=True)
        (self.root / "docs" / "agents" / "code-reviewer.md").write_text(
            "Owner: Engineering\nStatus: active\nCategory: review\n", encoding="utf-8"
        )
        (self.root / ".claude" / "hooks").mkdir(parents=True)
        (self.root / ".claude" / "hooks" / "pycache-cleanup.py").write_text("legacy\n", encoding="utf-8")
        (self.root / ".claude" / "settings.json").write_text(
            json.dumps({"hooks": {"PostToolUse": [
                {"matcher": "Bash",
                 "hooks": [{"type": "command", "command": ".claude/hooks/pycache-cleanup"}]},
            ]}}, indent=2),
            encoding="utf-8",
        )
        self.ext.post_extract(self._ctx())
        report = self._report_path().read_text(encoding="utf-8")
        self.assertIn("Role: backfill", report)
        self.assertIn("Pycache launcher cleanup", report)
        self.assertIn("settings.json pycache row removal", report)
        self.assertIn("code-reviewer.md", report)

    def test_idempotent_full_pipeline(self):
        """AC-13: a second full post_extract on an already-migrated repo
        writes no report (no work performed)."""
        (self.root / "docs" / "agents").mkdir(parents=True)
        (self.root / "docs" / "agents" / "code-reviewer.md").write_text(
            "Owner: Engineering\nStatus: active\nCategory: review\n", encoding="utf-8"
        )
        (self.root / ".claude" / "hooks").mkdir(parents=True)
        (self.root / ".claude" / "hooks" / "pycache-cleanup.py").write_text("legacy\n", encoding="utf-8")
        self.ext.post_extract(self._ctx())
        report_after_first = self._report_path().read_text(encoding="utf-8")
        self._report_path().unlink()  # remove first report so we can detect second-run state
        # Second run — same from_version, but state already migrated
        self.ext.post_extract(self._ctx())
        self.assertFalse(self._report_path().exists())
        # Sanity: the first report DID list the migration
        self.assertIn("code-reviewer.md", report_after_first)

    def test_exception_in_one_migration_isolated(self):
        """AC-12: a migration helper raising must not abort other migrations
        and must be recorded in the report."""
        from unittest.mock import patch
        # Plant launcher cleanup work
        (self.root / ".claude" / "hooks").mkdir(parents=True)
        (self.root / ".claude" / "hooks" / "pycache-cleanup.py").write_text("x", encoding="utf-8")
        # Patch Role: backfill to raise
        with patch.object(
            self.ext, "_backfill_role_field_on_agent_docs",
            side_effect=RuntimeError("synthetic failure"),
        ):
            self.ext.post_extract(self._ctx())
        # Pycache launcher migration still ran
        self.assertFalse((self.root / ".claude" / "hooks" / "pycache-cleanup.py").exists())
        # Report captures both: ERROR for backfill, success for cleanup
        report = self._report_path().read_text(encoding="utf-8")
        self.assertIn("ERROR", report)
        self.assertIn("synthetic failure", report)
        self.assertIn("pycache-cleanup.py", report)


# ---------------------------------------------------------------------------
# Wave 1p3b9 (1p3b6): migration preview helpers + post_extract dry-run branch
# ---------------------------------------------------------------------------


class RoleBackfillPreviewTests(unittest.TestCase):
    """AC-2: `_preview_role_field_backfill` reports planned actions without
    mutating files."""

    def setUp(self):
        self.ext = _load_upgrade_extensions()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()
        (self.root / "docs" / "agents").mkdir(parents=True)
        (self.root / "docs" / "agents" / "specialists").mkdir(parents=True)
        (self.root / "docs" / "agents" / "journals").mkdir(parents=True)

    def tearDown(self):
        self.tmp.cleanup()

    def test_returns_empty_when_no_agent_docs(self):
        self.assertEqual(self.ext._preview_role_field_backfill(self.root), [])

    def test_reports_planned_role_insertion_without_mutating(self):
        path = self.root / "docs" / "agents" / "code-reviewer.md"
        original = (
            "# Code Reviewer\n\n"
            "Owner: Engineering\n"
            "Status: active\n"
            "Category: review\n\n## Identity\n\nReviews.\n"
        )
        path.write_text(original, encoding="utf-8")
        planned = self.ext._preview_role_field_backfill(self.root)
        self.assertEqual(len(planned), 1)
        self.assertIn("code-reviewer.md", planned[0])
        self.assertIn("Role: code-reviewer", planned[0])
        # File content unchanged
        self.assertEqual(path.read_text(encoding="utf-8"), original)

    def test_already_present_role_not_planned(self):
        path = self.root / "docs" / "agents" / "existing.md"
        path.write_text(
            "Owner: Engineering\nStatus: active\nRole: existing\nCategory: review\n",
            encoding="utf-8",
        )
        self.assertEqual(self.ext._preview_role_field_backfill(self.root), [])

    def test_journals_subdir_not_walked(self):
        path = self.root / "docs" / "agents" / "journals" / "wave-coordinator.md"
        path.write_text("Owner: x\nStatus: active\n", encoding="utf-8")
        self.assertEqual(self.ext._preview_role_field_backfill(self.root), [])


class PycacheLauncherDeletionPreviewTests(unittest.TestCase):
    """AC-3: `_preview_pycache_launcher_deletion` reports planned deletes
    without removing files."""

    def setUp(self):
        self.ext = _load_upgrade_extensions()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()
        (self.root / ".claude" / "hooks").mkdir(parents=True)

    def tearDown(self):
        self.tmp.cleanup()

    def test_returns_empty_when_no_launchers(self):
        self.assertEqual(self.ext._preview_pycache_launcher_deletion(self.root), [])

    def test_reports_planned_deletes_without_mutating(self):
        for name in ("pycache-cleanup", "pycache-cleanup.py", "pycache-cleanup.cmd"):
            (self.root / ".claude" / "hooks" / name).write_text("legacy\n", encoding="utf-8")
        planned = self.ext._preview_pycache_launcher_deletion(self.root)
        self.assertEqual(len(planned), 3)
        for name in ("pycache-cleanup", "pycache-cleanup.py", "pycache-cleanup.cmd"):
            self.assertTrue((self.root / ".claude" / "hooks" / name).exists())


class SettingsPycacheStripPreviewTests(unittest.TestCase):
    """AC-4: `_preview_settings_pycache_strip` describes the row that would
    be stripped without rewriting the JSON."""

    def setUp(self):
        self.ext = _load_upgrade_extensions()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()
        self.settings_path = self.root / ".claude" / "settings.json"
        self.settings_path.parent.mkdir(parents=True)

    def tearDown(self):
        self.tmp.cleanup()

    def test_returns_none_when_no_settings_file(self):
        self.assertIsNone(self.ext._preview_settings_pycache_strip(self.root))

    def test_returns_none_when_no_pycache_row(self):
        self.settings_path.write_text(
            json.dumps({"hooks": {"PostToolUse": [
                {"matcher": "Edit|Write",
                 "hooks": [{"type": "command", "command": ".claude/hooks/post-edit"}]},
            ]}}, indent=2),
            encoding="utf-8",
        )
        original = self.settings_path.read_text(encoding="utf-8")
        self.assertIsNone(self.ext._preview_settings_pycache_strip(self.root))
        # File unchanged
        self.assertEqual(self.settings_path.read_text(encoding="utf-8"), original)

    def test_describes_planned_strip_without_mutating(self):
        body = {"hooks": {"PostToolUse": [
            {"matcher": "Bash",
             "hooks": [{"type": "command", "command": ".claude/hooks/pycache-cleanup"}]},
        ]}}
        self.settings_path.write_text(json.dumps(body, indent=2), encoding="utf-8")
        original = self.settings_path.read_text(encoding="utf-8")
        result = self.ext._preview_settings_pycache_strip(self.root)
        self.assertIsNotNone(result)
        self.assertEqual(result["matcher"], "Bash")
        self.assertIn("pycache-cleanup", result["command"])
        self.assertEqual(result["file"], ".claude/settings.json")
        # File unchanged
        self.assertEqual(self.settings_path.read_text(encoding="utf-8"), original)


class PostExtractDryRunBranchTests(unittest.TestCase):
    """AC-1, AC-5, AC-6, AC-8, AC-9: post_extract's dry-run branch produces
    a preview-log to a distinct filename and performs zero mutations."""

    def setUp(self):
        self.ext = _load_upgrade_extensions()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()

    def tearDown(self):
        self.tmp.cleanup()

    def _ctx(self, from_version="1.4.1+p347", dry_run=False):
        class _Ctx:
            pass
        ctx = _Ctx()
        ctx.root = self.root
        ctx.from_version = from_version
        ctx.to_version = "1.5.0"
        ctx.zip_path = None
        ctx.yes = True
        ctx.dry_run = dry_run
        return ctx

    def _preview_log(self) -> Path:
        return self.root / ".wavefoundry" / "logs" / "upgrade-migration-1.5.0.preview.log"

    def _real_log(self) -> Path:
        return self.root / ".wavefoundry" / "logs" / "upgrade-migration-1.5.0.log"

    def test_dry_run_uses_distinct_filename_from_real_run(self):
        """AC-6: preview log filename must differ from real-run log so a
        subsequent real run doesn't shadow the preview."""
        self.assertNotEqual(self._preview_log().name, self._real_log().name)

    def test_dry_run_writes_preview_log_when_actions_planned(self):
        """AC-5, AC-9: with planned actions present, dry-run writes the
        preview log AND does not write the real-run log."""
        (self.root / "docs" / "agents").mkdir(parents=True)
        (self.root / "docs" / "agents" / "code-reviewer.md").write_text(
            "Owner: x\nStatus: active\nCategory: review\n", encoding="utf-8",
        )
        self.ext.post_extract(self._ctx(dry_run=True))
        self.assertTrue(self._preview_log().exists())
        self.assertFalse(self._real_log().exists())
        text = self._preview_log().read_text(encoding="utf-8")
        self.assertIn("PREVIEW", text)
        self.assertIn("code-reviewer", text)

    def test_dry_run_zero_mutations(self):
        """AC-8: dry-run never touches the consumer files."""
        (self.root / "docs" / "agents").mkdir(parents=True)
        agent_path = self.root / "docs" / "agents" / "code-reviewer.md"
        agent_path.write_text(
            "Owner: x\nStatus: active\nCategory: review\n", encoding="utf-8",
        )
        (self.root / ".claude" / "hooks").mkdir(parents=True)
        launcher_path = self.root / ".claude" / "hooks" / "pycache-cleanup.py"
        launcher_path.write_text("legacy\n", encoding="utf-8")
        agent_before = agent_path.read_text(encoding="utf-8")
        launcher_before = launcher_path.read_text(encoding="utf-8")
        self.ext.post_extract(self._ctx(dry_run=True))
        # No mutations to either file
        self.assertEqual(agent_path.read_text(encoding="utf-8"), agent_before)
        self.assertEqual(launcher_path.read_text(encoding="utf-8"), launcher_before)

    def test_dry_run_with_no_planned_actions_writes_no_preview_log(self):
        """When the consumer state has nothing to migrate, no preview log
        is written (parallels the real-run behavior)."""
        self.ext.post_extract(self._ctx(dry_run=True))
        self.assertFalse(self._preview_log().exists())

    def test_dry_run_respects_version_gate(self):
        """Same version-gate behavior as the real run: if from_version is
        already at the cutoff, neither preview nor real-run path fires."""
        (self.root / "docs" / "agents").mkdir(parents=True)
        (self.root / "docs" / "agents" / "code-reviewer.md").write_text(
            "Owner: x\nStatus: active\nCategory: review\n", encoding="utf-8",
        )
        self.ext.post_extract(self._ctx(from_version="1.5.0", dry_run=True))
        self.assertFalse(self._preview_log().exists())


class ChunkerVersionBumpDetectionTests(unittest.TestCase):
    """Wave 1p3dk / 1p3ho: chunker-version-aware upgrade routing.

    Closes the field failure mode where 1.5.0's CHUNKER_VERSION bump didn't
    trigger a project-index rebuild because `indexer.build_index`'s internal
    auto-escalate was silent (no operator-visible decision log) and the
    upgrade reported success without verifying the rebuild ran."""

    def setUp(self) -> None:
        self.mod = load_upgrade_module()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        # Stand up the directory structure used by the helpers
        (self.root / ".wavefoundry" / "index").mkdir(parents=True)
        (self.root / ".wavefoundry" / "framework" / "scripts").mkdir(parents=True)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _write_meta(self, content: dict) -> None:
        # 1sed6 review-hardened contract: upgrade probes read the STORE ONLY.
        import importlib.util as _ilu
        index_dir = self.root / ".wavefoundry" / "index"
        spec = _ilu.spec_from_file_location(
            "index_state_store",
            Path(__file__).resolve().parents[1] / "index_state_store.py",
        )
        iss = _ilu.module_from_spec(spec)
        spec.loader.exec_module(iss)
        iss.write_build_bookkeeping(index_dir, content)

    def _write_chunker(self, version: str) -> None:
        (self.root / ".wavefoundry" / "framework" / "scripts" / "chunker.py").write_text(
            f'# stub chunker\nCHUNKER_VERSION = "{version}"\nMAX_DOC_CHUNK_CHARS = 2000\n',
            encoding="utf-8",
        )

    def test_snapshot_reads_per_layer_dict(self) -> None:
        """AC-2: pre-extract snapshot reads `chunker_versions` per-layer dict."""
        self._write_meta({"chunker_versions": {"docs": "22", "code": "22"}})
        snap = self.mod._snapshot_pre_extract_chunker_versions(self.root)
        self.assertEqual(snap, {"docs": "22", "code": "22"})

    def test_legacy_meta_json_is_ignored_entirely(self) -> None:
        """1sed6 review-hardened: a legacy meta.json is NEVER read — not even
        for version comparison. Empty snapshot = unknown = the upgrade treats
        the consumer as needing convergence (safe), instead of letting stale
        JSON claims skip required re-chunk work."""
        (self.root / ".wavefoundry" / "index" / "meta.json").write_text(
            json.dumps({"chunker_versions": {"docs": "22", "code": "22"},
                        "chunker_version": "22"}),
            encoding="utf-8",
        )
        snap = self.mod._snapshot_pre_extract_chunker_versions(self.root)
        self.assertEqual(snap, {})

    def test_snapshot_empty_when_meta_absent(self) -> None:
        """Fresh install with no prior meta.json → empty snapshot, no bump detection."""
        snap = self.mod._snapshot_pre_extract_chunker_versions(self.root)
        self.assertEqual(snap, {})

    def test_read_chunker_version_from_pack(self) -> None:
        """AC-3: post-extract version read via regex (no Python import)."""
        self._write_chunker("23")
        self.assertEqual(self.mod._read_chunker_version_from_pack(self.root), "23")

    def test_read_chunker_version_empty_when_chunker_missing(self) -> None:
        """Defensive: missing chunker.py → empty string → no bump detection."""
        self.assertEqual(self.mod._read_chunker_version_from_pack(self.root), "")

    def test_detect_bump_when_versions_differ(self) -> None:
        """AC-4: bump detected when old != new and both are non-empty."""
        bumped, transition = self.mod._detect_chunker_version_bump(
            {"docs": "22", "code": "22"}, "23",
        )
        self.assertTrue(bumped)
        self.assertEqual(transition, ("22", "23"))

    def test_no_bump_when_versions_match(self) -> None:
        """AC-12: bump NOT detected when old == new (regression guard for the
        unchanged path — incremental update path stays default when no bump)."""
        bumped, transition = self.mod._detect_chunker_version_bump(
            {"docs": "23", "code": "23"}, "23",
        )
        self.assertFalse(bumped)
        self.assertIsNone(transition)

    def test_no_bump_on_fresh_install(self) -> None:
        """AC-9: empty pre-extract dict → no bump (no comparison baseline)."""
        bumped, transition = self.mod._detect_chunker_version_bump({}, "23")
        self.assertFalse(bumped)
        self.assertIsNone(transition)

    def test_no_bump_when_new_version_unreadable(self) -> None:
        """Defensive: empty new version (chunker.py couldn't be read) → no bump."""
        bumped, transition = self.mod._detect_chunker_version_bump(
            {"docs": "22", "code": "22"}, "",
        )
        self.assertFalse(bumped)
        self.assertIsNone(transition)

    def test_store_recorded_bump_detected(self) -> None:
        """Bump detection reads the store's per-layer versions (the only
        surviving version source post-1sed6)."""
        self._write_meta({"chunker_versions": {"docs": "20", "code": "20"}})
        snap = self.mod._snapshot_pre_extract_chunker_versions(self.root)
        bumped, transition = self.mod._detect_chunker_version_bump(snap, "23")
        self.assertTrue(bumped)
        self.assertEqual(transition, ("20", "23"))

    def test_verify_succeeds_when_meta_matches_new_version(self) -> None:
        """AC-7: post-rebuild verification confirms the new chunker version is
        recorded in the index meta.json."""
        self._write_chunker("23")
        self._write_meta({"chunker_versions": {"docs": "23", "code": "23"}})
        self.assertTrue(self.mod._verify_chunker_rebuild_succeeded(self.root))

    def test_verify_fails_when_meta_still_stale(self) -> None:
        """AC-8: post-rebuild verification detects stale meta.json — the
        rebuild failed silently and the upgrade must surface this as a
        fail-loud actionable error."""
        self._write_chunker("23")
        self._write_meta({"chunker_versions": {"docs": "22", "code": "22"}})
        self.assertFalse(self.mod._verify_chunker_rebuild_succeeded(self.root))

    def test_verify_conservative_when_no_meta(self) -> None:
        """When meta.json doesn't exist post-rebuild, verification returns True
        (don't block the upgrade on a verification-tooling failure)."""
        self._write_chunker("23")
        # No meta.json at all
        self.assertTrue(self.mod._verify_chunker_rebuild_succeeded(self.root))


class MultiVersionTransitionDetectionTests(unittest.TestCase):
    """Wave 1p3dk / 1p3ho v2: detect chunker + walker + graph_builder
    transitions and log them. The indexer's auto-escalate handles the
    rebuild; the upgrade flow just surfaces the transitions for operator
    visibility."""

    def setUp(self) -> None:
        self.mod = load_upgrade_module()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / ".wavefoundry" / "index" / "graph").mkdir(parents=True)
        (self.root / ".wavefoundry" / "framework" / "scripts").mkdir(parents=True)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _write_pack(self, chunker: str, walker: str, graph_builder: str) -> None:
        """Plant version constants in the extracted-pack location."""
        scripts = self.root / ".wavefoundry" / "framework" / "scripts"
        (scripts / "chunker.py").write_text(
            f'CHUNKER_VERSION = "{chunker}"\n', encoding="utf-8",
        )
        (scripts / "indexer.py").write_text(
            f'WALKER_VERSION = "{walker}"\n', encoding="utf-8",
        )
        (scripts / "graph_indexer.py").write_text(
            f'GRAPH_BUILDER_VERSION = "{graph_builder}"\n', encoding="utf-8",
        )

    def _write_meta(self, content: dict) -> None:
        # 1sed6 review-hardened contract: upgrade probes read the STORE ONLY.
        import importlib.util as _ilu
        index_dir = self.root / ".wavefoundry" / "index"
        spec = _ilu.spec_from_file_location(
            "index_state_store",
            Path(__file__).resolve().parents[1] / "index_state_store.py",
        )
        iss = _ilu.module_from_spec(spec)
        spec.loader.exec_module(iss)
        iss.write_build_bookkeeping(index_dir, content)

    def _write_graph_state(self, content: dict) -> None:
        # Wave 1rvfx: the installed graph state lives in the REAL project graph dir — the legacy JSON
        # fallback path (pre-1p9q2 repos / the reader's fallback branch). The sqlite primary path is
        # exercised by _write_graph_state_sqlite + test_snapshot_reads_sqlite_graph_state.
        (self.root / ".wavefoundry" / "index" / "graph" / "project-graph-state.json").write_text(
            json.dumps(content), encoding="utf-8",
        )

    def _write_graph_state_sqlite(self, builder_version: str) -> None:
        # Wave 1rvfx: write the PRIMARY project graph state — the SQLite store's meta table — matching
        # the production shape read by _read_installed_graph_builder_version.
        import sqlite3
        store = self.root / ".wavefoundry" / "index" / "graph" / "project-graph-state.sqlite"
        conn = sqlite3.connect(str(store))
        try:
            conn.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT)")
            conn.execute("INSERT INTO meta (key, value) VALUES ('builder_version', ?)", (builder_version,))
            conn.commit()
        finally:
            conn.close()

    def test_read_walker_version(self) -> None:
        self._write_pack("24", "6", "23")
        self.assertEqual(self.mod._read_walker_version_from_pack(self.root), "6")

    def test_read_graph_builder_version(self) -> None:
        self._write_pack("24", "6", "24")
        self.assertEqual(self.mod._read_graph_builder_version_from_pack(self.root), "24")

    def test_snapshot_collects_all_version_constants(self) -> None:
        self._write_meta({
            "chunker_versions": {"docs": "22", "code": "22"},
            "walker_version": "4",
        })
        self._write_graph_state({"builder_version": "22"})
        snap = self.mod._snapshot_pre_extract_versions(self.root)
        self.assertEqual(snap["chunker_docs"], "22")
        self.assertEqual(snap["chunker_code"], "22")
        self.assertEqual(snap["walker"], "4")
        self.assertEqual(snap["graph_builder"], "22")

    def test_snapshot_reads_sqlite_graph_state(self) -> None:
        # Wave 1rvfx AC-1: the PRIMARY read path — the installed project graph SQLite store's meta table.
        self._write_graph_state_sqlite("42")
        self._write_pack("24", "5", "43")
        snap = self.mod._snapshot_pre_extract_versions(self.root)
        self.assertEqual(snap["graph_builder"], "42")
        transitions = self.mod._detect_version_transitions(snap, self.root)
        self.assertTrue(any("GRAPH_BUILDER_VERSION" in name for name, _, _ in transitions))

    def test_snapshot_sqlite_takes_precedence_over_legacy_json(self) -> None:
        # Wave 1rvfx: when both exist, the SQLite store wins (mirrors read_state_builder_version).
        self._write_graph_state_sqlite("42")
        self._write_graph_state({"builder_version": "40"})  # legacy JSON present but superseded
        self.assertEqual(self.mod._read_installed_graph_builder_version(self.root), "42")

    def test_snapshot_graph_builder_absent_is_fail_safe(self) -> None:
        # Wave 1rvfx AC-3: no installed project graph state → no graph_builder key, no GRAPH_BUILDER_VERSION
        # transition, and NO exception (the upgrade must proceed).
        self._write_pack("24", "5", "43")
        snap = self.mod._snapshot_pre_extract_versions(self.root)
        self.assertNotIn("graph_builder", snap)
        transitions = self.mod._detect_version_transitions(snap, self.root)
        self.assertFalse(any("GRAPH_BUILDER_VERSION" in name for name, _, _ in transitions))

    def test_snapshot_graph_builder_corrupt_store_is_fail_safe(self) -> None:
        # Wave 1rvfx AC-3: a corrupt/unreadable SQLite store yields no entry and never raises.
        store = self.root / ".wavefoundry" / "index" / "graph" / "project-graph-state.sqlite"
        store.write_text("this is not a sqlite database", encoding="utf-8")
        self.assertEqual(self.mod._read_installed_graph_builder_version(self.root), "")

    def test_detect_chunker_transition(self) -> None:
        self._write_meta({
            "chunker_versions": {"docs": "22", "code": "22"},
            "walker_version": "5",
        })
        self._write_graph_state({"builder_version": "23"})
        self._write_pack("24", "5", "23")
        snap = self.mod._snapshot_pre_extract_versions(self.root)
        transitions = self.mod._detect_version_transitions(snap, self.root)
        # Two chunker transitions (docs + code), no walker, no graph
        names = [name for name, _, _ in transitions]
        self.assertTrue(any("CHUNKER_VERSION (docs index)" in n for n in names))
        self.assertTrue(any("CHUNKER_VERSION (code index)" in n for n in names))
        self.assertFalse(any("WALKER" in n for n in names))
        self.assertFalse(any("GRAPH" in n for n in names))

    def test_detect_walker_transition(self) -> None:
        self._write_meta({
            "chunker_versions": {"docs": "24", "code": "24"},
            "walker_version": "4",
        })
        self._write_graph_state({"builder_version": "23"})
        self._write_pack("24", "5", "23")
        snap = self.mod._snapshot_pre_extract_versions(self.root)
        transitions = self.mod._detect_version_transitions(snap, self.root)
        names = [name for name, _, _ in transitions]
        self.assertTrue(any("WALKER_VERSION" in n for n in names))
        for name, old, new in transitions:
            if "WALKER" in name:
                self.assertEqual((old, new), ("4", "5"))

    def test_detect_graph_builder_transition(self) -> None:
        self._write_meta({
            "chunker_versions": {"docs": "24", "code": "24"},
            "walker_version": "5",
        })
        self._write_graph_state({"builder_version": "22"})
        self._write_pack("24", "5", "23")
        snap = self.mod._snapshot_pre_extract_versions(self.root)
        transitions = self.mod._detect_version_transitions(snap, self.root)
        names = [name for name, _, _ in transitions]
        self.assertTrue(any("GRAPH_BUILDER_VERSION" in n for n in names))

    def test_no_transitions_when_everything_matches(self) -> None:
        self._write_meta({
            "chunker_versions": {"docs": "24", "code": "24"},
            "walker_version": "5",
        })
        self._write_graph_state({"builder_version": "23"})
        self._write_pack("24", "5", "23")
        snap = self.mod._snapshot_pre_extract_versions(self.root)
        transitions = self.mod._detect_version_transitions(snap, self.root)
        self.assertEqual(transitions, [])

    def test_no_transitions_on_fresh_install(self) -> None:
        """No pre-existing meta or graph state → no transitions detected."""
        self._write_pack("24", "5", "23")
        snap = self.mod._snapshot_pre_extract_versions(self.root)
        transitions = self.mod._detect_version_transitions(snap, self.root)
        self.assertEqual(transitions, [])


class RemoveRootBootstrapFileTests(unittest.TestCase):
    """Wave 1rxyi: the upgrade removes the re-dropped root install-wavefoundry.md (fail-safe).

    The zip ships that single-use bootstrap file at the zip root by design, so every extract re-drops it
    at the project root and prune (MANIFEST-scoped to .wavefoundry/framework/) never removes it."""

    def setUp(self) -> None:
        self.mod = load_upgrade_module()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_removes_present_bootstrap_file(self) -> None:
        # AC-1: a present root install-wavefoundry.md is deleted.
        f = self.root / "install-wavefoundry.md"
        f.write_text("bootstrap instructions", encoding="utf-8")
        self.mod._remove_root_bootstrap_file(self.root)
        self.assertFalse(f.exists(), "the root bootstrap file must be removed")

    def test_absent_is_noop(self) -> None:
        # AC-2: no file present → no-op, no exception.
        self.mod._remove_root_bootstrap_file(self.root)  # must not raise
        self.assertFalse((self.root / "install-wavefoundry.md").exists())

    def test_unlink_error_is_swallowed(self) -> None:
        # AC-2: a failed unlink is logged and swallowed — the upgrade must never abort over cleanup.
        f = self.root / "install-wavefoundry.md"
        f.write_text("x", encoding="utf-8")
        with patch.object(self.mod.Path, "unlink", side_effect=OSError("boom")):
            self.mod._remove_root_bootstrap_file(self.root)  # must not raise

    def test_only_touches_the_reserved_bootstrap_name(self) -> None:
        # A same-directory unrelated file is never touched — only the framework-reserved name is removed.
        other = self.root / "README.md"
        other.write_text("project readme", encoding="utf-8")
        (self.root / "install-wavefoundry.md").write_text("bootstrap", encoding="utf-8")
        self.mod._remove_root_bootstrap_file(self.root)
        self.assertTrue(other.exists(), "unrelated root files must be left untouched")
        self.assertFalse((self.root / "install-wavefoundry.md").exists())

    def test_extract_phase_wires_the_cleanup_after_extractall(self) -> None:
        # F1 (delivery review): lock the wiring — the upgrade extract phase must CALL
        # `_remove_root_bootstrap_file(root)` AFTER `zf.extractall`, so a refactor that drops the call is
        # caught. The helper is otherwise only unit-tested and the full apply path has no test harness
        # (main() is only reachable in the suite via --resume-after-gate / --materialize-lifecycle-policy,
        # neither of which reaches the extract block).
        import inspect
        src = inspect.getsource(self.mod)
        self.assertIn("_remove_root_bootstrap_file(root)", src, "the cleanup call must be wired in")
        # Wave 1u0cc: the extract phase now calls the allowlist helper instead of a bare
        # zf.extractall — anchor on its unique call site (the def has annotated params).
        extract_pos = src.index("_extract_feature_members(zf, root)")
        # Wave 1rych added a second call in the --update-index phase (which precedes the extract block in
        # source order), so anchor on the FIRST call AT OR AFTER the extract call — that is the
        # extract-phase call this test locks.
        call_pos = src.index("_remove_root_bootstrap_file(root)", extract_pos)
        self.assertGreater(
            call_pos, extract_pos,
            "the bootstrap cleanup must run AFTER the filtered extraction in the extract phase",
        )

    def test_update_index_phase_wires_the_bootstrap_removal(self) -> None:
        # Wave 1rych: the --update-index phase must invoke _remove_root_bootstrap_file (from the freshly
        # extracted NEW code) so a from-old MCP upgrade — whose extract ran the OLD orchestrator with no
        # removal helper — still cleans up the re-dropped root install-wavefoundry.md. The full
        # --update-index path spawns a real index build (no unit harness), so lock the wiring by source:
        # the removal call must appear AFTER phase_index_update in the --update-index handler.
        import inspect
        src = inspect.getsource(self.mod)
        piu = src.index("phase_index_update(root)")  # closing paren matches the call site, not the def
        removal_after = src.index("_remove_root_bootstrap_file(root)", piu)
        self.assertGreater(
            removal_after, piu,
            "the --update-index phase must call _remove_root_bootstrap_file after phase_index_update",
        )

    def test_removal_wired_at_both_extract_and_update_index_sites(self) -> None:
        # AC-3: belt-and-suspenders — the extract-phase call is KEPT and the --update-index call is ADDED,
        # so there must be (at least) two distinct call sites of _remove_root_bootstrap_file(root).
        import inspect
        src = inspect.getsource(self.mod)
        self.assertGreaterEqual(
            src.count("_remove_root_bootstrap_file(root)"), 2,
            "both the extract-phase and --update-index removal call sites must be present",
        )


class ExtractFeatureMembersTests(unittest.TestCase):
    """Wave 1u0cc: Phase 0b extraction allowlists feature members — the combined release zip's
    zipapp runner members (payload/*, __main__.py, upgrade_bridge_bootstrap.py, subprocess_util.py)
    are never written to the target project root, and same-named project files are never touched."""

    RUNNER_MEMBERS = ("__main__.py", "upgrade_bridge_bootstrap.py", "subprocess_util.py")

    def setUp(self) -> None:
        self.mod = load_upgrade_module()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.proj = self.root / "proj"
        self.proj.mkdir()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _payload_prefix(self) -> str:
        import upgrade_bundle
        return upgrade_bundle.PAYLOAD_PREFIX

    def _combined_bundle_zip(self, extra_members: dict[str, str] | None = None) -> Path:
        """Bundle-shaped zip mirroring the canonical builder's member layout (build_pack appends the
        runner members and payload/* to the feature zip); the layout constants themselves are pinned
        against upgrade_bundle in test_allowlist_pins_bundle_layout_constants."""
        zp = self.root / "wavefoundry-9.9.9.test.zip"
        payload = self._payload_prefix()
        with zipfile.ZipFile(zp, "w") as zf:
            zf.writestr(".wavefoundry/framework/VERSION", "9.9.9+test")
            zf.writestr(".wavefoundry/framework/scripts/example.py", "print('hi')\n")
            zf.writestr("install-wavefoundry.md", "bootstrap instructions")
            for name in self.RUNNER_MEMBERS:
                zf.writestr(name, "# runner code\n")
            zf.writestr(payload + "selection.json", "{}")
            zf.writestr(payload + "bridge.zip", "not-a-real-zip")
            zf.writestr(payload + "feature.zip", "not-a-real-zip")
            for name, body in (extra_members or {}).items():
                zf.writestr(name, body)
        return zp

    def _extract(self, zp: Path) -> int:
        with zipfile.ZipFile(zp, "r") as zf:
            return self.mod._extract_feature_members(zf, self.proj)

    def test_runner_members_and_payload_are_skipped(self) -> None:
        # AC-1: no runner debris at the project root; skip count covers all six runner/payload members.
        skipped = self._extract(self._combined_bundle_zip())
        self.assertEqual(skipped, 6)
        for name in self.RUNNER_MEMBERS:
            self.assertFalse((self.proj / name).exists(), f"{name} must not be extracted")
        self.assertFalse((self.proj / "payload").exists(), "payload/ must not be extracted")

    def test_feature_members_and_bootstrap_extract_as_before(self) -> None:
        # AC-2: .wavefoundry/** extracts with content parity; the bootstrap file still lands at the
        # root (its removal stays the wired _remove_root_bootstrap_file cleanup, ordering-locked by
        # test_extract_phase_wires_the_cleanup_after_extractall).
        self._extract(self._combined_bundle_zip())
        self.assertEqual(
            (self.proj / ".wavefoundry" / "framework" / "VERSION").read_text(encoding="utf-8"),
            "9.9.9+test",
        )
        self.assertEqual(
            (self.proj / ".wavefoundry" / "framework" / "scripts" / "example.py").read_text(encoding="utf-8"),
            "print('hi')\n",
        )
        self.assertEqual(
            (self.proj / "install-wavefoundry.md").read_text(encoding="utf-8"),
            "bootstrap instructions",
        )
        self.mod._remove_root_bootstrap_file(self.proj)
        self.assertFalse((self.proj / "install-wavefoundry.md").exists())

    def test_preexisting_collision_files_are_byte_identical(self) -> None:
        # AC-3: a project's own root files named like runner members are never overwritten or deleted.
        own_main = self.proj / "__main__.py"
        own_main.write_bytes(b"project-owned entry point\n")
        own_payload = self.proj / "payload"
        own_payload.mkdir()
        (own_payload / "keep.txt").write_bytes(b"project data\n")
        self._extract(self._combined_bundle_zip())
        self.assertEqual(own_main.read_bytes(), b"project-owned entry point\n")
        self.assertEqual((own_payload / "keep.txt").read_bytes(), b"project data\n")
        self.assertEqual(
            sorted(p.name for p in own_payload.iterdir()), ["keep.txt"],
            "no archive payload member may land in the project's own payload/ directory",
        )

    def test_backslash_separator_member_is_skipped(self) -> None:
        # Memory 1tz9e: both POSIX and Windows separators are path syntax. CPython's extraction does
        # not treat backslash as a separator on POSIX, so an unfiltered extract would write a literal
        # root file named ".wavefoundry\\evil.py"; the allowlist skips it by structure.
        skipped = self._extract(
            self._combined_bundle_zip(extra_members={".wavefoundry\\evil.py": "evil"})
        )
        self.assertEqual(skipped, 7)
        self.assertEqual(
            [p.name for p in self.proj.iterdir() if "\\" in p.name], [],
            "no backslash-named member may land at the project root",
        )

    def test_traversal_inside_allowed_prefix_stays_contained(self) -> None:
        # zipfile's _extract_member drops '..' path parts, so an allowed-prefix member shaped like a
        # traversal stays contained under the project root.
        self._extract(
            self._combined_bundle_zip(extra_members={".wavefoundry/../escape.txt": "out"})
        )
        self.assertFalse((self.root / "escape.txt").exists(), "no member may escape the project root")
        escaped = [p for p in self.root.rglob("escape.txt") if self.proj not in p.parents]
        self.assertEqual(escaped, [], "the traversal-shaped member must stay under the project root")

    def test_feature_only_archive_skips_zero(self) -> None:
        # Requirement 5: the bridge-retained inner zip is feature-only; the skip log must never fire.
        zp = self.root / "feature-only.zip"
        with zipfile.ZipFile(zp, "w") as zf:
            zf.writestr(".wavefoundry/framework/VERSION", "9.9.9+test")
            zf.writestr("install-wavefoundry.md", "bootstrap instructions")
        self.assertEqual(self._extract(zp), 0)

    def test_allowlist_pins_bundle_layout_constants(self) -> None:
        # Requirement 2: the runner mirrors upgrade_bundle's layout constants (it cannot import them
        # mid-upgrade); this pin fails loudly if the pack layout contract moves.
        import upgrade_bundle
        self.assertEqual(self.mod._EXTRACT_MEMBER_PREFIX, upgrade_bundle.FEATURE_MEMBER_PREFIX)
        self.assertEqual(set(self.mod._EXTRACT_ROOT_MEMBERS), set(upgrade_bundle.FEATURE_ROOT_MEMBERS))
        self.assertFalse(
            upgrade_bundle.PAYLOAD_PREFIX.startswith(self.mod._EXTRACT_MEMBER_PREFIX),
            "payload members must fall outside the extraction allowlist",
        )

    def test_no_unfiltered_extractall_remains(self) -> None:
        # The bare full-archive extract must never return to the runner.
        import inspect
        src = inspect.getsource(self.mod)
        self.assertNotIn("zf.extractall(str(root))", src)


class UpgradeContextChunkerFieldsTests(unittest.TestCase):
    """AC-1: UpgradeContext gains the three chunker-version transition fields."""

    def setUp(self) -> None:
        self.mod = load_upgrade_module()

    def test_default_chunker_fields_preserve_existing_behavior(self) -> None:
        ctx = self.mod.UpgradeContext(
            root=Path("/tmp/fake"),
            from_version=None, to_version=None,
            zip_path=None, yes=False,
        )
        self.assertEqual(ctx.pre_extract_chunker_versions, {})
        self.assertFalse(ctx.chunker_version_bumped)
        self.assertIsNone(ctx.chunker_version_transition)


class BackgroundCodeIncompleteWarningTests(unittest.TestCase):
    """H1 (Phase 4b reliability): cleanup warns when the background code re-embed left the code layer
    behind the docs layer (the silent-failure case the JS/TS team hit on p4g3/p4su)."""

    def setUp(self):
        self.mod = load_upgrade_module()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / ".wavefoundry" / "index").mkdir(parents=True)

    def tearDown(self):
        self.tmp.cleanup()

    def _meta(self, docs, code):
        # 1sed6: the warning reads the store's build summary, not meta.json.
        import importlib.util as _ilu
        spec = _ilu.spec_from_file_location(
            "index_state_store",
            Path(__file__).resolve().parents[1] / "index_state_store.py",
        )
        iss = _ilu.module_from_spec(spec)
        spec.loader.exec_module(iss)
        iss.write_build_bookkeeping(
            self.root / ".wavefoundry" / "index",
            {"chunker_versions": {"docs": docs, "code": code}},
        )

    def _run_capturing(self):
        lines: list[str] = []
        with patch.object(self.mod, "_log", side_effect=lambda *a: lines.append(" ".join(str(x) for x in a))):
            self.mod._warn_if_background_code_incomplete(self.root)
        return lines

    def test_warns_on_chunker_mismatch(self):
        self._meta("29", "28")
        self.assertTrue(any("BEHIND" in ln for ln in self._run_capturing()))

    def test_silent_when_versions_match(self):
        self._meta("29", "29")
        self.assertFalse(any("BEHIND" in ln for ln in self._run_capturing()))

    def test_silent_when_meta_absent(self):
        self.assertEqual(self._run_capturing(), [])  # no meta.json → no warning, no crash


class UpgradeFloorAndMigrationSurfacingTests(unittest.TestCase):
    """1p5do: upgrade floor (warn, not abort), migration-log ERROR surfacing, and the
    empty-version-baseline rebuild signal."""

    def setUp(self):
        self.mod = load_upgrade_module()
        # _below_upgrade_floor does a call-time `from check_version import ...` (a sibling script);
        # ensure the scripts dir is importable when this test runs standalone.
        if str(SCRIPTS_ROOT) not in sys.path:
            sys.path.insert(0, str(SCRIPTS_ROOT))
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _capture(self, fn, *args):
        lines: list[str] = []
        with patch.object(self.mod, "_log", side_effect=lambda *a: lines.append(" ".join(str(x) for x in a))):
            fn(*args)
        return lines

    # AC-1 — floor is a warn at 1.4.0, never fires for >= 1.4.0, fires for below + unparseable.
    def test_below_floor_predicate(self):
        self.assertEqual(self.mod.SUPPORTED_UPGRADE_FLOOR, "1.4.0")
        for below in ("1.3.0", "0.9.0", "not-a-version", ""):
            self.assertTrue(self.mod._below_upgrade_floor(below), below)
        for ok in ("1.4.0", "1.5.1", "1.6.0", "1.5.0+p4uw"):
            self.assertFalse(self.mod._below_upgrade_floor(ok), ok)

    # AC-3 — empty snapshot + index present → rebuild signal; otherwise silent.
    def test_no_version_baseline_warns_when_index_exists(self):
        (self.root / ".wavefoundry" / "index").mkdir(parents=True)
        lines = self._capture(self.mod._warn_if_no_version_baseline, {}, self.root)
        self.assertTrue(any("No framework version baseline" in ln for ln in lines))

    def test_no_version_baseline_silent_when_baseline_present(self):
        (self.root / ".wavefoundry" / "index").mkdir(parents=True)
        self.assertEqual(self._capture(self.mod._warn_if_no_version_baseline, {"graph_builder": "30"}, self.root), [])

    def test_no_version_baseline_silent_when_no_index(self):
        self.assertEqual(self._capture(self.mod._warn_if_no_version_baseline, {}, self.root), [])

    # AC-2 — migration-log ERROR surfacing (real logs only, not .preview).
    def _logs_dir(self):
        d = self.root / ".wavefoundry" / "logs"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def test_migration_errors_surface(self):
        (self._logs_dir() / "upgrade-migration-1.5.0.log").write_text("ok\nERROR: Role backfill failed\n", encoding="utf-8")
        self.assertTrue(any("ERROR entries" in ln for ln in self._capture(self.mod._warn_if_migration_errors, self.root)))

    def test_migration_clean_log_silent(self):
        (self._logs_dir() / "upgrade-convergence-migration.log").write_text("renamed wave_execution -> wave_implement\n", encoding="utf-8")
        self.assertEqual(self._capture(self.mod._warn_if_migration_errors, self.root), [])

    def test_migration_preview_log_ignored(self):
        (self._logs_dir() / "upgrade-migration-1.5.0.preview.log").write_text("ERROR: would fail\n", encoding="utf-8")
        self.assertEqual(self._capture(self.mod._warn_if_migration_errors, self.root), [])

    # 1p5ik — remove the deprecated framework/index/ that manifest-prune can't.
    def test_removes_deprecated_framework_index(self):
        fidx = self.root / ".wavefoundry" / "framework" / "index"
        (fidx / "docs.lance").mkdir(parents=True)
        (fidx / "meta.json").write_text("{}", encoding="utf-8")
        with patch.object(self.mod, "_log", side_effect=lambda *a: None):
            removed = self.mod._remove_deprecated_framework_index(self.root)
        self.assertTrue(removed)
        self.assertFalse(fidx.exists(), "stale framework/index/ must be removed")

    def test_remove_framework_index_absent_is_noop(self):
        with patch.object(self.mod, "_log", side_effect=lambda *a: None):
            removed = self.mod._remove_deprecated_framework_index(self.root)
        self.assertFalse(removed)  # absent → False, no error


class ConvergenceParseWarningTests(unittest.TestCase):
    """1p5do (AC-4): a malformed workflow-config.json makes the convergence migration WARN rather
    than no-op silently, so a later docs-gate failure is connectable to the un-migrated config."""

    def setUp(self):
        spec = importlib.util.spec_from_file_location("upgrade_extensions", SCRIPTS_ROOT / "upgrade_extensions.py")
        self.ext = importlib.util.module_from_spec(spec)
        sys.modules["upgrade_extensions"] = self.ext
        spec.loader.exec_module(self.ext)
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "docs").mkdir(parents=True)

    def tearDown(self):
        self.tmp.cleanup()

    def test_malformed_config_warns_and_noops(self):
        (self.root / "docs" / "workflow-config.json").write_text("{ this is not valid json", encoding="utf-8")
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            result = self.ext._rewrite_legacy_config_keys(self.root)
        self.assertEqual(result, [])
        self.assertIn("WARNING", err.getvalue())
        self.assertIn("could not read/parse", err.getvalue())

    def test_valid_config_no_warning(self):
        (self.root / "docs" / "workflow-config.json").write_text(json.dumps({"wave_implement": "x"}), encoding="utf-8")
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            self.ext._rewrite_legacy_config_keys(self.root)
        self.assertNotIn("WARNING", err.getvalue())


class ConfigReviewRecommendationTests(unittest.TestCase):
    """Wave 1p5tk: the config-review recommendation is surfaced on every major/minor
    upgrade (stateless), silent on patch/downgrade/same, and fully fail-safe."""

    def setUp(self):
        # `_is_major_or_minor_upgrade` does `from check_version import _to_version`
        # at call time; make sure the scripts dir is importable.
        if str(SCRIPTS_ROOT) not in sys.path:
            sys.path.insert(0, str(SCRIPTS_ROOT))
        self.mod = load_upgrade_module()

    def test_minor_bump_recommends(self):
        lines = self.mod._config_review_recommendation_lines("1.5.0", "1.6.0")
        self.assertTrue(lines)
        self.assertTrue(any("framework-config-review.prompt.md" in ln for ln in lines))

    def test_major_bump_recommends(self):
        lines = self.mod._config_review_recommendation_lines("1.6.0", "2.0.0")
        self.assertTrue(lines)

    def test_build_suffix_stripped_minor_recommends(self):
        lines = self.mod._config_review_recommendation_lines("1.5.0+abc", "1.6.0+def")
        self.assertTrue(lines)

    def test_patch_bump_silent(self):
        self.assertEqual(self.mod._config_review_recommendation_lines("1.6.0", "1.6.1"), [])

    def test_same_version_silent(self):
        self.assertEqual(self.mod._config_review_recommendation_lines("1.6.0", "1.6.0"), [])

    def test_downgrade_silent(self):
        self.assertEqual(self.mod._config_review_recommendation_lines("1.6.0", "1.5.0"), [])

    def test_unparseable_is_silent_not_fatal(self):
        self.assertEqual(self.mod._config_review_recommendation_lines("garbage", "1.6.0"), [])

    def test_missing_version_silent(self):
        self.assertEqual(self.mod._config_review_recommendation_lines(None, "1.6.0"), [])
        self.assertEqual(self.mod._config_review_recommendation_lines("1.6.0", None), [])

    def test_is_major_or_minor_classification(self):
        self.assertTrue(self.mod._is_major_or_minor_upgrade("1.5.0", "1.6.0"))
        self.assertTrue(self.mod._is_major_or_minor_upgrade("1.6.0", "2.0.0"))
        self.assertFalse(self.mod._is_major_or_minor_upgrade("1.6.0", "1.6.1"))
        self.assertFalse(self.mod._is_major_or_minor_upgrade("1.6.0", "1.6.0"))


class ReconciliationRecommendationTests(unittest.TestCase):
    """Wave 1p7ww / 1p8et / 1p8kz: the reconciliation scan line runs on EVERY upgrade — operator
    direction (a patch or a same-version build-successor can change/retire a surface during testing).
    Unlike its sibling ``_config_review_recommendation_lines`` (still major/minor-gated), it is NOT
    gated on version delta; it returns [] only on an internal failure. Report-only; fail-safe."""

    def setUp(self):
        if str(SCRIPTS_ROOT) not in sys.path:
            sys.path.insert(0, str(SCRIPTS_ROOT))
        self.mod = load_upgrade_module()

    def test_minor_bump_recommends(self):
        # Wave 1p8et: the recommend-only prose was replaced by the actionable scan; the heading is
        # now "Reconciliation scan". With no findings supplied it still emits the heading + a
        # "no stale references" line so the operator sees the scan ran.
        lines = self.mod._reconciliation_recommendation_lines("1.5.0", "1.6.0")
        self.assertTrue(lines)
        self.assertTrue(any("Reconciliation scan" in ln for ln in lines))
        # Names the concrete 1.9.0 bin/* -> wf retirement example.
        self.assertTrue(any("`wf`" in ln or "bin/" in ln for ln in lines))

    def test_findings_render_actionable_file_line_suggested(self):
        # Wave 1p8et: when findings are supplied, the actionable file:line → suggested list is emitted.
        # The printed reference is the finding's `matched` text (INV-recline), not a synthesized form.
        findings = [
            {"file": "docs/x.md", "line": 7, "retired_surface": "docs-lint",
             "matched": ".wavefoundry/bin/docs-lint", "suggested": "wf docs-lint"},
        ]
        lines = self.mod._reconciliation_recommendation_lines("1.5.0", "1.6.0", findings)
        joined = "\n".join(lines)
        self.assertIn("docs/x.md:7", joined)
        self.assertIn(".wavefoundry/bin/docs-lint", joined)
        self.assertIn("wf docs-lint", joined)

    def test_findings_print_matched_text_for_py_join(self):
        # INV-recline: a .py-join finding prints its actual matched text, not `.wavefoundry/bin/<name>`.
        findings = [
            {"file": "s.py", "line": 3, "retired_surface": "wave-gate",
             "matched": 'bin_dir / "wave-gate"', "suggested": "wf gate"},
        ]
        lines = self.mod._reconciliation_recommendation_lines("1.5.0", "1.6.0", findings)
        joined = "\n".join(lines)
        self.assertIn('bin_dir / "wave-gate"', joined)
        self.assertNotIn(".wavefoundry/bin/wave-gate", joined)
        self.assertIn("wf gate", joined)

    def test_major_bump_recommends(self):
        self.assertTrue(self.mod._reconciliation_recommendation_lines("1.6.0", "2.0.0"))

    def test_build_suffix_stripped_minor_recommends(self):
        self.assertTrue(self.mod._reconciliation_recommendation_lines("1.5.0+abc", "1.6.0+def"))

    def test_patch_bump_runs(self):
        # 1p8kz: a patch bump now RUNS the scan (gate removed) — emits the heading.
        lines = self.mod._reconciliation_recommendation_lines("1.6.0", "1.6.1")
        self.assertTrue(any("Reconciliation scan" in ln for ln in lines))

    def test_same_version_build_successor_runs(self):
        # 1p8kz: a same-version build-successor (a rebuilt pack during testing) also runs the scan.
        lines = self.mod._reconciliation_recommendation_lines("1.6.0", "1.6.0")
        self.assertTrue(any("Reconciliation scan" in ln for ln in lines))

    def test_downgrade_runs(self):
        # 1p8kz: report-only scan runs on any upgrade run, including a version rollback during testing.
        lines = self.mod._reconciliation_recommendation_lines("1.6.0", "1.5.0")
        self.assertTrue(any("Reconciliation scan" in ln for ln in lines))

    def test_findings_supplied_render_regardless_of_version_delta(self):
        # 1p8kz: with findings supplied, the actionable list renders on a PATCH bump too (no gate).
        findings = [{"file": "d.md", "line": 2, "retired_surface": "wave-gate",
                     "matched": ".wavefoundry/bin/wave-gate", "suggested": "wf gate"}]
        lines = self.mod._reconciliation_recommendation_lines("1.6.0", "1.6.1", findings)
        joined = "\n".join(lines)
        self.assertIn("d.md:2", joined)
        self.assertIn("wf gate", joined)

    def _capture_summary(self, from_version, to_version):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.mod._print_operator_summary(
                from_version=from_version,
                to_version=to_version,
                zip_path=None,
                pruned_count=0,
                ran_index_rebuild=True,
                failed_phase=None,
            )
        return buf.getvalue()

    def test_reconciliation_line_wired_into_operator_summary_on_minor_bump(self):
        # Wave 1p7ww review: the GATE was tested but the WIRING into _print_operator_summary was not.
        # Wave 1p8et: heading is now "Reconciliation scan".
        out = self._capture_summary("1.5.0", "1.6.0")
        self.assertIn("Reconciliation scan", out)
        # Sibling config-review line is also present on the same gate.
        self.assertIn("Config review recommended", out)

    def test_reconciliation_line_present_in_summary_on_patch_bump(self):
        # 1p8kz: the reconciliation scan line now appears on a PATCH bump (gate removed). The sibling
        # Config-review line stays major/minor-gated, so it is correctly ABSENT on a patch bump.
        out = self._capture_summary("1.6.0", "1.6.1")
        self.assertIn("Reconciliation scan", out)
        self.assertNotIn("Config review recommended", out)

    def test_reconciliation_line_absent_in_summary_on_failed_phase(self):
        # Recommendations are suppressed when the upgrade failed mid-phase.
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.mod._print_operator_summary(
                from_version="1.5.0", to_version="1.6.0", zip_path=None,
                pruned_count=0, ran_index_rebuild=False, failed_phase="docs_gate",
            )
        self.assertNotIn("Reconciliation scan", buf.getvalue())


class ReconciliationScanIntegrationTests(unittest.TestCase):
    """Wave 1p8et: _print_operator_summary RUNS the shipped scan on a major/minor bump when a real
    root is supplied, and surfaces the actionable file:line → suggested list (report-only)."""

    def setUp(self):
        if str(SCRIPTS_ROOT) not in sys.path:
            sys.path.insert(0, str(SCRIPTS_ROOT))
        self.mod = load_upgrade_module()

    def _summary_over_root(self, root, from_v="1.5.0", to_v="1.6.0", failed_phase=None):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.mod._print_operator_summary(
                from_version=from_v, to_version=to_v, zip_path=None,
                pruned_count=0, ran_index_rebuild=True,
                failed_phase=failed_phase, root=Path(root),
            )
        return buf.getvalue()

    def test_scan_surfaces_actionable_finding(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "docs").mkdir()
            (root / "docs" / "runbook.md").write_text(
                "Run `.wavefoundry/bin/docs-lint` to lint.\n", encoding="utf-8"
            )
            out = self._summary_over_root(root)
            self.assertIn("docs/runbook.md:1", out)
            self.assertIn(".wavefoundry/bin/docs-lint", out)
            self.assertIn("wf docs-lint", out)

    def test_scan_runs_on_patch_bump(self):
        # 1p8kz (operator direction): the scan runs on a PATCH bump too and surfaces the actionable
        # finding (a patch can change/retire a surface during testing).
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "x.md").write_text("`.wavefoundry/bin/docs-lint`\n", encoding="utf-8")
            out = self._summary_over_root(root, from_v="1.6.0", to_v="1.6.1")
            self.assertIn("Reconciliation scan", out)
            self.assertIn("x.md:1", out)
            self.assertIn("wf docs-lint", out)

    def test_scan_skipped_when_root_none(self):
        # Back-compat: no root → no scan, no exception, summary still renders.
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.mod._print_operator_summary(
                from_version="1.5.0", to_version="1.6.0", zip_path=None,
                pruned_count=0, ran_index_rebuild=True,
            )
        out = buf.getvalue()
        self.assertIn("Reconciliation scan", out)
        self.assertIn("No stale retired-surface references found", out)

    def test_run_reconciliation_scan_is_fail_safe(self):
        # A bad root must not raise; returns ([], [], []) (1p8o5 two channels;
        # 1u2az adds the renderer-provenance self-heal channel).
        self.assertEqual(self.mod._run_reconciliation_scan(None), ([], [], []))


class UpgradeSummarySentinelTests(unittest.TestCase):
    """Wave 1p8eu: the operator summary is built ONCE as a dict and emitted both as prose and a
    machine-readable WAVE_UPGRADE_SUMMARY_JSON: sentinel line, rendered from the one dict."""

    def setUp(self):
        if str(SCRIPTS_ROOT) not in sys.path:
            sys.path.insert(0, str(SCRIPTS_ROOT))
        self.mod = load_upgrade_module()

    def _capture(self, **kwargs):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.mod._print_operator_summary(**kwargs)
        return buf.getvalue()

    def _parse_sentinel(self, out):
        sentinel = self.mod.WAVE_UPGRADE_SUMMARY_SENTINEL
        for line in out.splitlines():
            if line.startswith(sentinel):
                return json.loads(line[len(sentinel):])
        return None

    def test_sentinel_line_present_with_all_fields(self):
        out = self._capture(
            from_version="1.5.0", to_version="1.6.0", zip_path=None,
            pruned_count=4, ran_index_rebuild=True, failed_phase=None,
        )
        summary = self._parse_sentinel(out)
        self.assertIsNotNone(summary)
        for key in ("from_version", "to_version", "pruned_count", "docs_gate",
                    "index_update", "failed_phase", "is_major_or_minor", "reconciliation",
                    "host_permission_flags"):
            self.assertIn(key, summary)
        self.assertEqual(summary["from_version"], "1.5.0")
        self.assertEqual(summary["to_version"], "1.6.0")
        self.assertEqual(summary["pruned_count"], 4)
        self.assertEqual(summary["docs_gate"], "PASSED")
        self.assertTrue(summary["is_major_or_minor"])
        self.assertEqual(summary["reconciliation"], [])
        self.assertEqual(summary["host_permission_flags"], [])  # 1p8o5: additive, empty by default

    def test_sentinel_host_permission_flags_separate_from_reconciliation(self):
        # 1p8o5 #2 / AC-2: a stale ref in a host permission/allow-rule file lands in the SEPARATE
        # `host_permission_flags` summary field, NOT in `reconciliation`; an editable doc lands in
        # `reconciliation`. The summary exposes both channels distinctly.
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / ".claude").mkdir()
            (root / ".claude" / "settings.local.json").write_text(
                '{"allow": ["Bash(.wavefoundry/bin/docs-lint)"]}\n', encoding="utf-8"
            )
            (root / "docs").mkdir()
            (root / "docs" / "runbook.md").write_text(
                "Run `.wavefoundry/bin/wave-gate`.\n", encoding="utf-8"
            )
            out = self._capture(
                from_version="1.5.0", to_version="1.6.0", zip_path=None,
                pruned_count=0, ran_index_rebuild=True, failed_phase=None, root=root,
            )
            summary = self._parse_sentinel(out)
            recon_files = {f["file"] for f in summary["reconciliation"]}
            host_files = {f["file"] for f in summary["host_permission_flags"]}
            self.assertNotIn(".claude/settings.local.json", recon_files)
            self.assertIn(".claude/settings.local.json", host_files)
            self.assertIn("docs/runbook.md", recon_files)
            self.assertNotIn("docs/runbook.md", host_files)
            # The prose carries the separate operator-flag section.
            self.assertIn("Host permission/allow-rule files (flag for the OPERATOR", out)

    def test_sentinel_reconciliation_carries_findings(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "g.md").write_text("`.wavefoundry/bin/wave-gate`\n", encoding="utf-8")
            out = self._capture(
                from_version="1.5.0", to_version="1.6.0", zip_path=None,
                pruned_count=0, ran_index_rebuild=True, failed_phase=None, root=root,
            )
            summary = self._parse_sentinel(out)
            self.assertEqual(len(summary["reconciliation"]), 1)
            ref = summary["reconciliation"][0]
            self.assertEqual(ref["retired_surface"], "wave-gate")
            self.assertEqual(ref["matched"], ".wavefoundry/bin/wave-gate")
            self.assertEqual(ref["suggested"], "wf gate")

    def test_sentinel_failed_phase_reflected(self):
        out = self._capture(
            from_version="1.5.0", to_version="1.6.0", zip_path=None,
            pruned_count=0, ran_index_rebuild=False, failed_phase="docs_gate",
        )
        summary = self._parse_sentinel(out)
        self.assertEqual(summary["failed_phase"], "docs_gate")
        self.assertEqual(summary["docs_gate"], "FAILED")

    def test_prose_and_sentinel_agree_on_pruned_count(self):
        out = self._capture(
            from_version="1.5.0", to_version="1.6.0", zip_path=None,
            pruned_count=7, ran_index_rebuild=True, failed_phase=None,
        )
        summary = self._parse_sentinel(out)
        self.assertIn("Files pruned:       7", out)
        self.assertEqual(summary["pruned_count"], 7)


class PrimaryPhaseSummaryTests(unittest.TestCase):
    """Wave 1p8kz: the structured summary sentinel must surface at the END of the PRIMARY upgrade phase
    (phases 0–4, the default ``wf_upgrade()`` call) — not only on ``--cleanup`` — so an agent reading
    the primary upgrade response gets ``data.summary`` WITH the 1p8et reconciliation findings. The
    field gap (1.9.5 native-Windows): no summary on the primary call, persistent manual reconcile."""

    def setUp(self):
        if str(SCRIPTS_ROOT) not in sys.path:
            sys.path.insert(0, str(SCRIPTS_ROOT))
        self.mod = load_upgrade_module()

    def _emit_primary(self, root, from_v, to_v, pruned_count=0, index_published=True):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.mod._emit_primary_phase_summary(
                from_version=from_v, to_version=to_v, zip_path=None,
                pruned_count=pruned_count, root=Path(root) if root is not None else None,
                index_published=index_published,
            )
        return buf.getvalue()

    def _parse_sentinel(self, out):
        sentinel = self.mod.WAVE_UPGRADE_SUMMARY_SENTINEL
        return [json.loads(line[len(sentinel):]) for line in out.splitlines() if line.startswith(sentinel)]

    def test_emits_exactly_one_sentinel_line(self):
        out = self._emit_primary(None, "1.8.0", "1.9.0")
        summaries = self._parse_sentinel(out)
        self.assertEqual(len(summaries), 1, "primary phase must emit exactly one summary sentinel")

    def test_reconciliation_populated_on_minor_bump(self):
        # AC-1: a MINOR bump (1.8.0 → 1.9.0) runs the reconciliation scan; with a real root that has a
        # retired-surface reference, the sentinel's `reconciliation` carries the finding.
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "g.md").write_text("`.wavefoundry/bin/wave-gate`\n", encoding="utf-8")
            out = self._emit_primary(root, "1.8.0", "1.9.0")
            summary = self._parse_sentinel(out)[0]
            self.assertTrue(summary["is_major_or_minor"])
            self.assertEqual(len(summary["reconciliation"]), 1)
            self.assertEqual(summary["reconciliation"][0]["retired_surface"], "wave-gate")

    def test_reconciliation_populated_via_monkeypatched_scan_on_minor_bump(self):
        # AC-1 (monkeypatched form, per the task): a minor bump with _run_reconciliation_scan stubbed
        # to return a finding must surface that finding in the primary-phase sentinel.
        finding = [{"file": "x.md", "line": 1, "retired_surface": "docs-lint",
                    "matched": ".wavefoundry/bin/docs-lint", "suggested": "wf docs-lint"}]
        # 1p8o5/1u2az: _run_reconciliation_scan returns (reconciliation,
        # host_permission_flags, renderer_provenance_flags).
        with patch.object(self.mod, "_run_reconciliation_scan", return_value=(finding, [], [])):
            out = self._emit_primary("ignored-root-uses-stub", "1.8.0", "1.9.0")
        summary = self._parse_sentinel(out)[0]
        self.assertEqual(summary["reconciliation"], finding)

    def test_reconciliation_populated_on_patch_bump(self):
        # AC-6 (operator direction): the scan runs on EVERY upgrade — a PATCH bump (1.9.4 → 1.9.5) with
        # a retired-surface reference present DOES populate `reconciliation` (a patch can change/retire a
        # surface during testing). `is_major_or_minor` stays False (informational only — no longer gates).
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "g.md").write_text("`.wavefoundry/bin/wave-gate`\n", encoding="utf-8")
            out = self._emit_primary(root, "1.9.4", "1.9.5")
            summary = self._parse_sentinel(out)[0]
            self.assertFalse(summary["is_major_or_minor"])  # informational, not a gate
            self.assertEqual(len(summary["reconciliation"]), 1)
            self.assertEqual(summary["reconciliation"][0]["retired_surface"], "wave-gate")

    def test_scan_runs_on_patch_bump(self):
        # AC-6: a patch bump DOES invoke the scan (the major/minor gate was removed). Proven via a stub:
        # its return value now flows into the patch-bump sentinel.
        finding = [{"file": "x.md", "line": 1, "retired_surface": "docs-lint",
                    "matched": ".wavefoundry/bin/docs-lint", "suggested": "wf docs-lint"}]
        # 1p8o5/1u2az: stub returns the three-channel tuple.
        with patch.object(self.mod, "_run_reconciliation_scan", return_value=(finding, [], [])) as scan:
            out = self._emit_primary("some-root", "1.9.4", "1.9.5")
        summary = self._parse_sentinel(out)[0]
        scan.assert_called_once()
        self.assertEqual(summary["reconciliation"], finding)

    def test_reconciliation_populated_on_same_version_build_successor(self):
        # AC-6: a same-version build-successor (1.9.5 → 1.9.5 — a rebuilt pack at the same semver during
        # testing) ALSO runs the scan and populates reconciliation when stale refs exist.
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "g.md").write_text("`.wavefoundry/bin/wave-gate`\n", encoding="utf-8")
            out = self._emit_primary(root, "1.9.5", "1.9.5")
            summary = self._parse_sentinel(out)[0]
            self.assertFalse(summary["is_major_or_minor"])
            self.assertEqual(len(summary["reconciliation"]), 1)
            self.assertEqual(summary["reconciliation"][0]["retired_surface"], "wave-gate")

    def test_index_update_reflects_observed_publication_outcome(self):
        # 1u44n (re-pointed from the pre-fix hardcoded-True pin): index_update derives from the
        # OBSERVED Phase 4 publication result the caller passes in, never from the phase having
        # been attempted.
        out = self._emit_primary(None, "1.8.0", "1.9.0", index_published=True)
        summary = self._parse_sentinel(out)[0]
        self.assertEqual("docs and code layers complete", summary["index_update"])
        failed_out = self._emit_primary(None, "1.8.0", "1.9.0", index_published=False)
        failed_summary = self._parse_sentinel(failed_out)[0]
        self.assertTrue(
            failed_summary["index_update"].startswith("publication failed"),
            failed_summary["index_update"],
        )
        self.assertIn("index_health", failed_summary["index_update"])
        self.assertIn("index_build", failed_summary["index_update"])
        self.assertNotIn("running in background", failed_summary["index_update"])

    def test_primary_and_prose_render_from_same_builder(self):
        # AC-2: the primary-phase sentinel and the cleanup-phase prose sentinel are produced from the
        # one _build_upgrade_summary — assert identical sentinel JSON keys for the same inputs.
        primary_out = self._emit_primary(None, "1.8.0", "1.9.0", pruned_count=3)
        primary = self._parse_sentinel(primary_out)[0]
        prose_buf = io.StringIO()
        with contextlib.redirect_stdout(prose_buf):
            self.mod._print_operator_summary(
                from_version="1.8.0", to_version="1.9.0", zip_path=None,
                pruned_count=3, ran_index_rebuild=True, failed_phase=None, root=None,
            )
        prose_lines = [
            l for l in prose_buf.getvalue().splitlines()
            if l.startswith(self.mod.WAVE_UPGRADE_SUMMARY_SENTINEL)
        ]
        prose = json.loads(prose_lines[0][len(self.mod.WAVE_UPGRADE_SUMMARY_SENTINEL):])
        # Wave 1uf68 NARROWING (deliberate, not a weakening): the cleanup emit site
        # now sets SUMMARY_SCHEMA_KEY on the finished builder dict, so the two key
        # sets are no longer equal. The one-builder property this test exists to
        # protect survives as a SUPERSET assertion that names the schema token as
        # the ONLY permitted difference. Any other divergence still fails, which
        # is the drift hole that deleting the test would have opened.
        self.assertEqual(
            set(prose.keys()) - set(primary.keys()),
            {self.mod.SUMMARY_SCHEMA_KEY},
            "the cleanup summary may differ from the primary one in the schema "
            "token and nothing else",
        )
        self.assertEqual(
            set(primary.keys()) - set(prose.keys()), set(),
            "primary + cleanup summaries must share one _build_upgrade_summary shape",
        )
        # Same load-bearing values for the same inputs (one source, no drift).
        for k in ("from_version", "to_version", "pruned_count", "docs_gate", "is_major_or_minor"):
            self.assertEqual(primary[k], prose[k], f"key {k} drifted between the two emissions")

    def test_main_default_path_calls_emit_primary_phase_summary(self):
        # AC-1 (call-site, lighter harness per the task): the emit runs at the END of main()'s default
        # phases-0–4 path, BEFORE the "Phases 0–4 complete" log. Assert the call site via AST so a
        # refactor that drops it (re-stranding the summary to cleanup-only) fails — without driving a
        # real upgrade. Wave 1u44o (deliberate re-point, not a deletion): main()'s single emit site
        # is now `_emit_primary_summary_via_delegate_or_fallback`; the in-process
        # `_emit_primary_phase_summary` survives only as the delegator's degradation fallback and
        # must have NO direct call in main() (a second call would race the delegate under
        # last-sentinel-wins parsing).
        import ast as _ast
        tree = _ast.parse(UPGRADE_PATH.read_text(encoding="utf-8"))
        main_fn = next(
            (n for n in _ast.walk(tree)
             if isinstance(n, _ast.FunctionDef) and n.name == "main"), None
        )
        self.assertIsNotNone(main_fn, "upgrade_wavefoundry.main not found")
        calls = [
            n for n in _ast.walk(main_fn)
            if isinstance(n, _ast.Call) and isinstance(n.func, _ast.Name)
            and n.func.id == "_emit_primary_summary_via_delegate_or_fallback"
        ]
        self.assertEqual(
            len(calls), 1,
            "main() must call _emit_primary_summary_via_delegate_or_fallback exactly once "
            "on the default phase path",
        )
        direct_fallback_calls = [
            n for n in _ast.walk(main_fn)
            if isinstance(n, _ast.Call) and isinstance(n.func, _ast.Name)
            and n.func.id == "_emit_primary_phase_summary"
        ]
        self.assertEqual(
            direct_fallback_calls, [],
            "main() must never call the in-process fallback directly; it emits only "
            "through the mutually exclusive delegate-or-fallback site",
        )
        # And it must come BEFORE the "Phases 0–4 complete" log (the end of the default path).
        emit_line = calls[0].lineno
        complete_log_lines = [
            n.lineno for n in _ast.walk(main_fn)
            if isinstance(n, _ast.Call) and "Phases 0" in _ast.dump(n)
        ]
        if complete_log_lines:
            self.assertLess(emit_line, min(complete_log_lines),
                            "the primary-phase summary must emit before the 'Phases 0–4 complete' log")

    def test_fallback_emitter_is_called_only_from_the_delegator(self):
        # Wave 1u44o mutual-exclusion structural pin: module-wide, the in-process
        # fallback has exactly one caller; the single delegate-or-fallback emit
        # site; so a delegate success can never be followed by a fallback emit
        # from anywhere else (last-sentinel-wins hazard).
        import ast as _ast
        tree = _ast.parse(UPGRADE_PATH.read_text(encoding="utf-8"))
        callers: set[str] = set()
        for node in tree.body:
            if not isinstance(node, _ast.FunctionDef):
                continue
            for inner in _ast.walk(node):
                if (
                    isinstance(inner, _ast.Call)
                    and isinstance(inner.func, _ast.Name)
                    and inner.func.id == "_emit_primary_phase_summary"
                ):
                    callers.add(node.name)
        self.assertEqual(
            callers,
            {"_emit_primary_summary_via_delegate_or_fallback"},
            "the in-process fallback may only be invoked from the single "
            "mutually exclusive emit site",
        )


# ── Wave 1u44o: delegated primary-phase summary (post-extract subprocess backstop) ──

_DELEGATE_CHILD_MODULES = (
    "upgrade_wavefoundry.py",
    "upgrade_lib.py",
    "venv_bootstrap.py",
    "subprocess_util.py",
    "cli_stdio.py",
    "reconcile_scan.py",
    "render_platform_surfaces.py",
    "check_version.py",
)


def _stage_extracted_tree(root: Path, scripts_source: Path = SCRIPTS_ROOT) -> Path:
    """Copy the delegated-producer module set into *root*'s extracted-tree layout."""
    scripts = root / ".wavefoundry" / "framework" / "scripts"
    scripts.mkdir(parents=True, exist_ok=True)
    for name in _DELEGATE_CHILD_MODULES:
        shutil.copy2(scripts_source / name, scripts / name)
    return scripts


def _mismatched_reconcile_scan_stub(findings):
    """A future-shape reconcile_scan whose channel arity the in-process caller
    cannot unpack; the exact pg1a defect mechanism (old code calling a new
    module's API and eating the skew via the blanket except)."""
    import types as _types

    stub = _types.ModuleType("reconcile_scan")

    class _Ref:
        def __init__(self, d):
            self._d = d

        def as_dict(self):
            return dict(self._d)

    def scan_repo_channels(root):  # noqa: ARG001 - contract shape only
        # 4-tuple: a future channel arity the fixed 3-way unpack cannot take.
        return ([_Ref(f) for f in findings], [], [], [])

    stub.scan_repo_channels = scan_repo_channels
    return stub


class DelegatedSummaryPg1aReproductionTests(unittest.TestCase):
    """Wave 1u44o AC-3: reproduce the pg1a silent-empty-channel mechanism against
    the retained in-process path, then prove the delegated path repairs it."""

    FINDING = {"file": "g.md", "line": 1, "retired_surface": "wave-gate",
               "matched": ".wavefoundry/bin/wave-gate", "suggested": "wf gate"}

    def setUp(self):
        if str(SCRIPTS_ROOT) not in sys.path:
            sys.path.insert(0, str(SCRIPTS_ROOT))
        self.mod = load_upgrade_module()

    def _parse_sentinel(self, out):
        sentinel = self.mod.WAVE_UPGRADE_SUMMARY_SENTINEL
        return [json.loads(line[len(sentinel):])
                for line in out.splitlines() if line.startswith(sentinel)]

    def test_mismatched_scan_shape_yields_silent_empty_channels_in_process(self):
        # The pg1a mechanism, reproduced: the in-process caller unpacks a fixed
        # channel arity from `reconcile_scan.scan_repo_channels`; a module with a
        # DIFFERENT arity (here a future 4-channel shape) raises ValueError at the
        # unpack, and the blanket except swallows it into empty channels. The
        # findings the stub carries are silently lost; no error, no marker.
        stub = _mismatched_reconcile_scan_stub([self.FINDING])
        with patch.dict(sys.modules, {"reconcile_scan": stub}):
            result = self.mod._run_reconciliation_scan(Path("."))
        self.assertEqual(result, ([], [], []),
                         "shape skew must reproduce the silent empty channels")
        # And end to end through the retained in-process emitter: the sentinel
        # reports [] although the scan module had a finding.
        with patch.dict(sys.modules, {"reconcile_scan": stub}):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                self.mod._emit_primary_phase_summary(
                    from_version="1.14.0", to_version="1.15.0", zip_path=None,
                    pruned_count=0, root=Path("."), index_published=True,
                )
        summary = self._parse_sentinel(buf.getvalue())[0]
        self.assertEqual(summary["reconciliation"], [],
                         "the in-process path swallows the skew into []")

    def test_delegated_path_repairs_the_empty_channel(self):
        # AC-3 repair: with the SAME mismatched module poisoning the parent's
        # in-process import path, the parent's real emit site delegates to the
        # extracted tree's producer, which computes the scan fresh in its own
        # process; the finding flows into the sentinel end to end.
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "g.md").write_text(
                "`.wavefoundry/bin/wave-gate`\n", encoding="utf-8"
            )
            _stage_extracted_tree(root)
            lib = _load_upgrade_lib()
            lib.write_upgrade_lock(root, from_version="1.14.0", to_version="1.15.0")
            stub = _mismatched_reconcile_scan_stub([self.FINDING])
            buf = io.StringIO()
            with patch.dict(sys.modules, {"reconcile_scan": stub}), \
                    patch.object(self.mod, "_preferred_python",
                                 return_value=sys.executable), \
                    contextlib.redirect_stdout(buf):
                self.mod._emit_primary_summary_via_delegate_or_fallback(
                    root=root, from_version="1.14.0", to_version="1.15.0",
                    zip_path=None, pruned_count=0,
                    review_sidecar_cleanup=None, index_published=True,
                )
            summaries = self._parse_sentinel(buf.getvalue())
            self.assertEqual(len(summaries), 1, "exactly one sentinel per run")
            summary = summaries[0]
            self.assertEqual(len(summary["reconciliation"]), 1,
                             "the delegated producer must carry the finding")
            self.assertEqual(
                summary["reconciliation"][0]["retired_surface"], "wave-gate"
            )
            self.assertNotIn("summary_source_degraded", summary)
            self.assertEqual(summary["summary_schema_version"], 1)


def _write_stub_producer(root: Path, body: str) -> Path:
    """Write *body* as the fixture tree's upgrade_wavefoundry.py producer."""
    scripts = root / ".wavefoundry" / "framework" / "scripts"
    scripts.mkdir(parents=True, exist_ok=True)
    script = scripts / "upgrade_wavefoundry.py"
    script.write_text(body, encoding="utf-8")
    return script


class DelegatedSummaryContractTests(unittest.TestCase):
    """Wave 1u44o requirement 5: PERMANENT contract test.

    This test is the suite's standing guard for the entire fielded population of
    old runners: every runner that ships wave 1u44o invokes this exact surface
    on the freshly extracted tree of every future upgrade, forever. It locks the
    entry-point name, argv shape, output envelope, sentinel prefix VALUE, and
    version-token handling. The pins are a tripwire against ACCIDENTAL drift,
    not a wall: additive evolution needs no ceremony, and deliberate breaking
    evolution is supported by bumping SUMMARY_SCHEMA_VERSION (old parents then
    route to marked degradation for their transition run instead of
    mis-parsing) and updating these pins in the same change. If an edit makes
    this test fail WITHOUT that versioned-compatibility decision, the edit
    silently breaks fielded runners; that is the case this test exists to
    catch."""

    def setUp(self):
        if str(SCRIPTS_ROOT) not in sys.path:
            sys.path.insert(0, str(SCRIPTS_ROOT))
        self.mod = load_upgrade_module()

    def test_sentinel_prefix_value_is_frozen(self):
        # The literal VALUE, not just the constant name: fielded parsers match
        # this exact prefix.
        self.assertEqual(
            self.mod.WAVE_UPGRADE_SUMMARY_SENTINEL, "WAVE_UPGRADE_SUMMARY_JSON:"
        )

    def test_contract_constants_are_frozen(self):
        self.assertEqual(self.mod.SUMMARY_SCHEMA_KEY, "summary_schema_version")
        self.assertEqual(self.mod.SUMMARY_SCHEMA_VERSION, 1)
        self.assertIn(
            self.mod.SUMMARY_SCHEMA_VERSION, self.mod._RECOGNIZED_SUMMARY_SCHEMAS
        )
        self.assertEqual(
            self.mod.SUMMARY_DEGRADATION_MARKER_KEY, "summary_source_degraded"
        )
        timeout = self.mod._SUMMARY_DELEGATE_TIMEOUT_S
        self.assertIsInstance(timeout, (int, float))
        self.assertGreater(timeout, 0)
        # The entry-point flag literal exists in the module source (argparse
        # registration); a rename breaks every fielded caller.
        self.assertIn('"--emit-summary"', UPGRADE_PATH.read_text(encoding="utf-8"))

    def test_spawned_argv_shape_is_frozen_and_payload_reemitted_verbatim(self):
        payload = json.dumps(
            {"summary_schema_version": 1, "probe": "argv-pin \u2713"}, ensure_ascii=False
        )
        captured: dict = {}

        def fake_run(cmd, **kwargs):
            captured["cmd"] = list(cmd)
            captured["timeout"] = kwargs.get("timeout")
            return subprocess.CompletedProcess(
                cmd, 0,
                stdout=self.mod.WAVE_UPGRADE_SUMMARY_SENTINEL + payload + "\n",
                stderr="",
            )

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_stub_producer(root, "print('placeholder')\n")
            buf = io.StringIO()
            with patch.object(self.mod.subprocess_util, "isolated_run", fake_run), \
                    contextlib.redirect_stdout(buf):
                self.mod._emit_primary_summary_via_delegate_or_fallback(
                    root=root, from_version="1.14.0", to_version="1.15.0",
                    zip_path=None, pruned_count=0, index_published=True,
                )
            cmd = captured["cmd"]
            # Frozen argv shape: [python, <extracted script>, --emit-summary, --root, <root>]
            self.assertEqual(len(cmd), 5, cmd)
            self.assertEqual(
                Path(cmd[1]),
                root / ".wavefoundry" / "framework" / "scripts" / "upgrade_wavefoundry.py",
            )
            self.assertEqual(cmd[2], "--emit-summary")
            self.assertEqual(cmd[3], "--root")
            self.assertEqual(cmd[4], str(root))
            # The pinned timeout constant is what the spawn actually uses.
            self.assertEqual(captured["timeout"], self.mod._SUMMARY_DELEGATE_TIMEOUT_S)
            # Byte-verbatim re-emit under the parent's own sentinel constant.
            lines = [
                l for l in buf.getvalue().splitlines()
                if l.startswith(self.mod.WAVE_UPGRADE_SUMMARY_SENTINEL)
            ]
            self.assertEqual(len(lines), 1)
            self.assertEqual(
                lines[0], self.mod.WAVE_UPGRADE_SUMMARY_SENTINEL + payload
            )

    def test_real_child_envelope_and_old_schema_lock_tolerance(self):
        # The REAL producer, spawned as the contract argv, against a minimal
        # OLD-SCHEMA lock (only the fields the oldest FROM runners write): it
        # must exit 0 and emit exactly one sentinel line whose payload is a
        # JSON dict carrying the schema token; the inverse-skew named case.
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            scripts = _stage_extracted_tree(root)
            (root / ".wavefoundry" / "upgrade-in-progress.json").write_text(
                json.dumps({"from_version": "1.9.0", "to_version": "1.15.0"}),
                encoding="utf-8",
            )
            result = subprocess.run(
                [sys.executable, str(scripts / "upgrade_wavefoundry.py"),
                 "--emit-summary", "--root", str(root)],
                capture_output=True, text=True, timeout=120, check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            lines = [
                l for l in result.stdout.splitlines()
                if l.startswith(self.mod.WAVE_UPGRADE_SUMMARY_SENTINEL)
            ]
            self.assertEqual(len(lines), 1, "exactly one sentinel line")
            payload = json.loads(
                lines[0][len(self.mod.WAVE_UPGRADE_SUMMARY_SENTINEL):]
            )
            self.assertIsInstance(payload, dict)
            self.assertEqual(
                payload[self.mod.SUMMARY_SCHEMA_KEY], self.mod.SUMMARY_SCHEMA_VERSION
            )
            self.assertEqual(payload["from_version"], "1.9.0")
            self.assertEqual(payload["to_version"], "1.15.0")
            # Old-schema defaults: absent newer lock fields degrade cleanly.
            self.assertEqual(payload["pruned_count"], 0)
            self.assertEqual(payload["skipped_scan_locations"], [])
            self.assertNotIn(self.mod.SUMMARY_DEGRADATION_MARKER_KEY, payload)
            # Half-rename guard (wave 1u8o5): the REAL spawned producer's
            # payload must not carry the retired key. RAW literal on purpose:
            # post-rename SUMMARY_SCHEMA_KEY IS the new key, so the constant
            # form would assert the wrong thing.
            self.assertNotIn("summary_schema", payload)

    def test_real_child_reads_nonempty_skipped_scan_locations_from_lock(self):
        # Requirement 1 transport fidelity on the REAL producer: the parent-only
        # fact must round-trip through the lock into the child's summary. The
        # in-child module global is always empty, so a regression that drops the
        # lock-read override leaves the key present-but-empty and only THIS
        # assertion catches it (QA delivery lane, mutant D2).
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            scripts = _stage_extracted_tree(root)
            (root / ".wavefoundry" / "upgrade-in-progress.json").write_text(
                json.dumps({
                    "from_version": "1.15.0",
                    "to_version": "1.15.0",
                    "skipped_scan_locations": ["/probe/Downloads"],
                }),
                encoding="utf-8",
            )
            result = subprocess.run(
                [sys.executable, str(scripts / "upgrade_wavefoundry.py"),
                 "--emit-summary", "--root", str(root)],
                capture_output=True, text=True, timeout=120, check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            lines = [
                l for l in result.stdout.splitlines()
                if l.startswith(self.mod.WAVE_UPGRADE_SUMMARY_SENTINEL)
            ]
            self.assertEqual(len(lines), 1, "exactly one sentinel line")
            payload = json.loads(
                lines[0][len(self.mod.WAVE_UPGRADE_SUMMARY_SENTINEL):]
            )
            self.assertEqual(
                payload["skipped_scan_locations"], ["/probe/Downloads"]
            )

    def test_unrecognized_version_token_routes_to_degradation(self):
        # Requirement 5: an unrecognized token is the degradation path, NEVER
        # new-schema output (closes the silent-drift case a launch-failure
        # marker cannot see).
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_stub_producer(
                root,
                "print('WAVE_UPGRADE_SUMMARY_JSON:'"
                " + '{\"summary_schema_version\": 999, \"probe\": \"x\"}')\n",
            )
            buf = io.StringIO()
            with patch.object(self.mod, "_preferred_python",
                              return_value=sys.executable), \
                    contextlib.redirect_stdout(buf):
                self.mod._emit_primary_summary_via_delegate_or_fallback(
                    root=root, from_version="1.14.0", to_version="1.15.0",
                    zip_path=None, pruned_count=0, index_published=True,
                )
            lines = [
                l for l in buf.getvalue().splitlines()
                if l.startswith(self.mod.WAVE_UPGRADE_SUMMARY_SENTINEL)
            ]
            self.assertEqual(len(lines), 1)
            summary = json.loads(
                lines[0][len(self.mod.WAVE_UPGRADE_SUMMARY_SENTINEL):]
            )
            self.assertEqual(
                summary[self.mod.SUMMARY_DEGRADATION_MARKER_KEY],
                "unrecognized_schema_token_999",
            )
            self.assertNotIn(self.mod.SUMMARY_SCHEMA_KEY, summary)
            self.assertNotIn("probe", summary, "unrecognized-token output must be discarded")

    # ── Wave 1uf68: the cleanup emit site carries the schema token ─────────
    #
    # The token used to be delegation-exclusive, so on every run that emits a
    # summary WITHOUT the delegated producer (the checkpoint pause's recovery
    # cleanup, --resume-after-memory's, and every ordinary cleanup) "token
    # absent" and "token dropped or drifted" were indistinguishable, so the drift
    # tripwire was unobservable on exactly the runs that deviated.
    # `_print_operator_summary` is reachable ONLY through main()'s
    # `if args.cleanup:` branch (upgrade_wavefoundry.py:4350), so these pins
    # drive `main(["--cleanup"])` rather than calling the emitter directly: that
    # reachability IS the mechanism by which one insertion covers all three
    # token-less windows, and asserting it is what makes the fix real.

    def _cleanup_ready_root(self, **lock_fields):
        """A temp repo whose upgrade lock passes main()'s pre-cleanup gates.

        main() refuses `--cleanup` BEFORE `phase_cleanup` unless historical
        memory is `indexed` (upgrade_wavefoundry.py:4189-4219). That refusal
        emits no summary at all (exit 4, zero sentinels) and is censused out of
        scope for wave 1uf68, so the fixture satisfies it with a real indexed
        backfill run and the pins stay on the emit contract.

        Disclosure for the failure-branch caller: marking memory indexed while
        also setting `failed_phase="awaiting_memory_validation"` is a SYNTHETIC
        lock combination. A real pause-without-resume run has memory unmarked
        and is refused by the gate above, so it never reaches `phase_cleanup`;
        its documented recovery (`--resume-after-memory` then `--cleanup`)
        clears `failed_phase` and takes the SUCCESS branch. The failure branch
        is independently reachable from any other `failed_phase` value; this
        fixture just lets the pin use the pause's own value.
        """
        import memory_backfill

        lib = _load_upgrade_lib()
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        (root / ".wavefoundry" / "index").mkdir(parents=True, exist_ok=True)
        (root / "docs" / "waves").mkdir(parents=True, exist_ok=True)
        run_id = memory_backfill.ensure_run(root, "upgrade")
        memory_backfill.sync_inventory(root, run_id)
        memory_backfill.mark_indexed(root, run_id)
        lib.write_upgrade_lock(root, "1.15.2", "1.15.3")
        lib.update_upgrade_lock(
            root,
            memory_backfill_run_id=run_id,
            memory_backfill_state="indexed",
            **lock_fields,
        )
        return root

    def _drive_cleanup(self, root, *, expect_exit=False):
        """Run `main(["--root", root, "--cleanup"])` and return (stdout, code).

        Only the rendered-permissions backstop is patched out: it spawns the
        real renderer subprocess and has nothing to do with the emit seam. The
        summary sentinel is read from real captured stdout.
        """
        buf = io.StringIO()
        with patch.object(self.mod, "_ensure_rendered_permissions_backstop"), \
                contextlib.redirect_stdout(buf):
            if expect_exit:
                with self.assertRaises(SystemExit) as caught:
                    self.mod.main(["--root", str(root), "--cleanup"])
                code = caught.exception.code
            else:
                code = self.mod.main(["--root", str(root), "--cleanup"])
        return buf.getvalue(), code

    def _cleanup_sentinels(self, out):
        sentinel = self.mod.WAVE_UPGRADE_SUMMARY_SENTINEL
        return [
            json.loads(line[len(sentinel):])
            for line in out.splitlines()
            if line.startswith(sentinel)
        ]

    def test_checkpoint_pause_recovery_cleanup_carries_the_schema_token(self):
        """Wave 1uf68 requirement 6(a) / AC-1: the FAILURE branch of
        `phase_cleanup` (`:2489`) carries the token too. The token is a
        SELF-WITNESSING claim about the code that RENDERED the summary, not a
        claim that the upgrade succeeded; `failed_phase` remains the success
        discriminator, and cleanup reads it at `:4326`.

        The `failed_phase` used here is the value the memory checkpoint stamps
        (`:4890`), but see `_cleanup_ready_root`: a real pause-without-resume
        run is refused by the pre-cleanup memory gate with exit 4 and no
        sentinel, and its documented recovery takes the SUCCESS branch. This
        fixture force-marks memory indexed so the failure branch is reachable
        with that value; the branch itself is reachable from any other
        `failed_phase` too."""
        root = self._cleanup_ready_root(
            failed_phase="awaiting_memory_validation",
            failed_at=None,
            action_required={
                "kind": "historical_memory",
                "state": "awaiting_memory_validation",
                "resume_phase": "resume_after_memory",
                "run_id": "probe-run",
                "token": "probe-token",
            },
        )
        out, code = self._drive_cleanup(root, expect_exit=True)
        self.assertEqual(code, 1, out)
        summaries = self._cleanup_sentinels(out)
        self.assertEqual(len(summaries), 1, out)
        summary = summaries[0]
        self.assertEqual(
            summary.get(self.mod.SUMMARY_SCHEMA_KEY),
            self.mod.SUMMARY_SCHEMA_VERSION,
            "the recovery cleanup summary must carry the schema token",
        )
        # Non-vacuity: this really is the failure branch, and the token is not
        # riding in on a degradation disclosure.
        self.assertEqual(summary["failed_phase"], "awaiting_memory_validation")
        self.assertNotIn(self.mod.SUMMARY_DEGRADATION_MARKER_KEY, summary)

    def test_nominal_cleanup_carries_the_schema_token_on_both_lock_shapes(self):
        """Wave 1uf68 requirement 6(b) / AC-1: the ordinary success branch
        (`:2558`). The post-resume lock shape is a lock-shape parameterization
        of THIS case, not a separate window: `--resume-after-memory` clears
        `failed_phase` (`:4154-4157`) and stamps `index_rebuilt_at` (`:4150`),
        which cleanup reads as `ran_index_rebuild=True` (`:4320`); with
        `failed_phase=None` the path is identical, so it is a subTest rather
        than independent coverage. Parsing the REAL sentinel out of captured
        stdout is load-bearing: patching `_emit_summary_line` or asserting on
        `_build_upgrade_summary`'s return value would bypass the emit seam and
        be vacuous."""
        shapes = (
            ("fresh cleanup", {}, "not run"),
            (
                "post-resume",
                {
                    "index_rebuilt_at": "2026-08-04T00:00:00+00:00",
                    "action_required": None,
                    "failed_phase": None,
                },
                "docs and code layers complete",
            ),
        )
        for label, lock_fields, expected_index_update in shapes:
            with self.subTest(lock_shape=label):
                root = self._cleanup_ready_root(**lock_fields)
                out, code = self._drive_cleanup(root)
                self.assertEqual(code, 0, out)
                summaries = self._cleanup_sentinels(out)
                self.assertEqual(len(summaries), 1, out)
                summary = summaries[0]
                self.assertEqual(
                    summary.get(self.mod.SUMMARY_SCHEMA_KEY),
                    self.mod.SUMMARY_SCHEMA_VERSION,
                    "the nominal cleanup summary must carry the schema token",
                )
                self.assertIsNone(summary["failed_phase"])
                # The two lock shapes really do reach the emitter differently,
                # so the subTest is not decorative.
                self.assertIn(expected_index_update, summary["index_update"])

    def test_shared_builder_never_carries_the_schema_token(self):
        """Wave 1uf68 requirement 6(c) / AC-2: the token lives at the EMIT site,
        never in the shared builder. `_build_upgrade_summary` also produces the
        primary-phase degradation fallback, whose documented invariant (`:3019`)
        is that it never carries the token (pinned at `:5600-5601`); a token in
        the builder would make the fallback claim fresh-code provenance it does
        not have, the opposite of this fix."""
        summary = self.mod._build_upgrade_summary(
            from_version="1.15.2",
            to_version="1.15.3",
            zip_path=None,
            pruned_count=0,
            ran_index_rebuild=True,
            failed_phase=None,
            reconciliation=[],
        )
        self.assertNotIn(self.mod.SUMMARY_SCHEMA_KEY, summary)
        self.assertNotIn("summary_schema_version", summary)


class DelegatedSummaryDegradationTests(unittest.TestCase):
    """Wave 1u44o AC-2: each named failure class degrades to the parent's own
    in-process summary with the marker present, the exit status unchanged (the
    emit site never raises), and the fallback never labeled as new-schema."""

    def setUp(self):
        if str(SCRIPTS_ROOT) not in sys.path:
            sys.path.insert(0, str(SCRIPTS_ROOT))
        self.mod = load_upgrade_module()

    def _drive(self, root, timeout_s=None):
        buf = io.StringIO()
        kwargs = {} if timeout_s is None else {"timeout_s": timeout_s}
        with patch.object(self.mod, "_preferred_python",
                          return_value=sys.executable), \
                contextlib.redirect_stdout(buf):
            # Never raises; a delegation failure must not change the upgrade's
            # exit status (main() returns 0 after this site on the default path).
            self.mod._emit_primary_summary_via_delegate_or_fallback(
                root=root, from_version="1.14.0", to_version="1.15.0",
                zip_path=None, pruned_count=2, index_published=True, **kwargs
            )
        out = buf.getvalue()
        sentinel = self.mod.WAVE_UPGRADE_SUMMARY_SENTINEL
        summaries = [
            json.loads(line[len(sentinel):])
            for line in out.splitlines() if line.startswith(sentinel)
        ]
        return summaries, out

    def _assert_marked_degradation(self, summaries, expected_marker):
        self.assertEqual(len(summaries), 1, "exactly one sentinel per run")
        summary = summaries[0]
        marker = summary.get(self.mod.SUMMARY_DEGRADATION_MARKER_KEY)
        self.assertEqual(marker, expected_marker)
        # The marker must stay flat and small so it also survives the
        # unknown-scalar budget path on a pre-registration server.
        self.assertIsInstance(marker, str)
        self.assertLess(len(marker), 120)
        # The fallback is the parent's own old-schema summary; it must never
        # present itself as new-schema output.
        self.assertNotIn(self.mod.SUMMARY_SCHEMA_KEY, summary)
        # And it is a real summary, not a stub: parent-known fields intact.
        self.assertEqual(summary["from_version"], "1.14.0")
        self.assertEqual(summary["pruned_count"], 2)
        return summary

    def test_entry_point_absent_is_marker_carrying_degradation(self):
        # Class 1 (the realistic downgrade / pack-older-than-this-change case
        # when the script itself is gone). The prior-art silent
        # `if not script.exists(): return` shape is the anti-pattern: this MUST
        # carry the marker.
        with tempfile.TemporaryDirectory() as td:
            summaries, _ = self._drive(Path(td))
        self._assert_marked_degradation(summaries, "entry_point_absent")

    def test_old_pack_rejecting_the_flag_degrades_with_exit_status(self):
        # Class 1 variant: the extracted tree EXISTS but predates the flag -
        # argparse rejects --emit-summary with exit 2.
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_stub_producer(
                root,
                "import argparse\n"
                "p = argparse.ArgumentParser()\n"
                "p.add_argument('--root', default='.')\n"
                "p.parse_args()\n",
            )
            summaries, _ = self._drive(root)
        self._assert_marked_degradation(summaries, "exit_status_2")

    def test_nonzero_child_exit_degrades(self):
        # Class 2.
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_stub_producer(root, "import sys\nsys.exit(7)\n")
            summaries, _ = self._drive(root)
        self._assert_marked_degradation(summaries, "exit_status_7")

    def test_malformed_or_absent_sentinel_degrades(self):
        # Class 3: absent sentinel, malformed JSON, and non-dict payload.
        bodies = (
            "print('no sentinel here')\n",
            "print('WAVE_UPGRADE_SUMMARY_JSON:{not json')\n",
            "print('WAVE_UPGRADE_SUMMARY_JSON:[1, 2]')\n",
        )
        for body in bodies:
            with self.subTest(body=body):
                with tempfile.TemporaryDirectory() as td:
                    root = Path(td)
                    _write_stub_producer(root, body)
                    summaries, _ = self._drive(root)
                self._assert_marked_degradation(
                    summaries, "sentinel_missing_or_malformed"
                )

    def test_timeout_degrades_with_injected_deadline(self):
        # Class 4: the timeout is injectable for the test; production uses the
        # pinned _SUMMARY_DELEGATE_TIMEOUT_S constant (contract test asserts
        # the spawn passes it).
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_stub_producer(root, "import time\ntime.sleep(30)\n")
            summaries, _ = self._drive(root, timeout_s=1)
        self._assert_marked_degradation(summaries, "timeout_after_1s")

    def test_old_key_parent_against_new_key_payload_degrades_marked(self):
        # Cross-version transition (wave 1u8o5): a fielded parent that still
        # recognizes the OLD key ("summary_schema") receives the real NEW-key
        # payload and must take exactly one MARKED degradation run - the
        # disclosed one-run cost for the pg8h/pg9m runners. Simulating the old
        # recognizer by patching SUMMARY_SCHEMA_KEY back to the old literal is
        # faithful because the census proved every functional lookup (producer
        # emission and parent recognition alike) routes through
        # SUMMARY_SCHEMA_KEY; no functional code path names the key literally.
        payload = json.dumps(
            {"summary_schema_version": 1, "probe": "cross-version"}
        )
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_stub_producer(
                root, f"print('WAVE_UPGRADE_SUMMARY_JSON:' + {payload!r})\n"
            )
            buf = io.StringIO()
            with patch.object(self.mod, "SUMMARY_SCHEMA_KEY",
                              "summary_schema"), \
                    patch.object(self.mod, "_preferred_python",
                                 return_value=sys.executable), \
                    contextlib.redirect_stdout(buf):
                self.mod._emit_primary_summary_via_delegate_or_fallback(
                    root=root, from_version="1.14.0", to_version="1.15.0",
                    zip_path=None, pruned_count=2, index_published=True,
                )
        sentinel = self.mod.WAVE_UPGRADE_SUMMARY_SENTINEL
        summaries = [
            json.loads(line[len(sentinel):])
            for line in buf.getvalue().splitlines()
            if line.startswith(sentinel)
        ]
        self.assertEqual(len(summaries), 1, "exactly one sentinel per run")
        summary = summaries[0]
        # Exact equality: the old recognizer's .get on its old key yields None,
        # so the marker is the None-clamp token, nothing else.
        self.assertEqual(
            summary["summary_source_degraded"],
            "unrecognized_schema_token_None",
        )
        # The fallback is the parent's REAL summary, not a stub.
        self.assertEqual(summary["from_version"], "1.14.0")
        self.assertEqual(summary["pruned_count"], 2)
        # And it carries no schema key under either name: a fallback summary
        # is never presented as schema-versioned output.
        self.assertNotIn("summary_schema", summary)
        self.assertNotIn("summary_schema_version", summary)

    def test_successful_delegate_forbids_the_fallback(self):
        # The delegate-succeeded-then-fallback-also-fires ordering hazard,
        # driven and proven impossible: the fallback emitter is replaced by a
        # canary that fails the test if invoked after a successful delegation,
        # and exactly one sentinel reaches the output.
        payload = json.dumps({"summary_schema_version": 1, "probe": "only-once"})

        def canary(*args, **kwargs):
            raise AssertionError(
                "fallback fired after a successful delegation; the last-wins "
                "sentinel hazard the single emit site exists to prevent"
            )

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_stub_producer(
                root, f"print('WAVE_UPGRADE_SUMMARY_JSON:' + {payload!r})\n"
            )
            buf = io.StringIO()
            with patch.object(self.mod, "_preferred_python",
                              return_value=sys.executable), \
                    patch.object(self.mod, "_emit_primary_phase_summary",
                                 side_effect=canary), \
                    contextlib.redirect_stdout(buf):
                self.mod._emit_primary_summary_via_delegate_or_fallback(
                    root=root, from_version="1.14.0", to_version="1.15.0",
                    zip_path=None, pruned_count=0, index_published=True,
                )
            lines = [
                l for l in buf.getvalue().splitlines()
                if l.startswith(self.mod.WAVE_UPGRADE_SUMMARY_SENTINEL)
            ]
            self.assertEqual(len(lines), 1, "exactly one sentinel per run")
            self.assertEqual(
                json.loads(lines[0][len(self.mod.WAVE_UPGRADE_SUMMARY_SENTINEL):])["probe"],
                "only-once",
            )


class DelegatedSummarySchemaDivergentTests(unittest.TestCase):
    """Wave 1u44o AC-1: the anti-vacuity fixture: the extracted tree carries a
    SCHEMA-DIVERGENT producer emitting a probe field the parent's own
    `_build_upgrade_summary` cannot produce; only real delegation can transport
    it. A same-schema fixture (extracting the current scripts) cannot satisfy
    this test."""

    PROBE_KEY = "probe_from_future_schema"
    PROBE_VALUE = "delegation-transport-proof \u2713"

    STUB = (
        "import argparse, json\n"
        "from pathlib import Path\n"
        "p = argparse.ArgumentParser()\n"
        "p.add_argument('--emit-summary', action='store_true')\n"
        "p.add_argument('--root', required=True)\n"
        "a = p.parse_args()\n"
        "root = Path(a.root)\n"
        "lock_path = root / '.wavefoundry' / 'upgrade-in-progress.json'\n"
        "lock = json.loads(lock_path.read_text(encoding='utf-8')) if lock_path.exists() else {}\n"
        "payload = {\n"
        "    'summary_schema_version': 1,\n"
        "    'from_version': lock.get('from_version'),\n"
        "    'to_version': lock.get('to_version'),\n"
        "    'probe_from_future_schema': 'delegation-transport-proof \\u2713',\n"
        "    'producer_script_path': str(Path(__file__).resolve()),\n"
        "    'skipped_scan_locations': lock.get('skipped_scan_locations') or [],\n"
        "}\n"
        "text = json.dumps(payload, ensure_ascii=False)\n"
        "(root / 'child-payload.txt').write_text(text, encoding='utf-8')\n"
        "print('WAVE_UPGRADE_SUMMARY_JSON:' + text)\n"
    )

    def setUp(self):
        if str(SCRIPTS_ROOT) not in sys.path:
            sys.path.insert(0, str(SCRIPTS_ROOT))
        self.mod = load_upgrade_module()

    def test_probe_field_transports_through_the_parents_real_emit_path(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_stub_producer(root, self.STUB)
            # An OLD-SCHEMA lock (fields absent that only newer runners write);
            # the parent will persist the parent-only fact into it below.
            (root / ".wavefoundry" / "upgrade-in-progress.json").write_text(
                json.dumps({"from_version": "1.14.0", "to_version": "1.15.0"}),
                encoding="utf-8",
            )
            buf = io.StringIO()
            with patch.object(self.mod, "_preferred_python",
                              return_value=sys.executable), \
                    patch.object(self.mod, "_PACK_SCAN_SKIPPED",
                                 ["/probe/Downloads"]), \
                    contextlib.redirect_stdout(buf):
                # The parent's REAL emit path (the single site main() calls) -
                # not the producer function.
                self.mod._emit_primary_summary_via_delegate_or_fallback(
                    root=root, from_version="1.14.0", to_version="1.15.0",
                    zip_path=None, pruned_count=0, index_published=True,
                )
            out = buf.getvalue()
            sentinel = self.mod.WAVE_UPGRADE_SUMMARY_SENTINEL
            lines = [l for l in out.splitlines() if l.startswith(sentinel)]
            self.assertEqual(len(lines), 1, "exactly one sentinel per run")
            emitted_payload = lines[0][len(sentinel):]
            # Byte-verbatim transport: the parent re-emits the child's payload
            # text unchanged (the child recorded its exact bytes to a side file).
            self.assertEqual(
                emitted_payload,
                (root / "child-payload.txt").read_text(encoding="utf-8"),
            )
            summary = json.loads(emitted_payload)
            # The probe can ONLY have come through delegation…
            self.assertEqual(summary[self.PROBE_KEY], self.PROBE_VALUE)
            # …because the parent's own builder cannot produce it.
            parent_summary = self.mod._build_upgrade_summary(
                from_version="1.14.0", to_version="1.15.0", zip_path=None,
                pruned_count=0, ran_index_rebuild=True, failed_phase=None,
                reconciliation=[],
            )
            self.assertNotIn(self.PROBE_KEY, parent_summary)
            # The spawned argv resolved INSIDE the extracted fixture tree.
            producer_path = Path(summary["producer_script_path"])
            self.assertEqual(
                producer_path,
                (root / ".wavefoundry" / "framework" / "scripts"
                 / "upgrade_wavefoundry.py").resolve(),
            )
            # Parent-only fact round-trip: persisted to the lock BEFORE the
            # spawn, read back by the (old-schema-tolerant) producer.
            self.assertEqual(summary["skipped_scan_locations"], ["/probe/Downloads"])
            self.assertNotIn(self.mod.SUMMARY_DEGRADATION_MARKER_KEY, summary)
            # Parser-side: the probe survives the old server's parse + bound
            # layers (the wf_upgrade_response-level test lives in
            # test_server_tools.py).
            import server_impl

            parsed = server_impl._parse_upgrade_summary(out)
            self.assertIsNotNone(parsed)
            bounded = server_impl._bounded_upgrade_summary(parsed)
            self.assertEqual(bounded[self.PROBE_KEY], self.PROBE_VALUE)


class DetectDashboardLivenessTests(unittest.TestCase):
    """Wave 1p654 review follow-up: upgrade dashboard detection cmdline-verifies the
    recorded PID (a bare os.kill accepts a zombie / recycled PID)."""

    def setUp(self):
        self.mod = load_upgrade_module()
        if str(SCRIPTS_ROOT) not in sys.path:
            sys.path.insert(0, str(SCRIPTS_ROOT))
        import dashboard_lib
        self.dashboard_lib = dashboard_lib
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / ".wavefoundry").mkdir(parents=True)

    def tearDown(self):
        self.tmp.cleanup()

    def _write_lock(self, pid):
        (self.root / ".wavefoundry" / "dashboard-server.lock").write_text(
            json.dumps({"pid": pid, "url": "http://127.0.0.1:43127/dashboard.html"}),
            encoding="utf-8",
        )

    def test_recycled_pid_rejected_by_cmdline_scan(self):
        self._write_lock(999999)
        with patch.object(self.dashboard_lib, "dashboard_cmdline_pids", return_value=[]):
            self.assertEqual(self.mod._detect_dashboard(self.root), (False, None, None))

    def test_matched_live_pid_detected(self):
        self._write_lock(os.getpid())
        with patch.object(self.dashboard_lib, "dashboard_cmdline_pids", return_value=[os.getpid()]):
            running, pid, url = self.mod._detect_dashboard(self.root)
        self.assertTrue(running)
        self.assertEqual(pid, os.getpid())

    def test_scan_unavailable_falls_back_to_pid_liveness_helper(self):
        # Wave 1p9hi: when the cmdline scan is unavailable (Windows / ps-error → None), _detect_dashboard
        # must fall back to the cross-OS upgrade_lib._pid_is_running helper, NOT a bare os.kill(pid, 0)
        # (which on Windows is GenerateConsoleCtrlEvent/TerminateProcess, not a liveness probe). Assert
        # BOTH the live and dead branches by patching the helper — this exercises the fallback contract
        # without depending on POSIX signal-0 semantics (the old test only ever ran the POSIX path).
        import upgrade_lib
        self._write_lock(4242)
        with patch.object(self.dashboard_lib, "dashboard_cmdline_pids", return_value=None):
            with patch.object(upgrade_lib, "_pid_is_running", return_value=True) as live_probe:
                running, pid, url = self.mod._detect_dashboard(self.root)
            self.assertTrue(running)
            self.assertEqual(pid, 4242)
            live_probe.assert_called_once_with(4242)
            with patch.object(upgrade_lib, "_pid_is_running", return_value=False) as dead_probe:
                running_dead, pid_dead, url_dead = self.mod._detect_dashboard(self.root)
            self.assertEqual((running_dead, pid_dead, url_dead), (False, None, None))
            dead_probe.assert_called_once_with(4242)

    @unittest.skipIf(sys.platform == "win32", "POSIX holder probe uses fcntl in this test")
    def test_held_canonical_lifetime_lock_overrides_missing_metadata(self):
        import dashboard_lib
        from runtime_lock import RuntimeFileLock

        path = dashboard_lib.dashboard_metadata_path(self.root)
        path.parent.mkdir(parents=True, exist_ok=True)
        holder = RuntimeFileLock(
            path,
            blocking=False,
            offset=dashboard_lib._LOCK_BYTE_OFFSET,
        )
        holder.acquire()
        try:
            path.write_text("{}\n", encoding="utf-8")
            self.assertEqual(
                self.mod._detect_dashboard(self.root),
                (True, None, None),
            )
        finally:
            holder.release()


class WindowsTempPathRobustnessTests(unittest.TestCase):
    """Wave 1p8gv: the `/tmp` fallback raised FileNotFoundError copying the pre-upgrade MANIFEST on
    native Windows. The temp dir must come from tempfile.gettempdir() (cross-OS), not a hardcoded
    POSIX path."""

    def test_old_manifest_tmp_uses_gettempdir_not_slash_tmp(self):
        mod = load_upgrade_module()
        self.assertEqual(
            mod.OLD_MANIFEST_TMP.parent, Path(tempfile.gettempdir()),
            "OLD_MANIFEST_TMP must live under tempfile.gettempdir(), not a hardcoded /tmp",
        )
        self.assertEqual(mod.OLD_MANIFEST_TMP.name, "wf-manifest-old.txt")

    def test_no_hardcoded_tmp_or_tmpdir_fallback_in_source(self):
        src = UPGRADE_PATH.read_text(encoding="utf-8")
        self.assertNotIn('os.environ.get("TMPDIR", "/tmp")', src)
        self.assertIn("tempfile.gettempdir()", src)

    def test_old_manifest_copy_resolves_on_windows_style_temp(self):
        # Simulate a Windows-style temp dir (no real /tmp dependency): the MANIFEST copy target must
        # resolve under it and be writable (mirrors shutil.copy2(old_manifest, OLD_MANIFEST_TMP)).
        with tempfile.TemporaryDirectory() as win_temp:
            with patch.object(tempfile, "gettempdir", return_value=win_temp):
                target = Path(tempfile.gettempdir()) / "wf-manifest-old.txt"
            target.write_text("MANIFEST line\n", encoding="utf-8")
            self.assertTrue(target.exists())
            self.assertEqual(target.read_text(encoding="utf-8"), "MANIFEST line\n")


class UpgradeCliEncodingTests(unittest.TestCase):
    """Wave 1p8gv: the upgrade CLI reconfigures stdio to UTF-8 (so `⚠` prints never raise on a cp1252
    console) and captures child output as UTF-8 (so it decodes cleanly across OSes)."""

    def test_module_reconfigures_stdio_at_import(self):
        src = UPGRADE_PATH.read_text(encoding="utf-8")
        self.assertIn("import cli_stdio", src)
        self.assertIn("cli_stdio.configure_utf8_stdio()", src)

    def test_captured_prune_spawn_routes_through_isolated_run(self):
        src = UPGRADE_PATH.read_text(encoding="utf-8")
        self.assertIn(
            "subprocess_util.isolated_run(cmd, cwd=str(root), capture_output=True, text=True, check=False)",
            src,
        )

    def test_no_bare_capture_output_text_subprocess_run_in_upgrade(self):
        # AC-3 source-scan: no captured `subprocess.run(..., text=True)` may remain bare — all route
        # through subprocess_util.isolated_run (which folds in encoding="utf-8", errors="replace").
        import re
        src_lines = UPGRADE_PATH.read_text(encoding="utf-8").splitlines()
        offenders = []
        for i, line in enumerate(src_lines):
            if re.search(r"\bsubprocess\.run\(", line):
                window = "\n".join(src_lines[i:i + 6])
                if "text=True" in window or "capture_output=True" in window:
                    offenders.append(f"{i + 1}: {line.strip()}")
        self.assertEqual(
            offenders, [],
            "captured subprocess.run(..., text=True) must route through subprocess_util.isolated_run "
            "(UTF-8 capture encoding):\n" + "\n".join(offenders),
        )


class SandboxResilientPackDiscoveryTests(unittest.TestCase):
    """1p8xl: a permission/sandbox error on one pack-search location (e.g. macOS-TCC ~/Downloads) must
    not abort discovery — it is logged, skipped, recorded, and surfaced in the upgrade summary."""

    class _Sandboxed:
        """A search-dir stand-in that EXISTS but raises PermissionError on iterdir (macOS TCC)."""

        def __init__(self, label: str) -> None:
            self._label = label

        def expanduser(self):
            return self

        def is_dir(self) -> bool:
            return True

        def iterdir(self):
            raise PermissionError("Operation not permitted")

        def __str__(self) -> str:
            return self._label

    def setUp(self) -> None:
        self.mod = load_upgrade_module()
        self.mod._PACK_SCAN_SKIPPED.clear()

    def test_scan_dir_entries_skips_and_records_on_permission_error(self):
        # AC-1 mechanism + AC-2 record: an unreadable location returns None (skip) and is recorded.
        with contextlib.redirect_stdout(io.StringIO()):
            result = self.mod._scan_dir_entries(self._Sandboxed("/Users/x/Downloads"))
        self.assertIsNone(result)
        self.assertIn("/Users/x/Downloads", self.mod._PACK_SCAN_SKIPPED)

    def test_scan_dir_entries_lists_readable_dir(self):
        # AC-3: a readable location returns its listing and records no skip.
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "a.txt").write_text("x", encoding="utf-8")
            result = self.mod._scan_dir_entries(Path(d))
        self.assertIsNotNone(result)
        self.assertEqual(self.mod._PACK_SCAN_SKIPPED, [])

    def test_find_latest_release_zip_resilient_to_unreadable_location(self):
        # AC-1 end-to-end: one location raises PermissionError, discovery still returns the pack from
        # the readable locations and does not raise.
        with tempfile.TemporaryDirectory() as good:
            good_p = Path(good)
            (good_p / "wavefoundry-1.2.3.abcd.zip").write_text("x", encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()), \
                 patch.object(self.mod, "_HOME_DIR", good_p), \
                 patch.object(self.mod, "_HOME_WAVEFOUNDRY_DIR", good_p), \
                 patch.object(self.mod, "_DIST_DIR", good_p), \
                 patch.object(self.mod, "_DOWNLOADS_DIR", self._Sandboxed("/fake/Downloads")):
                result = self.mod._find_latest_release_zip(good_p)
        self.assertIsNotNone(result, "must return the pack from the readable location")
        self.assertEqual(result.name, "wavefoundry-1.2.3.abcd.zip")
        self.assertIn("/fake/Downloads", self.mod._PACK_SCAN_SKIPPED)

    def test_print_all_release_zips_resilient_to_unreadable_location(self):
        # AC-4: the --list-zips path is equally resilient — a sandboxed location is skipped, not fatal.
        with tempfile.TemporaryDirectory() as good:
            good_p = Path(good)
            (good_p / "wavefoundry-1.2.3.abcd.zip").write_text("x", encoding="utf-8")
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf), \
                 patch.object(self.mod, "_HOME_DIR", good_p), \
                 patch.object(self.mod, "_HOME_WAVEFOUNDRY_DIR", good_p), \
                 patch.object(self.mod, "_DIST_DIR", good_p), \
                 patch.object(self.mod, "_DOWNLOADS_DIR", self._Sandboxed("/fake/Downloads")):
                self.mod._print_all_release_zips(good_p)  # must not raise
        self.assertIn("wavefoundry-1.2.3.abcd.zip", buf.getvalue())

    def test_summary_surfaces_skipped_scan_locations(self):
        # AC-2 surfacing: the recorded skips appear in the upgrade summary dict.
        self.mod._PACK_SCAN_SKIPPED.extend(["/fake/Downloads"])
        summary = self.mod._build_upgrade_summary(
            from_version="1.9.7+a", to_version="1.9.8+b", zip_path=None,
            pruned_count=0, ran_index_rebuild=True, failed_phase=None, reconciliation=[],
        )
        self.assertEqual(summary["skipped_scan_locations"], ["/fake/Downloads"])

    def test_summary_skipped_empty_when_all_readable(self):
        # AC-3: no skips → empty field (no behavior change when everything reads).
        self.mod._PACK_SCAN_SKIPPED.clear()
        summary = self.mod._build_upgrade_summary(
            from_version="1.9.7+a", to_version="1.9.8+b", zip_path=None,
            pruned_count=0, ran_index_rebuild=True, failed_phase=None, reconciliation=[],
        )
        self.assertEqual(summary["skipped_scan_locations"], [])


class ReviewEvidenceSidecarCleanupTests(unittest.TestCase):
    """Wave 1tomw (AC-5/AC-11) + wave 1to78 (AC-2/AC-3): retired-sidecar cleanup.

    Tag-derived shapes: v1.12 and earlier waves are prose-only; v1.13
    introduced external ledgers while its publication lock lived at the
    repository root; v1.14+ use `.wavefoundry/locks/`. The cleanup deletes
    both retired sidecars without parsing either, byte-preserves every
    `wave.md`/`events.jsonl`, refuses while either shipped lock path is
    held, and holds both lock paths through the deletions (root-lock file
    released then unlinked last). `restart_required` is scoped to
    cutover-active runs: something was removed, or `from_version` predates
    1.15 (unknown fail-safe true).
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "docs" / "waves").mkdir(parents=True)
        (self.root / ".wavefoundry").mkdir()
        self.mod = load_upgrade_module()
        if str(SCRIPTS_ROOT) not in sys.path:
            sys.path.insert(0, str(SCRIPTS_ROOT))

    def tearDown(self):
        self.tmp.cleanup()

    def _seed_history(self) -> dict[Path, bytes]:
        # Fixture shapes are derived from the tagged release matrix recorded
        # at readiness (v1.12 prose-only; v1.13+ declared external ledger),
        # with the ledger and projection built through the CANONICAL
        # producers so the preserved history is real, validator-accepted
        # state rather than a hand-written approximation.
        import review_evidence as re_

        # v1.12 shape: prose-only wave, no ledger.
        prose = self.root / "docs" / "waves" / "1v12a prose-only" / "wave.md"
        prose.parent.mkdir(parents=True)
        prose.write_bytes(
            b"# Wave\n\nStatus: closed\n\n## Review Evidence\n\n"
            b"- operator-signoff: approved\n"
        )
        # v1.13+ shape: declared wave with a canonical external ledger.
        external_dir = self.root / "docs" / "waves" / "1v13a external"
        external_dir.mkdir()
        records = [
            {
                "record_type": "review_run",
                "review_run_id": "run-historical",
                "run_kind": "initial_delivery",
                "cycle": 0,
                "candidate_finding_ids": [],
                "source_record_ids": [],
                "dedup_evidence_id": None,
            }
        ]
        text = (
            "# Wave\nreview-evidence-source: events.jsonl\n\n"
            + re_.empty_external_finding_synthesis_section()
            + "\n## Review Evidence\n\n- operator-signoff: pending\n"
        )
        text = re_.render_review_evidence_projection(text, records)
        text = re_.render_review_status_projection(
            text, records, ["operator-signoff"]
        )
        (external_dir / "wave.md").write_bytes(text.encode("utf-8"))
        (external_dir / "events.jsonl").write_bytes(
            re_.canonical_review_events_bytes(records)
        )
        validation = re_.validate_external_review_evidence(external_dir / "wave.md")
        assert validation.ok, validation.errors
        # Both retired sidecars, deliberately unparseable: the cleanup must
        # not read them as authority or migration input.
        (self.root / "docs" / "waves" / "review-evidence-adoptions.json").write_bytes(
            b"{not json"
        )
        (self.root / "docs" / "waves" / "review-evidence-migration.json").write_bytes(
            b"{also not json"
        )
        return {
            path: path.read_bytes()
            for path in self.root.rglob("*")
            if path.is_file() and path.suffix in {".md", ".jsonl"}
        }

    def test_cleanup_removes_sidecars_without_parsing_and_preserves_history(self):
        preserved = self._seed_history()

        counts = self.mod.phase_review_evidence_sidecar_cleanup(self.root)

        self.assertEqual(counts["removed_sidecars"], 2)
        self.assertTrue(counts["restart_required"])
        waves = self.root / "docs" / "waves"
        self.assertFalse((waves / "review-evidence-adoptions.json").exists())
        self.assertFalse((waves / "review-evidence-migration.json").exists())
        for path, payload in preserved.items():
            self.assertEqual(path.read_bytes(), payload, path)

        # Wave 1to78 AC-3 — DELIBERATELY INVERTED from the 1tomw assertion.
        # 1tomw reported restart_required unconditionally forever; the scoped
        # restart boundary reports false on a converged rerun with a KNOWN
        # post-1.15 from_version (nothing removed, no cutover crossed). The
        # known version matters: an unknown from_version is fail-safe true and
        # would vacuously satisfy the old assertion.
        rerun = self.mod.phase_review_evidence_sidecar_cleanup(
            self.root, from_version="1.15.0"
        )
        self.assertEqual(rerun["removed_sidecars"], 0)
        self.assertFalse(rerun["restart_required"])

    def test_stale_v13_root_lock_is_cleaned_after_quiescence_proof(self):
        self._seed_history()
        legacy = self.root / ".wavefoundry" / "review-evidence-adoptions.lock"
        legacy.write_bytes(b"")

        counts = self.mod.phase_review_evidence_sidecar_cleanup(self.root)

        self.assertEqual(counts["removed_stale_root_lock"], 1)
        self.assertFalse(legacy.exists())

    def test_restart_required_is_scoped_to_cutover_active_runs(self):
        """Wave 1to78 AC-3: converged repo — restart tracks from_version only.

        Unknown or unparseable from_version is fail-safe true (treated
        pre-1.15); a known post-1.15 version on a converged tree is false.
        """
        cases = [
            (None, True),
            ("", True),
            ("garbage", True),
            ("2026-06-01a", True),
            ("1.14.3", True),
            ("1.15.0", False),
            ("1.15.7", False),
            ("2.0.0", False),
        ]
        for from_version, expected in cases:
            with self.subTest(from_version=from_version):
                counts = self.mod.phase_review_evidence_sidecar_cleanup(
                    self.root, from_version=from_version
                )
                self.assertEqual(counts["removed_sidecars"], 0)
                self.assertEqual(counts["removed_stale_root_lock"], 0)
                self.assertEqual(counts["restart_required"], expected)

    def test_restart_required_true_when_cutover_acted_despite_new_version(self):
        """Wave 1to78 AC-3: the run acting (removals) forces restart even on
        a known post-1.15 from_version."""
        self._seed_history()
        counts = self.mod.phase_review_evidence_sidecar_cleanup(
            self.root, from_version="1.15.0"
        )
        self.assertEqual(counts["removed_sidecars"], 2)
        self.assertTrue(counts["restart_required"])

        legacy = self.root / ".wavefoundry" / "review-evidence-adoptions.lock"
        legacy.write_bytes(b"")
        counts = self.mod.phase_review_evidence_sidecar_cleanup(
            self.root, from_version="1.15.0"
        )
        self.assertEqual(counts["removed_sidecars"], 0)
        self.assertEqual(counts["removed_stale_root_lock"], 1)
        self.assertTrue(counts["restart_required"])

    def test_pipeline_phase_threads_preflight_from_version(self):
        """Wave 1to78 AC-3 (call path 1): the Phase 2d pipeline call passes the
        preflight from_version. Source pin — the full pipeline (extract,
        render, prune) is impractical to execute in a unit test."""
        source = UPGRADE_PATH.read_text(encoding="utf-8")
        idx = source.index('current_phase = "review_sidecar_cleanup"')
        window = source[idx : idx + 300]
        self.assertIn("phase_review_evidence_sidecar_cleanup(", window)
        self.assertIn("from_version=from_version", window)

    def _run_cross_process_interleaving_control(
        self, *, preexisting_root_lock: bool
    ) -> None:
        self._seed_history()
        legacy = self.root / ".wavefoundry" / "review-evidence-adoptions.lock"
        if preexisting_root_lock:
            legacy.write_bytes(b"")

        with tempfile.TemporaryDirectory() as rendezvous:
            ctx = multiprocessing.get_context("spawn")
            outcomes = ctx.Queue()
            cleaner = ctx.Process(
                target=_sidecar_cleanup_worker,
                args=(str(self.root), rendezvous, "1.15.0", outcomes),
            )
            acquirer = ctx.Process(
                target=_blocking_acquirer_worker,
                args=(str(self.root), rendezvous, outcomes),
            )
            cleaner.start()
            acquirer.start()
            for process in (cleaner, acquirer):
                process.join(30)
                self.assertEqual(process.exitcode, 0)
            results = dict(outcomes.get(timeout=5) for _ in range(2))

        self.assertIn("cleanup", results, results)
        self.assertIn("acquirer", results, results)
        counts = results["cleanup"]
        self.assertEqual(counts["removed_sidecars"], 2)
        self.assertEqual(
            counts["removed_stale_root_lock"], 1 if preexisting_root_lock else 0
        )
        self.assertTrue(counts["restart_required"])
        # The blocking acquirer could not interleave with the deletions: at
        # the moment its acquire returned, every deletion — including the
        # root-lock unlink, which happens last after release — was complete.
        self.assertEqual(
            results["acquirer"],
            {"adoptions": False, "migration": False, "root_lock": False},
        )

    def test_concurrent_blocking_acquirer_cannot_interleave_with_deletions(self):
        """Wave 1to78 AC-2: real cross-process hold-through-deletion proof,
        pre-existing v1.13 root-lock fixture."""
        self._run_cross_process_interleaving_control(preexisting_root_lock=True)

    def test_concurrent_acquirer_cannot_interleave_when_root_lock_absent(self):
        """Wave 1to78 AC-2: absent root-lock fixture — acquiring mints the
        carrier, which is still held through deletion and unlinked last."""
        self._run_cross_process_interleaving_control(preexisting_root_lock=False)

    def test_held_current_lock_refuses_without_deleting_anything(self):
        self._seed_history()
        import review_evidence
        from runtime_lock import RuntimeFileLock

        current = self.root / review_evidence.PROJECT_STATE_PUBLICATION_LOCK_REL
        current.parent.mkdir(parents=True, exist_ok=True)
        holder = RuntimeFileLock(current, blocking=False)
        holder.acquire()
        try:
            with self.assertRaises(SystemExit) as raised:
                self.mod.phase_review_evidence_sidecar_cleanup(self.root)
        finally:
            holder.release()
        self.assertIn("held by a running process", str(raised.exception))
        waves = self.root / "docs" / "waves"
        self.assertTrue((waves / "review-evidence-adoptions.json").exists())
        self.assertTrue((waves / "review-evidence-migration.json").exists())

    def test_held_v13_root_lock_refuses_and_is_not_deleted(self):
        self._seed_history()
        from runtime_lock import RuntimeFileLock

        legacy = self.root / ".wavefoundry" / "review-evidence-adoptions.lock"
        legacy.write_bytes(b"")
        holder = RuntimeFileLock(legacy, blocking=False)
        holder.acquire()
        try:
            with self.assertRaises(SystemExit) as raised:
                self.mod.phase_review_evidence_sidecar_cleanup(self.root)
        finally:
            holder.release()
        self.assertIn("v1.13 root", str(raised.exception))
        self.assertTrue(legacy.exists())

    def test_symlinked_waves_parent_refuses_and_leaves_outside_sentinel(self):
        with tempfile.TemporaryDirectory() as outside_tmp:
            outside = Path(outside_tmp) / "outside-waves"
            outside.mkdir()
            sentinel = outside / "review-evidence-adoptions.json"
            sentinel.write_bytes(b"outside sentinel")
            waves = self.root / "docs" / "waves"
            shutil.rmtree(waves)
            try:
                waves.symlink_to(outside, target_is_directory=True)
            except OSError as exc:
                self.skipTest(f"directory symlinks unavailable: {exc}")

            with self.assertRaises(SystemExit) as raised:
                self.mod.phase_review_evidence_sidecar_cleanup(self.root)

            self.assertIn("symlink", str(raised.exception))
            self.assertEqual(sentinel.read_bytes(), b"outside sentinel")

    def test_symlinked_candidate_refuses_and_leaves_target_untouched(self):
        with tempfile.TemporaryDirectory() as outside_tmp:
            target = Path(outside_tmp) / "elsewhere.json"
            target.write_bytes(b"outside sentinel")
            candidate = (
                self.root / "docs" / "waves" / "review-evidence-adoptions.json"
            )
            try:
                candidate.symlink_to(target)
            except OSError as exc:
                self.skipTest(f"file symlinks unavailable: {exc}")

            with self.assertRaises(SystemExit) as raised:
                self.mod.phase_review_evidence_sidecar_cleanup(self.root)

            self.assertIn("symlink", str(raised.exception))
            self.assertEqual(target.read_bytes(), b"outside sentinel")
            self.assertTrue(candidate.is_symlink())
            # Wave 1to78 AC-2: a refusal must not leave behind the v1.13
            # root-lock carrier this run minted while taking its hold.
            self.assertFalse(
                (
                    self.root / ".wavefoundry" / "review-evidence-adoptions.lock"
                ).exists()
            )

    def test_inline_upgrade_bridge_is_fully_removed(self):
        # Wave 1tomw: the typed-inline authority never shipped in a tagged
        # release, so no bridge survives anywhere in the upgrade module.
        source = UPGRADE_PATH.read_text(encoding="utf-8")
        self.assertNotIn("externalize_adopted_inline_wave_locked", source)

    def test_post_cutover_public_mutation_succeeds_on_preserved_wave(self):
        # Wave 1tomw (AC-5, DF4 repair): after the cutover, the events-only
        # implementation (the code a restarted host runs) performs a public
        # create-mode typed-event append against the byte-preserved external
        # wave, and the grown ledger remains canonically valid.
        import review_evidence as re_
        import server_impl as srv

        self._seed_history()
        counts = self.mod.phase_review_evidence_sidecar_cleanup(self.root)
        self.assertEqual(counts["removed_sidecars"], 2)

        wave_md = self.root / "docs" / "waves" / "1v13a external" / "wave.md"
        before = re_.validate_external_review_evidence(wave_md)
        self.assertTrue(before.ok, before.errors)

        response = srv.wf_review_event_response(
            self.root,
            "1v13a external",
            "run",
            "wave-council",
            "post-cutover-mutation-context",
            mode="create",
            run_kind="initial_delivery",
            cycle=0,
        )
        self.assertEqual(response["status"], "ok", response)
        after = re_.validate_external_review_evidence(wave_md)
        self.assertTrue(after.ok, after.errors)
        self.assertEqual(len(after.records), len(before.records) + 1)


class MaterializeLifecyclePolicyTests(unittest.TestCase):
    """Wave 1p9q0 AC-7 — idempotent, atomic, key-preserving v2 provisioning."""

    @classmethod
    def setUpClass(cls):
        cls.mod = load_upgrade_module()

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name) / "proj"
        (self.root / "docs").mkdir(parents=True)
        self.cfg = self.root / "docs" / "workflow-config.json"

    def tearDown(self):
        self.temp_dir.cleanup()

    def _write_cfg(self, data):
        self.cfg.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def _policy(self):
        return json.loads(self.cfg.read_text(encoding="utf-8"))["lifecycle_id_policy"]

    def test_v1_repo_migrates_to_v2_with_scanned_offset(self):
        (self.root / "docs" / "waves" / "1p9pk example-wave").mkdir(parents=True)
        self._write_cfg({"lifecycle_id_policy": {"epoch_utc": "1999-05-01T00:00:00Z",
                                                 "hour_offset": 0}})
        msg = self.mod.materialize_lifecycle_policy(self.root)
        self.assertIn("provisioned scheme v2", msg)
        pol = self._policy()
        self.assertEqual(pol["scheme_version"], "v2")
        self.assertEqual(pol["offset"], int("1p9pk", 36) + 288 * 366)
        self.assertNotIn("project_seed", pol)  # migrated, not fresh
        # Rollout-date epoch, never the stale 1999/2020 values.
        self.assertNotIn(pol["epoch_utc"][:4], ("1999", "2020"))

    def test_fresh_repo_gets_scattered_band_and_project_seed(self):
        self._write_cfg({})
        self.mod.materialize_lifecycle_policy(self.root)
        pol = self._policy()
        self.assertEqual(pol["scheme_version"], "v2")
        self.assertGreaterEqual(pol["offset"], 36 ** 3)
        self.assertLess(pol["offset"], 619_520)
        self.assertIn("proj", pol["project_seed"])

    def test_second_run_is_a_noop(self):
        self._write_cfg({})
        self.mod.materialize_lifecycle_policy(self.root)
        before = self.cfg.read_text(encoding="utf-8")
        msg = self.mod.materialize_lifecycle_policy(self.root)
        self.assertIn("left unchanged", msg)
        self.assertEqual(self.cfg.read_text(encoding="utf-8"), before)

    def test_idempotence_keyed_on_scheme_version_not_epoch(self):
        """A partial prior write (epoch present, scheme_version absent) is
        re-attempted — all-or-nothing."""
        self._write_cfg({"lifecycle_id_policy": {"epoch_utc": "2026-06-01T00:00:00Z"}})
        msg = self.mod.materialize_lifecycle_policy(self.root)
        self.assertIn("provisioned scheme v2", msg)
        self.assertEqual(self._policy()["scheme_version"], "v2")

    def test_unrelated_top_level_keys_preserved_value_and_order_equal(self):
        # Value- and key-order-preserving via whole-document re-serialization
        # (indent 2). NOT byte-equal for arbitrary input formatting — the AC-7
        # contract wording was reconciled to this by the delivery code lane.
        extra = {"wave_implement": {"waves_required_for_non_trivial_work": True},
                 "custom_operator_key": {"nested": [1, 2, 3]},
                 "lifecycle_id_policy": {"epoch_utc": "1999-05-01T00:00:00Z",
                                         "custom_inner": "kept"}}
        self._write_cfg(extra)
        self.mod.materialize_lifecycle_policy(self.root)
        data = json.loads(self.cfg.read_text(encoding="utf-8"))
        self.assertEqual(data["wave_implement"], extra["wave_implement"])
        self.assertEqual(data["custom_operator_key"], extra["custom_operator_key"])
        # Unknown keys INSIDE the policy block are preserved too.
        self.assertEqual(data["lifecycle_id_policy"]["custom_inner"], "kept")
        # Top-level key ORDER is preserved (json round-trip is insertion-ordered).
        self.assertEqual(list(data.keys()), list(extra.keys()))

    def test_crash_mid_write_leaves_original_valid_and_reattempts(self):
        """AC-7 crash-window clause at the mechanism level: a failure inside the
        atomic write must leave the original config byte-identical + parseable,
        strand no temp file, raise loudly, and succeed on the next run."""
        self._write_cfg({"lifecycle_id_policy": {"epoch_utc": "1999-05-01T00:00:00Z"}})
        before = self.cfg.read_text(encoding="utf-8")
        with patch.object(self.mod.os, "replace", side_effect=OSError("simulated crash")):
            with self.assertRaises(RuntimeError):
                self.mod.materialize_lifecycle_policy(self.root)
        self.assertEqual(self.cfg.read_text(encoding="utf-8"), before)
        json.loads(before)  # still valid JSON
        leftovers = [p.name for p in (self.root / "docs").iterdir()
                     if p.name != "workflow-config.json"]
        self.assertEqual(leftovers, [])
        # Re-attempt (no crash) provisions normally — idempotence key still absent.
        self.mod.materialize_lifecycle_policy(self.root)
        self.assertEqual(self._policy()["scheme_version"], "v2")

    def test_low_horizon_warning_names_the_scanned_max(self):
        """A scanned max that leaves under ~5 years of 5-char space triggers the
        loud backstop naming the max prefix token (word-like false matches on
        6-char tokens are already excluded by the 5-char-only scan)."""
        # decode("w0000") = 53,747,712 → offset 54,063,936 > 36^5 − 1826×4096.
        (self.root / "docs" / "waves" / "w0000 anomalous").mkdir(parents=True)
        self._write_cfg({})
        msg = self.mod.materialize_lifecycle_policy(self.root)
        self.assertIn("WARNING", msg)
        self.assertIn("w0000", msg)

    def test_below_threshold_scanned_max_stays_silent(self):
        """Just under the 5-year threshold from the other side: a large-but-legal
        scanned max that still leaves 5+ years emits no warning."""
        # decode("j0000") = 31,912,704 → offset 32,228,928 ≪ threshold 52,986,880.
        (self.root / "docs" / "waves" / "j0000 large-legit").mkdir(parents=True)
        self._write_cfg({})
        msg = self.mod.materialize_lifecycle_policy(self.root)
        self.assertNotIn("WARNING", msg)

    def test_normal_migration_emits_no_horizon_warning(self):
        (self.root / "docs" / "waves" / "1p9pk example-wave").mkdir(parents=True)
        self._write_cfg({})
        msg = self.mod.materialize_lifecycle_policy(self.root)
        self.assertNotIn("WARNING", msg)

    def test_word_like_six_char_filename_does_not_poison_migration(self):
        """Delivery red-team F2: `review-notes.md` decodes above 36^5 as a
        6-char token; the migration scan must ignore it (v1 history is 5-char
        by construction) and take the fresh path here."""
        (self.root / "docs" / "plans").mkdir(parents=True)
        (self.root / "docs" / "plans" / "review-notes.md").write_text("x", encoding="utf-8")
        self._write_cfg({})
        self.mod.materialize_lifecycle_policy(self.root)
        pol = self._policy()
        self.assertLess(pol["offset"], 619_520)  # fresh band, not 1.6B
        self.assertIn("project_seed", pol)

    def test_stale_v1_descriptor_keys_removed(self):
        self._write_cfg({"lifecycle_id_policy": {"epoch_utc": "1999-05-01T00:00:00Z",
                                                 "time_unit": "5-minute-bucket",
                                                 "buckets_per_day": 288}})
        self.mod.materialize_lifecycle_policy(self.root)
        pol = self._policy()
        self.assertNotIn("time_unit", pol)
        self.assertNotIn("buckets_per_day", pol)

    def test_unparseable_config_fails_loudly_with_no_write(self):
        self.cfg.write_text("{corrupt json", encoding="utf-8")
        with self.assertRaises(RuntimeError):
            self.mod.materialize_lifecycle_policy(self.root)
        self.assertEqual(self.cfg.read_text(encoding="utf-8"), "{corrupt json")

    def test_missing_config_file_is_created(self):
        self.assertFalse(self.cfg.exists())
        self.mod.materialize_lifecycle_policy(self.root)
        self.assertEqual(self._policy()["scheme_version"], "v2")

    def test_no_temp_file_left_behind(self):
        self._write_cfg({})
        self.mod.materialize_lifecycle_policy(self.root)
        leftovers = [p.name for p in (self.root / "docs").iterdir()
                     if p.name != "workflow-config.json"]
        self.assertEqual(leftovers, [])

    def test_written_config_is_valid_json_and_loader_accepts_it(self):
        """End-to-end: the written policy round-trips through the strict loader
        and the first mint decodes above the scanned pre-migration max."""
        (self.root / "docs" / "waves" / "1p9pk example-wave").mkdir(parents=True)
        self._write_cfg({"lifecycle_id_policy": {"epoch_utc": "1999-05-01T00:00:00Z"}})
        self.mod.materialize_lifecycle_policy(self.root)
        spec = importlib.util.spec_from_file_location(
            "lifecycle_id_mig_test", SCRIPTS_ROOT / "lifecycle_id.py")
        lid = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(lid)
        policy = lid.load_lifecycle_policy(self.root)
        prefix = lid.build_prefix(policy=policy, kind="bug", slug="post-migration")
        self.assertGreater(lid.decode_base36(prefix), int("1p9pk", 36))

    def test_cli_flag_runs_only_provisioning_and_exits_zero(self):
        self._write_cfg({})
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            rc = self.mod.main(["--materialize-lifecycle-policy", "--root", str(self.root)])
        self.assertEqual(rc, 0)
        self.assertIn("provisioned scheme v2", stdout.getvalue())
        self.assertEqual(self._policy()["scheme_version"], "v2")

    def test_cli_flag_propagates_corrupt_config_as_error(self):
        self.cfg.write_text("{corrupt", encoding="utf-8")
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            rc = self.mod.main(["--materialize-lifecycle-policy", "--root", str(self.root)])
        self.assertEqual(rc, 1)
        self.assertIn("refusing to overwrite", stderr.getvalue())

    def test_cleanup_backstop_heals_unprovisioned_repo(self):
        """End-of-upgrade reconciliation check (operator directive): an
        un-provisioned repo at cleanup time is healed via the idempotent
        materialization."""
        self._write_cfg({})
        logged: list[str] = []
        with patch.object(self.mod, "_log", side_effect=logged.append):
            self.mod._ensure_lifecycle_policy_backstop(self.root)
        self.assertEqual(self._policy()["scheme_version"], "v2")
        self.assertTrue(any("backstop healed" in line for line in logged), logged)

    def test_cleanup_backstop_noop_when_already_v2(self):
        self._write_cfg({})
        self.mod.materialize_lifecycle_policy(self.root)
        before = self.cfg.read_text(encoding="utf-8")
        logged: list[str] = []
        with patch.object(self.mod, "_log", side_effect=logged.append):
            self.mod._ensure_lifecycle_policy_backstop(self.root)
        self.assertEqual(self.cfg.read_text(encoding="utf-8"), before)
        self.assertTrue(any("scheme v2 present" in line for line in logged), logged)

    def test_cleanup_backstop_never_raises_on_corrupt_config(self):
        """Fail-safe: a backstop error degrades to a loud recovery pointer —
        it must never fail cleanup."""
        self.cfg.write_text("{corrupt", encoding="utf-8")
        logged: list[str] = []
        with patch.object(self.mod, "_log", side_effect=logged.append):
            self.mod._ensure_lifecycle_policy_backstop(self.root)  # no raise
        self.assertEqual(self.cfg.read_text(encoding="utf-8"), "{corrupt")
        self.assertTrue(any("--materialize-lifecycle-policy" in line for line in logged), logged)

    def test_update_index_phase_wires_the_lifecycle_backstop(self):
        # Wave 1ryce: the --update-index phase must invoke _ensure_lifecycle_policy_backstop (from the
        # freshly extracted NEW code) so a from-<1.10.1 MCP upgrade — whose preflight ran old code with no
        # Phase 2c and whose old server never reached the cleanup backstop — self-provisions scheme v2.
        # The full --update-index path spawns a real index build (no unit harness), so lock the wiring by
        # source: the backstop call must appear AFTER phase_index_update in the --update-index handler.
        import inspect
        src = inspect.getsource(self.mod)
        # `phase_index_update(root)` (closing paren) matches call sites, not the `(root: Path)` def; the
        # first call is the --update-index handler.
        piu = src.index("phase_index_update(root)")
        backstop_after = src.index("_ensure_lifecycle_policy_backstop(root)", piu)
        self.assertGreater(
            backstop_after, piu,
            "the --update-index phase must call _ensure_lifecycle_policy_backstop after phase_index_update",
        )


class HistoricalMemoryUpgradeGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_upgrade_module()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / ".wavefoundry" / "index").mkdir(parents=True)
        (self.root / "docs" / "waves").mkdir(parents=True)
        sys.path.insert(0, str(SCRIPTS_ROOT))
        import memory_backfill
        import upgrade_lib

        self.backfill = memory_backfill
        self.upgrade_lib = upgrade_lib
        self.run_id = memory_backfill.ensure_run(self.root, "upgrade")
        memory_backfill.sync_inventory(self.root, self.run_id)
        upgrade_lib.write_upgrade_lock(self.root, "1.0.0", "1.1.0")
        upgrade_lib.update_upgrade_lock(
            self.root,
            memory_backfill_run_id=self.run_id,
            memory_backfill_state="ready_for_index",
        )

    def tearDown(self):
        self.tmp.cleanup()

    def _ready_candidate_run(self):
        import index_state_store
        import memory_records
        import server_impl

        self.root.joinpath("foo.py").write_text("LOCAL = True\n", encoding="utf-8")
        wave = self.root / "docs" / "waves" / "1abc closed"
        wave.mkdir()
        change_id = "1abd-enh durable-choice"
        wave.joinpath("wave.md").write_text(
            f"# Wave\n\nStatus: closed\n\nChange ID: `{change_id}`\n",
            encoding="utf-8",
        )
        wave.joinpath(f"{change_id}.md").write_text(
            "# Change\n\n## Decision Log\n\n"
            "| Date | Decision | Reason | Alternatives |\n"
            "| --- | --- | --- | --- |\n"
            "| 2026-01-01 | Keep `foo.py` local | Avoid remote authority | none |\n",
            encoding="utf-8",
        )
        server_impl.memory_backfill_response(
            self.root, mode="create", entry_path="upgrade"
        )
        candidate = memory_records.load_memory_records(self.root)[0]
        server_impl.memory_validate_response(
            self.root,
            candidate["memory_id"],
            "promote",
            "Reuse the local decision.",
            "The target remains current.",
            True,
            True,
            "none",
        )
        return wave, index_state_store

    def test_resume_publishes_before_marking_indexed_and_is_idempotent(self):
        observed: list[str] = []
        original_mark = self.backfill.mark_indexed

        def phase(_root):
            observed.append(self.backfill.run_summary(self.root, self.run_id)["state"])
            return True  # 1u44n: the stubbed phase reports an observed successful publication

        def mark(root, run_id):
            observed.append("mark")
            return original_mark(root, run_id)

        with patch.object(self.mod, "phase_index_update", side_effect=phase), \
             patch.object(self.backfill, "mark_indexed", side_effect=mark):
            first = self.mod.main(
                ["--root", str(self.root), "--resume-after-memory"]
            )
        self.assertEqual(first, 0)
        self.assertEqual(observed, ["ready_for_index", "mark"])
        self.assertEqual(
            self.backfill.run_summary(self.root, self.run_id)["state"], "indexed"
        )

        with patch.object(self.mod, "phase_index_update") as phase_again:
            second = self.mod.main(
                ["--root", str(self.root), "--resume-after-memory"]
            )
        self.assertEqual(second, 0)
        phase_again.assert_not_called()

    def test_resume_accepts_publication_checkpoint_and_clears_compatibility_lease(self):
        self.upgrade_lib.update_upgrade_lock(
            self.root,
            current_phase="awaiting_memory_publication",
            action_required={
                "kind": "historical_memory",
                "state": "awaiting_memory_publication",
                "resume_phase": "resume_after_memory",
                "run_id": self.run_id,
                "token": "test-token",
            },
            failed_phase="awaiting_memory_validation",
            failed_at=None,
        )
        with patch.object(self.mod, "phase_index_update", return_value=True) as phase:
            result = self.mod.main(["--root", str(self.root), "--resume-after-memory"])

        self.assertEqual(result, 0)
        phase.assert_called_once_with(self.root.resolve())
        checkpoint = self.upgrade_lib.read_upgrade_lock(self.root)
        self.assertEqual(checkpoint.get("current_phase"), "index_complete")
        self.assertIsNone(checkpoint.get("action_required"))
        self.assertIsNone(checkpoint.get("failed_phase"))
        self.assertIsNone(checkpoint.get("failed_at"))

    def test_docs_gate_resume_establishes_memory_checkpoint_and_composes(self):
        """External pfq6 reproduction: the successful docs recovery used to
        retain ``review_sidecar_cleanup_complete``, making the immediately
        documented memory recovery unreachable.
        """

        self.upgrade_lib.update_upgrade_lock(
            self.root,
            current_phase="review_sidecar_cleanup_complete",
            failed_phase="docs_gate",
            failed_at="t",
        )
        with patch.object(self.mod, "phase_docs_gate"):
            resumed_gate = self.mod.main(
                ["--root", str(self.root), "--resume-after-gate"]
            )
        self.assertEqual(resumed_gate, 0)
        checkpoint = self.upgrade_lib.read_upgrade_lock(self.root)
        self.assertIsNone(checkpoint.get("failed_phase"))
        self.assertEqual(
            checkpoint.get("current_phase"), "awaiting_memory_validation"
        )
        self.assertEqual(checkpoint.get("memory_backfill_run_id"), self.run_id)

        with patch.object(self.mod, "phase_index_update") as phase:
            resumed_memory = self.mod.main(
                ["--root", str(self.root), "--resume-after-memory"]
            )
        self.assertEqual(resumed_memory, 0)
        phase.assert_called_once_with(self.root.resolve())

    def _insert_memory_source(self, memory_id: str) -> None:
        conn = self.backfill._connect(self.root)
        try:
            with conn:
                conn.execute(
                    "INSERT INTO memory_backfill_sources"
                    "(run_id,wave_id,source_event,memory_id) VALUES(?,?,?,?)",
                    (
                        self.run_id,
                        "1aaa closed",
                        "decision-log:historical",
                        memory_id,
                    ),
                )
        finally:
            conn.close()

    def test_resume_after_memory_repairs_same_version_stale_memory_id(self):
        """The public recovery command must not depend on the <1.15 migration gate."""

        import memory_records

        legacy_id = "mem-" + ("a" * 59) + "-"
        slug = memory_records.slugify(legacy_id[4:])
        lifecycle_id = f"1abc1-mem {slug}"
        content = memory_records.render_memory_record(
            memory_id=lifecycle_id,
            kind="decision",
            summary="A rewritten historical candidate already resolved.",
            evidence=["`1aaaa-bug historical-source` — observed"],
            targets=["foo.py"],
            status="superseded",
            source_event="decision-log:historical",
            validation="rewrite",
            date="2026-01-10",
        )
        content = content.replace(
            "Status: superseded\n",
            "Status: superseded\nSuperseded by: `1abc9-mem successor`\n",
        )
        memory_records.write_memory_record(self.root, content, lifecycle_id)
        self._insert_memory_source(legacy_id)
        self.upgrade_lib.update_upgrade_lock(
            self.root,
            current_phase="awaiting_memory_validation",
            memory_backfill_state="awaiting_validation",
        )

        with patch.object(self.mod, "phase_index_update") as phase:
            result = self.mod.main(
                ["--root", str(self.root), "--resume-after-memory"]
            )

        self.assertEqual(result, 0)
        phase.assert_called_once_with(self.root.resolve())
        conn = self.backfill._connect(self.root)
        try:
            row = conn.execute(
                "SELECT memory_id FROM memory_backfill_sources WHERE run_id=?",
                (self.run_id,),
            ).fetchone()
        finally:
            conn.close()
        self.assertEqual(str(row["memory_id"]), lifecycle_id)

    def test_pending_resume_restores_memory_recovery_publication_phase(self):
        """Action-required may not strand the tools needed to clear the action."""

        import publication_control

        self._insert_memory_source("mem-genuinely-missing")
        self.upgrade_lib.update_upgrade_lock(
            self.root,
            current_phase="awaiting_memory_validation",
            memory_backfill_state="awaiting_validation",
        )
        stderr = io.StringIO()
        with patch.object(self.mod, "phase_index_update") as phase, \
             contextlib.redirect_stderr(stderr):
            result = self.mod.main(
                ["--root", str(self.root), "--resume-after-memory"]
            )

        self.assertEqual(result, self.backfill.ACTION_REQUIRED_EXIT)
        phase.assert_not_called()
        checkpoint = self.upgrade_lib.read_upgrade_lock(self.root)
        self.assertEqual(
            checkpoint.get("current_phase"), "awaiting_memory_validation"
        )
        self.assertIsNone(
            publication_control.publication_block_reason(
                self.root, "memory_backfill"
            )
        )
        self.assertIsNone(
            publication_control.publication_block_reason(
                self.root, "memory_validate"
            )
        )
        self.assertIn("awaiting validation", stderr.getvalue())

    def test_ambiguous_memory_id_resume_fails_loud_and_restores_phase(self):
        import memory_records
        import publication_control

        legacy_id = "mem-ambiguous-record"
        slug = memory_records.slugify(legacy_id[4:])
        for prefix in ("1abc1", "1abc2"):
            memory_id = f"{prefix}-mem {slug}"
            content = memory_records.render_memory_record(
                memory_id=memory_id,
                kind="decision",
                summary="An ambiguous migrated historical record.",
                evidence=["`1aaaa-bug historical-source` — observed"],
                targets=["foo.py"],
                source_event="decision-log:historical",
                validation="rewrite",
                date="2026-01-10",
            )
            memory_records.write_memory_record(self.root, content, memory_id)
        self._insert_memory_source(legacy_id)
        self.upgrade_lib.update_upgrade_lock(
            self.root,
            current_phase="awaiting_memory_validation",
            memory_backfill_state="awaiting_validation",
        )
        stderr = io.StringIO()

        with patch.object(self.mod, "phase_index_update") as phase, \
             contextlib.redirect_stderr(stderr):
            result = self.mod.main(
                ["--root", str(self.root), "--resume-after-memory"]
            )

        self.assertEqual(result, self.backfill.ACTION_REQUIRED_EXIT)
        phase.assert_not_called()
        self.assertIn("ambiguous migrated memory id", stderr.getvalue())
        checkpoint = self.upgrade_lib.read_upgrade_lock(self.root)
        self.assertEqual(
            checkpoint.get("current_phase"), "awaiting_memory_validation"
        )
        self.assertIsNone(
            publication_control.publication_block_reason(
                self.root, "memory_backfill"
            )
        )
        conn = self.backfill._connect(self.root)
        try:
            row = conn.execute(
                "SELECT memory_id FROM memory_backfill_sources WHERE run_id=?",
                (self.run_id,),
            ).fetchone()
        finally:
            conn.close()
        self.assertEqual(str(row["memory_id"]), legacy_id)

    def test_resume_after_memory_restages_receipt_to_trailing_graph_attempt(self):
        """External pfqq reproduction: the content child writes a staging
        receipt, then graph maintenance starts a later attempt at the same
        generation.  The graph child must become the exact authorized receipt
        attempt before the parent CAS; generation-only aliasing is not enough.
        """

        _wave, index_state_store = self._ready_candidate_run()
        attempts: list[tuple[str, str]] = []

        def child_run(argv, *, cwd, check, env=None, **_kwargs):
            scope = "graph" if "--graph-only" in argv else "all"
            with patch.dict(os.environ, env or {}, clear=True):
                attempt = index_state_store.begin_build_epoch(
                    self.root / ".wavefoundry" / "index", scope
                )
                attempts.append((scope, attempt))
                self.assertTrue(
                    index_state_store.finalize_build_epoch(
                        self.root / ".wavefoundry" / "index", attempt
                    )
                )
            return subprocess.CompletedProcess(argv, 0)

        with patch.object(
            self.mod.subprocess_util, "isolated_run", side_effect=child_run
        ):
            result = self.mod.main(
                ["--root", str(self.root), "--resume-after-memory"]
            )

        self.assertEqual(result, 0)
        self.assertEqual([scope for scope, _attempt in attempts], ["all", "graph"])
        state = index_state_store.read_build_state(
            self.root / ".wavefoundry" / "index"
        )
        self.assertEqual(state["status"], "complete")
        self.assertEqual(state["generation"], 1)
        self.assertEqual(state["attempt_id"], attempts[-1][1])
        self.assertEqual(
            self.backfill.run_summary(self.root, self.run_id)["state"], "indexed"
        )
        self.assertFalse(
            (
                self.root
                / ".wavefoundry"
                / "index"
                / "upgrade-index-staging-receipt.json"
            ).exists()
        )

    def test_resume_recovers_published_epoch_without_second_index_pass(self):
        _wave, index_state_store = self._ready_candidate_run()
        phase_calls = 0

        def phase(_root):
            nonlocal phase_calls
            phase_calls += 1
            index_dir = self.root / ".wavefoundry" / "index"
            attempt = index_state_store.begin_build_epoch(index_dir, "all")
            self.assertTrue(
                index_state_store.finalize_build_epoch(index_dir, attempt)
            )

        with patch.object(self.mod, "phase_index_update", side_effect=phase), \
             patch.object(
                 self.backfill,
                 "complete_index_publication",
                 side_effect=RuntimeError("checkpoint unavailable"),
             ):
            first = self.mod.main(
                ["--root", str(self.root), "--resume-after-memory"]
            )
        self.assertEqual(first, 1)
        self.assertEqual(phase_calls, 1)
        with patch.object(self.mod, "phase_index_update", side_effect=phase):
            second = self.mod.main(
                ["--root", str(self.root), "--resume-after-memory"]
            )
        self.assertEqual(second, 0)
        self.assertEqual(phase_calls, 1)
        self.assertEqual(
            self.backfill.run_summary(self.root, self.run_id)["state"],
            "indexed",
        )

    def test_resume_requeues_history_changed_at_index_finalize(self):
        wave, index_state_store = self._ready_candidate_run()

        def phase(_root):
            index_dir = self.root / ".wavefoundry" / "index"
            attempt = index_state_store.begin_build_epoch(index_dir, "all")
            wave.joinpath("wave.md").write_text(
                wave.joinpath("wave.md").read_text(encoding="utf-8")
                + "\nchanged during publication\n",
                encoding="utf-8",
            )
            self.assertFalse(
                index_state_store.finalize_build_epoch(index_dir, attempt)
            )

        with patch.object(self.mod, "phase_index_update", side_effect=phase):
            result = self.mod.main(
                ["--root", str(self.root), "--resume-after-memory"]
            )
        self.assertEqual(result, self.backfill.ACTION_REQUIRED_EXIT)
        self.assertEqual(
            self.backfill.run_summary(self.root, self.run_id)["state"],
            "awaiting_validation",
        )

    def test_update_index_cannot_bypass_ready_memory_gate(self):
        with patch.object(self.mod, "phase_index_update") as phase, \
             contextlib.redirect_stderr(io.StringIO()):
            result = self.mod.main(["--root", str(self.root), "--update-index"])
        self.assertEqual(result, self.backfill.ACTION_REQUIRED_EXIT)
        phase.assert_not_called()

    def test_standalone_gate_zero_pending_refusal_states_ordered_recovery(self):
        """1u44n (AC-2, third refusal surface): the zero-pending field
        scenario no longer emits the false "validation is pending" statement;
        it states the ordered resume/cleanup/index_build recovery and names
        index_health. The refusal itself is unchanged."""
        stderr = io.StringIO()
        with patch.object(self.mod, "phase_index_update") as phase, \
             contextlib.redirect_stderr(stderr):
            result = self.mod.main(["--root", str(self.root), "--update-index"])
        self.assertEqual(result, self.backfill.ACTION_REQUIRED_EXIT)
        phase.assert_not_called()
        text = stderr.getvalue()
        self.assertNotIn("validation is pending", text)
        self.assertIn("0 pending", text)
        resume = text.index("--resume-after-memory")
        cleanup = text.index("then --cleanup")
        build = text.index("then index_build")
        self.assertLess(resume, cleanup)
        self.assertLess(cleanup, build)
        self.assertIn("index_health", text)

    def test_standalone_gate_pending_refusal_keeps_validation_routing(self):
        """1u44n: with genuinely pending memory work the gate keeps routing to
        backfill + validation (the ordered recovery would skip validation)."""
        pending_summary = {
            "state": "awaiting_validation",
            "remaining_waves": 2,
            "candidates_pending": 1,
            "failures": 0,
            "last_failure": None,
        }
        stderr = io.StringIO()
        with patch.object(
            self.backfill, "sync_inventory", return_value=pending_summary
        ), patch.object(self.mod, "phase_index_update") as phase, \
             contextlib.redirect_stderr(stderr):
            result = self.mod.main(["--root", str(self.root), "--update-index"])
        self.assertEqual(result, self.backfill.ACTION_REQUIRED_EXIT)
        phase.assert_not_called()
        text = stderr.getvalue()
        self.assertIn("validation is pending", text)
        self.assertNotIn("index_health", text)

    def test_resume_after_memory_cannot_bypass_failed_review_or_docs_gate(self):
        """The memory resume must not publish while the earlier typed gate is failed."""

        self.upgrade_lib.update_upgrade_lock(
            self.root, failed_phase="docs_gate", failed_at="t"
        )
        stderr = io.StringIO()
        with patch.object(self.mod, "phase_index_update") as phase, \
             contextlib.redirect_stderr(stderr):
            result = self.mod.main(
                ["--root", str(self.root), "--resume-after-memory"]
            )
        self.assertEqual(result, 1)
        phase.assert_not_called()
        self.assertIn("--resume-after-gate", stderr.getvalue())
        self.assertEqual(
            self.backfill.run_summary(self.root, self.run_id)["state"],
            "ready_for_index",
        )

    def test_resume_success_clears_only_its_own_failure_marker(self):
        """1t49m field report: a failed resume left a marker that no later
        success cleared, so cleanup refused until a full re-run."""

        with patch.object(
            self.mod, "phase_index_update", side_effect=RuntimeError("disk full")
        ), contextlib.redirect_stderr(io.StringIO()):
            first = self.mod.main(
                ["--root", str(self.root), "--resume-after-memory"]
            )
        self.assertEqual(first, 1)
        lock = self.upgrade_lib.read_upgrade_lock(self.root)
        self.assertEqual(lock["failed_phase"], "index_update")

        with patch.object(self.mod, "phase_index_update"):
            second = self.mod.main(
                ["--root", str(self.root), "--resume-after-memory"]
            )
        self.assertEqual(second, 0)
        lock = self.upgrade_lib.read_upgrade_lock(self.root)
        self.assertIsNone(lock["failed_phase"])
        self.assertIsNone(lock["failed_at"])

    def test_resume_success_preserves_marker_naming_a_different_phase(self):
        """A later success must not launder an earlier unrecovered failure."""

        self.upgrade_lib.update_upgrade_lock(
            self.root, failed_phase="dashboard_restart", failed_at="t"
        )
        with patch.object(self.mod, "phase_index_update"):
            result = self.mod.main(
                ["--root", str(self.root), "--resume-after-memory"]
            )
        self.assertEqual(result, 0)
        lock = self.upgrade_lib.read_upgrade_lock(self.root)
        self.assertEqual(lock["failed_phase"], "dashboard_restart")
        self.assertEqual(lock["failed_at"], "t")

    def test_resume_already_complete_clears_retained_index_marker(self):
        """The idempotent re-run recovers a stale marker for the phase that
        reconciliation just proved complete, without a second index pass."""

        with patch.object(self.mod, "phase_index_update"):
            self.assertEqual(
                self.mod.main(["--root", str(self.root), "--resume-after-memory"]),
                0,
            )
        self.upgrade_lib.update_upgrade_lock(
            self.root, failed_phase="index_update", failed_at="t"
        )
        with patch.object(self.mod, "phase_index_update") as phase_again:
            self.assertEqual(
                self.mod.main(["--root", str(self.root), "--resume-after-memory"]),
                0,
            )
        phase_again.assert_not_called()
        lock = self.upgrade_lib.read_upgrade_lock(self.root)
        self.assertIsNone(lock["failed_phase"])
        self.assertIsNone(lock["failed_at"])

    def test_publication_verbs_cannot_bypass_failed_review_or_docs_gate(self):
        """Both incremental and full publication stop before the new-code backstop."""

        for option, phase_name in (
            ("--update-index", "phase_index_update"),
            ("--rebuild-index", "phase_index_rebuild"),
        ):
            with self.subTest(option=option):
                self.upgrade_lib.update_upgrade_lock(
                    self.root,
                    failed_phase="review_sidecar_cleanup",
                    failed_at="t",
                )
                stderr = io.StringIO()
                with patch.object(self.mod, phase_name) as phase, \
                     contextlib.redirect_stderr(stderr):
                    result = self.mod.main(["--root", str(self.root), option])
                self.assertEqual(result, 1)
                phase.assert_not_called()
                self.assertIn("re-run", stderr.getvalue())

    def test_backstop_scopes_restart_from_lock_carried_from_version(self):
        """Wave 1to78 AC-3 (call path 3): the deferred backstop cannot
        recompute from_version from disk post-extract; the upgrade lock state
        written at preflight is its carrier. A converged tree with a known
        post-1.15 lock from_version records restart_required false; a lock
        without a usable from_version is fail-safe true."""

        for lock_from, expected in (("1.15.0", False), (None, True)):
            with self.subTest(lock_from=lock_from):
                self.upgrade_lib.remove_upgrade_lock(self.root)
                self.upgrade_lib.write_upgrade_lock(
                    self.root, lock_from, "1.15.1"
                )
                self.upgrade_lib.update_upgrade_lock(
                    self.root,
                    memory_backfill_run_id=self.run_id,
                    memory_backfill_state="ready_for_index",
                )
                with patch.object(self.mod, "phase_index_update"):
                    self.mod.main(["--root", str(self.root), "--update-index"])
                lock = self.upgrade_lib.read_upgrade_lock(self.root) or {}
                self.assertIn("review_sidecar_cleanup", lock)
                self.assertEqual(
                    lock["review_sidecar_cleanup"]["restart_required"], expected
                )
                self.assertEqual(
                    lock["review_sidecar_cleanup"]["removed_sidecars"], 0
                )

    def test_new_code_sidecar_refusal_is_not_misreported_as_memory_action(self):
        """A cleanup backstop refusal is rc1 recovery, never rc4 memory work."""

        legacy_root = Path(self.tmp.name) / "sidecar-refusal-target"
        (legacy_root / ".wavefoundry").mkdir(parents=True)
        self.upgrade_lib.write_upgrade_lock(legacy_root, "1.0.0", "1.1.0")
        stderr = io.StringIO()
        with patch.object(
            self.mod,
            "phase_review_evidence_sidecar_cleanup",
            side_effect=SystemExit("publication lock is held by a running process"),
        ), patch.object(self.mod, "phase_index_update") as phase, \
             contextlib.redirect_stderr(stderr):
            result = self.mod.main(
                ["--root", str(legacy_root), "--update-index"]
            )
        self.assertEqual(result, 1)
        phase.assert_not_called()
        self.assertIn("refused", stderr.getvalue())
        lock = self.upgrade_lib.read_upgrade_lock(legacy_root) or {}
        self.assertEqual(
            lock.get("failed_phase"), "review_sidecar_cleanup"
        )

    def test_cleanup_cannot_remove_lock_after_memory_indexed_but_docs_failed(self):
        """An indexed memory run does not authorize cleanup around a failed docs gate."""

        self.backfill.mark_indexed(self.root, self.run_id)
        self.upgrade_lib.update_upgrade_lock(
            self.root,
            memory_backfill_state="indexed",
            failed_phase="docs_gate",
            failed_at="t",
        )
        stderr = io.StringIO()
        with patch.object(self.mod, "phase_cleanup") as cleanup, \
             contextlib.redirect_stderr(stderr):
            result = self.mod.main(["--root", str(self.root), "--cleanup"])
        self.assertEqual(result, 1)
        cleanup.assert_not_called()
        self.assertIn("--resume-after-gate", stderr.getvalue())
        lock = self.upgrade_lib.read_upgrade_lock(self.root)
        self.assertEqual(lock.get("failed_phase"), "docs_gate")

    def test_old_shaped_lock_bootstraps_new_migrations_before_update_index(self):
        legacy_root = Path(self.tmp.name) / "legacy-target"
        (legacy_root / ".wavefoundry").mkdir(parents=True)
        wave = legacy_root / "docs" / "waves" / "1old closed"
        wave.mkdir(parents=True)
        wave.joinpath("wave.md").write_text(
            "# Wave\n\nStatus: closed\n", encoding="utf-8"
        )
        self.upgrade_lib.write_upgrade_lock(legacy_root, "1.0.0", "1.1.0")
        before = self.upgrade_lib.read_upgrade_lock(legacy_root)
        self.assertNotIn("memory_backfill_run_id", before or {})
        self.assertFalse(
            (legacy_root / ".wavefoundry" / "index" / "memory-state.sqlite").exists()
        )

        with patch.object(self.mod, "phase_index_update") as phase:
            result = self.mod.main(
                ["--root", str(legacy_root), "--update-index"]
            )

        self.assertEqual(result, self.backfill.ACTION_REQUIRED_EXIT)
        phase.assert_not_called()
        lock = self.upgrade_lib.read_upgrade_lock(legacy_root) or {}
        self.assertTrue(lock.get("memory_backfill_run_id"))
        self.assertEqual(lock.get("memory_backfill_state"), "awaiting_validation")
        self.assertIn("review_sidecar_cleanup", lock)
        self.assertTrue(
            (legacy_root / ".wavefoundry" / "index" / "memory-state.sqlite").is_file()
        )

        with patch.object(self.mod, "phase_cleanup") as cleanup:
            cleanup_result = self.mod.main(
                ["--root", str(legacy_root), "--cleanup"]
            )
        self.assertEqual(cleanup_result, self.backfill.ACTION_REQUIRED_EXIT)
        cleanup.assert_not_called()

    def test_default_upgrade_marks_indexed_after_phase_four(self):
        source = UPGRADE_PATH.read_text(encoding="utf-8")
        default_gate = source.index(
            'memory_run_id = memory_backfill.ensure_run(root, "upgrade")'
        )
        phase = source.index("phase_index_update(root)", default_gate)
        mark = source.index(
            "memory_backfill.complete_index_publication(root, memory_run_id)",
            default_gate,
        )
        self.assertLess(phase, mark)

    def test_default_upgrade_clears_docs_failure_and_runs_canonical_bounded_batch(self):
        source = UPGRADE_PATH.read_text(encoding="utf-8")
        docs_pass = source.index("phase_docs_gate(root)")
        clear = source.index("failed_phase=None", docs_pass)
        post_hook = source.index('_run_hook("post_docs_gate"', docs_pass)
        batch = source.index("server_impl._memory_backfill_batch_locked(", post_hook)
        action_return = source.index(
            "return memory_backfill.ACTION_REQUIRED_EXIT",
            batch,
        )
        self.assertLess(docs_pass, clear)
        self.assertLess(clear, post_hook)
        self.assertLess(post_hook, batch)
        self.assertLess(batch, action_return)


class ArchivedLegacyMemoryCheckpointCompatibilityTests(unittest.TestCase):
    """Exercise the incoming hook under the exact pghn/pgi7 parent runners.

    The parent owns the broad ``except SystemExit`` handler while the new
    extension is loaded from the incoming pack.  Keeping these as archive
    fixtures prevents a current-runner mock from silently widening the bridge.
    """

    ARCHIVE_DIR = Path(os.environ.get(
        "WAVEFOUNDRY_LEGACY_COMPAT_ARCHIVE_DIR",
        "/Users/coryhacking/.wavefoundry/dist",
    ))
    LEGACY_BUILDS = ("pghn", "pgi7")
    EXTENSION_MEMBER = ".wavefoundry/framework/scripts/upgrade_extensions.py"
    RUNNER_MEMBER = ".wavefoundry/framework/scripts/upgrade_wavefoundry.py"
    SERVER_MEMBER = ".wavefoundry/framework/scripts/server_impl.py"

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        (self.root / ".wavefoundry").mkdir()
        if str(SCRIPTS_ROOT) not in sys.path:
            sys.path.insert(0, str(SCRIPTS_ROOT))
        import upgrade_lib

        self.upgrade_lib = upgrade_lib

    def _archive(self, build: str) -> Path | None:
        path = self.ARCHIVE_DIR / f"wavefoundry-1.15.0.{build}.zip"
        return path if path.is_file() else None

    def _legacy_parent_seam_fixture(self, build: str):
        """Repository-controlled minimal pghn/pgi7 finalizer ABI fixture.

        Release verification prefers the actual archived packs when available.
        The committed seam keeps the exact old-parent contract executable in
        ordinary test runs without embedding multi-megabyte historical packs.
        """
        name = f"legacy_parent_seam_{build}_{id(self)}"
        parent = types.ModuleType(name)
        parent.__file__ = f"fixture://wavefoundry-1.15.0+{build}/upgrade_wavefoundry.py"

        class UpgradeContext:
            def __init__(self, root, from_version, to_version, zip_path, yes):
                self.root = root
                self.from_version = from_version
                self.to_version = to_version
                self.zip_path = zip_path
                self.yes = yes

        def _load_extension_module(zip_path):
            if zip_path is None:
                return None
            with zipfile.ZipFile(zip_path) as zf:
                source = zf.read(self.EXTENSION_MEMBER).decode("utf-8")
            module = types.ModuleType("upgrade_extensions")
            module.__file__ = self.EXTENSION_MEMBER
            exec(compile(source, module.__file__, "exec"), module.__dict__)
            return module

        def _finalize_failed_upgrade(root, tree_mutated, current_phase):
            import upgrade_lib

            if tree_mutated:
                upgrade_lib.update_upgrade_lock(
                    root,
                    failed_phase=current_phase,
                    failed_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                )
                print(
                    f"ERROR: Upgrade failed during phase '{current_phase}'.",
                    file=sys.stderr,
                )
            else:
                upgrade_lib.remove_upgrade_lock(root)

        def _run_hook(name, ctx, ext_mod):
            hook = getattr(ext_mod, name, None)
            if callable(hook):
                try:
                    hook(ctx)
                except SystemExit:
                    raise
                except Exception as exc:
                    print(f"ERROR: Extension hook '{name}' raised: {exc}", file=sys.stderr)
                    raise SystemExit(3)

        UpgradeContext.__module__ = name
        parent.UpgradeContext = UpgradeContext
        parent._load_extension_module = _load_extension_module
        parent._finalize_failed_upgrade = _finalize_failed_upgrade
        parent._run_hook = _run_hook
        sys.modules[name] = parent
        self.addCleanup(lambda: sys.modules.pop(name, None))
        return parent

    def _load_archived_parent(self, build: str):
        archive = self._archive(build)
        if archive is None:
            return self._legacy_parent_seam_fixture(build)
        with zipfile.ZipFile(archive) as zf:
            source = zf.read(self.RUNNER_MEMBER).decode("utf-8")
        name = f"archived_upgrade_wavefoundry_{build}_{id(self)}"
        parent = types.ModuleType(name)
        parent.__file__ = f"{archive}!{self.RUNNER_MEMBER}"
        sys.modules[name] = parent
        self.addCleanup(lambda: sys.modules.pop(name, None))
        exec(compile(source, parent.__file__, "exec"), parent.__dict__)
        return parent

    def _load_archived_server(self, build: str):
        archive = self._archive(build)
        if archive is None:
            server = types.ModuleType(f"legacy_server_seam_{build}_{id(self)}")
            server._mcp_subprocess_run = lambda *_args, **_kwargs: None
            server._load_upgrade_lib = lambda: None
            server._load_script = lambda _name: None

            def wf_upgrade_response(root, phase="preflight_to_docs_gate", mode="apply"):
                child = server._mcp_subprocess_run([])
                lock = server._load_upgrade_lib().read_upgrade_lock(root) or {}
                run_id = str(lock.get("memory_backfill_run_id") or "")
                backfill = server._load_script("memory_backfill")
                return {
                    "status": "ok" if child.returncode == 4 else "error",
                    "data": {
                        "state": "awaiting_memory_validation",
                        "output": child.stdout,
                        "memory_backfill": {
                            **backfill.run_summary(root, run_id),
                            **backfill.validation_worklist(root, run_id),
                        },
                    },
                    "next_tools": ["wf_reload_mcp", "memory_backfill", "memory_validate"],
                }

            server.wf_upgrade_response = wf_upgrade_response
            return server
        with zipfile.ZipFile(archive) as zf:
            source = zf.read(self.SERVER_MEMBER).decode("utf-8")
        name = f"archived_server_impl_{build}_{id(self)}"
        server = types.ModuleType(name)
        # Keep relative runtime lookups pointed at the checked-out scripts;
        # the fixture replaces the child process, not the old server's code.
        server.__file__ = str(SCRIPTS_ROOT / "server_impl.py")
        sys.modules[name] = server
        self.addCleanup(lambda: sys.modules.pop(name, None))
        exec(compile(source, f"{archive}!{self.SERVER_MEMBER}", "exec"), server.__dict__)
        return server

    def _incoming_pack(self) -> Path:
        path = self.root / "incoming-memory-checkpoint.zip"
        with zipfile.ZipFile(path, "w") as zf:
            zf.write(SCRIPTS_ROOT / "upgrade_extensions.py", self.EXTENSION_MEMBER)
        return path

    def _context(self, parent, build: str, pack: Path):
        return parent.UpgradeContext(
            self.root, f"1.15.0+{build}", "1.15.0+incoming", pack, True
        )

    def _pause_then_finalize(
        self, extension, parent, ctx, *, state="awaiting_memory_publication", phase="index_update"
    ):
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            try:
                extension._pause_for_memory_action(
                    ctx,
                    state=state,
                    run_id="archive-run",
                    message="fixture pause",
                )
            except SystemExit as exc:
                self.assertEqual(exc.code, 4)
                parent._finalize_failed_upgrade(self.root, True, phase)
        return stderr.getvalue()

    def test_archived_pghn_and_pgi7_parents_preserve_action_required_checkpoint(self):
        """The exact legacy finalizers do not stamp the normal pause as failure."""
        for build in self.LEGACY_BUILDS:
            with self.subTest(build=build):
                self.upgrade_lib.write_upgrade_lock(
                    self.root, f"1.15.0+{build}", "1.15.0+incoming"
                )
                parent = self._load_archived_parent(build)
                original = parent._finalize_failed_upgrade
                extension = parent._load_extension_module(self._incoming_pack())
                self.assertIsNotNone(extension)
                stderr = self._pause_then_finalize(
                    extension, parent, self._context(parent, build, self._incoming_pack())
                )
                lock = self.upgrade_lib.read_upgrade_lock(self.root) or {}
                self.assertEqual(lock.get("current_phase"), "awaiting_memory_publication")
                self.assertEqual(lock.get("failed_phase"), "awaiting_memory_validation")
                self.assertIsNone(lock.get("failed_at"))
                self.assertEqual(lock.get("action_required", {}).get("run_id"), "archive-run")
                self.assertEqual(
                    lock.get("action_required", {}).get("state"),
                    "awaiting_memory_publication",
                )
                self.assertEqual(parent._finalize_failed_upgrade, original)
                self.assertNotIn("Upgrade failed during phase", stderr)
                self.upgrade_lib.remove_upgrade_lock(self.root)

    def test_archived_parent_fails_closed_for_mismatched_pause_context(self):
        """The one-shot exception cannot suppress an unrelated SystemExit."""
        for build in self.LEGACY_BUILDS:
            with self.subTest(build=build, case="wrong-phase"):
                self.upgrade_lib.write_upgrade_lock(
                    self.root, f"1.15.0+{build}", "1.15.0+incoming"
                )
                parent = self._load_archived_parent(build)
                original = parent._finalize_failed_upgrade
                pack = self._incoming_pack()
                extension = parent._load_extension_module(pack)
                self._pause_then_finalize(
                    extension, parent, self._context(parent, build, pack), phase="docs_gate"
                )
                lock = self.upgrade_lib.read_upgrade_lock(self.root) or {}
                self.assertEqual(lock.get("failed_phase"), "docs_gate")
                self.assertIsNotNone(lock.get("failed_at"))
                self.assertEqual(parent._finalize_failed_upgrade, original)
                self.upgrade_lib.remove_upgrade_lock(self.root)

            with self.subTest(build=build, case="wrong-token"):
                self.upgrade_lib.write_upgrade_lock(
                    self.root, f"1.15.0+{build}", "1.15.0+incoming"
                )
                parent = self._load_archived_parent(build)
                original = parent._finalize_failed_upgrade
                pack = self._incoming_pack()
                extension = parent._load_extension_module(pack)
                ctx = self._context(parent, build, pack)
                try:
                    extension._pause_for_memory_action(
                        ctx,
                        state="awaiting_memory_validation",
                        run_id="archive-run",
                        message="fixture pause",
                    )
                except SystemExit as exc:
                    self.assertEqual(exc.code, 4)
                    lock = self.upgrade_lib.read_upgrade_lock(self.root) or {}
                    lock["action_required"]["token"] = "wrong-token"
                    self.upgrade_lib.update_upgrade_lock(
                        self.root, action_required=lock["action_required"]
                    )
                    parent._finalize_failed_upgrade(self.root, True, "index_update")
                lock = self.upgrade_lib.read_upgrade_lock(self.root) or {}
                self.assertEqual(lock.get("failed_phase"), "index_update")
                self.assertIsNotNone(lock.get("failed_at"))
                self.assertEqual(parent._finalize_failed_upgrade, original)
                self.upgrade_lib.remove_upgrade_lock(self.root)

            with self.subTest(build=build, case="wrong-root"):
                self.upgrade_lib.write_upgrade_lock(
                    self.root, f"1.15.0+{build}", "1.15.0+incoming"
                )
                other_root = self.root / f"other-{build}"
                (other_root / ".wavefoundry").mkdir(parents=True)
                self.upgrade_lib.write_upgrade_lock(
                    other_root, f"1.15.0+{build}", "1.15.0+incoming"
                )
                parent = self._load_archived_parent(build)
                original = parent._finalize_failed_upgrade
                pack = self._incoming_pack()
                extension = parent._load_extension_module(pack)
                ctx = self._context(parent, build, pack)
                try:
                    extension._pause_for_memory_action(
                        ctx,
                        state="awaiting_memory_validation",
                        run_id="archive-run",
                        message="fixture pause",
                    )
                except SystemExit as exc:
                    self.assertEqual(exc.code, 4)
                    parent._finalize_failed_upgrade(other_root, True, "index_update")
                other_lock = self.upgrade_lib.read_upgrade_lock(other_root) or {}
                self.assertEqual(other_lock.get("failed_phase"), "index_update")
                self.assertIsNotNone(other_lock.get("failed_at"))
                self.assertEqual(parent._finalize_failed_upgrade, original)
                self.upgrade_lib.remove_upgrade_lock(self.root)
                self.upgrade_lib.remove_upgrade_lock(other_root)

            with self.subTest(build=build, case="wrong-exit"):
                self.upgrade_lib.write_upgrade_lock(
                    self.root, f"1.15.0+{build}", "1.15.0+incoming"
                )
                parent = self._load_archived_parent(build)
                original = parent._finalize_failed_upgrade
                pack = self._incoming_pack()
                extension = parent._load_extension_module(pack)
                ctx = self._context(parent, build, pack)
                extension._arm_memory_action_required(
                    ctx, state="awaiting_memory_validation", run_id="archive-run"
                )
                try:
                    raise SystemExit(3)
                except SystemExit:
                    parent._finalize_failed_upgrade(self.root, True, "index_update")
                lock = self.upgrade_lib.read_upgrade_lock(self.root) or {}
                self.assertEqual(lock.get("failed_phase"), "index_update")
                self.assertIsNotNone(lock.get("failed_at"))
                self.assertEqual(parent._finalize_failed_upgrade, original)
                self.upgrade_lib.remove_upgrade_lock(self.root)

            with self.subTest(build=build, case="unknown-build"):
                self.upgrade_lib.write_upgrade_lock(
                    self.root, "1.15.0+pgi6", "1.15.0+incoming"
                )
                parent = self._load_archived_parent(build)
                original = parent._finalize_failed_upgrade
                pack = self._incoming_pack()
                extension = parent._load_extension_module(pack)
                ctx = parent.UpgradeContext(
                    self.root, "1.15.0+pgi6", "1.15.0+incoming", pack, True
                )
                self._pause_then_finalize(extension, parent, ctx)
                lock = self.upgrade_lib.read_upgrade_lock(self.root) or {}
                self.assertEqual(lock.get("failed_phase"), "index_update")
                self.assertIsNotNone(lock.get("failed_at"))
                self.assertEqual(parent._finalize_failed_upgrade, original)
                self.upgrade_lib.remove_upgrade_lock(self.root)

            with self.subTest(build=build, case="missing-marker"):
                self.upgrade_lib.write_upgrade_lock(
                    self.root, f"1.15.0+{build}", "1.15.0+incoming"
                )
                parent = self._load_archived_parent(build)
                original = parent._finalize_failed_upgrade
                pack = self._incoming_pack()
                extension = parent._load_extension_module(pack)
                ctx = self._context(parent, build, pack)
                try:
                    extension._pause_for_memory_action(
                        ctx, state="awaiting_memory_publication",
                        run_id="archive-run", message="fixture pause",
                    )
                except SystemExit as exc:
                    self.assertEqual(exc.code, 4)
                    self.upgrade_lib.update_upgrade_lock(self.root, action_required=None)
                    parent._finalize_failed_upgrade(self.root, True, "index_update")
                lock = self.upgrade_lib.read_upgrade_lock(self.root) or {}
                self.assertEqual(lock.get("failed_phase"), "index_update")
                self.assertIsNotNone(lock.get("failed_at"))
                self.assertEqual(parent._finalize_failed_upgrade, original)
                self.upgrade_lib.remove_upgrade_lock(self.root)

            with self.subTest(build=build, case="hook-error"):
                self.upgrade_lib.write_upgrade_lock(
                    self.root, f"1.15.0+{build}", "1.15.0+incoming"
                )
                parent = self._load_archived_parent(build)
                original = parent._finalize_failed_upgrade
                pack = self._incoming_pack()
                extension = parent._load_extension_module(pack)
                with patch.object(extension, "pre_index_update", side_effect=RuntimeError("boom")):
                    try:
                        parent._run_hook(
                            "pre_index_update", self._context(parent, build, pack), extension
                        )
                    except SystemExit as exc:
                        self.assertEqual(exc.code, 3)
                        parent._finalize_failed_upgrade(self.root, True, "index_update")
                lock = self.upgrade_lib.read_upgrade_lock(self.root) or {}
                self.assertEqual(lock.get("failed_phase"), "index_update")
                self.assertIsNotNone(lock.get("failed_at"))
                self.assertEqual(parent._finalize_failed_upgrade, original)
                self.upgrade_lib.remove_upgrade_lock(self.root)

    def test_archived_servers_execute_validation_transition_envelope(self):
        """Before reload the exact pghn/pgi7 servers return validation success."""
        for build in self.LEGACY_BUILDS:
            with self.subTest(build=build):
                server = self._load_archived_server(build)
                lock = {"memory_backfill_run_id": "archive-run"}
                backfill = MagicMock()
                backfill.run_summary.return_value = {
                    "run_id": "archive-run", "state": "ready_for_index",
                }
                backfill.validation_worklist.return_value = {
                    "validation_worklist": [], "validation_worklist_count": 0,
                }
                child = MagicMock(
                    returncode=4,
                    stdout="Historical memory is ready for receipt-owned publication.\n",
                    stderr="",
                )
                legacy_lib = types.SimpleNamespace(read_upgrade_lock=lambda _root: lock)
                with patch.object(server, "_mcp_subprocess_run", return_value=child), \
                     patch.object(server, "_load_upgrade_lib", return_value=legacy_lib), \
                     patch.object(server, "_load_script", return_value=backfill):
                    result = server.wf_upgrade_response(self.root)
                self.assertEqual(result["status"], "ok")
                self.assertEqual(result["data"]["state"], "awaiting_memory_validation")
                self.assertIn("memory_validate", result["next_tools"])
                self.assertIn("receipt-owned publication", result["data"]["output"])


class CurrentLineageMemoryCheckpointPauseTests(unittest.TestCase):
    """Wave 1uf67: main's own ``except SystemExit`` handling must not report the
    designed memory-checkpoint pause as an upgrade failure or stamp a failure
    marker over the checkpoint's lock state.

    The archived pghn/pgi7 bridge class above covers only legacy parents; this
    class drives the CURRENT runner's full-upgrade path to the
    ``pre_index_update`` pause (typed ``action_required`` block, exit 4).
    """

    def _drive_main_to_index_update_exit(self, pause):
        mod = load_upgrade_module()
        import upgrade_extensions
        import upgrade_lib
        import venv_bootstrap

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir).resolve()
            (root / ".wavefoundry").mkdir()
            _stage_review_protocol_seeds(root)
            (root / "docs" / "waves").mkdir(parents=True)
            (root / "docs" / "workflow-config.json").write_text(
                "{}\n", encoding="utf-8"
            )

            def hook(name, ctx, ext_mod):
                if name == "pre_index_update":
                    pause(root)

            stdout, stderr = io.StringIO(), io.StringIO()
            with patch.object(mod, "phase_preflight", return_value=(None, None, None)), \
                 patch.object(mod, "_load_extension_module", return_value=None), \
                 patch.object(mod, "_run_hook", side_effect=hook), \
                 patch.object(upgrade_extensions, "pre_extract"), \
                 patch.object(mod, "_snapshot_pre_extract_chunker_versions", return_value={}), \
                 patch.object(mod, "_snapshot_pre_extract_versions", return_value={}), \
                 patch.object(mod, "phase_surface_rendering"), \
                 patch.object(mod, "_stamp_manifest_revision", return_value=False), \
                 patch.object(mod, "phase_pruning", return_value=0), \
                 patch.object(mod, "materialize_secrets_policy", return_value="ok"), \
                 patch.object(mod, "materialize_lifecycle_policy", return_value="ok"), \
                 patch.object(mod, "phase_docs_gate"), \
                 patch.object(mod, "phase_index_update", return_value=True), \
                 patch.object(mod, "_emit_primary_summary_via_delegate_or_fallback"), \
                 patch.object(venv_bootstrap, "ensure_python_resolves", return_value="ok"), \
                 patch.dict(os.environ, {"WAVEFOUNDRY_SKIP_PYTHON_HEAL": "1"}, clear=False), \
                 contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                with self.assertRaises(SystemExit) as raised:
                    mod.main(["--root", str(root), "--yes"])
                lock = upgrade_lib.read_upgrade_lock(root) or {}
        return raised.exception, stdout.getvalue() + stderr.getvalue(), lock

    def test_typed_checkpoint_pause_is_not_finalized_as_failure(self):
        """Red-first for 1uf67: no failure prose AND no failure lock stamp."""
        import memory_backfill
        import upgrade_lib

        def pause(root):
            upgrade_lib.update_upgrade_lock(
                root,
                current_phase="awaiting_memory_publication",
                action_required={
                    "kind": "historical_memory",
                    "state": "awaiting_memory_publication",
                    "resume_phase": "resume_after_memory",
                    "run_id": "field-run",
                    "token": "field-token",
                },
                failed_phase=None,
                failed_at=None,
            )
            raise SystemExit(memory_backfill.ACTION_REQUIRED_EXIT)

        exc, output, lock = self._drive_main_to_index_update_exit(pause)
        self.assertEqual(exc.code, memory_backfill.ACTION_REQUIRED_EXIT)
        self.assertNotIn("Upgrade failed", output)
        self.assertIn("resume_after_memory", output)
        self.assertEqual(
            (lock.get("action_required") or {}).get("run_id"), "field-run"
        )
        self.assertIsNone(lock.get("failed_phase"))
        self.assertIsNone(lock.get("failed_at"))

    def test_untyped_exit_four_still_finalizes_as_failure(self):
        """Over-suppression guard: exit 4 WITHOUT a typed action_required block
        is a genuine failure and keeps the retained-lock failure report."""
        import memory_backfill

        def pause(root):
            raise SystemExit(memory_backfill.ACTION_REQUIRED_EXIT)

        exc, output, lock = self._drive_main_to_index_update_exit(pause)
        self.assertEqual(exc.code, memory_backfill.ACTION_REQUIRED_EXIT)
        self.assertIn("Upgrade failed during phase 'index_update'", output)
        self.assertEqual(lock.get("failed_phase"), "index_update")
        self.assertIsNotNone(lock.get("failed_at"))


class HistoricalMemoryUpgradeExtensionBootstrapTests(unittest.TestCase):
    def setUp(self):
        self.ext = _load_upgrade_extensions()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / ".wavefoundry" / "index").mkdir(parents=True)
        (self.root / "docs" / "waves").mkdir(parents=True)
        (self.root / ".wavefoundry" / "upgrade-in-progress.json").write_text(
            "{}\n", encoding="utf-8"
        )
        sys.path.insert(0, str(SCRIPTS_ROOT))
        import memory_backfill

        self.backfill = memory_backfill
        self.ctx = MagicMock(root=self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def _seed_graph_builder_doc(self, *, code_version="44", doc_version="44"):
        scripts = self.root / ".wavefoundry" / "framework" / "scripts"
        scripts.mkdir(parents=True, exist_ok=True)
        scripts.joinpath("graph_indexer.py").write_text(
            f'GRAPH_BUILDER_VERSION = "{code_version}"\n', encoding="utf-8"
        )
        reliability = self.root / "docs" / "RELIABILITY.md"
        reliability.parent.mkdir(parents=True, exist_ok=True)
        reliability.write_text(
            "# Reliability\n\n"
            f"- graph builder version `{doc_version}`\n"
            "- operator-authored detail stays intact\n",
            encoding="utf-8",
        )
        return scripts, reliability

    def _seed_scalar_docs(self):
        scripts = self.root / ".wavefoundry" / "framework" / "scripts"
        scripts.mkdir(parents=True, exist_ok=True)
        scripts.joinpath("indexer.py").write_text(
            'DOCS_MODEL = "docs-v1"\nCODE_MODEL = "code-v1"\nRERANKER_MODEL = "reranker-v1"\n',
            encoding="utf-8",
        )
        scripts.joinpath("index_state_store.py").write_text(
            'STATE_STORE_SCHEMA_VERSION = "6"\n', encoding="utf-8"
        )
        scripts.joinpath("graph_indexer.py").write_text(
            'GRAPH_BUILDER_VERSION = "45"\n', encoding="utf-8"
        )
        scripts.joinpath("chunker.py").write_text(
            'CHUNKER_VERSION = "32"\n', encoding="utf-8"
        )
        reliability = self.root / "docs" / "RELIABILITY.md"
        reliability.parent.mkdir(parents=True, exist_ok=True)
        reliability.write_text(
            "# Reliability\n\n"
            "- state-store schema version `6`\n"
            "- graph builder version `45`\n",
            encoding="utf-8",
        )
        performance = self.root / "docs" / "architecture" / "performance-budget.md"
        performance.parent.mkdir(parents=True, exist_ok=True)
        performance.write_text(
            "# Performance\n\n"
            "- docs embedding model `docs-v1`\n"
            "- code embedding model `code-v1`\n"
            "- reranker model `reranker-v1`\n"
            "- chunker version `32`\n",
            encoding="utf-8",
        )
        return scripts, reliability, performance

    def _skip_sidecar_cleanup(self):
        path = self.root / ".wavefoundry" / "upgrade-in-progress.json"
        state = json.loads(path.read_text(encoding="utf-8"))
        state["review_sidecar_cleanup"] = {}
        path.write_text(json.dumps(state) + "\n", encoding="utf-8")

    def test_installing_upgrade_reconciles_exact_graph_builder_doc_claim(self):
        scripts, reliability = self._seed_graph_builder_doc()
        self._skip_sidecar_cleanup()

        with patch.object(self.ext, "_cut_over_runtime_locks"):
            self.ext.pre_extract(self.ctx)
        scripts.joinpath("graph_indexer.py").write_text(
            'GRAPH_BUILDER_VERSION = "45"\n', encoding="utf-8"
        )

        self.ext.pre_docs_gate(self.ctx)

        self.assertEqual(
            reliability.read_text(encoding="utf-8"),
            "# Reliability\n\n"
            "- graph builder version `45`\n"
            "- operator-authored detail stays intact\n",
        )
        lock = json.loads(
            (self.root / ".wavefoundry" / "upgrade-in-progress.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(lock["graph_builder_doc_claim_pre_extract"], "")

    def test_graph_builder_doc_reconciliation_survives_interruption_after_extract(self):
        scripts, reliability = self._seed_graph_builder_doc()
        packs = self.root / "packs"
        packs.mkdir()
        pack = packs / "wavefoundry-first.zip"
        retry_pack = packs / "wavefoundry-retry.zip"
        pack.write_bytes(b"same verified pack")
        retry_pack.write_bytes(pack.read_bytes())
        import upgrade_lib
        import upgrade_wavefoundry

        upgrade_lib.write_upgrade_lock(
            self.root, "1.14.0", "1.15.0+pgi2", pack
        )
        self.ctx.zip_path = pack
        self._skip_sidecar_cleanup()
        with patch.object(self.ext, "_cut_over_runtime_locks"):
            self.ext.pre_extract(self.ctx)
        scripts.joinpath("graph_indexer.py").write_text(
            'GRAPH_BUILDER_VERSION = "45"\n', encoding="utf-8"
        )

        with patch.object(upgrade_lib, "is_lock_stale", return_value=True):
            upgrade_wavefoundry._clear_stale_upgrade_lock_for_preflight(
                self.root, upgrade_lib
            )
        upgrade_lib.write_upgrade_lock(
            self.root, "1.15.0+pgi2", "1.15.0+pgi2", retry_pack
        )
        upgrade_lib.update_upgrade_lock(self.root, review_sidecar_cleanup={})

        recovery_ctx = MagicMock(root=self.root)
        self.ext.pre_docs_gate(recovery_ctx)

        self.assertIn(
            "graph builder version `45`", reliability.read_text(encoding="utf-8")
        )
        lock = json.loads(
            (self.root / ".wavefoundry" / "upgrade-in-progress.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(lock["graph_builder_doc_claim_pre_extract"], "")

    def test_graph_builder_doc_reconciliation_preserves_mid_upgrade_customization(self):
        scripts, reliability = self._seed_graph_builder_doc()
        self._skip_sidecar_cleanup()
        with patch.object(self.ext, "_cut_over_runtime_locks"):
            self.ext.pre_extract(self.ctx)
        scripts.joinpath("graph_indexer.py").write_text(
            'GRAPH_BUILDER_VERSION = "45"\n', encoding="utf-8"
        )
        customized = reliability.read_text(encoding="utf-8").replace(
            "graph builder version `44`", "graph builder version `operator-owned`"
        )
        reliability.write_text(customized, encoding="utf-8")

        self.ext.pre_docs_gate(self.ctx)

        self.assertEqual(reliability.read_text(encoding="utf-8"), customized)

    def test_graph_builder_doc_reconciliation_requires_pre_extract_code_doc_match(self):
        scripts, reliability = self._seed_graph_builder_doc(doc_version="43")
        self._skip_sidecar_cleanup()
        with patch.object(self.ext, "_cut_over_runtime_locks"):
            self.ext.pre_extract(self.ctx)
        scripts.joinpath("graph_indexer.py").write_text(
            'GRAPH_BUILDER_VERSION = "45"\n', encoding="utf-8"
        )

        self.ext.pre_docs_gate(self.ctx)

        self.assertIn("graph builder version `43`", reliability.read_text(encoding="utf-8"))

    def test_scalar_doc_reconciliation_advances_models_chunker_and_state_store(self):
        scripts, reliability, performance = self._seed_scalar_docs()
        self._skip_sidecar_cleanup()
        with patch.object(self.ext, "_cut_over_runtime_locks"):
            self.ext.pre_extract(self.ctx)
        scripts.joinpath("indexer.py").write_text(
            'DOCS_MODEL = "docs-v2"\nCODE_MODEL = "code-v2"\nRERANKER_MODEL = "reranker-v2"\n',
            encoding="utf-8",
        )
        scripts.joinpath("index_state_store.py").write_text(
            'STATE_STORE_SCHEMA_VERSION = "7"\n', encoding="utf-8"
        )
        scripts.joinpath("chunker.py").write_text(
            'CHUNKER_VERSION = "33"\n', encoding="utf-8"
        )

        self.ext.pre_docs_gate(self.ctx)

        self.assertIn("state-store schema version `7`", reliability.read_text(encoding="utf-8"))
        self.assertIn("graph builder version `45`", reliability.read_text(encoding="utf-8"))
        updated = performance.read_text(encoding="utf-8")
        for claim in (
            "docs embedding model `docs-v2`",
            "code embedding model `code-v2`",
            "reranker model `reranker-v2`",
            "chunker version `33`",
        ):
            self.assertIn(claim, updated)
        lock = json.loads(
            (self.root / ".wavefoundry" / "upgrade-in-progress.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(lock["docs_scalar_claims_pre_extract"], {})

    def test_scalar_snapshot_survives_retry_lock_without_graph_claim(self):
        scripts = self.root / ".wavefoundry" / "framework" / "scripts"
        scripts.mkdir(parents=True, exist_ok=True)
        scripts.joinpath("indexer.py").write_text(
            'DOCS_MODEL = "docs-v1"\n', encoding="utf-8"
        )
        performance = self.root / "docs" / "architecture" / "performance-budget.md"
        performance.parent.mkdir(parents=True, exist_ok=True)
        performance.write_text(
            "- docs embedding model `docs-v1`\n", encoding="utf-8"
        )
        pack = self.root / "pack.zip"
        pack.write_bytes(b"verified pack")
        import upgrade_lib

        upgrade_lib.write_upgrade_lock(self.root, "1.14.0", "1.15.0", pack)
        self.ctx.zip_path = pack
        with patch.object(self.ext, "_cut_over_runtime_locks"):
            self.ext.pre_extract(self.ctx)

        upgrade_lib.write_upgrade_lock(self.root, "1.15.0", "1.15.0", pack)
        lock = upgrade_lib.read_upgrade_lock(self.root) or {}
        self.assertEqual(lock["docs_scalar_claims_pre_extract"], {"docs embedding model": "docs-v1"})

    def test_post_docs_gate_pauses_pre_upgrade_runner_before_index(self):
        wave = self.root / "docs" / "waves" / "1old closed"
        wave.mkdir()
        wave.joinpath("wave.md").write_text(
            "# Wave\n\nStatus: closed\n", encoding="utf-8"
        )
        with patch.object(
            self.ext, "_installed_memory_backfill", return_value=self.backfill
        ), self.assertRaises(SystemExit) as raised:
            self.ext.post_docs_gate(self.ctx)
        self.assertEqual(raised.exception.code, self.backfill.ACTION_REQUIRED_EXIT)
        lock = json.loads(
            (self.root / ".wavefoundry" / "upgrade-in-progress.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(lock["memory_backfill_state"], "awaiting_validation")
        self.assertEqual(lock["memory_backfill_pending"], 1)

    def test_post_docs_gate_leaves_protocol_two_runner_to_process_bounded_batch(self):
        wave = self.root / "docs" / "waves" / "1old closed"
        wave.mkdir()
        wave.joinpath("wave.md").write_text(
            "# Wave\n\nStatus: closed\n", encoding="utf-8"
        )
        self.ctx.runner_protocol = 2
        with patch.object(
            self.ext, "_installed_memory_backfill", return_value=self.backfill
        ):
            self.assertIsNone(self.ext.post_docs_gate(self.ctx))
        lock = json.loads(
            (self.root / ".wavefoundry" / "upgrade-in-progress.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(lock["memory_backfill_state"], "awaiting_validation")

    def test_pre_docs_gate_loads_new_module_and_runs_sidecar_cleanup_for_old_runner(self):
        """An old loaded runner reaches the new cutover only through this hook."""

        scripts = self.root / ".wavefoundry" / "framework" / "scripts"
        scripts.mkdir(parents=True)
        shutil.copy2(UPGRADE_PATH, scripts / "upgrade_wavefoundry.py")

        wave_dir = self.root / "docs" / "waves" / "1hist external"
        wave_dir.mkdir()
        wave_bytes = (
            b"# Wave\nreview-evidence-source: events.jsonl\n\n"
            b"## Finding Synthesis\n\nHistorical narrative.\n"
        )
        (wave_dir / "wave.md").write_bytes(wave_bytes)
        (wave_dir / "events.jsonl").write_bytes(b"")
        waves = self.root / "docs" / "waves"
        (waves / "review-evidence-adoptions.json").write_bytes(b"{not json")
        (waves / "review-evidence-migration.json").write_bytes(b"{also not json")

        self.ext.pre_docs_gate(self.ctx)

        self.assertFalse((waves / "review-evidence-adoptions.json").exists())
        self.assertFalse((waves / "review-evidence-migration.json").exists())
        self.assertEqual((wave_dir / "wave.md").read_bytes(), wave_bytes)
        self.assertEqual((wave_dir / "events.jsonl").read_bytes(), b"")
        lock = json.loads(
            (
                self.root / ".wavefoundry" / "upgrade-in-progress.json"
            ).read_text(encoding="utf-8")
        )
        self.assertIn("review_sidecar_cleanup", lock)
        self.assertTrue(lock["review_sidecar_cleanup"]["restart_required"])

        with patch.object(self.ext, "_installed_upgrade_module") as loader:
            self.ext.pre_docs_gate(self.ctx)
        loader.assert_not_called()

    def test_pre_docs_gate_threads_known_from_version_into_restart_scope(self):
        """Wave 1to78 AC-3 (call path 2): the extension seam passes
        ctx.from_version; a converged tree upgraded from a known post-1.15
        version records restart_required false."""

        scripts = self.root / ".wavefoundry" / "framework" / "scripts"
        scripts.mkdir(parents=True)
        shutil.copy2(UPGRADE_PATH, scripts / "upgrade_wavefoundry.py")

        ctx = MagicMock(root=self.root, from_version="1.15.1")
        self.ext.pre_docs_gate(ctx)

        lock = json.loads(
            (
                self.root / ".wavefoundry" / "upgrade-in-progress.json"
            ).read_text(encoding="utf-8")
        )
        self.assertIn("review_sidecar_cleanup", lock)
        self.assertEqual(lock["review_sidecar_cleanup"]["removed_sidecars"], 0)
        self.assertFalse(lock["review_sidecar_cleanup"]["restart_required"])

    def test_pre_docs_gate_reloads_stale_review_evidence_module_in_place(self):
        """1t49m field report: the installed upgrader resolves its function-local
        ``from review_evidence import ...`` through ``sys.modules``, so a
        pre-extraction cache would hand the new cleanup OLD code. A pre-1.15
        module has no ``PROJECT_STATE_PUBLICATION_LOCK_REL`` at all; the hook
        must re-execute the on-disk source in place before the cutover."""

        scripts = self.root / ".wavefoundry" / "framework" / "scripts"
        scripts.mkdir(parents=True)
        shutil.copy2(UPGRADE_PATH, scripts / "upgrade_wavefoundry.py")

        if str(SCRIPTS_ROOT) not in sys.path:
            sys.path.insert(0, str(SCRIPTS_ROOT))
        import review_evidence

        waves = self.root / "docs" / "waves"
        (waves / "review-evidence-adoptions.json").write_bytes(b"{not json")

        original = review_evidence.PROJECT_STATE_PUBLICATION_LOCK_REL
        del review_evidence.PROJECT_STATE_PUBLICATION_LOCK_REL
        try:
            self.ext.pre_docs_gate(self.ctx)
        finally:
            if not hasattr(review_evidence, "PROJECT_STATE_PUBLICATION_LOCK_REL"):
                review_evidence.PROJECT_STATE_PUBLICATION_LOCK_REL = original

        # The reload repaired the cached module IN PLACE: same object, fresh code.
        self.assertIs(sys.modules["review_evidence"], review_evidence)
        self.assertEqual(
            review_evidence.PROJECT_STATE_PUBLICATION_LOCK_REL, original
        )
        self.assertFalse((waves / "review-evidence-adoptions.json").exists())
        lock = json.loads(
            (self.root / ".wavefoundry" / "upgrade-in-progress.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertIn("review_sidecar_cleanup", lock)

    def test_installed_memory_backfill_reloads_stale_cached_module_in_place(self):
        """Sibling of the review_evidence seam: a pre-upgrade runner's cached
        ``memory_backfill`` must not shadow the just-extracted coordinator."""

        original = self.backfill.ensure_run

        def stale(*_args, **_kwargs):
            raise AssertionError("stale pre-extraction memory_backfill was used")

        self.backfill.ensure_run = stale
        try:
            loaded = self.ext._installed_memory_backfill(self.root)
        finally:
            if self.backfill.ensure_run is stale:
                self.backfill.ensure_run = original

        self.assertIs(loaded, self.backfill)
        self.assertIs(sys.modules["memory_backfill"], self.backfill)
        self.assertIsNot(loaded.ensure_run, stale)

    def test_pre_docs_gate_migrates_memory_naming_for_pre_1_15_runner(self):
        """1t9w7: upgrades from pre-1.15 rename legacy memory records to the
        lifecycle naming before docs-lint sees them; the gate is version-
        gated but the migration itself is idempotent."""
        import io as _io
        import contextlib as _contextlib

        if str(SCRIPTS_ROOT) not in sys.path:
            sys.path.insert(0, str(SCRIPTS_ROOT))
        import memory_records

        content = memory_records.render_memory_record(
            memory_id="mem-old-lesson", kind="decision",
            summary="A durable decision from the pre-naming era.",
            evidence=["`1abcd-bug some-change` — observed"],
            targets=["src/a.py"], date="2026-01-10",
        )
        memory_records.write_memory_record(self.root, content, "mem-old-lesson")
        live_doc = self.root / "docs" / "live.md"
        live_doc.write_text(
            "Live ref `mem-old-lesson`; unknown `mem-never-existed-here`.\n",
            encoding="utf-8",
        )
        # Short-circuit the sidecar-cleanup half: the migration runs before it.
        (self.root / ".wavefoundry" / "upgrade-in-progress.json").write_text(
            '{"review_sidecar_cleanup": {}}\n', encoding="utf-8"
        )
        ctx = MagicMock(root=self.root, from_version="1.14.0")
        out = _io.StringIO()
        with _contextlib.redirect_stdout(out):
            self.ext.pre_docs_gate(ctx)
        memory_dir = self.root / "docs" / "agents" / "memory"
        self.assertFalse((memory_dir / "mem-old-lesson.md").exists())
        migrated = list(memory_dir.glob("*-mem old-lesson.md"))
        self.assertEqual(len(migrated), 1, list(memory_dir.iterdir()))
        # Live doc surfaces are rewritten and the mapping and residuals are
        # reported loudly in the upgrade output (operator P1 repair).
        live_text = live_doc.read_text(encoding="utf-8")
        self.assertIn(f"`{migrated[0].stem}`", live_text)
        self.assertNotIn("`mem-old-lesson`", live_text)
        report = out.getvalue()
        self.assertIn("mem-old-lesson ->", report)
        self.assertIn("repaired", report)
        self.assertIn("mem-never-existed-here", report)
        self.assertIn("docs/live.md", report)

        # From-versions at or past the gate skip the migration call entirely.
        with patch.object(self.ext, "_migrate_memory_naming") as migrate:
            self.ext.pre_docs_gate(
                MagicMock(root=self.root, from_version="1.15.0")
            )
        migrate.assert_not_called()

    def test_post_index_hook_seals_ready_run_for_pre_upgrade_runner(self):
        with patch.object(
            self.ext, "_installed_memory_backfill", return_value=self.backfill
        ):
            self.ext.post_docs_gate(self.ctx)
            lock = json.loads(
                (self.root / ".wavefoundry" / "upgrade-in-progress.json").read_text(
                    encoding="utf-8"
                )
            )
            run_id = lock["memory_backfill_run_id"]
            self.ext.post_index_update(self.ctx)
        self.assertEqual(
            self.backfill.run_summary(self.root, run_id)["state"], "indexed"
        )

    def test_old_runner_hook_hands_candidate_publication_to_installed_runner(self):
        import memory_records
        import server_impl

        self.root.joinpath("foo.py").write_text("LOCAL = True\n", encoding="utf-8")
        wave = self.root / "docs" / "waves" / "1old closed"
        wave.mkdir()
        change_id = "1old1-enh local-choice"
        wave.joinpath("wave.md").write_text(
            f"# Wave\n\nStatus: closed\n\nChange ID: `{change_id}`\n",
            encoding="utf-8",
        )
        wave.joinpath(f"{change_id}.md").write_text(
            "# Change\n\n## Decision Log\n\n"
            "| Date | Decision | Reason | Alternatives |\n"
            "| --- | --- | --- | --- |\n"
            "| 2026-01-01 | Keep `foo.py` local | Avoid remote authority | none |\n",
            encoding="utf-8",
        )
        with patch.object(
            self.ext, "_installed_memory_backfill", return_value=self.backfill
        ), self.assertRaises(SystemExit):
            self.ext.post_docs_gate(self.ctx)
        server_impl.memory_backfill_response(
            self.root, mode="create", entry_path="upgrade"
        )
        candidate = memory_records.load_memory_records(self.root)[0]
        validated = server_impl.memory_validate_response(
            self.root,
            candidate["memory_id"],
            "promote",
            "Reuse the local decision.",
            "The target remains current.",
            True,
            True,
            "none",
        )
        self.assertEqual(validated["status"], "ok")

        with patch.object(
            self.ext, "_installed_memory_backfill", return_value=self.backfill
        ), self.assertRaises(SystemExit) as raised:
            self.ext.pre_index_update(self.ctx)
        self.assertEqual(raised.exception.code, self.backfill.ACTION_REQUIRED_EXIT)
        with patch.object(
            self.ext, "_installed_memory_backfill", return_value=self.backfill
        ):
            run_id = json.loads(
                (
                    self.root / ".wavefoundry" / "upgrade-in-progress.json"
                ).read_text(encoding="utf-8")
            )["memory_backfill_run_id"]

        self.assertEqual(
            self.backfill.run_summary(self.root, run_id)["state"],
            "ready_for_index",
        )
        self.assertNotIn(self.backfill.INDEX_PUBLICATION_RUN_ENV, os.environ)


class JournalMigrationTests(unittest.TestCase):
    """1t9w9 journal retirement: the mechanical ``_migrate_journals`` hook.

    The pristine-template oracle was validated live against this repository's
    own 99 historical scaffolds before being frozen; these tests pin the
    classification gates, including two bugs that live run caught (relocation
    demanding all template fields; role journals with wave-id REFERENCES being
    mis-relocated before the filename check).
    """

    def setUp(self):
        self.ext = _load_upgrade_extensions()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.journals = self.root / "docs" / "agents" / "journals"
        self.journals.mkdir(parents=True)
        (self.root / "docs" / "waves").mkdir(parents=True)

    def tearDown(self):
        self.tmp.cleanup()

    def _run(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.ext._migrate_journals(self.root)
        return out.getvalue()

    def _write_pristine(self, wave_id, title, date):
        text = self.ext._pristine_journal_template(wave_id, title, date)
        name = f"{wave_id.replace(' ', '-')}.md"
        (self.journals / name).write_text(text, encoding="utf-8")
        return name, text

    def test_pristine_scaffold_is_deleted(self):
        self._write_pristine("1aaaa demo-wave", "demo-wave", "2026-01-05")
        report = self._run()
        self.assertEqual(list(self.journals.glob("*.md")), [])
        self.assertIn("deleted 1 pristine scaffold(s)", report)

    def test_one_content_line_prevents_deletion(self):
        name, text = self._write_pristine("1aaab demo-wave", "demo-wave", "2026-01-05")
        (self.journals / name).write_text(
            text.replace(
                "- Pending: distilled lessons emerge as the wave delivers",
                "- Operator ruled the retry budget stays at 3",
                1,
            ),
            encoding="utf-8",
        )
        report = self._run()
        # No wave dir exists, so the content-bearing journal is left+reported,
        # never deleted.
        self.assertTrue((self.journals / name).exists())
        self.assertIn(f"left {name} in place", report)

    def test_content_bearing_wave_journal_relocates_into_wave_dir(self):
        """Destination carries the lifecycle type suffix (wave 1t76w):
        `<prefix>-jrnl <slug>.md`, never the bare scaffold name."""

        wave_id = "1aaac demo-wave"
        name, text = self._write_pristine(wave_id, "demo-wave", "2026-01-05")
        edited = text + "\n- Real observation captured mid-wave.\n"
        (self.journals / name).write_text(edited, encoding="utf-8")
        (self.root / "docs" / "waves" / wave_id).mkdir()
        report = self._run()
        destination = self.root / "docs" / "waves" / wave_id / "1aaac-jrnl demo-wave.md"
        self.assertFalse((self.journals / name).exists())
        self.assertFalse(
            (self.root / "docs" / "waves" / wave_id / name).exists(),
            "relocation must not use the bare scaffold name",
        )
        self.assertEqual(destination.read_text(encoding="utf-8"), edited)
        self.assertIn("moved 1 wave journal(s)", report)
        self.assertIn(f"{name} -> docs/waves/{wave_id}/1aaac-jrnl demo-wave.md", report)

    def test_old_journal_without_template_fields_still_relocates(self):
        """Live-caught: relocation must need only the wave identity — older
        journals lack ``Last verified:``/title lines and must still move."""

        wave_id = "1aaad old-wave"
        name = f"{wave_id.replace(' ', '-')}.md"
        (self.journals / name).write_text(
            f"# Old journal\n\nwave-id: `{wave_id}`\n\n- Historical note.\n",
            encoding="utf-8",
        )
        (self.root / "docs" / "waves" / wave_id).mkdir()
        self._run()
        self.assertFalse((self.journals / name).exists())
        self.assertTrue(
            (self.root / "docs" / "waves" / wave_id / "1aaad-jrnl old-wave.md").exists()
        )

    def test_role_journal_referencing_wave_id_stays_in_place(self):
        """Live-caught: a ROLE journal that merely references a wave id must
        not be relocated into that wave's directory — only a journal whose
        filename equals its wave id is a wave journal."""

        wave_id = "1aaae other-wave"
        (self.root / "docs" / "waves" / wave_id).mkdir()
        (self.journals / "guru.md").write_text(
            "# Journal - guru\n\n"
            f"wave-id: `{wave_id}`\n\n"
            "- Durable role lesson referencing that wave.\n",
            encoding="utf-8",
        )
        report = self._run()
        self.assertTrue((self.journals / "guru.md").exists())
        self.assertEqual(
            list((self.root / "docs" / "waves" / wave_id).iterdir()), []
        )
        self.assertIn("left guru.md in place", report)

    def test_readme_untouched_and_rerun_is_silent_noop(self):
        (self.journals / "README.md").write_text(
            "# Journal contract\n", encoding="utf-8"
        )
        self._write_pristine("1aaaf demo-wave", "demo-wave", "2026-01-05")
        self._run()
        self.assertTrue((self.journals / "README.md").exists())
        report = self._run()
        self.assertEqual(report, "")

    def test_missing_journals_dir_is_noop(self):
        shutil.rmtree(self.journals)
        self.assertEqual(self._run(), "")

    def test_pre_docs_gate_version_gates_journal_migration(self):
        (self.root / ".wavefoundry").mkdir()
        (self.root / ".wavefoundry" / "upgrade-in-progress.json").write_text(
            '{"review_sidecar_cleanup": {}}\n', encoding="utf-8"
        )
        with patch.object(self.ext, "_migrate_memory_naming"), patch.object(
            self.ext, "_migrate_journals"
        ) as journals:
            self.ext.pre_docs_gate(MagicMock(root=self.root, from_version="1.14.0"))
        journals.assert_called_once_with(self.root)
        with patch.object(self.ext, "_migrate_memory_naming") as naming, patch.object(
            self.ext, "_migrate_journals"
        ) as journals:
            self.ext.pre_docs_gate(MagicMock(root=self.root, from_version="1.15.0"))
        naming.assert_not_called()
        journals.assert_not_called()


class PermissionsRenderConsentTests(unittest.TestCase):
    """Wave 1u2b0 (1u2az): the upgrade render passes the permissions switch and
    surfaces the rendered permissions delta as an explicit consent line."""

    def setUp(self):
        self.mod = load_upgrade_module()
        # load_upgrade_module builds a FRESH module object per setUp, so assigning
        # the delta global cannot bleed into a sibling test here. It CAN still
        # escape this class: load_upgrade_module also rebinds
        # sys.modules["upgrade_wavefoundry"], so a later plain
        # `import upgrade_wavefoundry` anywhere in the same process resolves the
        # polluted object (verified). Restore it explicitly.
        _prior_delta = self.mod._PERMISSIONS_DELTA
        self.addCleanup(setattr, self.mod, "_PERMISSIONS_DELTA", _prior_delta)
        if str(SCRIPTS_ROOT) not in sys.path:
            sys.path.insert(0, str(SCRIPTS_ROOT))
        import venv_bootstrap
        heal = patch.object(venv_bootstrap, "ensure_python_resolves", return_value="ok")
        heal.start()
        self.addCleanup(heal.stop)
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)
        # A stand-in renderer script so the phase does not skip.
        (self.root / "render_platform_surfaces.py").write_text("", encoding="utf-8")
        self.settings = self.root / ".claude" / "settings.json"
        self.settings.parent.mkdir(parents=True)
        self.settings.write_text(
            json.dumps({"permissions": {"allow": ["Bash(npm test:*)"]}}, indent=2) + "\n",
            encoding="utf-8",
        )

    def _run_phase(self, render_side_effect):
        lines: list[str] = []

        def fake_run(cmd, **kwargs):
            render_side_effect(cmd)
            return MagicMock(returncode=0)

        with patch.object(self.mod, "SCRIPTS_DIR", self.root), \
             patch.object(self.mod, "_log", side_effect=lines.append), \
             patch("subprocess.run", side_effect=fake_run) as run_mock:
            self.mod.phase_surface_rendering(self.root)
        return lines, run_mock

    def test_upgrade_render_passes_include_permissions_switch(self):
        captured: list[list[str]] = []
        lines, _ = self._run_phase(lambda cmd: captured.append(list(cmd)))
        self.assertEqual(len(captured), 1)
        self.assertIn("--include-permissions", captured[0])

    def test_permissions_delta_consent_line_names_added_rules(self):
        added_rule = "mcp__wavefoundry__code_search"

        def render(cmd):
            data = json.loads(self.settings.read_text(encoding="utf-8"))
            data["permissions"]["allow"].append(added_rule)
            self.settings.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

        lines, _ = self._run_phase(render)
        joined = "\n".join(lines)
        self.assertIn("Permissions delta", joined)
        self.assertIn(f"+ {added_rule}", joined)
        delta = self.mod._PERMISSIONS_DELTA
        self.assertTrue(delta)
        self.assertEqual(delta["added"], [added_rule])
        self.assertEqual(delta["removed"], [])

    def test_permissions_delta_reports_none_when_unchanged(self):
        lines, _ = self._run_phase(lambda cmd: None)
        joined = "\n".join(lines)
        self.assertIn("Permissions delta: none", joined)
        delta = self.mod._PERMISSIONS_DELTA
        self.assertIsNotNone(delta)
        self.assertEqual((delta["added"], delta["removed"]), ([], []))

    def test_phase_persists_the_delta_into_the_upgrade_lock(self):
        # F1 repair: the operator prose prints in the SEPARATE --cleanup process,
        # where the module global is None — so the rendering process must persist
        # the consent record for that process to adopt.
        lib = _load_upgrade_lib()
        lib.write_upgrade_lock(self.root, "1.14.0", "1.15.0")
        added_rule = "mcp__wavefoundry__code_search"

        def render(cmd):
            data = json.loads(self.settings.read_text(encoding="utf-8"))
            data["permissions"]["allow"].append(added_rule)
            self.settings.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

        self._run_phase(render)
        persisted = lib.read_upgrade_lock(self.root)["permissions_delta"]
        self.assertEqual(persisted["added"], [added_rule])
        self.assertEqual(persisted["file"], ".claude/settings.json")

    def test_summary_flattens_the_delta_into_lists_and_scalars(self):
        # F1 repair: the MCP response bounder treats a nested dict as ONE scalar
        # value and drops it whole past the per-value char cap, which the
        # write-tier delta exceeds. Lists + scalars are paged instead.
        self.mod._PERMISSIONS_DELTA = {
            "file": ".claude/settings.json",
            "added": ["mcp__wavefoundry__code_search"],
            "removed": ["mcp__wavefoundry__wave_close"],
            "unmanaged_present": 3,
        }
        summary = self._summary(renderer_provenance_flags=[{"file": ".claude/settings.json"}])
        self.assertNotIn(
            "permissions_delta",
            summary,
            "the nested dict key must be gone, not merely supplemented",
        )
        self.assertEqual(summary["permissions_added"], ["mcp__wavefoundry__code_search"])
        self.assertEqual(summary["permissions_removed"], ["mcp__wavefoundry__wave_close"])
        self.assertEqual(summary["permissions_changed"], 2)
        self.assertEqual(summary["permissions_file"], ".claude/settings.json")
        self.assertEqual(summary["permissions_unmanaged_present"], 3)
        self.assertEqual(summary["renderer_provenance_flags"], [{"file": ".claude/settings.json"}])
        # Every emitted permissions field is a scalar or a list of strings — never
        # a dict (the shape the bounder drops).
        for key, value in summary.items():
            if key.startswith("permissions_"):
                self.assertNotIsInstance(value, dict, key)

    def test_summary_changed_count_is_zero_when_render_changed_nothing(self):
        self.mod._PERMISSIONS_DELTA = {
            "file": ".claude/settings.json",
            "added": [],
            "removed": [],
            "unmanaged_present": 0,
        }
        summary = self._summary()
        self.assertEqual(summary["permissions_changed"], 0)
        self.assertEqual(summary["permissions_added"], [])

    def test_summary_changed_is_none_when_no_render_ran_in_this_upgrade(self):
        # Preserves the pre-repair `delta is not None` semantics: no permissions
        # render for this upgrade means NO consent claim at all (distinct from a
        # render that changed nothing).
        self.mod._PERMISSIONS_DELTA = None
        summary = self._summary()
        self.assertIsNone(summary["permissions_changed"])
        self.assertIsNone(summary["permissions_file"])
        self.assertEqual(summary["permissions_added"], [])
        lines: list[str] = []
        with patch.object(self.mod, "_log", side_effect=lines.append):
            self.mod._print_operator_summary(
                from_version="1.15.0",
                to_version="1.16.0",
                zip_path=None,
                pruned_count=0,
                ran_index_rebuild=True,
                failed_phase=None,
                root=None,
            )
        self.assertNotIn("Permissions:", "\n".join(str(x) for x in lines))

    def _summary(self, **overrides):
        kwargs = dict(
            from_version="1.15.0",
            to_version="1.16.0",
            zip_path=None,
            pruned_count=0,
            ran_index_rebuild=True,
            failed_phase=None,
            reconciliation=[],
            host_permission_flags=[],
        )
        kwargs.update(overrides)
        return self.mod._build_upgrade_summary(**kwargs)

    def test_operator_summary_names_unmanaged_present_rules(self):
        # F8 repair: the merge deliberately never claims a desired rule that is
        # already present; without this line the operator sees only
        # "Permissions: unchanged" and cannot tell the feature is inert.
        self.mod._PERMISSIONS_DELTA = {
            "file": ".claude/settings.json",
            "added": [],
            "removed": [],
            "unmanaged_present": 41,
        }
        lines: list[str] = []
        with patch.object(self.mod, "_log", side_effect=lines.append):
            self.mod._print_operator_summary(
                from_version="1.15.0",
                to_version="1.16.0",
                zip_path=None,
                pruned_count=0,
                ran_index_rebuild=True,
                failed_phase=None,
                root=None,
            )
        joined = "\n".join(str(x) for x in lines)
        self.assertIn("41 roster-desired rule(s)", joined)
        self.assertIn("UNMANAGED", joined)
        # And the count is genuinely computed from the real merge state.
        self.settings.write_text(
            json.dumps(
                {
                    "permissions": {
                        "allow": [
                            "mcp__wavefoundry__code_search",
                            "mcp__wavefoundry__docs_search",
                            "Bash(npm test:*)",
                        ]
                    }
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        self.assertEqual(self.mod._permissions_unmanaged_present(self.root), 2)
        # Claimed rules are NOT unmanaged (the near-miss control).
        self.settings.write_text(
            json.dumps(
                {
                    "permissions": {"allow": ["mcp__wavefoundry__code_search"]},
                    "wavefoundryManagedAllow": ["mcp__wavefoundry__code_search"],
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        self.assertEqual(self.mod._permissions_unmanaged_present(self.root), 0)

    def test_operator_summary_prints_explicit_permissions_consent_line(self):
        self.mod._PERMISSIONS_DELTA = {
            "file": ".claude/settings.json",
            "added": ["mcp__wavefoundry__code_search"],
            "removed": ["mcp__wavefoundry__wave_close"],
            "unmanaged_present": 0,
        }
        lines: list[str] = []
        with patch.object(self.mod, "_log", side_effect=lines.append):
            self.mod._print_operator_summary(
                from_version="1.15.0",
                to_version="1.16.0",
                zip_path=None,
                pruned_count=0,
                ran_index_rebuild=True,
                failed_phase=None,
                root=None,
            )
        joined = "\n".join(str(x) for x in lines)
        self.assertIn("Permissions:", joined)
        self.assertIn("CHANGED", joined)
        self.assertIn("+ mcp__wavefoundry__code_search", joined)
        self.assertIn("- mcp__wavefoundry__wave_close", joined)
        # Not folded into the generic surfaces-rendered line.
        surfaces_line = next(l for l in lines if str(l).startswith("Surfaces rendered:"))
        self.assertNotIn("permission", str(surfaces_line).lower())


class EditingPassStepsAreCurrentTests(unittest.TestCase):
    """1v4mv AC-1: the editing-pass output must not instruct a retired step.

    It shipped through 1.16.1 telling every operator to run "Journal
    reconciliation (seed-160 step 0 / Reconcile journals)", which was wrong
    twice: the journal system is retired per seed-120 and seed-160, and
    seed-160's step 0 is pack adoption, not journal work.
    """

    def setUp(self):
        self.mod = load_upgrade_module()

    def _steps(self) -> list[str]:
        lines: list[str] = []
        with patch.object(self.mod, "_log", side_effect=lines.append):
            self.mod._print_operator_summary(
                from_version="1.16.1",
                to_version="1.16.2",
                zip_path=None,
                pruned_count=0,
                ran_index_rebuild=True,
                failed_phase=None,
                root=None,
            )
        return [str(line) for line in lines]

    def test_editing_pass_does_not_instruct_the_retired_journal_step(self):
        joined = "\n".join(self._steps())
        # Non-vacuous: the block itself must still be emitted, or the absence
        # assertion below would pass on an empty output.
        self.assertIn("Next steps for agent editing pass:", joined)
        self.assertNotIn("Journal reconciliation", joined)
        self.assertNotIn("Reconcile journals", joined)

    def test_editing_pass_steps_are_contiguously_numbered(self):
        """Removing a step must renumber, not leave a gap."""
        numbers = [
            int(match.group(1))
            for line in self._steps()
            if (match := re.match(r"\s+(\d+)\.\s", line))
        ]
        self.assertTrue(numbers, "no numbered steps found")
        self.assertEqual(numbers, list(range(1, len(numbers) + 1)), numbers)


class RendererWarningsReachTheSummaryTests(unittest.TestCase):
    """1v4mt AC-4: the renderer's warn-and-skip finding must appear in the
    structured summary, not on stderr alone.

    The field signal was invisible for exactly that reason: one stderr line
    among roughly 90 gardener lines, absent from `data.summary`, with
    `failed_phase: null`. Four reviewer role docs then silently received no
    protocol updates across releases 1.13.0 through 1.16.1.
    """

    def setUp(self):
        self.mod = load_upgrade_module()
        self.root = Path(tempfile.mkdtemp(prefix="renderer-warnings-"))
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)

    def _carrier_with_half_paired_markers(self) -> str:
        import render_agent_surfaces as ras

        carrier = next(iter(ras.review_protocol_carriers(self.root)))
        path = self.root / carrier.destination
        path.parent.mkdir(parents=True, exist_ok=True)
        rendered = ras._upsert_review_protocol_region(
            "# Role doc\n\nProse.\n", ras._carrier_protocol_block(carrier)
        )
        path.write_text(
            rendered.replace(ras.REVIEW_PROTOCOL_MARKER_BEGIN, "", 1), encoding="utf-8"
        )
        return carrier.destination

    def test_summary_carries_the_warning_on_an_otherwise_successful_run(self):
        destination = self._carrier_with_half_paired_markers()
        lines: list[str] = []
        with patch.object(self.mod, "_log", side_effect=lines.append):
            self.mod._print_operator_summary(
                from_version="1.16.1",
                to_version="1.16.2",
                zip_path=None,
                pruned_count=0,
                ran_index_rebuild=True,
                # The precise field shape: the run reports success.
                failed_phase=None,
                root=self.root,
            )
        joined = "\n".join(str(item) for item in lines)
        sentinel = next(
            line for line in lines if str(line).startswith(self.mod.WAVE_UPGRADE_SUMMARY_SENTINEL)
        )
        summary = json.loads(str(sentinel)[len(self.mod.WAVE_UPGRADE_SUMMARY_SENTINEL):])
        self.assertTrue(summary["renderer_warnings"], summary)
        self.assertIn(
            destination,
            json.dumps(summary["renderer_warnings"]),
            "the machine-readable field must name the skipped carrier",
        )
        self.assertIsNone(summary["failed_phase"])
        # And the operator prose says it, distinguishing it from the
        # self-healing renderer_provenance_flags class right above it.
        self.assertIn("Renderer warnings", joined)
        self.assertIn(destination, joined)
        self.assertIn("do NOT self-heal", joined)

    def test_warning_still_emitted_on_a_failed_phase(self):
        """Review finding: the code deliberately scans OUTSIDE the
        `not failed_phase` guard and outside the major/minor gate that wraps the
        reconciliation prose, and that claim was recorded in the Decision Log
        but never asserted. A malformed marker pair is what a half-finished
        render leaves behind, so the failed-phase run is the one most likely to
        produce this finding."""
        destination = self._carrier_with_half_paired_markers()
        lines: list[str] = []
        with patch.object(self.mod, "_log", side_effect=lines.append):
            self.mod._print_operator_summary(
                from_version="1.16.1",
                to_version="1.16.2",
                zip_path=None,
                pruned_count=0,
                ran_index_rebuild=False,
                failed_phase="docs_gate",
                root=self.root,
            )
        joined = "\n".join(str(item) for item in lines)
        sentinel = next(
            line
            for line in lines
            if str(line).startswith(self.mod.WAVE_UPGRADE_SUMMARY_SENTINEL)
        )
        summary = json.loads(
            str(sentinel)[len(self.mod.WAVE_UPGRADE_SUMMARY_SENTINEL):]
        )
        self.assertEqual(summary["failed_phase"], "docs_gate")
        self.assertTrue(summary["renderer_warnings"], summary)
        self.assertIn(destination, json.dumps(summary["renderer_warnings"]))
        self.assertIn("Renderer warnings", joined)
        # Polarity: the reconciliation prose IS suppressed on a failed phase, so
        # this is not passing merely because everything prints.
        self.assertNotIn("Retired-surface", joined)

    def test_healthy_tree_reports_no_renderer_warnings(self):
        # Non-vacuous: an empty tree would pass by having no carriers at all.
        # Render a WELL-FORMED region, then assert silence.
        import render_agent_surfaces as ras

        carrier = next(iter(ras.review_protocol_carriers(self.root)))
        path = self.root / carrier.destination
        path.parent.mkdir(parents=True, exist_ok=True)
        rendered = ras._upsert_review_protocol_region(
            "# Role doc\n\nProse.\n", ras._carrier_protocol_block(carrier)
        )
        path.write_text(rendered, encoding="utf-8")
        self.assertIn(ras.REVIEW_PROTOCOL_MARKER_BEGIN, rendered)
        lines: list[str] = []
        with patch.object(self.mod, "_log", side_effect=lines.append):
            self.mod._print_operator_summary(
                from_version="1.16.1",
                to_version="1.16.2",
                zip_path=None,
                pruned_count=0,
                ran_index_rebuild=True,
                failed_phase=None,
                root=self.root,
            )
        sentinel = next(
            line for line in lines if str(line).startswith(self.mod.WAVE_UPGRADE_SUMMARY_SENTINEL)
        )
        summary = json.loads(str(sentinel)[len(self.mod.WAVE_UPGRADE_SUMMARY_SENTINEL):])
        self.assertEqual(summary["renderer_warnings"], [])
        self.assertNotIn("Renderer warnings", "\n".join(str(x) for x in lines))


class PermissionsConsentCrossesTheProcessBoundaryTests(unittest.TestCase):
    """Wave 1u2b0 F1 repair: the human consent prose prints from the SEPARATE
    `--cleanup` process, whose module global is None. The rendering process
    persists the delta into the upgrade lock and cleanup adopts it."""

    def setUp(self):
        self.mod = load_upgrade_module()
        self.lib = _load_upgrade_lib()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / ".wavefoundry").mkdir()
        self.addCleanup(self.tmp.cleanup)

    def _cleanup_output(self) -> str:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.mod.phase_cleanup(
                root=self.root,
                from_version="1.14.0",
                to_version="1.15.0",
                zip_path=None,
                pruned_count=0,
                ran_index_rebuild=True,
                failed_phase=None,
                lock_present=True,
            )
        return buf.getvalue()

    def test_cleanup_prints_the_persisted_consent_delta(self):
        self.lib.write_upgrade_lock(self.root, "1.14.0", "1.15.0")
        self.lib.update_upgrade_lock(
            self.root,
            permissions_delta={
                "file": ".claude/settings.json",
                "added": ["mcp__wavefoundry__code_search"],
                "removed": ["mcp__wavefoundry__wave_close"],
                "unmanaged_present": 0,
            },
        )
        # The real cross-process condition: this process never rendered.
        self.assertIsNone(self.mod._PERMISSIONS_DELTA)
        out = self._cleanup_output()
        self.assertIn("Permissions:", out)
        self.assertIn("CHANGED", out)
        self.assertIn("+ mcp__wavefoundry__code_search", out)
        self.assertIn("- mcp__wavefoundry__wave_close", out)

    def test_cleanup_makes_no_consent_claim_without_a_persisted_delta(self):
        # Non-vacuity control (and the pre-repair behaviour): with nothing
        # persisted there is no consent line at all, rather than a false
        # "unchanged" claim about a render this upgrade never made.
        self.lib.write_upgrade_lock(self.root, "1.14.0", "1.15.0")
        out = self._cleanup_output()
        self.assertIn("Upgrade complete", out)
        self.assertNotIn("Permissions:", out)

    def test_non_dict_persisted_delta_degrades_to_no_claim(self):
        self.lib.write_upgrade_lock(self.root, "1.14.0", "1.15.0")
        self.lib.update_upgrade_lock(self.root, permissions_delta="corrupt")
        out = self._cleanup_output()
        self.assertIn("Upgrade complete", out)
        self.assertNotIn("Permissions:", out)


class PermissionsRenderBackstopTests(unittest.TestCase):
    """Wave 1u2b0 F5 repair: the upgrade that INSTALLS the permission surface runs
    Phase 1 on the already-imported OLD orchestrator (no --include-permissions), so
    a NEW-code backstop in the `--update-index` subprocess renders it instead."""

    def setUp(self):
        self.mod = load_upgrade_module()
        _prior_delta = self.mod._PERMISSIONS_DELTA
        self.addCleanup(setattr, self.mod, "_PERMISSIONS_DELTA", _prior_delta)
        if str(SCRIPTS_ROOT) not in sys.path:
            sys.path.insert(0, str(SCRIPTS_ROOT))
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)
        self.settings = self.root / ".claude" / "settings.json"

    @staticmethod
    def _main_guard_chains(callee: str) -> list[frozenset[str]]:
        """Every call site of *callee* in main(), as the set of `args.<flag>` names
        guarding it. An empty set means the call is on the unguarded default path."""
        import ast as _ast

        source = UPGRADE_PATH.read_text(encoding="utf-8")
        main_fn = next(
            node for node in _ast.parse(source).body
            if isinstance(node, _ast.FunctionDef) and node.name == "main"
        )
        chains: list[frozenset[str]] = []

        def walk(node, guards: frozenset[str]) -> None:
            if isinstance(node, _ast.Call) and isinstance(node.func, _ast.Name):
                if node.func.id == callee:
                    chains.append(guards)
            if isinstance(node, _ast.If):
                extra: set[str] = set()
                for sub in _ast.walk(node.test):
                    if isinstance(sub, _ast.Attribute) and isinstance(sub.value, _ast.Name):
                        if sub.value.id == "args":
                            extra.add(sub.attr)
                for child in node.body:
                    walk(child, guards | extra)
                for child in node.orelse:
                    walk(child, guards)
                return
            for child in _ast.iter_child_nodes(node):
                walk(child, guards)

        for stmt in main_fn.body:
            walk(stmt, frozenset())
        return chains

    def test_update_index_phase_calls_the_backstop(self):
        # Source-level pin on the new-code place every MCP upgrade flow that runs the
        # --update-index subprocess reaches post-extract, alongside the two established
        # backstops. This is NOT the only site: an ordinary upgrade never runs
        # --update-index, which is what
        # test_default_upgrade_path_reaches_the_backstop covers.
        import ast as _ast

        source = UPGRADE_PATH.read_text(encoding="utf-8")
        main_fn = next(
            node for node in _ast.parse(source).body
            if isinstance(node, _ast.FunctionDef) and node.name == "main"
        )
        branch = None
        for node in _ast.walk(main_fn):
            if (
                isinstance(node, _ast.If)
                and isinstance(node.test, _ast.Attribute)
                and node.test.attr == "update_index"
            ):
                branch = node
                break
        self.assertIsNotNone(branch, "main() must have an `if args.update_index:` branch")
        called = {
            inner.func.id
            for inner in _ast.walk(branch)
            if isinstance(inner, _ast.Call) and isinstance(inner.func, _ast.Name)
        }
        self.assertIn("_ensure_rendered_permissions_backstop", called)
        # Positive control: the established new-code backstops live in the same branch.
        self.assertIn("_ensure_lifecycle_policy_backstop", called)

    def test_default_upgrade_path_reaches_the_backstop(self):
        """Wave 1u2b0 F5 re-repair: DEFAULT-PATH reachability, which the update_index
        pin above cannot establish.

        Known bad this pins: the backstop had exactly one call site, guarded by
        `args.update_index`, a flag an ordinary `wf upgrade` never passes (its primary
        phase renders surfaces and runs Phase 4 inline, then exits). Four shipped
        surfaces claim an ordinary upgrade renders the block during that same upgrade,
        so a backstop only the --update-index subprocess reaches makes them false.
        """
        chains = self._main_guard_chains("_ensure_rendered_permissions_backstop")
        self.assertTrue(chains, "main() must call _ensure_rendered_permissions_backstop")
        self.assertTrue(
            any("update_index" not in guards for guards in chains),
            "every backstop call site is behind args.update_index, which an ordinary "
            f"upgrade never passes; guard chains: {[sorted(g) for g in chains]}",
        )
        # The default-path site is the cleanup phase, mirroring the two-site shape of the
        # established lifecycle backstop (whose second site lives inside phase_cleanup,
        # which main() calls only from the same `if args.cleanup:` branch).
        self.assertTrue(
            any(
                "cleanup" in guards and "update_index" not in guards
                for guards in chains
            ),
            f"expected a call site on the cleanup path; got {[sorted(g) for g in chains]}",
        )
        self.assertEqual(
            [sorted(g) for g in self._main_guard_chains("phase_cleanup")],
            [["cleanup"]],
            "phase_cleanup is reached only from the cleanup branch, so a backstop there "
            "is on the same path the lifecycle-policy precedent uses",
        )

    def test_cleanup_invocation_really_renders_the_block(self):
        """Behavioural counterpart to the static pin: drive main() with `--cleanup` on a
        repo whose settings carry no permission block, and require the block to exist
        afterwards. phase_cleanup itself is patched out so this isolates the backstop."""
        import memory_backfill

        lib = _load_upgrade_lib()
        (self.root / ".wavefoundry" / "index").mkdir(parents=True, exist_ok=True)
        (self.root / "docs" / "waves").mkdir(parents=True, exist_ok=True)
        run_id = memory_backfill.ensure_run(self.root, "upgrade")
        memory_backfill.sync_inventory(self.root, run_id)
        memory_backfill.mark_indexed(self.root, run_id)
        lib.write_upgrade_lock(self.root, "1.14.0", "1.15.0")
        lib.update_upgrade_lock(
            self.root,
            memory_backfill_run_id=run_id,
            memory_backfill_state="indexed",
        )
        with patch.object(self.mod, "phase_cleanup") as cleanup, \
             patch.object(self.mod, "_open_log"), patch.object(self.mod, "_close_log"), \
             patch.object(self.mod, "_log"):
            result = self.mod.main(["--root", str(self.root), "--cleanup"])
        self.assertEqual(result, 0)
        cleanup.assert_called_once()
        self.assertTrue(self.settings.is_file(), "the cleanup phase must render the block")
        data = json.loads(self.settings.read_text(encoding="utf-8"))
        self.assertIn("mcp__wavefoundry__code_search", data["permissions"]["allow"])
        # The delta is persisted BEFORE the lock is removed, so the operator consent line
        # in the cleanup summary can still adopt it.
        persisted = lib.read_upgrade_lock(self.root)["permissions_delta"]
        self.assertIn("mcp__wavefoundry__code_search", persisted["added"])

    def test_cleanup_without_an_upgrade_lock_renders_nothing(self):
        """Non-vacuity control for the gate on the new site: with no upgrade in flight,
        cleanup warns and returns, and the backstop must not silently mutate a committed
        operator file outside an upgrade."""
        (self.root / ".wavefoundry").mkdir(parents=True, exist_ok=True)
        with patch.object(self.mod, "_open_log"), patch.object(self.mod, "_close_log"), \
             patch.object(self.mod, "_log"):
            result = self.mod.main(["--root", str(self.root), "--cleanup"])
        self.assertEqual(result, 0)
        self.assertFalse(
            self.settings.exists(),
            "no upgrade lock means no upgrade to back stop; nothing may be rendered",
        )

    def test_backstop_argv_is_permissions_only_and_gated_on_the_one_switch(self):
        captured: list[list[str]] = []

        def fake_run(cmd, **kwargs):
            captured.append(list(cmd))
            return MagicMock(returncode=0)

        with patch("subprocess.run", side_effect=fake_run), \
             patch.object(self.mod, "_log"):
            self.mod._ensure_rendered_permissions_backstop(self.root)
        self.assertEqual(len(captured), 1)
        self.assertIn("--include-permissions", captured[0])
        self.assertIn("--permissions-only", captured[0])

    def test_backstop_renders_the_block_then_is_idempotent(self):
        # Executes the REAL renderer subprocess: the backstop must produce the
        # permission block on a repo that has none, and be a no-op afterwards.
        lines: list[str] = []
        with patch.object(self.mod, "_log", side_effect=lines.append):
            self.mod._ensure_rendered_permissions_backstop(self.root)
        self.assertTrue(self.settings.is_file(), "\n".join(str(x) for x in lines))
        first = self.settings.read_bytes()
        data = json.loads(first.decode("utf-8"))
        self.assertIn("mcp__wavefoundry__code_search", data["permissions"]["allow"])
        self.assertTrue(data["wavefoundryManagedAllow"])
        delta = self.mod._PERMISSIONS_DELTA
        self.assertIn("mcp__wavefoundry__code_search", delta["added"])
        self.assertEqual(delta["removed"], [])
        # Permissions ONLY: no other surface was rendered by this pass.
        self.assertFalse((self.root / ".mcp.json").exists())
        self.assertFalse((self.root / ".claude" / "hooks").exists())
        self.assertFalse((self.root / ".wavefoundry" / "bin").exists())
        # Idempotent: byte-stable, and the second pass claims no delta.
        with patch.object(self.mod, "_log", side_effect=lines.append):
            self.mod._ensure_rendered_permissions_backstop(self.root)
        self.assertEqual(self.settings.read_bytes(), first)
        repeat = self.mod._PERMISSIONS_DELTA
        self.assertEqual((repeat["added"], repeat["removed"]), ([], []))

    def test_backstop_never_launders_an_earlier_render_record(self):
        # A new-code Phase 1 render already recorded the real delta; the
        # backstop's own no-op pass must not overwrite it with "unchanged".
        lib = _load_upgrade_lib()
        lib.write_upgrade_lock(self.root, "1.14.0", "1.15.0")
        recorded = {
            "file": ".claude/settings.json",
            "added": ["mcp__wavefoundry__code_search"],
            "removed": [],
            "unmanaged_present": 0,
        }
        lib.update_upgrade_lock(self.root, permissions_delta=recorded)
        with patch("subprocess.run", return_value=MagicMock(returncode=0)), \
             patch.object(self.mod, "_log"):
            self.mod._ensure_rendered_permissions_backstop(self.root)
        self.assertEqual(
            lib.read_upgrade_lock(self.root)["permissions_delta"], recorded
        )

    def test_backstop_records_its_own_delta_when_nothing_was_recorded(self):
        lib = _load_upgrade_lib()
        lib.write_upgrade_lock(self.root, "1.14.0", "1.15.0")
        with patch.object(self.mod, "_log"):
            self.mod._ensure_rendered_permissions_backstop(self.root)
        persisted = lib.read_upgrade_lock(self.root)["permissions_delta"]
        self.assertIn("mcp__wavefoundry__code_search", persisted["added"])

    def test_backstop_is_fail_safe_when_the_render_fails(self):
        with patch("subprocess.run", return_value=MagicMock(returncode=3)), \
             patch.object(self.mod, "_log") as log:
            self.mod._ensure_rendered_permissions_backstop(self.root)
        self.assertTrue(
            any("backstop" in str(call.args[0]) for call in log.call_args_list)
        )


if __name__ == "__main__":
    unittest.main()


class ScaffoldRepairIsClassATests(unittest.TestCase):
    """The scaffold rule is class-a; its repair must be too.

    `phase_docs_gate` subprocesses the freshly extracted `docs_lint.py`, so the
    new ERROR fires on the very upgrade that installs it. A repository whose
    template already declares would therefore halt at
    `failed_phase == "docs_gate"` — precisely the population the rule exists to
    protect. The repair runs from the pack-loaded `pre_docs_gate` extension so
    it clears on the same run, and separately from the resume path, which
    builds no extension module and is the only path a stranded repository can
    travel.
    """

    CONTAMINATED = (
        "# [Change Title]\n\n## Serialization Points\n\n"
        "**Review targets (repo-relative paths):**\n\n"
        "- `path/to/file.swift`\n"
        "- `docs/specs/`\n\n"
        "## Affected Architecture Docs\n"
    )

    def setUp(self):
        self.ext = _load_upgrade_extensions()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "docs" / "plans").mkdir(parents=True)
        self.template = self.root / "docs" / "plans" / "plan-template.md"
        sys.path.insert(0, str(SCRIPTS_ROOT))
        self.ctx = MagicMock(root=self.root)

    def _declared(self):
        import review_policy

        return review_policy.serialization_point_paths(
            self.template.read_text(encoding="utf-8")
        )

    def test_a_contaminated_template_is_repaired_before_the_gate(self):
        self.template.write_text(self.CONTAMINATED, encoding="utf-8")
        self.assertEqual(
            self._declared(), ("path/to/file.swift", "docs/specs/"),
            "fixture must start contaminated, or the test proves nothing",
        )
        repaired = self.ext.repair_declaring_scaffold(self.root)
        self.assertEqual(repaired, ["docs/plans/plan-template.md"])
        self.assertEqual(
            self._declared(), (),
            "after repair the scaffold must declare nothing",
        )

    def test_the_repair_preserves_the_example_text(self):
        """Fencing, not deleting: the author still sees how to declare."""

        self.template.write_text(self.CONTAMINATED, encoding="utf-8")
        self.ext.repair_declaring_scaffold(self.root)
        after = self.template.read_text(encoding="utf-8")
        self.assertIn("path/to/file.swift", after, "example text is retained")
        self.assertIn("**Review targets (repo-relative paths):**", after)
        self.assertIn("```", after, "the block is fenced")

    def test_a_clean_template_is_left_byte_identical(self):
        clean = (
            "# [Change Title]\n\n## Serialization Points\n\n"
            "```\n**Review targets (repo-relative paths):**\n\n"
            "- `path/to/file.swift`\n```\n\n## Affected Architecture Docs\n"
        )
        self.template.write_text(clean, encoding="utf-8")
        before = self.template.read_bytes()
        self.assertEqual(self.ext.repair_declaring_scaffold(self.root), [])
        self.assertEqual(self.template.read_bytes(), before)

    def test_pre_docs_gate_runs_the_repair_for_an_old_runner(self):
        """The class-a seam: an OLD orchestrator still gets the NEW repair.

        `pre_docs_gate` is dispatched from the module the orchestrator exec'd
        out of the pack, so this is the hook an old in-process runner reaches.
        """

        self.template.write_text(self.CONTAMINATED, encoding="utf-8")
        self.ctx.from_version = "1.15.5"
        self.ctx.runner_protocol = 2
        with patch.object(self.ext, "_installed_memory_backfill", return_value=None):
            try:
                self.ext.pre_docs_gate(self.ctx)
            except Exception:
                # Other hook steps may need fixtures this test does not build;
                # the repair runs first, so its effect is already observable.
                pass
        self.assertEqual(
            self._declared(), (),
            "pre_docs_gate must clear the scaffold before the gate runs",
        )

    def test_the_resume_path_reaches_the_repair(self):
        """Resume builds no ext_mod and has no zip, so it needs its own call.

        It is also the only path a repository that already halted can travel,
        so without this the scaffold rule would strand it permanently.
        """

        import upgrade_wavefoundry

        self.template.write_text(self.CONTAMINATED, encoding="utf-8")
        repaired = upgrade_wavefoundry._repair_declaring_scaffold_on_resume(self.root)
        self.assertEqual(repaired, ["docs/plans/plan-template.md"])
        self.assertEqual(self._declared(), ())

    def test_a_tier_one_pure_path_bullet_is_repaired_too(self):
        """The shape seed 040 literally hands a bootstrap agent.

        A marker-only repair would leave a freshly installed template halted at
        the docs gate with nothing to do but hand-edit, because seed 040's own
        example is a tier-1 bullet with no marker at all.
        """

        self.template.write_text(
            "# T\n\n## Serialization Points\n\n"
            "- `src/app/handler.py`, `docs/specs/`\n\n"
            "## Affected Architecture Docs\n",
            encoding="utf-8",
        )
        self.assertEqual(
            self._declared(), ("src/app/handler.py", "docs/specs/"),
            "fixture must start contaminated",
        )
        self.assertEqual(
            self.ext.repair_declaring_scaffold(self.root),
            ["docs/plans/plan-template.md"],
        )
        self.assertEqual(self._declared(), ())

    def test_instructional_prose_bullets_are_left_alone(self):
        """Only runs that DECLARE are fenced, decided by the parser."""

        prose = (
            "# T\n\n## Serialization Points\n\n"
            "- Serialize edits through the runner workstream.\n"
            "- Coordinate with the release lane.\n\n"
            "- `src/app/handler.py`\n\n## Next\n"
        )
        self.template.write_text(prose, encoding="utf-8")
        self.ext.repair_declaring_scaffold(self.root)
        after = self.template.read_text(encoding="utf-8")
        self.assertIn("- Serialize edits through the runner workstream.", after)
        self.assertNotIn(
            "```\n- Serialize edits", after,
            "an instructional bullet run must not be fenced",
        )
        self.assertEqual(self._declared(), ())

    def test_a_stray_bullet_beside_a_fenced_example_is_repaired_not_refused(self):
        """This shape used to halt the upgrade; it must now repair.

        A fenced marker example with a stray declaring bullet outside it is
        what an operator produces with one ordinary edit to the shipped
        template. The fencer used to be fence-blind, so it re-fenced the
        already-fenced example, flipped fence parity, still declared, and got
        refused by the post-fence re-check — leaving the operator stuck at the
        docs gate with the hand-edit the repair exists to avoid.
        """

        odd = (
            "# T\n\n## Serialization Points\n\n"
            "```\n**Review targets (repo-relative paths):**\n\n"
            "- `a/b.md`\n```\n\n"
            "- `src/app/handler.py`\n\n## Next\n"
        )
        self.template.write_text(odd, encoding="utf-8")
        self.assertEqual(
            self.ext.repair_declaring_scaffold(self.root),
            ["docs/plans/plan-template.md"],
        )
        self.assertEqual(self._declared(), ())
        after = self.template.read_text(encoding="utf-8")
        self.assertEqual(
            after.count("```"), 4, "the pre-existing fence must survive intact"
        )
        self.assertIn("- `a/b.md`", after, "the example content is preserved")

    def test_a_heading_inside_a_fenced_example_does_not_truncate_the_section(self):
        """`section_end` is fence-aware too, not just `section_start`.

        A "## " line inside a fenced example is sample text. Treating it as
        the next heading ends the section early, so a real declaring run past
        that false boundary is never fenced and the document still declares.
        """

        self.template.write_text(
            "# T\n\n## Serialization Points\n\n- `src/one.py`\n\n"
            "```\n## Next\n```\n\n- `src/two.py`\n\n## Real\n",
            encoding="utf-8",
        )
        self.assertEqual(self._declared(), ("src/one.py", "src/two.py"))
        self.assertEqual(
            self.ext.repair_declaring_scaffold(self.root),
            ["docs/plans/plan-template.md"],
        )
        self.assertEqual(self._declared(), ())

    def test_the_fence_tracker_agrees_with_the_shipped_parser(self):
        """The repair's fence tracking must match the parser it defers to.

        Every fence spelling the parser honors must also be honored here; a
        divergence means the repair either re-fences a safe example or skips a
        declaring one. Each variant carries a real declaring bullet, so a
        tracker that mishandles the fence fails to reach `()`.
        """

        variants = {
            "tilde": "~~~\n- `src/ex.py`\n~~~",
            "info string": "```markdown\n- `src/ex.py`\n```",
            "four backticks": "````\n```\n````",
            "indented": "    ```\n    - `src/ex.py`\n    ```",
            "unterminated": "```\nopened never closed",
        }
        for name, block in variants.items():
            with self.subTest(fence=name):
                self.template.write_text(
                    "# T\n\n## Serialization Points\n\n- `src/one.py`\n\n"
                    f"{block}\n\n## Next\n",
                    encoding="utf-8",
                )
                self.assertEqual(self._declared(), ("src/one.py",))
                self.assertEqual(
                    self.ext.repair_declaring_scaffold(self.root),
                    ["docs/plans/plan-template.md"],
                )
                self.assertEqual(self._declared(), ())
                self.assertIn(
                    block, self.template.read_text(encoding="utf-8"),
                    "the fenced block must come through byte-identical; "
                    "an unrecognized fence gets a nested fence spliced INTO it",
                )

    def test_a_fenced_section_heading_is_not_mistaken_for_the_section(self):
        """`section_start` is fence-aware: a documented example is not the section.

        A template that shows what a Serialization Points section looks like
        carries the heading inside a fence. Anchoring on it makes the repair
        scan the wrong region, find nothing to fence, and refuse — halting the
        upgrade on a document it could have repaired.
        """

        self.template.write_text(
            "# T\n\n## How to write one\n\n"
            "```\n## Serialization Points\n\n- `docs/example.md`\n```\n\n"
            "## Serialization Points\n\n- `src/real.py`\n\n## Next\n",
            encoding="utf-8",
        )
        self.assertEqual(self._declared(), ("src/real.py",))
        self.assertEqual(
            self.ext.repair_declaring_scaffold(self.root),
            ["docs/plans/plan-template.md"],
        )
        self.assertEqual(self._declared(), ())

    def test_the_marker_is_fenced_together_with_its_own_bullets(self):
        """The marker and the bullets beneath it are ONE construct.

        Fencing only the bullets clears the declaration but strands the
        `**Review targets…**` marker outside the example, so the template then
        shows a live-looking marker with nothing under it — and the next
        author to add a bullet there silently re-declares.
        """

        self.template.write_text(
            "# T\n\n## Serialization Points\n\n"
            "**Review targets (repo-relative paths):**\n\n"
            "- `src/one.py`\n\n## Next\n",
            encoding="utf-8",
        )
        self.assertEqual(
            self.ext.repair_declaring_scaffold(self.root),
            ["docs/plans/plan-template.md"],
        )
        self.assertEqual(self._declared(), ())
        body = self.template.read_text(encoding="utf-8")
        opening = body.index("```")
        self.assertLess(
            opening, body.index("**Review targets"),
            "the marker must sit INSIDE the fence, not above it",
        )

    def test_the_repair_preserves_the_file_s_line_endings(self):
        """A CRLF checkout must not come back as a whole-file LF diff."""

        crlf = self.CONTAMINATED.replace("\n", "\r\n")
        self.template.write_bytes(crlf.encode("utf-8"))
        self.ext.repair_declaring_scaffold(self.root)
        raw = self.template.read_bytes()
        self.assertGreater(raw.count(b"\r\n"), 0)
        self.assertEqual(
            raw.count(b"\n") - raw.count(b"\r\n"), 0,
            "no bare LF may survive in a CRLF file, and no mixed endings",
        )
        self.assertEqual(self._declared(), ())

    def test_an_unwritable_template_reports_instead_of_aborting(self):
        """The repair must never be fatal to an upgrade.

        An unguarded write escaped into the hook dispatcher's sys.exit(3),
        which reports itself as a pre-flight failure for a phase-3 problem.
        """

        import os

        self.template.write_text(self.CONTAMINATED, encoding="utf-8")
        os.chmod(self.template, 0o444)
        self.addCleanup(os.chmod, self.template, 0o644)
        try:
            result = self.ext.repair_declaring_scaffold(self.root)
        except Exception as exc:  # noqa: BLE001
            self.fail(f"repair must not raise; got {exc!r}")
        self.assertEqual(result, [], "an unwritable template repairs nothing")
        self.assertEqual(
            self.template.read_text(encoding="utf-8"), self.CONTAMINATED,
            "the repair writes through a staged file and a rename, which needs "
            "only directory permission — so it must check writability first "
            "rather than silently overriding the operator's read-only marking",
        )
        self.assertEqual(
            sorted(p.name for p in self.template.parent.iterdir()),
            ["plan-template.md"],
            "no staged temp file may be left behind",
        )

    def test_a_non_os_failure_also_reports_instead_of_aborting(self):
        """"Never fatal" must mean any exception, not just OSError.

        The chmod case above raises PermissionError, an OSError subclass, so a
        narrower `except (OSError, UnicodeDecodeError)` would still pass it.
        A parser that raises is the case that distinguishes them, and it is
        reachable: the repair loads `review_policy` from a tree that extraction
        has just rewritten.
        """

        self.template.write_text(self.CONTAMINATED, encoding="utf-8")

        def _boom(*_args, **_kwargs):
            raise ValueError("fencer exploded")

        # Patched on the extension module rather than on `review_policy`:
        # the repair calls `importlib.reload` on a cached parser, which
        # re-executes it from disk and discards any patch applied there.
        with patch.object(self.ext, "_fence_serialization_examples", _boom):
            try:
                result = self.ext.repair_declaring_scaffold(self.root)
            except Exception as exc:  # noqa: BLE001
                self.fail(f"repair must swallow any failure; got {exc!r}")
        self.assertEqual(result, [])
        self.assertEqual(
            self.template.read_text(encoding="utf-8"), self.CONTAMINATED,
            "a failed repair must leave the template untouched",
        )

    def test_the_resume_branch_repairs_before_it_re_runs_the_gate(self):
        """Pins the CALL SITE, not just the helper.

        `test_the_resume_path_reaches_the_repair` above calls the helper
        directly, so it stays green even if the resume branch stops calling it
        — which would silently restore the stranding this AC exists to prevent.
        Driving the whole resume branch needs a lock file, argv, and a full
        docs corpus, so this asserts the ordering structurally instead: the
        repair must appear immediately before the resume site's
        `phase_docs_gate(root)`, and the file must contain exactly the two
        gate call sites the plan accounts for.
        """

        import upgrade_lib
        import upgrade_wavefoundry

        self.template.write_text(self.CONTAMINATED, encoding="utf-8")
        upgrade_lib.write_upgrade_lock(
            self.root, from_version="1.0.0", to_version="1.0.1"
        )
        upgrade_lib.update_upgrade_lock(self.root, failed_phase="docs_gate")

        seen: list[tuple[str, ...]] = []

        def _recording_gate(root):
            # What the gate would ACTUALLY see. The gate is the thing the
            # repair exists to unblock, so ordering is the whole contract.
            seen.append(self._declared())

        with patch.object(upgrade_wavefoundry, "phase_docs_gate", _recording_gate):
            rc = upgrade_wavefoundry.main(
                ["--resume-after-gate", "--root", str(self.root)]
            )

        self.assertEqual(rc, 0, "the resume branch must complete")
        self.assertEqual(
            seen, [()],
            "the docs gate must run exactly once and see a repaired template; "
            "a repair that is skipped, or ordered after the gate, strands the "
            "one path a halted repository can travel",
        )

    def test_the_blocking_set_and_the_repairable_set_are_one_constant(self):
        """AC-4a's invariant, pinned rather than assumed.

        The lint rule blocks on `review_policy.SCAFFOLD_DOCS` and the repair
        iterates the same constant. Two independent literals would let the
        blocking set grow past the repairable set on the next edit, shipping a
        gate with no repair — the exact stranding this wave exists to prevent.
        """

        import review_policy
        from wave_lint_lib import core_validators

        # Value equality, not identity: `repair_declaring_scaffold` calls
        # `importlib.reload` on `review_policy`, which rebinds the constant to
        # a NEW tuple while `core_validators` still holds the pre-reload one.
        # An identity assertion passes standalone and fails in-suite the moment
        # any repair test has run first.
        self.assertEqual(
            core_validators.SCAFFOLD_DOCS, review_policy.SCAFFOLD_DOCS,
            "the linter and the parser must agree on the scaffold set",
        )
        linter_source = (SCRIPTS_ROOT / "wave_lint_lib" / "core_validators.py").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            "SCAFFOLD_DOCS,", linter_source,
            "the linter must IMPORT the shared constant, not define its own",
        )
        self.assertNotIn(
            "SCAFFOLD_DOCS = (", linter_source,
            "a local definition would let the two sets drift apart",
        )
        source = Path(self.ext.__file__ or "").read_text(encoding="utf-8") \
            if getattr(self.ext, "__file__", None) and Path(self.ext.__file__).is_file() \
            else (SCRIPTS_ROOT / "upgrade_extensions.py").read_text(encoding="utf-8")
        self.assertIn(
            'getattr(review_policy, "SCAFFOLD_DOCS", ())', source,
            "the repair must iterate the shared constant, not a literal, and "
            "must read it defensively because the loop header sits outside "
            "the per-file guard",
        )
        self.assertNotIn(
            '"docs/plans/plan-template.md",)', source,
            "a local literal would let the repairable set drift from the "
            "blocking set, which is the invariant AC-4a rests on",
        )

    def test_the_post_fence_recheck_prevents_a_corrupting_write(self):
        """The re-check is defense in depth against a fencer bug.

        It is pinned by INJECTION on purpose. A delivery lane once reached
        this guard with a real document — a fenced example beside a stray
        declaring bullet — but that was only possible because the fencer was
        fence-blind, and repairing that blindness turned the input into a
        successful repair (see the stray-bullet test above). No natural input
        is known to reach the re-check now, so a fixture-based pin would be
        vacuous. The guard still earns its place: it is the only thing
        standing between a future fencer defect and a written file that
        un-fences a real example, so the caller must refuse a transformation
        that still declares no matter which transform produced it.
        """

        self.template.write_text(self.CONTAMINATED, encoding="utf-8")
        before = self.template.read_bytes()
        still_declaring = (
            "# T\n\n## Serialization Points\n\n- `real/target.py`\n\n## Next\n"
        )
        import review_policy

        self.assertEqual(
            review_policy.serialization_point_paths(still_declaring),
            ("real/target.py",),
            "the injected transform must genuinely still declare",
        )
        with patch.object(
            self.ext,
            "_fence_serialization_examples",
            lambda *_a, **_k: still_declaring,
        ):
            self.assertEqual(self.ext.repair_declaring_scaffold(self.root), [])
        self.assertEqual(
            self.template.read_bytes(), before,
            "the re-check must refuse a transformation that still declares",
        )

    def test_a_clean_template_produces_no_operator_message(self):
        """The early-continue is NOT redundant with the post-fence re-check.

        With it removed, the transform double-fences the already-fenced
        example, the re-check refuses, and the repair prints a false
        "fence it by hand" warning on EVERY upgrade of EVERY clean repository.
        """

        import contextlib
        import io

        shipped = (SCRIPTS_ROOT.parent.parent.parent / "docs" / "plans" / "plan-template.md")
        self.template.write_text(shipped.read_text(encoding="utf-8"), encoding="utf-8")
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            result = self.ext.repair_declaring_scaffold(self.root)
        self.assertEqual(result, [])
        self.assertEqual(
            buffer.getvalue(), "",
            "a clean template must produce no message at all",
        )

    def test_the_repair_reloads_the_extracted_parser(self):
        """A cached pre-upgrade parser would silently skip the repair.

        `review_evidence` imports `review_policy` at module scope and the
        sidecar cleanup runs before this hook, so `sys.modules` really can hold
        an old parser — one that did not know the marker block at all.

        This is pinned BEHAVIORALLY. The previous assertion looked for the
        literal `importlib.reload(cached)` anywhere in the module source, but
        that string appears four times and three of them predate this change,
        so deleting the reload here left the test green while the repair
        silently no-opped and the docs gate halted the upgrade.

        The stub below is the transition run: a pre-upgrade runner holding a
        parser that does not know the marker block, so it reports the
        contaminated template as declaring nothing. Only a reload against the
        extracted tree can see the real declaration.
        """

        import importlib
        import review_policy

        self.template.write_text(self.CONTAMINATED, encoding="utf-8")
        self.assertEqual(
            self._declared(), ("path/to/file.swift", "docs/specs/"),
            "fixture must declare when read by the REAL parser",
        )

        stale = types.ModuleType("review_policy")
        stale.__file__ = review_policy.__file__
        stale.__spec__ = review_policy.__spec__
        stale.SCAFFOLD_DOCS = review_policy.SCAFFOLD_DOCS
        # The old parser's blind spot: it reports the contamination as clean.
        stale.serialization_point_paths = lambda _text: ()

        with patch.dict(sys.modules, {"review_policy": stale}):
            repaired = self.ext.repair_declaring_scaffold(self.root)

        self.assertEqual(
            repaired, ["docs/plans/plan-template.md"],
            "a stale cached parser must be reloaded, not trusted; with the "
            "reload gone the repair sees () and skips, and the class-a gate "
            "then halts exactly the repositories this change protects",
        )
        importlib.reload(review_policy)
        self.assertEqual(self._declared(), ())

    def test_a_run_reaching_eof_keeps_the_trailing_newline(self):
        """The repair is insertion-only; it must not eat the final newline."""

        self.template.write_text(
            "# T\n\n## Serialization Points\n\n- `src/app/handler.py`\n",
            encoding="utf-8",
        )
        self.ext.repair_declaring_scaffold(self.root)
        self.assertTrue(
            self.template.read_text(encoding="utf-8").endswith("\n"),
            "the trailing newline must survive a run that reaches EOF",
        )

    def test_both_ends_of_the_repair_open_with_untranslated_newlines(self):
        """The write side is a Windows-only corruption, so pin the contract.

        Reading without ``newline=""`` turns a CRLF checkout into LF in
        memory; writing without it translates every ``\\n`` back to
        ``os.linesep``. On POSIX that write-side translation is a no-op, so a
        byte-comparison test passes on this machine while a Windows operator
        gets ``\\r\\r\\n`` on every line of the template. Asserting the call
        contract is what makes the pin portable — a byte test cannot reach it
        from here.
        """

        import pathlib

        real_open = pathlib.Path.open
        modes: dict[str, object] = {}

        def _spy(self_path, mode="r", *args, **kwargs):
            # The write lands on a staged sibling that is then renamed over the
            # template, so match the prefix rather than the exact name.
            if self_path.name.startswith("plan-template.md"):
                modes[mode] = kwargs.get("newline", "<absent>")
            return real_open(self_path, mode, *args, **kwargs)

        self.template.write_text(self.CONTAMINATED, encoding="utf-8")
        with patch.object(pathlib.Path, "open", _spy):
            self.assertEqual(
                self.ext.repair_declaring_scaffold(self.root),
                ["docs/plans/plan-template.md"],
            )
        self.assertEqual(
            modes, {"r": "", "w": ""},
            "both the read and the write must pass newline='' — "
            f"saw {modes}",
        )

    def _repair_capturing(self):
        import contextlib
        import io

        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            result = self.ext.repair_declaring_scaffold(self.root)
        return result, buffer.getvalue()

    def test_the_repair_reports_every_outcome_to_the_operator(self):
        """AC-6's report, asserted rather than named.

        Production discards the return value at both call sites, so `print` is
        the ONLY operator-facing report. Deleting any of the three messages
        previously survived every test, and two tests named
        "..._reports_instead_of_aborting" asserted only the no-raise half.
        """

        import os

        # Success.
        self.template.write_text(self.CONTAMINATED, encoding="utf-8")
        result, out = self._repair_capturing()
        self.assertEqual(result, ["docs/plans/plan-template.md"])
        self.assertIn("fenced the example block", out)
        self.assertIn("plan-template.md", out)

        # Refusal: an unrecognized template the fencer declines to transform.
        # Injected, because the fencer now recognizes every natural shape.
        self.template.write_text(self.CONTAMINATED, encoding="utf-8")
        with patch.object(
            self.ext, "_fence_serialization_examples", lambda *_a, **_k: None
        ):
            result, out = self._repair_capturing()
        self.assertEqual(result, [])
        self.assertIn("could not be repaired", out)
        self.assertIn(
            "--resume-after-gate", out, "the refusal must name the remedy"
        )

        # Crash: the operator must still be told.
        self.template.write_text(self.CONTAMINATED, encoding="utf-8")

        def _boom(*_a, **_k):
            raise ValueError("fencer exploded")

        with patch.object(self.ext, "_fence_serialization_examples", _boom):
            result, out = self._repair_capturing()
        self.assertEqual(result, [])
        self.assertIn("could not be repaired", out)
        self.assertIn("fencer exploded", out, "the cause must reach the operator")

    def test_an_already_fenced_example_is_never_re_fenced(self):
        """The realistic contamination: shipped template plus one stray bullet.

        Re-fencing an already-fenced example flips fence parity, so the result
        still declares and the repair refuses — halting the upgrade on a
        template an operator produced with one ordinary edit. Uses the REAL
        shipped template so the fixture cannot drift from what ships.
        """

        shipped = (
            SCRIPTS_ROOT.parent.parent.parent / "docs" / "plans" / "plan-template.md"
        ).read_text(encoding="utf-8")
        self.assertIn("```", shipped, "the shipped template fences its example")
        contaminated = shipped.replace(
            "## Affected Architecture Docs",
            "- `src/api/routes.py`\n\n## Affected Architecture Docs",
            1,
        )
        self.template.write_text(contaminated, encoding="utf-8")
        self.assertEqual(self._declared(), ("src/api/routes.py",))
        self.assertEqual(
            self.ext.repair_declaring_scaffold(self.root),
            ["docs/plans/plan-template.md"],
            "a stray bullet beside a fenced example must be repairable",
        )
        self.assertEqual(self._declared(), ())
        after = self.template.read_text(encoding="utf-8")
        self.assertEqual(
            after.count("```"), shipped.count("```") + 2,
            "exactly one new fence pair; the existing one must be untouched",
        )

    def test_the_scan_loop_boundaries_are_pinned(self):
        """Branch coverage for the run scanner, not just fixture coverage.

        The section bound, the marker predicate, the multi-run splice order and
        the loop advance each get an input that fails when the branch is wrong.
        """

        fence = self.ext._fence_serialization_examples
        import review_policy

        declares = review_policy.serialization_point_paths

        # Section bound: a declaring bullet AFTER the section must be ignored.
        outside = (
            "# T\n\n## Serialization Points\n\n- prose only\n\n"
            "## Next\n\n- `src/after.py`\n"
        )
        self.assertIsNone(
            fence(outside, declares),
            "a bullet outside the section is not this rule's business",
        )

        # Multi-run splice: two separate declaring runs, both fenced, and the
        # document must keep every line (a forward splice corrupts indices).
        multi = (
            "# T\n\n## Serialization Points\n\n"
            "- `src/one.py`\n\nMiddle prose.\n\n- `src/two.py`\n\n## Next\n"
        )
        out = fence(multi, declares)
        self.assertIsNotNone(out)
        self.assertEqual(declares(out), ())
        self.assertIn("Middle prose.", out)
        self.assertIn("src/one.py", out)
        self.assertIn("src/two.py", out)
        self.assertEqual(out.count("```"), 4, "one fence pair per declaring run")

        # No declaring run at all: refuse rather than fence prose.
        self.assertIsNone(
            fence("# T\n\n## Serialization Points\n\n- prose only\n", declares)
        )

    def test_every_predicate_matches_the_shipped_parser_not_a_restatement(self):
        """Tab forms the parser accepts must not be invisible to the repair.

        Each shape below declares to `serialization_point_paths`, so each must
        be repaired. A locally-restated predicate misses them: the parser's
        `_BULLET_RE` accepts a tab after the bullet marker and
        `_SECTION_HEADING_RE` accepts a tab after `##`, while a
        `startswith("- ")` / `startswith("## ")` test does not.
        """

        shapes = {
            "tab-separated tier-1 bullet": (
                "# T\n\n## Serialization Points\n\n-\t`src/one.py`\n\n## Next\n"
            ),
            "tab-separated bullet under the marker": (
                "# T\n\n## Serialization Points\n\n"
                "**Review targets (repo-relative paths):**\n\n"
                "-\t`src/one.py`\n\n## Next\n"
            ),
            "tab-form next heading": (
                "# T\n\n## Serialization Points\n\n- `src/one.py`\n\n"
                "##\tAffected Architecture Docs\n\n- `src/two.py`\n"
            ),
        }
        for name, text in shapes.items():
            with self.subTest(shape=name):
                self.template.write_text(text, encoding="utf-8")
                self.assertNotEqual(
                    self._declared(), (),
                    "fixture must declare to the shipped parser",
                )
                self.assertEqual(
                    self.ext.repair_declaring_scaffold(self.root),
                    ["docs/plans/plan-template.md"],
                )
                self.assertEqual(self._declared(), ())

    def test_the_repair_never_writes_outside_its_own_section(self):
        """A tab-form heading used to truncate the scan and fence the NEXT section.

        The post-verify cannot catch this: fencing content in a section that
        declares nothing does not change what the parser extracts, so the file
        was written and reported as a success while carrying fences the
        operator never asked for in `## Affected Architecture Docs`.
        """

        self.template.write_text(
            "# T\n\n## Serialization Points\n\n"
            "**Review targets (repo-relative paths):**\n\n- `docs/specs/`\n\n"
            "##\tAffected Architecture Docs\n\n- `src/real/thing.py`\n",
            encoding="utf-8",
        )
        self.ext.repair_declaring_scaffold(self.root)
        after = self.template.read_text(encoding="utf-8")
        tail = after.split("##\tAffected Architecture Docs", 1)[1]
        self.assertNotIn(
            "```", tail,
            "the repair must not insert fences past its own section boundary",
        )

    def test_the_repair_sources_its_predicates_from_the_parser(self):
        """Structural pin for the rule that produced three drifted predicates.

        Requirement 2 forbids re-implementing extraction because a second
        implementation drifts. The same holds for the fence scanner and the
        boundary tests, which is exactly where the drift happened.
        """

        source = (SCRIPTS_ROOT / "upgrade_extensions.py").read_text(encoding="utf-8")
        body = source.split("def _fence_serialization_examples", 1)[1]
        body = body.split("\ndef ", 1)[0]
        for name in (
            "parser._fenced_line_flags",
            "parser._SERIALIZATION_POINTS_HEADING_RE",
            "parser._SECTION_HEADING_RE",
            "parser._BULLET_RE",
            "parser._REVIEW_TARGETS_MARKER_RE",
        ):
            self.assertIn(name, body, f"{name} must come from the parser")
        self.assertNotIn(
            'startswith(("- ", "* "))', body,
            "a locally-restated bullet test is the defect this pins",
        )
        self.assertNotIn(
            'startswith("## ")', body,
            "a locally-restated heading test is the defect this pins",
        )

    def test_the_staged_write_preserves_mode_and_leaves_no_debris(self):
        """Both properties of the atomic write, pinned where they can fail.

        The chmod-444 refusal returns BEFORE a staged file is ever created, so
        it cannot pin cleanup. These drive the two paths where a temp file
        actually exists: a failure during the staged write, and a failure at
        the rename. Mode preservation had no pin at all, so a checkout whose
        template is group-writable would silently come back private.
        """

        import os

        def _names():
            return sorted(p.name for p in self.template.parent.iterdir())

        for mode in (0o644, 0o664, 0o600):
            with self.subTest(mode=oct(mode)):
                self.template.write_text(self.CONTAMINATED, encoding="utf-8")
                os.chmod(self.template, mode)
                self.assertEqual(
                    self.ext.repair_declaring_scaffold(self.root),
                    ["docs/plans/plan-template.md"],
                )
                self.assertEqual(
                    self.template.stat().st_mode & 0o7777, mode,
                    "the repair must carry the template's own mode across the "
                    "rename; the staged file is created with the umask",
                )
                self.assertEqual(_names(), ["plan-template.md"])

        original = self.CONTAMINATED
        # Each case is INDEPENDENT: the directory is reset first, so a case
        # cannot pass by tripping on debris the previous one left. The first
        # two fail AFTER the staged file exists, so they are the ones that
        # genuinely pin cleanup; the third fails before it is created and
        # pins only that the original survives.
        cases = {
            "rename": lambda: patch.object(
                self.ext.os, "replace", side_effect=OSError("boom")
            ),
            "mode carry-over": lambda: patch.object(
                self.ext.os, "chmod", side_effect=OSError("no chmod")
            ),
            "staged write": lambda: patch.object(
                type(self.template), "open", _explode_on_staged
            ),
        }
        real_open = type(self.template).open

        def _explode_on_staged(self_path, mode="r", *a, **kw):
            if self_path.name.endswith(".wf-scaffold-repair"):
                raise OSError("disk full")
            return real_open(self_path, mode, *a, **kw)

        for label, make_patcher in cases.items():
            with self.subTest(fails_at=label):
                for stray in self.template.parent.iterdir():
                    if stray.name != "plan-template.md":
                        stray.unlink()
                self.template.write_text(original, encoding="utf-8")
                with make_patcher():
                    result = self.ext.repair_declaring_scaffold(self.root)
                self.assertEqual(result, [], "a failed write repairs nothing")
                self.assertEqual(
                    self.template.read_text(encoding="utf-8"), original,
                    "the original must survive intact; this is why the write "
                    "stages instead of truncating in place",
                )
                self.assertEqual(
                    _names(), ["plan-template.md"],
                    "a staged temp file must never be left in the operator's "
                    "docs/plans directory",
                )
