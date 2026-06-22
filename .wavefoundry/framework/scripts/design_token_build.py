#!/usr/bin/env python3
"""Built-in DTCG -> framework-export token transform (wave 12atj).

This module is the *canonical, tool-agnostic* token build engine for the
design-system pipeline. It reads the DTCG token source under
``<design-root>/tokens/`` and emits framework-specific outputs under
``<design-root>/exports/``:

    exports/css/tokens.css        CSS custom properties (light base + dark override block)
    exports/tailwind/theme.config.js  Tailwind theme.extend config (+ dark variants)
    exports/ts/tokens.ts          Typed token constants (per-mode maps)
    exports/json/tokens.json      Flat resolved key -> value map (aliases resolved)

Design constraints (see change doc 12atj):

* **Extract, don't invent.** Every emitted value is derived from the DTCG
  source. Nothing is hand-authored or defaulted.
* **Deterministic + idempotent.** Output is sorted by token path; re-running on
  an unchanged source produces byte-identical files (the only volatile content
  is an optional timestamp comment, which callers can disable).
* **Mode-aware.** Light values form the base; dark values that differ are
  emitted as an override block / per-mode map / dark variant.
* **No Node/Style-Dictionary dependency.** This is pure Python so the framework
  test suite can exercise the full transform on CI (which has no Node).

The ``bin/build-tokens`` wrapper dispatches to this engine for the built-in /
``custom`` path and to Style Dictionary when the operator configures and
installs it.
"""
from __future__ import annotations

import datetime
import json
import re
from pathlib import Path

GENERATED_HEADER = "generated — do not edit directly"

_TOKEN_REF_RE = re.compile(r"\{([^}]+)\}")


class TokenBuildError(Exception):
    """Raised for actionable build failures (broken refs, missing source)."""


# ---------------------------------------------------------------------------
# DTCG flattening + alias resolution
# ---------------------------------------------------------------------------

def _flatten(obj: object, prefix: str = "") -> dict[str, dict]:
    """Return {dot.path: token-node} for every leaf ($value-bearing) node."""
    out: dict[str, dict] = {}
    if not isinstance(obj, dict):
        return out
    for key, val in obj.items():
        if key.startswith("$"):
            continue
        full = f"{prefix}.{key}" if prefix else key
        if isinstance(val, dict) and "$value" in val:
            out[full] = val
        elif isinstance(val, dict):
            out.update(_flatten(val, full))
    return out


def _resolve_value(raw: str, primitives: dict[str, dict], path: str) -> str:
    """Resolve {alias.path} references against the primitive map.

    Raises TokenBuildError on a broken reference so the build fails loudly.
    """
    if not isinstance(raw, str):
        return raw

    def repl(m: re.Match) -> str:
        ref = m.group(1)
        node = primitives.get(ref)
        if node is None:
            raise TokenBuildError(
                f"broken token reference '{{{ref}}}' in '{path}' — "
                "no matching primitive in tokens/primitives.tokens.json"
            )
        return str(node.get("$value"))

    return _TOKEN_REF_RE.sub(repl, raw)


def _load(path: Path) -> dict:
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise TokenBuildError(f"missing token source file: {path}") from exc
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise TokenBuildError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise TokenBuildError(f"token file must be a JSON object: {path}")
    return data


# ---------------------------------------------------------------------------
# Resolved model
# ---------------------------------------------------------------------------

class ResolvedTokens:
    """Resolved, mode-aware token model derived from the DTCG source."""

    def __init__(self, design_root: Path):
        self.design_root = design_root
        tokens_dir = design_root / "tokens"
        primitives_raw = _load(tokens_dir / "primitives.tokens.json")
        semantic_raw = _load(tokens_dir / "semantic.tokens.json")

        self.primitives: dict[str, dict] = _flatten(primitives_raw)
        semantic = _flatten(semantic_raw)

        # Base (light) resolved values for every semantic token.
        self.base: dict[str, str] = {}
        self.types: dict[str, str] = {}
        for path in sorted(semantic):
            node = semantic[path]
            self.base[path] = _resolve_value(node.get("$value"), self.primitives, path)
            self.types[path] = node.get("$type", "")

        # Mode overrides. Mode files carry primitive-shaped trees; map each
        # semantic token to its mode value by following the same primitive
        # alias the semantic token uses.
        self.modes: dict[str, dict[str, str]] = {}
        self._semantic_alias: dict[str, str | None] = {}
        for path in sorted(semantic):
            raw = semantic[path].get("$value")
            m = _TOKEN_REF_RE.fullmatch(raw.strip()) if isinstance(raw, str) else None
            self._semantic_alias[path] = m.group(1) if m else None

        modes_dir = tokens_dir / "modes"
        if modes_dir.is_dir():
            for mode_file in sorted(modes_dir.glob("*.tokens.json")):
                mode_name = mode_file.name.replace(".tokens.json", "")
                mode_flat = _flatten(_load(mode_file))
                resolved: dict[str, str] = {}
                for path in sorted(semantic):
                    alias = self._semantic_alias.get(path)
                    if alias is not None and alias in mode_flat:
                        resolved[path] = str(mode_flat[alias].get("$value"))
                    else:
                        resolved[path] = self.base[path]
                self.modes[mode_name] = resolved

    @property
    def mode_names(self) -> list[str]:
        return sorted(self.modes)

    def dark_overrides(self) -> dict[str, str]:
        """Tokens whose dark value differs from the base (light) value."""
        dark = self.modes.get("dark", {})
        light = self.modes.get("light", self.base)
        return {
            path: dark[path]
            for path in sorted(dark)
            if dark.get(path) != light.get(path)
        }


