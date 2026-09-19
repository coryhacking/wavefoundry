"""Golden snapshot of the prepare / review / close response envelopes (wave 1y0h0 / 1y044).

`1y044` extracts the lifecycle checks into ordered gate units with no behavior
change. AC-1's oracle is this file: three fixture repositories are driven
through the three response functions in every mode the change touches, each
envelope is serialized deterministically, and the result is compared
byte-for-byte to the committed fixture ``fixtures/lifecycle-gate-golden.json``.
Regeneration is explicit and happens only under ``WF_UPDATE_LIFECYCLE_GOLDEN=1``.
Replacing a fixture that already exists needs ``WF_OVERWRITE_LIFECYCLE_GOLDEN=1``
beside it, so an ambient variable cannot rewrite drift into a committed fixture
and report success (wave 1yd99).

The capture is taken at the response-function level, not through the registered
handlers, so handler telemetry never enters the golden. Three producers reach a
mutating envelope that ``dry_run`` never touches and are patched here because
their output is not a function of the fixture:

* ``_run_post_write_lint`` — ``_attach_lint_to_response`` calls it on every
  successful mutating envelope, and it spawns ``run_validate_changed`` as a
  real subprocess whose payload varies with git availability and interpreter
  resolution. It returns early on ``dry_run`` and on error envelopes, so the
  patch is load-bearing only on captures that reach a successful envelope.
* ``_auto_populate_memory_for_wave`` — mints record ids from the clock.
* ``_maybe_optimize_index_on_close`` — reports byte counts.

The last two fire only on a close that completes its transition. No fixture
here completes one, so they are belt-and-braces; patching them keeps the golden
deterministic if a later fixture does.
"""
from __future__ import annotations

import copy
import json
import os
import shutil
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from server_tools_support import _make_repo, load_server

TESTS_DIR = Path(__file__).resolve().parent
GOLDEN_PATH = TESTS_DIR / "fixtures" / "lifecycle-gate-golden.json"
UPDATE_ENV = "WF_UPDATE_LIFECYCLE_GOLDEN"
OVERWRITE_ENV = "WF_OVERWRITE_LIFECYCLE_GOLDEN"
FIXTURE_SCHEMA = "1"

# Publication of the prepare policy state is guarded on the workflow config
# carrying a `wave_review` block; `_make_repo` writes only the id policy, so a
# fixture that must reach `_publish_prepare_policy_state` declares one here.
_WAVE_REVIEW_CONFIG = {
    "lifecycle_id_policy": {"epoch_utc": "2020-02-02T02:02:00Z", "hour_offset": 0},
    # The exact enablement/mode truth table normalize_wave_review_policy
    # enforces. A block missing either key is INVALID, not absent, and every
    # lifecycle response then short-circuits on review_policy_reprepare_required
    # before reaching any span this change extracts.
    "wave_review": {"enabled": True, "delivery_mode": "targeted"},
    "required_review_lanes": ["code-reviewer"],
}


def _write_config(root: Path, config: dict) -> None:
    (root / "docs" / "workflow-config.json").write_text(
        json.dumps(config, sort_keys=True), encoding="utf-8"
    )


def _change_doc(change_id: str) -> str:
    return (
        f"# {change_id}\n\n"
        "## Rationale\n\nFixture change document.\n\n"
        "## Requirements\n\n1. Fixture requirement.\n\n"
        "## Scope\n\nFixture scope.\n\n"
        "## Acceptance Criteria\n\n- [x] AC-1: fixture criterion.\n\n"
        "## Tasks\n\n- [x] Fixture task.\n\n"
        "## AC Priority\n\n"
        "| AC   | Priority | Rationale |\n"
        "| ---- | -------- | --------- |\n"
        "| AC-1 | required | fixture   |\n\n"
        "## Progress Log\n\n"
        "| Date | Update | Evidence |\n"
        "| ---- | ------ | -------- |\n"
        "| 2026-01-01 | Fixture | this document |\n\n"
        "## Decision Log\n\n"
        "| Date | Decision | Reason | Alternatives |\n"
        "| ---- | -------- | ------ | ------------ |\n"
        "| 2026-01-01 | Fixture | fixture | fixture |\n\n"
        "## Risks\n\n"
        "| Risk | Mitigation |\n"
        "| ---- | ---------- |\n"
        "| Fixture | Fixture |\n"
    )


