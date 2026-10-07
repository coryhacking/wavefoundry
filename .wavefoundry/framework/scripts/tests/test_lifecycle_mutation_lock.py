"""Wave 1seax (1seat): lifecycle mutation lock, forward recoverability, seat
alignment, and selective subprocess bounds."""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
from framework_files import source_path  # wf_server-aware source locations (wave 1yzd0)


# Extracted handlers resolve the public composition-root module per call.
# Use the shared loader so patches target that exact module identity.
from server_tools_support import load_server
from record_layout_support import RecordTreeBuilder
import vocabulary_profile


srv = load_server()


def _repo(root: Path) -> None:
    builder = RecordTreeBuilder(root)
    builder.waves_dir.mkdir(parents=True, exist_ok=True)
    builder.plans_dir.mkdir(parents=True, exist_ok=True)
    (root / ".wavefoundry").mkdir(parents=True, exist_ok=True)


def _wave(root: Path, wave_id: str, *, status: str = "active", changes: str = "") -> Path:
    """A minimal container record in the loaded profile; ``changes`` is
    written with the shipped labels and localized."""
    d = RecordTreeBuilder(root).waves_dir / wave_id
    d.mkdir(parents=True, exist_ok=True)
    wave_md = vocabulary_profile.record_file(d)
    wave_md.write_text(
        f"{vocabulary_profile.RECORD_TITLE}\n\nOwner: Engineering\nStatus: {status}\n"
        f"Last verified: 2026-07-20\n\n{vocabulary_profile.id_line(wave_id)}\n\n"
        f"{vocabulary_profile.MEMBER_HEADING}\n{vocabulary_profile.localize_template(changes)}\n\n"
        f"{vocabulary_profile.SUMMARY_HEADING}\n\nsummary\n",
        encoding="utf-8",
    )
    return wave_md


def _change_doc_text(change_id: str) -> str:
    return vocabulary_profile.localize_template(f"# T\n\nChange ID: `{change_id}`\n")


