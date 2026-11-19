"""Shape, delivery and reference contracts of the shipped Rust practices baseline.

These checks prove the document's structure only. Whether a stance matches its
sources, and whether a platform statement is true, is judged by reviewers.
"""
from __future__ import annotations

import io
from pathlib import Path
import re
import sys
import tempfile
import unittest
import zipfile

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))

import build_pack
import upgrade_wavefoundry

FRAMEWORK = SCRIPTS.parent
REPO = FRAMEWORK.parent.parent
BASELINE = ".wavefoundry/framework/docs/rust-practices.md"
SEEDS = (
    "012-install-wavefoundry-phase-2.prompt.md",
    "160-upgrade-wavefoundry.prompt.md",
    "222-software-engineer.prompt.md",
)

FIELDS = ("Practice", "Applies when", "Stance", "Setting", "Check", "Cost and caveats", "Sources")
STANCES = frozenset({"adopt", "propose", "situational"})
APPLIES = frozenset({"library", "application", "FFI", "async", "untrusted input", "any"})
TOUCHES = frozenset({"processes", "paths", "line-endings", "locking", "linking", "ffi", "none"})
MIN_ENTRIES = 7

# Requirement 4's topic areas, plus the async disagreement; each needs a disposition row.
TOPICS = (
    "Lint policy and exception reasons",
    "Panic-family lints by name with test exemptions",
    "Panics, expect and assertion messages",
    "Error types for libraries and applications",
    "Unsafe justification and FFI layout",
    "API design",
    "Documentation sections and module docs",
    "Logging in production code",
    "Cancellation, guard lifetimes and lock poisoning",
    "Process spawning",
    "Workspace inheritance, manifest lints, toolchain and minimum version, additive features",
    "Dependency and source policy",
    "Task-runner entry point and drift checks",
    "Crate layering checks",
    "Line endings for embedded files",
    "Continuous-integration actions pinned by commit",
    "Test placement and tests that restate the implementation",
    "Async",
    "Guidance aimed at coding agents",
)

PANIC_FAMILY = {
    "unwrap_used": "propose", "todo": "propose", "unimplemented": "propose",
    "panic": "situational", "unreachable": "situational", "expect_used": "situational",
}

# The five disagreements of requirement 3.3, matched against entry headings.
DISAGREEMENTS = {
    "catching a panic": r"(?i)catching a panic",
    "lint groups": r"(?i)lint groups",
    "error shape": r"(?i)error type shape",
    "test placement": r"(?i)tests of the public api",
    "async": r"(?i)\basync\b",
}

LINT_TABLES = {
    "lints.rust": "rustc", "workspace.lints.rust": "rustc",
    "lints.clippy": "Clippy", "workspace.lints.clippy": "Clippy",
    "lints.cargo": "Cargo", "workspace.lints.cargo": "Cargo",
}
CLIPPY_GROUPS = frozenset({"all", "cargo", "complexity", "correctness", "nursery", "pedantic",
                           "perf", "restriction", "style", "suspicious"})
LEVEL_VALUE = re.compile(r"""^(?:"(?:allow|warn|deny|forbid|expect)"|\{[^}]*\blevel\b)""")
# Lint attributes in Rust settings, such as #![deny(clippy::print_stdout)] or #![forbid(unsafe_code)].
LINT_ATTRIBUTE = re.compile(r"#!?\[(?:allow|warn|deny|forbid|expect)\(([^)]*)\)\]")
MEMBER_LINT_TABLE = re.compile(r"(?m)^\s*\[lints(?:\.[a-z]+)?\]\s*$")
INHERITANCE_SENTENCE = "replaces inheritance"
COMPOSING_PHRASES = ("fragments", "one table or one list per file", "not both", INHERITANCE_SENTENCE,
                     "attribute at the crate root")

# Topics derived from entry text; each derived topic must appear in the entry's Touches.
TOPIC_PATTERNS = {
    "processes": r"(?i)\bspawn|child process|std::process|Command::new",
    "line-endings": r"(?i)line ending|carriage return|\bCRLF\b",
    "paths": r"(?i)path separator",
    "locking": r"(?i)file lock",
    "linking": r"(?i)\blinking\b|\blinker\b",
    "ffi": r"\bFFI\b|(?i:foreign function)",
}
PINNED_PLATFORM_ENTRIES = {
    "One module owns process spawning": "processes",
    "Files embedded at compile time have fixed line endings": "line-endings",
}

