const { createElement: h, useState, useEffect, useRef, useCallback, Component } = React;

// ── Dark mode — apply before first render to prevent flash ────────────────────
const _DARK_KEY = "wf-dashboard-theme";
function _storedTheme() {
  try {
    const v = localStorage.getItem(_DARK_KEY);
    if (v === "dark" || v === "light") return v;
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  } catch { return "light"; }
}
(function () { document.documentElement.setAttribute("data-theme", _storedTheme()); })();

// ── Error boundary ────────────────────────────────────────────────────────────
class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }
  static getDerivedStateFromError(error) {
    return { error };
  }
  render() {
    if (this.state.error) {
      const label = this.props.projectName || "Dashboard";
      return h("main", { className: "shell" },
        h("article", { className: "hero-card", style: { marginTop: "2rem" } },
          h("span", { className: "eyebrow" }, label),
          h("h1", { style: { fontFamily: "var(--font-heading)", margin: "1rem 0 0.5rem" } }, "Render error"),
          h("pre", { style: { color: "var(--danger)", fontSize: "0.85rem", whiteSpace: "pre-wrap", margin: 0 } },
            String(this.state.error),
          ),
        ),
      );
    }
    return this.props.children;
  }
}

// ── Polling backoff ───────────────────────────────────────────────────────────
// Steps in ms: 2 → 5 → 8 → 13 → 21 → 30, holds at 30 until an update resets to 2.
const POLL_STEPS = [2000, 5000, 8000, 13000, 21000, 30000];

function _snapshotHash(snapshot) {
  const { generated_at: _ts, ...rest } = snapshot;
  // Sort keys so insertion-order differences in the server response don't produce spurious hash changes.
  return JSON.stringify(rest, Object.keys(rest).sort());
}

// ── Utilities ─────────────────────────────────────────────────────────────────

function localDateTime(isoString) {
  if (!isoString) return "—";
  try {
    return new Date(isoString).toLocaleString(undefined, {
      month: "short", day: "numeric",
      hour: "2-digit", minute: "2-digit",
      timeZoneName: "short",
    });
  } catch { return String(isoString); }
}

function todayLocalDate() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

const p = (n, singular, plural) => n === 1 ? singular : plural;

function relativeAge(isoString) {
  if (!isoString) return null;
  try {
    const diffMs = Date.now() - new Date(isoString).getTime();
    const mins  = Math.floor(diffMs / 60000);
    const hours = Math.floor(diffMs / 3600000);
    const days  = Math.floor(diffMs / 86400000);
    if (mins  <  2) return "just now";
    if (hours <  1) return `${mins}m ago`;
    if (hours < 24) return `${hours}h ago`;
    if (days  <  7) return `${days}d ago`;
    return `${Math.floor(days / 7)}w ago`;
  } catch { return null; }
}

function dashboardTitle(snapshot) {
  const project = snapshot?.project || {};
  const repo = String(project.repo_basename || project.name || "").trim();
  return repo ? `${repo} - Wavefoundry` : "Wavefoundry";
}

// ── Status classification ──────────────────────────────────────────────────────

const DONE_STATUSES = new Set(["complete", "completed", "done", "implemented", "approved", "closed"]);
function isDone(status) { return DONE_STATUSES.has(String(status || "").toLowerCase()); }
function waveStatus(w) { return String(w.status || "").toLowerCase(); }
function activeWaves(waves)  { return waves.filter(w => waveStatus(w) === "active" || waveStatus(w) === "implementing"); }
function pendingWaves(waves) { return waves.filter(w => waveStatus(w) !== "active" && waveStatus(w) !== "implementing" && waveStatus(w) !== "closed" && waveStatus(w) !== "completed"); }
function dialogScope(waves) { return activeWaves(waves).length > 0 ? "active" : "pending"; }
function sortPendingFirst(items, isItemDone) {
  return [...items].sort((a, b) => Number(isItemDone(a)) - Number(isItemDone(b)));
}

function dialogChangesForScope(snapshot) {
  const waves = snapshot.waves || [];
  const inWaves = snapshot.changes?.in_waves || [];
  const scope = dialogScope(waves);
  if (scope === "active") {
    const activeWaveIds = new Set(activeWaves(waves).map(w => w.wave_id));
    return {
      scope,
      changes: sortPendingFirst(inWaves.filter(c => activeWaveIds.has(c.wave_id)), c => isDone(c.status)),
    };
  }
  const openOrClosedIds = new Set(
    waves.filter(w => waveStatus(w) === "active" || waveStatus(w) === "implementing" || waveStatus(w) === "closed" || waveStatus(w) === "completed").map(w => w.wave_id)
  );
  return {
    scope,
    changes: sortPendingFirst(
      [
        ...inWaves.filter(c => !openOrClosedIds.has(c.wave_id)),
        ...(snapshot.changes?.staged || []).filter(c => !openOrClosedIds.has(c.wave_id)),
      ],
      c => isDone(c.status),
    ),
  };
}

function badgeClass(status) {
  const key = String(status || "unknown").toLowerCase();
  if (["active", "implementing", "ready", "complete", "completed", "done", "implemented", "approved"].includes(key))
    return "status-badge status-ok";
  if (key === "planned") return "status-badge status-neutral";
  if (["paused", "important"].includes(key)) return "status-badge status-warn";
  if (["draft"].includes(key)) return "status-badge status-draft";
  if (["blocked", "error", "needs-revision"].includes(key)) return "status-badge status-blocked";
  return "status-badge status-unknown";
}

function computeState(snapshot) {
  const waves = snapshot.waves || [];
  const health = snapshot.health || {};
  const hasActive = activeWaves(waves).length > 0;
  const indexMissing = !health.index?.project?.present;
  const lintFailed = ["error", "fail"].includes(health.docs_lint?.status);
  if (lintFailed || indexMissing) return { label: "BLOCKED", cls: "state-blocked" };
  if (hasActive) return { label: "LIVE", cls: "state-live" };
  return { label: "IDLE", cls: "state-idle" };
}

function computeProgress(changes) {
  const total = (changes || []).length;
  if (!total) return { done: 0, total: 0, pct: 0 };
  const done = changes.filter(c => isDone(c.status)).length;
  return { done, total, pct: Math.round((done / total) * 100) };
}

function waveStats(waveChanges) {
  const tasksTotal = waveChanges.reduce((s, c) => s + (Number(c.tasks_total) || 0), 0);
  const tasksDone  = waveChanges.reduce((s, c) => s + (Number(c.tasks_completed) || 0), 0);
  const acTotals = {}, acDone = {};
  for (const c of waveChanges) {
    for (const [k, v] of Object.entries(c.ac_priority_counts || {})) {
      acTotals[k] = (acTotals[k] || 0) + v;
    }
    for (const [k, v] of Object.entries(c.ac_completed_counts || {})) {
      acDone[k] = (acDone[k] || 0) + v;
    }
  }
  return { tasksTotal, tasksDone, acTotals, acDone };
}

function visibleAcItems(change) {
  return (change.ac_items || []).filter(ac => ac.priority !== "not-this-scope");
}

function acProgressStats(changes) {
  let total = 0;
  let done = 0;
  for (const change of changes || []) {
    for (const ac of visibleAcItems(change)) {
      total += 1;
      if (ac.done) done += 1;
    }
  }
  return { total, done, pending: Math.max(0, total - done) };
}

function stripScopePrefix(scope) {
  const i = (scope || "").indexOf(" — ");
  return i === -1 ? (scope || "").trim() : scope.slice(i + 3).trim();
}

function summarizeAc(counts = {}, completed = {}) {
  const ordered = ["required", "important", "nice-to-have", "not-this-scope"];
  return ordered.filter(k => counts[k]).map(k => {
    const d = completed[k] || 0;
    const t = counts[k];
    return `${d}/${t} ${k}`;
  }).join(" · ") || "—";
}

const FRAMEWORK_FLOW = [
  {
    id: "plan",
    step: "01",
    title: "Plan Change",
    summary: "Set the shape of the change before any edits begin.",
    flow: ["Idea", "Scope", "Admitted change"],
    body: `This is where an idea becomes a real change. You clarify what is in scope, what is out of scope, and why the change matters before anyone starts editing files.

That early clarity matters because every later stage depends on it. If the scope is fuzzy, the wave gets harder to review, harder to implement, and easier to drift. When the plan is still unclear, the right move is to stay here and resolve the unknowns before the wave moves forward.`,
  },
  {
    id: "prepare",
    step: "02",
    title: "Prepare Wave",
    summary: "Check readiness before the wave starts.",
    flow: ["Review", "Open questions", "Prepare Wave"],
    body: `This is the readiness gate. The council reviews the change, works through the open questions, and decides whether the wave is actually safe to start.

This phase matters because it catches avoidable mistakes before code or docs start moving. It is not just a paperwork step; it is where the wave earns the right to begin. If the evidence is thin, the dependencies are unclear, or the change still feels too broad, the wave goes back to planning instead of pretending it is ready.

When Prepare is done well, the team has a shared picture of what will happen next, what is still uncertain, and what the operator needs to watch closely during implementation.`,
  },
  {
    id: "implement",
    step: "03",
    title: "Implement Wave",
    summary: "Carry out the admitted changes and verify them.",
    flow: ["Wave + change plans", "Implement each change", "Check tasks + ACs", "Write tests", "Prepare for review"],
    body: `This is the coding pass. Once Prepare says the wave is ready, the coding agent takes over and uses the wave record plus each admitted change plan as the working guide.

The first job is to read the wave and the change docs carefully enough to understand what belongs in scope. Then the work happens one change at a time: make the edits that match the plan, check the tasks and acceptance criteria, and keep the write set inside the admitted boundaries.

Implementation is not just about moving text around. The agent also writes or updates tests, runs them, and confirms that the result matches the agreed intent instead of drifting into a new shape of work. If the change no longer matches what Prepare approved, the right move is to stop and send it back for another pass instead of widening the scope on the fly.

When the code, tests, and documented intent line up, the wave is ready for review. The implementation phase is successful when it leaves behind a small, understandable set of edits that another reviewer can inspect without guessing how the change was made.`,
  },
  {
    id: "review",
    step: "04",
    title: "Review Wave",
    summary: "Compare the result against evidence and acceptance criteria.",
    flow: ["Review", "Evidence", "Findings"],
    body: `This is the evidence check. Reviewers compare what actually changed against what the wave promised, looking for missing behavior, drift, or anything that still needs correction.

Review matters because it is where the team decides whether the change is genuinely ready or whether more work is needed. This is the phase that keeps optimism from outrunning proof. Findings do not mean failure; they mean the wave should iterate back to Implement or even Prepare until the gaps are closed and the evidence lines up.

When the review is strong, it gives the operator confidence that the change is not just present, but actually matches the wave's intent and acceptance criteria.`,
  },
  {
    id: "close",
    step: "05",
    title: "Close & Maintain",
    summary: "Capture what shipped and hand it off.",
    flow: ["Signoff", "Archive"],
    body: `This is the handoff and memory stage. Once the wave is signed off, the team archives what shipped, records the important lessons, and makes sure a future session can understand what happened without reconstructing it from scratch.

This phase matters because the work is not done when the code stops changing. The framework still needs a durable record of what shipped, what decisions mattered, and what a future operator should know before they try to extend it. If the handoff or summary does not match the completed wave, the process loops one more time to refresh the record before closure.

That is what keeps the system useful over time: closure is not just an ending, it is the point where the wave becomes usable memory.`,
  },
];

function FrameworkProcessDiagram({ process }) {
  const steps = process.flow || [];
  if (!steps.length) return null;

  return h("div", { className: "framework-process-diagram" },
    h("div", { className: "framework-process-diagram-track", "aria-label": `${process.title} internal flow` },
      steps.map((step, index) => [
        h("span", {
          key: `${process.id}-step-${index}`,
          className: "framework-process-diagram-step",
        },
          h("span", { className: "framework-process-diagram-step-label" }, step),
        ),
        index < steps.length - 1
          ? h("span", { key: `${process.id}-arrow-${index}`, className: "framework-process-diagram-arrow", "aria-hidden": "true" }, "→")
          : null,
      ]).flat().filter(Boolean),
    ),
  );
}

function FrameworkProcessDialog({ process, onClose }) {
  const bodyContent = process.body && process.body.trim()
    ? renderMarkdownish(process.body)
    : h("p", { className: "muted" }, "No details available.");

  return h(DialogFrame, {
    title: [
      h("span", { key: "step", className: `process-step-number process-step-number--${process.id}` }, process.step),
      h("span", { key: "title" }, process.title),
    ],
    subtitle: process.summary,
    meta: [
      { value: process.track, cls: "dialog-meta-pill" },
    ],
    className: `framework-process-dialog framework-process-dialog--${process.id}`,
    onClose,
  },
    h(FrameworkProcessDiagram, { process }),
    bodyContent,
  );
}

function FrameworkFlow({ onSelectProcess }) {
  if (!FRAMEWORK_FLOW.length) return null;

  return h("div", { className: "framework-flow" },
    h("div", { className: "framework-flow-header" },
      h("h2", { className: "framework-flow-heading" }, "Wave lifecycle"),
      h("p", { className: "framework-flow-note muted" },
        "Click a stage to see how a change moves through a wave, from planning through review and close."
      ),
    ),
    h("div", { className: "framework-flow-diagram" },
      h("div", { className: "framework-flow-path", "aria-label": "Wave Framework process flow" },
        FRAMEWORK_FLOW.map((process, index) => [
          h("button", {
            key: process.id,
            type: "button",
            className: `framework-flow-card framework-flow-card--${process.id}`,
            onClick: () => onSelectProcess(process),
            "aria-label": `Open ${process.title}`,
            title: process.summary,
          },
            h("span", { className: "framework-flow-step" }, process.step),
            h("strong", { className: "framework-flow-card-title" }, process.title),
            h("span", { className: "framework-flow-card-copy" }, process.summary),
          ),
          index < FRAMEWORK_FLOW.length - 1
            ? h("span", { key: `${process.id}-arrow`, className: "framework-flow-arrow", "aria-hidden": "true" }, "→")
            : null,
        ]).flat().filter(Boolean),
      ),
    ),
  );
}

// ── Dark mode hook ────────────────────────────────────────────────────────────

function useDarkMode() {
  const [dark, setDark] = useState(() => _storedTheme() === "dark");
  const toggle = useCallback(() => {
    setDark(prev => {
      const next = !prev;
      const theme = next ? "dark" : "light";
      document.documentElement.setAttribute("data-theme", theme);
      try { localStorage.setItem(_DARK_KEY, theme); } catch {}
      return next;
    });
  }, []);
  return [dark, toggle];
}

// ── Components ────────────────────────────────────────────────────────────────

function SunIcon() {
  return h("svg", { viewBox: "0 0 24 24", width: 16, height: 16, fill: "none", stroke: "currentColor", strokeWidth: 2, strokeLinecap: "round", strokeLinejoin: "round", "aria-hidden": "true" },
    h("circle", { cx: 12, cy: 12, r: 5 }),
    h("line", { x1: 12, y1: 1,  x2: 12, y2: 3 }),
    h("line", { x1: 12, y1: 21, x2: 12, y2: 23 }),
    h("line", { x1: 4.22,  y1: 4.22,  x2: 5.64,  y2: 5.64 }),
    h("line", { x1: 18.36, y1: 18.36, x2: 19.78, y2: 19.78 }),
    h("line", { x1: 1,  y1: 12, x2: 3,  y2: 12 }),
    h("line", { x1: 21, y1: 12, x2: 23, y2: 12 }),
    h("line", { x1: 4.22,  y1: 19.78, x2: 5.64,  y2: 18.36 }),
    h("line", { x1: 18.36, y1: 5.64,  x2: 19.78, y2: 4.22 }),
  );
}