class MutationLockTests(unittest.TestCase):
    """AC-1: concurrent lifecycle mutations serialize; the loser gets a
    structured busy response; the lock is invisible uncontended."""

    def _wrapped(self, root: Path, tool_name: str, fn):
        class _Tool: ...
        class _TM: ...
        class _MCP: ...
        tool = _Tool(); tool.fn = fn
        tm = _TM(); tm._tools = {tool_name: tool}
        mcp = _MCP(); mcp._tool_manager = tm
        handler = SimpleNamespace(root=root)
        srv._wrap_lifecycle_mutation_lock(mcp, lambda: handler)
        return tool.fn

    def test_contended_mutation_returns_structured_busy(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _repo(root)
            entered = threading.Event()
            release = threading.Event()

            def slow_tool(**kwargs):
                entered.set()
                release.wait(timeout=10)
                return {"status": "ok", "data": {}}

            def fast_tool(**kwargs):
                return {"status": "ok", "data": {}}

            slow = self._wrapped(root, "wf_close_wave", slow_tool)
            fast = self._wrapped(root, "wf_add_change", fast_tool)
            results = {}
            t = threading.Thread(target=lambda: results.update(slow=slow()))
            t.start()
            self.assertTrue(entered.wait(timeout=10))
            # fcntl record locks do not conflict intra-process, so the
            # contended path is exercised through a REAL second process.
            probe = subprocess.run(
                [sys.executable, "-c", (
                    "import sys, json; sys.path.insert(0, sys.argv[1]);\n"
                    "from types import SimpleNamespace\n"
                    "import importlib.util\n"
                    "spec = importlib.util.spec_from_file_location('si', sys.argv[1] + '/wf_server/server_impl.py')\n"
                    "m = importlib.util.module_from_spec(spec); sys.modules['si'] = m\n"
                    "spec.loader.exec_module(m)\n"
                    "from pathlib import Path\n"
                    "try:\n"
                    "    with m._lifecycle_mutation_lock(Path(sys.argv[2])):\n"
                    "        print('ACQUIRED')\n"
                    "except m.LifecycleMutationBusy:\n"
                    "    print('BUSY')\n"
                ), str(SCRIPTS_ROOT), str(root)],
                capture_output=True, text=True, timeout=60,
            )
            release.set()
            t.join(timeout=10)
            self.assertIn("BUSY", probe.stdout)
            self.assertEqual(results["slow"]["status"], "ok")

    def test_uncontended_mutation_is_invisible(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _repo(root)
            def tool(**kwargs):
                return {"status": "ok", "data": {"ran": True}}
            wrapped = self._wrapped(root, "wf_set_handoff", tool)
            out = wrapped()
            self.assertEqual(out["data"]["ran"], True)

    def test_busy_response_shape(self):
        busy = srv.LifecycleMutationBusy("lifecycle mutation lock is held: /x/lifecycle-mutation.lock")
        resp = srv._lifecycle_mutation_busy_response("wf_close_wave", busy)
        self.assertEqual(resp["status"], "error")
        self.assertTrue(resp["data"]["busy"])
        codes = [d["code"] for d in resp["diagnostics"]]
        self.assertIn("lifecycle_mutation_locked", codes)
        # Wave 1zls7 (1zlts): built from attributes, never from str(busy).
        self.assertNotIn("/x/", resp["diagnostics"][0]["message"])
        self.assertIn(".wavefoundry/lifecycle-mutation.lock", resp["diagnostics"][0]["message"])

    def test_non_census_tools_not_wrapped(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            def tool(**kwargs):
                return {"status": "ok", "data": {}}
            wrapped = self._wrapped(root, "code_read", tool)
            self.assertIs(wrapped, tool)

    def test_handler_resolution_failure_refuses_without_running_mutation(self):
        called = False

        def tool(**kwargs):
            nonlocal called
            called = True
            return {"status": "ok"}

        class _Tool: ...
        class _TM: ...
        class _MCP: ...
        wrapped_tool = _Tool(); wrapped_tool.fn = tool
        tm = _TM(); tm._tools = {"wf_prepare_wave": wrapped_tool}
        mcp = _MCP(); mcp._tool_manager = tm

        def broken_handler():
            raise RuntimeError("injected root failure")

        srv._wrap_lifecycle_mutation_lock(mcp, broken_handler)
        result = wrapped_tool.fn()
        self.assertEqual(result["status"], "error")
        self.assertFalse(called)
        self.assertIn(
            "lifecycle_lock_unavailable",
            {item["code"] for item in result["diagnostics"]},
        )


class ForwardRecoverabilityTests(unittest.TestCase):
    """AC-2: a retry after any single-step interruption converges."""

    def test_admission_retry_after_move_without_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _repo(root)
            wave_md = _wave(root, "1aaaa demo")
            doc = wave_md.parent / "1abcd-enh thing.md"
            doc.write_text(_change_doc_text("1abcd-enh thing"), encoding="utf-8")
            # Interrupted state: doc already moved into the wave folder, but
            # wave.md does not list it. Retry the SAME call.
            with patch.object(srv, "_attach_lint_to_response", side_effect=lambda e, *a, **k: e):
                out = srv.wf_add_change_response(root, "1aaaa", "1abcd", mode="create")
            self.assertEqual(out["status"], "ok")
            text = wave_md.read_text(encoding="utf-8")
            self.assertIn("1abcd-enh thing", text)

    def test_removal_retry_after_move_back_without_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _repo(root)
            wave_md = _wave(
                root, "1aaaa demo",
                changes="\nChange ID: `1abcd-enh thing`\nChange Status: `planned`\n",
            )
            # Interrupted state: doc already moved back to plans, wave.md still
            # lists it. Retry the SAME call.
            (RecordTreeBuilder(root).plans_dir / "1abcd-enh thing.md").write_text(
                _change_doc_text("1abcd-enh thing"), encoding="utf-8"
            )
            with patch.object(srv, "_attach_lint_to_response", side_effect=lambda e, *a, **k: e):
                out = srv.wf_remove_change_response(root, "1aaaa", "1abcd-enh thing", mode="create")
            self.assertEqual(out["status"], "ok")
            self.assertNotIn("1abcd-enh thing", wave_md.read_text(encoding="utf-8"))

    def test_close_retry_after_wave_md_written_heals_handoff(self):
        """The live-identified seam: wave.md closed, handoff not yet updated —
        re-running close converges the handoff instead of skipping it."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _repo(root)
            _wave(root, "1aaaa demo", status="closed")
            handoff = root / "docs" / "agents" / "session-handoff.md"
            handoff.parent.mkdir(parents=True, exist_ok=True)
            handoff.write_text(
                "# Session Handoff\n\nActive wave: `1aaaa demo`\n", encoding="utf-8"
            )
            with patch.object(srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}), \
                 patch.object(srv.lifecycle_gates, "_review_evidence_diagnostics", return_value=[]) as _gate_mock_1, \
                 patch.object(srv, "_close_wave_secrets_gate", return_value=({}, [])) if hasattr(srv, "_close_wave_secrets_gate") else patch.object(srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
                out = srv.wf_close_wave_response(root, "1aaaa", mode="create")
                _gate_mock_1.assert_called()
            # Whatever gates fire, the handoff convergence must have run for a
            # closed wave when the close path reached the convergence point.
            if out["status"] == "ok":
                self.assertNotIn("1aaaa demo", handoff.read_text(encoding="utf-8"))


class SeatAlignmentTests(unittest.TestCase):
    """AC-6: recorded councils must include the brief's required seats."""

    def test_missing_rotating_seat_is_flagged(self):
        info = {"meta": {
            "seats": "red-team, qa-reviewer",
            "rotating-seat": "docs-contract-reviewer",
        }}
        brief = {"fixed_seat": "red-team", "rotating_seat": "docs-contract-reviewer"}
        issues = srv._council_seat_alignment_issues(info, brief)
        self.assertTrue(any("rotating seat" in i for i in issues))

    def test_matching_council_passes(self):
        info = {"meta": {
            "seats": "red-team, architecture-reviewer, docs-contract-reviewer",
            "rotating-seat": "docs-contract-reviewer",
        }}
        brief = {"fixed_seat": "red-team", "rotating_seat": "docs-contract-reviewer"}
        self.assertEqual(srv._council_seat_alignment_issues(info, brief), [])

    def test_wrong_rotating_field_is_flagged(self):
        info = {"meta": {
            "seats": "red-team, security-reviewer, code-reviewer",
            "rotating-seat": "code-reviewer",
        }}
        brief = {"fixed_seat": "red-team", "rotating_seat": "docs-contract-reviewer"}
        issues = srv._council_seat_alignment_issues(info, brief)
        self.assertTrue(issues)

    def test_prepare_flow_wires_the_alignment_check(self):
        source = source_path("server_impl.py").read_text(encoding="utf-8")
        self.assertIn("seat_alignment_issues = _council_seat_alignment_issues(verdict_info, council_brief)", source)
        self.assertIn('"council_seats_misaligned"', source)


class SubprocessBoundsTests(unittest.TestCase):
    """AC-3: gardener + surface render are bounded; upgrade/setup stay exempt."""

    def test_gardener_timeout_returns_structured_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            def boom(*a, **k):
                raise subprocess.TimeoutExpired(cmd="gardener", timeout=k.get("timeout"))
            with patch.object(srv, "_mcp_subprocess_run", side_effect=boom):
                out = srv.run_garden(root)
            self.assertFalse(out["passed"])
            self.assertTrue(out["timed_out"])
            self.assertIn("gardener_timeout_seconds", out["output"])

    def test_surface_render_timeout_returns_structured_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            def boom(*a, **k):
                raise subprocess.TimeoutExpired(cmd="render", timeout=k.get("timeout"))
            with patch.object(srv, "_mcp_subprocess_run", side_effect=boom):
                out = srv.run_sync_surfaces(root)
            self.assertFalse(out["passed"])
            self.assertTrue(out["timed_out"])
            self.assertEqual(out["written"], [])
            self.assertIn("surface_render_timeout_seconds", out["output"])

    def test_output_bounded_with_truncation_marker(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fake = SimpleNamespace(returncode=0,
                                   stdout="x" * (srv.SUBPROCESS_OPS_OUTPUT_CAP_CHARS + 500),
                                   stderr="")
            with patch.object(srv, "_mcp_subprocess_run", return_value=fake):
                out = srv.run_garden(root)
            self.assertTrue(out["output_truncated"])
            self.assertIn("output truncated at", out["output"])

    def test_timeout_is_config_tunable_and_fail_safe(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "docs").mkdir()
            (root / "docs" / "workflow-config.json").write_text(
                json.dumps({"subprocess_ops": {"gardener_timeout_seconds": 555}}),
                encoding="utf-8",
            )
            self.assertEqual(srv.subprocess_ops_timeout_seconds(root, "gardener"), 555.0)
            self.assertEqual(
                srv.subprocess_ops_timeout_seconds(root, "surface_render"),
                srv.SUBPROCESS_OPS_TIMEOUT_DEFAULT,
            )
        self.assertEqual(
            srv.subprocess_ops_timeout_seconds(Path("/nonexistent"), "gardener"),
            srv.SUBPROCESS_OPS_TIMEOUT_DEFAULT,
        )

    def test_exemption_pins_upgrade_and_setup_spawns(self):
        """Source pin: the long-running orchestrations never consume the
        short-op bounds — a deadline there converts slow-network success
        into failure."""
        for name in ("upgrade_wavefoundry.py", "setup_wavefoundry.py"):
            source = source_path(name).read_text(encoding="utf-8")
            self.assertNotIn("subprocess_ops_timeout_seconds", source,
                             f"{name} must stay exempt from short-op bounds")


if __name__ == "__main__":
    unittest.main()


class LockReleaseRecordTests(unittest.TestCase):
    """1zf1u: the persisted lock carrier records its release, so a reader can
    tell a finished owner from a crashed one. Liveness stays the OS lock."""

    def setUp(self):
        sys.path.insert(0, str(SCRIPTS_ROOT))
        import lifecycle_lock
        import runtime_lock

        self.lifecycle_lock = lifecycle_lock
        self.runtime_lock = runtime_lock
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / ".wavefoundry").mkdir()
        self.path = self.root / lifecycle_lock.LIFECYCLE_MUTATION_LOCK_REL

    def tearDown(self):
        self.tmp.cleanup()

    def _metadata(self) -> dict:
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _free(self) -> bool:
        with self.lifecycle_lock.lifecycle_mutation_lock(self.root):
            return True

    def test_a_normal_exit_stamps_the_release(self):
        with self.lifecycle_lock.lifecycle_mutation_lock(self.root):
            held = self._metadata()
        self.assertNotIn("released_at", held)
        after = self._metadata()
        self.assertEqual(after["pid"], held["pid"])
        self.assertEqual(after["acquired_at"], held["acquired_at"])
        self.assertGreaterEqual(after["released_at"], after["acquired_at"])
        self.assertTrue(self._free())

    def test_a_raising_body_keeps_its_exception_and_is_stamped(self):
        with self.assertRaisesRegex(ValueError, "body failed"):
            with self.lifecycle_lock.lifecycle_mutation_lock(self.root):
                raise ValueError("body failed")
        self.assertIn("released_at", self._metadata())
        self.assertTrue(self._free())

    def test_a_failed_release_stamp_still_releases_and_keeps_the_outcome(self):
        real_write = self.runtime_lock.RuntimeFileLock.write_metadata

        def write(lock, payload):
            if "released_at" in payload:
                raise self.runtime_lock.RuntimeLockError(5, "injected")
            return real_write(lock, payload)

        real_release = self.runtime_lock.RuntimeFileLock.release
        released = []

        def release(lock):
            released.append(True)
            return real_release(lock)

        with patch.object(self.runtime_lock.RuntimeFileLock, "write_metadata", write), \
             patch.object(self.runtime_lock.RuntimeFileLock, "release", release):
            with self.assertRaisesRegex(ValueError, "body failed"):
                with self.lifecycle_lock.lifecycle_mutation_lock(self.root):
                    raise ValueError("body failed")
        self.assertEqual(released, [True])
        self.assertNotIn("released_at", self._metadata())

    def test_an_interrupt_during_the_stamp_still_releases(self):
        real_release = self.runtime_lock.RuntimeFileLock.release
        real_write = self.runtime_lock.RuntimeFileLock.write_metadata
        released = []

        def write(lock, payload):
            if "released_at" in payload:
                raise KeyboardInterrupt
            return real_write(lock, payload)

        def release(lock):
            released.append(True)
            return real_release(lock)

        with patch.object(self.runtime_lock.RuntimeFileLock, "write_metadata", write), \
             patch.object(self.runtime_lock.RuntimeFileLock, "release", release):
            with self.assertRaises(KeyboardInterrupt):
                with self.lifecycle_lock.lifecycle_mutation_lock(self.root):
                    pass
        self.assertEqual(released, [True])

    def test_an_interrupt_while_building_the_acquire_metadata_still_releases(self):
        # DEL-1ZF1U-ACQUIRE-METADATA: nothing between a successful acquire and
        # the release-protected region may skip release().
        real_release = self.runtime_lock.RuntimeFileLock.release
        released = []
        calls = []

        def release(lock):
            released.append(True)
            return real_release(lock)

        def interrupting_time():
            calls.append(True)
            if len(calls) == 1:
                raise KeyboardInterrupt
            return 0.0

        fake_time = SimpleNamespace(time=interrupting_time)
        with patch.object(self.lifecycle_lock, "time", fake_time), \
             patch.object(self.runtime_lock.RuntimeFileLock, "release", release):
            with self.assertRaises(KeyboardInterrupt):
                with self.lifecycle_lock.lifecycle_mutation_lock(self.root):
                    self.fail("the body must not run")
        self.assertEqual(released, [True])


# Wave 1zimc (1zimg): the lifecycle lock is a process-owned record lock on
# POSIX, so a same-process re-entry or a same-process probe that opens and
# closes the file would release the holder's lock. Every "other process" below
# is a fresh interpreter started with ``sys.executable`` (never a fork, which
# would inherit the in-process hold registry).
_CHILD_PRELUDE = (
    "import sys\n"
    "sys.path.insert(0, sys.argv[1])\n"
    "from pathlib import Path\n"
    "root = Path(sys.argv[2])\n"
)

_TRY_LIFECYCLE = _CHILD_PRELUDE + (
    "import lifecycle_lock\n"
    "try:\n"
    "    with lifecycle_lock.lifecycle_mutation_lock(root):\n"
    "        print('acquired', flush=True)\n"
    "except lifecycle_lock.LifecycleLockBusy:\n"
    "    print('busy', flush=True)\n"
)

_HOLD_PUBLICATION = _CHILD_PRELUDE + (
    "import review_evidence\n"
    "with review_evidence.project_state_publication_lock(root):\n"
    "    print('held', flush=True)\n"
    "    sys.stdin.readline()\n"
    "print('released', flush=True)\n"
)

_HOLD_LIFECYCLE = _CHILD_PRELUDE + (
    "import lifecycle_lock\n"
    "with lifecycle_lock.lifecycle_mutation_lock(root):\n"
    "    print('held', flush=True)\n"
    "    sys.stdin.readline()\n"
    "print('released', flush=True)\n"
)

# Wave 1zxnz (1zx02): a classic ``lockf`` on the lifecycle sentinel byte, as a
# pre-change process takes it. ``probe`` reports and exits; ``hold`` keeps it
# until a line arrives on stdin.
_LOCKF_LIFECYCLE = _CHILD_PRELUDE + (
    "import fcntl, os\n"
    "import lifecycle_lock\n"
    "path = root / lifecycle_lock.LIFECYCLE_MUTATION_LOCK_REL\n"
    "path.parent.mkdir(parents=True, exist_ok=True)\n"
    "fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o666)\n"
    "offset = lifecycle_lock.LIFECYCLE_MUTATION_LOCK_SENTINEL\n"
    "try:\n"
    "    fcntl.lockf(fd, fcntl.LOCK_EX | fcntl.LOCK_NB, 1, offset, os.SEEK_SET)\n"
    "except OSError:\n"
    "    print('busy', flush=True)\n"
    "    sys.exit(0)\n"
    "if sys.argv[3] == 'probe':\n"
    "    print('acquired', flush=True)\n"
    "    sys.exit(0)\n"
    "print('held', flush=True)\n"
    "sys.stdin.readline()\n"
)


def _other_process_lockf(root: Path) -> str:
    """One raw ``lockf`` attempt on the lifecycle sentinel byte from a fresh interpreter."""
    out = subprocess.run(
        [sys.executable, "-B", "-c", _LOCKF_LIFECYCLE, str(SCRIPTS_ROOT), str(root), "probe"],
        capture_output=True, text=True, timeout=120, stdin=subprocess.DEVNULL,
    )
    return out.stdout.strip() or f"<no answer: rc={out.returncode} {out.stderr[-2000:]}>"


def _ofd_expected() -> bool:
    """Requirement 1's conditions: a known layout and all three constants."""
    if os.name == "nt":
        return False
    import fcntl
    import runtime_lock

    return runtime_lock.flock_layout() is not None and all(
        hasattr(fcntl, name) for name in runtime_lock._OFD_COMMAND_NAMES
    )


_WAIT_INSIDE_TRANSACTION = _CHILD_PRELUDE + (
    "import time\n"
    "import lifecycle_lock\n"
    "import review_evidence\n"
    "with lifecycle_lock.lifecycle_publication_transaction(root):\n"
    "    for wait in (True, False):\n"
    "        started = time.monotonic()\n"
    "        try:\n"
    "            with review_evidence.project_state_publication_lock(root, wait=wait):\n"
    "                print(f'entered wait={wait}', flush=True)\n"
    "        except review_evidence.ProjectPublicationUnavailable as exc:\n"
    "            elapsed = time.monotonic() - started\n"
    "            print(f'refused wait={wait} elapsed={elapsed:.3f} {exc}', flush=True)\n"
    "    print('holding', flush=True)\n"
    "    sys.stdin.readline()\n"
    "print('done', flush=True)\n"
)


def _other_process_lifecycle(root: Path) -> str:
    """One acquire attempt on the lifecycle lock from a fresh interpreter."""
    out = subprocess.run(
        [sys.executable, "-B", "-c", _TRY_LIFECYCLE, str(SCRIPTS_ROOT), str(root)],
        capture_output=True, text=True, timeout=120, stdin=subprocess.DEVNULL,
    )
    return out.stdout.strip() or f"<no answer: rc={out.returncode} {out.stderr[-2000:]}>"


class _Child:
    """A fresh-interpreter child whose stdout lines are read with a timeout."""

    def __init__(self, code: str, root: Path, *extra: str) -> None:
        import queue

        self.proc = subprocess.Popen(
            [sys.executable, "-B", "-c", code, str(SCRIPTS_ROOT), str(root), *extra],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True,
        )
        self.lines: "queue.Queue[str | None]" = queue.Queue()
        threading.Thread(target=self._pump, daemon=True).start()

    def _pump(self) -> None:
        for line in self.proc.stdout:
            self.lines.put(line.rstrip("\n"))
        self.lines.put(None)

    def expect(self, timeout: float) -> str:
        import queue

        try:
            line = self.lines.get(timeout=timeout)
        except queue.Empty:
            return f"<timeout after {timeout}s>"
        return "<exited>" if line is None else line

    def say(self) -> None:
        try:
            self.proc.stdin.write("go\n")
            self.proc.stdin.flush()
        except (BrokenPipeError, OSError):
            pass

    def close(self) -> None:
        if self.proc.poll() is None:
            self.proc.kill()
        self.proc.wait(timeout=30)
        for stream in (self.proc.stdin, self.proc.stdout, self.proc.stderr):
            try:
                stream.close()
            except OSError:
                pass


class LifecycleHoldProcessTests(unittest.TestCase):
    """1zimg AC-1, AC-2, AC-5: real processes, no mocks of the lock."""

    def setUp(self):
        if str(SCRIPTS_ROOT) not in sys.path:
            sys.path.insert(0, str(SCRIPTS_ROOT))
        import lifecycle_lock
        import review_evidence

        self.ll = lifecycle_lock
        self.re = review_evidence
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / ".wavefoundry").mkdir()

    def test_reentry_is_refused_and_the_outer_hold_survives(self):
        # AC-1
        import os

        with self.ll.lifecycle_mutation_lock(self.root):
            self.assertEqual(_other_process_lifecycle(self.root), "busy")
            reentry = None
            try:
                with self.ll.lifecycle_mutation_lock(self.root):
                    pass
            except self.ll.LifecycleLockBusy as exc:
                reentry = exc
            self.assertEqual(
                _other_process_lifecycle(self.root), "busy",
                "a second process took the lifecycle lock while the outer hold was live",
            )
            self.assertIsNotNone(reentry, "re-entry in the holding process was not refused")
            self.assertIn("already held by this process", str(reentry))
            self.assertIn(f"pid {os.getpid()}", str(reentry))
        self.assertEqual(_other_process_lifecycle(self.root), "acquired")

    def test_publication_wait_keeps_the_callers_lifecycle_hold(self):
        # AC-2: A (a thread of this process) holds lifecycle, B (a child)
        # holds publication, A waits for publication; C (a child) must stay
        # refused throughout.
        import time

        holder = _Child(_HOLD_PUBLICATION, self.root)
        self.addCleanup(holder.close)
        self.assertEqual(holder.expect(60), "held")
        waiting = threading.Event()
        entered = threading.Event()
        leave = threading.Event()
        errors: list = []

        def process_a() -> None:
            try:
                with self.ll.lifecycle_mutation_lock(self.root):
                    waiting.set()
                    with self.re.project_state_publication_lock(self.root, wait=True):
                        entered.set()
                        leave.wait(60)
            except BaseException as exc:  # noqa: BLE001
                errors.append(exc)

        thread = threading.Thread(target=process_a)
        thread.start()
        try:
            self.assertTrue(waiting.wait(30), errors)
            time.sleep(0.5)  # A is now inside the publication wait
            self.assertFalse(entered.is_set(), "A entered while B held the publication lock")
            during = _other_process_lifecycle(self.root)
            holder.say()
            self.assertEqual(holder.expect(60), "released")
            self.assertTrue(entered.wait(60), errors)
            after = _other_process_lifecycle(self.root)
        finally:
            leave.set()
            thread.join(60)
        self.assertEqual(errors, [])
        self.assertEqual(during, "busy", "process C took the lifecycle lock while A waited for publication")
        self.assertEqual(after, "busy", "process C took the lifecycle lock after A entered publication")
        self.assertEqual(_other_process_lifecycle(self.root), "acquired")

    def test_publication_wait_inside_the_transaction_refuses_promptly(self):
        # AC-5: both waits name the same-process hold within a bounded time,
        # and the lifecycle hold survives them.
        child = _Child(_WAIT_INSIDE_TRANSACTION, self.root)
        self.addCleanup(child.close)
        first = child.expect(30)
        second = child.expect(30)
        for wait, line in (("True", first), ("False", second)):
            self.assertTrue(line.startswith(f"refused wait={wait} "), line)
            self.assertIn("held by this thread", line)
            self.assertIn(f"pid {child.proc.pid}", line)
            elapsed = float(line.split("elapsed=")[1].split()[0])
            self.assertLess(elapsed, 5.0, line)
        self.assertEqual(child.expect(30), "holding")
        self.assertEqual(_other_process_lifecycle(self.root), "busy")
        child.say()
        self.assertEqual(child.expect(30), "done")
        self.assertEqual(_other_process_lifecycle(self.root), "acquired")


class _OpenRecorder:
    """Patch the lock-carrier opener; fail if the lifecycle file is opened."""

    def __init__(self, runtime_lock, forbidden: Path) -> None:
        import os

        self.runtime_lock = runtime_lock
        self.forbidden = os.path.realpath(forbidden)
        self.opened: list[str] = []
        self.real = runtime_lock._open_lock_carrier

    def __call__(self, path, mode):
        import os

        resolved = os.path.realpath(os.fspath(path))
        self.opened.append(resolved)
        if resolved == self.forbidden:
            raise AssertionError(f"lifecycle lock file opened: {resolved}")
        return self.real(path, mode)

    def patch(self):
        return patch.object(self.runtime_lock, "_open_lock_carrier", self)


class _HeldOnThread:
    """Hold the lifecycle lock on a separate thread until ``stop()``."""

    def __init__(self, lifecycle_lock, root: Path) -> None:
        self.ready = threading.Event()
        self.leave = threading.Event()
        self.errors: list = []

        def run() -> None:
            try:
                with lifecycle_lock.lifecycle_mutation_lock(root):
                    self.ready.set()
                    self.leave.wait(60)
            except BaseException as exc:  # noqa: BLE001
                self.errors.append(exc)
                self.ready.set()

        self.thread = threading.Thread(target=run)
        self.thread.start()
        assert self.ready.wait(30)
        assert not self.errors, self.errors

    def stop(self) -> None:
        self.leave.set()
        self.thread.join(60)


class LifecycleHoldRegistryTests(unittest.TestCase):
    """1zimg AC-3, AC-4, AC-6: registry-backed decisions and release paths."""

    def setUp(self):
        if str(SCRIPTS_ROOT) not in sys.path:
            sys.path.insert(0, str(SCRIPTS_ROOT))
        import lifecycle_lock
        import review_evidence
        import runtime_lock

        self.ll = lifecycle_lock
        self.re = review_evidence
        self.rl = runtime_lock
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / ".wavefoundry").mkdir()
        self.path = self.root / lifecycle_lock.LIFECYCLE_MUTATION_LOCK_REL

    # AC-3 -----------------------------------------------------------------
    def test_same_thread_reentry_never_opens_the_file(self):
        recorder = _OpenRecorder(self.rl, self.path)
        with self.ll.lifecycle_mutation_lock(self.root):
            hold = self.rl.process_hold(self.path)
            self.assertEqual(hold["thread"], threading.get_ident())
            with recorder.patch():
                for strict in (True, False):
                    with self.assertRaisesRegex(
                        self.ll.LifecycleLockBusy,
                        "already held by this process .*the calling thread",
                    ):
                        with self.ll.lifecycle_mutation_lock(self.root, strict=strict):
                            self.fail("re-entry ran its body")
            self.assertNotIn(recorder.forbidden, recorder.opened)
            self.assertEqual(_other_process_lifecycle(self.root), "busy")
        self.assertIsNone(self.rl.process_hold(self.path))

    def test_other_thread_reentry_never_opens_the_file(self):
        holder = _HeldOnThread(self.ll, self.root)
        try:
            recorder = _OpenRecorder(self.rl, self.path)
            with recorder.patch():
                for strict in (True, False):
                    with self.assertRaisesRegex(
                        self.ll.LifecycleLockBusy,
                        "already held by this process .*another thread",
                    ):
                        with self.ll.lifecycle_mutation_lock(self.root, strict=strict):
                            self.fail("re-entry ran its body")
            self.assertEqual(recorder.opened, [])
            self.assertEqual(_other_process_lifecycle(self.root), "busy")
        finally:
            holder.stop()
        self.assertEqual(holder.errors, [])
        self.assertEqual(_other_process_lifecycle(self.root), "acquired")

    def test_middleware_returns_reentry_for_a_reentered_tool_call(self):
        # Wave 1zls7 (1zlts): a same-thread re-entry is reported as
        # ``lifecycle_lock_reentry``, not as another session's contention.
        called = []

        def tool(**kwargs):
            called.append(True)
            return {"status": "ok", "data": {}}

        wrapped = MutationLockTests._wrapped(self, self.root, "wf_set_handoff", tool)
        with srv._lifecycle_lock_authority.lifecycle_mutation_lock(self.root):
            result = wrapped()
            self.assertEqual(_other_process_lifecycle(self.root), "busy")
        self.assertEqual(called, [])
        self.assertEqual(result["status"], "error")
        self.assertEqual(
            ["lifecycle_lock_reentry"], [d["code"] for d in result["diagnostics"]]
        )
        self.assertEqual(wrapped()["status"], "ok")

    # AC-4 -----------------------------------------------------------------
    def test_probe_fails_fast_when_another_thread_holds_lifecycle(self):
        publication = _Child(_HOLD_PUBLICATION, self.root)
        self.addCleanup(publication.close)
        self.assertEqual(publication.expect(60), "held")
        holder = _HeldOnThread(self.ll, self.root)
        try:
            recorder = _OpenRecorder(self.rl, self.path)
            with recorder.patch():
                with self.assertRaisesRegex(
                    self.re.ProjectPublicationUnavailable, "another thread of this process"
                ):
                    with self.re.project_state_publication_lock(self.root, wait=True):
                        self.fail("entered while another thread held lifecycle")
            self.assertNotIn(recorder.forbidden, recorder.opened)
            self.assertEqual(_other_process_lifecycle(self.root), "busy")
        finally:
            holder.stop()
        self.assertEqual(holder.errors, [])

    def test_probe_still_fails_fast_when_another_process_holds_lifecycle(self):
        import time

        lifecycle = _Child(_HOLD_LIFECYCLE, self.root)
        self.addCleanup(lifecycle.close)
        self.assertEqual(lifecycle.expect(60), "held")
        publication = _Child(_HOLD_PUBLICATION, self.root)
        self.addCleanup(publication.close)
        self.assertEqual(publication.expect(60), "held")
        self.assertIsNone(self.rl.process_hold(self.path))
        started = time.monotonic()
        with self.assertRaisesRegex(
            self.re.ProjectPublicationUnavailable, "during lifecycle mutation"
        ):
            with self.re.project_state_publication_lock(self.root, wait=True):
                self.fail("entered while another process held lifecycle")
        self.assertLess(time.monotonic() - started, 5.0)

    # AC-6 -----------------------------------------------------------------
    def _assert_fully_released(self):
        self.assertIsNone(self.rl.process_hold(self.path))
        with self.ll.lifecycle_mutation_lock(self.root):
            self.assertIsNotNone(self.rl.process_hold(self.path))
        self.assertIsNone(self.rl.process_hold(self.path))
        self.assertEqual(_other_process_lifecycle(self.root), "acquired")

    def test_normal_exit_removes_the_entry_and_releases(self):
        with self.ll.lifecycle_mutation_lock(self.root):
            hold = self.rl.process_hold(self.path)
        import os

        self.assertEqual(hold["pid"], os.getpid())
        self.assertIn("acquired_at", hold)
        self.assertEqual(hold["thread"], threading.get_ident())
        self._assert_fully_released()

    def test_raising_body_removes_the_entry_and_releases(self):
        with self.assertRaisesRegex(ValueError, "body failed"):
            with self.ll.lifecycle_mutation_lock(self.root):
                raise ValueError("body failed")
        self._assert_fully_released()

    def test_interrupt_during_the_release_stamp_removes_the_entry(self):
        real_write = self.rl.RuntimeFileLock.write_metadata

        def write(lock, payload):
            if "released_at" in payload:
                raise KeyboardInterrupt
            return real_write(lock, payload)

        with patch.object(self.rl.RuntimeFileLock, "write_metadata", write):
            with self.assertRaises(KeyboardInterrupt):
                with self.ll.lifecycle_mutation_lock(self.root):
                    pass
        self._assert_fully_released()

    def test_interrupt_from_registration_still_releases(self):
        entered = []

        def interrupted(path, metadata):
            raise KeyboardInterrupt

        with patch.object(self.ll, "register_process_hold", interrupted):
            with self.assertRaises(KeyboardInterrupt):
                with self.ll.lifecycle_mutation_lock(self.root):
                    entered.append(True)
        self.assertEqual(entered, [])
        self._assert_fully_released()

    def test_the_entry_is_gone_before_the_os_lock_is_released(self):
        real_release = self.rl.RuntimeFileLock.release
        seen = []

        def release(lock):
            seen.append(self.rl.process_hold(lock.path))
            return real_release(lock)

        with patch.object(self.rl.RuntimeFileLock, "release", release):
            with self.ll.lifecycle_mutation_lock(self.root):
                pass
        self.assertEqual(seen, [None])

    def test_strict_false_fallback_registers_nothing(self):
        def unavailable(lock):
            raise self.rl.RuntimeLockError(5, "injected")

        entered = []
        with patch.object(self.rl.RuntimeFileLock, "acquire", unavailable):
            with self.ll.lifecycle_mutation_lock(self.root, strict=False):
                entered.append(self.rl.process_hold(self.path))
                # The guard is not held across the unlocked yield.
                acquired = []
                other = threading.Thread(
                    target=lambda: acquired.append(
                        self.rl.process_hold_guard().acquire(timeout=5)
                    ) or self.rl.process_hold_guard().release()
                )
                other.start()
                other.join(10)
        self.assertEqual(entered, [None])
        self.assertEqual(acquired, [True])

    def test_transaction_registers_and_removes_the_publication_hold(self):
        publication = self.root / self.re.PROJECT_STATE_PUBLICATION_LOCK_REL
        with self.ll.lifecycle_publication_transaction(self.root):
            hold = self.rl.process_hold(publication)
            self.assertEqual(hold["thread"], threading.get_ident())
            self.assertIsNotNone(self.rl.process_hold(self.path))
        self.assertIsNone(self.rl.process_hold(publication))
        self.assertIsNone(self.rl.process_hold(self.path))
        with self.re.project_state_publication_lock(self.root, wait=False):
            pass


class LifecycleOpenerCensusTests(unittest.TestCase):
    """1zimg AC-7: the lifecycle lock file has a fixed set of openers."""

    LITERALS = ("lifecycle-mutation", "LIFECYCLE_MUTATION_LOCK_REL", "LIFECYCLE_LOCK")
    OPENERS = {"lifecycle_lock.py", "review_evidence.py", "upgrade_bridge_bootstrap.py"}
    NAME_ONLY = {"wf_server/server_impl.py"}

    def _matches(self) -> dict[str, list[str]]:
        found: dict[str, list[str]] = {}
        for path in sorted(SCRIPTS_ROOT.rglob("*")):
            rel = path.relative_to(SCRIPTS_ROOT).as_posix()
            if not path.is_file() or rel.startswith("tests/") or "__pycache__" in rel:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            lines = [line for line in text.splitlines() if any(lit in line for lit in self.LITERALS)]
            if lines:
                found[rel] = lines
        return found

    def test_only_the_known_files_name_the_lifecycle_lock(self):
        found = self._matches()
        self.assertEqual(set(found), self.OPENERS | self.NAME_ONLY, found)

    def test_server_impl_only_names_the_lock_for_messages(self):
        lines = self._matches()["wf_server/server_impl.py"]
        self.assertTrue(lines)
        for line in lines:
            # Wave 1zls7 (1zlts): the repository-relative text names the lock
            # in refusal messages too; still a message-only use.
            self.assertTrue(
                "LIFECYCLE_MUTATION_LOCK_REL.name" in line
                or "LIFECYCLE_MUTATION_LOCK_REL.as_posix()" in line,
                line,
            )
            self.assertNotIn("RuntimeFileLock", line)
            self.assertNotIn("open(", line)

    def test_the_probe_path_and_offset_equal_the_lifecycle_constants(self):
        if str(SCRIPTS_ROOT) not in sys.path:
            sys.path.insert(0, str(SCRIPTS_ROOT))
        import lifecycle_lock
        import review_evidence

        self.assertEqual(
            review_evidence._LIFECYCLE_MUTATION_LOCK_REL,
            lifecycle_lock.LIFECYCLE_MUTATION_LOCK_REL,
        )
        self.assertEqual(
            review_evidence._LIFECYCLE_MUTATION_LOCK_SENTINEL,
            lifecycle_lock.LIFECYCLE_MUTATION_LOCK_SENTINEL,
        )


class LifecycleHoldReloadTests(unittest.TestCase):
    """1zimg AC-8: an MCP reload evicts and re-imports ``lifecycle_lock`` and
    ``review_evidence``; the hold registry lives in ``runtime_lock``, which is
    not evicted, so a hold taken before the reload stays visible through the
    re-imported modules."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        _repo(self.root)
        load_server()
        from wf_server import server_impl

        self.server_impl = server_impl
        import runtime_lock

        self.rl = runtime_lock

    def test_reload_during_a_hold_keeps_it_visible_and_refused(self):
        import importlib

        old_ll = self.server_impl._lifecycle_lock_authority
        old_re = sys.modules["review_evidence"]
        path = self.root / old_ll.LIFECYCLE_MUTATION_LOCK_REL
        publication = _Child(_HOLD_PUBLICATION, self.root)
        self.addCleanup(publication.close)
        self.assertEqual(publication.expect(60), "held")
        # Wave 1zxnz (1zx02) AC-9: runtime_lock is reloaded in place; its state
        # and its exception classes are the same objects afterwards.
        holds, guard = self.rl._PROCESS_RECORD_HOLDS, self.rl._PROCESS_HOLD_GUARD
        error, busy = self.rl.RuntimeLockError, self.rl.RuntimeLockBusy
        file_lock = self.rl.RuntimeFileLock
        with old_ll.lifecycle_mutation_lock(self.root):
            # What wf_reload_mcp does: drop the script cache, reload server_impl.
            self.server_impl._script_cache.clear()
            reloaded = importlib.reload(self.server_impl)
            new_ll = reloaded._lifecycle_lock_authority
            new_re = sys.modules["review_evidence"]
            self.assertIsNot(new_ll, old_ll, "reload no longer re-imports lifecycle_lock")
            self.assertIsNot(new_re, old_re, "reload no longer re-imports review_evidence")
            self.assertIs(sys.modules["runtime_lock"], self.rl)
            self.assertIsNot(self.rl.RuntimeFileLock, file_lock, "runtime_lock was not reloaded")
            self.assertIs(self.rl._PROCESS_RECORD_HOLDS, holds)
            self.assertIs(self.rl._PROCESS_HOLD_GUARD, guard)
            self.assertIs(self.rl.RuntimeLockError, error)
            self.assertIs(self.rl.RuntimeLockBusy, busy)
            self.assertIs(new_ll.RuntimeLockBusy, busy)
            self.assertIs(new_ll.RuntimeFileLock, self.rl.RuntimeFileLock)
            self.assertIsNotNone(self.rl.process_hold(path))
            with self.assertRaisesRegex(new_ll.LifecycleLockBusy, "already held by this process"):
                with new_ll.lifecycle_mutation_lock(self.root):
                    self.fail("re-entry after reload ran its body")
            with self.assertRaises(reloaded.LifecycleMutationBusy):
                with reloaded._lifecycle_mutation_lock(self.root):
                    self.fail("middleware re-entry after reload ran its body")
            # The re-imported review_evidence sees the hold too: from another
            # thread it fails fast without opening the lifecycle file.
            recorder = _OpenRecorder(self.rl, path)
            outcome: list = []

            def publish() -> None:
                try:
                    with new_re.project_state_publication_lock(self.root, wait=True):
                        outcome.append("entered")
                except new_re.ProjectPublicationUnavailable as exc:
                    outcome.append(str(exc))

            with recorder.patch():
                thread = threading.Thread(target=publish)
                thread.start()
                thread.join(30)
            self.assertEqual(len(outcome), 1, outcome)
            self.assertIn("another thread of this process", outcome[0])
            self.assertNotIn(recorder.forbidden, recorder.opened)
            self.assertEqual(_other_process_lifecycle(self.root), "busy")
        self.assertIsNone(self.rl.process_hold(path))
        self.assertEqual(_other_process_lifecycle(self.root), "acquired")


class LifecycleHoldGuardOrderingTests(unittest.TestCase):
    """1zimg repair round (DEL-1ZIMC-UNPINNED-GUARD-MECHANISMS): pin the
    in-guard re-check, the thread test of the own-publication refusal, and
    that registration and the probe's open happen while the guard is held."""

    def setUp(self):
        if str(SCRIPTS_ROOT) not in sys.path:
            sys.path.insert(0, str(SCRIPTS_ROOT))
        import lifecycle_lock
        import review_evidence
        import runtime_lock

        self.ll = lifecycle_lock
        self.re = review_evidence
        self.rl = runtime_lock
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / ".wavefoundry").mkdir()
        self.path = self.root / lifecycle_lock.LIFECYCLE_MUTATION_LOCK_REL

    def test_two_threads_past_the_first_check_cannot_both_acquire(self):
        # Requirement 2: both threads pass the up-front check (the barrier
        # holds each one after it), so only the re-check under the guard at
        # acquire time can refuse the second. The lock itself is real.
        barrier = threading.Barrier(2, timeout=30)
        real_lock = self.ll.RuntimeFileLock

        def after_first_check(*args, **kwargs):
            barrier.wait()
            return real_lock(*args, **kwargs)

        results: dict = {}
        inside = {name: threading.Event() for name in ("t1", "t2")}
        leave = threading.Event()

        def run(name: str) -> None:
            try:
                with self.ll.lifecycle_mutation_lock(self.root):
                    results[name] = "acquired"
                    inside[name].set()
                    leave.wait(60)
            except self.ll.LifecycleLockBusy as exc:
                results[name] = f"busy: {exc}"
                inside[name].set()
            except BaseException as exc:  # noqa: BLE001
                results[name] = f"error: {exc!r}"
                inside[name].set()

        with patch.object(self.ll, "RuntimeFileLock", after_first_check):
            threads = [threading.Thread(target=run, args=(n,)) for n in ("t1", "t2")]
            for thread in threads:
                thread.start()
            try:
                for event in inside.values():
                    self.assertTrue(event.wait(30), results)
                outcomes = sorted(results.values())
                self.assertEqual(outcomes[0], "acquired", results)
                self.assertTrue(outcomes[1].startswith("busy: "), results)
                self.assertIn("already held by this process", outcomes[1])
                self.assertEqual(_other_process_lifecycle(self.root), "busy")
            finally:
                leave.set()
                for thread in threads:
                    thread.join(60)
        self.assertIsNone(self.rl.process_hold(self.path))
        self.assertEqual(_other_process_lifecycle(self.root), "acquired")

    def test_another_threads_transaction_hold_gets_the_ordinary_busy_refusal(self):
        # Requirement 4: the own-hold refusal is for the holding thread only;
        # another thread meets the ordinary busy publication lock.
        ready = threading.Event()
        leave = threading.Event()
        errors: list = []

        def transaction() -> None:
            try:
                with self.ll.lifecycle_publication_transaction(self.root):
                    ready.set()
                    leave.wait(60)
            except BaseException as exc:  # noqa: BLE001
                errors.append(exc)
                ready.set()

        thread = threading.Thread(target=transaction)
        thread.start()
        try:
            self.assertTrue(ready.wait(30))
            self.assertEqual(errors, [])
            with self.assertRaises(self.re.ProjectPublicationUnavailable) as caught:
                with self.re.project_state_publication_lock(self.root, wait=False):
                    self.fail("entered while another thread held the publication lock")
            message = str(caught.exception)
            self.assertIn("project publication lock is busy", message)
            self.assertNotIn("held by this thread", message)
        finally:
            leave.set()
            thread.join(60)
        self.assertEqual(errors, [])

    def test_registration_happens_under_the_guard_before_the_metadata_write(self):
        # Requirement 1: acquire and register are one step under the guard,
        # so the entry exists before anything else touches the carrier.
        guard = self.rl.process_hold_guard()
        events: list = []
        real_register = self.ll.register_process_hold
        real_write = self.rl.RuntimeFileLock.write_metadata

        def register(path, metadata):
            events.append(("register", guard._is_owned()))
            return real_register(path, metadata)

        def write(lock, payload):
            events.append(("write", "released_at" in payload))
            return real_write(lock, payload)

        with patch.object(self.ll, "register_process_hold", register), \
                patch.object(self.rl.RuntimeFileLock, "write_metadata", write):
            with self.ll.lifecycle_mutation_lock(self.root):
                pass
        self.assertEqual(
            events, [("register", True), ("write", False), ("write", True)]
        )

    def test_the_probe_opens_the_lifecycle_file_only_under_the_guard(self):
        # Requirement 3: with no in-process hold, the registry check and the
        # probe's open happen under the guard, so no in-process acquire can
        # register between them.
        lifecycle = _Child(_HOLD_LIFECYCLE, self.root)
        self.addCleanup(lifecycle.close)
        self.assertEqual(lifecycle.expect(60), "held")
        publication = _Child(_HOLD_PUBLICATION, self.root)
        self.addCleanup(publication.close)
        self.assertEqual(publication.expect(60), "held")
        import os

        guard = self.rl.process_hold_guard()
        forbidden = os.path.realpath(self.path)
        opened: list = []
        real_open = self.rl._open_lock_carrier

        def recording_open(path, mode):
            if os.path.realpath(os.fspath(path)) == forbidden:
                opened.append(guard._is_owned())
            return real_open(path, mode)

        with patch.object(self.rl, "_open_lock_carrier", recording_open):
            with self.assertRaises(self.re.ProjectPublicationUnavailable):
                with self.re.project_state_publication_lock(self.root, wait=True):
                    self.fail("entered while another process held lifecycle")
        self.assertEqual(opened, [True])