# AC-2 oracle: imperatives addressed to the agent that would enable or create something.
IMPERATIVE = re.compile(
    r"(?i)\b(?:enable|add|install|create|write)\b[^.;:\n]{0,40}?"
    r"\b(?:lints?|settings?|tools?|files?|configuration)\b")
NEGATION = re.compile(r"(?i)\b(?:never|not|no|without|nor)\b|n't\b")

# AC-7 oracle: wave and change identifiers, and the repositories reviewed for the plan.
IDENTIFIER = re.compile(r"\b(?=[0-9a-z]{0,4}[a-z])[0-9][0-9a-z]{4}\b")
REVIEWED_REPOSITORIES = ("tensorwell", "craft-anything", "craft-libs", "storytold")


def normalize(text: str) -> str:
    return text.replace("\r\n", "\n")


def read_baseline(root: Path = REPO) -> str:
    return normalize((root / BASELINE).read_text(encoding="utf-8"))


def outside_fences(text: str) -> str:
    kept, fenced = [], False
    for line in text.split("\n"):
        if line.startswith("```"):
            fenced = not fenced
            continue
        if not fenced:
            kept.append(line)
    return "\n".join(kept)


def fenced_blocks(text: str) -> list[str]:
    return re.findall(r"(?ms)^```[^\n]*\n(.*?)^```", text)


def sections(text: str) -> dict[str, str]:
    parts = re.split(r"(?m)^## (.+)\n", text)
    return {parts[i].strip(): parts[i + 1] for i in range(1, len(parts) - 1, 2)}


def slug(heading: str) -> str:
    return re.sub(r"[^a-z0-9 _-]", "", heading.lower()).replace(" ", "-")


def table_rows(text: str) -> list[list[str]]:
    rows = []
    for line in text.split("\n"):
        if line.startswith("|") and not re.match(r"^\|\s*-", line):
            rows.append([cell.strip() for cell in line.strip().strip("|").split("|")])
    return rows[1:]


def usage_statement(text: str) -> str:
    head = text.split("\n## ", 1)[0]
    return head.split("Last verified:", 1)[1].split("\n", 1)[1] if "Last verified:" in head else ""


def parse_fields(body: str) -> list[tuple[str, str]]:
    fields, fenced = [], False
    for line in body.split("\n"):
        if line.startswith("```"):
            fenced = not fenced
        match = None if fenced else re.match(r"^\*\*([^*]+):\*\*\s*(.*)$", line)
        if match:
            fields.append([match.group(1), match.group(2)])
        elif fields:
            fields[-1][1] += "\n" + line
    return [(label, value.strip()) for label, value in fields]


def entries(text: str) -> list[dict]:
    found = []
    for chunk in re.split(r"(?m)^### ", sections(text).get("Entries", ""))[1:]:
        heading, _, body = chunk.partition("\n")
        fields = parse_fields(body)
        found.append({"heading": heading.strip(), "fields": fields, "body": body,
                      "map": dict(fields)})
    return found


def plain_lines(value: str, label: str) -> list[str]:
    return [m.group(1).strip() for m in re.finditer(rf"(?m)^\s+{label}:\s*(.*)$", value)]


def touches(entry: dict) -> set[str]:
    lines = plain_lines(entry["map"].get("Cost and caveats", ""), "Touches")
    return {v.strip() for v in lines[0].split(",")} if lines else set()


def setting_lints(entry: dict) -> set[tuple[str, str]]:
    named = set()
    for block in fenced_blocks(entry["map"].get("Setting", "")):
        table = None
        for line in block.split("\n"):
            header = re.match(r"^\s*\[([A-Za-z0-9_.-]+)\]\s*$", line)
            if header:
                table = header.group(1)
                continue
            assignment = re.match(r"^\s*([a-z_][a-z0-9_]*)\s*=\s*(.+)$", line)
            if table in LINT_TABLES and assignment and LEVEL_VALUE.match(assignment.group(2)):
                named.add((assignment.group(1), LINT_TABLES[table]))
        named.update((name, "Clippy") for name in re.findall(r"\bclippy::([a-z_]+)", block))
        for arguments in LINT_ATTRIBUTE.findall(block):
            for argument in (a.strip() for a in arguments.split(",")):
                if re.fullmatch(r"[a-z_][a-z0-9_]*", argument):
                    named.add((argument, "rustc"))
    return {(name, tool) for name, tool in named if not (tool == "Clippy" and name in CLIPPY_GROUPS)}


