"""Read-only archive record root (wave 1z8ts, change 1z827).

AC-2: with an archive root holding a wave and a change written under a second
profile, ``wf_get_change`` finds both by id (marked archived), the dashboard
document view serves the archived change with the archived header, and a new
id skips an archived prefix. Each read has an archive-unset control.
AC-3: each of the eleven lifecycle writers given an archived id returns
``archived_record_read_only`` and changes no file; a live record with the same
id wins; the gardener never stamps an archived file, even when named.
AC-4: overlapping, escaping or alias archive roots refuse to load.
AC-5: an invalid ``ARCHIVE_PROFILE`` refuses to import with the field named;
docs-lint skips archived files (full and changed-file runs), the secrets scan
still covers them, and an unreadable archived record is an advisory warning.
"""
from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
for extra in (SCRIPTS_DIR, SCRIPTS_DIR / "tests"):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

import record_paths  # noqa: E402
import vocabulary_profile  # noqa: E402
from record_layout_support import patch_layout, run_script_with_layout  # noqa: E402
from server_tools_support import _make_repo, load_server  # noqa: E402

ARCHIVE_REL = "docs/archive/records"
SECOND = dict(zip(vocabulary_profile.FIELD_NAMES, (
    "Set", "Sets", "Member", "Members", "set.md", "set-id", "# Set Record", "## Set Summary",
    "## Members", "Member ID", "Member Status", "Set",
)))
ARCHIVED_WAVE = "1a000 old-set"
ARCHIVED_CHANGE = "1a001-feat old-thing"


def _live_roots(root: Path, rp=record_paths):
    """The live waves and plans roots of the loaded layout under ``root``."""
    roots = rp.load_record_roots(root)
    return roots.waves, roots.plans


def _live_record(folder: Path, wave_id: str, *, status: str, title: str = "", vp=vocabulary_profile) -> None:
    """A minimal live container record in the loaded vocabulary."""
    folder.mkdir(parents=True)
    text = f"{vp.RECORD_TITLE}\n\nStatus: {status}\n\n{vp.id_line(wave_id)}\n"
    if title:
        text += f"Title: {title}\n\n{vp.MEMBER_HEADING}\n"
    (folder / vp.RECORD_FILENAME).write_text(text, encoding="utf-8")


def _tree_digest(path: Path) -> str:
    digest = hashlib.sha256()
    for item in sorted(path.rglob("*")):
        digest.update(item.relative_to(path).as_posix().encode())
        if item.is_file() and not item.is_symlink():
            digest.update(item.read_bytes())
    return digest.hexdigest()


def _module_copies(srv=None):
    """Every loaded copy of ``record_paths`` and ``vocabulary_profile``: the
    server loader reloads them, so a test patches each copy a caller may hold."""
    import lifecycle_id

    rps = {id(m): m for m in (record_paths, sys.modules.get("record_paths"), lifecycle_id.record_paths,
                                getattr(srv, "record_paths", None)) if m is not None}
    vps = {id(m): m for m in (vocabulary_profile, sys.modules.get("vocabulary_profile"),
                                getattr(srv, "_vocab", None), *(r.vocabulary_profile for r in rps.values()))
           if m is not None}
    return tuple(rps.values()), tuple(vps.values())


def _write_archive(root: Path) -> Path:
    folder = root / ARCHIVE_REL / ARCHIVED_WAVE
    folder.mkdir(parents=True)
    (folder / "set.md").write_text(
        "# Set Record\n\nStatus: closed\n\n"
        f"set-id: `{ARCHIVED_WAVE}`\n\n## Members\n\n"
        f"Member ID: `{ARCHIVED_CHANGE}`\nMember Status: `complete`\n",
        encoding="utf-8",
    )
    (folder / f"{ARCHIVED_CHANGE}.md").write_text(
        # A stale Last verified line the gardener would rewrite if it reached the file.
        f"# Old Thing\n\nLast verified: 2020-01-01\n\nMember ID: `{ARCHIVED_CHANGE}`\nMember Status: `complete`\n",
        encoding="utf-8",
    )
    return folder


