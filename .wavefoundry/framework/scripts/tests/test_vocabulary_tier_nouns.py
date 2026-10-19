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
import json, sys
sys.dont_write_bytecode = True
sys.path.insert(0, sys.argv[1])
import render_agent_surfaces as r
print(json.dumps({s.name: [s.description, s.body] for s in r.SKILL_REGISTRY}))
'''

# Census (Progress Log of 2134r): every tier noun in SKILL_REGISTRY prose, as
# exact spans per skill under the Set/Wave profile (container Set, item Wave).
SET_WAVE_SPANS = {
    "wf-plan-change": ["Plan a wave of any kind", "consolidated wave doc ready for set admission",
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
    "wf-close-change": ["Close one admitted wave inside the open set", "never closes the set (",
                        "is the only set close)", "# Close a wave (",
                        "has cleared the wave: a completed wave cannot be reopened",
                        "remains the only set close, whatever the wave count."],
    "wf-review-plan": ["Review a wave doc, or the current set record when no wave is specified",
                       "Review the named wave doc, or fall back to the current set record when no wave is specified",
                       "for the open set's required delivery-review lanes."],
    "wf-pause-wave": ["Park the current session's set state", "# Pause a set ("],
    "wf-council": ["Not the open set's required lanes", "the optional wave-doc or current-set stress test"],
    "wf-code-cleanup": ["and not the open set's required lanes"],
}


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
                shipped = span.replace("set", "\0").replace("wave", "change").replace("\0", "wave")
                with self.subTest(skill=name, span=shipped):
                    self.assertIn(shipped, text)

    def test_renamed_profile_names_its_own_tiers(self) -> None:
        for name, spans in SET_WAVE_SPANS.items():
            text = "\n".join(self.set_wave[name])
            for span in spans:
                with self.subTest(skill=name, span=span):
                    self.assertIn(span, text)

    def test_only_tier_nouns_change(self) -> None:
        # Product, tool and kind names stay literal under any profile.
        for literal in ("Wave Framework", "wf_close_change", "operations, change) by"):
            with self.subTest(literal=literal):
                self.assertIn(literal, json.dumps(self.set_wave))


if __name__ == "__main__":
    unittest.main()