def source_titles(text: str) -> list[str]:
    return [row[0] for row in table_rows(sections(text).get("Sources and attribution", "")) if row]


def structure_problems(text: str) -> list[str]:
    problems = []
    found = entries(text)
    if len(found) < MIN_ENTRIES:
        problems.append(f"only {len(found)} entries")
    headings = [e["heading"] for e in found]
    if len(headings) != len(set(headings)):
        problems.append("duplicate entry headings")
    for entry in found:
        name, fields = entry["heading"], entry["map"]
        labels = tuple(label for label, _ in entry["fields"])
        if labels != FIELDS:
            problems.append(f"{name}: fields {labels}")
            continue
        if fields["Stance"] not in STANCES:
            problems.append(f"{name}: stance {fields['Stance']!r}")
        for label in ("Check", "Sources", "Practice", "Setting"):
            if not fields[label]:
                problems.append(f"{name}: empty {label}")
        applies = {v.strip() for v in fields["Applies when"].split(",")}
        if not applies or not applies <= APPLIES:
            problems.append(f"{name}: applies when {sorted(applies)}")
        if re.search(r"(?m)^\*\*(?:Touches|Platforms)", entry["body"]):
            problems.append(f"{name}: Touches or Platforms as a bold label")
        values = touches(entry)
        if not values or not values <= TOUCHES or ("none" in values and len(values) > 1):
            problems.append(f"{name}: touches {sorted(values)}")
    index = table_rows(sections(text).get("Index", ""))
    by_slug = {slug(e["heading"]): e for e in found}
    if len(index) != len(found):
        problems.append(f"index has {len(index)} rows for {len(found)} entries")
    linked = set()
    for row in index:
        link = re.fullmatch(r"\[([^\]]+)\]\(#([^)]+)\)", row[0]) if row else None
        entry = by_slug.get(link.group(2)) if link else None
        if entry is None or link.group(1) != entry["heading"]:
            problems.append(f"index row does not link to an entry: {row}")
            continue
        linked.add(entry["heading"])
        if len(row) < 2 or row[1] != entry["map"].get("Stance"):
            problems.append(f"index stance differs for {entry['heading']}")
    for heading in set(headings) - linked:
        problems.append(f"entry not in index: {heading}")
    dispositions = {row[0]: row[1] if len(row) > 1 else "" for row in
                    table_rows(sections(text).get("Topic dispositions", ""))}
    for topic in TOPICS:
        if not dispositions.get(topic, "").strip():
            problems.append(f"no disposition for topic: {topic}")
    return problems


def setting_outside_fence_problems(text: str) -> list[str]:
    problems = []
    for number, line in enumerate(outside_fences(text).split("\n"), 1):
        if re.match(r"^\s*\[[A-Za-z0-9_.-]+\]\s*$", line) or re.match(r"^\s*[a-z_][\w.-]*\s*=\s*\S", line):
            problems.append(f"setting line outside a fence: {line}")
        for code in re.findall(r"`([^`\n]+)`", line):
            if " = " in code or "=" in code.replace("==", "") and re.search(r"\w=\w", code):
                problems.append(f"assignment in prose: {code}")
            if re.match(r"(?:cargo|rustup|rustc|git)\s+\S", code):
                problems.append(f"command in prose: {code}")
    return problems


def imperative_hits(text: str) -> list[str]:
    hits = []
    for match in IMPERATIVE.finditer(text):
        before = text[max(0, match.start() - 30):match.start()]
        if not NEGATION.search(before):
            hits.append(match.group(0))
    return hits


def identifier_hits(text: str) -> list[str]:
    hits = IDENTIFIER.findall(text)
    lowered = text.lower()
    return hits + [name for name in REVIEWED_REPOSITORIES if name in lowered]


def lint_table(text: str) -> dict[str, list[str]]:
    return {row[0].strip("`"): row for row in table_rows(sections(text).get("Lints named", "")) if row}