class _ArchiveCase(unittest.TestCase):
    """A repository with an archive under the second profile."""

    archive_enabled = True

    def setUp(self) -> None:
        self.srv = load_server()
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = _make_repo(Path(self._tmp.name).resolve())
        self.waves, self.plans = _live_roots(self.root, self.srv.record_paths)
        self.waves.mkdir(parents=True, exist_ok=True)
        self.plans.mkdir(parents=True, exist_ok=True)
        self.archived_folder = _write_archive(self.root)
        self._enable(self.archive_enabled)

    def _enable(self, enabled: bool) -> None:
        rps, vps = _module_copies(self.srv)
        layout = patch_layout(modules=rps, archive_root=ARCHIVE_REL if enabled else None)
        layout.__enter__()
        self.addCleanup(layout.__exit__, None, None, None)
        for vp in vps:
            profile = patch.object(vp, "ARCHIVE_PROFILE", SECOND if enabled else None)
            profile.start()
            self.addCleanup(profile.stop)


# ---------------------------------------------------------------------------
# AC-2: reads
# ---------------------------------------------------------------------------

class ArchiveReadTests(_ArchiveCase):
    def test_change_found_by_id_and_marked_archived(self) -> None:
        got = self.srv.wf_get_change_response(self.root, "1a001")
        self.assertEqual(got["status"], "ok")
        change = got["data"]["change"]
        self.assertEqual(change["change_id"], ARCHIVED_CHANGE)
        self.assertTrue(change["archived"])
        self.assertTrue(change["path"].startswith(ARCHIVE_REL + "/"))

    def test_wave_found_by_id_with_members_from_the_archive_only(self) -> None:
        # A live plan with the member's id must not be mixed in (N2).
        (self.plans / f"{ARCHIVED_CHANGE}.md").write_text("# live copy\n", encoding="utf-8")
        got = self.srv.wf_get_change_response(self.root, "", wave_id="1a000")
        data = got["data"]
        self.assertTrue(data["archived"])
        self.assertEqual(data["wave"]["wave_id"], ARCHIVED_WAVE)
        self.assertEqual([c["id"] for c in data["changes"]], [ARCHIVED_CHANGE])
        member = data["changes"][0]
        self.assertEqual(member["status"], "complete")
        self.assertTrue(member["path"].startswith(ARCHIVE_REL + "/"))
        self.assertTrue(member["archived"])

    @unittest.skipIf(os.name == "nt", "creating symlinks needs a privilege on Windows")
    def test_symlinked_archive_document_is_not_served(self) -> None:
        # N1: an archived file that resolves outside the archive is skipped.
        outside = self.root / "secret.md"
        outside.write_text("Member ID: `1a099-feat leak`\n", encoding="utf-8")
        (self.archived_folder / "1a099-feat leak.md").symlink_to(outside)
        got = self.srv.wf_get_change_response(self.root, "1a099")
        self.assertIsNone(got["data"]["change"])

    def test_live_record_wins_over_the_archive(self) -> None:
        _live_record(self.waves / "1a000 new-set", "1a000 new-set", status="active", vp=self.srv._vocab)
        got = self.srv.wf_get_change_response(self.root, "", wave_id="1a000")
        self.assertNotIn("archived", got["data"])

    def test_new_ids_skip_archived_prefixes(self) -> None:
        import lifecycle_id

        prefixes = lifecycle_id._existing_prefixes(self.root)
        self.assertLessEqual({"1a000", "1a001"}, prefixes)
        self.assertGreaterEqual(lifecycle_id.scan_max_prefix_value(self.root) or 0,
                                int("1a001", 36))

    def test_dashboard_serves_the_archived_change_with_the_header(self) -> None:
        import test_dashboard_server as dashboard_tests

        case = dashboard_tests.DashboardDocumentLayoutTests(methodName="run")
        _, case.srv = dashboard_tests.load_dashboard_modules()
        case.root = self.root
        case.snapshot = {}
        with patch_layout(modules=(case.srv.record_paths,), archive_root=ARCHIVE_REL):
            handler = case._make_handler(
                f"/api/doc?type=change&id={ARCHIVED_CHANGE.replace(' ', '%20')}&wave=1a000")
            handler.server.snapshot_store._record_roots = case.srv.record_paths.load_record_roots(self.root)
            with patch.object(case.srv._vocab, "ARCHIVE_PROFILE", SECOND):
                handler.do_GET()
        self.assertEqual(handler.response_code, 200, handler.error_message)
        self.assertIn(("X-Wavefoundry-Archived", "1"), handler.headers_written)
        self.assertIn("# Old Thing", handler.wfile.getvalue().decode())


