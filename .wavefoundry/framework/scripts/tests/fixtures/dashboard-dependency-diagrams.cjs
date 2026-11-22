// Exercise the shipped Markdown renderer and offline layout without installing a browser.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const dashboard = process.argv[2];
const ELK = require(path.join(dashboard, "vendor/elkjs/elk.bundled.js"));
const implementation = fs.readFileSync(path.join(dashboard, "ds/wfds.js"), "utf8");
const labels = {
  marker: "Fix the seed 070 marker requirement",
  ruling: "Clarify trusted ruling and timing",
  docs: "Docs-contract verifies",
  code: "Code verifies",
  qa: "QA verifies",
  security: "Security verifies",
  reassess: "Reassess readiness",
};
const pilot = [
  "flowchart LR",
  '  marker["Fix the seed 070 marker requirement"] --> docs["Docs-contract verifies"]',
  '  marker --> code["Code verifies"]',
  '  marker --> qa["QA verifies"]',
  '  ruling["Clarify trusted ruling and timing"] --> security["Security verifies"]',
  '  docs --> reassess["Reassess readiness"]',
  "  code --> reassess",
  "  qa --> reassess",
  "  security --> reassess",
].join("\n");
const expected = [
  ["marker", "docs"], ["marker", "code"], ["marker", "qa"], ["ruling", "security"],
  ["docs", "reassess"], ["code", "reassess"], ["qa", "reassess"], ["security", "reassess"],
].map(([from, to]) => [labels[from], labels[to]]);

function fenced(body, language = "mermaid") {
  return "```" + language + "\n" + body + "\n```";
}

function children(node) {
  return [...(node.children || [])].flat(Infinity).filter(n => n != null && n !== false);
}

function elements(node, type) {
  if (typeof node !== "object") return [];
  return [...(node.type === type ? [node] : []), ...children(node).flatMap(n => elements(n, type))];
}

function text(node) {
  if (typeof node !== "object") return String(node);
  return children(node).map(text).join("");
}

// Only effects and component state cross the parser/layout boundary under test.
function renderer(Layout = ELK) {
  let state = null, effect, cleanup;
  const React = {
    createElement(type, props, ...children) { return { type, props: props || {}, children }; },
    useState() { return [state, next => { state = next; }]; },
    useId() { return ":diagram-1:"; },
    useEffect(nextEffect) { effect = nextEffect; },
  };
  const document = {
    createElement(tag) {
      assert.equal(tag, "canvas");
      return { getContext: () => ({ measureText: label => ({ width: label.length * 8 }) }) };
    },
  };
  const window = { React, ELK: Layout, document };
  vm.runInNewContext(implementation, { window, console }, { filename: "wfds.js" });
  return {
    markdown: window.WFDS.renderMarkdownish,
    paint(node) {
      return typeof node.type === "function" ? node.type(node.props) : node;
    },
    commit() { cleanup = effect(); },
    unmount() { cleanup(); },
  };
}

function assertSource(node, source) {
  assert.equal(node.type, "pre");
  assert.equal(elements(node, "code").length, 1);
  assert.equal(text(node), source);
}

async function renderDiagram(source) {
  let layoutFinished;
  const drawn = new Promise(resolve => { layoutFinished = resolve; });
  class ObservedELK extends ELK {
    async layout(graph) {
      // ELK runs in Node’s realm while WFDS runs inside vm. Normalize the input arrays.
      const result = await super.layout(JSON.parse(JSON.stringify(graph)));
      layoutFinished(result);
      return result;
    }
  }
  const ui = renderer(ObservedELK);
  const blocks = ui.markdown(["Before", fenced(source), fenced("literal", "txt"), "After"].join("\n\n"));
  assert.deepEqual(Array.from(blocks, n => typeof n.type === "function" ? "diagram" : n.type),
    ["p", "diagram", "pre", "p"]);
  assertSource(blocks[2], "literal");
  const component = blocks[1];
  assertSource(ui.paint(component), source);
  ui.commit();
  const layout = await drawn;
  await new Promise(resolve => setImmediate(resolve));
  return { figure: ui.paint(component), layout };
}

function inspectFigure(figure) {
  const [svg] = elements(figure, "svg");
  assert.ok(svg, "expected a rendered diagram");
  const nodes = elements(svg, "g").filter(group => elements(group, "rect").length === 1);
  const boxes = nodes.map(group => ({
    ...elements(group, "rect")[0].props, label: text(elements(group, "text")[0]),
  }));
  function endpoint([x, y]) {
    const matches = boxes.filter(box => x >= box.x && x <= box.x + box.width &&
      y >= box.y && y <= box.y + box.height);
    assert.equal(matches.length, 1, "arrow endpoint must meet one box");
    return matches[0].label;
  }
  const [marker] = elements(svg, "marker");
  const routes = elements(svg, "polyline").map(line => {
    assert.equal(line.props.markerEnd, "url(#" + marker.props.id + ")");
    const points = line.props.points.split(" ").map(p => p.split(",").map(Number));
    return { line, points, from: endpoint(points[0]), to: endpoint(points.at(-1)) };
  });
  return { svg, boxes, routes };
}

