"""Contained repository access at every covered reader and writer (wave 200ey, change 1zyv2).

The session handoff tools, the prompt reader, the read-only MCP resources, the
two surface renderers, the install-log read and the prompt moves read and
write through one contained primitive. Each class here drives the real entry
point against a fixture repository: a target file or a parent directory linked
outside the repository is refused with a path-free message and the outside file
keeps its bytes and mode; a special file never blocks a reader; oversized input
is refused; links inside the repository and ordinary files behave as before.

This module imports nothing from the new primitive at module scope, so on code
without it these tests fail by behaviour rather than by an import error.
"""
from __future__ import annotations

import json
import os
import shutil
import stat
import sys
import tempfile
import threading
import types as _types
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
from server_tools_support import _make_repo, load_server  # noqa: E402

srv = load_server()

POSIX = os.name != "nt"
OUTSIDE_TEXT = "outside-secret-content\n"
HANDOFF = "docs/agents/session-handoff.md"
MIB8 = 8 * 1024 * 1024


def _run_with_timeout(case: unittest.TestCase, fn, timeout: float = 15.0):
    box: dict = {}

    def target() -> None:
        try:
            box["result"] = fn()
        except BaseException as exc:  # noqa: BLE001 - reported to the test
            box["error"] = exc

    worker = threading.Thread(target=target, daemon=True)
    worker.start()
    worker.join(timeout)
    case.assertFalse(worker.is_alive(), "the reader blocked on a special file")
    if "error" in box:
        raise box["error"]
    return box.get("result")


class _Fixture(unittest.TestCase):
    def setUp(self) -> None:
        base = Path(tempfile.mkdtemp(prefix="wf-contained-access-")).resolve()
        self.addCleanup(shutil.rmtree, base, ignore_errors=True)
        self.base = base
        self.root = _make_repo(base / "repo")
        self.outside = base / "outside"
        self.outside.mkdir()

    def outside_file(self, name: str = "secret.md") -> Path:
        path = self.outside / name
        path.write_text(OUTSIDE_TEXT, encoding="utf-8")
        if POSIX:
            os.chmod(path, 0o600)
        return path

    def link_file_outside(self, rel: str, name: str | None = None) -> Path:
        target = self.outside_file(name or Path(rel).name)
        link = self.root / rel
        link.parent.mkdir(parents=True, exist_ok=True)
        os.symlink(target, link)
        return target

    def link_dir_outside(self, rel_dir: str, files: "dict[str, str]") -> None:
        folder = self.outside / rel_dir.replace("/", "_")
        folder.mkdir(parents=True)
        for name in files:
            (folder / name).write_text(OUTSIDE_TEXT, encoding="utf-8")
            if POSIX:
                os.chmod(folder / name, 0o600)
        link = self.root / rel_dir
        link.parent.mkdir(parents=True, exist_ok=True)
        os.symlink(folder, link, target_is_directory=True)

    def assert_outside_untouched(self) -> None:
        for path in self.outside.rglob("*"):
            if path.is_file():
                with self.subTest(outside=path.name):
                    self.assertEqual(path.read_text(encoding="utf-8"), OUTSIDE_TEXT)
                    if POSIX:
                        self.assertEqual(stat.S_IMODE(os.stat(path).st_mode), 0o600)

    def assert_path_free(self, payload) -> None:
        text = payload if isinstance(payload, str) else json.dumps(payload, default=str)
        self.assertNotIn(str(self.base), text)
        self.assertNotIn(os.path.realpath(self.base), text)
        self.assertNotIn(OUTSIDE_TEXT.strip(), text)

    @staticmethod
    def codes(response) -> list:
        return [d.get("code") for d in response.get("diagnostics") or []]

    def resources(self):
        from declaration_support import RecordingFastMCP

        recorder = RecordingFastMCP()
        handler = _types.SimpleNamespace(root=self.root, cache=None)
        srv.register_mcp_surface(recorder, lambda: handler)
        return recorder.resource_functions

    def wave(self, status: str = "active") -> Path:
        import vocabulary_profile
        from record_layout_support import RecordTreeBuilder

        folder = RecordTreeBuilder(self.root).waves_dir / "1aaaa demo"
        folder.mkdir(parents=True, exist_ok=True)
        record = vocabulary_profile.record_file(folder)
        record.write_text(
            f"{vocabulary_profile.RECORD_TITLE}\n\nOwner: Engineering\nStatus: {status}\n"
            f"Last verified: 2026-07-20\n\n{vocabulary_profile.id_line('1aaaa demo')}\n\n"
            f"{vocabulary_profile.MEMBER_HEADING}\n\n{vocabulary_profile.SUMMARY_HEADING}\n\nsummary\n",
            encoding="utf-8",
        )
        return record

    def pause(self):
        self.wave("active")
        return srv.wf_pause_wave_response(self.root, "1aaaa", mode="create")

    def close(self):
        record = self.wave("active")
        record.write_text(
            record.read_text(encoding="utf-8")
            + "\n## Review Signoff Evidence\n\n- operator-signoff: approved\n"
            "- 2026-05-01: approved and signoff complete.\n",
            encoding="utf-8",
        )
        passed = {"passed": True, "errors": [], "warnings": [], "output": ""}
        with patch.object(srv, "run_validate", return_value=passed), \
                patch.object(srv, "run_garden", return_value={"passed": True}):
            return srv.wf_close_wave_response(self.root, "1aaaa", mode="create")


