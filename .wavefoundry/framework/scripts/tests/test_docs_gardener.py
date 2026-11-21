from __future__ import annotations

import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import contextmanager, redirect_stdout
from pathlib import Path
from unittest.mock import patch


TESTS_ROOT = Path(__file__).resolve().parent
SCRIPTS_ROOT = TESTS_ROOT.parent


def _load_gardener():
    path = SCRIPTS_ROOT / "docs_gardener.py"
    spec = importlib.util.spec_from_file_location("docs_gardener_test_module", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)
    return mod


dg = _load_gardener()


@contextmanager
def _windows_default_text_writes():
    """Real I/O with Windows' default write translation; not native qualification."""
    original_open = Path.open

    def open_with_windows_default(path, mode="r", buffering=-1, encoding=None,
                                  errors=None, newline=None):
        if "w" in mode and "b" not in mode and newline is None:
            newline = "\r\n"
        return original_open(path, mode, buffering, encoding, errors, newline)

    with patch.object(Path, "open", open_with_windows_default):
        yield


class GardenerLineEndingTests(unittest.TestCase):
    def _run(self, root):
        with redirect_stdout(io.StringIO()) as out:
            code, paths = dg.gardener_run(
                root, dg.parse_args(["--paths", "docs/sample.md", "--date", "2026-10-11"])
            )
        self.assertEqual(code, 0)
        return paths, out.getvalue()

    def _doc(self, root, newline=b"\n", date=b"2000-01-01"):
        path = root / "docs/sample.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        content = (b"# Sample\nOwner: Engineering\nStatus: active\nLast verified: "
                   + date + "\n\nBody café; 2000-01-01.\n".encode()).replace(b"\n", newline)
        path.write_bytes(content)
        return path, content

    def test_metadata_preserves_exact_lf_crlf_bytes_under_windows_translation(self):
        for newline in (b"\n", b"\r\n"):
            with self.subTest(newline=newline), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                path, before = self._doc(root, newline)
                if os.name != "nt":
                    path.chmod(0o640)
                mode = path.stat().st_mode
                with _windows_default_text_writes():
                    paths, output = self._run(root)
                self.assertEqual(path.read_bytes(), before.replace(b"2000-01-01", b"2026-10-11", 1))
                self.assertEqual(path.stat().st_mode, mode)
                self.assertIn("docs/sample.md", paths)
                self.assertIn("docs-gardener: updated docs/sample.md", output)
                self.assertIn("docs-gardener: stamped 1 doc(s)", output)
                published = [path, dg.manifest_path(root), root / "docs/agents/session-handoff.md"]
                state = [(p.read_bytes(), p.stat().st_mtime_ns) for p in published]
                with _windows_default_text_writes():
                    paths, output = self._run(root)
                self.assertEqual(paths, [])
                self.assertEqual(output.strip(), "docs-gardener: ok (nothing to report)")
                self.assertEqual([(p.read_bytes(), p.stat().st_mtime_ns) for p in published], state)

    def test_new_manifest_and_handoff_are_lf_with_windows_default_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._doc(root, date=b"2026-10-11")
            with _windows_default_text_writes():
                paths, _ = self._run(root)
            for path in (dg.manifest_path(root), root / "docs/agents/session-handoff.md"):
                self.assertIn(path.relative_to(root).as_posix(), paths)
                self.assertIn(b"\n", path.read_bytes())
                self.assertNotIn(b"\r", path.read_bytes())

    def test_manifest_reconcile_and_noop_preserve_lf_crlf_and_project_values(self):
        for newline in ("\n", "\r\n"):
            with self.subTest(newline=newline), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                self._doc(root, date=b"2026-10-11")
                path = dg.manifest_path(root)
                path.parent.mkdir(parents=True, exist_ok=True)
                data = dg.default_manifest_payload(root)
                data.pop("generated_artifacts")
                data["project-owned"] = "café"
                path.write_bytes(dg.normalize_manifest_json(data).replace("\n", newline).encode())
                expected = dict(data, generated_artifacts=dg.default_manifest_payload(root)["generated_artifacts"])
                with _windows_default_text_writes():
                    paths, _ = self._run(root)
                self.assertIn(path.relative_to(root).as_posix(), paths)
                self.assertEqual(path.read_bytes(), dg.normalize_manifest_json(expected).replace("\n", newline).encode())
                before = path.read_bytes(), path.stat().st_mtime_ns
                with _windows_default_text_writes():
                    paths, _ = self._run(root)
                self.assertNotIn(path.relative_to(root).as_posix(), paths)
                self.assertEqual((path.read_bytes(), path.stat().st_mtime_ns), before)

    def test_existing_handoff_and_unstamped_file_are_byte_and_mtime_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            doc, _ = self._doc(root)
            doc.write_bytes(b"# No metadata\r\nBody\r\n")
            handoff = root / "docs/agents/session-handoff.md"
            handoff.parent.mkdir(parents=True)
            handoff.write_bytes(b"# Project handoff\r\nKeep this\r\n")
            watched = [doc, handoff]
            before = [(p.read_bytes(), p.stat().st_mtime_ns) for p in watched]
            with _windows_default_text_writes():
                paths, _ = self._run(root)
            self.assertNotIn("docs/sample.md", paths)
            self.assertNotIn("docs/agents/session-handoff.md", paths)
            self.assertEqual([(p.read_bytes(), p.stat().st_mtime_ns) for p in watched], before)

    def test_public_cli_preserves_crlf_date_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path, before = self._doc(root, b"\r\n")
            env = dict(os.environ, PROJECT_ROOT=str(root), PYTHONDONTWRITEBYTECODE="1")
            env.pop("PYTHONPYCACHEPREFIX", None)
            proc = subprocess.run(
                [sys.executable, "-B", str(SCRIPTS_ROOT / "docs_gardener.py"),
                 "--paths", "docs/sample.md", "--date", "2026-10-11"],
                env=env, capture_output=True, text=True, timeout=30,
            )
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertEqual(path.read_bytes(), before.replace(b"2000-01-01", b"2026-10-11", 1))


class DocsGardenerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp(prefix="docs-gardener-test-"))

    def tearDown(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)

    def _write_doc(self, rel: str, last_verified: str = "2000-01-01") -> Path:
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(
            f"# T\n\nOwner: Engineering\nStatus: draft\nLast verified: {last_verified}\n",
            encoding="utf-8",
        )
        return p

    def _minimal_manifest(self) -> None:
        # 1v7a0: carries the CURRENT default `generated_artifacts`. Before
        # reconciliation existed, omitting it was harmless; now an incomplete
        # list is real work, so a fixture without it would make an "empty run"
        # non-empty and assert the wrong thing. The framework-owned list is
        # sourced from `default_manifest_payload` rather than hardcoded, so this
        # fixture cannot drift from the default the way a real manifest did.
        mp = self.root / "docs" / "prompts" / "prompt-surface-manifest.json"
        mp.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": 1,
            "framework_revision": "2099-01-01a",
            "public_prompt_surface": [],
            "seed_framework_source": "test",
            "generated_artifacts": dg.default_manifest_payload()[
                "generated_artifacts"
            ],
        }
        # Written through the gardener's OWN normalizer, so the fixture is
        # byte-identical to what a real gardened manifest looks like. Hand-rolled
        # json.dumps would differ by key order alone (`sort_keys=True`) and make
        # every run report a rewrite — a fixture artefact, not behaviour.
        mp.write_text(dg.normalize_manifest_json(payload), encoding="utf-8")

    def _ensure_session_handoff(self) -> None:
        sh = self.root / "docs" / "agents" / "session-handoff.md"
        sh.parent.mkdir(parents=True, exist_ok=True)
        sh.write_text(
            "# Session Handoff\n\nOwner: Engineering\nStatus: generated\nLast verified: 2000-01-01\n",
            encoding="utf-8",
        )

    def test_default_run_stamps_changed_docs(self) -> None:
        self._init_git()
        tracked = self._write_doc("docs/tracked.md", "2000-01-01")
        subprocess.run(
            ["git", "-C", str(self.root), "add", "docs/tracked.md"],
            check=True, capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(self.root), "commit", "-m", "init"],
            check=True, capture_output=True,
        )
        other = self._write_doc("docs/other.md", "2000-01-01")
        self._minimal_manifest()
        tracked.write_text(tracked.read_text(encoding="utf-8") + "\n## touch\n", encoding="utf-8")
        code, _ = dg.gardener_run(self.root, dg.parse_args(["--date", "2020-06-01"]))
        self.assertEqual(code, 0)
        self.assertIn("Last verified: 2020-06-01", tracked.read_text(encoding="utf-8"))
        self.assertIn("Last verified: 2000-01-01", other.read_text(encoding="utf-8"))

    def test_preserve_handoff_excludes_its_stamp_and_scaffold_only(self):
        handoff = self._write_doc("docs/agents/session-handoff.md")
        other = self._write_doc("docs/other.md")
        before = handoff.read_bytes()
        args = dg.parse_args(["--all-docs", "--date", "2020-06-01", "--preserve-handoff"])
        dg.gardener_run(self.root, args)
        self.assertEqual(handoff.read_bytes(), before)
        self.assertIn("Last verified: 2020-06-01", other.read_text())
        handoff.unlink()
        dg.gardener_run(self.root, args)
        self.assertFalse(handoff.exists())

    def test_verification_stamp_is_untouched_by_gardener_runs(self) -> None:
        # 1ro43 AC-11: the gardener's only edit is the `Last verified:` date
        # substitution — a `Verified against:` stamp line must survive a
        # stamping run byte-identical (stamp-field invariance, not whole-file
        # identity: newline handling may differ across platforms).
        stamp_line = "Verified against: abc1234def5678"
        p = self.root / "docs" / "stamped.md"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(
            "# T\n\nOwner: Engineering\nStatus: draft\n"
            f"Last verified: 2000-01-01\n{stamp_line}\n\nBody prose.\n",
            encoding="utf-8",
        )
        self._minimal_manifest()
        code, _ = dg.gardener_run(
            self.root,
            dg.parse_args(["--date", "2020-06-01", "--paths", "docs/stamped.md"]),
        )
        self.assertEqual(code, 0)
        text = p.read_text(encoding="utf-8")
        self.assertIn("Last verified: 2020-06-01", text)  # the date DID move
        self.assertIn(f"\n{stamp_line}\n", text)          # the stamp did not

    def test_paths_updates_target_only(self) -> None:
        a = self._write_doc("docs/a.md", "2000-01-01")
        b = self._write_doc("docs/b.md", "2000-01-01")
        self._minimal_manifest()
        code, paths = dg.gardener_run(
            self.root,
            dg.parse_args(["--date", "2020-06-01", "--paths", "docs/a.md"]),
        )
        self.assertEqual(code, 0)
        self.assertIn("Last verified: 2020-06-01", a.read_text(encoding="utf-8"))
        self.assertIn("Last verified: 2000-01-01", b.read_text(encoding="utf-8"))
        self.assertTrue(any("docs/a.md" in p for p in paths))

    def test_all_docs_and_paths_are_mutually_exclusive(self) -> None:
        self._write_doc("docs/a.md")
        with self.assertRaises(SystemExit):
            dg.gardener_run(self.root, dg.parse_args(["--all-docs", "--paths", "docs/a.md"]))

    def test_all_docs_stamps_every_doc(self) -> None:
        a = self._write_doc("docs/a.md", "2000-01-01")
        b = self._write_doc("docs/b.md", "2000-01-01")
        self._minimal_manifest()
        code, _ = dg.gardener_run(self.root, dg.parse_args(["--date", "2020-06-01", "--all-docs"]))
        self.assertEqual(code, 0)
        self.assertIn("Last verified: 2020-06-01", a.read_text(encoding="utf-8"))
        self.assertIn("Last verified: 2020-06-01", b.read_text(encoding="utf-8"))

    def test_stamping_run_writes_no_reindex_report(self) -> None:
        """Wave 1tbvo: the daily reindex-report artifact is retired — a
        stamping run stamps docs, prints a summary, and writes NOTHING under
        docs/reports/; the render_report helper no longer exists."""
        self._write_doc("docs/a.md", "2000-01-01")
        self._minimal_manifest()
        self._ensure_session_handoff()
        out = io.StringIO()
        with redirect_stdout(out):
            code, paths = dg.gardener_run(
                self.root, dg.parse_args(["--date", "2020-06-01", "--paths", "docs/a.md"])
            )
        self.assertEqual(code, 0)
        self.assertTrue(any("docs/a.md" in p for p in paths))
        reports_dir = self.root / "docs" / "reports"
        self.assertFalse(
            reports_dir.exists() and any(reports_dir.iterdir()),
            "a stamping run must not create anything under docs/reports/",
        )
        self.assertFalse(any("docs/reports/" in p for p in paths))
        # Stable output contract (parsed by run_garden in server_impl.py):
        # one `updated <path>` line per updated file, then the count summary.
        lines = out.getvalue().strip().splitlines()
        self.assertEqual(lines[-1], "docs-gardener: stamped 1 doc(s)")
        self.assertIn("docs-gardener: updated docs/a.md", lines)
        for line in lines[:-1]:
            self.assertTrue(line.startswith("docs-gardener: updated "), line)
        self.assertFalse(hasattr(dg, "render_report"))

    def test_empty_run_prints_nothing_to_report(self) -> None:
        self._minimal_manifest()
        self._ensure_session_handoff()
        out = io.StringIO()
        with redirect_stdout(out):
            code, paths = dg.gardener_run(self.root, dg.parse_args(["--date", "2020-06-01"]))
        self.assertEqual(code, 0)
        self.assertEqual(paths, [])
        self.assertEqual(out.getvalue().strip(), "docs-gardener: ok (nothing to report)")

    def _init_git(self) -> None:
        subprocess.run(
            ["git", "-C", str(self.root), "init"],
            check=True, capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(self.root), "config", "user.email", "t@e.st"],
            check=True, capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(self.root), "config", "user.name", "test"],
            check=True, capture_output=True,
        )

    def test_cli_subprocess_smoke(self) -> None:
        self._write_doc("docs/a.md")
        env = os.environ.copy()
        env["PROJECT_ROOT"] = str(self.root)
        proc = subprocess.run(
            [sys.executable, str(SCRIPTS_ROOT / "docs_gardener.py"), "--date", "2020-01-03"],
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)


