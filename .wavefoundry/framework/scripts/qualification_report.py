"""Bounded qualification evidence and deterministic exact profile comparison.

Release-only optional evidence, never framework receipt authority.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import sys
import uuid
from pathlib import Path

# Follow the framework entry/library rule before importing sibling modules.
if __name__ == "__main__" or sys.pycache_prefix is None:
    sys.dont_write_bytecode = True
import bytecode_cache  # noqa: E402

if __name__ == "__main__":
    bytecode_cache.configure()

import contained_files

OWNER = "wavefoundry-qualification-v1"
MAX_BYTES = 8 * 1024 * 1024
MAX_WORKERS = 2000
MAX_SKIPS = 20000
MAX_FIELD = 4096


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def output_path(root, path):
    """Reports live only in the ignored, unpacked qualification cache."""
    root = Path(root).resolve()
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = root / candidate
    parts = contained_files.relative_parts(root, candidate)
    if len(parts) < 4 or parts[:3] != (".wavefoundry", "cache", "qualification"):
        raise ValueError("report must be under .wavefoundry/cache/qualification")
    current = root
    for part in parts:
        current /= part
        try:
            entry = current.lstat()
        except FileNotFoundError:
            continue
        if current != candidate and (stat.S_ISLNK(entry.st_mode) or contained_files._is_windows_link(str(current))):
            raise ValueError("linked report target refused")
        if current == candidate and (not stat.S_ISREG(entry.st_mode) or contained_files._is_windows_link(str(current))):
            raise ValueError("special report target refused")
    return candidate


def read_report(root, path):
    path = output_path(root, path)
    data = contained_files.read_contained_bytes(root, path, max_bytes=MAX_BYTES)
    value = json.loads(data)
    if not isinstance(value, dict) or value.get("owner") != OWNER:
        raise ValueError("unowned report target refused")
    return value


def write_report(root, path, report):
    path = output_path(root, path)
    if path.exists():
        read_report(root, path)
    data = (json.dumps(report, sort_keys=True, ensure_ascii=True, separators=(",", ":")) + "\n").encode()
    if len(data) > MAX_BYTES:
        raise ValueError("report exceeds byte bound")
    contained_files.write_contained_bytes(root, path, data, mode=0o600)


def worker_detail(output, nonce, returncode, tests, skipped):
    prefix = f"WF_QUALIFICATION:{nonce}:"
    lines = [line[len(prefix):] for line in output.splitlines() if line.startswith(prefix)]
    issues = []
    detail = {}
    if len(lines) != 1:
        issues.append("missing or duplicate worker envelope")
    else:
        try:
            if len(lines[0]) > 4 * 1024 * 1024:
                raise ValueError()
            detail = json.loads(lines[0])
            if not isinstance(detail, dict):
                raise ValueError()
        except (ValueError, TypeError):
            issues.append("malformed worker envelope")
            detail = {}
    clean = "\n".join(line for line in output.splitlines() if not line.startswith(prefix))
    summaries = list(re.finditer(r"(?m)^Ran (\d+) tests? in [\d.]+s\s*$", clean))
    tail = clean[summaries[-1].end():].strip() if summaries else ""
    terminal = re.fullmatch(r"(?:OK|FAILED)(?: \([^\n]+\))?", tail)
    if not summaries or not terminal:
        issues.append("missing or malformed terminal unittest summary")
    elif (int(summaries[-1].group(1)) != tests
          or (tail.startswith("OK") != (returncode == 0))
          or int((re.findall(r"\bskipped=(\d+)", tail) or ["0"])[-1]) != skipped):
        issues.append("contradictory terminal unittest summary")
    if (detail.get("tests") != tests or detail.get("skipped") != skipped
            or detail.get("successful") != (returncode == 0) or detail.get("terminal") is not True):
        issues.append("contradictory worker summary")
    issues += detail.get("issues", []) if isinstance(detail.get("issues", []), list) else ["malformed issues"]
    rows = detail.get("skips", [])
    if not isinstance(rows, list) or len(rows) > MAX_SKIPS or len(rows) != skipped:
        issues.append("incomplete skip detail")
        rows = []
    seen = set()
    valid = []
    for row in rows:
        if (not isinstance(row, dict) or any(not isinstance(row.get(k), str)
                or len(row[k]) > MAX_FIELD for k in ("id", "reason"))):
            issues.append("malformed skip observation")
            continue
        if row["id"] in seen:
            issues.append("duplicate skipped-test identity")
        seen.add(row["id"])
        marker = row.get("default_profile_only")
        if marker is not None and (not isinstance(marker, str) or len(marker) > MAX_FIELD):
            issues.append("malformed default-profile marker")
            marker = None
        valid.append({"id": row["id"], "reason": row["reason"], "default_profile_only": marker})
    return {"terminal": bool(terminal), "complete": not issues,
            "skips": sorted(valid, key=lambda r: r["id"]), "issues": sorted(set(str(x)[:256] for x in issues))[:20]}


def make_report(identity, expected, results, rc, availability="executed"):
    workers = []
    for result in sorted(results, key=lambda r: r.name):
        detail = result.qualification or {"terminal": False, "complete": False, "skips": [], "issues": ["executed detail unavailable"]}
        workers.append({"name": result.name, "returncode": result.returncode,
                        "tests": result.test_count, "skipped": result.skip_count, **detail})
    observed = [r["name"] for r in workers]
    complete = (availability == "executed" and len(expected) <= MAX_WORKERS
                and observed == sorted(expected) and len(set(observed)) == len(observed)
                and all(r["complete"] for r in workers))
    return {"owner": OWNER, "schema_version": 1, "run_id": uuid.uuid4().hex,
            "identity": identity, "availability": availability, "expected_workers": sorted(expected),
            "observed_workers": observed, "returncode": rc, "complete": complete,
            "workers": workers[:MAX_WORKERS]}


def validate(report):
    if (report.get("owner") != OWNER or type(report.get("schema_version")) is not int
            or report["schema_version"] != 1 or report.get("complete") is not True):
        raise ValueError("qualification incomplete")
    if not isinstance(report.get("run_id"), str) or not re.fullmatch(r"[0-9a-f]{32}", report["run_id"]):
        raise ValueError("malformed execution run identity")
    if (report.get("availability") not in ("executed", "reused")
            or type(report.get("returncode")) is not int or report["returncode"] != 0):
        raise ValueError("qualification did not pass")
    workers = report.get("workers")
    expected = report.get("expected_workers")
    if not isinstance(workers, list) or len(workers) > MAX_WORKERS or not isinstance(expected, list):
        raise ValueError("invalid worker inventory")
    if any(not isinstance(r, dict) or not isinstance(r.get("name"), str)
           or len(r["name"]) > MAX_FIELD for r in workers):
        raise ValueError("malformed worker")
    if any(not isinstance(name, str) or len(name) > MAX_FIELD for name in expected):
        raise ValueError("malformed expected worker")
    names = [r["name"] for r in workers]
    if len(set(names)) != len(names) or sorted(names) != sorted(expected) or names != report.get("observed_workers"):
        raise ValueError("missing or duplicate workers")
    skips = {}
    for row in workers:
        if not isinstance(row, dict):
            raise ValueError("malformed worker")
        if (type(row.get("returncode")) is not int or row["returncode"] != 0
                or row.get("terminal") is not True or row.get("complete") is not True or row.get("issues")):
            raise ValueError("invalid terminal worker")
        if any(type(row.get(k)) is not int or row[k] < 0 for k in ("tests", "skipped")):
            raise ValueError("invalid worker counts")
        observations = row.get("skips")
        if not isinstance(observations, list) or len(observations) != row["skipped"] or len(observations) > MAX_SKIPS:
            raise ValueError("contradictory skip count")
        for item in observations:
            if not isinstance(item, dict) or any(not isinstance(item.get(k), str) or len(item[k]) > MAX_FIELD for k in ("id", "reason")):
                raise ValueError("malformed skip")
            key = (row["name"], item["id"])
            if key in skips:
                raise ValueError("duplicate skipped-test identity")
            skips[key] = item
    return skips


def compare(default, candidate, profile):
    baseline = validate(default)
    actual = validate(candidate)
    if profile not in ("second", "declared"):
        raise ValueError("comparison profile must be second or declared")
    for report in (default, candidate):
        identity = report.get("identity")
        if (not isinstance(identity, dict) or not isinstance(identity.get("source_hash"), str)
                or not re.fullmatch(r"[0-9a-f]{64}", identity["source_hash"])):
            raise ValueError("malformed source identity")
    identity = candidate["identity"]
    executed = candidate.get("executed_identity")
    if (any(not isinstance(identity.get(key), str)
            or not re.fullmatch(r"[0-9a-f]{64}", identity[key])
            for key in ("profile_input_hash", "applied_profile_hash"))
            or not isinstance(executed, dict) or executed.get("profile") != profile
            or not isinstance(executed.get("source_hash"), str)
            or not re.fullmatch(r"[0-9a-f]{64}", executed["source_hash"])):
        raise ValueError("missing or malformed actual-profile provenance")
    if (default["identity"]["profile"] != "default" or candidate["identity"]["profile"] != profile
            or default["identity"]["source_hash"] != candidate["identity"]["source_hash"]
            or default["expected_workers"] != candidate["expected_workers"]):
        raise ValueError("qualification identity mismatch")
    for key, row in baseline.items():
        if key not in actual or actual[key]["reason"] != row["reason"]:
            raise ValueError("missing skip or changed reason")
    extra = set(actual) - set(baseline)
    if profile == "declared" and extra:
        raise ValueError("declared profile has unexpected skips")
    for key in extra:
        row = actual[key]
        marker = row.get("default_profile_only")
        if (not isinstance(marker, str) or not marker or len(marker) > MAX_FIELD
                or not row["reason"].startswith(f"default-profile-only: {marker} (loaded ")
                or not row["reason"].endswith(" differ from the shipped defaults)")):
            raise ValueError("unexpected second-profile skip")
    return {"equal": True, "baseline_skips": len(baseline), "profile_skips": len(actual), "default_only": len(extra)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compare", nargs=2, required=True, metavar=("DEFAULT", "CANDIDATE"))
    parser.add_argument("--profile", choices=("second", "declared"), required=True)
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[3]))
    args = parser.parse_args()
    try:
        print(json.dumps(compare(*(read_report(args.root, path) for path in args.compare), args.profile), sort_keys=True))
        return 0
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(f"qualification refused: {str(exc)[:256]}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
