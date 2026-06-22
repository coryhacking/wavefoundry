/*
 * Wavefoundry Design System primitives — WFDS
 * ============================================
 *
 * Extracted from the dashboard monolith (wave 1p75h / change 1p72v-ref) as the
 * maintained, reusable primitive layer for the local dashboard and the future
 * claude.ai/design sync.
 *
 * CONSUMPTION MODEL (locked operator decision: no-build script-tag global):
 *   - This is plain, no-build JavaScript. It is loaded via a <script> tag in
 *     dashboard.html BEFORE dashboard.js and assigns every primitive onto the
 *     global `window.WFDS`. The dashboard consumes them via
 *     `const { Badge, Pill, ProgressBar, ... } = window.WFDS;`
 *   - It is UMD-React-compatible: it reads the same `React` UMD global the
 *     dashboard uses (`window.React`) and aliases `createElement` to `h`, so it
 *     needs no bundler or build step to run the dashboard.
 *
 * ESBUILD BUNDLABILITY (AC-1, future sync — NOT required to run the dashboard):
 *   - The whole module body is wrapped in a single factory `defineWFDS(React)`
 *     and the public surface is the `WFDS` object returned from it. A future
 *     downstream sync can `esbuild`-bundle this file (e.g. wrap as an ESM/IIFE
 *     entry that calls `defineWFDS(React)` and re-exports the result) without
 *     touching the dashboard. To keep that path open the file references React
 *     only through the injected `React` parameter — there are no hard globals in
 *     the primitive bodies. No build dependency or build step is introduced here.
 *
 * "Extract, don't invent": every primitive below is the exact implementation
 * (markup + classNames + behavior) that previously lived inline in dashboard.js.
 * The unified primitives (Badge, Pill, Chip, Card, Table, EmptyState,
 * SectionLabel) codify className conventions that were used inline; they emit
 * the same markup/classNames the dashboard already renders. See
 * docs/design-system/components/ for the contract specs.
 */