function MoonIcon() {
  return h("svg", { viewBox: "0 0 24 24", width: 16, height: 16, fill: "none", stroke: "currentColor", strokeWidth: 2, strokeLinecap: "round", strokeLinejoin: "round", "aria-hidden": "true" },
    h("path", { d: "M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" }),
  );
}

function ThemeToggle({ dark, onToggle }) {
  return h("button", {
    className: "theme-toggle",
    onClick: onToggle,
    "aria-label": dark ? "Switch to light mode" : "Switch to dark mode",
    title: dark ? "Switch to light mode" : "Switch to dark mode",
  }, dark ? h(SunIcon) : h(MoonIcon));
}

function GitPills({ git }) {
  if (!git?.branch) return null;
  const pills = [
    h("span", { key: "branch", className: "meta-pill git-branch-pill", title: `Branch: ${git.branch}` },
      h("span", { className: "git-branch-icon", "aria-hidden": "true" }, "⎇"),
      " ",
      git.branch,
    ),
  ];
  if (git.commit_hash) {
    const label = git.commit_date ? `${git.commit_hash} · ${git.commit_date}` : git.commit_hash;
    pills.push(h("span", { key: "commit", className: "meta-pill git-commit-pill", title: git.commit_message || "" }, label));
  }
  if (git.ahead > 0)  pills.push(h("span", { key: "ahead",  className: "meta-pill git-ahead-pill",  title: "Commits ahead of upstream"  }, `↑${git.ahead} ahead`));
  if (git.behind > 0) pills.push(h("span", { key: "behind", className: "meta-pill git-behind-pill", title: "Commits behind upstream" }, `↓${git.behind} behind`));
  return h(React.Fragment, null, ...pills);
}

function StateBadge({ snapshot }) {
  const state = computeState(snapshot);
  return h("div", {
    className: `state-badge ${state.cls}`,
    role: "status",
    "aria-label": `Project state: ${state.label}`,
  },
    h("span", { className: "state-dot", "aria-hidden": "true" }),
    state.label,
  );
}

function Header({ snapshot, dark, onToggleDark }) {
  const project = snapshot.project || {};
  return h("header", { className: "site-header" },
    h("div", { className: "header-brand" },
      h("div", { className: "header-logo", "aria-hidden": "true" },
        h("div", { className: "header-logo-mark" }),
      ),
      h("span", { className: "header-repo" }, project.name || project.repo_basename || "Repository"),
    ),
    h("div", { className: "header-actions" },
      h(ThemeToggle, { dark, onToggle: onToggleDark }),
    ),
  );
}

function ProgressRow({ label, done, total, variant }) {
  const safeTotal = Number(total) || 0;
  const safeDone = Number(done) || 0;
  const pct = safeTotal > 0 ? Math.round((safeDone / safeTotal) * 100) : 0;
  const complete = safeTotal > 0 && safeDone >= safeTotal;
  const cls = ["progress-row", variant && `progress-row--${variant}`, complete && "progress-row--complete"]
    .filter(Boolean).join(" ");
  return h("div", { className: cls },
    h("div", { className: "progress-row-label" }, label),
    h("div", { className: "progress-row-bar-wrap" },
      h("div", {
        className: "progress-bar-track",
        role: "progressbar",
        "aria-valuenow": pct,
        "aria-valuemin": 0,
        "aria-valuemax": 100,
        "aria-label": safeTotal > 0 ? `${label}: ${pct}%` : `${label}: 0 of 0`,
      },
        h("div", { className: "progress-bar-fill", style: { width: `${pct}%` } }),
      ),
    ),
    h("div", { className: "progress-row-fraction" }, `${safeDone}/${safeTotal}`),
  );
}

function ProgressCard({ snapshot, scopeChanges }) {
  const waves      = snapshot.waves || [];
  const allInWaves = snapshot.changes?.in_waves || [];
  const progressChanges = scopeChanges || allInWaves;

  const closedWaves = waves.filter(w => waveStatus(w) === "closed" || waveStatus(w) === "completed").length;
  const totalWaves  = waves.length;
  const closedWaveIds = new Set(waves.filter(w => waveStatus(w) === "closed" || waveStatus(w) === "completed").map(w => w.wave_id));

  // CHANGES: use wave.change_count for admitted in-wave changes from closed waves (handles
  // waves whose change doc files no longer exist on disk). progressChanges contains only
  // open-wave docs (pendingChanges already excludes staged docs referencing closed waves),
  // so openProgressChanges === progressChanges in practice; the filter is a safety guard.
  const closedChangesDone   = waves.filter(w => closedWaveIds.has(w.wave_id)).reduce((s, w) => s + (Number(w.change_count) || 0), 0);
  const openProgressChanges = progressChanges.filter(c => !closedWaveIds.has(c.wave_id));
  const changesDone  = closedChangesDone + openProgressChanges.filter(c => isDone(c.status)).length;
  const changesTotal = closedChangesDone + openProgressChanges.length;

  // TASKS & ACS: combine open-scope changes with closed-wave in-wave change docs so all
  // historical work is included regardless of scope.
  const closedInWaves = allInWaves.filter(c => closedWaveIds.has(c.wave_id));
  const allCountedChanges = [...openProgressChanges, ...closedInWaves];

  const tasksTotal = allCountedChanges.reduce((s, c) => s + (Number(c.tasks_total) || 0), 0);
  const tasksDone  = allCountedChanges.reduce((s, c) =>
    s + (closedWaveIds.has(c.wave_id) ? (Number(c.tasks_total) || 0) : (Number(c.tasks_completed) || 0)), 0);

  const acTotal = allCountedChanges.reduce((s, c) => s + visibleAcItems(c).length, 0);
  const acDone  = allCountedChanges.reduce((s, c) => {
    const items = visibleAcItems(c);
    return s + (closedWaveIds.has(c.wave_id) ? items.length : items.filter(a => a.done).length);
  }, 0);

  return h("article", { className: "progress-card" },
    h("div", { className: "progress-header" },
      h("h2", null, "Progress"),
    ),
    h("div", { className: "progress-rows" },
      h(ProgressRow, { label: "Waves",   done: closedWaves, total: totalWaves,   variant: "waves" }),
      h(ProgressRow, { label: "Changes", done: changesDone, total: changesTotal, variant: "changes" }),
      h(ProgressRow, { label: "ACs",   done: acDone,    total: acTotal,    variant: "acs" }),
      h(ProgressRow, { label: "Tasks", done: tasksDone, total: tasksTotal, variant: "tasks" }),
    ),
  );
}

function MiniGraph({ done, total, label, variant }) {
  if (!total) return null;
  const remaining = total - done;
  const donePct = (done / total) * 100;
  const remPct  = (remaining / total) * 100;
  const doneCls = variant ? `mini-graph-done mini-graph-done--${variant}` : "mini-graph-done";
  return h("div", { className: "mini-graph", role: "img", "aria-label": `${label}: ${done} of ${total} complete` },
    done > 0     ? h("div", { className: doneCls, style: { width: `${donePct}%` }, title: `${done} complete` }) : null,
    remaining > 0 ? h("div", { className: "mini-graph-rem",  style: { width: `${remPct}%` },  title: `${remaining} remaining` }) : null,
  );
}

function WaveTasks({ tasksTotal, tasksDone }) {
  if (!tasksTotal) return null;
  return h("div", { className: "wip-section wip-section--tasks" },
    h("div", { className: "wip-section-label" },
      "Tasks",
      h("span", { className: "wip-fraction" }, `${tasksDone} / ${tasksTotal} complete`),
    ),
    h(MiniGraph, { done: tasksDone, total: tasksTotal, label: "Tasks", variant: "tasks" }),
  );
}

function WaveAcs({ acTotals, acDone = {}, acStats = { total: 0, done: 0 } }) {
  const ordered = ["required", "important", "nice-to-have", "not-this-scope"];
  const entries = ordered.filter(k => acTotals[k]);
  const priorityTotal = entries.reduce((s, k) => s + acTotals[k], 0);
  const priorityDone  = entries.reduce((s, k) => s + (acDone[k] || 0), 0);
  const hasVisibleStats = acStats.total > 0 || acStats.done > 0;
  const total = hasVisibleStats ? acStats.total : priorityTotal;
  const done  = hasVisibleStats ? acStats.done : priorityDone;
  if (!entries.length && total === 0) return null;
  return h("div", { className: "wip-section wip-section--acs" },
    h("div", { className: "wip-section-label" },
      "Acceptance criteria",
      h("span", { className: "wip-fraction" }, `${done} / ${total} complete`),
    ),
    h(MiniGraph, { done, total, label: "Acceptance criteria", variant: "acs" }),
    h("div", { className: "ac-chips" },
      entries.map(k => {
        const d = acDone[k] || 0;
        const t = acTotals[k];
        return h("span", { key: k, className: "ac-chip" }, `${d}/${t} ${k}`);
      }),
    ),
  );
}

function WaveEvidence({ evidence }) {
  if (!evidence?.length) return null;
  return h("div", { className: "wip-section" },
    h("div", { className: "wip-section-label" }, "Review evidence"),
    h("ul", { className: "lanes-list" },
      evidence.map((item, i) =>
        h("li", { key: i, className: "lanes-item lanes-item--stacked" },
          h("span", { className: "lanes-role" }, item.key),
          h("span", { className: "lanes-scope muted" }, stripScopePrefix(item.value || "recorded")),
        )
      ),
    ),
  );
}

function WaveLanes({ participants }) {
  if (!participants?.length) return null;
  return h("div", { className: "wip-section" },
    h("div", { className: "wip-section-label" }, "Reviewers"),
    h("ul", { className: "lanes-list" },
      participants.map((pt, i) =>
        h("li", { key: i, className: "lanes-item lanes-item--stacked" },
          h("span", { className: "lanes-role" }, pt.role),
          pt.scope ? h("span", { className: "lanes-scope muted" }, stripScopePrefix(pt.scope)) : null,
        )
      ),
    ),
  );
}

function WaveChangeList({ changes, waveId, onChangeClick }) {
  if (!changes?.length) return null;
  return h("div", { className: "wip-section" },
    h("div", { className: "wip-section-label" }, "Changes"),
    h("ul", { className: "lanes-list" },
      changes.map((c, i) =>
        h("li", { key: i, className: "wave-change-item" },
          h("div", { className: "wave-change-header" },
            onChangeClick
              ? h("button", {
                  className: "wave-change-id id-link",
                  onClick: () => onChangeClick({ change_id: c.id, wave_id: waveId, title: c.title }),
                  title: "View change document",
                }, c.id)
              : h("span", { className: "wave-change-id" }, c.id),
            h("span", { className: "wave-change-title" }, c.title),
          ),
          c.description ? h("div", { className: "wave-change-desc muted" }, ...renderMarkdownish(c.description)) : null,
        )
      ),
    ),
  );
}

function OpenWaveCard({ wave, allChanges, handoffWaveId, onWaveClick, onChangeClick }) {
  const waveChanges = allChanges.filter(c => c.wave_id === wave.wave_id);
  const { tasksTotal, tasksDone, acTotals, acDone } = waveStats(waveChanges);
  const acStats = acProgressStats(waveChanges);
  const isHandoff = handoffWaveId && wave.wave_id === handoffWaveId;
  return h("div", { className: "open-wave-card" },
    h("div", { className: "status-row" },
      h("div", null,
        h("button", {
          className: "open-wave-id id-link",
          onClick: onWaveClick ? () => onWaveClick(wave) : undefined,
          title: "View wave document",
        }, wave.wave_id),
        h("div", { className: "open-wave-title" }, wave.title),
      ),
      h("div", { className: "open-wave-meta" },
        isHandoff ? h("span", { className: "handoff-pill", title: "Current session handoff" }, "↩ handoff") : null,
        h("span", { className: "muted open-wave-count" }, `${wave.change_count} ${p(wave.change_count, "change", "changes")}`),
      ),
    ),
    h(WaveChangeList, { changes: wave.changes, waveId: wave.wave_id, onChangeClick }),
    h(WaveAcs, { acTotals, acDone, acStats }),
    h(WaveTasks, { tasksTotal, tasksDone }),
    h(WaveEvidence, { evidence: wave.review_evidence }),
    h(WaveLanes, { participants: wave.participants }),
  );
}

function PendingWaveRow({ wave, onWaveClick }) {
  return h("div", { className: "pending-wave-row" },
    h("div", { className: "pending-wave-left" },
      h("button", {
        className: "open-wave-id id-link",
        onClick: onWaveClick ? () => onWaveClick(wave) : undefined,
        title: "View wave document",
      }, wave.wave_id),
      wave.title ? h("span", { className: "pending-wave-title" }, wave.title) : null,
    ),
    h("div", { className: "open-wave-meta" },
      h("span", { className: badgeClass(wave.status) }, wave.status),
      h("span", { className: "muted open-wave-count" }, `${wave.change_count} ${p(wave.change_count, "change", "changes")}`),
    ),
  );
}

function WavesCard({ waves, allChanges, handoffWaveId, onWaveClick, onChangeClick }) {
  const active  = activeWaves(waves);
  const pending = pendingWaves(waves).slice().sort((a, b) => String(b.wave_id).localeCompare(String(a.wave_id)));
  const closed  = waves.filter(w => waveStatus(w) === "closed").length;

  return h("article", { className: "table-card", "aria-label": "Waves" },
    h("h2", null, "Waves"),
    active.length
      ? active.map(wave => h(OpenWaveCard, { key: wave.wave_id, wave, allChanges, handoffWaveId, onWaveClick, onChangeClick }))
      : h("div", { className: "empty-state" }, "No active waves."),
    pending.length ? h(React.Fragment, null,
      h("div", { className: "waves-section-label" }, `${pending.length} pending`),
      pending.map(wave => h(PendingWaveRow, { key: wave.wave_id, wave, onWaveClick })),
    ) : null,
    closed ? h("p", { className: "muted", style: { marginTop: "var(--space-3)" } },
      `${closed} closed ${p(closed, "wave", "waves")}.`
    ) : null,
  );
}

