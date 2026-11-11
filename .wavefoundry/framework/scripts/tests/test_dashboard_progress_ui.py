"""Execute the Progress card and shipped design-system primitive (wave 2347r)."""
from __future__ import annotations

import json
import shutil
import subprocess
import unittest
from pathlib import Path


DASHBOARD = Path(__file__).resolve().parents[2] / "dashboard"


@unittest.skipUnless(shutil.which("node"), "Node is needed to execute dashboard component controls")
class ProgressCardRenderingTests(unittest.TestCase):
    def render(self, progress, *, source_replacement=None):
        script = r"""
const fs = require('node:fs');
const vm = require('node:vm');
const input = JSON.parse(fs.readFileSync(0, 'utf8'));
let source = fs.readFileSync(process.argv[1], 'utf8');
if (input.replacement) source = source.replace(...input.replacement);
const h = (tag, props, ...children) => typeof tag === 'function'
  ? tag({...props, children})
  : ({tag, props: props || {}, children: children.flat(Infinity).filter(x => x != null && x !== false)});
const context = {h, React: {createElement: h}, tierLabel: (name, plural, capital) => {
  const label = name + (plural ? 's' : '');
  return capital ? label[0].toUpperCase() + label.slice(1) : label;
}};
vm.createContext(context);
vm.runInContext(fs.readFileSync(process.argv[2], 'utf8'), context);
vm.runInContext(source.slice(source.indexOf('function ProgressRow('), source.indexOf('// MiniGraph')), context);
const tree = context.ProgressCard({snapshot: {progress: input.progress}});
const nodes = node => typeof node === 'object' ? [node, ...node.children.flatMap(nodes)] : [];
const text = node => typeof node === 'object' ? node.children.map(text).join(' ') : String(node);
console.log(JSON.stringify({text: text(tree), bars: nodes(tree).filter(n => n.props.role === 'progressbar').map(n => n.props),
  fractions: nodes(tree).filter(n => n.props.className === 'progress-row-fraction').map(text),
  statuses: nodes(tree).filter(n => n.props.role === 'status').map(text)}));
"""
        result = subprocess.run(
            [shutil.which("node"), "-e", script, str(DASHBOARD / "dashboard.js"), str(DASHBOARD / "ds/wfds.js")],
            input=json.dumps({"progress": progress, "replacement": source_replacement}),
            capture_output=True, text=True, timeout=15,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    @staticmethod
    def fixture():
        return {
            "waves": {"done": 2, "total": 6},
            "changes": {"done": 4, "total": 8},
            "criteria": {"done": 3, "deferred": 3, "open": 5, "total": 11, "not_this_scope": 1},
            "tasks": {"done": 4, "deferred": 2, "open": 6, "total": 12},
            "coverage": {"complete": False, "missing_admitted_documents": 1,
                         "unreadable_change_documents": 1, "warning": "Checklist coverage incomplete."},
        }

    def assert_fixture_counts(self, rendered):
        self.assertEqual(rendered["fractions"], ["2/6", "4/8", "3/11", "4/12"])
        for phrase in (
            "Lifecycle status: 2 of 6 complete", "Lifecycle status: 4 of 8 complete",
            "Done 3 · Deferred 3 · Open 5 · Total 11", "Done 4 · Deferred 2 · Open 6 · Total 12",
            "Not-this-scope criteria: 1 (excluded from total)",
            "Changes assigned to waves: acceptance criteria and implementation tasks. Plans not assigned to a wave are separate.",
        ):
            self.assertIn(phrase, rendered["text"])
        self.assertEqual(rendered["statuses"], ["Checklist coverage incomplete.  Missing admitted documents: 1; unreadable: 1."])
        self.assertEqual([bar["aria-valuenow"] for bar in rendered["bars"]], [33, 50, 27, 33])

    def test_renders_shared_states_and_incomplete_coverage(self):
        self.assert_fixture_counts(self.render(self.fixture()))

    def test_missing_progress_or_row_is_unavailable_not_zero(self):
        for progress in (None, {}):
            rendered = self.render(progress)
            self.assertEqual(rendered["bars"], [])
            self.assertEqual(rendered["fractions"], [])
            for label in ("Waves", "Changes", "Acceptance criteria", "Implementation tasks"):
                self.assertIn(label + ": unavailable", rendered["text"])
            self.assertEqual(rendered["statuses"], ["Checklist coverage unavailable."])
        progress = self.fixture()
        del progress["tasks"]["deferred"]
        rendered = self.render(progress)
        self.assertIn("Implementation tasks: unavailable", rendered["text"])
        self.assertEqual(rendered["fractions"], ["2/6", "4/8", "3/11"])

    def test_returned_zero_counts_are_visible(self):
        progress = self.fixture()
        for name in ("waves", "changes", "criteria", "tasks"):
            progress[name] = {key: 0 for key in progress[name]}
        progress["coverage"] = {"complete": True, "missing_admitted_documents": 0, "unreadable_change_documents": 0}
        rendered = self.render(progress)
        self.assertEqual(rendered["fractions"], ["0/0"] * 4)
        self.assertEqual(rendered["text"].count("Done 0 · Deferred 0 · Open 0 · Total 0"), 2)
        self.assertEqual(rendered["statuses"], [])

    def test_wrong_state_label_is_detected(self):
        rendered = self.render(self.fixture(), source_replacement=("Deferred ${counts.deferred}", "Deferred ${counts.done}"))
        with self.assertRaises(AssertionError):
            self.assert_fixture_counts(rendered)


if __name__ == "__main__":
    unittest.main()