class ArchiveUnsetControlTests(_ArchiveCase):
    archive_enabled = False

    def test_nothing_is_found_without_the_archive(self) -> None:
        self.assertIsNone(self.srv.wf_get_change_response(self.root, "1a001")["data"]["change"])
        got = self.srv.wf_get_change_response(self.root, "", wave_id="1a000")
        self.assertEqual([d["code"] for d in got["diagnostics"]], ["wave_not_found"])
        import lifecycle_id

        self.assertNotIn("1a000", lifecycle_id._existing_prefixes(self.root))
        rp = self.srv.record_paths
        self.assertEqual(rp.layout_constants(), (rp.WAVES_ROOT, rp.PLANS_ROOT, rp.NESTED, rp.MAX_DEPTH))

    def test_writers_report_not_found(self) -> None:
        got = self.srv.wf_review_wave_response(self.root, "1a000")
        self.assertEqual([d["code"] for d in got["diagnostics"]], ["wave_not_found"])


# ---------------------------------------------------------------------------
# AC-3: writers refuse; nothing under the archive changes
# ---------------------------------------------------------------------------

class ArchiveWriterRefusalTests(_ArchiveCase):
    def _calls(self):
        srv, root, wave, change = self.srv, self.root, "1a000", ARCHIVED_CHANGE
        return {
            "wf_add_change (wave)": lambda: srv.wf_add_change_response(root, wave, "1zzzz-feat x", mode="create"),
            "wf_remove_change": lambda: srv.wf_remove_change_response(root, wave, change, mode="create"),
            "wf_mark_ac": lambda: srv._mark_change_item_response(
                root, wave, change, "AC-1", "x", target_section="Acceptance Criteria", mode="create"),
            "wf_mark_task": lambda: srv._mark_change_item_response(
                root, wave, change, "Do it.", "x", target_section="Tasks", mode="create"),
            "wf_review_event": lambda: srv.wf_review_event_response(
                root, wave, "run", "wave-council", "ctx", mode="create", run_kind="readiness"),
            "wf_prepare_wave": lambda: srv.wf_prepare_wave_response(root, wave, mode="create"),
            "wf_pause_wave": lambda: srv.wf_pause_wave_response(root, wave, mode="create"),
            "wf_review_wave": lambda: srv.wf_review_wave_response(root, wave),
            "wf_implement_wave": lambda: srv.wf_implement_wave_response(root, wave, mode="create"),
            "wf_close_wave": lambda: srv.wf_close_wave_response(root, wave, mode="create"),
            "wf_reopen_wave": lambda: srv.wf_reopen_wave_response(root, wave),
        }

    def test_every_writer_refuses_an_archived_wave_and_writes_nothing(self) -> None:
        before = _tree_digest(self.root / ARCHIVE_REL)
        calls = self._calls()
        self.assertEqual(len(calls), 11)
        for name, call in calls.items():
            with self.subTest(writer=name):
                response = call()
                codes = [d["code"] for d in response.get("diagnostics", [])]
                self.assertIn("archived_record_read_only", codes, response)
                self.assertNotIn("wave_not_found", codes)
        self.assertEqual(_tree_digest(self.root / ARCHIVE_REL), before)

    def test_add_change_refuses_an_archived_change(self) -> None:
        _live_record(self.waves / "1b000 live", "1b000 live", status="planned", title="Live", vp=self.srv._vocab)
        before = _tree_digest(self.root / ARCHIVE_REL)
        response = self.srv.wf_add_change_response(self.root, "1b000", "1a001", mode="create")
        self.assertIn("archived_record_read_only", [d["code"] for d in response["diagnostics"]])
        self.assertEqual(_tree_digest(self.root / ARCHIVE_REL), before)

    def _garden(self, args: list[str], archive_root):
        return run_script_with_layout(
            SCRIPTS_DIR / "docs_gardener.py", args,
            layout={"archive_root": archive_root},
            env={**os.environ, "PROJECT_ROOT": str(self.root)}, cwd=self.root,
        )

    def test_gardener_never_stamps_an_archived_file(self) -> None:
        archived_doc = f"{ARCHIVE_REL}/{ARCHIVED_WAVE}/{ARCHIVED_CHANGE}.md"
        doc = self.root / archived_doc
        before = _tree_digest(self.root / ARCHIVE_REL)
        for args in (["--paths", archived_doc], ["--all-docs"]):
            with self.subTest(args=args):
                result = self._garden(args, ARCHIVE_REL)
                self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(_tree_digest(self.root / ARCHIVE_REL), before)
        # Control: with the archive unset the same file is an ordinary doc and is stamped.
        control = self._garden(["--paths", archived_doc], None)
        self.assertEqual(control.returncode, 0, control.stderr)
        self.assertNotIn("Last verified: 2020-01-01", doc.read_text(encoding="utf-8"))