async function renderPilot() {
  const { figure, layout } = await renderDiagram(pilot);
  const { svg, boxes, routes } = inspectFigure(figure);
  assert.equal(boxes.length, 7);
  assert.deepEqual(elements(svg, "text").map(text).sort(), Object.values(labels).sort());
  assert.deepEqual(routes.map(({ from, to }) => [from, to]).sort(), expected.slice().sort());
  assert.deepEqual(elements(figure, "summary").map(text), ["Dependencies"]);
  assert.deepEqual(elements(figure, "li").map(text).sort(),
    expected.map(([from, to]) => from + " must finish before " + to).sort());
  return layout;
}

// Two differently labeled parallel routes and a second source entering the same target.
const walkthrough = [
  "flowchart LR",
  '  view["View"] -->|  calls  | store["Store"]',
  "  view -->|reads from| store",
  '  job["Job"] -->|rebuilds| store',
].join("\n");
const triples = [["View", "calls", "Store"], ["View", "reads from", "Store"], ["Job", "rebuilds", "Store"]];

// Distance from a rendered text box to the nearest segment of an orthogonal route.
// The canvas stub measures 8 px per UTF-16 unit; ELK reserves 20 px of label height.
function gapToRoute(label, points) {
  const { x, y } = label.props;
  const halfWidth = text(label).length * 4;
  return Math.min(...points.slice(1).map(([bx, by], i) => {
    const [ax, ay] = points[i];
    assert.ok(ax === bx || ay === by);
    const dx = Math.max(0, Math.min(ax, bx) - x - halfWidth, x - halfWidth - Math.max(ax, bx));
    const dy = Math.max(0, Math.min(ay, by) - y - 10, y - 10 - Math.max(ay, by));
    return Math.hypot(dx, dy);
  }));
}

function assertWalkthrough(figure, expectedTriples) {
  const { svg, routes } = inspectFigure(figure);
  const groups = elements(svg, "g").filter(group => elements(group, "polyline").length === 1);
  assert.equal(groups.length, routes.length);
  const visible = groups.map(group => {
    const [line] = elements(group, "polyline");
    const { from, to } = routes.find(route => route.line === line);
    const texts = elements(group, "text");
    assert.equal(texts.length, 1, "each route needs one visible verb");
    return [from, text(texts[0]), to];
  });
  assert.deepEqual(visible.sort(), expectedTriples.slice().sort(), "visible relationship triples");
  assert.deepEqual(elements(figure, "summary").map(text), ["Relationships"]);
  assert.deepEqual(elements(figure, "li").map(text).sort(), visible.map(edge => edge.join(" ")).sort(),
    "accessible relationships must describe the visible arrows");
  for (const group of groups) {
    const [label] = elements(group, "text");
    const [line] = elements(group, "polyline");
    const route = routes.find(route => route.line === line);
    const ownGap = gapToRoute(label, route.points);
    assert.ok(ownGap <= 6, "label must be adjacent to its own route: " + text(label));
    for (const other of routes.filter(other => other !== route)) {
      assert.ok(ownGap < gapToRoute(label, other.points),
        "label must be nearest its own route: " + text(label));
    }
    const { x, y } = label.props;
    const halfWidth = text(label).length * 4;
    assert.ok(x - halfWidth >= 0 && x + halfWidth <= svg.props.width &&
      y - 10 >= 0 && y + 10 <= svg.props.height, "label must fit inside the drawing");
  }
  return groups;
}

async function testWalkthrough() {
  const { figure, layout } = await renderDiagram(walkthrough);
  const groups = assertWalkthrough(figure, triples);
  const verbs = groups.map(group => elements(group, "text")[0]);
  const calls = verbs.find(verb => text(verb) === "calls");
  const rebuilds = verbs.find(verb => text(verb) === "rebuilds");
  // Alter only the painted arrows. Counts, accessible text and the verb set all stay correct.
  [calls.children, rebuilds.children] = [rebuilds.children, calls.children];
  assert.throws(() => assertWalkthrough(figure, triples), /visible relationship triples/);
  [calls.children, rebuilds.children] = [rebuilds.children, calls.children];
  const line = elements(groups[0], "polyline")[0];
  const original = line.props.points;
  line.props.points = original.split(" ").reverse().join(" ");
  assert.throws(() => assertWalkthrough(figure, triples), /visible relationship triples/);
  line.props.points = original;

  const [firstX, firstY] = [calls.props.x, calls.props.y];
  calls.props.x = rebuilds.props.x;
  calls.props.y = rebuilds.props.y;
  assert.throws(() => assertWalkthrough(figure, triples), /its own route/);
  calls.props.x = firstX;
  calls.props.y = firstY;
  assertWalkthrough(figure, triples);
  return layout;
}

