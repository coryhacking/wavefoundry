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


# Change 1z8os (AC-2): a vocabulary whose labels are prefixes of one another in
# bare form (`Wave`, `Wave ID`, `Wave Status`) but distinct in colon form.
# BACKREF_LABEL equals the default, so the control discriminates on the
# `Wave ID` and `Wave Status` lines.
WAVE_SET_PROFILE = dict(
    SECOND_PROFILE, ITEM_NAME="Wave", ITEM_NAME_PLURAL="Waves", MEMBER_HEADING="## Waves",
    MEMBER_ID_LABEL="Wave ID", MEMBER_STATUS_LABEL="Wave Status", BACKREF_LABEL="Wave",
)
# The suffix pair: `ID:` is a substring of `Wave ID:`, so only a line-anchored
# reader tells them apart (the four ID_KEY record tests in docs-lint).
SUFFIX_PAIR_PROFILE = dict(WAVE_SET_PROFILE, ID_KEY="ID")
# A strict prefix of the folder name: docs-lint accepts it, and it differs from
# the folder fallback the dashboard would otherwise report.
BACKREF_VALUE = "change-2026"
PLAN_ID = "00060-enh fixture-admit"

PLAN_DOC = f"""# Fixture Admit

Owner: Engineering
Status: active
Last verified: 2026-03-21
Wave: TBD

## Wave ID

Wave ID: `{PLAN_ID}`

## Rationale

Fixture plan admitted and removed by the prefix-label driver.

## Acceptance Criteria

- [ ] AC-1: Fixture criterion pending.

## AC Priority

| AC | Priority |
|----|----------|
| AC-1 | required |
"""

WAVE_SET_DRIVER = r"""
import importlib.util, json, os, subprocess, sys
from pathlib import Path
scripts, root, folder = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
sys.path.insert(0, str(scripts))
import dashboard_lib, record_paths
out = {}
env = dict(os.environ, PROJECT_ROOT=str(root), PYTHONPATH=str(scripts))
def lint():
    run = subprocess.run([sys.executable, "-B", str(scripts / "docs_lint.py")],
                         env=env, text=True, capture_output=True, check=False)
    return run.returncode, run.stderr + run.stdout
out["discovered"] = [d.name for d in record_paths.discover_wave_dirs(root)]
out["lint_rc"], out["lint_output"] = lint()
spec = importlib.util.spec_from_file_location("server", scripts / "server.py")
module = importlib.util.module_from_spec(spec)
sys.modules["server"] = module
spec.loader.exec_module(module)
impl = sys.modules["server_impl"]
wave_dir = root / "docs" / "waves" / folder
record = wave_dir / impl._vocab.RECORD_FILENAME
out["list_waves"] = [
    {"wave_id": w.get("wave_id"), "status": w.get("status"), "changes": w.get("changes")}
    for w in impl.list_waves(root)
]
change = sorted(wave_dir.glob("00058-*.md"))[0]
parsed = dashboard_lib.parse_change_doc(root, change)
out["dashboard"] = {"change_id": parsed.change_id, "status": parsed.status, "wave_id": parsed.wave_id}
def member_ids():
    return impl._extract_change_ids_from_wave_text(record.read_text(encoding="utf-8")) if record.exists() else []
out["ids_before"] = member_ids()
added = impl.wf_add_change_response(root, "00057", sys.argv[4], mode="create")
out["add_status"] = added["status"]
admitted = wave_dir / (sys.argv[4] + ".md")
out["admitted_backref"] = [
    line for line in (admitted.read_text(encoding="utf-8").splitlines() if admitted.exists() else [])
    if line.startswith(sys.argv[5] + ":")
]
out["ids_after_add"] = member_ids()
out["lint_after_add_rc"], out["lint_after_add_output"] = lint()
removed = impl.wf_remove_change_response(root, "00057", sys.argv[4], mode="create")
out["remove_status"] = removed["status"]
out["remove_updated"] = removed["data"].get("updated")
out["ids_after_remove"] = member_ids()
print(json.dumps(out))
"""


