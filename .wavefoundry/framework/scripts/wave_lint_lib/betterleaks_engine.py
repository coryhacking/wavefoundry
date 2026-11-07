"""Pinned Betterleaks offline detection, evaluated only behind the worker boundary.

The semantics are ported from Betterleaks v2.0.0-rc.7 (MIT). Provider programs
are inert metadata. This module does not open project files or publish findings.
See scan/NOTICE.md for provenance and notices.
"""
from __future__ import annotations

from bisect import bisect_right
from collections import OrderedDict
from itertools import islice, product
import math
import re
import time

from .expr_filter import compile_filter, compile_regex, evaluate_filter
from .secret_tokenizer import entropy, verify_assets

PROFILE = "betterleaks-v2-8f376ff9"
MAX_RULES = 1024
MAX_MATCHES = 20000
MAX_COMPONENT_SETS = 100
MAX_RESULT_BYTES = 8 * 1024 * 1024
MAX_CONTENT_BYTES = 5 * 1024 * 1024
MAX_LINES = 200000
_RULE_FIELDS = frozenset(("id", "description", "regex", "path", "valueGroup",
    "tags", "specificity", "confidence", "keywords", "components", "skipReport",
    "validate", "analyze", "revoke", "filter", "allowlists"))


class ConfigurationError(ValueError):
    """Invalid or unsupported detection configuration; never includes input text."""


class WorkLimit(Exception):
    """An explicit bound prevented complete detection."""


def _bytes(value: str) -> bytes:
    return value.encode("utf-8", "surrogateescape")


def exceeded_input_limit(content: str) -> str | None:
    """Name the fixed input limit *content* exceeds, or None.

    The scanner parent and this engine share this one predicate so a file the
    parent sends can never fail the engine's own size or newline bound. The
    newline count is the engine's bound; it is not a line count. Every string
    the parent sends encodes strictly, where surrogateescape changes nothing.
    """
    if len(_bytes(content)) > MAX_CONTENT_BYTES:
        return "decoded_size"
    if content.count("\n") > MAX_LINES:
        return "line_count"
    return None


def _window(text: str) -> tuple[int, int, int, int, bool] | None:
    """Directional context grammar: line counts include the matching line."""
    if text.strip() in ("", "0"):
        return None
    before_l = after_l = before_c = after_c = 0
    has_lines = False
    for token in text.split(","):
        m = re.fullmatch(r"([+-]?)([0-9]+)([LC]?)", token.strip(), re.I)
        if not m:
            raise ConfigurationError("invalid_component_window")
        direction, count, unit = m.groups()
        amount = int(count)
        if amount > MAX_CONTENT_BYTES:
            raise ConfigurationError("component_window_limit")
        if unit.upper() == "L":
            has_lines = True
            amount = max(0, amount - 1)
            if direction != "+": before_l = max(before_l, amount)
            if direction != "-": after_l = max(after_l, amount)
        else:
            if direction != "+": before_c = max(before_c, amount)
            if direction != "-": after_c = max(after_c, amount)
    return before_l, after_l, before_c, after_c, has_lines


def _near(primary: dict, component: dict, window: tuple | None, size: int) -> bool:
    if window is None:
        return True
    lb, la, cb, ca, has_lines = window
    p, c = primary["location"], component["location"]
    if not has_lines:
        return max(primary["_start"] - cb, 0) <= component["_start"] < min(primary["_end"] + ca, size)
    if not p["start_line"] - lb <= c["start_line"] <= p["end_line"] + la:
        return False
    if p["start_line"] == p["end_line"] and (cb or ca):
        return max(p["start_column"] - 1 - cb, 0) <= c["start_column"] - 1 < p["end_column"] + ca
    return True


def _identity(finding: dict) -> tuple:
    return (finding["rule_id"], finding["_start"], finding["_end"], finding["match"]["value"])


