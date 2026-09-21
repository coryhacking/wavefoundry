"""Wave lifecycle/review/governance MCP tool tests (shard 3 of 3, wave
1tmtx), split from test_server_tools.py; shared fixtures come from
server_tools_support.
"""
from __future__ import annotations

import ast
import asyncio
import contextlib
import hashlib
import importlib.util
import inspect
import json
import math
import os
import stat
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
import server_tools_support
from server_tools_support import (  # noqa: F401 — shared server-test fixtures
    SCRIPTS_ROOT,
    SERVER_PATH,
    integrity_checks,
    load_server,
    load_thin_runner,
    _make_repo,
    _store_read_meta,
    _seed_store_state,
    _write_index_layer,
    _write_sqlite_index,
)


def _make_wave(tmp: Path, wave_id: str, status: str, changes: list[dict]) -> Path:
    """Write a wave.md into docs/waves/<wave_id>/."""
    wave_dir = tmp / "docs" / "waves" / wave_id
    wave_dir.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Wave Record\n",
        f"wave-id: `{wave_id}`\n",
        f"Status: {status}\n",
        "\n## Changes\n\n",
    ]
    for c in changes:
        lines.append(f"Change ID: `{c['id']}`\n")
        lines.append(f"Change Status: `{c['status']}`\n\n")
    (wave_dir / "wave.md").write_text("".join(lines), encoding="utf-8")
    return wave_dir


def _prepare_council_verdict_line(
    *,
    date: str = "2026-05-21",
    verdict: str = "PASS",
    rotating_seat: str = "none",
    strongest_challenge: str = "red-team identified the remaining unknowns",
    strongest_alternative: str = "keep the verdict structured and machine-readable",
) -> str:
    seats = "red-team, architecture-reviewer, security-reviewer, qa-reviewer, reality-checker"
    if rotating_seat and rotating_seat != "none":
        seats = f"{seats}, {rotating_seat}"
    return (
        f"- **Prepare-phase Wave Council [prepare-council] — {date}: {verdict}** "
        f"(moderator: wave-council; primer-depth: standard; seats: {seats}; rotating-seat: {rotating_seat}; "
        f"strongest-challenge: {strongest_challenge}; strongest-alternative: {strongest_alternative})"
    )


def _append_review_run(root: Path, wave_id: str, *, kind: str = "readiness") -> None:
    """Append a minimal executable lifecycle run to a new external-ledger wave."""
    wave_md = root / "docs" / "waves" / wave_id / "wave.md"
    short_id = wave_id.split()[0]
    evidence_id = f"dedup-{kind}-{short_id}"
    run_id = f"{kind}-{short_id}"
    evidence = {
        "record_type": "executable_evidence",
        "evidence_record_id": evidence_id,
        "claim_id": evidence_id,
        "claim_kind": "dedup",
        "required_for_approval": False,
        "phase": "readiness" if kind == "readiness" else "delivery",
        "proposition": f"{kind} candidates were deduplicated",
        "counterexample_or_failure_condition": "a duplicate candidate remains",
        "execution_status": "executed",
        "public_path": "public lifecycle fixture",
        "command_or_fixture": "test_server_tools lifecycle fixture",
        "expected": "zero duplicate candidates",
        "observed": "zero duplicate candidates",
        "artifact_or_test_id": f"test:{run_id}",
        "adjacent_controls": ["empty candidate set"],
        "test_ran_without_unintended_skip": True,
        "public_path_reached": True,
        "boundary_values_realistic": True,
        "assertions_non_vacuous": True,
        "known_bad_detected": True,
        "known_bad_detection_method": "duplicate injection control",
        "limitations": "temporary local wave",
        "safety_and_authorization": "local temporary fixture only",
        "probe_class": "local_safe",
        "authorization_status": "not_required",
        "safe_boundary": False,
        "unexecuted_remainder_prohibited": False,
        "universal_claim": False,
        "verification_context": {
            "actor": "qa-reviewer",
            "context_id": f"context-{run_id}",
            "fresh_context": True,
            "independent": True,
        },
    }
    run = {
        "record_type": "review_run",
        "review_run_id": run_id,
        "run_kind": kind,
        "cycle": 0,
        "candidate_finding_ids": [],
        "source_record_ids": ["test-council"],
        "dedup_evidence_id": evidence_id,
    }
    review = sys.modules["review_evidence"]
    events = review.review_event_path(wave_md)
    existing, errors = review.read_review_event_ledger(wave_md)
    assert not errors, errors
    records = (*existing, evidence, run)
    events.write_bytes(review.canonical_review_events_bytes(records))
    text = review.render_review_evidence_projection(
        wave_md.read_text(encoding="utf-8"), records
    )
    wave_md.write_text(text, encoding="utf-8")


def _append_typed_approval(
    root: Path,
    wave_id: str,
    signoff_key: str,
    *,
    actor: str,
) -> None:
    """Append one typed approval through the canonical external-ledger shape."""
    wave_md = root / "docs" / "waves" / wave_id / "wave.md"
    review = sys.modules["review_evidence"]
    existing, errors = review.read_review_event_ledger(wave_md)
    assert not errors, errors
    approval = WaveLifecycleMutationTests._approval_record(signoff_key, actor=actor)
    records = (*existing, approval)
    review.review_event_path(wave_md).write_bytes(
        review.canonical_review_events_bytes(records)
    )
    text = review.render_review_evidence_projection(
        wave_md.read_text(encoding="utf-8"), records
    )
    text = review.render_review_status_projection(
        text,
        records,
        review.required_review_status_keys(root, text, records),
    )
    wave_md.write_text(text, encoding="utf-8")


# ---------------------------------------------------------------------------
# Wave inspection
# ---------------------------------------------------------------------------


def _evidence_wave_md(srv, root, wave_key):
    """Resolve once at the test boundary; extracted evidence units take paths."""
    return srv._find_wave_md(root, wave_key)


class ListWavesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def test_no_waves_dir_returns_empty(self):
        result = self.srv.list_waves(self.root)
        self.assertEqual(result, [])

    def test_parses_wave_id_and_status(self):
        _make_wave(self.root, "1200a my-wave", "active", [])
        waves = self.srv.list_waves(self.root)
        self.assertEqual(len(waves), 1)
        self.assertEqual(waves[0]["wave_id"], "1200a my-wave")
        self.assertEqual(waves[0]["status"], "active")

    def test_parses_changes(self):
        _make_wave(self.root, "1200a my-wave", "active", [
            {"id": "1234-feat foo", "status": "ready"},
            {"id": "1235-bug bar", "status": "planned"},
        ])
        waves = self.srv.list_waves(self.root)
        changes = waves[0]["changes"]
        self.assertEqual(len(changes), 2)
        self.assertEqual(changes[0]["id"], "1234-feat foo")
        self.assertEqual(changes[0]["status"], "ready")

    def test_multiple_waves_sorted(self):
        _make_wave(self.root, "1100a wave-one", "closed", [])
        _make_wave(self.root, "1200a wave-two", "active", [])
        waves = self.srv.list_waves(self.root)
        names = [w["wave_id"] for w in waves]
        self.assertEqual(names, sorted(names))

    def test_mixed_width_corpus_sorts_by_decoded_value(self):
        """Wave 1p9q0 AC-6b — a 6-char (post-overflow) wave must list AFTER
        every 5-char wave. A filename-string sort inverts this ("100000" <
        "zzzzz" lexically while decoding to 36^5 > 36^5 - 1)."""
        _make_wave(self.root, "zzzzz last-five-char", "closed", [])
        _make_wave(self.root, "100000 first-six-char", "active", [])
        _make_wave(self.root, "1p9pk mid-v1", "closed", [])
        _make_wave(self.root, "1w1zk early-v2", "closed", [])
        waves = self.srv.list_waves(self.root)
        self.assertEqual(
            [w["wave_id"] for w in waves],
            ["1p9pk mid-v1", "1w1zk early-v2", "zzzzz last-five-char",
             "100000 first-six-char"],
        )

    def test_legacy_baseline_sorts_first_and_unprefixed_last(self):
        _make_wave(self.root, "00000 wave-zero", "closed", [])
        _make_wave(self.root, "1200a normal", "active", [])
        (self.root / "docs" / "waves" / "unprefixed-dir").mkdir(parents=True, exist_ok=True)
        (self.root / "docs" / "waves" / "unprefixed-dir" / "wave.md").write_text(
            "# Wave Record\n\nwave-id: `unprefixed-dir`\nStatus: closed\n",
            encoding="utf-8",
        )
        waves = self.srv.list_waves(self.root)
        ids = [w["wave_id"] for w in waves]
        self.assertEqual(ids[0], "00000 wave-zero")
        self.assertEqual(ids[1], "1200a normal")

    def test_list_response_exposes_page_bounded_scalar_metrics(self):
        _make_wave(self.root, "1200a first", "active", [])
        _make_wave(self.root, "1200b second", "closed", [])

        response = self.srv.wf_list_waves_response(self.root, limit=1)

        self.assertEqual([wave["wave_id"] for wave in response["data"]["waves"]], ["1200a first"])
        metrics = response["data"]["wave_metrics"]
        self.assertEqual(set(metrics), {"1200a first"})
        metric = metrics["1200a first"]
        self.assertEqual(set(metric), {"context", "review", "memory"})
        self.assertEqual(metric["context"]["estimated_tokens_saved"], 0)
        self.assertEqual(metric["memory"]["estimated_exploration_avoided"], 0)
        self.assertFalse(metric["review"]["available"])

    def test_list_response_isolates_an_unavailable_metric_group(self):
        _make_wave(self.root, "1200a first", "active", [])

        with patch.object(
            self.srv.context_efficiency,
            "read_wave_snapshot",
            side_effect=RuntimeError("unavailable snapshot"),
        ):
            response = self.srv.wf_list_waves_response(self.root)

        metric = response["data"]["wave_metrics"]["1200a first"]
        self.assertEqual(metric["context"], {"available": False})
        self.assertIn("memory", metric)
        self.assertIn("review", metric)


class ListPlansTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def test_no_plans_dir_returns_empty(self):
        result = self.srv.list_plans(self.root)
        self.assertEqual(result, [])

    def test_parses_plan_id_status_title_and_path(self):
        _make_repo(self.root, {
            "docs/plans/1234-feat sample.md": (
                "# Sample Plan\n\n"
                "Change ID: `1234-feat sample`\n"
                "Change Status: `planned`\n"
            ),
        })

        plans = self.srv.list_plans(self.root)

        self.assertEqual(len(plans), 1)
        self.assertEqual(plans[0]["id"], "1234-feat sample")
        self.assertEqual(plans[0]["status"], "planned")
        self.assertEqual(plans[0]["title"], "Sample Plan")
        self.assertEqual(plans[0]["path"], "docs/plans/1234-feat sample.md")

    def test_ignores_plan_template(self):
        _make_repo(self.root, {
            "docs/plans/plan-template.md": "# Template\n\nChange ID: `<id>`\n",
            "docs/plans/1234-feat sample.md": "# Sample\n",
        })

        plans = self.srv.list_plans(self.root)

        self.assertEqual([p["id"] for p in plans], ["1234-feat sample"])

    def test_mixed_width_corpus_sorts_by_decoded_value(self):
        """Wave 1p9q0 AC-6b — plans listing is decode-keyed, so a 6-char
        (post-overflow) plan lists after every 5-char plan and v1/v2 5-char
        plans interleave by value."""
        _make_repo(self.root, {
            "docs/plans/zzzzz-enh last-five.md": "# Last Five\n\nChange ID: `zzzzz-enh last-five`\n",
            "docs/plans/100000-bug first-six.md": "# First Six\n\nChange ID: `100000-bug first-six`\n",
            "docs/plans/1p9pk-enh mid-v1.md": "# Mid V1\n\nChange ID: `1p9pk-enh mid-v1`\n",
            "docs/plans/1w1zk-bug early-v2.md": "# Early V2\n\nChange ID: `1w1zk-bug early-v2`\n",
        })
        plans = self.srv.list_plans(self.root)
        self.assertEqual(
            [p["id"] for p in plans],
            ["1p9pk-enh mid-v1", "1w1zk-bug early-v2", "zzzzz-enh last-five",
             "100000-bug first-six"],
        )


class CurrentWaveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def test_returns_active_wave(self):
        _make_wave(self.root, "1200a wave", "active", [])
        wave = self.srv.current_wave(self.root)
        self.assertIsNotNone(wave)
        self.assertEqual(wave["status"], "active")

    def test_returns_planned_wave_if_no_active(self):
        _make_wave(self.root, "1200a wave", "planned", [])
        wave = self.srv.current_wave(self.root)
        self.assertIsNotNone(wave)

    def test_open_wave_outranks_earlier_planned_wave(self):
        _make_wave(self.root, "1200a planned", "planned", [])
        _make_wave(self.root, "1200b open", "implementing", [])
        wave = self.srv.current_wave(self.root)
        self.assertEqual(wave["wave_id"], "1200b open")

    def test_returns_none_when_all_closed(self):
        _make_wave(self.root, "1200a wave", "closed", [])
        wave = self.srv.current_wave(self.root)
        self.assertIsNone(wave)

    def test_returns_none_when_no_waves(self):
        wave = self.srv.current_wave(self.root)
        self.assertIsNone(wave)


class GetChangeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def test_finds_change_by_prefix_in_waves(self):
        _make_repo(self.root, {
            "docs/waves/1200a wave/1234-feat foo.md": "# Change\n\nsome content",
        })
        text = self.srv.get_change(self.root, "1234")
        self.assertIsNotNone(text)
        self.assertIn("some content", text)

    def test_returns_none_when_not_found(self):
        text = self.srv.get_change(self.root, "9999-nonexistent")
        self.assertIsNone(text)

    def test_case_insensitive_match(self):
        _make_repo(self.root, {
            "docs/waves/1200a wave/1234-feat Foo.md": "# Change\n",
        })
        text = self.srv.get_change(self.root, "1234-FEAT")
        self.assertIsNotNone(text)


class GetPromptTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def test_finds_prompt_by_slug(self):
        _make_repo(self.root, {
            "docs/prompts/plan-feature.prompt.md": "# Plan Feature\n\nDo the thing.\n",
        })
        text = self.srv.get_prompt(self.root, "plan-feature")
        self.assertIsNotNone(text)
        self.assertIn("Do the thing", text)

    def test_returns_none_when_no_match(self):
        text = self.srv.get_prompt(self.root, "nonexistent-shortcut")
        self.assertIsNone(text)

    def test_falls_back_to_content_search(self):
        _make_repo(self.root, {
            "docs/prompts/misc.md": "# Misc\n\nPrepare wave instructions here.\n",
        })
        text = self.srv.get_prompt(self.root, "Prepare wave")
        self.assertIsNotNone(text)


# ---------------------------------------------------------------------------
# new_change
# ---------------------------------------------------------------------------

class NewChangeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def test_new_change_passes_repo_root_to_build_id(self):  # 1p45b AC-2
        lc = self.srv._lifecycle_module()
        with patch.object(lc, "build_id", wraps=lc.build_id) as spy:
            self.srv.new_change(self.root, "feat", "dedup-x")
        self.assertEqual(spy.call_args.kwargs.get("repo_root"), self.root)

    def test_create_wave_passes_repo_root_to_build_id(self):  # 1p45b AC-2
        lc = self.srv._lifecycle_module()
        with patch.object(lc, "build_id", wraps=lc.build_id) as spy:
            self.srv.create_wave(self.root, "dedup-wave", mode="dry_run")
        self.assertEqual(spy.call_args.kwargs.get("repo_root"), self.root)

    def test_creates_change_doc_file(self):
        result = self.srv.new_change(self.root, "feat", "my-feature")
        out_path = self.root / result["path"]
        self.assertTrue(out_path.exists())

    def test_id_has_kind_and_slug(self):
        result = self.srv.new_change(self.root, "feat", "my-feature")
        self.assertIn("feat", result["id"])
        self.assertIn("my-feature", result["id"])

    def test_path_uses_forward_slashes(self):
        result = self.srv.new_change(self.root, "bug", "login-broken")
        self.assertNotIn("\\", result["path"])

    def test_uses_template_if_exists(self):
        plans_dir = self.root / "docs" / "plans"
        plans_dir.mkdir(parents=True, exist_ok=True)
        (plans_dir / "plan-template.md").write_text(
            "# Template\n\nChange ID: `<id>`\nCustom field: yes\n",
            encoding="utf-8",
        )
        result = self.srv.new_change(self.root, "feat", "from-template")
        text = (self.root / result["path"]).read_text(encoding="utf-8")
        self.assertIn("Custom field: yes", text)

    def test_falls_back_to_default_template(self):
        result = self.srv.new_change(self.root, "feat", "no-template")
        text = (self.root / result["path"]).read_text(encoding="utf-8")
        self.assertIn("Acceptance Criteria", text)
        self.assertIn("## Agent Execution Graph", text)
        self.assertNotIn("{{generated_at}}", text)

    def test_default_template_resolves_target_file_before_module(self):
        target = self.root / ".wavefoundry/framework/install/plan-template.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("# Target template\n", encoding="utf-8")
        self.assertEqual(self.srv._default_template(self.root), "# Target template\n")
        packaged = SCRIPTS_ROOT.parent / "install" / "plan-template.md"
        self.assertEqual(
            self.srv._default_template(),
            packaged.read_text(encoding="utf-8"),
        )

    def test_supports_all_lifecycle_change_kinds(self):
        kind_slugs = {
            "bug": "sample-bug",
            "feat": "sample-feature",
            "enh": "sample-enhancement",
            "change": "sample-change",
            "doc": "sample-documentation",
            "debt": "sample-tech-debt",
            "ref": "sample-refactor",
            "task": "sample-task",
            "maint": "sample-maintenance",
            "ops": "sample-operations",
        }
        for kind, slug in kind_slugs.items():
            with self.subTest(kind=kind):
                result = self.srv.new_change(self.root, kind, slug)
                self.assertIn(f"-{kind} ", result["id"])
                self.assertTrue((self.root / result["path"]).exists())


# ---------------------------------------------------------------------------
# McpRepoCache
# ---------------------------------------------------------------------------

class WaveMapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def test_wf_map_resolves_doc_path_and_reads_excerpt(self):
        index = MagicMock()
        index._ensure_loaded = MagicMock()
        index._docs_chunks = []
        index._code_chunks = []
        addr = "doc:docs/workflow-config.json"
        result = self.srv.wf_map_response(self.root, addr, index)
        self.assertEqual(result["status"], "ok")
        self.assertTrue(result["data"]["file_exists"])
        self.assertEqual(result["data"]["path"], "docs/workflow-config.json")
        self.assertIn("lifecycle_id_policy", result["data"]["excerpt"])

    def test_wf_map_rejects_bad_address_scheme(self):
        index = MagicMock()
        result = self.srv.wf_map_response(self.root, "http:evil", index)
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["diagnostics"][0]["code"], "invalid_address")

    def test_wf_map_rejects_path_outside_root(self):
        index = MagicMock()
        result = self.srv.wf_map_response(self.root, "doc:../../../etc/passwd", index)
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["diagnostics"][0]["code"], "path_outside_allowed_roots")


class WaveCreateScaffoldAlignmentTests(unittest.TestCase):
    """Newly-created waves emerge lint-clean from `wf_create_wave` without
    operators having to structurally repair the skeleton. The skeleton
    includes `## Objective`; journals are retired (wave 1t9w9) so none is
    scaffolded; the Change-ID lint deferral keeps the wave valid until the
    first change is admitted."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))
        lifecycle = self.srv._lifecycle_module()
        lifecycle._last_assigned_prefix = None

    def tearDown(self):
        self.tmp.cleanup()
        lifecycle = self.srv._lifecycle_module()
        lifecycle._last_assigned_prefix = None

    def _create_wave(self, slug):
        return self.srv.wf_create_wave_response(
            self.root, slug, mode="create",
        )["data"]

    def test_skeleton_includes_objective_section(self):
        """AC-2: `## Objective` appears between `Title:` and `## Changes`."""
        result = self._create_wave("alpha-wave")
        wave_md = self.root / result["path"]
        text = wave_md.read_text(encoding="utf-8")
        self.assertIn("## Objective", text)
        # Order check: Title line precedes ## Objective which precedes ## Changes
        title_idx = text.find("Title:")
        obj_idx = text.find("## Objective")
        changes_idx = text.find("## Changes")
        self.assertLess(title_idx, obj_idx)
        self.assertLess(obj_idx, changes_idx)

    def test_new_wave_opts_into_review_evidence_with_valid_empty_owned_block(self):
        result = self._create_wave("review-evidence-wave")
        wave_md = self.root / result["path"]
        text = wave_md.read_text(encoding="utf-8")
        # declaration-check: asserts the declaration contract; creates no lifecycle state
        self.assertIn("review-evidence-source: events.jsonl", text)
        self.assertNotIn("review-evidence-protocol", text)
        self.assertNotIn("```jsonl", text)
        self.assertIn("## Finding Synthesis", text)
        self.assertIn("wave:finding-synthesis begin", text)
        events = wave_md.parent / "events.jsonl"
        self.assertEqual(events.read_bytes(), b"")
        validation = self.srv.validate_external_review_evidence(wave_md)
        self.assertTrue(validation.ok, validation.errors)
        # Wave 1tomw (AC-1): creation writes no receipt sidecar of any kind.
        self.assertFalse(
            (self.root / "docs" / "waves" / "review-evidence-adoptions.json").exists()
        )
        self.assertFalse(
            (self.root / "docs" / "waves" / "review-evidence-migration.json").exists()
        )

    def test_source_removal_is_the_documented_undetectable_boundary(self):
        # Wave 1tomw (AC-9 companion), boundary narrowed by wave 1to78: with
        # no receipt state, removing the declaration reclassifies the wave as
        # prose-only legacy with no lifecycle diagnostic. The sibling ledger
        # here is EMPTY, so this exercises the NARROWED undetected boundary
        # (seed 209): whole-ledger rollback, empty-ledger declaration
        # removal, and co-deletion of ledger plus declaration. A surviving
        # NON-EMPTY ledger without a readable declared (or legacy-marked)
        # wave.md is now a DETECTED state: the docs-lint orphan-ledger
        # check fails it (see test_docs_lint.py's control matrix), covering
        # both declaration-line removal and wave.md deletion or rename.
        # Git/backups remain the optional history authority. A DOWNGRADED
        # declaration that is still present remains rejected.
        result = self._create_wave("events-only-wave")
        wave_md = self.root / result["path"]
        original = wave_md.read_text(encoding="utf-8")
        removed = re.sub(r"(?m)^review-evidence-source: events\.jsonl\n", "", original)
        removed = re.sub(
            r"(?ms)^## Finding Synthesis\n.*?^## Review Evidence\n",
            "## Review Evidence\n",
            removed,
        )
        wave_md.write_text(removed, encoding="utf-8")
        response = self.srv.wf_prepare_wave_response(self.root, result["wave_id"], mode="dry_run")
        self.assertFalse(
            any(
                diagnostic["code"] == "review_evidence_invalid"
                for diagnostic in response.get("diagnostics", [])
            ),
            response,
        )
        downgraded = original.replace(
            # declaration-check: removes or corrupts a declaration to test fail-closed behavior
            "review-evidence-source: events.jsonl",
            "review-evidence-source: wrong.jsonl",
        )
        wave_md.write_text(downgraded, encoding="utf-8")
        response = self.srv.wf_prepare_wave_response(self.root, result["wave_id"], mode="dry_run")
        self.assertTrue(
            any(
                diagnostic["code"] == "review_evidence_invalid"
                and "must be exactly" in diagnostic["message"]
                for diagnostic in response.get("diagnostics", [])
            ),
            response,
        )

    def test_wave_creation_scaffolds_no_journal(self):
        """1t9w9: journals are retired — wave creation writes no journal file
        and the envelope no longer advertises one; in-flight capture belongs
        to Progress Logs and memory candidates."""
        result = self._create_wave("beta-wave")
        self.assertNotIn("journal_path", result)
        self.assertNotIn("journal_created", result)
        journals_dir = self.root / "docs" / "agents" / "journals"
        self.assertFalse(
            journals_dir.exists() and any(journals_dir.iterdir()),
            "no journal file may be created for a new wave",
        )

    def test_dry_run_advertises_no_journal(self):
        result = self.srv.wf_create_wave_response(
            self.root, "zeta-wave", mode="dry_run",
        )["data"]
        self.assertNotIn("journal_path", result)
        self.assertFalse((self.root / result["path"]).exists())

    def test_new_scaffold_uses_watchpoints_heading(self):
        """New wave scaffolds carry `## Watchpoints`; the legacy
        `## Journal Watchpoints` heading remains lint-valid on old waves."""
        result = self._create_wave("eta-wave")
        text = (self.root / result["path"]).read_text(encoding="utf-8")
        self.assertIn("## Watchpoints\n", text)
        self.assertNotIn("## Journal Watchpoints", text)





class LifecycleIdPreservationTests(unittest.TestCase):
    """Wave 1p3dk / 1p3ds: dry_run preview must not burn lifecycle ID slots,
    and a change-doc creation must consume exactly one prefix (defect B in
    the field report — `change_create` previously called `build_id` twice
    via `new_change`)."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))
        # Reset the lifecycle counter between tests so each test starts from
        # the time-based prefix rather than inheriting the previous test's
        # in-process advancement.
        lifecycle = self.srv._lifecycle_module()
        lifecycle._last_assigned_prefix = None

    def tearDown(self):
        self.tmp.cleanup()
        lifecycle = self.srv._lifecycle_module()
        lifecycle._last_assigned_prefix = None

    def test_wave_create_dry_run_does_not_advance_counter(self):
        """AC-4: dry_run preview followed by apply returns the same wave_id."""
        lifecycle = self.srv._lifecycle_module()
        before = lifecycle._last_assigned_prefix
        previewed = self.srv.wf_create_wave_response(
            self.root, "preserve-id-wave", mode="dry_run",
        )
        after_peek = lifecycle._last_assigned_prefix
        self.assertEqual(
            before, after_peek,
            "dry_run must not advance _last_assigned_prefix",
        )
        committed = self.srv.wf_create_wave_response(
            self.root, "preserve-id-wave", mode="create",
        )
        self.assertEqual(
            previewed["data"]["wave_id"],
            committed["data"]["wave_id"],
            "dry_run-then-apply must return the same wave_id (1p3ds AC-4 / AC-10)",
        )

    def test_change_create_dry_run_does_not_advance_counter(self):
        """AC-5 parallel: dry_run preview of a change doc does not burn a slot."""
        lifecycle = self.srv._lifecycle_module()
        before = lifecycle._last_assigned_prefix
        previewed = self.srv._change_create_response(
            self.root, "enh", "preserve-id-change", mode="dry_run",
        )
        after = lifecycle._last_assigned_prefix
        self.assertEqual(before, after, "dry_run change preview must not advance counter")
        # And a subsequent apply returns the same id
        committed = self.srv._change_create_response(
            self.root, "enh", "preserve-id-change", mode="create",
        )
        self.assertEqual(
            previewed["data"]["change_id"],
            committed["data"]["change_id"],
        )

    def test_change_create_apply_consumes_exactly_one_prefix(self):
        """AC-6: defect B fix — a single change-doc creation must advance
        the counter by exactly one slot, not two. Field evidence: the same
        slug previously skipped one prefix per `wf_new_*` call."""
        lifecycle = self.srv._lifecycle_module()
        # Pin the counter to a known starting point by performing one commit
        first = self.srv._change_create_response(
            self.root, "enh", "first-change", mode="create",
        )
        first_prefix = lifecycle._last_assigned_prefix
        second = self.srv._change_create_response(
            self.root, "enh", "second-change", mode="create",
        )
        second_prefix = lifecycle._last_assigned_prefix

        # The two prefixes must be consecutive in base36. Convert and compare.
        first_n = lifecycle.decode_base36(first_prefix)
        second_n = lifecycle.decode_base36(second_prefix)
        self.assertEqual(
            second_n - first_n, 1,
            f"change creation must advance counter by 1, got "
            f"{first_prefix} → {second_prefix} (delta={second_n - first_n}). "
            f"Defect B regression: change_create + new_change burned two ids per call.",
        )

    def test_create_wave_apply_consumes_exactly_one_prefix(self):
        """AC-4 parallel: wave creation must advance the counter by exactly
        one slot. Mirrors the change-creation test but for `create_wave`."""
        lifecycle = self.srv._lifecycle_module()
        self.srv.wf_create_wave_response(
            self.root, "alpha-wave", mode="create",
        )
        first_prefix = lifecycle._last_assigned_prefix
        self.srv.wf_create_wave_response(
            self.root, "beta-wave", mode="create",
        )
        second_prefix = lifecycle._last_assigned_prefix
        first_n = lifecycle.decode_base36(first_prefix)
        second_n = lifecycle.decode_base36(second_prefix)
        self.assertEqual(
            second_n - first_n, 1,
            f"wave creation must advance counter by 1, got "
            f"{first_prefix} → {second_prefix}.",
        )


class WaveLifecycleMutationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))
        _make_wave(self.root, "1200a test-wave", "planned", [])
        _make_repo(self.root, {
            "docs/plans/1200a-feat sample.md": (
                "# Sample\n\n"
                "Change ID: `1200a-feat sample`\n"
                "Change Status: `planned`\n"
                "## Rationale\n\nWhy.\n\n"
                "## Requirements\n\n1. One.\n\n"
                "## Scope\n\nIn scope.\n\n"
                "## Acceptance Criteria\n\n- One.\n\n"
                "## Tasks\n\n- One.\n\n"
                "## AC Priority\n\n| AC | Priority | Rationale |\n| ---- | ---- | ---- |\n| AC-1 | required | Core behavior. |\n"
            ),
        })

    def tearDown(self):
        self.tmp.cleanup()

    @staticmethod
    def _approval_record(signoff_key: str, *, actor: str, fresh: bool = True, independent: bool = True) -> dict:
        return {
            "record_type": "executable_evidence",
            "evidence_record_id": f"approval-{signoff_key}-{actor}",
            "claim_id": f"approval:{signoff_key}",
            "claim_kind": "approval",
            "required_for_approval": True,
            "phase": "delivery",
            "proposition": f"{signoff_key} approval was independently executed",
            "counterexample_or_failure_condition": "the signer is not authorized for the lane",
            "execution_status": "executed",
            "public_path": "wf_review_wave",
            "command_or_fixture": "WaveLifecycleMutationTests approval binding",
            "expected": "the exact authorized actor is bound to the signoff",
            "observed": "the recorded actor was inspected",
            "artifact_or_test_id": f"test:approval-{signoff_key}",
            "adjacent_controls": ["valid exact actor"],
            "test_ran_without_unintended_skip": True,
            "public_path_reached": True,
            "boundary_values_realistic": True,
            "assertions_non_vacuous": True,
            "known_bad_detected": True,
            "known_bad_detection_method": "forged actor control",
            "limitations": "temporary local wave",
            "safety_and_authorization": "local temporary fixture only",
            "probe_class": "local_safe",
            "authorization_status": "not_required",
            "safe_boundary": False,
            "unexecuted_remainder_prohibited": False,
            "universal_claim": False,
            "verification_context": {
                "actor": actor,
                "context_id": f"context-{signoff_key}-{actor}",
                "fresh_context": fresh,
                "independent": independent,
            },
        }

    def _marked_wave_with_approval(self, signoff_key: str, *, actor: str, fresh: bool = True, independent: bool = True) -> str:
        created = self.srv.wf_create_wave_response(
            self.root, f"approval-{signoff_key}", mode="create"
        )
        wave_id = created["data"]["wave_id"]
        _append_review_run(self.root, wave_id, kind="initial_delivery")
        wave_md = self.root / "docs" / "waves" / wave_id / "wave.md"
        approval = self._approval_record(
            signoff_key, actor=actor, fresh=fresh, independent=independent
        )
        review = sys.modules["review_evidence"]
        records, errors = review.read_review_event_ledger(wave_md)
        self.assertFalse(errors)
        updated = (*records, approval)
        review.review_event_path(wave_md).write_bytes(
            review.canonical_review_events_bytes(updated)
        )
        wave_md.write_text(
            review.render_review_evidence_projection(
                wave_md.read_text(encoding="utf-8"), updated
            ),
            encoding="utf-8",
        )
        return wave_id

    def test_wf_create_wave_dry_run(self):
        result = self.srv.wf_create_wave_response(self.root, "new-wave", mode="dry_run")
        self.assertEqual(result["status"], "dry_run")
        self.assertFalse((self.root / result["data"]["path"]).exists())

    def test_wave_add_and_remove_change(self):
        with patch.object(self.srv, "_trigger_background_index_refresh_for_paths") as trigger:
            add = self.srv.wf_add_change_response(self.root, "1200a test-wave", "1200a-feat sample", mode="create")
        self.assertEqual(add["status"], "ok")
        wave_md = self.root / "docs" / "waves" / "1200a test-wave" / "wave.md"
        self.assertIn("1200a-feat sample", wave_md.read_text(encoding="utf-8"))
        self.assertFalse((self.root / "docs" / "plans" / "1200a-feat sample.md").exists())
        self.assertTrue((self.root / "docs" / "waves" / "1200a test-wave" / "1200a-feat sample.md").exists())
        trigger.assert_called_once()

        with patch.object(self.srv, "_trigger_background_index_refresh_for_paths") as trigger:
            remove = self.srv.wf_remove_change_response(self.root, "1200a test-wave", "1200a-feat sample", mode="create")
        self.assertEqual(remove["status"], "ok")
        self.assertNotIn("1200a-feat sample", wave_md.read_text(encoding="utf-8"))
        self.assertTrue((self.root / "docs" / "plans" / "1200a-feat sample.md").exists())
        self.assertFalse((self.root / "docs" / "waves" / "1200a test-wave" / "1200a-feat sample.md").exists())
        trigger.assert_called_once()

    def test_wf_add_change_rejects_ambiguous_prefix(self):
        _make_repo(self.root, {
            "docs/plans/1200a-feat sample-two.md": (
                "# Sample Two\n\n"
                "Change ID: `1200a-feat sample-two`\n"
                "Change Status: `planned`\n"
            ),
        })
        result = self.srv.wf_add_change_response(self.root, "1200a test-wave", "1200a", mode="dry_run")
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["diagnostics"][0]["code"], "ambiguous_change_id")

    def test_wf_add_change_is_safe_if_doc_already_relocated_to_target_wave(self):
        relocated = self.root / "docs" / "waves" / "1200a test-wave" / "1200a-feat sample.md"
        relocated.write_text(
            "# Sample\n\nChange ID: `1200a-feat sample`\nChange Status: `planned`\n",
            encoding="utf-8",
        )
        plan_path = self.root / "docs" / "plans" / "1200a-feat sample.md"
        plan_path.unlink()

        result = self.srv.wf_add_change_response(self.root, "1200a test-wave", "1200a-feat sample", mode="create")

        self.assertEqual(result["status"], "ok")
        self.assertTrue(relocated.exists())
        self.assertIn("1200a-feat sample", (self.root / "docs" / "waves" / "1200a test-wave" / "wave.md").read_text(encoding="utf-8"))

    def test_wf_prepare_wave_requires_admitted_changes(self):
        result = self.srv.wf_prepare_wave_response(self.root, "1200a test-wave", mode="dry_run")
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["diagnostics"][0]["code"], "no_admitted_changes")

    def test_marked_review_evidence_is_enforced_by_prepare_review_and_close(self):
        wave_md = self.root / "docs" / "waves" / "1200a test-wave" / "wave.md"
        review = sys.modules["review_evidence"]
        wave_md.write_text(
            wave_md.read_text(encoding="utf-8").replace(
                "# Wave Record\n",
                # negative-fixture: test_marked_review_evidence_is_enforced_by_prepare_review_and_close deliberately supplies invalid or unreadable authority
                "# Wave Record\n\nreview-evidence-source: events.jsonl\n",
                1,
            )
            + "\n"
            + review.empty_external_finding_synthesis_section(),
            encoding="utf-8",
        )
        review.review_event_path(wave_md).write_bytes(b"{not-json}\n")
        calls = (
            lambda: self.srv.wf_prepare_wave_response(self.root, "1200a test-wave", mode="dry_run"),
            lambda: self.srv.wf_review_wave_response(self.root, "1200a test-wave"),
            lambda: self.srv.wf_close_wave_response(self.root, "1200a test-wave", mode="dry_run"),
        )
        for call in calls:
            result = call()
            self.assertEqual(result["status"], "error")
            self.assertTrue(
                any(d["code"] == "review_evidence_invalid" for d in result["diagnostics"]),
                result["diagnostics"],
            )
            if "review_actions" in result.get("data", {}):
                actions = result["data"]["review_actions"]
                self.assertFalse(actions["available"])
                self.assertEqual(actions["next_actions"], [])
                self.assertIsNone(actions["recommended_next_action"])

    def test_stray_adoption_sidecar_is_never_read_by_lifecycle(self):
        # Wave 1tomw (AC-7): the retired sidecar is dead state. Even a
        # syntactically broken copy neither blocks nor influences lifecycle
        # validation, because no code path opens it.
        adoption = self.root / "docs" / "waves" / "review-evidence-adoptions.json"
        adoption.write_text("{broken", encoding="utf-8")

        result = self.srv.wf_review_wave_response(self.root, "1200a test-wave")

        self.assertFalse(
            any(
                "adoption" in diagnostic["message"]
                for diagnostic in result.get("diagnostics", [])
            ),
            result.get("diagnostics"),
        )

    def test_bullet_participants_are_enforced_by_public_review(self):
        wave_md = self.root / "docs" / "waves" / "1200a test-wave" / "wave.md"
        wave_md.write_text(
            wave_md.read_text(encoding="utf-8")
            + "\n## Participants\n\n"
            + "- Required review lanes: `code-reviewer`, `qa-reviewer`, `security-reviewer`\n"
            + "\n## Review Evidence\n\n- operator-signoff: approved\n",
            encoding="utf-8",
        )
        with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}), \
             patch.object(self.srv.lifecycle_gate_support, "_required_wave_council_signoffs", return_value=[]) as _gate_mock_1:
            response = self.srv.wf_review_wave_response(self.root, "1200a test-wave")
            _gate_mock_1.assert_called()
        self.assertEqual(
            response["data"]["required_lanes"][:4],
            ["operator", "code-reviewer", "qa-reviewer", "security-reviewer"],
        )
        self.assertIn("missing_required_lane", [item["code"] for item in response["diagnostics"]])

    def test_advisory_lint_warnings_reach_prepare_review_and_close_as_non_blocking(self):
        """Wave 1wuju (1wujs AC-1): an advisory sensor's finding is rendered at every
        lifecycle gate as `docs_lint_warning` with `advisory: true`, never as an error."""
        advisory = {"passed": True, "errors": [],
                    "warnings": ["WARNING: docs/waves/1200a test-wave/x.md: AC-1 asserts repository-wide state "
                                 "('full test suite') [advisory sensor `ac_asserts_repository_state`]"],
                    "output": ""}
        calls = {
            "prepare": lambda: self.srv.wf_prepare_wave_response(self.root, "1200a test-wave", "dry_run"),
            "review": lambda: self.srv.wf_review_wave_response(self.root, "1200a test-wave"),
            # Delivery review CODE-DEL-2 / ARCH-DEL-2 / QA-DEL-1: the readiness
            # phase renders through its own branch, so it is exercised by name.
            "review_prepare": lambda: self.srv.wf_review_wave_response(self.root, "1200a test-wave", phase="prepare"),
            "close": lambda: self.srv.wf_close_wave_response(self.root, "1200a test-wave", "dry_run"),
        }
        for gate, call in calls.items():
            with self.subTest(gate=gate):
                with patch.object(self.srv, "run_validate", return_value=advisory), \
                     patch.object(self.srv.lifecycle_gate_support, "_required_wave_council_signoffs", return_value=[]) as _gate_mock_9:
                    response = call()
                    if gate != "review_prepare":
                        _gate_mock_9.assert_called()
                    else:
                        # inert-by-design: prepare review checks lanes, not council currency.
                        _gate_mock_9.assert_not_called()
                diagnostics = response.get("diagnostics", [])
                warnings = [d for d in diagnostics if d["code"] == "docs_lint_warning"]
                self.assertEqual(1, len(warnings), (gate, diagnostics))
                self.assertIs(True, warnings[0].get("advisory"), (gate, warnings[0]))
                self.assertIn("asserts repository-wide state", warnings[0]["message"])
                self.assertNotIn("docs_lint_error", [d["code"] for d in diagnostics], gate)

    def test_review_status_fails_when_executable_approval_is_missing(self):
        created = self.srv.wf_create_wave_response(
            self.root, "review-status-approval", mode="create"
        )
        wave_id = created["data"]["wave_id"]
        _append_review_run(self.root, wave_id, kind="initial_delivery")
        wave_md = self.root / "docs" / "waves" / wave_id / "wave.md"
        wave_md.write_text(
            wave_md.read_text(encoding="utf-8").replace(
                "operator-signoff: <approved when operator confirms closure>",
                "operator-signoff: approved",
            ),
            encoding="utf-8",
        )
        with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}), \
             patch.object(self.srv.lifecycle_gate_support, "_required_wave_council_signoffs", return_value=[]) as _gate_mock_2, \
             patch.object(self.srv, "_extract_required_review_lanes", return_value=[]) as _gate_mock_3_server, \
             patch.object(self.srv.lifecycle_gate_support, "_extract_required_review_lanes", return_value=[]) as _gate_mock_3, \
             patch.object(self.srv, "_read_project_required_review_lanes", return_value=[]) as _gate_mock_4_server, \
             patch.object(self.srv.lifecycle_gate_support, "_read_project_required_review_lanes", return_value=[]) as _gate_mock_4:
            response = self.srv.wf_review_wave_response(self.root, wave_id)
            _gate_mock_2.assert_called()
            _gate_mock_3.assert_called()
            _gate_mock_3_server.assert_called()
            _gate_mock_4.assert_called()
            _gate_mock_4_server.assert_called()
        self.assertEqual(response["status"], "error", response)
        self.assertIn(
            "missing_executable_approval_evidence",
            [item["code"] for item in response["diagnostics"]],
        )

    def test_approval_evidence_binds_exact_actor_and_independence(self):
        forged_operator = self._marked_wave_with_approval(
            "operator-signoff", actor="implementer", fresh=False, independent=False
        )
        self.assertTrue(
            self.srv.lifecycle_gates._approval_evidence_diagnostics(
                "", ["operator-signoff"], root=self.root, wave_md=_evidence_wave_md(self.srv, self.root, forged_operator)
            )
        )
        valid_operator = self._marked_wave_with_approval(
            "operator-signoff", actor="operator", fresh=False, independent=False
        )
        self.assertEqual(
            self.srv.lifecycle_gates._approval_evidence_diagnostics(
                "", ["operator-signoff"], root=self.root, wave_md=_evidence_wave_md(self.srv, self.root, valid_operator)
            ), []
        )

        forged_lane = self._marked_wave_with_approval(
            "qa-reviewer", actor="code-reviewer", fresh=True, independent=True
        )
        self.assertTrue(
            self.srv.lifecycle_gates._approval_evidence_diagnostics(
                "", ["qa-reviewer"], root=self.root, wave_md=_evidence_wave_md(self.srv, self.root, forged_lane)
            )
        )
        stale_lane = self._marked_wave_with_approval(
            "qa-reviewer", actor="qa-reviewer", fresh=False, independent=False
        )
        self.assertTrue(
            self.srv.lifecycle_gates._approval_evidence_diagnostics(
                "", ["qa-reviewer"], root=self.root, wave_md=_evidence_wave_md(self.srv, self.root, stale_lane)
            )
        )
        valid_lane = self._marked_wave_with_approval(
            "qa-reviewer", actor="qa-reviewer", fresh=True, independent=True
        )
        self.assertEqual(
            self.srv.lifecycle_gates._approval_evidence_diagnostics(
                "", ["qa-reviewer"], root=self.root, wave_md=_evidence_wave_md(self.srv, self.root, valid_lane)
            ), []
        )

    def test_approval_evidence_must_follow_latest_repair_affecting_its_lane(self):
        approval = self._approval_record(
            "qa-reviewer", actor="qa-reviewer", fresh=True, independent=True
        )
        repair = {
            "record_type": "finding_synthesis",
            "record_id": "repair-head",
            "finding_id": "finding-1",
            "cycle": 1,
            "approval_recheck_lanes": ["qa-reviewer"],
            "blocking": True,
            "blocking_required_lanes": [],
            "repair_execution_state": "completed",
        }
        diagnostics = self.srv.lifecycle_gates._approval_evidence_diagnostics(
            "marked", ["qa-reviewer"], records=(approval, repair)
        )
        self.assertTrue(diagnostics)
        self.assertIn("chronology", diagnostics[0]["message"])
        self.assertEqual(
            self.srv.lifecycle_gates._approval_evidence_diagnostics(
                "marked", ["qa-reviewer"], records=(repair, approval)
            ), []
        )

    def test_unaffected_lane_approval_survives_later_repair_synthesis(self):
        approval = self._approval_record(
            "qa-reviewer", actor="qa-reviewer", fresh=True, independent=True
        )
        unrelated_repair = {
            "record_type": "finding_synthesis",
            "record_id": "docs-repair-head",
            "finding_id": "docs-finding",
            "cycle": 1,
            "approval_recheck_lanes": ["docs-contract-reviewer"],
            "review_depth": "focused",
        }
        self.assertEqual(
            self.srv.lifecycle_gates._approval_evidence_diagnostics(
                "marked", ["qa-reviewer"], records=(approval, unrelated_repair)
            ), []
        )

    def test_operator_and_full_council_approvals_remain_final_scope(self):
        operator = self._approval_record(
            "operator-signoff", actor="operator", fresh=False, independent=False
        )
        council = self._approval_record(
            "wave-council-delivery", actor="wave-council", fresh=True, independent=True
        )
        full_repair = {
            "record_type": "finding_synthesis",
            "record_id": "full-repair-head",
            "finding_id": "finding-1",
            "cycle": 1,
            "approval_recheck_lanes": [],
            "review_depth": "full",
            "blocking": True,
            "blocking_required_lanes": [],
            "repair_execution_state": "completed",
        }
        diagnostics = self.srv.lifecycle_gates._approval_evidence_diagnostics(
            "marked",
            ["operator-signoff", "wave-council-delivery"],
            records=(operator, council, full_repair),
        )
        self.assertTrue(diagnostics)
        self.assertIn("operator-signoff", diagnostics[0]["message"])
        self.assertIn("wave-council-delivery", diagnostics[0]["message"])

    def test_prepare_readiness_approval_is_not_staled_by_delivery_repairs(self):
        readiness = self._approval_record(
            "wave-council-readiness",
            actor="wave-council",
            fresh=True,
            independent=True,
        )
        full_repair = {
            "record_type": "finding_synthesis",
            "record_id": "full-delivery-repair-head",
            "review_run_id": "run-delivery-origin",
            "finding_id": "finding-1",
            "evidence_record_id": "ev-delivery-finding",
            "cycle": 1,
            "approval_recheck_lanes": [
                "wave-council-readiness",
                "wave-council-delivery",
            ],
            "review_depth": "full",
            "blocking": True,
            "blocking_required_lanes": [],
            "repair_execution_state": "completed",
        }
        delivery_finding = {
            "record_type": "executable_evidence",
            "evidence_record_id": "ev-delivery-finding",
            "claim_kind": "finding",
            "claim_id": "finding-1",
            "phase": "delivery",
        }
        delivery_run = {
            "record_type": "review_run",
            "review_run_id": "run-delivery-origin",
            "run_kind": "initial_delivery",
            "cycle": 0,
        }
        delivery = self._approval_record(
            "wave-council-delivery",
            actor="wave-council",
            fresh=True,
            independent=True,
        )
        self.assertEqual(
            self.srv.lifecycle_gates._approval_evidence_diagnostics(
                "marked",
                ["wave-council-readiness", "wave-council-delivery"],
                records=(readiness, delivery_finding, delivery_run, full_repair, delivery),
            ),
            [],
        )
        self.assertTrue(
            self.srv.lifecycle_gates._approval_evidence_diagnostics(
                "marked",
                ["wave-council-readiness", "wave-council-delivery"],
                records=(readiness, delivery_finding, delivery_run, delivery, full_repair),
            )
        )

    def test_legacy_form_projection_yields_no_stale_lifecycle_diagnostic(self):
        """Wave 1tb4z P1 repair: an old-form external archive (bodyless
        details wrapper, legacy class) is presentation-only equivalent — the
        lifecycle diagnostics must not report its projection as stale."""
        created = self.srv.wf_create_wave_response(
            self.root, "legacy-form-diag", mode="create"
        )
        wave_id = created["data"]["wave_id"]
        wave_md = self.root / "docs" / "waves" / wave_id / "wave.md"
        written = self.srv.wf_review_event_response(
            self.root,
            wave_id,
            "run",
            "wave-council",
            "legacy-form-diag-ctx",
            mode="create",
            run_kind="initial_delivery",
            cycle=0,
        )
        self.assertEqual(written["status"], "ok", written)
        text = wave_md.read_text(encoding="utf-8")
        match = re.search(r"^\*(Machine review state[^\n]*)\*$", text, re.MULTILINE)
        self.assertIsNotNone(match)
        legacy = (
            text[: match.start()]
            + '<details class="wavefoundry-review-evidence">\n'
            + f"<summary>{match.group(1)}</summary>\n"
            + "</details>"
            + text[match.end():]
        )
        wave_md.write_text(legacy, encoding="utf-8")
        diagnostics = self.srv.lifecycle_gates._review_evidence_diagnostics(
            legacy, root=self.root, wave_md=_evidence_wave_md(self.srv, self.root, wave_id)
        )
        rendered = json.dumps(diagnostics)
        self.assertNotIn("stale", rendered, diagnostics)
        # A genuinely stale projection is still detected through the same path.
        broken = legacy.replace("Machine review state", "Machine review state TAMPERED", 1)
        wave_md.write_text(broken, encoding="utf-8")
        diagnostics = self.srv.lifecycle_gates._review_evidence_diagnostics(
            broken, root=self.root, wave_md=_evidence_wave_md(self.srv, self.root, wave_id)
        )
        self.assertIn("stale", json.dumps(diagnostics), diagnostics)

    def test_closed_wave_review_status_is_not_reinterpreted_by_lifecycle(self):
        """1tmb0: closed approval history is not governed by newer staleness rules."""
        created = self.srv.wf_create_wave_response(
            self.root, "closed-review-status", mode="create"
        )
        wave_id = created["data"]["wave_id"]
        wave_md = self.root / "docs" / "waves" / wave_id / "wave.md"
        text = wave_md.read_text(encoding="utf-8")
        text = text.replace("Status: planned", "Status: closed", 1).replace(
            "| wave-council-readiness | pending |",
            "| wave-council-readiness | historical |",
            1,
        )
        wave_md.write_text(text, encoding="utf-8")

        diagnostics = self.srv.lifecycle_gates._review_evidence_diagnostics(
            text, root=self.root, wave_md=_evidence_wave_md(self.srv, self.root, wave_id)
        )

        self.assertNotIn("Review Status projection is stale", json.dumps(diagnostics))

    def test_typed_review_evidence_tool_previews_then_writes_lightweight_run(self):
        created = self.srv.wf_create_wave_response(
            self.root, "typed-review-run", mode="create"
        )
        wave_id = created["data"]["wave_id"]
        wave_md = self.root / "docs" / "waves" / wave_id / "wave.md"
        before = wave_md.read_text(encoding="utf-8")
        preview = self.srv.wf_review_event_response(
            self.root,
            wave_id,
            "run",
            "wave-council",
            "lightweight-delivery",
            run_kind="initial_delivery",
            cycle=0,
        )
        self.assertEqual(preview["status"], "dry_run", preview)
        self.assertEqual(len(preview["data"]["appended_records"]), 1)
        self.assertEqual(wave_md.read_text(encoding="utf-8"), before)
        with patch.object(self.srv, "_trigger_background_index_refresh_for_paths") as refresh:
            written = self.srv.wf_review_event_response(
                self.root,
                wave_id,
                "run",
                "wave-council",
                "lightweight-delivery",
                mode="create",
                run_kind="initial_delivery",
                cycle=0,
            )
        self.assertEqual(written["status"], "ok", written)
        text = wave_md.read_text(encoding="utf-8")
        # Wave 1tb4z: external-ledger projections carry a plain italic summary
        # line, no HTML details wrapper.
        self.assertIn("*Machine review state", text)
        self.assertNotIn("<details", text)
        self.assertIn("| Current finding | Disposition | Open block |", text)
        self.assertTrue(self.srv.validate_external_review_evidence(wave_md).ok)
        refresh.assert_called_once_with(self.root, [wave_md.resolve()])

    def test_typed_review_evidence_tool_requires_explicit_judgment_and_integrity(self):
        created = self.srv.wf_create_wave_response(
            self.root, "typed-review-invalid", mode="create"
        )
        wave_id = created["data"]["wave_id"]
        wave_md = self.root / "docs" / "waves" / wave_id / "wave.md"
        before = wave_md.read_text(encoding="utf-8")
        response = self.srv.wf_review_event_response(
            self.root,
            wave_id,
            "finding",
            "qa-reviewer",
            "missing-facts",
            finding_id="missing-facts",
            run_kind="initial_delivery",
            judgment={"validation_status": "real"},
            evidence={},
        )
        self.assertEqual(response["status"], "error")
        self.assertIn("invalid_review_event", [item["code"] for item in response["diagnostics"]])
        self.assertIn("missing load-bearing fields", "\n".join(item["message"] for item in response["diagnostics"]))
        self.assertEqual(wave_md.read_text(encoding="utf-8"), before)

    def test_typed_review_evidence_tool_rejects_evidence_semantic_key_collisions(self):
        created = self.srv.wf_create_wave_response(
            self.root, "typed-review-collision", mode="create"
        )
        wave_id = created["data"]["wave_id"]
        wave_md = self.root / "docs" / "waves" / wave_id / "wave.md"
        before = wave_md.read_text(encoding="utf-8")

        response = self.srv.wf_review_event_response(
            self.root,
            wave_id,
            "approval",
            "code-reviewer",
            "collision-probe",
            signoff_key="qa-reviewer",
            fresh_context=True,
            independent=True,
            integrity_checks=integrity_checks(),
            evidence={
                "actor": "qa-reviewer",
                "observed": "must not be accepted",
                "artifact_or_test_id": "qa:collision-probe",
            },
        )

        self.assertEqual(response["status"], "error", response)
        self.assertIn(
            "evidence may not override protected semantic field(s): actor",
            "\n".join(item["message"] for item in response["diagnostics"]),
        )
        self.assertEqual(wave_md.read_text(encoding="utf-8"), before)

    def test_typed_review_evidence_tool_rejects_reserved_metadata_without_poisoning_retry(self):
        created = self.srv.wf_create_wave_response(
            self.root, "typed-review-reserved", mode="create"
        )
        wave_id = created["data"]["wave_id"]
        events_path = self.root / "docs" / "waves" / wave_id / "events.jsonl"
        for evidence in (
            {"event_identity": {"actor": "attacker"}},
            {"request_digest": "0" * 64},
        ):
            rejected = self.srv.wf_review_event_response(
                self.root,
                wave_id,
                "run",
                "wave-council",
                "reserved-metadata",
                mode="create",
                run_kind="initial_delivery",
                evidence=evidence,
            )
            self.assertEqual(rejected["status"], "error", rejected)
            self.assertIn(
                "evidence may not override protected semantic field",
                "\n".join(item["message"] for item in rejected["diagnostics"]),
            )
            self.assertEqual(events_path.read_bytes(), b"")

        clean = self.srv.wf_review_event_response(
            self.root,
            wave_id,
            "run",
            "wave-council",
            "reserved-metadata",
            mode="create",
            run_kind="initial_delivery",
        )
        self.assertEqual(clean["status"], "ok", clean)
        self.assertFalse(clean["data"]["replayed"])

    def test_typed_review_writer_rejects_symlinked_wave_directory_escape(self):
        created = self.srv.wf_create_wave_response(
            self.root, "typed-review-symlink", mode="create"
        )
        wave_id = created["data"]["wave_id"]
        wave_dir = self.root / "docs" / "waves" / wave_id
        with tempfile.TemporaryDirectory() as outside_tmp:
            outside = Path(outside_tmp) / wave_id
            shutil.move(str(wave_dir), outside)
            before = (outside / "events.jsonl").read_bytes()
            try:
                wave_dir.symlink_to(outside, target_is_directory=True)
            except OSError as exc:
                self.skipTest(f"directory symlinks unavailable: {exc}")

            response = self.srv.wf_review_event_response(
                self.root,
                wave_id,
                "run",
                "wave-council",
                "symlink-escape",
                mode="create",
                run_kind="initial_delivery",
            )

            self.assertEqual(response["status"], "error", response)
            self.assertIn(
                "review_evidence_path_escape",
                [item["code"] for item in response["diagnostics"]],
            )
            self.assertEqual((outside / "events.jsonl").read_bytes(), before)

    def test_typed_review_approval_updates_machine_and_human_state(self):
        created = self.srv.wf_create_wave_response(
            self.root, "typed-review-approval", mode="create"
        )
        wave_id = created["data"]["wave_id"]
        self.srv.wf_review_event_response(
            self.root,
            wave_id,
            "run",
            "wave-council",
            "delivery-run",
            mode="create",
            run_kind="initial_delivery",
        )
        response = self.srv.wf_review_event_response(
            self.root,
            wave_id,
            "approval",
            "qa-reviewer",
            "qa-approval",
            mode="create",
            signoff_key="qa-reviewer",
            approval_phase="delivery",
            fresh_context=True,
            independent=True,
            integrity_checks=integrity_checks(),
            evidence={
                "observed": "public-path QA passed",
                "artifact_or_test_id": "qa:typed-review-approval",
            },
        )
        self.assertEqual(response["status"], "ok", response)
        wave_md = self.root / "docs" / "waves" / wave_id / "wave.md"
        text = wave_md.read_text(encoding="utf-8")
        self.assertIn(
            "| qa-reviewer | approved | current executed approval follows every affected repair | none |",
            text,
        )
        self.assertNotIn("- qa-reviewer: approved —", text)
        self.assertEqual(
            self.srv.lifecycle_gates._approval_evidence_diagnostics(
                text, ["qa-reviewer"], root=self.root, wave_md=_evidence_wave_md(self.srv, self.root, wave_id)
            ), []
        )

    def test_typed_review_evidence_projection_failure_is_partial_and_replayable(self):
        # Wave 1tomw (AC-3): after the ledger authority commit, an injected
        # projection replacement failure reports partial success and leaves
        # wave.md untouched; identical exact replay converges — repairing the
        # projection WITHOUT appending a duplicate event.
        created = self.srv.wf_create_wave_response(
            self.root, "typed-review-rollback", mode="create"
        )
        wave_id = created["data"]["wave_id"]
        wave_md = self.root / "docs" / "waves" / wave_id / "wave.md"
        before = wave_md.read_text(encoding="utf-8")
        events_path = sys.modules["review_evidence"].review_event_path(wave_md)
        real_replace = self.srv._atomic_replace_text

        def fail_projection(path, text, label):
            if Path(path).name == "wave.md":
                raise OSError("forced projection failure")
            return real_replace(path, text, label)

        with patch.object(self.srv, "_atomic_replace_text", side_effect=fail_projection):
            response = self.srv.wf_review_event_response(
                self.root,
                wave_id,
                "run",
                "wave-council",
                "rollback-run",
                mode="create",
                run_kind="initial_delivery",
            )
        self.assertEqual(response["status"], "partial")
        self.assertTrue(response["data"]["event_committed"])
        self.assertTrue(response["data"]["projection_stale"])
        self.assertIn(
            "review_evidence_projection_stale",
            [item["code"] for item in response["diagnostics"]],
        )
        self.assertEqual(wave_md.read_text(encoding="utf-8"), before)
        self.assertNotEqual(events_path.read_bytes(), b"")
        committed = events_path.read_bytes()
        with patch.object(
            self.srv, "_atomic_replace_text", wraps=real_replace
        ) as replay_replace:
            replay = self.srv.wf_review_event_response(
                self.root,
                wave_id,
                "run",
                "wave-council",
                "rollback-run",
                mode="create",
                run_kind="initial_delivery",
            )
        self.assertEqual(replay["status"], "ok", replay)
        self.assertTrue(replay["data"]["replayed"])
        self.assertEqual(events_path.read_bytes(), committed)
        replay_replace.assert_called_once()
        self.assertEqual(
            wave_md.read_text(encoding="utf-8"), replay_replace.call_args.args[1]
        )
        # A run-only event changes ledger history but no current finding or
        # approval state, so the simplified current-state projection may be
        # byte-identical. The replace call above is the repair oracle.
        self.assertEqual(wave_md.read_text(encoding="utf-8"), before)

    def test_typed_review_event_replay_conflict_new_context_and_concurrency(self):
        created = self.srv.wf_create_wave_response(
            self.root, "typed-review-idempotency", mode="create"
        )
        wave_id = created["data"]["wave_id"]
        def call(context, actor="qa-reviewer", signoff_key="qa-reviewer", observed="passed"):
            return self.srv.wf_review_event_response(
            self.root,
            wave_id,
            "approval",
            actor,
            context,
            mode="create",
            signoff_key=signoff_key,
            approval_phase="delivery",
            fresh_context=True,
            independent=True,
            integrity_checks=integrity_checks(),
            evidence={"observed": observed, "artifact_or_test_id": f"test:{signoff_key}"},
        )
        first = call("same-operation")
        replay = call("same-operation")
        conflict = call("same-operation", observed="different content")
        second = call("new-operation")
        self.assertEqual(first["status"], "ok", first)
        self.assertTrue(replay["data"]["replayed"])
        self.assertEqual(conflict["status"], "error", conflict)
        self.assertIn(
            "review_event_identity_conflict",
            [item["code"] for item in conflict["diagnostics"]],
        )
        self.assertFalse(second["data"]["replayed"])

        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(
                lambda args: call(*args),
                (
                    ("parallel-a", "code-reviewer", "code-reviewer"),
                    ("parallel-b", "security-reviewer", "security-reviewer"),
                ),
            ))
        self.assertEqual([item["status"] for item in results], ["ok", "ok"])
        records, errors = self.srv.read_review_event_ledger(
            self.root / created["data"]["path"]
        )
        self.assertFalse(errors)
        self.assertEqual(len(records), 4)

    def test_typed_review_multiple_findings_share_context_without_identity_collision(self):
        created = self.srv.wf_create_wave_response(
            self.root, "typed-review-multi-finding", mode="create"
        )
        wave_id = created["data"]["wave_id"]
        judgment = {
            "validation_status": "conforming",
            "scope_relation": "admitted",
            "introduced_or_worsened_by_wave": False,
            "contract_relevance": "none",
            "supported_reachability": False,
            "attacker_reachability": False,
            "authority_domain": "none",
            "authority_delta": "none",
            "observable_impact": "none",
            "containment": "preventive",
        }
        evidence = {
            "proposition": "candidate behavior conforms",
            "failure_condition": "a counterexample reaches the path",
            "public_path": "wf_review_event",
            "command_or_fixture": "multi-finding public fixture",
            "expected": "the behavior remains conforming",
            "observed": "the public fixture conformed",
            "artifact_or_test_id": "test:multi-finding",
            "known_bad_detection_method": "a known-bad control was rejected",
            "limitations": "local fixture",
            "safety_and_authorization": "local non-destructive fixture",
            "disposition_rationale": "no issue was reproduced",
        }
        for finding_id in ("finding-a", "finding-b"):
            result = self.srv.wf_review_event_response(
                self.root,
                wave_id,
                "finding",
                "qa-reviewer",
                "shared-review-context",
                mode="create",
                finding_id=finding_id,
                run_kind="initial_delivery",
                cycle=0,
                judgment=judgment,
                evidence=evidence,
                source_lanes=["qa-reviewer"],
                integrity_checks=integrity_checks(),
            )
            self.assertEqual(result["status"], "ok", result)
        records, errors = self.srv.read_review_event_ledger(
            self.root / created["data"]["path"]
        )
        self.assertFalse(errors)
        identities = [row["event_identity"] for row in records if "event_identity" in row]
        self.assertEqual({item["finding_id"] for item in identities}, {"finding-a", "finding-b"})

    def test_second_cycle_reverification_atomically_adds_convergence_checkpoint(self):
        created = self.srv.wf_create_wave_response(
            self.root, "typed-convergence", mode="create"
        )
        wave_id = created["data"]["wave_id"]
        judgment = {
            "validation_status": "real",
            "scope_relation": "admitted",
            "introduced_or_worsened_by_wave": True,
            "contract_relevance": "required_ac",
            "supported_reachability": True,
            "attacker_reachability": False,
            "authority_domain": "integrity",
            "authority_delta": "low",
            "observable_impact": "material",
            "containment": "none",
        }
        evidence = {
            "proposition": "the repair cycle closes",
            "failure_condition": "the public writer cannot append the required next state",
            "public_path": "wf_review_event",
            "command_or_fixture": "typed convergence fixture",
            "expected": "the second reverification and checkpoint commit together",
            "observed": "the public writer committed the requested transition",
            "artifact_or_test_id": "test:typed-convergence",
            "known_bad_detection_method": "without the checkpoint the second reverification fails validation",
            "limitations": "local temporary wave",
            "safety_and_authorization": "local non-destructive fixture",
            "disposition_rationale": "required lifecycle state is actionable",
        }

        def record(kind, cycle, context, blocking):
            # Wave 1tmb2: the repairing role is not the reverifying role.
            return self.srv.wf_review_event_response(
                self.root,
                wave_id,
                "finding",
                "implementer" if kind == "repair_start" else "qa-reviewer",
                context,
                mode="create",
                finding_id="convergence-finding",
                run_kind=kind,
                cycle=cycle,
                judgment=judgment,
                evidence=evidence,
                source_lanes=["qa-reviewer"],
                blocking_required_lanes=blocking,
                approval_recheck_lanes=["qa-reviewer"],
                review_boundaries_changed=[],
                fresh_context=True,
                independent=True,
                integrity_checks=integrity_checks(),
            )

        transitions = (
            ("initial_delivery", 0, "initial", ["qa-reviewer"]),
            ("repair_start", 1, "repair-1", ["qa-reviewer"]),
            ("reverification", 1, "verify-1", []),
            ("repair_start", 2, "repair-2", ["qa-reviewer"]),
            ("reverification", 2, "verify-2", []),
        )
        for transition in transitions:
            result = record(*transition)
            self.assertEqual(result["status"], "ok", result)

        records, errors = self.srv.read_review_event_ledger(
            self.root / created["data"]["path"]
        )
        self.assertFalse(errors)
        checkpoints = [
            row
            for row in records
            if row.get("record_type") == "review_run"
            and row.get("run_kind") == "convergence_checkpoint"
        ]
        self.assertEqual(len(checkpoints), 1)
        self.assertEqual(checkpoints[0]["cycle"], 2)
        self.assertEqual(checkpoints[0]["frozen_boundary"], ["convergence-finding"])

    def test_typed_multi_finding_repair_cycle_supports_progressive_lanes(self):
        created = self.srv.wf_create_wave_response(
            self.root, "typed-multi-repair-cycle", mode="create"
        )
        wave_id = created["data"]["wave_id"]
        judgment = {
            "validation_status": "real",
            "scope_relation": "admitted",
            "introduced_or_worsened_by_wave": True,
            "contract_relevance": "required_ac",
            "supported_reachability": True,
            "attacker_reachability": False,
            "authority_domain": "integrity",
            "authority_delta": "low",
            "observable_impact": "material",
            "containment": "none",
        }
        evidence = {
            "proposition": "the finding follows the shared repair cycle",
            "failure_condition": "the public writer fabricates cycles or strands a required lane",
            "public_path": "wf_review_event",
            "command_or_fixture": "five-finding progressive-lane fixture",
            "expected": "all findings share cycle one and each lane clears independently",
            "observed": "the public transition reached the requested state",
            "artifact_or_test_id": "test:multi-repair-cycle",
            "known_bad_detection_method": "the old validator rejects the second repair_start",
            "limitations": "local temporary wave",
            "safety_and_authorization": "local non-destructive fixture",
            "disposition_rationale": "required lifecycle state is actionable",
        }
        lanes = ["code-reviewer", "qa-reviewer"]

        def record(finding, kind, cycle, actor, context, blocking):
            return self.srv.wf_review_event_response(
                self.root,
                wave_id,
                "finding",
                actor,
                context,
                mode="create",
                finding_id=finding,
                run_kind=kind,
                cycle=cycle,
                judgment=judgment,
                evidence=evidence,
                source_lanes=lanes,
                blocking_required_lanes=blocking,
                approval_recheck_lanes=lanes,
                review_boundaries_changed=[],
                fresh_context=True,
                independent=True,
                integrity_checks=integrity_checks(),
            )

        findings = [f"finding-{index}" for index in range(5)]
        for finding in findings:
            result = record(
                finding, "initial_delivery", 0, "qa-reviewer",
                f"initial-{finding}", lanes,
            )
            self.assertEqual(result["status"], "ok", result)
        for finding in findings:
            result = record(
                finding, "repair_start", 1, "implementer",
                f"start-{finding}", lanes,
            )
            self.assertEqual(result["status"], "ok", result)

        replay = record(
            findings[0], "repair_start", 1, "implementer",
            f"start-{findings[0]}", lanes,
        )
        self.assertEqual(replay["status"], "ok", replay)
        self.assertTrue(replay["data"]["replayed"])
        duplicate = record(
            findings[0], "repair_start", 1, "implementer",
            "conflicting-second-start", lanes,
        )
        self.assertEqual(duplicate["status"], "error", duplicate)
        self.assertIn(
            "more than one repair_start",
            "\n".join(item["message"] for item in duplicate["diagnostics"]),
        )

        for finding in findings:
            first_lane = record(
                finding, "reverification", 1, "code-reviewer",
                f"verify-code-{finding}", ["qa-reviewer"],
            )
            self.assertEqual(first_lane["status"], "ok", first_lane)
            if finding != findings[-1]:
                final_lane = record(
                    finding, "reverification", 1, "qa-reviewer",
                    f"verify-qa-{finding}", [],
                )
                self.assertEqual(final_lane["status"], "ok", final_lane)

        premature = record(
            findings[0], "repair_start", 2, "implementer",
            "premature-cycle-two", lanes,
        )
        self.assertEqual(premature["status"], "error", premature)
        self.assertIn(
            "starts before cycle 1 completes",
            "\n".join(item["message"] for item in premature["diagnostics"]),
        )
        final_lane = record(
            findings[-1], "reverification", 1, "qa-reviewer",
            f"verify-qa-{findings[-1]}", [],
        )
        self.assertEqual(final_lane["status"], "ok", final_lane)

        records, errors = self.srv.read_review_event_ledger(
            self.root / created["data"]["path"]
        )
        self.assertFalse(errors)
        syntheses = [
            row for row in records if row.get("record_type") == "finding_synthesis"
        ]
        superseded = {
            row["supersedes_record_id"]
            for row in syntheses
            if row.get("supersedes_record_id")
        }
        heads = {
            row["finding_id"]: row
            for row in syntheses
            if row["record_id"] not in superseded
        }
        self.assertEqual(set(heads), set(findings))
        self.assertTrue(all(row["cycle"] == 1 for row in heads.values()))
        self.assertTrue(
            all(row["repair_execution_state"] == "completed" for row in heads.values())
        )
        self.assertTrue(
            all(row["blocking_required_lanes"] == [] for row in heads.values())
        )

    def test_lane_clearing_errors_carry_state_derived_recovery_guidance(self):
        """Wave 1tbw4: both lane-clearing diagnostics route the caller to the
        state-derived recipe (list, one blocking lane as actor, current list
        minus that actor) instead of leaving a bare rule statement."""
        created = self.srv.wf_create_wave_response(
            self.root, "typed-lane-recovery", mode="create"
        )
        wave_id = created["data"]["wave_id"]
        judgment = {
            "validation_status": "real",
            "scope_relation": "admitted",
            "introduced_or_worsened_by_wave": True,
            "contract_relevance": "required_ac",
            "supported_reachability": True,
            "attacker_reachability": False,
            "authority_domain": "integrity",
            "authority_delta": "low",
            "observable_impact": "material",
            "containment": "none",
        }
        evidence = {
            "proposition": "the lane-clearing diagnostics carry recovery guidance",
            "failure_condition": "a bare rule statement without a recovery route",
            "public_path": "wf_review_event",
            "command_or_fixture": "two-lane fixture with an invalid clear-both attempt",
            "expected": "the error names the list-first per-lane recipe",
            "observed": "the public transition reached the requested state",
            "artifact_or_test_id": "test:lane-recovery-guidance",
            "known_bad_detection_method": "the pre-1tbw4 messages lacked recovery text",
            "limitations": "local temporary wave",
            "safety_and_authorization": "local non-destructive fixture",
            "disposition_rationale": "required lifecycle state is actionable",
        }
        lanes = ["code-reviewer", "qa-reviewer"]

        def record(kind, cycle, actor, context, blocking):
            return self.srv.wf_review_event_response(
                self.root,
                wave_id,
                "finding",
                actor,
                context,
                mode="create",
                finding_id="recovery-finding",
                run_kind=kind,
                cycle=cycle,
                judgment=judgment,
                evidence=evidence,
                source_lanes=lanes,
                blocking_required_lanes=blocking,
                approval_recheck_lanes=lanes,
                review_boundaries_changed=[],
                fresh_context=True,
                independent=True,
                integrity_checks=integrity_checks(),
            )

        self.assertEqual(record("initial_delivery", 0, "qa-reviewer", "rg-init", lanes)["status"], "ok")
        self.assertEqual(record("repair_start", 1, "implementer", "rg-start", lanes)["status"], "ok")

        # Builder diagnostic: clearing both lanes in one event is rejected with
        # the state-derived recovery text.
        both = record("reverification", 1, "qa-reviewer", "rg-clear-both", [])
        self.assertEqual(both["status"], "error", both)
        messages = "\n".join(item["message"] for item in both["diagnostics"])
        self.assertIn("wf_review_wave", messages)
        self.assertNotIn('event="list"', messages)

        # Closure diagnostic: an unresolved-lanes head reports the same
        # recovery text at closure validation.
        wave_md = self.root / created["data"]["path"]
        closure = self.srv.validate_external_review_evidence(wave_md, closure=True)
        closure_errors = "\n".join(closure.errors)
        self.assertIn("retains unresolved required lanes", closure_errors)
        self.assertIn("wf_review_wave", closure_errors)
        self.assertNotIn('event="list"', closure_errors)

    def test_typed_reverification_can_reclassify_started_finding(self):
        created = self.srv.wf_create_wave_response(
            self.root, "typed-reclassification", mode="create"
        )
        wave_id = created["data"]["wave_id"]
        actionable = {
            "validation_status": "real",
            "scope_relation": "admitted",
            "introduced_or_worsened_by_wave": True,
            "contract_relevance": "required_ac",
            "supported_reachability": True,
            "attacker_reachability": False,
            "authority_domain": "integrity",
            "authority_delta": "low",
            "observable_impact": "material",
            "containment": "none",
        }
        conforming = {
            "validation_status": "conforming",
            "scope_relation": "admitted",
            "introduced_or_worsened_by_wave": False,
            "contract_relevance": "none",
            "supported_reachability": False,
            "attacker_reachability": False,
            "authority_domain": "none",
            "authority_delta": "none",
            "observable_impact": "none",
            "containment": "preventive",
        }
        evidence = {
            "proposition": "reverification may disprove an actionable finding",
            "failure_condition": "a truthful reclassification strands the repair cycle",
            "public_path": "wf_review_event",
            "command_or_fixture": "typed reclassification fixture",
            "expected": "the not_issue head terminalizes cycle one",
            "observed": "the public transition reached the requested state",
            "artifact_or_test_id": "test:typed-reclassification",
            "known_bad_detection_method": "the old validator requires an actionable reverification row",
            "limitations": "local temporary wave",
            "safety_and_authorization": "local non-destructive fixture",
            "disposition_rationale": "fresh evidence disproved the reported behavior",
        }

        def record(kind, cycle, context, judgment, blocking):
            # Wave 1tmb2: the repairing role is not the reverifying role.
            return self.srv.wf_review_event_response(
                self.root,
                wave_id,
                "finding",
                "implementer" if kind == "repair_start" else "qa-reviewer",
                context,
                mode="create",
                finding_id="reclassified-finding",
                run_kind=kind,
                cycle=cycle,
                judgment=judgment,
                evidence=evidence,
                source_lanes=["qa-reviewer"],
                blocking_required_lanes=blocking,
                approval_recheck_lanes=["qa-reviewer"],
                review_boundaries_changed=[],
                fresh_context=True,
                independent=True,
                integrity_checks=integrity_checks(),
            )

        self.assertEqual(
            record("initial_delivery", 0, "initial", actionable, ["qa-reviewer"])["status"],
            "ok",
        )
        self.assertEqual(
            record("repair_start", 1, "start-1", actionable, ["qa-reviewer"])["status"],
            "ok",
        )
        reclassified = record("reverification", 1, "verify-1", conforming, [])
        self.assertEqual(reclassified["status"], "ok", reclassified)
        cycle_two = record(
            "repair_start", 2, "reopened-cycle-2", actionable, ["qa-reviewer"]
        )
        self.assertEqual(cycle_two["status"], "ok", cycle_two)

    def test_convergence_waits_for_final_outstanding_finding(self):
        created = self.srv.wf_create_wave_response(
            self.root, "typed-aggregate-convergence", mode="create"
        )
        wave_id = created["data"]["wave_id"]
        judgment = {
            "validation_status": "real",
            "scope_relation": "admitted",
            "introduced_or_worsened_by_wave": True,
            "contract_relevance": "required_ac",
            "supported_reachability": True,
            "attacker_reachability": False,
            "authority_domain": "integrity",
            "authority_delta": "low",
            "observable_impact": "material",
            "containment": "none",
        }
        evidence = {
            "proposition": "aggregate convergence waits for every finding",
            "failure_condition": "a checkpoint freezes a partial second cycle",
            "public_path": "wf_review_event",
            "command_or_fixture": "aggregate convergence fixture",
            "expected": "the checkpoint appears only after the final finding",
            "observed": "the requested transition committed",
            "artifact_or_test_id": "test:aggregate-convergence",
            "known_bad_detection_method": "the old builder checkpoints on the first cycle-two reverification",
            "limitations": "local temporary wave",
            "safety_and_authorization": "local non-destructive fixture",
            "disposition_rationale": "required lifecycle state is actionable",
        }

        def record(finding, kind, cycle, context, blocking):
            # Wave 1tmb2: the repairing role is not the reverifying role.
            return self.srv.wf_review_event_response(
                self.root,
                wave_id,
                "finding",
                "implementer" if kind == "repair_start" else "qa-reviewer",
                context,
                mode="create",
                finding_id=finding,
                run_kind=kind,
                cycle=cycle,
                judgment=judgment,
                evidence=evidence,
                source_lanes=["qa-reviewer"],
                blocking_required_lanes=blocking,
                approval_recheck_lanes=["qa-reviewer"],
                review_boundaries_changed=[],
                fresh_context=True,
                independent=True,
                integrity_checks=integrity_checks(),
            )

        findings = ["finding-a", "finding-b"]
        for finding in findings:
            self.assertEqual(
                record(finding, "initial_delivery", 0, f"initial-{finding}", ["qa-reviewer"])["status"],
                "ok",
            )
        for cycle in (1, 2):
            for finding in findings:
                self.assertEqual(
                    record(finding, "repair_start", cycle, f"start-{cycle}-{finding}", ["qa-reviewer"])["status"],
                    "ok",
                )
            first = record(
                findings[0], "reverification", cycle,
                f"verify-{cycle}-{findings[0]}", [],
            )
            self.assertEqual(first["status"], "ok", first)
            if cycle == 2:
                self.assertFalse(
                    any(
                        row.get("run_kind") == "convergence_checkpoint"
                        for row in first["data"]["appended_records"]
                    )
                )
            second = record(
                findings[1], "reverification", cycle,
                f"verify-{cycle}-{findings[1]}", [],
            )
            self.assertEqual(second["status"], "ok", second)

        records, errors = self.srv.read_review_event_ledger(
            self.root / created["data"]["path"]
        )
        self.assertFalse(errors)
        checkpoints = [
            row for row in records
            if row.get("record_type") == "review_run"
            and row.get("run_kind") == "convergence_checkpoint"
        ]
        self.assertEqual(len(checkpoints), 1)
        self.assertEqual(
            checkpoints[0]["frozen_boundary"],
            ["finding-a", "finding-b"],
        )

    def test_event_commit_and_projection_failure_boundaries(self):
        created = self.srv.wf_create_wave_response(
            self.root, "typed-review-faults", mode="create"
        )
        wave_id = created["data"]["wave_id"]
        wave_md = self.root / created["data"]["path"]
        events_path = wave_md.parent / "events.jsonl"
        original_replace = self.srv._atomic_replace_bytes

        def fail_event(path, payload, purpose):
            if purpose == "review-events":
                raise OSError("forced event replacement failure")
            return original_replace(path, payload, purpose)

        with patch.object(self.srv, "_atomic_replace_bytes", side_effect=fail_event):
            failed = self.srv.wf_review_event_response(
                self.root, wave_id, "run", "wave-council", "event-fail",
                mode="create", run_kind="initial_delivery",
            )
        self.assertEqual(failed["status"], "error", failed)
        self.assertEqual(events_path.read_bytes(), b"")

        original_projection = wave_md.read_text(encoding="utf-8")
        with patch.object(
            self.srv, "_atomic_replace_text", side_effect=OSError("forced projection failure")
        ):
            partial = self.srv.wf_review_event_response(
                self.root, wave_id, "run", "wave-council", "projection-fail",
                mode="create", run_kind="initial_delivery",
            )
        self.assertEqual(partial["status"], "partial", partial)
        self.assertTrue(partial["data"]["event_committed"])
        self.assertTrue(partial["data"]["projection_stale"])
        committed = events_path.read_bytes()
        self.assertEqual(wave_md.read_text(encoding="utf-8"), original_projection)
        repaired = self.srv.wf_review_event_response(
            self.root, wave_id, "run", "wave-council", "projection-fail",
            mode="create", run_kind="initial_delivery",
        )
        self.assertEqual(repaired["status"], "ok", repaired)
        self.assertTrue(repaired["data"]["replayed"])
        self.assertEqual(events_path.read_bytes(), committed)

    def test_close_requires_initial_delivery_not_readiness_only(self):
        evidence = {
            "record_type": "executable_evidence",
            "evidence_record_id": "dedup-readiness",
            "claim_id": "dedup-readiness",
            "claim_kind": "dedup",
            "required_for_approval": False,
            "phase": "readiness",
            "proposition": "readiness candidates were deduplicated",
            "counterexample_or_failure_condition": "duplicate candidate remains",
            "execution_status": "executed",
            "public_path": "wf_prepare_wave",
            "command_or_fixture": "readiness-only fixture",
            "expected": "zero duplicate candidates",
            "observed": "zero duplicate candidates",
            "artifact_or_test_id": "test_close_requires_initial_delivery",
            "adjacent_controls": [],
            "test_ran_without_unintended_skip": True,
            "public_path_reached": True,
            "boundary_values_realistic": True,
            "assertions_non_vacuous": True,
            "known_bad_detected": True,
            "known_bad_detection_method": "readiness-only close reproduction",
            "limitations": "temporary local wave",
            "safety_and_authorization": "local read-only fixture",
            "probe_class": "local_safe",
            "authorization_status": "not_required",
            "safe_boundary": False,
            "unexecuted_remainder_prohibited": False,
            "universal_claim": False,
            "verification_context": {
                "actor": "qa-reviewer",
                "context_id": "readiness-context",
                "fresh_context": True,
                "independent": True,
            },
        }
        run = {
            "record_type": "review_run",
            "review_run_id": "readiness-1",
            "run_kind": "readiness",
            "cycle": 0,
            "candidate_finding_ids": [],
            "source_record_ids": ["prepare-council"],
            "dedup_evidence_id": "dedup-readiness",
        }
        created = self.srv.wf_create_wave_response(
            self.root, "readiness-only-close", mode="create"
        )
        wave_id = created["data"]["wave_id"]
        wave_md = self.root / "docs" / "waves" / wave_id / "wave.md"
        review = sys.modules["review_evidence"]
        records = (evidence, run)
        review.review_event_path(wave_md).write_bytes(
            review.canonical_review_events_bytes(records)
        )
        wave_md.write_text(
            review.render_review_evidence_projection(
                wave_md.read_text(encoding="utf-8"), records
            ),
            encoding="utf-8",
        )
        review_response = self.srv.wf_review_wave_response(self.root, wave_id)
        self.assertTrue(
            any(
                diagnostic["code"] == "review_evidence_invalid"
                and "initial_delivery" in diagnostic["message"]
                for diagnostic in review_response.get("diagnostics", [])
            ),
            review_response,
        )
        response = self.srv.wf_close_wave_response(self.root, wave_id, mode="dry_run")
        self.assertTrue(
            any(
                diagnostic["code"] == "review_evidence_invalid"
                and "initial_delivery" in diagnostic["message"]
                for diagnostic in response.get("diagnostics", [])
            ),
            response,
        )

    def test_close_binds_operator_signoff_to_executable_approval_evidence(self):
        created = self.srv.wf_create_wave_response(
            self.root, "approval-evidence-binding", mode="create"
        )
        wave_id = created["data"]["wave_id"]
        _append_review_run(self.root, wave_id, kind="initial_delivery")
        wave_md = self.root / "docs" / "waves" / wave_id / "wave.md"
        wave_md.write_text(
            wave_md.read_text(encoding="utf-8").replace(
                "operator-signoff: <approved when operator confirms closure>",
                "operator-signoff: approved",
            ),
            encoding="utf-8",
        )

        response = self.srv.wf_close_wave_response(self.root, wave_id, mode="dry_run")

        self.assertIn(
            "missing_executable_approval_evidence",
            [item["code"] for item in response.get("diagnostics", [])],
            response,
        )

    def test_wf_prepare_wave_repairs_staged_doc_when_wave_copy_missing(self):
        self.srv.wf_add_change_response(self.root, "1200a test-wave", "1200a-feat sample", mode="create")
        wave_doc = self.root / "docs" / "waves" / "1200a test-wave" / "1200a-feat sample.md"
        staged_doc = self.root / "docs" / "plans" / "1200a-feat sample.md"
        wave_doc.rename(staged_doc)
        # Add prepare-council verdict so the council gate passes
        wave_md = self.root / "docs" / "waves" / "1200a test-wave" / "wave.md"
        wave_md.write_text(
            wave_md.read_text(encoding="utf-8")
            + f"\n## Review Checkpoints\n\n{_prepare_council_verdict_line()}\n",
            encoding="utf-8",
        )

        with patch.object(self.srv, "run_garden", return_value={"passed": True, "files_updated": 0, "updated": [], "output": ""}):
            def validate_after_repair(root):
                self.assertTrue(wave_doc.exists())
                self.assertFalse(staged_doc.exists())
                return {"passed": True, "errors": [], "warnings": [], "output": ""}

            with patch.object(self.srv, "run_validate", side_effect=validate_after_repair):
                with patch.object(self.srv, "_trigger_background_index_refresh_for_paths") as trigger:
                    result = self.srv.wf_prepare_wave_response(self.root, "1200a test-wave", mode="create")

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["data"]["repaired"], 1)
        self.assertTrue(wave_doc.exists())
        self.assertFalse(staged_doc.exists())
        trigger.assert_called_once()

    def test_wf_prepare_wave_create_regenerates_codebase_map(self):
        # Wave 1p601 AC-2b: a successful prepare (mode=create) refreshes the
        # codebase map at the prepare-wave lifecycle checkpoint, fail-safe.
        self.srv.wf_add_change_response(self.root, "1200a test-wave", "1200a-feat sample", mode="create")
        wave_md = self.root / "docs" / "waves" / "1200a test-wave" / "wave.md"
        wave_md.write_text(
            wave_md.read_text(encoding="utf-8")
            + f"\n## Review Checkpoints\n\n{_prepare_council_verdict_line()}\n",
            encoding="utf-8",
        )
        with patch.object(self.srv, "run_garden", return_value={"passed": True, "files_updated": 0, "updated": [], "output": ""}):
            with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
                with patch.object(self.srv, "_trigger_background_index_refresh_for_paths"):
                    with patch.object(self.srv, "_regenerate_codebase_map_safe", return_value=True) as regen:
                        result = self.srv.wf_prepare_wave_response(self.root, "1200a test-wave", mode="create")
        self.assertEqual(result["status"], "ok")
        regen.assert_called_once_with(self.root)

    def test_wf_prepare_wave_dry_run_does_not_regenerate_codebase_map(self):
        # Lifecycle regen fires only on the actual prepare (create), not dry_run.
        self.srv.wf_add_change_response(self.root, "1200a test-wave", "1200a-feat sample", mode="create")
        with patch.object(self.srv, "run_garden", return_value={"passed": True, "files_updated": 0, "updated": [], "output": ""}):
            with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
                with patch.object(self.srv, "_regenerate_codebase_map_safe", return_value=True) as regen:
                    self.srv.wf_prepare_wave_response(self.root, "1200a test-wave", mode="dry_run")
        regen.assert_not_called()

    def test_wf_prepare_wave_reports_duplicate_change_doc_locations(self):
        self.srv.wf_add_change_response(self.root, "1200a test-wave", "1200a-feat sample", mode="create")
        wave_doc = self.root / "docs" / "waves" / "1200a test-wave" / "1200a-feat sample.md"
        staged_doc = self.root / "docs" / "plans" / "1200a-feat sample.md"
        staged_doc.write_text(wave_doc.read_text(encoding="utf-8"), encoding="utf-8")

        with patch.object(self.srv, "run_garden", return_value={"passed": True, "files_updated": 0, "updated": [], "output": ""}):
            with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
                result = self.srv.wf_prepare_wave_response(self.root, "1200a test-wave", mode="dry_run")

        self.assertEqual(result["status"], "error")
        self.assertTrue(any(d["code"] == "duplicate_change_doc_locations" for d in result["diagnostics"]))

    def test_wf_pause_wave_writes_handoff(self):
        result = self.srv.wf_pause_wave_response(self.root, "1200a test-wave", mode="create")
        self.assertEqual(result["status"], "ok")
        handoff = self.root / "docs" / "agents" / "session-handoff.md"
        self.assertTrue(handoff.exists())

    def test_wf_pause_wave_preserves_existing_handoff_sections(self):
        handoff = self.root / "docs" / "agents" / "session-handoff.md"
        handoff.parent.mkdir(parents=True, exist_ok=True)
        handoff.write_text(
            "# Session Handoff\n\n## Notes\n\nkeep-me\n\n## Current Session\n\n**Old wave:** placeholder\n",
            encoding="utf-8",
        )
        result = self.srv.wf_pause_wave_response(self.root, "1200a test-wave", mode="create")
        self.assertEqual(result["status"], "ok")
        text = handoff.read_text(encoding="utf-8")
        self.assertIn("keep-me", text)
        self.assertIn("1200a test-wave", text)

    def test_wf_review_wave_reports_ok_when_lint_passes(self):
        wave_md = self.root / "docs" / "waves" / "1200a test-wave" / "wave.md"
        wave_md.write_text(
            wave_md.read_text(encoding="utf-8") + "\n## Review Evidence\n\n- operator-signoff: approved\n",
            encoding="utf-8",
        )
        with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
            with patch.object(self.srv, "_trigger_background_index_refresh_for_paths") as trigger:
                with patch.object(
                    self.srv.lifecycle_gates,
                    "_review_evidence_diagnostics",
                    wraps=self.srv.lifecycle_gates._review_evidence_diagnostics,
                ) as evidence_diagnostics:
                    result = self.srv.wf_review_wave_response(self.root, "1200a test-wave")
                    evidence_diagnostics.assert_called()
        self.assertEqual(result["status"], "ok")
        self.assertTrue(result["data"]["lint_passed"])
        self.assertIn("required_lanes", result["data"])
        trigger.assert_not_called()
        self.assertNotIn("persist_adoption", evidence_diagnostics.call_args.kwargs)

    def test_wf_review_wave_ok_when_signoffs_recorded(self):
        wave_md = self.root / "docs" / "waves" / "1200a test-wave" / "wave.md"
        wave_md.write_text(
            (
                "# Wave Record\n"
                "wave-id: `1200a test-wave`\n"
                "Status: active\n\n"
                "## Participants\n\n"
                "| Role | Lane | Owns |\n"
                "|------|------|------|\n"
                "| architecture-reviewer | review | `1200a-feat sample` |\n"
                "| code-reviewer | review | `1200a-feat sample` |\n\n"
                "## Review Checkpoints\n\n"
                "- prepare wave completed\n\n"
                "## Review Evidence\n\n"
                "- operator-signoff: approved\n"
                "- architecture-reviewer sign-off: approved\n"
                "- code-reviewer sign-off: approved\n"
            ),
            encoding="utf-8",
        )
        with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
            result = self.srv.wf_review_wave_response(self.root, "1200a test-wave")
        self.assertEqual(result["status"], "ok")

    def test_wf_review_wave_requires_per_lane_evidence_not_global_checkpoint(self):
        wave_md = self.root / "docs" / "waves" / "1200a test-wave" / "wave.md"
        wave_md.write_text(
            (
                "# Wave Record\n"
                "wave-id: `1200a test-wave`\n"
                "Status: active\n\n"
                "## Participants\n\n"
                "| Role | Lane | Owns |\n"
                "|------|------|------|\n"
                "| architecture-reviewer | review | `1200a-feat sample` |\n"
                "| code-reviewer | review | `1200a-feat sample` |\n\n"
                "## Review Checkpoints\n\n"
                "- Wave approved globally with one sign-off line.\n\n"
                "## Review Evidence\n\n"
                "- architecture-reviewer sign-off: approved\n"
            ),
            encoding="utf-8",
        )
        with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
            result = self.srv.wf_review_wave_response(self.root, "1200a test-wave")
        self.assertEqual(result["status"], "error")
        self.assertTrue(any(d["code"] == "missing_required_lane" for d in result["diagnostics"]))

    def test_wf_close_wave_requires_signoff_and_no_open_changes(self):
        _make_wave(self.root, "1200a test-wave", "active", [{"id": "1200a-feat sample", "status": "active"}])
        with patch.object(self.srv, "run_garden", return_value={"passed": True, "files_updated": 0, "updated": [], "output": ""}):
            with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
                result = self.srv.wf_close_wave_response(self.root, "1200a test-wave", mode="dry_run")
        self.assertEqual(result["status"], "error")
        codes = {d["code"] for d in result["diagnostics"]}
        self.assertIn("open_changes_remaining", codes)
        self.assertIn("missing_signoff_evidence", codes)

    def test_wf_close_wave_create_succeeds_when_requirements_met(self):
        wave_md = self.root / "docs" / "waves" / "1200a test-wave" / "wave.md"
        wave_md.write_text(
            (
                "# Wave Record\n"
                "wave-id: `1200a test-wave`\n"
                "Status: active\n\n"
                "## Changes\n\n"
                "Change ID: `1200a-feat sample`\n"
                "Change Status: `complete`\n\n"
                "## Review Evidence\n\n"
                "- operator-signoff: approved\n"
                "- architecture-reviewer: approved\n"
                "- code-reviewer: approved\n"
                "- qa-reviewer: approved\n"
                "- security-reviewer: approved\n"
                "- performance-reviewer: approved\n"
            ),
            encoding="utf-8",
        )
        # 1v0lx: close blocks on a missing admitted document; model it on disk.
        for cid in self.srv._CHANGE_ID_PATTERN.findall(wave_md.read_text(encoding="utf-8")):
            (wave_md.parent / f"{cid}.md").write_text(
                f"# Sample\n\nChange ID: `{cid}`\n", encoding="utf-8")
        with patch.object(self.srv, "run_garden", return_value={"passed": True, "files_updated": 0, "updated": [], "output": ""}):
            with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
                result = self.srv.wf_close_wave_response(self.root, "1200a test-wave", mode="create")
        self.assertEqual(result["status"], "ok")
        self.assertIn("Status: closed", wave_md.read_text(encoding="utf-8"))
        self.assertNotIn("archive_path", result["data"])

    def test_wf_close_wave_dry_run_fails_when_participants_missing_lane_in_evidence(self):
        wave_md = self.root / "docs" / "waves" / "1200a test-wave" / "wave.md"
        wave_md.write_text(
            (
                "# Wave Record\n"
                "wave-id: `1200a test-wave`\n"
                "Status: active\n\n"
                "## Changes\n\n"
                "Change ID: `1200a-feat sample`\n"
                "Change Status: `complete`\n\n"
                "## Participants\n\n"
                "| Role | Lane | Owns |\n"
                "|------|------|------|\n"
                "| architecture-reviewer | review | x |\n"
                "| code-reviewer | review | x |\n\n"
                "## Review Evidence\n\n"
                "- architecture-reviewer sign-off: approved\n"
            ),
            encoding="utf-8",
        )
        with patch.object(self.srv, "run_garden", return_value={"passed": True, "files_updated": 0, "updated": [], "output": ""}):
            with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
                result = self.srv.wf_close_wave_response(self.root, "1200a test-wave", mode="dry_run")
        self.assertEqual(result["status"], "error")
        self.assertTrue(any(d["code"] == "missing_required_lane" for d in result["diagnostics"]))

    def _setup_close_gate_wave(self, change_doc_text: str) -> Path:
        """Wave 1p31b (1p32k): helper for close-time gate tests.

        Writes a wave + change doc with the supplied AC/Task content; sets up sign-offs
        so other gates pass and only the close-time hard gate is in play.
        """
        wave_dir = self.root / "docs" / "waves" / "1200a test-wave"
        wave_dir.mkdir(parents=True, exist_ok=True)
        wave_md = wave_dir / "wave.md"
        wave_md.write_text(
            (
                "# Wave Record\n"
                "wave-id: `1200a test-wave`\n"
                "Status: active\n\n"
                "## Changes\n\n"
                "Change ID: `1200a-feat sample`\n"
                "Change Status: `complete`\n\n"
                "## Review Evidence\n\n"
                "- operator-signoff: approved\n"
            ),
            encoding="utf-8",
        )
        (wave_dir / "1200a-feat sample.md").write_text(change_doc_text, encoding="utf-8")
        return wave_md

    def test_close_gate_passes_when_all_ac_and_tasks_checked(self):
        """Wave 1p31b (1p32k) AC-23(a): wave with all `[x]` items closes cleanly."""
        change_doc = (
            "# Sample\n\n"
            "Change ID: `1200a-feat sample`\n"
            "Change Status: `implemented`\n\n"
            "## Rationale\n\nWhy.\n\n"
            "## Requirements\n\n1. One.\n\n"
            "## Scope\n\nIn scope.\n\n"
            "## Acceptance Criteria\n\n- [x] AC-1: First criterion met.\n- [x] AC-2: Second criterion met.\n\n"
            "## Tasks\n\n- [x] Implement first.\n- [x] Implement second.\n\n"
            "## AC Priority\n\n| AC | Priority | Rationale |\n| --- | --- | --- |\n| AC-1 | required | Core. |\n| AC-2 | important | Polish. |\n"
        )
        self._setup_close_gate_wave(change_doc)
        with patch.object(self.srv, "run_garden", return_value={"passed": True, "files_updated": 0, "updated": [], "output": ""}):
            with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
                result = self.srv.wf_close_wave_response(self.root, "1200a test-wave", mode="dry_run")
        codes = {d["code"] for d in result.get("diagnostics", [])}
        self.assertNotIn("silent_unchecked_items_at_close", codes, msg=f"diagnostics: {result.get('diagnostics')}")

    def test_close_gate_passes_with_mix_of_checked_and_tilde(self):
        """Wave 1p31b (1p32k) AC-23(b): wave with `[x]` + `[~]` items closes cleanly."""
        change_doc = (
            "# Sample\n\n"
            "Change ID: `1200a-feat sample`\n"
            "Change Status: `implemented`\n\n"
            "## Rationale\n\nWhy.\n\n"
            "## Requirements\n\n1. One.\n\n"
            "## Scope\n\nIn scope.\n\n"
            "## Acceptance Criteria\n\n"
            "- [x] AC-1: First criterion met.\n"
            "- [~] AC-2: Removed mid-implementation per operator direction. *See Decision Log entry on 2026-06-03 explaining the operator-directed removal of this AC.*\n\n"
            "## Tasks\n\n- [x] Implement first.\n- [~] Bench against synthetic fixture — covered by unit-test path.\n\n"
            "## AC Priority\n\n| AC | Priority | Rationale |\n| --- | --- | --- |\n| AC-1 | required | Core. |\n| AC-2 | required | Polish. |\n"
        )
        self._setup_close_gate_wave(change_doc)
        with patch.object(self.srv, "run_garden", return_value={"passed": True, "files_updated": 0, "updated": [], "output": ""}):
            with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
                result = self.srv.wf_close_wave_response(self.root, "1200a test-wave", mode="dry_run")
        codes = {d["code"] for d in result.get("diagnostics", [])}
        self.assertNotIn("silent_unchecked_items_at_close", codes, msg=f"diagnostics: {result.get('diagnostics')}")

    def test_close_gate_blocks_on_silent_required_ac(self):
        """Wave 1p31b (1p32k) AC-23(c): one silent `[ ]` required AC blocks close."""
        change_doc = (
            "# Sample\n\n"
            "Change ID: `1200a-feat sample`\n"
            "Change Status: `implemented`\n\n"
            "## Rationale\n\nWhy.\n\n"
            "## Requirements\n\n1. One.\n\n"
            "## Scope\n\nIn scope.\n\n"
            "## Acceptance Criteria\n\n- [x] AC-1: First criterion met.\n- [ ] AC-2: Second criterion silent at close.\n\n"
            "## Tasks\n\n- [x] Implement first.\n\n"
            "## AC Priority\n\n| AC | Priority | Rationale |\n| --- | --- | --- |\n| AC-1 | required | Core. |\n| AC-2 | required | Polish. |\n"
        )
        self._setup_close_gate_wave(change_doc)
        with patch.object(self.srv, "run_garden", return_value={"passed": True, "files_updated": 0, "updated": [], "output": ""}):
            with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
                result = self.srv.wf_close_wave_response(self.root, "1200a test-wave", mode="dry_run")
        self.assertEqual(result["status"], "error")
        gate_diags = [d for d in result["diagnostics"] if d["code"] == "silent_unchecked_items_at_close"]
        self.assertEqual(len(gate_diags), 1, msg=f"all codes: {[d['code'] for d in result['diagnostics']]}")
        self.assertIn("AC-2", gate_diags[0]["message"])
        self.assertIn("1200a-feat sample", gate_diags[0]["message"])

    def test_close_gate_blocks_on_silent_task(self):
        """Wave 1p31b (1p32k) AC-23(d): one silent `[ ]` task blocks close."""
        change_doc = (
            "# Sample\n\n"
            "Change ID: `1200a-feat sample`\n"
            "Change Status: `implemented`\n\n"
            "## Rationale\n\nWhy.\n\n"
            "## Requirements\n\n1. One.\n\n"
            "## Scope\n\nIn scope.\n\n"
            "## Acceptance Criteria\n\n- [x] AC-1: First criterion met.\n\n"
            "## Tasks\n\n- [x] Implement first.\n- [ ] Run a missing bench fixture\n\n"
            "## AC Priority\n\n| AC | Priority | Rationale |\n| --- | --- | --- |\n| AC-1 | required | Core. |\n"
        )
        self._setup_close_gate_wave(change_doc)
        with patch.object(self.srv, "run_garden", return_value={"passed": True, "files_updated": 0, "updated": [], "output": ""}):
            with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
                result = self.srv.wf_close_wave_response(self.root, "1200a test-wave", mode="dry_run")
        self.assertEqual(result["status"], "error")
        gate_diags = [d for d in result["diagnostics"] if d["code"] == "silent_unchecked_items_at_close"]
        self.assertEqual(len(gate_diags), 1)
        self.assertIn("task", gate_diags[0]["message"].lower())
        self.assertIn("missing bench fixture", gate_diags[0]["message"])

    def test_close_gate_exempts_not_this_scope_priority_ac(self):
        """Wave 1p31b (1p32k) AC-23(e): silent `[ ]` `not-this-scope` AC closes cleanly."""
        change_doc = (
            "# Sample\n\n"
            "Change ID: `1200a-feat sample`\n"
            "Change Status: `implemented`\n\n"
            "## Rationale\n\nWhy.\n\n"
            "## Requirements\n\n1. One.\n\n"
            "## Scope\n\nIn scope.\n\n"
            "## Acceptance Criteria\n\n- [x] AC-1: First criterion met.\n- [ ] AC-2: Out-of-scope-by-design criterion.\n\n"
            "## Tasks\n\n- [x] Implement first.\n\n"
            "## AC Priority\n\n| AC | Priority | Rationale |\n| --- | --- | --- |\n| AC-1 | required | Core. |\n| AC-2 | not-this-scope | Bound check. |\n"
        )
        self._setup_close_gate_wave(change_doc)
        with patch.object(self.srv, "run_garden", return_value={"passed": True, "files_updated": 0, "updated": [], "output": ""}):
            with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
                result = self.srv.wf_close_wave_response(self.root, "1200a test-wave", mode="dry_run")
        codes = {d["code"] for d in result.get("diagnostics", [])}
        self.assertNotIn("silent_unchecked_items_at_close", codes, msg=f"diagnostics: {result.get('diagnostics')}")


class FrameworkTestReceiptGateTests(unittest.TestCase):
    """Wave 1wur7 (1wuui Requirement 5, AC-3): close VERIFIES the existing receipt.

    It runs no suite and spawns no subprocess. Where ``run_tests.py`` is absent --
    every pack-vendored target repository, because ``build_pack.py`` excludes the
    runner, the tests, and the receipt -- the check is a documented no-op that
    neither blocks nor claims proof.
    """

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()
        cls.real_runner = (Path(__file__).resolve().parents[1] / "run_tests.py")

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)
        self.framework = self.root / ".wavefoundry" / "framework"
        (self.framework / "scripts").mkdir(parents=True)
        (self.framework / "scripts" / "sample_module.py").write_text("VALUE = 1\n", encoding="utf-8")
        (self.framework / "seeds").mkdir()
        (self.framework / "seeds" / "000-sample.prompt.md").write_text("# sample\n", encoding="utf-8")

    def _install_runner(self) -> None:
        # Faithful fixture: the REAL runner, so the gate and the writer share one
        # hash computation and cannot drift apart in the test either.
        shutil.copy2(self.real_runner, self.framework / "scripts" / "run_tests.py")

    def _current_hash(self) -> str:
        module = self.srv.lifecycle_gate_support._load_framework_test_runner(self.framework / "scripts" / "run_tests.py")
        self.assertIsNotNone(module)
        return module._hash_inputs()

    def _write_receipt(self, **fields) -> None:
        payload = {"inputs_hash": self._current_hash(), "ran_at": "2026-08-31T00:00:00+00:00",
                   "test_count": 7889, "result": "ok"}
        payload.update(fields)
        (self.framework / "test-cache.json").write_text(json.dumps(payload) + "\n", encoding="utf-8")

    def test_absent_runner_is_a_documented_no_op(self):
        status = self.srv.lifecycle_gates._framework_test_receipt_status(self.root)
        self.assertEqual("not_applicable", status["state"])
        self.assertIsNone(self.srv.lifecycle_gates._framework_test_receipt_diagnostic(status))
        self.assertIn("distribution excludes it", status["detail"])

    def test_green_receipt_for_the_current_tree_is_proven(self):
        self._install_runner()
        self._write_receipt()
        status = self.srv.lifecycle_gates._framework_test_receipt_status(self.root)
        self.assertEqual("proven", status["state"])
        self.assertEqual(7889, status["test_count"])
        self.assertIsNone(self.srv.lifecycle_gates._framework_test_receipt_diagnostic(status))
        self.assertIn(".wavefoundry/framework/", status["detail"])

    def test_missing_receipt_is_not_proven_and_blocks(self):
        self._install_runner()
        status = self.srv.lifecycle_gates._framework_test_receipt_status(self.root)
        self.assertEqual("missing", status["state"])
        diagnostic = self.srv.lifecycle_gates._framework_test_receipt_diagnostic(status)
        self.assertEqual("framework_test_receipt_not_proven", diagnostic["code"])
        self.assertIn("never runs a suite", diagnostic["message"])

    def test_receipt_goes_stale_when_a_framework_file_changes(self):
        self._install_runner()
        self._write_receipt()
        self.assertEqual("proven", self.srv.lifecycle_gates._framework_test_receipt_status(self.root)["state"])
        (self.framework / "scripts" / "sample_module.py").write_text("VALUE = 2\n", encoding="utf-8")
        status = self.srv.lifecycle_gates._framework_test_receipt_status(self.root)
        self.assertEqual("stale", status["state"])
        diagnostic = self.srv.lifecycle_gates._framework_test_receipt_diagnostic(status)
        self.assertEqual("framework_test_receipt_not_proven", diagnostic["code"])
        # Reverification A2: this previously asserted a phrase the round-2 rewrite
        # removed, so the rewrite left the tree red. The assertion now guards the
        # two mechanical halves the message must always carry, which is the claim
        # that actually matters rather than one turn of phrase.
        self.assertIn("hash covers `.wavefoundry/framework/` only", diagnostic["message"])
        self.assertIn("written only on a whole-suite pass", diagnostic["message"])
        self.assertIn("attests the framework code, not the tree", diagnostic["message"])

    def test_a_red_receipt_is_not_proven(self):
        self._install_runner()
        self._write_receipt(result="failed")
        self.assertEqual("not_ok", self.srv.lifecycle_gates._framework_test_receipt_status(self.root)["state"])

    def test_loading_the_runner_restores_every_import_side_effect(self):
        # Delivery review ARCH-DEL-1 / CODE-DEL-2: the first version of this test
        # asserted a TWO-effect inventory and so institutionalised the wrong one.
        # Reverification then found the corrected FOUR short as well. run_tests.py
        # mutates five pieces of interpreter state at import: sys.dont_write_bytecode,
        # the dashboard-suppression variable, a sys.path insert of its own scripts
        # dir, activate_tool_venv() prepending the tool venv's site-packages, and
        # every module the borrow registers in sys.modules.
        # A long-lived server launched against a different --root must not end up
        # resolving imports against a foreign scripts directory.
        self._install_runner()
        env_name = self.srv._RUN_TESTS_IMPORT_ENV
        runner = self.framework / "scripts" / "run_tests.py"
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop(env_name, None)
            saved_path = list(sys.path)
            sys.dont_write_bytecode = False
            try:
                self.assertIsNotNone(self.srv.lifecycle_gate_support._load_framework_test_runner(runner))
                self.assertFalse(sys.dont_write_bytecode)
                self.assertNotIn(env_name, os.environ)
                self.assertEqual(saved_path, sys.path,
                                 "sys.path must be byte-identical after the borrow")
                self.assertNotIn(str(self.framework / "scripts"), sys.path)
            finally:
                sys.path[:] = saved_path
                sys.dont_write_bytecode = True
        self.assertNotIn("wavefoundry_close_gate_run_tests", sys.modules)
        with patch.dict(os.environ, {env_name: "0"}):
            self.srv.lifecycle_gate_support._load_framework_test_runner(runner)
            self.assertEqual("0", os.environ[env_name])

    def test_the_side_effect_inventory_is_stated_consistently(self):
        """Reverification N2: the count drifted twice (two, then four) and each
        wrong value was institutionalised in prose that no test guarded, so a code
        repair ended up contradicting the documentation of that same repair. The
        prose is pinned here."""
        docstring = self.srv._load_framework_test_runner.__doc__ or ""
        self.assertIn("FIVE pieces of interpreter state", docstring)
        self.assertIn("sys.modules", docstring)
        architecture = (Path(__file__).resolve().parents[4] / "docs" / "architecture"
                        / "testing-architecture.md").read_text(encoding="utf-8")
        self.assertIn("all FIVE of the", architecture,
                      "the architecture doc must not institutionalise a stale count")
        self.assertNotIn("all FOUR of the", architecture)

    def test_the_borrow_registers_no_foreign_module(self):
        # Reverification of ARCH-DEL-1: sys.modules is a fifth side-effect
        # channel. It was safe only because server_impl happens to import the
        # same two scripts-dir modules run_tests.py does, so the foreign copies
        # were shadowed. A runner with one module-scope import of a name the
        # server does NOT import leaked that module permanently -- it kept
        # serving `import` after the foreign repository was deleted from disk.
        runner = self.framework / "scripts" / "run_tests.py"
        (self.framework / "scripts" / "wf_close_gate_probe_module.py").write_text(
            "MARKER = 'foreign'\n", encoding="utf-8")
        runner.write_text(
            "import sys\n"
            "from pathlib import Path\n"
            "sys.path.insert(0, str(Path(__file__).resolve().parent))\n"
            "import wf_close_gate_probe_module\n"
            "\n\ndef _hash_inputs():\n    return 'x'\n"
            "\n\ndef _read_cache():\n    return None\n",
            encoding="utf-8")
        saved_modules = set(sys.modules)
        saved_path = list(sys.path)
        try:
            self.assertIsNotNone(self.srv.lifecycle_gate_support._load_framework_test_runner(runner))
            self.assertNotIn("wf_close_gate_probe_module", sys.modules,
                             "the borrow must not leave a foreign module registered")
            self.assertEqual(saved_modules, set(sys.modules))
            self.assertEqual(saved_path, sys.path)
        finally:
            for name in set(sys.modules) - saved_modules:
                sys.modules.pop(name, None)
            sys.path[:] = saved_path

    def test_a_keyboard_interrupt_during_the_borrow_is_not_swallowed(self):
        # Reverification of ARCH-DEL-2: `except BaseException` also caught
        # KeyboardInterrupt, which MCP delivers on the server's main thread
        # because sync tools are dispatched inline. That cost the operator a
        # Ctrl-C and mislabelled it as a load failure. Narrowing to
        # (Exception, SystemExit) catches every escape the wave documents.
        runner = self.framework / "scripts" / "run_tests.py"
        runner.write_text("raise KeyboardInterrupt\n", encoding="utf-8")
        with self.assertRaises(KeyboardInterrupt):
            self.srv.lifecycle_gate_support._load_framework_test_runner(runner)
        runner.write_text(
            "def _hash_inputs():\n    raise KeyboardInterrupt\n"
            "\n\ndef _read_cache():\n    return None\n",
            encoding="utf-8")
        with self.assertRaises(KeyboardInterrupt):
            self.srv.lifecycle_gates._framework_test_receipt_status(self.root)
    def test_a_runner_that_exits_on_import_is_not_proven_rather_than_fatal(self):
        # ARCH-DEL-2 / CODE-DEL-1 / REL-DEL-1: activate_tool_venv() calls
        # sys.exit(2) on a venv/interpreter mismatch. SystemExit is a
        # BaseException, so `except Exception` let it terminate the tool call --
        # in exactly the case the contract calls "not proven".
        (self.framework / "scripts" / "run_tests.py").write_text(
            "import sys\nsys.exit(2)\n", encoding="utf-8")
        self.assertIsNone(
            self.srv.lifecycle_gate_support._load_framework_test_runner(self.framework / "scripts" / "run_tests.py"))
        status = self.srv.lifecycle_gates._framework_test_receipt_status(self.root)
        self.assertEqual("unreadable", status["state"])
        self.assertEqual("framework_test_receipt_not_proven",
                         self.srv.lifecycle_gates._framework_test_receipt_diagnostic(status)["code"])

    def test_a_runner_with_a_drifted_call_contract_is_not_proven(self):
        # REL-DEL-1: presence was checked, the call contract was not. An older or
        # newer runner whose _hash_inputs takes an argument raised TypeError out
        # of the tool handler instead of degrading.
        (self.framework / "scripts" / "run_tests.py").write_text(
            "def _hash_inputs(root):\n    return 'x'\n\n\ndef _read_cache():\n    return {}\n",
            encoding="utf-8")
        status = self.srv.lifecycle_gates._framework_test_receipt_status(self.root)
        self.assertEqual("unreadable", status["state"])
        self.assertIn("TypeError", status["detail"])

    def test_a_symlinked_runner_cannot_attest_a_foreign_tree(self):
        # REL-DEL-2: `is_file()` follows symlinks and the runner derives its
        # framework dir and receipt path from its own RESOLVED location, so a
        # symlink made the gate read another repository's green receipt -- a
        # false proof, the one direction a gate must never fail in.
        foreign = tempfile.TemporaryDirectory()
        self.addCleanup(foreign.cleanup)
        target = Path(foreign.name) / "run_tests.py"
        shutil.copy2(self.real_runner, target)
        link = self.framework / "scripts" / "run_tests.py"
        link.symlink_to(target)
        status = self.srv.lifecycle_gates._framework_test_receipt_status(self.root)
        self.assertEqual("unreadable", status["state"])
        self.assertIn("resolves outside this repository", status["detail"])
        self.assertIsNotNone(self.srv.lifecycle_gates._framework_test_receipt_diagnostic(status))

    def test_the_gate_spawns_no_subprocess(self):
        # AC-3 states this in words; QA-DEL-11 found it unasserted.
        self._install_runner()
        self._write_receipt()
        with patch("subprocess.run", side_effect=AssertionError("gate spawned a subprocess")):
            with patch("subprocess.Popen", side_effect=AssertionError("gate spawned a subprocess")):
                self.assertEqual("proven",
                                 self.srv.lifecycle_gates._framework_test_receipt_status(self.root)["state"])

    def test_close_response_carries_the_receipt_and_blocks_on_a_stale_one(self):
        # REL-DEL-8 / QA-DEL-2: every existing test called the helpers directly,
        # so removing the call site from wf_close_wave_response left the suite
        # green. This pins the wiring at the tool boundary.
        self._install_runner()
        self._write_receipt()
        wave_dir = self.root / "docs" / "waves" / "1200a test-wave"
        wave_dir.mkdir(parents=True)
        (wave_dir / "wave.md").write_text(
            "# Wave Record\n\nOwner: Engineering\nStatus: active\nLast verified: 2026-09-01\n"
            "wave-id: `1200a test-wave`\nTitle: Test Wave\n\n## Objective\n\nObjective.\n\n"
            "## Changes\n\n## Wave Summary\n\nSummary.\n",
            encoding="utf-8")
        with patch.object(self.srv, "run_garden", return_value={"passed": True, "files_updated": 0, "updated": [], "output": ""}):
            with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
                proven = self.srv.wf_close_wave_response(self.root, "1200a test-wave", mode="dry_run")
                self.assertEqual("proven", proven["data"]["framework_test_receipt"]["state"])
                self.assertNotIn("framework_test_receipt_not_proven",
                                 {d["code"] for d in proven.get("diagnostics", [])})
                (self.framework / "scripts" / "sample_module.py").write_text(
                    "VALUE = 2\n", encoding="utf-8")
                stale = self.srv.wf_close_wave_response(self.root, "1200a test-wave", mode="dry_run")
        self.assertEqual("error", stale["status"])
        self.assertEqual("stale", stale["data"]["framework_test_receipt"]["state"])
        self.assertIn("framework_test_receipt_not_proven",
                      {d["code"] for d in stale["diagnostics"]})


class WaveReopenTests(unittest.TestCase):
    """12eb0: wf_reopen_wave MCP tool."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        _make_repo(self.root)
        wave_dir = self.root / "docs" / "waves" / "1200a test-wave"
        wave_dir.mkdir(parents=True, exist_ok=True)
        self.wave_md = wave_dir / "wave.md"

    def tearDown(self):
        self.tmp.cleanup()

    def _write_wave(self, status: str, completed_at: bool = False) -> None:
        text = (
            "# Wave Record\n"
            "wave-id: `1200a test-wave`\n"
            f"Status: {status}\n\n"
            "## Changes\n\n"
            "Change ID: `1200a-feat sample`\n"
            "Change Status: `done`\n\n"
        )
        if completed_at:
            text += "Completed At: 2026-05-06\n\n"
        text += "## Wave Summary\n\nSome summary.\n"
        self.wave_md.write_text(text, encoding="utf-8")

    def test_reopen_closed_wave_sets_status_active(self):
        self._write_wave("closed")
        result = self.srv.wf_reopen_wave_response(self.root, "1200a test-wave")
        self.assertEqual(result["status"], "ok")
        self.assertIn("Status: active", self.wave_md.read_text(encoding="utf-8"))

    def test_reopen_removes_completed_at_stamp(self):
        self._write_wave("closed", completed_at=True)
        self.assertIn("Completed At:", self.wave_md.read_text(encoding="utf-8"))
        self.srv.wf_reopen_wave_response(self.root, "1200a test-wave")
        self.assertNotIn("Completed At:", self.wave_md.read_text(encoding="utf-8"))

    def test_reopen_paused_wave_sets_status_active(self):
        self._write_wave("paused")
        result = self.srv.wf_reopen_wave_response(self.root, "1200a test-wave")
        self.assertEqual(result["status"], "ok")
        self.assertIn("Status: active", self.wave_md.read_text(encoding="utf-8"))

    def test_reopen_non_closed_wave_returns_error(self):
        self._write_wave("active")
        result = self.srv.wf_reopen_wave_response(self.root, "1200a test-wave")
        self.assertEqual(result["status"], "error")
        self.assertTrue(any(d["code"] == "wave_not_closed" for d in result["diagnostics"]))

    def test_reopen_planned_wave_returns_error(self):
        self._write_wave("planned")
        result = self.srv.wf_reopen_wave_response(self.root, "1200a test-wave")
        self.assertEqual(result["status"], "error")
        self.assertTrue(any(d["code"] == "wave_not_closed" for d in result["diagnostics"]))

    def test_reopen_nonexistent_wave_returns_error(self):
        result = self.srv.wf_reopen_wave_response(self.root, "nonexistent-wave")
        self.assertEqual(result["status"], "error")
        self.assertTrue(any(d["code"] == "wave_not_found" for d in result["diagnostics"]))


class OperatorSignoffTests(unittest.TestCase):
    """12eb2: operator review lane required for wf_review_wave and wf_close_wave."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        _make_repo(self.root)
        wave_dir = self.root / "docs" / "waves" / "1200a test-wave"
        wave_dir.mkdir(parents=True, exist_ok=True)
        self.wave_md = wave_dir / "wave.md"

    def tearDown(self):
        self.tmp.cleanup()

    def _base_wave(self, with_operator_signoff: bool = True) -> str:
        review = "## Review Evidence\n\n"
        if with_operator_signoff:
            review += "- operator-signoff: approved\n"
        return (
            "# Wave Record\n"
            "wave-id: `1200a test-wave`\n"
            "Status: active\n\n"
            "## Changes\n\n"
            "Change ID: `1200a-feat sample`\n"
            "Change Status: `done`\n\n"
            + review
        )

    def test_wf_review_wave_fails_without_operator_signoff(self):
        self.wave_md.write_text(self._base_wave(with_operator_signoff=False), encoding="utf-8")
        with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
            result = self.srv.wf_review_wave_response(self.root, "1200a test-wave")
        self.assertEqual(result["status"], "error")
        codes = {d["code"] for d in result["diagnostics"]}
        self.assertIn("missing_operator_signoff", codes)

    def test_wf_review_wave_passes_with_operator_signoff(self):
        self.wave_md.write_text(self._base_wave(with_operator_signoff=True), encoding="utf-8")
        with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
            result = self.srv.wf_review_wave_response(self.root, "1200a test-wave")
        self.assertEqual(result["status"], "ok")

    def test_wf_review_wave_includes_operator_in_required_lanes(self):
        self.wave_md.write_text(self._base_wave(with_operator_signoff=True), encoding="utf-8")
        with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
            result = self.srv.wf_review_wave_response(self.root, "1200a test-wave")
        self.assertIn("operator", result["data"]["required_lanes"])

    def test_wf_close_wave_blocked_without_operator_signoff(self):
        self.wave_md.write_text(self._base_wave(with_operator_signoff=False), encoding="utf-8")
        with patch.object(self.srv, "run_garden", return_value={"passed": True, "files_updated": 0, "updated": [], "output": ""}):
            with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
                result = self.srv.wf_close_wave_response(self.root, "1200a test-wave", mode="dry_run")
        self.assertEqual(result["status"], "error")
        codes = {d["code"] for d in result["diagnostics"]}
        self.assertIn("missing_operator_signoff", codes)

    def _write_admitted_docs(self) -> None:
        # 1v0lx: close now blocks on a missing admitted document, so a
        # close-path fixture must model a valid wave with its docs on disk.
        text = self.wave_md.read_text(encoding="utf-8")
        for cid in self.srv._CHANGE_ID_PATTERN.findall(text):
            (self.wave_md.parent / f"{cid}.md").write_text(
                f"# Sample\n\nChange ID: `{cid}`\n", encoding="utf-8")

    def test_wf_close_wave_succeeds_with_operator_signoff(self):
        self.wave_md.write_text(self._base_wave(with_operator_signoff=True), encoding="utf-8")
        self._write_admitted_docs()
        with patch.object(self.srv, "run_garden", return_value={"passed": True, "files_updated": 0, "updated": [], "output": ""}):
            with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
                result = self.srv.wf_close_wave_response(self.root, "1200a test-wave", mode="create")
        self.assertEqual(result["status"], "ok")
        self.assertIn("Status: closed", self.wave_md.read_text(encoding="utf-8"))

    def test_wf_close_wave_create_regenerates_codebase_map(self):
        # Wave 1p601 AC-2b: a successful close (mode=create) refreshes the
        # codebase map at the close-wave lifecycle checkpoint, fail-safe.
        self.wave_md.write_text(self._base_wave(with_operator_signoff=True), encoding="utf-8")
        self._write_admitted_docs()
        with patch.object(self.srv, "run_garden", return_value={"passed": True, "files_updated": 0, "updated": [], "output": ""}):
            with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
                with patch.object(self.srv, "_regenerate_codebase_map_safe", return_value=True) as regen:
                    result = self.srv.wf_close_wave_response(self.root, "1200a test-wave", mode="create")
        self.assertEqual(result["status"], "ok")
        regen.assert_called_once_with(self.root)

    def test_wf_close_wave_dry_run_does_not_regenerate_codebase_map(self):
        # Lifecycle regen fires only on the actual close (create), not dry_run.
        self.wave_md.write_text(self._base_wave(with_operator_signoff=True), encoding="utf-8")
        with patch.object(self.srv, "run_garden", return_value={"passed": True, "files_updated": 0, "updated": [], "output": ""}):
            with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
                with patch.object(self.srv, "_regenerate_codebase_map_safe", return_value=True) as regen:
                    self.srv.wf_close_wave_response(self.root, "1200a test-wave", mode="dry_run")
        regen.assert_not_called()

    def test_regenerate_codebase_map_safe_swallows_generator_error(self):
        # Fail-safe contract: the lifecycle regen helper must never raise, even if
        # loading the generator fails — so it can never break prepare/close.
        with patch.object(self.srv, "_load_script", side_effect=RuntimeError("boom")):
            self.assertFalse(self.srv._regenerate_codebase_map_safe(self.root))

    def test_placeholder_signoff_does_not_count_as_approval(self):
        # Regression: "<approved when operator confirms closure>" contains "approved"
        # but is a template placeholder, not a real signoff.
        text = (
            "# Wave Record\n"
            "wave-id: `1200a test-wave`\n"
            "Status: active\n\n"
            "## Changes\n\n"
            "Change ID: `1200a-feat sample`\n"
            "Change Status: `done`\n\n"
            "## Review Evidence\n\n"
            "- operator-signoff: <approved when operator confirms closure>\n"
        )
        self.wave_md.write_text(text, encoding="utf-8")
        with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
            result = self.srv.wf_review_wave_response(self.root, "1200a test-wave")
        self.assertEqual(result["status"], "error")
        codes = {d["code"] for d in result["diagnostics"]}
        self.assertIn("missing_operator_signoff", codes)

    def test_placeholder_signoff_blocks_wf_close_wave(self):
        text = (
            "# Wave Record\n"
            "wave-id: `1200a test-wave`\n"
            "Status: active\n\n"
            "## Changes\n\n"
            "Change ID: `1200a-feat sample`\n"
            "Change Status: `done`\n\n"
            "## Review Evidence\n\n"
            "- operator-signoff: <approved when operator confirms closure>\n"
        )
        self.wave_md.write_text(text, encoding="utf-8")
        with patch.object(self.srv, "run_garden", return_value={"passed": True, "files_updated": 0, "updated": [], "output": ""}):
            with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
                result = self.srv.wf_close_wave_response(self.root, "1200a test-wave", mode="dry_run")
        self.assertEqual(result["status"], "error")
        codes = {d["code"] for d in result["diagnostics"]}
        self.assertIn("missing_operator_signoff", codes)


# ---------------------------------------------------------------------------
# Framework ops (mocked subprocess)
# ---------------------------------------------------------------------------

class RunValidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _run(self, returncode: int, output: str) -> dict:
        mock_result = MagicMock()
        mock_result.returncode = returncode
        mock_result.stdout = output
        mock_result.stderr = ""
        with patch("subprocess.run", return_value=mock_result):
            return self.srv.run_validate(self.root)

    def test_passed_true_on_zero_returncode(self):
        result = self._run(0, "ok\n")
        self.assertTrue(result["passed"])

    def test_passed_false_on_nonzero(self):
        result = self._run(1, "ERROR: something wrong\n")
        self.assertFalse(result["passed"])

    def test_errors_extracted(self):
        result = self._run(1, "ERROR: bad field\nWARNING: stale date\n")
        self.assertIn("ERROR: bad field", result["errors"])
        self.assertIn("WARNING: stale date", result["warnings"])

    # --- Wave 1p9iu: configurable server-side full-scan docs-lint timeout ----------------------------

    def _write_docs_lint_config(self, full_scan_timeout: object) -> None:
        (self.root / "docs").mkdir(parents=True, exist_ok=True)
        (self.root / "docs" / "workflow-config.json").write_text(
            json.dumps({"docs_lint": {"full_scan_timeout_seconds": full_scan_timeout}}),
            encoding="utf-8",
        )

    def test_full_scan_timeout_helper_config_default_and_failsafe(self):
        # AC-1: default when absent, configured value when present, default on malformed/non-positive.
        self.assertGreaterEqual(self.srv.DOCS_LINT_FULL_SCAN_TIMEOUT_DEFAULT, 120)
        self.assertEqual(
            self.srv.docs_lint_full_scan_timeout_seconds(self.root),
            self.srv.DOCS_LINT_FULL_SCAN_TIMEOUT_DEFAULT,
        )
        self._write_docs_lint_config(240)
        self.assertEqual(self.srv.docs_lint_full_scan_timeout_seconds(self.root), 240.0)
        self._write_docs_lint_config(-5)
        self.assertEqual(
            self.srv.docs_lint_full_scan_timeout_seconds(self.root),
            self.srv.DOCS_LINT_FULL_SCAN_TIMEOUT_DEFAULT,
        )
        (self.root / "docs" / "workflow-config.json").write_text("{ not json", encoding="utf-8")
        self.assertEqual(
            self.srv.docs_lint_full_scan_timeout_seconds(self.root),
            self.srv.DOCS_LINT_FULL_SCAN_TIMEOUT_DEFAULT,
        )

    def test_run_validate_forwards_configured_timeout(self):
        # AC-2: run_validate passes the resolved value as the subprocess timeout (not the old 30).
        self._write_docs_lint_config(175)
        mock_result = MagicMock(returncode=0, stdout="ok\n", stderr="")
        with patch.object(self.srv, "_mcp_subprocess_run", return_value=mock_result) as run:
            self.srv.run_validate(self.root)
        self.assertEqual(run.call_args.kwargs.get("timeout"), 175.0)
        self.assertNotEqual(run.call_args.kwargs.get("timeout"), 30)

    def test_run_validate_runs_full_scan_no_changed_flag(self):
        # AC-3: full corpus scan is preserved — the spawned argv must not include --changed.
        mock_result = MagicMock(returncode=0, stdout="ok\n", stderr="")
        with patch.object(self.srv, "_mcp_subprocess_run", return_value=mock_result) as run:
            self.srv.run_validate(self.root)
        cmd = run.call_args.args[0]
        self.assertNotIn("--changed", cmd)

    def test_run_validate_timeout_returns_legible_result(self):
        # AC-4: on TimeoutExpired, return passed:False naming the config key + elapsed, not a raise.
        self._write_docs_lint_config(61)

        def _timeout(*args, **kwargs):
            raise subprocess.TimeoutExpired(cmd="docs_lint", timeout=61)

        with patch.object(self.srv, "_mcp_subprocess_run", side_effect=_timeout):
            result = self.srv.run_validate(self.root)
        self.assertFalse(result["passed"])
        self.assertTrue(
            any("docs_lint.full_scan_timeout_seconds" in e for e in result["errors"]),
            f"timeout error must name the config key: {result['errors']}",
        )
        self.assertTrue(
            any("61" in e for e in result["errors"]),
            f"timeout error must name the elapsed timeout: {result['errors']}",
        )

    CRASH_STDERR = (
        "Traceback (most recent call last):\n"
        "  File \"docs_lint.py\", line 1, in <module>\n"
        "ValueError: sensor `ac_asserts_repository_state` is registered with unknown polarity "
        "'advisry'; expected one of ('advisory', 'blocking')\n"
    )

    def test_run_validate_synthesizes_an_error_when_lint_exits_without_a_verdict(self):
        # Wave 1wuju (delivery review QA-DEL-2): a crash (non-zero exit, no ERROR
        # line) must reach every gate as a named docs_lint_error, mirroring the
        # timeout branch; a non-zero exit WITH an ERROR line keeps its own errors.
        crashed = MagicMock(returncode=1, stdout="", stderr=self.CRASH_STDERR)
        with patch.object(self.srv, "_mcp_subprocess_run", return_value=crashed):
            result = self.srv.run_validate(self.root)
        self.assertFalse(result["passed"])
        self.assertEqual(1, len(result["errors"]), result)
        self.assertTrue(result["errors"][0].startswith(self.srv.DOCS_LINT_VERDICT_GAP_PREFIX), result)
        self.assertIn("exited 1 without a lint verdict", result["errors"][0])
        self.assertIn("'advisry'", result["errors"][0])
        self.assertIn("Traceback", result["output"])
        verdict = MagicMock(returncode=1, stdout="ERROR: docs/x.md: broken\n", stderr="")
        with patch.object(self.srv, "_mcp_subprocess_run", return_value=verdict):
            result = self.srv.run_validate(self.root)
        self.assertEqual(["ERROR: docs/x.md: broken"], result["errors"])
        clean = MagicMock(returncode=0, stdout="docs-lint: ok\n", stderr="")
        with patch.object(self.srv, "_mcp_subprocess_run", return_value=clean):
            result = self.srv.run_validate(self.root)
        self.assertTrue(result["passed"])
        self.assertEqual([], result["errors"])

    def test_the_synthesized_cause_never_leaks_the_absolute_repository_path(self):
        # Full-suite regression caught after the QA-DEL-2 repair (1uu9z contract):
        # a crash line such as a PermissionError embeds the absolute repository
        # path in its given or resolved spelling; the cause is rendered
        # repo-relative in both.
        resolved = str(self.root.resolve())
        # Both runners pass the root through (code lane final pass CODE-RV4-1:
        # the incremental site was the one pass-through with no failing test).
        for runner_name in ("run_validate", "run_validate_changed"):
            for spelled in (str(self.root), resolved):
                with self.subTest(runner=runner_name, spelling=spelled):
                    crashed = MagicMock(returncode=1, stdout="", stderr=(
                        "Traceback (most recent call last):\n"
                        f"PermissionError: [Errno 13] Permission denied: '{spelled}/docs/waves/w/c.md'\n"))
                    with patch.object(self.srv, "_mcp_subprocess_run", return_value=crashed):
                        result = getattr(self.srv, runner_name)(self.root)
                    message = result["errors"][0]
                    self.assertIn("Permission denied: 'docs/waves/w/c.md'", message)
                    self.assertNotIn(str(self.root), message)
                    self.assertNotIn(resolved, message)

    def test_run_validate_changed_synthesizes_the_same_error(self):
        # The incremental sibling feeds the post-write attachment; a crash there
        # must count as an error, not as checked-and-clean with zero errors.
        crashed = MagicMock(returncode=1, stdout="", stderr=self.CRASH_STDERR)
        with patch.object(self.srv, "_mcp_subprocess_run", return_value=crashed):
            result = self.srv.run_validate_changed(self.root)
        self.assertFalse(result["passed"])
        self.assertEqual(1, len(result["errors"]), result)
        self.assertIn("without a lint verdict", result["errors"][0])

    def test_the_sanitizer_ignores_a_filesystem_root_or_relative_spelling(self):
        # Wave 1wybs (1wybr AC-1; readiness RT-RDY-4): a root spelling that is its
        # own parent would rewrite every separator, and a relative spelling would
        # delete a bare segment wherever it occurs; both leave the line byte-identical.
        cause = "PermissionError: [Errno 13] Permission denied: '/Users/x/repo/docs/waves/w/c.md'"
        for spelling in (Path("/"), Path("repo"), Path("."), Path("docs")):
            with self.subTest(root=str(spelling)):
                self.assertEqual(cause, self.srv._strip_repository_root(cause, spelling))
        # A real root is still stripped in its given and resolved spellings.
        for spelled in (str(self.root), str(self.root.resolve())):
            with self.subTest(spelling=spelled):
                line = f"PermissionError: [Errno 13] Permission denied: '{spelled}/docs/w.md'"
                self.assertEqual(
                    "PermissionError: [Errno 13] Permission denied: 'docs/w.md'",
                    self.srv._strip_repository_root(line, self.root),
                )

    def test_the_gap_producer_requires_the_root(self):
        # Wave 1wybs (1wybr AC-1): a caller that forgets the root cannot leak the path.
        with self.assertRaises(TypeError):
            self.srv._docs_lint_verdict_gap_error(1, "boom")  # type: ignore[call-arg]

    def test_a_long_cause_keeps_its_head_and_tail(self):
        # Wave 1wybs (1wybr AC-2; readiness RT-RDY-7): the cap retains the exception
        # class and the quoted detail around a marker, after the root is stripped;
        # a cause under the cap is unchanged.
        cap = self.srv.DOCS_LINT_VERDICT_GAP_CAUSE_CAP
        self.assertGreaterEqual(cap, 240)
        filler = "x" * (cap * 2)
        long_line = f"PermissionError: [Errno 13] {filler} Permission denied: '{self.root}/docs/w.md'"
        crashed = MagicMock(returncode=1, stdout="", stderr="Traceback\n" + long_line + "\n")
        with patch.object(self.srv, "_mcp_subprocess_run", return_value=crashed):
            message = self.srv.run_validate(self.root)["errors"][0]
        cause = message.split("without a lint verdict; ", 1)[1]
        self.assertLessEqual(len(cause), cap)
        self.assertTrue(cause.startswith("PermissionError:"), cause)
        self.assertTrue(cause.endswith("Permission denied: 'docs/w.md'"), cause)
        self.assertIn(self.srv.DOCS_LINT_VERDICT_GAP_CAUSE_MARKER, cause)
        self.assertNotIn(str(self.root), message)
        self.assertNotIn(str(self.root.resolve()), message)
        short = MagicMock(returncode=1, stdout="", stderr=self.CRASH_STDERR)
        with patch.object(self.srv, "_mcp_subprocess_run", return_value=short):
            message = self.srv.run_validate(self.root)["errors"][0]
        self.assertTrue(message.endswith(self.CRASH_STDERR.strip().splitlines()[-1]), message)
        # Delivery review CODE-DEL-3: the exact-cap boundary is unchanged and cap+1 is
        # truncated to exactly the cap.
        marker = self.srv.DOCS_LINT_VERDICT_GAP_CAUSE_MARKER
        self.assertEqual("A" * cap, self.srv._cap_cause_line("A" * cap))
        over = self.srv._cap_cause_line("A" * (cap + 1))
        self.assertEqual(cap, len(over))
        self.assertIn(marker, over)
        # Delivery review ARCH-DEL-2: the root is stripped BEFORE the cap. With the
        # root straddling the head cut, the reversed order leaves a root fragment
        # beside the marker that assertNotIn on the whole root cannot see.
        head = (cap - len(marker)) // 2
        prefix = "PermissionError: " + "x" * (head - 20 - len("PermissionError: "))
        straddle = f"{prefix}{self.root}/docs/w.md" + " y" * 200
        crashed = MagicMock(returncode=1, stdout="", stderr="Traceback\n" + straddle + "\n")
        with patch.object(self.srv, "_mcp_subprocess_run", return_value=crashed):
            message = self.srv.run_validate(self.root)["errors"][0]
        cause = message.split("without a lint verdict; ", 1)[1]
        self.assertEqual(
            self.srv._cap_cause_line(self.srv._strip_repository_root(straddle, self.root)), cause
        )
        self.assertIn("docs/w.md", cause)
        for spelled in (str(self.root), str(self.root.resolve())):
            self.assertNotIn(spelled[:20], cause, cause)

    def test_the_sanitizer_strips_a_repr_doubled_windows_spelling(self):
        # Wave 1wybs (1wybr; delivery review DOCS-DEL-5): a Windows traceback
        # renders the path through %r, doubling every backslash; the forms-level
        # seam lets the case be pinned at string level on any platform.
        root = r"C:\Users\x\repo"
        line = "PermissionError: [Errno 13] Permission denied: %r" % (root + r"\docs\w.md")
        self.assertIn(r"C:\\Users", line)
        stripped = self.srv._strip_root_forms(line, [root])
        self.assertEqual("PermissionError: [Errno 13] Permission denied: 'docs\\\\w.md'", stripped)
        self.assertNotIn("Users", stripped)
        plain = "denied: '" + root + r"\docs\w.md'"
        self.assertEqual("denied: 'docs\\w.md'", self.srv._strip_root_forms(plain, [root]))
        self.assertEqual("denied: <repo>", self.srv._strip_root_forms("denied: " + root, [root]))


class RunGardenTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _run(self, returncode: int, output: str) -> dict:
        mock_result = MagicMock()
        mock_result.returncode = returncode
        mock_result.stdout = output
        mock_result.stderr = ""
        with patch("subprocess.run", return_value=mock_result):
            return self.srv.run_garden(self.root)

    def test_passed_true_on_zero(self):
        result = self._run(0, "")
        self.assertTrue(result["passed"])

    def test_files_updated_parses_stable_updated_lines(self):
        """Wave 1tbvo P1 repair: run_garden parses the exact
        `docs-gardener: updated <path>` contract lines — prose summaries and
        legacy 'wrote' phrasing must not count."""
        result = self._run(
            0,
            "docs-gardener: updated docs/foo.md\n"
            "docs-gardener: updated docs/bar.md\n"
            "docs-gardener: stamped 2 doc(s)\n",
        )
        self.assertEqual(result["files_updated"], 2)
        self.assertEqual(result["updated"], ["docs/foo.md", "docs/bar.md"])

    def test_summary_and_legacy_lines_do_not_count_as_updates(self):
        result = self._run(0, "docs-gardener: stamped 3 doc(s)\nWrote docs/foo.md\n")
        self.assertEqual(result["files_updated"], 0)
        self.assertEqual(result["updated"], [])

    def test_over_cap_output_parses_all_records_from_complete_stdout(self):
        """1tbvp P2 repair: contract records are parsed from the COMPLETE
        stdout — the 200k output bound applies only to the human-facing
        `output` field. Operator reproduction: 6,000 records came back as
        2,273 with a corrupted final path when parsing the bounded text."""
        paths = [f"docs/{i:05d}-{'x' * 30}.md" for i in range(6000)]
        stdout = (
            "".join(f"docs-gardener: updated {p}\n" for p in paths)
            + "docs-gardener: stamped 6000 doc(s)\n"
        )
        self.assertGreater(len(stdout), 200_000, "fixture must exceed the output bound")
        result = self._run(0, stdout)
        self.assertTrue(result["passed"])
        self.assertEqual(result["files_updated"], 6000)
        self.assertEqual(result["updated"], paths)
        self.assertTrue(all(p.endswith(".md") for p in result["updated"]))
        self.assertTrue(result.get("output_truncated"))
        self.assertLessEqual(len(result["output"]), 200_000 + 200)
        self.assertNotIn("log_path", result["output"])

    def test_no_updates_when_empty_output(self):
        result = self._run(0, "")
        self.assertEqual(result["files_updated"], 0)

    def test_integration_real_gardener_stamping_run_reports_updated_paths(self):
        """Fixtures-from-canonical-producers: run the REAL docs_gardener
        subprocess against a git fixture repo and assert run_garden sees the
        stamped file through the live output contract — this is the test
        shape that would have caught the 'wrote'-grep break."""
        subprocess.run(["git", "init"], cwd=self.root, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "t@e.st"], cwd=self.root,
            check=True, capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "test"], cwd=self.root,
            check=True, capture_output=True,
        )
        doc = self.root / "docs" / "stamped.md"
        doc.parent.mkdir(parents=True, exist_ok=True)
        doc.write_text(
            "# Doc\n\nOwner: Engineering\nStatus: active\nLast verified: 2000-01-01\n\nBody.\n",
            encoding="utf-8",
        )
        subprocess.run(["git", "add", "-A"], cwd=self.root, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "seed"], cwd=self.root,
            check=True, capture_output=True,
        )
        doc.write_text(
            doc.read_text(encoding="utf-8").replace("Body.", "Body changed."),
            encoding="utf-8",
        )
        result = self.srv.run_garden(self.root)
        self.assertTrue(result["passed"], result.get("output"))
        self.assertIn("docs/stamped.md", result["updated"])
        self.assertGreaterEqual(result["files_updated"], 1)
        self.assertNotIn("Last verified: 2000-01-01", doc.read_text(encoding="utf-8"))

    def test_integration_real_gardener_empty_run_reports_zero_updates(self):
        subprocess.run(["git", "init"], cwd=self.root, check=True, capture_output=True)
        (self.root / "docs").mkdir(parents=True, exist_ok=True)
        result = self.srv.run_garden(self.root)
        self.assertTrue(result["passed"], result.get("output"))
        self.assertEqual(result["files_updated"], 0)
        self.assertEqual(result["updated"], [])


class GardenDocsIndexRefreshTriggerTests(unittest.TestCase):
    """Wave 1tbvo P1 repair: wf_garden_docs starts the background docs-index
    refresh exactly when the gardener updated files."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _garden(self, garden_result: dict) -> tuple[dict, MagicMock]:
        with patch.object(self.srv, "run_garden", return_value=garden_result), patch.object(
            self.srv, "_trigger_background_index_refresh_for_paths"
        ) as trigger:
            result = self.srv.wf_garden_docs_response(self.root, mode="run")
        return result, trigger

    def test_stamping_run_triggers_background_index_refresh(self):
        result, trigger = self._garden(
            {"passed": True, "files_updated": 1, "updated": ["docs/a.md"], "output": ""}
        )
        self.assertEqual(result["status"], "ok")
        trigger.assert_called_once_with(self.root, ["docs/"])

    def test_empty_run_does_not_trigger_background_index_refresh(self):
        result, trigger = self._garden(
            {"passed": True, "files_updated": 0, "updated": [], "output": ""}
        )
        self.assertEqual(result["status"], "ok")
        trigger.assert_not_called()


# ---------------------------------------------------------------------------
# wf_audit
# ---------------------------------------------------------------------------

class WaveAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    # Wave 1t59p: wf_audit's index leg is the bounded metadata snapshot, not
    # docs_health(); these fixtures patch the snapshot helper accordingly.
    def _healthy_snapshot(self):
        return {
            "metadata_ready": True,
            "epoch_complete": True,
            "docs_present": True,
            "code_present": True,
            "code_sources_in_scope": True,
            "code_layer_missing": False,
            "indexed_chunker_versions": {},
            "current_chunker_version": "1",
            "chunker_version_mismatch": False,
            "readiness_overview": "ready",
            "freshness_checked": False,
            "freshness": "unknown",
            "freshness_verification_tool": "index_health",
        }

    def _absent_snapshot(self):
        return {
            **self._healthy_snapshot(),
            "metadata_ready": False,
            "epoch_complete": False,
            "docs_present": False,
            "code_present": False,
            "readiness_overview": "absent",
        }

    def _passing_validate(self):
        return {"passed": True, "errors": [], "warnings": [], "output": ""}

    def _failing_validate(self):
        return {"passed": False, "errors": ["missing Last verified"], "warnings": [], "output": ""}

    def test_healthy_state_returns_ready_true(self):
        """AC-1, AC-2: all sub-checks pass → ready=True, status ok."""
        wave_record = {
            "id": "w1",
            "status": "active",
            "changes": [],
            "title": "Wave",
            "path": "docs/waves/w1/wave.md",
        }
        with patch.object(self.srv, "current_wave", return_value=wave_record), \
             patch.object(self.srv, "run_validate", return_value=self._passing_validate()), \
             patch.object(self.srv, "_audit_index_snapshot", return_value=self._healthy_snapshot()):
            result = self.srv.wf_audit_response(self.root)
        self.assertEqual(result["status"], "ok")
        self.assertTrue(result["data"]["ready"])
        # Advisory diagnostics (e.g. harness_coverage_gap) are allowed in healthy state.
        self.assertNotIn("error", [d.get("severity") for d in result.get("diagnostics", [])])
        self.assertIn("wf_current_wave", result["next_tools"])

    def test_agent_surface_integrity_advisory_rides_the_audit_envelope(self):
        """Wave 1vgep (1vflu) AC-7: wf_audit carries the agent-surface report and, when a
        framework role is duplicated, the advisory diagnostic; a clean tree carries the
        report with zero findings and no such diagnostic. Not patched: the real audit runs
        against the fixture root."""
        wave_record = {"id": "w1", "status": "active", "changes": [], "title": "Wave", "path": ""}
        agents = self.root / "docs" / "agents"
        (agents / "specialists").mkdir(parents=True, exist_ok=True)
        header = "# {name}\n\nOwner: Engineering\nStatus: active\nRole: red-team\nCategory: specialist\n"
        (agents / "specialists" / "red-team.md").write_text(header.format(name="Red Team"), encoding="utf-8")
        with patch.object(self.srv, "current_wave", return_value=wave_record), \
             patch.object(self.srv, "run_validate", return_value=self._passing_validate()), \
             patch.object(self.srv, "_audit_index_snapshot", return_value=self._healthy_snapshot()):
            clean = self.srv.wf_audit_response(self.root)
            (agents / "red-team.md").write_text(header.format(name="Red Team (legacy)"), encoding="utf-8")
            forked = self.srv.wf_audit_response(self.root)
        self.assertTrue(clean["data"]["agent_surface_integrity"]["available"])
        self.assertEqual(clean["data"]["agent_surface_integrity"]["finding_count"], 0)
        self.assertNotIn("agent_surface_integrity_drift", [d["code"] for d in clean.get("diagnostics", [])])
        report = forked["data"]["agent_surface_integrity"]
        self.assertEqual(report["finding_count"], 1)
        [duplicate] = report["duplicate_roles"]
        self.assertEqual(duplicate["role"], "red-team")
        self.assertEqual(duplicate["canonical_path"], "docs/agents/specialists/red-team.md")
        self.assertEqual({item["path"] for item in duplicate["paths"]},
                         {"docs/agents/red-team.md", "docs/agents/specialists/red-team.md"})
        codes = [d["code"] for d in forked["diagnostics"]]
        self.assertIn("agent_surface_integrity_drift", codes)
        # advisory: the audit envelope stays ok and the wave stays ready
        self.assertEqual(forked["status"], "ok")
        # both role docs untouched by the audit
        self.assertIn("Red Team (legacy)", (agents / "red-team.md").read_text(encoding="utf-8"))

    def test_lint_fail_path(self):
        """AC-3: lint failure adds wf_validate_docs to next_tools, ready=False."""
        wave_record = {"id": "w1", "status": "active", "changes": [], "title": "Wave", "path": ""}
        with patch.object(self.srv, "current_wave", return_value=wave_record), \
             patch.object(self.srv, "run_validate", return_value=self._failing_validate()), \
             patch.object(self.srv, "_audit_index_snapshot", return_value=self._healthy_snapshot()):
            result = self.srv.wf_audit_response(self.root)
        self.assertEqual(result["status"], "ok")
        self.assertFalse(result["data"]["ready"])
        self.assertIn("wf_validate_docs", result["next_tools"])
        codes = [d["code"] for d in result["diagnostics"]]
        self.assertIn("docs_lint_error", codes)

    def _advisory_validate(self):
        return {"passed": True, "errors": [],
                "warnings": ["WARNING: docs/waves/1w test/1w-enh x.md: AC-1 asserts repository-wide state "
                             "('full framework test suite') [advisory sensor `ac_asserts_repository_state`]"],
                "output": ""}

    def test_advisory_lint_warning_is_rendered_non_blocking_at_the_audit_gate(self):
        """Wave 1wuju (1wujs AC-1): an advisory sensor's finding reaches the audit envelope
        as a `docs_lint_warning` carrying `advisory: true`, with no `docs_lint_error` and
        the wave still ready."""
        wave_record = {"id": "w1", "status": "active", "changes": [], "title": "Wave", "path": ""}
        with patch.object(self.srv, "current_wave", return_value=wave_record), \
             patch.object(self.srv, "run_validate", return_value=self._advisory_validate()), \
             patch.object(self.srv, "_audit_index_snapshot", return_value=self._healthy_snapshot()):
            result = self.srv.wf_audit_response(self.root)
        self.assertEqual(result["status"], "ok")
        self.assertTrue(result["data"]["ready"])
        warnings = [d for d in result["diagnostics"] if d["code"] == "docs_lint_warning"]
        self.assertEqual(1, len(warnings), result["diagnostics"])
        self.assertIs(True, warnings[0].get("advisory"))
        self.assertIn("asserts repository-wide state", warnings[0]["message"])
        self.assertNotIn("docs_lint_error", [d["code"] for d in result["diagnostics"]])

    def test_advisory_lint_warning_carries_the_flag_at_validate_docs(self):
        with patch.object(self.srv, "run_validate", return_value=self._advisory_validate()):
            result = self.srv.wf_validate_docs_response(self.root)
        self.assertEqual(result["status"], "ok")
        warnings = [d for d in result["diagnostics"] if d["code"] == "docs_lint_warning"]
        self.assertEqual(1, len(warnings))
        self.assertIs(True, warnings[0].get("advisory"))

    def test_index_absent_path(self):
        """AC-4: index not ready adds index_build to next_tools, ready=False."""
        wave_record = {"id": "w1", "status": "active", "changes": [], "title": "Wave", "path": ""}
        with patch.object(self.srv, "current_wave", return_value=wave_record), \
             patch.object(self.srv, "run_validate", return_value=self._passing_validate()), \
             patch.object(self.srv, "_audit_index_snapshot", return_value=self._absent_snapshot()):
            result = self.srv.wf_audit_response(self.root)
        self.assertEqual(result["status"], "ok")
        self.assertFalse(result["data"]["ready"])
        self.assertIn("index_build", result["next_tools"])
        codes = [d["code"] for d in result["diagnostics"]]
        self.assertIn("index_not_ready", codes)

    def test_no_active_wave_path(self):
        """AC-5: no wave found → wave={}, ready=False, no unhandled exception."""
        with patch.object(self.srv, "current_wave", return_value=None), \
             patch.object(self.srv, "run_validate", return_value=self._passing_validate()), \
             patch.object(self.srv, "_audit_index_snapshot", return_value=self._healthy_snapshot()):
            result = self.srv.wf_audit_response(self.root)
        self.assertEqual(result["status"], "ok")
        self.assertFalse(result["data"]["ready"])
        self.assertEqual(result["data"]["wave"], {})
        codes = [d["code"] for d in result["diagnostics"]]
        self.assertIn("no_active_wave", codes)
        self.assertIn("wf_current_wave", result["next_tools"])

    def test_no_agent_role_docs_advisory_when_agents_dir_empty(self):
        """Wave 1p35d (1p35l, AC-4, AC-5): when collect_agents returns empty,
        surface a no_agent_role_docs diagnostic with a recovery hint pointing
        at seed-050. The bare _make_repo fixture ships no agent role docs, so
        this is the natural state to exercise."""
        wave_record = {
            "id": "w1",
            "status": "active",
            "changes": [],
            "title": "Wave",
            "path": "docs/waves/w1/wave.md",
        }
        with patch.object(self.srv, "current_wave", return_value=wave_record), \
             patch.object(self.srv, "run_validate", return_value=self._passing_validate()), \
             patch.object(self.srv, "_audit_index_snapshot", return_value=self._healthy_snapshot()):
            result = self.srv.wf_audit_response(self.root)
        diag_by_code = {d["code"]: d for d in result.get("diagnostics", [])}
        self.assertIn("no_agent_role_docs", diag_by_code)
        diag = diag_by_code["no_agent_role_docs"]
        self.assertIn("seed-050", diag["message"])
        self.assertIn("seed_get", diag.get("recovery_tools", []))

    def test_no_agent_role_docs_advisory_absent_when_role_docs_present(self):
        """Wave 1p35d (1p35l, AC-4): when at least one valid role doc exists,
        the advisory must not fire."""
        agents_dir = self.root / "docs" / "agents"
        agents_dir.mkdir(parents=True, exist_ok=True)
        (agents_dir / "planner.md").write_text(
            "# Planner\n\nOwner: Engineering\nStatus: active\nRole: planner\n"
            "Category: coordinate\nLast verified: 2026-06-04\n\n## Operating Identity\n\nPlans waves.\n",
            encoding="utf-8",
        )
        wave_record = {
            "id": "w1",
            "status": "active",
            "changes": [],
            "title": "Wave",
            "path": "docs/waves/w1/wave.md",
        }
        with patch.object(self.srv, "current_wave", return_value=wave_record), \
             patch.object(self.srv, "run_validate", return_value=self._passing_validate()), \
             patch.object(self.srv, "_audit_index_snapshot", return_value=self._healthy_snapshot()):
            result = self.srv.wf_audit_response(self.root)
        codes = [d["code"] for d in result.get("diagnostics", [])]
        self.assertNotIn("no_agent_role_docs", codes)


# ---------------------------------------------------------------------------
# wf_audit bounded index snapshot (wave 1t59p / 1t59o)
# ---------------------------------------------------------------------------

class WfAuditBoundedIndexSnapshotTests(unittest.TestCase):
    """1t59o: wf_audit's index leg is a bounded metadata snapshot — it must
    never cold-load native storage or hash the working tree, and it must
    never present metadata readiness as a freshness verdict."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))
        self.index_dir = self.root / ".wavefoundry" / "index"
        self.index_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self.tmp.cleanup()

    def test_audit_trips_no_native_load_and_no_full_hash(self):
        """AC-1/AC-4 tripwire: a REAL WaveIndex with poisoned native-load and
        full-hash seams must survive wf_audit untouched."""
        idx = self.srv.WaveIndex(self.root)
        wave_record = {"id": "w1", "status": "active", "changes": [], "title": "W", "path": ""}
        with patch.object(idx, "_ensure_loaded", side_effect=AssertionError("native load")), \
             patch.object(idx, "docs_health", side_effect=AssertionError("full health")), \
             patch.object(idx, "_layer_current_hashes", side_effect=AssertionError("full hash")), \
             patch.object(self.srv, "current_wave", return_value=wave_record), \
             patch.object(self.srv, "run_validate",
                          return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
            result = self.srv.wf_audit_response(self.root, index=idx)
        self.assertEqual(result["status"], "ok")
        self.assertIn("metadata_ready", result["data"]["index"])

    def test_audit_source_has_no_native_or_hash_references(self):
        """AC-1 source pin: neither the wf_audit_response body nor the
        snapshot-helper region references the native-load path, the full-hash
        walk, or the per-file store exporter (operator P1, 1t59p cycle 1:
        export_meta_snapshot materializes every build_file_meta row —
        O(indexed files) — and its own docstring says to prefer the bounded
        read_build_summary)."""
        source = (SCRIPTS_ROOT / "server_impl.py").read_text(encoding="utf-8")
        start = source.index("def wf_audit_response")
        end = source.index("def wf_audit_install_response")
        body = source[start:end]
        for forbidden in ("docs_health", "_ensure_loaded", "_layer_current_hashes",
                          "lancedb", "export_meta_snapshot", "file_meta"):
            self.assertNotIn(forbidden, body, f"wf_audit_response references {forbidden}")
        helper_start = source.index("def _audit_build_summary")
        helper_end = source.index("@contextlib.contextmanager", helper_start)
        helper_body = source[helper_start:helper_end]
        self.assertIn("read_build_summary", helper_body)
        for forbidden in ("export_meta_snapshot", "file_meta", "docs_health",
                          "_ensure_loaded", "_layer_current_hashes", "lancedb"):
            self.assertNotIn(forbidden, helper_body, f"snapshot helper references {forbidden}")

    def test_snapshot_ready_from_metadata_only(self):
        """AC-1: completed epoch + table dirs + matching store meta → ready,
        with freshness explicitly unknown."""
        _seed_store_state(self.index_dir, {"content": ["docs"], "file_hashes": {}})
        current_cv = self.srv._read_chunker_version()
        with patch.object(self.srv, "_store_has_completed_build", return_value=True), \
             patch.object(self.srv, "_audit_build_summary", return_value={
                 "chunker_versions": {"docs": current_cv},
                 "file_count": 1,
             }):
            snap = self.srv._audit_index_snapshot(self.root, self.index_dir)
        self.assertTrue(snap["metadata_ready"])
        self.assertEqual(snap["readiness_overview"], "ready")
        self.assertFalse(snap["freshness_checked"])
        self.assertEqual(snap["freshness"], "unknown")
        self.assertEqual(snap["freshness_verification_tool"], "index_health")
        self.assertFalse(snap["chunker_version_mismatch"])

    def test_snapshot_truthful_when_not_ready(self):
        """AC-2: an absent/incomplete store is reported honestly (never
        current, never a stale claim it could not have measured)."""
        snap = self.srv._audit_index_snapshot(self.root, self.index_dir)
        self.assertFalse(snap["metadata_ready"])
        self.assertEqual(snap["readiness_overview"], "absent")
        self.assertEqual(snap["freshness"], "unknown")
        self.assertNotIn("stale_layers", snap)
        self.assertNotIn("semantic_ready", snap)

    def test_snapshot_flags_missing_code_layer_from_configuration(self):
        """AC-2: configured code prefixes with no code.lance directory → not
        ready (the 1p7is missing-layer contract, config-authority form per the
        cycle-1 repair: readiness derives from no per-file metadata)."""
        (self.index_dir / "docs.lance").mkdir()
        idx_mod = self.srv._load_script("indexer")
        with patch.object(self.srv, "_store_has_completed_build", return_value=True), \
             patch.object(self.srv, "_audit_build_summary", return_value={
                 "chunker_versions": {},
                 "file_count": 1,
             }), \
             patch.object(idx_mod, "_workflow_project_include_prefixes",
                          return_value={"code": ("src/",)}):
            snap = self.srv._audit_index_snapshot(self.root, self.index_dir)
        self.assertTrue(snap["code_layer_missing"])
        self.assertFalse(snap["metadata_ready"])

    def test_chunker_mismatch_reported_not_conflated_with_freshness(self):
        """AC-2: an older indexed chunker version is surfaced as its own field
        while freshness stays unknown."""
        (self.index_dir / "docs.lance").mkdir()
        with patch.object(self.srv, "_store_has_completed_build", return_value=True), \
             patch.object(self.srv, "_audit_build_summary", return_value={
                 "chunker_versions": {"docs": "0"},
                 "file_count": 1,
             }):
            snap = self.srv._audit_index_snapshot(self.root, self.index_dir)
        self.assertTrue(snap["chunker_version_mismatch"])
        self.assertEqual(snap["freshness"], "unknown")

    def test_index_health_retains_full_scan_contrast(self):
        """AC-3: explicit index_health still routes through docs_health (the
        full hash-walk verification surface is unchanged)."""
        idx = MagicMock()
        idx.docs_health.return_value = {
            "semantic_ready": True,
            "readiness_overview": "ready",
            "stale_layers": [],
            "missing_layers": [],
            "compatible_chunks": True,
            "has_any_index": True,
            "project": {"stale_paths": [], "stale_paths_count": 0},
        }
        result = self.srv.index_health_response(idx)
        idx.docs_health.assert_called_once()
        self.assertEqual(result["status"], "ok")
        source = (SCRIPTS_ROOT / "server_impl.py").read_text(encoding="utf-8")
        start = source.index("def index_health_response")
        self.assertIn("docs_health", source[start:start + 4000])


# ---------------------------------------------------------------------------
# repair/reverification independence (wave 1tmb2)
# ---------------------------------------------------------------------------

class RepairIndependenceBoundaryTests(unittest.TestCase):
    """1tmb2 AC-3/AC-4: independence rejections through the real tool
    envelope, and the close-gate audit over chains appended by older code.

    Ledgers are produced through the canonical writer; the older-code shape is
    simulated by rewriting only the verification context fields the old code
    accepted, never by hand-authoring records."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))
        created = self.srv.wf_create_wave_response(
            self.root, "independence-fixture", mode="create"
        )
        self.wave_id = created["data"]["wave_id"]
        self.wave_md = self.root / "docs" / "waves" / self.wave_id / "wave.md"
        self.re_mod = sys.modules["review_evidence"]
        self.events_path = self.re_mod.review_event_path(self.wave_md)

    def tearDown(self):
        self.tmp.cleanup()

    def _finding(self, actor, context_id, run_kind, cycle, *, finding_id="finding-ind",
                 blocking=None, fresh=True, mode="create"):
        judgment = {
            "validation_status": "real", "scope_relation": "admitted",
            "introduced_or_worsened_by_wave": True,
            "contract_relevance": "required_ac", "supported_reachability": True,
            "attacker_reachability": False, "authority_domain": "none",
            "authority_delta": "none", "observable_impact": "material",
            "containment": "preventive",
        }
        evidence = {
            "proposition": f"{finding_id} reproduces through the named path",
            "failure_condition": "public result differs from the contract",
            "public_path": "test public path",
            "command_or_fixture": "RepairIndependenceBoundaryTests",
            "expected": "contract result",
            "observed": f"{run_kind} recorded for {finding_id}",
            "artifact_or_test_id": f"test:{finding_id}-{run_kind}-{cycle}",
            "known_bad_detection_method": "focused injected old behavior",
            "limitations": "temporary local fixture only",
            "safety_and_authorization": "local disposable fixture; no external effects",
            "disposition_rationale": "real defect on a required AC; repair now",
        }
        return self.srv.wf_review_event_response(
            self.root, self.wave_id, "finding", actor, context_id,
            mode=mode, finding_id=finding_id, run_kind=run_kind, cycle=cycle,
            judgment=judgment, evidence=evidence,
            source_lanes=["qa-reviewer"],
            blocking_required_lanes=["qa-reviewer"] if blocking is None else blocking,
            approval_recheck_lanes=["qa-reviewer"],
            fresh_context=fresh, independent=True, integrity_checks=integrity_checks(),
        )

    def _snapshot(self):
        return self.events_path.read_bytes(), self.wave_md.read_bytes()

    def _assert_rejected(self, response, code, snapshot):
        self.assertEqual(response["status"], "error", response)
        codes = [d["code"] for d in response["diagnostics"]]
        self.assertIn(code, codes, codes)
        self.assertEqual(self.events_path.read_bytes(), snapshot[0],
                         "rejection must append nothing to the ledger")
        self.assertEqual(self.wave_md.read_bytes(), snapshot[1],
                         "rejection must leave the projection byte-identical")

    # ---- AC-3: both rejection codes through preview and create -------------

    def test_append_boundary_rejects_both_codes_and_appends_nothing(self):
        self.assertEqual(
            self._finding("qa-reviewer", "ctx-review", "initial_delivery", 0)["status"],
            "ok",
        )
        self.assertEqual(
            self._finding("implementer", "ctx-repair", "repair_start", 1)["status"],
            "ok",
        )
        snapshot = self._snapshot()
        for mode in ("dry_run", "create"):
            rejected = self._finding(
                "qa-reviewer", "ctx-repair", "reverification", 1,
                blocking=[], mode=mode,
            )
            self._assert_rejected(rejected, "reverification_context_not_fresh", snapshot)

        self.assertEqual(
            self._finding("qa-reviewer", "ctx-review-2", "initial_delivery", 0,
                          finding_id="finding-ind-2")["status"],
            "ok",
        )
        self.assertEqual(
            self._finding("code-reviewer", "ctx-repair-2", "repair_start", 1,
                          finding_id="finding-ind-2")["status"],
            "ok",
        )
        snapshot = self._snapshot()
        for mode in ("dry_run", "create"):
            rejected = self._finding(
                "code-reviewer", "ctx-verify-2", "reverification", 1,
                finding_id="finding-ind-2", blocking=["qa-reviewer"], mode=mode,
            )
            self._assert_rejected(rejected, "reverification_actor_not_distinct", snapshot)

        # Neither attempt silently cleared a finding: both chains stay open.
        listing = self.srv.wf_review_event_response(
            self.root, self.wave_id, "list", "probe", "list-ind"
        )
        chains = listing["data"]["chain_summary"]
        self.assertFalse(chains["finding-ind"]["terminal"])
        self.assertFalse(chains["finding-ind-2"]["terminal"])
        self.assertEqual(chains["finding-ind"]["unresolved_required_lanes"], ["qa-reviewer"])

    # ---- AC-4: close-gate audit over older-code chains ---------------------

    def _seed_older_code_chain(self, *, same_context=False):
        """Valid distinct-role chain via the tool, then rewrite the repair
        evidence's verification context into the shape old code accepted."""
        self.assertEqual(
            self._finding("qa-reviewer", "ctx-review", "initial_delivery", 0)["status"],
            "ok",
        )
        self.assertEqual(
            self._finding("implementer", "ctx-repair", "repair_start", 1)["status"],
            "ok",
        )
        self.assertEqual(
            self._finding("qa-reviewer", "ctx-verify", "reverification", 1,
                          blocking=[])["status"],
            "ok",
        )
        records, errors = self.re_mod.read_review_event_ledger(self.wave_md)
        self.assertEqual(errors, ())
        rows = [dict(row) for row in records]
        for row in rows:
            context = row.get("verification_context")
            if not isinstance(context, dict) or context.get("context_id") != "ctx-repair":
                continue
            context = dict(context)
            identity = dict(row.get("event_identity") or {})
            if same_context:
                context["context_id"] = "ctx-verify"
                if identity:
                    identity["context_id"] = "ctx-verify"
            else:
                context["actor"] = "qa-reviewer"
                if identity:
                    identity["actor"] = "qa-reviewer"
            row["verification_context"] = context
            if identity:
                row["event_identity"] = identity
        self.events_path.write_bytes(self.re_mod.canonical_review_events_bytes(rows))
        # The rewritten chain must remain valid to generic validation
        # (Requirement 4: no retroactive invalidation by parsing).
        result = self.srv.validate_external_review_evidence(self.wave_md)
        self.assertTrue(result.ok, "\n".join(result.errors))

    def _close_codes(self):
        response = self.srv.wf_close_wave_response(self.root, self.wave_id, mode="dry_run")
        return [d["code"] for d in response["diagnostics"]]

    def test_close_gate_surfaces_older_code_chain_and_recovery_clears(self):
        self._seed_older_code_chain()
        self.assertIn("review_evidence_independence_invalid", self._close_codes())
        # Recovery: a new legal repair cycle from distinct roles and contexts.
        self.assertEqual(
            self._finding("implementer", "ctx-recovery-repair", "repair_start", 2)["status"],
            "ok",
        )
        self.assertEqual(
            self._finding("qa-reviewer", "ctx-recovery-verify", "reverification", 2,
                          blocking=[])["status"],
            "ok",
        )
        self.assertNotIn("review_evidence_independence_invalid", self._close_codes())

    def test_closed_archive_with_contradictions_stays_valid_until_reopened(self):
        self._seed_older_code_chain(same_context=True)
        text = self.wave_md.read_text(encoding="utf-8")
        closed_text = text.replace("Status: planned", "Status: closed", 1)
        self.wave_md.write_text(closed_text, encoding="utf-8")
        closed_diags = self.srv.lifecycle_gates._review_evidence_diagnostics(
            closed_text, root=self.root, wave_md=_evidence_wave_md(self.srv, self.root, self.wave_id), closure=True
        )
        self.assertNotIn(
            "review_evidence_independence_invalid",
            [d["code"] for d in closed_diags],
            "sealed/closed archives are never retroactively invalidated",
        )
        # Explicit reopen makes the forward audit apply before it can close.
        reopened_text = closed_text.replace("Status: closed", "Status: active", 1)
        self.wave_md.write_text(reopened_text, encoding="utf-8")
        reopened_diags = self.srv.lifecycle_gates._review_evidence_diagnostics(
            reopened_text, root=self.root, wave_md=_evidence_wave_md(self.srv, self.root, self.wave_id), closure=True
        )
        self.assertIn(
            "review_evidence_independence_invalid",
            [d["code"] for d in reopened_diags],
        )


# ---------------------------------------------------------------------------
# wf_review_event list event (wave 1t59p / 1t6ow)
# ---------------------------------------------------------------------------

class ReviewEvidenceListEventTests(unittest.TestCase):
    """1t6ow: the read-only listing surface for the review-evidence ledger.
    Fixtures are generated through the canonical writer, never hand-authored."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))
        created = self.srv.wf_create_wave_response(self.root, "list-fixture", mode="create")
        self.wave_id = created["data"]["wave_id"]
        self.wave_md = self.root / "docs" / "waves" / self.wave_id / "wave.md"
        self.events_path = sys.modules["review_evidence"].review_event_path(self.wave_md)

    def tearDown(self):
        self.tmp.cleanup()

    def _list(self, **kwargs):
        return self.srv.wf_review_event_response(
            self.root, self.wave_id, "list", "probe", "list-test", **kwargs
        )

    def _finding_payloads(self, *, repair_state="pending"):
        judgment = {
            "validation_status": "real", "scope_relation": "admitted",
            "introduced_or_worsened_by_wave": True, "contract_relevance": "required_ac",
            "observable_impact": "low", "disposition": "do_now",
            "decision_authority": "moderator", "repair_execution_state": repair_state,
            "attacker_reachability": False, "supported_reachability": True,
            "authority_delta": "none", "authority_domain": "none", "containment": "none",
            "trust_boundary_changed": False, "architecture_or_ownership_changed": False,
            "contract_or_required_ac_semantics_changed": False,
            "cross_component_protocol_or_state_changed": False,
            "failure_or_readiness_semantics_changed": False,
            "benefit_vs_fix_risk": "unverified", "fix_risk": "unverified",
            "optional_value": "none", "rejection_basis": "none",
            "repair_safety": "unverified", "repair_scope_bounded": "unverified",
            "review_depth": "focused",
        }
        evidence = {
            "disposition_rationale": "fixture rationale", "failure_condition": "fixture fails",
            "proposition": "fixture proposition", "public_path": "fixture path",
            "command_or_fixture": "fixture command", "expected": "fixture expected",
            "observed": "fixture observed", "artifact_or_test_id": "fixture artifact",
            "known_bad_detection_method": "fixture detection", "limitations": "fixture limits",
            "safety_and_authorization": "local only",
        }
        return judgment, evidence

    def _seed_finding_chain(self, *, complete=True):
        self.srv.wf_review_event_response(
            self.root, self.wave_id, "run", "wave-council", "delivery-run",
            mode="create", run_kind="initial_delivery", cycle=0,
        )
        judgment, evidence = self._finding_payloads()
        self.srv.wf_review_event_response(
            self.root, self.wave_id, "finding", "qa-reviewer", "find-ctx",
            mode="create", finding_id="fixture-finding", run_kind="initial_delivery",
            cycle=0, judgment=judgment, evidence=evidence,
            source_lanes=["qa-reviewer"], integrity_checks=integrity_checks(),
        )
        if not complete:
            return
        judgment, evidence = self._finding_payloads()
        self.srv.wf_review_event_response(
            self.root, self.wave_id, "finding", "implementer", "repair-ctx",
            mode="create", finding_id="fixture-finding", run_kind="repair_start",
            cycle=1, judgment=judgment, evidence=evidence,
            source_lanes=["qa-reviewer"], integrity_checks=integrity_checks(),
        )
        judgment, evidence = self._finding_payloads(repair_state="completed")
        self.srv.wf_review_event_response(
            self.root, self.wave_id, "finding", "reverifier", "reverify-ctx",
            mode="create", finding_id="fixture-finding", run_kind="reverification",
            cycle=1, judgment=judgment, evidence=evidence,
            source_lanes=["qa-reviewer"], integrity_checks=integrity_checks(),
            fresh_context=True, independent=True,
        )

    def test_list_missing_ledger_is_empty_ok(self):
        """AC-1/AC-3: an absent ledger lists empty with a diagnostic, no error."""
        if self.events_path.exists():
            self.events_path.unlink()
        result = self._list()
        self.assertEqual(result["status"], "ok", result)
        self.assertEqual(result["data"]["records"], [])
        self.assertEqual(result["data"]["total_records"], 0)
        codes = [d["code"] for d in result.get("diagnostics", [])]
        self.assertIn("review_evidence_empty", codes)

    def test_list_compact_rows_summary_and_approvals(self):
        """AC-1: compact index rows, summary, and per-signoff approvals."""
        self._seed_finding_chain()
        self.srv.wf_review_event_response(
            self.root, self.wave_id, "approval", "qa-reviewer", "qa-approval",
            mode="create", signoff_key="qa-reviewer", fresh_context=True,
            approval_phase="delivery",
            independent=True, integrity_checks=integrity_checks(),
            evidence={"observed": "qa pass", "artifact_or_test_id": "qa:list"},
        )
        result = self._list()
        self.assertEqual(result["status"], "ok", result)
        data = result["data"]
        self.assertGreaterEqual(data["total_records"], 8)
        for row in data["records"]:
            self.assertTrue(row["id"], row)
            self.assertIn("record_type", row)
        self.assertEqual(data["summary"]["findings"], 1)
        qa = [r for r in data["approvals"] if r["signoff_key"] == "qa-reviewer"]
        self.assertEqual(len(qa), 1)
        self.assertEqual(qa[0]["state"], "approved")

    def test_chain_summary_terminal_and_pending_match_gate_derivation(self):
        """AC-2: terminal after completed reverification; pending before it;
        composed from the gate's own current_synthesis_heads (source-pinned)."""
        self._seed_finding_chain(complete=False)
        pending = self._list()["data"]["chain_summary"]["fixture-finding"]
        self.assertFalse(pending["terminal"])
        self.assertEqual(pending["repair_execution_state"], "pending")
        self._seed_finding_chain_completion()
        done = self._list()["data"]["chain_summary"]["fixture-finding"]
        self.assertTrue(done["terminal"])
        self.assertEqual(done["repair_execution_state"], "completed")
        self.assertEqual(done["unresolved_required_lanes"], [])
        records = self.srv.validate_external_review_evidence(self.wave_md).records
        heads = sys.modules["review_evidence"].current_synthesis_heads(records)
        self.assertEqual(done["head_record_id"], heads["fixture-finding"]["record_id"])
        source = (SCRIPTS_ROOT / "server_impl.py").read_text(encoding="utf-8")
        start = source.index("def _review_evidence_list_response")
        end = source.index("def wf_review_event_response")
        body = source[start:end]
        self.assertIn("review_authority_projection", body)
        self.assertNotIn("current_synthesis_heads(", body)
        self.assertNotIn("review_status_rows(", body)
        self.assertNotIn("supersedes_record_id\"] ==", body)

    def _seed_finding_chain_completion(self):
        judgment, evidence = self._finding_payloads()
        self.srv.wf_review_event_response(
            self.root, self.wave_id, "finding", "implementer", "repair-ctx",
            mode="create", finding_id="fixture-finding", run_kind="repair_start",
            cycle=1, judgment=judgment, evidence=evidence,
            source_lanes=["qa-reviewer"], integrity_checks=integrity_checks(),
        )
        judgment, evidence = self._finding_payloads(repair_state="completed")
        self.srv.wf_review_event_response(
            self.root, self.wave_id, "finding", "reverifier", "reverify-ctx",
            mode="create", finding_id="fixture-finding", run_kind="reverification",
            cycle=1, judgment=judgment, evidence=evidence,
            source_lanes=["qa-reviewer"], integrity_checks=integrity_checks(),
            fresh_context=True, independent=True,
        )

    def test_list_is_read_only_and_lock_free(self):
        """AC-3: byte-identical ledger, and the write lock is never entered."""
        self._seed_finding_chain()
        before = self.events_path.read_bytes()
        with patch.object(self.srv, "project_state_publication_lock",
                          side_effect=AssertionError("write lock taken on list")):
            result = self._list()
        self.assertEqual(result["status"], "ok", result)
        self.assertEqual(self.events_path.read_bytes(), before)

    def test_list_filters_and_truncation(self):
        """AC-1: finding/record_type filters; capped output keeps the tail
        with an explicit named-total truncation marker."""
        self._seed_finding_chain()
        by_finding = self._list(finding_id="fixture-finding", record_type="finding_synthesis")
        ids = [r["id"] for r in by_finding["data"]["records"]]
        self.assertTrue(ids)
        self.assertTrue(all(i.startswith("syn-fixture-finding") for i in ids), ids)
        with patch.object(self.srv, "REVIEW_EVIDENCE_LIST_CAP", 2):
            capped = self._list()
        self.assertTrue(capped["data"]["truncated"])
        self.assertEqual(len(capped["data"]["records"]), 2)
        codes = [d["code"] for d in capped.get("diagnostics", [])]
        self.assertIn("review_evidence_list_truncated", codes)
        marker = next(d for d in capped["diagnostics"] if d["code"] == "review_evidence_list_truncated")
        self.assertIn(str(capped["data"]["total_records"]), marker["message"])

    def test_list_ignores_mode_and_never_validates_write_fields(self):
        """AC-1: mode is ignored for list; no judgment/evidence demanded."""
        result = self.srv.wf_review_event_response(
            self.root, self.wave_id, "list", "probe", "list-test", mode="bogus"
        )
        self.assertEqual(result["status"], "ok", result)

    def test_guided_action_cap_has_named_forensic_diagnostic(self):
        judgment, evidence = self._finding_payloads()
        for index in range(3):
            response = self.srv.wf_review_event_response(
                self.root, self.wave_id, "finding", "qa-reviewer", f"cap-{index}",
                mode="create", finding_id=f"cap-finding-{index}",
                run_kind="initial_delivery", cycle=0, judgment=judgment,
                evidence=evidence, source_lanes=["qa-reviewer"],
                blocking_required_lanes=["qa-reviewer"],
                approval_recheck_lanes=["qa-reviewer"],
                review_boundaries_changed=[], integrity_checks=integrity_checks(),
            )
            self.assertEqual(response["status"], "ok", response)
        review_evidence = sys.modules["review_evidence"]
        with patch.object(review_evidence, "REVIEW_ACTION_CAP", 2), patch.object(
            self.srv, "run_validate",
            return_value={"passed": True, "errors": [], "warnings": [], "output": ""},
        ):
            reviewed = self.srv.wf_review_wave_response(
                self.root, self.wave_id, phase="implementation"
            )
        actions = reviewed["data"]["review_actions"]
        self.assertEqual(actions["total_current_actions"], 3)
        self.assertEqual(actions["returned_current_actions"], 2)
        self.assertEqual(actions["omitted_current_actions"], 1)
        self.assertTrue(actions["truncated"])
        diagnostic = next(
            item for item in reviewed["diagnostics"]
            if item["code"] == review_evidence.REVIEW_ACTION_TRUNCATED_DIAGNOSTIC
        )
        self.assertIn("wf_review_event(event='list')", diagnostic["message"])

    def test_approval_actions_require_the_phase_run_and_preserve_public_actor_contract(self):
        """AC-1/AC-9: approval guidance begins only after the phase run.

        The mutation probe crosses the registered public response seam: if the
        product projection emits the wrong operator actor, the oracle must fail.
        """
        validate_ok = {"passed": True, "errors": [], "warnings": [], "output": ""}
        with patch.object(self.srv, "run_validate", return_value=validate_ok):
            before = self.srv.wf_review_wave_response(
                self.root, self.wave_id, phase="implementation"
            )
        self.assertEqual(
            before["data"]["review_actions"]["next_actions"], [], before
        )

        recorded = self.srv.wf_review_event_response(
            self.root, self.wave_id, "run", "wave-council", "delivery-run",
            mode="create", run_kind="initial_delivery", cycle=0,
        )
        self.assertEqual(recorded["status"], "ok", recorded)

        def assert_operator_actor(response):
            action = next(
                item for item in response["data"]["review_actions"]["next_actions"]
                if item["action_id"] == "approval:operator-signoff"
            )
            self.assertEqual(action["actor_role"], "operator")

        with patch.object(self.srv, "run_validate", return_value=validate_ok):
            after = self.srv.wf_review_wave_response(
                self.root, self.wave_id, phase="implementation"
            )
        assert_operator_actor(after)

        original_projection = self.srv.review_authority_projection

        def wrong_operator_actor(*args, **kwargs):
            projection = json.loads(json.dumps(original_projection(*args, **kwargs)))
            for action in projection["next_actions"]:
                if action["action_id"] == "approval:operator-signoff":
                    action["actor_role"] = "wave-council"
            recommended = projection.get("recommended_next_action")
            if recommended and recommended["action_id"] == "approval:operator-signoff":
                recommended["actor_role"] = "wave-council"
            return projection

        with patch.object(self.srv, "run_validate", return_value=validate_ok), \
             patch.object(self.srv, "review_authority_projection", wrong_operator_actor):
            mutated = self.srv.wf_review_wave_response(
                self.root, self.wave_id, phase="implementation"
            )
        with self.assertRaises(AssertionError):
            assert_operator_actor(mutated)

    def test_zero_lane_finding_has_a_terminal_guided_route(self):
        """AC-2: accepted historical zero-lane heads cannot loop forever."""
        judgment, evidence = self._finding_payloads()
        initial = self.srv.wf_review_event_response(
            self.root, self.wave_id, "finding", "implementer", "zero-initial",
            mode="create", finding_id="zero-lane", run_kind="initial_delivery",
            cycle=0, judgment=judgment, evidence=evidence,
            source_lanes=["implementer"], blocking_required_lanes=[],
            integrity_checks=integrity_checks(),
        )
        self.assertEqual(initial["status"], "ok", initial)
        repair = initial["data"]["review_actions"]["recommended_next_action"]
        self.assertEqual(repair["action_kind"], "repair_start", repair)

        repair_state = dict(repair["state_args"])
        repair_event = repair_state.pop("event")
        repaired = self.srv.wf_review_event_response(
            self.root, self.wave_id, repair_event, repair["actor_role"], "zero-repair",
            mode="create", judgment=judgment, evidence=evidence,
            integrity_checks=integrity_checks(), **repair_state,
        )
        self.assertEqual(repaired["status"], "ok", repaired)
        reverify = repaired["data"]["review_actions"]["recommended_next_action"]
        self.assertEqual(reverify["action_kind"], "reverification", reverify)
        self.assertEqual(reverify["actor_role"], "code-reviewer", reverify)
        self.assertEqual(reverify["state_args"]["blocking_required_lanes"], [])

        completed_judgment, completed_evidence = self._finding_payloads(
            repair_state="completed"
        )
        reverify_state = dict(reverify["state_args"])
        reverify_event = reverify_state.pop("event")
        verified = self.srv.wf_review_event_response(
            self.root, self.wave_id, reverify_event, reverify["actor_role"],
            "zero-reverify", mode="create", judgment=completed_judgment,
            evidence=completed_evidence, fresh_context=True, independent=True,
            integrity_checks=integrity_checks(), **reverify_state,
        )
        self.assertEqual(verified["status"], "ok", verified)
        summary = self._list(finding_id="zero-lane")["data"]["chain_summary"]["zero-lane"]
        self.assertTrue(summary["terminal"], summary)
        self.assertEqual(summary["unresolved_required_lanes"], [])
        self.assertTrue(
            any(
                action["action_kind"] == "approval"
                for action in verified["data"]["review_actions"]["next_actions"]
            ),
            verified,
        )

    def test_zero_lane_fallback_excludes_the_actual_repair_actor(self):
        """AC-2: accepted same-role repairs still get a distinct terminal route."""
        cases = (
            ("qa-reviewer", "qa-reviewer", "code-reviewer"),
            ("implementer", "code-reviewer", "qa-reviewer"),
        )
        for source_actor, repair_actor, expected_reviewer in cases:
            with self.subTest(
                source_actor=source_actor, repair_actor=repair_actor
            ), tempfile.TemporaryDirectory() as tmp:
                root = _make_repo(Path(tmp))
                created = self.srv.wf_create_wave_response(
                    root, f"zero-{source_actor}-{repair_actor}", mode="create"
                )
                wave_id = created["data"]["wave_id"]
                judgment, evidence = self._finding_payloads()
                initial = self.srv.wf_review_event_response(
                    root, wave_id, "finding", source_actor, "variant-initial",
                    mode="create", finding_id="zero-variant",
                    run_kind="initial_delivery", cycle=0, judgment=judgment,
                    evidence=evidence, source_lanes=[source_actor],
                    blocking_required_lanes=[], integrity_checks=integrity_checks(),
                )
                self.assertEqual(initial["status"], "ok", initial)
                repaired = self.srv.wf_review_event_response(
                    root, wave_id, "finding", repair_actor, "variant-repair",
                    mode="create", finding_id="zero-variant",
                    run_kind="repair_start", cycle=1, judgment=judgment,
                    evidence=evidence, source_lanes=[source_actor],
                    blocking_required_lanes=[], integrity_checks=integrity_checks(),
                )
                self.assertEqual(repaired["status"], "ok", repaired)
                action = repaired["data"]["review_actions"]["recommended_next_action"]
                self.assertEqual(action["actor_role"], expected_reviewer, action)
                state = dict(action["state_args"])
                event = state.pop("event")
                completed, completed_evidence = self._finding_payloads(
                    repair_state="completed"
                )
                verified = self.srv.wf_review_event_response(
                    root, wave_id, event, action["actor_role"], "variant-reverify",
                    mode="create", judgment=completed, evidence=completed_evidence,
                    fresh_context=True, independent=True,
                    integrity_checks=integrity_checks(), **state,
                )
                self.assertEqual(verified["status"], "ok", verified)
                listed = self.srv.wf_review_event_response(
                    root, wave_id, "list", "probe", "variant-list",
                    finding_id="zero-variant",
                )
                self.assertTrue(
                    listed["data"]["chain_summary"]["zero-variant"]["terminal"],
                    listed,
                )

    def test_repair_start_rejects_actor_blocking_lane_overlap_without_append(self):
        """A repair actor can never independently clear its own reviewer lane."""

        for lanes in (["qa-reviewer"], ["qa-reviewer", "code-reviewer"]):
            with self.subTest(lanes=lanes), tempfile.TemporaryDirectory() as tmp:
                root = _make_repo(Path(tmp))
                created = self.srv.wf_create_wave_response(
                    root, "repair-actor-overlap", mode="create"
                )
                wave_id = created["data"]["wave_id"]
                wave_md = root / "docs" / "waves" / wave_id / "wave.md"
                events_path = sys.modules["review_evidence"].review_event_path(wave_md)
                judgment, evidence = self._finding_payloads()
                initial = self.srv.wf_review_event_response(
                    root, wave_id, "finding", "qa-reviewer", "overlap-initial",
                    mode="create", finding_id="actor-overlap",
                    run_kind="initial_delivery", cycle=0, judgment=judgment,
                    evidence=evidence, source_lanes=lanes,
                    blocking_required_lanes=lanes,
                    approval_recheck_lanes=lanes,
                    integrity_checks=integrity_checks(),
                )
                self.assertEqual(initial["status"], "ok", initial)
                before = events_path.read_bytes()
                rejected = self.srv.wf_review_event_response(
                    root, wave_id, "finding", "qa-reviewer", "overlap-repair",
                    mode="create", finding_id="actor-overlap",
                    run_kind="repair_start", cycle=1, judgment=judgment,
                    evidence=evidence, source_lanes=lanes,
                    blocking_required_lanes=lanes,
                    approval_recheck_lanes=lanes,
                    integrity_checks=integrity_checks(),
                )
                self.assertEqual(rejected["status"], "error", rejected)
                self.assertEqual(events_path.read_bytes(), before)
                diagnostic = next(
                    item for item in rejected["diagnostics"]
                    if "repair_start actor" in item["message"]
                )
                self.assertEqual(diagnostic["code"], "invalid_review_event")
                self.assertEqual(diagnostic["recovery_tools"], ["wf_review_wave"])
                self.assertIn("phase='implementation'", diagnostic["recovery_usage"])

    def test_stale_lane_action_cannot_resurrect_a_cleared_lane(self):
        """AC-9: old legal alternatives reject with zero append."""

        judgment, evidence = self._finding_payloads()
        lanes = ["code-reviewer", "qa-reviewer"]
        initial = self.srv.wf_review_event_response(
            self.root, self.wave_id, "finding", "qa-reviewer", "stale-initial",
            mode="create", finding_id="stale-lanes", run_kind="initial_delivery",
            cycle=0, judgment=judgment, evidence=evidence, source_lanes=lanes,
            blocking_required_lanes=lanes, approval_recheck_lanes=lanes,
            integrity_checks=integrity_checks(),
        )
        self.assertEqual(initial["status"], "ok", initial)
        repair = initial["data"]["review_actions"]["recommended_next_action"]
        repair_state = dict(repair["state_args"])
        repair_event = repair_state.pop("event")
        repaired = self.srv.wf_review_event_response(
            self.root, self.wave_id, repair_event, repair["actor_role"],
            "stale-repair", mode="create", judgment=judgment,
            evidence=evidence, integrity_checks=integrity_checks(), **repair_state,
        )
        self.assertEqual(repaired["status"], "ok", repaired)
        actions = repaired["data"]["review_actions"]["next_actions"]
        code_action = next(
            action for action in actions if action["actor_role"] == "code-reviewer"
        )
        stale_qa_action = next(
            action for action in actions if action["actor_role"] == "qa-reviewer"
        )

        code_state = dict(code_action["state_args"])
        code_event = code_state.pop("event")
        completed, completed_evidence = self._finding_payloads(
            repair_state="completed"
        )
        cleared = self.srv.wf_review_event_response(
            self.root, self.wave_id, code_event, code_action["actor_role"],
            "stale-code-clear", mode="create", judgment=completed,
            evidence=completed_evidence, fresh_context=True, independent=True,
            integrity_checks=integrity_checks(), **code_state,
        )
        self.assertEqual(cleared["status"], "ok", cleared)
        before = self.events_path.read_bytes()

        stale_state = dict(stale_qa_action["state_args"])
        stale_event = stale_state.pop("event")
        rejected = self.srv.wf_review_event_response(
            self.root, self.wave_id, stale_event, stale_qa_action["actor_role"],
            "stale-qa-replay", mode="create", judgment=completed,
            evidence=completed_evidence, fresh_context=True, independent=True,
            integrity_checks=integrity_checks(), **stale_state,
        )
        self.assertEqual(rejected["status"], "error", rejected)
        self.assertEqual(self.events_path.read_bytes(), before)
        diagnostic = next(
            item for item in rejected["diagnostics"]
            if "stale reverification" in item["message"]
        )
        self.assertEqual(diagnostic["code"], "invalid_review_event")
        self.assertEqual(diagnostic["recovery_tools"], ["wf_review_wave"])
        current = self._list(finding_id="stale-lanes")
        self.assertEqual(
            current["data"]["chain_summary"]["stale-lanes"]
            ["unresolved_required_lanes"],
            ["qa-reviewer"],
        )

    def test_guided_single_lane_stale_approval_and_operator_shapes(self):
        """AC-3/AC-9: the remaining promised evaluation shapes are executable.

        One validation enters the guided flow. A current operator approval is
        then made stale by a new single-lane finding; the accepted write
        continuations repair, independently reverify, and refresh approval
        without an exploratory rejection or forensic-list navigation step.
        """
        run = self.srv.wf_review_event_response(
            self.root, self.wave_id, "run", "wave-council", "shape-run",
            mode="create", run_kind="initial_delivery", cycle=0,
        )
        self.assertEqual(run["status"], "ok", run)
        validate_ok = {"passed": True, "errors": [], "warnings": [], "output": ""}
        with patch.object(self.srv, "run_validate", return_value=validate_ok) as validate:
            reviewed = self.srv.wf_review_wave_response(
                self.root, self.wave_id, phase="implementation"
            )
        self.assertEqual(validate.call_count, 1)
        operator = reviewed["data"]["review_actions"]["recommended_next_action"]
        self.assertEqual(operator["action_id"], "approval:operator-signoff", operator)
        approved = self.srv.wf_review_event_response(
            self.root, self.wave_id, "approval", operator["actor_role"], "shape-approval",
            mode="create", signoff_key="operator-signoff", approval_phase="delivery",
            integrity_checks=integrity_checks(),
            evidence={"observed": "operator approved", "artifact_or_test_id": "shape"},
        )
        self.assertEqual(approved["status"], "ok", approved)

        judgment, evidence = self._finding_payloads()
        found = self.srv.wf_review_event_response(
            self.root, self.wave_id, "finding", "qa-reviewer", "shape-finding",
            mode="create", finding_id="single-lane-shape",
            run_kind="initial_delivery", cycle=0, judgment=judgment,
            evidence=evidence, source_lanes=["qa-reviewer"],
            blocking_required_lanes=["qa-reviewer"],
            approval_recheck_lanes=["operator-signoff"],
            integrity_checks=integrity_checks(),
        )
        self.assertEqual(found["status"], "ok", found)
        self.assertFalse(
            any(
                action["action_kind"] == "approval"
                for action in found["data"]["review_actions"]["next_actions"]
            ),
            found,
        )

        action = found["data"]["review_actions"]["recommended_next_action"]
        accepted_kinds = []
        for context in ("shape-repair", "shape-reverify"):
            state = dict(action["state_args"])
            event = state.pop("event")
            step_judgment, step_evidence = self._finding_payloads(
                repair_state=(
                    "completed"
                    if action["action_kind"] == "reverification"
                    else "pending"
                )
            )
            written = self.srv.wf_review_event_response(
                self.root, self.wave_id, event, action["actor_role"], context,
                mode="create", judgment=step_judgment, evidence=step_evidence,
                fresh_context=action["action_kind"] == "reverification",
                independent=action["action_kind"] == "reverification",
                integrity_checks=integrity_checks(), **state,
            )
            self.assertEqual(written["status"], "ok", written)
            accepted_kinds.append(action["action_kind"])
            action = written["data"]["review_actions"]["recommended_next_action"]

        self.assertEqual(accepted_kinds, ["repair_start", "reverification"])
        self.assertEqual(action["action_id"], "approval:operator-signoff", action)
        refreshed = self.srv.wf_review_event_response(
            self.root, self.wave_id, "approval", action["actor_role"], "shape-refresh",
            mode="create", signoff_key="operator-signoff", approval_phase="delivery",
            integrity_checks=integrity_checks(),
            evidence={"observed": "operator re-approved", "artifact_or_test_id": "shape"},
        )
        self.assertEqual(refreshed["status"], "ok", refreshed)
        operator_row = next(
            row for row in self._list()["data"]["approvals"]
            if row["signoff_key"] == "operator-signoff"
        )
        self.assertEqual(operator_row["state"], "approved", operator_row)

    def test_frozen_single_lane_stale_approval_operator_equivalence(self):
        """AC-9: the remaining three named shapes get the same fair oracle."""

        generated_wave_id = self.wave_id
        fixed_wave_id = "1200b ergonomics-single-lane"
        fixed_dir = self.wave_md.parent.parent / fixed_wave_id
        self.wave_md.parent.rename(fixed_dir)
        self.wave_id = fixed_wave_id
        self.wave_md = fixed_dir / "wave.md"
        self.wave_md.write_text(
            self.wave_md.read_text(encoding="utf-8").replace(
                generated_wave_id, fixed_wave_id
            ),
            encoding="utf-8",
        )
        self.events_path = sys.modules["review_evidence"].review_event_path(
            self.wave_md
        )

        run = self.srv.wf_review_event_response(
            self.root, self.wave_id, "run", "wave-council", "frozen-shape-run",
            mode="create", run_kind="initial_delivery", cycle=0,
        )
        self.assertEqual(run["status"], "ok", run)
        old_approval = self.srv.wf_review_event_response(
            self.root, self.wave_id, "approval", "operator", "frozen-old-approval",
            mode="create", signoff_key="operator-signoff",
            approval_phase="delivery", integrity_checks=integrity_checks(),
            evidence={
                "observed": "operator approved before the finding",
                "artifact_or_test_id": "frozen-single-lane",
            },
        )
        self.assertEqual(old_approval["status"], "ok", old_approval)
        judgment, evidence = self._finding_payloads()
        found = self.srv.wf_review_event_response(
            self.root, self.wave_id, "finding", "qa-reviewer", "frozen-finding",
            mode="create", finding_id="frozen-single-lane",
            run_kind="initial_delivery", cycle=0, judgment=judgment,
            evidence=evidence, source_lanes=["qa-reviewer"],
            blocking_required_lanes=["qa-reviewer"],
            approval_recheck_lanes=["operator-signoff"],
            integrity_checks=integrity_checks(),
        )
        self.assertEqual(found["status"], "ok", found)
        starting_bytes = self.events_path.read_bytes()
        starting_fingerprint = hashlib.sha256(starting_bytes).hexdigest()
        self.assertEqual(
            starting_fingerprint,
            "e3592ff07b5e48f80705a5570b27c9d16a735ad4754523197c530f2e607a81fa",
        )

        candidate_tmp = tempfile.TemporaryDirectory()
        self.addCleanup(candidate_tmp.cleanup)
        candidate_root = Path(candidate_tmp.name) / "candidate"
        shutil.copytree(self.root, candidate_root)
        candidate_events = candidate_root / self.events_path.relative_to(self.root)
        self.assertEqual(candidate_events.read_bytes(), starting_bytes)

        validate_ok = {"passed": True, "errors": [], "warnings": [], "output": ""}
        baseline_trace = []
        with patch.object(self.srv, "run_validate", return_value=validate_ok) as baseline_validate:
            reviewed = self.srv.wf_review_wave_response(
                self.root, self.wave_id, phase="implementation"
            )
            baseline_trace.append("wf_review_wave")
            self.assertIn(reviewed["status"], {"ok", "error"})
            for context, kind, actor, lanes, repair_state in (
                ("frozen-repair", "repair_start", "implementer", ["qa-reviewer"], "pending"),
                ("frozen-reverify", "reverification", "qa-reviewer", [], "completed"),
            ):
                listed = self._list(finding_id="frozen-single-lane")
                self.assertEqual(listed["status"], "ok", listed)
                baseline_trace.append("wf_review_event:list")
                step_judgment, step_evidence = self._finding_payloads(
                    repair_state=repair_state
                )
                written = self.srv.wf_review_event_response(
                    self.root, self.wave_id, "finding", actor, context,
                    mode="create", finding_id="frozen-single-lane",
                    run_kind=kind, cycle=1, judgment=step_judgment,
                    evidence=step_evidence, source_lanes=["qa-reviewer"],
                    blocking_required_lanes=lanes,
                    approval_recheck_lanes=["operator-signoff"],
                    fresh_context=kind == "reverification",
                    independent=kind == "reverification",
                    integrity_checks=integrity_checks(),
                )
                self.assertEqual(written["status"], "ok", written)
                baseline_trace.append(f"wf_review_event:{kind}")
            listed = self._list(finding_id="frozen-single-lane")
            self.assertTrue(
                listed["data"]["chain_summary"]["frozen-single-lane"]["terminal"]
            )
            baseline_trace.append("wf_review_event:list")
            refreshed = self.srv.wf_review_event_response(
                self.root, self.wave_id, "approval", "operator",
                "frozen-operator-refresh", mode="create",
                signoff_key="operator-signoff", approval_phase="delivery",
                integrity_checks=integrity_checks(),
                evidence={
                    "observed": "operator refreshed after repair",
                    "artifact_or_test_id": "frozen-single-lane",
                },
            )
            self.assertEqual(refreshed["status"], "ok", refreshed)
            baseline_trace.append("wf_review_event:approval")

        candidate_trace = []
        with patch.object(self.srv, "run_validate", return_value=validate_ok) as candidate_validate:
            reviewed = self.srv.wf_review_wave_response(
                candidate_root, self.wave_id, phase="implementation"
            )
            candidate_trace.append("wf_review_wave")
            action = reviewed["data"]["review_actions"]["recommended_next_action"]
            for context in (
                "frozen-repair", "frozen-reverify", "frozen-operator-refresh"
            ):
                state = dict(action["state_args"])
                event_name = state.pop("event")
                kwargs = {
                    "mode": "create",
                    "integrity_checks": integrity_checks(),
                    **state,
                }
                if action["action_kind"] in {"repair_start", "reverification"}:
                    step_judgment, step_evidence = self._finding_payloads(
                        repair_state=(
                            "completed"
                            if action["action_kind"] == "reverification"
                            else "pending"
                        )
                    )
                    kwargs.update(
                        judgment=step_judgment,
                        evidence=step_evidence,
                        fresh_context=action["action_kind"] == "reverification",
                        independent=action["action_kind"] == "reverification",
                    )
                else:
                    kwargs["evidence"] = {
                        "observed": "operator refreshed after repair",
                        "artifact_or_test_id": "frozen-single-lane",
                    }
                written = self.srv.wf_review_event_response(
                    candidate_root, self.wave_id, event_name,
                    action["actor_role"], context, **kwargs,
                )
                self.assertEqual(written["status"], "ok", written)
                candidate_trace.append(f"wf_review_event:{action['action_kind']}")
                action = written["data"]["review_actions"].get(
                    "recommended_next_action"
                )
                if action is None:
                    break

        self.assertEqual(baseline_validate.call_count, 1)
        self.assertEqual(candidate_validate.call_count, 1)
        self.assertNotIn("wf_review_event:list", candidate_trace)
        self.assertLess(len(candidate_trace), len(baseline_trace))
        self.assertEqual(candidate_events.read_bytes(), self.events_path.read_bytes())
        baseline_records = self.srv.validate_external_review_evidence(
            self.wave_md
        ).records
        candidate_wave = candidate_root / self.wave_md.relative_to(self.root)
        candidate_records = self.srv.validate_external_review_evidence(
            candidate_wave
        ).records
        review_evidence = sys.modules["review_evidence"]
        self.assertEqual(
            review_evidence.current_synthesis_heads(candidate_records),
            review_evidence.current_synthesis_heads(baseline_records),
        )
        self.assertEqual(
            review_evidence.review_status_rows(
                candidate_records, ("qa-reviewer", "operator-signoff")
            ),
            review_evidence.review_status_rows(
                baseline_records, ("qa-reviewer", "operator-signoff")
            ),
        )

    def test_frozen_invalid_transition_matrix_rejects_without_append(self):
        """AC-9: every named invalid transition is a frozen twin-tree oracle."""

        judgment, evidence = self._finding_payloads()
        initial = self.srv.wf_review_event_response(
            self.root, self.wave_id, "finding", "qa-reviewer", "matrix-initial",
            mode="create", finding_id="matrix-finding",
            run_kind="initial_delivery", cycle=0, judgment=judgment,
            evidence=evidence, source_lanes=["code-reviewer", "qa-reviewer"],
            blocking_required_lanes=["code-reviewer", "qa-reviewer"],
            approval_recheck_lanes=["code-reviewer", "qa-reviewer"],
            integrity_checks=integrity_checks(),
        )
        self.assertEqual(initial["status"], "ok", initial)

        def twin_roots(label):
            holder = tempfile.TemporaryDirectory()
            self.addCleanup(holder.cleanup)
            baseline = Path(holder.name) / f"{label}-baseline"
            candidate = Path(holder.name) / f"{label}-candidate"
            shutil.copytree(self.root, baseline)
            shutil.copytree(self.root, candidate)
            return baseline, candidate

        def assert_rejected_twins(label, invoke):
            baseline, candidate = twin_roots(label)
            signatures = []
            for root in (baseline, candidate):
                events_path = root / self.events_path.relative_to(self.root)
                before = events_path.read_bytes()
                response = invoke(root)
                self.assertEqual(response["status"], "error", (label, response))
                self.assertEqual(events_path.read_bytes(), before, label)
                signatures.append(
                    tuple(item["code"] for item in response.get("diagnostics", []))
                )
            self.assertEqual(signatures[0], signatures[1], label)

        common = {
            "mode": "create", "finding_id": "matrix-finding",
            "judgment": judgment, "evidence": evidence,
            "source_lanes": ["code-reviewer", "qa-reviewer"],
            "blocking_required_lanes": ["code-reviewer", "qa-reviewer"],
            "approval_recheck_lanes": ["code-reviewer", "qa-reviewer"],
            "integrity_checks": integrity_checks(),
        }
        assert_rejected_twins(
            "wrong-cycle",
            lambda root: self.srv.wf_review_event_response(
                root, self.wave_id, "finding", "implementer", "matrix-wrong-cycle",
                run_kind="repair_start", cycle=0, **common,
            ),
        )
        assert_rejected_twins(
            "missing-repair-start",
            lambda root: self.srv.wf_review_event_response(
                root, self.wave_id, "finding", "qa-reviewer", "matrix-no-repair",
                run_kind="reverification", cycle=1, fresh_context=True,
                independent=True, **common,
            ),
        )
        assert_rejected_twins(
            "wrong-approval-phase",
            lambda root: self.srv.wf_review_event_response(
                root, self.wave_id, "approval", "operator", "matrix-phase",
                mode="create", signoff_key="operator-signoff",
                approval_phase="readiness", integrity_checks=integrity_checks(),
                evidence={"observed": "wrong", "artifact_or_test_id": "matrix"},
            ),
        )
        assert_rejected_twins(
            "actor-swap",
            lambda root: self.srv.wf_review_event_response(
                root, self.wave_id, "approval", "wave-council", "matrix-actor",
                mode="create", signoff_key="operator-signoff",
                approval_phase="delivery", integrity_checks=integrity_checks(),
                evidence={"observed": "wrong", "artifact_or_test_id": "matrix"},
            ),
        )
        malformed = dict(common)
        malformed["integrity_checks"] = {
            "test_ran_without_unintended_skip": True
        }
        assert_rejected_twins(
            "malformed-integrity",
            lambda root: self.srv.wf_review_event_response(
                root, self.wave_id, "finding", "implementer", "matrix-integrity",
                run_kind="repair_start", cycle=1, **malformed,
            ),
        )

        def assert_same_context_rejected(root):
            repaired = self.srv.wf_review_event_response(
                root, self.wave_id, "finding", "implementer", "matrix-same-context",
                run_kind="repair_start", cycle=1, **common,
            )
            self.assertEqual(repaired["status"], "ok", repaired)
            events_path = root / self.events_path.relative_to(self.root)
            before = events_path.read_bytes()
            response = self.srv.wf_review_event_response(
                root, self.wave_id, "finding", "qa-reviewer", "matrix-same-context",
                run_kind="reverification", cycle=1, fresh_context=True,
                independent=True, **common,
            )
            self.assertEqual(events_path.read_bytes(), before)
            return response

        same_context_signatures = []
        for root in twin_roots("same-context"):
            response = assert_same_context_rejected(root)
            self.assertEqual(response["status"], "error", response)
            same_context_signatures.append(
                tuple(item["code"] for item in response.get("diagnostics", []))
            )
        self.assertEqual(same_context_signatures[0], same_context_signatures[1])

        def assert_stale_lane_rejected(root):
            repaired = self.srv.wf_review_event_response(
                root, self.wave_id, "finding", "implementer", "matrix-stale-repair",
                run_kind="repair_start", cycle=1, **common,
            )
            self.assertEqual(repaired["status"], "ok", repaired)
            actions = repaired["data"]["review_actions"]["next_actions"]
            code_action = next(
                action for action in actions
                if action["actor_role"] == "code-reviewer"
            )
            stale_qa_action = next(
                action for action in actions
                if action["actor_role"] == "qa-reviewer"
            )
            completed, completed_evidence = self._finding_payloads(
                repair_state="completed"
            )
            code_state = dict(code_action["state_args"])
            code_event = code_state.pop("event")
            cleared = self.srv.wf_review_event_response(
                root, self.wave_id, code_event, code_action["actor_role"],
                "matrix-stale-code", mode="create", judgment=completed,
                evidence=completed_evidence, fresh_context=True, independent=True,
                integrity_checks=integrity_checks(), **code_state,
            )
            self.assertEqual(cleared["status"], "ok", cleared)
            events_path = root / self.events_path.relative_to(self.root)
            before = events_path.read_bytes()
            stale_state = dict(stale_qa_action["state_args"])
            stale_event = stale_state.pop("event")
            response = self.srv.wf_review_event_response(
                root, self.wave_id, stale_event, stale_qa_action["actor_role"],
                "matrix-stale-qa", mode="create", judgment=completed,
                evidence=completed_evidence, fresh_context=True, independent=True,
                integrity_checks=integrity_checks(), **stale_state,
            )
            self.assertEqual(events_path.read_bytes(), before)
            return response

        stale_lane_signatures = []
        for root in twin_roots("stale-lane"):
            response = assert_stale_lane_rejected(root)
            self.assertEqual(response["status"], "error", response)
            stale_lane_signatures.append(
                tuple(item["code"] for item in response.get("diagnostics", []))
            )
        self.assertEqual(stale_lane_signatures[0], stale_lane_signatures[1])

    def test_action_cap_bounds_legal_alternatives_to_returned_actions(self):
        """AC-6: omitted actions cannot survive quadratically in alternatives."""
        judgment, evidence = self._finding_payloads()
        lanes = [f"lane-{index}" for index in range(8)]
        initial = self.srv.wf_review_event_response(
            self.root, self.wave_id, "finding", "qa-reviewer", "cap-initial",
            mode="create", finding_id="wide-finding", run_kind="initial_delivery",
            cycle=0, judgment=judgment, evidence=evidence,
            source_lanes=lanes, blocking_required_lanes=lanes,
            approval_recheck_lanes=lanes, integrity_checks=integrity_checks(),
        )
        self.assertEqual(initial["status"], "ok", initial)
        repair = initial["data"]["review_actions"]["recommended_next_action"]
        state = dict(repair["state_args"])
        event = state.pop("event")
        review_evidence = sys.modules["review_evidence"]
        with patch.object(review_evidence, "REVIEW_ACTION_CAP", 5):
            repaired = self.srv.wf_review_event_response(
                self.root, self.wave_id, event, repair["actor_role"], "cap-repair",
                mode="create", judgment=judgment, evidence=evidence,
                integrity_checks=integrity_checks(), **state,
            )
        self.assertEqual(repaired["status"], "ok", repaired)
        actions = repaired["data"]["review_actions"]
        self.assertEqual(actions["total_current_actions"], 8)
        self.assertEqual(actions["returned_current_actions"], 5)
        self.assertEqual(actions["omitted_current_actions"], 3)
        returned_ids = {item["action_id"] for item in actions["next_actions"]}
        for action in actions["next_actions"]:
            self.assertEqual(len(action["legal_alternatives"]), 4, action)
            self.assertTrue(
                set(action["legal_alternatives"]).issubset(returned_ids), action
            )

    def test_postbuild_relationship_rejection_has_guided_recovery(self):
        """AC-8: relationship validation failures get phase-correct recovery."""
        judgment, evidence = self._finding_payloads()
        initial = self.srv.wf_review_event_response(
            self.root, self.wave_id, "finding", "qa-reviewer", "invalid-initial",
            mode="create", finding_id="bad-cycle", run_kind="initial_delivery",
            cycle=0, judgment=judgment, evidence=evidence,
            source_lanes=["qa-reviewer"], blocking_required_lanes=["qa-reviewer"],
            integrity_checks=integrity_checks(),
        )
        self.assertEqual(initial["status"], "ok", initial)
        rejected = self.srv.wf_review_event_response(
            self.root, self.wave_id, "finding", "implementer", "invalid-repair",
            mode="create", finding_id="bad-cycle", run_kind="repair_start",
            cycle=0, judgment=judgment, evidence=evidence,
            source_lanes=["qa-reviewer"], blocking_required_lanes=["qa-reviewer"],
            integrity_checks=integrity_checks(),
        )
        self.assertEqual(rejected["status"], "error", rejected)
        diagnostic = next(
            item for item in rejected["diagnostics"]
            if "cycle >= 1" in item["message"]
        )
        self.assertEqual(diagnostic["code"], "review_evidence_invalid")
        self.assertEqual(diagnostic["recovery_tools"], ["wf_review_wave"])
        self.assertIn("phase='implementation'", diagnostic["recovery_usage"])

    def test_recovery_phase_is_derived_from_authority_not_invalid_caller_phase(self):
        """AC-8: invalid caller fields cannot redirect corrective guidance."""
        for supplied_phase in (None, "delivery", "bogus"):
            rejected = self.srv.wf_review_event_response(
                self.root, self.wave_id, "approval", "wave-council",
                f"bad-readiness-{supplied_phase}", mode="create",
                signoff_key="wave-council-readiness",
                approval_phase=supplied_phase, fresh_context=True, independent=True,
                integrity_checks=integrity_checks(),
                evidence={"observed": "invalid phase", "artifact_or_test_id": "phase"},
            )
            self.assertEqual(rejected["status"], "error", rejected)
            usages = " ".join(
                item.get("recovery_usage", "") for item in rejected["diagnostics"]
            )
            self.assertIn("phase='prepare'", usages, rejected)

        self.wave_md.write_text(
            self.wave_md.read_text(encoding="utf-8").replace(
                "Status: planned", "Status: implementing"
            ),
            encoding="utf-8",
        )
        delivery = self.srv.wf_review_event_response(
            self.root, self.wave_id, "approval", "operator", "bad-delivery",
            mode="create", signoff_key="operator-signoff",
            approval_phase="readiness", integrity_checks=integrity_checks(),
            evidence={"observed": "invalid phase", "artifact_or_test_id": "phase"},
        )
        self.assertEqual(delivery["status"], "error", delivery)
        delivery_usages = " ".join(
            item.get("recovery_usage", "") for item in delivery["diagnostics"]
        )
        self.assertIn("phase='implementation'", delivery_usages, delivery)

        judgment, evidence = self._finding_payloads()
        irrelevant_phase = self.srv.wf_review_event_response(
            self.root, self.wave_id, "finding", "qa-reviewer", "finding-phase",
            mode="create", finding_id="finding-phase", run_kind="initial_delivery",
            cycle=0, approval_phase="readiness", judgment=judgment,
            evidence=evidence, source_lanes=["qa-reviewer"],
            blocking_required_lanes=["qa-reviewer"],
            integrity_checks=integrity_checks(),
        )
        self.assertEqual(irrelevant_phase["status"], "ok", irrelevant_phase)
        self.assertEqual(
            irrelevant_phase["data"]["review_actions"]["phase"], "delivery"
        )
        self.assertEqual(
            irrelevant_phase["data"]["review_actions"]["recommended_next_action"]["phase"],
            "delivery",
        )

    def test_continuation_is_successful_create_only_and_runs_no_validation(self):
        judgment, evidence = self._finding_payloads()
        kwargs = {
            "finding_id": "continuation-boundary",
            "run_kind": "initial_delivery",
            "cycle": 0,
            "judgment": judgment,
            "evidence": evidence,
            "source_lanes": ["qa-reviewer"],
            "blocking_required_lanes": ["qa-reviewer"],
            "approval_recheck_lanes": ["qa-reviewer"],
            "review_boundaries_changed": [],
            "integrity_checks": integrity_checks(),
        }
        preview = self.srv.wf_review_event_response(
            self.root, self.wave_id, "finding", "qa-reviewer", "boundary-preview",
            **kwargs,
        )
        self.assertEqual(preview["status"], "dry_run", preview)
        self.assertNotIn("review_actions", preview["data"])
        invalid = self.srv.wf_review_event_response(
            self.root, self.wave_id, "finding", "qa-reviewer", "boundary-invalid",
            mode="create", finding_id="invalid-only",
        )
        self.assertEqual(invalid["status"], "error", invalid)
        self.assertNotIn("review_actions", invalid["data"])
        listed = self._list()
        self.assertNotIn("review_actions", listed["data"])
        with patch.object(
            self.srv, "run_validate",
            side_effect=AssertionError("event continuation must not run full validation"),
        ):
            created = self.srv.wf_review_event_response(
                self.root, self.wave_id, "finding", "qa-reviewer", "boundary-create",
                mode="create", **kwargs,
            )
        self.assertEqual(created["status"], "ok", created)
        self.assertTrue(created["data"]["review_actions"]["available"])
        self.assertEqual(
            created["data"]["review_actions"]["recommended_next_action"]["action_kind"],
            "repair_start",
        )

    def test_review_ergonomics_prechange_baseline_is_frozen(self):
        """1tvbs baseline: current public flow reinspects through list after writes.

        This driver intentionally uses only public response functions and freezes
        the canonical starting ledger before the action-continuation product edit.
        Candidate tests start from the same bytes and must remove inspections,
        never transitions or validation.
        """
        generated_wave_id = self.wave_id
        fixed_wave_id = "1200a ergonomics-baseline"
        fixed_dir = self.wave_md.parent.parent / fixed_wave_id
        self.wave_md.parent.rename(fixed_dir)
        self.wave_id = fixed_wave_id
        self.wave_md = fixed_dir / "wave.md"
        self.wave_md.write_text(
            self.wave_md.read_text(encoding="utf-8").replace(
                generated_wave_id, fixed_wave_id
            ),
            encoding="utf-8",
        )
        self.events_path = sys.modules["review_evidence"].review_event_path(self.wave_md)
        judgment = {
            "validation_status": "real",
            "scope_relation": "admitted",
            "introduced_or_worsened_by_wave": True,
            "contract_relevance": "required_ac",
            "supported_reachability": True,
            "attacker_reachability": False,
            "authority_domain": "integrity",
            "authority_delta": "low",
            "observable_impact": "material",
            "containment": "none",
        }
        evidence = {
            "proposition": "the repair chain requires two independent lanes",
            "failure_condition": "a lane is skipped or a transition is guessed",
            "public_path": "wf_review_event",
            "command_or_fixture": "1tvbs frozen two-lane baseline",
            "expected": "repair_start then one reverification per lane",
            "observed": "the requested public transition completed",
            "artifact_or_test_id": "test:1tvbs-baseline",
            "limitations": "local canonical fixture",
            "safety_and_authorization": "local non-destructive fixture",
            "disposition_rationale": "required review state is actionable",
        }

        def write(root, kind, actor, context, blocking, *, cycle=None):
            return self.srv.wf_review_event_response(
                root, self.wave_id, "finding", actor, context,
                mode="create", finding_id="ergonomics-finding", run_kind=kind,
                cycle=(0 if kind == "initial_delivery" else 1) if cycle is None else cycle,
                judgment=judgment, evidence=evidence,
                source_lanes=["code-reviewer", "qa-reviewer"],
                blocking_required_lanes=blocking,
                approval_recheck_lanes=["code-reviewer", "qa-reviewer"],
                review_boundaries_changed=[], fresh_context=True, independent=True,
                integrity_checks=integrity_checks(),
            )

        initial = write(
            self.root,
            "initial_delivery", "qa-reviewer", "baseline-initial",
            ["code-reviewer", "qa-reviewer"],
        )
        self.assertEqual(initial["status"], "ok", initial)
        starting_bytes = self.events_path.read_bytes()
        self.assertEqual(
            hashlib.sha256(starting_bytes).hexdigest(),
            "a3fa2311d0c993c22c1e950797c3b4a1ec40c1ac6d125126b33bfa560dad2fcc",
        )
        self.candidate_tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.candidate_tmp.cleanup)
        candidate_root = Path(self.candidate_tmp.name) / "candidate"
        shutil.copytree(self.root, candidate_root)
        candidate_events = candidate_root / self.events_path.relative_to(self.root)
        self.assertEqual(candidate_events.read_bytes(), starting_bytes)

        call_trace = []
        with patch.object(
            self.srv, "run_validate",
            return_value={"passed": True, "errors": [], "warnings": [], "output": ""},
        ) as full_validate:
            reviewed = self.srv.wf_review_wave_response(
                self.root, self.wave_id, phase="implementation"
            )
            call_trace.append("wf_review_wave")
            self.assertIn(reviewed["status"], {"ok", "error"})
            for transition in (
                ("repair_start", "implementer", "baseline-repair", ["code-reviewer", "qa-reviewer"]),
                ("reverification", "code-reviewer", "baseline-code", ["qa-reviewer"]),
                ("reverification", "qa-reviewer", "baseline-qa", []),
            ):
                listed = self._list(finding_id="ergonomics-finding")
                call_trace.append("wf_review_event:list")
                self.assertEqual(listed["status"], "ok", listed)
                written = write(self.root, *transition)
                call_trace.append(f"wf_review_event:{transition[0]}")
                self.assertEqual(written["status"], "ok", written)

        final_list = self._list(finding_id="ergonomics-finding")
        call_trace.append("wf_review_event:list")
        head = final_list["data"]["chain_summary"]["ergonomics-finding"]
        self.assertTrue(head["terminal"], head)
        self.assertEqual(head["unresolved_required_lanes"], [])

        # A later repair pass is caller judgment rather than a state-derived
        # continuation. Once that cycle is explicitly opened, the same guided
        # contract removes every intermediate list inspection and derives the
        # mandatory convergence checkpoint after the final lane clears.
        for transition in (
            ("repair_start", "implementer", "baseline-repair-2", ["code-reviewer", "qa-reviewer"]),
            ("reverification", "code-reviewer", "baseline-code-2", ["qa-reviewer"]),
            ("reverification", "qa-reviewer", "baseline-qa-2", []),
        ):
            written = write(self.root, *transition, cycle=2)
            call_trace.append(f"wf_review_event:{transition[0]}")
            self.assertEqual(written["status"], "ok", written)
            listed = self._list(finding_id="ergonomics-finding")
            call_trace.append("wf_review_event:list")
            self.assertEqual(listed["status"], "ok", listed)
        self.assertEqual(full_validate.call_count, 1)
        self.assertEqual(call_trace.count("wf_review_event:list"), 7)
        self.assertEqual(
            call_trace,
            [
                "wf_review_wave",
                "wf_review_event:list", "wf_review_event:repair_start",
                "wf_review_event:list", "wf_review_event:reverification",
                "wf_review_event:list", "wf_review_event:reverification",
                "wf_review_event:list",
                "wf_review_event:repair_start", "wf_review_event:list",
                "wf_review_event:reverification", "wf_review_event:list",
                "wf_review_event:reverification", "wf_review_event:list",
            ],
        )

        candidate_trace = []
        with patch.object(
            self.srv, "run_validate",
            return_value={"passed": True, "errors": [], "warnings": [], "output": ""},
        ) as candidate_validate:
            candidate_review = self.srv.wf_review_wave_response(
                candidate_root, self.wave_id, phase="implementation"
            )
            candidate_trace.append("wf_review_wave")
            action = candidate_review["data"]["review_actions"]["recommended_next_action"]
            self.assertEqual(action["action_kind"], "repair_start", action)
            for context in ("baseline-repair", "baseline-code", "baseline-qa"):
                state = dict(action["state_args"])
                event = state.pop("event")
                written = self.srv.wf_review_event_response(
                    candidate_root,
                    self.wave_id,
                    event,
                    action["actor_role"],
                    context,
                    mode="create",
                    judgment=judgment,
                    evidence=evidence,
                    review_boundaries_changed=[],
                    fresh_context=True,
                    independent=True,
                    integrity_checks=integrity_checks(),
                    **state,
                )
                self.assertEqual(written["status"], "ok", written)
                candidate_trace.append(f"wf_review_event:{action['action_kind']}")
                action = written["data"]["review_actions"]["recommended_next_action"]

            cycle_two = write(
                candidate_root,
                "repair_start",
                "implementer",
                "baseline-repair-2",
                ["code-reviewer", "qa-reviewer"],
                cycle=2,
            )
            self.assertEqual(cycle_two["status"], "ok", cycle_two)
            candidate_trace.append("wf_review_event:repair_start")
            action = cycle_two["data"]["review_actions"]["recommended_next_action"]
            for context in ("baseline-code-2", "baseline-qa-2"):
                state = dict(action["state_args"])
                event = state.pop("event")
                written = self.srv.wf_review_event_response(
                    candidate_root,
                    self.wave_id,
                    event,
                    action["actor_role"],
                    context,
                    mode="create",
                    judgment=judgment,
                    evidence=evidence,
                    review_boundaries_changed=[],
                    fresh_context=True,
                    independent=True,
                    integrity_checks=integrity_checks(),
                    **state,
                )
                self.assertEqual(written["status"], "ok", written)
                candidate_trace.append(f"wf_review_event:{action['action_kind']}")
                action = written["data"]["review_actions"]["recommended_next_action"]

        self.assertEqual(candidate_validate.call_count, 1)
        self.assertNotIn("wf_review_event:list", candidate_trace)
        self.assertEqual(
            candidate_trace,
            [
                "wf_review_wave",
                "wf_review_event:repair_start",
                "wf_review_event:reverification",
                "wf_review_event:reverification",
                "wf_review_event:repair_start",
                "wf_review_event:reverification",
                "wf_review_event:reverification",
            ],
        )
        self.assertLess(len(candidate_trace), len(call_trace))
        self.assertEqual(candidate_events.read_bytes(), self.events_path.read_bytes())
        baseline_records = self.srv.validate_external_review_evidence(self.wave_md).records
        candidate_wave_md = candidate_root / self.wave_md.relative_to(self.root)
        candidate_records = self.srv.validate_external_review_evidence(candidate_wave_md).records
        review_evidence = sys.modules["review_evidence"]
        self.assertEqual(
            review_evidence.current_synthesis_heads(candidate_records),
            review_evidence.current_synthesis_heads(baseline_records),
        )
        self.assertEqual(
            review_evidence.review_status_rows(
                candidate_records, ("code-reviewer", "qa-reviewer")
            ),
            review_evidence.review_status_rows(
                baseline_records, ("code-reviewer", "qa-reviewer")
            ),
        )
        self.assertTrue(
            any(
                row.get("record_type") == "review_run"
                and row.get("run_kind") == "convergence_checkpoint"
                for row in baseline_records
            ),
            "the multi-cycle path must derive its convergence checkpoint",
        )

        def close_signature(response):
            return (
                response["status"],
                tuple(row["code"] for row in response.get("diagnostics", [])),
            )

        close_validate = {
            "passed": True,
            "errors": [],
            "warnings": [],
            "output": "",
        }
        with patch.object(self.srv, "run_validate", return_value=close_validate) as baseline_close_validate:
            baseline_close = self.srv.wf_close_wave_response(
                self.root, self.wave_id, mode="dry_run"
            )
        with patch.object(self.srv, "run_validate", return_value=close_validate) as candidate_close_validate:
            candidate_close = self.srv.wf_close_wave_response(
                candidate_root, self.wave_id, mode="dry_run"
            )
        self.assertEqual(close_signature(candidate_close), close_signature(baseline_close))
        self.assertEqual(baseline_close_validate.call_count, 1)
        self.assertEqual(candidate_close_validate.call_count, 1)
        self.assertEqual(full_validate.call_count + baseline_close_validate.call_count, 2)
        self.assertEqual(candidate_validate.call_count + candidate_close_validate.call_count, 2)

    def test_list_event_credits_ledger_state_source(self):
        """Operator extension: the list response credits the live ledger file
        through the state-source census; previews and errors credit nothing.
        All inputs are REAL responses from the canonical builder (fragile-CE
        rule: never hand-model the envelope)."""
        self._seed_finding_chain()
        listed = self._list()
        credited = self.srv._state_sources_review_evidence(self.root, listed)
        rel_events = str(self.events_path.resolve().relative_to(self.root.resolve())).replace("\\", "/")
        self.assertEqual(credited, [rel_events])
        preview = self.srv.wf_review_event_response(
            self.root, self.wave_id, "run", "wave-council", "credit-preview",
            run_kind="initial_delivery", cycle=0,
        )
        self.assertEqual(preview["status"], "dry_run")
        self.assertEqual(self.srv._state_sources_review_evidence(self.root, preview), [])
        written = self.srv.wf_review_event_response(
            self.root, self.wave_id, "run", "wave-council", "credit-write",
            mode="create", run_kind="initial_delivery", cycle=0,
        )
        self.assertEqual(written["status"], "ok")
        write_credit = self.srv._state_sources_review_evidence(self.root, written)
        self.assertIn(rel_events, write_credit)

    def test_artifact_extractors_return_iterable_on_every_real_envelope(self):
        """1t6ow live-caught repair: the 1t3ek per-artifact wrapper iterates
        raw_artifacts, so every extractor return must be list-typed. The int
        `0` early returns made the observational recorder throw and silently
        drop the whole debit row for every non-create wf_review_event
        response (dry runs, errors, and the new list event). Inputs here are
        REAL envelopes from the canonical builder, and the wrapper's exact
        consumption expression is exercised against each."""
        self._seed_finding_chain()
        listed = self._list()
        dry = self.srv.wf_review_event_response(
            self.root, self.wave_id, "run", "wave-council", "extractor-preview",
            run_kind="initial_delivery", cycle=0,
        )
        error = self.srv.wf_review_event_response(
            self.root, self.wave_id, "finding", "qa-reviewer", "extractor-error",
            mode="create", finding_id="extractor-error", run_kind="initial_delivery",
        )
        written = self.srv.wf_review_event_response(
            self.root, self.wave_id, "run", "wave-council", "extractor-write",
            mode="create", run_kind="initial_delivery", cycle=0,
        )
        for label, envelope in (("list", listed), ("dry_run", dry),
                                ("error", error), ("create", written)):
            raw, _event_id = self.srv._artifact_from_review_evidence(self.root, envelope)
            # The wrapper's exact expression must not raise (TypeError was the
            # silent-drop failure mode).
            total = sum(max(0, int(r) - 5) for r in raw)
            self.assertGreaterEqual(total, 0, label)
        raw, _ = self.srv._artifact_from_written_paths("written")(self.root, listed)
        self.assertEqual(list(raw), [])

    def test_identical_repeat_listings_are_neutral_by_content_identity(self):
        """Operator policy: identical-content repeat listings share one
        content-hash event id, so the store's replay dedup makes them neutral
        (0 credit, 0 debit); a different filter or a changed ledger yields a
        new id and records normally. Real envelopes throughout."""
        self._seed_finding_chain()
        first = self._list()
        second = self._list()
        _, id_first = self.srv._artifact_from_review_evidence(self.root, first)
        _, id_second = self.srv._artifact_from_review_evidence(self.root, second)
        self.assertTrue(id_first and id_first.startswith("list:"))
        self.assertEqual(id_first, id_second)
        filtered = self._list(record_type="review_run")
        _, id_filtered = self.srv._artifact_from_review_evidence(self.root, filtered)
        self.assertNotEqual(id_first, id_filtered)
        self.srv.wf_review_event_response(
            self.root, self.wave_id, "run", "wave-council", "neutral-version-bump",
            mode="create", run_kind="initial_delivery", cycle=0,
        )
        after_write = self._list()
        _, id_after = self.srv._artifact_from_review_evidence(self.root, after_write)
        self.assertNotEqual(id_first, id_after)

    def test_write_rejection_recovery_hint_names_guided_review(self):
        """1tvbs: field-shape rejections route to phase-correct guided review."""
        response = self.srv.wf_review_event_response(
            self.root, self.wave_id, "finding", "qa-reviewer", "missing-facts",
            mode="create", finding_id="missing-facts", run_kind="initial_delivery",
        )
        self.assertEqual(response["status"], "error")
        usages = " ".join(d.get("recovery_usage", "") for d in response["diagnostics"])
        self.assertIn("wf_review_wave", usages)
        self.assertIn("phase='implementation'", usages)
        self.assertNotIn("event='list'", usages)


class MarkChangeItemRecoveryTests(unittest.TestCase):
    """1ug66: narrow marking errors must guide a safe retry, never a guess."""

    def setUp(self):
        self.srv = load_server()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.wave_id = "1200w-mark-recovery"
        self.wave_dir = self.root / "docs" / "waves" / self.wave_id
        self.wave_dir.mkdir(parents=True)
        (self.wave_dir / "wave.md").write_text(
            f"# Wave\n\nWave ID: `{self.wave_id}`\nStatus: implementing\n",
            encoding="utf-8",
        )

    def _write_change(self, body):
        (self.wave_dir / "1200c-mark-sample.md").write_text(body, encoding="utf-8")

    @staticmethod
    def _diagnostic(response):
        return response["diagnostics"][0]

    def test_ambiguous_task_returns_candidates_and_safe_recovery(self):
        self._write_change(
            "# Sample\n\n## Tasks\n\n- [ ] Implement\n- [ ] Implement\n"
        )
        response = self.srv._mark_change_item_response(
            self.root, self.wave_id, "1200c-mark-sample", "Implement", "x", target_section="Tasks",
        )
        diagnostic = self._diagnostic(response)
        self.assertEqual(response["status"], "error")
        self.assertEqual(diagnostic["code"], "ambiguous_mark_target")
        self.assertEqual(response["data"]["candidate_labels"], ["Implement", "Implement"])
        self.assertIn("Do not choose arbitrarily", diagnostic["message"])
        self.assertEqual(diagnostic["recovery_tools"], ["wf_get_change"])

    def test_missing_target_and_non_checkbox_text_return_a_structured_retry(self):
        self._write_change(
            "# Sample\n\n## Tasks\n\nA prose line that is not a checkbox.\n- [ ] Implement\n"
        )
        response = self.srv._mark_change_item_response(
            self.root, self.wave_id, "1200c-mark-sample", "Missing", "x", target_section="Tasks",
        )
        diagnostic = self._diagnostic(response)
        self.assertEqual(response["status"], "error")
        self.assertEqual(diagnostic["code"], "mark_target_not_found")
        self.assertIn("current exact label", diagnostic["message"])
        self.assertEqual(diagnostic["recovery_tools"], ["wf_get_change"])

    def test_wrapped_task_marks_by_its_logical_label(self):
        self._write_change(
            "# Sample\n\n## Tasks\n\n- [ ] Implement the parser\n"
            "  and preserve semicolon values.\n"
        )
        response = self.srv._mark_change_item_response(
            self.root, self.wave_id, "1200c-mark-sample",
            "Implement the parser and preserve semicolon values.", "x",
            target_section="Tasks", mode="create",
        )
        self.assertEqual(response["status"], "ok", response)
        self.assertIn("[x] Implement the parser", (self.wave_dir / "1200c-mark-sample.md").read_text(encoding="utf-8"))

    def test_missing_wrapped_task_returns_every_logical_label(self):
        self._write_change(
            "# Sample\n\n## Tasks\n\n- [ ] Implement the parser\n"
            "  and preserve semicolon values.\n- [ ] Add tests.\n"
        )
        response = self.srv._mark_change_item_response(
            self.root, self.wave_id, "1200c-mark-sample", "Missing", "x",
            target_section="Tasks",
        )
        self.assertEqual(response["status"], "error", response)
        self.assertEqual(
            response["data"]["candidate_labels"],
            ["Implement the parser and preserve semicolon values.", "Add tests."],
        )

    def test_required_ac_deferral_explains_how_to_supply_its_rationale(self):
        self._write_change(
            "# Sample\n\n## Acceptance Criteria\n\n- [ ] AC-1: Do it.\n\n"
            "## AC Priority\n\n| AC | Priority | Rationale |\n| --- | --- | --- |\n"
            "| AC-1 | required | Core |\n"
        )
        response = self.srv._mark_change_item_response(
            self.root, self.wave_id, "1200c-mark-sample", "AC-1", "~", target_section="Acceptance Criteria",
        )
        diagnostic = self._diagnostic(response)
        self.assertEqual(response["status"], "error")
        self.assertEqual(diagnostic["code"], "tilde_rationale_required")
        self.assertIn("wf_mark_ac", diagnostic["message"])
        self.assertIn("reason", diagnostic["message"])


class PrepareCouncilVerdictParserTests(unittest.TestCase):
    def setUp(self):
        self.srv = load_server()

    def test_wrapped_verdict_preserves_semicolons_inside_values(self):
        text = (
            "## Review Checkpoints\n\n"
            "- **Prepare-phase Wave Council [prepare-council] — 2026-08-06: PASS**\n"
            "  (moderator: wave-council; primer-depth: standard; seats: red-team, code-reviewer;\n"
            "  rotating-seat: code-reviewer; strongest-challenge: first concern; second concern;\n"
            "  strongest-alternative: retain the old parser; add diagnostics)\n"
        )
        info = self.srv._prepare_council_verdict_info(text)
        self.assertTrue(info["valid"], info)
        self.assertEqual(info["meta"]["strongest-challenge"], "first concern; second concern")
        self.assertEqual(info["meta"]["strongest-alternative"], "retain the old parser; add diagnostics")


class MarkAcReceiptRefreshTests(unittest.TestCase):
    """1ulnu: an AC deferral refreshes policy provenance without approvals."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))
        (self.root / "docs" / "workflow-config.json").write_text(
            json.dumps({"wave_review": {"enabled": True, "delivery_mode": "targeted"}}),
            encoding="utf-8",
        )
        created = self.srv.wf_create_wave_response(
            self.root, "receipt-refresh", mode="create"
        )
        self.wave_id = created["data"]["wave_id"]
        self.change_id = "1200a-enh receipt-refresh"
        staged = self.root / "docs" / "plans" / f"{self.change_id}.md"
        staged.parent.mkdir(parents=True, exist_ok=True)
        staged.write_text(
            "# Receipt refresh\n\n"
            f"Change ID: `{self.change_id}`\n"
            "Change Status: `planned`\n"
            "Owner: Engineering\nStatus: planned\nLast verified: 2026-08-05\n"
            "Wave: TBD\n\n## Rationale\n\nTest receipt refresh.\n\n"
            "## Requirements\n\n1. Keep the policy receipt current.\n\n"
            "## Scope\n\nIn scope.\n\n"
            "## Acceptance Criteria\n\n"
            "- [ ] AC-1: Defer only with a reason.\n"
            "- [ ] AC-2: Preserve ordinary completion tracking.\n\n"
            "## Tasks\n\n- [ ] Implement receipt refresh.\n\n"
            "## Serialization Points\n\n"
            "- `.wavefoundry/framework/scripts/server_impl.py`\n\n"
            "## Affected Architecture Docs\n\nN/A\n\n"
            "## AC Priority\n\n"
            "| AC | Priority | Rationale |\n| --- | --- | --- |\n"
            "| AC-1 | required | Contract change. |\n"
            "| AC-2 | important | Tracking stays cheap. |\n\n"
            "## Progress Log\n\n| Date | Update | Evidence |\n| --- | --- | --- |\n\n"
            "## Decision Log\n\n| Date | Decision | Reason | Alternatives |\n| --- | --- | --- | --- |\n\n"
            "## Risks\n\n| Risk | Mitigation |\n| --- | --- |\n\n"
            "## Session Handoff\n\nSee `docs/agents/session-handoff.md` for current session state.\n",
            encoding="utf-8",
        )
        added = self.srv.wf_add_change_response(
            self.root, self.wave_id, self.change_id, mode="create"
        )
        self.assertEqual(added["status"], "ok", added)
        self.wave_md = self.root / "docs" / "waves" / self.wave_id / "wave.md"
        self.change_path = self.wave_md.parent / f"{self.change_id}.md"
        _append_review_run(self.root, self.wave_id, kind="readiness")
        wave_text = self.wave_md.read_text(encoding="utf-8")
        state, errors = self.srv.lifecycle_gate_support._prepare_policy_state(
            self.root,
            self.wave_md,
            wave_text,
            [self.change_id],
            self.srv.lifecycle_gate_support._build_prepare_council_brief(self.wave_id, wave_text, [self.change_id]),
        )
        self.assertEqual(errors, ())
        self.assertIsNotNone(state)
        self.srv._publish_prepare_policy_state(
            self.root, self.wave_md, wave_text, state
        )
        self.review = sys.modules["review_evidence"]
        approved = self.srv.wf_review_event_response(
            self.root,
            self.wave_id,
            "approval",
            "wave-council",
            "receipt-refresh-before-deferral",
            mode="create",
            signoff_key="wave-council-readiness",
            approval_phase="readiness",
            fresh_context=True,
            independent=True,
            integrity_checks=integrity_checks(),
            evidence={
                "observed": "approved the current receipt before the contract changed",
                "artifact_or_test_id": "test:receipt-refresh-before-deferral",
            },
        )
        self.assertEqual(approved["status"], "ok", approved)

    def tearDown(self):
        self.tmp.cleanup()

    def _receipt_id(self):
        records, errors = self.review.read_review_event_ledger(self.wave_md)
        self.assertEqual(errors, ())
        return sys.modules["review_policy"].current_policy_receipt(records)["receipt_id"]

    def test_deferral_refreshes_receipt_and_returns_fresh_actions(self):
        previous = self._receipt_id()
        response = self.srv._mark_change_item_response(
            self.root, self.wave_id, self.change_id, "AC-1", "~",
            target_section="Acceptance Criteria",
            reason="requires an operator-run compatibility project",
            mode="create",
        )
        self.assertEqual(response["status"], "ok", response)
        refreshed = response["data"]["review_receipt_refreshed"]
        self.assertNotEqual(refreshed["receipt_id"], previous)
        self.assertTrue(refreshed["review_actions"]["available"])
        self.assertGreater(refreshed["review_actions"]["total_current_actions"], 0)
        self.assertEqual(
            refreshed["review_actions"]["next_actions"][0]["state_args"]["signoff_key"],
            "wave-council-readiness",
        )
        self.assertIn("[~] AC-1: Defer only with a reason.", self.change_path.read_text(encoding="utf-8"))
        self.assertIn("requires an operator-run compatibility project", self.change_path.read_text(encoding="utf-8"))

    def test_completion_and_task_marks_do_not_publish_receipts(self):
        before = self.review.review_event_path(self.wave_md).read_bytes()
        completed = self.srv._mark_change_item_response(
            self.root, self.wave_id, self.change_id, "AC-2", "x",
            target_section="Acceptance Criteria", mode="create",
        )
        self.assertEqual(completed["status"], "ok", completed)
        self.assertNotIn("review_receipt_refreshed", completed["data"])
        self.assertEqual(self.review.review_event_path(self.wave_md).read_bytes(), before)
        tasked = self.srv._mark_change_item_response(
            self.root, self.wave_id, self.change_id, "Implement receipt refresh.", "x",
            target_section="Tasks", mode="create",
        )
        self.assertEqual(tasked["status"], "ok", tasked)
        self.assertEqual(self.review.review_event_path(self.wave_md).read_bytes(), before)

    def test_refresh_failure_diagnostic_is_path_free(self):
        """1uzwh delivery-council repair, both halves pinned separately.

        The chmod scenario reaches the handler through _prepare_policy_state's
        ledger read (producer: review_evidence's ledger OSError branch, now
        path-free at the source), so it pins the PRODUCER half. The patched
        scenario raises a real path-carrying OSError from the publication step
        directly into the handler's except, bypassing every producer-side
        sanitation, so it pins the CONSUMER half (the message must render via
        _read_error_detail, not the raw exception). Red pre-fix on each half's
        own scenario: the message contained the absolute target."""
        leak_target = self.review.review_event_path(self.wave_md)

        def _assert_path_free(response):
            self.assertEqual(response["status"], "error", response)
            self.assertEqual(
                response["diagnostics"][0]["code"], "review_receipt_refresh_failed")
            message = response["diagnostics"][0]["message"]
            self.assertIn("Permission denied", message)
            self.assertNotIn(
                str(self.root), message,
                "the refresh-failure diagnostic must not leak the absolute path")

        with self.subTest(half="producer-ledger-read"):
            os.chmod(leak_target, 0)
            try:
                response = self.srv._mark_change_item_response(
                    self.root, self.wave_id, self.change_id, "AC-1", "~",
                    target_section="Acceptance Criteria",
                    reason="external validation pending", mode="create",
                )
            finally:
                os.chmod(leak_target, 0o644)
            _assert_path_free(response)

        with self.subTest(half="consumer-raw-oserror"):
            def boom(*args, **kwargs):
                raise PermissionError(13, "Permission denied", str(leak_target))

            with patch.object(self.srv, "_publish_prepare_policy_state", side_effect=boom):
                response = self.srv._mark_change_item_response(
                    self.root, self.wave_id, self.change_id, "AC-1", "~",
                    target_section="Acceptance Criteria",
                    reason="external validation pending", mode="create",
                )
            _assert_path_free(response)

    def test_receipt_write_failure_rolls_back_the_deferred_ac_and_ledger(self):
        change_before = self.change_path.read_bytes()
        ledger_before = self.review.review_event_path(self.wave_md).read_bytes()
        wave_before = self.wave_md.read_bytes()
        original_replace = self.srv._atomic_replace_bytes

        def fail_change_write(path, payload, purpose):
            if purpose == "receipt-change":
                raise OSError("injected change-write failure")
            return original_replace(path, payload, purpose)

        with patch.object(self.srv, "_atomic_replace_bytes", side_effect=fail_change_write):
            response = self.srv._mark_change_item_response(
                self.root, self.wave_id, self.change_id, "AC-1", "~",
                target_section="Acceptance Criteria", reason="external validation pending",
                mode="create",
            )
        self.assertEqual(response["status"], "error", response)
        self.assertEqual(response["diagnostics"][0]["code"], "review_receipt_refresh_failed")
        self.assertEqual(self.change_path.read_bytes(), change_before)
        self.assertEqual(self.review.review_event_path(self.wave_md).read_bytes(), ledger_before)
        self.assertEqual(self.wave_md.read_bytes(), wave_before)


class WaveCloseModeDiscoverabilityTests(unittest.TestCase):
    """AC-16: wf_close_wave invalid-mode response includes valid_modes field."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def test_invalid_mode_returns_valid_modes_in_data(self):
        result = self.srv.wf_close_wave_response(self.root, "some-wave", mode="run")
        self.assertEqual(result["status"], "error")
        self.assertIn("valid_modes", result["data"])
        self.assertIn("dry_run", result["data"]["valid_modes"])
        self.assertIn("create", result["data"]["valid_modes"])

    def test_valid_dry_run_mode_does_not_error_on_mode(self):
        # wave not found is a different error; confirm mode itself is accepted
        result = self.srv.wf_close_wave_response(self.root, "nonexistent-wave", mode="dry_run")
        # Should fail on wave_not_found, not invalid_arguments
        self.assertTrue(
            any(d.get("code") == "wave_not_found" for d in result.get("diagnostics", [])),
            f"Expected wave_not_found diagnostic, got: {result.get('diagnostics')}",
        )


class WaveCreateWaveTemplateTests(unittest.TestCase):
    """AC-17: wf_create_wave produces wave.md with Wave Summary and Watchpoints stubs."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def test_wave_md_contains_wave_summary_section(self):
        result = self.srv.wf_create_wave_response(self.root, "test-wave", mode="create")
        self.assertEqual(result["status"], "ok")
        wave_md = self.root / result["data"]["path"]
        text = wave_md.read_text(encoding="utf-8")
        self.assertIn("## Wave Summary", text)

    def test_wave_md_contains_watchpoints_section(self):
        result = self.srv.wf_create_wave_response(self.root, "test-wave", mode="create")
        self.assertEqual(result["status"], "ok")
        wave_md = self.root / result["data"]["path"]
        text = wave_md.read_text(encoding="utf-8")
        self.assertIn("## Watchpoints", text)


class WaveCreateWaveLastVerifiedTests(unittest.TestCase):
    """12as3: wf_create_wave scaffold emits today's ISO date, not the literal '<date>'."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def test_wf_create_wave_last_verified_populates_today(self):
        import datetime
        result = self.srv.wf_create_wave_response(self.root, "date-test", mode="create")
        self.assertEqual(result["status"], "ok")
        wave_md = self.root / result["data"]["path"]
        text = wave_md.read_text(encoding="utf-8")
        today_iso = datetime.date.today().isoformat()
        self.assertIn(f"Last verified: {today_iso}", text)
        self.assertNotIn("Last verified: <date>", text)

    def test_wf_create_wave_scaffold_last_verified_is_valid(self):
        """Scaffold emits a valid ISO date that docs-lint will accept."""
        import re
        result = self.srv.wf_create_wave_response(self.root, "valid-date", mode="create")
        wave_md = self.root / result["data"]["path"]
        text = wave_md.read_text(encoding="utf-8")
        m = re.search(r"^Last verified:\s*(\S+)", text, re.MULTILINE)
        self.assertIsNotNone(m, "Last verified line missing from scaffold")
        value = m.group(1)
        self.assertRegex(value, r"^\d{4}-\d{2}-\d{2}$", f"Last verified value not ISO date: {value!r}")


class WaveLifecycleWithoutJournalTests(unittest.TestCase):
    """1t9w9: no lifecycle step requires a journal to exist."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def test_prepare_dry_run_raises_no_journal_diagnostics(self):
        wave_response = self.srv.wf_create_wave_response(
            self.root, "journal-free", mode="create"
        )["data"]
        wave_id = wave_response["wave_id"]
        change_id = self.srv.new_change(self.root, "feat", "no-journal-needed")["id"]
        self.srv.wf_add_change_response(self.root, wave_id, change_id, mode="create")
        result = self.srv.wf_prepare_wave_response(self.root, wave_id, mode="dry_run")
        combined = " ".join(
            d.get("message", "") for d in result.get("diagnostics", [])
        ) + " " + " ".join(result.get("data", {}).get("errors", []))
        # The retired requirement must be gone; the minimal fixture's
        # unrelated missing-file noise is not what this test pins.
        self.assertNotIn("must be referenced by at least one journal artifact", combined)
        self.assertNotIn("add exactly this line to a file under docs/agents/journals/", combined)
        journals_dir = self.root / "docs" / "agents" / "journals"
        self.assertFalse(
            journals_dir.exists() and any(journals_dir.glob("*.md")),
            "the lifecycle must not have created a journal",
        )

    def test_start_wave_help_routes_capture_to_memory_not_journals(self):
        result = self.srv.wf_help_response(goal="start_wave")
        self.assertEqual(result["status"], "ok")
        rationale = str(result["data"])
        self.assertIn("memory", rationale.lower())
        self.assertNotIn("docs/agents/journals", rationale)


# ---------------------------------------------------------------------------
# 12aj7 MCP Layer Polish tests
# ---------------------------------------------------------------------------

class WaveStatusDriftDetectionTests(unittest.TestCase):
    """Item 1: wf_current_wave_response includes change_status_drift diagnostic."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        _make_repo(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def _make_wave_with_drift(self):
        """Create a wave with one change whose file status differs from wave.md."""
        wave_dir = self.root / "docs" / "waves" / "test-wave"
        wave_dir.mkdir(parents=True, exist_ok=True)
        wave_md = wave_dir / "wave.md"
        wave_md.write_text(
            "# Wave Record\n\nOwner: Engineering\nStatus: active\nLast verified: 2026-01-01\n\nwave-id: `test-wave`\nTitle: Test Wave\n\n## Changes\n\nChange ID: `abc12-feat my-change`\nChange Status: `in-progress`\n",
            encoding="utf-8",
        )
        change_doc = wave_dir / "abc12-feat my-change.md"
        change_doc.write_text(
            "# My Change\n\nChange ID: `abc12-feat my-change`\nChange Status: `complete`\n",
            encoding="utf-8",
        )
        return wave_dir

    def test_no_drift_no_diagnostic(self):
        wave_dir = self.root / "docs" / "waves" / "test-wave"
        wave_dir.mkdir(parents=True, exist_ok=True)
        (wave_dir / "wave.md").write_text(
            "# Wave Record\n\nOwner: Engineering\nStatus: active\nLast verified: 2026-01-01\n\nwave-id: `test-wave`\nTitle: Test Wave\n\n## Changes\n\nChange ID: `abc12-feat my-change`\nChange Status: `in-progress`\n",
            encoding="utf-8",
        )
        (wave_dir / "abc12-feat my-change.md").write_text(
            "# My Change\n\nChange ID: `abc12-feat my-change`\nChange Status: `in-progress`\n",
            encoding="utf-8",
        )
        resp = self.srv.wf_current_wave_response(self.root)
        codes = [d.get("code") for d in (resp.get("diagnostics") or [])]
        self.assertNotIn("change_status_drift", codes)

    def test_drift_produces_diagnostic(self):
        self._make_wave_with_drift()
        resp = self.srv.wf_current_wave_response(self.root)
        codes = [d.get("code") for d in (resp.get("diagnostics") or [])]
        self.assertIn("change_status_drift", codes)

    def test_drift_response_status_still_ok(self):
        """Drift detection is advisory — status must remain 'ok'."""
        self._make_wave_with_drift()
        resp = self.srv.wf_current_wave_response(self.root)
        self.assertEqual(resp["status"], "ok")


class EditGateToolTests(unittest.TestCase):
    """12ax9/12sf9: wf_open_gate / wf_close_gate / wf_gate_status MCP tools."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        _make_repo(self.root)
        # Start with both gates closed
        overrides_path = self.root / ".wavefoundry" / "guard-overrides.json"
        overrides_path.parent.mkdir(parents=True, exist_ok=True)
        import json
        overrides_path.write_text(
            json.dumps({"seed_edit_allowed": {"enabled": False}, "framework_edit_allowed": {"enabled": False}}) + "\n",
            encoding="utf-8",
        )

    def tearDown(self):
        self.tmp.cleanup()

    def _read_gates(self):
        import json
        path = self.root / ".wavefoundry" / "guard-overrides.json"
        return json.loads(path.read_text(encoding="utf-8"))

    def test_open_closed_gate_succeeds(self):
        resp = self.srv.wave_open_gate_response(self.root, "seed_edit_allowed")
        self.assertEqual(resp["status"], "ok")
        self.assertTrue(self._read_gates()["seed_edit_allowed"]["enabled"])

    def test_open_already_open_gate_returns_error(self):
        self.srv.wave_open_gate_response(self.root, "seed_edit_allowed")
        resp = self.srv.wave_open_gate_response(self.root, "seed_edit_allowed")
        self.assertEqual(resp["status"], "error")
        codes = [d.get("code") for d in (resp.get("diagnostics") or [])]
        self.assertIn("gate_already_open", codes)

    def test_close_open_gate_succeeds(self):
        self.srv.wave_open_gate_response(self.root, "seed_edit_allowed")
        resp = self.srv.wf_close_wave_gate_response(self.root, "seed_edit_allowed")
        self.assertEqual(resp["status"], "ok")
        self.assertFalse(self._read_gates()["seed_edit_allowed"]["enabled"])

    def test_close_already_closed_gate_returns_advisory(self):
        resp = self.srv.wf_close_wave_gate_response(self.root, "seed_edit_allowed")
        self.assertEqual(resp["status"], "ok")
        codes = [d.get("code") for d in (resp.get("diagnostics") or [])]
        self.assertIn("gate_already_closed", codes)

    def test_framework_edit_allowed_gate_works(self):
        resp = self.srv.wave_open_gate_response(self.root, "framework_edit_allowed")
        self.assertEqual(resp["status"], "ok")
        self.assertTrue(self._read_gates()["framework_edit_allowed"]["enabled"])
        resp2 = self.srv.wf_close_wave_gate_response(self.root, "framework_edit_allowed")
        self.assertEqual(resp2["status"], "ok")
        self.assertFalse(self._read_gates()["framework_edit_allowed"]["enabled"])

    def test_invalid_gate_name_returns_error(self):
        resp = self.srv.wave_open_gate_response(self.root, "nonexistent_gate")
        self.assertEqual(resp["status"], "error")
        codes = [d.get("code") for d in (resp.get("diagnostics") or [])]
        self.assertIn("invalid_arguments", codes)

    def test_design_system_gate_open_and_close(self):
        resp = self.srv.wave_open_gate_response(self.root, "design_system_edit_allowed")
        self.assertEqual(resp["status"], "ok")
        self.assertTrue(self._read_gates()["design_system_edit_allowed"]["enabled"])
        resp2 = self.srv.wf_close_wave_gate_response(self.root, "design_system_edit_allowed")
        self.assertEqual(resp2["status"], "ok")
        self.assertFalse(self._read_gates()["design_system_edit_allowed"]["enabled"])

    def test_gate_status_returns_all_gates(self):
        resp = self.srv.wf_gate_status_response(self.root)
        self.assertEqual(resp["status"], "ok")
        gates = resp["data"]["gates"]
        self.assertIn("seed_edit_allowed", gates)
        self.assertIn("framework_edit_allowed", gates)
        self.assertIn("design_system_edit_allowed", gates)
        # All gates should be closed in initial test state
        self.assertFalse(gates["seed_edit_allowed"])
        self.assertFalse(gates["framework_edit_allowed"])

    def test_gate_status_reflects_open_gate(self):
        self.srv.wave_open_gate_response(self.root, "seed_edit_allowed")
        resp = self.srv.wf_gate_status_response(self.root)
        self.assertEqual(resp["status"], "ok")
        gates = resp["data"]["gates"]
        self.assertTrue(gates["seed_edit_allowed"])
        self.assertFalse(gates["framework_edit_allowed"])


class GateAutoCloseTests(unittest.TestCase):
    """12ax9: wf_pause_wave and wf_close_wave auto-close open gates."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        _make_repo(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def _open_gate(self, gate="seed_edit_allowed"):
        import json
        path = self.root / ".wavefoundry" / "guard-overrides.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        data.setdefault(gate, {})["enabled"] = True
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    def _gate_state(self, gate="seed_edit_allowed"):
        import json
        path = self.root / ".wavefoundry" / "guard-overrides.json"
        if not path.exists():
            return False
        return json.loads(path.read_text(encoding="utf-8")).get(gate, {}).get("enabled", False)

    def _make_active_wave(self):
        wave_dir = self.root / "docs" / "waves" / "test-wave"
        wave_dir.mkdir(parents=True, exist_ok=True)
        (wave_dir / "wave.md").write_text(
            "# Wave Record\n\nOwner: Engineering\nStatus: active\nLast verified: 2026-05-01\n\nwave-id: `test-wave`\nTitle: Test Wave\n\n## Changes\n\n## Wave Summary\n\nTest.\n\n## Journal Watchpoints\n\n- Test.\n",
            encoding="utf-8",
        )

    def test_wf_pause_wave_with_open_gate_forces_close_and_emits_diagnostic(self):
        self._make_active_wave()
        self._open_gate("seed_edit_allowed")
        resp = self.srv.wf_pause_wave_response(self.root, "test-wave", mode="create")
        self.assertEqual(resp["status"], "ok")
        codes = [d.get("code") for d in (resp.get("diagnostics") or [])]
        self.assertIn("gates_forced_closed", codes)
        self.assertFalse(self._gate_state("seed_edit_allowed"))

    def test_wf_close_wave_dry_run_with_open_gate_emits_diagnostic_but_does_not_write(self):
        self._make_active_wave()
        self._open_gate("seed_edit_allowed")
        resp = self.srv.wf_close_wave_response(self.root, "test-wave", mode="dry_run")
        # dry_run may fail validation but should still emit gate diagnostic
        codes = [d.get("code") for d in (resp.get("diagnostics") or [])]
        self.assertIn("gates_forced_closed", codes)
        # Gate must NOT be written in dry-run
        self.assertTrue(self._gate_state("seed_edit_allowed"))

    def test_wf_close_wave_create_with_open_gate_forces_close_and_emits_diagnostic(self):
        self._make_active_wave()
        self._open_gate("seed_edit_allowed")
        # Add minimal review evidence so wf_close_wave can pass validation
        wave_md = self.root / "docs" / "waves" / "test-wave" / "wave.md"
        text = wave_md.read_text(encoding="utf-8")
        wave_md.write_text(text + "\n## Review Signoff Evidence\n\n- operator-signoff: approved\n- 2026-05-01: approved and signoff complete.\n", encoding="utf-8")
        with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": []}):
            with patch.object(self.srv, "run_garden", return_value={"passed": True}):
                resp = self.srv.wf_close_wave_response(self.root, "test-wave", mode="create")
        codes = [d.get("code") for d in (resp.get("diagnostics") or [])]
        self.assertIn("gates_forced_closed", codes)
        self.assertFalse(self._gate_state("seed_edit_allowed"))

    def test_wf_close_wave_with_no_open_gates_has_no_gate_diagnostic(self):
        self._make_active_wave()
        wave_md = self.root / "docs" / "waves" / "test-wave" / "wave.md"
        text = wave_md.read_text(encoding="utf-8")
        wave_md.write_text(text + "\n## Review Signoff Evidence\n\n- operator-signoff: approved\n- 2026-05-01: approved and signoff complete.\n", encoding="utf-8")
        with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": []}):
            with patch.object(self.srv, "run_garden", return_value={"passed": True}):
                resp = self.srv.wf_close_wave_response(self.root, "test-wave", mode="create")
        codes = [d.get("code") for d in (resp.get("diagnostics") or [])]
        self.assertNotIn("gates_forced_closed", codes)


class WaveCloseHandoffPreservationTests(unittest.TestCase):
    """12axd: wf_close_wave and wf_pause_wave preserve session handoff content."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        _make_repo(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def _make_active_wave(self):
        wave_dir = self.root / "docs" / "waves" / "hw-test"
        wave_dir.mkdir(parents=True, exist_ok=True)
        (wave_dir / "wave.md").write_text(
            "# Wave Record\n\nOwner: Engineering\nStatus: active\nLast verified: 2026-05-01\n\nwave-id: `hw-test`\nTitle: HW Test\n\n## Changes\n\n## Wave Summary\n\nTest.\n\n## Journal Watchpoints\n\n- Test.\n",
            encoding="utf-8",
        )

    def _write_handoff(self, content):
        handoff = self.root / "docs" / "agents" / "session-handoff.md"
        handoff.parent.mkdir(parents=True, exist_ok=True)
        handoff.write_text(content, encoding="utf-8")

    def _read_handoff(self):
        return (self.root / "docs" / "agents" / "session-handoff.md").read_text(encoding="utf-8")

    def test_close_updates_wave_md_status(self):
        self._make_active_wave()
        wave_md = self.root / "docs" / "waves" / "hw-test" / "wave.md"
        text = wave_md.read_text(encoding="utf-8")
        wave_md.write_text(text + "\n## Review Signoff Evidence\n\n- operator-signoff: approved\n- 2026-05-01: approved and signoff complete.\n", encoding="utf-8")
        with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": []}):
            with patch.object(self.srv, "run_garden", return_value={"passed": True}):
                self.srv.wf_close_wave_response(self.root, "hw-test", mode="create")
        content = wave_md.read_text(encoding="utf-8")
        self.assertIn("Status: closed", content)
        self.assertIn("Completed At:", content)
        # No archive folder should be created
        self.assertFalse((self.root / "docs" / "waves" / "hw-test" / "archive").exists())

    def test_wf_close_wave_preserves_handoff_content_outside_active_wave(self):
        self._make_active_wave()
        custom_section = "## My Notes\n\nSome important agent notes that must survive.\n"
        self._write_handoff(
            f"# Session Handoff\n\nOwner: wave-coordinator\nStatus: active\nLast verified: 2026-05-01\n\n"
            f"## Current Session\n\n**Active wave:** `hw-test`\n\n{custom_section}"
        )
        wave_md = self.root / "docs" / "waves" / "hw-test" / "wave.md"
        text = wave_md.read_text(encoding="utf-8")
        wave_md.write_text(text + "\n## Review Signoff Evidence\n\n- operator-signoff: approved\n- 2026-05-01: approved and signoff complete.\n", encoding="utf-8")
        with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": []}):
            with patch.object(self.srv, "run_garden", return_value={"passed": True}):
                self.srv.wf_close_wave_response(self.root, "hw-test", mode="create")
        result = self._read_handoff()
        self.assertIn("Some important agent notes that must survive.", result)
        self.assertIn("*(none)*", result)

    def test_wf_pause_wave_preserves_handoff_content_outside_active_wave(self):
        self._make_active_wave()
        custom_section = "## Research Notes\n\nContext that must not be wiped on pause.\n"
        self._write_handoff(
            f"# Session Handoff\n\nOwner: wave-coordinator\nStatus: active\nLast verified: 2026-05-01\n\n"
            f"## Current Session\n\n**Active wave:** `hw-test`\n\n{custom_section}"
        )
        self.srv.wf_pause_wave_response(self.root, "hw-test", mode="create")
        result = self._read_handoff()
        self.assertIn("Context that must not be wiped on pause.", result)

    def test_wf_close_wave_missing_handoff_creates_scaffold(self):
        self._make_active_wave()
        handoff = self.root / "docs" / "agents" / "session-handoff.md"
        if handoff.exists():
            handoff.unlink()
        wave_md = self.root / "docs" / "waves" / "hw-test" / "wave.md"
        text = wave_md.read_text(encoding="utf-8")
        wave_md.write_text(text + "\n## Review Signoff Evidence\n\n- operator-signoff: approved\n- 2026-05-01: approved and signoff complete.\n", encoding="utf-8")
        with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": []}):
            with patch.object(self.srv, "run_garden", return_value={"passed": True}):
                self.srv.wf_close_wave_response(self.root, "hw-test", mode="create")
        self.assertTrue(handoff.exists())
        content = handoff.read_text(encoding="utf-8")
        self.assertIn("Session Handoff", content)


class BulkWaveGetChangeTests(unittest.TestCase):
    """Item 3: wf_get_change with wave_id (no change_id) returns all admitted changes."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        _make_repo(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def _setup_wave(self):
        wave_dir = self.root / "docs" / "waves" / "bulk-wave"
        wave_dir.mkdir(parents=True, exist_ok=True)
        (wave_dir / "wave.md").write_text(
            "# Wave Record\n\nOwner: Engineering\nStatus: active\nLast verified: 2026-01-01\n\nwave-id: `bulk-wave`\nTitle: Bulk Wave\n\n## Changes\n\nChange ID: `ch1xx-feat first`\nChange Status: `in-progress`\n\nChange ID: `ch2xx-feat second`\nChange Status: `planned`\n",
            encoding="utf-8",
        )
        (wave_dir / "ch1xx-feat first.md").write_text(
            "# First\n\nChange ID: `ch1xx-feat first`\nChange Status: `in-progress`\n",
            encoding="utf-8",
        )
        (wave_dir / "ch2xx-feat second.md").write_text(
            "# Second\n\nChange ID: `ch2xx-feat second`\nChange Status: `planned`\n",
            encoding="utf-8",
        )

    def test_bulk_returns_all_changes(self):
        self._setup_wave()
        resp = self.srv.wf_get_change_response(self.root, wave_id="bulk-wave")
        self.assertEqual(resp["status"], "ok")
        changes = resp["data"]["changes"]
        ids = [c["id"] for c in changes]
        self.assertIn("ch1xx-feat first", ids)
        self.assertIn("ch2xx-feat second", ids)

    def test_bulk_count_field(self):
        self._setup_wave()
        resp = self.srv.wf_get_change_response(self.root, wave_id="bulk-wave")
        self.assertEqual(resp["data"]["count"], 2)

    def test_bulk_unknown_wave_returns_ok_with_diagnostic(self):
        resp = self.srv.wf_get_change_response(self.root, wave_id="nonexistent-wave")
        self.assertEqual(resp["status"], "ok")
        codes = [d.get("code") for d in (resp.get("diagnostics") or [])]
        self.assertIn("wave_not_found", codes)

    def test_single_mode_unchanged(self):
        """Providing change_id without wave_id uses original single-lookup mode."""
        self._setup_wave()
        resp = self.srv.wf_get_change_response(self.root, change_id="ch1xx-feat first")
        self.assertEqual(resp["status"], "ok")
        self.assertIn("change", resp["data"])
        self.assertIn("First", resp["data"]["change"]["content"])

    def test_single_mode_ambiguous_change_returns_all_matches(self):
        self._setup_wave()
        (self.root / "docs" / "plans").mkdir(parents=True, exist_ok=True)
        other = self.root / "docs" / "plans" / "ch1xx-bug collision.md"
        other.write_text("# Collision\n\nChange ID: `ch1xx-bug collision`\n", encoding="utf-8")
        resp = self.srv.wf_get_change_response(self.root, change_id="ch1xx")
        self.assertEqual(resp["status"], "ok")
        self.assertIsNone(resp["data"]["change"])
        ids = {m["change_id"] for m in resp["data"]["changes"]}
        self.assertEqual(ids, {"ch1xx-feat first", "ch1xx-bug collision"})
        codes = [d.get("code") for d in resp.get("diagnostics") or []]
        self.assertIn("ambiguous_change_id", codes)

    def test_single_mode_excludes_wave_md_from_change_lookup(self):
        self._setup_wave()
        wave_text = (self.root / "docs" / "waves" / "bulk-wave" / "wave.md").read_text(encoding="utf-8")
        self.assertIn("ch1xx-feat first", wave_text)
        matches = self.srv._resolve_change_doc_matches(self.root, "bulk-wave")
        self.assertEqual(matches, [])

    def test_token_anchored_change_matching_ignores_slug_substring(self):
        plans = self.root / "docs" / "plans"
        plans.mkdir(parents=True, exist_ok=True)
        (plans / "zzzzz-bug mentions-ch1xx.md").write_text(
            "# Mention\n\nChange ID: `zzzzz-bug mentions-ch1xx`\n",
            encoding="utf-8",
        )
        resp = self.srv.wf_get_change_response(self.root, change_id="ch1xx")
        self.assertEqual(resp["data"]["change"], None)
        codes = [d.get("code") for d in resp.get("diagnostics") or []]
        self.assertIn("change_not_found", codes)

    def test_ambiguous_wave_lookup_returns_all_matches(self):
        self._setup_wave()
        second = self.root / "docs" / "waves" / "bulk-wave-extra"
        second.mkdir(parents=True, exist_ok=True)
        (second / "wave.md").write_text(
            "# Wave Record\n\nOwner: Engineering\nStatus: planned\nLast verified: 2026-01-01\n\nwave-id: `bulk-wave-extra`\nTitle: Extra\n\n## Changes\n\nChange ID: `ch3xx-feat third`\nChange Status: `planned`\n",
            encoding="utf-8",
        )
        resp = self.srv.wf_get_change_response(self.root, wave_id="bulk-wave")
        self.assertEqual(resp["status"], "ok")
        self.assertEqual(resp["data"]["changes"], [])
        wave_ids = {m["wave_id"] for m in resp["data"]["waves"]}
        self.assertEqual(wave_ids, {"bulk-wave", "bulk-wave-extra"})
        codes = [d.get("code") for d in resp.get("diagnostics") or []]
        self.assertIn("ambiguous_wave_id", codes)

    def test_wave_and_change_namespaces_do_not_cross_resolve(self):
        self._setup_wave()
        plans = self.root / "docs" / "plans"
        plans.mkdir(parents=True, exist_ok=True)
        (plans / "bulk-wave-bug same-token.md").write_text(
            "# Same Token\n\nChange ID: `bulk-wave-bug same-token`\n",
            encoding="utf-8",
        )
        change_resp = self.srv.wf_get_change_response(self.root, change_id="bulk-wave")
        self.assertEqual(change_resp["data"]["change"]["change_id"], "bulk-wave-bug same-token")
        self.assertNotIn("waves", change_resp["data"])
        wave_resp = self.srv.wf_get_change_response(self.root, wave_id="bulk-wave")
        self.assertEqual(wave_resp["data"]["wave_id"], "bulk-wave")
        self.assertEqual(wave_resp["data"]["count"], 2)

    def _fresh_root(self):
        """Start a clean repo for one subTest without re-entering setUp().

        Re-calling setUp() rebinds self.tmp, so the earlier TemporaryDirectory
        leaks and any addCleanup() closure fires against a path tearDown has
        already removed.
        """
        self.tmp.cleanup()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        _make_repo(self.root)

    def _make_unreadable(self, path, mode):
        """Make `path` unreadable by `mode`, and restore it at test end.

        Restoration is registered against this exact path, so it must only be
        used on a root that stays alive for the rest of the test.
        """
        if mode == "decode":
            path.write_bytes(b"\xff\xfe not valid utf-8 \xff")
        else:
            if not path.exists():
                path.write_text("# placeholder\n", encoding="utf-8")
            os.chmod(path, 0)
            self.addCleanup(
                lambda: path.exists() and os.chmod(path, stat.S_IRUSR | stat.S_IWUSR))
        return path

    def _unreadable_admitted_wave(self, *, mode="decode", council=False):
        """A governed wave whose single admitted change cannot be read.

        `mode="decode"` writes invalid UTF-8; `mode="permission"` chmods it to 0.
        The OSError variant exists because an earlier revision guarded only the
        decode case, leaving the close hard gate fail-open for a
        permission-denied document.  `council=True` records a passing
        prepare-council verdict, which `wf_implement_wave` gates on *before* it
        reads any change document.
        """
        self._setup_wave()
        wave_md = self.root / "docs" / "waves" / "bulk-wave" / "wave.md"
        if council:
            wave_md.write_text(
                wave_md.read_text(encoding="utf-8")
                + "\n## Review Checkpoints\n\n"
                + _prepare_council_verdict_line(date="2026-08-06", verdict="PASS")
                + "\n",
                encoding="utf-8")
        return self._make_unreadable(
            self.root / "docs" / "waves" / "bulk-wave" / "ch1xx-feat first.md", mode)

    def test_close_blocks_on_an_unreadable_admitted_change(self):
        """1uu9z AC-4: VISIBLE, not silently dropped.

        The falsifying mutant is "catch the error, then `continue`" -- it
        produces a non-crashing result identical to the fix, and it survived the
        entire module before this test existed.  Both causes are asserted: the
        decode half was delivered first, and the OSError half was still silently
        skipped, which left the close hard gate fail-open for a `chmod 000`
        document.
        """
        for mode in ("decode", "permission"):
            with self.subTest(cause=mode):
                self._fresh_root()
                bad = self._unreadable_admitted_wave(mode=mode)
                wave_md = self.root / "docs" / "waves" / "bulk-wave" / "wave.md"
                findings = self.srv.lifecycle_gate_support._collect_silent_unchecked_items_for_close(
                    wave_md, wave_md.read_text(encoding="utf-8"))
                unreadable = [f for f in findings
                              if f.get("change_id") == "ch1xx-feat first"]
                self.assertTrue(
                    unreadable,
                    f"an unreadable admitted change ({mode}) must appear in the "
                    "close blocker list, not be skipped",
                )
                self.assertIn(
                    bad.name, unreadable[0]["item_text"],
                    "item_text must name the file; it is the operator-facing body",
                )
                self.assertIn(
                    "Error", unreadable[0]["item_text"],
                    "item_text must carry the exception type",
                )
                self.assertTrue(
                    unreadable[0].get("item_id"),
                    "item_id must be non-empty so the renderer does not tag an "
                    "unreadable file as an ordinary unchecked item",
                )

    def test_prepare_and_implement_report_an_unreadable_change(self):
        """1uu9z AC-1 and AC-2b: both tool boundaries return, naming the cause.

        Nine of twelve guard mutants survived the delivered suite; these are two
        of the boundaries that had no test at all.
        """
        for mode in ("decode", "permission"):
            for tool in ("prepare", "implement"):
                with self.subTest(cause=mode, tool=tool):
                    self._fresh_root()
                    self._unreadable_admitted_wave(
                        mode=mode, council=(tool == "implement"))
                    fn = (self.srv.wf_prepare_wave_response if tool == "prepare"
                          else self.srv.wf_implement_wave_response)
                    resp = fn(self.root, wave_id="bulk-wave", mode="dry_run")
                    diagnostics = resp.get("diagnostics") or []
                    codes = [d["code"] for d in diagnostics]
                    self.assertIn(
                        "change_doc_unreadable", codes,
                        f"{tool} must report the unreadable document, not crash "
                        f"and not stay silent (got {codes})",
                    )
                    message = " ".join(d["message"] for d in diagnostics
                                       if d["code"] == "change_doc_unreadable")
                    self.assertIn("ch1xx-feat first", message,
                                  "the diagnostic must name the document")
                    self.assertIn(
                        "Error", message,
                        "AC-3: the diagnostic must carry the CAUSE (exception "
                        "type), not the document name alone -- a message "
                        "dropping the cause survived mutation before this",
                    )

    def test_add_change_refuses_an_unreadable_doc_without_moving_it(self):
        """1uu9z Requirement 1: no site raises, and nothing mutates on refusal.

        Two defects meet here.  The resolver was widened to MATCH unreadable
        documents, which let `wf_add_change(mode='create')` reach
        `_move_change_doc` and relocate a file it could not read; and a second
        read in the same function was left unguarded, so `dry_run` still raised.
        """
        for mode in ("decode", "permission"):
            with self.subTest(cause=mode):
                self._fresh_root()
                self._setup_wave()
                plans = self.root / "docs" / "plans"
                plans.mkdir(parents=True, exist_ok=True)
                src = plans / "ch9xx-feat unreadable.md"
                src.write_text(
                    "# U\n\nChange ID: `ch9xx-feat unreadable`\n"
                    "Change Status: `planned`\n", encoding="utf-8")
                self._make_unreadable(src, mode)
                target = (self.root / "docs" / "waves" / "bulk-wave"
                          / "ch9xx-feat unreadable.md")
                for call_mode in ("dry_run", "create"):
                    resp = self.srv.wf_add_change_response(
                        self.root, wave_id="bulk-wave",
                        change_id="ch9xx-feat unreadable", mode=call_mode)
                    self.assertEqual(resp["status"], "error", (call_mode, resp))
                    self.assertIn(
                        "change_doc_unreadable",
                        [d["code"] for d in resp.get("diagnostics") or []])
                    self.assertTrue(
                        src.exists(),
                        f"{call_mode} must not move a document it cannot read")
                    self.assertFalse(
                        target.exists(),
                        f"{call_mode} relocated an unreadable document; a "
                        "refusal must not mutate")

    def test_close_returns_at_the_tool_boundary_not_just_the_helper(self):
        """1uu9z AC-2: asserted at `wf_close_wave`, both close-path sites.

        The helper test above calls `_collect_silent_unchecked_items_for_close`
        directly, which cannot satisfy this AC: a readiness seat proved that
        patching only that helper left `wf_close_wave` still raising, from
        `_generate_wf_close_wave_summary` in the same body.  Only a call at the
        tool boundary covers both.  Asserted as "does not raise" plus a named
        cause, because a crash and a silent pass are the two failure modes and
        one assertion each cannot tell them apart.
        """
        for mode in ("decode", "permission"):
            with self.subTest(cause=mode):
                self._fresh_root()
                self._unreadable_admitted_wave(mode=mode)
                try:
                    resp = self.srv.wf_close_wave_response(
                        self.root, "bulk-wave", mode="dry_run")
                except UnicodeError as exc:
                    self.fail(f"wf_close_wave raised instead of reporting: {exc!r}")
                except OSError as exc:
                    self.fail(f"wf_close_wave raised instead of reporting: {exc!r}")
                codes = [d["code"] for d in resp.get("diagnostics") or []]
                self.assertIn(
                    "change_doc_unreadable", codes,
                    "an unreadable admitted document is its own diagnostic, "
                    "under the code every sibling site uses -- not an "
                    "unchecked-items entry (the first version reported a false "
                    "unchecked count with an impossible instruction)",
                )
                close_message = " ".join(
                    d["message"] for d in resp["diagnostics"]
                    if d["code"] == "change_doc_unreadable")
                self.assertIn(
                    "Error", close_message,
                    "AC-3 at close: the partitioned diagnostic must carry the "
                    "cause, not the document name alone",
                )
                unchecked = " ".join(
                    d["message"] for d in resp["diagnostics"]
                    if d["code"] == "silent_unchecked_items_at_close")
                self.assertNotIn(
                    "ch1xx-feat first", unchecked,
                    "the unreadable document must be excluded from the "
                    "unchecked-items count and prose",
                )
                blob = json.dumps(resp)
                self.assertIn(
                    "ch1xx-feat first", blob,
                    "close must name the document it could not read",
                )
                self.assertNotEqual(
                    resp["status"], "ok",
                    "an unreadable admitted document must not close cleanly; "
                    "the hard gate cannot be verified over a document that "
                    "cannot be read",
                )

    def test_the_summary_boundary_catch_reports_when_the_race_lands(self):
        """1uu9z AC-2, second close-path site, exercised at the tool boundary.

        In-process, `_collect_silent_unchecked_items_for_close` blocks first
        over the identical change set, so `_generate_wf_close_wave_summary`'s
        caller-side catch is reachable only through a TOCTOU race: the document
        was readable during the hard-gate scan and unreadable by the summary
        read.  The race is simulated by patching the hard-gate helper to see
        nothing; every prior gate must also pass or close returns before the
        summary is generated.  Without this test all three narrowings of the
        boundary handler survived mutation.
        """
        from unittest.mock import patch as _patch

        wave_dir = self.root / "docs" / "waves" / "race-wave"
        wave_dir.mkdir(parents=True, exist_ok=True)
        (wave_dir / "wave.md").write_text(
            "# Wave Record\n"
            "wave-id: `race-wave`\n"
            "Status: active\n\n"
            "## Changes\n\n"
            "Change ID: `ch9ra-feat racer`\n"
            "Change Status: `complete`\n\n"
            "## Review Evidence\n\n"
            "- operator-signoff: approved\n"
            "- architecture-reviewer: approved\n"
            "- code-reviewer: approved\n"
            "- qa-reviewer: approved\n",
            encoding="utf-8",
        )
        (wave_dir / "ch9ra-feat racer.md").write_bytes(b"\xff\xfe not utf-8")
        with _patch.object(self.srv, "run_garden", return_value={"passed": True, "files_updated": 0, "updated": [], "output": ""}), \
             _patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}), \
             _patch.object(self.srv.lifecycle_gate_support, "_collect_silent_unchecked_items_for_close", return_value=[]) as _gate_mock_5:
            try:
                resp = self.srv.wf_close_wave_response(self.root, "race-wave", mode="dry_run")
            except (OSError, UnicodeError, ValueError) as exc:
                self.fail(f"the summary boundary catch must report, not raise: {exc!r}")
            _gate_mock_5.assert_called()
        self.assertEqual(resp["status"], "error")
        codes = [d["code"] for d in resp.get("diagnostics") or []]
        self.assertIn("change_doc_unreadable", codes, codes)
        message = " ".join(d["message"] for d in resp["diagnostics"]
                           if d["code"] == "change_doc_unreadable")
        self.assertIn("ch9ra-feat racer", message)
        self.assertNotIn(str(self.root), message,
                         "the boundary message must not leak the absolute path")

    def test_mark_and_footprint_survive_an_unreadable_doc_both_causes(self):
        """1uu9z AC-5 at the two sites the delivered suite left unproven.

        `_mark_change_item_response` must return an error naming the cause;
        `_wave_code_footprint` must degrade to None -- it feeds an advisory,
        and the pre-change whole-loop `except OSError` is exactly the shape
        that silently disabled a sensor before.
        """
        for mode in ("decode", "permission"):
            with self.subTest(cause=mode):
                self._fresh_root()
                self._unreadable_admitted_wave(mode=mode)
                resp = self.srv._mark_change_item_response(
                    self.root, "bulk-wave", "ch1xx-feat first", "AC-1", "x",
                    target_section="Acceptance Criteria", mode="dry_run")
                self.assertEqual(resp["status"], "error")
                self.assertIn(
                    "change_doc_unreadable",
                    [d["code"] for d in resp.get("diagnostics") or []])
                self.assertIsNone(
                    self.srv._wave_code_footprint(
                        self.root,
                        self.root / "docs" / "waves" / "bulk-wave" / "wave.md"),
                    "the footprint advisory must degrade, not raise",
                )

    def test_bulk_get_change_reports_the_oserror_cause_too(self):
        """1uu9z AC-5: the bulk surface was pinned for decode only; the OSError
        half survived mutation (drop `OSError`, keep `UnicodeError`)."""
        self._fresh_root()
        self._unreadable_admitted_wave(mode="permission")
        resp = self.srv.wf_get_change_response(self.root, wave_id="bulk-wave")
        self.assertEqual(resp["status"], "ok")
        codes = [d["code"] for d in resp.get("diagnostics") or []]
        self.assertIn("change_doc_unreadable", codes)
        entry = next(c for c in resp["data"]["changes"]
                     if c["id"] == "ch1xx-feat first")
        self.assertIsNone(entry["content"])
        self.assertIn("Error", entry["read_error"])

    def _ghost_wave(self) -> "Path":
        """A resolvable wave whose sole admitted change has no file on disk."""
        wave_dir = self.root / "docs" / "waves" / "ghost-wave"
        wave_dir.mkdir(parents=True, exist_ok=True)
        (wave_dir / "wave.md").write_text(
            "# Wave Record\n"
            "wave-id: `ghost-wave`\n"
            "Status: active\n\n"
            "## Changes\n\n"
            "Change ID: `ch9gh-feat ghost`\n"
            "Change Status: `complete`\n\n"
            "## Review Evidence\n\n"
            "- operator-signoff: approved\n"
            "- architecture-reviewer: approved\n"
            "- code-reviewer: approved\n"
            "- qa-reviewer: approved\n",
            encoding="utf-8",
        )
        return wave_dir

    def test_close_hard_gate_blocks_a_missing_admitted_doc(self):
        """1v0lx AC-1: a missing admitted document blocks close with its own
        `change_doc_missing` diagnostic naming the change id and the
        `wf_remove_change` recovery. Red pre-fix: the collector returned []
        for a ghost and close (lint patched out, the TOCTOU window the hard
        gate exists for) succeeded while the summary fabricated a record."""
        from unittest.mock import patch as _patch

        wave_dir = self._ghost_wave()
        items = self.srv.lifecycle_gate_support._collect_silent_unchecked_items_for_close(
            wave_dir / "wave.md",
            (wave_dir / "wave.md").read_text(encoding="utf-8"),
        )
        self.assertTrue(
            any(i["item_type"] == "change document" and i["item_id"] == "missing"
                for i in items),
            items,
        )
        with _patch.object(self.srv, "run_garden", return_value={"passed": True, "files_updated": 0, "updated": [], "output": ""}), \
             _patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
            resp = self.srv.wf_close_wave_response(self.root, "ghost-wave", mode="dry_run")
        self.assertEqual(resp["status"], "error")
        codes = [d["code"] for d in resp.get("diagnostics") or []]
        self.assertIn("change_doc_missing", codes, codes)
        self.assertNotIn(
            "change_doc_unreadable", codes,
            "absent is not broken: the missing case must not reuse the unreadable code",
        )
        message = " ".join(d["message"] for d in resp["diagnostics"]
                           if d["code"] == "change_doc_missing")
        self.assertIn("ch9gh-feat ghost", message)
        self.assertIn("wf_remove_change", message)
        self.assertNotIn(str(self.root), message,
                         "the missing-doc message must not leak the absolute path")

    def test_single_fault_publication_detail_is_path_free(self):
        """1v0ly AC-2, red-first (the qa readiness probe observed the head
        leaking the absolute path with `rollback_errors` empty): the common
        single-fault path must compose the whole detail path-free while still
        naming the artifact, its purpose, and the cause."""
        from unittest.mock import patch as _patch

        artifact = self.root / "docs" / "waves" / "bulk-wave" / "artifact-a.txt"

        def boom(path, payload, purpose):
            raise PermissionError(13, "Permission denied", str(path))

        with _patch.object(self.srv, "_atomic_replace_bytes", side_effect=boom):
            with self.assertRaises(OSError) as ctx:
                self.srv._replace_artifacts_transactionally(
                    self.root, [(artifact, b"payload", "receipt")])
        detail = str(ctx.exception)
        self.assertNotIn(str(self.root), detail,
                         "the single-fault head must not leak the absolute path")
        self.assertIn("artifact-a.txt", detail)
        self.assertIn("receipt", detail)
        self.assertIn("Permission denied", detail)
        self.assertNotIn("rollback incomplete", detail)

    def test_double_fault_publication_detail_is_path_free(self):
        """1v0ly AC-1: forced rollback double-fault, raise site exercised
        directly; entries render repo-relative with causes, no absolute
        path anywhere in the composed detail."""
        from unittest.mock import patch as _patch

        wave_dir = self.root / "docs" / "waves" / "bulk-wave"
        wave_dir.mkdir(parents=True, exist_ok=True)
        first = wave_dir / "artifact-a.txt"
        second = wave_dir / "artifact-b.txt"
        first.write_bytes(b"old-a")

        real = self.srv._atomic_replace_bytes
        calls = {"n": 0}

        def flaky(path, payload, purpose):
            calls["n"] += 1
            if calls["n"] == 1:
                real(path, payload, purpose)
                return
            raise PermissionError(13, "Permission denied", str(path))

        with _patch.object(self.srv, "_atomic_replace_bytes", side_effect=flaky):
            with self.assertRaises(OSError) as ctx:
                self.srv._replace_artifacts_transactionally(
                    self.root,
                    [(first, b"new-a", "receipt"), (second, b"new-b", "projection")])
        detail = str(ctx.exception)
        self.assertIn("rollback incomplete", detail)
        self.assertIn("artifact-a.txt", detail)
        self.assertIn("artifact-b.txt", detail)
        self.assertIn("Permission denied", detail)
        self.assertNotIn(str(self.root), detail,
                         "the double-fault entries must not leak absolute paths")

    def test_out_of_repo_artifact_renders_final_component_only(self):
        """1v0ly Requirement 1: `_repo_rel`'s fallback still raises for a
        genuinely out-of-repo path, so the composition keeps the artifact
        name and drops the absolute prefix."""
        import tempfile as _tempfile
        from unittest.mock import patch as _patch

        outside = Path(_tempfile.mkdtemp(prefix="outside-repo-"))
        self.addCleanup(shutil.rmtree, outside, ignore_errors=True)
        artifact = outside / "stray-receipt.jsonl"

        def boom(path, payload, purpose):
            raise PermissionError(13, "Permission denied", str(path))

        with _patch.object(self.srv, "_atomic_replace_bytes", side_effect=boom):
            with self.assertRaises(OSError) as ctx:
                self.srv._replace_artifacts_transactionally(
                    self.root, [(artifact, b"payload", "receipt")])
        detail = str(ctx.exception)
        self.assertIn("stray-receipt.jsonl", detail)
        self.assertNotIn(str(outside), detail,
                         "an out-of-repo artifact renders its final component only")

    def test_read_error_detail_behavioral_pin(self):
        """1v0ly AC-4: behavioral pin, not a source-literal one (the 1upba
        lesson): strerror rendering for a real OSError, verbatim fall-through
        for a synthetic single-arg one."""
        real = FileNotFoundError(2, "No such file or directory", "/abs/secret/path")
        with self.subTest(shape="real-oserror-strerror"):
            detail = self.srv.lifecycle_gate_support._read_error_detail(real)
            self.assertIn("FileNotFoundError", detail)
            self.assertIn("No such file or directory", detail)
            self.assertNotIn("/abs/secret/path", detail)
        with self.subTest(shape="synthetic-single-arg-verbatim"):
            synthetic = OSError("verbatim message with /some/path")
            self.assertIsNone(synthetic.strerror)
            detail = self.srv.lifecycle_gate_support._read_error_detail(synthetic)
            self.assertIn("verbatim message with /some/path", detail)

    def test_close_summary_raises_on_a_ghost_instead_of_fabricating(self):
        """1v0lx AC-2, by direct generator call (through the blocked gate no
        summary is generated and the branch would ship byte-unchanged). Red
        pre-fix: returned 'delivered one change' describing a document that
        does not exist."""
        wave_dir = self._ghost_wave()
        text = (wave_dir / "wave.md").read_text(encoding="utf-8")
        with self.assertRaises(ValueError) as ctx:
            self.srv._generate_wf_close_wave_summary(
                "ghost-wave", text, wave_dir / "wave.md")
        self.assertIn("ch9gh-feat ghost", str(ctx.exception))
        self.assertIn("wf_remove_change", str(ctx.exception))
        self.assertNotIn(str(self.root), str(ctx.exception))

    def test_list_plans_reports_an_unreadable_plan_doc(self):
        """1uu9z follow-up (twelfth site, found by the delivery code lane):
        `wf_list_plans` is the recovery tool `change_doc_unreadable` routes to
        from `wf_add_change`'s error exits, and it raised on the same input --
        the diagnostic sent the operator into a second stack trace.
        """
        for mode in ("decode", "permission"):
            with self.subTest(cause=mode):
                self._fresh_root()
                plans = self.root / "docs" / "plans"
                plans.mkdir(parents=True, exist_ok=True)
                (plans / "ch8ok-feat readable.md").write_text(
                    "# OK\n\nChange ID: `ch8ok-feat readable`\n"
                    "Change Status: `planned`\n", encoding="utf-8")
                bad = plans / "ch8xx-feat unreadable.md"
                self._make_unreadable(bad, mode)
                try:
                    resp = self.srv.wf_list_plans_response(self.root)
                except (OSError, UnicodeError) as exc:
                    self.fail(f"wf_list_plans must report, not raise: {exc!r}")
                self.assertEqual(resp["status"], "ok")
                self.assertIn(
                    "change_doc_unreadable",
                    [d["code"] for d in resp.get("diagnostics") or []],
                    "the unreadable plan must be reported, not silently listed",
                )
                ids = [p["id"] for p in resp["data"]["plans"]]
                self.assertIn("ch8ok-feat readable", ids,
                              "readable siblings must still be returned")
                bad_entry = next(p for p in resp["data"]["plans"]
                                 if p["id"] == "ch8xx-feat unreadable")
                self.assertIn("Error", bad_entry["read_error"])

    def test_the_close_read_failure_names_a_wave_relative_path(self):
        """1uu9z: the close diagnostic must not leak the operator's filesystem.

        `_generate_wf_close_wave_summary` has no repo root to hand `_repo_rel`,
        so its first version interpolated the absolute `change_path`.  Both
        causes are asserted: the OSError direction at this site survived
        mutation when only the decode case was pinned.
        """
        for mode in ("decode", "permission"):
            with self.subTest(cause=mode):
                self._fresh_root()
                self._unreadable_admitted_wave(mode=mode)
                try:
                    self.srv._generate_wf_close_wave_summary(
                        "bulk-wave",
                        (self.root / "docs" / "waves" / "bulk-wave" / "wave.md").read_text(
                            encoding="utf-8"),
                        self.root / "docs" / "waves" / "bulk-wave" / "wave.md",
                    )
                except ValueError as exc:
                    self.assertIn("bulk-wave/ch1xx-feat first.md", str(exc))
                    self.assertNotIn(
                        str(self.root), str(exc),
                        "the message must not contain the absolute repository path",
                    )
                else:
                    self.fail("expected the unreadable document to be reported")

    def test_an_unreadable_change_is_never_returned_as_empty(self):
        """1uu9z AC-4 at the read surfaces.

        `_resolve_change_doc_matches` now matches unreadable documents with
        `content: ""`.  Handing that back is the silent-drop failure relocated:
        an agent attaching the resource would see a blank change doc with no
        signal that anything failed.
        """
        self._unreadable_admitted_wave()
        self.assertIsNone(
            self.srv.get_change(self.root, "ch1xx-feat first"),
            "get_change must not return an empty string for an unreadable doc",
        )

    def test_one_unreadable_doc_does_not_disable_the_gapfill_scan(self):
        """1uu9z AC-4: a per-document guard, not a per-loop one.

        The falsifying mutant narrows the handler back to `except OSError`, so a
        decode failure escapes `_wave_has_gapfill_note`.  Both call sites wrap it
        in `except Exception`, so the visible effect is not a crash -- it is the
        retrieval-posture sensor silently reporting "no gapfill note" for the
        whole wave.  The unreadable document sorts FIRST so it is reached before
        the note; with a per-loop guard the scan aborts and never sees it.
        """
        for mode in ("decode", "permission"):
            with self.subTest(cause=mode):
                self._fresh_root()
                wave_dir = self.root / "docs" / "waves" / "bulk-wave"
                wave_dir.mkdir(parents=True, exist_ok=True)
                wave_md = wave_dir / "wave.md"
                wave_md.write_text("# Wave Record\n", encoding="utf-8")
                self._make_unreadable(wave_dir / "a-unreadable.md", mode)
                (wave_dir / "z-note.md").write_text(
                    "# Later\n\nGapfill: retrieval posture recorded.\n",
                    encoding="utf-8")
                self.assertTrue(
                    self.srv._wave_has_gapfill_note(wave_md),
                    f"one unreadable document ({mode}) must not hide a Gapfill "
                    "note in a document the scan had not reached yet",
                )

    def _registered_resources(self):
        """Capture the resource closures `register_mcp_surface` registers.

        `resource_change` is a closure over `get_handler`, not a module
        attribute, so it cannot be reached by import.  A recording double for
        the FastMCP surface is the only way to exercise the real function that
        the `wavefoundry://change/{change_id}` URI resolves to.
        """
        captured = {}
        root = self.root

        class _ToolManager:
            # register_mcp_surface probes mcp._tool_manager._tools; model that
            # shape rather than a catch-all __getattr__, which hands the probe a
            # function where it expects a mapping.
            def __init__(self):
                self._tools = {}

        class _Recorder:
            def __init__(self):
                self._tool_manager = _ToolManager()

            def resource(self, uri, **kwargs):
                def deco(fn):
                    captured[fn.__name__] = fn
                    return fn
                return deco

            def tool(self, *args, **kwargs):
                def deco(fn):
                    self._tool_manager._tools[kwargs.get("name", fn.__name__)] = fn
                    return fn
                if args and callable(args[0]):
                    return deco(args[0])
                return deco

        class _Handler:
            pass

        handler = _Handler()
        handler.root = root
        self.srv.register_mcp_surface(_Recorder(), lambda: handler)
        self.assertIn(
            "resource_change", captured,
            "register_mcp_surface no longer registers resource_change; this "
            "test's capture harness needs updating",
        )
        return captured

    def test_the_change_resource_signals_an_unreadable_doc(self):
        """1uu9z AC-4 at the resource surface.

        The falsifying mutant returns `matches[0]["content"]`, which the
        resolver sets to `""` for an unreadable document.  An agent attaching
        `wavefoundry://change/...` would then receive a blank change doc with no
        indication that anything failed -- the silent-drop defect relocated from
        the close gate to the read surface.
        """
        for mode in ("decode", "permission"):
            with self.subTest(cause=mode):
                self._fresh_root()
                self._unreadable_admitted_wave(mode=mode)
                body = self._registered_resources()["resource_change"](
                    "ch1xx-feat first")
                self.assertTrue(
                    body.strip(),
                    "an unreadable change doc must never render as an empty "
                    "resource body",
                )
                self.assertIn("Unreadable", body)
                self.assertIn("ch1xx-feat first", body)

    def test_no_read_failure_message_leaks_the_absolute_path(self):
        """1uu9z AC-3 hardening: a PermissionError's own str embeds the
        absolute path ("[Errno 13] Permission denied: '/…'"), so every site
        interpolating `{exc}` re-leaked the path its message had just rendered
        repo-relative.  All read-failure text now routes through
        `_read_error_detail`, which keeps `strerror` alone for OSError.
        Found red-first: the wave-relative pin failed the moment its
        permission subtest was added.
        """
        import json as _json
        self._unreadable_admitted_wave(mode="permission")
        # The prepare subject must reach `_prepare_policy_state`, which runs
        # only on a DECLARED wave with `wave_review` configured -- without
        # both, the leaking policy-selection line at that site is never
        # executed and this test passes vacuously for prepare.  Found by the
        # delivery code lane: the sanitized `change_doc_unreadable` message
        # and the leaking `review_policy_receipt_stale` one sat adjacent in
        # the same real-config envelope.
        (self.root / "docs" / "workflow-config.json").write_text(
            _json.dumps({"wave_review": {"enabled": True, "delivery_mode": "targeted"}}),
            encoding="utf-8",
        )
        wave_md = self.root / "docs" / "waves" / "bulk-wave" / "wave.md"
        wave_md.write_text(
            wave_md.read_text(encoding="utf-8").replace(
                "# Wave Record\n",
                # negative-fixture: test_no_read_failure_message_leaks_the_absolute_path deliberately supplies invalid or unreadable authority
                "# Wave Record\n\nreview-evidence-source: events.jsonl\n", 1),
            encoding="utf-8")
        (self.root / "docs" / "waves" / "bulk-wave" / "events.jsonl").write_text(
            "", encoding="utf-8")
        prepare_resp = self.srv.wf_prepare_wave_response(
            self.root, wave_id="bulk-wave", mode="dry_run")
        prepare_blob = _json.dumps(prepare_resp.get("diagnostics") or [])
        self.assertIn(
            "for policy selection", prepare_blob,
            "fixture must actually reach _prepare_policy_state's read-failure "
            "path, or the prepare half of this test is vacuous",
        )
        surfaces = {
            "prepare": prepare_resp,
            "get_change": self.srv.wf_get_change_response(
                self.root, wave_id="bulk-wave"),
            "mark": self.srv._mark_change_item_response(
                self.root, "bulk-wave", "ch1xx-feat first", "AC-1", "x",
                target_section="Acceptance Criteria", mode="dry_run"),
            "close": self.srv.wf_close_wave_response(
                self.root, "bulk-wave", mode="dry_run"),
        }
        for name, resp in surfaces.items():
            blob = _json.dumps(resp.get("diagnostics") or []) + _json.dumps(
                resp.get("data") or {})
            self.assertNotIn(
                str(self.root), blob,
                f"{name}: a read-failure message leaked the absolute repository path",
            )

    def test_a_readable_wave_is_unaffected_by_the_guards(self):
        """1uu9z AC-7 regression half: ok status, zero read diagnostics, determinism.

        This is NOT the before/after proof -- two calls of the same build cannot
        detect a regression against the pre-guard code, and a mutant that adds a
        field to every readable record passes it.  The real comparison was
        executed once against the reconstructed pre-guard shape across eight
        surfaces (byte-identical; recorded in the change doc's Progress Log)
        and is not reproducible from HEAD without mutating the working tree.
        What this test holds durably: a normally-decoding wave yields status
        ``ok``, no read diagnostics, and identical responses across calls.
        """
        self._setup_wave()
        first = self.srv.wf_get_change_response(self.root, wave_id="bulk-wave")
        second = self.srv.wf_get_change_response(self.root, wave_id="bulk-wave")
        self.assertEqual(first["status"], "ok")
        self.assertEqual(
            [d["code"] for d in first.get("diagnostics") or []], [],
            "a normally-decoding wave must produce no read diagnostics",
        )
        self.assertEqual(first["data"], second["data"])

    def test_undecodable_change_is_reported_in_bulk_and_single_lookup(self):
        """1uu9z AC-2b: the recovery tool must not turn decode failure into a crash."""
        self._setup_wave()
        bad = self.root / "docs" / "waves" / "bulk-wave" / "ch1xx-feat first.md"
        bad.write_bytes(b"\x80not utf-8")

        bulk = self.srv.wf_get_change_response(self.root, wave_id="bulk-wave")
        self.assertEqual(bulk["status"], "ok")
        bulk_diagnostics = bulk.get("diagnostics") or []
        self.assertTrue(any(d["code"] == "change_doc_unreadable" for d in bulk_diagnostics))
        self.assertIn("ch1xx-feat first", " ".join(d["message"] for d in bulk_diagnostics))
        self.assertIn("UnicodeDecodeError", " ".join(d["message"] for d in bulk_diagnostics))

        single = self.srv.wf_get_change_response(self.root, change_id="ch1xx-feat first")
        self.assertEqual(single["status"], "error")
        single_messages = " ".join(d["message"] for d in single.get("diagnostics") or [])
        self.assertIn("ch1xx-feat first", single_messages)
        self.assertIn("UnicodeDecodeError", single_messages)


class UnreadableWaveRecordTests(unittest.TestCase):
    """1v0lw: an unreadable ``wave.md`` returns diagnostics at every boundary.

    Red-first record (2026-08-11, against the pre-seam code): the decode cause
    raised ``UnicodeDecodeError`` at all nine probed boundaries; the permission
    cause raised ``PermissionError`` at the two enumeration tools and
    misreported ``wave_not_found`` at the seven by-id boundaries, because the
    resolution path swallowed ``OSError`` (`_resolve_wave_md_matches` skipped
    the record; `_wave_match_payload` substituted an empty parse).  Both
    fail-open shapes are pinned here per cause, per site class.
    """

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        _make_repo(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    _WAVE_TEXT = (
        "# Wave Record\n\nOwner: Engineering\nStatus: active\n"
        "Last verified: 2026-01-01\n\nwave-id: `seam-wave`\nTitle: Seam Wave\n\n"
        "## Changes\n\nChange ID: `ch1sm-feat first`\nChange Status: `planned`\n"
    )
    _CHANGE_TEXT = (
        "# First\n\nChange ID: `ch1sm-feat first`\nChange Status: `planned`\n\n"
        "## Acceptance Criteria\n\n- [ ] AC-1: the seam holds\n\n"
        "## Tasks\n\n- [ ] Route the read\n"
    )

    def _fresh_root(self):
        """Start a clean repo for one subTest without re-entering setUp().

        Same rationale as ``BulkWaveGetChangeTests._fresh_root``: re-calling
        setUp() rebinds self.tmp and leaks the earlier TemporaryDirectory.
        """
        self.tmp.cleanup()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        _make_repo(self.root)

    def _make_unreadable(self, path, mode):
        """Make `path` unreadable by `mode`; restore permissions at test end."""
        if mode == "decode":
            path.write_bytes(b"\xff\xfe not valid utf-8 \xff")
        else:
            if not path.exists():
                path.write_text("# placeholder\n", encoding="utf-8")
            os.chmod(path, 0)
            self.addCleanup(
                lambda: path.exists() and os.chmod(path, stat.S_IRUSR | stat.S_IWUSR))
        return path

    def _wave(self, name="seam-wave"):
        """A readable governed wave with one admitted change carrying AC and task items."""
        wave_dir = self.root / "docs" / "waves" / name
        wave_dir.mkdir(parents=True, exist_ok=True)
        wave_md = wave_dir / "wave.md"
        wave_md.write_text(
            self._WAVE_TEXT.replace("seam-wave", name), encoding="utf-8")
        (wave_dir / "ch1sm-feat first.md").write_text(
            self._CHANGE_TEXT, encoding="utf-8")
        return wave_md

    def _decision_calls(self):
        """The seven by-id boundaries of the nine-boundary matrix.

        ``wf_mark_ac`` and ``wf_mark_task`` are each probed at their own
        boundary through the shared responder's ``target_section`` variants.
        """
        return {
            "get_change": lambda: self.srv.wf_get_change_response(
                self.root, wave_id="seam-wave"),
            "prepare": lambda: self.srv.wf_prepare_wave_response(
                self.root, wave_id="seam-wave", mode="dry_run"),
            "implement": lambda: self.srv.wf_implement_wave_response(
                self.root, wave_id="seam-wave", mode="dry_run"),
            "close": lambda: self.srv.wf_close_wave_response(
                self.root, "seam-wave", mode="dry_run"),
            "pause": lambda: self.srv.wf_pause_wave_response(
                self.root, "seam-wave", mode="dry_run"),
            "mark_ac": lambda: self.srv._mark_change_item_response(
                self.root, "seam-wave", "ch1sm-feat first", "AC-1", "x",
                target_section="Acceptance Criteria", mode="dry_run"),
            "mark_task": lambda: self.srv._mark_change_item_response(
                self.root, "seam-wave", "ch1sm-feat first", "Route the read", "x",
                target_section="Tasks", mode="dry_run"),
        }

    def test_decision_tools_refuse_on_an_unreadable_wave_record(self):
        """1v0lw AC-2/AC-3/AC-5 at the seven by-id boundaries, both causes.

        AC-5 mutation kills, named per boundary: restoring a raw read at any
        of these boundaries resurfaces as a crash on the decode cause (the
        call raises ``UnicodeDecodeError`` again and the try/fail below
        reports it) or as the ``wave_not_found`` misdirection on the
        permission cause (the resolution skip returns and the exact-code
        assertions below catch the regression).  ``wf_mark_ac`` and
        ``wf_mark_task`` are covered at their own boundaries.
        """
        for cause in ("decode", "permission"):
            for name, call in self._decision_calls().items():
                with self.subTest(cause=cause, tool=name):
                    self._fresh_root()
                    self._wave()
                    self._make_unreadable(
                        self.root / "docs" / "waves" / "seam-wave" / "wave.md",
                        cause)
                    try:
                        resp = call()
                    except (OSError, UnicodeError) as exc:
                        self.fail(
                            f"{name} must report the unreadable wave record, "
                            f"not raise: {exc!r}")
                    self.assertEqual(resp["status"], "error", (name, cause, resp))
                    codes = [d["code"] for d in resp.get("diagnostics") or []]
                    self.assertIn(
                        "wave_record_unreadable", codes, (name, cause, codes))
                    self.assertNotIn(
                        "wave_not_found", codes,
                        f"{name}/{cause}: a read failure reported as a "
                        "nonexistent wave sends the operator to the wrong "
                        "recovery (the AC-9 misdirection)")
                    message = " ".join(
                        d["message"] for d in resp["diagnostics"]
                        if d["code"] == "wave_record_unreadable")
                    self.assertIn(
                        "wave.md", message,
                        "the diagnostic must name the wave record")
                    self.assertIn("seam-wave", message)
                    self.assertIn(
                        "Error", message,
                        "AC-3: the diagnostic must carry the CAUSE (exception "
                        "type), not the record name alone")
                    # Reach-guard: the exact diagnostic fired above, so the
                    # leak assertion cannot pass vacuously (1uu9z pattern).
                    blob = json.dumps(resp.get("diagnostics") or []) + json.dumps(
                        resp.get("data") or {})
                    self.assertNotIn(
                        str(self.root), blob,
                        f"{name}/{cause}: a read-failure message leaked the "
                        "absolute repository path")

    def _mutation_calls(self):
        """The census-added mutation boundaries beyond the probed nine."""
        return {
            "add_change": lambda: self.srv.wf_add_change_response(
                self.root, wave_id="seam-wave", change_id="chadd-feat plan",
                mode="dry_run"),
            "remove_change": lambda: self.srv.wf_remove_change_response(
                self.root, wave_id="seam-wave", change_id="ch1sm-feat first",
                mode="dry_run"),
            "review_event": lambda: self.srv.wf_review_event_response(
                self.root, "seam-wave", "approval", "tester", "ctx-1",
                mode="dry_run", signoff_key="code-reviewer",
                approval_phase="delivery"),
            "review_wave": lambda: self.srv.wf_review_wave_response(
                self.root, "seam-wave", phase="prepare"),
            "reopen": lambda: self.srv.wf_reopen_wave_response(
                self.root, "seam-wave"),
        }

    def test_census_added_mutation_tools_refuse_on_an_unreadable_wave_record(self):
        """1v0lw census extension: the six raising tools beyond the probed nine.

        Red-first: decode raised out of every one of these; permission
        misreported ``wave_not_found`` (``create_wave`` raised
        ``PermissionError`` instead, covered by its own test below).
        """
        for cause in ("decode", "permission"):
            for name, call in self._mutation_calls().items():
                with self.subTest(cause=cause, tool=name):
                    self._fresh_root()
                    self._wave()
                    plans = self.root / "docs" / "plans"
                    plans.mkdir(parents=True, exist_ok=True)
                    (plans / "chadd-feat plan.md").write_text(
                        "# Plan\n\nChange ID: `chadd-feat plan`\n"
                        "Change Status: `planned`\n", encoding="utf-8")
                    self._make_unreadable(
                        self.root / "docs" / "waves" / "seam-wave" / "wave.md",
                        cause)
                    try:
                        resp = call()
                    except (OSError, UnicodeError) as exc:
                        self.fail(
                            f"{name} must report the unreadable wave record, "
                            f"not raise: {exc!r}")
                    self.assertEqual(resp["status"], "error", (name, cause, resp))
                    codes = [d["code"] for d in resp.get("diagnostics") or []]
                    self.assertIn(
                        "wave_record_unreadable", codes, (name, cause, codes))
                    self.assertNotIn("wave_not_found", codes, (name, cause))
                    message = " ".join(
                        d["message"] for d in resp["diagnostics"]
                        if d["code"] == "wave_record_unreadable")
                    self.assertIn("wave.md", message)
                    self.assertIn("Error", message)
                    blob = json.dumps(resp.get("diagnostics") or []) + json.dumps(
                        resp.get("data") or {})
                    self.assertNotIn(str(self.root), blob, (name, cause))

    def test_create_wave_refuses_when_the_existing_record_is_unreadable(self):
        """1v0lw census extension at ``create_wave``'s existing-record read.

        The minted id is pinned by patching the lifecycle module (each real
        mint advances, so a dry-run preview cannot place the fixture), which
        lets the fixture plant the unreadable record exactly where the
        create-mode read (`existing_text = ...`) will find it.
        """
        for cause in ("decode", "permission"):
            with self.subTest(cause=cause):
                self._fresh_root()
                wave_md = (self.root / "docs" / "waves"
                           / "seamzz seam-probe" / "wave.md")
                wave_md.parent.mkdir(parents=True, exist_ok=True)
                self._make_unreadable(wave_md, cause)
                try:
                    with patch.object(self.srv, "_lifecycle_module") as lifecycle:
                        lifecycle.return_value.build_id.return_value = (
                            "seamzz seam-probe")
                        resp = self.srv.wf_create_wave_response(
                            self.root, "seam-probe", mode="create")
                except (OSError, UnicodeError) as exc:
                    self.fail(
                        "create_wave must refuse over an unreadable existing "
                        f"record, not raise: {exc!r}")
                self.assertEqual(resp["status"], "error", resp)
                codes = [d["code"] for d in resp.get("diagnostics") or []]
                self.assertIn("wave_record_unreadable", codes, codes)
                message = " ".join(
                    d["message"] for d in resp["diagnostics"]
                    if d["code"] == "wave_record_unreadable")
                self.assertIn("Error", message)
                self.assertNotIn(str(self.root), message)

    def test_enumeration_tools_degrade_per_entry_on_an_unreadable_wave_record(self):
        """1v0lw AC-4: the recovery tools recover; readable siblings survive.

        Red-first: both tools raised ``UnicodeDecodeError`` on decode and
        ``PermissionError`` on permission (their read path has no handler at
        all), taking the readable sibling down with the broken record.
        """
        for cause in ("decode", "permission"):
            for name in ("list_waves", "current_wave"):
                with self.subTest(cause=cause, tool=name):
                    self._fresh_root()
                    self._wave()
                    sibling = self.root / "docs" / "waves" / "aa-broken"
                    sibling.mkdir(parents=True, exist_ok=True)
                    self._make_unreadable(sibling / "wave.md", cause)
                    fn = (self.srv.wf_list_waves_response
                          if name == "list_waves"
                          else self.srv.wf_current_wave_response)
                    try:
                        resp = fn(self.root)
                    except (OSError, UnicodeError) as exc:
                        self.fail(
                            f"{name} must degrade per entry, not raise: {exc!r}")
                    self.assertEqual(resp["status"], "ok", (name, cause, resp))
                    waves = resp["data"]["waves"]
                    ids = [w.get("wave_id") for w in waves]
                    self.assertIn(
                        "seam-wave", ids,
                        "readable siblings must still be returned")
                    self.assertIn(
                        "aa-broken", ids,
                        "the unreadable wave must be LISTED with its error, "
                        "not silently dropped")
                    bad = next(w for w in waves if w["wave_id"] == "aa-broken")
                    self.assertIn("Error", bad["read_error"])
                    codes = [d["code"] for d in resp.get("diagnostics") or []]
                    self.assertIn("wave_record_unreadable", codes, (name, codes))
                    # Reach-guard held (entry + diagnostic asserted above).
                    # Readable sibling records keep their historical absolute
                    # `path`, so the leak assertion covers the NEW surfaces:
                    # the degraded entry and the diagnostics.
                    blob = json.dumps(resp.get("diagnostics") or []) + json.dumps(bad)
                    self.assertNotIn(str(self.root), blob, (name, cause))

    def test_current_wave_surfaces_the_only_wave_when_it_is_unreadable(self):
        """1v0lw AC-4 corner: unreadable-only-wave must not become 'no wave'.

        A silent ``no_active_wave`` here is the misdirection shape relocated:
        the operator's first diagnostic tool would deny the wave exists.
        """
        for cause in ("decode", "permission"):
            with self.subTest(cause=cause):
                self._fresh_root()
                wave_dir = self.root / "docs" / "waves" / "only-wave"
                wave_dir.mkdir(parents=True, exist_ok=True)
                self._make_unreadable(wave_dir / "wave.md", cause)
                try:
                    resp = self.srv.wf_current_wave_response(self.root)
                except (OSError, UnicodeError) as exc:
                    self.fail(f"wf_current_wave must degrade, not raise: {exc!r}")
                self.assertEqual(resp["status"], "ok", resp)
                waves = resp["data"]["waves"]
                self.assertTrue(
                    waves,
                    "the unreadable wave must be surfaced with its read_error, "
                    "not degraded to a silent 'no current wave'")
                self.assertEqual(waves[0]["wave_id"], "only-wave")
                self.assertIn("Error", waves[0]["read_error"])
                codes = [d["code"] for d in resp.get("diagnostics") or []]
                self.assertIn("wave_record_unreadable", codes, codes)
                self.assertNotIn(
                    "no_active_wave", codes,
                    "reporting 'no active wave' over a read failure is the "
                    "fail-open shape this test pins")

    def test_an_unreadable_sibling_does_not_contaminate_by_id_resolution(self):
        """1v0lw Requirement 5: sibling contamination, both causes.

        Red-first: an undecodable NON-matching sibling crashed by-id
        resolution of a READABLE wave (`_resolve_wave_md_matches` parses every
        record before token-matching); the permission cause resolved but
        silently hid the sibling.  Green: resolution succeeds AND the skipped
        sibling's diagnostic is surfaced alongside the successful result.
        """
        for cause in ("decode", "permission"):
            with self.subTest(cause=cause):
                self._fresh_root()
                self._wave()
                sibling = self.root / "docs" / "waves" / "aa-broken"
                sibling.mkdir(parents=True, exist_ok=True)
                self._make_unreadable(sibling / "wave.md", cause)
                try:
                    resp = self.srv.wf_get_change_response(
                        self.root, wave_id="seam-wave")
                except (OSError, UnicodeError) as exc:
                    self.fail(
                        "an unreadable SIBLING must not break resolution of a "
                        f"readable wave: {exc!r}")
                self.assertEqual(resp["status"], "ok", resp)
                self.assertEqual(resp["data"]["wave_id"], "seam-wave")
                ids = [c["id"] for c in resp["data"]["changes"]]
                self.assertIn("ch1sm-feat first", ids)
                codes = [d["code"] for d in resp.get("diagnostics") or []]
                self.assertIn(
                    "wave_record_unreadable", codes,
                    "the skipped unreadable sibling must be surfaced alongside "
                    "the successful result, not silently hidden")
                message = " ".join(
                    d["message"] for d in resp["diagnostics"]
                    if d["code"] == "wave_record_unreadable")
                self.assertIn("aa-broken", message)
                self.assertNotIn(str(self.root), message)

    def test_zero_match_resolution_with_unreadable_candidates_is_not_wave_not_found(self):
        """1v0lw AC-9: the renamed-dir evasion class, both causes.

        The requested id may live INSIDE the unreadable record (wave-id and
        dirname can diverge), so zero readable matches plus a skipped
        unreadable candidate is a read failure, never a missing wave.
        Red-first: permission yielded bare ``wave_not_found``; decode raised.
        """
        for cause in ("decode", "permission"):
            with self.subTest(cause=cause):
                self._fresh_root()
                renamed = self.root / "docs" / "waves" / "renamed-dir"
                renamed.mkdir(parents=True, exist_ok=True)
                self._make_unreadable(renamed / "wave.md", cause)
                try:
                    resp = self.srv.wf_prepare_wave_response(
                        self.root, wave_id="mystery-wave", mode="dry_run")
                except (OSError, UnicodeError) as exc:
                    self.fail(f"prepare must report, not raise: {exc!r}")
                self.assertEqual(resp["status"], "error", resp)
                codes = [d["code"] for d in resp.get("diagnostics") or []]
                self.assertIn(
                    "wave_record_unreadable", codes,
                    "zero matches with a skipped unreadable candidate is a "
                    "read failure, not a missing wave")
                self.assertNotIn("wave_not_found", codes, codes)
                message = " ".join(
                    d["message"] for d in resp["diagnostics"]
                    if d["code"] == "wave_record_unreadable")
                self.assertIn(
                    "renamed-dir", message,
                    "the skipped unreadable candidate must be listed")
                self.assertNotIn(str(self.root), message)

    def test_a_readable_wave_record_is_unaffected_by_the_seam(self):
        """1v0lw AC-6 durable half: ok status, zero read diagnostics, determinism.

        The executed before/after byte comparison across the touched tools is
        recorded in the change doc's Progress Log; what this holds durably is
        the regression invariant for a normally-decoding record.
        """
        self._wave()
        surfaces = {
            "current_wave": lambda: self.srv.wf_current_wave_response(self.root),
            "list_waves": lambda: self.srv.wf_list_waves_response(self.root),
            "get_change": lambda: self.srv.wf_get_change_response(
                self.root, wave_id="seam-wave"),
            "pause": lambda: self.srv.wf_pause_wave_response(
                self.root, "seam-wave", mode="dry_run"),
            "mark_ac": lambda: self.srv._mark_change_item_response(
                self.root, "seam-wave", "ch1sm-feat first", "AC-1", "x",
                target_section="Acceptance Criteria", mode="dry_run"),
            "mark_task": lambda: self.srv._mark_change_item_response(
                self.root, "seam-wave", "ch1sm-feat first", "Route the read",
                "x", target_section="Tasks", mode="dry_run"),
        }
        for name, call in surfaces.items():
            with self.subTest(surface=name):
                first, second = call(), call()
                # wf_pause_wave reports its preview mode as the envelope
                # status; every other surface here answers "ok".
                expected_status = "dry_run" if name == "pause" else "ok"
                self.assertEqual(first["status"], expected_status, (name, first))
                codes = [d.get("code") for d in first.get("diagnostics") or []]
                self.assertNotIn("wave_record_unreadable", codes, name)
                self.assertEqual(
                    first["data"], second["data"],
                    f"{name}: responses for a readable record must be "
                    "deterministic across calls")


class WaveRecordReadSeamCensusTests(unittest.TestCase):
    """1v0lw residue census: no ``wave.md`` read outside the read seam.

    Keyed by RESOLVED TARGET, not receiver name (the receiver-name census key
    missed ``contained_wave.read_text`` in ``_publish_prepare_policy_state``):
    a ``.read_text`` call is a wave-record read when its receiver expression
    contains the ``wave.md`` literal, uses a conventional wave-record binder
    name, or is bound from a wave-path producer
    (``_find_wave_md`` / ``_contained_wave_review_paths``).
    """

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    # Names conventionally bound to a wave record path in this module.
    _WAVE_RECEIVER_NAMES = {"wave_md", "wave_path", "wave_file", "contained_wave"}
    # Callables whose return value is a wave record path (element 0 for the
    # tuple-returning producer).
    _WAVE_PATH_PRODUCERS = {"_find_wave_md", "_find_wave_md_detailed", "_contained_wave_review_paths"}
    _ALLOWED_READERS = {
        # The seam itself: the sole raw-read boundary for wave records.
        "_read_wave_record_text",
        # MCP resource reader; resource surfaces are out of scope per the
        # 1v0lw change doc Scope ("Reads of prompts, seeds, handoff, and MCP
        # resources").  Listed so an in-scope reader can never hide behind
        # the resource exemption unreviewed.
        "_validated_wave_markdown",
    }

    def test_every_wave_record_read_routes_through_the_seam(self):
        module = ast.Module(body=[
            node
            for owner in (self.srv, self.srv.lifecycle_gates, self.srv.lifecycle_gate_support)
            for node in ast.parse(Path(owner.__file__).read_text(encoding="utf-8")).body
        ], type_ignores=[])
        parents = {}
        for node in ast.walk(module):
            for child in ast.iter_child_nodes(node):
                parents[child] = node

        def enclosing_function(node):
            cur = node
            while cur in parents:
                cur = parents[cur]
                if isinstance(cur, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    return cur
            return None

        def bound_names(value, targets):
            """Names bound to the wave-path half of an assignment/loop target."""
            names = set()
            for tgt in targets:
                if (isinstance(tgt, ast.Tuple) and tgt.elts
                        and isinstance(value, ast.Call)):
                    called = (getattr(value.func, "id", None)
                              or getattr(value.func, "attr", None))
                    if called == "_contained_wave_review_paths":
                        # (wave_md, events_path): only element 0 is the record.
                        first = tgt.elts[0]
                        names.update(
                            n.id for n in ast.walk(first)
                            if isinstance(n, ast.Name))
                        continue
                names.update(
                    n.id for n in ast.walk(tgt) if isinstance(n, ast.Name))
            return names

        def resolves_to_wave_record(call):
            recv = call.func.value
            recv_src = ast.unparse(recv)
            if "wave.md" in recv_src:
                return True
            recv_names = {
                n.id for n in ast.walk(recv) if isinstance(n, ast.Name)}
            if recv_names & self._WAVE_RECEIVER_NAMES:
                return True
            fn = enclosing_function(call)
            if fn is None or not recv_names:
                return False
            for node in ast.walk(fn):
                if isinstance(node, ast.Assign):
                    value, targets = node.value, node.targets
                elif isinstance(node, ast.For):
                    value, targets = node.iter, (node.target,)
                elif isinstance(node, ast.comprehension):
                    value, targets = node.iter, (node.target,)
                else:
                    continue
                if not (bound_names(value, targets) & recv_names):
                    continue
                if "wave.md" in ast.unparse(value):
                    return True
                called = {
                    (getattr(n.func, "id", None) or getattr(n.func, "attr", None))
                    for n in ast.walk(value) if isinstance(n, ast.Call)
                }
                if called & self._WAVE_PATH_PRODUCERS:
                    return True
            return False

        offenders = []
        flagged = 0
        for node in ast.walk(module):
            if not (isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "read_text"):
                continue
            if not resolves_to_wave_record(node):
                continue
            flagged += 1
            fn = enclosing_function(node)
            fn_name = fn.name if fn is not None else "<module>"
            if fn_name not in self._ALLOWED_READERS:
                offenders.append(
                    f"line {node.lineno} in {fn_name}: "
                    f"{ast.unparse(node.func.value)}.read_text(...)")
        self.assertTrue(
            flagged,
            "the census detector flagged no wave-record reads at all; the "
            "detector itself broke (the seam's own read must be flagged)")
        self.assertEqual(
            offenders, [],
            "every wave.md read must route through _read_wave_record_text "
            "(the 1v0lw seam); raw reads found: " + "; ".join(offenders))


class HandoffToolTests(unittest.TestCase):
    """Item 4: wf_get_handoff and wf_set_handoff."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        _make_repo(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def test_get_handoff_not_found(self):
        resp = self.srv.wf_get_handoff_response(self.root)
        self.assertEqual(resp["status"], "ok")
        self.assertIsNone(resp["data"]["content"])

    def test_set_handoff_creates_file(self):
        resp = self.srv.wf_set_handoff_response(self.root, content="# Session Handoff\n\nActive wave: test")
        self.assertEqual(resp["status"], "ok")
        self.assertTrue(resp["data"]["written"])
        handoff = self.root / "docs" / "agents" / "session-handoff.md"
        self.assertTrue(handoff.exists())

    def test_get_handoff_after_set(self):
        self.srv.wf_set_handoff_response(self.root, content="# Handoff\n\nDone.")
        resp = self.srv.wf_get_handoff_response(self.root)
        self.assertEqual(resp["status"], "ok")
        self.assertIn("Done.", resp["data"]["content"])

    def test_set_handoff_size_field(self):
        content = "# Session Handoff\n\nSome state."
        resp = self.srv.wf_set_handoff_response(self.root, content=content)
        self.assertEqual(resp["data"]["size"], len(content))

    def test_get_handoff_path_field(self):
        resp = self.srv.wf_get_handoff_response(self.root)
        self.assertEqual(resp["data"]["path"], "docs/agents/session-handoff.md")

    def test_handoff_tools_registered(self):
        try:
            mcp = load_thin_runner().build_server(self.root)
        except ImportError:
            self.skipTest("mcp package not installed")
        names = self.srv._registered_mcp_tool_names(mcp)
        self.assertIn("wf_get_handoff", names)
        self.assertIn("wf_set_handoff", names)


class WavePrepareACPriorityWarningTests(unittest.TestCase):
    """Item 6: wf_prepare_wave warns (non-blocking) when AC priority rows are unpopulated."""

    _VALID_LINT = {"passed": True, "errors": [], "warnings": [], "output": ""}

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def _make_wave_with_change(self, ac_text: str) -> Path:
        wave_dir = self.root / "docs" / "waves" / "ac-wave"
        wave_dir.mkdir(parents=True, exist_ok=True)
        (wave_dir / "wave.md").write_text(
            "# Wave Record\n\nOwner: Engineering\nStatus: planned\nLast verified: 2026-01-01\n\nwave-id: `ac-wave`\nTitle: AC Wave\n\n## Changes\n\nChange ID: `acx01-feat ac-test`\nChange Status: `planned`\n\n## Wave Summary\n\nTest wave.\n\n## Journal Watchpoints\n\n- Watch this.\n",
            encoding="utf-8",
        )
        change_doc = wave_dir / "acx01-feat ac-test.md"
        change_doc.write_text(
            "# AC Test\n\nChange ID: `acx01-feat ac-test`\nChange Status: `planned`\nOwner: Engineering\nWave: `ac-wave`\n\n"
            "## Rationale\n\nNeeded.\n\n## Requirements\n\n1. Do the thing.\n\n## Scope\n\nIn scope.\n\n"
            "## Acceptance Criteria\n\n- AC-1: Does the thing.\n\n## Tasks\n\n- Implement it.\n\n"
            f"## AC Priority\n\n| AC | Priority | Rationale |\n| -- | -------- | --------- |\n{ac_text}\n",
            encoding="utf-8",
        )
        return wave_dir

    def test_placeholder_ac_produces_advisory(self):
        self._make_wave_with_change(
            "| AC-1 | required / important / nice-to-have / not-this-scope | placeholder |"
        )
        with patch.object(self.srv, "run_validate", return_value=self._VALID_LINT):
            resp = self.srv.wf_prepare_wave_response(self.root, wave_id="ac-wave", mode="dry_run")
        # Must not be an error (advisory only)
        self.assertNotEqual(resp["status"], "error")
        codes = [d.get("code") for d in (resp.get("diagnostics") or [])]
        self.assertIn("ac_priority_unpopulated", codes)

    def test_scaffold_directs_a_plan_time_fill_and_keeps_the_backstop(self):
        """AC-8: the placeholder no longer instructs a Prepare-time fill.

        The advisory keys on the placeholder priority ROW, not on this prose, so
        the second half proves the instruction change did not trade one churn
        source for a missing gate.
        """

        template = self.srv._default_template()
        self.assertIn("## AC Priority", template)
        self.assertNotIn("Populated at Prepare wave", template)
        self.assertIn("at plan time", template)
        self.assertIn("before the prepare council runs", template)

        self._make_wave_with_change(
            "| AC-1 | required / important / nice-to-have / not-this-scope | placeholder |"
        )
        with patch.object(self.srv, "run_validate", return_value=self._VALID_LINT):
            resp = self.srv.wf_prepare_wave_response(self.root, wave_id="ac-wave", mode="dry_run")
        codes = [d.get("code") for d in (resp.get("diagnostics") or [])]
        self.assertIn("ac_priority_unpopulated", codes)

    def test_populated_ac_no_advisory(self):
        self._make_wave_with_change(
            "| AC-1 | required | Core feature. |"
        )
        with patch.object(self.srv, "run_validate", return_value=self._VALID_LINT):
            resp = self.srv.wf_prepare_wave_response(self.root, wave_id="ac-wave", mode="dry_run")
        codes = [d.get("code") for d in (resp.get("diagnostics") or [])]
        self.assertNotIn("ac_priority_unpopulated", codes)

    def test_placeholder_ac_does_not_block_prepare(self):
        """prepare must still succeed (dry_run) even with unpopulated AC rows."""
        self._make_wave_with_change(
            "| AC-1 | required / important / nice-to-have / not-this-scope | placeholder |"
        )
        with patch.object(self.srv, "run_validate", return_value=self._VALID_LINT):
            resp = self.srv.wf_prepare_wave_response(self.root, wave_id="ac-wave", mode="dry_run")
        self.assertIn(resp["status"], ("dry_run", "ok"))


class WavePauseStatusTransitionTests(unittest.TestCase):
    """12as6: wf_pause_wave transitions wave.md Status active→paused and records transition."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))
        (self.root / "docs" / "agents" / "journals").mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self.tmp.cleanup()

    def _make_wave(self, wave_id: str, status: str) -> Path:
        wave_dir = self.root / "docs" / "waves" / wave_id
        wave_dir.mkdir(parents=True, exist_ok=True)
        wave_md = wave_dir / "wave.md"
        wave_md.write_text(
            "# Wave Record\n\n"
            "Owner: Engineering\n"
            f"Status: {status}\n"
            "Last verified: 2026-05-01\n\n"
            f"wave-id: `{wave_id}`\n"
            "Title: Test Wave\n\n"
            "## Changes\n\n"
            "## Wave Summary\n\nTest.\n\n"
            "## Journal Watchpoints\n\n- Test.\n\n"
            "## Dependencies\n\n- None.\n",
            encoding="utf-8",
        )
        return wave_md

    def test_wf_pause_wave_transitions_active_to_paused(self):
        wave_md = self._make_wave("1200a active-wave", "active")
        result = self.srv.wf_pause_wave_response(self.root, "1200a active-wave", mode="create")
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["data"]["status_transition"], {"from": "active", "to": "paused"})
        text = wave_md.read_text(encoding="utf-8")
        self.assertIn("Status: paused", text)
        self.assertNotIn("Status: active", text)

    def test_wf_pause_wave_idempotent_on_paused(self):
        wave_md = self._make_wave("1200a paused-wave", "paused")
        result = self.srv.wf_pause_wave_response(self.root, "1200a paused-wave", mode="create")
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["data"]["status_transition"], {"from": "paused", "to": "paused"})
        text = wave_md.read_text(encoding="utf-8")
        self.assertIn("Status: paused", text)
        # Handoff still written
        self.assertTrue((self.root / "docs" / "agents" / "session-handoff.md").exists())

    def test_wf_pause_wave_advisory_on_planned(self):
        self._make_wave("1200a planned-wave", "planned")
        result = self.srv.wf_pause_wave_response(self.root, "1200a planned-wave", mode="create")
        self.assertEqual(result["status"], "ok")
        codes = [d.get("code") for d in result.get("diagnostics", [])]
        self.assertIn("pause_on_non_active_wave", codes)
        self.assertEqual(result["data"]["status_transition"]["to"], "planned")

    def test_wf_pause_wave_dry_run_reports_transition(self):
        wave_md = self._make_wave("1200a dry-run-wave", "active")
        original_text = wave_md.read_text(encoding="utf-8")
        result = self.srv.wf_pause_wave_response(self.root, "1200a dry-run-wave", mode="dry_run")
        self.assertEqual(result["status"], "dry_run")
        self.assertEqual(result["data"]["status_transition"], {"from": "active", "to": "paused"})
        # wave.md untouched
        self.assertEqual(wave_md.read_text(encoding="utf-8"), original_text)


class WavePrepareSingleActiveGuardTests(unittest.TestCase):
    """12as6: wf_prepare_wave blocks when another wave is active; allows self and post-pause prepare."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))
        (self.root / "docs" / "agents" / "journals").mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self.tmp.cleanup()

    def _make_wave_with_change(self, slug: str, status: str = "planned") -> tuple[str, str]:
        """Create a wave (fully scaffolded via scripts) with one admitted change."""
        wave_result = self.srv.wf_create_wave_response(self.root, slug, mode="create")
        wave_id = wave_result["data"]["wave_id"]
        change = self.srv.new_change(self.root, "feat", f"{slug}-change")
        change_id = change["id"]
        self.srv.wf_add_change_response(self.root, wave_id, change_id, mode="create")
        wave_md = self.root / "docs" / "waves" / wave_id / "wave.md"
        text = wave_md.read_text(encoding="utf-8")
        if status != "planned":
            text = text.replace("Status: planned", f"Status: {status}")
            wave_md.write_text(text, encoding="utf-8")
        # Add journal reference so lint passes
        journal = self.root / "docs" / "agents" / "journals" / "wave-coordinator.md"
        prior = journal.read_text(encoding="utf-8") if journal.exists() else "# Journal\n"
        journal.write_text(prior + f"\nwave-id: `{wave_id}`\n", encoding="utf-8")
        return wave_id, change_id

    def _add_council_verdict(self, wave_id: str) -> None:
        """Append a prepare-council verdict to the wave's ## Review Checkpoints section."""
        _append_review_run(self.root, wave_id, kind="readiness")
        _append_typed_approval(
            self.root,
            wave_id,
            "wave-council-readiness",
            actor="wave-council",
        )
        wave_md = self.root / "docs" / "waves" / wave_id / "wave.md"
        wave_md.write_text(
            wave_md.read_text(encoding="utf-8")
            + f"\n## Review Checkpoints\n\n{_prepare_council_verdict_line()}\n",
            encoding="utf-8",
        )

    def test_wf_prepare_wave_guards_when_another_wave_active_create(self):
        active_wave, _ = self._make_wave_with_change("active-one", status="active")
        target_wave, _ = self._make_wave_with_change("planned-one", status="planned")
        result = self.srv.wf_prepare_wave_response(self.root, target_wave, mode="create")
        self.assertEqual(result["status"], "error")
        codes = [d.get("code") for d in result.get("diagnostics", [])]
        self.assertIn("another_wave_active", codes)
        self.assertEqual(result["data"].get("active_wave_id"), active_wave)
        # target wave still planned
        target_md = self.root / "docs" / "waves" / target_wave / "wave.md"
        self.assertIn("Status: planned", target_md.read_text(encoding="utf-8"))

    def test_wf_prepare_wave_dry_run_not_guarded_by_other_open_wave(self):
        """Wave 1p45l (AC-6): dry_run is read-only and never takes the single-OPEN slot —
        it is not blocked when another wave is OPEN."""
        self._make_wave_with_change("active-two", status="active")
        target_wave, _ = self._make_wave_with_change("planned-two", status="planned")
        with patch.object(self.srv, "run_garden", return_value={"passed": True, "files_updated": 0, "updated": [], "output": ""}):
            with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
                result = self.srv.wf_prepare_wave_response(self.root, target_wave, mode="dry_run")
        codes = [d.get("code") for d in result.get("diagnostics", [])]
        self.assertNotIn("another_wave_active", codes)
        self.assertEqual(result["data"]["mode"], "dry_run")

    def test_wf_prepare_wave_self_reprepare_allowed(self):
        wave_id, _ = self._make_wave_with_change("self-prep", status="active")
        # Re-running prepare on the currently active target must not trigger the guard.
        result = self.srv.wf_prepare_wave_response(self.root, wave_id, mode="create")
        codes = [d.get("code") for d in result.get("diagnostics", [])]
        self.assertNotIn("another_wave_active", codes)

    def test_wf_prepare_wave_another_wave_active_envelope_shape(self):
        active_wave, _ = self._make_wave_with_change("env-active", status="active")
        target_wave, _ = self._make_wave_with_change("env-target", status="planned")
        result = self.srv.wf_prepare_wave_response(self.root, target_wave, mode="create")
        self.assertEqual(result["status"], "error")
        self.assertIn("active_wave_id", result["data"])
        self.assertIn("active_wave_path", result["data"])
        self.assertEqual(result["data"]["active_wave_id"], active_wave)
        # Recovery now offers `ready` — ready the target without opening it (wave 1p45l)
        self.assertIn("mode='ready'", result.get("usage", ""))
        recovery_tools = [t for d in result.get("diagnostics", []) if d.get("code") == "another_wave_active" for t in d.get("recovery_tools", [])]
        self.assertIn("wf_prepare_wave", recovery_tools)
        self.assertIn("wf_pause_wave", recovery_tools)

    def test_wf_prepare_wave_after_pause_succeeds(self):
        active_wave, _ = self._make_wave_with_change("ctx-switch-active", status="active")
        target_wave, _ = self._make_wave_with_change("ctx-switch-target", status="planned")
        self._add_council_verdict(target_wave)
        # Pause active wave
        pause_result = self.srv.wf_pause_wave_response(self.root, active_wave, mode="create")
        self.assertEqual(pause_result["data"]["status_transition"], {"from": "active", "to": "paused"})
        # Now prepare target wave (patch lint/garden because minimal test repo isn't fully seeded)
        with patch.object(self.srv, "run_garden", return_value={"passed": True, "files_updated": 0, "updated": [], "output": ""}):
            with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
                result = self.srv.wf_prepare_wave_response(self.root, target_wave, mode="create")
        codes = [d.get("code") for d in result.get("diagnostics", [])]
        self.assertNotIn("another_wave_active", codes)
        # Target wave transitioned to active
        target_md = self.root / "docs" / "waves" / target_wave / "wave.md"
        self.assertIn("Status: active", target_md.read_text(encoding="utf-8"))

    def test_wf_prepare_wave_resumes_paused_wave(self):
        paused_wave, _ = self._make_wave_with_change("resume-target", status="paused")
        self._add_council_verdict(paused_wave)
        with patch.object(self.srv, "run_garden", return_value={"passed": True, "files_updated": 0, "updated": [], "output": ""}):
            with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
                result = self.srv.wf_prepare_wave_response(self.root, paused_wave, mode="create")
        codes = [d.get("code") for d in result.get("diagnostics", [])]
        self.assertNotIn("another_wave_active", codes)
        wave_md = self.root / "docs" / "waves" / paused_wave / "wave.md"
        self.assertIn("Status: active", wave_md.read_text(encoding="utf-8"))

    def test_wf_prepare_wave_ready_succeeds_while_other_wave_open_and_stays_planned(self):
        """Wave 1p45l (AC-1/AC-2): `ready` runs full readiness WITHOUT activating — it
        succeeds while another wave is OPEN and leaves the target `planned` (readied)."""
        self._make_wave_with_change("ready-active", status="active")
        target_wave, _ = self._make_wave_with_change("ready-target", status="planned")
        self._add_council_verdict(target_wave)
        with patch.object(self.srv, "run_garden", return_value={"passed": True, "files_updated": 0, "updated": [], "output": ""}):
            with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
                result = self.srv.wf_prepare_wave_response(self.root, target_wave, mode="ready")
        codes = [d.get("code") for d in result.get("diagnostics", [])]
        self.assertNotIn("another_wave_active", codes)
        self.assertEqual(result["status"], "ok")
        self.assertTrue(result["data"].get("readied"))
        target_md = self.root / "docs" / "waves" / target_wave / "wave.md"
        self.assertIn("Status: planned", target_md.read_text(encoding="utf-8"))

    def test_wf_implement_wave_opens_readied_planned_wave(self):
        """Wave 1p45l (AC-3): wf_implement_wave accepts a readied `planned` wave and, when no
        other wave is OPEN, transitions it to `implementing`."""
        target_wave, _ = self._make_wave_with_change("impl-readied", status="planned")
        self._add_council_verdict(target_wave)
        result = self.srv.wf_implement_wave_response(self.root, target_wave, mode="create")
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["data"]["status_transition"], {"from": "planned", "to": "implementing"})
        wave_md = self.root / "docs" / "waves" / target_wave / "wave.md"
        self.assertIn("Status: implementing", wave_md.read_text(encoding="utf-8"))

    def test_wf_implement_wave_guarded_when_another_wave_open(self):
        """Wave 1p45l (AC-4): the single-OPEN guard now lives at the activation step —
        wf_implement_wave blocks with another_wave_active when another wave is OPEN, leaving the
        target unopened."""
        self._make_wave_with_change("impl-active", status="active")
        target_wave, _ = self._make_wave_with_change("impl-target", status="planned")
        self._add_council_verdict(target_wave)
        result = self.srv.wf_implement_wave_response(self.root, target_wave, mode="create")
        self.assertEqual(result["status"], "error")
        self.assertIn("another_wave_active", [d.get("code") for d in result.get("diagnostics", [])])
        target_md = self.root / "docs" / "waves" / target_wave / "wave.md"
        self.assertIn("Status: planned", target_md.read_text(encoding="utf-8"))

    def test_wf_reopen_wave_guarded_when_another_wave_open(self):
        """Wave 1p45l (AC-9): wf_reopen_wave runs the single-OPEN guard — it blocks when another
        wave is OPEN (closing the pre-existing unguarded-reopen hole) and succeeds once the
        slot is free."""
        with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
            self._make_wave_with_change("reopen-active", status="active")
            closed_wave, _ = self._make_wave_with_change("reopen-target", status="closed")
            blocked = self.srv.wf_reopen_wave_response(self.root, closed_wave)
            self.assertEqual(blocked["status"], "error")
            self.assertIn("another_wave_active", [d.get("code") for d in blocked.get("diagnostics", [])])
            # Free the slot, then reopen succeeds (closed -> active).
            self.srv.wf_pause_wave_response(self.root, blocked["data"]["active_wave_id"], mode="create")
            ok = self.srv.wf_reopen_wave_response(self.root, closed_wave)
        self.assertEqual(ok["status"], "ok")
        self.assertIn("Status: active", (self.root / "docs" / "waves" / closed_wave / "wave.md").read_text(encoding="utf-8"))

    def test_wf_prepare_wave_aggregates_active_wave_and_lint_diagnostics(self):
        """AC-6: when another wave is active AND lint fails, both diagnostics appear."""
        self._make_wave_with_change("agg-active", status="active")
        target_wave, _ = self._make_wave_with_change("agg-target", status="planned")
        with patch.object(self.srv, "run_garden", return_value={"passed": True, "files_updated": 0, "updated": [], "output": ""}):
            with patch.object(
                self.srv,
                "run_validate",
                return_value={"passed": False, "errors": ["synthetic lint error for AC-6 aggregation test"], "warnings": [], "output": ""},
            ):
                result = self.srv.wf_prepare_wave_response(self.root, target_wave, mode="create")
        self.assertEqual(result["status"], "error")
        codes = [d.get("code") for d in result.get("diagnostics", [])]
        self.assertIn("another_wave_active", codes)
        self.assertIn("docs_lint_error", codes)

    def test_wf_prepare_wave_resume_blocked_when_other_active(self):
        self._make_wave_with_change("resume-blocker", status="active")
        paused_wave, _ = self._make_wave_with_change("resume-paused", status="paused")
        result = self.srv.wf_prepare_wave_response(self.root, paused_wave, mode="create")
        self.assertEqual(result["status"], "error")
        codes = [d.get("code") for d in result.get("diagnostics", [])]
        self.assertIn("another_wave_active", codes)
        # Paused wave still paused
        wave_md = self.root / "docs" / "waves" / paused_wave / "wave.md"
        self.assertIn("Status: paused", wave_md.read_text(encoding="utf-8"))


class WaveCurrentListEnvelopeTests(unittest.TestCase):
    """12as6: wf_current_wave returns data.waves[] with all non-closed waves, active first."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def _make_wave(self, wave_id: str, status: str) -> None:
        wave_dir = self.root / "docs" / "waves" / wave_id
        wave_dir.mkdir(parents=True, exist_ok=True)
        (wave_dir / "wave.md").write_text(
            f"# Wave Record\n\nStatus: {status}\nwave-id: `{wave_id}`\n\n## Changes\n\n",
            encoding="utf-8",
        )

    def test_wf_current_wave_returns_waves_array(self):
        self._make_wave("1200a only-planned", "planned")
        result = self.srv.wf_current_wave_response(self.root)
        self.assertEqual(result["status"], "ok")
        self.assertIn("waves", result["data"])
        self.assertNotIn("wave", result["data"])
        self.assertEqual(len(result["data"]["waves"]), 1)
        self.assertEqual(result["data"]["waves"][0]["status"], "planned")

    def test_wf_current_wave_empty_state_returns_empty_array(self):
        result = self.srv.wf_current_wave_response(self.root)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["data"]["waves"], [])
        codes = [d.get("code") for d in result.get("diagnostics", [])]
        self.assertIn("no_active_wave", codes)

    def test_wf_current_wave_orders_active_planned_paused(self):
        # Intentionally put them out of order alphabetically so the sort verifies
        self._make_wave("1200z planned-z", "planned")
        self._make_wave("1200a active-a", "active")
        self._make_wave("1200m paused-m", "paused")
        self._make_wave("1200b planned-b", "planned")
        result = self.srv.wf_current_wave_response(self.root)
        waves = result["data"]["waves"]
        statuses = [w["status"] for w in waves]
        self.assertEqual(statuses, ["active", "planned", "planned", "paused"])
        # Within status groups, lifecycle-ID (wave_id) order preserved
        planned_ids = [w["wave_id"] for w in waves if w["status"] == "planned"]
        self.assertEqual(planned_ids, sorted(planned_ids))

    def test_wf_current_wave_entry_shape(self):
        self._make_wave("1200a active-shape", "active")
        result = self.srv.wf_current_wave_response(self.root)
        entry = result["data"]["waves"][0]
        for field in ("wave_id", "status", "changes", "path", "next_action"):
            self.assertIn(field, entry)
        self.assertEqual(entry["next_action"], "implement_wave")

    def test_wf_current_wf_pause_waved_next_action_is_resume_wave(self):
        self._make_wave("1200a only-paused", "paused")
        result = self.srv.wf_current_wave_response(self.root)
        entry = result["data"]["waves"][0]
        self.assertEqual(entry["status"], "paused")
        self.assertEqual(entry["next_action"], "resume_wave")

    def test_wf_current_wave_planned_next_action_is_prepare_wave(self):
        self._make_wave("1200a only-planned", "planned")
        result = self.srv.wf_current_wave_response(self.root)
        entry = result["data"]["waves"][0]
        self.assertEqual(entry["next_action"], "prepare_wave")

    def test_wf_current_wave_skips_paused_when_filtering_active(self):
        """Paused waves appear in data.waves but do not occupy the 'active' slot."""
        self._make_wave("1200a only-paused", "paused")
        result = self.srv.wf_current_wave_response(self.root)
        waves = result["data"]["waves"]
        self.assertEqual(len(waves), 1)
        self.assertEqual(waves[0]["status"], "paused")
        # No wave has status == 'active'
        self.assertFalse(any(w["status"] == "active" for w in waves))

    def test_wf_current_wave_excludes_closed(self):
        self._make_wave("1200a closed-wave", "closed")
        self._make_wave("1200b planned-wave", "planned")
        result = self.srv.wf_current_wave_response(self.root)
        statuses = [w["status"] for w in result["data"]["waves"]]
        self.assertNotIn("closed", statuses)
        self.assertIn("planned", statuses)


class WaveAuditUnaffectedByCurrentEnvelopeTests(unittest.TestCase):
    """AC-21: wf_audit still returns the expected shape after wf_current_wave envelope change.

    wf_audit_response uses the internal current_wave() helper (unchanged singular form),
    not wf_current_wave_response, so the envelope change is not a migration target — but this
    test asserts wf_audit continues to surface the active wave via its own response shape
    so any future refactor that wires wf_audit through wf_current_wave_response can't silently
    regress.
    """

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def _make_wave(self, wave_id: str, status: str) -> None:
        wave_dir = self.root / "docs" / "waves" / wave_id
        wave_dir.mkdir(parents=True, exist_ok=True)
        (wave_dir / "wave.md").write_text(
            f"# Wave Record\n\nStatus: {status}\nwave-id: `{wave_id}`\n\n## Changes\n\n",
            encoding="utf-8",
        )

    def test_wf_audit_reports_active_wave_when_present(self):
        self._make_wave("1200a audit-active", "active")
        result = self.srv.wf_audit_response(self.root)
        self.assertEqual(result["status"], "ok")
        wave_data = result["data"]["wave"]
        self.assertEqual(wave_data.get("status"), "active")
        self.assertEqual(wave_data.get("next_action"), "implement_wave")

    def test_wf_audit_reports_requested_wave_by_prefix(self):
        self._make_wave("1200a audit-target", "planned")
        result = self.srv.wf_audit_response(self.root, wave_id="1200a")
        self.assertEqual(result["status"], "ok")
        wave_data = result["data"]["wave"]
        self.assertEqual(wave_data.get("wave_id"), "1200a audit-target")
        self.assertEqual(wave_data.get("status"), "planned")
        self.assertEqual(wave_data.get("next_action"), "prepare_wave")

    def test_wf_audit_reports_no_wave_when_only_paused(self):
        """Paused wave should not satisfy wf_audit's 'active or planned' readiness check."""
        self._make_wave("1200a audit-paused", "paused")
        result = self.srv.wf_audit_response(self.root)
        codes = [d.get("code") for d in result.get("diagnostics", [])]
        self.assertIn("no_active_wave", codes)


class WaveValidateAcceptsPausedTests(unittest.TestCase):
    """12as6: lint must accept Status: paused in wave.md."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def test_paused_status_does_not_trigger_lint_error_on_status_field(self):
        """A wave.md with Status: paused must not produce any error referencing 'paused'
        as an invalid/unknown/rejected status value.

        Catches future regressions where a validator might enumerate allowed statuses
        and forget to include 'paused'. Other lint rules (journal reference, required
        sections) may still fail for unrelated reasons — those are excluded from the
        assertion.
        """
        wave_dir = self.root / "docs" / "waves" / "1200a paused-lint-check"
        wave_dir.mkdir(parents=True, exist_ok=True)
        wave_md = wave_dir / "wave.md"
        wave_md.write_text(
            "# Wave Record\n\n"
            "Owner: Engineering\n"
            "Status: paused\n"
            "Last verified: 2026-05-01\n\n"
            "wave-id: `1200a paused-lint-check`\n"
            "Title: Paused Lint Check\n\n"
            "## Changes\n\n"
            "## Wave Summary\n\nTest.\n\n"
            "## Journal Watchpoints\n\n- Paused wave testing.\n\n"
            "## Dependencies\n\n- None.\n",
            encoding="utf-8",
        )
        result = self.srv.run_validate(self.root)
        errors = result.get("errors", [])
        # No error may mention 'paused' as invalid / unknown / unexpected / rejected.
        # Validators that reject specific status values would produce such messages.
        paused_rejection_markers = ("invalid status", "unknown status", "unexpected status", "status.*paused", "paused.*invalid")
        offending = [
            err for err in errors
            if "paused" in err.lower() and any(marker.replace(".*", "") in err.lower() for marker in paused_rejection_markers)
        ]
        self.assertEqual(
            offending,
            [],
            f"Lint produced errors rejecting 'paused' as a wave status: {offending}",
        )


class WaveRunSensorsTests(unittest.TestCase):
    """12ecs-feat post-edit-computational-sensors: wf_run_sensors MCP tool."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def _write_config(self, sensors):
        cfg = {
            "lifecycle_id_policy": {"epoch_utc": "2020-02-02T02:02:00Z", "hour_offset": 0},
            "sensors": sensors,
        }
        (self.root / "docs" / "workflow-config.json").write_text(
            json.dumps(cfg), encoding="utf-8"
        )

    def test_no_sensors_configured(self):
        result = self.srv.wf_run_sensors_response(self.root)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["data"]["sensors_run"], 0)
        self.assertEqual(result["data"]["results"], [])
        self.assertTrue(result["data"]["all_passed"])

    def test_passing_sensor(self):
        self._write_config([{"name": "true-check", "command": ["true"], "dimension": "maintainability"}])
        result = self.srv.wf_run_sensors_response(self.root)
        self.assertEqual(result["status"], "ok")
        self.assertTrue(result["data"]["all_passed"])
        self.assertEqual(len(result["data"]["results"]), 1)
        self.assertTrue(result["data"]["results"][0]["passed"])

    def test_failing_sensor(self):
        self._write_config([{"name": "false-check", "command": ["false"], "dimension": "maintainability"}])
        result = self.srv.wf_run_sensors_response(self.root)
        self.assertEqual(result["status"], "error")
        self.assertFalse(result["data"]["all_passed"])
        self.assertFalse(result["data"]["results"][0]["passed"])
        self.assertEqual(result["data"]["results"][0]["name"], "false-check")
        self.assertTrue(any(d["code"] == "sensor_failed" for d in result["diagnostics"]))

    def test_sensor_with_invalid_command(self):
        self._write_config([{"name": "bad-cmd", "command": ["__nonexistent_command__"], "dimension": "behaviour"}])
        result = self.srv.wf_run_sensors_response(self.root)
        self.assertFalse(result["data"]["all_passed"])
        self.assertFalse(result["data"]["results"][0]["passed"])


class RequiredReviewLanesTests(unittest.TestCase):
    """12ecs-enh inferential-sensors-as-required-review-lanes: project-declared lanes enforcement."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        _make_repo(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def _write_config_with_lanes(self, lanes):
        cfg = {
            "lifecycle_id_policy": {"epoch_utc": "2020-02-02T02:02:00Z", "hour_offset": 0},
            "required_review_lanes": lanes,
        }
        (self.root / "docs" / "workflow-config.json").write_text(
            json.dumps(cfg), encoding="utf-8"
        )

    def _make_wave_with_evidence(self, evidence_lines):
        wave_dir = self.root / "docs" / "waves" / "1200a test-wave"
        wave_dir.mkdir(parents=True, exist_ok=True)
        (wave_dir / "wave.md").write_text(
            "# Wave Record\n"
            "wave-id: `1200a test-wave`\n"
            "Status: active\n\n"
            "## Changes\n\n"
            "Change ID: `1200a-feat sample`\n"
            "Change Status: `complete`\n\n"
            "## Review Evidence\n\n"
            + "\n".join(evidence_lines) + "\n",
            encoding="utf-8",
        )

    def test_project_declared_lane_appears_in_required_lanes(self):
        self._write_config_with_lanes(["security-review"])
        self._make_wave_with_evidence(["- operator-signoff: approved", "- security-review: approved"])
        with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
            result = self.srv.wf_review_wave_response(self.root, "1200a test-wave")
        self.assertIn("security-review", result["data"]["required_lanes"])

    def test_missing_declared_lane_emits_missing_required_lane(self):
        self._write_config_with_lanes(["security-review"])
        self._make_wave_with_evidence(["- operator-signoff: approved"])
        with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
            result = self.srv.wf_review_wave_response(self.root, "1200a test-wave")
        self.assertEqual(result["status"], "error")
        self.assertTrue(any(d["code"] == "missing_required_lane" for d in result["diagnostics"]))

    def test_no_declared_lanes_unchanged_behaviour(self):
        # AC-3: projects with no declared lanes only require operator
        self._make_wave_with_evidence(["- operator-signoff: approved"])
        with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
            result = self.srv.wf_review_wave_response(self.root, "1200a test-wave")
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["data"]["required_lanes"], ["operator"])

    def test_wf_close_wave_blocks_on_missing_declared_lane(self):
        self._write_config_with_lanes(["security-review"])
        self._make_wave_with_evidence(["- operator-signoff: approved"])
        with patch.object(self.srv, "run_garden", return_value={"passed": True, "files_updated": 0, "updated": [], "output": ""}):
            with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
                result = self.srv.wf_close_wave_response(self.root, "1200a test-wave", mode="dry_run")
        self.assertEqual(result["status"], "error")
        self.assertTrue(any(d["code"] == "missing_required_lane" for d in result["diagnostics"]))

    def test_wf_close_wave_passes_when_declared_lane_signed(self):
        self._write_config_with_lanes(["security-review"])
        self._make_wave_with_evidence(["- operator-signoff: approved", "- security-review: approved"])
        with patch.object(self.srv, "run_garden", return_value={"passed": True, "files_updated": 0, "updated": [], "output": ""}):
            with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
                result = self.srv.wf_close_wave_response(self.root, "1200a test-wave", mode="dry_run")
        self.assertNotIn("missing_required_lane", [d["code"] for d in result.get("diagnostics", [])])


class SeverityTriageTests(unittest.TestCase):
    """12ed1-enh sensor-finding-severity-triage: max_severity and advisory diagnostic."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        _make_repo(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def _make_wave_with_evidence(self, evidence_lines):
        wave_dir = self.root / "docs" / "waves" / "1200a test-wave"
        wave_dir.mkdir(parents=True, exist_ok=True)
        (wave_dir / "wave.md").write_text(
            "# Wave Record\n"
            "wave-id: `1200a test-wave`\n"
            "Status: active\n\n"
            "## Changes\n\n"
            "Change ID: `1200a-feat sample`\n"
            "Change Status: `complete`\n\n"
            "## Review Evidence\n\n"
            + "\n".join(evidence_lines) + "\n",
            encoding="utf-8",
        )

    def test_no_severity_annotations_returns_none(self):
        self._make_wave_with_evidence(["- operator-signoff: approved"])
        with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
            result = self.srv.wf_review_wave_response(self.root, "1200a test-wave")
        self.assertEqual(result["data"]["max_severity"], "none")

    def test_medium_severity_no_advisory(self):
        self._make_wave_with_evidence([
            "- operator-signoff: approved",
            "- security-review: approved-with-notes (medium — minor issue)",
        ])
        with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
            result = self.srv.wf_review_wave_response(self.root, "1200a test-wave")
        self.assertEqual(result["data"]["max_severity"], "medium")
        self.assertFalse(any(d["code"] == "high_severity_finding" for d in result.get("diagnostics", [])))

    def test_high_severity_emits_advisory(self):
        self._make_wave_with_evidence([
            "- operator-signoff: approved",
            "- security-review: needs-revision (high — path traversal in code_read)",
        ])
        with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
            result = self.srv.wf_review_wave_response(self.root, "1200a test-wave")
        self.assertEqual(result["data"]["max_severity"], "high")
        self.assertTrue(any(d["code"] == "high_severity_finding" for d in result.get("diagnostics", [])))

    def test_critical_severity_emits_advisory(self):
        self._make_wave_with_evidence([
            "- operator-signoff: approved",
            "- security-review: needs-revision (critical — exploitable RCE)",
        ])
        with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
            result = self.srv.wf_review_wave_response(self.root, "1200a test-wave")
        self.assertEqual(result["data"]["max_severity"], "critical")
        self.assertTrue(any(d["code"] == "high_severity_finding" for d in result.get("diagnostics", [])))

    def test_low_severity_no_advisory(self):
        self._make_wave_with_evidence([
            "- operator-signoff: approved",
            "- performance-review: approved-with-notes (low — micro-optimisation opportunity)",
        ])
        with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
            result = self.srv.wf_review_wave_response(self.root, "1200a test-wave")
        self.assertEqual(result["data"]["max_severity"], "low")
        self.assertFalse(any(d["code"] == "high_severity_finding" for d in result.get("diagnostics", [])))

    def test_substring_severity_words_do_not_false_trigger(self):
        """Wave 1p45s (AC-1): severity words embedded in larger words must NOT register —
        ordinary review prose like "highest-salience"/"below"/"allow"/"lower"/"criticality"
        yields no finding."""
        self._make_wave_with_evidence([
            "- operator-signoff: approved",
            "- wave-council-delivery: approved — rotating-seat [highest-salience surface]; "
            "flow below the allow threshold; lower risk; criticality assessed",
        ])
        with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
            result = self.srv.wf_review_wave_response(self.root, "1200a test-wave")
        self.assertEqual(result["data"]["max_severity"], "none")
        self.assertFalse(any(d["code"] == "high_severity_finding" for d in result.get("diagnostics", [])))

    def test_standalone_severity_word_wins_over_substring_noise(self):
        """Wave 1p45s (AC-2): a genuine standalone severity word is still detected even
        alongside substring noise like "highest-salience"."""
        self._make_wave_with_evidence([
            "- operator-signoff: approved",
            "- security-review: needs-revision — highest-salience surface, but a high severity bug",
        ])
        with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
            result = self.srv.wf_review_wave_response(self.root, "1200a test-wave")
        self.assertEqual(result["data"]["max_severity"], "high")

    def test_max_severity_matches_whole_words_only(self):
        """Wave 1p45s (AC-1/AC-3): unit-level — substring noise yields none; a standalone
        severity word is detected regardless of position in the line.

        Wave 1to78: the prose severity scan moved into review_evidence.py as the
        LEGACY branch of the review-authority facade (declared waves derive
        severity from typed finding heads instead); the prose semantics under
        test here are unchanged."""
        review = sys.modules["review_evidence"]
        noise = "## Review Evidence\n\n- note: highest-salience, flow below, allow, lower, criticality"
        self.assertEqual(review.prose_max_severity(noise), "none")
        genuine = "## Review Evidence\n\n- security: high severity confirmed"
        self.assertEqual(review.prose_max_severity(genuine), "high")


class WaveCouncilPolicyTests(unittest.TestCase):
    """12g1y-enh wave-council-review-system: council signoff enforcement."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        _make_repo(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def _write_config(self, enabled=True, transition_policy=""):
        cfg = {
            "lifecycle_id_policy": {"epoch_utc": "2020-02-02T02:02:00Z", "hour_offset": 0},
            "wave_review": {
                "enabled": enabled,
                "delivery_mode": "universal" if enabled else "disabled",
                "transition_policy": transition_policy,
                "phases": {
                    "prepare": {"signoff_key": "wave-council-readiness", "moderator_role": "wave-council"},
                    "review": {"signoff_key": "wave-council-delivery", "moderator_role": "wave-council"},
                },
            },
        }
        (self.root / "docs" / "workflow-config.json").write_text(json.dumps(cfg), encoding="utf-8")

    def _make_change_doc(self, change_id: str):
        wave_dir = self.root / "docs" / "waves" / "1200a test-wave"
        wave_dir.mkdir(parents=True, exist_ok=True)
        (wave_dir / f"{change_id}.md").write_text(
            "# Sample Change\n\n"
            f"Change ID: `{change_id}`\n"
            "Change Status: `planned`\n"
            "## Rationale\n\nwhy\n\n"
            "## Requirements\n\n1. x\n\n"
            "## Scope\n\nin scope\n\n"
            "## Acceptance Criteria\n\n- x\n\n"
            "## Tasks\n\n- x\n\n"
            "## AC Priority\n\n"
            "| AC | Priority | Rationale |\n"
            "| -- | -------- | --------- |\n"
            "| AC-1 | required | x |\n",
            encoding="utf-8",
        )

    def _make_wave(self, status="planned", evidence_lines=None):
        if evidence_lines is None:
            evidence_lines = []
        wave_dir = self.root / "docs" / "waves" / "1200a test-wave"
        wave_dir.mkdir(parents=True, exist_ok=True)
        (wave_dir / "wave.md").write_text(
            "# Wave Record\n"
            "Owner: Engineering\n"
            f"Status: {status}\n"
            "Last verified: 2026-05-08\n\n"
            "wave-id: `1200a test-wave`\n"
            "Title: Test Wave\n\n"
            "## Changes\n\n"
            "Change ID: `1200a-feat sample`\n"
            "Change Status: `planned`\n\n"
            "## Participants\n\n"
            "| Role | Lane | Scope |\n"
            "|------|------|-------|\n"
            "| code-reviewer | review | sample |\n\n"
            "## Review Evidence\n\n"
            + "\n".join(evidence_lines) + "\n",
            encoding="utf-8",
        )
        self._make_change_doc("1200a-feat sample")

    def test_prepare_requires_readiness_council_signoff(self):
        self._write_config()
        self._make_wave(status="planned", evidence_lines=[])
        with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
            result = self.srv.wf_prepare_wave_response(self.root, "1200a test-wave", mode="dry_run")
        self.assertEqual(result["status"], "error")
        self.assertTrue(any(d["code"] == "missing_wave_council_signoff" for d in result["diagnostics"]))

    def test_prepare_passes_when_readiness_signoff_present(self):
        self._write_config()
        self._make_wave(status="planned", evidence_lines=["- wave-council-readiness: approved"])
        with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
            result = self.srv.wf_prepare_wave_response(self.root, "1200a test-wave", mode="dry_run")
        self.assertIn("wave-council-readiness", result["data"]["required_council_signoffs"])
        self.assertNotEqual(result["status"], "error")

    def test_review_requires_delivery_council_signoff(self):
        self._write_config()
        self._make_wave(status="active", evidence_lines=["- operator-signoff: approved", "- code-reviewer: approved"])
        with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
            result = self.srv.wf_review_wave_response(self.root, "1200a test-wave")
        self.assertEqual(result["status"], "error")
        self.assertTrue(any(d["code"] == "missing_wave_council_signoff" for d in result["diagnostics"]))

    def test_close_requires_both_council_signoffs(self):
        self._write_config()
        self._make_wave(
            status="active",
            evidence_lines=[
                "- operator-signoff: approved",
                "- code-reviewer: approved",
                "- wave-council-delivery: approved",
            ],
        )
        with patch.object(self.srv, "run_garden", return_value={"passed": True, "files_updated": 0, "updated": [], "output": ""}):
            with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
                result = self.srv.wf_close_wave_response(self.root, "1200a test-wave", mode="dry_run")
        self.assertEqual(result["status"], "error")
        self.assertTrue(any(d["code"] == "missing_wave_council_signoff" for d in result["diagnostics"]))

    def test_disabled_policy_does_not_require_council(self):
        self._write_config(enabled=False)
        self._make_wave(status="active", evidence_lines=["- operator-signoff: approved", "- code-reviewer: approved"])
        with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
            result = self.srv.wf_review_wave_response(self.root, "1200a test-wave")
        self.assertEqual(result["data"]["required_council_signoffs"], [])
        self.assertFalse(any(d["code"] == "missing_wave_council_signoff" for d in result.get("diagnostics", [])))

    def test_transition_policy_still_requires_delivery_review_signoff(self):
        self._write_config(transition_policy="applies-from-next-prepare")
        self._make_wave(status="active", evidence_lines=["- operator-signoff: approved", "- code-reviewer: approved"])
        with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
            result = self.srv.wf_review_wave_response(self.root, "1200a test-wave")
        self.assertEqual(result["data"]["required_council_signoffs"], ["wave-council-delivery"])
        self.assertTrue(any(d["code"] == "missing_wave_council_signoff" for d in result["diagnostics"]))

    def test_transition_policy_close_does_not_require_missing_readiness_signoff(self):
        self._write_config(transition_policy="applies-from-next-prepare")
        self._make_wave(
            status="active",
            evidence_lines=[
                "- operator-signoff: approved",
                "- code-reviewer: approved",
                "- wave-council-delivery: approved",
            ],
        )
        with patch.object(self.srv, "run_garden", return_value={"passed": True, "files_updated": 0, "updated": [], "output": ""}):
            with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
                result = self.srv.wf_close_wave_response(self.root, "1200a test-wave", mode="dry_run")
        self.assertEqual(result["data"]["required_council_signoffs"], ["wave-council-delivery"])
        self.assertFalse(any(d["code"] == "missing_wave_council_signoff" for d in result.get("diagnostics", [])))

    def test_transition_policy_distinguishes_stale_absent_and_current_readiness(self):
        """1tsyx AC-7: canonical producers pin stale, absent, and current.

        1upba AC-9 amends the `absent` expectation DELIBERATELY.  This fixture
        publishes a receipt for every state and skips only the approval, so its
        "absent" wave is GOVERNED by the policy rather than in flight from
        before it.  The carve-out now keys on never-prepared-under-policy
        (no receipt, healthy ledger) instead of on approval absence, because
        refusing a stale readiness approval also makes it absent -- so keying on
        absence would let the refusal WEAKEN the close gate below what the
        silent accept required.  See the sibling test below for the population
        the carve-out still serves.
        """
        self._write_config(transition_policy="applies-from-next-prepare")
        expected = {
            "stale": ["wave-council-readiness", "wave-council-delivery"],
            "absent": ["wave-council-readiness", "wave-council-delivery"],
            "current": ["wave-council-readiness", "wave-council-delivery"],
        }
        for state, keys in expected.items():
            created = self.srv.wf_create_wave_response(
                self.root, f"transition-{state}", mode="create"
            )
            self.assertEqual(created["status"], "ok", created)
            wave_id = created["data"]["wave_id"]
            wave_md = self.root / "docs" / "waves" / wave_id / "wave.md"
            wave_text = wave_md.read_text(encoding="utf-8")
            brief = self.srv.lifecycle_gate_support._build_prepare_council_brief(wave_id, wave_text, [])
            policy_state, policy_errors = self.srv.lifecycle_gate_support._prepare_policy_state(
                self.root, wave_md, wave_text, [], brief
            )
            self.assertEqual(policy_errors, ())
            self.srv._publish_prepare_policy_state(
                self.root, wave_md, wave_text, policy_state
            )

            if state != "absent":
                approval = self.srv.wf_review_event_response(
                    self.root,
                    wave_id,
                    "approval",
                    "wave-council",
                    f"transition-{state}-approval",
                    mode="create",
                    signoff_key="wave-council-readiness",
                    approval_phase="readiness",
                    fresh_context=True,
                    independent=True,
                    integrity_checks=integrity_checks(),
                    evidence={
                        "observed": "readiness approved",
                        "artifact_or_test_id": f"test:transition-{state}-approval",
                    },
                )
                self.assertEqual(approval["status"], "ok", approval)

            if state == "stale":
                finding = self.srv.wf_review_event_response(
                    self.root,
                    wave_id,
                    "finding",
                    "qa-reviewer",
                    "transition-stale-finding",
                    mode="create",
                    finding_id="readiness-regression",
                    run_kind="readiness",
                    cycle=0,
                    judgment={
                        "validation_status": "real",
                        "scope_relation": "admitted",
                        "introduced_or_worsened_by_wave": True,
                        "contract_relevance": "required_ac",
                        "supported_reachability": True,
                        "attacker_reachability": False,
                        "authority_domain": "integrity",
                        "authority_delta": "low",
                        "observable_impact": "material",
                        "containment": "preventive",
                    },
                    evidence={
                        "proposition": "later readiness work makes the prior approval stale",
                        "failure_condition": "the stale approval remains current",
                        "public_path": "wf_review_event then close-policy derivation",
                        "command_or_fixture": "WaveCouncilPolicyTests canonical producer fixture",
                        "expected": "readiness approval is recorded but stale",
                        "observed": "blocking readiness finding recorded after approval",
                        "artifact_or_test_id": "test:transition-stale-finding",
                        "known_bad_detection_method": "mutate signoff_recorded to current-only",
                        "limitations": "temporary local fixture only",
                        "safety_and_authorization": "local disposable fixture",
                        "disposition_rationale": "required readiness behavior regressed",
                    },
                    source_lanes=["qa-reviewer"],
                    blocking_required_lanes=["qa-reviewer"],
                    approval_recheck_lanes=["wave-council-readiness"],
                    review_boundaries_changed=[],
                    fresh_context=True,
                    independent=True,
                    integrity_checks=integrity_checks(),
                )
                self.assertEqual(finding["status"], "ok", finding)

            with self.subTest(state=state):
                actual = self.srv.lifecycle_gate_support._required_wave_council_signoffs(
                    self.root,
                    "close",
                    wave_text=wave_md.read_text(encoding="utf-8"),
                    wave_md=wave_md,
                )
                self.assertEqual(actual, keys)

    LINT_OK = {"passed": True, "errors": [], "warnings": [], "output": ""}
    GARDEN_OK = {"passed": True, "files_updated": 0, "updated": [], "output": ""}

    def _run_prepare(self, **kwargs):
        """Drive prepare past the docs gate so it actually reaches publication.

        Without this the fixture's diagnostics short-circuit at
        `if diagnostics:` and every assertion downstream is vacuous -- which is
        exactly how two tests in this class shipped asserting nothing.
        """
        with patch.object(self.srv, "run_validate", return_value=self.LINT_OK), \
             patch.object(self.srv, "run_garden", return_value=self.GARDEN_OK), \
             patch.object(self.srv, "_trigger_background_index_refresh_for_paths"):
            return self.srv.wf_prepare_wave_response(self.root, **kwargs)

    def _close_roster(self, wave_md):
        return self.srv.lifecycle_gate_support._required_wave_council_signoffs(
            self.root,
            "close",
            wave_text=wave_md.read_text(encoding="utf-8"),
            wave_md=wave_md,
        )

    def _governed_wave_without_readiness_approval(self, slug):
        """A wave that HAS a receipt but no readiness approval.

        This is the state a refused readiness approval leaves behind, and it is
        the state the close carve-out must NOT treat as pre-policy.
        """
        created = self.srv.wf_create_wave_response(self.root, slug, mode="create")
        self.assertEqual(created["status"], "ok", created)
        wave_id = created["data"]["wave_id"]
        wave_md = self.root / "docs" / "waves" / wave_id / "wave.md"
        wave_text = wave_md.read_text(encoding="utf-8")
        brief = self.srv.lifecycle_gate_support._build_prepare_council_brief(wave_id, wave_text, [])
        policy_state, policy_errors = self.srv.lifecycle_gate_support._prepare_policy_state(
            self.root, wave_md, wave_text, [], brief
        )
        self.assertEqual(policy_errors, ())
        self.srv._publish_prepare_policy_state(
            self.root, wave_md, wave_text, policy_state
        )
        return wave_id, wave_md

    def test_close_carve_out_does_not_fire_at_the_delivery_signoff_exit(self):
        """1upba AC-9: the close branch has TWO exits that drop the readiness key.

        `if has_review_signoff and review_key: return [review_key]` is the exit
        an implementation that patches only the fallthrough leaves untouched,
        and it is the NORMAL end-state of a wave whose readiness approval was
        refused and which then completed delivery review.  Every earlier fixture
        for this behavior lacked a current delivery approval, so the inversion
        would have shipped green.
        """
        self._write_config(transition_policy="applies-from-next-prepare")
        wave_id, wave_md = self._governed_wave_without_readiness_approval(
            "close-exit-b"
        )
        self.assertEqual(
            self._close_roster(wave_md),
            ["wave-council-readiness", "wave-council-delivery"],
            "governed wave with no readiness approval must keep the readiness key",
        )

        run = self.srv.wf_review_event_response(
            self.root,
            wave_id=wave_id,
            event="run",
            mode="create",
            actor="wave-council",
            context_id="close-exit-b-delivery",
            approval_phase="delivery",
            run_kind="initial_delivery",
            cycle=0,
        )
        self.assertEqual(run["status"], "ok", run)
        approval = self.srv.wf_review_event_response(
            self.root,
            wave_id=wave_id,
            event="approval",
            mode="create",
            signoff_key="wave-council-delivery",
            approval_phase="delivery",
            actor="wave-council",
            context_id="close-exit-b-delivery",
            fresh_context=True,
            independent=True,
            evidence={
                "observed": "delivery council approved the delivered scope",
                "artifact_or_test_id": "test:close-exit-b",
            },
            integrity_checks=integrity_checks(),
        )
        self.assertEqual(approval["status"], "ok", approval)

        # Exit B is now reachable. Without the fix it returns only the delivery
        # key, which is strictly MORE permissive than the silent accept.
        self.assertEqual(
            self._close_roster(wave_md),
            ["wave-council-readiness", "wave-council-delivery"],
            "a current delivery approval must not drop the readiness key from a "
            "wave that was prepared under the policy",
        )

    def test_close_carve_out_still_serves_a_wave_with_no_receipt(self):
        """1upba AC-9: deleting the carve-out outright must not pass.

        The carve-out exists for waves in flight before the policy applied.
        Those carry no receipt at all, so they must still drop the readiness key.
        """
        self._write_config(transition_policy="applies-from-next-prepare")
        created = self.srv.wf_create_wave_response(
            self.root, "close-no-receipt", mode="create"
        )
        self.assertEqual(created["status"], "ok", created)
        wave_md = (
            self.root / "docs" / "waves" / created["data"]["wave_id"] / "wave.md"
        )
        self.assertNotIn(
            "wave-council-readiness",
            self._close_roster(wave_md),
            "a wave never prepared under the policy keeps its carve-out",
        )

    def _prepared_wave_with_change(self, slug, change_id="1abc-bug sample"):
        """A governed wave built through canonical creation/admission/Prepare."""
        from server_tools_support import make_declared_wave, declared_wave_doc_gates
        from test_declared_wave_fixtures import fixture_doc_stubs
        stubs = fixture_doc_stubs()
        with declared_wave_doc_gates(self.srv, stubs):
            made = self.srv.new_change(self.root, "bug", "sample", change_id=change_id)
        change_path = self.root / made["path"]
        change_path.write_text(
            "# Sample Change\n\n"
            f"Change ID: `{change_id}`\n"
            "Change Status: `planned`\n\n"
            "## Rationale\n\nwhy\n\n"
            "## Requirements\n\n1. x\n\n"
            "## Scope\n\nin scope\n\n"
            "## Acceptance Criteria\n\n- [ ] AC-1: a thing.\n\n"
            "## Tasks\n\n- [ ] do it.\n\n"
            "## AC Priority\n\n\n| AC | Priority | Rationale |\n| ---- | -------- | --------- |\n"
            "| AC-1 | required | the thing. |\n\n\n"
            "## Progress Log\n\n| Date | Update | Evidence |\n| --- | --- | --- |\n| d | u | e |\n",
            encoding="utf-8",
        )
        wave_id, wave_md = make_declared_wave(self.srv, self.root, slug,
            change_ids=(change_id,), ready=True, doc_gate_stubs=stubs)
        return wave_id, wave_md, wave_md.parent / f"{change_id}.md"

    def _record_readiness_approval(self, wave_id, signoff_key, context_id):
        # A specialist lane must be recorded BY that lane; only the council key
        # is recorded by `wave-council`.
        actor = "wave-council" if signoff_key.startswith("wave-council") else signoff_key
        self.srv.wf_review_event_response(
            self.root, wave_id=wave_id, event="run", mode="create",
            actor=actor, context_id=context_id,
            approval_phase="readiness", run_kind="readiness", cycle=0,
        )
        return self.srv.wf_review_event_response(
            self.root, wave_id=wave_id, event="approval", mode="create",
            signoff_key=signoff_key, approval_phase="readiness",
            actor=actor, context_id=context_id,
            fresh_context=True, independent=True,
            evidence={
                "observed": "reviewed the admitted scope",
                "artifact_or_test_id": "test:staleness",
            },
            integrity_checks=integrity_checks(),
        )

    def test_a_readiness_approval_is_refused_against_an_already_stale_receipt(self):
        """1upba AC-1 red-first: today this returns ok with zero diagnostics.

        The record is dead on arrival either way -- `review_authority_projection`
        only honors an approval while its `policy_receipt_id` matches the
        CURRENT receipt -- so accepting it writes a permanently unusable record
        into an append-only authority ledger and reports success.
        """
        self._write_config(transition_policy="applies-from-next-prepare")
        wave_id, wave_md, change_path = self._prepared_wave_with_change("stale-refusal")

        ok = self._record_readiness_approval(wave_id, "wave-council-readiness", "c0")
        self.assertEqual(ok["status"], "ok", ok)

        # Move a policy input: a requirement edit is digested.
        change_path.write_text(
            change_path.read_text(encoding="utf-8").replace(
                "1. x", "1. x, and a second requirement that changes the digest"
            ),
            encoding="utf-8",
        )
        # Snapshot AFTER the run record, so the assertion brackets the approval
        # alone rather than the run event that legitimately appends.
        self.srv.wf_review_event_response(
            self.root, wave_id=wave_id, event="run", mode="create",
            actor="wave-council", context_id="c1",
            approval_phase="readiness", run_kind="readiness", cycle=0,
        )
        ledger_before = (wave_md.parent / "events.jsonl").read_bytes()

        refused = self.srv.wf_review_event_response(
            self.root, wave_id=wave_id, event="approval", mode="create",
            signoff_key="wave-council-readiness", approval_phase="readiness",
            actor="wave-council", context_id="c1",
            fresh_context=True, independent=True,
            evidence={
                "observed": "reviewed the admitted scope",
                "artifact_or_test_id": "test:staleness",
            },
            integrity_checks=integrity_checks(),
        )
        self.assertEqual(refused["status"], "error", refused)
        codes = [d["code"] for d in refused["diagnostics"]]
        self.assertIn("review_policy_receipt_stale", codes)
        message = " ".join(d["message"] for d in refused["diagnostics"])
        self.assertIn("could never satisfy a gate", message)
        self.assertEqual(
            (wave_md.parent / "events.jsonl").read_bytes(),
            ledger_before,
            "a refused approval must append nothing to the authority ledger",
        )

    def test_the_refusal_covers_specialist_lanes_not_only_the_council_key(self):
        """1upba AC-1: `readiness_approval` is true for every key except two.

        An implementation scoped to `wave-council-readiness` alone would pass a
        council-key-only test while leaving specialist lanes accepting stale
        binds, which is half the defect shipping.
        """
        self._write_config(transition_policy="applies-from-next-prepare")
        wave_id, _wave_md, change_path = self._prepared_wave_with_change("stale-lane")
        change_path.write_text(
            change_path.read_text(encoding="utf-8").replace("1. x", "1. x plus more"),
            encoding="utf-8",
        )
        refused = self._record_readiness_approval(wave_id, "code-reviewer", "lane")
        self.assertEqual(refused["status"], "error", refused)
        self.assertIn(
            "review_policy_receipt_stale",
            [d["code"] for d in refused["diagnostics"]],
        )

    def test_delivery_and_operator_approvals_are_not_refused(self):
        """1upba AC-1 negative boundary.

        The `readiness_approval` predicate deliberately excludes
        `wave-council-delivery` and `operator-signoff`.  An implementer who
        hoisted the recompute above that branch would refuse them while still
        passing every positive case above.
        """
        self._write_config(transition_policy="applies-from-next-prepare")
        wave_id, _wave_md, change_path = self._prepared_wave_with_change("stale-neg")
        change_path.write_text(
            change_path.read_text(encoding="utf-8").replace("1. x", "1. x plus more"),
            encoding="utf-8",
        )
        self.srv.wf_review_event_response(
            self.root, wave_id=wave_id, event="run", mode="create",
            actor="wave-council", context_id="dv",
            approval_phase="delivery", run_kind="initial_delivery", cycle=0,
        )
        delivery = self.srv.wf_review_event_response(
            self.root, wave_id=wave_id, event="approval", mode="create",
            signoff_key="wave-council-delivery", approval_phase="delivery",
            actor="wave-council", context_id="dv",
            fresh_context=True, independent=True,
            evidence={
                "observed": "delivery reviewed",
                "artifact_or_test_id": "test:neg",
            },
            integrity_checks=integrity_checks(),
        )
        self.assertEqual(delivery["status"], "ok", delivery)

    def test_an_ambiguous_excluded_heading_refuses_rather_than_degrading(self):
        """1upba AC-2 case (d): the author-reachable bypass.

        `1urlc` added `ambiguous_excluded_headings` into the same `errors`
        channel as read failures.  Degrading the whole channel would let an
        author switch off the staleness check for their own wave by typing a
        second `## Progress Log` heading.  Built from a REAL fixture document
        rather than a stub, because a stub cannot show an ordinary author can
        reach it.
        """
        self._write_config(transition_policy="applies-from-next-prepare")
        wave_id, _wave_md, change_path = self._prepared_wave_with_change("stale-ambig")
        change_path.write_text(
            change_path.read_text(encoding="utf-8")
            + "\n## Progress Log\n\n| Date | Update | Evidence |\n| --- | --- | --- |\n| x | y | z |\n",
            encoding="utf-8",
        )
        refused = self._record_readiness_approval(
            wave_id, "wave-council-readiness", "ambig"
        )
        self.assertEqual(refused["status"], "error", refused)
        message = " ".join(d["message"] for d in refused["diagnostics"])
        self.assertIn("repairable rather than environmental", message)

    def test_an_unreadable_change_doc_warns_and_accepts(self):
        """1upba AC-2 case (a): the environmental cause degrades.

        An unparseable plan must never make approvals unrecordable -- but the
        ledger will not record that this approval skipped verification, so the
        response has to say so.
        """
        self._write_config(transition_policy="applies-from-next-prepare")
        wave_id, _wave_md, change_path = self._prepared_wave_with_change("stale-read")
        change_path.write_bytes(b"\xff\xfe not valid utf-8 \xff")
        accepted = self._record_readiness_approval(
            wave_id, "wave-council-readiness", "unreadable"
        )
        self.assertEqual(accepted["status"], "ok", accepted)
        codes = [d["code"] for d in accepted["diagnostics"]]
        self.assertIn("review_policy_staleness_unverified", codes)
        message = " ".join(d["message"] for d in accepted["diagnostics"])
        self.assertIn("COULD NOT BE PERFORMED", message)

    def test_the_staleness_refusal_names_what_moved(self):
        """1upba AC-3: attribution, asserted on content rather than code.

        It must also NOT claim per-document attribution, which the persisted
        data cannot support: the per-change digests are discarded and the
        receipt validator enforces a closed field set.
        """
        self._write_config(transition_policy="applies-from-next-prepare")
        wave_id, _wave_md, change_path = self._prepared_wave_with_change("stale-attr")
        change_path.write_text(
            change_path.read_text(encoding="utf-8").replace("1. x", "1. x and more"),
            encoding="utf-8",
        )
        refused = self._record_readiness_approval(
            wave_id, "wave-council-readiness", "attr"
        )
        message = " ".join(d["message"] for d in refused["diagnostics"])
        self.assertIn("current receipt", message)
        self.assertIn("pending receipt", message)
        self.assertIn("policy_input_digest", message)
        self.assertIn("digested change ids", message)
        self.assertIn("1abc-bug sample", message)
        self.assertIn("not attributable from persisted data", message)

    def test_prepare_dry_run_surfaces_a_pending_mint_and_writes_nothing(self):
        """1upba AC-4: the DOCS-GATE ERROR path.

        Kept alongside the `_run_prepare` preview test because it reaches
        prepare through a different exit: this call bails at the docs gate, so
        its byte-identity assertions run against a short-circuited response
        while the preview test asserts the same property on the path that
        reaches the end of the function.

        An earlier docstring claimed this was "the only test that kills the
        mutant dropping the advisory from the error return's splat". Wave
        `1uugg` removed the per-return splat entirely -- every return now
        routes through `_prepare_envelope` -- so that mutant no longer exists
        and the claim is withdrawn.
        """
        self._write_config(transition_policy="applies-from-next-prepare")
        wave_id, wave_md, change_path = self._prepared_wave_with_change("stale-dry")
        change_path.write_text(
            change_path.read_text(encoding="utf-8").replace("1. x", "1. x and more"),
            encoding="utf-8",
        )
        wave_before = wave_md.read_bytes()
        ledger_before = (wave_md.parent / "events.jsonl").read_bytes()

        resp = self.srv.wf_prepare_wave_response(
            self.root, wave_id=wave_id, mode="dry_run"
        )
        self.assertIn(
            "review_policy_receipt_stale",
            [d["code"] for d in resp.get("diagnostics") or []],
            resp,
        )
        self.assertEqual(wave_md.read_bytes(), wave_before, "dry_run must not write")
        self.assertEqual(
            (wave_md.parent / "events.jsonl").read_bytes(),
            ledger_before,
            "dry_run must not write",
        )

    def test_attribution_names_a_non_digest_field_when_one_moves(self):
        """1upba AC-3: the fixture that stops the field list being hardcoded.

        Every natural transition moves `policy_input_digest` ALONE, so an
        implementation that hardcoded that one field name passed every other
        attribution test.  Declaring Serialization Points targets grows
        `required_lanes`, which is a receipt-semantic field and not the digest.
        """
        self._write_config(transition_policy="applies-from-next-prepare")
        wave_id, _wave_md, change_path = self._prepared_wave_with_change("attr-nondigest")
        change_path.write_text(
            change_path.read_text(encoding="utf-8")
            + "\n## Serialization Points\n\n"
            "**Review targets (repo-relative paths):**\n\n"
            "- `src/auth/session.py`\n"
            "- `docs/specs/api.md`\n",
            encoding="utf-8",
        )
        refused = self._record_readiness_approval(
            wave_id, "wave-council-readiness", "nondigest"
        )
        self.assertEqual(refused["status"], "error", refused)
        message = " ".join(d["message"] for d in refused["diagnostics"])
        self.assertIn("required_lanes", message)
        self.assertIn("policy_input_digest", message)

    def test_mark_ac_deferral_reports_its_supersession_as_a_diagnostic(self):
        """1upba AC-5: today the payload field was the only signal.

        Suppressing this diagnostic survived the entire 1615-test module, so
        neither half of AC-5 existed.  Also pins the label correction: the
        receipt is already published here, so the helper's "pending" slot holds
        the NEW CURRENT receipt and must not be labelled "pending".
        """
        self._write_config(transition_policy="applies-from-next-prepare")
        wave_id, _wave_md, _change_path = self._prepared_wave_with_change("mark-ac-diag")
        # `_mark_change_item_response` is the real handler and is shared with
        # `wf_mark_task`; naming it directly is what AC-5 means by "the test
        # names which tool it drives". An earlier version guarded on a
        # `wf_mark_ac_response` symbol that exists nowhere in the tree.
        marked = self.srv._mark_change_item_response(
            self.root, wave_id, "1abc-bug sample", "AC-1", "~",
            target_section="Acceptance Criteria", mode="create",
            reason="Deliberately deferred for this fixture so the deferral path "
                   "publishes a receipt and the supersession signal is observable.",
        )
        self.assertEqual(marked["status"], "ok", marked)
        codes = [d["code"] for d in marked.get("diagnostics") or []]
        self.assertIn("review_policy_receipt_superseded", codes)
        message = " ".join(d["message"] for d in (marked.get("diagnostics") or []))
        self.assertIn("new current receipt", message)
        # AC-3 also requires the digested change ids and the explicit disclaimer;
        # asserting the label pair alone let a placeholder-attribution mutant
        # ("superseded receipt aaa; new current receipt bbb") pass all 38 tests.
        self.assertIn("digested change ids", message)
        self.assertIn("not attributable from persisted data", message)
        self.assertNotIn(
            "pending receipt", message,
            "the receipt is already published at this surface; calling it pending "
            "tells the operator the opposite of what happened",
        )

    def test_a_corrupt_ledger_does_not_drop_the_readiness_key(self):
        """1upba AC-9: the fail-open direction, one conjunct away.

        `resolve_review_authority` empties `records` on any ledger error, so a
        receipt-presence check ALONE reads a corrupt ledger as "never prepared"
        and drops the readiness key.  Dropping `and not authority.ledger_errors`
        survived the full module before this test existed.
        """
        self._write_config(transition_policy="applies-from-next-prepare")
        _wave_id, wave_md = self._governed_wave_without_readiness_approval(
            "close-corrupt"
        )
        (wave_md.parent / "events.jsonl").write_text(
            "{not valid json at all\n", encoding="utf-8"
        )
        self.assertIn(
            "wave-council-readiness",
            self._close_roster(wave_md),
            "an unreadable ledger must not be read as never-prepared",
        )

    def test_an_unreadable_wave_record_does_not_drop_the_readiness_key(self):
        """1v1de AC-4: the close carve-out must fail closed on an unreadable
        wave RECORD, not just an unreadable ledger.

        Red-first, both causes: before the facade fix the permission cause
        downgraded the authority to legacy-empty (``typed=False``, empty text,
        empty ``ledger_errors``), so ``never_prepared_under_policy`` read True
        and the readiness key fell off the close roster (strictly MORE
        permissive than the downgrade itself); the decode cause raised
        ``UnicodeDecodeError`` out of the roster derivation entirely.  The
        typed-with-errors shape keeps the key through the ledger-health
        conjunct.  ``wave_text`` is deliberately not passed: the facade's own
        record read is the seam under test (production callers pass pre-read
        seam text; this is the direct-consumer / post-gate-race window).
        """
        self._write_config(transition_policy="applies-from-next-prepare")
        _wave_id, wave_md = self._governed_wave_without_readiness_approval(
            "close-unreadable-record"
        )
        readable = wave_md.read_bytes()

        with self.subTest(cause="decode"):
            wave_md.write_bytes(b"\xff\xfe not valid utf-8 \xff")
            self.assertIn(
                "wave-council-readiness",
                self.srv.lifecycle_gate_support._required_wave_council_signoffs(
                    self.root, "close", wave_md=wave_md
                ),
                "an undecodable wave record must not be read as never-prepared",
            )

        with self.subTest(cause="permission"):
            wave_md.write_bytes(readable)
            os.chmod(wave_md, 0)
            try:
                roster = self.srv.lifecycle_gate_support._required_wave_council_signoffs(
                    self.root, "close", wave_md=wave_md
                )
            finally:
                os.chmod(wave_md, stat.S_IRUSR | stat.S_IWUSR)
            self.assertIn(
                "wave-council-readiness",
                roster,
                "a permission-unreadable wave record must not be read as "
                "never-prepared",
            )

    def test_an_invalid_wave_review_config_refuses_the_approval(self):
        """1upba AC-2 case (b): the accepted repository-wide refusal.

        Degrading here would turn one bad config into a global, config-controlled
        bypass of the whole change.  Recorded as accepted in Requirement 2, and
        previously pinned by nothing.
        """
        self._write_config(transition_policy="applies-from-next-prepare")
        wave_id, _wave_md, _change_path = self._prepared_wave_with_change("bad-config")
        cfg_path = self.root / "docs" / "workflow-config.json"
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        cfg["wave_review"] = "not an object"
        cfg_path.write_text(json.dumps(cfg), encoding="utf-8")
        refused = self._record_readiness_approval(
            wave_id, "wave-council-readiness", "badcfg"
        )
        self.assertEqual(refused["status"], "error", refused)
        message = " ".join(d["message"] for d in refused["diagnostics"])
        self.assertIn("repairable rather than environmental", message)
        # Recovery must route to the tool that can actually repair the cause;
        # re-preparing fails identically on a bad config.
        tools = [t for d in refused["diagnostics"] for t in (d.get("recovery_tools") or [])]
        self.assertIn("wf_validate_docs", tools)
        self.assertNotIn("wf_prepare_wave", tools)

    def test_the_ambiguous_heading_refusal_names_the_offending_document(self):
        """1upba AC-2 case (d) content half: dropping the interpolation survived."""
        self._write_config(transition_policy="applies-from-next-prepare")
        wave_id, _wave_md, change_path = self._prepared_wave_with_change("ambig-named")
        change_path.write_text(
            change_path.read_text(encoding="utf-8")
            + "\n## Progress Log\n\n| Date | Update | Evidence |\n| --- | --- | --- |\n| x | y | z |\n",
            encoding="utf-8",
        )
        refused = self._record_readiness_approval(
            wave_id, "wave-council-readiness", "ambignamed"
        )
        message = " ".join(d["message"] for d in refused["diagnostics"])
        self.assertIn("1abc-bug sample", message, "the offending document must be named")
        self.assertIn("Progress Log", message, "the offending heading must be named")

    def test_an_accepted_degraded_approval_is_actually_appended(self):
        """1upba AC-2 case (a): `ok` alone would pass an implementation that
        returned success without recording anything."""
        self._write_config(transition_policy="applies-from-next-prepare")
        wave_id, wave_md, change_path = self._prepared_wave_with_change("degraded-append")
        change_path.write_bytes(b"\xff\xfe not valid utf-8 \xff")
        accepted = self._record_readiness_approval(
            wave_id, "wave-council-readiness", "degraded"
        )
        self.assertEqual(accepted["status"], "ok", accepted)
        authority = self.srv.resolve_review_authority(
            self.root, wave_md, wave_text=wave_md.read_text(encoding="utf-8")
        )
        self.assertTrue(
            authority.signoff_recorded(
                "wave-council-readiness", approval_phase="readiness"
            ),
            "the degraded path must genuinely record the approval, not just return ok",
        )

    def test_an_idempotent_replay_of_a_recorded_approval_still_replays(self):
        """1upba: the recompute must not break the same-identity retry contract.

        The record is already in the ledger, so refusing the retry would report
        that the approval could never satisfy a gate about a call that wrote
        nothing.
        """
        self._write_config(transition_policy="applies-from-next-prepare")
        wave_id, wave_md, change_path = self._prepared_wave_with_change("replay")
        first = self._record_readiness_approval(wave_id, "wave-council-readiness", "rp")
        self.assertEqual(first["status"], "ok", first)
        change_path.write_text(
            change_path.read_text(encoding="utf-8").replace("1. x", "1. x and more"),
            encoding="utf-8",
        )
        before = (wave_md.parent / "events.jsonl").read_bytes()
        replay = self._record_readiness_approval(wave_id, "wave-council-readiness", "rp")
        self.assertEqual(replay["status"], "ok", replay)
        self.assertEqual(
            (wave_md.parent / "events.jsonl").read_bytes(), before,
            "a replay must not append",
        )

    def test_prepare_dry_run_keeps_its_preview_status_and_envelope(self):
        """1upba AC-4: a pending mint is information, not a failure.

        `error` is not in `LIFECYCLE_ENGAGED_STATUSES`, so blocking here would
        silently reclassify every ordinary preflight as not-engaged in focus and
        context-efficiency telemetry, and would drop the council-verdict fields
        the preview exists to produce.

        Both calls run through `_run_prepare` so the baseline is a genuine
        `status: "dry_run"` envelope.  An earlier version compared an error
        envelope to an error envelope, under which moving the advisory onto the
        shared blocking list -- the design executed and rejected during
        implementation -- survived all 7032 tests in the repository.
        """
        self._write_config(transition_policy="applies-from-next-prepare")
        wave_id, wave_md, change_path = self._prepared_wave_with_change("dry-status")
        self._record_readiness_approval(wave_id, "wave-council-readiness", "dry")

        clean = self._run_prepare(wave_id=wave_id, mode="dry_run")
        self.assertEqual(
            clean["status"], "dry_run",
            "the baseline must be a real preview envelope, or every assertion "
            "below compares an error to an error",
        )
        self.assertNotIn(
            "review_policy_receipt_stale",
            [d["code"] for d in clean.get("diagnostics") or []],
        )

        change_path.write_text(
            change_path.read_text(encoding="utf-8").replace("1. x", "1. x and more"),
            encoding="utf-8",
        )
        wave_before = wave_md.read_bytes()
        ledger_before = (wave_md.parent / "events.jsonl").read_bytes()
        pending = self._run_prepare(wave_id=wave_id, mode="dry_run")

        self.assertIn(
            "review_policy_receipt_stale",
            [d["code"] for d in pending.get("diagnostics") or []],
            "the pending mint must be reported on the preview path itself",
        )
        self.assertEqual(
            pending["status"], "dry_run",
            "a pending mint must not turn a preview into a failure",
        )
        self.assertIn(
            pending["status"], self.srv.LIFECYCLE_ENGAGED_STATUSES,
            "a preflight must stay target-engaged for focus and CE telemetry",
        )
        self.assertEqual(
            set(pending["data"]), set(clean["data"]),
            "a pending mint must not drop preview fields from the envelope",
        )
        # AC-4's byte-identity half, asserted on the REAL preview path. The
        # sibling direct-call test also asserts it, but that call bails at the
        # docs gate, so its assertions run against a short-circuited response.
        self.assertEqual(wave_md.read_bytes(), wave_before, "dry_run must not write")
        self.assertEqual(
            (wave_md.parent / "events.jsonl").read_bytes(), ledger_before,
            "dry_run must not write",
        )

    def test_prepare_advisory_requires_literal_true(self):
        """1uugg AC-1/2: only literal True is advisory at prepare gates."""
        self._write_config(transition_policy="applies-from-next-prepare")
        wave_id, _wave_md, _change_path = self._prepared_wave_with_change("literal-advisory")
        self._record_readiness_approval(wave_id, "wave-council-readiness", "literal")

        for value, expected_status in ((True, "dry_run"), (None, "error"), (False, "error"), ("false", "error"), (1, "error")):
            diagnostic = {"code": "probe", "message": "probe"}
            if value is not None:
                diagnostic["advisory"] = value
            with self.subTest(value=value), patch.object(
                self.srv.lifecycle_gates, "_wave_review_policy_diagnostics", return_value=[diagnostic]
            ) as _gate_mock_8:
                response = self._run_prepare(wave_id=wave_id, mode="dry_run")
                self.assertEqual(response["status"], expected_status, response)
                self.assertIn(diagnostic, response.get("diagnostics") or [])
                _gate_mock_8.assert_called()

    def test_every_prepare_return_routes_through_the_envelope_helper(self):
        """1uugg AC-4: asserted per RETURN NODE, derived from source.

        An earlier version asserted hardcoded counts (`len(returns) == 8`,
        `source.count("return _prepare_envelope") == 7`). That failed both
        halves of AC-4's claim: it never checked that EACH return routes
        through the helper, and a correctly-added return broke the count
        instead of being covered -- the opposite of the stated durability.
        This walks the nodes, so a return added later is checked rather than
        counted.
        """
        module = ast.parse(Path(self.srv.__file__).read_text(encoding="utf-8"))
        prepare = next(
            n for n in ast.walk(module)
            if isinstance(n, ast.FunctionDef) and n.name == "wf_prepare_wave_response"
        )
        nested = {
            n.name for n in ast.walk(prepare)
            if isinstance(n, ast.FunctionDef) and n is not prepare
        }

        def _enclosing_is_prepare(node):
            for candidate in ast.walk(prepare):
                if isinstance(candidate, ast.FunctionDef) and candidate is not prepare:
                    if any(child is node for child in ast.walk(candidate)):
                        return False
            return True

        top_level = [
            n for n in ast.walk(prepare)
            if isinstance(n, ast.Return) and _enclosing_is_prepare(n)
        ]
        self.assertTrue(top_level, "prepare must have returns to check")
        allowed = {"_prepare_envelope", "_attach_lint_to_response"}
        for node in top_level:
            value = node.value
            self.assertIsInstance(
                value, ast.Call,
                f"every prepare return must call a helper, not build a value inline "
                f"(line {node.lineno})",
            )
            name = getattr(value.func, "id", None) or getattr(value.func, "attr", None)
            self.assertIn(
                name, allowed,
                f"return at line {node.lineno} calls {name!r}; every return must route "
                f"through _prepare_envelope so no site can construct its own "
                f"diagnostics list (nested helpers seen: {sorted(nested)})",
            )
            if name == "_attach_lint_to_response":
                # Admitting the wrapper without inspecting its argument let a
                # return build its own diagnostics list INSIDE it and still
                # pass -- proved by a delivery-lane mutant. The wrapped value
                # must itself be an envelope-helper call.
                self.assertTrue(value.args, f"line {node.lineno}: no wrapped value")
                inner = value.args[0]
                if isinstance(inner, ast.Call):
                    inner_name = (getattr(inner.func, "id", None)
                                  or getattr(inner.func, "attr", None))
                elif isinstance(inner, ast.Name):
                    # Traced rather than assumed: the name must be bound from a
                    # `_prepare_envelope(...)` call inside this function.
                    inner_name = None
                    for assign in ast.walk(prepare):
                        if not isinstance(assign, ast.Assign):
                            continue
                        if not any(isinstance(tgt, ast.Name) and tgt.id == inner.id
                                   for tgt in assign.targets):
                            continue
                        if isinstance(assign.value, ast.Call):
                            inner_name = (getattr(assign.value.func, "id", None)
                                          or getattr(assign.value.func, "attr", None))
                else:
                    inner_name = type(inner).__name__
                self.assertEqual(
                    inner_name, "_prepare_envelope",
                    f"line {node.lineno}: _attach_lint_to_response wraps {inner_name!r}; "
                    "it must wrap a _prepare_envelope result, or a return can "
                    "construct its own diagnostics list inside the wrapper and "
                    "still pass",
                )

    def test_advisory_tags_appear_only_at_the_sanctioned_sites(self):
        """1uugg AC-10c: assert the sanctioned SET, not its cardinality.

        Two earlier forms were both defeatable. `inspect.getsource(prepare)`
        could not see a mistag in a contributing helper. Counting
        `advisory=True` occurrences could not see a tag MOVED from a sanctioned
        site onto another one -- the delivery QA lane moved it onto
        `missing_wave_council_signoff` (the readiness stage gate) and
        `another_wave_active` (the single-OPEN guard) while holding the count
        at three, and both passed. AC-10c says "the set equals exactly the
        sanctioned set", so this resolves each tag to the diagnostic code it
        actually marks.
        """
        import codenav_handlers
        import graph_handlers

        module = ast.Module(body=[
            node
            for owner in (self.srv, self.srv.lifecycle_gates, self.srv.lifecycle_gate_support,
                          codenav_handlers, graph_handlers)
            for node in ast.parse(Path(owner.__file__).read_text(encoding="utf-8")).body
        ], type_ignores=[])
        owner: dict[int, str] = {}
        for fn in ast.walk(module):
            if isinstance(fn, ast.FunctionDef):
                for child in ast.walk(fn):
                    owner.setdefault(id(child), fn.name)

        tagged: set[tuple[str, str]] = set()
        forwarding: set[str] = set()
        for node in ast.walk(module):
            if not isinstance(node, ast.Call):
                continue
            for kw in node.keywords:
                if kw.arg != "advisory":
                    continue
                callee = getattr(node.func, "id", None) or getattr(node.func, "attr", "?")
                where = owner.get(id(node), "<module>")
                if isinstance(kw.value, ast.Constant) and kw.value.value is True:
                    code = "<helper-call>"
                    if node.args and isinstance(node.args[0], ast.Constant):
                        code = node.args[0].value
                    tagged.add((where, callee, code))
                elif not isinstance(kw.value, ast.Constant):
                    forwarding.add(where)

        self.assertEqual(
            tagged,
            {
                ("change_sections_gate", "_diagnostic", "ac_priority_unpopulated"),
                ("required_sensors_gate", "_diagnostic", "phase_sensor_not_executed"),
                ("wf_prepare_wave_response", "_diagnostic", "prepare_council_verdict_missing"),
                ("_attach_prepare_readiness_advisories", "_diagnostic", "readiness_receipt_publications_high"),
                ("_attach_prepare_readiness_advisories", "_diagnostic", "readiness_lane_approvals_missing"),
                ("policy_advisory_gate", "_review_policy_receipt_diagnostics", "<helper-call>"),
                # Wave 1vbuu (1vbut): code_impact's test-visibility note is a
                # read-only retrieval advisory on a query tool, not a lifecycle
                # gate; it can soften nothing because code_impact gates nothing.
                ("_code_impact_graph_response", "_diagnostic", "test_callers_not_visible"),
                # Wave 1vj4e (1vj4d Requirement 10): the mixed-trio record of the
                # Backstage/TechDocs baseline is a fact about the tree the tool
                # just wrote (some members generated, some project-owned), never
                # a lifecycle gate; the tool gates nothing and the same record is
                # in `data.partial`, so the advisory softens no blocker.
                ("wf_techdocs_baseline_response", "_diagnostic", "backstage_techdocs_partial"),
                # Wave 1vqqi: the audit is a read-only report that gates nothing, so its
                # not-applicable verdict and its degrade notice are advisory for the same
                # reason code_impact's visibility note is. Each is emitted from its own
                # call site with a LITERAL code, because this test resolves the code by
                # AST and falls back to "<helper-call>" for anything computed.
                ("wf_techdocs_audit_response", "_diagnostic", "techdocs_audit_not_applicable"),
                ("wf_techdocs_audit_response", "_diagnostic", "techdocs_audit_degraded"),
                            # Wave 1wuju (1wujs): advisory docs-lint sensors render as
                # `docs_lint_warning` with `advisory: true` at every gate; the
                # shared helper is the one emit site, plus wf_validate_docs's own.
                ("_docs_lint_warning_diagnostics", "_diagnostic", "docs_lint_warning"),
                ("wf_validate_docs_response", "_diagnostic", "docs_lint_warning"),
                # Optional attribution never gates an otherwise valid review.
                ("wf_review_event_response", "_diagnostic", "operator_identity_unresolved"),
            },
            "exactly these sites may be advisory. A tag added, removed, or "
            "MOVED onto another diagnostic changes this set even when the count "
            "does not -- moving it onto missing_wave_council_signoff or "
            "another_wave_active would otherwise open the readiness stage gate "
            "or the single-OPEN guard silently.",
        )
        self.assertEqual(
            forwarding, {"_review_policy_receipt_diagnostics"},
            "only the shared stale-receipt helper may FORWARD an advisory flag; "
            "any other function doing so can tag a blocker its caller cannot see",
        )

    def test_prepare_advisory_predicate_and_workaround_removal(self):
        """1uugg AC-7 and the predicate direction, kept from the original pin.

        Wave 1yd98 extracted the predicate into `lifecycle_gates`, so the
        direction half of this pin now reads its single implementation there.
        The spelling it used to read lived only in prepare's closure, which now
        delegates.  The two workaround-symbol absence checks stay on
        `server_impl.py`, which is what 1uugg was protecting.
        """
        import lifecycle_gates

        gate_source = Path(lifecycle_gates.__file__).read_text(encoding="utf-8")
        self.assertIn('diagnostic.get("advisory") is not True', gate_source)
        source = Path(self.srv.__file__).read_text(encoding="utf-8")
        # AC-7 is scoped to Python sources, not to prepare's own body: an
        # earlier version checked only `inspect.getsource(prepare)`, so a
        # reintroduction elsewhere in `server_impl.py` would have passed. The
        # symbols deliberately survive in prose (this plan and two wave
        # records), which is why the census is Python-only rather than
        # repo-wide.
        self.assertNotIn("_prepare_stale_advisories", source)
        self.assertNotIn("_ac_advisories", source)

    def test_publication_behavior_is_unchanged_at_create(self):
        """1upba AC-6: pinned at `mode='create'`, not `mode='ready'`.

        `_activating` is create-only, so the false-ready outcome this guards --
        the wave reaching `active` on a dead approval with a required lane and
        the delivery council silently dropped -- is invisible at `ready`.

        Driven through `_run_prepare` so prepare passes the docs gate and
        genuinely publishes. An earlier version called prepare directly, hit
        `change_doc_missing_sections` plus 25 lint errors, never published, and
        asserted its own fixture's setup.
        """
        self._write_config(transition_policy="applies-from-next-prepare")
        wave_id, wave_md, change_path = self._prepared_wave_with_change("ac6-create")

        def receipt():
            return self.srv.current_policy_receipt(
                self.srv.resolve_review_authority(
                    self.root, wave_md, wave_text=wave_md.read_text(encoding="utf-8")
                ).records
            )

        before = receipt()
        # Declaring targets moves the doc off legacy-fallback scoring, so a
        # dropped lane would be visible.
        change_path.write_text(
            change_path.read_text(encoding="utf-8")
            + "\n## Serialization Points\n\n"
            "**Review targets (repo-relative paths):**\n\n"
            "- `src/auth/session.py`\n"
            "- `docs/specs/api.md`\n",
            encoding="utf-8",
        )
        resp = self._run_prepare(wave_id=wave_id, mode="create")
        after = receipt()

        self.assertIsNotNone(after)
        self.assertNotEqual(
            after["receipt_id"], before["receipt_id"],
            "prepare must publish the pending receipt; if these are equal the "
            "test is asserting its own setup rather than prepare's behavior",
        )
        wave_text = wave_md.read_text(encoding="utf-8")
        self.assertNotIn(
            "Status: active", wave_text,
            "a wave must not ready on a stale approval",
        )
        self.assertEqual(
            tuple(self.srv.lifecycle_gate_support._extract_required_review_lanes(wave_text)),
            tuple(after["required_lanes"]),
            "the persisted roster must match the published receipt",
        )
        self.assertEqual(
            resp["data"]["review_policy"]["delivery_council_required"],
            after["delivery_council_required"],
            "AC-6(iii): delivery_council_required must match the pending receipt",
        )

    def test_anti_revival_holds_end_to_end_including_the_midpoint(self):
        """1upba AC-8: the structural form passes trivially.

        `derive_receipt_id` chains to the parent, so an A -> B -> A' input cycle
        must yield THREE distinct ids and must not resurrect the A-bound
        approval. The symmetric half matters because a one-sided assertion
        would pass an implementation that special-cased the first approval.
        """
        self._write_config(transition_policy="applies-from-next-prepare")
        wave_id, wave_md, change_path = self._prepared_wave_with_change("ac8-revival")
        original = change_path.read_text(encoding="utf-8")

        def republish():
            text = wave_md.read_text(encoding="utf-8")
            ids = self.srv.lifecycle_gate_support._extract_change_ids_from_wave_text(text)
            state, errors = self.srv.lifecycle_gate_support._prepare_policy_state(
                self.root, wave_md, text, ids, {}
            )
            self.assertEqual(errors, ())
            self.srv._publish_prepare_policy_state(self.root, wave_md, text, state)
            return state["receipt"]["receipt_id"]

        id_a = republish()
        self.assertEqual(
            self._record_readiness_approval(wave_id, "wave-council-readiness", "A")["status"],
            "ok",
        )

        change_path.write_text(original.replace("1. x", "1. x variant B"), encoding="utf-8")
        id_b = republish()

        def current(key="wave-council-readiness"):
            text = wave_md.read_text(encoding="utf-8")
            return self.srv.resolve_review_authority(
                self.root, wave_md, wave_text=text
            ).signoff_current(key, approval_phase="readiness")

        self.assertFalse(current(), "the A-bound approval must be non-current at B")
        self.assertEqual(
            self._record_readiness_approval(wave_id, "wave-council-readiness", "B")["status"],
            "ok",
        )
        self.assertTrue(current(), "the B-bound approval is current at B")

        change_path.write_text(original, encoding="utf-8")  # revert to A'
        id_a_prime = republish()

        self.assertEqual(
            len({id_a, id_b, id_a_prime}), 3,
            "a reverted input must chain to a NEW receipt id, never collide with the first",
        )
        self.assertFalse(
            current(),
            "reverting must not revive the A approval, and must not leave B current",
        )

    def test_convergence_is_one_prepare_plus_one_approval_per_lane(self):
        """1upba AC-10: stated per lane, so a single-key pin cannot mask the
        AC-1 lane-scoping defect, and with zero duplicate approvals."""
        self._write_config(transition_policy="applies-from-next-prepare")
        wave_id, wave_md, change_path = self._prepared_wave_with_change("ac10-converge")
        self._record_readiness_approval(wave_id, "wave-council-readiness", "pre")
        change_path.write_text(
            change_path.read_text(encoding="utf-8").replace("1. x", "1. x edited"),
            encoding="utf-8",
        )
        text = wave_md.read_text(encoding="utf-8")
        ids = self.srv.lifecycle_gate_support._extract_change_ids_from_wave_text(text)
        state, errors = self.srv.lifecycle_gate_support._prepare_policy_state(self.root, wave_md, text, ids, {})
        self.assertEqual(errors, ())
        self.srv._publish_prepare_policy_state(self.root, wave_md, text, state)

        keys = ["wave-council-readiness", *state["required_lanes"]]
        self.assertGreater(len(keys), 1, "the fixture must exercise more than the council key")
        for key in keys:
            resp = self._record_readiness_approval(wave_id, key, f"conv-{key}")
            self.assertEqual(resp["status"], "ok", (key, resp))

        text = wave_md.read_text(encoding="utf-8")
        authority = self.srv.resolve_review_authority(self.root, wave_md, wave_text=text)
        for key in keys:
            self.assertTrue(
                authority.signoff_current(key, approval_phase="readiness"),
                f"{key} must be current after one prepare plus one approval",
            )
        records = [
            r for r in authority.records
            if r.get("record_type") == "executable_evidence"
            and r.get("approval_phase") == "readiness"
            and r.get("policy_receipt_id") == state["receipt"]["receipt_id"]
        ]
        self.assertEqual(
            len(records), len(keys),
            "convergence must not require re-recording any lane twice",
        )

    def test_delivery_phase_keys_are_excluded_from_the_readiness_recompute(self):
        """1upba AC-1, negative boundary, BOTH delivery-phase keys.

        An earlier version asserted the predicate SOURCE TEXT, on the premise
        that removing either key survives an end-to-end test. The code lane
        disproved that by execution: dropping either key makes the refusal fire
        on that key, observable as `review_policy_receipt_stale` replacing the
        phase rejection. So a behavioral pin exists, and asserting source text
        was an evasion -- it also pinned syntax, so reformatting the set literal
        would break it with no behavior change.

        Both keys are rejected at `approval_phase="readiness"` by the evidence
        layer BEFORE the recompute, which is why the correct assertion is that
        they carry `invalid_review_event` and NOT the staleness refusal.
        """
        self._write_config(transition_policy="applies-from-next-prepare")
        wave_id, _wave_md, change_path = self._prepared_wave_with_change("neg-boundary")
        change_path.write_text(
            change_path.read_text(encoding="utf-8").replace("1. x", "1. x and more"),
            encoding="utf-8",
        )
        for key in ("operator-signoff", "wave-council-delivery"):
            with self.subTest(signoff_key=key):
                self.srv.wf_review_event_response(
                    self.root, wave_id=wave_id, event="run", mode="create",
                    actor="wave-council", context_id=f"neg-{key}",
                    approval_phase="readiness", run_kind="readiness", cycle=0,
                )
                resp = self.srv.wf_review_event_response(
                    self.root, wave_id=wave_id, event="approval", mode="create",
                    signoff_key=key, approval_phase="readiness",
                    actor="wave-council", context_id=f"neg-{key}",
                    fresh_context=True, independent=True,
                    evidence={
                        "observed": "negative boundary probe",
                        "artifact_or_test_id": "test:neg-boundary",
                    },
                    integrity_checks=integrity_checks(),
                )
                codes = [d["code"] for d in resp["diagnostics"]]
                self.assertNotIn(
                    "review_policy_receipt_stale", codes,
                    f"{key} must not be subject to the readiness staleness refusal",
                )
                self.assertIn("invalid_review_event", codes, resp)

    def test_the_dry_run_surface_also_carries_the_attribution_payload(self):
        """1upba AC-3: content on the `_review_policy_receipt_diagnostics` surface.

        Stripping the attribution from that emit site survived the full module
        while the sibling test still passed, because the sibling asserts only
        the diagnostic code.
        """
        self._write_config(transition_policy="applies-from-next-prepare")
        wave_id, _wave_md, change_path = self._prepared_wave_with_change("dry-attr")
        self._record_readiness_approval(wave_id, "wave-council-readiness", "dryattr")
        change_path.write_text(
            change_path.read_text(encoding="utf-8").replace("1. x", "1. x and more"),
            encoding="utf-8",
        )
        resp = self._run_prepare(wave_id=wave_id, mode="dry_run")
        stale = [
            d for d in resp.get("diagnostics") or []
            if d["code"] == "review_policy_receipt_stale"
        ]
        self.assertTrue(stale, resp)
        message = " ".join(d["message"] for d in stale)
        self.assertIn("current receipt", message)
        self.assertIn("pending receipt", message)
        self.assertIn("digested change ids", message)
        self.assertIn("not attributable from persisted data", message)

    def test_a_mark_without_supersession_reports_no_supersession(self):
        """1upba AC-5, absence half.

        The mirror-image defect -- telling an operator their approvals lapsed
        when no receipt moved -- shipped unguarded: emitting a false
        `review_policy_receipt_superseded` on the receipt-neutral return
        survived the full module. Asserted as the ABSENCE of that code rather
        than an empty diagnostic list, because the deferral path returns
        fixture-dependent `action_diagnostics`.
        """
        self._write_config(transition_policy="applies-from-next-prepare")
        wave_id, _wave_md, _change_path = self._prepared_wave_with_change("mark-neutral")
        # A task mark is receipt-neutral: nothing is published, so nothing lapses.
        marked = self.srv._mark_change_item_response(
            self.root, wave_id, "1abc-bug sample", "do it.", "x",
            target_section="Tasks", mode="create",
        )
        self.assertEqual(marked["status"], "ok", marked)
        self.assertNotIn(
            "review_policy_receipt_superseded",
            [d["code"] for d in marked.get("diagnostics") or []],
            "a receipt-neutral mark must not claim approvals lapsed",
        )

    def test_policy_state_absent_with_no_error_refuses(self):
        """1upba AC-2 case (c): the fail-closed guard, asserted by outcome.

        Stubbing is legitimate here and only here: the plan records this branch
        as unreachable by construction on today's producer, so a real fixture
        cannot reach it. Case (d) by contrast is built from a real document,
        because its whole point is that an ordinary author can reach it.
        """
        self._write_config(transition_policy="applies-from-next-prepare")
        wave_id, _wave_md, _change_path = self._prepared_wave_with_change("none-empty")
        with patch.object(self.srv, "_prepare_policy_state", return_value=(None, ())) as _gate_mock_6:
            refused = self._record_readiness_approval(
                wave_id, "wave-council-readiness", "noneempty"
            )
            _gate_mock_6.assert_called()
        self.assertEqual(refused["status"], "error", refused)
        message = " ".join(d["message"] for d in refused["diagnostics"])
        self.assertIn("no state and no error", message)

    def test_the_stale_advisory_is_not_reported_twice(self):
        """The staleness message is reported once, by construction.

        History, because the mechanism changed twice. `1upba` shipped a
        `_seen_stale` dedupe for a genuine two-producer collision on the
        error-cause path. `1uugg` then guarded that block on
        `policy_state is not None`, and since `_prepare_policy_state` returns a
        state only from its single success return (always `errors == ()`), the
        two producers became mutually exclusive and the dedupe unreachable. Two
        delivery lanes independently proved it dead: deleting it survived all
        tests. The dedupe and its comment are gone.

        The PROPERTY is still worth pinning -- an operator must not be told the
        same thing twice -- so this test survives its mechanism, re-founded on
        what actually holds. It fails if a future change lets both producers
        fire again.
        """
        self._write_config(transition_policy="applies-from-next-prepare")
        wave_id, _wave_md, change_path = self._prepared_wave_with_change("no-dupe")
        change_path.write_text(
            change_path.read_text(encoding="utf-8")
            + "\n## Progress Log\n\n| Date | Update | Evidence |\n| --- | --- | --- |\n| x | y | z |\n",
            encoding="utf-8",
        )
        resp = self._run_prepare(wave_id=wave_id, mode="dry_run")
        messages = [
            d["message"] for d in resp.get("diagnostics") or []
            if d["code"] == "review_policy_receipt_stale"
        ]
        self.assertTrue(messages, resp)
        self.assertEqual(
            len(messages), len(set(messages)),
            "the same staleness message must not be reported twice",
        )

    def test_review_event_dry_run_previews_the_degraded_acceptance_warning(self):
        """1upba: a preview must not be quieter than the call it previews.

        The refusal branches already fire on dry-run; dropping only the
        degraded-acceptance warning made `dry_run` hide a caveat that `create`
        reports, which is the same asymmetry this change exists to remove.
        """
        self._write_config(transition_policy="applies-from-next-prepare")
        wave_id, _wave_md, change_path = self._prepared_wave_with_change("dry-warn")
        change_path.write_bytes(b"\xff\xfe not valid utf-8 \xff")
        self.srv.wf_review_event_response(
            self.root, wave_id=wave_id, event="run", mode="create",
            actor="wave-council", context_id="drywarn",
            approval_phase="readiness", run_kind="readiness", cycle=0,
        )
        preview = self.srv.wf_review_event_response(
            self.root, wave_id=wave_id, event="approval", mode="dry_run",
            signoff_key="wave-council-readiness", approval_phase="readiness",
            actor="wave-council", context_id="drywarn",
            fresh_context=True, independent=True,
            evidence={"observed": "preview", "artifact_or_test_id": "test:dry-warn"},
            integrity_checks=integrity_checks(),
        )
        self.assertIn(
            "review_policy_staleness_unverified",
            [d["code"] for d in preview.get("diagnostics") or []],
            "the preview must carry the same caveat the mutating call reports",
        )

    def test_attribution_reports_the_receipt_ids_by_value_and_in_order(self):
        """1upba AC-3: the ids are required CONTENT, not just labels.

        Asserting only the label pair let two mutants live: replacing both ids
        with `none`, and -- the harmful one -- SWAPPING current and pending, so
        the operator is told the superseded receipt is the new one. That is
        precisely the confusion AC-3 exists to remove.
        """
        self._write_config(transition_policy="applies-from-next-prepare")
        wave_id, wave_md, _change_path = self._prepared_wave_with_change("attr-ids")
        before = self.srv.current_policy_receipt(
            self.srv.resolve_review_authority(
                self.root, wave_md, wave_text=wave_md.read_text(encoding="utf-8")
            ).records
        )
        marked = self.srv._mark_change_item_response(
            self.root, wave_id, "1abc-bug sample", "AC-1", "~",
            target_section="Acceptance Criteria", mode="create",
            reason="Deferred so the supersession attribution is observable by value.",
        )
        self.assertEqual(marked["status"], "ok", marked)
        new_id = marked["data"]["review_receipt_refreshed"]["receipt_id"]
        message = " ".join(d["message"] for d in marked.get("diagnostics") or [])
        self.assertNotEqual(before["receipt_id"], new_id)
        self.assertIn(before["receipt_id"], message, "the superseded id must appear")
        self.assertIn(new_id, message, "the new current id must appear")
        # Order matters: swapping them inverts the operator-facing meaning.
        self.assertLess(
            message.index(f"superseded receipt {before['receipt_id']}"),
            message.index(f"new current receipt {new_id}"),
            "each id must sit under its own label, not the other's",
        )

    def test_an_ac_completion_mark_reports_no_supersession(self):
        """1upba AC-5 absence half, on the Acceptance Criteria path.

        The sibling test drives a Tasks mark, so a spurious diagnostic emitted
        only for `target_section == "Acceptance Criteria"` survived it. An AC
        `[x]` mark is receipt-neutral too and must stay silent.
        """
        self._write_config(transition_policy="applies-from-next-prepare")
        wave_id, _wave_md, _change_path = self._prepared_wave_with_change("ac-complete")
        marked = self.srv._mark_change_item_response(
            self.root, wave_id, "1abc-bug sample", "AC-1", "x",
            target_section="Acceptance Criteria", mode="create",
        )
        self.assertEqual(marked["status"], "ok", marked)
        self.assertNotIn(
            "review_policy_receipt_superseded",
            [d["code"] for d in marked.get("diagnostics") or []],
            "completing an AC publishes nothing, so nothing lapsed",
        )

    def test_the_ambiguous_heading_refusal_routes_recovery_to_the_change_doc(self):
        """1upba: the config arm's recovery routing was pinned, this one was not.

        Re-preparing cannot repair a duplicated heading any more than it can
        repair a bad config; both must route to the tool that can.
        """
        self._write_config(transition_policy="applies-from-next-prepare")
        wave_id, _wave_md, change_path = self._prepared_wave_with_change("ambig-route")
        change_path.write_text(
            change_path.read_text(encoding="utf-8")
            + "\n## Progress Log\n\n| Date | Update | Evidence |\n| --- | --- | --- |\n| x | y | z |\n",
            encoding="utf-8",
        )
        refused = self._record_readiness_approval(
            wave_id, "wave-council-readiness", "ambigroute"
        )
        self.assertEqual(refused["status"], "error", refused)
        tools = [t for d in refused["diagnostics"] for t in (d.get("recovery_tools") or [])]
        self.assertIn("wf_get_change", tools)
        self.assertNotIn("wf_prepare_wave", tools)

    def _wave_with_an_advisory_only_create(self, slug):
        """A governed wave whose only prepare diagnostic is advisory.

        Ordering matters and is the reason an earlier attempt at this test
        concluded the property was undeliverable: the placeholder edit must
        land BEFORE the readiness approval, or the edit moves the digest and
        lapses the approval, adding a blocking `missing_wave_council_signoff`
        that hides the behavior under test.
        """
        wave_id, wave_md, change_path = self._prepared_wave_with_change(slug)
        change_path.write_text(
            change_path.read_text(encoding="utf-8").replace(
                "| AC-1 | required | the thing. |",
                "| AC-1 | required / important / nice-to-have / not-this-scope |  |",
            ),
            encoding="utf-8",
        )
        text = wave_md.read_text(encoding="utf-8")
        ids = self.srv.lifecycle_gate_support._extract_change_ids_from_wave_text(text)
        state, errors = self.srv.lifecycle_gate_support._prepare_policy_state(self.root, wave_md, text, ids, {})
        self.assertEqual(errors, ())
        self.srv._publish_prepare_policy_state(self.root, wave_md, text, state)
        self._record_readiness_approval(wave_id, "wave-council-readiness", f"adv-{slug}")
        return wave_id, wave_md, change_path

    def test_an_advisory_only_create_publishes_and_activates(self):
        """1uugg AC-5: the publication guard is a WRITE.

        An earlier revision marked this `[~]` on the premise that publication
        rotates the receipt identity and stales the readiness approval in the
        same call, making activation unreachable. That is true only when
        `receipt_append_required` is True. On the ordinary ready-approve-create
        flow it is False, publication is a re-render, the approval stays
        current, and the wave activates -- so the requirement was satisfiable
        all along. Proved by spy trace during delivery review.
        """
        self._write_config(transition_policy="applies-from-next-prepare")
        wave_id, wave_md, _cp = self._wave_with_an_advisory_only_create("ac5-adv")

        published = []
        real = self.srv._publish_prepare_policy_state
        with patch.object(
            self.srv, "_publish_prepare_policy_state",
            side_effect=lambda *a, **k: (published.append(1), real(*a, **k))[1],
        ):
            resp = self._run_prepare(wave_id=wave_id, mode="create")

        codes = [(d["code"], d.get("advisory")) for d in resp.get("diagnostics") or []]
        self.assertEqual(
            codes, [("ac_priority_unpopulated", True), ("readiness_lane_approvals_missing", True)],
            "the fixture must produce only the two expected advisories and no blocker",
        )
        self.assertEqual(published, [1], "an advisory must not suppress publication")
        self.assertEqual(resp["status"], "ok")
        self.assertTrue(resp["data"].get("transitioned_to_active"))
        self.assertIn("Status: active", wave_md.read_text(encoding="utf-8"))

    def test_an_advisory_plus_a_blocker_does_not_publish(self):
        """1uugg AC-5b: the negative twin.

        Without it, a predicate that filters the list before the docs-gate
        diagnostics are appended satisfies AC-5 while publishing a receipt on a
        lint-failed wave. The blocker must be one appended BEFORE the
        publication guard -- `docs_lint_error` is the canonical choice, since
        `missing_wave_council_signoff` and `another_wave_active` are appended
        after it and would pass against pre-change code.
        """
        self._write_config(transition_policy="applies-from-next-prepare")
        wave_id, wave_md, _cp = self._wave_with_an_advisory_only_create("ac5b-adv")
        before_wave = wave_md.read_bytes()
        before_ledger = (wave_md.parent / "events.jsonl").read_bytes()

        published = []
        real = self.srv._publish_prepare_policy_state
        lint_bad = {"passed": False, "errors": ["ERROR: synthetic docs gate failure"],
                    "warnings": [], "output": ""}
        with patch.object(self.srv, "run_validate", return_value=lint_bad), \
             patch.object(self.srv, "run_garden", return_value=self.GARDEN_OK), \
             patch.object(self.srv, "_trigger_background_index_refresh_for_paths"), \
             patch.object(self.srv, "_publish_prepare_policy_state",
                          side_effect=lambda *a, **k: (published.append(1), real(*a, **k))[1]):
            resp = self.srv.wf_prepare_wave_response(self.root, wave_id=wave_id, mode="create")

        codes = [d["code"] for d in resp.get("diagnostics") or []]
        self.assertIn("ac_priority_unpopulated", codes, "the advisory must still be present")
        self.assertIn("docs_lint_error", codes, "the blocker must be present")
        self.assertEqual(resp["status"], "error")
        self.assertEqual(published, [], "a blocking diagnostic must suppress publication")
        self.assertEqual(wave_md.read_bytes(), before_wave)
        self.assertEqual((wave_md.parent / "events.jsonl").read_bytes(), before_ledger)

    def test_the_advisory_is_in_the_same_list_each_consumer_evaluates(self):
        """1uugg AC-5c: OBSERVED at each gate, not inferred from the outcome.

        An earlier version asserted publication happened, `status: ok`, and an
        exact envelope code list. A restored parallel advisory list merged only
        at the envelope satisfies all three, so the test could not tell a
        converted gate from an unconverted one -- exactly the two-list vacuity
        Requirement 4 exists to prevent.

        This replaces the advisory payload with a dict that records every
        `get("advisory")` call, so the assertion is that the three truthiness
        consumers each interrogated THAT object. A parallel list would leave
        the recorder untouched.
        """
        self._write_config(transition_policy="applies-from-next-prepare")

        class _RecordingDiagnostic(dict):
            probes = 0

            def get(self, key, default=None):
                if key == "advisory":
                    type(self).probes += 1
                return super().get(key, default)

        real_diagnostic = self.srv._diagnostic

        def _recording(code, message, **kwargs):
            payload = real_diagnostic(code, message, **kwargs)
            if code == "ac_priority_unpopulated":
                return _RecordingDiagnostic(payload)
            return payload

        with patch.object(self.srv.lifecycle_gate_support, "_diagnostic", side_effect=_recording) as _gate_mock_7:
            wave_id, _wave_md, _cp = self._wave_with_an_advisory_only_create("ac5c-obs")
            _RecordingDiagnostic.probes = 0
            resp = self._run_prepare(wave_id=wave_id, mode="create")
            _gate_mock_7.assert_called()

        self.assertEqual(resp["status"], "ok", resp)
        self.assertEqual(
            [d["code"] for d in resp.get("diagnostics") or []],
            ["ac_priority_unpopulated", "readiness_lane_approvals_missing"],
        )
        # Publication guard + both failure gates each evaluate the shared list.
        self.assertGreaterEqual(
            _RecordingDiagnostic.probes, 3,
            "the advisory must be interrogated by all three truthiness "
            f"consumers; it was probed {_RecordingDiagnostic.probes} time(s), "
            "which means at least one gate read a different list",
        )

    def test_dry_run_roster_drift_stays_a_preview(self):
        """1uugg AC-3b: the reclassification argued in Requirement 2.

        Roster drift is checked nowhere else in prepare and is reachable
        WITHOUT a pending mint -- the persisted value comes from the wave
        text's `Required review lanes` line while `receipt_append_required`
        comes from comparing receipt semantics.
        """
        self._write_config(transition_policy="applies-from-next-prepare")
        wave_id, wave_md, _cp = self._prepared_wave_with_change("ac3b-drift")
        text = wave_md.read_text(encoding="utf-8")
        persisted = self.srv.lifecycle_gate_support._extract_required_review_lanes(text)
        self.assertTrue(persisted, "fixture must persist a roster to drift from")
        # The edit must land BEFORE the approval: hand-editing `wave.md`
        # desyncs the Review Status projection, and the approval's write is what
        # re-syncs it. Editing after would add a blocking `review_evidence_invalid`
        # that hides the behavior under test.
        wave_md.write_text(
            text.replace(
                f"Required review lanes: {', '.join(persisted)}",
                "Required review lanes: qa-reviewer, security-reviewer",
            ),
            encoding="utf-8",
        )
        self._record_readiness_approval(wave_id, "wave-council-readiness", "ac3b")
        resp = self._run_prepare(wave_id=wave_id, mode="dry_run")
        stale = [d for d in resp.get("diagnostics") or []
                 if d["code"] == "review_policy_receipt_stale"]
        self.assertTrue(stale, resp)
        self.assertTrue(all(d.get("advisory") is True for d in stale))
        self.assertEqual(resp["status"], "dry_run")

    def test_the_two_in_prepare_stale_emissions_stay_blocking(self):
        """1uugg AC-10, first path: the `policy_state_errors` loop."""
        self._write_config(transition_policy="applies-from-next-prepare")
        wave_id, _wave_md, _cp = self._prepared_wave_with_change("ac10-block")
        cfg_path = self.root / "docs" / "workflow-config.json"
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        cfg["wave_review"] = "not an object"
        cfg_path.write_text(json.dumps(cfg), encoding="utf-8")
        resp = self._run_prepare(wave_id=wave_id, mode="dry_run")
        stale = [d for d in resp.get("diagnostics") or []
                 if d["code"] == "review_policy_receipt_stale"]
        self.assertTrue(stale, resp)
        self.assertTrue(
            any(d.get("advisory") is not True for d in stale),
            "a policy-state error must remain blocking even on the dry-run path",
        )
        self.assertEqual(resp["status"], "error")

    def test_a_publish_failure_emits_a_blocking_stale_diagnostic(self):
        """1uugg AC-10, SECOND path: the publish-failure handler.

        AC-10 names two in-prepare emissions. An earlier version exercised only
        the `policy_state_errors` loop, so the claim that both are covered was
        false. This one is reachable only when `_publish_prepare_policy_state`
        raises -- and if it were advisory, prepare would report `ok` after
        failing to write the roster and receipt.
        """
        self._write_config(transition_policy="applies-from-next-prepare")
        wave_id, wave_md, _cp = self._wave_with_an_advisory_only_create("ac10-pubfail")
        with patch.object(
            self.srv, "_publish_prepare_policy_state",
            side_effect=OSError("synthetic publication failure"),
        ):
            resp = self._run_prepare(wave_id=wave_id, mode="create")
        stale = [d for d in resp.get("diagnostics") or []
                 if d["code"] == "review_policy_receipt_stale"]
        self.assertTrue(stale, resp)
        self.assertIn("could not publish", " ".join(d["message"] for d in stale))
        self.assertTrue(
            all(d.get("advisory") is not True for d in stale),
            "a failed publication must block, never be advisory",
        )
        self.assertEqual(resp["status"], "error")
        self.assertNotIn("Status: active", wave_md.read_text(encoding="utf-8"))

    def test_the_other_callers_of_the_stale_helper_are_unaffected(self):
        """1uugg AC-10b: asserted PER CALLER, each verified to reach the helper.

        Two earlier forms were both weaker than the AC. The first called
        `_review_policy_receipt_diagnostics` directly, proving the default
        keyword but not that production callers preserve the payload. The
        second drove three tools but used one global flag, so an arm that
        contributed nothing was indistinguishable from one that did -- and its
        `wf_review_event` arm inspected the APPROVAL response, whose stale
        diagnostic comes from the `1upba` readiness-refusal path, not from this
        helper at all. The `run` response, the only `wf_review_event` call that
        reaches the helper, was discarded.

        This drives the three callers that surface the diagnostic in their
        response and asserts PER CALLER that each one did, and that the key is
        absent from it. `wf_close_wave` covers `_evaluate_shared_delivery_state`.

        `wf_review_event` is covered separately and deliberately: probed at both
        modes, its `run` path returns no diagnostics at all, and its approval
        path is refused by the `1upba` readiness-refusal recompute before
        `transact` runs, so neither response carries helper output. Asserting on
        either would be asserting on a different producer. What that caller
        actually consumes is the helper's DEFAULT invocation, which is checked
        directly below.
        """
        self._write_config(transition_policy="applies-from-next-prepare")
        wave_id, wave_md, change_path = self._prepared_wave_with_change("ac10b-real")
        self._record_readiness_approval(wave_id, "wave-council-readiness", "ac10b")
        change_path.write_text(
            change_path.read_text(encoding="utf-8").replace("1. x", "1. x and more"),
            encoding="utf-8",
        )

        responses = {
            "wf_review_wave": self.srv.wf_review_wave_response(
                self.root, wave_id=wave_id, phase="implementation"),
            "wf_implement_wave": self.srv.wf_implement_wave_response(
                self.root, wave_id=wave_id, mode="dry_run"),
            "wf_close_wave": self.srv.wf_close_wave_response(
                self.root, wave_id=wave_id, mode="dry_run"),
        }

        for tool, resp in responses.items():
            stale = [d for d in resp.get("diagnostics") or []
                     if d["code"] == "review_policy_receipt_stale"]
            with self.subTest(caller=tool):
                self.assertTrue(
                    stale,
                    f"{tool} must surface the stale receipt, or this arm proves "
                    "nothing about payload preservation",
                )
                for d in stale:
                    self.assertNotIn(
                        "advisory", d,
                        f"{tool} must receive it with the key ABSENT, not merely "
                        "false; tagging the shared construction rather than "
                        "prepare's call site would stamp it here",
                    )

        # The fourth caller, `wf_review_event`, consumes the helper's default
        # invocation inside `transact()` without surfacing it. Check that seam
        # directly rather than through a response that never carries it.
        text = wave_md.read_text(encoding="utf-8")
        default = self.srv.lifecycle_gate_support._review_policy_receipt_diagnostics(self.root, wave_md, text)
        self.assertTrue(default, "the fixture must produce a pending mint")
        for d in default:
            self.assertNotIn("advisory", d, "the default invocation must not tag")

    def test_absent_wave_review_config_adds_no_stale_diagnostic_to_a_preview(self):
        """1uugg Requirement 8: classification changes, detection does not.

        The dry-run advisory call must see exactly the configuration prepare's
        own policy block saw; the helper's internal guard is one conjunct
        weaker, so an unguarded call turned a clean preview into `error`.
        """
        self._write_config(transition_policy="applies-from-next-prepare")
        wave_id, _wave_md, _cp = self._prepared_wave_with_change("absent-cfg")
        cfg_path = self.root / "docs" / "workflow-config.json"
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        cfg.pop("wave_review", None)
        cfg_path.write_text(json.dumps(cfg), encoding="utf-8")
        resp = self._run_prepare(wave_id=wave_id, mode="dry_run")
        self.assertNotIn(
            "review_policy_receipt_stale",
            [d["code"] for d in resp.get("diagnostics") or []],
            "an absent wave_review section must not make the preview report a "
            "stale receipt; prepare's own policy block skips silently here",
        )

    def test_policy_input_errors_carry_a_typed_cause(self):
        """1upba Requirement 2: discriminate by cause, never by message prose."""
        tagged = self.srv.lifecycle_gate_support.PolicyInputError("ambiguous_headings", "boom")
        self.assertIsInstance(tagged, str)
        self.assertEqual(self.srv.lifecycle_gate_support.policy_input_error_cause(tagged), "ambiguous_headings")
        self.assertEqual(self.srv.lifecycle_gate_support.policy_input_error_cause("legacy"), "unknown")
        self.assertNotIn(
            "ambiguous_headings", self.srv.POLICY_INPUT_DEGRADABLE_CAUSES,
            "an authoring defect must never degrade to a warning",
        )
        self.assertIn("read", self.srv.POLICY_INPUT_DEGRADABLE_CAUSES)

    def test_policy_reader_no_longer_exposes_required_for_all_waves(self):
        """1tsyx AC-5 red-first: the parsed-but-unused flag is removed."""
        self._write_config()
        self.assertNotIn("required_for_all_waves", self.srv.lifecycle_gate_support._read_wave_council_policy(self.root))

    def test_projection_keys_follow_explicit_review_policy(self):
        """1tsbu: disabled policy has no phantom Council projection rows."""
        review = sys.modules["review_evidence"]
        wave_text = (
            "# Wave\nStatus: planned\n\n"
            "## Participants\n\n- Required review lanes: `qa-reviewer`\n"
        )
        results = []
        expected = {
            True: (
                "wave-council-readiness",
                "wave-council-delivery",
                "qa-reviewer",
                "operator-signoff",
            ),
            False: ("qa-reviewer", "operator-signoff"),
        }
        for enabled in (True, False):
            self._write_config(enabled=enabled)
            keys = review.required_review_status_keys(self.root, wave_text, ())
            results.append(keys)
            self.assertEqual(keys, expected[enabled])
        self.assertNotEqual(results[0], results[1])

    def _write_config_with_new_key(self, enabled=True, transition_policy=""):
        """Wave 1p337 (1p336): write config using the new `wave_review` key."""
        cfg = {
            "lifecycle_id_policy": {"epoch_utc": "2020-02-02T02:02:00Z", "hour_offset": 0},
            "wave_review": {
                "enabled": enabled,
                "delivery_mode": "universal" if enabled else "disabled",
                "transition_policy": transition_policy,
                "phases": {
                    "prepare": {"signoff_key": "wave-council-readiness", "moderator_role": "wave-council"},
                    "review": {"signoff_key": "wave-council-delivery", "moderator_role": "wave-council"},
                },
            },
        }
        (self.root / "docs" / "workflow-config.json").write_text(json.dumps(cfg), encoding="utf-8")

    def test_reader_uses_new_wave_review_key_when_present(self):
        """Wave 1p337 (1p336) AC-1: `_read_wave_council_policy()` reads `wave_review`
        first and returns its policy dict when present."""
        self._write_config_with_new_key(enabled=True)
        policy = self.srv.lifecycle_gate_support._read_wave_council_policy(self.root)
        self.assertTrue(policy, msg="policy must be returned when `wave_review` is set and enabled")
        self.assertIn("phases", policy)

    def test_reader_ignores_legacy_wave_council_policy_key(self):
        """Wave 1p5b4: the legacy `wave_council_policy` reader-fallback was removed —
        a config with only the legacy key yields no policy (the upgrade convergence
        rewrites it to `wave_review` before runtime)."""
        self._write_config(enabled=True)  # canonical `wave_review` from the helper
        # Re-author with ONLY the legacy key to prove it is no longer honored.
        cfg = {"lifecycle_id_policy": {"epoch_utc": "2020-02-02T02:02:00Z", "hour_offset": 0},
               "wave_council_policy": {"enabled": True,
                                       "phases": {"prepare": {"signoff_key": "wave-council-readiness"}}}}
        (self.root / "docs" / "workflow-config.json").write_text(json.dumps(cfg), encoding="utf-8")
        policy = self.srv.lifecycle_gate_support._read_wave_council_policy(self.root)
        self.assertEqual(policy, {}, msg="legacy `wave_council_policy` must no longer resolve")

    def test_reader_prefers_new_key_when_both_present(self):
        """Wave 1p337 (1p336) AC-3: when both keys are set, `wave_review` wins and
        `wave_council_policy` is ignored entirely (no legacy-precedence ambiguity)."""
        cfg = {
            "lifecycle_id_policy": {"epoch_utc": "2020-02-02T02:02:00Z", "hour_offset": 0},
            # New key: enabled → policy should be returned
            "wave_review": {
                "enabled": True,
                "phases": {
                    "prepare": {"signoff_key": "wave-council-readiness", "moderator_role": "wave-council"},
                    "review": {"signoff_key": "wave-council-delivery", "moderator_role": "wave-council"},
                },
            },
            # Legacy key: disabled → would return {} if it won; precedence test
            "wave_council_policy": {"enabled": False},
        }
        (self.root / "docs" / "workflow-config.json").write_text(json.dumps(cfg), encoding="utf-8")
        policy = self.srv.lifecycle_gate_support._read_wave_council_policy(self.root)
        self.assertTrue(policy, msg="new-key precedence: `wave_review.enabled=True` must win over legacy `enabled=False`")


class HarnessCoverageAuditTests(unittest.TestCase):
    """12ed1-feat harness-coverage-metrics: _audit_harness_coverage dimensions."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        _make_repo(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def _write_config(self, extra):
        cfg = {"lifecycle_id_policy": {"epoch_utc": "2020-02-02T02:02:00Z", "hour_offset": 0}, **extra}
        (self.root / "docs" / "workflow-config.json").write_text(json.dumps(cfg), encoding="utf-8")

    def test_no_config_returns_zero_coverage(self):
        result = self.srv._audit_harness_coverage(self.root)
        self.assertEqual(result["covered_count"], 0)
        self.assertEqual(result["coverage_ratio"], "0/3")

    def test_sensors_cover_maintainability(self):
        self._write_config({"sensors": [{"name": "lint", "command": ["true"], "dimension": "maintainability"}]})
        result = self.srv._audit_harness_coverage(self.root)
        self.assertTrue(result["dimensions"]["maintainability"]["covered"])

    def test_architecture_lane_covers_architecture(self):
        self._write_config({"required_review_lanes": ["architecture-review"]})
        result = self.srv._audit_harness_coverage(self.root)
        self.assertTrue(result["dimensions"]["architecture"]["covered"])

    def test_security_lane_covers_behaviour(self):
        self._write_config({"required_review_lanes": ["security-review"]})
        result = self.srv._audit_harness_coverage(self.root)
        self.assertTrue(result["dimensions"]["behaviour"]["covered"])

    def test_full_coverage(self):
        self._write_config({
            "sensors": [{"name": "lint", "command": ["true"], "dimension": "maintainability"}],
            "required_review_lanes": ["architecture-review", "security-review"],
        })
        result = self.srv._audit_harness_coverage(self.root)
        self.assertEqual(result["covered_count"], 3)
        self.assertEqual(result["coverage_ratio"], "3/3")


class WavePrepareCouncilGateTests(unittest.TestCase):
    """12sp5: wf_prepare_wave council verdict gate — AC-1, AC-2, AC-3, AC-4."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))
        (self.root / "docs" / "agents" / "journals").mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self.tmp.cleanup()

    def _make_wave(self, slug: str) -> str:
        wave_result = self.srv.wf_create_wave_response(self.root, slug, mode="create")
        wave_id = wave_result["data"]["wave_id"]
        change = self.srv.new_change(self.root, "feat", f"{slug}-change")
        self.srv.wf_add_change_response(self.root, wave_id, change["id"], mode="create")
        journal = self.root / "docs" / "agents" / "journals" / "wave-coordinator.md"
        prior = journal.read_text(encoding="utf-8") if journal.exists() else "# Journal\n"
        journal.write_text(prior + f"\nwave-id: `{wave_id}`\n", encoding="utf-8")
        return wave_id

    def _add_verdict(self, wave_id: str) -> None:
        _append_review_run(self.root, wave_id, kind="readiness")
        _append_typed_approval(
            self.root,
            wave_id,
            "wave-council-readiness",
            actor="wave-council",
        )
        wave_md = self.root / "docs" / "waves" / wave_id / "wave.md"
        wave_md.write_text(
            wave_md.read_text(encoding="utf-8")
            + f"\n## Review Checkpoints\n\n{_prepare_council_verdict_line()}\n",
            encoding="utf-8",
        )

    def _add_invalid_verdict(self, wave_id: str) -> None:
        wave_md = self.root / "docs" / "waves" / wave_id / "wave.md"
        wave_md.write_text(
            wave_md.read_text(encoding="utf-8")
            + "\n## Review Checkpoints\n\n- **Prepare-phase Wave Council [prepare-council] — 2026-05-21: PASS** (moderator: wave-council; seats: red-team; rotating-seat: none)\n",
            encoding="utf-8",
        )

    def test_prepare_create_blocked_without_council_verdict(self):
        """Declared Prepare blocks without the current typed readiness authority."""
        wave_id = self._make_wave("council-gate-block")
        with patch.object(self.srv, "run_garden", return_value={"passed": True, "files_updated": 0, "updated": [], "output": ""}):
            with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
                result = self.srv.wf_prepare_wave_response(self.root, wave_id, mode="create")
        self.assertEqual(result["status"], "error")
        codes = [d.get("code") for d in result.get("diagnostics", [])]
        self.assertIn("missing_wave_council_signoff", codes)
        self.assertIn("council_brief", result["data"])
        # Wave must not have transitioned to active
        wave_md = self.root / "docs" / "waves" / wave_id / "wave.md"
        self.assertNotIn("Status: active", wave_md.read_text(encoding="utf-8"))

    def test_prepare_create_succeeds_with_council_verdict(self):
        """Declared Prepare succeeds with current typed readiness authority."""
        wave_id = self._make_wave("council-gate-pass")
        self._add_verdict(wave_id)
        with patch.object(self.srv, "run_garden", return_value={"passed": True, "files_updated": 0, "updated": [], "output": ""}):
            with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
                result = self.srv.wf_prepare_wave_response(self.root, wave_id, mode="create")
        self.assertEqual(result["status"], "ok")
        wave_md = self.root / "docs" / "waves" / wave_id / "wave.md"
        self.assertIn("Status: active", wave_md.read_text(encoding="utf-8"))

    def test_prepare_create_blocks_on_malformed_council_verdict(self):
        """Malformed prose is inert when declared typed readiness is current."""
        wave_id = self._make_wave("council-gate-invalid")
        _append_review_run(self.root, wave_id, kind="readiness")
        _append_typed_approval(
            self.root,
            wave_id,
            "wave-council-readiness",
            actor="wave-council",
        )
        self._add_invalid_verdict(wave_id)
        with patch.object(self.srv, "run_garden", return_value={"passed": True, "files_updated": 0, "updated": [], "output": ""}):
            with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
                result = self.srv.wf_prepare_wave_response(self.root, wave_id, mode="create")
        self.assertEqual(result["status"], "ok")
        codes = [d.get("code") for d in result.get("diagnostics", [])]
        self.assertNotIn("prepare_council_verdict_invalid", codes)

    def test_prepare_dry_run_includes_council_brief_without_verdict(self):
        """AC-1: dry_run includes council_brief when no verdict is present."""
        wave_id = self._make_wave("council-brief-dry-run")
        with patch.object(self.srv, "run_garden", return_value={"passed": True, "files_updated": 0, "updated": [], "output": ""}):
            with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
                result = self.srv.wf_prepare_wave_response(self.root, wave_id, mode="dry_run")
        self.assertIn("council_brief", result.get("data", {}))
        brief = result["data"]["council_brief"]
        self.assertEqual(brief["fixed_seat"], "red-team")
        self.assertIn("wave_id", brief)

    def test_rotating_seat_selected_for_seed_wave(self):
        """AC-2: docs-contract-reviewer is selected for waves referencing seed/prompt changes."""
        wave_id = self._make_wave("seed-prompt-wave")
        # Append seed/prompt keywords to the wave change doc
        wave_md = self.root / "docs" / "waves" / wave_id / "wave.md"
        wave_md.write_text(
            wave_md.read_text(encoding="utf-8").replace(
                "## Wave Summary",
                "## Wave Summary\n\nThis wave authors new seed prompts and updates prompt templates.\n",
            ),
            encoding="utf-8",
        )
        with patch.object(self.srv, "run_garden", return_value={"passed": True, "files_updated": 0, "updated": [], "output": ""}):
            with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
                result = self.srv.wf_prepare_wave_response(self.root, wave_id, mode="dry_run")
        brief = result["data"]["council_brief"]
        self.assertEqual(brief["rotating_seat"], "docs-contract-reviewer")

    def test_rotating_seat_selected_for_security_wave(self):
        """AC-2: security-reviewer is selected for waves referencing auth/trust boundary changes."""
        wave_id = self._make_wave("auth-security-wave")
        wave_md = self.root / "docs" / "waves" / wave_id / "wave.md"
        wave_md.write_text(
            wave_md.read_text(encoding="utf-8").replace(
                "## Wave Summary",
                "## Wave Summary\n\nThis wave updates authentication middleware and trust boundary checks.\n",
            ),
            encoding="utf-8",
        )
        with patch.object(self.srv, "run_garden", return_value={"passed": True, "files_updated": 0, "updated": [], "output": ""}):
            with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
                result = self.srv.wf_prepare_wave_response(self.root, wave_id, mode="dry_run")
        brief = result["data"]["council_brief"]
        self.assertEqual(brief["rotating_seat"], "security-reviewer")


class ReviewPhaseAliasTests(unittest.TestCase):
    """The approval-phase vocabulary is accepted on the review-phase argument.

    Nothing pinned this: no test in the suite passed `readiness` or `delivery`
    as `phase`. That gap is why the wrapper regression below went unnoticed.
    """

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        # A real wave: the wave-not-found path returns before `phase` is ever
        # placed in the response, so it cannot show resolution.
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        (self.root / "docs").mkdir(parents=True)
        (self.root / "docs" / "workflow-config.json").write_text(
            json.dumps({
                "lifecycle_id_policy": {"epoch_utc": "2020-02-02T02:02:00Z", "hour_offset": 0},
                "wave_review": {"enabled": True, "delivery_mode": "targeted"},
            }),
            encoding="utf-8",
        )
        from server_tools_support import make_declared_wave, declared_wave_doc_gates
        from test_declared_wave_fixtures import fixture_doc_stubs
        stubs = fixture_doc_stubs()
        with declared_wave_doc_gates(self.srv, stubs):
            made = self.srv.new_change(self.root, "feat", "sample", change_id="1200a-feat sample")
        (self.root / made["path"]).write_text(
            "# Change\nChange ID: `1200a-feat sample`\n\n## Scope\n\nWork.\n", encoding="utf-8")
        self.wave_id, self.wave_md = make_declared_wave(self.srv, self.root, "sample",
            status="implementing", change_ids=("1200a-feat sample",), doc_gate_stubs=stubs)

    def _resolved(self, phase):
        return self.srv.wf_review_wave_response(self.root, self.wave_id, phase=phase)

    def test_approval_phase_words_map_onto_review_phases(self):
        for supplied, expected in (
            ("readiness", "prepare"),
            ("delivery", "implementation"),
            ("prepare", "prepare"),
            ("implementation", "implementation"),
        ):
            with self.subTest(phase=supplied):
                data = self._resolved(supplied).get("data", {})
                self.assertEqual(
                    data.get("phase"), expected, f"{supplied} did not map to {expected}"
                )

    def test_an_unknown_phase_is_rejected_and_names_the_mapping(self):
        result = self._resolved("nonsense")
        self.assertEqual(result["status"], "error")
        message = " ".join(d.get("message", "") for d in result.get("diagnostics", []))
        self.assertIn("prepare", message)
        self.assertIn("implementation", message)
        # The mapping is what a confused caller needs, not just the valid list.
        self.assertIn("readiness", message)
        self.assertIn("delivery", message)

    def test_the_wrapper_reads_the_resolved_phase_not_the_caller_spelling(self):
        """Regression: `phase='delivery'` must earn the same CE treatment.

        The wrapper derived `is_implementation_phase` from the raw argument, so
        an accepted spelling returned a fully green review while publishing no
        implement-stage accumulation, with no diagnostic. Assert the derivation
        the wrapper performs, against both spellings of the same phase.
        """
        # Scope the haystack to the registration block. Passing the whole
        # 1.4 MB module dumps all of it into the failure output.
        source = Path(self.srv.__file__).read_text(encoding="utf-8")
        idx = source.index('_ensure_no_extra_args("wf_review_wave"')
        window = source[idx : source.index("\n        )", source.index(
            'focus_stage="review"', idx))]
        self.assertNotIn(
            'is_implementation_phase = (phase or "").strip().lower()',
            window,
            "wrapper is deriving the phase from the caller's raw spelling again",
        )
        # Both spellings of the same phase must reach the same derivation. The
        # authoritative pin for the predicate itself lives in
        # test_server_context_efficiency, which is the only module that invokes
        # register_mcp_surface and can therefore reach the wrapper closure.
        for supplied in ("implementation", "delivery"):
            with self.subTest(phase=supplied):
                data = self._resolved(supplied).get("data", {})
                self.assertEqual(
                    str(data.get("phase") or "").strip().lower(), "implementation",
                    f"{supplied} did not resolve to the implementation phase",
                )


class ReceiptSemanticCanonicalInputTests(unittest.TestCase):
    """Every receipt-semantic reader consumes the same canonical carrier.

    Lane scoring canonicalized its input; trigger extraction and seat selection
    did not. A Progress Log row is mandated real-time tracking, so one carrying
    a trigger word could flip `delivery_council_required`, supersede the receipt
    and lapse approvals, while `policy_input_digest` stayed byte-identical and
    no diagnostic could explain it.
    """

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    CHANGE_ID = "1200a-feat sample"

    def _doc(self, *, trigger_in_progress_log: bool) -> str:
        """The SAME trigger word, moved between a digested and an excluded section."""
        row = "| 2026-08-06 | Repaired the windows path handling. | log |"
        scope = "Portable work." if trigger_in_progress_log else "Rework the windows path handling."
        return (
            f"# Change\nChange ID: `{self.CHANGE_ID}`\n\n"
            f"## Scope\n\n{scope}\n\n"
            "## Progress Log\n\n| Date | Update | Evidence |\n| --- | --- | --- |\n"
            f"{row if trigger_in_progress_log else '| 2026-08-06 | Did work. | log |'}\n"
        )

    def _policy_state(self, doc_text: str):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        (root / "docs").mkdir(parents=True)
        (root / "docs" / "workflow-config.json").write_text(
            json.dumps({
                "lifecycle_id_policy": {"epoch_utc": "2020-02-02T02:02:00Z", "hour_offset": 0},
                "wave_review": {"enabled": True, "delivery_mode": "targeted"},
            }),
            encoding="utf-8",
        )
        wave_dir = root / "docs" / "waves" / "0aaaa sample"
        wave_dir.mkdir(parents=True)
        wave_md = wave_dir / "wave.md"
        wave_text = (
            # component-fixture: _policy_state exercises this input representation directly
            "# Wave Record\n\nStatus: implementing\nreview-evidence-source: events.jsonl\n"
            "wave-id: `0aaaa sample`\n\n"
            f"## Changes\n\nChange ID: `{self.CHANGE_ID}`\nChange Status: `active`\n"
        )
        wave_md.write_text(wave_text, encoding="utf-8")
        (wave_dir / f"{self.CHANGE_ID}.md").write_text(doc_text, encoding="utf-8")
        (wave_dir / "events.jsonl").write_text("", encoding="utf-8")
        state, errors = self.srv.lifecycle_gate_support._prepare_policy_state(
            root, wave_md, wave_text, [self.CHANGE_ID], {},
            change_text_overrides={self.CHANGE_ID: doc_text},
        )
        self.assertEqual(errors, (), errors)
        self.assertIsNotNone(state, "policy state did not build")
        return state

    def test_a_progress_log_row_cannot_change_council_requirement(self):
        """The defect was the SERVER passing raw text, not the helper being wrong.

        Both fixtures carry the identical trigger word; only its section differs.
        The Progress Log is excluded from the digest, so a row there must not
        move a receipt-semantic field. Otherwise a mandated real-time-tracking
        row supersedes the receipt and lapses approvals while
        `policy_input_digest` stays byte-identical, leaving nothing able to
        explain it.
        """
        excluded = self._policy_state(self._doc(trigger_in_progress_log=True))
        digested = self._policy_state(self._doc(trigger_in_progress_log=False))

        # Control: the word genuinely triggers when it sits in a digested
        # section. Without this the assertion below could pass on a fixture that
        # never triggered at all.
        self.assertTrue(
            digested["delivery_council_required"],
            "fixture no longer triggers from ## Scope; the test would be vacuous",
        )
        self.assertFalse(
            excluded["delivery_council_required"],
            "a ## Progress Log row reached council selection",
        )

    def test_a_progress_log_row_cannot_choose_the_receipt_council_seat(self):
        """The seat reader is a second receipt-semantic consumer of the same text.

        `delivery_council_required` and the persisted `council_seats` are read
        by two different calls. Pinning only the first left the second free to
        pick a seat out of Progress Log narration, contradicting the comment at
        the call site that binds seat selection to admitted change bytes.
        """
        # "refactor" selects architecture-reviewer; "windows" does not move the
        # seat at all, so the seat probe needs its own word.
        def doc(*, in_progress_log: bool) -> str:
            word = "Reworked the layering refactor."
            scope = "Portable work." if in_progress_log else word
            row = word if in_progress_log else "Did work."
            return (
                f"# Change\nChange ID: `{self.CHANGE_ID}`\n\n"
                f"## Scope\n\n{scope}\n\n"
                "## Progress Log\n\n| Date | Update | Evidence |\n| --- | --- | --- |\n"
                f"| 2026-08-06 | {row} | log |\n"
            )

        excluded = self._policy_state(doc(in_progress_log=True))
        digested = self._policy_state(doc(in_progress_log=False))
        self.assertEqual(
            digested["receipt"]["council_seats"], ["red-team", "architecture-reviewer"],
            "fixture no longer moves the seat; the assertion below would be vacuous",
        )
        self.assertEqual(
            excluded["receipt"]["council_seats"], ["red-team"],
            "a ## Progress Log row selected the receipt's council seat",
        )


class PrepareCouncilVerdictTemplateTests(unittest.TestCase):
    """1p9pk AC-1/AC-2/AC-5: verdict template de-dup, replace-me placeholder, code-grounded brief."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def _template_seats_field(self, rotating_seat):
        template = self.srv.lifecycle_gate_support._prepare_council_verdict_template(rotating_seat)
        match = re.search(r"seats: (?P<seats>[^;]*);", template)
        self.assertIsNotNone(match, f"template has no seats: field: {template}")
        return template, match.group("seats")

    def test_receipt_binding_rebuilds_every_string_that_names_the_seat(self):
        """One response must never advertise two rosters.

        The binding overwrites `rotating_seat` and `council_seats` from the
        receipt. `instructions` and `verdict_format` also embed the seat, so
        leaving them at their wave-text value made the authoritative fields and
        the copy-paste template disagree: an agent following the template
        recorded a verdict the seat-alignment check then rejected against the
        very roster the same response had bound.
        """
        brief = self.srv.lifecycle_gate_support._build_prepare_council_brief(
            "w1", "Wave text naming a security-reviewer boundary", ["c1"]
        )
        self.assertEqual(brief["rotating_seat"], "security-reviewer")

        bound = self.srv._bind_prepare_council_brief_to_receipt(
            brief, {"council_seats": ["red-team", "code-reviewer"]}
        )
        seat = bound["rotating_seat"]
        self.assertEqual(seat, "code-reviewer")
        # Every surface that names a seat must name the SAME seat.
        for field in ("verdict_format", "instructions"):
            found = re.findall(r"rotating-seat: ([a-z-]+)", bound[field])
            self.assertTrue(found, f"{field} names no rotating seat: {bound[field]!r}")
            self.assertEqual(
                set(found), {seat},
                f"{field} still names a superseded seat: {found} != {seat}",
            )
        # Deliberately NOT asserting the superseded name is absent entirely:
        # `security-reviewer` also appears in the template's static example seat
        # list, which is unrelated to the rotating pick. The `rotating-seat:`
        # field checked above is the one that must agree.

    def test_template_dedups_security_reviewer_rotating_pick(self):
        """AC-1: security-reviewer rotating pick collides with the fixed seat — appears exactly once."""
        template, seats = self._template_seats_field("security-reviewer")
        self.assertEqual(seats.count("security-reviewer"), 1)
        # The served-as-both signal is preserved losslessly in the rotating-seat field.
        self.assertIn("rotating-seat: security-reviewer;", template)

    def test_template_dedups_architecture_reviewer_rotating_pick(self):
        """AC-1: architecture-reviewer is also in the fixed-seat list — same collision, same de-dup."""
        template, seats = self._template_seats_field("architecture-reviewer")
        self.assertEqual(seats.count("architecture-reviewer"), 1)
        self.assertIn("rotating-seat: architecture-reviewer;", template)

    def test_template_appends_non_colliding_rotating_pick(self):
        """AC-1: a rotating pick outside the fixed list is still appended, once."""
        template, seats = self._template_seats_field("docs-contract-reviewer")
        self.assertEqual(seats.count("docs-contract-reviewer"), 1)
        self.assertIn("rotating-seat: docs-contract-reviewer;", template)

    def test_template_without_rotating_seat_lists_each_fixed_seat_once(self):
        """AC-1: no rotating pick — five fixed seats, each exactly once, rotating-seat: none."""
        template, seats = self._template_seats_field(None)
        for seat in ("red-team", "architecture-reviewer", "security-reviewer", "qa-reviewer", "reality-checker"):
            self.assertEqual(seats.count(seat), 1, f"{seat} must appear exactly once in {seats!r}")
        self.assertIn("rotating-seat: none;", template)

    def test_template_seat_list_is_replace_me_placeholder(self):
        """AC-2: the seat list reads as a template placeholder, not a real roster."""
        for rotating in (None, "security-reviewer", "docs-contract-reviewer"):
            _, seats = self._template_seats_field(rotating)
            self.assertIn("<replace with the seats actually run", seats)

    def test_template_still_parses_as_valid_verdict_line(self):
        """The de-dup'd placeholder template still matches the structured verdict parser
        (the example the brief hands out must be a syntactically valid line)."""
        template = self.srv.lifecycle_gate_support._prepare_council_verdict_template("security-reviewer")
        info = self.srv._prepare_council_verdict_info(
            "## Review Checkpoints\n\n" + template + "\n"
        )
        self.assertTrue(info["present"])
        self.assertEqual(info["missing_fields"], [])

    def test_brief_instructions_require_code_grounded_verification(self):
        """AC-5: the prepare-council brief instructions carry the code-grounded verification contract."""
        brief = self.srv.lifecycle_gate_support._build_prepare_council_brief("w1", "wave text", ["c1"])
        instructions = brief["instructions"]
        self.assertIn("code-grounded", instructions)
        self.assertIn("file:line sites and symbols must resolve", instructions)
        self.assertIn("censuses must be complete", instructions)
        self.assertIn("seats actually run", instructions)

    def test_brief_carries_the_finding_authoring_citation_rule(self):
        """1uu9y AC-5: the runtime brief is a consumer surface, not an exemption.

        Seeds 209 and 237 state the resolvable-anchor rule, but a council seat
        at readiness receives THIS string, not the seed.  Leaving it un-updated
        meant the one surface a seat actually reads kept only the verification
        half of the rule and never the authoring half.

        Pinned as clauses rather than one exact sentence because the brief
        deliberately compresses seed 237's wording; the load-bearing parts are
        the anchor vocabulary, the resolvability reason, and the carve-outs
        carrying the name-the-case-inline obligation.
        """
        instructions = self.srv.lifecycle_gate_support._build_prepare_council_brief(
            "w1", "wave text", ["c1"])["instructions"]
        for clause in (
            "cite a resolvable anchor",
            "rather than a bare file:line",
            "distinguishing expression",
            "resolves to today's text",
            "module-level constant block",
            "deliberately historical",
            "name that case inline",
        ):
            self.assertIn(clause, instructions, f"missing clause: {clause!r}")
        self.assertLess(
            instructions.index("Do not approve a plan"),
            instructions.index("cite a resolvable anchor"),
            "the authoring rule must follow the verification rule, so the "
            "exact-value pin over the verification sentence stays contiguous",
        )

    def test_brief_code_grounded_sentence_is_pinned_exactly(self):
        """1tmb4 AC-6 (server site): exact-value pin over the full contract sentence.

        The substring test above passes a reworded sentence that keeps the
        substrings (e.g. "each plan's" -> "each artifact's"); this pin does
        not.  Wording here intentionally differs from seed 237's rule ("each
        plan's" vs "the artifact's"); one pin cannot cover both sites.
        """
        brief = self.srv.lifecycle_gate_support._build_prepare_council_brief("w1", "wave text", ["c1"])
        pinned = (
            "Verification must be code-grounded: verify each plan's load-bearing "
            "claims against the actual tree, not against the plan's own prose — "
            "cited file:line sites and symbols must resolve, 'X already does Y' "
            "claims must hold in the code, and 'no other caller/site' censuses "
            "must be complete. Do not approve a plan whose claims were checked "
            "only against its own text."
        )
        self.assertIn(pinned, brief["instructions"])


class WaveImplementTests(unittest.TestCase):
    """12sqb: wf_implement_wave gate and wf_review_wave phase parameter — AC-1 through AC-10."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))
        (self.root / "docs" / "workflow-config.json").write_text(
            json.dumps({"wave_review": {"enabled": True, "delivery_mode": "universal"}}), encoding="utf-8"
        )
        (self.root / "docs" / "agents" / "journals").mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self.tmp.cleanup()

    def _make_wave(self, slug: str, status: str = "active") -> str:
        wave_result = self.srv.wf_create_wave_response(self.root, slug, mode="create")
        wave_id = wave_result["data"]["wave_id"]
        change = self.srv.new_change(self.root, "feat", f"{slug}-change")
        self.srv.wf_add_change_response(self.root, wave_id, change["id"], mode="create")
        wave_md = self.root / "docs" / "waves" / wave_id / "wave.md"
        if status != "planned":
            wave_md.write_text(wave_md.read_text(encoding="utf-8").replace("Status: planned", f"Status: {status}"), encoding="utf-8")
        journal = self.root / "docs" / "agents" / "journals" / "wave-coordinator.md"
        prior = journal.read_text(encoding="utf-8") if journal.exists() else "# Journal\n"
        journal.write_text(prior + f"\nwave-id: `{wave_id}`\n", encoding="utf-8")
        return wave_id

    def _add_council_verdict(self, wave_id: str) -> None:
        self._add_prepare_review_signoffs(wave_id, ["wave-council-readiness"])
        wave_md = self.root / "docs" / "waves" / wave_id / "wave.md"
        wave_md.write_text(
            wave_md.read_text(encoding="utf-8")
            + f"\n## Review Checkpoints\n\n{_prepare_council_verdict_line()}\n",
            encoding="utf-8",
        )

    def _add_prepare_review_signoffs(self, wave_id: str, lanes: list) -> None:
        """Record prepare-phase lane signoffs for a DECLARED (scaffolded) wave.

        Wave 1to78: scaffolded waves carry `review-evidence-source:
        events.jsonl`, so lane signoff currency derives exclusively from typed
        approval records; a `## Prepare Review Evidence` prose section is
        narrative there (LegacyProseGateParityTests keeps the undeclared-wave
        prose behavior pinned). This helper therefore appends the typed
        approvals through the canonical serializer and re-renders the
        projections.
        """
        _append_review_run(self.root, wave_id, kind="readiness")
        wave_md = self.root / "docs" / "waves" / wave_id / "wave.md"
        review = sys.modules["review_evidence"]
        records, errors = review.read_review_event_ledger(wave_md)
        assert not errors, errors
        policy = __import__("review_policy")
        receipt = policy.current_policy_receipt(records)
        selected_lanes = list(lanes)
        if receipt is None:
            wave_text = wave_md.read_text(encoding="utf-8")
            change_ids = self.srv.lifecycle_gate_support._extract_change_ids_from_wave_text(wave_text)
            brief = self.srv.lifecycle_gate_support._build_prepare_council_brief(
                wave_id, wave_text, change_ids
            )
            state, state_errors = self.srv.lifecycle_gate_support._prepare_policy_state(
                self.root, wave_md, wave_text, change_ids, brief
            )
            assert not state_errors, state_errors
            self.srv._publish_prepare_policy_state(
                self.root, wave_md, wave_text, state
            )
            records, errors = review.read_review_event_ledger(wave_md)
            assert not errors, errors
            receipt = policy.current_policy_receipt(records)
            selected_lanes = list(
                dict.fromkeys([*lanes, *state["required_lanes"]])
            )
        receipt_id = receipt["receipt_id"]
        records = (
            *records,
            *(
                {
                    **WaveLifecycleMutationTests._approval_record(
                        lane,
                        actor="wave-council" if lane == "wave-council-readiness" else lane,
                    ),
                    "approval_phase": "readiness",
                    "policy_receipt_id": receipt_id,
                }
                for lane in selected_lanes
            ),
        )
        review.review_event_path(wave_md).write_bytes(
            review.canonical_review_events_bytes(records)
        )
        wave_md.write_text(
            review.render_review_evidence_projection(
                wave_md.read_text(encoding="utf-8"), records
            ),
            encoding="utf-8",
        )
        self._reproject(wave_id)

    def _add_participants(self, wave_id: str, review_lanes: list) -> None:
        wave_md = self.root / "docs" / "waves" / wave_id / "wave.md"
        rows = "\n".join(f"| {lane} | review | scope |" for lane in review_lanes)
        roster = (
            "- Requested review lanes: "
            + (", ".join(review_lanes) if review_lanes else "none")
            + "\n- Required review lanes: none\n\n"
            + f"| Role | Lane | Scope |\n|------|------|-------|\n{rows}\n\n"
        )
        text = wave_md.read_text(encoding="utf-8")
        text = re.sub(
            r"(?ms)(^## Participants[ \t]*\n).*?(?=^## )",
            rf"\1\n{roster}",
            text,
            count=1,
        )
        wave_md.write_text(text, encoding="utf-8")
        self._reproject(wave_id)

    def _reproject(self, wave_id: str) -> None:
        """Reconcile the review projections after a direct wave.md text edit —
        the 1t3dm contract requires the projection to stay fresh whenever the
        derived signoff keys change (1t3gu: the scaffold now bakes the block,
        so key-changing edits must re-render it the same way an agent must)."""
        wave_md = self.root / "docs" / "waves" / wave_id / "wave.md"
        text = wave_md.read_text(encoding="utf-8")
        wave_md.write_text(
            self.srv._project_current_review_status(self.root, wave_md, text),
            encoding="utf-8",
        )

    # --- 1tsyx AC-8(b): producer and parser parity ------------------------

    def test_create_wave_emits_discoverable_empty_roster_both_parsers_agree_on(self):
        wave_id = self._make_wave("empty-roster-producer", status="planned")
        wave_md = self.root / "docs" / "waves" / wave_id / "wave.md"
        text = wave_md.read_text(encoding="utf-8")
        self.assertIn("## Participants", text)
        self.assertEqual(self.srv.lifecycle_gate_support._extract_required_review_lanes(text), [])
        review = sys.modules["review_evidence"]
        keys = review.required_review_status_keys(self.root, text, ())
        projected_lanes = [
            key for key in keys
            if key not in {
                "wave-council-readiness",
                "wave-council-delivery",
                "operator-signoff",
            }
        ]
        self.assertEqual(projected_lanes, [])

    def test_roster_extractors_preserve_duplicate_order_parity(self):
        text = (
            "# Wave\nStatus: active\n\n"
            "## Participants\n\n"
            "- Required review lanes: `qa-reviewer`, `code-reviewer`, `qa-reviewer`\n"
            "| Role | Lane | Scope |\n"
            "|------|------|-------|\n"
            "| security-reviewer | review | trust |\n"
            "| code-reviewer | review | code |\n"
        )
        server_lanes = self.srv.lifecycle_gate_support._extract_required_review_lanes(text)
        review = sys.modules["review_evidence"]
        keys = review.required_review_status_keys(self.root, text, ())
        projection_lanes = [
            key for key in keys
            if key not in {
                "wave-council-readiness",
                "wave-council-delivery",
                "operator-signoff",
            }
        ]
        self.assertEqual(server_lanes, ["qa-reviewer", "code-reviewer", "security-reviewer"])
        self.assertEqual(projection_lanes, server_lanes)

    def test_roster_extractors_agree_over_current_wave_corpus(self):
        repo = Path(self.srv.__file__).resolve().parents[3]
        wave_paths = sorted((repo / "docs" / "waves").glob("*/wave.md"))
        if not wave_paths:
            self.skipTest("repository wave corpus is unavailable")
        review = sys.modules["review_evidence"]
        mismatches = []
        for wave_md in wave_paths:
            text = wave_md.read_text(encoding="utf-8")
            server_lanes = self.srv.lifecycle_gate_support._extract_required_review_lanes(text)
            keys = review.required_review_status_keys(repo, text, ())
            projection_lanes = [
                key for key in keys
                if key not in {
                    "wave-council-readiness",
                    "wave-council-delivery",
                    "operator-signoff",
                }
            ]
            if projection_lanes != server_lanes:
                mismatches.append((wave_md.parent.name, server_lanes, projection_lanes))
        self.assertEqual(mismatches, [])

    # --- AC-1/AC-2: wf_review_wave phase parameter ---

    def test_wf_review_wave_prepare_phase_checks_prepare_evidence_section(self):
        """AC-1: wf_review_wave(phase='prepare') gates on prepare-phase lane signoffs.

        Wave 1to78 update: this fixture wave is DECLARED (scaffolded), so the
        signoffs that satisfy the gate are typed approval records; the legacy
        `## Prepare Review Evidence` prose behavior for undeclared waves is
        pinned by LegacyProseGateParityTests instead."""
        wave_id = self._make_wave("review-prepare")
        self._add_participants(wave_id, ["code-reviewer"])
        # No signoffs yet
        with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
            result = self.srv.wf_review_wave_response(self.root, wave_id, phase="prepare")
        self.assertEqual(result["status"], "error")
        codes = [d.get("code") for d in result.get("diagnostics", [])]
        self.assertIn("missing_required_lane", codes)
        # With signoffs present
        self._add_prepare_review_signoffs(wave_id, ["code-reviewer"])
        with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
            result = self.srv.wf_review_wave_response(self.root, wave_id, phase="prepare")
        self.assertEqual(result["status"], "ok")

    def test_wf_review_wave_implementation_phase_is_default_behavior(self):
        """AC-2: wf_review_wave(phase='implementation') behaves identically to current wf_review_wave."""
        wave_id = self._make_wave("review-impl")
        with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
            default_result = self.srv.wf_review_wave_response(self.root, wave_id)
            impl_result = self.srv.wf_review_wave_response(self.root, wave_id, phase="implementation")
        self.assertEqual(default_result["status"], impl_result["status"])
        self.assertEqual(default_result["data"]["phase"], "implementation")
        self.assertEqual(impl_result["data"]["phase"], "implementation")

    def test_wf_review_wave_prepare_does_not_check_review_evidence(self):
        """AC-1: prepare phase does not interact with ## Review Evidence."""
        wave_id = self._make_wave("review-prepare-isolation")
        # Add an operator-signoff to Review Evidence (implementation phase style)
        wave_md = self.root / "docs" / "waves" / wave_id / "wave.md"
        wave_md.write_text(wave_md.read_text(encoding="utf-8").replace(
            "- operator-signoff: <approved when operator confirms closure>",
            "- operator-signoff: approved",
        ), encoding="utf-8")
        # prepare phase should still fail (no Prepare Review Evidence) despite impl phase having signoff
        with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
            result = self.srv.wf_review_wave_response(self.root, wave_id, phase="prepare")
        # No lanes required in this wave → should pass since no required_lanes
        self.assertEqual(result["data"]["phase"], "prepare")

    # --- AC-3/AC-4: wf_implement_wave gate checks ---

    def test_wf_implement_wave_blocked_without_council_readiness_approval(self):
        """AC-3: declared activation requires current typed council readiness."""
        wave_id = self._make_wave("impl-no-council")
        result = self.srv.wf_implement_wave_response(self.root, wave_id, mode="create")
        self.assertEqual(result["status"], "error")
        codes = [d.get("code") for d in result.get("diagnostics", [])]
        self.assertIn("missing_wave_council_signoff", codes)

    def test_wf_implement_wave_blocked_without_prepare_review(self):
        """AC-4: wf_implement_wave returns error when prepare-phase lane review is incomplete."""
        wave_id = self._make_wave("impl-no-review")
        self._add_participants(wave_id, ["code-reviewer"])
        self._add_council_verdict(wave_id)
        # Retain the Council approval but remove the independently required
        # lane so this fixture exercises the incomplete-roster branch.
        wave_md = self.root / "docs" / "waves" / wave_id / "wave.md"
        review = sys.modules["review_evidence"]
        records, errors = review.read_review_event_ledger(wave_md)
        self.assertEqual(errors, ())
        records = tuple(
            record
            for record in records
            if not (
                record.get("claim_id") == "approval:code-reviewer"
            )
        )
        review.review_event_path(wave_md).write_bytes(
            review.canonical_review_events_bytes(records)
        )
        wave_md.write_text(
            self.srv._project_current_review_status(
                self.root,
                wave_md,
                review.render_review_evidence_projection(
                    wave_md.read_text(encoding="utf-8"), records
                ),
            ),
            encoding="utf-8",
        )
        result = self.srv.wf_implement_wave_response(self.root, wave_id, mode="create")
        self.assertEqual(result["status"], "error")
        codes = [d.get("code") for d in result.get("diagnostics", [])]
        self.assertIn("prepare_review_incomplete", codes)

    # --- AC-5: implementation context ---

    def test_wf_implement_wave_returns_ordered_changes_and_watchpoints(self):
        """AC-5: wf_implement_wave returns ordered changes and watchpoints when gates pass.

        Wave 1t9w9 journal retirement: the response key is `watchpoints` (renamed
        from `journal_watchpoints`, no alias) and must never regress to the old name."""
        wave_id = self._make_wave("impl-context")
        self._add_council_verdict(wave_id)
        result = self.srv.wf_implement_wave_response(self.root, wave_id, mode="dry_run")
        self.assertEqual(result["status"], "dry_run")
        data = result["data"]
        self.assertIn("ordered_changes", data)
        self.assertIn("watchpoints", data)
        self.assertNotIn("journal_watchpoints", data)
        self.assertIn("serialization_points", data)
        self.assertGreater(len(data["ordered_changes"]), 0)

    # --- AC-6/AC-7: status transition ---

    def test_wf_implement_wave_create_transitions_to_implementing(self):
        """AC-6: wf_implement_wave(mode='create') transitions wave status to implementing."""
        wave_id = self._make_wave("impl-create")
        self._add_council_verdict(wave_id)
        result = self.srv.wf_implement_wave_response(self.root, wave_id, mode="create")
        self.assertEqual(result["status"], "ok")
        wave_md = self.root / "docs" / "waves" / wave_id / "wave.md"
        self.assertIn("Status: implementing", wave_md.read_text(encoding="utf-8"))

    def test_wf_implement_wave_dry_run_does_not_write(self):
        """AC-7: wf_implement_wave(mode='dry_run') validates readiness without writing."""
        wave_id = self._make_wave("impl-dry-run")
        self._add_council_verdict(wave_id)
        original_text = (self.root / "docs" / "waves" / wave_id / "wave.md").read_text(encoding="utf-8")
        result = self.srv.wf_implement_wave_response(self.root, wave_id, mode="dry_run")
        self.assertEqual(result["status"], "dry_run")
        self.assertEqual((self.root / "docs" / "waves" / wave_id / "wave.md").read_text(encoding="utf-8"), original_text)

    # --- AC-8: implementing status handling ---

    def test_current_wave_includes_implementing_status(self):
        """AC-8: current_wave() returns implementing waves."""
        from server_impl import current_wave
        wave_id = self._make_wave("ac8-implementing", status="implementing")
        result = current_wave(self.root)
        self.assertIsNotNone(result)
        self.assertEqual(result["status"], "implementing")

    def test_wf_pause_wave_can_pause_implementing_wave(self):
        """AC-8: wf_pause_wave handles implementing status gracefully."""
        wave_id = self._make_wave("ac8-pause-impl", status="implementing")
        result = self.srv.wf_pause_wave_response(self.root, wave_id, mode="create")
        self.assertEqual(result["status"], "ok")
        wave_md = self.root / "docs" / "waves" / wave_id / "wave.md"
        self.assertIn("Status: paused", wave_md.read_text(encoding="utf-8"))

    def test_wf_implement_wave_already_implementing_returns_ok(self):
        """AC-8: wf_implement_wave on an already-implementing wave returns ok with advisory."""
        wave_id = self._make_wave("ac8-already-impl", status="implementing")
        result = self.srv.wf_implement_wave_response(self.root, wave_id, mode="create")
        self.assertEqual(result["status"], "ok")
        self.assertTrue(result["data"].get("already_implementing"))

    # --- AC-11: wf_add_change next_tools ---

    def test_wf_add_change_includes_wf_add_change_in_next_tools(self):
        """AC-11: wf_add_change includes wf_add_change in next_tools."""
        wave_result = self.srv.wf_create_wave_response(self.root, "ac11-wave", mode="create")
        wave_id = wave_result["data"]["wave_id"]
        change = self.srv.new_change(self.root, "feat", "ac11-change")
        result = self.srv.wf_add_change_response(self.root, wave_id, change["id"], mode="create")
        self.assertIn("wf_add_change", result.get("next_tools", []))


class WaveCloseSummaryGenerationTests(unittest.TestCase):
    """12sq4: wf_close_wave summary generation — AC-1 through AC-5."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def _make_closeable_wave(self, wave_id: str, change_id: str, completed_acs: list[str] | None = None, decisions: list[str] | None = None) -> Path:
        wave_dir = self.root / "docs" / "waves" / wave_id
        wave_dir.mkdir(parents=True, exist_ok=True)
        wave_md = wave_dir / "wave.md"
        wave_md.write_text(
            f"# Wave Record\n"
            f"wave-id: `{wave_id}`\n"
            f"Title: Test Wave Title\n"
            f"Status: active\n\n"
            f"## Changes\n\n"
            f"Change ID: `{change_id}`\n"
            f"Change Status: `complete`\n\n"
            f"## Wave Summary\n\n"
            f"*(Populated at closure.)*\n\n"
            f"## Review Evidence\n\n"
            f"- operator-signoff: approved\n",
            encoding="utf-8",
        )
        # Write a minimal change doc
        ac_lines = "\n".join(f"- [x] {ac}" for ac in (completed_acs or ["AC-1: Core behavior"]))
        decision_rows = "\n".join(f"| 2026-05-21 | {d} | reason | alternative |" for d in (decisions or []))
        decision_table = (
            "## Decision Log\n\n"
            "| Date | Decision | Reason | Alternatives |\n"
            "| ---- | -------- | ------ | ------------ |\n"
            f"{decision_rows}\n"
        ) if decisions else ""
        change_doc = wave_dir / f"{change_id}.md"
        change_doc.write_text(
            f"# Change Title For {change_id}\n\n"
            f"Change ID: `{change_id}`\n"
            f"Change Status: `complete`\n\n"
            f"## Acceptance Criteria\n\n{ac_lines}\n\n"
            f"{decision_table}",
            encoding="utf-8",
        )
        return wave_md

    def test_wf_close_wave_populates_wave_summary(self):
        """AC-1: After wf_close_wave, ## Wave Summary contains a populated paragraph."""
        wave_md = self._make_closeable_wave("1200a-summ-test", "1200a-feat-summ-change")
        with patch.object(self.srv, "run_garden", return_value={"passed": True, "files_updated": 0, "updated": [], "output": ""}):
            with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
                result = self.srv.wf_close_wave_response(self.root, "1200a-summ-test", mode="create")
        self.assertEqual(result["status"], "ok")
        closed_text = wave_md.read_text(encoding="utf-8")
        self.assertIn("Status: closed", closed_text)
        # Placeholder replaced
        self.assertNotIn("*(Populated at closure.)*", closed_text)
        # Summary contains wave_id or title
        wave_summary_body = closed_text.split("## Wave Summary")[1].split("## ")[0] if "## Wave Summary" in closed_text else ""
        self.assertTrue(len(wave_summary_body.strip()) > 0, "Wave Summary section must be populated")

    def test_wf_close_wave_summary_includes_change_details(self):
        """AC-2: Summary includes completed ACs and decision log entries."""
        wave_md = self._make_closeable_wave(
            "1200a-detail-test",
            "1200a-feat-detail",
            completed_acs=["AC-1: Core behavior", "AC-2: Edge case handling"],
            decisions=["Use structured extraction instead of LLM inference"],
        )
        with patch.object(self.srv, "run_garden", return_value={"passed": True, "files_updated": 0, "updated": [], "output": ""}):
            with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
                result = self.srv.wf_close_wave_response(self.root, "1200a-detail-test", mode="create")
        self.assertEqual(result["status"], "ok")
        summary = result["data"].get("wave_summary", "")
        self.assertIn("AC", summary)

    def test_wf_close_wave_summary_skips_decision_log_separator_row(self):
        """Regression: a GFM Decision Log separator row written with 4+ dashes
        (`| ---- | -------- | ... |`, the plan-template default) must NOT be parsed
        as a decision. Previously the guard matched only the literal `---`, so a
        `----` separator cell leaked into the summary as a `--------` 'key decision'."""
        wave_md = self._make_closeable_wave(
            "1200a-sep-test",
            "1200a-feat-sep",
            completed_acs=["AC-1: Core behavior"],
            decisions=["Resolve the contradiction toward fix-canonical"],
        )
        with patch.object(self.srv, "run_garden", return_value={"passed": True, "files_updated": 0, "updated": [], "output": ""}):
            with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
                result = self.srv.wf_close_wave_response(self.root, "1200a-sep-test", mode="create")
        self.assertEqual(result["status"], "ok")
        summary = result["data"].get("wave_summary", "")
        # The real decision is present...
        self.assertIn("Resolve the contradiction toward fix-canonical", summary)
        # ...and no dashes-only separator cell leaked in as a decision.
        self.assertNotIn("Key decisions: --", summary)
        self.assertNotIn("; --", summary)

    def test_wf_close_wave_summary_requires_no_operator_input(self):
        """AC-3: Summary is generated without operator intervention."""
        wave_md = self._make_closeable_wave("1200a-auto-test", "1200a-feat-auto")
        with patch.object(self.srv, "run_garden", return_value={"passed": True, "files_updated": 0, "updated": [], "output": ""}):
            with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
                result = self.srv.wf_close_wave_response(self.root, "1200a-auto-test", mode="create")
        self.assertEqual(result["status"], "ok")
        self.assertIn("wave_summary", result["data"])
        self.assertTrue(result["data"]["wave_summary"].strip())

    def test_wf_close_wave_dry_run_includes_summary_without_writing(self):
        """AC-4: dry_run returns wave_summary in data without writing to disk."""
        wave_md = self._make_closeable_wave("1200a-dryrun-summ", "1200a-feat-dryrun-summ")
        original_text = wave_md.read_text(encoding="utf-8")
        with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
            result = self.srv.wf_close_wave_response(self.root, "1200a-dryrun-summ", mode="dry_run")
        self.assertEqual(result["status"], "dry_run")
        self.assertIn("wave_summary", result["data"])
        self.assertTrue(result["data"]["wave_summary"].strip())
        # File must not be modified
        self.assertEqual(wave_md.read_text(encoding="utf-8"), original_text)

    def test_wf_close_wave_summary_does_not_break_existing_close_behavior(self):
        """AC-5: Existing close behavior (status update, signoff) is not regressed."""
        wave_md = self._make_closeable_wave("1200a-regression-test", "1200a-feat-regression")
        with patch.object(self.srv, "run_garden", return_value={"passed": True, "files_updated": 0, "updated": [], "output": ""}):
            with patch.object(self.srv, "run_validate", return_value={"passed": True, "errors": [], "warnings": [], "output": ""}):
                result = self.srv.wf_close_wave_response(self.root, "1200a-regression-test", mode="create")
        self.assertEqual(result["status"], "ok")
        self.assertTrue(result["data"]["updated"])
        closed_text = wave_md.read_text(encoding="utf-8")
        self.assertIn("Status: closed", closed_text)
        self.assertIn("Completed At:", closed_text)


class GuruCitationContractRenderTests(unittest.TestCase):
    """Release review round 6 P1: the code_ask citation-field block must stay
    byte-identical between the canonical seed and the rendered guru surface,
    and its load-bearing claims must match the implementation — so this
    contract cannot silently diverge again.

    Cross-reference (wave 1wip2): a SECOND seed-211/guru parity oracle,
    GuruIndexScopeParityTests in test_shipped_reference_docs.py, byte-guards
    the `## Index Scope` section of the same file pair. The two oracles
    deliberately guard disjoint regions."""

    BLOCK_HEADER = "Citation fields in `code_ask` response:"

    def _block(self, path: Path) -> str:
        text = path.read_text(encoding="utf-8")
        self.assertIn(self.BLOCK_HEADER, text, path)
        start = text.index(self.BLOCK_HEADER)
        end = text.index("\n\n", start)
        return text[start:end]

    def _repo_root(self) -> Path:
        return Path(load_server().__file__).resolve().parents[3]

    def test_seed_and_rendered_blocks_are_byte_identical(self):
        repo = self._repo_root()
        seed = repo / ".wavefoundry" / "framework" / "seeds" / "211-guru.prompt.md"
        guru = repo / "docs" / "agents" / "guru.md"
        if not seed.exists() or not guru.exists():
            self.skipTest("seed/render surfaces not present")
        self.assertEqual(self._block(seed), self._block(guru),
                         "the rendered citation-field block diverged from the canonical seed")

    def test_block_claims_match_the_implementation(self):
        repo = self._repo_root()
        seed = repo / ".wavefoundry" / "framework" / "seeds" / "211-guru.prompt.md"
        if not seed.exists():
            self.skipTest("seed not present")
        block = self._block(seed)
        # Excerpt claim: full chunk text, both rerank spellings — the
        # implementation must carry no mode-conditional truncation.
        self.assertIn("full matched chunk text", block)
        self.assertNotIn("300 chars", block)
        src = Path(load_server().__file__).read_text(encoding="utf-8")
        start = src.index("def code_ask_response(")
        body = src[start:src.index("\ndef ", start + 10)]
        self.assertNotIn('full[:300]', body,
                         "the excerpt truncation the block denies must not exist")
        # Score claim: the two reranked=false cases are both stated.
        self.assertIn("vector/coverage score on the healthy path", block)
        self.assertIn("BM25 score in `lexical_fallback` mode", block)


class SignoffLatestStateTests(unittest.TestCase):
    """Release review rounds 3-4 P0: fail-closed structured signoff parsing —
    exact keys, last-state-wins, explicit positive states only, prose never
    authorizes lifecycle closure.

    Wave 1to78: the prose parser moved into review_evidence.py as the LEGACY
    branch of the review-authority facade; its semantics under test here are
    unchanged (declared waves bypass it entirely)."""

    def setUp(self):
        self.srv = load_server()
        self.review = sys.modules["review_evidence"]

    def _check(self, evidence, lane):
        return self.review.lane_has_signoff_in_evidence(evidence, lane)

    def test_full_attack_matrix(self):
        cases = [
            # explicit positive
            ("- wave-council-delivery: approved 2026-07-13 — final.\n", "wave-council-delivery", True),
            # approved then withdrawn → false
            ("- wave-council-delivery: approved.\n- wave-council-delivery: withdrawn.\n", "wave-council-delivery", False),
            # withdrawn then approved → true
            ("- wave-council-delivery: withdrawn.\n- wave-council-delivery: approved 2026-07-13.\n", "wave-council-delivery", True),
            # every negative/unknown state → false
            ("- wave-council-delivery: not approved\n", "wave-council-delivery", False),
            ("- wave-council-delivery: pending\n", "wave-council-delivery", False),
            ("- wave-council-delivery: signoff pending\n", "wave-council-delivery", False),
            ("- wave-council-delivery: blocked because previous checks passed\n", "wave-council-delivery", False),
            ("- wave-council-delivery: rejected — approved earlier though\n", "wave-council-delivery", False),
            ("- wave-council-delivery: denied\n", "wave-council-delivery", False),
            ("- wave-council-delivery: failed\n", "wave-council-delivery", False),
            ("- wave-council-delivery: withdrawn\n", "wave-council-delivery", False),
            ("- wave-council-delivery: revoked\n", "wave-council-delivery", False),
            ("- wave-council-delivery: rescinded\n", "wave-council-delivery", False),
            ("- wave-council-delivery: <approved when ready>\n", "wave-council-delivery", False),
            ("- wave-council-delivery: awaiting confirmation\n", "wave-council-delivery", False),
            # superseded-only approval → false
            ("- wave-council-delivery(superseded): approved 2026-07-12\n", "wave-council-delivery", False),
            # withdrawn current followed by superseded approval → false
            ("- wave-council-delivery: WITHDRAWN pending\n- wave-council-delivery(superseded): approved\n", "wave-council-delivery", False),
            # approved current followed by superseded withdrawal → true
            ("- wave-council-delivery: approved 2026-07-13\n- wave-council-delivery(superseded): withdrawn\n", "wave-council-delivery", True),
            # lane-prefix collisions → false
            ("- qa-reviewer: approved\n", "qa", False),
            ("- operator-signoff-notes: approved\n", "operator", False),
            ("- operator-signoff-notes: approved\n", "operator-signoff", False),
            # operator authorization: state line only; prose never authorizes
            ("- operator-signoff: approved 2026-07-13 — operator directed close.\n", "operator", True),
            ("- operator-signoff: <approved when operator confirms closure>\n", "operator", False),
            ("- the operator's review passed all gates and approved everything\n", "operator", False),
            # reviewer-seat prose compatibility preserved (spaced descriptor is not historical)
            ("- **red-team (delivery):** probes executed. Stance: approve. Signoff recorded.\n", "red-team", True),
        ]
        for ev, lane, expect in cases:
            self.assertIs(self._check(ev, lane), expect, (lane, ev.splitlines()[0]))

    def test_live_wave_records_parse_correctly(self):
        """The real records: closed 1seav/1sed7/1sc7c all parse as approved
        (1seav's final APPROVED verdict and operator closure direction were
        recorded 2026-07-13; its earlier withdrawn rounds remain visible as
        superseded lines and must not block)."""
        repo = Path(load_server().__file__).resolve().parents[3]
        for wave_dir, expect_delivery, expect_operator in (
            ("docs/waves/1seav search-freshness-degraded-retrieval", True, True),
            ("docs/waves/1sed7 sqlite-only-index-state", True, True),
            ("docs/waves/1sc7c content-scope-freshness", True, True),
        ):
            path = repo / wave_dir / "wave.md"
            if not path.exists():
                path = Path(wave_dir) / "wave.md"
            if not path.exists():
                self.skipTest(f"wave record not found: {wave_dir}")
            text = path.read_text(encoding="utf-8")
            ev = self.review.combined_review_evidence(text)
            self.assertIs(self.review.lane_has_signoff_in_evidence(ev, "wave-council-delivery"),
                          expect_delivery, wave_dir)
            self.assertIs(self.review.lane_has_signoff_in_evidence(ev, "operator"),
                          expect_operator, wave_dir)


class TypedExclusiveGateDerivationTests(unittest.TestCase):
    """Wave 1to78 AC-1(a): on a declared wave, all six gate surfaces derive
    review evidence solely from typed events.jsonl records.

    The fixture is built through canonical producers (wf_create_wave scaffold,
    wf_add_change admission, the canonical ledger serializer and both
    projection renderers) with a parseable ``- Required review lanes:`` bullet
    and ZERO operator-authored prose signoff lines, then exercised through
    wf_prepare_wave readiness, wf_review_wave(phase='prepare'),
    wf_implement_wave Gate 2, wf_review_wave(phase='implementation'), and the
    close gate.

    Old-code discrimination (executed against the pre-change tree at commit
    9ddc9b93 via a scratch worktree): the typed-only green path was RED at
    wf_review_wave(prepare) and Gate 2 (both demanded prose in `## Prepare
    Review Evidence`), the prose-only control turned Gate 2 GREEN (forgeable),
    and the planted prose severity words read back "critical". Under the
    facade the same fixtures produce the inverted, typed-exclusive outcomes
    asserted here, so every control in this class is proven able to fail.
    """

    LINT_OK = {"passed": True, "errors": [], "warnings": [], "output": ""}
    GARDEN_OK = {"passed": True, "files_updated": 0, "updated": [], "output": ""}

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.review = sys.modules["review_evidence"]
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "docs").mkdir(parents=True)
        (self.root / "docs" / "workflow-config.json").write_text(
            json.dumps({
                "lifecycle_id_policy": {"epoch_utc": "2020-02-02T02:02:00Z", "hour_offset": 0},
                "wave_review": {
                    "enabled": True,
                    "delivery_mode": "universal",
                    "phases": {
                        "prepare": {"signoff_key": "wave-council-readiness", "moderator_role": "wave-council"},
                        "review": {"signoff_key": "wave-council-delivery", "moderator_role": "wave-council"},
                    },
                },
            }),
            encoding="utf-8",
        )
        created = self.srv.wf_create_wave_response(self.root, "typed-gates", mode="create")
        self.wave_id = created["data"]["wave_id"]
        self.wave_md = self.root / "docs" / "waves" / self.wave_id / "wave.md"
        # Operator-authored configuration sections: populate the scaffolded
        # roster in place, then append the narrative council checkpoint.
        _scaffold = self.wave_md.read_text(encoding="utf-8")
        _scaffold = re.sub(
            r"(?ms)(^## Participants[ \t]*\n).*?(?=^## )",
            r"\1\n- Required review lanes: `qa-reviewer`\n\n",
            _scaffold,
            count=1,
        )
        self.wave_md.write_text(
            _scaffold + f"\n## Review Checkpoints\n\n{_prepare_council_verdict_line()}\n",
            encoding="utf-8",
        )
        # The roster edit changes the required projection key set. Keep the
        # generated projection current before exercising Prepare; otherwise
        # the preflight correctly refuses to mint a receipt from a stale
        # carrier.
        self._set_records(())
        # Admit one completed change through the canonical producer. The lane
        # selector reads only this declared section, so name a Python target to
        # recruit code-reviewer.
        (self.root / "docs" / "plans").mkdir(exist_ok=True)
        (self.root / "docs" / "plans" / "1200a-feat sample.md").write_text(
            "# Sample\n\n"
            "Change ID: `1200a-feat sample`\n"
            "Change Status: `planned`\n"
            "Last verified: 2026-07-29\n\n"
            "## Rationale\n\nWhy.\n\n"
            "## Requirements\n\n1. One.\n\n"
            "## Scope\n\nIn scope.\n\n"
            "## Acceptance Criteria\n\n- [x] AC-1: Criterion met.\n\n"
            "## Tasks\n\n- [x] Implement.\n\n"
            "## Serialization Points\n\n- .wavefoundry/framework/scripts/server_impl.py\n\n"
            "## AC Priority\n\n| AC | Priority | Rationale |\n| --- | --- | --- |\n| AC-1 | required | Core. |\n",
            encoding="utf-8",
        )
        add = self.srv.wf_add_change_response(self.root, self.wave_id, "1200a-feat sample", mode="create")
        assert add["status"] == "ok", add
        # Prepare first publishes the server-owned policy receipt/roster.  The
        # expected missing-approval result is still a successful publication
        # boundary; readiness actors can only approve that current receipt.
        seeded = self._run(
            self.srv.wf_prepare_wave_response,
            self.root,
            self.wave_id,
            mode="ready",
        )
        assert seeded["status"] == "error", seeded
        assert "missing_wave_council_signoff" in self._codes(seeded), seeded
        # Typed readiness evidence: readiness run + receipt-bound council and
        # specialist-lane approvals through the registered public producer.
        _append_review_run(self.root, self.wave_id, kind="readiness")
        for signoff_key, actor in (
            ("wave-council-readiness", "wave-council"),
            ("code-reviewer", "code-reviewer"),
        ):
            approval = self.srv.wf_review_event_response(
                self.root,
                self.wave_id,
                "approval",
                actor,
                f"typed-gates-{signoff_key}",
                mode="create",
                signoff_key=signoff_key,
                approval_phase="readiness",
                fresh_context=True,
                independent=True,
                integrity_checks=integrity_checks(),
                evidence={
                    "observed": "receipt-bound readiness approval passed",
                    "artifact_or_test_id": f"test:{signoff_key}",
                },
            )
            assert approval["status"] == "ok", approval

    # -- canonical ledger/projection helpers --------------------------------

    def _records(self):
        records, errors = self.review.read_review_event_ledger(self.wave_md)
        self.assertFalse(errors, errors)
        return records

    def _set_records(self, records):
        self.review.review_event_path(self.wave_md).write_bytes(
            self.review.canonical_review_events_bytes(records)
        )
        text = self.wave_md.read_text(encoding="utf-8")
        projected = self.review.render_review_evidence_projection(text, records)
        projected = self.review.render_review_status_projection(
            projected,
            records,
            self.review.required_review_status_keys(self.root, projected, records),
        )
        self.wave_md.write_text(projected, encoding="utf-8")

    def _append_records(self, *records):
        self._set_records((*self._records(), *records))

    def _drop_approval(self, signoff_key):
        self._set_records(tuple(
            record for record in self._records()
            if record.get("claim_id") != f"approval:{signoff_key}"
        ))

    def _add_delivery_evidence(self):
        _append_review_run(self.root, self.wave_id, kind="initial_delivery")
        for signoff_key, actor in (
            ("operator-signoff", "operator"),
            ("wave-council-delivery", "wave-council"),
            ("code-reviewer", "code-reviewer"),
        ):
            approval = self.srv.wf_review_event_response(
                self.root,
                self.wave_id,
                "approval",
                actor,
                f"typed-gates-delivery-{signoff_key}",
                mode="create",
                signoff_key=signoff_key,
                approval_phase="delivery",
                fresh_context=True,
                independent=True,
                integrity_checks=integrity_checks(),
                evidence={
                    "observed": "delivery approval passed",
                    "artifact_or_test_id": f"test:delivery-{signoff_key}",
                },
            )
            self.assertEqual(approval["status"], "ok", approval)

    def _mark_change_complete(self):
        for path in (self.wave_md, self.wave_md.parent / "1200a-feat sample.md"):
            path.write_text(
                path.read_text(encoding="utf-8").replace(
                    "Change Status: `planned`", "Change Status: `complete`"
                ),
                encoding="utf-8",
            )

    def _patched(self):
        return (
            patch.object(self.srv, "run_validate", return_value=self.LINT_OK),
            patch.object(self.srv, "run_garden", return_value=self.GARDEN_OK),
            patch.object(self.srv, "_trigger_background_index_refresh_for_paths"),
        )

    def _run(self, fn, *args, **kwargs):
        p1, p2, p3 = self._patched()
        with p1, p2, p3:
            return fn(*args, **kwargs)

    @staticmethod
    def _codes(response):
        return {d["code"] for d in response.get("diagnostics", [])}

    def _assert_no_prose_signoff_lines(self):
        for line in self.wave_md.read_text(encoding="utf-8").splitlines():
            self.assertIsNone(
                re.match(r"^-\s*[a-z][a-z-]*(-signoff)?:\s*approved", line.strip()),
                f"fixture must carry zero prose signoff lines, found: {line!r}",
            )

    def test_specialist_readiness_approval_uses_valid_phase_after_activation(self):
        """A valid specialist phase remains authoritative on an OPEN wave."""
        self.wave_md.write_text(
            self.wave_md.read_text(encoding="utf-8").replace(
                "Status: planned", "Status: implementing"
            ),
            encoding="utf-8",
        )
        approval = self.srv.wf_review_event_response(
            self.root, self.wave_id, "approval", "qa-reviewer",
            "specialist-readiness-after-activation", mode="create",
            signoff_key="qa-reviewer", approval_phase="readiness",
            fresh_context=True, independent=True,
            integrity_checks=integrity_checks(),
            evidence={
                "observed": "specialist approved the current readiness receipt",
                "artifact_or_test_id": "specialist-readiness-after-activation",
            },
        )
        self.assertEqual(approval["status"], "ok", approval)
        self.assertEqual(approval["data"]["review_actions"]["phase"], "readiness")

    # -- AC-1(a) green path --------------------------------------------------

    def test_typed_only_evidence_is_green_across_all_gate_surfaces(self):
        self._assert_no_prose_signoff_lines()

        prepare = self._run(self.srv.wf_prepare_wave_response, self.root, self.wave_id, mode="dry_run")
        self.assertEqual(prepare["status"], "dry_run", prepare)
        self.assertNotIn("missing_wave_council_signoff", self._codes(prepare))

        review_prepare = self._run(self.srv.wf_review_wave_response, self.root, self.wave_id, phase="prepare")
        self.assertEqual(review_prepare["status"], "ok", review_prepare)
        self.assertEqual(
            review_prepare["data"]["lane_results"],
            [{"lane": "code-reviewer", "recorded_signoff": True}],
        )

        gate2 = self._run(self.srv.wf_implement_wave_response, self.root, self.wave_id, mode="dry_run")
        self.assertEqual(gate2["status"], "dry_run", gate2)

        self._add_delivery_evidence()
        # AC-1 severity control: a standalone severity word in prose trips
        # nothing on a declared wave (the placeholder line is replaced by pure
        # narrative carrying severity words).
        self.wave_md.write_text(
            self.wave_md.read_text(encoding="utf-8").replace(
                "- operator-signoff: <approved when operator confirms closure>",
                "- narrative: reviewers discussed a high severity hypothetical; critical wording stays narrative",
            ),
            encoding="utf-8",
        )
        self._assert_no_prose_signoff_lines()

        review_impl = self._run(self.srv.wf_review_wave_response, self.root, self.wave_id)
        self.assertEqual(review_impl["status"], "ok", review_impl)
        self.assertEqual(review_impl["data"]["max_severity"], "none")
        self.assertNotIn("high_severity_finding", self._codes(review_impl))

        # Advancing a change to `complete` is progress, not a contract change:
        # it edits no Requirement, Scope, AC, or AC-Priority text, so it is
        # digest-neutral and the readiness roster it was granted against stays
        # current. Verification of the work itself lives behind the delivery
        # gate, which this does not touch.
        self._mark_change_complete()
        refreshed = self._run(
            self.srv.wf_prepare_wave_response,
            self.root,
            self.wave_id,
            mode="ready",
        )
        self.assertEqual(refreshed["status"], "ok", refreshed)
        self.assertNotIn("missing_wave_council_signoff", self._codes(refreshed))
        self.assertNotIn("review_policy_receipt_stale", self._codes(refreshed))
        for signoff_key, actor in (
            ("wave-council-readiness", "wave-council"),
            ("code-reviewer", "code-reviewer"),
        ):
            approval = self.srv.wf_review_event_response(
                self.root,
                self.wave_id,
                "approval",
                actor,
                f"typed-gates-final-{signoff_key}",
                mode="create",
                signoff_key=signoff_key,
                approval_phase="readiness",
                fresh_context=True,
                independent=True,
                integrity_checks=integrity_checks(),
                evidence={
                    "observed": "final change bytes approved",
                    "artifact_or_test_id": f"test:final-{signoff_key}",
                },
            )
            self.assertEqual(approval["status"], "ok", approval)
        close = self._run(self.srv.wf_close_wave_response, self.root, self.wave_id, mode="dry_run")
        self.assertEqual(close["status"], "dry_run", close)
        self.assertEqual(close.get("diagnostics", []), [])

    # -- AC-1(a) executed known-bad: one typed lane approval dropped ---------

    def test_dropping_one_typed_lane_approval_blocks_every_surface(self):
        self._add_delivery_evidence()
        self._mark_change_complete()
        self._drop_approval("code-reviewer")

        review_prepare = self._run(self.srv.wf_review_wave_response, self.root, self.wave_id, phase="prepare")
        self.assertEqual(review_prepare["status"], "error")
        self.assertIn("missing_required_lane", self._codes(review_prepare))

        gate2 = self._run(self.srv.wf_implement_wave_response, self.root, self.wave_id, mode="dry_run")
        self.assertEqual(gate2["status"], "error")
        self.assertIn("prepare_review_incomplete", self._codes(gate2))

        review_impl = self._run(self.srv.wf_review_wave_response, self.root, self.wave_id)
        self.assertEqual(review_impl["status"], "error")
        self.assertIn("missing_required_lane", self._codes(review_impl))

        close = self._run(self.srv.wf_close_wave_response, self.root, self.wave_id, mode="dry_run")
        self.assertEqual(close["status"], "error")
        self.assertIn("missing_required_lane", self._codes(close))

    # -- AC-1(a): prose-only signoff without the typed record satisfies nothing

    def test_prose_only_signoff_lines_satisfy_no_surface(self):
        self._add_delivery_evidence()
        self._mark_change_complete()
        self._drop_approval("code-reviewer")
        # Prose forgeries in BOTH prose evidence sections. The prepare-section
        # line is the decisive one: the pre-facade Gate 2 accepted it.
        self.wave_md.write_text(
            self.wave_md.read_text(encoding="utf-8")
            + "\n## Prepare Review Evidence\n\n- code-reviewer: approved\n",
            encoding="utf-8",
        )
        self.wave_md.write_text(
            self.wave_md.read_text(encoding="utf-8").replace(
                "- operator-signoff: <approved when operator confirms closure>",
                "- code-reviewer: approved\n- operator-signoff: approved",
            ),
            encoding="utf-8",
        )

        review_prepare = self._run(self.srv.wf_review_wave_response, self.root, self.wave_id, phase="prepare")
        self.assertEqual(review_prepare["status"], "error")
        self.assertIn("missing_required_lane", self._codes(review_prepare))

        gate2 = self._run(self.srv.wf_implement_wave_response, self.root, self.wave_id, mode="dry_run")
        self.assertEqual(gate2["status"], "error")
        self.assertIn("prepare_review_incomplete", self._codes(gate2))

        review_impl = self._run(self.srv.wf_review_wave_response, self.root, self.wave_id)
        self.assertEqual(review_impl["status"], "error")
        self.assertIn("missing_required_lane", self._codes(review_impl))

        close = self._run(self.srv.wf_close_wave_response, self.root, self.wave_id, mode="dry_run")
        self.assertEqual(close["status"], "error")
        self.assertIn("missing_required_lane", self._codes(close))

    # -- Wave 1to78 delivery repair (DF2): typed remediation wording ---------

    def test_declared_wave_gate_messages_instruct_typed_events(self):
        """DF2 (message-only): on a declared wave, the prepare-phase review
        surface and Gate 2 (the two blocking diagnostics with no typed
        companion diagnostic) instruct recording a typed approval via
        wf_review_event and name the signoff key, instead of telling the
        caller to write prose into `## Prepare Review Evidence` (which is
        inert on declared waves). Legacy prose fixtures keep the historical
        wording, pinned in LegacyProseGateParityTests."""
        self._drop_approval("code-reviewer")

        review_prepare = self._run(self.srv.wf_review_wave_response, self.root, self.wave_id, phase="prepare")
        self.assertEqual(review_prepare["status"], "error")
        [message] = [
            d["message"] for d in review_prepare["diagnostics"]
            if d["code"] == "missing_required_lane"
        ]
        self.assertIn("wf_review_event", message)
        self.assertIn("signoff_key", message)
        self.assertIn("code-reviewer", message)
        self.assertNotIn("`## Prepare Review Evidence` section", message)

        gate2 = self._run(self.srv.wf_implement_wave_response, self.root, self.wave_id, mode="dry_run")
        self.assertEqual(gate2["status"], "error")
        [gate2_message] = [
            d["message"] for d in gate2["diagnostics"]
            if d["code"] == "prepare_review_incomplete"
        ]
        self.assertIn("wf_review_event", gate2_message)
        self.assertIn("signoff_key", gate2_message)
        self.assertIn("code-reviewer", gate2_message)
        self.assertNotIn("missing signoffs in `## Prepare Review Evidence`", gate2_message)

    # -- AC-1(a): readiness council surface (f) ------------------------------

    def test_prose_only_readiness_council_signoff_satisfies_nothing(self):
        self._drop_approval("wave-council-readiness")
        self.wave_md.write_text(
            self.wave_md.read_text(encoding="utf-8").replace(
                "- operator-signoff: <approved when operator confirms closure>",
                "- wave-council-readiness: approved",
            ),
            encoding="utf-8",
        )
        prepare = self._run(self.srv.wf_prepare_wave_response, self.root, self.wave_id, mode="dry_run")
        self.assertEqual(prepare["status"], "error")
        self.assertIn("missing_wave_council_signoff", self._codes(prepare))

    def test_typed_readiness_approval_without_any_prose_passes_prepare_gate(self):
        text = self.wave_md.read_text(encoding="utf-8")
        text = text.split("\n## Review Checkpoints\n", 1)[0] + "\n"
        self.wave_md.write_text(text, encoding="utf-8")
        self._set_records(self._records())

        for mode, expected_status in (
            ("dry_run", "dry_run"),
            ("ready", "ok"),
            ("create", "ok"),
        ):
            prepare = self._run(
                self.srv.wf_prepare_wave_response,
                self.root,
                self.wave_id,
                mode=mode,
            )
            self.assertEqual(prepare["status"], expected_status, prepare)
            self.assertNotIn("missing_wave_council_signoff", self._codes(prepare))
            self.assertNotIn("prepare_council_verdict_missing", self._codes(prepare))

    def test_disabled_council_policy_requires_neither_council_phase(self):
        config_path = self.root / "docs" / "workflow-config.json"
        config = json.loads(config_path.read_text(encoding="utf-8"))
        config["wave_review"]["enabled"] = False
        config["wave_review"]["delivery_mode"] = "disabled"
        config_path.write_text(json.dumps(config), encoding="utf-8")
        text = self.wave_md.read_text(encoding="utf-8")
        text = text.split("\n## Review Checkpoints\n", 1)[0] + "\n"
        self.wave_md.write_text(text, encoding="utf-8")
        self._set_records(self._records())

        # The policy edit invalidates the old receipt. Re-Prepare publishes a
        # disabled receipt; the specialist lane remains non-waivable and must
        # approve the new receipt even though Council is no longer required.
        reprepared = self._run(
            self.srv.wf_prepare_wave_response,
            self.root,
            self.wave_id,
            mode="ready",
        )
        self.assertEqual(reprepared["status"], "ok", reprepared)
        lane_reapproval = self.srv.wf_review_event_response(
            self.root,
            self.wave_id,
            "approval",
            "code-reviewer",
            "typed-gates-code-disabled-receipt",
            mode="create",
            signoff_key="code-reviewer",
            approval_phase="readiness",
            fresh_context=True,
            independent=True,
            integrity_checks=integrity_checks(),
            evidence={
                "observed": "specialist lane approved the disabled-policy receipt",
                "artifact_or_test_id": "test:code-disabled-receipt",
            },
        )
        self.assertEqual(lane_reapproval["status"], "ok", lane_reapproval)

        self._drop_approval("wave-council-readiness")
        disabled_prepare = self._run(
            self.srv.wf_prepare_wave_response,
            self.root,
            self.wave_id,
            mode="dry_run",
        )
        self.assertEqual(disabled_prepare["status"], "dry_run", disabled_prepare)
        self.assertNotIn("missing_wave_council_signoff", self._codes(disabled_prepare))
        disabled_implement = self._run(
            self.srv.wf_implement_wave_response,
            self.root,
            self.wave_id,
            mode="dry_run",
        )
        self.assertEqual(disabled_implement["status"], "dry_run", disabled_implement)
        self.assertNotIn("missing_wave_council_signoff", self._codes(disabled_implement))

    # -- 1tsyx AC-1: activation reads typed readiness authority ------------

    def test_implement_rejects_declared_wave_with_only_prose_verdict(self):
        """A well-formed prose verdict cannot forge activation readiness."""
        self._drop_approval("wave-council-readiness")
        before = self.wave_md.read_bytes()
        result = self._run(
            self.srv.wf_implement_wave_response,
            self.root,
            self.wave_id,
            mode="create",
        )
        self.assertEqual(result["status"], "error", result)
        self.assertIn("missing_wave_council_signoff", self._codes(result))
        self.assertEqual(self.wave_md.read_bytes(), before, "rejection must not mutate the wave")

    def test_implement_accepts_declared_typed_readiness_without_prose_verdict(self):
        """Typed readiness is sufficient even when Review Checkpoints has no verdict."""
        text = self.wave_md.read_text(encoding="utf-8")
        text = text.split("\n## Review Checkpoints\n", 1)[0] + "\n"
        self.wave_md.write_text(text, encoding="utf-8")
        self._set_records(self._records())
        result = self._run(
            self.srv.wf_implement_wave_response,
            self.root,
            self.wave_id,
            mode="dry_run",
        )
        self.assertEqual(result["status"], "dry_run", result)
        self.assertNotIn("prepare_council_verdict_missing", self._codes(result))

    # -- AC-2: Prepare-owned roster tampering is stale and blocking ----------

    def test_declared_roster_tamper_blocks_review_and_close(self):
        text = self.wave_md.read_text(encoding="utf-8").replace(
            "- Required review lanes: code-reviewer",
            "- Required review lanes: none",
        )
        self.wave_md.write_text(text, encoding="utf-8")
        self._set_records(self._records())
        self._add_delivery_evidence()
        self._mark_change_complete()

        review = self._run(self.srv.wf_review_wave_response, self.root, self.wave_id)
        self.assertEqual(review["status"], "error", review)
        self.assertIn("review_policy_receipt_stale", self._codes(review))
        actions = review["data"]["review_actions"]
        self.assertFalse(actions["available"], actions)
        self.assertEqual(actions["reason"], "review_policy_receipt_stale")
        self.assertEqual(actions["next_actions"], [])

        close = self._run(
            self.srv.wf_close_wave_response,
            self.root,
            self.wave_id,
            mode="dry_run",
        )
        self.assertEqual(close["status"], "error", close)
        self.assertIn("review_policy_receipt_stale", self._codes(close))

    def test_advancing_change_status_is_progress_not_a_contract_change(self):
        """Status advancement is digest-neutral; editing the contract is not.

        This pins the rule directly rather than leaving it implied by other
        tests. It replaces the previous rule, under which advancing a change
        superseded the receipt and lapsed the readiness roster. That rule was
        ceremony: the re-recorded approvals attested to a plan whose reviewed
        text had not changed by a single byte.

        The negative control is the load-bearing half. Without it this test
        would pass just as well against a normalizer that swallowed every
        change-document edit.
        """
        import review_policy

        change = self.wave_md.parent / "1200a-feat sample.md"
        before = review_policy.canonical_review_policy_body(
            change.read_bytes()
        )

        self._mark_change_complete()
        after_status = review_policy.canonical_review_policy_body(
            change.read_bytes()
        )
        self.assertEqual(
            before,
            after_status,
            "advancing Change Status must not move the review-policy digest",
        )

        # Negative control: a requirement-bearing edit in the same document
        # must still move the digest and therefore still lapse approvals.
        change.write_text(
            change.read_text(encoding="utf-8").replace(
                "## Scope", "## Scope\n\nNewly added scope sentence.", 1
            ),
            encoding="utf-8",
        )
        after_scope = review_policy.canonical_review_policy_body(
            change.read_bytes()
        )
        self.assertNotEqual(
            after_status,
            after_scope,
            "a Scope edit must still be review-relevant",
        )

    def test_gardener_only_date_rollover_keeps_all_lifecycle_surfaces_current(self):
        """A midnight gardener stamp cannot invalidate the prepared receipt."""

        # Setup, and itself an assertion of the progress-only rule: advancing
        # the change supersedes no receipt, so the roster below is a no-op
        # refresh rather than a forced re-approval.
        self._mark_change_complete()
        refreshed = self._run(
            self.srv.wf_prepare_wave_response,
            self.root,
            self.wave_id,
            mode="ready",
        )
        self.assertEqual(refreshed["status"], "ok", refreshed)
        self.assertNotIn("review_policy_receipt_stale", self._codes(refreshed))
        for signoff_key, actor in (
            ("wave-council-readiness", "wave-council"),
            ("code-reviewer", "code-reviewer"),
        ):
            approved = self.srv.wf_review_event_response(
                self.root,
                self.wave_id,
                "approval",
                actor,
                f"midnight-{signoff_key}",
                mode="create",
                signoff_key=signoff_key,
                approval_phase="readiness",
                fresh_context=True,
                independent=True,
                integrity_checks=integrity_checks(),
                evidence={
                    "observed": "approved the completed pre-midnight change",
                    "artifact_or_test_id": f"test:midnight-{signoff_key}",
                },
            )
            self.assertEqual(approved["status"], "ok", approved)
        self._add_delivery_evidence()

        change = self.wave_md.parent / "1200a-feat sample.md"
        change.write_text(
            change.read_text(encoding="utf-8").replace(
                "Last verified: 2026-07-29", "Last verified: 2026-07-30"
            ),
            encoding="utf-8",
        )

        surfaces = (
            self._run(
                self.srv.wf_prepare_wave_response,
                self.root,
                self.wave_id,
                mode="dry_run",
            ),
            self._run(
                self.srv.wf_review_wave_response,
                self.root,
                self.wave_id,
                phase="prepare",
            ),
            self._run(
                self.srv.wf_implement_wave_response,
                self.root,
                self.wave_id,
                mode="dry_run",
            ),
            self._run(
                self.srv.wf_close_wave_response,
                self.root,
                self.wave_id,
                mode="dry_run",
            ),
        )
        for response in surfaces:
            self.assertNotIn("review_policy_receipt_stale", self._codes(response), response)
        self.assertEqual(surfaces[-1]["status"], "dry_run", surfaces[-1])

    def test_progress_log_repair_note_keeps_the_readiness_roster_current(self):
        """AC-4: logging a mandated repair supersedes nothing and lapses nothing.

        Readiness-phase specifically: `policy_receipt_id` is legal only on a
        readiness approval, so a delivery-lane version of this test passes on the
        unmodified tree and proves nothing.
        """

        def receipts():
            return tuple(
                record
                for record in self._records()
                if record.get("record_type") == "review_policy_receipt"
            )

        change = self.wave_md.parent / "1200a-feat sample.md"
        # Give the admitted change the mandated repair-tracking section, then
        # re-earn readiness against those bytes: adding a whole section IS a
        # substantive edit and must still supersede.
        change.write_text(
            change.read_text(encoding="utf-8")
            + "\n## Progress Log\n\n"
            "| Date | Update | Evidence |\n| ---- | ------ | -------- |\n"
            "| 2026-08-05 | Implemented the change. | test:impl |\n",
            encoding="utf-8",
        )
        superseded = self._run(
            self.srv.wf_prepare_wave_response, self.root, self.wave_id, mode="ready"
        )
        self.assertEqual(superseded["status"], "error", superseded)
        self.assertIn("missing_wave_council_signoff", self._codes(superseded))
        for signoff_key, actor in (
            ("wave-council-readiness", "wave-council"),
            ("code-reviewer", "code-reviewer"),
        ):
            approved = self.srv.wf_review_event_response(
                self.root,
                self.wave_id,
                "approval",
                actor,
                f"repair-note-{signoff_key}",
                mode="create",
                signoff_key=signoff_key,
                approval_phase="readiness",
                fresh_context=True,
                independent=True,
                integrity_checks=integrity_checks(),
                evidence={
                    "observed": "approved the change carrying its Progress Log",
                    "artifact_or_test_id": f"test:repair-note-{signoff_key}",
                },
            )
            self.assertEqual(approved["status"], "ok", approved)
        settled = len(receipts())

        # The act AGENTS.md mandates of every repairer: one appended row.
        change.write_text(
            change.read_text(encoding="utf-8")
            + "| 2026-08-05 | Repaired a drifted line citation in place. | test:repair |\n",
            encoding="utf-8",
        )
        prepared = self._run(
            self.srv.wf_prepare_wave_response, self.root, self.wave_id, mode="ready"
        )
        self.assertEqual(
            len(receipts()),
            settled,
            "a Progress-Log-only append must mint no new receipt",
        )
        self.assertNotIn("review_policy_receipt_stale", self._codes(prepared))
        self.assertNotIn("missing_wave_council_signoff", self._codes(prepared))

        review_prepare = self._run(
            self.srv.wf_review_wave_response, self.root, self.wave_id, phase="prepare"
        )
        self.assertEqual(review_prepare["status"], "ok", review_prepare)
        self.assertNotIn("review_policy_receipt_stale", self._codes(review_prepare))
        self.assertEqual(
            review_prepare["data"]["lane_results"],
            [{"lane": "code-reviewer", "recorded_signoff": True}],
        )

    def test_public_prepare_converged_once_from_evaluator_v1_to_v2(self):
        """The retired v1-to-v2 boundary, still pinned after the v3 bump."""

        review_policy = sys.modules["review_policy"]

        def receipts():
            return tuple(
                record
                for record in self._records()
                if record.get("record_type") == "review_policy_receipt"
            )

        initial_count = len(receipts())
        with patch.object(
            review_policy, "REVIEW_POLICY_EVALUATOR_VERSION", 1
        ), patch.object(
            self.srv.lifecycle_gate_support, "REVIEW_POLICY_EVALUATOR_VERSION", 1
        ):
            legacy = self._run(
                self.srv.wf_prepare_wave_response,
                self.root,
                self.wave_id,
                mode="ready",
            )
        self.assertEqual(legacy["status"], "error", legacy)
        self.assertEqual(len(receipts()), initial_count + 1)
        self.assertEqual(receipts()[-1]["evaluator_version"], 1)

        with patch.object(
            review_policy, "REVIEW_POLICY_EVALUATOR_VERSION", 2
        ), patch.object(
            self.srv.lifecycle_gate_support, "REVIEW_POLICY_EVALUATOR_VERSION", 2
        ):
            upgraded = self._run(
                self.srv.wf_prepare_wave_response,
                self.root,
                self.wave_id,
                mode="ready",
            )
            self.assertEqual(upgraded["status"], "error", upgraded)
            self.assertEqual(len(receipts()), initial_count + 2)
            self.assertEqual(receipts()[-1]["evaluator_version"], 2)

            repeated = self._run(
                self.srv.wf_prepare_wave_response,
                self.root,
                self.wave_id,
                mode="ready",
            )
            self.assertEqual(repeated["status"], "error", repeated)
            self.assertEqual(
                len(receipts()),
                initial_count + 2,
                "a current evaluator-v2 receipt must make repeated Prepare idempotent",
            )

    def test_public_prepare_converges_once_from_evaluator_v5_to_v6(self):
        """Wave 1uo1x: the live boundary, proven to converge exactly once.

        v6 moves lane semantics (per-document adoption, two-tier declaration)
        and the digest carrier boundary together, so a non-closed wave holding
        a v5 receipt needs one deterministic re-Prepare and is idempotent after
        it. The v4-to-v5 case below is RETAINED as a retired boundary rather
        than replaced, matching how v1-to-v2 was kept.
        """

        review_policy = sys.modules["review_policy"]

        def receipts():
            return tuple(
                record
                for record in self._records()
                if record.get("record_type") == "review_policy_receipt"
            )

        initial_count = len(receipts())
        with patch.object(
            review_policy, "REVIEW_POLICY_EVALUATOR_VERSION", 5
        ), patch.object(
            self.srv.lifecycle_gate_support, "REVIEW_POLICY_EVALUATOR_VERSION", 5
        ):
            legacy = self._run(
                self.srv.wf_prepare_wave_response,
                self.root,
                self.wave_id,
                mode="ready",
            )
        self.assertEqual(legacy["status"], "error", legacy)
        self.assertEqual(len(receipts()), initial_count + 1)
        self.assertEqual(receipts()[-1]["evaluator_version"], 5)

        upgraded = self._run(
            self.srv.wf_prepare_wave_response,
            self.root,
            self.wave_id,
            mode="ready",
        )
        self.assertEqual(upgraded["status"], "error", upgraded)
        self.assertEqual(len(receipts()), initial_count + 2)
        self.assertEqual(
            receipts()[-1]["evaluator_version"],
            review_policy.REVIEW_POLICY_EVALUATOR_VERSION,
            "convergence is about old -> current -> stable, not about which\n"
            "number is current; the conscious pin on the number itself lives\n"
            "in test_review_policy's transition-boundary tripwire, so this\n"
            "assertion tracks the constant and needs no edit per bump",
        )

        repeated = self._run(
            self.srv.wf_prepare_wave_response,
            self.root,
            self.wave_id,
            mode="ready",
        )
        self.assertEqual(repeated["status"], "error", repeated)
        self.assertEqual(
            len(receipts()),
            initial_count + 2,
            "a current evaluator-v6 receipt must make repeated Prepare "
            "idempotent",
        )

    def test_public_prepare_converged_once_from_evaluator_v4_to_v5(self):
        """Wave 1umst: a RETIRED boundary, still pinned after the v6 bump.

        Both prepares run pinned, exactly as the retired v1-to-v2 case above
        does. Leaving the second unpinned would silently retarget this test at
        whatever the live version happens to be, so it would stop proving the
        v4-to-v5 transition the moment the constant moved again.
        """

        review_policy = sys.modules["review_policy"]

        def receipts():
            return tuple(
                record
                for record in self._records()
                if record.get("record_type") == "review_policy_receipt"
            )

        initial_count = len(receipts())
        with patch.object(
            review_policy, "REVIEW_POLICY_EVALUATOR_VERSION", 4
        ), patch.object(
            self.srv.lifecycle_gate_support, "REVIEW_POLICY_EVALUATOR_VERSION", 4
        ):
            legacy = self._run(
                self.srv.wf_prepare_wave_response,
                self.root,
                self.wave_id,
                mode="ready",
            )
        self.assertEqual(legacy["status"], "error", legacy)
        self.assertEqual(len(receipts()), initial_count + 1)
        self.assertEqual(receipts()[-1]["evaluator_version"], 4)

        with patch.object(
            review_policy, "REVIEW_POLICY_EVALUATOR_VERSION", 5
        ), patch.object(
            self.srv.lifecycle_gate_support, "REVIEW_POLICY_EVALUATOR_VERSION", 5
        ):
            upgraded = self._run(
                self.srv.wf_prepare_wave_response,
                self.root,
                self.wave_id,
                mode="ready",
            )
            self.assertEqual(upgraded["status"], "error", upgraded)
            self.assertEqual(len(receipts()), initial_count + 2)
            self.assertEqual(receipts()[-1]["evaluator_version"], 5)

            repeated = self._run(
                self.srv.wf_prepare_wave_response,
                self.root,
                self.wave_id,
                mode="ready",
            )
            self.assertEqual(repeated["status"], "error", repeated)
            self.assertEqual(
                len(receipts()),
                initial_count + 2,
                "a current evaluator-v5 receipt must make repeated Prepare "
                "idempotent",
            )

    def test_failed_docs_gate_publishes_no_new_roster_receipt_or_projection(self):
        config_path = self.root / "docs/workflow-config.json"
        config = json.loads(config_path.read_text(encoding="utf-8"))
        config["wave_review"]["delivery_mode"] = "targeted"
        config_path.write_text(json.dumps(config), encoding="utf-8")
        wave_before = self.wave_md.read_bytes()
        ledger_before = self.review.review_event_path(self.wave_md).read_bytes()
        with patch.object(self.srv, "run_garden", return_value=self.GARDEN_OK), \
             patch.object(self.srv, "run_validate", return_value={"passed": False, "errors": ["injected lint failure"], "warnings": [], "output": ""}), \
             patch.object(self.srv, "_trigger_background_index_refresh_for_paths"):
            result = self.srv.wf_prepare_wave_response(
                self.root, self.wave_id, mode="ready"
            )
        self.assertEqual(result["status"], "error", result)
        self.assertIn("docs_lint_error", self._codes(result))
        self.assertEqual(self.wave_md.read_bytes(), wave_before)
        self.assertEqual(
            self.review.review_event_path(self.wave_md).read_bytes(), ledger_before
        )

    def test_targeted_prepare_receipt_binds_admitted_trust_boundary_trigger(self):
        config_path = self.root / "docs/workflow-config.json"
        config = json.loads(config_path.read_text(encoding="utf-8"))
        config["wave_review"]["delivery_mode"] = "targeted"
        config_path.write_text(json.dumps(config), encoding="utf-8")
        change = self.wave_md.parent / "1200a-feat sample.md"
        change.write_text(
            change.read_text(encoding="utf-8")
            + "\n## Boundary declaration\n\nThis changes a trust boundary.\n",
            encoding="utf-8",
        )
        result = self._run(
            self.srv.wf_prepare_wave_response,
            self.root,
            self.wave_id,
            mode="ready",
        )
        self.assertEqual(result["status"], "error", result)
        records = self._records()
        receipt = __import__("review_policy").current_policy_receipt(records)
        self.assertIsNotNone(receipt)
        self.assertTrue(receipt["delivery_council_required"])
        self.assertIn(
            "wave-council-delivery",
            self.srv.lifecycle_gate_support._required_wave_council_signoffs(
                self.root,
                "review",
                wave_text=self.wave_md.read_text(encoding="utf-8"),
                wave_md=self.wave_md,
            ),
        )

    def test_malformed_canonical_receipt_returns_diagnostic_instead_of_crashing(self):
        self.review.review_event_path(self.wave_md).write_bytes(
            self.review.canonical_review_events_bytes(
                (*self._records(), {"record_type": "review_policy_receipt"})
            )
        )
        result = self._run(
            self.srv.wf_prepare_wave_response,
            self.root,
            self.wave_id,
            mode="dry_run",
        )
        self.assertEqual(result["status"], "error", result)
        self.assertIn("review_policy_receipt_stale", self._codes(result))


    def test_operator_attribution_keeps_prepared_policy_receipt_current(self):
        import review_policy
        before = review_policy.current_policy_receipt(self._records())
        self.assertIsNotNone(before)
        (self.root / "docs/contributors.json").write_text(json.dumps({
            "alice": {"name": "Alice", "emails": ["alice@example.test"]},
        }), encoding="utf-8")
        result = self.srv.wf_review_event_response(
            self.root, self.wave_id, "approval", "code-reviewer", "identity-readiness",
            mode="create", signoff_key="code-reviewer", approval_phase="readiness",
            fresh_context=True, independent=True, operator_handle="alice",
            integrity_checks=integrity_checks(),
            evidence={"observed": "identity fixture", "artifact_or_test_id": "test:identity"},
        )
        self.assertEqual(result["status"], "ok", result)
        self.assertEqual(result["data"]["appended_records"][0]["verification_context"]["operator"],
                         {"handle": "alice", "source": "explicit"})
        self.assertEqual(review_policy.current_policy_receipt(self._records()), before)
        prepared = self._run(self.srv.wf_prepare_wave_response,
                             self.root, self.wave_id, mode="ready")
        self.assertEqual(prepared["status"], "ok", prepared)
        self.assertEqual(review_policy.current_policy_receipt(self._records()), before)


class LegacyProseGateParityTests(unittest.TestCase):
    """Wave 1to78 AC-1(b): the legacy-wave golden fixture — on an undeclared
    wave the facade's prose branch preserves the pre-facade behavior in BOTH
    directions (prose present satisfies; prose absent blocks). The fixture
    matches the long-standing raw-write legacy wave shape used across this
    module; no events.jsonl exists."""

    LINT_OK = {"passed": True, "errors": [], "warnings": [], "output": ""}
    GARDEN_OK = {"passed": True, "files_updated": 0, "updated": [], "output": ""}

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = _make_repo(Path(self.tmp.name))

    def _write_wave(self, *, evidence_lines, prepare_lines=(), checkpoint_lines=()):
        wave_dir = self.root / "docs" / "waves" / "1200a legacy-wave"
        wave_dir.mkdir(parents=True, exist_ok=True)
        prepare_section = (
            "## Prepare Review Evidence\n\n" + "\n".join(prepare_lines) + "\n\n"
            if prepare_lines else ""
        )
        checkpoint_section = (
            "## Review Checkpoints\n\n" + "\n".join(checkpoint_lines) + "\n\n"
            if checkpoint_lines else ""
        )
        (wave_dir / "wave.md").write_text(
            "# Wave Record\n"
            "wave-id: `1200a legacy-wave`\n"
            "Status: active\n\n"
            "## Changes\n\n"
            "Change ID: `1200a-feat sample`\n"
            "Change Status: `complete`\n\n"
            "## Participants\n\n"
            "| Role | Lane | Owns |\n"
            "|------|------|------|\n"
            "| code-reviewer | review | x |\n\n"
            + prepare_section +
            checkpoint_section +
            "## Review Evidence\n\n"
            + "\n".join(evidence_lines) + "\n",
            encoding="utf-8",
        )
        (wave_dir / "1200a-feat sample.md").write_text(
            "# Sample\n\nChange ID: `1200a-feat sample`\nChange Status: `complete`\n\n"
            "## Rationale\n\nx\n\n## Requirements\n\n1. x\n\n## Scope\n\nx\n\n"
            "## Acceptance Criteria\n\n- [x] x\n\n## Tasks\n\n- [x] x\n\n"
            "## AC Priority\n\n| AC | Priority | Rationale |\n| --- | --- | --- |\n"
            "| AC-1 | required | x |\n",
            encoding="utf-8",
        )
        return wave_dir / "wave.md"

    def _run(self, fn, *args, **kwargs):
        with patch.object(self.srv, "run_validate", return_value=self.LINT_OK), \
             patch.object(self.srv, "run_garden", return_value=self.GARDEN_OK), \
             patch.object(self.srv, "_trigger_background_index_refresh_for_paths"):
            return fn(*args, **kwargs)

    @staticmethod
    def _codes(response):
        return {d["code"] for d in response.get("diagnostics", [])}

    def test_prose_present_satisfies_legacy_gates(self):
        self._write_wave(
            evidence_lines=[
                "- operator-signoff: approved",
                "- code-reviewer: approved",
            ],
            prepare_lines=["- code-reviewer: approved"],
        )
        review_impl = self._run(self.srv.wf_review_wave_response, self.root, "1200a legacy-wave")
        self.assertEqual(review_impl["status"], "ok", review_impl)
        review_prepare = self._run(self.srv.wf_review_wave_response, self.root, "1200a legacy-wave", phase="prepare")
        self.assertEqual(review_prepare["status"], "ok", review_prepare)
        close = self._run(self.srv.wf_close_wave_response, self.root, "1200a legacy-wave", mode="dry_run")
        self.assertEqual(close["status"], "dry_run", close)
        self.assertEqual(self._codes(close), set())

    def test_advisory_lint_warning_never_blocks_review_or_close(self):
        """Wave 1wuju (1wujs AC-1; delivery review CODE-DEL-1 / ARCH-DEL-1): on an
        otherwise closable wave whose only lint output is one advisory line, review is
        `ok` and the close dry-run is `dry_run`, each carrying exactly one
        `docs_lint_warning` diagnostic flagged advisory and nothing else. The close
        predicate keyed on list non-emptiness and returned `error` here."""
        self._write_wave(
            evidence_lines=[
                "- operator-signoff: approved",
                "- code-reviewer: approved",
            ],
            prepare_lines=["- code-reviewer: approved"],
        )
        advisory = {"passed": True, "errors": [],
                    "warnings": ["WARNING: docs/waves/1200a legacy-wave/1200a-feat sample.md: AC-1 asserts "
                                 "repository-wide state ('full test suite') [advisory sensor "
                                 "`ac_asserts_repository_state`, introduced in wave `1wur7`]"],
                    "output": ""}
        with patch.object(self.srv, "run_validate", return_value=advisory), \
             patch.object(self.srv, "run_garden", return_value=self.GARDEN_OK), \
             patch.object(self.srv, "_trigger_background_index_refresh_for_paths"):
            review = self.srv.wf_review_wave_response(self.root, "1200a legacy-wave")
            close = self.srv.wf_close_wave_response(self.root, "1200a legacy-wave", mode="dry_run")
        for gate, response, status in (("review", review, "ok"), ("close", close, "dry_run")):
            with self.subTest(gate=gate):
                self.assertEqual(response["status"], status, response)
                diagnostics = response.get("diagnostics") or []
                self.assertEqual(["docs_lint_warning"], [d["code"] for d in diagnostics], diagnostics)
                self.assertIs(True, diagnostics[0].get("advisory"), diagnostics[0])
                self.assertIn("asserts repository-wide state", diagnostics[0]["message"])

    def test_a_lint_crash_without_a_verdict_blocks_every_gate(self):
        """Wave 1wuju (delivery review QA-DEL-2): a docs_lint subprocess that exits
        non-zero without an ERROR line (a misspelled registry polarity, any crash)
        reaches prepare, review, close, and wf_validate_docs as `error` with a
        `docs_lint_error` naming the cause. The gate result is derived from the REAL
        run_validate parser over the crashed subprocess shape, so the pin fails when
        the parser stops synthesizing the entry."""
        self._write_wave(
            evidence_lines=[
                "- operator-signoff: approved",
                "- code-reviewer: approved",
            ],
            prepare_lines=["- code-reviewer: approved"],
        )
        crashed = MagicMock(returncode=1, stdout="", stderr=(
            "Traceback (most recent call last):\n"
            "ValueError: sensor `ac_asserts_repository_state` is registered with unknown "
            "polarity 'advisry'; expected one of ('advisory', 'blocking')\n"))
        with patch.object(self.srv, "_mcp_subprocess_run", return_value=crashed):
            parsed = self.srv.run_validate(self.root)
        self.assertFalse(parsed["passed"], parsed)
        with patch.object(self.srv, "run_validate", return_value=parsed), \
             patch.object(self.srv, "run_garden", return_value=self.GARDEN_OK), \
             patch.object(self.srv, "_trigger_background_index_refresh_for_paths"):
            responses = {
                "validate_docs": self.srv.wf_validate_docs_response(self.root),
                "prepare": self.srv.wf_prepare_wave_response(self.root, "1200a legacy-wave", "dry_run"),
                "review": self.srv.wf_review_wave_response(self.root, "1200a legacy-wave"),
                "review_prepare": self.srv.wf_review_wave_response(self.root, "1200a legacy-wave", phase="prepare"),
                "close": self.srv.wf_close_wave_response(self.root, "1200a legacy-wave", mode="dry_run"),
            }
        for gate, response in responses.items():
            with self.subTest(gate=gate):
                self.assertEqual("error", response["status"], (gate, response))
                errors = [d for d in response.get("diagnostics") or [] if d["code"] == "docs_lint_error"]
                self.assertEqual(1, len(errors), (gate, response.get("diagnostics")))
                self.assertIn("without a lint verdict", errors[0]["message"])
                self.assertIn("'advisry'", errors[0]["message"])

    def test_legacy_prepare_and_activation_keep_the_prose_verdict_gate(self):
        self._write_wave(
            evidence_lines=["- operator-signoff: approved", "- code-reviewer: approved"],
            prepare_lines=["- code-reviewer: approved"],
            checkpoint_lines=[_prepare_council_verdict_line()],
        )
        prepare = self._run(
            self.srv.wf_prepare_wave_response, self.root, "1200a legacy-wave", mode="create"
        )
        self.assertEqual(prepare["status"], "ok", prepare)
        implement = self._run(
            self.srv.wf_implement_wave_response, self.root, "1200a legacy-wave", mode="dry_run"
        )
        self.assertEqual(implement["status"], "dry_run", implement)

        self._write_wave(
            evidence_lines=["- operator-signoff: approved", "- code-reviewer: approved"],
            prepare_lines=["- code-reviewer: approved"],
        )
        prepare_missing = self._run(
            self.srv.wf_prepare_wave_response, self.root, "1200a legacy-wave", mode="create"
        )
        self.assertEqual(prepare_missing["status"], "ready_for_council_review", prepare_missing)
        implement_missing = self._run(
            self.srv.wf_implement_wave_response, self.root, "1200a legacy-wave", mode="dry_run"
        )
        self.assertEqual(implement_missing["status"], "error", implement_missing)
        self.assertIn("prepare_council_verdict_missing", self._codes(implement_missing))

    def test_legacy_malformed_verdict_blocks_prepare_and_activation(self):
        """1tsyx AC-1: both legacy surfaces retain the invalid-verdict branch."""
        malformed = _prepare_council_verdict_line().replace(
            "primer-depth: standard; ", ""
        )
        self._write_wave(
            evidence_lines=["- operator-signoff: approved", "- code-reviewer: approved"],
            prepare_lines=["- code-reviewer: approved"],
            checkpoint_lines=[malformed],
        )

        prepare = self._run(
            self.srv.wf_prepare_wave_response,
            self.root,
            "1200a legacy-wave",
            mode="create",
        )
        self.assertEqual(prepare["status"], "error", prepare)
        self.assertIn("prepare_council_verdict_invalid", self._codes(prepare))

        implement = self._run(
            self.srv.wf_implement_wave_response,
            self.root,
            "1200a legacy-wave",
            mode="dry_run",
        )
        self.assertEqual(implement["status"], "error", implement)
        self.assertIn("prepare_council_verdict_invalid", self._codes(implement))

    def test_prose_absent_blocks_legacy_gates(self):
        self._write_wave(evidence_lines=["- note: review still pending"])
        review_impl = self._run(self.srv.wf_review_wave_response, self.root, "1200a legacy-wave")
        self.assertEqual(review_impl["status"], "error")
        self.assertIn("missing_operator_signoff", self._codes(review_impl))
        self.assertIn("missing_required_lane", self._codes(review_impl))
        review_prepare = self._run(self.srv.wf_review_wave_response, self.root, "1200a legacy-wave", phase="prepare")
        self.assertEqual(review_prepare["status"], "error")
        self.assertIn("missing_required_lane", self._codes(review_prepare))
        close = self._run(self.srv.wf_close_wave_response, self.root, "1200a legacy-wave", mode="dry_run")
        self.assertEqual(close["status"], "error")
        codes = self._codes(close)
        self.assertIn("missing_operator_signoff", codes)
        self.assertIn("missing_required_lane", codes)

    def test_prose_absent_legacy_messages_keep_prose_wording(self):
        """Wave 1to78 delivery repair (DF2): legacy (undeclared) waves keep
        the EXACT historical prose remediation wording; the typed
        wf_review_event instruction appears only on declared waves."""
        self._write_wave(evidence_lines=["- note: review still pending"])

        review_prepare = self._run(self.srv.wf_review_wave_response, self.root, "1200a legacy-wave", phase="prepare")
        [prepare_message] = [
            d["message"] for d in review_prepare["diagnostics"]
            if d["code"] == "missing_required_lane"
        ]
        self.assertIn(
            "Record each lane signoff in the `## Prepare Review Evidence` section of wave.md before running wf_implement_wave.",
            prepare_message,
        )
        self.assertNotIn("wf_review_event", prepare_message)

        gate2 = self._run(self.srv.wf_implement_wave_response, self.root, "1200a legacy-wave", mode="dry_run")
        [gate2_message] = [
            d["message"] for d in gate2["diagnostics"]
            if d["code"] == "prepare_review_incomplete"
        ]
        self.assertIn("missing signoffs in `## Prepare Review Evidence`", gate2_message)
        self.assertNotIn("wf_review_event", gate2_message)

        close = self._run(self.srv.wf_close_wave_response, self.root, "1200a legacy-wave", mode="dry_run")
        [operator_message] = [
            d["message"] for d in close["diagnostics"]
            if d["code"] == "missing_operator_signoff"
        ]
        self.assertIn(
            "Add `operator-signoff: approved` to `## Review Evidence` in wave.md.",
            operator_message,
        )
        self.assertNotIn("wf_review_event", operator_message)

    def test_legacy_prose_severity_word_still_registers(self):
        self._write_wave(
            evidence_lines=[
                "- operator-signoff: approved",
                "- code-reviewer: approved — one high severity finding repaired",
            ],
        )
        review_impl = self._run(self.srv.wf_review_wave_response, self.root, "1200a legacy-wave")
        self.assertEqual(review_impl["data"]["max_severity"], "high")


class DeclaredWaveTreeSweepTests(unittest.TestCase):
    """Wave 1to78 AC-1(c): tree sweep over every CLOSED wave in this
    repository whose parsed header (canonical declaration parser, never grep)
    declares events.jsonl.

    The sweep proves TOPOLOGY PRESERVATION AND LEGACY PARITY, not lane
    derivation: most declared waves parse to empty lane rosters, so the
    committed snapshot pins each wave's derived required-lane topology and
    whether the typed review-evidence gate derivation is green.

    Two pre-chronology archives (1stwm, 1sufq) derive `withheld` operator/
    delivery states under today's chronology rules; this predates the facade
    (the same derivation already blocked them via
    _approval_evidence_diagnostics before this change, verified against
    commit 9ddc9b93) and closed archives are never rewritten, so the snapshot
    records them honestly as non-green. Open/non-closed waves are excluded:
    their ledgers are still moving.
    """

    # wave dir name -> (sorted required lane roster, typed gate derivation green)
    TOPOLOGY_SNAPSHOT = {
        "1seax lifecycle-ops-hardening": ((), True),
        "1skt1 executable-review-evidence": (
            ("architecture-reviewer", "code-reviewer", "docs-contract-reviewer",
             "qa-reviewer", "security-reviewer"), True),
        "1slep external-wave-event-ledger": ((), True),
        "1snq3 credible-threat-gate": ((), True),
        "1so5p specialist-carrier-frontmatter": ((), True),
        "1sq4a review-verification-generalization": ((), True),
        "1sq9i freshness-false-stale-fix": ((), True),
        "1stwj context-efficiency-telemetry": ((), True),
        "1stwm memory-supply": ((), False),
        "1sufo memory-retrieval-eval-and-fusion": ((), True),
        "1sufq commit-reasoning-provenance": ((), False),
        "1sxj7 self-populating-memory-and-telemetry-reconciliation": ((), True),
        "1t1uo dashboard-multiline-ac-tasks": ((), True),
        "1t3dm memory-backfill-and-review-evidence-clarity": (
            ("architecture-reviewer", "code-reviewer", "docs-contract-reviewer",
             "performance-reviewer", "qa-reviewer", "reality-checker",
             "release-reviewer", "security-reviewer"), True),
        "1t3ek context-efficiency-feedback-loop": ((), True),
        "1t3gt mcp-tool-hygiene": ((), True),
        "1t550 upgrade-field-fixes": ((), True),
        "1t59p wf-audit-bounded-index-health": ((), True),
        "1t69a retrieval-posture-coverage": ((), True),
        "1t72b ce-hardening-and-paired-eval": ((), True),
        "1t87f relocated-journal-naming": ((), True),
        "1t8la memory-archival-and-retention": ((), True),
        "1t9ti memory-publication-receipt": ((), True),
        "1t9tk changelog-first-packaging": ((), True),
        "1t9w8 memory-lifecycle-naming": ((), True),
        "1t9wa retire-wave-journals": ((), True),
        "1tamx review-evidence-lane-clearing-recipe": ((), True),
        "1tbt5 memory-retrieval-quality-adaptive-freshness": ((), True),
        "1tbt7 review-evidence-telemetry-attribution": ((), True),
        "1tbvp retire-reindex-reports": ((), True),
        "1tg55 exploration-avoided-signal-quality": ((), True),
        "1ti11 remove-unused-context-efficiency-schema": ((), True),
        "1tis8 memory-eval-mcp-tool-and-decision-log-target": ((), True),
        "1tj0l cwd-independent-host-surface-launchers": ((), True),
        "1tmb1 review-loop-readiness-clearing-path": ((), True),
        "1to7k lifecycle-evidence-and-focus-integrity": ((), True),
        "1tomw events-only-review-evidence-authority": ((), True),
    }

    def setUp(self):
        self.srv = load_server()
        self.review = sys.modules["review_evidence"]
        self.repo = Path(self.srv.__file__).resolve().parents[3]
        if not (self.repo / "docs" / "waves").is_dir():
            self.skipTest("repository wave tree not present")

    def test_closed_declared_waves_match_committed_topology_snapshot(self):
        seen = {}
        for wave_md in sorted((self.repo / "docs" / "waves").glob("*/wave.md")):
            text = wave_md.read_text(encoding="utf-8")
            source, source_errors = self.review.parse_review_evidence_source(text)
            if source is None and not source_errors:
                continue  # legacy wave: prose-only, out of sweep scope
            if not re.search(r"(?mi)^Status:\s*closed\s*$", text):
                continue  # open/readied waves are still moving
            authority = self.review.resolve_review_authority(self.repo, wave_md, wave_text=text)
            self.assertTrue(authority.typed, wave_md)
            lanes = tuple(sorted(self.srv.lifecycle_gate_support._extract_required_review_lanes(text)))
            council = self.srv.lifecycle_gate_support._required_wave_council_signoffs(
                self.repo, "close", wave_text=text, wave_md=wave_md
            )
            required_keys = ["operator-signoff", *lanes, *council]
            green = (
                not authority.ledger_errors
                and all(
                    authority.signoff_current(
                        key,
                        approval_phase=(
                            "readiness"
                            if key == "wave-council-readiness"
                            else "delivery"
                        ),
                    )
                    for key in required_keys
                )
                and authority.evidence_present()
            )
            seen[wave_md.parent.name] = (lanes, green)
        self.assertTrue(seen, "no closed declared waves found — sweep is vacuous")
        for wave_key, derived in sorted(seen.items()):
            expected = self.TOPOLOGY_SNAPSHOT.get(wave_key)
            if expected is None:
                # Waves closed after this snapshot must be typed-green: the
                # facade is the only close-gate derivation they could satisfy.
                self.assertTrue(
                    derived[1],
                    f"newly closed declared wave {wave_key!r} does not derive "
                    f"a green typed review-evidence gate: {derived}",
                )
                continue
            self.assertEqual(derived, expected, wave_key)
        missing = set(self.TOPOLOGY_SNAPSHOT) - set(seen)
        self.assertFalse(missing, f"snapshot waves missing from tree: {sorted(missing)}")


class ReopenWavePurposeStageTests(unittest.TestCase):
    """Wave 1tj0k: `wf_reopen_wave` must not force implement-stage CE
    attribution when a wave is reopened in order to REVIEW it."""

    def setUp(self):
        self.srv = load_server()
        self.runner = load_thin_runner()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = _make_repo(Path(self.tmp.name))
        self.wave_id = "1200a test-wave"
        wave_dir = self.root / "docs" / "waves" / self.wave_id
        wave_dir.mkdir(parents=True, exist_ok=True)
        self.wave_md = wave_dir / "wave.md"
        self.wave_md.write_text(
            "# Wave Record\n"
            f"wave-id: `{self.wave_id}`\n"
            "Status: closed\n\n"
            "## Changes\n\n"
            "Change ID: `1200a-feat sample`\n"
            "Change Status: `implemented`\n\n"
            "## Wave Summary\n\nSome summary.\n",
            encoding="utf-8",
        )
        try:
            self.mcp = self.runner.build_server(self.root)
        except ImportError:
            self.skipTest("mcp package not installed")

    def _tool(self, name):
        return self.mcp._tool_manager._tools[name].fn

    def _stage_calls(self, stage):
        """Durable per-stage call count, read back from the store."""
        snapshot = self.srv.context_efficiency.read_wave_snapshot(
            self.root, self.wave_id
        )
        return int(
            (snapshot.get("stages") or {}).get(stage, {}).get("calls") or 0
        )

    def _focus(self):
        """The EXACT focus the tool mutates.

        Wave 1ti11 repair: per-stage call counts only observe `review` and
        `implement`, so a forbidden move to any other canonical stage (e.g.
        `plan`) is invisible to them. `Focus` is a frozen dataclass, so the
        returned value is a stable by-value snapshot.
        """
        return self.runner._get_handler().telemetry.focus

    def _sealed(self):
        """Durable telemetry seal flag, read straight from the store.

        Wave 1ti11 repair: the seal is not exposed by `read_wave_snapshot`, and
        an unseal leaves per-stage counters unchanged, so it needs its own
        observation or `unseal_wave` on a rejected argument goes undetected.
        """
        path = self.srv.context_efficiency.store_path(self.root)
        if not path.exists():
            return None
        conn = sqlite3.connect(str(path))
        try:
            row = conn.execute(
                "SELECT sealed FROM wave_state WHERE wave_id=?", (self.wave_id,)
            ).fetchone()
        except sqlite3.Error:
            return None
        finally:
            conn.close()
        return None if row is None else bool(row[0])

    def test_reopen_for_review_stores_later_calls_under_review_stage(self):
        """AC-1 (RED before the fix): reopening for review must put durable
        telemetry under `review`, proven through the registered public tool
        and the durable store — not an in-memory focus field."""
        reopen = self._tool("wf_reopen_wave")
        result = reopen(wave_id=self.wave_id, purpose="review")
        self.assertEqual(result.get("status"), "ok", result)
        data = result.get("data") or {}
        self.assertEqual(data.get("focus_stage"), "review", data)

        before = self._stage_calls("review")
        self._tool("wf_list_waves")()          # a recorded first-party call
        after = self._stage_calls("review")
        self.assertGreater(
            after, before,
            "a call after reopen(purpose='review') must be stored under the "
            "review stage; durable snapshot showed no review-stage growth",
        )

    def test_reopen_for_implement_stores_later_calls_under_implement_stage(self):
        """The implement path must durably record under `implement`."""
        result = self._tool("wf_reopen_wave")(
            wave_id=self.wave_id, purpose="implement"
        )
        self.assertEqual(result.get("status"), "ok", result)
        self.assertEqual(
            (result.get("data") or {}).get("focus_stage"), "implement", result
        )
        before = self._stage_calls("implement")
        self._tool("wf_list_waves")()
        self.assertGreater(
            self._stage_calls("implement"), before,
            "a call after reopen(purpose='implement') must be stored under "
            "the implement stage",
        )

    def test_public_schema_marks_purpose_required(self):
        """`purpose` must be REQUIRED in the registered MCP schema, so a caller
        cannot omit it and silently inherit a stage."""
        tool = self.mcp._tool_manager._tools["wf_reopen_wave"]
        schema = getattr(tool, "parameters", None)
        if not isinstance(schema, dict):
            self.skipTest("registered tool exposes no parameter schema")
        required = schema.get("required") or []
        self.assertIn("purpose", required, schema)

    def test_focus_failure_reports_the_exact_failure_envelope(self):
        """Wave 1ti11: when the focus write fails, the reopen still succeeds but
        the response must report NO applied stage, carry `focus_error`, and
        raise the `focus_stage_not_applied` diagnostic.

        This pins the envelope permanently. Against the original false-success
        implementation it fails, because that returned focus_stage='review'.
        """
        handler = self.runner._get_handler()
        with patch.object(
            handler.telemetry,
            "set_focus",
            side_effect=RuntimeError("injected focus failure"),
        ):
            result = self._tool("wf_reopen_wave")(
                wave_id=self.wave_id, purpose="review"
            )
        data = result.get("data") or {}
        codes = [d.get("code") for d in (result.get("diagnostics") or [])]
        self.assertEqual(result.get("status"), "ok", result)
        self.assertIsNone(data.get("focus_stage"), data)
        self.assertIn("injected focus failure", str(data.get("focus_error")), data)
        self.assertIn("focus_stage_not_applied", codes, result)

    def test_focus_failure_never_reports_an_applied_stage(self):
        """Regression guard for the original false success: with the focus write
        failing, no response field may name a stage and the real telemetry focus
        must be unchanged. Also pins that the retired `focus_stage_source` field
        does not resurface."""
        handler = self.runner._get_handler()
        before_focus = self._focus()
        with patch.object(
            handler.telemetry,
            "set_focus",
            side_effect=RuntimeError("injected focus failure"),
        ):
            result = self._tool("wf_reopen_wave")(
                wave_id=self.wave_id, purpose="review"
            )
        data = result.get("data") or {}
        self.assertNotEqual(data.get("focus_stage"), "review", data)
        self.assertNotIn(
            "focus_stage_source", data,
            "focus_stage_source was retired when purpose became required",
        )
        self.assertEqual(
            self._focus(), before_focus,
            "a failed focus write must leave the actual focus unchanged",
        )

    def _assert_purpose_rejected_before_any_mutation(self, **call_kwargs):
        """Shared fail-closed assertion for a rejected `purpose`.

        Wave 1ti11 repair: `purpose` is required, so the MISSING and the
        UNRECOGNIZED cases must both fail closed on this same path.
        """
        before_text = self.wave_md.read_text(encoding="utf-8")
        before_review = self._stage_calls("review")
        before_implement = self._stage_calls("implement")
        before_focus = self._focus()
        before_sealed = self._sealed()

        # Spy on the unseal seam itself. Comparing stored seal state alone is
        # vacuous whenever the fixture wave has no wave_state row (both reads
        # return None), so observe the CALL as well as the state.
        with patch.object(
            self.srv.context_efficiency,
            "unseal_wave",
            wraps=self.srv.context_efficiency.unseal_wave,
        ) as unseal_spy:
            result = self._tool("wf_reopen_wave")(
                wave_id=self.wave_id, **call_kwargs
            )
        self.assertEqual(result.get("status"), "error", result)
        codes = [d.get("code") for d in (result.get("diagnostics") or [])]
        self.assertIn("invalid_purpose", codes)

        self.assertEqual(
            self.wave_md.read_text(encoding="utf-8"), before_text,
            "a rejected purpose must not mutate wave status",
        )
        # Wave 1ti11 repair: assert the EXACT focus and the seal, not just the
        # review/implement counters. A move to any other canonical stage, or an
        # unseal, leaves those counters identical and used to pass here.
        self.assertEqual(
            self._focus(), before_focus,
            "a rejected purpose must not move the focus stage",
        )
        unseal_spy.assert_not_called()
        self.assertEqual(
            self._sealed(), before_sealed,
            "a rejected purpose must not unseal wave telemetry",
        )
        self._tool("wf_list_waves")()
        self.assertEqual(self._stage_calls("review"), before_review)
        self.assertEqual(self._stage_calls("implement"), before_implement)

    def test_invalid_purpose_fails_closed_before_any_mutation(self):
        """AC-3: an UNRECOGNIZED value leaves wave and telemetry untouched."""
        self._assert_purpose_rejected_before_any_mutation(purpose="REVIEWING")

    def test_empty_purpose_fails_closed_before_any_mutation(self):
        """Wave 1ti11: `purpose` is required, so an EMPTY value is rejected on
        the same fail-closed path as an unrecognized one. There is no omitted-
        purpose fallback that could silently select implement."""
        self._assert_purpose_rejected_before_any_mutation(purpose="")

    def test_omitted_purpose_is_rejected_before_the_tool_body_runs(self):
        """Wave 1ti11: the path a STALE pre-1.15.0 caller actually takes.

        Omitting the argument entirely is a different path from passing an
        empty string: it is rejected by the required-parameter signature before
        the tool body executes, so it never reaches the `invalid_purpose`
        branch and carries no recovery hints. What matters is that it still
        mutates nothing. Named separately from the empty-value case so the
        distinction is not lost, since the guided envelope covers only one.
        """
        before_text = self.wave_md.read_text(encoding="utf-8")
        before_focus = self._focus()

        with patch.object(
            self.srv.context_efficiency,
            "unseal_wave",
            wraps=self.srv.context_efficiency.unseal_wave,
        ) as unseal_spy:
            with self.assertRaises(TypeError) as caught:
                self._tool("wf_reopen_wave")(wave_id=self.wave_id)

        self.assertIn("purpose", str(caught.exception))
        self.assertEqual(
            self.wave_md.read_text(encoding="utf-8"), before_text,
            "an omitted purpose must not mutate wave status",
        )
        self.assertEqual(
            self._focus(), before_focus,
            "an omitted purpose must not move the focus stage",
        )
        unseal_spy.assert_not_called()

    def test_docstring_matches_the_implementation_status_guard(self):
        """AC-6: the docstring claimed closed-only; the guard accepts paused."""
        description = str(
            getattr(self.mcp._tool_manager._tools["wf_reopen_wave"], "description", "")
            or ""
        )
        self.assertIn("paused", description.lower())
        self.assertIn("purpose", description.lower())


class EpochSeqlockConcurrencyTests(unittest.TestCase):
    """1sed6 AC-4: the reader seqlock at the MCP tool boundary — a writer
    fencing the build epoch while a search is in flight means the results
    are discarded (structured not-ready), never served as current."""

    def setUp(self):
        load_server()
        self.runner = load_thin_runner()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))
        self.index_dir = self.root / ".wavefoundry" / "index"
        self.index_dir.mkdir(parents=True, exist_ok=True)
        _seed_store_state(self.index_dir, {"content": ["docs", "code"], "file_meta": {}})
        try:
            self.mcp = self.runner.build_server(self.root)
        except ImportError:
            self.skipTest("mcp package not installed")
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "index_state_store", Path(__file__).resolve().parents[1] / "index_state_store.py"
        )
        self.iss = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.iss)

    def tearDown(self):
        self.tmp.cleanup()

    def _tool_fn(self, name: str):
        return self.mcp._tool_manager._tools[name].fn

    def _with_hijacked_response(self, fn, response_name: str, replacement):
        """Swap the response function in the tool closure's own module
        globals (robust across module-instance reloads), returning a restore
        callable."""
        g = fn.__globals__
        original = g[response_name]
        g[response_name] = replacement
        return lambda: g.__setitem__(response_name, original)

    def test_docs_search_discards_results_when_epoch_changes_mid_search(self):
        fn = self._tool_fn("docs_search")

        def racing_writer(index, query, kind, limit=7, tags=None, **kwargs):
            # A build fences the epoch UNDER the in-flight search.
            self.iss.begin_build_epoch(self.index_dir, "concurrent-build")
            return {"status": "ok", "data": {"results": [{"id": "mixed-epoch-chunk"}]}}

        restore = self._with_hijacked_response(fn, "docs_search_response", racing_writer)
        try:
            result = fn("anything")
        finally:
            restore()
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["diagnostics"][0]["code"], "index_not_ready")
        self.assertNotIn("mixed-epoch-chunk", json.dumps(result),
                         "no mixed-epoch result may escape the seqlock")

    def test_docs_search_serves_results_when_epoch_is_stable(self):
        fn = self._tool_fn("docs_search")
        stable = {"status": "ok", "data": {"results": [{"id": "stable-chunk"}]}}
        restore = self._with_hijacked_response(
            fn, "docs_search_response", lambda *a, **k: stable
        )
        try:
            result = fn("anything")
        finally:
            restore()
        self.assertEqual(result["status"], "ok")
        self.assertIn("stable-chunk", json.dumps(result))

    def test_code_search_discards_results_when_epoch_changes_mid_search(self):
        fn = self._tool_fn("code_search")

        def racing_writer(*args, **kwargs):
            self.iss.begin_build_epoch(self.index_dir, "concurrent-build")
            return {"status": "ok", "data": {"results": [{"id": "mixed-epoch-chunk"}]}}

        restore = self._with_hijacked_response(fn, "code_search_response", racing_writer)
        try:
            result = fn("anything")
        finally:
            restore()
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["diagnostics"][0]["code"], "index_not_ready")
        self.assertNotIn("mixed-epoch-chunk", json.dumps(result))


    def test_docs_search_discards_when_epoch_publishes_mid_search(self):
        """Review refutation (initial-None escape): a None pre-token must not
        bypass the post-check — a build PUBLISHING mid-operation (None →
        complete) discards results just like a mid-operation rebuild."""
        # Reset to a token-less store: bookkeeping only, no completed epoch.
        import shutil
        shutil.rmtree(self.index_dir)
        self.index_dir.mkdir(parents=True)
        fn = self._tool_fn("docs_search")

        def publishing_writer(index, query, kind, limit=7, tags=None, **kwargs):
            attempt = self.iss.begin_build_epoch(self.index_dir, "publishing")
            assert self.iss.finalize_build_epoch(self.index_dir, attempt)
            return {"status": "ok", "data": {"results": [{"id": "mixed-epoch-chunk"}]}}

        restore = self._with_hijacked_response(fn, "docs_search_response", publishing_writer)
        try:
            result = fn("anything")
        finally:
            restore()
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["diagnostics"][0]["code"], "index_not_ready")
        self.assertNotIn("mixed-epoch-chunk", json.dumps(result))


    def test_docs_search_discards_on_aba_building_to_building_transition(self):
        """Review reproduction (initial-None ABA): building A → complete A →
        building B entirely within one docs_search. Both endpoints are "not
        ready" (the complete-only token is None at both), but the state-row
        token distinguishes the attempts — the results MUST be discarded."""
        import shutil
        shutil.rmtree(self.index_dir)
        self.index_dir.mkdir(parents=True)
        # Pre-state: building A.
        attempt_a = self.iss.begin_build_epoch(self.index_dir, "A")
        fn = self._tool_fn("docs_search")

        def aba_writer(index, query, kind, limit=7, tags=None, **kwargs):
            assert self.iss.finalize_build_epoch(self.index_dir, attempt_a)
            self.iss.begin_build_epoch(self.index_dir, "B")
            return {"status": "ok", "data": {"results": [{"id": "escaped-aba"}]}}

        restore = self._with_hijacked_response(fn, "docs_search_response", aba_writer)
        try:
            result = fn("anything")
        finally:
            restore()
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["diagnostics"][0]["code"], "index_not_ready")
        self.assertNotIn("escaped-aba", json.dumps(result))

    def test_docs_search_stable_building_state_serves_degraded_path(self):
        """Control: a STABLE building state (no transition at all) is the
        sanctioned degraded path — same attempt before and after serves."""
        import shutil
        shutil.rmtree(self.index_dir)
        self.index_dir.mkdir(parents=True)
        self.iss.begin_build_epoch(self.index_dir, "stable")
        fn = self._tool_fn("docs_search")
        degraded = {"status": "ok", "data": {"results": [{"id": "degraded-ok"}]}}
        restore = self._with_hijacked_response(fn, "docs_search_response", lambda *a, **k: degraded)
        try:
            result = fn("anything")
        finally:
            restore()
        self.assertEqual(result["status"], "ok")
        self.assertIn("degraded-ok", json.dumps(result))

    def test_docs_search_stable_none_token_serves_degraded_path(self):
        """The sanctioned degraded live-walk: a STABLE None token (no build
        activity at all) still serves."""
        import shutil
        shutil.rmtree(self.index_dir)
        self.index_dir.mkdir(parents=True)
        fn = self._tool_fn("docs_search")
        degraded = {"status": "ok", "data": {"results": [{"id": "live-walk-chunk"}]}}
        restore = self._with_hijacked_response(fn, "docs_search_response", lambda *a, **k: degraded)
        try:
            result = fn("anything")
        finally:
            restore()
        self.assertEqual(result["status"], "ok")
        self.assertIn("live-walk-chunk", json.dumps(result))


    def test_strict_tools_use_exactly_one_state_capture(self):
        """Review reproduction (between-probes window): a separate complete-
        probe followed by a state capture let a writer fence BETWEEN the two
        reads — the post-check then compared building==building and served.
        Structural pin: each strict tool's registration captures ONE
        `_epoch_state` token, gates completeness on the CAPTURED token's own
        status field, and has NO separate `_epoch_token` pre-read."""
        import inspect
        srv_path = Path(load_server().__file__)
        src = srv_path.read_text(encoding="utf-8")
        for tool in ("code_search", "code_ask", "code_lexical"):
            reg = src.index(f"    def {tool}(")
            end = src.index("    @mcp.tool", reg)
            body = src[reg:end]
            self.assertEqual(body.count("_epoch_state(get_handler().root, propagate_runtime_errors=True)"), 2,
                             f"{tool}: exactly one capture + one post-compare")
            self.assertIn('_tok[1] != "complete"', body,
                          f"{tool}: completeness gate must check the captured token")
            self.assertNotIn("_epoch_token(", body,
                             f"{tool}: no separate complete-probe read (between-reads window)")

    def test_code_search_refuses_on_building_pre_state_via_captured_token(self):
        """The captured token's own status gates: a BUILDING pre-state (not
        just an absent store) refuses before the response fn runs."""
        self.iss.begin_build_epoch(self.index_dir, "between-probes")
        fn = self._tool_fn("code_search")
        called = []
        restore = self._with_hijacked_response(
            fn, "code_search_response",
            lambda *a, **k: called.append(1) or {"status": "ok", "data": {"results": [{"id": "escaped-between-probes"}]}},
        )
        try:
            result = fn("anything")
        finally:
            restore()
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["diagnostics"][0]["code"], "index_not_ready")
        self.assertEqual(called, [], "a building pre-state must refuse up front")
        self.assertNotIn("escaped-between-probes", json.dumps(result))

    def test_code_search_and_code_ask_refuse_up_front_without_epoch(self):
        """Review refutation: strict pre-gate — with no complete epoch the
        response functions are never invoked, so keyword/graph stages cannot
        surface citations labeled current."""
        import shutil
        shutil.rmtree(self.index_dir)
        self.index_dir.mkdir(parents=True)
        for tool, response_name in (("code_search", "code_search_response"),
                                    ("code_ask", "code_ask_response")):
            fn = self._tool_fn(tool)
            called = []
            restore = self._with_hijacked_response(
                fn, response_name,
                lambda *a, **k: called.append(1) or {"status": "ok", "data": {}},
            )
            try:
                result = fn("anything")
            finally:
                restore()
            self.assertEqual(result["status"], "error", tool)
            self.assertEqual(result["diagnostics"][0]["code"], "index_not_ready", tool)
            self.assertEqual(called, [], f"{tool} must not run over a token-less store")

    def test_seed_get_discards_results_when_epoch_changes_mid_operation(self):
        fn = self._tool_fn("seed_get")

        def racing_writer(index, name):
            self.iss.begin_build_epoch(self.index_dir, "concurrent-build")
            return {"status": "ok", "data": {"seed": {"content": "mixed-epoch-seed"}}}

        restore = self._with_hijacked_response(fn, "seed_get_response", racing_writer)
        try:
            result = fn("020-run-contract")
        finally:
            restore()
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["diagnostics"][0]["code"], "index_not_ready")
        self.assertNotIn("mixed-epoch-seed", json.dumps(result))


    def test_optimize_response_surfaces_refusal_as_structured_error(self):
        """Independent-review N2: the optimize tool must return the structured
        index_not_ready envelope on the restore-only refusal, not crash."""
        srv = load_server()
        with tempfile.TemporaryDirectory() as td:
            root = _make_repo(Path(td))
            index_dir = root / ".wavefoundry" / "index"
            store = srv._load_script("index_state_store").IndexStateStore(index_dir)
            store.close()
            resp = srv._index_optimize_response(root)
            self.assertEqual(resp["status"], "error")
            codes = [d.get("code") for d in resp.get("diagnostics", [])]
            self.assertIn("index_not_ready", codes)

    def test_build_status_reports_interrupted_not_idle_over_building_epoch(self):
        """Review refutation: a `building` epoch with no live builder must
        surface as `interrupted` (with the epoch object), never `idle`."""
        srv = load_server()
        self.iss.begin_build_epoch(self.index_dir, "crashed-builder")
        resp = srv.index_build_status_response(self.root)
        data = resp["data"]
        self.assertEqual(data["state"], "interrupted")
        self.assertEqual(data["epoch"]["status"], "building")
        self.assertTrue(data["epoch"]["interrupted"])
        codes = [d.get("code") for d in resp.get("diagnostics", [])]
        self.assertIn("index_build_interrupted", codes)

    def test_build_status_idle_over_complete_epoch_carries_epoch_object(self):
        srv = load_server()
        resp = srv.index_build_status_response(self.root)
        data = resp["data"]
        self.assertEqual(data["state"], "idle")
        self.assertEqual(data["epoch"]["status"], "complete")
        self.assertFalse(data["epoch"]["interrupted"])

    def test_code_search_discards_when_epoch_changes_during_graph_augmentation(self):
        """Review reproduction (P0): the fence must close AFTER graph
        augmentation — a build fencing during the augmentation read makes
        the WHOLE result mixed and it must be discarded."""
        fn = self._tool_fn("code_search")
        g = fn.__globals__
        stable = {"status": "ok", "data": {"results": [{"id": "pre-augment-chunk"}]}}
        orig_augment = g["_augment_with_graph_neighbors_if_enabled"]

        def fencing_augment(result, root, **kwargs):
            self.iss.begin_build_epoch(self.index_dir, "augmentation-race")
            return result

        restore_resp = self._with_hijacked_response(fn, "code_search_response", lambda *a, **k: stable)
        g["_augment_with_graph_neighbors_if_enabled"] = fencing_augment
        try:
            result = fn("anything")
        finally:
            restore_resp()
            g["_augment_with_graph_neighbors_if_enabled"] = orig_augment
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["diagnostics"][0]["code"], "index_not_ready")
        self.assertNotIn("pre-augment-chunk", json.dumps(result))

    def test_wf_map_discards_when_epoch_changes_mid_operation(self):
        """Pre-release red-team P3: wf_map serves indexed chunk text with a
        disk fallback — same fence class as seed_get."""
        fn = self._tool_fn("wf_map")

        def racing_map(root, address, index):
            self.iss.begin_build_epoch(self.index_dir, "concurrent-build")
            return {"status": "ok", "data": {"excerpt": "mixed-epoch-excerpt", "index_match": True}}

        restore = self._with_hijacked_response(fn, "wf_map_response", racing_map)
        try:
            result = fn("doc:docs/README.md")
        finally:
            restore()
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["diagnostics"][0]["code"], "index_not_ready")
        self.assertNotIn("mixed-epoch-excerpt", json.dumps(result))

    def test_rebuilding_response_carries_contract_fields(self):
        """Review fix (AC-3): refusals carry the always-present contract."""
        srv = load_server()
        resp = srv._index_rebuilding_response("code_search", {"query": "q"})
        self.assertIn("search_mode", resp["data"])
        self.assertIsNone(resp["data"]["search_mode"])
        self.assertEqual(resp["data"]["fallback_reason"], "index_not_ready")
        self.assertEqual(resp["data"]["results"], [])

    def test_search_tools_unknown_args_carry_contract_fields(self):
        """Release review: unknown-argument rejections at the search tools
        carry the always-present contract fields."""
        for tool in ("docs_search", "code_search", "code_ask", "code_lexical", "seed_get"):
            fn = self._tool_fn(tool)
            kw = {"query": "q"} if tool != "code_ask" else {"question": "q"}
            if tool == "seed_get":
                kw = {"name": "q"}
            result = fn(bogus_argument=1, **kw)
            self.assertEqual(result["status"], "error", tool)
            self.assertIn("search_mode", result["data"], tool)
            self.assertIn("fallback_reason", result["data"], tool)


    def test_code_lexical_fails_closed_without_a_complete_epoch(self):
        # Strict pre-gate: mid-build (building status) FTS state is mixed and
        # never served — the tool refuses BEFORE touching the store.
        self.iss.begin_build_epoch(self.index_dir, "in-flight-build")
        fn = self._tool_fn("code_lexical")
        result = fn("anything")
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["diagnostics"][0]["code"], "index_not_ready")


# ---------------------------------------------------------------------------
# wf_audit_install MCP tool (wave 1p35d / change 1p35h)
# ---------------------------------------------------------------------------


class WaveInstallAuditTests(unittest.TestCase):
    """Branch tests for wf_audit_install_response.

    MF-6 (prepare-council must-fix): the end-to-end integration test at the
    bottom walks a realistic install log through all three states.
    """

    _MINIMAL_LOG = """\
# Wavefoundry Install Log

Owner: operator
Status: in-progress

## Phase 1 — Harness (no MCP required)

- [ ] 1.1 — Set lifecycle epoch in workflow-config (seed-020) — artifact: docs/workflow-config.json
- [ ] 1.2 — Bootstrap harness (setup_wavefoundry.py) — artifact: .mcp.json
- [ ] 1.3 — STOP: restart agent (instruction)

## Phase 2 — Project discovery (MCP required)

- [ ] 2.1 — Audit Phase 1 outputs (verify) — expects: wf_audit_install(phase=1) returns next_step
- [ ] 2.2 — Bootstrap evidence base (seed-030) — artifact: docs/repo-profile.json
"""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        import tempfile
        self.srv = type(self).srv
        self._tmp = tempfile.mkdtemp()
        self.root = Path(self._tmp)
        (self.root / "docs").mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def _write_log(self, body):
        log_path = self.root / ".wavefoundry" / "install-log.md"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text(body, encoding="utf-8")

    def _call(self, phase=None):
        from unittest.mock import patch
        with patch.object(self.srv, "run_validate") as mock_validate:
            mock_validate.return_value = {"passed": True, "errors": [], "warnings": [], "output": "ok"}
            return self.srv.wf_audit_install_response(self.root, phase=phase)

    def test_missing_log_returns_missing_log_error(self):
        result = self._call()
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["data"]["status"], "missing_log")
        self.assertIn("install-log.md", result["data"]["expected_path"])
        self.assertNotIn("pending_lint", result["data"])  # 1viyu: pre-lint status carries none
        codes = [d["code"] for d in result.get("diagnostics", [])]
        self.assertIn("install_log_missing", codes)

    def test_utf16_bom_log_surfaces_unparseable_not_crash(self):
        # Wave 1p9hj AC-3: a UTF-16-BOM install log (PowerShell Set-Content/Out-File default on
        # Windows) must NOT crash wf_audit_install with UnicodeDecodeError. read_install_log decodes
        # with errors="replace", is_unparseable classifies the garbled result, and the response
        # surfaces the actionable install_log_unparseable diagnostic instead of vacuous success.
        log_path = self.root / ".wavefoundry" / "install-log.md"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_bytes(self._MINIMAL_LOG.encode("utf-16"))  # includes BOM
        result = self._call()  # must not raise
        codes = [d["code"] for d in result.get("diagnostics", [])]
        self.assertIn("install_log_unparseable", codes)

    def test_unparseable_log_precedes_lint_and_has_no_pending_lint(self):
        from unittest.mock import patch
        log_path = self.root / ".wavefoundry" / "install-log.md"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_bytes(self._MINIMAL_LOG.encode("utf-16"))
        with patch.object(self.srv, "run_validate") as mock_validate:
            result = self.srv.wf_audit_install_response(self.root)
        mock_validate.assert_not_called()
        self.assertEqual(result["data"]["status"], "unparseable_log")
        self.assertNotIn("pending_lint", result["data"])

    def test_expected_absence_advances_and_is_carried_as_pending_lint(self):
        from unittest.mock import patch
        self._write_log(self._MINIMAL_LOG)
        missing = "docs/prompts/index.md: missing required Wavefoundry file"
        with patch.object(self.srv, "run_validate", return_value={
            "passed": False, "errors": [missing], "warnings": [], "output": "fail"
        }):
            result = self.srv.wf_audit_install_response(self.root)
        self.assertEqual(result["data"]["status"], "next_step")
        self.assertEqual(result["data"]["pending_lint"]["errors"], [missing])

    def test_advisory_lint_warning_is_rendered_non_blocking_at_the_install_audit(self):
        """Wave 1wuju (1wujs AC-1; delivery review ARCH-DEL-2): the install audit runs the
        full-corpus lint, so an advisory sensor's finding reaches its envelope as a flagged
        `docs_lint_warning` on the success path and beside `docs_lint_error` on the
        lint-errors path, and it advances the audit either way."""
        from unittest.mock import patch
        self._write_log(self._MINIMAL_LOG)
        warning = ("WARNING: docs/waves/1w test/1w-enh x.md: AC-1 asserts repository-wide state "
                   "('full test suite') [advisory sensor `ac_asserts_repository_state`]")
        with patch.object(self.srv, "run_validate", return_value={
            "passed": True, "errors": [], "warnings": [warning], "output": "ok"
        }):
            clean = self.srv.wf_audit_install_response(self.root)
        self.assertEqual(clean["data"]["status"], "next_step", clean)
        with patch.object(self.srv, "run_validate", return_value={
            "passed": False, "errors": ["docs/x.md: broken"], "warnings": [warning], "output": "fail"
        }):
            blocked = self.srv.wf_audit_install_response(self.root)
        self.assertEqual(blocked["data"]["status"], "lint_errors", blocked)
        self.assertIn("docs_lint_error", [d["code"] for d in blocked["diagnostics"]])
        # Delivery review ARCH-RV2-1: the terminal (complete / phase_complete)
        # envelope carries the same flagged warning.
        import install_log_lib  # the response imports it locally; patch the module object
        with patch.object(self.srv, "run_validate", return_value={
            "passed": True, "errors": [], "warnings": [warning], "output": "ok"
        }), patch.object(install_log_lib, "checked_rows_missing_artifact", return_value=[]), \
             patch.object(install_log_lib, "first_unchecked_row", return_value=None):
            terminal = self.srv.wf_audit_install_response(self.root)
        self.assertIn(terminal["data"]["status"], {"complete", "phase_complete"}, terminal)
        # Docs-contract final pass DOCS-FIN-1: the checked_but_missing envelope
        # (a [x] row whose artifact is absent) carries the same flagged warning
        # beside its own diagnostics, so no post-parse envelope hides it.
        self._write_log(self._MINIMAL_LOG.replace("- [ ] 2.2", "- [x] 2.2"))
        with patch.object(self.srv, "run_validate", return_value={
            "passed": True, "errors": [], "warnings": [warning], "output": "ok"
        }):
            missing = self.srv.wf_audit_install_response(self.root)
        self.assertEqual(missing["data"]["status"], "checked_but_missing", missing)
        self.assertIn("install_log_checked_but_missing", [d["code"] for d in missing["diagnostics"]])
        for label, response in (("clean", clean), ("blocked", blocked), ("terminal", terminal),
                                ("missing", missing)):
            with self.subTest(path=label):
                warnings = [d for d in response.get("diagnostics") or [] if d["code"] == "docs_lint_warning"]
                self.assertEqual(1, len(warnings), response.get("diagnostics"))
                self.assertIs(True, warnings[0].get("advisory"), warnings[0])
                self.assertIn("asserts repository-wide state", warnings[0]["message"])

    def _build_phase_one_complete_tree(self):
        """Wave 1viyu (CODE-DEL-1): a FAITHFUL Phase-1-complete tree.

        Mirrors what ``wf setup`` leaves behind before the operator restarts for
        Phase 2: the shipped ``seeds/`` and ``install/`` trees under
        ``.wavefoundry/framework/``, Step 0 provisioning (lifecycle policy plus
        the seven workflow-config default sections), and the Phase 1
        ``render_agent_surfaces`` pass that materializes the lifecycle prompt
        baselines, the plan-template scaffold, and the review carriers. The
        install log is the shipped template with every Phase 1 row ``[x]``.
        The earlier fixture (bare framework dir, empty ``docs/``) never
        exercised the renderer's own output against the real validator, which
        is exactly where the fresh-install failure lived.
        """
        import shutil
        import setup_wavefoundry
        import render_agent_surfaces

        real_fw = Path(self.srv.__file__).resolve().parent.parent
        target_fw = self.root / ".wavefoundry" / "framework"
        for name in ("seeds", "install"):
            shutil.copytree(real_fw / name, target_fw / name)
        for name in ("VERSION", "README.md"):
            if (real_fw / name).is_file():
                shutil.copy2(real_fw / name, target_fw / name)
        self.assertEqual(setup_wavefoundry._provision_lifecycle_policy_if_absent(self.root), 0)
        self.assertEqual(setup_wavefoundry._provision_workflow_defaults_if_absent(self.root), 0)
        render_agent_surfaces.render_agent_surfaces(self.root)
        template = (target_fw / "install" / "install-log.template.md").read_text(encoding="utf-8")
        lines = []
        for line in template.splitlines():
            if line.startswith("- [ ] 1."):
                line = line.replace("- [ ] 1.", "- [x] 1.", 1)
            lines.append(line)
        self._write_log("\n".join(lines) + "\n")

    def test_real_validator_phase_one_complete_repo_reaches_phase_two_seed(self):
        import contextlib
        import io
        import install_log_lib

        with contextlib.redirect_stdout(io.StringIO()):
            self._build_phase_one_complete_tree()
        review_plan = self.root / "docs" / "prompts" / "review-plan.prompt.md"
        self.assertTrue(review_plan.is_file())
        review_plan_text = review_plan.read_text(encoding="utf-8")
        self.assertIn("Owner: Engineering", review_plan_text)
        self.assertIn("Status: active", review_plan_text)
        self.assertRegex(review_plan_text, r"Last verified: \d{4}-\d{2}-\d{2}")
        self.assertNotIn("{{generated_at}}", review_plan_text)
        # Real validator, no mock: the point of the test.
        scoped = self.srv.wf_audit_install_response(self.root, phase=1)
        self.assertEqual(scoped["data"]["status"], "phase_complete", scoped)
        result = self.srv.wf_audit_install_response(self.root)
        self.assertEqual(result["data"]["status"], "next_step", result)
        self.assertEqual(result["data"]["row"]["number"], "2.1")
        pending = result["data"]["pending_lint"]
        self.assertGreater(pending["count"], 0)
        # Every deferred entry is an absence-class message about a path a later
        # seed row will create; nothing the Phase 1 render itself wrote may be
        # among the deferred set, and nothing at all may be blocking.
        markers = install_log_lib.INSTALL_PENDING_ERROR_MARKERS
        for entry in pending["errors"]:
            self.assertTrue(any(marker in entry for marker in markers), entry)
        # And the renderer's own outputs are lint-clean on their own (the
        # CODE-DEL-1 defect: 21 metadata errors on materialized carriers).
        for entry in pending["errors"]:
            self.assertNotIn("Owner", entry)
            self.assertNotIn("Last verified", entry)

    def test_techdocs_baseline_precondition_fails_on_the_faithful_phase_one_tree(self):
        """Wave 1vj4e (1vj4d AC-3): on a FAITHFUL Phase-1-complete tree the three navigation
        targets do not exist yet, so `wf techdocs-baseline` writes none of the trio, names all
        three missing targets on stderr, exits 1, and leaves the tree byte-identical; the
        faithful audit still reaches the Phase 2 seed with nothing blocking."""
        import contextlib
        import hashlib
        import io
        import wf_cli

        with contextlib.redirect_stdout(io.StringIO()):
            self._build_phase_one_complete_tree()

        def digest() -> dict:
            out = {}
            for path in sorted(self.root.rglob("*")):
                if path.is_file() and not path.is_symlink():
                    out[str(path.relative_to(self.root))] = hashlib.sha256(path.read_bytes()).hexdigest()
            return out

        before = digest()
        err = io.StringIO()
        with patch.object(wf_cli.venv_bootstrap, "activate_tool_venv"), \
             contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
            rc = wf_cli.main(["techdocs-baseline", "--root", str(self.root)])
        self.assertEqual(rc, 1)
        lines = err.getvalue().splitlines()
        self.assertEqual(len(lines), 1, lines)
        self.assertTrue(lines[0].startswith("techdocs-baseline: ERROR precondition unmet"), lines)
        for target in ("docs/references/project-overview.md", "docs/ARCHITECTURE.md", "docs/prompts/index.md"):
            self.assertIn(target, lines[0])
        for rel in ("catalog-info.yaml", "mkdocs.yml", "docs/index.md"):
            self.assertFalse((self.root / rel).exists(), rel)
        self.assertEqual(digest(), before)
        result = self.srv.wf_audit_install_response(self.root)
        self.assertEqual(result["data"]["status"], "next_step", result)
        self.assertEqual(result["data"]["row"]["number"], "2.1")

    def test_blocking_error_is_separated_from_pending_absence(self):
        from unittest.mock import patch
        self._write_log(self._MINIMAL_LOG)
        pending = "docs/prompts/index.md: missing required Wavefoundry file"
        blocking = "docs/workflow-config.json: invalid policy value"
        with patch.object(self.srv, "run_validate", return_value={
            "passed": False, "errors": [pending, blocking], "warnings": [], "output": "fail"
        }):
            result = self.srv.wf_audit_install_response(self.root)
        self.assertEqual(result["data"]["status"], "lint_errors")
        self.assertEqual(result["data"]["errors"], [blocking])
        self.assertEqual(result["data"]["pending_lint"]["errors"], [pending])

    def test_final_tail_advances_214_then_215_then_complete(self):
        tail = """# Install\n\n## Phase 2\n\n- [ ] 2.14 — Remove bootstrap installer (instruction)\n- [ ] 2.15 — Prepare structured operator summary (instruction)\n"""
        self._write_log(tail)
        first = self._call()
        self.assertEqual(first["data"]["row"]["number"], "2.14")
        self._write_log(tail.replace("- [ ] 2.14", "- [x] 2.14"))
        second = self._call()
        self.assertEqual(second["data"]["row"]["number"], "2.15")
        self._write_log(tail.replace("- [ ]", "- [x]"))
        final = self._call()
        self.assertEqual(final["data"]["status"], "complete")
        # 1viyu matrix: next_step / complete carry pending_lint (empty here);
        # missing_log / unparseable_log never do (asserted in their own tests).
        self.assertIn("pending_lint", first["data"])
        self.assertIn("pending_lint", final["data"])
        self.assertEqual(final["data"]["pending_lint"]["count"], 0)

    def test_lint_errors_block_and_no_artifact_check(self):
        from unittest.mock import patch
        self._write_log(self._MINIMAL_LOG)
        with patch.object(self.srv, "run_validate") as mock_validate:
            mock_validate.return_value = {
                "passed": False,
                "errors": ["ERROR: foo.md missing required Role: field"],
                "warnings": [],
                "output": "fail",
            }
            result = self.srv.wf_audit_install_response(self.root)
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["data"]["status"], "lint_errors")
        self.assertEqual(result["data"]["errors"], ["ERROR: foo.md missing required Role: field"])
        self.assertIn("docs-lint", result["data"]["next_action"])

    def test_a_lint_crash_reaches_the_install_audit_through_the_real_parser(self):
        """Wave 1wybs (1wybr AC-3; replaces the 1viyu patched-result pin and the
        1wuju hand-built gap pin): a crashed docs-lint subprocess (non-zero exit,
        no ERROR line) is parsed by the real run_validate into the producer's
        verdict-gap entry, which blocks the audit and is never deferred as
        pending lint, even when its tail quotes an absence marker while seed
        rows still pend (RTD-1)."""
        from unittest.mock import MagicMock, patch
        cases = {
            "plain_crash": (
                self._MINIMAL_LOG.replace("- [ ]", "- [x]"),
                "docs/: missing repository docs root",
            ),
            "absence_marker_tail_with_pending_rows": (
                self._MINIMAL_LOG,
                "WARNING: docs/x.md: missing required Wavefoundry file",
            ),
        }
        for label, (log, tail) in cases.items():
            with self.subTest(case=label):
                self._write_log(log)
                output = "Traceback (most recent call last):\n" + tail + "\n"
                crashed = MagicMock(returncode=1, stdout="", stderr=output)
                with patch.object(self.srv, "_mcp_subprocess_run", return_value=crashed):
                    result = self.srv.wf_audit_install_response(self.root)
                self.assertEqual(result["status"], "error")
                self.assertEqual(result["data"]["status"], "lint_errors")
                expected = self.srv._docs_lint_verdict_gap_error(1, output, self.root)
                self.assertEqual([expected], result["data"]["errors"])
                self.assertEqual(0, result["data"]["pending_lint"]["count"])
                self.assertEqual([], result["data"]["pending_lint"]["errors"])
                self.assertIn(tail.split(": ", 1)[-1], result["data"]["errors"][0])

    def test_checked_but_missing_artifact_returns_diagnostic(self):
        log = self._MINIMAL_LOG.replace(
            "- [ ] 1.1 — Set lifecycle epoch in workflow-config (seed-020) — artifact: docs/workflow-config.json",
            "- [x] 1.1 — Set lifecycle epoch in workflow-config (seed-020) — artifact: docs/workflow-config.json",
        )
        self._write_log(log)
        result = self._call()
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["data"]["status"], "checked_but_missing")
        self.assertEqual(result["data"]["row"]["number"], "1.1")
        # Wave 1wybs (1wybr AC-4): every operator-facing path is repo-relative.
        self.assertEqual("docs/workflow-config.json", result["data"]["expected_artifact"])
        self.assertEqual(
            ["docs/workflow-config.json"],
            [m["expected_artifact"] for m in result["data"]["all_missing"]],
        )
        self.assertIn("does not exist at docs/workflow-config.json.", result["data"]["next_action"])
        messages = [
            d["message"] for d in result["diagnostics"] if d["code"] == "install_log_checked_but_missing"
        ]
        self.assertEqual(1, len(messages), result["diagnostics"])
        self.assertIn("does not exist at docs/workflow-config.json.", messages[0])
        for text in (result["data"]["next_action"], messages[0]):
            self.assertNotIn(str(self.root), text)
            self.assertNotIn(str(self.root.resolve()), text)
        self.assertIn("pending_lint", result["data"])  # 1viyu matrix
        # An operator-authored row whose artifact resolves outside the repository
        # still returns the envelope, carrying a `..`-relative path (readiness RT-RDY-5;
        # delivery review CODE-DEL-5 replaced the resolved-string fallback).
        escaping = self._MINIMAL_LOG.replace(
            "- [ ] 1.1 — Set lifecycle epoch in workflow-config (seed-020) — artifact: docs/workflow-config.json",
            "- [x] 1.1 — Set lifecycle epoch in workflow-config (seed-020) — artifact: ../outside/config.json",
        )
        self._write_log(escaping)
        result = self._call()
        self.assertEqual(result["data"]["status"], "checked_but_missing")
        # Delivery review CODE-DEL-5: a `..`-relative path, never an absolute segment.
        self.assertEqual("../outside/config.json", result["data"]["expected_artifact"])
        self.assertIn("does not exist at ../outside/config.json.", result["data"]["next_action"])
        for text in (result["data"]["expected_artifact"], result["data"]["next_action"]):
            self.assertNotIn(str(self.root.resolve().parent), text)

    def test_checked_row_missing_artifact_still_flagged_while_absences_pend(self):
        """Wave 1viyu (1vitr test f): a [x] seed row whose OWN artifact is absent
        returns checked_but_missing even while other seed rows pend and lint carries
        expected absences; CHECK 2 is unaffected by the classifier."""
        from unittest.mock import patch
        log = self._MINIMAL_LOG.replace(
            "- [ ] 1.1 — Set lifecycle epoch in workflow-config (seed-020) — artifact: docs/workflow-config.json",
            "- [x] 1.1 — Set lifecycle epoch in workflow-config (seed-020) — artifact: docs/workflow-config.json",
        )
        self._write_log(log)
        pending = "docs/prompts/index.md: missing required Wavefoundry file"
        with patch.object(self.srv, "run_validate", return_value={
            "passed": False, "errors": [pending], "warnings": [], "output": "fail"
        }):
            result = self.srv.wf_audit_install_response(self.root)
        self.assertEqual(result["data"]["status"], "checked_but_missing")
        self.assertEqual(result["data"]["row"]["number"], "1.1")
        self.assertEqual(result["data"]["pending_lint"]["errors"], [pending])

    def test_next_step_returned_when_all_clean(self):
        self._write_log(self._MINIMAL_LOG)
        result = self._call()
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["data"]["status"], "next_step")
        self.assertEqual(result["data"]["row"]["number"], "1.1")
        self.assertIn("install-log.md", result["data"]["instructions"])

    def test_complete_status_when_all_rows_terminal(self):
        (self.root / "docs" / "workflow-config.json").write_text("{}\n")
        (self.root / ".mcp.json").write_text("{}\n")  # wave 1p7tz: 1.2 artifact is .mcp.json
        (self.root / "docs" / "repo-profile.json").write_text("{}\n")
        log = self._MINIMAL_LOG.replace("- [ ]", "- [x]")
        self._write_log(log)
        result = self._call()
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["data"]["status"], "complete")

    def test_tilde_row_skipped_by_next_step(self):
        (self.root / "docs" / "workflow-config.json").write_text("{}\n")
        log = self._MINIMAL_LOG.replace(
            "- [ ] 1.1 — Set lifecycle epoch in workflow-config (seed-020) — artifact: docs/workflow-config.json",
            "- [x] 1.1 — Set lifecycle epoch in workflow-config (seed-020) — artifact: docs/workflow-config.json",
        ).replace(
            "- [ ] 1.2 — Bootstrap harness (setup_wavefoundry.py) — artifact: .mcp.json",
            "- [~] 1.2 — Bootstrap harness (setup_wavefoundry.py) — artifact: .mcp.json",
        )
        self._write_log(log)
        result = self._call()
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["data"]["status"], "next_step")
        self.assertEqual(result["data"]["row"]["number"], "1.3")

    def test_phase_arg_limits_next_step_to_phase(self):
        (self.root / "docs" / "workflow-config.json").write_text("{}\n")
        (self.root / ".mcp.json").write_text("{}\n")  # wave 1p7tz: 1.2 artifact is .mcp.json
        log = self._MINIMAL_LOG.replace(
            "- [ ] 1.1 —",
            "- [x] 1.1 —",
        ).replace(
            "- [ ] 1.2 —",
            "- [x] 1.2 —",
        ).replace(
            "- [ ] 1.3 —",
            "- [x] 1.3 —",
        )
        self._write_log(log)
        result = self._call(phase=1)
        self.assertEqual(result["status"], "ok")
        self.assertIn(result["data"]["status"], ("complete", "phase_complete"))
        self.assertIn("pending_lint", result["data"])  # 1viyu matrix

    def test_mf6_integration_walk_through_state_transitions(self):
        """MF-6: walk a realistic install log through lint-fail -> fix -> checked-but-missing -> fix -> next-step -> complete."""
        from unittest.mock import patch
        self._write_log(self._MINIMAL_LOG)
        with patch.object(self.srv, "run_validate") as mock_validate:
            mock_validate.return_value = {
                "passed": False,
                "errors": ["ERROR: simulated lint failure"],
                "warnings": [],
                "output": "fail",
            }
            r = self.srv.wf_audit_install_response(self.root)
        self.assertEqual(r["data"]["status"], "lint_errors")

        log_with_x = self._MINIMAL_LOG.replace(
            "- [ ] 1.1 — Set lifecycle epoch in workflow-config (seed-020) — artifact: docs/workflow-config.json",
            "- [x] 1.1 — Set lifecycle epoch in workflow-config (seed-020) — artifact: docs/workflow-config.json",
        )
        self._write_log(log_with_x)
        r = self._call()
        self.assertEqual(r["data"]["status"], "checked_but_missing")
        self.assertEqual(r["data"]["row"]["number"], "1.1")

        (self.root / "docs" / "workflow-config.json").write_text("{}\n")
        r = self._call()
        self.assertEqual(r["data"]["status"], "next_step")
        self.assertEqual(r["data"]["row"]["number"], "1.2")

        (self.root / ".mcp.json").write_text("{}\n")  # wave 1p7tz: 1.2 artifact is .mcp.json
        (self.root / "docs" / "repo-profile.json").write_text("{}\n")
        log_all_done = log_with_x.replace("- [ ]", "- [x]")
        self._write_log(log_all_done)
        r = self._call()
        self.assertEqual(r["data"]["status"], "complete")

    # --- Wave 1p8gw: description-as-path regression ---

    _COMPOUND_LOG = """\
# Wavefoundry Install Log

Owner: operator
Status: in-progress

## Phase 1 — Harness (no MCP required)

- [ ] 1.1 — Set lifecycle epoch in workflow-config (seed-020) — artifact: docs/workflow-config.json
- [x] 1.2 — Bootstrap harness: venv + deps (setup_wavefoundry.py) — artifact: the committed `.mcp.json` names `command: "python"` + `args: [...]` AND `python3 .wavefoundry/framework/scripts/server.py --dry-run` exits 0
- [ ] 1.3 — STOP: restart agent (instruction)
"""

    def test_compound_artifact_row_not_reported_as_missing_path(self):
        # Regression for the native-Windows defect: a [x] row whose artifact: value is a compound
        # verification DESCRIPTION (backticks + " AND " + "exits 0") must NOT be stat'd as a literal
        # file path. Before the fix the audit returned checked_but_missing for a bogus "path".
        self._write_log(self._COMPOUND_LOG)
        (self.root / "docs" / "workflow-config.json").write_text("{}\n")  # 1.1 artifact (still pending)
        result = self._call()
        # The compound 1.2 row is [x] but is a description — it must be skipped, so the audit advances
        # to the first pending row (1.1), never reporting checked_but_missing for 1.2.
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["data"]["status"], "next_step")
        self.assertEqual(result["data"]["row"]["number"], "1.1")

    def test_compound_artifact_row_brief_exposes_description_not_path(self):
        # Mark 1.1 [x] too (its artifact exists) so the audit reaches 1.3 — proving 1.2 (the compound
        # row) is treated as terminal/non-path and never blocks. The row brief classifies it correctly.
        log = self._COMPOUND_LOG.replace(
            "- [ ] 1.1 — Set lifecycle epoch in workflow-config (seed-020) — artifact: docs/workflow-config.json",
            "- [x] 1.1 — Set lifecycle epoch in workflow-config (seed-020) — artifact: docs/workflow-config.json",
        )
        self._write_log(log)
        (self.root / "docs" / "workflow-config.json").write_text("{}\n")
        result = self._call()
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["data"]["status"], "next_step")
        self.assertEqual(result["data"]["row"]["number"], "1.3")
        # Directly confirm 1.2's classification via the parser the audit uses.
        import install_log_lib
        rows = install_log_lib.parse_log(log)
        row_12 = next(r for r in rows if r.number == "1.2")
        self.assertIsNone(row_12.artifact_path)
        self.assertIsNotNone(row_12.description)


# ---------------------------------------------------------------------------
# seed_get disk-fallback (wave 1p35d / change 1p35j)
# ---------------------------------------------------------------------------


class SeedGetDiskFallbackTests(unittest.TestCase):
    """Tests for the seed_get disk-fallback path.

    AC-2: every seed file in .wavefoundry/framework/seeds/ is reachable.
    AC-3: closest-match suggestions surface for unknown names.
    """

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        import tempfile
        self.srv = type(self).srv
        self._tmp = tempfile.mkdtemp()
        self.root = Path(self._tmp)
        seeds_dir = self.root / ".wavefoundry" / "framework" / "seeds"
        seeds_dir.mkdir(parents=True)
        (seeds_dir / "010-install-wavefoundry.prompt.md").write_text(
            "# 010 - Init\n\nPreamble for seed 010.\n", encoding="utf-8"
        )
        (seeds_dir / "216-reality-checker.prompt.md").write_text(
            "# Reality Checker\n\nSpecialist body.\n", encoding="utf-8"
        )
        (seeds_dir / "224-data-engineer.prompt.md").write_text(
            "# Data Engineer\n\nSpecialist body.\n", encoding="utf-8"
        )
        (seeds_dir / "232-api-tester.prompt.md").write_text(
            "# API Tester\n\nSpecialist body.\n", encoding="utf-8"
        )

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def _make_empty_index_stub(self):
        # 1sed6: _ensure_loaded revalidates the epoch token even when loaded —
        # seed a completed (empty) build so the stub survives revalidation and
        # get_seed exercises its DISK fallback (no seed chunks in Lance).
        _seed_store_state(self.root / ".wavefoundry" / "index",
                          {"model_versions": {}, "content": [], "file_meta": {}})
        idx = self.srv.WaveIndex(self.root)
        idx._loaded = True
        idx._loaded_meta_signature = {"project": idx._index_meta_signature(idx.index_dir)}
        idx._proj_docs_vector_layer = None
        idx._fw_docs_vector_layer = None
        return idx

    def test_disk_fallback_finds_seed_by_number(self):
        idx = self._make_empty_index_stub()
        for num in ("216", "224", "232"):
            with self.subTest(num=num):
                chunk = idx.get_seed(num)
                self.assertIsNotNone(chunk)
                self.assertIn(num, chunk["path"])
                self.assertEqual(chunk.get("_source"), "disk_fallback")

    def test_disk_fallback_finds_seed_by_substring(self):
        idx = self._make_empty_index_stub()
        chunk = idx.get_seed("reality")
        self.assertIsNotNone(chunk)
        self.assertIn("216-reality-checker", chunk["path"])

    def test_disk_fallback_returns_none_for_unknown(self):
        idx = self._make_empty_index_stub()
        self.assertIsNone(idx.get_seed("999"))

    def test_closest_seed_names_returns_suggestions(self):
        idx = self._make_empty_index_stub()
        suggestions = idx.closest_seed_names("realtiy-checker")
        self.assertTrue(any("reality" in s for s in suggestions),
                        f"expected reality-checker suggestion, got: {suggestions}")


class SeedGetCoverageTest(unittest.TestCase):
    """AC-2: every numbered seed file on disk is reachable via seed_get."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()
        cls.repo_root = Path(__file__).resolve().parents[3]
        cls.seeds_dir = cls.repo_root / ".wavefoundry" / "framework" / "seeds"

    def setUp(self):
        self.srv = type(self).srv

    def test_every_numbered_seed_reachable(self):
        seeds = sorted(self.seeds_dir.glob("*.prompt.md")) + sorted(self.seeds_dir.glob("*.md"))
        seen: set[Path] = set()
        unique: list[Path] = []
        for p in seeds:
            if p in seen:
                continue
            seen.add(p)
            unique.append(p)

        idx = self.srv.WaveIndex(self.repo_root)
        idx._loaded = True
        idx._proj_docs_vector_layer = None
        idx._fw_docs_vector_layer = None

        misses: list[str] = []
        for p in unique:
            stem = p.name
            num_prefix = stem.split("-", 1)[0].split(".", 1)[0]
            if not num_prefix.isdigit():
                continue
            chunk = idx.get_seed(num_prefix)
            if chunk is None or not chunk.get("text"):
                misses.append(f"{num_prefix} -> {stem}")
        self.assertEqual(misses, [], f"seeds not reachable via seed_get: {misses}")


# ---------------------------------------------------------------------------
# Wave close secrets gate (wave 1p3rm / 1p3rp)
# ---------------------------------------------------------------------------

_WAVE_CLOSE_READY_TEXT = (
    "# Wave Record\n"
    "wave-id: `{wave_id}`\n"
    "Status: active\n\n"
    "## Changes\n\n"
    "Change ID: `{wave_id}-feat sample`\n"
    "Change Status: `complete`\n\n"
    "## Review Evidence\n\n"
    "- operator-signoff: approved\n"
)

_MOCK_PASS = {"passed": True, "errors": [], "warnings": [], "output": ""}
_MOCK_GARDEN_PASS = {"passed": True, "files_updated": 0, "updated": [], "output": ""}


class WaveCloseSecretsGateTests(unittest.TestCase):
    """AC-1..AC-10 for 1p3rp (wf_close_wave secrets gate)."""

    def setUp(self):
        self.srv = load_server()
        self.tmp = Path(tempfile.mkdtemp())
        self.root = _make_repo(self.tmp)
        self.wave_id = "1200b secrets-gate-test"
        wave_dir = self.root / "docs" / "waves" / self.wave_id
        wave_dir.mkdir(parents=True, exist_ok=True)
        wave_text = _WAVE_CLOSE_READY_TEXT.format(wave_id=self.wave_id)
        (wave_dir / "wave.md").write_text(wave_text, encoding="utf-8")
        # 1v0lx: close blocks on a missing admitted document; the close-ready
        # fixture models a valid wave, so its docs exist on disk.
        for cid in self.srv._CHANGE_ID_PATTERN.findall(wave_text):
            (wave_dir / f"{cid}.md").write_text(
                f"# Sample\n\nChange ID: `{cid}`\n", encoding="utf-8")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _write_exceptions(self, entries: list) -> None:
        path = self.root / "docs" / "scan-findings.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(entries, indent=2) + "\n", encoding="utf-8")

    def _close(self, mode: str = "dry_run") -> dict:
        with patch.object(self.srv, "run_garden", return_value=_MOCK_GARDEN_PASS):
            with patch.object(self.srv, "run_validate", return_value=_MOCK_PASS):
                return self.srv.wf_close_wave_response(self.root, self.wave_id, mode=mode)

    def _diagnostic_codes(self, result: dict) -> set[str]:
        return {d["code"] for d in result.get("diagnostics", [])}

    def test_no_exceptions_file_passes_gate(self):
        # absent file: no block, no reminder
        result = self._close()
        self.assertNotIn("secrets_gate_unresolved", self._diagnostic_codes(result))
        self.assertNotIn("confirmed_secrets", result["data"])

    def _record_guard_skip(self):
        from scanner_skips import LEDGER_REL, update_scanner_skips
        (self.root / "omitted.txt").write_bytes(b"\0fixture")
        row = {"file": "omitted.txt", "reason": "binary file", "detail": "NUL byte in first 8192 bytes"}
        update_scanner_skips(self.root, {"omitted.txt": {"complete": False, "skips": [row]}})
        return self.root / LEDGER_REL, row

    def test_guard_skip_advisory_on_dry_run_and_successful_close(self):
        ledger, row = self._record_guard_skip()
        before = ledger.read_bytes()
        for mode in ("dry_run", "create"):
            with self.subTest(mode=mode):
                result = self._close(mode)
                self.assertEqual(result["status"], "dry_run" if mode == "dry_run" else "ok", result)
                self.assertEqual(result["data"]["scanner_skips"], [row])
                self.assertEqual(ledger.read_bytes(), before)

    def test_guard_skip_advisory_survives_existing_secret_block(self):
        _, row = self._record_guard_skip()
        self._write_exceptions([{
            "id": "exc-001", "file": "config.py", "line": 1, "rule_id": "r",
            "matched_text": "****", "status": "pending", "confirmations": [],
        }])
        result = self._close()
        self.assertEqual(result["status"], "error")
        self.assertIn("secrets_gate_unresolved", self._diagnostic_codes(result))
        self.assertEqual(result["data"]["scanner_skips"], [row])

    def test_absent_and_malformed_guard_history_do_not_change_close_status(self):
        from scanner_skips import LEDGER_REL
        ledger = self.root / LEDGER_REL
        result = self._close()
        self.assertNotIn("scanner_skips", result["data"])
        self.assertNotIn("scanner_skips_error", result["data"])
        self.assertFalse(ledger.exists())
        ledger.parent.mkdir(parents=True, exist_ok=True)
        ledger.write_bytes(b"malformed")
        result = self._close()
        self.assertEqual(result["status"], "dry_run", result)
        self.assertNotIn("scanner_skips", result["data"])
        self.assertIn("coverage unavailable", result["data"]["scanner_skips_error"].lower())
        self.assertEqual(ledger.read_bytes(), b"malformed")

    def test_guard_advisory_reads_observations_after_existing_validation(self):
        def validation(root):
            self.assertEqual(root, self.root)
            self._record_guard_skip()
            return _MOCK_PASS
        with patch.object(self.srv, "run_validate", side_effect=validation) as validate:
            result = self.srv.wf_close_wave_response(self.root, self.wave_id, mode="dry_run")
        validate.assert_called_once()
        self.assertEqual(result["status"], "dry_run", result)
        self.assertEqual(result["data"]["scanner_skips"][0]["file"], "omitted.txt")

    def test_empty_exceptions_file_passes_gate(self):
        self._write_exceptions([])
        result = self._close()
        self.assertNotIn("secrets_gate_unresolved", self._diagnostic_codes(result))
        self.assertNotIn("confirmed_secrets", result["data"])

    def test_always_present_empty_ledger_does_not_block(self):
        # Wave 1p8o5 #4 / AC-4: a clean full scan now WRITES a bare `[]` (always-present ledger). That
        # `[]` must keep the gate non-blocking — presence of the file is "scan ran", not "has findings".
        # This pins the always-write (#4) → gate (`[]` → no block) contract end-to-end.
        path = self.root / "docs" / "scan-findings.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("[]\n", encoding="utf-8")  # exactly what save_exceptions(root, []) writes
        result = self._close()
        self.assertNotIn("secrets_gate_unresolved", self._diagnostic_codes(result))
        self.assertNotIn("confirmed_secrets", result["data"])

    def test_pending_entry_hard_blocks(self):
        self._write_exceptions([{
            "id": "exc-001", "file": "config.py", "line": 1,
            "rule_id": "test-rule", "matched_text": "sk_l****5678",
            "status": "pending", "confirmations": [],
        }])
        result = self._close()
        self.assertEqual(result["status"], "error")
        self.assertIn("secrets_gate_unresolved", self._diagnostic_codes(result))

    def test_pending_hard_block_lists_entry_details(self):
        self._write_exceptions([{
            "id": "exc-001", "file": "config.py", "line": 5,
            "rule_id": "stripe-key", "matched_text": "sk_l****5678",
            "status": "pending", "confirmations": [],
        }])
        result = self._close()
        msg = next(d["message"] for d in result["diagnostics"] if d["code"] == "secrets_gate_unresolved")
        self.assertIn("config.py", msg)
        self.assertIn("stripe-key", msg)

    def test_suspected_secret_hard_blocks(self):
        # 1p5pz: suspected-secret is unresolved → hard-block until reclassified
        self._write_exceptions([{
            "id": "exc-005", "file": "auth.py", "line": 7,
            "rule_id": "github-token", "matched_text": "ghp_****ABCD",
            "status": "suspected-secret", "confirmations": [],
        }])
        result = self._close()
        self.assertEqual(result["status"], "error")
        self.assertIn("secrets_gate_unresolved", self._diagnostic_codes(result))

    def test_suspected_secret_blocks_even_with_legacy_ack(self):
        # legacy acknowledged_for_wave must NOT unblock an unresolved suspected-secret
        self._write_exceptions([{
            "id": "exc-005", "file": "auth.py", "line": 7,
            "rule_id": "github-token", "matched_text": "ghp_****ABCD",
            "status": "suspected-secret", "override_reason": "old",
            "acknowledged_for_wave": self.wave_id, "confirmations": [],
        }])
        result = self._close()
        self.assertEqual(result["status"], "error")
        self.assertIn("secrets_gate_unresolved", self._diagnostic_codes(result))

    def test_unknown_status_fails_closed(self):
        # fail-closed: an unrecognized/typo status must hard-block, not slip through
        self._write_exceptions([{
            "id": "exc-009", "file": "x.py", "line": 1, "rule_id": "r",
            "matched_text": "****", "status": "totally-bogus", "confirmations": [],
        }])
        result = self._close()
        self.assertEqual(result["status"], "error")
        self.assertIn("secrets_gate_unresolved", self._diagnostic_codes(result))

    def test_confirmed_secret_does_not_block(self):
        # 1p5pz: confirmed-secret no longer blocks close
        self._write_exceptions([{
            "id": "exc-002", "file": "secret.py", "line": 3,
            "rule_id": "aws-key", "matched_text": "AKIA****WXYZ",
            "status": "confirmed-secret", "confirmations": [],
        }])
        result = self._close()
        self.assertNotEqual(result["status"], "error")
        self.assertNotIn("secrets_gate_unresolved", self._diagnostic_codes(result))

    def test_confirmed_secret_reminder_on_success_path(self):
        # the standing reminder rides the (non-error) close response data
        self._write_exceptions([{
            "id": "exc-002", "file": "secret.py", "line": 3,
            "rule_id": "aws-key", "matched_text": "AKIA****WXYZ",
            "status": "confirmed-secret", "confirmations": [],
        }])
        result = self._close()
        self.assertNotEqual(result["status"], "error")
        self.assertEqual([i["id"] for i in result["data"]["confirmed_secrets"]], ["exc-002"])
        self.assertIn("confirmed secret", result["data"]["secrets_reminder"].lower())
        self.assertIn("secret.py", result["data"]["secrets_reminder"])

    def test_confirmed_secret_reminder_also_on_error_path(self):
        # a separate blocking finding errors the close, but the reminder still surfaces
        self._write_exceptions([
            {"id": "exc-001", "file": "config.py", "line": 1, "rule_id": "r",
             "matched_text": "****", "status": "pending", "confirmations": []},
            {"id": "exc-002", "file": "secret.py", "line": 3, "rule_id": "aws-key",
             "matched_text": "AKIA****WXYZ", "status": "confirmed-secret", "confirmations": []},
        ])
        result = self._close()
        self.assertEqual(result["status"], "error")
        self.assertIn("secrets_gate_unresolved", self._diagnostic_codes(result))
        self.assertEqual([i["id"] for i in result["data"]["confirmed_secrets"]], ["exc-002"])

    def test_confirmed_secret_legacy_ack_fields_tolerated(self):
        # legacy acknowledged_for_wave / override_reason are ignored, not errored
        self._write_exceptions([{
            "id": "exc-002", "file": "secret.py", "line": 3,
            "rule_id": "aws-key", "matched_text": "AKIA****WXYZ",
            "status": "confirmed-secret", "override_reason": "rotating",
            "acknowledged_for_wave": "1100z some-other-wave", "confirmations": [],
        }])
        result = self._close()
        self.assertNotEqual(result["status"], "error")
        self.assertIn("confirmed_secrets", result["data"])

    def test_gate_does_not_run_after_mutations(self):
        # unresolved finding blocks before mutations; wave.md stays unchanged on block
        self._write_exceptions([{
            "id": "exc-001", "file": "x.py", "line": 1,
            "rule_id": "r", "matched_text": "****",
            "status": "pending", "confirmations": [],
        }])
        wave_md = self.root / "docs" / "waves" / self.wave_id / "wave.md"
        before = wave_md.read_text(encoding="utf-8")
        self._close(mode="create")
        after = wave_md.read_text(encoding="utf-8")
        self.assertEqual(before, after, "wave.md was mutated despite gate block")

    def test_false_positive_status_does_not_trigger_gate(self):
        # false-positive entries are not a gate concern and produce no reminder
        self._write_exceptions([{
            "id": "exc-004", "file": "test_x.py", "line": 2,
            "rule_id": "stripe-key", "matched_text": "sk_l****test",
            "status": "false-positive", "confirmations": [
                {"git_user_name": "A", "git_user_email": "a@x.com",
                 "verdict": "false-positive", "reason": "fixture",
                 "confirmed_at": "2026-06-06T10:00:00Z"},
                {"git_user_name": "B", "git_user_email": "b@x.com",
                 "verdict": "false-positive", "reason": "fixture",
                 "confirmed_at": "2026-06-06T11:00:00Z"},
            ],
        }])
        result = self._close()
        self.assertNotIn("secrets_gate_unresolved", self._diagnostic_codes(result))
        self.assertNotIn("confirmed_secrets", result["data"])


def _typed_event_race_worker(
    scripts_root, root, wave_id, actor, barrier, disable_lock, results
):
    """Spawn-process worker for the public create-mode typed-event race.

    No lock is mocked on the real path: the transaction runs exactly as
    shipped. ``disable_lock`` is the focused known-bad mutation — it bypasses
    the cross-process publication lock so the fixture can prove it detects a
    lost or interleaved append.
    """
    import contextlib as _contextlib
    import sys as _sys
    import time as _time
    from pathlib import Path as _Path

    _sys.path.insert(0, scripts_root)
    import server_impl as srv

    if disable_lock:
        srv.project_state_publication_lock = (
            lambda _root: _contextlib.nullcontext()
        )

    window = {}
    real_validate = srv.validate_external_review_evidence

    def instrumented_validate(path, **kwargs):
        result = real_validate(path, **kwargs)
        if "enter" not in window:
            window["enter"] = _time.monotonic()
            # Hold the transaction open so a lock bypass guarantees both
            # processes read the ledger before either writes it.
            _time.sleep(0.6)
        return result

    real_replace = srv._atomic_replace_bytes

    def instrumented_replace(path, payload, label):
        if label == "review-events":
            window["write"] = _time.monotonic()
        return real_replace(path, payload, label)

    srv.validate_external_review_evidence = instrumented_validate
    srv._atomic_replace_bytes = instrumented_replace

    barrier.wait()
    response = srv.wf_review_event_response(
        _Path(root),
        wave_id,
        "approval",
        actor,
        f"race-context-{actor}",
        mode="create",
        signoff_key=actor,
        approval_phase="delivery",
        fresh_context=True,
        independent=True,
        integrity_checks=integrity_checks(),
        evidence={"observed": "passed", "artifact_or_test_id": f"test:{actor}"},
    )
    results.put(
        {
            "actor": actor,
            "status": response.get("status"),
            "enter": window.get("enter"),
            "write": window.get("write"),
        }
    )


class PublicTypedEventProcessRaceTests(unittest.TestCase):
    """Wave 1tomw (AC-3): real two-process serialization of the public
    create-mode typed-event transaction, with a known-bad no-lock control."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def _race(self, slug, disable_lock):
        import multiprocessing

        created = self.srv.wf_create_wave_response(self.root, slug, mode="create")
        self.assertEqual(created["status"], "ok", created)
        wave_id = created["data"]["wave_id"]
        wave_md = self.root / created["data"]["path"]
        ctx = multiprocessing.get_context("spawn")
        barrier = ctx.Barrier(2)
        results = ctx.Queue()
        processes = [
            ctx.Process(
                target=_typed_event_race_worker,
                args=(
                    str(SCRIPTS_ROOT),
                    str(self.root),
                    wave_id,
                    actor,
                    barrier,
                    disable_lock,
                    results,
                ),
            )
            for actor in ("qa-reviewer", "security-reviewer")
        ]
        for process in processes:
            process.start()
        for process in processes:
            process.join(30)
            self.assertEqual(process.exitcode, 0)
        outcomes = [results.get(timeout=5) for _ in range(2)]
        records, errors = self.srv.read_review_event_ledger(wave_md)
        return outcomes, records, errors

    @staticmethod
    def _intervals_overlap(outcomes):
        (a, b) = outcomes
        if None in (a["enter"], a["write"], b["enter"], b["write"]):
            return False
        return not (a["write"] <= b["enter"] or b["write"] <= a["enter"])

    def test_two_process_append_serializes_and_keeps_both_bundles_exactly_once(self):
        outcomes, records, errors = self._race("typed-race-real-lock", False)
        self.assertEqual([o["status"] for o in outcomes], ["ok", "ok"])
        self.assertFalse(errors)
        # Both bundles landed exactly once, with distinct identities.
        self.assertEqual(len(records), 2)
        identities = {
            json.dumps(record.get("event_identity"), sort_keys=True)
            for record in records
        }
        self.assertEqual(len(identities), 2)
        actors = sorted(
            record.get("verification_context", {}).get("actor")
            for record in records
        )
        self.assertEqual(actors, ["qa-reviewer", "security-reviewer"])
        # DF4 repair: the overlap check is meaningful only when every window
        # was actually captured — seam drift must fail loudly, not vacuously.
        for outcome in outcomes:
            self.assertIsNotNone(outcome["enter"], outcome)
            self.assertIsNotNone(outcome["write"], outcome)
        # The interprocess handshake proves BLOCKING inside the transaction:
        # both workers left the same barrier together, each held the
        # transaction open ~0.6s, and the second's transaction window began
        # only after the first's authority commit.
        self.assertFalse(self._intervals_overlap(outcomes), outcomes)

    def test_known_bad_no_lock_mutation_is_detected_by_the_same_fixture(self):
        outcomes, records, _errors = self._race("typed-race-no-lock", True)
        # With the publication lock bypassed, both processes read the empty
        # ledger inside their overlapping windows and the second replace
        # discards the first bundle — exactly the corruption the real lock
        # prevents. The fixture's detections must fire.
        detected = self._intervals_overlap(outcomes) or len(records) != 2
        self.assertTrue(detected, (outcomes, [r.get("event_identity") for r in records]))

    def test_lock_order_is_lifecycle_then_publication_structurally(self):
        # AC-3: the outer advisory lifecycle lock wraps whole tools at the
        # registration layer; the inner blocking publication lock is only
        # ever acquired inside. No code path may inject the lifecycle lock
        # INSIDE a held publication lock.
        source = (SCRIPTS_ROOT / "server_impl.py").read_text(encoding="utf-8")
        self.assertIn("_wrap_lifecycle_mutation_lock(mcp, get_handler)", source)
        tree = ast.parse(source)
        publication_blocks = 0
        violations = []

        class _Visitor(ast.NodeVisitor):
            def visit_With(self, node):
                nonlocal publication_blocks
                takes_publication = any(
                    isinstance(item.context_expr, ast.Call)
                    and isinstance(item.context_expr.func, ast.Name)
                    and item.context_expr.func.id == "project_state_publication_lock"
                    for item in node.items
                )
                if takes_publication:
                    publication_blocks += 1
                    for inner in ast.walk(node):
                        if (
                            isinstance(inner, ast.Call)
                            and isinstance(inner.func, ast.Name)
                            and inner.func.id == "_lifecycle_mutation_lock"
                        ):
                            violations.append(ast.unparse(inner))
                self.generic_visit(node)

        _Visitor().visit(tree)
        self.assertGreaterEqual(publication_blocks, 8)
        self.assertEqual(violations, [])
        # The publication lock's own module never reaches back out to the
        # advisory lifecycle lock.
        review_source = (SCRIPTS_ROOT / "review_evidence.py").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("_lifecycle_mutation_lock", review_source)


class TypedEventNamedCrashCutTests(unittest.TestCase):
    """Wave 1tomw (AC-3): named recovery cuts around the authority commit.

    Each cut injects failure at the exact named boundary and asserts the
    surviving on-disk state, that canonical parsing still succeeds, and that
    identical exact replay converges. Atomic visibility and process-crash
    replay are claimed; fsync/power-loss durability is not.
    """

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))
        created = self.srv.wf_create_wave_response(
            self.root, "crash-cut-wave", mode="create"
        )
        self.wave_id = created["data"]["wave_id"]
        self.wave_md = self.root / created["data"]["path"]
        self.events_path = sys.modules["review_evidence"].review_event_path(
            self.wave_md
        )

    def tearDown(self):
        self.tmp.cleanup()

    def _approve(self, context):
        return self.srv.wf_review_event_response(
            self.root,
            self.wave_id,
            "approval",
            "qa-reviewer",
            context,
            mode="create",
            signoff_key="qa-reviewer",
            approval_phase="delivery",
            fresh_context=True,
            independent=True,
            integrity_checks=integrity_checks(),
            evidence={"observed": "passed", "artifact_or_test_id": "test:qa"},
        )

    def _parse_ok(self):
        records, errors = self.srv.read_review_event_ledger(self.wave_md)
        self.assertFalse(errors)
        return records

    def test_cut_before_ledger_replace_keeps_old_ledger_and_retry_appends_once(self):
        before_wave = self.wave_md.read_text(encoding="utf-8")
        with patch.object(
            self.srv,
            "_atomic_replace_bytes",
            side_effect=OSError("cut: termination before ledger os.replace"),
        ):
            response = self._approve("crash-cut-context")
        self.assertEqual(response["status"], "error")
        self.assertEqual(self.events_path.read_bytes(), b"")
        self.assertEqual(self.wave_md.read_text(encoding="utf-8"), before_wave)
        self.assertEqual(self._parse_ok(), ())

        retry = self._approve("crash-cut-context")
        self.assertEqual(retry["status"], "ok", retry)
        self.assertFalse(retry["data"]["replayed"])
        self.assertEqual(len(self._parse_ok()), 1)

    def test_cut_after_ledger_replace_before_projection_replays_without_append(self):
        before_wave = self.wave_md.read_text(encoding="utf-8")
        with patch.object(
            self.srv,
            "_atomic_replace_text",
            side_effect=OSError("cut: termination after ledger replace, before projection"),
        ):
            response = self._approve("crash-cut-context")
        self.assertEqual(response["status"], "partial")
        self.assertTrue(response["data"]["event_committed"])
        self.assertTrue(response["data"]["projection_stale"])
        committed = self.events_path.read_bytes()
        self.assertNotEqual(committed, b"")
        self.assertEqual(self.wave_md.read_text(encoding="utf-8"), before_wave)
        self.assertEqual(len(self._parse_ok()), 1)

        replay = self._approve("crash-cut-context")
        self.assertEqual(replay["status"], "ok", replay)
        self.assertTrue(replay["data"]["replayed"])
        self.assertEqual(self.events_path.read_bytes(), committed)
        self.assertNotEqual(self.wave_md.read_text(encoding="utf-8"), before_wave)
        self.assertEqual(len(self._parse_ok()), 1)


def _true_termination_crash_cut_worker(scripts_root, root, wave_id, cut):
    """Wave 1to78 (AC-6): child process for the true-termination crash cuts.

    Runs the REAL public create-mode typed append (``wf_review_event_response``)
    with the atomic-replace seam wrapped so the process dies via ``os._exit(1)``
    at the named boundary: no raised exception, no ``finally`` unwinding, no
    interpreter shutdown hooks; genuine termination mid-transaction, holding
    the publication lock (the OS releases it with the process).

    ``cut`` values:

    - ``before_ledger_replace``: die before the ledger's atomic os.replace.
    - ``after_ledger_before_projection``: die after the ledger authority
      commit, before the projection rebuild.
    - ``torn_write_control``: executed known-bad; instead of the atomic
      replace, tear half a JSON line directly into the ledger path and die,
      proving the parent's canonical-parseability oracle detects a corrupted
      survivor (the oracle can fail; it is not vacuous).

    Exit code 1 signals the cut fired; reaching the end (no cut taken) exits
    0, so seam drift (a renamed purpose label or replaced seam) fails the
    parent's exit-code assertion loudly instead of silently testing nothing.
    """
    import os as _os
    import sys as _sys
    from pathlib import Path as _Path

    _sys.path.insert(0, scripts_root)
    import server_impl as srv

    real_replace = srv._atomic_replace_bytes

    def cut_replace(path, payload, purpose):
        if purpose != "review-events":
            return real_replace(path, payload, purpose)
        if cut == "torn_write_control":
            with open(path, "ab") as handle:
                handle.write(b'{"record_type": "review_run", "review_')
                handle.flush()
                _os.fsync(handle.fileno())
            _os._exit(1)
        if cut == "before_ledger_replace":
            _os._exit(1)
        real_replace(path, payload, purpose)
        if cut == "after_ledger_before_projection":
            _os._exit(1)
        return None

    srv._atomic_replace_bytes = cut_replace
    srv.wf_review_event_response(
        _Path(root),
        wave_id,
        "run",
        "wave-council",
        "true-kill-context",
        mode="create",
        run_kind="initial_delivery",
    )
    _os._exit(0)


class TrueTerminationCrashCutTests(unittest.TestCase):
    """Wave 1to78 (AC-6): the named crash cuts as REAL process terminations.

    The exception-injection cuts above stay as fast equivalents; these
    variants kill a spawned child (wavefoundry venv python via the spawn
    context, the 1tomw race-worker pattern) with ``os._exit`` at each named
    boundary and assert from the parent: the surviving on-disk state matches
    the cut contract, the surviving ledger parses canonically, and identical
    exact replay converges (clean append before commit; replayed-no-append
    after commit), the same oracle as the injection cuts.
    """

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.srv = type(self).srv
        self.tmp = tempfile.TemporaryDirectory()
        self.root = _make_repo(Path(self.tmp.name))
        created = self.srv.wf_create_wave_response(
            self.root, "true-kill-wave", mode="create"
        )
        self.wave_id = created["data"]["wave_id"]
        self.wave_md = self.root / created["data"]["path"]
        self.events_path = self.wave_md.parent / "events.jsonl"

    def tearDown(self):
        self.tmp.cleanup()

    def _spawn_cut(self, cut):
        import multiprocessing

        ctx = multiprocessing.get_context("spawn")
        process = ctx.Process(
            target=_true_termination_crash_cut_worker,
            args=(str(SCRIPTS_ROOT), str(self.root), self.wave_id, cut),
        )
        process.start()
        process.join(60)
        self.assertIsNotNone(process.exitcode, "child did not terminate")
        self.assertEqual(process.exitcode, 1, "named cut did not fire in the child")

    def _replay_event(self):
        # Byte-identical semantic event to the one the child was killed
        # running (exact replay per the established convergence semantics).
        return self.srv.wf_review_event_response(
            self.root,
            self.wave_id,
            "run",
            "wave-council",
            "true-kill-context",
            mode="create",
            run_kind="initial_delivery",
        )

    def _no_temp_residue(self):
        leftovers = [
            path.name
            for path in self.wave_md.parent.iterdir()
            if path.name.endswith(".tmp")
        ]
        self.assertEqual(leftovers, [])

    def test_child_killed_before_ledger_replace_leaves_state_untouched(self):
        before_wave = self.wave_md.read_text(encoding="utf-8")
        self._spawn_cut("before_ledger_replace")
        # Cut contract: ledger unchanged, no partial write, projection intact.
        self.assertEqual(self.events_path.read_bytes(), b"")
        self.assertEqual(self.wave_md.read_text(encoding="utf-8"), before_wave)
        self._no_temp_residue()
        # Canonical parseability of the surviving (empty) ledger.
        records, errors = self.srv.read_review_event_ledger(self.wave_md)
        self.assertFalse(errors)
        self.assertEqual(records, ())
        # Exact replay converges as a CLEAN APPEND: nothing was committed.
        retry = self._replay_event()
        self.assertEqual(retry["status"], "ok", retry)
        self.assertFalse(retry["data"]["replayed"])
        records, errors = self.srv.read_review_event_ledger(self.wave_md)
        self.assertFalse(errors)
        self.assertEqual(len(records), 1)

    def test_child_killed_after_ledger_replace_before_projection(self):
        before_wave = self.wave_md.read_text(encoding="utf-8")
        self._spawn_cut("after_ledger_before_projection")
        # Cut contract: ledger updated canonically, projection stale.
        committed = self.events_path.read_bytes()
        self.assertNotEqual(committed, b"")
        self.assertEqual(self.wave_md.read_text(encoding="utf-8"), before_wave)
        self._no_temp_residue()
        records, errors = self.srv.read_review_event_ledger(self.wave_md)
        self.assertFalse(errors)
        self.assertEqual(len(records), 1)
        self.assertEqual(
            committed, self.srv.canonical_review_events_bytes(records)
        )
        # Exact replay converges WITHOUT another append: it repairs only the
        # projection (same oracle as the injection cut above).
        real_replace = self.srv._atomic_replace_text
        with patch.object(
            self.srv, "_atomic_replace_text", wraps=real_replace
        ) as replay_replace:
            replay = self._replay_event()
        self.assertEqual(replay["status"], "ok", replay)
        self.assertTrue(replay["data"]["replayed"])
        self.assertEqual(self.events_path.read_bytes(), committed)
        replay_replace.assert_called_once()
        self.assertEqual(
            self.wave_md.read_text(encoding="utf-8"),
            replay_replace.call_args.args[1],
        )
        # Run bookkeeping lives only in the ledger; the current-state-only
        # projection is legitimately byte-identical after this repair.
        self.assertEqual(self.wave_md.read_text(encoding="utf-8"), before_wave)
        records, errors = self.srv.read_review_event_ledger(self.wave_md)
        self.assertFalse(errors)
        self.assertEqual(len(records), 1)

    def test_torn_write_control_is_detected_by_the_parseability_oracle(self):
        # Executed known-bad (AC-6): a child that dies after tearing half a
        # JSON line into the ledger (the corruption the atomic-replace
        # pattern exists to prevent) is caught by the SAME canonical-parse
        # oracle the real cuts assert with. This proves the oracle is
        # sensitive: were the seam not atomic, the cut tests would go red.
        self._spawn_cut("torn_write_control")
        records, errors = self.srv.read_review_event_ledger(self.wave_md)
        self.assertTrue(errors)


class SharedDeliveryEvaluatorContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def test_shared_and_closure_only_registries_are_exact(self):
        self.assertEqual(
            self.srv.SHARED_DELIVERY_DIAGNOSTIC_CODES,
            (
                "review_evidence_invalid",
                "missing_executable_approval_evidence",
                "docs_lint_error",
                "missing_operator_signoff",
                "missing_required_lane",
                "missing_wave_council_signoff",
                "review_policy_receipt_stale",
                "review_policy_reprepare_required",
            ),
        )
        self.assertEqual(len(self.srv.CLOSURE_ONLY_DIAGNOSTIC_CODES), 11)
        self.assertTrue(
            set(self.srv.SHARED_DELIVERY_DIAGNOSTIC_CODES).isdisjoint(
                self.srv.CLOSURE_ONLY_DIAGNOSTIC_CODES
            )
        )

    def test_review_and_close_both_consume_the_single_evaluator(self):
        review_source = inspect.getsource(self.srv.wf_review_wave_response)
        close_source = inspect.getsource(self.srv.wf_close_wave_response)
        self.assertEqual(review_source.count("_evaluate_shared_delivery_state("), 0)
        self.assertEqual(close_source.count("_evaluate_shared_delivery_state("), 0)
        gates = self.srv.lifecycle_gates
        unit_source = inspect.getsource(gates.shared_delivery_gate)
        self.assertEqual(unit_source.count("_evaluate_shared_delivery_state("), 1)
        self.assertIn(gates.shared_delivery_gate, gates.REVIEW_GATES)
        self.assertIn(gates.shared_delivery_gate, gates.CLOSE_SHARED_GATES)


if __name__ == "__main__":
    unittest.main()
