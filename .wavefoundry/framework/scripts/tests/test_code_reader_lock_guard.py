"""Wave 1zv87 (1zuq7): code readers never open a framework runtime lock.

The lifecycle and index-build locks are POSIX record locks (``lockf``), which
the kernel releases when the holding process closes ANY descriptor of the
file. A reader in the server process that opens one silently drops the lock.
The oracle is a second process that tries to take the lock byte with a raw
``lockf``: it must still see the lock busy after every refused read.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
from server_tools_support import _make_repo, load_server  # noqa: E402

srv = load_server()

import lifecycle_lock  # noqa: E402
import wf_server.codenav_handlers as codenav_handlers  # noqa: E402
import wf_server.graph_handlers as graph_handlers  # noqa: E402

_PROBE = textwrap.dedent(
    """
    import fcntl, os, sys
    fd = os.open(sys.argv[1], os.O_RDWR)
    try:
        os.lseek(fd, int(sys.argv[2]), os.SEEK_SET)
        fcntl.lockf(fd, fcntl.LOCK_EX | fcntl.LOCK_NB, 1, int(sys.argv[2]))
    except OSError:
        print("held")
    else:
        print("free")
    """
)

LOCK_REL = ".wavefoundry/lifecycle-mutation.lock"


def _case_insensitive(root: Path) -> bool:
    probe = root / "CaseProbe.tmp"
    probe.write_text("", encoding="utf-8")
    try:
        return (root / "caseprobe.TMP").exists()
    finally:
        probe.unlink()


class _RepoCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = _make_repo(Path(self.tmp.name).resolve(), {
            "src/app.py": "def app():\n    return 'needle'\n",
            ".wavefoundry/framework/scripts/tool.py": "def tool():\n    return 'needle'\n",
            ".wavefoundry/index/index-build.lock": "{}\n",
            ".wavefoundry/locks/dashboard-server.lock": "{}\n",
        })

    def assert_refused(self, response: dict) -> None:
        self.assertEqual(response["status"], "error", response)


class ResolverRefusesLockFilesTests(_RepoCase):
    """AC-2: the resolver rule and its scope."""

    def test_lock_paths_are_refused(self) -> None:
        (self.root / LOCK_REL).write_text("{}\n", encoding="utf-8")
        for rel in (
            LOCK_REL,
            ".wavefoundry/index/index-build.lock",
            ".wavefoundry/locks/dashboard-server.lock",
            ".WAVEFOUNDRY/Lifecycle-Mutation.LOCK",
            ".wavefoundry/./index/../lifecycle-mutation.lock",
        ):
            with self.subTest(rel=rel):
                self.assertIsNone(srv._resolve_repo_path(self.root, rel))
                self.assert_refused(codenav_handlers.code_read_response(self.root, rel))

    def test_case_variant_is_refused_where_it_names_the_lock(self) -> None:
        (self.root / LOCK_REL).write_text("{}\n", encoding="utf-8")
        variant = ".WAVEFOUNDRY/Lifecycle-Mutation.LOCK"
        if _case_insensitive(self.root):
            self.assertTrue((self.root / variant).is_file())
        self.assertTrue(srv._is_runtime_lock_path(self.root, self.root / variant))
        self.assert_refused(codenav_handlers.code_read_response(self.root, variant))

    def test_ordinary_and_framework_files_still_read(self) -> None:
        (self.root / "yarn.lock").write_text("# not a framework lock\n", encoding="utf-8")
        for rel in ("src/app.py", ".wavefoundry/framework/scripts/tool.py", "yarn.lock"):
            with self.subTest(rel=rel):
                self.assertIsNotNone(srv._resolve_repo_path(self.root, rel))
                self.assertEqual(codenav_handlers.code_read_response(self.root, rel)["status"], "ok")

    def test_every_resolver_reader_refuses_the_lock(self) -> None:
        (self.root / ".wavefoundry/framework/scripts/held.lock").write_text("x = 1\n", encoding="utf-8")
        rel = ".wavefoundry/framework/scripts/held.lock"
        self.assert_refused(codenav_handlers.code_outline_response(self.root, rel))
        self.assert_refused(codenav_handlers.code_hover_response(self.root, rel, 1))
        self.assert_refused(codenav_handlers.code_dependencies_response(self.root, rel))
        self.assert_refused(graph_handlers._code_impact_heuristic_response(self.root, rel))

    def test_walker_mirror_agrees_with_the_server_predicate(self) -> None:
        idx = srv._indexer_module()
        cases = [
            LOCK_REL, ".wavefoundry/index/index-build.lock", ".wavefoundry/locks/a.lock",
            ".wavefoundry/framework/test-run.lock", ".WAVEFOUNDRY/X.LOCK", ".wavefoundry/a.lock.txt",
            "yarn.lock", "src/.wavefoundry/a.lock", ".wavefoundry/framework/scripts/tool.py",
        ]
        for rel in cases:
            path = self.root / rel
            if not path.exists():
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("", encoding="utf-8")
        # Hard links: one to a lock (refused), one between ordinary files (not).
        os.link(self.root / LOCK_REL, self.root / "src/hard.py")
        os.link(self.root / "src/app.py", self.root / "src/twin.py")
        cases += ["src/hard.py", "src/twin.py", "src/app.py"]
        for rel in cases:
            path = self.root / rel
            with self.subTest(rel=rel):
                self.assertEqual(
                    srv._is_runtime_lock_path(self.root, path.resolve()),
                    idx._walk_target_is_runtime_lock(path, self.root),
                )
        self.assertTrue(srv._is_runtime_lock_path(self.root, self.root / "src/hard.py"))
        self.assertFalse(srv._is_runtime_lock_path(self.root, self.root / "src/twin.py"))


class _HeldLockCase(_RepoCase):
    def setUp(self) -> None:
        super().setUp()
        self.lock_path = self.root / LOCK_REL

    def other_process_sees(self) -> str:
        out = subprocess.run(
            [sys.executable, "-B", "-c", _PROBE, str(self.lock_path),
             str(lifecycle_lock.LIFECYCLE_MUTATION_LOCK_SENTINEL)],
            capture_output=True, text=True, timeout=30, stdin=subprocess.DEVNULL,
        )
        return out.stdout.strip()


@unittest.skipIf(os.name == "nt", "POSIX record-lock release semantics")
class HeldLifecycleLockTests(_HeldLockCase):
    """AC-1 and AC-3: a refused read leaves the in-process hold intact."""

    def test_code_read_of_the_held_lock_is_refused_and_the_hold_survives(self) -> None:
        with lifecycle_lock.lifecycle_mutation_lock(self.root):
            self.assertEqual(self.other_process_sees(), "held")
            self.assert_refused(codenav_handlers.code_read_response(self.root, LOCK_REL))
            self.assertEqual(self.other_process_sees(), "held")

    def test_symlink_to_the_held_lock_is_not_opened_by_walk_readers(self) -> None:
        with lifecycle_lock.lifecycle_mutation_lock(self.root):
            # notes.py takes the known-text path; notes.xyz takes the walker's sniff.
            # Created under the hold: since wave 1zv8c the acquisition refuses a
            # hold while such a link exists, and these readers are the backstop.
            for name in ("notes.py", "notes.xyz"):
                os.symlink(os.path.join(".wavefoundry", "lifecycle-mutation.lock"), self.root / name)
            self.assertEqual(self.other_process_sees(), "held")
            walked = {p.name for p in srv._indexer_module().walk_repo(self.root)}
            self.assertNotIn("notes.py", walked)
            self.assertNotIn("notes.xyz", walked)
            self.assertIn("app.py", walked)
            self.assertEqual(self.other_process_sees(), "held")
            keyword = codenav_handlers.code_keyword_response(self.root, "needle")
            self.assertEqual(keyword["status"], "ok", keyword)
            self.assertNotIn("notes.py", {r["path"] for r in keyword["data"]["results"]})
            self.assertEqual(self.other_process_sees(), "held")
            pattern = codenav_handlers.code_pattern_response(self.root, "pid|needle")
            self.assertEqual(pattern["status"], "ok", pattern)
            self.assertEqual(self.other_process_sees(), "held")
            # Index-derived reads (graph nodes, citations) go through the same rule.
            self.assertTrue(srv._repo_rel_path_refused(self.root, "notes.py"))
            self.assertEqual(graph_handlers._scan_call_sites_in_file(self.root, "app", "notes.py"), [])
            self.assertEqual(self.other_process_sees(), "held")

    def test_hard_link_to_the_held_lock_is_not_opened(self) -> None:
        with lifecycle_lock.lifecycle_mutation_lock(self.root):
            os.link(self.lock_path, self.root / "src/hard.py")
            os.link(self.root / "src/app.py", self.root / "src/twin.py")
            self.assertEqual(self.other_process_sees(), "held")
            self.assert_refused(codenav_handlers.code_read_response(self.root, "src/hard.py"))
            self.assert_refused(codenav_handlers.code_outline_response(self.root, "src/hard.py"))
            self.assertEqual(self.other_process_sees(), "held")
            walked = {p.name for p in srv._indexer_module().walk_repo(self.root)}
            self.assertNotIn("hard.py", walked)
            self.assertIn("twin.py", walked)
            keyword = codenav_handlers.code_keyword_response(self.root, "needle")
            self.assertEqual(keyword["status"], "ok", keyword)
            self.assertIn("src/twin.py", {r["path"] for r in keyword["data"]["results"]})
            self.assertEqual(self.other_process_sees(), "held")
            pattern = codenav_handlers.code_pattern_response(self.root, "pid|needle")
            self.assertEqual(pattern["status"], "ok", pattern)
            self.assertEqual(self.other_process_sees(), "held")
            self.assertEqual(graph_handlers._scan_call_sites_in_file(self.root, "app", "src/hard.py"), [])
            self.assertEqual(self.other_process_sees(), "held")
            # A hard link between two ordinary files still reads.
            self.assertEqual(codenav_handlers.code_read_response(self.root, "src/twin.py")["status"], "ok")


@unittest.skipIf(os.name == "nt", "POSIX record-lock release semantics")
class ReferenceCandidateFilterTests(_HeldLockCase):
    """code_references opens graph-named files; each filter keeps a lock out.

    A stale graph still names a lock as a candidate file, a retry candidate
    or a constant reader. ``hard.py`` is a hard link to the held lock (the
    reference readers skip a symlink themselves, since they compare the
    resolved path against the candidate set); ``notes.py`` is a symlink to it.
    """

    def setUp(self) -> None:
        super().setUp()
        refresh = patch.object(srv, "_graph_refresh_then_recheck", return_value=None)
        refresh.start()
        self.addCleanup(refresh.stop)

    def references(self, symbol: str, candidates) -> dict:
        with lifecycle_lock.lifecycle_mutation_lock(self.root):
            # Both links are made under the hold (wave 1zv8c refuses a hold
            # while one exists); the reference readers are the backstop.
            os.symlink(os.path.join(".wavefoundry", "lifecycle-mutation.lock"), self.root / "notes.py")
            os.link(self.lock_path, self.root / "hard.py")
            self.assertEqual(self.other_process_sees(), "held")
            with patch.object(codenav_handlers, "_graph_references_candidate_files", side_effect=candidates):
                response = codenav_handlers.code_references_response(self.root, symbol)
            self.assertEqual(self.other_process_sees(), "held")
        return response

    def test_first_candidate_filter(self) -> None:
        response = self.references("needle", lambda root, symbol: frozenset({"hard.py", "src/app.py"}))
        self.assertEqual(response["status"], "ok", response)

    def test_retry_candidate_filter(self) -> None:
        def candidates(root, symbol):
            return frozenset({"src/app.py"}) if "." in symbol else frozenset({"hard.py"})

        response = self.references("schema.zzzabsent", candidates)
        self.assertEqual(response["status"], "ok", response)

    def test_constant_reader_filter(self) -> None:
        index = SimpleNamespace(
            present=True,
            resolve_symbol=lambda symbol: "const",
            get_node=lambda node_id: (
                {"kind": "constant"} if node_id == "const"
                else {"source_file": "notes.py", "source_location": "1"}
            ),
            _in={"const": [{"relation": "reads", "source": "reader"}]},
        )
        graph_query = SimpleNamespace(get_query_index=lambda root, layer="project": index)
        with patch.object(srv, "_load_graph_query", return_value=graph_query):
            response = self.references("NEEDLE_CONST", lambda root, symbol: frozenset({"src/app.py"}))
        self.assertEqual(response["status"], "ok", response)



# --- Wave 1zxnz (1zx02): handoff, prompt and resource readers ---------------

_LOCK_BODY = "lock-carrier-bytes\n"


class _OpenRecorder:
    """Record every path opened by name; the lock file must never be one."""

    def __init__(self, forbidden: Path) -> None:
        import builtins
        import io

        self.forbidden = os.path.realpath(forbidden)
        self.opened: list[str] = []
        self._builtins_open = builtins.open
        self._io_open = io.open
        self._os_open = os.open

    def _note(self, path) -> None:
        if isinstance(path, (str, bytes, os.PathLike)):
            self.opened.append(os.path.realpath(os.fsdecode(path)))

    def patches(self):
        from contextlib import ExitStack

        recorder = self

        def builtins_open(file, *args, **kwargs):
            recorder._note(file)
            return recorder._builtins_open(file, *args, **kwargs)

        def io_open(file, *args, **kwargs):
            recorder._note(file)
            return recorder._io_open(file, *args, **kwargs)

        def os_open(path, *args, **kwargs):
            if kwargs.get("dir_fd") is None:
                recorder._note(path)
            return recorder._os_open(path, *args, **kwargs)

        stack = ExitStack()
        stack.enter_context(patch("builtins.open", builtins_open))
        stack.enter_context(patch("io.open", io_open))
        stack.enter_context(patch("os.open", os_open))
        return stack

    def assert_never_opened(self, case: unittest.TestCase) -> None:
        case.assertTrue(self.opened, "the recorder saw no opens at all")
        case.assertNotIn(self.forbidden, self.opened)


@unittest.skipIf(os.name == "nt", "symlink fixtures")
class _LockTargetCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = _make_repo(Path(self.tmp.name).resolve())
        self.lock_path = self.root / LOCK_REL
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        self.lock_path.write_text(_LOCK_BODY, encoding="utf-8")
        self.recorder = _OpenRecorder(self.lock_path)

    def link_to_lock(self, rel: str) -> Path:
        link = self.root / rel
        link.parent.mkdir(parents=True, exist_ok=True)
        os.symlink(os.path.relpath(self.lock_path, link.parent), link)
        return link

    def assert_path_free(self, payload) -> None:
        import json

        text = payload if isinstance(payload, str) else json.dumps(payload, default=str)
        self.assertNotIn(str(self.root), text)
        self.assertNotIn(os.path.realpath(self.root), text)
        self.assertNotIn(_LOCK_BODY.strip(), text)

    def assert_refused_markdown(self, text: str, rel: str) -> None:
        self.assertTrue(text.startswith("# Refused\n"), text)
        self.assertIn(rel, text)
        self.assert_path_free(text)

    @staticmethod
    def codes(response) -> list:
        return [d.get("code") for d in response.get("diagnostics") or []]


class HandoffLockTargetTests(_LockTargetCase):
    """AC-11: handoff readers and writers refuse a lock target."""

    HANDOFF = "docs/agents/session-handoff.md"

    def test_get_and_set_handoff_refuse_without_opening(self) -> None:
        import wf_server.edit_gate_handlers as edit_gate_handlers

        self.link_to_lock(self.HANDOFF)
        with self.recorder.patches():
            got = edit_gate_handlers.wf_get_handoff_response(self.root)
            put = edit_gate_handlers.wf_set_handoff_response(self.root, "# New\n")
        for response in (got, put):
            self.assertEqual(response["status"], "error", response)
            self.assertIn("runtime_lock_target_refused", self.codes(response))
            self.assert_path_free(response)
        self.assertNotIn(self.recorder.forbidden, self.recorder.opened)
        self.assertEqual(self.lock_path.read_text(encoding="utf-8"), _LOCK_BODY)

    def _wave(self, status: str) -> Path:
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

    def test_pause_skips_the_handoff_and_keeps_the_transition(self) -> None:
        record = self._wave("active")
        self.link_to_lock(self.HANDOFF)
        with self.recorder.patches():
            response = srv.wf_pause_wave_response(self.root, "1aaaa", mode="create")
        self.assertEqual(response["status"], "ok", response)
        self.assertIn("runtime_lock_target_refused", self.codes(response))
        self.assertFalse(response["data"]["written"])
        self.assertIn("Status: paused", record.read_text(encoding="utf-8"))
        self.assert_path_free(response)
        self.recorder.assert_never_opened(self)
        self.assertEqual(self.lock_path.read_text(encoding="utf-8"), _LOCK_BODY)

    def test_close_skips_the_handoff_and_keeps_the_close(self) -> None:
        record = self._wave("active")
        record.write_text(
            record.read_text(encoding="utf-8")
            + "\n## Review Signoff Evidence\n\n- operator-signoff: approved\n"
            "- 2026-05-01: approved and signoff complete.\n",
            encoding="utf-8",
        )
        self.link_to_lock(self.HANDOFF)
        passed = {"passed": True, "errors": [], "warnings": [], "output": ""}
        with patch.object(srv, "run_validate", return_value=passed), \
                patch.object(srv, "run_garden", return_value={"passed": True}), \
                self.recorder.patches():
            response = srv.wf_close_wave_response(self.root, "1aaaa", mode="create")
        self.assertEqual(response["status"], "ok", response)
        self.assertTrue(response["data"]["transitioned_to_closed"], response)
        self.assertIn("Status: closed", record.read_text(encoding="utf-8"))
        self.assertIn("runtime_lock_target_refused", self.codes(response))
        self.assert_path_free(response["diagnostics"])
        self.recorder.assert_never_opened(self)
        self.assertEqual(self.lock_path.read_text(encoding="utf-8"), _LOCK_BODY)


class ResourceLockTargetTests(_LockTargetCase):
    """AC-11: every census resource refuses a lock target with ``# Refused``."""

    def resources(self):
        import types as _types

        from declaration_support import RecordingFastMCP

        recorder = RecordingFastMCP()
        handler = _types.SimpleNamespace(root=self.root, cache=None)
        srv.register_mcp_surface(recorder, lambda: handler)
        return recorder.resource_functions

    def call(self, fn, *args) -> str:
        with self.recorder.patches():
            text = fn(*args)
        self.assertNotIn(self.recorder.forbidden, self.recorder.opened)
        return text

    def test_fixed_document_resources(self) -> None:
        resources = self.resources()
        for name, rel in (
            ("resource_prompt_index", "docs/prompts/index.md"),
            ("resource_architecture_current_state", "docs/architecture/current-state.md"),
            ("resource_session_handoff", "docs/agents/session-handoff.md"),
            ("resource_agents", "AGENTS.md"),
            ("resource_project_overview", "docs/references/project-overview.md"),
        ):
            with self.subTest(resource=name):
                self.link_to_lock(rel)
                self.assert_refused_markdown(self.call(resources[name]), rel)

    def test_slug_resources(self) -> None:
        resources = self.resources()
        seed = ".wavefoundry/framework/seeds/999-held.prompt.md"
        self.link_to_lock(seed)
        self.assert_refused_markdown(self.call(resources["resource_seed"], "999-held.prompt"), seed)
        arch = "docs/architecture/held-map.md"
        self.link_to_lock(arch)
        self.assert_refused_markdown(self.call(resources["resource_architecture"], "held-map"), arch)
        from record_layout_support import RecordTreeBuilder

        plans_rel = RecordTreeBuilder(self.root).plans_dir.relative_to(self.root).as_posix()
        change = f"{plans_rel}/1bbbb-bug held.md"
        self.link_to_lock(change)
        self.assert_refused_markdown(self.call(resources["resource_change"], "1bbbb"), change)

    def test_wave_resources(self) -> None:
        resources = self.resources()
        rel = "docs/held-record.md"
        self.link_to_lock(rel)
        match = [{"wave_id": "1aaaa demo", "path": rel, "changes": []}]
        with patch.object(srv, "_resolve_wave_md_matches", return_value=(match, [])):
            self.assert_refused_markdown(self.call(resources["resource_wave"], "1aaaa"), rel)
        with patch.object(srv, "_waves_and_dirs", return_value=([], [])), \
                patch.object(srv, "current_wave", return_value={"path": rel}):
            self.assert_refused_markdown(self.call(resources["resource_current_wave"]), rel)

    def test_codebase_map_and_area_resources(self) -> None:
        resources = self.resources()
        map_rel = "docs/references/codebase-map.md"
        self.link_to_lock(map_rel)
        area_rel = "src/AGENTS.md"
        self.link_to_lock(area_rel)
        area = SimpleNamespace(area_id="src", representative_path="src", name="src")
        gen = SimpleNamespace(
            OUTPUT_REL_PATH=map_rel,
            generate_safe=lambda root: self.fail("an existing map must not be regenerated"),
            compute_areas=lambda root: SimpleNamespace(areas=[area]),
            _resolve_area_context_rel_path=lambda root, match: area_rel,
            _area_context_rel_path=lambda match: area_rel,
        )
        with patch.object(srv, "_load_script", return_value=gen):
            self.assert_refused_markdown(self.call(resources["resource_codebase_map"]), map_rel)
            self.assert_refused_markdown(self.call(resources["resource_area_context"], "src"), area_rel)

    def test_ordinary_targets_still_read(self) -> None:
        resources = self.resources()
        agents = self.root / "AGENTS.md"
        agents.write_text("# Agents\n", encoding="utf-8")
        self.assertEqual(resources["resource_agents"](), "# Agents\n")
        self.assertEqual(srv._read_repo_text_checked(self.root, agents), "# Agents\n")
        with self.assertRaises(srv.RuntimeLockTargetRefused) as raised:
            srv._read_repo_text_checked(self.root, self.link_to_lock("docs/x.md"))
        self.assertEqual(raised.exception.rel_path, "docs/x.md")
        self.assertNotIn(str(self.root), str(raised.exception))


