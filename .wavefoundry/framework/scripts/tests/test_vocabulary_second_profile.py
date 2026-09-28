"""Readers follow a second vocabulary profile (wave 1z8mm, change 1z826, AC-2).

The scripts tree is copied and its ``vocabulary_profile.py`` edited the way a
fork edits it at merge time; the docs-lint fixture is rewritten into the second
profile's names (``set.md``, ``set-id``, ``## Members``, ``Member ID``,
``Member Status`` and so on). A fresh interpreter over the copied tree then
runs discovery, docs-lint, ``list_waves``, ``wf_get_change``, dashboard
parsing, memory backfill and the review-policy digest against those records.

Every assertion is paired with a control: the unedited tree over the same
rewritten records finds nothing (or reads a different value), so a reader that
still hard-codes a default marker fails here rather than passing vacuously.
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

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = SCRIPTS_ROOT / "tests" / "fixtures" / "docs_lint" / "base"
WAVE_FOLDER = "change-2026-03"

SECOND_PROFILE = {
    "CONTAINER_NAME": "Set", "CONTAINER_NAME_PLURAL": "Sets",
    "ITEM_NAME": "Member", "ITEM_NAME_PLURAL": "Members",
    "RECORD_FILENAME": "set.md", "ID_KEY": "set-id", "RECORD_TITLE": "# Set Record",
    "SUMMARY_HEADING": "## Set Summary", "MEMBER_HEADING": "## Members",
    "MEMBER_ID_LABEL": "Member ID", "MEMBER_STATUS_LABEL": "Member Status",
    "BACKREF_LABEL": "Set",
}

RECORD_SUBSTITUTIONS = (
    ("wave-id:", "set-id:"), ("# Wave Record", "# Set Record"),
    ("## Wave Summary", "## Set Summary"), ("## Changes", "## Members"),
    ("Change ID", "Member ID"), ("Change Status", "Member Status"),
)

# Runs in a fresh interpreter with the scripts tree under test first on sys.path.
DRIVER = r'''
import importlib.util, json, os, subprocess, sys
from pathlib import Path
scripts, root = Path(sys.argv[1]), Path(sys.argv[2])
sys.path.insert(0, str(scripts))
import dashboard_lib, gardener_metadata, memory_backfill, record_paths
out = {}
out["discovered"] = [d.name for d in record_paths.discover_wave_dirs(root)]
env = dict(os.environ, PROJECT_ROOT=str(root), PYTHONPATH=str(scripts))
lint = subprocess.run([sys.executable, "-B", str(scripts / "docs_lint.py")],
                      env=env, text=True, capture_output=True, check=False)
out["lint_rc"], out["lint_stderr"] = lint.returncode, lint.stderr
spec = importlib.util.spec_from_file_location("server", scripts / "server.py")
module = importlib.util.module_from_spec(spec)
sys.modules["server"] = module
spec.loader.exec_module(module)
impl = sys.modules["server_impl"]
out["list_waves"] = [
    {"wave_id": w.get("wave_id"), "status": w.get("status"), "changes": w.get("changes")}
    for w in impl.list_waves(root)
]
got = impl.wf_get_change_response(root, "00058")
out["get_change"] = {"status": got["status"], "change_id": (got["data"].get("change") or {}).get("change_id")}
# Lookup by wave reads the member list in the record, so only the profile finds it.
by_wave = impl.wf_get_change_response(root, "", wave_id="00057")
out["get_change_by_wave"] = sorted(c["id"] for c in by_wave["data"].get("changes", []))
wave_dir = root / "docs" / "waves" / sys.argv[3]
change = sorted(wave_dir.glob("00058-*.md"))[0]
record = dashboard_lib.parse_change_doc(root, change)
out["dashboard"] = {"change_id": record.change_id, "status": record.status, "wave_id": record.wave_id}
out["backfill"] = list(memory_backfill._wave_status(root, wave_dir))
body = change.read_bytes()
advanced = body.replace(sys.argv[4].encode() + b": `planned`", sys.argv[4].encode() + b": `implementing`")
out["digest_changed_by_status_advance"] = (
    gardener_metadata.canonical_review_policy_body(body)
    != gardener_metadata.canonical_review_policy_body(advanced)
)
print(json.dumps(out))
'''


def _copy_tree(dest: Path, profile: dict[str, str] | None) -> Path:
    """Copy the framework's ``scripts`` and ``install`` under ``dest``, apply
    ``profile`` to the copied ``vocabulary_profile.py``, and return the copied
    scripts directory."""
    scripts = dest / "scripts"
    shutil.copytree(
        SCRIPTS_ROOT, scripts,
        ignore=shutil.ignore_patterns("tests", "benchmarks", "__pycache__", ".pytest_cache", "*.pyc"),
    )
    shutil.copytree(SCRIPTS_ROOT.parent / "install", dest / "install")
    if profile:
        path = scripts / "vocabulary_profile.py"
        text = path.read_text(encoding="utf-8")
        for name, value in profile.items():
            text, count = re.subn(rf'^{name} = "[^"]*"', f'{name} = "{value}"', text, flags=re.MULTILINE)
            if count != 1:
                raise AssertionError(f"{name} not found once in the copied profile")
        path.write_text(text, encoding="utf-8")
    return scripts


def _second_profile_records(dest: Path) -> Path:
    shutil.copytree(FIXTURE_ROOT, dest)
    for path in (dest / "docs" / "waves").rglob("*.md"):
        if path.name == "README.md":
            continue
        text = path.read_text(encoding="utf-8")
        for old, new in RECORD_SUBSTITUTIONS:
            text = text.replace(old, new)
        text = re.sub(r"(?m)^Wave:", "Set:", text)
        if path.name.startswith("00058-"):
            # A status line the dashboard and the digest must both read.
            text = text.replace("Status: active\n", "Status: active\nMember Status: `planned`\n", 1)
        path.write_text(text, encoding="utf-8")
        if path.name == "wave.md":
            path.rename(path.with_name(SECOND_PROFILE["RECORD_FILENAME"]))
    return dest


def _run(tree: Path, root: Path) -> dict:
    result = subprocess.run(
        [sys.executable, "-B", "-c", DRIVER, str(tree), str(root), WAVE_FOLDER,
         SECOND_PROFILE["MEMBER_STATUS_LABEL"]],
        cwd=str(root), env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        text=True, capture_output=True, check=False, timeout=300,
    )
    if result.returncode != 0:
        raise AssertionError(f"driver failed ({result.returncode}):\n{result.stderr[-4000:]}")
    return json.loads(result.stdout.strip().splitlines()[-1])


class SecondProfileReaderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        base = Path(cls._tmp.name)
        records = _second_profile_records(base / "records")
        cls.second = _run(_copy_tree(base / "second", SECOND_PROFILE), records)
        cls.control = _run(_copy_tree(base / "default", None), records)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def test_discovery(self) -> None:
        self.assertEqual(self.second["discovered"], [WAVE_FOLDER])
        self.assertEqual(self.control["discovered"], [])

    def test_docs_lint(self) -> None:
        self.assertEqual(self.second["lint_rc"], 0, self.second["lint_stderr"])
        self.assertNotIn("record_file_not_found", self.second["lint_stderr"])
        self.assertNotEqual(self.control["lint_rc"], 0)
        self.assertIn("record_file_not_found", self.control["lint_stderr"])

    def test_list_waves(self) -> None:
        self.assertEqual(self.second["list_waves"], [{
            "wave_id": "00057 routine-behavior-contract",
            "status": "active",
            "changes": [
                {"id": "00058-bug fixture-core", "status": "complete"},
                {"id": "00059-enh fixture-follow-up", "status": "ready"},
            ],
        }])
        self.assertEqual(self.control["list_waves"], [])

    def test_get_change(self) -> None:
        self.assertEqual(self.second["get_change"], {"status": "ok", "change_id": "00058-bug fixture-core"})
        # A lookup by id finds the file by name under either tree; the lookup by
        # wave reads the record's member list and is the profile-dependent one.
        self.assertEqual(self.second["get_change_by_wave"],
                         ["00058-bug fixture-core", "00059-enh fixture-follow-up"])
        self.assertEqual(self.control["get_change_by_wave"], [])

    def test_dashboard_parse(self) -> None:
        self.assertEqual(self.second["dashboard"], {
            "change_id": "00058-bug fixture-core", "status": "planned", "wave_id": WAVE_FOLDER,
        })
        self.assertNotEqual(self.control["dashboard"]["status"], "planned")

    def test_memory_backfill(self) -> None:
        self.assertEqual(self.second["backfill"], ["active", ""])
        self.assertEqual(self.control["backfill"][0], "unsupported")

    def test_status_advance_leaves_digest_unchanged(self) -> None:
        self.assertFalse(self.second["digest_changed_by_status_advance"])
        self.assertTrue(self.control["digest_changed_by_status_advance"])


if __name__ == "__main__":
    unittest.main()
