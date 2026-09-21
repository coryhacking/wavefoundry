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

DASHBOARD_JS = SCRIPTS_ROOT.parent / "dashboard" / "dashboard.js"
DEFAULTS = {key: key for key in ("wave", "change", "task")}

# Skip comments and regex literals before examining strings, including templates.
# Hyphen/underscore-bound identifiers (CSS classes) are not display nouns.
TOKENS = re.compile(r'''//[^\n]*|/\*[\s\S]*?\*/|/(?![\s/])(?:\\.|\[(?:\\.|[^\]\\\n])*\]|[^/\\\n])+/[gimsuy]*|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|`(?:\\.|[^`\\])*`''')
NOUN = re.compile(r"(?<![\w-])(?:wave|change|task)s?(?![\w-])")
CAPITALIZED = re.compile(r"(?<![\w-])(?:Wave|Change|Task)s?(?![\w-])")
P_NOUN = re.compile(r'''\bp\([^;\n]*?,\s*["'](?:wave|change|task)s?["']\s*,\s*["'](?:wave|change|task)s?["']\s*\)''')

ALLOWLIST = {
    """`This is where an idea becomes a real change. You clarify what is in scope, what is out of scope, and why the change matters before anyone starts editing files.

That early clarity matters because every later stage depends on it. If the scope is fuzzy, the wave gets harder to review, harder to implement, and easier to drift. When the plan is still unclear, the right move is to stay here and resolve the unknowns before the wave moves forward.`""": 'Framework lifecycle explanatory body intentionally stays canonical.',
    """`This is the readiness gate. The council reviews the change, works through the open questions, and decides whether the wave is actually safe to start.

This phase matters because it catches avoidable mistakes before code or docs start moving. It is not just a paperwork step; it is where the wave earns the right to begin. If the evidence is thin, the dependencies are unclear, or the change still feels too broad, the wave goes back to planning instead of pretending it is ready.

When Prepare is done well, the team has a shared picture of what will happen next, what is still uncertain, and what the operator needs to watch closely during implementation.`""": 'Framework lifecycle explanatory body intentionally stays canonical.',
    """`This is the coding pass. Once Prepare says the wave is ready, the coding agent takes over and uses the wave record plus each admitted change plan as the working guide.

The first job is to read the wave and the change docs carefully enough to understand what belongs in scope. Then the work happens one change at a time: make the edits that match the plan, check the tasks and acceptance criteria, and keep the write set inside the admitted boundaries.

Implementation is not just about moving text around. The agent also writes or updates tests, runs them, and confirms that the result matches the agreed intent instead of drifting into a new shape of work. If the change no longer matches what Prepare approved, the right move is to stop and send it back for another pass instead of widening the scope on the fly.

When the code, tests, and documented intent line up, the wave is ready for review. The implementation phase is successful when it leaves behind a small, understandable set of edits that another reviewer can inspect without guessing how the change was made.`""": 'Framework lifecycle explanatory body intentionally stays canonical.',
    """`This is the evidence check. Reviewers compare what actually changed against what the wave promised, looking for missing behavior, drift, or anything that still needs correction.

Review matters because it is where the team decides whether the change is genuinely ready or whether more work is needed. This is the phase that keeps optimism from outrunning proof. Findings do not mean failure; they mean the wave should iterate back to Implement or even Prepare until the gaps are closed and the evidence lines up.

When the review is strong, it gives the operator confidence that the change is not just present, but actually matches the wave's intent and acceptance criteria.`""": 'Framework lifecycle explanatory body intentionally stays canonical.',
    """`This is the handoff and memory stage. Once the wave is signed off, the team archives what shipped, records the important lessons, and makes sure a future session can understand what happened without reconstructing it from scratch.

This phase matters because the work is not done when the code stops changing. The framework still needs a durable record of what shipped, what decisions mattered, and what a future operator should know before they try to extend it. If the handoff or summary does not match the completed wave, the process loops one more time to refresh the record before closure.

That is what keeps the system useful over time: closure is not just an ending, it is the point where the wave becomes usable memory.`""": 'Framework lifecycle explanatory body intentionally stays canonical.',
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
            ({"feature": "Feature", "set": "Set", "wave": "Wave", "task": "Task"}, {"wave": "Wave", "change": "change", "task": "Task"}, ["feature", "set"]),
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
  const progress = context.ProgressCard({snapshot: {}, scopeChanges: []});
  const waves = context.WavesCard({waves: [{status: 'closed'}], allChanges: []});
  const tasks = context.WaveTasks({tasksTotal: 2, tasksDone: 1});
  return [classes(flow, 'framework-flow-heading')[0], ...classes(flow, 'framework-flow-card-title'), ...steps,
    ...nodes(progress).filter(n => n.tag === 'label').map(text), text(nodes(waves).find(n => n.tag === 'h2')),
    ...classes(waves, 'empty-state'), ...nodes(waves).filter(n => n.tag === 'p').map(text),
    ...nodes(tasks).filter(n => n.tag === 'label').map(text)];
};
const defaults = ['Wave lifecycle', 'Plan Change', 'Prepare Wave', 'Implement Wave', 'Review Wave', 'Close & Maintain',
  'Idea', 'Scope', 'Admitted change', 'Review', 'Open questions', 'Prepare Wave', 'Wave + change plans', 'Implement each change', 'Check tasks + ACs', 'Write tests', 'Prepare for review', 'Review', 'Evidence', 'Findings', 'Signoff', 'Archive',
  'Waves', 'Changes', 'ACs', 'Tasks', 'Waves', 'No active waves.', '1 closed wave.', 'Tasks'];
assert.deepEqual(collect(), defaults);
context.updateTerminology({wave: 'Sprint', change: 'Story', task: 'Step'});
assert.deepEqual(collect(), defaults.map(s => s.replace(/Wave/g, 'Sprint').replace(/wave/g, 'sprint').replace(/Change/g, 'Story').replace(/change/g, 'story').replace(/Task/g, 'Step').replace(/task/g, 'step')));
assert.equal(context.tierLabel('change', true), 'storys');
const flow = context.FrameworkFlow({onSelectProcess: () => {}});
assert.ok(nodes(flow).some(n => n.props['aria-label'] === 'Sprint Framework process flow'));
assert.ok(nodes(flow).some(n => n.props['aria-label'] === 'Open Prepare Sprint'));
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