(function (root) {
  "use strict";

  function defineWFDS(React) {
    const h = React.createElement;
    const { useState, useEffect, useRef, useCallback } = React;

    // ── Icons ────────────────────────────────────────────────────────────────
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

    function NavIcon({ name }) {
      const kids = name === "graph"
        ? [
            h("circle", { cx: 5,  cy: 6,  r: 2 }),
            h("circle", { cx: 18, cy: 8,  r: 2 }),
            h("circle", { cx: 9,  cy: 18, r: 2 }),
            h("line", { x1: 6.7,  y1: 7,   x2: 16.4, y2: 7.6 }),
            h("line", { x1: 6,    y1: 7.8, x2: 8.4,  y2: 16.3 }),
            h("line", { x1: 10.8, y1: 17,  x2: 16.5, y2: 9.5 }),
          ]
        : [ // "work"
            h("rect", { x: 3,  y: 3,  width: 7, height: 9,  rx: 1.5 }),
            h("rect", { x: 14, y: 3,  width: 7, height: 5,  rx: 1.5 }),
            h("rect", { x: 14, y: 11, width: 7, height: 10, rx: 1.5 }),
            h("rect", { x: 3,  y: 15, width: 7, height: 6,  rx: 1.5 }),
          ];
      return h("svg", {
        className: "nav-icon", viewBox: "0 0 24 24", width: 20, height: 20,
        "aria-hidden": "true", fill: "none", stroke: "currentColor",
        strokeWidth: 1.9, strokeLinecap: "round", strokeLinejoin: "round",
      }, ...kids);
    }

    function WaveMark() {
      // Wavefoundry mark: a sine wave between code brackets `< >` with an AI node on
      // the crest — wave + software-engineering + AI. Rendered white on the accent tile.
      return h("svg", {
        className: "wave-mark", viewBox: "0 0 24 24", width: "100%", height: "100%",
        fill: "none", stroke: "currentColor", strokeWidth: 2,
        strokeLinecap: "round", strokeLinejoin: "round", "aria-hidden": "true",
      },
        h("polyline", { points: "7 5 3.5 12 7 19" }),                // <  software
        h("polyline", { points: "17 5 20.5 12 17 19" }),             // >
        h("path", { d: "M8.2 13.9 Q10.1 8.4 12 13.9 T15.8 13.9" }),  // wave
        h("circle", { cx: 10.05, cy: 9.4, r: 1.5, fill: "currentColor", stroke: "none" }), // AI node
      );
    }

    // `Icon` namespace — the named SVG glyphs the dashboard uses.
    const Icon = { Sun: SunIcon, Moon: MoonIcon, Nav: NavIcon, WaveMark };

    // ── ThemeToggle ────────────────────────────────────────────────────────────
    function ThemeToggle({ dark, onToggle }) {
      return h("button", {
        className: "theme-toggle",
        onClick: onToggle,
        "aria-label": dark ? "Switch to light mode" : "Switch to dark mode",
        title: dark ? "Switch to light mode" : "Switch to dark mode",
      }, dark ? h(SunIcon) : h(MoonIcon));
    }

    // ── Badge (unifies StateBadge / .status-badge convention) ───────────────────
    // `badgeClass(status)` maps a lifecycle status to the .status-badge variant
    // className. Badge renders a status pill using it. This is the exact mapping
    // the dashboard used inline via `h("span", { className: badgeClass(s) }, s)`.
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

    function Badge({ status, label, title, className }) {
      const cls = [badgeClass(status), className].filter(Boolean).join(" ");
      return h("span", { className: cls, title }, label != null ? label : status);
    }
    Badge.classFor = badgeClass;

    // ── Pill (unifies meta / git / index / handoff pills) ───────────────────────
    // Emits the `meta-pill`-style span convention. `variant` appends a modifier
    // class (e.g. "git-branch-pill"); pass a full className via `className` for
    // bespoke pills.
    function Pill({ variant, className, title, children, ...rest }) {
      const cls = ["meta-pill", variant && variant, className].filter(Boolean).join(" ");
      return h("span", { className: cls, title, ...rest }, children);
    }

    // ── Chip (small inline tag, e.g. ac-chip) ───────────────────────────────────
    function Chip({ className, title, children }) {
      const cls = ["chip", className].filter(Boolean).join(" ");
      return h("span", { className: cls, title }, children);
    }

    // ── ProgressBar (from ProgressRow) ──────────────────────────────────────────
    function ProgressBar({ label, done, total, variant }) {
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

    // ── Sparkline (from MiniGraph) ──────────────────────────────────────────────
    function Sparkline({ done, total, label, variant }) {
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

    // ── Card (panel / hero / table-card surface) ────────────────────────────────
    // The dashboard renders cards as `<article>`/`<div>` with surface classNames
    // (panel-card, hero-card, metric-dialog-card, …). Card emits that convention.
    function Card({ as, className, children, ...rest }) {
      const tag = as || "article";
      const cls = ["card", className].filter(Boolean).join(" ");
      return h(tag, { className: cls, ...rest }, children);
    }

    // ── Dialog (from DialogFrame) ───────────────────────────────────────────────
    function Dialog({ className, title, subtitle, meta, onClose, children }) {
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

    // ── Table ───────────────────────────────────────────────────────────────────
    // Thin structural table wrapper emitting the dashboard's table markup. The
    // dashboard's domain tables (ChangesTable, markdown tables) keep their own
    // rich cell rendering; Table is the reusable shell for simple head+rows data.
    function Table({ className, head, rows }) {
      const cls = className || undefined;
      return h("table", { className: cls },
        head ? h("thead", null, h("tr", null, head.map((c, i) => h("th", { key: i }, c)))) : null,
        h("tbody", null,
          (rows || []).map((row, i) =>
            h("tr", { key: i }, row.map((cell, j) => h("td", { key: j }, cell)))
          ),
        ),
      );
    }

    // ── FileTree (+ buildFileTree) ──────────────────────────────────────────────
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

    // ── DiffView (the diff-rendering core of DiffDialog) ────────────────────────
    // Renders a parsed unified-diff body. The dashboard's DiffDialog wraps this in
    // a Dialog with fetch; DiffView is the reusable presentation primitive.
    function DiffView({ text }) {
      if (text === null || text === undefined) return h("div", { className: "empty-state" }, "Loading…");
      const trimmed = String(text).trim();
      if (!trimmed) return h("div", { className: "empty-state" }, "No changes.");
      const lines = String(text).split("\n").filter(line =>
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
    }

    // ── EmptyState ──────────────────────────────────────────────────────────────
    // Codifies the `empty-state` convention the dashboard renders inline.
    function EmptyState({ className, children }) {
      const cls = ["empty-state", className].filter(Boolean).join(" ");
      return h("div", { className: cls }, children);
    }

    // ── SectionLabel / Eyebrow ──────────────────────────────────────────────────
    // The small uppercase section label convention (e.g. wip-section-label).
    function SectionLabel({ className, children }) {
      const cls = ["section-label", className].filter(Boolean).join(" ");
      return h("div", { className: cls }, children);
    }
    const Eyebrow = SectionLabel;

    // ── Markdown / Prose (from renderInline + renderMarkdownish) ────────────────
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

    // `Markdown`/`Prose` render markdown text into the prose body.
    function Markdown({ text }) { return renderMarkdownish(String(text || "")); }
    const Prose = Markdown;

    // ── NavSidebar (from Sidebar) ───────────────────────────────────────────────
    function NavSidebar({ sections, current, collapsed, onToggle, onNavigate, project, dark, onToggleDark, frameworkVersion, sseConnected, pollIdx, generatedAt, pollSteps, localDateTime }) {
      const repoName = (project && (project.name || project.repo_basename)) || "Repository";
      const POLL_STEPS = pollSteps || [];
      const fmtTime = typeof localDateTime === "function" ? localDateTime : (x) => x;
      // Show the major.minor version in the footer; keep the full version
      // (with build metadata) in the tooltip.
      const fullVersion = String(frameworkVersion || "");
      const shortVersion = fullVersion.split("+")[0].split(".").slice(0, 2).join(".") || fullVersion;
      return h("aside", {
        className: `sidebar ${collapsed ? "sidebar--collapsed" : "sidebar--expanded"}`,
        "aria-label": "Primary navigation",
      },
        // The brand (logo + repo name) doubles as the collapse/expand toggle.
        // When expanded, the theme toggle sits at the top-right beside the title;
        // when collapsed it drops to the footer (below) so it stays reachable.
        h("div", { className: "sidebar-brand-row" },
          h("button", {
            type: "button", className: "sidebar-brand", onClick: onToggle,
            "aria-label": collapsed ? `${repoName} — expand navigation` : `${repoName} — collapse navigation`,
            "aria-expanded": collapsed ? "false" : "true",
            "data-tooltip": collapsed ? repoName : undefined,
          },
            h("span", { className: "sidebar-brand-logo", "aria-hidden": "true" }, h(WaveMark)),
            h("span", { className: "sidebar-brand-name" }, repoName),
          ),
          collapsed ? null : h(ThemeToggle, { dark, onToggle: onToggleDark }),
        ),
        h("nav", { className: "sidebar-nav", "aria-label": "Sections" },
          sections.map(s =>
            h("button", {
              key: s.id, type: "button",
              className: `nav-item ${current === s.id ? "nav-item--active" : ""}`,
              onClick: () => onNavigate(s.id),
              "aria-label": s.label,
              "aria-current": current === s.id ? "page" : undefined,
              "data-tooltip": collapsed ? s.label : undefined,
            },
              h("span", { className: "nav-item-icon" }, h(NavIcon, { name: s.icon })),
              h("span", { className: "nav-item-label" }, s.label),
            ),
          ),
        ),
        // Footer: collapsed → just the theme toggle (the brand-row copy is hidden);
        // expanded → version on the left (major.minor, full build in the tooltip)
        // and the live/refresh status on the right.
        h("div", { className: "sidebar-footer" },
          collapsed
            ? h(ThemeToggle, { dark, onToggle: onToggleDark })
            : h("div", { className: "sidebar-footer-meta" },
                h("span", { className: "site-footer-brand", title: `Wavefoundry ${fullVersion}` }, `Wavefoundry v${shortVersion}`),
                sseConnected
                  ? h("span", { className: "sse-live", title: generatedAt ? `Updated ${fmtTime(generatedAt)}` : "Server-sent events connected — updates are pushed in real time" }, "Live")
                  : h("span", { className: "site-footer-refresh", title: generatedAt ? `Updated ${fmtTime(generatedAt)}` : undefined }, `Next refresh in ${POLL_STEPS[pollIdx] / 1000}s`),
              ),
        ),
      );
    }

    // ── Public surface ──────────────────────────────────────────────────────────
    return {
      // Icons
      Icon, SunIcon, MoonIcon, NavIcon, WaveMark,
      // Controls
      ThemeToggle,
      // Status / tags
      Badge, badgeClass, Pill, Chip,
      // Progress / data-viz
      ProgressBar, Sparkline,
      // Surfaces / overlays
      Card, Dialog, Table,
      // Files / diff
      FileTree, buildFileTree, DiffView,
      // States / labels
      EmptyState, SectionLabel, Eyebrow,
      // Navigation
      NavSidebar,
      // Prose / markdown
      Prose, Markdown, renderMarkdownish, renderInline,
    };
  }

  // No-build global attach (UMD-React-compatible). esbuild downstream can call
  // defineWFDS(React) directly; here we attach against the page's React global.
  const React = root.React;
  if (!React) {
    throw new Error("WFDS requires React (UMD global) to be loaded first.");
  }
  root.WFDS = defineWFDS(React);
  // Expose the factory for downstream bundlers that inject their own React.
  root.WFDS.defineWFDS = defineWFDS;
})(typeof window !== "undefined" ? window : this);
