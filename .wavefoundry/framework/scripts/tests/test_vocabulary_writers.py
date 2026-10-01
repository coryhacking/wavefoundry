"""Writers follow the vocabulary profile (wave 1z8mm, change 1z8qi).

AC-1: under the default profile the shipped change template renders unchanged,
and the Stop-hook body differs from its pre-change form only by the runtime
profile import and the routed name references (pinned below).
AC-2: over a copied scripts tree with a second profile, a scratch repository
(the shared asset of change 1zim1, nested live root included) runs create
wave, admit change, prepare, readiness and delivery review
evidence, a member-status advance after the approvals, and close. Discovery,
``list_waves`` and docs-lint find the records, and no default vocabulary
marker (the census matcher) appears anywhere under the waves or plans root.
The default tree over default records is the control: the same lifecycle
closes there and the matcher does find its markers, so it is live.

The close is also the approval-survival oracle: close refuses a stale
review-policy receipt, so a member-status line the digest failed to exclude
under the second profile would block it (checked by mutation when written).
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import render_platform_surfaces  # noqa: E402
import test_vocabulary_census as _census  # noqa: E402  (module imports keep their tests out of this module)
import test_vocabulary_second_profile as _second  # noqa: E402
import vocabulary_profile  # noqa: E402
from record_layout_support import (  # noqa: E402
    DOCS_LINT_FIXTURE, SHIPPED_DEFAULTS, default_profile_only, shipped_default_profile,
)

FIXTURE_WAVE = "change-2026-03"
# The control tree is the shipped default profile, whatever profile this run loaded.
SHIPPED_RECORD = SHIPPED_DEFAULTS["vocabulary_profile"]["RECORD_FILENAME"]
SHIPPED_WAVES_ROOT = SHIPPED_DEFAULTS["record_paths"]["WAVES_ROOT"]

# Runs in a fresh interpreter with the scripts tree under test first on sys.path.
LIFECYCLE_DRIVER = r'''
import importlib.util, json, sys
from pathlib import Path
from unittest.mock import patch
scripts, root = Path(sys.argv[1]), Path(sys.argv[2])
sys.path.insert(0, str(scripts))
spec = importlib.util.spec_from_file_location("server", scripts / "server.py")
module = importlib.util.module_from_spec(spec)
sys.modules["server"] = module
spec.loader.exec_module(module)
srv = sys.modules["server_impl"]
import record_paths, vocabulary_profile
INTEGRITY = {"test_ran_without_unintended_skip": True, "public_path_reached": True,
             "boundary_values_realistic": True, "assertions_non_vacuous": True,
             "known_bad_detected": True, "known_bad_detection_method": "fixture control"}

def ok(step, response):
    if response.get("status") != "ok":
        raise SystemExit(f"{step}: {json.dumps(response, default=str)[:6000]}")
    return response.get("data", {})

def event(step, wave_id, kind, actor, context_id, **kwargs):
    return ok(step, srv.wf_review_event_response(
        root, wave_id, kind, actor, context_id, mode="create", fresh_context=True, independent=True,
        evidence={"observed": f"{actor} fixture", "artifact_or_test_id": "vocabulary-writers:" + context_id},
        integrity_checks=dict(INTEGRITY), **kwargs))

stubs = dict(
    run_validate=lambda *a, **k: {"passed": True, "errors": [], "warnings": [], "output": "ok\n"},
    run_garden=lambda *a, **k: {"passed": True, "files_updated": 0, "updated": [], "output": "ok\n"},
    _run_post_write_lint=lambda *a, **k: {"mode": "stubbed"},
)
status_label = vocabulary_profile.MEMBER_STATUS_LABEL
out = {}
with patch.multiple(srv, **stubs):
    made = ok("create wave", srv.wf_create_wave_response(root, "vocab-e2e", mode="create"))
    wave_id, record = made["wave_id"], root / made["path"]
    change_id = srv.new_change(root, "feat", "vocab-thing")["id"]
    plan = record_paths.load_record_roots(root).plans / f"{change_id}.md"
    text = plan.read_text(encoding="utf-8")
    for old, new in (("- [ ] AC-1: [Testable outcome]", "- [ ] AC-1: The thing works."),
                     ("- [ ] [Concrete implementation step]", "- [ ] Do the thing."),
                     ("| AC-1 | required / important / nice-to-have / not-this-scope | |", "| AC-1 | required | Core |")):
        text = text.replace(old, new)
    plan.write_text(text, encoding="utf-8")
    ok("admit", srv.wf_add_change_response(root, wave_id, change_id, mode="create"))
    change_doc = record.parent / f"{change_id}.md"
    ready = srv.wf_prepare_wave_response(root, wave_id, mode="ready")
    readiness_lanes = list(ready["data"]["review_policy"]["required_lanes"])
    event("readiness run", wave_id, "run", "wave-council", "ready-run", run_kind="readiness", cycle=0)
    for lane in readiness_lanes:
        event("readiness " + lane, wave_id, "approval", lane, "ready-" + lane,
              signoff_key=lane, approval_phase="readiness")
    event("readiness council", wave_id, "approval", "wave-council", "ready-council",
          signoff_key="wave-council-readiness", approval_phase="readiness")
    ok("prepare create", srv.wf_prepare_wave_response(root, wave_id, mode="create"))
    for path in (change_doc, record):
        path.write_text(path.read_text(encoding="utf-8").replace(
            f"{status_label}: `planned`", f"{status_label}: `implementing`"), encoding="utf-8")
    change_doc.write_text(change_doc.read_text(encoding="utf-8")
                          .replace("- [ ] AC-1:", "- [x] AC-1:")
                          .replace("- [ ] Do the thing.", "- [x] Do the thing."), encoding="utf-8")
    reviewed = srv.wf_review_wave_response(root, wave_id)
    delivery_lanes = [lane for lane in reviewed["data"]["required_lanes"] if lane != "operator"]
    event("delivery run", wave_id, "run", "wave-council", "delivery-run", run_kind="initial_delivery", cycle=0)
    for lane in delivery_lanes:
        event("delivery " + lane, wave_id, "approval", lane, "delivery-" + lane,
              signoff_key=lane, approval_phase="delivery")
    event("delivery council", wave_id, "approval", "wave-council", "delivery-council",
          signoff_key="wave-council-delivery", approval_phase="delivery")
    # The member status advances after the approvals; they must survive it.
    for path in (change_doc, record):
        path.write_text(path.read_text(encoding="utf-8").replace(
            f"{status_label}: `implementing`", f"{status_label}: `complete`"), encoding="utf-8")
    event("operator signoff", wave_id, "approval", "operator", "operator",
          signoff_key="operator-signoff", approval_phase="delivery")
    dry = srv.wf_close_wave_response(root, wave_id, mode="dry_run")
    closed = srv.wf_close_wave_response(root, wave_id, mode="create")
out["readiness_lanes"] = readiness_lanes
out["close_dry_codes"] = [d.get("code") for d in dry.get("diagnostics", [])]
out["close_status"] = closed.get("status")
out["close_codes"] = [d.get("code") for d in closed.get("diagnostics", [])]
out["record"] = record.relative_to(root).as_posix()
out["discovered"] = sorted(d.name for d in record_paths.discover_wave_dirs(root))
out["list_waves"] = sorted(
    ({"wave_id": w.get("wave_id"), "status": w.get("status"), "changes": w.get("changes")}
     for w in srv.list_waves(root)),
    key=lambda w: w["wave_id"],
)
print(json.dumps(out))
'''


def _lifecycle_repo(dest: Path, *, second: bool) -> Path:
    """The docs-lint fixture (lint-clean), in the matching vocabulary, with its
    own wave paused so a new one can open and a lifecycle-id policy set."""
    if second:
        _second._second_profile_records(dest)
        record = dest / _second.WAVE_DIR_REL / _second.SECOND_PROFILE["RECORD_FILENAME"]
    else:
        shutil.copytree(DOCS_LINT_FIXTURE, dest)
        record = dest / SHIPPED_WAVES_ROOT / FIXTURE_WAVE / SHIPPED_RECORD
    text, count = re.subn(r"(?m)^Status: active$", "Status: paused", record.read_text(encoding="utf-8"), count=1)
    assert count == 1
    record.write_text(text, encoding="utf-8")
    config_path = dest / "docs" / "workflow-config.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config["lifecycle_id_policy"] = {"epoch_utc": "2020-02-02T02:02:00Z", "hour_offset": 0}
    config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    return dest


def _run_lifecycle(scripts: Path, root: Path, layout: dict) -> dict:
    """``layout`` is the tree's ``record_paths`` constants: the census scans
    its waves and plans roots."""
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    result = subprocess.run(
        [sys.executable, "-B", "-c", LIFECYCLE_DRIVER, str(scripts), str(root)],
        cwd=str(root), env=env, text=True, capture_output=True, check=False, timeout=300,
    )
    if result.returncode != 0:
        raise AssertionError(f"lifecycle driver failed ({result.returncode}):\n"
                             f"{result.stdout[-4000:]}\n{result.stderr[-4000:]}")
    out = json.loads(result.stdout.strip().splitlines()[-1])
    lint = subprocess.run(
        [sys.executable, "-B", str(scripts / "docs_lint.py")],
        env={**env, "PROJECT_ROOT": str(root), "PYTHONPATH": str(scripts)},
        text=True, capture_output=True, check=False, timeout=300,
    )
    out["lint_rc"], out["lint_stderr"] = lint.returncode, lint.stderr
    hits = []
    for top in (layout["WAVES_ROOT"], layout["PLANS_ROOT"]):
        for path in sorted((root / top).rglob("*")):
            if not path.is_file():
                continue
            for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
                if _census.MARKER_RE.search(line):
                    hits.append(f"{path.relative_to(root).as_posix()}:{lineno}: {line.strip()}")
    out["marker_hits"] = hits
    return out


class SecondProfileLifecycleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        base = Path(cls._tmp.name)
        cls.second = _run_lifecycle(
            _second._copy_tree(base / "second-tree", _second.SECOND),
            _lifecycle_repo(base / "second-repo", second=True),
            {**SHIPPED_DEFAULTS["record_paths"], **_second.LAYOUT},
        )
        cls.control = _run_lifecycle(
            _second._copy_tree(base / "default-tree", shipped_default_profile()),
            _lifecycle_repo(base / "default-repo", second=False),
            SHIPPED_DEFAULTS["record_paths"],
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def _new_wave(self, out: dict) -> dict:
        waves = [w for w in out["list_waves"] if w["wave_id"].endswith(" vocab-e2e")]
        self.assertEqual(len(waves), 1, out["list_waves"])
        return waves[0]

    def test_lifecycle_closes_under_the_second_profile(self) -> None:
        self.assertEqual(self.second["close_dry_codes"], [])
        self.assertEqual((self.second["close_status"], self.second["close_codes"]), ("ok", []))
        self.assertTrue(self.second["record"].endswith("/set.md"), self.second["record"])
        wave = self._new_wave(self.second)
        self.assertEqual(wave["status"], "closed")
        self.assertEqual([c["status"] for c in wave["changes"]], ["complete"])
        self.assertEqual(len(self.second["discovered"]), 2)
        self.assertTrue(self.second["readiness_lanes"], "the receipt must name lanes, or the approvals prove little")

    def test_docs_lint_is_clean_under_the_second_profile(self) -> None:
        self.assertEqual(self.second["lint_rc"], 0, self.second["lint_stderr"])

    def test_no_default_marker_is_written(self) -> None:
        self.assertEqual(self.second["marker_hits"], [])

    def test_control_closes_and_the_matcher_is_live(self) -> None:
        self.assertEqual((self.control["close_status"], self.control["close_codes"]), ("ok", []))
        self.assertEqual(self._new_wave(self.control)["status"], "closed")
        self.assertEqual(self.control["lint_rc"], 0, self.control["lint_stderr"])
        self.assertTrue(any(f"vocab-e2e/{SHIPPED_RECORD}" in hit for hit in self.control["marker_hits"]))


class DefaultProfileWriterTests(unittest.TestCase):
    TEMPLATE = SCRIPTS_DIR.parent / "install" / "plan-template.md"

    @default_profile_only("pins the shipped template as the identity of localize_template under the shipped labels")
    def test_shipped_template_is_unchanged_under_the_default_profile(self) -> None:
        text = self.TEMPLATE.read_text(encoding="utf-8")
        self.assertEqual(vocabulary_profile.localize_template(text), text)

    def test_shipped_template_is_localized_under_a_second_profile(self) -> None:
        text = self.TEMPLATE.read_text(encoding="utf-8")
        with patch.multiple(vocabulary_profile, MEMBER_ID_LABEL="Member ID",
                            MEMBER_STATUS_LABEL="Member Status", BACKREF_LABEL="Set", RECORD_FILENAME="set.md"):
            localized = vocabulary_profile.localize_template(text)
        self.assertEqual([line for line in localized.splitlines() if _census.MARKER_RE.search(line)], [])
        for line in ("Member ID: `<id-prefix>-<kind> <slug>`", "Member Status: `planned`", "Set: TBD",
                     "- `docs/waves/1abc some slug/set.md`"):
            self.assertIn(line, localized.splitlines())

    def test_localize_template_is_one_pass(self) -> None:
        # A profile label equal to another shipped label is not rewritten twice.
        with patch.multiple(vocabulary_profile, MEMBER_ID_LABEL="Wave", BACKREF_LABEL="Change ID"):
            self.assertEqual(vocabulary_profile.localize_template("Change ID: `x`\nWave: y\n"),
                             "Wave: `x`\nChange ID: y\n")

    def test_stop_hook_reads_the_profile_at_runtime(self) -> None:
        # Golden for the hook-body diff: these lines are the whole routed delta
        # against the pre-change body, which named the record file and id key
        # literally at three sites.
        body = render_platform_surfaces.claude_stop_source()
        routed = [line.strip() for line in body.splitlines()
                  if re.search(r"_wf_vocab\b|_wf_record_file\b|_wf_id_prefix\b", line)]
        self.assertEqual(routed, [
            "import vocabulary_profile as _wf_vocab",
            "_wf_vocab = None",
            '_wf_record_file = getattr(_wf_vocab, "RECORD_FILENAME", None)',
            '_wf_id_prefix = getattr(_wf_vocab, "ID_KEY", None)',
            "if _wf_record_file is None:",
            "wave_md = wave_dir / _wf_record_file",
            'elif _wf_id_prefix and s.startswith(_wf_id_prefix + ":"):',
            "if md.name == _wf_record_file:",
        ])
        self.assertEqual([line for line in body.splitlines() if _census.MARKER_RE.search(line)], [])


if __name__ == "__main__":
    unittest.main()
