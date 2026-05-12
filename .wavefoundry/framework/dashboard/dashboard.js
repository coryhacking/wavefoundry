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

// ── Status classification ──────────────────────────────────────────────────────

const DONE_STATUSES = new Set(["complete", "completed", "done", "implemented", "approved"]);
function isDone(status) { return DONE_STATUSES.has(String(status || "").toLowerCase()); }
function waveStatus(w) { return String(w.status || "").toLowerCase(); }
function activeWaves(waves)  { return waves.filter(w => waveStatus(w) === "active"); }
function pendingWaves(waves) { return waves.filter(w => waveStatus(w) !== "active" && waveStatus(w) !== "closed" && waveStatus(w) !== "completed"); }

function badgeClass(status) {
  const key = String(status || "unknown").toLowerCase();
  if (["active", "ready", "complete", "completed", "done", "implemented", "approved"].includes(key))
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
  const version = project.framework_version || project.framework_revision || null;
  return h("header", { className: "site-header" },
    h("div", { className: "header-brand" },
      h("div", { className: "header-logo", "aria-hidden": "true" },
        h("div", { className: "header-logo-mark" }),
      ),
      h("span", { className: "header-repo" }, project.name || project.repo_basename || "Repository"),
      version ? h(React.Fragment, null,
        h("span", { className: "header-sep", "aria-hidden": "true" }, "/"),
        h("span", { className: "header-framework" }, `v${version}`),
      ) : null,
    ),
    h("div", { className: "header-actions" },
      h(ThemeToggle, { dark, onToggle: onToggleDark }),
    ),
  );
}

function ProgressRow({ label, done, total, variant }) {
  if (!total) return null;
  const pct = Math.round((done / total) * 100);
  const complete = done >= total;
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
        "aria-label": `${label}: ${pct}%`,
      },
        h("div", { className: "progress-bar-fill", style: { width: `${pct}%` } }),
      ),
    ),
    h("div", { className: "progress-row-fraction" }, `${done}/${total}`),
  );
}