@unittest.skipUnless(POSIX, "symlink fixtures")
class HandoffContainmentTests(_Fixture):
    """AC-1 (handoff get, set, pause and close)."""

    def _assert_refused_everywhere(self) -> None:
        import wf_server.edit_gate_handlers as edit_gate_handlers

        got = edit_gate_handlers.wf_get_handoff_response(self.root)
        put = edit_gate_handlers.wf_set_handoff_response(self.root, "# New\n")
        for response in (got, put):
            self.assertEqual(response["status"], "error", response)
            self.assertIn("repo_file_refused", self.codes(response))
            self.assertIsNone(response["data"].get("content"))
            self.assert_path_free(response)
        paused = self.pause()
        self.assertEqual(paused["status"], "ok", paused)
        self.assertFalse(paused["data"]["written"])
        self.assertIn("repo_file_refused", self.codes(paused))
        self.assert_path_free(paused)
        closed = self.close()
        self.assertTrue(closed["data"]["transitioned_to_closed"], closed)
        self.assertIn("repo_file_refused", self.codes(closed))
        self.assert_path_free(closed["diagnostics"])
        self.assert_outside_untouched()

    def test_a_handoff_file_linked_outside_is_refused_by_every_tool(self) -> None:
        self.link_file_outside(HANDOFF)
        self._assert_refused_everywhere()

    def test_a_handoff_folder_linked_outside_is_refused_by_every_tool(self) -> None:
        self.link_dir_outside("docs/agents", {"session-handoff.md": OUTSIDE_TEXT})
        self._assert_refused_everywhere()