class ArchiveUntouchedByLiveLifecycleTests(_ArchiveCase):
    """AC-3: a full live lifecycle, gardening and lint leave the archive byte-identical."""

    def setUp(self) -> None:
        super().setUp()
        config = self.root / "docs" / "workflow-config.json"
        import json

        data = json.loads(config.read_text(encoding="utf-8"))
        data["wave_review"] = {"enabled": True, "delivery_mode": "targeted"}
        config.write_text(json.dumps(data), encoding="utf-8")

    def test_full_live_lifecycle_leaves_the_archive_unchanged(self) -> None:
        srv, root = self.srv, self.root
        before = _tree_digest(root / ARCHIVE_REL)
        integrity = {"test_ran_without_unintended_skip": True, "public_path_reached": True,
                     "boundary_values_realistic": True, "assertions_non_vacuous": True,
                     "known_bad_detected": True, "known_bad_detection_method": "fixture control"}

        def ok(step, response):
            self.assertEqual(response.get("status"), "ok", f"{step}: {response}")
            return response.get("data", {})

        def event(step, wave_id, kind, actor, context, **kwargs):
            return ok(step, srv.wf_review_event_response(
                root, wave_id, kind, actor, context, mode="create", fresh_context=True, independent=True,
                evidence={"observed": "fixture", "artifact_or_test_id": "archive:" + context},
                integrity_checks=dict(integrity), **kwargs))

        stubs = dict(
            run_validate=lambda *a, **k: {"passed": True, "errors": [], "warnings": [], "output": "ok\n"},
            run_garden=lambda *a, **k: {"passed": True, "files_updated": 0, "updated": [], "output": "ok\n"},
            _run_post_write_lint=lambda *a, **k: {"mode": "stubbed"},
        )
        with patch.multiple(srv, **stubs):
            wave_id = ok("create", srv.wf_create_wave_response(root, "live-work", mode="create"))["wave_id"]
            change_id = srv.new_change(root, "feat", "live-thing")["id"]
            plan = self.plans / f"{change_id}.md"
            text = plan.read_text(encoding="utf-8")
            for old, new in (("- [ ] AC-1: [Testable outcome]", "- [x] AC-1: Works."),
                             ("- [ ] [Concrete implementation step]", "- [x] Do it."),
                             ("| AC-1 | required / important / nice-to-have / not-this-scope | |",
                              "| AC-1 | required | Core |")):
                text = text.replace(old, new)
            plan.write_text(text, encoding="utf-8")
            ok("admit", srv.wf_add_change_response(root, wave_id, change_id, mode="create"))
            lanes = srv.wf_prepare_wave_response(root, wave_id, mode="ready")["data"]["review_policy"]["required_lanes"]
            event("readiness run", wave_id, "run", "wave-council", "r-run", run_kind="readiness", cycle=0)
            for lane in lanes:
                event("readiness " + lane, wave_id, "approval", lane, "r-" + lane,
                      signoff_key=lane, approval_phase="readiness")
            event("readiness council", wave_id, "approval", "wave-council", "r-council",
                  signoff_key="wave-council-readiness", approval_phase="readiness")
            ok("prepare create", srv.wf_prepare_wave_response(root, wave_id, mode="create"))
            status_label = srv._vocab.MEMBER_STATUS_LABEL
            record = next(self.waves.glob(f"{wave_id.split()[0]} */{srv._vocab.RECORD_FILENAME}"))
            for path in (record, record.parent / f"{change_id}.md"):
                path.write_text(path.read_text(encoding="utf-8").replace(
                    f"{status_label}: `planned`", f"{status_label}: `complete`"), encoding="utf-8")
            reviewed = srv.wf_review_wave_response(root, wave_id)
            event("delivery run", wave_id, "run", "wave-council", "d-run", run_kind="initial_delivery", cycle=0)
            for lane in [lane for lane in reviewed["data"]["required_lanes"] if lane != "operator"]:
                event("delivery " + lane, wave_id, "approval", lane, "d-" + lane,
                      signoff_key=lane, approval_phase="delivery")
            event("delivery council", wave_id, "approval", "wave-council", "d-council",
                  signoff_key="wave-council-delivery", approval_phase="delivery")
            event("operator", wave_id, "approval", "operator", "op", signoff_key="operator-signoff",
                  approval_phase="delivery")
            closed = srv.wf_close_wave_response(root, wave_id, mode="create")
            self.assertEqual(closed["status"], "ok", closed)
        env = {**os.environ, "PROJECT_ROOT": str(root)}
        archived_doc = f"{ARCHIVE_REL}/{ARCHIVED_WAVE}/{ARCHIVED_CHANGE}.md"
        for script, args in ((SCRIPTS_DIR / "docs_gardener.py", ["--all-docs"]),
                             (SCRIPTS_DIR / "docs_gardener.py", ["--paths", archived_doc]),
                             (SCRIPTS_DIR / "docs_lint.py", [])):
            run_script_with_layout(script, args, layout={"archive_root": ARCHIVE_REL}, env=env, cwd=root)
        self.assertEqual(_tree_digest(root / ARCHIVE_REL), before)