if __name__ == "__main__":
    unittest.main()


class ManifestReconciliationTests(unittest.TestCase):
    """1v7a0: an existing manifest reconciles against `default_manifest_payload`.

    Before this change, `ensure_manifest` on an existing file only performed two
    `setdefault` calls and stamped `last_gardened_at`, so the generated-artifact
    list froze at install time. Because the file is renderer-managed it is also
    excluded from the reconciliation scan by basename, so nothing surfaced the
    drift either. Field-reported downstream on 1.16.2.
    """

    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp(prefix="manifest-reconcile-"))
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        self.path = self.root / "docs" / "prompts" / "prompt-surface-manifest.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _write(self, payload: dict) -> None:
        self.path.write_text(
            json.dumps(payload, indent=2) + "\n", encoding="utf-8"
        )

    def _read(self) -> dict:
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _drifted_payload(self) -> dict:
        """Drifted in BOTH directions, plus non-default keys with live consumers."""
        return {
            "schema_version": 1,
            # Carries a retired entry; missing several current default entries.
            "generated_artifacts": [
                "docs/agents/journals/",
                "docs/prompts/prompt-surface-manifest.json",
            ],
            "enabled_internal_features": ["agent_journals", "wave_lifecycle"],
            "last_gardened_at": "2026-01-01",
            "public_prompt_surface": [],
            "seed_framework_source": ".wavefoundry/framework",
            # NOT in default_manifest_payload, and each has a real consumer:
            # wave_root is read by wave_lint_lib, framework_revision by
            # check_version/dashboard_lib, upgrade_merge_notes by reconcile_scan.
            "wave_root": "docs/waves",
            "framework_revision": "1.16.1+pimb",
            "upgrade_merge_notes": ["kept"],
        }

    def test_retired_entry_is_removed(self) -> None:
        """AC-1, using the field-reported entry."""
        self._write(self._drifted_payload())
        dg.ensure_manifest(self.root)
        self.assertNotIn("docs/agents/journals/", self._read()["generated_artifacts"])

    def test_entry_added_to_the_default_arrives(self) -> None:
        """AC-2: the direction the field report did not observe. A repository
        installed before an entry was added never receives it, which leaves the
        framework's own record of what it generates wrong."""
        self._write(self._drifted_payload())
        dg.ensure_manifest(self.root)
        current = dg.default_manifest_payload()["generated_artifacts"]
        self.assertEqual(self._read()["generated_artifacts"], current)

    def test_keys_the_default_does_not_own_survive(self) -> None:
        """AC-3, and this is a regression guard rather than hygiene: clobbering
        `wave_root` would break docs-lint, which reads it through
        wave_lint_lib."""
        self._write(self._drifted_payload())
        dg.ensure_manifest(self.root)
        data = self._read()
        self.assertEqual(data["wave_root"], "docs/waves")
        self.assertEqual(data["framework_revision"], "1.16.1+pimb")
        self.assertEqual(data["upgrade_merge_notes"], ["kept"])

    def test_retired_feature_pruned_but_key_kept(self) -> None:
        """The retired VALUE goes; the key stays. Nothing in this repository
        reads `enabled_internal_features`, but a target repo or host might, and
        a manifest is the wrong place to prove a negative about out-of-tree
        readers."""
        self._write(self._drifted_payload())
        dg.ensure_manifest(self.root)
        data = self._read()
        self.assertIn("enabled_internal_features", data)
        self.assertEqual(data["enabled_internal_features"], ["wave_lifecycle"])

    def test_matching_manifest_is_not_rewritten(self) -> None:
        """AC-4: no churn for healthy repositories. Asserted on bytes AND on the
        returned wrote-flag, so a rewrite that happened to be byte-identical
        would still be caught."""
        self._write(self._drifted_payload())
        dg.ensure_manifest(self.root)
        before = self.path.read_bytes()
        _path, wrote = dg.ensure_manifest(self.root)
        self.assertFalse(wrote)
        self.assertEqual(self.path.read_bytes(), before)

    def test_partial_manifest_gains_the_default_without_losing_content(self) -> None:
        """AC-6: the gardener runs inside the docs gate, so a partial manifest
        must not crash it or discard project content."""
        self._write({"wave_root": "docs/waves"})
        dg.ensure_manifest(self.root)
        data = self._read()
        self.assertEqual(
            data["generated_artifacts"],
            dg.default_manifest_payload()["generated_artifacts"],
        )
        self.assertEqual(data["wave_root"], "docs/waves")

    def test_reconcile_is_a_no_op_when_default_omits_the_key(self) -> None:
        """Polarity: the reconciler assigns only keys the default actually
        carries, so a default without a framework-owned key leaves the
        repository's value alone rather than deleting it."""
        payload = self._drifted_payload()
        original = list(payload["generated_artifacts"])
        result = dg.reconcile_manifest_payload(payload, {"schema_version": 1})
        self.assertEqual(result["generated_artifacts"], original)

    def test_reconciles_through_the_real_entry_point_with_nothing_to_stamp(self) -> None:
        """The defect a post-implementation review caught, pinned at the PUBLIC path.

        `gardener_run` used to pass `bump_last_gardened = bool(updated_paths)`,
        which is False exactly when no doc needed stamping — the steady state of
        a well-gardened repository. The first implementation returned early on
        that flag, so the manifest healed only on runs that happened to stamp
        something else. Asserting through `ensure_manifest` alone missed it
        entirely, because that call site passed the flag directly. 1z8tu removed
        the flag with the date it gated; this run also drops the date key.
        """
        import argparse

        self._write({
            "schema_version": 1,
            "generated_artifacts": ["docs/agents/journals/"],
            "last_gardened_at": "2026-08-12",
            "seed_framework_source": ".wavefoundry/framework",
        })
        # Already current, so nothing needs a stamp.
        (self.root / "docs" / "fresh.md").write_text(
            "# T\n\nOwner: Engineering\nStatus: draft\nLast verified: 2026-08-12\n",
            encoding="utf-8",
        )
        dg.gardener_run(
            self.root,
            argparse.Namespace(date="2026-08-12", paths=None, all_docs=True),
        )
        data = self._read()
        artifacts = data["generated_artifacts"]
        self.assertNotIn("docs/agents/journals/", artifacts)
        self.assertIn("docs/reports/", artifacts)
        # 1z8tu AC-1: a run that stamps nothing still removes the date key.
        self.assertNotIn("last_gardened_at", data)

    def _stale_doc(self) -> Path:
        doc = self.root / "docs" / "stale.md"
        doc.write_text(
            "# T\n\nOwner: Engineering\nStatus: draft\nLast verified: 2000-01-01\n",
            encoding="utf-8",
        )
        return doc

    def _run(self, date_value: str) -> list[str]:
        import argparse

        _code, paths = dg.gardener_run(
            self.root,
            argparse.Namespace(date=date_value, paths=None, all_docs=True),
        )
        return paths

    def test_stamping_run_removes_the_date(self) -> None:
        """1z8tu AC-1: a run that stamps a document drops `last_gardened_at`
        instead of moving it, and the rest of the manifest reconciles and
        survives as before."""
        self._write(self._drifted_payload())
        doc = self._stale_doc()
        paths = self._run("2026-09-28")
        self.assertIn("Last verified: 2026-09-28", doc.read_text(encoding="utf-8"))
        data = self._read()
        self.assertNotIn("last_gardened_at", data)
        self.assertEqual(
            data["generated_artifacts"], dg.default_manifest_payload()["generated_artifacts"]
        )
        self.assertEqual(data["framework_revision"], "1.16.1+pimb")
        self.assertIn("docs/prompts/prompt-surface-manifest.json", paths)

    def test_keyless_manifest_is_not_rewritten_on_a_later_date(self) -> None:
        """1z8tu AC-1: once the key is gone, later gardening days leave the
        manifest byte-identical, whether or not the run stamps a document.
        The stamping case is the one that used to churn the file."""
        self._write(self._drifted_payload())
        self._run("2026-09-01")
        settled = self.path.read_bytes()
        handoff = self.root / "docs" / "agents" / "session-handoff.md"
        for label, stamp in (("nothing stamped", False), ("doc stamped", True)):
            with self.subTest(label):
                if stamp:
                    doc = self._stale_doc()
                    paths = self._run("2026-10-15")
                    self.assertIn("Last verified: 2026-10-15", doc.read_text(encoding="utf-8"))
                else:
                    # The settling run created the handoff with its own date;
                    # bring it to the run's date so this run truly stamps nothing.
                    handoff.write_text(
                        handoff.read_text(encoding="utf-8").replace(
                            "Last verified: 2026-09-01", "Last verified: 2026-10-14"
                        ),
                        encoding="utf-8",
                    )
                    paths = self._run("2026-10-14")
                    self.assertEqual(paths, [])
                self.assertEqual(self.path.read_bytes(), settled)
                self.assertNotIn("docs/prompts/prompt-surface-manifest.json", paths)

    def test_new_manifest_has_no_date(self) -> None:
        """1z8tu AC-2: neither the default payload nor a created manifest
        carries `last_gardened_at`."""
        self.assertNotIn("last_gardened_at", dg.default_manifest_payload())
        _path, wrote = dg.ensure_manifest(self.root)
        self.assertTrue(wrote)
        data = self._read()
        self.assertNotIn("last_gardened_at", data)
        self.assertEqual(
            data["generated_artifacts"], dg.default_manifest_payload()["generated_artifacts"]
        )