@unittest.skipUnless(POSIX, "symlink fixtures")
class ResourceAndPromptContainmentTests(_Fixture):
    """AC-1 (prompt reader and every census resource) and AC-13."""

    FIXED = (
        ("resource_prompt_index", "docs/prompts/index.md"),
        ("resource_architecture_current_state", "docs/architecture/current-state.md"),
        ("resource_session_handoff", "docs/agents/session-handoff.md"),
        ("resource_agents", "AGENTS.md"),
        ("resource_project_overview", "docs/references/project-overview.md"),
    )

    def assert_unavailable(self, text: str) -> None:
        self.assertTrue(text.startswith("# Unavailable\n"), text)
        self.assert_path_free(text)

    def _call_all(self, resources, wave_rel: str, area_rel: str, map_rel: str) -> None:
        for name, _rel in self.FIXED:
            with self.subTest(resource=name):
                self.assert_unavailable(resources[name]())
        self.assert_unavailable(resources["resource_seed"]("999-held.prompt"))
        self.assert_unavailable(resources["resource_architecture"]("held-map"))
        match = [{"wave_id": "1aaaa demo", "path": wave_rel, "changes": []}]
        with patch.object(srv, "_resolve_wave_md_matches", return_value=(match, [])):
            self.assert_unavailable(resources["resource_wave"]("1aaaa"))
        with patch.object(srv, "_waves_and_dirs", return_value=([], [])), \
                patch.object(srv, "current_wave", return_value={"path": wave_rel}):
            self.assert_unavailable(resources["resource_current_wave"]())
        area = SimpleNamespace(area_id="src", representative_path="src", name="src")
        gen = SimpleNamespace(
            OUTPUT_REL_PATH=map_rel,
            generate_safe=lambda root: self.fail("an existing map must not be regenerated"),
            compute_areas=lambda root: SimpleNamespace(areas=[area]),
            _resolve_area_context_rel_path=lambda root, match: area_rel,
            _area_context_rel_path=lambda match: area_rel,
        )
        with patch.object(srv, "_load_script", return_value=gen):
            self.assert_unavailable(resources["resource_codebase_map"]())
            self.assert_unavailable(resources["resource_area_context"]("src"))
        refused: list = []
        self.assertIsNone(srv.get_prompt(self.root, "held-prompt", refused=refused))
        # The content fallback reaches the linked index too; both are refused.
        self.assertEqual(sorted(refused), ["docs/prompts/held-prompt.md", "docs/prompts/index.md"])
        response = srv.wf_get_prompt_response(self.root, "held-prompt")
        self.assertIsNone(response["data"]["prompt"])
        self.assert_path_free(response)
        text = resources["resource_prompt"]("held-prompt")
        self.assertTrue(text.startswith("# Not Found\n"), text)
        self.assert_path_free(text)
        self.assert_outside_untouched()

    def test_files_linked_outside_are_refused(self) -> None:
        for _name, rel in self.FIXED:
            self.link_file_outside(rel, rel.replace("/", "_"))
        self.link_file_outside(".wavefoundry/framework/seeds/999-held.prompt.md")
        self.link_file_outside("docs/architecture/held-map.md")
        self.link_file_outside("docs/held-record.md")
        self.link_file_outside("docs/references/codebase-map.md")
        self.link_file_outside("src/AGENTS.md", "area-agents.md")
        self.link_file_outside("docs/prompts/held-prompt.md")
        self._call_all(self.resources(), "docs/held-record.md", "src/AGENTS.md", "docs/references/codebase-map.md")

    def test_folders_linked_outside_are_refused(self) -> None:
        self.link_dir_outside("docs/prompts", {"index.md": "", "held-prompt.md": ""})
        self.link_dir_outside("docs/architecture", {"current-state.md": "", "held-map.md": ""})
        self.link_dir_outside("docs/agents", {"session-handoff.md": ""})
        self.link_dir_outside("docs/references", {"project-overview.md": "", "codebase-map.md": ""})
        self.link_dir_outside(".wavefoundry/framework/seeds", {"999-held.prompt.md": ""})
        self.link_dir_outside("src", {"AGENTS.md": ""})
        self.link_dir_outside("docs/records", {"held-record.md": ""})
        self.link_file_outside("AGENTS.md", "root-agents.md")
        self._call_all(
            self.resources(), "docs/records/held-record.md", "src/AGENTS.md", "docs/references/codebase-map.md"
        )

    def test_one_refused_prompt_does_not_hide_the_others(self) -> None:
        prompts = self.root / "docs" / "prompts"
        prompts.mkdir(parents=True)
        self.link_file_outside("docs/prompts/held-prompt.md")
        (prompts / "plan-change.prompt.md").write_text("# Plan change\n\nheld-prompt\n", encoding="utf-8")
        (prompts / "other.prompt.md").write_text("# Other\n", encoding="utf-8")
        refused: list = []
        self.assertEqual(srv.get_prompt(self.root, "held-prompt", refused=refused), "# Plan change\n\nheld-prompt\n")
        self.assertEqual(refused, ["docs/prompts/held-prompt.md"])
        self.assertEqual(srv.get_prompt(self.root, "other"), "# Other\n")
        response = srv.wf_get_prompt_response(self.root, "held-prompt")
        self.assertEqual(response["data"]["prompt"]["content"], "# Plan change\n\nheld-prompt\n")
        self.assert_path_free(response)
        self.assert_outside_untouched()