function Metrics({ snapshot, scopeChanges, onWavesClick, onChangesClick, onAcsClick, onTasksClick, onFilesClick, onIndexClick }) {
  const waves = snapshot.waves || [];
  const git = snapshot.git || {};
  const health = snapshot.health || {};
  // active = on active wave(s); pending = on non-active waves + staged plans not yet in a wave

  const waveActive  = activeWaves(waves).length;
  const wavePending = pendingWaves(waves).length;
  const waveTotal   = waves.length;
  const waveMode = waveActive > 0 ? "active" : "pending";
  const waveMetricCount = waveMode === "active" ? waveActive : wavePending;
  const waveMetricLabel = waveMode === "active"
    ? p(waveActive, "Active wave", "Active waves")
    : p(wavePending, "Pending wave", "Pending waves");
  const scopeMetricLabel = waveMode === "active" ? "Active" : "Pending";
  const changeMetrics = {
    total: (scopeChanges || []).length,
    pending: (scopeChanges || []).reduce((s, c) => s + (isDone(c.status) ? 0 : 1), 0),
  };
  const acMetrics = acProgressStats(scopeChanges);
  const taskMetrics = {
    total: (scopeChanges || []).reduce((s, c) => s + (Number(c.tasks_total) || 0), 0),
    pending: (scopeChanges || []).reduce((s, c) => s + Math.max(0, (Number(c.tasks_total) || 0) - (Number(c.tasks_completed) || 0)), 0),
  };
  const currentWaveMetrics = snapshot.metrics || {};
  const waveMetrics = currentWaveMetrics.waves || {
    active: waveActive,
    pending: wavePending,
    total: waveTotal,
  };
  const gitFileCount = Number(git.files_changed) || 0;
  const gitLinesAdded = Number(git.lines_added) || 0;
  const gitLinesRemoved = Number(git.lines_removed) || 0;
  const fileNote = gitLinesAdded || gitLinesRemoved
    ? h("span", { className: "metric-diff-note", title: "Lines added / removed" },
        gitLinesAdded ? h("span", { className: "metric-diff-added" }, `+${gitLinesAdded.toLocaleString()}`) : null,
        gitLinesAdded && gitLinesRemoved ? h("span", { className: "metric-diff-sep" }, " ") : null,
        gitLinesRemoved ? h("span", { className: "metric-diff-removed" }, `−${gitLinesRemoved.toLocaleString()}`) : null,
      )
    : gitFileCount
      ? "working tree"
      : "clean working tree";

  const metrics = [
    { label: waveMetricLabel, value: waveMetricCount, note: `${waveMetrics.pending} pending · ${waveMetrics.total} total`, onClick: onWavesClick, variant: "waves" },
    { label: p(changeMetrics.pending, `${scopeMetricLabel} change`, `${scopeMetricLabel} changes`), value: changeMetrics.pending, note: `pending, ${changeMetrics.total} total`, onClick: onChangesClick, variant: "changes" },
    { label: p(acMetrics.pending,    `${scopeMetricLabel} AC`,     `${scopeMetricLabel} ACs`),     value: acMetrics.pending,     note: `pending, ${acMetrics.total} total`, onClick: onAcsClick,     variant: "acs" },
    { label: p(taskMetrics.pending, `${scopeMetricLabel} task`, `${scopeMetricLabel} tasks`),   value: taskMetrics.pending, note: `pending, ${taskMetrics.total} total`, onClick: onTasksClick,   variant: "tasks" },
    { label: p(gitFileCount, "File changed", "Files changed"), value: gitFileCount, note: fileNote, onClick: onFilesClick, variant: "files" },
    (() => {
      const projectIdx = health.index?.project || {};
      const projectGraph = health.graph?.project || {};
      const totalChunks = (Number(projectIdx.doc_chunks) || 0) + (Number(projectIdx.code_chunks) || 0);
      const totalFiles = Number(projectIdx.files_indexed) || 0;
      const graphNodes = Number(projectGraph.counts?.nodes) || 0;
      const graphEdges = Number(projectGraph.counts?.edges) || 0;
      const buildStatus = projectIdx.build_status === "running"
        ? "running"
        : projectIdx.build_status === "failed"
          ? "failed"
          : null;
      const noSemanticIndex = !projectIdx.present;
      const state = buildStatus === "running" ? "running" : buildStatus === "failed" ? "failed" : null;
      const statusText = buildStatus === "running"
        ? "Indexing..."
        : buildStatus === "failed"
          ? "Index build failed"
          : null;
      const note = h(React.Fragment, null,
        h("div", { className: "metric-subnote" }, `files, ${totalChunks.toLocaleString()} chunks`),
        h("div", { className: "metric-subnote" }, `${graphNodes.toLocaleString()} nodes · ${graphEdges.toLocaleString()} edges`),
        h("div", { className: "metric-status-line" }, statusText || "\u00A0"),
      );
      const value = totalFiles ? totalFiles.toLocaleString() : (buildStatus === "running" ? "Indexing…" : "Missing");
      return { label: "Index", value, note, state, onClick: onIndexClick, variant: "index" };
    })(),
  ];

  return h("section", { className: "metrics", "aria-label": "Project metrics" },
    metrics.map(({ label, value, note, state, onClick, variant }) => {
      const isClickable = !!onClick;
      const variantClass = variant ? ` metric--${variant}` : "";
      return h("article", {
        key: label,
        className: (state ? `metric metric--${state}` : "metric") + variantClass + (isClickable ? " metric--clickable" : ""),
        onClick,
        role: isClickable ? "button" : undefined,
        tabIndex: isClickable ? 0 : undefined,
        onKeyDown: isClickable ? (e => { if (e.key === "Enter" || e.key === " ") onClick(); }) : undefined,
      },
        h("div", { className: "metric-label" }, label),
        h("div", { className: "metric-value" }, String(value)),
        h("div", { className: "metric-note" }, note),
      );
    }),
  );
}

function buildFileTree(entries) {
  const root = {};
  for (const entry of entries) {
    const { path, status = "modified", lines_added = null, lines_deleted = null } =
      typeof entry === "string" ? { path: entry } : entry;
    const parts = path.split("/");
    let node = root;
    for (let i = 0; i < parts.length - 1; i++) {
      if (!Array.isArray(node[parts[i]]) && (typeof node[parts[i]] !== "object" || node[parts[i]] === null))
        node[parts[i]] = {};
      node = node[parts[i]];
    }
    node[parts[parts.length - 1]] = [status, lines_added, lines_deleted];
  }
  return root;
}

function FileTree({ node, depth = 0, onFileClick = null, pathPrefix = "" }) {
  const entries = Object.entries(node).sort(([ak, av], [bk, bv]) => {
    const aDir = !Array.isArray(av) && typeof av === "object" && av !== null;
    const bDir = !Array.isArray(bv) && typeof bv === "object" && bv !== null;
    if (aDir !== bDir) return bDir ? 1 : -1;
    return ak.localeCompare(bk);
  });
  return h("ul", { className: "file-tree", style: depth === 0 ? {} : { paddingLeft: "1.1em" } },
    entries.map(([name, child]) => {
      const isDir = !Array.isArray(child) && typeof child === "object" && child !== null;
      const fullPath = pathPrefix ? `${pathPrefix}/${name}` : name;
      if (isDir) {
        return h("li", { key: name, className: "file-tree-dir" },
          h("span", { className: "file-tree-dir-name" }, name + "/"),
          h(FileTree, { node: child, depth: depth + 1, onFileClick, pathPrefix: fullPath }),
        );
      }
      const [status, linesAdded, linesDeleted] = Array.isArray(child) ? child : [child, null, null];
      const isNew = status === "added";
      const lineCountEl = (linesAdded || linesDeleted)
        ? h("span", { className: "file-tree-lines" },
            linesAdded ? h("span", { className: "file-tree-lines-added" }, `+${linesAdded}`) : null,
            (!isNew && linesDeleted) ? h("span", { className: "file-tree-lines-deleted" }, `-${linesDeleted}`) : null,
          )
        : null;
      const leafProps = {
        key: name,
        className: `file-tree-file file-tree-file--${status}`,
        ...(onFileClick ? { "data-clickable": "1", onClick: () => onFileClick(fullPath) } : {}),
      };
      return h("li", leafProps, h("span", null, name), lineCountEl);
    }),
  );
}

function DiffDialog({ filePath, onClose }) {
  const [diffText, setDiffText] = useState(null);
  useEffect(() => {
    fetch(`/api/diff?path=${encodeURIComponent(filePath)}`)
      .then(r => r.text())
      .then(text => setDiffText(text))
      .catch(() => setDiffText(""));
  }, [filePath]);

  const renderDiff = (text) => {
    if (text === null) return h("div", { className: "empty-state" }, "Loading…");
    const trimmed = text.trim();
    if (!trimmed) return h("div", { className: "empty-state" }, "No changes.");
    const lines = text.split("\n").filter(line =>
      !line.startsWith("diff ") && !line.startsWith("index ") &&
      !line.startsWith("--- ") && !line.startsWith("+++ ")
    );
    return h("div", { className: "diff-view" },
      h("div", { className: "diff-view-lines" },
        lines.map((line, i) => {
          let cls = "diff-line diff-line--context";
          if (line.startsWith("@@")) cls = "diff-line diff-line--hunk";
          else if (line.startsWith("+")) cls = "diff-line diff-line--added";
          else if (line.startsWith("-")) cls = "diff-line diff-line--removed";
          return h("span", { key: i, className: cls }, line || " ");
        }),
      ),
    );
  };

  const fileName = filePath.split("/").pop();
  return h(DialogFrame, {
    className: "diff-dialog",
    title: fileName,
    subtitle: filePath,
    onClose,
  }, renderDiff(diffText));
}

function DialogFrame({ className, title, subtitle, meta, onClose, children }) {
  const dialogRef = useRef(null);
  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    dialog.showModal();
    const onCancel = (e) => { e.preventDefault(); onClose(); };
    dialog.addEventListener("cancel", onCancel);
    return () => dialog.removeEventListener("cancel", onCancel);
  }, [onClose]);
  const handleBackdropClick = (e) => { if (e.target === dialogRef.current) onClose(); };
  return h("dialog", { ref: dialogRef, className: `agent-dialog ${className || ""}`, onClick: handleBackdropClick },
    h("div", { className: "agent-dialog-header" },
      h("div", null,
        h("h2", { className: "agent-dialog-title" }, title),
        subtitle ? h("span", { className: "agent-dialog-subtitle muted" }, subtitle) : null,
        meta?.length ? h("div", { className: "dialog-meta-row" },
          meta.map((item, i) =>
            h("span", { key: i, className: item.cls || "dialog-meta-pill" }, item.value)
          ),
        ) : null,
      ),
      h("button", { className: "agent-dialog-close", "aria-label": "Close", onClick: onClose }, "×"),
    ),
    h("div", { className: "agent-dialog-body" }, children),
  );
}

function WavesDialog({ snapshot, onClose }) {
  const waves = snapshot.waves || [];
  const active = activeWaves(waves);
  const pending = pendingWaves(waves).slice().sort((a, b) => String(b.wave_id).localeCompare(String(a.wave_id)));
  const displayWaves = active.length ? active : pending;
  const title = active.length ? "Active Waves" : "Pending Waves";
  return h(DialogFrame, { title, onClose },
    displayWaves.length ? displayWaves.map(wave =>
      h("div", { key: wave.wave_id, className: "metric-dialog-card" },
        h("div", { className: "metric-dialog-card-header" },
          h("span", { className: "open-wave-id" }, wave.wave_id),
          h("span", { className: badgeClass(wave.status) }, wave.status),
        ),
        h("div", { className: "metric-dialog-card-title" }, wave.title),
        wave.objective ? h("div", { className: "metric-dialog-card-desc" }, wave.objective) : null,
      )
    ) : h("div", { className: "empty-state" }, "No pending waves."),
  );
}

function ChangesDialog({ snapshot, onClose }) {
  const { scope, changes } = dialogChangesForScope(snapshot);
  const title = scope === "active"
    ? p(changes.length, "Active Change", "Active Changes")
    : p(changes.length, "Pending Change", "Pending Changes");
  return h(DialogFrame, { title, onClose },
    changes.length ? changes.map(c =>
      h("div", { key: c.change_id, className: "metric-dialog-card" },
        h("div", { className: "metric-dialog-card-header" },
          h("span", { className: "wave-change-id" }, c.change_id),
          c.status ? h("span", { className: badgeClass(c.status) }, c.status) : null,
        ),
        h("div", { className: "metric-dialog-card-title" }, c.title),
        c.description ? h("div", { className: "metric-dialog-card-desc" }, c.description) : null,
      )
    ) : h("div", { className: "empty-state" }, scope === "active" ? "No active changes." : "No pending changes."),
  );
}

function AcsDialog({ snapshot, onClose }) {
  const { scope, changes } = dialogChangesForScope(snapshot);
  const waves = snapshot.waves || [];
  const waveMap = Object.fromEntries(waves.map(w => [w.wave_id, w]));
  const PRIORITY_BADGE = { required: "status-blocked", important: "status-warn", "nice-to-have": "status-neutral", unknown: "status-unknown" };
  return h(DialogFrame, { title: scope === "active" ? "Active ACs" : "Pending ACs", onClose },
    changes.length ? changes.map(c => {
      const items = sortPendingFirst(visibleAcItems(c), ac => Boolean(ac.done));
      if (!items.length) return null;
      const wave = c.wave_id ? waveMap[c.wave_id] : null;
      const evidence = wave?.review_evidence || [];
      return h("div", { key: c.change_id, className: "metric-dialog-card" },
        h("div", { className: "metric-dialog-card-header" },
          h("span", { className: "wave-change-id" }, c.change_id),
          evidence.length
            ? h("span", { className: "metric-dialog-review-badge status-badge status-done", title: evidence.map(e => `${e.key}: ${e.value}`).join("\n") }, "reviewed")
            : h("span", { className: "metric-dialog-review-badge status-badge status-neutral" }, "not reviewed"),
        ),
        h("div", { className: "metric-dialog-card-title" }, c.title),
        h("div", { className: "metric-dialog-ac-rows" },
          items.map((ac, i) =>
            h("div", { key: i, className: `metric-dialog-ac-item${ac.done ? " metric-dialog-ac-item--done" : ""}` },
              h("span", { className: `metric-dialog-ac-check${ac.done ? " metric-dialog-ac-check--done" : ""}` }, ac.done ? "✓" : "○"),
              h("span", { className: "metric-dialog-ac-text" }, renderInline(ac.text || "")),
              ac.priority && ac.priority !== "unknown"
                ? h("span", { className: `status-badge ${PRIORITY_BADGE[ac.priority] || "status-unknown"} metric-dialog-ac-priority` }, ac.priority)
                : null,
            )
          ),
        ),
      );
    }).filter(Boolean) : h("div", { className: "empty-state" }, scope === "active" ? "No active ACs." : "No pending ACs."),
  );
}

function TasksDialog({ snapshot, onClose }) {
  const { scope, changes } = dialogChangesForScope(snapshot);
  const cards = changes.map(c => {
    const items = sortPendingFirst(c.tasks_items || [], task => Boolean(task.done));
    if (!items.length) return null;
    return h("div", { key: c.change_id, className: "metric-dialog-card" },
      h("div", { className: "metric-dialog-card-header" },
        h("span", { className: "wave-change-id" }, c.change_id),
      ),
      h("div", { className: "metric-dialog-card-title" }, c.title),
      h("div", { className: "metric-dialog-ac-rows" },
        items.map((task, i) =>
          h("div", { key: i, className: `metric-dialog-ac-item${task.done ? " metric-dialog-ac-item--done" : ""}` },
            h("span", { className: `metric-dialog-ac-check${task.done ? " metric-dialog-ac-check--done" : ""}` }, task.done ? "✓" : "○"),
            h("span", { className: "metric-dialog-ac-text" }, renderInline(task.label || "")),
          )
        ),
      ),
    );
  }).filter(Boolean);
  return h(DialogFrame, { title: scope === "active" ? "Active Tasks" : "Pending Tasks", onClose },
    cards.length ? cards : h("div", { className: "empty-state" }, scope === "active" ? "No active tasks." : "No pending tasks."),
  );
}