async function main() {
  const ui = renderer();
  for (const source of [
    walkthrough + "\n  job --> store",
    pilot + "\n  marker -->|calls| docs",
    walkthrough + '\n  click job "https://example.invalid"',
    walkthrough + "\n  view -->|unterminated store",
    ...["", "  ", "calls|on", 'bad"verb', "<tag", "x>", "a\tb", "a\u0085b", "a\u202eb",
      "a\u2028b", "a\u2029b", "a".repeat(63) + "😀", "\u00a0" + "x".repeat(65)].map(verb =>
      walkthrough + "\n  view -->|" + verb + "| store"),
    pilot + "\n  security --- reassess",
    pilot + '\n  click docs "https://example.invalid"',
    pilot + "\n  %%{init: {}}%%",
    "flowchart TD\n  a --> b --> c",
    'flowchart LR\n  a["Unclosed] --> b',
    "flowchart TD\n" + Array.from({ length: 1024 }, (_, i) => "  a --> n" + i).join("\n"),
  ]) {
    const blocks = ui.markdown([fenced(source), fenced("OK", "example")].join("\n"));
    assert.equal(blocks.length, 2);
    assertSource(blocks[0], source);
    assertSource(blocks[1], "OK");
  }
  for (const source of [
    "flowchart LR\n" + " ".repeat(8200) + "a --> b",
    "flowchart TD\n" + Array.from({ length: 32 }, (_, i) => "  root --> n" + i).join("\n"),
    "flowchart TD\n" + Array(65).fill("  a --> b").join("\n"),
  ]) assertSource(ui.markdown(fenced(source))[0], source);
  assertSource(ui.markdown("```mermaid\n" + pilot)[0], pilot);
  const two = ui.markdown([fenced(pilot), fenced("flowchart TD\n  a --> b")].join("\n\n"));
  assert.ok(two.every(n => typeof n.type === "function") && two.length === 2);
  assert.notEqual(two[0].props.key, two[1].props.key);
  const ninth = ui.markdown(Array(9).fill(fenced(pilot)).join("\n\n"));
  assertSource(ninth[8], pilot);
  const layout = await renderPilot();
  const labeledLayout = await testWalkthrough();
  const longVerb = "a".repeat(62) + "😀";
  const padded = await renderDiagram("flowchart LR\n  a -->|\u00a0" + longVerb + "\u00a0| b");
  assertWalkthrough(padded.figure, [["a", longVerb, "b"]]);
  for (const verb of [longVerb, "uses agent's **cache** & [index](https://example.invalid)"]) {
    const { figure } = await renderDiagram("flowchart TD\n  a -->|  " + verb + "  | b");
    assertWalkthrough(figure, [["a", verb, "b"]]);
    assert.equal(elements(figure, "a").length, 0);
    assert.equal(elements(figure, "strong").length, 0);
  }

  // A completed old request must not publish into a replacement document.
  let finish;
  class DelayedELK { layout() { return new Promise(resolve => { finish = resolve; }); } }
  const delayed = renderer(DelayedELK);
  const [first] = delayed.markdown(fenced(pilot));
  delayed.paint(first);
  delayed.commit();
  delayed.unmount();
  finish(layout);
  await new Promise(resolve => setImmediate(resolve));
  assertSource(delayed.paint(first), pilot);

  class FailingELK { layout() { return Promise.reject(Error("layout unavailable")); } }
  // A rejected layout or a missing or ambiguous placement cannot publish a partial figure.
  async function assertLayoutFallback(source, Layout) {
    const failing = renderer(Layout);
    const [component] = failing.markdown(fenced(source));
    failing.paint(component);
    failing.commit();
    await new Promise(resolve => setImmediate(resolve));
    assertSource(failing.paint(component), source);
  }
  await assertLayoutFallback(pilot, FailingELK);
  await assertLayoutFallback(walkthrough, FailingELK);
  for (const damage of [
    graph => { graph.width = 0; },
    graph => { graph.height = Infinity; },
    graph => { graph.edges[0].sections = []; },
    graph => { graph.edges[0].sections[0].endPoint.x = -1; },
    graph => { graph.edges[0].labels = []; },
    graph => { graph.edges[0].labels.push({ ...graph.edges[0].labels[0] }); },
    graph => { delete graph.edges[0].labels[0].x; },
    graph => { graph.edges[0].labels[0].y = Infinity; },
    graph => { graph.edges[0].labels[0].x = graph.width - 1; },
    graph => { graph.edges[0].labels[0].text = "different relationship"; },
  ]) {
    const invalid = structuredClone(labeledLayout);
    damage(invalid);
    await assertLayoutFallback(walkthrough, class { async layout() { return invalid; } });
  }
}

const timeout = setTimeout(() => {
  console.error("Dashboard layout never completed");
  process.exit(1);
}, 5000);
main().catch(error => { console.error(error); process.exitCode = 1; }).finally(() => clearTimeout(timeout));