@unittest.skipUnless(POSIX, "FIFO fixtures")
class SpecialFileTests(_Fixture):
    """AC-2: a FIFO at the handoff path and at a prompt path never blocks."""

    def test_a_fifo_handoff_is_refused_without_blocking(self) -> None:
        import wf_server.edit_gate_handlers as edit_gate_handlers

        fifo = self.root / HANDOFF
        fifo.parent.mkdir(parents=True)
        os.mkfifo(fifo)
        response = _run_with_timeout(self, lambda: edit_gate_handlers.wf_get_handoff_response(self.root))
        self.assertEqual(response["status"], "error", response)
        self.assertIn("repo_file_refused", self.codes(response))
        text = _run_with_timeout(self, lambda: self.resources()["resource_session_handoff"]())
        self.assertTrue(text.startswith("# Unavailable\n"), text)

    def test_a_fifo_prompt_is_refused_without_blocking(self) -> None:
        prompts = self.root / "docs" / "prompts"
        prompts.mkdir(parents=True)
        os.mkfifo(prompts / "held-prompt.md")
        (prompts / "real.md").write_text("# Real\n", encoding="utf-8")
        refused: list = []
        self.assertIsNone(_run_with_timeout(self, lambda: srv.get_prompt(self.root, "held-prompt", refused=refused)))
        self.assertEqual(refused, ["docs/prompts/held-prompt.md"])
        self.assertEqual(_run_with_timeout(self, lambda: srv.get_prompt(self.root, "real")), "# Real\n")


class SizeCapTests(_Fixture):
    """AC-3: a file at its cap reads in full; one byte more is refused."""

    def test_the_handoff_cap(self) -> None:
        import wf_server.edit_gate_handlers as edit_gate_handlers

        path = self.root / HANDOFF
        path.parent.mkdir(parents=True)
        path.write_bytes(b"a" * MIB8)
        response = edit_gate_handlers.wf_get_handoff_response(self.root)
        self.assertEqual(response["status"], "ok", response["diagnostics"])
        self.assertEqual(len(response["data"]["content"]), MIB8)
        path.write_bytes(b"a" * (MIB8 + 1))
        response = edit_gate_handlers.wf_get_handoff_response(self.root)
        self.assertEqual(response["status"], "error")
        self.assertIn("repo_file_refused", self.codes(response))
        self.assertIn("exceeds the size cap", json.dumps(response["diagnostics"]))
        put = edit_gate_handlers.wf_set_handoff_response(self.root, "b" * (MIB8 + 1))
        self.assertEqual(put["status"], "error")
        self.assertIn("repo_file_refused", self.codes(put))
        self.assertEqual(path.stat().st_size, MIB8 + 1, "nothing was written")

    def test_the_prompt_cap(self) -> None:
        prompts = self.root / "docs" / "prompts"
        prompts.mkdir(parents=True)
        (prompts / "big-prompt.md").write_bytes(b"p" * MIB8)
        self.assertEqual(len(srv.get_prompt(self.root, "big-prompt")), MIB8)
        (prompts / "big-prompt.md").write_bytes(b"p" * (MIB8 + 1))
        refused: list = []
        self.assertIsNone(srv.get_prompt(self.root, "big-prompt", refused=refused))
        self.assertEqual(refused, ["docs/prompts/big-prompt.md"])


