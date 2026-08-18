#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import review_policy
import review_policy_reconcile
import review_policy_upgrade
import review_evidence
import render_agent_surfaces
import lifecycle_lock
import index_state_store
import gardener_metadata
import publication_control
from wave_lint_lib.core_validators import check_review_policy_carriers


class ReviewPolicyReconcilerTests(unittest.TestCase):
    def _root(self, tmp: str) -> Path:
        root = Path(tmp)
        for relative, replacements in review_policy_reconcile.KNOWN_SECTION_REPLACEMENTS.items():
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            body = replacements[0][0] if replacements else "current carrier\n"
            path.write_text("operator prefix\n" + body + "operator suffix\n", encoding="utf-8")
        return root

    def test_registry_and_reconciler_share_exact_carrier_scope(self):
        registry = {
            carrier.destination
            for carrier in review_policy.REVIEW_POLICY_CARRIER_REGISTRY
            if carrier.owner == "lifecycle_reconciler"
        }
        self.assertEqual(registry, set(review_policy.LIFECYCLE_RECONCILER_CARRIERS))

    def test_direct_doc_registry_names_real_validation_only_carriers(self):
        repo_root = SCRIPTS.parents[2]
        direct_docs = tuple(
            carrier
            for carrier in review_policy.REVIEW_POLICY_CARRIER_REGISTRY
            if carrier.owner == "direct_docs"
        )
        self.assertTrue(direct_docs)
        self.assertIn(
            "docs/references/dashboard-adapter-model.md",
            {carrier.destination for carrier in direct_docs},
        )
        for carrier in direct_docs:
            with self.subTest(destination=carrier.destination):
                self.assertTrue((repo_root / carrier.destination).exists())
                self.assertTrue(carrier.conditional_existing)
                self.assertFalse(carrier.create_if_missing)

    def test_direct_doc_policy_baselines_have_marker_owned_renderer_companions(self):
        direct_destinations = {
            carrier.destination
            for carrier in review_policy.REVIEW_POLICY_CARRIER_REGISTRY
            if carrier.owner == "direct_docs" and carrier.destination != "docs/agents"
        }
        renderer_destinations = {
            carrier.destination
            for carrier in review_policy.REVIEW_POLICY_CARRIER_REGISTRY
            if carrier.owner == "renderer"
            and carrier.destination in review_policy.REVIEW_POLICY_SURFACE_BLOCKS
        }
        self.assertTrue(direct_destinations)
        self.assertTrue(direct_destinations.issubset(renderer_destinations))

    def test_production_validator_consumes_direct_doc_obligations(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            prepare = root / "docs/prompts/prepare-wave.prompt.md"
            prepare.parent.mkdir(parents=True)
            prepare.write_text(
                review_policy.REVIEW_POLICY_SURFACE_MARKER_BEGIN
                + "\nPrepare Wave; review policy receipt; re-Prepare; delivery_mode\n"
                + review_policy.REVIEW_POLICY_SURFACE_MARKER_END
                + "\n",
                encoding="utf-8",
            )
            build_doc = root / "docs/contributing/build-and-verification.md"
            build_doc.parent.mkdir(parents=True)
            build_doc.write_text("review policy bridge\n", encoding="utf-8")
            self.assertEqual(check_review_policy_carriers(root), [])
            build_doc.write_text("bridge only\n", encoding="utf-8")
            self.assertIn(
                "docs/contributing/build-and-verification.md: registered "
                "review-policy obligation is missing: policy",
                check_review_policy_carriers(root),
            )

    def test_every_registered_obligation_has_a_production_anchor(self):
        obligations = {
            obligation
            for carrier in review_policy.REVIEW_POLICY_CARRIER_REGISTRY
            for obligation in carrier.obligations
        }
        self.assertEqual(
            obligations, set(review_policy.REVIEW_POLICY_OBLIGATION_ANCHORS)
        )

    def test_native_publication_producers_are_registry_backed(self):
        self.assertEqual(
            set(publication_control.registered_native_publication_producers()),
            {"retrieval_context_telemetry", "background_index_refresh"},
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            checkpoint = root / publication_control.UPGRADE_CHECKPOINT_REL
            checkpoint.parent.mkdir(parents=True)
            checkpoint.write_text(
                json.dumps({"current_phase": "surface_rendering"}),
                encoding="utf-8",
            )
            for producer in publication_control.registered_native_publication_producers():
                self.assertIn(
                    "upgrade_in_progress",
                    publication_control.native_publication_block_reason(root, producer),
                )

    def test_exact_legacy_sections_replace_idempotently_and_preserve_surrounding(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._root(tmp)
            changed = review_policy_reconcile.reconcile_lifecycle_sections(root)
            self.assertEqual(
                set(changed),
                set(review_policy_reconcile.KNOWN_SECTION_REPLACEMENTS),
            )
            for relative in changed:
                text = (root / relative).read_text(encoding="utf-8")
                self.assertTrue(text.startswith("operator prefix\n"))
                self.assertIn("operator suffix\n", text)
                self.assertFalse(any(token in text.lower() for token in review_policy.RETIRED_LIFECYCLE_TOKENS))
            snapshot = {p: (root / p).read_bytes() for p in review_policy.LIFECYCLE_RECONCILER_CARRIERS}
            self.assertEqual(review_policy_reconcile.reconcile_lifecycle_sections(root), ())
            self.assertEqual(snapshot, {p: (root / p).read_bytes() for p in snapshot})

    def test_one_ambiguous_carrier_prevents_every_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._root(tmp)
            path = root / "docs/prompts/implement-wave.prompt.md"
            path.write_text("unrecognized pre-implementation review gate prose\n", encoding="utf-8")
            before = {p: (root / p).read_bytes() for p in review_policy.LIFECYCLE_RECONCILER_CARRIERS}
            with self.assertRaisesRegex(ValueError, "not an exact registered baseline"):
                review_policy_reconcile.reconcile_lifecycle_sections(root)
            self.assertEqual(before, {p: (root / p).read_bytes() for p in before})

    def test_ambiguous_carrier_reports_complete_retired_token_worklist_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._root(tmp)
            path = root / "docs/prompts/implement-wave.prompt.md"
            path.write_text(
                "project heading\npre-implementation review gate\n"
                "project prose\nreviewer loop\n",
                encoding="utf-8",
            )
            before = {
                relative: (root / relative).read_bytes()
                for relative in review_policy.LIFECYCLE_RECONCILER_CARRIERS
            }
            with self.assertRaises(ValueError) as caught:
                review_policy_reconcile.reconcile_lifecycle_sections(root)
            message = str(caught.exception)
            self.assertIn("'pre-implementation review gate' at line(s) 2", message)
            self.assertIn("'reviewer loop' at line(s) 4", message)
            self.assertIn("registered replacement preview(s)", message)
            self.assertIn("--- docs/prompts/implement-wave.prompt.md:registered-legacy-", message)
            self.assertIn("+++ docs/prompts/implement-wave.prompt.md:current-", message)
            self.assertIn("edit the listed project-authored prose", message)
            self.assertIn("retry the same upgrade command", message)
            self.assertEqual(
                before,
                {
                    relative: (root / relative).read_bytes()
                    for relative in review_policy.LIFECYCLE_RECONCILER_CARRIERS
                },
            )

    def test_live_markdown_outside_registered_carriers_is_reported_not_rewritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._root(tmp)
            live = root / "docs/agents/wave-council.md"
            live.parent.mkdir(parents=True, exist_ok=True)
            live.write_text(
                "# Council\n\nRun the pre-implementation review gate.\n",
                encoding="utf-8",
            )
            historical = root / "docs/waves/1old closed/wave.md"
            historical.parent.mkdir(parents=True)
            historical.write_text(
                "# Historical\n\nRun the pre-implementation review gate.\n",
                encoding="utf-8",
            )
            # A second project-authored carrier, so this test still proves more
            # than one file is reported. It replaces `.wavefoundry/README.md` in
            # that role: that file is shipped by the pack, so reporting it told
            # operators to hand-rewrite a file the same upgrade replaces. It now
            # sits in the excluded group below.
            second_live = root / "docs/contributing/review-notes.md"
            second_live.parent.mkdir(parents=True, exist_ok=True)
            second_live.write_text(
                "# Notes\n\nRun the reviewer loop.\n", encoding="utf-8",
            )
            generated_paths = (
                root / ".wavefoundry/README.md",
                root / ".wavefoundry/CHANGELOG.md",
                root / ".wavefoundry/framework/README.md",
                root / ".wavefoundry/index/README.md",
                root / ".wavefoundry/upgrade-assets/README.md",
                root / ".wavefoundry/framework.rollback-bridge-p2/README.md",
            )
            for generated in generated_paths:
                generated.parent.mkdir(parents=True, exist_ok=True)
                generated.write_text(
                    "# Generated history\n\nRun the reviewer loop.\n",
                    encoding="utf-8",
                )
            before = {
                live: live.read_bytes(),
                second_live: second_live.read_bytes(),
            }
            with self.assertRaises(ValueError) as caught:
                review_policy_reconcile.plan_reconciliation(root)
            message = str(caught.exception)
            self.assertIn("docs/agents/wave-council.md", message)
            self.assertIn("docs/contributing/review-notes.md", message)
            self.assertIn("outside a registered carrier", message)
            self.assertNotIn("docs/waves/1old closed/wave.md", message)
            for generated in generated_paths:
                self.assertNotIn(generated.relative_to(root).as_posix(), message)
            self.assertEqual(
                {path: path.read_bytes() for path in before},
                before,
            )

    def test_symlink_carrier_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._root(tmp)
            path = root / "docs/prompts/implement-wave.prompt.md"
            path.unlink()
            try:
                path.symlink_to(Path(tmp).parent / "outside.md")
            except (OSError, NotImplementedError):
                self.skipTest("symlinks unavailable")
            with self.assertRaisesRegex(ValueError, "may not traverse symlink"):
                review_policy_reconcile.plan_reconciliation(root)

    def test_real_v114_carrier_family_reconciles_and_retries_byte_stably(self):
        probe = subprocess.run(
            ["git", "rev-parse", "--verify", "v1.14.0"],
            cwd=str(SCRIPTS.parents[2]),
            check=False,
            capture_output=True,
        )
        if probe.returncode != 0:
            self.skipTest("v1.14.0 tag unavailable in this source distribution")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for relative in review_policy.LIFECYCLE_RECONCILER_CARRIERS:
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(
                    subprocess.check_output(
                        ["git", "show", f"v1.14.0:{relative}"],
                        cwd=str(SCRIPTS.parents[2]),
                    )
                )
            self.assertEqual(
                set(review_policy_reconcile.reconcile_lifecycle_sections(root)),
                set(review_policy.LIFECYCLE_RECONCILER_CARRIERS),
            )
            snapshot = {
                relative: (root / relative).read_bytes()
                for relative in review_policy.LIFECYCLE_RECONCILER_CARRIERS
            }
            self.assertEqual(review_policy_reconcile.reconcile_lifecycle_sections(root), ())
            self.assertEqual(
                snapshot,
                {relative: (root / relative).read_bytes() for relative in snapshot},
            )

    def test_shipped_v1153_review_prompt_baseline_reconciles_and_retries_byte_stably(self):
        """Pin the exact 1.15.3-to-1.15.4 review-prompt transition."""

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "docs/prompts/review-wave.prompt.md"
            path.parent.mkdir(parents=True, exist_ok=True)
            shipped_v1153 = (
                "Blocking findings open a recorded repair cycle; the implementer repairs the affected "
                "boundary and each blocking lane independently reverifies it before delivery approval is "
                "restored."
            )
            self.assertEqual(
                review_policy_reconcile._SHIPPED_REPAIR_CYCLE_SENTENCE,
                shipped_v1153,
            )
            path.write_text(
                "operator prefix\n"
                + shipped_v1153
                + "\noperator suffix\n",
                encoding="utf-8",
            )

            self.assertEqual(
                review_policy_reconcile.reconcile_lifecycle_sections(root),
                ("docs/prompts/review-wave.prompt.md",),
            )
            current = path.read_bytes()
            self.assertIn(
                review_policy_reconcile._REPAIR_CYCLE_STOP_CONDITION,
                current.decode("utf-8"),
            )
            self.assertEqual(review_policy_reconcile.reconcile_lifecycle_sections(root), ())
            self.assertEqual(path.read_bytes(), current)

    def test_real_v114_carriers_render_policy_and_pass_production_validator(self):
        repo_root = SCRIPTS.parents[2]
        probe = subprocess.run(
            ["git", "rev-parse", "--verify", "v1.14.0"],
            cwd=str(repo_root),
            check=False,
            capture_output=True,
        )
        if probe.returncode != 0:
            self.skipTest("v1.14.0 tag unavailable in this source distribution")
        direct_files = {
            carrier.destination
            for carrier in review_policy.REVIEW_POLICY_CARRIER_REGISTRY
            if carrier.owner == "direct_docs" and carrier.destination != "docs/agents"
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for relative in (
                set(review_policy.LIFECYCLE_RECONCILER_CARRIERS) | direct_files
            ):
                exists = subprocess.run(
                    ["git", "cat-file", "-e", f"v1.14.0:{relative}"],
                    cwd=str(repo_root),
                    check=False,
                    capture_output=True,
                )
                if exists.returncode != 0:
                    continue
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(
                    subprocess.check_output(
                        ["git", "show", f"v1.14.0:{relative}"],
                        cwd=str(repo_root),
                    )
                )

            review_policy_reconcile.reconcile_lifecycle_sections(root)
            render_agent_surfaces.render_agent_surfaces(root)
            self.assertEqual(check_review_policy_carriers(root), [])
            snapshot = {
                path.relative_to(root).as_posix(): path.read_bytes()
                for path in root.rglob("*")
                if path.is_file()
            }
            self.assertEqual(render_agent_surfaces.render_agent_surfaces(root), [])
            self.assertEqual(
                snapshot,
                {
                    path.relative_to(root).as_posix(): path.read_bytes()
                    for path in root.rglob("*")
                    if path.is_file()
                },
            )


class ShippedMarkdownIsNotProjectDriftTests(unittest.TestCase):
    """The upgrade must not demand a manual rewrite of a file it ships.

    Field report: the preflight halted on `.wavefoundry/README.md` carrying a
    retired token, telling the operator to rewrite it by hand. That file is in
    the pack. The cause is a prefix gap, not a per-file oversight: the
    exclusions covered `.wavefoundry/framework/`, `/index/`, and
    `/upgrade-assets/` but nothing at the `.wavefoundry/` root, where the pack
    ships exactly README.md and CHANGELOG.md. The changelog exposure is the
    worse half and was never reported, because a release history must name
    retired concepts to do its job.
    """

    RETIRED = "reviewer loop"

    def _scan(self, files: dict[str, str]) -> tuple[str, ...]:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        for rel, body in files.items():
            p = root / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(body, encoding="utf-8")
        return review_policy_reconcile._live_markdown_retired_errors(root)

    def _flagged(self, errors, rel):
        return any(rel in e for e in errors)

    def test_shipped_root_markdown_is_not_reported_as_project_drift(self):
        errors = self._scan({
            ".wavefoundry/README.md": f"# R\n\nThe {self.RETIRED} is retired.\n",
            ".wavefoundry/CHANGELOG.md": f"# C\n\nRemoved the {self.RETIRED}.\n",
        })
        self.assertFalse(self._flagged(errors, ".wavefoundry/README.md"), errors)
        self.assertFalse(self._flagged(errors, ".wavefoundry/CHANGELOG.md"), errors)

    def test_project_authored_prose_is_still_reported(self):
        """The control. A blanket silence would pass the test above and this one fails."""
        errors = self._scan({
            "docs/contributing/notes.md": f"# N\n\nThe {self.RETIRED} still runs.\n",
        })
        self.assertTrue(self._flagged(errors, "docs/contributing/notes.md"), errors)

    def test_the_exclusion_is_a_prefix_rule_not_a_per_file_list(self):
        """A future shipped file at that level inherits the exclusion."""
        errors = self._scan({
            ".wavefoundry/NOTICE.md": f"# N\n\nThe {self.RETIRED} is gone.\n",
        })
        self.assertFalse(self._flagged(errors, ".wavefoundry/NOTICE.md"), errors)


class EmptyWaveReviewPolicyMigrationTests(unittest.TestCase):
    """An empty mapping means what an absent key means.

    Field report: a 1.11.0 repository carrying `"wave_review": {}` could not
    upgrade at all. `migrate_wave_review_policy` defaulted only on `None`, so
    the empty mapping fell through to the validator and hard-failed the
    preflight before any mutation. Migration is the one component whose whole
    job is normalizing old shapes.
    """

    FRESH = {"enabled": True, "delivery_mode": review_policy.FRESH_INSTALL_DELIVERY_MODE}

    def test_an_empty_mapping_migrates_like_an_absent_key(self):
        self.assertEqual(review_policy.migrate_wave_review_policy({}), self.FRESH)
        self.assertEqual(review_policy.migrate_wave_review_policy(None), self.FRESH)

    def test_widening_the_unset_case_does_not_weaken_rejection(self):
        """The control. Without it, `return FRESH` unconditionally would pass."""
        for bad in ("enabled", 5, [], {"enabled": "yes"}, {"enabled": None}):
            with self.subTest(value=bad):
                with self.assertRaises(ValueError):
                    review_policy.migrate_wave_review_policy(bad)

    def test_a_partial_mapping_still_migrates_on_the_existing_path(self):
        """`allow_legacy_missing_mode` already covered this; the gap was only `{}`."""
        self.assertEqual(
            review_policy.migrate_wave_review_policy({"enabled": True}), self.FRESH
        )
        self.assertEqual(
            review_policy.migrate_wave_review_policy({"enabled": False})["enabled"], False
        )


class ReviewPolicyUpgradeTests(unittest.TestCase):
    def test_evaluator_version_seven_is_the_shipped_transition_boundary(self):
        """Deliberate tripwire: update it consciously on every evaluator bump.

        v4 to v5 (wave 1umst): legacy extension triggers are path-shaped rather
        than raw substrings, and receipt semantics exclude rotating council
        seats. The pin moves with the constant, it is never deleted, and
        `test_server_tools.py` carries the paired public transition test.

        v5 to v6 (wave 1uo1x): lane semantics and digest boundary both moved.
        Adoption of the declared-target contract is decided per DOCUMENT rather
        than per wave, declaration requires a pure-path bullet or the explicit
        `**Review targets (repo-relative paths):**` block, and the status
        normalizer bounds its carrier by a known-key allowlist. One bump
        carries both changes.

        v6 to v7 (wave 1uprb): the canonicalizer gained carrier normalization
        (BOM, line endings, trailing newline, and trailing whitespace outside a
        fence, preserved inside one), a `## Session Handoff` exclusion
        conditional on an exact match against the shipped template sentence,
        an order-invariant `changes` payload sorted by `change_id`, and
        whitespace-independent legacy lane matching. Bumped for the same reason
        v2 to v3 was: without it the permanent ledger cannot tell a plan edit
        apart from a canonicalization change. The re-digest happens either way,
        so the bump only decides whether the history can explain it.
        """

        self.assertEqual(review_policy.REVIEW_POLICY_EVALUATOR_VERSION, 7)

    def test_upgrade_policy_guidance_matches_legacy_migration(self):
        self.assertIn("delivery_mode=targeted", review_policy.UPGRADE_POLICY_BLOCK)
        self.assertIn("selected delivery mode", review_policy.UPGRADE_POLICY_BLOCK)
        self.assertNotIn("delivery_mode=universal", review_policy.UPGRADE_POLICY_BLOCK)
        self.assertIn("**Review memories**", review_policy.UPGRADE_POLICY_BLOCK)
        self.assertIn("curation_required=true", review_policy.UPGRADE_POLICY_BLOCK)
        self.assertIn("consolidation candidates", review_policy.UPGRADE_POLICY_BLOCK)
        self.assertIn("`AGENTS.md`", review_policy.UPGRADE_POLICY_BLOCK)
        self.assertIn("`docs/prompts/index.md`", review_policy.UPGRADE_POLICY_BLOCK)
        self.assertIn(
            "`docs/prompts/prompt-surface-manifest.json`",
            review_policy.UPGRADE_POLICY_BLOCK,
        )
        self.assertIn("never auto-curates or\npurges memory", review_policy.UPGRADE_POLICY_BLOCK)
        self.assertNotIn("memory_purge(", review_policy.UPGRADE_POLICY_BLOCK)
        self.assertNotIn('memory_consolidate(mode="create"', review_policy.UPGRADE_POLICY_BLOCK)

    def _repo(self, tmp: str, *, enabled: bool) -> tuple[Path, Path, Path]:
        root = Path(tmp)
        config = root / "docs/workflow-config.json"
        config.parent.mkdir(parents=True)
        config.write_text(
            '{\n  "wave_review": {"enabled": ' + str(enabled).lower() + '}\n}\n',
            encoding="utf-8",
        )
        # Missing registered carriers are valid target shapes.
        open_md = root / "docs/waves/open-wave/wave.md"
        open_md.parent.mkdir(parents=True)
        open_md.write_text(
            "# Wave\n\nStatus: implementing\nreview-evidence-protocol: `2`\n"
            "review-evidence-source: events.jsonl\n\n## Participants\n\n"
            "- Requested review lanes: none\n- Required review lanes: none\n\n"
            "## Finding Synthesis\n\n"
            f"{review_evidence.FINDING_SYNTHESIS_MARKER_BEGIN}\n"
            f"{review_evidence.review_evidence_human_table(())}\n\n"
            f"{review_evidence.review_evidence_plain_summary(review_evidence.review_evidence_summary_line(()))}\n"
            f"{review_evidence.FINDING_SYNTHESIS_MARKER_END}\n\n"
            "## Review Evidence\n\n"
            f"{review_evidence.REVIEW_STATUS_MARKER_BEGIN}\n"
            f"{review_evidence.review_status_human_table((), ())}\n"
            f"{review_evidence.REVIEW_STATUS_MARKER_END}\n",
            encoding="utf-8",
        )
        review_evidence.review_event_path(open_md).write_bytes(b"")
        closed_md = root / "docs/waves/closed-wave/wave.md"
        closed_md.parent.mkdir(parents=True)
        closed_md.write_bytes(open_md.read_bytes().replace(b"Status: implementing", b"Status: closed"))
        review_evidence.review_event_path(closed_md).write_bytes(b"")
        return root, open_md, closed_md

    def test_legacy_policy_mapping_marks_open_waves_and_preserves_closed_bytes(self):
        for enabled, expected in ((True, "targeted"), (False, "disabled")):
            with self.subTest(enabled=enabled), tempfile.TemporaryDirectory() as tmp:
                root, open_md, closed_md = self._repo(tmp, enabled=enabled)
                closed_before = closed_md.read_bytes()
                closed_events = review_evidence.review_event_path(closed_md)
                closed_events_before = closed_events.read_bytes()
                plan = review_policy_upgrade.plan_review_policy_upgrade(root)
                result = review_policy_upgrade.apply_review_policy_upgrade(root, plan)
                self.assertEqual(result["delivery_mode"], expected)
                self.assertEqual(
                    result["waves_marked_for_reprepare"],
                    ["docs/waves/open-wave/wave.md"],
                )
                self.assertIn("review-policy-reprepare-required: true", open_md.read_text("utf-8"))
                self.assertEqual(closed_md.read_bytes(), closed_before)
                self.assertEqual(closed_events.read_bytes(), closed_events_before)
                projected = open_md.read_text("utf-8")
                self.assertIn("operator-signoff", projected)
                self.assertEqual(
                    "wave-council-delivery" in projected,
                    enabled,
                )

    def test_noop_policy_migration_leaves_readied_waves_untouched(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, open_md, _closed_md = self._repo(tmp, enabled=True)
            config = root / "docs/workflow-config.json"
            first = review_policy_upgrade.apply_review_policy_upgrade(
                root, review_policy_upgrade.plan_review_policy_upgrade(root)
            )
            self.assertEqual(
                first["waves_marked_for_reprepare"], ["docs/waves/open-wave/wave.md"]
            )
            # The operator re-readies the wave, exactly as `wf_prepare_wave(mode='ready')`
            # does; the migrated config is now canonical, so a second pack adoption is a
            # true no-op and must not invalidate that prepare state again.
            open_md.write_text(
                review_policy.set_reprepare_marker(open_md.read_text("utf-8"), False),
                encoding="utf-8",
            )
            config_before = config.read_bytes()
            wave_before = open_md.read_bytes()
            plan = review_policy_upgrade.plan_review_policy_upgrade(root)
            second = review_policy_upgrade.apply_review_policy_upgrade(root, plan)
            self.assertEqual(second["waves_marked_for_reprepare"], [])
            self.assertEqual(open_md.read_bytes(), wave_before)
            self.assertEqual(config.read_bytes(), config_before)
            self.assertEqual(plan.config_after, plan.config_before)
            self.assertEqual(plan.carriers, ())
            self.assertEqual(plan.waves, ())

    def test_carrier_only_delta_still_marks_readied_waves(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, open_md, _closed_md = self._repo(tmp, enabled=True)
            config = root / "docs/workflow-config.json"
            review_policy_upgrade.apply_review_policy_upgrade(
                root, review_policy_upgrade.plan_review_policy_upgrade(root)
            )
            # The operator re-readies the wave, exactly as the no-op test does, so the
            # migrated config is now canonical and cannot contribute a delta.
            open_md.write_text(
                review_policy.set_reprepare_marker(open_md.read_text("utf-8"), False),
                encoding="utf-8",
            )
            # Only the carrier half of the guard can see this delta: one registered legacy
            # section that reconciliation rewrites while the config stays byte-identical.
            relative = "docs/prompts/implement-wave.prompt.md"
            legacy = "Required review lanes from readiness must participate during execution."
            self.assertIn(
                legacy,
                [
                    entry[0]
                    for entry in review_policy_reconcile.KNOWN_SECTION_REPLACEMENTS[relative]
                ],
            )
            carrier = root / relative
            carrier.parent.mkdir(parents=True, exist_ok=True)
            carrier.write_text(f"# Implement wave\n\n{legacy}\n", encoding="utf-8")
            config_before = config.read_bytes()
            wave_before = open_md.read_bytes()
            plan = review_policy_upgrade.plan_review_policy_upgrade(root)
            self.assertEqual(plan.config_after, plan.config_before)
            self.assertGreaterEqual(len(plan.carriers), 1)
            result = review_policy_upgrade.apply_review_policy_upgrade(root, plan)
            self.assertEqual(
                result["waves_marked_for_reprepare"],
                ["docs/waves/open-wave/wave.md"],
            )
            self.assertNotEqual(open_md.read_bytes(), wave_before)
            self.assertIn("review-policy-reprepare-required: true", open_md.read_text("utf-8"))
            self.assertEqual(config.read_bytes(), config_before)

    def test_noop_migration_still_fails_preflight_on_an_unreadable_wave(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, _open_md, _closed_md = self._repo(tmp, enabled=True)
            review_policy_upgrade.apply_review_policy_upgrade(
                root, review_policy_upgrade.plan_review_policy_upgrade(root)
            )
            # The migrated config is now canonical, so this rerun is a true no-op:
            # the guard suppresses marking, never the validation walk.
            self.assertEqual(
                review_policy_upgrade.plan_review_policy_upgrade(root).waves, ()
            )
            broken = root / "docs/waves/broken-wave/wave.md"
            broken.parent.mkdir(parents=True)
            broken.write_bytes(b"# Wave\n\nStatus: implementing\n\xff\xfe\n")
            with self.assertRaisesRegex(ValueError, "preflight failed.*unreadable wave"):
                review_policy_upgrade.plan_review_policy_upgrade(root)

    def test_noop_migration_still_fails_preflight_on_a_ledger_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, open_md, _closed_md = self._repo(tmp, enabled=True)
            review_policy_upgrade.apply_review_policy_upgrade(
                root, review_policy_upgrade.plan_review_policy_upgrade(root)
            )
            self.assertEqual(
                review_policy_upgrade.plan_review_policy_upgrade(root).waves, ()
            )
            review_evidence.review_event_path(open_md).write_bytes(b"not json\n")
            with self.assertRaisesRegex(
                ValueError, "review-policy upgrade preflight failed"
            ):
                review_policy_upgrade.plan_review_policy_upgrade(root)

    def test_preflight_failure_leaves_config_carriers_and_waves_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, open_md, _closed_md = self._repo(tmp, enabled=True)
            bad = root / "docs/prompts/implement-wave.prompt.md"
            bad.parent.mkdir(parents=True)
            bad.write_text("unknown pre-implementation review gate\n", encoding="utf-8")
            config_before = (root / "docs/workflow-config.json").read_bytes()
            wave_before = open_md.read_bytes()
            with self.assertRaisesRegex(ValueError, "preflight failed"):
                review_policy_upgrade.plan_review_policy_upgrade(root)
            self.assertEqual((root / "docs/workflow-config.json").read_bytes(), config_before)
            self.assertEqual(open_md.read_bytes(), wave_before)


class ReviewPolicyAdoptionGateTests(unittest.TestCase):
    def test_operator_direction_sets_targeted_default(self):
        self.assertEqual(review_policy.FRESH_INSTALL_DELIVERY_MODE, "targeted")
        self.assertFalse(
            review_policy.targeted_default_adoption_allowed(
                council_reduction=0.0,
                specialist_lane_reduction=0.0,
                omitted_required_lanes=0,
            )
        )

    def test_targeted_delivery_escalates_only_for_boundary_triggers(self):
        self.assertFalse(review_policy.delivery_council_required("targeted"))
        self.assertTrue(
            review_policy.delivery_council_required(
                "targeted",
                delivered_boundary_triggers=review_policy.extract_full_council_triggers(
                    ["The feature must behave consistently on Windows, macOS, and Linux."]
                ),
            )
        )
        self.assertTrue(
            review_policy.delivery_council_required(
                "targeted",
                delivered_boundary_triggers=review_policy.extract_full_council_triggers(
                    ["This changes the release artifact distribution boundary."]
                ),
            )
        )
        self.assertTrue(
            review_policy.delivery_council_required(
                "targeted",
                current_heads=[{"permission_boundary_changed": True}],
            )
        )

    def test_both_thresholds_and_zero_omissions_are_independently_load_bearing(self):
        cases = (
            (0.19, 0.15, 0, False),
            (0.20, 0.14, 0, False),
            (0.20, 0.15, 1, False),
            (0.20, 0.15, 0, True),
        )
        for council, lanes, omissions, expected in cases:
            with self.subTest(council=council, lanes=lanes, omissions=omissions):
                self.assertEqual(
                    review_policy.targeted_default_adoption_allowed(
                        council_reduction=council,
                        specialist_lane_reduction=lanes,
                        omitted_required_lanes=omissions,
                    ),
                    expected,
                )

    def test_explicit_operator_decision_is_the_only_measurement_override(self):
        self.assertTrue(
            review_policy.targeted_default_adoption_allowed(
                council_reduction=0.0,
                specialist_lane_reduction=0.0,
                omitted_required_lanes=9,
                explicit_operator_decision=True,
            )
        )


class LockAndPublicationPolicyTests(unittest.TestCase):
    def test_dual_lock_order_and_reverse_release(self):
        calls = []

        class FakeLock:
            def __init__(self, path, **kwargs):
                self.path = Path(path)
                calls.append(("init", self.path.name, kwargs))

            def acquire(self):
                calls.append(("acquire", self.path.name))

            def write_metadata(self, _value):
                calls.append(("metadata", self.path.name))

            def release(self):
                calls.append(("release", self.path.name))

        with tempfile.TemporaryDirectory() as tmp, patch.object(
            lifecycle_lock, "RuntimeFileLock", FakeLock
        ):
            with lifecycle_lock.lifecycle_publication_transaction(Path(tmp)):
                calls.append(("body",))
        self.assertEqual(
            [row[:2] for row in calls if row[0] in {"acquire", "release"}],
            [
                ("acquire", "lifecycle-mutation.lock"),
                ("acquire", "review-evidence-adoptions.lock"),
                ("release", "review-evidence-adoptions.lock"),
                ("release", "lifecycle-mutation.lock"),
            ],
        )

    def test_strict_lock_failure_never_yields_unlocked(self):
        class BrokenLock:
            def __init__(self, *_args, **_kwargs):
                self.path = Path("broken")

            def acquire(self):
                raise lifecycle_lock.RuntimeLockError("no backend")

        entered = False
        with tempfile.TemporaryDirectory() as tmp, patch.object(
            lifecycle_lock, "RuntimeFileLock", BrokenLock
        ):
            with self.assertRaises(lifecycle_lock.LifecycleLockUnavailable):
                with lifecycle_lock.lifecycle_mutation_lock(Path(tmp), strict=True):
                    entered = True
        self.assertFalse(entered)

    def test_checkpoint_guard_is_fail_closed_and_allows_only_memory_recovery(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            checkpoint = root / publication_control.UPGRADE_CHECKPOINT_REL
            checkpoint.parent.mkdir(parents=True)
            checkpoint.write_text("{", encoding="utf-8")
            self.assertIn(
                "upgrade_in_progress",
                publication_control.publication_block_reason(root, "wf_review_event"),
            )
            checkpoint.write_text(
                json.dumps({"current_phase": "awaiting_memory_validation"}),
                encoding="utf-8",
            )
            self.assertIsNone(
                publication_control.publication_block_reason(root, "memory_validate")
            )
            self.assertIsNone(
                publication_control.publication_block_reason(root, "memory_backfill")
            )
            self.assertIn(
                "upgrade_in_progress",
                publication_control.publication_block_reason(root, "wf_prepare_wave"),
            )
            checkpoint.write_text(
                json.dumps({"current_phase": "index_update"}), encoding="utf-8"
            )
            self.assertIn(
                "upgrade_in_progress",
                publication_control.publication_block_reason(root, "memory_validate"),
            )

    def test_zero_pending_refusal_names_the_complete_ordered_recovery(self):
        """1u44n (AC-2): with historical memory complete (0 pending) the
        refusal states the ordered recovery (resume_after_memory, then
        cleanup, then index_build), names index_health as the confirming
        check, and states that resume_after_memory exits zero while the
        lifecycle is still non-terminal."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            checkpoint = root / publication_control.UPGRADE_CHECKPOINT_REL
            checkpoint.parent.mkdir(parents=True)
            checkpoint.write_text(
                json.dumps(
                    {
                        "current_phase": "awaiting_memory_validation",
                        "memory_backfill_pending": 0,
                    }
                ),
                encoding="utf-8",
            )
            reason = publication_control.publication_checkpoint_reason(
                root, "index_build"
            )
            self.assertTrue(reason.startswith("upgrade_in_progress"))
            resume = reason.index("resume_after_memory")
            cleanup = reason.index("cleanup")
            build = reason.index("index_build; confirm")
            self.assertLess(resume, cleanup)
            self.assertLess(cleanup, build)
            self.assertIn("index_health", reason)
            self.assertIn("exits zero", reason)
            self.assertNotIn("memory_validate", reason)

    def test_pending_or_unknown_refusal_routes_to_validation_not_skip(self):
        """1u44n (AC-2): non-zero, absent, or unreadable pending is a genuine
        pause (fail safe) — route to memory_backfill / memory_validate and
        never emit the skip-validation ordered recovery."""
        cases = (
            {"current_phase": "awaiting_memory_validation", "memory_backfill_pending": 3},
            {"current_phase": "awaiting_memory_validation"},
            {"current_phase": "awaiting_memory_validation", "memory_backfill_pending": "junk"},
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            checkpoint = root / publication_control.UPGRADE_CHECKPOINT_REL
            checkpoint.parent.mkdir(parents=True)
            for payload in cases:
                with self.subTest(payload=payload):
                    checkpoint.write_text(json.dumps(payload), encoding="utf-8")
                    reason = publication_control.publication_checkpoint_reason(
                        root, "index_build"
                    )
                    self.assertIn("memory_backfill", reason)
                    self.assertIn("memory_validate", reason)
                    self.assertNotIn("index_health", reason)
                    self.assertNotIn("cleanup", reason)
            # Unreadable checkpoint file: read_upgrade_checkpoint returns {}
            # (pending absent) — same genuine-pause branch.
            checkpoint.write_text("{", encoding="utf-8")
            reason = publication_control.publication_checkpoint_reason(
                root, "index_build"
            )
            self.assertIn("memory_validate", reason)
            self.assertNotIn("index_health", reason)

    def test_child_raise_renders_the_same_composed_refusal_text(self):
        """1u44n (AC-2): the in-upgrade child surface (begin_build_epoch's
        RuntimeError) renders EXACTLY the composed string; the MCP surface
        strips only the `upgrade_in_progress: ` prefix (asserted in
        test_server_tools)."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            index_dir = root / ".wavefoundry" / "index"
            checkpoint = root / publication_control.UPGRADE_CHECKPOINT_REL
            checkpoint.parent.mkdir(parents=True)
            checkpoint.write_text(
                json.dumps(
                    {
                        "current_phase": "awaiting_memory_validation",
                        "pid": -1,
                        "memory_backfill_pending": 0,
                    }
                ),
                encoding="utf-8",
            )
            reason = publication_control.publication_checkpoint_reason(
                root, "index_build"
            )
            import os

            with patch.dict(os.environ, {}, clear=False):
                os.environ.pop("WAVEFOUNDRY_UPGRADE_PARENT_FINALIZE_RECEIPT", None)
                os.environ.pop("WAVEFOUNDRY_UPGRADE_PUBLISHER_TOKEN", None)
                with self.assertRaises(RuntimeError) as raised:
                    index_state_store.begin_build_epoch(index_dir, "docs")
            self.assertEqual(str(raised.exception), reason)
            self.assertIn("index_health", str(raised.exception))

    def test_non_object_checkpoint_shapes_are_corrupt_and_blocking(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            checkpoint = root / publication_control.UPGRADE_CHECKPOINT_REL
            checkpoint.parent.mkdir(parents=True)
            for value in ([], None, "x", 42):
                with self.subTest(value=value):
                    checkpoint.write_text(json.dumps(value), encoding="utf-8")
                    self.assertEqual(publication_control.read_upgrade_checkpoint(root), {})
                    self.assertIn(
                        "upgrade_in_progress",
                        publication_control.publication_block_reason(root, "wf_prepare_wave"),
                    )

    def test_receipt_id_is_recomputed_from_semantics_and_parent(self):
        semantic = {
            "schema_version": review_policy.REVIEW_POLICY_SCHEMA_VERSION,
            "evaluator_version": review_policy.REVIEW_POLICY_EVALUATOR_VERSION,
            "policy_input_digest": "digest",
            "delivery_mode": "universal",
            "primer_depth": "standard",
            "council_seats": ["red-team"],
            "requested_lanes": [],
            "required_lanes": ["code-reviewer"],
            "delivery_council_required": True,
        }
        receipt, _append = review_policy.build_policy_receipt(semantic, None)
        self.assertIsNotNone(receipt)
        forged = dict(receipt)
        forged["receipt_id"] = "forged-receipt"
        self.assertTrue(
            any(
                "receipt_id does not match" in error
                for error in review_evidence.validate_review_evidence_records([forged])
            )
        )

    # One change body through the real policy digest path, shared by every
    # digest stability/sensitivity test below so none of them can drift into
    # asserting on the canonicalizer alone.
    def _policy_digest(self, body: bytes) -> str:
        return review_policy.policy_input_digest(
            wave_review={"enabled": True, "delivery_mode": "universal"},
            project_lanes=(),
            review_policies={},
            changes=(("1abc-bug example", "bug", body),),
            requested_lanes=(),
        )

    def _policy_receipt_id(self, body: bytes) -> str:
        semantic = {
            "schema_version": review_policy.REVIEW_POLICY_SCHEMA_VERSION,
            "evaluator_version": review_policy.REVIEW_POLICY_EVALUATOR_VERSION,
            "policy_input_digest": self._policy_digest(body),
            "delivery_mode": "universal",
            "primer_depth": "standard",
            "council_seats": ["red-team"],
            "requested_lanes": [],
            "required_lanes": ["code-reviewer"],
            "delivery_council_required": True,
        }
        return review_policy.derive_receipt_id(
            semantic, review_policy.GENESIS_RECEIPT_PARENT
        )

    def test_policy_digest_ignores_only_one_canonical_gardener_date(self):
        digest = self._policy_digest

        base = b"# Change\nOwner: Engineering\nLast verified: 2026-07-29\n\n## Requirements\n\nKeep this.\n"
        next_day = base.replace(b"2026-07-29", b"2026-07-30")
        substantive = base.replace(b"Keep this.", b"Keep that.")
        self.assertEqual(digest(base), digest(next_day))
        self.assertNotEqual(digest(base), digest(substantive))

    @staticmethod
    def _change_doc_with_progress_log() -> bytes:
        """A change doc carrying every requirement-bearing section.

        `## Progress Log` sits in the middle so the sensitivity cases below also
        prove the excluded region ends at the next `## ` heading instead of
        swallowing the sections that follow it.
        """

        return (
            "# Change\n"
            "Owner: Engineering\n"
            "Last verified: 2026-08-05\n"
            "\n## Rationale\n\nThe receipt digests repair-tracking prose.\n"
            "\n## Requirements\n\n1. Exclude the Progress Log body from the digest.\n"
            "\n## Scope\n\n**In scope:** one canonicalizer helper.\n"
            "\n## Acceptance Criteria\n\n- [ ] AC-1: A logged repair keeps the digest stable.\n"
            "\n## Tasks\n\n- [ ] Add the helper.\n"
            "\n## Serialization Points\n\n- `gardener_metadata.py`\n"
            "\n## AC Priority\n\n"
            "| AC | Priority | Rationale |\n| --- | --- | --- |\n"
            "| AC-1 | required | The stability property is the fix. |\n"
            "\n## Progress Log\n\n"
            "| Date | Update | Evidence |\n| ---- | ------ | -------- |\n"
            "| 2026-08-05 | Filed after the operator flagged the reopening loop. | ledger |\n"
            "\n## Decision Log\n\n"
            "| Date | Decision | Reason | Alternatives |\n| ---- | -------- | ------ | ------------ |\n"
            "| 2026-08-05 | Exclude the section. | Narration states no claim. | Cycle cap. |\n"
            "\n## Risks\n\n"
            "| Risk | Mitigation |\n| ---- | ---------- |\n"
            "| The exclusion is drawn too wide. | One sensitivity case per surface. |\n"
            "\n## Session Handoff\n\n"
            "See `docs/agents/session-handoff.md` for current session state.\n"
        ).encode("utf-8")

    def test_progress_log_narration_never_moves_the_policy_digest(self):
        """AC-1: appending, editing, or reordering rows keeps digest and receipt id."""

        base = self._change_doc_with_progress_log()
        first_row = b"| 2026-08-05 | Filed after the operator flagged the reopening loop. | ledger |\n"
        second_row = b"| 2026-08-05 | Repaired a drifted line citation in place. | test:x |\n"
        appended = base.replace(first_row, first_row + second_row)
        reordered = base.replace(first_row, second_row + first_row)
        rewritten = base.replace(
            b"Filed after the operator flagged the reopening loop.",
            b"Filed after the operator flagged that the review loop kept reopening.",
        )
        emptied = base.replace(first_row, b"")
        for label, variant in (
            ("appended", appended),
            ("reordered", reordered),
            ("rewritten", rewritten),
            ("emptied", emptied),
        ):
            with self.subTest(variant=label):
                self.assertNotEqual(base, variant, "the fixture must really differ on disk")
                self.assertEqual(self._policy_digest(base), self._policy_digest(variant))
                self.assertEqual(self._policy_receipt_id(base), self._policy_receipt_id(variant))
        # CRLF line endings are the field-normal case on Windows checkouts under
        # `core.autocrlf`, where the heading arrives as `## Progress Log\r`. A
        # heading pattern that tolerated only spaces and tabs matched zero times
        # there, the `len(matches) != 1` guard returned the body unchanged, and
        # the exclusion degraded to a silent no-op on every Windows target repo.
        crlf = base.replace(b"\n", b"\r\n")
        crlf_appended = crlf.replace(
            first_row.replace(b"\n", b"\r\n"),
            first_row.replace(b"\n", b"\r\n") + second_row.replace(b"\n", b"\r\n"),
        )
        with self.subTest(variant="crlf-appended"):
            self.assertIn(b"## Progress Log\r\n", crlf, "the fixture must really carry CRLF")
            self.assertNotEqual(crlf, crlf_appended, "the fixture must really differ on disk")
            self.assertIn(
                gardener_metadata.PROGRESS_LOG_SENTINEL,
                gardener_metadata.canonical_review_policy_body(crlf).decode("utf-8"),
            )
            self.assertEqual(self._policy_digest(crlf), self._policy_digest(crlf_appended))
            self.assertEqual(
                self._policy_receipt_id(crlf), self._policy_receipt_id(crlf_appended)
            )

    def test_every_other_change_doc_surface_still_moves_the_policy_digest(self):
        """AC-2 and AC-3a: one sensitivity case per requirement-bearing surface."""

        base = self._change_doc_with_progress_log()
        cases = (
            ("rationale", b"The receipt digests repair-tracking prose.", b"The receipt digests narration."),
            ("requirements", b"1. Exclude the Progress Log body from the digest.", b"1. Exclude two sections."),
            ("scope", b"**In scope:** one canonicalizer helper.", b"**In scope:** two canonicalizer helpers."),
            ("acceptance-criteria", b"AC-1: A logged repair keeps the digest stable.", b"AC-1: A logged repair moves the digest."),
            ("tasks", b"- [ ] Add the helper.", b"- [ ] Add the helper and a second one."),
            ("serialization-points", b"- `gardener_metadata.py`", b"- `gardener_metadata.py`; `review_policy.py`"),
            ("ac-priority", b"| AC-1 | required | The stability property is the fix. |", b"| AC-1 | important | The stability property is the fix. |"),
            ("decision-log", b"| 2026-08-05 | Exclude the section. | Narration states no claim. | Cycle cap. |", b"| 2026-08-05 | Cap the cycles. | Simpler. | Exclusion. |"),
            ("risks", b"| The exclusion is drawn too wide. | One sensitivity case per surface. |", b"| The exclusion is drawn too wide. | Nothing. |"),
            ("session-handoff", b"See `docs/agents/session-handoff.md` for current session state.", b"Paused mid-implementation; resume at the canonicalizer."),
        )
        for label, old, new in cases:
            with self.subTest(surface=label):
                self.assertIn(old, base)
                variant = base.replace(old, new)
                self.assertNotEqual(self._policy_digest(base), self._policy_digest(variant))

    def test_policy_and_drift_consumers_share_the_same_gardener_date_boundary(self):
        """The DATE boundary is shared; it is no longer the only one.

        `index_state_store`'s doc-drift consumer deliberately shares only
        `normalize_gardener_date`. The review-policy body carries one further
        normalization (the `## Progress Log` body), so these cases carry no
        Progress Log section and pin the shared date boundary alone.
        """

        cases = (
            (
                "# Change\nOwner: Engineering\nLast verified: 2026-07-29\n\n## Body\nText.\n",
                True,
            ),
            (
                "# Change\nOwner: Engineering\nLast verified: 2026-07-29\nLast verified: 2026-07-30\n\n## Body\nText.\n",
                False,
            ),
            (
                "# Change\nOwner: Engineering\n\n## Body\nLast verified: 2026-07-29\n",
                False,
            ),
            (
                "# Change\nOwner: Engineering\nLast verified: yesterday\n\n## Body\nText.\n",
                False,
            ),
        )
        for text, normalized in cases:
            with self.subTest(text=text):
                stripped = gardener_metadata.normalize_gardener_date(text, replacement=None)
                canonical = gardener_metadata.canonical_review_policy_body(text.encode()).decode()
                self.assertEqual(stripped != text, normalized)
                self.assertEqual(canonical != text, normalized)
                if normalized:
                    self.assertIn(gardener_metadata.GARDENER_DATE_SENTINEL, canonical)
                else:
                    self.assertEqual(canonical, text)

    def test_progress_log_region_is_anchored_and_degrades_on_ambiguity(self):
        """AC-3: fenced lookalikes, zero matches, and two matches all degrade."""

        real = (
            "# Change\nOwner: Engineering\n\n"
            "## Progress Log\n\n| Date | Update | Evidence |\n| 2026-08-05 | Filed. | x |\n\n"
            "## Decision Log\n\nKeep this row digested.\n"
        )
        fenced_only = (
            "# Change\nOwner: Engineering\n\n"
            "## Rationale\n\nThe scaffold emits:\n\n"
            "```markdown\n## Progress Log\n\n| Date | Update | Evidence |\n```\n\n"
            "## Decision Log\n\nKeep this row digested.\n"
        )
        absent = "# Change\nOwner: Engineering\n\n## Rationale\n\nNo tracking section here.\n"
        duplicated = (
            "# Change\nOwner: Engineering\n\n"
            "## Progress Log\n\nFirst.\n\n"
            "## Progress Log\n\nSecond.\n\n"
            "## Decision Log\n\nKeep.\n"
        )
        tilde_inside_backticks = (
            "# Change\nOwner: Engineering\n\n"
            "## Rationale\n\n"
            "```markdown\n~~~\n## Progress Log\n~~~\n```\n\n"
            "## Decision Log\n\nKeep this row digested.\n"
        )
        for label, text, changes in (
            ("fenced-lookalike-only", fenced_only, False),
            ("absent", absent, False),
            ("duplicated", duplicated, False),
            ("tilde-inside-backticks", tilde_inside_backticks, False),
            ("real-section", real, True),
        ):
            with self.subTest(case=label):
                normalized = gardener_metadata.normalize_progress_log(
                    text, replacement=gardener_metadata.PROGRESS_LOG_SENTINEL
                )
                canonical = gardener_metadata.canonical_review_policy_body(
                    text.encode("utf-8")
                ).decode("utf-8")
                self.assertEqual(normalized != text, changes)
                self.assertEqual(canonical != text, changes)
                if not changes:
                    self.assertEqual(normalized, text)
                    self.assertNotIn(gardener_metadata.PROGRESS_LOG_SENTINEL, normalized)
                else:
                    self.assertIn(gardener_metadata.PROGRESS_LOG_SENTINEL, normalized)
                # Sections after the region always survive, fenced or not.
                if "Keep this row digested." in text:
                    self.assertIn("Keep this row digested.", canonical)

    def test_a_fenced_lookalike_inside_the_real_section_neither_ends_nor_reopens_it(self):
        """AC-3: an in-region fence cannot terminate the region early."""

        text = (
            "# Change\nOwner: Engineering\n\n"
            "## Progress Log\n\n"
            "| 2026-08-05 | Filed. | x |\n\n"
            "```markdown\n## Progress Log\n## Decision Log\n```\n\n"
            "| 2026-08-05 | Repaired. | y |\n\n"
            "## Decision Log\n\nKeep this row digested.\n"
        )
        canonical = gardener_metadata.canonical_review_policy_body(
            text.encode("utf-8")
        ).decode("utf-8")
        self.assertIn(gardener_metadata.PROGRESS_LOG_SENTINEL, canonical)
        self.assertNotIn("Filed.", canonical)
        self.assertNotIn("Repaired.", canonical)
        self.assertNotIn("```markdown", canonical)
        self.assertIn("## Decision Log\n\nKeep this row digested.", canonical)

    def test_marker_matched_fence_toggling_keeps_the_real_section_excluded(self):
        """AC-3 / Requirement 4: only a matching marker may close an open fence.

        The other fence cases carry no real `## Progress Log` after the fenced
        construct, so they pass whenever *some* fence guard exists. This case
        puts a real section after a `~~~` nested in a backtick fence, so a
        toggle that is not marker-matched shifts the fence state past the fence
        and the real section is either matched twice or never matched at all.
        """

        text = (
            "# Change\nOwner: Engineering\n\n"
            "## Rationale\n\nThe scaffold emits:\n\n"
            "```markdown\n~~~\n## Progress Log\n~~~\n```\n\n"
            "## Progress Log\n\n"
            "| 2026-08-05 | Filed. | x |\n\n"
            "## Decision Log\n\nKeep this row digested.\n"
        )
        canonical = gardener_metadata.canonical_review_policy_body(
            text.encode("utf-8")
        ).decode("utf-8")
        self.assertIn(gardener_metadata.PROGRESS_LOG_SENTINEL, canonical)
        self.assertNotIn("| 2026-08-05 | Filed. | x |", canonical)
        # The fenced lookalike is untouched prose in a digested section.
        self.assertIn("```markdown\n~~~\n## Progress Log\n~~~\n```", canonical)
        self.assertIn("## Decision Log\n\nKeep this row digested.", canonical)

    def test_the_progress_log_region_ends_only_at_a_level_two_heading(self):
        """AC-3 / Requirement 4: a `###` subheading stays inside the region.

        Seed-180 asks implementers to record `Reflect:` narration, which this
        repository sometimes subheads. Ending the region at any `#` heading would
        leave that narration digested and reopen the churn for exactly the rows
        the exclusion exists to cover.
        """

        text = (
            "# Change\nOwner: Engineering\n\n"
            "## Progress Log\n\n"
            "| 2026-08-05 | Filed. | x |\n\n"
            "### Reflect notes\n\nRoot cause pattern recorded here.\n\n"
            "## Decision Log\n\nKeep this row digested.\n"
        )
        canonical = gardener_metadata.canonical_review_policy_body(
            text.encode("utf-8")
        ).decode("utf-8")
        self.assertIn(gardener_metadata.PROGRESS_LOG_SENTINEL, canonical)
        self.assertNotIn("### Reflect notes", canonical)
        self.assertNotIn("Root cause pattern recorded here.", canonical)
        self.assertNotIn("| 2026-08-05 | Filed. | x |", canonical)
        self.assertIn("## Decision Log\n\nKeep this row digested.", canonical)

    def test_hash_exclusion_diverges_from_the_on_disk_progress_log(self):
        """AC-5a: the digest body carries the sentinel; the file keeps `Gapfill:`."""

        with tempfile.TemporaryDirectory() as tmp:
            change = Path(tmp) / "1abc-bug example.md"
            change.write_bytes(
                self._change_doc_with_progress_log().replace(
                    b"| 2026-08-05 | Filed after the operator flagged the reopening loop. | ledger |",
                    b"| 2026-08-05 | Gapfill: the briefing packet lacked the ledger split. | ledger |",
                )
            )
            on_disk = change.read_text(encoding="utf-8")
            canonical = gardener_metadata.canonical_review_policy_body(
                change.read_bytes()
            ).decode("utf-8")
            self.assertIn("Gapfill:", on_disk)
            self.assertNotIn("Gapfill:", canonical)
            self.assertIn(gardener_metadata.PROGRESS_LOG_SENTINEL, canonical)
            self.assertEqual(on_disk, change.read_text(encoding="utf-8"))

    def test_background_index_epoch_cannot_begin_or_finalize_during_upgrade(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            index_dir = root / ".wavefoundry/index"
            attempt = index_state_store.begin_build_epoch(index_dir, "docs")
            checkpoint = root / publication_control.UPGRADE_CHECKPOINT_REL
            checkpoint.write_text(
                json.dumps({"current_phase": "surface_rendering", "pid": -1}),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(RuntimeError, "upgrade_in_progress"):
                index_state_store.begin_build_epoch(index_dir, "code")
            with self.assertRaisesRegex(RuntimeError, "upgrade_in_progress"):
                index_state_store.finalize_build_epoch(index_dir, attempt)


class ReviewLoopFrictionPolicyTests(unittest.TestCase):
    def test_legacy_extension_fallback_requires_a_real_path_and_reports_location(self):
        # The control must exercise the PATH-SHAPE requirement, so the bare
        # extension lives in `## Scope`, a digested section. Putting it in
        # `## Progress Log` made this pass for an unrelated reason: the
        # canonicalizer replaces that body wholesale, so the matcher never saw
        # the token at all and the test could not detect a relaxed path rule.
        false_positive, _ = review_policy.select_required_review_lanes(
            requested_lanes=(),
            project_lanes=(),
            change_texts=(
                "# Change\n\n## Scope\n\nRecorded in events.jsonl; "
                "the Markdown filename is README.js.md; prose says .js.\n",
            ),
        )
        lanes, reasons = review_policy.select_required_review_lanes(
            requested_lanes=(),
            project_lanes=(),
            change_texts=("# Change\n\n## Scope\n\nTouches lib/widget.js.\n",),
        )
        self.assertNotIn("code-reviewer", false_positive)
        self.assertEqual(lanes, ("code-reviewer",))
        # The reason names the token and a normalized excerpt. It deliberately
        # invents no source location: the corpus is every undeclared document
        # joined and canonicalized, so any offset into it points at no line in
        # any real document. Assert the PROPERTY (no location-shaped number),
        # not one spelling of it; `L22` and `offset 341` are equally misleading.
        reason = reasons["code-reviewer"][0]
        self.assertIn("matched in undeclared change-document prose", reason)
        self.assertIn("lib/widget.js", reason)
        self.assertIsNone(
            re.search(r"(?:line|offset|L|:)\s*\d+", reason),
            f"reason invents a source location: {reason!r}",
        )

    def test_digest_ignores_leading_workflow_status_metadata(self):
        base = b"# Change\nChange Status: planned\nStatus: planned\nLast verified: 2026-08-05\n\n## Scope\n\nKeep this.\n"
        progressed = base.replace(b"Change Status: planned", b"Change Status: implemented").replace(b"Status: planned", b"Status: reviewing").replace(b"2026-08-05", b"2026-08-06")
        digest = lambda body: review_policy.policy_input_digest(
            wave_review={"enabled": True, "delivery_mode": "targeted"},
            project_lanes=(), review_policies={},
            changes=(("1abc-bug example", "bug", body),), requested_lanes=(),
        )
        self.assertEqual(digest(base), digest(progressed))

    # ---- 1uo1w: per-document adoption and the two-tier declaration form ----

    _PROSE_DOC = (
        "# Change\n\nChange ID: `1abc-bug example`\n\n## Scope\n\n"
        "A state machine change.\n\n## Serialization Points\n\n"
        "{body}\n\n## Next\n"
    )

    def _lanes(self, *docs: str) -> tuple[str, ...]:
        lanes, _ = review_policy.select_required_review_lanes(
            requested_lanes=(), project_lanes=(), change_texts=docs
        )
        return lanes

    def test_prose_naming_a_directory_never_confers_adoption(self):
        """Field report: one sentence of prose emptied a required-lane roster.

        Any extracted path was read as proof the author adopted the
        declared-target contract, so a narrative mention of `docs/` switched
        the document out of prose scoring and left it with NOTHING. Pinned at
        the measured worst case (an empty roster, not a reduced one) and in
        BOTH shapes: a plain prose line and a prose BULLET.

        The bullet shape is load-bearing. A first design scanned bullets for
        path tokens, which reproduced this exact failure, because real
        Serialization Points prose is mostly written as bullets.
        """

        baseline = self._lanes(self._PROSE_DOC.format(
            body="- Serialize edits through the runner workstream."
        ))
        self.assertEqual(baseline, ("qa-reviewer", "architecture-reviewer"))
        for shape in (
            "- Shared with the wave that also touches the docs/ folder",
            "Shared with the wave that also touches the docs/ folder",
        ):
            with self.subTest(shape=shape):
                self.assertEqual(
                    self._lanes(self._PROSE_DOC.format(body=shape)),
                    baseline,
                    "prose that merely mentions a directory must not switch "
                    "the document into declared mode",
                )

    def test_adoption_is_per_document_so_a_mixed_wave_loses_no_lane(self):
        """The wave-level suppression IS the defect, at wave scope.

        A wave with one adopting document and one un-migrated sibling scored
        the whole wave on paths alone, so the sibling's prose stopped
        recruiting and the roster collapsed. No corpus census can detect this:
        nearly every declared document is in a closed wave or alone in its
        wave, so a static count returns zero losses under a correct and an
        incorrect design alike. Only a mixed fixture discriminates.
        """

        declared = self._PROSE_DOC.format(
            body="- `docs/specs/mcp-tool-surface.md`"
        )
        undeclared = (
            "# Change\n\nChange ID: `1abd-bug sibling`\n\n## Scope\n\n"
            "Touches framework/scripts/ and tests/ regression harness.\n\n"
            "## Serialization Points\n\n- Serialize through the runner.\n"
        )
        declared_alone = self._lanes(declared)
        undeclared_alone = self._lanes(undeclared)
        self.assertEqual(declared_alone, ("docs-contract-reviewer",))
        self.assertIn("code-reviewer", undeclared_alone)
        mixed = self._lanes(declared, undeclared)
        for lane in set(declared_alone) | set(undeclared_alone):
            self.assertIn(
                lane, mixed,
                "a mixed wave must union each document's own mode, never "
                "suppress the un-migrated sibling's coverage",
            )

    def test_a_shredded_path_fragment_is_not_a_declared_target(self):
        """A phantom is worse than a silent drop: it suppresses the fallback.

        `_REPO_PATH_RE` has no space in its character class, so this project's
        own `<id> <slug>` artifact path shreds into two fragments. The second
        has a dot in its final segment, so it was ACCEPTED as a declared
        target: it matches no risk trigger, flips the document into declared
        mode, and yields zero required lanes. Declaring a real on-disk
        wave-owned artifact was therefore actively harmful.
        """

        doc = self._PROSE_DOC.format(
            body="- docs/waves/1uo1x declaration-and-digest-boundaries/wave.md"
        )
        self.assertEqual(
            review_policy.serialization_point_paths(doc), (),
            "an unbackticked spaced path must declare nothing: its first "
            "fragment is not a declared target, so the bullet is prose",
        )
        self.assertNotEqual(
            self._lanes(doc), (),
            "a shredded fragment must never suppress the fallback",
        )

    def test_a_wrapped_pure_path_bullet_is_prose_not_a_partial_declaration(self):
        """Readiness finding: "continuation lines are not scanned" was ambiguous.

        One reading scans the bullet's first line and discards the rest, which
        silently drops the continuation targets. Measured over the corpus that
        reading keeps five extra documents and loses `docs-contract-reviewer`
        on the real declaration reproduced here, the only lane loss either
        reading produces. A wrapped bullet is therefore prose in its entirety;
        a multi-target declaration belongs in the explicit block.
        """

        wrapped = self._PROSE_DOC.format(body=(
            "- `upgrade_wavefoundry.py`, `server_impl.py`,\n"
            "  `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md`"
        ))
        self.assertEqual(
            review_policy.serialization_point_paths(wrapped), (),
            "a wrapped bullet must not declare its first line's targets while "
            "silently dropping the seed on its continuation line",
        )
        # The real `1uf68` bullet above opens with BARE filenames, which carry
        # no separator and are therefore not declared targets at all. That
        # makes it a weak pin on its own: it stays green even with the
        # wrapped-bullet rule deleted. This variant opens with genuine slashed
        # paths, so the first line WOULD declare if the rule were removed, and
        # the assertion is load-bearing rather than incidentally true.
        wrapped_slashed = self._PROSE_DOC.format(body=(
            "- `src/a.py`, `src/b.py`,\n"
            "  `docs/specs/mcp-tool-surface.md` land together"
        ))
        self.assertEqual(
            review_policy.serialization_point_paths(wrapped_slashed), (),
            "deleting the wrapped-bullet rule must fail this assertion",
        )

    def test_the_explicit_block_declares_a_target_containing_spaces(self):
        """This project's own `<id> <slug>` artifacts were undeclarable.

        Regex extraction has no space in its character class, so a wave-owned
        path shredded into fragments. Inside the marker block a backtick span
        is ONE target, spaces included, which is the only reason the strict
        opt-in tier exists. Proven against a real on-disk artifact.
        """

        root = Path(__file__).resolve().parents[4]
        artifact = (
            "docs/waves/1uo1x declaration-and-digest-boundaries/wave.md"
        )
        self.assertTrue(
            (root / artifact).exists(), "fixture must name a real artifact"
        )
        doc = self._PROSE_DOC.format(body=(
            "**Review targets (repo-relative paths):**\n\n"
            f"- `{artifact}`\n- `.wavefoundry/framework/scripts/Review_Policy.py`"
        ))
        declared = review_policy.serialization_point_paths(doc)
        self.assertIn(artifact.lower(), declared)
        self.assertIn(
            ".wavefoundry/framework/scripts/review_policy.py", declared,
            "spans lowercase like every other target, because the footprint "
            "consumer folds case on the git side only",
        )

    def test_prose_declares_nothing_inside_the_explicit_block_either(self):
        """Delivery finding: the reported defect survived inside tier 2.

        Span extraction took every backticked token and ignored the English
        words around it, so the wave's own worst-case sentence still emptied a
        roster when written INSIDE the block the docs present as the stricter
        opt-in. The direction of harm is the silent one: an author who believes
        their sentence is prose has actually declared, which suppresses the
        fallback. Seven shipped carriers state "prose declares nothing in any
        shape", so the code has to mean it in both tiers.
        """

        marker = "**Review targets (repo-relative paths):**"
        prose = (
            "- Shared with the wave that also touches the `docs/` folder"
        )
        outside = self._lanes(self._PROSE_DOC.format(body=prose))
        inside = self._lanes(
            self._PROSE_DOC.format(body=f"{marker}\n\n{prose}")
        )
        self.assertEqual(
            inside, outside,
            "a prose bullet must score identically inside and outside the "
            "explicit block",
        )
        self.assertEqual(inside, ("qa-reviewer", "architecture-reviewer"))
        wrapped = self._PROSE_DOC.format(body=(
            f"{marker}\n\n- `src/a.py` and the module owning\n"
            "  the thing must land together"
        ))
        self.assertEqual(
            review_policy.serialization_point_paths(wrapped), (),
            "the wrapped-bullet rule applies in both tiers, not just the floor",
        )
        # The bullet above is ALSO rejected by the residue rule, so it does not
        # isolate the wrapped-bullet rule inside the block. Here the first line
        # is pure targets with no residue, so only the wrapped-bullet rule can
        # reject it.
        wrapped_clean_first_line = self._PROSE_DOC.format(body=(
            f"{marker}\n\n- `src/a.py`\n  and the module owning it"
        ))
        self.assertEqual(
            review_policy.serialization_point_paths(wrapped_clean_first_line),
            (),
            "deleting the block's wrapped-bullet rule must fail this assertion",
        )
        # A span that is not a declared target rejects the whole bullet, the
        # same all-or-nothing contract the floor uses.
        non_target = self._PROSE_DOC.format(
            body=f"{marker}\n\n- `notes`, `src/a.py`"
        )
        self.assertEqual(
            review_policy.serialization_point_paths(non_target), (),
            "one non-target span makes the whole block bullet prose",
        )

    def test_a_fenced_example_of_the_section_never_substitutes_for_the_real_one(self):
        """Delivery finding: the section finder itself was fence-blind.

        A document illustrating the declaration form inside a fence had that
        example read as the real section, so it declared the example's path and
        dropped every real one, losing a lane. The closing scan was blind the
        same way, letting a fenced `## ` line truncate the section.

        The shipped scaffold now teaches fenced examples in this exact section,
        so this is the ordinary case rather than an exotic one.
        """

        doc = (
            "# C\n\n## Rationale\n\nAuthors write it like this:\n\n"
            "```\n## Serialization Points\n\n- `src/example.py`\n\n```\n\n"
            "## Serialization Points\n\n- `src/real.py`\n"
            "- `docs/specs/real.md`\n\n## Next\n"
        )
        self.assertEqual(
            review_policy.serialization_point_paths(doc),
            ("src/real.py", "docs/specs/real.md"),
        )
        truncating = (
            "## Serialization Points\n\n```\n## Fake\n```\n\n"
            "- `src/real.py`\n\n## Next\n"
        )
        self.assertEqual(
            review_policy.serialization_point_paths(truncating),
            ("src/real.py",),
            "a fenced heading must not close the section",
        )

    def test_the_tiers_union_rather_than_the_block_masking_the_floor(self):
        """Delivery finding: a marker line could silently disable the floor.

        A mixed-notation bullet (one unbackticked path, one backticked) is
        rejected by the span rule but accepted by the floor. Because block
        bullets were excluded from the floor pass, adding a marker line above
        such a bullet dropped it entirely, contradicting the union invariant
        this module documents and producing the silent under-recruitment the
        wave exists to remove.
        """

        marker = "**Review targets (repo-relative paths):**"
        mixed = "- src/app/handler.py, `docs/specs/x.md`"
        inside = self._PROSE_DOC.format(body=f"{marker}\n\n{mixed}")
        outside = self._PROSE_DOC.format(body=mixed)
        self.assertEqual(
            review_policy.serialization_point_paths(inside),
            review_policy.serialization_point_paths(outside),
        )
        self.assertEqual(
            set(review_policy.serialization_point_paths(inside)),
            {"src/app/handler.py", "docs/specs/x.md"},
        )

    def test_a_span_carrying_a_note_or_two_paths_declares_nothing(self):
        """Reverification finding: the space tolerance opened a phantom.

        `_is_declared_target` only asks whether the final segment has a dot, so
        a real path with a trailing note glued on, or two paths crammed into
        one span, declared the whole string. That names no file, matches no
        trigger, SUPPRESSES the fallback, and yields a SMALLER roster than the
        identical bullet with no marker above it. It also zeroes the wave
        footprint for a file that really changed.

        The space tolerance is spent deliberately: a directory segment may
        contain spaces, a basename may not, and an extension is never followed
        by more text.
        """

        marker = "**Review targets (repo-relative paths):**"
        noted = self._PROSE_DOC.format(body=(
            f"{marker}\n\n- `.wavefoundry/framework/scripts/"
            "upgrade_wavefoundry.py (extraction filter)`"
        ))
        self.assertEqual(review_policy.serialization_point_paths(noted), ())
        self.assertIn(
            "release-reviewer", self._lanes(noted),
            "rejecting the phantom must leave the document on its fallback, "
            "which is strictly more coverage than the phantom produced",
        )
        two_paths = self._PROSE_DOC.format(
            body=f"{marker}\n\n- `src/a.py src/b.py`"
        )
        self.assertEqual(review_policy.serialization_point_paths(two_paths), ())
        # The legitimate spaced shape still declares: the space is in a
        # DIRECTORY segment and the basename is a plain filename.
        legit = self._PROSE_DOC.format(
            body=f"{marker}\n\n- `docs/waves/1abc some slug/wave.md`"
        )
        self.assertEqual(
            review_policy.serialization_point_paths(legit),
            ("docs/waves/1abc some slug/wave.md",),
        )

    def test_a_span_must_look_like_a_path_not_merely_carry_a_dot(self):
        """A version string is not a declared target.

        `_is_declared_target` accepts any dotted final segment, which the floor
        survives only because `_REPO_PATH_RE` independently requires a
        separator. Spans get no such regex, so without an explicit separator
        rule `- ``1.15.4``` declared itself, matched no trigger, and zeroed the
        document's roster.
        """

        doc = self._PROSE_DOC.format(body=(
            "**Review targets (repo-relative paths):**\n\n- `1.15.4`"
        ))
        self.assertEqual(review_policy.serialization_point_paths(doc), ())
        self.assertNotEqual(
            self._lanes(doc), (),
            "a rejected span must leave the document on its fallback",
        )

    def test_a_declaration_directly_above_a_fence_is_not_a_wrapped_bullet(self):
        """A fence marker opens a block; it is a boundary, not a continuation.

        Reading it as one dropped a real declaration that sits immediately
        above a fenced example, which the shipped scaffold now teaches authors
        to write in this section.
        """

        doc = self._PROSE_DOC.format(
            body="- `docs/specs/a.md`\n```\nexample\n```"
        )
        self.assertEqual(
            review_policy.serialization_point_paths(doc),
            ("docs/specs/a.md",),
        )

    def test_a_fenced_marker_never_preempts_the_real_block(self):
        """The marker scan skips fences, and nothing pinned that.

        Both shipped scaffolds now carry a FENCED marker example, so the first
        author who keeps the example and adds a real block below lands in this
        shape. If the fenced marker wins, the real block degrades to tier 1 and
        its spaced target shreds: silent loss of a declaration, which is the
        class this wave exists to remove.
        """

        marker = "**Review targets (repo-relative paths):**"
        doc = self._PROSE_DOC.format(body=(
            f"```\n{marker}\n\n- `src/fake.py`\n```\n\n"
            f"{marker}\n\n- `docs/waves/1abc some slug/wave.md`"
        ))
        self.assertEqual(
            review_policy.serialization_point_paths(doc),
            ("docs/waves/1abc some slug/wave.md",),
        )

    def test_the_marker_block_ends_at_the_first_non_bullet_line(self):
        """Requirement 5's block boundary had no test.

        Without the terminator the tier-2 span rules leak past the block, so a
        spaced target written in ordinary prose further down the section is
        picked up as a declaration.
        """

        marker = "**Review targets (repo-relative paths):**"
        doc = self._PROSE_DOC.format(body=(
            f"{marker}\n\n- `src/a.py`\n\nAlso:\n\n"
            "- `docs/waves/1abc some slug/wave.md`"
        ))
        self.assertEqual(
            review_policy.serialization_point_paths(doc), ("src/a.py",),
            "the block ends at `Also:`, so the spaced target below it is "
            "outside tier 2 and the floor cannot declare it either",
        )

    def test_a_root_level_file_is_not_a_declared_target(self):
        """Root-level declarations are deliberately out of scope.

        `_is_declared_target` alone would accept `README.md`, so the tier-1
        shape check carries this decision on its own. Measured across four
        repositories at plan time: zero root-level source files, zero lane
        impact, so requiring a separator is what keeps ordinary prose from
        reading as a declaration.
        """

        doc = self._PROSE_DOC.format(body="- `README.md`")
        self.assertEqual(review_policy.serialization_point_paths(doc), ())

    def test_the_marker_is_matched_case_insensitively_on_purpose(self):
        """Leniency here is deliberate, not an accident of a regex flag.

        A near-miss on the marker degrades to the tier-1 floor, so tolerating
        case costs nothing and removes one way to lose a spaced declaration
        silently.
        """

        doc = self._PROSE_DOC.format(body=(
            "**review targets (repo-relative paths):**\n\n"
            "- `docs/waves/1abc some slug/wave.md`"
        ))
        self.assertEqual(
            review_policy.serialization_point_paths(doc),
            ("docs/waves/1abc some slug/wave.md",),
        )

    def test_an_inadmissible_status_count_degrades_byte_for_byte(self):
        """AC-4's degrade clause, pinned directly rather than by census.

        The corpus census cannot test this: the guard returns the input
        unchanged on an inadmissible count, so the census's own count
        assertion can never observe a value outside the admissible set. Only a
        constructed three-status-line document reaches the branch.
        """

        three = (
            "# T\n\nChange Status: planned\nStatus: planned\n"
            "Previous Change Status: draft\nStatus: reviewing\n\n## Scope\n\nX\n"
        )
        self.assertEqual(
            gardener_metadata.normalize_review_tracking_status(
                three, replacement="<workflow-status>"
            ),
            three,
            "a count outside {1, 2} returns the input byte-for-byte",
        )

    def test_declarations_survive_a_crlf_checkout(self):
        """A Windows checkout must not silently lose its declarations.

        The line splitter splits on `\\n`, so every line carries a trailing
        `\\r`. A marker pattern anchored with `[ \\t]*$` therefore never matches
        there, and the document degrades to the floor with its spaced targets
        gone: silent loss, in the change that exists to remove silent loss.
        Both tiers are pinned, and both must produce byte-identical results
        under either line ending.
        """

        body = (
            "**Review targets (repo-relative paths):**\n\n"
            "- `docs/waves/1abc some slug/wave.md`\n\n"
            "Also serialized:\n\n"
            "- `.wavefoundry/framework/scripts/review_policy.py`"
        )
        doc = self._PROSE_DOC.format(body=body)
        self.assertEqual(
            review_policy.serialization_point_paths(doc.replace("\n", "\r\n")),
            review_policy.serialization_point_paths(doc),
        )
        self.assertIn(
            "docs/waves/1abc some slug/wave.md",
            review_policy.serialization_point_paths(doc.replace("\n", "\r\n")),
        )

    def test_fenced_examples_and_tier_union_are_pinned_not_left_to_chance(self):
        """AC-7b: two behaviors nothing else would have decided deliberately.

        A fenced example inside the section is documentation, not a
        declaration; it currently declares its example path. And a document
        carrying BOTH a marker block and separate pure-path bullets must keep
        both sets, so adding a block can never silently drop what the floor
        already accepted.
        """

        # The bullet is followed by a BLANK line inside the fence, so the
        # wrapped-bullet rule cannot reject it and only the fence skip can.
        # Without the blank line this fixture stays green with fence handling
        # deleted, which would make it a pin in name only.
        fenced = self._PROSE_DOC.format(body=(
            "Authors declare targets like this:\n\n"
            "```\n- `src/app/handler.py`\n\n```"
        ))
        self.assertEqual(
            review_policy.serialization_point_paths(fenced), (),
            "a fenced example must declare nothing",
        )
        both = self._PROSE_DOC.format(body=(
            "**Review targets (repo-relative paths):**\n\n"
            "- `docs/specs/mcp-tool-surface.md`\n\n"
            "Also serialized:\n\n"
            "- `.wavefoundry/framework/scripts/review_policy.py`"
        ))
        declared = review_policy.serialization_point_paths(both)
        self.assertIn("docs/specs/mcp-tool-surface.md", declared)
        self.assertIn(
            ".wavefoundry/framework/scripts/review_policy.py", declared,
            "the tiers union; a marker block must not suppress the floor",
        )

    def test_declaration_change_loses_no_lane_anywhere_in_the_corpus(self):
        """AC-7: the floor's safety contract, asserted over the real corpus.

        A stricter declaration rule reclassifies documents, and the only
        outcome that would be unacceptable is a document ending up with LESS
        required review than it has today. Asserts that invariant rather than a
        fixed keep/revert count, because a downstream repository will differ.

        Measured here at delivery: 814 change documents, 138 declared before
        and 37 after, 101 reverting to whole-document fallback, 95 gaining
        lanes, and ZERO losing any.
        """

        root = Path(__file__).resolve().parents[4]
        docs = [
            p for p in sorted((root / "docs/plans").glob("*.md"))
            if "plan-template" not in p.name
        ]
        docs += [
            p for p in sorted((root / "docs/waves").glob("*/*.md"))
            if p.name != "wave.md"
        ]
        self.assertGreater(len(docs), 100, "census must see a real corpus")

        def roster(text, paths):
            lanes, _ = review_policy.select_required_review_lanes(
                requested_lanes=(), project_lanes=(),
                change_texts=(text if not paths else
                              "## Serialization Points\n\n"
                              + "".join(f"- `{p}`\n" for p in paths),),
            )
            return set(lanes)

        losses = []
        for path in docs:
            try:
                text = path.read_text("utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            before = roster(text, self._legacy_declared_paths(text))
            after = roster(text, review_policy.serialization_point_paths(text))
            if before - after:
                losses.append((path.name, sorted(before - after)))
        self.assertEqual(
            losses, [],
            "no change document may lose a required lane; a stricter "
            "declaration rule must only ever restore coverage",
        )

    @staticmethod
    def _legacy_declared_paths(text: str) -> tuple[str, ...]:
        """The pre-change extractor: regex-scan the whole section."""

        body = review_policy._serialization_points_body(text)
        if body is None:
            return ()
        return tuple(dict.fromkeys(
            candidate
            for candidate in (
                m.group("path").lower()
                for m in review_policy._REPO_PATH_RE.finditer(body)
            )
            if review_policy._is_declared_target(candidate)
        ))

    def test_the_shipped_scaffolds_declare_nothing_until_an_author_edits_them(self):
        """Both project and shipped scaffold authorities declare no targets."""

        root = Path(__file__).resolve().parents[4]
        template = (root / "docs/plans/plan-template.md").read_text("utf-8")
        self.assertEqual(
            review_policy.serialization_point_paths(template), (),
            "the plan template must scaffold zero declared targets",
        )
        shipped = (
            root / ".wavefoundry/framework/install/plan-template.md"
        ).read_text("utf-8")
        self.assertEqual(
            review_policy.serialization_point_paths(shipped), (),
            "the shipped fallback template must scaffold zero declared targets",
        )
        server_impl_src = (
            root / ".wavefoundry/framework/scripts/server_impl.py"
        ).read_text("utf-8")
        self.assertNotIn(
            'return """# [Change Title]',
            server_impl_src,
            "server_impl must not retain a second inline template authority",
        )

    def test_body_prose_status_line_is_never_normalized(self):
        """Readiness finding: the carrier boundary was a line SHAPE, not a key.

        The scan kept the region open for any line matching `Word: text`, so
        `Problem: the gate fails.` held it open and the later body `Status:`
        line was rewritten. That makes a real contract edit digest-invisible:
        an operator changes a document's meaning and the receipt does not move.

        The fixture deliberately carries NO `## ` heading. An earlier revision
        of this plan proposed bounding the region at the first `## ` heading;
        that is structurally incapable of fixing this, because a `## ` heading
        already closes the current scan, so every capture necessarily lies
        before it. This document is the case that disproved that design.
        """

        text = (
            "# T\n\nOwner: Eng\n\nProblem: the gate fails.\n\n"
            "Status: this sentence is real contract prose a reviewer must read.\n"
        )
        self.assertEqual(
            gardener_metadata.normalize_review_tracking_status(
                text, replacement="<workflow-status>"
            ),
            text,
            "a body Status: line held open by unknown-key prose must survive "
            "byte-identical",
        )

    def test_leading_carrier_survives_a_blockquote_and_stops_at_prose(self):
        """The boundary moves in neither direction, and a fence closes it.

        Blockquote tolerance is the repair for a measured wrong result: the
        current scan truncates at a `> **REFRAMED...**` line, leaving genuine
        frontmatter status lines digest-SIGNIFICANT, so advancing that
        document's status lapses its approvals. `1p7dg-enh` is the real case.

        The fence direction is already correct today and is pinned as a
        preserved behavior, not a repair.
        """

        normalize = gardener_metadata.normalize_review_tracking_status
        quoted = (
            "# T\n\n> **REFRAMED 2026-06-23** superseded by a later wave.\n\n"
            "Change Status: planned\nStatus: planned\n\n## Scope\n\nKeep this.\n"
        )
        normalized = normalize(quoted, replacement="<workflow-status>")
        self.assertIn("Change Status: <workflow-status>", normalized)
        self.assertIn("Status: <workflow-status>", normalized)
        self.assertIn("> **REFRAMED 2026-06-23**", normalized)

        fenced = (
            "# T\n\nOwner: Eng\n\n```\nStatus: inside a fenced example\n```\n"
        )
        self.assertEqual(
            normalize(fenced, replacement="<workflow-status>"), fenced,
            "a fence marker closes the carrier, so a fenced example is prose",
        )

    def test_status_normalization_admits_one_or_two_matches_not_exactly_one(self):
        """A literal `len(matches) != 1` guard would lapse approvals en masse.

        The siblings `normalize_gardener_date` and `normalize_progress_log`
        normalize a SINGLE line and degrade on any other count. Copying that
        contract here is wrong: a change document legitimately carries both
        `Change Status:` and `Status:`, and 794 of 1457 documents in this
        repository have exactly that pair. Under `!= 1` every one of them
        stops normalizing, so the digest moves on each status advance and the
        recorded approvals lapse.

        This test fails under the literal sibling guard and passes under the
        stated admissible set, which is what makes it an anti-regression pin
        rather than a comment.
        """

        normalize = gardener_metadata.normalize_review_tracking_status
        pair = (
            "# T\n\nChange ID: `1abc-bug example`\nChange Status: planned\n"
            "Owner: Engineering\nStatus: planned\n\n## Scope\n\nKeep this.\n"
        )
        normalized = normalize(pair, replacement="<workflow-status>")
        self.assertEqual(normalized.count("<workflow-status>"), 2)
        self.assertIn("Change Status: <workflow-status>", normalized)

        single = "# T\n\nChange Status: planned\n\n## Scope\n\nKeep this.\n"
        self.assertIn(
            "Change Status: <workflow-status>",
            normalize(single, replacement="<workflow-status>"),
            "one match stays admissible; the set is {1, 2}, not {2}",
        )

    def test_carrier_boundary_census_reports_its_own_transition_cost(self):
        """AC-6: the boundary change must report what it moves, not assume it.

        Asserts the PROPERTIES that make the transition safe rather than a
        fixed count, because a downstream repository will differ: no document
        may produce a match count outside the admissible set, and no document
        may LOSE a captured line (that direction would make a previously
        digest-neutral status advance suddenly contract-bearing).

        On this repository the measured result is one differing document,
        `1p7dg-enh cross-file-receiver-resolution.md`, which widens because its
        line-3 blockquote currently truncates the carrier, and its wave is
        closed. Recorded rather than asserted, so the census stays honest
        somewhere else.
        """

        root = Path(__file__).resolve().parents[4]
        docs = sorted((root / "docs").rglob("*.md"))
        self.assertGreater(len(docs), 100, "census must see a real corpus")
        normalize = gardener_metadata.normalize_review_tracking_status
        status_re = gardener_metadata._REVIEW_TRACKING_STATUS_LINE_RE
        legacy_re = gardener_metadata._FRONTMATTER_METADATA_RE

        def legacy_captured(lines):
            found = []
            for index, line in enumerate(lines):
                if status_re.fullmatch(line):
                    found.append(index)
                if (
                    line.strip()
                    and not line.startswith("# ")
                    and not legacy_re.match(line)
                ):
                    break
            return tuple(found)

        # A sentinel that cannot occur in the corpus. Counting the production
        # `<workflow-status>` marker instead reports a false 3 for this wave's
        # own change doc, which quotes that marker in its Rationale prose.
        sentinel = "<<<census-sentinel-9f3a>>>"
        losses = []
        for path in docs:
            try:
                text = path.read_text("utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            self.assertNotIn(sentinel, text, "sentinel must be corpus-unique")
            lines = text.split("\n")
            normalized = normalize(text, replacement=sentinel)
            shipped = normalized.count(sentinel)
            self.assertIn(
                shipped, (0, 1, 2),
                f"{path.name} normalized an inadmissible count {shipped}",
            )
            if shipped < len(legacy_captured(lines)):
                losses.append(path.name)
        self.assertEqual(
            losses, [],
            "no document may lose a normalized status line: that direction "
            "makes a previously digest-neutral status advance contract-bearing",
        )

    def test_receipt_rotation_is_not_semantic_but_the_roster_is_persisted(self):
        semantic = {
            "schema_version": 1, "evaluator_version": review_policy.REVIEW_POLICY_EVALUATOR_VERSION,
            "policy_input_digest": "digest", "delivery_mode": "targeted", "primer_depth": "standard",
            "council_seats": ["red-team", "code-reviewer"], "requested_lanes": [],
            "required_lanes": ["code-reviewer"], "delivery_council_required": False,
        }
        current, appended = review_policy.build_policy_receipt(semantic, None)
        self.assertTrue(appended)
        changed_rotation = {**semantic, "council_seats": ["red-team", "docs-contract-reviewer"]}
        retained, appended = review_policy.build_policy_receipt(changed_rotation, current)
        self.assertFalse(appended)
        self.assertEqual(retained["council_seats"], ["red-team", "code-reviewer"])

    def test_checkbox_tracking_preserves_ac_deferral_but_not_completion_or_tasks(self):
        base = (
            "# Change\n\n## Acceptance Criteria\n\n"
            "- [ ] AC-1: required contract\n- [~] AC-2: deferred *operator decision*\n"
            "\n## Tasks\n\n- [x] implement it\n- [~] follow-up note\n"
            "\n## Rationale\n\nLiteral [x] prose remains significant.\n"
        )
        completed = base.replace("- [ ] AC-1", "- [x] AC-1")
        task_variant = completed.replace("- [x] implement it", "- [ ] implement it")
        deferred_ac = completed.replace("AC-2: deferred", "AC-2: materially deferred")
        canonical = gardener_metadata.canonical_review_policy_body
        self.assertEqual(canonical(base.encode()), canonical(completed.encode()))
        self.assertEqual(canonical(completed.encode()), canonical(task_variant.encode()))
        self.assertNotEqual(canonical(completed.encode()), canonical(deferred_ac.encode()))

    def test_lane_selection_uses_only_serialization_paths_and_explicit_requests(self):
        prose_only = "# Change\n\n## Scope\n\nSecurity boundary latency build_pack.py events.jsonl.\n"
        paths = (
            "# Change\n\n## Serialization Points\n\n"
            "- `.wavefoundry/framework/scripts/review_policy.py`; "
            "`.wavefoundry/framework/scripts/tests/test_review_policy.py`; "
            "`.wavefoundry/framework/seeds/170-plan-feature.prompt.md`\n"
        )
        lanes, reasons = review_policy.select_required_review_lanes(
            requested_lanes=(), project_lanes=(), change_texts=(prose_only, paths)
        )
        # RE-PINNED for per-document adoption. This previously asserted that
        # one document's declaration switched prose scoring off for the WHOLE
        # wave, so the un-migrated sibling contributed nothing. That was the
        # reported defect at wave scope: migrating one plan silently removed a
        # different plan's coverage. Each document is now scored in its own
        # mode and the results union, so the declaring document contributes its
        # exact path roster AND the prose sibling keeps its fallback lanes.
        self.assertEqual(
            lanes,
            (
                "code-reviewer",
                "qa-reviewer",
                "docs-contract-reviewer",
                "release-reviewer",
            ),
        )
        self.assertTrue(
            any("fallback" in r for r in reasons["release-reviewer"]),
            "the sibling's lane must be labelled a fallback, never presented "
            "as a declared-target match",
        )
        # Still true, and independent of adoption: `events.jsonl` contains the
        # substring `.js` but is not a JavaScript target, so no JS-driven lane
        # is recruited by it.
        self.assertNotIn(
            "events.jsonl",
            " ".join(r for rs in reasons.values() for r in rs),
        )

        # An UN-MIGRATED wave (no admitted change declares any target) keeps its
        # legacy coverage instead of dropping to nothing. This assertion was
        # inverted before the delivery review: it required a prose-only corpus to
        # recruit nothing, and the AC-2 census then measured what that costs —
        # 775 change docs losing lanes, zero gaining any, and five of six
        # non-closed change docs at an EMPTY roster. Silent loss of all review is
        # a worse failure than the over-recruitment this change removes, so prose
        # scoring survives exactly where nothing better exists, and only there.
        requested, reasons = review_policy.select_required_review_lanes(
            requested_lanes=("security-reviewer", "performance-reviewer"),
            project_lanes=(), change_texts=(prose_only,)
        )
        self.assertIn("performance-reviewer", requested)
        self.assertIn("security-reviewer", requested)
        self.assertIn("release-reviewer", requested)
        self.assertTrue(
            all(
                "fallback" in reason
                for reason in reasons["release-reviewer"]
            ),
            "a legacy-fallback lane must be labelled as one, never presented as "
            "a declared-target match",
        )

    @staticmethod
    def _roster(serialization_points: str) -> tuple[str, ...]:
        doc = (
            "# Change\n\n## Serialization Points\n\n"
            f"{serialization_points}\n\n## Next\n"
        )
        lanes, _ = review_policy.select_required_review_lanes(
            requested_lanes=(), project_lanes=(), change_texts=(doc,)
        )
        return lanes

    def test_every_automatic_lane_is_selected_by_a_real_declared_path(self):
        """Delivery finding: `docs/architecture` matched only the bare string.

        `_path_token_matches` fell through to `path == token or
        path.endswith("/" + token)`, so a change declaring
        `docs/architecture/current-state.md` selected NOTHING and the
        architecture lane was unreachable from any real target. One case per
        automatic lane, so a lane can never again lose selection silently.
        """

        self.assertEqual(
            self._roster("- `docs/architecture/current-state.md`"),
            ("architecture-reviewer",),
        )
        self.assertEqual(
            self._roster("- `docs/ARCHITECTURE.md`"), ("architecture-reviewer",)
        )
        self.assertEqual(
            self._roster("- `.wavefoundry/framework/scripts/review_policy.py`"),
            ("code-reviewer",),
        )
        self.assertEqual(
            self._roster("- `.wavefoundry/framework/scripts/tests/test_x.py`"),
            ("code-reviewer", "qa-reviewer"),
        )
        self.assertEqual(
            self._roster("- `docs/specs/mcp-tool-surface.md`"),
            ("docs-contract-reviewer",),
        )
        self.assertEqual(
            self._roster("- `.wavefoundry/framework/scripts/upgrade_wavefoundry.py`"),
            ("code-reviewer", "release-reviewer"),
        )

    def test_path_extraction_is_layout_agnostic_across_target_repositories(self):
        """Delivery finding: a four-prefix allowlist blanked non-Wavefoundry repos.

        `_REPO_PATH_RE` accepted only `.wavefoundry/`, `docs/`, `src/` and
        `tests/`, so a Go, JS or Java target laid out as `lib/`, `pkg/`, `cmd/`
        or `internal/` extracted zero paths, selected zero automatic lanes, and
        emitted no diagnostic at all.
        """

        for declared in (
            "- `lib/foo.py`",
            "- `pkg/x.go`",
            "- `app/main.ts`",
            "- `internal/service/handler.py`",
            "- `cmd/tool/main.go`",
        ):
            with self.subTest(declared=declared):
                self.assertEqual(self._roster(declared), ("code-reviewer",))
        self.assertEqual(
            review_policy.serialization_point_paths(
                "## Serialization Points\n\n- `lib/foo.py`\n\n## Next\n"
            ),
            ("lib/foo.py",),
        )

    def test_an_undeclared_plan_keeps_its_coverage_instead_of_dropping_to_zero(self):
        """Delivery finding: path-only scoring was retroactive.

        Measured over the corpus, 775 change docs lost lanes and none gained
        any, and five of six non-closed change docs fell to an EMPTY roster,
        because every plan authored before the explicit-path contract describes
        its targets in prose. An un-migrated plan must keep the coverage it had.
        """

        undeclared = (
            "# Change\n\n## Scope\n\nTouches framework/scripts/ and tests/ and "
            "a regression harness.\n\n## Serialization Points\n\n"
            "- Serialize edits to the runner through the runner workstream.\n"
        )
        self.assertEqual(
            review_policy.serialization_point_paths(undeclared), (),
            "prose Serialization Points declare no machine-readable target",
        )
        lanes, reasons = review_policy.select_required_review_lanes(
            requested_lanes=(), project_lanes=(), change_texts=(undeclared,)
        )
        self.assertIn("code-reviewer", lanes)
        self.assertIn("qa-reviewer", lanes)
        self.assertTrue(
            any("fallback" in r for rs in reasons.values() for r in rs),
            "the fallback must be visible in the reason strings, not silent",
        )
        # The retired lanes stay request-only even on the fallback path.
        self.assertNotIn("security-reviewer", lanes)
        self.assertNotIn("performance-reviewer", lanes)

    def test_slashed_prose_is_not_mistaken_for_a_declared_target(self):
        """A misclassified declaration silently suppresses the fallback.

        `the runner/test corpus` and `dashboard/index activity` are English, not
        paths. Reading them as declared targets is worse than ignoring them,
        because a document counted as DECLARED loses the undeclared fallback and
        can end up with no required lanes at all.
        """

        body = (
            "## Serialization Points\n\n- Do not edit the runner/test corpus; "
            "freeze source/inventory and stop dashboard/index activity.\n\n## X\n"
        )
        self.assertEqual(review_policy.serialization_point_paths(body), ())
        declared = "## Serialization Points\n\n- `docs/architecture/`\n\n## X\n"
        self.assertEqual(
            review_policy.serialization_point_paths(declared), ("docs/architecture/",),
            "an explicit directory declaration keeps its trailing separator",
        )

    def test_each_checkbox_transition_direction_is_pinned_independently(self):
        """Requirement 2 states seven directions; pin each rather than a subset."""

        def doc(ac_mark: str, ac_note: str, task_mark: str) -> bytes:
            return (
                "# Change\n\n## Acceptance Criteria\n\n"
                f"- [{ac_mark}] AC-1: required contract{ac_note}\n"
                f"\n## Tasks\n\n- [{task_mark}] implement it\n"
            ).encode()

        canonical = gardener_metadata.canonical_review_policy_body
        # The AC marker comparisons hold the LABEL byte-identical, so only the
        # marker can move the digest. Varying the note as well would let this
        # test pass on a canonicalizer that wrongly normalizes an AC `[~]`,
        # because the note text alone would still differ.
        note = " *operator removed this*"
        ac_open = canonical(doc(" ", note, " "))
        ac_done = canonical(doc("x", note, " "))
        ac_deferred = canonical(doc("~", note, " "))
        self.assertEqual(ac_open, ac_done, "AC [ ]->[x] must be free")
        self.assertNotEqual(ac_done, ac_deferred, "AC [x]->[~] must move the digest")
        self.assertNotEqual(ac_deferred, ac_done, "AC [~]->[x] must move the digest")
        self.assertNotEqual(
            ac_deferred,
            canonical(doc("~", " *operator removed this after review*", " ")),
            "editing a [~] rationale must move the digest",
        )
        for before, after in ((" ", "x"), ("x", "~"), ("~", "x"), ("~", " ")):
            with self.subTest(task_transition=f"{before}->{after}"):
                self.assertEqual(
                    canonical(doc(" ", "", before)),
                    canonical(doc(" ", "", after)),
                    "every task marker transition must be digest-neutral",
                )


if __name__ == "__main__":
    unittest.main()


class RecordkeepingChurnTests(unittest.TestCase):
    """Wave 1uprb / 1urlc: recordkeeping edits must not lapse approvals.

    Every assertion here is on the CANONICAL body, which is what both the
    digest and lane scoring consume. The negative halves matter as much as the
    positives: an over-applied exclusion converts a churn problem into a
    silent-coverage problem, which is strictly worse.
    """

    TEMPLATE_HANDOFF = "See `docs/agents/session-handoff.md` for current session state."

    def _doc(self, handoff=None, extra=""):
        handoff = self.TEMPLATE_HANDOFF if handoff is None else handoff
        return (
            "# T\n\nChange ID: `1abc-bug slug`\nStatus: planned\n"
            "Last verified: 2026-08-08\n\n"
            "## Rationale\n\nWhy.\n\n"
            "## Requirements\n\n1. A thing.\n\n"
            "## Acceptance Criteria\n\n- [ ] AC-1: A thing.\n\n"
            "## Tasks\n\n- [ ] Do it.\n\n"
            "## Risks\n\n| Risk | Mitigation |\n| --- | --- |\n| r | m |\n\n"
            f"## Session Handoff\n\n{handoff}\n{extra}"
        )

    def _canon(self, text):
        return gardener_metadata.canonical_review_policy_body(text.encode("utf-8"))

    def test_a_boilerplate_session_handoff_is_excluded(self):
        """AC-1. The measured-harmless half of the exclusion set."""

        base = self._canon(self._doc())
        edited = self._canon(self._doc(handoff=self.TEMPLATE_HANDOFF + "\n\nParked mid-wave."))
        # Assert the exclusion actually FIRED. An earlier revision compared a
        # pure function against itself on identical input, which passes under
        # `return body`.
        self.assertIn(
            gardener_metadata.SESSION_HANDOFF_SENTINEL, base.decode("utf-8"),
            "a boilerplate handoff must be replaced by its sentinel",
        )
        self.assertNotIn(
            self.TEMPLATE_HANDOFF, base.decode("utf-8"),
            "the template sentence itself must not survive canonicalization",
        )
        self.assertNotEqual(
            base, edited,
            "a substantive handoff body must still be digested; excluding the "
            "whole section would blind review to the 5 percent that use it",
        )

    def test_a_substantive_session_handoff_still_churns(self):
        """AC-1 negative half. Over-application is the worse failure."""

        a = self._canon(self._doc(handoff="Blocked on operator decision about the release."))
        b = self._canon(self._doc(handoff="Unblocked; proceeding with the release."))
        self.assertNotEqual(
            a, b,
            "two different substantive handoffs must produce different canonical "
            "bodies, or an admission precondition could be deleted invisibly",
        )

    def test_the_boilerplate_match_is_exact_not_a_prefix(self):
        """AC-1b. Five real corpus documents begin with the template sentence.

        A `startswith` or `in` implementation swallows all five while still
        passing a negative test built from a wholly-different body, so the
        prefix case needs its own fixture.
        """

        plain = self._canon(self._doc())
        prefixed = self._canon(
            self._doc(handoff=self.TEMPLATE_HANDOFF + " Change doc scaffolded 2026-06-05.")
        )
        self.assertNotEqual(
            plain, prefixed,
            "a body that BEGINS with the template sentence and continues with "
            "substantive text must not be treated as boilerplate",
        )

    def test_the_boilerplate_match_survives_carrier_normalization(self):
        """AC-1a. Ordering is load-bearing and cannot fail loudly.

        If the body match runs before whitespace normalization, a CRLF checkout
        or a stray trailing space makes the boilerplate fail to match and the
        churn returns for exactly the population the carrier rules protect.
        That failure is silent, because a body that differs from the template
        is indistinguishable from an author who wrote something substantive.
        """

        plain = self._canon(self._doc())
        for label, variant in {
            "CRLF": self._doc().replace("\n", "\r\n"),
            "BOM": "﻿" + self._doc(),
            "one trailing space": self._doc(handoff=self.TEMPLATE_HANDOFF + " "),
            "no EOF newline": self._doc().rstrip("\n"),
        }.items():
            with self.subTest(carrier=label):
                self.assertEqual(
                    plain, self._canon(variant),
                    f"{label} must not defeat the boilerplate match",
                )

    def test_carrier_only_edits_do_not_move_the_canonical_body(self):
        """AC-2. Zero human intent, and a Windows checkout hits every document."""

        base = self._canon(self._doc(handoff="Substantive note here."))
        doc = self._doc(handoff="Substantive note here.")
        for label, variant in {
            "CRLF": doc.replace("\n", "\r\n"),
            "BOM": "﻿" + doc,
            "trailing newline added": doc + "\n",
            "trailing newline removed": doc.rstrip("\n"),
            "one trailing space": doc.replace("Substantive note here.", "Substantive note here. "),
        }.items():
            with self.subTest(carrier=label):
                self.assertEqual(base, self._canon(variant), f"{label} must not churn")

    def test_all_trailing_whitespace_outside_a_fence_is_noise(self):
        """AC-2. A hard line break changes layout, not the claim.

        An earlier revision preserved runs of two or more spaces because they
        are a markdown hard break. The digest exists to detect changes to the
        approved contract, and a hard break changes rendering rather than
        words, so the split was arbitrary AND backwards: it normalized the 2
        lines in this corpus carrying a lone trailing space while leaving the
        24 carrying a run of two or more to churn.
        """

        doc = self._doc(handoff="Substantive note here.")
        for label, trailer in {"one space": " ", "hard break": "  ", "tab": "\t"}.items():
            with self.subTest(trailing=label):
                self.assertEqual(
                    self._canon(doc),
                    self._canon(doc.replace("Substantive note here.",
                                            "Substantive note here." + trailer)),
                    f"a trailing {label} outside a fence must not move the digest",
                )

    def test_trailing_whitespace_inside_a_fence_is_preserved(self):
        """AC-2 negative half. In a fence the whitespace can be the subject.

        A change document demonstrating one-space versus two-space behaviour in
        a fenced example must not become indistinguishable from itself.
        """

        base = self._doc(handoff="Note.\n\n```\nexample line\n```")
        spaced = self._doc(handoff="Note.\n\n```\nexample line  \n```")
        self.assertNotEqual(
            self._canon(base), self._canon(spaced),
            "trailing whitespace inside a fence is content, not formatting",
        )

    def test_legacy_lane_matching_is_whitespace_independent(self):
        """AC-3a. Operator-directed semantics change, asserted in both directions.

        Four whole-document triggers carry a literal trailing space, so lane
        selection currently depends on invisible whitespace: a line ending
        `-bug ` recruits a lane and a line ending `-bug` does not. The trigger
        is the token, not the space.
        """

        with_space = review_policy._legacy_token_match("-bug ", "see 1abc-bug \nnext")
        bare_eol = review_policy._legacy_token_match("-bug ", "see 1abc-bug\nnext")
        self.assertIsNotNone(with_space, "the trailing-space form must keep matching")
        self.assertIsNotNone(
            bare_eol,
            "a bare token at end of line must ALSO match; this is the widening "
            "the operator chose, and asserting it positively is what stops it "
            "shipping as an unnoticed side effect of the whitespace rule",
        )

    def test_a_legacy_token_inside_a_word_still_does_not_match(self):
        """AC-3a guard. Boundary matching must not become substring matching."""

        # The falsifier must actually CONTAIN the token. An earlier revision
        # used "debugger", which does not contain "-bug" at all, so the
        # assertion held under substring search, under boundary search, and
        # with the lookahead deleted.
        self.assertIsNone(
            review_policy._legacy_token_match("-bug ", "see 1abc-bugfix notes\n"),
            "'-bug' inside '-bugfix' is a longer word, not a kind token",
        )
        self.assertIsNone(
            review_policy._legacy_token_match("-enh ", "see 1abc-enhanced notes\n"),
            "'-enh' inside '-enhanced' is not a kind token either",
        )

    def _digest(self, changes):
        return review_policy.policy_input_digest(
            wave_review={}, project_lanes=(), review_policies=None,
            changes=changes, requested_lanes=(),
        )

    def test_reordering_the_changes_payload_does_not_move_the_digest(self):
        """AC-3. Pure bookkeeping with no content change at all.

        `change_ids` are collected from wave.md in DOCUMENT order, so swapping
        two admitted entries moved the digest and lapsed every approval.
        """

        a = ("1aaa-bug alpha", "bug", self._doc().encode("utf-8"))
        b = ("1bbb-enh beta", "enh", self._doc(handoff="Other.").encode("utf-8"))
        self.assertEqual(
            self._digest([a, b]), self._digest([b, a]),
            "reordering admitted changes must not move the digest",
        )
        self.assertNotEqual(
            self._digest([a, b]), self._digest([a]),
            "removing a change is a real contract change and must still move it",
        )

    def test_the_declined_sections_still_churn(self):
        """AC-4. The guard against over-applying the exclusion pattern.

        Each of these was measured on both policy-output channels and declined.
        Excluding any of them would convert a churn problem into a silent
        coverage problem, which is strictly worse.
        """

        base = self._doc()
        for label, edited in {
            "Risks": base.replace("| r | m |", "| r | m |\n| r2 | m2 |"),
            "Rationale": base.replace("Why.", "Why, restated."),
            "Requirements": base.replace("1. A thing.", "1. A different thing."),
            "Acceptance Criteria label": base.replace(
                "- [ ] AC-1: A thing.", "- [ ] AC-1: A narrower thing."
            ),
            # The three AC-4 names that the fixture previously had no section
            # for, so the AC claimed four and the test covered one.
            "AC Priority rationale": base.replace(
                "## Risks", "## AC Priority\n\n| AC | Priority | Rationale |\n| - | - | - |\n| AC-1 | required | Because it is the reported defect. |\n\n## Risks"
            ),
            "Affected Architecture Docs": base.replace(
                "## Risks", "## Affected Architecture Docs\n\nN/A with rationale.\n\n## Risks"
            ),
            "Serialization Points prose": base.replace(
                "## Risks", "## Serialization Points\n\nProse explaining why nothing is declared.\n\n## Risks"
            ),
        }.items():
            with self.subTest(section=label):
                self.assertNotEqual(
                    self._canon(base), self._canon(edited),
                    f"{label} is load-bearing and must keep churning",
                )

    def test_an_excluded_region_is_never_partially_canonicalized(self):
        """AC-6. Anti-leak: the region is replaced WHOLE, never in part.

        Exercised on `## Progress Log`, because that is the only excluded
        region whose body can carry a payload and still be excluded. The
        Session Handoff exclusion is exact-equality, so any payload defeats the
        match by construction and the region simply stays digested -- which the
        AC-1b and AC-7 tests already pin.

        An earlier revision of this test looped over three payloads and never
        used the loop variable, so it made three byte-identical assertions on a
        plain document. It was vacuous AND self-contradictory: inserting a
        payload into a boilerplate handoff makes it non-boilerplate, so the
        sentinel assertion could never have held.
        """

        for payload in (
            "- `.wavefoundry/framework/scripts/upgrade_wavefoundry.py`",
            "**Review targets (repo-relative paths):**\n\n- `docs/specs/`",
            "windows security upgrade migration schema trust boundary",
        ):
            with self.subTest(payload=payload[:34]):
                doc = self._doc().replace(
                    "## Session Handoff",
                    f"## Progress Log\n\n| Date | Update | Evidence |\n| - | - | - |\n| d | {payload} | e |\n\n## Session Handoff",
                )
                canon = self._canon(doc).decode("utf-8")
                self.assertIn(
                    gardener_metadata.PROGRESS_LOG_SENTINEL, canon,
                    "the excluded region must be replaced by its sentinel",
                )
                self.assertNotIn(
                    payload.split("\n")[0], canon,
                    "no part of the excluded body may survive; a partial "
                    "replacement leaves a half-canonicalized document",
                )

    def test_the_template_sentence_producers_stay_in_step(self):
        """P2 from the security lane: three producers, nothing keeping them aligned.

        `SESSION_HANDOFF_TEMPLATE_BODY`, the shipped `plan-template.md`, and the
        `wf_new_*` literal all carry this sentence. They are byte-identical
        today and Requirement 1 says they must stay so, but no test asserted it.
        The dangerous direction is not narrowing: if the sentence ever gained a
        token like `docs/prompts/`, the exclusion would silently strip a lane
        trigger from roughly 700 documents.
        """

        repo_root = Path(__file__).resolve().parents[4]
        template = (repo_root / "docs/plans/plan-template.md").read_text("utf-8")
        self.assertIn(
            gardener_metadata.SESSION_HANDOFF_TEMPLATE_BODY, template,
            "docs/plans/plan-template.md must ship the exact template sentence",
        )
        # Measured against the REAL producers rather than a hand-listed token
        # set: what matters is that swapping the sentence for its sentinel
        # changes no policy output. The sentence does contain `docs/agents/...`,
        # so a hand-rolled "carries no path" assertion would be both wrong and
        # beside the point.
        sentence = gardener_metadata.SESSION_HANDOFF_TEMPLATE_BODY
        sentinel = gardener_metadata.SESSION_HANDOFF_SENTINEL
        for label, text in {"sentence": sentence, "sentinel": sentinel}.items():
            lanes, _ = review_policy.select_required_review_lanes(
                requested_lanes=(), project_lanes=(), change_texts=(text,),
            )
            triggers = review_policy.extract_full_council_triggers((text,))
            self.assertEqual(
                (tuple(lanes), tuple(triggers)), ((), ()),
                f"the {label} must recruit no lane and fire no council trigger, "
                "or replacing one with the other would move policy output on "
                "roughly 700 documents",
            )

    def test_an_ambiguous_or_absent_heading_never_raises(self):
        """AC-7. Loud is a diagnostic, never an exception from a pure helper.

        `canonical_review_policy_body` has three call sites and none wraps it,
        so raising would take down lane selection, digest computation and
        prepare on ordinary author input. Zero matches is the NORMAL absent
        case: 89 of 825 documents carry no such section at all.
        """

        absent = self._doc().split("## Session Handoff")[0]
        duplicated = self._doc() + "\n## Session Handoff\n\nSecond one.\n"
        variant = self._doc().replace("## Session Handoff", "## Session Handoff (notes)")
        for label, text in {
            "absent": absent, "duplicated": duplicated, "variant heading": variant,
        }.items():
            with self.subTest(shape=label):
                try:
                    canon = self._canon(text)
                except Exception as exc:  # noqa: BLE001
                    self.fail(f"{label} must not raise from the canonicalizer; got {exc!r}")
                self.assertNotIn(
                    gardener_metadata.SESSION_HANDOFF_SENTINEL,
                    canon.decode("utf-8"),
                    f"{label} must degrade to a digested region, not a partial one",
                )

    def test_an_ambiguous_heading_is_reported_loudly(self):
        """AC-7's loud half. A silent degrade returns the churn unexplained.

        The normalizer cannot raise, because its three call sites have no
        handler, so the loudness lives in a detector the caller surfaces
        through the diagnostic channel that already exists.
        """

        duplicated = self._doc() + "\n## Session Handoff\n\nSecond one.\n"
        problems = gardener_metadata.ambiguous_excluded_headings(duplicated)
        self.assertTrue(problems, "a duplicated excluded heading must be reported")
        self.assertIn("Session Handoff", problems[0])
        self.assertIn(
            "was NOT applied", problems[0],
            "the message must say the exclusion did not apply, or the operator "
            "cannot connect the churn to its cause",
        )

    def test_absent_and_single_headings_are_never_reported(self):
        """AC-7 negative half. Zero matches is NORMAL, not malformed.

        89 of 825 change documents carry no Session Handoff section at all.
        Conflating absent with duplicated is the defect the shipped
        `len(matches) != 1` predicate has, and reporting it would produce a
        diagnostic on 89 healthy documents.
        """

        for label, text in {
            "single heading": self._doc(),
            "absent section": self._doc().split("## Session Handoff")[0],
        }.items():
            with self.subTest(shape=label):
                self.assertEqual(
                    gardener_metadata.ambiguous_excluded_headings(text), (),
                    f"{label} must be silent",
                )

    def test_a_variant_heading_is_reported_loudly(self):
        """AC-7's other half, which the first implementation left silent.

        A duplicate heading is the loud shape; a VARIANT is the quiet one. The
        author sees only that their narration started superseding the receipt,
        with nothing naming the cause.
        """

        for variant in (
            "## Progress Log (delivery)",
            "### Progress Log",
            "## progress log",
            "## Session Handoff (notes)",
        ):
            with self.subTest(heading=variant):
                base = self._doc()
                doc = (
                    base.replace("## Session Handoff", variant)
                    if "Handoff" in variant
                    else base.replace("## Risks", f"{variant}\n\n| d | u | e |\n\n## Risks")
                )
                problems = gardener_metadata.ambiguous_excluded_headings(doc)
                self.assertTrue(
                    problems, f"`{variant}` disables its exclusion and must be named"
                )
                self.assertIn("was NOT", " ".join(problems))

    def test_the_detector_is_fence_aware(self):
        """Mutation-found: a fenced example must not raise a blocking diagnostic.

        The detector's output flows into `_prepare_policy_state`'s
        `(None, errors)`, which blocks receipt publication. A change document
        that DEMONSTRATES a duplicate heading inside a fenced example would
        otherwise block its own prepare. This document class is exactly what a
        plan about heading hazards looks like.
        """

        fenced = self._doc().replace(
            "## Risks",
            "```\n## Progress Log\n## Progress Log\n```\n\n## Risks",
        )
        self.assertEqual(
            gardener_metadata.ambiguous_excluded_headings(fenced), (),
            "headings inside a fence are examples, not structure",
        )
