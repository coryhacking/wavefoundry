"""The work area is named without the container noun (wave 22r99, change 22r98).

A renamed distribution calls the container tier something else, so the shipped
work-area wording must not carry it. This census pins the exact forms over the
files that name the work area.
"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
import vocabulary_profile
from record_layout_support import default_profile_only

FRAMEWORK = SCRIPTS.parent
REPO = SCRIPTS.parents[2]
TEMPLATES = [f"install/lifecycle-prompts/{name}.prompt.md"
             for name in ("close-wave", "create-wave", "implement-wave", "prepare-wave", "review-wave")]
SEED_050 = "seeds/050-agent-entry-surface-bootstrap.prompt.md"
SEED_160 = "seeds/160-upgrade-wavefoundry.prompt.md"
SEED_180 = "seeds/180-implement-change.prompt.md"
SEED_209 = "seeds/209-agent-harness-core.prompt.md"
HEADING_PROMPTS = ("close-wave", "create-wave", "implement-change", "implement-wave",
                   "install-wavefoundry", "pause-wave", "prepare-wave", "review-wave")
PROMPTS = (*HEADING_PROMPTS, "upgrade-wavefoundry")


def _framework(rel: str) -> Path:
    return FRAMEWORK / rel


def _prompt(key: str) -> Path:
    # Lifecycle prompts follow the vocabulary profile's names; the others are fixed.
    if key in vocabulary_profile.PROMPT_NAMES:
        return REPO / vocabulary_profile.prompt_doc(key)
    return REPO / f"docs/prompts/{key}.prompt.md"


HEADING_FILES = (*map(_framework, TEMPLATES), _framework(SEED_180), *map(_prompt, HEADING_PROMPTS),
                 REPO / "docs/architecture/threat-model.md",
                 REPO / "docs/contributing/build-and-verification.md",
                 REPO / "docs/specs/mcp-tool-surface.md")
LEAD_IN_FILES = (_framework(SEED_160), _prompt("upgrade-wavefoundry"))
CROSS_REFERENCE_FILES = (*map(_framework, TEMPLATES), _framework(SEED_160), _framework(SEED_209),
                         *map(_prompt, PROMPTS))
DOMAIN_MAP = REPO / "docs/architecture/domain-map.md"
RUNNING_PHRASE_FILES = (_framework("install/lifecycle-prompts/implement-wave.prompt.md"),
                        _prompt("implement-wave"), SCRIPTS / "wave_work.py", SCRIPTS / "run_tests.py",
                        REPO / "docs/references/native-windows-support.md")
# Every file Requirement 3 and the Scope name. render_platform_surfaces.py is
# checked by its own tests instead: it must keep the previous .gitignore comment
# as a recognized legacy line.
CENSUS_FILES = tuple(dict.fromkeys((
    *HEADING_FILES, *LEAD_IN_FILES, *CROSS_REFERENCE_FILES, DOMAIN_MAP, *RUNNING_PHRASE_FILES,
    _framework(SEED_050), REPO / ".gitignore", REPO / "docs/architecture/testing-architecture.md",
    REPO / "CHANGELOG.md",
)))

HEADINGS = {"## Disposable work", "### Disposable work"}
LEAD_IN = "**Disposable work.**"
CROSS_REFERENCE = "seed 180’s **Disposable work**"
DOMAIN_TERM = "| **Disposable Work** |"
RUNNING_PHRASE = "disposable work area"
_HEADING_LINE = re.compile(r"^ {0,3}#{1,6}[ \t]+disposable", re.IGNORECASE)
_CROSS_REFERENCE_CANDIDATE = re.compile(r"[Ss]eed 180[^\n*]{0,6}\*\*[^*\n]*\*\*")
_BOLD_TERM = re.compile(r"\*\*Disposable[^*\n]*\*\*")


def work_area_wording_problems(files) -> list[str]:
    problems = []
    for path in files:
        if not path.is_file():
            problems.append(f"{path}: missing")
            continue
        text = path.read_text(encoding="utf-8")
        for forbidden in ("Disposable work area", "Disposable Work Area"):
            if forbidden in text:
                problems.append(f"{path}: contains {forbidden!r}")
        if "disposable wave work" in text.lower():
            problems.append(f"{path}: contains 'disposable wave work'")
        if path.suffix == ".md":
            for number, line in enumerate(text.splitlines(), 1):
                if _HEADING_LINE.match(line) and line not in HEADINGS:
                    problems.append(f"{path}:{number}: heading {line!r}")
        for match in _CROSS_REFERENCE_CANDIDATE.finditer(text):
            if "isposable" in match[0] and match[0] != CROSS_REFERENCE:
                problems.append(f"{path}: cross-reference {match[0]!r}")
        for match in _BOLD_TERM.finditer(text):
            if match[0] not in {"**Disposable work**", LEAD_IN, "**Disposable Work**"}:
                problems.append(f"{path}: term {match[0]!r}")
    return problems


class WorkAreaWordingCensusTests(unittest.TestCase):
    @default_profile_only("a census of this repository's own documents, which are written in the default profile")
    def test_no_named_file_carries_the_container_noun_or_a_variant_form(self):
        self.assertEqual(work_area_wording_problems(CENSUS_FILES), [])

    @default_profile_only("a census of this repository's own documents, which are written in the default profile")
    def test_each_named_file_carries_its_exact_form(self):
        for path in HEADING_FILES:
            with self.subTest(heading=str(path)):
                lines = path.read_text(encoding="utf-8").splitlines()
                self.assertTrue(HEADINGS & set(lines), path)
        for path in LEAD_IN_FILES:
            with self.subTest(lead_in=str(path)):
                self.assertIn(LEAD_IN, path.read_text(encoding="utf-8"))
        for path in CROSS_REFERENCE_FILES:
            with self.subTest(cross_reference=str(path)):
                self.assertIn(CROSS_REFERENCE, path.read_text(encoding="utf-8"))
        for path in RUNNING_PHRASE_FILES:
            with self.subTest(running=str(path)):
                self.assertIn(RUNNING_PHRASE, path.read_text(encoding="utf-8"))
        self.assertIn(DOMAIN_TERM, DOMAIN_MAP.read_text(encoding="utf-8"))

    def test_the_census_rejects_each_previous_form(self):
        import tempfile
        samples = {
            "heading.md": "## Disposable work area\n",
            "heading-wave.md": "### Disposable wave work\n",
            "cross.md": "Follow Seed 180’s **Disposable work area** here.\n",
            "paren.md": "(seed 180, **Disposable work**)\n",
            "term.md": "| **Disposable Work Area** | x |\n",
            "comment.txt": "# Wavefoundry Disposable Wave Work (scratch)\n",
        }
        with tempfile.TemporaryDirectory() as tmp:
            for name, body in samples.items():
                path = Path(tmp) / name
                path.write_text(body, encoding="utf-8")
                with self.subTest(sample=name):
                    self.assertTrue(work_area_wording_problems([path]))
            clean = Path(tmp) / "clean.md"
            clean.write_text("## Disposable work\n\nFollow seed 180’s **Disposable work** in the "
                             "disposable work area.\n", encoding="utf-8")
            self.assertEqual(work_area_wording_problems([clean]), [])


if __name__ == "__main__":
    unittest.main()