class OrdinaryAndInRepositoryLinkTests(_Fixture):
    """AC-4: ordinary outputs are byte-identical to the ``read_text`` reads they
    replaced, and links that stay inside the repository keep working."""

    CONTENT = "# Title\r\nLine two\rLine three\nUnicode: café — ✓\n"

    def _old_read(self, rel: str) -> str:
        # The oracle: the read these readers performed before the change.
        return (self.root / rel).read_text(encoding="utf-8")

    def test_ordinary_outputs_match_the_previous_reads(self) -> None:
        import wf_server.edit_gate_handlers as edit_gate_handlers

        for rel in (HANDOFF, "docs/prompts/index.md", "docs/prompts/plan-change.prompt.md", "AGENTS.md",
                    "docs/architecture/current-state.md", "docs/references/project-overview.md"):
            path = self.root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("w", encoding="utf-8", newline="") as handle:
                handle.write(self.CONTENT)
        got = edit_gate_handlers.wf_get_handoff_response(self.root)
        self.assertEqual(got["data"]["content"], self._old_read(HANDOFF))
        self.assertEqual(got["data"]["mtime"], (self.root / HANDOFF).stat().st_mtime)
        prompt = srv.wf_get_prompt_response(self.root, "plan-change")
        self.assertEqual(prompt["data"]["prompt"]["content"], self._old_read("docs/prompts/plan-change.prompt.md"))
        resources = self.resources()
        for name, rel in ResourceAndPromptContainmentTests.FIXED:
            with self.subTest(resource=name):
                self.assertEqual(resources[name](), self._old_read(rel))

    def test_a_handoff_write_matches_the_previous_bytes(self) -> None:
        import wf_server.edit_gate_handlers as edit_gate_handlers

        text = "# Handoff\n\nline\n"
        put = edit_gate_handlers.wf_set_handoff_response(self.root, text)
        self.assertEqual(put["status"], "ok", put)
        oracle = self.base / "oracle.md"
        oracle.write_text(text, encoding="utf-8")
        self.assertEqual((self.root / HANDOFF).read_bytes(), oracle.read_bytes())

    @unittest.skipUnless(POSIX, "symlink fixtures")
    def test_links_inside_the_repository_keep_working(self) -> None:
        import wf_server.edit_gate_handlers as edit_gate_handlers

        real_prompts = self.root / "shared" / "prompts"
        real_prompts.mkdir(parents=True)
        (real_prompts / "linked-dir.md").write_text("# Linked dir\n", encoding="utf-8")
        (self.root / "docs").mkdir(exist_ok=True)
        os.symlink(real_prompts, self.root / "docs" / "prompts", target_is_directory=True)
        (real_prompts.parent / "final.md").write_text("# Final link\n", encoding="utf-8")
        os.symlink(real_prompts.parent / "final.md", real_prompts / "final-link.md")
        self.assertEqual(srv.get_prompt(self.root, "linked-dir"), "# Linked dir\n")
        self.assertEqual(srv.get_prompt(self.root, "final-link"), "# Final link\n")
        real_handoff = self.root / "shared" / "handoff.md"
        real_handoff.write_text("# Old\n", encoding="utf-8")
        handoff = self.root / HANDOFF
        handoff.parent.mkdir(parents=True)
        os.symlink(real_handoff, handoff)
        put = edit_gate_handlers.wf_set_handoff_response(self.root, "# New\n")
        self.assertEqual(put["status"], "ok", put)
        self.assertTrue(handoff.is_symlink())
        self.assertEqual(real_handoff.read_text(encoding="utf-8"), "# New\n")
        self.assertEqual(edit_gate_handlers.wf_get_handoff_response(self.root)["data"]["content"], "# New\n")


