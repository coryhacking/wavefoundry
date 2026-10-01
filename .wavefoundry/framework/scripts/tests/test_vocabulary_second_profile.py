"""Readers follow a second vocabulary profile (wave 1z8mm, change 1z826, AC-2).

The scripts tree is copied and the shared second-profile asset
(``tests/fixtures/profiles/second.json``, changes 1zim1 and 1zima) applied to
it the way a fork edits it at merge time; the docs-lint fixture is localized
into the second profile's names, read from the asset (Set records holding
Waves: ``set.md``, ``set-id``, ``## Waves``, ``Wave ID``, ``Wave Status`` and
so on, mirroring a distribution that renamed its tiers to Set and Wave) and
its nested live root. A fresh interpreter
over the copied tree then runs discovery, docs-lint, ``list_waves``,
``wf_get_change``, dashboard parsing, memory backfill and the review-policy
digest against those records.

Every assertion is paired with a control: a tree with only the asset's layout
applied (the default vocabulary) over the same records finds nothing (or reads
a different value), so a reader that still hard-codes a default marker fails
here rather than passing vacuously.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from record_layout_support import (
    apply_profile,
    copy_scripts_tree,
    load_profile,
    localized_docs_lint_fixture,
    shipped_default_profile,
    with_vocabulary,
)

WAVE_FOLDER = "change-2026-03"

SECOND = load_profile("second")
SECOND_PROFILE = SECOND["modules"]["vocabulary_profile"]
LAYOUT = SECOND["modules"]["record_paths"]
# The fixture's wave folder under the asset's (nested) live root.
WAVE_DIR_REL = f"{LAYOUT['WAVES_ROOT']}/{WAVE_FOLDER}"

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
wave_dir = root / sys.argv[3]
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


def _copy_tree(dest: Path, profile: dict, modules: "tuple[str, ...] | None" = None) -> Path:
    """Copy the framework's ``scripts`` and ``install`` under ``dest``, reset
    it to the shipped defaults (the suite may itself run under a profile),
    apply ``profile`` (only ``modules`` of it, when given) the way a fork
    does, and return the copied scripts directory."""
    scripts = copy_scripts_tree(dest, with_support=False)
    apply_profile(scripts, shipped_default_profile())
    apply_profile(scripts, profile, modules=modules)
    return scripts


def _layout_only(dest: Path) -> Path:
    """The control tree: the asset's layout, the default vocabulary."""
    return _copy_tree(dest, SECOND, modules=("record_paths",))


def _second_profile_records(dest: Path) -> Path:
    localized_docs_lint_fixture(dest, vocabulary=SECOND_PROFILE, layout=LAYOUT)
    path = sorted((dest / WAVE_DIR_REL).glob("00058-*.md"))[0]
    # A status line the dashboard and the digest must both read.
    text = path.read_text(encoding="utf-8")
    status = f"Status: active\n{SECOND_PROFILE['MEMBER_STATUS_LABEL']}: `planned`\n"
    path.write_text(text.replace("Status: active\n", status, 1), encoding="utf-8")
    return dest


def _run(tree: Path, root: Path) -> dict:
    result = subprocess.run(
        [sys.executable, "-B", "-c", DRIVER, str(tree), str(root), WAVE_DIR_REL,
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
        cls.second = _run(_copy_tree(base / "second", SECOND), records)
        cls.control = _run(_layout_only(base / "default"), records)

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
WAVE_SET = with_vocabulary(
    SECOND, ITEM_NAME="Wave", ITEM_NAME_PLURAL="Waves", MEMBER_HEADING="## Waves",
    MEMBER_ID_LABEL="Wave ID", MEMBER_STATUS_LABEL="Wave Status", BACKREF_LABEL="Wave",
)
# The suffix pair: `ID:` is a substring of `Wave ID:`, so only a line-anchored
# reader tells them apart (the four ID_KEY record tests in docs-lint).
SUFFIX_PAIR = with_vocabulary(WAVE_SET, ID_KEY="ID")
WAVE_SET_PROFILE = WAVE_SET["modules"]["vocabulary_profile"]
SUFFIX_PAIR_PROFILE = SUFFIX_PAIR["modules"]["vocabulary_profile"]
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
scripts, root, wave_rel = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
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
wave_dir = root / wave_rel
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
    """The docs-lint fixture localized into ``profile``'s names and the
    asset's layout, with a ``Wave:`` back-reference on one change doc and a
    ``Wave: TBD`` plan."""
    localized_docs_lint_fixture(dest, vocabulary=profile, layout=LAYOUT)
    path = sorted((dest / WAVE_DIR_REL).glob("00058-*.md"))[0]
    text = path.read_text(encoding="utf-8")
    text = text.replace("Status: active\n", f"Status: active\n{profile['MEMBER_STATUS_LABEL']}: `planned`\n", 1)
    # After the `Wave ID:` line, so a reader of bare `Wave` finds the wrong line first.
    id_line = f"{profile['MEMBER_ID_LABEL']}: `00058-bug fixture-core`\n"
    text = text.replace(id_line, id_line + f"{profile['BACKREF_LABEL']}: `{BACKREF_VALUE}`\n", 1)
    path.write_text(text, encoding="utf-8")
    plans = dest / "docs" / "plans"
    plans.mkdir(parents=True, exist_ok=True)
    (plans / f"{PLAN_ID}.md").write_text(PLAN_DOC, encoding="utf-8")
    return dest


def _run_wave_set(tree: Path, root: Path, backref: str) -> dict:
    result = subprocess.run(
        [sys.executable, "-B", "-c", WAVE_SET_DRIVER, str(tree), str(root), WAVE_DIR_REL, PLAN_ID, backref],
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
        cls.second = _run_wave_set(_copy_tree(base / "second", WAVE_SET),
                                   _wave_set_records(base / "records-second", WAVE_SET_PROFILE), "Wave")
        cls.control = _run_wave_set(_layout_only(base / "default"),
                                    _wave_set_records(base / "records-control", WAVE_SET_PROFILE), "Wave")
        cls.suffix = _run_wave_set(_copy_tree(base / "suffix", SUFFIX_PAIR),
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