function ProgressCard({ snapshot }) {
  const waves      = snapshot.waves || [];
  const allChanges = snapshot.changes?.in_waves || [];

  const closedWaves = waves.filter(w => waveStatus(w) === "closed").length;
  const totalWaves  = waves.length;
  const closedWaveIds = new Set(waves.filter(w => waveStatus(w) === "closed").map(w => w.wave_id));

  const { done: changesDone, total: changesTotal } = computeProgress(allChanges);

  // Closed-wave changes: all tasks/ACs count as done (wave accepted = work complete).
  // Open-wave changes: use actual checked state.
  const tasksTotal = allChanges.reduce((s, c) => s + (Number(c.tasks_total) || 0), 0);
  const tasksDone  = allChanges.reduce((s, c) =>
    s + (closedWaveIds.has(c.wave_id) ? (Number(c.tasks_total) || 0) : (Number(c.tasks_completed) || 0)), 0);

  const acTotal = allChanges.reduce((s, c) =>
    s + Object.values(c.ac_priority_counts || {}).reduce((a, v) => a + v, 0), 0);
  const acDone = allChanges.reduce((s, c) =>
    s + (closedWaveIds.has(c.wave_id)
      ? Object.values(c.ac_priority_counts  || {}).reduce((a, v) => a + v, 0)
      : Object.values(c.ac_completed_counts || {}).reduce((a, v) => a + v, 0)), 0);

  return h("article", { className: "progress-card" },
    h("div", { className: "progress-header" },
      h("h2", null, "Progress"),
    ),
    h("div", { className: "progress-rows" },
      h(ProgressRow, { label: "Waves",   done: closedWaves, total: totalWaves,   variant: "waves" }),
      h(ProgressRow, { label: "Changes", done: changesDone, total: changesTotal, variant: "changes" }),
      acTotal    ? h(ProgressRow, { label: "ACs",   done: acDone,    total: acTotal,    variant: "acs" })   : null,
      tasksTotal ? h(ProgressRow, { label: "Tasks", done: tasksDone, total: tasksTotal, variant: "tasks" }) : null,
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

function WaveAcs({ acTotals, acDone = {} }) {
  const ordered = ["required", "important", "nice-to-have", "not-this-scope"];
  const entries = ordered.filter(k => acTotals[k]);
  if (!entries.length) return null;
  const total = entries.reduce((s, k) => s + acTotals[k], 0);
  const done  = entries.reduce((s, k) => s + (acDone[k] || 0), 0);
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

function WaveChangeList({ changes }) {
  if (!changes?.length) return null;
  return h("div", { className: "wip-section" },
    h("div", { className: "wip-section-label" }, "Changes"),
    h("ul", { className: "lanes-list" },
      changes.map((c, i) =>
        h("li", { key: i, className: "wave-change-item" },
          h("div", { className: "wave-change-header" },
            h("span", { className: "wave-change-id" }, c.id),
            h("span", { className: "wave-change-title" }, c.title),
          ),
          c.description ? h("div", { className: "wave-change-desc muted" }, c.description) : null,
        )
      ),
    ),
  );
}

function OpenWaveCard({ wave, allChanges, handoffWaveId }) {
  const waveChanges = allChanges.filter(c => c.wave_id === wave.wave_id);
  const { tasksTotal, tasksDone, acTotals, acDone } = waveStats(waveChanges);
  const isHandoff = handoffWaveId && wave.wave_id === handoffWaveId;
  return h("div", { className: "open-wave-card" },
    h("div", { className: "status-row" },
      h("div", null,
        h("strong", { className: "open-wave-id" }, wave.wave_id),
        h("div", { className: "open-wave-title" }, wave.title),
      ),
      h("div", { className: "open-wave-meta" },
        isHandoff ? h("span", { className: "handoff-pill", title: "Current session handoff" }, "↩ handoff") : null,
        h("span", { className: badgeClass(wave.status) }, wave.status),
        h("span", { className: "muted open-wave-count" }, `${wave.change_count} ${p(wave.change_count, "change", "changes")}`),
      ),
    ),
    h(WaveChangeList, { changes: wave.changes }),
    h(WaveAcs, { acTotals, acDone }),
    h(WaveTasks, { tasksTotal, tasksDone }),
    h(WaveEvidence, { evidence: wave.review_evidence }),
    h(WaveLanes, { participants: wave.participants }),
  );
}

function PendingWaveRow({ wave }) {
  return h("div", { className: "pending-wave-row" },
    h("div", { className: "pending-wave-left" },
      h("span", { className: "open-wave-id" }, wave.wave_id),
      wave.title ? h("span", { className: "pending-wave-title" }, wave.title) : null,
    ),
    h("div", { className: "open-wave-meta" },
      h("span", { className: badgeClass(wave.status) }, wave.status),
      h("span", { className: "muted open-wave-count" }, `${wave.change_count} ${p(wave.change_count, "change", "changes")}`),
    ),
  );
}

function WavesCard({ waves, allChanges, handoffWaveId }) {
  const active  = activeWaves(waves);
  const pending = pendingWaves(waves);
  const closed  = waves.filter(w => waveStatus(w) === "closed").length;

  return h("article", { className: "table-card", "aria-label": "Waves" },
    h("h2", null, "Waves"),
    active.length
      ? active.map(wave => h(OpenWaveCard, { key: wave.wave_id, wave, allChanges, handoffWaveId }))
      : h("div", { className: "empty-state" }, "No active waves."),
    pending.length ? h(React.Fragment, null,
      h("div", { className: "waves-section-label" }, `${pending.length} pending`),
      pending.map(wave => h(PendingWaveRow, { key: wave.wave_id, wave })),
    ) : null,
    closed ? h("p", { className: "muted", style: { marginTop: "var(--space-3)" } },
      `${closed} closed ${p(closed, "wave", "waves")}.`
    ) : null,
  );
}

function Metrics({ snapshot, onWavesClick, onChangesClick, onAcsClick, onTasksClick, onFilesClick, onIndexClick }) {
  const waves = snapshot.waves || [];
  const inWaves = snapshot.changes?.in_waves || [];
  const git = snapshot.git || {};
  const health = snapshot.health || {};
  // active = on active wave(s); pending = on non-active waves + staged plans not yet in a wave
  const staged = snapshot.changes?.staged || [];

  const waveActive  = activeWaves(waves).length;
  const wavePending = pendingWaves(waves).length;
  const waveTotal   = waves.length;

  const activeWaveIds  = new Set(activeWaves(waves).map(w => w.wave_id));
  const pendingWaveIds = new Set(pendingWaves(waves).map(w => w.wave_id));
  const activeChanges  = inWaves.filter(c => activeWaveIds.has(c.wave_id));
  const pendingChanges = [...inWaves.filter(c => pendingWaveIds.has(c.wave_id)), ...staged];
  const changeActive   = activeChanges.length;
  const changePending  = pendingChanges.length;
  const changeTotal    = inWaves.length + staged.length;

  const allTasksTotal   = [...inWaves, ...staged].reduce((s, c) => s + (Number(c.tasks_total) || 0), 0);
  const allTasksActive  = activeChanges.reduce((s, c) => s + Math.max(0, (Number(c.tasks_total) || 0) - (Number(c.tasks_completed) || 0)), 0);
  const allTasksPending = pendingChanges.reduce((s, c) => s + (Number(c.tasks_total) || 0), 0);

  const countAcs = (changes) => changes.reduce((s, c) =>
    s + Object.values(c.ac_priority_counts || {}).reduce((a, v) => a + v, 0), 0);
  const countCompletedAcs = (changes) => changes.reduce((s, c) =>
    s + Object.values(c.ac_completed_counts || {}).reduce((a, v) => a + v, 0), 0);
  const acTotal   = countAcs([...inWaves, ...staged]);
  const acActive  = Math.max(0, countAcs(activeChanges)  - countCompletedAcs(activeChanges));
  const acPending = Math.max(0, countAcs(pendingChanges) - countCompletedAcs(pendingChanges));
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
    { label: p(waveActive,  "Active wave",   "Active waves"),   value: waveActive,   note: `${wavePending} pending · ${waveTotal} total`,          onClick: onWavesClick,   variant: "waves" },
    { label: p(changeActive,"Active change", "Active changes"), value: changeActive, note: `${changePending} pending · ${changeTotal} total`,       onClick: onChangesClick, variant: "changes" },
    { label: p(acActive,    "Active AC",     "Active ACs"),     value: acActive,     note: `${acPending} pending · ${acTotal} total`,               onClick: onAcsClick,     variant: "acs" },
    { label: p(allTasksActive, "Active task","Active tasks"),   value: allTasksActive, note: `${allTasksPending} pending · ${allTasksTotal} total`, onClick: onTasksClick,   variant: "tasks" },
    { label: p(gitFileCount, "File changed", "Files changed"), value: gitFileCount, note: fileNote, onClick: onFilesClick, variant: "files" },
    (() => {
      const projectIdx = health.index?.project || {};
      const frameworkIdx = health.index?.framework || {};
      const totalChunks = (projectIdx.doc_chunks || 0) + (projectIdx.code_chunks || 0) + (frameworkIdx.doc_chunks || 0) + (frameworkIdx.code_chunks || 0);
      const totalFiles = (projectIdx.files_indexed || 0) + (frameworkIdx.files_indexed || 0);
      const buildStatus = projectIdx.build_status === "running" || frameworkIdx.build_status === "running"
        ? "running"
        : projectIdx.build_status === "failed" || frameworkIdx.build_status === "failed"
          ? "failed"
          : null;
      const isStale = projectIdx.stale === true || frameworkIdx.stale === true;
      const state = buildStatus === "running" ? "running" : buildStatus === "failed" ? "failed" : isStale ? "stale" : null;
      const statusText = buildStatus === "running"
        ? "Indexing…"
        : buildStatus === "failed"
          ? "Index build failed"
          : isStale
            ? "Stale"
            : (!projectIdx.present && !frameworkIdx.present)
              ? "Not yet built"
              : null;
      const note = h(React.Fragment, null,
        h("div", { className: "metric-subnote" }, `files / ${totalChunks.toLocaleString()} chunks`),
        h("div", { className: "metric-status-line" }, statusText || "\u00A0"),
      );
      const value = totalFiles ? totalFiles.toLocaleString() : (buildStatus === "running" ? "Indexing…" : "Missing");
      return { label: "Semantic Index", value, note, state, onClick: onIndexClick, variant: "index" };
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
    const { path, status = "modified" } = typeof entry === "string" ? { path: entry } : entry;
    const parts = path.split("/");
    let node = root;
    for (let i = 0; i < parts.length - 1; i++) {
      if (typeof node[parts[i]] !== "object" || node[parts[i]] === null) node[parts[i]] = {};
      node = node[parts[i]];
    }
    node[parts[parts.length - 1]] = status;
  }
  return root;
}

function FileTree({ node, depth = 0 }) {
  const entries = Object.entries(node).sort(([ak, av], [bk, bv]) => {
    const aDir = typeof av === "object" && av !== null;
    const bDir = typeof bv === "object" && bv !== null;
    if (aDir !== bDir) return bDir ? 1 : -1;
    return ak.localeCompare(bk);
  });
  return h("ul", { className: "file-tree", style: depth === 0 ? {} : { paddingLeft: "1.1em" } },
    entries.map(([name, child]) =>
      typeof child === "object" && child !== null
        ? h("li", { key: name, className: "file-tree-dir" },
            h("span", { className: "file-tree-dir-name" }, name + "/"),
            h(FileTree, { node: child, depth: depth + 1 }),
          )
        : h("li", { key: name, className: `file-tree-file file-tree-file--${child}` }, name)
    ),
  );
}

function DialogFrame({ className, title, subtitle, onClose, children }) {
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
        subtitle ? h("span", { className: "muted", style: { fontSize: "0.85rem" } }, subtitle) : null,
      ),
      h("button", { className: "agent-dialog-close", "aria-label": "Close", onClick: onClose }, "×"),
    ),
    h("div", { className: "agent-dialog-body" }, children),
  );
}

function WavesDialog({ snapshot, onClose }) {
  const waves = snapshot.waves || [];
  const active = activeWaves(waves);
  return h(DialogFrame, { title: p(active.length, "Active Wave", "Active Waves"), onClose },
    active.length ? active.map(wave =>
      h("div", { key: wave.wave_id, className: "metric-dialog-card" },
        h("div", { className: "metric-dialog-card-header" },
          h("span", { className: "open-wave-id" }, wave.wave_id),
          h("span", { className: badgeClass(wave.status) }, wave.status),
        ),
        h("div", { className: "metric-dialog-card-title" }, wave.title),
        wave.objective ? h("div", { className: "metric-dialog-card-desc" }, wave.objective) : null,
      )
    ) : h("div", { className: "empty-state" }, "No active waves."),
  );
}

function ChangesDialog({ snapshot, onClose }) {
  const waves = snapshot.waves || [];
  const inWaves = snapshot.changes?.in_waves || [];
  const activeWaveIds = new Set(activeWaves(waves).map(w => w.wave_id));
  const active = inWaves.filter(c => activeWaveIds.has(c.wave_id));
  return h(DialogFrame, { title: p(active.length, "Active Change", "Active Changes"), onClose },
    active.length ? active.map(c =>
      h("div", { key: c.change_id, className: "metric-dialog-card" },
        h("div", { className: "metric-dialog-card-header" },
          h("span", { className: "wave-change-id" }, c.change_id),
          c.status ? h("span", { className: badgeClass(c.status) }, c.status) : null,
        ),
        h("div", { className: "metric-dialog-card-title" }, c.title),
        c.description ? h("div", { className: "metric-dialog-card-desc" }, c.description) : null,
      )
    ) : h("div", { className: "empty-state" }, "No active changes."),
  );
}

function AcsDialog({ snapshot, onClose }) {
  const waves = snapshot.waves || [];
  const inWaves = snapshot.changes?.in_waves || [];
  const activeWaveIds = new Set(activeWaves(waves).map(w => w.wave_id));
  const activeChanges = inWaves.filter(c => activeWaveIds.has(c.wave_id));
  const PRIORITY_BADGE = { required: "status-blocked", important: "status-warn", "nice-to-have": "status-neutral", unknown: "status-unknown" };
  return h(DialogFrame, { title: "Active ACs", onClose },
    activeChanges.length ? activeChanges.map(c => {
      const items = (c.ac_items || []).filter(ac => ac.priority !== "not-this-scope");
      if (!items.length) return null;
      return h("div", { key: c.change_id, className: "metric-dialog-card" },
        h("div", { className: "metric-dialog-card-header" },
          h("span", { className: "wave-change-id" }, c.change_id),
        ),
        h("div", { className: "metric-dialog-card-title" }, c.title),
        h("div", { className: "metric-dialog-ac-rows" },
          items.map((ac, i) =>
            h("div", { key: i, className: `metric-dialog-ac-item${ac.done ? " metric-dialog-ac-item--done" : ""}` },
              h("span", { className: `metric-dialog-ac-check${ac.done ? " metric-dialog-ac-check--done" : ""}` }, ac.done ? "✓" : "○"),
              h("span", { className: "metric-dialog-ac-text" }, ac.text),
              ac.priority && ac.priority !== "unknown"
                ? h("span", { className: `status-badge ${PRIORITY_BADGE[ac.priority] || "status-unknown"} metric-dialog-ac-priority` }, ac.priority)
                : null,
            )
          ),
        ),
      );
    }).filter(Boolean) : h("div", { className: "empty-state" }, "No active ACs."),
  );
}

function TasksDialog({ snapshot, onClose }) {
  const waves = snapshot.waves || [];
  const inWaves = snapshot.changes?.in_waves || [];
  const activeWaveIds = new Set(activeWaves(waves).map(w => w.wave_id));
  const activeChanges = inWaves.filter(c => activeWaveIds.has(c.wave_id));
  return h(DialogFrame, { title: "Active Tasks", onClose },
    activeChanges.length ? activeChanges.map(c => {
      const items = c.tasks_items || [];
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
              h("span", { className: "metric-dialog-ac-text" }, task.label),
            )
          ),
        ),
      );
    }).filter(Boolean) : h("div", { className: "empty-state" }, "No active tasks."),
  );
}