# ---------------------------------------------------------------------------
# AC-4: layout validation
# ---------------------------------------------------------------------------

class ArchiveLayoutValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name).resolve()
        self.waves, self.plans = _live_roots(self.root)
        self.waves.mkdir(parents=True)
        self.plans.mkdir(parents=True)
        self.waves_rel = record_paths.load_record_roots(self.root).waves_rel
        self.plans_rel = record_paths.load_record_roots(self.root).plans_rel

    def _errors(self, archive_root) -> list[str]:
        with patch_layout(modules=(record_paths,), archive_root=archive_root):
            return record_paths.validate_record_layout(self.root)

    def test_valid_archive_root(self) -> None:
        self.assertEqual(self._errors(ARCHIVE_REL), [])

    def _assert_refused(self, values) -> None:
        for value in values:
            with self.subTest(archive_root=value):
                errors = self._errors(value)
                self.assertTrue(errors, value)
                self.assertTrue(any("record_paths.ARCHIVE_ROOT" in e for e in errors), errors)
                with patch_layout(modules=(record_paths,), archive_root=value), \
                        self.assertRaises(record_paths.RecordLayoutInvalid):
                    record_paths.load_record_roots(self.root)

    def test_overlapping_or_escaping_roots_refuse(self) -> None:
        # The live roots, a folder inside one, their common parent, an absolute and an escaping path.
        self._assert_refused((self.waves_rel, self.waves_rel + "/old", "docs", self.plans_rel, "/abs/archive", "../x"))

    @unittest.skipIf(os.name == "nt", "creating symlinks needs a privilege on Windows")
    def test_symlink_escape_or_alias_roots_refuse(self) -> None:
        outside = Path(self._tmp.name).resolve().parent / (Path(self._tmp.name).name + "-outside")
        outside.mkdir()
        self.addCleanup(shutil.rmtree, outside, True)
        (self.root / "docs" / "escape").symlink_to(outside, target_is_directory=True)
        (self.root / "docs" / "alias").symlink_to(self.waves, target_is_directory=True)
        self._assert_refused(("docs/escape", "docs/alias"))


# ---------------------------------------------------------------------------
# AC-5: profile validation and lint
# ---------------------------------------------------------------------------

class ArchiveProfileValidationTests(unittest.TestCase):
    def test_missing_extra_and_invalid_fields_refuse(self) -> None:
        missing = dict(SECOND)
        missing.pop("ID_KEY")
        extra = dict(SECOND, SURPRISE="x")
        invalid = dict(SECOND, RECORD_FILENAME="set.txt")
        for mapping, field in ((missing, "ID_KEY"), (extra, "SURPRISE"), (invalid, "RECORD_FILENAME")):
            with self.subTest(field=field), patch.object(vocabulary_profile, "ARCHIVE_PROFILE", mapping):
                with self.assertRaisesRegex(vocabulary_profile.VocabularyProfileInvalid,
                                            rf"ARCHIVE_PROFILE: .*{field}"):
                    vocabulary_profile.validate()

    def test_valid_profile_and_default(self) -> None:
        self.assertEqual(vocabulary_profile.validation_errors(SECOND), [])
        with patch.object(vocabulary_profile, "ARCHIVE_PROFILE", None):
            self.assertEqual(vocabulary_profile.archive_profile().RECORD_FILENAME,
                             vocabulary_profile.RECORD_FILENAME)