# ---------------------------------------------------------------------------
# CSS var naming
# ---------------------------------------------------------------------------

_PREFIX = "ds"


def _css_var_name(path: str) -> str:
    return "--" + _PREFIX + "-" + path.replace(".", "-")


# ---------------------------------------------------------------------------
# Emitters (each returns a deterministic string body)
# ---------------------------------------------------------------------------

def _header_css() -> str:
    return f"/* {GENERATED_HEADER} */\n"


def _header_line_comment() -> str:
    return f"// {GENERATED_HEADER}\n"


def render_css(rt: ResolvedTokens) -> str:
    lines = [_header_css().rstrip("\n"), ":root {"]
    for path in sorted(rt.base):
        lines.append(f"  {_css_var_name(path)}: {rt.base[path]};")
    lines.append("}")

    overrides = rt.dark_overrides()
    if overrides:
        block = ["  :root {"]
        for path in sorted(overrides):
            block.append(f"    {_css_var_name(path)}: {overrides[path]};")
        block.append("  }")
        body = "\n".join(block)
        lines.append("")
        lines.append('@media (prefers-color-scheme: dark) {')
        lines.append(body)
        lines.append("}")
        lines.append("")
        lines.append('[data-theme="dark"] {')
        for path in sorted(overrides):
            lines.append(f"  {_css_var_name(path)}: {overrides[path]};")
        lines.append("}")
    return "\n".join(lines) + "\n"


# Map a token category (first path segment) to a Tailwind theme.extend key.
_TAILWIND_KEY = {
    "color": "colors",
    "space": "spacing",
    "radius": "borderRadius",
    "elevation": "boxShadow",
    "font": "fontFamily",
}


def _nested_set(tree: dict, parts: list[str], value) -> None:
    node = tree
    for p in parts[:-1]:
        node = node.setdefault(p, {})
    node[parts[-1]] = value


def render_tailwind(rt: ResolvedTokens) -> str:
    extend: dict[str, dict] = {}
    dark_extend: dict[str, dict] = {}
    overrides = rt.dark_overrides()
    for path in sorted(rt.base):
        cat = path.split(".")[0]
        tw_key = _TAILWIND_KEY.get(cat)
        if tw_key is None:
            continue
        sub_parts = path.split(".")[1:] or [cat]
        _nested_set(extend.setdefault(tw_key, {}), sub_parts, rt.base[path])
        if path in overrides:
            _nested_set(dark_extend.setdefault(tw_key, {}), sub_parts, overrides[path])

    payload = {"theme": {"extend": extend}}
    if dark_extend:
        payload["darkMode"] = "class"
        payload["theme"]["extendDark"] = dark_extend

    body = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False)
    lines = [
        _header_line_comment().rstrip("\n"),
        "// Tailwind theme config generated from the DTCG token source.",
        "// `theme.extend` is the light/base palette. `theme.extendDark` holds dark-mode",
        "// overrides for tokens whose dark value differs (merge under your dark variant).",
        f"module.exports = {body};",
        "",
    ]
    return "\n".join(lines)


def _ts_ident(path: str) -> str:
    return path  # kept as dotted string keys; safe in a record literal


def render_ts(rt: ResolvedTokens) -> str:
    lines = [_header_line_comment().rstrip("\n")]
    lines.append("// Typed design token constants generated from the DTCG source.")
    lines.append("")
    lines.append("export type TokenMode = " + " | ".join(
        f'"{m}"' for m in rt.mode_names) + ";" if rt.mode_names else "export type TokenMode = string;")
    lines.append("export type TokenName =")
    paths = sorted(rt.base)
    for i, path in enumerate(paths):
        sep = ";" if i == len(paths) - 1 else ""
        lines.append(f'  | "{path}"{sep}')
    lines.append("")
    lines.append("export type TokenMap = Record<TokenName, string>;")
    lines.append("")

    # Base map.
    lines.append("export const tokens: TokenMap = {")
    for path in paths:
        lines.append(f'  "{path}": {json.dumps(rt.base[path], ensure_ascii=False)},')
    lines.append("};")
    lines.append("")

    # Per-mode maps.
    lines.append("export const tokensByMode: Record<TokenMode, TokenMap> = {")
    for mode in rt.mode_names:
        lines.append(f'  "{mode}": {{')
        for path in paths:
            val = rt.modes[mode].get(path, rt.base[path])
            lines.append(f'    "{path}": {json.dumps(val, ensure_ascii=False)},')
        lines.append("  },")
    lines.append("};")
    lines.append("")
    return "\n".join(lines)