def _wave_set_records(dest: Path, profile: dict[str, str]) -> Path:
    """The docs-lint fixture rewritten into ``profile``'s names, with a
    ``Wave:`` back-reference on one change doc and a ``Wave: TBD`` plan."""
    shutil.copytree(FIXTURE_ROOT, dest)
    substitutions = (
        ("wave-id:", profile["ID_KEY"] + ":"), ("# Wave Record", profile["RECORD_TITLE"]),
        ("## Wave Summary", profile["SUMMARY_HEADING"]), ("## Changes", profile["MEMBER_HEADING"]),
        ("Change ID", profile["MEMBER_ID_LABEL"]), ("Change Status", profile["MEMBER_STATUS_LABEL"]),
    )
    for path in (dest / "docs" / "waves").rglob("*.md"):
        if path.name == "README.md":
            continue
        text = path.read_text(encoding="utf-8")
        for old, new in substitutions:
            text = text.replace(old, new)
        if path.name.startswith("00058-"):
            text = text.replace("Status: active\n", f"Status: active\n{profile['MEMBER_STATUS_LABEL']}: `planned`\n", 1)
            # After the `Wave ID:` line, so a reader of bare `Wave` finds the wrong line first.
            id_line = f"{profile['MEMBER_ID_LABEL']}: `00058-bug fixture-core`\n"
            text = text.replace(id_line, id_line + f"{profile['BACKREF_LABEL']}: `{BACKREF_VALUE}`\n", 1)
        path.write_text(text, encoding="utf-8")
        if path.name == "wave.md":
            path.rename(path.with_name(profile["RECORD_FILENAME"]))
    plans = dest / "docs" / "plans"
    plans.mkdir(parents=True, exist_ok=True)
    (plans / f"{PLAN_ID}.md").write_text(PLAN_DOC, encoding="utf-8")
    return dest


def _run_wave_set(tree: Path, root: Path, backref: str) -> dict:
    result = subprocess.run(
        [sys.executable, "-B", "-c", WAVE_SET_DRIVER, str(tree), str(root), WAVE_FOLDER, PLAN_ID, backref],
        cwd=str(root), env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        text=True, capture_output=True, check=False, timeout=300,
    )
    if result.returncode != 0:
        raise AssertionError(f"driver failed ({result.returncode}):\n{result.stderr[-4000:]}")
    return json.loads(result.stdout.strip().splitlines()[-1])


class PrefixLabelProfileTests(unittest.TestCase):
    """Change 1z8os (AC-2): `Wave`, `Wave ID` and `Wave Status` together."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        base = Path(cls._tmp.name)
        # Each run mutates its records (admission moves a document), so each gets its own copy.
        cls.second = _run_wave_set(_copy_tree(base / "second", WAVE_SET_PROFILE),
                                   _wave_set_records(base / "records-second", WAVE_SET_PROFILE), "Wave")
        cls.control = _run_wave_set(_copy_tree(base / "default", None),
                                    _wave_set_records(base / "records-control", WAVE_SET_PROFILE), "Wave")
        cls.suffix = _run_wave_set(_copy_tree(base / "suffix", SUFFIX_PAIR_PROFILE),
                                   _wave_set_records(base / "records-suffix", SUFFIX_PAIR_PROFILE), "Wave")

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def test_docs_lint_before_and_after_admission(self) -> None:
        for run in (self.second, self.suffix):
            self.assertEqual(run["discovered"], [WAVE_FOLDER])
            self.assertEqual(run["lint_rc"], 0, run["lint_output"])
            self.assertEqual(run["lint_after_add_rc"], 0, run["lint_after_add_output"])
        self.assertNotEqual(self.control["lint_rc"], 0)

    def test_member_ids_and_statuses(self) -> None:
        expected = [{
            "wave_id": "00057 routine-behavior-contract",
            "status": "active",
            "changes": [
                {"id": "00058-bug fixture-core", "status": "complete"},
                {"id": "00059-enh fixture-follow-up", "status": "ready"},
            ],
        }]
        self.assertEqual(self.second["list_waves"], expected)
        self.assertEqual(self.suffix["list_waves"], expected)
        self.assertEqual(self.control["list_waves"], [])

    def test_dashboard_reads_the_back_reference(self) -> None:
        expected = {"change_id": "00058-bug fixture-core", "status": "planned", "wave_id": BACKREF_VALUE}
        self.assertEqual(self.second["dashboard"], expected)
        self.assertEqual(self.suffix["dashboard"], expected)
        self.assertNotEqual(BACKREF_VALUE, WAVE_FOLDER)
        # The default tree reads `Wave:` too (the same label), but not the
        # `Wave Status` line (its change id falls back to the file stem).
        self.assertNotEqual(self.control["dashboard"]["status"], "planned")

    def test_admission_repairs_the_back_reference_and_removal_removes_the_block(self) -> None:
        existing = ["00058-bug fixture-core", "00059-enh fixture-follow-up"]
        for run in (self.second, self.suffix):
            self.assertEqual(run["ids_before"], existing)
            self.assertEqual(run["add_status"], "ok")
            self.assertEqual(run["admitted_backref"], [f"Wave: {WAVE_FOLDER}"])
            self.assertEqual(run["ids_after_add"], existing + [PLAN_ID])
            self.assertEqual((run["remove_status"], run["remove_updated"]), ("ok", True))
            self.assertEqual(run["ids_after_remove"], existing)
        self.assertEqual(self.control["ids_before"], [])
        self.assertEqual(self.control["add_status"], "error")


if __name__ == "__main__":
    unittest.main()