def _build_one(srv, root: Path, slug: str, *, status: str) -> tuple[Path, str]:
    """Create one declared wave through the real producers.

    `wf_create_wave_response` writes the skeleton a declared wave actually
    needs: the `review-evidence-source` header, exactly one Finding Synthesis
    projection with its markers, the Review Evidence section, and an empty
    sibling ledger. Hand-authoring that shape is what a fixture must not do —
    every field the validator checks would then be a guess.
    """
    created = srv.wf_create_wave_response(root, slug, mode="create")["data"]
    wave_id = created["wave_id"]
    wave_md = root / created["path"]
    change_id = f"{wave_id.split()[0]}z-ref fixture-change"
    (wave_md.parent / f"{change_id}.md").write_text(_change_doc(change_id), encoding="utf-8")
    srv.wf_add_change_response(root, wave_id, change_id, mode="create")
    if status != "planned":
        text = wave_md.read_text(encoding="utf-8")
        wave_md.write_text(
            text.replace("Status: planned", f"Status: {status}", 1), encoding="utf-8"
        )
    return wave_md, wave_id


def _approval_evidence(actor: str) -> dict:
    return {
        "observed": f"{actor} verified the fixture scope",
        "artifact_or_test_id": f"lifecycle-golden-fixture:{actor}",
    }


_APPROVAL_INTEGRITY = {
    "test_ran_without_unintended_skip": True,
    "public_path_reached": True,
    "boundary_values_realistic": True,
    "assertions_non_vacuous": True,
    "known_bad_detected": True,
    "known_bad_detection_method": "fixture control",
}


def seed_state(srv, root: Path, wave_id: str, approvals: tuple[str, ...]) -> None:
    """Drive the real producers so fixture state is what production writes.

    The receipt comes from a real ``ready`` pass and the approvals from real
    review events, rather than from hand-authored JSONL that can drift from
    the record shapes the readers expect.
    """
    with patch.object(srv, "run_validate", _stub_validate), \
         patch.object(srv, "run_garden", _stub_garden), \
         patch.object(srv, "_run_post_write_lint", lambda *a, **k: {"mode": "stubbed"}):
        srv.wf_prepare_wave_response(root, wave_id, mode="ready")
        if approvals:
            # A wave carrying approvals must also carry the run record for that
            # phase; without it the readers reject the marked wave and every
            # response short-circuits before the spans under extraction.
            srv.wf_review_event_response(
                root,
                wave_id,
                "run",
                "wave-council",
                "lifecycle-golden-readiness-run",
                mode="create",
                run_kind="readiness",
                fresh_context=True,
                independent=True,
                evidence=_approval_evidence("wave-council"),
                integrity_checks=dict(_APPROVAL_INTEGRITY),
            )
        for signoff_key in approvals:
            actor = "wave-council" if signoff_key.startswith("wave-council") else signoff_key
            srv.wf_review_event_response(
                root,
                wave_id,
                "approval",
                actor,
                f"lifecycle-golden-{signoff_key}",
                mode="create",
                signoff_key=signoff_key,
                approval_phase="readiness",
                fresh_context=True,
                independent=True,
                evidence=_approval_evidence(actor),
                integrity_checks=dict(_APPROVAL_INTEGRITY),
            )


def _stub_validate(root, *args, **kwargs):
    return {"passed": True, "errors": [], "warnings": [], "output": "docs-lint: ok\n"}


def _stub_garden(root, *args, **kwargs):
    # Mirrors run_garden's real summary contract: a passing run that updated
    # nothing. Keeping the producer's field names means a change to that
    # contract shows up here rather than being masked by a convenient stub.
    return {
        "passed": True,
        "files_updated": 0,
        "updated": [],
        "output": "docs-gardener: ok\n",
    }


def _scrub(node, root: Path):
    """Replace absolute fixture paths so the golden is machine-independent."""
    if isinstance(node, dict):
        return {key: _scrub(value, root) for key, value in sorted(node.items())}
    if isinstance(node, list):
        return [_scrub(item, root) for item in node]
    if isinstance(node, str):
        return node.replace(str(root), "<repo>")
    return node


