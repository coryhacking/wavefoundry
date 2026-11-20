"""Dashboard terminology contract: real producers, literal census and rendered slices."""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_ROOT))
import dashboard_lib
import vocabulary_profile

DASHBOARD_JS = SCRIPTS_ROOT.parent / "dashboard" / "dashboard.js"
# The register keys stay canonical; their default labels follow the loaded
# vocabulary profile (the shipped profile's are the keys themselves).
DEFAULTS = {
    "wave": vocabulary_profile.CONTAINER_NAME.lower(),
    "change": vocabulary_profile.ITEM_NAME.lower(),
    "task": "task",
}

# Skip comments and regex literals before examining strings, including templates.
# Hyphen/underscore-bound identifiers (CSS classes) are not display nouns.
TOKENS = re.compile(r'''//[^\n]*|/\*[\s\S]*?\*/|/(?![\s/])(?:\\.|\[(?:\\.|[^\]\\\n])*\]|[^/\\\n])+/[gimsuy]*|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|`(?:\\.|[^`\\])*`''')
NOUN = re.compile(r"(?<![\w-])(?:wave|change|task)s?(?![\w-])")
CAPITALIZED = re.compile(r"(?<![\w-])(?:Wave|Change|Task)s?(?![\w-])")
P_NOUN = re.compile(r'''\bp\([^;\n]*?,\s*["'](?:wave|change|task)s?["']\s*,\s*["'](?:wave|change|task)s?["']\s*\)''')

ALLOWLIST = {
    '"Recent changes"': 'Git activity heading, not the change tier.',
}


def census(source: str) -> list[str]:
    hits = []
    for token in TOKENS.finditer(source):
        literal = token.group()
        if literal[0] not in "\"'`":
            continue
        # Expressions use canonical identifiers; only the rendered text is a label.
        rendered = re.sub(r"\$\{[^}]*\}", "", literal[1:-1])
        if CAPITALIZED.search(rendered) or (" " in rendered and NOUN.search(rendered)):
            hits.append(literal)
    hits.extend(match.group() for match in P_NOUN.finditer(source))
    return hits