function FilesDialog({ title, files, emptyMessage, onClose }) {
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
  const tree = buildFileTree(files);

  return h("dialog", { ref: dialogRef, className: "agent-dialog files-dialog", onClick: handleBackdropClick },
    h("div", { className: "agent-dialog-header" },
      h("div", null,
        h("h2", { className: "agent-dialog-title" }, title),
        h("span", { className: "muted", style: { fontSize: "0.85rem" } }, `${files.length} ${files.length === 1 ? "file" : "files"}`),
      ),
      h("button", { className: "agent-dialog-close", "aria-label": "Close", onClick: onClose }, "×"),
    ),
    h("div", { className: "agent-dialog-body" },
      files.length
        ? h(FileTree, { node: tree })
        : h("div", { className: "empty-state" }, emptyMessage || "No files."),
    ),
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

  const proj = health?.index?.project   || {};
  const fw   = health?.index?.framework || {};

  return h("dialog", { ref: dialogRef, className: "agent-dialog index-dialog", onClick: handleBackdropClick },
    h("div", { className: "agent-dialog-header" },
      h("h2", { className: "agent-dialog-title" }, "Semantic Index"),
      h("button", { className: "agent-dialog-close", "aria-label": "Close", onClick: onClose }, "×"),
    ),
    h("div", { className: "agent-dialog-body" },
      h(IndexSection, { label: "Project", idx: proj }),
      (fw.present || fw.built_at) ? h(IndexSection, { label: "Framework", idx: fw }) : null,
    ),
  );
}

function IndexSection({ label, idx }) {
  const buildStatus = idx.build_status;
  const buildBadge = (buildStatus === "running")
    ? h("div", { className: "index-build-status" },
        h("span", { className: "index-build-badge index-build-badge--running" }, "Indexing…"),
      )
    : buildStatus === "failed"
      ? h("div", { className: "index-build-status" },
          h("span", { className: "index-build-badge index-build-badge--failed" }, "Index build failed"),
        )
      : idx.stale === true
        ? h("div", { className: "index-build-status" },
            h("span", { className: "index-build-badge index-build-badge--stale" }, "Stale"),
          )
        : idx.stale === false
          ? h("div", { className: "index-build-status" },
              h("span", { className: "index-build-badge index-build-badge--current" }, "Up to date"),
            )
          : null;

  if (!idx.present) {
    return h("div", { className: "index-section index-section--missing" },
      h("div", { className: "index-section-label" }, label),
      h("span", { className: "index-stat-missing" }, "not built"),
      buildBadge,
    );
  }
  const totalChunks = (idx.doc_chunks || 0) + (idx.code_chunks || 0);
  const age = relativeAge(idx.built_at);
  const elapsed = idx.elapsed_seconds
    ? (idx.elapsed_seconds >= 60
        ? `${Math.round(idx.elapsed_seconds / 60)}m ${idx.elapsed_seconds % 60}s`
        : `${idx.elapsed_seconds}s`)
    : null;
  return h("div", { className: "index-section" },
    h("div", { className: "index-section-label" }, label),
    h("div", { className: "index-stat-grid" },
      h("div", { className: "index-stat" },
        h("span", { className: "index-stat-value" }, (idx.files_indexed || 0).toLocaleString()),
        h("span", { className: "index-stat-label" }, "files"),
      ),
      h("div", { className: "index-stat" },
        h("span", { className: "index-stat-value" }, totalChunks.toLocaleString()),
        h("span", { className: "index-stat-label" }, "chunks"),
      ),
      idx.doc_chunks ? h("div", { className: "index-stat" },
        h("span", { className: "index-stat-value" }, idx.doc_chunks.toLocaleString()),
        h("span", { className: "index-stat-label" }, "doc"),
      ) : null,
      idx.code_chunks ? h("div", { className: "index-stat" },
        h("span", { className: "index-stat-value" }, idx.code_chunks.toLocaleString()),
        h("span", { className: "index-stat-label" }, "code"),
      ) : null,
    ),
    h("div", { className: "index-meta-row" },
      age    ? h("span", { className: "index-meta-pill" }, `built ${age}`) : null,
      elapsed ? h("span", { className: "index-meta-pill" }, `${elapsed}${idx.mode ? ` ${idx.mode}` : ""}`) : null,
      idx.model ? h("span", { className: "index-meta-pill index-meta-pill--model" }, idx.model) : null,
    ),
    buildBadge,
  );
}

function ChangesTable({ changes, title }) {
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
                h("div", { className: "wave-change-id" },
                  c.change_id.split("-").flatMap((part, i) => i === 0 ? [part] : ["-", h("wbr", { key: i }), part]),
                ),
                h("div", { className: "wave-change-title" }, c.title),
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

function Activity({ activity }) {
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
          items.map((item, i) =>
            h("li", { key: i },
              h("span", { className: "wave-change-id", style: { display: "block", marginBottom: "2px", fontSize: "0.85rem" } }, item.change_id),
              item.title ? h("div", { className: "wave-change-title", style: { marginBottom: "var(--space-1)" } }, item.title) : null,
              h("div", null, item.update || ""),
              item.evidence ? h("div", { className: "muted" }, item.evidence) : null,
            )
          ),
        ),
      )
    ),
  );
}