def build_fixtures(base: Path, srv) -> dict[str, tuple[Path, str]]:
    """The three fixture repositories AC-1 names, at three different depths.

    Each is a real declared wave built by the create/admit producers, then
    seeded by real prepare and review events, so the golden exercises the
    spans this change extracts rather than three copies of one early return:

    * ``planned_with_verdict`` holds the council signoff, so prepare carries
      past the activation cluster into the readiness check.
    * ``active_typed_approvals`` additionally holds its required lane. That
      extra lane separates it from ``planned_with_verdict`` at prepare only.
    * ``missing_lane`` records nothing and blocks at activation, which sits
      after publication, so its mutating capture still reaches all three
      writes.

    What the captures actually show, re-derived from the committed golden with
    each fixture's own wave identifier normalized away (wave 1yd99). The review
    capture is identical across all three. ``active_typed_approvals`` and
    ``planned_with_verdict`` are identical at both close captures and are
    separated only at prepare; ``missing_lane`` is separated at close as well.
    Raw, no two fixtures are byte-identical anywhere, because the identifier
    differs. An earlier version of this docstring claimed the extra lane makes
    review and close reach the shared delivery evaluation, which the captures do
    not show.
    """
    # Freeze producer inputs, not response IDs: receipts digest those IDs too.
    # Reset the producer's process-local allocation floor for each independent
    # fixture batch, then restore it so this suite cannot affect other tests.
    clock = datetime(2026, 9, 18, 16, 40, tzinfo=timezone.utc)
    ids = srv._lifecycle_module()
    with patch.object(ids, "current_utc_time", return_value=clock), \
         patch.object(ids, "_last_assigned_prefix", None), \
         patch.object(ids, "_last_assigned_policy", None):
        fixtures: dict[str, tuple[Path, str]] = {}

        planned = _make_repo(base / "planned_with_verdict")
        _write_config(planned, _WAVE_REVIEW_CONFIG)
        _, planned_id = _build_one(srv, planned, "fixture-planned", status="planned")
        seed_state(srv, planned, planned_id, ("wave-council-readiness",))
        fixtures["planned_with_verdict"] = (planned, planned_id)

        active = _make_repo(base / "active_typed_approvals")
        _write_config(active, _WAVE_REVIEW_CONFIG)
        _, active_id = _build_one(srv, active, "fixture-active", status="active")
        seed_state(srv, active, active_id, ("wave-council-readiness", "code-reviewer"))
        fixtures["active_typed_approvals"] = (active, active_id)

        missing = _make_repo(base / "missing_lane")
        _write_config(missing, _WAVE_REVIEW_CONFIG)
        _, missing_id = _build_one(srv, missing, "fixture-missing-lane", status="planned")
        seed_state(srv, missing, missing_id, ())
        fixtures["missing_lane"] = (missing, missing_id)

        return fixtures


def capture(srv, root: Path, wave_id: str) -> dict:
    """Every envelope `1y044` touches, on one fixture repository.

    Each mutating capture runs on a fresh copy, so an earlier write never
    changes a later capture's input.
    """
    captures: dict[str, object] = {}

    def _run(label, fn, mode_kwargs):
        # Response labels contain colons; Windows directory names cannot.
        directory_label = label.replace(":", "-")
        work = root.parent / f"{root.name}__{directory_label}"
        if work.exists():
            shutil.rmtree(work)
        shutil.copytree(root, work)
        with patch.object(srv, "run_validate", _stub_validate), \
             patch.object(srv, "run_garden", _stub_garden), \
             patch.object(srv, "_run_post_write_lint", lambda *a, **k: {"mode": "stubbed"}), \
             patch.object(srv, "_auto_populate_memory_for_wave", lambda *a, **k: None), \
             patch.object(srv, "_maybe_optimize_index_on_close", lambda *a, **k: None):
            response = fn(work, wave_id, **mode_kwargs)
        captures[label] = _scrub(response, work)

    _run("prepare:dry_run", srv.wf_prepare_wave_response, {"mode": "dry_run"})
    _run("prepare:ready", srv.wf_prepare_wave_response, {"mode": "ready"})
    _run("prepare:create", srv.wf_prepare_wave_response, {"mode": "create"})
    _run("review:implementation", srv.wf_review_wave_response, {"phase": "implementation"})
    _run("close:dry_run", srv.wf_close_wave_response, {"mode": "dry_run"})
    _run("close:create", srv.wf_close_wave_response, {"mode": "create"})
    return captures