class DashboardTerminologyTests(unittest.TestCase):
    def test_snapshot_uses_the_selected_checkouts_planning_shortcut(self):
        from unittest import mock
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = root / "docs/prompts"
            folder.mkdir(parents=True)
            manifest = {"prompt_names": {"plan-change": "design-ticket"},
                        "public_prompt_surface": [{"doc": "docs/prompts/design-ticket.prompt.md",
                                                   "shortcut": "Draft a ticket"}]}
            (folder / "prompt-surface-manifest.json").write_text(json.dumps(manifest))
            with mock.patch.multiple(dashboard_lib._vocab, ITEM_NAME="Ticket", CONTAINER_NAME="Batch"):
                config = dashboard_lib.collect_dashboard_snapshot(root, skip_git=True)["config"]
            self.assertEqual(config["planning"],
                             {"shortcut": "Draft a ticket", "doc": "ticket doc", "docs": "ticket docs"})

    def test_custom_shortcut_stays_within_selected_checkout(self):
        from unittest import mock
        with tempfile.TemporaryDirectory() as tmp:
            parent = Path(tmp)
            root = parent / "selected"
            folder = root / "docs/prompts"
            folder.mkdir(parents=True)
            other = parent / "other-manifest.json"
            other.write_text('{"public_prompt_surface": []}')
            try:
                (folder / "prompt-surface-manifest.json").symlink_to(other)
            except OSError as exc:
                self.skipTest(f"Symlinks unavailable: {exc}")
            with mock.patch.multiple(dashboard_lib._vocab, ITEM_NAME="Ticket", CONTAINER_NAME="Batch"):
                config = dashboard_lib.collect_dashboard_snapshot(root, skip_git=True)["config"]
            self.assertEqual(config["planning"]["shortcut"], "Planning shortcut unavailable")
            self.assertEqual(dashboard_lib.read_prompt_manifest(root), {})

    def test_real_reader_normalizes_without_changing_other_fields(self):
        cases = [
            ({}, DEFAULTS, []),
            ({"terminology": None}, DEFAULTS, []),
            ({"terminology": ["wave"]}, DEFAULTS, []),
            ({"terminology": "sprint"}, DEFAULTS, []),
            ({"terminology": {"wave": " Sprint ", "change": "Story", "task": "Step"}},
             {"wave": "Sprint", "change": "Story", "task": "Step"}, []),
            ({"terminology": {"set": "Set", "feature": "Feature", "wave": 2, "change": None, "task": False}},
             DEFAULTS, ["change", "feature", "set", "task", "wave"]),
            ({"terminology": {"wave": "", "change": "  ", "task": []}}, DEFAULTS, ["change", "task", "wave"]),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "docs").mkdir()
            config = root / "docs/workflow-config.json"
            preserved = {"poll_interval_ms": 3123, "entrypoint": "viewer.html", "project_label": "Demo", "host": "localhost", "preferred_port": 43200, "include_dirs": ["extra"]}
            config.write_text(json.dumps({"dashboard": preserved}))
            baseline = dashboard_lib.read_dashboard_config(root)
            for block, expected, ignored in cases:
                with self.subTest(block=block):
                    config.write_text(json.dumps({"dashboard": {**preserved, **block}}))
                    actual = dashboard_lib.read_dashboard_config(root)
                    self.assertEqual(actual.pop("terminology"), expected)
                    self.assertEqual(actual.pop("terminology_ignored"), ignored)
                    self.assertEqual(actual, {k: v for k, v in baseline.items() if k not in ("terminology", "terminology_ignored")})

    def test_real_snapshot_publishes_normalized_register_and_ignored_keys(self):
        for supplied, expected, ignored in [
            ({"wave": "Sprint", "change": "Story", "task": "Step"}, {"wave": "Sprint", "change": "Story", "task": "Step"}, []),
            (None, DEFAULTS, []),
            ({"feature": "Feature", "set": "Set", "wave": "Wave", "task": "Task"}, {"wave": "Wave", "change": DEFAULTS["change"], "task": "Task"}, ["feature", "set"]),
        ]:
            with self.subTest(supplied=supplied), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                (root / "docs").mkdir()
                dashboard = {} if supplied is None else {"terminology": supplied}
                (root / "docs/workflow-config.json").write_text(json.dumps({"dashboard": dashboard}))
                config = dashboard_lib.collect_dashboard_snapshot(root, skip_git=True)["config"]
                self.assertEqual(config["terminology"], expected)
                self.assertEqual(config["terminology_ignored"], ignored)

    def test_literal_census_and_stale_allowlist(self):
        hits = census(DASHBOARD_JS.read_text())
        self.assertEqual(set(hits) - ALLOWLIST.keys(), set())
        self.assertEqual(ALLOWLIST.keys() - set(hits), set(), "stale allowlist")
        self.assertTrue(all(ALLOWLIST.values()))

    def test_census_polarity_mutant_and_identifier_controls(self):
        source = DASHBOARD_JS.read_text()
        baseline = Counter(census(source))
        self.assertEqual(Counter(census(source + '\nconst mutant = "Prepare Wave";')) - baseline, Counter({'"Prepare Wave"': 1}))
        for sample in ['"Prepare Wave"', '"No active waves."', 'p(n, "task", "tasks")', '`Prepare Wave ${tierLabel("change")}`']:
            self.assertTrue(census(sample), sample)
        for sample in ['"wave-change-id id-link"', '"tasks"', '`/api/doc?type=wave&id=${id}`', '`${base}&wave=${encodeURIComponent(change.wave_id || "")}`', '`Prepare ${tierLabel("wave")}`']:
            self.assertEqual(census(sample), [], sample)

    def test_dashboard_wires_advisory_inside_hero_meta(self):
        source = DASHBOARD_JS.read_text()
        dashboard = source[source.index('function Dashboard('):source.index('function ErrorView(')]
        hero = dashboard[dashboard.index('className: "hero-meta"'):dashboard.index('h(Metrics,')]
        self.assertIn('h(GitPills, { git: snapshot.git })', hero)
        self.assertIn('h(TerminologyAdvisoryPill, { ignored: snapshot.config?.terminology_ignored })', hero)

    @unittest.skipUnless(shutil.which("node"), "Node needed for dashboard render slices")
    def test_rendered_labels_and_advisory(self):
        result = subprocess.run([shutil.which("node"), "-e", RENDER_SCRIPT, str(DASHBOARD_JS)], text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


class DashboardDoneStatusTests(unittest.TestCase):
    """Wave 1zoju (1zody): the dashboard counts a change done by the lint
    constants' one done set, in Python and in the page."""

    def test_predicate_reproducer(self):
        """AC-1: `implemented` and `deferred` are done, `closed` is not."""
        self.assertTrue(dashboard_lib._is_terminal_change_status("implemented"))
        self.assertTrue(dashboard_lib._is_terminal_change_status("deferred"))
        self.assertFalse(dashboard_lib._is_terminal_change_status("closed"))

    def test_predicate_reads_the_constant(self):
        """AC-2: agreement on every change status, and a patch reaches it."""
        from unittest import mock
        constants = dashboard_lib._lint_constants()  # the module the predicate reads at call time
        for status in [*constants.ALLOWED_CHANGE_STATUS_TRANSITIONS, "closed", "approved"]:
            with self.subTest(status=status):
                self.assertEqual(dashboard_lib._is_terminal_change_status(f" {status.upper()} "),
                                 status in constants.DONE_CHANGE_STATUSES)
        with mock.patch.object(constants, "DONE_CHANGE_STATUSES", frozenset({"planned"})):
            self.assertTrue(dashboard_lib._is_terminal_change_status("planned"))
            self.assertFalse(dashboard_lib._is_terminal_change_status("complete"))

    def test_snapshot_carries_the_done_set(self):
        """AC-3."""
        from wave_lint_lib import constants
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "docs").mkdir()
            config = dashboard_lib.collect_dashboard_snapshot(root, skip_git=True)["config"]
        self.assertEqual(config["done_change_statuses"], sorted(constants.DONE_CHANGE_STATUSES))

    def test_no_status_list_remains(self):
        """AC-5: no literal inside the page's done set, none in the module."""
        import ast
        from wave_lint_lib import constants
        source = DASHBOARD_JS.read_text()
        start = source.index("const DONE_STATUSES")
        definition = source[start:source.index("function isDone(", start)]
        self.assertEqual(re.findall(r'"[^"]*"|\'[^\']*\'', definition), [], definition)
        statuses = {*constants.ALLOWED_CHANGE_STATUS_TRANSITIONS, *constants.DONE_CHANGE_STATUSES, "closed", "approved"}
        tree = ast.parse((SCRIPTS_ROOT / "dashboard_lib.py").read_text())
        for node in tree.body:
            if isinstance(node, (ast.Assign, ast.AnnAssign)):
                literals = {n.value for n in ast.walk(node) if isinstance(n, ast.Constant) and isinstance(n.value, str)}
                self.assertFalse(literals & statuses and any(isinstance(n, (ast.Set, ast.Call)) for n in ast.walk(node)),
                                 ast.unparse(node))

    @unittest.skipUnless(shutil.which("node"), "Node needed for dashboard render slices")
    def test_page_reads_the_payload(self):
        """AC-4: the payload decides; App refills the set in its render body."""
        result = subprocess.run([shutil.which("node"), "-e", DONE_SCRIPT, str(DASHBOARD_JS)], text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        source = DASHBOARD_JS.read_text()
        app = source[source.index("function App() {"):]
        self.assertIn("updateTerminology(snapshot?.config?.terminology, snapshot?.config?.planning);\n  updateDoneStatuses(snapshot?.config?.done_change_statuses);", app)


DONE_SCRIPT = r'''
const assert = require('node:assert/strict'), fs = require('node:fs'), vm = require('node:vm');
const source = fs.readFileSync(process.argv[1], 'utf8');
const context = {};
vm.createContext(context);
vm.runInContext(source.slice(source.indexOf('const DONE_STATUSES'), source.indexOf('function waveStatus(')), context);
assert.equal(context.isDone('implemented'), false, 'empty before the first snapshot');
context.updateDoneStatuses({config: {done_change_statuses: ['complete', 'implemented']}}.config.done_change_statuses);
assert.equal(context.isDone('implemented'), true);
assert.equal(context.isDone('IMPLEMENTED'), true);
assert.equal(context.isDone('approved'), false);
assert.equal(context.isDone('done'), false);
context.updateDoneStatuses(['Done']);
assert.equal(context.isDone('done'), true);
assert.equal(context.isDone('complete'), false, 'the set is refilled, not extended');
context.updateDoneStatuses(undefined);
assert.equal(context.isDone('done'), false);
console.log('done statuses follow the payload');
'''


RENDER_SCRIPT = r'''
const assert = require('node:assert/strict'), fs = require('node:fs'), vm = require('node:vm');
const source = fs.readFileSync(process.argv[1], 'utf8');
const h = (tag, props, ...children) => typeof tag === 'function' ? tag({...props, children}) : ({tag, props: props || {}, children: children.flat(Infinity).filter(x => x != null && x !== false)});
const context = {h, React: {Fragment: 'fragment'}, WFDS: {ProgressBar: ({label}) => h('label', {}, label)}, MiniGraph: ({label}) => h('label', {}, label)};
vm.createContext(context);
const slice = (start, end) => source.slice(source.indexOf(start), source.indexOf(end));
vm.runInContext(slice('const p =', 'function relativeAge(') + slice('const DONE_STATUSES', 'function FrameworkProcessDiagram(') + slice('function FrameworkProcessDiagram(', '// ── Dark mode hook') + slice('function TerminologyAdvisoryPill(', 'function Metrics('), context);
const nodes = node => node && typeof node === 'object' ? [node, ...node.children.flatMap(nodes)] : [];
const text = node => node && typeof node === 'object' ? node.children.map(text).join('') : String(node ?? '');
const classes = (tree, cls) => nodes(tree).filter(n => n.props.className === cls).map(text);
const collect = () => {
  const flow = context.FrameworkFlow({onSelectProcess: () => {}});
  const steps = context.FRAMEWORK_FLOW().flatMap(process => classes(context.FrameworkProcessDiagram({process}), 'framework-process-diagram-step-label'));
  const progress = context.ProgressCard({snapshot: {progress: {
    waves: {done: 0, total: 0}, changes: {done: 0, total: 0},
    criteria: {done: 0, deferred: 0, open: 0, total: 0, not_this_scope: 0},
    tasks: {done: 0, deferred: 0, open: 0, total: 0}, coverage: {complete: true},
  }}});
  const waves = context.WavesCard({waves: [{status: 'closed'}], allChanges: []});
  const tasks = context.WaveTasks({tasksTotal: 2, tasksDone: 1});
  return [classes(flow, 'framework-flow-heading')[0], ...classes(flow, 'framework-flow-card-title'), ...steps,
    ...nodes(progress).filter(n => n.tag === 'label').map(text), text(nodes(waves).find(n => n.tag === 'h2')),
    ...classes(waves, 'empty-state'), ...nodes(waves).filter(n => n.tag === 'p').map(text),
    ...nodes(tasks).filter(n => n.tag === 'label').map(text)];
};
const defaults = ['Wave lifecycle', 'Plan spec', 'Prepare Wave', 'Implement Wave', 'Review Wave', 'Close & Maintain',
  'Idea', 'Scope', 'Draft spec', 'Review', 'Open questions', 'Prepare Wave', 'Wave + specs', 'Implement', 'Check tasks + ACs', 'Run tests', 'Prepare for review', 'Review', 'Evidence', 'Findings', 'Signoff', 'Archive',
  'Waves', 'Changes', 'Acceptance criteria', 'Implementation tasks', 'Waves', 'No active waves.', '1 closed wave.', 'Tasks'];
assert.deepEqual(collect(), defaults);
context.updateTerminology({wave: 'Sprint', change: 'Story', task: 'Step'});
assert.deepEqual(collect(), defaults.map(s => s.replace(/Wave/g, 'Sprint').replace(/wave/g, 'sprint').replace(/Change/g, 'Story').replace(/change/g, 'story').replace(/Task/g, 'Step').replace(/task/g, 'step')));
assert.equal(context.tierLabel('change', true), 'storys');
const flow = context.FrameworkFlow({onSelectProcess: () => {}});
assert.ok(nodes(flow).some(n => n.props['aria-label'] === 'Sprint Framework process flow'));
assert.ok(nodes(flow).some(n => n.props['aria-label'] === 'Open Prepare Sprint'));
context.updateTerminology({wave: 'Batch', change: 'Ticket'}, {shortcut: 'Draft a ticket', doc: 'ticket doc', docs: 'ticket docs'});
let selected;
const customFlow = context.FrameworkFlow({onSelectProcess: process => { selected = process; }});
nodes(customFlow).find(n => n.props['aria-label'] === 'Open Draft a ticket').props.onClick();
assert.equal(selected.id, 'plan');
context.renderMarkdownish = content => h('p', {}, content);
context.DialogFrame = ({children}) => h('section', {}, ...children);
assert.match(text(context.FrameworkProcessDialog({process: selected})), /Use this stage to write the ticket doc/);
for (const stage of context.FRAMEWORK_FLOW()) {
  const detail = text(context.FrameworkProcessDialog({process: stage}));
  assert.doesNotMatch(detail, /\b(?:waves?|specs?)\b/i);
}
context.updateTerminology(undefined);
assert.deepEqual(collect(), defaults, 'register reset must affect flow after first render');
const pill = context.TerminologyAdvisoryPill({ignored: ['set', 'feature']});
assert.equal(nodes(pill).length, 1);
assert.equal(pill.props.className, 'meta-pill');
assert.equal(text(pill), 'Ignored terminology keys: feature, set');
assert.equal(context.TerminologyAdvisoryPill({ignored: []}), null);
assert.equal(context.TerminologyAdvisoryPill({}), null);
console.log('default/sprint-story render slices and advisory presence/absence passed');
'''
