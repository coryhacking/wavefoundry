"""Memory backfill from the read-only archive (wave 1z8tz, change 1z8tt).

AC-1: with the archive unset, inventory rows and backfill rows are unchanged.
AC-2: an archived closed wave written under a second profile is inventoried,
claimed, drafted from and completed; its drafts equal the drafts the same wave
yields when live, and the archive tree stays byte-identical.
AC-3: a live wave with the same id token (different slug) shadows the archived
one, which is skipped with an advisory ``archived_wave_shadowed`` diagnostic
and counted in the run summary; a merely prefix-related id does not shadow.
AC-4: an archive-only repository (no live waves root) inventories and claims
its archived closed waves.
AC-5: without ``include_archive``, ``resolve_wave_dir`` never returns an
archived wave.
"""
from __future__ import annotations

import hashlib
import shutil
import sqlite3
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
from record_layout_support import load_profile, patch_layout  # noqa: E402
from server_tools_support import _make_repo, load_server  # noqa: E402

ARCHIVE_REL = "docs/archive/records"
# The configured live waves root (the shipped layout, or a profile's); this
# file sets only its own archive root.
LIVE_REL = record_paths.WAVES_ROOT
# The archived records' vocabulary: the shared second profile's live names,
# read from its asset (change 1zima), so the suite has one Set/Wave profile.
SECOND = {name: value for name, value in load_profile("second")["modules"]["vocabulary_profile"].items()
          if name in vocabulary_profile.FIELD_NAMES}
ARCHIVED_WAVE = "1a000 old-set"
ARCHIVED_CHANGE = "1a001-feat old-thing"
DECISION_DOC = (
    "# Old Thing\n\n## Decision Log\n\n"
    "| Date | Decision | Reason | Alternatives |\n"
    "| --- | --- | --- | --- |\n"
    "| 2020-01-01 | Keep `foo.py` local | Avoid remote authority | none |\n"
)


def _tree_digest(path: Path) -> str:
    digest = hashlib.sha256()
    for item in sorted(path.rglob("*")):
        digest.update(item.relative_to(path).as_posix().encode())
        if item.is_file() and not item.is_symlink():
            digest.update(item.read_bytes())
    return digest.hexdigest()


def _write_wave(folder: Path, *, archived: bool, status: str = "closed",
                change_id: str = ARCHIVED_CHANGE) -> Path:
    """One wave with one admitted change carrying a code-anchored decision,
    written in the archived (second) or the live vocabulary."""
    folder.mkdir(parents=True)
    if archived:
        v = SECOND
        record, title, id_key, label, status_label = (
            v["RECORD_FILENAME"], v["RECORD_TITLE"], v["ID_KEY"], v["MEMBER_ID_LABEL"], v["MEMBER_STATUS_LABEL"])
    else:
        v = vocabulary_profile
        record, title, id_key, label, status_label = (
            v.RECORD_FILENAME, v.RECORD_TITLE, v.ID_KEY, v.MEMBER_ID_LABEL, v.MEMBER_STATUS_LABEL)
    (folder / record).write_text(
        f"{title}\n\nStatus: {status}\n\n{id_key}: `{folder.name}`\n\n"
        f"{label}: `{change_id}`\n{status_label}: `complete`\n",
        encoding="utf-8",
    )
    (folder / f"{change_id}.md").write_text(DECISION_DOC, encoding="utf-8")
    return folder