def render(document) -> bytes:
    text = json.dumps(document, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
    return text.replace("\r\n", "\n").encode("utf-8")


def check_golden(document: dict, fixture_path: Path, environ=None) -> list[str]:
    env = os.environ if environ is None else environ
    rendered = render(document)
    if env.get(UPDATE_ENV) == "1":
        # Wave 1yd99: regenerating over an existing committed fixture rewrites
        # drift into it and reports success, so an ambient variable exported in a
        # shell or CI job silently disarms this oracle.  The refusal keys on
        # fixture existence, so generating a fixture that does not yet exist is
        # unaffected and the landed known-bad below stays green.
        if fixture_path.exists() and env.get(OVERWRITE_ENV) != "1":
            return [
                f"lifecycle golden refused to overwrite {fixture_path}: "
                f"set {OVERWRITE_ENV}=1 beside {UPDATE_ENV}=1 to replace a committed fixture"
            ]
        fixture_path.parent.mkdir(parents=True, exist_ok=True)
        fixture_path.write_bytes(rendered)
        return []
    if not fixture_path.exists():
        return [
            f"lifecycle golden missing: {fixture_path} "
            f"(run with {UPDATE_ENV}=1 to generate it)"
        ]
    on_disk = fixture_path.read_bytes()
    if on_disk == rendered:
        return []
    try:
        expected = json.loads(on_disk.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return [f"lifecycle golden unreadable: {fixture_path}: {exc}"]
    lines: list[str] = []
    _diff(expected, json.loads(rendered.decode("utf-8")), "", lines)
    return lines or [f"lifecycle golden differs byte-wise at {fixture_path}"]


def _diff(expected, actual, path: str, lines: list[str]) -> None:
    if isinstance(expected, dict) and isinstance(actual, dict):
        for key in sorted(set(expected) | set(actual)):
            child = f"{path}/{key}" if path else key
            if key not in actual:
                lines.append(f"removed {child}")
            elif key not in expected:
                lines.append(f"added {child}")
            else:
                _diff(expected[key], actual[key], child, lines)
    elif isinstance(expected, list) and isinstance(actual, list):
        if len(expected) != len(actual):
            lines.append(f"length {path}: {len(expected)} -> {len(actual)}")
        for index, (exp, act) in enumerate(zip(expected, actual)):
            _diff(exp, act, f"{path}[{index}]", lines)
        # Name the elements the zip above cannot reach, so a diff always says
        # WHAT was added or removed rather than only that a count moved.
        for index in range(len(actual), len(expected)):
            lines.append(f"removed {path}[{index}]: {expected[index]!r}")
        for index in range(len(expected), len(actual)):
            lines.append(f"added {path}[{index}]: {actual[index]!r}")
    elif expected != actual:
        lines.append(f"changed {path}: {expected!r} -> {actual!r}")


class LifecycleGoldenTests(unittest.TestCase):
    """AC-1: the envelopes are unchanged by the extraction."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

    def surface(self) -> dict:
        fixtures = build_fixtures(self.base, self.srv)
        document = {"fixture_schema": FIXTURE_SCHEMA, "fixtures": {}}
        for name, (root, wave_id) in sorted(fixtures.items()):
            document["fixtures"][name] = capture(self.srv, root, wave_id)
        return document

    def test_lifecycle_envelopes_match_the_committed_golden(self):
        # 1yd98 AC-8: an empty environment mapping, not the ambient one.  The
        # helper rewrites the fixture and returns clean whenever the regeneration
        # variable is set, so with the ambient mapping this comparison can satisfy
        # itself and, worse, bake drift into the committed fixture.  This is the
        # only call in the suite that compares against the committed golden, so
        # repointing it here removes the ambient path entirely.
        lines = check_golden(self.surface(), GOLDEN_PATH, environ={})
        self.assertEqual(lines, [], "lifecycle envelopes drifted:\n" + "\n".join(lines))

    def test_regeneration_refuses_to_overwrite_a_committed_fixture(self):
        """1yd99 AC-2: the ambient variable alone cannot rewrite a fixture that exists.

        Proven in a temp fixture so the committed file is never touched.
        """
        import tempfile

        document = {"probe": "one"}
        with tempfile.TemporaryDirectory() as tmp:
            fixture = Path(tmp) / "golden.json"
            # Generating a fixture that does not yet exist is unchanged.
            self.assertEqual(check_golden(document, fixture, environ={UPDATE_ENV: "1"}), [])
            self.assertTrue(fixture.exists())
            original = fixture.read_bytes()
            # Regenerating over it is refused, and the fixture is left alone.
            drifted = {"probe": "two"}
            lines = check_golden(drifted, fixture, environ={UPDATE_ENV: "1"})
            self.assertTrue(lines)
            self.assertIn("refused to overwrite", lines[0])
            self.assertEqual(fixture.read_bytes(), original)
            # The second explicit flag permits it.
            self.assertEqual(
                check_golden(drifted, fixture, environ={UPDATE_ENV: "1", OVERWRITE_ENV: "1"}), [])
            self.assertNotEqual(fixture.read_bytes(), original)

    def test_configured_provenance_is_the_only_change_from_extraction_golden(self):
        before = json.loads(GOLDEN_PATH.with_name("lifecycle-gate-pre-configured-golden.json").read_text())
        after = json.loads(GOLDEN_PATH.read_text())
        additions = []
        def strip(old, new, path="$"):
            if isinstance(old, dict) and isinstance(new, dict):
                for key in set(new) - set(old):
                    self.assertEqual(key, "configured_gates", path)
                    self.assertEqual(new[key], [], path)
                    additions.append(path)
                return {key: strip(old[key], new[key], path + "." + key) for key in old}
            if isinstance(old, list) and isinstance(new, list):
                self.assertEqual(len(old), len(new), path)
                return [strip(a, b, path + f"[{i}]") for i, (a, b) in enumerate(zip(old, new))]
            self.assertEqual(old, new, path)
            return new
        self.assertEqual(strip(before, after), before)
        self.assertTrue(additions)

    def test_capture_ignores_ambient_clock_and_prior_id_allocation(self):
        ids = self.srv._lifecycle_module()
        for year in (2027, 2031):
            with self.subTest(year=year), tempfile.TemporaryDirectory() as tmp, \
                 patch.object(ids, "current_utc_time", return_value=datetime(year, 1, 1, tzinfo=timezone.utc)), \
                 patch.object(ids, "_last_assigned_prefix", "zzzzz"), \
                 patch.object(ids, "_last_assigned_policy", (datetime(2020, 2, 2, 2, 2, tzinfo=timezone.utc), 0, 0, "v1")):
                fixtures = build_fixtures(Path(tmp), self.srv)
                actual = {name: wave_id for name, (_, wave_id) in fixtures.items()}
                self.assertEqual(actual, {
                    "planned_with_verdict": "0exxk fixture-planned",
                    "active_typed_approvals": "0exxl fixture-active",
                    "missing_lane": "0exxm fixture-missing-lane",
                })
                self.assertEqual(ids._last_assigned_prefix, "zzzzz")

    def test_a_changed_diagnostic_is_detected(self):
        # Known-bad: the golden must redden on any envelope change, which is
        # what makes AC-1 a real oracle rather than a recorded observation.
        base = self.surface()
        mutated = copy.deepcopy(base)
        fixture = mutated["fixtures"]["missing_lane"]["prepare:dry_run"]
        fixture.setdefault("diagnostics", [])
        fixture["diagnostics"] = list(fixture.get("diagnostics") or []) + [
            {"code": "__mutant__", "message": "injected"}
        ]
        temp_golden = self.base / "regen" / "golden.json"
        with patch.dict(os.environ, {UPDATE_ENV: "1"}, clear=False):
            self.assertEqual(check_golden(base, temp_golden), [])
        lines = check_golden(mutated, temp_golden, environ={})
        self.assertTrue(lines, "a changed diagnostic was not detected")
        self.assertTrue(
            any("__mutant__" in line for line in lines),
            f"diff does not name the injected diagnostic: {lines}",
        )


if __name__ == "__main__":
    unittest.main()
