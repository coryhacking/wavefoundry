const { createElement: h, useState, useEffect, useRef, useCallback, Component } = React;

// ── Design-system primitives (WFDS) ───────────────────────────────────────────
// The reusable primitive layer lives in /ds/wfds.js, loaded as a no-build global
// before this file (see dashboard.html). The dashboard consumes the shared
// primitives from window.WFDS rather than re-declaring them inline (wave 1p75h /
// change 1p72v-ref). Local names below keep the dashboard's existing call sites
// working while the single source of truth is the WFDS module.
// window.WFDS is the full primitive library (Icon, ThemeToggle, Badge, Pill,
// Chip, ProgressBar, Sparkline, Card, Dialog, Table, FileTree, DiffView,
// EmptyState, SectionLabel, NavSidebar, Prose/Markdown — see ds/wfds.js and
// docs/design-system/components/). The dashboard destructures the subset it
// references directly; the rest are consumed through WFDS.* or via the thin
// delegators below (ProgressRow → WFDS.ProgressBar, Sidebar → WFDS.NavSidebar).
const WFDS = window.WFDS;
const {
  badgeClass,
  FileTree, buildFileTree, DiffView,
  renderInline, renderMarkdownish,
} = WFDS;
// DialogFrame / MiniGraph are the dashboard's historical names for the shared
// WFDS.Dialog / WFDS.Sparkline primitives.
const DialogFrame = WFDS.Dialog;
const MiniGraph = WFDS.Sparkline;

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
  // Wave 1rtju: `watcher` is a read-time liveness view (its last_cycle_age_seconds changes every
  // request) — exclude it, like generated_at, so it never produces a spurious content-change hash.
  const { generated_at: _ts, watcher: _w, ...rest } = snapshot;
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

// badgeClass / Badge now live in WFDS (see top-of-file destructure).

function computeProgress(changes) {
  const total = (changes || []).length;
  if (!total) return { done: 0, total: 0, pct: 0 };
  const done = changes.filter(c => isDone(c.status)).length;
  return { done, total, pct: Math.round((done / total) * 100) };
}

function waveStats(waveChanges) {
  // Wave 1p458 (1p45a): `[~]` deferred items stay in the denominator and read as outstanding
  // while the wave is open (this card renders active waves only). `tasks_total` and
  // `ac_priority_counts` include deferred; `tasks_completed` / `ac_completed_counts` are
  // `[x]`-only, so deferred items count toward the total but not toward done.
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
  // Wave 1p458 (1p45a): count every visible (non-`not-this-scope`) AC in the denominator,
  // including `[~]` deferred items. Deferred items have done=false, so while the wave is
  // open they read as outstanding; the closed-wave fold lives in ProgressCard.
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

// SunIcon / MoonIcon / ThemeToggle now live in WFDS (see top-of-file destructure).

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

// ProgressRow is the dashboard's name for the shared WFDS.ProgressBar primitive.
// The implementation lives in /ds/wfds.js; this thin delegator keeps the existing
// call sites (h(ProgressRow, …)) working with no inlined copy of the markup.
function ProgressRow({ label, done, total, variant }) {
  return h(WFDS.ProgressBar, { label, done, total, variant });
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

  // Wave 1p458 (1p45a): `[~]` deferred items stay IN the denominator. For a closed wave every
  // in-scope item (incl deferred) counts as done; for an open wave only `[x]`/done items
  // count, so deferred items read as outstanding until the wave is closed. The separate
  // "· N deferred" tally is gone (the per-item `~` detail marker is retained).
  const tasksTotal = allCountedChanges.reduce((s, c) => s + (Number(c.tasks_total) || 0), 0);
  const tasksDone  = allCountedChanges.reduce((s, c) =>
    s + (closedWaveIds.has(c.wave_id) ? (Number(c.tasks_total) || 0) : (Number(c.tasks_completed) || 0)), 0);

  const acTotal = allCountedChanges.reduce((s, c) => s + visibleAcItems(c).length, 0);
  const acDone  = allCountedChanges.reduce((s, c) => {
    const inScope = visibleAcItems(c);
    return s + (closedWaveIds.has(c.wave_id) ? inScope.length : inScope.filter(a => a.done).length);
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

// MiniGraph now lives in WFDS as Sparkline (see top-of-file alias).

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

// buildFileTree / FileTree now live in WFDS (see top-of-file destructure).

function DiffDialog({ filePath, onClose }) {
  const [diffText, setDiffText] = useState(null);
  useEffect(() => {
    fetch(`/api/diff?path=${encodeURIComponent(filePath)}`)
      .then(r => r.text())
      .then(text => setDiffText(text))
      .catch(() => setDiffText(""));
  }, [filePath]);

  const fileName = filePath.split("/").pop();
  return h(DialogFrame, {
    className: "diff-dialog",
    title: fileName,
    subtitle: filePath,
    onClose,
  }, h(DiffView, { text: diffText }));
}

// DialogFrame now lives in WFDS as Dialog (see top-of-file alias).

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
      // Wave 1p31b (1p32k): treat deferred items as "not pending" so they sort with done.
      const items = sortPendingFirst(visibleAcItems(c), ac => Boolean(ac.done) || Boolean(ac.deferred));
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
          items.map((ac, i) => {
            // Wave 1p31b (1p32k): render `[~]` deferred ACs with a distinct check icon (`~`)
            // and a `--deferred` modifier so operators see them as a third category rather
            // than falsely-pending or falsely-done.
            const stateMod = ac.deferred
              ? " metric-dialog-ac-item--deferred"
              : (ac.done ? " metric-dialog-ac-item--done" : "");
            const checkMod = ac.deferred
              ? " metric-dialog-ac-check--deferred"
              : (ac.done ? " metric-dialog-ac-check--done" : "");
            const checkGlyph = ac.deferred ? "~" : (ac.done ? "✓" : "○");
            // Wave 1p31b (1p32k): for deferred ACs, replace the priority badge with a
            // "deferred" label — the priority isn't load-bearing once the AC is set aside.
            const badge = ac.deferred
              ? h("span", { className: "status-badge status-deferred metric-dialog-ac-priority" }, "deferred")
              : (ac.priority && ac.priority !== "unknown"
                ? h("span", { className: `status-badge ${PRIORITY_BADGE[ac.priority] || "status-unknown"} metric-dialog-ac-priority` }, ac.priority)
                : null);
            return h("div", { key: i, className: `metric-dialog-ac-item${stateMod}` },
              h("span", { className: `metric-dialog-ac-check${checkMod}`, title: ac.deferred ? "Intentionally deferred" : null }, checkGlyph),
              h("span", { className: "metric-dialog-ac-text" }, renderInline(ac.text || "")),
              badge,
            );
          }),
        ),
      );
    }).filter(Boolean) : h("div", { className: "empty-state" }, scope === "active" ? "No active ACs." : "No pending ACs."),
  );
}