def render_json(rt: ResolvedTokens) -> str:
    flat = {path: rt.base[path] for path in sorted(rt.base)}
    payload = {
        "$generated": GENERATED_HEADER,
        "tokens": flat,
        "modes": {m: rt.modes[m] for m in rt.mode_names},
    }
    return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


# ---------------------------------------------------------------------------
# Target dispatch
# ---------------------------------------------------------------------------

_RENDERERS = {
    "css": ("css/tokens.css", render_css),
    "tailwind": ("tailwind/theme.config.js", render_tailwind),
    "ts": ("ts/tokens.ts", render_ts),
    "json": ("json/tokens.json", render_json),
}


# ---------------------------------------------------------------------------
# Export staleness + manifest parity
# ---------------------------------------------------------------------------

def _token_source_mtime(design_root: Path) -> float:
    """Newest mtime across the DTCG token source tree."""
    tokens_dir = design_root / "tokens"
    mtimes = [p.stat().st_mtime for p in tokens_dir.rglob("*.tokens.json") if p.is_file()]
    return max(mtimes) if mtimes else 0.0


def _export_mtime(design_root: Path) -> float | None:
    """Oldest mtime across generated export files, or None when no exports exist."""
    exports_dir = design_root / "exports"
    files = [
        p for p in exports_dir.rglob("*")
        if p.is_file() and p.suffix in {".css", ".js", ".ts", ".json"}
        and p.name != "README.md"
    ]
    if not files:
        return None
    return min(p.stat().st_mtime for p in files)


def exports_exist(design_root: Path) -> bool:
    return _export_mtime(design_root) is not None


def exports_stale(design_root: Path) -> bool:
    """True when the token source is newer than the generated exports.

    Also True when exports are missing entirely (nothing generated yet).
    """
    export_mtime = _export_mtime(design_root)
    if export_mtime is None:
        return True
    return _token_source_mtime(design_root) > export_mtime


def update_manifest_parity(design_root: Path, *, generated: bool) -> bool:
    """Write export-parity fields into manifest.json validationSummary.

    Sets ``exportsGenerated``, ``exportsAt`` (ISO-8601, only when generated),
    and ``exportsStale``. Returns True when the manifest was written.
    Silently no-ops when manifest.json is absent or invalid.
    """
    manifest_path = design_root / "manifest.json"
    if not manifest_path.exists():
        return False
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return False
    if not isinstance(data, dict):
        return False
    summary = data.setdefault("validationSummary", {})
    if not isinstance(summary, dict):
        return False
    summary["exportsGenerated"] = bool(generated)
    if generated:
        summary["exportsAt"] = datetime.datetime.now(
            datetime.timezone.utc
        ).replace(microsecond=0).isoformat()
    summary["exportsStale"] = exports_stale(design_root)
    manifest_path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return True


def build(
    design_root: Path,
    targets: list[dict] | None = None,
    *,
    update_manifest: bool = True,
) -> list[Path]:
    """Run the built-in transform for the configured targets.

    ``targets`` is the build.config.json ``targets`` array
    (``[{format, outputDir, options}]``). When None, all four standard
    formats are emitted to their default ``exports/<fmt>/`` dirs.

    Returns the list of written file paths. Raises TokenBuildError on any
    broken reference or missing source. When ``update_manifest`` is True and a
    manifest.json exists, records export-parity fields after a successful build.
    """
    rt = ResolvedTokens(design_root)
    written: list[Path] = []

    if targets is None:
        targets = [{"format": fmt} for fmt in ("css", "tailwind", "ts", "json")]

    for target in targets:
        fmt = target.get("format")
        spec = _RENDERERS.get(fmt)
        if spec is None:
            raise TokenBuildError(
                f"unknown target format '{fmt}' — supported: {sorted(_RENDERERS)}"
            )
        default_rel, renderer = spec
        out_dir = target.get("outputDir")
        if out_dir:
            out_path = design_root / out_dir / Path(default_rel).name
        else:
            out_path = design_root / "exports" / default_rel
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(renderer(rt), encoding="utf-8")
        written.append(out_path)

    if update_manifest:
        update_manifest_parity(design_root, generated=True)

    return written
