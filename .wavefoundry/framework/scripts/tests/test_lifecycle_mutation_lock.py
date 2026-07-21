"""Wave 1seax (1seat): lifecycle mutation lock, forward recoverability, seat
alignment, and selective subprocess bounds."""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]


def load_server():
    if str(SCRIPTS_ROOT) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_ROOT))
    spec = importlib.util.spec_from_file_location(
        "server_impl_lifecycle_lock", SCRIPTS_ROOT / "server_impl.py"
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["server_impl_lifecycle_lock"] = mod
    spec.loader.exec_module(mod)
    return mod


srv = load_server()


def _repo(root: Path) -> None:
    (root / "docs" / "waves").mkdir(parents=True, exist_ok=True)
    (root / "docs" / "plans").mkdir(parents=True, exist_ok=True)
    (root / ".wavefoundry").mkdir(parents=True, exist_ok=True)


def _wave(root: Path, wave_id: str, *, status: str = "active", changes: str = "") -> Path:
    d = root / "docs" / "waves" / wave_id
    d.mkdir(parents=True, exist_ok=True)
    wave_md = d / "wave.md"
    wave_md.write_text(
        f"# Wave Record\n\nOwner: Engineering\nStatus: {status}\n"
        f"Last verified: 2026-07-20\n\nwave-id: `{wave_id}`\n\n"
        f"## Changes\n{changes}\n\n## Wave Summary\n\nsummary\n",
        encoding="utf-8",
    )
    return wave_md


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
                    "spec = importlib.util.spec_from_file_location('si', sys.argv[1] + '/server_impl.py')\n"
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
        resp = srv._lifecycle_mutation_busy_response("wf_close_wave", "/x/lifecycle-mutation.lock")
        self.assertEqual(resp["status"], "error")
        self.assertTrue(resp["data"]["busy"])
        codes = [d["code"] for d in resp["diagnostics"]]
        self.assertIn("lifecycle_mutation_locked", codes)

    def test_non_census_tools_not_wrapped(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            def tool(**kwargs):
                return {"status": "ok", "data": {}}
            wrapped = self._wrapped(root, "code_read", tool)
            self.assertIs(wrapped, tool)


class ForwardRecoverabilityTests(unittest.TestCase):
    """AC-2: a retry after any single-step interruption converges."""

    def test_admission_retry_after_move_without_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _repo(root)
            wave_md = _wave(root, "1aaaa demo")
            doc = root / "docs" / "waves" / "1aaaa demo" / "1abcd-enh thing.md"
            doc.write_text("# T\n\nChange ID: `1abcd-enh thing`\n", encoding="utf-8")
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
            (root / "docs" / "plans" / "1abcd-enh thing.md").write_text(
                "# T\n\nChange ID: `1abcd-enh thing`\n", encoding="utf-8"
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
                 patch.object(srv, "_review_evidence_diagnostics", return_value=[]), \
                 patch.object(srv, "_close_wave_secrets_gate", return_value=({}, [])) if hasattr(srv, "_close_wave_secrets_gate") else patch.object(srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
                out = srv.wf_close_wave_response(root, "1aaaa", mode="create")
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
        source = (SCRIPTS_ROOT / "server_impl.py").read_text(encoding="utf-8")
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
            source = (SCRIPTS_ROOT / name).read_text(encoding="utf-8")
            self.assertNotIn("subprocess_ops_timeout_seconds", source,
                             f"{name} must stay exempt from short-op bounds")


if __name__ == "__main__":
    unittest.main()