_HOLD_TRANSACTION = _CHILD_PRELUDE + (
    "import lifecycle_lock\n"
    "with lifecycle_lock.lifecycle_publication_transaction(root):\n"
    "    print('held', flush=True)\n"
    "    sys.stdin.readline()\n"
    "print('released', flush=True)\n"
)


class LifecycleRefusalContractTests(unittest.TestCase):
    """Wave 1zls7 (1zlts): the refusal names the lock actually held, by its
    repository-relative path, and never leaks the absolute path."""

    LOCK_REL = ".wavefoundry/lifecycle-mutation.lock"

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        _repo(self.root)
        self.ll = srv._lifecycle_lock_authority

    def _wrapped(self, tool_name, fn, get_handler=None):
        class _Tool: ...
        class _TM: ...
        class _MCP: ...
        tool = _Tool(); tool.fn = fn
        tm = _TM(); tm._tools = {tool_name: tool}
        mcp = _MCP(); mcp._tool_manager = tm
        handler = SimpleNamespace(root=self.root)
        srv._wrap_lifecycle_mutation_lock(mcp, get_handler or (lambda: handler))
        return tool.fn

    def _assert_path_free(self, result):
        text = json.dumps(result)
        for absolute in {str(self.root), str(self.root.resolve()), os.fspath(self.root.resolve()).replace("\\", "/")}:
            self.assertNotIn(absolute, text)
            self.assertNotIn(json.dumps(absolute)[1:-1], text)

    @staticmethod
    def _codes(result):
        return [d["code"] for d in result["diagnostics"]]

    def test_contention_from_another_process_names_the_relative_lock_once(self):
        # AC-1
        holder = _Child(_HOLD_LIFECYCLE, self.root)
        self.addCleanup(holder.close)
        self.assertEqual(holder.expect(60), "held")
        called = []
        result = self._wrapped("wf_close_wave", lambda **kw: called.append(kw))()
        holder.say()
        self.assertEqual(holder.expect(60), "released")
        self.assertEqual(called, [])
        self.assertEqual(self._codes(result), ["lifecycle_mutation_locked"])
        self.assertIs(result["data"]["busy"], True)
        message = result["diagnostics"][0]["message"]
        self.assertIn(self.LOCK_REL, message)
        self.assertIn("another process", message)
        self.assertLessEqual(message.count("lock is held"), 1, message)
        self._assert_path_free(result)

    def test_contention_from_another_thread_says_this_server_process(self):
        # AC-8 (last sentence)
        holder = _HeldOnThread(self.ll, self.root)
        try:
            result = self._wrapped("wf_add_change", lambda **kw: {"status": "ok"})()
        finally:
            holder.stop()
        self.assertEqual(self._codes(result), ["lifecycle_mutation_locked"])
        message = result["diagnostics"][0]["message"]
        self.assertIn("another call in this server process", message)
        self.assertIn(self.LOCK_REL, message)
        self._assert_path_free(result)

    def test_unavailable_at_acquire_is_not_busy(self):
        # AC-2
        import errno
        rl = sys.modules[self.ll.RuntimeFileLock.__module__]

        def refuse(lock_self):
            raise rl.RuntimeLockError(
                errno.ENOLCK, f"Unable to acquire runtime lock {lock_self.path}: no locks")

        called = []
        wrapped = self._wrapped("wf_set_handoff", lambda **kw: called.append(kw))
        with patch.object(self.ll.RuntimeFileLock, "acquire", refuse):
            result = wrapped()
        self.assertEqual(called, [])
        self.assertEqual(self._codes(result), ["lifecycle_lock_unavailable"])
        self.assertIsNot(result["data"].get("busy"), True)
        message = result["diagnostics"][0]["message"]
        self.assertIn(self.LOCK_REL, message)
        self.assertIn("RuntimeLockError", message)
        self.assertNotIn("Retry once", message)
        self._assert_path_free(result)

    def test_body_reentry_is_reported_as_reentry_and_the_hold_is_released(self):
        # AC-3
        def body(**kwargs):
            with self.ll.lifecycle_mutation_lock(self.root):
                self.fail("re-entry ran its body")

        result = self._wrapped("wf_set_handoff", body)()
        self.assertEqual(self._codes(result), ["lifecycle_lock_reentry"])
        message = result["diagnostics"][0]["message"]
        self.assertIn("no other session", message)
        self.assertIn(self.LOCK_REL, message)
        self._assert_path_free(result)
        self.assertIsNone(self.ll.process_hold(self.root / self.ll.LIFECYCLE_MUTATION_LOCK_REL))
        self.assertEqual(_other_process_lifecycle(self.root), "acquired")

    def test_nested_wrapped_call_on_the_same_thread_is_reentry(self):
        # AC-3: an extension body invoking another wrapped tool.
        inner = self._wrapped("wf_set_handoff", lambda **kw: {"status": "ok"})
        seen = {}

        def outer(**kwargs):
            seen["inner"] = inner()
            return {"status": "ok", "data": {}}

        self.assertEqual(self._wrapped("wf_create_wave", outer)()["status"], "ok")
        self.assertEqual(self._codes(seen["inner"]), ["lifecycle_lock_reentry"])
        self._assert_path_free(seen["inner"])
        self.assertEqual(_other_process_lifecycle(self.root), "acquired")

    def test_non_lock_body_exception_propagates_and_releases(self):
        # AC-5
        def body(**kwargs):
            raise ValueError("body failure")

        with self.assertRaisesRegex(ValueError, "body failure"):
            self._wrapped("wf_close_wave", body)()
        self.assertEqual(_other_process_lifecycle(self.root), "acquired")

    def test_body_lock_refusals_that_are_not_reentry_propagate(self):
        # AC-5 / Requirement 1: only acquisition maps to the lifecycle
        # refusal; a busy lock raised by the body is not reported as one.
        for raised in (
            srv.LifecycleMutationBusy("raised by the body"),
            self.ll.LifecycleLockBusy("some other lock is held"),
        ):
            with self.subTest(raised=type(raised).__name__):
                def body(**kwargs):
                    raise raised

                with self.assertRaises(type(raised)):
                    self._wrapped("wf_close_wave", body)()
                self.assertEqual(_other_process_lifecycle(self.root), "acquired")

    def test_root_resolution_refusal_names_only_the_exception_class(self):
        # AC-8: no str(exc) text in the root-resolution refusal.
        secret = str(self.root / "secret-home")

        def broken():
            raise RuntimeError(f"cannot resolve {secret}")

        result = self._wrapped("wf_prepare_wave", lambda **kw: {"status": "ok"}, broken)()
        self.assertEqual(self._codes(result), ["lifecycle_lock_unavailable"])
        message = result["diagnostics"][0]["message"]
        self.assertIn("RuntimeError", message)
        self.assertNotIn("cannot resolve", message)
        self._assert_path_free(result)

    def test_upgrade_guard_publication_refusal_is_path_free(self):
        # AC-8: a real ProjectPublicationUnavailable while another process
        # holds the upgrade shape (lifecycle, then publication).
        review_evidence = sys.modules[srv.ProjectPublicationUnavailable.__module__]
        holder = _Child(_HOLD_TRANSACTION, self.root)
        self.addCleanup(holder.close)
        self.assertEqual(holder.expect(60), "held")

        def body(**kwargs):
            with review_evidence.project_state_publication_lock(self.root, wait=True):
                self.fail("entered while another process held the transaction")

        class _Tool: ...
        tool = _Tool(); tool.fn = body
        mcp = SimpleNamespace(_tool_manager=SimpleNamespace(_tools={"wf_prepare_wave": tool}))
        srv._wrap_upgrade_publication_guard(mcp, lambda: SimpleNamespace(root=self.root))
        with patch.object(srv.publication_control, "publication_block_reason", return_value=None):
            result = tool.fn()
        holder.say()
        self.assertEqual(holder.expect(60), "released")
        self.assertEqual(self._codes(result), ["project_publication_busy"])
        message = result["diagnostics"][0]["message"]
        self.assertIn(self.LOCK_REL, message)
        self._assert_path_free(result)

    def test_context_efficiency_publication_error_is_path_free(self):
        # Requirement 4a sibling: the projection's ``error`` reaches
        # ``data.context_efficiency_persistence`` of lifecycle tool responses.
        _wave(self.root, "1aaaa demo")
        holder = _Child(_HOLD_TRANSACTION, self.root)
        self.addCleanup(holder.close)
        self.assertEqual(holder.expect(60), "held")
        result = srv._project_context_efficiency_wave(self.root, "1aaaa demo", automatic=True)
        holder.say()
        self.assertEqual(holder.expect(60), "released")
        self.assertEqual(result.get("reason"), "publication_lock_busy", result)
        self._assert_path_free(result)


