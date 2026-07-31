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
    def test_evaluator_version_two_is_the_shipped_transition_boundary(self):
        self.assertEqual(review_policy.REVIEW_POLICY_EVALUATOR_VERSION, 2)

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
        for enabled, expected in ((True, "universal"), (False, "disabled")):
            with self.subTest(enabled=enabled), tempfile.TemporaryDirectory() as tmp:
                root, open_md, closed_md = self._repo(tmp, enabled=enabled)
                closed_before = closed_md.read_bytes()
                closed_events = review_evidence.review_event_path(closed_md)
                closed_events_before = closed_events.read_bytes()
                plan = review_policy_upgrade.plan_review_policy_upgrade(root)
                result = review_policy_upgrade.apply_review_policy_upgrade(root, plan)
                self.assertEqual(result["delivery_mode"], expected)
                self.assertIn("review-policy-reprepare-required: true", open_md.read_text("utf-8"))
                self.assertEqual(closed_md.read_bytes(), closed_before)
                self.assertEqual(closed_events.read_bytes(), closed_events_before)
                projected = open_md.read_text("utf-8")
                self.assertIn("operator-signoff", projected)
                self.assertEqual(
                    "wave-council-delivery" in projected,
                    enabled,
                )

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
    def test_measured_baseline_keeps_universal_default(self):
        self.assertEqual(review_policy.FRESH_INSTALL_DELIVERY_MODE, "universal")
        self.assertFalse(
            review_policy.targeted_default_adoption_allowed(
                council_reduction=0.0,
                specialist_lane_reduction=0.0,
                omitted_required_lanes=0,
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

    def test_policy_digest_ignores_only_one_canonical_gardener_date(self):
        def digest(body: bytes) -> str:
            return review_policy.policy_input_digest(
                wave_review={"enabled": True, "delivery_mode": "universal"},
                project_lanes=(),
                review_policies={},
                changes=(("1abc-bug example", "bug", body),),
                requested_lanes=(),
            )

        base = b"# Change\nOwner: Engineering\nLast verified: 2026-07-29\n\n## Requirements\n\nKeep this.\n"
        next_day = base.replace(b"2026-07-29", b"2026-07-30")
        substantive = base.replace(b"Keep this.", b"Keep that.")
        self.assertEqual(digest(base), digest(next_day))
        self.assertNotEqual(digest(base), digest(substantive))

    def test_policy_and_drift_consumers_share_the_same_narrow_boundary(self):
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


if __name__ == "__main__":
    unittest.main()