@unittest.skipUnless(POSIX, "symlink fixtures and executable bits")
class RendererContainmentTests(_Fixture):
    """AC-6: rendered outputs and merged configs linked outside are refused."""

    def setUp(self) -> None:
        super().setUp()
        import render_platform_surfaces as rps

        self.rps = rps

    def assert_refusal(self, call) -> None:
        with self.assertRaises(RuntimeError) as caught:
            call()
        self.assert_path_free(str(caught.exception))

    def test_a_hook_output_linked_outside_is_refused(self) -> None:
        self.link_file_outside(".claude/hooks/pre-edit.py")
        self.assert_refusal(lambda: self.rps.render_platform_entrypoints(self.root, "claude"))
        self.assert_outside_untouched()

    def test_the_wf_launcher_linked_outside_is_refused(self) -> None:
        self.link_file_outside(".wavefoundry/bin/wf")
        self.assert_refusal(lambda: self.rps.render_bin_launchers(self.root))
        self.assert_outside_untouched()

    def test_a_merged_config_linked_outside_is_refused(self) -> None:
        import contained_files

        target = self.link_file_outside(".mcp.json")
        target.write_text('{"mcpServers": {}}\n', encoding="utf-8")
        os.chmod(target, 0o600)
        before = target.read_bytes()
        with self.assertRaises((RuntimeError, contained_files.ContainedFileRefused)) as caught:
            self.rps.render_mcp_json(self.root)
        self.assert_path_free(str(caught.exception))
        self.assertEqual(target.read_bytes(), before)
        self.assertEqual(stat.S_IMODE(os.stat(target).st_mode), 0o600)

    def test_the_cli_reports_a_path_free_error_and_exits_nonzero(self) -> None:
        import contextlib
        import io

        self.link_file_outside(".claude/hooks/post-edit.py")
        err = io.StringIO()
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
            code = self.rps.main(["--repo-root", str(self.root), "--platform", "claude"])
        self.assertEqual(code, 1)
        self.assertIn("ERROR", err.getvalue())
        self.assertIn(".claude/hooks/post-edit.py", err.getvalue())
        self.assert_path_free(err.getvalue())
        self.assert_outside_untouched()

    def test_an_ordinary_render_keeps_bytes_and_executable_bits(self) -> None:
        self.rps.render_platform_entrypoints(self.root, "claude")
        self.rps.render_bin_launchers(self.root)
        hooks = self.root / ".claude" / "hooks"
        expected = {
            "pre-edit.py": self.rps.claude_pre_edit_source(),
            "post-edit.py": self.rps.claude_post_edit_source(),
            "session-capture.py": self.rps.claude_stop_source(),
        }
        for name, source in expected.items():
            with self.subTest(hook=name):
                self.assertEqual((hooks / name).read_bytes(), source.encode("utf-8"))
                self.assertEqual(os.stat(hooks / name).st_mode & 0o111, 0o111)
        wf = self.root / ".wavefoundry" / "bin" / "wf"
        cmd = self.root / ".wavefoundry" / "bin" / "wf.cmd"
        self.assertEqual(os.stat(wf).st_mode & 0o111, 0o111)
        self.assertEqual(os.stat(cmd).st_mode & 0o111, 0)
        self.assertTrue(wf.read_bytes().startswith(b"#!/usr/bin/env bash\n"))
        self.assertIn(b"\r\n", cmd.read_bytes())
        self.assertNotIn(b"\r\r\n", cmd.read_bytes())
        settings = json.loads((self.root / ".claude" / "settings.json").read_text(encoding="utf-8"))
        self.assertIn("hooks", settings)
        umask = os.umask(0)
        os.umask(umask)
        self.assertEqual(stat.S_IMODE(os.stat(self.root / ".mcp.json").st_mode), 0o666 & ~umask)


class InstallLogTests(_Fixture):
    """AC-7: a linked, special or oversized install log is reported, path-free,
    by every caller; an ordinary log reads as before."""

    LOG = ".wavefoundry/install-log.md"

    def _assert_reported(self) -> None:
        import setup_wavefoundry
        import wf_server.upgrade_handlers as upgrade_handlers

        audit_install = upgrade_handlers.wf_audit_install_response(self.root)
        self.assertEqual(audit_install["status"], "error", audit_install)
        self.assertEqual(audit_install["data"]["status"], "unreadable_log")
        self.assert_path_free(audit_install)
        audit = srv.wf_audit_response(self.root)
        self.assertIn("install_log_unreadable", self.codes(audit))
        self.assert_path_free([d for d in audit["diagnostics"] if d.get("code") == "install_log_unreadable"])
        self.assertTrue(setup_wavefoundry._install_in_progress(self.root))
        self.assert_outside_untouched()

    @unittest.skipUnless(POSIX, "symlink fixture")
    def test_a_log_linked_outside(self) -> None:
        self.link_file_outside(self.LOG)
        self._assert_reported()

    @unittest.skipUnless(POSIX, "FIFO fixture")
    def test_a_fifo_log(self) -> None:
        path = self.root / self.LOG
        path.parent.mkdir(parents=True, exist_ok=True)
        os.mkfifo(path)
        _run_with_timeout(self, self._assert_reported, timeout=120)

    def test_an_oversized_log(self) -> None:
        path = self.root / self.LOG
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"x" * (MIB8 + 1))
        self._assert_reported()

    def test_an_ordinary_log_reads_as_before(self) -> None:
        import install_log_lib

        path = self.root / self.LOG
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"# Install\r\n- [ ] 1.1 \xe2\x80\x94 x (seed-010)\r\nbad:\xff\n")
        self.assertEqual(install_log_lib.read_install_log(self.root),
                         path.read_text(encoding="utf-8", errors="replace"))
        path.unlink()
        self.assertIsNone(install_log_lib.read_install_log(self.root))