class ArchiveLintTests(unittest.TestCase):
    def setUp(self) -> None:
        import test_docs_lint as docs_lint_tests

        self.helper = docs_lint_tests.DocsLintFixtureTests()
        self.root = self.helper.copy_fixture()
        self.addCleanup(shutil.rmtree, self.root, True)
        self.folder = _write_archive(self.root)
        # An archived document that breaks live rules: no metadata header, a
        # dead relative link.
        (self.folder / "notes.md").write_text("# Notes\n\nSee [gone](../missing.md).\n", encoding="utf-8")

    def _lint(self, *args: str, archive: bool = True) -> subprocess.CompletedProcess[str]:
        layout = {"archive_root": ARCHIVE_REL} if archive else {}
        code_env = {**os.environ, "PROJECT_ROOT": str(self.root)}
        prelude = f"import vocabulary_profile as _vp; _vp.ARCHIVE_PROFILE = {SECOND!r}\n" if archive else ""
        handle, name = tempfile.mkstemp(suffix="-lint.py")
        os.close(handle)
        script = Path(name)
        script.write_text(prelude + f"import runpy; runpy.run_path({str(SCRIPTS_DIR / 'docs_lint.py')!r}, run_name='__main__')\n",
                          encoding="utf-8")
        self.addCleanup(script.unlink, True)
        return run_script_with_layout(script, list(args), layout=layout, env=code_env, cwd=self.root)

    def test_full_lint_skips_archived_documents(self) -> None:
        result = self._lint()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn(ARCHIVE_REL, result.stderr)
        control = self._lint(archive=False)
        self.assertNotEqual(control.returncode, 0)
        self.assertIn(ARCHIVE_REL, control.stderr)

    def test_changed_file_lint_skips_archived_documents(self) -> None:
        env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com",
               "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.com"}
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True, env=env)
        waves_rel = record_paths.load_record_roots(self.root).waves_rel
        subprocess.run(["git", "add", "-A", "--", waves_rel, "docs/workflow-config.json"], cwd=self.root,
                       check=True, env=env)
        subprocess.run(["git", "commit", "-qm", "base"], cwd=self.root, check=True, env=env)
        result = self._lint("--changed")
        self.assertNotIn(f"{ARCHIVE_REL}/{ARCHIVED_WAVE}/notes.md", result.stderr)
        control = self._lint("--changed", archive=False)
        self.assertIn(f"{ARCHIVE_REL}/{ARCHIVED_WAVE}/notes.md", control.stderr)

    def test_unreadable_archived_record_is_an_advisory_warning(self) -> None:
        (self.folder / "set.md").write_bytes(b"\xff\xfe not utf-8")
        result = self._lint()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertRegex(result.stderr, r"(?m)^WARNING: .*archived record cannot be read.*archive_record_unreadable")

    def test_secrets_scan_still_covers_the_archive(self) -> None:
        import test_secrets_validators as secrets_tests
        from wave_lint_lib.secrets_validators import check_hardcoded_secrets

        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            secrets_tests._make_root(repo)
            secrets_tests._write_framework_toml(repo)
            leak = repo / ARCHIVE_REL / "1a000 old" / "notes.md"
            leak.parent.mkdir(parents=True)
            leak.write_text('key = "sk_live_ABCDEFGHIJKLMNOPQRSTUVWX"\n', encoding="utf-8")
            with patch_layout(modules=(record_paths,), archive_root=ARCHIVE_REL), \
                    patch("wave_lint_lib.secrets_validators.get_current_git_user_email", return_value="t@x.com"):
                errors = check_hardcoded_secrets(repo, scan_all=True)
        self.assertTrue(any("test-stripe-key" in e for e in errors), errors)


if __name__ == "__main__":
    unittest.main()