function TasksDialog({ snapshot, onClose }) {
  const { scope, changes } = dialogChangesForScope(snapshot);
  const cards = changes.map(c => {
    // Wave 1p31b (1p32k): treat deferred tasks as "not pending" so they sort with done.
    const items = sortPendingFirst(c.tasks_items || [], task => Boolean(task.done) || Boolean(task.deferred));
    if (!items.length) return null;
    return h("div", { key: c.change_id, className: "metric-dialog-card" },
      h("div", { className: "metric-dialog-card-header" },
        h("span", { className: "wave-change-id" }, c.change_id),
      ),
      h("div", { className: "metric-dialog-card-title" }, c.title),
      h("div", { className: "metric-dialog-ac-rows" },
        items.map((task, i) => {
          // Wave 1p31b (1p32k): same `[~]` distinct treatment for tasks as for ACs.
          const stateMod = task.deferred
            ? " metric-dialog-ac-item--deferred"
            : (task.done ? " metric-dialog-ac-item--done" : "");
          const checkMod = task.deferred
            ? " metric-dialog-ac-check--deferred"
            : (task.done ? " metric-dialog-ac-check--done" : "");
          const checkGlyph = task.deferred ? "~" : (task.done ? "✓" : "○");
          return h("div", { key: i, className: `metric-dialog-ac-item${stateMod}` },
            h("span", { className: `metric-dialog-ac-check${checkMod}`, title: task.deferred ? "Intentionally deferred" : null }, checkGlyph),
            h("span", { className: "metric-dialog-ac-text" }, renderInline(task.label || "")),
          );
        }),
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

// Wave 1p2q3 (131es): palette designed so every node kind is unambiguously
// distinct. Field feedback flagged two problems: (1) `variable` falling back
// to "external" grey and reading as `doc` charcoal, and (2) `doc` and
// `external` reading as "two greys" even at different lightness. Fixes:
//   - `seed` collapses into the `doc` bucket (seeds are markdown prompts —
//     semantically documents). Routed in `_graphKindBucket`, no separate entry.
//   - `external` lifted to a cool light blue-grey, distinct hue family from
//     `doc` charcoal so they no longer read as a grey pair.
//   - New `variable` slot uses vivid red — far from every other hue.
//   - `community`/`package`/`namespace` shifted off prior near-collision
//     zones (teal vs cyan-teal, purple vs deep purple).
const GRAPH_KIND_COLORS = {
  module: "#1976d2",     // blue
  class: "#6f42c1",      // purple
  function: "#53ac04",   // green
  doc: "#495057",        // charcoal — also the bucket for `seed` (see _graphKindBucket)
  community: "#16a085",  // emerald (shifted from teal so it parts from `package`)
  external: "#90a4ae",   // light blue-grey (shifted from neutral grey so it parts from `doc`)
  package: "#00acc1",    // bright cyan (shifted from teal so it parts from `community`)
  namespace: "#c2185b",  // magenta (shifted from deep purple so it parts from `class`)
  variable: "#d32f2f",   // vivid red — distinct from `doc` charcoal and every other hue
};

const GRAPH_COMMUNITY_PALETTE = [
  "#1976d2",
  "#6f42c1",
  "#0f766e",
  "#00897b",
  "#e65100",
  "#f57c00",
  "#ef6c00",
  "#ff9800",
  "#7b1fa2",
  "#4527a0",
  "#0288d1",
  "#29b6f6",
  "#ab47bc",
  "#26c6da",
  "#66bb6a",
  "#ad1457",
  "#5c6bc0",
  "#ffa726",
  "#9c27b0",
  "#00acc1",
];

const GRAPH_RELATION_COLORS = {
  defines: "#1976d2",
  imports: "#6f42c1",
  calls: "#53ac04",
  doc_references_code: "#ff9100",
  doc_references_doc: "#00897b",
};

const ALL_GRAPH_RELATIONS = ["calls", "imports", "defines", "doc_references_code", "doc_references_doc"];
/** Hover preview: brighten calls/imports edges only; defines stay faint but nodes still light up. */
const GRAPH_HOVER_HIGHLIGHT_RELATIONS = new Set(["calls", "imports"]);
/** Community overview bubbles: code dependencies only (no doc reference spokes). */
const GRAPH_COMMUNITY_OVERVIEW_RELATIONS = new Set(["calls", "imports", "defines"]);
const ALL_GRAPH_RELATIONS_SET = new Set(ALL_GRAPH_RELATIONS);
const GRAPH_MIN_COMMUNITY_NODES = 2;
const GRAPH_OVERVIEW_COMMUNITY_LIMIT = 24;
const GRAPH_COMMUNITY_DRILLDOWN_LIMIT = 50;
const GRAPH_OVERVIEW_SEED_LIMIT = 24;
/** Pre-assigned category communities from graph_cluster (never use as layout hub). */
const GRAPH_CATEGORY_COMMUNITY_LABELS = new Set([
  "Documentation", "Tests", "Benchmarks", "CI/CD",
  "Generated", "Scripts", "Configuration",
]);

function _hexToRgba(hex, alpha) {
  const value = String(hex || "").trim().replace(/^#/, "");
  if (value.length !== 6) return `rgba(0, 0, 0, ${alpha})`;
  const r = parseInt(value.slice(0, 2), 16);
  const g = parseInt(value.slice(2, 4), 16);
  const b = parseInt(value.slice(4, 6), 16);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

function _graphKindBucket(kind) {
  // Wave 1p2q3 (131es): `seed` is visually collapsed into the `doc` bucket —
  // seeds are markdown prompt files, semantically documents. Operators don't
  // need a separate hue to distinguish them.
  if (kind === "seed") return "doc";
  return GRAPH_KIND_COLORS[kind] ? kind : "external";
}

function _graphCommunityColor(communityId) {
  const id = String(communityId || "").trim();
  if (!id) return GRAPH_KIND_COLORS.external;
  const idx = Math.abs(_hashString(id)) % GRAPH_COMMUNITY_PALETTE.length;
  return GRAPH_COMMUNITY_PALETTE[idx];
}

function _shouldColorNodeByCommunity(node, { hasCommunityOverview, selectedClusterId, viewMode }) {
  if (node?.kind === "community") return true;
  if (hasCommunityOverview) return true;
  return viewMode === "overview" && !selectedClusterId && Boolean(node?.community_id);
}

function _graphNodeFillColor(node, colorContext) {
  if (_shouldColorNodeByCommunity(node, colorContext) && node?.community_id) {
    return _graphCommunityColor(node.community_id);
  }
  return GRAPH_KIND_COLORS[_graphKindBucket(node?.kind)];
}

function _graphLabel(node) {
  return String(node?.label || node?.id || "").trim();
}

const GRAPH_LABEL_MAX_CHARS_PER_LINE = 18;
const GRAPH_LABEL_MAX_LINES = 3;
const GRAPH_LABEL_LINE_HEIGHT = 14;
const GRAPH_LABEL_BASELINE_OFFSET = 12;
const GRAPH_LAYOUT_MAX_NODE_RADIUS = 21;
const GRAPH_LAYOUT_COMMUNITY_MAX_NODE_RADIUS = 28;

/** Label block below a node circle: max lines plus one blank line. */
function _graphLayoutLabelPadBelowCircle() {
  return GRAPH_LABEL_BASELINE_OFFSET
    + GRAPH_LABEL_MAX_LINES * GRAPH_LABEL_LINE_HEIGHT
    + GRAPH_LABEL_LINE_HEIGHT;
}

/** Center-to-center vertical stride between hierarchical graph rows. */
function _graphLayoutSubRowGap(maxNodeRadius = GRAPH_LAYOUT_MAX_NODE_RADIUS) {
  return 2 * maxNodeRadius + _graphLayoutLabelPadBelowCircle();
}

/** Layered (horizontal-band) rows: typical node size, three label lines, no extra blank line. */
function _graphLayoutHierarchicalRowGap(shallow = false) {
  const radius = shallow ? 16 : 14;
  const labelPad = GRAPH_LABEL_BASELINE_OFFSET + GRAPH_LABEL_MAX_LINES * GRAPH_LABEL_LINE_HEIGHT;
  return 2 * radius + labelPad;
}

/** Angular spacing along one radial ring (node circle + label block). */
function _graphLayoutRadialAngularSlot(avgNodeRadius, densityBonus = 0) {
  return 2 * avgNodeRadius + _graphLayoutLabelPadBelowCircle() + densityBonus;
}

/** Radial gap between concentric rings — tighter than full center-to-center stride. */
function _graphLayoutRadialHopGap(angularSlot) {
  return Math.max(angularSlot * 0.55, 48);
}

function _graphLabelParts(label) {
  const text = String(label || "").trim();
  if (!text) return [""];
  const tokens = text.split(/[\s._\-/\\:]+/).filter(Boolean);
  if (!tokens.length) return [text.slice(0, GRAPH_LABEL_MAX_CHARS_PER_LINE)];
  const lines = [];
  let current = "";
  let truncated = false;
  const pushLine = (line) => {
    if (!line || lines.length >= GRAPH_LABEL_MAX_LINES) return false;
    lines.push(line);
    return lines.length >= GRAPH_LABEL_MAX_LINES;
  };
  const pushLongToken = (token) => {
    for (let index = 0; index < token.length; index += GRAPH_LABEL_MAX_CHARS_PER_LINE) {
      if (pushLine(token.slice(index, index + GRAPH_LABEL_MAX_CHARS_PER_LINE))) return true;
    }
    return false;
  };
  for (const token of tokens) {
    const candidate = current ? `${current} ${token}` : token;
    if (candidate.length <= GRAPH_LABEL_MAX_CHARS_PER_LINE) {
      current = candidate;
      continue;
    }
    if (current && pushLine(current)) {
      truncated = true;
      break;
    }
    current = "";
    if (token.length > GRAPH_LABEL_MAX_CHARS_PER_LINE) {
      if (pushLongToken(token)) {
        truncated = true;
        break;
      }
      continue;
    }
    current = token;
  }
  if (!truncated && current) pushLine(current);
  else if (current) truncated = true;
  if (!lines.length) lines.push(text.slice(0, GRAPH_LABEL_MAX_CHARS_PER_LINE));
  if (truncated && lines.length) {
    const lastIndex = lines.length - 1;
    const last = lines[lastIndex];
    lines[lastIndex] = last.length >= GRAPH_LABEL_MAX_CHARS_PER_LINE
      ? `${last.slice(0, GRAPH_LABEL_MAX_CHARS_PER_LINE - 1)}…`
      : `${last}…`;
  }
  return lines;
}

function _graphLabelMetrics(label) {
  const lines = _graphLabelParts(label);
  const maxLineChars = Math.max(...lines.map(line => line.length), 1);
  return { lines, lineCount: lines.length, maxLineChars };
}

function _graphRenderNodeLabel(node, radius) {
  const { lines } = _graphLabelMetrics(_graphLabel(node));
  const startY = radius + GRAPH_LABEL_BASELINE_OFFSET;
  return h(
    "text",
    { className: "graph-node-label", textAnchor: "middle" },
    lines.map((line, index) =>
      h("tspan", {
        key: `${index}-${line}`,
        x: 0,
        y: index === 0 ? startY : undefined,
        dy: index === 0 ? 0 : GRAPH_LABEL_LINE_HEIGHT,
      }, line)
    ),
  );
}

const GRAPH_COMMUNITY_FOCUS_KIND_ORDER = ["module", "class", "function"];
const GRAPH_COMMUNITY_OVERVIEW_FOCUS_KIND_ORDER = ["module", "class", "function", "doc", "seed"];
const GRAPH_NEIGHBOR_KIND_ORDER = ["module", "class", "function", "doc", "seed", "external"];
const GRAPH_KIND_LAYER_ORDER = ["module", "class", "function", "external", "doc", "seed"];
const GRAPH_KIND_LAYER_ORDER_DOC_FOCUS = ["doc", "seed", "module", "class", "function", "external"];

function _graphKindLayerIndex(node, layerOrder = GRAPH_KIND_LAYER_ORDER) {
  const kind = _graphKindBucket(node?.kind);
  const idx = layerOrder.indexOf(kind);
  return idx >= 0 ? idx : layerOrder.indexOf("external");
}

function _graphLayoutOptions(focusNodeId, nodeById) {
  const selectionId = focusNodeId ? String(focusNodeId) : "";
  const selected = selectionId ? nodeById.get(selectionId) : null;
  const docFocus = Boolean(selected && _graphIsDocumentationKind(selected));
  let layoutFocusId = selectionId;
  let moduleFocus = false;
  if (selected && !docFocus) {
    if (_graphKindBucket(selected.kind) === "module") {
      moduleFocus = true;
      layoutFocusId = selectionId;
    } else {
      const moduleId = String(selected.source_file || "").split("::")[0];
      const moduleNode = moduleId ? nodeById.get(moduleId) : null;
      if (moduleNode && _graphKindBucket(moduleNode.kind) === "module") {
        moduleFocus = true;
        layoutFocusId = moduleId;
      }
    }
  }
  return {
    layerOrder: docFocus ? GRAPH_KIND_LAYER_ORDER_DOC_FOCUS : GRAPH_KIND_LAYER_ORDER,
    focusNodeId: layoutFocusId,
    selectionNodeId: selectionId,
    docFocus,
    moduleFocus,
  };
}

function _graphSortBandNodeIds(ids, nodeById, subLayers, focusNodeId) {
  return ids.slice().sort((a, b) => {
    if (focusNodeId && focusNodeId === a) return -1;
    if (focusNodeId && focusNodeId === b) return 1;
    const layerDelta = (subLayers.get(a) || 0) - (subLayers.get(b) || 0);
    if (layerDelta) return layerDelta;
    return _graphCompareNodesByFileAndLabel(nodeById.get(a), nodeById.get(b));
  });
}

function _graphIsDocumentationKind(node) {
  const kind = _graphKindBucket(node?.kind);
  return kind === "doc" || kind === "seed";
}

/** Doc focus: keep EXTRACTED doc links; drop noisy AMBIGUOUS keyword matches. */
function _graphFilterDocFocusNeighborhood(data, focusNodeId) {
  if (!data?.present || !focusNodeId) return data;
  const focusNode = (data.nodes || []).find(node => node.id === focusNodeId);
  if (!focusNode || !_graphIsDocumentationKind(focusNode)) return data;
  const edges = (data.edges || []).filter(edge =>
    edge.relation !== "doc_references_code" || edge.confidence === "EXTRACTED"
  );
  const nodeIds = new Set([focusNodeId]);
  for (const edge of edges) {
    nodeIds.add(edge.source);
    nodeIds.add(edge.target);
  }
  const nodes = (data.nodes || []).filter(node => nodeIds.has(node.id));
  return { ...data, nodes, edges };
}

function _graphCompareNodesByFileAndLabel(nodeA, nodeB) {
  const fileA = String(nodeA?.source_file || nodeA?.id || "").split("::")[0];
  const fileB = String(nodeB?.source_file || nodeB?.id || "").split("::")[0];
  return fileA.localeCompare(fileB)
    || String(_graphLabel(nodeA)).localeCompare(String(_graphLabel(nodeB)));
}

const GRAPH_KIND_LAYOUT_RELATIONS = new Set(["calls", "imports", "defines", "doc_references_code"]);
/** At most one linked neighbor on each side of a focused node to keep edge lines readable. */
const GRAPH_FOCUS_MAX_SIDE_NEIGHBORS = 1;
const GRAPH_KIND_LAYOUT_MAX_ROW_NODES = 8;
const GRAPH_KIND_LAYOUT_SHALLOW_MAX_ROW_NODES = 5;
const GRAPH_KIND_LAYOUT_SUBGRAPH_GAP = 56;
const GRAPH_KIND_LAYOUT_MIN_CELL_WIDTH = 80;
const GRAPH_KIND_LAYOUT_SHALLOW_CELL_WIDTH = 108;
const GRAPH_KIND_LAYOUT_SHALLOW_ROW_GAP = 28;

function _graphSortNodeIds(ids, nodeById) {
  return ids.slice().sort((a, b) =>
    _graphCompareNodesByFileAndLabel(nodeById.get(a), nodeById.get(b))
  );
}

/** Neighbors with a direct edge to the focus node for the given relation. */
function _graphFocusLinkedNeighborSet(focusId, neighborIds, edges, relation) {
  const neighborSet = new Set(neighborIds);
  const linked = new Set();
  for (const edge of edges) {
    const rel = String(edge.relation || "");
    if (rel !== relation) continue;
    if (edge.source === focusId && neighborSet.has(edge.target)) linked.add(edge.target);
    if (edge.target === focusId && neighborSet.has(edge.source)) linked.add(edge.source);
  }
  return linked;
}

/** Pick at most one left and one right linked neighbor; balance same-direction links across both slots. */
function _graphFocusSideNeighbors(focusId, neighborIds, edges, relation, nodeById) {
  const linkedSet = _graphFocusLinkedNeighborSet(focusId, neighborIds, edges, relation);
  const linkedNeighbors = neighborIds.filter(id => linkedSet.has(id));
  const unlinked = _graphSortNodeIds(neighborIds.filter(id => !linkedSet.has(id)), nodeById);
  const leftIds = [];
  const rightIds = [];
  for (const edge of edges) {
    const rel = String(edge.relation || "");
    if (rel !== relation) continue;
    if (edge.source === focusId && linkedSet.has(edge.target)) {
      rightIds.push(edge.target);
    } else if (edge.target === focusId && linkedSet.has(edge.source)) {
      leftIds.push(edge.source);
    }
  }
  const sortedLeft = _graphSortNodeIds(leftIds, nodeById);
  const sortedRight = _graphSortNodeIds(rightIds, nodeById);
  let left = sortedLeft.slice(0, GRAPH_FOCUS_MAX_SIDE_NEIGHBORS);
  let right = sortedRight.slice(0, GRAPH_FOCUS_MAX_SIDE_NEIGHBORS);
  // Imports/doc links often share one direction — fill both side slots before rows below.
  if (!left.length && sortedRight.length > 1) {
    right = sortedRight.slice(0, 1);
    left = sortedRight.slice(1, 2);
  } else if (!right.length && sortedLeft.length > 1) {
    left = sortedLeft.slice(0, 1);
    right = sortedLeft.slice(1, 2);
  }
  const used = new Set([...left, ...right]);
  const linkedRemainder = _graphSortNodeIds(
    linkedNeighbors.filter(id => !used.has(id)),
    nodeById,
  );
  return { left, right, linkedRemainder, unlinked };
}

function _graphAppendFocusBandRowSpecs(
  rowSpecs,
  {
    focusId,
    neighborIds,
    edges,
    sideRelation,
    nodeById,
    shallow,
    subRowGap,
    yCursor,
    rowInBand,
    rowGap,
    layoutWidth,
  },
) {
  const { left, right, linkedRemainder, unlinked } = _graphFocusSideNeighbors(
    focusId,
    neighborIds,
    edges,
    sideRelation,
    nodeById,
  );
  const focusRowIds = [...left, focusId, ...right];
  rowSpecs.push({
    rowIds: focusRowIds,
    hGap: shallow ? GRAPH_KIND_LAYOUT_SHALLOW_CELL_WIDTH : GRAPH_KIND_LAYOUT_MIN_CELL_WIDTH,
    y: yCursor + rowInBand * subRowGap,
    variableWidth: focusRowIds.length > 1,
    rowGap,
  });
  rowInBand += 1;
  const wrapOpts = { variableWidth: true };
  if (linkedRemainder.length) {
    rowInBand = _graphAppendWrappedRowSpecs(rowSpecs, linkedRemainder, {
      nodeById,
      shallow,
      layoutWidth,
      rowGap,
      subRowGap,
      yCursor,
      rowInBand,
      ...wrapOpts,
    });
  }
  rowInBand = _graphAppendWrappedRowSpecs(rowSpecs, unlinked, {
    nodeById,
    shallow,
    layoutWidth,
    rowGap,
    subRowGap,
    yCursor,
    rowInBand,
    ...wrapOpts,
  });
  return rowInBand;
}

function _graphModuleFileKey(node) {
  return String(node?.source_file || node?.id || "").split("::")[0];
}

function _graphWrapIds(ids, maxPerRow) {
  const limit = Math.max(1, maxPerRow);
  const rows = [];
  for (let index = 0; index < ids.length; index += limit) {
    rows.push(ids.slice(index, index + limit));
  }
  return rows.length ? rows : [[]];
}

function _graphNodeLayoutCellWidth(node, shallow = false) {
  const { maxLineChars } = _graphLabelMetrics(_graphLabel(node));
  const floor = shallow ? GRAPH_KIND_LAYOUT_SHALLOW_CELL_WIDTH : GRAPH_KIND_LAYOUT_MIN_CELL_WIDTH;
  return Math.min(240, Math.max(floor, maxLineChars * 6.4 + 24));
}

function _graphWrapIdsByWidth(ids, nodeById, maxRowWidth, gap, shallow = false) {
  const rows = [];
  let currentRow = [];
  let rowWidth = 0;
  for (const id of ids) {
    const cellWidth = _graphNodeLayoutCellWidth(nodeById.get(id), shallow);
    const nextWidth = rowWidth + (currentRow.length ? gap : 0) + cellWidth;
    if (currentRow.length && nextWidth > maxRowWidth) {
      rows.push(currentRow);
      currentRow = [];
      rowWidth = 0;
    }
    if (currentRow.length) rowWidth += gap;
    rowWidth += cellWidth;
    currentRow.push(id);
  }
  if (currentRow.length) rows.push(currentRow);
  return rows.length ? rows : [[]];
}

/** Order row ids from center outward (+1, -1, +2, -2, …) so rows balance under a focus node. */
function _graphCenterOutRowOrder(ids, flip = false) {
  if (ids.length <= 1) return ids.slice();
  const slotById = new Map();
  let leftDepth = 0;
  let rightDepth = 0;
  ids.forEach((id, index) => {
    const pickRight = flip ? index % 2 !== 0 : index % 2 === 0;
    if (pickRight) {
      rightDepth += 1;
      slotById.set(id, rightDepth);
    } else {
      leftDepth += 1;
      slotById.set(id, -leftDepth);
    }
  });
  return ids.slice().sort((a, b) => slotById.get(a) - slotById.get(b));
}

function _graphWrapIdsByWidthCenterOut(ids, nodeById, maxRowWidth, gap, shallow = false) {
  const rows = [];
  let currentRow = [];
  let rowFlip = false;
  for (const id of ids) {
    const trial = _graphCenterOutRowOrder([...currentRow, id], rowFlip);
    const trialWidth = _graphRowTotalWidth(trial, nodeById, gap, shallow);
    if (currentRow.length && trialWidth > maxRowWidth) {
      rows.push(_graphCenterOutRowOrder(currentRow, rowFlip));
      rowFlip = !rowFlip;
      currentRow = [id];
    } else {
      currentRow.push(id);
    }
  }
  if (currentRow.length) rows.push(_graphCenterOutRowOrder(currentRow, rowFlip));
  return rows.length ? rows : [[]];
}

function _graphLayoutMaxRowWidth(layoutWidth) {
  return Math.max(320, layoutWidth - 88);
}

function _graphAppendWrappedRowSpecs(rowSpecs, ids, {
  nodeById,
  shallow,
  layoutWidth,
  rowGap,
  subRowGap,
  yCursor,
  rowInBand,
  variableWidth = false,
}) {
  if (!ids.length) return rowInBand;
  const useVariableWidth = variableWidth;
  const wrappedRows = _graphWrapIdsByWidthCenterOut(
    ids,
    nodeById,
    _graphLayoutMaxRowWidth(layoutWidth),
    rowGap,
    useVariableWidth || shallow,
  );
  for (const rowIds of wrappedRows) {
    rowSpecs.push({
      rowIds,
      hGap: useVariableWidth || shallow
        ? GRAPH_KIND_LAYOUT_SHALLOW_CELL_WIDTH
        : Math.max(GRAPH_KIND_LAYOUT_MIN_CELL_WIDTH, 96 / Math.max(1, rowIds.length)),
      y: yCursor + rowInBand * subRowGap,
      variableWidth: useVariableWidth || shallow,
      rowGap,
    });
    rowInBand += 1;
  }
  return rowInBand;
}

function _graphRowTotalWidth(rowIds, nodeById, gap, shallow = false) {
  if (!rowIds.length) return 0;
  let total = 0;
  rowIds.forEach((id, index) => {
    total += _graphNodeLayoutCellWidth(nodeById.get(id), shallow);
    if (index) total += gap;
  });
  return total;
}

function _graphGroupMaxLayoutDepth(nodeIds, edges, nodeById, layoutOpts) {
  layoutOpts = layoutOpts || _graphLayoutOptions("", nodeById);
  const byKindBand = new Map();
  for (const id of nodeIds) {
    const node = nodeById.get(id);
    if (!node) continue;
    const band = _graphKindLayerIndex(node, layoutOpts.layerOrder);
    if (!byKindBand.has(band)) byKindBand.set(band, []);
    byKindBand.get(band).push(id);
  }
  let maxDepth = 0;
  for (const bandNodeIds of byKindBand.values()) {
    const subLayers = _graphWithinBandSubLayers(bandNodeIds, edges, nodeById, layoutOpts);
    for (const depth of subLayers.values()) maxDepth = Math.max(maxDepth, depth);
  }
  return maxDepth;
}

function _graphIsShallowFanOut(nodeIds, edges, nodeById, layoutOpts) {
  if (!nodeIds.length) return false;
  layoutOpts = layoutOpts || _graphLayoutOptions("", nodeById);
  if (!_graphBandHasLayoutEdges(nodeIds, edges, nodeById, layoutOpts)) return true;
  return _graphGroupMaxLayoutDepth(nodeIds, edges, nodeById, layoutOpts) <= 1;
}

function _graphCenterLayoutExpanded(positions, minWidth, minHeight, padding = 44) {
  if (!positions.size) return { positions, viewWidth: minWidth, viewHeight: minHeight };
  const bounds = _graphPositionsBounds(positions, padding);
  const viewWidth = Math.max(minWidth, bounds.width);
  const viewHeight = Math.max(minHeight, bounds.height);
  const midX = (bounds.minX + bounds.maxX) / 2;
  const midY = (bounds.minY + bounds.maxY) / 2;
  const centered = new Map();
  for (const [id, pos] of positions.entries()) {
    centered.set(id, {
      x: viewWidth / 2 + pos.x - midX,
      y: viewHeight / 2 + pos.y - midY,
    });
  }
  return { positions: centered, viewWidth, viewHeight };
}

function _graphViewBoxFromLayout(positions, defaultWidth, defaultHeight, padding = 56) {
  if (!positions.size) return { width: defaultWidth, height: defaultHeight };
  const maxNodeRadius = Math.max(GRAPH_LAYOUT_MAX_NODE_RADIUS, GRAPH_LAYOUT_COMMUNITY_MAX_NODE_RADIUS);
  const labelPadBelow = maxNodeRadius + _graphLayoutLabelPadBelowCircle();
  const bounds = _graphPositionsBounds(positions, padding);
  return {
    width: Math.max(defaultWidth, Math.ceil(bounds.maxX + padding / 2 + maxNodeRadius)),
    height: Math.max(defaultHeight, Math.ceil(bounds.maxY + padding / 2 + labelPadBelow)),
  };
}

function _graphPositionsBounds(positions, padding = 24) {
  let minX = Infinity;
  let minY = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;
  for (const pos of positions.values()) {
    minX = Math.min(minX, pos.x);
    minY = Math.min(minY, pos.y);
    maxX = Math.max(maxX, pos.x);
    maxY = Math.max(maxY, pos.y);
  }
  if (!Number.isFinite(minX)) {
    return { minX: 0, minY: 0, maxX: padding * 2, maxY: padding * 2, width: padding * 2, height: padding * 2 };
  }
  return {
    minX,
    minY,
    maxX,
    maxY,
    width: Math.max(padding * 2, maxX - minX + padding * 2),
    height: Math.max(padding * 2, maxY - minY + padding * 2),
  };
}

/** Group nodes into module-rooted mini-graphs for separated layout regions. */
function _graphModuleSubgraphs(nodes, edges) {
  const nodeById = new Map(nodes.map(node => [node.id, node]));
  const modules = nodes.filter(node => _graphKindBucket(node.kind) === "module");
  if (!modules.length) {
    return [{ key: "all", nodeIds: nodes.map(node => node.id) }];
  }

  const groupNodeIds = new Map(modules.map(mod => [mod.id, new Set([mod.id])]));
  const nodeGroup = new Map(modules.map(mod => [mod.id, mod.id]));
  const moduleIdSet = new Set(modules.map(mod => mod.id));

  for (const node of nodes) {
    if (_graphKindBucket(node.kind) === "module") continue;
    const fileKey = _graphModuleFileKey(node);
    let groupKey = moduleIdSet.has(fileKey) ? fileKey : "";
    if (!groupKey) {
      for (const modId of moduleIdSet) {
        if (fileKey === modId || fileKey.endsWith(`/${modId}`) || modId.endsWith(fileKey)) {
          groupKey = modId;
          break;
        }
      }
    }
    if (!groupKey) continue;
    if (!groupNodeIds.has(groupKey)) groupNodeIds.set(groupKey, new Set());
    groupNodeIds.get(groupKey).add(node.id);
    nodeGroup.set(node.id, groupKey);
  }

  for (const edge of edges) {
    if (String(edge.relation || "") !== "defines") continue;
    const source = nodeById.get(edge.source);
    if (!source || _graphKindBucket(source.kind) !== "module") continue;
    const groupKey = source.id;
    if (!groupNodeIds.has(groupKey)) groupNodeIds.set(groupKey, new Set([groupKey]));
    groupNodeIds.get(groupKey).add(edge.target);
    nodeGroup.set(edge.target, groupKey);
  }

  for (const node of nodes) {
    if (nodeGroup.has(node.id)) continue;
    for (const edge of edges) {
      if (edge.target !== node.id) continue;
      const sourceGroup = nodeGroup.get(edge.source);
      if (!sourceGroup) continue;
      groupNodeIds.get(sourceGroup).add(node.id);
      nodeGroup.set(node.id, sourceGroup);
      break;
    }
  }

  const unassigned = nodes.filter(node => !nodeGroup.has(node.id)).map(node => node.id);
  if (unassigned.length) {
    const idSet = new Set(unassigned);
    const adjacency = new Map(unassigned.map(id => [id, new Set()]));
    for (const edge of edges) {
      if (!idSet.has(edge.source) || !idSet.has(edge.target)) continue;
      adjacency.get(edge.source).add(edge.target);
      adjacency.get(edge.target).add(edge.source);
    }
    const visited = new Set();
    for (const startId of unassigned) {
      if (visited.has(startId)) continue;
      const component = [];
      const queue = [startId];
      visited.add(startId);
      while (queue.length) {
        const current = queue.shift();
        component.push(current);
        for (const nextId of adjacency.get(current) || []) {
          if (visited.has(nextId)) continue;
          visited.add(nextId);
          queue.push(nextId);
        }
      }
      const key = component.length === 1 ? component[0] : `shared:${component[0]}`;
      groupNodeIds.set(key, new Set(component));
      for (const id of component) nodeGroup.set(id, key);
    }
  }

  let mergedImports = true;
  while (mergedImports) {
    mergedImports = false;
    for (const edge of edges) {
      if (String(edge.relation || "") !== "imports") continue;
      const sourceGroup = nodeGroup.get(edge.source);
      const targetGroup = nodeGroup.get(edge.target);
      if (!sourceGroup || !targetGroup || sourceGroup === targetGroup) continue;
      const targetMembers = groupNodeIds.get(targetGroup);
      if (!targetMembers?.size) continue;
      const moduleOnly = [...targetMembers].every(id => {
        const node = nodeById.get(id);
        return node && _graphKindBucket(node.kind) === "module";
      });
      if (!moduleOnly) continue;
      const sourceMembers = groupNodeIds.get(sourceGroup);
      if (!sourceMembers) continue;
      for (const id of targetMembers) {
        sourceMembers.add(id);
        nodeGroup.set(id, sourceGroup);
      }
      groupNodeIds.delete(targetGroup);
      mergedImports = true;
    }
  }

  return [...groupNodeIds.entries()]
    .map(([key, idSet]) => ({
      key,
      nodeIds: [...idSet],
      moduleLabel: _graphLabel(nodeById.get(key) || { id: key }),
    }))
    .filter(group => group.nodeIds.length)
    .sort((a, b) => b.nodeIds.length - a.nodeIds.length
      || String(a.moduleLabel).localeCompare(String(b.moduleLabel)));
}

/** Sub-rows inside one kind band from within-band and incoming cross-band dependency edges. */
function _graphWithinBandSubLayers(nodeIds, edges, nodeById, layoutOpts) {
  layoutOpts = layoutOpts || _graphLayoutOptions("", nodeById);
  const idSet = new Set(nodeIds);
  const subLayer = new Map(nodeIds.map(id => [id, 0]));
  const bandEdges = [];
  for (const edge of edges) {
    const relation = String(edge.relation || "");
    if (!GRAPH_KIND_LAYOUT_RELATIONS.has(relation)) continue;
    const sourceIn = idSet.has(edge.source);
    const targetIn = idSet.has(edge.target);
    if (sourceIn && targetIn) {
      bandEdges.push(edge);
      continue;
    }
    if (!targetIn || sourceIn || !nodeById) continue;
    const sourceNode = nodeById.get(edge.source);
    const targetNode = nodeById.get(edge.target);
    if (!sourceNode || !targetNode) continue;
    if (_graphKindLayerIndex(sourceNode, layoutOpts.layerOrder) < _graphKindLayerIndex(targetNode, layoutOpts.layerOrder)) {
      bandEdges.push(edge);
    }
  }
  if (!bandEdges.length) return subLayer;

  let changed = true;
  let iterations = 0;
  const maxIterations = Math.max(12, nodeIds.length * 2);
  while (changed && iterations < maxIterations) {
    changed = false;
    iterations += 1;
    for (const edge of bandEdges) {
      const sourceDepth = idSet.has(edge.source) ? (subLayer.get(edge.source) || 0) : 0;
      const next = sourceDepth + 1;
      if (next > (subLayer.get(edge.target) || 0)) {
        subLayer.set(edge.target, next);
        changed = true;
      }
    }
  }
  if (layoutOpts.focusNodeId && idSet.has(layoutOpts.focusNodeId)) {
    if (layoutOpts.docFocus || layoutOpts.moduleFocus) {
      subLayer.set(layoutOpts.focusNodeId, 0);
    }
  }
  return subLayer;
}

function _graphBandStacksNodesVertically(bandIdx, layerOrder = GRAPH_KIND_LAYER_ORDER) {
  const kind = layerOrder[bandIdx] || "";
  return kind === "module" || kind === "external" || kind === "doc" || kind === "seed";
}

function _graphBandHasLayoutEdges(bandNodeIds, edges, nodeById, layoutOpts) {
  layoutOpts = layoutOpts || _graphLayoutOptions("", nodeById);
  const idSet = new Set(bandNodeIds);
  for (const edge of edges) {
    const relation = String(edge.relation || "");
    if (!GRAPH_KIND_LAYOUT_RELATIONS.has(relation)) continue;
    const sourceIn = idSet.has(edge.source);
    const targetIn = idSet.has(edge.target);
    if (sourceIn && targetIn) return true;
    if (!targetIn || sourceIn || !nodeById) continue;
    const sourceNode = nodeById.get(edge.source);
    const targetNode = nodeById.get(edge.target);
    if (!sourceNode || !targetNode) continue;
    if (_graphKindLayerIndex(sourceNode, layoutOpts.layerOrder) < _graphKindLayerIndex(targetNode, layoutOpts.layerOrder)) {
      return true;
    }
  }
  return false;
}

function _layoutGraphKindLayersGroup(nodeIds, edges, nodeById, layoutWidth = 1040, layoutOpts) {
  layoutOpts = layoutOpts || _graphLayoutOptions("", nodeById);
  const shallow = _graphIsShallowFanOut(nodeIds, edges, nodeById, layoutOpts);
  const subRowGap = _graphLayoutHierarchicalRowGap(shallow);
  const rowGap = shallow ? GRAPH_KIND_LAYOUT_SHALLOW_ROW_GAP : 12;
  const focusWrap = layoutOpts.moduleFocus || layoutOpts.docFocus;
  const positions = new Map();
  const rowSpecs = [];
  let yCursor = 0;
  const byKindBand = new Map();

  for (const id of nodeIds) {
    const node = nodeById.get(id);
    if (!node) continue;
    const band = _graphKindLayerIndex(node, layoutOpts.layerOrder);
    if (!byKindBand.has(band)) byKindBand.set(band, []);
    byKindBand.get(band).push(id);
  }

  for (const bandIdx of [...byKindBand.keys()].sort((a, b) => a - b)) {
    const bandNodeIds = byKindBand.get(bandIdx);
    const subLayers = _graphWithinBandSubLayers(bandNodeIds, edges, nodeById, layoutOpts);
    let rowInBand = 0;
    const bandKind = layoutOpts.layerOrder[bandIdx] || "";
    const focusSort = layoutOpts.focusNodeId
      && bandNodeIds.includes(layoutOpts.focusNodeId)
      && (
        (layoutOpts.docFocus && (bandKind === "doc" || bandKind === "seed"))
        || (layoutOpts.moduleFocus && bandKind === "module")
      );

    if (layoutOpts.docFocus && (bandKind === "doc" || bandKind === "seed") && bandNodeIds.includes(layoutOpts.focusNodeId)) {
      rowInBand = _graphAppendFocusBandRowSpecs(rowSpecs, {
        focusId: layoutOpts.focusNodeId,
        neighborIds: bandNodeIds.filter(id => id !== layoutOpts.focusNodeId),
        edges,
        sideRelation: "doc_references_doc",
        nodeById,
        shallow,
        subRowGap,
        yCursor,
        rowInBand,
        rowGap,
        layoutWidth,
      });
    } else if (layoutOpts.docFocus && bandKind === "module" && bandNodeIds.length) {
      rowInBand = _graphAppendWrappedRowSpecs(rowSpecs, _graphSortNodeIds(bandNodeIds, nodeById), {
        nodeById,
        shallow,
        layoutWidth,
        rowGap,
        subRowGap,
        yCursor,
        rowInBand,
        variableWidth: true,
      });
    } else if (layoutOpts.moduleFocus && bandKind === "module" && bandNodeIds.includes(layoutOpts.focusNodeId)) {
      rowInBand = _graphAppendFocusBandRowSpecs(rowSpecs, {
        focusId: layoutOpts.focusNodeId,
        neighborIds: bandNodeIds.filter(id => id !== layoutOpts.focusNodeId),
        edges,
        sideRelation: "imports",
        nodeById,
        shallow,
        subRowGap,
        yCursor,
        rowInBand,
        rowGap,
        layoutWidth,
      });
    } else if (layoutOpts.moduleFocus && bandKind === "external" && bandNodeIds.length) {
      rowInBand = _graphAppendWrappedRowSpecs(rowSpecs, _graphSortNodeIds(bandNodeIds, nodeById), {
        nodeById,
        shallow,
        layoutWidth,
        rowGap,
        subRowGap,
        yCursor,
        rowInBand,
        variableWidth: true,
      });
    } else if (_graphBandStacksNodesVertically(bandIdx, layoutOpts.layerOrder)
      && _graphBandHasLayoutEdges(bandNodeIds, edges, nodeById, layoutOpts)
      && !layoutOpts.moduleFocus) {
      const sortedIds = focusSort
        ? _graphSortBandNodeIds(bandNodeIds, nodeById, subLayers, layoutOpts.focusNodeId)
        : bandNodeIds.slice().sort((a, b) => {
          const layerDelta = (subLayers.get(a) || 0) - (subLayers.get(b) || 0);
          if (layerDelta) return layerDelta;
          return _graphCompareNodesByFileAndLabel(nodeById.get(a), nodeById.get(b));
        });
      for (const id of sortedIds) {
        rowSpecs.push({
          rowIds: [id],
          hGap: shallow ? GRAPH_KIND_LAYOUT_SHALLOW_CELL_WIDTH : GRAPH_KIND_LAYOUT_MIN_CELL_WIDTH,
          y: yCursor + rowInBand * subRowGap,
          variableWidth: false,
          rowGap,
        });
        rowInBand += 1;
      }
    } else {
      const bySubRow = new Map();
      for (const id of bandNodeIds) {
        const subRow = subLayers.get(id) || 0;
        if (!bySubRow.has(subRow)) bySubRow.set(subRow, []);
        bySubRow.get(subRow).push(id);
      }
      const subRowKeys = [...bySubRow.keys()].sort((a, b) => a - b);
      for (const subRow of subRowKeys) {
        const ids = focusSort
          ? _graphSortBandNodeIds(bySubRow.get(subRow), nodeById, subLayers, layoutOpts.focusNodeId)
          : bySubRow.get(subRow).slice().sort((a, b) =>
            _graphCompareNodesByFileAndLabel(nodeById.get(a), nodeById.get(b))
          );
        const wrappedRows = _graphWrapIdsByWidthCenterOut(
          ids,
          nodeById,
          _graphLayoutMaxRowWidth(layoutWidth),
          rowGap,
          focusWrap || shallow,
        );
        for (const rowIds of wrappedRows) {
          const hGap = focusWrap || shallow
            ? GRAPH_KIND_LAYOUT_SHALLOW_CELL_WIDTH
            : Math.max(GRAPH_KIND_LAYOUT_MIN_CELL_WIDTH, 96 / Math.max(1, rowIds.length));
          rowSpecs.push({
            rowIds,
            hGap,
            y: yCursor + rowInBand * subRowGap,
            variableWidth: focusWrap || shallow,
            rowGap,
          });
          rowInBand += 1;
        }
      }
    }

    if (rowInBand) {
      yCursor += rowInBand * subRowGap;
    }
  }

  const maxRowSpan = rowSpecs.reduce((max, row) => {
    if (row.variableWidth) {
      return Math.max(max, _graphRowTotalWidth(row.rowIds, nodeById, row.rowGap, true));
    }
    return Math.max(max, row.rowIds.length * row.hGap);
  }, shallow ? GRAPH_KIND_LAYOUT_SHALLOW_CELL_WIDTH : GRAPH_KIND_LAYOUT_MIN_CELL_WIDTH);
  const originX = maxRowSpan / 2;
  rowSpecs.forEach((row, rowIndex) => {
    const brickShift = rowIndex % 2 === 1
      ? (row.rowGap + (row.variableWidth ? GRAPH_KIND_LAYOUT_SHALLOW_CELL_WIDTH : row.hGap)) / 2
      : 0;
    const rowOriginX = originX + brickShift;
    if (row.variableWidth) {
      const totalSpan = _graphRowTotalWidth(row.rowIds, nodeById, row.rowGap, true);
      let x = rowOriginX - totalSpan / 2;
      for (const id of row.rowIds) {
        const cellWidth = _graphNodeLayoutCellWidth(nodeById.get(id), true);
        x += cellWidth / 2;
        positions.set(id, { x, y: row.y });
        x += cellWidth / 2 + row.rowGap;
      }
      return;
    }
    const count = row.rowIds.length;
    row.rowIds.forEach((id, index) => {
      positions.set(id, {
        x: rowOriginX + row.hGap * (index - (count - 1) / 2),
        y: row.y,
      });
    });
  });

  const bounds = _graphPositionsBounds(positions);
  return { positions, bounds, shallow };
}

function _graphPackModuleSubgraphRows(subgraphs, availWidth, gap) {
  const rows = [];
  let row = [];
  let rowWidth = 0;
  const flushRow = () => {
    if (row.length) rows.push({ subgraphs: row, width: rowWidth });
    row = [];
    rowWidth = 0;
  };

  for (const subgraph of subgraphs) {
    const nextWidth = row.length ? rowWidth + gap + subgraph.bounds.width : subgraph.bounds.width;
    if (row.length && nextWidth > availWidth) flushRow();
    if (row.length) rowWidth += gap;
    rowWidth += subgraph.bounds.width;
    row.push(subgraph);
  }
  flushRow();
  return rows;
}

function _graphPackModuleSubgraphs(subgraphs, width, height, { fit = true, focusNodeId = "" } = {}) {
  const gap = GRAPH_KIND_LAYOUT_SUBGRAPH_GAP;
  const padding = 44;
  const availWidth = width - padding * 2;
  const merged = new Map();
  if (!subgraphs.length) return merged;

  const focusId = String(focusNodeId || "");
  let rowGroups;
  if (focusId && subgraphs.length > 1) {
    const primary = subgraphs.filter(subgraph => subgraph.positions?.has(focusId));
    const satellites = subgraphs.filter(subgraph => !subgraph.positions?.has(focusId));
    if (primary.length && satellites.length) {
      rowGroups = [
        ..._graphPackModuleSubgraphRows(primary, availWidth, gap),
        ..._graphPackModuleSubgraphRows(satellites, availWidth, gap),
      ];
    }
  }
  if (!rowGroups) {
    rowGroups = _graphPackModuleSubgraphRows(subgraphs, availWidth, gap);
  }

  let yCursor = padding;
  for (const { subgraphs: rowSubs, width: totalRowWidth } of rowGroups) {
    let xCursor = padding + Math.max(0, (availWidth - totalRowWidth) / 2);
    let rowHeight = 0;
    for (const subgraph of rowSubs) {
      const { bounds, positions: subgraphPositions } = subgraph;
      const offsetX = xCursor - bounds.minX;
      const offsetY = yCursor - bounds.minY;
      for (const [id, pos] of subgraphPositions.entries()) {
        merged.set(id, { x: pos.x + offsetX, y: pos.y + offsetY });
      }
      xCursor += bounds.width + gap;
      rowHeight = Math.max(rowHeight, bounds.height);
    }
    yCursor += rowHeight + gap;
  }

  return fit ? _fitLayoutPositions(merged, width, height) : merged;
}

/** Code-only layout: module subgraphs with kind bands and packed separation. */
function _layoutGraphKindLayersFinish(merged, nodeIds, edges, nodeById, width, height, layoutOpts) {
  layoutOpts = layoutOpts || _graphLayoutOptions("", nodeById);
  if (layoutOpts.docFocus || layoutOpts.moduleFocus) {
    return _graphCenterLayoutExpanded(merged, width, height).positions;
  }
  if (_graphIsShallowFanOut(nodeIds, edges, nodeById, layoutOpts)) {
    return _graphCenterLayoutExpanded(merged, width, height).positions;
  }
  return _fitLayoutPositions(merged, width, height);
}

function _layoutGraphKindLayersCode(nodes, edges, nodeById, width, height, layoutOpts) {
  layoutOpts = layoutOpts || _graphLayoutOptions("", nodeById);
  const nodeIds = nodes.map(node => node.id);
  const subgraphSpecs = _graphModuleSubgraphs(nodes, edges);
  if (subgraphSpecs.length <= 1) {
    const ids = subgraphSpecs[0]?.nodeIds || nodeIds;
    const { positions } = _layoutGraphKindLayersGroup(ids, edges, nodeById, width, layoutOpts);
    return _layoutGraphKindLayersFinish(positions, ids, edges, nodeById, width, height, layoutOpts);
  }

  const packedSubgraphs = subgraphSpecs.map(spec => {
    const idSet = new Set(spec.nodeIds);
    const subgraphEdges = edges.filter(edge => idSet.has(edge.source) && idSet.has(edge.target));
    return _layoutGraphKindLayersGroup(spec.nodeIds, subgraphEdges, nodeById, width, layoutOpts);
  });
  const merged = _graphPackModuleSubgraphs(packedSubgraphs, width, height, {
    fit: false,
    focusNodeId: layoutOpts.focusNodeId || "",
  });
  return _layoutGraphKindLayersFinish(merged, nodeIds, edges, nodeById, width, height, layoutOpts);
}

/** Module-rooted code graphs with documentation nodes pinned to the bottom. */
function _layoutGraphKindLayers(nodes, edges, width, height, focusNodeId = "") {
  const nodeById = new Map(nodes.map(node => [node.id, node]));
  const layoutOpts = _graphLayoutOptions(focusNodeId, nodeById);
  const nodeIds = nodes.map(node => node.id);

  if (layoutOpts.docFocus || layoutOpts.moduleFocus) {
    const { positions } = _layoutGraphKindLayersGroup(nodeIds, edges, nodeById, width, layoutOpts);
    return _layoutGraphKindLayersFinish(positions, nodeIds, edges, nodeById, width, height, layoutOpts);
  }

  const docNodes = nodes.filter(node => _graphIsDocumentationKind(node));
  const codeNodes = nodes.filter(node => !_graphIsDocumentationKind(node));
  const docIdSet = new Set(docNodes.map(node => node.id));
  const codeEdges = edges.filter(edge => !docIdSet.has(edge.source) && !docIdSet.has(edge.target));

  let merged = new Map();
  if (codeNodes.length) {
    merged = _layoutGraphKindLayersCode(codeNodes, codeEdges, nodeById, width, height, layoutOpts);
  }
  if (!docNodes.length) {
    return merged;
  }

  const docEdges = edges.filter(edge => docIdSet.has(edge.source) || docIdSet.has(edge.target));
  const { positions: docPositions, bounds: docBounds } = _layoutGraphKindLayersGroup(
    docNodes.map(node => node.id),
    docEdges,
    nodeById,
    width,
    layoutOpts,
  );

  const sectionGap = 52;
  let yOffset;
  if (merged.size) {
    let codeMaxY = -Infinity;
    for (const pos of merged.values()) codeMaxY = Math.max(codeMaxY, pos.y);
    yOffset = codeMaxY + sectionGap - docBounds.minY;
  } else {
    yOffset = 52 - docBounds.minY;
  }

  let alignMidX = width / 2;
  if (merged.size) {
    let codeMinX = Infinity;
    let codeMaxX = -Infinity;
    for (const pos of merged.values()) {
      codeMinX = Math.min(codeMinX, pos.x);
      codeMaxX = Math.max(codeMaxX, pos.x);
    }
    alignMidX = (codeMinX + codeMaxX) / 2;
  }
  const xOffset = alignMidX - (docBounds.minX + docBounds.maxX) / 2;

  for (const [id, pos] of docPositions.entries()) {
    merged.set(id, { x: pos.x + xOffset, y: pos.y + yOffset });
  }

  return _layoutGraphKindLayersFinish(merged, nodeIds, edges, nodeById, width, height, layoutOpts);
}

function _graphMostConnectedNodeId(nodes, degreeMap) {
  if (!nodes.length) return "";
  let best = nodes[0];
  let bestDegree = degreeMap.get(best.id) || 0;
  for (const node of nodes) {
    const degree = degreeMap.get(node.id) || 0;
    if (
      degree > bestDegree
      || (degree === bestDegree && String(node.id).localeCompare(String(best.id)) < 0)
    ) {
      best = node;
      bestDegree = degree;
    }
  }
  return String(best.id || "");
}

/** Default community drill-down focus: module, then class, then function; degree breaks ties within a kind. */
function _graphDefaultCommunityFocusNodeId(nodes, degreeMap, kindOrder = GRAPH_COMMUNITY_FOCUS_KIND_ORDER) {
  if (!nodes.length) return "";
  for (const kind of kindOrder) {
    const candidates = nodes.filter(node => _graphKindBucket(node.kind) === kind);
    if (candidates.length) return _graphMostConnectedNodeId(candidates, degreeMap);
  }
  if (kindOrder === GRAPH_COMMUNITY_FOCUS_KIND_ORDER) {
    return _graphMostConnectedNodeId(nodes, degreeMap);
  }
  return "";
}

function _graphSortNeighborNodes(nodes) {
  return nodes.slice().sort((a, b) =>
    _graphKindLayerIndex(a, GRAPH_NEIGHBOR_KIND_ORDER) - _graphKindLayerIndex(b, GRAPH_NEIGHBOR_KIND_ORDER)
    || String(_graphLabel(a) || a.label || a.id || "").localeCompare(
      String(_graphLabel(b) || b.label || b.id || ""),
      undefined,
      { sensitivity: "base" },
    )
    || String(a.id || "").localeCompare(String(b.id || "")),
  );
}

function _graphCompareCommunitiesByInspectability(a, b) {
  return _communityInspectabilityScore(b) - _communityInspectabilityScore(a)
    || (Number(b.boundary_node_count) || 0) - (Number(a.boundary_node_count) || 0)
    || (Number(b.node_count || b.total_node_count) || 0) - (Number(a.node_count || a.total_node_count) || 0)
    || String(a.label || a.community_id || a.id || "").localeCompare(String(b.label || b.community_id || b.id || ""));
}

/** Center bubble in community overview (matches _layoutGraphCommunityBubbles hub pick). */
function _graphOverviewHubCommunityNode(overviewNodes) {
  if (!overviewNodes.length) return null;
  const production = overviewNodes.filter(node => !_graphIsCategoryCommunity(node)).sort(_graphCompareCommunitiesByInspectability);
  return production[0] || overviewNodes.slice().sort(_graphCompareCommunitiesByInspectability)[0] || null;
}

function _graphCommunityMemberNodes(communityId, communities, allNodes) {
  const cluster = (communities || []).find(entry => String(entry.community_id || "") === String(communityId || ""));
  if (!cluster) return [];
  const nodeIds = new Set((cluster.node_ids || []).map(id => String(id)));
  return allNodes.filter(node => nodeIds.has(String(node.id || "")));
}

function _hashString(value) {
  let h = 0;
  for (let i = 0; i < value.length; i += 1) {
    h = Math.imul(31, h) + value.charCodeAt(i);
    h |= 0;
  }
  return Math.abs(h);
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

function _graphSeedPosition(node, index, total, width, height, nodeDegree = 0, maxDegree = 1) {
  const key = `${node.id || index}`;
  const angle = ((_hashString(key) % 360) / 180) * Math.PI;
  const base = Math.min(width, height);
  const ringSpread = total > 1 ? base * (0.14 + ((index % 5) * 0.07)) : base * 0.16;
  const hubFactor = maxDegree > 0 ? 1 - (nodeDegree / maxDegree) * 0.62 : 1;
  const ring = ringSpread * Math.max(0.28, hubFactor);
  return {
    x: width / 2 + Math.cos(angle) * ring,
    y: height / 2 + Math.sin(angle) * ring,
  };
}

function _graphHopGroups(hubId, nodeIds, edges) {
  const allowed = new Set(nodeIds);
  const hops = new Map();
  if (hubId && allowed.has(hubId)) hops.set(hubId, 0);
  const queue = hubId && allowed.has(hubId) ? [hubId] : [];
  while (queue.length) {
    const current = queue.shift();
    const depth = hops.get(current);
    for (const edge of edges) {
      for (const [from, to] of [[edge.source, edge.target], [edge.target, edge.source]]) {
        if (from === current && allowed.has(to) && !hops.has(to)) {
          hops.set(to, depth + 1);
          queue.push(to);
        }
      }
    }
  }
  let fallbackHop = 1;
  for (const value of hops.values()) fallbackHop = Math.max(fallbackHop, value + 1);
  const groups = new Map();
  for (const id of nodeIds) {
    const hop = hops.has(id) ? hops.get(id) : fallbackHop;
    if (!groups.has(hop)) groups.set(hop, []);
    groups.get(hop).push(id);
  }
  return groups;
}

function _shouldUseHubRadialLayout(nodes, edges, degree, hubId) {
  const n = nodes.length;
  if (n > 40 || n < 16 || !hubId) return false;
  if (nodes.every(node => node.kind === "community")) return false;
  const hubDegree = degree.get(hubId) || 0;
  if (hubDegree < 8) return false;
  if (hubDegree >= (n - 1) * 0.55) return true;
  return hubDegree >= edges.length * 0.4 && hubDegree >= n * 0.35;
}

/** Even rings around a hub for dense star / drill-down views (e.g. server_impl). */
function _layoutGraphHubRadial(nodes, edges, width, height, hubId, radii) {
  const cx = width / 2;
  const cy = height / 2;
  const n = nodes.length;
  const maxR = Math.min(width, height) * 0.38;
  const groups = _graphHopGroups(hubId, nodes.map(node => node.id), edges);
  const hopLevels = [...groups.keys()].filter(h => h > 0).sort((a, b) => a - b);
  const positions = new Map();
  positions.set(hubId, { x: cx, y: cy });

  let prevOuter = 0;
  for (const hop of hopLevels) {
    const members = groups.get(hop).slice().sort((a, b) => String(a).localeCompare(String(b)));
    const count = members.length;
    if (!count) continue;
    let avgNodeR = 0;
    for (const id of members) avgNodeR += radii.get(id) || 12;
    avgNodeR /= count;
    const densityBonus = Math.min(18, Math.floor(n / 4));
    const angularSlot = _graphLayoutRadialAngularSlot(avgNodeR, densityBonus);
    const hopGap = _graphLayoutRadialHopGap(angularSlot);
    const innerR = Math.max(prevOuter + hopGap, hop === 1 ? Math.max(88, hopGap) : prevOuter + hopGap);
    const minLayoutR = (count * angularSlot) / (2 * Math.PI);
    const layoutMaxR = Math.max(maxR, minLayoutR * 1.08);
    const ringsNeeded = Math.max(1, Math.ceil((count * angularSlot) / (2 * Math.PI * layoutMaxR)));
    const perRing = Math.ceil(count / ringsNeeded);
    const ringGap = ringsNeeded === 1
      ? 0
      : Math.max((layoutMaxR - innerR) / (ringsNeeded - 1), hopGap);
    for (let ringIdx = 0; ringIdx < ringsNeeded; ringIdx += 1) {
      const chunk = members.slice(ringIdx * perRing, (ringIdx + 1) * perRing);
      const chunkCount = chunk.length;
      if (!chunkCount) continue;
      const ringFromCount = (chunkCount * angularSlot) / (2 * Math.PI);
      const ringR = ringsNeeded === 1
        ? Math.max(innerR, ringFromCount)
        : innerR + ringGap * ringIdx;
      prevOuter = ringR + avgNodeR + _graphLayoutLabelPadBelowCircle() * 0.35;
      chunk.forEach((id, index) => {
        const angle = (2 * Math.PI * index) / chunkCount - Math.PI / 2;
        positions.set(id, {
          x: cx + ringR * Math.cos(angle),
          y: cy + ringR * Math.sin(angle),
        });
      });
    }
  }

  const nonHub = nodes.filter(node => node.id !== hubId);
  const collisionMaxR = Math.max(maxR, prevOuter * 1.05);
  for (let iter = 0; iter < 48; iter += 1) {
    const alpha = 1 - iter / 48;
    for (let i = 0; i < nonHub.length; i += 1) {
      for (let j = i + 1; j < nonHub.length; j += 1) {
        const a = positions.get(nonHub[i].id);
        const b = positions.get(nonHub[j].id);
        if (!a || !b) continue;
        const dx = b.x - a.x;
        const dy = b.y - a.y;
        const dist = Math.hypot(dx, dy) || 1;
        const ra = radii.get(nonHub[i].id) || 10;
        const rb = radii.get(nonHub[j].id) || 10;
        const minDist = ra + rb + _graphLayoutLabelPadBelowCircle();
        if (dist >= minDist) continue;
        const push = ((minDist - dist) / dist) * 0.55 * alpha;
        a.x -= dx * push;
        a.y -= dy * push;
        b.x += dx * push;
        b.y += dy * push;
      }
    }
    for (const node of nonHub) {
      const pos = positions.get(node.id);
      if (!pos) continue;
      const dx = pos.x - cx;
      const dy = pos.y - cy;
      const r = Math.hypot(dx, dy) || 1;
      if (r > collisionMaxR) {
        pos.x = cx + (dx / r) * collisionMaxR;
        pos.y = cy + (dy / r) * collisionMaxR;
      }
    }
  }

  return positions;
}

function _graphLayoutInputKey(nodes, edges, mode, focusId, width, height) {
  const nodePart = nodes.map(node => String(node.id || "")).join("\0");
  const edgePart = edges.map(edge => `${edge.source}\0${edge.target}\0${edge.relation || ""}`).join("\1");
  return `${mode}|${focusId}|${width}|${height}|${nodePart}|${edgePart}`;
}

function _layoutGraphCommunityBubbles(nodes, width, height) {
  const cx = width / 2;
  const cy = height / 2;
  const byScore = (a, b) =>
    _communityInspectabilityScore(b) - _communityInspectabilityScore(a)
    || (Number(b.boundary_node_count) || 0) - (Number(a.boundary_node_count) || 0)
    || (Number(b.node_count || b.total_node_count) || 0) - (Number(a.node_count || a.total_node_count) || 0)
    || String(a.label || a.id || "").localeCompare(String(b.label || b.id || ""));

  const production = nodes.filter(node => !_graphIsCategoryCommunity(node)).sort(byScore);
  const categories = nodes.filter(node => _graphIsCategoryCommunity(node)).sort(byScore);
  const center = production[0] || nodes.slice().sort(byScore)[0];
  const positions = new Map();
  if (!center) return positions;

  const ringNodes = [
    ...production.filter(node => node.id !== center.id),
    ...categories,
  ].sort((a, b) =>
    _graphNodeRadius(b, 0) - _graphNodeRadius(a, 0)
    || String(a.label || a.id || "").localeCompare(String(b.label || b.id || "")),
  );

  positions.set(center.id, { x: cx, y: cy });
  const spokeCount = 7;
  const maxR = Math.min(width, height) * 0.37;
  const innerRing = maxR * 0.54;
  const ringStep = maxR * 0.16;
  const ringBase = maxR * 0.62;
  const outerRing = ringBase + 2 * ringStep;
  const tierSpan = outerRing - innerRing + ringStep;
  const twistPerSlot = (2 * Math.PI) / (spokeCount * 1.6);
  ringNodes.forEach((node, index) => {
    const spoke = index % spokeCount;
    const radialSlot = Math.floor(index / spokeCount);
    const band = radialSlot % 3;
    const tier = Math.floor(radialSlot / 3);
    const bandRing = band === 0 ? innerRing : ringBase + band * ringStep;
    const ring = bandRing + tier * tierSpan;
    const angle = (2 * Math.PI * spoke) / spokeCount - Math.PI / 2 + radialSlot * twistPerSlot;
    positions.set(node.id, {
      x: cx + ring * Math.cos(angle),
      y: cy + ring * Math.sin(angle),
    });
  });
  return positions;
}

function _graphResolveLayoutMode({
  viewMode,
  selectedNodeId,
  hasCommunityOverview,
  selectedClusterId,
  nodeCount,
}) {
  if (hasCommunityOverview) return "force";
  if (selectedClusterId || viewMode === "files") return "hierarchical";
  if (viewMode === "focus" && selectedNodeId) return "hierarchical";
  if (nodeCount > 28) return "hierarchical";
  return "force";
}

function _graphLayoutModeLabel(mode) {
  if (mode === "hierarchical") return "Layered layout";
  if (mode === "radial") return "Radial layout";
  return "Force layout";
}

function _graphElkNodeSize(node) {
  const { maxLineChars, lineCount } = _graphLabelMetrics(_graphLabel(node));
  return {
    width: Math.min(240, Math.max(64, maxLineChars * 6.2)),
    height: Math.max(36, 20 + lineCount * GRAPH_LABEL_LINE_HEIGHT),
  };
}

function _fitLayoutPositions(positions, width, height, padding = 44) {
  if (!positions.size) return positions;
  let minX = Infinity;
  let minY = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;
  for (const pos of positions.values()) {
    minX = Math.min(minX, pos.x);
    minY = Math.min(minY, pos.y);
    maxX = Math.max(maxX, pos.x);
    maxY = Math.max(maxY, pos.y);
  }
  const boxW = Math.max(1, maxX - minX);
  const boxH = Math.max(1, maxY - minY);
  const scale = Math.min(
    (width - padding * 2) / boxW,
    (height - padding * 2) / boxH,
    2.4,
  );
  const midX = (minX + maxX) / 2;
  const midY = (minY + maxY) / 2;
  const fitted = new Map();
  for (const [id, pos] of positions.entries()) {
    fitted.set(id, {
      x: width / 2 + (pos.x - midX) * scale,
      y: height / 2 + (pos.y - midY) * scale,
    });
  }
  return fitted;
}

async function _graphElkLayout(nodes, edges, width, height) {
  if (typeof ELK !== "function") {
    throw new Error("ELK layout library not loaded");
  }
  const elk = new ELK();
  const children = nodes.map((node) => {
    const size = _graphElkNodeSize(node);
    return { id: node.id, width: size.width, height: size.height };
  });
  const elkEdges = edges.map((edge, index) => ({
    id: `e${index}`,
    sources: [edge.source],
    targets: [edge.target],
  }));
  const nodeCount = Math.max(1, nodes.length);
  const nodeSpacing = Math.max(44, Math.min(96, Math.floor(720 / Math.sqrt(nodeCount))));
  const layerSpacing = Math.max(
    _graphLayoutHierarchicalRowGap(false),
    Math.min(88, 80 - Math.floor(nodeCount / 10)),
  );
  const layout = await elk.layout({
    id: "root",
    layoutOptions: {
      "elk.algorithm": "layered",
      "elk.direction": "DOWN",
      "elk.spacing.nodeNode": String(nodeSpacing),
      "elk.layered.spacing.nodeNodeBetweenLayers": String(layerSpacing),
      "elk.layered.nodePlacement.strategy": "NETWORK_SIMPLEX",
      "elk.layered.cycleBreaking.strategy": "GREEDY",
      "elk.padding": "[top=24,left=24,bottom=24,right=24]",
    },
    children,
    edges: elkEdges,
  });
  const positions = new Map();
  for (const child of layout.children || []) {
    positions.set(child.id, {
      x: (child.x || 0) + (child.width || 64) / 2,
      y: (child.y || 0) + (child.height || 36) / 2,
    });
  }
  if (!positions.size) {
    nodes.forEach((node, index) => {
      positions.set(node.id, { x: width / 2, y: 48 + index * _graphLayoutSubRowGap(GRAPH_LAYOUT_MAX_NODE_RADIUS) });
    });
  }
  return _fitLayoutPositions(positions, width, height);
}

/** Radial rings by hop distance from a focus node (focus / ego views). */
function _layoutGraphRadialByHop(nodes, edges, width, height, focusId, radii) {
  const cx = width / 2;
  const cy = height / 2;
  const maxR = Math.min(width, height) * 0.4;
  const groups = _graphHopGroups(focusId, nodes.map(node => node.id), edges);
  const hopLevels = [...groups.keys()].sort((a, b) => a - b);
  const positions = new Map();
  if (focusId) positions.set(focusId, { x: cx, y: cy });

  let prevOuter = 0;
  for (const hop of hopLevels) {
    if (hop === 0) continue;
    const members = groups.get(hop).slice().sort((a, b) => String(a).localeCompare(String(b)));
    const count = members.length;
    if (!count) continue;
    let avgNodeR = 0;
    for (const id of members) avgNodeR += radii.get(id) || 12;
    avgNodeR /= count;
    const angularSlot = _graphLayoutRadialAngularSlot(avgNodeR);
    const hopGap = _graphLayoutRadialHopGap(angularSlot);
    const innerR = Math.max(prevOuter + hopGap, 72 + hop * 18);
    const minLayoutR = (count * angularSlot) / (2 * Math.PI);
    const layoutMaxR = Math.max(maxR, minLayoutR * 1.08);
    const ringsNeeded = Math.max(1, Math.ceil((count * angularSlot) / (2 * Math.PI * layoutMaxR)));
    const perRing = Math.ceil(count / ringsNeeded);
    const ringGap = ringsNeeded === 1
      ? 0
      : Math.max((layoutMaxR - innerR) / (ringsNeeded - 1), hopGap);
    for (let ringIdx = 0; ringIdx < ringsNeeded; ringIdx += 1) {
      const chunk = members.slice(ringIdx * perRing, (ringIdx + 1) * perRing);
      const chunkCount = chunk.length;
      if (!chunkCount) continue;
      const ringFromCount = (chunkCount * angularSlot) / (2 * Math.PI);
      const ringR = ringsNeeded === 1
        ? Math.max(innerR, ringFromCount)
        : innerR + ringGap * ringIdx;
      prevOuter = ringR + avgNodeR + _graphLayoutLabelPadBelowCircle() * 0.35;
      chunk.forEach((id, index) => {
        const angle = (2 * Math.PI * index) / chunkCount - Math.PI / 2;
        positions.set(id, {
          x: cx + ringR * Math.cos(angle),
          y: cy + ringR * Math.sin(angle),
        });
      });
    }
  }
  for (const node of nodes) {
    if (!positions.has(node.id)) {
      positions.set(node.id, { x: cx + maxR * 0.9, y: cy });
    }
  }
  return positions;
}

/** Simple top-down layering when ELK is unavailable (better than force hairballs). */
function _layoutGraphTopoLayers(nodes, edges, width, height) {
  const nodeIds = nodes.map(node => node.id);
  const layers = new Map();
  const inDegree = new Map(nodeIds.map(id => [id, 0]));
  for (const edge of edges) {
    if (inDegree.has(edge.target)) {
      inDegree.set(edge.target, (inDegree.get(edge.target) || 0) + 1);
    }
  }
  const queue = nodeIds.filter(id => (inDegree.get(id) || 0) === 0);
  if (!queue.length && nodeIds.length) queue.push(nodeIds[0]);
  for (const id of queue) layers.set(id, 0);
  while (queue.length) {
    const current = queue.shift();
    const depth = layers.get(current);
    for (const edge of edges) {
      if (edge.source === current && !layers.has(edge.target)) {
        layers.set(edge.target, depth + 1);
        queue.push(edge.target);
      }
    }
  }
  let maxLayer = 0;
  for (const depth of layers.values()) maxLayer = Math.max(maxLayer, depth);
  for (const id of nodeIds) {
    if (!layers.has(id)) layers.set(id, maxLayer + 1);
  }
  const byLayer = new Map();
  for (const id of nodeIds) {
    const layer = layers.get(id);
    if (!byLayer.has(layer)) byLayer.set(layer, []);
    byLayer.get(layer).push(id);
  }
  const positions = new Map();
  const layerKeys = [...byLayer.keys()].sort((a, b) => a - b);
  const vGap = Math.max(64, Math.min(92, Math.floor(680 / Math.max(1, layerKeys.length))));
  for (const layer of layerKeys) {
    const members = byLayer.get(layer).slice().sort((a, b) => String(a).localeCompare(String(b)));
    const hGap = Math.max(56, width / (members.length + 1));
    members.forEach((id, index) => {
      positions.set(id, { x: hGap * (index + 1), y: 52 + layer * vGap });
    });
  }
  return _fitLayoutPositions(positions, width, height);
}

async function _layoutGraphAsync(nodes, edges, width, height, { mode, focusId } = {}) {
  if (!nodes.length) return new Map();
  const degree = new Map(nodes.map(node => [node.id, 0]));
  for (const edge of edges) {
    degree.set(edge.source, (degree.get(edge.source) || 0) + 1);
    degree.set(edge.target, (degree.get(edge.target) || 0) + 1);
  }
  const radii = new Map(nodes.map(node => [node.id, _graphNodeRadius(node, degree.get(node.id) || 0)]));

  if (mode === "hierarchical") {
    return _layoutGraphKindLayers(nodes, edges, width, height, focusId || "");
  }
  if (mode === "radial" && focusId) {
    return _layoutGraphRadialByHop(nodes, edges, width, height, focusId, radii);
  }
  if (mode === "force" && nodes.length && nodes.every(node => node.kind === "community")) {
    return _layoutGraphCommunityBubbles(nodes, width, height);
  }
  return _layoutGraph(nodes, edges, width, height);
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

  let maxDegree = 0;
  const hubId = _graphPickLayoutHubId(nodes, degree);
  for (const node of nodes) {
    maxDegree = Math.max(maxDegree, degree.get(node.id) || 0);
  }

  const cx = width / 2;
  const cy = height / 2;
  const radii = new Map(nodes.map((node) => [node.id, _graphNodeRadius(node, degree.get(node.id) || 0)]));

  if (_shouldUseHubRadialLayout(nodes, edges, degree, hubId)) {
    return _layoutGraphHubRadial(nodes, edges, width, height, hubId, radii);
  }

  for (let i = 0; i < nodes.length; i += 1) {
    const node = nodes[i];
    positions.set(node.id, {
      ..._graphSeedPosition(node, i, nodes.length, width, height, degree.get(node.id) || 0, maxDegree),
      vx: 0,
      vy: 0,
    });
  }

  const n = Math.max(1, nodes.length);
  const linkPad = 72 + Math.min(22, Math.floor(n / 4));
  const repel = 5200 + n * 200;
  const spring = 0.0085;
  const center = 0.0045 + Math.min(0.0035, n * 0.0001);
  const damping = 0.81;
  const iterations = Math.min(200, 96 + n * 2);
  const margin = 32;

  for (let iter = 0; iter < iterations; iter += 1) {
    const alpha = 1 - iter / iterations;
    for (let i = 0; i < nodes.length; i += 1) {
      const a = positions.get(nodes[i].id);
      if (!a) continue;
      for (let j = i + 1; j < nodes.length; j += 1) {
        const b = positions.get(nodes[j].id);
        if (!b) continue;
        let dx = b.x - a.x;
        let dy = b.y - a.y;
        let dist = Math.sqrt(dx * dx + dy * dy) || 1;
        const ra = radii.get(nodes[i].id) || 10;
        const rb = radii.get(nodes[j].id) || 10;
        const minDist = ra + rb + 46;
        if (dist < minDist) dist = minDist;
        const force = (repel * alpha) / (dist * dist);
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
      const desired = (radii.get(nodes[sourceIndex].id) || 10)
        + (radii.get(nodes[targetIndex].id) || 10)
        + linkPad;
      const stretch = dist - desired;
      const capped = Math.max(-desired * 0.2, Math.min(stretch, desired * 0.42));
      const force = capped * spring * alpha;
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
      pos.vx += (cx - pos.x) * center * alpha;
      pos.vy += (cy - pos.y) * center * alpha;
      pos.vx *= damping;
      pos.vy *= damping;
      pos.x += pos.vx;
      pos.y += pos.vy;
      pos.x = Math.max(margin, Math.min(width - margin, pos.x));
      pos.y = Math.max(margin, Math.min(height - margin, pos.y));
    }
  }

  return positions;
}

// 1p72v / AC-6: removed a duplicate, dead `_graphEdgeLineOpacity` definition.
// Two identical signatures existed; with function hoisting the second
// (higher-contrast: 0.92/0.85/0.82/0.74/0.12/0.48) shadowed and overrode the
// first at the only call site, so the first was dead code. The surviving
// definition below is the intended one (matches the in-effect runtime behavior).
function _graphEdgeLineOpacity({ edgePreview, edgeSelected, edgeFocused, edgeConnectedToHover, previewNodeId }) {
  if (edgePreview) return 0.92;
  if (edgeSelected) return 0.85;
  if (edgeFocused) return 0.82;
  if (edgeConnectedToHover) return 0.74;
  if (previewNodeId) return 0.12;
  return 0.48;
}

function _graphEdgeStrokeWidth({ edgePreview, edgeSelected, edgeFocused, edgeConnectedToHover }, edgeWeight) {
  const base = Math.min(4.0, 1.15 + Math.log2(edgeWeight + 1) * 0.35);
  if (edgePreview || edgeSelected) return 2.0;
  if (edgeFocused) return 1.75;
  if (edgeConnectedToHover) return 1.45;
  return base;
}

function _graphEdgeArrowMarkers() {
  return h("marker", {
    id: "graph-arrow",
    markerWidth: 6,
    markerHeight: 6,
    refX: 5.5,
    refY: 3,
    orient: "auto",
    markerUnits: "userSpaceOnUse",
  }, h("path", { d: "M0,0 L0,6 L9,3 z", fill: "currentColor" }));
}

function _graphCommunityNodeId(communityId) {
  return `community:${String(communityId || "").trim() || "__ungrouped__"}`;
}

function _communityInspectabilityScore(cluster) {
  const nodeCount = Math.max(0, Number(cluster?.node_count || cluster?.total_node_count || 0));
  const boundaryCount = Math.max(0, Number(cluster?.boundary_node_count || 0));
  if (!nodeCount) return 0;
  return (boundaryCount / nodeCount) * Math.log2(nodeCount + 1);
}

function _graphIsCategoryCommunity(node) {
  if (!node) return false;
  if (String(node.cluster_kind || "").trim() === "fixed") return true;
  if (String(node.kind || "").trim() === "fixed") return true;
  return GRAPH_CATEGORY_COMMUNITY_LABELS.has(String(node.label || "").trim());
}

/** Prefer a production (non-category) community/module as the radial or force hub. */
function _graphPickLayoutHubId(nodes, degree) {
  const eligible = nodes.filter(node => !_graphIsCategoryCommunity(node));
  const pool = eligible.length ? eligible : nodes;
  let hubId = pool[0]?.id || "";
  let maxDegree = -1;
  for (const node of pool) {
    const nodeDegree = degree.get(node.id) || 0;
    if (nodeDegree > maxDegree) {
      maxDegree = nodeDegree;
      hubId = node.id;
    }
  }
  return hubId;
}

function _isMeaningfulCommunity(cluster) {
  return Math.max(0, Number(cluster?.node_count || 0)) >= GRAPH_MIN_COMMUNITY_NODES;
}

function _buildCommunityOverviewGraph(nodes, edges, communities) {
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
        cluster_kind: String(community.kind || "").trim(),
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
      cluster_kind: bucket.cluster_kind || "",
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
    if (!GRAPH_COMMUNITY_OVERVIEW_RELATIONS.has(relation)) continue;
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

function _graphEdgeRelationLabel(relation) {
  return String(relation || "").replace(/_/g, " ").toUpperCase();
}

function _graphEdgeTooltipLabel(edge, focusId) {
  const other = edge.source === focusId ? edge.target : edge.source;
  return `${_graphEdgeRelationLabel(edge.relation)} ${other}`;
}

function _graphNeighborTooltip(focusId, neighborId, edges) {
  return edges
    .filter(edge =>
      (edge.source === focusId && edge.target === neighborId)
      || (edge.target === focusId && edge.source === neighborId),
    )
    .map(edge => _graphEdgeTooltipLabel(edge, focusId))
    .join("\n");
}

function GraphTreeNav({ focusNodeId, focusNode, layer, onSelectNode }) {
  const [payload, setPayload] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [activeIndex, setActiveIndex] = useState(0);

  useEffect(() => {
    if (!focusNodeId) {
      setPayload(null);
      setError("");
      setActiveIndex(0);
      return undefined;
    }
    let cancelled = false;
    const controller = new AbortController();
    async function loadNeighbors() {
      setLoading(true);
      setError("");
      try {
        const response = await fetch(
          `/api/graph/neighbors?layer=${encodeURIComponent(layer)}&symbol=${encodeURIComponent(focusNodeId)}`,
          { cache: "no-store", signal: controller.signal },
        );
        if (!response.ok) throw new Error(`Neighbor request failed with ${response.status}`);
        const data = await response.json();
        if (!cancelled) setPayload(data);
      } catch (err) {
        if (!cancelled && err.name !== "AbortError") {
          setError(err.message || String(err));
          setPayload(null);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    loadNeighbors();
    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [focusNodeId, layer]);

  const neighborNodes = Array.isArray(payload?.nodes)
    ? payload.nodes.filter(node => String(node.id || "") !== String(focusNodeId))
    : [];
  const visibleNeighborNodes = _graphSortNeighborNodes(neighborNodes);
  const edges = Array.isArray(payload?.edges) ? payload.edges : [];
  const focusNodeRecord = focusNode
    || (Array.isArray(payload?.nodes)
      ? payload.nodes.find(node => String(node.id || "") === String(focusNodeId))
      : null)
    || null;

  useEffect(() => {
    setActiveIndex(0);
  }, [focusNodeId, payload]);

  const onTreeKeyDown = (event) => {
    if (!visibleNeighborNodes.length) return;
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setActiveIndex(index => Math.min(visibleNeighborNodes.length - 1, index + 1));
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setActiveIndex(index => Math.max(0, index - 1));
    } else if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      const node = visibleNeighborNodes[activeIndex];
      if (node) onSelectNode(String(node.id || ""));
    }
  };

  if (!focusNodeId) {
    return h("aside", { className: "graph-tree-nav", "aria-label": "Graph tree navigation" },
      h("div", { className: "graph-tree-nav-header" },
        h("h3", { className: "graph-tree-nav-title" }, "Neighbors"),
        h("p", { className: "muted" }, "Select a node to load 1-hop neighbors."),
      ),
    );
  }
  return h("aside", {
    className: "graph-tree-nav",
    "aria-label": "Graph tree navigation",
    tabIndex: 0,
    onKeyDown: onTreeKeyDown,
  },
    h("div", { className: "graph-tree-nav-header" },
      h("h3", { className: "graph-tree-nav-title" }, "Neighbors"),
      focusNodeRecord
        ? h(React.Fragment, null,
            h("div", { className: "graph-selection-title graph-tree-nav-focus-title" }, _graphLabel(focusNodeRecord)),
            h("div", { className: "graph-selection-meta graph-tree-nav-focus-meta muted" },
              `${focusNodeRecord.kind || "node"} · ${focusNodeRecord.source_file || focusNodeRecord.id}`,
            ),
            (focusNodeRecord.is_chokepoint || focusNodeRecord.is_entry_point || focusNodeRecord.dead_code_risk)
              ? h("div", { className: "graph-node-badges graph-tree-nav-badges" },
                  focusNodeRecord.is_chokepoint ? h("span", { className: "graph-node-badge graph-node-badge--chokepoint" }, "Chokepoint") : null,
                  focusNodeRecord.is_entry_point ? h("span", { className: "graph-node-badge graph-node-badge--entry" }, "Entry point") : null,
                  focusNodeRecord.dead_code_risk ? h("span", { className: "graph-node-badge graph-node-badge--dead" }, "Dead code risk") : null,
                )
              : null,
          )
        : h("p", { className: "graph-tree-nav-focus muted" }, focusNodeId),
      loading ? h("p", { className: "muted" }, "Loading neighbors…") : null,
      error ? h("p", { className: "graph-error" }, error) : null,
      !loading && !error && !payload?.present
        ? h("p", { className: "muted" }, payload?.diagnostic || "Graph unavailable.")
        : null,
      !loading && !error && payload?.present && !visibleNeighborNodes.length
        ? h("p", { className: "muted" }, "No neighbors — isolated node.")
        : null,
    ),
    h("ul", { className: "graph-tree-nav-list", role: "tree" },
      visibleNeighborNodes.slice(0, 40).map((node, index) => {
        const neighborId = String(node.id || "");
        const tooltip = _graphNeighborTooltip(focusNodeId, neighborId, edges);
        return h("li", { key: node.id, role: "treeitem" },
          h("button", {
            type: "button",
            className: `graph-tree-nav-item${index === activeIndex ? " graph-tree-nav-item--active" : ""}`,
            "aria-current": index === activeIndex ? "true" : undefined,
            title: tooltip || undefined,
            onClick: () => onSelectNode(neighborId),
          }, `${node.label || node.id} (${node.kind || "node"})`),
        );
      }),
    ),
    edges.length
      ? h("p", { className: "graph-tree-nav-meta muted" }, `${edges.length} connecting edge(s)`)
      : h("p", { className: "graph-tree-nav-meta muted" }, visibleNeighborNodes.length ? "No connecting edges." : null),
  );
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
  const [selectedNodeId, setSelectedNodeId] = useState("");
  const [hoveredNodeId, setHoveredNodeId] = useState("");
  const [selectedFile, setSelectedFile] = useState("");
  const [selectedClusterId, setSelectedClusterId] = useState("");
  const [focusNeighborhood, setFocusNeighborhood] = useState(null);
  const [focusNeighborsLoading, setFocusNeighborsLoading] = useState(false);
  const OVERVIEW_CRUMB = { label: "Communities", viewMode: "overview", selectedNodeId: "", selectedClusterId: "", selectedFile: "" };
  const [navHistory, setNavHistory] = useState([OVERVIEW_CRUMB]);
  // Refs for browser-history sync — avoid stale closures in popstate/keydown handlers.
  const _navHistoryRef = useRef([OVERVIEW_CRUMB]);
  const _browserNavIndexRef = useRef(0);
  const _suppressPopstateRef = useRef(false);
  const graphVersion = snapshot?.health?.graph?.[layer]?.graph_version || snapshot?.health?.graph?.[layer]?.graph_mtime || 0;

  // Wave 1p2q3 (131es AC-17/18): avoid the full-page flicker on graph refresh.
  // The prior implementation flipped `loading=true` on every reload (showing the
  // "Loading graph…" banner) and reset selectedNodeId. On dashboards polling at
  // sub-second cadence that produced a perceptible flash even when the snapshot
  // was unchanged. The refresh path now:
  //   1) only shows the loading state on the initial load (graph still null);
  //   2) computes a cheap signature of the incoming payload and skips `setGraph`
  //      when identical (AC-18: no-op on empty delta);
  //   3) preserves selectedNodeId across reloads when the node is still present.
  const _initialLoadDoneRef = useRef(false);
  const _graphSigRef = useRef("");
  function _graphSignature(g) {
    if (!g || !g.present) return "absent";
    const nodes = g.nodes || [];
    const edges = g.edges || [];
    return `${nodes.length}:${edges.length}:${g.builder_version || ""}:${g.counts?.nodes || 0}:${g.counts?.edges || 0}`;
  }
  useEffect(() => {
    let cancelled = false;
    const controller = new AbortController();
    async function loadGraph() {
      const isInitial = !_initialLoadDoneRef.current;
      if (isInitial) setLoading(true);
      setError("");
      try {
        const response = await fetch(`/api/graph?layer=${encodeURIComponent(layer)}`, { cache: "no-store", signal: controller.signal });
        if (!response.ok) {
          throw new Error(`Graph request failed with ${response.status}`);
        }
        const data = await response.json();
        if (cancelled) return;
        const newSig = _graphSignature(data);
        const prevSig = _graphSigRef.current;
        _initialLoadDoneRef.current = true;
        if (newSig === prevSig) {
          // AC-18: identical snapshot — skip the state update so React performs
          // no reconciliation work and no DOM mutation occurs.
          return;
        }
        _graphSigRef.current = newSig;
        setGraph(data);
        // Preserve selection across refresh when the previously-selected node
        // still exists in the new payload.
        if (selectedNodeId) {
          const stillExists = (data?.nodes || []).some(n => n.id === selectedNodeId);
          if (!stillExists) setSelectedNodeId("");
        }
      } catch (err) {
        if (!cancelled && err.name !== "AbortError") {
          setError(err.message || String(err));
          if (!_initialLoadDoneRef.current) setGraph(null);
        }
      } finally {
        if (!cancelled && isInitial) setLoading(false);
      }
    }
    loadGraph();
    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [layer, graphVersion]);

  useEffect(() => {
    if (viewMode !== "focus" || !selectedNodeId) {
      setFocusNeighborhood(null);
      setFocusNeighborsLoading(false);
      return undefined;
    }
    let cancelled = false;
    const controller = new AbortController();
    async function loadFocusNeighborhood() {
      setFocusNeighborsLoading(true);
      try {
        const response = await fetch(
          `/api/graph/neighbors?layer=${encodeURIComponent(layer)}&symbol=${encodeURIComponent(selectedNodeId)}`,
          { cache: "no-store", signal: controller.signal },
        );
        if (!response.ok) throw new Error(`Neighbor request failed with ${response.status}`);
        const data = await response.json();
        const focusId = data.focus_node_id || selectedNodeId;
        if (!cancelled) setFocusNeighborhood(_graphFilterDocFocusNeighborhood(data, focusId));
      } catch (err) {
        if (!cancelled && err.name !== "AbortError") setFocusNeighborhood({ present: false, diagnostic: err.message || String(err) });
      } finally {
        if (!cancelled) setFocusNeighborsLoading(false);
      }
    }
    loadFocusNeighborhood();
    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [viewMode, selectedNodeId, layer, graphVersion]);

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
  for (const node of nodes) {
    if (node.degree != null) degreeMap.set(node.id, Number(node.degree) || 0);
  }
  for (const edge of edges) {
    if (!degreeMap.has(edge.source)) degreeMap.set(edge.source, (degreeMap.get(edge.source) || 0) + 1);
    if (!degreeMap.has(edge.target)) degreeMap.set(edge.target, (degreeMap.get(edge.target) || 0) + 1);
  }
  const previewNodeId = selectedNodeId || hoveredNodeId;
  const focusModeConnectedIds = selectedNodeId ? (() => {
    const ids = new Set([selectedNodeId]);
    for (const edge of edges) {
      if (edge.source === selectedNodeId || edge.target === selectedNodeId) {
        ids.add(edge.source);
        ids.add(edge.target);
      }
    }
    return ids;
  })() : null;
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
    ? _buildCommunityOverviewGraph(filteredNodes, edges, meaningfulCommunities)
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
  const overviewHubCommunityNode = hasCommunityOverview && overviewGraph?.nodes?.length
    ? _graphOverviewHubCommunityNode(overviewGraph.nodes)
    : null;
  const overviewHubMemberNodes = overviewHubCommunityNode?.community_id
    ? _graphCommunityMemberNodes(overviewHubCommunityNode.community_id, meaningfulCommunities, filteredNodes)
    : [];
  const overviewHubFocusNodeId = hasCommunityOverview && !selectedNodeId && !selectedClusterId && overviewHubMemberNodes.length
    ? _graphDefaultCommunityFocusNodeId(overviewHubMemberNodes, degreeMap, GRAPH_COMMUNITY_OVERVIEW_FOCUS_KIND_ORDER)
    : "";
  const selectedCommunityBubbleId = hasCommunityOverview && !selectedClusterId && overviewHubCommunityNode?.community_id
    ? _graphCommunityNodeId(overviewHubCommunityNode.community_id)
    : "";
  const treeNavFocusNodeId = selectedNodeId
    || (selectedClusterId && clusterNodes.length
      ? _graphDefaultCommunityFocusNodeId(clusterNodes, degreeMap)
      : "")
    || overviewHubFocusNodeId;
  const visibleClusterNodeIds = selectedClusterNodeIds ? new Set(clusterNodes.map(node => node.id)) : null;
  const focusedNodes = focusModeConnectedIds
    ? filteredNodes.filter(node => focusModeConnectedIds.has(node.id))
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
    const relationOk = !relation || ALL_GRAPH_RELATIONS_SET.has(relation);
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
  const useFocusNeighborhood = viewMode === "focus" && selectedNodeId && focusNeighborhood?.present;
  const layoutNodes = useFocusNeighborhood ? (focusNeighborhood.nodes || []) : visibleNodes;
  const layoutEdges = useFocusNeighborhood ? (focusNeighborhood.edges || []) : visibleCommunityEdges;
  const interactionFocusId = hoveredNodeId || selectedNodeId || "";
  const previewUsesNavRelationsOnly = Boolean(hoveredNodeId && !selectedNodeId);
  const connectedNodeIds = (() => {
    if (!interactionFocusId) return new Set();
    const ids = new Set([interactionFocusId]);
    for (const edge of layoutEdges) {
      if (edge.source === interactionFocusId || edge.target === interactionFocusId) {
        ids.add(edge.source);
        ids.add(edge.target);
      }
    }
    return ids;
  })();
  const graphHighlightFocus = Boolean(
    previewNodeId
    && interactionFocusId
    && layoutEdges.some(edge => edge.source === interactionFocusId || edge.target === interactionFocusId),
  );
  const highlightPreviewNodeId = graphHighlightFocus ? previewNodeId : "";
  const nodesWithLayoutEdges = React.useMemo(() => {
    const ids = new Set();
    for (const edge of layoutEdges) {
      ids.add(edge.source);
      ids.add(edge.target);
    }
    return ids;
  }, [layoutEdges]);
  const graphWidth = 1040;
  const graphHeight = 760;
  const graphEdgeArrowInset = 1.5;
  const graphLayoutMode = _graphResolveLayoutMode({
    viewMode,
    selectedNodeId,
    hasCommunityOverview,
    selectedClusterId,
    nodeCount: layoutNodes.length,
  });
  const graphLayoutFocusId = treeNavFocusNodeId || selectedNodeId || "";
  const layoutInputKey = _graphLayoutInputKey(
    layoutNodes,
    layoutEdges,
    graphLayoutMode,
    graphLayoutFocusId,
    graphWidth,
    graphHeight,
  );
  const layoutNodesRef = React.useRef(layoutNodes);
  const layoutEdgesRef = React.useRef(layoutEdges);
  layoutNodesRef.current = layoutNodes;
  layoutEdgesRef.current = layoutEdges;
  const [layout, setLayout] = React.useState(() => new Map());
  const [layoutPending, setLayoutPending] = React.useState(false);
  const layoutRunRef = React.useRef(0);
  const graphViewBox = React.useMemo(
    () => _graphViewBoxFromLayout(layout, graphWidth, graphHeight),
    [layout, graphWidth, graphHeight],
  );
  React.useEffect(() => {
    const runId = layoutRunRef.current + 1;
    layoutRunRef.current = runId;
    let cancelled = false;
    const nodes = layoutNodesRef.current;
    const edges = layoutEdgesRef.current;
    async function computeLayout() {
      if (!nodes.length) {
        if (!cancelled && layoutRunRef.current === runId) {
          setLayout(new Map());
          setLayoutPending(false);
        }
        return;
      }
      setLayoutPending(true);
      try {
        const positions = await _layoutGraphAsync(
          nodes,
          edges,
          graphWidth,
          graphHeight,
          { mode: graphLayoutMode, focusId: graphLayoutFocusId },
        );
        if (!cancelled && layoutRunRef.current === runId) setLayout(positions);
      } catch {
        if (!cancelled && layoutRunRef.current === runId) {
          setLayout(_layoutGraph(nodes, edges, graphWidth, graphHeight));
        }
      } finally {
        if (layoutRunRef.current === runId) setLayoutPending(false);
      }
    }
    computeLayout();
    return () => { cancelled = true; };
  }, [layoutInputKey, graphLayoutMode, graphLayoutFocusId, graphWidth, graphHeight]);
  const graphNodeColorContext = { hasCommunityOverview, selectedClusterId, viewMode };
  const selectedNode = layoutNodes.find(node => node.id === selectedNodeId)
    || visibleNodes.find(node => node.id === selectedNodeId)
    || null;
  const treeNavFocusNode = selectedNode
    || (treeNavFocusNodeId ? filteredNodes.find(node => node.id === treeNavFocusNodeId) || null : null);
  const selectedMode = selectedNodeId ? "focus" : selectedClusterId ? "overview" : viewMode;
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

  const focusFirstSearchMatch = () => {
    const match = filteredNodes[0];
    if (match?.id) selectNode(String(match.id));
  };

  return h("article", { className: "graph-card" },
    h("div", { className: "graph-header" },
      h("div", null,
        h("h2", { className: "panel-heading" }, "Graph"),
        h("p", { className: "graph-subtitle muted" },
          graph?.present ? `${graphCounts.nodes || nodes.length} nodes · ${graphCounts.edges || edges.length} edges` : "Graph index has not been built yet."
        ),
      ),
    ),
      h("div", { className: "graph-toolbar" },
        h("label", { className: "graph-search" },
          h("span", { className: "graph-search-label" }, "Filter"),
          h("input", {
            type: "search",
          value: query,
          onChange: (e) => setQuery(e.target.value),
          onKeyDown: (e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              focusFirstSearchMatch();
            }
          },
          placeholder: "file, symbol, or path — Enter to focus",
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
    graph?.present ? h("div", { className: "graph-shell graph-shell--with-tree" },
      h(GraphTreeNav, {
        focusNodeId: treeNavFocusNodeId,
        focusNode: treeNavFocusNode,
        layer,
        onSelectNode: selectNode,
      }),
      h("div", { className: "graph-canvas-column" },
      h("div", { className: "graph-svg-wrap" },
      focusNeighborsLoading && viewMode === "focus" && selectedNodeId
        ? h("p", { className: "graph-svg-banner muted" }, "Loading focus neighborhood…")
        : null,
      viewMode === "focus" && selectedNodeId && focusNeighborhood && !focusNeighborhood.present && !focusNeighborsLoading
        ? h("p", { className: "graph-svg-banner graph-state--error" }, focusNeighborhood.diagnostic || "Focus neighborhood unavailable.")
        : null,
      layoutPending && layoutNodes.length
        ? h("p", { className: "graph-svg-banner muted" }, "Computing layout…")
        : null,
      layoutNodes.length && !layoutPending && layout.size
        ? h("svg", { className: "graph-svg", viewBox: `0 0 ${graphViewBox.width} ${graphViewBox.height}`, role: "img", "aria-label": "Graph visualization" },
        h("defs", null, _graphEdgeArrowMarkers()),
        layoutEdges.map((edge, index) => {
          const source = layout.get(edge.source);
          const target = layout.get(edge.target);
          if (!source || !target) return null;
          const relation = String(edge.relation || "");
          const color = GRAPH_RELATION_COLORS[relation] || "var(--panel-border)";
          const sourceNode = layoutNodes.find(node => node.id === edge.source) || null;
          const targetNode = layoutNodes.find(node => node.id === edge.target) || null;
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
          const edgeFocusNodeId = interactionFocusId || treeNavFocusNodeId;
          const edgeTouchesFocus = edgeFocusNodeId
            && (edge.source === edgeFocusNodeId || edge.target === edgeFocusNodeId);
          const edgeInConnectedSubgraph = !interactionFocusId
            || (connectedNodeIds.has(edge.source) && connectedNodeIds.has(edge.target));
          const edgeAdjacent = Boolean(edgeTouchesFocus);
          const edgeHighlightRelationOk = !previewUsesNavRelationsOnly
            || GRAPH_HOVER_HIGHLIGHT_RELATIONS.has(relation);
          const edgeFocused = edgeAdjacent && edgeHighlightRelationOk && edgeInConnectedSubgraph;
          const edgeConnectedToHover = Boolean(previewUsesNavRelationsOnly && edgeAdjacent);
          const edgeSelected = Boolean(treeNavFocusNodeId && !hoveredNodeId && edgeFocused);
          const edgePreview = Boolean(hoveredNodeId && edgeFocused);
          const edgeWeight = Math.max(1, Number(edge.weight || edge.count || 1));
          const edgeVisual = {
            edgePreview,
            edgeSelected,
            edgeFocused,
            edgeConnectedToHover,
            previewNodeId: highlightPreviewNodeId,
          };
          const lineOpacity = _graphEdgeLineOpacity(edgeVisual);
          return h("line", {
            key: `${edge.source}-${edge.target}-${edge.relation}-${index}`,
            x1,
            y1,
            x2,
            y2,
            className: `graph-edge${highlightPreviewNodeId && !edgeFocused && !edgeConnectedToHover ? " graph-edge--dimmed" : ""}${edgeSelected ? " graph-edge--highlighted" : ""}${edgePreview ? " graph-edge--preview" : ""}`,
            stroke: color,
            "marker-end": "url(#graph-arrow)",
            style: {
              color,
              opacity: lineOpacity,
              strokeWidth: _graphEdgeStrokeWidth(edgeVisual, edgeWeight),
            },
            onClick: () => selectNode(edge.source),
          });
        }),
        layoutNodes.map((node, index) => {
          const pos = layout.get(node.id);
          if (!pos) return null;
          const degree = degreeMap.get(node.id) || 0;
          const radius = _graphNodeRadius(node, degree);
          const kind = _graphKindBucket(node.kind);
          const fillColor = _graphNodeFillColor(node, graphNodeColorContext);
          const isSelected = treeNavFocusNodeId === node.id
            || (kind === "community" && selectedCommunityBubbleId === node.id);
          const isHovered = hoveredNodeId === node.id;
          const isConnected = !highlightPreviewNodeId || connectedNodeIds.has(node.id);
          const hasLayoutEdges = nodesWithLayoutEdges.has(node.id);
          const isSoloHover = isHovered && !isSelected && !hasLayoutEdges;
          const showLabel = true;
          return h("g", {
            key: node.id,
            className: `graph-node graph-node--${kind}${isSelected ? " graph-node--selected" : ""}${highlightPreviewNodeId && !isConnected ? " graph-node--dimmed" : ""}${isHovered && !isSelected ? " graph-node--preview" : ""}${isSoloHover ? " graph-node--hover-isolated" : ""}`,
            transform: `translate(${pos.x}, ${pos.y})${isHovered && !isSelected ? (isSoloHover ? " scale(1.1)" : " scale(1.07)") : ""}`,
            onClick: () => hasCommunityOverview && node.kind === "community" ? selectCluster(node.community_id) : selectNode(node.id),
            onMouseEnter: () => setHoveredNodeId(node.id),
            onMouseLeave: () => setHoveredNodeId(current => current === node.id ? "" : current),
          },
            isHovered && !isSelected
              ? h("circle", {
                className: isSoloHover ? "graph-node-hover-ring graph-node-hover-ring--isolated" : "graph-node-hover-ring",
                r: isSoloHover ? radius + 6 : radius + 4,
                fill: "none",
                stroke: isSoloHover ? "rgba(25, 118, 210, 0.65)" : "rgba(25, 118, 210, 0.45)",
                strokeWidth: isSoloHover ? 2.5 : 2,
              })
              : null,
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
              className: "graph-node-core",
              r: radius,
              fill: fillColor,
              stroke: isSelected
                ? "var(--ink)"
                : isHovered
                  ? "rgba(25, 118, 210, 0.85)"
                  : "rgba(255,255,255,0.75)",
              strokeWidth: isSelected ? 3 : isHovered ? 2.25 : 1.5,
              style: { opacity: highlightPreviewNodeId && !isConnected ? 0.26 : isSelected ? 1 : isHovered ? 1 : 0.9 },
            }),
            showLabel
              ? _graphRenderNodeLabel(node, radius)
              : null,
          );
        }),
      )
        : !layoutPending
          ? h("p", { className: "graph-svg-empty muted" }, layoutNodes.length ? "Layout unavailable for the current graph." : "No nodes match the current filters.")
          : null,
      ),
      )
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

// Render a change ID so it wraps only after dashes, never at the kind/slug space.
// Mirrors the table view's dash-split <wbr> approach (dashboard.js ~4133); the Activity
// timeline span is not inside a <td>, so it also needs the scoped `.timeline .wave-change-id`
// wrap rule in dashboard.css.
function renderChangeIdParts(id) {
  const safe = String(id == null ? "" : id);
  return safe.split("-").flatMap((part, i) => {
    // Protect the kind/slug space (e.g. "...bug recent-...") from becoming a break point.
    const text = part.replace(/ /g, "\u00a0");
    return i === 0 ? [text] : ["-", h("wbr", { key: i }), text];
  });
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
              h("span", { className: "wave-change-id", style: { display: "block", marginBottom: "2px", fontSize: "0.85rem" } }, ...renderChangeIdParts(item.change_id)),
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

// renderInline / renderMarkdownish now live in WFDS (see top-of-file destructure).

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
  if (!agents?.length) {
    // Wave 1p35d (1p35l, AC-6): empty Agents panel renders as guidance, not silence.
    // An empty panel previously read as "feature unused"; the real cause is almost
    // always that seed-050 (Init agent surfaces) never ran or that generated docs
    // are missing the `Role:` inclusion gate.
    return h("div", { className: "hero-agents hero-agents--empty" },
      h("h2", { className: "hero-agents-heading" }, "Agents"),
      h("p", { className: "hero-agents-empty-msg" },
        "No agent role docs found. Run ",
        h("strong", null, "Init agent surfaces"),
        " (seed-050) to generate them. Each generated doc must declare ",
        h("code", null, "Role: <role-slug>"),
        " in the header — docs without it are silently skipped.",
      ),
    );
  }
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

// ── Navigation shell: section registry + hash routing + collapsible sidebar ───
// Wave 1p6nl. The registry decouples nav chrome from views; page routing keys off
// location.hash (the 'hashchange' event). GraphPanel keeps its own History-*state*
// breadcrumbs, guarded on `e.state.wfGraph` (dashboard.js popstate handler), so they
// are isolated from this URL-hash routing — no namespacing needed.

const NAV_SECTIONS = [
  { id: "work",  label: "Work",  group: "Work",    icon: "work"  },
  { id: "graph", label: "Graph", group: "Inspect", icon: "graph" },
  // Roadmap (drop-in later): { id: "config", group: "Configure", ... },
  //                          { id: "secrets", group: "Configure", ... },
  //                          { id: "docs", group: "Inspect", ... }.
  // The `group` field is carried now but rendered flat until the set grows (~5+).
];
const NAV_SECTION_IDS = NAV_SECTIONS.map(s => s.id);

// NavIcon / WaveMark now live in WFDS (see top-of-file destructure).

function parseHashView() {
  const raw = (window.location.hash || "").replace(/^#\/?/, "").trim();
  return raw || "work";
}

function useHashRoute(validIds) {
  const [raw, setRaw] = useState(parseHashView);
  useEffect(() => {
    const onHash = () => setRaw(parseHashView());
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);
  const view = validIds.includes(raw) ? raw : "work";
  const navigate = useCallback((id) => {
    if (parseHashView() === id) return;
    window.location.hash = `#/${id}`;
  }, []);
  return [view, navigate];
}

function useSidebarCollapsed() {
  const [collapsed, setCollapsed] = useState(() => {
    try {
      const v = localStorage.getItem("wf-sidebar-collapsed");
      return v === null ? true : v === "1";   // default collapsed
    } catch (_e) { return true; }
  });
  const toggle = useCallback(() => {
    setCollapsed(prev => {
      const next = !prev;
      try { localStorage.setItem("wf-sidebar-collapsed", next ? "1" : "0"); } catch (_e) {}
      return next;
    });
  }, []);
  return [collapsed, toggle];
}

// Sidebar is the dashboard's nav shell (1p6nm ADR 1p6q5). The implementation
// is the shared WFDS.NavSidebar primitive; this thin delegator injects the
// dashboard-local POLL_STEPS and localDateTime helpers it needs for the footer.
function Sidebar(props) {
  return h(WFDS.NavSidebar, { ...props, pollSteps: POLL_STEPS, localDateTime });
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
  const [view, navigate] = useHashRoute(NAV_SECTION_IDS);
  const [sidebarCollapsed, toggleSidebar] = useSidebarCollapsed();

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
    h("div", { className: "app-body" },
      h(Sidebar, {
        sections: NAV_SECTIONS, current: view, collapsed: sidebarCollapsed,
        onToggle: toggleSidebar, onNavigate: navigate,
        project, dark, onToggleDark,
        frameworkVersion, sseConnected, pollIdx, generatedAt: snapshot.generated_at,
      }),
      h("main", { className: "app-main" },
        view === "graph"
          ? h("section", { className: "app-graph", "aria-label": "Graph index" },
              h(GraphPanel, { snapshot }),
            )
          : h("div", { className: "app-main-inner" },
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
                  h(Agents, { agents, onSelectAgent: setSelectedAgent }),
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
            ),
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
  // Wave 1rtju (AC-4): a client staleness watchdog recovers from a silent server stall — an
  // EventSource that stays "connected" (heartbeats keep it open) but stops delivering `update`
  // events because the server watcher wedged. We track the last time real data arrived and, while
  // connected, run a low-frequency safety poll if no update has landed within the bounded window.
  // It stands down the moment updates resume (no double-fetching when SSE is healthy).
  const lastUpdateAtRef = useRef(Date.now());
  const watchdogRef = useRef(null);
  // Bounded window: above the 60s server git-refresh cadence so a healthy idle repo does not trip it
  // every tick; comparable to the server's own _WATCHER_STALL_SECONDS.
  const WATCHDOG_STALE_MS = 90000;
  const WATCHDOG_INTERVAL_MS = 30000;

  useEffect(() => {
    let reconnectDelay = 2000;

    function connect() {
      const es = new EventSource("/api/events");
      esRef.current = es;

      es.addEventListener("update", () => {
        lastUpdateAtRef.current = Date.now();
        if (timerRef.current) { window.clearTimeout(timerRef.current); timerRef.current = null; }
        refresh();
      });
      // Wave 1rtju: an explicit server stall signal — poll immediately (bypasses the wedged watcher)
      // rather than waiting for the watchdog window to elapse.
      es.addEventListener("watcher_status", (ev) => {
        try {
          const data = JSON.parse(ev.data);
          if (data && data.stalled) { refresh(); }
        } catch (_e) { /* ignore malformed payloads */ }
      });
      es.onopen = () => {
        sseActiveRef.current = true;
        setSseConnected(true);
        reconnectDelay = 2000;
        lastUpdateAtRef.current = Date.now();
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
    // Wave 1rtju: the connected-but-silent safety poll. Only fires while SSE reports connected and no
    // update has arrived within WATCHDOG_STALE_MS; a single active fetch keeps the page fresh even if
    // the server watcher is wedged. Re-arms the window so a persistently-stalled server keeps refreshing.
    watchdogRef.current = window.setInterval(() => {
      if (sseActiveRef.current && Date.now() - lastUpdateAtRef.current > WATCHDOG_STALE_MS) {
        lastUpdateAtRef.current = Date.now();
        refresh();
      }
    }, WATCHDOG_INTERVAL_MS);
    return () => {
      if (esRef.current) { esRef.current.close(); esRef.current = null; }
      if (reconnectTimerRef.current) { window.clearTimeout(reconnectTimerRef.current); reconnectTimerRef.current = null; }
      if (watchdogRef.current) { window.clearInterval(watchdogRef.current); watchdogRef.current = null; }
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