def lint_problems(text: str) -> list[str]:
    problems = []
    table = lint_table(text)
    named = set().union(*(setting_lints(e) for e in entries(text)))
    for name, tool in sorted(named):
        row = table.get(name)
        if row is None:
            problems.append(f"lint not in table: {name}")
        elif len(row) < 5 or row[1] != tool or not row[2] or not row[3] or "Rust 1.100.0" not in row[4]:
            problems.append(f"incomplete or mismatched row: {row}")
    for name in set(table) - {name for name, _ in named}:
        problems.append(f"table row for a lint no Setting names: {name}")
    return problems


def composing_problems(text: str) -> list[str]:
    section = sections(text).get("Composing settings")
    if section is None:
        return ["no Composing settings section"]
    names = list(sections(text))
    problems = [] if names.index("Composing settings") == names.index("Index") + 1 else [
        "Composing settings does not follow the index"]
    return problems + [f"composing settings missing: {p}" for p in COMPOSING_PHRASES if p not in section]


def member_table_problems(text: str) -> list[str]:
    """A member-level manifest lint table other than plain inheritance must say it replaces inheritance."""
    problems = []
    for entry in entries(text):
        for block in fenced_blocks(entry["map"].get("Setting", "")):
            if not MEMBER_LINT_TABLE.search(block):
                continue
            lines = [line.strip() for line in block.split("\n") if line.strip() and not line.strip().startswith("#")]
            if lines == ["[lints]", "workspace = true"]:
                continue
            if INHERITANCE_SENTENCE not in entry["map"].get("Cost and caveats", ""):
                problems.append(f"{entry['heading']}: member lint table without the inheritance sentence")
    return problems


def panic_family_problems(text: str) -> list[str]:
    problems = []
    found = entries(text)
    for lint, stance in PANIC_FAMILY.items():
        owners = [e for e in found if (lint, "Clippy") in setting_lints(e)]
        if len(owners) != 1:
            problems.append(f"{lint}: {len(owners)} entries")
        elif owners[0]["map"]["Stance"] != stance:
            problems.append(f"{lint}: stance {owners[0]['map']['Stance']}")
    return problems


def disagreement_problems(text: str) -> list[str]:
    problems = []
    for topic, pattern in DISAGREEMENTS.items():
        matching = [e for e in entries(text) if re.search(pattern, e["heading"])]
        situational = [e for e in matching if e["map"].get("Stance") == "situational"]
        if len(situational) != 1 or len(matching) != 1:
            problems.append(f"{topic}: {len(matching)} entries, {len(situational)} situational")
            continue
        body = situational[0]["body"]
        if "One position" not in body or "The other position" not in body:
            problems.append(f"{topic}: both positions not stated")
    return problems


def source_problems(text: str) -> list[str]:
    problems = []
    titles = source_titles(text)
    for entry in entries(text):
        cited = [t for t in titles if t in entry["map"].get("Sources", "")]
        if not cited:
            problems.append(f"{entry['heading']}: no listed source")
        if entry["map"].get("Stance") == "adopt":
            public = [t for t in cited if t in ("Google Rust Style Guide", "Microsoft Pragmatic Rust Guidelines",
                                                "Rust API Guidelines")]
            if not public:
                problems.append(f"{entry['heading']}: adopt without a recommending source")
    rows = table_rows(sections(text).get("Sources and attribution", ""))
    for row in rows:
        if len(row) < 4 or not row[1].startswith("https://") or not row[2] or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", row[3]):
            problems.append(f"incomplete source row: {row}")
    required = {"Google Rust Style Guide": "CC BY 3.0", "Microsoft Pragmatic Rust Guidelines": "MIT",
                "Rust API Guidelines": "Apache-2.0 or MIT", "Clippy documentation": "Apache-2.0 or MIT"}
    licences = {row[0]: row[2] for row in rows if len(row) > 2}
    for title, licence in required.items():
        if licences.get(title) != licence:
            problems.append(f"{title}: licence {licences.get(title)!r}")
    attribution = sections(text).get("Sources and attribution", "")
    for phrase in ("Creative Commons Attribution 3.0", "paraphrased and changed",
                   "Copyright (c) Microsoft Corporation", "MIT license",
                   "Copyright (c) The Rust Project Contributors"):
        if phrase not in attribution:
            problems.append(f"attribution missing: {phrase}")
    return problems


