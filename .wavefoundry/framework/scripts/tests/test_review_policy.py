#!/usr/bin/env python3
from __future__ import annotations

import json
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
            wavefoundry_live = root / ".wavefoundry/README.md"
            wavefoundry_live.parent.mkdir(parents=True, exist_ok=True)
            wavefoundry_live.write_text(
                "# Local framework guidance\n\nRun the reviewer loop.\n",
                encoding="utf-8",
            )
            generated_paths = (
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
                wavefoundry_live: wavefoundry_live.read_bytes(),
            }
            with self.assertRaises(ValueError) as caught:
                review_policy_reconcile.plan_reconciliation(root)
            message = str(caught.exception)
            self.assertIn("docs/agents/wave-council.md", message)
            self.assertIn(".wavefoundry/README.md", message)
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


class ReviewPolicyUpgradeTests(unittest.TestCase):
    def test_evaluator_version_four_is_the_shipped_transition_boundary(self):
        """Deliberate tripwire: update it consciously on every evaluator bump.

        v3 to v4 (wave 1ui1d): lane selection now scores only declared
        Serialization Points paths. The pin moves with the constant, it is
        never deleted, and `test_server_tools.py` carries the paired public
        transition test.
        """

        self.assertEqual(review_policy.REVIEW_POLICY_EVALUATOR_VERSION, 4)

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
        lanes, _ = review_policy.select_required_review_lanes(
            requested_lanes=(), project_lanes=(), change_texts=(prose_only, paths)
        )
        # A wave that has ADOPTED the contract scores paths only: the prose
        # sibling contributes nothing, so `build_pack.py` and `events.jsonl`
        # recruit neither the release nor a JavaScript lane.
        self.assertEqual(lanes, ("code-reviewer", "qa-reviewer", "docs-contract-reviewer"))

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
