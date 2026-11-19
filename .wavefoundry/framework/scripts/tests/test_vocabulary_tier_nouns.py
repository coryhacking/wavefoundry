"""Wave 2134s (change 2134r): tier nouns in skill prose follow the profile.

``vocabulary_profile.tier_noun`` derives the container and item nouns (with a
declared indefinite article) that ``render_agent_surfaces.SKILL_REGISTRY``
uses in its descriptions and body titles. Under the default profile the
rendered text is unchanged; under a renamed profile every census-listed span
names the profile's own tiers.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from record_layout_support import apply_profile, copy_scripts_tree, load_profile, shipped_default_profile

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import vocabulary_profile  # noqa: E402

DUMP = r'''
import json, sys, tempfile
from pathlib import Path
sys.dont_write_bytecode = True
sys.path.insert(0, sys.argv[1])
import render_agent_surfaces as r
result = {s.name: [s.description, s.body] for s in r.SKILL_REGISTRY}
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    bridge = root / "CLAUDE.md"
    bridge.write_text(r.ROOT_BRIDGE_MARKER_BEGIN + "\n@AGENTS.md\n" + r.ROOT_BRIDGE_MARKER_END)
    r.patch_root_bridge(bridge, root=root)
    result["_root_bridge"] = bridge.read_text()
print(json.dumps(result))
'''

# Census (Progress Log of 2134r): every tier noun in SKILL_REGISTRY prose, as
# exact spans per skill under the Set/Wave profile (container Set, item Wave).
SET_WAVE_SPANS = {
    "wf-plan-spec": ["Plan a wave of any kind", "consolidated wave doc ready for set admission",
                       "# Plan a wave (", "by wave kind", "(wave doc, set admission, recorded readiness) is satisfied"],
    "wf-prepare-wave": ["Confirm a set's readiness", "# Prepare a set (", "recorded before the set readies",
                        "only one set may be OPEN"],
    "wf-implement-wave": ["Open a readied set and coordinate multi-wave implementation", "# Implement a set (",
                          "open the readied set and receive the ordered wave list",
                          "(wave doc, set admission, recorded readiness); mark ACs", "not at set end",
                          "Single-wave variant:"],
    "wf-review-wave": ["Run the open set's required review lanes", "# Review a set ("],
    "wf-close-wave": ["Close and archive a set after", "# Close a set (", "Single wave: ",
                      "marks one wave `complete` inside the open set", "is still the only set close."],
    "wf-close-spec": ["Close one admitted wave inside the open set", "never closes the set (",
                        "is the only set close)", "# Close a wave (",
                        "has cleared the wave: a completed wave cannot be reopened",
                        "remains the only set close, whatever the wave count."],
    "wf-review-plan": ["Review a wave doc, or the current set record when no wave is specified",
                       "Review the named wave doc, or fall back to the current set record when no wave is specified",
                       "for the open set's required delivery-review lanes."],
    "wf-pause-wave": ["Park the current session's set state", "# Pause a set ("],
    "wf-council": ["Not the open set's required lanes", "the optional wave-doc or current-set stress test"],
    "wf-code-cleanup": ["and not the open set's required lanes"],
    # Change 230k7: the Plan arc skill names the container tier in three places.
    "wf-plan-arc": ["bounded outcome across sets in a concise", "next useful set from relevant records",
                    "link to authoritative set evidence."],
}

# Change 23myn Requirement 10: the planning-document noun is "spec" under the
# shipped item name, so these spans have their own default oracle instead of
# the tier swap.
DEFAULT_PLANNING_SPANS = {
    "consolidated wave doc ready for set admission": "consolidated spec ready for wave admission",
    "(wave doc, set admission, recorded readiness) is satisfied": "(spec, wave admission, recorded readiness) is satisfied",
    "(wave doc, set admission, recorded readiness); mark ACs": "(spec, wave admission, recorded readiness); mark ACs",
    "Review a wave doc, or the current set record when no wave is specified":
        "Review a spec, or the current wave record when no change is specified",
    "Review the named wave doc, or fall back to the current set record when no wave is specified":
        "Review the named spec, or fall back to the current wave record when no change is specified",
    "the optional wave-doc or current-set stress test": "the optional spec or current-wave stress test",
}

# The council skill's Boundary line, whose planning-document and container
# nouns follow the profile since change 23myn (fixed words before it).
DEFAULT_BOUNDARY = (
    "- Boundary: the open wave's REQUIRED review lanes run under Review wave (`wf-review-wave`), "
    "and a spec or current wave record gets Review plan (`wf-review-plan`; aliases: Interrogate this "
    "plan, Stress-test this plan) before implementation; this router is for on-demand reviews outside both."
)


def _skills(profile: "dict | None") -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        scripts = copy_scripts_tree(Path(tmp), with_support=False)
        apply_profile(scripts, shipped_default_profile())
        if profile is not None:
            apply_profile(scripts, profile)
        out = subprocess.run([sys.executable, "-B", "-c", DUMP, str(scripts)],
                             capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


class TierNounHelperTests(unittest.TestCase):
    def test_default_nouns(self) -> None:
        # Pin the shipped names explicitly so the test holds on any profile.
        shipped = {"CONTAINER_NAME": "Wave", "CONTAINER_NAME_PLURAL": "Waves", "ITEM_NAME": "Change",
                   "ITEM_NAME_PLURAL": "Changes", "CONTAINER_NAME_ARTICLE": "a", "ITEM_NAME_ARTICLE": "a"}
        with mock.patch.multiple(vocabulary_profile, **shipped):
            self._assert_shipped_nouns()

    def _assert_shipped_nouns(self) -> None:
        noun = vocabulary_profile.tier_noun
        self.assertEqual(noun("container"), "wave")
        self.assertEqual(noun("container", article=True), "a wave")
        self.assertEqual(noun("item", plural=True), "changes")
        self.assertEqual(noun("item", title=True), "Change")
        self.assertEqual(noun("item", plural=True, article=True), "changes")
        with self.assertRaises(ValueError):
            noun("record")

    def test_declared_article_is_used(self) -> None:
        with mock.patch.object(vocabulary_profile, "ITEM_NAME", "Item"), \
             mock.patch.object(vocabulary_profile, "ITEM_NAME_ARTICLE", "an"):
            self.assertEqual(vocabulary_profile.tier_noun("item", article=True), "an item")

    def test_article_must_be_a_or_an(self) -> None:
        self.assertEqual(vocabulary_profile.tier_article_errors(), [])
        for name in ("CONTAINER_NAME_ARTICLE", "ITEM_NAME_ARTICLE"):
            with self.subTest(name=name), mock.patch.object(vocabulary_profile, name, "the"):
                errors = vocabulary_profile.tier_article_errors()
                self.assertEqual(len(errors), 1)
                self.assertIn(name, errors[0])
                with self.assertRaises(vocabulary_profile.VocabularyProfileInvalid):
                    vocabulary_profile.validate()


class SkillProseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.default = _skills(None)
        cls.set_wave = _skills(load_profile("second"))

    def test_default_profile_renders_the_shipped_wording(self) -> None:
        for name, spans in SET_WAVE_SPANS.items():
            text = "\n".join(self.default[name])
            for span in spans:
                shipped = DEFAULT_PLANNING_SPANS.get(span) or (
                    span.replace("set", "\0").replace("wave", "change").replace("\0", "wave"))
                with self.subTest(skill=name, span=shipped):
                    self.assertIn(shipped, text)

    def test_renamed_profile_names_its_own_tiers(self) -> None:
        for name, spans in SET_WAVE_SPANS.items():
            text = "\n".join(self.set_wave[name])
            for span in spans:
                with self.subTest(skill=name, span=span):
                    self.assertIn(span, text)

    def test_plan_arc_keeps_its_identity_routing_and_authority_limits(self) -> None:
        # Change 230k7: only the container noun moves; a literal container noun left in the
        # registry would survive into the renamed profile and fail the last assertion.
        for label, skills in (("default", self.default), ("renamed", self.set_wave)):
            description, body = skills["wf-plan-arc"]
            with self.subTest(profile=label):
                self.assertIn("workflow grants no implementation authority.", description)
                self.assertIn("adds no lifecycle gate or implementation authority.", body)
                self.assertIn("# Plan arc (", body)
                self.assertIn("docs/prompts/plan-arc.prompt.md", body)
                self.assertIn("honor a read-only request", body)
        renamed = "\n".join(self.set_wave["wf-plan-arc"]).lower().replace("wavefoundry", "")
        self.assertNotIn("wave", renamed)
        self.assertEqual(self.default["wf-plan-arc"][0],
                         "Plan or resume a bounded outcome across waves in a concise arc record, explaining "
                         "evidence, remaining obligations and the next useful advance. The optional Plan arc "
                         "workflow grants no implementation authority.")

    def test_only_tier_nouns_change(self) -> None:
        # Product, tool and kind names stay literal under any profile.
        for literal in ("Wave Framework", "wf_close_change", "operations, change) by"):
            with self.subTest(literal=literal):
                self.assertIn(literal, json.dumps(self.set_wave))

    def test_council_boundary_line_follows_the_profile(self) -> None:
        # Change 23myn Requirement 10: literal oracles for both profiles; the
        # line used fixed words before, so it has no earlier renamed baseline.
        self.assertIn(DEFAULT_BOUNDARY, self.default["wf-council"][1])
        renamed = self.set_wave["wf-council"][1]
        self.assertIn("- Boundary: the open set's REQUIRED review lanes run under", renamed)
        self.assertIn("and a wave doc or current set record gets Review plan", renamed)

    def test_default_profile_planning_strings_are_unchanged(self) -> None:
        # Change 23myn: under the default profile each composed sentence keeps
        # the bytes it had before the noun followed the profile.
        sentences = {
            "wf-plan-spec": [
                "and produce a consolidated spec ready for wave admission.",
                "Gate reminder: planning writes docs only; no repository code edits until the stage gate "
                "(spec, wave admission, recorded readiness) is satisfied.",
            ],
            "wf-implement-wave": [
                "Gate reminder: the stage gate applies before any code edit (spec, wave admission, recorded "
                "readiness); mark ACs and tasks as work completes, not at wave end.",
            ],
            "wf-review-plan": [
                "Review a spec, or the current wave record when no change is specified, before implementation",
                "Review the named spec, or fall back to the current wave record when no change is specified; "
                "this may run before or after admission, but only before implementation.",
            ],
            "wf-council": [
                "and not Review plan, the optional spec or current-wave stress test whose aliases are "
                "Interrogate this plan and Stress-test this plan.",
                DEFAULT_BOUNDARY,
            ],
        }
        for name, expected in sentences.items():
            text = "\n".join(self.default[name])
            for sentence in expected:
                with self.subTest(skill=name, sentence=sentence[:40]):
                    self.assertIn(sentence, text)

    def test_root_bridge_default_bytes_and_renamed_literal_oracle(self) -> None:
        # Default sentence pinned to 3d21af8e; renamed nouns are independent
        # literals, not computed by the helper whose output is under test.
        prefix = "<!-- wave:root-bridge begin — generated by render_agent_surfaces.py; do not edit -->\n@AGENTS.md\n"
        suffix = "\n<!-- wave:root-bridge end -->"
        default = "When compacting, preserve the open wave and change ids, the operator's scoped authorizations and decisions still pending, the files modified, and the exact verification commands with their last results; a summary never records an approval the operator did not give. After resuming, recheck mutable state such as open gates and wave status with the tools instead of trusting the summary."
        renamed = "When compacting, preserve the open set and wave ids, the operator's scoped authorizations and decisions still pending, the files modified, and the exact verification commands with their last results; a summary never records an approval the operator did not give. After resuming, recheck mutable state such as open gates and set status with the tools instead of trusting the summary."
        self.assertEqual(self.default["_root_bridge"], prefix + default + suffix)
        self.assertEqual(self.set_wave["_root_bridge"], prefix + renamed + suffix)


_SHIPPED_NOUNS = {"CONTAINER_NAME": "Wave", "CONTAINER_NAME_PLURAL": "Waves", "ITEM_NAME": "Change",
                  "ITEM_NAME_PLURAL": "Changes", "CONTAINER_NAME_ARTICLE": "a", "ITEM_NAME_ARTICLE": "a"}
_TICKET_NOUNS = {"ITEM_NAME": "Ticket", "ITEM_NAME_PLURAL": "Tickets",
                 "CONTAINER_NAME": "Batch", "CONTAINER_NAME_PLURAL": "Batches"}


class PlanningNounTests(unittest.TestCase):
    """Change 23myn Requirement 10: ``vocabulary_profile.planning_noun`` and
    the message strings composed from it, in process under patched profiles."""

    def test_forms_under_the_shipped_item_name(self) -> None:
        with mock.patch.multiple(vocabulary_profile, **_SHIPPED_NOUNS):
            forms = {form: vocabulary_profile.planning_noun(form)
                     for form in ("doc", "docs", "article", "documents", "hyphen")}
            self.assertEqual(vocabulary_profile.planning_noun(), "spec")
        self.assertEqual(forms, {"doc": "spec", "docs": "specs", "article": "a spec",
                                 "documents": "specs", "hyphen": "spec"})

    def test_forms_under_a_renamed_item(self) -> None:
        with mock.patch.multiple(vocabulary_profile, **_TICKET_NOUNS):
            forms = {form: vocabulary_profile.planning_noun(form)
                     for form in ("doc", "docs", "article", "documents", "hyphen")}
        self.assertEqual(forms, {"doc": "ticket doc", "docs": "ticket docs", "article": "a ticket doc",
                                 "documents": "ticket documents", "hyphen": "ticket-doc"})
        with mock.patch.multiple(vocabulary_profile, ITEM_NAME="Item", ITEM_NAME_ARTICLE="an"):
            self.assertEqual(vocabulary_profile.planning_noun("article"), "an item doc")
        # The shipped name is a fixed constant compared exactly, not the word "spec".
        with mock.patch.object(vocabulary_profile, "ITEM_NAME", "Spec"):
            self.assertEqual(vocabulary_profile.planning_noun(), "spec doc")
        self.assertEqual(vocabulary_profile.SHIPPED_ITEM_NAME, "Change")
        with self.assertRaises(ValueError):
            vocabulary_profile.planning_noun("record")

    def _attribution(self) -> str:
        import lifecycle_gate_support as lgs
        current = {"receipt_id": "a", "policy_inputs": {"project_policy_sha256": "x",
                                                         "changes": [{"change_id": "1abcz-bug s", "h": 1}]}}
        state = {"receipt": {"receipt_id": "b", "policy_inputs": {"project_policy_sha256": "x",
                                                                   "changes": [{"change_id": "1abcz-bug s", "h": 2}]}},
                 "records": []}
        with mock.patch.object(lgs, "receipt_semantic_fields", lambda record: {}), \
             mock.patch.object(lgs, "current_policy_receipt", lambda records: current), \
             mock.patch.object(lgs.review_policy, "compare_receipt_sections",
                               lambda a, b: {"available": False, "limitations": []}):
            return str(lgs.receipt_supersession_attribution(state, ["1abcz-bug s"]))

    def _stats(self) -> str:
        # A static payload with both coverage keys: the real collector imports
        # the server, which re-imports this module and would drop the patch.
        import project_stats
        coverage = {"missing_admitted_documents": 1, "unreadable_change_documents": 2}
        return project_stats.format_report({"schema_version": 1, "sections": {"lifecycle": {"coverage": coverage}}})

    def test_message_strings_under_the_shipped_profile(self) -> None:
        import lifecycle_gate_support as lgs
        with mock.patch.multiple(vocabulary_profile, **_SHIPPED_NOUNS):
            self.assertIn("changed specs: 1abcz-bug s", self._attribution())
            stats = self._stats()
            self.assertIn("- Missing specs assigned to waves: 1", stats)
            self.assertIn("- Unreadable specs: 2", stats)
            self.assertIn("against the admitted specs and wave record. ",
                          lgs._prepare_council_instructions(None, typed=True))

    def test_message_strings_under_a_ticket_and_batch_profile(self) -> None:
        with mock.patch.multiple(vocabulary_profile, **_TICKET_NOUNS):
            self.assertIn("changed ticket docs: 1abcz-bug s", self._attribution())
            stats = self._stats()
            self.assertIn("- Missing ticket documents assigned to batches: 1", stats)
            self.assertIn("- Unreadable ticket documents: 2", stats)

    def test_article_form_reaches_the_rendered_skills(self) -> None:
        # ITEM_NAME_ARTICLE is not a fork-editable constant, so patch it in
        # process and reload the renderer, whose skill text is built at import.
        import importlib
        import render_agent_surfaces
        try:
            with mock.patch.multiple(vocabulary_profile, ITEM_NAME="Item", ITEM_NAME_PLURAL="Items",
                                     ITEM_NAME_ARTICLE="an"):
                renderer = importlib.reload(render_agent_surfaces)
                descriptions = [skill.description for skill in renderer.SKILL_REGISTRY]
                council_body = renderer.WF_COUNCIL_SKILL_BODY
        finally:
            importlib.reload(render_agent_surfaces)
        self.assertTrue(any(text.startswith("Review an item doc, or the current ") for text in descriptions),
                        descriptions)
        self.assertIn("and an item doc or current ", council_body)


if __name__ == "__main__":
    unittest.main()