def platform_problems(text: str) -> list[str]:
    problems = []
    found = {e["heading"]: e for e in entries(text)}
    for name, entry in found.items():
        values = touches(entry)
        platforms = plain_lines(entry["map"].get("Cost and caveats", ""), "Platforms")
        if values - {"none"} and not (platforms and platforms[0]):
            problems.append(f"{name}: no Platforms line")
        prose = re.sub(r"(?m)^\s+(?:Touches|Platforms):.*$", "", entry["body"])
        for topic, pattern in TOPIC_PATTERNS.items():
            if re.search(pattern, prose) and topic not in values:
                problems.append(f"{name}: mentions {topic} but Touches is {sorted(values)}")
    for name, topic in PINNED_PLATFORM_ENTRIES.items():
        if name not in found or topic not in touches(found[name]):
            problems.append(f"pinned entry {name} lacks {topic}")
    return problems


def not_included_problems(text: str) -> list[str]:
    items = re.findall(r"(?m)^- (.+)$", sections(text).get("Not included", ""))
    problems = [] if items else ["no not-included items"]
    problems += [f"no reason: {item}" for item in items if not re.search(r":\s+\S", item)]
    return problems


def metadata_problems(text: str) -> list[str]:
    head = text.split("\n## ", 1)[0]
    problems = []
    for pattern in (r"(?m)^Owner: \S", r"(?m)^Status: active$", r"(?m)^Last verified: \d{4}-\d{2}-\d{2}$"):
        if not re.search(pattern, head):
            problems.append(f"metadata missing: {pattern}")
    usage = usage_statement(text)
    for phrase in ("a menu, not a policy", "own record", "governs",
                   "never enables a lint, adds a tool, or creates or edits a configuration file",
                   "operator's direction through an admitted change", "scoped decision",
                   "re-checks each lint", "pinned toolchain"):
        if phrase not in usage:
            problems.append(f"usage statement missing: {phrase}")
    return problems


def body_without_usage(text: str) -> str:
    usage = usage_statement(text)
    return outside_fences(text.replace(usage, "", 1) if usage else text)