@unittest.skipUnless(POSIX, "file modes and symlink swaps need POSIX")
class PromptMoveTests(_Fixture):
    """AC-8: each mover keeps the source's mode and refuses a source swapped
    for a link after its preflight, publishing nothing."""

    def setUp(self) -> None:
        super().setUp()
        import render_agent_surfaces as ras

        self.ras = ras

    def _legacy_review_plan(self) -> str:
        return "\n".join(
            [old for _label, old, _new in self.ras.REVIEW_PLAN_LEGACY_CONTRACT_LINES]
            + ["", "## Project extension", "Keep this.", ""]
        )

    def _swap_on_open(self, source: Path, target: "Path | None" = None):
        import contained_files

        secret = target if target is not None else self.outside_file("swapped.md")
        fired = {"done": False}

        def swap(stage: str) -> None:
            if stage == "open" and not fired["done"] and source.is_file() and not source.is_symlink():
                fired["done"] = True
                source.unlink()
                os.symlink(secret, source)

        return patch.object(contained_files, "_checkpoint", side_effect=swap), fired

    def test_each_mover_refuses_a_source_swapped_for_an_in_repository_link(self) -> None:
        # The swap lands between the mover's own lstat and the contained read,
        # and the link stays inside the repository, so the contained read
        # follows it; the movers' identity check is what refuses the swap.
        import contained_files

        decoy = self.root / "decoy.md"
        decoy.write_text("# Decoy\n", encoding="utf-8")
        real_read = contained_files.read_contained
        for name, old_rel, new_rel, text, move in self._movers():
            with self.subTest(mover=name):
                source = self._seed(old_rel, text)
                fired = {"done": False}

                def swap_then_read(root, path, *args, source=source, fired=fired, **kwargs):
                    if not fired["done"] and Path(path) == source:
                        fired["done"] = True
                        source.unlink()
                        os.symlink(decoy, source)
                    return real_read(root, path, *args, **kwargs)

                swapping = patch.object(contained_files, "read_contained", side_effect=swap_then_read)
                with swapping:
                    with self.assertRaises(RuntimeError) as caught:
                        move()
                self.assertTrue(fired["done"], "the swap point was never reached")
                self.assertFalse(os.path.lexists(self.root / new_rel), "nothing is published")
                self.assert_path_free(str(caught.exception))
                self.assertEqual(decoy.read_text(encoding="utf-8"), "# Decoy\n")
                source.unlink()

    def _movers(self):
        ras = self.ras
        old_change, new_change, _shortcut = ras.CHANGE_PROMPT_RENAMES[0]
        pair = ras._PromptMovePair("plan-change", "docs/prompts/old-name.prompt.md", "docs/prompts/new-name.prompt.md")
        return (
            ("migrate_change_prompt_renames", old_change, new_change, "# Plan feature\n",
             lambda: ras.migrate_change_prompt_renames(self.root)),
            ("_move_prompt_pair", pair.source, pair.target, "# Old name\n",
             lambda: ras._move_prompt_pair(self.root, pair)),
            ("migrate_review_plan_prompt", ras.REVIEW_PLAN_OLD_PROMPT, ras.REVIEW_PLAN_NEW_PROMPT,
             self._legacy_review_plan(), lambda: ras.migrate_review_plan_prompt(self.root)),
        )

    def _seed(self, rel: str, text: str) -> Path:
        source = self.root / rel
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text(text, encoding="utf-8")
        os.chmod(source, 0o640)
        return source

    def test_each_mover_keeps_the_source_mode(self) -> None:
        for name, old_rel, new_rel, text, move in self._movers():
            with self.subTest(mover=name):
                self._seed(old_rel, text)
                move()
                target = self.root / new_rel
                self.assertTrue(target.is_file())
                self.assertFalse((self.root / old_rel).exists())
                self.assertEqual(stat.S_IMODE(os.stat(target).st_mode), 0o640)

    def test_each_mover_refuses_a_source_swapped_after_the_preflight(self) -> None:
        for name, old_rel, new_rel, text, move in self._movers():
            with self.subTest(mover=name):
                source = self._seed(old_rel, text)
                swapping, fired = self._swap_on_open(source)
                with swapping:
                    with self.assertRaises(RuntimeError) as caught:
                        move()
                self.assertTrue(fired["done"], "the swap point was never reached")
                self.assertFalse(os.path.lexists(self.root / new_rel), "nothing is published")
                self.assert_path_free(str(caught.exception))
                self.assert_outside_untouched()
                source.unlink()


if __name__ == "__main__":
    unittest.main()