function renderMarkdownish(text) {
  const lines = text.split("\n");
  const result = [];
  let listItems = [];
  let key = 0;

  const flushList = () => {
    if (listItems.length) {
      result.push(h("ul", { key: key++ }, listItems));
      listItems = [];
    }
  };

  for (const raw of lines) {
    const line = raw.trim();
    if (line.startsWith("- ")) {
      listItems.push(h("li", { key: key++ }, line.slice(2)));
    } else {
      flushList();
      if (line) result.push(h("p", { key: key++ }, line));
    }
  }
  flushList();
  return result;
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
    operate: "Operate", specialist: "Specialist", journal: "Journal",
  }[agent.category] || agent.category;

  return h("dialog", { ref: dialogRef, className: "agent-dialog", onClick: handleBackdropClick },
    h("div", { className: `agent-dialog-header agent-dialog-header--${agent.category}` },
      h("div", null,
        h("h2", { className: "agent-dialog-title" }, agent.name),
        h("span", { className: `hero-agent-pill hero-agent-pill--${agent.category}` }, categoryLabel),
        agent.status !== "active" ? h("span", { className: badgeClass(agent.status) }, agent.status) : null,
      ),
      h("button", { className: "agent-dialog-close", "aria-label": "Close", onClick: onClose }, "×"),
    ),
    h("div", { className: "agent-dialog-body" },
      (agent.details || []).map((d, i) =>
        h("section", { key: i, className: "agent-detail-section" },
          h("h3", null, d.heading),
          h("div", { className: "agent-detail-body" }, renderMarkdownish(d.body)),
        )
      ),
    ),
  );
}