def collected_archive(framework: Path, members: set[str]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for source, name in build_pack.collect_files(framework):
            if name in members:
                archive.write(source, name)
    return buffer.getvalue()


def set_stance(text: str, heading: str, stance: str) -> str:
    start = text.index("### " + heading + "\n")
    at = text.index("**Stance:** ", start)
    return text[:at] + "**Stance:** " + stance + text[text.index("\n", at):]


def replace_once(text: str, old: str, new: str) -> str:
    if old not in text:
        raise AssertionError(f"control anchor missing: {old!r}")
    return text.replace(old, new, 1)


class RustPracticesBaselineShapeTests(unittest.TestCase):
    def setUp(self):
        self.text = read_baseline()

    def test_entries_index_and_dispositions_parse(self):
        self.assertEqual(structure_problems(self.text), [])
        self.assertGreaterEqual(len(entries(self.text)), MIN_ENTRIES)

    def test_structure_controls_fail(self):
        first = entries(self.text)[0]
        check = "**Check:** " + first["map"]["Check"]
        stance = "**Stance:** " + first["map"]["Stance"]
        cost = "**Cost and caveats:**"
        controls = {
            "deleted field": replace_once(self.text, check, ""),
            "swapped fields": replace_once(replace_once(replace_once(
                self.text, "**Practice:**", "@@P@@"), "**Applies when:**", "**Practice:**"),
                "@@P@@", "**Applies when:**"),
            "unknown stance": replace_once(self.text, stance, "**Stance:** recommended"),
            "bold touches": replace_once(self.text, "  Touches: none", "**Touches:** none"),
            "missing index row": re.sub(r"(?m)^\| \[Default lints[^\n]*\n", "", self.text, count=1),
            "missing topic": re.sub(r"(?m)^\| Async \|[^\n]*\n", "", self.text, count=1),
            "too few entries": self.text.split("\n### ", 2)[0] + "\n### " + self.text.split("\n### ", 2)[1]
                               + "\n## Lints named\n" + sections(self.text)["Lints named"],
        }
        self.assertIn(cost, self.text)
        for name, mutant in controls.items():
            with self.subTest(control=name):
                self.assertTrue(structure_problems(mutant), name)

    def test_metadata_and_usage_statement(self):
        self.assertEqual(metadata_problems(self.text), [])
        for mutant in (self.text.replace("Status: active", "Status:", 1),
                       self.text.replace("a menu, not a policy", "a policy", 1)):
            self.assertTrue(metadata_problems(mutant))

    def test_settings_only_in_fences(self):
        self.assertEqual(setting_outside_fence_problems(self.text), [])
        mutant = replace_once(self.text, "**Cost and caveats:** A toolchain update",
                              "**Cost and caveats:** Set `unwrap_used = \"deny\"`. A toolchain update")
        self.assertTrue(setting_outside_fence_problems(mutant))
        mutant = replace_once(self.text, "**Cost and caveats:** A toolchain update",
                              "**Cost and caveats:** Run `cargo deny check`. A toolchain update")
        self.assertTrue(setting_outside_fence_problems(mutant))

    def test_no_agent_imperative_outside_usage_statement(self):
        self.assertEqual(imperative_hits(body_without_usage(self.text)), [])
        positive = replace_once(self.text, "**Cost and caveats:** A toolchain update",
                                "**Cost and caveats:** Enable the lint in the workspace file. A toolchain update")
        self.assertTrue(imperative_hits(body_without_usage(positive)))
        negated = replace_once(self.text, "**Cost and caveats:** A toolchain update",
                               "**Cost and caveats:** An agent must never enable this lint on its own. A toolchain update")
        self.assertEqual(imperative_hits(body_without_usage(negated)), [])

    def test_every_setting_lint_is_in_the_lints_named_table(self):
        self.assertEqual(lint_problems(self.text), [])
        unlisted = replace_once(self.text, 'implicit_clone = "warn"\n',
                                'implicit_clone = "warn"\nneedless_pass_by_value = "warn"\n')
        self.assertIn("lint not in table: needless_pass_by_value", lint_problems(unlisted))
        wrong_tool = replace_once(self.text, "| `unsafe_code` | rustc |", "| `unsafe_code` | Clippy |")
        self.assertTrue(lint_problems(wrong_tool))

    def test_lints_in_crate_root_attributes_are_cross_checked(self):
        entry = {e["heading"]: e for e in entries(self.text)}["Crates that need no unsafe code forbid it"]
        self.assertIn(("unsafe_code", "rustc"), setting_lints(entry))
        unlisted = replace_once(self.text, "#![forbid(unsafe_code)]", "#![forbid(unsafe_code, missing_copy_implementations)]")
        self.assertIn("lint not in table: missing_copy_implementations", lint_problems(unlisted))
        clippy = replace_once(self.text, "#![deny(clippy::indexing_slicing)]",
                              "#![deny(clippy::indexing_slicing, clippy::as_conversions)]")
        self.assertIn("lint not in table: as_conversions", lint_problems(clippy))

    def test_composing_settings_paragraph_follows_the_index(self):
        self.assertEqual(composing_problems(self.text), [])
        removed = re.sub(r"(?ms)^## Composing settings\n.*?(?=^## Entries)", "", self.text, count=1)
        self.assertIn("no Composing settings section", composing_problems(removed))
        self.assertTrue(composing_problems(replace_once(self.text, "not both", "or both")))

    def test_member_lint_tables_state_that_they_replace_inheritance(self):
        self.assertEqual(member_table_problems(self.text), [])
        mutant = replace_once(self.text, "```rust\n// at the crate root (lib.rs or main.rs) of each crate that needs no unsafe code\n"
                                         "#![forbid(unsafe_code)]\n```",
                              "```toml\n# in each crate's manifest\n[lints.rust]\nunsafe_code = \"forbid\"\n```")
        mutant = replace_once(mutant, "would replace inheritance for every lint", "would stop inheriting")
        self.assertIn("Crates that need no unsafe code forbid it: member lint table without the inheritance sentence",
                      member_table_problems(mutant))
        # The plain inheritance block is the default home, not a deviation, and needs no sentence.
        plain = replace_once(self.text, "its own table replaces inheritance for every lint; a crate-root attribute",
                             "its own table is used; a crate-root attribute")
        self.assertEqual(member_table_problems(plain), [])

    def test_panic_family_stances_are_pinned(self):
        self.assertEqual(panic_family_problems(self.text), [])
        mutant = set_stance(self.text, "Panic, unreachable and expect are denied outside tests", "adopt")
        self.assertIn("expect_used: stance adopt", panic_family_problems(mutant))

    def test_disagreements_are_single_situational_entries_with_both_positions(self):
        self.assertEqual(disagreement_problems(self.text), [])
        mutant = set_stance(self.text, "Error type shape", "propose")
        self.assertTrue(disagreement_problems(mutant))
        self.assertTrue(disagreement_problems(self.text.replace("The other position", "Another view", 1)))

    def test_adopt_entries_name_a_listed_recommending_source(self):
        self.assertEqual(source_problems(self.text), [])
        heading = "### Enums instead of unclear bool parameters"
        part = self.text.split(heading, 1)[1]
        sources = part.split("**Sources:** ", 1)[1].split("\n", 1)[0]
        mutant = self.text.replace("**Sources:** " + sources, "**Sources:** Common practice.", 1)
        self.assertIn("Enums instead of unclear bool parameters: adopt without a recommending source",
                      source_problems(mutant))

    def test_not_included_section_gives_reasons(self):
        self.assertEqual(not_included_problems(self.text), [])
        self.assertTrue(not_included_problems(
            re.sub(r"(?m)^(- Required allocators and internal build-system rules of any one company):.*$",
                   r"\1", self.text)))

    def test_platform_lines(self):
        self.assertEqual(platform_problems(self.text), [])
        deleted = re.sub(r"(?m)^\s+Platforms: Windows has no POSIX[^\n]*\n", "", self.text, count=1)
        self.assertIn("One module owns process spawning: no Platforms line", platform_problems(deleted))
        none = replace_once(self.text, "  Touches: processes\n  Platforms: Windows has no POSIX",
                            "  Touches: none\n  Platforms: Windows has no POSIX")
        self.assertTrue(platform_problems(none))
        mentioned = replace_once(self.text, "**Practice:** Code uses no unstable language or library features.",
                                 "**Practice:** Code uses no unstable language or library features, even when it calls a linker.")
        self.assertTrue(platform_problems(mentioned))

    def test_no_identifiers_or_reviewed_repository_names(self):
        self.assertEqual(identifier_hits(self.text), [])
        self.assertTrue(identifier_hits(self.text + "\nSee change 1abcd.\n"))
        self.assertTrue(identifier_hits(self.text + "\nAs in Tensorwell.\n"))


class RustPracticesBaselineDeliveryTests(unittest.TestCase):
    """Mechanical delivery evidence, modelled on the writing-guide delivery test."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.members = {BASELINE} | {f".wavefoundry/framework/seeds/{name}" for name in SEEDS}

    def assert_readable_reference(self, root: Path, text: str) -> None:
        self.assertNotRegex(text, r"\]\([^)]*rust-practices\.md", "baseline referenced as a Markdown link")
        references = re.findall(r"`([^`\n]*rust-practices[^`\n]*)`", text)
        self.assertTrue(references, "no baseline reference")
        for reference in references:
            self.assertEqual(reference, BASELINE, "stale or noncanonical baseline reference")
            self.assertTrue((root / reference).read_text(encoding="utf-8").strip(), "baseline is empty")

    def test_fresh_extraction_delivers_baseline_and_seed_references(self):
        payload = collected_archive(FRAMEWORK, self.members)
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            self.assertEqual(set(archive.namelist()), self.members)
            upgrade_wavefoundry._extract_feature_members(archive, self.root)
        self.assertEqual((self.root / BASELINE).read_bytes(), (REPO / BASELINE).read_bytes())
        for seed in SEEDS:
            with self.subTest(seed=seed):
                text = (self.root / ".wavefoundry/framework/seeds" / seed).read_text(encoding="utf-8")
                self.assert_readable_reference(self.root, text)
        self.assertEqual(structure_problems(read_baseline(self.root)), [])

    def test_missing_baseline_and_link_form_controls_are_rejected(self):
        payload = collected_archive(FRAMEWORK, self.members - {BASELINE})
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            upgrade_wavefoundry._extract_feature_members(archive, self.root)
        carrier = f"Consult `{BASELINE}` through its index."
        with self.assertRaises(FileNotFoundError):
            self.assert_readable_reference(self.root, carrier)
        with self.assertRaisesRegex(AssertionError, "Markdown link"):
            self.assert_readable_reference(self.root, f"See [the baseline]({BASELINE}).")
        with self.assertRaisesRegex(AssertionError, "stale or noncanonical"):
            self.assert_readable_reference(self.root, carrier.replace("docs/rust-practices", "docs/old-rust-practices"))


if __name__ == "__main__":
    unittest.main()
