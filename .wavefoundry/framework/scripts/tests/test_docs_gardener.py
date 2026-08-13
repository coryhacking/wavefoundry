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
from contextlib import redirect_stdout
from pathlib import Path


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
            "last_gardened_at": "1999-01-01",
            "public_prompt_surface": [],
            "seed_framework_source": "test",
            "generated_artifacts": dg.default_manifest_payload("1999-01-01")[
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
        dg.ensure_manifest(self.root, "2026-08-12", bump_last_gardened=True)
        self.assertNotIn("docs/agents/journals/", self._read()["generated_artifacts"])

    def test_entry_added_to_the_default_arrives(self) -> None:
        """AC-2: the direction the field report did not observe. A repository
        installed before an entry was added never receives it, which leaves the
        framework's own record of what it generates wrong."""
        self._write(self._drifted_payload())
        dg.ensure_manifest(self.root, "2026-08-12", bump_last_gardened=True)
        current = dg.default_manifest_payload("2026-08-12")["generated_artifacts"]
        self.assertEqual(self._read()["generated_artifacts"], current)

    def test_keys_the_default_does_not_own_survive(self) -> None:
        """AC-3, and this is a regression guard rather than hygiene: clobbering
        `wave_root` would break docs-lint, which reads it through
        wave_lint_lib."""
        self._write(self._drifted_payload())
        dg.ensure_manifest(self.root, "2026-08-12", bump_last_gardened=True)
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
        dg.ensure_manifest(self.root, "2026-08-12", bump_last_gardened=True)
        data = self._read()
        self.assertIn("enabled_internal_features", data)
        self.assertEqual(data["enabled_internal_features"], ["wave_lifecycle"])

    def test_matching_manifest_is_not_rewritten(self) -> None:
        """AC-4: no churn for healthy repositories. Asserted on bytes AND on the
        returned wrote-flag, so a rewrite that happened to be byte-identical
        would still be caught."""
        self._write(self._drifted_payload())
        dg.ensure_manifest(self.root, "2026-08-12", bump_last_gardened=True)
        before = self.path.read_bytes()
        _path, wrote = dg.ensure_manifest(
            self.root, "2026-08-12", bump_last_gardened=True
        )
        self.assertFalse(wrote)
        self.assertEqual(self.path.read_bytes(), before)

    def test_partial_manifest_gains_the_default_without_losing_content(self) -> None:
        """AC-6: the gardener runs inside the docs gate, so a partial manifest
        must not crash it or discard project content."""
        self._write({"wave_root": "docs/waves"})
        dg.ensure_manifest(self.root, "2026-08-12", bump_last_gardened=True)
        data = self._read()
        self.assertEqual(
            data["generated_artifacts"],
            dg.default_manifest_payload("2026-08-12")["generated_artifacts"],
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

        `gardener_run` computes `bump_last_gardened = bool(updated_paths)`, so it
        is False exactly when no doc needed stamping — the steady state of a
        well-gardened repository. The first implementation returned early on
        that flag, so the manifest healed only on runs that happened to stamp
        something else. Asserting through `ensure_manifest` alone missed it
        entirely, because that call site passes the flag directly.
        """
        import argparse

        self._write({
            "schema_version": 1,
            "generated_artifacts": ["docs/agents/journals/"],
            "last_gardened_at": "2026-08-12",
            "seed_framework_source": ".wavefoundry/framework",
        })
        # Already current, so nothing needs a stamp and bump_last_gardened is False.
        (self.root / "docs" / "fresh.md").write_text(
            "# T\n\nOwner: Engineering\nStatus: draft\nLast verified: 2026-08-12\n",
            encoding="utf-8",
        )
        dg.gardener_run(
            self.root,
            argparse.Namespace(date="2026-08-12", paths=None, all_docs=True),
        )
        artifacts = self._read()["generated_artifacts"]
        self.assertNotIn("docs/agents/journals/", artifacts)
        self.assertIn("docs/reports/", artifacts)

    def test_non_bumping_run_does_not_stamp_the_date(self) -> None:
        """The gating that must SURVIVE the fix: reconciliation runs always, but
        a non-bumping caller still must not churn `last_gardened_at`."""
        self._write({
            "schema_version": 1,
            "generated_artifacts": dg.default_manifest_payload("x")["generated_artifacts"],
            "last_gardened_at": "2026-01-01",
            "seed_framework_source": ".wavefoundry/framework",
        })
        dg.ensure_manifest(self.root, "2026-08-12", bump_last_gardened=False)
        self.assertEqual(self._read()["last_gardened_at"], "2026-01-01")