class PromptLockTargetTests(_LockTargetCase):
    """AC-16: a refused prompt candidate is skipped, reported, never cached."""

    def setUp(self) -> None:
        super().setUp()
        self.prompts = self.root / "docs" / "prompts"
        self.prompts.mkdir(parents=True, exist_ok=True)
        self.held = "docs/prompts/held-prompt.md"
        self.link_to_lock(self.held)

    def test_a_refused_candidate_is_skipped_for_a_later_match(self) -> None:
        # The slug pass reaches only the lock target; the content fallback
        # skips it again and finds this prompt.
        (self.prompts / "other.md").write_text("# Real\n\nheld-prompt\n", encoding="utf-8")
        refused: list = []
        with self.recorder.patches():
            text = srv.get_prompt(self.root, "held-prompt", refused=refused)
        self.assertEqual(text, "# Real\n\nheld-prompt\n")
        self.assertEqual(refused, [self.held])
        self.assertNotIn(self.recorder.forbidden, self.recorder.opened)
        response = srv.wf_get_prompt_response(self.root, "held-prompt")
        self.assertEqual(response["data"]["prompt"]["content"], "# Real\n\nheld-prompt\n")
        warning = [d for d in response["diagnostics"] if d["code"] == "runtime_lock_target_refused"]
        self.assertEqual(len(warning), 1, response)
        self.assertEqual(warning[0].get("severity"), "warning")
        self.assert_path_free(response["diagnostics"])

    def test_a_miss_reports_the_refusal_and_is_not_cached(self) -> None:
        cache = srv.McpRepoCache(self.root)
        for _ in range(2):
            with self.recorder.patches():
                response = srv.wf_get_prompt_response(self.root, "held-prompt", cache=cache)
            self.assertNotIn(self.recorder.forbidden, self.recorder.opened)
            self.assertIsNone(response["data"]["prompt"])
            self.assertEqual(self.codes(response), ["prompt_not_found", "runtime_lock_target_refused"])
            self.assert_path_free(response)
        resources = ResourceLockTargetTests.resources(self)
        with self.recorder.patches():
            text = resources["resource_prompt"]("held-prompt")
        self.assertTrue(text.startswith("# Not Found\n"), text)
        self.assertIn(self.held, text)
        self.assert_path_free(text)

    def test_an_ordinary_miss_is_still_cached(self) -> None:
        cache = srv.McpRepoCache(self.root)
        with patch.object(srv, "get_prompt", wraps=srv.get_prompt) as lookup:
            srv.wf_get_prompt_response(self.root, "no-such-prompt-anywhere", cache=cache)
            srv.wf_get_prompt_response(self.root, "no-such-prompt-anywhere", cache=cache)
        # The content fallback skips the refused candidate, so even an
        # ordinary miss here involved a refusal and is re-run.
        self.assertEqual(lookup.call_count, 2)
        os.unlink(self.root / self.held)
        with patch.object(srv, "get_prompt", wraps=srv.get_prompt) as lookup:
            srv.wf_get_prompt_response(self.root, "no-such-prompt-anywhere", cache=cache)
            srv.wf_get_prompt_response(self.root, "no-such-prompt-anywhere", cache=cache)
        self.assertEqual(lookup.call_count, 1)


