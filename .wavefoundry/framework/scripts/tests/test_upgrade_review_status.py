"""Exercise the incoming review renderer across a real upgrade and its resume."""
from __future__ import annotations

import contextlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import review_evidence
import review_policy
import review_policy_reconcile
import upgrade_protocol
import vocabulary_profile
from record_layout_support import RecordTreeBuilder, copy_scripts_tree, localized_docs_lint_fixture
import test_review_evidence as evidence_fixtures


# This is the old public table format. The installed module on disk is replaced
# during extraction, but the process driving the upgrade keeps this function.
OLD_TABLE = '''
def review_status_human_table(records, required_signoff_keys, *, wave_closed=False):
    lines = ["| Signoff | State | Why | Next action |", "| --- | --- | --- | --- |"]
    for row in review_status_rows(records, required_signoff_keys, wave_closed=wave_closed):
        lines.append("| " + " | ".join(_markdown_cell(row[k]) for k in
                     ("signoff_key", "state", "why", "next_action")) + " |")
    return "\\n".join(lines)
'''

# Keep extraction, policy reconciliation, incoming hook dispatch and the two
# real docs-gate children. Omit unrelated optional hooks, host rendering,
# pruning and index publication. A fresh interpreter drives each attempt.
DRIVER = '''
import sys
from pathlib import Path
root, pack, action = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
scripts = root / ".wavefoundry/framework/scripts"
sys.path.insert(0, str(scripts))
import review_evidence as evidence
import upgrade_wavefoundry as runner
runner._preferred_python = lambda: sys.executable
runner.phase_index_update = lambda root: True
if action == "resume":
    runner._load_extension_module = lambda pack: None  # omit post-gate index hooks
    raise SystemExit(runner.main(["--root", str(root), "--resume-after-gate"]))
assert evidence.review_status_human_table([], []).startswith("| Signoff | State |")
runner.phase_preflight = lambda *args, **kwargs: ("1.46.0", "1.47.0", pack)
runner.phase_surface_rendering = lambda root: None
runner.phase_pruning = lambda root: 0
dispatch = runner._run_hook
def hook(name, ctx, extension):
    if name == "pre_docs_gate":
        assert extension is not None
        dispatch(name, ctx, extension)
    elif name == "post_docs_gate":
        assert evidence.review_status_human_table([], []).startswith("| Signoff | State |")
        print("OLD PARENT REACHED POST-DOCS GATE", flush=True)
        raise SystemExit(77)
runner._run_hook = hook
raise SystemExit(runner.main(["--root", str(root), "--pack", str(pack), "--yes"]))
'''


class InstallingReviewStatusTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.temp = Path(tmp.name).resolve()
        self.root = self.temp / "target repo"
        localized_docs_lint_fixture(self.root)
        self.framework = self.root / ".wavefoundry/framework"
        self.scripts = copy_scripts_tree(self.framework, with_support=False)
        (self.framework / "VERSION").write_text("1.46.0\n", encoding="utf-8")
        (self.framework / "MANIFEST").write_text("VERSION\nMANIFEST\n", encoding="utf-8")
        config = self.root / "docs/workflow-config.json"
        data = json.loads(config.read_bytes())
        data["wave_review"] = review_policy.migrate_wave_review_policy(data["wave_review"])
        config.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        review_policy_reconcile.apply_reconciliation(self.root, review_policy_reconcile.plan_reconciliation(self.root))
        self.pack = self.temp / "wavefoundry-1.47.0.fixture.zip"
        with zipfile.ZipFile(self.pack, "w", zipfile.ZIP_DEFLATED) as archive:
            for file in self.scripts.rglob("*.py"):
                archive.write(file, file.relative_to(self.root).as_posix())
            archive.writestr(".wavefoundry/framework/VERSION", "1.47.0\n")
            archive.writestr(upgrade_protocol.PROTOCOL_METADATA_ARCNAME, json.dumps(
                upgrade_protocol.build_protocol_metadata(release_version="1.47.0", build_id="fixture", artifact_type="feature")))
        with (self.scripts / "review_evidence.py").open("a", encoding="utf-8") as stream:
            stream.write(OLD_TABLE)
        shutil.copyfile(SCRIPTS / "tests/fixtures/upgrade_old_runner/upgrade_runner_v1_31_0.py.txt",
                        self.scripts / "upgrade_wavefoundry.py")
        self.driver = self.temp / "driver.py"
        self.driver.write_text(DRIVER, encoding="utf-8")
        builder = RecordTreeBuilder(self.root)
        # Generate historical bytes with the old table and current typed receipts.
        namespace = dict(vars(review_evidence))
        exec(OLD_TABLE, namespace)
        self.waves = {}
        receipt = evidence_fixtures.LapsedApprovalReasonTests._receipt("a" * 64, ["qa-reviewer"])
        del receipt["receipt_id"]
        receipt, _ = review_policy.build_policy_receipt(
            {**receipt, "evaluator_version": review_policy.REVIEW_POLICY_EVALUATOR_VERSION}, None)
        for key, status, members, rows in (
            ("0a001 ready", "ready", [("0a004-enh checked", "ready")],
             [receipt, evidence_fixtures.LapsedApprovalReasonTests._readiness_approval(receipt["receipt_id"])]),
            ("0a002 planned", "planned", [], []),
            ("0a003 closed", "closed", [("0a005-bug done", "complete")], []),
            ("0a006 completed", "completed", [("0a007-bug prior", "complete")], []),
        ):
            folder = builder.container(key, key, status=status, members=members)
            path = folder / vocabulary_profile.RECORD_FILENAME
            ledger = review_evidence.canonical_review_events_bytes(rows)
            path.with_name("events.jsonl").write_bytes(ledger)
            text = path.read_text(encoding="utf-8")
            text = text.replace("\n## Objective", "\nreview-policy-reprepare-required: false\n\n## Objective", 1)
            text = review_evidence.render_review_evidence_projection(text, rows)
            keys = review_evidence.required_review_status_keys(self.root, text, rows)
            with patch.object(review_evidence, "review_status_human_table", namespace["review_status_human_table"]):
                text = review_evidence.render_review_status_projection(text, rows, keys)
            if status == "ready":
                start = review_evidence.REVIEW_STATUS_MARKER_BEGIN
                end = review_evidence.REVIEW_STATUS_MARKER_END
                text = text.replace(start, "Operator's preface.\n\n\n" + start)
                text = text.replace(end, end + "\n\n```markdown\n"
                                    "- wave-council-readiness: approved — historical syntax example\n"
                                    "- site-reviewer: approved — adjacent example\n```\n"
                                    "- wave-council-readiness: approved — operator's original note\n")
            raw = text.replace("\n", "\r\n").encode() if status == "ready" else text.encode()
            path.write_bytes(raw)
            self.waves[status] = (path, raw, ledger)

    def run_driver(self, action):
        env = dict(os.environ, PROJECT_ROOT=str(self.root), WAVEFOUNDRY_SKIP_PYTHON_HEAL="1",
                   PYTHONDONTWRITEBYTECODE="1")
        env.update({name: str(self.temp) for name in ("TMPDIR", "TMP", "TEMP")})
        env.pop("PYTHONPYCACHEPREFIX", None)
        return subprocess.run([sys.executable, "-B", str(self.driver), str(self.root), str(self.pack), action],
                              cwd=self.root, env=env, capture_output=True, text=True, timeout=90)

    def assert_updated(self):
        for status, (path, before, ledger) in self.waves.items():
            with self.subTest(status=status):
                after = path.read_bytes()
                self.assertEqual(path.with_name("events.jsonl").read_bytes(), ledger)
                if status in {"closed", "completed"}:
                    self.assertEqual(after, before)
                    import lifecycle_gates
                    diagnostics = lifecycle_gates._review_evidence_diagnostics(
                        path.read_text(encoding="utf-8"), root=self.root, wave_md=path)
                    self.assertEqual(diagnostics, [])
                    continue
                self.assertIn(b"| Signoff | Phase | State |", after)
                self.assertIn(b"review-policy-reprepare-required: false", after)
                if status == "ready":
                    self.assertEqual(after.count(b"\n"), after.count(b"\r\n"))
                else:
                    self.assertNotIn(b"\r", after)
                begin = review_evidence.REVIEW_STATUS_MARKER_BEGIN.encode()
                end = review_evidence.REVIEW_STATUS_MARKER_END.encode()
                self.assertEqual(after.split(begin)[0], before.split(begin)[0])
                self.assertEqual(after.split(end)[1], before.split(end)[1])

    def test_install_and_resume_render_from_extracted_code(self):
        applied = self.run_driver("apply")
        self.assertIn("OLD PARENT REACHED POST-DOCS GATE", applied.stdout, applied.stdout + applied.stderr)
        self.assert_updated()

        import upgrade_lib
        checkpoint = upgrade_lib.read_upgrade_lock(self.root)
        self.assertEqual(checkpoint["review_policy_migration"]["waves_marked_for_reprepare"], [])
        # Recreate a retained docs-gate failure after extraction. The second
        # process uses the current runner and cannot replay the incoming hook.
        for path, before, _ledger in self.waves.values():
            path.write_bytes(before)
        upgrade_lib.update_upgrade_lock(self.root, failed_phase="docs_gate")
        resumed = self.run_driver("resume")
        self.assertEqual(resumed.returncode, 0, resumed.stdout + resumed.stderr)
        self.assertIn("Docs gate: PASSED", resumed.stdout)
        self.assert_updated()

    def test_unreadable_ledger_preserves_one_record_and_refreshes_others(self):
        import review_policy_upgrade

        path, before, _ = self.waves["ready"]
        path.with_name("events.jsonl").unlink()
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            review_policy_upgrade.refresh_review_status_blocks(self.root)
        messages = [line for line in out.getvalue().splitlines() if path.parent.name in line]
        self.assertEqual(len(messages), 1)
        self.assertIn("ledger is missing", messages[0])
        self.assertEqual(path.read_bytes(), before)
        planned, _, _ = self.waves["planned"]
        self.assertIn(b"| Signoff | Phase |", planned.read_bytes())

    def test_refresh_retains_mixed_newlines_in_operator_text(self):
        import review_policy_upgrade

        path, before, _ = self.waves["ready"]
        before = before.replace(b"Operator's preface.\r\n", b"Operator's preface.\n")
        path.write_bytes(before)
        review_policy_upgrade.refresh_review_status_blocks(self.root)
        begin = review_evidence.REVIEW_STATUS_MARKER_BEGIN.encode()
        end = review_evidence.REVIEW_STATUS_MARKER_END.encode()
        after = path.read_bytes()
        self.assertNotEqual(before, after)
        self.assertEqual(before.partition(begin)[0], after.partition(begin)[0])
        self.assertEqual(before.partition(end)[2], after.partition(end)[2])

    def test_policy_planner_skips_historical_ledgers(self):
        import review_policy_upgrade

        for status in ("closed", "completed"):
            path, _, _ = self.waves[status]
            path.with_name("events.jsonl").unlink()
        plan = review_policy_upgrade.plan_review_policy_upgrade(self.root)
        self.assertEqual(plan.waves, ())
        path, _, _ = self.waves["ready"]
        path.with_name("events.jsonl").unlink()
        with self.assertRaisesRegex(ValueError, "ledger is missing"):
            review_policy_upgrade.plan_review_policy_upgrade(self.root)