class RecordLayoutGardenerTests(unittest.TestCase):
    """Wave 1y0gz: the gardener walks the record roots, not only ``docs/``.

    The layout is the ``record_paths`` constants; these cases patch them
    through ``record_layout_support`` (in-process for the payload/run pins, in
    the child interpreter for the CLI pins) and relocate the waves root outside
    ``docs/``.
    """

    WAVES = "project/records/waves"
    PLANS = "project/records/plans"
    LAYOUT = {"waves_root": WAVES, "plans_root": PLANS}

    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp(prefix="docs-gardener-layout-"))
        (self.root / "docs").mkdir()

    def tearDown(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)

    def _write_doc(self, rel: str, last_verified: str = "2000-01-01") -> Path:
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(
            f"# T\n\nOwner: Engineering\nStatus: draft\nLast verified: {last_verified}\n",
            encoding="utf-8",
        )
        return p

    def _run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        from record_layout_support import run_script_with_layout

        env = os.environ.copy()
        env["PROJECT_ROOT"] = str(self.root)
        return run_script_with_layout(SCRIPTS_ROOT / "docs_gardener.py", list(args), layout=self.LAYOUT, env=env)

    def test_default_manifest_payload_names_the_relocated_waves_root(self) -> None:
        from record_layout_support import patch_layout

        (self.root / "project" / "records" / "waves").mkdir(parents=True)
        # The configured layout (the shipped one, or a profile's).
        configured = dg.record_paths.WAVES_ROOT
        # 1z8tw: patch the gardener's own copy; a prior `load_server()` in this
        # interpreter replaces the `record_paths` that sys.modules holds.
        with patch_layout(modules=(dg.record_paths,), **self.LAYOUT):
            artifacts = dg.default_manifest_payload(self.root)["generated_artifacts"]
        self.assertIn(f"{self.WAVES}/", artifacts)
        self.assertIn(f"{self.WAVES}/README.md", artifacts)
        self.assertFalse(any(entry.startswith(configured) for entry in artifacts), artifacts)
        # The configured layout is unchanged.
        default = dg.default_manifest_payload(self.root)["generated_artifacts"]
        self.assertIn(f"{configured}/", default)
        self.assertIn(f"{configured}/README.md", default)

    def test_paths_accepts_a_doc_under_the_relocated_waves_root(self) -> None:
        rel = f"{self.WAVES}/1abcd wave/wave.md"
        target = self._write_doc(rel)
        proc = self._run_cli("--paths", rel, "--date", "2020-01-03")
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        self.assertIn(f"docs-gardener: updated {rel}", proc.stdout)
        self.assertIn("Last verified: 2020-01-03", target.read_text(encoding="utf-8"))

    def test_paths_outside_docs_and_record_roots_is_refused(self) -> None:
        rel = "elsewhere/note.md"
        self._write_doc(rel)
        proc = self._run_cli("--paths", rel, "--date", "2020-01-03")
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("path must be under docs/ or a record root", proc.stderr)

    def test_all_docs_walks_the_relocated_record_roots(self) -> None:
        in_docs = self._write_doc("docs/a.md")
        in_waves = self._write_doc(f"{self.WAVES}/1abcd wave/wave.md")
        in_plans = self._write_doc(f"{self.PLANS}/1abce-feat thing.md")
        outside = self._write_doc("elsewhere/note.md")
        proc = self._run_cli("--all-docs", "--date", "2020-01-03")
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        for path in (in_docs, in_waves, in_plans):
            self.assertIn("Last verified: 2020-01-03", path.read_text(encoding="utf-8"), path)
        self.assertIn("Last verified: 2000-01-01", outside.read_text(encoding="utf-8"))
        self.assertIn("docs-gardener: stamped 3 doc(s)", proc.stdout)

    def test_invalid_layout_fails_closed_before_any_stamp(self) -> None:
        from record_layout_support import patch_layout

        doc = self._write_doc("docs/a.md")
        args = dg.parse_args(["--all-docs", "--date", "2020-01-03"])
        with patch_layout(modules=(dg.record_paths,), waves_root="../outside-waves"):
            with self.assertRaises(SystemExit) as ctx:
                dg.gardener_run(self.root, args)
        self.assertIn("record_layout_invalid:", str(ctx.exception))
        self.assertIn("Last verified: 2000-01-01", doc.read_text(encoding="utf-8"))