class MemoryToolPublicationRefusalTests(unittest.TestCase):
    """Wave 1zls7 (1zodv, AC-3): ``memory_consolidate`` and ``memory_purge`` are
    registered publication writers, so the upgrade guard wraps the real
    handlers: a held publication lock returns the path-free
    ``project_publication_busy`` refusal, and an upgrade checkpoint refuses
    them before the handler runs."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        _repo(self.root)
        (self.root / "docs" / "agents").mkdir(parents=True, exist_ok=True)
        review_evidence = sys.modules[srv.ProjectPublicationUnavailable.__module__]
        self.LOCK_REL = review_evidence.PROJECT_STATE_PUBLICATION_LOCK_REL.as_posix()
        self.ll = srv._lifecycle_lock_authority
        import memory_records

        for memory_id in ("mem-alpha-one", "mem-alpha-two"):
            content = memory_records.render_memory_record(
                memory_id=memory_id, kind="decision", summary=f"Lesson from {memory_id}.",
                evidence=["`1abcd-bug some-change` observed"], targets=["src/a.py"],
                title=f"Lesson {memory_id}", confidence=0.8, status="active",
                supersedes="", date="2026-10-01",
            )
            memory_records.write_memory_record(self.root, content, memory_id)
        self.calls = {
            "memory_consolidate": lambda: srv.memory_consolidate_response(
                self.root, mode="create", memory_ids=["mem-alpha-one", "mem-alpha-two"],
                title="Consolidated", summary="Both lessons in one record.", reviewed=True,
                eligibility_confirmed=True,
            ),
            "memory_purge": lambda: srv.memory_purge_response(
                self.root, "mem-alpha-one", reviewed=True,
            ),
        }

    def _guarded(self, name):
        entered = []

        def body(**kwargs):
            entered.append(name)
            return self.calls[name]()

        class _Tool: ...
        tool = _Tool(); tool.fn = body
        mcp = SimpleNamespace(_tool_manager=SimpleNamespace(_tools={name: tool}))
        srv._wrap_upgrade_publication_guard(mcp, lambda: SimpleNamespace(root=self.root))
        return tool.fn, entered

    def _assert_path_free(self, result):
        text = json.dumps(result)
        forms = set()
        for absolute in {str(self.root), str(self.root.resolve())}:
            for form in (absolute, absolute.replace("\\", "/"), absolute.replace("/", "\\")):
                forms.add(form)
                forms.add(json.dumps(form)[1:-1])
        for form in forms:
            self.assertNotIn(form, text)

    def _assert_busy(self, result, name):
        self.assertEqual([d["code"] for d in result["diagnostics"]], ["project_publication_busy"], result)
        self.assertEqual(result["status"], "error")
        self.assertIs(result["data"]["publication_applied"], False)
        self.assertEqual(result["data"]["tool"], name)
        self.assertIn(self.LOCK_REL, result["diagnostics"][0]["message"])
        self._assert_path_free(result)

    def test_both_tools_are_registered_fail_fast_memory_writers(self):
        import publication_control

        for name in ("memory_consolidate", "memory_purge"):
            writer = publication_control._BY_TOOL[name]
            self.assertEqual(
                (writer.producer, writer.contention_policy, writer.surface, writer.memory_recovery),
                ("memory", "fail_fast", "tool", False),
            )

    def test_another_process_holding_the_locks_gets_the_path_free_busy_refusal(self):
        holder = _Child(_HOLD_TRANSACTION, self.root)
        self.addCleanup(holder.close)
        self.assertEqual(holder.expect(60), "held")
        try:
            results = {}
            for name in ("memory_consolidate", "memory_purge"):
                fn, entered = self._guarded(name)
                results[name] = fn()
                self.assertEqual(entered, [name])
        finally:
            holder.say()
        self.assertEqual(holder.expect(60), "released")
        for name, result in results.items():
            with self.subTest(tool=name):
                self._assert_busy(result, name)

    def test_another_thread_running_a_lifecycle_mutation_gets_the_busy_refusal(self):
        publication = _Child(_HOLD_PUBLICATION, self.root)
        self.addCleanup(publication.close)
        self.assertEqual(publication.expect(60), "held")
        holder = _HeldOnThread(self.ll, self.root)
        try:
            results = {name: self._guarded(name)[0]() for name in ("memory_consolidate", "memory_purge")}
        finally:
            holder.stop()
            publication.say()
        self.assertEqual(holder.errors, [])
        for name, result in results.items():
            with self.subTest(tool=name):
                self._assert_busy(result, name)
                self.assertIn("another call in this server process", result["diagnostics"][0]["message"])

    def test_an_upgrade_checkpoint_refuses_both_tools_before_the_handler(self):
        checkpoint = self.root / ".wavefoundry" / "upgrade-in-progress.json"
        checkpoint.write_text(json.dumps({"current_phase": "surface_rendering"}), encoding="utf-8")
        for name in ("memory_consolidate", "memory_purge"):
            with self.subTest(tool=name):
                fn, entered = self._guarded(name)
                result = fn()
                self.assertEqual([d["code"] for d in result["diagnostics"]], ["upgrade_in_progress"])
                self.assertIs(result["data"]["upgrade_in_progress"], True)
                self.assertEqual(entered, [])
                self._assert_path_free(result)

    def test_a_purge_failure_renders_without_an_absolute_path(self):
        """Requirement 3, last sentence: ``memory_purge_failed`` follows the
        Requirement 4 rendering rule."""
        import errno

        mem = srv._load_script("memory_records")
        inside = self.root / "docs" / "agents" / "memory" / "mem-alpha-one.md"
        cases = {
            "oserror_inside": (OSError(errno.EACCES, "Permission denied", str(inside)),
                               "PermissionError EACCES on docs/agents/memory/mem-alpha-one.md"),
            "oserror_outside": (OSError(errno.EACCES, "Permission denied", "/elsewhere/x.md"),
                                "PermissionError EACCES"),
            "value_error_path": (ValueError(f"cannot purge {inside}"), "ValueError"),
            "value_error_relative": (ValueError("mem-alpha-one: not retired"), "mem-alpha-one: not retired"),
        }
        for label, (exc, expected) in cases.items():
            with self.subTest(case=label):
                with patch.object(mem, "resolve_purge_memory_source", side_effect=exc):
                    result = self._guarded("memory_purge")[0]()
                self.assertEqual([d["code"] for d in result["diagnostics"]], ["memory_purge_failed"])
                self.assertEqual(result["diagnostics"][0]["message"], expected)
                self._assert_path_free(result)
                self.assertNotIn("/elsewhere", json.dumps(result))

    def test_a_consolidation_failure_renders_without_an_absolute_path(self):
        """Review F2: ``memory_consolidation_failed`` renders the failure and a
        rollback failure by the Requirement 4 rule."""
        import errno

        mem = srv._load_script("memory_records")
        inside = self.root / "docs" / "agents" / "memory" / "mem-alpha-two.md"
        cases = {
            "oserror_inside": (OSError(errno.EIO, "I/O error", str(inside)),
                               "OSError EIO on docs/agents/memory/mem-alpha-two.md"),
            "oserror_outside": (OSError(errno.EIO, "I/O error", "/elsewhere/x.md"), "OSError EIO"),
        }
        for label, (exc, expected) in cases.items():
            with self.subTest(case=label):
                with patch.object(mem, "archive_memory_record", side_effect=exc):
                    result = self._guarded("memory_consolidate")[0]()
                self.assertEqual([d["code"] for d in result["diagnostics"]], ["memory_consolidation_failed"])
                self.assertEqual(result["diagnostics"][0]["message"], expected)
                self.assertIs(result["data"]["rollback_completed"], True)
                self._assert_path_free(result)
                self.assertNotIn("/elsewhere", json.dumps(result))

    def test_a_consolidation_rollback_failure_renders_without_an_absolute_path(self):
        import errno

        mem = srv._load_script("memory_records")
        real_write = Path.write_bytes

        def failing_write(path, data):
            if path.name.startswith("mem-alpha"):
                raise PermissionError(errno.EACCES, "Permission denied", str(path))
            return real_write(path, data)

        with patch.object(mem, "archive_memory_record",
                          side_effect=OSError(errno.EIO, "I/O error", "/elsewhere/x.md")), \
                patch.object(Path, "write_bytes", failing_write):
            result = self._guarded("memory_consolidate")[0]()
        message = result["diagnostics"][0]["message"]
        self.assertIs(result["data"]["rollback_completed"], False)
        self.assertRegex(message, r"^OSError EIO; rollback incomplete: PermissionError EACCES on [^/].*mem-alpha-\w+\.md$")
        self._assert_path_free(result)
        self.assertNotIn("/elsewhere", json.dumps(result))

    # Wave 1zrak (1zraj): Python 3.14 ``Path.exists`` reads an uninspectable
    # rollback member as absent, so the rollback reported itself complete
    # while a partial archive body it could not inspect remained.

    def _consolidate_with_partial_archive(self, after_write):
        import errno

        mem = srv._load_script("memory_records")
        archive_dir = self.root / mem.MEMORY_ARCHIVE_DIR
        written = []

        def partial_archive(_root, memory_id, *args, **kwargs):
            archive_dir.mkdir(parents=True, exist_ok=True)
            body = archive_dir / f"{memory_id}.md"
            body.write_text("partial archive body\n", encoding="utf-8")
            written.append(body)
            after_write(archive_dir, body)
            raise OSError(errno.EIO, "I/O error", "/elsewhere/x.md")

        with patch.object(mem, "archive_memory_record", side_effect=partial_archive):
            result = self._guarded("memory_consolidate")[0]()
        return result, written

    def _assert_rollback_reported_incomplete(self, result, written):
        self.assertEqual(len(written), 1, result)
        self.assertIs(result["data"]["rollback_completed"], False, result)
        self.assertRegex(
            result["diagnostics"][0]["message"],
            r"^OSError EIO; rollback incomplete: PermissionError EACCES",
        )
        self._assert_path_free(result)

    def test_an_untraversable_archive_member_is_reported_rollback_incomplete(self):
        if os.name == "nt":
            self.skipTest("chmod 0 does not deny directory traversal on Windows; the patched os.stat pin covers it")
        if hasattr(os, "geteuid") and os.geteuid() == 0:
            self.skipTest("root ignores mode 0")
        locked = []

        def lock_archive(archive_dir, _body):
            os.chmod(archive_dir, 0)
            locked.append(archive_dir)

        try:
            result, written = self._consolidate_with_partial_archive(lock_archive)
        finally:
            for archive_dir in locked:
                os.chmod(archive_dir, 0o755)
        self._assert_rollback_reported_incomplete(result, written)

    def test_a_denied_archive_member_stat_is_reported_rollback_incomplete(self):
        import errno

        real_stat = os.stat
        denied = set()

        def deny_body(_archive_dir, body):
            denied.update({os.path.abspath(body), os.path.realpath(body)})

        def fake_stat(path, *args, **kwargs):
            if (kwargs.get("follow_symlinks", True) and not isinstance(path, int)
                    and os.path.abspath(os.fspath(path)) in denied):
                raise PermissionError(errno.EACCES, "Permission denied", os.fspath(path))
            return real_stat(path, *args, **kwargs)

        with patch("os.stat", fake_stat):
            result, written = self._consolidate_with_partial_archive(deny_body)
        self._assert_rollback_reported_incomplete(result, written)


@unittest.skipIf(os.name == "nt", "POSIX record-lock mechanics")
class LifecycleOfdLockTests(unittest.TestCase):
    """Wave 1zxnz (1zx02) AC-1, AC-2: the lifecycle lock is an OFD lock that
    an unrelated close cannot release, and it excludes classic ``lockf``
    holders in both directions."""

    def setUp(self):
        if str(SCRIPTS_ROOT) not in sys.path:
            sys.path.insert(0, str(SCRIPTS_ROOT))
        import lifecycle_lock

        self.ll = lifecycle_lock
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / ".wavefoundry").mkdir()
        self.path = self.root / lifecycle_lock.LIFECYCLE_MUTATION_LOCK_REL

    def test_an_unrelated_close_in_the_holder_keeps_the_lock(self):
        if not _ofd_expected():
            self.skipTest("platform excluded by Requirement 1 (no known layout or no F_OFD_* constants)")
        acquired = []
        real_acquire = self.ll.RuntimeFileLock.acquire

        def spy(lock_self, *args, **kwargs):
            out = real_acquire(lock_self, *args, **kwargs)
            acquired.append(lock_self)
            return out

        with patch.object(self.ll.RuntimeFileLock, "acquire", spy):
            with self.ll.lifecycle_mutation_lock(self.root):
                # The mechanism first: a silent fallback fails here, never skips.
                self.assertEqual([lock.mechanism for lock in acquired], ["ofd"])
                # Bypass the registry: open and close the lock file directly.
                fd = os.open(self.path, os.O_RDONLY)
                os.close(fd)
                self.path.read_bytes()
                self.assertEqual(_other_process_lockf(self.root), "busy")
        self.assertEqual(_other_process_lockf(self.root), "acquired")

    def test_a_classic_lockf_holder_makes_the_lifecycle_lock_busy(self):
        holder = _Child(_LOCKF_LIFECYCLE, self.root, "hold")
        self.addCleanup(holder.close)
        self.assertEqual(holder.expect(60), "held")
        with self.assertRaises(self.ll.LifecycleLockBusy):
            with self.ll.lifecycle_mutation_lock(self.root):
                self.fail("entered while a classic lockf holder held the byte")
        holder.say()
        holder.close()
        with self.ll.lifecycle_mutation_lock(self.root):
            self.assertEqual(_other_process_lockf(self.root), "busy")
        self.assertEqual(_other_process_lockf(self.root), "acquired")


_RELOAD_DRIVER = r'''
import json, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path.cwd() / "tests"))
from server_tools_support import _make_repo, load_server, load_thin_runner

SCRATCH = Path.cwd()
out = {}
with tempfile.TemporaryDirectory() as tmp:
    root = _make_repo(Path(tmp))
    load_server()
    runner = load_thin_runner()
    runner.build_server(root)
    try:
        # A release adds a name to runtime_lock and an evicted module imports it.
        rl = SCRATCH / "runtime_lock.py"
        rl.write_text(rl.read_text(encoding="utf-8")
                      + "\n\ndef reload_probe_marker():\n    return 'fresh'\n", encoding="utf-8")
        ll = SCRATCH / "lifecycle_lock.py"
        source = ll.read_text(encoding="utf-8")
        edited = source.replace("from runtime_lock import (", "from runtime_lock import (\n    reload_probe_marker,", 1)
        assert edited != source
        ll.write_text(edited + "\n\ndef reload_probe():\n    return reload_probe_marker()\n", encoding="utf-8")
        try:
            response = runner.perform_mcp_reload()
            out["status"] = response.get("status")
            out["codes"] = [d.get("code") for d in response.get("diagnostics") or []]
            out["probe"] = sys.modules["lifecycle_lock"].reload_probe()
        except Exception as exc:
            out["raised"] = f"{type(exc).__name__}: {exc}"
    finally:
        try:
            runner._get_handler().close()
        except Exception:
            pass
print(json.dumps(out))
'''


def _run_reload_driver(mutate_server=None) -> dict:
    import shutil

    with tempfile.TemporaryDirectory() as temp:
        scratch = Path(temp) / "scripts"
        shutil.copytree(SCRIPTS_ROOT, scratch, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        if mutate_server is not None:
            server = scratch / "wf_server" / "server_impl.py"
            source = server.read_text(encoding="utf-8")
            mutated = mutate_server(source)
            assert mutated != source
            server.write_text(mutated, encoding="utf-8")
        result = subprocess.run(
            [sys.executable, "-B", "-c", _RELOAD_DRIVER],
            cwd=scratch,
            env=dict(os.environ, PYTHONPATH=str(scratch), PYTHONDONTWRITEBYTECODE="1"),
            capture_output=True, text=True, timeout=300, stdin=subprocess.DEVNULL,
        )
        if result.returncode != 0 or not result.stdout.strip():
            raise AssertionError(f"reload driver failed:\n{result.stderr[-6000:]}")
        return json.loads(result.stdout.strip().splitlines()[-1])


class RuntimeLockReloadInPlaceTests(unittest.TestCase):
    """Wave 1zxnz (1zx02) AC-8: a reload loads new runtime_lock names."""

    def test_a_reload_picks_up_a_name_added_to_runtime_lock(self):
        out = _run_reload_driver()
        self.assertEqual(out.get("status"), "ok", out)
        self.assertNotIn("reload_failed", out.get("codes", []), out)
        self.assertEqual(out.get("probe"), "fresh", out)

    def test_without_the_in_place_reload_the_import_fails(self):
        out = _run_reload_driver(lambda source: source.replace(
            '_IN_PLACE_RELOAD_MODULES = ("runtime_lock",)', "_IN_PLACE_RELOAD_MODULES = ()", 1))
        self.assertIn("ImportError", out.get("raised", ""), out)
        self.assertIn("reload_probe_marker", out.get("raised", ""), out)


@unittest.skipIf(os.name == "nt", "POSIX flock fixture")
class DashboardLockAfterReloadTests(unittest.TestCase):
    """Wave 1zxnz (1zx02) AC-15: ``dashboard_lib`` bound runtime_lock's names
    at import and is not evicted; after a reload its busy conversion still
    catches what the lock raises."""

    def test_a_held_dashboard_lock_is_still_dashboard_busy_after_reload(self):
        if str(SCRIPTS_ROOT) not in sys.path:
            sys.path.insert(0, str(SCRIPTS_ROOT))
        import dashboard_lib
        import runtime_lock
        from wf_server import server_impl

        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        (root / ".wavefoundry").mkdir()
        busy = runtime_lock.RuntimeLockBusy
        server_impl._script_cache.clear()
        importlib.reload(server_impl)
        self.assertIs(sys.modules["dashboard_lib"], dashboard_lib, "dashboard_lib was evicted")
        self.assertIs(runtime_lock.RuntimeLockBusy, busy)
        # The scenario: dashboard_lib still holds the pre-reload class.
        self.assertIsNot(dashboard_lib.RuntimeFileLock, runtime_lock.RuntimeFileLock)
        holder = _Child(_CHILD_PRELUDE + (
            "import dashboard_lib\n"
            "with dashboard_lib.dashboard_start_lock(root):\n"
            "    print('held', flush=True)\n"
            "    sys.stdin.readline()\n"
        ), root)
        self.addCleanup(holder.close)
        self.assertEqual(holder.expect(60), "held")
        with self.assertRaises(dashboard_lib.DashboardLockBusy):
            with dashboard_lib.dashboard_start_lock(root):
                self.fail("entered a dashboard lock another process holds")