class BetterleaksEngine:
    """Immutable compiled profile; callers must enforce the process deadline."""

    def __init__(self, config: dict):
        if not isinstance(config, dict):
            raise ConfigurationError("configuration_not_table")
        if config.get("wavefoundryProfile", PROFILE) != PROFILE:
            raise ConfigurationError("unsupported_profile")
        if set(config) - {"title", "minVersion", "wavefoundryProfile", "prefilter", "filter", "rules", "policy", "allowlist"}:
            raise ConfigurationError("unsupported_configuration_field")
        rules = config.get("rules", [])
        if not isinstance(rules, list) or len(rules) > MAX_RULES:
            raise ConfigurationError("rule_count_limit")
        verify_assets()
        self.prefilter = compile_filter(config.get("prefilter", "false"), prefilter=True)
        self.global_filter = compile_filter(config.get("filter", "false"))
        allowlist = config.get("allowlist", {})
        if not isinstance(allowlist, dict) or set(allowlist) - {"regexes", "stopwords", "paths", "description"}:
            raise ConfigurationError("unsupported_value_allowlist")
        if not isinstance(allowlist.get("description", ""), str):
            raise ConfigurationError("invalid_value_allowlist")
        for key in ("regexes", "stopwords", "paths"):
            if not isinstance(allowlist.get(key, []), list) or any(not isinstance(v, str) for v in allowlist.get(key, [])):
                raise ConfigurationError("invalid_value_allowlist")
        self.value_patterns = [compile_regex(p) for p in allowlist.get("regexes", [])]
        self.path_patterns = [compile_regex(p) for p in allowlist.get("paths", [])]
        self.stopwords = [word.lower() for word in allowlist.get("stopwords", [])]
        self.rules = []
        self.by_id = {}
        for source in rules:
            if not isinstance(source, dict) or set(source) - _RULE_FIELDS:
                raise ConfigurationError("unsupported_rule_field")
            rid = source.get("id", "")
            if not isinstance(rid, str) or not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]{0,127}", rid) or rid in self.by_id:
                raise ConfigurationError("invalid_or_duplicate_rule_id")
            rule = dict(source)
            for key in ("regex", "path", "description", "filter", "confidence", "validate", "analyze", "revoke"):
                if not isinstance(rule.get(key, ""), str):
                    raise ConfigurationError("invalid_rule_string")
            if not rule.get("regex") and not rule.get("path"):
                raise ConfigurationError("rule_has_no_detector")
            for key in ("valueGroup", "specificity"):
                if type(rule.get(key, 0)) is not int:
                    raise ConfigurationError("invalid_rule_integer")
            if type(rule.get("skipReport", False)) is not bool:
                raise ConfigurationError("invalid_skip_report")
            if rule.get("confidence", "") not in ("", "low", "medium", "high"):
                raise ConfigurationError("invalid_confidence")
            for key in ("tags", "keywords"):
                if not isinstance(rule.get(key, []), list) or any(not isinstance(x, str) for x in rule.get(key, [])):
                    raise ConfigurationError("invalid_rule_list")
            rule["_regex"] = compile_regex(rule["regex"]) if rule.get("regex") else None
            rule["_path"] = compile_regex(rule["path"]) if rule.get("path") else None
            group = rule.get("valueGroup", 0)
            if group < 0 or group > (rule["_regex"].groups if rule["_regex"] else 0):
                raise ConfigurationError("invalid_capture_selector")
            rule["_filter"] = compile_filter(rule.get("filter") or "false")
            rule["_keywords"] = tuple(x.lower() for x in rule.get("keywords", []))
            rule["_allow_paths"], rule["_allow_regexes"] = [], []
            allowlists = rule.get("allowlists", [])
            if not isinstance(allowlists, list):
                raise ConfigurationError("invalid_rule_allowlist")
            for allow in allowlists:
                if not isinstance(allow, dict) or set(allow) - {"paths", "regexes", "description"}:
                    raise ConfigurationError("unsupported_rule_allowlist")
                for key in ("paths", "regexes"):
                    values = allow.get(key, [])
                    if not isinstance(values, list) or any(not isinstance(x, str) for x in values):
                        raise ConfigurationError("invalid_rule_allowlist")
                    rule["_allow_" + key].extend(compile_regex(x) for x in values)
            components = rule.get("components", [])
            if not isinstance(components, list) or len(components) > 64:
                raise ConfigurationError("invalid_components")
            seen = set()
            rule["_components"] = []
            for component in components:
                if not isinstance(component, dict) or set(component) - {"id", "optional", "within"}:
                    raise ConfigurationError("unsupported_component_field")
                cid = component.get("id")
                if not isinstance(cid, str) or cid == rid or cid in seen or type(component.get("optional", False)) is not bool or not isinstance(component.get("within", ""), str):
                    raise ConfigurationError("invalid_component")
                seen.add(cid)
                rule["_components"].append((cid, component.get("optional", False), _window(component.get("within", ""))))
            if rule["_regex"] is None and (components or any(rule.get(k) for k in ("validate", "analyze", "revoke"))):
                raise ConfigurationError("invalid_path_only_rule")
            self.rules.append(rule)
            self.by_id[rid] = rule
        for rule in self.rules:
            if any(cid not in self.by_id for cid, _, _ in rule["_components"]):
                raise ConfigurationError("missing_component_rule")
        self.rules.sort(key=lambda r: -r.get("specificity", 0))

    def path_excluded(self, path: str) -> bool:
        """Local pre-read exclusions; execute only within the bounded worker."""
        return any(pattern.search(path) for pattern in self.path_patterns)

    def scan(self, content: str, path: str, metadata_only: bool = False) -> dict:
        result = {"findings": [], "complete": True, "diagnostics": [], "prefilter_skipped": False, "costs": {}}
        diagnostics = result["diagnostics"]
        if not isinstance(content, str) or not isinstance(path, str):
            raise ConfigurationError("invalid_scan_input")
        if self.path_excluded(path):
            return result
        if exceeded_input_limit(content) is not None:
            return {**result, "complete": False, "diagnostics": ["input_limit"]}
        raw = _bytes(content)
        try:
            if evaluate_filter(self.prefilter, {}, {"path": path}):
                result["prefilter_skipped"] = True
                return result
        except Exception:
            diagnostics.append("prefilter_evaluation_error")
            result["complete"] = False
        # Go indexes and columns are byte offsets; Python regexp indexes are runes.
        if content.isascii():
            byte_offset = lambda i: i
        else:
            from array import array
            offsets = array("I", [0])
            for char in content:
                offsets.append(offsets[-1] + len(_bytes(char)))
            byte_offset = offsets.__getitem__
        line_starts = [0] + [m.end() for m in re.finditer(b"\n", raw) if m.end() < len(raw)]
        lower = content.lower()
        cache = {}
        work = [0, 0]

        def basic(rule: dict) -> list[dict]:
            rid = rule["id"]
            if rid in cache:
                return cache[rid]
            started = time.monotonic()
            hits = []
            cache[rid] = hits
            if rule["_path"] and (not path or not rule["_path"].search(path)):
                return hits
            if any(p.search(path) for p in rule["_allow_paths"]):
                return hits
            if rule["_regex"] is None:
                hits.append({"rule_id": rid, "description": rule.get("description", ""),
                    "confidence": rule.get("confidence", ""), "match": {"full": "file detected: " + path, "value": "", "line": ""},
                    "location": {"path": path, "start_line": 0, "end_line": 0, "start_column": 0, "end_column": 0}, "_start": 0, "_end": 0})
                return hits
            if metadata_only or (rule["_keywords"] and not any(k in lower for k in rule["_keywords"])):
                return hits
            for match in rule["_regex"].finditer(content):
                work[0] += 1
                if work[0] > MAX_MATCHES:
                    raise WorkLimit("match_limit")
                full = match.group(0).strip("\n")
                start, filter_end = byte_offset(match.start()), byte_offset(match.end())
                end = start + len(_bytes(full))
                sl = bisect_right(line_starts, start)
                el = bisect_right(line_starts, end)
                line_end = line_starts[el] if el < len(line_starts) else len(raw)
                line = raw[line_starts[sl - 1]:line_end].decode("utf-8", "surrogateescape")
                group = rule.get("valueGroup", 0)
                value = (match.group(group) or "") if group else next((v for v in match.groups() if v), full)
                captures = {k: v for k, v in match.groupdict().items() if v}
                finding = {"secret": value, "match": full, "line": line, "rule_id": rid,
                    "description": rule.get("description", ""), "confidence": rule.get("confidence", ""), "context": "",
                    "captures": captures, "entropy": str(entropy(value)), "fragment_raw": content,
                    "match_start_idx": start, "match_end_idx": filter_end,
                    "match_line_start_idx": max(raw.rfind(b"\n", 0, start), raw.rfind(b"\r", 0, start)) + 1,
                    "match_line_end_idx": min((i for i in (raw.find(b"\n", filter_end), raw.find(b"\r", filter_end)) if i >= 0), default=len(raw))}
                attributes = {"path": path}
                skip = False
                for program in (self.global_filter, rule["_filter"]):
                    try:
                        skip = evaluate_filter(program, finding, attributes)
                    except Exception:
                        if len(diagnostics) < 64:
                            diagnostics.append("filter_evaluation_error:" + rid)
                        result["complete"] = False
                    if "confidence" in attributes:
                        finding["confidence"] = attributes.pop("confidence")
                    if skip:
                        break
                if skip or any(p.search(full) or p.search(line) for p in rule["_allow_regexes"]):
                    continue
                if any(p.fullmatch(value) for p in self.value_patterns) or any(word in value.lower() for word in self.stopwords):
                    continue
                work[1] += len(_bytes(full)) + len(_bytes(value)) + len(_bytes(line))
                if work[1] > MAX_RESULT_BYTES:
                    raise WorkLimit("result_limit")
                hit = {"rule_id": rid, "description": rule.get("description", ""), "confidence": finding["confidence"],
                    "match": {"full": full, "value": value, "line": line},
                    "location": {"path": path, "start_line": sl, "end_line": el, "start_column": start - line_starts[sl-1] + 1, "end_column": end - line_starts[el-1]},
                    "_start": start, "_end": end}
                if captures:
                    hit["match"]["captures"] = captures
                hits.append(hit)
            result["costs"][rid] = time.monotonic() - started
            return hits

        def superseded(hit: dict, owners: list[dict]) -> bool:
            for owner in owners:
                candidates = [owner] + [c for group in owner.get("component_sets", []) for c in group["components"]]
                for candidate in candidates:
                    if hit["rule_id"] == candidate["rule_id"]:
                        continue
                    if self.by_id[candidate["rule_id"]].get("specificity", 0) <= self.by_id[hit["rule_id"]].get("specificity", 0):
                        continue
                    if hit["_start"] < candidate["_end"] and candidate["_start"] < hit["_end"] and hit["match"]["value"] in candidate["match"]["value"]:
                        return True
            return False

        findings = result["findings"]
        try:
            for rule in self.rules:
                if rule.get("skipReport", False):
                    continue
                for original in basic(rule):
                    if superseded(original, findings):
                        continue
                    hit = dict(original)
                    groups = OrderedDict()
                    missing = False
                    for cid, optional, window in rule["_components"]:
                        candidates = []
                        for component in basic(self.by_id[cid]):
                            if _near(hit, component, window, len(raw)):
                                # Upstream's component record does not carry a
                                # top-level finding's confidence or description.
                                candidates.append({**{k: v for k, v in component.items() if k not in ("confidence", "description")}, "optional": optional})
                        if not candidates and not optional:
                            missing = True
                            break
                        if candidates:
                            groups[cid] = candidates
                    if missing:
                        continue
                    if groups:
                        count = math.prod(len(group) for group in groups.values())
                        hit["component_sets"] = []
                        for values in islice(product(*groups.values()), MAX_COMPONENT_SETS):
                            work[1] += sum(256 + sum(len(_bytes(c["match"][k])) for k in ("full", "value", "line")) for c in values)
                            if work[1] > MAX_RESULT_BYTES:
                                raise WorkLimit("result_limit")
                            hit["component_sets"].append({"components": list(values)})
                        if count > MAX_COMPONENT_SETS:
                            hit["component_sets_truncated"] = True
                            result["complete"] = False
                            if "component_set_limit" not in diagnostics:
                                diagnostics.append("component_set_limit")
                    findings.append(hit)
            component_ids = {_identity(c) for f in findings for group in f.get("component_sets", []) for c in group["components"]}
            result["findings"] = [f for f in findings if _identity(f) not in component_ids and not superseded(f, findings)]
        except WorkLimit as exc:
            result["complete"] = False
            diagnostics.append(str(exc))
        return result