class _ArchiveBackfillCase(unittest.TestCase):
    archive_enabled = True

    def setUp(self) -> None:
        self.srv = load_server()
        self.backfill = self.srv._load_script("memory_backfill")
        self.supply = self.srv._load_script("memory_supply")
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = _make_repo(Path(self._tmp.name).resolve() / "repo")
        (self.root / "foo.py").write_text("VALUE = 1\n", encoding="utf-8")
        (self.root / LIVE_REL).mkdir(parents=True, exist_ok=True)
        (self.root / "docs" / "plans").mkdir(parents=True, exist_ok=True)
        self.archived_folder = _write_wave(self.root / ARCHIVE_REL / ARCHIVED_WAVE, archived=True)
        self._enable(self.archive_enabled)
        refresh = patch.object(self.srv, "_trigger_background_index_refresh_for_paths")
        refresh.start()
        self.addCleanup(refresh.stop)

    def _module_copies(self):
        """Every loaded copy of ``record_paths`` and ``vocabulary_profile`` a
        caller may hold, including the server's cached script modules."""
        import lifecycle_id

        rps = {id(m): m for m in (
            record_paths, sys.modules.get("record_paths"), lifecycle_id.record_paths,
            getattr(self.srv, "record_paths", None), getattr(self.supply, "record_paths", None),
        ) if m is not None}
        vps = {id(m): m for m in (
            vocabulary_profile, sys.modules.get("vocabulary_profile"),
            getattr(self.srv, "_vocab", None), getattr(self.supply, "_vocab", None),
            getattr(self.backfill, "_vocab", None),
            *(r.vocabulary_profile for r in rps.values()),
        ) if m is not None}
        return tuple(rps.values()), tuple(vps.values())

    def _enable(self, enabled: bool) -> None:
        rps, vps = self._module_copies()
        layout = patch_layout(modules=rps, archive_root=ARCHIVE_REL if enabled else None)
        layout.__enter__()
        self.addCleanup(layout.__exit__, None, None, None)
        for vp in vps:
            profile = patch.object(vp, "ARCHIVE_PROFILE", SECOND if enabled else None)
            profile.start()
            self.addCleanup(profile.stop)

    def _wave_rows(self) -> list[tuple[str, str]]:
        conn = sqlite3.connect(str(self.root / ".wavefoundry" / "index" / "memory-state.sqlite"))
        try:
            return sorted(
                (str(r[0]), str(r[1]))
                for r in conn.execute("SELECT wave_id,state FROM memory_backfill_waves")
            )
        finally:
            conn.close()

    def _create(self) -> dict:
        response = self.srv.memory_backfill_response(self.root, mode="create", entry_path="manual")
        self.assertEqual(response["status"], "ok", response)
        return response

    def _live_equivalent_drafts(self) -> list[dict]:
        """The same wave written live in a separate repository."""
        live_root = _make_repo(Path(self._tmp.name).resolve() / "live")
        (live_root / "foo.py").write_text("VALUE = 1\n", encoding="utf-8")
        _write_wave(live_root / LIVE_REL / ARCHIVED_WAVE, archived=False)
        return self.supply.draft_candidates(live_root, ARCHIVED_WAVE, limit=None)


class ArchiveUnsetTests(_ArchiveBackfillCase):
    archive_enabled = False

    def test_ac1_rows_unchanged_with_archive_unset(self) -> None:
        live = _write_wave(self.root / LIVE_REL / "1b000 live-wave", archived=False,
                           change_id="1b001-feat live-thing")
        inventory = self.backfill.inventory_closed_waves(self.root)
        self.assertEqual([row["wave_id"] for row in inventory], [live.name])
        self.assertEqual(set(inventory[0]), {"wave_id", "path", "status", "error", "fingerprint"})
        self.assertEqual(inventory[0]["fingerprint"], self.backfill.source_fingerprint(self.root, live))
        self.assertEqual(self.backfill.shadowed_archive_waves(self.root), ())
        response = self._create()
        self.assertEqual(response["diagnostics"], [])
        self.assertEqual(response["data"]["archived_waves_shadowed"], 0)
        self.assertEqual([row["wave_id"] for row in response["data"]["processed"]], [live.name])
        self.assertEqual(self._wave_rows(), [(live.name, "complete")])