function FilesDialog({ title, files, emptyMessage, onClose }) {
  const dialogRef = useRef(null);
  const [diffFile, setDiffFile] = useState(null);
  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    dialog.showModal();
    const onCancel = () => onClose();
    dialog.addEventListener("cancel", onCancel);
    return () => dialog.removeEventListener("cancel", onCancel);
  }, [onClose]);
  const handleBackdropClick = (e) => { if (e.target === dialogRef.current) onClose(); };
  const tree = buildFileTree(files);

  return h(
    React.Fragment,
    null,
    h("dialog", { ref: dialogRef, className: "agent-dialog files-dialog", onClick: handleBackdropClick },
      h("div", { className: "agent-dialog-header" },
        h("div", { className: "files-dialog-header-text" },
          h("h2", { className: "agent-dialog-title" }, title),
          h("span", { className: "files-dialog-subtitle" }, `${files.length} ${files.length === 1 ? "file" : "files"}`),
        ),
        h("button", { className: "agent-dialog-close", "aria-label": "Close", onClick: onClose }, "×"),
      ),
      h("div", { className: "agent-dialog-body" },
        files.length
          ? h(FileTree, { node: tree, onFileClick: setDiffFile })
          : h("div", { className: "empty-state" }, emptyMessage || "No files."),
      ),
    ),
    diffFile ? h(DiffDialog, { filePath: diffFile, onClose: () => setDiffFile(null) }) : null,
  );
}

const GRAPH_KIND_COLORS = {
  module: "#1976d2",
  class: "#6f42c1",
  function: "#53ac04",
  doc: "#495057",
  seed: "#c25800",
  community: "#0f766e",
  external: "#7a7f87",
};

const GRAPH_RELATION_COLORS = {
  defines: "#1976d2",
  imports: "#6f42c1",
  calls: "#53ac04",
  doc_references_code: "#ff9100",
};

const DEFAULT_GRAPH_RELATIONS = ["defines", "calls"];
const GRAPH_MIN_COMMUNITY_NODES = 2;
const GRAPH_OVERVIEW_COMMUNITY_LIMIT = 24;
const GRAPH_COMMUNITY_QUICK_PICK_LIMIT = 6;
const GRAPH_COMMUNITY_DRILLDOWN_LIMIT = 50;
const GRAPH_OVERVIEW_SEED_LIMIT = 24;