function Agents({ agents, onSelectAgent }) {
  if (!agents?.length) return null;
  const categories = ["build", "review", "coordinate", "operate", "specialist"];
  const labels = {
    build: "Build", review: "Review", coordinate: "Coordinate",
    operate: "Operate", specialist: "Specialist", journal: "Journal",
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
              title: a.usage_count
                ? `Used in ${a.usage_count} ${p(a.usage_count, "wave", "waves")}`
                : labels[a.category],
            },
              a.name,
              a.usage_count
                ? h("span", { className: "agent-pill-count", "aria-label": `${a.usage_count} waves` }, a.usage_count)
                : null,
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
  const [showWaves, setShowWaves] = useState(false);
  const [showChanges, setShowChanges] = useState(false);
  const [showAcs, setShowAcs] = useState(false);
  const [showTasks, setShowTasks] = useState(false);
  const [showIndex, setShowIndex] = useState(false);
  const [showAllFiles, setShowAllFiles] = useState(false);

  const project    = snapshot.project    || {};
  const waves      = snapshot.waves      || [];
  const allChanges = snapshot.changes?.in_waves || [];
  const agents     = snapshot.agents     || [];
  const handoffWaveId = snapshot.activity?.session_handoff_active_wave || "";

  const openOrClosedIds = new Set(
    waves.filter(w => waveStatus(w) === "active" || waveStatus(w) === "closed").map(w => w.wave_id)
  );
  const pendingChanges = [
    ...allChanges.filter(c => !openOrClosedIds.has(c.wave_id)),
    ...(snapshot.changes?.staged || []),
  ];

  return h(React.Fragment, null,
    h(Header, { snapshot, dark, onToggleDark }),
    h("main", { className: "shell" },
      h("section", { className: "hero", "aria-label": "Project overview" },
        h("article", { className: "hero-card" },
          h("div", { className: "hero-meta" },
            h("span", { className: "meta-pill" }, `Repository: ${project.repo_basename || ""}`),
            h(GitPills, { git: snapshot.git }),
          ),
          h(Metrics, { snapshot,
            onWavesClick:   () => setShowWaves(true),
            onChangesClick: () => setShowChanges(true),
            onAcsClick:     () => setShowAcs(true),
            onTasksClick:   () => setShowTasks(true),
            onFilesClick:   () => setShowAllFiles(true),
            onIndexClick:   () => setShowIndex(true),
          }),
          h(ProgressCard, { snapshot }),
          agents.length ? h(Agents, { agents, onSelectAgent: setSelectedAgent }) : null,
        ),
      ),

      h("section", { className: "content-grid", "aria-label": "Project details" },
        h("div", { className: "card-grid" },
          h(WavesCard, { waves, allChanges, handoffWaveId }),
          h(ChangesTable, { changes: [...pendingChanges].reverse(), title: p(pendingChanges.length, "Pending change", "Pending changes") }),
        ),
        h("div", { className: "card-grid" },
          h("article", { className: "timeline-card", "aria-label": "Recent activity" },
            h("h2", { className: "panel-heading" }, "Recent changes"),
            h(Activity, { activity: snapshot.activity }),
          ),
        ),
      ),

      h("footer", { className: "site-footer" },
        h("span", null,
          `Updated ${localDateTime(snapshot.generated_at)} · `,
          sseConnected
            ? h("span", { className: "sse-live", title: "Server-sent events connected — updates are pushed in real time" }, "Live")
            : `Next refresh in ${POLL_STEPS[pollIdx] / 1000}s`,
        ),
      ),
    ),
    selectedAgent ? h(AgentDialog, { agent: selectedAgent, onClose: () => setSelectedAgent(null) }) : null,
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