class ArchiveBackfillTests(_ArchiveBackfillCase):
    def test_ac2_archived_wave_inventoried_claimed_drafted_and_completed(self) -> None:
        before = _tree_digest(self.root / ARCHIVE_REL)
        inventory = self.backfill.inventory_closed_waves(self.root)
        self.assertEqual([(r["wave_id"], r["status"], r.get("archived")) for r in inventory],
                         [(ARCHIVED_WAVE, "closed", True)])

        response = self._create()
        processed = response["data"]["processed"]
        self.assertEqual([(p["wave_id"], p["outcome"]) for p in processed],
                         [(ARCHIVED_WAVE, "extracted")])
        self.assertEqual(response["data"]["candidates_drafted"], 1)
        self.assertEqual(self._wave_rows(), [(ARCHIVED_WAVE, "complete")])

        records = self.srv._memory_mod().load_memory_records(self.root)
        self.assertEqual(len(records), 1)
        drafts = self.supply.draft_candidates(
            self.root, ARCHIVED_WAVE, limit=None, wave_dir=self.archived_folder,
            profile=vocabulary_profile.archive_profile())
        self.assertEqual(drafts, self._live_equivalent_drafts())
        self.assertEqual(drafts[0]["evidence"], [ARCHIVED_CHANGE, "1a000"])
        self.assertTrue(drafts[0]["source_event"].startswith(f"decision-log:{ARCHIVED_CHANGE}:"))
        self.assertEqual(records[0]["source_event"], drafts[0]["source_event"])
        self.assertEqual(_tree_digest(self.root / ARCHIVE_REL), before)

    def test_draft_candidates_uses_the_passed_archived_wave_and_profile(self) -> None:
        drafts = self.supply.draft_candidates(
            self.root, ARCHIVED_WAVE, limit=None, wave_dir=self.archived_folder,
            profile=vocabulary_profile.archive_profile())
        self.assertEqual([d["kind"] for d in drafts], ["decision"])
        # Without a resolved wave, resolution stays live-only.
        self.assertEqual(self.supply.draft_candidates(self.root, ARCHIVED_WAVE, limit=None), [])

    def test_memory_propose_drafts_from_an_archived_id(self) -> None:
        got = self.srv.memory_propose_response(self.root, wave_id="1a000", mode="dry_run")
        self.assertEqual(got["status"], "ok", got)
        self.assertEqual(got["data"]["records_proposed"], 1)

    def test_ac3_live_wave_with_same_id_token_shadows_the_archived_one(self) -> None:
        live = _write_wave(self.root / LIVE_REL / "1a000 new-slug", archived=False,
                           change_id="1a002-feat new-thing")
        inventory = self.backfill.inventory_closed_waves(self.root)
        self.assertEqual([row["wave_id"] for row in inventory], [live.name])
        dry = self.srv.memory_backfill_response(self.root, mode="dry_run", entry_path="manual")
        self.assertEqual(dry["data"]["archived_waves_shadowed"], 1)
        response = self._create()
        self.assertEqual(response["data"]["archived_waves_shadowed"], 1)
        self.assertEqual([p["wave_id"] for p in response["data"]["processed"]], [live.name])
        for envelope in (dry, response):
            (diag,) = envelope["diagnostics"]
            self.assertEqual(diag["code"], "archived_wave_shadowed")
            self.assertTrue(diag["advisory"])
            self.assertIn(f"{ARCHIVE_REL}/{ARCHIVED_WAVE}", diag["message"])
            self.assertIn(f"{LIVE_REL}/{live.name}", diag["message"])
        self.assertEqual(self._wave_rows(), [(live.name, "complete")])
        run_id = response["data"]["run_id"]
        self.assertEqual(self.backfill.sync_inventory(self.root, run_id)["archived_waves_shadowed"], 1)
        # The resolver applies the same rule: the archived copy is not reachable.
        self.assertEqual(self.supply.resolve_wave_dir(self.root, ARCHIVED_WAVE, include_archive=True),
                         (None, "wave_not_found"))

    def test_ac3_prefix_related_id_does_not_shadow(self) -> None:
        live = _write_wave(self.root / LIVE_REL / "1a0000 distinct", archived=False,
                           change_id="1a0001-feat distinct-thing")
        inventory = self.backfill.inventory_closed_waves(self.root)
        self.assertEqual([row["wave_id"] for row in inventory], [live.name, ARCHIVED_WAVE])
        self.assertEqual(self.backfill.shadowed_archive_waves(self.root), ())

    def test_ac4_archive_only_repository(self) -> None:
        shutil.rmtree(self.root / LIVE_REL)
        inventory = self.backfill.inventory_closed_waves(self.root)
        self.assertEqual([row["wave_id"] for row in inventory], [ARCHIVED_WAVE])
        self.assertEqual(self.supply.resolve_wave_dir(self.root, "1a000", include_archive=True),
                         (self.archived_folder, None))
        response = self._create()
        self.assertEqual([(p["wave_id"], p["outcome"]) for p in response["data"]["processed"]],
                         [(ARCHIVED_WAVE, "extracted")])
        self.assertEqual(self._wave_rows(), [(ARCHIVED_WAVE, "complete")])

    def test_ac5_resolver_is_live_only_by_default(self) -> None:
        self.assertEqual(self.supply.resolve_wave_dir(self.root, "1a000"), (None, "wave_not_found"))
        self.assertEqual(self.supply.resolve_wave_dir(self.root, ARCHIVED_WAVE),
                         (None, "wave_not_found"))
        self.assertEqual(self.supply.resolve_wave_dir(self.root, "1a000", include_archive=True),
                         (self.archived_folder, None))
        shutil.rmtree(self.root / LIVE_REL)
        self.assertEqual(self.supply.resolve_wave_dir(self.root, "1a000"), (None, "wave_not_found"))

    def test_live_wave_wins_over_archive_in_resolution(self) -> None:
        live = _write_wave(self.root / LIVE_REL / "1a000 new-slug", archived=False,
                           change_id="1a002-feat new-thing")
        self.assertEqual(self.supply.resolve_wave_dir(self.root, "1a000", include_archive=True),
                         (live, None))


if __name__ == "__main__":
    unittest.main()