function _hexToRgba(hex, alpha) {
  const value = String(hex || "").trim().replace(/^#/, "");
  if (value.length !== 6) return `rgba(0, 0, 0, ${alpha})`;
  const r = parseInt(value.slice(0, 2), 16);
  const g = parseInt(value.slice(2, 4), 16);
  const b = parseInt(value.slice(4, 6), 16);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

function _hashString(value) {
  let h = 0;
  for (let i = 0; i < value.length; i += 1) {
    h = Math.imul(31, h) + value.charCodeAt(i);
    h |= 0;
  }
  return Math.abs(h);
}

function _graphKindBucket(kind) {
  return GRAPH_KIND_COLORS[kind] ? kind : "external";
}

function _graphLabel(node) {
  return String(node?.label || node?.id || "").trim();
}

function _graphNodeRadius(node, degree) {
  const kind = _graphKindBucket(node?.kind);
  const base = kind === "community"
    ? 18
    : kind === "module"
      ? 14
    : kind === "class"
      ? 13
      : kind === "function"
        ? 12
        : 10;
  const clusterBoost = kind === "community"
    ? Math.min(10, Math.max(0, Math.sqrt(Number(node?.node_count || node?.total_node_count || degree || 0))))
    : Math.min(4, Math.max(0, degree / 4));
  return Math.min(kind === "community" ? 28 : 21, base + clusterBoost);
}

function _graphSeedPosition(node, index, total, width, height) {
  const key = `${node.id || index}`;
  const angle = ((_hashString(key) % 360) / 180) * Math.PI;
  const ring = total > 1 ? Math.min(width, height) * (0.16 + ((index % 5) * 0.08)) : Math.min(width, height) * 0.18;
  return {
    x: width / 2 + Math.cos(angle) * ring,
    y: height / 2 + Math.sin(angle) * ring,
  };
}

function _layoutGraph(nodes, edges, width, height) {
  const positions = new Map();
  const nodeIndex = new Map(nodes.map((node, index) => [node.id, index]));
  const degree = new Map(nodes.map((node) => [node.id, 0]));
  const links = [];

  for (const edge of edges) {
    const sourceIndex = nodeIndex.get(edge.source);
    const targetIndex = nodeIndex.get(edge.target);
    if (sourceIndex === undefined || targetIndex === undefined) continue;
    links.push([sourceIndex, targetIndex, edge]);
    degree.set(nodes[sourceIndex].id, (degree.get(nodes[sourceIndex].id) || 0) + 1);
    degree.set(nodes[targetIndex].id, (degree.get(nodes[targetIndex].id) || 0) + 1);
  }

  for (let i = 0; i < nodes.length; i += 1) {
    positions.set(nodes[i].id, {
      ..._graphSeedPosition(nodes[i], i, nodes.length, width, height),
      vx: 0,
      vy: 0,
    });
  }

  const radii = new Map(nodes.map((node) => [node.id, _graphNodeRadius(node, degree.get(node.id) || 0)]));

  const repel = 4800;
  const spring = 0.008;
  const center = 0.0025;
  const damping = 0.82;

  for (let iter = 0; iter < 120; iter += 1) {
    for (let i = 0; i < nodes.length; i += 1) {
      const a = positions.get(nodes[i].id);
      if (!a) continue;
      for (let j = i + 1; j < nodes.length; j += 1) {
        const b = positions.get(nodes[j].id);
        if (!b) continue;
        let dx = b.x - a.x;
        let dy = b.y - a.y;
        let dist = Math.sqrt(dx * dx + dy * dy) || 1;
        const minDist = (radii.get(nodes[i].id) || 10) + (radii.get(nodes[j].id) || 10) + 42;
        if (dist < minDist) dist = minDist;
        const force = repel / (dist * dist);
        const fx = (dx / dist) * force;
        const fy = (dy / dist) * force;
        a.vx -= fx;
        a.vy -= fy;
        b.vx += fx;
        b.vy += fy;
      }
    }

    for (const [sourceIndex, targetIndex] of links) {
      const a = positions.get(nodes[sourceIndex].id);
      const b = positions.get(nodes[targetIndex].id);
      if (!a || !b) continue;
      const dx = b.x - a.x;
      const dy = b.y - a.y;
      const dist = Math.sqrt(dx * dx + dy * dy) || 1;
      const desired = (radii.get(nodes[sourceIndex].id) || 10) + (radii.get(nodes[targetIndex].id) || 10) + 84;
      const force = (dist - desired) * spring;
      const fx = (dx / dist) * force;
      const fy = (dy / dist) * force;
      a.vx += fx;
      a.vy += fy;
      b.vx -= fx;
      b.vy -= fy;
    }

    for (const node of nodes) {
      const pos = positions.get(node.id);
      if (!pos) continue;
      pos.vx += (width / 2 - pos.x) * center;
      pos.vy += (height / 2 - pos.y) * center;
      pos.vx *= damping;
      pos.vy *= damping;
      pos.x += pos.vx;
      pos.y += pos.vy;
      pos.x = Math.max(24, Math.min(width - 24, pos.x));
      pos.y = Math.max(24, Math.min(height - 24, pos.y));
    }
  }

  return positions;
}

function _graphCommunityNodeId(communityId) {
  return `community:${String(communityId || "").trim() || "__ungrouped__"}`;
}

function _communityInspectabilityScore(cluster) {
  const nodeCount = Math.max(0, Number(cluster?.node_count || 0));
  const boundaryCount = Math.max(0, Number(cluster?.boundary_node_count || 0));
  if (!nodeCount) return 0;
  return (boundaryCount / nodeCount) * Math.log2(nodeCount + 1);
}

function _isMeaningfulCommunity(cluster) {
  return Math.max(0, Number(cluster?.node_count || 0)) >= GRAPH_MIN_COMMUNITY_NODES;
}

function _buildCommunityOverviewGraph(nodes, edges, communities, selectedRelations) {
  const nodeById = new Map(nodes.map(node => [String(node.id || ""), node]));
  const communityByNodeId = new Map();
  const communityById = new Map();
  const orderedCommunities = Array.isArray(communities) ? communities.slice() : [];
  orderedCommunities.sort((a, b) =>
    _communityInspectabilityScore(b) - _communityInspectabilityScore(a)
    || (Number(b.boundary_node_count) || 0) - (Number(a.boundary_node_count) || 0)
    || (Number(b.node_count) || 0) - (Number(a.node_count) || 0)
    || String(a.label || a.community_id || "").localeCompare(String(b.label || b.community_id || ""))
  );

  for (const cluster of orderedCommunities) {
    const communityId = String(cluster?.community_id || "").trim();
    if (!communityId) continue;
    if (!_isMeaningfulCommunity(cluster)) continue;
    const nodeIds = Array.isArray(cluster.node_ids) ? cluster.node_ids.map(id => String(id)) : [];
    const meta = {
      ...cluster,
      community_id: communityId,
      node_ids: nodeIds,
      label: String(cluster.label || communityId).trim() || communityId,
    };
    communityById.set(communityId, meta);
    for (const nodeId of nodeIds) {
      if (!communityByNodeId.has(nodeId)) communityByNodeId.set(nodeId, meta);
    }
  }

  const grouped = new Map();
  const fallbackId = "__ungrouped__";

  for (const node of nodes) {
    const nodeId = String(node.id || "").trim();
    if (!nodeId) continue;
    const cluster = communityByNodeId.get(nodeId) || null;
    const communityId = cluster ? cluster.community_id : fallbackId;
    const community = cluster || communityById.get(communityId) || {
      community_id: communityId,
      label: "Ungrouped",
      node_count: 0,
      boundary_node_count: 0,
      node_ids: [],
    };
    let bucket = grouped.get(communityId);
    if (!bucket) {
      bucket = {
        community_id: community.community_id,
        label: community.label || community.community_id,
        node_ids: [],
        node_count: 0,
        total_node_count: Number(community.node_count) || 0,
        boundary_node_count: Number(community.boundary_node_count) || 0,
      };
      grouped.set(communityId, bucket);
    }
    bucket.node_ids.push(nodeId);
    bucket.node_count += 1;
  }

  const buckets = Array.from(grouped.values());
  const realBuckets = buckets.filter(bucket => bucket.community_id !== fallbackId && bucket.node_count > 0);
  const overviewBuckets = realBuckets.length
    ? realBuckets
        .sort((a, b) =>
          _communityInspectabilityScore(b) - _communityInspectabilityScore(a)
          || (Number(b.boundary_node_count) || 0) - (Number(a.boundary_node_count) || 0)
          || (Number(b.node_count) || 0) - (Number(a.node_count) || 0)
          || String(a.label || a.community_id || "").localeCompare(String(b.label || b.community_id || ""))
        )
        .slice(0, GRAPH_OVERVIEW_COMMUNITY_LIMIT)
    : buckets
        .filter(bucket => bucket.community_id === fallbackId && bucket.node_count > 0)
        .slice(0, 1);

  const overviewNodes = overviewBuckets
    .sort((a, b) =>
      _communityInspectabilityScore(b) - _communityInspectabilityScore(a)
      || (Number(b.boundary_node_count) || 0) - (Number(a.boundary_node_count) || 0)
      || (Number(b.node_count) || 0) - (Number(a.node_count) || 0)
      || String(a.label || a.community_id || "").localeCompare(String(b.label || b.community_id || ""))
    )
    .map(bucket => ({
      id: _graphCommunityNodeId(bucket.community_id),
      label: bucket.label || bucket.community_id,
      kind: "community",
      community_id: bucket.community_id,
      node_count: bucket.node_count,
      total_node_count: bucket.total_node_count || bucket.node_count,
      boundary_node_count: bucket.boundary_node_count || 0,
    }));

  if (!realBuckets.length) {
    return {
      nodes: [],
      edges: [],
      fallback_nodes: overviewNodes,
    };
  }

  const aggregateByCommunityId = new Map(overviewNodes.map(node => [String(node.community_id || ""), node]));
  const aggregatedEdges = new Map();

  for (const edge of edges) {
    const relation = String(edge.relation || "");
    if (selectedRelations && selectedRelations.size && !selectedRelations.has(relation)) continue;
    const sourceNode = nodeById.get(String(edge.source || ""));
    const targetNode = nodeById.get(String(edge.target || ""));
    if (!sourceNode || !targetNode) continue;
    const sourceCluster = communityByNodeId.get(String(sourceNode.id || "")) || null;
    const targetCluster = communityByNodeId.get(String(targetNode.id || "")) || null;
    const sourceCommunityId = sourceCluster ? sourceCluster.community_id : fallbackId;
    const targetCommunityId = targetCluster ? targetCluster.community_id : fallbackId;
    if (sourceCommunityId === targetCommunityId) continue;
    const sourceCommunity = aggregateByCommunityId.get(sourceCommunityId);
    const targetCommunity = aggregateByCommunityId.get(targetCommunityId);
    if (!sourceCommunity || !targetCommunity) continue;
    const key = `${sourceCommunity.id}::${targetCommunity.id}::${relation}`;
    const current = aggregatedEdges.get(key) || {
      source: sourceCommunity.id,
      target: targetCommunity.id,
      relation,
      count: 0,
      weight: 0,
    };
    current.count += 1;
    current.weight += 1;
    aggregatedEdges.set(key, current);
  }

  return {
    nodes: overviewNodes,
    edges: Array.from(aggregatedEdges.values()).sort((a, b) =>
      (Number(b.weight) || 0) - (Number(a.weight) || 0)
      || String(a.source).localeCompare(String(b.source))
      || String(a.target).localeCompare(String(b.target))
      || String(a.relation).localeCompare(String(b.relation))
    ),
  };
}

function GraphPanel({ snapshot }) {
  // Project-layer only; framework-layer visualization is deferred to the graph
  // visualization/navigation overhaul, not exposed in this panel.
  const layer = "project";
  const [graph, setGraph] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");
  const [viewMode, setViewMode] = useState("overview");
  const [selectedKinds, setSelectedKinds] = useState(() => new Set());
  const [selectedRelations, setSelectedRelations] = useState(() => new Set(DEFAULT_GRAPH_RELATIONS));
  const [selectedNodeId, setSelectedNodeId] = useState("");
  const [hoveredNodeId, setHoveredNodeId] = useState("");
  const [selectedFile, setSelectedFile] = useState("");
  const [selectedClusterId, setSelectedClusterId] = useState("");
  const OVERVIEW_CRUMB = { label: "Overview", viewMode: "overview", selectedNodeId: "", selectedClusterId: "", selectedFile: "" };
  const [navHistory, setNavHistory] = useState([OVERVIEW_CRUMB]);
  // Refs for browser-history sync — avoid stale closures in popstate/keydown handlers.
  const _navHistoryRef = useRef([OVERVIEW_CRUMB]);
  const _browserNavIndexRef = useRef(0);
  const _suppressPopstateRef = useRef(false);
  const graphVersion = snapshot?.health?.graph?.[layer]?.graph_version || snapshot?.health?.graph?.[layer]?.graph_mtime || 0;

  useEffect(() => {
    let cancelled = false;
    const controller = new AbortController();
    async function loadGraph() {
      setLoading(true);
      setError("");
      try {
        const response = await fetch(`/api/graph?layer=${encodeURIComponent(layer)}`, { cache: "no-store", signal: controller.signal });
        if (!response.ok) {
          throw new Error(`Graph request failed with ${response.status}`);
        }
        const data = await response.json();
        if (!cancelled) {
          setGraph(data);
          setSelectedNodeId("");
        }
      } catch (err) {
        if (!cancelled && err.name !== "AbortError") {
          setError(err.message || String(err));
          setGraph(null);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    loadGraph();
    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [layer, graphVersion]);

  const nodes = graph?.nodes || [];
  const edges = graph?.edges || [];
  const graphCounts = graph?.counts || {};
  const clusterCommunities = Array.isArray(graph?.clusters?.communities) ? graph.clusters.communities.slice() : [];
  const meaningfulCommunities = clusterCommunities.filter(_isMeaningfulCommunity);
  const selectedCluster = selectedClusterId
    ? meaningfulCommunities.find(cluster => String(cluster.community_id || "") === selectedClusterId) || null
    : null;
  const selectedClusterNodeIds = selectedCluster ? new Set((selectedCluster.node_ids || []).map(id => String(id))) : null;
  const inFixedCommunity = selectedCluster?.kind === "fixed";
  // Exclude fixed-community nodes only when drilling into a production community,
  // so Tests/Config/etc. don't leak into focus views. In the overview and when
  // viewing a fixed community itself, all nodes are visible.
  const inProductionDrillDown = selectedCluster !== null && !inFixedCommunity;
  const fixedNodeIds = inProductionDrillDown ? (() => {
    const ids = new Set();
    for (const c of clusterCommunities) {
      if (c.kind === "fixed") for (const id of (c.node_ids || [])) ids.add(String(id));
    }
    return ids;
  })() : null;
  const relationKinds = Array.from(new Set(edges.map(e => String(e.relation || "")).filter(Boolean))).sort();
  const nodeKinds = Array.from(new Set(nodes.map(n => String(n.kind || "")).filter(Boolean))).sort();
  const graphKindOptions = nodeKinds.length ? nodeKinds : ["module", "class", "function", "doc", "seed", "external"];
  const fileCounts = new Map();
  for (const node of nodes) {
    const key = String(node.source_file || "").trim();
    if (!key) continue;
    fileCounts.set(key, (fileCounts.get(key) || 0) + 1);
  }
  const fileOptions = Array.from(fileCounts.entries())
    .sort((a, b) => b[1] - a[1] || String(a[0]).localeCompare(String(b[0])))
    .slice(0, 24)
    .map(([path, count]) => ({ path, count }));
  const filteredNodes = nodes.filter(node => {
    const q = query.trim().toLowerCase();
    const matchesQuery = !q
      || String(node.id || "").toLowerCase().includes(q)
      || String(node.label || "").toLowerCase().includes(q)
      || String(node.source_file || "").toLowerCase().includes(q);
    const matchesKind = !selectedKinds.size || selectedKinds.has(String(node.kind || ""));
    const matchesFile = !selectedFile || String(node.source_file || "") === selectedFile;
    const matchesCluster = !selectedClusterNodeIds || selectedClusterNodeIds.has(node.id);
    const notFixed = !fixedNodeIds || !fixedNodeIds.has(String(node.id || ""));
    return matchesQuery && matchesKind && matchesFile && matchesCluster && notFixed;
  });
  const degreeMap = new Map();
  for (const edge of edges) {
    degreeMap.set(edge.source, (degreeMap.get(edge.source) || 0) + 1);
    degreeMap.set(edge.target, (degreeMap.get(edge.target) || 0) + 1);
  }
  const previewNodeId = selectedNodeId || hoveredNodeId;
  const connectedNodeIds = new Set();
  if (selectedNodeId) {
    connectedNodeIds.add(selectedNodeId);
    for (const edge of edges) {
      if (edge.source === selectedNodeId || edge.target === selectedNodeId) {
        connectedNodeIds.add(edge.source);
        connectedNodeIds.add(edge.target);
      }
    }
  }
  const sortedByDegree = filteredNodes
    .slice()
    .sort((a, b) => (degreeMap.get(b.id) || 0) - (degreeMap.get(a.id) || 0) || String(a.id).localeCompare(String(b.id)));
  const topHubNodes = sortedByDegree.slice(0, 8);
  const overviewSeedNodes = [];
  const overviewSeenIds = new Set();
  const addOverviewNode = (node) => {
    if (!node || overviewSeenIds.has(node.id)) return;
    overviewSeenIds.add(node.id);
    overviewSeedNodes.push(node);
  };
  for (const node of topHubNodes) addOverviewNode(node);
  for (const file of fileOptions.slice(0, 4)) {
    const fileNodes = filteredNodes
      .filter(node => String(node.source_file || "") === file.path)
      .slice()
      .sort((a, b) => (degreeMap.get(b.id) || 0) - (degreeMap.get(a.id) || 0) || String(a.id).localeCompare(String(b.id)))
      .slice(0, 6);
    for (const node of fileNodes) addOverviewNode(node);
  }
  const communityOverview = viewMode === "overview" && !selectedClusterId && meaningfulCommunities.length > 0;
  const overviewGraph = communityOverview
    ? _buildCommunityOverviewGraph(filteredNodes, edges, meaningfulCommunities, selectedRelations)
    : null;
  const hasCommunityOverview = Boolean(communityOverview && overviewGraph && overviewGraph.nodes.length);
  const overviewNodes = viewMode === "overview"
    ? hasCommunityOverview
      ? overviewGraph.nodes
      : overviewGraph?.fallback_nodes?.length
        ? overviewGraph.fallback_nodes.slice(0, 1)
        : overviewSeedNodes.slice(0, GRAPH_OVERVIEW_SEED_LIMIT)
    : sortedByDegree.slice(0, 120);
  const clusterNodes = selectedClusterNodeIds
    ? filteredNodes
        .filter(node => selectedClusterNodeIds.has(node.id))
        .slice()
        .sort((a, b) => (degreeMap.get(b.id) || 0) - (degreeMap.get(a.id) || 0) || String(a.id).localeCompare(String(b.id)))
        .slice(0, GRAPH_COMMUNITY_DRILLDOWN_LIMIT)
    : [];
  const visibleClusterNodeIds = selectedClusterNodeIds ? new Set(clusterNodes.map(node => node.id)) : null;
  const focusedNodes = selectedNodeId
    ? filteredNodes.filter(node => connectedNodeIds.has(node.id))
    : overviewNodes;
  const focusedInCluster = selectedNodeId && selectedClusterId && selectedClusterNodeIds
    ? focusedNodes.filter(node => selectedClusterNodeIds.has(node.id))
    : null;
  const visibleNodes = viewMode === "focus" && selectedNodeId
    ? (focusedInCluster || focusedNodes)
    : selectedClusterId
      ? clusterNodes
      : overviewNodes;
  const visibleNodeIds = new Set(visibleNodes.map(n => n.id));
  const visibleEdges = edges.filter(edge => {
    const relation = String(edge.relation || "");
    const relationOk = !selectedRelations.size || selectedRelations.has(relation);
    const nodeMatch = viewMode === "focus" && selectedNodeId
      ? (edge.source === selectedNodeId || edge.target === selectedNodeId) &&
        (focusedInCluster ? visibleNodeIds.has(edge.source) && visibleNodeIds.has(edge.target) : true)
      : hasCommunityOverview
        ? false
        : visibleClusterNodeIds
        ? visibleClusterNodeIds.has(edge.source) && visibleClusterNodeIds.has(edge.target)
        : visibleNodeIds.has(edge.source) && visibleNodeIds.has(edge.target);
    return relationOk && nodeMatch;
  });
  const visibleCommunityEdges = hasCommunityOverview ? overviewGraph.edges : visibleEdges;
  if (!selectedNodeId && previewNodeId) {
    connectedNodeIds.add(previewNodeId);
    for (const edge of visibleCommunityEdges) {
      if (edge.source === previewNodeId || edge.target === previewNodeId) {
        connectedNodeIds.add(edge.source);
        connectedNodeIds.add(edge.target);
      }
    }
  }
  const graphWidth = 1040;
  const graphHeight = 760;
  const layout = React.useMemo(
    () => _layoutGraph(visibleNodes, visibleCommunityEdges, graphWidth, graphHeight),
    [visibleNodes, visibleCommunityEdges]
  );
  const selectedNode = visibleNodes.find(node => node.id === selectedNodeId) || null;
  const selectedEdges = selectedNode
    ? visibleCommunityEdges.filter(edge => edge.source === selectedNode.id || edge.target === selectedNode.id)
    : [];
  const topNodes = topHubNodes.slice(0, 6);
  const communityQuickPickPool = clusterCommunities
    .filter(cluster => _isMeaningfulCommunity(cluster))
    .sort((a, b) =>
      _communityInspectabilityScore(b) - _communityInspectabilityScore(a)
      || (Number(b.boundary_node_count) || 0) - (Number(a.boundary_node_count) || 0)
      || (Number(b.node_count) || 0) - (Number(a.node_count) || 0)
      || String(a.label || a.community_id || "").localeCompare(String(b.label || b.community_id || ""))
    );
  const topCommunities = (communityQuickPickPool.length ? communityQuickPickPool : meaningfulCommunities.slice())
    .sort((a, b) =>
      _communityInspectabilityScore(b) - _communityInspectabilityScore(a)
      || (Number(b.boundary_node_count) || 0) - (Number(a.boundary_node_count) || 0)
      || (Number(b.node_count) || 0) - (Number(a.node_count) || 0)
      || String(a.community_id || "").localeCompare(String(b.community_id || ""))
    )
    .slice(0, GRAPH_COMMUNITY_QUICK_PICK_LIMIT);
  const truncated = filteredNodes.length > visibleNodes.length;
  const overviewLabel = hasCommunityOverview
    ? `${visibleNodes.length} communities`
    : `${visibleNodes.length} visible nodes`;
  const edgeLabel = hasCommunityOverview
    ? `${visibleCommunityEdges.length} community links`
    : `${visibleEdges.length} visible edges`;
  const selectedMode = selectedNodeId ? "focus" : selectedClusterId ? "overview" : viewMode;
  const graphEdgeArrowInset = 1.5;
  const _applyNavState = (crumb) => {
    setViewMode(crumb.viewMode);
    setSelectedNodeId(crumb.selectedNodeId);
    setSelectedClusterId(crumb.selectedClusterId);
    setSelectedFile(crumb.selectedFile);
    setHoveredNodeId("");
  };

  const _setNavHistory = (newHistory) => {
    _navHistoryRef.current = newHistory;
    setNavHistory(newHistory);
  };

  const navigateToCrumb = (index) => {
    const sliced = _navHistoryRef.current.slice(0, index + 1);
    if (!sliced.length) return;
    const delta = index - _browserNavIndexRef.current;
    if (delta !== 0) { _suppressPopstateRef.current = true; history.go(delta); }
    _browserNavIndexRef.current = index;
    _applyNavState(sliced[sliced.length - 1]);
    _setNavHistory(sliced);
  };

  const backToOverview = () => {
    const delta = -_browserNavIndexRef.current;
    if (delta !== 0) { _suppressPopstateRef.current = true; history.go(delta); }
    _browserNavIndexRef.current = 0;
    _applyNavState(OVERVIEW_CRUMB);
    _setNavHistory([OVERVIEW_CRUMB]);
  };

  // Stamp the base browser history entry so popstate can identify our entries.
  useEffect(() => {
    history.replaceState({ wfGraph: true, navIndex: 0 }, "");
  }, []);

  // Browser back/forward (trackpad swipe, browser buttons) → restore nav state.
  useEffect(() => {
    function onPopState(e) {
      if (_suppressPopstateRef.current) { _suppressPopstateRef.current = false; return; }
      if (!e.state?.wfGraph) return;
      const targetIndex = e.state.navIndex ?? 0;
      _browserNavIndexRef.current = targetIndex;
      const sliced = _navHistoryRef.current.slice(0, targetIndex + 1);
      if (!sliced.length) return;
      _applyNavState(sliced[sliced.length - 1]);
      _setNavHistory(sliced);
    }
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []); // stable — all access via refs

  // Backspace / Escape / Alt+← → go back one breadcrumb step (skip when typing).
  useEffect(() => {
    function onKeyDown(e) {
      // A modal dialog owns the keyboard while open — let it handle Escape
      // (its native `cancel` event closes it) instead of navigating the graph
      // behind it.
      if (document.querySelector("dialog[open]")) return;
      const isBack =
        e.key === "Backspace" ||
        e.key === "Escape" ||
        (e.key === "ArrowLeft" && e.altKey);
      if (!isBack) return;
      const tag = (e.target?.tagName || "").toLowerCase();
      if (tag === "input" || tag === "textarea" || e.target?.isContentEditable) return;
      if (_browserNavIndexRef.current < 1) return;
      e.preventDefault();
      history.back(); // triggers popstate which handles state update
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []); // stable — all access via refs
  const selectionCard = selectedNode
    ? h("div", { className: "graph-selection" },
        h("div", { className: "graph-selection-title" }, _graphLabel(selectedNode)),
        h("div", { className: "graph-selection-meta muted" }, `${selectedNode.kind} · ${selectedNode.source_file || selectedNode.id}`),
        (selectedNode.is_chokepoint || selectedNode.is_entry_point || selectedNode.dead_code_risk)
          ? h("div", { className: "graph-node-badges" },
              selectedNode.is_chokepoint ? h("span", { className: "graph-node-badge graph-node-badge--chokepoint" }, "Chokepoint") : null,
              selectedNode.is_entry_point ? h("span", { className: "graph-node-badge graph-node-badge--entry" }, "Entry point") : null,
              selectedNode.dead_code_risk ? h("span", { className: "graph-node-badge graph-node-badge--dead" }, "Dead code risk") : null,
            )
          : null,
        selectedEdges.length
          ? h("ul", { className: "graph-selection-edges" },
              selectedEdges.slice(0, 8).map((edge, i) =>
                h("li", { key: `${edge.source}-${edge.target}-${i}` },
                  h("span", { className: "graph-selection-rel" }, edge.relation.replace(/_/g, " ")),
                  " ",
                  h("span", { className: "graph-selection-target" },
                    edge.source === selectedNode.id ? edge.target : edge.source,
                  ),
                )
              ),
            )
          : null,
      )
    : selectedCluster
      ? h("div", { className: "graph-selection" },
          h("div", { className: "graph-selection-title" }, selectedCluster.label || selectedCluster.community_id),
          h("div", { className: "graph-selection-meta muted" }, `${selectedCluster.node_count || 0} nodes · ${selectedCluster.boundary_node_count || 0} boundary nodes`),
        )
      : selectedFile
        ? h("div", { className: "graph-selection" },
            h("div", { className: "graph-selection-title" }, "File neighborhood"),
            h("div", { className: "graph-selection-meta muted" }, selectedFile),
          )
        : null;

  const toggleSelectionSet = (setter, value) => {
    setter(prev => {
      const next = new Set(prev);
      if (next.has(value)) next.delete(value);
      else next.add(value);
      return next;
    });
  };

  const clearGraphFilters = () => {
    setSelectedKinds(new Set());
    setSelectedRelations(new Set(DEFAULT_GRAPH_RELATIONS));
    backToOverview();
  };

  const _pushCrumb = (crumb) => {
    const prev = _navHistoryRef.current;
    const existingIdx = prev.findIndex((c, i) =>
      (c.selectedNodeId === crumb.selectedNodeId &&
       c.selectedClusterId === crumb.selectedClusterId &&
       c.selectedFile === crumb.selectedFile) ||
      (i > 0 && c.label === crumb.label)
    );
    if (existingIdx >= 0) {
      const sliced = prev.slice(0, existingIdx + 1);
      const delta = existingIdx - _browserNavIndexRef.current;
      if (delta !== 0) { _suppressPopstateRef.current = true; history.go(delta); }
      _browserNavIndexRef.current = existingIdx;
      _applyNavState(sliced[sliced.length - 1]);
      _setNavHistory(sliced);
    } else {
      const newHistory = [...prev, crumb];
      const newIndex = newHistory.length - 1;
      history.pushState({ wfGraph: true, navIndex: newIndex }, "");
      _browserNavIndexRef.current = newIndex;
      _setNavHistory(newHistory);
    }
  };

  const selectNode = (nodeId) => {
    const node = nodes.find(n => String(n.id || "") === nodeId);
    const label = node ? _graphLabel(node) : nodeId;
    _pushCrumb({ label, viewMode: "focus", selectedNodeId: nodeId, selectedClusterId, selectedFile: "" });
    setSelectedNodeId(nodeId);
    setHoveredNodeId("");
    setViewMode("focus");
  };

  const selectCluster = (clusterId) => {
    const cluster = meaningfulCommunities.find(c => String(c.community_id || "") === clusterId);
    const label = cluster ? (String(cluster.label || cluster.community_id || clusterId)) : clusterId;
    _pushCrumb({ label, viewMode: "overview", selectedNodeId: "", selectedClusterId: clusterId, selectedFile: "" });
    setSelectedClusterId(clusterId);
    setSelectedNodeId("");
    setHoveredNodeId("");
    setSelectedFile("");
    setViewMode("overview");
  };

  const selectFile = (filePath) => {
    const shortLabel = filePath.split("/").slice(-2).join("/");
    _pushCrumb({ label: shortLabel, viewMode: "files", selectedNodeId: "", selectedClusterId: "", selectedFile: filePath });
    setSelectedFile(filePath);
    setSelectedNodeId("");
    setViewMode("files");
  };

  return h("article", { className: "graph-card" },
    h("div", { className: "graph-header" },
      h("div", null,
        h("h2", { className: "panel-heading" }, "Graph"),
        h("p", { className: "graph-subtitle muted" },
          graph?.present ? `${graphCounts.nodes || nodes.length} nodes · ${graphCounts.edges || edges.length} edges` : "Graph index has not been built yet."
        ),
      ),
      h("div", { className: "graph-layer-switch", role: "tablist", "aria-label": "Graph layer" },
        h("button", {
          type: "button",
          className: "graph-layer-pill graph-layer-pill--active",
          role: "tab",
          "aria-selected": true,
        }, "project"),
      ),
    ),
    h("div", { className: "graph-mode-switch" },
      ["overview", "focus", "files"].map(option =>
        h("button", {
          key: option,
          type: "button",
          className: `graph-layer-pill ${selectedMode === option ? "graph-layer-pill--active" : ""}`,
          onClick: () => {
            setViewMode(option);
            if (option !== "focus") setSelectedNodeId("");
          },
        }, option === "overview" ? "Overview" : option === "focus" ? "Focus" : "Files")
      ),
      h("button", { type: "button", className: "graph-layer-pill", onClick: clearGraphFilters }, "Clear"),
    ),
      h("div", { className: "graph-toolbar" },
        h("label", { className: "graph-search" },
          h("span", { className: "graph-search-label" }, "Filter"),
          h("input", {
            type: "search",
          value: query,
          onChange: (e) => setQuery(e.target.value),
          placeholder: "file, symbol, or path",
          }),
        ),
        h("div", { className: "graph-filter-group" },
          h("span", { className: "graph-filter-label" }, "Kinds"),
          h("div", { className: "graph-kind-pills" },
            graphKindOptions.map(kind => {
              const kindColor = GRAPH_KIND_COLORS[_graphKindBucket(kind)] || "var(--panel-border)";
              const active = selectedKinds.has(kind);
              return h("button", {
                key: kind,
                type: "button",
                className: `graph-filter-pill graph-filter-pill--kind ${active ? "graph-filter-pill--active" : ""}`,
                onClick: () => toggleSelectionSet(setSelectedKinds, kind),
                style: {
                  "--kind-color": kindColor,
                  "--kind-bg": active ? _hexToRgba(kindColor, 0.18) : _hexToRgba(kindColor, 0.08),
                },
              },
                h("span", { className: "graph-kind-swatch", style: { backgroundColor: kindColor } }),
                kind
              );
            }),
          ),
        ),
    ),
    h("details", { className: "graph-filter-details" },
      h("summary", null, "Annotations"),
      h("div", { className: "graph-node-badges graph-annotation-legend" },
        h("span", { className: "graph-node-badge graph-node-badge--chokepoint" }, "Chokepoint — removal disconnects the graph"),
        h("span", { className: "graph-node-badge graph-node-badge--entry" }, "Entry point — nothing imports this file"),
        h("span", { className: "graph-node-badge graph-node-badge--dead" }, "Dead code risk — no external callers"),
      ),
    ),
    h("details", { className: "graph-filter-details" },
      h("summary", null, "Relations"),
      h("div", { className: "graph-filter-group graph-filter-group--relation" },
        (relationKinds.length ? relationKinds : ["defines", "imports", "calls", "doc_references_code"]).map(rel =>
          h("button", {
            key: rel,
            type: "button",
            className: `graph-filter-pill ${selectedRelations.has(rel) ? "graph-filter-pill--active" : ""}`,
            onClick: () => toggleSelectionSet(setSelectedRelations, rel),
          }, rel.replace(/_/g, " "))
        ),
      ),
    ),
      h("div", { className: "graph-quick-picks" },
        h("div", { className: "graph-quick-picks-group" },
          h("span", { className: "graph-filter-label" }, "Top hubs"),
        topNodes.length
          ? topNodes.map(node =>
              h("button", {
                key: node.id,
                type: "button",
                className: `graph-filter-pill ${selectedNodeId === node.id ? "graph-filter-pill--active" : ""}`,
                "aria-pressed": selectedNodeId === node.id,
                onClick: () => selectNode(node.id),
              }, _graphLabel(node))
            )
          : h("span", { className: "graph-quick-picks-empty muted" }, "No nodes yet."),
      ),
      h("div", { className: "graph-quick-picks-group" },
        h("span", { className: "graph-filter-label" }, "Communities"),
        topCommunities.length
          ? topCommunities.map(cluster =>
              h("button", {
                key: cluster.community_id,
                type: "button",
                className: `graph-filter-pill ${selectedClusterId === cluster.community_id ? "graph-filter-pill--active" : ""}`,
                "aria-pressed": selectedClusterId === cluster.community_id,
                onClick: () => selectCluster(cluster.community_id),
                title: `${cluster.node_count || 0} nodes · ${cluster.boundary_node_count || 0} boundary nodes`,
              }, `${cluster.label || cluster.community_id} · ${cluster.node_count || 0}`)
            )
          : h("span", { className: "graph-quick-picks-empty muted" }, "No communities yet."),
      ),
      h("div", { className: "graph-quick-picks-group" },
        h("span", { className: "graph-filter-label" }, "File neighborhoods"),
        fileOptions.length
          ? fileOptions.slice(0, 6).map(file =>
              h("button", {
                key: file.path,
                type: "button",
                className: `graph-filter-pill ${selectedFile === file.path ? "graph-filter-pill--active" : ""}`,
                onClick: () => selectFile(file.path),
              }, file.path.split("/").slice(-2).join("/"))
            )
          : h("span", { className: "graph-quick-picks-empty muted" }, "No file groups yet."),
      ),
    ),
    loading ? h("div", { className: "graph-state muted" }, "Loading graph…") : null,
    error ? h("div", { className: "graph-state graph-state--error" }, error) : null,
    h("nav", { className: "graph-breadcrumb", "aria-label": "Graph navigation" },
      (() => {
        const showEllipsis = navHistory.length > 5;
        const rendered = [];
        if (navHistory.length >= 1) rendered.push({ crumb: navHistory[0], realIdx: 0 });
        if (navHistory.length >= 2) rendered.push({ crumb: navHistory[1], realIdx: 1 });
        if (showEllipsis) rendered.push({ crumb: null, realIdx: -1 });
        const shownSet = new Set(rendered.filter(r => r.realIdx >= 0).map(r => r.realIdx));
        [-3, -2, -1].map(o => navHistory.length + o).filter(idx => idx >= 0 && !shownSet.has(idx))
          .forEach(idx => rendered.push({ crumb: navHistory[idx], realIdx: idx }));
        return rendered.map(({ crumb, realIdx }, visIdx) => {
          if (crumb === null) return h(React.Fragment, { key: "ellipsis" },
            h("span", { className: "graph-breadcrumb-sep", "aria-hidden": "true" }, "›"),
            h("span", { className: "graph-breadcrumb-ellipsis" }, "…"),
          );
          const isLast = realIdx === navHistory.length - 1;
          return h(React.Fragment, { key: realIdx },
            visIdx > 0 ? h("span", { className: "graph-breadcrumb-sep", "aria-hidden": "true" }, "›") : null,
            isLast
              ? h("span", { className: "graph-breadcrumb-current" }, crumb.label)
              : h("button", { type: "button", className: "graph-breadcrumb-item", onClick: () => navigateToCrumb(realIdx) }, crumb.label),
          );
        });
      })(),
    ),
    graph?.present ? h("div", { className: "graph-shell" },
      h("svg", { className: "graph-svg", viewBox: `0 0 ${graphWidth} ${graphHeight}`, role: "img", "aria-label": "Graph visualization" },
        h("defs", null,
          h("marker", {
            id: "graph-arrow",
            markerWidth: 6,
            markerHeight: 6,
            refX: 5.5,
            refY: 3,
            orient: "auto",
            markerUnits: "userSpaceOnUse",
          }, h("path", { d: "M0,0 L0,6 L9,3 z", fill: "currentColor", opacity: 0.58 })),
        ),
        visibleCommunityEdges.map((edge, index) => {
          const source = layout.get(edge.source);
          const target = layout.get(edge.target);
          if (!source || !target) return null;
          const relation = String(edge.relation || "");
          const color = GRAPH_RELATION_COLORS[relation] || "var(--panel-border)";
          const sourceNode = visibleNodes.find(node => node.id === edge.source) || null;
          const targetNode = visibleNodes.find(node => node.id === edge.target) || null;
          const sourceRadius = sourceNode ? _graphNodeRadius(sourceNode, degreeMap.get(edge.source) || 0) : 10;
          const targetRadius = targetNode ? _graphNodeRadius(targetNode, degreeMap.get(edge.target) || 0) : 10;
          const dx = target.x - source.x;
          const dy = target.y - source.y;
          const distance = Math.hypot(dx, dy) || 1;
          const ux = dx / distance;
          const uy = dy / distance;
          const x1 = source.x + ux * (sourceRadius + graphEdgeArrowInset);
          const y1 = source.y + uy * (sourceRadius + graphEdgeArrowInset);
          const x2 = target.x - ux * (targetRadius + graphEdgeArrowInset + 0.75);
          const y2 = target.y - uy * (targetRadius + graphEdgeArrowInset + 0.75);
          const edgeFocusNodeId = hoveredNodeId && !selectedNodeId ? hoveredNodeId : selectedNodeId;
          const edgeFocused = !edgeFocusNodeId || edge.source === edgeFocusNodeId || edge.target === edgeFocusNodeId;
          const edgeSelected = selectedNodeId && edgeFocused;
          const edgePreview = hoveredNodeId && !selectedNodeId && edgeFocused;
          const edgeWeight = Math.max(1, Number(edge.weight || edge.count || 1));
          return h("line", {
            key: `${edge.source}-${edge.target}-${edge.relation}-${index}`,
            x1,
            y1,
            x2,
            y2,
            className: `graph-edge${previewNodeId && !edgeFocused ? " graph-edge--dimmed" : ""}${edgeSelected ? " graph-edge--highlighted" : ""}${edgePreview ? " graph-edge--preview" : ""}`,
            stroke: color,
            "marker-end": "url(#graph-arrow)",
            style: {
              opacity: previewNodeId && !edgeFocused ? 0.08 : edgeSelected ? 0.58 : edgePreview ? 0.56 : 0.34,
              strokeWidth: edgeSelected ? 2.0 : edgePreview ? 1.85 : Math.min(4.0, 1.15 + Math.log2(edgeWeight + 1) * 0.35),
            },
            onClick: () => selectNode(edge.source),
          });
        }),
        visibleNodes.map((node, index) => {
          const pos = layout.get(node.id);
          if (!pos) return null;
          const degree = degreeMap.get(node.id) || 0;
          const radius = _graphNodeRadius(node, degree);
          const kind = _graphKindBucket(node.kind);
          const isSelected = selectedNodeId === node.id;
          const isHovered = hoveredNodeId === node.id;
          const isConnected = !previewNodeId || connectedNodeIds.has(node.id);
          const showLabel = true;
          return h("g", {
            key: node.id,
            className: `graph-node graph-node--${kind}${isSelected ? " graph-node--selected" : ""}${previewNodeId && !isConnected ? " graph-node--dimmed" : ""}${isHovered && !isSelected ? " graph-node--preview" : ""}`,
            transform: `translate(${pos.x}, ${pos.y})`,
            onClick: () => hasCommunityOverview && node.kind === "community" ? selectCluster(node.community_id) : selectNode(node.id),
            onMouseEnter: () => setHoveredNodeId(node.id),
            onMouseLeave: () => setHoveredNodeId(current => current === node.id ? "" : current),
          },
            node.is_chokepoint
              ? h("circle", { r: radius + 5, fill: "none", stroke: "#e65100", strokeWidth: 2, strokeDasharray: "4 2.5", style: { opacity: 0.8 } })
              : null,
            node.is_entry_point
              ? h("circle", { r: radius + 4, fill: "none", stroke: "#00897b", strokeWidth: 1.5, style: { opacity: 0.75 } })
              : null,
            node.dead_code_risk
              ? h("circle", { r: radius + 4, fill: "none", stroke: "#b00020", strokeWidth: 1.5, strokeDasharray: "3 3", style: { opacity: 0.7 } })
              : null,
            h("circle", {
              r: radius,
              fill: GRAPH_KIND_COLORS[kind],
              stroke: isSelected ? "var(--ink)" : "rgba(255,255,255,0.75)",
              strokeWidth: isSelected ? 3 : 1.5,
              style: { opacity: previewNodeId && !isConnected ? 0.26 : isSelected ? 1 : isHovered ? 0.98 : 0.9 },
            }),
            showLabel
              ? h("text", { className: "graph-node-label", y: radius + 8, textAnchor: "middle" }, _graphLabel(node))
              : null,
          );
        }),
      ),
        h("div", { className: "graph-summary" },
        h("div", { className: "graph-summary-meta" },
          h("span", { className: "graph-summary-pill" }, overviewLabel),
          h("span", { className: "graph-summary-pill" }, edgeLabel),
          viewMode === "overview" && !selectedClusterId && truncated
            ? h("span", { className: "graph-summary-pill" }, communityOverview ? "Community overview" : `Showing top ${visibleNodes.length} by connectivity`)
            : null,
          selectedCluster
            ? h("span", { className: "graph-summary-pill" }, `Community: ${selectedCluster.label || selectedCluster.community_id}`)
            : null,
          selectedFile ? h("span", { className: "graph-summary-pill" }, `File: ${selectedFile.split("/").slice(-2).join("/")}`) : null,
        ),
        selectionCard,
      ),
    ) : h("div", { className: "empty-state" }, "Graph data is not available yet."),
  );
}

function IndexDialog({ health, onClose }) {
  const dialogRef = useRef(null);
  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    dialog.showModal();
    const onCancel = () => onClose();
    dialog.addEventListener("cancel", onCancel);
    return () => dialog.removeEventListener("cancel", onCancel);
  }, [onClose]);
  const handleBackdropClick = (e) => { if (e.target === dialogRef.current) onClose(); };

  const proj = health?.index?.project || {};
  const graphProj = health?.graph?.project || {};

  const idxStatus = String(proj.build_status || "").toLowerCase();
  const idxRunning = idxStatus === "running";
  const idxFailed  = idxStatus === "failed";
  const idxAction  = proj.mode === "rebuild" ? "Rebuilding" : "Updating";
  const statusPill = idxRunning
    ? h("span", { className: "index-build-badge index-build-badge--running" }, `${idxAction}…`)
    : idxFailed
      ? h("span", { className: "index-build-badge index-build-badge--failed" }, "Build failed")
      : null;
  const age = relativeAge(proj.built_at);

  return h("dialog", { ref: dialogRef, className: "agent-dialog index-dialog", onClick: handleBackdropClick },
    h("div", { className: "agent-dialog-header" },
      h("div", { className: "agent-dialog-header-text" },
        h("h2", { className: "agent-dialog-title" }, "Index"),
        (age || statusPill) ? h("div", { className: "index-dialog-header-pills" },
          age ? h("span", { className: "index-meta-pill" }, `updated ${age}`) : null,
          statusPill,
        ) : null,
      ),
      h("button", { className: "agent-dialog-close", "aria-label": "Close", onClick: onClose }, "×"),
    ),
    h("div", { className: "agent-dialog-body" },
      h(IndexSection, { label: "Semantic", idx: proj }),
      h(GraphIndexSection, { label: "Graph", idx: graphProj }),
    ),
  );
}

function IndexSection({ label, idx }) {
  const staleLocksCleaned = Array.isArray(idx.stale_locks_cleaned) ? idx.stale_locks_cleaned.length : 0;

  if (!idx.present) {
    return h("div", { className: "index-section index-section--missing" },
      h("div", { className: "index-section-label" }, label),
      h("span", { className: "index-stat-missing" }, "not built"),
    );
  }
  const filesIndexed = Number(idx.files_indexed) || 0;
  const docChunks = Number(idx.doc_chunks) || 0;
  const codeChunks = Number(idx.code_chunks) || 0;
  const totalChunks = docChunks + codeChunks;
  const modelPill = (() => {
    const dm = idx.docs_model, cm = idx.code_model;
    if (dm && cm && dm !== cm) {
      return [
        h("span", { className: "index-meta-pill index-meta-pill--model", key: "dm" }, `docs: ${dm}`),
        h("span", { className: "index-meta-pill index-meta-pill--model", key: "cm" }, `code: ${cm}`),
      ];
    }
    const single = dm || cm || idx.model;
    return single ? h("span", { className: "index-meta-pill index-meta-pill--model" }, single) : null;
  })();
  return h("div", { className: "index-section" },
    h("div", { className: "index-section-label" }, label),
    h("div", { className: "index-stat-grid" },
      h("div", { className: "index-stat" },
        h("span", { className: "index-stat-value" }, filesIndexed.toLocaleString()),
        h("span", { className: "index-stat-label" }, "files"),
      ),
      h("div", { className: "index-stat" },
        h("span", { className: "index-stat-value" }, totalChunks.toLocaleString()),
        h("span", { className: "index-stat-label" }, "chunks"),
      ),
      docChunks > 0 ? h("div", { className: "index-stat" },
        h("span", { className: "index-stat-value" }, docChunks.toLocaleString()),
        h("span", { className: "index-stat-label" }, "doc"),
      ) : null,
      codeChunks > 0 ? h("div", { className: "index-stat" },
        h("span", { className: "index-stat-value" }, codeChunks.toLocaleString()),
        h("span", { className: "index-stat-label" }, "code"),
      ) : null,
    ),
    modelPill ? h("div", { className: "index-meta-row" }, modelPill) : null,
    staleLocksCleaned ? h("div", { className: "index-build-status" },
      h("span", { className: "index-build-badge index-build-badge--current" },
        `Cleaned ${staleLocksCleaned} stale ${p(staleLocksCleaned, "lock", "locks")}`),
    ) : null,
  );
}

function GraphIndexSection({ label, idx }) {

  if (!idx.present) {
    return h("div", { className: "index-section index-section--missing" },
      h("div", { className: "index-section-label" }, label),
      h("span", { className: "index-stat-missing" }, "not built"),
    );
  }

  const nodeCount = Number(idx.counts?.nodes) || 0;
  const edgeCount = Number(idx.counts?.edges) || 0;
  const fileCount = Number(idx.counts?.files) || 0;
  const clusterAlgorithm = idx.clusters?.cluster_algorithm;

  return h("div", { className: "index-section" },
    h("div", { className: "index-section-label" }, label),
    h("div", { className: "index-stat-grid" },
      h("div", { className: "index-stat" },
        h("span", { className: "index-stat-value" }, fileCount.toLocaleString()),
        h("span", { className: "index-stat-label" }, "files"),
      ),
      h("div", { className: "index-stat" },
        h("span", { className: "index-stat-value" }, nodeCount.toLocaleString()),
        h("span", { className: "index-stat-label" }, "nodes"),
      ),
      h("div", { className: "index-stat" },
        h("span", { className: "index-stat-value" }, edgeCount.toLocaleString()),
        h("span", { className: "index-stat-label" }, "edges"),
      ),
    ),
    clusterAlgorithm ? h("div", { className: "index-meta-row" },
      h("span", { className: "index-meta-pill index-meta-pill--model" }, clusterAlgorithm),
    ) : null,
  );
}

function ChangesTable({ changes, title, onChangeClick }) {
  const CAP = 15;
  const doneCount = changes.filter(c => isDone(c.status)).length;
  const pending   = changes.filter(c => !isDone(c.status));
  const shown     = pending.slice(0, CAP);
  const pendingHidden = pending.length - shown.length;

  let footer = null;
  if (pendingHidden > 0 && doneCount > 0)
    footer = h("p", { className: "muted" }, `${pendingHidden} more open + ${doneCount} completed ${p(doneCount, "change", "changes")}.`);
  else if (pendingHidden > 0)
    footer = h("p", { className: "muted" }, `${pendingHidden} more open ${p(pendingHidden, "change", "changes")}.`);
  else if (doneCount > 0)
    footer = h("p", { className: "muted" }, `${doneCount} completed ${p(doneCount, "change", "changes")}.`);

  let body;
  if (!changes.length)
    body = h("div", { className: "empty-state" }, "No changes in this bucket.");
  else if (!shown.length)
    body = h("div", { className: "empty-state" }, `All ${doneCount} ${p(doneCount, "change", "changes")} complete.`);
  else
    body = h("div", { className: "table-wrap" },
      h("table", null,
        h("thead", null,
          h("tr", null,
            h("th", null, "Change"),
            h("th", { style: { textAlign: "center" } }, "Status"),
            h("th", null, "Tasks"),
            h("th", null, "AC priority"),
          ),
        ),
        h("tbody", null,
          shown.map(c =>
            h("tr", { key: c.change_id },
              h("td", null,
                h("button", {
                  className: "change-id-cell id-link",
                  onClick: onChangeClick ? () => onChangeClick(c) : undefined,
                  title: "View change document",
                },
                  h("div", { className: "wave-change-id" },
                    c.change_id.split("-").flatMap((part, i) => i === 0 ? [part] : ["-", h("wbr", { key: i }), part]),
                  ),
                  h("div", { className: "wave-change-title" }, c.title),
                ),
              ),
              h("td", { style: { textAlign: "center" } }, h("span", { className: badgeClass(c.status) }, c.status)),
              h("td", null, (() => {
                const open = Math.max(0, (Number(c.tasks_total) || 0) - (Number(c.tasks_completed) || 0));
                return c.tasks_total ? `${open} open` : "—";
              })()),
              h("td", null, summarizeAc(c.ac_priority_counts, c.ac_completed_counts)),
            )
          ),
        ),
      ),
    );

  return h("article", { className: "table-card", "aria-label": title },
    h("h2", null, title),
    body,
    footer,
  );
}

function Activity({ activity, onChangeClick }) {
  const all    = activity?.recent_progress || [];
  const today  = todayLocalDate();
  const groups = [];
  const seen   = {};
  for (const item of all.slice(0, 30)) {
    const key = item.date || "undated";
    if (!seen[key]) { seen[key] = []; groups.push({ date: key, items: seen[key] }); }
    seen[key].push(item);
  }

  if (!groups.length)
    return h("div", { className: "empty-state" }, "No progress log entries recorded yet.");

  return h(React.Fragment, null,
    groups.map(({ date, items }) =>
      h("div", { key: date, className: "activity-group" },
        h("div", { className: "activity-date" }, date === today ? "Today" : date),
        h("ol", { className: "timeline" },
          items.map((item, i) => {
            const clickable = !!onChangeClick;
            const handleClick = clickable ? () => onChangeClick({ change_id: item.change_id, wave_id: item.wave_id || "", title: item.title || "" }) : undefined;
            return h("li", {
              key: i,
              onClick: handleClick,
              style: clickable ? { cursor: "pointer" } : undefined,
              tabIndex: clickable ? 0 : undefined,
              role: clickable ? "button" : undefined,
              onKeyDown: clickable ? (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); handleClick(); } } : undefined,
              "aria-label": clickable ? `Open change ${item.change_id}` : undefined,
            },
              h("span", { className: "wave-change-id", style: { display: "block", marginBottom: "2px", fontSize: "0.85rem" } }, item.change_id),
              item.title ? h("div", { className: "wave-change-title", style: { marginBottom: "var(--space-1)" } }, item.title) : null,
              h("div", null, ...renderMarkdownish(item.update || "")),
              item.evidence ? h("div", { className: "muted" }, ...renderMarkdownish(item.evidence)) : null,
            );
          }),
        ),
      )
    ),
  );
}

function renderInline(str) {
  const parts = [];
  const inlineRe = /(\*\*([^*]+)\*\*|`([^`]+)`|\[([^\]]+)\]\(([^)]+)\))/g;
  let lastIndex = 0;
  let partKey = 0;
  let match;
  while ((match = inlineRe.exec(str)) !== null) {
    if (match.index > lastIndex) parts.push(str.slice(lastIndex, match.index));
    if (match[2] !== undefined) {
      parts.push(h("strong", { key: partKey++ }, match[2]));
    } else if (match[3] !== undefined) {
      parts.push(h("code", { key: partKey++ }, match[3]));
    } else if (match[4] !== undefined) {
      const url = match[5].trim();
      const safe = url.startsWith("https://") || url.startsWith("http://");
      parts.push(safe
        ? h("a", { key: partKey++, href: url, target: "_blank", rel: "noopener noreferrer" }, renderInline(match[4]))
        : match[0]);
    }
    lastIndex = match.index + match[0].length;
  }
  if (lastIndex < str.length) parts.push(str.slice(lastIndex));
  return parts.length === 1 && typeof parts[0] === "string" ? parts[0] : parts;
}

function renderMarkdownish(text) {
  const lines = text.split("\n");
  const result = [];
  let listItems = [];
  let tableLines = [];
  let codeLines = null; // null = not in a code block; [] = collecting
  let key = 0;
  let lastH2 = "";

  const flushList = () => {
    if (listItems.length) {
      result.push(h("ul", { key: key++ }, listItems));
      listItems = [];
    }
  };

  const isSeparatorRow = (line) => /^\|[-:| ]+\|$/.test(line);

  const parseTableCells = (line) => {
    const stripped = line.replace(/^\||\|$/g, "");
    const cells = [];
    let current = "";
    let inCode = false;
    for (let i = 0; i < stripped.length; i++) {
      const ch = stripped[i];
      if (ch === "`") { inCode = !inCode; current += ch; }
      else if (ch === "|" && !inCode) { cells.push(current.trim()); current = ""; }
      else { current += ch; }
    }
    cells.push(current.trim());
    return cells;
  };

  const NOWRAP_FIRST_COL_SECTIONS = new Set(["AC Priority", "Progress Log", "Decision Log"]);

  const flushTable = () => {
    if (!tableLines.length) return;
    const rows = tableLines;
    tableLines = [];
    if (rows.length < 1) return;
    const headerCells = parseTableCells(rows[0]);
    const thead = h("thead", { key: "thead" },
      h("tr", { key: "tr" },
        headerCells.map((cell, i) => h("th", { key: i }, renderInline(cell)))
      )
    );
    const bodyRows = [];
    for (let i = 1; i < rows.length; i++) {
      if (isSeparatorRow(rows[i])) continue;
      const cells = parseTableCells(rows[i]);
      bodyRows.push(h("tr", { key: i },
        cells.map((cell, j) => h("td", { key: j }, renderInline(cell)))
      ));
    }
    const tableClass = NOWRAP_FIRST_COL_SECTIONS.has(lastH2) ? "table--nowrap-first" : undefined;
    result.push(h("table", { key: key++, className: tableClass },
      thead,
      bodyRows.length ? h("tbody", { key: "tbody" }, bodyRows) : null
    ));
  };

  for (const raw of lines) {
    const line = raw.trim();

    // Fenced code block handling
    if (codeLines !== null) {
      if (line.startsWith("```")) {
        // Closing fence — emit the block
        result.push(h("pre", { key: key++ }, h("code", null, codeLines.join("\n"))));
        codeLines = null;
      } else {
        codeLines.push(raw); // preserve original indentation inside the block
      }
      continue;
    }
    if (line.startsWith("```")) {
      flushList();
      flushTable();
      codeLines = [];
      continue;
    }

    if (line.startsWith("|")) {
      flushList();
      tableLines.push(line);
    } else if (line.startsWith("### ")) {
      flushList();
      flushTable();
      result.push(h("h3", { key: key++ }, renderInline(line.slice(4))));
    } else if (line.startsWith("## ")) {
      flushList();
      flushTable();
      lastH2 = line.slice(3).trim();
      result.push(h("h2", { key: key++ }, renderInline(line.slice(3))));
    } else if (line.startsWith("# ")) {
      flushList();
      flushTable();
      result.push(h("h1", { key: key++ }, renderInline(line.slice(2))));
    } else if (line.startsWith("- ")) {
      flushTable();
      listItems.push(h("li", { key: key++ }, renderInline(line.slice(2))));
    } else {
      flushList();
      flushTable();
      if (line) result.push(h("p", { key: key++ }, renderInline(line)));
    }
  }
  flushList();
  flushTable();
  // Unclosed fence — emit whatever was collected
  if (codeLines !== null && codeLines.length) {
    result.push(h("pre", { key: key++ }, h("code", null, codeLines.join("\n"))));
  }
  return result;
}

function DocDialog({ title, subtitle, fetchUrl, onClose }) {
  const [content, setContent] = useState(null);
  const [fetchError, setFetchError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    fetch(fetchUrl, { cache: "no-store" })
      .then(r => {
        if (!r.ok) throw new Error(`Server returned ${r.status}`);
        return r.text();
      })
      .then(text => { if (!cancelled) setContent(text); })
      .catch(err => { if (!cancelled) setFetchError(err.message || String(err)); });
    return () => { cancelled = true; };
  }, [fetchUrl]);

  // Parse Owner and Status from the metadata block before stripping it.
  const docMeta = content ? (() => {
    const ownerMatch  = content.match(/^Owner:\s*(.+)$/m);
    const statusMatch = content.match(/^(?:Change )?Status:\s*`?([^`\n]+)`?$/m);
    const items = [];
    if (ownerMatch) items.push({ value: ownerMatch[1].trim(), cls: "dialog-meta-pill" });
    if (statusMatch) {
      const s = statusMatch[1].trim();
      items.push({ value: s, cls: badgeClass(s) });
    }
    return items.length ? items : null;
  })() : null;

  // Strip everything before the first ## section — the metadata block (h1, Owner,
  // Status, wave-id, Title, Change ID, Wave, etc.) is already in the dialog header.
  const bodyText = (() => {
    if (!content) return "";
    const lines = content.split("\n");
    const idx = lines.findIndex(l => l.startsWith("## "));
    return (idx > -1 ? lines.slice(idx) : lines).join("\n").trimStart();
  })();
  const body = fetchError
    ? h("p", { className: "muted" }, `Failed to load document: ${fetchError}`)
    : content === null
      ? h("p", { className: "muted" }, "Loading…")
      : renderMarkdownish(bodyText);

  return h(DialogFrame, { title, subtitle, meta: docMeta, className: "doc-dialog", onClose },
    h("div", { className: "doc-dialog-body" }, body),
  );
}

function AgentDialog({ agent, onClose }) {
  const dialogRef = useRef(null);

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    dialog.showModal();
    const onCancel = () => onClose();
    dialog.addEventListener("cancel", onCancel);
    return () => dialog.removeEventListener("cancel", onCancel);
  }, [onClose]);

  const handleBackdropClick = (e) => {
    if (e.target === dialogRef.current) onClose();
  };

  const categoryLabel = {
    build: "Build", review: "Review", coordinate: "Coordinate",
    operate: "Operate", persona: "Persona", specialist: "Specialist", factor: "Factor",
  }[agent.category] || agent.category;

  const bodyContent = agent.body && agent.body.trim()
    ? renderMarkdownish(agent.body)
    : h("p", { className: "muted" }, "No details available.");

  return h("dialog", { ref: dialogRef, className: "agent-dialog", onClick: handleBackdropClick },
    h("div", { className: `agent-dialog-header agent-dialog-header--${agent.category}` },
      h("div", { className: "agent-dialog-header-text" },
        h("h2", { className: "agent-dialog-title" }, agent.name),
        h("span", { className: `hero-agent-pill hero-agent-pill--${agent.category}` }, categoryLabel),
      ),
      h("button", { className: "agent-dialog-close", "aria-label": "Close", onClick: onClose }, "×"),
    ),
    h("div", { className: "agent-dialog-body" }, bodyContent),
  );
}

function Agents({ agents, onSelectAgent }) {
  if (!agents?.length) return null;
  const categories = ["coordinate", "review", "build", "specialist", "factor", "operate", "persona"];
  const labels = {
    build: "Build", review: "Review", coordinate: "Coordinate",
    operate: "Operate", persona: "Persona", specialist: "Specialist", factor: "Factor",
  };

  return h("div", { className: "hero-agents" },
    h("h2", { className: "hero-agents-heading" }, "Agents"),
    h("div", { className: "hero-agents-grid" },
    categories.map(cat => {
      const items = agents.filter(a => a.category === cat && a.status !== "inactive");
      if (!items.length) return null;
      return h("div", { key: cat, className: "hero-agent-group" },
        h("span", { className: `hero-agent-label hero-agent-label--${cat}` }, labels[cat]),
        h("div", { className: "hero-agent-pills" },
          items.map(a =>
            h("button", {
              key: a.name,
              className: `hero-agent-pill hero-agent-pill--${a.category}`,
              onClick: () => onSelectAgent(a),
              title: labels[a.category],
            },
              a.name,
            )
          ),
        ),
      );
    }),
    ),
  );
}

function Dashboard({ snapshot, pollIdx, sseConnected, dark, onToggleDark }) {
  const [selectedAgent, setSelectedAgent] = useState(null);
  const [selectedFrameworkProcess, setSelectedFrameworkProcess] = useState(null);
  const [showWaves, setShowWaves] = useState(false);
  const [showChanges, setShowChanges] = useState(false);
  const [showAcs, setShowAcs] = useState(false);
  const [showTasks, setShowTasks] = useState(false);
  const [showIndex, setShowIndex] = useState(false);
  const [showAllFiles, setShowAllFiles] = useState(false);
  const [docView, setDocView] = useState(null); // { title, url }

  const openWaveDoc = useCallback((wave) => {
    const url = `/api/doc?type=wave&id=${encodeURIComponent(wave.wave_id)}`;
    setDocView({ title: wave.wave_id, subtitle: wave.title || "", url });
  }, []);

  const openChangeDoc = useCallback((change) => {
    const base = `/api/doc?type=change&id=${encodeURIComponent(change.change_id)}`;
    const url = change.path
      ? `${base}&path=${encodeURIComponent(change.path)}`
      : `${base}&wave=${encodeURIComponent(change.wave_id || "")}`;
    setDocView({ title: change.change_id, subtitle: change.title || "", url });
  }, []);

  const project    = snapshot.project    || {};
  const frameworkVersion = project.framework_version || project.framework_revision || "unknown";
  const waves      = snapshot.waves      || [];
  const allChanges = snapshot.changes?.in_waves || [];
  const agents     = snapshot.agents     || [];
  const handoffWaveId = snapshot.activity?.session_handoff_active_wave || "";

  const openOrClosedIds = new Set(
    waves.filter(w => waveStatus(w) === "active" || waveStatus(w) === "implementing" || waveStatus(w) === "closed" || waveStatus(w) === "completed").map(w => w.wave_id)
  );
  const activeWaveIds = new Set(activeWaves(waves).map(w => w.wave_id));
  const activeChanges = allChanges.filter(c => activeWaveIds.has(c.wave_id));
  const pendingChanges = [
    ...allChanges.filter(c => !openOrClosedIds.has(c.wave_id)),
    ...(snapshot.changes?.staged || []).filter(c => !openOrClosedIds.has(c.wave_id)),
  ];
  const scopeChanges = activeWaves(waves).length > 0
    ? activeChanges
    : pendingChanges;

  return h(React.Fragment, null,
    h(Header, { snapshot, dark, onToggleDark }),
    h("main", { className: "shell" },
      h("section", { className: "hero", "aria-label": "Project overview" },
        h("article", { className: "hero-card" },
          h("div", { className: "hero-meta" },
            h("span", { className: "meta-pill" }, `Repository: ${project.repo_basename || ""}`),
            h(GitPills, { git: snapshot.git }),
          ),
          h(Metrics, { snapshot, scopeChanges,
            onWavesClick:   () => setShowWaves(true),
            onChangesClick: () => setShowChanges(true),
            onAcsClick:     () => setShowAcs(true),
            onTasksClick:   () => setShowTasks(true),
            onFilesClick:   () => setShowAllFiles(true),
            onIndexClick:   () => setShowIndex(true),
          }),
          h(ProgressCard, { snapshot, scopeChanges }),
          h(FrameworkFlow, { onSelectProcess: setSelectedFrameworkProcess }),
          h(GraphPanel, { snapshot }),
          agents.length ? h(Agents, { agents, onSelectAgent: setSelectedAgent }) : null,
        ),
      ),

      h("section", { className: "content-grid", "aria-label": "Project details" },
        h("div", { className: "card-grid" },
          h(WavesCard, { waves, allChanges, handoffWaveId, onWaveClick: openWaveDoc, onChangeClick: openChangeDoc }),
          h(ChangesTable, { changes: [...pendingChanges].reverse(), title: p(pendingChanges.length, "Pending change", "Pending changes"), onChangeClick: openChangeDoc }),
        ),
        h("div", { className: "card-grid" },
          h("article", { className: "timeline-card", "aria-label": "Recent activity" },
            h("h2", { className: "panel-heading" }, "Recent changes"),
            h(Activity, { activity: snapshot.activity, onChangeClick: openChangeDoc }),
          ),
        ),
      ),

      h("footer", { className: "site-footer" },
        h("div", { className: "site-footer-left" },
          h("span", { className: "site-footer-brand" }, `Wavefoundry v${frameworkVersion}`),
          sseConnected
            ? h("span", { className: "sse-live", title: "Server-sent events connected — updates are pushed in real time" }, "Live")
            : h("span", { className: "site-footer-refresh" }, `Next refresh in ${POLL_STEPS[pollIdx] / 1000}s`),
        ),
        h("span", { className: "site-footer-updated" }, `Updated ${localDateTime(snapshot.generated_at)}`),
      ),
    ),
    selectedFrameworkProcess ? h(FrameworkProcessDialog, {
      process: selectedFrameworkProcess,
      onClose: () => setSelectedFrameworkProcess(null),
    }) : null,
    selectedAgent ? h(AgentDialog, { agent: selectedAgent, onClose: () => setSelectedAgent(null) }) : null,
    docView ? h(DocDialog, { title: docView.title, subtitle: docView.subtitle, fetchUrl: docView.url, onClose: () => setDocView(null) }) : null,
    showWaves   ? h(WavesDialog,   { snapshot, onClose: () => setShowWaves(false) })   : null,
    showChanges ? h(ChangesDialog, { snapshot, onClose: () => setShowChanges(false) }) : null,
    showAcs     ? h(AcsDialog,     { snapshot, onClose: () => setShowAcs(false) })     : null,
    showTasks   ? h(TasksDialog,   { snapshot, onClose: () => setShowTasks(false) })   : null,
    showIndex   ? h(IndexDialog,   { health: snapshot.health, onClose: () => setShowIndex(false) }) : null,
    showAllFiles ? h(FilesDialog,  { title: "Changed files", files: snapshot.activity?.files_changed_all || [], emptyMessage: "Working tree is clean.", onClose: () => setShowAllFiles(false) }) : null,
  );
}

function ErrorView({ message, projectName }) {
  return h("main", { className: "shell" },
    h("article", { className: "hero-card", style: { marginTop: "2rem" } },
      h("span", { className: "eyebrow" }, projectName || "Dashboard"),
      h("h1", { style: { fontFamily: "var(--font-heading)", margin: "1rem 0 0.5rem" } }, "Dashboard unavailable"),
      h("p", { className: "muted" }, message),
      h("p", { className: "muted" }, "Retrying in 5 seconds…"),
    ),
  );
}

// ── Root app ──────────────────────────────────────────────────────────────────

function App() {
  const [dark, onToggleDark] = useDarkMode();
  const [snapshot, setSnapshot]         = useState(null);
  const [error, setError]               = useState(null);
  const [sseConnected, setSseConnected] = useState(false);
  const pollIdxRef    = useRef(0);
  const lastHashRef   = useRef(null);
  const timerRef      = useRef(null);
  const sseActiveRef  = useRef(false);   // ref so refresh() can read it without re-creating
  const [pollIdx, setPollIdx] = useState(0);

  useEffect(() => {
    document.title = dashboardTitle(snapshot);
  }, [snapshot?.project?.repo_basename, snapshot?.project?.name, error]);

  const refresh = useCallback(async () => {
    try {
      const response = await fetch("/api/dashboard", { cache: "no-store" });
      if (!response.ok) throw new Error(`Dashboard request failed with ${response.status}`);
      const data = await response.json();
      const hash = _snapshotHash(data);
      if (hash !== lastHashRef.current) {
        pollIdxRef.current = 0;
        lastHashRef.current = hash;
      } else {
        pollIdxRef.current = Math.min(pollIdxRef.current + 1, POLL_STEPS.length - 1);
      }
      setPollIdx(pollIdxRef.current);
      setSnapshot(data);
      setError(null);
      // Only schedule the next poll when SSE is not connected.
      if (!sseActiveRef.current) {
        timerRef.current = window.setTimeout(refresh, POLL_STEPS[pollIdxRef.current]);
      }
    } catch (err) {
      setError(err.message || String(err));
      setSnapshot(null);
      timerRef.current = window.setTimeout(refresh, 5000);
    }
  }, []);

  // Initial fetch only — SSE takes over once connected; polling resumes if SSE drops.
  useEffect(() => {
    refresh();
    return () => { if (timerRef.current) window.clearTimeout(timerRef.current); };
  }, [refresh]);

  // SSE connection — server pushes updates; polling is suspended while connected.
  // esRef and reconnectTimerRef are refs so the cleanup always closes the *current*
  // active EventSource, even after reconnect cycles replace the original instance.
  const esRef = useRef(null);
  const reconnectTimerRef = useRef(null);

  useEffect(() => {
    let reconnectDelay = 2000;

    function connect() {
      const es = new EventSource("/api/events");
      esRef.current = es;

      es.addEventListener("update", () => {
        if (timerRef.current) { window.clearTimeout(timerRef.current); timerRef.current = null; }
        refresh();
      });
      es.onopen = () => {
        sseActiveRef.current = true;
        setSseConnected(true);
        reconnectDelay = 2000;
        // Cancel any in-flight poll timer — SSE is driving from here.
        if (timerRef.current) { window.clearTimeout(timerRef.current); timerRef.current = null; }
      };
      es.onerror = () => {
        sseActiveRef.current = false;
        setSseConnected(false);
        es.close();
        // Reset back-off so the first fallback poll is immediate rather than
        // whatever long interval SSE happened to interrupt.
        pollIdxRef.current = 0;
        if (!timerRef.current) {
          timerRef.current = window.setTimeout(refresh, POLL_STEPS[0]);
        }
        reconnectTimerRef.current = window.setTimeout(connect, reconnectDelay);
        reconnectDelay = Math.min(reconnectDelay * 2, 30000);
      };
    }

    connect();
    return () => {
      if (esRef.current) { esRef.current.close(); esRef.current = null; }
      if (reconnectTimerRef.current) { window.clearTimeout(reconnectTimerRef.current); reconnectTimerRef.current = null; }
    };
  }, [refresh]);

  const projectName = snapshot?.project?.name || null;
  if (error)     return h(ErrorView, { message: error, projectName });
  if (!snapshot) return h("main", { className: "shell" },
    h("article", { className: "hero-card", style: { marginTop: "2rem" } },
      h("span", { className: "eyebrow" }, "Dashboard"),
      h("p", { className: "muted", style: { marginTop: "1rem" } }, "Loading…"),
    ),
  );
  return h(Dashboard, { snapshot, pollIdx, sseConnected, dark, onToggleDark });
}

// ── Mount ─────────────────────────────────────────────────────────────────────

const root = ReactDOM.createRoot(document.getElementById("app"));
root.render(h(ErrorBoundary, null, h(App, null)));