def _local_noon(days_from_today: int) -> float:
    """Local noon of a day counted from the local today, as a POSIX time.

    Built from a naive local datetime so the calendar day is the one the
    gardener reads back with ``date.fromtimestamp`` on every host.
    """
    import datetime as _dt

    day = _dt.date.today() + _dt.timedelta(days=days_from_today)
    return _dt.datetime.combine(day, _dt.time(12, 0)).timestamp()


def _day(days_from_today: int) -> str:
    import datetime as _dt

    return (_dt.date.today() + _dt.timedelta(days=days_from_today)).isoformat()


class DefaultModeStampRuleTests(unittest.TestCase):
    """Change 23qfz: the default mode stamps a Git-changed document only when
    it differs from HEAD outside its date line and changed since its stamp."""

    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp(prefix="docs-gardener-rule-")).resolve()
        self._git("init")
        self._git("config", "user.email", "t@e.st")
        self._git("config", "user.name", "test")
        self._git("config", "core.autocrlf", "false")
        # A normalized manifest and handoff, committed, so a run writes only
        # the documents the rule selects.
        mp = dg.manifest_path(self.root)
        mp.parent.mkdir(parents=True, exist_ok=True)
        mp.write_text(dg.normalize_manifest_json(dg.default_manifest_payload(self.root)),
                      encoding="utf-8", newline="")
        handoff = self.root / "docs" / "agents" / "session-handoff.md"
        handoff.parent.mkdir(parents=True, exist_ok=True)
        handoff.write_bytes(b"# Session Handoff\n\nOwner: Engineering\nStatus: generated\n"
                            b"Last verified: 2000-01-01\n")
        self._git("add", "-A")
        self._git("commit", "-m", "base")

    def tearDown(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)

    def _git(self, *args: str) -> None:
        subprocess.run(["git", "-C", str(self.root), *args], check=True, capture_output=True)

    def _text(self, stamp: str, body: str = "Body.", newline: str = "\n") -> bytes:
        text = f"# Doc\n\nOwner: Engineering\nStatus: active\nLast verified: {stamp}\n\n{body}\n"
        return text.replace("\n", newline).encode("utf-8")

    def _commit(self, rel: str, data: bytes) -> Path:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        self._git("add", rel)
        self._git("commit", "-m", f"add {rel}")
        return path

    def _set_mtime(self, path: Path, days_from_today: int) -> None:
        when = _local_noon(days_from_today)
        os.utime(path, (when, when))

    def _run(self, *argv: str) -> tuple[list[str], list[str]]:
        out = io.StringIO()
        with redirect_stdout(out):
            code, paths = dg.gardener_run(self.root, dg.parse_args(list(argv)))
        self.assertEqual(code, 0)
        updated = [line[len("docs-gardener: updated "):]
                   for line in out.getvalue().splitlines()
                   if line.startswith("docs-gardener: updated ")]
        return paths, updated

    def test_edit_is_stamped_once_and_a_later_run_writes_nothing(self) -> None:
        # AC-1: first edit stamped by a run with the local today (no --date);
        # a later day's run with no further edit leaves the file alone.
        doc = self._commit("docs/a.md", self._text(_day(-10)))
        doc.write_bytes(self._text(_day(-10), "Body, edited."))
        paths, updated = self._run()
        self.assertEqual(updated, ["docs/a.md"])
        self.assertEqual(paths, ["docs/a.md"])
        self.assertEqual(doc.read_bytes(), self._text(_day(0), "Body, edited."))
        before = (doc.read_bytes(), doc.stat().st_mtime_ns)
        paths, updated = self._run("--date", _day(1))
        self.assertEqual((paths, updated), ([], []))
        self.assertEqual((doc.read_bytes(), doc.stat().st_mtime_ns), before)
        # AC-2 case 1: edited again on a later day, stamped by the next run.
        doc.write_bytes(self._text(_day(0), "Body, edited twice."))
        self._set_mtime(doc, 2)
        paths, updated = self._run("--date", _day(2))
        self.assertEqual(updated, ["docs/a.md"])
        self.assertEqual(doc.read_bytes(), self._text(_day(2), "Body, edited twice."))

    def test_date_line_only_difference_is_never_stamped(self) -> None:
        # AC-2 case 2: a hand edit of the date line, modified after its stamp.
        doc = self._commit("docs/a.md", self._text(_day(-10)))
        doc.write_bytes(self._text(_day(-5)))
        self._set_mtime(doc, 0)
        before = doc.read_bytes()
        paths, updated = self._run("--date", _day(0))
        self.assertEqual((paths, updated), ([], []))
        self.assertEqual(doc.read_bytes(), before)

    def test_date_line_only_difference_with_autocrlf_crlf_working_copy(self) -> None:
        # AC-2 case 2 on a Windows-style checkout: the blob is LF, the working
        # copy CRLF; only the date line differs once line endings are normalized.
        self._git("config", "core.autocrlf", "true")
        doc = self._commit("docs/crlf.md", self._text(_day(-10), newline="\r\n"))
        blob = subprocess.run(["git", "-C", str(self.root), "show", "HEAD:docs/crlf.md"],
                              check=True, capture_output=True).stdout
        self.assertNotIn(b"\r\n", blob)  # the control: a raw comparison would differ
        doc.write_bytes(self._text(_day(-5), newline="\r\n"))
        self._set_mtime(doc, 0)
        before = doc.read_bytes()
        paths, updated = self._run("--date", _day(0))
        self.assertEqual((paths, updated), ([], []))
        self.assertEqual(doc.read_bytes(), before)
        # A content change on the same checkout is still stamped, CRLF kept.
        doc.write_bytes(self._text(_day(-5), "Body, edited.", newline="\r\n"))
        self._set_mtime(doc, 0)
        paths, updated = self._run("--date", _day(0))
        self.assertEqual(updated, ["docs/crlf.md"])
        self.assertEqual(doc.read_bytes(), self._text(_day(0), "Body, edited.", newline="\r\n"))

    def test_future_stamp_with_a_content_change_is_stamped_with_the_run_date(self) -> None:
        # AC-2 case 3: the modification date is not later than the stamp.
        doc = self._commit("docs/a.md", self._text(_day(30)))
        doc.write_bytes(self._text(_day(30), "Body, edited."))
        self._set_mtime(doc, 0)
        paths, updated = self._run("--date", _day(0))
        self.assertEqual(updated, ["docs/a.md"])
        self.assertEqual(doc.read_bytes(), self._text(_day(0), "Body, edited."))

    def test_future_stamp_is_compared_with_the_run_date_not_the_local_today(self) -> None:
        # AC-2 case 3 with a past --date: a stamp of today is later than the
        # run's date, so the changed document is stamped with that date. Were
        # the clause compared with the local today, the stamp (today) would not
        # be in the future and the modification date (today) not later, so the
        # document would be left alone.
        doc = self._commit("docs/a.md", self._text(_day(0)))
        doc.write_bytes(self._text(_day(0), "Body, edited."))
        self._set_mtime(doc, 0)
        paths, updated = self._run("--date", _day(-2))
        self.assertEqual(updated, ["docs/a.md"])
        self.assertEqual(paths, ["docs/a.md"])
        self.assertEqual(doc.read_bytes(), self._text(_day(-2), "Body, edited."))

    def test_document_with_no_head_version_is_stamped(self) -> None:
        # AC-2 case 4: added to the index, so it is in the default target set.
        doc = self.root / "docs" / "new.md"
        doc.write_bytes(self._text(_day(-10)))
        self._git("add", "docs/new.md")
        self._set_mtime(doc, 0)
        paths, updated = self._run("--date", _day(0))
        self.assertEqual(updated, ["docs/new.md"])
        self.assertEqual(doc.read_bytes(), self._text(_day(0)))

    @contextmanager
    def _batch_spy(self, rewrite=None):
        """Record every ``cat-file`` call through the resolver, with its input
        bytes; ``rewrite`` may replace the real result or raise."""
        real = dg._run_tree_kill
        calls: list[bytes] = []

        def run(cmd, **kwargs):
            if "cat-file" not in cmd:
                return real(cmd, **kwargs)
            calls.append(kwargs.get("input"))
            if rewrite is None:
                return real(cmd, **kwargs)
            return rewrite(real(cmd, **kwargs))

        with patch.object(dg, "_run_tree_kill", side_effect=run):
            yield calls

    def _date_only_docs(self, *rels: str) -> list[Path]:
        # Each committed document has a distinct body and later differs from
        # its HEAD version only in its date line, so only a fallback stamps it.
        return [self._commit(rel, self._text(_day(-10), f"Body of {rel}.")) for rel in rels]

    def _reset_date_only(self, docs: list[Path]) -> None:
        for doc in docs:
            doc.write_bytes(self._text(_day(-5), f"Body of {doc.relative_to(self.root).as_posix()}."))
            self._set_mtime(doc, 0)

    def test_one_batched_head_read_for_all_candidates(self) -> None:
        # AC-1: three candidates, one cat-file process, all three names sent.
        a = self._commit("docs/a.md", self._text(_day(-10), "Alpha."))
        b = self._commit("docs/b.md", self._text(_day(-10), "Beta."))
        (c,) = self._date_only_docs("docs/c.md")
        a.write_bytes(self._text(_day(-10), "Alpha, edited."))
        b.write_bytes(self._text(_day(-10), "Beta, edited."))
        for doc in (a, b):
            self._set_mtime(doc, 0)
        self._reset_date_only([c])
        with self._batch_spy() as calls:
            paths, updated = self._run("--date", _day(0))
        self.assertEqual(updated, ["docs/a.md", "docs/b.md"])
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0], b"HEAD:./docs/a.md\nHEAD:./docs/b.md\nHEAD:./docs/c.md\n")

    def test_no_candidate_starts_no_batched_head_read(self) -> None:
        # AC-1: Git-changed, but modified before its stamp: not a candidate.
        doc = self._commit("docs/a.md", self._text(_day(-3)))
        doc.write_bytes(self._text(_day(-3), "Body, edited."))
        self._set_mtime(doc, -5)
        with self._batch_spy() as calls:
            paths, updated = self._run("--date", _day(0))
        self.assertEqual((paths, updated), ([], []))
        self.assertEqual(calls, [])

    def test_mixed_batch_stamps_exactly_the_differing_documents(self) -> None:
        # AC-2: one batch holding a document that differs, one that differs
        # only in its date line, one with no HEAD version sorted into the
        # middle, and date-only documents with non-ASCII and CRLF content.
        # A swapped or shifted blob would make a date-only document differ.
        differs = self._commit("docs/a-differs.md", self._text(_day(-10), "Alpha."))
        date_only = self._commit("docs/b-date-only.md", self._text(_day(-10), "Beta."))
        unicode_doc = self._commit("docs/d-unicode.md",
                                   self._text(_day(-10), "Grüße, naïve ✓."))
        crlf_doc = self._commit("docs/e-crlf.md", self._text(_day(-10), "Epsilon.", newline="\r\n"))
        new = self.root / "docs" / "c-new.md"
        new.write_bytes(self._text(_day(-10), "Gamma."))
        self._git("add", "docs/c-new.md")
        differs.write_bytes(self._text(_day(-10), "Alpha, edited."))
        date_only.write_bytes(self._text(_day(-5), "Beta."))
        unicode_doc.write_bytes(self._text(_day(-5), "Grüße, naïve ✓."))
        crlf_doc.write_bytes(self._text(_day(-5), "Epsilon.", newline="\r\n"))
        for doc in (differs, date_only, unicode_doc, crlf_doc, new):
            self._set_mtime(doc, 0)
        before = {doc: doc.read_bytes() for doc in (date_only, unicode_doc, crlf_doc)}
        with self._batch_spy() as calls:
            paths, updated = self._run("--date", _day(0))
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0].count(b"\n"), 5)
        self.assertEqual(updated, ["docs/a-differs.md", "docs/c-new.md"])
        for doc, data in before.items():
            self.assertEqual(doc.read_bytes(), data, doc)

    def test_head_read_failure_counts_every_unread_candidate_as_differing(self) -> None:
        # AC-3: both documents differ from HEAD only in their date line, so a
        # stamp here can come only from the failure fallback.
        docs = self._date_only_docs("docs/a.md", "docs/b.md")
        both = ["docs/a.md", "docs/b.md"]

        def raising(exc):
            def rewrite(result):
                raise exc
            return rewrite

        def with_stdout(transform, returncode=0):
            def rewrite(result):
                self.assertEqual(result.returncode, 0)
                return subprocess.CompletedProcess(result.args, returncode,
                                                   transform(result.stdout), result.stderr)
            return rewrite

        def first_header(data: bytes) -> bytes:
            return data[:data.index(b"\n")]

        def bad_size(data: bytes) -> bytes:
            header = first_header(data)
            return header.rsplit(b" ", 1)[0] + b" 12x" + data[len(header):]

        def first_entry(data: bytes) -> bytes:
            size = int(first_header(data).rsplit(b" ", 1)[1])
            return data[:len(first_header(data)) + 1 + size + 1]

        def oversized_last(data: bytes, size: bytes = b"999999") -> bytes:
            # The second (last) reply claims more bytes than follow it.
            head, rest = first_entry(data), data[len(first_entry(data)):]
            header = first_header(rest)
            return head + header.rsplit(b" ", 1)[0] + b" " + size + rest[len(header):]

        def extra_entry(data: bytes) -> bytes:
            return first_entry(data) + data

        def missing_for_another_name(data: bytes) -> bytes:
            # The first reply says the second document is missing; the second
            # reply is intact. The reply does not name the document sent first.
            return b"HEAD:./docs/b.md missing\n" + data[len(first_entry(data)):]

        cases = {
            "timeout": (raising(subprocess.TimeoutExpired(cmd="git", timeout=45)), both),
            "not_found": (raising(FileNotFoundError("git")), both),
            "exit_128_after_full_output": (with_stdout(lambda d: d, returncode=128), both),
            "cut_mid_second_blob": (with_stdout(lambda d: d[:-10]), ["docs/b.md"]),
            "non_integer_size": (with_stdout(bad_size), both),
            "size_beyond_data": (with_stdout(oversized_last), ["docs/b.md"]),
            "oversized_decimal_header": (with_stdout(lambda d: oversized_last(d, b"9" * 5000)), ["docs/b.md"]),
            "injected_extra_entry": (with_stdout(extra_entry), both),
            # Exit 0 with no header after the first complete reply, and exit 0
            # with no output at all: every unread document is stamped.
            "cut_after_first_entry": (with_stdout(first_entry), ["docs/b.md"]),
            "empty_output": (with_stdout(lambda d: b""), both),
            # A missing reply naming another document does not answer for the
            # one sent: framing stops there, so both are stamped.
            "missing_reply_names_another_document": (with_stdout(missing_for_another_name), both),
        }
        for label, (rewrite, expected) in cases.items():
            with self.subTest(case=label):
                self._reset_date_only(docs)
                with self._batch_spy(rewrite) as calls:
                    paths, updated = self._run("--date", _day(0))
                self.assertEqual(len(calls), 1)  # the injection fired
                self.assertEqual(updated, expected)
        # The control: the same documents with an intact batch stay unstamped.
        self._reset_date_only(docs)
        with self._batch_spy() as calls:
            paths, updated = self._run("--date", _day(0))
        self.assertEqual((len(calls), updated), (1, []))

    def test_names_that_cannot_be_sent_are_not_sent_and_count_as_differing(self) -> None:
        # AC-4: names with a line feed, a carriage return or a NUL never reach
        # Git; the date-only document after them is still read correctly.
        (date_only,) = self._date_only_docs("docs/z-date-only.md")
        self._reset_date_only([date_only])
        unsafe = [self.root / "docs" / name for name in ("bad\nname.md", "bad\rname.md", "bad\0name.md")]
        with self._batch_spy() as calls:
            heads = dg._read_head_versions(self.root, [*unsafe, date_only])
        self.assertEqual(calls, [b"HEAD:./docs/z-date-only.md\n"])
        for path in unsafe:
            self.assertNotIn(path, heads)
            self.assertTrue(dg._differs_from_head_outside_date_line(path, heads.get(path)))
        self.assertFalse(dg._differs_from_head_outside_date_line(date_only, heads.get(date_only)))

    def test_names_with_spaces_and_non_ascii_characters_are_read(self) -> None:
        # AC-4: such names are sent as their file-system bytes and the
        # committed bytes come back exactly.
        committed = {
            "docs/with space.md": self._text(_day(-10), "Spaced."),
            "docs/naïve ✓.md": self._text(_day(-10), "Accented."),
        }
        paths = [self._commit(rel, data) for rel, data in committed.items()]
        heads = dg._read_head_versions(self.root, paths)
        self.assertEqual({p.relative_to(self.root).as_posix(): heads[p] for p in paths}, committed)

    def test_explicit_modes_stamp_without_either_check(self) -> None:
        # AC-3: modification date not later than the stamp, only the date line
        # differs from HEAD, stamp earlier than the run's date.
        for rel, argv in (("docs/a.md", ("--paths", "docs/a.md")), ("docs/b.md", ("--all-docs",))):
            with self.subTest(argv=argv):
                doc = self._commit(rel, self._text(_day(-10)))
                doc.write_bytes(self._text(_day(-5)))
                self._set_mtime(doc, -6)
                paths, updated = self._run(*argv, "--date", _day(0))
                self.assertIn(rel, updated)
                self.assertEqual(doc.read_bytes(), self._text(_day(0)))

    def test_unreadable_modification_time_stamps_a_changed_document(self) -> None:
        # AC-4: modification date no later than the stamp, run date different
        # from the stamp and not before it, so only the fallback can stamp.
        doc = self._commit("docs/a.md", self._text(_day(-3)))
        doc.write_bytes(self._text(_day(-3), "Body, edited."))
        self._set_mtime(doc, -5)
        real = dg._modification_time

        def mtime(path):
            if Path(path) == doc:
                raise OSError("unreadable")
            return real(path)

        with patch.object(dg, "_modification_time", side_effect=mtime):
            paths, updated = self._run("--date", _day(0))
        self.assertEqual(updated, ["docs/a.md"])
        self.assertEqual(doc.read_bytes(), self._text(_day(0), "Body, edited."))

    def test_updated_lines_and_run_garden_list_exactly_the_written_documents(self) -> None:
        # AC-5: a stamped document, a Git-changed document the rule skips
        # (stamp earlier than the run's date, so the old code stamped it) and
        # the committed manifest and handoff, through the real run_garden parser.
        from server_tools_support import load_server

        stamped = self._commit("docs/stamped.md", self._text(_day(-10)))
        skipped = self._commit("docs/skipped.md", self._text(_day(-10)))
        stamped.write_bytes(self._text(_day(-10), "Body, edited."))
        self._set_mtime(stamped, 0)
        skipped.write_bytes(self._text(_day(-10), "Body, edited."))
        self._set_mtime(skipped, -10)
        skipped_before = skipped.read_bytes()
        srv = load_server()
        summary = srv.run_garden(self.root)
        self.assertTrue(summary["passed"], summary)
        self.assertEqual(summary["updated"], ["docs/stamped.md"])
        self.assertEqual(summary["files_updated"], 1)
        lines = [line for line in summary["output"].splitlines()
                 if line.startswith("docs-gardener: updated ")]
        self.assertEqual(lines, ["docs-gardener: updated docs/stamped.md"])
        self.assertIn("docs-gardener: stamped 1 doc(s)", summary["output"])
        self.assertEqual(stamped.read_bytes(), self._text(_day(0), "Body, edited."))
        self.assertEqual(skipped.read_bytes(), skipped_before)