class CheckedReaderCensusTests(unittest.TestCase):
    """AC-11: the census sites read only through ``_read_repo_text_checked``."""

    def test_no_direct_read_text_at_census_sites(self) -> None:
        import ast

        from framework_files import source_path

        server = ast.parse(source_path("server_impl").read_text(encoding="utf-8"))
        handoff = ast.parse(source_path("wf_server.edit_gate_handlers").read_text(encoding="utf-8"))
        wanted = {
            "get_prompt", "_resolve_change_doc_matches", "_read_doc_or_not_found",
            "_validated_wave_markdown", "resource_project_overview", "resource_seed",
            "resource_architecture", "resource_area_context", "resource_codebase_map",
            "resource_prompt", "resource_current_wave", "resource_wave", "resource_change",
            "resource_session_handoff", "resource_agents", "resource_prompt_index",
            "resource_architecture_current_state",
        }
        found = {}
        for tree in (server,):
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name in wanted:
                    found[node.name] = node
        for node in ast.walk(handoff):
            if isinstance(node, ast.FunctionDef) and node.name in {
                "wf_get_handoff_response", "wf_set_handoff_response",
            }:
                found[node.name] = node
        self.assertEqual(set(found), wanted | {"wf_get_handoff_response", "wf_set_handoff_response"})
        for name, node in sorted(found.items()):
            calls = {
                call.func.attr
                for call in ast.walk(node)
                if isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute)
            }
            with self.subTest(function=name):
                self.assertNotIn("read_text", calls)
        checked = {
            name for name, node in found.items()
            if any(isinstance(n, (ast.Name, ast.Attribute))
                   and (getattr(n, "id", None) or getattr(n, "attr", None)) in {
                       "_read_repo_text_checked", "_read_repo_text_and_stat",
                       "_refuse_runtime_lock_target"}
                   for n in ast.walk(node))
        }
        self.assertTrue({
            "get_prompt", "_resolve_change_doc_matches", "_read_doc_or_not_found",
            "_validated_wave_markdown", "resource_project_overview", "resource_seed",
            "resource_architecture", "resource_area_context", "resource_codebase_map",
            "wf_get_handoff_response", "wf_set_handoff_response",
        } <= checked, checked)
        # The pause and close handoff writes check the target first.
        for name in ("wf_pause_wave_response", "wf_close_wave_response"):
            node = next(n for n in ast.walk(server) if isinstance(n, ast.FunctionDef) and n.name == name)
            text = ast.unparse(node)
            with self.subTest(function=name):
                self.assertIn("_refuse_runtime_lock_target(root, handoff)", text)
                self.assertNotIn("handoff.read_text", text)

    def test_census_sites_read_and_write_through_the_contained_primitive(self) -> None:
        """Wave 200ey (1zyv2) AC-10: the checked reader is the contained read, the
        handoff writers are the contained write, and no census site opens,
        reads, writes or creates a directory by path itself."""
        import ast

        from framework_files import source_path

        server = ast.parse(source_path("server_impl").read_text(encoding="utf-8"))
        handoff = ast.parse(source_path("wf_server.edit_gate_handlers").read_text(encoding="utf-8"))
        functions = {
            node.name: node
            for tree in (server, handoff)
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef)
        }

        def text(name: str) -> str:
            return ast.unparse(functions[name])

        self.assertIn("contained_files.read_contained(", text("_read_repo_text_and_stat"))
        self.assertIn("_read_repo_text_and_stat(", text("_read_repo_text_checked"))
        self.assertIn("contained_files.write_contained_bytes(", text("_write_handoff_text"))
        for name in ("wf_set_handoff_response", "wf_pause_wave_response", "wf_close_wave_response"):
            with self.subTest(writer=name):
                self.assertIn("_write_handoff_text(", text(name))
        self.assertIn("_read_repo_text_and_stat(", text("wf_get_handoff_response"))
        census = {
            "get_prompt", "_read_doc_or_not_found", "_validated_wave_markdown",
            "resource_project_overview", "resource_seed", "resource_architecture",
            "resource_area_context", "resource_codebase_map", "resource_prompt",
            "resource_current_wave", "resource_wave", "resource_session_handoff",
            "resource_agents", "resource_prompt_index", "resource_architecture_current_state",
            "wf_get_handoff_response", "wf_set_handoff_response", "_read_handoff_prior",
            "_write_handoff_text", "_read_repo_text_checked", "_read_repo_text_and_stat",
        }
        forbidden = {"read_text", "read_bytes", "write_text", "write_bytes", "open", "mkdir", "chmod"}
        for name in sorted(census):
            node = functions[name]
            calls = set()
            for call in ast.walk(node):
                if not isinstance(call, ast.Call):
                    continue
                if isinstance(call.func, ast.Attribute):
                    calls.add(call.func.attr)
                elif isinstance(call.func, ast.Name):
                    calls.add(call.func.id)
            with self.subTest(function=name):
                self.assertFalse(calls & forbidden, sorted(calls & forbidden))
        # The pause and close handoff blocks create no directory by path either.
        for name in ("wf_pause_wave_response", "wf_close_wave_response"):
            with self.subTest(function=name):
                self.assertNotIn("handoff.parent.mkdir", text(name))
                self.assertNotIn("handoff.write_text", text(name))


if __name__ == "__main__":
    unittest.main()
